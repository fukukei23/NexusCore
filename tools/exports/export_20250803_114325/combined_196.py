
# === NexusCore/openenv\Lib\site-packages\fontTools\cu2qu\ufo.py ===
# Copyright 2015 Google Inc. All Rights Reserved.
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


"""Converts cubic bezier curves to quadratic splines.

Conversion is performed such that the quadratic splines keep the same end-curve
tangents as the original cubics. The approach is iterative, increasing the
number of segments for a spline until the error gets below a bound.

Respective curves from multiple fonts will be converted at once to ensure that
the resulting splines are interpolation-compatible.
"""

import logging
from fontTools.pens.basePen import AbstractPen
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.pens.reverseContourPen import ReverseContourPen

from . import curves_to_quadratic
from .errors import (
    UnequalZipLengthsError,
    IncompatibleSegmentNumberError,
    IncompatibleSegmentTypesError,
    IncompatibleGlyphsError,
    IncompatibleFontsError,
)


__all__ = ["fonts_to_quadratic", "font_to_quadratic"]

# The default approximation error below is a relative value (1/1000 of the EM square).
# Later on, we convert it to absolute font units by multiplying it by a font's UPEM
# (see fonts_to_quadratic).
DEFAULT_MAX_ERR = 0.001
CURVE_TYPE_LIB_KEY = "com.github.googlei18n.cu2qu.curve_type"

logger = logging.getLogger(__name__)


_zip = zip


def zip(*args):
    """Ensure each argument to zip has the same length. Also make sure a list is
    returned for python 2/3 compatibility.
    """

    if len(set(len(a) for a in args)) != 1:
        raise UnequalZipLengthsError(*args)
    return list(_zip(*args))


class GetSegmentsPen(AbstractPen):
    """Pen to collect segments into lists of points for conversion.

    Curves always include their initial on-curve point, so some points are
    duplicated between segments.
    """

    def __init__(self):
        self._last_pt = None
        self.segments = []

    def _add_segment(self, tag, *args):
        if tag in ["move", "line", "qcurve", "curve"]:
            self._last_pt = args[-1]
        self.segments.append((tag, args))

    def moveTo(self, pt):
        self._add_segment("move", pt)

    def lineTo(self, pt):
        self._add_segment("line", pt)

    def qCurveTo(self, *points):
        self._add_segment("qcurve", self._last_pt, *points)

    def curveTo(self, *points):
        self._add_segment("curve", self._last_pt, *points)

    def closePath(self):
        self._add_segment("close")

    def endPath(self):
        self._add_segment("end")

    def addComponent(self, glyphName, transformation):
        pass


def _get_segments(glyph):
    """Get a glyph's segments as extracted by GetSegmentsPen."""

    pen = GetSegmentsPen()
    # glyph.draw(pen)
    # We can't simply draw the glyph with the pen, but we must initialize the
    # PointToSegmentPen explicitly with outputImpliedClosingLine=True.
    # By default PointToSegmentPen does not outputImpliedClosingLine -- unless
    # last and first point on closed contour are duplicated. Because we are
    # converting multiple glyphs at the same time, we want to make sure
    # this function returns the same number of segments, whether or not
    # the last and first point overlap.
    # https://github.com/googlefonts/fontmake/issues/572
    # https://github.com/fonttools/fonttools/pull/1720
    pointPen = PointToSegmentPen(pen, outputImpliedClosingLine=True)
    glyph.drawPoints(pointPen)
    return pen.segments


def _set_segments(glyph, segments, reverse_direction):
    """Draw segments as extracted by GetSegmentsPen back to a glyph."""

    glyph.clearContours()
    pen = glyph.getPen()
    if reverse_direction:
        pen = ReverseContourPen(pen)
    for tag, args in segments:
        if tag == "move":
            pen.moveTo(*args)
        elif tag == "line":
            pen.lineTo(*args)
        elif tag == "curve":
            pen.curveTo(*args[1:])
        elif tag == "qcurve":
            pen.qCurveTo(*args[1:])
        elif tag == "close":
            pen.closePath()
        elif tag == "end":
            pen.endPath()
        else:
            raise AssertionError('Unhandled segment type "%s"' % tag)


def _segments_to_quadratic(segments, max_err, stats, all_quadratic=True):
    """Return quadratic approximations of cubic segments."""

    assert all(s[0] == "curve" for s in segments), "Non-cubic given to convert"

    new_points = curves_to_quadratic([s[1] for s in segments], max_err, all_quadratic)
    n = len(new_points[0])
    assert all(len(s) == n for s in new_points[1:]), "Converted incompatibly"

    spline_length = str(n - 2)
    stats[spline_length] = stats.get(spline_length, 0) + 1

    if all_quadratic or n == 3:
        return [("qcurve", p) for p in new_points]
    else:
        return [("curve", p) for p in new_points]


def _glyphs_to_quadratic(glyphs, max_err, reverse_direction, stats, all_quadratic=True):
    """Do the actual conversion of a set of compatible glyphs, after arguments
    have been set up.

    Return True if the glyphs were modified, else return False.
    """

    try:
        segments_by_location = zip(*[_get_segments(g) for g in glyphs])
    except UnequalZipLengthsError:
        raise IncompatibleSegmentNumberError(glyphs)
    if not any(segments_by_location):
        return False

    # always modify input glyphs if reverse_direction is True
    glyphs_modified = reverse_direction

    new_segments_by_location = []
    incompatible = {}
    for i, segments in enumerate(segments_by_location):
        tag = segments[0][0]
        if not all(s[0] == tag for s in segments[1:]):
            incompatible[i] = [s[0] for s in segments]
        elif tag == "curve":
            new_segments = _segments_to_quadratic(
                segments, max_err, stats, all_quadratic
            )
            if all_quadratic or new_segments != segments:
                glyphs_modified = True
            segments = new_segments
        new_segments_by_location.append(segments)

    if glyphs_modified:
        new_segments_by_glyph = zip(*new_segments_by_location)
        for glyph, new_segments in zip(glyphs, new_segments_by_glyph):
            _set_segments(glyph, new_segments, reverse_direction)

    if incompatible:
        raise IncompatibleSegmentTypesError(glyphs, segments=incompatible)
    return glyphs_modified


def glyphs_to_quadratic(
    glyphs, max_err=None, reverse_direction=False, stats=None, all_quadratic=True
):
    """Convert the curves of a set of compatible of glyphs to quadratic.

    All curves will be converted to quadratic at once, ensuring interpolation
    compatibility. If this is not required, calling glyphs_to_quadratic with one
    glyph at a time may yield slightly more optimized results.

    Return True if glyphs were modified, else return False.

    Raises IncompatibleGlyphsError if glyphs have non-interpolatable outlines.
    """
    if stats is None:
        stats = {}

    if not max_err:
        # assume 1000 is the default UPEM
        max_err = DEFAULT_MAX_ERR * 1000

    if isinstance(max_err, (list, tuple)):
        max_errors = max_err
    else:
        max_errors = [max_err] * len(glyphs)
    assert len(max_errors) == len(glyphs)

    return _glyphs_to_quadratic(
        glyphs, max_errors, reverse_direction, stats, all_quadratic
    )


def fonts_to_quadratic(
    fonts,
    max_err_em=None,
    max_err=None,
    reverse_direction=False,
    stats=None,
    dump_stats=False,
    remember_curve_type=True,
    all_quadratic=True,
):
    """Convert the curves of a collection of fonts to quadratic.

    All curves will be converted to quadratic at once, ensuring interpolation
    compatibility. If this is not required, calling fonts_to_quadratic with one
    font at a time may yield slightly more optimized results.

    Return the set of modified glyph names if any, else return an empty set.

    By default, cu2qu stores the curve type in the fonts' lib, under a private
    key "com.github.googlei18n.cu2qu.curve_type", and will not try to convert
    them again if the curve type is already set to "quadratic".
    Setting 'remember_curve_type' to False disables this optimization.

    Raises IncompatibleFontsError if same-named glyphs from different fonts
    have non-interpolatable outlines.
    """

    if remember_curve_type:
        curve_types = {f.lib.get(CURVE_TYPE_LIB_KEY, "cubic") for f in fonts}
        if len(curve_types) == 1:
            curve_type = next(iter(curve_types))
            if curve_type in ("quadratic", "mixed"):
                logger.info("Curves already converted to quadratic")
                return False
            elif curve_type == "cubic":
                pass  # keep converting
            else:
                raise NotImplementedError(curve_type)
        elif len(curve_types) > 1:
            # going to crash later if they do differ
            logger.warning("fonts may contain different curve types")

    if stats is None:
        stats = {}

    if max_err_em and max_err:
        raise TypeError("Only one of max_err and max_err_em can be specified.")
    if not (max_err_em or max_err):
        max_err_em = DEFAULT_MAX_ERR

    if isinstance(max_err, (list, tuple)):
        assert len(max_err) == len(fonts)
        max_errors = max_err
    elif max_err:
        max_errors = [max_err] * len(fonts)

    if isinstance(max_err_em, (list, tuple)):
        assert len(fonts) == len(max_err_em)
        max_errors = [f.info.unitsPerEm * e for f, e in zip(fonts, max_err_em)]
    elif max_err_em:
        max_errors = [f.info.unitsPerEm * max_err_em for f in fonts]

    modified = set()
    glyph_errors = {}
    for name in set().union(*(f.keys() for f in fonts)):
        glyphs = []
        cur_max_errors = []
        for font, error in zip(fonts, max_errors):
            if name in font:
                glyphs.append(font[name])
                cur_max_errors.append(error)
        try:
            if _glyphs_to_quadratic(
                glyphs, cur_max_errors, reverse_direction, stats, all_quadratic
            ):
                modified.add(name)
        except IncompatibleGlyphsError as exc:
            logger.error(exc)
            glyph_errors[name] = exc

    if glyph_errors:
        raise IncompatibleFontsError(glyph_errors)

    if modified and dump_stats:
        spline_lengths = sorted(stats.keys())
        logger.info(
            "New spline lengths: %s"
            % (", ".join("%s: %d" % (l, stats[l]) for l in spline_lengths))
        )

    if remember_curve_type:
        for font in fonts:
            curve_type = font.lib.get(CURVE_TYPE_LIB_KEY, "cubic")
            new_curve_type = "quadratic" if all_quadratic else "mixed"
            if curve_type != new_curve_type:
                font.lib[CURVE_TYPE_LIB_KEY] = new_curve_type
    return modified


def glyph_to_quadratic(glyph, **kwargs):
    """Convenience wrapper around glyphs_to_quadratic, for just one glyph.
    Return True if the glyph was modified, else return False.
    """

    return glyphs_to_quadratic([glyph], **kwargs)


def font_to_quadratic(font, **kwargs):
    """Convenience wrapper around fonts_to_quadratic, for just one font.
    Return the set of modified glyph names if any, else return empty set.
    """

    return fonts_to_quadratic([font], **kwargs)

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\configTools.py ===
"""
Code of the config system; not related to fontTools or fonts in particular.

The options that are specific to fontTools are in :mod:`fontTools.config`.

To create your own config system, you need to create an instance of
:class:`Options`, and a subclass of :class:`AbstractConfig` with its
``options`` class variable set to your instance of Options.

"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    Mapping,
    MutableMapping,
    Optional,
    Set,
    Union,
)


log = logging.getLogger(__name__)

__all__ = [
    "AbstractConfig",
    "ConfigAlreadyRegisteredError",
    "ConfigError",
    "ConfigUnknownOptionError",
    "ConfigValueParsingError",
    "ConfigValueValidationError",
    "Option",
    "Options",
]


class ConfigError(Exception):
    """Base exception for the config module."""


class ConfigAlreadyRegisteredError(ConfigError):
    """Raised when a module tries to register a configuration option that
    already exists.

    Should not be raised too much really, only when developing new fontTools
    modules.
    """

    def __init__(self, name):
        super().__init__(f"Config option {name} is already registered.")


class ConfigValueParsingError(ConfigError):
    """Raised when a configuration value cannot be parsed."""

    def __init__(self, name, value):
        super().__init__(
            f"Config option {name}: value cannot be parsed (given {repr(value)})"
        )


class ConfigValueValidationError(ConfigError):
    """Raised when a configuration value cannot be validated."""

    def __init__(self, name, value):
        super().__init__(
            f"Config option {name}: value is invalid (given {repr(value)})"
        )


class ConfigUnknownOptionError(ConfigError):
    """Raised when a configuration option is unknown."""

    def __init__(self, option_or_name):
        name = (
            f"'{option_or_name.name}' (id={id(option_or_name)})>"
            if isinstance(option_or_name, Option)
            else f"'{option_or_name}'"
        )
        super().__init__(f"Config option {name} is unknown")


# eq=False because Options are unique, not fungible objects
@dataclass(frozen=True, eq=False)
class Option:
    name: str
    """Unique name identifying the option (e.g. package.module:MY_OPTION)."""
    help: str
    """Help text for this option."""
    default: Any
    """Default value for this option."""
    parse: Callable[[str], Any]
    """Turn input (e.g. string) into proper type. Only when reading from file."""
    validate: Optional[Callable[[Any], bool]] = None
    """Return true if the given value is an acceptable value."""

    @staticmethod
    def parse_optional_bool(v: str) -> Optional[bool]:
        s = str(v).lower()
        if s in {"0", "no", "false"}:
            return False
        if s in {"1", "yes", "true"}:
            return True
        if s in {"auto", "none"}:
            return None
        raise ValueError("invalid optional bool: {v!r}")

    @staticmethod
    def validate_optional_bool(v: Any) -> bool:
        return v is None or isinstance(v, bool)


class Options(Mapping):
    """Registry of available options for a given config system.

    Define new options using the :meth:`register()` method.

    Access existing options using the Mapping interface.
    """

    __options: Dict[str, Option]

    def __init__(self, other: "Options" = None) -> None:
        self.__options = {}
        if other is not None:
            for option in other.values():
                self.register_option(option)

    def register(
        self,
        name: str,
        help: str,
        default: Any,
        parse: Callable[[str], Any],
        validate: Optional[Callable[[Any], bool]] = None,
    ) -> Option:
        """Create and register a new option."""
        return self.register_option(Option(name, help, default, parse, validate))

    def register_option(self, option: Option) -> Option:
        """Register a new option."""
        name = option.name
        if name in self.__options:
            raise ConfigAlreadyRegisteredError(name)
        self.__options[name] = option
        return option

    def is_registered(self, option: Option) -> bool:
        """Return True if the same option object is already registered."""
        return self.__options.get(option.name) is option

    def __getitem__(self, key: str) -> Option:
        return self.__options.__getitem__(key)

    def __iter__(self) -> Iterator[str]:
        return self.__options.__iter__()

    def __len__(self) -> int:
        return self.__options.__len__()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({{\n"
            + "".join(
                f"    {k!r}: Option(default={v.default!r}, ...),\n"
                for k, v in self.__options.items()
            )
            + "})"
        )


_USE_GLOBAL_DEFAULT = object()


class AbstractConfig(MutableMapping):
    """
    Create a set of config values, optionally pre-filled with values from
    the given dictionary or pre-existing config object.

    The class implements the MutableMapping protocol keyed by option name (`str`).
    For convenience its methods accept either Option or str as the key parameter.

    .. seealso:: :meth:`set()`

    This config class is abstract because it needs its ``options`` class
    var to be set to an instance of :class:`Options` before it can be
    instanciated and used.

    .. code:: python

        class MyConfig(AbstractConfig):
            options = Options()

        MyConfig.register_option( "test:option_name", "This is an option", 0, int, lambda v: isinstance(v, int))

        cfg = MyConfig({"test:option_name": 10})

    """

    options: ClassVar[Options]

    @classmethod
    def register_option(
        cls,
        name: str,
        help: str,
        default: Any,
        parse: Callable[[str], Any],
        validate: Optional[Callable[[Any], bool]] = None,
    ) -> Option:
        """Register an available option in this config system."""
        return cls.options.register(
            name, help=help, default=default, parse=parse, validate=validate
        )

    _values: Dict[str, Any]

    def __init__(
        self,
        values: Union[AbstractConfig, Dict[Union[Option, str], Any]] = {},
        parse_values: bool = False,
        skip_unknown: bool = False,
    ):
        self._values = {}
        values_dict = values._values if isinstance(values, AbstractConfig) else values
        for name, value in values_dict.items():
            self.set(name, value, parse_values, skip_unknown)

    def _resolve_option(self, option_or_name: Union[Option, str]) -> Option:
        if isinstance(option_or_name, Option):
            option = option_or_name
            if not self.options.is_registered(option):
                raise ConfigUnknownOptionError(option)
            return option
        elif isinstance(option_or_name, str):
            name = option_or_name
            try:
                return self.options[name]
            except KeyError:
                raise ConfigUnknownOptionError(name)
        else:
            raise TypeError(
                "expected Option or str, found "
                f"{type(option_or_name).__name__}: {option_or_name!r}"
            )

    def set(
        self,
        option_or_name: Union[Option, str],
        value: Any,
        parse_values: bool = False,
        skip_unknown: bool = False,
    ):
        """Set the value of an option.

        Args:
            * `option_or_name`: an `Option` object or its name (`str`).
            * `value`: the value to be assigned to given option.
            * `parse_values`: parse the configuration value from a string into
                its proper type, as per its `Option` object. The default
                behavior is to raise `ConfigValueValidationError` when the value
                is not of the right type. Useful when reading options from a
                file type that doesn't support as many types as Python.
            * `skip_unknown`: skip unknown configuration options. The default
                behaviour is to raise `ConfigUnknownOptionError`. Useful when
                reading options from a configuration file that has extra entries
                (e.g. for a later version of fontTools)
        """
        try:
            option = self._resolve_option(option_or_name)
        except ConfigUnknownOptionError as e:
            if skip_unknown:
                log.debug(str(e))
                return
            raise

        # Can be useful if the values come from a source that doesn't have
        # strict typing (.ini file? Terminal input?)
        if parse_values:
            try:
                value = option.parse(value)
            except Exception as e:
                raise ConfigValueParsingError(option.name, value) from e

        if option.validate is not None and not option.validate(value):
            raise ConfigValueValidationError(option.name, value)

        self._values[option.name] = value

    def get(
        self, option_or_name: Union[Option, str], default: Any = _USE_GLOBAL_DEFAULT
    ) -> Any:
        """
        Get the value of an option. The value which is returned is the first
        provided among:

        1. a user-provided value in the options's ``self._values`` dict
        2. a caller-provided default value to this method call
        3. the global default for the option provided in ``fontTools.config``

        This is to provide the ability to migrate progressively from config
        options passed as arguments to fontTools APIs to config options read
        from the current TTFont, e.g.

        .. code:: python

            def fontToolsAPI(font, some_option):
                value = font.cfg.get("someLib.module:SOME_OPTION", some_option)
                # use value

        That way, the function will work the same for users of the API that
        still pass the option to the function call, but will favour the new
        config mechanism if the given font specifies a value for that option.
        """
        option = self._resolve_option(option_or_name)
        if option.name in self._values:
            return self._values[option.name]
        if default is not _USE_GLOBAL_DEFAULT:
            return default
        return option.default

    def copy(self):
        return self.__class__(self._values)

    def __getitem__(self, option_or_name: Union[Option, str]) -> Any:
        return self.get(option_or_name)

    def __setitem__(self, option_or_name: Union[Option, str], value: Any) -> None:
        return self.set(option_or_name, value)

    def __delitem__(self, option_or_name: Union[Option, str]) -> None:
        option = self._resolve_option(option_or_name)
        del self._values[option.name]

    def __iter__(self) -> Iterable[str]:
        return self._values.__iter__()

    def __len__(self) -> int:
        return len(self._values)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self._values)})"

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\services\model_service\transports\grpc.py ===
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
import grpc  # type: ignore

from google.ai.generativelanguage_v1.types import model, model_service

from .base import DEFAULT_CLIENT_INFO, ModelServiceTransport


class ModelServiceGrpcTransport(ModelServiceTransport):
    """gRPC backend transport for ModelService.

    Provides methods for getting metadata information about
    Generative Models.

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
    def get_model(self) -> Callable[[model_service.GetModelRequest], model.Model]:
        r"""Return a callable for the get model method over gRPC.

        Gets information about a specific Model.

        Returns:
            Callable[[~.GetModelRequest],
                    ~.Model]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_model" not in self._stubs:
            self._stubs["get_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1.ModelService/GetModel",
                request_serializer=model_service.GetModelRequest.serialize,
                response_deserializer=model.Model.deserialize,
            )
        return self._stubs["get_model"]

    @property
    def list_models(
        self,
    ) -> Callable[[model_service.ListModelsRequest], model_service.ListModelsResponse]:
        r"""Return a callable for the list models method over gRPC.

        Lists models available through the API.

        Returns:
            Callable[[~.ListModelsRequest],
                    ~.ListModelsResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_models" not in self._stubs:
            self._stubs["list_models"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1.ModelService/ListModels",
                request_serializer=model_service.ListModelsRequest.serialize,
                response_deserializer=model_service.ListModelsResponse.deserialize,
            )
        return self._stubs["list_models"]

    def close(self):
        self.grpc_channel.close()

    @property
    def cancel_operation(
        self,
    ) -> Callable[[operations_pb2.CancelOperationRequest], None]:
        r"""Return a callable for the cancel_operation method over gRPC."""
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "cancel_operation" not in self._stubs:
            self._stubs["cancel_operation"] = self.grpc_channel.unary_unary(
                "/google.longrunning.Operations/CancelOperation",
                request_serializer=operations_pb2.CancelOperationRequest.SerializeToString,
                response_deserializer=None,
            )
        return self._stubs["cancel_operation"]

    @property
    def get_operation(
        self,
    ) -> Callable[[operations_pb2.GetOperationRequest], operations_pb2.Operation]:
        r"""Return a callable for the get_operation method over gRPC."""
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_operation" not in self._stubs:
            self._stubs["get_operation"] = self.grpc_channel.unary_unary(
                "/google.longrunning.Operations/GetOperation",
                request_serializer=operations_pb2.GetOperationRequest.SerializeToString,
                response_deserializer=operations_pb2.Operation.FromString,
            )
        return self._stubs["get_operation"]

    @property
    def list_operations(
        self,
    ) -> Callable[
        [operations_pb2.ListOperationsRequest], operations_pb2.ListOperationsResponse
    ]:
        r"""Return a callable for the list_operations method over gRPC."""
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_operations" not in self._stubs:
            self._stubs["list_operations"] = self.grpc_channel.unary_unary(
                "/google.longrunning.Operations/ListOperations",
                request_serializer=operations_pb2.ListOperationsRequest.SerializeToString,
                response_deserializer=operations_pb2.ListOperationsResponse.FromString,
            )
        return self._stubs["list_operations"]

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("ModelServiceGrpcTransport",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\file_service\transports\grpc.py ===
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

from google.ai.generativelanguage_v1beta.types import file, file_service

from .base import DEFAULT_CLIENT_INFO, FileServiceTransport


class FileServiceGrpcTransport(FileServiceTransport):
    """gRPC backend transport for FileService.

    An API for uploading and managing files.

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
    def create_file(
        self,
    ) -> Callable[[file_service.CreateFileRequest], file_service.CreateFileResponse]:
        r"""Return a callable for the create file method over gRPC.

        Creates a ``File``.

        Returns:
            Callable[[~.CreateFileRequest],
                    ~.CreateFileResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_file" not in self._stubs:
            self._stubs["create_file"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.FileService/CreateFile",
                request_serializer=file_service.CreateFileRequest.serialize,
                response_deserializer=file_service.CreateFileResponse.deserialize,
            )
        return self._stubs["create_file"]

    @property
    def list_files(
        self,
    ) -> Callable[[file_service.ListFilesRequest], file_service.ListFilesResponse]:
        r"""Return a callable for the list files method over gRPC.

        Lists the metadata for ``File``\ s owned by the requesting
        project.

        Returns:
            Callable[[~.ListFilesRequest],
                    ~.ListFilesResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_files" not in self._stubs:
            self._stubs["list_files"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.FileService/ListFiles",
                request_serializer=file_service.ListFilesRequest.serialize,
                response_deserializer=file_service.ListFilesResponse.deserialize,
            )
        return self._stubs["list_files"]

    @property
    def get_file(self) -> Callable[[file_service.GetFileRequest], file.File]:
        r"""Return a callable for the get file method over gRPC.

        Gets the metadata for the given ``File``.

        Returns:
            Callable[[~.GetFileRequest],
                    ~.File]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_file" not in self._stubs:
            self._stubs["get_file"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.FileService/GetFile",
                request_serializer=file_service.GetFileRequest.serialize,
                response_deserializer=file.File.deserialize,
            )
        return self._stubs["get_file"]

    @property
    def delete_file(
        self,
    ) -> Callable[[file_service.DeleteFileRequest], empty_pb2.Empty]:
        r"""Return a callable for the delete file method over gRPC.

        Deletes the ``File``.

        Returns:
            Callable[[~.DeleteFileRequest],
                    ~.Empty]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_file" not in self._stubs:
            self._stubs["delete_file"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.FileService/DeleteFile",
                request_serializer=file_service.DeleteFileRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_file"]

    def close(self):
        self.grpc_channel.close()

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("FileServiceGrpcTransport",)

# === NexusCore/openenv\Lib\site-packages\nltk\classify\decisiontree.py ===
# Natural Language Toolkit: Decision Tree Classifiers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A classifier model that decides which label to assign to a token on
the basis of a tree structure, where branches correspond to conditions
on feature values, and leaves correspond to label assignments.
"""

from collections import defaultdict

from nltk.classify.api import ClassifierI
from nltk.probability import FreqDist, MLEProbDist, entropy


class DecisionTreeClassifier(ClassifierI):
    def __init__(self, label, feature_name=None, decisions=None, default=None):
        """
        :param label: The most likely label for tokens that reach
            this node in the decision tree.  If this decision tree
            has no children, then this label will be assigned to
            any token that reaches this decision tree.
        :param feature_name: The name of the feature that this
            decision tree selects for.
        :param decisions: A dictionary mapping from feature values
            for the feature identified by ``feature_name`` to
            child decision trees.
        :param default: The child that will be used if the value of
            feature ``feature_name`` does not match any of the keys in
            ``decisions``.  This is used when constructing binary
            decision trees.
        """
        self._label = label
        self._fname = feature_name
        self._decisions = decisions
        self._default = default

    def labels(self):
        labels = [self._label]
        if self._decisions is not None:
            for dt in self._decisions.values():
                labels.extend(dt.labels())
        if self._default is not None:
            labels.extend(self._default.labels())
        return list(set(labels))

    def classify(self, featureset):
        # Decision leaf:
        if self._fname is None:
            return self._label

        # Decision tree:
        fval = featureset.get(self._fname)
        if fval in self._decisions:
            return self._decisions[fval].classify(featureset)
        elif self._default is not None:
            return self._default.classify(featureset)
        else:
            return self._label

    def error(self, labeled_featuresets):
        errors = 0
        for featureset, label in labeled_featuresets:
            if self.classify(featureset) != label:
                errors += 1
        return errors / len(labeled_featuresets)

    def pretty_format(self, width=70, prefix="", depth=4):
        """
        Return a string containing a pretty-printed version of this
        decision tree.  Each line in this string corresponds to a
        single decision tree node or leaf, and indentation is used to
        display the structure of the decision tree.
        """
        # [xx] display default!!
        if self._fname is None:
            n = width - len(prefix) - 15
            return "{}{} {}\n".format(prefix, "." * n, self._label)
        s = ""
        for i, (fval, result) in enumerate(
            sorted(
                self._decisions.items(),
                key=lambda item: (item[0] in [None, False, True], str(item[0]).lower()),
            )
        ):
            hdr = f"{prefix}{self._fname}={fval}? "
            n = width - 15 - len(hdr)
            s += "{}{} {}\n".format(hdr, "." * (n), result._label)
            if result._fname is not None and depth > 1:
                s += result.pretty_format(width, prefix + "  ", depth - 1)
        if self._default is not None:
            n = width - len(prefix) - 21
            s += "{}else: {} {}\n".format(prefix, "." * n, self._default._label)
            if self._default._fname is not None and depth > 1:
                s += self._default.pretty_format(width, prefix + "  ", depth - 1)
        return s

    def pseudocode(self, prefix="", depth=4):
        """
        Return a string representation of this decision tree that
        expresses the decisions it makes as a nested set of pseudocode
        if statements.
        """
        if self._fname is None:
            return f"{prefix}return {self._label!r}\n"
        s = ""
        for fval, result in sorted(
            self._decisions.items(),
            key=lambda item: (item[0] in [None, False, True], str(item[0]).lower()),
        ):
            s += f"{prefix}if {self._fname} == {fval!r}: "
            if result._fname is not None and depth > 1:
                s += "\n" + result.pseudocode(prefix + "  ", depth - 1)
            else:
                s += f"return {result._label!r}\n"
        if self._default is not None:
            if len(self._decisions) == 1:
                s += "{}if {} != {!r}: ".format(
                    prefix, self._fname, list(self._decisions.keys())[0]
                )
            else:
                s += f"{prefix}else: "
            if self._default._fname is not None and depth > 1:
                s += "\n" + self._default.pseudocode(prefix + "  ", depth - 1)
            else:
                s += f"return {self._default._label!r}\n"
        return s

    def __str__(self):
        return self.pretty_format()

    @staticmethod
    def train(
        labeled_featuresets,
        entropy_cutoff=0.05,
        depth_cutoff=100,
        support_cutoff=10,
        binary=False,
        feature_values=None,
        verbose=False,
    ):
        """
        :param binary: If true, then treat all feature/value pairs as
            individual binary features, rather than using a single n-way
            branch for each feature.
        """
        # Collect a list of all feature names.
        feature_names = set()
        for featureset, label in labeled_featuresets:
            for fname in featureset:
                feature_names.add(fname)

        # Collect a list of the values each feature can take.
        if feature_values is None and binary:
            feature_values = defaultdict(set)
            for featureset, label in labeled_featuresets:
                for fname, fval in featureset.items():
                    feature_values[fname].add(fval)

        # Start with a stump.
        if not binary:
            tree = DecisionTreeClassifier.best_stump(
                feature_names, labeled_featuresets, verbose
            )
        else:
            tree = DecisionTreeClassifier.best_binary_stump(
                feature_names, labeled_featuresets, feature_values, verbose
            )

        # Refine the stump.
        tree.refine(
            labeled_featuresets,
            entropy_cutoff,
            depth_cutoff - 1,
            support_cutoff,
            binary,
            feature_values,
            verbose,
        )

        # Return it
        return tree

    @staticmethod
    def leaf(labeled_featuresets):
        label = FreqDist(label for (featureset, label) in labeled_featuresets).max()
        return DecisionTreeClassifier(label)

    @staticmethod
    def stump(feature_name, labeled_featuresets):
        label = FreqDist(label for (featureset, label) in labeled_featuresets).max()

        # Find the best label for each value.
        freqs = defaultdict(FreqDist)  # freq(label|value)
        for featureset, label in labeled_featuresets:
            feature_value = featureset.get(feature_name)
            freqs[feature_value][label] += 1

        decisions = {val: DecisionTreeClassifier(freqs[val].max()) for val in freqs}
        return DecisionTreeClassifier(label, feature_name, decisions)

    def refine(
        self,
        labeled_featuresets,
        entropy_cutoff,
        depth_cutoff,
        support_cutoff,
        binary=False,
        feature_values=None,
        verbose=False,
    ):
        if len(labeled_featuresets) <= support_cutoff:
            return
        if self._fname is None:
            return
        if depth_cutoff <= 0:
            return
        for fval in self._decisions:
            fval_featuresets = [
                (featureset, label)
                for (featureset, label) in labeled_featuresets
                if featureset.get(self._fname) == fval
            ]

            label_freqs = FreqDist(label for (featureset, label) in fval_featuresets)
            if entropy(MLEProbDist(label_freqs)) > entropy_cutoff:
                self._decisions[fval] = DecisionTreeClassifier.train(
                    fval_featuresets,
                    entropy_cutoff,
                    depth_cutoff,
                    support_cutoff,
                    binary,
                    feature_values,
                    verbose,
                )
        if self._default is not None:
            default_featuresets = [
                (featureset, label)
                for (featureset, label) in labeled_featuresets
                if featureset.get(self._fname) not in self._decisions
            ]
            label_freqs = FreqDist(label for (featureset, label) in default_featuresets)
            if entropy(MLEProbDist(label_freqs)) > entropy_cutoff:
                self._default = DecisionTreeClassifier.train(
                    default_featuresets,
                    entropy_cutoff,
                    depth_cutoff,
                    support_cutoff,
                    binary,
                    feature_values,
                    verbose,
                )

    @staticmethod
    def best_stump(feature_names, labeled_featuresets, verbose=False):
        best_stump = DecisionTreeClassifier.leaf(labeled_featuresets)
        best_error = best_stump.error(labeled_featuresets)
        for fname in feature_names:
            stump = DecisionTreeClassifier.stump(fname, labeled_featuresets)
            stump_error = stump.error(labeled_featuresets)
            if stump_error < best_error:
                best_error = stump_error
                best_stump = stump
        if verbose:
            print(
                "best stump for {:6d} toks uses {:20} err={:6.4f}".format(
                    len(labeled_featuresets), best_stump._fname, best_error
                )
            )
        return best_stump

    @staticmethod
    def binary_stump(feature_name, feature_value, labeled_featuresets):
        label = FreqDist(label for (featureset, label) in labeled_featuresets).max()

        # Find the best label for each value.
        pos_fdist = FreqDist()
        neg_fdist = FreqDist()
        for featureset, label in labeled_featuresets:
            if featureset.get(feature_name) == feature_value:
                pos_fdist[label] += 1
            else:
                neg_fdist[label] += 1

        decisions = {}
        default = label
        # But hopefully we have observations!
        if pos_fdist.N() > 0:
            decisions = {feature_value: DecisionTreeClassifier(pos_fdist.max())}
        if neg_fdist.N() > 0:
            default = DecisionTreeClassifier(neg_fdist.max())

        return DecisionTreeClassifier(label, feature_name, decisions, default)

    @staticmethod
    def best_binary_stump(
        feature_names, labeled_featuresets, feature_values, verbose=False
    ):
        best_stump = DecisionTreeClassifier.leaf(labeled_featuresets)
        best_error = best_stump.error(labeled_featuresets)
        for fname in feature_names:
            for fval in feature_values[fname]:
                stump = DecisionTreeClassifier.binary_stump(
                    fname, fval, labeled_featuresets
                )
                stump_error = stump.error(labeled_featuresets)
                if stump_error < best_error:
                    best_error = stump_error
                    best_stump = stump
        if verbose:
            if best_stump._decisions:
                descr = "{}={}".format(
                    best_stump._fname, list(best_stump._decisions.keys())[0]
                )
            else:
                descr = "(default)"
            print(
                "best stump for {:6d} toks uses {:20} err={:6.4f}".format(
                    len(labeled_featuresets), descr, best_error
                )
            )
        return best_stump


##//////////////////////////////////////////////////////
##  Demo
##//////////////////////////////////////////////////////


def f(x):
    return DecisionTreeClassifier.train(x, binary=True, verbose=True)


def demo():
    from nltk.classify.util import binary_names_demo_features, names_demo

    classifier = names_demo(
        f, binary_names_demo_features  # DecisionTreeClassifier.train,
    )
    print(classifier.pretty_format(depth=7))
    print(classifier.pseudocode(depth=7))


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\formatters\rtf.py ===
"""
    pygments.formatters.rtf
    ~~~~~~~~~~~~~~~~~~~~~~~

    A formatter that generates RTF files.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from collections import OrderedDict
from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.style import _ansimap
from pip._vendor.pygments.util import get_bool_opt, get_int_opt, get_list_opt, surrogatepair


__all__ = ['RtfFormatter']


class RtfFormatter(Formatter):
    """
    Format tokens as RTF markup. This formatter automatically outputs full RTF
    documents with color information and other useful stuff. Perfect for Copy and
    Paste into Microsoft(R) Word(R) documents.

    Please note that ``encoding`` and ``outencoding`` options are ignored.
    The RTF format is ASCII natively, but handles unicode characters correctly
    thanks to escape sequences.

    .. versionadded:: 0.6

    Additional options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `fontface`
        The used font family, for example ``Bitstream Vera Sans``. Defaults to
        some generic font which is supposed to have fixed width.

    `fontsize`
        Size of the font used. Size is specified in half points. The
        default is 24 half-points, giving a size 12 font.

        .. versionadded:: 2.0

    `linenos`
        Turn on line numbering (default: ``False``).

        .. versionadded:: 2.18

    `lineno_fontsize`
        Font size for line numbers. Size is specified in half points
        (default: `fontsize`). 

        .. versionadded:: 2.18

    `lineno_padding`
        Number of spaces between the (inline) line numbers and the
        source code (default: ``2``).

        .. versionadded:: 2.18

    `linenostart`
        The line number for the first line (default: ``1``).

        .. versionadded:: 2.18

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

        .. versionadded:: 2.18

    `lineno_color`
        Color for line numbers specified as a hex triplet, e.g. ``'5e5e5e'``. 
        Defaults to the style's line number color if it is a hex triplet, 
        otherwise ansi bright black.

        .. versionadded:: 2.18

    `hl_lines`
        Specify a list of lines to be highlighted, as line numbers separated by
        spaces, e.g. ``'3 7 8'``. The line numbers are relative to the input 
        (i.e. the first line is line 1) unless `hl_linenostart` is set.

        .. versionadded:: 2.18

    `hl_color`
        Color for highlighting the lines specified in `hl_lines`, specified as 
        a hex triplet (default: style's `highlight_color`).

        .. versionadded:: 2.18

    `hl_linenostart`
        If set to ``True`` line numbers in `hl_lines` are specified
        relative to `linenostart` (default ``False``).

        .. versionadded:: 2.18
    """
    name = 'RTF'
    aliases = ['rtf']
    filenames = ['*.rtf']

    def __init__(self, **options):
        r"""
        Additional options accepted:

        ``fontface``
            Name of the font used. Could for example be ``'Courier New'``
            to further specify the default which is ``'\fmodern'``. The RTF
            specification claims that ``\fmodern`` are "Fixed-pitch serif
            and sans serif fonts". Hope every RTF implementation thinks
            the same about modern...

        """
        Formatter.__init__(self, **options)
        self.fontface = options.get('fontface') or ''
        self.fontsize = get_int_opt(options, 'fontsize', 0)
        self.linenos = get_bool_opt(options, 'linenos', False)
        self.lineno_fontsize = get_int_opt(options, 'lineno_fontsize',
                                           self.fontsize)
        self.lineno_padding = get_int_opt(options, 'lineno_padding', 2)
        self.linenostart = abs(get_int_opt(options, 'linenostart', 1))
        self.linenostep = abs(get_int_opt(options, 'linenostep', 1))
        self.hl_linenostart = get_bool_opt(options, 'hl_linenostart', False)

        self.hl_color = options.get('hl_color', '')
        if not self.hl_color:
            self.hl_color = self.style.highlight_color

        self.hl_lines = []
        for lineno in get_list_opt(options, 'hl_lines', []):
            try:
                lineno = int(lineno)
                if self.hl_linenostart:
                    lineno = lineno - self.linenostart + 1
                self.hl_lines.append(lineno)
            except ValueError:
                pass

        self.lineno_color = options.get('lineno_color', '')
        if not self.lineno_color:
            if  self.style.line_number_color == 'inherit':
                # style color is the css value 'inherit'
                # default to ansi bright-black
                self.lineno_color = _ansimap['ansibrightblack']
            else:
                # style color is assumed to be a hex triplet as other
                # colors in pygments/style.py
                self.lineno_color = self.style.line_number_color

        self.color_mapping = self._create_color_mapping()

    def _escape(self, text):
        return text.replace('\\', '\\\\') \
                   .replace('{', '\\{') \
                   .replace('}', '\\}')

    def _escape_text(self, text):
        # empty strings, should give a small performance improvement
        if not text:
            return ''

        # escape text
        text = self._escape(text)

        buf = []
        for c in text:
            cn = ord(c)
            if cn < (2**7):
                # ASCII character
                buf.append(str(c))
            elif (2**7) <= cn < (2**16):
                # single unicode escape sequence
                buf.append('{\\u%d}' % cn)
            elif (2**16) <= cn:
                # RTF limits unicode to 16 bits.
                # Force surrogate pairs
                buf.append('{\\u%d}{\\u%d}' % surrogatepair(cn))

        return ''.join(buf).replace('\n', '\\par')

    @staticmethod
    def hex_to_rtf_color(hex_color):
        if hex_color[0] == "#":
            hex_color = hex_color[1:]

        return '\\red%d\\green%d\\blue%d;' % (
                        int(hex_color[0:2], 16),
                        int(hex_color[2:4], 16),
                        int(hex_color[4:6], 16)
                    )

    def _split_tokens_on_newlines(self, tokensource):
        """
        Split tokens containing newline characters into multiple token
        each representing a line of the input file. Needed for numbering
        lines of e.g. multiline comments.
        """
        for ttype, value in tokensource:
            if value == '\n':
                yield (ttype, value)
            elif "\n" in value:
                lines = value.split("\n")
                for line in lines[:-1]:
                    yield (ttype, line+"\n")
                if lines[-1]:
                    yield (ttype, lines[-1])
            else:
                yield (ttype, value)

    def _create_color_mapping(self):
        """
        Create a mapping of style hex colors to index/offset in
        the RTF color table.
        """
        color_mapping = OrderedDict()
        offset = 1

        if self.linenos:
            color_mapping[self.lineno_color] = offset
            offset += 1

        if self.hl_lines:
            color_mapping[self.hl_color] = offset
            offset += 1

        for _, style in self.style:
            for color in style['color'], style['bgcolor'], style['border']:
                if color and color not in color_mapping:
                    color_mapping[color] = offset
                    offset += 1

        return color_mapping

    @property
    def _lineno_template(self):
        if self.lineno_fontsize != self.fontsize:
            return '{{\\fs{} \\cf{} %s{}}}'.format(self.lineno_fontsize,
                          self.color_mapping[self.lineno_color],
                          " " * self.lineno_padding)

        return '{{\\cf{} %s{}}}'.format(self.color_mapping[self.lineno_color],
                      " " * self.lineno_padding)

    @property
    def _hl_open_str(self):
        return rf'{{\highlight{self.color_mapping[self.hl_color]} '

    @property
    def _rtf_header(self):
        lines = []
        # rtf 1.8 header
        lines.append('{\\rtf1\\ansi\\uc0\\deff0'
                     '{\\fonttbl{\\f0\\fmodern\\fprq1\\fcharset0%s;}}'
                     % (self.fontface and ' '
                        + self._escape(self.fontface) or ''))

        # color table
        lines.append('{\\colortbl;')
        for color, _ in self.color_mapping.items():
            lines.append(self.hex_to_rtf_color(color))
        lines.append('}')

        # font and fontsize
        lines.append('\\f0\\sa0')
        if self.fontsize:
            lines.append('\\fs%d' % self.fontsize)

        # ensure Libre Office Writer imports and renders consecutive
        # space characters the same width, needed for line numbering.
        # https://bugs.documentfoundation.org/show_bug.cgi?id=144050
        lines.append('\\dntblnsbdb')

        return lines

    def format_unencoded(self, tokensource, outfile):
        for line in self._rtf_header:
            outfile.write(line + "\n")

        tokensource = self._split_tokens_on_newlines(tokensource)

        # first pass of tokens to count lines, needed for line numbering
        if self.linenos:
            line_count = 0
            tokens = [] # for copying the token source generator
            for ttype, value in tokensource:
                tokens.append((ttype, value))
                if value.endswith("\n"):
                    line_count += 1

            # width of line number strings (for padding with spaces)
            linenos_width = len(str(line_count+self.linenostart-1))

            tokensource = tokens

        # highlight stream
        lineno = 1
        start_new_line = True
        for ttype, value in tokensource:
            if start_new_line and lineno in self.hl_lines:
                outfile.write(self._hl_open_str)

            if start_new_line and self.linenos:
                if (lineno-self.linenostart+1)%self.linenostep == 0:
                    current_lineno = lineno + self.linenostart - 1
                    lineno_str = str(current_lineno).rjust(linenos_width)
                else:
                    lineno_str = "".rjust(linenos_width)
                outfile.write(self._lineno_template % lineno_str)

            while not self.style.styles_token(ttype) and ttype.parent:
                ttype = ttype.parent
            style = self.style.style_for_token(ttype)
            buf = []
            if style['bgcolor']:
                buf.append('\\cb%d' % self.color_mapping[style['bgcolor']])
            if style['color']:
                buf.append('\\cf%d' % self.color_mapping[style['color']])
            if style['bold']:
                buf.append('\\b')
            if style['italic']:
                buf.append('\\i')
            if style['underline']:
                buf.append('\\ul')
            if style['border']:
                buf.append('\\chbrdr\\chcfpat%d' %
                           self.color_mapping[style['border']])
            start = ''.join(buf)
            if start:
                outfile.write(f'{{{start} ')
            outfile.write(self._escape_text(value))
            if start:
                outfile.write('}')
            start_new_line = False

            # complete line of input
            if value.endswith("\n"):
                # close line highlighting
                if lineno in self.hl_lines:
                    outfile.write('}')
                # newline in RTF file after closing }
                outfile.write("\n")

                start_new_line = True
                lineno += 1

        outfile.write('}\n')

# === NexusCore/openenv\Lib\site-packages\pygments\formatters\rtf.py ===
"""
    pygments.formatters.rtf
    ~~~~~~~~~~~~~~~~~~~~~~~

    A formatter that generates RTF files.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from collections import OrderedDict
from pygments.formatter import Formatter
from pygments.style import _ansimap
from pygments.util import get_bool_opt, get_int_opt, get_list_opt, surrogatepair


__all__ = ['RtfFormatter']


class RtfFormatter(Formatter):
    """
    Format tokens as RTF markup. This formatter automatically outputs full RTF
    documents with color information and other useful stuff. Perfect for Copy and
    Paste into Microsoft(R) Word(R) documents.

    Please note that ``encoding`` and ``outencoding`` options are ignored.
    The RTF format is ASCII natively, but handles unicode characters correctly
    thanks to escape sequences.

    .. versionadded:: 0.6

    Additional options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `fontface`
        The used font family, for example ``Bitstream Vera Sans``. Defaults to
        some generic font which is supposed to have fixed width.

    `fontsize`
        Size of the font used. Size is specified in half points. The
        default is 24 half-points, giving a size 12 font.

        .. versionadded:: 2.0

    `linenos`
        Turn on line numbering (default: ``False``).

        .. versionadded:: 2.18

    `lineno_fontsize`
        Font size for line numbers. Size is specified in half points
        (default: `fontsize`). 

        .. versionadded:: 2.18

    `lineno_padding`
        Number of spaces between the (inline) line numbers and the
        source code (default: ``2``).

        .. versionadded:: 2.18

    `linenostart`
        The line number for the first line (default: ``1``).

        .. versionadded:: 2.18

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

        .. versionadded:: 2.18

    `lineno_color`
        Color for line numbers specified as a hex triplet, e.g. ``'5e5e5e'``. 
        Defaults to the style's line number color if it is a hex triplet, 
        otherwise ansi bright black.

        .. versionadded:: 2.18

    `hl_lines`
        Specify a list of lines to be highlighted, as line numbers separated by
        spaces, e.g. ``'3 7 8'``. The line numbers are relative to the input 
        (i.e. the first line is line 1) unless `hl_linenostart` is set.

        .. versionadded:: 2.18

    `hl_color`
        Color for highlighting the lines specified in `hl_lines`, specified as 
        a hex triplet (default: style's `highlight_color`).

        .. versionadded:: 2.18

    `hl_linenostart`
        If set to ``True`` line numbers in `hl_lines` are specified
        relative to `linenostart` (default ``False``).

        .. versionadded:: 2.18
    """
    name = 'RTF'
    aliases = ['rtf']
    filenames = ['*.rtf']

    def __init__(self, **options):
        r"""
        Additional options accepted:

        ``fontface``
            Name of the font used. Could for example be ``'Courier New'``
            to further specify the default which is ``'\fmodern'``. The RTF
            specification claims that ``\fmodern`` are "Fixed-pitch serif
            and sans serif fonts". Hope every RTF implementation thinks
            the same about modern...

        """
        Formatter.__init__(self, **options)
        self.fontface = options.get('fontface') or ''
        self.fontsize = get_int_opt(options, 'fontsize', 0)
        self.linenos = get_bool_opt(options, 'linenos', False)
        self.lineno_fontsize = get_int_opt(options, 'lineno_fontsize',
                                           self.fontsize)
        self.lineno_padding = get_int_opt(options, 'lineno_padding', 2)
        self.linenostart = abs(get_int_opt(options, 'linenostart', 1))
        self.linenostep = abs(get_int_opt(options, 'linenostep', 1))
        self.hl_linenostart = get_bool_opt(options, 'hl_linenostart', False)

        self.hl_color = options.get('hl_color', '')
        if not self.hl_color:
            self.hl_color = self.style.highlight_color

        self.hl_lines = []
        for lineno in get_list_opt(options, 'hl_lines', []):
            try:
                lineno = int(lineno)
                if self.hl_linenostart:
                    lineno = lineno - self.linenostart + 1
                self.hl_lines.append(lineno)
            except ValueError:
                pass

        self.lineno_color = options.get('lineno_color', '')
        if not self.lineno_color:
            if  self.style.line_number_color == 'inherit':
                # style color is the css value 'inherit'
                # default to ansi bright-black
                self.lineno_color = _ansimap['ansibrightblack']
            else:
                # style color is assumed to be a hex triplet as other
                # colors in pygments/style.py
                self.lineno_color = self.style.line_number_color

        self.color_mapping = self._create_color_mapping()

    def _escape(self, text):
        return text.replace('\\', '\\\\') \
                   .replace('{', '\\{') \
                   .replace('}', '\\}')

    def _escape_text(self, text):
        # empty strings, should give a small performance improvement
        if not text:
            return ''

        # escape text
        text = self._escape(text)

        buf = []
        for c in text:
            cn = ord(c)
            if cn < (2**7):
                # ASCII character
                buf.append(str(c))
            elif (2**7) <= cn < (2**16):
                # single unicode escape sequence
                buf.append('{\\u%d}' % cn)
            elif (2**16) <= cn:
                # RTF limits unicode to 16 bits.
                # Force surrogate pairs
                buf.append('{\\u%d}{\\u%d}' % surrogatepair(cn))

        return ''.join(buf).replace('\n', '\\par')

    @staticmethod
    def hex_to_rtf_color(hex_color):
        if hex_color[0] == "#":
            hex_color = hex_color[1:]

        return '\\red%d\\green%d\\blue%d;' % (
                        int(hex_color[0:2], 16),
                        int(hex_color[2:4], 16),
                        int(hex_color[4:6], 16)
                    )

    def _split_tokens_on_newlines(self, tokensource):
        """
        Split tokens containing newline characters into multiple token
        each representing a line of the input file. Needed for numbering
        lines of e.g. multiline comments.
        """
        for ttype, value in tokensource:
            if value == '\n':
                yield (ttype, value)
            elif "\n" in value:
                lines = value.split("\n")
                for line in lines[:-1]:
                    yield (ttype, line+"\n")
                if lines[-1]:
                    yield (ttype, lines[-1])
            else:
                yield (ttype, value)

    def _create_color_mapping(self):
        """
        Create a mapping of style hex colors to index/offset in
        the RTF color table.
        """
        color_mapping = OrderedDict()
        offset = 1

        if self.linenos:
            color_mapping[self.lineno_color] = offset
            offset += 1

        if self.hl_lines:
            color_mapping[self.hl_color] = offset
            offset += 1

        for _, style in self.style:
            for color in style['color'], style['bgcolor'], style['border']:
                if color and color not in color_mapping:
                    color_mapping[color] = offset
                    offset += 1

        return color_mapping

    @property
    def _lineno_template(self):
        if self.lineno_fontsize != self.fontsize:
            return '{{\\fs{} \\cf{} %s{}}}'.format(self.lineno_fontsize,
                          self.color_mapping[self.lineno_color],
                          " " * self.lineno_padding)

        return '{{\\cf{} %s{}}}'.format(self.color_mapping[self.lineno_color],
                      " " * self.lineno_padding)

    @property
    def _hl_open_str(self):
        return rf'{{\highlight{self.color_mapping[self.hl_color]} '

    @property
    def _rtf_header(self):
        lines = []
        # rtf 1.8 header
        lines.append('{\\rtf1\\ansi\\uc0\\deff0'
                     '{\\fonttbl{\\f0\\fmodern\\fprq1\\fcharset0%s;}}'
                     % (self.fontface and ' '
                        + self._escape(self.fontface) or ''))

        # color table
        lines.append('{\\colortbl;')
        for color, _ in self.color_mapping.items():
            lines.append(self.hex_to_rtf_color(color))
        lines.append('}')

        # font and fontsize
        lines.append('\\f0\\sa0')
        if self.fontsize:
            lines.append('\\fs%d' % self.fontsize)

        # ensure Libre Office Writer imports and renders consecutive
        # space characters the same width, needed for line numbering.
        # https://bugs.documentfoundation.org/show_bug.cgi?id=144050
        lines.append('\\dntblnsbdb')

        return lines

    def format_unencoded(self, tokensource, outfile):
        for line in self._rtf_header:
            outfile.write(line + "\n")

        tokensource = self._split_tokens_on_newlines(tokensource)

        # first pass of tokens to count lines, needed for line numbering
        if self.linenos:
            line_count = 0
            tokens = [] # for copying the token source generator
            for ttype, value in tokensource:
                tokens.append((ttype, value))
                if value.endswith("\n"):
                    line_count += 1

            # width of line number strings (for padding with spaces)
            linenos_width = len(str(line_count+self.linenostart-1))

            tokensource = tokens

        # highlight stream
        lineno = 1
        start_new_line = True
        for ttype, value in tokensource:
            if start_new_line and lineno in self.hl_lines:
                outfile.write(self._hl_open_str)

            if start_new_line and self.linenos:
                if (lineno-self.linenostart+1)%self.linenostep == 0:
                    current_lineno = lineno + self.linenostart - 1
                    lineno_str = str(current_lineno).rjust(linenos_width)
                else:
                    lineno_str = "".rjust(linenos_width)
                outfile.write(self._lineno_template % lineno_str)

            while not self.style.styles_token(ttype) and ttype.parent:
                ttype = ttype.parent
            style = self.style.style_for_token(ttype)
            buf = []
            if style['bgcolor']:
                buf.append('\\cb%d' % self.color_mapping[style['bgcolor']])
            if style['color']:
                buf.append('\\cf%d' % self.color_mapping[style['color']])
            if style['bold']:
                buf.append('\\b')
            if style['italic']:
                buf.append('\\i')
            if style['underline']:
                buf.append('\\ul')
            if style['border']:
                buf.append('\\chbrdr\\chcfpat%d' %
                           self.color_mapping[style['border']])
            start = ''.join(buf)
            if start:
                outfile.write(f'{{{start} ')
            outfile.write(self._escape_text(value))
            if start:
                outfile.write('}')
            start_new_line = False

            # complete line of input
            if value.endswith("\n"):
                # close line highlighting
                if lineno in self.hl_lines:
                    outfile.write('}')
                # newline in RTF file after closing }
                outfile.write("\n")

                start_new_line = True
                lineno += 1

        outfile.write('}\n')

# === NexusCore/openenv\Lib\site-packages\httpx\_auth.py ===
from __future__ import annotations

import hashlib
import os
import re
import time
import typing
from base64 import b64encode
from urllib.request import parse_http_list

from ._exceptions import ProtocolError
from ._models import Cookies, Request, Response
from ._utils import to_bytes, to_str, unquote

if typing.TYPE_CHECKING:  # pragma: no cover
    from hashlib import _Hash


__all__ = ["Auth", "BasicAuth", "DigestAuth", "NetRCAuth"]


class Auth:
    """
    Base class for all authentication schemes.

    To implement a custom authentication scheme, subclass `Auth` and override
    the `.auth_flow()` method.

    If the authentication scheme does I/O such as disk access or network calls, or uses
    synchronization primitives such as locks, you should override `.sync_auth_flow()`
    and/or `.async_auth_flow()` instead of `.auth_flow()` to provide specialized
    implementations that will be used by `Client` and `AsyncClient` respectively.
    """

    requires_request_body = False
    requires_response_body = False

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        """
        Execute the authentication flow.

        To dispatch a request, `yield` it:

        ```
        yield request
        ```

        The client will `.send()` the response back into the flow generator. You can
        access it like so:

        ```
        response = yield request
        ```

        A `return` (or reaching the end of the generator) will result in the
        client returning the last response obtained from the server.

        You can dispatch as many requests as is necessary.
        """
        yield request

    def sync_auth_flow(
        self, request: Request
    ) -> typing.Generator[Request, Response, None]:
        """
        Execute the authentication flow synchronously.

        By default, this defers to `.auth_flow()`. You should override this method
        when the authentication scheme does I/O and/or uses concurrency primitives.
        """
        if self.requires_request_body:
            request.read()

        flow = self.auth_flow(request)
        request = next(flow)

        while True:
            response = yield request
            if self.requires_response_body:
                response.read()

            try:
                request = flow.send(response)
            except StopIteration:
                break

    async def async_auth_flow(
        self, request: Request
    ) -> typing.AsyncGenerator[Request, Response]:
        """
        Execute the authentication flow asynchronously.

        By default, this defers to `.auth_flow()`. You should override this method
        when the authentication scheme does I/O and/or uses concurrency primitives.
        """
        if self.requires_request_body:
            await request.aread()

        flow = self.auth_flow(request)
        request = next(flow)

        while True:
            response = yield request
            if self.requires_response_body:
                await response.aread()

            try:
                request = flow.send(response)
            except StopIteration:
                break


class FunctionAuth(Auth):
    """
    Allows the 'auth' argument to be passed as a simple callable function,
    that takes the request, and returns a new, modified request.
    """

    def __init__(self, func: typing.Callable[[Request], Request]) -> None:
        self._func = func

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        yield self._func(request)


class BasicAuth(Auth):
    """
    Allows the 'auth' argument to be passed as a (username, password) pair,
    and uses HTTP Basic authentication.
    """

    def __init__(self, username: str | bytes, password: str | bytes) -> None:
        self._auth_header = self._build_auth_header(username, password)

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        request.headers["Authorization"] = self._auth_header
        yield request

    def _build_auth_header(self, username: str | bytes, password: str | bytes) -> str:
        userpass = b":".join((to_bytes(username), to_bytes(password)))
        token = b64encode(userpass).decode()
        return f"Basic {token}"


class NetRCAuth(Auth):
    """
    Use a 'netrc' file to lookup basic auth credentials based on the url host.
    """

    def __init__(self, file: str | None = None) -> None:
        # Lazily import 'netrc'.
        # There's no need for us to load this module unless 'NetRCAuth' is being used.
        import netrc

        self._netrc_info = netrc.netrc(file)

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        auth_info = self._netrc_info.authenticators(request.url.host)
        if auth_info is None or not auth_info[2]:
            # The netrc file did not have authentication credentials for this host.
            yield request
        else:
            # Build a basic auth header with credentials from the netrc file.
            request.headers["Authorization"] = self._build_auth_header(
                username=auth_info[0], password=auth_info[2]
            )
            yield request

    def _build_auth_header(self, username: str | bytes, password: str | bytes) -> str:
        userpass = b":".join((to_bytes(username), to_bytes(password)))
        token = b64encode(userpass).decode()
        return f"Basic {token}"


class DigestAuth(Auth):
    _ALGORITHM_TO_HASH_FUNCTION: dict[str, typing.Callable[[bytes], _Hash]] = {
        "MD5": hashlib.md5,
        "MD5-SESS": hashlib.md5,
        "SHA": hashlib.sha1,
        "SHA-SESS": hashlib.sha1,
        "SHA-256": hashlib.sha256,
        "SHA-256-SESS": hashlib.sha256,
        "SHA-512": hashlib.sha512,
        "SHA-512-SESS": hashlib.sha512,
    }

    def __init__(self, username: str | bytes, password: str | bytes) -> None:
        self._username = to_bytes(username)
        self._password = to_bytes(password)
        self._last_challenge: _DigestAuthChallenge | None = None
        self._nonce_count = 1

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        if self._last_challenge:
            request.headers["Authorization"] = self._build_auth_header(
                request, self._last_challenge
            )

        response = yield request

        if response.status_code != 401 or "www-authenticate" not in response.headers:
            # If the response is not a 401 then we don't
            # need to build an authenticated request.
            return

        for auth_header in response.headers.get_list("www-authenticate"):
            if auth_header.lower().startswith("digest "):
                break
        else:
            # If the response does not include a 'WWW-Authenticate: Digest ...'
            # header, then we don't need to build an authenticated request.
            return

        self._last_challenge = self._parse_challenge(request, response, auth_header)
        self._nonce_count = 1

        request.headers["Authorization"] = self._build_auth_header(
            request, self._last_challenge
        )
        if response.cookies:
            Cookies(response.cookies).set_cookie_header(request=request)
        yield request

    def _parse_challenge(
        self, request: Request, response: Response, auth_header: str
    ) -> _DigestAuthChallenge:
        """
        Returns a challenge from a Digest WWW-Authenticate header.
        These take the form of:
        `Digest realm="realm@host.com",qop="auth,auth-int",nonce="abc",opaque="xyz"`
        """
        scheme, _, fields = auth_header.partition(" ")

        # This method should only ever have been called with a Digest auth header.
        assert scheme.lower() == "digest"

        header_dict: dict[str, str] = {}
        for field in parse_http_list(fields):
            key, value = field.strip().split("=", 1)
            header_dict[key] = unquote(value)

        try:
            realm = header_dict["realm"].encode()
            nonce = header_dict["nonce"].encode()
            algorithm = header_dict.get("algorithm", "MD5")
            opaque = header_dict["opaque"].encode() if "opaque" in header_dict else None
            qop = header_dict["qop"].encode() if "qop" in header_dict else None
            return _DigestAuthChallenge(
                realm=realm, nonce=nonce, algorithm=algorithm, opaque=opaque, qop=qop
            )
        except KeyError as exc:
            message = "Malformed Digest WWW-Authenticate header"
            raise ProtocolError(message, request=request) from exc

    def _build_auth_header(
        self, request: Request, challenge: _DigestAuthChallenge
    ) -> str:
        hash_func = self._ALGORITHM_TO_HASH_FUNCTION[challenge.algorithm.upper()]

        def digest(data: bytes) -> bytes:
            return hash_func(data).hexdigest().encode()

        A1 = b":".join((self._username, challenge.realm, self._password))

        path = request.url.raw_path
        A2 = b":".join((request.method.encode(), path))
        # TODO: implement auth-int
        HA2 = digest(A2)

        nc_value = b"%08x" % self._nonce_count
        cnonce = self._get_client_nonce(self._nonce_count, challenge.nonce)
        self._nonce_count += 1

        HA1 = digest(A1)
        if challenge.algorithm.lower().endswith("-sess"):
            HA1 = digest(b":".join((HA1, challenge.nonce, cnonce)))

        qop = self._resolve_qop(challenge.qop, request=request)
        if qop is None:
            # Following RFC 2069
            digest_data = [HA1, challenge.nonce, HA2]
        else:
            # Following RFC 2617/7616
            digest_data = [HA1, challenge.nonce, nc_value, cnonce, qop, HA2]

        format_args = {
            "username": self._username,
            "realm": challenge.realm,
            "nonce": challenge.nonce,
            "uri": path,
            "response": digest(b":".join(digest_data)),
            "algorithm": challenge.algorithm.encode(),
        }
        if challenge.opaque:
            format_args["opaque"] = challenge.opaque
        if qop:
            format_args["qop"] = b"auth"
            format_args["nc"] = nc_value
            format_args["cnonce"] = cnonce

        return "Digest " + self._get_header_value(format_args)

    def _get_client_nonce(self, nonce_count: int, nonce: bytes) -> bytes:
        s = str(nonce_count).encode()
        s += nonce
        s += time.ctime().encode()
        s += os.urandom(8)

        return hashlib.sha1(s).hexdigest()[:16].encode()

    def _get_header_value(self, header_fields: dict[str, bytes]) -> str:
        NON_QUOTED_FIELDS = ("algorithm", "qop", "nc")
        QUOTED_TEMPLATE = '{}="{}"'
        NON_QUOTED_TEMPLATE = "{}={}"

        header_value = ""
        for i, (field, value) in enumerate(header_fields.items()):
            if i > 0:
                header_value += ", "
            template = (
                QUOTED_TEMPLATE
                if field not in NON_QUOTED_FIELDS
                else NON_QUOTED_TEMPLATE
            )
            header_value += template.format(field, to_str(value))

        return header_value

    def _resolve_qop(self, qop: bytes | None, request: Request) -> bytes | None:
        if qop is None:
            return None
        qops = re.split(b", ?", qop)
        if b"auth" in qops:
            return b"auth"

        if qops == [b"auth-int"]:
            raise NotImplementedError("Digest auth-int support is not yet implemented")

        message = f'Unexpected qop value "{qop!r}" in digest auth'
        raise ProtocolError(message, request=request)


class _DigestAuthChallenge(typing.NamedTuple):
    realm: bytes
    nonce: bytes
    algorithm: str
    opaque: bytes | None
    qop: bytes | None

# === NexusCore/openenv\Lib\site-packages\IPython\core\page.py ===
# encoding: utf-8
"""
Paging capabilities for IPython.core

Notes
-----

For now this uses IPython hooks, so it can't be in IPython.utils.  If we can get
rid of that dependency, we could move it there.
-----
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.


import os
import io
import re
import sys
import tempfile
import subprocess

from io import UnsupportedOperation
from pathlib import Path

from IPython import get_ipython
from IPython.display import display
from IPython.core.error import TryNext
from IPython.utils.data import chop
from IPython.utils.process import system
from IPython.utils.terminal import get_terminal_size
from IPython.utils import py3compat


def display_page(strng, start=0, screen_lines=25):
    """Just display, no paging. screen_lines is ignored."""
    if isinstance(strng, dict):
        data = strng
    else:
        if start:
            strng = u'\n'.join(strng.splitlines()[start:])
        data = { 'text/plain': strng }
    display(data, raw=True)


def as_hook(page_func):
    """Wrap a pager func to strip the `self` arg

    so it can be called as a hook.
    """
    return lambda self, *args, **kwargs: page_func(*args, **kwargs)


esc_re = re.compile(r"(\x1b[^m]+m)")

def page_dumb(strng, start=0, screen_lines=25):
    """Very dumb 'pager' in Python, for when nothing else works.

    Only moves forward, same interface as page(), except for pager_cmd and
    mode.
    """
    if isinstance(strng, dict):
        strng = strng.get('text/plain', '')
    out_ln  = strng.splitlines()[start:]
    screens = chop(out_ln,screen_lines-1)
    if len(screens) == 1:
        print(os.linesep.join(screens[0]))
    else:
        last_escape = ""
        for scr in screens[0:-1]:
            hunk = os.linesep.join(scr)
            print(last_escape + hunk)
            if not page_more():
                return
            esc_list = esc_re.findall(hunk)
            if len(esc_list) > 0:
                last_escape = esc_list[-1]
        print(last_escape + os.linesep.join(screens[-1]))

def _detect_screen_size(screen_lines_def):
    """Attempt to work out the number of lines on the screen.

    This is called by page(). It can raise an error (e.g. when run in the
    test suite), so it's separated out so it can easily be called in a try block.
    """
    TERM = os.environ.get('TERM',None)
    if not((TERM=='xterm' or TERM=='xterm-color') and sys.platform != 'sunos5'):
        # curses causes problems on many terminals other than xterm, and
        # some termios calls lock up on Sun OS5.
        return screen_lines_def
    
    try:
        import termios
        import curses
    except ImportError:
        return screen_lines_def
    
    # There is a bug in curses, where *sometimes* it fails to properly
    # initialize, and then after the endwin() call is made, the
    # terminal is left in an unusable state.  Rather than trying to
    # check every time for this (by requesting and comparing termios
    # flags each time), we just save the initial terminal state and
    # unconditionally reset it every time.  It's cheaper than making
    # the checks.
    try:
        term_flags = termios.tcgetattr(sys.stdout)
    except termios.error as err:
        # can fail on Linux 2.6, pager_page will catch the TypeError
        raise TypeError('termios error: {0}'.format(err)) from err

    try:
        scr = curses.initscr()
    except AttributeError:
        # Curses on Solaris may not be complete, so we can't use it there
        return screen_lines_def
    
    screen_lines_real,screen_cols = scr.getmaxyx()
    curses.endwin()

    # Restore terminal state in case endwin() didn't.
    termios.tcsetattr(sys.stdout,termios.TCSANOW,term_flags)
    # Now we have what we needed: the screen size in rows/columns
    return screen_lines_real
    # print('***Screen size:',screen_lines_real,'lines x',
    #       screen_cols,'columns.')  # dbg

def pager_page(strng, start=0, screen_lines=0, pager_cmd=None) -> None:
    """Display a string, piping through a pager after a certain length.

    strng can be a mime-bundle dict, supplying multiple representations,
    keyed by mime-type.

    The screen_lines parameter specifies the number of *usable* lines of your
    terminal screen (total lines minus lines you need to reserve to show other
    information).

    If you set screen_lines to a number <=0, page() will try to auto-determine
    your screen size and will only use up to (screen_size+screen_lines) for
    printing, paging after that. That is, if you want auto-detection but need
    to reserve the bottom 3 lines of the screen, use screen_lines = -3, and for
    auto-detection without any lines reserved simply use screen_lines = 0.

    If a string won't fit in the allowed lines, it is sent through the
    specified pager command. If none given, look for PAGER in the environment,
    and ultimately default to less.

    If no system pager works, the string is sent through a 'dumb pager'
    written in python, very simplistic.
    """
    
    # for compatibility with mime-bundle form:
    if isinstance(strng, dict):
        strng = strng['text/plain']

    # Ugly kludge, but calling curses.initscr() flat out crashes in emacs
    TERM = os.environ.get('TERM','dumb')
    if TERM in ['dumb','emacs'] and os.name != 'nt':
        print(strng)
        return
    # chop off the topmost part of the string we don't want to see
    str_lines = strng.splitlines()[start:]
    str_toprint = os.linesep.join(str_lines)
    num_newlines = len(str_lines)
    len_str = len(str_toprint)

    # Dumb heuristics to guesstimate number of on-screen lines the string
    # takes.  Very basic, but good enough for docstrings in reasonable
    # terminals. If someone later feels like refining it, it's not hard.
    numlines = max(num_newlines,int(len_str/80)+1)

    screen_lines_def = get_terminal_size()[1]

    # auto-determine screen size
    if screen_lines <= 0:
        try:
            screen_lines += _detect_screen_size(screen_lines_def)
        except (TypeError, UnsupportedOperation):
            print(str_toprint)
            return

    # print('numlines',numlines,'screenlines',screen_lines)  # dbg
    if numlines <= screen_lines :
        # print('*** normal print')  # dbg
        print(str_toprint)
    else:
        # Try to open pager and default to internal one if that fails.
        # All failure modes are tagged as 'retval=1', to match the return
        # value of a failed system command.  If any intermediate attempt
        # sets retval to 1, at the end we resort to our own page_dumb() pager.
        pager_cmd = get_pager_cmd(pager_cmd)
        pager_cmd += ' ' + get_pager_start(pager_cmd,start)
        if os.name == 'nt':
            if pager_cmd.startswith('type'):
                # The default WinXP 'type' command is failing on complex strings.
                retval = 1
            else:
                fd, tmpname = tempfile.mkstemp('.txt')
                tmppath = Path(tmpname)
                try:
                    os.close(fd)
                    with tmppath.open("wt", encoding="utf-8") as tmpfile:
                        tmpfile.write(strng)
                        cmd = "%s < %s" % (pager_cmd, tmppath)
                    # tmpfile needs to be closed for windows
                    if os.system(cmd):
                        retval = 1
                    else:
                        retval = None
                finally:
                    Path.unlink(tmppath)
        else:
            try:
                retval = None
                # Emulate os.popen, but redirect stderr
                proc = subprocess.Popen(
                    pager_cmd,
                    shell=True,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                pager = os._wrap_close(
                    io.TextIOWrapper(proc.stdin, encoding="utf-8"), proc
                )
                try:
                    pager_encoding = pager.encoding or sys.stdout.encoding
                    pager.write(strng)
                finally:
                    retval = pager.close()
            except IOError as msg:  # broken pipe when user quits
                if msg.args == (32, 'Broken pipe'):
                    retval = None
                else:
                    retval = 1
            except OSError:
                # Other strange problems, sometimes seen in Win2k/cygwin
                retval = 1
        if retval is not None:
            page_dumb(strng,screen_lines=screen_lines)


def page(data, start: int = 0, screen_lines: int = 0, pager_cmd=None):
    """Display content in a pager, piping through a pager after a certain length.

    data can be a mime-bundle dict, supplying multiple representations,
    keyed by mime-type, or text.

    Pager is dispatched via the `show_in_pager` IPython hook.
    If no hook is registered, `pager_page` will be used.
    """
    # Some routines may auto-compute start offsets incorrectly and pass a
    # negative value.  Offset to 0 for robustness.
    start = max(0, start)

    # first, try the hook
    ip = get_ipython()
    if ip:
        try:
            ip.hooks.show_in_pager(data, start=start, screen_lines=screen_lines)
            return
        except TryNext:
            pass
    
    # fallback on default pager
    return pager_page(data, start, screen_lines, pager_cmd)


def page_file(fname, start=0, pager_cmd=None):
    """Page a file, using an optional pager command and starting line.
    """

    pager_cmd = get_pager_cmd(pager_cmd)
    pager_cmd += ' ' + get_pager_start(pager_cmd,start)

    try:
        if os.environ['TERM'] in ['emacs','dumb']:
            raise EnvironmentError
        system(pager_cmd + ' ' + fname)
    except:
        try:
            if start > 0:
                start -= 1
            page(open(fname, encoding="utf-8").read(), start)
        except:
            print('Unable to show file',repr(fname))


def get_pager_cmd(pager_cmd=None):
    """Return a pager command.

    Makes some attempts at finding an OS-correct one.
    """
    if os.name == 'posix':
        default_pager_cmd = 'less -R'  # -R for color control sequences
    elif os.name in ['nt','dos']:
        default_pager_cmd = 'type'

    if pager_cmd is None:
        try:
            pager_cmd = os.environ['PAGER']
        except:
            pager_cmd = default_pager_cmd
    
    if pager_cmd == 'less' and '-r' not in os.environ.get('LESS', '').lower():
        pager_cmd += ' -R'
    
    return pager_cmd


def get_pager_start(pager, start):
    """Return the string for paging files with an offset.

    This is the '+N' argument which less and more (under Unix) accept.
    """

    if pager in ['less','more']:
        if start:
            start_string = '+' + str(start)
        else:
            start_string = ''
    else:
        start_string = ''
    return start_string


# (X)emacs on win32 doesn't like to be bypassed with msvcrt.getch()
if os.name == 'nt' and os.environ.get('TERM','dumb') != 'emacs':
    import msvcrt
    def page_more():
        """ Smart pausing between pages

        @return:    True if need print more lines, False if quit
        """
        sys.stdout.write('---Return to continue, q to quit--- ')
        ans = msvcrt.getwch()
        if ans in ("q", "Q"):
            result = False
        else:
            result = True
        sys.stdout.write("\b"*37 + " "*37 + "\b"*37)
        return result
else:
    def page_more():
        ans = py3compat.input('---Return to continue, q to quit--- ')
        if ans.lower().startswith('q'):
            return False
        else:
            return True

# === NexusCore/openenv\Lib\site-packages\litellm\secret_managers\main.py ===
import ast
import base64
import binascii
import os
import traceback
from typing import Any, Optional, Union

import httpx

import litellm
from litellm._logging import print_verbose, verbose_logger
from litellm.caching.caching import DualCache
from litellm.llms.custom_httpx.http_handler import HTTPHandler
from litellm.proxy._types import KeyManagementSystem
from litellm.secret_managers.get_azure_ad_token_provider import (
    get_azure_ad_token_provider,
)

oidc_cache = DualCache()


######### Secret Manager ############################
# checks if user has passed in a secret manager client
# if passed in then checks the secret there
def _is_base64(s):
    try:
        return base64.b64encode(base64.b64decode(s)).decode() == s
    except binascii.Error:
        return False


def str_to_bool(value: Optional[str]) -> Optional[bool]:
    """
    Converts a string to a boolean if it's a recognized boolean string.
    Returns None if the string is not a recognized boolean value.

    :param value: The string to be checked.
    :return: True or False if the string is a recognized boolean, otherwise None.
    """
    if value is None:
        return None

    true_values = {"true"}
    false_values = {"false"}

    value_lower = value.strip().lower()

    if value_lower in true_values:
        return True
    elif value_lower in false_values:
        return False
    else:
        return None


def get_secret_str(
    secret_name: str,
    default_value: Optional[Union[str, bool]] = None,
) -> Optional[str]:
    """
    Guarantees response from 'get_secret' is either string or none. Used for fixing linting errors.
    """
    value = get_secret(secret_name=secret_name, default_value=default_value)
    if value is not None and not isinstance(value, str):
        return None

    return value


def get_secret_bool(
    secret_name: str,
    default_value: Optional[bool] = None,
) -> Optional[bool]:
    """
    Guarantees response from 'get_secret' is either boolean or none. Used for fixing linting errors.

    Args:
        secret_name: The name of the secret to get.
        default_value: The default value to return if the secret is not found.

    Returns:
        The secret value as a boolean or None if the secret is not found.
    """
    _secret_value = get_secret(secret_name, default_value)
    if _secret_value is None:
        return None
    elif isinstance(_secret_value, bool):
        return _secret_value
    else:
        return str_to_bool(_secret_value)


def get_secret(  # noqa: PLR0915
    secret_name: str,
    default_value: Optional[Union[str, bool]] = None,
):
    key_management_system = litellm._key_management_system
    key_management_settings = litellm._key_management_settings
    secret = None

    if secret_name.startswith("os.environ/"):
        secret_name = secret_name.replace("os.environ/", "")

    # Example: oidc/google/https://bedrock-runtime.us-east-1.amazonaws.com/model/stability.stable-diffusion-xl-v1/invoke
    if secret_name.startswith("oidc/"):
        secret_name_split = secret_name.replace("oidc/", "")
        oidc_provider, oidc_aud = secret_name_split.split("/", 1)
        oidc_aud = "/".join(secret_name_split.split("/")[1:])
        # TODO: Add caching for HTTP requests
        if oidc_provider == "google":
            oidc_token = oidc_cache.get_cache(key=secret_name)
            if oidc_token is not None:
                return oidc_token

            oidc_client = HTTPHandler(timeout=httpx.Timeout(timeout=600.0, connect=5.0))
            # https://cloud.google.com/compute/docs/instances/verifying-instance-identity#request_signature
            response = oidc_client.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity",
                params={"audience": oidc_aud},
                headers={"Metadata-Flavor": "Google"},
            )
            if response.status_code == 200:
                oidc_token = response.text
                oidc_cache.set_cache(key=secret_name, value=oidc_token, ttl=3600 - 60)
                return oidc_token
            else:
                raise ValueError("Google OIDC provider failed")
        elif oidc_provider == "circleci":
            # https://circleci.com/docs/openid-connect-tokens/
            env_secret = os.getenv("CIRCLE_OIDC_TOKEN")
            if env_secret is None:
                raise ValueError("CIRCLE_OIDC_TOKEN not found in environment")
            return env_secret
        elif oidc_provider == "circleci_v2":
            # https://circleci.com/docs/openid-connect-tokens/
            env_secret = os.getenv("CIRCLE_OIDC_TOKEN_V2")
            if env_secret is None:
                raise ValueError("CIRCLE_OIDC_TOKEN_V2 not found in environment")
            return env_secret
        elif oidc_provider == "github":
            # https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-cloud-providers#using-custom-actions
            actions_id_token_request_url = os.getenv("ACTIONS_ID_TOKEN_REQUEST_URL")
            actions_id_token_request_token = os.getenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
            if actions_id_token_request_url is None or actions_id_token_request_token is None:
                raise ValueError(
                    "ACTIONS_ID_TOKEN_REQUEST_URL or ACTIONS_ID_TOKEN_REQUEST_TOKEN not found in environment"
                )

            oidc_token = oidc_cache.get_cache(key=secret_name)
            if oidc_token is not None:
                return oidc_token

            oidc_client = HTTPHandler(timeout=httpx.Timeout(timeout=600.0, connect=5.0))
            response = oidc_client.get(
                actions_id_token_request_url,
                params={"audience": oidc_aud},
                headers={
                    "Authorization": f"Bearer {actions_id_token_request_token}",
                    "Accept": "application/json; api-version=2.0",
                },
            )
            if response.status_code == 200:
                oidc_token = response.json().get("value", None)
                oidc_cache.set_cache(key=secret_name, value=oidc_token, ttl=300 - 5)
                return oidc_token
            else:
                raise ValueError("Github OIDC provider failed")
        elif oidc_provider == "azure":
            # https://azure.github.io/azure-workload-identity/docs/quick-start.html
            azure_federated_token_file = os.getenv("AZURE_FEDERATED_TOKEN_FILE")
            if azure_federated_token_file is None:
                verbose_logger.warning(
                    "AZURE_FEDERATED_TOKEN_FILE not found in environment will use Azure AD token provider"
                )
                azure_token_provider = get_azure_ad_token_provider(azure_scope=oidc_aud)
                try:
                    oidc_token = azure_token_provider()
                    if oidc_token is None:
                        raise ValueError("Azure OIDC provider returned None token")
                    return oidc_token
                except Exception as e:
                    error_msg = f"Azure OIDC provider failed: {str(e)}"
                    verbose_logger.error(error_msg)
                    raise ValueError(error_msg)
            with open(azure_federated_token_file, "r") as f:
                oidc_token = f.read()
                return oidc_token
        elif oidc_provider == "file":
            # Load token from a file
            with open(oidc_aud, "r") as f:
                oidc_token = f.read()
                return oidc_token
        elif oidc_provider == "env":
            # Load token directly from an environment variable
            oidc_token = os.getenv(oidc_aud)
            if oidc_token is None:
                raise ValueError(f"Environment variable {oidc_aud} not found")
            return oidc_token
        elif oidc_provider == "env_path":
            # Load token from a file path specified in an environment variable
            token_file_path = os.getenv(oidc_aud)
            if token_file_path is None:
                raise ValueError(f"Environment variable {oidc_aud} not found")
            with open(token_file_path, "r") as f:
                oidc_token = f.read()
                return oidc_token
        else:
            raise ValueError("Unsupported OIDC provider")

    try:
        if _should_read_secret_from_secret_manager() and litellm.secret_manager_client is not None:
            try:
                client = litellm.secret_manager_client
                key_manager = "local"
                if key_management_system is not None:
                    key_manager = key_management_system.value

                if key_management_settings is not None:
                    if (
                        key_management_settings.hosted_keys is not None
                        and secret_name not in key_management_settings.hosted_keys
                    ):  # allow user to specify which keys to check in hosted key manager
                        key_manager = "local"

                if (
                    key_manager == KeyManagementSystem.AZURE_KEY_VAULT.value
                    or type(client).__module__ + "." + type(client).__name__
                    == "azure.keyvault.secrets._client.SecretClient"
                ):  # support Azure Secret Client - from azure.keyvault.secrets import SecretClient
                    secret = client.get_secret(secret_name).value
                elif (
                    key_manager == KeyManagementSystem.GOOGLE_KMS.value
                    or client.__class__.__name__ == "KeyManagementServiceClient"
                ):
                    encrypted_secret: Any = os.getenv(secret_name)
                    if encrypted_secret is None:
                        raise ValueError("Google KMS requires the encrypted secret to be in the environment!")
                    b64_flag = _is_base64(encrypted_secret)
                    if b64_flag is True:  # if passed in as encoded b64 string
                        encrypted_secret = base64.b64decode(encrypted_secret)
                        ciphertext = encrypted_secret
                    else:
                        raise ValueError(
                            "Google KMS requires the encrypted secret to be encoded in base64"
                        )  # fix for this vulnerability https://huntr.com/bounties/ae623c2f-b64b-4245-9ed4-f13a0a5824ce
                    response = client.decrypt(
                        request={
                            "name": litellm._google_kms_resource_name,
                            "ciphertext": ciphertext,
                        }
                    )
                    secret = response.plaintext.decode("utf-8")  # assumes the original value was encoded with utf-8
                elif key_manager == KeyManagementSystem.AWS_KMS.value:
                    """
                    Only check the tokens which start with 'aws_kms/'. This prevents latency impact caused by checking all keys.
                    """
                    encrypted_value = os.getenv(secret_name, None)
                    if encrypted_value is None:
                        raise Exception("AWS KMS - Encrypted Value of Key={} is None".format(secret_name))
                    # Decode the base64 encoded ciphertext
                    ciphertext_blob = base64.b64decode(encrypted_value)

                    # Set up the parameters for the decrypt call
                    params = {"CiphertextBlob": ciphertext_blob}
                    # Perform the decryption
                    response = client.decrypt(**params)

                    # Extract and decode the plaintext
                    plaintext = response["Plaintext"]
                    secret = plaintext.decode("utf-8")
                    if isinstance(secret, str):
                        secret = secret.strip()
                elif key_manager == KeyManagementSystem.AWS_SECRET_MANAGER.value:
                    from litellm.secret_managers.aws_secret_manager_v2 import (
                        AWSSecretsManagerV2,
                    )

                    if isinstance(client, AWSSecretsManagerV2):
                        secret = client.sync_read_secret(
                            secret_name=secret_name,
                            primary_secret_name=key_management_settings.primary_secret_name,
                        )
                        print_verbose(f"get_secret_value_response: {secret}")
                elif key_manager == KeyManagementSystem.GOOGLE_SECRET_MANAGER.value:
                    try:
                        secret = client.get_secret_from_google_secret_manager(secret_name)
                        print_verbose(f"secret from google secret manager:  {secret}")
                        if secret is None:
                            raise ValueError(f"No secret found in Google Secret Manager for {secret_name}")
                    except Exception as e:
                        print_verbose(f"An error occurred - {str(e)}")
                        raise e
                elif key_manager == KeyManagementSystem.HASHICORP_VAULT.value:
                    try:
                        secret = client.sync_read_secret(secret_name=secret_name)
                        if secret is None:
                            raise ValueError(f"No secret found in Hashicorp Secret Manager for {secret_name}")
                    except Exception as e:
                        print_verbose(f"An error occurred - {str(e)}")
                        raise e
                elif key_manager == "local":
                    secret = os.getenv(secret_name)
                else:  # assume the default is infisicial client
                    secret = client.get_secret(secret_name).secret_value
            except Exception as e:  # check if it's in os.environ
                verbose_logger.error(
                    f"Defaulting to os.environ value for key={secret_name}. An exception occurred - {str(e)}.\n\n{traceback.format_exc()}"
                )
                secret = os.getenv(secret_name)
            try:
                if isinstance(secret, str):
                    secret_value_as_bool = ast.literal_eval(secret)
                    if isinstance(secret_value_as_bool, bool):
                        return secret_value_as_bool
                    else:
                        return secret
            except Exception:
                return secret
        else:
            secret = os.environ.get(secret_name)
            secret_value_as_bool = str_to_bool(secret) if secret is not None else None
            if secret_value_as_bool is not None and isinstance(secret_value_as_bool, bool):
                return secret_value_as_bool
            else:
                return secret
    except Exception as e:
        if default_value is not None:
            return default_value
        else:
            raise e


def _should_read_secret_from_secret_manager() -> bool:
    """
    Returns True if the secret manager should be used to read the secret, False otherwise

    - If the secret manager client is not set, return False
    - If the `_key_management_settings` access mode is "read_only" or "read_and_write", return True
    - Otherwise, return False
    """
    if litellm.secret_manager_client is not None:
        if litellm._key_management_settings is not None:
            if (
                litellm._key_management_settings.access_mode == "read_only"
                or litellm._key_management_settings.access_mode == "read_and_write"
            ):
                return True
    return False

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\key_binding\bindings\mouse.py ===
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from prompt_toolkit.data_structures import Point
from prompt_toolkit.key_binding.key_processor import KeyPress, KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.mouse_events import (
    MouseButton,
    MouseEvent,
    MouseEventType,
    MouseModifier,
)

from ..key_bindings import KeyBindings

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone

__all__ = [
    "load_mouse_bindings",
]

E = KeyPressEvent

# fmt: off
SCROLL_UP   = MouseEventType.SCROLL_UP
SCROLL_DOWN = MouseEventType.SCROLL_DOWN
MOUSE_DOWN  = MouseEventType.MOUSE_DOWN
MOUSE_MOVE  = MouseEventType.MOUSE_MOVE
MOUSE_UP    = MouseEventType.MOUSE_UP

NO_MODIFIER      : frozenset[MouseModifier] = frozenset()
SHIFT            : frozenset[MouseModifier] = frozenset({MouseModifier.SHIFT})
ALT              : frozenset[MouseModifier] = frozenset({MouseModifier.ALT})
SHIFT_ALT        : frozenset[MouseModifier] = frozenset({MouseModifier.SHIFT, MouseModifier.ALT})
CONTROL          : frozenset[MouseModifier] = frozenset({MouseModifier.CONTROL})
SHIFT_CONTROL    : frozenset[MouseModifier] = frozenset({MouseModifier.SHIFT, MouseModifier.CONTROL})
ALT_CONTROL      : frozenset[MouseModifier] = frozenset({MouseModifier.ALT, MouseModifier.CONTROL})
SHIFT_ALT_CONTROL: frozenset[MouseModifier] = frozenset({MouseModifier.SHIFT, MouseModifier.ALT, MouseModifier.CONTROL})
UNKNOWN_MODIFIER : frozenset[MouseModifier] = frozenset()

LEFT           = MouseButton.LEFT
MIDDLE         = MouseButton.MIDDLE
RIGHT          = MouseButton.RIGHT
NO_BUTTON      = MouseButton.NONE
UNKNOWN_BUTTON = MouseButton.UNKNOWN

xterm_sgr_mouse_events = {
    ( 0, "m") : (LEFT, MOUSE_UP, NO_MODIFIER),                # left_up                       0+ + +  =0
    ( 4, "m") : (LEFT, MOUSE_UP, SHIFT),                      # left_up     Shift             0+4+ +  =4
    ( 8, "m") : (LEFT, MOUSE_UP, ALT),                        # left_up           Alt         0+ +8+  =8
    (12, "m") : (LEFT, MOUSE_UP, SHIFT_ALT),                  # left_up     Shift Alt         0+4+8+  =12
    (16, "m") : (LEFT, MOUSE_UP, CONTROL),                    # left_up               Control 0+ + +16=16
    (20, "m") : (LEFT, MOUSE_UP, SHIFT_CONTROL),              # left_up     Shift     Control 0+4+ +16=20
    (24, "m") : (LEFT, MOUSE_UP, ALT_CONTROL),                # left_up           Alt Control 0+ +8+16=24
    (28, "m") : (LEFT, MOUSE_UP, SHIFT_ALT_CONTROL),          # left_up     Shift Alt Control 0+4+8+16=28

    ( 1, "m") : (MIDDLE, MOUSE_UP, NO_MODIFIER),              # middle_up                     1+ + +  =1
    ( 5, "m") : (MIDDLE, MOUSE_UP, SHIFT),                    # middle_up   Shift             1+4+ +  =5
    ( 9, "m") : (MIDDLE, MOUSE_UP, ALT),                      # middle_up         Alt         1+ +8+  =9
    (13, "m") : (MIDDLE, MOUSE_UP, SHIFT_ALT),                # middle_up   Shift Alt         1+4+8+  =13
    (17, "m") : (MIDDLE, MOUSE_UP, CONTROL),                  # middle_up             Control 1+ + +16=17
    (21, "m") : (MIDDLE, MOUSE_UP, SHIFT_CONTROL),            # middle_up   Shift     Control 1+4+ +16=21
    (25, "m") : (MIDDLE, MOUSE_UP, ALT_CONTROL),              # middle_up         Alt Control 1+ +8+16=25
    (29, "m") : (MIDDLE, MOUSE_UP, SHIFT_ALT_CONTROL),        # middle_up   Shift Alt Control 1+4+8+16=29

    ( 2, "m") : (RIGHT, MOUSE_UP, NO_MODIFIER),               # right_up                      2+ + +  =2
    ( 6, "m") : (RIGHT, MOUSE_UP, SHIFT),                     # right_up    Shift             2+4+ +  =6
    (10, "m") : (RIGHT, MOUSE_UP, ALT),                       # right_up          Alt         2+ +8+  =10
    (14, "m") : (RIGHT, MOUSE_UP, SHIFT_ALT),                 # right_up    Shift Alt         2+4+8+  =14
    (18, "m") : (RIGHT, MOUSE_UP, CONTROL),                   # right_up              Control 2+ + +16=18
    (22, "m") : (RIGHT, MOUSE_UP, SHIFT_CONTROL),             # right_up    Shift     Control 2+4+ +16=22
    (26, "m") : (RIGHT, MOUSE_UP, ALT_CONTROL),               # right_up          Alt Control 2+ +8+16=26
    (30, "m") : (RIGHT, MOUSE_UP, SHIFT_ALT_CONTROL),         # right_up    Shift Alt Control 2+4+8+16=30

    ( 0, "M") : (LEFT, MOUSE_DOWN, NO_MODIFIER),              # left_down                     0+ + +  =0
    ( 4, "M") : (LEFT, MOUSE_DOWN, SHIFT),                    # left_down   Shift             0+4+ +  =4
    ( 8, "M") : (LEFT, MOUSE_DOWN, ALT),                      # left_down         Alt         0+ +8+  =8
    (12, "M") : (LEFT, MOUSE_DOWN, SHIFT_ALT),                # left_down   Shift Alt         0+4+8+  =12
    (16, "M") : (LEFT, MOUSE_DOWN, CONTROL),                  # left_down             Control 0+ + +16=16
    (20, "M") : (LEFT, MOUSE_DOWN, SHIFT_CONTROL),            # left_down   Shift     Control 0+4+ +16=20
    (24, "M") : (LEFT, MOUSE_DOWN, ALT_CONTROL),              # left_down         Alt Control 0+ +8+16=24
    (28, "M") : (LEFT, MOUSE_DOWN, SHIFT_ALT_CONTROL),        # left_down   Shift Alt Control 0+4+8+16=28

    ( 1, "M") : (MIDDLE, MOUSE_DOWN, NO_MODIFIER),            # middle_down                   1+ + +  =1
    ( 5, "M") : (MIDDLE, MOUSE_DOWN, SHIFT),                  # middle_down Shift             1+4+ +  =5
    ( 9, "M") : (MIDDLE, MOUSE_DOWN, ALT),                    # middle_down       Alt         1+ +8+  =9
    (13, "M") : (MIDDLE, MOUSE_DOWN, SHIFT_ALT),              # middle_down Shift Alt         1+4+8+  =13
    (17, "M") : (MIDDLE, MOUSE_DOWN, CONTROL),                # middle_down           Control 1+ + +16=17
    (21, "M") : (MIDDLE, MOUSE_DOWN, SHIFT_CONTROL),          # middle_down Shift     Control 1+4+ +16=21
    (25, "M") : (MIDDLE, MOUSE_DOWN, ALT_CONTROL),            # middle_down       Alt Control 1+ +8+16=25
    (29, "M") : (MIDDLE, MOUSE_DOWN, SHIFT_ALT_CONTROL),      # middle_down Shift Alt Control 1+4+8+16=29

    ( 2, "M") : (RIGHT, MOUSE_DOWN, NO_MODIFIER),             # right_down                    2+ + +  =2
    ( 6, "M") : (RIGHT, MOUSE_DOWN, SHIFT),                   # right_down  Shift             2+4+ +  =6
    (10, "M") : (RIGHT, MOUSE_DOWN, ALT),                     # right_down        Alt         2+ +8+  =10
    (14, "M") : (RIGHT, MOUSE_DOWN, SHIFT_ALT),               # right_down  Shift Alt         2+4+8+  =14
    (18, "M") : (RIGHT, MOUSE_DOWN, CONTROL),                 # right_down            Control 2+ + +16=18
    (22, "M") : (RIGHT, MOUSE_DOWN, SHIFT_CONTROL),           # right_down  Shift     Control 2+4+ +16=22
    (26, "M") : (RIGHT, MOUSE_DOWN, ALT_CONTROL),             # right_down        Alt Control 2+ +8+16=26
    (30, "M") : (RIGHT, MOUSE_DOWN, SHIFT_ALT_CONTROL),       # right_down  Shift Alt Control 2+4+8+16=30

    (32, "M") : (LEFT, MOUSE_MOVE, NO_MODIFIER),              # left_drag                     32+ + +  =32
    (36, "M") : (LEFT, MOUSE_MOVE, SHIFT),                    # left_drag   Shift             32+4+ +  =36
    (40, "M") : (LEFT, MOUSE_MOVE, ALT),                      # left_drag         Alt         32+ +8+  =40
    (44, "M") : (LEFT, MOUSE_MOVE, SHIFT_ALT),                # left_drag   Shift Alt         32+4+8+  =44
    (48, "M") : (LEFT, MOUSE_MOVE, CONTROL),                  # left_drag             Control 32+ + +16=48
    (52, "M") : (LEFT, MOUSE_MOVE, SHIFT_CONTROL),            # left_drag   Shift     Control 32+4+ +16=52
    (56, "M") : (LEFT, MOUSE_MOVE, ALT_CONTROL),              # left_drag         Alt Control 32+ +8+16=56
    (60, "M") : (LEFT, MOUSE_MOVE, SHIFT_ALT_CONTROL),        # left_drag   Shift Alt Control 32+4+8+16=60

    (33, "M") : (MIDDLE, MOUSE_MOVE, NO_MODIFIER),            # middle_drag                   33+ + +  =33
    (37, "M") : (MIDDLE, MOUSE_MOVE, SHIFT),                  # middle_drag Shift             33+4+ +  =37
    (41, "M") : (MIDDLE, MOUSE_MOVE, ALT),                    # middle_drag       Alt         33+ +8+  =41
    (45, "M") : (MIDDLE, MOUSE_MOVE, SHIFT_ALT),              # middle_drag Shift Alt         33+4+8+  =45
    (49, "M") : (MIDDLE, MOUSE_MOVE, CONTROL),                # middle_drag           Control 33+ + +16=49
    (53, "M") : (MIDDLE, MOUSE_MOVE, SHIFT_CONTROL),          # middle_drag Shift     Control 33+4+ +16=53
    (57, "M") : (MIDDLE, MOUSE_MOVE, ALT_CONTROL),            # middle_drag       Alt Control 33+ +8+16=57
    (61, "M") : (MIDDLE, MOUSE_MOVE, SHIFT_ALT_CONTROL),      # middle_drag Shift Alt Control 33+4+8+16=61

    (34, "M") : (RIGHT, MOUSE_MOVE, NO_MODIFIER),             # right_drag                    34+ + +  =34
    (38, "M") : (RIGHT, MOUSE_MOVE, SHIFT),                   # right_drag  Shift             34+4+ +  =38
    (42, "M") : (RIGHT, MOUSE_MOVE, ALT),                     # right_drag        Alt         34+ +8+  =42
    (46, "M") : (RIGHT, MOUSE_MOVE, SHIFT_ALT),               # right_drag  Shift Alt         34+4+8+  =46
    (50, "M") : (RIGHT, MOUSE_MOVE, CONTROL),                 # right_drag            Control 34+ + +16=50
    (54, "M") : (RIGHT, MOUSE_MOVE, SHIFT_CONTROL),           # right_drag  Shift     Control 34+4+ +16=54
    (58, "M") : (RIGHT, MOUSE_MOVE, ALT_CONTROL),             # right_drag        Alt Control 34+ +8+16=58
    (62, "M") : (RIGHT, MOUSE_MOVE, SHIFT_ALT_CONTROL),       # right_drag  Shift Alt Control 34+4+8+16=62

    (35, "M") : (NO_BUTTON, MOUSE_MOVE, NO_MODIFIER),         # none_drag                     35+ + +  =35
    (39, "M") : (NO_BUTTON, MOUSE_MOVE, SHIFT),               # none_drag   Shift             35+4+ +  =39
    (43, "M") : (NO_BUTTON, MOUSE_MOVE, ALT),                 # none_drag         Alt         35+ +8+  =43
    (47, "M") : (NO_BUTTON, MOUSE_MOVE, SHIFT_ALT),           # none_drag   Shift Alt         35+4+8+  =47
    (51, "M") : (NO_BUTTON, MOUSE_MOVE, CONTROL),             # none_drag             Control 35+ + +16=51
    (55, "M") : (NO_BUTTON, MOUSE_MOVE, SHIFT_CONTROL),       # none_drag   Shift     Control 35+4+ +16=55
    (59, "M") : (NO_BUTTON, MOUSE_MOVE, ALT_CONTROL),         # none_drag         Alt Control 35+ +8+16=59
    (63, "M") : (NO_BUTTON, MOUSE_MOVE, SHIFT_ALT_CONTROL),   # none_drag   Shift Alt Control 35+4+8+16=63

    (64, "M") : (NO_BUTTON, SCROLL_UP, NO_MODIFIER),          # scroll_up                     64+ + +  =64
    (68, "M") : (NO_BUTTON, SCROLL_UP, SHIFT),                # scroll_up   Shift             64+4+ +  =68
    (72, "M") : (NO_BUTTON, SCROLL_UP, ALT),                  # scroll_up         Alt         64+ +8+  =72
    (76, "M") : (NO_BUTTON, SCROLL_UP, SHIFT_ALT),            # scroll_up   Shift Alt         64+4+8+  =76
    (80, "M") : (NO_BUTTON, SCROLL_UP, CONTROL),              # scroll_up             Control 64+ + +16=80
    (84, "M") : (NO_BUTTON, SCROLL_UP, SHIFT_CONTROL),        # scroll_up   Shift     Control 64+4+ +16=84
    (88, "M") : (NO_BUTTON, SCROLL_UP, ALT_CONTROL),          # scroll_up         Alt Control 64+ +8+16=88
    (92, "M") : (NO_BUTTON, SCROLL_UP, SHIFT_ALT_CONTROL),    # scroll_up   Shift Alt Control 64+4+8+16=92

    (65, "M") : (NO_BUTTON, SCROLL_DOWN, NO_MODIFIER),        # scroll_down                   64+ + +  =65
    (69, "M") : (NO_BUTTON, SCROLL_DOWN, SHIFT),              # scroll_down Shift             64+4+ +  =69
    (73, "M") : (NO_BUTTON, SCROLL_DOWN, ALT),                # scroll_down       Alt         64+ +8+  =73
    (77, "M") : (NO_BUTTON, SCROLL_DOWN, SHIFT_ALT),          # scroll_down Shift Alt         64+4+8+  =77
    (81, "M") : (NO_BUTTON, SCROLL_DOWN, CONTROL),            # scroll_down           Control 64+ + +16=81
    (85, "M") : (NO_BUTTON, SCROLL_DOWN, SHIFT_CONTROL),      # scroll_down Shift     Control 64+4+ +16=85
    (89, "M") : (NO_BUTTON, SCROLL_DOWN, ALT_CONTROL),        # scroll_down       Alt Control 64+ +8+16=89
    (93, "M") : (NO_BUTTON, SCROLL_DOWN, SHIFT_ALT_CONTROL),  # scroll_down Shift Alt Control 64+4+8+16=93
}

typical_mouse_events = {
    32: (LEFT           , MOUSE_DOWN , UNKNOWN_MODIFIER),
    33: (MIDDLE         , MOUSE_DOWN , UNKNOWN_MODIFIER),
    34: (RIGHT          , MOUSE_DOWN , UNKNOWN_MODIFIER),
    35: (UNKNOWN_BUTTON , MOUSE_UP   , UNKNOWN_MODIFIER),

    64: (LEFT           , MOUSE_MOVE , UNKNOWN_MODIFIER),
    65: (MIDDLE         , MOUSE_MOVE , UNKNOWN_MODIFIER),
    66: (RIGHT          , MOUSE_MOVE , UNKNOWN_MODIFIER),
    67: (NO_BUTTON      , MOUSE_MOVE , UNKNOWN_MODIFIER),

    96: (NO_BUTTON      , SCROLL_UP  , UNKNOWN_MODIFIER),
    97: (NO_BUTTON      , SCROLL_DOWN, UNKNOWN_MODIFIER),
}

urxvt_mouse_events={
    32: (UNKNOWN_BUTTON, MOUSE_DOWN , UNKNOWN_MODIFIER),
    35: (UNKNOWN_BUTTON, MOUSE_UP   , UNKNOWN_MODIFIER),
    96: (NO_BUTTON     , SCROLL_UP  , UNKNOWN_MODIFIER),
    97: (NO_BUTTON     , SCROLL_DOWN, UNKNOWN_MODIFIER),
}
# fmt:on


def load_mouse_bindings() -> KeyBindings:
    """
    Key bindings, required for mouse support.
    (Mouse events enter through the key binding system.)
    """
    key_bindings = KeyBindings()

    @key_bindings.add(Keys.Vt100MouseEvent)
    def _(event: E) -> NotImplementedOrNone:
        """
        Handling of incoming mouse event.
        """
        # TypicaL:   "eSC[MaB*"
        # Urxvt:     "Esc[96;14;13M"
        # Xterm SGR: "Esc[<64;85;12M"

        # Parse incoming packet.
        if event.data[2] == "M":
            # Typical.
            mouse_event, x, y = map(ord, event.data[3:])

            # TODO: Is it possible to add modifiers here?
            mouse_button, mouse_event_type, mouse_modifiers = typical_mouse_events[
                mouse_event
            ]

            # Handle situations where `PosixStdinReader` used surrogateescapes.
            if x >= 0xDC00:
                x -= 0xDC00
            if y >= 0xDC00:
                y -= 0xDC00

            x -= 32
            y -= 32
        else:
            # Urxvt and Xterm SGR.
            # When the '<' is not present, we are not using the Xterm SGR mode,
            # but Urxvt instead.
            data = event.data[2:]
            if data[:1] == "<":
                sgr = True
                data = data[1:]
            else:
                sgr = False

            # Extract coordinates.
            mouse_event, x, y = map(int, data[:-1].split(";"))
            m = data[-1]

            # Parse event type.
            if sgr:
                try:
                    (
                        mouse_button,
                        mouse_event_type,
                        mouse_modifiers,
                    ) = xterm_sgr_mouse_events[mouse_event, m]
                except KeyError:
                    return NotImplemented

            else:
                # Some other terminals, like urxvt, Hyper terminal, ...
                (
                    mouse_button,
                    mouse_event_type,
                    mouse_modifiers,
                ) = urxvt_mouse_events.get(
                    mouse_event, (UNKNOWN_BUTTON, MOUSE_MOVE, UNKNOWN_MODIFIER)
                )

        x -= 1
        y -= 1

        # Only handle mouse events when we know the window height.
        if event.app.renderer.height_is_known and mouse_event_type is not None:
            # Take region above the layout into account. The reported
            # coordinates are absolute to the visible part of the terminal.
            from prompt_toolkit.renderer import HeightIsUnknownError

            try:
                y -= event.app.renderer.rows_above_layout
            except HeightIsUnknownError:
                return NotImplemented

            # Call the mouse handler from the renderer.

            # Note: This can return `NotImplemented` if no mouse handler was
            #       found for this position, or if no repainting needs to
            #       happen. this way, we avoid excessive repaints during mouse
            #       movements.
            handler = event.app.renderer.mouse_handlers.mouse_handlers[y][x]
            return handler(
                MouseEvent(
                    position=Point(x=x, y=y),
                    event_type=mouse_event_type,
                    button=mouse_button,
                    modifiers=mouse_modifiers,
                )
            )

        return NotImplemented

    @key_bindings.add(Keys.ScrollUp)
    def _scroll_up(event: E) -> None:
        """
        Scroll up event without cursor position.
        """
        # We don't receive a cursor position, so we don't know which window to
        # scroll. Just send an 'up' key press instead.
        event.key_processor.feed(KeyPress(Keys.Up), first=True)

    @key_bindings.add(Keys.ScrollDown)
    def _scroll_down(event: E) -> None:
        """
        Scroll down event without cursor position.
        """
        event.key_processor.feed(KeyPress(Keys.Down), first=True)

    @key_bindings.add(Keys.WindowsMouseEvent)
    def _mouse(event: E) -> NotImplementedOrNone:
        """
        Handling of mouse events for Windows.
        """
        # This key binding should only exist for Windows.
        if sys.platform == "win32":
            # Parse data.
            pieces = event.data.split(";")

            button = MouseButton(pieces[0])
            event_type = MouseEventType(pieces[1])
            x = int(pieces[2])
            y = int(pieces[3])

            # Make coordinates absolute to the visible part of the terminal.
            output = event.app.renderer.output

            from prompt_toolkit.output.win32 import Win32Output
            from prompt_toolkit.output.windows10 import Windows10_Output

            if isinstance(output, (Win32Output, Windows10_Output)):
                screen_buffer_info = output.get_win32_screen_buffer_info()
                rows_above_cursor = (
                    screen_buffer_info.dwCursorPosition.Y
                    - event.app.renderer._cursor_pos.y
                )
                y -= rows_above_cursor

                # Call the mouse event handler.
                # (Can return `NotImplemented`.)
                handler = event.app.renderer.mouse_handlers.mouse_handlers[y][x]

                return handler(
                    MouseEvent(
                        position=Point(x=x, y=y),
                        event_type=event_type,
                        button=button,
                        modifiers=UNKNOWN_MODIFIER,
                    )
                )

        # No mouse handler found. Return `NotImplemented` so that we don't
        # invalidate the UI.
        return NotImplemented

    return key_bindings

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\version.py ===
#
# distutils/version.py
#
# Implements multiple version numbering conventions for the
# Python Module Distribution Utilities.
#
# $Id$
#

"""Provides classes to represent module version numbers (one class for
each style of version numbering).  There are currently two such classes
implemented: StrictVersion and LooseVersion.

Every version number class implements the following interface:
  * the 'parse' method takes a string and parses it to some internal
    representation; if the string is an invalid version number,
    'parse' raises a ValueError exception
  * the class constructor takes an optional string argument which,
    if supplied, is passed to 'parse'
  * __str__ reconstructs the string that was passed to 'parse' (or
    an equivalent string -- ie. one that will generate an equivalent
    version number instance)
  * __repr__ generates Python code to recreate the version number instance
  * _cmp compares the current instance with either another instance
    of the same class or a string (which will be parsed to an instance
    of the same class, thus must follow the same rules)
"""

import contextlib
import re
import warnings


@contextlib.contextmanager
def suppress_known_deprecation():
    with warnings.catch_warnings(record=True) as ctx:
        warnings.filterwarnings(
            action='default',
            category=DeprecationWarning,
            message="distutils Version classes are deprecated.",
        )
        yield ctx


class Version:
    """Abstract base class for version numbering classes.  Just provides
    constructor (__init__) and reproducer (__repr__), because those
    seem to be the same for all version numbering classes; and route
    rich comparisons to _cmp.
    """

    def __init__(self, vstring=None):
        if vstring:
            self.parse(vstring)
        warnings.warn(
            "distutils Version classes are deprecated. Use packaging.version instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def __repr__(self):
        return f"{self.__class__.__name__} ('{self}')"

    def __eq__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c == 0

    def __lt__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c < 0

    def __le__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c <= 0

    def __gt__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c > 0

    def __ge__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c >= 0


# Interface for version-number classes -- must be implemented
# by the following classes (the concrete ones -- Version should
# be treated as an abstract class).
#    __init__ (string) - create and take same action as 'parse'
#                        (string parameter is optional)
#    parse (string)    - convert a string representation to whatever
#                        internal representation is appropriate for
#                        this style of version numbering
#    __str__ (self)    - convert back to a string; should be very similar
#                        (if not identical to) the string supplied to parse
#    __repr__ (self)   - generate Python code to recreate
#                        the instance
#    _cmp (self, other) - compare two version numbers ('other' may
#                        be an unparsed version string, or another
#                        instance of your version class)


class StrictVersion(Version):
    """Version numbering for anal retentives and software idealists.
    Implements the standard interface for version number classes as
    described above.  A version number consists of two or three
    dot-separated numeric components, with an optional "pre-release" tag
    on the end.  The pre-release tag consists of the letter 'a' or 'b'
    followed by a number.  If the numeric components of two version
    numbers are equal, then one with a pre-release tag will always
    be deemed earlier (lesser) than one without.

    The following are valid version numbers (shown in the order that
    would be obtained by sorting according to the supplied cmp function):

        0.4       0.4.0  (these two are equivalent)
        0.4.1
        0.5a1
        0.5b3
        0.5
        0.9.6
        1.0
        1.0.4a3
        1.0.4b1
        1.0.4

    The following are examples of invalid version numbers:

        1
        2.7.2.2
        1.3.a4
        1.3pl1
        1.3c4

    The rationale for this version numbering system will be explained
    in the distutils documentation.
    """

    version_re = re.compile(
        r'^(\d+) \. (\d+) (\. (\d+))? ([ab](\d+))?$', re.VERBOSE | re.ASCII
    )

    def parse(self, vstring):
        match = self.version_re.match(vstring)
        if not match:
            raise ValueError(f"invalid version number '{vstring}'")

        (major, minor, patch, prerelease, prerelease_num) = match.group(1, 2, 4, 5, 6)

        if patch:
            self.version = tuple(map(int, [major, minor, patch]))
        else:
            self.version = tuple(map(int, [major, minor])) + (0,)

        if prerelease:
            self.prerelease = (prerelease[0], int(prerelease_num))
        else:
            self.prerelease = None

    def __str__(self):
        if self.version[2] == 0:
            vstring = '.'.join(map(str, self.version[0:2]))
        else:
            vstring = '.'.join(map(str, self.version))

        if self.prerelease:
            vstring = vstring + self.prerelease[0] + str(self.prerelease[1])

        return vstring

    def _cmp(self, other):
        if isinstance(other, str):
            with suppress_known_deprecation():
                other = StrictVersion(other)
        elif not isinstance(other, StrictVersion):
            return NotImplemented

        if self.version == other.version:
            # versions match; pre-release drives the comparison
            return self._cmp_prerelease(other)

        return -1 if self.version < other.version else 1

    def _cmp_prerelease(self, other):
        """
        case 1: self has prerelease, other doesn't; other is greater
        case 2: self doesn't have prerelease, other does: self is greater
        case 3: both or neither have prerelease: compare them!
        """
        if self.prerelease and not other.prerelease:
            return -1
        elif not self.prerelease and other.prerelease:
            return 1

        if self.prerelease == other.prerelease:
            return 0
        elif self.prerelease < other.prerelease:
            return -1
        else:
            return 1


# end class StrictVersion


# The rules according to Greg Stein:
# 1) a version number has 1 or more numbers separated by a period or by
#    sequences of letters. If only periods, then these are compared
#    left-to-right to determine an ordering.
# 2) sequences of letters are part of the tuple for comparison and are
#    compared lexicographically
# 3) recognize the numeric components may have leading zeroes
#
# The LooseVersion class below implements these rules: a version number
# string is split up into a tuple of integer and string components, and
# comparison is a simple tuple comparison.  This means that version
# numbers behave in a predictable and obvious way, but a way that might
# not necessarily be how people *want* version numbers to behave.  There
# wouldn't be a problem if people could stick to purely numeric version
# numbers: just split on period and compare the numbers as tuples.
# However, people insist on putting letters into their version numbers;
# the most common purpose seems to be:
#   - indicating a "pre-release" version
#     ('alpha', 'beta', 'a', 'b', 'pre', 'p')
#   - indicating a post-release patch ('p', 'pl', 'patch')
# but of course this can't cover all version number schemes, and there's
# no way to know what a programmer means without asking him.
#
# The problem is what to do with letters (and other non-numeric
# characters) in a version number.  The current implementation does the
# obvious and predictable thing: keep them as strings and compare
# lexically within a tuple comparison.  This has the desired effect if
# an appended letter sequence implies something "post-release":
# eg. "0.99" < "0.99pl14" < "1.0", and "5.001" < "5.001m" < "5.002".
#
# However, if letters in a version number imply a pre-release version,
# the "obvious" thing isn't correct.  Eg. you would expect that
# "1.5.1" < "1.5.2a2" < "1.5.2", but under the tuple/lexical comparison
# implemented here, this just isn't so.
#
# Two possible solutions come to mind.  The first is to tie the
# comparison algorithm to a particular set of semantic rules, as has
# been done in the StrictVersion class above.  This works great as long
# as everyone can go along with bondage and discipline.  Hopefully a
# (large) subset of Python module programmers will agree that the
# particular flavour of bondage and discipline provided by StrictVersion
# provides enough benefit to be worth using, and will submit their
# version numbering scheme to its domination.  The free-thinking
# anarchists in the lot will never give in, though, and something needs
# to be done to accommodate them.
#
# Perhaps a "moderately strict" version class could be implemented that
# lets almost anything slide (syntactically), and makes some heuristic
# assumptions about non-digits in version number strings.  This could
# sink into special-case-hell, though; if I was as talented and
# idiosyncratic as Larry Wall, I'd go ahead and implement a class that
# somehow knows that "1.2.1" < "1.2.2a2" < "1.2.2" < "1.2.2pl3", and is
# just as happy dealing with things like "2g6" and "1.13++".  I don't
# think I'm smart enough to do it right though.
#
# In any case, I've coded the test suite for this module (see
# ../test/test_version.py) specifically to fail on things like comparing
# "1.2a2" and "1.2".  That's not because the *code* is doing anything
# wrong, it's because the simple, obvious design doesn't match my
# complicated, hairy expectations for real-world version numbers.  It
# would be a snap to fix the test suite to say, "Yep, LooseVersion does
# the Right Thing" (ie. the code matches the conception).  But I'd rather
# have a conception that matches common notions about version numbers.


class LooseVersion(Version):
    """Version numbering for anarchists and software realists.
    Implements the standard interface for version number classes as
    described above.  A version number consists of a series of numbers,
    separated by either periods or strings of letters.  When comparing
    version numbers, the numeric components will be compared
    numerically, and the alphabetic components lexically.  The following
    are all valid version numbers, in no particular order:

        1.5.1
        1.5.2b2
        161
        3.10a
        8.02
        3.4j
        1996.07.12
        3.2.pl0
        3.1.1.6
        2g6
        11g
        0.960923
        2.2beta29
        1.13++
        5.5.kw
        2.0b1pl0

    In fact, there is no such thing as an invalid version number under
    this scheme; the rules for comparison are simple and predictable,
    but may not always give the results you want (for some definition
    of "want").
    """

    component_re = re.compile(r'(\d+ | [a-z]+ | \.)', re.VERBOSE)

    def parse(self, vstring):
        # I've given up on thinking I can reconstruct the version string
        # from the parsed tuple -- so I just store the string here for
        # use by __str__
        self.vstring = vstring
        components = [x for x in self.component_re.split(vstring) if x and x != '.']
        for i, obj in enumerate(components):
            try:
                components[i] = int(obj)
            except ValueError:
                pass

        self.version = components

    def __str__(self):
        return self.vstring

    def __repr__(self):
        return f"LooseVersion ('{self}')"

    def _cmp(self, other):
        if isinstance(other, str):
            other = LooseVersion(other)
        elif not isinstance(other, LooseVersion):
            return NotImplemented

        if self.version == other.version:
            return 0
        if self.version < other.version:
            return -1
        if self.version > other.version:
            return 1


# end class LooseVersion

# === NexusCore/openenv\Lib\site-packages\google\generativeai\text.py ===
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
from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Sequence
import itertools
from typing import Any, Iterable, overload, TypeVar

import google.ai.generativelanguage as glm

from google.generativeai import protos

from google.generativeai.client import get_default_text_client
from google.generativeai import string_utils
from google.generativeai.types import helper_types
from google.generativeai.types import text_types
from google.generativeai.types import model_types
from google.generativeai import models
from google.generativeai.types import palm_safety_types

DEFAULT_TEXT_MODEL = "models/text-bison-001"
EMBEDDING_MAX_BATCH_SIZE = 100

try:
    # python 3.12+
    _batched = itertools.batched  # type: ignore
except AttributeError:
    T = TypeVar("T")

    def _batched(iterable: Iterable[T], n: int) -> Iterable[list[T]]:
        if n < 1:
            raise ValueError(f"Batch size `n` must be >1, got: {n}")
        batch = []
        for item in iterable:
            batch.append(item)
            if len(batch) == n:
                yield batch
                batch = []

        if batch:
            yield batch


def _make_text_prompt(prompt: str | dict[str, str]) -> protos.TextPrompt:
    """
    Creates a `protos.TextPrompt` object based on the provided prompt input.

    Args:
        prompt: The prompt input, either a string or a dictionary.

    Returns:
        protos.TextPrompt: A TextPrompt object containing the prompt text.

    Raises:
        TypeError: If the provided prompt is neither a string nor a dictionary.
    """
    if isinstance(prompt, str):
        return protos.TextPrompt(text=prompt)
    elif isinstance(prompt, dict):
        return protos.TextPrompt(prompt)
    else:
        raise TypeError(
            "Invalid argument type: Expected a string or dictionary for the text prompt."
        )


def _make_generate_text_request(
    *,
    model: model_types.AnyModelNameOptions = DEFAULT_TEXT_MODEL,
    prompt: str | None = None,
    temperature: float | None = None,
    candidate_count: int | None = None,
    max_output_tokens: int | None = None,
    top_p: int | None = None,
    top_k: int | None = None,
    safety_settings: palm_safety_types.SafetySettingOptions | None = None,
    stop_sequences: str | Iterable[str] | None = None,
) -> protos.GenerateTextRequest:
    """
    Creates a `protos.GenerateTextRequest` object based on the provided parameters.

    This function generates a `protos.GenerateTextRequest` object with the specified
    parameters. It prepares the input parameters and creates a request that can be
    used for generating text using the chosen model.

    Args:
        model: The model to use for text generation.
        prompt: The prompt for text generation. Defaults to None.
        temperature: The temperature for randomness in generation. Defaults to None.
        candidate_count: The number of candidates to consider. Defaults to None.
        max_output_tokens: The maximum number of output tokens. Defaults to None.
        top_p: The nucleus sampling probability threshold. Defaults to None.
        top_k: The top-k sampling parameter. Defaults to None.
        safety_settings: Safety settings for generated text. Defaults to None.
        stop_sequences: Stop sequences to halt text generation. Can be a string
             or iterable of strings. Defaults to None.

    Returns:
        `protos.GenerateTextRequest`: A `GenerateTextRequest` object configured with the specified parameters.
    """
    model = model_types.make_model_name(model)
    prompt = _make_text_prompt(prompt=prompt)
    safety_settings = palm_safety_types.normalize_safety_settings(safety_settings)
    if isinstance(stop_sequences, str):
        stop_sequences = [stop_sequences]
    if stop_sequences:
        stop_sequences = list(stop_sequences)

    return protos.GenerateTextRequest(
        model=model,
        prompt=prompt,
        temperature=temperature,
        candidate_count=candidate_count,
        max_output_tokens=max_output_tokens,
        top_p=top_p,
        top_k=top_k,
        safety_settings=safety_settings,
        stop_sequences=stop_sequences,
    )


def generate_text(
    *,
    model: model_types.AnyModelNameOptions = DEFAULT_TEXT_MODEL,
    prompt: str,
    temperature: float | None = None,
    candidate_count: int | None = None,
    max_output_tokens: int | None = None,
    top_p: float | None = None,
    top_k: float | None = None,
    safety_settings: palm_safety_types.SafetySettingOptions | None = None,
    stop_sequences: str | Iterable[str] | None = None,
    client: glm.TextServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> text_types.Completion:
    """Calls the API to generate text based on the provided prompt.

    Args:
        model: Which model to call, as a string or a `types.Model`.
        prompt: Free-form input text given to the model. Given a prompt, the model will
                generate text that completes the input text.
        temperature: Controls the randomness of the output. Must be positive.
            Typical values are in the range: `[0.0,1.0]`. Higher values produce a
            more random and varied response. A temperature of zero will be deterministic.
        candidate_count: The **maximum** number of generated response messages to return.
            This value must be between `[1, 8]`, inclusive. If unset, this
            will default to `1`.

            Note: Only unique candidates are returned. Higher temperatures are more
            likely to produce unique candidates. Setting `temperature=0.0` will always
            return 1 candidate regardless of the `candidate_count`.
        max_output_tokens: Maximum number of tokens to include in a candidate. Must be greater
                           than zero. If unset, will default to 64.
        top_k: The API uses combined [nucleus](https://arxiv.org/abs/1904.09751) and top-k sampling.
            `top_k` sets the maximum number of tokens to sample from on each step.
        top_p: The API uses combined [nucleus](https://arxiv.org/abs/1904.09751) and top-k sampling.
            `top_p` configures the nucleus sampling. It sets the maximum cumulative
            probability of tokens to sample from.
            For example, if the sorted probabilities are
            `[0.5, 0.2, 0.1, 0.1, 0.05, 0.05]` a `top_p` of `0.8` will sample
            as `[0.625, 0.25, 0.125, 0, 0, 0]`.
        safety_settings: A list of unique `types.SafetySetting` instances for blocking unsafe content.
           These will be enforced on the `prompt` and
           `candidates`. There should not be more than one
           setting for each `types.SafetyCategory` type. The API will block any prompts and
           responses that fail to meet the thresholds set by these settings. This list
           overrides the default settings for each `SafetyCategory` specified in the
           safety_settings. If there is no `types.SafetySetting` for a given
           `SafetyCategory` provided in the list, the API will use the default safety
           setting for that category.
        stop_sequences: A set of up to 5 character sequences that will stop output generation.
          If specified, the API will stop at the first appearance of a stop
          sequence. The stop sequence will not be included as part of the response.
        client: If you're not relying on a default client, you pass a `glm.TextServiceClient` instead.
        request_options: Options for the request.

    Returns:
        A `types.Completion` containing the model's text completion response.
    """
    request = _make_generate_text_request(
        model=model,
        prompt=prompt,
        temperature=temperature,
        candidate_count=candidate_count,
        max_output_tokens=max_output_tokens,
        top_p=top_p,
        top_k=top_k,
        safety_settings=safety_settings,
        stop_sequences=stop_sequences,
    )

    return _generate_response(client=client, request=request, request_options=request_options)


@string_utils.prettyprint
@dataclasses.dataclass(init=False)
class Completion(text_types.Completion):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.result = None
        if self.candidates:
            self.result = self.candidates[0]["output"]


def _generate_response(
    request: protos.GenerateTextRequest,
    client: glm.TextServiceClient = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> Completion:
    """
    Generates a response using the provided `protos.GenerateTextRequest` and client.

    Args:
        request: The text generation request.
        client: The client to use for text generation. Defaults to None, in which
            case the default text client is used.
        request_options: Options for the request.

    Returns:
        `Completion`: A `Completion` object with the generated text and response information.
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_text_client()

    response = client.generate_text(request, **request_options)
    response = type(response).to_dict(response)

    response["filters"] = palm_safety_types.convert_filters_to_enums(response["filters"])
    response["safety_feedback"] = palm_safety_types.convert_safety_feedback_to_enums(
        response["safety_feedback"]
    )
    response["candidates"] = palm_safety_types.convert_candidate_enums(response["candidates"])

    return Completion(_client=client, **response)


def count_text_tokens(
    model: model_types.AnyModelNameOptions,
    prompt: str,
    client: glm.TextServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> text_types.TokenCount:
    """Calls the API to count the number of tokens in the text prompt."""

    base_model = models.get_base_model_name(model)

    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_text_client()

    result = client.count_text_tokens(
        protos.CountTextTokensRequest(model=base_model, prompt={"text": prompt}),
        **request_options,
    )

    return type(result).to_dict(result)


@overload
def generate_embeddings(
    model: model_types.BaseModelNameOptions,
    text: str,
    client: glm.TextServiceClient = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> text_types.EmbeddingDict: ...


@overload
def generate_embeddings(
    model: model_types.BaseModelNameOptions,
    text: Sequence[str],
    client: glm.TextServiceClient = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> text_types.BatchEmbeddingDict: ...


def generate_embeddings(
    model: model_types.BaseModelNameOptions,
    text: str | Sequence[str],
    client: glm.TextServiceClient = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> text_types.EmbeddingDict | text_types.BatchEmbeddingDict:
    """Calls the API to create an embedding for the text passed in.

    Args:
        model: Which model to call, as a string or a `types.Model`.

        text: Free-form input text given to the model. Given a string, the model will
              generate an embedding based on the input text.

        client: If you're not relying on a default client, you pass a `glm.TextServiceClient` instead.

        request_options: Options for the request.

    Returns:
        Dictionary containing the embedding (list of float values) for the input text.
    """
    model = model_types.make_model_name(model)

    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_text_client()

    if isinstance(text, str):
        embedding_request = protos.EmbedTextRequest(model=model, text=text)
        embedding_response = client.embed_text(
            embedding_request,
            **request_options,
        )
        embedding_dict = type(embedding_response).to_dict(embedding_response)
        embedding_dict["embedding"] = embedding_dict["embedding"]["value"]
    else:
        result = {"embedding": []}
        for batch in _batched(text, EMBEDDING_MAX_BATCH_SIZE):
            # TODO(markdaoust): This could use an option for returning an iterator or wait-bar.
            embedding_request = protos.BatchEmbedTextRequest(model=model, texts=batch)
            embedding_response = client.batch_embed_text(
                embedding_request,
                **request_options,
            )
            embedding_dict = type(embedding_response).to_dict(embedding_response)
            result["embedding"].extend(e["value"] for e in embedding_dict["embeddings"])
        return result

    return embedding_dict

# === NexusCore/openenv\Lib\site-packages\nltk\classify\util.py ===
# Natural Language Toolkit: Classifier Utility Functions
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com> (minor additions)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Utility functions and classes for classifiers.
"""

import math

# from nltk.util import Deprecated
import nltk.classify.util  # for accuracy & log_likelihood
from nltk.util import LazyMap

######################################################################
# { Helper Functions
######################################################################


# alternative name possibility: 'map_featurefunc()'?
# alternative name possibility: 'detect_features()'?
# alternative name possibility: 'map_featuredetect()'?
# or.. just have users use LazyMap directly?
def apply_features(feature_func, toks, labeled=None):
    """
    Use the ``LazyMap`` class to construct a lazy list-like
    object that is analogous to ``map(feature_func, toks)``.  In
    particular, if ``labeled=False``, then the returned list-like
    object's values are equal to::

        [feature_func(tok) for tok in toks]

    If ``labeled=True``, then the returned list-like object's values
    are equal to::

        [(feature_func(tok), label) for (tok, label) in toks]

    The primary purpose of this function is to avoid the memory
    overhead involved in storing all the featuresets for every token
    in a corpus.  Instead, these featuresets are constructed lazily,
    as-needed.  The reduction in memory overhead can be especially
    significant when the underlying list of tokens is itself lazy (as
    is the case with many corpus readers).

    :param feature_func: The function that will be applied to each
        token.  It should return a featureset -- i.e., a dict
        mapping feature names to feature values.
    :param toks: The list of tokens to which ``feature_func`` should be
        applied.  If ``labeled=True``, then the list elements will be
        passed directly to ``feature_func()``.  If ``labeled=False``,
        then the list elements should be tuples ``(tok,label)``, and
        ``tok`` will be passed to ``feature_func()``.
    :param labeled: If true, then ``toks`` contains labeled tokens --
        i.e., tuples of the form ``(tok, label)``.  (Default:
        auto-detect based on types.)
    """
    if labeled is None:
        labeled = toks and isinstance(toks[0], (tuple, list))
    if labeled:

        def lazy_func(labeled_token):
            return (feature_func(labeled_token[0]), labeled_token[1])

        return LazyMap(lazy_func, toks)
    else:
        return LazyMap(feature_func, toks)


def attested_labels(tokens):
    """
    :return: A list of all labels that are attested in the given list
        of tokens.
    :rtype: list of (immutable)
    :param tokens: The list of classified tokens from which to extract
        labels.  A classified token has the form ``(token, label)``.
    :type tokens: list
    """
    return tuple({label for (tok, label) in tokens})


def log_likelihood(classifier, gold):
    results = classifier.prob_classify_many([fs for (fs, l) in gold])
    ll = [pdist.prob(l) for ((fs, l), pdist) in zip(gold, results)]
    return math.log(sum(ll) / len(ll))


def accuracy(classifier, gold):
    results = classifier.classify_many([fs for (fs, l) in gold])
    correct = [l == r for ((fs, l), r) in zip(gold, results)]
    if correct:
        return sum(correct) / len(correct)
    else:
        return 0


class CutoffChecker:
    """
    A helper class that implements cutoff checks based on number of
    iterations and log likelihood.

    Accuracy cutoffs are also implemented, but they're almost never
    a good idea to use.
    """

    def __init__(self, cutoffs):
        self.cutoffs = cutoffs.copy()
        if "min_ll" in cutoffs:
            cutoffs["min_ll"] = -abs(cutoffs["min_ll"])
        if "min_lldelta" in cutoffs:
            cutoffs["min_lldelta"] = abs(cutoffs["min_lldelta"])
        self.ll = None
        self.acc = None
        self.iter = 1

    def check(self, classifier, train_toks):
        cutoffs = self.cutoffs
        self.iter += 1
        if "max_iter" in cutoffs and self.iter >= cutoffs["max_iter"]:
            return True  # iteration cutoff.

        new_ll = nltk.classify.util.log_likelihood(classifier, train_toks)
        if math.isnan(new_ll):
            return True

        if "min_ll" in cutoffs or "min_lldelta" in cutoffs:
            if "min_ll" in cutoffs and new_ll >= cutoffs["min_ll"]:
                return True  # log likelihood cutoff
            if (
                "min_lldelta" in cutoffs
                and self.ll
                and ((new_ll - self.ll) <= abs(cutoffs["min_lldelta"]))
            ):
                return True  # log likelihood delta cutoff
            self.ll = new_ll

        if "max_acc" in cutoffs or "min_accdelta" in cutoffs:
            new_acc = nltk.classify.util.log_likelihood(classifier, train_toks)
            if "max_acc" in cutoffs and new_acc >= cutoffs["max_acc"]:
                return True  # log likelihood cutoff
            if (
                "min_accdelta" in cutoffs
                and self.acc
                and ((new_acc - self.acc) <= abs(cutoffs["min_accdelta"]))
            ):
                return True  # log likelihood delta cutoff
            self.acc = new_acc

            return False  # no cutoff reached.


######################################################################
# { Demos
######################################################################


def names_demo_features(name):
    features = {}
    features["alwayson"] = True
    features["startswith"] = name[0].lower()
    features["endswith"] = name[-1].lower()
    for letter in "abcdefghijklmnopqrstuvwxyz":
        features["count(%s)" % letter] = name.lower().count(letter)
        features["has(%s)" % letter] = letter in name.lower()
    return features


def binary_names_demo_features(name):
    features = {}
    features["alwayson"] = True
    features["startswith(vowel)"] = name[0].lower() in "aeiouy"
    features["endswith(vowel)"] = name[-1].lower() in "aeiouy"
    for letter in "abcdefghijklmnopqrstuvwxyz":
        features["count(%s)" % letter] = name.lower().count(letter)
        features["has(%s)" % letter] = letter in name.lower()
        features["startswith(%s)" % letter] = letter == name[0].lower()
        features["endswith(%s)" % letter] = letter == name[-1].lower()
    return features


def names_demo(trainer, features=names_demo_features):
    import random

    from nltk.corpus import names

    # Construct a list of classified names, using the names corpus.
    namelist = [(name, "male") for name in names.words("male.txt")] + [
        (name, "female") for name in names.words("female.txt")
    ]

    # Randomly split the names into a test & train set.
    random.seed(123456)
    random.shuffle(namelist)
    train = namelist[:5000]
    test = namelist[5000:5500]

    # Train up a classifier.
    print("Training classifier...")
    classifier = trainer([(features(n), g) for (n, g) in train])

    # Run the classifier on the test data.
    print("Testing classifier...")
    acc = accuracy(classifier, [(features(n), g) for (n, g) in test])
    print("Accuracy: %6.4f" % acc)

    # For classifiers that can find probabilities, show the log
    # likelihood and some sample probability distributions.
    try:
        test_featuresets = [features(n) for (n, g) in test]
        pdists = classifier.prob_classify_many(test_featuresets)
        ll = [pdist.logprob(gold) for ((name, gold), pdist) in zip(test, pdists)]
        print("Avg. log likelihood: %6.4f" % (sum(ll) / len(test)))
        print()
        print("Unseen Names      P(Male)  P(Female)\n" + "-" * 40)
        for (name, gender), pdist in list(zip(test, pdists))[:5]:
            if gender == "male":
                fmt = "  %-15s *%6.4f   %6.4f"
            else:
                fmt = "  %-15s  %6.4f  *%6.4f"
            print(fmt % (name, pdist.prob("male"), pdist.prob("female")))
    except NotImplementedError:
        pass

    # Return the classifier
    return classifier


def partial_names_demo(trainer, features=names_demo_features):
    import random

    from nltk.corpus import names

    male_names = names.words("male.txt")
    female_names = names.words("female.txt")

    random.seed(654321)
    random.shuffle(male_names)
    random.shuffle(female_names)

    # Create a list of male names to be used as positive-labeled examples for training
    positive = map(features, male_names[:2000])

    # Create a list of male and female names to be used as unlabeled examples
    unlabeled = map(features, male_names[2000:2500] + female_names[:500])

    # Create a test set with correctly-labeled male and female names
    test = [(name, True) for name in male_names[2500:2750]] + [
        (name, False) for name in female_names[500:750]
    ]

    random.shuffle(test)

    # Train up a classifier.
    print("Training classifier...")
    classifier = trainer(positive, unlabeled)

    # Run the classifier on the test data.
    print("Testing classifier...")
    acc = accuracy(classifier, [(features(n), m) for (n, m) in test])
    print("Accuracy: %6.4f" % acc)

    # For classifiers that can find probabilities, show the log
    # likelihood and some sample probability distributions.
    try:
        test_featuresets = [features(n) for (n, m) in test]
        pdists = classifier.prob_classify_many(test_featuresets)
        ll = [pdist.logprob(gold) for ((name, gold), pdist) in zip(test, pdists)]
        print("Avg. log likelihood: %6.4f" % (sum(ll) / len(test)))
        print()
        print("Unseen Names      P(Male)  P(Female)\n" + "-" * 40)
        for (name, is_male), pdist in zip(test, pdists)[:5]:
            if is_male == True:
                fmt = "  %-15s *%6.4f   %6.4f"
            else:
                fmt = "  %-15s  %6.4f  *%6.4f"
            print(fmt % (name, pdist.prob(True), pdist.prob(False)))
    except NotImplementedError:
        pass

    # Return the classifier
    return classifier


_inst_cache = {}


def wsd_demo(trainer, word, features, n=1000):
    import random

    from nltk.corpus import senseval

    # Get the instances.
    print("Reading data...")
    global _inst_cache
    if word not in _inst_cache:
        _inst_cache[word] = [(i, i.senses[0]) for i in senseval.instances(word)]
    instances = _inst_cache[word][:]
    if n > len(instances):
        n = len(instances)
    senses = list({l for (i, l) in instances})
    print("  Senses: " + " ".join(senses))

    # Randomly split the names into a test & train set.
    print("Splitting into test & train...")
    random.seed(123456)
    random.shuffle(instances)
    train = instances[: int(0.8 * n)]
    test = instances[int(0.8 * n) : n]

    # Train up a classifier.
    print("Training classifier...")
    classifier = trainer([(features(i), l) for (i, l) in train])

    # Run the classifier on the test data.
    print("Testing classifier...")
    acc = accuracy(classifier, [(features(i), l) for (i, l) in test])
    print("Accuracy: %6.4f" % acc)

    # For classifiers that can find probabilities, show the log
    # likelihood and some sample probability distributions.
    try:
        test_featuresets = [features(i) for (i, n) in test]
        pdists = classifier.prob_classify_many(test_featuresets)
        ll = [pdist.logprob(gold) for ((name, gold), pdist) in zip(test, pdists)]
        print("Avg. log likelihood: %6.4f" % (sum(ll) / len(test)))
    except NotImplementedError:
        pass

    # Return the classifier
    return classifier


def check_megam_config():
    """
    Checks whether the MEGAM binary is configured.
    """
    try:
        _megam_bin
    except NameError as e:
        err_msg = str(
            "Please configure your megam binary first, e.g.\n"
            ">>> nltk.config_megam('/usr/bin/local/megam')"
        )
        raise NameError(err_msg) from e

# === NexusCore/openenv\Lib\site-packages\numpy\_array_api_info.py ===
"""
Array API Inspection namespace

This is the namespace for inspection functions as defined by the array API
standard. See
https://data-apis.org/array-api/latest/API_specification/inspection.html for
more details.

"""
from numpy._core import (
    bool,
    complex64,
    complex128,
    dtype,
    float32,
    float64,
    int8,
    int16,
    int32,
    int64,
    intp,
    uint8,
    uint16,
    uint32,
    uint64,
)


class __array_namespace_info__:
    """
    Get the array API inspection namespace for NumPy.

    The array API inspection namespace defines the following functions:

    - capabilities()
    - default_device()
    - default_dtypes()
    - dtypes()
    - devices()

    See
    https://data-apis.org/array-api/latest/API_specification/inspection.html
    for more details.

    Returns
    -------
    info : ModuleType
        The array API inspection namespace for NumPy.

    Examples
    --------
    >>> info = np.__array_namespace_info__()
    >>> info.default_dtypes()
    {'real floating': numpy.float64,
     'complex floating': numpy.complex128,
     'integral': numpy.int64,
     'indexing': numpy.int64}

    """

    __module__ = 'numpy'

    def capabilities(self):
        """
        Return a dictionary of array API library capabilities.

        The resulting dictionary has the following keys:

        - **"boolean indexing"**: boolean indicating whether an array library
          supports boolean indexing. Always ``True`` for NumPy.

        - **"data-dependent shapes"**: boolean indicating whether an array
          library supports data-dependent output shapes. Always ``True`` for
          NumPy.

        See
        https://data-apis.org/array-api/latest/API_specification/generated/array_api.info.capabilities.html
        for more details.

        See Also
        --------
        __array_namespace_info__.default_device,
        __array_namespace_info__.default_dtypes,
        __array_namespace_info__.dtypes,
        __array_namespace_info__.devices

        Returns
        -------
        capabilities : dict
            A dictionary of array API library capabilities.

        Examples
        --------
        >>> info = np.__array_namespace_info__()
        >>> info.capabilities()
        {'boolean indexing': True,
         'data-dependent shapes': True,
         'max dimensions': 64}

        """
        return {
            "boolean indexing": True,
            "data-dependent shapes": True,
            "max dimensions": 64,
        }

    def default_device(self):
        """
        The default device used for new NumPy arrays.

        For NumPy, this always returns ``'cpu'``.

        See Also
        --------
        __array_namespace_info__.capabilities,
        __array_namespace_info__.default_dtypes,
        __array_namespace_info__.dtypes,
        __array_namespace_info__.devices

        Returns
        -------
        device : str
            The default device used for new NumPy arrays.

        Examples
        --------
        >>> info = np.__array_namespace_info__()
        >>> info.default_device()
        'cpu'

        """
        return "cpu"

    def default_dtypes(self, *, device=None):
        """
        The default data types used for new NumPy arrays.

        For NumPy, this always returns the following dictionary:

        - **"real floating"**: ``numpy.float64``
        - **"complex floating"**: ``numpy.complex128``
        - **"integral"**: ``numpy.intp``
        - **"indexing"**: ``numpy.intp``

        Parameters
        ----------
        device : str, optional
            The device to get the default data types for. For NumPy, only
            ``'cpu'`` is allowed.

        Returns
        -------
        dtypes : dict
            A dictionary describing the default data types used for new NumPy
            arrays.

        See Also
        --------
        __array_namespace_info__.capabilities,
        __array_namespace_info__.default_device,
        __array_namespace_info__.dtypes,
        __array_namespace_info__.devices

        Examples
        --------
        >>> info = np.__array_namespace_info__()
        >>> info.default_dtypes()
        {'real floating': numpy.float64,
         'complex floating': numpy.complex128,
         'integral': numpy.int64,
         'indexing': numpy.int64}

        """
        if device not in ["cpu", None]:
            raise ValueError(
                'Device not understood. Only "cpu" is allowed, but received:'
                f' {device}'
            )
        return {
            "real floating": dtype(float64),
            "complex floating": dtype(complex128),
            "integral": dtype(intp),
            "indexing": dtype(intp),
        }

    def dtypes(self, *, device=None, kind=None):
        """
        The array API data types supported by NumPy.

        Note that this function only returns data types that are defined by
        the array API.

        Parameters
        ----------
        device : str, optional
            The device to get the data types for. For NumPy, only ``'cpu'`` is
            allowed.
        kind : str or tuple of str, optional
            The kind of data types to return. If ``None``, all data types are
            returned. If a string, only data types of that kind are returned.
            If a tuple, a dictionary containing the union of the given kinds
            is returned. The following kinds are supported:

            - ``'bool'``: boolean data types (i.e., ``bool``).
            - ``'signed integer'``: signed integer data types (i.e., ``int8``,
              ``int16``, ``int32``, ``int64``).
            - ``'unsigned integer'``: unsigned integer data types (i.e.,
              ``uint8``, ``uint16``, ``uint32``, ``uint64``).
            - ``'integral'``: integer data types. Shorthand for ``('signed
              integer', 'unsigned integer')``.
            - ``'real floating'``: real-valued floating-point data types
              (i.e., ``float32``, ``float64``).
            - ``'complex floating'``: complex floating-point data types (i.e.,
              ``complex64``, ``complex128``).
            - ``'numeric'``: numeric data types. Shorthand for ``('integral',
              'real floating', 'complex floating')``.

        Returns
        -------
        dtypes : dict
            A dictionary mapping the names of data types to the corresponding
            NumPy data types.

        See Also
        --------
        __array_namespace_info__.capabilities,
        __array_namespace_info__.default_device,
        __array_namespace_info__.default_dtypes,
        __array_namespace_info__.devices

        Examples
        --------
        >>> info = np.__array_namespace_info__()
        >>> info.dtypes(kind='signed integer')
        {'int8': numpy.int8,
         'int16': numpy.int16,
         'int32': numpy.int32,
         'int64': numpy.int64}

        """
        if device not in ["cpu", None]:
            raise ValueError(
                'Device not understood. Only "cpu" is allowed, but received:'
                f' {device}'
            )
        if kind is None:
            return {
                "bool": dtype(bool),
                "int8": dtype(int8),
                "int16": dtype(int16),
                "int32": dtype(int32),
                "int64": dtype(int64),
                "uint8": dtype(uint8),
                "uint16": dtype(uint16),
                "uint32": dtype(uint32),
                "uint64": dtype(uint64),
                "float32": dtype(float32),
                "float64": dtype(float64),
                "complex64": dtype(complex64),
                "complex128": dtype(complex128),
            }
        if kind == "bool":
            return {"bool": bool}
        if kind == "signed integer":
            return {
                "int8": dtype(int8),
                "int16": dtype(int16),
                "int32": dtype(int32),
                "int64": dtype(int64),
            }
        if kind == "unsigned integer":
            return {
                "uint8": dtype(uint8),
                "uint16": dtype(uint16),
                "uint32": dtype(uint32),
                "uint64": dtype(uint64),
            }
        if kind == "integral":
            return {
                "int8": dtype(int8),
                "int16": dtype(int16),
                "int32": dtype(int32),
                "int64": dtype(int64),
                "uint8": dtype(uint8),
                "uint16": dtype(uint16),
                "uint32": dtype(uint32),
                "uint64": dtype(uint64),
            }
        if kind == "real floating":
            return {
                "float32": dtype(float32),
                "float64": dtype(float64),
            }
        if kind == "complex floating":
            return {
                "complex64": dtype(complex64),
                "complex128": dtype(complex128),
            }
        if kind == "numeric":
            return {
                "int8": dtype(int8),
                "int16": dtype(int16),
                "int32": dtype(int32),
                "int64": dtype(int64),
                "uint8": dtype(uint8),
                "uint16": dtype(uint16),
                "uint32": dtype(uint32),
                "uint64": dtype(uint64),
                "float32": dtype(float32),
                "float64": dtype(float64),
                "complex64": dtype(complex64),
                "complex128": dtype(complex128),
            }
        if isinstance(kind, tuple):
            res = {}
            for k in kind:
                res.update(self.dtypes(kind=k))
            return res
        raise ValueError(f"unsupported kind: {kind!r}")

    def devices(self):
        """
        The devices supported by NumPy.

        For NumPy, this always returns ``['cpu']``.

        Returns
        -------
        devices : list of str
            The devices supported by NumPy.

        See Also
        --------
        __array_namespace_info__.capabilities,
        __array_namespace_info__.default_device,
        __array_namespace_info__.default_dtypes,
        __array_namespace_info__.dtypes

        Examples
        --------
        >>> info = np.__array_namespace_info__()
        >>> info.devices()
        ['cpu']

        """
        return ["cpu"]

# === NexusCore/openenv\Lib\site-packages\fontTools\ufoLib\filenames.py ===
"""
Convert user-provided internal UFO names to spec-compliant filenames.

This module implements the algorithm for converting between a "user name" -
something that a user can choose arbitrarily inside a font editor - and a file
name suitable for use in a wide range of operating systems and filesystems.

The `UFO 3 specification <http://unifiedfontobject.org/versions/ufo3/conventions/>`_
provides an example of an algorithm for such conversion, which avoids illegal
characters, reserved file names, ambiguity between upper- and lower-case
characters, and clashes with existing files.

This code was originally copied from
`ufoLib <https://github.com/unified-font-object/ufoLib/blob/8747da7/Lib/ufoLib/filenames.py>`_
by Tal Leming and is copyright (c) 2005-2016, The RoboFab Developers:

-	Erik van Blokland
-	Tal Leming
-	Just van Rossum
"""

# Restrictions are taken mostly from
# https://docs.microsoft.com/en-gb/windows/win32/fileio/naming-a-file#naming-conventions.
#
# 1. Integer value zero, sometimes referred to as the ASCII NUL character.
# 2. Characters whose integer representations are in the range 1 to 31,
#    inclusive.
# 3. Various characters that (mostly) Windows and POSIX-y filesystems don't
#    allow, plus "(" and ")", as per the specification.
illegalCharacters = {
    "\x00",
    "\x01",
    "\x02",
    "\x03",
    "\x04",
    "\x05",
    "\x06",
    "\x07",
    "\x08",
    "\t",
    "\n",
    "\x0b",
    "\x0c",
    "\r",
    "\x0e",
    "\x0f",
    "\x10",
    "\x11",
    "\x12",
    "\x13",
    "\x14",
    "\x15",
    "\x16",
    "\x17",
    "\x18",
    "\x19",
    "\x1a",
    "\x1b",
    "\x1c",
    "\x1d",
    "\x1e",
    "\x1f",
    '"',
    "*",
    "+",
    "/",
    ":",
    "<",
    ">",
    "?",
    "[",
    "\\",
    "]",
    "(",
    ")",
    "|",
    "\x7f",
}
reservedFileNames = {
    "aux",
    "clock$",
    "com1",
    "com2",
    "com3",
    "com4",
    "com5",
    "com6",
    "com7",
    "com8",
    "com9",
    "con",
    "lpt1",
    "lpt2",
    "lpt3",
    "lpt4",
    "lpt5",
    "lpt6",
    "lpt7",
    "lpt8",
    "lpt9",
    "nul",
    "prn",
}
maxFileNameLength = 255


class NameTranslationError(Exception):
    pass


def userNameToFileName(userName: str, existing=(), prefix="", suffix=""):
    """Converts from a user name to a file name.

    Takes care to avoid illegal characters, reserved file names, ambiguity between
    upper- and lower-case characters, and clashes with existing files.

    Args:
            userName (str): The input file name.
            existing: A case-insensitive list of all existing file names.
            prefix: Prefix to be prepended to the file name.
            suffix: Suffix to be appended to the file name.

    Returns:
            A suitable filename.

    Raises:
            NameTranslationError: If no suitable name could be generated.

    Examples::

            >>> userNameToFileName("a") == "a"
            True
            >>> userNameToFileName("A") == "A_"
            True
            >>> userNameToFileName("AE") == "A_E_"
            True
            >>> userNameToFileName("Ae") == "A_e"
            True
            >>> userNameToFileName("ae") == "ae"
            True
            >>> userNameToFileName("aE") == "aE_"
            True
            >>> userNameToFileName("a.alt") == "a.alt"
            True
            >>> userNameToFileName("A.alt") == "A_.alt"
            True
            >>> userNameToFileName("A.Alt") == "A_.A_lt"
            True
            >>> userNameToFileName("A.aLt") == "A_.aL_t"
            True
            >>> userNameToFileName(u"A.alT") == "A_.alT_"
            True
            >>> userNameToFileName("T_H") == "T__H_"
            True
            >>> userNameToFileName("T_h") == "T__h"
            True
            >>> userNameToFileName("t_h") == "t_h"
            True
            >>> userNameToFileName("F_F_I") == "F__F__I_"
            True
            >>> userNameToFileName("f_f_i") == "f_f_i"
            True
            >>> userNameToFileName("Aacute_V.swash") == "A_acute_V_.swash"
            True
            >>> userNameToFileName(".notdef") == "_notdef"
            True
            >>> userNameToFileName("con") == "_con"
            True
            >>> userNameToFileName("CON") == "C_O_N_"
            True
            >>> userNameToFileName("con.alt") == "_con.alt"
            True
            >>> userNameToFileName("alt.con") == "alt._con"
            True
    """
    # the incoming name must be a string
    if not isinstance(userName, str):
        raise ValueError("The value for userName must be a string.")
    # establish the prefix and suffix lengths
    prefixLength = len(prefix)
    suffixLength = len(suffix)
    # replace an initial period with an _
    # if no prefix is to be added
    if not prefix and userName[0] == ".":
        userName = "_" + userName[1:]
    # filter the user name
    filteredUserName = []
    for character in userName:
        # replace illegal characters with _
        if character in illegalCharacters:
            character = "_"
        # add _ to all non-lower characters
        elif character != character.lower():
            character += "_"
        filteredUserName.append(character)
    userName = "".join(filteredUserName)
    # clip to 255
    sliceLength = maxFileNameLength - prefixLength - suffixLength
    userName = userName[:sliceLength]
    # test for illegal files names
    parts = []
    for part in userName.split("."):
        if part.lower() in reservedFileNames:
            part = "_" + part
        parts.append(part)
    userName = ".".join(parts)
    # test for clash
    fullName = prefix + userName + suffix
    if fullName.lower() in existing:
        fullName = handleClash1(userName, existing, prefix, suffix)
    # finished
    return fullName


def handleClash1(userName, existing=[], prefix="", suffix=""):
    """A helper function that resolves collisions with existing names when choosing a filename.

    This function attempts to append an unused integer counter to the filename.

        Args:
                userName (str): The input file name.
                existing: A case-insensitive list of all existing file names.
                prefix: Prefix to be prepended to the file name.
                suffix: Suffix to be appended to the file name.

        Returns:
                A suitable filename.

        >>> prefix = ("0" * 5) + "."
        >>> suffix = "." + ("0" * 10)
        >>> existing = ["a" * 5]

        >>> e = list(existing)
        >>> handleClash1(userName="A" * 5, existing=e,
        ...		prefix=prefix, suffix=suffix) == (
        ... 	'00000.AAAAA000000000000001.0000000000')
        True

        >>> e = list(existing)
        >>> e.append(prefix + "aaaaa" + "1".zfill(15) + suffix)
        >>> handleClash1(userName="A" * 5, existing=e,
        ...		prefix=prefix, suffix=suffix) == (
        ... 	'00000.AAAAA000000000000002.0000000000')
        True

        >>> e = list(existing)
        >>> e.append(prefix + "AAAAA" + "2".zfill(15) + suffix)
        >>> handleClash1(userName="A" * 5, existing=e,
        ...		prefix=prefix, suffix=suffix) == (
        ... 	'00000.AAAAA000000000000001.0000000000')
        True
    """
    # if the prefix length + user name length + suffix length + 15 is at
    # or past the maximum length, silce 15 characters off of the user name
    prefixLength = len(prefix)
    suffixLength = len(suffix)
    if prefixLength + len(userName) + suffixLength + 15 > maxFileNameLength:
        l = prefixLength + len(userName) + suffixLength + 15
        sliceLength = maxFileNameLength - l
        userName = userName[:sliceLength]
    finalName = None
    # try to add numbers to create a unique name
    counter = 1
    while finalName is None:
        name = userName + str(counter).zfill(15)
        fullName = prefix + name + suffix
        if fullName.lower() not in existing:
            finalName = fullName
            break
        else:
            counter += 1
        if counter >= 999999999999999:
            break
    # if there is a clash, go to the next fallback
    if finalName is None:
        finalName = handleClash2(existing, prefix, suffix)
    # finished
    return finalName


def handleClash2(existing=[], prefix="", suffix=""):
    """A helper function that resolves collisions with existing names when choosing a filename.

    This function is a fallback to :func:`handleClash1`. It attempts to append an unused integer counter to the filename.

        Args:
                userName (str): The input file name.
                existing: A case-insensitive list of all existing file names.
                prefix: Prefix to be prepended to the file name.
                suffix: Suffix to be appended to the file name.

        Returns:
                A suitable filename.

        Raises:
                NameTranslationError: If no suitable name could be generated.

        Examples::

          >>> prefix = ("0" * 5) + "."
          >>> suffix = "." + ("0" * 10)
          >>> existing = [prefix + str(i) + suffix for i in range(100)]

          >>> e = list(existing)
          >>> handleClash2(existing=e, prefix=prefix, suffix=suffix) == (
          ... 	'00000.100.0000000000')
          True

          >>> e = list(existing)
          >>> e.remove(prefix + "1" + suffix)
          >>> handleClash2(existing=e, prefix=prefix, suffix=suffix) == (
          ... 	'00000.1.0000000000')
          True

          >>> e = list(existing)
          >>> e.remove(prefix + "2" + suffix)
          >>> handleClash2(existing=e, prefix=prefix, suffix=suffix) == (
          ... 	'00000.2.0000000000')
          True
    """
    # calculate the longest possible string
    maxLength = maxFileNameLength - len(prefix) - len(suffix)
    maxValue = int("9" * maxLength)
    # try to find a number
    finalName = None
    counter = 1
    while finalName is None:
        fullName = prefix + str(counter) + suffix
        if fullName.lower() not in existing:
            finalName = fullName
            break
        else:
            counter += 1
        if counter >= maxValue:
            break
    # raise an error if nothing has been found
    if finalName is None:
        raise NameTranslationError("No unique name could be found.")
    # finished
    return finalName


if __name__ == "__main__":
    import doctest

    doctest.testmod()

# === NexusCore/openenv\Lib\site-packages\google\api_core\path_template.py ===
# Copyright 2017 Google LLC
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

"""Expand and validate URL path templates.

This module provides the :func:`expand` and :func:`validate` functions for
interacting with Google-style URL `path templates`_ which are commonly used
in Google APIs for `resource names`_.

.. _path templates: https://github.com/googleapis/googleapis/blob
    /57e2d376ac7ef48681554204a3ba78a414f2c533/google/api/http.proto#L212
.. _resource names: https://cloud.google.com/apis/design/resource_names
"""

from __future__ import unicode_literals

from collections import deque
import copy
import functools
import re

# Regular expression for extracting variable parts from a path template.
# The variables can be expressed as:
#
# - "*": a single-segment positional variable, for example: "books/*"
# - "**": a multi-segment positional variable, for example: "shelf/**/book/*"
# - "{name}": a single-segment wildcard named variable, for example
#   "books/{name}"
# - "{name=*}: same as above.
# - "{name=**}": a multi-segment wildcard named variable, for example
#   "shelf/{name=**}"
# - "{name=/path/*/**}": a multi-segment named variable with a sub-template.
_VARIABLE_RE = re.compile(
    r"""
    (  # Capture the entire variable expression
        (?P<positional>\*\*?)  # Match & capture * and ** positional variables.
        |
        # Match & capture named variables {name}
        {
            (?P<name>[^/]+?)
            # Optionally match and capture the named variable's template.
            (?:=(?P<template>.+?))?
        }
    )
    """,
    re.VERBOSE,
)

# Segment expressions used for validating paths against a template.
_SINGLE_SEGMENT_PATTERN = r"([^/]+)"
_MULTI_SEGMENT_PATTERN = r"(.+)"


def _expand_variable_match(positional_vars, named_vars, match):
    """Expand a matched variable with its value.

    Args:
        positional_vars (list): A list of positional variables. This list will
            be modified.
        named_vars (dict): A dictionary of named variables.
        match (re.Match): A regular expression match.

    Returns:
        str: The expanded variable to replace the match.

    Raises:
        ValueError: If a positional or named variable is required by the
            template but not specified or if an unexpected template expression
            is encountered.
    """
    positional = match.group("positional")
    name = match.group("name")
    if name is not None:
        try:
            return str(named_vars[name])
        except KeyError:
            raise ValueError(
                "Named variable '{}' not specified and needed by template "
                "`{}` at position {}".format(name, match.string, match.start())
            )
    elif positional is not None:
        try:
            return str(positional_vars.pop(0))
        except IndexError:
            raise ValueError(
                "Positional variable not specified and needed by template "
                "`{}` at position {}".format(match.string, match.start())
            )
    else:
        raise ValueError("Unknown template expression {}".format(match.group(0)))


def expand(tmpl, *args, **kwargs):
    """Expand a path template with the given variables.

    .. code-block:: python

        >>> expand('users/*/messages/*', 'me', '123')
        users/me/messages/123
        >>> expand('/v1/{name=shelves/*/books/*}', name='shelves/1/books/3')
        /v1/shelves/1/books/3

    Args:
        tmpl (str): The path template.
        args: The positional variables for the path.
        kwargs: The named variables for the path.

    Returns:
        str: The expanded path

    Raises:
        ValueError: If a positional or named variable is required by the
            template but not specified or if an unexpected template expression
            is encountered.
    """
    replacer = functools.partial(_expand_variable_match, list(args), kwargs)
    return _VARIABLE_RE.sub(replacer, tmpl)


def _replace_variable_with_pattern(match):
    """Replace a variable match with a pattern that can be used to validate it.

    Args:
        match (re.Match): A regular expression match

    Returns:
        str: A regular expression pattern that can be used to validate the
            variable in an expanded path.

    Raises:
        ValueError: If an unexpected template expression is encountered.
    """
    positional = match.group("positional")
    name = match.group("name")
    template = match.group("template")
    if name is not None:
        if not template:
            return _SINGLE_SEGMENT_PATTERN.format(name)
        elif template == "**":
            return _MULTI_SEGMENT_PATTERN.format(name)
        else:
            return _generate_pattern_for_template(template)
    elif positional == "*":
        return _SINGLE_SEGMENT_PATTERN
    elif positional == "**":
        return _MULTI_SEGMENT_PATTERN
    else:
        raise ValueError("Unknown template expression {}".format(match.group(0)))


def _generate_pattern_for_template(tmpl):
    """Generate a pattern that can validate a path template.

    Args:
        tmpl (str): The path template

    Returns:
        str: A regular expression pattern that can be used to validate an
            expanded path template.
    """
    return _VARIABLE_RE.sub(_replace_variable_with_pattern, tmpl)


def get_field(request, field):
    """Get the value of a field from a given dictionary.

    Args:
        request (dict | Message): A dictionary or a Message object.
        field (str): The key to the request in dot notation.

    Returns:
        The value of the field.
    """
    parts = field.split(".")
    value = request

    for part in parts:
        if not isinstance(value, dict):
            value = getattr(value, part, None)
        else:
            value = value.get(part)
    if isinstance(value, dict):
        return
    return value


def delete_field(request, field):
    """Delete the value of a field from a given dictionary.

    Args:
        request (dict | Message): A dictionary object or a Message.
        field (str): The key to the request in dot notation.
    """
    parts = deque(field.split("."))
    while len(parts) > 1:
        part = parts.popleft()
        if not isinstance(request, dict):
            if hasattr(request, part):
                request = getattr(request, part, None)
            else:
                return
        else:
            request = request.get(part)
    part = parts.popleft()
    if not isinstance(request, dict):
        if hasattr(request, part):
            request.ClearField(part)
        else:
            return
    else:
        request.pop(part, None)


def validate(tmpl, path):
    """Validate a path against the path template.

    .. code-block:: python

        >>> validate('users/*/messages/*', 'users/me/messages/123')
        True
        >>> validate('users/*/messages/*', 'users/me/drafts/123')
        False
        >>> validate('/v1/{name=shelves/*/books/*}', /v1/shelves/1/books/3)
        True
        >>> validate('/v1/{name=shelves/*/books/*}', /v1/shelves/1/tapes/3)
        False

    Args:
        tmpl (str): The path template.
        path (str): The expanded path.

    Returns:
        bool: True if the path matches.
    """
    pattern = _generate_pattern_for_template(tmpl) + "$"
    return True if re.match(pattern, path) is not None else False


def transcode(http_options, message=None, **request_kwargs):
    """Transcodes a grpc request pattern into a proper HTTP request following the rules outlined here,
    https://github.com/googleapis/googleapis/blob/master/google/api/http.proto#L44-L312

     Args:
         http_options (list(dict)): A list of dicts which consist of these keys,
             'method'    (str): The http method
             'uri'       (str): The path template
             'body'      (str): The body field name (optional)
             (This is a simplified representation of the proto option `google.api.http`)

         message (Message) : A request object (optional)
         request_kwargs (dict) : A dict representing the request object

     Returns:
         dict: The transcoded request with these keys,
             'method'        (str)   : The http method
             'uri'           (str)   : The expanded uri
             'body'          (dict | Message)  : A dict or a Message representing the body (optional)
             'query_params'  (dict | Message)  : A dict or Message mapping query parameter variables and values

     Raises:
         ValueError: If the request does not match the given template.
    """
    transcoded_value = message or request_kwargs
    bindings = []
    for http_option in http_options:
        request = {}

        # Assign path
        uri_template = http_option["uri"]
        fields = [
            (m.group("name"), m.group("template"))
            for m in _VARIABLE_RE.finditer(uri_template)
        ]
        bindings.append((uri_template, fields))

        path_args = {field: get_field(transcoded_value, field) for field, _ in fields}
        request["uri"] = expand(uri_template, **path_args)

        if not validate(uri_template, request["uri"]) or not all(path_args.values()):
            continue

        # Remove fields used in uri path from request
        leftovers = copy.deepcopy(transcoded_value)
        for path_field, _ in fields:
            delete_field(leftovers, path_field)

        # Assign body and query params
        body = http_option.get("body")

        if body:
            if body == "*":
                request["body"] = leftovers
                if message:
                    request["query_params"] = message.__class__()
                else:
                    request["query_params"] = {}
            else:
                try:
                    if message:
                        request["body"] = getattr(leftovers, body)
                        delete_field(leftovers, body)
                    else:
                        request["body"] = leftovers.pop(body)
                except (KeyError, AttributeError):
                    continue
                request["query_params"] = leftovers
        else:
            request["query_params"] = leftovers
        request["method"] = http_option["method"]
        return request

    bindings_description = [
        '\n\tURI: "{}"'
        "\n\tRequired request fields:\n\t\t{}".format(
            uri,
            "\n\t\t".join(
                [
                    'field: "{}", pattern: "{}"'.format(n, p if p else "*")
                    for n, p in fields
                ]
            ),
        )
        for uri, fields in bindings
    ]

    raise ValueError(
        "Invalid request."
        "\nSome of the fields of the request message are either not initialized or "
        "initialized with an invalid value."
        "\nPlease make sure your request matches at least one accepted HTTP binding."
        "\nTo match a binding the request message must have all the required fields "
        "initialized with values matching their patterns as listed below:{}".format(
            "\n".join(bindings_description)
        )
    )

# === NexusCore/openenv\Lib\site-packages\IPython\core\displayhook.py ===
# -*- coding: utf-8 -*-
"""Displayhook for IPython.

This defines a callable class that IPython uses for `sys.displayhook`.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import builtins as builtin_mod
import sys
import io as _io
import tokenize

from traitlets.config.configurable import Configurable
from traitlets import Instance, Float
from warnings import warn

from .history import HistoryOutput

# TODO: Move the various attributes (cache_size, [others now moved]). Some
# of these are also attributes of InteractiveShell. They should be on ONE object
# only and the other objects should ask that one object for their values.

class DisplayHook(Configurable):
    """The custom IPython displayhook to replace sys.displayhook.

    This class does many things, but the basic idea is that it is a callable
    that gets called anytime user code returns a value.
    """

    shell = Instance('IPython.core.interactiveshell.InteractiveShellABC',
                     allow_none=True)
    exec_result = Instance('IPython.core.interactiveshell.ExecutionResult',
                           allow_none=True)
    cull_fraction = Float(0.2)

    def __init__(self, shell=None, cache_size=1000, **kwargs):
        super(DisplayHook, self).__init__(shell=shell, **kwargs)
        self._is_active = False
        cache_size_min = 3
        if cache_size <= 0:
            self.do_full_cache = 0
            cache_size = 0
        elif cache_size < cache_size_min:
            self.do_full_cache = 0
            cache_size = 0
            warn('caching was disabled (min value for cache size is %s).' %
                 cache_size_min,stacklevel=3)
        else:
            self.do_full_cache = 1

        self.cache_size = cache_size

        # we need a reference to the user-level namespace
        self.shell = shell

        self._,self.__,self.___ = '','',''

        # these are deliberately global:
        to_user_ns = {'_':self._,'__':self.__,'___':self.___}
        self.shell.user_ns.update(to_user_ns)

    @property
    def prompt_count(self):
        return self.shell.execution_count

    #-------------------------------------------------------------------------
    # Methods used in __call__. Override these methods to modify the behavior
    # of the displayhook.
    #-------------------------------------------------------------------------

    def check_for_underscore(self):
        """Check if the user has set the '_' variable by hand."""
        # If something injected a '_' variable in __builtin__, delete
        # ipython's automatic one so we don't clobber that.  gettext() in
        # particular uses _, so we need to stay away from it.
        if '_' in builtin_mod.__dict__:
            try:
                user_value = self.shell.user_ns['_']
                if user_value is not self._:
                    return
                del self.shell.user_ns['_']
            except KeyError:
                pass

    def quiet(self):
        """Should we silence the display hook because of ';'?"""
        # do not print output if input ends in ';'

        try:
            cell = self.shell.history_manager.input_hist_parsed[-1]
        except IndexError:
            # some uses of ipshellembed may fail here
            return False

        return self.semicolon_at_end_of_expression(cell)

    @staticmethod
    def semicolon_at_end_of_expression(expression):
        """Parse Python expression and detects whether last token is ';'"""

        sio = _io.StringIO(expression)
        tokens = list(tokenize.generate_tokens(sio.readline))

        for token in reversed(tokens):
            if token[0] in (tokenize.ENDMARKER, tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT):
                continue
            if (token[0] == tokenize.OP) and (token[1] == ';'):
                return True
            else:
                return False

    def start_displayhook(self):
        """Start the displayhook, initializing resources."""
        self._is_active = True

    @property
    def is_active(self):
        return self._is_active

    def write_output_prompt(self):
        """Write the output prompt.

        The default implementation simply writes the prompt to
        ``sys.stdout``.
        """
        # Use write, not print which adds an extra space.
        sys.stdout.write(self.shell.separate_out)
        outprompt = 'Out[{}]: '.format(self.shell.execution_count)
        if self.do_full_cache:
            sys.stdout.write(outprompt)

    def compute_format_data(self, result):
        """Compute format data of the object to be displayed.

        The format data is a generalization of the :func:`repr` of an object.
        In the default implementation the format data is a :class:`dict` of
        key value pair where the keys are valid MIME types and the values
        are JSON'able data structure containing the raw data for that MIME
        type. It is up to frontends to determine pick a MIME to to use and
        display that data in an appropriate manner.

        This method only computes the format data for the object and should
        NOT actually print or write that to a stream.

        Parameters
        ----------
        result : object
            The Python object passed to the display hook, whose format will be
            computed.

        Returns
        -------
        (format_dict, md_dict) : dict
            format_dict is a :class:`dict` whose keys are valid MIME types and values are
            JSON'able raw data for that MIME type. It is recommended that
            all return values of this should always include the "text/plain"
            MIME type representation of the object.
            md_dict is a :class:`dict` with the same MIME type keys
            of metadata associated with each output.

        """
        return self.shell.display_formatter.format(result)

    # This can be set to True by the write_output_prompt method in a subclass
    prompt_end_newline = False

    def write_format_data(self, format_dict, md_dict=None) -> None:
        """Write the format data dict to the frontend.

        This default version of this method simply writes the plain text
        representation of the object to ``sys.stdout``. Subclasses should
        override this method to send the entire `format_dict` to the
        frontends.

        Parameters
        ----------
        format_dict : dict
            The format dict for the object passed to `sys.displayhook`.
        md_dict : dict (optional)
            The metadata dict to be associated with the display data.
        """
        if 'text/plain' not in format_dict:
            # nothing to do
            return
        # We want to print because we want to always make sure we have a
        # newline, even if all the prompt separators are ''. This is the
        # standard IPython behavior.
        result_repr = format_dict['text/plain']
        if '\n' in result_repr:
            # So that multi-line strings line up with the left column of
            # the screen, instead of having the output prompt mess up
            # their first line.
            # We use the prompt template instead of the expanded prompt
            # because the expansion may add ANSI escapes that will interfere
            # with our ability to determine whether or not we should add
            # a newline.
            if not self.prompt_end_newline:
                # But avoid extraneous empty lines.
                result_repr = '\n' + result_repr

        try:
            print(result_repr)
        except UnicodeEncodeError:
            # If a character is not supported by the terminal encoding replace
            # it with its \u or \x representation
            print(result_repr.encode(sys.stdout.encoding,'backslashreplace').decode(sys.stdout.encoding))

    def update_user_ns(self, result):
        """Update user_ns with various things like _, __, _1, etc."""

        # Avoid recursive reference when displaying _oh/Out
        if self.cache_size and result is not self.shell.user_ns['_oh']:
            if len(self.shell.user_ns['_oh']) >= self.cache_size and self.do_full_cache:
                self.cull_cache()

            # Don't overwrite '_' and friends if '_' is in __builtin__
            # (otherwise we cause buggy behavior for things like gettext). and
            # do not overwrite _, __ or ___ if one of these has been assigned
            # by the user.
            update_unders = True
            for unders in ['_'*i for i in range(1,4)]:
                if unders not in self.shell.user_ns:
                    continue
                if getattr(self, unders) is not self.shell.user_ns.get(unders):
                    update_unders = False

            self.___ = self.__
            self.__ = self._
            self._ = result

            if ('_' not in builtin_mod.__dict__) and (update_unders):
                self.shell.push({'_':self._,
                                 '__':self.__,
                                '___':self.___}, interactive=False)

            # hackish access to top-level  namespace to create _1,_2... dynamically
            to_main = {}
            if self.do_full_cache:
                new_result = '_%s' % self.prompt_count
                to_main[new_result] = result
                self.shell.push(to_main, interactive=False)
                self.shell.user_ns['_oh'][self.prompt_count] = result

    def fill_exec_result(self, result):
        if self.exec_result is not None:
            self.exec_result.result = result

    def log_output(self, format_dict):
        """Log the output."""
        self.shell.history_manager.outputs[self.prompt_count].append(
            HistoryOutput(output_type="execute_result", bundle=format_dict)
        )
        if "text/plain" not in format_dict:
            # nothing to do
            return
        if self.shell.logger.log_output:
            self.shell.logger.log_write(format_dict['text/plain'], 'output')
        self.shell.history_manager.output_hist_reprs[self.prompt_count] = \
                                                    format_dict['text/plain']

    def finish_displayhook(self):
        """Finish up all displayhook activities."""
        sys.stdout.write(self.shell.separate_out2)
        sys.stdout.flush()
        self._is_active = False

    def __call__(self, result=None):
        """Printing with history cache management.

        This is invoked every time the interpreter needs to print, and is
        activated by setting the variable sys.displayhook to it.
        """
        self.check_for_underscore()
        if result is not None and not self.quiet():
            self.start_displayhook()
            self.write_output_prompt()
            format_dict, md_dict = self.compute_format_data(result)
            self.update_user_ns(result)
            self.fill_exec_result(result)
            if format_dict:
                self.write_format_data(format_dict, md_dict)
                self.log_output(format_dict)
            self.finish_displayhook()

    def cull_cache(self):
        """Output cache is full, cull the oldest entries"""
        oh = self.shell.user_ns.get('_oh', {})
        sz = len(oh)
        cull_count = max(int(sz * self.cull_fraction), 2)
        warn('Output cache limit (currently {sz} entries) hit.\n'
             'Flushing oldest {cull_count} entries.'.format(sz=sz, cull_count=cull_count))

        for i, n in enumerate(sorted(oh)):
            if i >= cull_count:
                break
            self.shell.user_ns.pop('_%i' % n, None)
            oh.pop(n, None)

    def flush(self):
        if not self.do_full_cache:
            raise ValueError("You shouldn't have reached the cache flush "
                             "if full caching is not enabled!")
        # delete auto-generated vars from global namespace

        for n in range(1,self.prompt_count + 1):
            key = '_'+repr(n)
            try:
                del self.shell.user_ns_hidden[key]
            except KeyError:
                pass
            try:
                del self.shell.user_ns[key]
            except KeyError:
                pass
        # In some embedded circumstances, the user_ns doesn't have the
        # '_oh' key set up.
        oh = self.shell.user_ns.get('_oh', None)
        if oh is not None:
            oh.clear()

        # Release our own references to objects:
        self._, self.__, self.___ = '', '', ''

        if '_' not in builtin_mod.__dict__:
            self.shell.user_ns.update({'_':self._,'__':self.__,'___':self.___})
        import gc
        # TODO: Is this really needed?
        # IronPython blocks here forever
        if sys.platform != "cli":
            gc.collect()


class CapturingDisplayHook:
    def __init__(self, shell, outputs=None):
        self.shell = shell
        if outputs is None:
            outputs = []
        self.outputs = outputs

    def __call__(self, result=None):
        if result is None:
            return
        format_dict, md_dict = self.shell.display_formatter.format(result)
        self.outputs.append({ 'data': format_dict, 'metadata': md_dict })

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\ipapp.py ===
# encoding: utf-8
"""
The :class:`~traitlets.config.application.Application` object for the command
line :command:`ipython` program.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.


import logging
import os
import sys
import warnings

from traitlets.config.loader import Config
from traitlets.config.application import boolean_flag, catch_config_error
from IPython.core import release
from IPython.core import usage
from IPython.core.completer import IPCompleter
from IPython.core.crashhandler import CrashHandler
from IPython.core.formatters import PlainTextFormatter
from IPython.core.history import HistoryManager
from IPython.core.application import (
    ProfileDir, BaseIPythonApplication, base_flags, base_aliases
)
from IPython.core.magic import MagicsManager
from IPython.core.magics import (
    ScriptMagics, LoggingMagics
)
from IPython.core.shellapp import (
    InteractiveShellApp, shell_flags, shell_aliases
)
from IPython.extensions.storemagic import StoreMagics
from .interactiveshell import TerminalInteractiveShell
from IPython.paths import get_ipython_dir
from traitlets import (
    Bool, List, default, observe, Type
)

#-----------------------------------------------------------------------------
# Globals, utilities and helpers
#-----------------------------------------------------------------------------

_examples = """
ipython --matplotlib       # enable matplotlib integration
ipython --matplotlib=qt    # enable matplotlib integration with qt4 backend

ipython --log-level=DEBUG  # set logging to DEBUG
ipython --profile=foo      # start with profile foo

ipython profile create foo # create profile foo w/ default config files
ipython help profile       # show the help for the profile subcmd

ipython locate             # print the path to the IPython directory
ipython locate profile foo # print the path to the directory for profile `foo`
"""

#-----------------------------------------------------------------------------
# Crash handler for this application
#-----------------------------------------------------------------------------

class IPAppCrashHandler(CrashHandler):
    """sys.excepthook for IPython itself, leaves a detailed report on disk."""

    def __init__(self, app):
        contact_name = release.author
        contact_email = release.author_email
        bug_tracker = 'https://github.com/ipython/ipython/issues'
        super(IPAppCrashHandler,self).__init__(
            app, contact_name, contact_email, bug_tracker
        )

    def make_report(self,traceback):
        """Return a string containing a crash report."""

        sec_sep = self.section_sep
        # Start with parent report
        report = [super(IPAppCrashHandler, self).make_report(traceback)]
        # Add interactive-specific info we may have
        rpt_add = report.append
        try:
            rpt_add(sec_sep+"History of session input:")
            for line in self.app.shell.user_ns['_ih']:
                rpt_add(line)
            rpt_add('\n*** Last line of input (may not be in above history):\n')
            rpt_add(self.app.shell._last_input_line+'\n')
        except:
            pass

        return ''.join(report)

#-----------------------------------------------------------------------------
# Aliases and Flags
#-----------------------------------------------------------------------------
flags = dict(base_flags)
flags.update(shell_flags)
frontend_flags = {}
addflag = lambda *args: frontend_flags.update(boolean_flag(*args))
addflag('autoedit-syntax', 'TerminalInteractiveShell.autoedit_syntax',
        'Turn on auto editing of files with syntax errors.',
        'Turn off auto editing of files with syntax errors.'
)
addflag('simple-prompt', 'TerminalInteractiveShell.simple_prompt',
        "Force simple minimal prompt using `raw_input`",
        "Use a rich interactive prompt with prompt_toolkit",
)

addflag('banner', 'TerminalIPythonApp.display_banner',
        "Display a banner upon starting IPython.",
        "Don't display a banner upon starting IPython."
)
addflag('confirm-exit', 'TerminalInteractiveShell.confirm_exit',
    """Set to confirm when you try to exit IPython with an EOF (Control-D
    in Unix, Control-Z/Enter in Windows). By typing 'exit' or 'quit',
    you can force a direct exit without any confirmation.""",
    "Don't prompt the user when exiting."
)
addflag(
    "tip",
    "TerminalInteractiveShell.enable_tip",
    """Shows a tip when IPython starts.""",
    "Don't show tip when IPython starts.",
)
addflag('term-title', 'TerminalInteractiveShell.term_title',
    "Enable auto setting the terminal title.",
    "Disable auto setting the terminal title."
)
classic_config = Config()
classic_config.InteractiveShell.cache_size = 0
classic_config.PlainTextFormatter.pprint = False
classic_config.TerminalInteractiveShell.prompts_class = (
    "IPython.terminal.prompts.ClassicPrompts"
)
classic_config.InteractiveShell.separate_in = ""
classic_config.InteractiveShell.separate_out = ""
classic_config.InteractiveShell.separate_out2 = ""
classic_config.InteractiveShell.colors = "nocolor"
classic_config.InteractiveShell.xmode = "Plain"

frontend_flags['classic']=(
    classic_config,
    "Gives IPython a similar feel to the classic Python prompt."
)
# # log doesn't make so much sense this way anymore
# paa('--log','-l',
#     action='store_true', dest='InteractiveShell.logstart',
#     help="Start logging to the default log file (./ipython_log.py).")
#
# # quick is harder to implement
frontend_flags['quick']=(
    {'TerminalIPythonApp' : {'quick' : True}},
    "Enable quick startup with no config files."
)

frontend_flags['i'] = (
    {'TerminalIPythonApp' : {'force_interact' : True}},
    """If running code from the command line, become interactive afterwards.
    It is often useful to follow this with `--` to treat remaining flags as
    script arguments.
    """
)
flags.update(frontend_flags)

aliases = dict(base_aliases)
aliases.update(shell_aliases)  # type: ignore[arg-type]

#-----------------------------------------------------------------------------
# Main classes and functions
#-----------------------------------------------------------------------------


class LocateIPythonApp(BaseIPythonApplication):
    description = """print the path to the IPython dir"""
    subcommands = dict(
        profile=('IPython.core.profileapp.ProfileLocate',
            "print the path to an IPython profile directory",
        ),
    )
    def start(self):
        if self.subapp is not None:
            return self.subapp.start()
        else:
            print(self.ipython_dir)


class TerminalIPythonApp(BaseIPythonApplication, InteractiveShellApp):
    name = "ipython"
    description = usage.cl_usage
    crash_handler_class = IPAppCrashHandler  # typing: ignore[assignment]
    examples = _examples

    flags = flags
    aliases = aliases
    classes = List()

    interactive_shell_class = Type(
        klass=object,   # use default_value otherwise which only allow subclasses.
        default_value=TerminalInteractiveShell,
        help="Class to use to instantiate the TerminalInteractiveShell object. Useful for custom Frontends"
    ).tag(config=True)

    @default('classes')
    def _classes_default(self):
        """This has to be in a method, for TerminalIPythonApp to be available."""
        return [
            InteractiveShellApp,  # ShellApp comes before TerminalApp, because
            self.__class__,      # it will also affect subclasses (e.g. QtConsole)
            TerminalInteractiveShell,
            HistoryManager,
            MagicsManager,
            ProfileDir,
            PlainTextFormatter,
            IPCompleter,
            ScriptMagics,
            LoggingMagics,
            StoreMagics,
        ]

    subcommands = dict(
        profile = ("IPython.core.profileapp.ProfileApp",
            "Create and manage IPython profiles."
        ),
        kernel = ("ipykernel.kernelapp.IPKernelApp",
            "Start a kernel without an attached frontend."
        ),
        locate=('IPython.terminal.ipapp.LocateIPythonApp',
            LocateIPythonApp.description
        ),
        history=('IPython.core.historyapp.HistoryApp',
            "Manage the IPython history database."
        ),
    )

    # *do* autocreate requested profile, but don't create the config file.
    auto_create = Bool(True).tag(config=True)

    # configurables
    quick = Bool(False,
        help="""Start IPython quickly by skipping the loading of config files."""
    ).tag(config=True)
    @observe('quick')
    def _quick_changed(self, change):
        if change['new']:
            self.load_config_file = lambda *a, **kw: None

    display_banner = Bool(True,
        help="Whether to display a banner upon starting IPython."
    ).tag(config=True)

    # if there is code of files to run from the cmd line, don't interact
    # unless the --i flag (App.force_interact) is true.
    force_interact = Bool(False,
        help="""If a command or file is given via the command-line,
        e.g. 'ipython foo.py', start an interactive shell after executing the
        file or command."""
    ).tag(config=True)
    @observe('force_interact')
    def _force_interact_changed(self, change):
        if change['new']:
            self.interact = True

    @observe('file_to_run', 'code_to_run', 'module_to_run')
    def _file_to_run_changed(self, change):
        new = change['new']
        if new:
            self.something_to_run = True
        if new and not self.force_interact:
                self.interact = False

    # internal, not-configurable
    something_to_run=Bool(False)

    @catch_config_error
    def initialize(self, argv=None):
        """Do actions after construct, but before starting the app."""
        super(TerminalIPythonApp, self).initialize(argv)
        if self.subapp is not None:
            # don't bother initializing further, starting subapp
            return
        # print(self.extra_args)
        if self.extra_args and not self.something_to_run:
            self.file_to_run = self.extra_args[0]
        self.init_path()
        # create the shell
        self.init_shell()
        # and draw the banner
        self.init_banner()
        # Now a variety of things that happen after the banner is printed.
        self.init_gui_pylab()
        self.init_extensions()
        self.init_code()

    def init_shell(self):
        """initialize the InteractiveShell instance"""
        # Create an InteractiveShell instance.
        # shell.display_banner should always be False for the terminal
        # based app, because we call shell.show_banner() by hand below
        # so the banner shows *before* all extension loading stuff.
        self.shell = self.interactive_shell_class.instance(parent=self,
                        profile_dir=self.profile_dir,
                        ipython_dir=self.ipython_dir, user_ns=self.user_ns)
        self.shell.configurables.append(self)

    def init_banner(self):
        """optionally display the banner"""
        if self.display_banner and self.interact:
            self.shell.show_banner()
        # Make sure there is a space below the banner.
        if self.log_level <= logging.INFO: print()

    def _pylab_changed(self, name, old, new):
        """Replace --pylab='inline' with --pylab='auto'"""
        if new == 'inline':
            warnings.warn("'inline' not available as pylab backend, "
                      "using 'auto' instead.")
            self.pylab = 'auto'

    def start(self):
        if self.subapp is not None:
            return self.subapp.start()
        # perform any prexec steps:
        if self.interact:
            self.log.debug("Starting IPython's mainloop...")
            self.shell.mainloop()
        else:
            self.log.debug("IPython not interactive...")
            self.shell.restore_term_title()
            if not self.shell.last_execution_succeeded:
                sys.exit(1)

def load_default_config(ipython_dir=None):
    """Load the default config file from the default ipython_dir.

    This is useful for embedded shells.
    """
    if ipython_dir is None:
        ipython_dir = get_ipython_dir()

    profile_dir = os.path.join(ipython_dir, 'profile_default')
    app = TerminalIPythonApp()
    app.config_file_paths.append(profile_dir)
    app.load_config_file()
    return app.config

launch_new_instance = TerminalIPythonApp.launch_instance

# === NexusCore/openenv\Lib\site-packages\nltk\translate\ibm3.py ===
# Natural Language Toolkit: IBM Model 3
#
# Copyright (C) 2001-2013 NLTK Project
# Authors: Chin Yee Lee, Hengfeng Li, Ruxin Hou, Calvin Tanujaya Lim
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Translation model that considers how a word can be aligned to
multiple words in another language.

IBM Model 3 improves on Model 2 by directly modeling the phenomenon
where a word in one language may be translated into zero or more words
in another. This is expressed by the fertility probability,
n(phi | source word).

If a source word translates into more than one word, it is possible to
generate sentences that have the same alignment in multiple ways. This
is modeled by a distortion step. The distortion probability, d(j|i,l,m),
predicts a target word position, given its aligned source word's
position. The distortion probability replaces the alignment probability
of Model 2.

The fertility probability is not applicable for NULL. Target words that
align to NULL are assumed to be distributed uniformly in the target
sentence. The existence of these words is modeled by p1, the probability
that a target word produced by a real source word requires another
target word that is produced by NULL.

The EM algorithm used in Model 3 is:

:E step: In the training data, collect counts, weighted by prior
         probabilities.

         - (a) count how many times a source language word is translated
               into a target language word
         - (b) count how many times a particular position in the target
               sentence is aligned to a particular position in the source
               sentence
         - (c) count how many times a source word is aligned to phi number
               of target words
         - (d) count how many times NULL is aligned to a target word

:M step: Estimate new probabilities based on the counts from the E step

Because there are too many possible alignments, only the most probable
ones are considered. First, the best alignment is determined using prior
probabilities. Then, a hill climbing approach is used to find other good
candidates.

Notations
---------

:i: Position in the source sentence
     Valid values are 0 (for NULL), 1, 2, ..., length of source sentence
:j: Position in the target sentence
     Valid values are 1, 2, ..., length of target sentence
:l: Number of words in the source sentence, excluding NULL
:m: Number of words in the target sentence
:s: A word in the source language
:t: A word in the target language
:phi: Fertility, the number of target words produced by a source word
:p1: Probability that a target word produced by a source word is
     accompanied by another target word that is aligned to NULL
:p0: 1 - p1

References
----------

Philipp Koehn. 2010. Statistical Machine Translation.
Cambridge University Press, New York.

Peter E Brown, Stephen A. Della Pietra, Vincent J. Della Pietra, and
Robert L. Mercer. 1993. The Mathematics of Statistical Machine
Translation: Parameter Estimation. Computational Linguistics, 19 (2),
263-311.
"""

import warnings
from collections import defaultdict
from math import factorial

from nltk.translate import AlignedSent, Alignment, IBMModel, IBMModel2
from nltk.translate.ibm_model import Counts


class IBMModel3(IBMModel):
    """
    Translation model that considers how a word can be aligned to
    multiple words in another language

    >>> bitext = []
    >>> bitext.append(AlignedSent(['klein', 'ist', 'das', 'haus'], ['the', 'house', 'is', 'small']))
    >>> bitext.append(AlignedSent(['das', 'haus', 'war', 'ja', 'groß'], ['the', 'house', 'was', 'big']))
    >>> bitext.append(AlignedSent(['das', 'buch', 'ist', 'ja', 'klein'], ['the', 'book', 'is', 'small']))
    >>> bitext.append(AlignedSent(['ein', 'haus', 'ist', 'klein'], ['a', 'house', 'is', 'small']))
    >>> bitext.append(AlignedSent(['das', 'haus'], ['the', 'house']))
    >>> bitext.append(AlignedSent(['das', 'buch'], ['the', 'book']))
    >>> bitext.append(AlignedSent(['ein', 'buch'], ['a', 'book']))
    >>> bitext.append(AlignedSent(['ich', 'fasse', 'das', 'buch', 'zusammen'], ['i', 'summarize', 'the', 'book']))
    >>> bitext.append(AlignedSent(['fasse', 'zusammen'], ['summarize']))

    >>> ibm3 = IBMModel3(bitext, 5)

    >>> print(round(ibm3.translation_table['buch']['book'], 3))
    1.0
    >>> print(round(ibm3.translation_table['das']['book'], 3))
    0.0
    >>> print(round(ibm3.translation_table['ja'][None], 3))
    1.0

    >>> print(round(ibm3.distortion_table[1][1][2][2], 3))
    1.0
    >>> print(round(ibm3.distortion_table[1][2][2][2], 3))
    0.0
    >>> print(round(ibm3.distortion_table[2][2][4][5], 3))
    0.75

    >>> print(round(ibm3.fertility_table[2]['summarize'], 3))
    1.0
    >>> print(round(ibm3.fertility_table[1]['book'], 3))
    1.0

    >>> print(round(ibm3.p1, 3))
    0.054

    >>> test_sentence = bitext[2]
    >>> test_sentence.words
    ['das', 'buch', 'ist', 'ja', 'klein']
    >>> test_sentence.mots
    ['the', 'book', 'is', 'small']
    >>> test_sentence.alignment
    Alignment([(0, 0), (1, 1), (2, 2), (3, None), (4, 3)])

    """

    def __init__(self, sentence_aligned_corpus, iterations, probability_tables=None):
        """
        Train on ``sentence_aligned_corpus`` and create a lexical
        translation model, a distortion model, a fertility model, and a
        model for generating NULL-aligned words.

        Translation direction is from ``AlignedSent.mots`` to
        ``AlignedSent.words``.

        :param sentence_aligned_corpus: Sentence-aligned parallel corpus
        :type sentence_aligned_corpus: list(AlignedSent)

        :param iterations: Number of iterations to run training algorithm
        :type iterations: int

        :param probability_tables: Optional. Use this to pass in custom
            probability values. If not specified, probabilities will be
            set to a uniform distribution, or some other sensible value.
            If specified, all the following entries must be present:
            ``translation_table``, ``alignment_table``,
            ``fertility_table``, ``p1``, ``distortion_table``.
            See ``IBMModel`` for the type and purpose of these tables.
        :type probability_tables: dict[str]: object
        """
        super().__init__(sentence_aligned_corpus)
        self.reset_probabilities()

        if probability_tables is None:
            # Get translation and alignment probabilities from IBM Model 2
            ibm2 = IBMModel2(sentence_aligned_corpus, iterations)
            self.translation_table = ibm2.translation_table
            self.alignment_table = ibm2.alignment_table
            self.set_uniform_probabilities(sentence_aligned_corpus)
        else:
            # Set user-defined probabilities
            self.translation_table = probability_tables["translation_table"]
            self.alignment_table = probability_tables["alignment_table"]
            self.fertility_table = probability_tables["fertility_table"]
            self.p1 = probability_tables["p1"]
            self.distortion_table = probability_tables["distortion_table"]

        for n in range(0, iterations):
            self.train(sentence_aligned_corpus)

    def reset_probabilities(self):
        super().reset_probabilities()
        self.distortion_table = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(lambda: defaultdict(lambda: self.MIN_PROB))
            )
        )
        """
        dict[int][int][int][int]: float. Probability(j | i,l,m).
        Values accessed as ``distortion_table[j][i][l][m]``.
        """

    def set_uniform_probabilities(self, sentence_aligned_corpus):
        # d(j | i,l,m) = 1 / m for all i, j, l, m
        l_m_combinations = set()
        for aligned_sentence in sentence_aligned_corpus:
            l = len(aligned_sentence.mots)
            m = len(aligned_sentence.words)
            if (l, m) not in l_m_combinations:
                l_m_combinations.add((l, m))
                initial_prob = 1 / m
                if initial_prob < IBMModel.MIN_PROB:
                    warnings.warn(
                        "A target sentence is too long ("
                        + str(m)
                        + " words). Results may be less accurate."
                    )
                for j in range(1, m + 1):
                    for i in range(0, l + 1):
                        self.distortion_table[j][i][l][m] = initial_prob

        # simple initialization, taken from GIZA++
        self.fertility_table[0] = defaultdict(lambda: 0.2)
        self.fertility_table[1] = defaultdict(lambda: 0.65)
        self.fertility_table[2] = defaultdict(lambda: 0.1)
        self.fertility_table[3] = defaultdict(lambda: 0.04)
        MAX_FERTILITY = 10
        initial_fert_prob = 0.01 / (MAX_FERTILITY - 4)
        for phi in range(4, MAX_FERTILITY):
            self.fertility_table[phi] = defaultdict(lambda: initial_fert_prob)

        self.p1 = 0.5

    def train(self, parallel_corpus):
        counts = Model3Counts()
        for aligned_sentence in parallel_corpus:
            l = len(aligned_sentence.mots)
            m = len(aligned_sentence.words)

            # Sample the alignment space
            sampled_alignments, best_alignment = self.sample(aligned_sentence)
            # Record the most probable alignment
            aligned_sentence.alignment = Alignment(
                best_alignment.zero_indexed_alignment()
            )

            # E step (a): Compute normalization factors to weigh counts
            total_count = self.prob_of_alignments(sampled_alignments)

            # E step (b): Collect counts
            for alignment_info in sampled_alignments:
                count = self.prob_t_a_given_s(alignment_info)
                normalized_count = count / total_count

                for j in range(1, m + 1):
                    counts.update_lexical_translation(
                        normalized_count, alignment_info, j
                    )
                    counts.update_distortion(normalized_count, alignment_info, j, l, m)

                counts.update_null_generation(normalized_count, alignment_info)
                counts.update_fertility(normalized_count, alignment_info)

        # M step: Update probabilities with maximum likelihood estimates
        # If any probability is less than MIN_PROB, clamp it to MIN_PROB
        existing_alignment_table = self.alignment_table
        self.reset_probabilities()
        self.alignment_table = existing_alignment_table  # don't retrain

        self.maximize_lexical_translation_probabilities(counts)
        self.maximize_distortion_probabilities(counts)
        self.maximize_fertility_probabilities(counts)
        self.maximize_null_generation_probabilities(counts)

    def maximize_distortion_probabilities(self, counts):
        MIN_PROB = IBMModel.MIN_PROB
        for j, i_s in counts.distortion.items():
            for i, src_sentence_lengths in i_s.items():
                for l, trg_sentence_lengths in src_sentence_lengths.items():
                    for m in trg_sentence_lengths:
                        estimate = (
                            counts.distortion[j][i][l][m]
                            / counts.distortion_for_any_j[i][l][m]
                        )
                        self.distortion_table[j][i][l][m] = max(estimate, MIN_PROB)

    def prob_t_a_given_s(self, alignment_info):
        """
        Probability of target sentence and an alignment given the
        source sentence
        """
        src_sentence = alignment_info.src_sentence
        trg_sentence = alignment_info.trg_sentence
        l = len(src_sentence) - 1  # exclude NULL
        m = len(trg_sentence) - 1
        p1 = self.p1
        p0 = 1 - p1

        probability = 1.0
        MIN_PROB = IBMModel.MIN_PROB

        # Combine NULL insertion probability
        null_fertility = alignment_info.fertility_of_i(0)
        probability *= pow(p1, null_fertility) * pow(p0, m - 2 * null_fertility)
        if probability < MIN_PROB:
            return MIN_PROB

        # Compute combination (m - null_fertility) choose null_fertility
        for i in range(1, null_fertility + 1):
            probability *= (m - null_fertility - i + 1) / i
            if probability < MIN_PROB:
                return MIN_PROB

        # Combine fertility probabilities
        for i in range(1, l + 1):
            fertility = alignment_info.fertility_of_i(i)
            probability *= (
                factorial(fertility) * self.fertility_table[fertility][src_sentence[i]]
            )
            if probability < MIN_PROB:
                return MIN_PROB

        # Combine lexical and distortion probabilities
        for j in range(1, m + 1):
            t = trg_sentence[j]
            i = alignment_info.alignment[j]
            s = src_sentence[i]

            probability *= (
                self.translation_table[t][s] * self.distortion_table[j][i][l][m]
            )
            if probability < MIN_PROB:
                return MIN_PROB

        return probability


class Model3Counts(Counts):
    """
    Data object to store counts of various parameters during training.
    Includes counts for distortion.
    """

    def __init__(self):
        super().__init__()
        self.distortion = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        )
        self.distortion_for_any_j = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float))
        )

    def update_distortion(self, count, alignment_info, j, l, m):
        i = alignment_info.alignment[j]
        self.distortion[j][i][l][m] += count
        self.distortion_for_any_j[i][l][m] += count

# === NexusCore/openenv\Lib\site-packages\jedi\parser_utils.py ===
import re
import textwrap
from ast import literal_eval
from inspect import cleandoc
from weakref import WeakKeyDictionary

from parso.python import tree
from parso.cache import parser_cache
from parso import split_lines

_EXECUTE_NODES = {'funcdef', 'classdef', 'import_from', 'import_name', 'test',
                  'or_test', 'and_test', 'not_test', 'comparison', 'expr',
                  'xor_expr', 'and_expr', 'shift_expr', 'arith_expr',
                  'atom_expr', 'term', 'factor', 'power', 'atom'}

_FLOW_KEYWORDS = (
    'try', 'except', 'finally', 'else', 'if', 'elif', 'with', 'for', 'while'
)


def get_executable_nodes(node, last_added=False):
    """
    For static analysis.
    """
    result = []
    typ = node.type
    if typ == 'name':
        next_leaf = node.get_next_leaf()
        if last_added is False and node.parent.type != 'param' and next_leaf != '=':
            result.append(node)
    elif typ == 'expr_stmt':
        # I think inferring the statement (and possibly returned arrays),
        # should be enough for static analysis.
        result.append(node)
        for child in node.children:
            result += get_executable_nodes(child, last_added=True)
    elif typ == 'decorator':
        # decorator
        if node.children[-2] == ')':
            node = node.children[-3]
            if node != '(':
                result += get_executable_nodes(node)
    else:
        try:
            children = node.children
        except AttributeError:
            pass
        else:
            if node.type in _EXECUTE_NODES and not last_added:
                result.append(node)

            for child in children:
                result += get_executable_nodes(child, last_added)

    return result


def get_sync_comp_fors(comp_for):
    yield comp_for
    last = comp_for.children[-1]
    while True:
        if last.type == 'comp_for':
            yield last.children[1]  # Ignore the async.
        elif last.type == 'sync_comp_for':
            yield last
        elif not last.type == 'comp_if':
            break
        last = last.children[-1]


def for_stmt_defines_one_name(for_stmt):
    """
    Returns True if only one name is returned: ``for x in y``.
    Returns False if the for loop is more complicated: ``for x, z in y``.

    :returns: bool
    """
    return for_stmt.children[1].type == 'name'


def get_flow_branch_keyword(flow_node, node):
    start_pos = node.start_pos
    if not (flow_node.start_pos < start_pos <= flow_node.end_pos):
        raise ValueError('The node is not part of the flow.')

    keyword = None
    for i, child in enumerate(flow_node.children):
        if start_pos < child.start_pos:
            return keyword
        first_leaf = child.get_first_leaf()
        if first_leaf in _FLOW_KEYWORDS:
            keyword = first_leaf
    return None


def clean_scope_docstring(scope_node):
    """ Returns a cleaned version of the docstring token. """
    node = scope_node.get_doc_node()
    if node is not None:
        # TODO We have to check next leaves until there are no new
        # leaves anymore that might be part of the docstring. A
        # docstring can also look like this: ``'foo' 'bar'
        # Returns a literal cleaned version of the ``Token``.
        return cleandoc(safe_literal_eval(node.value))
    return ''


def find_statement_documentation(tree_node):
    if tree_node.type == 'expr_stmt':
        tree_node = tree_node.parent  # simple_stmt
        maybe_string = tree_node.get_next_sibling()
        if maybe_string is not None:
            if maybe_string.type == 'simple_stmt':
                maybe_string = maybe_string.children[0]
                if maybe_string.type == 'string':
                    return cleandoc(safe_literal_eval(maybe_string.value))
    return ''


def safe_literal_eval(value):
    first_two = value[:2].lower()
    if first_two[0] == 'f' or first_two in ('fr', 'rf'):
        # literal_eval is not able to resovle f literals. We have to do that
        # manually, but that's right now not implemented.
        return ''

    return literal_eval(value)


def get_signature(funcdef, width=72, call_string=None,
                  omit_first_param=False, omit_return_annotation=False):
    """
    Generate a string signature of a function.

    :param width: Fold lines if a line is longer than this value.
    :type width: int
    :arg func_name: Override function name when given.
    :type func_name: str

    :rtype: str
    """
    # Lambdas have no name.
    if call_string is None:
        if funcdef.type == 'lambdef':
            call_string = '<lambda>'
        else:
            call_string = funcdef.name.value
    params = funcdef.get_params()
    if omit_first_param:
        params = params[1:]
    p = '(' + ''.join(param.get_code() for param in params).strip() + ')'
    # TODO this is pretty bad, we should probably just normalize.
    p = re.sub(r'\s+', ' ', p)
    if funcdef.annotation and not omit_return_annotation:
        rtype = " ->" + funcdef.annotation.get_code()
    else:
        rtype = ""
    code = call_string + p + rtype

    return '\n'.join(textwrap.wrap(code, width))


def move(node, line_offset):
    """
    Move the `Node` start_pos.
    """
    try:
        children = node.children
    except AttributeError:
        node.line += line_offset
    else:
        for c in children:
            move(c, line_offset)


def get_following_comment_same_line(node):
    """
    returns (as string) any comment that appears on the same line,
    after the node, including the #
    """
    try:
        if node.type == 'for_stmt':
            whitespace = node.children[5].get_first_leaf().prefix
        elif node.type == 'with_stmt':
            whitespace = node.children[3].get_first_leaf().prefix
        elif node.type == 'funcdef':
            # actually on the next line
            whitespace = node.children[4].get_first_leaf().get_next_leaf().prefix
        else:
            whitespace = node.get_last_leaf().get_next_leaf().prefix
    except AttributeError:
        return None
    except ValueError:
        # TODO in some particular cases, the tree doesn't seem to be linked
        # correctly
        return None
    if "#" not in whitespace:
        return None
    comment = whitespace[whitespace.index("#"):]
    if "\r" in comment:
        comment = comment[:comment.index("\r")]
    if "\n" in comment:
        comment = comment[:comment.index("\n")]
    return comment


def is_scope(node):
    t = node.type
    if t == 'comp_for':
        # Starting with Python 3.8, async is outside of the statement.
        return node.children[1].type != 'sync_comp_for'

    return t in ('file_input', 'classdef', 'funcdef', 'lambdef', 'sync_comp_for')


def _get_parent_scope_cache(func):
    cache = WeakKeyDictionary()

    def wrapper(parso_cache_node, node, include_flows=False):
        if parso_cache_node is None:
            return func(node, include_flows)

        try:
            for_module = cache[parso_cache_node]
        except KeyError:
            for_module = cache[parso_cache_node] = {}

        try:
            return for_module[node]
        except KeyError:
            result = for_module[node] = func(node, include_flows)
            return result
    return wrapper


def get_parent_scope(node, include_flows=False):
    """
    Returns the underlying scope.
    """
    scope = node.parent
    if scope is None:
        return None  # It's a module already.

    while True:
        if is_scope(scope):
            if scope.type in ('classdef', 'funcdef', 'lambdef'):
                index = scope.children.index(':')
                if scope.children[index].start_pos >= node.start_pos:
                    if node.parent.type == 'param' and node.parent.name == node:
                        pass
                    elif node.parent.type == 'tfpdef' and node.parent.children[0] == node:
                        pass
                    else:
                        scope = scope.parent
                        continue
            return scope
        elif include_flows and isinstance(scope, tree.Flow):
            # The cursor might be on `if foo`, so the parent scope will not be
            # the if, but the parent of the if.
            if not (scope.type == 'if_stmt'
                    and any(n.start_pos <= node.start_pos < n.end_pos
                            for n in scope.get_test_nodes())):
                return scope

        scope = scope.parent


get_cached_parent_scope = _get_parent_scope_cache(get_parent_scope)


def get_cached_code_lines(grammar, path):
    """
    Basically access the cached code lines in parso. This is not the nicest way
    to do this, but we avoid splitting all the lines again.
    """
    return get_parso_cache_node(grammar, path).lines


def get_parso_cache_node(grammar, path):
    """
    This is of course not public. But as long as I control parso, this
    shouldn't be a problem. ~ Dave

    The reason for this is mostly caching. This is obviously also a sign of a
    broken caching architecture.
    """
    return parser_cache[grammar._hashed][path]


def cut_value_at_position(leaf, position):
    """
    Cuts of the value of the leaf at position
    """
    lines = split_lines(leaf.value, keepends=True)[:position[0] - leaf.line + 1]
    column = position[1]
    if leaf.line == position[0]:
        column -= leaf.column
    if not lines:
        return ''
    lines[-1] = lines[-1][:column]
    return ''.join(lines)


def expr_is_dotted(node):
    """
    Checks if a path looks like `name` or `name.foo.bar` and not `name()`.
    """
    if node.type == 'atom':
        if len(node.children) == 3 and node.children[0] == '(':
            return expr_is_dotted(node.children[1])
        return False
    if node.type == 'atom_expr':
        children = node.children
        if children[0] == 'await':
            return False
        if not expr_is_dotted(children[0]):
            return False
        # Check trailers
        return all(c.children[0] == '.' for c in children[1:])
    return node.type == 'name'


def _function_is_x_method(decorator_checker):
    def wrapper(function_node):
        """
        This is a heuristic. It will not hold ALL the times, but it will be
        correct pretty much for anyone that doesn't try to beat it.
        staticmethod/classmethod are builtins and unless overwritten, this will
        be correct.
        """
        for decorator in function_node.get_decorators():
            dotted_name = decorator.children[1]
            if decorator_checker(dotted_name.get_code()):
                return True
        return False
    return wrapper


function_is_staticmethod = _function_is_x_method(lambda m: m == "staticmethod")
function_is_classmethod = _function_is_x_method(lambda m: m == "classmethod")
function_is_property = _function_is_x_method(
    lambda m: m == "property"
    or m == "cached_property"
    or (m.endswith(".setter"))
)

# === NexusCore/openenv\Lib\site-packages\markdown_it\tree.py ===
"""A tree representation of a linear markdown-it token stream.

This module is not part of upstream JavaScript markdown-it.
"""
from __future__ import annotations

from collections.abc import Generator, Sequence
import textwrap
from typing import Any, NamedTuple, TypeVar, overload

from .token import Token


class _NesterTokens(NamedTuple):
    opening: Token
    closing: Token


_NodeType = TypeVar("_NodeType", bound="SyntaxTreeNode")


class SyntaxTreeNode:
    """A Markdown syntax tree node.

    A class that can be used to construct a tree representation of a linear
    `markdown-it-py` token stream.

    Each node in the tree represents either:
      - root of the Markdown document
      - a single unnested `Token`
      - a `Token` "_open" and "_close" token pair, and the tokens nested in
          between
    """

    def __init__(
        self, tokens: Sequence[Token] = (), *, create_root: bool = True
    ) -> None:
        """Initialize a `SyntaxTreeNode` from a token stream.

        If `create_root` is True, create a root node for the document.
        """
        # Only nodes representing an unnested token have self.token
        self.token: Token | None = None

        # Only containers have nester tokens
        self.nester_tokens: _NesterTokens | None = None

        # Root node does not have self.parent
        self._parent: Any = None

        # Empty list unless a non-empty container, or unnested token that has
        # children (i.e. inline or img)
        self._children: list[Any] = []

        if create_root:
            self._set_children_from_tokens(tokens)
            return

        if not tokens:
            raise ValueError(
                "Can only create root from empty token sequence."
                " Set `create_root=True`."
            )
        elif len(tokens) == 1:
            inline_token = tokens[0]
            if inline_token.nesting:
                raise ValueError(
                    "Unequal nesting level at the start and end of token stream."
                )
            self.token = inline_token
            if inline_token.children:
                self._set_children_from_tokens(inline_token.children)
        else:
            self.nester_tokens = _NesterTokens(tokens[0], tokens[-1])
            self._set_children_from_tokens(tokens[1:-1])

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.type})"

    @overload
    def __getitem__(self: _NodeType, item: int) -> _NodeType:
        ...

    @overload
    def __getitem__(self: _NodeType, item: slice) -> list[_NodeType]:
        ...

    def __getitem__(self: _NodeType, item: int | slice) -> _NodeType | list[_NodeType]:
        return self.children[item]

    def to_tokens(self: _NodeType) -> list[Token]:
        """Recover the linear token stream."""

        def recursive_collect_tokens(node: _NodeType, token_list: list[Token]) -> None:
            if node.type == "root":
                for child in node.children:
                    recursive_collect_tokens(child, token_list)
            elif node.token:
                token_list.append(node.token)
            else:
                assert node.nester_tokens
                token_list.append(node.nester_tokens.opening)
                for child in node.children:
                    recursive_collect_tokens(child, token_list)
                token_list.append(node.nester_tokens.closing)

        tokens: list[Token] = []
        recursive_collect_tokens(self, tokens)
        return tokens

    @property
    def children(self: _NodeType) -> list[_NodeType]:
        return self._children

    @children.setter
    def children(self: _NodeType, value: list[_NodeType]) -> None:
        self._children = value

    @property
    def parent(self: _NodeType) -> _NodeType | None:
        return self._parent  # type: ignore

    @parent.setter
    def parent(self: _NodeType, value: _NodeType | None) -> None:
        self._parent = value

    @property
    def is_root(self) -> bool:
        """Is the node a special root node?"""
        return not (self.token or self.nester_tokens)

    @property
    def is_nested(self) -> bool:
        """Is this node nested?.

        Returns `True` if the node represents a `Token` pair and tokens in the
        sequence between them, where `Token.nesting` of the first `Token` in
        the pair is 1 and nesting of the other `Token` is -1.
        """
        return bool(self.nester_tokens)

    @property
    def siblings(self: _NodeType) -> Sequence[_NodeType]:
        """Get siblings of the node.

        Gets the whole group of siblings, including self.
        """
        if not self.parent:
            return [self]
        return self.parent.children

    @property
    def type(self) -> str:
        """Get a string type of the represented syntax.

        - "root" for root nodes
        - `Token.type` if the node represents an unnested token
        - `Token.type` of the opening token, with "_open" suffix stripped, if
            the node represents a nester token pair
        """
        if self.is_root:
            return "root"
        if self.token:
            return self.token.type
        assert self.nester_tokens
        return _removesuffix(self.nester_tokens.opening.type, "_open")

    @property
    def next_sibling(self: _NodeType) -> _NodeType | None:
        """Get the next node in the sequence of siblings.

        Returns `None` if this is the last sibling.
        """
        self_index = self.siblings.index(self)
        if self_index + 1 < len(self.siblings):
            return self.siblings[self_index + 1]
        return None

    @property
    def previous_sibling(self: _NodeType) -> _NodeType | None:
        """Get the previous node in the sequence of siblings.

        Returns `None` if this is the first sibling.
        """
        self_index = self.siblings.index(self)
        if self_index - 1 >= 0:
            return self.siblings[self_index - 1]
        return None

    def _add_child(
        self,
        tokens: Sequence[Token],
    ) -> None:
        """Make a child node for `self`."""
        child = type(self)(tokens, create_root=False)
        child.parent = self
        self.children.append(child)

    def _set_children_from_tokens(self, tokens: Sequence[Token]) -> None:
        """Convert the token stream to a tree structure and set the resulting
        nodes as children of `self`."""
        reversed_tokens = list(reversed(tokens))
        while reversed_tokens:
            token = reversed_tokens.pop()

            if not token.nesting:
                self._add_child([token])
                continue
            if token.nesting != 1:
                raise ValueError("Invalid token nesting")

            nested_tokens = [token]
            nesting = 1
            while reversed_tokens and nesting:
                token = reversed_tokens.pop()
                nested_tokens.append(token)
                nesting += token.nesting
            if nesting:
                raise ValueError(f"unclosed tokens starting {nested_tokens[0]}")

            self._add_child(nested_tokens)

    def pretty(
        self, *, indent: int = 2, show_text: bool = False, _current: int = 0
    ) -> str:
        """Create an XML style string of the tree."""
        prefix = " " * _current
        text = prefix + f"<{self.type}"
        if not self.is_root and self.attrs:
            text += " " + " ".join(f"{k}={v!r}" for k, v in self.attrs.items())
        text += ">"
        if (
            show_text
            and not self.is_root
            and self.type in ("text", "text_special")
            and self.content
        ):
            text += "\n" + textwrap.indent(self.content, prefix + " " * indent)
        for child in self.children:
            text += "\n" + child.pretty(
                indent=indent, show_text=show_text, _current=_current + indent
            )
        return text

    def walk(
        self: _NodeType, *, include_self: bool = True
    ) -> Generator[_NodeType, None, None]:
        """Recursively yield all descendant nodes in the tree starting at self.

        The order mimics the order of the underlying linear token
        stream (i.e. depth first).
        """
        if include_self:
            yield self
        for child in self.children:
            yield from child.walk(include_self=True)

    # NOTE:
    # The values of the properties defined below directly map to properties
    # of the underlying `Token`s. A root node does not translate to a `Token`
    # object, so calling these property getters on a root node will raise an
    # `AttributeError`.
    #
    # There is no mapping for `Token.nesting` because the `is_nested` property
    # provides that data, and can be called on any node type, including root.

    def _attribute_token(self) -> Token:
        """Return the `Token` that is used as the data source for the
        properties defined below."""
        if self.token:
            return self.token
        if self.nester_tokens:
            return self.nester_tokens.opening
        raise AttributeError("Root node does not have the accessed attribute")

    @property
    def tag(self) -> str:
        """html tag name, e.g. \"p\" """
        return self._attribute_token().tag

    @property
    def attrs(self) -> dict[str, str | int | float]:
        """Html attributes."""
        return self._attribute_token().attrs

    def attrGet(self, name: str) -> None | str | int | float:
        """Get the value of attribute `name`, or null if it does not exist."""
        return self._attribute_token().attrGet(name)

    @property
    def map(self) -> tuple[int, int] | None:
        """Source map info. Format: `tuple[ line_begin, line_end ]`"""
        map_ = self._attribute_token().map
        if map_:
            # Type ignore because `Token`s attribute types are not perfect
            return tuple(map_)  # type: ignore
        return None

    @property
    def level(self) -> int:
        """nesting level, the same as `state.level`"""
        return self._attribute_token().level

    @property
    def content(self) -> str:
        """In a case of self-closing tag (code, html, fence, etc.), it
        has contents of this tag."""
        return self._attribute_token().content

    @property
    def markup(self) -> str:
        """'*' or '_' for emphasis, fence string for fence, etc."""
        return self._attribute_token().markup

    @property
    def info(self) -> str:
        """fence infostring"""
        return self._attribute_token().info

    @property
    def meta(self) -> dict[Any, Any]:
        """A place for plugins to store an arbitrary data."""
        return self._attribute_token().meta

    @property
    def block(self) -> bool:
        """True for block-level tokens, false for inline tokens."""
        return self._attribute_token().block

    @property
    def hidden(self) -> bool:
        """If it's true, ignore this element when rendering.
        Used for tight lists to hide paragraphs."""
        return self._attribute_token().hidden


def _removesuffix(string: str, suffix: str) -> str:
    """Remove a suffix from a string.

    Replace this with str.removesuffix() from stdlib when minimum Python
    version is 3.9.
    """
    if suffix and string.endswith(suffix):
        return string[: -len(suffix)]
    return string

# === NexusCore/openenv\Lib\site-packages\wcwidth\wcwidth.py ===
"""
This is a python implementation of wcwidth() and wcswidth().

https://github.com/jquast/wcwidth

from Markus Kuhn's C code, retrieved from:

    http://www.cl.cam.ac.uk/~mgk25/ucs/wcwidth.c

This is an implementation of wcwidth() and wcswidth() (defined in
IEEE Std 1002.1-2001) for Unicode.

http://www.opengroup.org/onlinepubs/007904975/functions/wcwidth.html
http://www.opengroup.org/onlinepubs/007904975/functions/wcswidth.html

In fixed-width output devices, Latin characters all occupy a single
"cell" position of equal width, whereas ideographic CJK characters
occupy two such cells. Interoperability between terminal-line
applications and (teletype-style) character terminals using the
UTF-8 encoding requires agreement on which character should advance
the cursor by how many cell positions. No established formal
standards exist at present on which Unicode character shall occupy
how many cell positions on character terminals. These routines are
a first attempt of defining such behavior based on simple rules
applied to data provided by the Unicode Consortium.

For some graphical characters, the Unicode standard explicitly
defines a character-cell width via the definition of the East Asian
FullWidth (F), Wide (W), Half-width (H), and Narrow (Na) classes.
In all these cases, there is no ambiguity about which width a
terminal shall use. For characters in the East Asian Ambiguous (A)
class, the width choice depends purely on a preference of backward
compatibility with either historic CJK or Western practice.
Choosing single-width for these characters is easy to justify as
the appropriate long-term solution, as the CJK practice of
displaying these characters as double-width comes from historic
implementation simplicity (8-bit encoded characters were displayed
single-width and 16-bit ones double-width, even for Greek,
Cyrillic, etc.) and not any typographic considerations.

Much less clear is the choice of width for the Not East Asian
(Neutral) class. Existing practice does not dictate a width for any
of these characters. It would nevertheless make sense
typographically to allocate two character cells to characters such
as for instance EM SPACE or VOLUME INTEGRAL, which cannot be
represented adequately with a single-width glyph. The following
routines at present merely assign a single-cell width to all
neutral characters, in the interest of simplicity. This is not
entirely satisfactory and should be reconsidered before
establishing a formal standard in this area. At the moment, the
decision which Not East Asian (Neutral) characters should be
represented by double-width glyphs cannot yet be answered by
applying a simple rule from the Unicode database content. Setting
up a proper standard for the behavior of UTF-8 character terminals
will require a careful analysis not only of each Unicode character,
but also of each presentation form, something the author of these
routines has avoided to do so far.

http://www.unicode.org/unicode/reports/tr11/

Latest version: http://www.cl.cam.ac.uk/~mgk25/ucs/wcwidth.c
"""
from __future__ import division

# std imports
import os
import sys
import warnings

# local
from .table_vs16 import VS16_NARROW_TO_WIDE
from .table_wide import WIDE_EASTASIAN
from .table_zero import ZERO_WIDTH
from .unicode_versions import list_versions

try:
    # std imports
    from functools import lru_cache
except ImportError:
    # lru_cache was added in Python 3.2
    # 3rd party
    from backports.functools_lru_cache import lru_cache

# global cache
_PY3 = sys.version_info[0] >= 3


def _bisearch(ucs, table):
    """
    Auxiliary function for binary search in interval table.

    :arg int ucs: Ordinal value of unicode character.
    :arg list table: List of starting and ending ranges of ordinal values,
        in form of ``[(start, end), ...]``.
    :rtype: int
    :returns: 1 if ordinal value ucs is found within lookup table, else 0.
    """
    lbound = 0
    ubound = len(table) - 1

    if ucs < table[0][0] or ucs > table[ubound][1]:
        return 0
    while ubound >= lbound:
        mid = (lbound + ubound) // 2
        if ucs > table[mid][1]:
            lbound = mid + 1
        elif ucs < table[mid][0]:
            ubound = mid - 1
        else:
            return 1

    return 0


@lru_cache(maxsize=1000)
def wcwidth(wc, unicode_version='auto'):
    r"""
    Given one Unicode character, return its printable length on a terminal.

    :param str wc: A single Unicode character.
    :param str unicode_version: A Unicode version number, such as
        ``'6.0.0'``. A list of version levels suported by wcwidth
        is returned by :func:`list_versions`.

        Any version string may be specified without error -- the nearest
        matching version is selected.  When ``latest`` (default), the
        highest Unicode version level is used.
    :return: The width, in cells, necessary to display the character of
        Unicode string character, ``wc``.  Returns 0 if the ``wc`` argument has
        no printable effect on a terminal (such as NUL '\0'), -1 if ``wc`` is
        not printable, or has an indeterminate effect on the terminal, such as
        a control character.  Otherwise, the number of column positions the
        character occupies on a graphic terminal (1 or 2) is returned.
    :rtype: int

    See :ref:`Specification` for details of cell measurement.
    """
    ucs = ord(wc) if wc else 0

    # small optimization: early return of 1 for printable ASCII, this provides
    # approximately 40% performance improvement for mostly-ascii documents, with
    # less than 1% impact to others.
    if 32 <= ucs < 0x7f:
        return 1

    # C0/C1 control characters are -1 for compatibility with POSIX-like calls
    if ucs and ucs < 32 or 0x07F <= ucs < 0x0A0:
        return -1

    _unicode_version = _wcmatch_version(unicode_version)

    # Zero width
    if _bisearch(ucs, ZERO_WIDTH[_unicode_version]):
        return 0

    # 1 or 2 width
    return 1 + _bisearch(ucs, WIDE_EASTASIAN[_unicode_version])


def wcswidth(pwcs, n=None, unicode_version='auto'):
    """
    Given a unicode string, return its printable length on a terminal.

    :param str pwcs: Measure width of given unicode string.
    :param int n: When ``n`` is None (default), return the length of the entire
        string, otherwise only the first ``n`` characters are measured. This
        argument exists only for compatibility with the C POSIX function
        signature. It is suggested instead to use python's string slicing
        capability, ``wcswidth(pwcs[:n])``
    :param str unicode_version: An explicit definition of the unicode version
        level to use for determination, may be ``auto`` (default), which uses
        the Environment Variable, ``UNICODE_VERSION`` if defined, or the latest
        available unicode version, otherwise.
    :rtype: int
    :returns: The width, in cells, needed to display the first ``n`` characters
        of the unicode string ``pwcs``.  Returns ``-1`` for C0 and C1 control
        characters!

    See :ref:`Specification` for details of cell measurement.
    """
    # this 'n' argument is a holdover for POSIX function
    _unicode_version = None
    end = len(pwcs) if n is None else n
    width = 0
    idx = 0
    last_measured_char = None
    while idx < end:
        char = pwcs[idx]
        if char == u'\u200D':
            # Zero Width Joiner, do not measure this or next character
            idx += 2
            continue
        if char == u'\uFE0F' and last_measured_char:
            # on variation selector 16 (VS16) following another character,
            # conditionally add '1' to the measured width if that character is
            # known to be converted from narrow to wide by the VS16 character.
            if _unicode_version is None:
                _unicode_version = _wcversion_value(_wcmatch_version(unicode_version))
            if _unicode_version >= (9, 0, 0):
                width += _bisearch(ord(last_measured_char), VS16_NARROW_TO_WIDE["9.0.0"])
                last_measured_char = None
            idx += 1
            continue
        # measure character at current index
        wcw = wcwidth(char, unicode_version)
        if wcw < 0:
            # early return -1 on C0 and C1 control characters
            return wcw
        if wcw > 0:
            # track last character measured to contain a cell, so that
            # subsequent VS-16 modifiers may be understood
            last_measured_char = char
        width += wcw
        idx += 1
    return width


@lru_cache(maxsize=128)
def _wcversion_value(ver_string):
    """
    Integer-mapped value of given dotted version string.

    :param str ver_string: Unicode version string, of form ``n.n.n``.
    :rtype: tuple(int)
    :returns: tuple of digit tuples, ``tuple(int, [...])``.
    """
    retval = tuple(map(int, (ver_string.split('.'))))
    return retval


@lru_cache(maxsize=8)
def _wcmatch_version(given_version):
    """
    Return nearest matching supported Unicode version level.

    If an exact match is not determined, the nearest lowest version level is
    returned after a warning is emitted.  For example, given supported levels
    ``4.1.0`` and ``5.0.0``, and a version string of ``4.9.9``, then ``4.1.0``
    is selected and returned:

    >>> _wcmatch_version('4.9.9')
    '4.1.0'
    >>> _wcmatch_version('8.0')
    '8.0.0'
    >>> _wcmatch_version('1')
    '4.1.0'

    :param str given_version: given version for compare, may be ``auto``
        (default), to select Unicode Version from Environment Variable,
        ``UNICODE_VERSION``. If the environment variable is not set, then the
        latest is used.
    :rtype: str
    :returns: unicode string, or non-unicode ``str`` type for python 2
        when given ``version`` is also type ``str``.
    """
    # Design note: the choice to return the same type that is given certainly
    # complicates it for python 2 str-type, but allows us to define an api that
    # uses 'string-type' for unicode version level definitions, so all of our
    # example code works with all versions of python.
    #
    # That, along with the string-to-numeric and comparisons of earliest,
    # latest, matching, or nearest, greatly complicates this function.
    # Performance is somewhat curbed by memoization.
    _return_str = not _PY3 and isinstance(given_version, str)

    if _return_str:
        # avoid list-comprehension to work around a coverage issue:
        # https://github.com/nedbat/coveragepy/issues/753
        unicode_versions = list(map(lambda ucs: ucs.encode(), list_versions()))
    else:
        unicode_versions = list_versions()
    latest_version = unicode_versions[-1]

    if given_version in (u'auto', 'auto'):
        given_version = os.environ.get(
            'UNICODE_VERSION',
            'latest' if not _return_str else latest_version.encode())

    if given_version in (u'latest', 'latest'):
        # default match, when given as 'latest', use the most latest unicode
        # version specification level supported.
        return latest_version if not _return_str else latest_version.encode()

    if given_version in unicode_versions:
        # exact match, downstream has specified an explicit matching version
        # matching any value of list_versions().
        return given_version if not _return_str else given_version.encode()

    # The user's version is not supported by ours. We return the newest unicode
    # version level that we support below their given value.
    try:
        cmp_given = _wcversion_value(given_version)

    except ValueError:
        # submitted value raises ValueError in int(), warn and use latest.
        warnings.warn("UNICODE_VERSION value, {given_version!r}, is invalid. "
                      "Value should be in form of `integer[.]+', the latest "
                      "supported unicode version {latest_version!r} has been "
                      "inferred.".format(given_version=given_version,
                                         latest_version=latest_version))
        return latest_version if not _return_str else latest_version.encode()

    # given version is less than any available version, return earliest
    # version.
    earliest_version = unicode_versions[0]
    cmp_earliest_version = _wcversion_value(earliest_version)

    if cmp_given <= cmp_earliest_version:
        # this probably isn't what you wanted, the oldest wcwidth.c you will
        # find in the wild is likely version 5 or 6, which we both support,
        # but it's better than not saying anything at all.
        warnings.warn("UNICODE_VERSION value, {given_version!r}, is lower "
                      "than any available unicode version. Returning lowest "
                      "version level, {earliest_version!r}".format(
                          given_version=given_version,
                          earliest_version=earliest_version))
        return earliest_version if not _return_str else earliest_version.encode()

    # create list of versions which are less than our equal to given version,
    # and return the tail value, which is the highest level we may support,
    # or the latest value we support, when completely unmatched or higher
    # than any supported version.
    #
    # function will never complete, always returns.
    for idx, unicode_version in enumerate(unicode_versions):
        # look ahead to next value
        try:
            cmp_next_version = _wcversion_value(unicode_versions[idx + 1])
        except IndexError:
            # at end of list, return latest version
            return latest_version if not _return_str else latest_version.encode()

        # Maybe our given version has less parts, as in tuple(8, 0), than the
        # next compare version tuple(8, 0, 0). Test for an exact match by
        # comparison of only the leading dotted piece(s): (8, 0) == (8, 0).
        if cmp_given == cmp_next_version[:len(cmp_given)]:
            return unicode_versions[idx + 1]

        # Or, if any next value is greater than our given support level
        # version, return the current value in index.  Even though it must
        # be less than the given value, its our closest possible match. That
        # is, 4.1 is returned for given 4.9.9, where 4.1 and 5.0 are available.
        if cmp_next_version > cmp_given:
            return unicode_version
    assert False, ("Code path unreachable", given_version, unicode_versions)  # pragma: no cover

# === NexusCore/openenv\Lib\site-packages\google\api_core\operations_v1\operations_rest_client_async.py ===
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
from typing import Optional, Sequence, Tuple, Union

from google.api_core import client_options as client_options_lib  # type: ignore
from google.api_core import gapic_v1  # type: ignore
from google.api_core.operations_v1 import pagers_async as pagers
from google.api_core.operations_v1.transports.base import (
    DEFAULT_CLIENT_INFO,
    OperationsTransport,
)
from google.api_core.operations_v1.abstract_operations_base_client import (
    AbstractOperationsBaseClient,
)
from google.longrunning import operations_pb2

try:
    from google.auth.aio import credentials as ga_credentials  # type: ignore
except ImportError as e:  # pragma: NO COVER
    raise ImportError(
        "The `async_rest` extra of `google-api-core` is required to use long-running operations.  Install it by running "
        "`pip install google-api-core[async_rest]`."
    ) from e


class AsyncOperationsRestClient(AbstractOperationsBaseClient):
    """Manages long-running operations with a REST API service for the asynchronous client.

    When an API method normally takes long time to complete, it can be
    designed to return [Operation][google.api_core.operations_v1.Operation] to the
    client, and the client can use this interface to receive the real
    response asynchronously by polling the operation resource, or pass
    the operation resource to another API (such as Google Cloud Pub/Sub
    API) to receive the response. Any API service that returns
    long-running operations should implement the ``Operations``
    interface so developers can have a consistent client experience.
    """

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Union[str, OperationsTransport, None] = None,
        client_options: Optional[client_options_lib.ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the operations client.

        Args:
            credentials (Optional[google.auth.aio.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Union[str, OperationsTransport]): The
                transport to use. If set to None, this defaults to 'rest_asyncio'.
            client_options (google.api_core.client_options.ClientOptions): Custom options for the
                client. It won't take effect if a ``transport`` instance is provided.
                (1) The ``api_endpoint`` property can be used to override the
                default endpoint provided by the client. GOOGLE_API_USE_MTLS_ENDPOINT
                environment variable can also be used to override the endpoint:
                "always" (always use the default mTLS endpoint), "never" (always
                use the default regular endpoint) and "auto" (auto switch to the
                default mTLS endpoint if client certificate is present, this is
                the default value). However, the ``api_endpoint`` property takes
                precedence if provided.
                (2) If GOOGLE_API_USE_CLIENT_CERTIFICATE environment variable
                is "true", then the ``client_cert_source`` property can be used
                to provide client certificate for mutual TLS transport. If
                not provided, the default SSL client certificate will be used if
                present. If GOOGLE_API_USE_CLIENT_CERTIFICATE is "false" or not
                set, no client certificate will be used.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        super().__init__(
            credentials=credentials,  # type: ignore
            # NOTE: If a transport is not provided, we force the client to use the async
            # REST transport.
            transport=transport or "rest_asyncio",
            client_options=client_options,
            client_info=client_info,
        )

    async def get_operation(
        self,
        name: str,
        *,
        # TODO(https://github.com/googleapis/python-api-core/issues/722): Leverage `retry`
        # to allow configuring retryable error codes.
        retry=gapic_v1.method_async.DEFAULT,
        timeout: Optional[float] = None,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operations_pb2.Operation:
        r"""Gets the latest state of a long-running operation.
        Clients can use this method to poll the operation result
        at intervals as recommended by the API service.

        Args:
            name (str):
                The name of the operation resource.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.longrunning.operations_pb2.Operation:
                This resource represents a long-
                running operation that is the result of a
                network API call.

        """

        request = operations_pb2.GetOperationRequest(name=name)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.get_operation]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata or ()) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def list_operations(
        self,
        name: str,
        filter_: Optional[str] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        # TODO(https://github.com/googleapis/python-api-core/issues/722): Leverage `retry`
        # to allow configuring retryable error codes.
        retry=gapic_v1.method_async.DEFAULT,
        timeout: Optional[float] = None,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListOperationsAsyncPager:
        r"""Lists operations that match the specified filter in the request.
        If the server doesn't support this method, it returns
        ``UNIMPLEMENTED``.

        NOTE: the ``name`` binding allows API services to override the
        binding to use different resource name schemes, such as
        ``users/*/operations``. To override the binding, API services
        can add a binding such as ``"/v1/{name=users/*}/operations"`` to
        their service configuration. For backwards compatibility, the
        default name includes the operations collection id, however
        overriding users must ensure the name binding is the parent
        resource, without the operations collection id.

        Args:
            name (str):
                The name of the operation's parent
                resource.
            filter_ (str):
                The standard list filter.
                This corresponds to the ``filter`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.api_core.operations_v1.pagers.ListOperationsPager:
                The response message for
                [Operations.ListOperations][google.api_core.operations_v1.Operations.ListOperations].

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create a protobuf request object.
        request = operations_pb2.ListOperationsRequest(name=name, filter=filter_)
        if page_size is not None:
            request.page_size = page_size
        if page_token is not None:
            request.page_token = page_token

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.list_operations]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata or ()) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__iter__` convenience method.
        response = pagers.ListOperationsAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def delete_operation(
        self,
        name: str,
        *,
        # TODO(https://github.com/googleapis/python-api-core/issues/722): Leverage `retry`
        # to allow configuring retryable error codes.
        retry=gapic_v1.method_async.DEFAULT,
        timeout: Optional[float] = None,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes a long-running operation. This method indicates that the
        client is no longer interested in the operation result. It does
        not cancel the operation. If the server doesn't support this
        method, it returns ``google.rpc.Code.UNIMPLEMENTED``.

        Args:
            name (str):
                The name of the operation resource to
                be deleted.

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        # Create the request object.
        request = operations_pb2.DeleteOperationRequest(name=name)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.delete_operation]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata or ()) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Send the request.
        await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    async def cancel_operation(
        self,
        name: Optional[str] = None,
        *,
        # TODO(https://github.com/googleapis/python-api-core/issues/722): Leverage `retry`
        # to allow configuring retryable error codes.
        retry=gapic_v1.method_async.DEFAULT,
        timeout: Optional[float] = None,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Starts asynchronous cancellation on a long-running operation.
        The server makes a best effort to cancel the operation, but
        success is not guaranteed. If the server doesn't support this
        method, it returns ``google.rpc.Code.UNIMPLEMENTED``. Clients
        can use
        [Operations.GetOperation][google.api_core.operations_v1.Operations.GetOperation]
        or other methods to check whether the cancellation succeeded or
        whether the operation completed despite cancellation. On
        successful cancellation, the operation is not deleted; instead,
        it becomes an operation with an
        [Operation.error][google.api_core.operations_v1.Operation.error] value with
        a [google.rpc.Status.code][google.rpc.Status.code] of 1,
        corresponding to ``Code.CANCELLED``.

        Args:
            name (str):
                The name of the operation resource to
                be cancelled.

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        # Create the request object.
        request = operations_pb2.CancelOperationRequest(name=name)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.cancel_operation]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata or ()) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Send the request.
        await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

# === NexusCore/openenv\Lib\site-packages\grpc\beta\implementations.py ===
# Copyright 2015-2016 gRPC authors.
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
"""Entry points into the Beta API of gRPC Python."""

# threading is referenced from specification in this module.
import threading  # pylint: disable=unused-import

# interfaces, cardinality, and face are referenced from specification in this
# module.
import grpc
from grpc import _auth
from grpc.beta import _client_adaptations
from grpc.beta import _metadata
from grpc.beta import _server_adaptations
from grpc.beta import interfaces  # pylint: disable=unused-import
from grpc.framework.common import cardinality  # pylint: disable=unused-import
from grpc.framework.interfaces.face import face  # pylint: disable=unused-import

# pylint: disable=too-many-arguments

ChannelCredentials = grpc.ChannelCredentials
ssl_channel_credentials = grpc.ssl_channel_credentials
CallCredentials = grpc.CallCredentials


def metadata_call_credentials(metadata_plugin, name=None):
    def plugin(context, callback):
        def wrapped_callback(beta_metadata, error):
            callback(_metadata.unbeta(beta_metadata), error)

        metadata_plugin(context, wrapped_callback)

    return grpc.metadata_call_credentials(plugin, name=name)


def google_call_credentials(credentials):
    """Construct CallCredentials from GoogleCredentials.

    Args:
      credentials: A GoogleCredentials object from the oauth2client library.

    Returns:
      A CallCredentials object for use in a GRPCCallOptions object.
    """
    return metadata_call_credentials(_auth.GoogleCallCredentials(credentials))


access_token_call_credentials = grpc.access_token_call_credentials
composite_call_credentials = grpc.composite_call_credentials
composite_channel_credentials = grpc.composite_channel_credentials


class Channel(object):
    """A channel to a remote host through which RPCs may be conducted.

    Only the "subscribe" and "unsubscribe" methods are supported for application
    use. This class' instance constructor and all other attributes are
    unsupported.
    """

    def __init__(self, channel):
        self._channel = channel

    def subscribe(self, callback, try_to_connect=None):
        """Subscribes to this Channel's connectivity.

        Args:
          callback: A callable to be invoked and passed an
            interfaces.ChannelConnectivity identifying this Channel's connectivity.
            The callable will be invoked immediately upon subscription and again for
            every change to this Channel's connectivity thereafter until it is
            unsubscribed.
          try_to_connect: A boolean indicating whether or not this Channel should
            attempt to connect if it is not already connected and ready to conduct
            RPCs.
        """
        self._channel.subscribe(callback, try_to_connect=try_to_connect)

    def unsubscribe(self, callback):
        """Unsubscribes a callback from this Channel's connectivity.

        Args:
          callback: A callable previously registered with this Channel from having
            been passed to its "subscribe" method.
        """
        self._channel.unsubscribe(callback)


def insecure_channel(host, port):
    """Creates an insecure Channel to a remote host.

    Args:
      host: The name of the remote host to which to connect.
      port: The port of the remote host to which to connect.
        If None only the 'host' part will be used.

    Returns:
      A Channel to the remote host through which RPCs may be conducted.
    """
    channel = grpc.insecure_channel(
        host if port is None else "%s:%d" % (host, port)
    )
    return Channel(channel)


def secure_channel(host, port, channel_credentials):
    """Creates a secure Channel to a remote host.

    Args:
      host: The name of the remote host to which to connect.
      port: The port of the remote host to which to connect.
        If None only the 'host' part will be used.
      channel_credentials: A ChannelCredentials.

    Returns:
      A secure Channel to the remote host through which RPCs may be conducted.
    """
    channel = grpc.secure_channel(
        host if port is None else "%s:%d" % (host, port), channel_credentials
    )
    return Channel(channel)


class StubOptions(object):
    """A value encapsulating the various options for creation of a Stub.

    This class and its instances have no supported interface - it exists to define
    the type of its instances and its instances exist to be passed to other
    functions.
    """

    def __init__(
        self,
        host,
        request_serializers,
        response_deserializers,
        metadata_transformer,
        thread_pool,
        thread_pool_size,
    ):
        self.host = host
        self.request_serializers = request_serializers
        self.response_deserializers = response_deserializers
        self.metadata_transformer = metadata_transformer
        self.thread_pool = thread_pool
        self.thread_pool_size = thread_pool_size


_EMPTY_STUB_OPTIONS = StubOptions(None, None, None, None, None, None)


def stub_options(
    host=None,
    request_serializers=None,
    response_deserializers=None,
    metadata_transformer=None,
    thread_pool=None,
    thread_pool_size=None,
):
    """Creates a StubOptions value to be passed at stub creation.

    All parameters are optional and should always be passed by keyword.

    Args:
      host: A host string to set on RPC calls.
      request_serializers: A dictionary from service name-method name pair to
        request serialization behavior.
      response_deserializers: A dictionary from service name-method name pair to
        response deserialization behavior.
      metadata_transformer: A callable that given a metadata object produces
        another metadata object to be used in the underlying communication on the
        wire.
      thread_pool: A thread pool to use in stubs.
      thread_pool_size: The size of thread pool to create for use in stubs;
        ignored if thread_pool has been passed.

    Returns:
      A StubOptions value created from the passed parameters.
    """
    return StubOptions(
        host,
        request_serializers,
        response_deserializers,
        metadata_transformer,
        thread_pool,
        thread_pool_size,
    )


def generic_stub(channel, options=None):
    """Creates a face.GenericStub on which RPCs can be made.

    Args:
      channel: A Channel for use by the created stub.
      options: A StubOptions customizing the created stub.

    Returns:
      A face.GenericStub on which RPCs can be made.
    """
    effective_options = _EMPTY_STUB_OPTIONS if options is None else options
    return _client_adaptations.generic_stub(
        channel._channel,  # pylint: disable=protected-access
        effective_options.host,
        effective_options.metadata_transformer,
        effective_options.request_serializers,
        effective_options.response_deserializers,
    )


def dynamic_stub(channel, service, cardinalities, options=None):
    """Creates a face.DynamicStub with which RPCs can be invoked.

    Args:
      channel: A Channel for the returned face.DynamicStub to use.
      service: The package-qualified full name of the service.
      cardinalities: A dictionary from RPC method name to cardinality.Cardinality
        value identifying the cardinality of the RPC method.
      options: An optional StubOptions value further customizing the functionality
        of the returned face.DynamicStub.

    Returns:
      A face.DynamicStub with which RPCs can be invoked.
    """
    effective_options = _EMPTY_STUB_OPTIONS if options is None else options
    return _client_adaptations.dynamic_stub(
        channel._channel,  # pylint: disable=protected-access
        service,
        cardinalities,
        effective_options.host,
        effective_options.metadata_transformer,
        effective_options.request_serializers,
        effective_options.response_deserializers,
    )


ServerCredentials = grpc.ServerCredentials
ssl_server_credentials = grpc.ssl_server_credentials


class ServerOptions(object):
    """A value encapsulating the various options for creation of a Server.

    This class and its instances have no supported interface - it exists to define
    the type of its instances and its instances exist to be passed to other
    functions.
    """

    def __init__(
        self,
        multi_method_implementation,
        request_deserializers,
        response_serializers,
        thread_pool,
        thread_pool_size,
        default_timeout,
        maximum_timeout,
    ):
        self.multi_method_implementation = multi_method_implementation
        self.request_deserializers = request_deserializers
        self.response_serializers = response_serializers
        self.thread_pool = thread_pool
        self.thread_pool_size = thread_pool_size
        self.default_timeout = default_timeout
        self.maximum_timeout = maximum_timeout


_EMPTY_SERVER_OPTIONS = ServerOptions(None, None, None, None, None, None, None)


def server_options(
    multi_method_implementation=None,
    request_deserializers=None,
    response_serializers=None,
    thread_pool=None,
    thread_pool_size=None,
    default_timeout=None,
    maximum_timeout=None,
):
    """Creates a ServerOptions value to be passed at server creation.

    All parameters are optional and should always be passed by keyword.

    Args:
      multi_method_implementation: A face.MultiMethodImplementation to be called
        to service an RPC if the server has no specific method implementation for
        the name of the RPC for which service was requested.
      request_deserializers: A dictionary from service name-method name pair to
        request deserialization behavior.
      response_serializers: A dictionary from service name-method name pair to
        response serialization behavior.
      thread_pool: A thread pool to use in stubs.
      thread_pool_size: The size of thread pool to create for use in stubs;
        ignored if thread_pool has been passed.
      default_timeout: A duration in seconds to allow for RPC service when
        servicing RPCs that did not include a timeout value when invoked.
      maximum_timeout: A duration in seconds to allow for RPC service when
        servicing RPCs no matter what timeout value was passed when the RPC was
        invoked.

    Returns:
      A StubOptions value created from the passed parameters.
    """
    return ServerOptions(
        multi_method_implementation,
        request_deserializers,
        response_serializers,
        thread_pool,
        thread_pool_size,
        default_timeout,
        maximum_timeout,
    )


def server(service_implementations, options=None):
    """Creates an interfaces.Server with which RPCs can be serviced.

    Args:
      service_implementations: A dictionary from service name-method name pair to
        face.MethodImplementation.
      options: An optional ServerOptions value further customizing the
        functionality of the returned Server.

    Returns:
      An interfaces.Server with which RPCs can be serviced.
    """
    effective_options = _EMPTY_SERVER_OPTIONS if options is None else options
    return _server_adaptations.server(
        service_implementations,
        effective_options.multi_method_implementation,
        effective_options.request_deserializers,
        effective_options.response_serializers,
        effective_options.thread_pool,
        effective_options.thread_pool_size,
    )

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_generated\types\chat_completion.py ===
# Inference code generated from the JSON schema spec in @huggingface/tasks.
#
# See:
#   - script: https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-codegen.ts
#   - specs:  https://github.com/huggingface/huggingface.js/tree/main/packages/tasks/src/tasks.
from typing import Any, Dict, List, Literal, Optional, Union

from .base import BaseInferenceType, dataclass_with_extra


@dataclass_with_extra
class ChatCompletionInputURL(BaseInferenceType):
    url: str


ChatCompletionInputMessageChunkType = Literal["text", "image_url"]


@dataclass_with_extra
class ChatCompletionInputMessageChunk(BaseInferenceType):
    type: "ChatCompletionInputMessageChunkType"
    image_url: Optional[ChatCompletionInputURL] = None
    text: Optional[str] = None


@dataclass_with_extra
class ChatCompletionInputFunctionDefinition(BaseInferenceType):
    name: str
    parameters: Any
    description: Optional[str] = None


@dataclass_with_extra
class ChatCompletionInputToolCall(BaseInferenceType):
    function: ChatCompletionInputFunctionDefinition
    id: str
    type: str


@dataclass_with_extra
class ChatCompletionInputMessage(BaseInferenceType):
    role: str
    content: Optional[Union[List[ChatCompletionInputMessageChunk], str]] = None
    name: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionInputToolCall]] = None


@dataclass_with_extra
class ChatCompletionInputJSONSchema(BaseInferenceType):
    name: str
    """
    The name of the response format.
    """
    description: Optional[str] = None
    """
    A description of what the response format is for, used by the model to determine
    how to respond in the format.
    """
    schema: Optional[Dict[str, object]] = None
    """
    The schema for the response format, described as a JSON Schema object. Learn how
    to build JSON schemas [here](https://json-schema.org/).
    """
    strict: Optional[bool] = None
    """
    Whether to enable strict schema adherence when generating the output. If set to
    true, the model will always follow the exact schema defined in the `schema`
    field.
    """


@dataclass_with_extra
class ChatCompletionInputResponseFormatText(BaseInferenceType):
    type: Literal["text"]


@dataclass_with_extra
class ChatCompletionInputResponseFormatJSONSchema(BaseInferenceType):
    type: Literal["json_schema"]
    json_schema: ChatCompletionInputJSONSchema


@dataclass_with_extra
class ChatCompletionInputResponseFormatJSONObject(BaseInferenceType):
    type: Literal["json_object"]


ChatCompletionInputGrammarType = Union[
    ChatCompletionInputResponseFormatText,
    ChatCompletionInputResponseFormatJSONSchema,
    ChatCompletionInputResponseFormatJSONObject,
]


@dataclass_with_extra
class ChatCompletionInputStreamOptions(BaseInferenceType):
    include_usage: Optional[bool] = None
    """If set, an additional chunk will be streamed before the data: [DONE] message. The usage
    field on this chunk shows the token usage statistics for the entire request, and the
    choices field will always be an empty array. All other chunks will also include a usage
    field, but with a null value.
    """


@dataclass_with_extra
class ChatCompletionInputFunctionName(BaseInferenceType):
    name: str


@dataclass_with_extra
class ChatCompletionInputToolChoiceClass(BaseInferenceType):
    function: ChatCompletionInputFunctionName


ChatCompletionInputToolChoiceEnum = Literal["auto", "none", "required"]


@dataclass_with_extra
class ChatCompletionInputTool(BaseInferenceType):
    function: ChatCompletionInputFunctionDefinition
    type: str


@dataclass_with_extra
class ChatCompletionInput(BaseInferenceType):
    """Chat Completion Input.
    Auto-generated from TGI specs.
    For more details, check out
    https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-tgi-import.ts.
    """

    messages: List[ChatCompletionInputMessage]
    """A list of messages comprising the conversation so far."""
    frequency_penalty: Optional[float] = None
    """Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing
    frequency in the text so far,
    decreasing the model's likelihood to repeat the same line verbatim.
    """
    logit_bias: Optional[List[float]] = None
    """UNUSED
    Modify the likelihood of specified tokens appearing in the completion. Accepts a JSON
    object that maps tokens
    (specified by their token ID in the tokenizer) to an associated bias value from -100 to
    100. Mathematically,
    the bias is added to the logits generated by the model prior to sampling. The exact
    effect will vary per model,
    but values between -1 and 1 should decrease or increase likelihood of selection; values
    like -100 or 100 should
    result in a ban or exclusive selection of the relevant token.
    """
    logprobs: Optional[bool] = None
    """Whether to return log probabilities of the output tokens or not. If true, returns the log
    probabilities of each
    output token returned in the content of message.
    """
    max_tokens: Optional[int] = None
    """The maximum number of tokens that can be generated in the chat completion."""
    model: Optional[str] = None
    """[UNUSED] ID of the model to use. See the model endpoint compatibility table for details
    on which models work with the Chat API.
    """
    n: Optional[int] = None
    """UNUSED
    How many chat completion choices to generate for each input message. Note that you will
    be charged based on the
    number of generated tokens across all of the choices. Keep n as 1 to minimize costs.
    """
    presence_penalty: Optional[float] = None
    """Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they
    appear in the text so far,
    increasing the model's likelihood to talk about new topics
    """
    response_format: Optional[ChatCompletionInputGrammarType] = None
    seed: Optional[int] = None
    stop: Optional[List[str]] = None
    """Up to 4 sequences where the API will stop generating further tokens."""
    stream: Optional[bool] = None
    stream_options: Optional[ChatCompletionInputStreamOptions] = None
    temperature: Optional[float] = None
    """What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the
    output more random, while
    lower values like 0.2 will make it more focused and deterministic.
    We generally recommend altering this or `top_p` but not both.
    """
    tool_choice: Optional[Union[ChatCompletionInputToolChoiceClass, "ChatCompletionInputToolChoiceEnum"]] = None
    tool_prompt: Optional[str] = None
    """A prompt to be appended before the tools"""
    tools: Optional[List[ChatCompletionInputTool]] = None
    """A list of tools the model may call. Currently, only functions are supported as a tool.
    Use this to provide a list of
    functions the model may generate JSON inputs for.
    """
    top_logprobs: Optional[int] = None
    """An integer between 0 and 5 specifying the number of most likely tokens to return at each
    token position, each with
    an associated log probability. logprobs must be set to true if this parameter is used.
    """
    top_p: Optional[float] = None
    """An alternative to sampling with temperature, called nucleus sampling, where the model
    considers the results of the
    tokens with top_p probability mass. So 0.1 means only the tokens comprising the top 10%
    probability mass are considered.
    """


@dataclass_with_extra
class ChatCompletionOutputTopLogprob(BaseInferenceType):
    logprob: float
    token: str


@dataclass_with_extra
class ChatCompletionOutputLogprob(BaseInferenceType):
    logprob: float
    token: str
    top_logprobs: List[ChatCompletionOutputTopLogprob]


@dataclass_with_extra
class ChatCompletionOutputLogprobs(BaseInferenceType):
    content: List[ChatCompletionOutputLogprob]


@dataclass_with_extra
class ChatCompletionOutputFunctionDefinition(BaseInferenceType):
    arguments: str
    name: str
    description: Optional[str] = None


@dataclass_with_extra
class ChatCompletionOutputToolCall(BaseInferenceType):
    function: ChatCompletionOutputFunctionDefinition
    id: str
    type: str


@dataclass_with_extra
class ChatCompletionOutputMessage(BaseInferenceType):
    role: str
    content: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionOutputToolCall]] = None


@dataclass_with_extra
class ChatCompletionOutputComplete(BaseInferenceType):
    finish_reason: str
    index: int
    message: ChatCompletionOutputMessage
    logprobs: Optional[ChatCompletionOutputLogprobs] = None


@dataclass_with_extra
class ChatCompletionOutputUsage(BaseInferenceType):
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int


@dataclass_with_extra
class ChatCompletionOutput(BaseInferenceType):
    """Chat Completion Output.
    Auto-generated from TGI specs.
    For more details, check out
    https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-tgi-import.ts.
    """

    choices: List[ChatCompletionOutputComplete]
    created: int
    id: str
    model: str
    system_fingerprint: str
    usage: ChatCompletionOutputUsage


@dataclass_with_extra
class ChatCompletionStreamOutputFunction(BaseInferenceType):
    arguments: str
    name: Optional[str] = None


@dataclass_with_extra
class ChatCompletionStreamOutputDeltaToolCall(BaseInferenceType):
    function: ChatCompletionStreamOutputFunction
    id: str
    index: int
    type: str


@dataclass_with_extra
class ChatCompletionStreamOutputDelta(BaseInferenceType):
    role: str
    content: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionStreamOutputDeltaToolCall]] = None


@dataclass_with_extra
class ChatCompletionStreamOutputTopLogprob(BaseInferenceType):
    logprob: float
    token: str


@dataclass_with_extra
class ChatCompletionStreamOutputLogprob(BaseInferenceType):
    logprob: float
    token: str
    top_logprobs: List[ChatCompletionStreamOutputTopLogprob]


@dataclass_with_extra
class ChatCompletionStreamOutputLogprobs(BaseInferenceType):
    content: List[ChatCompletionStreamOutputLogprob]


@dataclass_with_extra
class ChatCompletionStreamOutputChoice(BaseInferenceType):
    delta: ChatCompletionStreamOutputDelta
    index: int
    finish_reason: Optional[str] = None
    logprobs: Optional[ChatCompletionStreamOutputLogprobs] = None


@dataclass_with_extra
class ChatCompletionStreamOutputUsage(BaseInferenceType):
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int


@dataclass_with_extra
class ChatCompletionStreamOutput(BaseInferenceType):
    """Chat Completion Stream Output.
    Auto-generated from TGI specs.
    For more details, check out
    https://github.com/huggingface/huggingface.js/blob/main/packages/tasks/scripts/inference-tgi-import.ts.
    """

    choices: List[ChatCompletionStreamOutputChoice]
    created: int
    id: str
    model: str
    system_fingerprint: str
    usage: Optional[ChatCompletionStreamOutputUsage] = None

# === NexusCore/openenv\Lib\site-packages\litellm\llms\triton\completion\transformation.py ===
"""
Translates from OpenAI's `/v1/chat/completions` endpoint to Triton's `/generate` endpoint.
"""

import json
from typing import Any, AsyncIterator, Dict, Iterator, List, Literal, Optional, Union

from httpx import Headers, Response

from litellm.constants import DEFAULT_MAX_TOKENS_FOR_TRITON
from litellm.litellm_core_utils.prompt_templates.factory import prompt_factory
from litellm.llms.base_llm.base_model_iterator import BaseModelResponseIterator
from litellm.llms.base_llm.chat.transformation import (
    BaseConfig,
    BaseLLMException,
    LiteLLMLoggingObj,
)
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import (
    ChatCompletionToolCallChunk,
    ChatCompletionUsageBlock,
    Choices,
    GenericStreamingChunk,
    Message,
    ModelResponse,
)

from ..common_utils import TritonError


class TritonConfig(BaseConfig):
    """
    Base class for Triton configurations.

    Handles routing between /infer and /generate triton completion llms
    """

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[Dict, Headers]
    ) -> BaseLLMException:
        return TritonError(
            status_code=status_code, message=error_message, headers=headers
        )

    def validate_environment(
        self,
        headers: Dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> Dict:
        return {"Content-Type": "application/json"}

    def get_supported_openai_params(self, model: str) -> List:
        return ["max_tokens", "max_completion_tokens"]

    def map_openai_params(
        self,
        non_default_params: Dict,
        optional_params: Dict,
        model: str,
        drop_params: bool,
    ) -> Dict:
        for param, value in non_default_params.items():
            if param == "max_tokens" or param == "max_completion_tokens":
                optional_params[param] = value
        return optional_params

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        if api_base is None:
            raise ValueError("api_base is required")
        llm_type = self._get_triton_llm_type(api_base)
        if llm_type == "generate" and stream:
            return api_base + "_stream"
        return api_base

    def transform_response(
        self,
        model: str,
        raw_response: Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: Dict,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: Dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        api_base = litellm_params.get("api_base", "")
        llm_type = self._get_triton_llm_type(api_base)
        if llm_type == "generate":
            return TritonGenerateConfig().transform_response(
                model=model,
                raw_response=raw_response,
                model_response=model_response,
                logging_obj=logging_obj,
                request_data=request_data,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
                encoding=encoding,
                api_key=api_key,
                json_mode=json_mode,
            )
        elif llm_type == "infer":
            return TritonInferConfig().transform_response(
                model=model,
                raw_response=raw_response,
                model_response=model_response,
                logging_obj=logging_obj,
                request_data=request_data,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
                encoding=encoding,
                api_key=api_key,
                json_mode=json_mode,
            )
        return model_response

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        api_base = litellm_params.get("api_base", "")
        llm_type = self._get_triton_llm_type(api_base)
        if llm_type == "generate":
            return TritonGenerateConfig().transform_request(
                model=model,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
                headers=headers,
            )
        elif llm_type == "infer":
            return TritonInferConfig().transform_request(
                model=model,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
                headers=headers,
            )
        return {}

    def _get_triton_llm_type(self, api_base: str) -> Literal["generate", "infer"]:
        if api_base.endswith("/generate"):
            return "generate"
        elif api_base.endswith("/infer"):
            return "infer"
        else:
            raise ValueError(f"Invalid Triton API base: {api_base}")

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ) -> Any:
        return TritonResponseIterator(
            streaming_response=streaming_response,
            sync_stream=sync_stream,
            json_mode=json_mode,
        )


class TritonGenerateConfig(TritonConfig):
    """
    Transformations for triton /generate endpoint (This is a trtllm model)
    """

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        inference_params = optional_params.copy()
        stream = inference_params.pop("stream", False)
        data_for_triton: Dict[str, Any] = {
            "text_input": prompt_factory(model=model, messages=messages),
            "parameters": {
                "max_tokens": int(
                    optional_params.get("max_tokens", DEFAULT_MAX_TOKENS_FOR_TRITON)
                ),
            },
            "stream": bool(stream),
        }
        data_for_triton["parameters"].update(inference_params)
        return data_for_triton

    def transform_response(
        self,
        model: str,
        raw_response: Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: Dict,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: Dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        try:
            raw_response_json = raw_response.json()
        except Exception:
            raise TritonError(
                message=raw_response.text, status_code=raw_response.status_code
            )
        model_response.choices = [
            Choices(index=0, message=Message(content=raw_response_json["text_output"]))
        ]

        return model_response


class TritonInferConfig(TritonConfig):
    """
    Transformations for triton /infer endpoint (his is an infer model with a custom model on triton)
    """

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        text_input = messages[0].get("content", "")
        data_for_triton = {
            "inputs": [
                {
                    "name": "text_input",
                    "shape": [1],
                    "datatype": "BYTES",
                    "data": [text_input],
                }
            ]
        }

        for k, v in optional_params.items():
            if not (k == "stream" or k == "max_retries"):
                datatype = "INT32" if isinstance(v, int) else "BYTES"
                datatype = "FP32" if isinstance(v, float) else datatype
                data_for_triton["inputs"].append(
                    {"name": k, "shape": [1], "datatype": datatype, "data": [v]}
                )

        if "max_tokens" not in optional_params:
            data_for_triton["inputs"].append(
                {
                    "name": "max_tokens",
                    "shape": [1],
                    "datatype": "INT32",
                    "data": [20],
                }
            )
        return data_for_triton

    def transform_response(
        self,
        model: str,
        raw_response: Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: Dict,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: Dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        try:
            raw_response_json = raw_response.json()
        except Exception:
            raise TritonError(
                message=raw_response.text, status_code=raw_response.status_code
            )

        _triton_response_data = raw_response_json["outputs"][0]["data"]
        triton_response_data: Optional[str] = None
        if isinstance(_triton_response_data, list):
            triton_response_data = "".join(_triton_response_data)
        else:
            triton_response_data = _triton_response_data

        model_response.choices = [
            Choices(
                index=0,
                message=Message(content=triton_response_data),
            )
        ]

        return model_response


class TritonResponseIterator(BaseModelResponseIterator):
    def chunk_parser(self, chunk: dict) -> GenericStreamingChunk:
        try:
            text = ""
            tool_use: Optional[ChatCompletionToolCallChunk] = None
            is_finished = False
            finish_reason = ""
            usage: Optional[ChatCompletionUsageBlock] = None
            provider_specific_fields = None
            index = int(chunk.get("index", 0))

            # set values
            text = chunk.get("text_output", "")
            finish_reason = chunk.get("stop_reason", "")
            is_finished = chunk.get("is_finished", False)

            return GenericStreamingChunk(
                text=text,
                tool_use=tool_use,
                is_finished=is_finished,
                finish_reason=finish_reason,
                usage=usage,
                index=index,
                provider_specific_fields=provider_specific_fields,
            )
        except json.JSONDecodeError:
            raise ValueError(f"Failed to decode JSON from chunk: {chunk}")

# === NexusCore/openenv\Lib\site-packages\markdown_it\rules_block\list.py ===
# Lists
import logging

from ..common.utils import isStrSpace
from .state_block import StateBlock

LOGGER = logging.getLogger(__name__)


# Search `[-+*][\n ]`, returns next pos after marker on success
# or -1 on fail.
def skipBulletListMarker(state: StateBlock, startLine: int) -> int:
    pos = state.bMarks[startLine] + state.tShift[startLine]
    maximum = state.eMarks[startLine]

    try:
        marker = state.src[pos]
    except IndexError:
        return -1
    pos += 1

    if marker not in ("*", "-", "+"):
        return -1

    if pos < maximum:
        ch = state.src[pos]

        if not isStrSpace(ch):
            # " -test " - is not a list item
            return -1

    return pos


# Search `\d+[.)][\n ]`, returns next pos after marker on success
# or -1 on fail.
def skipOrderedListMarker(state: StateBlock, startLine: int) -> int:
    start = state.bMarks[startLine] + state.tShift[startLine]
    pos = start
    maximum = state.eMarks[startLine]

    # List marker should have at least 2 chars (digit + dot)
    if pos + 1 >= maximum:
        return -1

    ch = state.src[pos]
    pos += 1

    ch_ord = ord(ch)
    # /* 0 */  /* 9 */
    if ch_ord < 0x30 or ch_ord > 0x39:
        return -1

    while True:
        # EOL -> fail
        if pos >= maximum:
            return -1

        ch = state.src[pos]
        pos += 1

        # /* 0 */  /* 9 */
        ch_ord = ord(ch)
        if ch_ord >= 0x30 and ch_ord <= 0x39:
            # List marker should have no more than 9 digits
            # (prevents integer overflow in browsers)
            if pos - start >= 10:
                return -1

            continue

        # found valid marker
        if ch in (")", "."):
            break

        return -1

    if pos < maximum:
        ch = state.src[pos]

        if not isStrSpace(ch):
            # " 1.test " - is not a list item
            return -1

    return pos


def markTightParagraphs(state: StateBlock, idx: int) -> None:
    level = state.level + 2

    i = idx + 2
    length = len(state.tokens) - 2
    while i < length:
        if state.tokens[i].level == level and state.tokens[i].type == "paragraph_open":
            state.tokens[i + 2].hidden = True
            state.tokens[i].hidden = True
            i += 2
        i += 1


def list_block(state: StateBlock, startLine: int, endLine: int, silent: bool) -> bool:
    LOGGER.debug("entering list: %s, %s, %s, %s", state, startLine, endLine, silent)

    isTerminatingParagraph = False
    tight = True

    if state.is_code_block(startLine):
        return False

    # Special case:
    #  - item 1
    #   - item 2
    #    - item 3
    #     - item 4
    #      - this one is a paragraph continuation
    if (
        state.listIndent >= 0
        and state.sCount[startLine] - state.listIndent >= 4
        and state.sCount[startLine] < state.blkIndent
    ):
        return False

    # limit conditions when list can interrupt
    # a paragraph (validation mode only)
    # Next list item should still terminate previous list item
    #
    # This code can fail if plugins use blkIndent as well as lists,
    # but I hope the spec gets fixed long before that happens.
    #
    if (
        silent
        and state.parentType == "paragraph"
        and state.sCount[startLine] >= state.blkIndent
    ):
        isTerminatingParagraph = True

    # Detect list type and position after marker
    posAfterMarker = skipOrderedListMarker(state, startLine)
    if posAfterMarker >= 0:
        isOrdered = True
        start = state.bMarks[startLine] + state.tShift[startLine]
        markerValue = int(state.src[start : posAfterMarker - 1])

        # If we're starting a new ordered list right after
        # a paragraph, it should start with 1.
        if isTerminatingParagraph and markerValue != 1:
            return False
    else:
        posAfterMarker = skipBulletListMarker(state, startLine)
        if posAfterMarker >= 0:
            isOrdered = False
        else:
            return False

    # If we're starting a new unordered list right after
    # a paragraph, first line should not be empty.
    if (
        isTerminatingParagraph
        and state.skipSpaces(posAfterMarker) >= state.eMarks[startLine]
    ):
        return False

    # We should terminate list on style change. Remember first one to compare.
    markerChar = state.src[posAfterMarker - 1]

    # For validation mode we can terminate immediately
    if silent:
        return True

    # Start list
    listTokIdx = len(state.tokens)

    if isOrdered:
        token = state.push("ordered_list_open", "ol", 1)
        if markerValue != 1:
            token.attrs = {"start": markerValue}

    else:
        token = state.push("bullet_list_open", "ul", 1)

    token.map = listLines = [startLine, 0]
    token.markup = markerChar

    #
    # Iterate list items
    #

    nextLine = startLine
    prevEmptyEnd = False
    terminatorRules = state.md.block.ruler.getRules("list")

    oldParentType = state.parentType
    state.parentType = "list"

    while nextLine < endLine:
        pos = posAfterMarker
        maximum = state.eMarks[nextLine]

        initial = offset = (
            state.sCount[nextLine]
            + posAfterMarker
            - (state.bMarks[startLine] + state.tShift[startLine])
        )

        while pos < maximum:
            ch = state.src[pos]

            if ch == "\t":
                offset += 4 - (offset + state.bsCount[nextLine]) % 4
            elif ch == " ":
                offset += 1
            else:
                break

            pos += 1

        contentStart = pos

        # trimming space in "-    \n  3" case, indent is 1 here
        indentAfterMarker = 1 if contentStart >= maximum else offset - initial

        # If we have more than 4 spaces, the indent is 1
        # (the rest is just indented code block)
        if indentAfterMarker > 4:
            indentAfterMarker = 1

        # "  -  test"
        #  ^^^^^ - calculating total length of this thing
        indent = initial + indentAfterMarker

        # Run subparser & write tokens
        token = state.push("list_item_open", "li", 1)
        token.markup = markerChar
        token.map = itemLines = [startLine, 0]
        if isOrdered:
            token.info = state.src[start : posAfterMarker - 1]

        # change current state, then restore it after parser subcall
        oldTight = state.tight
        oldTShift = state.tShift[startLine]
        oldSCount = state.sCount[startLine]

        #  - example list
        # ^ listIndent position will be here
        #   ^ blkIndent position will be here
        #
        oldListIndent = state.listIndent
        state.listIndent = state.blkIndent
        state.blkIndent = indent

        state.tight = True
        state.tShift[startLine] = contentStart - state.bMarks[startLine]
        state.sCount[startLine] = offset

        if contentStart >= maximum and state.isEmpty(startLine + 1):
            # workaround for this case
            # (list item is empty, list terminates before "foo"):
            # ~~~~~~~~
            #   -
            #
            #     foo
            # ~~~~~~~~
            state.line = min(state.line + 2, endLine)
        else:
            # NOTE in list.js this was:
            # state.md.block.tokenize(state, startLine, endLine, True)
            # but  tokeniz does not take the final parameter
            state.md.block.tokenize(state, startLine, endLine)

        # If any of list item is tight, mark list as tight
        if (not state.tight) or prevEmptyEnd:
            tight = False

        # Item become loose if finish with empty line,
        # but we should filter last element, because it means list finish
        prevEmptyEnd = (state.line - startLine) > 1 and state.isEmpty(state.line - 1)

        state.blkIndent = state.listIndent
        state.listIndent = oldListIndent
        state.tShift[startLine] = oldTShift
        state.sCount[startLine] = oldSCount
        state.tight = oldTight

        token = state.push("list_item_close", "li", -1)
        token.markup = markerChar

        nextLine = startLine = state.line
        itemLines[1] = nextLine

        if nextLine >= endLine:
            break

        contentStart = state.bMarks[startLine]

        #
        # Try to check if list is terminated or continued.
        #
        if state.sCount[nextLine] < state.blkIndent:
            break

        if state.is_code_block(startLine):
            break

        # fail if terminating block found
        terminate = False
        for terminatorRule in terminatorRules:
            if terminatorRule(state, nextLine, endLine, True):
                terminate = True
                break

        if terminate:
            break

        # fail if list has another type
        if isOrdered:
            posAfterMarker = skipOrderedListMarker(state, nextLine)
            if posAfterMarker < 0:
                break
            start = state.bMarks[nextLine] + state.tShift[nextLine]
        else:
            posAfterMarker = skipBulletListMarker(state, nextLine)
            if posAfterMarker < 0:
                break

        if markerChar != state.src[posAfterMarker - 1]:
            break

    # Finalize list
    if isOrdered:
        token = state.push("ordered_list_close", "ol", -1)
    else:
        token = state.push("bullet_list_close", "ul", -1)

    token.markup = markerChar

    listLines[1] = nextLine
    state.line = nextLine

    state.parentType = oldParentType

    # mark paragraphs tight if needed
    if tight:
        markTightParagraphs(state, listTokIdx)

    return True

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\markdown.py ===
from collections import namedtuple
from functools import partial, wraps

from nltk.corpus.reader.api import CategorizedCorpusReader
from nltk.corpus.reader.plaintext import PlaintextCorpusReader
from nltk.corpus.reader.util import concat, read_blankline_block
from nltk.tokenize import blankline_tokenize, sent_tokenize, word_tokenize


def comma_separated_string_args(func):
    """
    A decorator that allows a function to be called with
    a single string of comma-separated values which become
    individual function arguments.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        _args = list()
        for arg in args:
            if isinstance(arg, str):
                _args.append({part.strip() for part in arg.split(",")})
            elif isinstance(arg, list):
                _args.append(set(arg))
            else:
                _args.append(arg)
        for name, value in kwargs.items():
            if isinstance(value, str):
                kwargs[name] = {part.strip() for part in value.split(",")}
        return func(*_args, **kwargs)

    return wrapper


def read_parse_blankline_block(stream, parser):
    block = read_blankline_block(stream)
    if block:
        return [parser.render(block[0])]
    return block


class MarkdownBlock:
    def __init__(self, content):
        self.content = content
        self.truncate_at = 16

    def __repr__(self):
        return f"{self.__class__.__name__}(content={repr(str(self))})"

    def __str__(self):
        return (
            f"{self.content[:self.truncate_at]}"
            f"{'...' if len(self.content) > self.truncate_at else ''}"
        )

    @property
    def raw(self):
        return self.content

    @property
    def words(self):
        return word_tokenize(self.content)

    @property
    def sents(self):
        return [word_tokenize(sent) for sent in sent_tokenize(self.content)]

    @property
    def paras(self):
        return [
            [word_tokenize(sent) for sent in sent_tokenize(para)]
            for para in blankline_tokenize(self.content)
        ]


class CodeBlock(MarkdownBlock):
    def __init__(self, language, *args):
        self.language = language
        super().__init__(*args)

    @property
    def sents(self):
        return [word_tokenize(line) for line in self.content.splitlines()]

    @property
    def lines(self):
        return self.content.splitlines()

    @property
    def paras(self):
        return [
            [word_tokenize(line) for line in para.splitlines()]
            for para in blankline_tokenize(self.content)
        ]


class MarkdownSection(MarkdownBlock):
    def __init__(self, heading, level, *args):
        self.heading = heading
        self.level = level
        super().__init__(*args)


Image = namedtuple("Image", "label, src, title")
Link = namedtuple("Link", "label, href, title")
List = namedtuple("List", "is_ordered, items")


class MarkdownCorpusReader(PlaintextCorpusReader):
    def __init__(self, *args, parser=None, **kwargs):
        from markdown_it import MarkdownIt
        from mdit_plain.renderer import RendererPlain
        from mdit_py_plugins.front_matter import front_matter_plugin

        self.parser = parser
        if self.parser is None:
            self.parser = MarkdownIt("commonmark", renderer_cls=RendererPlain)
            self.parser.use(front_matter_plugin)

        kwargs.setdefault(
            "para_block_reader", partial(read_parse_blankline_block, parser=self.parser)
        )
        super().__init__(*args, **kwargs)

    # This override takes care of removing markup.
    def _read_word_block(self, stream):
        words = list()
        for para in self._para_block_reader(stream):
            words.extend(self._word_tokenizer.tokenize(para))
        return words


class CategorizedMarkdownCorpusReader(CategorizedCorpusReader, MarkdownCorpusReader):
    """
    A reader for markdown corpora whose documents are divided into
    categories based on their file identifiers.

    Based on nltk.corpus.reader.plaintext.CategorizedPlaintextCorpusReader:
    https://www.nltk.org/_modules/nltk/corpus/reader/api.html#CategorizedCorpusReader
    """

    def __init__(self, *args, cat_field="tags", **kwargs):
        """
        Initialize the corpus reader. Categorization arguments
        (``cat_pattern``, ``cat_map``, and ``cat_file``) are passed to
        the ``CategorizedCorpusReader`` constructor.  The remaining arguments
        are passed to the ``MarkdownCorpusReader`` constructor.
        """
        cat_args = ["cat_pattern", "cat_map", "cat_file"]
        if not any(arg in kwargs for arg in cat_args):
            # Initialize with a blank map now,
            # and try to build categories from document metadata later.
            kwargs["cat_map"] = dict()
        CategorizedCorpusReader.__init__(self, kwargs)
        MarkdownCorpusReader.__init__(self, *args, **kwargs)

        # Map file IDs to categories if self._map exists but is still empty:
        if self._map is not None and not self._map:
            for file_id in self._fileids:
                metadata = self.metadata(file_id)
                if metadata:
                    self._map[file_id] = metadata[0].get(cat_field, [])

    ### Begin CategorizedCorpusReader Overrides
    @comma_separated_string_args
    def categories(self, fileids=None):
        return super().categories(fileids)

    @comma_separated_string_args
    def fileids(self, categories=None):
        if categories is None:
            return self._fileids
        return super().fileids(categories)

    ### End CategorizedCorpusReader Overrides

    ### Begin MarkdownCorpusReader Overrides
    @comma_separated_string_args
    def raw(self, fileids=None, categories=None):
        return super().raw(self._resolve(fileids, categories))

    @comma_separated_string_args
    def words(self, fileids=None, categories=None):
        return super().words(self._resolve(fileids, categories))

    @comma_separated_string_args
    def sents(self, fileids=None, categories=None):
        return super().sents(self._resolve(fileids, categories))

    @comma_separated_string_args
    def paras(self, fileids=None, categories=None):
        return super().paras(self._resolve(fileids, categories))

    ### End MarkdownCorpusReader Overrides

    def concatenated_view(self, reader, fileids, categories):
        return concat(
            [
                self.CorpusView(path, reader, encoding=enc)
                for (path, enc) in self.abspaths(
                    self._resolve(fileids, categories), include_encoding=True
                )
            ]
        )

    def metadata_reader(self, stream):
        from yaml import safe_load

        return [
            safe_load(t.content)
            for t in self.parser.parse(stream.read())
            if t.type == "front_matter"
        ]

    @comma_separated_string_args
    def metadata(self, fileids=None, categories=None):
        return self.concatenated_view(self.metadata_reader, fileids, categories)

    def blockquote_reader(self, stream):
        tokens = self.parser.parse(stream.read())
        opening_tokens = filter(
            lambda t: t.level == 0 and t.type == "blockquote_open", tokens
        )
        closing_tokens = filter(
            lambda t: t.level == 0 and t.type == "blockquote_close", tokens
        )
        blockquotes = list()
        for o, c in zip(opening_tokens, closing_tokens):
            opening_index = tokens.index(o)
            closing_index = tokens.index(c, opening_index)
            blockquotes.append(tokens[opening_index : closing_index + 1])
        return [
            MarkdownBlock(
                self.parser.renderer.render(block, self.parser.options, env=None)
            )
            for block in blockquotes
        ]

    @comma_separated_string_args
    def blockquotes(self, fileids=None, categories=None):
        return self.concatenated_view(self.blockquote_reader, fileids, categories)

    def code_block_reader(self, stream):
        return [
            CodeBlock(
                t.info,
                t.content,
            )
            for t in self.parser.parse(stream.read())
            if t.level == 0 and t.type in ("fence", "code_block")
        ]

    @comma_separated_string_args
    def code_blocks(self, fileids=None, categories=None):
        return self.concatenated_view(self.code_block_reader, fileids, categories)

    def image_reader(self, stream):
        return [
            Image(
                child_token.content,
                child_token.attrGet("src"),
                child_token.attrGet("title"),
            )
            for inline_token in filter(
                lambda t: t.type == "inline", self.parser.parse(stream.read())
            )
            for child_token in inline_token.children
            if child_token.type == "image"
        ]

    @comma_separated_string_args
    def images(self, fileids=None, categories=None):
        return self.concatenated_view(self.image_reader, fileids, categories)

    def link_reader(self, stream):
        return [
            Link(
                inline_token.children[i + 1].content,
                child_token.attrGet("href"),
                child_token.attrGet("title"),
            )
            for inline_token in filter(
                lambda t: t.type == "inline", self.parser.parse(stream.read())
            )
            for i, child_token in enumerate(inline_token.children)
            if child_token.type == "link_open"
        ]

    @comma_separated_string_args
    def links(self, fileids=None, categories=None):
        return self.concatenated_view(self.link_reader, fileids, categories)

    def list_reader(self, stream):
        tokens = self.parser.parse(stream.read())
        opening_types = ("bullet_list_open", "ordered_list_open")
        opening_tokens = filter(
            lambda t: t.level == 0 and t.type in opening_types, tokens
        )
        closing_types = ("bullet_list_close", "ordered_list_close")
        closing_tokens = filter(
            lambda t: t.level == 0 and t.type in closing_types, tokens
        )
        list_blocks = list()
        for o, c in zip(opening_tokens, closing_tokens):
            opening_index = tokens.index(o)
            closing_index = tokens.index(c, opening_index)
            list_blocks.append(tokens[opening_index : closing_index + 1])
        return [
            List(
                tokens[0].type == "ordered_list_open",
                [t.content for t in tokens if t.content],
            )
            for tokens in list_blocks
        ]

    @comma_separated_string_args
    def lists(self, fileids=None, categories=None):
        return self.concatenated_view(self.list_reader, fileids, categories)

    def section_reader(self, stream):
        section_blocks, block = list(), list()
        for t in self.parser.parse(stream.read()):
            if t.level == 0 and t.type == "heading_open":
                if not block:
                    block.append(t)
                else:
                    section_blocks.append(block)
                    block = [t]
            elif block:
                block.append(t)
        if block:
            section_blocks.append(block)
        return [
            MarkdownSection(
                block[1].content,
                block[0].markup.count("#"),
                self.parser.renderer.render(block, self.parser.options, env=None),
            )
            for block in section_blocks
        ]

    @comma_separated_string_args
    def sections(self, fileids=None, categories=None):
        return self.concatenated_view(self.section_reader, fileids, categories)