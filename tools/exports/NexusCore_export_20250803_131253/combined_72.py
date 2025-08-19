
# === NexusCore/tools\exports\export_20250803_114325\combined_36.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pkg_resources\__init__.py ===
# TODO: Add Generic type annotations to initialized collections.
# For now we'd simply use implicit Any/Unknown which would add redundant annotations
# mypy: disable-error-code="var-annotated"
"""
Package resource API
--------------------

A resource is a logical file contained within a package, or a logical
subdirectory thereof.  The package resource API expects resource names
to have their path parts separated with ``/``, *not* whatever the local
path separator is.  Do not use os.path operations to manipulate resource
names being passed into the API.

The package resource API is designed to work with normal filesystem packages,
.egg files, and unpacked .egg files.  It can also work in a limited way with
.zip files and with custom PEP 302 loaders that support the ``get_data()``
method.

This module is deprecated. Users are directed to :mod:`importlib.resources`,
:mod:`importlib.metadata` and :pypi:`packaging` instead.
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 8):  # noqa: UP036 # Check for unsupported versions
    raise RuntimeError("Python 3.8 or later is required")

import os
import io
import time
import re
import types
from typing import (
    Any,
    Literal,
    Dict,
    Iterator,
    Mapping,
    MutableSequence,
    NamedTuple,
    NoReturn,
    Tuple,
    Union,
    TYPE_CHECKING,
    Protocol,
    Callable,
    Iterable,
    TypeVar,
    overload,
)
import zipfile
import zipimport
import warnings
import stat
import functools
import pkgutil
import operator
import platform
import collections
import plistlib
import email.parser
import errno
import tempfile
import textwrap
import inspect
import ntpath
import posixpath
import importlib
import importlib.abc
import importlib.machinery
from pkgutil import get_importer

import _imp

# capture these to bypass sandboxing
from os import utime
from os import open as os_open
from os.path import isdir, split

try:
    from os import mkdir, rename, unlink

    WRITE_SUPPORT = True
except ImportError:
    # no write support, probably under GAE
    WRITE_SUPPORT = False

from pip._internal.utils._jaraco_text import (
    yield_lines,
    drop_comment,
    join_continuation,
)
from pip._vendor.packaging import markers as _packaging_markers
from pip._vendor.packaging import requirements as _packaging_requirements
from pip._vendor.packaging import utils as _packaging_utils
from pip._vendor.packaging import version as _packaging_version
from pip._vendor.platformdirs import user_cache_dir as _user_cache_dir

if TYPE_CHECKING:
    from _typeshed import BytesPath, StrPath, StrOrBytesPath
    from pip._vendor.typing_extensions import Self


# Patch: Remove deprecation warning from vendored pkg_resources.
# Setting PYTHONWARNINGS=error to verify builds produce no warnings
# causes immediate exceptions.
# See https://github.com/pypa/pip/issues/12243


_T = TypeVar("_T")
_DistributionT = TypeVar("_DistributionT", bound="Distribution")
# Type aliases
_NestedStr = Union[str, Iterable[Union[str, Iterable["_NestedStr"]]]]
_InstallerTypeT = Callable[["Requirement"], "_DistributionT"]
_InstallerType = Callable[["Requirement"], Union["Distribution", None]]
_PkgReqType = Union[str, "Requirement"]
_EPDistType = Union["Distribution", _PkgReqType]
_MetadataType = Union["IResourceProvider", None]
_ResolvedEntryPoint = Any  # Can be any attribute in the module
_ResourceStream = Any  # TODO / Incomplete: A readable file-like object
# Any object works, but let's indicate we expect something like a module (optionally has __loader__ or __file__)
_ModuleLike = Union[object, types.ModuleType]
# Any: Should be _ModuleLike but we end up with issues where _ModuleLike doesn't have _ZipLoaderModule's __loader__
_ProviderFactoryType = Callable[[Any], "IResourceProvider"]
_DistFinderType = Callable[[_T, str, bool], Iterable["Distribution"]]
_NSHandlerType = Callable[[_T, str, str, types.ModuleType], Union[str, None]]
_AdapterT = TypeVar(
    "_AdapterT", _DistFinderType[Any], _ProviderFactoryType, _NSHandlerType[Any]
)


# Use _typeshed.importlib.LoaderProtocol once available https://github.com/python/typeshed/pull/11890
class _LoaderProtocol(Protocol):
    def load_module(self, fullname: str, /) -> types.ModuleType: ...


class _ZipLoaderModule(Protocol):
    __loader__: zipimport.zipimporter


_PEP440_FALLBACK = re.compile(r"^v?(?P<safe>(?:[0-9]+!)?[0-9]+(?:\.[0-9]+)*)", re.I)


class PEP440Warning(RuntimeWarning):
    """
    Used when there is an issue with a version or specifier not complying with
    PEP 440.
    """


parse_version = _packaging_version.Version


_state_vars: dict[str, str] = {}


def _declare_state(vartype: str, varname: str, initial_value: _T) -> _T:
    _state_vars[varname] = vartype
    return initial_value


def __getstate__() -> dict[str, Any]:
    state = {}
    g = globals()
    for k, v in _state_vars.items():
        state[k] = g['_sget_' + v](g[k])
    return state


def __setstate__(state: dict[str, Any]) -> dict[str, Any]:
    g = globals()
    for k, v in state.items():
        g['_sset_' + _state_vars[k]](k, g[k], v)
    return state


def _sget_dict(val):
    return val.copy()


def _sset_dict(key, ob, state):
    ob.clear()
    ob.update(state)


def _sget_object(val):
    return val.__getstate__()


def _sset_object(key, ob, state):
    ob.__setstate__(state)


_sget_none = _sset_none = lambda *args: None


def get_supported_platform():
    """Return this platform's maximum compatible version.

    distutils.util.get_platform() normally reports the minimum version
    of macOS that would be required to *use* extensions produced by
    distutils.  But what we want when checking compatibility is to know the
    version of macOS that we are *running*.  To allow usage of packages that
    explicitly require a newer version of macOS, we must also know the
    current version of the OS.

    If this condition occurs for any other platform with a version in its
    platform strings, this function should be extended accordingly.
    """
    plat = get_build_platform()
    m = macosVersionString.match(plat)
    if m is not None and sys.platform == "darwin":
        try:
            plat = 'macosx-%s-%s' % ('.'.join(_macos_vers()[:2]), m.group(3))
        except ValueError:
            # not macOS
            pass
    return plat


__all__ = [
    # Basic resource access and distribution/entry point discovery
    'require',
    'run_script',
    'get_provider',
    'get_distribution',
    'load_entry_point',
    'get_entry_map',
    'get_entry_info',
    'iter_entry_points',
    'resource_string',
    'resource_stream',
    'resource_filename',
    'resource_listdir',
    'resource_exists',
    'resource_isdir',
    # Environmental control
    'declare_namespace',
    'working_set',
    'add_activation_listener',
    'find_distributions',
    'set_extraction_path',
    'cleanup_resources',
    'get_default_cache',
    # Primary implementation classes
    'Environment',
    'WorkingSet',
    'ResourceManager',
    'Distribution',
    'Requirement',
    'EntryPoint',
    # Exceptions
    'ResolutionError',
    'VersionConflict',
    'DistributionNotFound',
    'UnknownExtra',
    'ExtractionError',
    # Warnings
    'PEP440Warning',
    # Parsing functions and string utilities
    'parse_requirements',
    'parse_version',
    'safe_name',
    'safe_version',
    'get_platform',
    'compatible_platforms',
    'yield_lines',
    'split_sections',
    'safe_extra',
    'to_filename',
    'invalid_marker',
    'evaluate_marker',
    # filesystem utilities
    'ensure_directory',
    'normalize_path',
    # Distribution "precedence" constants
    'EGG_DIST',
    'BINARY_DIST',
    'SOURCE_DIST',
    'CHECKOUT_DIST',
    'DEVELOP_DIST',
    # "Provider" interfaces, implementations, and registration/lookup APIs
    'IMetadataProvider',
    'IResourceProvider',
    'FileMetadata',
    'PathMetadata',
    'EggMetadata',
    'EmptyProvider',
    'empty_provider',
    'NullProvider',
    'EggProvider',
    'DefaultProvider',
    'ZipProvider',
    'register_finder',
    'register_namespace_handler',
    'register_loader_type',
    'fixup_namespace_packages',
    'get_importer',
    # Warnings
    'PkgResourcesDeprecationWarning',
    # Deprecated/backward compatibility only
    'run_main',
    'AvailableDistributions',
]


class ResolutionError(Exception):
    """Abstract base for dependency resolution errors"""

    def __repr__(self):
        return self.__class__.__name__ + repr(self.args)


class VersionConflict(ResolutionError):
    """
    An already-installed version conflicts with the requested version.

    Should be initialized with the installed Distribution and the requested
    Requirement.
    """

    _template = "{self.dist} is installed but {self.req} is required"

    @property
    def dist(self) -> Distribution:
        return self.args[0]

    @property
    def req(self) -> Requirement:
        return self.args[1]

    def report(self):
        return self._template.format(**locals())

    def with_context(self, required_by: set[Distribution | str]):
        """
        If required_by is non-empty, return a version of self that is a
        ContextualVersionConflict.
        """
        if not required_by:
            return self
        args = self.args + (required_by,)
        return ContextualVersionConflict(*args)


class ContextualVersionConflict(VersionConflict):
    """
    A VersionConflict that accepts a third parameter, the set of the
    requirements that required the installed Distribution.
    """

    _template = VersionConflict._template + ' by {self.required_by}'

    @property
    def required_by(self) -> set[str]:
        return self.args[2]


class DistributionNotFound(ResolutionError):
    """A requested distribution was not found"""

    _template = (
        "The '{self.req}' distribution was not found "
        "and is required by {self.requirers_str}"
    )

    @property
    def req(self) -> Requirement:
        return self.args[0]

    @property
    def requirers(self) -> set[str] | None:
        return self.args[1]

    @property
    def requirers_str(self):
        if not self.requirers:
            return 'the application'
        return ', '.join(self.requirers)

    def report(self):
        return self._template.format(**locals())

    def __str__(self):
        return self.report()


class UnknownExtra(ResolutionError):
    """Distribution doesn't have an "extra feature" of the given name"""


_provider_factories: dict[type[_ModuleLike], _ProviderFactoryType] = {}

PY_MAJOR = '{}.{}'.format(*sys.version_info)
EGG_DIST = 3
BINARY_DIST = 2
SOURCE_DIST = 1
CHECKOUT_DIST = 0
DEVELOP_DIST = -1


def register_loader_type(
    loader_type: type[_ModuleLike], provider_factory: _ProviderFactoryType
):
    """Register `provider_factory` to make providers for `loader_type`

    `loader_type` is the type or class of a PEP 302 ``module.__loader__``,
    and `provider_factory` is a function that, passed a *module* object,
    returns an ``IResourceProvider`` for that module.
    """
    _provider_factories[loader_type] = provider_factory


@overload
def get_provider(moduleOrReq: str) -> IResourceProvider: ...
@overload
def get_provider(moduleOrReq: Requirement) -> Distribution: ...
def get_provider(moduleOrReq: str | Requirement) -> IResourceProvider | Distribution:
    """Return an IResourceProvider for the named module or requirement"""
    if isinstance(moduleOrReq, Requirement):
        return working_set.find(moduleOrReq) or require(str(moduleOrReq))[0]
    try:
        module = sys.modules[moduleOrReq]
    except KeyError:
        __import__(moduleOrReq)
        module = sys.modules[moduleOrReq]
    loader = getattr(module, '__loader__', None)
    return _find_adapter(_provider_factories, loader)(module)


@functools.lru_cache(maxsize=None)
def _macos_vers():
    version = platform.mac_ver()[0]
    # fallback for MacPorts
    if version == '':
        plist = '/System/Library/CoreServices/SystemVersion.plist'
        if os.path.exists(plist):
            with open(plist, 'rb') as fh:
                plist_content = plistlib.load(fh)
            if 'ProductVersion' in plist_content:
                version = plist_content['ProductVersion']
    return version.split('.')


def _macos_arch(machine):
    return {'PowerPC': 'ppc', 'Power_Macintosh': 'ppc'}.get(machine, machine)


def get_build_platform():
    """Return this platform's string for platform-specific distributions

    XXX Currently this is the same as ``distutils.util.get_platform()``, but it
    needs some hacks for Linux and macOS.
    """
    from sysconfig import get_platform

    plat = get_platform()
    if sys.platform == "darwin" and not plat.startswith('macosx-'):
        try:
            version = _macos_vers()
            machine = os.uname()[4].replace(" ", "_")
            return "macosx-%d.%d-%s" % (
                int(version[0]),
                int(version[1]),
                _macos_arch(machine),
            )
        except ValueError:
            # if someone is running a non-Mac darwin system, this will fall
            # through to the default implementation
            pass
    return plat


macosVersionString = re.compile(r"macosx-(\d+)\.(\d+)-(.*)")
darwinVersionString = re.compile(r"darwin-(\d+)\.(\d+)\.(\d+)-(.*)")
# XXX backward compat
get_platform = get_build_platform


def compatible_platforms(provided: str | None, required: str | None):
    """Can code for the `provided` platform run on the `required` platform?

    Returns true if either platform is ``None``, or the platforms are equal.

    XXX Needs compatibility checks for Linux and other unixy OSes.
    """
    if provided is None or required is None or provided == required:
        # easy case
        return True

    # macOS special cases
    reqMac = macosVersionString.match(required)
    if reqMac:
        provMac = macosVersionString.match(provided)

        # is this a Mac package?
        if not provMac:
            # this is backwards compatibility for packages built before
            # setuptools 0.6. All packages built after this point will
            # use the new macOS designation.
            provDarwin = darwinVersionString.match(provided)
            if provDarwin:
                dversion = int(provDarwin.group(1))
                macosversion = "%s.%s" % (reqMac.group(1), reqMac.group(2))
                if (
                    dversion == 7
                    and macosversion >= "10.3"
                    or dversion == 8
                    and macosversion >= "10.4"
                ):
                    return True
            # egg isn't macOS or legacy darwin
            return False

        # are they the same major version and machine type?
        if provMac.group(1) != reqMac.group(1) or provMac.group(3) != reqMac.group(3):
            return False

        # is the required OS major update >= the provided one?
        if int(provMac.group(2)) > int(reqMac.group(2)):
            return False

        return True

    # XXX Linux and other platforms' special cases should go here
    return False


@overload
def get_distribution(dist: _DistributionT) -> _DistributionT: ...
@overload
def get_distribution(dist: _PkgReqType) -> Distribution: ...
def get_distribution(dist: Distribution | _PkgReqType) -> Distribution:
    """Return a current distribution object for a Requirement or string"""
    if isinstance(dist, str):
        dist = Requirement.parse(dist)
    if isinstance(dist, Requirement):
        # Bad type narrowing, dist has to be a Requirement here, so get_provider has to return Distribution
        dist = get_provider(dist)  # type: ignore[assignment]
    if not isinstance(dist, Distribution):
        raise TypeError("Expected str, Requirement, or Distribution", dist)
    return dist


def load_entry_point(dist: _EPDistType, group: str, name: str) -> _ResolvedEntryPoint:
    """Return `name` entry point of `group` for `dist` or raise ImportError"""
    return get_distribution(dist).load_entry_point(group, name)


@overload
def get_entry_map(
    dist: _EPDistType, group: None = None
) -> dict[str, dict[str, EntryPoint]]: ...
@overload
def get_entry_map(dist: _EPDistType, group: str) -> dict[str, EntryPoint]: ...
def get_entry_map(dist: _EPDistType, group: str | None = None):
    """Return the entry point map for `group`, or the full entry map"""
    return get_distribution(dist).get_entry_map(group)


def get_entry_info(dist: _EPDistType, group: str, name: str):
    """Return the EntryPoint object for `group`+`name`, or ``None``"""
    return get_distribution(dist).get_entry_info(group, name)


class IMetadataProvider(Protocol):
    def has_metadata(self, name: str) -> bool:
        """Does the package's distribution contain the named metadata?"""

    def get_metadata(self, name: str) -> str:
        """The named metadata resource as a string"""

    def get_metadata_lines(self, name: str) -> Iterator[str]:
        """Yield named metadata resource as list of non-blank non-comment lines

        Leading and trailing whitespace is stripped from each line, and lines
        with ``#`` as the first non-blank character are omitted."""

    def metadata_isdir(self, name: str) -> bool:
        """Is the named metadata a directory?  (like ``os.path.isdir()``)"""

    def metadata_listdir(self, name: str) -> list[str]:
        """List of metadata names in the directory (like ``os.listdir()``)"""

    def run_script(self, script_name: str, namespace: dict[str, Any]) -> None:
        """Execute the named script in the supplied namespace dictionary"""


class IResourceProvider(IMetadataProvider, Protocol):
    """An object that provides access to package resources"""

    def get_resource_filename(
        self, manager: ResourceManager, resource_name: str
    ) -> str:
        """Return a true filesystem path for `resource_name`

        `manager` must be a ``ResourceManager``"""

    def get_resource_stream(
        self, manager: ResourceManager, resource_name: str
    ) -> _ResourceStream:
        """Return a readable file-like object for `resource_name`

        `manager` must be a ``ResourceManager``"""

    def get_resource_string(
        self, manager: ResourceManager, resource_name: str
    ) -> bytes:
        """Return the contents of `resource_name` as :obj:`bytes`

        `manager` must be a ``ResourceManager``"""

    def has_resource(self, resource_name: str) -> bool:
        """Does the package contain the named resource?"""

    def resource_isdir(self, resource_name: str) -> bool:
        """Is the named resource a directory?  (like ``os.path.isdir()``)"""

    def resource_listdir(self, resource_name: str) -> list[str]:
        """List of resource names in the directory (like ``os.listdir()``)"""


class WorkingSet:
    """A collection of active distributions on sys.path (or a similar list)"""

    def __init__(self, entries: Iterable[str] | None = None):
        """Create working set from list of path entries (default=sys.path)"""
        self.entries: list[str] = []
        self.entry_keys = {}
        self.by_key = {}
        self.normalized_to_canonical_keys = {}
        self.callbacks = []

        if entries is None:
            entries = sys.path

        for entry in entries:
            self.add_entry(entry)

    @classmethod
    def _build_master(cls):
        """
        Prepare the master working set.
        """
        ws = cls()
        try:
            from __main__ import __requires__
        except ImportError:
            # The main program does not list any requirements
            return ws

        # ensure the requirements are met
        try:
            ws.require(__requires__)
        except VersionConflict:
            return cls._build_from_requirements(__requires__)

        return ws

    @classmethod
    def _build_from_requirements(cls, req_spec):
        """
        Build a working set from a requirement spec. Rewrites sys.path.
        """
        # try it without defaults already on sys.path
        # by starting with an empty path
        ws = cls([])
        reqs = parse_requirements(req_spec)
        dists = ws.resolve(reqs, Environment())
        for dist in dists:
            ws.add(dist)

        # add any missing entries from sys.path
        for entry in sys.path:
            if entry not in ws.entries:
                ws.add_entry(entry)

        # then copy back to sys.path
        sys.path[:] = ws.entries
        return ws

    def add_entry(self, entry: str):
        """Add a path item to ``.entries``, finding any distributions on it

        ``find_distributions(entry, True)`` is used to find distributions
        corresponding to the path entry, and they are added.  `entry` is
        always appended to ``.entries``, even if it is already present.
        (This is because ``sys.path`` can contain the same value more than
        once, and the ``.entries`` of the ``sys.path`` WorkingSet should always
        equal ``sys.path``.)
        """
        self.entry_keys.setdefault(entry, [])
        self.entries.append(entry)
        for dist in find_distributions(entry, True):
            self.add(dist, entry, False)

    def __contains__(self, dist: Distribution) -> bool:
        """True if `dist` is the active distribution for its project"""
        return self.by_key.get(dist.key) == dist

    def find(self, req: Requirement) -> Distribution | None:
        """Find a distribution matching requirement `req`

        If there is an active distribution for the requested project, this
        returns it as long as it meets the version requirement specified by
        `req`.  But, if there is an active distribution for the project and it
        does *not* meet the `req` requirement, ``VersionConflict`` is raised.
        If there is no active distribution for the requested project, ``None``
        is returned.
        """
        dist = self.by_key.get(req.key)

        if dist is None:
            canonical_key = self.normalized_to_canonical_keys.get(req.key)

            if canonical_key is not None:
                req.key = canonical_key
                dist = self.by_key.get(canonical_key)

        if dist is not None and dist not in req:
            # XXX add more info
            raise VersionConflict(dist, req)
        return dist

    def iter_entry_points(self, group: str, name: str | None = None):
        """Yield entry point objects from `group` matching `name`

        If `name` is None, yields all entry points in `group` from all
        distributions in the working set, otherwise only ones matching
        both `group` and `name` are yielded (in distribution order).
        """
        return (
            entry
            for dist in self
            for entry in dist.get_entry_map(group).values()
            if name is None or name == entry.name
        )

    def run_script(self, requires: str, script_name: str):
        """Locate distribution for `requires` and run `script_name` script"""
        ns = sys._getframe(1).f_globals
        name = ns['__name__']
        ns.clear()
        ns['__name__'] = name
        self.require(requires)[0].run_script(script_name, ns)

    def __iter__(self) -> Iterator[Distribution]:
        """Yield distributions for non-duplicate projects in the working set

        The yield order is the order in which the items' path entries were
        added to the working set.
        """
        seen = set()
        for item in self.entries:
            if item not in self.entry_keys:
                # workaround a cache issue
                continue

            for key in self.entry_keys[item]:
                if key not in seen:
                    seen.add(key)
                    yield self.by_key[key]

    def add(
        self,
        dist: Distribution,
        entry: str | None = None,
        insert: bool = True,
        replace: bool = False,
    ):
        """Add `dist` to working set, associated with `entry`

        If `entry` is unspecified, it defaults to the ``.location`` of `dist`.
        On exit from this routine, `entry` is added to the end of the working
        set's ``.entries`` (if it wasn't already present).

        `dist` is only added to the working set if it's for a project that
        doesn't already have a distribution in the set, unless `replace=True`.
        If it's added, any callbacks registered with the ``subscribe()`` method
        will be called.
        """
        if insert:
            dist.insert_on(self.entries, entry, replace=replace)

        if entry is None:
            entry = dist.location
        keys = self.entry_keys.setdefault(entry, [])
        keys2 = self.entry_keys.setdefault(dist.location, [])
        if not replace and dist.key in self.by_key:
            # ignore hidden distros
            return

        self.by_key[dist.key] = dist
        normalized_name = _packaging_utils.canonicalize_name(dist.key)
        self.normalized_to_canonical_keys[normalized_name] = dist.key
        if dist.key not in keys:
            keys.append(dist.key)
        if dist.key not in keys2:
            keys2.append(dist.key)
        self._added_new(dist)

    @overload
    def resolve(
        self,
        requirements: Iterable[Requirement],
        env: Environment | None,
        installer: _InstallerTypeT[_DistributionT],
        replace_conflicting: bool = False,
        extras: tuple[str, ...] | None = None,
    ) -> list[_DistributionT]: ...
    @overload
    def resolve(
        self,
        requirements: Iterable[Requirement],
        env: Environment | None = None,
        *,
        installer: _InstallerTypeT[_DistributionT],
        replace_conflicting: bool = False,
        extras: tuple[str, ...] | None = None,
    ) -> list[_DistributionT]: ...
    @overload
    def resolve(
        self,
        requirements: Iterable[Requirement],
        env: Environment | None = None,
        installer: _InstallerType | None = None,
        replace_conflicting: bool = False,
        extras: tuple[str, ...] | None = None,
    ) -> list[Distribution]: ...
    def resolve(
        self,
        requirements: Iterable[Requirement],
        env: Environment | None = None,
        installer: _InstallerType | None | _InstallerTypeT[_DistributionT] = None,
        replace_conflicting: bool = False,
        extras: tuple[str, ...] | None = None,
    ) -> list[Distribution] | list[_DistributionT]:
        """List all distributions needed to (recursively) meet `requirements`

        `requirements` must be a sequence of ``Requirement`` objects.  `env`,
        if supplied, should be an ``Environment`` instance.  If
        not supplied, it defaults to all distributions available within any
        entry or distribution in the working set.  `installer`, if supplied,
        will be invoked with each requirement that cannot be met by an
        already-installed distribution; it should return a ``Distribution`` or
        ``None``.

        Unless `replace_conflicting=True`, raises a VersionConflict exception
        if
        any requirements are found on the path that have the correct name but
        the wrong version.  Otherwise, if an `installer` is supplied it will be
        invoked to obtain the correct version of the requirement and activate
        it.

        `extras` is a list of the extras to be used with these requirements.
        This is important because extra requirements may look like `my_req;
        extra = "my_extra"`, which would otherwise be interpreted as a purely
        optional requirement.  Instead, we want to be able to assert that these
        requirements are truly required.
        """

        # set up the stack
        requirements = list(requirements)[::-1]
        # set of processed requirements
        processed = set()
        # key -> dist
        best = {}
        to_activate = []

        req_extras = _ReqExtras()

        # Mapping of requirement to set of distributions that required it;
        # useful for reporting info about conflicts.
        required_by = collections.defaultdict(set)

        while requirements:
            # process dependencies breadth-first
            req = requirements.pop(0)
            if req in processed:
                # Ignore cyclic or redundant dependencies
                continue

            if not req_extras.markers_pass(req, extras):
                continue

            dist = self._resolve_dist(
                req, best, replace_conflicting, env, installer, required_by, to_activate
            )

            # push the new requirements onto the stack
            new_requirements = dist.requires(req.extras)[::-1]
            requirements.extend(new_requirements)

            # Register the new requirements needed by req
            for new_requirement in new_requirements:
                required_by[new_requirement].add(req.project_name)
                req_extras[new_requirement] = req.extras

            processed.add(req)

        # return list of distros to activate
        return to_activate

    def _resolve_dist(
        self, req, best, replace_conflicting, env, installer, required_by, to_activate
    ) -> Distribution:
        dist = best.get(req.key)
        if dist is None:
            # Find the best distribution and add it to the map
            dist = self.by_key.get(req.key)
            if dist is None or (dist not in req and replace_conflicting):
                ws = self
                if env is None:
                    if dist is None:
                        env = Environment(self.entries)
                    else:
                        # Use an empty environment and workingset to avoid
                        # any further conflicts with the conflicting
                        # distribution
                        env = Environment([])
                        ws = WorkingSet([])
                dist = best[req.key] = env.best_match(
                    req, ws, installer, replace_conflicting=replace_conflicting
                )
                if dist is None:
                    requirers = required_by.get(req, None)
                    raise DistributionNotFound(req, requirers)
            to_activate.append(dist)
        if dist not in req:
            # Oops, the "best" so far conflicts with a dependency
            dependent_req = required_by[req]
            raise VersionConflict(dist, req).with_context(dependent_req)
        return dist

    @overload
    def find_plugins(
        self,
        plugin_env: Environment,
        full_env: Environment | None,
        installer: _InstallerTypeT[_DistributionT],
        fallback: bool = True,
    ) -> tuple[list[_DistributionT], dict[Distribution, Exception]]: ...
    @overload
    def find_plugins(
        self,
        plugin_env: Environment,
        full_env: Environment | None = None,
        *,
        installer: _InstallerTypeT[_DistributionT],
        fallback: bool = True,
    ) -> tuple[list[_DistributionT], dict[Distribution, Exception]]: ...
    @overload
    def find_plugins(
        self,
        plugin_env: Environment,
        full_env: Environment | None = None,
        installer: _InstallerType | None = None,
        fallback: bool = True,
    ) -> tuple[list[Distribution], dict[Distribution, Exception]]: ...
    def find_plugins(
        self,
        plugin_env: Environment,
        full_env: Environment | None = None,
        installer: _InstallerType | None | _InstallerTypeT[_DistributionT] = None,
        fallback: bool = True,
    ) -> tuple[
        list[Distribution] | list[_DistributionT],
        dict[Distribution, Exception],
    ]:
        """Find all activatable distributions in `plugin_env`

        Example usage::

            distributions, errors = working_set.find_plugins(
                Environment(plugin_dirlist)
            )
            # add plugins+libs to sys.path
            map(working_set.add, distributions)
            # display errors
            print('Could not load', errors)

        The `plugin_env` should be an ``Environment`` instance that contains
        only distributions that are in the project's "plugin directory" or
        directories. The `full_env`, if supplied, should be an ``Environment``
        contains all currently-available distributions.  If `full_env` is not
        supplied, one is created automatically from the ``WorkingSet`` this
        method is called on, which will typically mean that every directory on
        ``sys.path`` will be scanned for distributions.

        `installer` is a standard installer callback as used by the
        ``resolve()`` method. The `fallback` flag indicates whether we should
        attempt to resolve older versions of a plugin if the newest version
        cannot be resolved.

        This method returns a 2-tuple: (`distributions`, `error_info`), where
        `distributions` is a list of the distributions found in `plugin_env`
        that were loadable, along with any other distributions that are needed
        to resolve their dependencies.  `error_info` is a dictionary mapping
        unloadable plugin distributions to an exception instance describing the
        error that occurred. Usually this will be a ``DistributionNotFound`` or
        ``VersionConflict`` instance.
        """

        plugin_projects = list(plugin_env)
        # scan project names in alphabetic order
        plugin_projects.sort()

        error_info: dict[Distribution, Exception] = {}
        distributions: dict[Distribution, Exception | None] = {}

        if full_env is None:
            env = Environment(self.entries)
            env += plugin_env
        else:
            env = full_env + plugin_env

        shadow_set = self.__class__([])
        # put all our entries in shadow_set
        list(map(shadow_set.add, self))

        for project_name in plugin_projects:
            for dist in plugin_env[project_name]:
                req = [dist.as_requirement()]

                try:
                    resolvees = shadow_set.resolve(req, env, installer)

                except ResolutionError as v:
                    # save error info
                    error_info[dist] = v
                    if fallback:
                        # try the next older version of project
                        continue
                    else:
                        # give up on this project, keep going
                        break

                else:
                    list(map(shadow_set.add, resolvees))
                    distributions.update(dict.fromkeys(resolvees))

                    # success, no need to try any more versions of this project
                    break

        sorted_distributions = list(distributions)
        sorted_distributions.sort()

        return sorted_distributions, error_info

    def require(self, *requirements: _NestedStr):
        """Ensure that distributions matching `requirements` are activated

        `requirements` must be a string or a (possibly-nested) sequence
        thereof, specifying the distributions and versions required.  The
        return value is a sequence of the distributions that needed to be
        activated to fulfill the requirements; all relevant distributions are
        included, even if they were already activated in this working set.
        """
        needed = self.resolve(parse_requirements(requirements))

        for dist in needed:
            self.add(dist)

        return needed

    def subscribe(
        self, callback: Callable[[Distribution], object], existing: bool = True
    ):
        """Invoke `callback` for all distributions

        If `existing=True` (default),
        call on all existing ones, as well.
        """
        if callback in self.callbacks:
            return
        self.callbacks.append(callback)
        if not existing:
            return
        for dist in self:
            callback(dist)

    def _added_new(self, dist):
        for callback in self.callbacks:
            callback(dist)

    def __getstate__(self):
        return (
            self.entries[:],
            self.entry_keys.copy(),
            self.by_key.copy(),
            self.normalized_to_canonical_keys.copy(),
            self.callbacks[:],
        )

    def __setstate__(self, e_k_b_n_c):
        entries, keys, by_key, normalized_to_canonical_keys, callbacks = e_k_b_n_c
        self.entries = entries[:]
        self.entry_keys = keys.copy()
        self.by_key = by_key.copy()
        self.normalized_to_canonical_keys = normalized_to_canonical_keys.copy()
        self.callbacks = callbacks[:]


class _ReqExtras(Dict["Requirement", Tuple[str, ...]]):
    """
    Map each requirement to the extras that demanded it.
    """

    def markers_pass(self, req: Requirement, extras: tuple[str, ...] | None = None):
        """
        Evaluate markers for req against each extra that
        demanded it.

        Return False if the req has a marker and fails
        evaluation. Otherwise, return True.
        """
        extra_evals = (
            req.marker.evaluate({'extra': extra})
            for extra in self.get(req, ()) + (extras or (None,))
        )
        return not req.marker or any(extra_evals)


class Environment:
    """Searchable snapshot of distributions on a search path"""

    def __init__(
        self,
        search_path: Iterable[str] | None = None,
        platform: str | None = get_supported_platform(),
        python: str | None = PY_MAJOR,
    ):
        """Snapshot distributions available on a search path

        Any distributions found on `search_path` are added to the environment.
        `search_path` should be a sequence of ``sys.path`` items.  If not
        supplied, ``sys.path`` is used.

        `platform` is an optional string specifying the name of the platform
        that platform-specific distributions must be compatible with.  If
        unspecified, it defaults to the current platform.  `python` is an
        optional string naming the desired version of Python (e.g. ``'3.6'``);
        it defaults to the current version.

        You may explicitly set `platform` (and/or `python`) to ``None`` if you
        wish to map *all* distributions, not just those compatible with the
        running platform or Python version.
        """
        self._distmap = {}
        self.platform = platform
        self.python = python
        self.scan(search_path)

    def can_add(self, dist: Distribution):
        """Is distribution `dist` acceptable for this environment?

        The distribution must match the platform and python version
        requirements specified when this environment was created, or False
        is returned.
        """
        py_compat = (
            self.python is None
            or dist.py_version is None
            or dist.py_version == self.python
        )
        return py_compat and compatible_platforms(dist.platform, self.platform)

    def remove(self, dist: Distribution):
        """Remove `dist` from the environment"""
        self._distmap[dist.key].remove(dist)

    def scan(self, search_path: Iterable[str] | None = None):
        """Scan `search_path` for distributions usable in this environment

        Any distributions found are added to the environment.
        `search_path` should be a sequence of ``sys.path`` items.  If not
        supplied, ``sys.path`` is used.  Only distributions conforming to
        the platform/python version defined at initialization are added.
        """
        if search_path is None:
            search_path = sys.path

        for item in search_path:
            for dist in find_distributions(item):
                self.add(dist)

    def __getitem__(self, project_name: str) -> list[Distribution]:
        """Return a newest-to-oldest list of distributions for `project_name`

        Uses case-insensitive `project_name` comparison, assuming all the
        project's distributions use their project's name converted to all
        lowercase as their key.

        """
        distribution_key = project_name.lower()
        return self._distmap.get(distribution_key, [])

    def add(self, dist: Distribution):
        """Add `dist` if we ``can_add()`` it and it has not already been added"""
        if self.can_add(dist) and dist.has_version():
            dists = self._distmap.setdefault(dist.key, [])
            if dist not in dists:
                dists.append(dist)
                dists.sort(key=operator.attrgetter('hashcmp'), reverse=True)

    @overload
    def best_match(
        self,
        req: Requirement,
        working_set: WorkingSet,
        installer: _InstallerTypeT[_DistributionT],
        replace_conflicting: bool = False,
    ) -> _DistributionT: ...
    @overload
    def best_match(
        self,
        req: Requirement,
        working_set: WorkingSet,
        installer: _InstallerType | None = None,
        replace_conflicting: bool = False,
    ) -> Distribution | None: ...
    def best_match(
        self,
        req: Requirement,
        working_set: WorkingSet,
        installer: _InstallerType | None | _InstallerTypeT[_DistributionT] = None,
        replace_conflicting: bool = False,
    ) -> Distribution | None:
        """Find distribution best matching `req` and usable on `working_set`

        This calls the ``find(req)`` method of the `working_set` to see if a
        suitable distribution is already active.  (This may raise
        ``VersionConflict`` if an unsuitable version of the project is already
        active in the specified `working_set`.)  If a suitable distribution
        isn't active, this method returns the newest distribution in the
        environment that meets the ``Requirement`` in `req`.  If no suitable
        distribution is found, and `installer` is supplied, then the result of
        calling the environment's ``obtain(req, installer)`` method will be
        returned.
        """
        try:
            dist = working_set.find(req)
        except VersionConflict:
            if not replace_conflicting:
                raise
            dist = None
        if dist is not None:
            return dist
        for dist in self[req.key]:
            if dist in req:
                return dist
        # try to download/install
        return self.obtain(req, installer)

    @overload
    def obtain(
        self,
        requirement: Requirement,
        installer: _InstallerTypeT[_DistributionT],
    ) -> _DistributionT: ...
    @overload
    def obtain(
        self,
        requirement: Requirement,
        installer: Callable[[Requirement], None] | None = None,
    ) -> None: ...
    @overload
    def obtain(
        self,
        requirement: Requirement,
        installer: _InstallerType | None = None,
    ) -> Distribution | None: ...
    def obtain(
        self,
        requirement: Requirement,
        installer: Callable[[Requirement], None]
        | _InstallerType
        | None
        | _InstallerTypeT[_DistributionT] = None,
    ) -> Distribution | None:
        """Obtain a distribution matching `requirement` (e.g. via download)

        Obtain a distro that matches requirement (e.g. via download).  In the
        base ``Environment`` class, this routine just returns
        ``installer(requirement)``, unless `installer` is None, in which case
        None is returned instead.  This method is a hook that allows subclasses
        to attempt other ways of obtaining a distribution before falling back
        to the `installer` argument."""
        return installer(requirement) if installer else None

    def __iter__(self) -> Iterator[str]:
        """Yield the unique project names of the available distributions"""
        for key in self._distmap.keys():
            if self[key]:
                yield key

    def __iadd__(self, other: Distribution | Environment):
        """In-place addition of a distribution or environment"""
        if isinstance(other, Distribution):
            self.add(other)
        elif isinstance(other, Environment):
            for project in other:
                for dist in other[project]:
                    self.add(dist)
        else:
            raise TypeError("Can't add %r to environment" % (other,))
        return self

    def __add__(self, other: Distribution | Environment):
        """Add an environment or distribution to an environment"""
        new = self.__class__([], platform=None, python=None)
        for env in self, other:
            new += env
        return new


# XXX backward compatibility
AvailableDistributions = Environment


class ExtractionError(RuntimeError):
    """An error occurred extracting a resource

    The following attributes are available from instances of this exception:

    manager
        The resource manager that raised this exception

    cache_path
        The base directory for resource extraction

    original_error
        The exception instance that caused extraction to fail
    """

    manager: ResourceManager
    cache_path: str
    original_error: BaseException | None


class ResourceManager:
    """Manage resource extraction and packages"""

    extraction_path: str | None = None

    def __init__(self):
        self.cached_files = {}

    def resource_exists(self, package_or_requirement: _PkgReqType, resource_name: str):
        """Does the named resource exist?"""
        return get_provider(package_or_requirement).has_resource(resource_name)

    def resource_isdir(self, package_or_requirement: _PkgReqType, resource_name: str):
        """Is the named resource an existing directory?"""
        return get_provider(package_or_requirement).resource_isdir(resource_name)

    def resource_filename(
        self, package_or_requirement: _PkgReqType, resource_name: str
    ):
        """Return a true filesystem path for specified resource"""
        return get_provider(package_or_requirement).get_resource_filename(
            self, resource_name
        )

    def resource_stream(self, package_or_requirement: _PkgReqType, resource_name: str):
        """Return a readable file-like object for specified resource"""
        return get_provider(package_or_requirement).get_resource_stream(
            self, resource_name
        )

    def resource_string(
        self, package_or_requirement: _PkgReqType, resource_name: str
    ) -> bytes:
        """Return specified resource as :obj:`bytes`"""
        return get_provider(package_or_requirement).get_resource_string(
            self, resource_name
        )

    def resource_listdir(self, package_or_requirement: _PkgReqType, resource_name: str):
        """List the contents of the named resource directory"""
        return get_provider(package_or_requirement).resource_listdir(resource_name)

    def extraction_error(self) -> NoReturn:
        """Give an error message for problems extracting file(s)"""

        old_exc = sys.exc_info()[1]
        cache_path = self.extraction_path or get_default_cache()

        tmpl = textwrap.dedent(
            """
            Can't extract file(s) to egg cache

            The following error occurred while trying to extract file(s)
            to the Python egg cache:

              {old_exc}

            The Python egg cache directory is currently set to:

              {cache_path}

            Perhaps your account does not have write access to this directory?
            You can change the cache directory by setting the PYTHON_EGG_CACHE
            environment variable to point to an accessible directory.
            """
        ).lstrip()
        err = ExtractionError(tmpl.format(**locals()))
        err.manager = self
        err.cache_path = cache_path
        err.original_error = old_exc
        raise err

    def get_cache_path(self, archive_name: str, names: Iterable[StrPath] = ()):
        """Return absolute location in cache for `archive_name` and `names`

        The parent directory of the resulting path will be created if it does
        not already exist.  `archive_name` should be the base filename of the
        enclosing egg (which may not be the name of the enclosing zipfile!),
        including its ".egg" extension.  `names`, if provided, should be a
        sequence of path name parts "under" the egg's extraction location.

        This method should only be called by resource providers that need to
        obtain an extraction location, and only for names they intend to
        extract, as it tracks the generated names for possible cleanup later.
        """
        extract_path = self.extraction_path or get_default_cache()
        target_path = os.path.join(extract_path, archive_name + '-tmp', *names)
        try:
            _bypass_ensure_directory(target_path)
        except Exception:
            self.extraction_error()

        self._warn_unsafe_extraction_path(extract_path)

        self.cached_files[target_path] = True
        return target_path

    @staticmethod
    def _warn_unsafe_extraction_path(path):
        """
        If the default extraction path is overridden and set to an insecure
        location, such as /tmp, it opens up an opportunity for an attacker to
        replace an extracted file with an unauthorized payload. Warn the user
        if a known insecure location is used.

        See Distribute #375 for more details.
        """
        if os.name == 'nt' and not path.startswith(os.environ['windir']):
            # On Windows, permissions are generally restrictive by default
            #  and temp directories are not writable by other users, so
            #  bypass the warning.
            return
        mode = os.stat(path).st_mode
        if mode & stat.S_IWOTH or mode & stat.S_IWGRP:
            msg = (
                "Extraction path is writable by group/others "
                "and vulnerable to attack when "
                "used with get_resource_filename ({path}). "
                "Consider a more secure "
                "location (set with .set_extraction_path or the "
                "PYTHON_EGG_CACHE environment variable)."
            ).format(**locals())
            warnings.warn(msg, UserWarning)

    def postprocess(self, tempname: StrOrBytesPath, filename: StrOrBytesPath):
        """Perform any platform-specific postprocessing of `tempname`

        This is where Mac header rewrites should be done; other platforms don't
        have anything special they should do.

        Resource providers should call this method ONLY after successfully
        extracting a compressed resource.  They must NOT call it on resources
        that are already in the filesystem.

        `tempname` is the current (temporary) name of the file, and `filename`
        is the name it will be renamed to by the caller after this routine
        returns.
        """

        if os.name == 'posix':
            # Make the resource executable
            mode = ((os.stat(tempname).st_mode) | 0o555) & 0o7777
            os.chmod(tempname, mode)

    def set_extraction_path(self, path: str):
        """Set the base path where resources will be extracted to, if needed.

        If you do not call this routine before any extractions take place, the
        path defaults to the return value of ``get_default_cache()``.  (Which
        is based on the ``PYTHON_EGG_CACHE`` environment variable, with various
        platform-specific fallbacks.  See that routine's documentation for more
        details.)

        Resources are extracted to subdirectories of this path based upon
        information given by the ``IResourceProvider``.  You may set this to a
        temporary directory, but then you must call ``cleanup_resources()`` to
        delete the extracted files when done.  There is no guarantee that
        ``cleanup_resources()`` will be able to remove all extracted files.

        (Note: you may not change the extraction path for a given resource
        manager once resources have been extracted, unless you first call
        ``cleanup_resources()``.)
        """
        if self.cached_files:
            raise ValueError("Can't change extraction path, files already extracted")

        self.extraction_path = path

    def cleanup_resources(self, force: bool = False) -> list[str]:
        """
        Delete all extracted resource files and directories, returning a list
        of the file and directory names that could not be successfully removed.
        This function does not have any concurrency protection, so it should
        generally only be called when the extraction path is a temporary
        directory exclusive to a single process.  This method is not
        automatically called; you must call it explicitly or register it as an
        ``atexit`` function if you wish to ensure cleanup of a temporary
        directory used for extractions.
        """
        # XXX
        return []


def get_default_cache() -> str:
    """
    Return the ``PYTHON_EGG_CACHE`` environment variable
    or a platform-relevant user cache dir for an app
    named "Python-Eggs".
    """
    return os.environ.get('PYTHON_EGG_CACHE') or _user_cache_dir(appname='Python-Eggs')


def safe_name(name: str):
    """Convert an arbitrary string to a standard distribution name

    Any runs of non-alphanumeric/. characters are replaced with a single '-'.
    """
    return re.sub('[^A-Za-z0-9.]+', '-', name)


def safe_version(version: str):
    """
    Convert an arbitrary string to a standard version string
    """
    try:
        # normalize the version
        return str(_packaging_version.Version(version))
    except _packaging_version.InvalidVersion:
        version = version.replace(' ', '.')
        return re.sub('[^A-Za-z0-9.]+', '-', version)


def _forgiving_version(version):
    """Fallback when ``safe_version`` is not safe enough
    >>> parse_version(_forgiving_version('0.23ubuntu1'))
    <Version('0.23.dev0+sanitized.ubuntu1')>
    >>> parse_version(_forgiving_version('0.23-'))
    <Version('0.23.dev0+sanitized')>
    >>> parse_version(_forgiving_version('0.-_'))
    <Version('0.dev0+sanitized')>
    >>> parse_version(_forgiving_version('42.+?1'))
    <Version('42.dev0+sanitized.1')>
    >>> parse_version(_forgiving_version('hello world'))
    <Version('0.dev0+sanitized.hello.world')>
    """
    version = version.replace(' ', '.')
    match = _PEP440_FALLBACK.search(version)
    if match:
        safe = match["safe"]
        rest = version[len(safe) :]
    else:
        safe = "0"
        rest = version
    local = f"sanitized.{_safe_segment(rest)}".strip(".")
    return f"{safe}.dev0+{local}"


def _safe_segment(segment):
    """Convert an arbitrary string into a safe segment"""
    segment = re.sub('[^A-Za-z0-9.]+', '-', segment)
    segment = re.sub('-[^A-Za-z0-9]+', '-', segment)
    return re.sub(r'\.[^A-Za-z0-9]+', '.', segment).strip(".-")


def safe_extra(extra: str):
    """Convert an arbitrary string to a standard 'extra' name

    Any runs of non-alphanumeric characters are replaced with a single '_',
    and the result is always lowercased.
    """
    return re.sub('[^A-Za-z0-9.-]+', '_', extra).lower()


def to_filename(name: str):
    """Convert a project or version name to its filename-escaped form

    Any '-' characters are currently replaced with '_'.
    """
    return name.replace('-', '_')


def invalid_marker(text: str):
    """
    Validate text as a PEP 508 environment marker; return an exception
    if invalid or False otherwise.
    """
    try:
        evaluate_marker(text)
    except SyntaxError as e:
        e.filename = None
        e.lineno = None
        return e
    return False


def evaluate_marker(text: str, extra: str | None = None) -> bool:
    """
    Evaluate a PEP 508 environment marker.
    Return a boolean indicating the marker result in this environment.
    Raise SyntaxError if marker is invalid.

    This implementation uses the 'pyparsing' module.
    """
    try:
        marker = _packaging_markers.Marker(text)
        return marker.evaluate()
    except _packaging_markers.InvalidMarker as e:
        raise SyntaxError(e) from e


class NullProvider:
    """Try to implement resources and metadata for arbitrary PEP 302 loaders"""

    egg_name: str | None = None
    egg_info: str | None = None
    loader: _LoaderProtocol | None = None

    def __init__(self, module: _ModuleLike):
        self.loader = getattr(module, '__loader__', None)
        self.module_path = os.path.dirname(getattr(module, '__file__', ''))

    def get_resource_filename(self, manager: ResourceManager, resource_name: str):
        return self._fn(self.module_path, resource_name)

    def get_resource_stream(self, manager: ResourceManager, resource_name: str):
        return io.BytesIO(self.get_resource_string(manager, resource_name))

    def get_resource_string(
        self, manager: ResourceManager, resource_name: str
    ) -> bytes:
        return self._get(self._fn(self.module_path, resource_name))

    def has_resource(self, resource_name: str):
        return self._has(self._fn(self.module_path, resource_name))

    def _get_metadata_path(self, name):
        return self._fn(self.egg_info, name)

    def has_metadata(self, name: str) -> bool:
        if not self.egg_info:
            return False

        path = self._get_metadata_path(name)
        return self._has(path)

    def get_metadata(self, name: str):
        if not self.egg_info:
            return ""
        path = self._get_metadata_path(name)
        value = self._get(path)
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError as exc:
            # Include the path in the error message to simplify
            # troubleshooting, and without changing the exception type.
            exc.reason += ' in {} file at path: {}'.format(name, path)
            raise

    def get_metadata_lines(self, name: str) -> Iterator[str]:
        return yield_lines(self.get_metadata(name))

    def resource_isdir(self, resource_name: str):
        return self._isdir(self._fn(self.module_path, resource_name))

    def metadata_isdir(self, name: str) -> bool:
        return bool(self.egg_info and self._isdir(self._fn(self.egg_info, name)))

    def resource_listdir(self, resource_name: str):
        return self._listdir(self._fn(self.module_path, resource_name))

    def metadata_listdir(self, name: str) -> list[str]:
        if self.egg_info:
            return self._listdir(self._fn(self.egg_info, name))
        return []

    def run_script(self, script_name: str, namespace: dict[str, Any]):
        script = 'scripts/' + script_name
        if not self.has_metadata(script):
            raise ResolutionError(
                "Script {script!r} not found in metadata at {self.egg_info!r}".format(
                    **locals()
                ),
            )

        script_text = self.get_metadata(script).replace('\r\n', '\n')
        script_text = script_text.replace('\r', '\n')
        script_filename = self._fn(self.egg_info, script)
        namespace['__file__'] = script_filename
        if os.path.exists(script_filename):
            source = _read_utf8_with_fallback(script_filename)
            code = compile(source, script_filename, 'exec')
            exec(code, namespace, namespace)
        else:
            from linecache import cache

            cache[script_filename] = (
                len(script_text),
                0,
                script_text.split('\n'),
                script_filename,
            )
            script_code = compile(script_text, script_filename, 'exec')
            exec(script_code, namespace, namespace)

    def _has(self, path) -> bool:
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _isdir(self, path) -> bool:
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _listdir(self, path) -> list[str]:
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _fn(self, base: str | None, resource_name: str):
        if base is None:
            raise TypeError(
                "`base` parameter in `_fn` is `None`. Either override this method or check the parameter first."
            )
        self._validate_resource_path(resource_name)
        if resource_name:
            return os.path.join(base, *resource_name.split('/'))
        return base

    @staticmethod
    def _validate_resource_path(path):
        """
        Validate the resource paths according to the docs.
        https://setuptools.pypa.io/en/latest/pkg_resources.html#basic-resource-access

        >>> warned = getfixture('recwarn')
        >>> warnings.simplefilter('always')
        >>> vrp = NullProvider._validate_resource_path
        >>> vrp('foo/bar.txt')
        >>> bool(warned)
        False
        >>> vrp('../foo/bar.txt')
        >>> bool(warned)
        True
        >>> warned.clear()
        >>> vrp('/foo/bar.txt')
        >>> bool(warned)
        True
        >>> vrp('foo/../../bar.txt')
        >>> bool(warned)
        True
        >>> warned.clear()
        >>> vrp('foo/f../bar.txt')
        >>> bool(warned)
        False

        Windows path separators are straight-up disallowed.
        >>> vrp(r'\\foo/bar.txt')
        Traceback (most recent call last):
        ...
        ValueError: Use of .. or absolute path in a resource path \
is not allowed.

        >>> vrp(r'C:\\foo/bar.txt')
        Traceback (most recent call last):
        ...
        ValueError: Use of .. or absolute path in a resource path \
is not allowed.

        Blank values are allowed

        >>> vrp('')
        >>> bool(warned)
        False

        Non-string values are not.

        >>> vrp(None)
        Traceback (most recent call last):
        ...
        AttributeError: ...
        """
        invalid = (
            os.path.pardir in path.split(posixpath.sep)
            or posixpath.isabs(path)
            or ntpath.isabs(path)
            or path.startswith("\\")
        )
        if not invalid:
            return

        msg = "Use of .. or absolute path in a resource path is not allowed."

        # Aggressively disallow Windows absolute paths
        if (path.startswith("\\") or ntpath.isabs(path)) and not posixpath.isabs(path):
            raise ValueError(msg)

        # for compatibility, warn; in future
        # raise ValueError(msg)
        issue_warning(
            msg[:-1] + " and will raise exceptions in a future release.",
            DeprecationWarning,
        )

    def _get(self, path) -> bytes:
        if hasattr(self.loader, 'get_data') and self.loader:
            # Already checked get_data exists
            return self.loader.get_data(path)  # type: ignore[attr-defined]
        raise NotImplementedError(
            "Can't perform this operation for loaders without 'get_data()'"
        )


register_loader_type(object, NullProvider)


def _parents(path):
    """
    yield all parents of path including path
    """
    last = None
    while path != last:
        yield path
        last = path
        path, _ = os.path.split(path)


class EggProvider(NullProvider):
    """Provider based on a virtual filesystem"""

    def __init__(self, module: _ModuleLike):
        super().__init__(module)
        self._setup_prefix()

    def _setup_prefix(self):
        # Assume that metadata may be nested inside a "basket"
        # of multiple eggs and use module_path instead of .archive.
        eggs = filter(_is_egg_path, _parents(self.module_path))
        egg = next(eggs, None)
        egg and self._set_egg(egg)

    def _set_egg(self, path: str):
        self.egg_name = os.path.basename(path)
        self.egg_info = os.path.join(path, 'EGG-INFO')
        self.egg_root = path


class DefaultProvider(EggProvider):
    """Provides access to package resources in the filesystem"""

    def _has(self, path) -> bool:
        return os.path.exists(path)

    def _isdir(self, path) -> bool:
        return os.path.isdir(path)

    def _listdir(self, path):
        return os.listdir(path)

    def get_resource_stream(self, manager: object, resource_name: str):
        return open(self._fn(self.module_path, resource_name), 'rb')

    def _get(self, path) -> bytes:
        with open(path, 'rb') as stream:
            return stream.read()

    @classmethod
    def _register(cls):
        loader_names = (
            'SourceFileLoader',
            'SourcelessFileLoader',
        )
        for name in loader_names:
            loader_cls = getattr(importlib.machinery, name, type(None))
            register_loader_type(loader_cls, cls)


DefaultProvider._register()


class EmptyProvider(NullProvider):
    """Provider that returns nothing for all requests"""

    # A special case, we don't want all Providers inheriting from NullProvider to have a potentially None module_path
    module_path: str | None = None  # type: ignore[assignment]

    _isdir = _has = lambda self, path: False

    def _get(self, path) -> bytes:
        return b''

    def _listdir(self, path):
        return []

    def __init__(self):
        pass


empty_provider = EmptyProvider()


class ZipManifests(Dict[str, "MemoizedZipManifests.manifest_mod"]):
    """
    zip manifest builder
    """

    # `path` could be `StrPath | IO[bytes]` but that violates the LSP for `MemoizedZipManifests.load`
    @classmethod
    def build(cls, path: str):
        """
        Build a dictionary similar to the zipimport directory
        caches, except instead of tuples, store ZipInfo objects.

        Use a platform-specific path separator (os.sep) for the path keys
        for compatibility with pypy on Windows.
        """
        with zipfile.ZipFile(path) as zfile:
            items = (
                (
                    name.replace('/', os.sep),
                    zfile.getinfo(name),
                )
                for name in zfile.namelist()
            )
            return dict(items)

    load = build


class MemoizedZipManifests(ZipManifests):
    """
    Memoized zipfile manifests.
    """

    class manifest_mod(NamedTuple):
        manifest: dict[str, zipfile.ZipInfo]
        mtime: float

    def load(self, path: str) -> dict[str, zipfile.ZipInfo]:  # type: ignore[override] # ZipManifests.load is a classmethod
        """
        Load a manifest at path or return a suitable manifest already loaded.
        """
        path = os.path.normpath(path)
        mtime = os.stat(path).st_mtime

        if path not in self or self[path].mtime != mtime:
            manifest = self.build(path)
            self[path] = self.manifest_mod(manifest, mtime)

        return self[path].manifest


class ZipProvider(EggProvider):
    """Resource support for zips and eggs"""

    eagers: list[str] | None = None
    _zip_manifests = MemoizedZipManifests()
    # ZipProvider's loader should always be a zipimporter or equivalent
    loader: zipimport.zipimporter

    def __init__(self, module: _ZipLoaderModule):
        super().__init__(module)
        self.zip_pre = self.loader.archive + os.sep

    def _zipinfo_name(self, fspath):
        # Convert a virtual filename (full path to file) into a zipfile subpath
        # usable with the zipimport directory cache for our target archive
        fspath = fspath.rstrip(os.sep)
        if fspath == self.loader.archive:
            return ''
        if fspath.startswith(self.zip_pre):
            return fspath[len(self.zip_pre) :]
        raise AssertionError("%s is not a subpath of %s" % (fspath, self.zip_pre))

    def _parts(self, zip_path):
        # Convert a zipfile subpath into an egg-relative path part list.
        # pseudo-fs path
        fspath = self.zip_pre + zip_path
        if fspath.startswith(self.egg_root + os.sep):
            return fspath[len(self.egg_root) + 1 :].split(os.sep)
        raise AssertionError("%s is not a subpath of %s" % (fspath, self.egg_root))

    @property
    def zipinfo(self):
        return self._zip_manifests.load(self.loader.archive)

    def get_resource_filename(self, manager: ResourceManager, resource_name: str):
        if not self.egg_name:
            raise NotImplementedError(
                "resource_filename() only supported for .egg, not .zip"
            )
        # no need to lock for extraction, since we use temp names
        zip_path = self._resource_to_zip(resource_name)
        eagers = self._get_eager_resources()
        if '/'.join(self._parts(zip_path)) in eagers:
            for name in eagers:
                self._extract_resource(manager, self._eager_to_zip(name))
        return self._extract_resource(manager, zip_path)

    @staticmethod
    def _get_date_and_size(zip_stat):
        size = zip_stat.file_size
        # ymdhms+wday, yday, dst
        date_time = zip_stat.date_time + (0, 0, -1)
        # 1980 offset already done
        timestamp = time.mktime(date_time)
        return timestamp, size

    # FIXME: 'ZipProvider._extract_resource' is too complex (12)
    def _extract_resource(self, manager: ResourceManager, zip_path) -> str:  # noqa: C901
        if zip_path in self._index():
            for name in self._index()[zip_path]:
                last = self._extract_resource(manager, os.path.join(zip_path, name))
            # return the extracted directory name
            return os.path.dirname(last)

        timestamp, size = self._get_date_and_size(self.zipinfo[zip_path])

        if not WRITE_SUPPORT:
            raise OSError(
                '"os.rename" and "os.unlink" are not supported on this platform'
            )
        try:
            if not self.egg_name:
                raise OSError(
                    '"egg_name" is empty. This likely means no egg could be found from the "module_path".'
                )
            real_path = manager.get_cache_path(self.egg_name, self._parts(zip_path))

            if self._is_current(real_path, zip_path):
                return real_path

            outf, tmpnam = _mkstemp(
                ".$extract",
                dir=os.path.dirname(real_path),
            )
            os.write(outf, self.loader.get_data(zip_path))
            os.close(outf)
            utime(tmpnam, (timestamp, timestamp))
            manager.postprocess(tmpnam, real_path)

            try:
                rename(tmpnam, real_path)

            except OSError:
                if os.path.isfile(real_path):
                    if self._is_current(real_path, zip_path):
                        # the file became current since it was checked above,
                        #  so proceed.
                        return real_path
                    # Windows, del old file and retry
                    elif os.name == 'nt':
                        unlink(real_path)
                        rename(tmpnam, real_path)
                        return real_path
                raise

        except OSError:
            # report a user-friendly error
            manager.extraction_error()

        return real_path

    def _is_current(self, file_path, zip_path):
        """
        Return True if the file_path is current for this zip_path
        """
        timestamp, size = self._get_date_and_size(self.zipinfo[zip_path])
        if not os.path.isfile(file_path):
            return False
        stat = os.stat(file_path)
        if stat.st_size != size or stat.st_mtime != timestamp:
            return False
        # check that the contents match
        zip_contents = self.loader.get_data(zip_path)
        with open(file_path, 'rb') as f:
            file_contents = f.read()
        return zip_contents == file_contents

    def _get_eager_resources(self):
        if self.eagers is None:
            eagers = []
            for name in ('native_libs.txt', 'eager_resources.txt'):
                if self.has_metadata(name):
                    eagers.extend(self.get_metadata_lines(name))
            self.eagers = eagers
        return self.eagers

    def _index(self):
        try:
            return self._dirindex
        except AttributeError:
            ind = {}
            for path in self.zipinfo:
                parts = path.split(os.sep)
                while parts:
                    parent = os.sep.join(parts[:-1])
                    if parent in ind:
                        ind[parent].append(parts[-1])
                        break
                    else:
                        ind[parent] = [parts.pop()]
            self._dirindex = ind
            return ind

    def _has(self, fspath) -> bool:
        zip_path = self._zipinfo_name(fspath)
        return zip_path in self.zipinfo or zip_path in self._index()

    def _isdir(self, fspath) -> bool:
        return self._zipinfo_name(fspath) in self._index()

    def _listdir(self, fspath):
        return list(self._index().get(self._zipinfo_name(fspath), ()))

    def _eager_to_zip(self, resource_name: str):
        return self._zipinfo_name(self._fn(self.egg_root, resource_name))

    def _resource_to_zip(self, resource_name: str):
        return self._zipinfo_name(self._fn(self.module_path, resource_name))


register_loader_type(zipimport.zipimporter, ZipProvider)


class FileMetadata(EmptyProvider):
    """Metadata handler for standalone PKG-INFO files

    Usage::

        metadata = FileMetadata("/path/to/PKG-INFO")

    This provider rejects all data and metadata requests except for PKG-INFO,
    which is treated as existing, and will be the contents of the file at
    the provided location.
    """

    def __init__(self, path: StrPath):
        self.path = path

    def _get_metadata_path(self, name):
        return self.path

    def has_metadata(self, name: str) -> bool:
        return name == 'PKG-INFO' and os.path.isfile(self.path)

    def get_metadata(self, name: str):
        if name != 'PKG-INFO':
            raise KeyError("No metadata except PKG-INFO is available")

        with open(self.path, encoding='utf-8', errors="replace") as f:
            metadata = f.read()
        self._warn_on_replacement(metadata)
        return metadata

    def _warn_on_replacement(self, metadata):
        replacement_char = '�'
        if replacement_char in metadata:
            tmpl = "{self.path} could not be properly decoded in UTF-8"
            msg = tmpl.format(**locals())
            warnings.warn(msg)

    def get_metadata_lines(self, name: str) -> Iterator[str]:
        return yield_lines(self.get_metadata(name))


class PathMetadata(DefaultProvider):
    """Metadata provider for egg directories

    Usage::

        # Development eggs:

        egg_info = "/path/to/PackageName.egg-info"
        base_dir = os.path.dirname(egg_info)
        metadata = PathMetadata(base_dir, egg_info)
        dist_name = os.path.splitext(os.path.basename(egg_info))[0]
        dist = Distribution(basedir, project_name=dist_name, metadata=metadata)

        # Unpacked egg directories:

        egg_path = "/path/to/PackageName-ver-pyver-etc.egg"
        metadata = PathMetadata(egg_path, os.path.join(egg_path,'EGG-INFO'))
        dist = Distribution.from_filename(egg_path, metadata=metadata)
    """

    def __init__(self, path: str, egg_info: str):
        self.module_path = path
        self.egg_info = egg_info


class EggMetadata(ZipProvider):
    """Metadata provider for .egg files"""

    def __init__(self, importer: zipimport.zipimporter):
        """Create a metadata provider from a zipimporter"""

        self.zip_pre = importer.archive + os.sep
        self.loader = importer
        if importer.prefix:
            self.module_path = os.path.join(importer.archive, importer.prefix)
        else:
            self.module_path = importer.archive
        self._setup_prefix()


_distribution_finders: dict[type, _DistFinderType[Any]] = _declare_state(
    'dict', '_distribution_finders', {}
)


def register_finder(importer_type: type[_T], distribution_finder: _DistFinderType[_T]):
    """Register `distribution_finder` to find distributions in sys.path items

    `importer_type` is the type or class of a PEP 302 "Importer" (sys.path item
    handler), and `distribution_finder` is a callable that, passed a path
    item and the importer instance, yields ``Distribution`` instances found on
    that path item.  See ``pkg_resources.find_on_path`` for an example."""
    _distribution_finders[importer_type] = distribution_finder


def find_distributions(path_item: str, only: bool = False):
    """Yield distributions accessible via `path_item`"""
    importer = get_importer(path_item)
    finder = _find_adapter(_distribution_finders, importer)
    return finder(importer, path_item, only)


def find_eggs_in_zip(
    importer: zipimport.zipimporter, path_item: str, only: bool = False
) -> Iterator[Distribution]:
    """
    Find eggs in zip files; possibly multiple nested eggs.
    """
    if importer.archive.endswith('.whl'):
        # wheels are not supported with this finder
        # they don't have PKG-INFO metadata, and won't ever contain eggs
        return
    metadata = EggMetadata(importer)
    if metadata.has_metadata('PKG-INFO'):
        yield Distribution.from_filename(path_item, metadata=metadata)
    if only:
        # don't yield nested distros
        return
    for subitem in metadata.resource_listdir(''):
        if _is_egg_path(subitem):
            subpath = os.path.join(path_item, subitem)
            dists = find_eggs_in_zip(zipimport.zipimporter(subpath), subpath)
            yield from dists
        elif subitem.lower().endswith(('.dist-info', '.egg-info')):
            subpath = os.path.join(path_item, subitem)
            submeta = EggMetadata(zipimport.zipimporter(subpath))
            submeta.egg_info = subpath
            yield Distribution.from_location(path_item, subitem, submeta)


register_finder(zipimport.zipimporter, find_eggs_in_zip)


def find_nothing(
    importer: object | None, path_item: str | None, only: bool | None = False
):
    return ()


register_finder(object, find_nothing)


def find_on_path(importer: object | None, path_item, only=False):
    """Yield distributions accessible on a sys.path directory"""
    path_item = _normalize_cached(path_item)

    if _is_unpacked_egg(path_item):
        yield Distribution.from_filename(
            path_item,
            metadata=PathMetadata(path_item, os.path.join(path_item, 'EGG-INFO')),
        )
        return

    entries = (os.path.join(path_item, child) for child in safe_listdir(path_item))

    # scan for .egg and .egg-info in directory
    for entry in sorted(entries):
        fullpath = os.path.join(path_item, entry)
        factory = dist_factory(path_item, entry, only)
        yield from factory(fullpath)


def dist_factory(path_item, entry, only):
    """Return a dist_factory for the given entry."""
    lower = entry.lower()
    is_egg_info = lower.endswith('.egg-info')
    is_dist_info = lower.endswith('.dist-info') and os.path.isdir(
        os.path.join(path_item, entry)
    )
    is_meta = is_egg_info or is_dist_info
    return (
        distributions_from_metadata
        if is_meta
        else find_distributions
        if not only and _is_egg_path(entry)
        else resolve_egg_link
        if not only and lower.endswith('.egg-link')
        else NoDists()
    )


class NoDists:
    """
    >>> bool(NoDists())
    False

    >>> list(NoDists()('anything'))
    []
    """

    def __bool__(self):
        return False

    def __call__(self, fullpath):
        return iter(())


def safe_listdir(path: StrOrBytesPath):
    """
    Attempt to list contents of path, but suppress some exceptions.
    """
    try:
        return os.listdir(path)
    except (PermissionError, NotADirectoryError):
        pass
    except OSError as e:
        # Ignore the directory if does not exist, not a directory or
        # permission denied
        if e.errno not in (errno.ENOTDIR, errno.EACCES, errno.ENOENT):
            raise
    return ()


def distributions_from_metadata(path: str):
    root = os.path.dirname(path)
    if os.path.isdir(path):
        if len(os.listdir(path)) == 0:
            # empty metadata dir; skip
            return
        metadata: _MetadataType = PathMetadata(root, path)
    else:
        metadata = FileMetadata(path)
    entry = os.path.basename(path)
    yield Distribution.from_location(
        root,
        entry,
        metadata,
        precedence=DEVELOP_DIST,
    )


def non_empty_lines(path):
    """
    Yield non-empty lines from file at path
    """
    for line in _read_utf8_with_fallback(path).splitlines():
        line = line.strip()
        if line:
            yield line


def resolve_egg_link(path):
    """
    Given a path to an .egg-link, resolve distributions
    present in the referenced path.
    """
    referenced_paths = non_empty_lines(path)
    resolved_paths = (
        os.path.join(os.path.dirname(path), ref) for ref in referenced_paths
    )
    dist_groups = map(find_distributions, resolved_paths)
    return next(dist_groups, ())


if hasattr(pkgutil, 'ImpImporter'):
    register_finder(pkgutil.ImpImporter, find_on_path)

register_finder(importlib.machinery.FileFinder, find_on_path)

_namespace_handlers: dict[type, _NSHandlerType[Any]] = _declare_state(
    'dict', '_namespace_handlers', {}
)
_namespace_packages: dict[str | None, list[str]] = _declare_state(
    'dict', '_namespace_packages', {}
)


def register_namespace_handler(
    importer_type: type[_T], namespace_handler: _NSHandlerType[_T]
):
    """Register `namespace_handler` to declare namespace packages

    `importer_type` is the type or class of a PEP 302 "Importer" (sys.path item
    handler), and `namespace_handler` is a callable like this::

        def namespace_handler(importer, path_entry, moduleName, module):
            # return a path_entry to use for child packages

    Namespace handlers are only called if the importer object has already
    agreed that it can handle the relevant path item, and they should only
    return a subpath if the module __path__ does not already contain an
    equivalent subpath.  For an example namespace handler, see
    ``pkg_resources.file_ns_handler``.
    """
    _namespace_handlers[importer_type] = namespace_handler


def _handle_ns(packageName, path_item):
    """Ensure that named package includes a subpath of path_item (if needed)"""

    importer = get_importer(path_item)
    if importer is None:
        return None

    # use find_spec (PEP 451) and fall-back to find_module (PEP 302)
    try:
        spec = importer.find_spec(packageName)
    except AttributeError:
        # capture warnings due to #1111
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            loader = importer.find_module(packageName)
    else:
        loader = spec.loader if spec else None

    if loader is None:
        return None
    module = sys.modules.get(packageName)
    if module is None:
        module = sys.modules[packageName] = types.ModuleType(packageName)
        module.__path__ = []
        _set_parent_ns(packageName)
    elif not hasattr(module, '__path__'):
        raise TypeError("Not a package:", packageName)
    handler = _find_adapter(_namespace_handlers, importer)
    subpath = handler(importer, path_item, packageName, module)
    if subpath is not None:
        path = module.__path__
        path.append(subpath)
        importlib.import_module(packageName)
        _rebuild_mod_path(path, packageName, module)
    return subpath


def _rebuild_mod_path(orig_path, package_name, module: types.ModuleType):
    """
    Rebuild module.__path__ ensuring that all entries are ordered
    corresponding to their sys.path order
    """
    sys_path = [_normalize_cached(p) for p in sys.path]

    def safe_sys_path_index(entry):
        """
        Workaround for #520 and #513.
        """
        try:
            return sys_path.index(entry)
        except ValueError:
            return float('inf')

    def position_in_sys_path(path):
        """
        Return the ordinal of the path based on its position in sys.path
        """
        path_parts = path.split(os.sep)
        module_parts = package_name.count('.') + 1
        parts = path_parts[:-module_parts]
        return safe_sys_path_index(_normalize_cached(os.sep.join(parts)))

    new_path = sorted(orig_path, key=position_in_sys_path)
    new_path = [_normalize_cached(p) for p in new_path]

    if isinstance(module.__path__, list):
        module.__path__[:] = new_path
    else:
        module.__path__ = new_path


def declare_namespace(packageName: str):
    """Declare that package 'packageName' is a namespace package"""

    msg = (
        f"Deprecated call to `pkg_resources.declare_namespace({packageName!r})`.\n"
        "Implementing implicit namespace packages (as specified in PEP 420) "
        "is preferred to `pkg_resources.declare_namespace`. "
        "See https://setuptools.pypa.io/en/latest/references/"
        "keywords.html#keyword-namespace-packages"
    )
    warnings.warn(msg, DeprecationWarning, stacklevel=2)

    _imp.acquire_lock()
    try:
        if packageName in _namespace_packages:
            return

        path: MutableSequence[str] = sys.path
        parent, _, _ = packageName.rpartition('.')

        if parent:
            declare_namespace(parent)
            if parent not in _namespace_packages:
                __import__(parent)
            try:
                path = sys.modules[parent].__path__
            except AttributeError as e:
                raise TypeError("Not a package:", parent) from e

        # Track what packages are namespaces, so when new path items are added,
        # they can be updated
        _namespace_packages.setdefault(parent or None, []).append(packageName)
        _namespace_packages.setdefault(packageName, [])

        for path_item in path:
            # Ensure all the parent's path items are reflected in the child,
            # if they apply
            _handle_ns(packageName, path_item)

    finally:
        _imp.release_lock()


def fixup_namespace_packages(path_item: str, parent: str | None = None):
    """Ensure that previously-declared namespace packages include path_item"""
    _imp.acquire_lock()
    try:
        for package in _namespace_packages.get(parent, ()):
            subpath = _handle_ns(package, path_item)
            if subpath:
                fixup_namespace_packages(subpath, package)
    finally:
        _imp.release_lock()


def file_ns_handler(
    importer: object,
    path_item: StrPath,
    packageName: str,
    module: types.ModuleType,
):
    """Compute an ns-package subpath for a filesystem or zipfile importer"""

    subpath = os.path.join(path_item, packageName.split('.')[-1])
    normalized = _normalize_cached(subpath)
    for item in module.__path__:
        if _normalize_cached(item) == normalized:
            break
    else:
        # Only return the path if it's not already there
        return subpath


if hasattr(pkgutil, 'ImpImporter'):
    register_namespace_handler(pkgutil.ImpImporter, file_ns_handler)

register_namespace_handler(zipimport.zipimporter, file_ns_handler)
register_namespace_handler(importlib.machinery.FileFinder, file_ns_handler)


def null_ns_handler(
    importer: object,
    path_item: str | None,
    packageName: str | None,
    module: _ModuleLike | None,
):
    return None


register_namespace_handler(object, null_ns_handler)


@overload
def normalize_path(filename: StrPath) -> str: ...
@overload
def normalize_path(filename: BytesPath) -> bytes: ...
def normalize_path(filename: StrOrBytesPath):
    """Normalize a file/dir name for comparison purposes"""
    return os.path.normcase(os.path.realpath(os.path.normpath(_cygwin_patch(filename))))


def _cygwin_patch(filename: StrOrBytesPath):  # pragma: nocover
    """
    Contrary to POSIX 2008, on Cygwin, getcwd (3) contains
    symlink components. Using
    os.path.abspath() works around this limitation. A fix in os.getcwd()
    would probably better, in Cygwin even more so, except
    that this seems to be by design...
    """
    return os.path.abspath(filename) if sys.platform == 'cygwin' else filename


if TYPE_CHECKING:
    # https://github.com/python/mypy/issues/16261
    # https://github.com/python/typeshed/issues/6347
    @overload
    def _normalize_cached(filename: StrPath) -> str: ...
    @overload
    def _normalize_cached(filename: BytesPath) -> bytes: ...
    def _normalize_cached(filename: StrOrBytesPath) -> str | bytes: ...
else:

    @functools.lru_cache(maxsize=None)
    def _normalize_cached(filename):
        return normalize_path(filename)


def _is_egg_path(path):
    """
    Determine if given path appears to be an egg.
    """
    return _is_zip_egg(path) or _is_unpacked_egg(path)


def _is_zip_egg(path):
    return (
        path.lower().endswith('.egg')
        and os.path.isfile(path)
        and zipfile.is_zipfile(path)
    )


def _is_unpacked_egg(path):
    """
    Determine if given path appears to be an unpacked egg.
    """
    return path.lower().endswith('.egg') and os.path.isfile(
        os.path.join(path, 'EGG-INFO', 'PKG-INFO')
    )


def _set_parent_ns(packageName):
    parts = packageName.split('.')
    name = parts.pop()
    if parts:
        parent = '.'.join(parts)
        setattr(sys.modules[parent], name, sys.modules[packageName])


MODULE = re.compile(r"\w+(\.\w+)*$").match
EGG_NAME = re.compile(
    r"""
    (?P<name>[^-]+) (
        -(?P<ver>[^-]+) (
            -py(?P<pyver>[^-]+) (
                -(?P<plat>.+)
            )?
        )?
    )?
    """,
    re.VERBOSE | re.IGNORECASE,
).match


class EntryPoint:
    """Object representing an advertised importable object"""

    def __init__(
        self,
        name: str,
        module_name: str,
        attrs: Iterable[str] = (),
        extras: Iterable[str] = (),
        dist: Distribution | None = None,
    ):
        if not MODULE(module_name):
            raise ValueError("Invalid module name", module_name)
        self.name = name
        self.module_name = module_name
        self.attrs = tuple(attrs)
        self.extras = tuple(extras)
        self.dist = dist

    def __str__(self):
        s = "%s = %s" % (self.name, self.module_name)
        if self.attrs:
            s += ':' + '.'.join(self.attrs)
        if self.extras:
            s += ' [%s]' % ','.join(self.extras)
        return s

    def __repr__(self):
        return "EntryPoint.parse(%r)" % str(self)

    @overload
    def load(
        self,
        require: Literal[True] = True,
        env: Environment | None = None,
        installer: _InstallerType | None = None,
    ) -> _ResolvedEntryPoint: ...
    @overload
    def load(
        self,
        require: Literal[False],
        *args: Any,
        **kwargs: Any,
    ) -> _ResolvedEntryPoint: ...
    def load(
        self,
        require: bool = True,
        *args: Environment | _InstallerType | None,
        **kwargs: Environment | _InstallerType | None,
    ) -> _ResolvedEntryPoint:
        """
        Require packages for this EntryPoint, then resolve it.
        """
        if not require or args or kwargs:
            warnings.warn(
                "Parameters to load are deprecated.  Call .resolve and "
                ".require separately.",
                PkgResourcesDeprecationWarning,
                stacklevel=2,
            )
        if require:
            # We could pass `env` and `installer` directly,
            # but keeping `*args` and `**kwargs` for backwards compatibility
            self.require(*args, **kwargs)  # type: ignore
        return self.resolve()

    def resolve(self) -> _ResolvedEntryPoint:
        """
        Resolve the entry point from its module and attrs.
        """
        module = __import__(self.module_name, fromlist=['__name__'], level=0)
        try:
            return functools.reduce(getattr, self.attrs, module)
        except AttributeError as exc:
            raise ImportError(str(exc)) from exc

    def require(
        self,
        env: Environment | None = None,
        installer: _InstallerType | None = None,
    ):
        if not self.dist:
            error_cls = UnknownExtra if self.extras else AttributeError
            raise error_cls("Can't require() without a distribution", self)

        # Get the requirements for this entry point with all its extras and
        # then resolve them. We have to pass `extras` along when resolving so
        # that the working set knows what extras we want. Otherwise, for
        # dist-info distributions, the working set will assume that the
        # requirements for that extra are purely optional and skip over them.
        reqs = self.dist.requires(self.extras)
        items = working_set.resolve(reqs, env, installer, extras=self.extras)
        list(map(working_set.add, items))

    pattern = re.compile(
        r'\s*'
        r'(?P<name>.+?)\s*'
        r'=\s*'
        r'(?P<module>[\w.]+)\s*'
        r'(:\s*(?P<attr>[\w.]+))?\s*'
        r'(?P<extras>\[.*\])?\s*$'
    )

    @classmethod
    def parse(cls, src: str, dist: Distribution | None = None):
        """Parse a single entry point from string `src`

        Entry point syntax follows the form::

            name = some.module:some.attr [extra1, extra2]

        The entry name and module name are required, but the ``:attrs`` and
        ``[extras]`` parts are optional
        """
        m = cls.pattern.match(src)
        if not m:
            msg = "EntryPoint must be in 'name=module:attrs [extras]' format"
            raise ValueError(msg, src)
        res = m.groupdict()
        extras = cls._parse_extras(res['extras'])
        attrs = res['attr'].split('.') if res['attr'] else ()
        return cls(res['name'], res['module'], attrs, extras, dist)

    @classmethod
    def _parse_extras(cls, extras_spec):
        if not extras_spec:
            return ()
        req = Requirement.parse('x' + extras_spec)
        if req.specs:
            raise ValueError
        return req.extras

    @classmethod
    def parse_group(
        cls,
        group: str,
        lines: _NestedStr,
        dist: Distribution | None = None,
    ):
        """Parse an entry point group"""
        if not MODULE(group):
            raise ValueError("Invalid group name", group)
        this: dict[str, Self] = {}
        for line in yield_lines(lines):
            ep = cls.parse(line, dist)
            if ep.name in this:
                raise ValueError("Duplicate entry point", group, ep.name)
            this[ep.name] = ep
        return this

    @classmethod
    def parse_map(
        cls,
        data: str | Iterable[str] | dict[str, str | Iterable[str]],
        dist: Distribution | None = None,
    ):
        """Parse a map of entry point groups"""
        _data: Iterable[tuple[str | None, str | Iterable[str]]]
        if isinstance(data, dict):
            _data = data.items()
        else:
            _data = split_sections(data)
        maps: dict[str, dict[str, Self]] = {}
        for group, lines in _data:
            if group is None:
                if not lines:
                    continue
                raise ValueError("Entry points must be listed in groups")
            group = group.strip()
            if group in maps:
                raise ValueError("Duplicate group name", group)
            maps[group] = cls.parse_group(group, lines, dist)
        return maps


def _version_from_file(lines):
    """
    Given an iterable of lines from a Metadata file, return
    the value of the Version field, if present, or None otherwise.
    """

    def is_version_line(line):
        return line.lower().startswith('version:')

    version_lines = filter(is_version_line, lines)
    line = next(iter(version_lines), '')
    _, _, value = line.partition(':')
    return safe_version(value.strip()) or None


class Distribution:
    """Wrap an actual or potential sys.path entry w/metadata"""

    PKG_INFO = 'PKG-INFO'

    def __init__(
        self,
        location: str | None = None,
        metadata: _MetadataType = None,
        project_name: str | None = None,
        version: str | None = None,
        py_version: str | None = PY_MAJOR,
        platform: str | None = None,
        precedence: int = EGG_DIST,
    ):
        self.project_name = safe_name(project_name or 'Unknown')
        if version is not None:
            self._version = safe_version(version)
        self.py_version = py_version
        self.platform = platform
        self.location = location
        self.precedence = precedence
        self._provider = metadata or empty_provider

    @classmethod
    def from_location(
        cls,
        location: str,
        basename: StrPath,
        metadata: _MetadataType = None,
        **kw: int,  # We could set `precedence` explicitly, but keeping this as `**kw` for full backwards and subclassing compatibility
    ) -> Distribution:
        project_name, version, py_version, platform = [None] * 4
        basename, ext = os.path.splitext(basename)
        if ext.lower() in _distributionImpl:
            cls = _distributionImpl[ext.lower()]

            match = EGG_NAME(basename)
            if match:
                project_name, version, py_version, platform = match.group(
                    'name', 'ver', 'pyver', 'plat'
                )
        return cls(
            location,
            metadata,
            project_name=project_name,
            version=version,
            py_version=py_version,
            platform=platform,
            **kw,
        )._reload_version()

    def _reload_version(self):
        return self

    @property
    def hashcmp(self):
        return (
            self._forgiving_parsed_version,
            self.precedence,
            self.key,
            self.location,
            self.py_version or '',
            self.platform or '',
        )

    def __hash__(self):
        return hash(self.hashcmp)

    def __lt__(self, other: Distribution):
        return self.hashcmp < other.hashcmp

    def __le__(self, other: Distribution):
        return self.hashcmp <= other.hashcmp

    def __gt__(self, other: Distribution):
        return self.hashcmp > other.hashcmp

    def __ge__(self, other: Distribution):
        return self.hashcmp >= other.hashcmp

    def __eq__(self, other: object):
        if not isinstance(other, self.__class__):
            # It's not a Distribution, so they are not equal
            return False
        return self.hashcmp == other.hashcmp

    def __ne__(self, other: object):
        return not self == other

    # These properties have to be lazy so that we don't have to load any
    # metadata until/unless it's actually needed.  (i.e., some distributions
    # may not know their name or version without loading PKG-INFO)

    @property
    def key(self):
        try:
            return self._key
        except AttributeError:
            self._key = key = self.project_name.lower()
            return key

    @property
    def parsed_version(self):
        if not hasattr(self, "_parsed_version"):
            try:
                self._parsed_version = parse_version(self.version)
            except _packaging_version.InvalidVersion as ex:
                info = f"(package: {self.project_name})"
                if hasattr(ex, "add_note"):
                    ex.add_note(info)  # PEP 678
                    raise
                raise _packaging_version.InvalidVersion(f"{str(ex)} {info}") from None

        return self._parsed_version

    @property
    def _forgiving_parsed_version(self):
        try:
            return self.parsed_version
        except _packaging_version.InvalidVersion as ex:
            self._parsed_version = parse_version(_forgiving_version(self.version))

            notes = "\n".join(getattr(ex, "__notes__", []))  # PEP 678
            msg = f"""!!\n\n
            *************************************************************************
            {str(ex)}\n{notes}

            This is a long overdue deprecation.
            For the time being, `pkg_resources` will use `{self._parsed_version}`
            as a replacement to avoid breaking existing environments,
            but no future compatibility is guaranteed.

            If you maintain package {self.project_name} you should implement
            the relevant changes to adequate the project to PEP 440 immediately.
            *************************************************************************
            \n\n!!
            """
            warnings.warn(msg, DeprecationWarning)

            return self._parsed_version

    @property
    def version(self):
        try:
            return self._version
        except AttributeError as e:
            version = self._get_version()
            if version is None:
                path = self._get_metadata_path_for_display(self.PKG_INFO)
                msg = ("Missing 'Version:' header and/or {} file at path: {}").format(
                    self.PKG_INFO, path
                )
                raise ValueError(msg, self) from e

            return version

    @property
    def _dep_map(self):
        """
        A map of extra to its list of (direct) requirements
        for this distribution, including the null extra.
        """
        try:
            return self.__dep_map
        except AttributeError:
            self.__dep_map = self._filter_extras(self._build_dep_map())
        return self.__dep_map

    @staticmethod
    def _filter_extras(dm: dict[str | None, list[Requirement]]):
        """
        Given a mapping of extras to dependencies, strip off
        environment markers and filter out any dependencies
        not matching the markers.
        """
        for extra in list(filter(None, dm)):
            new_extra: str | None = extra
            reqs = dm.pop(extra)
            new_extra, _, marker = extra.partition(':')
            fails_marker = marker and (
                invalid_marker(marker) or not evaluate_marker(marker)
            )
            if fails_marker:
                reqs = []
            new_extra = safe_extra(new_extra) or None

            dm.setdefault(new_extra, []).extend(reqs)
        return dm

    def _build_dep_map(self):
        dm = {}
        for name in 'requires.txt', 'depends.txt':
            for extra, reqs in split_sections(self._get_metadata(name)):
                dm.setdefault(extra, []).extend(parse_requirements(reqs))
        return dm

    def requires(self, extras: Iterable[str] = ()):
        """List of Requirements needed for this distro if `extras` are used"""
        dm = self._dep_map
        deps: list[Requirement] = []
        deps.extend(dm.get(None, ()))
        for ext in extras:
            try:
                deps.extend(dm[safe_extra(ext)])
            except KeyError as e:
                raise UnknownExtra(
                    "%s has no such extra feature %r" % (self, ext)
                ) from e
        return deps

    def _get_metadata_path_for_display(self, name):
        """
        Return the path to the given metadata file, if available.
        """
        try:
            # We need to access _get_metadata_path() on the provider object
            # directly rather than through this class's __getattr__()
            # since _get_metadata_path() is marked private.
            path = self._provider._get_metadata_path(name)

        # Handle exceptions e.g. in case the distribution's metadata
        # provider doesn't support _get_metadata_path().
        except Exception:
            return '[could not detect]'

        return path

    def _get_metadata(self, name):
        if self.has_metadata(name):
            yield from self.get_metadata_lines(name)

    def _get_version(self):
        lines = self._get_metadata(self.PKG_INFO)
        return _version_from_file(lines)

    def activate(self, path: list[str] | None = None, replace: bool = False):
        """Ensure distribution is importable on `path` (default=sys.path)"""
        if path is None:
            path = sys.path
        self.insert_on(path, replace=replace)
        if path is sys.path and self.location is not None:
            fixup_namespace_packages(self.location)
            for pkg in self._get_metadata('namespace_packages.txt'):
                if pkg in sys.modules:
                    declare_namespace(pkg)

    def egg_name(self):
        """Return what this distribution's standard .egg filename should be"""
        filename = "%s-%s-py%s" % (
            to_filename(self.project_name),
            to_filename(self.version),
            self.py_version or PY_MAJOR,
        )

        if self.platform:
            filename += '-' + self.platform
        return filename

    def __repr__(self):
        if self.location:
            return "%s (%s)" % (self, self.location)
        else:
            return str(self)

    def __str__(self):
        try:
            version = getattr(self, 'version', None)
        except ValueError:
            version = None
        version = version or "[unknown version]"
        return "%s %s" % (self.project_name, version)

    def __getattr__(self, attr):
        """Delegate all unrecognized public attributes to .metadata provider"""
        if attr.startswith('_'):
            raise AttributeError(attr)
        return getattr(self._provider, attr)

    def __dir__(self):
        return list(
            set(super().__dir__())
            | set(attr for attr in self._provider.__dir__() if not attr.startswith('_'))
        )

    @classmethod
    def from_filename(
        cls,
        filename: StrPath,
        metadata: _MetadataType = None,
        **kw: int,  # We could set `precedence` explicitly, but keeping this as `**kw` for full backwards and subclassing compatibility
    ):
        return cls.from_location(
            _normalize_cached(filename), os.path.basename(filename), metadata, **kw
        )

    def as_requirement(self):
        """Return a ``Requirement`` that matches this distribution exactly"""
        if isinstance(self.parsed_version, _packaging_version.Version):
            spec = "%s==%s" % (self.project_name, self.parsed_version)
        else:
            spec = "%s===%s" % (self.project_name, self.parsed_version)

        return Requirement.parse(spec)

    def load_entry_point(self, group: str, name: str) -> _ResolvedEntryPoint:
        """Return the `name` entry point of `group` or raise ImportError"""
        ep = self.get_entry_info(group, name)
        if ep is None:
            raise ImportError("Entry point %r not found" % ((group, name),))
        return ep.load()

    @overload
    def get_entry_map(self, group: None = None) -> dict[str, dict[str, EntryPoint]]: ...
    @overload
    def get_entry_map(self, group: str) -> dict[str, EntryPoint]: ...
    def get_entry_map(self, group: str | None = None):
        """Return the entry point map for `group`, or the full entry map"""
        if not hasattr(self, "_ep_map"):
            self._ep_map = EntryPoint.parse_map(
                self._get_metadata('entry_points.txt'), self
            )
        if group is not None:
            return self._ep_map.get(group, {})
        return self._ep_map

    def get_entry_info(self, group: str, name: str):
        """Return the EntryPoint object for `group`+`name`, or ``None``"""
        return self.get_entry_map(group).get(name)

    # FIXME: 'Distribution.insert_on' is too complex (13)
    def insert_on(  # noqa: C901
        self,
        path: list[str],
        loc=None,
        replace: bool = False,
    ):
        """Ensure self.location is on path

        If replace=False (default):
            - If location is already in path anywhere, do nothing.
            - Else:
              - If it's an egg and its parent directory is on path,
                insert just ahead of the parent.
              - Else: add to the end of path.
        If replace=True:
            - If location is already on path anywhere (not eggs)
              or higher priority than its parent (eggs)
              do nothing.
            - Else:
              - If it's an egg and its parent directory is on path,
                insert just ahead of the parent,
                removing any lower-priority entries.
              - Else: add it to the front of path.
        """

        loc = loc or self.location
        if not loc:
            return

        nloc = _normalize_cached(loc)
        bdir = os.path.dirname(nloc)
        npath = [(p and _normalize_cached(p) or p) for p in path]

        for p, item in enumerate(npath):
            if item == nloc:
                if replace:
                    break
                else:
                    # don't modify path (even removing duplicates) if
                    # found and not replace
                    return
            elif item == bdir and self.precedence == EGG_DIST:
                # if it's an .egg, give it precedence over its directory
                # UNLESS it's already been added to sys.path and replace=False
                if (not replace) and nloc in npath[p:]:
                    return
                if path is sys.path:
                    self.check_version_conflict()
                path.insert(p, loc)
                npath.insert(p, nloc)
                break
        else:
            if path is sys.path:
                self.check_version_conflict()
            if replace:
                path.insert(0, loc)
            else:
                path.append(loc)
            return

        # p is the spot where we found or inserted loc; now remove duplicates
        while True:
            try:
                np = npath.index(nloc, p + 1)
            except ValueError:
                break
            else:
                del npath[np], path[np]
                # ha!
                p = np

        return

    def check_version_conflict(self):
        if self.key == 'setuptools':
            # ignore the inevitable setuptools self-conflicts  :(
            return

        nsp = dict.fromkeys(self._get_metadata('namespace_packages.txt'))
        loc = normalize_path(self.location)
        for modname in self._get_metadata('top_level.txt'):
            if (
                modname not in sys.modules
                or modname in nsp
                or modname in _namespace_packages
            ):
                continue
            if modname in ('pkg_resources', 'setuptools', 'site'):
                continue
            fn = getattr(sys.modules[modname], '__file__', None)
            if fn and (
                normalize_path(fn).startswith(loc) or fn.startswith(self.location)
            ):
                continue
            issue_warning(
                "Module %s was already imported from %s, but %s is being added"
                " to sys.path" % (modname, fn, self.location),
            )

    def has_version(self):
        try:
            self.version
        except ValueError:
            issue_warning("Unbuilt egg for " + repr(self))
            return False
        except SystemError:
            # TODO: remove this except clause when python/cpython#103632 is fixed.
            return False
        return True

    def clone(self, **kw: str | int | IResourceProvider | None):
        """Copy this distribution, substituting in any changed keyword args"""
        names = 'project_name version py_version platform location precedence'
        for attr in names.split():
            kw.setdefault(attr, getattr(self, attr, None))
        kw.setdefault('metadata', self._provider)
        # Unsafely unpacking. But keeping **kw for backwards and subclassing compatibility
        return self.__class__(**kw)  # type:ignore[arg-type]

    @property
    def extras(self):
        return [dep for dep in self._dep_map if dep]


class EggInfoDistribution(Distribution):
    def _reload_version(self):
        """
        Packages installed by distutils (e.g. numpy or scipy),
        which uses an old safe_version, and so
        their version numbers can get mangled when
        converted to filenames (e.g., 1.11.0.dev0+2329eae to
        1.11.0.dev0_2329eae). These distributions will not be
        parsed properly
        downstream by Distribution and safe_version, so
        take an extra step and try to get the version number from
        the metadata file itself instead of the filename.
        """
        md_version = self._get_version()
        if md_version:
            self._version = md_version
        return self


class DistInfoDistribution(Distribution):
    """
    Wrap an actual or potential sys.path entry
    w/metadata, .dist-info style.
    """

    PKG_INFO = 'METADATA'
    EQEQ = re.compile(r"([\(,])\s*(\d.*?)\s*([,\)])")

    @property
    def _parsed_pkg_info(self):
        """Parse and cache metadata"""
        try:
            return self._pkg_info
        except AttributeError:
            metadata = self.get_metadata(self.PKG_INFO)
            self._pkg_info = email.parser.Parser().parsestr(metadata)
            return self._pkg_info

    @property
    def _dep_map(self):
        try:
            return self.__dep_map
        except AttributeError:
            self.__dep_map = self._compute_dependencies()
            return self.__dep_map

    def _compute_dependencies(self) -> dict[str | None, list[Requirement]]:
        """Recompute this distribution's dependencies."""
        self.__dep_map: dict[str | None, list[Requirement]] = {None: []}

        reqs: list[Requirement] = []
        # Including any condition expressions
        for req in self._parsed_pkg_info.get_all('Requires-Dist') or []:
            reqs.extend(parse_requirements(req))

        def reqs_for_extra(extra):
            for req in reqs:
                if not req.marker or req.marker.evaluate({'extra': extra}):
                    yield req

        common = types.MappingProxyType(dict.fromkeys(reqs_for_extra(None)))
        self.__dep_map[None].extend(common)

        for extra in self._parsed_pkg_info.get_all('Provides-Extra') or []:
            s_extra = safe_extra(extra.strip())
            self.__dep_map[s_extra] = [
                r for r in reqs_for_extra(extra) if r not in common
            ]

        return self.__dep_map


_distributionImpl = {
    '.egg': Distribution,
    '.egg-info': EggInfoDistribution,
    '.dist-info': DistInfoDistribution,
}


def issue_warning(*args, **kw):
    level = 1
    g = globals()
    try:
        # find the first stack frame that is *not* code in
        # the pkg_resources module, to use for the warning
        while sys._getframe(level).f_globals is g:
            level += 1
    except ValueError:
        pass
    warnings.warn(stacklevel=level + 1, *args, **kw)


def parse_requirements(strs: _NestedStr):
    """
    Yield ``Requirement`` objects for each specification in `strs`.

    `strs` must be a string, or a (possibly-nested) iterable thereof.
    """
    return map(Requirement, join_continuation(map(drop_comment, yield_lines(strs))))


class RequirementParseError(_packaging_requirements.InvalidRequirement):
    "Compatibility wrapper for InvalidRequirement"


class Requirement(_packaging_requirements.Requirement):
    def __init__(self, requirement_string: str):
        """DO NOT CALL THIS UNDOCUMENTED METHOD; use Requirement.parse()!"""
        super().__init__(requirement_string)
        self.unsafe_name = self.name
        project_name = safe_name(self.name)
        self.project_name, self.key = project_name, project_name.lower()
        self.specs = [(spec.operator, spec.version) for spec in self.specifier]
        # packaging.requirements.Requirement uses a set for its extras. We use a variable-length tuple
        self.extras: tuple[str] = tuple(map(safe_extra, self.extras))
        self.hashCmp = (
            self.key,
            self.url,
            self.specifier,
            frozenset(self.extras),
            str(self.marker) if self.marker else None,
        )
        self.__hash = hash(self.hashCmp)

    def __eq__(self, other: object):
        return isinstance(other, Requirement) and self.hashCmp == other.hashCmp

    def __ne__(self, other):
        return not self == other

    def __contains__(self, item: Distribution | str | tuple[str, ...]) -> bool:
        if isinstance(item, Distribution):
            if item.key != self.key:
                return False

            item = item.version

        # Allow prereleases always in order to match the previous behavior of
        # this method. In the future this should be smarter and follow PEP 440
        # more accurately.
        return self.specifier.contains(item, prereleases=True)

    def __hash__(self):
        return self.__hash

    def __repr__(self):
        return "Requirement.parse(%r)" % str(self)

    @staticmethod
    def parse(s: str | Iterable[str]):
        (req,) = parse_requirements(s)
        return req


def _always_object(classes):
    """
    Ensure object appears in the mro even
    for old-style classes.
    """
    if object not in classes:
        return classes + (object,)
    return classes


def _find_adapter(registry: Mapping[type, _AdapterT], ob: object) -> _AdapterT:
    """Return an adapter factory for `ob` from `registry`"""
    types = _always_object(inspect.getmro(getattr(ob, '__class__', type(ob))))
    for t in types:
        if t in registry:
            return registry[t]
    # _find_adapter would previously return None, and immediately be called.
    # So we're raising a TypeError to keep backward compatibility if anyone depended on that behaviour.
    raise TypeError(f"Could not find adapter for {registry} and {ob}")


def ensure_directory(path: StrOrBytesPath):
    """Ensure that the parent directory of `path` exists"""
    dirname = os.path.dirname(path)
    os.makedirs(dirname, exist_ok=True)


def _bypass_ensure_directory(path):
    """Sandbox-bypassing version of ensure_directory()"""
    if not WRITE_SUPPORT:
        raise OSError('"os.mkdir" not supported on this platform.')
    dirname, filename = split(path)
    if dirname and filename and not isdir(dirname):
        _bypass_ensure_directory(dirname)
        try:
            mkdir(dirname, 0o755)
        except FileExistsError:
            pass


def split_sections(s: _NestedStr) -> Iterator[tuple[str | None, list[str]]]:
    """Split a string or iterable thereof into (section, content) pairs

    Each ``section`` is a stripped version of the section header ("[section]")
    and each ``content`` is a list of stripped lines excluding blank lines and
    comment-only lines.  If there are any such lines before the first section
    header, they're returned in a first ``section`` of ``None``.
    """
    section = None
    content = []
    for line in yield_lines(s):
        if line.startswith("["):
            if line.endswith("]"):
                if section or content:
                    yield section, content
                section = line[1:-1].strip()
                content = []
            else:
                raise ValueError("Invalid section heading", line)
        else:
            content.append(line)

    # wrap up last segment
    yield section, content


def _mkstemp(*args, **kw):
    old_open = os.open
    try:
        # temporarily bypass sandboxing
        os.open = os_open
        return tempfile.mkstemp(*args, **kw)
    finally:
        # and then put it back
        os.open = old_open


# Silence the PEP440Warning by default, so that end users don't get hit by it
# randomly just because they use pkg_resources. We want to append the rule
# because we want earlier uses of filterwarnings to take precedence over this
# one.
warnings.filterwarnings("ignore", category=PEP440Warning, append=True)


class PkgResourcesDeprecationWarning(Warning):
    """
    Base class for warning about deprecations in ``pkg_resources``

    This class is not derived from ``DeprecationWarning``, and as such is
    visible by default.
    """


# Ported from ``setuptools`` to avoid introducing an import inter-dependency:
_LOCALE_ENCODING = "locale" if sys.version_info >= (3, 10) else None


def _read_utf8_with_fallback(file: str, fallback_encoding=_LOCALE_ENCODING) -> str:
    """See setuptools.unicode_utils._read_utf8_with_fallback"""
    try:
        with open(file, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:  # pragma: no cover
        msg = f"""\
        ********************************************************************************
        `encoding="utf-8"` fails with {file!r}, trying `encoding={fallback_encoding!r}`.

        This fallback behaviour is considered **deprecated** and future versions of
        `setuptools/pkg_resources` may not implement it.

        Please encode {file!r} with "utf-8" to ensure future builds will succeed.

        If this file was produced by `setuptools` itself, cleaning up the cached files
        and re-building/re-installing the package with a newer version of `setuptools`
        (e.g. by updating `build-system.requires` in its `pyproject.toml`)
        might solve the problem.
        ********************************************************************************
        """
        # TODO: Add a deadline?
        #       See comment in setuptools.unicode_utils._Utf8EncodingNeeded
        warnings.warn(msg, PkgResourcesDeprecationWarning, stacklevel=2)
        with open(file, "r", encoding=fallback_encoding) as f:
            return f.read()


# from jaraco.functools 1.3
def _call_aside(f, *args, **kwargs):
    f(*args, **kwargs)
    return f


@_call_aside
def _initialize(g=globals()):
    "Set up global resource manager (deliberately not state-saved)"
    manager = ResourceManager()
    g['_manager'] = manager
    g.update(
        (name, getattr(manager, name))
        for name in dir(manager)
        if not name.startswith('_')
    )


@_call_aside
def _initialize_master_working_set():
    """
    Prepare the master working set and make the ``require()``
    API available.

    This function has explicit effects on the global state
    of pkg_resources. It is intended to be invoked once at
    the initialization of this module.

    Invocation by other packages is unsupported and done
    at their own risk.
    """
    working_set = _declare_state('object', 'working_set', WorkingSet._build_master())

    require = working_set.require
    iter_entry_points = working_set.iter_entry_points
    add_activation_listener = working_set.subscribe
    run_script = working_set.run_script
    # backward compatibility
    run_main = run_script
    # Activate all distributions already on sys.path with replace=False and
    # ensure that all distributions added to the working set in the future
    # (e.g. by calling ``require()``) will get activated as well,
    # with higher priority (replace=True).
    tuple(dist.activate(replace=False) for dist in working_set)
    add_activation_listener(
        lambda dist: dist.activate(replace=True),
        existing=False,
    )
    working_set.entries = []
    # match order
    list(map(working_set.add_entry, sys.path))
    globals().update(locals())


if TYPE_CHECKING:
    # All of these are set by the @_call_aside methods above
    __resource_manager = ResourceManager()  # Won't exist at runtime
    resource_exists = __resource_manager.resource_exists
    resource_isdir = __resource_manager.resource_isdir
    resource_filename = __resource_manager.resource_filename
    resource_stream = __resource_manager.resource_stream
    resource_string = __resource_manager.resource_string
    resource_listdir = __resource_manager.resource_listdir
    set_extraction_path = __resource_manager.set_extraction_path
    cleanup_resources = __resource_manager.cleanup_resources

    working_set = WorkingSet()
    require = working_set.require
    iter_entry_points = working_set.iter_entry_points
    add_activation_listener = working_set.subscribe
    run_script = working_set.run_script
    run_main = run_script

# === NexusCore/openenv\Lib\site-packages\IPython\core\completer.py ===
"""Completion for IPython.

This module started as fork of the rlcompleter module in the Python standard
library.  The original enhancements made to rlcompleter have been sent
upstream and were accepted as of Python 2.3,

This module now support a wide variety of completion mechanism both available
for normal classic Python code, as well as completer for IPython specific
Syntax like magics.

Latex and Unicode completion
============================

IPython and compatible frontends not only can complete your code, but can help
you to input a wide range of characters. In particular we allow you to insert
a unicode character using the tab completion mechanism.

Forward latex/unicode completion
--------------------------------

Forward completion allows you to easily type a unicode character using its latex
name, or unicode long description. To do so type a backslash follow by the
relevant name and press tab:


Using latex completion:

.. code::

    \\alpha<tab>
    α

or using unicode completion:


.. code::

    \\GREEK SMALL LETTER ALPHA<tab>
    α


Only valid Python identifiers will complete. Combining characters (like arrow or
dots) are also available, unlike latex they need to be put after the their
counterpart that is to say, ``F\\\\vec<tab>`` is correct, not ``\\\\vec<tab>F``.

Some browsers are known to display combining characters incorrectly.

Backward latex completion
-------------------------

It is sometime challenging to know how to type a character, if you are using
IPython, or any compatible frontend you can prepend backslash to the character
and press :kbd:`Tab` to expand it to its latex form.

.. code::

    \\α<tab>
    \\alpha


Both forward and backward completions can be deactivated by setting the
:std:configtrait:`Completer.backslash_combining_completions` option to
``False``.


Experimental
============

Starting with IPython 6.0, this module can make use of the Jedi library to
generate completions both using static analysis of the code, and dynamically
inspecting multiple namespaces. Jedi is an autocompletion and static analysis
for Python. The APIs attached to this new mechanism is unstable and will
raise unless use in an :any:`provisionalcompleter` context manager.

You will find that the following are experimental:

    - :any:`provisionalcompleter`
    - :any:`IPCompleter.completions`
    - :any:`Completion`
    - :any:`rectify_completions`

.. note::

    better name for :any:`rectify_completions` ?

We welcome any feedback on these new API, and we also encourage you to try this
module in debug mode (start IPython with ``--Completer.debug=True``) in order
to have extra logging information if :any:`jedi` is crashing, or if current
IPython completer pending deprecations are returning results not yet handled
by :any:`jedi`

Using Jedi for tab completion allow snippets like the following to work without
having to execute any code:

   >>> myvar = ['hello', 42]
   ... myvar[1].bi<tab>

Tab completion will be able to infer that ``myvar[1]`` is a real number without
executing almost any code unlike the deprecated :any:`IPCompleter.greedy`
option.

Be sure to update :any:`jedi` to the latest stable version or to try the
current development version to get better completions.

Matchers
========

All completions routines are implemented using unified *Matchers* API.
The matchers API is provisional and subject to change without notice.

The built-in matchers include:

- :any:`IPCompleter.dict_key_matcher`:  dictionary key completions,
- :any:`IPCompleter.magic_matcher`: completions for magics,
- :any:`IPCompleter.unicode_name_matcher`,
  :any:`IPCompleter.fwd_unicode_matcher`
  and :any:`IPCompleter.latex_name_matcher`: see `Forward latex/unicode completion`_,
- :any:`back_unicode_name_matcher` and :any:`back_latex_name_matcher`: see `Backward latex completion`_,
- :any:`IPCompleter.file_matcher`: paths to files and directories,
- :any:`IPCompleter.python_func_kw_matcher` - function keywords,
- :any:`IPCompleter.python_matches` - globals and attributes (v1 API),
- ``IPCompleter.jedi_matcher`` - static analysis with Jedi,
- :any:`IPCompleter.custom_completer_matcher` - pluggable completer with a default
  implementation in :any:`InteractiveShell` which uses IPython hooks system
  (`complete_command`) with string dispatch (including regular expressions).
  Differently to other matchers, ``custom_completer_matcher`` will not suppress
  Jedi results to match behaviour in earlier IPython versions.

Custom matchers can be added by appending to ``IPCompleter.custom_matchers`` list.

Matcher API
-----------

Simplifying some details, the ``Matcher`` interface can described as

.. code-block::

    MatcherAPIv1 = Callable[[str], list[str]]
    MatcherAPIv2 = Callable[[CompletionContext], SimpleMatcherResult]

    Matcher = MatcherAPIv1 | MatcherAPIv2

The ``MatcherAPIv1`` reflects the matcher API as available prior to IPython 8.6.0
and remains supported as a simplest way for generating completions. This is also
currently the only API supported by the IPython hooks system `complete_command`.

To distinguish between matcher versions ``matcher_api_version`` attribute is used.
More precisely, the API allows to omit ``matcher_api_version`` for v1 Matchers,
and requires a literal ``2`` for v2 Matchers.

Once the API stabilises future versions may relax the requirement for specifying
``matcher_api_version`` by switching to :any:`functools.singledispatch`, therefore
please do not rely on the presence of ``matcher_api_version`` for any purposes.

Suppression of competing matchers
---------------------------------

By default results from all matchers are combined, in the order determined by
their priority. Matchers can request to suppress results from subsequent
matchers by setting ``suppress`` to ``True`` in the ``MatcherResult``.

When multiple matchers simultaneously request suppression, the results from of
the matcher with higher priority will be returned.

Sometimes it is desirable to suppress most but not all other matchers;
this can be achieved by adding a set of identifiers of matchers which
should not be suppressed to ``MatcherResult`` under ``do_not_suppress`` key.

The suppression behaviour can is user-configurable via
:std:configtrait:`IPCompleter.suppress_competing_matchers`.
"""


# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
#
# Some of this code originated from rlcompleter in the Python standard library
# Copyright (C) 2001 Python Software Foundation, www.python.org

from __future__ import annotations
import builtins as builtin_mod
import enum
import glob
import inspect
import itertools
import keyword
import ast
import os
import re
import string
import sys
import tokenize
import time
import unicodedata
import uuid
import warnings
from ast import literal_eval
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cached_property, partial
from types import SimpleNamespace
from typing import (
    Iterable,
    Iterator,
    Union,
    Any,
    Sequence,
    Optional,
    TYPE_CHECKING,
    Sized,
    TypeVar,
    Literal,
)

from IPython.core.guarded_eval import guarded_eval, EvaluationContext
from IPython.core.error import TryNext
from IPython.core.inputtransformer2 import ESC_MAGIC
from IPython.core.latex_symbols import latex_symbols, reverse_latex_symbol
from IPython.testing.skipdoctest import skip_doctest
from IPython.utils import generics
from IPython.utils.PyColorize import theme_table
from IPython.utils.decorators import sphinx_options
from IPython.utils.dir2 import dir2, get_real_method
from IPython.utils.docs import GENERATING_DOCUMENTATION
from IPython.utils.path import ensure_dir_exists
from IPython.utils.process import arg_split
from traitlets import (
    Bool,
    Enum,
    Int,
    List as ListTrait,
    Unicode,
    Dict as DictTrait,
    DottedObjectName,
    Union as UnionTrait,
    observe,
)
from traitlets.config.configurable import Configurable
from traitlets.utils.importstring import import_item

import __main__

from typing import cast

if sys.version_info < (3, 12):
    from typing_extensions import TypedDict, NotRequired, Protocol, TypeAlias, TypeGuard
else:
    from typing import TypedDict, NotRequired, Protocol, TypeAlias, TypeGuard


# skip module docstests
__skip_doctest__ = True


try:
    import jedi
    jedi.settings.case_insensitive_completion = False
    import jedi.api.helpers
    import jedi.api.classes
    JEDI_INSTALLED = True
except ImportError:
    JEDI_INSTALLED = False


# -----------------------------------------------------------------------------
# Globals
#-----------------------------------------------------------------------------

# ranges where we have most of the valid unicode names. We could be more finer
# grained but is it worth it for performance  While unicode have character in the
# range 0, 0x110000, we seem to have name for about 10% of those. (131808 as I
# write this). With below range we cover them all, with a density of ~67%
# biggest next gap we consider only adds up about 1% density and there are 600
# gaps that would need hard coding.
_UNICODE_RANGES = [(32, 0x323B0), (0xE0001, 0xE01F0)]

# Public API
__all__ = ["Completer", "IPCompleter"]

if sys.platform == 'win32':
    PROTECTABLES = ' '
else:
    PROTECTABLES = ' ()[]{}?=\\|;:\'#*"^&'

# Protect against returning an enormous number of completions which the frontend
# may have trouble processing.
MATCHES_LIMIT = 500

# Completion type reported when no type can be inferred.
_UNKNOWN_TYPE = "<unknown>"

# sentinel value to signal lack of a match
not_found = object()

class ProvisionalCompleterWarning(FutureWarning):
    """
    Exception raise by an experimental feature in this module.

    Wrap code in :any:`provisionalcompleter` context manager if you
    are certain you want to use an unstable feature.
    """
    pass

warnings.filterwarnings('error', category=ProvisionalCompleterWarning)


@skip_doctest
@contextmanager
def provisionalcompleter(action='ignore'):
    """
    This context manager has to be used in any place where unstable completer
    behavior and API may be called.

    >>> with provisionalcompleter():
    ...     completer.do_experimental_things() # works

    >>> completer.do_experimental_things() # raises.

    .. note::

        Unstable

        By using this context manager you agree that the API in use may change
        without warning, and that you won't complain if they do so.

        You also understand that, if the API is not to your liking, you should report
        a bug to explain your use case upstream.

        We'll be happy to get your feedback, feature requests, and improvements on
        any of the unstable APIs!
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(action, category=ProvisionalCompleterWarning)
        yield


def has_open_quotes(s: str) -> Union[str, bool]:
    """Return whether a string has open quotes.

    This simply counts whether the number of quote characters of either type in
    the string is odd.

    Returns
    -------
    If there is an open quote, the quote character is returned.  Else, return
    False.
    """
    # We check " first, then ', so complex cases with nested quotes will get
    # the " to take precedence.
    if s.count('"') % 2:
        return '"'
    elif s.count("'") % 2:
        return "'"
    else:
        return False


def protect_filename(s: str, protectables: str = PROTECTABLES) -> str:
    """Escape a string to protect certain characters."""
    if set(s) & set(protectables):
        if sys.platform == "win32":
            return '"' + s + '"'
        else:
            return "".join(("\\" + c if c in protectables else c) for c in s)
    else:
        return s


def expand_user(path: str) -> tuple[str, bool, str]:
    """Expand ``~``-style usernames in strings.

    This is similar to :func:`os.path.expanduser`, but it computes and returns
    extra information that will be useful if the input was being used in
    computing completions, and you wish to return the completions with the
    original '~' instead of its expanded value.

    Parameters
    ----------
    path : str
        String to be expanded.  If no ~ is present, the output is the same as the
        input.

    Returns
    -------
    newpath : str
        Result of ~ expansion in the input path.
    tilde_expand : bool
        Whether any expansion was performed or not.
    tilde_val : str
        The value that ~ was replaced with.
    """
    # Default values
    tilde_expand = False
    tilde_val = ''
    newpath = path

    if path.startswith('~'):
        tilde_expand = True
        rest = len(path)-1
        newpath = os.path.expanduser(path)
        if rest:
            tilde_val = newpath[:-rest]
        else:
            tilde_val = newpath

    return newpath, tilde_expand, tilde_val


def compress_user(path:str, tilde_expand:bool, tilde_val:str) -> str:
    """Does the opposite of expand_user, with its outputs.
    """
    if tilde_expand:
        return path.replace(tilde_val, '~')
    else:
        return path


def completions_sorting_key(word):
    """key for sorting completions

    This does several things:

    - Demote any completions starting with underscores to the end
    - Insert any %magic and %%cellmagic completions in the alphabetical order
      by their name
    """
    prio1, prio2 = 0, 0

    if word.startswith('__'):
        prio1 = 2
    elif word.startswith('_'):
        prio1 = 1

    if word.endswith('='):
        prio1 = -1

    if word.startswith('%%'):
        # If there's another % in there, this is something else, so leave it alone
        if "%" not in word[2:]:
            word = word[2:]
            prio2 = 2
    elif word.startswith('%'):
        if "%" not in word[1:]:
            word = word[1:]
            prio2 = 1

    return prio1, word, prio2


class _FakeJediCompletion:
    """
    This is a workaround to communicate to the UI that Jedi has crashed and to
    report a bug. Will be used only id :any:`IPCompleter.debug` is set to true.

    Added in IPython 6.0 so should likely be removed for 7.0

    """

    def __init__(self, name):

        self.name = name
        self.complete = name
        self.type = 'crashed'
        self.name_with_symbols = name
        self.signature = ""
        self._origin = "fake"
        self.text = "crashed"

    def __repr__(self):
        return '<Fake completion object jedi has crashed>'


_JediCompletionLike = Union["jedi.api.Completion", _FakeJediCompletion]


class Completion:
    """
    Completion object used and returned by IPython completers.

    .. warning::

        Unstable

        This function is unstable, API may change without warning.
        It will also raise unless use in proper context manager.

    This act as a middle ground :any:`Completion` object between the
    :any:`jedi.api.classes.Completion` object and the Prompt Toolkit completion
    object. While Jedi need a lot of information about evaluator and how the
    code should be ran/inspected, PromptToolkit (and other frontend) mostly
    need user facing information.

    - Which range should be replaced replaced by what.
    - Some metadata (like completion type), or meta information to displayed to
      the use user.

    For debugging purpose we can also store the origin of the completion (``jedi``,
    ``IPython.python_matches``, ``IPython.magics_matches``...).
    """

    __slots__ = ['start', 'end', 'text', 'type', 'signature', '_origin']

    def __init__(
        self,
        start: int,
        end: int,
        text: str,
        *,
        type: Optional[str] = None,
        _origin="",
        signature="",
    ) -> None:
        warnings.warn(
            "``Completion`` is a provisional API (as of IPython 6.0). "
            "It may change without warnings. "
            "Use in corresponding context manager.",
            category=ProvisionalCompleterWarning,
            stacklevel=2,
        )

        self.start = start
        self.end = end
        self.text = text
        self.type = type
        self.signature = signature
        self._origin = _origin

    def __repr__(self):
        return '<Completion start=%s end=%s text=%r type=%r, signature=%r,>' % \
                (self.start, self.end, self.text, self.type or '?', self.signature or '?')

    def __eq__(self, other) -> bool:
        """
        Equality and hash do not hash the type (as some completer may not be
        able to infer the type), but are use to (partially) de-duplicate
        completion.

        Completely de-duplicating completion is a bit tricker that just
        comparing as it depends on surrounding text, which Completions are not
        aware of.
        """
        return self.start == other.start and \
            self.end == other.end and \
            self.text == other.text

    def __hash__(self):
        return hash((self.start, self.end, self.text))


class SimpleCompletion:
    """Completion item to be included in the dictionary returned by new-style Matcher (API v2).

    .. warning::

        Provisional

        This class is used to describe the currently supported attributes of
        simple completion items, and any additional implementation details
        should not be relied on. Additional attributes may be included in
        future versions, and meaning of text disambiguated from the current
        dual meaning of "text to insert" and "text to used as a label".
    """

    __slots__ = ["text", "type"]

    def __init__(self, text: str, *, type: Optional[str] = None):
        self.text = text
        self.type = type

    def __repr__(self):
        return f"<SimpleCompletion text={self.text!r} type={self.type!r}>"


class _MatcherResultBase(TypedDict):
    """Definition of dictionary to be returned by new-style Matcher (API v2)."""

    #: Suffix of the provided ``CompletionContext.token``, if not given defaults to full token.
    matched_fragment: NotRequired[str]

    #: Whether to suppress results from all other matchers (True), some
    #: matchers (set of identifiers) or none (False); default is False.
    suppress: NotRequired[Union[bool, set[str]]]

    #: Identifiers of matchers which should NOT be suppressed when this matcher
    #: requests to suppress all other matchers; defaults to an empty set.
    do_not_suppress: NotRequired[set[str]]

    #: Are completions already ordered and should be left as-is? default is False.
    ordered: NotRequired[bool]


@sphinx_options(show_inherited_members=True, exclude_inherited_from=["dict"])
class SimpleMatcherResult(_MatcherResultBase, TypedDict):
    """Result of new-style completion matcher."""

    # note: TypedDict is added again to the inheritance chain
    # in order to get __orig_bases__ for documentation

    #: List of candidate completions
    completions: Sequence[SimpleCompletion] | Iterator[SimpleCompletion]


class _JediMatcherResult(_MatcherResultBase):
    """Matching result returned by Jedi (will be processed differently)"""

    #: list of candidate completions
    completions: Iterator[_JediCompletionLike]


AnyMatcherCompletion = Union[_JediCompletionLike, SimpleCompletion]
AnyCompletion = TypeVar("AnyCompletion", AnyMatcherCompletion, Completion)


@dataclass
class CompletionContext:
    """Completion context provided as an argument to matchers in the Matcher API v2."""

    # rationale: many legacy matchers relied on completer state (`self.text_until_cursor`)
    # which was not explicitly visible as an argument of the matcher, making any refactor
    # prone to errors; by explicitly passing `cursor_position` we can decouple the matchers
    # from the completer, and make substituting them in sub-classes easier.

    #: Relevant fragment of code directly preceding the cursor.
    #: The extraction of token is implemented via splitter heuristic
    #: (following readline behaviour for legacy reasons), which is user configurable
    #: (by switching the greedy mode).
    token: str

    #: The full available content of the editor or buffer
    full_text: str

    #: Cursor position in the line (the same for ``full_text`` and ``text``).
    cursor_position: int

    #: Cursor line in ``full_text``.
    cursor_line: int

    #: The maximum number of completions that will be used downstream.
    #: Matchers can use this information to abort early.
    #: The built-in Jedi matcher is currently excepted from this limit.
    # If not given, return all possible completions.
    limit: Optional[int]

    @cached_property
    def text_until_cursor(self) -> str:
        return self.line_with_cursor[: self.cursor_position]

    @cached_property
    def line_with_cursor(self) -> str:
        return self.full_text.split("\n")[self.cursor_line]


#: Matcher results for API v2.
MatcherResult = Union[SimpleMatcherResult, _JediMatcherResult]


class _MatcherAPIv1Base(Protocol):
    def __call__(self, text: str) -> list[str]:
        """Call signature."""
        ...

    #: Used to construct the default matcher identifier
    __qualname__: str


class _MatcherAPIv1Total(_MatcherAPIv1Base, Protocol):
    #: API version
    matcher_api_version: Optional[Literal[1]]

    def __call__(self, text: str) -> list[str]:
        """Call signature."""
        ...


#: Protocol describing Matcher API v1.
MatcherAPIv1: TypeAlias = Union[_MatcherAPIv1Base, _MatcherAPIv1Total]


class MatcherAPIv2(Protocol):
    """Protocol describing Matcher API v2."""

    #: API version
    matcher_api_version: Literal[2] = 2

    def __call__(self, context: CompletionContext) -> MatcherResult:
        """Call signature."""
        ...

    #: Used to construct the default matcher identifier
    __qualname__: str


Matcher: TypeAlias = Union[MatcherAPIv1, MatcherAPIv2]


def _is_matcher_v1(matcher: Matcher) -> TypeGuard[MatcherAPIv1]:
    api_version = _get_matcher_api_version(matcher)
    return api_version == 1


def _is_matcher_v2(matcher: Matcher) -> TypeGuard[MatcherAPIv2]:
    api_version = _get_matcher_api_version(matcher)
    return api_version == 2


def _is_sizable(value: Any) -> TypeGuard[Sized]:
    """Determines whether objects is sizable"""
    return hasattr(value, "__len__")


def _is_iterator(value: Any) -> TypeGuard[Iterator]:
    """Determines whether objects is sizable"""
    return hasattr(value, "__next__")


def has_any_completions(result: MatcherResult) -> bool:
    """Check if any result includes any completions."""
    completions = result["completions"]
    if _is_sizable(completions):
        return len(completions) != 0
    if _is_iterator(completions):
        try:
            old_iterator = completions
            first = next(old_iterator)
            result["completions"] = cast(
                Iterator[SimpleCompletion],
                itertools.chain([first], old_iterator),
            )
            return True
        except StopIteration:
            return False
    raise ValueError(
        "Completions returned by matcher need to be an Iterator or a Sizable"
    )


def completion_matcher(
    *,
    priority: Optional[float] = None,
    identifier: Optional[str] = None,
    api_version: int = 1,
) -> Callable[[Matcher], Matcher]:
    """Adds attributes describing the matcher.

    Parameters
    ----------
    priority : Optional[float]
        The priority of the matcher, determines the order of execution of matchers.
        Higher priority means that the matcher will be executed first. Defaults to 0.
    identifier : Optional[str]
        identifier of the matcher allowing users to modify the behaviour via traitlets,
        and also used to for debugging (will be passed as ``origin`` with the completions).

        Defaults to matcher function's ``__qualname__`` (for example,
        ``IPCompleter.file_matcher`` for the built-in matched defined
        as a ``file_matcher`` method of the ``IPCompleter`` class).
    api_version: Optional[int]
        version of the Matcher API used by this matcher.
        Currently supported values are 1 and 2.
        Defaults to 1.
    """

    def wrapper(func: Matcher):
        func.matcher_priority = priority or 0  # type: ignore
        func.matcher_identifier = identifier or func.__qualname__  # type: ignore
        func.matcher_api_version = api_version  # type: ignore
        if TYPE_CHECKING:
            if api_version == 1:
                func = cast(MatcherAPIv1, func)
            elif api_version == 2:
                func = cast(MatcherAPIv2, func)
        return func

    return wrapper


def _get_matcher_priority(matcher: Matcher):
    return getattr(matcher, "matcher_priority", 0)


def _get_matcher_id(matcher: Matcher):
    return getattr(matcher, "matcher_identifier", matcher.__qualname__)


def _get_matcher_api_version(matcher):
    return getattr(matcher, "matcher_api_version", 1)


context_matcher = partial(completion_matcher, api_version=2)


_IC = Iterable[Completion]


def _deduplicate_completions(text: str, completions: _IC)-> _IC:
    """
    Deduplicate a set of completions.

    .. warning::

        Unstable

        This function is unstable, API may change without warning.

    Parameters
    ----------
    text : str
        text that should be completed.
    completions : Iterator[Completion]
        iterator over the completions to deduplicate

    Yields
    ------
    `Completions` objects
    Completions coming from multiple sources, may be different but end up having
    the same effect when applied to ``text``. If this is the case, this will
    consider completions as equal and only emit the first encountered.
    Not folded in `completions()` yet for debugging purpose, and to detect when
    the IPython completer does return things that Jedi does not, but should be
    at some point.
    """
    completions = list(completions)
    if not completions:
        return

    new_start = min(c.start for c in completions)
    new_end = max(c.end for c in completions)

    seen = set()
    for c in completions:
        new_text = text[new_start:c.start] + c.text + text[c.end:new_end]
        if new_text not in seen:
            yield c
            seen.add(new_text)


def rectify_completions(text: str, completions: _IC, *, _debug: bool = False) -> _IC:
    """
    Rectify a set of completions to all have the same ``start`` and ``end``

    .. warning::

        Unstable

        This function is unstable, API may change without warning.
        It will also raise unless use in proper context manager.

    Parameters
    ----------
    text : str
        text that should be completed.
    completions : Iterator[Completion]
        iterator over the completions to rectify
    _debug : bool
        Log failed completion

    Notes
    -----
    :any:`jedi.api.classes.Completion` s returned by Jedi may not have the same start and end, though
    the Jupyter Protocol requires them to behave like so. This will readjust
    the completion to have the same ``start`` and ``end`` by padding both
    extremities with surrounding text.

    During stabilisation should support a ``_debug`` option to log which
    completion are return by the IPython completer and not found in Jedi in
    order to make upstream bug report.
    """
    warnings.warn("`rectify_completions` is a provisional API (as of IPython 6.0). "
                 "It may change without warnings. "
                 "Use in corresponding context manager.",
                  category=ProvisionalCompleterWarning, stacklevel=2)

    completions = list(completions)
    if not completions:
        return
    starts = (c.start for c in completions)
    ends = (c.end for c in completions)

    new_start = min(starts)
    new_end = max(ends)

    seen_jedi = set()
    seen_python_matches = set()
    for c in completions:
        new_text = text[new_start:c.start] + c.text + text[c.end:new_end]
        if c._origin == 'jedi':
            seen_jedi.add(new_text)
        elif c._origin == "IPCompleter.python_matcher":
            seen_python_matches.add(new_text)
        yield Completion(new_start, new_end, new_text, type=c.type, _origin=c._origin, signature=c.signature)
    diff = seen_python_matches.difference(seen_jedi)
    if diff and _debug:
        print('IPython.python matches have extras:', diff)


if sys.platform == 'win32':
    DELIMS = ' \t\n`!@#$^&*()=+[{]}|;\'",<>?'
else:
    DELIMS = ' \t\n`!@#$^&*()=+[{]}\\|;:\'",<>?'

GREEDY_DELIMS = ' =\r\n'


class CompletionSplitter:
    """An object to split an input line in a manner similar to readline.

    By having our own implementation, we can expose readline-like completion in
    a uniform manner to all frontends.  This object only needs to be given the
    line of text to be split and the cursor position on said line, and it
    returns the 'word' to be completed on at the cursor after splitting the
    entire line.

    What characters are used as splitting delimiters can be controlled by
    setting the ``delims`` attribute (this is a property that internally
    automatically builds the necessary regular expression)"""

    # Private interface

    # A string of delimiter characters.  The default value makes sense for
    # IPython's most typical usage patterns.
    _delims = DELIMS

    # The expression (a normal string) to be compiled into a regular expression
    # for actual splitting.  We store it as an attribute mostly for ease of
    # debugging, since this type of code can be so tricky to debug.
    _delim_expr = None

    # The regular expression that does the actual splitting
    _delim_re = None

    def __init__(self, delims=None):
        delims = CompletionSplitter._delims if delims is None else delims
        self.delims = delims

    @property
    def delims(self):
        """Return the string of delimiter characters."""
        return self._delims

    @delims.setter
    def delims(self, delims):
        """Set the delimiters for line splitting."""
        expr = '[' + ''.join('\\'+ c for c in delims) + ']'
        self._delim_re = re.compile(expr)
        self._delims = delims
        self._delim_expr = expr

    def split_line(self, line, cursor_pos=None):
        """Split a line of text with a cursor at the given position.
        """
        cut_line = line if cursor_pos is None else line[:cursor_pos]
        return self._delim_re.split(cut_line)[-1]



class Completer(Configurable):

    greedy = Bool(
        False,
        help="""Activate greedy completion.

        .. deprecated:: 8.8
            Use :std:configtrait:`Completer.evaluation` and :std:configtrait:`Completer.auto_close_dict_keys` instead.

        When enabled in IPython 8.8 or newer, changes configuration as follows:

        - ``Completer.evaluation = 'unsafe'``
        - ``Completer.auto_close_dict_keys = True``
        """,
    ).tag(config=True)

    evaluation = Enum(
        ("forbidden", "minimal", "limited", "unsafe", "dangerous"),
        default_value="limited",
        help="""Policy for code evaluation under completion.

        Successive options allow to enable more eager evaluation for better
        completion suggestions, including for nested dictionaries, nested lists,
        or even results of function calls.
        Setting ``unsafe`` or higher can lead to evaluation of arbitrary user
        code on :kbd:`Tab` with potentially unwanted or dangerous side effects.

        Allowed values are:

        - ``forbidden``: no evaluation of code is permitted,
        - ``minimal``: evaluation of literals and access to built-in namespace;
          no item/attribute evaluation, no access to locals/globals,
          no evaluation of any operations or comparisons.
        - ``limited``: access to all namespaces, evaluation of hard-coded methods
          (for example: :any:`dict.keys`, :any:`object.__getattr__`,
          :any:`object.__getitem__`) on allow-listed objects (for example:
          :any:`dict`, :any:`list`, :any:`tuple`, ``pandas.Series``),
        - ``unsafe``: evaluation of all methods and function calls but not of
          syntax with side-effects like `del x`,
        - ``dangerous``: completely arbitrary evaluation; does not support auto-import.

        To override specific elements of the policy, you can use ``policy_overrides`` trait.
        """,
    ).tag(config=True)

    use_jedi = Bool(default_value=JEDI_INSTALLED,
                    help="Experimental: Use Jedi to generate autocompletions. "
                    "Default to True if jedi is installed.").tag(config=True)

    jedi_compute_type_timeout = Int(default_value=400,
        help="""Experimental: restrict time (in milliseconds) during which Jedi can compute types.
        Set to 0 to stop computing types. Non-zero value lower than 100ms may hurt
        performance by preventing jedi to build its cache.
        """).tag(config=True)

    debug = Bool(default_value=False,
                 help='Enable debug for the Completer. Mostly print extra '
                      'information for experimental jedi integration.')\
                      .tag(config=True)

    backslash_combining_completions = Bool(True,
        help="Enable unicode completions, e.g. \\alpha<tab> . "
             "Includes completion of latex commands, unicode names, and expanding "
             "unicode characters back to latex commands.").tag(config=True)

    auto_close_dict_keys = Bool(
        False,
        help="""
        Enable auto-closing dictionary keys.

        When enabled string keys will be suffixed with a final quote
        (matching the opening quote), tuple keys will also receive a
        separating comma if needed, and keys which are final will
        receive a closing bracket (``]``).
        """,
    ).tag(config=True)

    policy_overrides = DictTrait(
        default_value={},
        key_trait=Unicode(),
        help="""Overrides for policy evaluation.

        For example, to enable auto-import on completion specify:

        .. code-block::

            ipython --Completer.policy_overrides='{"allow_auto_import": True}' --Completer.use_jedi=False

        """,
    ).tag(config=True)

    auto_import_method = DottedObjectName(
        default_value="importlib.import_module",
        allow_none=True,
        help="""\
        Provisional:
              This is a provisional API in IPython 9.3, it may change without warnings.

        A fully qualified path to an auto-import method for use by completer.
        The function should take a single string and return `ModuleType` and
        can raise `ImportError` exception if module is not found.

        The default auto-import implementation does not populate the user namespace with the imported module.
        """,
    ).tag(config=True)

    def __init__(self, namespace=None, global_namespace=None, **kwargs):
        """Create a new completer for the command line.

        Completer(namespace=ns, global_namespace=ns2) -> completer instance.

        If unspecified, the default namespace where completions are performed
        is __main__ (technically, __main__.__dict__). Namespaces should be
        given as dictionaries.

        An optional second namespace can be given.  This allows the completer
        to handle cases where both the local and global scopes need to be
        distinguished.
        """

        # Don't bind to namespace quite yet, but flag whether the user wants a
        # specific namespace or to use __main__.__dict__. This will allow us
        # to bind to __main__.__dict__ at completion time, not now.
        if namespace is None:
            self.use_main_ns = True
        else:
            self.use_main_ns = False
            self.namespace = namespace

        # The global namespace, if given, can be bound directly
        if global_namespace is None:
            self.global_namespace = {}
        else:
            self.global_namespace = global_namespace

        self.custom_matchers = []

        super(Completer, self).__init__(**kwargs)

    def complete(self, text, state):
        """Return the next possible completion for 'text'.

        This is called successively with state == 0, 1, 2, ... until it
        returns None.  The completion should begin with 'text'.

        """
        if self.use_main_ns:
            self.namespace = __main__.__dict__

        if state == 0:
            if "." in text:
                self.matches = self.attr_matches(text)
            else:
                self.matches = self.global_matches(text)
        try:
            return self.matches[state]
        except IndexError:
            return None

    def global_matches(self, text):
        """Compute matches when text is a simple name.

        Return a list of all keywords, built-in functions and names currently
        defined in self.namespace or self.global_namespace that match.

        """
        matches = []
        match_append = matches.append
        n = len(text)
        for lst in [
            keyword.kwlist,
            builtin_mod.__dict__.keys(),
            list(self.namespace.keys()),
            list(self.global_namespace.keys()),
        ]:
            for word in lst:
                if word[:n] == text and word != "__builtins__":
                    match_append(word)

        snake_case_re = re.compile(r"[^_]+(_[^_]+)+?\Z")
        for lst in [list(self.namespace.keys()), list(self.global_namespace.keys())]:
            shortened = {
                "_".join([sub[0] for sub in word.split("_")]): word
                for word in lst
                if snake_case_re.match(word)
            }
            for word in shortened.keys():
                if word[:n] == text and word != "__builtins__":
                    match_append(shortened[word])
        return matches

    def attr_matches(self, text):
        """Compute matches when text contains a dot.

        Assuming the text is of the form NAME.NAME....[NAME], and is
        evaluatable in self.namespace or self.global_namespace, it will be
        evaluated and its attributes (as revealed by dir()) are used as
        possible completions.  (For class instances, class members are
        also considered.)

        WARNING: this can still invoke arbitrary C code, if an object
        with a __getattr__ hook is evaluated.

        """
        return self._attr_matches(text)[0]

    # we simple attribute matching with normal identifiers.
    _ATTR_MATCH_RE = re.compile(r"(.+)\.(\w*)$")

    def _strip_code_before_operator(self, code: str) -> str:
        o_parens = {"(", "[", "{"}
        c_parens = {")", "]", "}"}

        # Dry-run tokenize to catch errors
        try:
            _ = list(tokenize.generate_tokens(iter(code.splitlines()).__next__))
        except tokenize.TokenError:
            # Try trimming the expression and retrying
            trimmed_code = self._trim_expr(code)
            try:
                _ = list(
                    tokenize.generate_tokens(iter(trimmed_code.splitlines()).__next__)
                )
                code = trimmed_code
            except tokenize.TokenError:
                return code

        tokens = _parse_tokens(code)
        encountered_operator = False
        after_operator = []
        nesting_level = 0

        for t in tokens:
            if t.type == tokenize.OP:
                if t.string in o_parens:
                    nesting_level += 1
                elif t.string in c_parens:
                    nesting_level -= 1
                elif t.string != "." and nesting_level == 0:
                    encountered_operator = True
                    after_operator = []
                    continue

            if encountered_operator:
                after_operator.append(t.string)

        if encountered_operator:
            return "".join(after_operator)
        else:
            return code

    def _attr_matches(
        self, text: str, include_prefix: bool = True
    ) -> tuple[Sequence[str], str]:
        m2 = self._ATTR_MATCH_RE.match(text)
        if not m2:
            return [], ""
        expr, attr = m2.group(1, 2)
        try:
            expr = self._strip_code_before_operator(expr)
        except tokenize.TokenError:
            pass

        obj = self._evaluate_expr(expr)
        if obj is not_found:
            return [], ""

        if self.limit_to__all__ and hasattr(obj, '__all__'):
            words = get__all__entries(obj)
        else:
            words = dir2(obj)

        try:
            words = generics.complete_object(obj, words)
        except TryNext:
            pass
        except AssertionError:
            raise
        except Exception:
            # Silence errors from completion function
            pass
        # Build match list to return
        n = len(attr)

        # Note: ideally we would just return words here and the prefix
        # reconciliator would know that we intend to append to rather than
        # replace the input text; this requires refactoring to return range
        # which ought to be replaced (as does jedi).
        if include_prefix:
            tokens = _parse_tokens(expr)
            rev_tokens = reversed(tokens)
            skip_over = {tokenize.ENDMARKER, tokenize.NEWLINE}
            name_turn = True

            parts = []
            for token in rev_tokens:
                if token.type in skip_over:
                    continue
                if token.type == tokenize.NAME and name_turn:
                    parts.append(token.string)
                    name_turn = False
                elif (
                    token.type == tokenize.OP and token.string == "." and not name_turn
                ):
                    parts.append(token.string)
                    name_turn = True
                else:
                    # short-circuit if not empty nor name token
                    break

            prefix_after_space = "".join(reversed(parts))
        else:
            prefix_after_space = ""

        return (
            ["%s.%s" % (prefix_after_space, w) for w in words if w[:n] == attr],
            "." + attr,
        )

    def _trim_expr(self, code: str) -> str:
        """
        Trim the code until it is a valid expression and not a tuple;

        return the trimmed expression for guarded_eval.
        """
        while code:
            code = code[1:]
            try:
                res = ast.parse(code)
            except SyntaxError:
                continue

            assert res is not None
            if len(res.body) != 1:
                continue
            expr = res.body[0].value
            if isinstance(expr, ast.Tuple) and not code[-1] == ")":
                # we skip implicit tuple, like when trimming `fun(a,b`<completion>
                # as `a,b` would be a tuple, and we actually expect to get only `b`
                continue
            return code
        return ""

    def _evaluate_expr(self, expr):
        obj = not_found
        done = False
        while not done and expr:
            try:
                obj = guarded_eval(
                    expr,
                    EvaluationContext(
                        globals=self.global_namespace,
                        locals=self.namespace,
                        evaluation=self.evaluation,
                        auto_import=self._auto_import,
                        policy_overrides=self.policy_overrides,
                    ),
                )
                done = True
            except Exception as e:
                if self.debug:
                    print("Evaluation exception", e)
                # trim the expression to remove any invalid prefix
                # e.g. user starts `(d[`, so we get `expr = '(d'`,
                # where parenthesis is not closed.
                # TODO: make this faster by reusing parts of the computation?
                expr = self._trim_expr(expr)
        return obj

    @property
    def _auto_import(self):
        if self.auto_import_method is None:
            return None
        if not hasattr(self, "_auto_import_func"):
            self._auto_import_func = import_item(self.auto_import_method)
        return self._auto_import_func

def get__all__entries(obj):
    """returns the strings in the __all__ attribute"""
    try:
        words = getattr(obj, '__all__')
    except Exception:
        return []

    return [w for w in words if isinstance(w, str)]


class _DictKeyState(enum.Flag):
    """Represent state of the key match in context of other possible matches.

    - given `d1 = {'a': 1}` completion on `d1['<tab>` will yield `{'a': END_OF_ITEM}` as there is no tuple.
    - given `d2 = {('a', 'b'): 1}`: `d2['a', '<tab>` will yield `{'b': END_OF_TUPLE}` as there is no tuple members to add beyond `'b'`.
    - given `d3 = {('a', 'b'): 1}`: `d3['<tab>` will yield `{'a': IN_TUPLE}` as `'a'` can be added.
    - given `d4 = {'a': 1, ('a', 'b'): 2}`: `d4['<tab>` will yield `{'a': END_OF_ITEM & END_OF_TUPLE}`
    """

    BASELINE = 0
    END_OF_ITEM = enum.auto()
    END_OF_TUPLE = enum.auto()
    IN_TUPLE = enum.auto()


def _parse_tokens(c):
    """Parse tokens even if there is an error."""
    tokens = []
    token_generator = tokenize.generate_tokens(iter(c.splitlines()).__next__)
    while True:
        try:
            tokens.append(next(token_generator))
        except tokenize.TokenError:
            return tokens
        except StopIteration:
            return tokens


def _match_number_in_dict_key_prefix(prefix: str) -> Union[str, None]:
    """Match any valid Python numeric literal in a prefix of dictionary keys.

    References:
    - https://docs.python.org/3/reference/lexical_analysis.html#numeric-literals
    - https://docs.python.org/3/library/tokenize.html
    """
    if prefix[-1].isspace():
        # if user typed a space we do not have anything to complete
        # even if there was a valid number token before
        return None
    tokens = _parse_tokens(prefix)
    rev_tokens = reversed(tokens)
    skip_over = {tokenize.ENDMARKER, tokenize.NEWLINE}
    number = None
    for token in rev_tokens:
        if token.type in skip_over:
            continue
        if number is None:
            if token.type == tokenize.NUMBER:
                number = token.string
                continue
            else:
                # we did not match a number
                return None
        if token.type == tokenize.OP:
            if token.string == ",":
                break
            if token.string in {"+", "-"}:
                number = token.string + number
        else:
            return None
    return number


_INT_FORMATS = {
    "0b": bin,
    "0o": oct,
    "0x": hex,
}


def match_dict_keys(
    keys: list[Union[str, bytes, tuple[Union[str, bytes], ...]]],
    prefix: str,
    delims: str,
    extra_prefix: Optional[tuple[Union[str, bytes], ...]] = None,
) -> tuple[str, int, dict[str, _DictKeyState]]:
    """Used by dict_key_matches, matching the prefix to a list of keys

    Parameters
    ----------
    keys
        list of keys in dictionary currently being completed.
    prefix
        Part of the text already typed by the user. E.g. `mydict[b'fo`
    delims
        String of delimiters to consider when finding the current key.
    extra_prefix : optional
        Part of the text already typed in multi-key index cases. E.g. for
        `mydict['foo', "bar", 'b`, this would be `('foo', 'bar')`.

    Returns
    -------
    A tuple of three elements: ``quote``, ``token_start``, ``matched``, with
    ``quote`` being the quote that need to be used to close current string.
    ``token_start`` the position where the replacement should start occurring,
    ``matches`` a dictionary of replacement/completion keys on keys and values
        indicating whether the state.
    """
    prefix_tuple = extra_prefix if extra_prefix else ()

    prefix_tuple_size = sum(
        [
            # for pandas, do not count slices as taking space
            not isinstance(k, slice)
            for k in prefix_tuple
        ]
    )
    text_serializable_types = (str, bytes, int, float, slice)

    def filter_prefix_tuple(key):
        # Reject too short keys
        if len(key) <= prefix_tuple_size:
            return False
        # Reject keys which cannot be serialised to text
        for k in key:
            if not isinstance(k, text_serializable_types):
                return False
        # Reject keys that do not match the prefix
        for k, pt in zip(key, prefix_tuple):
            if k != pt and not isinstance(pt, slice):
                return False
        # All checks passed!
        return True

    filtered_key_is_final: dict[Union[str, bytes, int, float], _DictKeyState] = (
        defaultdict(lambda: _DictKeyState.BASELINE)
    )

    for k in keys:
        # If at least one of the matches is not final, mark as undetermined.
        # This can happen with `d = {111: 'b', (111, 222): 'a'}` where
        # `111` appears final on first match but is not final on the second.

        if isinstance(k, tuple):
            if filter_prefix_tuple(k):
                key_fragment = k[prefix_tuple_size]
                filtered_key_is_final[key_fragment] |= (
                    _DictKeyState.END_OF_TUPLE
                    if len(k) == prefix_tuple_size + 1
                    else _DictKeyState.IN_TUPLE
                )
        elif prefix_tuple_size > 0:
            # we are completing a tuple but this key is not a tuple,
            # so we should ignore it
            pass
        else:
            if isinstance(k, text_serializable_types):
                filtered_key_is_final[k] |= _DictKeyState.END_OF_ITEM

    filtered_keys = filtered_key_is_final.keys()

    if not prefix:
        return "", 0, {repr(k): v for k, v in filtered_key_is_final.items()}

    quote_match = re.search("(?:\"|')", prefix)
    is_user_prefix_numeric = False

    if quote_match:
        quote = quote_match.group()
        valid_prefix = prefix + quote
        try:
            prefix_str = literal_eval(valid_prefix)
        except Exception:
            return "", 0, {}
    else:
        # If it does not look like a string, let's assume
        # we are dealing with a number or variable.
        number_match = _match_number_in_dict_key_prefix(prefix)

        # We do not want the key matcher to suggest variable names so we yield:
        if number_match is None:
            # The alternative would be to assume that user forgort the quote
            # and if the substring matches, suggest adding it at the start.
            return "", 0, {}

        prefix_str = number_match
        is_user_prefix_numeric = True
        quote = ""

    pattern = '[^' + ''.join('\\' + c for c in delims) + ']*$'
    token_match = re.search(pattern, prefix, re.UNICODE)
    assert token_match is not None # silence mypy
    token_start = token_match.start()
    token_prefix = token_match.group()

    matched: dict[str, _DictKeyState] = {}

    str_key: Union[str, bytes]

    for key in filtered_keys:
        if isinstance(key, (int, float)):
            # User typed a number but this key is not a number.
            if not is_user_prefix_numeric:
                continue
            str_key = str(key)
            if isinstance(key, int):
                int_base = prefix_str[:2].lower()
                # if user typed integer using binary/oct/hex notation:
                if int_base in _INT_FORMATS:
                    int_format = _INT_FORMATS[int_base]
                    str_key = int_format(key)
        else:
            # User typed a string but this key is a number.
            if is_user_prefix_numeric:
                continue
            str_key = key
        try:
            if not str_key.startswith(prefix_str):
                continue
        except (AttributeError, TypeError, UnicodeError):
            # Python 3+ TypeError on b'a'.startswith('a') or vice-versa
            continue

        # reformat remainder of key to begin with prefix
        rem = str_key[len(prefix_str) :]
        # force repr wrapped in '
        rem_repr = repr(rem + '"') if isinstance(rem, str) else repr(rem + b'"')
        rem_repr = rem_repr[1 + rem_repr.index("'"):-2]
        if quote == '"':
            # The entered prefix is quoted with ",
            # but the match is quoted with '.
            # A contained " hence needs escaping for comparison:
            rem_repr = rem_repr.replace('"', '\\"')

        # then reinsert prefix from start of token
        match = "%s%s" % (token_prefix, rem_repr)

        matched[match] = filtered_key_is_final[key]
    return quote, token_start, matched


def cursor_to_position(text:str, line:int, column:int)->int:
    """
    Convert the (line,column) position of the cursor in text to an offset in a
    string.

    Parameters
    ----------
    text : str
        The text in which to calculate the cursor offset
    line : int
        Line of the cursor; 0-indexed
    column : int
        Column of the cursor 0-indexed

    Returns
    -------
    Position of the cursor in ``text``, 0-indexed.

    See Also
    --------
    position_to_cursor : reciprocal of this function

    """
    lines = text.split('\n')
    assert line <= len(lines), '{} <= {}'.format(str(line), str(len(lines)))

    return sum(len(line) + 1 for line in lines[:line]) + column


def position_to_cursor(text: str, offset: int) -> tuple[int, int]:
    """
    Convert the position of the cursor in text (0 indexed) to a line
    number(0-indexed) and a column number (0-indexed) pair

    Position should be a valid position in ``text``.

    Parameters
    ----------
    text : str
        The text in which to calculate the cursor offset
    offset : int
        Position of the cursor in ``text``, 0-indexed.

    Returns
    -------
    (line, column) : (int, int)
        Line of the cursor; 0-indexed, column of the cursor 0-indexed

    See Also
    --------
    cursor_to_position : reciprocal of this function

    """

    assert 0 <= offset <= len(text) , "0 <= %s <= %s" % (offset , len(text))

    before = text[:offset]
    blines = before.split('\n')  # ! splitnes trim trailing \n
    line = before.count('\n')
    col = len(blines[-1])
    return line, col


def _safe_isinstance(obj, module, class_name, *attrs):
    """Checks if obj is an instance of module.class_name if loaded
    """
    if module in sys.modules:
        m = sys.modules[module]
        for attr in [class_name, *attrs]:
            m = getattr(m, attr)
        return isinstance(obj, m)


@context_matcher()
def back_unicode_name_matcher(context: CompletionContext):
    """Match Unicode characters back to Unicode name

    Same as :any:`back_unicode_name_matches`, but adopted to new Matcher API.
    """
    fragment, matches = back_unicode_name_matches(context.text_until_cursor)
    return _convert_matcher_v1_result_to_v2(
        matches, type="unicode", fragment=fragment, suppress_if_matches=True
    )


def back_unicode_name_matches(text: str) -> tuple[str, Sequence[str]]:
    """Match Unicode characters back to Unicode name

    This does  ``☃`` -> ``\\snowman``

    Note that snowman is not a valid python3 combining character but will be expanded.
    Though it will not recombine back to the snowman character by the completion machinery.

    This will not either back-complete standard sequences like \\n, \\b ...

    .. deprecated:: 8.6
        You can use :meth:`back_unicode_name_matcher` instead.

    Returns
    =======

    Return a tuple with two elements:

    - The Unicode character that was matched (preceded with a backslash), or
        empty string,
    - a sequence (of 1), name for the match Unicode character, preceded by
        backslash, or empty if no match.
    """
    if len(text)<2:
        return '', ()
    maybe_slash = text[-2]
    if maybe_slash != '\\':
        return '', ()

    char = text[-1]
    # no expand on quote for completion in strings.
    # nor backcomplete standard ascii keys
    if char in string.ascii_letters or char in ('"',"'"):
        return '', ()
    try :
        unic = unicodedata.name(char)
        return '\\'+char,('\\'+unic,)
    except KeyError:
        pass
    return '', ()


@context_matcher()
def back_latex_name_matcher(context: CompletionContext) -> SimpleMatcherResult:
    """Match latex characters back to unicode name

    This does ``\\ℵ`` -> ``\\aleph``
    """

    text = context.text_until_cursor
    no_match = {
        "completions": [],
        "suppress": False,
    }

    if len(text)<2:
        return no_match
    maybe_slash = text[-2]
    if maybe_slash != '\\':
        return no_match

    char = text[-1]
    # no expand on quote for completion in strings.
    # nor backcomplete standard ascii keys
    if char in string.ascii_letters or char in ('"',"'"):
        return no_match
    try :
        latex = reverse_latex_symbol[char]
        # '\\' replace the \ as well
        return {
            "completions": [SimpleCompletion(text=latex, type="latex")],
            "suppress": True,
            "matched_fragment": "\\" + char,
        }
    except KeyError:
        pass

    return no_match

def _formatparamchildren(parameter) -> str:
    """
    Get parameter name and value from Jedi Private API

    Jedi does not expose a simple way to get `param=value` from its API.

    Parameters
    ----------
    parameter
        Jedi's function `Param`

    Returns
    -------
    A string like 'a', 'b=1', '*args', '**kwargs'

    """
    description = parameter.description
    if not description.startswith('param '):
        raise ValueError('Jedi function parameter description have change format.'
                         'Expected "param ...", found %r".' % description)
    return description[6:]

def _make_signature(completion)-> str:
    """
    Make the signature from a jedi completion

    Parameters
    ----------
    completion : jedi.Completion
        object does not complete a function type

    Returns
    -------
    a string consisting of the function signature, with the parenthesis but
    without the function name. example:
    `(a, *args, b=1, **kwargs)`

    """

    # it looks like this might work on jedi 0.17
    if hasattr(completion, 'get_signatures'):
        signatures = completion.get_signatures()
        if not signatures:
            return  '(?)'

        c0 = completion.get_signatures()[0]
        return '('+c0.to_string().split('(', maxsplit=1)[1]

    return '(%s)'% ', '.join([f for f in (_formatparamchildren(p) for signature in completion.get_signatures()
                                          for p in signature.defined_names()) if f])


_CompleteResult = dict[str, MatcherResult]


DICT_MATCHER_REGEX = re.compile(
    r"""(?x)
(  # match dict-referring - or any get item object - expression
    .+
)
\[   # open bracket
\s*  # and optional whitespace
# Capture any number of serializable objects (e.g. "a", "b", 'c')
# and slices
((?:(?:
    (?: # closed string
        [uUbB]?  # string prefix (r not handled)
        (?:
            '(?:[^']|(?<!\\)\\')*'
        |
            "(?:[^"]|(?<!\\)\\")*"
        )
    )
    |
        # capture integers and slices
        (?:[-+]?\d+)?(?::(?:[-+]?\d+)?){0,2}
    |
        # integer in bin/hex/oct notation
        0[bBxXoO]_?(?:\w|\d)+
    )
    \s*,\s*
)*)
((?:
    (?: # unclosed string
        [uUbB]?  # string prefix (r not handled)
        (?:
            '(?:[^']|(?<!\\)\\')*
            |
            "(?:[^"]|(?<!\\)\\")*
        )
    )
    |
        # unfinished integer
        (?:[-+]?\d+)
    |
        # integer in bin/hex/oct notation
        0[bBxXoO]_?(?:\w|\d)+
    )
)?
$
"""
)


def _convert_matcher_v1_result_to_v2_no_no(
    matches: Sequence[str],
    type: str,
) -> SimpleMatcherResult:
    """same as _convert_matcher_v1_result_to_v2 but fragment=None, and suppress_if_matches is False by construction"""
    return SimpleMatcherResult(
        completions=[SimpleCompletion(text=match, type=type) for match in matches],
        suppress=False,
    )


def _convert_matcher_v1_result_to_v2(
    matches: Sequence[str],
    type: str,
    fragment: Optional[str] = None,
    suppress_if_matches: bool = False,
) -> SimpleMatcherResult:
    """Utility to help with transition"""
    result = {
        "completions": [SimpleCompletion(text=match, type=type) for match in matches],
        "suppress": (True if matches else False) if suppress_if_matches else False,
    }
    if fragment is not None:
        result["matched_fragment"] = fragment
    return cast(SimpleMatcherResult, result)


class IPCompleter(Completer):
    """Extension of the completer class with IPython-specific features"""

    @observe('greedy')
    def _greedy_changed(self, change):
        """update the splitter and readline delims when greedy is changed"""
        if change["new"]:
            self.evaluation = "unsafe"
            self.auto_close_dict_keys = True
            self.splitter.delims = GREEDY_DELIMS
        else:
            self.evaluation = "limited"
            self.auto_close_dict_keys = False
            self.splitter.delims = DELIMS

    dict_keys_only = Bool(
        False,
        help="""
        Whether to show dict key matches only.

        (disables all matchers except for `IPCompleter.dict_key_matcher`).
        """,
    )

    suppress_competing_matchers = UnionTrait(
        [Bool(allow_none=True), DictTrait(Bool(None, allow_none=True))],
        default_value=None,
        help="""
        Whether to suppress completions from other *Matchers*.

        When set to ``None`` (default) the matchers will attempt to auto-detect
        whether suppression of other matchers is desirable. For example, at
        the beginning of a line followed by `%` we expect a magic completion
        to be the only applicable option, and after ``my_dict['`` we usually
        expect a completion with an existing dictionary key.

        If you want to disable this heuristic and see completions from all matchers,
        set ``IPCompleter.suppress_competing_matchers = False``.
        To disable the heuristic for specific matchers provide a dictionary mapping:
        ``IPCompleter.suppress_competing_matchers = {'IPCompleter.dict_key_matcher': False}``.

        Set ``IPCompleter.suppress_competing_matchers = True`` to limit
        completions to the set of matchers with the highest priority;
        this is equivalent to ``IPCompleter.merge_completions`` and
        can be beneficial for performance, but will sometimes omit relevant
        candidates from matchers further down the priority list.
        """,
    ).tag(config=True)

    merge_completions = Bool(
        True,
        help="""Whether to merge completion results into a single list

        If False, only the completion results from the first non-empty
        completer will be returned.

        As of version 8.6.0, setting the value to ``False`` is an alias for:
        ``IPCompleter.suppress_competing_matchers = True.``.
        """,
    ).tag(config=True)

    disable_matchers = ListTrait(
        Unicode(),
        help="""List of matchers to disable.

        The list should contain matcher identifiers (see :any:`completion_matcher`).
        """,
    ).tag(config=True)

    omit__names = Enum(
        (0, 1, 2),
        default_value=2,
        help="""Instruct the completer to omit private method names

        Specifically, when completing on ``object.<tab>``.

        When 2 [default]: all names that start with '_' will be excluded.

        When 1: all 'magic' names (``__foo__``) will be excluded.

        When 0: nothing will be excluded.
        """
    ).tag(config=True)
    limit_to__all__ = Bool(False,
        help="""
        DEPRECATED as of version 5.0.

        Instruct the completer to use __all__ for the completion

        Specifically, when completing on ``object.<tab>``.

        When True: only those names in obj.__all__ will be included.

        When False [default]: the __all__ attribute is ignored
        """,
    ).tag(config=True)

    profile_completions = Bool(
        default_value=False,
        help="If True, emit profiling data for completion subsystem using cProfile."
    ).tag(config=True)

    profiler_output_dir = Unicode(
        default_value=".completion_profiles",
        help="Template for path at which to output profile data for completions."
    ).tag(config=True)

    @observe('limit_to__all__')
    def _limit_to_all_changed(self, change):
        warnings.warn('`IPython.core.IPCompleter.limit_to__all__` configuration '
            'value has been deprecated since IPython 5.0, will be made to have '
            'no effects and then removed in future version of IPython.',
            UserWarning)

    def __init__(
        self, shell=None, namespace=None, global_namespace=None, config=None, **kwargs
    ):
        """IPCompleter() -> completer

        Return a completer object.

        Parameters
        ----------
        shell
            a pointer to the ipython shell itself.  This is needed
            because this completer knows about magic functions, and those can
            only be accessed via the ipython instance.
        namespace : dict, optional
            an optional dict where completions are performed.
        global_namespace : dict, optional
            secondary optional dict for completions, to
            handle cases (such as IPython embedded inside functions) where
            both Python scopes are visible.
        config : Config
            traitlet's config object
        **kwargs
            passed to super class unmodified.
        """

        self.magic_escape = ESC_MAGIC
        self.splitter = CompletionSplitter()

        # _greedy_changed() depends on splitter and readline being defined:
        super().__init__(
            namespace=namespace,
            global_namespace=global_namespace,
            config=config,
            **kwargs,
        )

        # List where completion matches will be stored
        self.matches = []
        self.shell = shell
        # Regexp to split filenames with spaces in them
        self.space_name_re = re.compile(r'([^\\] )')
        # Hold a local ref. to glob.glob for speed
        self.glob = glob.glob

        # Determine if we are running on 'dumb' terminals, like (X)Emacs
        # buffers, to avoid completion problems.
        term = os.environ.get('TERM','xterm')
        self.dumb_terminal = term in ['dumb','emacs']

        # Special handling of backslashes needed in win32 platforms
        if sys.platform == "win32":
            self.clean_glob = self._clean_glob_win32
        else:
            self.clean_glob = self._clean_glob

        #regexp to parse docstring for function signature
        self.docstring_sig_re = re.compile(r'^[\w|\s.]+\(([^)]*)\).*')
        self.docstring_kwd_re = re.compile(r'[\s|\[]*(\w+)(?:\s*=\s*.*)')
        #use this if positional argument name is also needed
        #= re.compile(r'[\s|\[]*(\w+)(?:\s*=?\s*.*)')

        self.magic_arg_matchers = [
            self.magic_config_matcher,
            self.magic_color_matcher,
        ]

        # This is set externally by InteractiveShell
        self.custom_completers = None

        # This is a list of names of unicode characters that can be completed
        # into their corresponding unicode value. The list is large, so we
        # lazily initialize it on first use. Consuming code should access this
        # attribute through the `@unicode_names` property.
        self._unicode_names = None

        self._backslash_combining_matchers = [
            self.latex_name_matcher,
            self.unicode_name_matcher,
            back_latex_name_matcher,
            back_unicode_name_matcher,
            self.fwd_unicode_matcher,
        ]

        if not self.backslash_combining_completions:
            for matcher in self._backslash_combining_matchers:
                self.disable_matchers.append(_get_matcher_id(matcher))

        if not self.merge_completions:
            self.suppress_competing_matchers = True

    @property
    def matchers(self) -> list[Matcher]:
        """All active matcher routines for completion"""
        if self.dict_keys_only:
            return [self.dict_key_matcher]

        if self.use_jedi:
            return [
                *self.custom_matchers,
                *self._backslash_combining_matchers,
                *self.magic_arg_matchers,
                self.custom_completer_matcher,
                self.magic_matcher,
                self._jedi_matcher,
                self.dict_key_matcher,
                self.file_matcher,
            ]
        else:
            return [
                *self.custom_matchers,
                *self._backslash_combining_matchers,
                *self.magic_arg_matchers,
                self.custom_completer_matcher,
                self.dict_key_matcher,
                self.magic_matcher,
                self.python_matcher,
                self.file_matcher,
                self.python_func_kw_matcher,
            ]

    def all_completions(self, text: str) -> list[str]:
        """
        Wrapper around the completion methods for the benefit of emacs.
        """
        prefix = text.rpartition('.')[0]
        with provisionalcompleter():
            return ['.'.join([prefix, c.text]) if prefix and self.use_jedi else c.text
                    for c in self.completions(text, len(text))]

        return self.complete(text)[1]

    def _clean_glob(self, text:str):
        return self.glob("%s*" % text)

    def _clean_glob_win32(self, text:str):
        return [f.replace("\\","/")
                for f in self.glob("%s*" % text)]

    @context_matcher()
    def file_matcher(self, context: CompletionContext) -> SimpleMatcherResult:
        """Match filenames, expanding ~USER type strings.

        Most of the seemingly convoluted logic in this completer is an
        attempt to handle filenames with spaces in them.  And yet it's not
        quite perfect, because Python's readline doesn't expose all of the
        GNU readline details needed for this to be done correctly.

        For a filename with a space in it, the printed completions will be
        only the parts after what's already been typed (instead of the
        full completions, as is normally done).  I don't think with the
        current (as of Python 2.3) Python readline it's possible to do
        better.
        """
        # TODO: add a heuristic for suppressing (e.g. if it has OS-specific delimiter,
        #  starts with `/home/`, `C:\`, etc)

        text = context.token

        # chars that require escaping with backslash - i.e. chars
        # that readline treats incorrectly as delimiters, but we
        # don't want to treat as delimiters in filename matching
        # when escaped with backslash
        if text.startswith('!'):
            text = text[1:]
            text_prefix = u'!'
        else:
            text_prefix = u''

        text_until_cursor = self.text_until_cursor
        # track strings with open quotes
        open_quotes = has_open_quotes(text_until_cursor)

        if '(' in text_until_cursor or '[' in text_until_cursor:
            lsplit = text
        else:
            try:
                # arg_split ~ shlex.split, but with unicode bugs fixed by us
                lsplit = arg_split(text_until_cursor)[-1]
            except ValueError:
                # typically an unmatched ", or backslash without escaped char.
                if open_quotes:
                    lsplit = text_until_cursor.split(open_quotes)[-1]
                else:
                    return {
                        "completions": [],
                        "suppress": False,
                    }
            except IndexError:
                # tab pressed on empty line
                lsplit = ""

        if not open_quotes and lsplit != protect_filename(lsplit):
            # if protectables are found, do matching on the whole escaped name
            has_protectables = True
            text0,text = text,lsplit
        else:
            has_protectables = False
            text = os.path.expanduser(text)

        if text == "":
            return {
                "completions": [
                    SimpleCompletion(
                        text=text_prefix + protect_filename(f), type="path"
                    )
                    for f in self.glob("*")
                ],
                "suppress": False,
            }

        # Compute the matches from the filesystem
        if sys.platform == 'win32':
            m0 = self.clean_glob(text)
        else:
            m0 = self.clean_glob(text.replace('\\', ''))

        if has_protectables:
            # If we had protectables, we need to revert our changes to the
            # beginning of filename so that we don't double-write the part
            # of the filename we have so far
            len_lsplit = len(lsplit)
            matches = [text_prefix + text0 +
                       protect_filename(f[len_lsplit:]) for f in m0]
        else:
            if open_quotes:
                # if we have a string with an open quote, we don't need to
                # protect the names beyond the quote (and we _shouldn't_, as
                # it would cause bugs when the filesystem call is made).
                matches = m0 if sys.platform == "win32" else\
                    [protect_filename(f, open_quotes) for f in m0]
            else:
                matches = [text_prefix +
                           protect_filename(f) for f in m0]

        # Mark directories in input list by appending '/' to their names.
        return {
            "completions": [
                SimpleCompletion(text=x + "/" if os.path.isdir(x) else x, type="path")
                for x in matches
            ],
            "suppress": False,
        }

    @context_matcher()
    def magic_matcher(self, context: CompletionContext) -> SimpleMatcherResult:
        """Match magics."""

        # Get all shell magics now rather than statically, so magics loaded at
        # runtime show up too.
        text = context.token
        lsm = self.shell.magics_manager.lsmagic()
        line_magics = lsm['line']
        cell_magics = lsm['cell']
        pre = self.magic_escape
        pre2 = pre+pre

        explicit_magic = text.startswith(pre)

        # Completion logic:
        # - user gives %%: only do cell magics
        # - user gives %: do both line and cell magics
        # - no prefix: do both
        # In other words, line magics are skipped if the user gives %% explicitly
        #
        # We also exclude magics that match any currently visible names:
        # https://github.com/ipython/ipython/issues/4877, unless the user has
        # typed a %:
        # https://github.com/ipython/ipython/issues/10754
        bare_text = text.lstrip(pre)
        global_matches = self.global_matches(bare_text)
        if not explicit_magic:
            def matches(magic):
                """
                Filter magics, in particular remove magics that match
                a name present in global namespace.
                """
                return ( magic.startswith(bare_text) and
                         magic not in global_matches )
        else:
            def matches(magic):
                return magic.startswith(bare_text)

        completions = [pre2 + m for m in cell_magics if matches(m)]
        if not text.startswith(pre2):
            completions += [pre + m for m in line_magics if matches(m)]

        is_magic_prefix = len(text) > 0 and text[0] == "%"

        return {
            "completions": [
                SimpleCompletion(text=comp, type="magic") for comp in completions
            ],
            "suppress": is_magic_prefix and len(completions) > 0,
        }

    @context_matcher()
    def magic_config_matcher(self, context: CompletionContext) -> SimpleMatcherResult:
        """Match class names and attributes for %config magic."""
        # NOTE: uses `line_buffer` equivalent for compatibility
        matches = self.magic_config_matches(context.line_with_cursor)
        return _convert_matcher_v1_result_to_v2_no_no(matches, type="param")

    def magic_config_matches(self, text: str) -> list[str]:
        """Match class names and attributes for %config magic.

        .. deprecated:: 8.6
            You can use :meth:`magic_config_matcher` instead.
        """
        texts = text.strip().split()

        if len(texts) > 0 and (texts[0] == 'config' or texts[0] == '%config'):
            # get all configuration classes
            classes = sorted(set([ c for c in self.shell.configurables
                                   if c.__class__.class_traits(config=True)
                                   ]), key=lambda x: x.__class__.__name__)
            classnames = [ c.__class__.__name__ for c in classes ]

            # return all classnames if config or %config is given
            if len(texts) == 1:
                return classnames

            # match classname
            classname_texts = texts[1].split('.')
            classname = classname_texts[0]
            classname_matches = [ c for c in classnames
                                  if c.startswith(classname) ]

            # return matched classes or the matched class with attributes
            if texts[1].find('.') < 0:
                return classname_matches
            elif len(classname_matches) == 1 and \
                            classname_matches[0] == classname:
                cls = classes[classnames.index(classname)].__class__
                help = cls.class_get_help()
                # strip leading '--' from cl-args:
                help = re.sub(re.compile(r'^--', re.MULTILINE), '', help)
                return [ attr.split('=')[0]
                         for attr in help.strip().splitlines()
                         if attr.startswith(texts[1]) ]
        return []

    @context_matcher()
    def magic_color_matcher(self, context: CompletionContext) -> SimpleMatcherResult:
        """Match color schemes for %colors magic."""
        text = context.line_with_cursor
        texts = text.split()
        if text.endswith(' '):
            # .split() strips off the trailing whitespace. Add '' back
            # so that: '%colors ' -> ['%colors', '']
            texts.append('')

        if len(texts) == 2 and (texts[0] == 'colors' or texts[0] == '%colors'):
            prefix = texts[1]
            return SimpleMatcherResult(
                completions=[
                    SimpleCompletion(color, type="param")
                    for color in theme_table.keys()
                    if color.startswith(prefix)
                ],
                suppress=False,
            )
        return SimpleMatcherResult(
            completions=[],
            suppress=False,
        )

    @context_matcher(identifier="IPCompleter.jedi_matcher")
    def _jedi_matcher(self, context: CompletionContext) -> _JediMatcherResult:
        matches = self._jedi_matches(
            cursor_column=context.cursor_position,
            cursor_line=context.cursor_line,
            text=context.full_text,
        )
        return {
            "completions": matches,
            # static analysis should not suppress other matchers
            "suppress": False,
        }

    def _jedi_matches(
        self, cursor_column: int, cursor_line: int, text: str
    ) -> Iterator[_JediCompletionLike]:
        """
        Return a list of :any:`jedi.api.Completion`\\s object from a ``text`` and
        cursor position.

        Parameters
        ----------
        cursor_column : int
            column position of the cursor in ``text``, 0-indexed.
        cursor_line : int
            line position of the cursor in ``text``, 0-indexed
        text : str
            text to complete

        Notes
        -----
        If ``IPCompleter.debug`` is ``True`` may return a :any:`_FakeJediCompletion`
        object containing a string with the Jedi debug information attached.

        .. deprecated:: 8.6
            You can use :meth:`_jedi_matcher` instead.
        """
        namespaces = [self.namespace]
        if self.global_namespace is not None:
            namespaces.append(self.global_namespace)

        completion_filter = lambda x:x
        offset = cursor_to_position(text, cursor_line, cursor_column)
        # filter output if we are completing for object members
        if offset:
            pre = text[offset-1]
            if pre == '.':
                if self.omit__names == 2:
                    completion_filter = lambda c:not c.name.startswith('_')
                elif self.omit__names == 1:
                    completion_filter = lambda c:not (c.name.startswith('__') and c.name.endswith('__'))
                elif self.omit__names == 0:
                    completion_filter = lambda x:x
                else:
                    raise ValueError("Don't understand self.omit__names == {}".format(self.omit__names))

        interpreter = jedi.Interpreter(text[:offset], namespaces)
        try_jedi = True

        try:
            # find the first token in the current tree -- if it is a ' or " then we are in a string
            completing_string = False
            try:
                first_child = next(c for c in interpreter._get_module().tree_node.children if hasattr(c, 'value'))
            except StopIteration:
                pass
            else:
                # note the value may be ', ", or it may also be ''' or """, or
                # in some cases, """what/you/typed..., but all of these are
                # strings.
                completing_string = len(first_child.value) > 0 and first_child.value[0] in {"'", '"'}

            # if we are in a string jedi is likely not the right candidate for
            # now. Skip it.
            try_jedi = not completing_string
        except Exception as e:
            # many of things can go wrong, we are using private API just don't crash.
            if self.debug:
                print("Error detecting if completing a non-finished string :", e, '|')

        if not try_jedi:
            return iter([])
        try:
            return filter(completion_filter, interpreter.complete(column=cursor_column, line=cursor_line + 1))
        except Exception as e:
            if self.debug:
                return iter(
                    [
                        _FakeJediCompletion(
                            'Oops Jedi has crashed, please report a bug with the following:\n"""\n%s\ns"""'
                            % (e)
                        )
                    ]
                )
            else:
                return iter([])

    class _CompletionContextType(enum.Enum):
        ATTRIBUTE = "attribute"  # For attribute completion
        GLOBAL = "global"  # For global completion

    def _determine_completion_context(self, line):
        """
        Determine whether the cursor is in an attribute or global completion context.
        """
        # Cursor in string/comment → GLOBAL.
        is_string, is_in_expression = self._is_in_string_or_comment(line)
        if is_string and not is_in_expression:
            return self._CompletionContextType.GLOBAL

        # If we're in a template string expression, handle specially
        if is_string and is_in_expression:
            # Extract the expression part - look for the last { that isn't closed
            expr_start = line.rfind("{")
            if expr_start >= 0:
                # We're looking at the expression inside a template string
                expr = line[expr_start + 1 :]
                # Recursively determine the context of the expression
                return self._determine_completion_context(expr)

        # Handle plain number literals - should be global context
        # Ex: 3. -42.14 but not 3.1.
        if re.search(r"(?<!\w)(?<!\d\.)([-+]?\d+\.(\d+)?)(?!\w)$", line):
            return self._CompletionContextType.GLOBAL

        # Handle all other attribute matches np.ran, d[0].k, (a,b).count
        chain_match = re.search(r".*(.+\.(?:[a-zA-Z]\w*)?)$", line)
        if chain_match:
            return self._CompletionContextType.ATTRIBUTE

        return self._CompletionContextType.GLOBAL

    def _is_in_string_or_comment(self, text):
        """
        Determine if the cursor is inside a string or comment.
        Returns (is_string, is_in_expression) tuple:
        - is_string: True if in any kind of string
        - is_in_expression: True if inside an f-string/t-string expression
        """
        in_single_quote = False
        in_double_quote = False
        in_triple_single = False
        in_triple_double = False
        in_template_string = False  # Covers both f-strings and t-strings
        in_expression = False  # For expressions in f/t-strings
        expression_depth = 0  # Track nested braces in expressions
        i = 0

        while i < len(text):
            # Check for f-string or t-string start
            if (
                i + 1 < len(text)
                and text[i] in ("f", "t")
                and (text[i + 1] == '"' or text[i + 1] == "'")
                and not (
                    in_single_quote
                    or in_double_quote
                    or in_triple_single
                    or in_triple_double
                )
            ):
                in_template_string = True
                i += 1  # Skip the 'f' or 't'

            # Handle triple quotes
            if i + 2 < len(text):
                if (
                    text[i : i + 3] == '"""'
                    and not in_single_quote
                    and not in_triple_single
                ):
                    in_triple_double = not in_triple_double
                    if not in_triple_double:
                        in_template_string = False
                    i += 3
                    continue
                if (
                    text[i : i + 3] == "'''"
                    and not in_double_quote
                    and not in_triple_double
                ):
                    in_triple_single = not in_triple_single
                    if not in_triple_single:
                        in_template_string = False
                    i += 3
                    continue

            # Handle escapes
            if text[i] == "\\" and i + 1 < len(text):
                i += 2
                continue

            # Handle nested braces within f-strings
            if in_template_string:
                # Special handling for consecutive opening braces
                if i + 1 < len(text) and text[i : i + 2] == "{{":
                    i += 2
                    continue

                # Detect start of an expression
                if text[i] == "{":
                    # Only increment depth and mark as expression if not already in an expression
                    # or if we're at a top-level nested brace
                    if not in_expression or (in_expression and expression_depth == 0):
                        in_expression = True
                        expression_depth += 1
                    i += 1
                    continue

                # Detect end of an expression
                if text[i] == "}":
                    expression_depth -= 1
                    if expression_depth <= 0:
                        in_expression = False
                        expression_depth = 0
                    i += 1
                    continue

            in_triple_quote = in_triple_single or in_triple_double

            # Handle quotes - also reset template string when closing quotes are encountered
            if text[i] == '"' and not in_single_quote and not in_triple_quote:
                in_double_quote = not in_double_quote
                if not in_double_quote and not in_triple_quote:
                    in_template_string = False
            elif text[i] == "'" and not in_double_quote and not in_triple_quote:
                in_single_quote = not in_single_quote
                if not in_single_quote and not in_triple_quote:
                    in_template_string = False

            # Check for comment
            if text[i] == "#" and not (
                in_single_quote or in_double_quote or in_triple_quote
            ):
                return True, False

            i += 1

        is_string = (
            in_single_quote or in_double_quote or in_triple_single or in_triple_double
        )

        # Return tuple (is_string, is_in_expression)
        return (
            is_string or (in_template_string and not in_expression),
            in_expression and expression_depth > 0,
        )

    @context_matcher()
    def python_matcher(self, context: CompletionContext) -> SimpleMatcherResult:
        """Match attributes or global python names"""
        text = context.text_until_cursor
        completion_type = self._determine_completion_context(text)
        if completion_type == self._CompletionContextType.ATTRIBUTE:
            try:
                matches, fragment = self._attr_matches(text, include_prefix=False)
                if text.endswith(".") and self.omit__names:
                    if self.omit__names == 1:
                        # true if txt is _not_ a __ name, false otherwise:
                        no__name = lambda txt: re.match(r".*\.__.*?__", txt) is None
                    else:
                        # true if txt is _not_ a _ name, false otherwise:
                        no__name = (
                            lambda txt: re.match(r"\._.*?", txt[txt.rindex(".") :])
                            is None
                        )
                    matches = filter(no__name, matches)
                return _convert_matcher_v1_result_to_v2(
                    matches, type="attribute", fragment=fragment
                )
            except NameError:
                # catches <undefined attributes>.<tab>
                return SimpleMatcherResult(completions=[], suppress=False)
        else:
            matches = self.global_matches(context.token)
            # TODO: maybe distinguish between functions, modules and just "variables"
            return SimpleMatcherResult(
                completions=[
                    SimpleCompletion(text=match, type="variable") for match in matches
                ],
                suppress=False,
            )

    @completion_matcher(api_version=1)
    def python_matches(self, text: str) -> Iterable[str]:
        """Match attributes or global python names.

        .. deprecated:: 8.27
            You can use :meth:`python_matcher` instead."""
        if "." in text:
            try:
                matches = self.attr_matches(text)
                if text.endswith('.') and self.omit__names:
                    if self.omit__names == 1:
                        # true if txt is _not_ a __ name, false otherwise:
                        no__name = (lambda txt:
                                    re.match(r'.*\.__.*?__',txt) is None)
                    else:
                        # true if txt is _not_ a _ name, false otherwise:
                        no__name = (lambda txt:
                                    re.match(r'\._.*?',txt[txt.rindex('.'):]) is None)
                    matches = filter(no__name, matches)
            except NameError:
                # catches <undefined attributes>.<tab>
                matches = []
        else:
            matches = self.global_matches(text)
        return matches

    def _default_arguments_from_docstring(self, doc):
        """Parse the first line of docstring for call signature.

        Docstring should be of the form 'min(iterable[, key=func])\n'.
        It can also parse cython docstring of the form
        'Minuit.migrad(self, int ncall=10000, resume=True, int nsplit=1)'.
        """
        if doc is None:
            return []

        #care only the firstline
        line = doc.lstrip().splitlines()[0]

        #p = re.compile(r'^[\w|\s.]+\(([^)]*)\).*')
        #'min(iterable[, key=func])\n' -> 'iterable[, key=func]'
        sig = self.docstring_sig_re.search(line)
        if sig is None:
            return []
        # iterable[, key=func]' -> ['iterable[' ,' key=func]']
        sig = sig.groups()[0].split(',')
        ret = []
        for s in sig:
            #re.compile(r'[\s|\[]*(\w+)(?:\s*=\s*.*)')
            ret += self.docstring_kwd_re.findall(s)
        return ret

    def _default_arguments(self, obj):
        """Return the list of default arguments of obj if it is callable,
        or empty list otherwise."""
        call_obj = obj
        ret = []
        if inspect.isbuiltin(obj):
            pass
        elif not (inspect.isfunction(obj) or inspect.ismethod(obj)):
            if inspect.isclass(obj):
                #for cython embedsignature=True the constructor docstring
                #belongs to the object itself not __init__
                ret += self._default_arguments_from_docstring(
                            getattr(obj, '__doc__', ''))
                # for classes, check for __init__,__new__
                call_obj = (getattr(obj, '__init__', None) or
                       getattr(obj, '__new__', None))
            # for all others, check if they are __call__able
            elif hasattr(obj, '__call__'):
                call_obj = obj.__call__
        ret += self._default_arguments_from_docstring(
                 getattr(call_obj, '__doc__', ''))

        _keeps = (inspect.Parameter.KEYWORD_ONLY,
                  inspect.Parameter.POSITIONAL_OR_KEYWORD)

        try:
            sig = inspect.signature(obj)
            ret.extend(k for k, v in sig.parameters.items() if
                       v.kind in _keeps)
        except ValueError:
            pass

        return list(set(ret))

    @context_matcher()
    def python_func_kw_matcher(self, context: CompletionContext) -> SimpleMatcherResult:
        """Match named parameters (kwargs) of the last open function."""
        matches = self.python_func_kw_matches(context.token)
        return _convert_matcher_v1_result_to_v2_no_no(matches, type="param")

    def python_func_kw_matches(self, text):
        """Match named parameters (kwargs) of the last open function.

        .. deprecated:: 8.6
            You can use :meth:`python_func_kw_matcher` instead.
        """

        if "." in text: # a parameter cannot be dotted
            return []
        try: regexp = self.__funcParamsRegex
        except AttributeError:
            regexp = self.__funcParamsRegex = re.compile(r'''
                '.*?(?<!\\)' |    # single quoted strings or
                ".*?(?<!\\)" |    # double quoted strings or
                \w+          |    # identifier
                \S                # other characters
                ''', re.VERBOSE | re.DOTALL)
        # 1. find the nearest identifier that comes before an unclosed
        # parenthesis before the cursor
        # e.g. for "foo (1+bar(x), pa<cursor>,a=1)", the candidate is "foo"
        tokens = regexp.findall(self.text_until_cursor)
        iterTokens = reversed(tokens)
        openPar = 0

        for token in iterTokens:
            if token == ')':
                openPar -= 1
            elif token == '(':
                openPar += 1
                if openPar > 0:
                    # found the last unclosed parenthesis
                    break
        else:
            return []
        # 2. Concatenate dotted names ("foo.bar" for "foo.bar(x, pa" )
        ids = []
        isId = re.compile(r'\w+$').match

        while True:
            try:
                ids.append(next(iterTokens))
                if not isId(ids[-1]):
                    ids.pop()
                    break
                if not next(iterTokens) == '.':
                    break
            except StopIteration:
                break

        # Find all named arguments already assigned to, as to avoid suggesting
        # them again
        usedNamedArgs = set()
        par_level = -1
        for token, next_token in zip(tokens, tokens[1:]):
            if token == '(':
                par_level += 1
            elif token == ')':
                par_level -= 1

            if par_level != 0:
                continue

            if next_token != '=':
                continue

            usedNamedArgs.add(token)

        argMatches = []
        try:
            callableObj = '.'.join(ids[::-1])
            namedArgs = self._default_arguments(eval(callableObj,
                                                    self.namespace))

            # Remove used named arguments from the list, no need to show twice
            for namedArg in set(namedArgs) - usedNamedArgs:
                if namedArg.startswith(text):
                    argMatches.append("%s=" %namedArg)
        except:
            pass

        return argMatches

    @staticmethod
    def _get_keys(obj: Any) -> list[Any]:
        # Objects can define their own completions by defining an
        # _ipy_key_completions_() method.
        method = get_real_method(obj, '_ipython_key_completions_')
        if method is not None:
            return method()

        # Special case some common in-memory dict-like types
        if isinstance(obj, dict) or _safe_isinstance(obj, "pandas", "DataFrame"):
            try:
                return list(obj.keys())
            except Exception:
                return []
        elif _safe_isinstance(obj, "pandas", "core", "indexing", "_LocIndexer"):
            try:
                return list(obj.obj.keys())
            except Exception:
                return []
        elif _safe_isinstance(obj, 'numpy', 'ndarray') or\
             _safe_isinstance(obj, 'numpy', 'void'):
            return obj.dtype.names or []
        return []

    @context_matcher()
    def dict_key_matcher(self, context: CompletionContext) -> SimpleMatcherResult:
        """Match string keys in a dictionary, after e.g. ``foo[``."""
        matches = self.dict_key_matches(context.token)
        return _convert_matcher_v1_result_to_v2(
            matches, type="dict key", suppress_if_matches=True
        )

    def dict_key_matches(self, text: str) -> list[str]:
        """Match string keys in a dictionary, after e.g. ``foo[``.

        .. deprecated:: 8.6
            You can use :meth:`dict_key_matcher` instead.
        """

        # Short-circuit on closed dictionary (regular expression would
        # not match anyway, but would take quite a while).
        if self.text_until_cursor.strip().endswith("]"):
            return []

        match = DICT_MATCHER_REGEX.search(self.text_until_cursor)

        if match is None:
            return []

        expr, prior_tuple_keys, key_prefix = match.groups()

        obj = self._evaluate_expr(expr)

        if obj is not_found:
            return []

        keys = self._get_keys(obj)
        if not keys:
            return keys

        tuple_prefix = guarded_eval(
            prior_tuple_keys,
            EvaluationContext(
                globals=self.global_namespace,
                locals=self.namespace,
                evaluation=self.evaluation,  # type: ignore
                in_subscript=True,
                auto_import=self._auto_import,
                policy_overrides=self.policy_overrides,
            ),
        )

        closing_quote, token_offset, matches = match_dict_keys(
            keys, key_prefix, self.splitter.delims, extra_prefix=tuple_prefix
        )
        if not matches:
            return []

        # get the cursor position of
        # - the text being completed
        # - the start of the key text
        # - the start of the completion
        text_start = len(self.text_until_cursor) - len(text)
        if key_prefix:
            key_start = match.start(3)
            completion_start = key_start + token_offset
        else:
            key_start = completion_start = match.end()

        # grab the leading prefix, to make sure all completions start with `text`
        if text_start > key_start:
            leading = ''
        else:
            leading = text[text_start:completion_start]

        # append closing quote and bracket as appropriate
        # this is *not* appropriate if the opening quote or bracket is outside
        # the text given to this method, e.g. `d["""a\nt
        can_close_quote = False
        can_close_bracket = False

        continuation = self.line_buffer[len(self.text_until_cursor) :].strip()

        if continuation.startswith(closing_quote):
            # do not close if already closed, e.g. `d['a<tab>'`
            continuation = continuation[len(closing_quote) :]
        else:
            can_close_quote = True

        continuation = continuation.strip()

        # e.g. `pandas.DataFrame` has different tuple indexer behaviour,
        # handling it is out of scope, so let's avoid appending suffixes.
        has_known_tuple_handling = isinstance(obj, dict)

        can_close_bracket = (
            not continuation.startswith("]") and self.auto_close_dict_keys
        )
        can_close_tuple_item = (
            not continuation.startswith(",")
            and has_known_tuple_handling
            and self.auto_close_dict_keys
        )
        can_close_quote = can_close_quote and self.auto_close_dict_keys

        # fast path if closing quote should be appended but not suffix is allowed
        if not can_close_quote and not can_close_bracket and closing_quote:
            return [leading + k for k in matches]

        results = []

        end_of_tuple_or_item = _DictKeyState.END_OF_TUPLE | _DictKeyState.END_OF_ITEM

        for k, state_flag in matches.items():
            result = leading + k
            if can_close_quote and closing_quote:
                result += closing_quote

            if state_flag == end_of_tuple_or_item:
                # We do not know which suffix to add,
                # e.g. both tuple item and string
                # match this item.
                pass

            if state_flag in end_of_tuple_or_item and can_close_bracket:
                result += "]"
            if state_flag == _DictKeyState.IN_TUPLE and can_close_tuple_item:
                result += ", "
            results.append(result)
        return results

    @context_matcher()
    def unicode_name_matcher(self, context: CompletionContext) -> SimpleMatcherResult:
        """Match Latex-like syntax for unicode characters base
        on the name of the character.

        This does  ``\\GREEK SMALL LETTER ETA`` -> ``η``

        Works only on valid python 3 identifier, or on combining characters that
        will combine to form a valid identifier.
        """

        text = context.text_until_cursor

        slashpos = text.rfind('\\')
        if slashpos > -1:
            s = text[slashpos+1:]
            try :
                unic = unicodedata.lookup(s)
                # allow combining chars
                if ('a'+unic).isidentifier():
                    return {
                        "completions": [SimpleCompletion(text=unic, type="unicode")],
                        "suppress": True,
                        "matched_fragment": "\\" + s,
                    }
            except KeyError:
                pass
        return {
            "completions": [],
            "suppress": False,
        }

    @context_matcher()
    def latex_name_matcher(self, context: CompletionContext):
        """Match Latex syntax for unicode characters.

        This does both ``\\alp`` -> ``\\alpha`` and ``\\alpha`` -> ``α``
        """
        fragment, matches = self.latex_matches(context.text_until_cursor)
        return _convert_matcher_v1_result_to_v2(
            matches, type="latex", fragment=fragment, suppress_if_matches=True
        )

    def latex_matches(self, text: str) -> tuple[str, Sequence[str]]:
        """Match Latex syntax for unicode characters.

        This does both ``\\alp`` -> ``\\alpha`` and ``\\alpha`` -> ``α``

        .. deprecated:: 8.6
            You can use :meth:`latex_name_matcher` instead.
        """
        slashpos = text.rfind('\\')
        if slashpos > -1:
            s = text[slashpos:]
            if s in latex_symbols:
                # Try to complete a full latex symbol to unicode
                # \\alpha -> α
                return s, [latex_symbols[s]]
            else:
                # If a user has partially typed a latex symbol, give them
                # a full list of options \al -> [\aleph, \alpha]
                matches = [k for k in latex_symbols if k.startswith(s)]
                if matches:
                    return s, matches
        return '', ()

    @context_matcher()
    def custom_completer_matcher(self, context):
        """Dispatch custom completer.

        If a match is found, suppresses all other matchers except for Jedi.
        """
        matches = self.dispatch_custom_completer(context.token) or []
        result = _convert_matcher_v1_result_to_v2(
            matches, type=_UNKNOWN_TYPE, suppress_if_matches=True
        )
        result["ordered"] = True
        result["do_not_suppress"] = {_get_matcher_id(self._jedi_matcher)}
        return result

    def dispatch_custom_completer(self, text):
        """
        .. deprecated:: 8.6
            You can use :meth:`custom_completer_matcher` instead.
        """
        if not self.custom_completers:
            return

        line = self.line_buffer
        if not line.strip():
            return None

        # Create a little structure to pass all the relevant information about
        # the current completion to any custom completer.
        event = SimpleNamespace()
        event.line = line
        event.symbol = text
        cmd = line.split(None,1)[0]
        event.command = cmd
        event.text_until_cursor = self.text_until_cursor

        # for foo etc, try also to find completer for %foo
        if not cmd.startswith(self.magic_escape):
            try_magic = self.custom_completers.s_matches(
                self.magic_escape + cmd)
        else:
            try_magic = []

        for c in itertools.chain(self.custom_completers.s_matches(cmd),
                 try_magic,
                 self.custom_completers.flat_matches(self.text_until_cursor)):
            try:
                res = c(event)
                if res:
                    # first, try case sensitive match
                    withcase = [r for r in res if r.startswith(text)]
                    if withcase:
                        return withcase
                    # if none, then case insensitive ones are ok too
                    text_low = text.lower()
                    return [r for r in res if r.lower().startswith(text_low)]
            except TryNext:
                pass
            except KeyboardInterrupt:
                """
                If custom completer take too long,
                let keyboard interrupt abort and return nothing.
                """
                break

        return None

    def completions(self, text: str, offset: int)->Iterator[Completion]:
        """
        Returns an iterator over the possible completions

        .. warning::

            Unstable

            This function is unstable, API may change without warning.
            It will also raise unless use in proper context manager.

        Parameters
        ----------
        text : str
            Full text of the current input, multi line string.
        offset : int
            Integer representing the position of the cursor in ``text``. Offset
            is 0-based indexed.

        Yields
        ------
        Completion

        Notes
        -----
        The cursor on a text can either be seen as being "in between"
        characters or "On" a character depending on the interface visible to
        the user. For consistency the cursor being on "in between" characters X
        and Y is equivalent to the cursor being "on" character Y, that is to say
        the character the cursor is on is considered as being after the cursor.

        Combining characters may span more that one position in the
        text.

        .. note::

            If ``IPCompleter.debug`` is :any:`True` will yield a ``--jedi/ipython--``
            fake Completion token to distinguish completion returned by Jedi
            and usual IPython completion.

        .. note::

            Completions are not completely deduplicated yet. If identical
            completions are coming from different sources this function does not
            ensure that each completion object will only be present once.
        """
        warnings.warn("_complete is a provisional API (as of IPython 6.0). "
                      "It may change without warnings. "
                      "Use in corresponding context manager.",
                      category=ProvisionalCompleterWarning, stacklevel=2)

        seen = set()
        profiler:Optional[cProfile.Profile]
        try:
            if self.profile_completions:
                import cProfile
                profiler = cProfile.Profile()
                profiler.enable()
            else:
                profiler = None

            for c in self._completions(text, offset, _timeout=self.jedi_compute_type_timeout/1000):
                if c and (c in seen):
                    continue
                yield c
                seen.add(c)
        except KeyboardInterrupt:
            """if completions take too long and users send keyboard interrupt,
            do not crash and return ASAP. """
            pass
        finally:
            if profiler is not None:
                profiler.disable()
                ensure_dir_exists(self.profiler_output_dir)
                output_path = os.path.join(self.profiler_output_dir, str(uuid.uuid4()))
                print("Writing profiler output to", output_path)
                profiler.dump_stats(output_path)

    def _completions(self, full_text: str, offset: int, *, _timeout) -> Iterator[Completion]:
        """
        Core completion module.Same signature as :any:`completions`, with the
        extra `timeout` parameter (in seconds).

        Computing jedi's completion ``.type`` can be quite expensive (it is a
        lazy property) and can require some warm-up, more warm up than just
        computing the ``name`` of a completion. The warm-up can be :

            - Long warm-up the first time a module is encountered after
            install/update: actually build parse/inference tree.

            - first time the module is encountered in a session: load tree from
            disk.

        We don't want to block completions for tens of seconds so we give the
        completer a "budget" of ``_timeout`` seconds per invocation to compute
        completions types, the completions that have not yet been computed will
        be marked as "unknown" an will have a chance to be computed next round
        are things get cached.

        Keep in mind that Jedi is not the only thing treating the completion so
        keep the timeout short-ish as if we take more than 0.3 second we still
        have lots of processing to do.

        """
        deadline = time.monotonic() + _timeout

        before = full_text[:offset]
        cursor_line, cursor_column = position_to_cursor(full_text, offset)

        jedi_matcher_id = _get_matcher_id(self._jedi_matcher)

        def is_non_jedi_result(
            result: MatcherResult, identifier: str
        ) -> TypeGuard[SimpleMatcherResult]:
            return identifier != jedi_matcher_id

        results = self._complete(
            full_text=full_text, cursor_line=cursor_line, cursor_pos=cursor_column
        )

        non_jedi_results: dict[str, SimpleMatcherResult] = {
            identifier: result
            for identifier, result in results.items()
            if is_non_jedi_result(result, identifier)
        }

        jedi_matches = (
            cast(_JediMatcherResult, results[jedi_matcher_id])["completions"]
            if jedi_matcher_id in results
            else ()
        )

        iter_jm = iter(jedi_matches)
        if _timeout:
            for jm in iter_jm:
                try:
                    type_ = jm.type
                except Exception:
                    if self.debug:
                        print("Error in Jedi getting type of ", jm)
                    type_ = None
                delta = len(jm.name_with_symbols) - len(jm.complete)
                if type_ == 'function':
                    signature = _make_signature(jm)
                else:
                    signature = ''
                yield Completion(start=offset - delta,
                                 end=offset,
                                 text=jm.name_with_symbols,
                                 type=type_,
                                 signature=signature,
                                 _origin='jedi')

                if time.monotonic() > deadline:
                    break

        for jm in iter_jm:
            delta = len(jm.name_with_symbols) - len(jm.complete)
            yield Completion(
                start=offset - delta,
                end=offset,
                text=jm.name_with_symbols,
                type=_UNKNOWN_TYPE,  # don't compute type for speed
                _origin="jedi",
                signature="",
            )

        # TODO:
        # Suppress this, right now just for debug.
        if jedi_matches and non_jedi_results and self.debug:
            some_start_offset = before.rfind(
                next(iter(non_jedi_results.values()))["matched_fragment"]
            )
            yield Completion(
                start=some_start_offset,
                end=offset,
                text="--jedi/ipython--",
                _origin="debug",
                type="none",
                signature="",
            )

        ordered: list[Completion] = []
        sortable: list[Completion] = []

        for origin, result in non_jedi_results.items():
            matched_text = result["matched_fragment"]
            start_offset = before.rfind(matched_text)
            is_ordered = result.get("ordered", False)
            container = ordered if is_ordered else sortable

            # I'm unsure if this is always true, so let's assert and see if it
            # crash
            assert before.endswith(matched_text)

            for simple_completion in result["completions"]:
                completion = Completion(
                    start=start_offset,
                    end=offset,
                    text=simple_completion.text,
                    _origin=origin,
                    signature="",
                    type=simple_completion.type or _UNKNOWN_TYPE,
                )
                container.append(completion)

        yield from list(self._deduplicate(ordered + self._sort(sortable)))[
            :MATCHES_LIMIT
        ]

    def complete(
        self, text=None, line_buffer=None, cursor_pos=None
    ) -> tuple[str, Sequence[str]]:
        """Find completions for the given text and line context.

        Note that both the text and the line_buffer are optional, but at least
        one of them must be given.

        Parameters
        ----------
        text : string, optional
            Text to perform the completion on.  If not given, the line buffer
            is split using the instance's CompletionSplitter object.
        line_buffer : string, optional
            If not given, the completer attempts to obtain the current line
            buffer via readline.  This keyword allows clients which are
            requesting for text completions in non-readline contexts to inform
            the completer of the entire text.
        cursor_pos : int, optional
            Index of the cursor in the full line buffer.  Should be provided by
            remote frontends where kernel has no access to frontend state.

        Returns
        -------
        Tuple of two items:
        text : str
            Text that was actually used in the completion.
        matches : list
            A list of completion matches.

        Notes
        -----
            This API is likely to be deprecated and replaced by
            :any:`IPCompleter.completions` in the future.

        """
        warnings.warn('`Completer.complete` is pending deprecation since '
                'IPython 6.0 and will be replaced by `Completer.completions`.',
                      PendingDeprecationWarning)
        # potential todo, FOLD the 3rd throw away argument of _complete
        # into the first 2 one.
        # TODO: Q: does the above refer to jedi completions (i.e. 0-indexed?)
        # TODO: should we deprecate now, or does it stay?

        results = self._complete(
            line_buffer=line_buffer, cursor_pos=cursor_pos, text=text, cursor_line=0
        )

        jedi_matcher_id = _get_matcher_id(self._jedi_matcher)

        return self._arrange_and_extract(
            results,
            # TODO: can we confirm that excluding Jedi here was a deliberate choice in previous version?
            skip_matchers={jedi_matcher_id},
            # this API does not support different start/end positions (fragments of token).
            abort_if_offset_changes=True,
        )

    def _arrange_and_extract(
        self,
        results: dict[str, MatcherResult],
        skip_matchers: set[str],
        abort_if_offset_changes: bool,
    ):
        sortable: list[AnyMatcherCompletion] = []
        ordered: list[AnyMatcherCompletion] = []
        most_recent_fragment = None
        for identifier, result in results.items():
            if identifier in skip_matchers:
                continue
            if not result["completions"]:
                continue
            if not most_recent_fragment:
                most_recent_fragment = result["matched_fragment"]
            if (
                abort_if_offset_changes
                and result["matched_fragment"] != most_recent_fragment
            ):
                break
            if result.get("ordered", False):
                ordered.extend(result["completions"])
            else:
                sortable.extend(result["completions"])

        if not most_recent_fragment:
            most_recent_fragment = ""  # to satisfy typechecker (and just in case)

        return most_recent_fragment, [
            m.text for m in self._deduplicate(ordered + self._sort(sortable))
        ]

    def _complete(self, *, cursor_line, cursor_pos, line_buffer=None, text=None,
                  full_text=None) -> _CompleteResult:
        """
        Like complete but can also returns raw jedi completions as well as the
        origin of the completion text. This could (and should) be made much
        cleaner but that will be simpler once we drop the old (and stateful)
        :any:`complete` API.

        With current provisional API, cursor_pos act both (depending on the
        caller) as the offset in the ``text`` or ``line_buffer``, or as the
        ``column`` when passing multiline strings this could/should be renamed
        but would add extra noise.

        Parameters
        ----------
        cursor_line
            Index of the line the cursor is on. 0 indexed.
        cursor_pos
            Position of the cursor in the current line/line_buffer/text. 0
            indexed.
        line_buffer : optional, str
            The current line the cursor is in, this is mostly due to legacy
            reason that readline could only give a us the single current line.
            Prefer `full_text`.
        text : str
            The current "token" the cursor is in, mostly also for historical
            reasons. as the completer would trigger only after the current line
            was parsed.
        full_text : str
            Full text of the current cell.

        Returns
        -------
        An ordered dictionary where keys are identifiers of completion
        matchers and values are ``MatcherResult``s.
        """

        # if the cursor position isn't given, the only sane assumption we can
        # make is that it's at the end of the line (the common case)
        if cursor_pos is None:
            cursor_pos = len(line_buffer) if text is None else len(text)

        if self.use_main_ns:
            self.namespace = __main__.__dict__

        # if text is either None or an empty string, rely on the line buffer
        if (not line_buffer) and full_text:
            line_buffer = full_text.split('\n')[cursor_line]
        if not text:  # issue #11508: check line_buffer before calling split_line
            text = (
                self.splitter.split_line(line_buffer, cursor_pos) if line_buffer else ""
            )

        # If no line buffer is given, assume the input text is all there was
        if line_buffer is None:
            line_buffer = text

        # deprecated - do not use `line_buffer` in new code.
        self.line_buffer = line_buffer
        self.text_until_cursor = self.line_buffer[:cursor_pos]

        if not full_text:
            full_text = line_buffer

        context = CompletionContext(
            full_text=full_text,
            cursor_position=cursor_pos,
            cursor_line=cursor_line,
            token=text,
            limit=MATCHES_LIMIT,
        )

        # Start with a clean slate of completions
        results: dict[str, MatcherResult] = {}

        jedi_matcher_id = _get_matcher_id(self._jedi_matcher)

        suppressed_matchers: set[str] = set()

        matchers = {
            _get_matcher_id(matcher): matcher
            for matcher in sorted(
                self.matchers, key=_get_matcher_priority, reverse=True
            )
        }

        for matcher_id, matcher in matchers.items():
            matcher_id = _get_matcher_id(matcher)

            if matcher_id in self.disable_matchers:
                continue

            if matcher_id in results:
                warnings.warn(f"Duplicate matcher ID: {matcher_id}.")

            if matcher_id in suppressed_matchers:
                continue

            result: MatcherResult
            try:
                if _is_matcher_v1(matcher):
                    result = _convert_matcher_v1_result_to_v2_no_no(
                        matcher(text), type=_UNKNOWN_TYPE
                    )
                elif _is_matcher_v2(matcher):
                    result = matcher(context)
                else:
                    api_version = _get_matcher_api_version(matcher)
                    raise ValueError(f"Unsupported API version {api_version}")
            except BaseException:
                # Show the ugly traceback if the matcher causes an
                # exception, but do NOT crash the kernel!
                sys.excepthook(*sys.exc_info())
                continue

            # set default value for matched fragment if suffix was not selected.
            result["matched_fragment"] = result.get("matched_fragment", context.token)

            if not suppressed_matchers:
                suppression_recommended: Union[bool, set[str]] = result.get(
                    "suppress", False
                )

                suppression_config = (
                    self.suppress_competing_matchers.get(matcher_id, None)
                    if isinstance(self.suppress_competing_matchers, dict)
                    else self.suppress_competing_matchers
                )
                should_suppress = (
                    (suppression_config is True)
                    or (suppression_recommended and (suppression_config is not False))
                ) and has_any_completions(result)

                if should_suppress:
                    suppression_exceptions: set[str] = result.get(
                        "do_not_suppress", set()
                    )
                    if isinstance(suppression_recommended, Iterable):
                        to_suppress = set(suppression_recommended)
                    else:
                        to_suppress = set(matchers)
                    suppressed_matchers = to_suppress - suppression_exceptions

                    new_results = {}
                    for previous_matcher_id, previous_result in results.items():
                        if previous_matcher_id not in suppressed_matchers:
                            new_results[previous_matcher_id] = previous_result
                    results = new_results

            results[matcher_id] = result

        _, matches = self._arrange_and_extract(
            results,
            # TODO Jedi completions non included in legacy stateful API; was this deliberate or omission?
            #  if it was omission, we can remove the filtering step, otherwise remove this comment.
            skip_matchers={jedi_matcher_id},
            abort_if_offset_changes=False,
        )

        # populate legacy stateful API
        self.matches = matches

        return results

    @staticmethod
    def _deduplicate(
        matches: Sequence[AnyCompletion],
    ) -> Iterable[AnyCompletion]:
        filtered_matches: dict[str, AnyCompletion] = {}
        for match in matches:
            text = match.text
            if (
                text not in filtered_matches
                or filtered_matches[text].type == _UNKNOWN_TYPE
            ):
                filtered_matches[text] = match

        return filtered_matches.values()

    @staticmethod
    def _sort(matches: Sequence[AnyCompletion]):
        return sorted(matches, key=lambda x: completions_sorting_key(x.text))

    @context_matcher()
    def fwd_unicode_matcher(self, context: CompletionContext):
        """Same as :any:`fwd_unicode_match`, but adopted to new Matcher API."""
        # TODO: use `context.limit` to terminate early once we matched the maximum
        #  number that will be used downstream; can be added as an optional to
        #  `fwd_unicode_match(text: str, limit: int = None)` or we could re-implement here.
        fragment, matches = self.fwd_unicode_match(context.text_until_cursor)
        return _convert_matcher_v1_result_to_v2(
            matches, type="unicode", fragment=fragment, suppress_if_matches=True
        )

    def fwd_unicode_match(self, text: str) -> tuple[str, Sequence[str]]:
        """
        Forward match a string starting with a backslash with a list of
        potential Unicode completions.

        Will compute list of Unicode character names on first call and cache it.

        .. deprecated:: 8.6
            You can use :meth:`fwd_unicode_matcher` instead.

        Returns
        -------
        At tuple with:
            - matched text (empty if no matches)
            - list of potential completions, empty tuple  otherwise)
        """
        # TODO: self.unicode_names is here a list we traverse each time with ~100k elements.
        # We could do a faster match using a Trie.

        # Using pygtrie the following seem to work:

        #     s = PrefixSet()

        #     for c in range(0,0x10FFFF + 1):
        #         try:
        #             s.add(unicodedata.name(chr(c)))
        #         except ValueError:
        #             pass
        #     [''.join(k) for k in s.iter(prefix)]

        # But need to be timed and adds an extra dependency.

        slashpos = text.rfind('\\')
        # if text starts with slash
        if slashpos > -1:
            # PERF: It's important that we don't access self._unicode_names
            # until we're inside this if-block. _unicode_names is lazily
            # initialized, and it takes a user-noticeable amount of time to
            # initialize it, so we don't want to initialize it unless we're
            # actually going to use it.
            s = text[slashpos + 1 :]
            sup = s.upper()
            candidates = [x for x in self.unicode_names if x.startswith(sup)]
            if candidates:
                return s, candidates
            candidates = [x for x in self.unicode_names if sup in x]
            if candidates:
                return s, candidates
            splitsup = sup.split(" ")
            candidates = [
                x for x in self.unicode_names if all(u in x for u in splitsup)
            ]
            if candidates:
                return s, candidates

            return "", ()

        # if text does not start with slash
        else:
            return '', ()

    @property
    def unicode_names(self) -> list[str]:
        """List of names of unicode code points that can be completed.

        The list is lazily initialized on first access.
        """
        if self._unicode_names is None:
            names = []
            for c in range(0,0x10FFFF + 1):
                try:
                    names.append(unicodedata.name(chr(c)))
                except ValueError:
                    pass
            self._unicode_names = _unicode_name_compute(_UNICODE_RANGES)

        return self._unicode_names


def _unicode_name_compute(ranges: list[tuple[int, int]]) -> list[str]:
    names = []
    for start,stop in ranges:
        for c in range(start, stop) :
            try:
                names.append(unicodedata.name(chr(c)))
            except ValueError:
                pass
    return names

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\typing_extensions.py ===
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