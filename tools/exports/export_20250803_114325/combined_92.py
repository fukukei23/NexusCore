
# === NexusCore/openenv\Lib\site-packages\pydantic\networks.py ===
"""The networks module contains types for common network-related fields."""

from __future__ import annotations as _annotations

import dataclasses as _dataclasses
import re
from dataclasses import fields
from functools import lru_cache
from importlib.metadata import version
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from pydantic_core import (
    MultiHostHost,
    PydanticCustomError,
    PydanticSerializationUnexpectedValue,
    SchemaSerializer,
    core_schema,
)
from pydantic_core import MultiHostUrl as _CoreMultiHostUrl
from pydantic_core import Url as _CoreUrl
from typing_extensions import Self, TypeAlias

from pydantic.errors import PydanticUserError

from ._internal import _repr, _schema_generation_shared
from ._migration import getattr_migration
from .annotated_handlers import GetCoreSchemaHandler
from .json_schema import JsonSchemaValue
from .type_adapter import TypeAdapter

if TYPE_CHECKING:
    import email_validator

    NetworkType: TypeAlias = 'str | bytes | int | tuple[str | bytes | int, str | int]'

else:
    email_validator = None


__all__ = [
    'AnyUrl',
    'AnyHttpUrl',
    'FileUrl',
    'FtpUrl',
    'HttpUrl',
    'WebsocketUrl',
    'AnyWebsocketUrl',
    'UrlConstraints',
    'EmailStr',
    'NameEmail',
    'IPvAnyAddress',
    'IPvAnyInterface',
    'IPvAnyNetwork',
    'PostgresDsn',
    'CockroachDsn',
    'AmqpDsn',
    'RedisDsn',
    'MongoDsn',
    'KafkaDsn',
    'NatsDsn',
    'validate_email',
    'MySQLDsn',
    'MariaDBDsn',
    'ClickHouseDsn',
    'SnowflakeDsn',
]


@_dataclasses.dataclass
class UrlConstraints:
    """Url constraints.

    Attributes:
        max_length: The maximum length of the url. Defaults to `None`.
        allowed_schemes: The allowed schemes. Defaults to `None`.
        host_required: Whether the host is required. Defaults to `None`.
        default_host: The default host. Defaults to `None`.
        default_port: The default port. Defaults to `None`.
        default_path: The default path. Defaults to `None`.
    """

    max_length: int | None = None
    allowed_schemes: list[str] | None = None
    host_required: bool | None = None
    default_host: str | None = None
    default_port: int | None = None
    default_path: str | None = None

    def __hash__(self) -> int:
        return hash(
            (
                self.max_length,
                tuple(self.allowed_schemes) if self.allowed_schemes is not None else None,
                self.host_required,
                self.default_host,
                self.default_port,
                self.default_path,
            )
        )

    @property
    def defined_constraints(self) -> dict[str, Any]:
        """Fetch a key / value mapping of constraints to values that are not None. Used for core schema updates."""
        return {field.name: value for field in fields(self) if (value := getattr(self, field.name)) is not None}

    def __get_pydantic_core_schema__(self, source: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        schema = handler(source)

        # for function-wrap schemas, url constraints is applied to the inner schema
        # because when we generate schemas for urls, we wrap a core_schema.url_schema() with a function-wrap schema
        # that helps with validation on initialization, see _BaseUrl and _BaseMultiHostUrl below.
        schema_to_mutate = schema['schema'] if schema['type'] == 'function-wrap' else schema
        if annotated_type := schema_to_mutate['type'] not in ('url', 'multi-host-url'):
            raise PydanticUserError(
                f"'UrlConstraints' cannot annotate '{annotated_type}'.", code='invalid-annotated-type'
            )
        for constraint_key, constraint_value in self.defined_constraints.items():
            schema_to_mutate[constraint_key] = constraint_value
        return schema


class _BaseUrl:
    _constraints: ClassVar[UrlConstraints] = UrlConstraints()
    _url: _CoreUrl

    def __init__(self, url: str | _CoreUrl | _BaseUrl) -> None:
        self._url = _build_type_adapter(self.__class__).validate_python(url)._url

    @property
    def scheme(self) -> str:
        """The scheme part of the URL.

        e.g. `https` in `https://user:pass@host:port/path?query#fragment`
        """
        return self._url.scheme

    @property
    def username(self) -> str | None:
        """The username part of the URL, or `None`.

        e.g. `user` in `https://user:pass@host:port/path?query#fragment`
        """
        return self._url.username

    @property
    def password(self) -> str | None:
        """The password part of the URL, or `None`.

        e.g. `pass` in `https://user:pass@host:port/path?query#fragment`
        """
        return self._url.password

    @property
    def host(self) -> str | None:
        """The host part of the URL, or `None`.

        If the URL must be punycode encoded, this is the encoded host, e.g if the input URL is `https://£££.com`,
        `host` will be `xn--9aaa.com`
        """
        return self._url.host

    def unicode_host(self) -> str | None:
        """The host part of the URL as a unicode string, or `None`.

        e.g. `host` in `https://user:pass@host:port/path?query#fragment`

        If the URL must be punycode encoded, this is the decoded host, e.g if the input URL is `https://£££.com`,
        `unicode_host()` will be `£££.com`
        """
        return self._url.unicode_host()

    @property
    def port(self) -> int | None:
        """The port part of the URL, or `None`.

        e.g. `port` in `https://user:pass@host:port/path?query#fragment`
        """
        return self._url.port

    @property
    def path(self) -> str | None:
        """The path part of the URL, or `None`.

        e.g. `/path` in `https://user:pass@host:port/path?query#fragment`
        """
        return self._url.path

    @property
    def query(self) -> str | None:
        """The query part of the URL, or `None`.

        e.g. `query` in `https://user:pass@host:port/path?query#fragment`
        """
        return self._url.query

    def query_params(self) -> list[tuple[str, str]]:
        """The query part of the URL as a list of key-value pairs.

        e.g. `[('foo', 'bar')]` in `https://user:pass@host:port/path?foo=bar#fragment`
        """
        return self._url.query_params()

    @property
    def fragment(self) -> str | None:
        """The fragment part of the URL, or `None`.

        e.g. `fragment` in `https://user:pass@host:port/path?query#fragment`
        """
        return self._url.fragment

    def unicode_string(self) -> str:
        """The URL as a unicode string, unlike `__str__()` this will not punycode encode the host.

        If the URL must be punycode encoded, this is the decoded string, e.g if the input URL is `https://£££.com`,
        `unicode_string()` will be `https://£££.com`
        """
        return self._url.unicode_string()

    def encoded_string(self) -> str:
        """The URL's encoded string representation via __str__().

        This returns the punycode-encoded host version of the URL as a string.
        """
        return str(self)

    def __str__(self) -> str:
        """The URL as a string, this will punycode encode the host if required."""
        return str(self._url)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({str(self._url)!r})'

    def __deepcopy__(self, memo: dict) -> Self:
        return self.__class__(self._url)

    def __eq__(self, other: Any) -> bool:
        return self.__class__ is other.__class__ and self._url == other._url

    def __lt__(self, other: Any) -> bool:
        return self.__class__ is other.__class__ and self._url < other._url

    def __gt__(self, other: Any) -> bool:
        return self.__class__ is other.__class__ and self._url > other._url

    def __le__(self, other: Any) -> bool:
        return self.__class__ is other.__class__ and self._url <= other._url

    def __ge__(self, other: Any) -> bool:
        return self.__class__ is other.__class__ and self._url >= other._url

    def __hash__(self) -> int:
        return hash(self._url)

    def __len__(self) -> int:
        return len(str(self._url))

    @classmethod
    def build(
        cls,
        *,
        scheme: str,
        username: str | None = None,
        password: str | None = None,
        host: str,
        port: int | None = None,
        path: str | None = None,
        query: str | None = None,
        fragment: str | None = None,
    ) -> Self:
        """Build a new `Url` instance from its component parts.

        Args:
            scheme: The scheme part of the URL.
            username: The username part of the URL, or omit for no username.
            password: The password part of the URL, or omit for no password.
            host: The host part of the URL.
            port: The port part of the URL, or omit for no port.
            path: The path part of the URL, or omit for no path.
            query: The query part of the URL, or omit for no query.
            fragment: The fragment part of the URL, or omit for no fragment.

        Returns:
            An instance of URL
        """
        return cls(
            _CoreUrl.build(
                scheme=scheme,
                username=username,
                password=password,
                host=host,
                port=port,
                path=path,
                query=query,
                fragment=fragment,
            )
        )

    @classmethod
    def serialize_url(cls, url: Any, info: core_schema.SerializationInfo) -> str | Self:
        if not isinstance(url, cls):
            raise PydanticSerializationUnexpectedValue(
                f"Expected `{cls}` but got `{type(url)}` with value `'{url}'` - serialized value may not be as expected."
            )
        if info.mode == 'json':
            return str(url)
        return url

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[_BaseUrl], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def wrap_val(v, h):
            if isinstance(v, source):
                return v
            if isinstance(v, _BaseUrl):
                v = str(v)
            core_url = h(v)
            instance = source.__new__(source)
            instance._url = core_url
            return instance

        return core_schema.no_info_wrap_validator_function(
            wrap_val,
            schema=core_schema.url_schema(**cls._constraints.defined_constraints),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.serialize_url, info_arg=True, when_used='always'
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: _schema_generation_shared.GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        # we use the url schema for json schema generation, but we might have to extract it from
        # the function-wrap schema we use as a tool for validation on initialization
        inner_schema = core_schema['schema'] if core_schema['type'] == 'function-wrap' else core_schema
        return handler(inner_schema)

    __pydantic_serializer__ = SchemaSerializer(core_schema.any_schema(serialization=core_schema.to_string_ser_schema()))


class _BaseMultiHostUrl:
    _constraints: ClassVar[UrlConstraints] = UrlConstraints()
    _url: _CoreMultiHostUrl

    def __init__(self, url: str | _CoreMultiHostUrl | _BaseMultiHostUrl) -> None:
        self._url = _build_type_adapter(self.__class__).validate_python(url)._url

    @property
    def scheme(self) -> str:
        """The scheme part of the URL.

        e.g. `https` in `https://foo.com,bar.com/path?query#fragment`
        """
        return self._url.scheme

    @property
    def path(self) -> str | None:
        """The path part of the URL, or `None`.

        e.g. `/path` in `https://foo.com,bar.com/path?query#fragment`
        """
        return self._url.path

    @property
    def query(self) -> str | None:
        """The query part of the URL, or `None`.

        e.g. `query` in `https://foo.com,bar.com/path?query#fragment`
        """
        return self._url.query

    def query_params(self) -> list[tuple[str, str]]:
        """The query part of the URL as a list of key-value pairs.

        e.g. `[('foo', 'bar')]` in `https://foo.com,bar.com/path?foo=bar#fragment`
        """
        return self._url.query_params()

    @property
    def fragment(self) -> str | None:
        """The fragment part of the URL, or `None`.

        e.g. `fragment` in `https://foo.com,bar.com/path?query#fragment`
        """
        return self._url.fragment

    def hosts(self) -> list[MultiHostHost]:
        '''The hosts of the `MultiHostUrl` as [`MultiHostHost`][pydantic_core.MultiHostHost] typed dicts.

        ```python
        from pydantic_core import MultiHostUrl

        mhu = MultiHostUrl('https://foo.com:123,foo:bar@bar.com/path')
        print(mhu.hosts())
        """
        [
            {'username': None, 'password': None, 'host': 'foo.com', 'port': 123},
            {'username': 'foo', 'password': 'bar', 'host': 'bar.com', 'port': 443}
        ]
        ```
        Returns:
            A list of dicts, each representing a host.
        '''
        return self._url.hosts()

    def encoded_string(self) -> str:
        """The URL's encoded string representation via __str__().

        This returns the punycode-encoded host version of the URL as a string.
        """
        return str(self)

    def unicode_string(self) -> str:
        """The URL as a unicode string, unlike `__str__()` this will not punycode encode the hosts."""
        return self._url.unicode_string()

    def __str__(self) -> str:
        """The URL as a string, this will punycode encode the host if required."""
        return str(self._url)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({str(self._url)!r})'

    def __deepcopy__(self, memo: dict) -> Self:
        return self.__class__(self._url)

    def __eq__(self, other: Any) -> bool:
        return self.__class__ is other.__class__ and self._url == other._url

    def __hash__(self) -> int:
        return hash(self._url)

    def __len__(self) -> int:
        return len(str(self._url))

    @classmethod
    def build(
        cls,
        *,
        scheme: str,
        hosts: list[MultiHostHost] | None = None,
        username: str | None = None,
        password: str | None = None,
        host: str | None = None,
        port: int | None = None,
        path: str | None = None,
        query: str | None = None,
        fragment: str | None = None,
    ) -> Self:
        """Build a new `MultiHostUrl` instance from its component parts.

        This method takes either `hosts` - a list of `MultiHostHost` typed dicts, or the individual components
        `username`, `password`, `host` and `port`.

        Args:
            scheme: The scheme part of the URL.
            hosts: Multiple hosts to build the URL from.
            username: The username part of the URL.
            password: The password part of the URL.
            host: The host part of the URL.
            port: The port part of the URL.
            path: The path part of the URL.
            query: The query part of the URL, or omit for no query.
            fragment: The fragment part of the URL, or omit for no fragment.

        Returns:
            An instance of `MultiHostUrl`
        """
        return cls(
            _CoreMultiHostUrl.build(
                scheme=scheme,
                hosts=hosts,
                username=username,
                password=password,
                host=host,
                port=port,
                path=path,
                query=query,
                fragment=fragment,
            )
        )

    @classmethod
    def serialize_url(cls, url: Any, info: core_schema.SerializationInfo) -> str | Self:
        if not isinstance(url, cls):
            raise PydanticSerializationUnexpectedValue(
                f"Expected `{cls}` but got `{type(url)}` with value `'{url}'` - serialized value may not be as expected."
            )
        if info.mode == 'json':
            return str(url)
        return url

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[_BaseMultiHostUrl], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def wrap_val(v, h):
            if isinstance(v, source):
                return v
            if isinstance(v, _BaseMultiHostUrl):
                v = str(v)
            core_url = h(v)
            instance = source.__new__(source)
            instance._url = core_url
            return instance

        return core_schema.no_info_wrap_validator_function(
            wrap_val,
            schema=core_schema.multi_host_url_schema(**cls._constraints.defined_constraints),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.serialize_url, info_arg=True, when_used='always'
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: _schema_generation_shared.GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        # we use the url schema for json schema generation, but we might have to extract it from
        # the function-wrap schema we use as a tool for validation on initialization
        inner_schema = core_schema['schema'] if core_schema['type'] == 'function-wrap' else core_schema
        return handler(inner_schema)

    __pydantic_serializer__ = SchemaSerializer(core_schema.any_schema(serialization=core_schema.to_string_ser_schema()))


@lru_cache
def _build_type_adapter(cls: type[_BaseUrl | _BaseMultiHostUrl]) -> TypeAdapter:
    return TypeAdapter(cls)


class AnyUrl(_BaseUrl):
    """Base type for all URLs.

    * Any scheme allowed
    * Top-level domain (TLD) not required
    * Host not required

    Assuming an input URL of `http://samuel:pass@example.com:8000/the/path/?query=here#fragment=is;this=bit`,
    the types export the following properties:

    - `scheme`: the URL scheme (`http`), always set.
    - `host`: the URL host (`example.com`).
    - `username`: optional username if included (`samuel`).
    - `password`: optional password if included (`pass`).
    - `port`: optional port (`8000`).
    - `path`: optional path (`/the/path/`).
    - `query`: optional URL query (for example, `GET` arguments or "search string", such as `query=here`).
    - `fragment`: optional fragment (`fragment=is;this=bit`).
    """


# Note: all single host urls inherit from `AnyUrl` to preserve compatibility with pre-v2.10 code
# Where urls were annotated variants of `AnyUrl`, which was an alias to `pydantic_core.Url`


class AnyHttpUrl(AnyUrl):
    """A type that will accept any http or https URL.

    * TLD not required
    * Host not required
    """

    _constraints = UrlConstraints(allowed_schemes=['http', 'https'])


class HttpUrl(AnyUrl):
    """A type that will accept any http or https URL.

    * TLD not required
    * Host not required
    * Max length 2083

    ```python
    from pydantic import BaseModel, HttpUrl, ValidationError

    class MyModel(BaseModel):
        url: HttpUrl

    m = MyModel(url='http://www.example.com')  # (1)!
    print(m.url)
    #> http://www.example.com/

    try:
        MyModel(url='ftp://invalid.url')
    except ValidationError as e:
        print(e)
        '''
        1 validation error for MyModel
        url
          URL scheme should be 'http' or 'https' [type=url_scheme, input_value='ftp://invalid.url', input_type=str]
        '''

    try:
        MyModel(url='not a url')
    except ValidationError as e:
        print(e)
        '''
        1 validation error for MyModel
        url
          Input should be a valid URL, relative URL without a base [type=url_parsing, input_value='not a url', input_type=str]
        '''
    ```

    1. Note: mypy would prefer `m = MyModel(url=HttpUrl('http://www.example.com'))`, but Pydantic will convert the string to an HttpUrl instance anyway.

    "International domains" (e.g. a URL where the host or TLD includes non-ascii characters) will be encoded via
    [punycode](https://en.wikipedia.org/wiki/Punycode) (see
    [this article](https://www.xudongz.com/blog/2017/idn-phishing/) for a good description of why this is important):

    ```python
    from pydantic import BaseModel, HttpUrl

    class MyModel(BaseModel):
        url: HttpUrl

    m1 = MyModel(url='http://puny£code.com')
    print(m1.url)
    #> http://xn--punycode-eja.com/
    m2 = MyModel(url='https://www.аррӏе.com/')
    print(m2.url)
    #> https://www.xn--80ak6aa92e.com/
    m3 = MyModel(url='https://www.example.珠宝/')
    print(m3.url)
    #> https://www.example.xn--pbt977c/
    ```


    !!! warning "Underscores in Hostnames"
        In Pydantic, underscores are allowed in all parts of a domain except the TLD.
        Technically this might be wrong - in theory the hostname cannot have underscores, but subdomains can.

        To explain this; consider the following two cases:

        - `exam_ple.co.uk`: the hostname is `exam_ple`, which should not be allowed since it contains an underscore.
        - `foo_bar.example.com` the hostname is `example`, which should be allowed since the underscore is in the subdomain.

        Without having an exhaustive list of TLDs, it would be impossible to differentiate between these two. Therefore
        underscores are allowed, but you can always do further validation in a validator if desired.

        Also, Chrome, Firefox, and Safari all currently accept `http://exam_ple.com` as a URL, so we're in good
        (or at least big) company.
    """

    _constraints = UrlConstraints(max_length=2083, allowed_schemes=['http', 'https'])


class AnyWebsocketUrl(AnyUrl):
    """A type that will accept any ws or wss URL.

    * TLD not required
    * Host not required
    """

    _constraints = UrlConstraints(allowed_schemes=['ws', 'wss'])


class WebsocketUrl(AnyUrl):
    """A type that will accept any ws or wss URL.

    * TLD not required
    * Host not required
    * Max length 2083
    """

    _constraints = UrlConstraints(max_length=2083, allowed_schemes=['ws', 'wss'])


class FileUrl(AnyUrl):
    """A type that will accept any file URL.

    * Host not required
    """

    _constraints = UrlConstraints(allowed_schemes=['file'])


class FtpUrl(AnyUrl):
    """A type that will accept ftp URL.

    * TLD not required
    * Host not required
    """

    _constraints = UrlConstraints(allowed_schemes=['ftp'])


class PostgresDsn(_BaseMultiHostUrl):
    """A type that will accept any Postgres DSN.

    * User info required
    * TLD not required
    * Host required
    * Supports multiple hosts

    If further validation is required, these properties can be used by validators to enforce specific behaviour:

    ```python
    from pydantic import (
        BaseModel,
        HttpUrl,
        PostgresDsn,
        ValidationError,
        field_validator,
    )

    class MyModel(BaseModel):
        url: HttpUrl

    m = MyModel(url='http://www.example.com')

    # the repr() method for a url will display all properties of the url
    print(repr(m.url))
    #> HttpUrl('http://www.example.com/')
    print(m.url.scheme)
    #> http
    print(m.url.host)
    #> www.example.com
    print(m.url.port)
    #> 80

    class MyDatabaseModel(BaseModel):
        db: PostgresDsn

        @field_validator('db')
        def check_db_name(cls, v):
            assert v.path and len(v.path) > 1, 'database must be provided'
            return v

    m = MyDatabaseModel(db='postgres://user:pass@localhost:5432/foobar')
    print(m.db)
    #> postgres://user:pass@localhost:5432/foobar

    try:
        MyDatabaseModel(db='postgres://user:pass@localhost:5432')
    except ValidationError as e:
        print(e)
        '''
        1 validation error for MyDatabaseModel
        db
          Assertion failed, database must be provided
        assert (None)
         +  where None = PostgresDsn('postgres://user:pass@localhost:5432').path [type=assertion_error, input_value='postgres://user:pass@localhost:5432', input_type=str]
        '''
    ```
    """

    _constraints = UrlConstraints(
        host_required=True,
        allowed_schemes=[
            'postgres',
            'postgresql',
            'postgresql+asyncpg',
            'postgresql+pg8000',
            'postgresql+psycopg',
            'postgresql+psycopg2',
            'postgresql+psycopg2cffi',
            'postgresql+py-postgresql',
            'postgresql+pygresql',
        ],
    )

    @property
    def host(self) -> str:
        """The required URL host."""
        return self._url.host  # pyright: ignore[reportAttributeAccessIssue]


class CockroachDsn(AnyUrl):
    """A type that will accept any Cockroach DSN.

    * User info required
    * TLD not required
    * Host required
    """

    _constraints = UrlConstraints(
        host_required=True,
        allowed_schemes=[
            'cockroachdb',
            'cockroachdb+psycopg2',
            'cockroachdb+asyncpg',
        ],
    )

    @property
    def host(self) -> str:
        """The required URL host."""
        return self._url.host  # pyright: ignore[reportReturnType]


class AmqpDsn(AnyUrl):
    """A type that will accept any AMQP DSN.

    * User info required
    * TLD not required
    * Host not required
    """

    _constraints = UrlConstraints(allowed_schemes=['amqp', 'amqps'])


class RedisDsn(AnyUrl):
    """A type that will accept any Redis DSN.

    * User info required
    * TLD not required
    * Host required (e.g., `rediss://:pass@localhost`)
    """

    _constraints = UrlConstraints(
        allowed_schemes=['redis', 'rediss'],
        default_host='localhost',
        default_port=6379,
        default_path='/0',
        host_required=True,
    )

    @property
    def host(self) -> str:
        """The required URL host."""
        return self._url.host  # pyright: ignore[reportReturnType]


class MongoDsn(_BaseMultiHostUrl):
    """A type that will accept any MongoDB DSN.

    * User info not required
    * Database name not required
    * Port not required
    * User info may be passed without user part (e.g., `mongodb://mongodb0.example.com:27017`).
    """

    _constraints = UrlConstraints(allowed_schemes=['mongodb', 'mongodb+srv'], default_port=27017)


class KafkaDsn(AnyUrl):
    """A type that will accept any Kafka DSN.

    * User info required
    * TLD not required
    * Host not required
    """

    _constraints = UrlConstraints(allowed_schemes=['kafka'], default_host='localhost', default_port=9092)


class NatsDsn(_BaseMultiHostUrl):
    """A type that will accept any NATS DSN.

    NATS is a connective technology built for the ever increasingly hyper-connected world.
    It is a single technology that enables applications to securely communicate across
    any combination of cloud vendors, on-premise, edge, web and mobile, and devices.
    More: https://nats.io
    """

    _constraints = UrlConstraints(
        allowed_schemes=['nats', 'tls', 'ws', 'wss'], default_host='localhost', default_port=4222
    )


class MySQLDsn(AnyUrl):
    """A type that will accept any MySQL DSN.

    * User info required
    * TLD not required
    * Host not required
    """

    _constraints = UrlConstraints(
        allowed_schemes=[
            'mysql',
            'mysql+mysqlconnector',
            'mysql+aiomysql',
            'mysql+asyncmy',
            'mysql+mysqldb',
            'mysql+pymysql',
            'mysql+cymysql',
            'mysql+pyodbc',
        ],
        default_port=3306,
        host_required=True,
    )


class MariaDBDsn(AnyUrl):
    """A type that will accept any MariaDB DSN.

    * User info required
    * TLD not required
    * Host not required
    """

    _constraints = UrlConstraints(
        allowed_schemes=['mariadb', 'mariadb+mariadbconnector', 'mariadb+pymysql'],
        default_port=3306,
    )


class ClickHouseDsn(AnyUrl):
    """A type that will accept any ClickHouse DSN.

    * User info required
    * TLD not required
    * Host not required
    """

    _constraints = UrlConstraints(
        allowed_schemes=[
            'clickhouse+native',
            'clickhouse+asynch',
            'clickhouse+http',
            'clickhouse',
            'clickhouses',
            'clickhousedb',
        ],
        default_host='localhost',
        default_port=9000,
    )


class SnowflakeDsn(AnyUrl):
    """A type that will accept any Snowflake DSN.

    * User info required
    * TLD not required
    * Host required
    """

    _constraints = UrlConstraints(
        allowed_schemes=['snowflake'],
        host_required=True,
    )

    @property
    def host(self) -> str:
        """The required URL host."""
        return self._url.host  # pyright: ignore[reportReturnType]


def import_email_validator() -> None:
    global email_validator
    try:
        import email_validator
    except ImportError as e:
        raise ImportError('email-validator is not installed, run `pip install pydantic[email]`') from e
    if not version('email-validator').partition('.')[0] == '2':
        raise ImportError('email-validator version >= 2.0 required, run pip install -U email-validator')


if TYPE_CHECKING:
    EmailStr = Annotated[str, ...]
else:

    class EmailStr:
        """
        Info:
            To use this type, you need to install the optional
            [`email-validator`](https://github.com/JoshData/python-email-validator) package:

            ```bash
            pip install email-validator
            ```

        Validate email addresses.

        ```python
        from pydantic import BaseModel, EmailStr

        class Model(BaseModel):
            email: EmailStr

        print(Model(email='contact@mail.com'))
        #> email='contact@mail.com'
        ```
        """  # noqa: D212

        @classmethod
        def __get_pydantic_core_schema__(
            cls,
            _source: type[Any],
            _handler: GetCoreSchemaHandler,
        ) -> core_schema.CoreSchema:
            import_email_validator()
            return core_schema.no_info_after_validator_function(cls._validate, core_schema.str_schema())

        @classmethod
        def __get_pydantic_json_schema__(
            cls, core_schema: core_schema.CoreSchema, handler: _schema_generation_shared.GetJsonSchemaHandler
        ) -> JsonSchemaValue:
            field_schema = handler(core_schema)
            field_schema.update(type='string', format='email')
            return field_schema

        @classmethod
        def _validate(cls, input_value: str, /) -> str:
            return validate_email(input_value)[1]


class NameEmail(_repr.Representation):
    """
    Info:
        To use this type, you need to install the optional
        [`email-validator`](https://github.com/JoshData/python-email-validator) package:

        ```bash
        pip install email-validator
        ```

    Validate a name and email address combination, as specified by
    [RFC 5322](https://datatracker.ietf.org/doc/html/rfc5322#section-3.4).

    The `NameEmail` has two properties: `name` and `email`.
    In case the `name` is not provided, it's inferred from the email address.

    ```python
    from pydantic import BaseModel, NameEmail

    class User(BaseModel):
        email: NameEmail

    user = User(email='Fred Bloggs <fred.bloggs@example.com>')
    print(user.email)
    #> Fred Bloggs <fred.bloggs@example.com>
    print(user.email.name)
    #> Fred Bloggs

    user = User(email='fred.bloggs@example.com')
    print(user.email)
    #> fred.bloggs <fred.bloggs@example.com>
    print(user.email.name)
    #> fred.bloggs
    ```
    """  # noqa: D212

    __slots__ = 'name', 'email'

    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, NameEmail) and (self.name, self.email) == (other.name, other.email)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: _schema_generation_shared.GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        field_schema = handler(core_schema)
        field_schema.update(type='string', format='name-email')
        return field_schema

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source: type[Any],
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        import_email_validator()

        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.json_or_python_schema(
                json_schema=core_schema.str_schema(),
                python_schema=core_schema.union_schema(
                    [core_schema.is_instance_schema(cls), core_schema.str_schema()],
                    custom_error_type='name_email_type',
                    custom_error_message='Input is not a valid NameEmail',
                ),
                serialization=core_schema.to_string_ser_schema(),
            ),
        )

    @classmethod
    def _validate(cls, input_value: Self | str, /) -> Self:
        if isinstance(input_value, str):
            name, email = validate_email(input_value)
            return cls(name, email)
        else:
            return input_value

    def __str__(self) -> str:
        if '@' in self.name:
            return f'"{self.name}" <{self.email}>'

        return f'{self.name} <{self.email}>'


IPvAnyAddressType: TypeAlias = 'IPv4Address | IPv6Address'
IPvAnyInterfaceType: TypeAlias = 'IPv4Interface | IPv6Interface'
IPvAnyNetworkType: TypeAlias = 'IPv4Network | IPv6Network'

if TYPE_CHECKING:
    IPvAnyAddress = IPvAnyAddressType
    IPvAnyInterface = IPvAnyInterfaceType
    IPvAnyNetwork = IPvAnyNetworkType
else:

    class IPvAnyAddress:
        """Validate an IPv4 or IPv6 address.

        ```python
        from pydantic import BaseModel
        from pydantic.networks import IPvAnyAddress

        class IpModel(BaseModel):
            ip: IPvAnyAddress

        print(IpModel(ip='127.0.0.1'))
        #> ip=IPv4Address('127.0.0.1')

        try:
            IpModel(ip='http://www.example.com')
        except ValueError as e:
            print(e.errors())
            '''
            [
                {
                    'type': 'ip_any_address',
                    'loc': ('ip',),
                    'msg': 'value is not a valid IPv4 or IPv6 address',
                    'input': 'http://www.example.com',
                }
            ]
            '''
        ```
        """

        __slots__ = ()

        def __new__(cls, value: Any) -> IPvAnyAddressType:
            """Validate an IPv4 or IPv6 address."""
            try:
                return IPv4Address(value)
            except ValueError:
                pass

            try:
                return IPv6Address(value)
            except ValueError:
                raise PydanticCustomError('ip_any_address', 'value is not a valid IPv4 or IPv6 address')

        @classmethod
        def __get_pydantic_json_schema__(
            cls, core_schema: core_schema.CoreSchema, handler: _schema_generation_shared.GetJsonSchemaHandler
        ) -> JsonSchemaValue:
            field_schema = {}
            field_schema.update(type='string', format='ipvanyaddress')
            return field_schema

        @classmethod
        def __get_pydantic_core_schema__(
            cls,
            _source: type[Any],
            _handler: GetCoreSchemaHandler,
        ) -> core_schema.CoreSchema:
            return core_schema.no_info_plain_validator_function(
                cls._validate, serialization=core_schema.to_string_ser_schema()
            )

        @classmethod
        def _validate(cls, input_value: Any, /) -> IPvAnyAddressType:
            return cls(input_value)  # type: ignore[return-value]

    class IPvAnyInterface:
        """Validate an IPv4 or IPv6 interface."""

        __slots__ = ()

        def __new__(cls, value: NetworkType) -> IPvAnyInterfaceType:
            """Validate an IPv4 or IPv6 interface."""
            try:
                return IPv4Interface(value)
            except ValueError:
                pass

            try:
                return IPv6Interface(value)
            except ValueError:
                raise PydanticCustomError('ip_any_interface', 'value is not a valid IPv4 or IPv6 interface')

        @classmethod
        def __get_pydantic_json_schema__(
            cls, core_schema: core_schema.CoreSchema, handler: _schema_generation_shared.GetJsonSchemaHandler
        ) -> JsonSchemaValue:
            field_schema = {}
            field_schema.update(type='string', format='ipvanyinterface')
            return field_schema

        @classmethod
        def __get_pydantic_core_schema__(
            cls,
            _source: type[Any],
            _handler: GetCoreSchemaHandler,
        ) -> core_schema.CoreSchema:
            return core_schema.no_info_plain_validator_function(
                cls._validate, serialization=core_schema.to_string_ser_schema()
            )

        @classmethod
        def _validate(cls, input_value: NetworkType, /) -> IPvAnyInterfaceType:
            return cls(input_value)  # type: ignore[return-value]

    class IPvAnyNetwork:
        """Validate an IPv4 or IPv6 network."""

        __slots__ = ()

        def __new__(cls, value: NetworkType) -> IPvAnyNetworkType:
            """Validate an IPv4 or IPv6 network."""
            # Assume IP Network is defined with a default value for `strict` argument.
            # Define your own class if you want to specify network address check strictness.
            try:
                return IPv4Network(value)
            except ValueError:
                pass

            try:
                return IPv6Network(value)
            except ValueError:
                raise PydanticCustomError('ip_any_network', 'value is not a valid IPv4 or IPv6 network')

        @classmethod
        def __get_pydantic_json_schema__(
            cls, core_schema: core_schema.CoreSchema, handler: _schema_generation_shared.GetJsonSchemaHandler
        ) -> JsonSchemaValue:
            field_schema = {}
            field_schema.update(type='string', format='ipvanynetwork')
            return field_schema

        @classmethod
        def __get_pydantic_core_schema__(
            cls,
            _source: type[Any],
            _handler: GetCoreSchemaHandler,
        ) -> core_schema.CoreSchema:
            return core_schema.no_info_plain_validator_function(
                cls._validate, serialization=core_schema.to_string_ser_schema()
            )

        @classmethod
        def _validate(cls, input_value: NetworkType, /) -> IPvAnyNetworkType:
            return cls(input_value)  # type: ignore[return-value]


def _build_pretty_email_regex() -> re.Pattern[str]:
    name_chars = r'[\w!#$%&\'*+\-/=?^_`{|}~]'
    unquoted_name_group = rf'((?:{name_chars}+\s+)*{name_chars}+)'
    quoted_name_group = r'"((?:[^"]|\")+)"'
    email_group = r'<(.+)>'
    return re.compile(rf'\s*(?:{unquoted_name_group}|{quoted_name_group})?\s*{email_group}\s*')


pretty_email_regex = _build_pretty_email_regex()

MAX_EMAIL_LENGTH = 2048
"""Maximum length for an email.
A somewhat arbitrary but very generous number compared to what is allowed by most implementations.
"""


def validate_email(value: str) -> tuple[str, str]:
    """Email address validation using [email-validator](https://pypi.org/project/email-validator/).

    Returns:
        A tuple containing the local part of the email (or the name for "pretty" email addresses)
            and the normalized email.

    Raises:
        PydanticCustomError: If the email is invalid.

    Note:
        Note that:

        * Raw IP address (literal) domain parts are not allowed.
        * `"John Doe <local_part@domain.com>"` style "pretty" email addresses are processed.
        * Spaces are striped from the beginning and end of addresses, but no error is raised.
    """
    if email_validator is None:
        import_email_validator()

    if len(value) > MAX_EMAIL_LENGTH:
        raise PydanticCustomError(
            'value_error',
            'value is not a valid email address: {reason}',
            {'reason': f'Length must not exceed {MAX_EMAIL_LENGTH} characters'},
        )

    m = pretty_email_regex.fullmatch(value)
    name: str | None = None
    if m:
        unquoted_name, quoted_name, value = m.groups()
        name = unquoted_name or quoted_name

    email = value.strip()

    try:
        parts = email_validator.validate_email(email, check_deliverability=False)
    except email_validator.EmailNotValidError as e:
        raise PydanticCustomError(
            'value_error', 'value is not a valid email address: {reason}', {'reason': str(e.args[0])}
        ) from e

    email = parts.normalized
    assert email is not None
    name = name or parts.local_part
    return name, email


__getattr__ = getattr_migration(__name__)

# === NexusCore/openenv\Lib\site-packages\win32\lib\rasutil.py ===
import win32ras

stateStrings = {
    win32ras.RASCS_OpenPort: "OpenPort",
    win32ras.RASCS_PortOpened: "PortOpened",
    win32ras.RASCS_ConnectDevice: "ConnectDevice",
    win32ras.RASCS_DeviceConnected: "DeviceConnected",
    win32ras.RASCS_AllDevicesConnected: "AllDevicesConnected",
    win32ras.RASCS_Authenticate: "Authenticate",
    win32ras.RASCS_AuthNotify: "AuthNotify",
    win32ras.RASCS_AuthRetry: "AuthRetry",
    win32ras.RASCS_AuthCallback: "AuthCallback",
    win32ras.RASCS_AuthChangePassword: "AuthChangePassword",
    win32ras.RASCS_AuthProject: "AuthProject",
    win32ras.RASCS_AuthLinkSpeed: "AuthLinkSpeed",
    win32ras.RASCS_AuthAck: "AuthAck",
    win32ras.RASCS_ReAuthenticate: "ReAuthenticate",
    win32ras.RASCS_Authenticated: "Authenticated",
    win32ras.RASCS_PrepareForCallback: "PrepareForCallback",
    win32ras.RASCS_WaitForModemReset: "WaitForModemReset",
    win32ras.RASCS_WaitForCallback: "WaitForCallback",
    win32ras.RASCS_Projected: "Projected",
    win32ras.RASCS_StartAuthentication: "StartAuthentication",
    win32ras.RASCS_CallbackComplete: "CallbackComplete",
    win32ras.RASCS_LogonNetwork: "LogonNetwork",
    win32ras.RASCS_Interactive: "Interactive",
    win32ras.RASCS_RetryAuthentication: "RetryAuthentication",
    win32ras.RASCS_CallbackSetByCaller: "CallbackSetByCaller",
    win32ras.RASCS_PasswordExpired: "PasswordExpired",
    win32ras.RASCS_Connected: "Connected",
    win32ras.RASCS_Disconnected: "Disconnected",
}


def TestCallback(hras, msg, state, error, exterror):
    print("Callback called with ", hras, msg, stateStrings[state], error, exterror)


def test(rasName="_ Divert Off"):
    return win32ras.Dial(None, None, (rasName,), TestCallback)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\emulation.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Emulation
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import network
from . import page


@dataclass
class SafeAreaInsets:
    #: Overrides safe-area-inset-top.
    top: typing.Optional[int] = None

    #: Overrides safe-area-max-inset-top.
    top_max: typing.Optional[int] = None

    #: Overrides safe-area-inset-left.
    left: typing.Optional[int] = None

    #: Overrides safe-area-max-inset-left.
    left_max: typing.Optional[int] = None

    #: Overrides safe-area-inset-bottom.
    bottom: typing.Optional[int] = None

    #: Overrides safe-area-max-inset-bottom.
    bottom_max: typing.Optional[int] = None

    #: Overrides safe-area-inset-right.
    right: typing.Optional[int] = None

    #: Overrides safe-area-max-inset-right.
    right_max: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        if self.top is not None:
            json['top'] = self.top
        if self.top_max is not None:
            json['topMax'] = self.top_max
        if self.left is not None:
            json['left'] = self.left
        if self.left_max is not None:
            json['leftMax'] = self.left_max
        if self.bottom is not None:
            json['bottom'] = self.bottom
        if self.bottom_max is not None:
            json['bottomMax'] = self.bottom_max
        if self.right is not None:
            json['right'] = self.right
        if self.right_max is not None:
            json['rightMax'] = self.right_max
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            top=int(json['top']) if 'top' in json else None,
            top_max=int(json['topMax']) if 'topMax' in json else None,
            left=int(json['left']) if 'left' in json else None,
            left_max=int(json['leftMax']) if 'leftMax' in json else None,
            bottom=int(json['bottom']) if 'bottom' in json else None,
            bottom_max=int(json['bottomMax']) if 'bottomMax' in json else None,
            right=int(json['right']) if 'right' in json else None,
            right_max=int(json['rightMax']) if 'rightMax' in json else None,
        )


@dataclass
class ScreenOrientation:
    '''
    Screen orientation.
    '''
    #: Orientation type.
    type_: str

    #: Orientation angle.
    angle: int

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['angle'] = self.angle
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            angle=int(json['angle']),
        )


@dataclass
class DisplayFeature:
    #: Orientation of a display feature in relation to screen
    orientation: str

    #: The offset from the screen origin in either the x (for vertical
    #: orientation) or y (for horizontal orientation) direction.
    offset: int

    #: A display feature may mask content such that it is not physically
    #: displayed - this length along with the offset describes this area.
    #: A display feature that only splits content will have a 0 mask_length.
    mask_length: int

    def to_json(self):
        json = dict()
        json['orientation'] = self.orientation
        json['offset'] = self.offset
        json['maskLength'] = self.mask_length
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            orientation=str(json['orientation']),
            offset=int(json['offset']),
            mask_length=int(json['maskLength']),
        )


@dataclass
class DevicePosture:
    #: Current posture of the device
    type_: str

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
        )


@dataclass
class MediaFeature:
    name: str

    value: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
        )


class VirtualTimePolicy(enum.Enum):
    '''
    advance: If the scheduler runs out of immediate work, the virtual time base may fast forward to
    allow the next delayed task (if any) to run; pause: The virtual time base may not advance;
    pauseIfNetworkFetchesPending: The virtual time base may not advance if there are any pending
    resource fetches.
    '''
    ADVANCE = "advance"
    PAUSE = "pause"
    PAUSE_IF_NETWORK_FETCHES_PENDING = "pauseIfNetworkFetchesPending"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class UserAgentBrandVersion:
    '''
    Used to specify User Agent Client Hints to emulate. See https://wicg.github.io/ua-client-hints
    '''
    brand: str

    version: str

    def to_json(self):
        json = dict()
        json['brand'] = self.brand
        json['version'] = self.version
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            brand=str(json['brand']),
            version=str(json['version']),
        )


@dataclass
class UserAgentMetadata:
    '''
    Used to specify User Agent Client Hints to emulate. See https://wicg.github.io/ua-client-hints
    Missing optional values will be filled in by the target with what it would normally use.
    '''
    platform: str

    platform_version: str

    architecture: str

    model: str

    mobile: bool

    #: Brands appearing in Sec-CH-UA.
    brands: typing.Optional[typing.List[UserAgentBrandVersion]] = None

    #: Brands appearing in Sec-CH-UA-Full-Version-List.
    full_version_list: typing.Optional[typing.List[UserAgentBrandVersion]] = None

    full_version: typing.Optional[str] = None

    bitness: typing.Optional[str] = None

    wow64: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['platform'] = self.platform
        json['platformVersion'] = self.platform_version
        json['architecture'] = self.architecture
        json['model'] = self.model
        json['mobile'] = self.mobile
        if self.brands is not None:
            json['brands'] = [i.to_json() for i in self.brands]
        if self.full_version_list is not None:
            json['fullVersionList'] = [i.to_json() for i in self.full_version_list]
        if self.full_version is not None:
            json['fullVersion'] = self.full_version
        if self.bitness is not None:
            json['bitness'] = self.bitness
        if self.wow64 is not None:
            json['wow64'] = self.wow64
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            platform=str(json['platform']),
            platform_version=str(json['platformVersion']),
            architecture=str(json['architecture']),
            model=str(json['model']),
            mobile=bool(json['mobile']),
            brands=[UserAgentBrandVersion.from_json(i) for i in json['brands']] if 'brands' in json else None,
            full_version_list=[UserAgentBrandVersion.from_json(i) for i in json['fullVersionList']] if 'fullVersionList' in json else None,
            full_version=str(json['fullVersion']) if 'fullVersion' in json else None,
            bitness=str(json['bitness']) if 'bitness' in json else None,
            wow64=bool(json['wow64']) if 'wow64' in json else None,
        )


class SensorType(enum.Enum):
    '''
    Used to specify sensor types to emulate.
    See https://w3c.github.io/sensors/#automation for more information.
    '''
    ABSOLUTE_ORIENTATION = "absolute-orientation"
    ACCELEROMETER = "accelerometer"
    AMBIENT_LIGHT = "ambient-light"
    GRAVITY = "gravity"
    GYROSCOPE = "gyroscope"
    LINEAR_ACCELERATION = "linear-acceleration"
    MAGNETOMETER = "magnetometer"
    RELATIVE_ORIENTATION = "relative-orientation"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SensorMetadata:
    available: typing.Optional[bool] = None

    minimum_frequency: typing.Optional[float] = None

    maximum_frequency: typing.Optional[float] = None

    def to_json(self):
        json = dict()
        if self.available is not None:
            json['available'] = self.available
        if self.minimum_frequency is not None:
            json['minimumFrequency'] = self.minimum_frequency
        if self.maximum_frequency is not None:
            json['maximumFrequency'] = self.maximum_frequency
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            available=bool(json['available']) if 'available' in json else None,
            minimum_frequency=float(json['minimumFrequency']) if 'minimumFrequency' in json else None,
            maximum_frequency=float(json['maximumFrequency']) if 'maximumFrequency' in json else None,
        )


@dataclass
class SensorReadingSingle:
    value: float

    def to_json(self):
        json = dict()
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=float(json['value']),
        )


@dataclass
class SensorReadingXYZ:
    x: float

    y: float

    z: float

    def to_json(self):
        json = dict()
        json['x'] = self.x
        json['y'] = self.y
        json['z'] = self.z
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            x=float(json['x']),
            y=float(json['y']),
            z=float(json['z']),
        )


@dataclass
class SensorReadingQuaternion:
    x: float

    y: float

    z: float

    w: float

    def to_json(self):
        json = dict()
        json['x'] = self.x
        json['y'] = self.y
        json['z'] = self.z
        json['w'] = self.w
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            x=float(json['x']),
            y=float(json['y']),
            z=float(json['z']),
            w=float(json['w']),
        )


@dataclass
class SensorReading:
    single: typing.Optional[SensorReadingSingle] = None

    xyz: typing.Optional[SensorReadingXYZ] = None

    quaternion: typing.Optional[SensorReadingQuaternion] = None

    def to_json(self):
        json = dict()
        if self.single is not None:
            json['single'] = self.single.to_json()
        if self.xyz is not None:
            json['xyz'] = self.xyz.to_json()
        if self.quaternion is not None:
            json['quaternion'] = self.quaternion.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            single=SensorReadingSingle.from_json(json['single']) if 'single' in json else None,
            xyz=SensorReadingXYZ.from_json(json['xyz']) if 'xyz' in json else None,
            quaternion=SensorReadingQuaternion.from_json(json['quaternion']) if 'quaternion' in json else None,
        )


class PressureSource(enum.Enum):
    CPU = "cpu"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PressureState(enum.Enum):
    NOMINAL = "nominal"
    FAIR = "fair"
    SERIOUS = "serious"
    CRITICAL = "critical"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PressureMetadata:
    available: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        if self.available is not None:
            json['available'] = self.available
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            available=bool(json['available']) if 'available' in json else None,
        )


class DisabledImageType(enum.Enum):
    '''
    Enum of image types that can be disabled.
    '''
    AVIF = "avif"
    WEBP = "webp"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def can_emulate() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Tells whether emulation is supported.

    :returns: True if emulation is supported.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.canEmulate',
    }
    json = yield cmd_dict
    return bool(json['result'])


def clear_device_metrics_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears the overridden device metrics.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.clearDeviceMetricsOverride',
    }
    json = yield cmd_dict


def clear_geolocation_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears the overridden Geolocation Position and Error.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.clearGeolocationOverride',
    }
    json = yield cmd_dict


def reset_page_scale_factor() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Requests that page scale factor is reset to initial values.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.resetPageScaleFactor',
    }
    json = yield cmd_dict


def set_focus_emulation_enabled(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables or disables simulating a focused and active page.

    **EXPERIMENTAL**

    :param enabled: Whether to enable to disable focus emulation.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setFocusEmulationEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_auto_dark_mode_override(
        enabled: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Automatically render all web contents using a dark theme.

    **EXPERIMENTAL**

    :param enabled: *(Optional)* Whether to enable or disable automatic dark mode. If not specified, any existing override will be cleared.
    '''
    params: T_JSON_DICT = dict()
    if enabled is not None:
        params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setAutoDarkModeOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_cpu_throttling_rate(
        rate: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables CPU throttling to emulate slow CPUs.

    :param rate: Throttling rate as a slowdown factor (1 is no throttle, 2 is 2x slowdown, etc).
    '''
    params: T_JSON_DICT = dict()
    params['rate'] = rate
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setCPUThrottlingRate',
        'params': params,
    }
    json = yield cmd_dict


def set_default_background_color_override(
        color: typing.Optional[dom.RGBA] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets or clears an override of the default background color of the frame. This override is used
    if the content does not specify one.

    :param color: *(Optional)* RGBA of the default background color. If not specified, any existing override will be cleared.
    '''
    params: T_JSON_DICT = dict()
    if color is not None:
        params['color'] = color.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setDefaultBackgroundColorOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_safe_area_insets_override(
        insets: SafeAreaInsets
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides the values for env(safe-area-inset-*) and env(safe-area-max-inset-*). Unset values will cause the
    respective variables to be undefined, even if previously overridden.

    **EXPERIMENTAL**

    :param insets:
    '''
    params: T_JSON_DICT = dict()
    params['insets'] = insets.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setSafeAreaInsetsOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_device_metrics_override(
        width: int,
        height: int,
        device_scale_factor: float,
        mobile: bool,
        scale: typing.Optional[float] = None,
        screen_width: typing.Optional[int] = None,
        screen_height: typing.Optional[int] = None,
        position_x: typing.Optional[int] = None,
        position_y: typing.Optional[int] = None,
        dont_set_visible_size: typing.Optional[bool] = None,
        screen_orientation: typing.Optional[ScreenOrientation] = None,
        viewport: typing.Optional[page.Viewport] = None,
        display_feature: typing.Optional[DisplayFeature] = None,
        device_posture: typing.Optional[DevicePosture] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides the values of device screen dimensions (window.screen.width, window.screen.height,
    window.innerWidth, window.innerHeight, and "device-width"/"device-height"-related CSS media
    query results).

    :param width: Overriding width value in pixels (minimum 0, maximum 10000000). 0 disables the override.
    :param height: Overriding height value in pixels (minimum 0, maximum 10000000). 0 disables the override.
    :param device_scale_factor: Overriding device scale factor value. 0 disables the override.
    :param mobile: Whether to emulate mobile device. This includes viewport meta tag, overlay scrollbars, text autosizing and more.
    :param scale: **(EXPERIMENTAL)** *(Optional)* Scale to apply to resulting view image.
    :param screen_width: **(EXPERIMENTAL)** *(Optional)* Overriding screen width value in pixels (minimum 0, maximum 10000000).
    :param screen_height: **(EXPERIMENTAL)** *(Optional)* Overriding screen height value in pixels (minimum 0, maximum 10000000).
    :param position_x: **(EXPERIMENTAL)** *(Optional)* Overriding view X position on screen in pixels (minimum 0, maximum 10000000).
    :param position_y: **(EXPERIMENTAL)** *(Optional)* Overriding view Y position on screen in pixels (minimum 0, maximum 10000000).
    :param dont_set_visible_size: **(EXPERIMENTAL)** *(Optional)* Do not set visible view size, rely upon explicit setVisibleSize call.
    :param screen_orientation: *(Optional)* Screen orientation override.
    :param viewport: **(EXPERIMENTAL)** *(Optional)* If set, the visible area of the page will be overridden to this viewport. This viewport change is not observed by the page, e.g. viewport-relative elements do not change positions.
    :param display_feature: **(EXPERIMENTAL)** *(Optional)* If set, the display feature of a multi-segment screen. If not set, multi-segment support is turned-off. Deprecated, use Emulation.setDisplayFeaturesOverride.
    :param device_posture: **(EXPERIMENTAL)** *(Optional)* If set, the posture of a foldable device. If not set the posture is set to continuous. Deprecated, use Emulation.setDevicePostureOverride.
    '''
    params: T_JSON_DICT = dict()
    params['width'] = width
    params['height'] = height
    params['deviceScaleFactor'] = device_scale_factor
    params['mobile'] = mobile
    if scale is not None:
        params['scale'] = scale
    if screen_width is not None:
        params['screenWidth'] = screen_width
    if screen_height is not None:
        params['screenHeight'] = screen_height
    if position_x is not None:
        params['positionX'] = position_x
    if position_y is not None:
        params['positionY'] = position_y
    if dont_set_visible_size is not None:
        params['dontSetVisibleSize'] = dont_set_visible_size
    if screen_orientation is not None:
        params['screenOrientation'] = screen_orientation.to_json()
    if viewport is not None:
        params['viewport'] = viewport.to_json()
    if display_feature is not None:
        params['displayFeature'] = display_feature.to_json()
    if device_posture is not None:
        params['devicePosture'] = device_posture.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setDeviceMetricsOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_device_posture_override(
        posture: DevicePosture
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Start reporting the given posture value to the Device Posture API.
    This override can also be set in setDeviceMetricsOverride().

    **EXPERIMENTAL**

    :param posture:
    '''
    params: T_JSON_DICT = dict()
    params['posture'] = posture.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setDevicePostureOverride',
        'params': params,
    }
    json = yield cmd_dict


def clear_device_posture_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears a device posture override set with either setDeviceMetricsOverride()
    or setDevicePostureOverride() and starts using posture information from the
    platform again.
    Does nothing if no override is set.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.clearDevicePostureOverride',
    }
    json = yield cmd_dict


def set_display_features_override(
        features: typing.List[DisplayFeature]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Start using the given display features to pupulate the Viewport Segments API.
    This override can also be set in setDeviceMetricsOverride().

    **EXPERIMENTAL**

    :param features:
    '''
    params: T_JSON_DICT = dict()
    params['features'] = [i.to_json() for i in features]
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setDisplayFeaturesOverride',
        'params': params,
    }
    json = yield cmd_dict


def clear_display_features_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears the display features override set with either setDeviceMetricsOverride()
    or setDisplayFeaturesOverride() and starts using display features from the
    platform again.
    Does nothing if no override is set.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.clearDisplayFeaturesOverride',
    }
    json = yield cmd_dict


def set_scrollbars_hidden(
        hidden: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param hidden: Whether scrollbars should be always hidden.
    '''
    params: T_JSON_DICT = dict()
    params['hidden'] = hidden
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setScrollbarsHidden',
        'params': params,
    }
    json = yield cmd_dict


def set_document_cookie_disabled(
        disabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param disabled: Whether document.coookie API should be disabled.
    '''
    params: T_JSON_DICT = dict()
    params['disabled'] = disabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setDocumentCookieDisabled',
        'params': params,
    }
    json = yield cmd_dict


def set_emit_touch_events_for_mouse(
        enabled: bool,
        configuration: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param enabled: Whether touch emulation based on mouse input should be enabled.
    :param configuration: *(Optional)* Touch/gesture events configuration. Default: current platform.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    if configuration is not None:
        params['configuration'] = configuration
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setEmitTouchEventsForMouse',
        'params': params,
    }
    json = yield cmd_dict


def set_emulated_media(
        media: typing.Optional[str] = None,
        features: typing.Optional[typing.List[MediaFeature]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Emulates the given media type or media feature for CSS media queries.

    :param media: *(Optional)* Media type to emulate. Empty string disables the override.
    :param features: *(Optional)* Media features to emulate.
    '''
    params: T_JSON_DICT = dict()
    if media is not None:
        params['media'] = media
    if features is not None:
        params['features'] = [i.to_json() for i in features]
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setEmulatedMedia',
        'params': params,
    }
    json = yield cmd_dict


def set_emulated_vision_deficiency(
        type_: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Emulates the given vision deficiency.

    :param type_: Vision deficiency to emulate. Order: best-effort emulations come first, followed by any physiologically accurate emulations for medically recognized color vision deficiencies.
    '''
    params: T_JSON_DICT = dict()
    params['type'] = type_
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setEmulatedVisionDeficiency',
        'params': params,
    }
    json = yield cmd_dict


def set_geolocation_override(
        latitude: typing.Optional[float] = None,
        longitude: typing.Optional[float] = None,
        accuracy: typing.Optional[float] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides the Geolocation Position or Error. Omitting any of the parameters emulates position
    unavailable.

    :param latitude: *(Optional)* Mock latitude
    :param longitude: *(Optional)* Mock longitude
    :param accuracy: *(Optional)* Mock accuracy
    '''
    params: T_JSON_DICT = dict()
    if latitude is not None:
        params['latitude'] = latitude
    if longitude is not None:
        params['longitude'] = longitude
    if accuracy is not None:
        params['accuracy'] = accuracy
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setGeolocationOverride',
        'params': params,
    }
    json = yield cmd_dict


def get_overridden_sensor_information(
        type_: SensorType
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''


    **EXPERIMENTAL**

    :param type_:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['type'] = type_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.getOverriddenSensorInformation',
        'params': params,
    }
    json = yield cmd_dict
    return float(json['requestedSamplingFrequency'])


def set_sensor_override_enabled(
        enabled: bool,
        type_: SensorType,
        metadata: typing.Optional[SensorMetadata] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides a platform sensor of a given type. If ``enabled`` is true, calls to
    Sensor.start() will use a virtual sensor as backend rather than fetching
    data from a real hardware sensor. Otherwise, existing virtual
    sensor-backend Sensor objects will fire an error event and new calls to
    Sensor.start() will attempt to use a real sensor instead.

    **EXPERIMENTAL**

    :param enabled:
    :param type_:
    :param metadata: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    params['type'] = type_.to_json()
    if metadata is not None:
        params['metadata'] = metadata.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setSensorOverrideEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_sensor_override_readings(
        type_: SensorType,
        reading: SensorReading
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Updates the sensor readings reported by a sensor type previously overridden
    by setSensorOverrideEnabled.

    **EXPERIMENTAL**

    :param type_:
    :param reading:
    '''
    params: T_JSON_DICT = dict()
    params['type'] = type_.to_json()
    params['reading'] = reading.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setSensorOverrideReadings',
        'params': params,
    }
    json = yield cmd_dict


def set_pressure_source_override_enabled(
        enabled: bool,
        source: PressureSource,
        metadata: typing.Optional[PressureMetadata] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides a pressure source of a given type, as used by the Compute
    Pressure API, so that updates to PressureObserver.observe() are provided
    via setPressureStateOverride instead of being retrieved from
    platform-provided telemetry data.

    **EXPERIMENTAL**

    :param enabled:
    :param source:
    :param metadata: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    params['source'] = source.to_json()
    if metadata is not None:
        params['metadata'] = metadata.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setPressureSourceOverrideEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_pressure_state_override(
        source: PressureSource,
        state: PressureState
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Provides a given pressure state that will be processed and eventually be
    delivered to PressureObserver users. ``source`` must have been previously
    overridden by setPressureSourceOverrideEnabled.

    **EXPERIMENTAL**

    :param source:
    :param state:
    '''
    params: T_JSON_DICT = dict()
    params['source'] = source.to_json()
    params['state'] = state.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setPressureStateOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_idle_override(
        is_user_active: bool,
        is_screen_unlocked: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides the Idle state.

    :param is_user_active: Mock isUserActive
    :param is_screen_unlocked: Mock isScreenUnlocked
    '''
    params: T_JSON_DICT = dict()
    params['isUserActive'] = is_user_active
    params['isScreenUnlocked'] = is_screen_unlocked
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setIdleOverride',
        'params': params,
    }
    json = yield cmd_dict


def clear_idle_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears Idle state overrides.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.clearIdleOverride',
    }
    json = yield cmd_dict


def set_navigator_overrides(
        platform: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides value returned by the javascript navigator object.

    **EXPERIMENTAL**

    :param platform: The platform navigator.platform should return.
    '''
    params: T_JSON_DICT = dict()
    params['platform'] = platform
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setNavigatorOverrides',
        'params': params,
    }
    json = yield cmd_dict


def set_page_scale_factor(
        page_scale_factor: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets a specified page scale factor.

    **EXPERIMENTAL**

    :param page_scale_factor: Page scale factor.
    '''
    params: T_JSON_DICT = dict()
    params['pageScaleFactor'] = page_scale_factor
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setPageScaleFactor',
        'params': params,
    }
    json = yield cmd_dict


def set_script_execution_disabled(
        value: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Switches script execution in the page.

    :param value: Whether script execution should be disabled in the page.
    '''
    params: T_JSON_DICT = dict()
    params['value'] = value
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setScriptExecutionDisabled',
        'params': params,
    }
    json = yield cmd_dict


def set_touch_emulation_enabled(
        enabled: bool,
        max_touch_points: typing.Optional[int] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables touch on platforms which do not support them.

    :param enabled: Whether the touch event emulation should be enabled.
    :param max_touch_points: *(Optional)* Maximum touch points supported. Defaults to one.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    if max_touch_points is not None:
        params['maxTouchPoints'] = max_touch_points
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setTouchEmulationEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_virtual_time_policy(
        policy: VirtualTimePolicy,
        budget: typing.Optional[float] = None,
        max_virtual_time_task_starvation_count: typing.Optional[int] = None,
        initial_virtual_time: typing.Optional[network.TimeSinceEpoch] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''
    Turns on virtual time for all frames (replacing real-time with a synthetic time source) and sets
    the current virtual time policy.  Note this supersedes any previous time budget.

    **EXPERIMENTAL**

    :param policy:
    :param budget: *(Optional)* If set, after this many virtual milliseconds have elapsed virtual time will be paused and a virtualTimeBudgetExpired event is sent.
    :param max_virtual_time_task_starvation_count: *(Optional)* If set this specifies the maximum number of tasks that can be run before virtual is forced forwards to prevent deadlock.
    :param initial_virtual_time: *(Optional)* If set, base::Time::Now will be overridden to initially return this value.
    :returns: Absolute timestamp at which virtual time was first enabled (up time in milliseconds).
    '''
    params: T_JSON_DICT = dict()
    params['policy'] = policy.to_json()
    if budget is not None:
        params['budget'] = budget
    if max_virtual_time_task_starvation_count is not None:
        params['maxVirtualTimeTaskStarvationCount'] = max_virtual_time_task_starvation_count
    if initial_virtual_time is not None:
        params['initialVirtualTime'] = initial_virtual_time.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setVirtualTimePolicy',
        'params': params,
    }
    json = yield cmd_dict
    return float(json['virtualTimeTicksBase'])


def set_locale_override(
        locale: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides default host system locale with the specified one.

    **EXPERIMENTAL**

    :param locale: *(Optional)* ICU style C locale (e.g. "en_US"). If not specified or empty, disables the override and restores default host system locale.
    '''
    params: T_JSON_DICT = dict()
    if locale is not None:
        params['locale'] = locale
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setLocaleOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_timezone_override(
        timezone_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides default host system timezone with the specified one.

    :param timezone_id: The timezone identifier. List of supported timezones: https://source.chromium.org/chromium/chromium/deps/icu.git/+/faee8bc70570192d82d2978a71e2a615788597d1:source/data/misc/metaZones.txt If empty, disables the override and restores default host system timezone.
    '''
    params: T_JSON_DICT = dict()
    params['timezoneId'] = timezone_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setTimezoneOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_visible_size(
        width: int,
        height: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resizes the frame/viewport of the page. Note that this does not affect the frame's container
    (e.g. browser window). Can be used to produce screenshots of the specified size. Not supported
    on Android.

    **EXPERIMENTAL**

    :param width: Frame width (DIP).
    :param height: Frame height (DIP).
    '''
    params: T_JSON_DICT = dict()
    params['width'] = width
    params['height'] = height
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setVisibleSize',
        'params': params,
    }
    json = yield cmd_dict


def set_disabled_image_types(
        image_types: typing.List[DisabledImageType]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param image_types: Image types to disable.
    '''
    params: T_JSON_DICT = dict()
    params['imageTypes'] = [i.to_json() for i in image_types]
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setDisabledImageTypes',
        'params': params,
    }
    json = yield cmd_dict


def set_hardware_concurrency_override(
        hardware_concurrency: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param hardware_concurrency: Hardware concurrency to report
    '''
    params: T_JSON_DICT = dict()
    params['hardwareConcurrency'] = hardware_concurrency
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setHardwareConcurrencyOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_user_agent_override(
        user_agent: str,
        accept_language: typing.Optional[str] = None,
        platform: typing.Optional[str] = None,
        user_agent_metadata: typing.Optional[UserAgentMetadata] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Allows overriding user agent with the given string.
    ``userAgentMetadata`` must be set for Client Hint headers to be sent.

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
        'method': 'Emulation.setUserAgentOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_automation_override(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Allows overriding the automation flag.

    **EXPERIMENTAL**

    :param enabled: Whether the override should be enabled.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setAutomationOverride',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Emulation.virtualTimeBudgetExpired')
@dataclass
class VirtualTimeBudgetExpired:
    '''
    **EXPERIMENTAL**

    Notification sent after the virtual time budget for the current VirtualTimePolicy has run out.
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> VirtualTimeBudgetExpired:
        return cls(

        )

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_frame.py ===
import linecache
import os.path
import re

from _pydev_bundle import pydev_log
from _pydevd_bundle import pydevd_dont_trace
from _pydevd_bundle.pydevd_constants import (
    RETURN_VALUES_DICT,
    NO_FTRACE,
    EXCEPTION_TYPE_HANDLED,
    EXCEPTION_TYPE_USER_UNHANDLED,
    PYDEVD_IPYTHON_CONTEXT,
    PYDEVD_USE_SYS_MONITORING,
)
from _pydevd_bundle.pydevd_frame_utils import add_exception_to_frame, just_raised, remove_exception_from_frame, ignore_exception_trace
from _pydevd_bundle.pydevd_utils import get_clsname_for_code
from pydevd_file_utils import get_abs_path_real_path_and_base_from_frame
from _pydevd_bundle.pydevd_comm_constants import constant_to_str, CMD_SET_FUNCTION_BREAK
import sys

try:
    from _pydevd_bundle.pydevd_bytecode_utils import get_smart_step_into_variant_from_frame_offset
except ImportError:

    def get_smart_step_into_variant_from_frame_offset(*args, **kwargs):
        return None

# IFDEF CYTHON
# cython_inline_constant: CMD_STEP_INTO = 107
# cython_inline_constant: CMD_STEP_INTO_MY_CODE = 144
# cython_inline_constant: CMD_STEP_RETURN = 109
# cython_inline_constant: CMD_STEP_RETURN_MY_CODE = 160
# cython_inline_constant: CMD_STEP_OVER = 108
# cython_inline_constant: CMD_STEP_OVER_MY_CODE = 159
# cython_inline_constant: CMD_STEP_CAUGHT_EXCEPTION = 137
# cython_inline_constant: CMD_SET_BREAK = 111
# cython_inline_constant: CMD_SMART_STEP_INTO = 128
# cython_inline_constant: CMD_STEP_INTO_COROUTINE = 206
# cython_inline_constant: STATE_RUN = 1
# cython_inline_constant: STATE_SUSPEND = 2
# ELSE
# Note: those are now inlined on cython.
CMD_STEP_INTO = 107
CMD_STEP_INTO_MY_CODE = 144
CMD_STEP_RETURN = 109
CMD_STEP_RETURN_MY_CODE = 160
CMD_STEP_OVER = 108
CMD_STEP_OVER_MY_CODE = 159
CMD_STEP_CAUGHT_EXCEPTION = 137
CMD_SET_BREAK = 111
CMD_SMART_STEP_INTO = 128
CMD_STEP_INTO_COROUTINE = 206
STATE_RUN = 1
STATE_SUSPEND = 2
# ENDIF

basename = os.path.basename

IGNORE_EXCEPTION_TAG = re.compile("[^#]*#.*@IgnoreException")
DEBUG_START = ("pydevd.py", "run")
DEBUG_START_PY3K = ("_pydev_execfile.py", "execfile")
TRACE_PROPERTY = "pydevd_traceproperty.py"

import dis

try:
    StopAsyncIteration
except NameError:
    StopAsyncIteration = StopIteration


# IFDEF CYTHON
# def is_unhandled_exception(container_obj, py_db, frame, int last_raise_line, set raise_lines):
# ELSE
def is_unhandled_exception(container_obj, py_db, frame, last_raise_line, raise_lines):
    # ENDIF
    if frame.f_lineno in raise_lines:
        return True

    else:
        try_except_infos = container_obj.try_except_infos
        if try_except_infos is None:
            container_obj.try_except_infos = try_except_infos = py_db.collect_try_except_info(frame.f_code)

        if not try_except_infos:
            # Consider the last exception as unhandled because there's no try..except in it.
            return True
        else:
            # Now, consider only the try..except for the raise
            valid_try_except_infos = []
            for try_except_info in try_except_infos:
                if try_except_info.is_line_in_try_block(last_raise_line):
                    valid_try_except_infos.append(try_except_info)

            if not valid_try_except_infos:
                return True

            else:
                # Note: check all, not only the "valid" ones to cover the case
                # in "tests_python.test_tracing_on_top_level.raise_unhandled10"
                # where one try..except is inside the other with only a raise
                # and it's gotten in the except line.
                for try_except_info in try_except_infos:
                    if try_except_info.is_line_in_except_block(frame.f_lineno):
                        if frame.f_lineno == try_except_info.except_line or frame.f_lineno in try_except_info.raise_lines_in_except:
                            # In a raise inside a try..except block or some except which doesn't
                            # match the raised exception.
                            return True
    return False


# IFDEF CYTHON
# cdef class _TryExceptContainerObj:
#     cdef public list try_except_infos;
#     def __init__(self):
#         self.try_except_infos = None
# ELSE
class _TryExceptContainerObj(object):
    """
    A dumb container object just to contain the try..except info when needed. Meant to be
    persistent among multiple PyDBFrames to the same code object.
    """

    try_except_infos = None

# ENDIF


# =======================================================================================================================
# PyDBFrame
# =======================================================================================================================
# IFDEF CYTHON
# cdef class PyDBFrame:
# ELSE
class PyDBFrame:
    """This makes the tracing for a given frame, so, the trace_dispatch
    is used initially when we enter into a new context ('call') and then
    is reused for the entire context.
    """

    # ENDIF

    # IFDEF CYTHON
    # cdef tuple _args
    # cdef int should_skip
    # cdef object exc_info
    # def __init__(self, tuple args):
    #     self._args = args # In the cython version we don't need to pass the frame
    #     self.should_skip = -1  # On cythonized version, put in instance.
    #     self.exc_info = ()
    # ELSE
    should_skip = -1  # Default value in class (put in instance on set).
    exc_info = ()  # Default value in class (put in instance on set).

    if PYDEVD_USE_SYS_MONITORING:

        def __init__(self, *args, **kwargs):
            raise RuntimeError("Not expected to be used in sys.monitoring.")

    else:

        def __init__(self, args):
            # args = py_db, abs_path_canonical_path_and_base, base, info, t, frame
            # yeap, much faster than putting in self and then getting it from self later on
            self._args = args
    # ENDIF

    def set_suspend(self, *args, **kwargs):
        self._args[0].set_suspend(*args, **kwargs)

    def do_wait_suspend(self, *args, **kwargs):
        self._args[0].do_wait_suspend(*args, **kwargs)

    # IFDEF CYTHON
    # def trace_exception(self, frame, str event, arg):
    #     cdef bint should_stop;
    #     cdef tuple exc_info;
    # ELSE
    def trace_exception(self, frame, event, arg):
        # ENDIF
        if event == "exception":
            should_stop, frame, exc_info = should_stop_on_exception(self._args[0], self._args[2], frame, self._args[3], arg, self.exc_info)
            self.exc_info = exc_info

            if should_stop:
                if handle_exception(self._args[0], self._args[3], frame, arg, EXCEPTION_TYPE_HANDLED):
                    return self.trace_dispatch

        elif event == "return":
            exc_info = self.exc_info
            if exc_info and arg is None:
                frame_skips_cache, frame_cache_key = self._args[4], self._args[5]
                custom_key = (frame_cache_key, "try_exc_info")
                container_obj = frame_skips_cache.get(custom_key)
                if container_obj is None:
                    container_obj = frame_skips_cache[custom_key] = _TryExceptContainerObj()
                if is_unhandled_exception(container_obj, self._args[0], frame, exc_info[1], exc_info[2]) and self.handle_user_exception(
                    frame
                ):
                    return self.trace_dispatch

        return self.trace_exception

    def handle_user_exception(self, frame):
        exc_info = self.exc_info
        if exc_info:
            return handle_exception(self._args[0], self._args[3], frame, exc_info[0], EXCEPTION_TYPE_USER_UNHANDLED)
        return False

    # IFDEF CYTHON
    # cdef get_func_name(self, frame):
    #     cdef str func_name
    # ELSE
    def get_func_name(self, frame):
        # ENDIF
        code_obj = frame.f_code
        func_name = code_obj.co_name
        try:
            cls_name = get_clsname_for_code(code_obj, frame)
            if cls_name is not None:
                return "%s.%s" % (cls_name, func_name)
            else:
                return func_name
        except:
            pydev_log.exception()
            return func_name

    # IFDEF CYTHON
    # cdef _show_return_values(self, frame, arg):
    # ELSE
    def _show_return_values(self, frame, arg):
        # ENDIF
        try:
            try:
                f_locals_back = getattr(frame.f_back, "f_locals", None)
                if f_locals_back is not None:
                    return_values_dict = f_locals_back.get(RETURN_VALUES_DICT, None)
                    if return_values_dict is None:
                        return_values_dict = {}
                        f_locals_back[RETURN_VALUES_DICT] = return_values_dict
                    name = self.get_func_name(frame)
                    return_values_dict[name] = arg
            except:
                pydev_log.exception()
        finally:
            f_locals_back = None

    # IFDEF CYTHON
    # cdef _remove_return_values(self, py_db, frame):
    # ELSE
    def _remove_return_values(self, py_db, frame):
        # ENDIF
        try:
            try:
                # Showing return values was turned off, we should remove them from locals dict.
                # The values can be in the current frame or in the back one
                frame.f_locals.pop(RETURN_VALUES_DICT, None)

                f_locals_back = getattr(frame.f_back, "f_locals", None)
                if f_locals_back is not None:
                    f_locals_back.pop(RETURN_VALUES_DICT, None)
            except:
                pydev_log.exception()
        finally:
            f_locals_back = None

    # IFDEF CYTHON
    # cdef _get_unfiltered_back_frame(self, py_db, frame):
    # ELSE
    def _get_unfiltered_back_frame(self, py_db, frame):
        # ENDIF
        f = frame.f_back
        while f is not None:
            if not py_db.is_files_filter_enabled:
                return f

            else:
                if py_db.apply_files_filter(f, f.f_code.co_filename, False):
                    f = f.f_back

                else:
                    return f

        return f

    # IFDEF CYTHON
    # cdef _is_same_frame(self, target_frame, current_frame):
    #     cdef PyDBAdditionalThreadInfo info;
    # ELSE
    def _is_same_frame(self, target_frame, current_frame):
        # ENDIF
        if target_frame is current_frame:
            return True

        info = self._args[2]
        if info.pydev_use_scoped_step_frame:
            # If using scoped step we don't check the target, we just need to check
            # if the current matches the same heuristic where the target was defined.
            if target_frame is not None and current_frame is not None:
                if target_frame.f_code.co_filename == current_frame.f_code.co_filename:
                    # The co_name may be different (it may include the line number), but
                    # the filename must still be the same.
                    f = current_frame.f_back
                    if f is not None and f.f_code.co_name == PYDEVD_IPYTHON_CONTEXT[1]:
                        f = f.f_back
                        if f is not None and f.f_code.co_name == PYDEVD_IPYTHON_CONTEXT[2]:
                            return True

        return False

    # IFDEF CYTHON
    # cpdef trace_dispatch(self, frame, str event, arg):
    #     cdef tuple abs_path_canonical_path_and_base;
    #     cdef bint is_exception_event;
    #     cdef bint has_exception_breakpoints;
    #     cdef bint can_skip;
    #     cdef bint stop;
    #     cdef bint stop_on_plugin_breakpoint;
    #     cdef PyDBAdditionalThreadInfo info;
    #     cdef int step_cmd;
    #     cdef int line;
    #     cdef bint is_line;
    #     cdef bint is_call;
    #     cdef bint is_return;
    #     cdef bint should_stop;
    #     cdef dict breakpoints_for_file;
    #     cdef dict stop_info;
    #     cdef str curr_func_name;
    #     cdef dict frame_skips_cache;
    #     cdef object frame_cache_key;
    #     cdef tuple line_cache_key;
    #     cdef int breakpoints_in_line_cache;
    #     cdef int breakpoints_in_frame_cache;
    #     cdef bint has_breakpoint_in_frame;
    #     cdef bint is_coroutine_or_generator;
    #     cdef int bp_line;
    #     cdef object bp;
    #     cdef int pydev_smart_parent_offset
    #     cdef int pydev_smart_child_offset
    #     cdef tuple pydev_smart_step_into_variants
    # ELSE
    def trace_dispatch(self, frame, event, arg):
        # ENDIF
        # Note: this is a big function because most of the logic related to hitting a breakpoint and
        # stepping is contained in it. Ideally this could be split among multiple functions, but the
        # problem in this case is that in pure-python function calls are expensive and even more so
        # when tracing is on (because each function call will get an additional tracing call). We
        # try to address this by using the info.is_tracing for the fastest possible return, but the
        # cost is still high (maybe we could use code-generation in the future and make the code
        # generation be better split among what each part does).

        try:
            # DEBUG = '_debugger_case_yield_from.py' in frame.f_code.co_filename
            py_db, abs_path_canonical_path_and_base, info, thread, frame_skips_cache, frame_cache_key = self._args
            # if DEBUG: print('frame trace_dispatch %s %s %s %s %s %s, stop: %s' % (frame.f_lineno, frame.f_code.co_name, frame.f_code.co_filename, event, constant_to_str(info.pydev_step_cmd), arg, info.pydev_step_stop))
            info.is_tracing += 1

            # TODO: This shouldn't be needed. The fact that frame.f_lineno
            # is None seems like a bug in Python 3.11.
            # Reported in: https://github.com/python/cpython/issues/94485
            line = frame.f_lineno or 0  # Workaround or case where frame.f_lineno is None
            line_cache_key = (frame_cache_key, line)

            if py_db.pydb_disposed:
                return None if event == "call" else NO_FTRACE

            plugin_manager = py_db.plugin
            has_exception_breakpoints = (
                py_db.break_on_caught_exceptions or py_db.break_on_user_uncaught_exceptions or py_db.has_plugin_exception_breaks
            )

            stop_frame = info.pydev_step_stop
            step_cmd = info.pydev_step_cmd
            function_breakpoint_on_call_event = None

            if frame.f_code.co_flags & 0xA0:  # 0xa0 ==  CO_GENERATOR = 0x20 | CO_COROUTINE = 0x80
                # Dealing with coroutines and generators:
                # When in a coroutine we change the perceived event to the debugger because
                # a call, StopIteration exception and return are usually just pausing/unpausing it.
                if event == "line":
                    is_line = True
                    is_call = False
                    is_return = False
                    is_exception_event = False

                elif event == "return":
                    is_line = False
                    is_call = False
                    is_return = True
                    is_exception_event = False

                    returns_cache_key = (frame_cache_key, "returns")
                    return_lines = frame_skips_cache.get(returns_cache_key)
                    if return_lines is None:
                        # Note: we're collecting the return lines by inspecting the bytecode as
                        # there are multiple returns and multiple stop iterations when awaiting and
                        # it doesn't give any clear indication when a coroutine or generator is
                        # finishing or just pausing.
                        return_lines = set()
                        for x in py_db.collect_return_info(frame.f_code):
                            # Note: cython does not support closures in cpdefs (so we can't use
                            # a list comprehension).
                            return_lines.add(x.return_line)

                        frame_skips_cache[returns_cache_key] = return_lines

                    if line not in return_lines:
                        # Not really a return (coroutine/generator paused).
                        return self.trace_dispatch
                    else:
                        if self.exc_info:
                            self.handle_user_exception(frame)
                            return self.trace_dispatch

                        # Tricky handling: usually when we're on a frame which is about to exit
                        # we set the step mode to step into, but in this case we'd end up in the
                        # asyncio internal machinery, which is not what we want, so, we just
                        # ask the stop frame to be a level up.
                        #
                        # Note that there's an issue here which we may want to fix in the future: if
                        # the back frame is a frame which is filtered, we won't stop properly.
                        # Solving this may not be trivial as we'd need to put a scope in the step
                        # in, but we may have to do it anyways to have a step in which doesn't end
                        # up in asyncio).
                        #
                        # Note2: we don't revert to a step in if we're doing scoped stepping
                        # (because on scoped stepping we're always receiving a call/line/return
                        # event for each line in ipython, so, we can't revert to step in on return
                        # as the return shouldn't mean that we've actually completed executing a
                        # frame in this case).
                        if stop_frame is frame and not info.pydev_use_scoped_step_frame:
                            if step_cmd in (CMD_STEP_OVER, CMD_STEP_OVER_MY_CODE, CMD_STEP_INTO, CMD_STEP_INTO_MY_CODE):
                                f = self._get_unfiltered_back_frame(py_db, frame)
                                if f is not None:
                                    info.pydev_step_cmd = CMD_STEP_INTO_COROUTINE
                                    info.pydev_step_stop = f
                                else:
                                    if step_cmd == CMD_STEP_OVER:
                                        info.pydev_step_cmd = CMD_STEP_INTO
                                        info.pydev_step_stop = None

                                    elif step_cmd == CMD_STEP_OVER_MY_CODE:
                                        info.pydev_step_cmd = CMD_STEP_INTO_MY_CODE
                                        info.pydev_step_stop = None

                            elif step_cmd == CMD_STEP_INTO_COROUTINE:
                                # We're exiting this one, so, mark the new coroutine context.
                                f = self._get_unfiltered_back_frame(py_db, frame)
                                if f is not None:
                                    info.pydev_step_stop = f
                                else:
                                    info.pydev_step_cmd = CMD_STEP_INTO
                                    info.pydev_step_stop = None

                elif event == "exception":
                    breakpoints_for_file = None
                    if has_exception_breakpoints:
                        should_stop, frame, exc_info = should_stop_on_exception(
                            self._args[0], self._args[2], frame, self._args[3], arg, self.exc_info
                        )
                        self.exc_info = exc_info
                        if should_stop:
                            if handle_exception(self._args[0], self._args[3], frame, arg, EXCEPTION_TYPE_HANDLED):
                                return self.trace_dispatch

                    return self.trace_dispatch
                else:
                    # event == 'call' or event == 'c_XXX'
                    return self.trace_dispatch

            else:  # Not coroutine nor generator
                if event == "line":
                    is_line = True
                    is_call = False
                    is_return = False
                    is_exception_event = False

                elif event == "return":
                    is_line = False
                    is_return = True
                    is_call = False
                    is_exception_event = False

                    # If we are in single step mode and something causes us to exit the current frame, we need to make sure we break
                    # eventually.  Force the step mode to step into and the step stop frame to None.
                    # I.e.: F6 in the end of a function should stop in the next possible position (instead of forcing the user
                    # to make a step in or step over at that location).
                    # Note: this is especially troublesome when we're skipping code with the
                    # @DontTrace comment.
                    if (
                        stop_frame is frame
                        and not info.pydev_use_scoped_step_frame
                        and is_return
                        and step_cmd
                        in (CMD_STEP_OVER, CMD_STEP_RETURN, CMD_STEP_OVER_MY_CODE, CMD_STEP_RETURN_MY_CODE, CMD_SMART_STEP_INTO)
                    ):
                        if step_cmd in (CMD_STEP_OVER, CMD_STEP_RETURN, CMD_SMART_STEP_INTO):
                            info.pydev_step_cmd = CMD_STEP_INTO
                        else:
                            info.pydev_step_cmd = CMD_STEP_INTO_MY_CODE
                        info.pydev_step_stop = None

                    if self.exc_info:
                        if self.handle_user_exception(frame):
                            return self.trace_dispatch

                elif event == "call":
                    is_line = False
                    is_call = True
                    is_return = False
                    is_exception_event = False
                    if frame.f_code.co_firstlineno == frame.f_lineno:  # Check line to deal with async/await.
                        function_breakpoint_on_call_event = py_db.function_breakpoint_name_to_breakpoint.get(frame.f_code.co_name)

                elif event == "exception":
                    is_exception_event = True
                    breakpoints_for_file = None
                    if has_exception_breakpoints:
                        should_stop, frame, exc_info = should_stop_on_exception(
                            self._args[0], self._args[2], frame, self._args[3], arg, self.exc_info
                        )
                        self.exc_info = exc_info
                        if should_stop:
                            if handle_exception(self._args[0], self._args[3], frame, arg, EXCEPTION_TYPE_HANDLED):
                                return self.trace_dispatch
                    is_line = False
                    is_return = False
                    is_call = False

                else:
                    # Unexpected: just keep the same trace func (i.e.: event == 'c_XXX').
                    return self.trace_dispatch

            if not is_exception_event:
                breakpoints_for_file = py_db.breakpoints.get(abs_path_canonical_path_and_base[1])

                can_skip = False

                if info.pydev_state == 1:  # STATE_RUN = 1
                    # we can skip if:
                    # - we have no stop marked
                    # - we should make a step return/step over and we're not in the current frame
                    # - we're stepping into a coroutine context and we're not in that context
                    if step_cmd == -1:
                        can_skip = True

                    elif step_cmd in (
                        CMD_STEP_OVER,
                        CMD_STEP_RETURN,
                        CMD_STEP_OVER_MY_CODE,
                        CMD_STEP_RETURN_MY_CODE,
                    ) and not self._is_same_frame(stop_frame, frame):
                        can_skip = True

                    elif step_cmd == CMD_SMART_STEP_INTO and (
                        stop_frame is not None
                        and stop_frame is not frame
                        and stop_frame is not frame.f_back
                        and (frame.f_back is None or stop_frame is not frame.f_back.f_back)
                    ):
                        can_skip = True

                    elif step_cmd == CMD_STEP_INTO_MY_CODE:
                        if py_db.apply_files_filter(frame, frame.f_code.co_filename, True) and (
                            frame.f_back is None or py_db.apply_files_filter(frame.f_back, frame.f_back.f_code.co_filename, True)
                        ):
                            can_skip = True

                    elif step_cmd == CMD_STEP_INTO_COROUTINE:
                        f = frame
                        while f is not None:
                            if self._is_same_frame(stop_frame, f):
                                break
                            f = f.f_back
                        else:
                            can_skip = True

                    if can_skip:
                        if plugin_manager is not None and (py_db.has_plugin_line_breaks or py_db.has_plugin_exception_breaks):
                            can_skip = plugin_manager.can_skip(py_db, frame)

                        if (
                            can_skip
                            and py_db.show_return_values
                            and info.pydev_step_cmd in (CMD_STEP_OVER, CMD_STEP_OVER_MY_CODE)
                            and self._is_same_frame(stop_frame, frame.f_back)
                        ):
                            # trace function for showing return values after step over
                            can_skip = False

                # Let's check to see if we are in a function that has a breakpoint. If we don't have a breakpoint,
                # we will return nothing for the next trace
                # also, after we hit a breakpoint and go to some other debugging state, we have to force the set trace anyway,
                # so, that's why the additional checks are there.

                if function_breakpoint_on_call_event:
                    pass  # Do nothing here (just keep on going as we can't skip it).

                elif not breakpoints_for_file:
                    if can_skip:
                        if has_exception_breakpoints:
                            return self.trace_exception
                        else:
                            return None if is_call else NO_FTRACE

                else:
                    # When cached, 0 means we don't have a breakpoint and 1 means we have.
                    if can_skip:
                        breakpoints_in_line_cache = frame_skips_cache.get(line_cache_key, -1)
                        if breakpoints_in_line_cache == 0:
                            return self.trace_dispatch

                    breakpoints_in_frame_cache = frame_skips_cache.get(frame_cache_key, -1)
                    if breakpoints_in_frame_cache != -1:
                        # Gotten from cache.
                        has_breakpoint_in_frame = breakpoints_in_frame_cache == 1

                    else:
                        has_breakpoint_in_frame = False

                        try:
                            func_lines = set()
                            for offset_and_lineno in dis.findlinestarts(frame.f_code):
                                if offset_and_lineno[1] is not None:
                                    func_lines.add(offset_and_lineno[1])
                        except:
                            # This is a fallback for implementations where we can't get the function
                            # lines -- i.e.: jython (in this case clients need to provide the function
                            # name to decide on the skip or we won't be able to skip the function
                            # completely).

                            # Checks the breakpoint to see if there is a context match in some function.
                            curr_func_name = frame.f_code.co_name

                            # global context is set with an empty name
                            if curr_func_name in ("?", "<module>", "<lambda>"):
                                curr_func_name = ""

                            for bp in breakpoints_for_file.values():
                                # will match either global or some function
                                if bp.func_name in ("None", curr_func_name):
                                    has_breakpoint_in_frame = True
                                    break
                        else:
                            for bp_line in breakpoints_for_file:  # iterate on keys
                                if bp_line in func_lines:
                                    has_breakpoint_in_frame = True
                                    break

                        # Cache the value (1 or 0 or -1 for default because of cython).
                        if has_breakpoint_in_frame:
                            frame_skips_cache[frame_cache_key] = 1
                        else:
                            frame_skips_cache[frame_cache_key] = 0

                    if can_skip and not has_breakpoint_in_frame:
                        if has_exception_breakpoints:
                            return self.trace_exception
                        else:
                            return None if is_call else NO_FTRACE

            # We may have hit a breakpoint or we are already in step mode. Either way, let's check what we should do in this frame
            # if DEBUG: print('NOT skipped: %s %s %s %s' % (frame.f_lineno, frame.f_code.co_name, event, frame.__class__.__name__))

            try:
                stop_on_plugin_breakpoint = False
                # return is not taken into account for breakpoint hit because we'd have a double-hit in this case
                # (one for the line and the other for the return).

                stop_info = {}
                breakpoint = None
                stop = False
                stop_reason = CMD_SET_BREAK
                bp_type = None

                if function_breakpoint_on_call_event:
                    breakpoint = function_breakpoint_on_call_event
                    stop = True
                    new_frame = frame
                    stop_reason = CMD_SET_FUNCTION_BREAK

                elif is_line and info.pydev_state != STATE_SUSPEND and breakpoints_for_file is not None and line in breakpoints_for_file:
                    breakpoint = breakpoints_for_file[line]
                    new_frame = frame
                    stop = True

                elif plugin_manager is not None and py_db.has_plugin_line_breaks:
                    result = plugin_manager.get_breakpoint(py_db, frame, event, self._args[2])
                    if result:
                        stop_on_plugin_breakpoint = True
                        breakpoint, new_frame, bp_type = result

                if breakpoint:
                    # ok, hit breakpoint, now, we have to discover if it is a conditional breakpoint
                    # lets do the conditional stuff here
                    if breakpoint.expression is not None:
                        py_db.handle_breakpoint_expression(breakpoint, info, new_frame)

                    if stop or stop_on_plugin_breakpoint:
                        eval_result = False
                        if breakpoint.has_condition:
                            eval_result = py_db.handle_breakpoint_condition(info, breakpoint, new_frame)
                            if not eval_result:
                                stop = False
                                stop_on_plugin_breakpoint = False

                    if is_call and (
                        frame.f_code.co_name in ("<lambda>", "<module>") or (line == 1 and frame.f_code.co_name.startswith("<cell"))
                    ):
                        # If we find a call for a module, it means that the module is being imported/executed for the
                        # first time. In this case we have to ignore this hit as it may later duplicated by a
                        # line event at the same place (so, if there's a module with a print() in the first line
                        # the user will hit that line twice, which is not what we want).
                        #
                        # For lambda, as it only has a single statement, it's not interesting to trace
                        # its call and later its line event as they're usually in the same line.
                        #
                        # For ipython, <cell xxx> may be executed having each line compiled as a new
                        # module, so it's the same case as <module>.

                        return self.trace_dispatch

                    # Handle logpoint (on a logpoint we should never stop).
                    if (stop or stop_on_plugin_breakpoint) and breakpoint.is_logpoint:
                        stop = False
                        stop_on_plugin_breakpoint = False

                        if info.pydev_message is not None and len(info.pydev_message) > 0:
                            cmd = py_db.cmd_factory.make_io_message(info.pydev_message + os.linesep, "1")
                            py_db.writer.add_command(cmd)

                if py_db.show_return_values:
                    if is_return and (
                        (
                            info.pydev_step_cmd in (CMD_STEP_OVER, CMD_STEP_OVER_MY_CODE, CMD_SMART_STEP_INTO)
                            and (self._is_same_frame(stop_frame, frame.f_back))
                        )
                        or (info.pydev_step_cmd in (CMD_STEP_RETURN, CMD_STEP_RETURN_MY_CODE) and (self._is_same_frame(stop_frame, frame)))
                        or (info.pydev_step_cmd in (CMD_STEP_INTO, CMD_STEP_INTO_COROUTINE))
                        or (
                            info.pydev_step_cmd == CMD_STEP_INTO_MY_CODE
                            and frame.f_back is not None
                            and not py_db.apply_files_filter(frame.f_back, frame.f_back.f_code.co_filename, True)
                        )
                    ):
                        self._show_return_values(frame, arg)

                elif py_db.remove_return_values_flag:
                    try:
                        self._remove_return_values(py_db, frame)
                    finally:
                        py_db.remove_return_values_flag = False

                if stop:
                    self.set_suspend(
                        thread,
                        stop_reason,
                        suspend_other_threads=breakpoint and breakpoint.suspend_policy == "ALL",
                    )

                elif stop_on_plugin_breakpoint and plugin_manager is not None:
                    result = plugin_manager.suspend(py_db, thread, frame, bp_type)
                    if result:
                        frame = result

                # if thread has a suspend flag, we suspend with a busy wait
                if info.pydev_state == STATE_SUSPEND:
                    self.do_wait_suspend(thread, frame, event, arg)
                    return self.trace_dispatch
                else:
                    if not breakpoint and is_line:
                        # No stop from anyone and no breakpoint found in line (cache that).
                        frame_skips_cache[line_cache_key] = 0

            except:
                # Unfortunately Python itself stops the tracing when it originates from
                # the tracing function, so, we can't do much about it (just let the user know).
                exc = sys.exc_info()[0]
                cmd = py_db.cmd_factory.make_console_message(
                    "%s raised from within the callback set in sys.settrace.\nDebugging will be disabled for this thread (%s).\n"
                    % (
                        exc,
                        thread,
                    )
                )
                py_db.writer.add_command(cmd)
                if not issubclass(exc, (KeyboardInterrupt, SystemExit)):
                    pydev_log.exception()

                raise

            # step handling. We stop when we hit the right frame
            try:
                should_skip = 0
                if pydevd_dont_trace.should_trace_hook is not None:
                    if self.should_skip == -1:
                        # I.e.: cache the result on self.should_skip (no need to evaluate the same frame multiple times).
                        # Note that on a code reload, we won't re-evaluate this because in practice, the frame.f_code
                        # Which will be handled by this frame is read-only, so, we can cache it safely.
                        if not pydevd_dont_trace.should_trace_hook(frame.f_code, abs_path_canonical_path_and_base[0]):
                            # -1, 0, 1 to be Cython-friendly
                            should_skip = self.should_skip = 1
                        else:
                            should_skip = self.should_skip = 0
                    else:
                        should_skip = self.should_skip

                plugin_stop = False
                if should_skip:
                    stop = False

                elif step_cmd in (CMD_STEP_INTO, CMD_STEP_INTO_MY_CODE, CMD_STEP_INTO_COROUTINE):
                    force_check_project_scope = step_cmd == CMD_STEP_INTO_MY_CODE
                    if is_line:
                        if not info.pydev_use_scoped_step_frame:
                            if force_check_project_scope or py_db.is_files_filter_enabled:
                                stop = not py_db.apply_files_filter(frame, frame.f_code.co_filename, force_check_project_scope)
                            else:
                                stop = True
                        else:
                            if force_check_project_scope or py_db.is_files_filter_enabled:
                                # Make sure we check the filtering inside ipython calls too...
                                if not not py_db.apply_files_filter(frame, frame.f_code.co_filename, force_check_project_scope):
                                    return None if is_call else NO_FTRACE

                            # We can only stop inside the ipython call.
                            filename = frame.f_code.co_filename
                            if filename.endswith(".pyc"):
                                filename = filename[:-1]

                            if not filename.endswith(PYDEVD_IPYTHON_CONTEXT[0]):
                                f = frame.f_back
                                while f is not None:
                                    if f.f_code.co_name == PYDEVD_IPYTHON_CONTEXT[1]:
                                        f2 = f.f_back
                                        if f2 is not None and f2.f_code.co_name == PYDEVD_IPYTHON_CONTEXT[2]:
                                            pydev_log.debug("Stop inside ipython call")
                                            stop = True
                                            break
                                    f = f.f_back

                                del f

                            if not stop:
                                # In scoped mode if step in didn't work in this context it won't work
                                # afterwards anyways.
                                return None if is_call else NO_FTRACE

                    elif is_return and frame.f_back is not None and not info.pydev_use_scoped_step_frame:
                        if py_db.get_file_type(frame.f_back) == py_db.PYDEV_FILE:
                            stop = False
                        else:
                            if force_check_project_scope or py_db.is_files_filter_enabled:
                                stop = not py_db.apply_files_filter(
                                    frame.f_back, frame.f_back.f_code.co_filename, force_check_project_scope
                                )
                                if stop:
                                    # Prevent stopping in a return to the same location we were initially
                                    # (i.e.: double-stop at the same place due to some filtering).
                                    if info.step_in_initial_location == (frame.f_back, frame.f_back.f_lineno):
                                        stop = False
                            else:
                                stop = True
                    else:
                        stop = False

                    if stop:
                        if step_cmd == CMD_STEP_INTO_COROUTINE:
                            # i.e.: Check if we're stepping into the proper context.
                            f = frame
                            while f is not None:
                                if self._is_same_frame(stop_frame, f):
                                    break
                                f = f.f_back
                            else:
                                stop = False

                    if plugin_manager is not None:
                        result = plugin_manager.cmd_step_into(py_db, frame, event, self._args[2], self._args[3], stop_info, stop)
                        if result:
                            stop, plugin_stop = result

                elif step_cmd in (CMD_STEP_OVER, CMD_STEP_OVER_MY_CODE):
                    # Note: when dealing with a step over my code it's the same as a step over (the
                    # difference is that when we return from a frame in one we go to regular step
                    # into and in the other we go to a step into my code).
                    stop = self._is_same_frame(stop_frame, frame) and is_line
                    # Note: don't stop on a return for step over, only for line events
                    # i.e.: don't stop in: (stop_frame is frame.f_back and is_return) as we'd stop twice in that line.

                    if plugin_manager is not None:
                        result = plugin_manager.cmd_step_over(py_db, frame, event, self._args[2], self._args[3], stop_info, stop)
                        if result:
                            stop, plugin_stop = result

                elif step_cmd == CMD_SMART_STEP_INTO:
                    stop = False
                    back = frame.f_back
                    if self._is_same_frame(stop_frame, frame) and is_return:
                        # We're exiting the smart step into initial frame (so, we probably didn't find our target).
                        stop = True

                    elif self._is_same_frame(stop_frame, back) and is_line:
                        if info.pydev_smart_child_offset != -1:
                            # i.e.: in this case, we're not interested in the pause in the parent, rather
                            # we're interested in the pause in the child (when the parent is at the proper place).
                            stop = False

                        else:
                            pydev_smart_parent_offset = info.pydev_smart_parent_offset

                            pydev_smart_step_into_variants = info.pydev_smart_step_into_variants
                            if pydev_smart_parent_offset >= 0 and pydev_smart_step_into_variants:
                                # Preferred mode (when the smart step into variants are available
                                # and the offset is set).
                                stop = get_smart_step_into_variant_from_frame_offset(
                                    back.f_lasti, pydev_smart_step_into_variants
                                ) is get_smart_step_into_variant_from_frame_offset(
                                    pydev_smart_parent_offset, pydev_smart_step_into_variants
                                )

                            else:
                                # Only the name/line is available, so, check that.
                                curr_func_name = frame.f_code.co_name

                                # global context is set with an empty name
                                if curr_func_name in ("?", "<module>") or curr_func_name is None:
                                    curr_func_name = ""
                                if curr_func_name == info.pydev_func_name and stop_frame.f_lineno == info.pydev_next_line:
                                    stop = True

                        if not stop:
                            # In smart step into, if we didn't hit it in this frame once, that'll
                            # not be the case next time either, so, disable tracing for this frame.
                            return None if is_call else NO_FTRACE

                    elif back is not None and self._is_same_frame(stop_frame, back.f_back) and is_line:
                        # Ok, we have to track 2 stops at this point, the parent and the child offset.
                        # This happens when handling a step into which targets a function inside a list comprehension
                        # or generator (in which case an intermediary frame is created due to an internal function call).
                        pydev_smart_parent_offset = info.pydev_smart_parent_offset
                        pydev_smart_child_offset = info.pydev_smart_child_offset
                        # print('matched back frame', pydev_smart_parent_offset, pydev_smart_child_offset)
                        # print('parent f_lasti', back.f_back.f_lasti)
                        # print('child f_lasti', back.f_lasti)
                        stop = False
                        if pydev_smart_child_offset >= 0 and pydev_smart_child_offset >= 0:
                            pydev_smart_step_into_variants = info.pydev_smart_step_into_variants

                            if pydev_smart_parent_offset >= 0 and pydev_smart_step_into_variants:
                                # Note that we don't really check the parent offset, only the offset of
                                # the child (because this is a generator, the parent may have moved forward
                                # already -- and that's ok, so, we just check that the parent frame
                                # matches in this case).
                                smart_step_into_variant = get_smart_step_into_variant_from_frame_offset(
                                    pydev_smart_parent_offset, pydev_smart_step_into_variants
                                )
                                # print('matched parent offset', pydev_smart_parent_offset)
                                # Ok, now, check the child variant
                                children_variants = smart_step_into_variant.children_variants
                                stop = children_variants and (
                                    get_smart_step_into_variant_from_frame_offset(back.f_lasti, children_variants)
                                    is get_smart_step_into_variant_from_frame_offset(pydev_smart_child_offset, children_variants)
                                )
                                # print('stop at child', stop)

                        if not stop:
                            # In smart step into, if we didn't hit it in this frame once, that'll
                            # not be the case next time either, so, disable tracing for this frame.
                            return None if is_call else NO_FTRACE

                elif step_cmd in (CMD_STEP_RETURN, CMD_STEP_RETURN_MY_CODE):
                    stop = is_return and self._is_same_frame(stop_frame, frame)

                else:
                    stop = False

                if stop and step_cmd != -1 and is_return and hasattr(frame, "f_back"):
                    f_code = getattr(frame.f_back, "f_code", None)
                    if f_code is not None:
                        if py_db.get_file_type(frame.f_back) == py_db.PYDEV_FILE:
                            stop = False

                if plugin_stop:
                    plugin_manager.stop(py_db, frame, event, self._args[3], stop_info, arg, step_cmd)
                elif stop:
                    if is_line:
                        self.set_suspend(thread, step_cmd, original_step_cmd=info.pydev_original_step_cmd)
                        self.do_wait_suspend(thread, frame, event, arg)
                    elif is_return:  # return event
                        back = frame.f_back
                        if back is not None:
                            # When we get to the pydevd run function, the debugging has actually finished for the main thread
                            # (note that it can still go on for other threads, but for this one, we just make it finish)
                            # So, just setting it to None should be OK
                            back_absolute_filename, _, base = get_abs_path_real_path_and_base_from_frame(back)
                            if (base, back.f_code.co_name) in (DEBUG_START, DEBUG_START_PY3K):
                                back = None

                            elif base == TRACE_PROPERTY:
                                # We dont want to trace the return event of pydevd_traceproperty (custom property for debugging)
                                # if we're in a return, we want it to appear to the user in the previous frame!
                                return None if is_call else NO_FTRACE

                            elif pydevd_dont_trace.should_trace_hook is not None:
                                if not pydevd_dont_trace.should_trace_hook(back.f_code, back_absolute_filename):
                                    # In this case, we'll have to skip the previous one because it shouldn't be traced.
                                    # Also, we have to reset the tracing, because if the parent's parent (or some
                                    # other parent) has to be traced and it's not currently, we wouldn't stop where
                                    # we should anymore (so, a step in/over/return may not stop anywhere if no parent is traced).
                                    # Related test: _debugger_case17a.py
                                    py_db.set_trace_for_frame_and_parents(thread.ident, back)
                                    return None if is_call else NO_FTRACE

                        if back is not None:
                            # if we're in a return, we want it to appear to the user in the previous frame!
                            self.set_suspend(thread, step_cmd, original_step_cmd=info.pydev_original_step_cmd)
                            self.do_wait_suspend(thread, back, event, arg)
                        else:
                            # in jython we may not have a back frame
                            info.pydev_step_stop = None
                            info.pydev_original_step_cmd = -1
                            info.pydev_step_cmd = -1
                            info.pydev_state = STATE_RUN
                            info.update_stepping_info()

                # if we are quitting, let's stop the tracing
                if py_db.quitting:
                    return None if is_call else NO_FTRACE

                return self.trace_dispatch
            except:
                # Unfortunately Python itself stops the tracing when it originates from
                # the tracing function, so, we can't do much about it (just let the user know).
                exc = sys.exc_info()[0]
                cmd = py_db.cmd_factory.make_console_message(
                    "%s raised from within the callback set in sys.settrace.\nDebugging will be disabled for this thread (%s).\n"
                    % (
                        exc,
                        thread,
                    )
                )
                py_db.writer.add_command(cmd)
                if not issubclass(exc, (KeyboardInterrupt, SystemExit)):
                    pydev_log.exception()
                raise

        finally:
            info.is_tracing -= 1

        # end trace_dispatch


# IFDEF CYTHON
# def should_stop_on_exception(py_db, PyDBAdditionalThreadInfo info, frame, thread, arg, prev_user_uncaught_exc_info, is_unwind=False):
#     cdef bint should_stop;
#     cdef bint was_just_raised;
#     cdef list check_excs;
# ELSE
def should_stop_on_exception(py_db, info, frame, thread, arg, prev_user_uncaught_exc_info, is_unwind=False):
    # ENDIF

    should_stop = False
    maybe_user_uncaught_exc_info = prev_user_uncaught_exc_info

    # STATE_SUSPEND = 2
    if info.pydev_state != 2:  # and breakpoint is not None:
        exception, value, trace = arg

        if trace is not None and hasattr(trace, "tb_next"):
            # on jython trace is None on the first event and it may not have a tb_next.

            should_stop = False
            exception_breakpoint = None
            try:
                if py_db.plugin is not None:
                    result = py_db.plugin.exception_break(py_db, frame, thread, arg, is_unwind)
                    if result:
                        should_stop, frame = result
            except:
                pydev_log.exception()

            if not should_stop:
                # Apply checks that don't need the exception breakpoint (where we shouldn't ever stop).
                if exception == SystemExit and py_db.ignore_system_exit_code(value):
                    pass

                elif exception in (GeneratorExit, StopIteration, StopAsyncIteration):
                    # These exceptions are control-flow related (they work as a generator
                    # pause), so, we shouldn't stop on them.
                    pass

                elif ignore_exception_trace(trace):
                    pass

                else:
                    was_just_raised = trace.tb_next is None

                    # It was not handled by any plugin, lets check exception breakpoints.
                    check_excs = []

                    # Note: check user unhandled before regular exceptions.
                    exc_break_user = py_db.get_exception_breakpoint(exception, py_db.break_on_user_uncaught_exceptions)
                    if exc_break_user is not None:
                        check_excs.append((exc_break_user, True))

                    exc_break_caught = py_db.get_exception_breakpoint(exception, py_db.break_on_caught_exceptions)
                    if exc_break_caught is not None:
                        check_excs.append((exc_break_caught, False))

                    for exc_break, is_user_uncaught in check_excs:
                        # Initially mark that it should stop and then go into exclusions.
                        should_stop = True

                        if py_db.exclude_exception_by_filter(exc_break, trace):
                            pydev_log.debug(
                                "Ignore exception %s in library %s -- (%s)" % (exception, frame.f_code.co_filename, frame.f_code.co_name)
                            )
                            should_stop = False

                        elif exc_break.condition is not None and not py_db.handle_breakpoint_condition(info, exc_break, frame):
                            should_stop = False

                        elif is_user_uncaught:
                            # Note: we don't stop here, we just collect the exc_info to use later on...
                            should_stop = False
                            if not py_db.apply_files_filter(frame, frame.f_code.co_filename, True) and (
                                frame.f_back is None or py_db.apply_files_filter(frame.f_back, frame.f_back.f_code.co_filename, True)
                            ):
                                # User uncaught means that we're currently in user code but the code
                                # up the stack is library code.
                                exc_info = prev_user_uncaught_exc_info
                                if not exc_info:
                                    exc_info = (arg, frame.f_lineno, set([frame.f_lineno]))
                                else:
                                    lines = exc_info[2]
                                    lines.add(frame.f_lineno)
                                    exc_info = (arg, frame.f_lineno, lines)
                                maybe_user_uncaught_exc_info = exc_info
                        else:
                            # I.e.: these are only checked if we're not dealing with user uncaught exceptions.
                            if (
                                exc_break.notify_on_first_raise_only
                                and py_db.skip_on_exceptions_thrown_in_same_context
                                and not was_just_raised
                                and not just_raised(trace.tb_next)
                            ):
                                # In this case we never stop if it was just raised, so, to know if it was the first we
                                # need to check if we're in the 2nd method.
                                should_stop = False  # I.e.: we stop only when we're at the caller of a method that throws an exception

                            elif (
                                exc_break.notify_on_first_raise_only
                                and not py_db.skip_on_exceptions_thrown_in_same_context
                                and not was_just_raised
                            ):
                                should_stop = False  # I.e.: we stop only when it was just raised

                            elif was_just_raised and py_db.skip_on_exceptions_thrown_in_same_context:
                                # Option: Don't break if an exception is caught in the same function from which it is thrown
                                should_stop = False

                        if should_stop:
                            exception_breakpoint = exc_break
                            try:
                                info.pydev_message = exc_break.qname
                            except:
                                info.pydev_message = exc_break.qname.encode("utf-8")
                            break

            if should_stop:
                # Always add exception to frame (must remove later after we proceed).
                add_exception_to_frame(frame, (exception, value, trace))

                if exception_breakpoint is not None and exception_breakpoint.expression is not None:
                    py_db.handle_breakpoint_expression(exception_breakpoint, info, frame)

    return should_stop, frame, maybe_user_uncaught_exc_info


# Same thing in the main debugger but only considering the file contents, while the one in the main debugger
# considers the user input (so, the actual result must be a join of both).
filename_to_lines_where_exceptions_are_ignored: dict = {}
filename_to_stat_info: dict = {}


# IFDEF CYTHON
# def handle_exception(py_db, thread, frame, arg, str exception_type):
#     cdef bint stopped;
#     cdef tuple abs_real_path_and_base;
#     cdef str absolute_filename;
#     cdef str canonical_normalized_filename;
#     cdef dict lines_ignored;
#     cdef dict frame_id_to_frame;
#     cdef dict merged;
#     cdef object trace_obj;
# ELSE
def handle_exception(py_db, thread, frame, arg, exception_type):
    # ENDIF
    stopped = False
    try:
        # print('handle_exception', frame.f_lineno, frame.f_code.co_name)

        # We have 3 things in arg: exception type, description, traceback object
        trace_obj = arg[2]

        initial_trace_obj = trace_obj
        if trace_obj.tb_next is None and trace_obj.tb_frame is frame:
            # I.e.: tb_next should be only None in the context it was thrown (trace_obj.tb_frame is frame is just a double check).
            pass
        else:
            # Get the trace_obj from where the exception was raised...
            while trace_obj.tb_next is not None:
                trace_obj = trace_obj.tb_next

        if py_db.ignore_exceptions_thrown_in_lines_with_ignore_exception:
            for check_trace_obj in (initial_trace_obj, trace_obj):
                abs_real_path_and_base = get_abs_path_real_path_and_base_from_frame(check_trace_obj.tb_frame)
                absolute_filename = abs_real_path_and_base[0]
                canonical_normalized_filename = abs_real_path_and_base[1]

                lines_ignored = filename_to_lines_where_exceptions_are_ignored.get(canonical_normalized_filename)
                if lines_ignored is None:
                    lines_ignored = filename_to_lines_where_exceptions_are_ignored[canonical_normalized_filename] = {}

                try:
                    curr_stat = os.stat(absolute_filename)
                    curr_stat = (curr_stat.st_size, curr_stat.st_mtime)
                except:
                    curr_stat = None

                last_stat = filename_to_stat_info.get(absolute_filename)
                if last_stat != curr_stat:
                    filename_to_stat_info[absolute_filename] = curr_stat
                    lines_ignored.clear()
                    try:
                        linecache.checkcache(absolute_filename)
                    except:
                        pydev_log.exception("Error in linecache.checkcache(%r)", absolute_filename)

                from_user_input = py_db.filename_to_lines_where_exceptions_are_ignored.get(canonical_normalized_filename)
                if from_user_input:
                    merged = {}
                    merged.update(lines_ignored)
                    # Override what we have with the related entries that the user entered
                    merged.update(from_user_input)
                else:
                    merged = lines_ignored

                exc_lineno = check_trace_obj.tb_lineno

                # print ('lines ignored', lines_ignored)
                # print ('user input', from_user_input)
                # print ('merged', merged, 'curr', exc_lineno)

                if exc_lineno not in merged:  # Note: check on merged but update lines_ignored.
                    try:
                        line = linecache.getline(absolute_filename, exc_lineno, check_trace_obj.tb_frame.f_globals)
                    except:
                        pydev_log.exception("Error in linecache.getline(%r, %s, f_globals)", absolute_filename, exc_lineno)
                        line = ""

                    if IGNORE_EXCEPTION_TAG.match(line) is not None:
                        lines_ignored[exc_lineno] = 1
                        return False
                    else:
                        # Put in the cache saying not to ignore
                        lines_ignored[exc_lineno] = 0
                else:
                    # Ok, dict has it already cached, so, let's check it...
                    if merged.get(exc_lineno, 0):
                        return False

        try:
            frame_id_to_frame = {}
            frame_id_to_frame[id(frame)] = frame
            f = trace_obj.tb_frame
            while f is not None:
                frame_id_to_frame[id(f)] = f
                f = f.f_back
            f = None

            stopped = True
            py_db.send_caught_exception_stack(thread, arg, id(frame))
            try:
                py_db.set_suspend(thread, CMD_STEP_CAUGHT_EXCEPTION)
                py_db.do_wait_suspend(thread, frame, "exception", arg, exception_type=exception_type)
            finally:
                py_db.send_caught_exception_stack_proceeded(thread)
        except:
            pydev_log.exception()

        py_db.set_trace_for_frame_and_parents(thread.ident, frame)
    finally:
        # Make sure the user cannot see the '__exception__' we added after we leave the suspend state.
        remove_exception_from_frame(frame)
        # Clear some local variables...
        frame = None
        trace_obj = None
        initial_trace_obj = None
        check_trace_obj = None
        f = None
        frame_id_to_frame = None
        py_db = None
        thread = None

    return stopped

# === NexusCore/openenv\Lib\site-packages\nltk\util.py ===
# Natural Language Toolkit: Utility functions
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Eric Kafe <kafe.eric@gmail.com> (acyclic closures)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
import inspect
import locale
import os
import pydoc
import re
import textwrap
import unicodedata
import warnings
from collections import defaultdict, deque
from itertools import chain, combinations, islice, tee
from pprint import pprint
from urllib.request import (
    HTTPPasswordMgrWithDefaultRealm,
    ProxyBasicAuthHandler,
    ProxyDigestAuthHandler,
    ProxyHandler,
    build_opener,
    getproxies,
    install_opener,
)

from nltk.collections import *
from nltk.internals import deprecated, raise_unorderable_types, slice_bounds

######################################################################
# Short usage message
######################################################################


@deprecated("Use help(obj) instead.")
def usage(obj):
    str(obj)  # In case it's lazy, this will load it.

    if not isinstance(obj, type):
        obj = obj.__class__

    print(f"{obj.__name__} supports the following operations:")
    for name, method in sorted(pydoc.allmethods(obj).items()):
        if name.startswith("_"):
            continue
        if getattr(method, "__deprecated__", False):
            continue

        try:
            sig = str(inspect.signature(method))
        except ValueError as e:
            # builtins sometimes don't support introspection
            if "builtin" in str(e):
                continue
            else:
                raise

        args = sig.lstrip("(").rstrip(")").split(", ")
        meth = inspect.getattr_static(obj, name)
        if isinstance(meth, (classmethod, staticmethod)):
            name = f"cls.{name}"
        elif args and args[0] == "self":
            name = f"self.{name}"
            args.pop(0)
        print(
            textwrap.fill(
                f"{name}({', '.join(args)})",
                initial_indent="  - ",
                subsequent_indent=" " * (len(name) + 5),
            )
        )


##########################################################################
# IDLE
##########################################################################


def in_idle():
    """
    Return True if this function is run within idle.  Tkinter
    programs that are run in idle should never call ``Tk.mainloop``; so
    this function should be used to gate all calls to ``Tk.mainloop``.

    :warning: This function works by checking ``sys.stdin``.  If the
        user has modified ``sys.stdin``, then it may return incorrect
        results.
    :rtype: bool
    """
    import sys

    return sys.stdin.__class__.__name__ in ("PyShell", "RPCProxy")


##########################################################################
# PRETTY PRINTING
##########################################################################


def pr(data, start=0, end=None):
    """
    Pretty print a sequence of data items

    :param data: the data stream to print
    :type data: sequence or iter
    :param start: the start position
    :type start: int
    :param end: the end position
    :type end: int
    """
    pprint(list(islice(data, start, end)))


def print_string(s, width=70):
    """
    Pretty print a string, breaking lines on whitespace

    :param s: the string to print, consisting of words and spaces
    :type s: str
    :param width: the display width
    :type width: int
    """
    print("\n".join(textwrap.wrap(s, width=width)))


def tokenwrap(tokens, separator=" ", width=70):
    """
    Pretty print a list of text tokens, breaking lines on whitespace

    :param tokens: the tokens to print
    :type tokens: list
    :param separator: the string to use to separate tokens
    :type separator: str
    :param width: the display width (default=70)
    :type width: int
    """
    return "\n".join(textwrap.wrap(separator.join(tokens), width=width))


def cut_string(s, width=70):
    """
    Cut off and return a given width of a string

    Return the same as s[:width] if width >= 0 or s[-width:] if
    width < 0, as long as s has no unicode combining characters.
    If it has combining characters make sure the returned string's
    visible width matches the called-for width.

    :param s: the string to cut
    :type s: str
    :param width: the display_width
    :type width: int
    """
    chars_sofar = 0
    width_sofar = 0
    result = ""

    abs_width = abs(width)
    max_chars = len(s)
    while width_sofar < abs_width and chars_sofar < max_chars:
        if width < 0:
            char = s[-(chars_sofar + 1)]
            result = char + result
        else:
            char = s[chars_sofar]
            result = result + char

        chars_sofar += 1
        if not unicodedata.combining(char):
            width_sofar += 1

    return result


##########################################################################
# Indexing
##########################################################################


class Index(defaultdict):
    def __init__(self, pairs):
        defaultdict.__init__(self, list)
        for key, value in pairs:
            self[key].append(value)


######################################################################
## Regexp display (thanks to David Mertz)
######################################################################


def re_show(regexp, string, left="{", right="}"):
    """
    Return a string with markers surrounding the matched substrings.
    Search str for substrings matching ``regexp`` and wrap the matches
    with braces.  This is convenient for learning about regular expressions.

    :param regexp: The regular expression.
    :type regexp: str
    :param string: The string being matched.
    :type string: str
    :param left: The left delimiter (printed before the matched substring)
    :type left: str
    :param right: The right delimiter (printed after the matched substring)
    :type right: str
    :rtype: str
    """
    print(re.compile(regexp, re.M).sub(left + r"\g<0>" + right, string.rstrip()))


##########################################################################
# READ FROM FILE OR STRING
##########################################################################


# recipe from David Mertz
def filestring(f):
    if hasattr(f, "read"):
        return f.read()
    elif isinstance(f, str):
        with open(f) as infile:
            return infile.read()
    else:
        raise ValueError("Must be called with a filename or file-like object")


##########################################################################
# Breadth-First Search
##########################################################################


def breadth_first(tree, children=iter, maxdepth=-1):
    """Traverse the nodes of a tree in breadth-first order.
    (No check for cycles.)
    The first argument should be the tree root;
    children should be a function taking as argument a tree node
    and returning an iterator of the node's children.
    """
    queue = deque([(tree, 0)])

    while queue:
        node, depth = queue.popleft()
        yield node

        if depth != maxdepth:
            try:
                queue.extend((c, depth + 1) for c in children(node))
            except TypeError:
                pass


##########################################################################
# Graph Drawing
##########################################################################


def edge_closure(tree, children=iter, maxdepth=-1, verbose=False):
    """
    :param tree: the tree root
    :param children: a function taking as argument a tree node
    :param maxdepth: to limit the search depth
    :param verbose: to print warnings when cycles are discarded

    Yield the edges of a graph in breadth-first order,
    discarding eventual cycles.
    The first argument should be the start node;
    children should be a function taking as argument a graph node
    and returning an iterator of the node's children.

    >>> from nltk.util import edge_closure
    >>> print(list(edge_closure('A', lambda node:{'A':['B','C'], 'B':'C', 'C':'B'}[node])))
    [('A', 'B'), ('A', 'C'), ('B', 'C'), ('C', 'B')]
    """
    traversed = set()
    edges = set()
    queue = deque([(tree, 0)])
    while queue:
        node, depth = queue.popleft()
        traversed.add(node)
        if depth != maxdepth:
            try:
                for child in children(node):
                    if child not in traversed:
                        queue.append((child, depth + 1))
                    else:
                        if verbose:
                            warnings.warn(
                                f"Discarded redundant search for {child} at depth {depth + 1}",
                                stacklevel=2,
                            )
                    edge = (node, child)
                    if edge not in edges:
                        yield edge
                        edges.add(edge)
            except TypeError:
                pass


def edges2dot(edges, shapes=None, attr=None):
    """
    :param edges: the set (or list) of edges of a directed graph.
    :param shapes: dictionary of strings that trigger a specified shape.
    :param attr: dictionary with global graph attributes
    :return: a representation of 'edges' as a string in the DOT graph language.

    Returns dot_string: a representation of 'edges' as a string in the DOT
    graph language, which can be converted to an image by the 'dot' program
    from the Graphviz package, or nltk.parse.dependencygraph.dot2img(dot_string).

    >>> import nltk
    >>> from nltk.util import edges2dot
    >>> print(edges2dot([('A', 'B'), ('A', 'C'), ('B', 'C'), ('C', 'B')]))
    digraph G {
    "A" -> "B";
    "A" -> "C";
    "B" -> "C";
    "C" -> "B";
    }
    <BLANKLINE>
    """
    if not shapes:
        shapes = dict()
    if not attr:
        attr = dict()

    dot_string = "digraph G {\n"

    for pair in attr.items():
        dot_string += f"{pair[0]} = {pair[1]};\n"

    for edge in edges:
        for shape in shapes.items():
            for node in range(2):
                if shape[0] in repr(edge[node]):
                    dot_string += f'"{edge[node]}" [shape = {shape[1]}];\n'
        dot_string += f'"{edge[0]}" -> "{edge[1]}";\n'

    dot_string += "}\n"
    return dot_string


def unweighted_minimum_spanning_digraph(tree, children=iter, shapes=None, attr=None):
    """
    :param tree: the tree root
    :param children: a function taking as argument a tree node
    :param shapes: dictionary of strings that trigger a specified shape.
    :param attr: dictionary with global graph attributes

        Build a Minimum Spanning Tree (MST) of an unweighted graph,
    by traversing the nodes of a tree in breadth-first order,
    discarding eventual cycles.

    Return a representation of this MST as a string in the DOT graph language,
    which can be converted to an image by the 'dot' program from the Graphviz
    package, or nltk.parse.dependencygraph.dot2img(dot_string).

    The first argument should be the tree root;
    children should be a function taking as argument a tree node
    and returning an iterator of the node's children.

    >>> import nltk
    >>> wn=nltk.corpus.wordnet
    >>> from nltk.util import unweighted_minimum_spanning_digraph as umsd
    >>> print(umsd(wn.synset('bound.a.01'), lambda s:sorted(s.also_sees())))
    digraph G {
    "Synset('bound.a.01')" -> "Synset('unfree.a.02')";
    "Synset('unfree.a.02')" -> "Synset('confined.a.02')";
    "Synset('unfree.a.02')" -> "Synset('dependent.a.01')";
    "Synset('unfree.a.02')" -> "Synset('restricted.a.01')";
    "Synset('restricted.a.01')" -> "Synset('classified.a.02')";
    }
    <BLANKLINE>
    """
    return edges2dot(
        edge_closure(
            tree, lambda node: unweighted_minimum_spanning_dict(tree, children)[node]
        ),
        shapes,
        attr,
    )


##########################################################################
# Breadth-First / Depth-first Searches with Cycle Detection
##########################################################################


def acyclic_breadth_first(tree, children=iter, maxdepth=-1, verbose=False):
    """
    :param tree: the tree root
    :param children: a function taking as argument a tree node
    :param maxdepth: to limit the search depth
    :param verbose: to print warnings when cycles are discarded
    :return: the tree in breadth-first order

        Adapted from breadth_first() above, to discard cycles.
    Traverse the nodes of a tree in breadth-first order,
    discarding eventual cycles.

    The first argument should be the tree root;
    children should be a function taking as argument a tree node
    and returning an iterator of the node's children.
    """
    traversed = set()
    queue = deque([(tree, 0)])
    while queue:
        node, depth = queue.popleft()
        if node in traversed:
            continue
        yield node
        traversed.add(node)
        if depth != maxdepth:
            try:
                for child in children(node):
                    if child not in traversed:
                        queue.append((child, depth + 1))
                    elif verbose:
                        warnings.warn(
                            "Discarded redundant search for {} at depth {}".format(
                                child, depth + 1
                            ),
                            stacklevel=2,
                        )
            except TypeError:
                pass


def acyclic_depth_first(
    tree, children=iter, depth=-1, cut_mark=None, traversed=None, verbose=False
):
    """
    :param tree: the tree root
    :param children: a function taking as argument a tree node
    :param depth: the maximum depth of the search
    :param cut_mark: the mark to add when cycles are truncated
    :param traversed: the set of traversed nodes
    :param verbose: to print warnings when cycles are discarded
    :return: the tree in depth-first order

    Traverse the nodes of a tree in depth-first order,
    discarding eventual cycles within any branch,
    adding cut_mark (when specified) if cycles were truncated.
    The first argument should be the tree root;
    children should be a function taking as argument a tree node
    and returning an iterator of the node's children.

    Catches all cycles:

    >>> import nltk
    >>> from nltk.util import acyclic_depth_first as acyclic_tree
    >>> wn=nltk.corpus.wordnet
    >>> from pprint import pprint
    >>> pprint(acyclic_tree(wn.synset('dog.n.01'), lambda s:sorted(s.hypernyms()),cut_mark='...'))
    [Synset('dog.n.01'),
     [Synset('canine.n.02'),
      [Synset('carnivore.n.01'),
       [Synset('placental.n.01'),
        [Synset('mammal.n.01'),
         [Synset('vertebrate.n.01'),
          [Synset('chordate.n.01'),
           [Synset('animal.n.01'),
            [Synset('organism.n.01'),
             [Synset('living_thing.n.01'),
              [Synset('whole.n.02'),
               [Synset('object.n.01'),
                [Synset('physical_entity.n.01'),
                 [Synset('entity.n.01')]]]]]]]]]]]]],
     [Synset('domestic_animal.n.01'), "Cycle(Synset('animal.n.01'),-3,...)"]]
    """
    if traversed is None:
        traversed = {tree}
    out_tree = [tree]
    if depth != 0:
        try:
            for child in children(tree):
                if child not in traversed:
                    # Recurse with a common "traversed" set for all children:
                    traversed.add(child)
                    out_tree += [
                        acyclic_depth_first(
                            child, children, depth - 1, cut_mark, traversed
                        )
                    ]
                else:
                    if verbose:
                        warnings.warn(
                            "Discarded redundant search for {} at depth {}".format(
                                child, depth - 1
                            ),
                            stacklevel=3,
                        )
                    if cut_mark:
                        out_tree += [f"Cycle({child},{depth - 1},{cut_mark})"]
        except TypeError:
            pass
    elif cut_mark:
        out_tree += [cut_mark]
    return out_tree


def acyclic_branches_depth_first(
    tree, children=iter, depth=-1, cut_mark=None, traversed=None, verbose=False
):
    """
    :param tree: the tree root
    :param children: a function taking as argument a tree node
    :param depth: the maximum depth of the search
    :param cut_mark: the mark to add when cycles are truncated
    :param traversed: the set of traversed nodes
    :param verbose: to print warnings when cycles are discarded
    :return: the tree in depth-first order

        Adapted from acyclic_depth_first() above, to
    traverse the nodes of a tree in depth-first order,
    discarding eventual cycles within the same branch,
    but keep duplicate paths in different branches.
    Add cut_mark (when defined) if cycles were truncated.

    The first argument should be the tree root;
    children should be a function taking as argument a tree node
    and returning an iterator of the node's children.

    Catches only only cycles within the same branch,
    but keeping cycles from different branches:

    >>> import nltk
    >>> from nltk.util import acyclic_branches_depth_first as tree
    >>> wn=nltk.corpus.wordnet
    >>> from pprint import pprint
    >>> pprint(tree(wn.synset('certified.a.01'), lambda s:sorted(s.also_sees()), cut_mark='...', depth=4))
    [Synset('certified.a.01'),
     [Synset('authorized.a.01'),
      [Synset('lawful.a.01'),
       [Synset('legal.a.01'),
        "Cycle(Synset('lawful.a.01'),0,...)",
        [Synset('legitimate.a.01'), '...']],
       [Synset('straight.a.06'),
        [Synset('honest.a.01'), '...'],
        "Cycle(Synset('lawful.a.01'),0,...)"]],
      [Synset('legitimate.a.01'),
       "Cycle(Synset('authorized.a.01'),1,...)",
       [Synset('legal.a.01'),
        [Synset('lawful.a.01'), '...'],
        "Cycle(Synset('legitimate.a.01'),0,...)"],
       [Synset('valid.a.01'),
        "Cycle(Synset('legitimate.a.01'),0,...)",
        [Synset('reasonable.a.01'), '...']]],
      [Synset('official.a.01'), "Cycle(Synset('authorized.a.01'),1,...)"]],
     [Synset('documented.a.01')]]
    """
    if traversed is None:
        traversed = {tree}
    out_tree = [tree]
    if depth != 0:
        try:
            for child in children(tree):
                if child not in traversed:
                    # Recurse with a different "traversed" set for each child:
                    out_tree += [
                        acyclic_branches_depth_first(
                            child,
                            children,
                            depth - 1,
                            cut_mark,
                            traversed.union({child}),
                        )
                    ]
                else:
                    if verbose:
                        warnings.warn(
                            "Discarded redundant search for {} at depth {}".format(
                                child, depth - 1
                            ),
                            stacklevel=3,
                        )
                    if cut_mark:
                        out_tree += [f"Cycle({child},{depth - 1},{cut_mark})"]
        except TypeError:
            pass
    elif cut_mark:
        out_tree += [cut_mark]
    return out_tree


def acyclic_dic2tree(node, dic):
    """
    :param node: the root node
    :param dic: the dictionary of children

    Convert acyclic dictionary 'dic', where the keys are nodes, and the
    values are lists of children, to output tree suitable for pprint(),
    starting at root 'node', with subtrees as nested lists."""
    return [node] + [acyclic_dic2tree(child, dic) for child in dic[node]]


def unweighted_minimum_spanning_dict(tree, children=iter):
    """
    :param tree: the tree root
    :param children: a function taking as argument a tree node

            Output a dictionary representing a Minimum Spanning Tree (MST)
    of an unweighted graph, by traversing the nodes of a tree in
    breadth-first order, discarding eventual cycles.

    The first argument should be the tree root;
    children should be a function taking as argument a tree node
    and returning an iterator of the node's children.

    >>> import nltk
    >>> from nltk.corpus import wordnet as wn
    >>> from nltk.util import unweighted_minimum_spanning_dict as umsd
    >>> from pprint import pprint
    >>> pprint(umsd(wn.synset('bound.a.01'), lambda s:sorted(s.also_sees())))
    {Synset('bound.a.01'): [Synset('unfree.a.02')],
     Synset('classified.a.02'): [],
     Synset('confined.a.02'): [],
     Synset('dependent.a.01'): [],
     Synset('restricted.a.01'): [Synset('classified.a.02')],
     Synset('unfree.a.02'): [Synset('confined.a.02'),
                             Synset('dependent.a.01'),
                             Synset('restricted.a.01')]}

    """
    traversed = set()  # Empty set of traversed nodes
    queue = deque([tree])  # Initialize queue
    agenda = {tree}  # Set of all nodes ever queued
    mstdic = {}  # Empty MST dictionary
    while queue:
        node = queue.popleft()  # Node is not yet in the MST dictionary,
        mstdic[node] = []  # so add it with an empty list of children
        if node not in traversed:  # Avoid cycles
            traversed.add(node)
            for child in children(node):
                if child not in agenda:  # Queue nodes only once
                    mstdic[node].append(child)  # Add child to the MST
                    queue.append(child)  # Add child to queue
                    agenda.add(child)
    return mstdic


def unweighted_minimum_spanning_tree(tree, children=iter):
    """
    :param tree: the tree root
    :param children: a function taking as argument a tree node

       Output a Minimum Spanning Tree (MST) of an unweighted graph,
    by traversing the nodes of a tree in breadth-first order,
    discarding eventual cycles.

    The first argument should be the tree root;
    children should be a function taking as argument a tree node
    and returning an iterator of the node's children.

    >>> import nltk
    >>> from nltk.util import unweighted_minimum_spanning_tree as mst
    >>> wn=nltk.corpus.wordnet
    >>> from pprint import pprint
    >>> pprint(mst(wn.synset('bound.a.01'), lambda s:sorted(s.also_sees())))
    [Synset('bound.a.01'),
     [Synset('unfree.a.02'),
      [Synset('confined.a.02')],
      [Synset('dependent.a.01')],
      [Synset('restricted.a.01'), [Synset('classified.a.02')]]]]
    """
    return acyclic_dic2tree(tree, unweighted_minimum_spanning_dict(tree, children))


##########################################################################
# Guess Character Encoding
##########################################################################

# adapted from io.py in the docutils extension module (https://docutils.sourceforge.io/)
# http://www.pyzine.com/Issue008/Section_Articles/article_Encodings.html


def guess_encoding(data):
    """
    Given a byte string, attempt to decode it.
    Tries the standard 'UTF8' and 'latin-1' encodings,
    Plus several gathered from locale information.

    The calling program *must* first call::

        locale.setlocale(locale.LC_ALL, '')

    If successful it returns ``(decoded_unicode, successful_encoding)``.
    If unsuccessful it raises a ``UnicodeError``.
    """
    successful_encoding = None
    # we make 'utf-8' the first encoding
    encodings = ["utf-8"]
    #
    # next we add anything we can learn from the locale
    try:
        encodings.append(locale.nl_langinfo(locale.CODESET))
    except AttributeError:
        pass
    try:
        encodings.append(locale.getlocale()[1])
    except (AttributeError, IndexError):
        pass
    try:
        encodings.append(locale.getdefaultlocale()[1])
    except (AttributeError, IndexError):
        pass
    #
    # we try 'latin-1' last
    encodings.append("latin-1")
    for enc in encodings:
        # some of the locale calls
        # may have returned None
        if not enc:
            continue
        try:
            decoded = str(data, enc)
            successful_encoding = enc

        except (UnicodeError, LookupError):
            pass
        else:
            break
    if not successful_encoding:
        raise UnicodeError(
            "Unable to decode input data. "
            "Tried the following encodings: %s."
            % ", ".join([repr(enc) for enc in encodings if enc])
        )
    else:
        return (decoded, successful_encoding)


##########################################################################
# Remove repeated elements from a list deterministcally
##########################################################################


def unique_list(xs):
    seen = set()
    # not seen.add(x) here acts to make the code shorter without using if statements, seen.add(x) always returns None.
    return [x for x in xs if x not in seen and not seen.add(x)]


##########################################################################
# Invert a dictionary
##########################################################################


def invert_dict(d):
    inverted_dict = defaultdict(list)
    for key in d:
        if hasattr(d[key], "__iter__"):
            for term in d[key]:
                inverted_dict[term].append(key)
        else:
            inverted_dict[d[key]] = key
    return inverted_dict


##########################################################################
# Utilities for directed graphs: transitive closure, and inversion
# The graph is represented as a dictionary of sets
##########################################################################


def transitive_closure(graph, reflexive=False):
    """
    Calculate the transitive closure of a directed graph,
    optionally the reflexive transitive closure.

    The algorithm is a slight modification of the "Marking Algorithm" of
    Ioannidis & Ramakrishnan (1998) "Efficient Transitive Closure Algorithms".

    :param graph: the initial graph, represented as a dictionary of sets
    :type graph: dict(set)
    :param reflexive: if set, also make the closure reflexive
    :type reflexive: bool
    :rtype: dict(set)
    """
    if reflexive:
        base_set = lambda k: {k}
    else:
        base_set = lambda k: set()
    # The graph U_i in the article:
    agenda_graph = {k: graph[k].copy() for k in graph}
    # The graph M_i in the article:
    closure_graph = {k: base_set(k) for k in graph}
    for i in graph:
        agenda = agenda_graph[i]
        closure = closure_graph[i]
        while agenda:
            j = agenda.pop()
            closure.add(j)
            closure |= closure_graph.setdefault(j, base_set(j))
            agenda |= agenda_graph.get(j, base_set(j))
            agenda -= closure
    return closure_graph


def invert_graph(graph):
    """
    Inverts a directed graph.

    :param graph: the graph, represented as a dictionary of sets
    :type graph: dict(set)
    :return: the inverted graph
    :rtype: dict(set)
    """
    inverted = {}
    for key in graph:
        for value in graph[key]:
            inverted.setdefault(value, set()).add(key)
    return inverted


##########################################################################
# HTML Cleaning
##########################################################################


def clean_html(html):
    raise NotImplementedError(
        "To remove HTML markup, use BeautifulSoup's get_text() function"
    )


def clean_url(url):
    raise NotImplementedError(
        "To remove HTML markup, use BeautifulSoup's get_text() function"
    )


##########################################################################
# FLATTEN LISTS
##########################################################################


def flatten(*args):
    """
    Flatten a list.

        >>> from nltk.util import flatten
        >>> flatten(1, 2, ['b', 'a' , ['c', 'd']], 3)
        [1, 2, 'b', 'a', 'c', 'd', 3]

    :param args: items and lists to be combined into a single list
    :rtype: list
    """

    x = []
    for l in args:
        if not isinstance(l, (list, tuple)):
            l = [l]
        for item in l:
            if isinstance(item, (list, tuple)):
                x.extend(flatten(item))
            else:
                x.append(item)
    return x


##########################################################################
# Ngram iteration
##########################################################################


def pad_sequence(
    sequence,
    n,
    pad_left=False,
    pad_right=False,
    left_pad_symbol=None,
    right_pad_symbol=None,
):
    """
    Returns a padded sequence of items before ngram extraction.

        >>> list(pad_sequence([1,2,3,4,5], 2, pad_left=True, pad_right=True, left_pad_symbol='<s>', right_pad_symbol='</s>'))
        ['<s>', 1, 2, 3, 4, 5, '</s>']
        >>> list(pad_sequence([1,2,3,4,5], 2, pad_left=True, left_pad_symbol='<s>'))
        ['<s>', 1, 2, 3, 4, 5]
        >>> list(pad_sequence([1,2,3,4,5], 2, pad_right=True, right_pad_symbol='</s>'))
        [1, 2, 3, 4, 5, '</s>']

    :param sequence: the source data to be padded
    :type sequence: sequence or iter
    :param n: the degree of the ngrams
    :type n: int
    :param pad_left: whether the ngrams should be left-padded
    :type pad_left: bool
    :param pad_right: whether the ngrams should be right-padded
    :type pad_right: bool
    :param left_pad_symbol: the symbol to use for left padding (default is None)
    :type left_pad_symbol: any
    :param right_pad_symbol: the symbol to use for right padding (default is None)
    :type right_pad_symbol: any
    :rtype: sequence or iter
    """
    sequence = iter(sequence)
    if pad_left:
        sequence = chain((left_pad_symbol,) * (n - 1), sequence)
    if pad_right:
        sequence = chain(sequence, (right_pad_symbol,) * (n - 1))
    return sequence


# add a flag to pad the sequence so we get peripheral ngrams?


def ngrams(sequence, n, **kwargs):
    """
    Return the ngrams generated from a sequence of items, as an iterator.
    For example:

        >>> from nltk.util import ngrams
        >>> list(ngrams([1,2,3,4,5], 3))
        [(1, 2, 3), (2, 3, 4), (3, 4, 5)]

    Wrap with list for a list version of this function.  Set pad_left
    or pad_right to true in order to get additional ngrams:

        >>> list(ngrams([1,2,3,4,5], 2, pad_right=True))
        [(1, 2), (2, 3), (3, 4), (4, 5), (5, None)]
        >>> list(ngrams([1,2,3,4,5], 2, pad_right=True, right_pad_symbol='</s>'))
        [(1, 2), (2, 3), (3, 4), (4, 5), (5, '</s>')]
        >>> list(ngrams([1,2,3,4,5], 2, pad_left=True, left_pad_symbol='<s>'))
        [('<s>', 1), (1, 2), (2, 3), (3, 4), (4, 5)]
        >>> list(ngrams([1,2,3,4,5], 2, pad_left=True, pad_right=True, left_pad_symbol='<s>', right_pad_symbol='</s>'))
        [('<s>', 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, '</s>')]


    :param sequence: the source data to be converted into ngrams
    :type sequence: sequence or iter
    :param n: the degree of the ngrams
    :type n: int
    :param pad_left: whether the ngrams should be left-padded
    :type pad_left: bool
    :param pad_right: whether the ngrams should be right-padded
    :type pad_right: bool
    :param left_pad_symbol: the symbol to use for left padding (default is None)
    :type left_pad_symbol: any
    :param right_pad_symbol: the symbol to use for right padding (default is None)
    :type right_pad_symbol: any
    :rtype: sequence or iter
    """
    sequence = pad_sequence(sequence, n, **kwargs)

    # sliding_window('ABCDEFG', 4) --> ABCD BCDE CDEF DEFG
    # https://docs.python.org/3/library/itertools.html?highlight=sliding_window#itertools-recipes
    it = iter(sequence)
    window = deque(islice(it, n), maxlen=n)
    if len(window) == n:
        yield tuple(window)
    for x in it:
        window.append(x)
        yield tuple(window)


def bigrams(sequence, **kwargs):
    """
    Return the bigrams generated from a sequence of items, as an iterator.
    For example:

        >>> from nltk.util import bigrams
        >>> list(bigrams([1,2,3,4,5]))
        [(1, 2), (2, 3), (3, 4), (4, 5)]

    Use bigrams for a list version of this function.

    :param sequence: the source data to be converted into bigrams
    :type sequence: sequence or iter
    :rtype: iter(tuple)
    """

    yield from ngrams(sequence, 2, **kwargs)


def trigrams(sequence, **kwargs):
    """
    Return the trigrams generated from a sequence of items, as an iterator.
    For example:

        >>> from nltk.util import trigrams
        >>> list(trigrams([1,2,3,4,5]))
        [(1, 2, 3), (2, 3, 4), (3, 4, 5)]

    Use trigrams for a list version of this function.

    :param sequence: the source data to be converted into trigrams
    :type sequence: sequence or iter
    :rtype: iter(tuple)
    """

    yield from ngrams(sequence, 3, **kwargs)


def everygrams(
    sequence, min_len=1, max_len=-1, pad_left=False, pad_right=False, **kwargs
):
    """
    Returns all possible ngrams generated from a sequence of items, as an iterator.

        >>> sent = 'a b c'.split()

    New version outputs for everygrams.
        >>> list(everygrams(sent))
        [('a',), ('a', 'b'), ('a', 'b', 'c'), ('b',), ('b', 'c'), ('c',)]

    Old version outputs for everygrams.
        >>> sorted(everygrams(sent), key=len)
        [('a',), ('b',), ('c',), ('a', 'b'), ('b', 'c'), ('a', 'b', 'c')]

        >>> list(everygrams(sent, max_len=2))
        [('a',), ('a', 'b'), ('b',), ('b', 'c'), ('c',)]

    :param sequence: the source data to be converted into ngrams. If max_len is
        not provided, this sequence will be loaded into memory
    :type sequence: sequence or iter
    :param min_len: minimum length of the ngrams, aka. n-gram order/degree of ngram
    :type  min_len: int
    :param max_len: maximum length of the ngrams (set to length of sequence by default)
    :type  max_len: int
    :param pad_left: whether the ngrams should be left-padded
    :type pad_left: bool
    :param pad_right: whether the ngrams should be right-padded
    :type pad_right: bool
    :rtype: iter(tuple)
    """

    # Get max_len for padding.
    if max_len == -1:
        try:
            max_len = len(sequence)
        except TypeError:
            sequence = list(sequence)
            max_len = len(sequence)

    # Pad if indicated using max_len.
    sequence = pad_sequence(sequence, max_len, pad_left, pad_right, **kwargs)

    # Sliding window to store grams.
    history = list(islice(sequence, max_len))

    # Yield ngrams from sequence.
    while history:
        for ngram_len in range(min_len, len(history) + 1):
            yield tuple(history[:ngram_len])

        # Append element to history if sequence has more items.
        try:
            history.append(next(sequence))
        except StopIteration:
            pass

        del history[0]


def skipgrams(sequence, n, k, **kwargs):
    """
    Returns all possible skipgrams generated from a sequence of items, as an iterator.
    Skipgrams are ngrams that allows tokens to be skipped.
    Refer to http://homepages.inf.ed.ac.uk/ballison/pdf/lrec_skipgrams.pdf

        >>> sent = "Insurgents killed in ongoing fighting".split()
        >>> list(skipgrams(sent, 2, 2))
        [('Insurgents', 'killed'), ('Insurgents', 'in'), ('Insurgents', 'ongoing'), ('killed', 'in'), ('killed', 'ongoing'), ('killed', 'fighting'), ('in', 'ongoing'), ('in', 'fighting'), ('ongoing', 'fighting')]
        >>> list(skipgrams(sent, 3, 2))
        [('Insurgents', 'killed', 'in'), ('Insurgents', 'killed', 'ongoing'), ('Insurgents', 'killed', 'fighting'), ('Insurgents', 'in', 'ongoing'), ('Insurgents', 'in', 'fighting'), ('Insurgents', 'ongoing', 'fighting'), ('killed', 'in', 'ongoing'), ('killed', 'in', 'fighting'), ('killed', 'ongoing', 'fighting'), ('in', 'ongoing', 'fighting')]

    :param sequence: the source data to be converted into trigrams
    :type sequence: sequence or iter
    :param n: the degree of the ngrams
    :type n: int
    :param k: the skip distance
    :type  k: int
    :rtype: iter(tuple)
    """

    # Pads the sequence as desired by **kwargs.
    if "pad_left" in kwargs or "pad_right" in kwargs:
        sequence = pad_sequence(sequence, n, **kwargs)

    # Note when iterating through the ngrams, the pad_right here is not
    # the **kwargs padding, it's for the algorithm to detect the SENTINEL
    # object on the right pad to stop inner loop.
    SENTINEL = object()
    for ngram in ngrams(sequence, n + k, pad_right=True, right_pad_symbol=SENTINEL):
        head = ngram[:1]
        tail = ngram[1:]
        for skip_tail in combinations(tail, n - 1):
            if skip_tail[-1] is SENTINEL:
                continue
            yield head + skip_tail


######################################################################
# Binary Search in a File
######################################################################


# inherited from pywordnet, by Oliver Steele
def binary_search_file(file, key, cache=None, cacheDepth=-1):
    """
    Return the line from the file with first word key.
    Searches through a sorted file using the binary search algorithm.

    :type file: file
    :param file: the file to be searched through.
    :type key: str
    :param key: the identifier we are searching for.
    """

    key = key + " "
    keylen = len(key)
    start = 0
    currentDepth = 0

    if hasattr(file, "name"):
        end = os.stat(file.name).st_size - 1
    else:
        file.seek(0, 2)
        end = file.tell() - 1
        file.seek(0)

    if cache is None:
        cache = {}

    while start < end:
        lastState = start, end
        middle = (start + end) // 2

        if cache.get(middle):
            offset, line = cache[middle]

        else:
            line = ""
            while True:
                file.seek(max(0, middle - 1))
                if middle > 0:
                    file.discard_line()
                offset = file.tell()
                line = file.readline()
                if line != "":
                    break
                # at EOF; try to find start of the last line
                middle = (start + middle) // 2
                if middle == end - 1:
                    return None
            if currentDepth < cacheDepth:
                cache[middle] = (offset, line)

        if offset > end:
            assert end != middle - 1, "infinite loop"
            end = middle - 1
        elif line[:keylen] == key:
            return line
        elif line > key:
            assert end != middle - 1, "infinite loop"
            end = middle - 1
        elif line < key:
            start = offset + len(line) - 1

        currentDepth += 1
        thisState = start, end

        if lastState == thisState:
            # Detects the condition where we're searching past the end
            # of the file, which is otherwise difficult to detect
            return None

    return None


######################################################################
# Proxy configuration
######################################################################


def set_proxy(proxy, user=None, password=""):
    """
    Set the HTTP proxy for Python to download through.

    If ``proxy`` is None then tries to set proxy from environment or system
    settings.

    :param proxy: The HTTP proxy server to use. For example:
        'http://proxy.example.com:3128/'
    :param user: The username to authenticate with. Use None to disable
        authentication.
    :param password: The password to authenticate with.
    """
    if proxy is None:
        # Try and find the system proxy settings
        try:
            proxy = getproxies()["http"]
        except KeyError as e:
            raise ValueError("Could not detect default proxy settings") from e

    # Set up the proxy handler
    proxy_handler = ProxyHandler({"https": proxy, "http": proxy})
    opener = build_opener(proxy_handler)

    if user is not None:
        # Set up basic proxy authentication if provided
        password_manager = HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(realm=None, uri=proxy, user=user, passwd=password)
        opener.add_handler(ProxyBasicAuthHandler(password_manager))
        opener.add_handler(ProxyDigestAuthHandler(password_manager))

    # Override the existing url opener
    install_opener(opener)


######################################################################
# ElementTree pretty printing from https://www.effbot.org/zone/element-lib.htm
######################################################################


def elementtree_indent(elem, level=0):
    """
    Recursive function to indent an ElementTree._ElementInterface
    used for pretty printing. Run indent on elem and then output
    in the normal way.

    :param elem: element to be indented. will be modified.
    :type elem: ElementTree._ElementInterface
    :param level: level of indentation for this element
    :type level: nonnegative integer
    :rtype:   ElementTree._ElementInterface
    :return:  Contents of elem indented to reflect its structure
    """

    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for elem in elem:
            elementtree_indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


######################################################################
# Mathematical approximations
######################################################################


def choose(n, k):
    """
    This function is a fast way to calculate binomial coefficients, commonly
    known as nCk, i.e. the number of combinations of n things taken k at a time.
    (https://en.wikipedia.org/wiki/Binomial_coefficient).

    This is the *scipy.special.comb()* with long integer computation but this
    approximation is faster, see https://github.com/nltk/nltk/issues/1181

        >>> choose(4, 2)
        6
        >>> choose(6, 2)
        15

    :param n: The number of things.
    :type n: int
    :param r: The number of times a thing is taken.
    :type r: int
    """
    if 0 <= k <= n:
        ntok, ktok = 1, 1
        for t in range(1, min(k, n - k) + 1):
            ntok *= n
            ktok *= t
            n -= 1
        return ntok // ktok
    else:
        return 0


######################################################################
# Iteration utilities
######################################################################


def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


######################################################################
# Parallelization.
######################################################################


def parallelize_preprocess(func, iterator, processes, progress_bar=False):
    from joblib import Parallel, delayed
    from tqdm import tqdm

    iterator = tqdm(iterator) if progress_bar else iterator
    if processes <= 1:
        return map(func, iterator)
    return Parallel(n_jobs=processes)(delayed(func)(line) for line in iterator)

# === NexusCore/openenv\Lib\site-packages\IPython\core\latex_symbols.py ===
# encoding: utf-8

# DO NOT EDIT THIS FILE BY HAND.

# To update this file, run the script /tools/gen_latex_symbols.py using Python 3

# This file is autogenerated from the file:
# https://raw.githubusercontent.com/JuliaLang/julia/master/stdlib/REPL/src/latex_symbols.jl
# This original list is filtered to remove any unicode characters that are not valid
# Python identifiers.

latex_symbols = {
    "\\euler": "ℯ",
    "\\ohm": "Ω",
    "\\^a": "ᵃ",
    "\\^b": "ᵇ",
    "\\^c": "ᶜ",
    "\\^d": "ᵈ",
    "\\^e": "ᵉ",
    "\\^f": "ᶠ",
    "\\^g": "ᵍ",
    "\\^h": "ʰ",
    "\\^i": "ⁱ",
    "\\^j": "ʲ",
    "\\^k": "ᵏ",
    "\\^l": "ˡ",
    "\\^m": "ᵐ",
    "\\^n": "ⁿ",
    "\\^o": "ᵒ",
    "\\^p": "ᵖ",
    "\\^r": "ʳ",
    "\\^s": "ˢ",
    "\\^t": "ᵗ",
    "\\^u": "ᵘ",
    "\\^v": "ᵛ",
    "\\^w": "ʷ",
    "\\^x": "ˣ",
    "\\^y": "ʸ",
    "\\^z": "ᶻ",
    "\\^A": "ᴬ",
    "\\^B": "ᴮ",
    "\\^D": "ᴰ",
    "\\^E": "ᴱ",
    "\\^G": "ᴳ",
    "\\^H": "ᴴ",
    "\\^I": "ᴵ",
    "\\^J": "ᴶ",
    "\\^K": "ᴷ",
    "\\^L": "ᴸ",
    "\\^M": "ᴹ",
    "\\^N": "ᴺ",
    "\\^O": "ᴼ",
    "\\^P": "ᴾ",
    "\\^R": "ᴿ",
    "\\^T": "ᵀ",
    "\\^U": "ᵁ",
    "\\^V": "ⱽ",
    "\\^W": "ᵂ",
    "\\^alpha": "ᵅ",
    "\\^beta": "ᵝ",
    "\\^gamma": "ᵞ",
    "\\^delta": "ᵟ",
    "\\^epsilon": "ᵋ",
    "\\^theta": "ᶿ",
    "\\^iota": "ᶥ",
    "\\^phi": "ᵠ",
    "\\^chi": "ᵡ",
    "\\^ltphi": "ᶲ",
    "\\^uparrow": "ꜛ",
    "\\^downarrow": "ꜜ",
    "\\^!": "ꜝ",
    "\\_a": "ₐ",
    "\\_e": "ₑ",
    "\\_h": "ₕ",
    "\\_i": "ᵢ",
    "\\_j": "ⱼ",
    "\\_k": "ₖ",
    "\\_l": "ₗ",
    "\\_m": "ₘ",
    "\\_n": "ₙ",
    "\\_o": "ₒ",
    "\\_p": "ₚ",
    "\\_r": "ᵣ",
    "\\_s": "ₛ",
    "\\_t": "ₜ",
    "\\_u": "ᵤ",
    "\\_v": "ᵥ",
    "\\_x": "ₓ",
    "\\_schwa": "ₔ",
    "\\_beta": "ᵦ",
    "\\_gamma": "ᵧ",
    "\\_rho": "ᵨ",
    "\\_phi": "ᵩ",
    "\\_chi": "ᵪ",
    "\\hbar": "ħ",
    "\\sout": "̶",
    "\\ordfeminine": "ª",
    "\\cdotp": "·",
    "\\ordmasculine": "º",
    "\\AA": "Å",
    "\\AE": "Æ",
    "\\DH": "Ð",
    "\\O": "Ø",
    "\\TH": "Þ",
    "\\ss": "ß",
    "\\aa": "å",
    "\\ae": "æ",
    "\\eth": "ð",
    "\\dh": "ð",
    "\\o": "ø",
    "\\th": "þ",
    "\\DJ": "Đ",
    "\\dj": "đ",
    "\\imath": "ı",
    "\\jmath": "ȷ",
    "\\L": "Ł",
    "\\l": "ł",
    "\\NG": "Ŋ",
    "\\ng": "ŋ",
    "\\OE": "Œ",
    "\\oe": "œ",
    "\\hvlig": "ƕ",
    "\\nrleg": "ƞ",
    "\\doublepipe": "ǂ",
    "\\trna": "ɐ",
    "\\trnsa": "ɒ",
    "\\openo": "ɔ",
    "\\rtld": "ɖ",
    "\\schwa": "ə",
    "\\varepsilon": "ε",
    "\\pgamma": "ɣ",
    "\\pbgam": "ɤ",
    "\\trnh": "ɥ",
    "\\btdl": "ɬ",
    "\\rtll": "ɭ",
    "\\trnm": "ɯ",
    "\\trnmlr": "ɰ",
    "\\ltlmr": "ɱ",
    "\\ltln": "ɲ",
    "\\rtln": "ɳ",
    "\\clomeg": "ɷ",
    "\\ltphi": "ɸ",
    "\\trnr": "ɹ",
    "\\trnrl": "ɺ",
    "\\rttrnr": "ɻ",
    "\\rl": "ɼ",
    "\\rtlr": "ɽ",
    "\\fhr": "ɾ",
    "\\rtls": "ʂ",
    "\\esh": "ʃ",
    "\\trnt": "ʇ",
    "\\rtlt": "ʈ",
    "\\pupsil": "ʊ",
    "\\pscrv": "ʋ",
    "\\invv": "ʌ",
    "\\invw": "ʍ",
    "\\trny": "ʎ",
    "\\rtlz": "ʐ",
    "\\yogh": "ʒ",
    "\\glst": "ʔ",
    "\\reglst": "ʕ",
    "\\inglst": "ʖ",
    "\\turnk": "ʞ",
    "\\dyogh": "ʤ",
    "\\tesh": "ʧ",
    "\\rasp": "ʼ",
    "\\verts": "ˈ",
    "\\verti": "ˌ",
    "\\lmrk": "ː",
    "\\hlmrk": "ˑ",
    "\\grave": "̀",
    "\\acute": "́",
    "\\hat": "̂",
    "\\tilde": "̃",
    "\\bar": "̄",
    "\\breve": "̆",
    "\\dot": "̇",
    "\\ddot": "̈",
    "\\ocirc": "̊",
    "\\H": "̋",
    "\\check": "̌",
    "\\palh": "̡",
    "\\rh": "̢",
    "\\c": "̧",
    "\\k": "̨",
    "\\sbbrg": "̪",
    "\\strike": "̶",
    "\\Alpha": "Α",
    "\\Beta": "Β",
    "\\Gamma": "Γ",
    "\\Delta": "Δ",
    "\\Epsilon": "Ε",
    "\\Zeta": "Ζ",
    "\\Eta": "Η",
    "\\Theta": "Θ",
    "\\Iota": "Ι",
    "\\Kappa": "Κ",
    "\\Lambda": "Λ",
    "\\Xi": "Ξ",
    "\\Pi": "Π",
    "\\Rho": "Ρ",
    "\\Sigma": "Σ",
    "\\Tau": "Τ",
    "\\Upsilon": "Υ",
    "\\Phi": "Φ",
    "\\Chi": "Χ",
    "\\Psi": "Ψ",
    "\\Omega": "Ω",
    "\\alpha": "α",
    "\\beta": "β",
    "\\gamma": "γ",
    "\\delta": "δ",
    "\\zeta": "ζ",
    "\\eta": "η",
    "\\theta": "θ",
    "\\iota": "ι",
    "\\kappa": "κ",
    "\\lambda": "λ",
    "\\mu": "μ",
    "\\nu": "ν",
    "\\xi": "ξ",
    "\\pi": "π",
    "\\rho": "ρ",
    "\\varsigma": "ς",
    "\\sigma": "σ",
    "\\tau": "τ",
    "\\upsilon": "υ",
    "\\varphi": "φ",
    "\\chi": "χ",
    "\\psi": "ψ",
    "\\omega": "ω",
    "\\vartheta": "ϑ",
    "\\phi": "ϕ",
    "\\varpi": "ϖ",
    "\\Stigma": "Ϛ",
    "\\Digamma": "Ϝ",
    "\\digamma": "ϝ",
    "\\Koppa": "Ϟ",
    "\\Sampi": "Ϡ",
    "\\varkappa": "ϰ",
    "\\varrho": "ϱ",
    "\\varTheta": "ϴ",
    "\\epsilon": "ϵ",
    "\\dddot": "⃛",
    "\\ddddot": "⃜",
    "\\hslash": "ℏ",
    "\\Im": "ℑ",
    "\\ell": "ℓ",
    "\\wp": "℘",
    "\\Re": "ℜ",
    "\\aleph": "ℵ",
    "\\beth": "ℶ",
    "\\gimel": "ℷ",
    "\\daleth": "ℸ",
    "\\bbPi": "ℿ",
    "\\Zbar": "Ƶ",
    "\\overbar": "̅",
    "\\ovhook": "̉",
    "\\candra": "̐",
    "\\oturnedcomma": "̒",
    "\\ocommatopright": "̕",
    "\\droang": "̚",
    "\\wideutilde": "̰",
    "\\not": "̸",
    "\\Mu": "Μ",
    "\\Nu": "Ν",
    "\\Omicron": "Ο",
    "\\omicron": "ο",
    "\\varbeta": "ϐ",
    "\\oldKoppa": "Ϙ",
    "\\oldkoppa": "ϙ",
    "\\stigma": "ϛ",
    "\\koppa": "ϟ",
    "\\sampi": "ϡ",
    "\\tieconcat": "⁀",
    "\\leftharpoonaccent": "⃐",
    "\\rightharpoonaccent": "⃑",
    "\\vertoverlay": "⃒",
    "\\overleftarrow": "⃖",
    "\\vec": "⃗",
    "\\overleftrightarrow": "⃡",
    "\\annuity": "⃧",
    "\\threeunderdot": "⃨",
    "\\widebridgeabove": "⃩",
    "\\bbC": "ℂ",
    "\\eulermascheroni": "ℇ",
    "\\scrg": "ℊ",
    "\\scrH": "ℋ",
    "\\frakH": "ℌ",
    "\\bbH": "ℍ",
    "\\planck": "ℎ",
    "\\scrI": "ℐ",
    "\\scrL": "ℒ",
    "\\bbN": "ℕ",
    "\\bbP": "ℙ",
    "\\bbQ": "ℚ",
    "\\scrR": "ℛ",
    "\\bbR": "ℝ",
    "\\bbZ": "ℤ",
    "\\frakZ": "ℨ",
    "\\Angstrom": "Å",
    "\\scrB": "ℬ",
    "\\frakC": "ℭ",
    "\\scre": "ℯ",
    "\\scrE": "ℰ",
    "\\scrF": "ℱ",
    "\\Finv": "Ⅎ",
    "\\scrM": "ℳ",
    "\\scro": "ℴ",
    "\\bbgamma": "ℽ",
    "\\bbGamma": "ℾ",
    "\\bbiD": "ⅅ",
    "\\bbid": "ⅆ",
    "\\bbie": "ⅇ",
    "\\bbii": "ⅈ",
    "\\bbij": "ⅉ",
    "\\bfA": "𝐀",
    "\\bfB": "𝐁",
    "\\bfC": "𝐂",
    "\\bfD": "𝐃",
    "\\bfE": "𝐄",
    "\\bfF": "𝐅",
    "\\bfG": "𝐆",
    "\\bfH": "𝐇",
    "\\bfI": "𝐈",
    "\\bfJ": "𝐉",
    "\\bfK": "𝐊",
    "\\bfL": "𝐋",
    "\\bfM": "𝐌",
    "\\bfN": "𝐍",
    "\\bfO": "𝐎",
    "\\bfP": "𝐏",
    "\\bfQ": "𝐐",
    "\\bfR": "𝐑",
    "\\bfS": "𝐒",
    "\\bfT": "𝐓",
    "\\bfU": "𝐔",
    "\\bfV": "𝐕",
    "\\bfW": "𝐖",
    "\\bfX": "𝐗",
    "\\bfY": "𝐘",
    "\\bfZ": "𝐙",
    "\\bfa": "𝐚",
    "\\bfb": "𝐛",
    "\\bfc": "𝐜",
    "\\bfd": "𝐝",
    "\\bfe": "𝐞",
    "\\bff": "𝐟",
    "\\bfg": "𝐠",
    "\\bfh": "𝐡",
    "\\bfi": "𝐢",
    "\\bfj": "𝐣",
    "\\bfk": "𝐤",
    "\\bfl": "𝐥",
    "\\bfm": "𝐦",
    "\\bfn": "𝐧",
    "\\bfo": "𝐨",
    "\\bfp": "𝐩",
    "\\bfq": "𝐪",
    "\\bfr": "𝐫",
    "\\bfs": "𝐬",
    "\\bft": "𝐭",
    "\\bfu": "𝐮",
    "\\bfv": "𝐯",
    "\\bfw": "𝐰",
    "\\bfx": "𝐱",
    "\\bfy": "𝐲",
    "\\bfz": "𝐳",
    "\\itA": "𝐴",
    "\\itB": "𝐵",
    "\\itC": "𝐶",
    "\\itD": "𝐷",
    "\\itE": "𝐸",
    "\\itF": "𝐹",
    "\\itG": "𝐺",
    "\\itH": "𝐻",
    "\\itI": "𝐼",
    "\\itJ": "𝐽",
    "\\itK": "𝐾",
    "\\itL": "𝐿",
    "\\itM": "𝑀",
    "\\itN": "𝑁",
    "\\itO": "𝑂",
    "\\itP": "𝑃",
    "\\itQ": "𝑄",
    "\\itR": "𝑅",
    "\\itS": "𝑆",
    "\\itT": "𝑇",
    "\\itU": "𝑈",
    "\\itV": "𝑉",
    "\\itW": "𝑊",
    "\\itX": "𝑋",
    "\\itY": "𝑌",
    "\\itZ": "𝑍",
    "\\ita": "𝑎",
    "\\itb": "𝑏",
    "\\itc": "𝑐",
    "\\itd": "𝑑",
    "\\ite": "𝑒",
    "\\itf": "𝑓",
    "\\itg": "𝑔",
    "\\ith": "ℎ",
    "\\iti": "𝑖",
    "\\itj": "𝑗",
    "\\itk": "𝑘",
    "\\itl": "𝑙",
    "\\itm": "𝑚",
    "\\itn": "𝑛",
    "\\ito": "𝑜",
    "\\itp": "𝑝",
    "\\itq": "𝑞",
    "\\itr": "𝑟",
    "\\its": "𝑠",
    "\\itt": "𝑡",
    "\\itu": "𝑢",
    "\\itv": "𝑣",
    "\\itw": "𝑤",
    "\\itx": "𝑥",
    "\\ity": "𝑦",
    "\\itz": "𝑧",
    "\\biA": "𝑨",
    "\\biB": "𝑩",
    "\\biC": "𝑪",
    "\\biD": "𝑫",
    "\\biE": "𝑬",
    "\\biF": "𝑭",
    "\\biG": "𝑮",
    "\\biH": "𝑯",
    "\\biI": "𝑰",
    "\\biJ": "𝑱",
    "\\biK": "𝑲",
    "\\biL": "𝑳",
    "\\biM": "𝑴",
    "\\biN": "𝑵",
    "\\biO": "𝑶",
    "\\biP": "𝑷",
    "\\biQ": "𝑸",
    "\\biR": "𝑹",
    "\\biS": "𝑺",
    "\\biT": "𝑻",
    "\\biU": "𝑼",
    "\\biV": "𝑽",
    "\\biW": "𝑾",
    "\\biX": "𝑿",
    "\\biY": "𝒀",
    "\\biZ": "𝒁",
    "\\bia": "𝒂",
    "\\bib": "𝒃",
    "\\bic": "𝒄",
    "\\bid": "𝒅",
    "\\bie": "𝒆",
    "\\bif": "𝒇",
    "\\big": "𝒈",
    "\\bih": "𝒉",
    "\\bii": "𝒊",
    "\\bij": "𝒋",
    "\\bik": "𝒌",
    "\\bil": "𝒍",
    "\\bim": "𝒎",
    "\\bin": "𝒏",
    "\\bio": "𝒐",
    "\\bip": "𝒑",
    "\\biq": "𝒒",
    "\\bir": "𝒓",
    "\\bis": "𝒔",
    "\\bit": "𝒕",
    "\\biu": "𝒖",
    "\\biv": "𝒗",
    "\\biw": "𝒘",
    "\\bix": "𝒙",
    "\\biy": "𝒚",
    "\\biz": "𝒛",
    "\\scrA": "𝒜",
    "\\scrC": "𝒞",
    "\\scrD": "𝒟",
    "\\scrG": "𝒢",
    "\\scrJ": "𝒥",
    "\\scrK": "𝒦",
    "\\scrN": "𝒩",
    "\\scrO": "𝒪",
    "\\scrP": "𝒫",
    "\\scrQ": "𝒬",
    "\\scrS": "𝒮",
    "\\scrT": "𝒯",
    "\\scrU": "𝒰",
    "\\scrV": "𝒱",
    "\\scrW": "𝒲",
    "\\scrX": "𝒳",
    "\\scrY": "𝒴",
    "\\scrZ": "𝒵",
    "\\scra": "𝒶",
    "\\scrb": "𝒷",
    "\\scrc": "𝒸",
    "\\scrd": "𝒹",
    "\\scrf": "𝒻",
    "\\scrh": "𝒽",
    "\\scri": "𝒾",
    "\\scrj": "𝒿",
    "\\scrk": "𝓀",
    "\\scrm": "𝓂",
    "\\scrn": "𝓃",
    "\\scrp": "𝓅",
    "\\scrq": "𝓆",
    "\\scrr": "𝓇",
    "\\scrs": "𝓈",
    "\\scrt": "𝓉",
    "\\scru": "𝓊",
    "\\scrv": "𝓋",
    "\\scrw": "𝓌",
    "\\scrx": "𝓍",
    "\\scry": "𝓎",
    "\\scrz": "𝓏",
    "\\bscrA": "𝓐",
    "\\bscrB": "𝓑",
    "\\bscrC": "𝓒",
    "\\bscrD": "𝓓",
    "\\bscrE": "𝓔",
    "\\bscrF": "𝓕",
    "\\bscrG": "𝓖",
    "\\bscrH": "𝓗",
    "\\bscrI": "𝓘",
    "\\bscrJ": "𝓙",
    "\\bscrK": "𝓚",
    "\\bscrL": "𝓛",
    "\\bscrM": "𝓜",
    "\\bscrN": "𝓝",
    "\\bscrO": "𝓞",
    "\\bscrP": "𝓟",
    "\\bscrQ": "𝓠",
    "\\bscrR": "𝓡",
    "\\bscrS": "𝓢",
    "\\bscrT": "𝓣",
    "\\bscrU": "𝓤",
    "\\bscrV": "𝓥",
    "\\bscrW": "𝓦",
    "\\bscrX": "𝓧",
    "\\bscrY": "𝓨",
    "\\bscrZ": "𝓩",
    "\\bscra": "𝓪",
    "\\bscrb": "𝓫",
    "\\bscrc": "𝓬",
    "\\bscrd": "𝓭",
    "\\bscre": "𝓮",
    "\\bscrf": "𝓯",
    "\\bscrg": "𝓰",
    "\\bscrh": "𝓱",
    "\\bscri": "𝓲",
    "\\bscrj": "𝓳",
    "\\bscrk": "𝓴",
    "\\bscrl": "𝓵",
    "\\bscrm": "𝓶",
    "\\bscrn": "𝓷",
    "\\bscro": "𝓸",
    "\\bscrp": "𝓹",
    "\\bscrq": "𝓺",
    "\\bscrr": "𝓻",
    "\\bscrs": "𝓼",
    "\\bscrt": "𝓽",
    "\\bscru": "𝓾",
    "\\bscrv": "𝓿",
    "\\bscrw": "𝔀",
    "\\bscrx": "𝔁",
    "\\bscry": "𝔂",
    "\\bscrz": "𝔃",
    "\\frakA": "𝔄",
    "\\frakB": "𝔅",
    "\\frakD": "𝔇",
    "\\frakE": "𝔈",
    "\\frakF": "𝔉",
    "\\frakG": "𝔊",
    "\\frakI": "ℑ",
    "\\frakJ": "𝔍",
    "\\frakK": "𝔎",
    "\\frakL": "𝔏",
    "\\frakM": "𝔐",
    "\\frakN": "𝔑",
    "\\frakO": "𝔒",
    "\\frakP": "𝔓",
    "\\frakQ": "𝔔",
    "\\frakR": "ℜ",
    "\\frakS": "𝔖",
    "\\frakT": "𝔗",
    "\\frakU": "𝔘",
    "\\frakV": "𝔙",
    "\\frakW": "𝔚",
    "\\frakX": "𝔛",
    "\\frakY": "𝔜",
    "\\fraka": "𝔞",
    "\\frakb": "𝔟",
    "\\frakc": "𝔠",
    "\\frakd": "𝔡",
    "\\frake": "𝔢",
    "\\frakf": "𝔣",
    "\\frakg": "𝔤",
    "\\frakh": "𝔥",
    "\\fraki": "𝔦",
    "\\frakj": "𝔧",
    "\\frakk": "𝔨",
    "\\frakl": "𝔩",
    "\\frakm": "𝔪",
    "\\frakn": "𝔫",
    "\\frako": "𝔬",
    "\\frakp": "𝔭",
    "\\frakq": "𝔮",
    "\\frakr": "𝔯",
    "\\fraks": "𝔰",
    "\\frakt": "𝔱",
    "\\fraku": "𝔲",
    "\\frakv": "𝔳",
    "\\frakw": "𝔴",
    "\\frakx": "𝔵",
    "\\fraky": "𝔶",
    "\\frakz": "𝔷",
    "\\bbA": "𝔸",
    "\\bbB": "𝔹",
    "\\bbD": "𝔻",
    "\\bbE": "𝔼",
    "\\bbF": "𝔽",
    "\\bbG": "𝔾",
    "\\bbI": "𝕀",
    "\\bbJ": "𝕁",
    "\\bbK": "𝕂",
    "\\bbL": "𝕃",
    "\\bbM": "𝕄",
    "\\bbO": "𝕆",
    "\\bbS": "𝕊",
    "\\bbT": "𝕋",
    "\\bbU": "𝕌",
    "\\bbV": "𝕍",
    "\\bbW": "𝕎",
    "\\bbX": "𝕏",
    "\\bbY": "𝕐",
    "\\bba": "𝕒",
    "\\bbb": "𝕓",
    "\\bbc": "𝕔",
    "\\bbd": "𝕕",
    "\\bbe": "𝕖",
    "\\bbf": "𝕗",
    "\\bbg": "𝕘",
    "\\bbh": "𝕙",
    "\\bbi": "𝕚",
    "\\bbj": "𝕛",
    "\\bbk": "𝕜",
    "\\bbl": "𝕝",
    "\\bbm": "𝕞",
    "\\bbn": "𝕟",
    "\\bbo": "𝕠",
    "\\bbp": "𝕡",
    "\\bbq": "𝕢",
    "\\bbr": "𝕣",
    "\\bbs": "𝕤",
    "\\bbt": "𝕥",
    "\\bbu": "𝕦",
    "\\bbv": "𝕧",
    "\\bbw": "𝕨",
    "\\bbx": "𝕩",
    "\\bby": "𝕪",
    "\\bbz": "𝕫",
    "\\bfrakA": "𝕬",
    "\\bfrakB": "𝕭",
    "\\bfrakC": "𝕮",
    "\\bfrakD": "𝕯",
    "\\bfrakE": "𝕰",
    "\\bfrakF": "𝕱",
    "\\bfrakG": "𝕲",
    "\\bfrakH": "𝕳",
    "\\bfrakI": "𝕴",
    "\\bfrakJ": "𝕵",
    "\\bfrakK": "𝕶",
    "\\bfrakL": "𝕷",
    "\\bfrakM": "𝕸",
    "\\bfrakN": "𝕹",
    "\\bfrakO": "𝕺",
    "\\bfrakP": "𝕻",
    "\\bfrakQ": "𝕼",
    "\\bfrakR": "𝕽",
    "\\bfrakS": "𝕾",
    "\\bfrakT": "𝕿",
    "\\bfrakU": "𝖀",
    "\\bfrakV": "𝖁",
    "\\bfrakW": "𝖂",
    "\\bfrakX": "𝖃",
    "\\bfrakY": "𝖄",
    "\\bfrakZ": "𝖅",
    "\\bfraka": "𝖆",
    "\\bfrakb": "𝖇",
    "\\bfrakc": "𝖈",
    "\\bfrakd": "𝖉",
    "\\bfrake": "𝖊",
    "\\bfrakf": "𝖋",
    "\\bfrakg": "𝖌",
    "\\bfrakh": "𝖍",
    "\\bfraki": "𝖎",
    "\\bfrakj": "𝖏",
    "\\bfrakk": "𝖐",
    "\\bfrakl": "𝖑",
    "\\bfrakm": "𝖒",
    "\\bfrakn": "𝖓",
    "\\bfrako": "𝖔",
    "\\bfrakp": "𝖕",
    "\\bfrakq": "𝖖",
    "\\bfrakr": "𝖗",
    "\\bfraks": "𝖘",
    "\\bfrakt": "𝖙",
    "\\bfraku": "𝖚",
    "\\bfrakv": "𝖛",
    "\\bfrakw": "𝖜",
    "\\bfrakx": "𝖝",
    "\\bfraky": "𝖞",
    "\\bfrakz": "𝖟",
    "\\sansA": "𝖠",
    "\\sansB": "𝖡",
    "\\sansC": "𝖢",
    "\\sansD": "𝖣",
    "\\sansE": "𝖤",
    "\\sansF": "𝖥",
    "\\sansG": "𝖦",
    "\\sansH": "𝖧",
    "\\sansI": "𝖨",
    "\\sansJ": "𝖩",
    "\\sansK": "𝖪",
    "\\sansL": "𝖫",
    "\\sansM": "𝖬",
    "\\sansN": "𝖭",
    "\\sansO": "𝖮",
    "\\sansP": "𝖯",
    "\\sansQ": "𝖰",
    "\\sansR": "𝖱",
    "\\sansS": "𝖲",
    "\\sansT": "𝖳",
    "\\sansU": "𝖴",
    "\\sansV": "𝖵",
    "\\sansW": "𝖶",
    "\\sansX": "𝖷",
    "\\sansY": "𝖸",
    "\\sansZ": "𝖹",
    "\\sansa": "𝖺",
    "\\sansb": "𝖻",
    "\\sansc": "𝖼",
    "\\sansd": "𝖽",
    "\\sanse": "𝖾",
    "\\sansf": "𝖿",
    "\\sansg": "𝗀",
    "\\sansh": "𝗁",
    "\\sansi": "𝗂",
    "\\sansj": "𝗃",
    "\\sansk": "𝗄",
    "\\sansl": "𝗅",
    "\\sansm": "𝗆",
    "\\sansn": "𝗇",
    "\\sanso": "𝗈",
    "\\sansp": "𝗉",
    "\\sansq": "𝗊",
    "\\sansr": "𝗋",
    "\\sanss": "𝗌",
    "\\sanst": "𝗍",
    "\\sansu": "𝗎",
    "\\sansv": "𝗏",
    "\\sansw": "𝗐",
    "\\sansx": "𝗑",
    "\\sansy": "𝗒",
    "\\sansz": "𝗓",
    "\\bsansA": "𝗔",
    "\\bsansB": "𝗕",
    "\\bsansC": "𝗖",
    "\\bsansD": "𝗗",
    "\\bsansE": "𝗘",
    "\\bsansF": "𝗙",
    "\\bsansG": "𝗚",
    "\\bsansH": "𝗛",
    "\\bsansI": "𝗜",
    "\\bsansJ": "𝗝",
    "\\bsansK": "𝗞",
    "\\bsansL": "𝗟",
    "\\bsansM": "𝗠",
    "\\bsansN": "𝗡",
    "\\bsansO": "𝗢",
    "\\bsansP": "𝗣",
    "\\bsansQ": "𝗤",
    "\\bsansR": "𝗥",
    "\\bsansS": "𝗦",
    "\\bsansT": "𝗧",
    "\\bsansU": "𝗨",
    "\\bsansV": "𝗩",
    "\\bsansW": "𝗪",
    "\\bsansX": "𝗫",
    "\\bsansY": "𝗬",
    "\\bsansZ": "𝗭",
    "\\bsansa": "𝗮",
    "\\bsansb": "𝗯",
    "\\bsansc": "𝗰",
    "\\bsansd": "𝗱",
    "\\bsanse": "𝗲",
    "\\bsansf": "𝗳",
    "\\bsansg": "𝗴",
    "\\bsansh": "𝗵",
    "\\bsansi": "𝗶",
    "\\bsansj": "𝗷",
    "\\bsansk": "𝗸",
    "\\bsansl": "𝗹",
    "\\bsansm": "𝗺",
    "\\bsansn": "𝗻",
    "\\bsanso": "𝗼",
    "\\bsansp": "𝗽",
    "\\bsansq": "𝗾",
    "\\bsansr": "𝗿",
    "\\bsanss": "𝘀",
    "\\bsanst": "𝘁",
    "\\bsansu": "𝘂",
    "\\bsansv": "𝘃",
    "\\bsansw": "𝘄",
    "\\bsansx": "𝘅",
    "\\bsansy": "𝘆",
    "\\bsansz": "𝘇",
    "\\isansA": "𝘈",
    "\\isansB": "𝘉",
    "\\isansC": "𝘊",
    "\\isansD": "𝘋",
    "\\isansE": "𝘌",
    "\\isansF": "𝘍",
    "\\isansG": "𝘎",
    "\\isansH": "𝘏",
    "\\isansI": "𝘐",
    "\\isansJ": "𝘑",
    "\\isansK": "𝘒",
    "\\isansL": "𝘓",
    "\\isansM": "𝘔",
    "\\isansN": "𝘕",
    "\\isansO": "𝘖",
    "\\isansP": "𝘗",
    "\\isansQ": "𝘘",
    "\\isansR": "𝘙",
    "\\isansS": "𝘚",
    "\\isansT": "𝘛",
    "\\isansU": "𝘜",
    "\\isansV": "𝘝",
    "\\isansW": "𝘞",
    "\\isansX": "𝘟",
    "\\isansY": "𝘠",
    "\\isansZ": "𝘡",
    "\\isansa": "𝘢",
    "\\isansb": "𝘣",
    "\\isansc": "𝘤",
    "\\isansd": "𝘥",
    "\\isanse": "𝘦",
    "\\isansf": "𝘧",
    "\\isansg": "𝘨",
    "\\isansh": "𝘩",
    "\\isansi": "𝘪",
    "\\isansj": "𝘫",
    "\\isansk": "𝘬",
    "\\isansl": "𝘭",
    "\\isansm": "𝘮",
    "\\isansn": "𝘯",
    "\\isanso": "𝘰",
    "\\isansp": "𝘱",
    "\\isansq": "𝘲",
    "\\isansr": "𝘳",
    "\\isanss": "𝘴",
    "\\isanst": "𝘵",
    "\\isansu": "𝘶",
    "\\isansv": "𝘷",
    "\\isansw": "𝘸",
    "\\isansx": "𝘹",
    "\\isansy": "𝘺",
    "\\isansz": "𝘻",
    "\\bisansA": "𝘼",
    "\\bisansB": "𝘽",
    "\\bisansC": "𝘾",
    "\\bisansD": "𝘿",
    "\\bisansE": "𝙀",
    "\\bisansF": "𝙁",
    "\\bisansG": "𝙂",
    "\\bisansH": "𝙃",
    "\\bisansI": "𝙄",
    "\\bisansJ": "𝙅",
    "\\bisansK": "𝙆",
    "\\bisansL": "𝙇",
    "\\bisansM": "𝙈",
    "\\bisansN": "𝙉",
    "\\bisansO": "𝙊",
    "\\bisansP": "𝙋",
    "\\bisansQ": "𝙌",
    "\\bisansR": "𝙍",
    "\\bisansS": "𝙎",
    "\\bisansT": "𝙏",
    "\\bisansU": "𝙐",
    "\\bisansV": "𝙑",
    "\\bisansW": "𝙒",
    "\\bisansX": "𝙓",
    "\\bisansY": "𝙔",
    "\\bisansZ": "𝙕",
    "\\bisansa": "𝙖",
    "\\bisansb": "𝙗",
    "\\bisansc": "𝙘",
    "\\bisansd": "𝙙",
    "\\bisanse": "𝙚",
    "\\bisansf": "𝙛",
    "\\bisansg": "𝙜",
    "\\bisansh": "𝙝",
    "\\bisansi": "𝙞",
    "\\bisansj": "𝙟",
    "\\bisansk": "𝙠",
    "\\bisansl": "𝙡",
    "\\bisansm": "𝙢",
    "\\bisansn": "𝙣",
    "\\bisanso": "𝙤",
    "\\bisansp": "𝙥",
    "\\bisansq": "𝙦",
    "\\bisansr": "𝙧",
    "\\bisanss": "𝙨",
    "\\bisanst": "𝙩",
    "\\bisansu": "𝙪",
    "\\bisansv": "𝙫",
    "\\bisansw": "𝙬",
    "\\bisansx": "𝙭",
    "\\bisansy": "𝙮",
    "\\bisansz": "𝙯",
    "\\ttA": "𝙰",
    "\\ttB": "𝙱",
    "\\ttC": "𝙲",
    "\\ttD": "𝙳",
    "\\ttE": "𝙴",
    "\\ttF": "𝙵",
    "\\ttG": "𝙶",
    "\\ttH": "𝙷",
    "\\ttI": "𝙸",
    "\\ttJ": "𝙹",
    "\\ttK": "𝙺",
    "\\ttL": "𝙻",
    "\\ttM": "𝙼",
    "\\ttN": "𝙽",
    "\\ttO": "𝙾",
    "\\ttP": "𝙿",
    "\\ttQ": "𝚀",
    "\\ttR": "𝚁",
    "\\ttS": "𝚂",
    "\\ttT": "𝚃",
    "\\ttU": "𝚄",
    "\\ttV": "𝚅",
    "\\ttW": "𝚆",
    "\\ttX": "𝚇",
    "\\ttY": "𝚈",
    "\\ttZ": "𝚉",
    "\\tta": "𝚊",
    "\\ttb": "𝚋",
    "\\ttc": "𝚌",
    "\\ttd": "𝚍",
    "\\tte": "𝚎",
    "\\ttf": "𝚏",
    "\\ttg": "𝚐",
    "\\tth": "𝚑",
    "\\tti": "𝚒",
    "\\ttj": "𝚓",
    "\\ttk": "𝚔",
    "\\ttl": "𝚕",
    "\\ttm": "𝚖",
    "\\ttn": "𝚗",
    "\\tto": "𝚘",
    "\\ttp": "𝚙",
    "\\ttq": "𝚚",
    "\\ttr": "𝚛",
    "\\tts": "𝚜",
    "\\ttt": "𝚝",
    "\\ttu": "𝚞",
    "\\ttv": "𝚟",
    "\\ttw": "𝚠",
    "\\ttx": "𝚡",
    "\\tty": "𝚢",
    "\\ttz": "𝚣",
    "\\bfAlpha": "𝚨",
    "\\bfBeta": "𝚩",
    "\\bfGamma": "𝚪",
    "\\bfDelta": "𝚫",
    "\\bfEpsilon": "𝚬",
    "\\bfZeta": "𝚭",
    "\\bfEta": "𝚮",
    "\\bfTheta": "𝚯",
    "\\bfIota": "𝚰",
    "\\bfKappa": "𝚱",
    "\\bfLambda": "𝚲",
    "\\bfMu": "𝚳",
    "\\bfNu": "𝚴",
    "\\bfXi": "𝚵",
    "\\bfOmicron": "𝚶",
    "\\bfPi": "𝚷",
    "\\bfRho": "𝚸",
    "\\bfvarTheta": "𝚹",
    "\\bfSigma": "𝚺",
    "\\bfTau": "𝚻",
    "\\bfUpsilon": "𝚼",
    "\\bfPhi": "𝚽",
    "\\bfChi": "𝚾",
    "\\bfPsi": "𝚿",
    "\\bfOmega": "𝛀",
    "\\bfalpha": "𝛂",
    "\\bfbeta": "𝛃",
    "\\bfgamma": "𝛄",
    "\\bfdelta": "𝛅",
    "\\bfvarepsilon": "𝛆",
    "\\bfzeta": "𝛇",
    "\\bfeta": "𝛈",
    "\\bftheta": "𝛉",
    "\\bfiota": "𝛊",
    "\\bfkappa": "𝛋",
    "\\bflambda": "𝛌",
    "\\bfmu": "𝛍",
    "\\bfnu": "𝛎",
    "\\bfxi": "𝛏",
    "\\bfomicron": "𝛐",
    "\\bfpi": "𝛑",
    "\\bfrho": "𝛒",
    "\\bfvarsigma": "𝛓",
    "\\bfsigma": "𝛔",
    "\\bftau": "𝛕",
    "\\bfupsilon": "𝛖",
    "\\bfvarphi": "𝛗",
    "\\bfchi": "𝛘",
    "\\bfpsi": "𝛙",
    "\\bfomega": "𝛚",
    "\\bfepsilon": "𝛜",
    "\\bfvartheta": "𝛝",
    "\\bfvarkappa": "𝛞",
    "\\bfphi": "𝛟",
    "\\bfvarrho": "𝛠",
    "\\bfvarpi": "𝛡",
    "\\itAlpha": "𝛢",
    "\\itBeta": "𝛣",
    "\\itGamma": "𝛤",
    "\\itDelta": "𝛥",
    "\\itEpsilon": "𝛦",
    "\\itZeta": "𝛧",
    "\\itEta": "𝛨",
    "\\itTheta": "𝛩",
    "\\itIota": "𝛪",
    "\\itKappa": "𝛫",
    "\\itLambda": "𝛬",
    "\\itMu": "𝛭",
    "\\itNu": "𝛮",
    "\\itXi": "𝛯",
    "\\itOmicron": "𝛰",
    "\\itPi": "𝛱",
    "\\itRho": "𝛲",
    "\\itvarTheta": "𝛳",
    "\\itSigma": "𝛴",
    "\\itTau": "𝛵",
    "\\itUpsilon": "𝛶",
    "\\itPhi": "𝛷",
    "\\itChi": "𝛸",
    "\\itPsi": "𝛹",
    "\\itOmega": "𝛺",
    "\\italpha": "𝛼",
    "\\itbeta": "𝛽",
    "\\itgamma": "𝛾",
    "\\itdelta": "𝛿",
    "\\itvarepsilon": "𝜀",
    "\\itzeta": "𝜁",
    "\\iteta": "𝜂",
    "\\ittheta": "𝜃",
    "\\itiota": "𝜄",
    "\\itkappa": "𝜅",
    "\\itlambda": "𝜆",
    "\\itmu": "𝜇",
    "\\itnu": "𝜈",
    "\\itxi": "𝜉",
    "\\itomicron": "𝜊",
    "\\itpi": "𝜋",
    "\\itrho": "𝜌",
    "\\itvarsigma": "𝜍",
    "\\itsigma": "𝜎",
    "\\ittau": "𝜏",
    "\\itupsilon": "𝜐",
    "\\itvarphi": "𝜑",
    "\\itchi": "𝜒",
    "\\itpsi": "𝜓",
    "\\itomega": "𝜔",
    "\\itepsilon": "𝜖",
    "\\itvartheta": "𝜗",
    "\\itvarkappa": "𝜘",
    "\\itphi": "𝜙",
    "\\itvarrho": "𝜚",
    "\\itvarpi": "𝜛",
    "\\biAlpha": "𝜜",
    "\\biBeta": "𝜝",
    "\\biGamma": "𝜞",
    "\\biDelta": "𝜟",
    "\\biEpsilon": "𝜠",
    "\\biZeta": "𝜡",
    "\\biEta": "𝜢",
    "\\biTheta": "𝜣",
    "\\biIota": "𝜤",
    "\\biKappa": "𝜥",
    "\\biLambda": "𝜦",
    "\\biMu": "𝜧",
    "\\biNu": "𝜨",
    "\\biXi": "𝜩",
    "\\biOmicron": "𝜪",
    "\\biPi": "𝜫",
    "\\biRho": "𝜬",
    "\\bivarTheta": "𝜭",
    "\\biSigma": "𝜮",
    "\\biTau": "𝜯",
    "\\biUpsilon": "𝜰",
    "\\biPhi": "𝜱",
    "\\biChi": "𝜲",
    "\\biPsi": "𝜳",
    "\\biOmega": "𝜴",
    "\\bialpha": "𝜶",
    "\\bibeta": "𝜷",
    "\\bigamma": "𝜸",
    "\\bidelta": "𝜹",
    "\\bivarepsilon": "𝜺",
    "\\bizeta": "𝜻",
    "\\bieta": "𝜼",
    "\\bitheta": "𝜽",
    "\\biiota": "𝜾",
    "\\bikappa": "𝜿",
    "\\bilambda": "𝝀",
    "\\bimu": "𝝁",
    "\\binu": "𝝂",
    "\\bixi": "𝝃",
    "\\biomicron": "𝝄",
    "\\bipi": "𝝅",
    "\\birho": "𝝆",
    "\\bivarsigma": "𝝇",
    "\\bisigma": "𝝈",
    "\\bitau": "𝝉",
    "\\biupsilon": "𝝊",
    "\\bivarphi": "𝝋",
    "\\bichi": "𝝌",
    "\\bipsi": "𝝍",
    "\\biomega": "𝝎",
    "\\biepsilon": "𝝐",
    "\\bivartheta": "𝝑",
    "\\bivarkappa": "𝝒",
    "\\biphi": "𝝓",
    "\\bivarrho": "𝝔",
    "\\bivarpi": "𝝕",
    "\\bsansAlpha": "𝝖",
    "\\bsansBeta": "𝝗",
    "\\bsansGamma": "𝝘",
    "\\bsansDelta": "𝝙",
    "\\bsansEpsilon": "𝝚",
    "\\bsansZeta": "𝝛",
    "\\bsansEta": "𝝜",
    "\\bsansTheta": "𝝝",
    "\\bsansIota": "𝝞",
    "\\bsansKappa": "𝝟",
    "\\bsansLambda": "𝝠",
    "\\bsansMu": "𝝡",
    "\\bsansNu": "𝝢",
    "\\bsansXi": "𝝣",
    "\\bsansOmicron": "𝝤",
    "\\bsansPi": "𝝥",
    "\\bsansRho": "𝝦",
    "\\bsansvarTheta": "𝝧",
    "\\bsansSigma": "𝝨",
    "\\bsansTau": "𝝩",
    "\\bsansUpsilon": "𝝪",
    "\\bsansPhi": "𝝫",
    "\\bsansChi": "𝝬",
    "\\bsansPsi": "𝝭",
    "\\bsansOmega": "𝝮",
    "\\bsansalpha": "𝝰",
    "\\bsansbeta": "𝝱",
    "\\bsansgamma": "𝝲",
    "\\bsansdelta": "𝝳",
    "\\bsansvarepsilon": "𝝴",
    "\\bsanszeta": "𝝵",
    "\\bsanseta": "𝝶",
    "\\bsanstheta": "𝝷",
    "\\bsansiota": "𝝸",
    "\\bsanskappa": "𝝹",
    "\\bsanslambda": "𝝺",
    "\\bsansmu": "𝝻",
    "\\bsansnu": "𝝼",
    "\\bsansxi": "𝝽",
    "\\bsansomicron": "𝝾",
    "\\bsanspi": "𝝿",
    "\\bsansrho": "𝞀",
    "\\bsansvarsigma": "𝞁",
    "\\bsanssigma": "𝞂",
    "\\bsanstau": "𝞃",
    "\\bsansupsilon": "𝞄",
    "\\bsansvarphi": "𝞅",
    "\\bsanschi": "𝞆",
    "\\bsanspsi": "𝞇",
    "\\bsansomega": "𝞈",
    "\\bsansepsilon": "𝞊",
    "\\bsansvartheta": "𝞋",
    "\\bsansvarkappa": "𝞌",
    "\\bsansphi": "𝞍",
    "\\bsansvarrho": "𝞎",
    "\\bsansvarpi": "𝞏",
    "\\bisansAlpha": "𝞐",
    "\\bisansBeta": "𝞑",
    "\\bisansGamma": "𝞒",
    "\\bisansDelta": "𝞓",
    "\\bisansEpsilon": "𝞔",
    "\\bisansZeta": "𝞕",
    "\\bisansEta": "𝞖",
    "\\bisansTheta": "𝞗",
    "\\bisansIota": "𝞘",
    "\\bisansKappa": "𝞙",
    "\\bisansLambda": "𝞚",
    "\\bisansMu": "𝞛",
    "\\bisansNu": "𝞜",
    "\\bisansXi": "𝞝",
    "\\bisansOmicron": "𝞞",
    "\\bisansPi": "𝞟",
    "\\bisansRho": "𝞠",
    "\\bisansvarTheta": "𝞡",
    "\\bisansSigma": "𝞢",
    "\\bisansTau": "𝞣",
    "\\bisansUpsilon": "𝞤",
    "\\bisansPhi": "𝞥",
    "\\bisansChi": "𝞦",
    "\\bisansPsi": "𝞧",
    "\\bisansOmega": "𝞨",
    "\\bisansalpha": "𝞪",
    "\\bisansbeta": "𝞫",
    "\\bisansgamma": "𝞬",
    "\\bisansdelta": "𝞭",
    "\\bisansvarepsilon": "𝞮",
    "\\bisanszeta": "𝞯",
    "\\bisanseta": "𝞰",
    "\\bisanstheta": "𝞱",
    "\\bisansiota": "𝞲",
    "\\bisanskappa": "𝞳",
    "\\bisanslambda": "𝞴",
    "\\bisansmu": "𝞵",
    "\\bisansnu": "𝞶",
    "\\bisansxi": "𝞷",
    "\\bisansomicron": "𝞸",
    "\\bisanspi": "𝞹",
    "\\bisansrho": "𝞺",
    "\\bisansvarsigma": "𝞻",
    "\\bisanssigma": "𝞼",
    "\\bisanstau": "𝞽",
    "\\bisansupsilon": "𝞾",
    "\\bisansvarphi": "𝞿",
    "\\bisanschi": "𝟀",
    "\\bisanspsi": "𝟁",
    "\\bisansomega": "𝟂",
    "\\bisansepsilon": "𝟄",
    "\\bisansvartheta": "𝟅",
    "\\bisansvarkappa": "𝟆",
    "\\bisansphi": "𝟇",
    "\\bisansvarrho": "𝟈",
    "\\bisansvarpi": "𝟉",
    "\\bfzero": "𝟎",
    "\\bfone": "𝟏",
    "\\bftwo": "𝟐",
    "\\bfthree": "𝟑",
    "\\bffour": "𝟒",
    "\\bffive": "𝟓",
    "\\bfsix": "𝟔",
    "\\bfseven": "𝟕",
    "\\bfeight": "𝟖",
    "\\bfnine": "𝟗",
    "\\bbzero": "𝟘",
    "\\bbone": "𝟙",
    "\\bbtwo": "𝟚",
    "\\bbthree": "𝟛",
    "\\bbfour": "𝟜",
    "\\bbfive": "𝟝",
    "\\bbsix": "𝟞",
    "\\bbseven": "𝟟",
    "\\bbeight": "𝟠",
    "\\bbnine": "𝟡",
    "\\sanszero": "𝟢",
    "\\sansone": "𝟣",
    "\\sanstwo": "𝟤",
    "\\sansthree": "𝟥",
    "\\sansfour": "𝟦",
    "\\sansfive": "𝟧",
    "\\sanssix": "𝟨",
    "\\sansseven": "𝟩",
    "\\sanseight": "𝟪",
    "\\sansnine": "𝟫",
    "\\bsanszero": "𝟬",
    "\\bsansone": "𝟭",
    "\\bsanstwo": "𝟮",
    "\\bsansthree": "𝟯",
    "\\bsansfour": "𝟰",
    "\\bsansfive": "𝟱",
    "\\bsanssix": "𝟲",
    "\\bsansseven": "𝟳",
    "\\bsanseight": "𝟴",
    "\\bsansnine": "𝟵",
    "\\ttzero": "𝟶",
    "\\ttone": "𝟷",
    "\\tttwo": "𝟸",
    "\\ttthree": "𝟹",
    "\\ttfour": "𝟺",
    "\\ttfive": "𝟻",
    "\\ttsix": "𝟼",
    "\\ttseven": "𝟽",
    "\\tteight": "𝟾",
    "\\ttnine": "𝟿",
    "\\underbar": "̲",
    "\\underleftrightarrow": "͍",
}


reverse_latex_symbol = {v: k for k, v in latex_symbols.items()}

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\reference.py ===
import base64
import collections
import io
import itertools
import logging
import math
import os
from functools import lru_cache
from itertools import chain
from typing import TYPE_CHECKING, Literal

import fsspec.core
from fsspec.spec import AbstractBufferedFile

try:
    import ujson as json
except ImportError:
    if not TYPE_CHECKING:
        import json

from fsspec.asyn import AsyncFileSystem
from fsspec.callbacks import DEFAULT_CALLBACK
from fsspec.core import filesystem, open, split_protocol
from fsspec.implementations.asyn_wrapper import AsyncFileSystemWrapper
from fsspec.utils import isfilelike, merge_offset_ranges, other_paths

logger = logging.getLogger("fsspec.reference")


class ReferenceNotReachable(RuntimeError):
    def __init__(self, reference, target, *args):
        super().__init__(*args)
        self.reference = reference
        self.target = target

    def __str__(self):
        return f'Reference "{self.reference}" failed to fetch target {self.target}'


def _first(d):
    return next(iter(d.values()))


def _prot_in_references(path, references):
    ref = references.get(path)
    if isinstance(ref, (list, tuple)) and isinstance(ref[0], str):
        return split_protocol(ref[0])[0] if ref[0] else ref[0]


def _protocol_groups(paths, references):
    if isinstance(paths, str):
        return {_prot_in_references(paths, references): [paths]}
    out = {}
    for path in paths:
        protocol = _prot_in_references(path, references)
        out.setdefault(protocol, []).append(path)
    return out


class RefsValuesView(collections.abc.ValuesView):
    def __iter__(self):
        for val in self._mapping.zmetadata.values():
            yield json.dumps(val).encode()
        yield from self._mapping._items.values()
        for field in self._mapping.listdir():
            chunk_sizes = self._mapping._get_chunk_sizes(field)
            if len(chunk_sizes) == 0:
                yield self._mapping[field + "/0"]
                continue
            yield from self._mapping._generate_all_records(field)


class RefsItemsView(collections.abc.ItemsView):
    def __iter__(self):
        return zip(self._mapping.keys(), self._mapping.values())


def ravel_multi_index(idx, sizes):
    val = 0
    mult = 1
    for i, s in zip(idx[::-1], sizes[::-1]):
        val += i * mult
        mult *= s
    return val


class LazyReferenceMapper(collections.abc.MutableMapping):
    """This interface can be used to read/write references from Parquet stores.
    It is not intended for other types of references.
    It can be used with Kerchunk's MultiZarrToZarr method to combine
    references into a parquet store.
    Examples of this use-case can be found here:
    https://fsspec.github.io/kerchunk/advanced.html?highlight=parquet#parquet-storage"""

    # import is class level to prevent numpy dep requirement for fsspec
    @property
    def np(self):
        import numpy as np

        return np

    @property
    def pd(self):
        import pandas as pd

        return pd

    def __init__(
        self,
        root,
        fs=None,
        out_root=None,
        cache_size=128,
        categorical_threshold=10,
        engine: Literal["fastparquet", "pyarrow"] = "fastparquet",
    ):
        """

        This instance will be writable, storing changes in memory until full partitions
        are accumulated or .flush() is called.

        To create an empty lazy store, use .create()

        Parameters
        ----------
        root : str
            Root of parquet store
        fs : fsspec.AbstractFileSystem
            fsspec filesystem object, default is local filesystem.
        cache_size : int, default=128
            Maximum size of LRU cache, where cache_size*record_size denotes
            the total number of references that can be loaded in memory at once.
        categorical_threshold : int
            Encode urls as pandas.Categorical to reduce memory footprint if the ratio
            of the number of unique urls to total number of refs for each variable
            is greater than or equal to this number. (default 10)
        engine: Literal["fastparquet","pyarrow"]
            Engine choice for reading parquet files. (default is "fastparquet")
        """

        self.root = root
        self.chunk_sizes = {}
        self.cat_thresh = categorical_threshold
        self.engine = engine
        self.cache_size = cache_size
        self.url = self.root + "/{field}/refs.{record}.parq"
        # TODO: derive fs from `root`
        self.fs = fsspec.filesystem("file") if fs is None else fs
        self.out_root = self.fs.unstrip_protocol(out_root or self.root)

        from importlib.util import find_spec

        if self.engine == "pyarrow" and find_spec("pyarrow") is None:
            raise ImportError("engine choice `pyarrow` is not installed.")

    def __getattr__(self, item):
        if item in ("_items", "record_size", "zmetadata"):
            self.setup()
            # avoid possible recursion if setup fails somehow
            return self.__dict__[item]
        raise AttributeError(item)

    def setup(self):
        self._items = {}
        self._items[".zmetadata"] = self.fs.cat_file(
            "/".join([self.root, ".zmetadata"])
        )
        met = json.loads(self._items[".zmetadata"])
        self.record_size = met["record_size"]
        self.zmetadata = met["metadata"]

        # Define function to open and decompress refs
        @lru_cache(maxsize=self.cache_size)
        def open_refs(field, record):
            """cached parquet file loader"""
            path = self.url.format(field=field, record=record)
            data = io.BytesIO(self.fs.cat_file(path))
            try:
                df = self.pd.read_parquet(data, engine=self.engine)
                refs = {c: df[c].to_numpy() for c in df.columns}
            except OSError:
                refs = None
            return refs

        self.open_refs = open_refs

    @staticmethod
    def create(root, storage_options=None, fs=None, record_size=10000, **kwargs):
        """Make empty parquet reference set

        First deletes the contents of the given directory, if it exists.

        Parameters
        ----------
        root: str
            Directory to contain the output; will be created
        storage_options: dict | None
            For making the filesystem to use for writing is fs is None
        fs: FileSystem | None
            Filesystem for writing
        record_size: int
            Number of references per parquet file
        kwargs: passed to __init__

        Returns
        -------
        LazyReferenceMapper instance
        """
        met = {"metadata": {}, "record_size": record_size}
        if fs is None:
            fs, root = fsspec.core.url_to_fs(root, **(storage_options or {}))
        if fs.exists(root):
            fs.rm(root, recursive=True)
        fs.makedirs(root, exist_ok=True)
        fs.pipe("/".join([root, ".zmetadata"]), json.dumps(met).encode())
        return LazyReferenceMapper(root, fs, **kwargs)

    @lru_cache()
    def listdir(self):
        """List top-level directories"""
        dirs = (p.rsplit("/", 1)[0] for p in self.zmetadata if not p.startswith(".z"))
        return set(dirs)

    def ls(self, path="", detail=True):
        """Shortcut file listings"""
        path = path.rstrip("/")
        pathdash = path + "/" if path else ""
        dirnames = self.listdir()
        dirs = [
            d
            for d in dirnames
            if d.startswith(pathdash) and "/" not in d.lstrip(pathdash)
        ]
        if dirs:
            others = {
                f
                for f in chain(
                    [".zmetadata"],
                    (name for name in self.zmetadata),
                    (name for name in self._items),
                )
                if f.startswith(pathdash) and "/" not in f.lstrip(pathdash)
            }
            if detail is False:
                others.update(dirs)
                return sorted(others)
            dirinfo = [{"name": name, "type": "directory", "size": 0} for name in dirs]
            fileinfo = [
                {
                    "name": name,
                    "type": "file",
                    "size": len(
                        json.dumps(self.zmetadata[name])
                        if name in self.zmetadata
                        else self._items[name]
                    ),
                }
                for name in others
            ]
            return sorted(dirinfo + fileinfo, key=lambda s: s["name"])
        field = path
        others = set(
            [name for name in self.zmetadata if name.startswith(f"{path}/")]
            + [name for name in self._items if name.startswith(f"{path}/")]
        )
        fileinfo = [
            {
                "name": name,
                "type": "file",
                "size": len(
                    json.dumps(self.zmetadata[name])
                    if name in self.zmetadata
                    else self._items[name]
                ),
            }
            for name in others
        ]
        keys = self._keys_in_field(field)

        if detail is False:
            return list(others) + list(keys)
        recs = self._generate_all_records(field)
        recinfo = [
            {"name": name, "type": "file", "size": rec[-1]}
            for name, rec in zip(keys, recs)
            if rec[0]  # filters out path==None, deleted/missing
        ]
        return fileinfo + recinfo

    def _load_one_key(self, key):
        """Get the reference for one key

        Returns bytes, one-element list or three-element list.
        """
        if key in self._items:
            return self._items[key]
        elif key in self.zmetadata:
            return json.dumps(self.zmetadata[key]).encode()
        elif "/" not in key or self._is_meta(key):
            raise KeyError(key)
        field, _ = key.rsplit("/", 1)
        record, ri, chunk_size = self._key_to_record(key)
        maybe = self._items.get((field, record), {}).get(ri, False)
        if maybe is None:
            # explicitly deleted
            raise KeyError
        elif maybe:
            return maybe
        elif chunk_size == 0:
            return b""

        # Chunk keys can be loaded from row group and cached in LRU cache
        try:
            refs = self.open_refs(field, record)
        except (ValueError, TypeError, FileNotFoundError) as exc:
            raise KeyError(key) from exc
        columns = ["path", "offset", "size", "raw"]
        selection = [refs[c][ri] if c in refs else None for c in columns]
        raw = selection[-1]
        if raw is not None:
            return raw
        if selection[0] is None:
            raise KeyError("This reference does not exist or has been deleted")
        if selection[1:3] == [0, 0]:
            # URL only
            return selection[:1]
        # URL, offset, size
        return selection[:3]

    @lru_cache(4096)
    def _key_to_record(self, key):
        """Details needed to construct a reference for one key"""
        field, chunk = key.rsplit("/", 1)
        chunk_sizes = self._get_chunk_sizes(field)
        if len(chunk_sizes) == 0:
            return 0, 0, 0
        chunk_idx = [int(c) for c in chunk.split(".")]
        chunk_number = ravel_multi_index(chunk_idx, chunk_sizes)
        record = chunk_number // self.record_size
        ri = chunk_number % self.record_size
        return record, ri, len(chunk_sizes)

    def _get_chunk_sizes(self, field):
        """The number of chunks along each axis for a given field"""
        if field not in self.chunk_sizes:
            zarray = self.zmetadata[f"{field}/.zarray"]
            size_ratio = [
                math.ceil(s / c) for s, c in zip(zarray["shape"], zarray["chunks"])
            ]
            self.chunk_sizes[field] = size_ratio or [1]
        return self.chunk_sizes[field]

    def _generate_record(self, field, record):
        """The references for a given parquet file of a given field"""
        refs = self.open_refs(field, record)
        it = iter(zip(*refs.values()))
        if len(refs) == 3:
            # All urls
            return (list(t) for t in it)
        elif len(refs) == 1:
            # All raws
            return refs["raw"]
        else:
            # Mix of urls and raws
            return (list(t[:3]) if not t[3] else t[3] for t in it)

    def _generate_all_records(self, field):
        """Load all the references within a field by iterating over the parquet files"""
        nrec = 1
        for ch in self._get_chunk_sizes(field):
            nrec *= ch
        nrec = math.ceil(nrec / self.record_size)
        for record in range(nrec):
            yield from self._generate_record(field, record)

    def values(self):
        return RefsValuesView(self)

    def items(self):
        return RefsItemsView(self)

    def __hash__(self):
        return id(self)

    def __getitem__(self, key):
        return self._load_one_key(key)

    def __setitem__(self, key, value):
        if "/" in key and not self._is_meta(key):
            field, chunk = key.rsplit("/", 1)
            record, i, _ = self._key_to_record(key)
            subdict = self._items.setdefault((field, record), {})
            subdict[i] = value
            if len(subdict) == self.record_size:
                self.write(field, record)
        else:
            # metadata or top-level
            if hasattr(value, "to_bytes"):
                val = value.to_bytes().decode()
            elif isinstance(value, bytes):
                val = value.decode()
            else:
                val = value
            self._items[key] = val
            new_value = json.loads(val)
            self.zmetadata[key] = {**self.zmetadata.get(key, {}), **new_value}

    @staticmethod
    def _is_meta(key):
        return key.startswith(".z") or "/.z" in key

    def __delitem__(self, key):
        if key in self._items:
            del self._items[key]
        elif key in self.zmetadata:
            del self.zmetadata[key]
        else:
            if "/" in key and not self._is_meta(key):
                field, _ = key.rsplit("/", 1)
                record, i, _ = self._key_to_record(key)
                subdict = self._items.setdefault((field, record), {})
                subdict[i] = None
                if len(subdict) == self.record_size:
                    self.write(field, record)
            else:
                # metadata or top-level
                self._items[key] = None

    def write(self, field, record, base_url=None, storage_options=None):
        # extra requirements if writing
        import kerchunk.df
        import numpy as np
        import pandas as pd

        partition = self._items[(field, record)]
        original = False
        if len(partition) < self.record_size:
            try:
                original = self.open_refs(field, record)
            except OSError:
                pass

        if original:
            paths = original["path"]
            offsets = original["offset"]
            sizes = original["size"]
            raws = original["raw"]
        else:
            paths = np.full(self.record_size, np.nan, dtype="O")
            offsets = np.zeros(self.record_size, dtype="int64")
            sizes = np.zeros(self.record_size, dtype="int64")
            raws = np.full(self.record_size, np.nan, dtype="O")
        for j, data in partition.items():
            if isinstance(data, list):
                if (
                    str(paths.dtype) == "category"
                    and data[0] not in paths.dtype.categories
                ):
                    paths = paths.add_categories(data[0])
                paths[j] = data[0]
                if len(data) > 1:
                    offsets[j] = data[1]
                    sizes[j] = data[2]
            elif data is None:
                # delete
                paths[j] = None
                offsets[j] = 0
                sizes[j] = 0
                raws[j] = None
            else:
                # this is the only call into kerchunk, could remove
                raws[j] = kerchunk.df._proc_raw(data)
        # TODO: only save needed columns
        df = pd.DataFrame(
            {
                "path": paths,
                "offset": offsets,
                "size": sizes,
                "raw": raws,
            },
            copy=False,
        )
        if df.path.count() / (df.path.nunique() or 1) > self.cat_thresh:
            df["path"] = df["path"].astype("category")
        object_encoding = {"raw": "bytes", "path": "utf8"}
        has_nulls = ["path", "raw"]

        fn = f"{base_url or self.out_root}/{field}/refs.{record}.parq"
        self.fs.mkdirs(f"{base_url or self.out_root}/{field}", exist_ok=True)

        if self.engine == "pyarrow":
            df_backend_kwargs = {"write_statistics": False}
        elif self.engine == "fastparquet":
            df_backend_kwargs = {
                "stats": False,
                "object_encoding": object_encoding,
                "has_nulls": has_nulls,
            }
        else:
            raise NotImplementedError(f"{self.engine} not supported")
        df.to_parquet(
            fn,
            engine=self.engine,
            storage_options=storage_options
            or getattr(self.fs, "storage_options", None),
            compression="zstd",
            index=False,
            **df_backend_kwargs,
        )

        partition.clear()
        self._items.pop((field, record))

    def flush(self, base_url=None, storage_options=None):
        """Output any modified or deleted keys

        Parameters
        ----------
        base_url: str
            Location of the output
        """

        # write what we have so far and clear sub chunks
        for thing in list(self._items):
            if isinstance(thing, tuple):
                field, record = thing
                self.write(
                    field,
                    record,
                    base_url=base_url,
                    storage_options=storage_options,
                )

        # gather .zmetadata from self._items and write that too
        for k in list(self._items):
            if k != ".zmetadata" and ".z" in k:
                self.zmetadata[k] = json.loads(self._items.pop(k))
        met = {"metadata": self.zmetadata, "record_size": self.record_size}
        self._items.clear()
        self._items[".zmetadata"] = json.dumps(met).encode()
        self.fs.pipe(
            "/".join([base_url or self.out_root, ".zmetadata"]),
            self._items[".zmetadata"],
        )

        # TODO: only clear those that we wrote to?
        self.open_refs.cache_clear()

    def __len__(self):
        # Caveat: This counts expected references, not actual - but is fast
        count = 0
        for field in self.listdir():
            if field.startswith("."):
                count += 1
            else:
                count += math.prod(self._get_chunk_sizes(field))
        count += len(self.zmetadata)  # all metadata keys
        # any other files not in reference partitions
        count += sum(1 for _ in self._items if not isinstance(_, tuple))
        return count

    def __iter__(self):
        # Caveat: returns only existing keys, so the number of these does not
        #  match len(self)
        metas = set(self.zmetadata)
        metas.update(self._items)
        for bit in metas:
            if isinstance(bit, str):
                yield bit
        for field in self.listdir():
            for k in self._keys_in_field(field):
                if k in self:
                    yield k

    def __contains__(self, item):
        try:
            self._load_one_key(item)
            return True
        except KeyError:
            return False

    def _keys_in_field(self, field):
        """List key names in given field

        Produces strings like "field/x.y" appropriate from the chunking of the array
        """
        chunk_sizes = self._get_chunk_sizes(field)
        if len(chunk_sizes) == 0:
            yield field + "/0"
            return
        inds = itertools.product(*(range(i) for i in chunk_sizes))
        for ind in inds:
            yield field + "/" + ".".join([str(c) for c in ind])


class ReferenceFileSystem(AsyncFileSystem):
    """View byte ranges of some other file as a file system
    Initial version: single file system target, which must support
    async, and must allow start and end args in _cat_file. Later versions
    may allow multiple arbitrary URLs for the targets.
    This FileSystem is read-only. It is designed to be used with async
    targets (for now). We do not get original file details from the target FS.
    Configuration is by passing a dict of references at init, or a URL to
    a JSON file containing the same; this dict
    can also contain concrete data for some set of paths.
    Reference dict format:
    {path0: bytes_data, path1: (target_url, offset, size)}
    https://github.com/fsspec/kerchunk/blob/main/README.md
    """

    protocol = "reference"
    cachable = False

    def __init__(
        self,
        fo,
        target=None,
        ref_storage_args=None,
        target_protocol=None,
        target_options=None,
        remote_protocol=None,
        remote_options=None,
        fs=None,
        template_overrides=None,
        simple_templates=True,
        max_gap=64_000,
        max_block=256_000_000,
        cache_size=128,
        **kwargs,
    ):
        """
        Parameters
        ----------
        fo : dict or str
            The set of references to use for this instance, with a structure as above.
            If str referencing a JSON file, will use fsspec.open, in conjunction
            with target_options and target_protocol to open and parse JSON at this
            location. If a directory, then assume references are a set of parquet
            files to be loaded lazily.
        target : str
            For any references having target_url as None, this is the default file
            target to use
        ref_storage_args : dict
            If references is a str, use these kwargs for loading the JSON file.
            Deprecated: use target_options instead.
        target_protocol : str
            Used for loading the reference file, if it is a path. If None, protocol
            will be derived from the given path
        target_options : dict
            Extra FS options for loading the reference file ``fo``, if given as a path
        remote_protocol : str
            The protocol of the filesystem on which the references will be evaluated
            (unless fs is provided). If not given, will be derived from the first
            URL that has a protocol in the templates or in the references, in that
            order.
        remote_options : dict
            kwargs to go with remote_protocol
        fs : AbstractFileSystem | dict(str, (AbstractFileSystem | dict))
            Directly provide a file system(s):
                - a single filesystem instance
                - a dict of protocol:filesystem, where each value is either a filesystem
                  instance, or a dict of kwargs that can be used to create in
                  instance for the given protocol

            If this is given, remote_options and remote_protocol are ignored.
        template_overrides : dict
            Swap out any templates in the references file with these - useful for
            testing.
        simple_templates: bool
            Whether templates can be processed with simple replace (True) or if
            jinja  is needed (False, much slower). All reference sets produced by
            ``kerchunk`` are simple in this sense, but the spec allows for complex.
        max_gap, max_block: int
            For merging multiple concurrent requests to the same remote file.
            Neighboring byte ranges will only be merged when their
            inter-range gap is <= ``max_gap``. Default is 64KB. Set to 0
            to only merge when it requires no extra bytes. Pass a negative
            number to disable merging, appropriate for local target files.
            Neighboring byte ranges will only be merged when the size of
            the aggregated range is <= ``max_block``. Default is 256MB.
        cache_size : int
            Maximum size of LRU cache, where cache_size*record_size denotes
            the total number of references that can be loaded in memory at once.
            Only used for lazily loaded references.
        kwargs : passed to parent class
        """
        super().__init__(**kwargs)
        self.target = target
        self.template_overrides = template_overrides
        self.simple_templates = simple_templates
        self.templates = {}
        self.fss = {}
        self._dircache = {}
        self.max_gap = max_gap
        self.max_block = max_block
        if isinstance(fo, str):
            dic = dict(
                **(ref_storage_args or target_options or {}), protocol=target_protocol
            )
            ref_fs, fo2 = fsspec.core.url_to_fs(fo, **dic)
            if ref_fs.isfile(fo2):
                # text JSON
                with fsspec.open(fo, "rb", **dic) as f:
                    logger.info("Read reference from URL %s", fo)
                    text = json.load(f)
                self._process_references(text, template_overrides)
            else:
                # Lazy parquet refs
                logger.info("Open lazy reference dict from URL %s", fo)
                self.references = LazyReferenceMapper(
                    fo2,
                    fs=ref_fs,
                    cache_size=cache_size,
                )
        else:
            # dictionaries
            self._process_references(fo, template_overrides)
        if isinstance(fs, dict):
            self.fss = {
                k: (
                    fsspec.filesystem(k.split(":", 1)[0], **opts)
                    if isinstance(opts, dict)
                    else opts
                )
                for k, opts in fs.items()
            }
            if None not in self.fss:
                self.fss[None] = filesystem("file")
            return
        if fs is not None:
            # single remote FS
            remote_protocol = (
                fs.protocol[0] if isinstance(fs.protocol, tuple) else fs.protocol
            )
            self.fss[remote_protocol] = fs

        if remote_protocol is None:
            # get single protocol from any templates
            for ref in self.templates.values():
                if callable(ref):
                    ref = ref()
                protocol, _ = fsspec.core.split_protocol(ref)
                if protocol and protocol not in self.fss:
                    fs = filesystem(protocol, **(remote_options or {}))
                    self.fss[protocol] = fs
        if remote_protocol is None:
            # get single protocol from references
            # TODO: warning here, since this can be very expensive?
            for ref in self.references.values():
                if callable(ref):
                    ref = ref()
                if isinstance(ref, list) and ref[0]:
                    protocol, _ = fsspec.core.split_protocol(ref[0])
                    if protocol not in self.fss:
                        fs = filesystem(protocol, **(remote_options or {}))
                        self.fss[protocol] = fs
                        # only use first remote URL
                        break

        if remote_protocol and remote_protocol not in self.fss:
            fs = filesystem(remote_protocol, **(remote_options or {}))
            self.fss[remote_protocol] = fs

        self.fss[None] = fs or filesystem("file")  # default one
        # Wrap any non-async filesystems to ensure async methods are available below
        for k, f in self.fss.items():
            if not f.async_impl:
                self.fss[k] = AsyncFileSystemWrapper(f, asynchronous=self.asynchronous)
            elif self.asynchronous ^ f.asynchronous:
                raise ValueError(
                    "Reference-FS's target filesystem must have same value"
                    "of asynchronous"
                )

    def _cat_common(self, path, start=None, end=None):
        path = self._strip_protocol(path)
        logger.debug(f"cat: {path}")
        try:
            part = self.references[path]
        except KeyError as exc:
            raise FileNotFoundError(path) from exc
        if isinstance(part, str):
            part = part.encode()
        if hasattr(part, "to_bytes"):
            part = part.to_bytes()
        if isinstance(part, bytes):
            logger.debug(f"Reference: {path}, type bytes")
            if part.startswith(b"base64:"):
                part = base64.b64decode(part[7:])
            return part, None, None

        if len(part) == 1:
            logger.debug(f"Reference: {path}, whole file => {part}")
            url = part[0]
            start1, end1 = start, end
        else:
            url, start0, size = part
            logger.debug(f"Reference: {path} => {url}, offset {start0}, size {size}")
            end0 = start0 + size

            if start is not None:
                if start >= 0:
                    start1 = start0 + start
                else:
                    start1 = end0 + start
            else:
                start1 = start0
            if end is not None:
                if end >= 0:
                    end1 = start0 + end
                else:
                    end1 = end0 + end
            else:
                end1 = end0
        if url is None:
            url = self.target
        return url, start1, end1

    async def _cat_file(self, path, start=None, end=None, **kwargs):
        part_or_url, start0, end0 = self._cat_common(path, start=start, end=end)
        if isinstance(part_or_url, bytes):
            return part_or_url[start:end]
        protocol, _ = split_protocol(part_or_url)
        try:
            return await self.fss[protocol]._cat_file(
                part_or_url, start=start0, end=end0
            )
        except Exception as e:
            raise ReferenceNotReachable(path, part_or_url) from e

    def cat_file(self, path, start=None, end=None, **kwargs):
        part_or_url, start0, end0 = self._cat_common(path, start=start, end=end)
        if isinstance(part_or_url, bytes):
            return part_or_url[start:end]
        protocol, _ = split_protocol(part_or_url)
        try:
            return self.fss[protocol].cat_file(part_or_url, start=start0, end=end0)
        except Exception as e:
            raise ReferenceNotReachable(path, part_or_url) from e

    def pipe_file(self, path, value, **_):
        """Temporarily add binary data or reference as a file"""
        self.references[path] = value

    async def _get_file(self, rpath, lpath, **kwargs):
        if self.isdir(rpath):
            return os.makedirs(lpath, exist_ok=True)
        data = await self._cat_file(rpath)
        with open(lpath, "wb") as f:
            f.write(data)

    def get_file(self, rpath, lpath, callback=DEFAULT_CALLBACK, **kwargs):
        if self.isdir(rpath):
            return os.makedirs(lpath, exist_ok=True)
        data = self.cat_file(rpath, **kwargs)
        callback.set_size(len(data))
        if isfilelike(lpath):
            lpath.write(data)
        else:
            with open(lpath, "wb") as f:
                f.write(data)
        callback.absolute_update(len(data))

    def get(self, rpath, lpath, recursive=False, **kwargs):
        if recursive:
            # trigger directory build
            self.ls("")
        rpath = self.expand_path(rpath, recursive=recursive)
        fs = fsspec.filesystem("file", auto_mkdir=True)
        targets = other_paths(rpath, lpath)
        if recursive:
            data = self.cat([r for r in rpath if not self.isdir(r)])
        else:
            data = self.cat(rpath)
        for remote, local in zip(rpath, targets):
            if remote in data:
                fs.pipe_file(local, data[remote])

    def cat(self, path, recursive=False, on_error="raise", **kwargs):
        if isinstance(path, str) and recursive:
            raise NotImplementedError
        if isinstance(path, list) and (recursive or any("*" in p for p in path)):
            raise NotImplementedError
        # TODO: if references is lazy, pre-fetch all paths in batch before access
        proto_dict = _protocol_groups(path, self.references)
        out = {}
        for proto, paths in proto_dict.items():
            fs = self.fss[proto]
            urls, starts, ends, valid_paths = [], [], [], []
            for p in paths:
                # find references or label not-found. Early exit if any not
                # found and on_error is "raise"
                try:
                    u, s, e = self._cat_common(p)
                    if not isinstance(u, (bytes, str)):
                        # nan/None from parquet
                        continue
                except FileNotFoundError as err:
                    if on_error == "raise":
                        raise
                    if on_error != "omit":
                        out[p] = err
                else:
                    urls.append(u)
                    starts.append(s)
                    ends.append(e)
                    valid_paths.append(p)

            # process references into form for merging
            urls2 = []
            starts2 = []
            ends2 = []
            paths2 = []
            whole_files = set()
            for u, s, e, p in zip(urls, starts, ends, valid_paths):
                if isinstance(u, bytes):
                    # data
                    out[p] = u
                elif s is None:
                    # whole file - limits are None, None, but no further
                    # entries take for this file
                    whole_files.add(u)
                    urls2.append(u)
                    starts2.append(s)
                    ends2.append(e)
                    paths2.append(p)
            for u, s, e, p in zip(urls, starts, ends, valid_paths):
                # second run to account for files that are to be loaded whole
                if s is not None and u not in whole_files:
                    urls2.append(u)
                    starts2.append(s)
                    ends2.append(e)
                    paths2.append(p)

            # merge and fetch consolidated ranges
            new_paths, new_starts, new_ends = merge_offset_ranges(
                list(urls2),
                list(starts2),
                list(ends2),
                sort=True,
                max_gap=self.max_gap,
                max_block=self.max_block,
            )
            bytes_out = fs.cat_ranges(new_paths, new_starts, new_ends)

            # unbundle from merged bytes - simple approach
            for u, s, e, p in zip(urls, starts, ends, valid_paths):
                if p in out:
                    continue  # was bytes, already handled
                for np, ns, ne, b in zip(new_paths, new_starts, new_ends, bytes_out):
                    if np == u and (ns is None or ne is None):
                        if isinstance(b, Exception):
                            out[p] = b
                        else:
                            out[p] = b[s:e]
                    elif np == u and s >= ns and e <= ne:
                        if isinstance(b, Exception):
                            out[p] = b
                        else:
                            out[p] = b[s - ns : (e - ne) or None]

        for k, v in out.copy().items():
            # these were valid references, but fetch failed, so transform exc
            if isinstance(v, Exception) and k in self.references:
                ex = out[k]
                new_ex = ReferenceNotReachable(k, self.references[k])
                new_ex.__cause__ = ex
                if on_error == "raise":
                    raise new_ex
                elif on_error != "omit":
                    out[k] = new_ex

        if len(out) == 1 and isinstance(path, str) and "*" not in path:
            return _first(out)
        return out

    def _process_references(self, references, template_overrides=None):
        vers = references.get("version", None)
        if vers is None:
            self._process_references0(references)
        elif vers == 1:
            self._process_references1(references, template_overrides=template_overrides)
        else:
            raise ValueError(f"Unknown reference spec version: {vers}")
        # TODO: we make dircache by iterating over all entries, but for Spec >= 1,
        #  can replace with programmatic. Is it even needed for mapper interface?

    def _process_references0(self, references):
        """Make reference dict for Spec Version 0"""
        if isinstance(references, dict):
            # do not do this for lazy/parquet backend, which will not make dicts,
            # but must remain writable in the original object
            references = {
                key: json.dumps(val) if isinstance(val, dict) else val
                for key, val in references.items()
            }
        self.references = references

    def _process_references1(self, references, template_overrides=None):
        if not self.simple_templates or self.templates:
            import jinja2
        self.references = {}
        self._process_templates(references.get("templates", {}))

        @lru_cache(1000)
        def _render_jinja(u):
            return jinja2.Template(u).render(**self.templates)

        for k, v in references.get("refs", {}).items():
            if isinstance(v, str):
                if v.startswith("base64:"):
                    self.references[k] = base64.b64decode(v[7:])
                self.references[k] = v
            elif isinstance(v, dict):
                self.references[k] = json.dumps(v)
            elif self.templates:
                u = v[0]
                if "{{" in u:
                    if self.simple_templates:
                        u = (
                            u.replace("{{", "{")
                            .replace("}}", "}")
                            .format(**self.templates)
                        )
                    else:
                        u = _render_jinja(u)
                self.references[k] = [u] if len(v) == 1 else [u, v[1], v[2]]
            else:
                self.references[k] = v
        self.references.update(self._process_gen(references.get("gen", [])))

    def _process_templates(self, tmp):
        self.templates = {}
        if self.template_overrides is not None:
            tmp.update(self.template_overrides)
        for k, v in tmp.items():
            if "{{" in v:
                import jinja2

                self.templates[k] = lambda temp=v, **kwargs: jinja2.Template(
                    temp
                ).render(**kwargs)
            else:
                self.templates[k] = v

    def _process_gen(self, gens):
        out = {}
        for gen in gens:
            dimension = {
                k: (
                    v
                    if isinstance(v, list)
                    else range(v.get("start", 0), v["stop"], v.get("step", 1))
                )
                for k, v in gen["dimensions"].items()
            }
            products = (
                dict(zip(dimension.keys(), values))
                for values in itertools.product(*dimension.values())
            )
            for pr in products:
                import jinja2

                key = jinja2.Template(gen["key"]).render(**pr, **self.templates)
                url = jinja2.Template(gen["url"]).render(**pr, **self.templates)
                if ("offset" in gen) and ("length" in gen):
                    offset = int(
                        jinja2.Template(gen["offset"]).render(**pr, **self.templates)
                    )
                    length = int(
                        jinja2.Template(gen["length"]).render(**pr, **self.templates)
                    )
                    out[key] = [url, offset, length]
                elif ("offset" in gen) ^ ("length" in gen):
                    raise ValueError(
                        "Both 'offset' and 'length' are required for a "
                        "reference generator entry if either is provided."
                    )
                else:
                    out[key] = [url]
        return out

    def _dircache_from_items(self):
        self.dircache = {"": []}
        it = self.references.items()
        for path, part in it:
            if isinstance(part, (bytes, str)) or hasattr(part, "to_bytes"):
                size = len(part)
            elif len(part) == 1:
                size = None
            else:
                _, _, size = part
            par = path.rsplit("/", 1)[0] if "/" in path else ""
            par0 = par
            subdirs = [par0]
            while par0 and par0 not in self.dircache:
                # collect parent directories
                par0 = self._parent(par0)
                subdirs.append(par0)

            subdirs.reverse()
            for parent, child in zip(subdirs, subdirs[1:]):
                # register newly discovered directories
                assert child not in self.dircache
                assert parent in self.dircache
                self.dircache[parent].append(
                    {"name": child, "type": "directory", "size": 0}
                )
                self.dircache[child] = []

            self.dircache[par].append({"name": path, "type": "file", "size": size})

    def _open(self, path, mode="rb", block_size=None, cache_options=None, **kwargs):
        part_or_url, start0, end0 = self._cat_common(path)
        # This logic is kept outside `ReferenceFile` to avoid unnecessary redirection.
        # That does mean `_cat_common` gets called twice if it eventually reaches `ReferenceFile`.
        if isinstance(part_or_url, bytes):
            return io.BytesIO(part_or_url[start0:end0])

        protocol, _ = split_protocol(part_or_url)
        if start0 is None and end0 is None:
            return self.fss[protocol]._open(
                part_or_url,
                mode,
                block_size=block_size,
                cache_options=cache_options,
                **kwargs,
            )

        return ReferenceFile(
            self,
            path,
            mode,
            block_size=block_size,
            cache_options=cache_options,
            **kwargs,
        )

    def ls(self, path, detail=True, **kwargs):
        logger.debug("list %s", path)
        path = self._strip_protocol(path)
        if isinstance(self.references, LazyReferenceMapper):
            try:
                return self.references.ls(path, detail)
            except KeyError:
                pass
            raise FileNotFoundError(f"'{path}' is not a known key")
        if not self.dircache:
            self._dircache_from_items()
        out = self._ls_from_cache(path)
        if out is None:
            raise FileNotFoundError(path)
        if detail:
            return out
        return [o["name"] for o in out]

    def exists(self, path, **kwargs):  # overwrite auto-sync version
        return self.isdir(path) or self.isfile(path)

    def isdir(self, path):  # overwrite auto-sync version
        if self.dircache:
            return path in self.dircache
        elif isinstance(self.references, LazyReferenceMapper):
            return path in self.references.listdir()
        else:
            # this may be faster than building dircache for single calls, but
            # by looping will be slow for many calls; could cache it?
            return any(_.startswith(f"{path}/") for _ in self.references)

    def isfile(self, path):  # overwrite auto-sync version
        return path in self.references

    async def _ls(self, path, detail=True, **kwargs):  # calls fast sync code
        return self.ls(path, detail, **kwargs)

    def find(self, path, maxdepth=None, withdirs=False, detail=False, **kwargs):
        if withdirs:
            return super().find(
                path, maxdepth=maxdepth, withdirs=withdirs, detail=detail, **kwargs
            )
        if path:
            path = self._strip_protocol(path)
            r = sorted(k for k in self.references if k.startswith(path))
        else:
            r = sorted(self.references)
        if detail:
            if not self.dircache:
                self._dircache_from_items()
            return {k: self._ls_from_cache(k)[0] for k in r}
        else:
            return r

    def info(self, path, **kwargs):
        out = self.references.get(path)
        if out is not None:
            if isinstance(out, (str, bytes)):
                # decode base64 here
                return {"name": path, "type": "file", "size": len(out)}
            elif len(out) > 1:
                return {"name": path, "type": "file", "size": out[2]}
            else:
                out0 = [{"name": path, "type": "file", "size": None}]
        else:
            out = self.ls(path, True)
            out0 = [o for o in out if o["name"] == path]
            if not out0:
                return {"name": path, "type": "directory", "size": 0}
        if out0[0]["size"] is None:
            # if this is a whole remote file, update size using remote FS
            prot, _ = split_protocol(self.references[path][0])
            out0[0]["size"] = self.fss[prot].size(self.references[path][0])
        return out0[0]

    async def _info(self, path, **kwargs):  # calls fast sync code
        return self.info(path)

    async def _rm_file(self, path, **kwargs):
        self.references.pop(
            path, None
        )  # ignores FileNotFound, just as well for directories
        self.dircache.clear()  # this is a bit heavy handed

    async def _pipe_file(self, path, data, mode="overwrite", **kwargs):
        if mode == "create" and self.exists(path):
            raise FileExistsError
        # can be str or bytes
        self.references[path] = data
        self.dircache.clear()  # this is a bit heavy handed

    async def _put_file(self, lpath, rpath, mode="overwrite", **kwargs):
        # puts binary
        if mode == "create" and self.exists(rpath):
            raise FileExistsError
        with open(lpath, "rb") as f:
            self.references[rpath] = f.read()
        self.dircache.clear()  # this is a bit heavy handed

    def save_json(self, url, **storage_options):
        """Write modified references into new location"""
        out = {}
        for k, v in self.references.items():
            if isinstance(v, bytes):
                try:
                    out[k] = v.decode("ascii")
                except UnicodeDecodeError:
                    out[k] = (b"base64:" + base64.b64encode(v)).decode()
            else:
                out[k] = v
        with fsspec.open(url, "wb", **storage_options) as f:
            f.write(json.dumps({"version": 1, "refs": out}).encode())


class ReferenceFile(AbstractBufferedFile):
    def __init__(
        self,
        fs,
        path,
        mode="rb",
        block_size="default",
        autocommit=True,
        cache_type="readahead",
        cache_options=None,
        size=None,
        **kwargs,
    ):
        super().__init__(
            fs,
            path,
            mode=mode,
            block_size=block_size,
            autocommit=autocommit,
            size=size,
            cache_type=cache_type,
            cache_options=cache_options,
            **kwargs,
        )
        part_or_url, self.start, self.end = self.fs._cat_common(self.path)
        protocol, _ = split_protocol(part_or_url)
        self.src_fs = self.fs.fss[protocol]
        self.src_path = part_or_url
        self._f = None

    @property
    def f(self):
        if self._f is None or self._f.closed:
            self._f = self.src_fs._open(
                self.src_path,
                mode=self.mode,
                block_size=self.blocksize,
                autocommit=self.autocommit,
                cache_type="none",
                **self.kwargs,
            )
        return self._f

    def close(self):
        if self._f is not None:
            self._f.close()
        return super().close()

    def _fetch_range(self, start, end):
        start = start + self.start
        end = min(end + self.start, self.end)
        self.f.seek(start)
        return self.f.read(end - start)

# === NexusCore/openenv\Lib\site-packages\aiohttp\web_urldispatcher.py ===
import abc
import asyncio
import base64
import functools
import hashlib
import html
import inspect
import keyword
import os
import re
import sys
import warnings
from functools import wraps
from pathlib import Path
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Container,
    Dict,
    Final,
    Generator,
    Iterable,
    Iterator,
    List,
    Mapping,
    NoReturn,
    Optional,
    Pattern,
    Set,
    Sized,
    Tuple,
    Type,
    TypedDict,
    Union,
    cast,
)

from yarl import URL, __version__ as yarl_version

from . import hdrs
from .abc import AbstractMatchInfo, AbstractRouter, AbstractView
from .helpers import DEBUG
from .http import HttpVersion11
from .typedefs import Handler, PathLike
from .web_exceptions import (
    HTTPException,
    HTTPExpectationFailed,
    HTTPForbidden,
    HTTPMethodNotAllowed,
    HTTPNotFound,
)
from .web_fileresponse import FileResponse
from .web_request import Request
from .web_response import Response, StreamResponse
from .web_routedef import AbstractRouteDef

__all__ = (
    "UrlDispatcher",
    "UrlMappingMatchInfo",
    "AbstractResource",
    "Resource",
    "PlainResource",
    "DynamicResource",
    "AbstractRoute",
    "ResourceRoute",
    "StaticResource",
    "View",
)


if TYPE_CHECKING:
    from .web_app import Application

    BaseDict = Dict[str, str]
else:
    BaseDict = dict

CIRCULAR_SYMLINK_ERROR = (
    (OSError,)
    if sys.version_info < (3, 10) and sys.platform.startswith("win32")
    else (RuntimeError,) if sys.version_info < (3, 13) else ()
)

YARL_VERSION: Final[Tuple[int, ...]] = tuple(map(int, yarl_version.split(".")[:2]))

HTTP_METHOD_RE: Final[Pattern[str]] = re.compile(
    r"^[0-9A-Za-z!#\$%&'\*\+\-\.\^_`\|~]+$"
)
ROUTE_RE: Final[Pattern[str]] = re.compile(
    r"(\{[_a-zA-Z][^{}]*(?:\{[^{}]*\}[^{}]*)*\})"
)
PATH_SEP: Final[str] = re.escape("/")


_ExpectHandler = Callable[[Request], Awaitable[Optional[StreamResponse]]]
_Resolve = Tuple[Optional["UrlMappingMatchInfo"], Set[str]]

html_escape = functools.partial(html.escape, quote=True)


class _InfoDict(TypedDict, total=False):
    path: str

    formatter: str
    pattern: Pattern[str]

    directory: Path
    prefix: str
    routes: Mapping[str, "AbstractRoute"]

    app: "Application"

    domain: str

    rule: "AbstractRuleMatching"

    http_exception: HTTPException


class AbstractResource(Sized, Iterable["AbstractRoute"]):
    def __init__(self, *, name: Optional[str] = None) -> None:
        self._name = name

    @property
    def name(self) -> Optional[str]:
        return self._name

    @property
    @abc.abstractmethod
    def canonical(self) -> str:
        """Exposes the resource's canonical path.

        For example '/foo/bar/{name}'

        """

    @abc.abstractmethod  # pragma: no branch
    def url_for(self, **kwargs: str) -> URL:
        """Construct url for resource with additional params."""

    @abc.abstractmethod  # pragma: no branch
    async def resolve(self, request: Request) -> _Resolve:
        """Resolve resource.

        Return (UrlMappingMatchInfo, allowed_methods) pair.
        """

    @abc.abstractmethod
    def add_prefix(self, prefix: str) -> None:
        """Add a prefix to processed URLs.

        Required for subapplications support.
        """

    @abc.abstractmethod
    def get_info(self) -> _InfoDict:
        """Return a dict with additional info useful for introspection"""

    def freeze(self) -> None:
        pass

    @abc.abstractmethod
    def raw_match(self, path: str) -> bool:
        """Perform a raw match against path"""


class AbstractRoute(abc.ABC):
    def __init__(
        self,
        method: str,
        handler: Union[Handler, Type[AbstractView]],
        *,
        expect_handler: Optional[_ExpectHandler] = None,
        resource: Optional[AbstractResource] = None,
    ) -> None:

        if expect_handler is None:
            expect_handler = _default_expect_handler

        assert inspect.iscoroutinefunction(expect_handler) or (
            sys.version_info < (3, 14) and asyncio.iscoroutinefunction(expect_handler)
        ), f"Coroutine is expected, got {expect_handler!r}"

        method = method.upper()
        if not HTTP_METHOD_RE.match(method):
            raise ValueError(f"{method} is not allowed HTTP method")

        assert callable(handler), handler
        if inspect.iscoroutinefunction(handler) or (
            sys.version_info < (3, 14) and asyncio.iscoroutinefunction(handler)
        ):
            pass
        elif inspect.isgeneratorfunction(handler):
            warnings.warn(
                "Bare generators are deprecated, use @coroutine wrapper",
                DeprecationWarning,
            )
        elif isinstance(handler, type) and issubclass(handler, AbstractView):
            pass
        else:
            warnings.warn(
                "Bare functions are deprecated, use async ones", DeprecationWarning
            )

            @wraps(handler)
            async def handler_wrapper(request: Request) -> StreamResponse:
                result = old_handler(request)  # type: ignore[call-arg]
                if asyncio.iscoroutine(result):
                    result = await result
                assert isinstance(result, StreamResponse)
                return result

            old_handler = handler
            handler = handler_wrapper

        self._method = method
        self._handler = handler
        self._expect_handler = expect_handler
        self._resource = resource

    @property
    def method(self) -> str:
        return self._method

    @property
    def handler(self) -> Handler:
        return self._handler

    @property
    @abc.abstractmethod
    def name(self) -> Optional[str]:
        """Optional route's name, always equals to resource's name."""

    @property
    def resource(self) -> Optional[AbstractResource]:
        return self._resource

    @abc.abstractmethod
    def get_info(self) -> _InfoDict:
        """Return a dict with additional info useful for introspection"""

    @abc.abstractmethod  # pragma: no branch
    def url_for(self, *args: str, **kwargs: str) -> URL:
        """Construct url for route with additional params."""

    async def handle_expect_header(self, request: Request) -> Optional[StreamResponse]:
        return await self._expect_handler(request)


class UrlMappingMatchInfo(BaseDict, AbstractMatchInfo):

    __slots__ = ("_route", "_apps", "_current_app", "_frozen")

    def __init__(self, match_dict: Dict[str, str], route: AbstractRoute) -> None:
        super().__init__(match_dict)
        self._route = route
        self._apps: List[Application] = []
        self._current_app: Optional[Application] = None
        self._frozen = False

    @property
    def handler(self) -> Handler:
        return self._route.handler

    @property
    def route(self) -> AbstractRoute:
        return self._route

    @property
    def expect_handler(self) -> _ExpectHandler:
        return self._route.handle_expect_header

    @property
    def http_exception(self) -> Optional[HTTPException]:
        return None

    def get_info(self) -> _InfoDict:  # type: ignore[override]
        return self._route.get_info()

    @property
    def apps(self) -> Tuple["Application", ...]:
        return tuple(self._apps)

    def add_app(self, app: "Application") -> None:
        if self._frozen:
            raise RuntimeError("Cannot change apps stack after .freeze() call")
        if self._current_app is None:
            self._current_app = app
        self._apps.insert(0, app)

    @property
    def current_app(self) -> "Application":
        app = self._current_app
        assert app is not None
        return app

    @current_app.setter
    def current_app(self, app: "Application") -> None:
        if DEBUG:  # pragma: no cover
            if app not in self._apps:
                raise RuntimeError(
                    "Expected one of the following apps {!r}, got {!r}".format(
                        self._apps, app
                    )
                )
        self._current_app = app

    def freeze(self) -> None:
        self._frozen = True

    def __repr__(self) -> str:
        return f"<MatchInfo {super().__repr__()}: {self._route}>"


class MatchInfoError(UrlMappingMatchInfo):

    __slots__ = ("_exception",)

    def __init__(self, http_exception: HTTPException) -> None:
        self._exception = http_exception
        super().__init__({}, SystemRoute(self._exception))

    @property
    def http_exception(self) -> HTTPException:
        return self._exception

    def __repr__(self) -> str:
        return "<MatchInfoError {}: {}>".format(
            self._exception.status, self._exception.reason
        )


async def _default_expect_handler(request: Request) -> None:
    """Default handler for Expect header.

    Just send "100 Continue" to client.
    raise HTTPExpectationFailed if value of header is not "100-continue"
    """
    expect = request.headers.get(hdrs.EXPECT, "")
    if request.version == HttpVersion11:
        if expect.lower() == "100-continue":
            await request.writer.write(b"HTTP/1.1 100 Continue\r\n\r\n")
            # Reset output_size as we haven't started the main body yet.
            request.writer.output_size = 0
        else:
            raise HTTPExpectationFailed(text="Unknown Expect: %s" % expect)


class Resource(AbstractResource):
    def __init__(self, *, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self._routes: Dict[str, ResourceRoute] = {}
        self._any_route: Optional[ResourceRoute] = None
        self._allowed_methods: Set[str] = set()

    def add_route(
        self,
        method: str,
        handler: Union[Type[AbstractView], Handler],
        *,
        expect_handler: Optional[_ExpectHandler] = None,
    ) -> "ResourceRoute":
        if route := self._routes.get(method, self._any_route):
            raise RuntimeError(
                "Added route will never be executed, "
                f"method {route.method} is already "
                "registered"
            )

        route_obj = ResourceRoute(method, handler, self, expect_handler=expect_handler)
        self.register_route(route_obj)
        return route_obj

    def register_route(self, route: "ResourceRoute") -> None:
        assert isinstance(
            route, ResourceRoute
        ), f"Instance of Route class is required, got {route!r}"
        if route.method == hdrs.METH_ANY:
            self._any_route = route
        self._allowed_methods.add(route.method)
        self._routes[route.method] = route

    async def resolve(self, request: Request) -> _Resolve:
        if (match_dict := self._match(request.rel_url.path_safe)) is None:
            return None, set()
        if route := self._routes.get(request.method, self._any_route):
            return UrlMappingMatchInfo(match_dict, route), self._allowed_methods
        return None, self._allowed_methods

    @abc.abstractmethod
    def _match(self, path: str) -> Optional[Dict[str, str]]:
        pass  # pragma: no cover

    def __len__(self) -> int:
        return len(self._routes)

    def __iter__(self) -> Iterator["ResourceRoute"]:
        return iter(self._routes.values())

    # TODO: implement all abstract methods


class PlainResource(Resource):
    def __init__(self, path: str, *, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        assert not path or path.startswith("/")
        self._path = path

    @property
    def canonical(self) -> str:
        return self._path

    def freeze(self) -> None:
        if not self._path:
            self._path = "/"

    def add_prefix(self, prefix: str) -> None:
        assert prefix.startswith("/")
        assert not prefix.endswith("/")
        assert len(prefix) > 1
        self._path = prefix + self._path

    def _match(self, path: str) -> Optional[Dict[str, str]]:
        # string comparison is about 10 times faster than regexp matching
        if self._path == path:
            return {}
        return None

    def raw_match(self, path: str) -> bool:
        return self._path == path

    def get_info(self) -> _InfoDict:
        return {"path": self._path}

    def url_for(self) -> URL:  # type: ignore[override]
        return URL.build(path=self._path, encoded=True)

    def __repr__(self) -> str:
        name = "'" + self.name + "' " if self.name is not None else ""
        return f"<PlainResource {name} {self._path}>"


class DynamicResource(Resource):

    DYN = re.compile(r"\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*)\}")
    DYN_WITH_RE = re.compile(r"\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*):(?P<re>.+)\}")
    GOOD = r"[^{}/]+"

    def __init__(self, path: str, *, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self._orig_path = path
        pattern = ""
        formatter = ""
        for part in ROUTE_RE.split(path):
            match = self.DYN.fullmatch(part)
            if match:
                pattern += "(?P<{}>{})".format(match.group("var"), self.GOOD)
                formatter += "{" + match.group("var") + "}"
                continue

            match = self.DYN_WITH_RE.fullmatch(part)
            if match:
                pattern += "(?P<{var}>{re})".format(**match.groupdict())
                formatter += "{" + match.group("var") + "}"
                continue

            if "{" in part or "}" in part:
                raise ValueError(f"Invalid path '{path}'['{part}']")

            part = _requote_path(part)
            formatter += part
            pattern += re.escape(part)

        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"Bad pattern '{pattern}': {exc}") from None
        assert compiled.pattern.startswith(PATH_SEP)
        assert formatter.startswith("/")
        self._pattern = compiled
        self._formatter = formatter

    @property
    def canonical(self) -> str:
        return self._formatter

    def add_prefix(self, prefix: str) -> None:
        assert prefix.startswith("/")
        assert not prefix.endswith("/")
        assert len(prefix) > 1
        self._pattern = re.compile(re.escape(prefix) + self._pattern.pattern)
        self._formatter = prefix + self._formatter

    def _match(self, path: str) -> Optional[Dict[str, str]]:
        match = self._pattern.fullmatch(path)
        if match is None:
            return None
        return {
            key: _unquote_path_safe(value) for key, value in match.groupdict().items()
        }

    def raw_match(self, path: str) -> bool:
        return self._orig_path == path

    def get_info(self) -> _InfoDict:
        return {"formatter": self._formatter, "pattern": self._pattern}

    def url_for(self, **parts: str) -> URL:
        url = self._formatter.format_map({k: _quote_path(v) for k, v in parts.items()})
        return URL.build(path=url, encoded=True)

    def __repr__(self) -> str:
        name = "'" + self.name + "' " if self.name is not None else ""
        return "<DynamicResource {name} {formatter}>".format(
            name=name, formatter=self._formatter
        )


class PrefixResource(AbstractResource):
    def __init__(self, prefix: str, *, name: Optional[str] = None) -> None:
        assert not prefix or prefix.startswith("/"), prefix
        assert prefix in ("", "/") or not prefix.endswith("/"), prefix
        super().__init__(name=name)
        self._prefix = _requote_path(prefix)
        self._prefix2 = self._prefix + "/"

    @property
    def canonical(self) -> str:
        return self._prefix

    def add_prefix(self, prefix: str) -> None:
        assert prefix.startswith("/")
        assert not prefix.endswith("/")
        assert len(prefix) > 1
        self._prefix = prefix + self._prefix
        self._prefix2 = self._prefix + "/"

    def raw_match(self, prefix: str) -> bool:
        return False

    # TODO: impl missing abstract methods


class StaticResource(PrefixResource):
    VERSION_KEY = "v"

    def __init__(
        self,
        prefix: str,
        directory: PathLike,
        *,
        name: Optional[str] = None,
        expect_handler: Optional[_ExpectHandler] = None,
        chunk_size: int = 256 * 1024,
        show_index: bool = False,
        follow_symlinks: bool = False,
        append_version: bool = False,
    ) -> None:
        super().__init__(prefix, name=name)
        try:
            directory = Path(directory).expanduser().resolve(strict=True)
        except FileNotFoundError as error:
            raise ValueError(f"'{directory}' does not exist") from error
        if not directory.is_dir():
            raise ValueError(f"'{directory}' is not a directory")
        self._directory = directory
        self._show_index = show_index
        self._chunk_size = chunk_size
        self._follow_symlinks = follow_symlinks
        self._expect_handler = expect_handler
        self._append_version = append_version

        self._routes = {
            "GET": ResourceRoute(
                "GET", self._handle, self, expect_handler=expect_handler
            ),
            "HEAD": ResourceRoute(
                "HEAD", self._handle, self, expect_handler=expect_handler
            ),
        }
        self._allowed_methods = set(self._routes)

    def url_for(  # type: ignore[override]
        self,
        *,
        filename: PathLike,
        append_version: Optional[bool] = None,
    ) -> URL:
        if append_version is None:
            append_version = self._append_version
        filename = str(filename).lstrip("/")

        url = URL.build(path=self._prefix, encoded=True)
        # filename is not encoded
        if YARL_VERSION < (1, 6):
            url = url / filename.replace("%", "%25")
        else:
            url = url / filename

        if append_version:
            unresolved_path = self._directory.joinpath(filename)
            try:
                if self._follow_symlinks:
                    normalized_path = Path(os.path.normpath(unresolved_path))
                    normalized_path.relative_to(self._directory)
                    filepath = normalized_path.resolve()
                else:
                    filepath = unresolved_path.resolve()
                    filepath.relative_to(self._directory)
            except (ValueError, FileNotFoundError):
                # ValueError for case when path point to symlink
                # with follow_symlinks is False
                return url  # relatively safe
            if filepath.is_file():
                # TODO cache file content
                # with file watcher for cache invalidation
                with filepath.open("rb") as f:
                    file_bytes = f.read()
                h = self._get_file_hash(file_bytes)
                url = url.with_query({self.VERSION_KEY: h})
                return url
        return url

    @staticmethod
    def _get_file_hash(byte_array: bytes) -> str:
        m = hashlib.sha256()  # todo sha256 can be configurable param
        m.update(byte_array)
        b64 = base64.urlsafe_b64encode(m.digest())
        return b64.decode("ascii")

    def get_info(self) -> _InfoDict:
        return {
            "directory": self._directory,
            "prefix": self._prefix,
            "routes": self._routes,
        }

    def set_options_route(self, handler: Handler) -> None:
        if "OPTIONS" in self._routes:
            raise RuntimeError("OPTIONS route was set already")
        self._routes["OPTIONS"] = ResourceRoute(
            "OPTIONS", handler, self, expect_handler=self._expect_handler
        )
        self._allowed_methods.add("OPTIONS")

    async def resolve(self, request: Request) -> _Resolve:
        path = request.rel_url.path_safe
        method = request.method
        if not path.startswith(self._prefix2) and path != self._prefix:
            return None, set()

        allowed_methods = self._allowed_methods
        if method not in allowed_methods:
            return None, allowed_methods

        match_dict = {"filename": _unquote_path_safe(path[len(self._prefix) + 1 :])}
        return (UrlMappingMatchInfo(match_dict, self._routes[method]), allowed_methods)

    def __len__(self) -> int:
        return len(self._routes)

    def __iter__(self) -> Iterator[AbstractRoute]:
        return iter(self._routes.values())

    async def _handle(self, request: Request) -> StreamResponse:
        rel_url = request.match_info["filename"]
        filename = Path(rel_url)
        if filename.anchor:
            # rel_url is an absolute name like
            # /static/\\machine_name\c$ or /static/D:\path
            # where the static dir is totally different
            raise HTTPForbidden()

        unresolved_path = self._directory.joinpath(filename)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._resolve_path_to_response, unresolved_path
        )

    def _resolve_path_to_response(self, unresolved_path: Path) -> StreamResponse:
        """Take the unresolved path and query the file system to form a response."""
        # Check for access outside the root directory. For follow symlinks, URI
        # cannot traverse out, but symlinks can. Otherwise, no access outside
        # root is permitted.
        try:
            if self._follow_symlinks:
                normalized_path = Path(os.path.normpath(unresolved_path))
                normalized_path.relative_to(self._directory)
                file_path = normalized_path.resolve()
            else:
                file_path = unresolved_path.resolve()
                file_path.relative_to(self._directory)
        except (ValueError, *CIRCULAR_SYMLINK_ERROR) as error:
            # ValueError is raised for the relative check. Circular symlinks
            # raise here on resolving for python < 3.13.
            raise HTTPNotFound() from error

        # if path is a directory, return the contents if permitted. Note the
        # directory check will raise if a segment is not readable.
        try:
            if file_path.is_dir():
                if self._show_index:
                    return Response(
                        text=self._directory_as_html(file_path),
                        content_type="text/html",
                    )
                else:
                    raise HTTPForbidden()
        except PermissionError as error:
            raise HTTPForbidden() from error

        # Return the file response, which handles all other checks.
        return FileResponse(file_path, chunk_size=self._chunk_size)

    def _directory_as_html(self, dir_path: Path) -> str:
        """returns directory's index as html."""
        assert dir_path.is_dir()

        relative_path_to_dir = dir_path.relative_to(self._directory).as_posix()
        index_of = f"Index of /{html_escape(relative_path_to_dir)}"
        h1 = f"<h1>{index_of}</h1>"

        index_list = []
        dir_index = dir_path.iterdir()
        for _file in sorted(dir_index):
            # show file url as relative to static path
            rel_path = _file.relative_to(self._directory).as_posix()
            quoted_file_url = _quote_path(f"{self._prefix}/{rel_path}")

            # if file is a directory, add '/' to the end of the name
            if _file.is_dir():
                file_name = f"{_file.name}/"
            else:
                file_name = _file.name

            index_list.append(
                f'<li><a href="{quoted_file_url}">{html_escape(file_name)}</a></li>'
            )
        ul = "<ul>\n{}\n</ul>".format("\n".join(index_list))
        body = f"<body>\n{h1}\n{ul}\n</body>"

        head_str = f"<head>\n<title>{index_of}</title>\n</head>"
        html = f"<html>\n{head_str}\n{body}\n</html>"

        return html

    def __repr__(self) -> str:
        name = "'" + self.name + "'" if self.name is not None else ""
        return "<StaticResource {name} {path} -> {directory!r}>".format(
            name=name, path=self._prefix, directory=self._directory
        )


class PrefixedSubAppResource(PrefixResource):
    def __init__(self, prefix: str, app: "Application") -> None:
        super().__init__(prefix)
        self._app = app
        self._add_prefix_to_resources(prefix)

    def add_prefix(self, prefix: str) -> None:
        super().add_prefix(prefix)
        self._add_prefix_to_resources(prefix)

    def _add_prefix_to_resources(self, prefix: str) -> None:
        router = self._app.router
        for resource in router.resources():
            # Since the canonical path of a resource is about
            # to change, we need to unindex it and then reindex
            router.unindex_resource(resource)
            resource.add_prefix(prefix)
            router.index_resource(resource)

    def url_for(self, *args: str, **kwargs: str) -> URL:
        raise RuntimeError(".url_for() is not supported by sub-application root")

    def get_info(self) -> _InfoDict:
        return {"app": self._app, "prefix": self._prefix}

    async def resolve(self, request: Request) -> _Resolve:
        match_info = await self._app.router.resolve(request)
        match_info.add_app(self._app)
        if isinstance(match_info.http_exception, HTTPMethodNotAllowed):
            methods = match_info.http_exception.allowed_methods
        else:
            methods = set()
        return match_info, methods

    def __len__(self) -> int:
        return len(self._app.router.routes())

    def __iter__(self) -> Iterator[AbstractRoute]:
        return iter(self._app.router.routes())

    def __repr__(self) -> str:
        return "<PrefixedSubAppResource {prefix} -> {app!r}>".format(
            prefix=self._prefix, app=self._app
        )


class AbstractRuleMatching(abc.ABC):
    @abc.abstractmethod  # pragma: no branch
    async def match(self, request: Request) -> bool:
        """Return bool if the request satisfies the criteria"""

    @abc.abstractmethod  # pragma: no branch
    def get_info(self) -> _InfoDict:
        """Return a dict with additional info useful for introspection"""

    @property
    @abc.abstractmethod  # pragma: no branch
    def canonical(self) -> str:
        """Return a str"""


class Domain(AbstractRuleMatching):
    re_part = re.compile(r"(?!-)[a-z\d-]{1,63}(?<!-)")

    def __init__(self, domain: str) -> None:
        super().__init__()
        self._domain = self.validation(domain)

    @property
    def canonical(self) -> str:
        return self._domain

    def validation(self, domain: str) -> str:
        if not isinstance(domain, str):
            raise TypeError("Domain must be str")
        domain = domain.rstrip(".").lower()
        if not domain:
            raise ValueError("Domain cannot be empty")
        elif "://" in domain:
            raise ValueError("Scheme not supported")
        url = URL("http://" + domain)
        assert url.raw_host is not None
        if not all(self.re_part.fullmatch(x) for x in url.raw_host.split(".")):
            raise ValueError("Domain not valid")
        if url.port == 80:
            return url.raw_host
        return f"{url.raw_host}:{url.port}"

    async def match(self, request: Request) -> bool:
        host = request.headers.get(hdrs.HOST)
        if not host:
            return False
        return self.match_domain(host)

    def match_domain(self, host: str) -> bool:
        return host.lower() == self._domain

    def get_info(self) -> _InfoDict:
        return {"domain": self._domain}


class MaskDomain(Domain):
    re_part = re.compile(r"(?!-)[a-z\d\*-]{1,63}(?<!-)")

    def __init__(self, domain: str) -> None:
        super().__init__(domain)
        mask = self._domain.replace(".", r"\.").replace("*", ".*")
        self._mask = re.compile(mask)

    @property
    def canonical(self) -> str:
        return self._mask.pattern

    def match_domain(self, host: str) -> bool:
        return self._mask.fullmatch(host) is not None


class MatchedSubAppResource(PrefixedSubAppResource):
    def __init__(self, rule: AbstractRuleMatching, app: "Application") -> None:
        AbstractResource.__init__(self)
        self._prefix = ""
        self._app = app
        self._rule = rule

    @property
    def canonical(self) -> str:
        return self._rule.canonical

    def get_info(self) -> _InfoDict:
        return {"app": self._app, "rule": self._rule}

    async def resolve(self, request: Request) -> _Resolve:
        if not await self._rule.match(request):
            return None, set()
        match_info = await self._app.router.resolve(request)
        match_info.add_app(self._app)
        if isinstance(match_info.http_exception, HTTPMethodNotAllowed):
            methods = match_info.http_exception.allowed_methods
        else:
            methods = set()
        return match_info, methods

    def __repr__(self) -> str:
        return f"<MatchedSubAppResource -> {self._app!r}>"


class ResourceRoute(AbstractRoute):
    """A route with resource"""

    def __init__(
        self,
        method: str,
        handler: Union[Handler, Type[AbstractView]],
        resource: AbstractResource,
        *,
        expect_handler: Optional[_ExpectHandler] = None,
    ) -> None:
        super().__init__(
            method, handler, expect_handler=expect_handler, resource=resource
        )

    def __repr__(self) -> str:
        return "<ResourceRoute [{method}] {resource} -> {handler!r}".format(
            method=self.method, resource=self._resource, handler=self.handler
        )

    @property
    def name(self) -> Optional[str]:
        if self._resource is None:
            return None
        return self._resource.name

    def url_for(self, *args: str, **kwargs: str) -> URL:
        """Construct url for route with additional params."""
        assert self._resource is not None
        return self._resource.url_for(*args, **kwargs)

    def get_info(self) -> _InfoDict:
        assert self._resource is not None
        return self._resource.get_info()


class SystemRoute(AbstractRoute):
    def __init__(self, http_exception: HTTPException) -> None:
        super().__init__(hdrs.METH_ANY, self._handle)
        self._http_exception = http_exception

    def url_for(self, *args: str, **kwargs: str) -> URL:
        raise RuntimeError(".url_for() is not allowed for SystemRoute")

    @property
    def name(self) -> Optional[str]:
        return None

    def get_info(self) -> _InfoDict:
        return {"http_exception": self._http_exception}

    async def _handle(self, request: Request) -> StreamResponse:
        raise self._http_exception

    @property
    def status(self) -> int:
        return self._http_exception.status

    @property
    def reason(self) -> str:
        return self._http_exception.reason

    def __repr__(self) -> str:
        return "<SystemRoute {self.status}: {self.reason}>".format(self=self)


class View(AbstractView):
    async def _iter(self) -> StreamResponse:
        if self.request.method not in hdrs.METH_ALL:
            self._raise_allowed_methods()
        method: Optional[Callable[[], Awaitable[StreamResponse]]]
        method = getattr(self, self.request.method.lower(), None)
        if method is None:
            self._raise_allowed_methods()
        ret = await method()
        assert isinstance(ret, StreamResponse)
        return ret

    def __await__(self) -> Generator[Any, None, StreamResponse]:
        return self._iter().__await__()

    def _raise_allowed_methods(self) -> NoReturn:
        allowed_methods = {m for m in hdrs.METH_ALL if hasattr(self, m.lower())}
        raise HTTPMethodNotAllowed(self.request.method, allowed_methods)


class ResourcesView(Sized, Iterable[AbstractResource], Container[AbstractResource]):
    def __init__(self, resources: List[AbstractResource]) -> None:
        self._resources = resources

    def __len__(self) -> int:
        return len(self._resources)

    def __iter__(self) -> Iterator[AbstractResource]:
        yield from self._resources

    def __contains__(self, resource: object) -> bool:
        return resource in self._resources


class RoutesView(Sized, Iterable[AbstractRoute], Container[AbstractRoute]):
    def __init__(self, resources: List[AbstractResource]):
        self._routes: List[AbstractRoute] = []
        for resource in resources:
            for route in resource:
                self._routes.append(route)

    def __len__(self) -> int:
        return len(self._routes)

    def __iter__(self) -> Iterator[AbstractRoute]:
        yield from self._routes

    def __contains__(self, route: object) -> bool:
        return route in self._routes


class UrlDispatcher(AbstractRouter, Mapping[str, AbstractResource]):

    NAME_SPLIT_RE = re.compile(r"[.:-]")

    def __init__(self) -> None:
        super().__init__()
        self._resources: List[AbstractResource] = []
        self._named_resources: Dict[str, AbstractResource] = {}
        self._resource_index: dict[str, list[AbstractResource]] = {}
        self._matched_sub_app_resources: List[MatchedSubAppResource] = []

    async def resolve(self, request: Request) -> UrlMappingMatchInfo:
        resource_index = self._resource_index
        allowed_methods: Set[str] = set()

        # Walk the url parts looking for candidates. We walk the url backwards
        # to ensure the most explicit match is found first. If there are multiple
        # candidates for a given url part because there are multiple resources
        # registered for the same canonical path, we resolve them in a linear
        # fashion to ensure registration order is respected.
        url_part = request.rel_url.path_safe
        while url_part:
            for candidate in resource_index.get(url_part, ()):
                match_dict, allowed = await candidate.resolve(request)
                if match_dict is not None:
                    return match_dict
                else:
                    allowed_methods |= allowed
            if url_part == "/":
                break
            url_part = url_part.rpartition("/")[0] or "/"

        #
        # We didn't find any candidates, so we'll try the matched sub-app
        # resources which we have to walk in a linear fashion because they
        # have regex/wildcard match rules and we cannot index them.
        #
        # For most cases we do not expect there to be many of these since
        # currently they are only added by `add_domain`
        #
        for resource in self._matched_sub_app_resources:
            match_dict, allowed = await resource.resolve(request)
            if match_dict is not None:
                return match_dict
            else:
                allowed_methods |= allowed

        if allowed_methods:
            return MatchInfoError(HTTPMethodNotAllowed(request.method, allowed_methods))

        return MatchInfoError(HTTPNotFound())

    def __iter__(self) -> Iterator[str]:
        return iter(self._named_resources)

    def __len__(self) -> int:
        return len(self._named_resources)

    def __contains__(self, resource: object) -> bool:
        return resource in self._named_resources

    def __getitem__(self, name: str) -> AbstractResource:
        return self._named_resources[name]

    def resources(self) -> ResourcesView:
        return ResourcesView(self._resources)

    def routes(self) -> RoutesView:
        return RoutesView(self._resources)

    def named_resources(self) -> Mapping[str, AbstractResource]:
        return MappingProxyType(self._named_resources)

    def register_resource(self, resource: AbstractResource) -> None:
        assert isinstance(
            resource, AbstractResource
        ), f"Instance of AbstractResource class is required, got {resource!r}"
        if self.frozen:
            raise RuntimeError("Cannot register a resource into frozen router.")

        name = resource.name

        if name is not None:
            parts = self.NAME_SPLIT_RE.split(name)
            for part in parts:
                if keyword.iskeyword(part):
                    raise ValueError(
                        f"Incorrect route name {name!r}, "
                        "python keywords cannot be used "
                        "for route name"
                    )
                if not part.isidentifier():
                    raise ValueError(
                        "Incorrect route name {!r}, "
                        "the name should be a sequence of "
                        "python identifiers separated "
                        "by dash, dot or column".format(name)
                    )
            if name in self._named_resources:
                raise ValueError(
                    "Duplicate {!r}, "
                    "already handled by {!r}".format(name, self._named_resources[name])
                )
            self._named_resources[name] = resource
        self._resources.append(resource)

        if isinstance(resource, MatchedSubAppResource):
            # We cannot index match sub-app resources because they have match rules
            self._matched_sub_app_resources.append(resource)
        else:
            self.index_resource(resource)

    def _get_resource_index_key(self, resource: AbstractResource) -> str:
        """Return a key to index the resource in the resource index."""
        if "{" in (index_key := resource.canonical):
            # strip at the first { to allow for variables, and than
            # rpartition at / to allow for variable parts in the path
            # For example if the canonical path is `/core/locations{tail:.*}`
            # the index key will be `/core` since index is based on the
            # url parts split by `/`
            index_key = index_key.partition("{")[0].rpartition("/")[0]
        return index_key.rstrip("/") or "/"

    def index_resource(self, resource: AbstractResource) -> None:
        """Add a resource to the resource index."""
        resource_key = self._get_resource_index_key(resource)
        # There may be multiple resources for a canonical path
        # so we keep them in a list to ensure that registration
        # order is respected.
        self._resource_index.setdefault(resource_key, []).append(resource)

    def unindex_resource(self, resource: AbstractResource) -> None:
        """Remove a resource from the resource index."""
        resource_key = self._get_resource_index_key(resource)
        self._resource_index[resource_key].remove(resource)

    def add_resource(self, path: str, *, name: Optional[str] = None) -> Resource:
        if path and not path.startswith("/"):
            raise ValueError("path should be started with / or be empty")
        # Reuse last added resource if path and name are the same
        if self._resources:
            resource = self._resources[-1]
            if resource.name == name and resource.raw_match(path):
                return cast(Resource, resource)
        if not ("{" in path or "}" in path or ROUTE_RE.search(path)):
            resource = PlainResource(path, name=name)
            self.register_resource(resource)
            return resource
        resource = DynamicResource(path, name=name)
        self.register_resource(resource)
        return resource

    def add_route(
        self,
        method: str,
        path: str,
        handler: Union[Handler, Type[AbstractView]],
        *,
        name: Optional[str] = None,
        expect_handler: Optional[_ExpectHandler] = None,
    ) -> AbstractRoute:
        resource = self.add_resource(path, name=name)
        return resource.add_route(method, handler, expect_handler=expect_handler)

    def add_static(
        self,
        prefix: str,
        path: PathLike,
        *,
        name: Optional[str] = None,
        expect_handler: Optional[_ExpectHandler] = None,
        chunk_size: int = 256 * 1024,
        show_index: bool = False,
        follow_symlinks: bool = False,
        append_version: bool = False,
    ) -> AbstractResource:
        """Add static files view.

        prefix - url prefix
        path - folder with files

        """
        assert prefix.startswith("/")
        if prefix.endswith("/"):
            prefix = prefix[:-1]
        resource = StaticResource(
            prefix,
            path,
            name=name,
            expect_handler=expect_handler,
            chunk_size=chunk_size,
            show_index=show_index,
            follow_symlinks=follow_symlinks,
            append_version=append_version,
        )
        self.register_resource(resource)
        return resource

    def add_head(self, path: str, handler: Handler, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method HEAD."""
        return self.add_route(hdrs.METH_HEAD, path, handler, **kwargs)

    def add_options(self, path: str, handler: Handler, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method OPTIONS."""
        return self.add_route(hdrs.METH_OPTIONS, path, handler, **kwargs)

    def add_get(
        self,
        path: str,
        handler: Handler,
        *,
        name: Optional[str] = None,
        allow_head: bool = True,
        **kwargs: Any,
    ) -> AbstractRoute:
        """Shortcut for add_route with method GET.

        If allow_head is true, another
        route is added allowing head requests to the same endpoint.
        """
        resource = self.add_resource(path, name=name)
        if allow_head:
            resource.add_route(hdrs.METH_HEAD, handler, **kwargs)
        return resource.add_route(hdrs.METH_GET, handler, **kwargs)

    def add_post(self, path: str, handler: Handler, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method POST."""
        return self.add_route(hdrs.METH_POST, path, handler, **kwargs)

    def add_put(self, path: str, handler: Handler, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method PUT."""
        return self.add_route(hdrs.METH_PUT, path, handler, **kwargs)

    def add_patch(self, path: str, handler: Handler, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method PATCH."""
        return self.add_route(hdrs.METH_PATCH, path, handler, **kwargs)

    def add_delete(self, path: str, handler: Handler, **kwargs: Any) -> AbstractRoute:
        """Shortcut for add_route with method DELETE."""
        return self.add_route(hdrs.METH_DELETE, path, handler, **kwargs)

    def add_view(
        self, path: str, handler: Type[AbstractView], **kwargs: Any
    ) -> AbstractRoute:
        """Shortcut for add_route with ANY methods for a class-based view."""
        return self.add_route(hdrs.METH_ANY, path, handler, **kwargs)

    def freeze(self) -> None:
        super().freeze()
        for resource in self._resources:
            resource.freeze()

    def add_routes(self, routes: Iterable[AbstractRouteDef]) -> List[AbstractRoute]:
        """Append routes to route table.

        Parameter should be a sequence of RouteDef objects.

        Returns a list of registered AbstractRoute instances.
        """
        registered_routes = []
        for route_def in routes:
            registered_routes.extend(route_def.register(self))
        return registered_routes


def _quote_path(value: str) -> str:
    if YARL_VERSION < (1, 6):
        value = value.replace("%", "%25")
    return URL.build(path=value, encoded=False).raw_path


def _unquote_path_safe(value: str) -> str:
    if "%" not in value:
        return value
    return value.replace("%2F", "/").replace("%25", "%")


def _requote_path(value: str) -> str:
    # Quote non-ascii characters and other characters which must be quoted,
    # but preserve existing %-sequences.
    result = _quote_path(value)
    if "%" in value:
        result = result.replace("%25", "%")
    return result

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\pydev_monkey.py ===
# License: EPL
import os
import re
import sys
from _pydev_bundle._pydev_saved_modules import threading
from _pydevd_bundle.pydevd_constants import (
    get_global_debugger,
    IS_WINDOWS,
    IS_JYTHON,
    get_current_thread_id,
    sorted_dict_repr,
    set_global_debugger,
    DebugInfoHolder,
    PYDEVD_USE_SYS_MONITORING,
    IS_PY313_OR_GREATER,
)
from _pydev_bundle import pydev_log
from contextlib import contextmanager
from _pydevd_bundle import pydevd_constants, pydevd_defaults
from _pydevd_bundle.pydevd_defaults import PydevdCustomization
import ast
from pathlib import Path

# ===============================================================================
# Things that are dependent on having the pydevd debugger
# ===============================================================================

pydev_src_dir = os.path.dirname(os.path.dirname(__file__))

_arg_patch = threading.local()


@contextmanager
def skip_subprocess_arg_patch():
    _arg_patch.apply_arg_patching = False
    try:
        yield
    finally:
        _arg_patch.apply_arg_patching = True


def _get_apply_arg_patching():
    return getattr(_arg_patch, "apply_arg_patching", True)


def _get_setup_updated_with_protocol_and_ppid(setup, is_exec=False):
    if setup is None:
        setup = {}
    setup = setup.copy()
    # Discard anything related to the protocol (we'll set the the protocol based on the one
    # currently set).
    setup.pop(pydevd_constants.ARGUMENT_HTTP_JSON_PROTOCOL, None)
    setup.pop(pydevd_constants.ARGUMENT_JSON_PROTOCOL, None)
    setup.pop(pydevd_constants.ARGUMENT_QUOTED_LINE_PROTOCOL, None)

    if not is_exec:
        # i.e.: The ppid for the subprocess is the current pid.
        # If it's an exec, keep it what it was.
        setup[pydevd_constants.ARGUMENT_PPID] = os.getpid()

    protocol = pydevd_constants.get_protocol()
    if protocol == pydevd_constants.HTTP_JSON_PROTOCOL:
        setup[pydevd_constants.ARGUMENT_HTTP_JSON_PROTOCOL] = True

    elif protocol == pydevd_constants.JSON_PROTOCOL:
        setup[pydevd_constants.ARGUMENT_JSON_PROTOCOL] = True

    elif protocol == pydevd_constants.QUOTED_LINE_PROTOCOL:
        setup[pydevd_constants.ARGUMENT_QUOTED_LINE_PROTOCOL] = True

    elif protocol == pydevd_constants.HTTP_PROTOCOL:
        setup[pydevd_constants.ARGUMENT_HTTP_PROTOCOL] = True

    else:
        pydev_log.debug("Unexpected protocol: %s", protocol)

    mode = pydevd_defaults.PydevdCustomization.DEBUG_MODE
    if mode:
        setup["debug-mode"] = mode

    preimport = pydevd_defaults.PydevdCustomization.PREIMPORT
    if preimport:
        setup["preimport"] = preimport

    if DebugInfoHolder.PYDEVD_DEBUG_FILE:
        setup["log-file"] = DebugInfoHolder.PYDEVD_DEBUG_FILE

    if DebugInfoHolder.DEBUG_TRACE_LEVEL:
        setup["log-level"] = DebugInfoHolder.DEBUG_TRACE_LEVEL

    return setup


class _LastFutureImportFinder(ast.NodeVisitor):
    def __init__(self):
        self.last_future_import_found = None

    def visit_ImportFrom(self, node):
        if node.module == "__future__":
            self.last_future_import_found = node


def _get_offset_from_line_col(code, line, col):
    offset = 0
    for i, line_contents in enumerate(code.splitlines(True)):
        if i == line:
            offset += col
            return offset
        else:
            offset += len(line_contents)

    return -1


def _separate_future_imports(code):
    """
    :param code:
        The code from where we want to get the __future__ imports (note that it's possible that
        there's no such entry).

    :return tuple(str, str):
        The return is a tuple(future_import, code).

        If the future import is not available a return such as ('', code) is given, otherwise, the
        future import will end with a ';' (so that it can be put right before the pydevd attach
        code).
    """
    try:
        node = ast.parse(code, "<string>", "exec")
        visitor = _LastFutureImportFinder()
        visitor.visit(node)

        if visitor.last_future_import_found is None:
            return "", code

        node = visitor.last_future_import_found
        offset = -1
        if hasattr(node, "end_lineno") and hasattr(node, "end_col_offset"):
            # Python 3.8 onwards has these (so, use when possible).
            line, col = node.end_lineno, node.end_col_offset
            offset = _get_offset_from_line_col(code, line - 1, col)  # ast lines are 1-based, make it 0-based.

        else:
            # end line/col not available, let's just find the offset and then search
            # for the alias from there.
            line, col = node.lineno, node.col_offset
            offset = _get_offset_from_line_col(code, line - 1, col)  # ast lines are 1-based, make it 0-based.
            if offset >= 0 and node.names:
                from_future_import_name = node.names[-1].name
                i = code.find(from_future_import_name, offset)
                if i < 0:
                    offset = -1
                else:
                    offset = i + len(from_future_import_name)

        if offset >= 0:
            for i in range(offset, len(code)):
                if code[i] in (" ", "\t", ";", ")", "\n"):
                    offset += 1
                else:
                    break

            future_import = code[:offset]
            code_remainder = code[offset:]

            # Now, put '\n' lines back into the code remainder (we had to search for
            # `\n)`, but in case we just got the `\n`, it should be at the remainder,
            # not at the future import.
            while future_import.endswith("\n"):
                future_import = future_import[:-1]
                code_remainder = "\n" + code_remainder

            if not future_import.endswith(";"):
                future_import += ";"
            return future_import, code_remainder

        # This shouldn't happen...
        pydev_log.info("Unable to find line %s in code:\n%r", line, code)
        return "", code

    except:
        pydev_log.exception("Error getting from __future__ imports from: %r", code)
        return "", code


def _get_python_c_args(host, port, code, args, setup):
    setup = _get_setup_updated_with_protocol_and_ppid(setup)

    # i.e.: We want to make the repr sorted so that it works in tests.
    setup_repr = setup if setup is None else (sorted_dict_repr(setup))

    future_imports = ""
    if "__future__" in code:
        # If the code has a __future__ import, we need to be able to strip the __future__
        # imports from the code and add them to the start of our code snippet.
        future_imports, code = _separate_future_imports(code)

    return (
        "%simport sys; sys.path.insert(0, r'%s'); import pydevd; pydevd.config(%r, %r); "
        "pydevd.settrace(host=%r, port=%s, suspend=False, trace_only_current_thread=False, patch_multiprocessing=True, access_token=%r, client_access_token=%r, __setup_holder__=%s); "
        "%s"
    ) % (
        future_imports,
        pydev_src_dir,
        pydevd_constants.get_protocol(),
        PydevdCustomization.DEBUG_MODE,
        host,
        port,
        setup.get("access-token"),
        setup.get("client-access-token"),
        setup_repr,
        code,
    )


def _get_host_port():
    import pydevd

    host, port = pydevd.dispatch()
    return host, port


def _is_managed_arg(arg):
    pydevd_py = _get_str_type_compatible(arg, "pydevd.py")
    if arg.endswith(pydevd_py):
        return True
    return False


def _on_forked_process(setup_tracing=True):
    pydevd_constants.after_fork()
    pydev_log.initialize_debug_stream(reinitialize=True)

    if setup_tracing:
        pydev_log.debug("pydevd on forked process: %s", os.getpid())

    import pydevd

    pydevd.threadingCurrentThread().__pydevd_main_thread = True
    pydevd.settrace_forked(setup_tracing=setup_tracing)


def _on_set_trace_for_new_thread(global_debugger):
    if global_debugger is not None:
        if not PYDEVD_USE_SYS_MONITORING:
            global_debugger.enable_tracing()


def _get_str_type_compatible(s, args):
    """
    This method converts `args` to byte/unicode based on the `s' type.
    """
    if isinstance(args, (list, tuple)):
        ret = []
        for arg in args:
            if type(s) == type(arg):
                ret.append(arg)
            else:
                if isinstance(s, bytes):
                    ret.append(arg.encode("utf-8"))
                else:
                    ret.append(arg.decode("utf-8"))
        return ret
    else:
        if type(s) == type(args):
            return args
        else:
            if isinstance(s, bytes):
                return args.encode("utf-8")
            else:
                return args.decode("utf-8")


# ===============================================================================
# Things related to monkey-patching
# ===============================================================================
def is_python(path):
    single_quote, double_quote = _get_str_type_compatible(path, ["'", '"'])

    if path.endswith(single_quote) or path.endswith(double_quote):
        path = path[1 : len(path) - 1]
    filename = os.path.basename(path).lower()
    for name in _get_str_type_compatible(filename, ["python", "jython", "pypy"]):
        if filename.find(name) != -1:
            return True

    return False


class InvalidTypeInArgsException(Exception):
    pass


def remove_quotes_from_args(args):
    if sys.platform == "win32":
        new_args = []

        for x in args:
            if isinstance(x, Path):
                x = str(x)
            else:
                if not isinstance(x, (bytes, str)):
                    raise InvalidTypeInArgsException(str(type(x)))

            double_quote, two_double_quotes = _get_str_type_compatible(x, ['"', '""'])

            if x != two_double_quotes:
                if len(x) > 1 and x.startswith(double_quote) and x.endswith(double_quote):
                    x = x[1:-1]

            new_args.append(x)
        return new_args
    else:
        new_args = []
        for x in args:
            if isinstance(x, Path):
                x = x.as_posix()
            else:
                if not isinstance(x, (bytes, str)):
                    raise InvalidTypeInArgsException(str(type(x)))
            new_args.append(x)

        return new_args


def quote_arg_win32(arg):
    fix_type = lambda x: _get_str_type_compatible(arg, x)

    # See if we need to quote at all - empty strings need quoting, as do strings
    # with whitespace or quotes in them. Backslashes do not need quoting.
    if arg and not set(arg).intersection(fix_type(' "\t\n\v')):
        return arg

    # Per https://docs.microsoft.com/en-us/windows/desktop/api/shellapi/nf-shellapi-commandlinetoargvw,
    # the standard way to interpret arguments in double quotes is as follows:
    #
    #       2N backslashes followed by a quotation mark produce N backslashes followed by
    #       begin/end quote. This does not become part of the parsed argument, but toggles
    #       the "in quotes" mode.
    #
    #       2N+1 backslashes followed by a quotation mark again produce N backslashes followed
    #       by a quotation mark literal ("). This does not toggle the "in quotes" mode.
    #
    #       N backslashes not followed by a quotation mark simply produce N backslashes.
    #
    # This code needs to do the reverse transformation, thus:
    #
    #       N backslashes followed by " produce 2N+1 backslashes followed by "
    #
    #       N backslashes at the end (i.e. where the closing " goes) produce 2N backslashes.
    #
    #       N backslashes in any other position remain as is.

    arg = re.sub(fix_type(r"(\\*)\""), fix_type(r'\1\1\\"'), arg)
    arg = re.sub(fix_type(r"(\\*)$"), fix_type(r"\1\1"), arg)
    return fix_type('"') + arg + fix_type('"')


def quote_args(args):
    if sys.platform == "win32":
        return list(map(quote_arg_win32, args))
    else:
        return args


def patch_args(args, is_exec=False):
    """
    :param list args:
        Arguments to patch.

    :param bool is_exec:
        If it's an exec, the current process will be replaced (this means we have
        to keep the same ppid).
    """
    try:
        pydev_log.debug("Patching args: %s", args)
        original_args = args
        try:
            unquoted_args = remove_quotes_from_args(args)
        except InvalidTypeInArgsException as e:
            pydev_log.info("Unable to monkey-patch subprocess arguments because a type found in the args is invalid: %s", e)
            return original_args

        # Internally we should reference original_args (if we want to return them) or unquoted_args
        # to add to the list which will be then quoted in the end.
        del args

        from pydevd import SetupHolder

        if not unquoted_args:
            return original_args

        if not is_python(unquoted_args[0]):
            pydev_log.debug("Process is not python, returning.")
            return original_args

        # Note: we create a copy as string to help with analyzing the arguments, but
        # the final list should have items from the unquoted_args as they were initially.
        args_as_str = _get_str_type_compatible("", unquoted_args)

        params_with_value_in_separate_arg = (
            "--check-hash-based-pycs",
            "--jit",  # pypy option
        )

        # All short switches may be combined together. The ones below require a value and the
        # value itself may be embedded in the arg.
        #
        # i.e.: Python accepts things as:
        #
        # python -OQold -qmtest
        #
        # Which is the same as:
        #
        # python -O -Q old -q -m test
        #
        # or even:
        #
        # python -OQold "-vcimport sys;print(sys)"
        #
        # Which is the same as:
        #
        # python -O -Q old -v -c "import sys;print(sys)"

        params_with_combinable_arg = set(("W", "X", "Q", "c", "m"))

        module_name = None
        before_module_flag = ""
        module_name_i_start = -1
        module_name_i_end = -1

        code = None
        code_i = -1
        code_i_end = -1
        code_flag = ""

        filename = None
        filename_i = -1

        ignore_next = True  # start ignoring the first (the first entry is the python executable)
        for i, arg_as_str in enumerate(args_as_str):
            if ignore_next:
                ignore_next = False
                continue

            if arg_as_str.startswith("-"):
                if arg_as_str == "-":
                    # Contents will be read from the stdin. This is not currently handled.
                    pydev_log.debug('Unable to fix arguments to attach debugger on subprocess when reading from stdin ("python ... -").')
                    return original_args

                if arg_as_str.startswith(params_with_value_in_separate_arg):
                    if arg_as_str in params_with_value_in_separate_arg:
                        ignore_next = True
                    continue

                break_out = False
                for j, c in enumerate(arg_as_str):
                    # i.e.: Python supports -X faulthandler as well as -Xfaulthandler
                    # (in one case we have to ignore the next and in the other we don't
                    # have to ignore it).
                    if c in params_with_combinable_arg:
                        remainder = arg_as_str[j + 1 :]
                        if not remainder:
                            ignore_next = True

                        if c == "m":
                            # i.e.: Something as
                            # python -qm test
                            # python -m test
                            # python -qmtest
                            before_module_flag = arg_as_str[:j]  # before_module_flag would then be "-q"
                            if before_module_flag == "-":
                                before_module_flag = ""
                            module_name_i_start = i
                            if not remainder:
                                module_name = unquoted_args[i + 1]
                                module_name_i_end = i + 1
                            else:
                                # i.e.: python -qmtest should provide 'test' as the module_name
                                module_name = unquoted_args[i][j + 1 :]
                                module_name_i_end = module_name_i_start
                            break_out = True
                            break

                        elif c == "c":
                            # i.e.: Something as
                            # python -qc "import sys"
                            # python -c "import sys"
                            # python "-qcimport sys"
                            code_flag = arg_as_str[: j + 1]  # code_flag would then be "-qc"

                            if not remainder:
                                # arg_as_str is something as "-qc", "import sys"
                                code = unquoted_args[i + 1]
                                code_i_end = i + 2
                            else:
                                # if arg_as_str is something as "-qcimport sys"
                                code = remainder  # code would be "import sys"
                                code_i_end = i + 1
                            code_i = i
                            break_out = True
                            break

                        else:
                            break

                if break_out:
                    break

            else:
                # It doesn't start with '-' and we didn't ignore this entry:
                # this means that this is the file to be executed.
                filename = unquoted_args[i]

                # Note that the filename is not validated here.
                # There are cases where even a .exe is valid (xonsh.exe):
                # https://github.com/microsoft/debugpy/issues/945
                # So, we should support whatever runpy.run_path
                # supports in this case.

                filename_i = i

                if _is_managed_arg(filename):  # no need to add pydevd twice
                    pydev_log.debug("Skipped monkey-patching as pydevd.py is in args already.")
                    return original_args

                break
        else:
            # We didn't find the filename (something is unexpected).
            pydev_log.debug("Unable to fix arguments to attach debugger on subprocess (filename not found).")
            return original_args

        if code_i != -1:
            host, port = _get_host_port()

            if port is not None:
                new_args = []
                new_args.extend(unquoted_args[:code_i])
                new_args.append(code_flag)
                new_args.append(_get_python_c_args(host, port, code, unquoted_args, SetupHolder.setup))
                new_args.extend(unquoted_args[code_i_end:])

                return quote_args(new_args)

        first_non_vm_index = max(filename_i, module_name_i_start)
        if first_non_vm_index == -1:
            pydev_log.debug("Unable to fix arguments to attach debugger on subprocess (could not resolve filename nor module name).")
            return original_args

        # Original args should be something as:
        # ['X:\\pysrc\\pydevd.py', '--multiprocess', '--print-in-debugger-startup',
        #  '--vm_type', 'python', '--client', '127.0.0.1', '--port', '56352', '--file', 'x:\\snippet1.py']
        from _pydevd_bundle.pydevd_command_line_handling import setup_to_argv

        new_args = []
        new_args.extend(unquoted_args[:first_non_vm_index])
        if before_module_flag:
            new_args.append(before_module_flag)

        add_module_at = len(new_args) + 1

        new_args.extend(
            setup_to_argv(
                _get_setup_updated_with_protocol_and_ppid(SetupHolder.setup, is_exec=is_exec), skip_names=set(("module", "cmd-line"))
            )
        )
        new_args.append("--file")

        if module_name is not None:
            assert module_name_i_start != -1
            assert module_name_i_end != -1
            # Always after 'pydevd' (i.e.: pydevd "--module" --multiprocess ...)
            new_args.insert(add_module_at, "--module")
            new_args.append(module_name)
            new_args.extend(unquoted_args[module_name_i_end + 1 :])

        elif filename is not None:
            assert filename_i != -1
            new_args.append(filename)
            new_args.extend(unquoted_args[filename_i + 1 :])

        else:
            raise AssertionError("Internal error (unexpected condition)")

        return quote_args(new_args)
    except:
        pydev_log.exception("Error patching args (debugger not attached to subprocess).")
        return original_args


def str_to_args_windows(args):
    # See https://docs.microsoft.com/en-us/cpp/c-language/parsing-c-command-line-arguments.
    #
    # Implemetation ported from DebugPlugin.parseArgumentsWindows:
    # https://github.com/eclipse/eclipse.platform.debug/blob/master/org.eclipse.debug.core/core/org/eclipse/debug/core/DebugPlugin.java

    result = []

    DEFAULT = 0
    ARG = 1
    IN_DOUBLE_QUOTE = 2

    state = DEFAULT
    backslashes = 0
    buf = ""

    args_len = len(args)
    for i in range(args_len):
        ch = args[i]
        if ch == "\\":
            backslashes += 1
            continue
        elif backslashes != 0:
            if ch == '"':
                while backslashes >= 2:
                    backslashes -= 2
                    buf += "\\"
                if backslashes == 1:
                    if state == DEFAULT:
                        state = ARG

                    buf += '"'
                    backslashes = 0
                    continue
                # else fall through to switch
            else:
                # false alarm, treat passed backslashes literally...
                if state == DEFAULT:
                    state = ARG

                while backslashes > 0:
                    backslashes -= 1
                    buf += "\\"
                # fall through to switch
        if ch in (" ", "\t"):
            if state == DEFAULT:
                # skip
                continue
            elif state == ARG:
                state = DEFAULT
                result.append(buf)
                buf = ""
                continue

        if state in (DEFAULT, ARG):
            if ch == '"':
                state = IN_DOUBLE_QUOTE
            else:
                state = ARG
                buf += ch

        elif state == IN_DOUBLE_QUOTE:
            if ch == '"':
                if i + 1 < args_len and args[i + 1] == '"':
                    # Undocumented feature in Windows:
                    # Two consecutive double quotes inside a double-quoted argument are interpreted as
                    # a single double quote.
                    buf += '"'
                    i += 1
                else:
                    state = ARG
            else:
                buf += ch

        else:
            raise RuntimeError("Illegal condition")

    if len(buf) > 0 or state != DEFAULT:
        result.append(buf)

    return result


def patch_arg_str_win(arg_str):
    args = str_to_args_windows(arg_str)
    # Fix https://youtrack.jetbrains.com/issue/PY-9767 (args may be empty)
    if not args or not is_python(args[0]):
        return arg_str
    arg_str = " ".join(patch_args(args))
    pydev_log.debug("New args: %s", arg_str)
    return arg_str


def monkey_patch_module(module, funcname, create_func):
    if hasattr(module, funcname):
        original_name = "original_" + funcname
        if not hasattr(module, original_name):
            setattr(module, original_name, getattr(module, funcname))
            setattr(module, funcname, create_func(original_name))


def monkey_patch_os(funcname, create_func):
    monkey_patch_module(os, funcname, create_func)


def warn_multiproc():
    pass  # TODO: Provide logging as messages to the IDE.
    # pydev_log.error_once(
    #     "pydev debugger: New process is launching (breakpoints won't work in the new process).\n"
    #     "pydev debugger: To debug that process please enable 'Attach to subprocess automatically while debugging?' option in the debugger settings.\n")
    #


def create_warn_multiproc(original_name):
    def new_warn_multiproc(*args, **kwargs):
        import os

        warn_multiproc()

        return getattr(os, original_name)(*args, **kwargs)

    return new_warn_multiproc


def create_execl(original_name):
    def new_execl(path, *args):
        """
        os.execl(path, arg0, arg1, ...)
        os.execle(path, arg0, arg1, ..., env)
        os.execlp(file, arg0, arg1, ...)
        os.execlpe(file, arg0, arg1, ..., env)
        """
        if _get_apply_arg_patching():
            args = patch_args(args, is_exec=True)
            send_process_created_message()
            send_process_about_to_be_replaced()

        return getattr(os, original_name)(path, *args)

    return new_execl


def create_execv(original_name):
    def new_execv(path, args):
        """
        os.execv(path, args)
        os.execvp(file, args)
        """
        if _get_apply_arg_patching():
            args = patch_args(args, is_exec=True)
            send_process_created_message()
            send_process_about_to_be_replaced()

        return getattr(os, original_name)(path, args)

    return new_execv


def create_execve(original_name):
    """
    os.execve(path, args, env)
    os.execvpe(file, args, env)
    """

    def new_execve(path, args, env):
        if _get_apply_arg_patching():
            args = patch_args(args, is_exec=True)
            send_process_created_message()
            send_process_about_to_be_replaced()

        return getattr(os, original_name)(path, args, env)

    return new_execve


def create_spawnl(original_name):
    def new_spawnl(mode, path, *args):
        """
        os.spawnl(mode, path, arg0, arg1, ...)
        os.spawnlp(mode, file, arg0, arg1, ...)
        """
        if _get_apply_arg_patching():
            args = patch_args(args)
            send_process_created_message()

        return getattr(os, original_name)(mode, path, *args)

    return new_spawnl


def create_spawnv(original_name):
    def new_spawnv(mode, path, args):
        """
        os.spawnv(mode, path, args)
        os.spawnvp(mode, file, args)
        """
        if _get_apply_arg_patching():
            args = patch_args(args)
            send_process_created_message()

        return getattr(os, original_name)(mode, path, args)

    return new_spawnv


def create_spawnve(original_name):
    """
    os.spawnve(mode, path, args, env)
    os.spawnvpe(mode, file, args, env)
    """

    def new_spawnve(mode, path, args, env):
        if _get_apply_arg_patching():
            args = patch_args(args)
            send_process_created_message()

        return getattr(os, original_name)(mode, path, args, env)

    return new_spawnve


def create_posix_spawn(original_name):
    """
    os.posix_spawn(executable, args, env, **kwargs)
    """

    def new_posix_spawn(executable, args, env, **kwargs):
        if _get_apply_arg_patching():
            args = patch_args(args)
            send_process_created_message()

        return getattr(os, original_name)(executable, args, env, **kwargs)

    return new_posix_spawn


def create_fork_exec(original_name):
    """
    _posixsubprocess.fork_exec(args, executable_list, close_fds, ... (13 more))
    """

    def new_fork_exec(args, *other_args):
        import _posixsubprocess  # @UnresolvedImport

        if _get_apply_arg_patching():
            args = patch_args(args)
            send_process_created_message()

        return getattr(_posixsubprocess, original_name)(args, *other_args)

    return new_fork_exec


def create_warn_fork_exec(original_name):
    """
    _posixsubprocess.fork_exec(args, executable_list, close_fds, ... (13 more))
    """

    def new_warn_fork_exec(*args):
        try:
            import _posixsubprocess

            warn_multiproc()
            return getattr(_posixsubprocess, original_name)(*args)
        except:
            pass

    return new_warn_fork_exec


def create_subprocess_fork_exec(original_name):
    """
    subprocess._fork_exec(args, executable_list, close_fds, ... (13 more))
    """

    def new_fork_exec(args, *other_args):
        import subprocess

        if _get_apply_arg_patching():
            args = patch_args(args)
            send_process_created_message()

        return getattr(subprocess, original_name)(args, *other_args)

    return new_fork_exec


def create_subprocess_warn_fork_exec(original_name):
    """
    subprocess._fork_exec(args, executable_list, close_fds, ... (13 more))
    """

    def new_warn_fork_exec(*args):
        try:
            import subprocess

            warn_multiproc()
            return getattr(subprocess, original_name)(*args)
        except:
            pass

    return new_warn_fork_exec


def create_CreateProcess(original_name):
    """
    CreateProcess(*args, **kwargs)
    """

    def new_CreateProcess(app_name, cmd_line, *args):
        try:
            import _subprocess
        except ImportError:
            import _winapi as _subprocess

        if _get_apply_arg_patching():
            cmd_line = patch_arg_str_win(cmd_line)
            send_process_created_message()

        return getattr(_subprocess, original_name)(app_name, cmd_line, *args)

    return new_CreateProcess


def create_CreateProcessWarnMultiproc(original_name):
    """
    CreateProcess(*args, **kwargs)
    """

    def new_CreateProcess(*args):
        try:
            import _subprocess
        except ImportError:
            import _winapi as _subprocess
        warn_multiproc()
        return getattr(_subprocess, original_name)(*args)

    return new_CreateProcess


def create_fork(original_name):
    def new_fork():
        # A simple fork will result in a new python process
        is_new_python_process = True
        frame = sys._getframe()

        apply_arg_patch = _get_apply_arg_patching()

        is_subprocess_fork = False
        while frame is not None:
            if frame.f_code.co_name == "_execute_child" and "subprocess" in frame.f_code.co_filename:
                is_subprocess_fork = True
                # If we're actually in subprocess.Popen creating a child, it may
                # result in something which is not a Python process, (so, we
                # don't want to connect with it in the forked version).
                executable = frame.f_locals.get("executable")
                if executable is not None:
                    is_new_python_process = False
                    if is_python(executable):
                        is_new_python_process = True
                break

            frame = frame.f_back
        frame = None  # Just make sure we don't hold on to it.

        protocol = pydevd_constants.get_protocol()
        debug_mode = PydevdCustomization.DEBUG_MODE

        child_process = getattr(os, original_name)()  # fork
        if not child_process:
            if is_new_python_process:
                PydevdCustomization.DEFAULT_PROTOCOL = protocol
                PydevdCustomization.DEBUG_MODE = debug_mode
                _on_forked_process(setup_tracing=apply_arg_patch and not is_subprocess_fork)
            else:
                set_global_debugger(None)
        else:
            if is_new_python_process:
                send_process_created_message()
        return child_process

    return new_fork


def send_process_created_message():
    py_db = get_global_debugger()
    if py_db is not None:
        py_db.send_process_created_message()


def send_process_about_to_be_replaced():
    py_db = get_global_debugger()
    if py_db is not None:
        py_db.send_process_about_to_be_replaced()


def patch_new_process_functions():
    # os.execl(path, arg0, arg1, ...)
    # os.execle(path, arg0, arg1, ..., env)
    # os.execlp(file, arg0, arg1, ...)
    # os.execlpe(file, arg0, arg1, ..., env)
    # os.execv(path, args)
    # os.execve(path, args, env)
    # os.execvp(file, args)
    # os.execvpe(file, args, env)
    monkey_patch_os("execl", create_execl)
    monkey_patch_os("execle", create_execl)
    monkey_patch_os("execlp", create_execl)
    monkey_patch_os("execlpe", create_execl)
    monkey_patch_os("execv", create_execv)
    monkey_patch_os("execve", create_execve)
    monkey_patch_os("execvp", create_execv)
    monkey_patch_os("execvpe", create_execve)

    # os.spawnl(mode, path, ...)
    # os.spawnle(mode, path, ..., env)
    # os.spawnlp(mode, file, ...)
    # os.spawnlpe(mode, file, ..., env)
    # os.spawnv(mode, path, args)
    # os.spawnve(mode, path, args, env)
    # os.spawnvp(mode, file, args)
    # os.spawnvpe(mode, file, args, env)

    monkey_patch_os("spawnl", create_spawnl)
    monkey_patch_os("spawnle", create_spawnl)
    monkey_patch_os("spawnlp", create_spawnl)
    monkey_patch_os("spawnlpe", create_spawnl)
    monkey_patch_os("spawnv", create_spawnv)
    monkey_patch_os("spawnve", create_spawnve)
    monkey_patch_os("spawnvp", create_spawnv)
    monkey_patch_os("spawnvpe", create_spawnve)
    monkey_patch_os("posix_spawn", create_posix_spawn)

    if not IS_WINDOWS:
        monkey_patch_os("posix_spawnp", create_posix_spawn)

    if not IS_JYTHON:
        if not IS_WINDOWS:
            monkey_patch_os("fork", create_fork)
            try:
                import _posixsubprocess

                monkey_patch_module(_posixsubprocess, "fork_exec", create_fork_exec)
            except ImportError:
                pass

            try:
                import subprocess

                monkey_patch_module(subprocess, "_fork_exec", create_subprocess_fork_exec)
            except AttributeError:
                pass
        else:
            # Windows
            try:
                import _subprocess
            except ImportError:
                import _winapi as _subprocess
            monkey_patch_module(_subprocess, "CreateProcess", create_CreateProcess)


def patch_new_process_functions_with_warning():
    monkey_patch_os("execl", create_warn_multiproc)
    monkey_patch_os("execle", create_warn_multiproc)
    monkey_patch_os("execlp", create_warn_multiproc)
    monkey_patch_os("execlpe", create_warn_multiproc)
    monkey_patch_os("execv", create_warn_multiproc)
    monkey_patch_os("execve", create_warn_multiproc)
    monkey_patch_os("execvp", create_warn_multiproc)
    monkey_patch_os("execvpe", create_warn_multiproc)
    monkey_patch_os("spawnl", create_warn_multiproc)
    monkey_patch_os("spawnle", create_warn_multiproc)
    monkey_patch_os("spawnlp", create_warn_multiproc)
    monkey_patch_os("spawnlpe", create_warn_multiproc)
    monkey_patch_os("spawnv", create_warn_multiproc)
    monkey_patch_os("spawnve", create_warn_multiproc)
    monkey_patch_os("spawnvp", create_warn_multiproc)
    monkey_patch_os("spawnvpe", create_warn_multiproc)
    monkey_patch_os("posix_spawn", create_warn_multiproc)

    if not IS_JYTHON:
        if not IS_WINDOWS:
            monkey_patch_os("fork", create_warn_multiproc)
            try:
                import _posixsubprocess

                monkey_patch_module(_posixsubprocess, "fork_exec", create_warn_fork_exec)
            except ImportError:
                pass

            try:
                import subprocess

                monkey_patch_module(subprocess, "_fork_exec", create_subprocess_warn_fork_exec)
            except AttributeError:
                pass

        else:
            # Windows
            try:
                import _subprocess
            except ImportError:
                import _winapi as _subprocess
            monkey_patch_module(_subprocess, "CreateProcess", create_CreateProcessWarnMultiproc)


class _NewThreadStartupWithTrace:
    def __init__(self, original_func, args, kwargs):
        self.original_func = original_func
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        # We monkey-patch the thread creation so that this function is called in the new thread. At this point
        # we notify of its creation and start tracing it.
        py_db = get_global_debugger()

        thread_id = None
        if py_db is not None:
            # Note: if this is a thread from threading.py, we're too early in the boostrap process (because we mocked
            # the start_new_thread internal machinery and thread._bootstrap has not finished), so, the code below needs
            # to make sure that we use the current thread bound to the original function and not use
            # threading.current_thread() unless we're sure it's a dummy thread.
            t = getattr(self.original_func, "__self__", getattr(self.original_func, "im_self", None))
            if not isinstance(t, threading.Thread):
                # This is not a threading.Thread but a Dummy thread (so, get it as a dummy thread using
                # currentThread).
                t = threading.current_thread()

            if not getattr(t, "is_pydev_daemon_thread", False):
                thread_id = get_current_thread_id(t)
                py_db.notify_thread_created(thread_id, t)
                _on_set_trace_for_new_thread(py_db)

            if getattr(py_db, "thread_analyser", None) is not None:
                try:
                    from _pydevd_bundle.pydevd_concurrency_analyser.pydevd_concurrency_logger import log_new_thread

                    log_new_thread(py_db, t)
                except:
                    sys.stderr.write("Failed to detect new thread for visualization")
        try:
            ret = self.original_func(*self.args, **self.kwargs)
        finally:
            if thread_id is not None:
                if py_db is not None:
                    # At thread shutdown we only have pydevd-related code running (which shouldn't
                    # be tracked).
                    py_db.disable_tracing()
                    py_db.notify_thread_not_alive(thread_id)

        return ret


class _NewThreadStartupWithoutTrace:
    def __init__(self, original_func, args, kwargs):
        self.original_func = original_func
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        return self.original_func(*self.args, **self.kwargs)


_UseNewThreadStartup = _NewThreadStartupWithTrace


def _get_threading_modules_to_patch():
    threading_modules_to_patch = []

    try:
        import thread as _thread
    except:
        import _thread
    threading_modules_to_patch.append(_thread)
    threading_modules_to_patch.append(threading)

    return threading_modules_to_patch


threading_modules_to_patch = _get_threading_modules_to_patch()


def patch_thread_module(thread_module):
    # Note: this is needed not just for the tracing, but to have an early way to
    # notify that a thread was created (i.e.: tests_python.test_debugger_json.test_case_started_exited_threads_protocol)
    start_thread_attrs = ["_start_new_thread", "start_new_thread", "start_new"]
    start_joinable_attrs = ["start_joinable_thread", "_start_joinable_thread"]
    check = start_thread_attrs + start_joinable_attrs

    replace_attrs = []
    for attr in check:
        if hasattr(thread_module, attr):
            replace_attrs.append(attr)

    if not replace_attrs:
        return

    for attr in replace_attrs:
        if attr in start_joinable_attrs:
            if getattr(thread_module, "_original_start_joinable_thread", None) is None:
                _original_start_joinable_thread = thread_module._original_start_joinable_thread = getattr(thread_module, attr)
            else:
                _original_start_joinable_thread = thread_module._original_start_joinable_thread
        else:
            if getattr(thread_module, "_original_start_new_thread", None) is None:
                _original_start_new_thread = thread_module._original_start_new_thread = getattr(thread_module, attr)
            else:
                _original_start_new_thread = thread_module._original_start_new_thread

    class ClassWithPydevStartNewThread:
        def pydev_start_new_thread(self, function, args=(), kwargs={}):
            """
            We need to replace the original thread_module.start_new_thread with this function so that threads started
            through it and not through the threading module are properly traced.
            """
            return _original_start_new_thread(_UseNewThreadStartup(function, args, kwargs), ())

    class ClassWithPydevStartJoinableThread:
        def pydev_start_joinable_thread(self, function, *args, **kwargs):
            """
            We need to replace the original thread_module._start_joinable_thread with this function so that threads started
            through it and not through the threading module are properly traced.
            """
            # Note: only handling the case from threading.py where the handle
            # and daemon flags are passed explicitly. This will fail if some user library
            # actually passes those without being a keyword argument!
            handle = kwargs.pop("handle", None)
            daemon = kwargs.pop("daemon", True)
            return _original_start_joinable_thread(_UseNewThreadStartup(function, args, kwargs), handle=handle, daemon=daemon)

    # This is a hack for the situation where the thread_module.start_new_thread is declared inside a class, such as the one below
    # class F(object):
    #    start_new_thread = thread_module.start_new_thread
    #
    #    def start_it(self):
    #        self.start_new_thread(self.function, args, kwargs)
    # So, if it's an already bound method, calling self.start_new_thread won't really receive a different 'self' -- it
    # does work in the default case because in builtins self isn't passed either.
    pydev_start_new_thread = ClassWithPydevStartNewThread().pydev_start_new_thread
    pydev_start_joinable_thread = ClassWithPydevStartJoinableThread().pydev_start_joinable_thread

    # We need to replace the original thread_module.start_new_thread with this function so that threads started through
    # it and not through the threading module are properly traced.
    for attr in replace_attrs:
        if attr in start_joinable_attrs:
            setattr(thread_module, attr, pydev_start_joinable_thread)
        else:
            setattr(thread_module, attr, pydev_start_new_thread)


def patch_thread_modules():
    for t in threading_modules_to_patch:
        patch_thread_module(t)


def undo_patch_thread_modules():
    for t in threading_modules_to_patch:
        try:
            t.start_new_thread = t._original_start_new_thread
        except:
            pass

        try:
            t.start_new = t._original_start_new_thread
        except:
            pass

        try:
            t._start_new_thread = t._original_start_new_thread
        except:
            pass

        try:
            t._start_joinable_thread = t._original_start_joinable_thread
        except:
            pass

        try:
            t.start_joinable_thread = t._original_start_joinable_thread
        except:
            pass


def disable_trace_thread_modules():
    """
    Can be used to temporarily stop tracing threads created with thread.start_new_thread.
    """
    global _UseNewThreadStartup
    _UseNewThreadStartup = _NewThreadStartupWithoutTrace


def enable_trace_thread_modules():
    """
    Can be used to start tracing threads created with thread.start_new_thread again.
    """
    global _UseNewThreadStartup
    _UseNewThreadStartup = _NewThreadStartupWithTrace


def get_original_start_new_thread(threading_module):
    try:
        return threading_module._original_start_new_thread
    except:
        return threading_module.start_new_thread