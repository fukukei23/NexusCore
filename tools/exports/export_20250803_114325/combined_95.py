
# === NexusCore/openenv\Lib\site-packages\pydantic\v1\fields.py ===
import copy
import re
from collections import Counter as CollectionCounter, defaultdict, deque
from collections.abc import Callable, Hashable as CollectionsHashable, Iterable as CollectionsIterable
from typing import (
    TYPE_CHECKING,
    Any,
    Counter,
    DefaultDict,
    Deque,
    Dict,
    ForwardRef,
    FrozenSet,
    Generator,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Pattern,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from typing_extensions import Annotated, Final

from pydantic.v1 import errors as errors_
from pydantic.v1.class_validators import Validator, make_generic_validator, prep_validators
from pydantic.v1.error_wrappers import ErrorWrapper
from pydantic.v1.errors import ConfigError, InvalidDiscriminator, MissingDiscriminator, NoneIsNotAllowedError
from pydantic.v1.types import Json, JsonWrapper
from pydantic.v1.typing import (
    NoArgAnyCallable,
    convert_generics,
    display_as_type,
    get_args,
    get_origin,
    is_finalvar,
    is_literal_type,
    is_new_type,
    is_none_type,
    is_typeddict,
    is_typeddict_special,
    is_union,
    new_type_supertype,
)
from pydantic.v1.utils import (
    PyObjectStr,
    Representation,
    ValueItems,
    get_discriminator_alias_and_values,
    get_unique_discriminator_alias,
    lenient_isinstance,
    lenient_issubclass,
    sequence_like,
    smart_deepcopy,
)
from pydantic.v1.validators import constant_validator, dict_validator, find_validators, validate_json

Required: Any = Ellipsis

T = TypeVar('T')


class UndefinedType:
    def __repr__(self) -> str:
        return 'PydanticUndefined'

    def __copy__(self: T) -> T:
        return self

    def __reduce__(self) -> str:
        return 'Undefined'

    def __deepcopy__(self: T, _: Any) -> T:
        return self


Undefined = UndefinedType()

if TYPE_CHECKING:
    from pydantic.v1.class_validators import ValidatorsList
    from pydantic.v1.config import BaseConfig
    from pydantic.v1.error_wrappers import ErrorList
    from pydantic.v1.types import ModelOrDc
    from pydantic.v1.typing import AbstractSetIntStr, MappingIntStrAny, ReprArgs

    ValidateReturn = Tuple[Optional[Any], Optional[ErrorList]]
    LocStr = Union[Tuple[Union[int, str], ...], str]
    BoolUndefined = Union[bool, UndefinedType]


class FieldInfo(Representation):
    """
    Captures extra information about a field.
    """

    __slots__ = (
        'default',
        'default_factory',
        'alias',
        'alias_priority',
        'title',
        'description',
        'exclude',
        'include',
        'const',
        'gt',
        'ge',
        'lt',
        'le',
        'multiple_of',
        'allow_inf_nan',
        'max_digits',
        'decimal_places',
        'min_items',
        'max_items',
        'unique_items',
        'min_length',
        'max_length',
        'allow_mutation',
        'repr',
        'regex',
        'discriminator',
        'extra',
    )

    # field constraints with the default value, it's also used in update_from_config below
    __field_constraints__ = {
        'min_length': None,
        'max_length': None,
        'regex': None,
        'gt': None,
        'lt': None,
        'ge': None,
        'le': None,
        'multiple_of': None,
        'allow_inf_nan': None,
        'max_digits': None,
        'decimal_places': None,
        'min_items': None,
        'max_items': None,
        'unique_items': None,
        'allow_mutation': True,
    }

    def __init__(self, default: Any = Undefined, **kwargs: Any) -> None:
        self.default = default
        self.default_factory = kwargs.pop('default_factory', None)
        self.alias = kwargs.pop('alias', None)
        self.alias_priority = kwargs.pop('alias_priority', 2 if self.alias is not None else None)
        self.title = kwargs.pop('title', None)
        self.description = kwargs.pop('description', None)
        self.exclude = kwargs.pop('exclude', None)
        self.include = kwargs.pop('include', None)
        self.const = kwargs.pop('const', None)
        self.gt = kwargs.pop('gt', None)
        self.ge = kwargs.pop('ge', None)
        self.lt = kwargs.pop('lt', None)
        self.le = kwargs.pop('le', None)
        self.multiple_of = kwargs.pop('multiple_of', None)
        self.allow_inf_nan = kwargs.pop('allow_inf_nan', None)
        self.max_digits = kwargs.pop('max_digits', None)
        self.decimal_places = kwargs.pop('decimal_places', None)
        self.min_items = kwargs.pop('min_items', None)
        self.max_items = kwargs.pop('max_items', None)
        self.unique_items = kwargs.pop('unique_items', None)
        self.min_length = kwargs.pop('min_length', None)
        self.max_length = kwargs.pop('max_length', None)
        self.allow_mutation = kwargs.pop('allow_mutation', True)
        self.regex = kwargs.pop('regex', None)
        self.discriminator = kwargs.pop('discriminator', None)
        self.repr = kwargs.pop('repr', True)
        self.extra = kwargs

    def __repr_args__(self) -> 'ReprArgs':
        field_defaults_to_hide: Dict[str, Any] = {
            'repr': True,
            **self.__field_constraints__,
        }

        attrs = ((s, getattr(self, s)) for s in self.__slots__)
        return [(a, v) for a, v in attrs if v != field_defaults_to_hide.get(a, None)]

    def get_constraints(self) -> Set[str]:
        """
        Gets the constraints set on the field by comparing the constraint value with its default value

        :return: the constraints set on field_info
        """
        return {attr for attr, default in self.__field_constraints__.items() if getattr(self, attr) != default}

    def update_from_config(self, from_config: Dict[str, Any]) -> None:
        """
        Update this FieldInfo based on a dict from get_field_info, only fields which have not been set are dated.
        """
        for attr_name, value in from_config.items():
            try:
                current_value = getattr(self, attr_name)
            except AttributeError:
                # attr_name is not an attribute of FieldInfo, it should therefore be added to extra
                # (except if extra already has this value!)
                self.extra.setdefault(attr_name, value)
            else:
                if current_value is self.__field_constraints__.get(attr_name, None):
                    setattr(self, attr_name, value)
                elif attr_name == 'exclude':
                    self.exclude = ValueItems.merge(value, current_value)
                elif attr_name == 'include':
                    self.include = ValueItems.merge(value, current_value, intersect=True)

    def _validate(self) -> None:
        if self.default is not Undefined and self.default_factory is not None:
            raise ValueError('cannot specify both default and default_factory')


def Field(
    default: Any = Undefined,
    *,
    default_factory: Optional[NoArgAnyCallable] = None,
    alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny', Any]] = None,
    include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny', Any]] = None,
    const: Optional[bool] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
    allow_inf_nan: Optional[bool] = None,
    max_digits: Optional[int] = None,
    decimal_places: Optional[int] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    unique_items: Optional[bool] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    allow_mutation: bool = True,
    regex: Optional[str] = None,
    discriminator: Optional[str] = None,
    repr: bool = True,
    **extra: Any,
) -> Any:
    """
    Used to provide extra information about a field, either for the model schema or complex validation. Some arguments
    apply only to number fields (``int``, ``float``, ``Decimal``) and some apply only to ``str``.

    :param default: since this is replacing the field’s default, its first argument is used
      to set the default, use ellipsis (``...``) to indicate the field is required
    :param default_factory: callable that will be called when a default value is needed for this field
      If both `default` and `default_factory` are set, an error is raised.
    :param alias: the public name of the field
    :param title: can be any string, used in the schema
    :param description: can be any string, used in the schema
    :param exclude: exclude this field while dumping.
      Takes same values as the ``include`` and ``exclude`` arguments on the ``.dict`` method.
    :param include: include this field while dumping.
      Takes same values as the ``include`` and ``exclude`` arguments on the ``.dict`` method.
    :param const: this field is required and *must* take it's default value
    :param gt: only applies to numbers, requires the field to be "greater than". The schema
      will have an ``exclusiveMinimum`` validation keyword
    :param ge: only applies to numbers, requires the field to be "greater than or equal to". The
      schema will have a ``minimum`` validation keyword
    :param lt: only applies to numbers, requires the field to be "less than". The schema
      will have an ``exclusiveMaximum`` validation keyword
    :param le: only applies to numbers, requires the field to be "less than or equal to". The
      schema will have a ``maximum`` validation keyword
    :param multiple_of: only applies to numbers, requires the field to be "a multiple of". The
      schema will have a ``multipleOf`` validation keyword
    :param allow_inf_nan: only applies to numbers, allows the field to be NaN or infinity (+inf or -inf),
        which is a valid Python float. Default True, set to False for compatibility with JSON.
    :param max_digits: only applies to Decimals, requires the field to have a maximum number
      of digits within the decimal. It does not include a zero before the decimal point or trailing decimal zeroes.
    :param decimal_places: only applies to Decimals, requires the field to have at most a number of decimal places
      allowed. It does not include trailing decimal zeroes.
    :param min_items: only applies to lists, requires the field to have a minimum number of
      elements. The schema will have a ``minItems`` validation keyword
    :param max_items: only applies to lists, requires the field to have a maximum number of
      elements. The schema will have a ``maxItems`` validation keyword
    :param unique_items: only applies to lists, requires the field not to have duplicated
      elements. The schema will have a ``uniqueItems`` validation keyword
    :param min_length: only applies to strings, requires the field to have a minimum length. The
      schema will have a ``minLength`` validation keyword
    :param max_length: only applies to strings, requires the field to have a maximum length. The
      schema will have a ``maxLength`` validation keyword
    :param allow_mutation: a boolean which defaults to True. When False, the field raises a TypeError if the field is
      assigned on an instance.  The BaseModel Config must set validate_assignment to True
    :param regex: only applies to strings, requires the field match against a regular expression
      pattern string. The schema will have a ``pattern`` validation keyword
    :param discriminator: only useful with a (discriminated a.k.a. tagged) `Union` of sub models with a common field.
      The `discriminator` is the name of this common field to shorten validation and improve generated schema
    :param repr: show this field in the representation
    :param **extra: any additional keyword arguments will be added as is to the schema
    """
    field_info = FieldInfo(
        default,
        default_factory=default_factory,
        alias=alias,
        title=title,
        description=description,
        exclude=exclude,
        include=include,
        const=const,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        allow_inf_nan=allow_inf_nan,
        max_digits=max_digits,
        decimal_places=decimal_places,
        min_items=min_items,
        max_items=max_items,
        unique_items=unique_items,
        min_length=min_length,
        max_length=max_length,
        allow_mutation=allow_mutation,
        regex=regex,
        discriminator=discriminator,
        repr=repr,
        **extra,
    )
    field_info._validate()
    return field_info


# used to be an enum but changed to int's for small performance improvement as less access overhead
SHAPE_SINGLETON = 1
SHAPE_LIST = 2
SHAPE_SET = 3
SHAPE_MAPPING = 4
SHAPE_TUPLE = 5
SHAPE_TUPLE_ELLIPSIS = 6
SHAPE_SEQUENCE = 7
SHAPE_FROZENSET = 8
SHAPE_ITERABLE = 9
SHAPE_GENERIC = 10
SHAPE_DEQUE = 11
SHAPE_DICT = 12
SHAPE_DEFAULTDICT = 13
SHAPE_COUNTER = 14
SHAPE_NAME_LOOKUP = {
    SHAPE_LIST: 'List[{}]',
    SHAPE_SET: 'Set[{}]',
    SHAPE_TUPLE_ELLIPSIS: 'Tuple[{}, ...]',
    SHAPE_SEQUENCE: 'Sequence[{}]',
    SHAPE_FROZENSET: 'FrozenSet[{}]',
    SHAPE_ITERABLE: 'Iterable[{}]',
    SHAPE_DEQUE: 'Deque[{}]',
    SHAPE_DICT: 'Dict[{}]',
    SHAPE_DEFAULTDICT: 'DefaultDict[{}]',
    SHAPE_COUNTER: 'Counter[{}]',
}

MAPPING_LIKE_SHAPES: Set[int] = {SHAPE_DEFAULTDICT, SHAPE_DICT, SHAPE_MAPPING, SHAPE_COUNTER}


class ModelField(Representation):
    __slots__ = (
        'type_',
        'outer_type_',
        'annotation',
        'sub_fields',
        'sub_fields_mapping',
        'key_field',
        'validators',
        'pre_validators',
        'post_validators',
        'default',
        'default_factory',
        'required',
        'final',
        'model_config',
        'name',
        'alias',
        'has_alias',
        'field_info',
        'discriminator_key',
        'discriminator_alias',
        'validate_always',
        'allow_none',
        'shape',
        'class_validators',
        'parse_json',
    )

    def __init__(
        self,
        *,
        name: str,
        type_: Type[Any],
        class_validators: Optional[Dict[str, Validator]],
        model_config: Type['BaseConfig'],
        default: Any = None,
        default_factory: Optional[NoArgAnyCallable] = None,
        required: 'BoolUndefined' = Undefined,
        final: bool = False,
        alias: Optional[str] = None,
        field_info: Optional[FieldInfo] = None,
    ) -> None:
        self.name: str = name
        self.has_alias: bool = alias is not None
        self.alias: str = alias if alias is not None else name
        self.annotation = type_
        self.type_: Any = convert_generics(type_)
        self.outer_type_: Any = type_
        self.class_validators = class_validators or {}
        self.default: Any = default
        self.default_factory: Optional[NoArgAnyCallable] = default_factory
        self.required: 'BoolUndefined' = required
        self.final: bool = final
        self.model_config = model_config
        self.field_info: FieldInfo = field_info or FieldInfo(default)
        self.discriminator_key: Optional[str] = self.field_info.discriminator
        self.discriminator_alias: Optional[str] = self.discriminator_key

        self.allow_none: bool = False
        self.validate_always: bool = False
        self.sub_fields: Optional[List[ModelField]] = None
        self.sub_fields_mapping: Optional[Dict[str, 'ModelField']] = None  # used for discriminated union
        self.key_field: Optional[ModelField] = None
        self.validators: 'ValidatorsList' = []
        self.pre_validators: Optional['ValidatorsList'] = None
        self.post_validators: Optional['ValidatorsList'] = None
        self.parse_json: bool = False
        self.shape: int = SHAPE_SINGLETON
        self.model_config.prepare_field(self)
        self.prepare()

    def get_default(self) -> Any:
        return smart_deepcopy(self.default) if self.default_factory is None else self.default_factory()

    @staticmethod
    def _get_field_info(
        field_name: str, annotation: Any, value: Any, config: Type['BaseConfig']
    ) -> Tuple[FieldInfo, Any]:
        """
        Get a FieldInfo from a root typing.Annotated annotation, value, or config default.

        The FieldInfo may be set in typing.Annotated or the value, but not both. If neither contain
        a FieldInfo, a new one will be created using the config.

        :param field_name: name of the field for use in error messages
        :param annotation: a type hint such as `str` or `Annotated[str, Field(..., min_length=5)]`
        :param value: the field's assigned value
        :param config: the model's config object
        :return: the FieldInfo contained in the `annotation`, the value, or a new one from the config.
        """
        field_info_from_config = config.get_field_info(field_name)

        field_info = None
        if get_origin(annotation) is Annotated:
            field_infos = [arg for arg in get_args(annotation)[1:] if isinstance(arg, FieldInfo)]
            if len(field_infos) > 1:
                raise ValueError(f'cannot specify multiple `Annotated` `Field`s for {field_name!r}')
            field_info = next(iter(field_infos), None)
            if field_info is not None:
                field_info = copy.copy(field_info)
                field_info.update_from_config(field_info_from_config)
                if field_info.default not in (Undefined, Required):
                    raise ValueError(f'`Field` default cannot be set in `Annotated` for {field_name!r}')
                if value is not Undefined and value is not Required:
                    # check also `Required` because of `validate_arguments` that sets `...` as default value
                    field_info.default = value

        if isinstance(value, FieldInfo):
            if field_info is not None:
                raise ValueError(f'cannot specify `Annotated` and value `Field`s together for {field_name!r}')
            field_info = value
            field_info.update_from_config(field_info_from_config)
        elif field_info is None:
            field_info = FieldInfo(value, **field_info_from_config)
        value = None if field_info.default_factory is not None else field_info.default
        field_info._validate()
        return field_info, value

    @classmethod
    def infer(
        cls,
        *,
        name: str,
        value: Any,
        annotation: Any,
        class_validators: Optional[Dict[str, Validator]],
        config: Type['BaseConfig'],
    ) -> 'ModelField':
        from pydantic.v1.schema import get_annotation_from_field_info

        field_info, value = cls._get_field_info(name, annotation, value, config)
        required: 'BoolUndefined' = Undefined
        if value is Required:
            required = True
            value = None
        elif value is not Undefined:
            required = False
        annotation = get_annotation_from_field_info(annotation, field_info, name, config.validate_assignment)

        return cls(
            name=name,
            type_=annotation,
            alias=field_info.alias,
            class_validators=class_validators,
            default=value,
            default_factory=field_info.default_factory,
            required=required,
            model_config=config,
            field_info=field_info,
        )

    def set_config(self, config: Type['BaseConfig']) -> None:
        self.model_config = config
        info_from_config = config.get_field_info(self.name)
        config.prepare_field(self)
        new_alias = info_from_config.get('alias')
        new_alias_priority = info_from_config.get('alias_priority') or 0
        if new_alias and new_alias_priority >= (self.field_info.alias_priority or 0):
            self.field_info.alias = new_alias
            self.field_info.alias_priority = new_alias_priority
            self.alias = new_alias
        new_exclude = info_from_config.get('exclude')
        if new_exclude is not None:
            self.field_info.exclude = ValueItems.merge(self.field_info.exclude, new_exclude)
        new_include = info_from_config.get('include')
        if new_include is not None:
            self.field_info.include = ValueItems.merge(self.field_info.include, new_include, intersect=True)

    @property
    def alt_alias(self) -> bool:
        return self.name != self.alias

    def prepare(self) -> None:
        """
        Prepare the field but inspecting self.default, self.type_ etc.

        Note: this method is **not** idempotent (because _type_analysis is not idempotent),
        e.g. calling it it multiple times may modify the field and configure it incorrectly.
        """
        self._set_default_and_type()
        if self.type_.__class__ is ForwardRef or self.type_.__class__ is DeferredType:
            # self.type_ is currently a ForwardRef and there's nothing we can do now,
            # user will need to call model.update_forward_refs()
            return

        self._type_analysis()
        if self.required is Undefined:
            self.required = True
        if self.default is Undefined and self.default_factory is None:
            self.default = None
        self.populate_validators()

    def _set_default_and_type(self) -> None:
        """
        Set the default value, infer the type if needed and check if `None` value is valid.
        """
        if self.default_factory is not None:
            if self.type_ is Undefined:
                raise errors_.ConfigError(
                    f'you need to set the type of field {self.name!r} when using `default_factory`'
                )
            return

        default_value = self.get_default()

        if default_value is not None and self.type_ is Undefined:
            self.type_ = default_value.__class__
            self.outer_type_ = self.type_
            self.annotation = self.type_

        if self.type_ is Undefined:
            raise errors_.ConfigError(f'unable to infer type for attribute "{self.name}"')

        if self.required is False and default_value is None:
            self.allow_none = True

    def _type_analysis(self) -> None:  # noqa: C901 (ignore complexity)
        # typing interface is horrible, we have to do some ugly checks
        if lenient_issubclass(self.type_, JsonWrapper):
            self.type_ = self.type_.inner_type
            self.parse_json = True
        elif lenient_issubclass(self.type_, Json):
            self.type_ = Any
            self.parse_json = True
        elif isinstance(self.type_, TypeVar):
            if self.type_.__bound__:
                self.type_ = self.type_.__bound__
            elif self.type_.__constraints__:
                self.type_ = Union[self.type_.__constraints__]
            else:
                self.type_ = Any
        elif is_new_type(self.type_):
            self.type_ = new_type_supertype(self.type_)

        if self.type_ is Any or self.type_ is object:
            if self.required is Undefined:
                self.required = False
            self.allow_none = True
            return
        elif self.type_ is Pattern or self.type_ is re.Pattern:
            # python 3.7 only, Pattern is a typing object but without sub fields
            return
        elif is_literal_type(self.type_):
            return
        elif is_typeddict(self.type_):
            return

        if is_finalvar(self.type_):
            self.final = True

            if self.type_ is Final:
                self.type_ = Any
            else:
                self.type_ = get_args(self.type_)[0]

            self._type_analysis()
            return

        origin = get_origin(self.type_)

        if origin is Annotated or is_typeddict_special(origin):
            self.type_ = get_args(self.type_)[0]
            self._type_analysis()
            return

        if self.discriminator_key is not None and not is_union(origin):
            raise TypeError('`discriminator` can only be used with `Union` type with more than one variant')

        # add extra check for `collections.abc.Hashable` for python 3.10+ where origin is not `None`
        if origin is None or origin is CollectionsHashable:
            # field is not "typing" object eg. Union, Dict, List etc.
            # allow None for virtual superclasses of NoneType, e.g. Hashable
            if isinstance(self.type_, type) and isinstance(None, self.type_):
                self.allow_none = True
            return
        elif origin is Callable:
            return
        elif is_union(origin):
            types_ = []
            for type_ in get_args(self.type_):
                if is_none_type(type_) or type_ is Any or type_ is object:
                    if self.required is Undefined:
                        self.required = False
                    self.allow_none = True
                if is_none_type(type_):
                    continue
                types_.append(type_)

            if len(types_) == 1:
                # Optional[]
                self.type_ = types_[0]
                # this is the one case where the "outer type" isn't just the original type
                self.outer_type_ = self.type_
                # re-run to correctly interpret the new self.type_
                self._type_analysis()
            else:
                self.sub_fields = [self._create_sub_type(t, f'{self.name}_{display_as_type(t)}') for t in types_]

                if self.discriminator_key is not None:
                    self.prepare_discriminated_union_sub_fields()
            return
        elif issubclass(origin, Tuple):  # type: ignore
            # origin == Tuple without item type
            args = get_args(self.type_)
            if not args:  # plain tuple
                self.type_ = Any
                self.shape = SHAPE_TUPLE_ELLIPSIS
            elif len(args) == 2 and args[1] is Ellipsis:  # e.g. Tuple[int, ...]
                self.type_ = args[0]
                self.shape = SHAPE_TUPLE_ELLIPSIS
                self.sub_fields = [self._create_sub_type(args[0], f'{self.name}_0')]
            elif args == ((),):  # Tuple[()] means empty tuple
                self.shape = SHAPE_TUPLE
                self.type_ = Any
                self.sub_fields = []
            else:
                self.shape = SHAPE_TUPLE
                self.sub_fields = [self._create_sub_type(t, f'{self.name}_{i}') for i, t in enumerate(args)]
            return
        elif issubclass(origin, List):
            # Create self validators
            get_validators = getattr(self.type_, '__get_validators__', None)
            if get_validators:
                self.class_validators.update(
                    {f'list_{i}': Validator(validator, pre=True) for i, validator in enumerate(get_validators())}
                )

            self.type_ = get_args(self.type_)[0]
            self.shape = SHAPE_LIST
        elif issubclass(origin, Set):
            # Create self validators
            get_validators = getattr(self.type_, '__get_validators__', None)
            if get_validators:
                self.class_validators.update(
                    {f'set_{i}': Validator(validator, pre=True) for i, validator in enumerate(get_validators())}
                )

            self.type_ = get_args(self.type_)[0]
            self.shape = SHAPE_SET
        elif issubclass(origin, FrozenSet):
            # Create self validators
            get_validators = getattr(self.type_, '__get_validators__', None)
            if get_validators:
                self.class_validators.update(
                    {f'frozenset_{i}': Validator(validator, pre=True) for i, validator in enumerate(get_validators())}
                )

            self.type_ = get_args(self.type_)[0]
            self.shape = SHAPE_FROZENSET
        elif issubclass(origin, Deque):
            self.type_ = get_args(self.type_)[0]
            self.shape = SHAPE_DEQUE
        elif issubclass(origin, Sequence):
            self.type_ = get_args(self.type_)[0]
            self.shape = SHAPE_SEQUENCE
        # priority to most common mapping: dict
        elif origin is dict or origin is Dict:
            self.key_field = self._create_sub_type(get_args(self.type_)[0], 'key_' + self.name, for_keys=True)
            self.type_ = get_args(self.type_)[1]
            self.shape = SHAPE_DICT
        elif issubclass(origin, DefaultDict):
            self.key_field = self._create_sub_type(get_args(self.type_)[0], 'key_' + self.name, for_keys=True)
            self.type_ = get_args(self.type_)[1]
            self.shape = SHAPE_DEFAULTDICT
        elif issubclass(origin, Counter):
            self.key_field = self._create_sub_type(get_args(self.type_)[0], 'key_' + self.name, for_keys=True)
            self.type_ = int
            self.shape = SHAPE_COUNTER
        elif issubclass(origin, Mapping):
            self.key_field = self._create_sub_type(get_args(self.type_)[0], 'key_' + self.name, for_keys=True)
            self.type_ = get_args(self.type_)[1]
            self.shape = SHAPE_MAPPING
        # Equality check as almost everything inherits form Iterable, including str
        # check for Iterable and CollectionsIterable, as it could receive one even when declared with the other
        elif origin in {Iterable, CollectionsIterable}:
            self.type_ = get_args(self.type_)[0]
            self.shape = SHAPE_ITERABLE
            self.sub_fields = [self._create_sub_type(self.type_, f'{self.name}_type')]
        elif issubclass(origin, Type):  # type: ignore
            return
        elif hasattr(origin, '__get_validators__') or self.model_config.arbitrary_types_allowed:
            # Is a Pydantic-compatible generic that handles itself
            # or we have arbitrary_types_allowed = True
            self.shape = SHAPE_GENERIC
            self.sub_fields = [self._create_sub_type(t, f'{self.name}_{i}') for i, t in enumerate(get_args(self.type_))]
            self.type_ = origin
            return
        else:
            raise TypeError(f'Fields of type "{origin}" are not supported.')

        # type_ has been refined eg. as the type of a List and sub_fields needs to be populated
        self.sub_fields = [self._create_sub_type(self.type_, '_' + self.name)]

    def prepare_discriminated_union_sub_fields(self) -> None:
        """
        Prepare the mapping <discriminator key> -> <ModelField> and update `sub_fields`
        Note that this process can be aborted if a `ForwardRef` is encountered
        """
        assert self.discriminator_key is not None

        if self.type_.__class__ is DeferredType:
            return

        assert self.sub_fields is not None
        sub_fields_mapping: Dict[str, 'ModelField'] = {}
        all_aliases: Set[str] = set()

        for sub_field in self.sub_fields:
            t = sub_field.type_
            if t.__class__ is ForwardRef:
                # Stopping everything...will need to call `update_forward_refs`
                return

            alias, discriminator_values = get_discriminator_alias_and_values(t, self.discriminator_key)
            all_aliases.add(alias)
            for discriminator_value in discriminator_values:
                sub_fields_mapping[discriminator_value] = sub_field

        self.sub_fields_mapping = sub_fields_mapping
        self.discriminator_alias = get_unique_discriminator_alias(all_aliases, self.discriminator_key)

    def _create_sub_type(self, type_: Type[Any], name: str, *, for_keys: bool = False) -> 'ModelField':
        if for_keys:
            class_validators = None
        else:
            # validators for sub items should not have `each_item` as we want to check only the first sublevel
            class_validators = {
                k: Validator(
                    func=v.func,
                    pre=v.pre,
                    each_item=False,
                    always=v.always,
                    check_fields=v.check_fields,
                    skip_on_failure=v.skip_on_failure,
                )
                for k, v in self.class_validators.items()
                if v.each_item
            }

        field_info, _ = self._get_field_info(name, type_, None, self.model_config)

        return self.__class__(
            type_=type_,
            name=name,
            class_validators=class_validators,
            model_config=self.model_config,
            field_info=field_info,
        )

    def populate_validators(self) -> None:
        """
        Prepare self.pre_validators, self.validators, and self.post_validators based on self.type_'s  __get_validators__
        and class validators. This method should be idempotent, e.g. it should be safe to call multiple times
        without mis-configuring the field.
        """
        self.validate_always = getattr(self.type_, 'validate_always', False) or any(
            v.always for v in self.class_validators.values()
        )

        class_validators_ = self.class_validators.values()
        if not self.sub_fields or self.shape == SHAPE_GENERIC:
            get_validators = getattr(self.type_, '__get_validators__', None)
            v_funcs = (
                *[v.func for v in class_validators_ if v.each_item and v.pre],
                *(get_validators() if get_validators else list(find_validators(self.type_, self.model_config))),
                *[v.func for v in class_validators_ if v.each_item and not v.pre],
            )
            self.validators = prep_validators(v_funcs)

        self.pre_validators = []
        self.post_validators = []

        if self.field_info and self.field_info.const:
            self.post_validators.append(make_generic_validator(constant_validator))

        if class_validators_:
            self.pre_validators += prep_validators(v.func for v in class_validators_ if not v.each_item and v.pre)
            self.post_validators += prep_validators(v.func for v in class_validators_ if not v.each_item and not v.pre)

        if self.parse_json:
            self.pre_validators.append(make_generic_validator(validate_json))

        self.pre_validators = self.pre_validators or None
        self.post_validators = self.post_validators or None

    def validate(
        self, v: Any, values: Dict[str, Any], *, loc: 'LocStr', cls: Optional['ModelOrDc'] = None
    ) -> 'ValidateReturn':
        assert self.type_.__class__ is not DeferredType

        if self.type_.__class__ is ForwardRef:
            assert cls is not None
            raise ConfigError(
                f'field "{self.name}" not yet prepared so type is still a ForwardRef, '
                f'you might need to call {cls.__name__}.update_forward_refs().'
            )

        errors: Optional['ErrorList']
        if self.pre_validators:
            v, errors = self._apply_validators(v, values, loc, cls, self.pre_validators)
            if errors:
                return v, errors

        if v is None:
            if is_none_type(self.type_):
                # keep validating
                pass
            elif self.allow_none:
                if self.post_validators:
                    return self._apply_validators(v, values, loc, cls, self.post_validators)
                else:
                    return None, None
            else:
                return v, ErrorWrapper(NoneIsNotAllowedError(), loc)

        if self.shape == SHAPE_SINGLETON:
            v, errors = self._validate_singleton(v, values, loc, cls)
        elif self.shape in MAPPING_LIKE_SHAPES:
            v, errors = self._validate_mapping_like(v, values, loc, cls)
        elif self.shape == SHAPE_TUPLE:
            v, errors = self._validate_tuple(v, values, loc, cls)
        elif self.shape == SHAPE_ITERABLE:
            v, errors = self._validate_iterable(v, values, loc, cls)
        elif self.shape == SHAPE_GENERIC:
            v, errors = self._apply_validators(v, values, loc, cls, self.validators)
        else:
            #  sequence, list, set, generator, tuple with ellipsis, frozen set
            v, errors = self._validate_sequence_like(v, values, loc, cls)

        if not errors and self.post_validators:
            v, errors = self._apply_validators(v, values, loc, cls, self.post_validators)
        return v, errors

    def _validate_sequence_like(  # noqa: C901 (ignore complexity)
        self, v: Any, values: Dict[str, Any], loc: 'LocStr', cls: Optional['ModelOrDc']
    ) -> 'ValidateReturn':
        """
        Validate sequence-like containers: lists, tuples, sets and generators
        Note that large if-else blocks are necessary to enable Cython
        optimization, which is why we disable the complexity check above.
        """
        if not sequence_like(v):
            e: errors_.PydanticTypeError
            if self.shape == SHAPE_LIST:
                e = errors_.ListError()
            elif self.shape in (SHAPE_TUPLE, SHAPE_TUPLE_ELLIPSIS):
                e = errors_.TupleError()
            elif self.shape == SHAPE_SET:
                e = errors_.SetError()
            elif self.shape == SHAPE_FROZENSET:
                e = errors_.FrozenSetError()
            else:
                e = errors_.SequenceError()
            return v, ErrorWrapper(e, loc)

        loc = loc if isinstance(loc, tuple) else (loc,)
        result = []
        errors: List[ErrorList] = []
        for i, v_ in enumerate(v):
            v_loc = *loc, i
            r, ee = self._validate_singleton(v_, values, v_loc, cls)
            if ee:
                errors.append(ee)
            else:
                result.append(r)

        if errors:
            return v, errors

        converted: Union[List[Any], Set[Any], FrozenSet[Any], Tuple[Any, ...], Iterator[Any], Deque[Any]] = result

        if self.shape == SHAPE_SET:
            converted = set(result)
        elif self.shape == SHAPE_FROZENSET:
            converted = frozenset(result)
        elif self.shape == SHAPE_TUPLE_ELLIPSIS:
            converted = tuple(result)
        elif self.shape == SHAPE_DEQUE:
            converted = deque(result, maxlen=getattr(v, 'maxlen', None))
        elif self.shape == SHAPE_SEQUENCE:
            if isinstance(v, tuple):
                converted = tuple(result)
            elif isinstance(v, set):
                converted = set(result)
            elif isinstance(v, Generator):
                converted = iter(result)
            elif isinstance(v, deque):
                converted = deque(result, maxlen=getattr(v, 'maxlen', None))
        return converted, None

    def _validate_iterable(
        self, v: Any, values: Dict[str, Any], loc: 'LocStr', cls: Optional['ModelOrDc']
    ) -> 'ValidateReturn':
        """
        Validate Iterables.

        This intentionally doesn't validate values to allow infinite generators.
        """

        try:
            iterable = iter(v)
        except TypeError:
            return v, ErrorWrapper(errors_.IterableError(), loc)
        return iterable, None

    def _validate_tuple(
        self, v: Any, values: Dict[str, Any], loc: 'LocStr', cls: Optional['ModelOrDc']
    ) -> 'ValidateReturn':
        e: Optional[Exception] = None
        if not sequence_like(v):
            e = errors_.TupleError()
        else:
            actual_length, expected_length = len(v), len(self.sub_fields)  # type: ignore
            if actual_length != expected_length:
                e = errors_.TupleLengthError(actual_length=actual_length, expected_length=expected_length)

        if e:
            return v, ErrorWrapper(e, loc)

        loc = loc if isinstance(loc, tuple) else (loc,)
        result = []
        errors: List[ErrorList] = []
        for i, (v_, field) in enumerate(zip(v, self.sub_fields)):  # type: ignore
            v_loc = *loc, i
            r, ee = field.validate(v_, values, loc=v_loc, cls=cls)
            if ee:
                errors.append(ee)
            else:
                result.append(r)

        if errors:
            return v, errors
        else:
            return tuple(result), None

    def _validate_mapping_like(
        self, v: Any, values: Dict[str, Any], loc: 'LocStr', cls: Optional['ModelOrDc']
    ) -> 'ValidateReturn':
        try:
            v_iter = dict_validator(v)
        except TypeError as exc:
            return v, ErrorWrapper(exc, loc)

        loc = loc if isinstance(loc, tuple) else (loc,)
        result, errors = {}, []
        for k, v_ in v_iter.items():
            v_loc = *loc, '__key__'
            key_result, key_errors = self.key_field.validate(k, values, loc=v_loc, cls=cls)  # type: ignore
            if key_errors:
                errors.append(key_errors)
                continue

            v_loc = *loc, k
            value_result, value_errors = self._validate_singleton(v_, values, v_loc, cls)
            if value_errors:
                errors.append(value_errors)
                continue

            result[key_result] = value_result
        if errors:
            return v, errors
        elif self.shape == SHAPE_DICT:
            return result, None
        elif self.shape == SHAPE_DEFAULTDICT:
            return defaultdict(self.type_, result), None
        elif self.shape == SHAPE_COUNTER:
            return CollectionCounter(result), None
        else:
            return self._get_mapping_value(v, result), None

    def _get_mapping_value(self, original: T, converted: Dict[Any, Any]) -> Union[T, Dict[Any, Any]]:
        """
        When type is `Mapping[KT, KV]` (or another unsupported mapping), we try to avoid
        coercing to `dict` unwillingly.
        """
        original_cls = original.__class__

        if original_cls == dict or original_cls == Dict:
            return converted
        elif original_cls in {defaultdict, DefaultDict}:
            return defaultdict(self.type_, converted)
        else:
            try:
                # Counter, OrderedDict, UserDict, ...
                return original_cls(converted)  # type: ignore
            except TypeError:
                raise RuntimeError(f'Could not convert dictionary to {original_cls.__name__!r}') from None

    def _validate_singleton(
        self, v: Any, values: Dict[str, Any], loc: 'LocStr', cls: Optional['ModelOrDc']
    ) -> 'ValidateReturn':
        if self.sub_fields:
            if self.discriminator_key is not None:
                return self._validate_discriminated_union(v, values, loc, cls)

            errors = []

            if self.model_config.smart_union and is_union(get_origin(self.type_)):
                # 1st pass: check if the value is an exact instance of one of the Union types
                # (e.g. to avoid coercing a bool into an int)
                for field in self.sub_fields:
                    if v.__class__ is field.outer_type_:
                        return v, None

                # 2nd pass: check if the value is an instance of any subclass of the Union types
                for field in self.sub_fields:
                    # This whole logic will be improved later on to support more complex `isinstance` checks
                    # It will probably be done once a strict mode is added and be something like:
                    # ```
                    #     value, error = field.validate(v, values, strict=True)
                    #     if error is None:
                    #         return value, None
                    # ```
                    try:
                        if isinstance(v, field.outer_type_):
                            return v, None
                    except TypeError:
                        # compound type
                        if lenient_isinstance(v, get_origin(field.outer_type_)):
                            value, error = field.validate(v, values, loc=loc, cls=cls)
                            if not error:
                                return value, None

            # 1st pass by default or 3rd pass with `smart_union` enabled:
            # check if the value can be coerced into one of the Union types
            for field in self.sub_fields:
                value, error = field.validate(v, values, loc=loc, cls=cls)
                if error:
                    errors.append(error)
                else:
                    return value, None
            return v, errors
        else:
            return self._apply_validators(v, values, loc, cls, self.validators)

    def _validate_discriminated_union(
        self, v: Any, values: Dict[str, Any], loc: 'LocStr', cls: Optional['ModelOrDc']
    ) -> 'ValidateReturn':
        assert self.discriminator_key is not None
        assert self.discriminator_alias is not None

        try:
            try:
                discriminator_value = v[self.discriminator_alias]
            except KeyError:
                if self.model_config.allow_population_by_field_name:
                    discriminator_value = v[self.discriminator_key]
                else:
                    raise
        except KeyError:
            return v, ErrorWrapper(MissingDiscriminator(discriminator_key=self.discriminator_key), loc)
        except TypeError:
            try:
                # BaseModel or dataclass
                discriminator_value = getattr(v, self.discriminator_key)
            except (AttributeError, TypeError):
                return v, ErrorWrapper(MissingDiscriminator(discriminator_key=self.discriminator_key), loc)

        if self.sub_fields_mapping is None:
            assert cls is not None
            raise ConfigError(
                f'field "{self.name}" not yet prepared so type is still a ForwardRef, '
                f'you might need to call {cls.__name__}.update_forward_refs().'
            )

        try:
            sub_field = self.sub_fields_mapping[discriminator_value]
        except (KeyError, TypeError):
            # KeyError: `discriminator_value` is not in the dictionary.
            # TypeError: `discriminator_value` is unhashable.
            assert self.sub_fields_mapping is not None
            return v, ErrorWrapper(
                InvalidDiscriminator(
                    discriminator_key=self.discriminator_key,
                    discriminator_value=discriminator_value,
                    allowed_values=list(self.sub_fields_mapping),
                ),
                loc,
            )
        else:
            if not isinstance(loc, tuple):
                loc = (loc,)
            return sub_field.validate(v, values, loc=(*loc, display_as_type(sub_field.type_)), cls=cls)

    def _apply_validators(
        self, v: Any, values: Dict[str, Any], loc: 'LocStr', cls: Optional['ModelOrDc'], validators: 'ValidatorsList'
    ) -> 'ValidateReturn':
        for validator in validators:
            try:
                v = validator(cls, v, values, self, self.model_config)
            except (ValueError, TypeError, AssertionError) as exc:
                return v, ErrorWrapper(exc, loc)
        return v, None

    def is_complex(self) -> bool:
        """
        Whether the field is "complex" eg. env variables should be parsed as JSON.
        """
        from pydantic.v1.main import BaseModel

        return (
            self.shape != SHAPE_SINGLETON
            or hasattr(self.type_, '__pydantic_model__')
            or lenient_issubclass(self.type_, (BaseModel, list, set, frozenset, dict))
        )

    def _type_display(self) -> PyObjectStr:
        t = display_as_type(self.type_)

        if self.shape in MAPPING_LIKE_SHAPES:
            t = f'Mapping[{display_as_type(self.key_field.type_)}, {t}]'  # type: ignore
        elif self.shape == SHAPE_TUPLE:
            t = 'Tuple[{}]'.format(', '.join(display_as_type(f.type_) for f in self.sub_fields))  # type: ignore
        elif self.shape == SHAPE_GENERIC:
            assert self.sub_fields
            t = '{}[{}]'.format(
                display_as_type(self.type_), ', '.join(display_as_type(f.type_) for f in self.sub_fields)
            )
        elif self.shape != SHAPE_SINGLETON:
            t = SHAPE_NAME_LOOKUP[self.shape].format(t)

        if self.allow_none and (self.shape != SHAPE_SINGLETON or not self.sub_fields):
            t = f'Optional[{t}]'
        return PyObjectStr(t)

    def __repr_args__(self) -> 'ReprArgs':
        args = [('name', self.name), ('type', self._type_display()), ('required', self.required)]

        if not self.required:
            if self.default_factory is not None:
                args.append(('default_factory', f'<function {self.default_factory.__name__}>'))
            else:
                args.append(('default', self.default))

        if self.alt_alias:
            args.append(('alias', self.alias))
        return args


class ModelPrivateAttr(Representation):
    __slots__ = ('default', 'default_factory')

    def __init__(self, default: Any = Undefined, *, default_factory: Optional[NoArgAnyCallable] = None) -> None:
        self.default = default
        self.default_factory = default_factory

    def get_default(self) -> Any:
        return smart_deepcopy(self.default) if self.default_factory is None else self.default_factory()

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and (self.default, self.default_factory) == (
            other.default,
            other.default_factory,
        )


def PrivateAttr(
    default: Any = Undefined,
    *,
    default_factory: Optional[NoArgAnyCallable] = None,
) -> Any:
    """
    Indicates that attribute is only used internally and never mixed with regular fields.

    Types or values of private attrs are not checked by pydantic and it's up to you to keep them relevant.

    Private attrs are stored in model __slots__.

    :param default: the attribute’s default value
    :param default_factory: callable that will be called when a default value is needed for this attribute
      If both `default` and `default_factory` are set, an error is raised.
    """
    if default is not Undefined and default_factory is not None:
        raise ValueError('cannot specify both default and default_factory')

    return ModelPrivateAttr(
        default,
        default_factory=default_factory,
    )


class DeferredType:
    """
    Used to postpone field preparation, while creating recursive generic models.
    """


def is_finalvar_with_default_val(type_: Type[Any], val: Any) -> bool:
    return is_finalvar(type_) and val is not Undefined and not isinstance(val, FieldInfo)

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_socket.py ===
from __future__ import annotations

import errno
import inspect
import os
import socket as stdlib_socket
import sys
import tempfile
from pathlib import Path
from socket import AddressFamily, SocketKind
from typing import TYPE_CHECKING, Union, cast

import attrs
import pytest

from .. import _core, socket as tsocket
from .._core._tests.tutil import binds_ipv6, can_create_ipv6, creates_ipv6, slow
from .._socket import _NUMERIC_ONLY, AddressFormat, SocketType, _SocketType, _try_sync
from ..testing import assert_checkpoints, wait_all_tasks_blocked

if TYPE_CHECKING:
    from collections.abc import Callable

    from typing_extensions import TypeAlias

    from .._highlevel_socket import SocketStream

    GaiTuple: TypeAlias = tuple[
        AddressFamily,
        SocketKind,
        int,
        str,
        Union[tuple[str, int], tuple[str, int, int, int], tuple[int, bytes]],
    ]
    GetAddrInfoResponse: TypeAlias = list[GaiTuple]
    GetAddrInfoArgs: TypeAlias = tuple[
        Union[str, bytes, None],
        Union[str, bytes, int, None],
        int,
        int,
        int,
        int,
    ]
else:
    GaiTuple: object
    GetAddrInfoResponse = object
    GetAddrInfoArgs = object

################################################################
# utils
################################################################


class MonkeypatchedGAI:
    __slots__ = ("_orig_getaddrinfo", "_responses", "record")

    def __init__(
        self,
        orig_getaddrinfo: Callable[
            [str | bytes | None, str | bytes | int | None, int, int, int, int],
            GetAddrInfoResponse,
        ],
    ) -> None:
        self._orig_getaddrinfo = orig_getaddrinfo
        self._responses: dict[
            GetAddrInfoArgs,
            GetAddrInfoResponse | str,
        ] = {}
        self.record: list[GetAddrInfoArgs] = []

    # get a normalized getaddrinfo argument tuple
    def _frozenbind(
        self,
        host: str | bytes | None,
        port: str | bytes | int | None,
        family: int = 0,
        type: int = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> GetAddrInfoArgs:
        sig = inspect.signature(self._orig_getaddrinfo)
        bound = sig.bind(host, port, family=family, type=type, proto=proto, flags=flags)
        bound.apply_defaults()
        frozenbound = bound.args
        assert not bound.kwargs
        return frozenbound

    def set(
        self,
        response: GetAddrInfoResponse | str,
        host: str | bytes | None,
        port: str | bytes | int | None,
        family: int = 0,
        type: int = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> None:
        self._responses[
            self._frozenbind(
                host,
                port,
                family=family,
                type=type,
                proto=proto,
                flags=flags,
            )
        ] = response

    def getaddrinfo(
        self,
        host: str | bytes | None,
        port: str | bytes | int | None,
        family: int = 0,
        type: int = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> GetAddrInfoResponse | str:
        bound = self._frozenbind(host, port, family, type, proto, flags)
        self.record.append(bound)
        if bound in self._responses:
            return self._responses[bound]
        elif flags & stdlib_socket.AI_NUMERICHOST:
            return self._orig_getaddrinfo(host, port, family, type, proto, flags)
        else:
            raise RuntimeError(f"gai called with unexpected arguments {bound}")


@pytest.fixture
def monkeygai(monkeypatch: pytest.MonkeyPatch) -> MonkeypatchedGAI:
    controller = MonkeypatchedGAI(stdlib_socket.getaddrinfo)
    monkeypatch.setattr(stdlib_socket, "getaddrinfo", controller.getaddrinfo)
    return controller


async def test__try_sync() -> None:
    with assert_checkpoints():
        async with _try_sync():
            pass

    with assert_checkpoints():
        with pytest.raises(KeyError):
            async with _try_sync():
                raise KeyError

    async with _try_sync():
        raise BlockingIOError

    def _is_ValueError(exc: BaseException) -> bool:
        return isinstance(exc, ValueError)

    async with _try_sync(_is_ValueError):
        raise ValueError

    with assert_checkpoints():
        with pytest.raises(BlockingIOError):
            async with _try_sync(_is_ValueError):
                raise BlockingIOError


################################################################
# basic re-exports
################################################################


def test_socket_has_some_reexports() -> None:
    assert tsocket.SOL_SOCKET == stdlib_socket.SOL_SOCKET
    assert tsocket.TCP_NODELAY == stdlib_socket.TCP_NODELAY
    assert tsocket.gaierror == stdlib_socket.gaierror
    assert tsocket.ntohs == stdlib_socket.ntohs


################################################################
# name resolution
################################################################


async def test_getaddrinfo(monkeygai: MonkeypatchedGAI) -> None:
    def check(got: GetAddrInfoResponse, expected: GetAddrInfoResponse) -> None:
        # win32 returns 0 for the proto field
        # musl and glibc have inconsistent handling of the canonical name
        # field (https://github.com/python-trio/trio/issues/1499)
        # Neither field gets used much and there isn't much opportunity for us
        # to mess them up, so we don't bother checking them here
        def interesting_fields(
            gai_tup: GaiTuple,
        ) -> tuple[
            AddressFamily,
            SocketKind,
            tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes],
        ]:
            # (family, type, proto, canonname, sockaddr)
            family, type_, _proto, _canonname, sockaddr = gai_tup
            return (family, type_, sockaddr)

        def filtered(
            gai_list: GetAddrInfoResponse,
        ) -> list[
            tuple[
                AddressFamily,
                SocketKind,
                tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes],
            ]
        ]:
            return [interesting_fields(gai_tup) for gai_tup in gai_list]

        assert filtered(got) == filtered(expected)

    # Simple non-blocking non-error cases, ipv4 and ipv6:
    with assert_checkpoints():
        res = await tsocket.getaddrinfo("127.0.0.1", "12345", type=tsocket.SOCK_STREAM)

    check(
        res,
        [
            (
                tsocket.AF_INET,  # 127.0.0.1 is ipv4
                tsocket.SOCK_STREAM,
                tsocket.IPPROTO_TCP,
                "",
                ("127.0.0.1", 12345),
            ),
        ],
    )

    with assert_checkpoints():
        res = await tsocket.getaddrinfo("::1", "12345", type=tsocket.SOCK_DGRAM)
    check(
        res,
        [
            (
                tsocket.AF_INET6,
                tsocket.SOCK_DGRAM,
                tsocket.IPPROTO_UDP,
                "",
                ("::1", 12345, 0, 0),
            ),
        ],
    )

    monkeygai.set("x", b"host", "port", family=0, type=0, proto=0, flags=0)
    with assert_checkpoints():
        res = await tsocket.getaddrinfo("host", "port")
    assert res == "x"
    assert monkeygai.record[-1] == (b"host", "port", 0, 0, 0, 0)

    # check raising an error from a non-blocking getaddrinfo
    with assert_checkpoints():
        with pytest.raises(tsocket.gaierror) as excinfo:
            await tsocket.getaddrinfo("::1", "12345", type=-1)
    # Linux + glibc, Windows
    expected_errnos = {tsocket.EAI_SOCKTYPE}
    # Linux + musl
    expected_errnos.add(tsocket.EAI_SERVICE)
    # macOS
    if hasattr(tsocket, "EAI_BADHINTS"):
        expected_errnos.add(tsocket.EAI_BADHINTS)
    assert excinfo.value.errno in expected_errnos

    # check raising an error from a blocking getaddrinfo (exploits the fact
    # that monkeygai raises if it gets a non-numeric request it hasn't been
    # given an answer for)
    with assert_checkpoints():
        with pytest.raises(RuntimeError):
            await tsocket.getaddrinfo("asdf", "12345")


async def test_getnameinfo() -> None:
    # Trivial test:
    ni_numeric = stdlib_socket.NI_NUMERICHOST | stdlib_socket.NI_NUMERICSERV
    with assert_checkpoints():
        got = await tsocket.getnameinfo(("127.0.0.1", 1234), ni_numeric)
    assert got == ("127.0.0.1", "1234")

    # getnameinfo requires a numeric address as input:
    with assert_checkpoints():
        with pytest.raises(tsocket.gaierror):
            await tsocket.getnameinfo(("google.com", 80), 0)

    with assert_checkpoints():
        with pytest.raises(tsocket.gaierror):
            await tsocket.getnameinfo(("localhost", 80), 0)

    # Blocking call to get expected values:
    host, service = stdlib_socket.getnameinfo(("127.0.0.1", 80), 0)

    # Some working calls:
    got = await tsocket.getnameinfo(("127.0.0.1", 80), 0)
    assert got == (host, service)

    got = await tsocket.getnameinfo(("127.0.0.1", 80), tsocket.NI_NUMERICHOST)
    assert got == ("127.0.0.1", service)

    got = await tsocket.getnameinfo(("127.0.0.1", 80), tsocket.NI_NUMERICSERV)
    assert got == (host, "80")


################################################################
# constructors
################################################################


async def test_from_stdlib_socket() -> None:
    sa, sb = stdlib_socket.socketpair()
    assert not isinstance(sa, tsocket.SocketType)
    with sa, sb:
        ta = tsocket.from_stdlib_socket(sa)
        assert isinstance(ta, tsocket.SocketType)
        assert sa.fileno() == ta.fileno()
        await ta.send(b"x")
        assert sb.recv(1) == b"x"

    # rejects other types
    with pytest.raises(TypeError):
        tsocket.from_stdlib_socket(1)  # type: ignore[arg-type]

    class MySocket(stdlib_socket.socket):
        pass

    with MySocket() as mysock:
        with pytest.raises(TypeError):
            tsocket.from_stdlib_socket(mysock)


async def test_from_fd() -> None:
    sa, sb = stdlib_socket.socketpair()
    ta = tsocket.fromfd(sa.fileno(), sa.family, sa.type, sa.proto)
    with sa, sb, ta:
        assert ta.fileno() != sa.fileno()
        await ta.send(b"x")
        assert sb.recv(3) == b"x"


async def test_socketpair_simple() -> None:
    async def child(sock: SocketType) -> None:
        print("sending hello")
        await sock.send(b"h")
        assert await sock.recv(1) == b"h"

    a, b = tsocket.socketpair()
    with a, b:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(child, a)
            nursery.start_soon(child, b)


@pytest.mark.skipif(not hasattr(tsocket, "fromshare"), reason="windows only")
async def test_fromshare() -> None:
    if TYPE_CHECKING and sys.platform != "win32":  # pragma: no cover
        return
    a, b = tsocket.socketpair()
    with a, b:
        # share with ourselves
        shared = a.share(os.getpid())
        a2 = tsocket.fromshare(shared)
        with a2:
            assert a.fileno() != a2.fileno()
            await a2.send(b"x")
            assert await b.recv(1) == b"x"


async def test_socket() -> None:
    with tsocket.socket() as s:
        assert isinstance(s, tsocket.SocketType)
        assert s.family == tsocket.AF_INET


@creates_ipv6
async def test_socket_v6() -> None:
    with tsocket.socket(tsocket.AF_INET6, tsocket.SOCK_DGRAM) as s:
        assert isinstance(s, tsocket.SocketType)
        assert s.family == tsocket.AF_INET6


@pytest.mark.skipif(sys.platform != "linux", reason="linux only")
async def test_sniff_sockopts() -> None:
    from socket import AF_INET, AF_INET6, SOCK_DGRAM, SOCK_STREAM

    # generate the combinations of families/types we're testing:
    families = (AF_INET, AF_INET6) if can_create_ipv6 else (AF_INET,)
    sockets = [
        stdlib_socket.socket(family, type_)
        for family in families
        for type_ in [SOCK_DGRAM, SOCK_STREAM]
    ]
    for socket in sockets:
        # regular Trio socket constructor
        tsocket_socket = tsocket.socket(fileno=socket.fileno())
        # check family / type for correctness:
        assert tsocket_socket.family == socket.family
        assert tsocket_socket.type == socket.type
        tsocket_socket.detach()

        # fromfd constructor
        tsocket_from_fd = tsocket.fromfd(socket.fileno(), AF_INET, SOCK_STREAM)
        # check family / type for correctness:
        assert tsocket_from_fd.family == socket.family
        assert tsocket_from_fd.type == socket.type
        tsocket_from_fd.close()

        socket.close()


################################################################
# _SocketType
################################################################


async def test_SocketType_basics() -> None:
    sock = tsocket.socket()
    with sock as cm_enter_value:
        assert cm_enter_value is sock
        assert isinstance(sock.fileno(), int)
        assert not sock.get_inheritable()
        sock.set_inheritable(True)
        assert sock.get_inheritable()

        sock.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, False)
        assert not sock.getsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY)
        sock.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, True)
        assert sock.getsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY)
    # closed sockets have fileno() == -1
    assert sock.fileno() == -1

    # smoke test
    repr(sock)

    # detach
    with tsocket.socket() as sock:
        fd = sock.fileno()
        assert sock.detach() == fd
        assert sock.fileno() == -1

    # close
    sock = tsocket.socket()
    assert sock.fileno() >= 0
    sock.close()
    assert sock.fileno() == -1

    # share was tested above together with fromshare

    # check __dir__
    assert "family" in dir(sock)
    assert "recv" in dir(sock)
    assert "setsockopt" in dir(sock)

    # our __getattr__ handles unknown names
    with pytest.raises(AttributeError):
        sock.asdf  # type: ignore[attr-defined]  # noqa: B018

    # type family proto
    stdlib_sock = stdlib_socket.socket()
    sock = tsocket.from_stdlib_socket(stdlib_sock)
    assert sock.type == stdlib_sock.type
    assert sock.family == stdlib_sock.family
    assert sock.proto == stdlib_sock.proto
    sock.close()


async def test_SocketType_setsockopt() -> None:
    sock = tsocket.socket()
    with sock as _:
        setsockopt_tests(sock)


def setsockopt_tests(sock: SocketType | SocketStream) -> None:
    """Extract these out, to be reused for SocketStream also."""
    # specifying optlen. Not supported on pypy, and I couldn't find
    # valid calls on darwin or win32.
    if hasattr(tsocket, "SO_BINDTODEVICE"):
        try:
            sock.setsockopt(tsocket.SOL_SOCKET, tsocket.SO_BINDTODEVICE, None, 0)
        except OSError as e:
            assert e.errno in [  # noqa: PT017
                # some versions of Python have the attribute yet can run on
                # platforms that do not support it. For instance, MacOS 15
                # gained support for SO_BINDTODEVICE and CPython 3.13.1 was
                # built on it (presumably), but our CI runners ran MacOS 14 and
                # so failed.
                42,
                # Older Linux kernels (prior to patch
                # https://lore.kernel.org/netdev/m37drhs1jn.fsf@bernat.ch/t/)
                # do not support SO_BINDTODEVICE as an unprivileged user.
                errno.EPERM,
            ]

    # specifying value
    sock.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, False)

    # specifying both
    with pytest.raises(TypeError, match="invalid value for argument 'value'"):
        sock.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, False, 5)  # type: ignore[call-overload]

    # specifying neither
    with pytest.raises(TypeError, match="invalid value for argument 'value'"):
        sock.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, None)  # type: ignore[call-overload]


async def test_SocketType_dup() -> None:
    a, b = tsocket.socketpair()
    with a, b:
        a2 = a.dup()
        with a2:
            assert isinstance(a2, tsocket.SocketType)
            assert a2.fileno() != a.fileno()
            a.close()
            await a2.send(b"x")
            assert await b.recv(1) == b"x"


async def test_SocketType_shutdown() -> None:
    a, b = tsocket.socketpair()
    with a, b:
        await a.send(b"x")
        assert await b.recv(1) == b"x"
        assert not a.did_shutdown_SHUT_WR
        assert not b.did_shutdown_SHUT_WR
        a.shutdown(tsocket.SHUT_WR)
        assert a.did_shutdown_SHUT_WR
        assert not b.did_shutdown_SHUT_WR
        assert await b.recv(1) == b""
        await b.send(b"y")
        assert await a.recv(1) == b"y"

    a, b = tsocket.socketpair()
    with a, b:
        assert not a.did_shutdown_SHUT_WR
        a.shutdown(tsocket.SHUT_RD)
        assert not a.did_shutdown_SHUT_WR

    a, b = tsocket.socketpair()
    with a, b:
        assert not a.did_shutdown_SHUT_WR
        a.shutdown(tsocket.SHUT_RDWR)
        assert a.did_shutdown_SHUT_WR


@pytest.mark.parametrize(
    ("address", "socket_type"),
    [
        ("127.0.0.1", tsocket.AF_INET),
        pytest.param("::1", tsocket.AF_INET6, marks=binds_ipv6),
    ],
)
async def test_SocketType_simple_server(
    address: str,
    socket_type: AddressFamily,
) -> None:
    # listen, bind, accept, connect, getpeername, getsockname
    listener = tsocket.socket(socket_type)
    client = tsocket.socket(socket_type)
    with listener, client:
        await listener.bind((address, 0))
        listener.listen(20)
        addr = listener.getsockname()[:2]
        async with _core.open_nursery() as nursery:
            nursery.start_soon(client.connect, addr)
            server, client_addr = await listener.accept()
        with server:
            assert client_addr == server.getpeername() == client.getsockname()
            await server.send(b"x")
            assert await client.recv(1) == b"x"


async def test_SocketType_is_readable() -> None:
    a, b = tsocket.socketpair()
    with a, b:
        assert not a.is_readable()
        await b.send(b"x")
        await _core.wait_readable(a)
        assert a.is_readable()
        assert await a.recv(1) == b"x"
        assert not a.is_readable()


# On some macOS systems, getaddrinfo likes to return V4-mapped addresses even
# when we *don't* pass AI_V4MAPPED.
# https://github.com/python-trio/trio/issues/580
def gai_without_v4mapped_is_buggy() -> bool:  # pragma: no cover
    try:
        stdlib_socket.getaddrinfo("1.2.3.4", 0, family=stdlib_socket.AF_INET6)
    except stdlib_socket.gaierror:
        return False
    else:
        return True


@attrs.define(slots=False)
class Addresses:
    bind_all: str
    localhost: str
    arbitrary: str
    broadcast: str


# Direct thorough tests of the implicit resolver helpers
@pytest.mark.parametrize(
    ("socket_type", "addrs"),
    [
        (
            tsocket.AF_INET,
            Addresses(
                bind_all="0.0.0.0",
                localhost="127.0.0.1",
                arbitrary="1.2.3.4",
                broadcast="255.255.255.255",
            ),
        ),
        pytest.param(
            tsocket.AF_INET6,
            Addresses(
                bind_all="::",
                localhost="::1",
                arbitrary="1::2",
                broadcast="::ffff:255.255.255.255",
            ),
            marks=creates_ipv6,
        ),
    ],
)
async def test_SocketType_resolve(socket_type: AddressFamily, addrs: Addresses) -> None:
    v6 = socket_type == tsocket.AF_INET6

    def pad(addr: tuple[str | int, ...]) -> tuple[str | int, ...]:
        if v6:
            while len(addr) < 4:
                addr += (0,)
        return addr

    def assert_eq(
        actual: tuple[str | int, ...],
        expected: tuple[str | int, ...],
    ) -> None:
        assert pad(expected) == pad(actual)

    with tsocket.socket(family=socket_type) as sock:
        # testing internal functionality, so we check it against the internal type
        assert isinstance(sock, _SocketType)

        # For some reason the stdlib special-cases "" to pass NULL to
        # getaddrinfo. They also error out on None, but whatever, None is much
        # more consistent, so we accept it too.
        # TODO: this implies that we can send host=None, but what does that imply for the return value, and other stuff?
        for null in [None, ""]:
            got = await sock._resolve_address_nocp((null, 80), local=True)
            assert not isinstance(got, (str, bytes))
            assert_eq(got, (addrs.bind_all, 80))
            got = await sock._resolve_address_nocp((null, 80), local=False)
            assert not isinstance(got, (str, bytes))
            assert_eq(got, (addrs.localhost, 80))

        # AI_PASSIVE only affects the wildcard address, so for everything else
        # local=True/local=False should work the same:
        for local in [False, True]:

            async def res(
                args: (
                    tuple[str, int]
                    | tuple[str, int, int]
                    | tuple[str, int, int, int]
                    | tuple[str, str]
                    | tuple[str, str, int]
                    | tuple[str, str, int, int]
                ),
            ) -> tuple[str | int, ...]:
                value = await sock._resolve_address_nocp(
                    args,
                    local=local,  # noqa: B023  # local is not bound in function definition
                )
                assert isinstance(value, tuple)
                return cast("tuple[Union[str, int], ...]", value)

            assert_eq(await res((addrs.arbitrary, "http")), (addrs.arbitrary, 80))
            if v6:
                # Check handling of different length ipv6 address tuples
                assert_eq(await res(("1::2", 80)), ("1::2", 80, 0, 0))
                assert_eq(await res(("1::2", 80, 0)), ("1::2", 80, 0, 0))
                assert_eq(await res(("1::2", 80, 0, 0)), ("1::2", 80, 0, 0))
                # Non-zero flowinfo/scopeid get passed through
                assert_eq(await res(("1::2", 80, 1)), ("1::2", 80, 1, 0))
                assert_eq(await res(("1::2", 80, 1, 2)), ("1::2", 80, 1, 2))

                # And again with a string port, as a trick to avoid the
                # already-resolved address fastpath and make sure we call
                # getaddrinfo
                assert_eq(await res(("1::2", "80")), ("1::2", 80, 0, 0))
                assert_eq(await res(("1::2", "80", 0)), ("1::2", 80, 0, 0))
                assert_eq(await res(("1::2", "80", 0, 0)), ("1::2", 80, 0, 0))
                assert_eq(await res(("1::2", "80", 1)), ("1::2", 80, 1, 0))
                assert_eq(await res(("1::2", "80", 1, 2)), ("1::2", 80, 1, 2))

                # V4 mapped addresses resolved if V6ONLY is False
                sock.setsockopt(tsocket.IPPROTO_IPV6, tsocket.IPV6_V6ONLY, False)
                assert_eq(await res(("1.2.3.4", "http")), ("::ffff:1.2.3.4", 80))

            # Check the <broadcast> special case, because why not
            assert_eq(await res(("<broadcast>", 123)), (addrs.broadcast, 123))

            # But not if it's true (at least on systems where getaddrinfo works
            # correctly)
            if v6 and not gai_without_v4mapped_is_buggy():
                sock.setsockopt(tsocket.IPPROTO_IPV6, tsocket.IPV6_V6ONLY, True)
                with pytest.raises(tsocket.gaierror) as excinfo:
                    await res(("1.2.3.4", 80))
                # Windows, macOS, musl/Linux
                expected_errnos = {tsocket.EAI_NONAME, tsocket.EAI_NODATA}
                # Linux
                if hasattr(tsocket, "EAI_ADDRFAMILY"):
                    expected_errnos.add(tsocket.EAI_ADDRFAMILY)
                assert excinfo.value.errno in expected_errnos

            # A family where we know nothing about the addresses, so should just
            # pass them through. This should work on Linux, which is enough to
            # smoke test the basic functionality...
            try:
                netlink_sock = tsocket.socket(
                    family=tsocket.AF_NETLINK,
                    type=tsocket.SOCK_DGRAM,
                )
            except (AttributeError, OSError):
                pass
            else:
                assert isinstance(netlink_sock, _SocketType)
                assert (
                    await netlink_sock._resolve_address_nocp("asdf", local=local)
                    == "asdf"
                )
                netlink_sock.close()

            address = r"^address should be a \(host, port(, \[flowinfo, \[scopeid\]\])*\) tuple$"
            with pytest.raises(ValueError, match=address):
                await res("1.2.3.4")  # type: ignore[arg-type]
            with pytest.raises(ValueError, match=address):
                await res(("1.2.3.4",))  # type: ignore[arg-type]
            with pytest.raises(
                ValueError,
                match=address,
            ):
                if v6:
                    await res(("1.2.3.4", 80, 0, 0, 0))  # type: ignore[arg-type]
                else:
                    # I guess in theory there could be enough overloads that this could error?
                    await res(("1.2.3.4", 80, 0, 0))


async def test_SocketType_unresolved_names() -> None:
    with tsocket.socket() as sock:
        await sock.bind(("localhost", 0))
        assert sock.getsockname()[0] == "127.0.0.1"
        sock.listen(10)

        with tsocket.socket() as sock2:
            await sock2.connect(("localhost", sock.getsockname()[1]))
            assert sock2.getpeername() == sock.getsockname()

    # check gaierror propagates out
    with tsocket.socket() as sock:
        with pytest.raises(tsocket.gaierror):
            # definitely not a valid request
            await sock.bind(("1.2:3", -1))


# This tests all the complicated paths through _nonblocking_helper, using recv
# as a stand-in for all the methods that use _nonblocking_helper.
async def test_SocketType_non_blocking_paths() -> None:
    a, b = stdlib_socket.socketpair()
    with a, b:
        ta = tsocket.from_stdlib_socket(a)
        b.setblocking(False)

        # cancel before even calling
        b.send(b"1")
        with _core.CancelScope() as cscope:
            cscope.cancel()
            with assert_checkpoints():
                with pytest.raises(_core.Cancelled):
                    await ta.recv(10)
        # immediate success (also checks that the previous attempt didn't
        # actually read anything)
        with assert_checkpoints():
            assert await ta.recv(10) == b"1"
        # immediate failure
        with assert_checkpoints():
            with pytest.raises(TypeError):
                await ta.recv("haha")  # type: ignore[arg-type]
        # block then succeed

        async def do_successful_blocking_recv() -> None:
            with assert_checkpoints():
                assert await ta.recv(10) == b"2"

        async with _core.open_nursery() as nursery:
            nursery.start_soon(do_successful_blocking_recv)
            await wait_all_tasks_blocked()
            b.send(b"2")
        # block then cancelled

        async def do_cancelled_blocking_recv() -> None:
            with assert_checkpoints():
                with pytest.raises(_core.Cancelled):
                    await ta.recv(10)

        async with _core.open_nursery() as nursery:
            nursery.start_soon(do_cancelled_blocking_recv)
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()
        # Okay, here's the trickiest one: we want to exercise the path where
        # the task is signaled to wake, goes to recv, but then the recv fails,
        # so it has to go back to sleep and try again. Strategy: have two
        # tasks waiting on two sockets (to work around the rule against having
        # two tasks waiting on the same socket), wake them both up at the same
        # time, and whichever one runs first "steals" the data from the
        # other:
        tb = tsocket.from_stdlib_socket(b)

        async def t1() -> None:
            with assert_checkpoints():
                assert await ta.recv(1) == b"a"
            with assert_checkpoints():
                assert await tb.recv(1) == b"b"

        async def t2() -> None:
            with assert_checkpoints():
                assert await tb.recv(1) == b"b"
            with assert_checkpoints():
                assert await ta.recv(1) == b"a"

        async with _core.open_nursery() as nursery:
            nursery.start_soon(t1)
            nursery.start_soon(t2)
            await wait_all_tasks_blocked()
            a.send(b"b")
            b.send(b"a")
            await wait_all_tasks_blocked()
            a.send(b"b")
            b.send(b"a")


# This tests the complicated paths through connect
@slow
async def test_SocketType_connect_paths() -> None:
    with tsocket.socket() as sock:
        with pytest.raises(
            ValueError,
            match=r"^address should be a \(host, port(, \[flowinfo, \[scopeid\]\])*\) tuple$",
        ):
            # Should be a tuple
            await sock.connect("localhost")

    # cancelled before we start
    with tsocket.socket() as sock:
        with _core.CancelScope() as cancel_scope:
            cancel_scope.cancel()
            with pytest.raises(_core.Cancelled):
                await sock.connect(("127.0.0.1", 80))

    # Cancelled in between the connect() call and the connect completing
    with _core.CancelScope() as cancel_scope:
        with tsocket.socket() as sock, tsocket.socket() as listener:
            await listener.bind(("127.0.0.1", 0))
            listener.listen()

            # Swap in our weird subclass under the trio.socket._SocketType's
            # nose -- and then swap it back out again before we hit
            # wait_socket_writable, which insists on a real socket.
            class CancelSocket(stdlib_socket.socket):
                def connect(
                    self,
                    address: AddressFormat,
                ) -> None:
                    # accessing private method only available in _SocketType
                    assert isinstance(sock, _SocketType)

                    cancel_scope.cancel()
                    sock._sock = stdlib_socket.fromfd(
                        self.detach(),
                        self.family,
                        self.type,
                    )
                    sock._sock.connect(address)
                    # If connect *doesn't* raise, then pretend it did
                    raise BlockingIOError  # pragma: no cover

            # accessing private method only available in _SocketType
            assert isinstance(sock, _SocketType)
            sock._sock.close()
            sock._sock = CancelSocket()

            with assert_checkpoints():
                with pytest.raises(_core.Cancelled):
                    await sock.connect(listener.getsockname())
            assert sock.fileno() == -1

    # Failed connect (hopefully after raising BlockingIOError)
    with tsocket.socket() as sock:
        with pytest.raises(
            OSError,
            match=r"^\[\w+ \d+\] Error connecting to \('127\.0\.0\.\d', \d+\): (Connection refused|Unknown error)$",
        ):
            # TCP port 2 is not assigned. Pretty sure nothing will be
            # listening there. (We used to bind a port and then *not* call
            # listen() to ensure nothing was listening there, but it turns
            # out on macOS if you do this it takes 30 seconds for the
            # connect to fail. Really. Also if you use a non-routable
            # address. This way fails instantly though. As long as nothing
            # is listening on port 2.)

            # Windows retries failed connections so this takes seconds
            # (and that's why this is marked @slow)
            await sock.connect(("127.0.0.1", 2))


# Fix issue #1810
@slow
async def test_address_in_socket_error() -> None:
    address = "127.0.0.1"
    with tsocket.socket() as sock:
        with pytest.raises(
            OSError,
            match=rf"^\[\w+ \d+\] Error connecting to \({address!r}, 2\): (Connection refused|Unknown error)$",
        ):
            # Windows retries failed connections so this takes seconds
            # (and that's why this is marked @slow)
            await sock.connect((address, 2))


async def test_resolve_address_exception_in_connect_closes_socket() -> None:
    # Here we are testing issue 247, any cancellation will leave the socket closed
    with _core.CancelScope() as cancel_scope:
        with tsocket.socket() as sock:

            async def _resolve_address_nocp(
                address: AddressFormat,
                *,
                local: bool,
            ) -> None:
                assert address == ""
                assert not local
                cancel_scope.cancel()
                await _core.checkpoint()

            assert isinstance(sock, _SocketType)
            sock._resolve_address_nocp = _resolve_address_nocp  # type: ignore[method-assign]
            with assert_checkpoints():
                with pytest.raises(_core.Cancelled):
                    await sock.connect("")
            assert sock.fileno() == -1


async def test_send_recv_variants() -> None:
    a, b = tsocket.socketpair()
    with a, b:
        # recv, including with flags
        assert await a.send(b"x") == 1
        assert await b.recv(10, tsocket.MSG_PEEK) == b"x"
        assert await b.recv(10) == b"x"

        # recv_into
        await a.send(b"x")
        buf = bytearray(10)
        await b.recv_into(buf)
        assert buf == b"x" + b"\x00" * 9

        if hasattr(a, "sendmsg"):
            assert await a.sendmsg([b"xxx"], []) == 3
            assert await b.recv(10) == b"xxx"

    a = tsocket.socket(type=tsocket.SOCK_DGRAM)
    b = tsocket.socket(type=tsocket.SOCK_DGRAM)
    with a, b:
        await a.bind(("127.0.0.1", 0))
        await b.bind(("127.0.0.1", 0))

        targets = [b.getsockname(), ("localhost", b.getsockname()[1])]

        # recvfrom + sendto, with and without names
        for target in targets:
            assert await a.sendto(b"xxx", target) == 3
            (data, addr) = await b.recvfrom(10)
            assert data == b"xxx"
            assert addr == a.getsockname()

        # sendto + flags
        #
        # I can't find any flags that send() accepts... on Linux at least
        # passing MSG_MORE to send_some on a connected UDP socket seems to
        # just be ignored.
        #
        # But there's no MSG_MORE on Windows or macOS. I guess send_some flags
        # are really not very useful, but at least this tests them a bit.
        if hasattr(tsocket, "MSG_MORE"):
            await a.sendto(b"xxx", tsocket.MSG_MORE, b.getsockname())
            await a.sendto(b"yyy", tsocket.MSG_MORE, b.getsockname())
            await a.sendto(b"zzz", b.getsockname())
            (data, addr) = await b.recvfrom(10)
            assert data == b"xxxyyyzzz"
            assert addr == a.getsockname()

        # recvfrom_into
        assert await a.sendto(b"xxx", b.getsockname()) == 3
        buf = bytearray(10)
        (nbytes, addr) = await b.recvfrom_into(buf)
        assert nbytes == 3
        assert buf == b"xxx" + b"\x00" * 7
        assert addr == a.getsockname()

        if hasattr(b, "recvmsg"):
            assert await a.sendto(b"xxx", b.getsockname()) == 3
            (data, ancdata, msg_flags, addr) = await b.recvmsg(10)
            assert data == b"xxx"
            assert ancdata == []
            assert msg_flags == 0
            assert addr == a.getsockname()

        if hasattr(b, "recvmsg_into"):
            assert await a.sendto(b"xyzw", b.getsockname()) == 4
            buf1 = bytearray(2)
            buf2 = bytearray(3)
            ret = await b.recvmsg_into([buf1, buf2])
            (nbytes, ancdata, msg_flags, addr) = ret
            assert nbytes == 4
            assert buf1 == b"xy"
            assert buf2 == b"zw" + b"\x00"
            assert ancdata == []
            assert msg_flags == 0
            assert addr == a.getsockname()

        if hasattr(a, "sendmsg"):
            for target in targets:
                assert await a.sendmsg([b"x", b"yz"], [], 0, target) == 3
                assert await b.recvfrom(10) == (b"xyz", a.getsockname())

    a = tsocket.socket(type=tsocket.SOCK_DGRAM)
    b = tsocket.socket(type=tsocket.SOCK_DGRAM)
    with a, b:
        await b.bind(("127.0.0.1", 0))
        await a.connect(b.getsockname())
        # send on a connected udp socket; each call creates a separate
        # datagram
        await a.send(b"xxx")
        await a.send(b"yyy")
        assert await b.recv(10) == b"xxx"
        assert await b.recv(10) == b"yyy"


async def test_idna(monkeygai: MonkeypatchedGAI) -> None:
    # This is the encoding for "faß.de", which uses one of the characters that
    # IDNA 2003 handles incorrectly:
    monkeygai.set("ok faß.de", b"xn--fa-hia.de", 80)
    monkeygai.set("ok ::1", "::1", 80, flags=_NUMERIC_ONLY)
    monkeygai.set("ok ::1", b"::1", 80, flags=_NUMERIC_ONLY)
    # Some things that should not reach the underlying socket.getaddrinfo:
    monkeygai.set("bad", "fass.de", 80)
    # We always call socket.getaddrinfo with bytes objects:
    monkeygai.set("bad", "xn--fa-hia.de", 80)

    assert await tsocket.getaddrinfo("::1", 80) == "ok ::1"
    assert await tsocket.getaddrinfo(b"::1", 80) == "ok ::1"
    assert await tsocket.getaddrinfo("faß.de", 80) == "ok faß.de"
    assert await tsocket.getaddrinfo("xn--fa-hia.de", 80) == "ok faß.de"
    assert await tsocket.getaddrinfo(b"xn--fa-hia.de", 80) == "ok faß.de"


async def test_getprotobyname() -> None:
    # These are the constants used in IP header fields, so the numeric values
    # had *better* be stable across systems...
    assert await tsocket.getprotobyname("udp") == 17
    assert await tsocket.getprotobyname("tcp") == 6


async def test_custom_hostname_resolver(monkeygai: MonkeypatchedGAI) -> None:
    # This intentionally breaks the signatures used in HostnameResolver
    class CustomResolver:
        async def getaddrinfo(
            self,
            host: str,
            port: str,
            family: int,
            type: int,
            proto: int,
            flags: int,
        ) -> tuple[str, str, str, int, int, int, int]:
            return ("custom_gai", host, port, family, type, proto, flags)

        async def getnameinfo(
            self,
            sockaddr: tuple[str, int] | tuple[str, int, int, int],
            flags: int,
        ) -> tuple[str, tuple[str, int] | tuple[str, int, int, int], int]:
            return ("custom_gni", sockaddr, flags)

    cr = CustomResolver()

    assert tsocket.set_custom_hostname_resolver(cr) is None  # type: ignore[arg-type]

    # Check that the arguments are all getting passed through.
    # We have to use valid calls to avoid making the underlying system
    # getaddrinfo cranky when it's used for NUMERIC checks.
    for vals in [
        (tsocket.AF_INET, 0, 0, 0),
        (0, tsocket.SOCK_STREAM, 0, 0),
        (0, 0, tsocket.IPPROTO_TCP, 0),
        (0, 0, 0, tsocket.AI_CANONNAME),
    ]:
        assert await tsocket.getaddrinfo("localhost", "foo", *vals) == (
            "custom_gai",
            b"localhost",
            "foo",
            *vals,
        )

    # IDNA encoding is handled before calling the special object
    got = await tsocket.getaddrinfo("föö", "foo")
    expected = ("custom_gai", b"xn--f-1gaa", "foo", 0, 0, 0, 0)
    assert got == expected

    assert await tsocket.getnameinfo("a", 0) == (  # type: ignore[arg-type]
        "custom_gni",
        "a",
        0,
    )

    # We can set it back to None
    assert tsocket.set_custom_hostname_resolver(None) is cr

    # And now Trio switches back to calling socket.getaddrinfo (specifically
    # our monkeypatched version of socket.getaddrinfo)
    monkeygai.set("x", b"host", "port", family=0, type=0, proto=0, flags=0)
    assert await tsocket.getaddrinfo("host", "port") == "x"


async def test_custom_socket_factory() -> None:
    class CustomSocketFactory:
        def socket(
            self,
            family: AddressFamily,
            type: SocketKind,
            proto: int,
        ) -> tuple[str, AddressFamily, SocketKind, int]:
            return ("hi", family, type, proto)

    csf = CustomSocketFactory()

    assert tsocket.set_custom_socket_factory(csf) is None  # type: ignore[arg-type]

    assert tsocket.socket() == ("hi", tsocket.AF_INET, tsocket.SOCK_STREAM, 0)
    assert tsocket.socket(1, 2, 3) == ("hi", 1, 2, 3)

    # socket with fileno= doesn't call our custom method
    fd = stdlib_socket.socket().detach()
    wrapped = tsocket.socket(fileno=fd)
    assert hasattr(wrapped, "bind")
    wrapped.close()

    # Likewise for socketpair
    a, b = tsocket.socketpair()
    with a, b:
        assert hasattr(a, "bind")
        assert hasattr(b, "bind")

    assert tsocket.set_custom_socket_factory(None) is csf


def test_SocketType_is_abstract() -> None:
    with pytest.raises(TypeError):
        tsocket.SocketType()


@pytest.mark.skipif(not hasattr(tsocket, "AF_UNIX"), reason="no unix domain sockets")
async def test_unix_domain_socket() -> None:
    # Bind has a special branch to use a thread, since it has to do filesystem
    # traversal. Maybe connect should too? Not sure.

    async def check_AF_UNIX(path: str | bytes | os.PathLike[str]) -> None:
        with tsocket.socket(family=tsocket.AF_UNIX) as lsock:
            await lsock.bind(path)
            lsock.listen(10)
            with tsocket.socket(family=tsocket.AF_UNIX) as csock:
                await csock.connect(path)
                ssock, _ = await lsock.accept()
                with ssock:
                    await csock.send(b"x")
                    assert await ssock.recv(1) == b"x"

    # Can't use tmpdir fixture, because we can exceed the maximum AF_UNIX path
    # length on macOS.
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test passing various supported types as path
        # Must use different filenames to prevent "address already in use"
        await check_AF_UNIX(f"{tmpdir}/sock")
        await check_AF_UNIX(Path(f"{tmpdir}/sock1"))
        await check_AF_UNIX(os.fsencode(f"{tmpdir}/sock2"))

    try:
        cookie = os.urandom(20).hex().encode("ascii")
        await check_AF_UNIX(b"\x00trio-test-" + cookie)
    except FileNotFoundError:
        # macOS doesn't support abstract filenames with the leading NUL byte
        pass


async def test_interrupted_by_close() -> None:
    a_stdlib, b_stdlib = stdlib_socket.socketpair()
    with a_stdlib, b_stdlib:
        a_stdlib.setblocking(False)

        data = b"x" * 99999

        try:
            while True:
                a_stdlib.send(data)
        except BlockingIOError:
            pass

        a = tsocket.from_stdlib_socket(a_stdlib)

        async def sender() -> None:
            with pytest.raises(_core.ClosedResourceError):
                await a.send(data)

        async def receiver() -> None:
            with pytest.raises(_core.ClosedResourceError):
                await a.recv(1)

        async with _core.open_nursery() as nursery:
            nursery.start_soon(sender)
            nursery.start_soon(receiver)
            await wait_all_tasks_blocked()
            a.close()


async def test_many_sockets() -> None:
    total = 1000  # Must be more than MAX_AFD_GROUP_SIZE
    sockets = []
    # Open at most <total> socket pairs
    for opened in range(0, total, 2):
        try:
            a, b = stdlib_socket.socketpair()
        except OSError as exc:  # pragma: no cover
            # Semi-expecting following errors (sockets are files):
            # EMFILE: "Too many open files" (reached kernel cap)
            # ENFILE: "File table overflow" (beyond kernel cap)
            assert exc.errno in (errno.EMFILE, errno.ENFILE)  # noqa: PT017
            print(f"Unable to open more than {opened} sockets.")
            # Stop opening any more sockets if too many are open
            break
        sockets += [a, b]
    async with _core.open_nursery() as nursery:
        for socket in sockets:
            nursery.start_soon(_core.wait_readable, socket)
        await _core.wait_all_tasks_blocked()
        nursery.cancel_scope.cancel()
    for socket in sockets:
        socket.close()

# === NexusCore/openenv\Lib\site-packages\IPython\core\ultratb.py ===
"""
Verbose and colourful traceback formatting.

**ColorTB**

I've always found it a bit hard to visually parse tracebacks in Python.  The
ColorTB class is a solution to that problem.  It colors the different parts of a
traceback in a manner similar to what you would expect from a syntax-highlighting
text editor.

Installation instructions for ColorTB::

    import sys,ultratb
    sys.excepthook = ultratb.ColorTB()

**VerboseTB**

I've also included a port of Ka-Ping Yee's "cgitb.py" that produces all kinds
of useful info when a traceback occurs.  Ping originally had it spit out HTML
and intended it for CGI programmers, but why should they have all the fun?  I
altered it to spit out colored text to the terminal.  It's a bit overwhelming,
but kind of neat, and maybe useful for long-running programs that you believe
are bug-free.  If a crash *does* occur in that type of program you want details.
Give it a shot--you'll love it or you'll hate it.

.. note::

  The Verbose mode prints the variables currently visible where the exception
  happened (shortening their strings if too long). This can potentially be
  very slow, if you happen to have a huge data structure whose string
  representation is complex to compute. Your computer may appear to freeze for
  a while with cpu usage at 100%. If this occurs, you can cancel the traceback
  with Ctrl-C (maybe hitting it more than once).

  If you encounter this kind of situation often, you may want to use the
  Verbose_novars mode instead of the regular Verbose, which avoids formatting
  variables (but otherwise includes the information and context given by
  Verbose).

.. note::

  The verbose mode print all variables in the stack, which means it can
  potentially leak sensitive information like access keys, or unencrypted
  password.

Installation instructions for VerboseTB::

    import sys,ultratb
    sys.excepthook = ultratb.VerboseTB()

Note:  Much of the code in this module was lifted verbatim from the standard
library module 'traceback.py' and Ka-Ping Yee's 'cgitb.py'.


Inheritance diagram:

.. inheritance-diagram:: IPython.core.ultratb
   :parts: 3
"""

# *****************************************************************************
# Copyright (C) 2001 Nathaniel Gray <n8gray@caltech.edu>
# Copyright (C) 2001-2004 Fernando Perez <fperez@colorado.edu>
#
# Distributed under the terms of the BSD License.  The full license is in
# the file COPYING, distributed as part of this software.
# *****************************************************************************

import functools
import inspect
import linecache
import sys
import time
import traceback
import types
import warnings
from collections.abc import Sequence
from types import TracebackType
from typing import Any, Callable, List, Optional, Tuple

import stack_data
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.token import Token

from IPython import get_ipython
from IPython.utils import path as util_path
from IPython.utils import py3compat
from IPython.utils.PyColorize import Parser, Theme, TokenStream, theme_table
from IPython.utils.terminal import get_terminal_size

from .display_trap import DisplayTrap
from .doctb import DocTB
from .tbtools import (
    FrameInfo,
    TBTools,
    _format_traceback_lines,
    _safe_string,
    _simple_format_traceback_lines,
    _tokens_filename,
    eqrepr,
    get_line_number_of_frame,
    nullrepr,
    text_repr,
)

# Globals
# amount of space to put line numbers before verbose tracebacks
INDENT_SIZE = 8

# When files are too long do not use stackdata to get frames.
# it is too long.
FAST_THRESHOLD = 10_000

# ---------------------------------------------------------------------------
class ListTB(TBTools):
    """Print traceback information from a traceback list, with optional color.

    Calling requires 3 arguments: (etype, evalue, elist)
    as would be obtained by::

      etype, evalue, tb = sys.exc_info()
      if tb:
        elist = traceback.extract_tb(tb)
      else:
        elist = None

    It can thus be used by programs which need to process the traceback before
    printing (such as console replacements based on the code module from the
    standard library).

    Because they are meant to be called without a full traceback (only a
    list), instances of this class can't call the interactive pdb debugger."""

    def __call__(
        self,
        etype: type[BaseException],
        evalue: BaseException | None,
        etb: TracebackType | None,
    ) -> None:
        self.ostream.flush()
        self.ostream.write(self.text(etype, evalue, etb))
        self.ostream.write("\n")

    def _extract_tb(self, tb: TracebackType | None) -> traceback.StackSummary | None:
        if tb:
            return traceback.extract_tb(tb)
        else:
            return None

    def structured_traceback(
        self,
        etype: type,
        evalue: Optional[BaseException],
        etb: Optional[TracebackType] = None,
        tb_offset: Optional[int] = None,
        context: int = 5,
    ) -> list[str]:
        """Return a color formatted string with the traceback info.

        Parameters
        ----------
        etype : exception type
            Type of the exception raised.
        evalue : object
            Data stored in the exception
        etb : list | TracebackType | None
            If list: List of frames, see class docstring for details.
            If Traceback: Traceback of the exception.
        tb_offset : int, optional
            Number of frames in the traceback to skip.  If not given, the
            instance evalue is used (set in constructor).
        context : int, optional
            Number of lines of context information to print.

        Returns
        -------
        String with formatted exception.
        """
        # This is a workaround to get chained_exc_ids in recursive calls
        # etb should not be a tuple if structured_traceback is not recursive
        if isinstance(etb, tuple):
            etb, chained_exc_ids = etb
        else:
            chained_exc_ids = set()
        elist: list[Any]
        if isinstance(etb, list):
            elist = etb
        elif etb is not None:
            elist = self._extract_tb(etb)  # type: ignore[assignment]
        else:
            elist = []
        tb_offset = self.tb_offset if tb_offset is None else tb_offset
        assert isinstance(tb_offset, int)
        out_list: list[str] = []
        if elist:
            if tb_offset and len(elist) > tb_offset:
                elist = elist[tb_offset:]

            out_list.append(
                theme_table[self._theme_name].format(
                    [
                        (Token, "Traceback"),
                        (Token, " "),
                        (Token.NormalEm, "(most recent call last)"),
                        (Token, ":"),
                        (Token, "\n"),
                    ]
                ),
            )
            out_list.extend(self._format_list(elist))
        # The exception info should be a single entry in the list.
        lines = "".join(self._format_exception_only(etype, evalue))
        out_list.append(lines)

        # Find chained exceptions if we have a traceback (not for exception-only mode)
        if etb is not None:
            exception = self.get_parts_of_chained_exception(evalue)

            if exception and (id(exception[1]) not in chained_exc_ids):
                chained_exception_message: list[str] = (
                    self.prepare_chained_exception_message(evalue.__cause__)[0]
                    if evalue is not None
                    else [""]
                )
                etype, evalue, etb = exception
                # Trace exception to avoid infinite 'cause' loop
                chained_exc_ids.add(id(exception[1]))
                chained_exceptions_tb_offset = 0
                ol1 = self.structured_traceback(
                    etype,
                    evalue,
                    (etb, chained_exc_ids),  # type: ignore[arg-type]
                    chained_exceptions_tb_offset,
                    context,
                )
                ol2 = chained_exception_message

                out_list = ol1 + ol2 + out_list

        return out_list

    def _format_list(self, extracted_list: list[Any]) -> list[str]:
        """Format a list of traceback entry tuples for printing.

        Given a list of tuples as returned by extract_tb() or
        extract_stack(), return a list of strings ready for printing.
        Each string in the resulting list corresponds to the item with the
        same index in the argument list.  Each string ends in a newline;
        the strings may contain internal newlines as well, for those items
        whose source text line is not None.

        Lifted almost verbatim from traceback.py
        """

        output_list = []
        for ind, (filename, lineno, name, line) in enumerate(extracted_list):
            # Will emphasize the last entry
            em = True if ind == len(extracted_list) - 1 else False

            item = theme_table[self._theme_name].format(
                [(Token.NormalEm if em else Token.Normal, "  ")]
                + _tokens_filename(em, filename, lineno=lineno)
            )

            # This seem to be only in xmode plain (%run sinpleer), investigate why not share with verbose.
            # look at _tokens_filename in forma_record.
            if name != "<module>":
                item += theme_table[self._theme_name].format(
                    [
                        (Token.NormalEm if em else Token.Normal, " in "),
                        (Token.TB.NameEm if em else Token.TB.Name, name),
                    ]
                )
            item += theme_table[self._theme_name].format(
                [(Token.NormalEm if em else Token, "\n")]
            )
            if line:
                item += theme_table[self._theme_name].format(
                    [
                        (Token.Line if em else Token, "    "),
                        (Token.Line if em else Token, line.strip()),
                        (Token, "\n"),
                    ]
                )
            output_list.append(item)

        return output_list

    def _format_exception_only(
        self, etype: type[BaseException], value: BaseException | None
    ) -> list[str]:
        """Format the exception part of a traceback.

        The arguments are the exception type and value such as given by
        sys.exc_info()[:2]. The return value is a list of strings, each ending
        in a newline.  Normally, the list contains a single string; however,
        for SyntaxError exceptions, it contains several lines that (when
        printed) display detailed information about where the syntax error
        occurred.  The message indicating which exception occurred is the
        always last string in the list.

        Also lifted nearly verbatim from traceback.py
        """
        have_filedata = False
        output_list = []
        stype_tokens = [(Token.ExcName, etype.__name__)]
        stype: str = theme_table[self._theme_name].format(stype_tokens)
        if value is None:
            # Not sure if this can still happen in Python 2.6 and above
            output_list.append(stype + "\n")
        else:
            if issubclass(etype, SyntaxError):
                assert hasattr(value, "filename")
                assert hasattr(value, "lineno")
                assert hasattr(value, "text")
                assert hasattr(value, "offset")
                assert hasattr(value, "msg")
                have_filedata = True
                if not value.filename:
                    value.filename = "<string>"
                if value.lineno:
                    lineno = value.lineno
                    textline = linecache.getline(value.filename, value.lineno)
                else:
                    lineno = "unknown"
                    textline = ""
                output_list.append(
                    theme_table[self._theme_name].format(
                        [(Token, "  ")]
                        + _tokens_filename(
                            True,
                            value.filename,
                            lineno=(None if lineno == "unknown" else lineno),
                        )
                        + [(Token, "\n")]
                    )
                )
                if textline == "":
                    textline = py3compat.cast_unicode(value.text, "utf-8")

                if textline is not None:
                    i = 0
                    while i < len(textline) and textline[i].isspace():
                        i += 1
                    output_list.append(
                        theme_table[self._theme_name].format(
                            [
                                (Token.Line, "    "),
                                (Token.Line, textline.strip()),
                                (Token, "\n"),
                            ]
                        )
                    )
                    if value.offset is not None:
                        s = "    "
                        for c in textline[i : value.offset - 1]:
                            if c.isspace():
                                s += c
                            else:
                                s += " "
                        output_list.append(
                            theme_table[self._theme_name].format(
                                [(Token.Caret, s + "^"), (Token, "\n")]
                            )
                        )

            try:
                assert hasattr(value, "msg")
                s = value.msg
            except Exception:
                s = self._some_str(value)
            if s:
                output_list.append(
                    theme_table[self._theme_name].format(
                        stype_tokens
                        + [
                            (Token.ExcName, ":"),
                            (Token, " "),
                            (Token, s),
                            (Token, "\n"),
                        ]
                    )
                )
            else:
                output_list.append("%s\n" % stype)

            # PEP-678 notes
            output_list.extend(f"{x}\n" for x in getattr(value, "__notes__", []))

        # sync with user hooks
        if have_filedata:
            ipinst = get_ipython()
            if ipinst is not None:
                assert value is not None
                assert hasattr(value, "lineno")
                assert hasattr(value, "filename")
                ipinst.hooks.synchronize_with_editor(value.filename, value.lineno, 0)

        return output_list

    def get_exception_only(self, etype, value):
        """Only print the exception type and message, without a traceback.

        Parameters
        ----------
        etype : exception type
        value : exception value
        """
        return ListTB.structured_traceback(self, etype, value)

    def show_exception_only(
        self, etype: BaseException | None, evalue: TracebackType | None
    ) -> None:
        """Only print the exception type and message, without a traceback.

        Parameters
        ----------
        etype : exception type
        evalue : exception value
        """
        # This method needs to use __call__ from *this* class, not the one from
        # a subclass whose signature or behavior may be different
        ostream = self.ostream
        ostream.flush()
        ostream.write("\n".join(self.get_exception_only(etype, evalue)))
        ostream.flush()

    def _some_str(self, value: Any) -> str:
        # Lifted from traceback.py
        try:
            return py3compat.cast_unicode(str(value))
        except:
            return "<unprintable %s object>" % type(value).__name__


_sentinel = object()
_default = "default"


# ----------------------------------------------------------------------------
class VerboseTB(TBTools):
    """A port of Ka-Ping Yee's cgitb.py module that outputs color text instead
    of HTML.  Requires inspect and pydoc.  Crazy, man.

    Modified version which optionally strips the topmost entries from the
    traceback, to be used with alternate interpreters (because their own code
    would appear in the traceback)."""

    tb_highlight = "bg:ansiyellow"
    tb_highlight_style = "default"

    _mode: str

    def __init__(
        self,
        # TODO: no default ?
        theme_name: str = _default,
        call_pdb: bool = False,
        ostream: Any = None,
        tb_offset: int = 0,
        long_header: bool = False,
        include_vars: bool = True,
        check_cache: Callable[[], None] | None = None,
        debugger_cls: type | None = None,
        *,
        color_scheme: Any = _sentinel,
    ):
        """Specify traceback offset, headers and color scheme.

        Define how many frames to drop from the tracebacks. Calling it with
        tb_offset=1 allows use of this handler in interpreters which will have
        their own code at the top of the traceback (VerboseTB will first
        remove that frame before printing the traceback info)."""
        if color_scheme is not _sentinel:
            assert isinstance(color_scheme, str)
            theme_name = color_scheme.lower()

            warnings.warn(
                "color_scheme is deprecated as of IPython 9.0 and replaced by "
                "theme_name (which should be lowercase). As you passed a "
                "color_scheme value I will try to see if I have corresponding "
                "theme.",
                stacklevel=2,
                category=DeprecationWarning,
            )

            if theme_name != _default:
                warnings.warn(
                    "You passed both `theme_name` and `color_scheme` "
                    "(deprecated) to VerboseTB constructor. `theme_name` will "
                    "be ignored for the time being.",
                    stacklevel=2,
                    category=DeprecationWarning,
                )

        if theme_name == _default:
            theme_name = "linux"

        assert isinstance(theme_name, str)
        super().__init__(
            theme_name=theme_name,
            call_pdb=call_pdb,
            ostream=ostream,
            debugger_cls=debugger_cls,
        )
        self.tb_offset = tb_offset
        self.long_header = long_header
        self.include_vars = include_vars
        # By default we use linecache.checkcache, but the user can provide a
        # different check_cache implementation.  This was formerly used by the
        # IPython kernel for interactive code, but is no longer necessary.
        if check_cache is None:
            check_cache = linecache.checkcache
        self.check_cache = check_cache

        self.skip_hidden = True

    def format_record(self, frame_info: FrameInfo) -> str:
        """Format a single stack frame"""
        assert isinstance(frame_info, FrameInfo)

        if isinstance(frame_info._sd, stack_data.RepeatedFrames):
            return theme_table[self._theme_name].format(
                [
                    (Token, "    "),
                    (
                        Token.ExcName,
                        "[... skipping similar frames: %s]" % frame_info.description,
                    ),
                    (Token, "\n"),
                ]
            )

        indent: str = " " * INDENT_SIZE

        assert isinstance(frame_info.lineno, int)
        args, varargs, varkw, locals_ = inspect.getargvalues(frame_info.frame)
        if frame_info.executing is not None:
            func = frame_info.executing.code_qualname()
        else:
            func = "?"
        if func == "<module>":
            call = ""
        else:
            # Decide whether to include variable details or not
            var_repr = eqrepr if self.include_vars else nullrepr
            try:
                scope = inspect.formatargvalues(
                    args, varargs, varkw, locals_, formatvalue=var_repr
                )
                assert isinstance(scope, str)
                call = theme_table[self._theme_name].format(
                    [(Token, "in "), (Token.VName, func), (Token.ValEm, scope)]
                )
            except KeyError:
                # This happens in situations like errors inside generator
                # expressions, where local variables are listed in the
                # line, but can't be extracted from the frame.  I'm not
                # 100% sure this isn't actually a bug in inspect itself,
                # but since there's no info for us to compute with, the
                # best we can do is report the failure and move on.  Here
                # we must *not* call any traceback construction again,
                # because that would mess up use of %debug later on.  So we
                # simply report the failure and move on.  The only
                # limitation will be that this frame won't have locals
                # listed in the call signature.  Quite subtle problem...
                # I can't think of a good way to validate this in a unit
                # test, but running a script consisting of:
                #  dict( (k,v.strip()) for (k,v) in range(10) )
                # will illustrate the error, if this exception catch is
                # disabled.
                call = theme_table[self._theme_name].format(
                    [
                        (Token, "in "),
                        (Token.VName, func),
                        (Token.ValEm, "(***failed resolving arguments***)"),
                    ]
                )

        lvals_toks: list[TokenStream] = []
        if self.include_vars:
            try:
                # we likely want to fix stackdata at some point, but
                # still need a workaround.
                fibp = frame_info.variables_in_executing_piece
                for var in fibp:
                    lvals_toks.append(
                        [
                            (Token, var.name),
                            (Token, " "),
                            (Token.ValEm, "= "),
                            (Token.ValEm, repr(var.value)),
                        ]
                    )
            except Exception:
                lvals_toks.append(
                    [
                        (
                            Token,
                            "Exception trying to inspect frame. No more locals available.",
                        ),
                    ]
                )

        if frame_info._sd is None:
            # fast fallback if file is too long
            assert frame_info.filename is not None
            level_tokens = [
                (Token.FilenameEm, util_path.compress_user(frame_info.filename)),
                (Token, " "),
                (Token, call),
                (Token, "\n"),
            ]

            _line_format = Parser(theme_name=self._theme_name).format2
            assert isinstance(frame_info.code, types.CodeType)
            first_line: int = frame_info.code.co_firstlineno
            current_line: int = frame_info.lineno
            raw_lines: list[str] = frame_info.raw_lines
            index: int = current_line - first_line
            assert frame_info.context is not None
            if index >= frame_info.context:
                start = max(index - frame_info.context, 0)
                stop = index + frame_info.context
                index = frame_info.context
            else:
                start = 0
                stop = index + frame_info.context
            raw_lines = raw_lines[start:stop]

            # Jan 2025: may need _line_format(py3ompat.cast_unicode(s))
            raw_color_err = [(s, _line_format(s, "str")) for s in raw_lines]

            tb_tokens = _simple_format_traceback_lines(
                current_line,
                index,
                raw_color_err,
                lvals_toks,
                theme=theme_table[self._theme_name],
            )
            _tb_lines: str = theme_table[self._theme_name].format(tb_tokens)

            return theme_table[self._theme_name].format(level_tokens + tb_tokens)
        else:
            result = theme_table[self._theme_name].format(
                _tokens_filename(True, frame_info.filename, lineno=frame_info.lineno)
            )
            result += ", " if call else ""
            result += f"{call}\n"
            result += theme_table[self._theme_name].format(
                _format_traceback_lines(
                    frame_info.lines,
                    theme_table[self._theme_name],
                    self.has_colors,
                    lvals_toks,
                )
            )
            return result

    def prepare_header(self, etype: str, long_version: bool = False) -> str:
        width = min(75, get_terminal_size()[0])
        if long_version:
            # Header with the exception type, python version, and date
            pyver = "Python " + sys.version.split()[0] + ": " + sys.executable
            date = time.ctime(time.time())
            theme = theme_table[self._theme_name]
            head = theme.format(
                [
                    (Token.Topline, theme.symbols["top_line"] * width),
                    (Token, "\n"),
                    (Token.ExcName, etype),
                    (Token, " " * (width - len(etype) - len(pyver))),
                    (Token, pyver),
                    (Token, "\n"),
                    (Token, date.rjust(width)),
                ]
            )
            head += (
                "\nA problem occurred executing Python code.  Here is the sequence of function"
                "\ncalls leading up to the error, with the most recent (innermost) call last."
            )
        else:
            # Simplified header
            head = theme_table[self._theme_name].format(
                [
                    (Token.ExcName, etype),
                    (
                        Token,
                        "Traceback (most recent call last)".rjust(width - len(etype)),
                    ),
                ]
            )

        return head

    def format_exception(self, etype, evalue):
        # Get (safely) a string form of the exception info
        try:
            etype_str, evalue_str = map(str, (etype, evalue))
        except:
            # User exception is improperly defined.
            etype, evalue = str, sys.exc_info()[:2]
            etype_str, evalue_str = map(str, (etype, evalue))

        # PEP-678 notes
        notes = getattr(evalue, "__notes__", [])
        if not isinstance(notes, Sequence) or isinstance(notes, (str, bytes)):
            notes = [_safe_string(notes, "__notes__", func=repr)]

        # ... and format it
        return [
            theme_table[self._theme_name].format(
                [(Token.ExcName, etype_str), (Token, ": "), (Token, evalue_str)]
            ),
            *(
                theme_table[self._theme_name].format(
                    [(Token, _safe_string(py3compat.cast_unicode(n), "note"))]
                )
                for n in notes
            ),
        ]

    def format_exception_as_a_whole(
        self,
        etype: type,
        evalue: Optional[BaseException],
        etb: Optional[TracebackType],
        context: int,
        tb_offset: Optional[int],
    ) -> list[list[str]]:
        """Formats the header, traceback and exception message for a single exception.

        This may be called multiple times by Python 3 exception chaining
        (PEP 3134).
        """
        # some locals
        orig_etype = etype
        try:
            etype = etype.__name__  # type: ignore[assignment]
        except AttributeError:
            pass

        tb_offset = self.tb_offset if tb_offset is None else tb_offset
        assert isinstance(tb_offset, int)
        head = self.prepare_header(str(etype), self.long_header)
        records = self.get_records(etb, context, tb_offset) if etb else []

        frames = []
        skipped = 0
        lastrecord = len(records) - 1
        for i, record in enumerate(records):
            if (
                not isinstance(record._sd, stack_data.RepeatedFrames)
                and self.skip_hidden
            ):
                if (
                    record.frame.f_locals.get("__tracebackhide__", 0)
                    and i != lastrecord
                ):
                    skipped += 1
                    continue
            if skipped:
                frames.append(
                    theme_table[self._theme_name].format(
                        [
                            (Token, "    "),
                            (Token.ExcName, "[... skipping hidden %s frame]" % skipped),
                            (Token, "\n"),
                        ]
                    )
                )
                skipped = 0
            frames.append(self.format_record(record))
        if skipped:
            frames.append(
                theme_table[self._theme_name].format(
                    [
                        (Token, "    "),
                        (Token.ExcName, "[... skipping hidden %s frame]" % skipped),
                        (Token, "\n"),
                    ]
                )
            )

        formatted_exception = self.format_exception(etype, evalue)
        if records:
            frame_info = records[-1]
            ipinst = get_ipython()
            if ipinst is not None:
                ipinst.hooks.synchronize_with_editor(
                    frame_info.filename, frame_info.lineno, 0
                )

        return [[head] + frames + formatted_exception]

    def get_records(self, etb: TracebackType, context: int, tb_offset: int) -> Any:
        assert etb is not None
        context = context - 1
        after = context // 2
        before = context - after
        if self.has_colors:
            base_style = theme_table[self._theme_name].as_pygments_style()
            style = stack_data.style_with_executing_node(base_style, self.tb_highlight)
            formatter = Terminal256Formatter(style=style)
        else:
            formatter = None
        options = stack_data.Options(
            before=before,
            after=after,
            pygments_formatter=formatter,
        )

        # Let's estimate the amount of code we will have to parse/highlight.
        cf: Optional[TracebackType] = etb
        max_len = 0
        tbs = []
        while cf is not None:
            try:
                mod = inspect.getmodule(cf.tb_frame)
                if mod is not None:
                    mod_name = mod.__name__
                    root_name, *_ = mod_name.split(".")
                    if root_name == "IPython":
                        cf = cf.tb_next
                        continue
                max_len = get_line_number_of_frame(cf.tb_frame)

            except OSError:
                max_len = 0
            max_len = max(max_len, max_len)
            tbs.append(cf)
            cf = getattr(cf, "tb_next", None)

        if max_len > FAST_THRESHOLD:
            FIs: list[FrameInfo] = []
            for tb in tbs:
                frame = tb.tb_frame  # type: ignore[union-attr]
                lineno = frame.f_lineno
                code = frame.f_code
                filename = code.co_filename
                # TODO: Here we need to use before/after/
                FIs.append(
                    FrameInfo(
                        "Raw frame", filename, lineno, frame, code, context=context
                    )
                )
            return FIs
        res = list(stack_data.FrameInfo.stack_data(etb, options=options))[tb_offset:]
        res2 = [FrameInfo._from_stack_data_FrameInfo(r) for r in res]
        return res2

    def structured_traceback(
        self,
        etype: type,
        evalue: Optional[BaseException],
        etb: Optional[TracebackType] = None,
        tb_offset: Optional[int] = None,
        context: int = 5,
    ) -> list[str]:
        """Return a nice text document describing the traceback."""
        formatted_exceptions: list[list[str]] = self.format_exception_as_a_whole(
            etype, evalue, etb, context, tb_offset
        )

        termsize = min(75, get_terminal_size()[0])
        theme = theme_table[self._theme_name]
        head: str = theme.format(
            [
                (
                    Token.Topline,
                    theme.symbols["top_line"] * termsize,
                ),
            ]
        )
        structured_traceback_parts: list[str] = [head]
        chained_exceptions_tb_offset = 0
        lines_of_context = 3
        exception = self.get_parts_of_chained_exception(evalue)
        if exception:
            assert evalue is not None
            formatted_exceptions += self.prepare_chained_exception_message(
                evalue.__cause__
            )
            etype, evalue, etb = exception
        else:
            evalue = None
        chained_exc_ids = set()
        while evalue:
            formatted_exceptions += self.format_exception_as_a_whole(
                etype, evalue, etb, lines_of_context, chained_exceptions_tb_offset
            )
            exception = self.get_parts_of_chained_exception(evalue)

            if exception and id(exception[1]) not in chained_exc_ids:
                chained_exc_ids.add(
                    id(exception[1])
                )  # trace exception to avoid infinite 'cause' loop
                formatted_exceptions += self.prepare_chained_exception_message(
                    evalue.__cause__
                )
                etype, evalue, etb = exception
            else:
                evalue = None

        # we want to see exceptions in a reversed order:
        # the first exception should be on top
        for fx in reversed(formatted_exceptions):
            structured_traceback_parts += fx

        return structured_traceback_parts

    def debugger(self, force: bool = False) -> None:
        """Call up the pdb debugger if desired, always clean up the tb
        reference.

        Keywords:

          - force(False): by default, this routine checks the instance call_pdb
            flag and does not actually invoke the debugger if the flag is false.
            The 'force' option forces the debugger to activate even if the flag
            is false.

        If the call_pdb flag is set, the pdb interactive debugger is
        invoked. In all cases, the self.tb reference to the current traceback
        is deleted to prevent lingering references which hamper memory
        management.

        Note that each call to pdb() does an 'import readline', so if your app
        requires a special setup for the readline completers, you'll have to
        fix that by hand after invoking the exception handler."""

        if force or self.call_pdb:
            if self.pdb is None:
                self.pdb = self.debugger_cls()
            # the system displayhook may have changed, restore the original
            # for pdb
            display_trap = DisplayTrap(hook=sys.__displayhook__)
            with display_trap:
                self.pdb.reset()
                # Find the right frame so we don't pop up inside ipython itself
                if hasattr(self, "tb") and self.tb is not None:  # type: ignore[has-type]
                    etb = self.tb  # type: ignore[has-type]
                else:
                    etb = self.tb = sys.last_traceback
                while self.tb is not None and self.tb.tb_next is not None:
                    assert self.tb.tb_next is not None
                    self.tb = self.tb.tb_next
                if etb and etb.tb_next:
                    etb = etb.tb_next
                self.pdb.botframe = etb.tb_frame
                # last_value should be deprecated, but last-exc sometimme not set
                # please check why later and remove the getattr.
                exc = (
                    sys.last_value
                    if sys.version_info < (3, 12)
                    else getattr(sys, "last_exc", sys.last_value)
                )  # type: ignore[attr-defined]
                if exc:
                    self.pdb.interaction(None, exc)
                else:
                    self.pdb.interaction(None, etb)

        if hasattr(self, "tb"):
            del self.tb

    def handler(self, info=None):
        (etype, evalue, etb) = info or sys.exc_info()
        self.tb = etb
        ostream = self.ostream
        ostream.flush()
        ostream.write(self.text(etype, evalue, etb))  # type:ignore[arg-type]
        ostream.write("\n")
        ostream.flush()

    # Changed so an instance can just be called as VerboseTB_inst() and print
    # out the right info on its own.
    def __call__(self, etype=None, evalue=None, etb=None):
        """This hook can replace sys.excepthook (for Python 2.1 or higher)."""
        if etb is None:
            self.handler()
        else:
            self.handler((etype, evalue, etb))
        try:
            self.debugger()
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt")


# ----------------------------------------------------------------------------
class FormattedTB(VerboseTB, ListTB):
    """Subclass ListTB but allow calling with a traceback.

    It can thus be used as a sys.excepthook for Python > 2.1.

    Also adds 'Context' and 'Verbose' modes, not available in ListTB.

    Allows a tb_offset to be specified. This is useful for situations where
    one needs to remove a number of topmost frames from the traceback (such as
    occurs with python programs that themselves execute other python code,
    like Python shells)."""

    mode: str

    def __init__(
        self,
        mode="Plain",
        # TODO: no default
        theme_name="linux",
        call_pdb=False,
        ostream=None,
        tb_offset=0,
        long_header=False,
        include_vars=False,
        check_cache=None,
        debugger_cls=None,
    ):
        # NEVER change the order of this list. Put new modes at the end:
        self.valid_modes = ["Plain", "Context", "Verbose", "Minimal", "Docs"]
        self.verbose_modes = self.valid_modes[1:3]

        VerboseTB.__init__(
            self,
            theme_name=theme_name,
            call_pdb=call_pdb,
            ostream=ostream,
            tb_offset=tb_offset,
            long_header=long_header,
            include_vars=include_vars,
            check_cache=check_cache,
            debugger_cls=debugger_cls,
        )

        # Different types of tracebacks are joined with different separators to
        # form a single string.  They are taken from this dict
        self._join_chars = dict(
            Plain="", Context="\n", Verbose="\n", Minimal="", Docs=""
        )
        # set_mode also sets the tb_join_char attribute
        self.set_mode(mode)

    def structured_traceback(
        self,
        etype: type,
        evalue: BaseException | None,
        etb: TracebackType | None = None,
        tb_offset: int | None = None,
        context: int = 5,
    ) -> list[str]:
        tb_offset = self.tb_offset if tb_offset is None else tb_offset
        mode = self.mode
        if mode in self.verbose_modes:
            # Verbose modes need a full traceback
            return VerboseTB.structured_traceback(
                self, etype, evalue, etb, tb_offset, context
            )
        elif mode == "Docs":
            # return DocTB
            return DocTB(
                theme_name=self._theme_name,
                call_pdb=self.call_pdb,
                ostream=self.ostream,
                tb_offset=tb_offset,
                long_header=self.long_header,
                include_vars=self.include_vars,
                check_cache=self.check_cache,
                debugger_cls=self.debugger_cls,
            ).structured_traceback(
                etype, evalue, etb, tb_offset, 1
            )  # type: ignore[arg-type]

        elif mode == "Minimal":
            return ListTB.get_exception_only(self, etype, evalue)
        else:
            # We must check the source cache because otherwise we can print
            # out-of-date source code.
            self.check_cache()
            # Now we can extract and format the exception
            return ListTB.structured_traceback(
                self, etype, evalue, etb, tb_offset, context
            )

    def stb2text(self, stb: list[str]) -> str:
        """Convert a structured traceback (a list) to a string."""
        return self.tb_join_char.join(stb)

    def set_mode(self, mode: Optional[str] = None) -> None:
        """Switch to the desired mode.

        If mode is not specified, cycles through the available modes."""

        if not mode:
            new_idx = (self.valid_modes.index(self.mode) + 1) % len(self.valid_modes)
            self.mode = self.valid_modes[new_idx]
        elif mode not in self.valid_modes:
            raise ValueError(
                "Unrecognized mode in FormattedTB: <" + mode + ">\n"
                "Valid modes: " + str(self.valid_modes)
            )
        else:
            assert isinstance(mode, str)
            self.mode = mode
        # include variable details only in 'Verbose' mode
        self.include_vars = self.mode == self.valid_modes[2]
        # Set the join character for generating text tracebacks
        self.tb_join_char = self._join_chars[self.mode]

    # some convenient shortcuts
    def plain(self) -> None:
        self.set_mode(self.valid_modes[0])

    def context(self) -> None:
        self.set_mode(self.valid_modes[1])

    def verbose(self) -> None:
        self.set_mode(self.valid_modes[2])

    def minimal(self) -> None:
        self.set_mode(self.valid_modes[3])


# ----------------------------------------------------------------------------
class AutoFormattedTB(FormattedTB):
    """A traceback printer which can be called on the fly.

    It will find out about exceptions by itself.

    A brief example::

        AutoTB = AutoFormattedTB(mode = 'Verbose', theme_name='linux')
        try:
          ...
        except:
          AutoTB()  # or AutoTB(out=logfile) where logfile is an open file object
    """

    def __call__(
        self,
        etype: type | None = None,
        evalue: BaseException | None = None,
        etb: TracebackType | None = None,
        out: Any = None,
        tb_offset: int | None = None,
    ) -> None:
        """Print out a formatted exception traceback.

        Optional arguments:
          - out: an open file-like object to direct output to.

          - tb_offset: the number of frames to skip over in the stack, on a
          per-call basis (this overrides temporarily the instance's tb_offset
          given at initialization time."""

        if out is None:
            out = self.ostream
        out.flush()
        out.write(self.text(etype, evalue, etb, tb_offset))  # type:ignore[arg-type]
        out.write("\n")
        out.flush()
        # FIXME: we should remove the auto pdb behavior from here and leave
        # that to the clients.
        try:
            self.debugger()
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt")

    def structured_traceback(
        self,
        etype: type,
        evalue: Optional[BaseException],
        etb: Optional[TracebackType] = None,
        tb_offset: Optional[int] = None,
        context: int = 5,
    ) -> list[str]:
        # tb: TracebackType or tupleof tb types ?
        if etype is None:
            etype, evalue, etb = sys.exc_info()
        if isinstance(etb, tuple):
            # tb is a tuple if this is a chained exception.
            self.tb = etb[0]
        else:
            self.tb = etb
        return FormattedTB.structured_traceback(
            self, etype, evalue, etb, tb_offset, context
        )


# ---------------------------------------------------------------------------


# A simple class to preserve Nathan's original functionality.
class ColorTB(FormattedTB):
    """Deprecated since IPython 9.0."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Deprecated since IPython 9.0 use FormattedTB directly ColorTB is just an alias",
            DeprecationWarning,
            stacklevel=2,
        )

        super().__init__(*args, **kwargs)


class SyntaxTB(ListTB):
    """Extension which holds some state: the last exception value"""

    last_syntax_error: BaseException | None

    def __init__(self, *, theme_name):
        super().__init__(theme_name=theme_name)
        self.last_syntax_error = None

    def __call__(self, etype, value, elist):
        self.last_syntax_error = value

        super().__call__(etype, value, elist)

    def structured_traceback(
        self,
        etype: type,
        evalue: BaseException | None,
        etb: TracebackType | None = None,
        tb_offset: int | None = None,
        context: int = 5,
    ) -> list[str]:
        value = evalue
        # If the source file has been edited, the line in the syntax error can
        # be wrong (retrieved from an outdated cache). This replaces it with
        # the current value.
        if (
            isinstance(value, SyntaxError)
            and isinstance(value.filename, str)
            and isinstance(value.lineno, int)
        ):
            linecache.checkcache(value.filename)
            newtext = linecache.getline(value.filename, value.lineno)
            if newtext:
                value.text = newtext
        self.last_syntax_error = value
        return super(SyntaxTB, self).structured_traceback(
            etype, value, etb, tb_offset=tb_offset, context=context
        )

    def clear_err_state(self) -> Any | None:
        """Return the current error state and clear it"""
        e = self.last_syntax_error
        self.last_syntax_error = None
        return e

    def stb2text(self, stb: list[str]) -> str:
        """Convert a structured traceback (a list) to a string."""
        return "".join(stb)

# === NexusCore/openenv\Lib\site-packages\git\remote.py ===
# Copyright (C) 2008, 2009 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

"""Module implementing a remote object allowing easy access to git remotes."""

__all__ = ["RemoteProgress", "PushInfo", "FetchInfo", "Remote"]

import contextlib
import logging
import re

from git.cmd import Git, handle_process_output
from git.compat import defenc, force_text
from git.config import GitConfigParser, SectionConstraint, cp
from git.exc import GitCommandError
from git.refs import Head, Reference, RemoteReference, SymbolicReference, TagReference
from git.util import (
    CallableRemoteProgress,
    IterableList,
    IterableObj,
    LazyMixin,
    RemoteProgress,
    join_path,
)

# typing-------------------------------------------------------

from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    NoReturn,
    Optional,
    Sequence,
    TYPE_CHECKING,
    Type,
    Union,
    cast,
    overload,
)

from git.types import AnyGitObject, Literal, PathLike

if TYPE_CHECKING:
    from git.objects.commit import Commit
    from git.objects.submodule.base import UpdateProgress
    from git.repo.base import Repo

flagKeyLiteral = Literal[" ", "!", "+", "-", "*", "=", "t", "?"]

# -------------------------------------------------------------

_logger = logging.getLogger(__name__)

# { Utilities


def add_progress(
    kwargs: Any,
    git: Git,
    progress: Union[RemoteProgress, "UpdateProgress", Callable[..., RemoteProgress], None],
) -> Any:
    """Add the ``--progress`` flag to the given `kwargs` dict if supported by the git
    command.

    :note:
        If the actual progress in the given progress instance is not given, we do not
        request any progress.

    :return:
        Possibly altered `kwargs`
    """
    if progress is not None:
        v = git.version_info[:2]
        if v >= (1, 7):
            kwargs["progress"] = True
        # END handle --progress
    # END handle progress
    return kwargs


# } END utilities


@overload
def to_progress_instance(progress: None) -> RemoteProgress: ...


@overload
def to_progress_instance(progress: Callable[..., Any]) -> CallableRemoteProgress: ...


@overload
def to_progress_instance(progress: RemoteProgress) -> RemoteProgress: ...


def to_progress_instance(
    progress: Union[Callable[..., Any], RemoteProgress, None],
) -> Union[RemoteProgress, CallableRemoteProgress]:
    """Given the `progress` return a suitable object derived from
    :class:`~git.util.RemoteProgress`."""
    # New API only needs progress as a function.
    if callable(progress):
        return CallableRemoteProgress(progress)

    # Where None is passed create a parser that eats the progress.
    elif progress is None:
        return RemoteProgress()

    # Assume its the old API with an instance of RemoteProgress.
    return progress


class PushInfo(IterableObj):
    """
    Carries information about the result of a push operation of a single head::

        info = remote.push()[0]
        info.flags          # bitflags providing more information about the result
        info.local_ref      # Reference pointing to the local reference that was pushed
                            # It is None if the ref was deleted.
        info.remote_ref_string # path to the remote reference located on the remote side
        info.remote_ref # Remote Reference on the local side corresponding to
                        # the remote_ref_string. It can be a TagReference as well.
        info.old_commit # commit at which the remote_ref was standing before we pushed
                        # it to local_ref.commit. Will be None if an error was indicated
        info.summary    # summary line providing human readable english text about the push
    """

    __slots__ = (
        "local_ref",
        "remote_ref_string",
        "flags",
        "_old_commit_sha",
        "_remote",
        "summary",
    )

    _id_attribute_ = "pushinfo"

    (
        NEW_TAG,
        NEW_HEAD,
        NO_MATCH,
        REJECTED,
        REMOTE_REJECTED,
        REMOTE_FAILURE,
        DELETED,
        FORCED_UPDATE,
        FAST_FORWARD,
        UP_TO_DATE,
        ERROR,
    ) = [1 << x for x in range(11)]

    _flag_map = {
        "X": NO_MATCH,
        "-": DELETED,
        "*": 0,
        "+": FORCED_UPDATE,
        " ": FAST_FORWARD,
        "=": UP_TO_DATE,
        "!": ERROR,
    }

    def __init__(
        self,
        flags: int,
        local_ref: Union[SymbolicReference, None],
        remote_ref_string: str,
        remote: "Remote",
        old_commit: Optional[str] = None,
        summary: str = "",
    ) -> None:
        """Initialize a new instance.

        local_ref: HEAD | Head | RemoteReference | TagReference | Reference | SymbolicReference | None
        """
        self.flags = flags
        self.local_ref = local_ref
        self.remote_ref_string = remote_ref_string
        self._remote = remote
        self._old_commit_sha = old_commit
        self.summary = summary

    @property
    def old_commit(self) -> Union["Commit", None]:
        return self._old_commit_sha and self._remote.repo.commit(self._old_commit_sha) or None

    @property
    def remote_ref(self) -> Union[RemoteReference, TagReference]:
        """
        :return:
            Remote :class:`~git.refs.reference.Reference` or
            :class:`~git.refs.tag.TagReference` in the local repository corresponding to
            the :attr:`remote_ref_string` kept in this instance.
        """
        # Translate heads to a local remote. Tags stay as they are.
        if self.remote_ref_string.startswith("refs/tags"):
            return TagReference(self._remote.repo, self.remote_ref_string)
        elif self.remote_ref_string.startswith("refs/heads"):
            remote_ref = Reference(self._remote.repo, self.remote_ref_string)
            return RemoteReference(
                self._remote.repo,
                "refs/remotes/%s/%s" % (str(self._remote), remote_ref.name),
            )
        else:
            raise ValueError("Could not handle remote ref: %r" % self.remote_ref_string)
        # END

    @classmethod
    def _from_line(cls, remote: "Remote", line: str) -> "PushInfo":
        """Create a new :class:`PushInfo` instance as parsed from line which is expected
        to be like refs/heads/master:refs/heads/master 05d2687..1d0568e as bytes."""
        control_character, from_to, summary = line.split("\t", 3)
        flags = 0

        # Control character handling
        try:
            flags |= cls._flag_map[control_character]
        except KeyError as e:
            raise ValueError("Control character %r unknown as parsed from line %r" % (control_character, line)) from e
        # END handle control character

        # from_to handling
        from_ref_string, to_ref_string = from_to.split(":")
        if flags & cls.DELETED:
            from_ref: Union[SymbolicReference, None] = None
        else:
            if from_ref_string == "(delete)":
                from_ref = None
            else:
                from_ref = Reference.from_path(remote.repo, from_ref_string)

        # Commit handling, could be message or commit info
        old_commit: Optional[str] = None
        if summary.startswith("["):
            if "[rejected]" in summary:
                flags |= cls.REJECTED
            elif "[remote rejected]" in summary:
                flags |= cls.REMOTE_REJECTED
            elif "[remote failure]" in summary:
                flags |= cls.REMOTE_FAILURE
            elif "[no match]" in summary:
                flags |= cls.ERROR
            elif "[new tag]" in summary:
                flags |= cls.NEW_TAG
            elif "[new branch]" in summary:
                flags |= cls.NEW_HEAD
            # `uptodate` encoded in control character
        else:
            # Fast-forward or forced update - was encoded in control character,
            # but we parse the old and new commit.
            split_token = "..."
            if control_character == " ":
                split_token = ".."
            old_sha, _new_sha = summary.split(" ")[0].split(split_token)
            # Have to use constructor here as the sha usually is abbreviated.
            old_commit = old_sha
        # END message handling

        return PushInfo(flags, from_ref, to_ref_string, remote, old_commit, summary)

    @classmethod
    def iter_items(cls, repo: "Repo", *args: Any, **kwargs: Any) -> NoReturn:  # -> Iterator['PushInfo']:
        raise NotImplementedError


class PushInfoList(IterableList[PushInfo]):
    """:class:`~git.util.IterableList` of :class:`PushInfo` objects."""

    def __new__(cls) -> "PushInfoList":
        return cast(PushInfoList, IterableList.__new__(cls, "push_infos"))

    def __init__(self) -> None:
        super().__init__("push_infos")
        self.error: Optional[Exception] = None

    def raise_if_error(self) -> None:
        """Raise an exception if any ref failed to push."""
        if self.error:
            raise self.error


class FetchInfo(IterableObj):
    """
    Carries information about the results of a fetch operation of a single head::

     info = remote.fetch()[0]
     info.ref           # Symbolic Reference or RemoteReference to the changed
                        # remote head or FETCH_HEAD
     info.flags         # additional flags to be & with enumeration members,
                        # i.e. info.flags & info.REJECTED
                        # is 0 if ref is SymbolicReference
     info.note          # additional notes given by git-fetch intended for the user
     info.old_commit    # if info.flags & info.FORCED_UPDATE|info.FAST_FORWARD,
                        # field is set to the previous location of ref, otherwise None
     info.remote_ref_path # The path from which we fetched on the remote. It's the remote's version of our info.ref
    """

    __slots__ = ("ref", "old_commit", "flags", "note", "remote_ref_path")

    _id_attribute_ = "fetchinfo"

    (
        NEW_TAG,
        NEW_HEAD,
        HEAD_UPTODATE,
        TAG_UPDATE,
        REJECTED,
        FORCED_UPDATE,
        FAST_FORWARD,
        ERROR,
    ) = [1 << x for x in range(8)]

    _re_fetch_result = re.compile(r"^ *(?:.{0,3})(.) (\[[\w \.$@]+\]|[\w\.$@]+) +(.+) -> ([^ ]+)(    \(.*\)?$)?")

    _flag_map: Dict[flagKeyLiteral, int] = {
        "!": ERROR,
        "+": FORCED_UPDATE,
        "*": 0,
        "=": HEAD_UPTODATE,
        " ": FAST_FORWARD,
        "-": TAG_UPDATE,
    }

    @classmethod
    def refresh(cls) -> Literal[True]:
        """Update information about which :manpage:`git-fetch(1)` flags are supported
        by the git executable being used.

        Called by the :func:`git.refresh` function in the top level ``__init__``.
        """
        # Clear the old values in _flag_map.
        with contextlib.suppress(KeyError):
            del cls._flag_map["t"]
        with contextlib.suppress(KeyError):
            del cls._flag_map["-"]

        # Set the value given the git version.
        if Git().version_info[:2] >= (2, 10):
            cls._flag_map["t"] = cls.TAG_UPDATE
        else:
            cls._flag_map["-"] = cls.TAG_UPDATE

        return True

    def __init__(
        self,
        ref: SymbolicReference,
        flags: int,
        note: str = "",
        old_commit: Union[AnyGitObject, None] = None,
        remote_ref_path: Optional[PathLike] = None,
    ) -> None:
        """Initialize a new instance."""
        self.ref = ref
        self.flags = flags
        self.note = note
        self.old_commit = old_commit
        self.remote_ref_path = remote_ref_path

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        """:return: Name of our remote ref"""
        return self.ref.name

    @property
    def commit(self) -> "Commit":
        """:return: Commit of our remote ref"""
        return self.ref.commit

    @classmethod
    def _from_line(cls, repo: "Repo", line: str, fetch_line: str) -> "FetchInfo":
        """Parse information from the given line as returned by ``git-fetch -v`` and
        return a new :class:`FetchInfo` object representing this information.

        We can handle a line as follows::

            %c %-*s %-*s -> %s%s

        Where ``c`` is either a space, ``!``, ``+``, ``-``, ``*``, or ``=``:

        - '!' means error
        - '+' means success forcing update
        - '-' means a tag was updated
        - '*' means birth of new branch or tag
        - '=' means the head was up to date (and not moved)
        - ' ' means a fast-forward

        `fetch_line` is the corresponding line from FETCH_HEAD, like::

            acb0fa8b94ef421ad60c8507b634759a472cd56c    not-for-merge   branch '0.1.7RC' of /tmp/tmpya0vairemote_repo
        """
        match = cls._re_fetch_result.match(line)
        if match is None:
            raise ValueError("Failed to parse line: %r" % line)

        # Parse lines.
        remote_local_ref_str: str
        (
            control_character,
            operation,
            local_remote_ref,
            remote_local_ref_str,
            note,
        ) = match.groups()
        control_character = cast(flagKeyLiteral, control_character)
        try:
            _new_hex_sha, _fetch_operation, fetch_note = fetch_line.split("\t")
            ref_type_name, fetch_note = fetch_note.split(" ", 1)
        except ValueError as e:  # unpack error
            raise ValueError("Failed to parse FETCH_HEAD line: %r" % fetch_line) from e

        # Parse flags from control_character.
        flags = 0
        try:
            flags |= cls._flag_map[control_character]
        except KeyError as e:
            raise ValueError("Control character %r unknown as parsed from line %r" % (control_character, line)) from e
        # END control char exception handling

        # Parse operation string for more info.
        # This makes no sense for symbolic refs, but we parse it anyway.
        old_commit: Union[AnyGitObject, None] = None
        is_tag_operation = False
        if "rejected" in operation:
            flags |= cls.REJECTED
        if "new tag" in operation:
            flags |= cls.NEW_TAG
            is_tag_operation = True
        if "tag update" in operation:
            flags |= cls.TAG_UPDATE
            is_tag_operation = True
        if "new branch" in operation:
            flags |= cls.NEW_HEAD
        if "..." in operation or ".." in operation:
            split_token = "..."
            if control_character == " ":
                split_token = split_token[:-1]
            old_commit = repo.rev_parse(operation.split(split_token)[0])
        # END handle refspec

        # Handle FETCH_HEAD and figure out ref type.
        # If we do not specify a target branch like master:refs/remotes/origin/master,
        # the fetch result is stored in FETCH_HEAD which destroys the rule we usually
        # have. In that case we use a symbolic reference which is detached.
        ref_type: Optional[Type[SymbolicReference]] = None
        if remote_local_ref_str == "FETCH_HEAD":
            ref_type = SymbolicReference
        elif ref_type_name == "tag" or is_tag_operation:
            # The ref_type_name can be branch, whereas we are still seeing a tag
            # operation. It happens during testing, which is based on actual git
            # operations.
            ref_type = TagReference
        elif ref_type_name in ("remote-tracking", "branch"):
            # Note: remote-tracking is just the first part of the
            # 'remote-tracking branch' token. We don't parse it correctly, but it's
            # enough to know what to do, and it's new in git 1.7something.
            ref_type = RemoteReference
        elif "/" in ref_type_name:
            # If the fetch spec look something like '+refs/pull/*:refs/heads/pull/*',
            # and is thus pretty much anything the user wants, we will have trouble
            # determining what's going on. For now, we assume the local ref is a Head.
            ref_type = Head
        else:
            raise TypeError("Cannot handle reference type: %r" % ref_type_name)
        # END handle ref type

        # Create ref instance.
        if ref_type is SymbolicReference:
            remote_local_ref = ref_type(repo, "FETCH_HEAD")
        else:
            # Determine prefix. Tags are usually pulled into refs/tags; they may have
            # subdirectories. It is not clear sometimes where exactly the item is,
            # unless we have an absolute path as indicated by the 'ref/' prefix.
            # Otherwise even a tag could be in refs/remotes, which is when it will have
            # the 'tags/' subdirectory in its path. We don't want to test for actual
            # existence, but try to figure everything out analytically.
            ref_path: Optional[PathLike] = None
            remote_local_ref_str = remote_local_ref_str.strip()

            if remote_local_ref_str.startswith(Reference._common_path_default + "/"):
                # Always use actual type if we get absolute paths. This will always be
                # the case if something is fetched outside of refs/remotes (if its not a
                # tag).
                ref_path = remote_local_ref_str
                if ref_type is not TagReference and not remote_local_ref_str.startswith(
                    RemoteReference._common_path_default + "/"
                ):
                    ref_type = Reference
                # END downgrade remote reference
            elif ref_type is TagReference and "tags/" in remote_local_ref_str:
                # Even though it's a tag, it is located in refs/remotes.
                ref_path = join_path(RemoteReference._common_path_default, remote_local_ref_str)
            else:
                ref_path = join_path(ref_type._common_path_default, remote_local_ref_str)
            # END obtain refpath

            # Even though the path could be within the git conventions, we make sure we
            # respect whatever the user wanted, and disabled path checking.
            remote_local_ref = ref_type(repo, ref_path, check_path=False)
        # END create ref instance

        note = (note and note.strip()) or ""

        return cls(remote_local_ref, flags, note, old_commit, local_remote_ref)

    @classmethod
    def iter_items(cls, repo: "Repo", *args: Any, **kwargs: Any) -> NoReturn:  # -> Iterator['FetchInfo']:
        raise NotImplementedError


class Remote(LazyMixin, IterableObj):
    """Provides easy read and write access to a git remote.

    Everything not part of this interface is considered an option for the current
    remote, allowing constructs like ``remote.pushurl`` to query the pushurl.

    :note:
        When querying configuration, the configuration accessor will be cached to speed
        up subsequent accesses.
    """

    __slots__ = ("repo", "name", "_config_reader")

    _id_attribute_ = "name"

    unsafe_git_fetch_options = [
        # This option allows users to execute arbitrary commands.
        # https://git-scm.com/docs/git-fetch#Documentation/git-fetch.txt---upload-packltupload-packgt
        "--upload-pack",
    ]
    unsafe_git_pull_options = [
        # This option allows users to execute arbitrary commands.
        # https://git-scm.com/docs/git-pull#Documentation/git-pull.txt---upload-packltupload-packgt
        "--upload-pack"
    ]
    unsafe_git_push_options = [
        # This option allows users to execute arbitrary commands.
        # https://git-scm.com/docs/git-push#Documentation/git-push.txt---execltgit-receive-packgt
        "--receive-pack",
        "--exec",
    ]

    url: str  # Obtained dynamically from _config_reader. See __getattr__ below.
    """The URL configured for the remote."""

    def __init__(self, repo: "Repo", name: str) -> None:
        """Initialize a remote instance.

        :param repo:
            The repository we are a remote of.

        :param name:
            The name of the remote, e.g. ``origin``.
        """
        self.repo = repo
        self.name = name

    def __getattr__(self, attr: str) -> Any:
        """Allows to call this instance like ``remote.special(*args, **kwargs)`` to
        call ``git remote special self.name``."""
        if attr == "_config_reader":
            return super().__getattr__(attr)

        # Sometimes, probably due to a bug in Python itself, we are being called even
        # though a slot of the same name exists.
        try:
            return self._config_reader.get(attr)
        except cp.NoOptionError:
            return super().__getattr__(attr)
        # END handle exception

    def _config_section_name(self) -> str:
        return 'remote "%s"' % self.name

    def _set_cache_(self, attr: str) -> None:
        if attr == "_config_reader":
            # NOTE: This is cached as __getattr__ is overridden to return remote config
            # values implicitly, such as in print(r.pushurl).
            self._config_reader = SectionConstraint(
                self.repo.config_reader("repository"),
                self._config_section_name(),
            )
        else:
            super()._set_cache_(attr)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return '<git.%s "%s">' % (self.__class__.__name__, self.name)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.name == other.name

    def __ne__(self, other: object) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return hash(self.name)

    def exists(self) -> bool:
        """
        :return:
            ``True`` if this is a valid, existing remote.
            Valid remotes have an entry in the repository's configuration.
        """
        try:
            self.config_reader.get("url")
            return True
        except cp.NoOptionError:
            # We have the section at least...
            return True
        except cp.NoSectionError:
            return False

    @classmethod
    def iter_items(cls, repo: "Repo", *args: Any, **kwargs: Any) -> Iterator["Remote"]:
        """:return: Iterator yielding :class:`Remote` objects of the given repository"""
        for section in repo.config_reader("repository").sections():
            if not section.startswith("remote "):
                continue
            lbound = section.find('"')
            rbound = section.rfind('"')
            if lbound == -1 or rbound == -1:
                raise ValueError("Remote-Section has invalid format: %r" % section)
            yield Remote(repo, section[lbound + 1 : rbound])
        # END for each configuration section

    def set_url(
        self, new_url: str, old_url: Optional[str] = None, allow_unsafe_protocols: bool = False, **kwargs: Any
    ) -> "Remote":
        """Configure URLs on current remote (cf. command ``git remote set-url``).

        This command manages URLs on the remote.

        :param new_url:
            String being the URL to add as an extra remote URL.

        :param old_url:
            When set, replaces this URL with `new_url` for the remote.

        :param allow_unsafe_protocols:
            Allow unsafe protocols to be used, like ``ext``.

        :return:
            self
        """
        if not allow_unsafe_protocols:
            Git.check_unsafe_protocols(new_url)
        scmd = "set-url"
        kwargs["insert_kwargs_after"] = scmd
        if old_url:
            self.repo.git.remote(scmd, "--", self.name, new_url, old_url, **kwargs)
        else:
            self.repo.git.remote(scmd, "--", self.name, new_url, **kwargs)
        return self

    def add_url(self, url: str, allow_unsafe_protocols: bool = False, **kwargs: Any) -> "Remote":
        """Adds a new url on current remote (special case of ``git remote set-url``).

        This command adds new URLs to a given remote, making it possible to have
        multiple URLs for a single remote.

        :param url:
            String being the URL to add as an extra remote URL.

        :param allow_unsafe_protocols:
            Allow unsafe protocols to be used, like ``ext``.

        :return:
            self
        """
        return self.set_url(url, add=True, allow_unsafe_protocols=allow_unsafe_protocols)

    def delete_url(self, url: str, **kwargs: Any) -> "Remote":
        """Deletes a new url on current remote (special case of ``git remote set-url``).

        This command deletes new URLs to a given remote, making it possible to have
        multiple URLs for a single remote.

        :param url:
            String being the URL to delete from the remote.

        :return:
            self
        """
        return self.set_url(url, delete=True)

    @property
    def urls(self) -> Iterator[str]:
        """:return: Iterator yielding all configured URL targets on a remote as strings"""
        try:
            remote_details = self.repo.git.remote("get-url", "--all", self.name)
            assert isinstance(remote_details, str)
            for line in remote_details.split("\n"):
                yield line
        except GitCommandError as ex:
            ## We are on git < 2.7 (i.e TravisCI as of Oct-2016),
            #  so `get-utl` command does not exist yet!
            #    see: https://github.com/gitpython-developers/GitPython/pull/528#issuecomment-252976319
            #    and: http://stackoverflow.com/a/32991784/548792
            #
            if "Unknown subcommand: get-url" in str(ex):
                try:
                    remote_details = self.repo.git.remote("show", self.name)
                    assert isinstance(remote_details, str)
                    for line in remote_details.split("\n"):
                        if "  Push  URL:" in line:
                            yield line.split(": ")[-1]
                except GitCommandError as _ex:
                    if any(msg in str(_ex) for msg in ["correct access rights", "cannot run ssh"]):
                        # If ssh is not setup to access this repository, see issue 694.
                        remote_details = self.repo.git.config("--get-all", "remote.%s.url" % self.name)
                        assert isinstance(remote_details, str)
                        for line in remote_details.split("\n"):
                            yield line
                    else:
                        raise _ex
            else:
                raise ex

    @property
    def refs(self) -> IterableList[RemoteReference]:
        """
        :return:
            :class:`~git.util.IterableList` of :class:`~git.refs.remote.RemoteReference`
            objects.

            It is prefixed, allowing you to omit the remote path portion, e.g.::

                remote.refs.master  # yields RemoteReference('/refs/remotes/origin/master')
        """
        out_refs: IterableList[RemoteReference] = IterableList(RemoteReference._id_attribute_, "%s/" % self.name)
        out_refs.extend(RemoteReference.list_items(self.repo, remote=self.name))
        return out_refs

    @property
    def stale_refs(self) -> IterableList[Reference]:
        """
        :return:
            :class:`~git.util.IterableList` of :class:`~git.refs.remote.RemoteReference`
            objects that do not have a corresponding head in the remote reference
            anymore as they have been deleted on the remote side, but are still
            available locally.

            The :class:`~git.util.IterableList` is prefixed, hence the 'origin' must be
            omitted. See :attr:`refs` property for an example.

            To make things more complicated, it can be possible for the list to include
            other kinds of references, for example, tag references, if these are stale
            as well. This is a fix for the issue described here:
            https://github.com/gitpython-developers/GitPython/issues/260
        """
        out_refs: IterableList[Reference] = IterableList(RemoteReference._id_attribute_, "%s/" % self.name)
        for line in self.repo.git.remote("prune", "--dry-run", self).splitlines()[2:]:
            # expecting
            # * [would prune] origin/new_branch
            token = " * [would prune] "
            if not line.startswith(token):
                continue
            ref_name = line.replace(token, "")
            # Sometimes, paths start with a full ref name, like refs/tags/foo. See #260.
            if ref_name.startswith(Reference._common_path_default + "/"):
                out_refs.append(Reference.from_path(self.repo, ref_name))
            else:
                fqhn = "%s/%s" % (RemoteReference._common_path_default, ref_name)
                out_refs.append(RemoteReference(self.repo, fqhn))
            # END special case handling
        # END for each line
        return out_refs

    @classmethod
    def create(cls, repo: "Repo", name: str, url: str, allow_unsafe_protocols: bool = False, **kwargs: Any) -> "Remote":
        """Create a new remote to the given repository.

        :param repo:
            Repository instance that is to receive the new remote.

        :param name:
            Desired name of the remote.

        :param url:
            URL which corresponds to the remote's name.

        :param allow_unsafe_protocols:
            Allow unsafe protocols to be used, like ``ext``.

        :param kwargs:
            Additional arguments to be passed to the ``git remote add`` command.

        :return:
            New :class:`Remote` instance

        :raise git.exc.GitCommandError:
            In case an origin with that name already exists.
        """
        scmd = "add"
        kwargs["insert_kwargs_after"] = scmd
        url = Git.polish_url(url)
        if not allow_unsafe_protocols:
            Git.check_unsafe_protocols(url)
        repo.git.remote(scmd, "--", name, url, **kwargs)
        return cls(repo, name)

    # `add` is an alias.
    @classmethod
    def add(cls, repo: "Repo", name: str, url: str, **kwargs: Any) -> "Remote":
        return cls.create(repo, name, url, **kwargs)

    @classmethod
    def remove(cls, repo: "Repo", name: str) -> str:
        """Remove the remote with the given name.

        :return:
            The passed remote name to remove
        """
        repo.git.remote("rm", name)
        if isinstance(name, cls):
            name._clear_cache()
        return name

    @classmethod
    def rm(cls, repo: "Repo", name: str) -> str:
        """Alias of remove.
        Remove the remote with the given name.

        :return:
            The passed remote name to remove
        """
        return cls.remove(repo, name)

    def rename(self, new_name: str) -> "Remote":
        """Rename self to the given `new_name`.

        :return:
            self
        """
        if self.name == new_name:
            return self

        self.repo.git.remote("rename", self.name, new_name)
        self.name = new_name
        self._clear_cache()

        return self

    def update(self, **kwargs: Any) -> "Remote":
        """Fetch all changes for this remote, including new branches which will be
        forced in (in case your local remote branch is not part the new remote branch's
        ancestry anymore).

        :param kwargs:
            Additional arguments passed to ``git remote update``.

        :return:
            self
        """
        scmd = "update"
        kwargs["insert_kwargs_after"] = scmd
        self.repo.git.remote(scmd, self.name, **kwargs)
        return self

    def _get_fetch_info_from_stderr(
        self,
        proc: "Git.AutoInterrupt",
        progress: Union[Callable[..., Any], RemoteProgress, None],
        kill_after_timeout: Union[None, float] = None,
    ) -> IterableList["FetchInfo"]:
        progress = to_progress_instance(progress)

        # Skip first line as it is some remote info we are not interested in.
        output: IterableList["FetchInfo"] = IterableList("name")

        # Lines which are no progress are fetch info lines.
        # This also waits for the command to finish.
        # Skip some progress lines that don't provide relevant information.
        fetch_info_lines = []
        # Basically we want all fetch info lines which appear to be in regular form, and
        # thus have a command character. Everything else we ignore.
        cmds = set(FetchInfo._flag_map.keys())

        progress_handler = progress.new_message_handler()
        handle_process_output(
            proc,
            None,
            progress_handler,
            finalizer=None,
            decode_streams=False,
            kill_after_timeout=kill_after_timeout,
        )

        stderr_text = progress.error_lines and "\n".join(progress.error_lines) or ""
        proc.wait(stderr=stderr_text)
        if stderr_text:
            _logger.warning("Error lines received while fetching: %s", stderr_text)

        for line in progress.other_lines:
            line = force_text(line)
            for cmd in cmds:
                if len(line) > 1 and line[0] == " " and line[1] == cmd:
                    fetch_info_lines.append(line)
                    continue

        # Read head information.
        fetch_head = SymbolicReference(self.repo, "FETCH_HEAD")
        with open(fetch_head.abspath, "rb") as fp:
            fetch_head_info = [line.decode(defenc) for line in fp.readlines()]

        l_fil = len(fetch_info_lines)
        l_fhi = len(fetch_head_info)
        if l_fil != l_fhi:
            msg = "Fetch head lines do not match lines provided via progress information\n"
            msg += "length of progress lines %i should be equal to lines in FETCH_HEAD file %i\n"
            msg += "Will ignore extra progress lines or fetch head lines."
            msg %= (l_fil, l_fhi)
            _logger.debug(msg)
            _logger.debug(b"info lines: " + str(fetch_info_lines).encode("UTF-8"))
            _logger.debug(b"head info: " + str(fetch_head_info).encode("UTF-8"))
            if l_fil < l_fhi:
                fetch_head_info = fetch_head_info[:l_fil]
            else:
                fetch_info_lines = fetch_info_lines[:l_fhi]
            # END truncate correct list
        # END sanity check + sanitization

        for err_line, fetch_line in zip(fetch_info_lines, fetch_head_info):
            try:
                output.append(FetchInfo._from_line(self.repo, err_line, fetch_line))
            except ValueError as exc:
                _logger.debug("Caught error while parsing line: %s", exc)
                _logger.warning("Git informed while fetching: %s", err_line.strip())
        return output

    def _get_push_info(
        self,
        proc: "Git.AutoInterrupt",
        progress: Union[Callable[..., Any], RemoteProgress, None],
        kill_after_timeout: Union[None, float] = None,
    ) -> PushInfoList:
        progress = to_progress_instance(progress)

        # Read progress information from stderr.
        # We hope stdout can hold all the data, it should...
        # Read the lines manually as it will use carriage returns between the messages
        # to override the previous one. This is why we read the bytes manually.
        progress_handler = progress.new_message_handler()
        output: PushInfoList = PushInfoList()

        def stdout_handler(line: str) -> None:
            try:
                output.append(PushInfo._from_line(self, line))
            except ValueError:
                # If an error happens, additional info is given which we parse below.
                pass

        handle_process_output(
            proc,
            stdout_handler,
            progress_handler,
            finalizer=None,
            decode_streams=False,
            kill_after_timeout=kill_after_timeout,
        )
        stderr_text = progress.error_lines and "\n".join(progress.error_lines) or ""
        try:
            proc.wait(stderr=stderr_text)
        except Exception as e:
            # This is different than fetch (which fails if there is any stderr
            # even if there is an output).
            if not output:
                raise
            elif stderr_text:
                _logger.warning("Error lines received while fetching: %s", stderr_text)
                output.error = e

        return output

    def _assert_refspec(self) -> None:
        """Turns out we can't deal with remotes if the refspec is missing."""
        config = self.config_reader
        unset = "placeholder"
        try:
            if config.get_value("fetch", default=unset) is unset:
                msg = "Remote '%s' has no refspec set.\n"
                msg += "You can set it as follows:"
                msg += " 'git config --add \"remote.%s.fetch +refs/heads/*:refs/heads/*\"'."
                raise AssertionError(msg % (self.name, self.name))
        finally:
            config.release()

    def fetch(
        self,
        refspec: Union[str, List[str], None] = None,
        progress: Union[RemoteProgress, None, "UpdateProgress"] = None,
        verbose: bool = True,
        kill_after_timeout: Union[None, float] = None,
        allow_unsafe_protocols: bool = False,
        allow_unsafe_options: bool = False,
        **kwargs: Any,
    ) -> IterableList[FetchInfo]:
        """Fetch the latest changes for this remote.

        :param refspec:
            A "refspec" is used by fetch and push to describe the mapping
            between remote ref and local ref. They are combined with a colon in
            the format ``<src>:<dst>``, preceded by an optional plus sign, ``+``.
            For example: ``git fetch $URL refs/heads/master:refs/heads/origin`` means
            "grab the master branch head from the $URL and store it as my origin
            branch head". And ``git push $URL refs/heads/master:refs/heads/to-upstream``
            means "publish my master branch head as to-upstream branch at $URL".
            See also :manpage:`git-push(1)`.

            Taken from the git manual, :manpage:`gitglossary(7)`.

            Fetch supports multiple refspecs (as the underlying :manpage:`git-fetch(1)`
            does) - supplying a list rather than a string for 'refspec' will make use of
            this facility.

        :param progress:
            See the :meth:`push` method.

        :param verbose:
            Boolean for verbose output.

        :param kill_after_timeout:
            To specify a timeout in seconds for the git command, after which the process
            should be killed. It is set to ``None`` by default.

        :param allow_unsafe_protocols:
            Allow unsafe protocols to be used, like ``ext``.

        :param allow_unsafe_options:
            Allow unsafe options to be used, like ``--upload-pack``.

        :param kwargs:
            Additional arguments to be passed to :manpage:`git-fetch(1)`.

        :return:
            IterableList(FetchInfo, ...) list of :class:`FetchInfo` instances providing
            detailed information about the fetch results

        :note:
            As fetch does not provide progress information to non-ttys, we cannot make
            it available here unfortunately as in the :meth:`push` method.
        """
        if refspec is None:
            # No argument refspec, then ensure the repo's config has a fetch refspec.
            self._assert_refspec()

        kwargs = add_progress(kwargs, self.repo.git, progress)
        if isinstance(refspec, list):
            args: Sequence[Optional[str]] = refspec
        else:
            args = [refspec]

        if not allow_unsafe_protocols:
            for ref in args:
                if ref:
                    Git.check_unsafe_protocols(ref)

        if not allow_unsafe_options:
            Git.check_unsafe_options(options=list(kwargs.keys()), unsafe_options=self.unsafe_git_fetch_options)

        proc = self.repo.git.fetch(
            "--", self, *args, as_process=True, with_stdout=False, universal_newlines=True, v=verbose, **kwargs
        )
        res = self._get_fetch_info_from_stderr(proc, progress, kill_after_timeout=kill_after_timeout)
        if hasattr(self.repo.odb, "update_cache"):
            self.repo.odb.update_cache()
        return res

    def pull(
        self,
        refspec: Union[str, List[str], None] = None,
        progress: Union[RemoteProgress, "UpdateProgress", None] = None,
        kill_after_timeout: Union[None, float] = None,
        allow_unsafe_protocols: bool = False,
        allow_unsafe_options: bool = False,
        **kwargs: Any,
    ) -> IterableList[FetchInfo]:
        """Pull changes from the given branch, being the same as a fetch followed by a
        merge of branch with your local branch.

        :param refspec:
            See :meth:`fetch` method.

        :param progress:
            See :meth:`push` method.

        :param kill_after_timeout:
            See :meth:`fetch` method.

        :param allow_unsafe_protocols:
            Allow unsafe protocols to be used, like ``ext``.

        :param allow_unsafe_options:
            Allow unsafe options to be used, like ``--upload-pack``.

        :param kwargs:
            Additional arguments to be passed to :manpage:`git-pull(1)`.

        :return:
            Please see :meth:`fetch` method.
        """
        if refspec is None:
            # No argument refspec, then ensure the repo's config has a fetch refspec.
            self._assert_refspec()
        kwargs = add_progress(kwargs, self.repo.git, progress)

        refspec = Git._unpack_args(refspec or [])
        if not allow_unsafe_protocols:
            for ref in refspec:
                Git.check_unsafe_protocols(ref)

        if not allow_unsafe_options:
            Git.check_unsafe_options(options=list(kwargs.keys()), unsafe_options=self.unsafe_git_pull_options)

        proc = self.repo.git.pull(
            "--", self, refspec, with_stdout=False, as_process=True, universal_newlines=True, v=True, **kwargs
        )
        res = self._get_fetch_info_from_stderr(proc, progress, kill_after_timeout=kill_after_timeout)
        if hasattr(self.repo.odb, "update_cache"):
            self.repo.odb.update_cache()
        return res

    def push(
        self,
        refspec: Union[str, List[str], None] = None,
        progress: Union[RemoteProgress, "UpdateProgress", Callable[..., RemoteProgress], None] = None,
        kill_after_timeout: Union[None, float] = None,
        allow_unsafe_protocols: bool = False,
        allow_unsafe_options: bool = False,
        **kwargs: Any,
    ) -> PushInfoList:
        """Push changes from source branch in refspec to target branch in refspec.

        :param refspec:
            See :meth:`fetch` method.

        :param progress:
            Can take one of many value types:

            * ``None``, to discard progress information.
            * A function (callable) that is called with the progress information.
              Signature: ``progress(op_code, cur_count, max_count=None, message='')``.
              See :meth:`RemoteProgress.update <git.util.RemoteProgress.update>` for a
              description of all arguments given to the function.
            * An instance of a class derived from :class:`~git.util.RemoteProgress` that
              overrides the
              :meth:`RemoteProgress.update <git.util.RemoteProgress.update>` method.

        :note:
            No further progress information is returned after push returns.

        :param kill_after_timeout:
            To specify a timeout in seconds for the git command, after which the process
            should be killed. It is set to ``None`` by default.

        :param allow_unsafe_protocols:
            Allow unsafe protocols to be used, like ``ext``.

        :param allow_unsafe_options:
            Allow unsafe options to be used, like ``--receive-pack``.

        :param kwargs:
            Additional arguments to be passed to :manpage:`git-push(1)`.

        :return:
            A :class:`PushInfoList` object, where each list member represents an
            individual head which had been updated on the remote side.

            If the push contains rejected heads, these will have the
            :const:`PushInfo.ERROR` bit set in their flags.

            If the operation fails completely, the length of the returned
            :class:`PushInfoList` will be 0.

            Call :meth:`~PushInfoList.raise_if_error` on the returned object to raise on
            any failure.
        """
        kwargs = add_progress(kwargs, self.repo.git, progress)

        refspec = Git._unpack_args(refspec or [])
        if not allow_unsafe_protocols:
            for ref in refspec:
                Git.check_unsafe_protocols(ref)

        if not allow_unsafe_options:
            Git.check_unsafe_options(options=list(kwargs.keys()), unsafe_options=self.unsafe_git_push_options)

        proc = self.repo.git.push(
            "--",
            self,
            refspec,
            porcelain=True,
            as_process=True,
            universal_newlines=True,
            kill_after_timeout=kill_after_timeout,
            **kwargs,
        )
        return self._get_push_info(proc, progress, kill_after_timeout=kill_after_timeout)

    @property
    def config_reader(self) -> SectionConstraint[GitConfigParser]:
        """
        :return:
            :class:`~git.config.GitConfigParser` compatible object able to read options
            for only our remote. Hence you may simply type ``config.get("pushurl")`` to
            obtain the information.
        """
        return self._config_reader

    def _clear_cache(self) -> None:
        try:
            del self._config_reader
        except AttributeError:
            pass
        # END handle exception

    @property
    def config_writer(self) -> SectionConstraint:
        """
        :return:
            :class:`~git.config.GitConfigParser`-compatible object able to write options
            for this remote.

        :note:
            You can only own one writer at a time - delete it to release the
            configuration file and make it usable by others.

            To assure consistent results, you should only query options through the
            writer. Once you are done writing, you are free to use the config reader
            once again.
        """
        writer = self.repo.config_writer()

        # Clear our cache to ensure we re-read the possibly changed configuration.
        self._clear_cache()
        return SectionConstraint(writer, self._config_section_name())

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\lib\prompt_utils.py ===
# -*- coding: utf-8 -*-
# Copyright 2023 Google LLC
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
"""Utilities for processing prompts."""
from __future__ import annotations

import string
from typing import AbstractSet


def get_placeholders(prompt: str) -> AbstractSet[str]:
    """Returns the placeholders for `prompt`.

    E.g. Given "A for {word_one} B for {word_two}", returns {"word_one",
    "word_two"}.

    Args:
      prompt: A prompt template with optional placeholders.

    Returns:
      A sequence of placeholders in `prompt`.
    """
    placeholders: list[str] = []
    for _, field_name, _, _ in string.Formatter().parse(prompt):
        if field_name is not None:
            placeholders.append(field_name)
    return frozenset(placeholders)

# === NexusCore/openenv\Lib\site-packages\parso\python\tree.py ===
"""
This is the syntax tree for Python 3 syntaxes. The classes represent
syntax elements like functions and imports.

All of the nodes can be traced back to the `Python grammar file
<https://docs.python.org/3/reference/grammar.html>`_. If you want to know how
a tree is structured, just analyse that file (for each Python version it's a
bit different).

There's a lot of logic here that makes it easier for Jedi (and other libraries)
to deal with a Python syntax tree.

By using :py:meth:`parso.tree.NodeOrLeaf.get_code` on a module, you can get
back the 1-to-1 representation of the input given to the parser. This is
important if you want to refactor a parser tree.

>>> from parso import parse
>>> parser = parse('import os')
>>> module = parser.get_root_node()
>>> module
<Module: @1-1>

Any subclasses of :class:`Scope`, including :class:`Module` has an attribute
:attr:`iter_imports <Scope.iter_imports>`:

>>> list(module.iter_imports())
[<ImportName: import os@1,0>]

Changes to the Python Grammar
-----------------------------

A few things have changed when looking at Python grammar files:

- :class:`Param` does not exist in Python grammar files. It is essentially a
  part of a ``parameters`` node.  |parso| splits it up to make it easier to
  analyse parameters. However this just makes it easier to deal with the syntax
  tree, it doesn't actually change the valid syntax.
- A few nodes like `lambdef` and `lambdef_nocond` have been merged in the
  syntax tree to make it easier to do deal with them.

Parser Tree Classes
-------------------
"""

import re
try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping
from typing import Tuple

from parso.tree import Node, BaseNode, Leaf, ErrorNode, ErrorLeaf, search_ancestor  # noqa
from parso.python.prefix import split_prefix
from parso.utils import split_lines

_FLOW_CONTAINERS = set(['if_stmt', 'while_stmt', 'for_stmt', 'try_stmt',
                        'with_stmt', 'async_stmt', 'suite'])
_RETURN_STMT_CONTAINERS = set(['suite', 'simple_stmt']) | _FLOW_CONTAINERS

_FUNC_CONTAINERS = set(
    ['suite', 'simple_stmt', 'decorated', 'async_funcdef']
) | _FLOW_CONTAINERS

_GET_DEFINITION_TYPES = set([
    'expr_stmt', 'sync_comp_for', 'with_stmt', 'for_stmt', 'import_name',
    'import_from', 'param', 'del_stmt', 'namedexpr_test',
])
_IMPORTS = set(['import_name', 'import_from'])


class DocstringMixin:
    __slots__ = ()

    def get_doc_node(self):
        """
        Returns the string leaf of a docstring. e.g. ``r'''foo'''``.
        """
        if self.type == 'file_input':
            node = self.children[0]
        elif self.type in ('funcdef', 'classdef'):
            node = self.children[self.children.index(':') + 1]
            if node.type == 'suite':  # Normally a suite
                node = node.children[1]  # -> NEWLINE stmt
        else:  # ExprStmt
            simple_stmt = self.parent
            c = simple_stmt.parent.children
            index = c.index(simple_stmt)
            if not index:
                return None
            node = c[index - 1]

        if node.type == 'simple_stmt':
            node = node.children[0]
        if node.type == 'string':
            return node
        return None


class PythonMixin:
    """
    Some Python specific utilities.
    """
    __slots__ = ()

    def get_name_of_position(self, position):
        """
        Given a (line, column) tuple, returns a :py:class:`Name` or ``None`` if
        there is no name at that position.
        """
        for c in self.children:
            if isinstance(c, Leaf):
                if c.type == 'name' and c.start_pos <= position <= c.end_pos:
                    return c
            else:
                result = c.get_name_of_position(position)
                if result is not None:
                    return result
        return None


class PythonLeaf(PythonMixin, Leaf):
    __slots__ = ()

    def _split_prefix(self):
        return split_prefix(self, self.get_start_pos_of_prefix())

    def get_start_pos_of_prefix(self):
        """
        Basically calls :py:meth:`parso.tree.NodeOrLeaf.get_start_pos_of_prefix`.
        """
        # TODO it is really ugly that we have to override it. Maybe change
        #   indent error leafs somehow? No idea how, though.
        previous_leaf = self.get_previous_leaf()
        if previous_leaf is not None and previous_leaf.type == 'error_leaf' \
                and previous_leaf.token_type in ('INDENT', 'DEDENT', 'ERROR_DEDENT'):
            previous_leaf = previous_leaf.get_previous_leaf()

        if previous_leaf is None:  # It's the first leaf.
            lines = split_lines(self.prefix)
            # + 1 is needed because split_lines always returns at least [''].
            return self.line - len(lines) + 1, 0  # It's the first leaf.
        return previous_leaf.end_pos


class _LeafWithoutNewlines(PythonLeaf):
    """
    Simply here to optimize performance.
    """
    __slots__ = ()

    @property
    def end_pos(self) -> Tuple[int, int]:
        return self.line, self.column + len(self.value)


# Python base classes
class PythonBaseNode(PythonMixin, BaseNode):
    __slots__ = ()


class PythonNode(PythonMixin, Node):
    __slots__ = ()


class PythonErrorNode(PythonMixin, ErrorNode):
    __slots__ = ()


class PythonErrorLeaf(ErrorLeaf, PythonLeaf):
    __slots__ = ()


class EndMarker(_LeafWithoutNewlines):
    __slots__ = ()
    type = 'endmarker'

    def __repr__(self):
        return "<%s: prefix=%s end_pos=%s>" % (
            type(self).__name__, repr(self.prefix), self.end_pos
        )


class Newline(PythonLeaf):
    """Contains NEWLINE and ENDMARKER tokens."""
    __slots__ = ()
    type = 'newline'

    def __repr__(self):
        return "<%s: %s>" % (type(self).__name__, repr(self.value))


class Name(_LeafWithoutNewlines):
    """
    A string. Sometimes it is important to know if the string belongs to a name
    or not.
    """
    type = 'name'
    __slots__ = ()

    def __repr__(self):
        return "<%s: %s@%s,%s>" % (type(self).__name__, self.value,
                                   self.line, self.column)

    def is_definition(self, include_setitem=False):
        """
        Returns True if the name is being defined.
        """
        return self.get_definition(include_setitem=include_setitem) is not None

    def get_definition(self, import_name_always=False, include_setitem=False):
        """
        Returns None if there's no definition for a name.

        :param import_name_always: Specifies if an import name is always a
            definition. Normally foo in `from foo import bar` is not a
            definition.
        """
        node = self.parent
        type_ = node.type

        if type_ in ('funcdef', 'classdef'):
            if self == node.name:
                return node
            return None

        if type_ == 'except_clause':
            if self.get_previous_sibling() == 'as':
                return node.parent  # The try_stmt.
            return None

        while node is not None:
            if node.type == 'suite':
                return None
            if node.type in _GET_DEFINITION_TYPES:
                if self in node.get_defined_names(include_setitem):
                    return node
                if import_name_always and node.type in _IMPORTS:
                    return node
                return None
            node = node.parent
        return None


class Literal(PythonLeaf):
    __slots__ = ()


class Number(Literal):
    type = 'number'
    __slots__ = ()


class String(Literal):
    type = 'string'
    __slots__ = ()

    @property
    def string_prefix(self):
        return re.match(r'\w*(?=[\'"])', self.value).group(0)

    def _get_payload(self):
        match = re.search(
            r'''('{3}|"{3}|'|")(.*)$''',
            self.value,
            flags=re.DOTALL
        )
        return match.group(2)[:-len(match.group(1))]


class FStringString(PythonLeaf):
    """
    f-strings contain f-string expressions and normal python strings. These are
    the string parts of f-strings.
    """
    type = 'fstring_string'
    __slots__ = ()


class FStringStart(PythonLeaf):
    """
    f-strings contain f-string expressions and normal python strings. These are
    the string parts of f-strings.
    """
    type = 'fstring_start'
    __slots__ = ()


class FStringEnd(PythonLeaf):
    """
    f-strings contain f-string expressions and normal python strings. These are
    the string parts of f-strings.
    """
    type = 'fstring_end'
    __slots__ = ()


class _StringComparisonMixin:
    __slots__ = ()

    def __eq__(self, other):
        """
        Make comparisons with strings easy.
        Improves the readability of the parser.
        """
        if isinstance(other, str):
            return self.value == other

        return self is other

    def __hash__(self):
        return hash(self.value)


class Operator(_LeafWithoutNewlines, _StringComparisonMixin):
    type = 'operator'
    __slots__ = ()


class Keyword(_LeafWithoutNewlines, _StringComparisonMixin):
    type = 'keyword'
    __slots__ = ()


class Scope(PythonBaseNode, DocstringMixin):
    """
    Super class for the parser tree, which represents the state of a python
    text file.
    A Scope is either a function, class or lambda.
    """
    __slots__ = ()

    def __init__(self, children):
        super().__init__(children)

    def iter_funcdefs(self):
        """
        Returns a generator of `funcdef` nodes.
        """
        return self._search_in_scope('funcdef')

    def iter_classdefs(self):
        """
        Returns a generator of `classdef` nodes.
        """
        return self._search_in_scope('classdef')

    def iter_imports(self):
        """
        Returns a generator of `import_name` and `import_from` nodes.
        """
        return self._search_in_scope('import_name', 'import_from')

    def _search_in_scope(self, *names):
        def scan(children):
            for element in children:
                if element.type in names:
                    yield element
                if element.type in _FUNC_CONTAINERS:
                    yield from scan(element.children)

        return scan(self.children)

    def get_suite(self):
        """
        Returns the part that is executed by the function.
        """
        return self.children[-1]

    def __repr__(self):
        try:
            name = self.name.value
        except AttributeError:
            name = ''

        return "<%s: %s@%s-%s>" % (type(self).__name__, name,
                                   self.start_pos[0], self.end_pos[0])


class Module(Scope):
    """
    The top scope, which is always a module.
    Depending on the underlying parser this may be a full module or just a part
    of a module.
    """
    __slots__ = ('_used_names',)
    type = 'file_input'

    def __init__(self, children):
        super().__init__(children)
        self._used_names = None

    def _iter_future_import_names(self):
        """
        :return: A list of future import names.
        :rtype: list of str
        """
        # In Python it's not allowed to use future imports after the first
        # actual (non-future) statement. However this is not a linter here,
        # just return all future imports. If people want to scan for issues
        # they should use the API.
        for imp in self.iter_imports():
            if imp.type == 'import_from' and imp.level == 0:
                for path in imp.get_paths():
                    names = [name.value for name in path]
                    if len(names) == 2 and names[0] == '__future__':
                        yield names[1]

    def get_used_names(self):
        """
        Returns all the :class:`Name` leafs that exist in this module. This
        includes both definitions and references of names.
        """
        if self._used_names is None:
            # Don't directly use self._used_names to eliminate a lookup.
            dct = {}

            def recurse(node):
                try:
                    children = node.children
                except AttributeError:
                    if node.type == 'name':
                        arr = dct.setdefault(node.value, [])
                        arr.append(node)
                else:
                    for child in children:
                        recurse(child)

            recurse(self)
            self._used_names = UsedNamesMapping(dct)
        return self._used_names


class Decorator(PythonBaseNode):
    type = 'decorator'
    __slots__ = ()


class ClassOrFunc(Scope):
    __slots__ = ()

    @property
    def name(self):
        """
        Returns the `Name` leaf that defines the function or class name.
        """
        return self.children[1]

    def get_decorators(self):
        """
        :rtype: list of :class:`Decorator`
        """
        decorated = self.parent
        if decorated.type == 'async_funcdef':
            decorated = decorated.parent

        if decorated.type == 'decorated':
            if decorated.children[0].type == 'decorators':
                return decorated.children[0].children
            else:
                return decorated.children[:1]
        else:
            return []


class Class(ClassOrFunc):
    """
    Used to store the parsed contents of a python class.
    """
    type = 'classdef'
    __slots__ = ()

    def __init__(self, children):
        super().__init__(children)

    def get_super_arglist(self):
        """
        Returns the `arglist` node that defines the super classes. It returns
        None if there are no arguments.
        """
        if self.children[2] != '(':  # Has no parentheses
            return None
        else:
            if self.children[3] == ')':  # Empty parentheses
                return None
            else:
                return self.children[3]


def _create_params(parent, argslist_list):
    """
    `argslist_list` is a list that can contain an argslist as a first item, but
    most not. It's basically the items between the parameter brackets (which is
    at most one item).
    This function modifies the parser structure. It generates `Param` objects
    from the normal ast. Those param objects do not exist in a normal ast, but
    make the evaluation of the ast tree so much easier.
    You could also say that this function replaces the argslist node with a
    list of Param objects.
    """
    try:
        first = argslist_list[0]
    except IndexError:
        return []

    if first.type in ('name', 'fpdef'):
        return [Param([first], parent)]
    elif first == '*':
        return [first]
    else:  # argslist is a `typedargslist` or a `varargslist`.
        if first.type == 'tfpdef':
            children = [first]
        else:
            children = first.children
        new_children = []
        start = 0
        # Start with offset 1, because the end is higher.
        for end, child in enumerate(children + [None], 1):
            if child is None or child == ',':
                param_children = children[start:end]
                if param_children:  # Could as well be comma and then end.
                    if param_children[0] == '*' \
                            and (len(param_children) == 1
                                 or param_children[1] == ',') \
                            or param_children[0] == '/':
                        for p in param_children:
                            p.parent = parent
                        new_children += param_children
                    else:
                        new_children.append(Param(param_children, parent))
                    start = end
        return new_children


class Function(ClassOrFunc):
    """
    Used to store the parsed contents of a python function.

    Children::

        0. <Keyword: def>
        1. <Name>
        2. parameter list (including open-paren and close-paren <Operator>s)
        3. or 5. <Operator: :>
        4. or 6. Node() representing function body
        3. -> (if annotation is also present)
        4. annotation (if present)
    """
    type = 'funcdef'
    __slots__ = ()

    def __init__(self, children):
        super().__init__(children)
        parameters = self.children[2]  # After `def foo`
        parameters_children = parameters.children[1:-1]
        # If input parameters list already has Param objects, keep it as is;
        # otherwise, convert it to a list of Param objects.
        if not any(isinstance(child, Param) for child in parameters_children):
            parameters.children[1:-1] = _create_params(parameters, parameters_children)

    def _get_param_nodes(self):
        return self.children[2].children

    def get_params(self):
        """
        Returns a list of `Param()`.
        """
        return [p for p in self._get_param_nodes() if p.type == 'param']

    @property
    def name(self):
        return self.children[1]  # First token after `def`

    def iter_yield_exprs(self):
        """
        Returns a generator of `yield_expr`.
        """
        def scan(children):
            for element in children:
                if element.type in ('classdef', 'funcdef', 'lambdef'):
                    continue

                try:
                    nested_children = element.children
                except AttributeError:
                    if element.value == 'yield':
                        if element.parent.type == 'yield_expr':
                            yield element.parent
                        else:
                            yield element
                else:
                    yield from scan(nested_children)

        return scan(self.children)

    def iter_return_stmts(self):
        """
        Returns a generator of `return_stmt`.
        """
        def scan(children):
            for element in children:
                if element.type == 'return_stmt' \
                        or element.type == 'keyword' and element.value == 'return':
                    yield element
                if element.type in _RETURN_STMT_CONTAINERS:
                    yield from scan(element.children)

        return scan(self.children)

    def iter_raise_stmts(self):
        """
        Returns a generator of `raise_stmt`. Includes raise statements inside try-except blocks
        """
        def scan(children):
            for element in children:
                if element.type == 'raise_stmt' \
                        or element.type == 'keyword' and element.value == 'raise':
                    yield element
                if element.type in _RETURN_STMT_CONTAINERS:
                    yield from scan(element.children)

        return scan(self.children)

    def is_generator(self):
        """
        :return bool: Checks if a function is a generator or not.
        """
        return next(self.iter_yield_exprs(), None) is not None

    @property
    def annotation(self):
        """
        Returns the test node after `->` or `None` if there is no annotation.
        """
        try:
            if self.children[3] == "->":
                return self.children[4]
            assert self.children[3] == ":"
            return None
        except IndexError:
            return None


class Lambda(Function):
    """
    Lambdas are basically trimmed functions, so give it the same interface.

    Children::

         0. <Keyword: lambda>
         *. <Param x> for each argument x
        -2. <Operator: :>
        -1. Node() representing body
    """
    type = 'lambdef'
    __slots__ = ()

    def __init__(self, children):
        # We don't want to call the Function constructor, call its parent.
        super(Function, self).__init__(children)
        # Everything between `lambda` and the `:` operator is a parameter.
        parameters_children = self.children[1:-2]
        # If input children list already has Param objects, keep it as is;
        # otherwise, convert it to a list of Param objects.
        if not any(isinstance(child, Param) for child in parameters_children):
            self.children[1:-2] = _create_params(self, parameters_children)

    @property
    def name(self):
        """
        Raises an AttributeError. Lambdas don't have a defined name.
        """
        raise AttributeError("lambda is not named.")

    def _get_param_nodes(self):
        return self.children[1:-2]

    @property
    def annotation(self):
        """
        Returns `None`, lambdas don't have annotations.
        """
        return None

    def __repr__(self):
        return "<%s@%s>" % (self.__class__.__name__, self.start_pos)


class Flow(PythonBaseNode):
    __slots__ = ()


class IfStmt(Flow):
    type = 'if_stmt'
    __slots__ = ()

    def get_test_nodes(self):
        """
        E.g. returns all the `test` nodes that are named as x, below:

            if x:
                pass
            elif x:
                pass
        """
        for i, c in enumerate(self.children):
            if c in ('elif', 'if'):
                yield self.children[i + 1]

    def get_corresponding_test_node(self, node):
        """
        Searches for the branch in which the node is and returns the
        corresponding test node (see function above). However if the node is in
        the test node itself and not in the suite return None.
        """
        start_pos = node.start_pos
        for check_node in reversed(list(self.get_test_nodes())):
            if check_node.start_pos < start_pos:
                if start_pos < check_node.end_pos:
                    return None
                    # In this case the node is within the check_node itself,
                    # not in the suite
                else:
                    return check_node

    def is_node_after_else(self, node):
        """
        Checks if a node is defined after `else`.
        """
        for c in self.children:
            if c == 'else':
                if node.start_pos > c.start_pos:
                    return True
        else:
            return False


class WhileStmt(Flow):
    type = 'while_stmt'
    __slots__ = ()


class ForStmt(Flow):
    type = 'for_stmt'
    __slots__ = ()

    def get_testlist(self):
        """
        Returns the input node ``y`` from: ``for x in y:``.
        """
        return self.children[3]

    def get_defined_names(self, include_setitem=False):
        return _defined_names(self.children[1], include_setitem)


class TryStmt(Flow):
    type = 'try_stmt'
    __slots__ = ()

    def get_except_clause_tests(self):
        """
        Returns the ``test`` nodes found in ``except_clause`` nodes.
        Returns ``[None]`` for except clauses without an exception given.
        """
        for node in self.children:
            if node.type == 'except_clause':
                yield node.children[1]
            elif node == 'except':
                yield None


class WithStmt(Flow):
    type = 'with_stmt'
    __slots__ = ()

    def get_defined_names(self, include_setitem=False):
        """
        Returns the a list of `Name` that the with statement defines. The
        defined names are set after `as`.
        """
        names = []
        for with_item in self.children[1:-2:2]:
            # Check with items for 'as' names.
            if with_item.type == 'with_item':
                names += _defined_names(with_item.children[2], include_setitem)
        return names

    def get_test_node_from_name(self, name):
        node = name.search_ancestor("with_item")
        if node is None:
            raise ValueError('The name is not actually part of a with statement.')
        return node.children[0]


class Import(PythonBaseNode):
    __slots__ = ()

    def get_path_for_name(self, name):
        """
        The path is the list of names that leads to the searched name.

        :return list of Name:
        """
        try:
            # The name may be an alias. If it is, just map it back to the name.
            name = self._aliases()[name]
        except KeyError:
            pass

        for path in self.get_paths():
            if name in path:
                return path[:path.index(name) + 1]
        raise ValueError('Name should be defined in the import itself')

    def is_nested(self):
        return False  # By default, sub classes may overwrite this behavior

    def is_star_import(self):
        return self.children[-1] == '*'


class ImportFrom(Import):
    type = 'import_from'
    __slots__ = ()

    def get_defined_names(self, include_setitem=False):
        """
        Returns the a list of `Name` that the import defines. The
        defined names are set after `import` or in case an alias - `as` - is
        present that name is returned.
        """
        return [alias or name for name, alias in self._as_name_tuples()]

    def _aliases(self):
        """Mapping from alias to its corresponding name."""
        return dict((alias, name) for name, alias in self._as_name_tuples()
                    if alias is not None)

    def get_from_names(self):
        for n in self.children[1:]:
            if n not in ('.', '...'):
                break
        if n.type == 'dotted_name':  # from x.y import
            return n.children[::2]
        elif n == 'import':  # from . import
            return []
        else:  # from x import
            return [n]

    @property
    def level(self):
        """The level parameter of ``__import__``."""
        level = 0
        for n in self.children[1:]:
            if n in ('.', '...'):
                level += len(n.value)
            else:
                break
        return level

    def _as_name_tuples(self):
        last = self.children[-1]
        if last == ')':
            last = self.children[-2]
        elif last == '*':
            return  # No names defined directly.

        if last.type == 'import_as_names':
            as_names = last.children[::2]
        else:
            as_names = [last]
        for as_name in as_names:
            if as_name.type == 'name':
                yield as_name, None
            else:
                yield as_name.children[::2]  # yields x, y -> ``x as y``

    def get_paths(self):
        """
        The import paths defined in an import statement. Typically an array
        like this: ``[<Name: datetime>, <Name: date>]``.

        :return list of list of Name:
        """
        dotted = self.get_from_names()

        if self.children[-1] == '*':
            return [dotted]
        return [dotted + [name] for name, alias in self._as_name_tuples()]


class ImportName(Import):
    """For ``import_name`` nodes. Covers normal imports without ``from``."""
    type = 'import_name'
    __slots__ = ()

    def get_defined_names(self, include_setitem=False):
        """
        Returns the a list of `Name` that the import defines. The defined names
        is always the first name after `import` or in case an alias - `as` - is
        present that name is returned.
        """
        return [alias or path[0] for path, alias in self._dotted_as_names()]

    @property
    def level(self):
        """The level parameter of ``__import__``."""
        return 0  # Obviously 0 for imports without from.

    def get_paths(self):
        return [path for path, alias in self._dotted_as_names()]

    def _dotted_as_names(self):
        """Generator of (list(path), alias) where alias may be None."""
        dotted_as_names = self.children[1]
        if dotted_as_names.type == 'dotted_as_names':
            as_names = dotted_as_names.children[::2]
        else:
            as_names = [dotted_as_names]

        for as_name in as_names:
            if as_name.type == 'dotted_as_name':
                alias = as_name.children[2]
                as_name = as_name.children[0]
            else:
                alias = None
            if as_name.type == 'name':
                yield [as_name], alias
            else:
                # dotted_names
                yield as_name.children[::2], alias

    def is_nested(self):
        """
        This checks for the special case of nested imports, without aliases and
        from statement::

            import foo.bar
        """
        return bool([1 for path, alias in self._dotted_as_names()
                    if alias is None and len(path) > 1])

    def _aliases(self):
        """
        :return list of Name: Returns all the alias
        """
        return dict((alias, path[-1]) for path, alias in self._dotted_as_names()
                    if alias is not None)


class KeywordStatement(PythonBaseNode):
    """
    For the following statements: `assert`, `del`, `global`, `nonlocal`,
    `raise`, `return`, `yield`.

    `pass`, `continue` and `break` are not in there, because they are just
    simple keywords and the parser reduces it to a keyword.
    """
    __slots__ = ()

    @property
    def type(self):
        """
        Keyword statements start with the keyword and end with `_stmt`. You can
        crosscheck this with the Python grammar.
        """
        return '%s_stmt' % self.keyword

    @property
    def keyword(self):
        return self.children[0].value

    def get_defined_names(self, include_setitem=False):
        keyword = self.keyword
        if keyword == 'del':
            return _defined_names(self.children[1], include_setitem)
        if keyword in ('global', 'nonlocal'):
            return self.children[1::2]
        return []


class AssertStmt(KeywordStatement):
    __slots__ = ()

    @property
    def assertion(self):
        return self.children[1]


class GlobalStmt(KeywordStatement):
    __slots__ = ()

    def get_global_names(self):
        return self.children[1::2]


class ReturnStmt(KeywordStatement):
    __slots__ = ()


class YieldExpr(PythonBaseNode):
    type = 'yield_expr'
    __slots__ = ()


def _defined_names(current, include_setitem):
    """
    A helper function to find the defined names in statements, for loops and
    list comprehensions.
    """
    names = []
    if current.type in ('testlist_star_expr', 'testlist_comp', 'exprlist', 'testlist'):
        for child in current.children[::2]:
            names += _defined_names(child, include_setitem)
    elif current.type in ('atom', 'star_expr'):
        names += _defined_names(current.children[1], include_setitem)
    elif current.type in ('power', 'atom_expr'):
        if current.children[-2] != '**':  # Just if there's no operation
            trailer = current.children[-1]
            if trailer.children[0] == '.':
                names.append(trailer.children[1])
            elif trailer.children[0] == '[' and include_setitem:
                for node in current.children[-2::-1]:
                    if node.type == 'trailer':
                        names.append(node.children[1])
                        break
                    if node.type == 'name':
                        names.append(node)
                        break
    else:
        names.append(current)
    return names


class ExprStmt(PythonBaseNode, DocstringMixin):
    type = 'expr_stmt'
    __slots__ = ()

    def get_defined_names(self, include_setitem=False):
        """
        Returns a list of `Name` defined before the `=` sign.
        """
        names = []
        if self.children[1].type == 'annassign':
            names = _defined_names(self.children[0], include_setitem)
        return [
            name
            for i in range(0, len(self.children) - 2, 2)
            if '=' in self.children[i + 1].value
            for name in _defined_names(self.children[i], include_setitem)
        ] + names

    def get_rhs(self):
        """Returns the right-hand-side of the equals."""
        node = self.children[-1]
        if node.type == 'annassign':
            if len(node.children) == 4:
                node = node.children[3]
            else:
                node = node.children[1]
        return node

    def yield_operators(self):
        """
        Returns a generator of `+=`, `=`, etc. or None if there is no operation.
        """
        first = self.children[1]
        if first.type == 'annassign':
            if len(first.children) <= 2:
                return  # No operator is available, it's just PEP 484.

            first = first.children[2]
        yield first

        yield from self.children[3::2]


class NamedExpr(PythonBaseNode):
    type = 'namedexpr_test'

    def get_defined_names(self, include_setitem=False):
        return _defined_names(self.children[0], include_setitem)


class Param(PythonBaseNode):
    """
    It's a helper class that makes business logic with params much easier. The
    Python grammar defines no ``param`` node. It defines it in a different way
    that is not really suited to working with parameters.
    """
    type = 'param'

    def __init__(self, children, parent=None):
        super().__init__(children)
        self.parent = parent

    @property
    def star_count(self):
        """
        Is `0` in case of `foo`, `1` in case of `*foo` or `2` in case of
        `**foo`.
        """
        first = self.children[0]
        if first in ('*', '**'):
            return len(first.value)
        return 0

    @property
    def default(self):
        """
        The default is the test node that appears after the `=`. Is `None` in
        case no default is present.
        """
        has_comma = self.children[-1] == ','
        try:
            if self.children[-2 - int(has_comma)] == '=':
                return self.children[-1 - int(has_comma)]
        except IndexError:
            return None

    @property
    def annotation(self):
        """
        The default is the test node that appears after `:`. Is `None` in case
        no annotation is present.
        """
        tfpdef = self._tfpdef()
        if tfpdef.type == 'tfpdef':
            assert tfpdef.children[1] == ":"
            assert len(tfpdef.children) == 3
            annotation = tfpdef.children[2]
            return annotation
        else:
            return None

    def _tfpdef(self):
        """
        tfpdef: see e.g. grammar36.txt.
        """
        offset = int(self.children[0] in ('*', '**'))
        return self.children[offset]

    @property
    def name(self):
        """
        The `Name` leaf of the param.
        """
        if self._tfpdef().type == 'tfpdef':
            return self._tfpdef().children[0]
        else:
            return self._tfpdef()

    def get_defined_names(self, include_setitem=False):
        return [self.name]

    @property
    def position_index(self):
        """
        Property for the positional index of a paramter.
        """
        index = self.parent.children.index(self)
        try:
            keyword_only_index = self.parent.children.index('*')
            if index > keyword_only_index:
                # Skip the ` *, `
                index -= 2
        except ValueError:
            pass
        try:
            keyword_only_index = self.parent.children.index('/')
            if index > keyword_only_index:
                # Skip the ` /, `
                index -= 2
        except ValueError:
            pass
        return index - 1

    def get_parent_function(self):
        """
        Returns the function/lambda of a parameter.
        """
        return self.search_ancestor('funcdef', 'lambdef')

    def get_code(self, include_prefix=True, include_comma=True):
        """
        Like all the other get_code functions, but includes the param
        `include_comma`.

        :param include_comma bool: If enabled includes the comma in the string output.
        """
        if include_comma:
            return super().get_code(include_prefix)

        children = self.children
        if children[-1] == ',':
            children = children[:-1]
        return self._get_code_for_children(
            children,
            include_prefix=include_prefix
        )

    def __repr__(self):
        default = '' if self.default is None else '=%s' % self.default.get_code()
        return '<%s: %s>' % (type(self).__name__, str(self._tfpdef()) + default)


class SyncCompFor(PythonBaseNode):
    type = 'sync_comp_for'
    __slots__ = ()

    def get_defined_names(self, include_setitem=False):
        """
        Returns the a list of `Name` that the comprehension defines.
        """
        # allow async for
        return _defined_names(self.children[1], include_setitem)


# This is simply here so an older Jedi version can work with this new parso
# version. Can be deleted in the next release.
CompFor = SyncCompFor


class UsedNamesMapping(Mapping):
    """
    This class exists for the sole purpose of creating an immutable dict.
    """
    def __init__(self, dct):
        self._dict = dct

    def __getitem__(self, key):
        return self._dict[key]

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        # Comparing these dicts does not make sense.
        return self is other

# === NexusCore/openenv\Lib\site-packages\joblib\memory.py ===
"""
A context object for caching a function's return value each time it
is called with the same input arguments.

"""

# Author: Gael Varoquaux <gael dot varoquaux at normalesup dot org>
# Copyright (c) 2009 Gael Varoquaux
# License: BSD Style, 3 clauses.

import asyncio
import datetime
import functools
import inspect
import logging
import os
import pathlib
import pydoc
import re
import textwrap
import time
import tokenize
import traceback
import warnings
import weakref

from . import hashing
from ._store_backends import (
    CacheWarning,  # noqa
    FileSystemStoreBackend,
    StoreBackendBase,
)
from .func_inspect import (
    filter_args,
    format_call,
    format_signature,
    get_func_code,
    get_func_name,
)
from .logger import Logger, format_time, pformat

FIRST_LINE_TEXT = "# first line:"

# TODO: The following object should have a data store object as a sub
# object, and the interface to persist and query should be separated in
# the data store.
#
# This would enable creating 'Memory' objects with a different logic for
# pickling that would simply span a MemorizedFunc with the same
# store (or do we want to copy it to avoid cross-talks?), for instance to
# implement HDF5 pickling.

# TODO: Same remark for the logger, and probably use the Python logging
# mechanism.


def extract_first_line(func_code):
    """Extract the first line information from the function code
    text if available.
    """
    if func_code.startswith(FIRST_LINE_TEXT):
        func_code = func_code.split("\n")
        first_line = int(func_code[0][len(FIRST_LINE_TEXT) :])
        func_code = "\n".join(func_code[1:])
    else:
        first_line = -1
    return func_code, first_line


class JobLibCollisionWarning(UserWarning):
    """Warn that there might be a collision between names of functions."""


_STORE_BACKENDS = {"local": FileSystemStoreBackend}


def register_store_backend(backend_name, backend):
    """Extend available store backends.

    The Memory, MemorizeResult and MemorizeFunc objects are designed to be
    agnostic to the type of store used behind. By default, the local file
    system is used but this function gives the possibility to extend joblib's
    memory pattern with other types of storage such as cloud storage (S3, GCS,
    OpenStack, HadoopFS, etc) or blob DBs.

    Parameters
    ----------
    backend_name: str
        The name identifying the store backend being registered. For example,
        'local' is used with FileSystemStoreBackend.
    backend: StoreBackendBase subclass
        The name of a class that implements the StoreBackendBase interface.

    """
    if not isinstance(backend_name, str):
        raise ValueError(
            "Store backend name should be a string, '{0}' given.".format(backend_name)
        )
    if backend is None or not issubclass(backend, StoreBackendBase):
        raise ValueError(
            "Store backend should inherit StoreBackendBase, '{0}' given.".format(
                backend
            )
        )

    _STORE_BACKENDS[backend_name] = backend


def _store_backend_factory(backend, location, verbose=0, backend_options=None):
    """Return the correct store object for the given location."""
    if backend_options is None:
        backend_options = {}

    if isinstance(location, pathlib.Path):
        location = str(location)

    if isinstance(location, StoreBackendBase):
        return location
    elif isinstance(location, str):
        obj = None
        location = os.path.expanduser(location)
        # The location is not a local file system, we look in the
        # registered backends if there's one matching the given backend
        # name.
        for backend_key, backend_obj in _STORE_BACKENDS.items():
            if backend == backend_key:
                obj = backend_obj()

        # By default, we assume the FileSystemStoreBackend can be used if no
        # matching backend could be found.
        if obj is None:
            raise TypeError(
                "Unknown location {0} or backend {1}".format(location, backend)
            )

        # The store backend is configured with the extra named parameters,
        # some of them are specific to the underlying store backend.
        obj.configure(location, verbose=verbose, backend_options=backend_options)
        return obj
    elif location is not None:
        warnings.warn(
            "Instantiating a backend using a {} as a location is not "
            "supported by joblib. Returning None instead.".format(
                location.__class__.__name__
            ),
            UserWarning,
        )

    return None


def _build_func_identifier(func):
    """Build a roughly unique identifier for the cached function."""
    modules, funcname = get_func_name(func)
    # We reuse historical fs-like way of building a function identifier
    return os.path.join(*modules, funcname)


# An in-memory store to avoid looking at the disk-based function
# source code to check if a function definition has changed
_FUNCTION_HASHES = weakref.WeakKeyDictionary()


###############################################################################
# class `MemorizedResult`
###############################################################################
class MemorizedResult(Logger):
    """Object representing a cached value.

    Attributes
    ----------
    location: str
        The location of joblib cache. Depends on the store backend used.

    func: function or str
        function whose output is cached. The string case is intended only for
        instantiation based on the output of repr() on another instance.
        (namely eval(repr(memorized_instance)) works).

    argument_hash: str
        hash of the function arguments.

    backend: str
        Type of store backend for reading/writing cache files.
        Default is 'local'.

    mmap_mode: {None, 'r+', 'r', 'w+', 'c'}
        The memmapping mode used when loading from cache numpy arrays. See
        numpy.load for the meaning of the different values.

    verbose: int
        verbosity level (0 means no message).

    timestamp, metadata: string
        for internal use only.
    """

    def __init__(
        self,
        location,
        call_id,
        backend="local",
        mmap_mode=None,
        verbose=0,
        timestamp=None,
        metadata=None,
    ):
        Logger.__init__(self)
        self._call_id = call_id
        self.store_backend = _store_backend_factory(backend, location, verbose=verbose)
        self.mmap_mode = mmap_mode

        if metadata is not None:
            self.metadata = metadata
        else:
            self.metadata = self.store_backend.get_metadata(self._call_id)

        self.duration = self.metadata.get("duration", None)
        self.verbose = verbose
        self.timestamp = timestamp

    @property
    def func(self):
        return self.func_id

    @property
    def func_id(self):
        return self._call_id[0]

    @property
    def args_id(self):
        return self._call_id[1]

    def get(self):
        """Read value from cache and return it."""
        try:
            return self.store_backend.load_item(
                self._call_id,
                timestamp=self.timestamp,
                metadata=self.metadata,
                verbose=self.verbose,
            )
        except ValueError as exc:
            new_exc = KeyError(
                "Error while trying to load a MemorizedResult's value. "
                "It seems that this folder is corrupted : {}".format(
                    os.path.join(self.store_backend.location, *self._call_id)
                )
            )
            raise new_exc from exc

    def clear(self):
        """Clear value from cache"""
        self.store_backend.clear_item(self._call_id)

    def __repr__(self):
        return '{}(location="{}", func="{}", args_id="{}")'.format(
            self.__class__.__name__, self.store_backend.location, *self._call_id
        )

    def __getstate__(self):
        state = self.__dict__.copy()
        state["timestamp"] = None
        return state


class NotMemorizedResult(object):
    """Class representing an arbitrary value.

    This class is a replacement for MemorizedResult when there is no cache.
    """

    __slots__ = ("value", "valid")

    def __init__(self, value):
        self.value = value
        self.valid = True

    def get(self):
        if self.valid:
            return self.value
        else:
            raise KeyError("No value stored.")

    def clear(self):
        self.valid = False
        self.value = None

    def __repr__(self):
        if self.valid:
            return "{class_name}({value})".format(
                class_name=self.__class__.__name__, value=pformat(self.value)
            )
        else:
            return self.__class__.__name__ + " with no value"

    # __getstate__ and __setstate__ are required because of __slots__
    def __getstate__(self):
        return {"valid": self.valid, "value": self.value}

    def __setstate__(self, state):
        self.valid = state["valid"]
        self.value = state["value"]


###############################################################################
# class `NotMemorizedFunc`
###############################################################################
class NotMemorizedFunc(object):
    """No-op object decorating a function.

    This class replaces MemorizedFunc when there is no cache. It provides an
    identical API but does not write anything on disk.

    Attributes
    ----------
    func: callable
        Original undecorated function.
    """

    # Should be a light as possible (for speed)
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def call_and_shelve(self, *args, **kwargs):
        return NotMemorizedResult(self.func(*args, **kwargs))

    def __repr__(self):
        return "{0}(func={1})".format(self.__class__.__name__, self.func)

    def clear(self, warn=True):
        # Argument "warn" is for compatibility with MemorizedFunc.clear
        pass

    def call(self, *args, **kwargs):
        return self.func(*args, **kwargs), {}

    def check_call_in_cache(self, *args, **kwargs):
        return False


###############################################################################
# class `AsyncNotMemorizedFunc`
###############################################################################
class AsyncNotMemorizedFunc(NotMemorizedFunc):
    async def call_and_shelve(self, *args, **kwargs):
        return NotMemorizedResult(await self.func(*args, **kwargs))


###############################################################################
# class `MemorizedFunc`
###############################################################################
class MemorizedFunc(Logger):
    """Callable object decorating a function for caching its return value
    each time it is called.

    Methods are provided to inspect the cache or clean it.

    Attributes
    ----------
    func: callable
        The original, undecorated, function.

    location: string
        The location of joblib cache. Depends on the store backend used.

    backend: str
        Type of store backend for reading/writing cache files.
        Default is 'local', in which case the location is the path to a
        disk storage.

    ignore: list or None
        List of variable names to ignore when choosing whether to
        recompute.

    mmap_mode: {None, 'r+', 'r', 'w+', 'c'}
        The memmapping mode used when loading from cache
        numpy arrays. See numpy.load for the meaning of the different
        values.

    compress: boolean, or integer
        Whether to zip the stored data on disk. If an integer is
        given, it should be between 1 and 9, and sets the amount
        of compression. Note that compressed arrays cannot be
        read by memmapping.

    verbose: int, optional
        The verbosity flag, controls messages that are issued as
        the function is evaluated.

    cache_validation_callback: callable, optional
        Callable to check if a result in cache is valid or is to be recomputed.
        When the function is called with arguments for which a cache exists,
        the callback is called with the cache entry's metadata as its sole
        argument. If it returns True, the cached result is returned, else the
        cache for these arguments is cleared and the result is recomputed.
    """

    # ------------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------------

    def __init__(
        self,
        func,
        location,
        backend="local",
        ignore=None,
        mmap_mode=None,
        compress=False,
        verbose=1,
        timestamp=None,
        cache_validation_callback=None,
    ):
        Logger.__init__(self)
        self.mmap_mode = mmap_mode
        self.compress = compress
        self.func = func
        self.cache_validation_callback = cache_validation_callback
        self.func_id = _build_func_identifier(func)
        self.ignore = ignore if ignore is not None else []
        self._verbose = verbose

        # retrieve store object from backend type and location.
        self.store_backend = _store_backend_factory(
            backend,
            location,
            verbose=verbose,
            backend_options=dict(compress=compress, mmap_mode=mmap_mode),
        )
        if self.store_backend is not None:
            # Create func directory on demand.
            self.store_backend.store_cached_func_code([self.func_id])

        self.timestamp = timestamp if timestamp is not None else time.time()
        try:
            functools.update_wrapper(self, func)
        except Exception:
            pass  # Objects like ufunc don't like that
        if inspect.isfunction(func):
            doc = pydoc.TextDoc().document(func)
            # Remove blank line
            doc = doc.replace("\n", "\n\n", 1)
            # Strip backspace-overprints for compatibility with autodoc
            doc = re.sub("\x08.", "", doc)
        else:
            # Pydoc does a poor job on other objects
            doc = func.__doc__
        self.__doc__ = "Memoized version of %s" % doc

        self._func_code_info = None
        self._func_code_id = None

    def _is_in_cache_and_valid(self, call_id):
        """Check if the function call is cached and valid for given arguments.

        - Compare the function code with the one from the cached function,
        asserting if it has changed.
        - Check if the function call is present in the cache.
        - Call `cache_validation_callback` for user define cache validation.

        Returns True if the function call is in cache and can be used, and
        returns False otherwise.
        """
        # Check if the code of the function has changed
        if not self._check_previous_func_code(stacklevel=4):
            return False

        # Check if this specific call is in the cache
        if not self.store_backend.contains_item(call_id):
            return False

        # Call the user defined cache validation callback
        metadata = self.store_backend.get_metadata(call_id)
        if (
            self.cache_validation_callback is not None
            and not self.cache_validation_callback(metadata)
        ):
            self.store_backend.clear_item(call_id)
            return False

        return True

    def _cached_call(self, args, kwargs, shelving):
        """Call wrapped function and cache result, or read cache if available.

        This function returns the wrapped function output or a reference to
        the cached result.

        Arguments:
        ----------

        args, kwargs: list and dict
            input arguments for wrapped function

        shelving: bool
            True when called via the call_and_shelve function.


        Returns
        -------
        output: Output of the wrapped function if shelving is false, or a
            MemorizedResult reference to the value if shelving is true.
        metadata: dict containing the metadata associated with the call.
        """
        args_id = self._get_args_id(*args, **kwargs)
        call_id = (self.func_id, args_id)
        _, func_name = get_func_name(self.func)
        func_info = self.store_backend.get_cached_func_info([self.func_id])
        location = func_info["location"]

        if self._verbose >= 20:
            logging.basicConfig(level=logging.INFO)
            _, signature = format_signature(self.func, *args, **kwargs)
            self.info(
                textwrap.dedent(
                    f"""
                        Querying {func_name} with signature
                        {signature}.

                        (argument hash {args_id})

                        The store location is {location}.
                        """
                )
            )

        # Compare the function code with the previous to see if the
        # function code has changed and check if the results are present in
        # the cache.
        if self._is_in_cache_and_valid(call_id):
            if shelving:
                return self._get_memorized_result(call_id), {}

            try:
                start_time = time.time()
                output = self._load_item(call_id)
                if self._verbose > 4:
                    self._print_duration(
                        time.time() - start_time, context="cache loaded "
                    )
                return output, {}
            except Exception:
                # XXX: Should use an exception logger
                _, signature = format_signature(self.func, *args, **kwargs)
                self.warn(
                    "Exception while loading results for {}\n {}".format(
                        signature, traceback.format_exc()
                    )
                )

        if self._verbose > 10:
            self.warn(
                f"Computing func {func_name}, argument hash {args_id} "
                f"in location {location}"
            )

        # Returns the output but not the metadata
        return self._call(call_id, args, kwargs, shelving)

    @property
    def func_code_info(self):
        # 3-tuple property containing: the function source code, source file,
        # and first line of the code inside the source file
        if hasattr(self.func, "__code__"):
            if self._func_code_id is None:
                self._func_code_id = id(self.func.__code__)
            elif id(self.func.__code__) != self._func_code_id:
                # Be robust to dynamic reassignments of self.func.__code__
                self._func_code_info = None

        if self._func_code_info is None:
            # Cache the source code of self.func . Provided that get_func_code
            # (which should be called once on self) gets called in the process
            # in which self.func was defined, this caching mechanism prevents
            # undesired cache clearing when the cached function is called in
            # an environment where the introspection utilities get_func_code
            # relies on do not work (typically, in joblib child processes).
            # See #1035 for  more info
            # TODO (pierreglaser): do the same with get_func_name?
            self._func_code_info = get_func_code(self.func)
        return self._func_code_info

    def call_and_shelve(self, *args, **kwargs):
        """Call wrapped function, cache result and return a reference.

        This method returns a reference to the cached result instead of the
        result itself. The reference object is small and picklable, allowing
        to send or store it easily. Call .get() on reference object to get
        result.

        Returns
        -------
        cached_result: MemorizedResult or NotMemorizedResult
            reference to the value returned by the wrapped function. The
            class "NotMemorizedResult" is used when there is no cache
            activated (e.g. location=None in Memory).
        """
        # Return the wrapped output, without the metadata
        return self._cached_call(args, kwargs, shelving=True)[0]

    def __call__(self, *args, **kwargs):
        # Return the output, without the metadata
        return self._cached_call(args, kwargs, shelving=False)[0]

    def __getstate__(self):
        # Make sure self.func's source is introspected prior to being pickled -
        # code introspection utilities typically do not work inside child
        # processes
        _ = self.func_code_info

        # We don't store the timestamp when pickling, to avoid the hash
        # depending from it.
        state = self.__dict__.copy()
        state["timestamp"] = None

        # Invalidate the code id as id(obj) will be different in the child
        state["_func_code_id"] = None

        return state

    def check_call_in_cache(self, *args, **kwargs):
        """Check if the function call is cached and valid for given arguments.

        Does not call the function or do any work besides function inspection
        and argument hashing.

        - Compare the function code with the one from the cached function,
          asserting if it has changed.
        - Check if the function call is present in the cache.
        - Call `cache_validation_callback` for user define cache validation.

        Returns
        -------
        is_call_in_cache: bool
            Whether or not the function call is in cache and can be used.
        """
        call_id = (self.func_id, self._get_args_id(*args, **kwargs))
        return self._is_in_cache_and_valid(call_id)

    # ------------------------------------------------------------------------
    # Private interface
    # ------------------------------------------------------------------------

    def _get_args_id(self, *args, **kwargs):
        """Return the input parameter hash of a result."""
        return hashing.hash(
            filter_args(self.func, self.ignore, args, kwargs),
            coerce_mmap=self.mmap_mode is not None,
        )

    def _hash_func(self):
        """Hash a function to key the online cache"""
        func_code_h = hash(getattr(self.func, "__code__", None))
        return id(self.func), hash(self.func), func_code_h

    def _write_func_code(self, func_code, first_line):
        """Write the function code and the filename to a file."""
        # We store the first line because the filename and the function
        # name is not always enough to identify a function: people
        # sometimes have several functions named the same way in a
        # file. This is bad practice, but joblib should be robust to bad
        # practice.
        func_code = "%s %i\n%s" % (FIRST_LINE_TEXT, first_line, func_code)
        self.store_backend.store_cached_func_code([self.func_id], func_code)

        # Also store in the in-memory store of function hashes
        is_named_callable = (
            hasattr(self.func, "__name__") and self.func.__name__ != "<lambda>"
        )
        if is_named_callable:
            # Don't do this for lambda functions or strange callable
            # objects, as it ends up being too fragile
            func_hash = self._hash_func()
            try:
                _FUNCTION_HASHES[self.func] = func_hash
            except TypeError:
                # Some callable are not hashable
                pass

    def _check_previous_func_code(self, stacklevel=2):
        """
        stacklevel is the depth a which this function is called, to
        issue useful warnings to the user.
        """
        # First check if our function is in the in-memory store.
        # Using the in-memory store not only makes things faster, but it
        # also renders us robust to variations of the files when the
        # in-memory version of the code does not vary
        try:
            if self.func in _FUNCTION_HASHES:
                # We use as an identifier the id of the function and its
                # hash. This is more likely to falsely change than have hash
                # collisions, thus we are on the safe side.
                func_hash = self._hash_func()
                if func_hash == _FUNCTION_HASHES[self.func]:
                    return True
        except TypeError:
            # Some callables are not hashable
            pass

        # Here, we go through some effort to be robust to dynamically
        # changing code and collision. We cannot inspect.getsource
        # because it is not reliable when using IPython's magic "%run".
        func_code, source_file, first_line = self.func_code_info
        try:
            old_func_code, old_first_line = extract_first_line(
                self.store_backend.get_cached_func_code([self.func_id])
            )
        except (IOError, OSError):  # some backend can also raise OSError
            self._write_func_code(func_code, first_line)
            return False
        if old_func_code == func_code:
            return True

        # We have differing code, is this because we are referring to
        # different functions, or because the function we are referring to has
        # changed?

        _, func_name = get_func_name(
            self.func, resolv_alias=False, win_characters=False
        )
        if old_first_line == first_line == -1 or func_name == "<lambda>":
            if not first_line == -1:
                func_description = "{0} ({1}:{2})".format(
                    func_name, source_file, first_line
                )
            else:
                func_description = func_name
            warnings.warn(
                JobLibCollisionWarning(
                    "Cannot detect name collisions for function '{0}'".format(
                        func_description
                    )
                ),
                stacklevel=stacklevel,
            )

        # Fetch the code at the old location and compare it. If it is the
        # same than the code store, we have a collision: the code in the
        # file has not changed, but the name we have is pointing to a new
        # code block.
        if not old_first_line == first_line and source_file is not None:
            if os.path.exists(source_file):
                _, func_name = get_func_name(self.func, resolv_alias=False)
                num_lines = len(func_code.split("\n"))
                with tokenize.open(source_file) as f:
                    on_disk_func_code = f.readlines()[
                        old_first_line - 1 : old_first_line - 1 + num_lines - 1
                    ]
                on_disk_func_code = "".join(on_disk_func_code)
                possible_collision = (
                    on_disk_func_code.rstrip() == old_func_code.rstrip()
                )
            else:
                possible_collision = source_file.startswith("<doctest ")
            if possible_collision:
                warnings.warn(
                    JobLibCollisionWarning(
                        "Possible name collisions between functions "
                        "'%s' (%s:%i) and '%s' (%s:%i)"
                        % (
                            func_name,
                            source_file,
                            old_first_line,
                            func_name,
                            source_file,
                            first_line,
                        )
                    ),
                    stacklevel=stacklevel,
                )

        # The function has changed, wipe the cache directory.
        # XXX: Should be using warnings, and giving stacklevel
        if self._verbose > 10:
            _, func_name = get_func_name(self.func, resolv_alias=False)
            self.warn(
                "Function {0} (identified by {1}) has changed.".format(
                    func_name, self.func_id
                )
            )
        self.clear(warn=True)
        return False

    def clear(self, warn=True):
        """Empty the function's cache."""
        func_id = self.func_id
        if self._verbose > 0 and warn:
            self.warn("Clearing function cache identified by %s" % func_id)
        self.store_backend.clear_path(
            [
                func_id,
            ]
        )

        func_code, _, first_line = self.func_code_info
        self._write_func_code(func_code, first_line)

    def call(self, *args, **kwargs):
        """Force the execution of the function with the given arguments.

        The output values will be persisted, i.e., the cache will be updated
        with any new values.

        Parameters
        ----------
        *args: arguments
            The arguments.
        **kwargs: keyword arguments
            Keyword arguments.

        Returns
        -------
        output : object
            The output of the function call.
        metadata : dict
            The metadata associated with the call.
        """
        call_id = (self.func_id, self._get_args_id(*args, **kwargs))

        # Return the output and the metadata
        return self._call(call_id, args, kwargs)

    def _call(self, call_id, args, kwargs, shelving=False):
        # Return the output and the metadata
        self._before_call(args, kwargs)
        start_time = time.time()
        output = self.func(*args, **kwargs)
        return self._after_call(call_id, args, kwargs, shelving, output, start_time)

    def _before_call(self, args, kwargs):
        if self._verbose > 0:
            print(format_call(self.func, args, kwargs))

    def _after_call(self, call_id, args, kwargs, shelving, output, start_time):
        self.store_backend.dump_item(call_id, output, verbose=self._verbose)
        duration = time.time() - start_time
        if self._verbose > 0:
            self._print_duration(duration)
        metadata = self._persist_input(duration, call_id, args, kwargs)
        if shelving:
            return self._get_memorized_result(call_id, metadata), metadata

        if self.mmap_mode is not None:
            # Memmap the output at the first call to be consistent with
            # later calls
            output = self._load_item(call_id, metadata)
        return output, metadata

    def _persist_input(self, duration, call_id, args, kwargs, this_duration_limit=0.5):
        """Save a small summary of the call using json format in the
        output directory.

        output_dir: string
            directory where to write metadata.

        duration: float
            time taken by hashing input arguments, calling the wrapped
            function and persisting its output.

        args, kwargs: list and dict
            input arguments for wrapped function

        this_duration_limit: float
            Max execution time for this function before issuing a warning.
        """
        start_time = time.time()
        argument_dict = filter_args(self.func, self.ignore, args, kwargs)

        input_repr = dict((k, repr(v)) for k, v in argument_dict.items())
        # This can fail due to race-conditions with multiple
        # concurrent joblibs removing the file or the directory
        metadata = {
            "duration": duration,
            "input_args": input_repr,
            "time": start_time,
        }

        self.store_backend.store_metadata(call_id, metadata)

        this_duration = time.time() - start_time
        if this_duration > this_duration_limit:
            # This persistence should be fast. It will not be if repr() takes
            # time and its output is large, because json.dump will have to
            # write a large file. This should not be an issue with numpy arrays
            # for which repr() always output a short representation, but can
            # be with complex dictionaries. Fixing the problem should be a
            # matter of replacing repr() above by something smarter.
            warnings.warn(
                "Persisting input arguments took %.2fs to run."
                "If this happens often in your code, it can cause "
                "performance problems "
                "(results will be correct in all cases). "
                "The reason for this is probably some large input "
                "arguments for a wrapped function." % this_duration,
                stacklevel=5,
            )
        return metadata

    def _get_memorized_result(self, call_id, metadata=None):
        return MemorizedResult(
            self.store_backend,
            call_id,
            metadata=metadata,
            timestamp=self.timestamp,
            verbose=self._verbose - 1,
        )

    def _load_item(self, call_id, metadata=None):
        return self.store_backend.load_item(
            call_id, metadata=metadata, timestamp=self.timestamp, verbose=self._verbose
        )

    def _print_duration(self, duration, context=""):
        _, name = get_func_name(self.func)
        msg = f"{name} {context}- {format_time(duration)}"
        print(max(0, (80 - len(msg))) * "_" + msg)

    # ------------------------------------------------------------------------
    # Private `object` interface
    # ------------------------------------------------------------------------

    def __repr__(self):
        return "{class_name}(func={func}, location={location})".format(
            class_name=self.__class__.__name__,
            func=self.func,
            location=self.store_backend.location,
        )


###############################################################################
# class `AsyncMemorizedFunc`
###############################################################################
class AsyncMemorizedFunc(MemorizedFunc):
    async def __call__(self, *args, **kwargs):
        out = self._cached_call(args, kwargs, shelving=False)
        out = await out if asyncio.iscoroutine(out) else out
        return out[0]  # Don't return metadata

    async def call_and_shelve(self, *args, **kwargs):
        out = self._cached_call(args, kwargs, shelving=True)
        out = await out if asyncio.iscoroutine(out) else out
        return out[0]  # Don't return metadata

    async def call(self, *args, **kwargs):
        out = super().call(*args, **kwargs)
        return await out if asyncio.iscoroutine(out) else out

    async def _call(self, call_id, args, kwargs, shelving=False):
        self._before_call(args, kwargs)
        start_time = time.time()
        output = await self.func(*args, **kwargs)
        return self._after_call(call_id, args, kwargs, shelving, output, start_time)


###############################################################################
# class `Memory`
###############################################################################
class Memory(Logger):
    """A context object for caching a function's return value each time it
    is called with the same input arguments.

    All values are cached on the filesystem, in a deep directory
    structure.

    Read more in the :ref:`User Guide <memory>`.

    Parameters
    ----------
    location: str, pathlib.Path or None
        The path of the base directory to use as a data store
        or None. If None is given, no caching is done and
        the Memory object is completely transparent. This option
        replaces cachedir since version 0.12.

    backend: str, optional, default='local'
        Type of store backend for reading/writing cache files.
        The 'local' backend is using regular filesystem operations to
        manipulate data (open, mv, etc) in the backend.

    mmap_mode: {None, 'r+', 'r', 'w+', 'c'}, optional
        The memmapping mode used when loading from cache
        numpy arrays. See numpy.load for the meaning of the
        arguments.

    compress: boolean, or integer, optional
        Whether to zip the stored data on disk. If an integer is
        given, it should be between 1 and 9, and sets the amount
        of compression. Note that compressed arrays cannot be
        read by memmapping.

    verbose: int, optional
        Verbosity flag, controls the debug messages that are issued
        as functions are evaluated.

    backend_options: dict, optional
        Contains a dictionary of named parameters used to configure
        the store backend.
    """

    # ------------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------------

    def __init__(
        self,
        location=None,
        backend="local",
        mmap_mode=None,
        compress=False,
        verbose=1,
        backend_options=None,
    ):
        Logger.__init__(self)
        self._verbose = verbose
        self.mmap_mode = mmap_mode
        self.timestamp = time.time()
        self.backend = backend
        self.compress = compress
        if backend_options is None:
            backend_options = {}
        self.backend_options = backend_options

        if compress and mmap_mode is not None:
            warnings.warn("Compressed results cannot be memmapped", stacklevel=2)

        self.location = location
        if isinstance(location, str):
            location = os.path.join(location, "joblib")

        self.store_backend = _store_backend_factory(
            backend,
            location,
            verbose=self._verbose,
            backend_options=dict(
                compress=compress, mmap_mode=mmap_mode, **backend_options
            ),
        )

    def cache(
        self,
        func=None,
        ignore=None,
        verbose=None,
        mmap_mode=False,
        cache_validation_callback=None,
    ):
        """Decorates the given function func to only compute its return
        value for input arguments not cached on disk.

        Parameters
        ----------
        func: callable, optional
            The function to be decorated
        ignore: list of strings
            A list of arguments name to ignore in the hashing
        verbose: integer, optional
            The verbosity mode of the function. By default that
            of the memory object is used.
        mmap_mode: {None, 'r+', 'r', 'w+', 'c'}, optional
            The memmapping mode used when loading from cache
            numpy arrays. See numpy.load for the meaning of the
            arguments. By default that of the memory object is used.
        cache_validation_callback: callable, optional
            Callable to validate whether or not the cache is valid. When
            the cached function is called with arguments for which a cache
            exists, this callable is called with the metadata of the cached
            result as its sole argument. If it returns True, then the
            cached result is returned, else the cache for these arguments
            is cleared and recomputed.

        Returns
        -------
        decorated_func: MemorizedFunc object
            The returned object is a MemorizedFunc object, that is
            callable (behaves like a function), but offers extra
            methods for cache lookup and management. See the
            documentation for :class:`joblib.memory.MemorizedFunc`.
        """
        if cache_validation_callback is not None and not callable(
            cache_validation_callback
        ):
            raise ValueError(
                "cache_validation_callback needs to be callable. "
                f"Got {cache_validation_callback}."
            )
        if func is None:
            # Partial application, to be able to specify extra keyword
            # arguments in decorators
            return functools.partial(
                self.cache,
                ignore=ignore,
                mmap_mode=mmap_mode,
                verbose=verbose,
                cache_validation_callback=cache_validation_callback,
            )
        if self.store_backend is None:
            cls = (
                AsyncNotMemorizedFunc
                if asyncio.iscoroutinefunction(func)
                else NotMemorizedFunc
            )
            return cls(func)
        if verbose is None:
            verbose = self._verbose
        if mmap_mode is False:
            mmap_mode = self.mmap_mode
        if isinstance(func, MemorizedFunc):
            func = func.func
        cls = AsyncMemorizedFunc if asyncio.iscoroutinefunction(func) else MemorizedFunc
        return cls(
            func,
            location=self.store_backend,
            backend=self.backend,
            ignore=ignore,
            mmap_mode=mmap_mode,
            compress=self.compress,
            verbose=verbose,
            timestamp=self.timestamp,
            cache_validation_callback=cache_validation_callback,
        )

    def clear(self, warn=True):
        """Erase the complete cache directory."""
        if warn:
            self.warn("Flushing completely the cache")
        if self.store_backend is not None:
            self.store_backend.clear()

            # As the cache is completely clear, make sure the _FUNCTION_HASHES
            # cache is also reset. Else, for a function that is present in this
            # table, results cached after this clear will be have cache miss
            # as the function code is not re-written.
            _FUNCTION_HASHES.clear()

    def reduce_size(self, bytes_limit=None, items_limit=None, age_limit=None):
        """Remove cache elements to make the cache fit its limits.

        The limitation can impose that the cache size fits in ``bytes_limit``,
        that the number of cache items is no more than ``items_limit``, and
        that all files in cache are not older than ``age_limit``.

        Parameters
        ----------
        bytes_limit: int | str, optional
            Limit in bytes of the size of the cache. By default, the size of
            the cache is unlimited. When reducing the size of the cache,
            ``joblib`` keeps the most recently accessed items first. If a
            str is passed, it is converted to a number of bytes using units
            { K | M | G} for kilo, mega, giga.

        items_limit: int, optional
            Number of items to limit the cache to.  By default, the number of
            items in the cache is unlimited.  When reducing the size of the
            cache, ``joblib`` keeps the most recently accessed items first.

        age_limit: datetime.timedelta, optional
            Maximum age of items to limit the cache to.  When reducing the size
            of the cache, any items last accessed more than the given length of
            time ago are deleted. Example: to remove files older than 5 days,
            use datetime.timedelta(days=5). Negative timedelta are not
            accepted.
        """
        if self.store_backend is None:
            # No cached results, this function does nothing.
            return

        if bytes_limit is None and items_limit is None and age_limit is None:
            # No limitation to impose, returning
            return

        # Defers the actual limits enforcing to the store backend.
        self.store_backend.enforce_store_limits(bytes_limit, items_limit, age_limit)

    def eval(self, func, *args, **kwargs):
        """Eval function func with arguments `*args` and `**kwargs`,
        in the context of the memory.

        This method works similarly to the builtin `apply`, except
        that the function is called only if the cache is not
        up to date.

        """
        if self.store_backend is None:
            return func(*args, **kwargs)
        return self.cache(func)(*args, **kwargs)

    # ------------------------------------------------------------------------
    # Private `object` interface
    # ------------------------------------------------------------------------

    def __repr__(self):
        return "{class_name}(location={location})".format(
            class_name=self.__class__.__name__,
            location=(
                None if self.store_backend is None else self.store_backend.location
            ),
        )

    def __getstate__(self):
        """We don't store the timestamp when pickling, to avoid the hash
        depending from it.
        """
        state = self.__dict__.copy()
        state["timestamp"] = None
        return state


###############################################################################
# cache_validation_callback helpers
###############################################################################


def expires_after(
    days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0
):
    """Helper cache_validation_callback to force recompute after a duration.

    Parameters
    ----------
    days, seconds, microseconds, milliseconds, minutes, hours, weeks: numbers
        argument passed to a timedelta.
    """
    delta = datetime.timedelta(
        days=days,
        seconds=seconds,
        microseconds=microseconds,
        milliseconds=milliseconds,
        minutes=minutes,
        hours=hours,
        weeks=weeks,
    )

    def cache_validation_callback(metadata):
        computation_age = time.time() - metadata["time"]
        return computation_age < delta.total_seconds()

    return cache_validation_callback

# === NexusCore/openenv\Lib\site-packages\IPython\core\debugger.py ===
"""
Pdb debugger class.


This is an extension to PDB which adds a number of new features.
Note that there is also the `IPython.terminal.debugger` class which provides UI
improvements.

We also strongly recommend to use this via the `ipdb` package, which provides
extra configuration options.

Among other things, this subclass of PDB:
 - supports many IPython magics like pdef/psource
 - hide frames in tracebacks based on `__tracebackhide__`
 - allows to skip frames based on `__debuggerskip__`


Global Configuration
--------------------

The IPython debugger will by read the global ``~/.pdbrc`` file.
That is to say you can list all commands supported by ipdb in your `~/.pdbrc`
configuration file, to globally configure pdb.

Example::

   # ~/.pdbrc
   skip_predicates debuggerskip false
   skip_hidden false
   context 25

Features
--------

The IPython debugger can hide and skip frames when printing or moving through
the stack. This can have a performance impact, so can be configures.

The skipping and hiding frames are configurable via the `skip_predicates`
command.

By default, frames from readonly files will be hidden, frames containing
``__tracebackhide__ = True`` will be hidden.

Frames containing ``__debuggerskip__`` will be stepped over, frames whose parent
frames value of ``__debuggerskip__`` is ``True`` will also be skipped.

    >>> def helpers_helper():
    ...     pass
    ...
    ... def helper_1():
    ...     print("don't step in me")
    ...     helpers_helpers() # will be stepped over unless breakpoint set.
    ...
    ...
    ... def helper_2():
    ...     print("in me neither")
    ...

One can define a decorator that wraps a function between the two helpers:

    >>> def pdb_skipped_decorator(function):
    ...
    ...
    ...     def wrapped_fn(*args, **kwargs):
    ...         __debuggerskip__ = True
    ...         helper_1()
    ...         __debuggerskip__ = False
    ...         result = function(*args, **kwargs)
    ...         __debuggerskip__ = True
    ...         helper_2()
    ...         # setting __debuggerskip__ to False again is not necessary
    ...         return result
    ...
    ...     return wrapped_fn

When decorating a function, ipdb will directly step into ``bar()`` by
default:

    >>> @foo_decorator
    ... def bar(x, y):
    ...     return x * y


You can toggle the behavior with

    ipdb> skip_predicates debuggerskip false

or configure it in your ``.pdbrc``



License
-------

Modified from the standard pdb.Pdb class to avoid including readline, so that
the command line completion of other programs which include this isn't
damaged.

In the future, this class will be expanded with improvements over the standard
pdb.

The original code in this file is mainly lifted out of cmd.py in Python 2.2,
with minor changes. Licensing should therefore be under the standard Python
terms.  For details on the PSF (Python Software Foundation) standard license,
see:

https://docs.python.org/2/license.html


All the changes since then are under the same license as IPython.

"""

# *****************************************************************************
#
#       This file is licensed under the PSF license.
#
#       Copyright (C) 2001 Python Software Foundation, www.python.org
#       Copyright (C) 2005-2006 Fernando Perez. <fperez@colorado.edu>
#
#
# *****************************************************************************

from __future__ import annotations

import inspect
import linecache
import os
import re
import sys
import warnings
from contextlib import contextmanager
from functools import lru_cache

from IPython import get_ipython
from IPython.utils import PyColorize
from IPython.utils.PyColorize import TokenStream

from typing import TYPE_CHECKING
from types import FrameType

# We have to check this directly from sys.argv, config struct not yet available
from pdb import Pdb as OldPdb
from pygments.token import Token

if TYPE_CHECKING:
    # otherwise circular import
    from IPython.core.interactiveshell import InteractiveShell

# skip module docstests
__skip_doctest__ = True

prompt = "ipdb> "


# Allow the set_trace code to operate outside of an ipython instance, even if
# it does so with some limitations.  The rest of this support is implemented in
# the Tracer constructor.

DEBUGGERSKIP = "__debuggerskip__"


# this has been implemented in Pdb in Python 3.13 (https://github.com/python/cpython/pull/106676
# on lower python versions, we backported the feature.
CHAIN_EXCEPTIONS = sys.version_info < (3, 13)


def BdbQuit_excepthook(et, ev, tb, excepthook=None):
    """Exception hook which handles `BdbQuit` exceptions.

    All other exceptions are processed using the `excepthook`
    parameter.
    """
    raise ValueError(
        "`BdbQuit_excepthook` is deprecated since version 5.1. It is still around only because it is still imported by ipdb.",
    )


RGX_EXTRA_INDENT = re.compile(r"(?<=\n)\s+")


def strip_indentation(multiline_string):
    return RGX_EXTRA_INDENT.sub("", multiline_string)


def decorate_fn_with_doc(new_fn, old_fn, additional_text=""):
    """Make new_fn have old_fn's doc string. This is particularly useful
    for the ``do_...`` commands that hook into the help system.
    Adapted from from a comp.lang.python posting
    by Duncan Booth."""

    def wrapper(*args, **kw):
        return new_fn(*args, **kw)

    if old_fn.__doc__:
        wrapper.__doc__ = strip_indentation(old_fn.__doc__) + additional_text
    return wrapper


class Pdb(OldPdb):
    """Modified Pdb class, does not load readline.

    for a standalone version that uses prompt_toolkit, see
    `IPython.terminal.debugger.TerminalPdb` and
    `IPython.terminal.debugger.set_trace()`


    This debugger can hide and skip frames that are tagged according to some predicates.
    See the `skip_predicates` commands.

    """

    shell: InteractiveShell
    _theme_name: str
    _context: int

    _chained_exceptions: tuple[Exception, ...]
    _chained_exception_index: int

    if CHAIN_EXCEPTIONS:
        MAX_CHAINED_EXCEPTION_DEPTH = 999

    default_predicates = {
        "tbhide": True,
        "readonly": False,
        "ipython_internal": True,
        "debuggerskip": True,
    }

    def __init__(
        self,
        completekey=None,
        stdin=None,
        stdout=None,
        context: int | None | str = 5,
        **kwargs,
    ):
        """Create a new IPython debugger.

        Parameters
        ----------
        completekey : default None
            Passed to pdb.Pdb.
        stdin : default None
            Passed to pdb.Pdb.
        stdout : default None
            Passed to pdb.Pdb.
        context : int
            Number of lines of source code context to show when
            displaying stacktrace information.
        **kwargs
            Passed to pdb.Pdb.

        Notes
        -----
        The possibilities are python version dependent, see the python
        docs for more info.
        """
        # ipdb issue, see https://github.com/ipython/ipython/issues/14811
        if context is None:
            context = 5
        if isinstance(context, str):
            context = int(context)
        self.context = context

        # `kwargs` ensures full compatibility with stdlib's `pdb.Pdb`.
        OldPdb.__init__(self, completekey, stdin, stdout, **kwargs)

        # IPython changes...
        self.shell = get_ipython()

        if self.shell is None:
            save_main = sys.modules["__main__"]
            # No IPython instance running, we must create one
            from IPython.terminal.interactiveshell import TerminalInteractiveShell

            self.shell = TerminalInteractiveShell.instance()
            # needed by any code which calls __import__("__main__") after
            # the debugger was entered. See also #9941.
            sys.modules["__main__"] = save_main

        self.aliases = {}

        theme_name = self.shell.colors
        assert isinstance(theme_name, str)
        assert theme_name.lower() == theme_name

        # Add a python parser so we can syntax highlight source while
        # debugging.
        self.parser = PyColorize.Parser(theme_name=theme_name)
        self.set_theme_name(theme_name)

        # Set the prompt - the default prompt is '(Pdb)'
        self.prompt = prompt
        self.skip_hidden = True
        self.report_skipped = True

        # list of predicates we use to skip frames
        self._predicates = self.default_predicates

        if CHAIN_EXCEPTIONS:
            self._chained_exceptions = tuple()
            self._chained_exception_index = 0

    @property
    def context(self) -> int:
        return self._context

    @context.setter
    def context(self, value: int | str) -> None:
        # ipdb issue see https://github.com/ipython/ipython/issues/14811
        if not isinstance(value, int):
            value = int(value)
        assert isinstance(value, int)
        assert value >= 0
        self._context = value

    def set_theme_name(self, name):
        assert name.lower() == name
        assert isinstance(name, str)
        self._theme_name = name
        self.parser.theme_name = name

    @property
    def theme(self):
        return PyColorize.theme_table[self._theme_name]

    #
    def set_colors(self, scheme):
        """Shorthand access to the color table scheme selector method."""
        warnings.warn(
            "set_colors is deprecated since IPython 9.0, use set_theme_name instead",
            DeprecationWarning,
            stacklevel=2,
        )
        assert scheme == scheme.lower()
        self._theme_name = scheme.lower()
        self.parser.theme_name = scheme.lower()

    def set_trace(self, frame=None):
        if frame is None:
            frame = sys._getframe().f_back
        self.initial_frame = frame
        return super().set_trace(frame)

    def _hidden_predicate(self, frame):
        """
        Given a frame return whether it it should be hidden or not by IPython.
        """

        if self._predicates["readonly"]:
            fname = frame.f_code.co_filename
            # we need to check for file existence and interactively define
            # function would otherwise appear as RO.
            if os.path.isfile(fname) and not os.access(fname, os.W_OK):
                return True

        if self._predicates["tbhide"]:
            if frame in (self.curframe, getattr(self, "initial_frame", None)):
                return False
            frame_locals = self._get_frame_locals(frame)
            if "__tracebackhide__" not in frame_locals:
                return False
            return frame_locals["__tracebackhide__"]
        return False

    def hidden_frames(self, stack):
        """
        Given an index in the stack return whether it should be skipped.

        This is used in up/down and where to skip frames.
        """
        # The f_locals dictionary is updated from the actual frame
        # locals whenever the .f_locals accessor is called, so we
        # avoid calling it here to preserve self.curframe_locals.
        # Furthermore, there is no good reason to hide the current frame.
        ip_hide = [self._hidden_predicate(s[0]) for s in stack]
        ip_start = [i for i, s in enumerate(ip_hide) if s == "__ipython_bottom__"]
        if ip_start and self._predicates["ipython_internal"]:
            ip_hide = [h if i > ip_start[0] else True for (i, h) in enumerate(ip_hide)]
        return ip_hide

    if CHAIN_EXCEPTIONS:

        def _get_tb_and_exceptions(self, tb_or_exc):
            """
            Given a tracecack or an exception, return a tuple of chained exceptions
            and current traceback to inspect.
            This will deal with selecting the right ``__cause__`` or ``__context__``
            as well as handling cycles, and return a flattened list of exceptions we
            can jump to with do_exceptions.
            """
            _exceptions = []
            if isinstance(tb_or_exc, BaseException):
                traceback, current = tb_or_exc.__traceback__, tb_or_exc

                while current is not None:
                    if current in _exceptions:
                        break
                    _exceptions.append(current)
                    if current.__cause__ is not None:
                        current = current.__cause__
                    elif (
                        current.__context__ is not None
                        and not current.__suppress_context__
                    ):
                        current = current.__context__

                    if len(_exceptions) >= self.MAX_CHAINED_EXCEPTION_DEPTH:
                        self.message(
                            f"More than {self.MAX_CHAINED_EXCEPTION_DEPTH}"
                            " chained exceptions found, not all exceptions"
                            "will be browsable with `exceptions`."
                        )
                        break
            else:
                traceback = tb_or_exc
            return tuple(reversed(_exceptions)), traceback

        @contextmanager
        def _hold_exceptions(self, exceptions):
            """
            Context manager to ensure proper cleaning of exceptions references
            When given a chained exception instead of a traceback,
            pdb may hold references to many objects which may leak memory.
            We use this context manager to make sure everything is properly cleaned
            """
            try:
                self._chained_exceptions = exceptions
                self._chained_exception_index = len(exceptions) - 1
                yield
            finally:
                # we can't put those in forget as otherwise they would
                # be cleared on exception change
                self._chained_exceptions = tuple()
                self._chained_exception_index = 0

        def do_exceptions(self, arg):
            """exceptions [number]
            List or change current exception in an exception chain.
            Without arguments, list all the current exception in the exception
            chain. Exceptions will be numbered, with the current exception indicated
            with an arrow.
            If given an integer as argument, switch to the exception at that index.
            """
            if not self._chained_exceptions:
                self.message(
                    "Did not find chained exceptions. To move between"
                    " exceptions, pdb/post_mortem must be given an exception"
                    " object rather than a traceback."
                )
                return
            if not arg:
                for ix, exc in enumerate(self._chained_exceptions):
                    prompt = ">" if ix == self._chained_exception_index else " "
                    rep = repr(exc)
                    if len(rep) > 80:
                        rep = rep[:77] + "..."
                    indicator = (
                        "  -"
                        if self._chained_exceptions[ix].__traceback__ is None
                        else f"{ix:>3}"
                    )
                    self.message(f"{prompt} {indicator} {rep}")
            else:
                try:
                    number = int(arg)
                except ValueError:
                    self.error("Argument must be an integer")
                    return
                if 0 <= number < len(self._chained_exceptions):
                    if self._chained_exceptions[number].__traceback__ is None:
                        self.error(
                            "This exception does not have a traceback, cannot jump to it"
                        )
                        return

                    self._chained_exception_index = number
                    self.setup(None, self._chained_exceptions[number].__traceback__)
                    self.print_stack_entry(self.stack[self.curindex])
                else:
                    self.error("No exception with that number")

    def interaction(self, frame, tb_or_exc):
        try:
            if CHAIN_EXCEPTIONS:
                # this context manager is part of interaction in 3.13
                _chained_exceptions, tb = self._get_tb_and_exceptions(tb_or_exc)
                if isinstance(tb_or_exc, BaseException):
                    assert tb is not None, "main exception must have a traceback"
                with self._hold_exceptions(_chained_exceptions):
                    OldPdb.interaction(self, frame, tb)
            else:
                OldPdb.interaction(self, frame, tb_or_exc)

        except KeyboardInterrupt:
            self.stdout.write("\n" + self.shell.get_exception_only())

    def precmd(self, line):
        """Perform useful escapes on the command before it is executed."""

        if line.endswith("??"):
            line = "pinfo2 " + line[:-2]
        elif line.endswith("?"):
            line = "pinfo " + line[:-1]

        line = super().precmd(line)

        return line

    def new_do_quit(self, arg):
        return OldPdb.do_quit(self, arg)

    do_q = do_quit = decorate_fn_with_doc(new_do_quit, OldPdb.do_quit)

    def print_stack_trace(self, context: int | None = None):
        if context is None:
            context = self.context
        try:
            skipped = 0
            to_print = ""
            for hidden, frame_lineno in zip(self.hidden_frames(self.stack), self.stack):
                if hidden and self.skip_hidden:
                    skipped += 1
                    continue
                if skipped:
                    to_print += self.theme.format(
                        [
                            (
                                Token.ExcName,
                                f"    [... skipping {skipped} hidden frame(s)]",
                            ),
                            (Token, "\n"),
                        ]
                    )

                    skipped = 0
                to_print += self.format_stack_entry(frame_lineno)
            if skipped:
                to_print += self.theme.format(
                    [
                        (
                            Token.ExcName,
                            f"    [... skipping {skipped} hidden frame(s)]",
                        ),
                        (Token, "\n"),
                    ]
                )
            print(to_print, file=self.stdout)
        except KeyboardInterrupt:
            pass

    def print_stack_entry(
        self, frame_lineno: tuple[FrameType, int], prompt_prefix: str = "\n-> "
    ) -> None:
        """
        Overwrite print_stack_entry from superclass (PDB)
        """
        print(self.format_stack_entry(frame_lineno, ""), file=self.stdout)

        frame, lineno = frame_lineno
        filename = frame.f_code.co_filename
        self.shell.hooks.synchronize_with_editor(filename, lineno, 0)

    def _get_frame_locals(self, frame):
        """ "
        Accessing f_local of current frame reset the namespace, so we want to avoid
        that or the following can happen

        ipdb> foo
        "old"
        ipdb> foo = "new"
        ipdb> foo
        "new"
        ipdb> where
        ipdb> foo
        "old"

        So if frame is self.current_frame we instead return self.curframe_locals

        """
        if frame is getattr(self, "curframe", None):
            return self.curframe_locals
        else:
            return frame.f_locals

    def format_stack_entry(
        self,
        frame_lineno: tuple[FrameType, int],  # type: ignore[override] # stubs are wrong
        lprefix: str = ": ",
    ) -> str:
        """
        overwrite from super class so must -> str
        """
        context = self.context
        try:
            context = int(context)
            if context <= 0:
                print("Context must be a positive integer", file=self.stdout)
        except (TypeError, ValueError):
            print("Context must be a positive integer", file=self.stdout)

        import reprlib

        ret_tok = []

        frame, lineno = frame_lineno

        return_value = ""
        loc_frame = self._get_frame_locals(frame)
        if "__return__" in loc_frame:
            rv = loc_frame["__return__"]
            # return_value += '->'
            return_value += reprlib.repr(rv) + "\n"
            ret_tok.extend([(Token, return_value)])

        # s = filename + '(' + `lineno` + ')'
        filename = self.canonic(frame.f_code.co_filename)
        link_tok = (Token.FilenameEm, filename)

        if frame.f_code.co_name:
            func = frame.f_code.co_name
        else:
            func = "<lambda>"

        call_toks = []
        if func != "?":
            if "__args__" in loc_frame:
                args = reprlib.repr(loc_frame["__args__"])
            else:
                args = "()"
            call_toks = [(Token.VName, func), (Token.ValEm, args)]

        # The level info should be generated in the same format pdb uses, to
        # avoid breaking the pdbtrack functionality of python-mode in *emacs.
        if frame is self.curframe:
            ret_tok.append((Token.CurrentFrame, self.theme.make_arrow(2)))
        else:
            ret_tok.append((Token, "  "))

        ret_tok.extend(
            [
                link_tok,
                (Token, "("),
                (Token.Lineno, str(lineno)),
                (Token, ")"),
                *call_toks,
                (Token, "\n"),
            ]
        )

        start = lineno - 1 - context // 2
        lines = linecache.getlines(filename)
        start = min(start, len(lines) - context)
        start = max(start, 0)
        lines = lines[start : start + context]

        for i, line in enumerate(lines):
            show_arrow = start + 1 + i == lineno

            bp, num, colored_line = self.__line_content(
                filename,
                start + 1 + i,
                line,
                arrow=show_arrow,
            )
            if frame is self.curframe or show_arrow:
                rlt = [
                    bp,
                    (Token.LinenoEm, num),
                    (Token, " "),
                    # TODO: investigate Toke.Line here, likely LineEm,
                    # Token is problematic here as line is already colored, a
                    # and this changes the full style of the colored line.
                    # ideally, __line_content returns the token and we modify the style.
                    (Token, colored_line),
                ]
            else:
                rlt = [
                    bp,
                    (Token.Lineno, num),
                    (Token, " "),
                    # TODO: investigate Toke.Line here, likely Line
                    # Token is problematic here as line is already colored, a
                    # and this changes the full style of the colored line.
                    # ideally, __line_content returns the token and we modify the style.
                    (Token.Line, colored_line),
                ]
            ret_tok.extend(rlt)

        return self.theme.format(ret_tok)

    def __line_content(
        self, filename: str, lineno: int, line: str, arrow: bool = False
    ):
        bp_mark = ""
        BreakpointToken = Token.Breakpoint

        new_line, err = self.parser.format2(line, "str")
        if not err:
            line = new_line

        bp = None
        if lineno in self.get_file_breaks(filename):
            bps = self.get_breaks(filename, lineno)
            bp = bps[-1]

        if bp:
            bp_mark = str(bp.number)
            BreakpointToken = Token.Breakpoint.Enabled
            if not bp.enabled:
                BreakpointToken = Token.Breakpoint.Disabled
        numbers_width = 7
        if arrow:
            # This is the line with the error
            pad = numbers_width - len(str(lineno)) - len(bp_mark)
            num = "%s%s" % (self.theme.make_arrow(pad), str(lineno))
        else:
            num = "%*s" % (numbers_width - len(bp_mark), str(lineno))
        bp_str = (BreakpointToken, bp_mark)
        return (bp_str, num, line)

    def print_list_lines(self, filename: str, first: int, last: int) -> None:
        """The printing (as opposed to the parsing part of a 'list'
        command."""
        toks: TokenStream = []
        try:
            if filename == "<string>" and hasattr(self, "_exec_filename"):
                filename = self._exec_filename

            for lineno in range(first, last + 1):
                line = linecache.getline(filename, lineno)
                if not line:
                    break

                assert self.curframe is not None

                if lineno == self.curframe.f_lineno:
                    bp, num, colored_line = self.__line_content(
                        filename, lineno, line, arrow=True
                    )
                    toks.extend(
                        [
                            bp,
                            (Token.LinenoEm, num),
                            (Token, " "),
                            # TODO: invsetigate Toke.Line here
                            (Token, colored_line),
                        ]
                    )
                else:
                    bp, num, colored_line = self.__line_content(
                        filename, lineno, line, arrow=False
                    )
                    toks.extend(
                        [
                            bp,
                            (Token.Lineno, num),
                            (Token, " "),
                            (Token, colored_line),
                        ]
                    )

                self.lineno = lineno

            print(self.theme.format(toks), file=self.stdout)

        except KeyboardInterrupt:
            pass

    def do_skip_predicates(self, args):
        """
        Turn on/off individual predicates as to whether a frame should be hidden/skip.

        The global option to skip (or not) hidden frames is set with skip_hidden

        To change the value of a predicate

            skip_predicates key [true|false]

        Call without arguments to see the current values.

        To permanently change the value of an option add the corresponding
        command to your ``~/.pdbrc`` file. If you are programmatically using the
        Pdb instance you can also change the ``default_predicates`` class
        attribute.
        """
        if not args.strip():
            print("current predicates:")
            for p, v in self._predicates.items():
                print("   ", p, ":", v)
            return
        type_value = args.strip().split(" ")
        if len(type_value) != 2:
            print(
                f"Usage: skip_predicates <type> <value>, with <type> one of {set(self._predicates.keys())}"
            )
            return

        type_, value = type_value
        if type_ not in self._predicates:
            print(f"{type_!r} not in {set(self._predicates.keys())}")
            return
        if value.lower() not in ("true", "yes", "1", "no", "false", "0"):
            print(
                f"{value!r} is invalid - use one of ('true', 'yes', '1', 'no', 'false', '0')"
            )
            return

        self._predicates[type_] = value.lower() in ("true", "yes", "1")
        if not any(self._predicates.values()):
            print(
                "Warning, all predicates set to False, skip_hidden may not have any effects."
            )

    def do_skip_hidden(self, arg):
        """
        Change whether or not we should skip frames with the
        __tracebackhide__ attribute.
        """
        if not arg.strip():
            print(
                f"skip_hidden = {self.skip_hidden}, use 'yes','no', 'true', or 'false' to change."
            )
        elif arg.strip().lower() in ("true", "yes"):
            self.skip_hidden = True
        elif arg.strip().lower() in ("false", "no"):
            self.skip_hidden = False
        if not any(self._predicates.values()):
            print(
                "Warning, all predicates set to False, skip_hidden may not have any effects."
            )

    def do_list(self, arg):
        """Print lines of code from the current stack frame"""
        self.lastcmd = "list"
        last = None
        if arg and arg != ".":
            try:
                x = eval(arg, {}, {})
                if type(x) == type(()):
                    first, last = x
                    first = int(first)
                    last = int(last)
                    if last < first:
                        # Assume it's a count
                        last = first + last
                else:
                    first = max(1, int(x) - 5)
            except:
                print("*** Error in argument:", repr(arg), file=self.stdout)
                return
        elif self.lineno is None or arg == ".":
            assert self.curframe is not None
            first = max(1, self.curframe.f_lineno - 5)
        else:
            first = self.lineno + 1
        if last is None:
            last = first + 10
        assert self.curframe is not None
        self.print_list_lines(self.curframe.f_code.co_filename, first, last)

        lineno = first
        filename = self.curframe.f_code.co_filename
        self.shell.hooks.synchronize_with_editor(filename, lineno, 0)

    do_l = do_list

    def getsourcelines(self, obj):
        lines, lineno = inspect.findsource(obj)
        if inspect.isframe(obj) and obj.f_globals is self._get_frame_locals(obj):
            # must be a module frame: do not try to cut a block out of it
            return lines, 1
        elif inspect.ismodule(obj):
            return lines, 1
        return inspect.getblock(lines[lineno:]), lineno + 1

    def do_longlist(self, arg):
        """Print lines of code from the current stack frame.

        Shows more lines than 'list' does.
        """
        self.lastcmd = "longlist"
        try:
            lines, lineno = self.getsourcelines(self.curframe)
        except OSError as err:
            self.error(str(err))
            return
        last = lineno + len(lines)
        assert self.curframe is not None
        self.print_list_lines(self.curframe.f_code.co_filename, lineno, last)

    do_ll = do_longlist

    def do_debug(self, arg):
        """debug code
        Enter a recursive debugger that steps through the code
        argument (which is an arbitrary expression or statement to be
        executed in the current environment).
        """
        trace_function = sys.gettrace()
        sys.settrace(None)
        assert self.curframe is not None
        globals = self.curframe.f_globals
        locals = self.curframe_locals
        p = self.__class__(
            completekey=self.completekey, stdin=self.stdin, stdout=self.stdout
        )
        p.use_rawinput = self.use_rawinput
        p.prompt = "(%s) " % self.prompt.strip()
        self.message("ENTERING RECURSIVE DEBUGGER")
        sys.call_tracing(p.run, (arg, globals, locals))
        self.message("LEAVING RECURSIVE DEBUGGER")
        sys.settrace(trace_function)
        self.lastcmd = p.lastcmd

    def do_pdef(self, arg):
        """Print the call signature for any callable object.

        The debugger interface to %pdef"""
        assert self.curframe is not None
        namespaces = [
            ("Locals", self.curframe_locals),
            ("Globals", self.curframe.f_globals),
        ]
        self.shell.find_line_magic("pdef")(arg, namespaces=namespaces)

    def do_pdoc(self, arg):
        """Print the docstring for an object.

        The debugger interface to %pdoc."""
        assert self.curframe is not None
        namespaces = [
            ("Locals", self.curframe_locals),
            ("Globals", self.curframe.f_globals),
        ]
        self.shell.find_line_magic("pdoc")(arg, namespaces=namespaces)

    def do_pfile(self, arg):
        """Print (or run through pager) the file where an object is defined.

        The debugger interface to %pfile.
        """
        assert self.curframe is not None
        namespaces = [
            ("Locals", self.curframe_locals),
            ("Globals", self.curframe.f_globals),
        ]
        self.shell.find_line_magic("pfile")(arg, namespaces=namespaces)

    def do_pinfo(self, arg):
        """Provide detailed information about an object.

        The debugger interface to %pinfo, i.e., obj?."""
        assert self.curframe is not None
        namespaces = [
            ("Locals", self.curframe_locals),
            ("Globals", self.curframe.f_globals),
        ]
        self.shell.find_line_magic("pinfo")(arg, namespaces=namespaces)

    def do_pinfo2(self, arg):
        """Provide extra detailed information about an object.

        The debugger interface to %pinfo2, i.e., obj??."""
        assert self.curframe is not None
        namespaces = [
            ("Locals", self.curframe_locals),
            ("Globals", self.curframe.f_globals),
        ]
        self.shell.find_line_magic("pinfo2")(arg, namespaces=namespaces)

    def do_psource(self, arg):
        """Print (or run through pager) the source code for an object."""
        assert self.curframe is not None
        namespaces = [
            ("Locals", self.curframe_locals),
            ("Globals", self.curframe.f_globals),
        ]
        self.shell.find_line_magic("psource")(arg, namespaces=namespaces)

    def do_where(self, arg: str):
        """w(here)
        Print a stack trace, with the most recent frame at the bottom.
        An arrow indicates the "current frame", which determines the
        context of most commands. 'bt' is an alias for this command.

        Take a number as argument as an (optional) number of context line to
        print"""
        if arg:
            try:
                context = int(arg)
            except ValueError as err:
                self.error(str(err))
                return
            self.print_stack_trace(context)
        else:
            self.print_stack_trace()

    do_w = do_where

    def break_anywhere(self, frame):
        """
        _stop_in_decorator_internals is overly restrictive, as we may still want
        to trace function calls, so we need to also update break_anywhere so
        that is we don't `stop_here`, because of debugger skip, we may still
        stop at any point inside the function

        """

        sup = super().break_anywhere(frame)
        if sup:
            return sup
        if self._predicates["debuggerskip"]:
            if DEBUGGERSKIP in frame.f_code.co_varnames:
                return True
            if frame.f_back and self._get_frame_locals(frame.f_back).get(DEBUGGERSKIP):
                return True
        return False

    def _is_in_decorator_internal_and_should_skip(self, frame):
        """
        Utility to tell us whether we are in a decorator internal and should stop.

        """
        # if we are disabled don't skip
        if not self._predicates["debuggerskip"]:
            return False

        return self._cachable_skip(frame)

    @lru_cache(1024)
    def _cached_one_parent_frame_debuggerskip(self, frame):
        """
        Cache looking up for DEBUGGERSKIP on parent frame.

        This should speedup walking through deep frame when one of the highest
        one does have a debugger skip.

        This is likely to introduce fake positive though.
        """
        while getattr(frame, "f_back", None):
            frame = frame.f_back
            if self._get_frame_locals(frame).get(DEBUGGERSKIP):
                return True
        return None

    @lru_cache(1024)
    def _cachable_skip(self, frame):
        # if frame is tagged, skip by default.
        if DEBUGGERSKIP in frame.f_code.co_varnames:
            return True

        # if one of the parent frame value set to True skip as well.
        if self._cached_one_parent_frame_debuggerskip(frame):
            return True

        return False

    def stop_here(self, frame):
        if self._is_in_decorator_internal_and_should_skip(frame) is True:
            return False

        hidden = False
        if self.skip_hidden:
            hidden = self._hidden_predicate(frame)
        if hidden:
            if self.report_skipped:
                print(
                    self.theme.format(
                        [
                            (
                                Token.ExcName,
                                "    [... skipped 1 hidden frame(s)]",
                            ),
                            (Token, "\n"),
                        ]
                    )
                )
        return super().stop_here(frame)

    def do_up(self, arg):
        """u(p) [count]
        Move the current frame count (default one) levels up in the
        stack trace (to an older frame).

        Will skip hidden frames.
        """
        # modified version of upstream that skips
        # frames with __tracebackhide__
        if self.curindex == 0:
            self.error("Oldest frame")
            return
        try:
            count = int(arg or 1)
        except ValueError:
            self.error("Invalid frame count (%s)" % arg)
            return
        skipped = 0
        if count < 0:
            _newframe = 0
        else:
            counter = 0
            hidden_frames = self.hidden_frames(self.stack)
            for i in range(self.curindex - 1, -1, -1):
                if hidden_frames[i] and self.skip_hidden:
                    skipped += 1
                    continue
                counter += 1
                if counter >= count:
                    break
            else:
                # if no break occurred.
                self.error(
                    "all frames above hidden, use `skip_hidden False` to get get into those."
                )
                return

            _newframe = i
        self._select_frame(_newframe)
        if skipped:
            print(
                self.theme.format(
                    [
                        (
                            Token.ExcName,
                            f"    [... skipped {skipped} hidden frame(s)]",
                        ),
                        (Token, "\n"),
                    ]
                )
            )

    def do_down(self, arg):
        """d(own) [count]
        Move the current frame count (default one) levels down in the
        stack trace (to a newer frame).

        Will skip hidden frames.
        """
        if self.curindex + 1 == len(self.stack):
            self.error("Newest frame")
            return
        try:
            count = int(arg or 1)
        except ValueError:
            self.error("Invalid frame count (%s)" % arg)
            return
        if count < 0:
            _newframe = len(self.stack) - 1
        else:
            counter = 0
            skipped = 0
            hidden_frames = self.hidden_frames(self.stack)
            for i in range(self.curindex + 1, len(self.stack)):
                if hidden_frames[i] and self.skip_hidden:
                    skipped += 1
                    continue
                counter += 1
                if counter >= count:
                    break
            else:
                self.error(
                    "all frames below hidden, use `skip_hidden False` to get get into those."
                )
                return

            if skipped:
                print(
                    self.theme.format(
                        [
                            (
                                Token.ExcName,
                                f"    [... skipped {skipped} hidden frame(s)]",
                            ),
                            (Token, "\n"),
                        ]
                    )
                )
            _newframe = i

        self._select_frame(_newframe)

    do_d = do_down
    do_u = do_up

    def do_context(self, context: str):
        """context number_of_lines
        Set the number of lines of source code to show when displaying
        stacktrace information.
        """
        try:
            new_context = int(context)
            if new_context <= 0:
                raise ValueError()
            self.context = new_context
        except ValueError:
            self.error(
                f"The 'context' command requires a positive integer argument (current value {self.context})."
            )


class InterruptiblePdb(Pdb):
    """Version of debugger where KeyboardInterrupt exits the debugger altogether."""

    def cmdloop(self, intro=None):
        """Wrap cmdloop() such that KeyboardInterrupt stops the debugger."""
        try:
            return OldPdb.cmdloop(self, intro=intro)
        except KeyboardInterrupt:
            self.stop_here = lambda frame: False  # type: ignore[method-assign]
            self.do_quit("")
            sys.settrace(None)
            self.quitting = False
            raise

    def _cmdloop(self):
        while True:
            try:
                # keyboard interrupts allow for an easy way to cancel
                # the current command, so allow them during interactive input
                self.allow_kbdint = True
                self.cmdloop()
                self.allow_kbdint = False
                break
            except KeyboardInterrupt:
                self.message("--KeyboardInterrupt--")
                raise


def set_trace(frame=None, header=None):
    """
    Start debugging from `frame`.

    If frame is not specified, debugging starts from caller's frame.
    """
    pdb = Pdb()
    if header is not None:
        pdb.message(header)
    pdb.set_trace(frame or sys._getframe().f_back)

# === NexusCore/openenv\Lib\site-packages\litellm\caching\redis_cache.py ===
"""
Redis Cache implementation

Has 4 primary methods:
    - set_cache
    - get_cache
    - async_set_cache
    - async_get_cache
"""

import ast
import asyncio
import inspect
import json
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union, cast

import litellm
from litellm._logging import print_verbose, verbose_logger
from litellm.litellm_core_utils.core_helpers import _get_parent_otel_span_from_kwargs
from litellm.types.caching import RedisPipelineIncrementOperation
from litellm.types.services import ServiceTypes

from .base_cache import BaseCache

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span
    from redis.asyncio import Redis, RedisCluster
    from redis.asyncio.client import Pipeline
    from redis.asyncio.cluster import ClusterPipeline

    pipeline = Pipeline
    cluster_pipeline = ClusterPipeline
    async_redis_client = Redis
    async_redis_cluster_client = RedisCluster
    Span = Union[_Span, Any]
else:
    pipeline = Any
    cluster_pipeline = Any
    async_redis_client = Any
    async_redis_cluster_client = Any
    Span = Any


class RedisCache(BaseCache):
    # if users don't provider one, use the default litellm cache

    def __init__(
        self,
        host=None,
        port=None,
        password=None,
        redis_flush_size: Optional[int] = 100,
        namespace: Optional[str] = None,
        startup_nodes: Optional[List] = None,  # for redis-cluster
        socket_timeout: Optional[float] = 5.0,  # default 5 second timeout
        **kwargs,
    ):
        from litellm._service_logger import ServiceLogging

        from .._redis import get_redis_client, get_redis_connection_pool

        redis_kwargs = {}
        if host is not None:
            redis_kwargs["host"] = host
        if port is not None:
            redis_kwargs["port"] = port
        if password is not None:
            redis_kwargs["password"] = password
        if startup_nodes is not None:
            redis_kwargs["startup_nodes"] = startup_nodes
        if socket_timeout is not None:
            redis_kwargs["socket_timeout"] = socket_timeout

        ### HEALTH MONITORING OBJECT ###
        if kwargs.get("service_logger_obj", None) is not None and isinstance(
            kwargs["service_logger_obj"], ServiceLogging
        ):
            self.service_logger_obj = kwargs.pop("service_logger_obj")
        else:
            self.service_logger_obj = ServiceLogging()

        redis_kwargs.update(kwargs)
        self.redis_client = get_redis_client(**redis_kwargs)
        self.redis_async_client: Optional[
            Union[async_redis_client, async_redis_cluster_client]
        ] = None
        self.redis_kwargs = redis_kwargs
        self.async_redis_conn_pool = get_redis_connection_pool(**redis_kwargs)

        # redis namespaces
        self.namespace = namespace
        # for high traffic, we store the redis results in memory and then batch write to redis
        self.redis_batch_writing_buffer: list = []
        if redis_flush_size is None:
            self.redis_flush_size: int = 100
        else:
            self.redis_flush_size = redis_flush_size
        self.redis_version = "Unknown"
        try:
            if not inspect.iscoroutinefunction(self.redis_client):
                self.redis_version = self.redis_client.info()["redis_version"]  # type: ignore
        except Exception:
            pass

        ### ASYNC HEALTH PING ###
        try:
            # asyncio.get_running_loop().create_task(self.ping())
            _ = asyncio.get_running_loop().create_task(self.ping())
        except Exception as e:
            if "no running event loop" in str(e):
                verbose_logger.debug(
                    "Ignoring async redis ping. No running event loop."
                )
            else:
                verbose_logger.error(
                    "Error connecting to Async Redis client - {}".format(str(e)),
                    extra={"error": str(e)},
                )

        ### SYNC HEALTH PING ###
        try:
            if hasattr(self.redis_client, "ping"):
                self.redis_client.ping()  # type: ignore
        except Exception as e:
            verbose_logger.error(
                "Error connecting to Sync Redis client", extra={"error": str(e)}
            )

        if litellm.default_redis_ttl is not None:
            super().__init__(default_ttl=int(litellm.default_redis_ttl))
        else:
            super().__init__()  # defaults to 60s

    def init_async_client(
        self,
    ) -> Union[async_redis_client, async_redis_cluster_client]:
        from litellm import in_memory_llm_clients_cache

        from .._redis import get_redis_async_client, get_redis_connection_pool

        cached_client = in_memory_llm_clients_cache.get_cache(key="async-redis-client")
        if cached_client is not None:
            redis_async_client = cast(
                Union[async_redis_client, async_redis_cluster_client], cached_client
            )
        else:
            # Create new connection pool and client for current event loop
            self.async_redis_conn_pool = get_redis_connection_pool(**self.redis_kwargs)
            redis_async_client = get_redis_async_client(
                connection_pool=self.async_redis_conn_pool, **self.redis_kwargs
            )
            in_memory_llm_clients_cache.set_cache(
                key="async-redis-client", value=self.redis_async_client
            )

        self.redis_async_client = redis_async_client  # type: ignore
        return redis_async_client

    def check_and_fix_namespace(self, key: str) -> str:
        """
        Make sure each key starts with the given namespace
        """
        if self.namespace is not None and not key.startswith(self.namespace):
            key = self.namespace + ":" + key

        return key

    def set_cache(self, key, value, **kwargs):
        ttl = self.get_ttl(**kwargs)
        print_verbose(
            f"Set Redis Cache: key: {key}\nValue {value}\nttl={ttl}, redis_version={self.redis_version}"
        )
        key = self.check_and_fix_namespace(key=key)
        try:
            start_time = time.time()
            self.redis_client.set(name=key, value=str(value), ex=ttl)
            end_time = time.time()
            _duration = end_time - start_time
            self.service_logger_obj.service_success_hook(
                service=ServiceTypes.REDIS,
                duration=_duration,
                call_type="set_cache",
                start_time=start_time,
                end_time=end_time,
            )
        except Exception as e:
            # NON blocking - notify users Redis is throwing an exception
            print_verbose(
                f"litellm.caching.caching: set() - Got exception from REDIS : {str(e)}"
            )

    def increment_cache(
        self, key, value: int, ttl: Optional[float] = None, **kwargs
    ) -> int:
        _redis_client = self.redis_client
        start_time = time.time()
        set_ttl = self.get_ttl(ttl=ttl)
        try:
            start_time = time.time()
            result: int = _redis_client.incr(name=key, amount=value)  # type: ignore
            end_time = time.time()
            _duration = end_time - start_time
            self.service_logger_obj.service_success_hook(
                service=ServiceTypes.REDIS,
                duration=_duration,
                call_type="increment_cache",
                start_time=start_time,
                end_time=end_time,
            )

            if set_ttl is not None:
                # check if key already has ttl, if not -> set ttl
                start_time = time.time()
                current_ttl = _redis_client.ttl(key)
                end_time = time.time()
                _duration = end_time - start_time
                self.service_logger_obj.service_success_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    call_type="increment_cache_ttl",
                    start_time=start_time,
                    end_time=end_time,
                )
                if current_ttl == -1:
                    # Key has no expiration
                    start_time = time.time()
                    _redis_client.expire(key, set_ttl)  # type: ignore
                    end_time = time.time()
                    _duration = end_time - start_time
                    self.service_logger_obj.service_success_hook(
                        service=ServiceTypes.REDIS,
                        duration=_duration,
                        call_type="increment_cache_expire",
                        start_time=start_time,
                        end_time=end_time,
                    )
            return result
        except Exception as e:
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            verbose_logger.error(
                "LiteLLM Redis Caching: increment_cache() - Got exception from REDIS %s, Writing value=%s",
                str(e),
                value,
            )
            raise e

    async def async_scan_iter(self, pattern: str, count: int = 100) -> list:
        start_time = time.time()
        try:
            keys = []
            _redis_client = self.init_async_client()
            if not hasattr(_redis_client, "scan_iter"):
                verbose_logger.debug(
                    "Redis client does not support scan_iter, potentially using Redis Cluster. Returning empty list."
                )
                return []

            async for key in _redis_client.scan_iter(match=pattern + "*", count=count):  # type: ignore
                keys.append(key)
                if len(keys) >= count:
                    break

            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    call_type="async_scan_iter",
                    start_time=start_time,
                    end_time=end_time,
                )
            )  # DO NOT SLOW DOWN CALL B/C OF THIS
            return keys
        except Exception as e:
            # NON blocking - notify users Redis is throwing an exception
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    call_type="async_scan_iter",
                    start_time=start_time,
                    end_time=end_time,
                )
            )
            raise e

    def async_register_script(self, script: str) -> Any:
        """
        Register a Lua script with Redis asynchronously.
        Works with both standalone Redis and Redis Cluster.

        Args:
            script (str): The Lua script to register

        Returns:
            Any: A script object that can be called with keys and args
        """
        try:
            _redis_client = self.init_async_client()
            # For standalone Redis
            if hasattr(_redis_client, "register_script"):
                return _redis_client.register_script(script)  # type: ignore
            # For Redis Cluster
            elif hasattr(_redis_client, "script_load"):
                # Load the script and get its SHA
                script_sha = _redis_client.script_load(script)  # type: ignore

                # Return a callable that uses evalsha
                async def script_callable(keys: List[str], args: List[Any]) -> Any:
                    return _redis_client.evalsha(script_sha, len(keys), *keys, *args)  # type: ignore

                return script_callable
        except Exception as e:
            verbose_logger.error(f"Error registering Redis script: {str(e)}")
            raise e

    async def async_set_cache(self, key, value, **kwargs):
        from redis.asyncio import Redis

        start_time = time.time()
        try:
            _redis_client: Redis = self.init_async_client()  # type: ignore
        except Exception as e:
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=_get_parent_otel_span_from_kwargs(kwargs),
                    call_type="async_set_cache",
                )
            )
            verbose_logger.error(
                "LiteLLM Redis Caching: async set() - Got exception from REDIS %s, Writing value=%s",
                str(e),
                value,
            )
            raise e

        key = self.check_and_fix_namespace(key=key)
        ttl = self.get_ttl(**kwargs)
        nx = kwargs.get("nx", False)
        print_verbose(f"Set ASYNC Redis Cache: key: {key}\nValue {value}\nttl={ttl}")

        try:
            if not hasattr(_redis_client, "set"):
                raise Exception("Redis client cannot set cache. Attribute not found.")
            result = await _redis_client.set(
                name=key,
                value=json.dumps(value),
                nx=nx,
                ex=ttl,
            )
            print_verbose(
                f"Successfully Set ASYNC Redis Cache: key: {key}\nValue {value}\nttl={ttl}"
            )
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    call_type="async_set_cache",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=_get_parent_otel_span_from_kwargs(kwargs),
                    event_metadata={"key": key},
                )
            )
            return result
        except Exception as e:
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    call_type="async_set_cache",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=_get_parent_otel_span_from_kwargs(kwargs),
                    event_metadata={"key": key},
                )
            )
            verbose_logger.error(
                "LiteLLM Redis Caching: async set() - Got exception from REDIS %s, Writing value=%s",
                str(e),
                value,
            )

    async def _pipeline_helper(
        self,
        pipe: Union[pipeline, cluster_pipeline],
        cache_list: List[Tuple[Any, Any]],
        ttl: Optional[float],
    ) -> List:
        """
        Helper function for executing a pipeline of set operations on Redis
        """
        ttl = self.get_ttl(ttl=ttl)
        # Iterate through each key-value pair in the cache_list and set them in the pipeline.
        for cache_key, cache_value in cache_list:
            cache_key = self.check_and_fix_namespace(key=cache_key)
            print_verbose(
                f"Set ASYNC Redis Cache PIPELINE: key: {cache_key}\nValue {cache_value}\nttl={ttl}"
            )
            json_cache_value = json.dumps(cache_value)
            # Set the value with a TTL if it's provided.
            _td: Optional[timedelta] = None
            if ttl is not None:
                _td = timedelta(seconds=ttl)
            pipe.set(  # type: ignore
                name=cache_key,
                value=json_cache_value,
                ex=_td,
            )
        # Execute the pipeline and return the results.
        results = await pipe.execute()
        return results

    async def async_set_cache_pipeline(
        self, cache_list: List[Tuple[Any, Any]], ttl: Optional[float] = None, **kwargs
    ):
        """
        Use Redis Pipelines for bulk write operations
        """
        # don't waste a network request if there's nothing to set
        if len(cache_list) == 0:
            return

        _redis_client = self.init_async_client()
        start_time = time.time()

        print_verbose(
            f"Set Async Redis Cache: key list: {cache_list}\nttl={ttl}, redis_version={self.redis_version}"
        )
        cache_value: Any = None
        try:
            async with _redis_client.pipeline(transaction=False) as pipe:
                results = await self._pipeline_helper(pipe, cache_list, ttl)

            print_verbose(f"pipeline results: {results}")
            # Optionally, you could process 'results' to make sure that all set operations were successful.
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    call_type="async_set_cache_pipeline",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=_get_parent_otel_span_from_kwargs(kwargs),
                )
            )
            return None
        except Exception as e:
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    call_type="async_set_cache_pipeline",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=_get_parent_otel_span_from_kwargs(kwargs),
                )
            )

            verbose_logger.error(
                "LiteLLM Redis Caching: async set_cache_pipeline() - Got exception from REDIS %s, Writing value=%s",
                str(e),
                cache_value,
            )

    async def _set_cache_sadd_helper(
        self,
        redis_client: async_redis_client,
        key: str,
        value: List,
        ttl: Optional[float],
    ) -> None:
        """Helper function for async_set_cache_sadd. Separated for testing."""
        ttl = self.get_ttl(ttl=ttl)
        try:
            await redis_client.sadd(key, *value)  # type: ignore
            if ttl is not None:
                _td = timedelta(seconds=ttl)
                await redis_client.expire(key, _td)
        except Exception:
            raise

    async def async_set_cache_sadd(
        self, key, value: List, ttl: Optional[float], **kwargs
    ):
        from redis.asyncio import Redis

        start_time = time.time()
        try:
            _redis_client: Redis = self.init_async_client()  # type: ignore
        except Exception as e:
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=_get_parent_otel_span_from_kwargs(kwargs),
                    call_type="async_set_cache_sadd",
                )
            )
            # NON blocking - notify users Redis is throwing an exception
            verbose_logger.error(
                "LiteLLM Redis Caching: async set() - Got exception from REDIS %s, Writing value=%s",
                str(e),
                value,
            )
            raise e

        key = self.check_and_fix_namespace(key=key)
        print_verbose(f"Set ASYNC Redis Cache: key: {key}\nValue {value}\nttl={ttl}")
        try:
            await self._set_cache_sadd_helper(
                redis_client=_redis_client, key=key, value=value, ttl=ttl
            )
            print_verbose(
                f"Successfully Set ASYNC Redis Cache SADD: key: {key}\nValue {value}\nttl={ttl}"
            )
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    call_type="async_set_cache_sadd",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=_get_parent_otel_span_from_kwargs(kwargs),
                )
            )
        except Exception as e:
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    call_type="async_set_cache_sadd",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=_get_parent_otel_span_from_kwargs(kwargs),
                )
            )
            # NON blocking - notify users Redis is throwing an exception
            verbose_logger.error(
                "LiteLLM Redis Caching: async set_cache_sadd() - Got exception from REDIS %s, Writing value=%s",
                str(e),
                value,
            )

    async def batch_cache_write(self, key, value, **kwargs):
        print_verbose(
            f"in batch cache writing for redis buffer size={len(self.redis_batch_writing_buffer)}",
        )
        key = self.check_and_fix_namespace(key=key)
        self.redis_batch_writing_buffer.append((key, value))
        if len(self.redis_batch_writing_buffer) >= self.redis_flush_size:
            await self.flush_cache_buffer()  # logging done in here

    async def async_increment(
        self,
        key,
        value: float,
        ttl: Optional[int] = None,
        parent_otel_span: Optional[Span] = None,
    ) -> float:
        from redis.asyncio import Redis

        _redis_client: Redis = self.init_async_client()  # type: ignore
        start_time = time.time()
        _used_ttl = self.get_ttl(ttl=ttl)
        key = self.check_and_fix_namespace(key=key)
        try:
            result = await _redis_client.incrbyfloat(name=key, amount=value)
            if _used_ttl is not None:
                # check if key already has ttl, if not -> set ttl
                current_ttl = await _redis_client.ttl(key)
                if current_ttl == -1:
                    # Key has no expiration
                    await _redis_client.expire(key, _used_ttl)

            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time

            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    call_type="async_increment",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=parent_otel_span,
                )
            )
            return result
        except Exception as e:
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    call_type="async_increment",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=parent_otel_span,
                )
            )
            verbose_logger.error(
                "LiteLLM Redis Caching: async async_increment() - Got exception from REDIS %s, Writing value=%s",
                str(e),
                value,
            )
            raise e

    async def flush_cache_buffer(self):
        print_verbose(
            f"flushing to redis....reached size of buffer {len(self.redis_batch_writing_buffer)}"
        )
        await self.async_set_cache_pipeline(self.redis_batch_writing_buffer)
        self.redis_batch_writing_buffer = []

    def _get_cache_logic(self, cached_response: Any):
        """
        Common 'get_cache_logic' across sync + async redis client implementations
        """
        if cached_response is None:
            return cached_response
        # cached_response is in `b{} convert it to ModelResponse
        cached_response = cached_response.decode("utf-8")  # Convert bytes to string
        try:
            cached_response = json.loads(
                cached_response
            )  # Convert string to dictionary
        except Exception:
            cached_response = ast.literal_eval(cached_response)
        return cached_response

    def get_cache(self, key, parent_otel_span: Optional[Span] = None, **kwargs):
        try:
            key = self.check_and_fix_namespace(key=key)
            print_verbose(f"Get Redis Cache: key: {key}")
            start_time = time.time()
            cached_response = self.redis_client.get(key)
            end_time = time.time()
            _duration = end_time - start_time
            self.service_logger_obj.service_success_hook(
                service=ServiceTypes.REDIS,
                duration=_duration,
                call_type="get_cache",
                start_time=start_time,
                end_time=end_time,
                parent_otel_span=parent_otel_span,
            )
            print_verbose(
                f"Got Redis Cache: key: {key}, cached_response {cached_response}"
            )
            return self._get_cache_logic(cached_response=cached_response)
        except Exception as e:
            # NON blocking - notify users Redis is throwing an exception
            verbose_logger.error(
                "litellm.caching.caching: get() - Got exception from REDIS: ", e
            )

    def _run_redis_mget_operation(self, keys: List[str]) -> List[Any]:
        """
        Wrapper to call `mget` on the redis client

        We use a wrapper so RedisCluster can override this method
        """
        return self.redis_client.mget(keys=keys)  # type: ignore

    async def _async_run_redis_mget_operation(self, keys: List[str]) -> List[Any]:
        """
        Wrapper to call `mget` on the redis client

        We use a wrapper so RedisCluster can override this method
        """
        async_redis_client = self.init_async_client()
        return await async_redis_client.mget(keys=keys)  # type: ignore

    def batch_get_cache(
        self,
        key_list: Union[List[str], List[Optional[str]]],
        parent_otel_span: Optional[Span] = None,
    ) -> dict:
        """
        Use Redis for bulk read operations

        Args:
            key_list: List of keys to get from Redis
            parent_otel_span: Optional parent OpenTelemetry span

        Returns:
            dict: A dictionary mapping keys to their cached values
        """
        key_value_dict = {}
        _key_list = [key for key in key_list if key is not None]

        try:
            _keys = []
            for cache_key in _key_list:
                cache_key = self.check_and_fix_namespace(key=cache_key or "")
                _keys.append(cache_key)
            start_time = time.time()
            results: List = self._run_redis_mget_operation(keys=_keys)
            end_time = time.time()
            _duration = end_time - start_time
            self.service_logger_obj.service_success_hook(
                service=ServiceTypes.REDIS,
                duration=_duration,
                call_type="batch_get_cache",
                start_time=start_time,
                end_time=end_time,
                parent_otel_span=parent_otel_span,
            )

            # Associate the results back with their keys.
            # 'results' is a list of values corresponding to the order of keys in '_key_list'.
            key_value_dict = dict(zip(_key_list, results))

            decoded_results = {}
            for k, v in key_value_dict.items():
                if isinstance(k, bytes):
                    k = k.decode("utf-8")
                v = self._get_cache_logic(v)
                decoded_results[k] = v

            return decoded_results
        except Exception as e:
            verbose_logger.error(f"Error occurred in batch get cache - {str(e)}")
            return key_value_dict

    async def async_get_cache(
        self, key, parent_otel_span: Optional[Span] = None, **kwargs
    ):
        from redis.asyncio import Redis

        _redis_client: Redis = self.init_async_client()  # type: ignore
        key = self.check_and_fix_namespace(key=key)
        start_time = time.time()

        try:
            print_verbose(f"Get Async Redis Cache: key: {key}")
            cached_response = await _redis_client.get(key)
            print_verbose(
                f"Got Async Redis Cache: key: {key}, cached_response {cached_response}"
            )
            response = self._get_cache_logic(cached_response=cached_response)

            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    call_type="async_get_cache",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=parent_otel_span,
                    event_metadata={"key": key},
                )
            )
            return response
        except Exception as e:
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    call_type="async_get_cache",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=parent_otel_span,
                    event_metadata={"key": key},
                )
            )
            print_verbose(
                f"litellm.caching.caching: async get() - Got exception from REDIS: {str(e)}"
            )

    async def async_batch_get_cache(
        self,
        key_list: Union[List[str], List[Optional[str]]],
        parent_otel_span: Optional[Span] = None,
    ) -> dict:
        """
        Use Redis for bulk read operations

        Args:
            key_list: List of keys to get from Redis
            parent_otel_span: Optional parent OpenTelemetry span

        Returns:
            dict: A dictionary mapping keys to their cached values

        `.mget` does not support None keys. This will filter out None keys.
        """
        # typed as Any, redis python lib has incomplete type stubs for RedisCluster and does not include `mget`
        key_value_dict = {}
        start_time = time.time()
        _key_list = [key for key in key_list if key is not None]
        try:
            _keys = []
            for cache_key in _key_list:
                cache_key = self.check_and_fix_namespace(key=cache_key)
                _keys.append(cache_key)
            results = await self._async_run_redis_mget_operation(keys=_keys)
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    call_type="async_batch_get_cache",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=parent_otel_span,
                )
            )

            # Associate the results back with their keys.
            # 'results' is a list of values corresponding to the order of keys in 'key_list'.
            key_value_dict = dict(zip(_key_list, results))

            decoded_results = {}
            for k, v in key_value_dict.items():
                if isinstance(k, bytes):
                    k = k.decode("utf-8")
                v = self._get_cache_logic(v)
                decoded_results[k] = v

            return decoded_results
        except Exception as e:
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    call_type="async_batch_get_cache",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=parent_otel_span,
                )
            )
            verbose_logger.error(f"Error occurred in async batch get cache - {str(e)}")
            return key_value_dict

    def sync_ping(self) -> bool:
        """
        Tests if the sync redis client is correctly setup.
        """
        print_verbose("Pinging Sync Redis Cache")
        start_time = time.time()
        try:
            response: bool = self.redis_client.ping()  # type: ignore
            print_verbose(f"Redis Cache PING: {response}")
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            self.service_logger_obj.service_success_hook(
                service=ServiceTypes.REDIS,
                duration=_duration,
                call_type="sync_ping",
                start_time=start_time,
                end_time=end_time,
            )
            return response
        except Exception as e:
            # NON blocking - notify users Redis is throwing an exception
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            self.service_logger_obj.service_failure_hook(
                service=ServiceTypes.REDIS,
                duration=_duration,
                error=e,
                call_type="sync_ping",
            )
            verbose_logger.error(
                f"LiteLLM Redis Cache PING: - Got exception from REDIS : {str(e)}"
            )
            raise e

    async def ping(self) -> bool:
        # typed as Any, redis python lib has incomplete type stubs for RedisCluster and does not include `ping`
        _redis_client: Any = self.init_async_client()
        start_time = time.time()
        print_verbose("Pinging Async Redis Cache")
        try:
            response = await _redis_client.ping()
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    call_type="async_ping",
                )
            )
            return response
        except Exception as e:
            # NON blocking - notify users Redis is throwing an exception
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    call_type="async_ping",
                )
            )
            verbose_logger.error(
                f"LiteLLM Redis Cache PING: - Got exception from REDIS : {str(e)}"
            )
            raise e

    async def delete_cache_keys(self, keys):
        # typed as Any, redis python lib has incomplete type stubs for RedisCluster and does not include `delete`
        _redis_client: Any = self.init_async_client()
        # keys is a list, unpack it so it gets passed as individual elements to delete
        await _redis_client.delete(*keys)

    def client_list(self) -> List:
        client_list: List = self.redis_client.client_list()  # type: ignore
        return client_list

    def info(self):
        info = self.redis_client.info()
        return info

    def flush_cache(self):
        self.redis_client.flushall()

    def flushall(self):
        self.redis_client.flushall()

    async def disconnect(self):
        await self.async_redis_conn_pool.disconnect(inuse_connections=True)

    async def async_delete_cache(self, key: str):
        # typed as Any, redis python lib has incomplete type stubs for RedisCluster and does not include `delete`
        _redis_client: Any = self.init_async_client()
        # keys is str
        return await _redis_client.delete(key)

    def delete_cache(self, key):
        self.redis_client.delete(key)

    async def _pipeline_increment_helper(
        self,
        pipe: pipeline,
        increment_list: List[RedisPipelineIncrementOperation],
    ) -> Optional[List[float]]:
        """Helper function for pipeline increment operations"""
        # Iterate through each increment operation and add commands to pipeline
        for increment_op in increment_list:
            cache_key = self.check_and_fix_namespace(key=increment_op["key"])
            print_verbose(
                f"Increment ASYNC Redis Cache PIPELINE: key: {cache_key}\nValue {increment_op['increment_value']}\nttl={increment_op['ttl']}"
            )
            pipe.incrbyfloat(cache_key, increment_op["increment_value"])
            if increment_op["ttl"] is not None:
                _td = timedelta(seconds=increment_op["ttl"])
                pipe.expire(cache_key, _td)
        # Execute the pipeline and return results
        results = await pipe.execute()
        # only return float values
        verbose_logger.debug(
            f"Increment ASYNC Redis Cache PIPELINE: results: {results}"
        )
        return [r for r in results if isinstance(r, float)]

    async def async_increment_pipeline(
        self, increment_list: List[RedisPipelineIncrementOperation], **kwargs
    ) -> Optional[List[float]]:
        """
        Use Redis Pipelines for bulk increment operations
        Args:
            increment_list: List of RedisPipelineIncrementOperation dicts containing:
                - key: str
                - increment_value: float
                - ttl_seconds: int
        """
        # don't waste a network request if there's nothing to increment
        if len(increment_list) == 0:
            return None

        from redis.asyncio import Redis

        _redis_client: Redis = self.init_async_client()  # type: ignore
        start_time = time.time()

        print_verbose(
            f"Increment Async Redis Cache Pipeline: increment list: {increment_list}"
        )

        try:
            async with _redis_client.pipeline(transaction=False) as pipe:
                results = await self._pipeline_increment_helper(pipe, increment_list)

            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    call_type="async_increment_pipeline",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=_get_parent_otel_span_from_kwargs(kwargs),
                )
            )
            return results
        except Exception as e:
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    call_type="async_increment_pipeline",
                    start_time=start_time,
                    end_time=end_time,
                    parent_otel_span=_get_parent_otel_span_from_kwargs(kwargs),
                )
            )
            verbose_logger.error(
                "LiteLLM Redis Caching: async increment_pipeline() - Got exception from REDIS %s",
                str(e),
            )
            raise e

    async def async_get_ttl(self, key: str) -> Optional[int]:
        """
        Get the remaining TTL of a key in Redis

        Args:
            key (str): The key to get TTL for

        Returns:
            Optional[int]: The remaining TTL in seconds, or None if key doesn't exist

        Redis ref: https://redis.io/docs/latest/commands/ttl/
        """
        try:
            # typed as Any, redis python lib has incomplete type stubs for RedisCluster and does not include `ttl`
            _redis_client: Any = self.init_async_client()
            ttl = await _redis_client.ttl(key)
            if ttl <= -1:  # -1 means the key does not exist, -2 key does not exist
                return None
            return ttl
        except Exception as e:
            verbose_logger.debug(f"Redis TTL Error: {e}")
            return None

    async def async_rpush(
        self,
        key: str,
        values: List[Any],
        parent_otel_span: Optional[Span] = None,
        **kwargs,
    ) -> int:
        """
        Append one or multiple values to a list stored at key

        Args:
            key: The Redis key of the list
            values: One or more values to append to the list
            parent_otel_span: Optional parent OpenTelemetry span

        Returns:
            int: The length of the list after the push operation
        """
        _redis_client: Any = self.init_async_client()
        start_time = time.time()
        try:
            response = await _redis_client.rpush(key, *values)
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    call_type="async_rpush",
                )
            )
            return response
        except Exception as e:
            # NON blocking - notify users Redis is throwing an exception
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    call_type="async_rpush",
                )
            )
            verbose_logger.error(
                f"LiteLLM Redis Cache RPUSH: - Got exception from REDIS : {str(e)}"
            )
            raise e

    async def handle_lpop_count_for_older_redis_versions(
        self, pipe: pipeline, key: str, count: int
    ) -> List[bytes]:
        result: List[bytes] = []
        for _ in range(count):
            pipe.lpop(key)
            results = await pipe.execute()

            # Filter out None values and decode bytes
            for r in results:
                if r is not None:
                    result.append(r)

        return result

    async def async_lpop(
        self,
        key: str,
        count: Optional[int] = None,
        parent_otel_span: Optional[Span] = None,
        **kwargs,
    ) -> Union[Any, List[Any]]:
        _redis_client: Any = self.init_async_client()
        start_time = time.time()
        print_verbose(f"LPOP from Redis list: key: {key}, count: {count}")
        try:
            major_version: int = 7
            # Check Redis version and use appropriate method
            if self.redis_version != "Unknown":
                # Parse version string like "6.0.0" to get major version
                major_version = int(self.redis_version.split(".")[0])

            if count is not None and major_version < 7:
                # For Redis < 7.0, use pipeline to execute multiple LPOP commands
                async with _redis_client.pipeline(transaction=False) as pipe:
                    result = await self.handle_lpop_count_for_older_redis_versions(
                        pipe, key, count
                    )
            else:
                # For Redis >= 7.0 or when count is None, use native LPOP with count
                result = await _redis_client.lpop(key, count)

            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_success_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    call_type="async_lpop",
                )
            )

            # Handle result parsing if needed
            if isinstance(result, bytes):
                try:
                    return result.decode("utf-8")
                except Exception:
                    return result
            elif isinstance(result, list) and all(
                isinstance(item, bytes) for item in result
            ):
                try:
                    return [item.decode("utf-8") for item in result]
                except Exception:
                    return result
            return result
        except Exception as e:
            # NON blocking - notify users Redis is throwing an exception
            ## LOGGING ##
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.service_logger_obj.async_service_failure_hook(
                    service=ServiceTypes.REDIS,
                    duration=_duration,
                    error=e,
                    call_type="async_lpop",
                )
            )
            verbose_logger.error(
                f"LiteLLM Redis Cache LPOP: - Got exception from REDIS : {str(e)}"
            )
            raise e