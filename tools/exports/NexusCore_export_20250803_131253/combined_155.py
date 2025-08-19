
# === NexusCore/tools\exports\export_20250803_114325\combined_146.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\metadata\base.py ===
import csv
import email.message
import functools
import json
import logging
import pathlib
import re
import zipfile
from typing import (
    IO,
    Any,
    Collection,
    Container,
    Dict,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    Union,
)

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import InvalidSpecifier, SpecifierSet
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import Version

from pip._internal.exceptions import NoneMetadataError
from pip._internal.locations import site_packages, user_site
from pip._internal.models.direct_url import (
    DIRECT_URL_METADATA_NAME,
    DirectUrl,
    DirectUrlValidationError,
)
from pip._internal.utils.compat import stdlib_pkgs  # TODO: Move definition here.
from pip._internal.utils.egg_link import egg_link_path_from_sys_path
from pip._internal.utils.misc import is_local, normalize_path
from pip._internal.utils.urls import url_to_path

from ._json import msg_to_json

InfoPath = Union[str, pathlib.PurePath]

logger = logging.getLogger(__name__)


class BaseEntryPoint(Protocol):
    @property
    def name(self) -> str:
        raise NotImplementedError()

    @property
    def value(self) -> str:
        raise NotImplementedError()

    @property
    def group(self) -> str:
        raise NotImplementedError()


def _convert_installed_files_path(
    entry: Tuple[str, ...],
    info: Tuple[str, ...],
) -> str:
    """Convert a legacy installed-files.txt path into modern RECORD path.

    The legacy format stores paths relative to the info directory, while the
    modern format stores paths relative to the package root, e.g. the
    site-packages directory.

    :param entry: Path parts of the installed-files.txt entry.
    :param info: Path parts of the egg-info directory relative to package root.
    :returns: The converted entry.

    For best compatibility with symlinks, this does not use ``abspath()`` or
    ``Path.resolve()``, but tries to work with path parts:

    1. While ``entry`` starts with ``..``, remove the equal amounts of parts
       from ``info``; if ``info`` is empty, start appending ``..`` instead.
    2. Join the two directly.
    """
    while entry and entry[0] == "..":
        if not info or info[-1] == "..":
            info += ("..",)
        else:
            info = info[:-1]
        entry = entry[1:]
    return str(pathlib.Path(*info, *entry))


class RequiresEntry(NamedTuple):
    requirement: str
    extra: str
    marker: str


class BaseDistribution(Protocol):
    @classmethod
    def from_directory(cls, directory: str) -> "BaseDistribution":
        """Load the distribution from a metadata directory.

        :param directory: Path to a metadata directory, e.g. ``.dist-info``.
        """
        raise NotImplementedError()

    @classmethod
    def from_metadata_file_contents(
        cls,
        metadata_contents: bytes,
        filename: str,
        project_name: str,
    ) -> "BaseDistribution":
        """Load the distribution from the contents of a METADATA file.

        This is used to implement PEP 658 by generating a "shallow" dist object that can
        be used for resolution without downloading or building the actual dist yet.

        :param metadata_contents: The contents of a METADATA file.
        :param filename: File name for the dist with this metadata.
        :param project_name: Name of the project this dist represents.
        """
        raise NotImplementedError()

    @classmethod
    def from_wheel(cls, wheel: "Wheel", name: str) -> "BaseDistribution":
        """Load the distribution from a given wheel.

        :param wheel: A concrete wheel definition.
        :param name: File name of the wheel.

        :raises InvalidWheel: Whenever loading of the wheel causes a
            :py:exc:`zipfile.BadZipFile` exception to be thrown.
        :raises UnsupportedWheel: If the wheel is a valid zip, but malformed
            internally.
        """
        raise NotImplementedError()

    def __repr__(self) -> str:
        return f"{self.raw_name} {self.raw_version} ({self.location})"

    def __str__(self) -> str:
        return f"{self.raw_name} {self.raw_version}"

    @property
    def location(self) -> Optional[str]:
        """Where the distribution is loaded from.

        A string value is not necessarily a filesystem path, since distributions
        can be loaded from other sources, e.g. arbitrary zip archives. ``None``
        means the distribution is created in-memory.

        Do not canonicalize this value with e.g. ``pathlib.Path.resolve()``. If
        this is a symbolic link, we want to preserve the relative path between
        it and files in the distribution.
        """
        raise NotImplementedError()

    @property
    def editable_project_location(self) -> Optional[str]:
        """The project location for editable distributions.

        This is the directory where pyproject.toml or setup.py is located.
        None if the distribution is not installed in editable mode.
        """
        # TODO: this property is relatively costly to compute, memoize it ?
        direct_url = self.direct_url
        if direct_url:
            if direct_url.is_local_editable():
                return url_to_path(direct_url.url)
        else:
            # Search for an .egg-link file by walking sys.path, as it was
            # done before by dist_is_editable().
            egg_link_path = egg_link_path_from_sys_path(self.raw_name)
            if egg_link_path:
                # TODO: get project location from second line of egg_link file
                #       (https://github.com/pypa/pip/issues/10243)
                return self.location
        return None

    @property
    def installed_location(self) -> Optional[str]:
        """The distribution's "installed" location.

        This should generally be a ``site-packages`` directory. This is
        usually ``dist.location``, except for legacy develop-installed packages,
        where ``dist.location`` is the source code location, and this is where
        the ``.egg-link`` file is.

        The returned location is normalized (in particular, with symlinks removed).
        """
        raise NotImplementedError()

    @property
    def info_location(self) -> Optional[str]:
        """Location of the .[egg|dist]-info directory or file.

        Similarly to ``location``, a string value is not necessarily a
        filesystem path. ``None`` means the distribution is created in-memory.

        For a modern .dist-info installation on disk, this should be something
        like ``{location}/{raw_name}-{version}.dist-info``.

        Do not canonicalize this value with e.g. ``pathlib.Path.resolve()``. If
        this is a symbolic link, we want to preserve the relative path between
        it and other files in the distribution.
        """
        raise NotImplementedError()

    @property
    def installed_by_distutils(self) -> bool:
        """Whether this distribution is installed with legacy distutils format.

        A distribution installed with "raw" distutils not patched by setuptools
        uses one single file at ``info_location`` to store metadata. We need to
        treat this specially on uninstallation.
        """
        info_location = self.info_location
        if not info_location:
            return False
        return pathlib.Path(info_location).is_file()

    @property
    def installed_as_egg(self) -> bool:
        """Whether this distribution is installed as an egg.

        This usually indicates the distribution was installed by (older versions
        of) easy_install.
        """
        location = self.location
        if not location:
            return False
        return location.endswith(".egg")

    @property
    def installed_with_setuptools_egg_info(self) -> bool:
        """Whether this distribution is installed with the ``.egg-info`` format.

        This usually indicates the distribution was installed with setuptools
        with an old pip version or with ``single-version-externally-managed``.

        Note that this ensure the metadata store is a directory. distutils can
        also installs an ``.egg-info``, but as a file, not a directory. This
        property is *False* for that case. Also see ``installed_by_distutils``.
        """
        info_location = self.info_location
        if not info_location:
            return False
        if not info_location.endswith(".egg-info"):
            return False
        return pathlib.Path(info_location).is_dir()

    @property
    def installed_with_dist_info(self) -> bool:
        """Whether this distribution is installed with the "modern format".

        This indicates a "modern" installation, e.g. storing metadata in the
        ``.dist-info`` directory. This applies to installations made by
        setuptools (but through pip, not directly), or anything using the
        standardized build backend interface (PEP 517).
        """
        info_location = self.info_location
        if not info_location:
            return False
        if not info_location.endswith(".dist-info"):
            return False
        return pathlib.Path(info_location).is_dir()

    @property
    def canonical_name(self) -> NormalizedName:
        raise NotImplementedError()

    @property
    def version(self) -> Version:
        raise NotImplementedError()

    @property
    def raw_version(self) -> str:
        raise NotImplementedError()

    @property
    def setuptools_filename(self) -> str:
        """Convert a project name to its setuptools-compatible filename.

        This is a copy of ``pkg_resources.to_filename()`` for compatibility.
        """
        return self.raw_name.replace("-", "_")

    @property
    def direct_url(self) -> Optional[DirectUrl]:
        """Obtain a DirectUrl from this distribution.

        Returns None if the distribution has no `direct_url.json` metadata,
        or if `direct_url.json` is invalid.
        """
        try:
            content = self.read_text(DIRECT_URL_METADATA_NAME)
        except FileNotFoundError:
            return None
        try:
            return DirectUrl.from_json(content)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            DirectUrlValidationError,
        ) as e:
            logger.warning(
                "Error parsing %s for %s: %s",
                DIRECT_URL_METADATA_NAME,
                self.canonical_name,
                e,
            )
            return None

    @property
    def installer(self) -> str:
        try:
            installer_text = self.read_text("INSTALLER")
        except (OSError, ValueError, NoneMetadataError):
            return ""  # Fail silently if the installer file cannot be read.
        for line in installer_text.splitlines():
            cleaned_line = line.strip()
            if cleaned_line:
                return cleaned_line
        return ""

    @property
    def requested(self) -> bool:
        return self.is_file("REQUESTED")

    @property
    def editable(self) -> bool:
        return bool(self.editable_project_location)

    @property
    def local(self) -> bool:
        """If distribution is installed in the current virtual environment.

        Always True if we're not in a virtualenv.
        """
        if self.installed_location is None:
            return False
        return is_local(self.installed_location)

    @property
    def in_usersite(self) -> bool:
        if self.installed_location is None or user_site is None:
            return False
        return self.installed_location.startswith(normalize_path(user_site))

    @property
    def in_site_packages(self) -> bool:
        if self.installed_location is None or site_packages is None:
            return False
        return self.installed_location.startswith(normalize_path(site_packages))

    def is_file(self, path: InfoPath) -> bool:
        """Check whether an entry in the info directory is a file."""
        raise NotImplementedError()

    def iter_distutils_script_names(self) -> Iterator[str]:
        """Find distutils 'scripts' entries metadata.

        If 'scripts' is supplied in ``setup.py``, distutils records those in the
        installed distribution's ``scripts`` directory, a file for each script.
        """
        raise NotImplementedError()

    def read_text(self, path: InfoPath) -> str:
        """Read a file in the info directory.

        :raise FileNotFoundError: If ``path`` does not exist in the directory.
        :raise NoneMetadataError: If ``path`` exists in the info directory, but
            cannot be read.
        """
        raise NotImplementedError()

    def iter_entry_points(self) -> Iterable[BaseEntryPoint]:
        raise NotImplementedError()

    def _metadata_impl(self) -> email.message.Message:
        raise NotImplementedError()

    @functools.cached_property
    def metadata(self) -> email.message.Message:
        """Metadata of distribution parsed from e.g. METADATA or PKG-INFO.

        This should return an empty message if the metadata file is unavailable.

        :raises NoneMetadataError: If the metadata file is available, but does
            not contain valid metadata.
        """
        metadata = self._metadata_impl()
        self._add_egg_info_requires(metadata)
        return metadata

    @property
    def metadata_dict(self) -> Dict[str, Any]:
        """PEP 566 compliant JSON-serializable representation of METADATA or PKG-INFO.

        This should return an empty dict if the metadata file is unavailable.

        :raises NoneMetadataError: If the metadata file is available, but does
            not contain valid metadata.
        """
        return msg_to_json(self.metadata)

    @property
    def metadata_version(self) -> Optional[str]:
        """Value of "Metadata-Version:" in distribution metadata, if available."""
        return self.metadata.get("Metadata-Version")

    @property
    def raw_name(self) -> str:
        """Value of "Name:" in distribution metadata."""
        # The metadata should NEVER be missing the Name: key, but if it somehow
        # does, fall back to the known canonical name.
        return self.metadata.get("Name", self.canonical_name)

    @property
    def requires_python(self) -> SpecifierSet:
        """Value of "Requires-Python:" in distribution metadata.

        If the key does not exist or contains an invalid value, an empty
        SpecifierSet should be returned.
        """
        value = self.metadata.get("Requires-Python")
        if value is None:
            return SpecifierSet()
        try:
            # Convert to str to satisfy the type checker; this can be a Header object.
            spec = SpecifierSet(str(value))
        except InvalidSpecifier as e:
            message = "Package %r has an invalid Requires-Python: %s"
            logger.warning(message, self.raw_name, e)
            return SpecifierSet()
        return spec

    def iter_dependencies(self, extras: Collection[str] = ()) -> Iterable[Requirement]:
        """Dependencies of this distribution.

        For modern .dist-info distributions, this is the collection of
        "Requires-Dist:" entries in distribution metadata.
        """
        raise NotImplementedError()

    def iter_raw_dependencies(self) -> Iterable[str]:
        """Raw Requires-Dist metadata."""
        return self.metadata.get_all("Requires-Dist", [])

    def iter_provided_extras(self) -> Iterable[NormalizedName]:
        """Extras provided by this distribution.

        For modern .dist-info distributions, this is the collection of
        "Provides-Extra:" entries in distribution metadata.

        The return value of this function is expected to be normalised names,
        per PEP 685, with the returned value being handled appropriately by
        `iter_dependencies`.
        """
        raise NotImplementedError()

    def _iter_declared_entries_from_record(self) -> Optional[Iterator[str]]:
        try:
            text = self.read_text("RECORD")
        except FileNotFoundError:
            return None
        # This extra Path-str cast normalizes entries.
        return (str(pathlib.Path(row[0])) for row in csv.reader(text.splitlines()))

    def _iter_declared_entries_from_legacy(self) -> Optional[Iterator[str]]:
        try:
            text = self.read_text("installed-files.txt")
        except FileNotFoundError:
            return None
        paths = (p for p in text.splitlines(keepends=False) if p)
        root = self.location
        info = self.info_location
        if root is None or info is None:
            return paths
        try:
            info_rel = pathlib.Path(info).relative_to(root)
        except ValueError:  # info is not relative to root.
            return paths
        if not info_rel.parts:  # info *is* root.
            return paths
        return (
            _convert_installed_files_path(pathlib.Path(p).parts, info_rel.parts)
            for p in paths
        )

    def iter_declared_entries(self) -> Optional[Iterator[str]]:
        """Iterate through file entries declared in this distribution.

        For modern .dist-info distributions, this is the files listed in the
        ``RECORD`` metadata file. For legacy setuptools distributions, this
        comes from ``installed-files.txt``, with entries normalized to be
        compatible with the format used by ``RECORD``.

        :return: An iterator for listed entries, or None if the distribution
            contains neither ``RECORD`` nor ``installed-files.txt``.
        """
        return (
            self._iter_declared_entries_from_record()
            or self._iter_declared_entries_from_legacy()
        )

    def _iter_requires_txt_entries(self) -> Iterator[RequiresEntry]:
        """Parse a ``requires.txt`` in an egg-info directory.

        This is an INI-ish format where an egg-info stores dependencies. A
        section name describes extra other environment markers, while each entry
        is an arbitrary string (not a key-value pair) representing a dependency
        as a requirement string (no markers).

        There is a construct in ``importlib.metadata`` called ``Sectioned`` that
        does mostly the same, but the format is currently considered private.
        """
        try:
            content = self.read_text("requires.txt")
        except FileNotFoundError:
            return
        extra = marker = ""  # Section-less entries don't have markers.
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):  # Comment; ignored.
                continue
            if line.startswith("[") and line.endswith("]"):  # A section header.
                extra, _, marker = line.strip("[]").partition(":")
                continue
            yield RequiresEntry(requirement=line, extra=extra, marker=marker)

    def _iter_egg_info_extras(self) -> Iterable[str]:
        """Get extras from the egg-info directory."""
        known_extras = {""}
        for entry in self._iter_requires_txt_entries():
            extra = canonicalize_name(entry.extra)
            if extra in known_extras:
                continue
            known_extras.add(extra)
            yield extra

    def _iter_egg_info_dependencies(self) -> Iterable[str]:
        """Get distribution dependencies from the egg-info directory.

        To ease parsing, this converts a legacy dependency entry into a PEP 508
        requirement string. Like ``_iter_requires_txt_entries()``, there is code
        in ``importlib.metadata`` that does mostly the same, but not do exactly
        what we need.

        Namely, ``importlib.metadata`` does not normalize the extra name before
        putting it into the requirement string, which causes marker comparison
        to fail because the dist-info format do normalize. This is consistent in
        all currently available PEP 517 backends, although not standardized.
        """
        for entry in self._iter_requires_txt_entries():
            extra = canonicalize_name(entry.extra)
            if extra and entry.marker:
                marker = f'({entry.marker}) and extra == "{extra}"'
            elif extra:
                marker = f'extra == "{extra}"'
            elif entry.marker:
                marker = entry.marker
            else:
                marker = ""
            if marker:
                yield f"{entry.requirement} ; {marker}"
            else:
                yield entry.requirement

    def _add_egg_info_requires(self, metadata: email.message.Message) -> None:
        """Add egg-info requires.txt information to the metadata."""
        if not metadata.get_all("Requires-Dist"):
            for dep in self._iter_egg_info_dependencies():
                metadata["Requires-Dist"] = dep
        if not metadata.get_all("Provides-Extra"):
            for extra in self._iter_egg_info_extras():
                metadata["Provides-Extra"] = extra


class BaseEnvironment:
    """An environment containing distributions to introspect."""

    @classmethod
    def default(cls) -> "BaseEnvironment":
        raise NotImplementedError()

    @classmethod
    def from_paths(cls, paths: Optional[List[str]]) -> "BaseEnvironment":
        raise NotImplementedError()

    def get_distribution(self, name: str) -> Optional["BaseDistribution"]:
        """Given a requirement name, return the installed distributions.

        The name may not be normalized. The implementation must canonicalize
        it for lookup.
        """
        raise NotImplementedError()

    def _iter_distributions(self) -> Iterator["BaseDistribution"]:
        """Iterate through installed distributions.

        This function should be implemented by subclass, but never called
        directly. Use the public ``iter_distribution()`` instead, which
        implements additional logic to make sure the distributions are valid.
        """
        raise NotImplementedError()

    def iter_all_distributions(self) -> Iterator[BaseDistribution]:
        """Iterate through all installed distributions without any filtering."""
        for dist in self._iter_distributions():
            # Make sure the distribution actually comes from a valid Python
            # packaging distribution. Pip's AdjacentTempDirectory leaves folders
            # e.g. ``~atplotlib.dist-info`` if cleanup was interrupted. The
            # valid project name pattern is taken from PEP 508.
            project_name_valid = re.match(
                r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$",
                dist.canonical_name,
                flags=re.IGNORECASE,
            )
            if not project_name_valid:
                logger.warning(
                    "Ignoring invalid distribution %s (%s)",
                    dist.canonical_name,
                    dist.location,
                )
                continue
            yield dist

    def iter_installed_distributions(
        self,
        local_only: bool = True,
        skip: Container[str] = stdlib_pkgs,
        include_editables: bool = True,
        editables_only: bool = False,
        user_only: bool = False,
    ) -> Iterator[BaseDistribution]:
        """Return a list of installed distributions.

        This is based on ``iter_all_distributions()`` with additional filtering
        options. Note that ``iter_installed_distributions()`` without arguments
        is *not* equal to ``iter_all_distributions()``, since some of the
        configurations exclude packages by default.

        :param local_only: If True (default), only return installations
        local to the current virtualenv, if in a virtualenv.
        :param skip: An iterable of canonicalized project names to ignore;
            defaults to ``stdlib_pkgs``.
        :param include_editables: If False, don't report editables.
        :param editables_only: If True, only report editables.
        :param user_only: If True, only report installations in the user
        site directory.
        """
        it = self.iter_all_distributions()
        if local_only:
            it = (d for d in it if d.local)
        if not include_editables:
            it = (d for d in it if not d.editable)
        if editables_only:
            it = (d for d in it if d.editable)
        if user_only:
            it = (d for d in it if d.in_usersite)
        return (d for d in it if d.canonical_name not in skip)


class Wheel(Protocol):
    location: str

    def as_zipfile(self) -> zipfile.ZipFile:
        raise NotImplementedError()


class FilesystemWheel(Wheel):
    def __init__(self, location: str) -> None:
        self.location = location

    def as_zipfile(self) -> zipfile.ZipFile:
        return zipfile.ZipFile(self.location, allowZip64=True)


class MemoryWheel(Wheel):
    def __init__(self, location: str, stream: IO[bytes]) -> None:
        self.location = location
        self.stream = stream

    def as_zipfile(self) -> zipfile.ZipFile:
        return zipfile.ZipFile(self.stream, allowZip64=True)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\vcs\versioncontrol.py ===
"""Handles all VCS (version control) support"""

import logging
import os
import shutil
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Mapping,
    Optional,
    Tuple,
    Type,
    Union,
)

from pip._internal.cli.spinners import SpinnerInterface
from pip._internal.exceptions import BadCommand, InstallationError
from pip._internal.utils.misc import (
    HiddenText,
    ask_path_exists,
    backup_dir,
    display_path,
    hide_url,
    hide_value,
    is_installable_dir,
    rmtree,
)
from pip._internal.utils.subprocess import (
    CommandArgs,
    call_subprocess,
    format_command_args,
    make_command,
)

__all__ = ["vcs"]


logger = logging.getLogger(__name__)

AuthInfo = Tuple[Optional[str], Optional[str]]


def is_url(name: str) -> bool:
    """
    Return true if the name looks like a URL.
    """
    scheme = urllib.parse.urlsplit(name).scheme
    if not scheme:
        return False
    return scheme in ["http", "https", "file", "ftp"] + vcs.all_schemes


def make_vcs_requirement_url(
    repo_url: str, rev: str, project_name: str, subdir: Optional[str] = None
) -> str:
    """
    Return the URL for a VCS requirement.

    Args:
      repo_url: the remote VCS url, with any needed VCS prefix (e.g. "git+").
      project_name: the (unescaped) project name.
    """
    egg_project_name = project_name.replace("-", "_")
    req = f"{repo_url}@{rev}#egg={egg_project_name}"
    if subdir:
        req += f"&subdirectory={subdir}"

    return req


def find_path_to_project_root_from_repo_root(
    location: str, repo_root: str
) -> Optional[str]:
    """
    Find the the Python project's root by searching up the filesystem from
    `location`. Return the path to project root relative to `repo_root`.
    Return None if the project root is `repo_root`, or cannot be found.
    """
    # find project root.
    orig_location = location
    while not is_installable_dir(location):
        last_location = location
        location = os.path.dirname(location)
        if location == last_location:
            # We've traversed up to the root of the filesystem without
            # finding a Python project.
            logger.warning(
                "Could not find a Python project for directory %s (tried all "
                "parent directories)",
                orig_location,
            )
            return None

    if os.path.samefile(repo_root, location):
        return None

    return os.path.relpath(location, repo_root)


class RemoteNotFoundError(Exception):
    pass


class RemoteNotValidError(Exception):
    def __init__(self, url: str):
        super().__init__(url)
        self.url = url


@dataclass(frozen=True)
class RevOptions:
    """
    Encapsulates a VCS-specific revision to install, along with any VCS
    install options.

    Args:
        vc_class: a VersionControl subclass.
        rev: the name of the revision to install.
        extra_args: a list of extra options.
    """

    vc_class: Type["VersionControl"]
    rev: Optional[str] = None
    extra_args: CommandArgs = field(default_factory=list)
    branch_name: Optional[str] = None

    def __repr__(self) -> str:
        return f"<RevOptions {self.vc_class.name}: rev={self.rev!r}>"

    @property
    def arg_rev(self) -> Optional[str]:
        if self.rev is None:
            return self.vc_class.default_arg_rev

        return self.rev

    def to_args(self) -> CommandArgs:
        """
        Return the VCS-specific command arguments.
        """
        args: CommandArgs = []
        rev = self.arg_rev
        if rev is not None:
            args += self.vc_class.get_base_rev_args(rev)
        args += self.extra_args

        return args

    def to_display(self) -> str:
        if not self.rev:
            return ""

        return f" (to revision {self.rev})"

    def make_new(self, rev: str) -> "RevOptions":
        """
        Make a copy of the current instance, but with a new rev.

        Args:
          rev: the name of the revision for the new object.
        """
        return self.vc_class.make_rev_options(rev, extra_args=self.extra_args)


class VcsSupport:
    _registry: Dict[str, "VersionControl"] = {}
    schemes = ["ssh", "git", "hg", "bzr", "sftp", "svn"]

    def __init__(self) -> None:
        # Register more schemes with urlparse for various version control
        # systems
        urllib.parse.uses_netloc.extend(self.schemes)
        super().__init__()

    def __iter__(self) -> Iterator[str]:
        return self._registry.__iter__()

    @property
    def backends(self) -> List["VersionControl"]:
        return list(self._registry.values())

    @property
    def dirnames(self) -> List[str]:
        return [backend.dirname for backend in self.backends]

    @property
    def all_schemes(self) -> List[str]:
        schemes: List[str] = []
        for backend in self.backends:
            schemes.extend(backend.schemes)
        return schemes

    def register(self, cls: Type["VersionControl"]) -> None:
        if not hasattr(cls, "name"):
            logger.warning("Cannot register VCS %s", cls.__name__)
            return
        if cls.name not in self._registry:
            self._registry[cls.name] = cls()
            logger.debug("Registered VCS backend: %s", cls.name)

    def unregister(self, name: str) -> None:
        if name in self._registry:
            del self._registry[name]

    def get_backend_for_dir(self, location: str) -> Optional["VersionControl"]:
        """
        Return a VersionControl object if a repository of that type is found
        at the given directory.
        """
        vcs_backends = {}
        for vcs_backend in self._registry.values():
            repo_path = vcs_backend.get_repository_root(location)
            if not repo_path:
                continue
            logger.debug("Determine that %s uses VCS: %s", location, vcs_backend.name)
            vcs_backends[repo_path] = vcs_backend

        if not vcs_backends:
            return None

        # Choose the VCS in the inner-most directory. Since all repository
        # roots found here would be either `location` or one of its
        # parents, the longest path should have the most path components,
        # i.e. the backend representing the inner-most repository.
        inner_most_repo_path = max(vcs_backends, key=len)
        return vcs_backends[inner_most_repo_path]

    def get_backend_for_scheme(self, scheme: str) -> Optional["VersionControl"]:
        """
        Return a VersionControl object or None.
        """
        for vcs_backend in self._registry.values():
            if scheme in vcs_backend.schemes:
                return vcs_backend
        return None

    def get_backend(self, name: str) -> Optional["VersionControl"]:
        """
        Return a VersionControl object or None.
        """
        name = name.lower()
        return self._registry.get(name)


vcs = VcsSupport()


class VersionControl:
    name = ""
    dirname = ""
    repo_name = ""
    # List of supported schemes for this Version Control
    schemes: Tuple[str, ...] = ()
    # Iterable of environment variable names to pass to call_subprocess().
    unset_environ: Tuple[str, ...] = ()
    default_arg_rev: Optional[str] = None

    @classmethod
    def should_add_vcs_url_prefix(cls, remote_url: str) -> bool:
        """
        Return whether the vcs prefix (e.g. "git+") should be added to a
        repository's remote url when used in a requirement.
        """
        return not remote_url.lower().startswith(f"{cls.name}:")

    @classmethod
    def get_subdirectory(cls, location: str) -> Optional[str]:
        """
        Return the path to Python project root, relative to the repo root.
        Return None if the project root is in the repo root.
        """
        return None

    @classmethod
    def get_requirement_revision(cls, repo_dir: str) -> str:
        """
        Return the revision string that should be used in a requirement.
        """
        return cls.get_revision(repo_dir)

    @classmethod
    def get_src_requirement(cls, repo_dir: str, project_name: str) -> str:
        """
        Return the requirement string to use to redownload the files
        currently at the given repository directory.

        Args:
          project_name: the (unescaped) project name.

        The return value has a form similar to the following:

            {repository_url}@{revision}#egg={project_name}
        """
        repo_url = cls.get_remote_url(repo_dir)

        if cls.should_add_vcs_url_prefix(repo_url):
            repo_url = f"{cls.name}+{repo_url}"

        revision = cls.get_requirement_revision(repo_dir)
        subdir = cls.get_subdirectory(repo_dir)
        req = make_vcs_requirement_url(repo_url, revision, project_name, subdir=subdir)

        return req

    @staticmethod
    def get_base_rev_args(rev: str) -> List[str]:
        """
        Return the base revision arguments for a vcs command.

        Args:
          rev: the name of a revision to install.  Cannot be None.
        """
        raise NotImplementedError

    def is_immutable_rev_checkout(self, url: str, dest: str) -> bool:
        """
        Return true if the commit hash checked out at dest matches
        the revision in url.

        Always return False, if the VCS does not support immutable commit
        hashes.

        This method does not check if there are local uncommitted changes
        in dest after checkout, as pip currently has no use case for that.
        """
        return False

    @classmethod
    def make_rev_options(
        cls, rev: Optional[str] = None, extra_args: Optional[CommandArgs] = None
    ) -> RevOptions:
        """
        Return a RevOptions object.

        Args:
          rev: the name of a revision to install.
          extra_args: a list of extra options.
        """
        return RevOptions(cls, rev, extra_args=extra_args or [])

    @classmethod
    def _is_local_repository(cls, repo: str) -> bool:
        """
        posix absolute paths start with os.path.sep,
        win32 ones start with drive (like c:\\folder)
        """
        drive, tail = os.path.splitdrive(repo)
        return repo.startswith(os.path.sep) or bool(drive)

    @classmethod
    def get_netloc_and_auth(
        cls, netloc: str, scheme: str
    ) -> Tuple[str, Tuple[Optional[str], Optional[str]]]:
        """
        Parse the repository URL's netloc, and return the new netloc to use
        along with auth information.

        Args:
          netloc: the original repository URL netloc.
          scheme: the repository URL's scheme without the vcs prefix.

        This is mainly for the Subversion class to override, so that auth
        information can be provided via the --username and --password options
        instead of through the URL.  For other subclasses like Git without
        such an option, auth information must stay in the URL.

        Returns: (netloc, (username, password)).
        """
        return netloc, (None, None)

    @classmethod
    def get_url_rev_and_auth(cls, url: str) -> Tuple[str, Optional[str], AuthInfo]:
        """
        Parse the repository URL to use, and return the URL, revision,
        and auth info to use.

        Returns: (url, rev, (username, password)).
        """
        scheme, netloc, path, query, frag = urllib.parse.urlsplit(url)
        if "+" not in scheme:
            raise ValueError(
                f"Sorry, {url!r} is a malformed VCS url. "
                "The format is <vcs>+<protocol>://<url>, "
                "e.g. svn+http://myrepo/svn/MyApp#egg=MyApp"
            )
        # Remove the vcs prefix.
        scheme = scheme.split("+", 1)[1]
        netloc, user_pass = cls.get_netloc_and_auth(netloc, scheme)
        rev = None
        if "@" in path:
            path, rev = path.rsplit("@", 1)
            if not rev:
                raise InstallationError(
                    f"The URL {url!r} has an empty revision (after @) "
                    "which is not supported. Include a revision after @ "
                    "or remove @ from the URL."
                )
        url = urllib.parse.urlunsplit((scheme, netloc, path, query, ""))
        return url, rev, user_pass

    @staticmethod
    def make_rev_args(
        username: Optional[str], password: Optional[HiddenText]
    ) -> CommandArgs:
        """
        Return the RevOptions "extra arguments" to use in obtain().
        """
        return []

    def get_url_rev_options(self, url: HiddenText) -> Tuple[HiddenText, RevOptions]:
        """
        Return the URL and RevOptions object to use in obtain(),
        as a tuple (url, rev_options).
        """
        secret_url, rev, user_pass = self.get_url_rev_and_auth(url.secret)
        username, secret_password = user_pass
        password: Optional[HiddenText] = None
        if secret_password is not None:
            password = hide_value(secret_password)
        extra_args = self.make_rev_args(username, password)
        rev_options = self.make_rev_options(rev, extra_args=extra_args)

        return hide_url(secret_url), rev_options

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize a URL for comparison by unquoting it and removing any
        trailing slash.
        """
        return urllib.parse.unquote(url).rstrip("/")

    @classmethod
    def compare_urls(cls, url1: str, url2: str) -> bool:
        """
        Compare two repo URLs for identity, ignoring incidental differences.
        """
        return cls.normalize_url(url1) == cls.normalize_url(url2)

    def fetch_new(
        self, dest: str, url: HiddenText, rev_options: RevOptions, verbosity: int
    ) -> None:
        """
        Fetch a revision from a repository, in the case that this is the
        first fetch from the repository.

        Args:
          dest: the directory to fetch the repository to.
          rev_options: a RevOptions object.
          verbosity: verbosity level.
        """
        raise NotImplementedError

    def switch(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        """
        Switch the repo at ``dest`` to point to ``URL``.

        Args:
          rev_options: a RevOptions object.
        """
        raise NotImplementedError

    def update(self, dest: str, url: HiddenText, rev_options: RevOptions) -> None:
        """
        Update an already-existing repo to the given ``rev_options``.

        Args:
          rev_options: a RevOptions object.
        """
        raise NotImplementedError

    @classmethod
    def is_commit_id_equal(cls, dest: str, name: Optional[str]) -> bool:
        """
        Return whether the id of the current commit equals the given name.

        Args:
          dest: the repository directory.
          name: a string name.
        """
        raise NotImplementedError

    def obtain(self, dest: str, url: HiddenText, verbosity: int) -> None:
        """
        Install or update in editable mode the package represented by this
        VersionControl object.

        :param dest: the repository directory in which to install or update.
        :param url: the repository URL starting with a vcs prefix.
        :param verbosity: verbosity level.
        """
        url, rev_options = self.get_url_rev_options(url)

        if not os.path.exists(dest):
            self.fetch_new(dest, url, rev_options, verbosity=verbosity)
            return

        rev_display = rev_options.to_display()
        if self.is_repository_directory(dest):
            existing_url = self.get_remote_url(dest)
            if self.compare_urls(existing_url, url.secret):
                logger.debug(
                    "%s in %s exists, and has correct URL (%s)",
                    self.repo_name.title(),
                    display_path(dest),
                    url,
                )
                if not self.is_commit_id_equal(dest, rev_options.rev):
                    logger.info(
                        "Updating %s %s%s",
                        display_path(dest),
                        self.repo_name,
                        rev_display,
                    )
                    self.update(dest, url, rev_options)
                else:
                    logger.info("Skipping because already up-to-date.")
                return

            logger.warning(
                "%s %s in %s exists with URL %s",
                self.name,
                self.repo_name,
                display_path(dest),
                existing_url,
            )
            prompt = ("(s)witch, (i)gnore, (w)ipe, (b)ackup ", ("s", "i", "w", "b"))
        else:
            logger.warning(
                "Directory %s already exists, and is not a %s %s.",
                dest,
                self.name,
                self.repo_name,
            )
            # https://github.com/python/mypy/issues/1174
            prompt = ("(i)gnore, (w)ipe, (b)ackup ", ("i", "w", "b"))  # type: ignore

        logger.warning(
            "The plan is to install the %s repository %s",
            self.name,
            url,
        )
        response = ask_path_exists(f"What to do?  {prompt[0]}", prompt[1])

        if response == "a":
            sys.exit(-1)

        if response == "w":
            logger.warning("Deleting %s", display_path(dest))
            rmtree(dest)
            self.fetch_new(dest, url, rev_options, verbosity=verbosity)
            return

        if response == "b":
            dest_dir = backup_dir(dest)
            logger.warning("Backing up %s to %s", display_path(dest), dest_dir)
            shutil.move(dest, dest_dir)
            self.fetch_new(dest, url, rev_options, verbosity=verbosity)
            return

        # Do nothing if the response is "i".
        if response == "s":
            logger.info(
                "Switching %s %s to %s%s",
                self.repo_name,
                display_path(dest),
                url,
                rev_display,
            )
            self.switch(dest, url, rev_options)

    def unpack(self, location: str, url: HiddenText, verbosity: int) -> None:
        """
        Clean up current location and download the url repository
        (and vcs infos) into location

        :param url: the repository URL starting with a vcs prefix.
        :param verbosity: verbosity level.
        """
        if os.path.exists(location):
            rmtree(location)
        self.obtain(location, url=url, verbosity=verbosity)

    @classmethod
    def get_remote_url(cls, location: str) -> str:
        """
        Return the url used at location

        Raises RemoteNotFoundError if the repository does not have a remote
        url configured.
        """
        raise NotImplementedError

    @classmethod
    def get_revision(cls, location: str) -> str:
        """
        Return the current commit id of the files at the given location.
        """
        raise NotImplementedError

    @classmethod
    def run_command(
        cls,
        cmd: Union[List[str], CommandArgs],
        show_stdout: bool = True,
        cwd: Optional[str] = None,
        on_returncode: 'Literal["raise", "warn", "ignore"]' = "raise",
        extra_ok_returncodes: Optional[Iterable[int]] = None,
        command_desc: Optional[str] = None,
        extra_environ: Optional[Mapping[str, Any]] = None,
        spinner: Optional[SpinnerInterface] = None,
        log_failed_cmd: bool = True,
        stdout_only: bool = False,
    ) -> str:
        """
        Run a VCS subcommand
        This is simply a wrapper around call_subprocess that adds the VCS
        command name, and checks that the VCS is available
        """
        cmd = make_command(cls.name, *cmd)
        if command_desc is None:
            command_desc = format_command_args(cmd)
        try:
            return call_subprocess(
                cmd,
                show_stdout,
                cwd,
                on_returncode=on_returncode,
                extra_ok_returncodes=extra_ok_returncodes,
                command_desc=command_desc,
                extra_environ=extra_environ,
                unset_environ=cls.unset_environ,
                spinner=spinner,
                log_failed_cmd=log_failed_cmd,
                stdout_only=stdout_only,
            )
        except NotADirectoryError:
            raise BadCommand(f"Cannot find command {cls.name!r} - invalid PATH")
        except FileNotFoundError:
            # errno.ENOENT = no such file or directory
            # In other words, the VCS executable isn't available
            raise BadCommand(
                f"Cannot find command {cls.name!r} - do you have "
                f"{cls.name!r} installed and in your PATH?"
            )
        except PermissionError:
            # errno.EACCES = Permission denied
            # This error occurs, for instance, when the command is installed
            # only for another user. So, the current user don't have
            # permission to call the other user command.
            raise BadCommand(
                f"No permission to execute {cls.name!r} - install it "
                f"locally, globally (ask admin), or check your PATH. "
                f"See possible solutions at "
                f"https://pip.pypa.io/en/latest/reference/pip_freeze/"
                f"#fixing-permission-denied."
            )

    @classmethod
    def is_repository_directory(cls, path: str) -> bool:
        """
        Return whether a directory path is a repository directory.
        """
        logger.debug("Checking in %s for %s (%s)...", path, cls.dirname, cls.name)
        return os.path.exists(os.path.join(path, cls.dirname))

    @classmethod
    def get_repository_root(cls, location: str) -> Optional[str]:
        """
        Return the "root" (top-level) directory controlled by the vcs,
        or `None` if the directory is not in any.

        It is meant to be overridden to implement smarter detection
        mechanisms for specific vcs.

        This can do more than is_repository_directory() alone. For
        example, the Git override checks that Git is actually available.
        """
        if cls.is_repository_directory(location):
            return location
        return None

# === NexusCore/openenv\Lib\site-packages\zmq\eventloop\zmqstream.py ===
# Derived from iostream.py from tornado 1.0, Copyright 2009 Facebook
# Used under Apache License Version 2.0
#
# Modifications are Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.
"""A utility class for event-based messaging on a zmq socket using tornado.

.. seealso::

    - :mod:`zmq.asyncio`
    - :mod:`zmq.eventloop.future`
"""

from __future__ import annotations

import asyncio
import pickle
import warnings
from queue import Queue
from typing import Any, Awaitable, Callable, Literal, Sequence, cast, overload

from tornado.ioloop import IOLoop
from tornado.log import gen_log

import zmq
import zmq._future
from zmq import POLLIN, POLLOUT
from zmq.utils import jsonapi


class ZMQStream:
    """A utility class to register callbacks when a zmq socket sends and receives

    For use with tornado IOLoop.

    There are three main methods

    Methods:

    * **on_recv(callback, copy=True):**
        register a callback to be run every time the socket has something to receive
    * **on_send(callback):**
        register a callback to be run every time you call send
    * **send_multipart(self, msg, flags=0, copy=False, callback=None):**
        perform a send that will trigger the callback
        if callback is passed, on_send is also called.

        There are also send_multipart(), send_json(), send_pyobj()

    Three other methods for deactivating the callbacks:

    * **stop_on_recv():**
        turn off the recv callback
    * **stop_on_send():**
        turn off the send callback

    which simply call ``on_<evt>(None)``.

    The entire socket interface, excluding direct recv methods, is also
    provided, primarily through direct-linking the methods.
    e.g.

    >>> stream.bind is stream.socket.bind
    True


    .. versionadded:: 25

        send/recv callbacks can be coroutines.

    .. versionchanged:: 25

        ZMQStreams only support base zmq.Socket classes (this has always been true, but not enforced).
        If ZMQStreams are created with e.g. async Socket subclasses,
        a RuntimeWarning will be shown,
        and the socket cast back to the default zmq.Socket
        before connecting events.

        Previously, using async sockets (or any zmq.Socket subclass) would result in undefined behavior for the
        arguments passed to callback functions.
        Now, the callback functions reliably get the return value of the base `zmq.Socket` send/recv_multipart methods
        (the list of message frames).
    """

    socket: zmq.Socket
    io_loop: IOLoop
    poller: zmq.Poller
    _send_queue: Queue
    _recv_callback: Callable | None
    _send_callback: Callable | None
    _close_callback: Callable | None
    _state: int = 0
    _flushed: bool = False
    _recv_copy: bool = False
    _fd: int

    def __init__(self, socket: zmq.Socket, io_loop: IOLoop | None = None):
        if isinstance(socket, zmq._future._AsyncSocket):
            warnings.warn(
                f"""ZMQStream only supports the base zmq.Socket class.

                Use zmq.Socket(shadow=other_socket)
                or `ctx.socket(zmq.{socket._type_name}, socket_class=zmq.Socket)`
                to create a base zmq.Socket object,
                no matter what other kind of socket your Context creates.
                """,
                RuntimeWarning,
                stacklevel=2,
            )
            # shadow back to base zmq.Socket,
            # otherwise callbacks like `on_recv` will get the wrong types.
            socket = zmq.Socket(shadow=socket)
        self.socket = socket

        # IOLoop.current() is deprecated if called outside the event loop
        # that means
        self.io_loop = io_loop or IOLoop.current()
        self.poller = zmq.Poller()
        self._fd = cast(int, self.socket.FD)

        self._send_queue = Queue()
        self._recv_callback = None
        self._send_callback = None
        self._close_callback = None
        self._recv_copy = False
        self._flushed = False

        self._state = 0
        self._init_io_state()

        # shortcircuit some socket methods
        self.bind = self.socket.bind
        self.bind_to_random_port = self.socket.bind_to_random_port
        self.connect = self.socket.connect
        self.setsockopt = self.socket.setsockopt
        self.getsockopt = self.socket.getsockopt
        self.setsockopt_string = self.socket.setsockopt_string
        self.getsockopt_string = self.socket.getsockopt_string
        self.setsockopt_unicode = self.socket.setsockopt_unicode
        self.getsockopt_unicode = self.socket.getsockopt_unicode

    def stop_on_recv(self):
        """Disable callback and automatic receiving."""
        return self.on_recv(None)

    def stop_on_send(self):
        """Disable callback on sending."""
        return self.on_send(None)

    def stop_on_err(self):
        """DEPRECATED, does nothing"""
        gen_log.warn("on_err does nothing, and will be removed")

    def on_err(self, callback: Callable):
        """DEPRECATED, does nothing"""
        gen_log.warn("on_err does nothing, and will be removed")

    @overload
    def on_recv(
        self,
        callback: Callable[[list[bytes]], Any],
    ) -> None: ...

    @overload
    def on_recv(
        self,
        callback: Callable[[list[bytes]], Any],
        copy: Literal[True],
    ) -> None: ...

    @overload
    def on_recv(
        self,
        callback: Callable[[list[zmq.Frame]], Any],
        copy: Literal[False],
    ) -> None: ...

    @overload
    def on_recv(
        self,
        callback: Callable[[list[zmq.Frame]], Any] | Callable[[list[bytes]], Any],
        copy: bool = ...,
    ): ...

    def on_recv(
        self,
        callback: Callable[[list[zmq.Frame]], Any] | Callable[[list[bytes]], Any],
        copy: bool = True,
    ) -> None:
        """Register a callback for when a message is ready to recv.

        There can be only one callback registered at a time, so each
        call to `on_recv` replaces previously registered callbacks.

        on_recv(None) disables recv event polling.

        Use on_recv_stream(callback) instead, to register a callback that will receive
        both this ZMQStream and the message, instead of just the message.

        Parameters
        ----------

        callback : callable
            callback must take exactly one argument, which will be a
            list, as returned by socket.recv_multipart()
            if callback is None, recv callbacks are disabled.
        copy : bool
            copy is passed directly to recv, so if copy is False,
            callback will receive Message objects. If copy is True,
            then callback will receive bytes/str objects.

        Returns : None
        """

        self._check_closed()
        assert callback is None or callable(callback)
        self._recv_callback = callback
        self._recv_copy = copy
        if callback is None:
            self._drop_io_state(zmq.POLLIN)
        else:
            self._add_io_state(zmq.POLLIN)

    @overload
    def on_recv_stream(
        self,
        callback: Callable[[ZMQStream, list[bytes]], Any],
    ) -> None: ...

    @overload
    def on_recv_stream(
        self,
        callback: Callable[[ZMQStream, list[bytes]], Any],
        copy: Literal[True],
    ) -> None: ...

    @overload
    def on_recv_stream(
        self,
        callback: Callable[[ZMQStream, list[zmq.Frame]], Any],
        copy: Literal[False],
    ) -> None: ...

    @overload
    def on_recv_stream(
        self,
        callback: (
            Callable[[ZMQStream, list[zmq.Frame]], Any]
            | Callable[[ZMQStream, list[bytes]], Any]
        ),
        copy: bool = ...,
    ): ...

    def on_recv_stream(
        self,
        callback: (
            Callable[[ZMQStream, list[zmq.Frame]], Any]
            | Callable[[ZMQStream, list[bytes]], Any]
        ),
        copy: bool = True,
    ):
        """Same as on_recv, but callback will get this stream as first argument

        callback must take exactly two arguments, as it will be called as::

            callback(stream, msg)

        Useful when a single callback should be used with multiple streams.
        """
        if callback is None:
            self.stop_on_recv()
        else:

            def stream_callback(msg):
                return callback(self, msg)

            self.on_recv(stream_callback, copy=copy)

    def on_send(
        self, callback: Callable[[Sequence[Any], zmq.MessageTracker | None], Any]
    ):
        """Register a callback to be called on each send

        There will be two arguments::

            callback(msg, status)

        * `msg` will be the list of sendable objects that was just sent
        * `status` will be the return result of socket.send_multipart(msg) -
          MessageTracker or None.

        Non-copying sends return a MessageTracker object whose
        `done` attribute will be True when the send is complete.
        This allows users to track when an object is safe to write to
        again.

        The second argument will always be None if copy=True
        on the send.

        Use on_send_stream(callback) to register a callback that will be passed
        this ZMQStream as the first argument, in addition to the other two.

        on_send(None) disables recv event polling.

        Parameters
        ----------

        callback : callable
            callback must take exactly two arguments, which will be
            the message being sent (always a list),
            and the return result of socket.send_multipart(msg) -
            MessageTracker or None.

            if callback is None, send callbacks are disabled.
        """

        self._check_closed()
        assert callback is None or callable(callback)
        self._send_callback = callback

    def on_send_stream(
        self,
        callback: Callable[[ZMQStream, Sequence[Any], zmq.MessageTracker | None], Any],
    ):
        """Same as on_send, but callback will get this stream as first argument

        Callback will be passed three arguments::

            callback(stream, msg, status)

        Useful when a single callback should be used with multiple streams.
        """
        if callback is None:
            self.stop_on_send()
        else:
            self.on_send(lambda msg, status: callback(self, msg, status))

    def send(self, msg, flags=0, copy=True, track=False, callback=None, **kwargs):
        """Send a message, optionally also register a new callback for sends.
        See zmq.socket.send for details.
        """
        return self.send_multipart(
            [msg], flags=flags, copy=copy, track=track, callback=callback, **kwargs
        )

    def send_multipart(
        self,
        msg: Sequence[Any],
        flags: int = 0,
        copy: bool = True,
        track: bool = False,
        callback: Callable | None = None,
        **kwargs: Any,
    ) -> None:
        """Send a multipart message, optionally also register a new callback for sends.
        See zmq.socket.send_multipart for details.
        """
        kwargs.update(dict(flags=flags, copy=copy, track=track))
        self._send_queue.put((msg, kwargs))
        callback = callback or self._send_callback
        if callback is not None:
            self.on_send(callback)
        else:
            # noop callback
            self.on_send(lambda *args: None)
        self._add_io_state(zmq.POLLOUT)

    def send_string(
        self,
        u: str,
        flags: int = 0,
        encoding: str = 'utf-8',
        callback: Callable | None = None,
        **kwargs: Any,
    ):
        """Send a unicode message with an encoding.
        See zmq.socket.send_unicode for details.
        """
        if not isinstance(u, str):
            raise TypeError("unicode/str objects only")
        return self.send(u.encode(encoding), flags=flags, callback=callback, **kwargs)

    send_unicode = send_string

    def send_json(
        self,
        obj: Any,
        flags: int = 0,
        callback: Callable | None = None,
        **kwargs: Any,
    ):
        """Send json-serialized version of an object.
        See zmq.socket.send_json for details.
        """
        msg = jsonapi.dumps(obj)
        return self.send(msg, flags=flags, callback=callback, **kwargs)

    def send_pyobj(
        self,
        obj: Any,
        flags: int = 0,
        protocol: int = -1,
        callback: Callable | None = None,
        **kwargs: Any,
    ):
        """Send a Python object as a message using pickle to serialize.

        See zmq.socket.send_json for details.
        """
        msg = pickle.dumps(obj, protocol)
        return self.send(msg, flags, callback=callback, **kwargs)

    def _finish_flush(self):
        """callback for unsetting _flushed flag."""
        self._flushed = False

    def flush(self, flag: int = zmq.POLLIN | zmq.POLLOUT, limit: int | None = None):
        """Flush pending messages.

        This method safely handles all pending incoming and/or outgoing messages,
        bypassing the inner loop, passing them to the registered callbacks.

        A limit can be specified, to prevent blocking under high load.

        flush will return the first time ANY of these conditions are met:
            * No more events matching the flag are pending.
            * the total number of events handled reaches the limit.

        Note that if ``flag|POLLIN != 0``, recv events will be flushed even if no callback
        is registered, unlike normal IOLoop operation. This allows flush to be
        used to remove *and ignore* incoming messages.

        Parameters
        ----------
        flag : int
            default=POLLIN|POLLOUT
            0MQ poll flags.
            If flag|POLLIN,  recv events will be flushed.
            If flag|POLLOUT, send events will be flushed.
            Both flags can be set at once, which is the default.
        limit : None or int, optional
            The maximum number of messages to send or receive.
            Both send and recv count against this limit.

        Returns
        -------
        int :
            count of events handled (both send and recv)
        """
        self._check_closed()
        # unset self._flushed, so callbacks will execute, in case flush has
        # already been called this iteration
        already_flushed = self._flushed
        self._flushed = False
        # initialize counters
        count = 0

        def update_flag():
            """Update the poll flag, to prevent registering POLLOUT events
            if we don't have pending sends."""
            return flag & zmq.POLLIN | (self.sending() and flag & zmq.POLLOUT)

        flag = update_flag()
        if not flag:
            # nothing to do
            return 0
        self.poller.register(self.socket, flag)
        events = self.poller.poll(0)
        while events and (not limit or count < limit):
            s, event = events[0]
            if event & POLLIN:  # receiving
                self._handle_recv()
                count += 1
                if self.socket is None:
                    # break if socket was closed during callback
                    break
            if event & POLLOUT and self.sending():
                self._handle_send()
                count += 1
                if self.socket is None:
                    # break if socket was closed during callback
                    break

            flag = update_flag()
            if flag:
                self.poller.register(self.socket, flag)
                events = self.poller.poll(0)
            else:
                events = []
        if count:  # only bypass loop if we actually flushed something
            # skip send/recv callbacks this iteration
            self._flushed = True
            # reregister them at the end of the loop
            if not already_flushed:  # don't need to do it again
                self.io_loop.add_callback(self._finish_flush)
        elif already_flushed:
            self._flushed = True

        # update ioloop poll state, which may have changed
        self._rebuild_io_state()
        return count

    def set_close_callback(self, callback: Callable | None):
        """Call the given callback when the stream is closed."""
        self._close_callback = callback

    def close(self, linger: int | None = None) -> None:
        """Close this stream."""
        if self.socket is not None:
            if self.socket.closed:
                # fallback on raw fd for closed sockets
                # hopefully this happened promptly after close,
                # otherwise somebody else may have the FD
                warnings.warn(
                    f"Unregistering FD {self._fd} after closing socket. "
                    "This could result in unregistering handlers for the wrong socket. "
                    "Please use stream.close() instead of closing the socket directly.",
                    stacklevel=2,
                )
                self.io_loop.remove_handler(self._fd)
            else:
                self.io_loop.remove_handler(self.socket)
                self.socket.close(linger)
            self.socket = None  # type: ignore
            if self._close_callback:
                self._run_callback(self._close_callback)

    def receiving(self) -> bool:
        """Returns True if we are currently receiving from the stream."""
        return self._recv_callback is not None

    def sending(self) -> bool:
        """Returns True if we are currently sending to the stream."""
        return not self._send_queue.empty()

    def closed(self) -> bool:
        if self.socket is None:
            return True
        if self.socket.closed:
            # underlying socket has been closed, but not by us!
            # trigger our cleanup
            self.close()
            return True
        return False

    def _run_callback(self, callback, *args, **kwargs):
        """Wrap running callbacks in try/except to allow us to
        close our socket."""
        try:
            f = callback(*args, **kwargs)
            if isinstance(f, Awaitable):
                f = asyncio.ensure_future(f)
            else:
                f = None
        except Exception:
            gen_log.error("Uncaught exception in ZMQStream callback", exc_info=True)
            # Re-raise the exception so that IOLoop.handle_callback_exception
            # can see it and log the error
            raise

        if f is not None:
            # handle async callbacks
            def _log_error(f):
                try:
                    f.result()
                except Exception:
                    gen_log.error(
                        "Uncaught exception in ZMQStream callback", exc_info=True
                    )

            f.add_done_callback(_log_error)

    def _handle_events(self, fd, events):
        """This method is the actual handler for IOLoop, that gets called whenever
        an event on my socket is posted. It dispatches to _handle_recv, etc."""
        if not self.socket:
            gen_log.warning("Got events for closed stream %s", self)
            return
        try:
            zmq_events = self.socket.EVENTS
        except zmq.ContextTerminated:
            gen_log.warning("Got events for stream %s after terminating context", self)
            # trigger close check, this will unregister callbacks
            self.closed()
            return
        except zmq.ZMQError as e:
            # run close check
            # shadow sockets may have been closed elsewhere,
            # which should show up as ENOTSOCK here
            if self.closed():
                gen_log.warning(
                    "Got events for stream %s attached to closed socket: %s", self, e
                )
            else:
                gen_log.error("Error getting events for %s: %s", self, e)
            return
        try:
            # dispatch events:
            if zmq_events & zmq.POLLIN and self.receiving():
                self._handle_recv()
                if not self.socket:
                    return
            if zmq_events & zmq.POLLOUT and self.sending():
                self._handle_send()
                if not self.socket:
                    return

            # rebuild the poll state
            self._rebuild_io_state()
        except Exception:
            gen_log.error("Uncaught exception in zmqstream callback", exc_info=True)
            raise

    def _handle_recv(self):
        """Handle a recv event."""
        if self._flushed:
            return
        try:
            msg = self.socket.recv_multipart(zmq.NOBLOCK, copy=self._recv_copy)
        except zmq.ZMQError as e:
            if e.errno == zmq.EAGAIN:
                # state changed since poll event
                pass
            else:
                raise
        else:
            if self._recv_callback:
                callback = self._recv_callback
                self._run_callback(callback, msg)

    def _handle_send(self):
        """Handle a send event."""
        if self._flushed:
            return
        if not self.sending():
            gen_log.error("Shouldn't have handled a send event")
            return

        msg, kwargs = self._send_queue.get()
        try:
            status = self.socket.send_multipart(msg, **kwargs)
        except zmq.ZMQError as e:
            gen_log.error("SEND Error: %s", e)
            status = e
        if self._send_callback:
            callback = self._send_callback
            self._run_callback(callback, msg, status)

    def _check_closed(self):
        if not self.socket:
            raise OSError("Stream is closed")

    def _rebuild_io_state(self):
        """rebuild io state based on self.sending() and receiving()"""
        if self.socket is None:
            return
        state = 0
        if self.receiving():
            state |= zmq.POLLIN
        if self.sending():
            state |= zmq.POLLOUT

        self._state = state
        self._update_handler(state)

    def _add_io_state(self, state):
        """Add io_state to poller."""
        self._state = self._state | state
        self._update_handler(self._state)

    def _drop_io_state(self, state):
        """Stop poller from watching an io_state."""
        self._state = self._state & (~state)
        self._update_handler(self._state)

    def _update_handler(self, state):
        """Update IOLoop handler with state."""
        if self.socket is None:
            return

        if state & self.socket.events:
            # events still exist that haven't been processed
            # explicitly schedule handling to avoid missing events due to edge-triggered FDs
            self.io_loop.add_callback(lambda: self._handle_events(self.socket, 0))

    def _init_io_state(self):
        """initialize the ioloop event handler"""
        self.io_loop.add_handler(self.socket, self._handle_events, self.io_loop.READ)

# === NexusCore/openenv\Lib\site-packages\google\protobuf\internal\containers.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Contains container classes to represent different protocol buffer types.

This file defines container classes which represent categories of protocol
buffer field types which need extra maintenance. Currently these categories
are:

-   Repeated scalar fields - These are all repeated fields which aren't
    composite (e.g. they are of simple types like int32, string, etc).
-   Repeated composite fields - Repeated fields which are composite. This
    includes groups and nested messages.
"""

import collections.abc
import copy
import pickle
from typing import (
    Any,
    Iterable,
    Iterator,
    List,
    MutableMapping,
    MutableSequence,
    NoReturn,
    Optional,
    Sequence,
    TypeVar,
    Union,
    overload,
)


_T = TypeVar('_T')
_K = TypeVar('_K')
_V = TypeVar('_V')


class BaseContainer(Sequence[_T]):
  """Base container class."""

  # Minimizes memory usage and disallows assignment to other attributes.
  __slots__ = ['_message_listener', '_values']

  def __init__(self, message_listener: Any) -> None:
    """
    Args:
      message_listener: A MessageListener implementation.
        The RepeatedScalarFieldContainer will call this object's
        Modified() method when it is modified.
    """
    self._message_listener = message_listener
    self._values = []

  @overload
  def __getitem__(self, key: int) -> _T:
    ...

  @overload
  def __getitem__(self, key: slice) -> List[_T]:
    ...

  def __getitem__(self, key):
    """Retrieves item by the specified key."""
    return self._values[key]

  def __len__(self) -> int:
    """Returns the number of elements in the container."""
    return len(self._values)

  def __ne__(self, other: Any) -> bool:
    """Checks if another instance isn't equal to this one."""
    # The concrete classes should define __eq__.
    return not self == other

  __hash__ = None

  def __repr__(self) -> str:
    return repr(self._values)

  def sort(self, *args, **kwargs) -> None:
    # Continue to support the old sort_function keyword argument.
    # This is expected to be a rare occurrence, so use LBYL to avoid
    # the overhead of actually catching KeyError.
    if 'sort_function' in kwargs:
      kwargs['cmp'] = kwargs.pop('sort_function')
    self._values.sort(*args, **kwargs)

  def reverse(self) -> None:
    self._values.reverse()


# TODO: Remove this. BaseContainer does *not* conform to
# MutableSequence, only its subclasses do.
collections.abc.MutableSequence.register(BaseContainer)


class RepeatedScalarFieldContainer(BaseContainer[_T], MutableSequence[_T]):
  """Simple, type-checked, list-like container for holding repeated scalars."""

  # Disallows assignment to other attributes.
  __slots__ = ['_type_checker']

  def __init__(
      self,
      message_listener: Any,
      type_checker: Any,
  ) -> None:
    """Args:

      message_listener: A MessageListener implementation. The
      RepeatedScalarFieldContainer will call this object's Modified() method
      when it is modified.
      type_checker: A type_checkers.ValueChecker instance to run on elements
      inserted into this container.
    """
    super().__init__(message_listener)
    self._type_checker = type_checker

  def append(self, value: _T) -> None:
    """Appends an item to the list. Similar to list.append()."""
    self._values.append(self._type_checker.CheckValue(value))
    if not self._message_listener.dirty:
      self._message_listener.Modified()

  def insert(self, key: int, value: _T) -> None:
    """Inserts the item at the specified position. Similar to list.insert()."""
    self._values.insert(key, self._type_checker.CheckValue(value))
    if not self._message_listener.dirty:
      self._message_listener.Modified()

  def extend(self, elem_seq: Iterable[_T]) -> None:
    """Extends by appending the given iterable. Similar to list.extend()."""
# TODO: Change OSS to raise error too
    if elem_seq is None:
      return
    try:
      elem_seq_iter = iter(elem_seq)
    except TypeError:
      if not elem_seq:
        warnings.warn('Value is not iterable. Please remove the wrong '
                      'usage. This will be changed to raise TypeError soon.')
        return
      raise
    new_values = [self._type_checker.CheckValue(elem) for elem in elem_seq_iter]
    if new_values:
      self._values.extend(new_values)
    self._message_listener.Modified()

  def MergeFrom(
      self,
      other: Union['RepeatedScalarFieldContainer[_T]', Iterable[_T]],
  ) -> None:
    """Appends the contents of another repeated field of the same type to this
    one. We do not check the types of the individual fields.
    """
    self._values.extend(other)
    self._message_listener.Modified()

  def remove(self, elem: _T):
    """Removes an item from the list. Similar to list.remove()."""
    self._values.remove(elem)
    self._message_listener.Modified()

  def pop(self, key: Optional[int] = -1) -> _T:
    """Removes and returns an item at a given index. Similar to list.pop()."""
    value = self._values[key]
    self.__delitem__(key)
    return value

  @overload
  def __setitem__(self, key: int, value: _T) -> None:
    ...

  @overload
  def __setitem__(self, key: slice, value: Iterable[_T]) -> None:
    ...

  def __setitem__(self, key, value) -> None:
    """Sets the item on the specified position."""
    if isinstance(key, slice):
      if key.step is not None:
        raise ValueError('Extended slices not supported')
      self._values[key] = map(self._type_checker.CheckValue, value)
      self._message_listener.Modified()
    else:
      self._values[key] = self._type_checker.CheckValue(value)
      self._message_listener.Modified()

  def __delitem__(self, key: Union[int, slice]) -> None:
    """Deletes the item at the specified position."""
    del self._values[key]
    self._message_listener.Modified()

  def __eq__(self, other: Any) -> bool:
    """Compares the current instance with another one."""
    if self is other:
      return True
    # Special case for the same type which should be common and fast.
    if isinstance(other, self.__class__):
      return other._values == self._values
    # We are presumably comparing against some other sequence type.
    return other == self._values

  def __deepcopy__(
      self,
      unused_memo: Any = None,
  ) -> 'RepeatedScalarFieldContainer[_T]':
    clone = RepeatedScalarFieldContainer(
        copy.deepcopy(self._message_listener), self._type_checker)
    clone.MergeFrom(self)
    return clone

  def __reduce__(self, **kwargs) -> NoReturn:
    raise pickle.PickleError(
        "Can't pickle repeated scalar fields, convert to list first")


# TODO: Constrain T to be a subtype of Message.
class RepeatedCompositeFieldContainer(BaseContainer[_T], MutableSequence[_T]):
  """Simple, list-like container for holding repeated composite fields."""

  # Disallows assignment to other attributes.
  __slots__ = ['_message_descriptor']

  def __init__(self, message_listener: Any, message_descriptor: Any) -> None:
    """
    Note that we pass in a descriptor instead of the generated directly,
    since at the time we construct a _RepeatedCompositeFieldContainer we
    haven't yet necessarily initialized the type that will be contained in the
    container.

    Args:
      message_listener: A MessageListener implementation.
        The RepeatedCompositeFieldContainer will call this object's
        Modified() method when it is modified.
      message_descriptor: A Descriptor instance describing the protocol type
        that should be present in this container.  We'll use the
        _concrete_class field of this descriptor when the client calls add().
    """
    super().__init__(message_listener)
    self._message_descriptor = message_descriptor

  def add(self, **kwargs: Any) -> _T:
    """Adds a new element at the end of the list and returns it. Keyword
    arguments may be used to initialize the element.
    """
    new_element = self._message_descriptor._concrete_class(**kwargs)
    new_element._SetListener(self._message_listener)
    self._values.append(new_element)
    if not self._message_listener.dirty:
      self._message_listener.Modified()
    return new_element

  def append(self, value: _T) -> None:
    """Appends one element by copying the message."""
    new_element = self._message_descriptor._concrete_class()
    new_element._SetListener(self._message_listener)
    new_element.CopyFrom(value)
    self._values.append(new_element)
    if not self._message_listener.dirty:
      self._message_listener.Modified()

  def insert(self, key: int, value: _T) -> None:
    """Inserts the item at the specified position by copying."""
    new_element = self._message_descriptor._concrete_class()
    new_element._SetListener(self._message_listener)
    new_element.CopyFrom(value)
    self._values.insert(key, new_element)
    if not self._message_listener.dirty:
      self._message_listener.Modified()

  def extend(self, elem_seq: Iterable[_T]) -> None:
    """Extends by appending the given sequence of elements of the same type

    as this one, copying each individual message.
    """
    message_class = self._message_descriptor._concrete_class
    listener = self._message_listener
    values = self._values
    for message in elem_seq:
      new_element = message_class()
      new_element._SetListener(listener)
      new_element.MergeFrom(message)
      values.append(new_element)
    listener.Modified()

  def MergeFrom(
      self,
      other: Union['RepeatedCompositeFieldContainer[_T]', Iterable[_T]],
  ) -> None:
    """Appends the contents of another repeated field of the same type to this
    one, copying each individual message.
    """
    self.extend(other)

  def remove(self, elem: _T) -> None:
    """Removes an item from the list. Similar to list.remove()."""
    self._values.remove(elem)
    self._message_listener.Modified()

  def pop(self, key: Optional[int] = -1) -> _T:
    """Removes and returns an item at a given index. Similar to list.pop()."""
    value = self._values[key]
    self.__delitem__(key)
    return value

  @overload
  def __setitem__(self, key: int, value: _T) -> None:
    ...

  @overload
  def __setitem__(self, key: slice, value: Iterable[_T]) -> None:
    ...

  def __setitem__(self, key, value):
    # This method is implemented to make RepeatedCompositeFieldContainer
    # structurally compatible with typing.MutableSequence. It is
    # otherwise unsupported and will always raise an error.
    raise TypeError(
        f'{self.__class__.__name__} object does not support item assignment')

  def __delitem__(self, key: Union[int, slice]) -> None:
    """Deletes the item at the specified position."""
    del self._values[key]
    self._message_listener.Modified()

  def __eq__(self, other: Any) -> bool:
    """Compares the current instance with another one."""
    if self is other:
      return True
    if not isinstance(other, self.__class__):
      raise TypeError('Can only compare repeated composite fields against '
                      'other repeated composite fields.')
    return self._values == other._values


class ScalarMap(MutableMapping[_K, _V]):
  """Simple, type-checked, dict-like container for holding repeated scalars."""

  # Disallows assignment to other attributes.
  __slots__ = ['_key_checker', '_value_checker', '_values', '_message_listener',
               '_entry_descriptor']

  def __init__(
      self,
      message_listener: Any,
      key_checker: Any,
      value_checker: Any,
      entry_descriptor: Any,
  ) -> None:
    """
    Args:
      message_listener: A MessageListener implementation.
        The ScalarMap will call this object's Modified() method when it
        is modified.
      key_checker: A type_checkers.ValueChecker instance to run on keys
        inserted into this container.
      value_checker: A type_checkers.ValueChecker instance to run on values
        inserted into this container.
      entry_descriptor: The MessageDescriptor of a map entry: key and value.
    """
    self._message_listener = message_listener
    self._key_checker = key_checker
    self._value_checker = value_checker
    self._entry_descriptor = entry_descriptor
    self._values = {}

  def __getitem__(self, key: _K) -> _V:
    try:
      return self._values[key]
    except KeyError:
      key = self._key_checker.CheckValue(key)
      val = self._value_checker.DefaultValue()
      self._values[key] = val
      return val

  def __contains__(self, item: _K) -> bool:
    # We check the key's type to match the strong-typing flavor of the API.
    # Also this makes it easier to match the behavior of the C++ implementation.
    self._key_checker.CheckValue(item)
    return item in self._values

  @overload
  def get(self, key: _K) -> Optional[_V]:
    ...

  @overload
  def get(self, key: _K, default: _T) -> Union[_V, _T]:
    ...

  # We need to override this explicitly, because our defaultdict-like behavior
  # will make the default implementation (from our base class) always insert
  # the key.
  def get(self, key, default=None):
    if key in self:
      return self[key]
    else:
      return default

  def __setitem__(self, key: _K, value: _V) -> _T:
    checked_key = self._key_checker.CheckValue(key)
    checked_value = self._value_checker.CheckValue(value)
    self._values[checked_key] = checked_value
    self._message_listener.Modified()

  def __delitem__(self, key: _K) -> None:
    del self._values[key]
    self._message_listener.Modified()

  def __len__(self) -> int:
    return len(self._values)

  def __iter__(self) -> Iterator[_K]:
    return iter(self._values)

  def __repr__(self) -> str:
    return repr(self._values)

  def MergeFrom(self, other: 'ScalarMap[_K, _V]') -> None:
    self._values.update(other._values)
    self._message_listener.Modified()

  def InvalidateIterators(self) -> None:
    # It appears that the only way to reliably invalidate iterators to
    # self._values is to ensure that its size changes.
    original = self._values
    self._values = original.copy()
    original[None] = None

  # This is defined in the abstract base, but we can do it much more cheaply.
  def clear(self) -> None:
    self._values.clear()
    self._message_listener.Modified()

  def GetEntryClass(self) -> Any:
    return self._entry_descriptor._concrete_class


class MessageMap(MutableMapping[_K, _V]):
  """Simple, type-checked, dict-like container for with submessage values."""

  # Disallows assignment to other attributes.
  __slots__ = ['_key_checker', '_values', '_message_listener',
               '_message_descriptor', '_entry_descriptor']

  def __init__(
      self,
      message_listener: Any,
      message_descriptor: Any,
      key_checker: Any,
      entry_descriptor: Any,
  ) -> None:
    """
    Args:
      message_listener: A MessageListener implementation.
        The ScalarMap will call this object's Modified() method when it
        is modified.
      key_checker: A type_checkers.ValueChecker instance to run on keys
        inserted into this container.
      value_checker: A type_checkers.ValueChecker instance to run on values
        inserted into this container.
      entry_descriptor: The MessageDescriptor of a map entry: key and value.
    """
    self._message_listener = message_listener
    self._message_descriptor = message_descriptor
    self._key_checker = key_checker
    self._entry_descriptor = entry_descriptor
    self._values = {}

  def __getitem__(self, key: _K) -> _V:
    key = self._key_checker.CheckValue(key)
    try:
      return self._values[key]
    except KeyError:
      new_element = self._message_descriptor._concrete_class()
      new_element._SetListener(self._message_listener)
      self._values[key] = new_element
      self._message_listener.Modified()
      return new_element

  def get_or_create(self, key: _K) -> _V:
    """get_or_create() is an alias for getitem (ie. map[key]).

    Args:
      key: The key to get or create in the map.

    This is useful in cases where you want to be explicit that the call is
    mutating the map.  This can avoid lint errors for statements like this
    that otherwise would appear to be pointless statements:

      msg.my_map[key]
    """
    return self[key]

  @overload
  def get(self, key: _K) -> Optional[_V]:
    ...

  @overload
  def get(self, key: _K, default: _T) -> Union[_V, _T]:
    ...

  # We need to override this explicitly, because our defaultdict-like behavior
  # will make the default implementation (from our base class) always insert
  # the key.
  def get(self, key, default=None):
    if key in self:
      return self[key]
    else:
      return default

  def __contains__(self, item: _K) -> bool:
    item = self._key_checker.CheckValue(item)
    return item in self._values

  def __setitem__(self, key: _K, value: _V) -> NoReturn:
    raise ValueError('May not set values directly, call my_map[key].foo = 5')

  def __delitem__(self, key: _K) -> None:
    key = self._key_checker.CheckValue(key)
    del self._values[key]
    self._message_listener.Modified()

  def __len__(self) -> int:
    return len(self._values)

  def __iter__(self) -> Iterator[_K]:
    return iter(self._values)

  def __repr__(self) -> str:
    return repr(self._values)

  def MergeFrom(self, other: 'MessageMap[_K, _V]') -> None:
    # pylint: disable=protected-access
    for key in other._values:
      # According to documentation: "When parsing from the wire or when merging,
      # if there are duplicate map keys the last key seen is used".
      if key in self:
        del self[key]
      self[key].CopyFrom(other[key])
    # self._message_listener.Modified() not required here, because
    # mutations to submessages already propagate.

  def InvalidateIterators(self) -> None:
    # It appears that the only way to reliably invalidate iterators to
    # self._values is to ensure that its size changes.
    original = self._values
    self._values = original.copy()
    original[None] = None

  # This is defined in the abstract base, but we can do it much more cheaply.
  def clear(self) -> None:
    self._values.clear()
    self._message_listener.Modified()

  def GetEntryClass(self) -> Any:
    return self._entry_descriptor._concrete_class


class _UnknownField:
  """A parsed unknown field."""

  # Disallows assignment to other attributes.
  __slots__ = ['_field_number', '_wire_type', '_data']

  def __init__(self, field_number, wire_type, data):
    self._field_number = field_number
    self._wire_type = wire_type
    self._data = data
    return

  def __lt__(self, other):
    # pylint: disable=protected-access
    return self._field_number < other._field_number

  def __eq__(self, other):
    if self is other:
      return True
    # pylint: disable=protected-access
    return (self._field_number == other._field_number and
            self._wire_type == other._wire_type and
            self._data == other._data)


class UnknownFieldRef:  # pylint: disable=missing-class-docstring

  def __init__(self, parent, index):
    self._parent = parent
    self._index = index

  def _check_valid(self):
    if not self._parent:
      raise ValueError('UnknownField does not exist. '
                       'The parent message might be cleared.')
    if self._index >= len(self._parent):
      raise ValueError('UnknownField does not exist. '
                       'The parent message might be cleared.')

  @property
  def field_number(self):
    self._check_valid()
    # pylint: disable=protected-access
    return self._parent._internal_get(self._index)._field_number

  @property
  def wire_type(self):
    self._check_valid()
    # pylint: disable=protected-access
    return self._parent._internal_get(self._index)._wire_type

  @property
  def data(self):
    self._check_valid()
    # pylint: disable=protected-access
    return self._parent._internal_get(self._index)._data


class UnknownFieldSet:
  """UnknownField container"""

  # Disallows assignment to other attributes.
  __slots__ = ['_values']

  def __init__(self):
    self._values = []

  def __getitem__(self, index):
    if self._values is None:
      raise ValueError('UnknownFields does not exist. '
                       'The parent message might be cleared.')
    size = len(self._values)
    if index < 0:
      index += size
    if index < 0 or index >= size:
      raise IndexError('index %d out of range'.index)

    return UnknownFieldRef(self, index)

  def _internal_get(self, index):
    return self._values[index]

  def __len__(self):
    if self._values is None:
      raise ValueError('UnknownFields does not exist. '
                       'The parent message might be cleared.')
    return len(self._values)

  def _add(self, field_number, wire_type, data):
    unknown_field = _UnknownField(field_number, wire_type, data)
    self._values.append(unknown_field)
    return unknown_field

  def __iter__(self):
    for i in range(len(self)):
      yield UnknownFieldRef(self, i)

  def _extend(self, other):
    if other is None:
      return
    # pylint: disable=protected-access
    self._values.extend(other._values)

  def __eq__(self, other):
    if self is other:
      return True
    # Sort unknown fields because their order shouldn't
    # affect equality test.
    values = list(self._values)
    if other is None:
      return not values
    values.sort()
    # pylint: disable=protected-access
    other_values = sorted(other._values)
    return values == other_values

  def _clear(self):
    for value in self._values:
      # pylint: disable=protected-access
      if isinstance(value._data, UnknownFieldSet):
        value._data._clear()  # pylint: disable=protected-access
    self._values = None

# === NexusCore/openenv\Lib\site-packages\parso\python\tokenize.py ===
# -*- coding: utf-8 -*-
"""
This tokenizer has been copied from the ``tokenize.py`` standard library
tokenizer. The reason was simple: The standard library tokenizer fails
if the indentation is not right. To make it possible to do error recovery the
    tokenizer needed to be rewritten.

Basically this is a stripped down version of the standard library module, so
you can read the documentation there. Additionally we included some speed and
memory optimizations here.
"""
from __future__ import absolute_import

import sys
import re
import itertools as _itertools
from codecs import BOM_UTF8
from typing import NamedTuple, Tuple, Iterator, Iterable, List, Dict, \
    Pattern, Set

from parso.python.token import PythonTokenTypes
from parso.utils import split_lines, PythonVersionInfo, parse_version_string


# Maximum code point of Unicode 6.0: 0x10ffff (1,114,111)
MAX_UNICODE = '\U0010ffff'

STRING = PythonTokenTypes.STRING
NAME = PythonTokenTypes.NAME
NUMBER = PythonTokenTypes.NUMBER
OP = PythonTokenTypes.OP
NEWLINE = PythonTokenTypes.NEWLINE
INDENT = PythonTokenTypes.INDENT
DEDENT = PythonTokenTypes.DEDENT
ENDMARKER = PythonTokenTypes.ENDMARKER
ERRORTOKEN = PythonTokenTypes.ERRORTOKEN
ERROR_DEDENT = PythonTokenTypes.ERROR_DEDENT
FSTRING_START = PythonTokenTypes.FSTRING_START
FSTRING_STRING = PythonTokenTypes.FSTRING_STRING
FSTRING_END = PythonTokenTypes.FSTRING_END


class TokenCollection(NamedTuple):
    pseudo_token: Pattern
    single_quoted: Set[str]
    triple_quoted: Set[str]
    endpats: Dict[str, Pattern]
    whitespace: Pattern
    fstring_pattern_map: Dict[str, str]
    always_break_tokens: Tuple[str]


BOM_UTF8_STRING = BOM_UTF8.decode('utf-8')

_token_collection_cache: Dict[PythonVersionInfo, TokenCollection] = {}


def group(*choices, capture=False, **kwargs):
    assert not kwargs

    start = '('
    if not capture:
        start += '?:'
    return start + '|'.join(choices) + ')'


def maybe(*choices):
    return group(*choices) + '?'


# Return the empty string, plus all of the valid string prefixes.
def _all_string_prefixes(*, include_fstring=False, only_fstring=False):
    def different_case_versions(prefix):
        for s in _itertools.product(*[(c, c.upper()) for c in prefix]):
            yield ''.join(s)
    # The valid string prefixes. Only contain the lower case versions,
    #  and don't contain any permuations (include 'fr', but not
    #  'rf'). The various permutations will be generated.
    valid_string_prefixes = ['b', 'r', 'u', 'br']

    result = {''}
    if include_fstring:
        f = ['f', 'fr']
        if only_fstring:
            valid_string_prefixes = f
            result = set()
        else:
            valid_string_prefixes += f
    elif only_fstring:
        return set()

    # if we add binary f-strings, add: ['fb', 'fbr']
    for prefix in valid_string_prefixes:
        for t in _itertools.permutations(prefix):
            # create a list with upper and lower versions of each
            #  character
            result.update(different_case_versions(t))
    return result


def _compile(expr):
    return re.compile(expr, re.UNICODE)


def _get_token_collection(version_info):
    try:
        return _token_collection_cache[tuple(version_info)]
    except KeyError:
        _token_collection_cache[tuple(version_info)] = result = \
            _create_token_collection(version_info)
        return result


unicode_character_name = r'[A-Za-z0-9\-]+(?: [A-Za-z0-9\-]+)*'
fstring_string_single_line = _compile(
    r'(?:\{\{|\}\}|\\N\{' + unicode_character_name
    + r'\}|\\(?:\r\n?|\n)|\\[^\r\nN]|[^{}\r\n\\])+'
)
fstring_string_multi_line = _compile(
    r'(?:\{\{|\}\}|\\N\{' + unicode_character_name + r'\}|\\[^N]|[^{}\\])+'
)
fstring_format_spec_single_line = _compile(r'(?:\\(?:\r\n?|\n)|[^{}\r\n])+')
fstring_format_spec_multi_line = _compile(r'[^{}]+')


def _create_token_collection(version_info):
    # Note: we use unicode matching for names ("\w") but ascii matching for
    # number literals.
    Whitespace = r'[ \f\t]*'
    whitespace = _compile(Whitespace)
    Comment = r'#[^\r\n]*'
    Name = '([A-Za-z_0-9\u0080-' + MAX_UNICODE + ']+)'

    Hexnumber = r'0[xX](?:_?[0-9a-fA-F])+'
    Binnumber = r'0[bB](?:_?[01])+'
    Octnumber = r'0[oO](?:_?[0-7])+'
    Decnumber = r'(?:0(?:_?0)*|[1-9](?:_?[0-9])*)'
    Intnumber = group(Hexnumber, Binnumber, Octnumber, Decnumber)
    Exponent = r'[eE][-+]?[0-9](?:_?[0-9])*'
    Pointfloat = group(r'[0-9](?:_?[0-9])*\.(?:[0-9](?:_?[0-9])*)?',
                       r'\.[0-9](?:_?[0-9])*') + maybe(Exponent)
    Expfloat = r'[0-9](?:_?[0-9])*' + Exponent
    Floatnumber = group(Pointfloat, Expfloat)
    Imagnumber = group(r'[0-9](?:_?[0-9])*[jJ]', Floatnumber + r'[jJ]')
    Number = group(Imagnumber, Floatnumber, Intnumber)

    # Note that since _all_string_prefixes includes the empty string,
    #  StringPrefix can be the empty string (making it optional).
    possible_prefixes = _all_string_prefixes()
    StringPrefix = group(*possible_prefixes)
    StringPrefixWithF = group(*_all_string_prefixes(include_fstring=True))
    fstring_prefixes = _all_string_prefixes(include_fstring=True, only_fstring=True)
    FStringStart = group(*fstring_prefixes)

    # Tail end of ' string.
    Single = r"(?:\\.|[^'\\])*'"
    # Tail end of " string.
    Double = r'(?:\\.|[^"\\])*"'
    # Tail end of ''' string.
    Single3 = r"(?:\\.|'(?!'')|[^'\\])*'''"
    # Tail end of """ string.
    Double3 = r'(?:\\.|"(?!"")|[^"\\])*"""'
    Triple = group(StringPrefixWithF + "'''", StringPrefixWithF + '"""')

    # Because of leftmost-then-longest match semantics, be sure to put the
    # longest operators first (e.g., if = came before ==, == would get
    # recognized as two instances of =).
    Operator = group(r"\*\*=?", r">>=?", r"<<=?",
                     r"//=?", r"->",
                     r"[+\-*/%&@`|^!=<>]=?",
                     r"~")

    Bracket = '[][(){}]'

    special_args = [r'\.\.\.', r'\r\n?', r'\n', r'[;.,@]']
    if version_info >= (3, 8):
        special_args.insert(0, ":=?")
    else:
        special_args.insert(0, ":")
    Special = group(*special_args)

    Funny = group(Operator, Bracket, Special)

    # First (or only) line of ' or " string.
    ContStr = group(StringPrefix + r"'[^\r\n'\\]*(?:\\.[^\r\n'\\]*)*"
                    + group("'", r'\\(?:\r\n?|\n)'),
                    StringPrefix + r'"[^\r\n"\\]*(?:\\.[^\r\n"\\]*)*'
                    + group('"', r'\\(?:\r\n?|\n)'))
    pseudo_extra_pool = [Comment, Triple]
    all_quotes = '"', "'", '"""', "'''"
    if fstring_prefixes:
        pseudo_extra_pool.append(FStringStart + group(*all_quotes))

    PseudoExtras = group(r'\\(?:\r\n?|\n)|\Z', *pseudo_extra_pool)
    PseudoToken = group(Whitespace, capture=True) + \
        group(PseudoExtras, Number, Funny, ContStr, Name, capture=True)

    # For a given string prefix plus quotes, endpats maps it to a regex
    #  to match the remainder of that string. _prefix can be empty, for
    #  a normal single or triple quoted string (with no prefix).
    endpats = {}
    for _prefix in possible_prefixes:
        endpats[_prefix + "'"] = _compile(Single)
        endpats[_prefix + '"'] = _compile(Double)
        endpats[_prefix + "'''"] = _compile(Single3)
        endpats[_prefix + '"""'] = _compile(Double3)

    # A set of all of the single and triple quoted string prefixes,
    #  including the opening quotes.
    single_quoted = set()
    triple_quoted = set()
    fstring_pattern_map = {}
    for t in possible_prefixes:
        for quote in '"', "'":
            single_quoted.add(t + quote)

        for quote in '"""', "'''":
            triple_quoted.add(t + quote)

    for t in fstring_prefixes:
        for quote in all_quotes:
            fstring_pattern_map[t + quote] = quote

    ALWAYS_BREAK_TOKENS = (';', 'import', 'class', 'def', 'try', 'except',
                           'finally', 'while', 'with', 'return', 'continue',
                           'break', 'del', 'pass', 'global', 'assert', 'nonlocal')
    pseudo_token_compiled = _compile(PseudoToken)
    return TokenCollection(
        pseudo_token_compiled, single_quoted, triple_quoted, endpats,
        whitespace, fstring_pattern_map, set(ALWAYS_BREAK_TOKENS)
    )


class Token(NamedTuple):
    type: PythonTokenTypes
    string: str
    start_pos: Tuple[int, int]
    prefix: str

    @property
    def end_pos(self) -> Tuple[int, int]:
        lines = split_lines(self.string)
        if len(lines) > 1:
            return self.start_pos[0] + len(lines) - 1, 0
        else:
            return self.start_pos[0], self.start_pos[1] + len(self.string)


class PythonToken(Token):
    def __repr__(self):
        return ('TokenInfo(type=%s, string=%r, start_pos=%r, prefix=%r)' %
                self._replace(type=self.type.name))


class FStringNode:
    def __init__(self, quote):
        self.quote = quote
        self.parentheses_count = 0
        self.previous_lines = ''
        self.last_string_start_pos = None
        # In the syntax there can be multiple format_spec's nested:
        # {x:{y:3}}
        self.format_spec_count = 0

    def open_parentheses(self, character):
        self.parentheses_count += 1

    def close_parentheses(self, character):
        self.parentheses_count -= 1
        if self.parentheses_count == 0:
            # No parentheses means that the format spec is also finished.
            self.format_spec_count = 0

    def allow_multiline(self):
        return len(self.quote) == 3

    def is_in_expr(self):
        return self.parentheses_count > self.format_spec_count

    def is_in_format_spec(self):
        return not self.is_in_expr() and self.format_spec_count


def _close_fstring_if_necessary(fstring_stack, string, line_nr, column, additional_prefix):
    for fstring_stack_index, node in enumerate(fstring_stack):
        lstripped_string = string.lstrip()
        len_lstrip = len(string) - len(lstripped_string)
        if lstripped_string.startswith(node.quote):
            token = PythonToken(
                FSTRING_END,
                node.quote,
                (line_nr, column + len_lstrip),
                prefix=additional_prefix+string[:len_lstrip],
            )
            additional_prefix = ''
            assert not node.previous_lines
            del fstring_stack[fstring_stack_index:]
            return token, '', len(node.quote) + len_lstrip
    return None, additional_prefix, 0


def _find_fstring_string(endpats, fstring_stack, line, lnum, pos):
    tos = fstring_stack[-1]
    allow_multiline = tos.allow_multiline()
    if tos.is_in_format_spec():
        if allow_multiline:
            regex = fstring_format_spec_multi_line
        else:
            regex = fstring_format_spec_single_line
    else:
        if allow_multiline:
            regex = fstring_string_multi_line
        else:
            regex = fstring_string_single_line

    match = regex.match(line, pos)
    if match is None:
        return tos.previous_lines, pos

    if not tos.previous_lines:
        tos.last_string_start_pos = (lnum, pos)

    string = match.group(0)
    for fstring_stack_node in fstring_stack:
        end_match = endpats[fstring_stack_node.quote].match(string)
        if end_match is not None:
            string = end_match.group(0)[:-len(fstring_stack_node.quote)]

    new_pos = pos
    new_pos += len(string)
    # even if allow_multiline is False, we still need to check for trailing
    # newlines, because a single-line f-string can contain line continuations
    if string.endswith('\n') or string.endswith('\r'):
        tos.previous_lines += string
        string = ''
    else:
        string = tos.previous_lines + string

    return string, new_pos


def tokenize(
    code: str, *, version_info: PythonVersionInfo, start_pos: Tuple[int, int] = (1, 0)
) -> Iterator[PythonToken]:
    """Generate tokens from a the source code (string)."""
    lines = split_lines(code, keepends=True)
    return tokenize_lines(lines, version_info=version_info, start_pos=start_pos)


def _print_tokens(func):
    """
    A small helper function to help debug the tokenize_lines function.
    """
    def wrapper(*args, **kwargs):
        for token in func(*args, **kwargs):
            print(token)  # This print is intentional for debugging!
            yield token

    return wrapper


# @_print_tokens
def tokenize_lines(
    lines: Iterable[str],
    *,
    version_info: PythonVersionInfo,
    indents: List[int] = None,
    start_pos: Tuple[int, int] = (1, 0),
    is_first_token=True,
) -> Iterator[PythonToken]:
    """
    A heavily modified Python standard library tokenizer.

    Additionally to the default information, yields also the prefix of each
    token. This idea comes from lib2to3. The prefix contains all information
    that is irrelevant for the parser like newlines in parentheses or comments.
    """
    def dedent_if_necessary(start):
        while start < indents[-1]:
            if start > indents[-2]:
                yield PythonToken(ERROR_DEDENT, '', (lnum, start), '')
                indents[-1] = start
                break
            indents.pop()
            yield PythonToken(DEDENT, '', spos, '')

    pseudo_token, single_quoted, triple_quoted, endpats, whitespace, \
        fstring_pattern_map, always_break_tokens, = \
        _get_token_collection(version_info)
    paren_level = 0  # count parentheses
    if indents is None:
        indents = [0]
    max_ = 0
    numchars = '0123456789'
    contstr = ''
    contline: str
    contstr_start: Tuple[int, int]
    endprog: Pattern
    # We start with a newline. This makes indent at the first position
    # possible. It's not valid Python, but still better than an INDENT in the
    # second line (and not in the first). This makes quite a few things in
    # Jedi's fast parser possible.
    new_line = True
    prefix = ''  # Should never be required, but here for safety
    additional_prefix = ''
    lnum = start_pos[0] - 1
    fstring_stack: List[FStringNode] = []
    for line in lines:  # loop over lines in stream
        lnum += 1
        pos = 0
        max_ = len(line)
        if is_first_token:
            if line.startswith(BOM_UTF8_STRING):
                additional_prefix = BOM_UTF8_STRING
                line = line[1:]
                max_ = len(line)

            # Fake that the part before was already parsed.
            line = '^' * start_pos[1] + line
            pos = start_pos[1]
            max_ += start_pos[1]

            is_first_token = False

        if contstr:                                         # continued string
            endmatch = endprog.match(line)  # noqa: F821
            if endmatch:
                pos = endmatch.end(0)
                yield PythonToken(
                    STRING, contstr + line[:pos],
                    contstr_start, prefix)  # noqa: F821
                contstr = ''
                contline = ''
            else:
                contstr = contstr + line
                contline = contline + line
                continue

        while pos < max_:
            if fstring_stack:
                tos = fstring_stack[-1]
                if not tos.is_in_expr():
                    string, pos = _find_fstring_string(endpats, fstring_stack, line, lnum, pos)
                    if string:
                        yield PythonToken(
                            FSTRING_STRING, string,
                            tos.last_string_start_pos,
                            # Never has a prefix because it can start anywhere and
                            # include whitespace.
                            prefix=''
                        )
                        tos.previous_lines = ''
                        continue
                    if pos == max_:
                        break

                rest = line[pos:]
                fstring_end_token, additional_prefix, quote_length = _close_fstring_if_necessary(
                    fstring_stack,
                    rest,
                    lnum,
                    pos,
                    additional_prefix,
                )
                pos += quote_length
                if fstring_end_token is not None:
                    yield fstring_end_token
                    continue

            # in an f-string, match until the end of the string
            if fstring_stack:
                string_line = line
                for fstring_stack_node in fstring_stack:
                    quote = fstring_stack_node.quote
                    end_match = endpats[quote].match(line, pos)
                    if end_match is not None:
                        end_match_string = end_match.group(0)
                        if len(end_match_string) - len(quote) + pos < len(string_line):
                            string_line = line[:pos] + end_match_string[:-len(quote)]
                pseudomatch = pseudo_token.match(string_line, pos)
            else:
                pseudomatch = pseudo_token.match(line, pos)

            if pseudomatch:
                prefix = additional_prefix + pseudomatch.group(1)
                additional_prefix = ''
                start, pos = pseudomatch.span(2)
                spos = (lnum, start)
                token = pseudomatch.group(2)
                if token == '':
                    assert prefix
                    additional_prefix = prefix
                    # This means that we have a line with whitespace/comments at
                    # the end, which just results in an endmarker.
                    break
                initial = token[0]
            else:
                match = whitespace.match(line, pos)
                initial = line[match.end()]
                start = match.end()
                spos = (lnum, start)

            if new_line and initial not in '\r\n#' and (initial != '\\' or pseudomatch is None):
                new_line = False
                if paren_level == 0 and not fstring_stack:
                    indent_start = start
                    if indent_start > indents[-1]:
                        yield PythonToken(INDENT, '', spos, '')
                        indents.append(indent_start)
                    yield from dedent_if_necessary(indent_start)

            if not pseudomatch:  # scan for tokens
                match = whitespace.match(line, pos)
                if new_line and paren_level == 0 and not fstring_stack:
                    yield from dedent_if_necessary(match.end())
                pos = match.end()
                new_line = False
                yield PythonToken(
                    ERRORTOKEN, line[pos], (lnum, pos),
                    additional_prefix + match.group(0)
                )
                additional_prefix = ''
                pos += 1
                continue

            if (initial in numchars                      # ordinary number
                    or (initial == '.' and token != '.' and token != '...')):
                yield PythonToken(NUMBER, token, spos, prefix)
            elif pseudomatch.group(3) is not None:            # ordinary name
                if token in always_break_tokens and (fstring_stack or paren_level):
                    fstring_stack[:] = []
                    paren_level = 0
                    # We only want to dedent if the token is on a new line.
                    m = re.match(r'[ \f\t]*$', line[:start])
                    if m is not None:
                        yield from dedent_if_necessary(m.end())
                if token.isidentifier():
                    yield PythonToken(NAME, token, spos, prefix)
                else:
                    yield from _split_illegal_unicode_name(token, spos, prefix)
            elif initial in '\r\n':
                if any(not f.allow_multiline() for f in fstring_stack):
                    fstring_stack.clear()

                if not new_line and paren_level == 0 and not fstring_stack:
                    yield PythonToken(NEWLINE, token, spos, prefix)
                else:
                    additional_prefix = prefix + token
                new_line = True
            elif initial == '#':  # Comments
                assert not token.endswith("\n") and not token.endswith("\r")
                if fstring_stack and fstring_stack[-1].is_in_expr():
                    # `#` is not allowed in f-string expressions
                    yield PythonToken(ERRORTOKEN, initial, spos, prefix)
                    pos = start + 1
                else:
                    additional_prefix = prefix + token
            elif token in triple_quoted:
                endprog = endpats[token]
                endmatch = endprog.match(line, pos)
                if endmatch:                                # all on one line
                    pos = endmatch.end(0)
                    token = line[start:pos]
                    yield PythonToken(STRING, token, spos, prefix)
                else:
                    contstr_start = spos                    # multiple lines
                    contstr = line[start:]
                    contline = line
                    break

            # Check up to the first 3 chars of the token to see if
            #  they're in the single_quoted set. If so, they start
            #  a string.
            # We're using the first 3, because we're looking for
            #  "rb'" (for example) at the start of the token. If
            #  we switch to longer prefixes, this needs to be
            #  adjusted.
            # Note that initial == token[:1].
            # Also note that single quote checking must come after
            #  triple quote checking (above).
            elif initial in single_quoted or \
                    token[:2] in single_quoted or \
                    token[:3] in single_quoted:
                if token[-1] in '\r\n':                       # continued string
                    # This means that a single quoted string ends with a
                    # backslash and is continued.
                    contstr_start = lnum, start
                    endprog = (endpats.get(initial) or endpats.get(token[1])
                               or endpats.get(token[2]))
                    contstr = line[start:]
                    contline = line
                    break
                else:                                       # ordinary string
                    yield PythonToken(STRING, token, spos, prefix)
            elif token in fstring_pattern_map:  # The start of an fstring.
                fstring_stack.append(FStringNode(fstring_pattern_map[token]))
                yield PythonToken(FSTRING_START, token, spos, prefix)
            elif initial == '\\' and line[start:] in ('\\\n', '\\\r\n', '\\\r'):  # continued stmt
                additional_prefix += prefix + line[start:]
                break
            else:
                if token in '([{':
                    if fstring_stack:
                        fstring_stack[-1].open_parentheses(token)
                    else:
                        paren_level += 1
                elif token in ')]}':
                    if fstring_stack:
                        fstring_stack[-1].close_parentheses(token)
                    else:
                        if paren_level:
                            paren_level -= 1
                elif token.startswith(':') and fstring_stack \
                        and fstring_stack[-1].parentheses_count \
                        - fstring_stack[-1].format_spec_count == 1:
                    # `:` and `:=` both count
                    fstring_stack[-1].format_spec_count += 1
                    token = ':'
                    pos = start + 1

                yield PythonToken(OP, token, spos, prefix)

    if contstr:
        yield PythonToken(ERRORTOKEN, contstr, contstr_start, prefix)
        if contstr.endswith('\n') or contstr.endswith('\r'):
            new_line = True

    if fstring_stack:
        tos = fstring_stack[-1]
        if tos.previous_lines:
            yield PythonToken(
                FSTRING_STRING, tos.previous_lines,
                tos.last_string_start_pos,
                # Never has a prefix because it can start anywhere and
                # include whitespace.
                prefix=''
            )

    end_pos = lnum, max_
    # As the last position we just take the maximally possible position. We
    # remove -1 for the last new line.
    for indent in indents[1:]:
        indents.pop()
        yield PythonToken(DEDENT, '', end_pos, '')
    yield PythonToken(ENDMARKER, '', end_pos, additional_prefix)


def _split_illegal_unicode_name(token, start_pos, prefix):
    def create_token():
        return PythonToken(ERRORTOKEN if is_illegal else NAME, found, pos, prefix)

    found = ''
    is_illegal = False
    pos = start_pos
    for i, char in enumerate(token):
        if is_illegal:
            if char.isidentifier():
                yield create_token()
                found = char
                is_illegal = False
                prefix = ''
                pos = start_pos[0], start_pos[1] + i
            else:
                found += char
        else:
            new_found = found + char
            if new_found.isidentifier():
                found = new_found
            else:
                if found:
                    yield create_token()
                    prefix = ''
                    pos = start_pos[0], start_pos[1] + i
                found = char
                is_illegal = True

    if found:
        yield create_token()


if __name__ == "__main__":
    path = sys.argv[1]
    with open(path) as f:
        code = f.read()

    for token in tokenize(code, version_info=parse_version_string('3.10')):
        print(token)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\services\model_service\transports\rest.py ===
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

import dataclasses
import json  # type: ignore
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, path_template, rest_helpers, rest_streaming
from google.api_core import exceptions as core_exceptions
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.auth.transport.requests import AuthorizedSession  # type: ignore
from google.protobuf import json_format
import grpc  # type: ignore
from requests import __version__ as requests_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore


from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1.types import model, model_service

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import ModelServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class ModelServiceRestInterceptor:
    """Interceptor for ModelService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the ModelServiceRestTransport.

    .. code-block:: python
        class MyCustomModelServiceInterceptor(ModelServiceRestInterceptor):
            def pre_get_model(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_model(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_list_models(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_models(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = ModelServiceRestTransport(interceptor=MyCustomModelServiceInterceptor())
        client = ModelServiceClient(transport=transport)


    """

    def pre_get_model(
        self,
        request: model_service.GetModelRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.GetModelRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for get_model

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_get_model(self, response: model.Model) -> model.Model:
        """Post-rpc interceptor for get_model

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_list_models(
        self,
        request: model_service.ListModelsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.ListModelsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for list_models

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_list_models(
        self, response: model_service.ListModelsResponse
    ) -> model_service.ListModelsResponse:
        """Post-rpc interceptor for list_models

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_cancel_operation(
        self,
        request: operations_pb2.CancelOperationRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[operations_pb2.CancelOperationRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for cancel_operation

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_cancel_operation(self, response: None) -> None:
        """Post-rpc interceptor for cancel_operation

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_get_operation(
        self,
        request: operations_pb2.GetOperationRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[operations_pb2.GetOperationRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for get_operation

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_get_operation(
        self, response: operations_pb2.Operation
    ) -> operations_pb2.Operation:
        """Post-rpc interceptor for get_operation

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_list_operations(
        self,
        request: operations_pb2.ListOperationsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[operations_pb2.ListOperationsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for list_operations

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_list_operations(
        self, response: operations_pb2.ListOperationsResponse
    ) -> operations_pb2.ListOperationsResponse:
        """Post-rpc interceptor for list_operations

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class ModelServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: ModelServiceRestInterceptor


class ModelServiceRestTransport(ModelServiceTransport):
    """REST backend transport for ModelService.

    Provides methods for getting metadata information about
    Generative Models.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1

    """

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme: str = "https",
        interceptor: Optional[ModelServiceRestInterceptor] = None,
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

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you are developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(
                f"Unexpected hostname structure: {host}"
            )  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST
        )
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        self._interceptor = interceptor or ModelServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _GetModel(ModelServiceRestStub):
        def __hash__(self):
            return hash("GetModel")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: model_service.GetModelRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> model.Model:
            r"""Call the get model method over HTTP.

            Args:
                request (~.model_service.GetModelRequest):
                    The request object. Request for getting information about
                a specific Model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.model.Model:
                    Information about a Generative
                Language Model.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1/{name=models/*}",
                },
            ]
            request, metadata = self._interceptor.pre_get_model(request, metadata)
            pb_request = model_service.GetModelRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = model.Model()
            pb_resp = model.Model.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_get_model(resp)
            return resp

    class _ListModels(ModelServiceRestStub):
        def __hash__(self):
            return hash("ListModels")

        def __call__(
            self,
            request: model_service.ListModelsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> model_service.ListModelsResponse:
            r"""Call the list models method over HTTP.

            Args:
                request (~.model_service.ListModelsRequest):
                    The request object. Request for listing all Models.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.model_service.ListModelsResponse:
                    Response from ``ListModel`` containing a paginated list
                of Models.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1/models",
                },
            ]
            request, metadata = self._interceptor.pre_list_models(request, metadata)
            pb_request = model_service.ListModelsRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = model_service.ListModelsResponse()
            pb_resp = model_service.ListModelsResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_list_models(resp)
            return resp

    @property
    def get_model(self) -> Callable[[model_service.GetModelRequest], model.Model]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetModel(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def list_models(
        self,
    ) -> Callable[[model_service.ListModelsRequest], model_service.ListModelsResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListModels(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def cancel_operation(self):
        return self._CancelOperation(self._session, self._host, self._interceptor)  # type: ignore

    class _CancelOperation(ModelServiceRestStub):
        def __call__(
            self,
            request: operations_pb2.CancelOperationRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> None:
            r"""Call the cancel operation method over HTTP.

            Args:
                request (operations_pb2.CancelOperationRequest):
                    The request object for CancelOperation method.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1/{name=tunedModels/*/operations/*}:cancel",
                    "body": "*",
                },
            ]

            request, metadata = self._interceptor.pre_cancel_operation(
                request, metadata
            )
            request_kwargs = json_format.MessageToDict(request)
            transcoded_request = path_template.transcode(http_options, **request_kwargs)

            body = json.dumps(transcoded_request["body"])
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(json.dumps(transcoded_request["query_params"]))

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"

            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            return self._interceptor.post_cancel_operation(None)

    @property
    def get_operation(self):
        return self._GetOperation(self._session, self._host, self._interceptor)  # type: ignore

    class _GetOperation(ModelServiceRestStub):
        def __call__(
            self,
            request: operations_pb2.GetOperationRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> operations_pb2.Operation:
            r"""Call the get operation method over HTTP.

            Args:
                request (operations_pb2.GetOperationRequest):
                    The request object for GetOperation method.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                operations_pb2.Operation: Response from GetOperation method.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1/{name=tunedModels/*/operations/*}",
                },
            ]

            request, metadata = self._interceptor.pre_get_operation(request, metadata)
            request_kwargs = json_format.MessageToDict(request)
            transcoded_request = path_template.transcode(http_options, **request_kwargs)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(json.dumps(transcoded_request["query_params"]))

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"

            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            resp = operations_pb2.Operation()
            resp = json_format.Parse(response.content.decode("utf-8"), resp)
            resp = self._interceptor.post_get_operation(resp)
            return resp

    @property
    def list_operations(self):
        return self._ListOperations(self._session, self._host, self._interceptor)  # type: ignore

    class _ListOperations(ModelServiceRestStub):
        def __call__(
            self,
            request: operations_pb2.ListOperationsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> operations_pb2.ListOperationsResponse:
            r"""Call the list operations method over HTTP.

            Args:
                request (operations_pb2.ListOperationsRequest):
                    The request object for ListOperations method.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                operations_pb2.ListOperationsResponse: Response from ListOperations method.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1/{name=operations}",
                },
                {
                    "method": "get",
                    "uri": "/v1/{name=tunedModels/*}/operations",
                },
            ]

            request, metadata = self._interceptor.pre_list_operations(request, metadata)
            request_kwargs = json_format.MessageToDict(request)
            transcoded_request = path_template.transcode(http_options, **request_kwargs)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(json.dumps(transcoded_request["query_params"]))

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"

            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            resp = operations_pb2.ListOperationsResponse()
            resp = json_format.Parse(response.content.decode("utf-8"), resp)
            resp = self._interceptor.post_list_operations(resp)
            return resp

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("ModelServiceRestTransport",)

# === NexusCore/openenv\Lib\site-packages\pygments\formatters\img.py ===
"""
    pygments.formatters.img
    ~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for Pixmap output.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import os
import sys

from pygments.formatter import Formatter
from pygments.util import get_bool_opt, get_int_opt, get_list_opt, \
    get_choice_opt

import subprocess

# Import this carefully
try:
    from PIL import Image, ImageDraw, ImageFont
    pil_available = True
except ImportError:
    pil_available = False

try:
    import _winreg
except ImportError:
    try:
        import winreg as _winreg
    except ImportError:
        _winreg = None

__all__ = ['ImageFormatter', 'GifImageFormatter', 'JpgImageFormatter',
           'BmpImageFormatter']


# For some unknown reason every font calls it something different
STYLES = {
    'NORMAL':     ['', 'Roman', 'Book', 'Normal', 'Regular', 'Medium'],
    'ITALIC':     ['Oblique', 'Italic'],
    'BOLD':       ['Bold'],
    'BOLDITALIC': ['Bold Oblique', 'Bold Italic'],
}

# A sane default for modern systems
DEFAULT_FONT_NAME_NIX = 'DejaVu Sans Mono'
DEFAULT_FONT_NAME_WIN = 'Courier New'
DEFAULT_FONT_NAME_MAC = 'Menlo'


class PilNotAvailable(ImportError):
    """When Python imaging library is not available"""


class FontNotFound(Exception):
    """When there are no usable fonts specified"""


class FontManager:
    """
    Manages a set of fonts: normal, italic, bold, etc...
    """

    def __init__(self, font_name, font_size=14):
        self.font_name = font_name
        self.font_size = font_size
        self.fonts = {}
        self.encoding = None
        self.variable = False
        if hasattr(font_name, 'read') or os.path.isfile(font_name):
            font = ImageFont.truetype(font_name, self.font_size)
            self.variable = True
            for style in STYLES:
                self.fonts[style] = font

            return

        if sys.platform.startswith('win'):
            if not font_name:
                self.font_name = DEFAULT_FONT_NAME_WIN
            self._create_win()
        elif sys.platform.startswith('darwin'):
            if not font_name:
                self.font_name = DEFAULT_FONT_NAME_MAC
            self._create_mac()
        else:
            if not font_name:
                self.font_name = DEFAULT_FONT_NAME_NIX
            self._create_nix()

    def _get_nix_font_path(self, name, style):
        proc = subprocess.Popen(['fc-list', f"{name}:style={style}", 'file'],
                                stdout=subprocess.PIPE, stderr=None)
        stdout, _ = proc.communicate()
        if proc.returncode == 0:
            lines = stdout.splitlines()
            for line in lines:
                if line.startswith(b'Fontconfig warning:'):
                    continue
                path = line.decode().strip().strip(':')
                if path:
                    return path
            return None

    def _create_nix(self):
        for name in STYLES['NORMAL']:
            path = self._get_nix_font_path(self.font_name, name)
            if path is not None:
                self.fonts['NORMAL'] = ImageFont.truetype(path, self.font_size)
                break
        else:
            raise FontNotFound(f'No usable fonts named: "{self.font_name}"')
        for style in ('ITALIC', 'BOLD', 'BOLDITALIC'):
            for stylename in STYLES[style]:
                path = self._get_nix_font_path(self.font_name, stylename)
                if path is not None:
                    self.fonts[style] = ImageFont.truetype(path, self.font_size)
                    break
            else:
                if style == 'BOLDITALIC':
                    self.fonts[style] = self.fonts['BOLD']
                else:
                    self.fonts[style] = self.fonts['NORMAL']

    def _get_mac_font_path(self, font_map, name, style):
        return font_map.get((name + ' ' + style).strip().lower())

    def _create_mac(self):
        font_map = {}
        for font_dir in (os.path.join(os.getenv("HOME"), 'Library/Fonts/'),
                         '/Library/Fonts/', '/System/Library/Fonts/'):
            font_map.update(
                (os.path.splitext(f)[0].lower(), os.path.join(font_dir, f))
                for _, _, files in os.walk(font_dir)
                for f in files
                if f.lower().endswith(('ttf', 'ttc')))

        for name in STYLES['NORMAL']:
            path = self._get_mac_font_path(font_map, self.font_name, name)
            if path is not None:
                self.fonts['NORMAL'] = ImageFont.truetype(path, self.font_size)
                break
        else:
            raise FontNotFound(f'No usable fonts named: "{self.font_name}"')
        for style in ('ITALIC', 'BOLD', 'BOLDITALIC'):
            for stylename in STYLES[style]:
                path = self._get_mac_font_path(font_map, self.font_name, stylename)
                if path is not None:
                    self.fonts[style] = ImageFont.truetype(path, self.font_size)
                    break
            else:
                if style == 'BOLDITALIC':
                    self.fonts[style] = self.fonts['BOLD']
                else:
                    self.fonts[style] = self.fonts['NORMAL']

    def _lookup_win(self, key, basename, styles, fail=False):
        for suffix in ('', ' (TrueType)'):
            for style in styles:
                try:
                    valname = '{}{}{}'.format(basename, style and ' '+style, suffix)
                    val, _ = _winreg.QueryValueEx(key, valname)
                    return val
                except OSError:
                    continue
        else:
            if fail:
                raise FontNotFound(f'Font {basename} ({styles[0]}) not found in registry')
            return None

    def _create_win(self):
        lookuperror = None
        keynames = [ (_winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows NT\CurrentVersion\Fonts'),
                     (_winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Fonts'),
                     (_winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows NT\CurrentVersion\Fonts'),
                     (_winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\Fonts') ]
        for keyname in keynames:
            try:
                key = _winreg.OpenKey(*keyname)
                try:
                    path = self._lookup_win(key, self.font_name, STYLES['NORMAL'], True)
                    self.fonts['NORMAL'] = ImageFont.truetype(path, self.font_size)
                    for style in ('ITALIC', 'BOLD', 'BOLDITALIC'):
                        path = self._lookup_win(key, self.font_name, STYLES[style])
                        if path:
                            self.fonts[style] = ImageFont.truetype(path, self.font_size)
                        else:
                            if style == 'BOLDITALIC':
                                self.fonts[style] = self.fonts['BOLD']
                            else:
                                self.fonts[style] = self.fonts['NORMAL']
                    return
                except FontNotFound as err:
                    lookuperror = err
                finally:
                    _winreg.CloseKey(key)
            except OSError:
                pass
        else:
            # If we get here, we checked all registry keys and had no luck
            # We can be in one of two situations now:
            # * All key lookups failed. In this case lookuperror is None and we
            #   will raise a generic error
            # * At least one lookup failed with a FontNotFound error. In this
            #   case, we will raise that as a more specific error
            if lookuperror:
                raise lookuperror
            raise FontNotFound('Can\'t open Windows font registry key')

    def get_char_size(self):
        """
        Get the character size.
        """
        return self.get_text_size('M')

    def get_text_size(self, text):
        """
        Get the text size (width, height).
        """
        font = self.fonts['NORMAL']
        if hasattr(font, 'getbbox'):  # Pillow >= 9.2.0
            return font.getbbox(text)[2:4]
        else:
            return font.getsize(text)

    def get_font(self, bold, oblique):
        """
        Get the font based on bold and italic flags.
        """
        if bold and oblique:
            if self.variable:
                return self.get_style('BOLDITALIC')

            return self.fonts['BOLDITALIC']
        elif bold:
            if self.variable:
                return self.get_style('BOLD')

            return self.fonts['BOLD']
        elif oblique:
            if self.variable:
                return self.get_style('ITALIC')

            return self.fonts['ITALIC']
        else:
            if self.variable:
                return self.get_style('NORMAL')

            return self.fonts['NORMAL']

    def get_style(self, style):
        """
        Get the specified style of the font if it is a variable font.
        If not found, return the normal font.
        """
        font = self.fonts[style]
        for style_name in STYLES[style]:
            try:
                font.set_variation_by_name(style_name)
                return font
            except ValueError:
                pass
            except OSError:
                return font

        return font


class ImageFormatter(Formatter):
    """
    Create a PNG image from source code. This uses the Python Imaging Library to
    generate a pixmap from the source code.

    .. versionadded:: 0.10

    Additional options accepted:

    `image_format`
        An image format to output to that is recognised by PIL, these include:

        * "PNG" (default)
        * "JPEG"
        * "BMP"
        * "GIF"

    `line_pad`
        The extra spacing (in pixels) between each line of text.

        Default: 2

    `font_name`
        The font name to be used as the base font from which others, such as
        bold and italic fonts will be generated.  This really should be a
        monospace font to look sane.
        If a filename or a file-like object is specified, the user must
        provide different styles of the font.

        Default: "Courier New" on Windows, "Menlo" on Mac OS, and
                 "DejaVu Sans Mono" on \\*nix

    `font_size`
        The font size in points to be used.

        Default: 14

    `image_pad`
        The padding, in pixels to be used at each edge of the resulting image.

        Default: 10

    `line_numbers`
        Whether line numbers should be shown: True/False

        Default: True

    `line_number_start`
        The line number of the first line.

        Default: 1

    `line_number_step`
        The step used when printing line numbers.

        Default: 1

    `line_number_bg`
        The background colour (in "#123456" format) of the line number bar, or
        None to use the style background color.

        Default: "#eed"

    `line_number_fg`
        The text color of the line numbers (in "#123456"-like format).

        Default: "#886"

    `line_number_chars`
        The number of columns of line numbers allowable in the line number
        margin.

        Default: 2

    `line_number_bold`
        Whether line numbers will be bold: True/False

        Default: False

    `line_number_italic`
        Whether line numbers will be italicized: True/False

        Default: False

    `line_number_separator`
        Whether a line will be drawn between the line number area and the
        source code area: True/False

        Default: True

    `line_number_pad`
        The horizontal padding (in pixels) between the line number margin, and
        the source code area.

        Default: 6

    `hl_lines`
        Specify a list of lines to be highlighted.

        .. versionadded:: 1.2

        Default: empty list

    `hl_color`
        Specify the color for highlighting lines.

        .. versionadded:: 1.2

        Default: highlight color of the selected style
    """

    # Required by the pygments mapper
    name = 'img'
    aliases = ['img', 'IMG', 'png']
    filenames = ['*.png']

    unicodeoutput = False

    default_image_format = 'png'

    def __init__(self, **options):
        """
        See the class docstring for explanation of options.
        """
        if not pil_available:
            raise PilNotAvailable(
                'Python Imaging Library is required for this formatter')
        Formatter.__init__(self, **options)
        self.encoding = 'latin1'  # let pygments.format() do the right thing
        # Read the style
        self.styles = dict(self.style)
        if self.style.background_color is None:
            self.background_color = '#fff'
        else:
            self.background_color = self.style.background_color
        # Image options
        self.image_format = get_choice_opt(
            options, 'image_format', ['png', 'jpeg', 'gif', 'bmp'],
            self.default_image_format, normcase=True)
        self.image_pad = get_int_opt(options, 'image_pad', 10)
        self.line_pad = get_int_opt(options, 'line_pad', 2)
        # The fonts
        fontsize = get_int_opt(options, 'font_size', 14)
        self.fonts = FontManager(options.get('font_name', ''), fontsize)
        self.fontw, self.fonth = self.fonts.get_char_size()
        # Line number options
        self.line_number_fg = options.get('line_number_fg', '#886')
        self.line_number_bg = options.get('line_number_bg', '#eed')
        self.line_number_chars = get_int_opt(options,
                                             'line_number_chars', 2)
        self.line_number_bold = get_bool_opt(options,
                                             'line_number_bold', False)
        self.line_number_italic = get_bool_opt(options,
                                               'line_number_italic', False)
        self.line_number_pad = get_int_opt(options, 'line_number_pad', 6)
        self.line_numbers = get_bool_opt(options, 'line_numbers', True)
        self.line_number_separator = get_bool_opt(options,
                                                  'line_number_separator', True)
        self.line_number_step = get_int_opt(options, 'line_number_step', 1)
        self.line_number_start = get_int_opt(options, 'line_number_start', 1)
        if self.line_numbers:
            self.line_number_width = (self.fontw * self.line_number_chars +
                                      self.line_number_pad * 2)
        else:
            self.line_number_width = 0
        self.hl_lines = []
        hl_lines_str = get_list_opt(options, 'hl_lines', [])
        for line in hl_lines_str:
            try:
                self.hl_lines.append(int(line))
            except ValueError:
                pass
        self.hl_color = options.get('hl_color',
                                    self.style.highlight_color) or '#f90'
        self.drawables = []

    def get_style_defs(self, arg=''):
        raise NotImplementedError('The -S option is meaningless for the image '
                                  'formatter. Use -O style=<stylename> instead.')

    def _get_line_height(self):
        """
        Get the height of a line.
        """
        return self.fonth + self.line_pad

    def _get_line_y(self, lineno):
        """
        Get the Y coordinate of a line number.
        """
        return lineno * self._get_line_height() + self.image_pad

    def _get_char_width(self):
        """
        Get the width of a character.
        """
        return self.fontw

    def _get_char_x(self, linelength):
        """
        Get the X coordinate of a character position.
        """
        return linelength + self.image_pad + self.line_number_width

    def _get_text_pos(self, linelength, lineno):
        """
        Get the actual position for a character and line position.
        """
        return self._get_char_x(linelength), self._get_line_y(lineno)

    def _get_linenumber_pos(self, lineno):
        """
        Get the actual position for the start of a line number.
        """
        return (self.image_pad, self._get_line_y(lineno))

    def _get_text_color(self, style):
        """
        Get the correct color for the token from the style.
        """
        if style['color'] is not None:
            fill = '#' + style['color']
        else:
            fill = '#000'
        return fill

    def _get_text_bg_color(self, style):
        """
        Get the correct background color for the token from the style.
        """
        if style['bgcolor'] is not None:
            bg_color = '#' + style['bgcolor']
        else:
            bg_color = None
        return bg_color

    def _get_style_font(self, style):
        """
        Get the correct font for the style.
        """
        return self.fonts.get_font(style['bold'], style['italic'])

    def _get_image_size(self, maxlinelength, maxlineno):
        """
        Get the required image size.
        """
        return (self._get_char_x(maxlinelength) + self.image_pad,
                self._get_line_y(maxlineno + 0) + self.image_pad)

    def _draw_linenumber(self, posno, lineno):
        """
        Remember a line number drawable to paint later.
        """
        self._draw_text(
            self._get_linenumber_pos(posno),
            str(lineno).rjust(self.line_number_chars),
            font=self.fonts.get_font(self.line_number_bold,
                                     self.line_number_italic),
            text_fg=self.line_number_fg,
            text_bg=None,
        )

    def _draw_text(self, pos, text, font, text_fg, text_bg):
        """
        Remember a single drawable tuple to paint later.
        """
        self.drawables.append((pos, text, font, text_fg, text_bg))

    def _create_drawables(self, tokensource):
        """
        Create drawables for the token content.
        """
        lineno = charno = maxcharno = 0
        maxlinelength = linelength = 0
        for ttype, value in tokensource:
            while ttype not in self.styles:
                ttype = ttype.parent
            style = self.styles[ttype]
            # TODO: make sure tab expansion happens earlier in the chain.  It
            # really ought to be done on the input, as to do it right here is
            # quite complex.
            value = value.expandtabs(4)
            lines = value.splitlines(True)
            # print lines
            for i, line in enumerate(lines):
                temp = line.rstrip('\n')
                if temp:
                    self._draw_text(
                        self._get_text_pos(linelength, lineno),
                        temp,
                        font = self._get_style_font(style),
                        text_fg = self._get_text_color(style),
                        text_bg = self._get_text_bg_color(style),
                    )
                    temp_width, _ = self.fonts.get_text_size(temp)
                    linelength += temp_width
                    maxlinelength = max(maxlinelength, linelength)
                    charno += len(temp)
                    maxcharno = max(maxcharno, charno)
                if line.endswith('\n'):
                    # add a line for each extra line in the value
                    linelength = 0
                    charno = 0
                    lineno += 1
        self.maxlinelength = maxlinelength
        self.maxcharno = maxcharno
        self.maxlineno = lineno

    def _draw_line_numbers(self):
        """
        Create drawables for the line numbers.
        """
        if not self.line_numbers:
            return
        for p in range(self.maxlineno):
            n = p + self.line_number_start
            if (n % self.line_number_step) == 0:
                self._draw_linenumber(p, n)

    def _paint_line_number_bg(self, im):
        """
        Paint the line number background on the image.
        """
        if not self.line_numbers:
            return
        if self.line_number_fg is None:
            return
        draw = ImageDraw.Draw(im)
        recth = im.size[-1]
        rectw = self.image_pad + self.line_number_width - self.line_number_pad
        draw.rectangle([(0, 0), (rectw, recth)],
                       fill=self.line_number_bg)
        if self.line_number_separator:
            draw.line([(rectw, 0), (rectw, recth)], fill=self.line_number_fg)
        del draw

    def format(self, tokensource, outfile):
        """
        Format ``tokensource``, an iterable of ``(tokentype, tokenstring)``
        tuples and write it into ``outfile``.

        This implementation calculates where it should draw each token on the
        pixmap, then calculates the required pixmap size and draws the items.
        """
        self._create_drawables(tokensource)
        self._draw_line_numbers()
        im = Image.new(
            'RGB',
            self._get_image_size(self.maxlinelength, self.maxlineno),
            self.background_color
        )
        self._paint_line_number_bg(im)
        draw = ImageDraw.Draw(im)
        # Highlight
        if self.hl_lines:
            x = self.image_pad + self.line_number_width - self.line_number_pad + 1
            recth = self._get_line_height()
            rectw = im.size[0] - x
            for linenumber in self.hl_lines:
                y = self._get_line_y(linenumber - 1)
                draw.rectangle([(x, y), (x + rectw, y + recth)],
                               fill=self.hl_color)
        for pos, value, font, text_fg, text_bg in self.drawables:
            if text_bg:
                # see deprecations https://pillow.readthedocs.io/en/stable/releasenotes/9.2.0.html#font-size-and-offset-methods
                if hasattr(draw, 'textsize'):
                    text_size = draw.textsize(text=value, font=font)
                else:
                    text_size = font.getbbox(value)[2:]
                draw.rectangle([pos[0], pos[1], pos[0] + text_size[0], pos[1] + text_size[1]], fill=text_bg)
            draw.text(pos, value, font=font, fill=text_fg)
        im.save(outfile, self.image_format.upper())


# Add one formatter per format, so that the "-f gif" option gives the correct result
# when used in pygmentize.

class GifImageFormatter(ImageFormatter):
    """
    Create a GIF image from source code. This uses the Python Imaging Library to
    generate a pixmap from the source code.

    .. versionadded:: 1.0
    """

    name = 'img_gif'
    aliases = ['gif']
    filenames = ['*.gif']
    default_image_format = 'gif'


class JpgImageFormatter(ImageFormatter):
    """
    Create a JPEG image from source code. This uses the Python Imaging Library to
    generate a pixmap from the source code.

    .. versionadded:: 1.0
    """

    name = 'img_jpg'
    aliases = ['jpg', 'jpeg']
    filenames = ['*.jpg']
    default_image_format = 'jpeg'


class BmpImageFormatter(ImageFormatter):
    """
    Create a bitmap image from source code. This uses the Python Imaging Library to
    generate a pixmap from the source code.

    .. versionadded:: 1.0
    """

    name = 'img_bmp'
    aliases = ['bmp', 'bitmap']
    filenames = ['*.bmp']
    default_image_format = 'bmp'

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\formatters\img.py ===
"""
    pygments.formatters.img
    ~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for Pixmap output.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import os
import sys

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.util import get_bool_opt, get_int_opt, get_list_opt, \
    get_choice_opt

import subprocess

# Import this carefully
try:
    from PIL import Image, ImageDraw, ImageFont
    pil_available = True
except ImportError:
    pil_available = False

try:
    import _winreg
except ImportError:
    try:
        import winreg as _winreg
    except ImportError:
        _winreg = None

__all__ = ['ImageFormatter', 'GifImageFormatter', 'JpgImageFormatter',
           'BmpImageFormatter']


# For some unknown reason every font calls it something different
STYLES = {
    'NORMAL':     ['', 'Roman', 'Book', 'Normal', 'Regular', 'Medium'],
    'ITALIC':     ['Oblique', 'Italic'],
    'BOLD':       ['Bold'],
    'BOLDITALIC': ['Bold Oblique', 'Bold Italic'],
}

# A sane default for modern systems
DEFAULT_FONT_NAME_NIX = 'DejaVu Sans Mono'
DEFAULT_FONT_NAME_WIN = 'Courier New'
DEFAULT_FONT_NAME_MAC = 'Menlo'


class PilNotAvailable(ImportError):
    """When Python imaging library is not available"""


class FontNotFound(Exception):
    """When there are no usable fonts specified"""


class FontManager:
    """
    Manages a set of fonts: normal, italic, bold, etc...
    """

    def __init__(self, font_name, font_size=14):
        self.font_name = font_name
        self.font_size = font_size
        self.fonts = {}
        self.encoding = None
        self.variable = False
        if hasattr(font_name, 'read') or os.path.isfile(font_name):
            font = ImageFont.truetype(font_name, self.font_size)
            self.variable = True
            for style in STYLES:
                self.fonts[style] = font

            return

        if sys.platform.startswith('win'):
            if not font_name:
                self.font_name = DEFAULT_FONT_NAME_WIN
            self._create_win()
        elif sys.platform.startswith('darwin'):
            if not font_name:
                self.font_name = DEFAULT_FONT_NAME_MAC
            self._create_mac()
        else:
            if not font_name:
                self.font_name = DEFAULT_FONT_NAME_NIX
            self._create_nix()

    def _get_nix_font_path(self, name, style):
        proc = subprocess.Popen(['fc-list', f"{name}:style={style}", 'file'],
                                stdout=subprocess.PIPE, stderr=None)
        stdout, _ = proc.communicate()
        if proc.returncode == 0:
            lines = stdout.splitlines()
            for line in lines:
                if line.startswith(b'Fontconfig warning:'):
                    continue
                path = line.decode().strip().strip(':')
                if path:
                    return path
            return None

    def _create_nix(self):
        for name in STYLES['NORMAL']:
            path = self._get_nix_font_path(self.font_name, name)
            if path is not None:
                self.fonts['NORMAL'] = ImageFont.truetype(path, self.font_size)
                break
        else:
            raise FontNotFound(f'No usable fonts named: "{self.font_name}"')
        for style in ('ITALIC', 'BOLD', 'BOLDITALIC'):
            for stylename in STYLES[style]:
                path = self._get_nix_font_path(self.font_name, stylename)
                if path is not None:
                    self.fonts[style] = ImageFont.truetype(path, self.font_size)
                    break
            else:
                if style == 'BOLDITALIC':
                    self.fonts[style] = self.fonts['BOLD']
                else:
                    self.fonts[style] = self.fonts['NORMAL']

    def _get_mac_font_path(self, font_map, name, style):
        return font_map.get((name + ' ' + style).strip().lower())

    def _create_mac(self):
        font_map = {}
        for font_dir in (os.path.join(os.getenv("HOME"), 'Library/Fonts/'),
                         '/Library/Fonts/', '/System/Library/Fonts/'):
            font_map.update(
                (os.path.splitext(f)[0].lower(), os.path.join(font_dir, f))
                for f in os.listdir(font_dir)
                if f.lower().endswith(('ttf', 'ttc')))

        for name in STYLES['NORMAL']:
            path = self._get_mac_font_path(font_map, self.font_name, name)
            if path is not None:
                self.fonts['NORMAL'] = ImageFont.truetype(path, self.font_size)
                break
        else:
            raise FontNotFound(f'No usable fonts named: "{self.font_name}"')
        for style in ('ITALIC', 'BOLD', 'BOLDITALIC'):
            for stylename in STYLES[style]:
                path = self._get_mac_font_path(font_map, self.font_name, stylename)
                if path is not None:
                    self.fonts[style] = ImageFont.truetype(path, self.font_size)
                    break
            else:
                if style == 'BOLDITALIC':
                    self.fonts[style] = self.fonts['BOLD']
                else:
                    self.fonts[style] = self.fonts['NORMAL']

    def _lookup_win(self, key, basename, styles, fail=False):
        for suffix in ('', ' (TrueType)'):
            for style in styles:
                try:
                    valname = '{}{}{}'.format(basename, style and ' '+style, suffix)
                    val, _ = _winreg.QueryValueEx(key, valname)
                    return val
                except OSError:
                    continue
        else:
            if fail:
                raise FontNotFound(f'Font {basename} ({styles[0]}) not found in registry')
            return None

    def _create_win(self):
        lookuperror = None
        keynames = [ (_winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows NT\CurrentVersion\Fonts'),
                     (_winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Fonts'),
                     (_winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows NT\CurrentVersion\Fonts'),
                     (_winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\Fonts') ]
        for keyname in keynames:
            try:
                key = _winreg.OpenKey(*keyname)
                try:
                    path = self._lookup_win(key, self.font_name, STYLES['NORMAL'], True)
                    self.fonts['NORMAL'] = ImageFont.truetype(path, self.font_size)
                    for style in ('ITALIC', 'BOLD', 'BOLDITALIC'):
                        path = self._lookup_win(key, self.font_name, STYLES[style])
                        if path:
                            self.fonts[style] = ImageFont.truetype(path, self.font_size)
                        else:
                            if style == 'BOLDITALIC':
                                self.fonts[style] = self.fonts['BOLD']
                            else:
                                self.fonts[style] = self.fonts['NORMAL']
                    return
                except FontNotFound as err:
                    lookuperror = err
                finally:
                    _winreg.CloseKey(key)
            except OSError:
                pass
        else:
            # If we get here, we checked all registry keys and had no luck
            # We can be in one of two situations now:
            # * All key lookups failed. In this case lookuperror is None and we
            #   will raise a generic error
            # * At least one lookup failed with a FontNotFound error. In this
            #   case, we will raise that as a more specific error
            if lookuperror:
                raise lookuperror
            raise FontNotFound('Can\'t open Windows font registry key')

    def get_char_size(self):
        """
        Get the character size.
        """
        return self.get_text_size('M')

    def get_text_size(self, text):
        """
        Get the text size (width, height).
        """
        font = self.fonts['NORMAL']
        if hasattr(font, 'getbbox'):  # Pillow >= 9.2.0
            return font.getbbox(text)[2:4]
        else:
            return font.getsize(text)

    def get_font(self, bold, oblique):
        """
        Get the font based on bold and italic flags.
        """
        if bold and oblique:
            if self.variable:
                return self.get_style('BOLDITALIC')

            return self.fonts['BOLDITALIC']
        elif bold:
            if self.variable:
                return self.get_style('BOLD')

            return self.fonts['BOLD']
        elif oblique:
            if self.variable:
                return self.get_style('ITALIC')

            return self.fonts['ITALIC']
        else:
            if self.variable:
                return self.get_style('NORMAL')

            return self.fonts['NORMAL']

    def get_style(self, style):
        """
        Get the specified style of the font if it is a variable font.
        If not found, return the normal font.
        """
        font = self.fonts[style]
        for style_name in STYLES[style]:
            try:
                font.set_variation_by_name(style_name)
                return font
            except ValueError:
                pass
            except OSError:
                return font

        return font


class ImageFormatter(Formatter):
    """
    Create a PNG image from source code. This uses the Python Imaging Library to
    generate a pixmap from the source code.

    .. versionadded:: 0.10

    Additional options accepted:

    `image_format`
        An image format to output to that is recognised by PIL, these include:

        * "PNG" (default)
        * "JPEG"
        * "BMP"
        * "GIF"

    `line_pad`
        The extra spacing (in pixels) between each line of text.

        Default: 2

    `font_name`
        The font name to be used as the base font from which others, such as
        bold and italic fonts will be generated.  This really should be a
        monospace font to look sane.
        If a filename or a file-like object is specified, the user must
        provide different styles of the font.

        Default: "Courier New" on Windows, "Menlo" on Mac OS, and
                 "DejaVu Sans Mono" on \\*nix

    `font_size`
        The font size in points to be used.

        Default: 14

    `image_pad`
        The padding, in pixels to be used at each edge of the resulting image.

        Default: 10

    `line_numbers`
        Whether line numbers should be shown: True/False

        Default: True

    `line_number_start`
        The line number of the first line.

        Default: 1

    `line_number_step`
        The step used when printing line numbers.

        Default: 1

    `line_number_bg`
        The background colour (in "#123456" format) of the line number bar, or
        None to use the style background color.

        Default: "#eed"

    `line_number_fg`
        The text color of the line numbers (in "#123456"-like format).

        Default: "#886"

    `line_number_chars`
        The number of columns of line numbers allowable in the line number
        margin.

        Default: 2

    `line_number_bold`
        Whether line numbers will be bold: True/False

        Default: False

    `line_number_italic`
        Whether line numbers will be italicized: True/False

        Default: False

    `line_number_separator`
        Whether a line will be drawn between the line number area and the
        source code area: True/False

        Default: True

    `line_number_pad`
        The horizontal padding (in pixels) between the line number margin, and
        the source code area.

        Default: 6

    `hl_lines`
        Specify a list of lines to be highlighted.

        .. versionadded:: 1.2

        Default: empty list

    `hl_color`
        Specify the color for highlighting lines.

        .. versionadded:: 1.2

        Default: highlight color of the selected style
    """

    # Required by the pygments mapper
    name = 'img'
    aliases = ['img', 'IMG', 'png']
    filenames = ['*.png']

    unicodeoutput = False

    default_image_format = 'png'

    def __init__(self, **options):
        """
        See the class docstring for explanation of options.
        """
        if not pil_available:
            raise PilNotAvailable(
                'Python Imaging Library is required for this formatter')
        Formatter.__init__(self, **options)
        self.encoding = 'latin1'  # let pygments.format() do the right thing
        # Read the style
        self.styles = dict(self.style)
        if self.style.background_color is None:
            self.background_color = '#fff'
        else:
            self.background_color = self.style.background_color
        # Image options
        self.image_format = get_choice_opt(
            options, 'image_format', ['png', 'jpeg', 'gif', 'bmp'],
            self.default_image_format, normcase=True)
        self.image_pad = get_int_opt(options, 'image_pad', 10)
        self.line_pad = get_int_opt(options, 'line_pad', 2)
        # The fonts
        fontsize = get_int_opt(options, 'font_size', 14)
        self.fonts = FontManager(options.get('font_name', ''), fontsize)
        self.fontw, self.fonth = self.fonts.get_char_size()
        # Line number options
        self.line_number_fg = options.get('line_number_fg', '#886')
        self.line_number_bg = options.get('line_number_bg', '#eed')
        self.line_number_chars = get_int_opt(options,
                                             'line_number_chars', 2)
        self.line_number_bold = get_bool_opt(options,
                                             'line_number_bold', False)
        self.line_number_italic = get_bool_opt(options,
                                               'line_number_italic', False)
        self.line_number_pad = get_int_opt(options, 'line_number_pad', 6)
        self.line_numbers = get_bool_opt(options, 'line_numbers', True)
        self.line_number_separator = get_bool_opt(options,
                                                  'line_number_separator', True)
        self.line_number_step = get_int_opt(options, 'line_number_step', 1)
        self.line_number_start = get_int_opt(options, 'line_number_start', 1)
        if self.line_numbers:
            self.line_number_width = (self.fontw * self.line_number_chars +
                                      self.line_number_pad * 2)
        else:
            self.line_number_width = 0
        self.hl_lines = []
        hl_lines_str = get_list_opt(options, 'hl_lines', [])
        for line in hl_lines_str:
            try:
                self.hl_lines.append(int(line))
            except ValueError:
                pass
        self.hl_color = options.get('hl_color',
                                    self.style.highlight_color) or '#f90'
        self.drawables = []

    def get_style_defs(self, arg=''):
        raise NotImplementedError('The -S option is meaningless for the image '
                                  'formatter. Use -O style=<stylename> instead.')

    def _get_line_height(self):
        """
        Get the height of a line.
        """
        return self.fonth + self.line_pad

    def _get_line_y(self, lineno):
        """
        Get the Y coordinate of a line number.
        """
        return lineno * self._get_line_height() + self.image_pad

    def _get_char_width(self):
        """
        Get the width of a character.
        """
        return self.fontw

    def _get_char_x(self, linelength):
        """
        Get the X coordinate of a character position.
        """
        return linelength + self.image_pad + self.line_number_width

    def _get_text_pos(self, linelength, lineno):
        """
        Get the actual position for a character and line position.
        """
        return self._get_char_x(linelength), self._get_line_y(lineno)

    def _get_linenumber_pos(self, lineno):
        """
        Get the actual position for the start of a line number.
        """
        return (self.image_pad, self._get_line_y(lineno))

    def _get_text_color(self, style):
        """
        Get the correct color for the token from the style.
        """
        if style['color'] is not None:
            fill = '#' + style['color']
        else:
            fill = '#000'
        return fill

    def _get_text_bg_color(self, style):
        """
        Get the correct background color for the token from the style.
        """
        if style['bgcolor'] is not None:
            bg_color = '#' + style['bgcolor']
        else:
            bg_color = None
        return bg_color

    def _get_style_font(self, style):
        """
        Get the correct font for the style.
        """
        return self.fonts.get_font(style['bold'], style['italic'])

    def _get_image_size(self, maxlinelength, maxlineno):
        """
        Get the required image size.
        """
        return (self._get_char_x(maxlinelength) + self.image_pad,
                self._get_line_y(maxlineno + 0) + self.image_pad)

    def _draw_linenumber(self, posno, lineno):
        """
        Remember a line number drawable to paint later.
        """
        self._draw_text(
            self._get_linenumber_pos(posno),
            str(lineno).rjust(self.line_number_chars),
            font=self.fonts.get_font(self.line_number_bold,
                                     self.line_number_italic),
            text_fg=self.line_number_fg,
            text_bg=None,
        )

    def _draw_text(self, pos, text, font, text_fg, text_bg):
        """
        Remember a single drawable tuple to paint later.
        """
        self.drawables.append((pos, text, font, text_fg, text_bg))

    def _create_drawables(self, tokensource):
        """
        Create drawables for the token content.
        """
        lineno = charno = maxcharno = 0
        maxlinelength = linelength = 0
        for ttype, value in tokensource:
            while ttype not in self.styles:
                ttype = ttype.parent
            style = self.styles[ttype]
            # TODO: make sure tab expansion happens earlier in the chain.  It
            # really ought to be done on the input, as to do it right here is
            # quite complex.
            value = value.expandtabs(4)
            lines = value.splitlines(True)
            # print lines
            for i, line in enumerate(lines):
                temp = line.rstrip('\n')
                if temp:
                    self._draw_text(
                        self._get_text_pos(linelength, lineno),
                        temp,
                        font = self._get_style_font(style),
                        text_fg = self._get_text_color(style),
                        text_bg = self._get_text_bg_color(style),
                    )
                    temp_width, _ = self.fonts.get_text_size(temp)
                    linelength += temp_width
                    maxlinelength = max(maxlinelength, linelength)
                    charno += len(temp)
                    maxcharno = max(maxcharno, charno)
                if line.endswith('\n'):
                    # add a line for each extra line in the value
                    linelength = 0
                    charno = 0
                    lineno += 1
        self.maxlinelength = maxlinelength
        self.maxcharno = maxcharno
        self.maxlineno = lineno

    def _draw_line_numbers(self):
        """
        Create drawables for the line numbers.
        """
        if not self.line_numbers:
            return
        for p in range(self.maxlineno):
            n = p + self.line_number_start
            if (n % self.line_number_step) == 0:
                self._draw_linenumber(p, n)

    def _paint_line_number_bg(self, im):
        """
        Paint the line number background on the image.
        """
        if not self.line_numbers:
            return
        if self.line_number_fg is None:
            return
        draw = ImageDraw.Draw(im)
        recth = im.size[-1]
        rectw = self.image_pad + self.line_number_width - self.line_number_pad
        draw.rectangle([(0, 0), (rectw, recth)],
                       fill=self.line_number_bg)
        if self.line_number_separator:
            draw.line([(rectw, 0), (rectw, recth)], fill=self.line_number_fg)
        del draw

    def format(self, tokensource, outfile):
        """
        Format ``tokensource``, an iterable of ``(tokentype, tokenstring)``
        tuples and write it into ``outfile``.

        This implementation calculates where it should draw each token on the
        pixmap, then calculates the required pixmap size and draws the items.
        """
        self._create_drawables(tokensource)
        self._draw_line_numbers()
        im = Image.new(
            'RGB',
            self._get_image_size(self.maxlinelength, self.maxlineno),
            self.background_color
        )
        self._paint_line_number_bg(im)
        draw = ImageDraw.Draw(im)
        # Highlight
        if self.hl_lines:
            x = self.image_pad + self.line_number_width - self.line_number_pad + 1
            recth = self._get_line_height()
            rectw = im.size[0] - x
            for linenumber in self.hl_lines:
                y = self._get_line_y(linenumber - 1)
                draw.rectangle([(x, y), (x + rectw, y + recth)],
                               fill=self.hl_color)
        for pos, value, font, text_fg, text_bg in self.drawables:
            if text_bg:
                # see deprecations https://pillow.readthedocs.io/en/stable/releasenotes/9.2.0.html#font-size-and-offset-methods
                if hasattr(draw, 'textsize'):
                    text_size = draw.textsize(text=value, font=font)
                else:
                    text_size = font.getbbox(value)[2:]
                draw.rectangle([pos[0], pos[1], pos[0] + text_size[0], pos[1] + text_size[1]], fill=text_bg)
            draw.text(pos, value, font=font, fill=text_fg)
        im.save(outfile, self.image_format.upper())


# Add one formatter per format, so that the "-f gif" option gives the correct result
# when used in pygmentize.

class GifImageFormatter(ImageFormatter):
    """
    Create a GIF image from source code. This uses the Python Imaging Library to
    generate a pixmap from the source code.

    .. versionadded:: 1.0
    """

    name = 'img_gif'
    aliases = ['gif']
    filenames = ['*.gif']
    default_image_format = 'gif'


class JpgImageFormatter(ImageFormatter):
    """
    Create a JPEG image from source code. This uses the Python Imaging Library to
    generate a pixmap from the source code.

    .. versionadded:: 1.0
    """

    name = 'img_jpg'
    aliases = ['jpg', 'jpeg']
    filenames = ['*.jpg']
    default_image_format = 'jpeg'


class BmpImageFormatter(ImageFormatter):
    """
    Create a bitmap image from source code. This uses the Python Imaging Library to
    generate a pixmap from the source code.

    .. versionadded:: 1.0
    """

    name = 'img_bmp'
    aliases = ['bmp', 'bitmap']
    filenames = ['*.bmp']
    default_image_format = 'bmp'

# === NexusCore/openenv\Lib\site-packages\google\auth\_default.py ===
# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Application default credentials.

Implements application default credentials and project ID detection.
"""

import io
import json
import logging
import os
import warnings

from google.auth import environment_vars
from google.auth import exceptions
import google.auth.transport._http_client

_LOGGER = logging.getLogger(__name__)

# Valid types accepted for file-based credentials.
_AUTHORIZED_USER_TYPE = "authorized_user"
_SERVICE_ACCOUNT_TYPE = "service_account"
_EXTERNAL_ACCOUNT_TYPE = "external_account"
_EXTERNAL_ACCOUNT_AUTHORIZED_USER_TYPE = "external_account_authorized_user"
_IMPERSONATED_SERVICE_ACCOUNT_TYPE = "impersonated_service_account"
_GDCH_SERVICE_ACCOUNT_TYPE = "gdch_service_account"
_VALID_TYPES = (
    _AUTHORIZED_USER_TYPE,
    _SERVICE_ACCOUNT_TYPE,
    _EXTERNAL_ACCOUNT_TYPE,
    _EXTERNAL_ACCOUNT_AUTHORIZED_USER_TYPE,
    _IMPERSONATED_SERVICE_ACCOUNT_TYPE,
    _GDCH_SERVICE_ACCOUNT_TYPE,
)

# Help message when no credentials can be found.
_CLOUD_SDK_MISSING_CREDENTIALS = """\
Your default credentials were not found. To set up Application Default Credentials, \
see https://cloud.google.com/docs/authentication/external/set-up-adc for more information.\
"""

# Warning when using Cloud SDK user credentials
_CLOUD_SDK_CREDENTIALS_WARNING = """\
Your application has authenticated using end user credentials from Google \
Cloud SDK without a quota project. You might receive a "quota exceeded" \
or "API not enabled" error. See the following page for troubleshooting: \
https://cloud.google.com/docs/authentication/adc-troubleshooting/user-creds. \
"""

# The subject token type used for AWS external_account credentials.
_AWS_SUBJECT_TOKEN_TYPE = "urn:ietf:params:aws:token-type:aws4_request"


def _warn_about_problematic_credentials(credentials):
    """Determines if the credentials are problematic.

    Credentials from the Cloud SDK that are associated with Cloud SDK's project
    are problematic because they may not have APIs enabled and have limited
    quota. If this is the case, warn about it.
    """
    from google.auth import _cloud_sdk

    if credentials.client_id == _cloud_sdk.CLOUD_SDK_CLIENT_ID:
        warnings.warn(_CLOUD_SDK_CREDENTIALS_WARNING)


def load_credentials_from_file(
    filename, scopes=None, default_scopes=None, quota_project_id=None, request=None
):
    """Loads Google credentials from a file.

    The credentials file must be a service account key, stored authorized
    user credentials, external account credentials, or impersonated service
    account credentials.

    .. warning::
        Important: If you accept a credential configuration (credential JSON/File/Stream)
        from an external source for authentication to Google Cloud Platform, you must
        validate it before providing it to any Google API or client library. Providing an
        unvalidated credential configuration to Google APIs or libraries can compromise
        the security of your systems and data. For more information, refer to
        `Validate credential configurations from external sources`_.

        .. _Validate credential configurations from external sources:
            https://cloud.google.com/docs/authentication/external/externally-sourced-credentials

    Args:
        filename (str): The full path to the credentials file.
        scopes (Optional[Sequence[str]]): The list of scopes for the credentials. If
            specified, the credentials will automatically be scoped if
            necessary
        default_scopes (Optional[Sequence[str]]): Default scopes passed by a
            Google client library. Use 'scopes' for user-defined scopes.
        quota_project_id (Optional[str]):  The project ID used for
            quota and billing.
        request (Optional[google.auth.transport.Request]): An object used to make
            HTTP requests. This is used to determine the associated project ID
            for a workload identity pool resource (external account credentials).
            If not specified, then it will use a
            google.auth.transport.requests.Request client to make requests.

    Returns:
        Tuple[google.auth.credentials.Credentials, Optional[str]]: Loaded
            credentials and the project ID. Authorized user credentials do not
            have the project ID information. External account credentials project
            IDs may not always be determined.

    Raises:
        google.auth.exceptions.DefaultCredentialsError: if the file is in the
            wrong format or is missing.
    """
    if not os.path.exists(filename):
        raise exceptions.DefaultCredentialsError(
            "File {} was not found.".format(filename)
        )

    with io.open(filename, "r") as file_obj:
        try:
            info = json.load(file_obj)
        except ValueError as caught_exc:
            new_exc = exceptions.DefaultCredentialsError(
                "File {} is not a valid json file.".format(filename), caught_exc
            )
            raise new_exc from caught_exc
    return _load_credentials_from_info(
        filename, info, scopes, default_scopes, quota_project_id, request
    )


def load_credentials_from_dict(
    info, scopes=None, default_scopes=None, quota_project_id=None, request=None
):
    """Loads Google credentials from a dict.

    The credentials file must be a service account key, stored authorized
    user credentials, external account credentials, or impersonated service
    account credentials.

    .. warning::
        Important: If you accept a credential configuration (credential JSON/File/Stream)
        from an external source for authentication to Google Cloud Platform, you must
        validate it before providing it to any Google API or client library. Providing an
        unvalidated credential configuration to Google APIs or libraries can compromise
        the security of your systems and data. For more information, refer to
        `Validate credential configurations from external sources`_.

    .. _Validate credential configurations from external sources:
        https://cloud.google.com/docs/authentication/external/externally-sourced-credentials

    Args:
        info (Dict[str, Any]): A dict object containing the credentials
        scopes (Optional[Sequence[str]]): The list of scopes for the credentials. If
            specified, the credentials will automatically be scoped if
            necessary
        default_scopes (Optional[Sequence[str]]): Default scopes passed by a
            Google client library. Use 'scopes' for user-defined scopes.
        quota_project_id (Optional[str]):  The project ID used for
            quota and billing.
        request (Optional[google.auth.transport.Request]): An object used to make
            HTTP requests. This is used to determine the associated project ID
            for a workload identity pool resource (external account credentials).
            If not specified, then it will use a
            google.auth.transport.requests.Request client to make requests.

    Returns:
        Tuple[google.auth.credentials.Credentials, Optional[str]]: Loaded
            credentials and the project ID. Authorized user credentials do not
            have the project ID information. External account credentials project
            IDs may not always be determined.

    Raises:
        google.auth.exceptions.DefaultCredentialsError: if the file is in the
            wrong format or is missing.
    """
    if not isinstance(info, dict):
        raise exceptions.DefaultCredentialsError(
            "info object was of type {} but dict type was expected.".format(type(info))
        )

    return _load_credentials_from_info(
        "dict object", info, scopes, default_scopes, quota_project_id, request
    )


def _load_credentials_from_info(
    filename, info, scopes, default_scopes, quota_project_id, request
):
    from google.auth.credentials import CredentialsWithQuotaProject

    credential_type = info.get("type")

    if credential_type == _AUTHORIZED_USER_TYPE:
        credentials, project_id = _get_authorized_user_credentials(
            filename, info, scopes
        )

    elif credential_type == _SERVICE_ACCOUNT_TYPE:
        credentials, project_id = _get_service_account_credentials(
            filename, info, scopes, default_scopes
        )

    elif credential_type == _EXTERNAL_ACCOUNT_TYPE:
        credentials, project_id = _get_external_account_credentials(
            info,
            filename,
            scopes=scopes,
            default_scopes=default_scopes,
            request=request,
        )

    elif credential_type == _EXTERNAL_ACCOUNT_AUTHORIZED_USER_TYPE:
        credentials, project_id = _get_external_account_authorized_user_credentials(
            filename, info, request
        )

    elif credential_type == _IMPERSONATED_SERVICE_ACCOUNT_TYPE:
        credentials, project_id = _get_impersonated_service_account_credentials(
            filename, info, scopes
        )
    elif credential_type == _GDCH_SERVICE_ACCOUNT_TYPE:
        credentials, project_id = _get_gdch_service_account_credentials(filename, info)
    else:
        raise exceptions.DefaultCredentialsError(
            "The file {file} does not have a valid type. "
            "Type is {type}, expected one of {valid_types}.".format(
                file=filename, type=credential_type, valid_types=_VALID_TYPES
            )
        )
    if isinstance(credentials, CredentialsWithQuotaProject):
        credentials = _apply_quota_project_id(credentials, quota_project_id)
    return credentials, project_id


def _get_gcloud_sdk_credentials(quota_project_id=None):
    """Gets the credentials and project ID from the Cloud SDK."""
    from google.auth import _cloud_sdk

    _LOGGER.debug("Checking Cloud SDK credentials as part of auth process...")

    # Check if application default credentials exist.
    credentials_filename = _cloud_sdk.get_application_default_credentials_path()

    if not os.path.isfile(credentials_filename):
        _LOGGER.debug("Cloud SDK credentials not found on disk; not using them")
        return None, None

    credentials, project_id = load_credentials_from_file(
        credentials_filename, quota_project_id=quota_project_id
    )
    credentials._cred_file_path = credentials_filename

    if not project_id:
        project_id = _cloud_sdk.get_project_id()

    return credentials, project_id


def _get_explicit_environ_credentials(quota_project_id=None):
    """Gets credentials from the GOOGLE_APPLICATION_CREDENTIALS environment
    variable."""
    from google.auth import _cloud_sdk

    cloud_sdk_adc_path = _cloud_sdk.get_application_default_credentials_path()
    explicit_file = os.environ.get(environment_vars.CREDENTIALS)

    _LOGGER.debug(
        "Checking %s for explicit credentials as part of auth process...", explicit_file
    )

    if explicit_file is not None and explicit_file == cloud_sdk_adc_path:
        # Cloud sdk flow calls gcloud to fetch project id, so if the explicit
        # file path is cloud sdk credentials path, then we should fall back
        # to cloud sdk flow, otherwise project id cannot be obtained.
        _LOGGER.debug(
            "Explicit credentials path %s is the same as Cloud SDK credentials path, fall back to Cloud SDK credentials flow...",
            explicit_file,
        )
        return _get_gcloud_sdk_credentials(quota_project_id=quota_project_id)

    if explicit_file is not None:
        credentials, project_id = load_credentials_from_file(
            os.environ[environment_vars.CREDENTIALS], quota_project_id=quota_project_id
        )
        credentials._cred_file_path = f"{explicit_file} file via the GOOGLE_APPLICATION_CREDENTIALS environment variable"

        return credentials, project_id

    else:
        return None, None


def _get_gae_credentials():
    """Gets Google App Engine App Identity credentials and project ID."""
    # If not GAE gen1, prefer the metadata service even if the GAE APIs are
    # available as per https://google.aip.dev/auth/4115.
    if os.environ.get(environment_vars.LEGACY_APPENGINE_RUNTIME) != "python27":
        return None, None

    # While this library is normally bundled with app_engine, there are
    # some cases where it's not available, so we tolerate ImportError.
    try:
        _LOGGER.debug("Checking for App Engine runtime as part of auth process...")
        import google.auth.app_engine as app_engine
    except ImportError:
        _LOGGER.warning("Import of App Engine auth library failed.")
        return None, None

    try:
        credentials = app_engine.Credentials()
        project_id = app_engine.get_project_id()
        return credentials, project_id
    except EnvironmentError:
        _LOGGER.debug(
            "No App Engine library was found so cannot authentication via App Engine Identity Credentials."
        )
        return None, None


def _get_gce_credentials(request=None, quota_project_id=None):
    """Gets credentials and project ID from the GCE Metadata Service."""
    # Ping requires a transport, but we want application default credentials
    # to require no arguments. So, we'll use the _http_client transport which
    # uses http.client. This is only acceptable because the metadata server
    # doesn't do SSL and never requires proxies.

    # While this library is normally bundled with compute_engine, there are
    # some cases where it's not available, so we tolerate ImportError.
    try:
        from google.auth import compute_engine
        from google.auth.compute_engine import _metadata
    except ImportError:
        _LOGGER.warning("Import of Compute Engine auth library failed.")
        return None, None

    if request is None:
        request = google.auth.transport._http_client.Request()

    if _metadata.is_on_gce(request=request):
        # Get the project ID.
        try:
            project_id = _metadata.get_project_id(request=request)
        except exceptions.TransportError:
            project_id = None

        cred = compute_engine.Credentials()
        cred = _apply_quota_project_id(cred, quota_project_id)

        return cred, project_id
    else:
        _LOGGER.warning(
            "Authentication failed using Compute Engine authentication due to unavailable metadata server."
        )
        return None, None


def _get_external_account_credentials(
    info, filename, scopes=None, default_scopes=None, request=None
):
    """Loads external account Credentials from the parsed external account info.

    The credentials information must correspond to a supported external account
    credentials.

    Args:
        info (Mapping[str, str]): The external account info in Google format.
        filename (str): The full path to the credentials file.
        scopes (Optional[Sequence[str]]): The list of scopes for the credentials. If
            specified, the credentials will automatically be scoped if
            necessary.
        default_scopes (Optional[Sequence[str]]): Default scopes passed by a
            Google client library. Use 'scopes' for user-defined scopes.
        request (Optional[google.auth.transport.Request]): An object used to make
            HTTP requests. This is used to determine the associated project ID
            for a workload identity pool resource (external account credentials).
            If not specified, then it will use a
            google.auth.transport.requests.Request client to make requests.

    Returns:
        Tuple[google.auth.credentials.Credentials, Optional[str]]: Loaded
            credentials and the project ID. External account credentials project
            IDs may not always be determined.

    Raises:
        google.auth.exceptions.DefaultCredentialsError: if the info dictionary
            is in the wrong format or is missing required information.
    """
    # There are currently 3 types of external_account credentials.
    if info.get("subject_token_type") == _AWS_SUBJECT_TOKEN_TYPE:
        # Check if configuration corresponds to an AWS credentials.
        from google.auth import aws

        credentials = aws.Credentials.from_info(
            info, scopes=scopes, default_scopes=default_scopes
        )
    elif (
        info.get("credential_source") is not None
        and info.get("credential_source").get("executable") is not None
    ):
        from google.auth import pluggable

        credentials = pluggable.Credentials.from_info(
            info, scopes=scopes, default_scopes=default_scopes
        )
    else:
        try:
            # Check if configuration corresponds to an Identity Pool credentials.
            from google.auth import identity_pool

            credentials = identity_pool.Credentials.from_info(
                info, scopes=scopes, default_scopes=default_scopes
            )
        except ValueError:
            # If the configuration is invalid or does not correspond to any
            # supported external_account credentials, raise an error.
            raise exceptions.DefaultCredentialsError(
                "Failed to load external account credentials from {}".format(filename)
            )
    if request is None:
        import google.auth.transport.requests

        request = google.auth.transport.requests.Request()

    return credentials, credentials.get_project_id(request=request)


def _get_external_account_authorized_user_credentials(
    filename, info, scopes=None, default_scopes=None, request=None
):
    try:
        from google.auth import external_account_authorized_user

        credentials = external_account_authorized_user.Credentials.from_info(info)
    except ValueError:
        raise exceptions.DefaultCredentialsError(
            "Failed to load external account authorized user credentials from {}".format(
                filename
            )
        )

    return credentials, None


def _get_authorized_user_credentials(filename, info, scopes=None):
    from google.oauth2 import credentials

    try:
        credentials = credentials.Credentials.from_authorized_user_info(
            info, scopes=scopes
        )
    except ValueError as caught_exc:
        msg = "Failed to load authorized user credentials from {}".format(filename)
        new_exc = exceptions.DefaultCredentialsError(msg, caught_exc)
        raise new_exc from caught_exc
    return credentials, None


def _get_service_account_credentials(filename, info, scopes=None, default_scopes=None):
    from google.oauth2 import service_account

    try:
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=scopes, default_scopes=default_scopes
        )
    except ValueError as caught_exc:
        msg = "Failed to load service account credentials from {}".format(filename)
        new_exc = exceptions.DefaultCredentialsError(msg, caught_exc)
        raise new_exc from caught_exc
    return credentials, info.get("project_id")


def _get_impersonated_service_account_credentials(filename, info, scopes):
    from google.auth import impersonated_credentials

    try:
        credentials = impersonated_credentials.Credentials.from_impersonated_service_account_info(
            info, scopes=scopes
        )
    except ValueError as caught_exc:
        msg = "Failed to load impersonated service account credentials from {}".format(
            filename
        )
        new_exc = exceptions.DefaultCredentialsError(msg, caught_exc)
        raise new_exc from caught_exc
    return credentials, None


def _get_gdch_service_account_credentials(filename, info):
    from google.oauth2 import gdch_credentials

    try:
        credentials = gdch_credentials.ServiceAccountCredentials.from_service_account_info(
            info
        )
    except ValueError as caught_exc:
        msg = "Failed to load GDCH service account credentials from {}".format(filename)
        new_exc = exceptions.DefaultCredentialsError(msg, caught_exc)
        raise new_exc from caught_exc
    return credentials, info.get("project")


def get_api_key_credentials(key):
    """Return credentials with the given API key."""
    from google.auth import api_key

    return api_key.Credentials(key)


def _apply_quota_project_id(credentials, quota_project_id):
    if quota_project_id:
        credentials = credentials.with_quota_project(quota_project_id)
    else:
        credentials = credentials.with_quota_project_from_environment()

    from google.oauth2 import credentials as authorized_user_credentials

    if isinstance(credentials, authorized_user_credentials.Credentials) and (
        not credentials.quota_project_id
    ):
        _warn_about_problematic_credentials(credentials)
    return credentials


def default(scopes=None, request=None, quota_project_id=None, default_scopes=None):
    """Gets the default credentials for the current environment.

    `Application Default Credentials`_ provides an easy way to obtain
    credentials to call Google APIs for server-to-server or local applications.
    This function acquires credentials from the environment in the following
    order:

    1. If the environment variable ``GOOGLE_APPLICATION_CREDENTIALS`` is set
       to the path of a valid service account JSON private key file, then it is
       loaded and returned. The project ID returned is the project ID defined
       in the service account file if available (some older files do not
       contain project ID information).

       If the environment variable is set to the path of a valid external
       account JSON configuration file (workload identity federation), then the
       configuration file is used to determine and retrieve the external
       credentials from the current environment (AWS, Azure, etc).
       These will then be exchanged for Google access tokens via the Google STS
       endpoint.
       The project ID returned in this case is the one corresponding to the
       underlying workload identity pool resource if determinable.

       If the environment variable is set to the path of a valid GDCH service
       account JSON file (`Google Distributed Cloud Hosted`_), then a GDCH
       credential will be returned. The project ID returned is the project
       specified in the JSON file.
    2. If the `Google Cloud SDK`_ is installed and has application default
       credentials set they are loaded and returned.

       To enable application default credentials with the Cloud SDK run::

            gcloud auth application-default login

       If the Cloud SDK has an active project, the project ID is returned. The
       active project can be set using::

            gcloud config set project

    3. If the application is running in the `App Engine standard environment`_
       (first generation) then the credentials and project ID from the
       `App Identity Service`_ are used.
    4. If the application is running in `Compute Engine`_ or `Cloud Run`_ or
       the `App Engine flexible environment`_ or the `App Engine standard
       environment`_ (second generation) then the credentials and project ID
       are obtained from the `Metadata Service`_.
    5. If no credentials are found,
       :class:`~google.auth.exceptions.DefaultCredentialsError` will be raised.

    .. _Application Default Credentials: https://developers.google.com\
            /identity/protocols/application-default-credentials
    .. _Google Cloud SDK: https://cloud.google.com/sdk
    .. _App Engine standard environment: https://cloud.google.com/appengine
    .. _App Identity Service: https://cloud.google.com/appengine/docs/python\
            /appidentity/
    .. _Compute Engine: https://cloud.google.com/compute
    .. _App Engine flexible environment: https://cloud.google.com\
            /appengine/flexible
    .. _Metadata Service: https://cloud.google.com/compute/docs\
            /storing-retrieving-metadata
    .. _Cloud Run: https://cloud.google.com/run
    .. _Google Distributed Cloud Hosted: https://cloud.google.com/blog/topics\
            /hybrid-cloud/announcing-google-distributed-cloud-edge-and-hosted

    Example::

        import google.auth

        credentials, project_id = google.auth.default()

    Args:
        scopes (Sequence[str]): The list of scopes for the credentials. If
            specified, the credentials will automatically be scoped if
            necessary.
        request (Optional[google.auth.transport.Request]): An object used to make
            HTTP requests. This is used to either detect whether the application
            is running on Compute Engine or to determine the associated project
            ID for a workload identity pool resource (external account
            credentials). If not specified, then it will either use the standard
            library http client to make requests for Compute Engine credentials
            or a google.auth.transport.requests.Request client for external
            account credentials.
        quota_project_id (Optional[str]): The project ID used for
            quota and billing.
        default_scopes (Optional[Sequence[str]]): Default scopes passed by a
            Google client library. Use 'scopes' for user-defined scopes.
    Returns:
        Tuple[~google.auth.credentials.Credentials, Optional[str]]:
            the current environment's credentials and project ID. Project ID
            may be None, which indicates that the Project ID could not be
            ascertained from the environment.

    Raises:
        ~google.auth.exceptions.DefaultCredentialsError:
            If no credentials were found, or if the credentials found were
            invalid.
    """
    from google.auth.credentials import with_scopes_if_required
    from google.auth.credentials import CredentialsWithQuotaProject

    explicit_project_id = os.environ.get(
        environment_vars.PROJECT, os.environ.get(environment_vars.LEGACY_PROJECT)
    )

    checkers = (
        # Avoid passing scopes here to prevent passing scopes to user credentials.
        # with_scopes_if_required() below will ensure scopes/default scopes are
        # safely set on the returned credentials since requires_scopes will
        # guard against setting scopes on user credentials.
        lambda: _get_explicit_environ_credentials(quota_project_id=quota_project_id),
        lambda: _get_gcloud_sdk_credentials(quota_project_id=quota_project_id),
        _get_gae_credentials,
        lambda: _get_gce_credentials(request, quota_project_id=quota_project_id),
    )

    for checker in checkers:
        credentials, project_id = checker()
        if credentials is not None:
            credentials = with_scopes_if_required(
                credentials, scopes, default_scopes=default_scopes
            )

            effective_project_id = explicit_project_id or project_id

            # For external account credentials, scopes are required to determine
            # the project ID. Try to get the project ID again if not yet
            # determined.
            if not effective_project_id and callable(
                getattr(credentials, "get_project_id", None)
            ):
                if request is None:
                    import google.auth.transport.requests

                    request = google.auth.transport.requests.Request()
                effective_project_id = credentials.get_project_id(request=request)

            if quota_project_id and isinstance(
                credentials, CredentialsWithQuotaProject
            ):
                credentials = credentials.with_quota_project(quota_project_id)

            if not effective_project_id:
                _LOGGER.warning(
                    "No project ID could be determined. Consider running "
                    "`gcloud config set project` or setting the %s "
                    "environment variable",
                    environment_vars.PROJECT,
                )
            return credentials, effective_project_id

    raise exceptions.DefaultCredentialsError(_CLOUD_SDK_MISSING_CREDENTIALS)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\services\model_service\async_client.py ===
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
from collections import OrderedDict
import functools
import re
from typing import (
    Callable,
    Dict,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry_async as retries
from google.api_core.client_options import ClientOptions
from google.auth import credentials as ga_credentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.AsyncRetry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.AsyncRetry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1.services.model_service import pagers
from google.ai.generativelanguage_v1.types import model, model_service

from .client import ModelServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, ModelServiceTransport
from .transports.grpc_asyncio import ModelServiceGrpcAsyncIOTransport


class ModelServiceAsyncClient:
    """Provides methods for getting metadata information about
    Generative Models.
    """

    _client: ModelServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = ModelServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = ModelServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = ModelServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = ModelServiceClient._DEFAULT_UNIVERSE

    model_path = staticmethod(ModelServiceClient.model_path)
    parse_model_path = staticmethod(ModelServiceClient.parse_model_path)
    common_billing_account_path = staticmethod(
        ModelServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        ModelServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(ModelServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(ModelServiceClient.parse_common_folder_path)
    common_organization_path = staticmethod(ModelServiceClient.common_organization_path)
    parse_common_organization_path = staticmethod(
        ModelServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(ModelServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        ModelServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(ModelServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        ModelServiceClient.parse_common_location_path
    )

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            ModelServiceAsyncClient: The constructed client.
        """
        return ModelServiceClient.from_service_account_info.__func__(ModelServiceAsyncClient, info, *args, **kwargs)  # type: ignore

    @classmethod
    def from_service_account_file(cls, filename: str, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            file.

        Args:
            filename (str): The path to the service account private key json
                file.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            ModelServiceAsyncClient: The constructed client.
        """
        return ModelServiceClient.from_service_account_file.__func__(ModelServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

    from_service_account_json = from_service_account_file

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[ClientOptions] = None
    ):
        """Return the API endpoint and client cert source for mutual TLS.

        The client cert source is determined in the following order:
        (1) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is not "true", the
        client cert source is None.
        (2) if `client_options.client_cert_source` is provided, use the provided one; if the
        default client cert source exists, use the default one; otherwise the client cert
        source is None.

        The API endpoint is determined in the following order:
        (1) if `client_options.api_endpoint` if provided, use the provided one.
        (2) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is "always", use the
        default mTLS endpoint; if the environment variable is "never", use the default API
        endpoint; otherwise if client cert source exists, use the default mTLS endpoint, otherwise
        use the default API endpoint.

        More details can be found at https://google.aip.dev/auth/4114.

        Args:
            client_options (google.api_core.client_options.ClientOptions): Custom options for the
                client. Only the `api_endpoint` and `client_cert_source` properties may be used
                in this method.

        Returns:
            Tuple[str, Callable[[], Tuple[bytes, bytes]]]: returns the API endpoint and the
                client cert source to use.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If any errors happen.
        """
        return ModelServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> ModelServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            ModelServiceTransport: The transport used by the client instance.
        """
        return self._client.transport

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._client._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used
                by the client instance.
        """
        return self._client._universe_domain

    get_transport_class = functools.partial(
        type(ModelServiceClient).get_transport_class, type(ModelServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, ModelServiceTransport, Callable[..., ModelServiceTransport]]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the model service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,ModelServiceTransport,Callable[..., ModelServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the ModelServiceTransport constructor.
                If set to None, a transport is chosen automatically.
            client_options (Optional[Union[google.api_core.client_options.ClientOptions, dict]]):
                Custom options for the client.

                1. The ``api_endpoint`` property can be used to override the
                default endpoint provided by the client when ``transport`` is
                not explicitly provided. Only if this property is not set and
                ``transport`` was not explicitly provided, the endpoint is
                determined by the GOOGLE_API_USE_MTLS_ENDPOINT environment
                variable, which have one of the following values:
                "always" (always use the default mTLS endpoint), "never" (always
                use the default regular endpoint) and "auto" (auto-switch to the
                default mTLS endpoint if client certificate is present; this is
                the default value).

                2. If the GOOGLE_API_USE_CLIENT_CERTIFICATE environment variable
                is "true", then the ``client_cert_source`` property can be used
                to provide a client certificate for mTLS transport. If
                not provided, the default SSL client certificate will be used if
                present. If GOOGLE_API_USE_CLIENT_CERTIFICATE is "false" or not
                set, no client certificate will be used.

                3. The ``universe_domain`` property can be used to override the
                default "googleapis.com" universe. Note that ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client = ModelServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def get_model(
        self,
        request: Optional[Union[model_service.GetModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> model.Model:
        r"""Gets information about a specific Model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1

            async def sample_get_model():
                # Create a client
                client = generativelanguage_v1.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1.GetModelRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1.types.GetModelRequest, dict]]):
                The request object. Request for getting information about
                a specific Model.
            name (:class:`str`):
                Required. The resource name of the model.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1.types.Model:
                Information about a Generative
                Language Model.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.GetModelRequest):
            request = model_service.GetModelRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.get_model
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def list_models(
        self,
        request: Optional[Union[model_service.ListModelsRequest, dict]] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListModelsAsyncPager:
        r"""Lists models available through the API.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1

            async def sample_list_models():
                # Create a client
                client = generativelanguage_v1.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1.ListModelsRequest(
                )

                # Make the request
                page_result = client.list_models(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1.types.ListModelsRequest, dict]]):
                The request object. Request for listing all Models.
            page_size (:class:`int`):
                The maximum number of ``Models`` to return (per page).

                The service may return fewer models. If unspecified, at
                most 50 models will be returned per page. This method
                returns at most 1000 models per page, even if you pass a
                larger page_size.

                This corresponds to the ``page_size`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            page_token (:class:`str`):
                A page token, received from a previous ``ListModels``
                call.

                Provide the ``page_token`` returned by one request as an
                argument to the next request to retrieve the next page.

                When paginating, all other parameters provided to
                ``ListModels`` must match the call that provided the
                page token.

                This corresponds to the ``page_token`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1.services.model_service.pagers.ListModelsAsyncPager:
                Response from ListModel containing a paginated list of
                Models.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([page_size, page_token])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.ListModelsRequest):
            request = model_service.ListModelsRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if page_size is not None:
            request.page_size = page_size
        if page_token is not None:
            request.page_token = page_token

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_models
        ]

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__aiter__` convenience method.
        response = pagers.ListModelsAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def list_operations(
        self,
        request: Optional[operations_pb2.ListOperationsRequest] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operations_pb2.ListOperationsResponse:
        r"""Lists operations that match the specified filter in the request.

        Args:
            request (:class:`~.operations_pb2.ListOperationsRequest`):
                The request object. Request message for
                `ListOperations` method.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors,
                    if any, should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        Returns:
            ~.operations_pb2.ListOperationsResponse:
                Response message for ``ListOperations`` method.
        """
        # Create or coerce a protobuf request object.
        # The request isn't a proto-plus wrapped type,
        # so it must be constructed via keyword expansion.
        if isinstance(request, dict):
            request = operations_pb2.ListOperationsRequest(**request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.list_operations,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def get_operation(
        self,
        request: Optional[operations_pb2.GetOperationRequest] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operations_pb2.Operation:
        r"""Gets the latest state of a long-running operation.

        Args:
            request (:class:`~.operations_pb2.GetOperationRequest`):
                The request object. Request message for
                `GetOperation` method.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors,
                    if any, should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        Returns:
            ~.operations_pb2.Operation:
                An ``Operation`` object.
        """
        # Create or coerce a protobuf request object.
        # The request isn't a proto-plus wrapped type,
        # so it must be constructed via keyword expansion.
        if isinstance(request, dict):
            request = operations_pb2.GetOperationRequest(**request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.get_operation,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def cancel_operation(
        self,
        request: Optional[operations_pb2.CancelOperationRequest] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Starts asynchronous cancellation on a long-running operation.

        The server makes a best effort to cancel the operation, but success
        is not guaranteed.  If the server doesn't support this method, it returns
        `google.rpc.Code.UNIMPLEMENTED`.

        Args:
            request (:class:`~.operations_pb2.CancelOperationRequest`):
                The request object. Request message for
                `CancelOperation` method.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors,
                    if any, should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        Returns:
            None
        """
        # Create or coerce a protobuf request object.
        # The request isn't a proto-plus wrapped type,
        # so it must be constructed via keyword expansion.
        if isinstance(request, dict):
            request = operations_pb2.CancelOperationRequest(**request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = gapic_v1.method_async.wrap_method(
            self._client._transport.cancel_operation,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    async def __aenter__(self) -> "ModelServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("ModelServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\formatters\img.py ===
"""
    pygments.formatters.img
    ~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for Pixmap output.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import os
import sys

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.util import get_bool_opt, get_int_opt, get_list_opt, \
    get_choice_opt

import subprocess

# Import this carefully
try:
    from PIL import Image, ImageDraw, ImageFont
    pil_available = True
except ImportError:
    pil_available = False

try:
    import _winreg
except ImportError:
    try:
        import winreg as _winreg
    except ImportError:
        _winreg = None

__all__ = ['ImageFormatter', 'GifImageFormatter', 'JpgImageFormatter',
           'BmpImageFormatter']


# For some unknown reason every font calls it something different
STYLES = {
    'NORMAL':     ['', 'Roman', 'Book', 'Normal', 'Regular', 'Medium'],
    'ITALIC':     ['Oblique', 'Italic'],
    'BOLD':       ['Bold'],
    'BOLDITALIC': ['Bold Oblique', 'Bold Italic'],
}

# A sane default for modern systems
DEFAULT_FONT_NAME_NIX = 'DejaVu Sans Mono'
DEFAULT_FONT_NAME_WIN = 'Courier New'
DEFAULT_FONT_NAME_MAC = 'Menlo'


class PilNotAvailable(ImportError):
    """When Python imaging library is not available"""


class FontNotFound(Exception):
    """When there are no usable fonts specified"""


class FontManager:
    """
    Manages a set of fonts: normal, italic, bold, etc...
    """

    def __init__(self, font_name, font_size=14):
        self.font_name = font_name
        self.font_size = font_size
        self.fonts = {}
        self.encoding = None
        self.variable = False
        if hasattr(font_name, 'read') or os.path.isfile(font_name):
            font = ImageFont.truetype(font_name, self.font_size)
            self.variable = True
            for style in STYLES:
                self.fonts[style] = font

            return

        if sys.platform.startswith('win'):
            if not font_name:
                self.font_name = DEFAULT_FONT_NAME_WIN
            self._create_win()
        elif sys.platform.startswith('darwin'):
            if not font_name:
                self.font_name = DEFAULT_FONT_NAME_MAC
            self._create_mac()
        else:
            if not font_name:
                self.font_name = DEFAULT_FONT_NAME_NIX
            self._create_nix()

    def _get_nix_font_path(self, name, style):
        proc = subprocess.Popen(['fc-list', f"{name}:style={style}", 'file'],
                                stdout=subprocess.PIPE, stderr=None)
        stdout, _ = proc.communicate()
        if proc.returncode == 0:
            lines = stdout.splitlines()
            for line in lines:
                if line.startswith(b'Fontconfig warning:'):
                    continue
                path = line.decode().strip().strip(':')
                if path:
                    return path
            return None

    def _create_nix(self):
        for name in STYLES['NORMAL']:
            path = self._get_nix_font_path(self.font_name, name)
            if path is not None:
                self.fonts['NORMAL'] = ImageFont.truetype(path, self.font_size)
                break
        else:
            raise FontNotFound(f'No usable fonts named: "{self.font_name}"')
        for style in ('ITALIC', 'BOLD', 'BOLDITALIC'):
            for stylename in STYLES[style]:
                path = self._get_nix_font_path(self.font_name, stylename)
                if path is not None:
                    self.fonts[style] = ImageFont.truetype(path, self.font_size)
                    break
            else:
                if style == 'BOLDITALIC':
                    self.fonts[style] = self.fonts['BOLD']
                else:
                    self.fonts[style] = self.fonts['NORMAL']

    def _get_mac_font_path(self, font_map, name, style):
        return font_map.get((name + ' ' + style).strip().lower())

    def _create_mac(self):
        font_map = {}
        for font_dir in (os.path.join(os.getenv("HOME"), 'Library/Fonts/'),
                         '/Library/Fonts/', '/System/Library/Fonts/'):
            font_map.update(
                (os.path.splitext(f)[0].lower(), os.path.join(font_dir, f))
                for f in os.listdir(font_dir)
                if f.lower().endswith(('ttf', 'ttc')))

        for name in STYLES['NORMAL']:
            path = self._get_mac_font_path(font_map, self.font_name, name)
            if path is not None:
                self.fonts['NORMAL'] = ImageFont.truetype(path, self.font_size)
                break
        else:
            raise FontNotFound(f'No usable fonts named: "{self.font_name}"')
        for style in ('ITALIC', 'BOLD', 'BOLDITALIC'):
            for stylename in STYLES[style]:
                path = self._get_mac_font_path(font_map, self.font_name, stylename)
                if path is not None:
                    self.fonts[style] = ImageFont.truetype(path, self.font_size)
                    break
            else:
                if style == 'BOLDITALIC':
                    self.fonts[style] = self.fonts['BOLD']
                else:
                    self.fonts[style] = self.fonts['NORMAL']

    def _lookup_win(self, key, basename, styles, fail=False):
        for suffix in ('', ' (TrueType)'):
            for style in styles:
                try:
                    valname = '{}{}{}'.format(basename, style and ' '+style, suffix)
                    val, _ = _winreg.QueryValueEx(key, valname)
                    return val
                except OSError:
                    continue
        else:
            if fail:
                raise FontNotFound(f'Font {basename} ({styles[0]}) not found in registry')
            return None

    def _create_win(self):
        lookuperror = None
        keynames = [ (_winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows NT\CurrentVersion\Fonts'),
                     (_winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Fonts'),
                     (_winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows NT\CurrentVersion\Fonts'),
                     (_winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\Fonts') ]
        for keyname in keynames:
            try:
                key = _winreg.OpenKey(*keyname)
                try:
                    path = self._lookup_win(key, self.font_name, STYLES['NORMAL'], True)
                    self.fonts['NORMAL'] = ImageFont.truetype(path, self.font_size)
                    for style in ('ITALIC', 'BOLD', 'BOLDITALIC'):
                        path = self._lookup_win(key, self.font_name, STYLES[style])
                        if path:
                            self.fonts[style] = ImageFont.truetype(path, self.font_size)
                        else:
                            if style == 'BOLDITALIC':
                                self.fonts[style] = self.fonts['BOLD']
                            else:
                                self.fonts[style] = self.fonts['NORMAL']
                    return
                except FontNotFound as err:
                    lookuperror = err
                finally:
                    _winreg.CloseKey(key)
            except OSError:
                pass
        else:
            # If we get here, we checked all registry keys and had no luck
            # We can be in one of two situations now:
            # * All key lookups failed. In this case lookuperror is None and we
            #   will raise a generic error
            # * At least one lookup failed with a FontNotFound error. In this
            #   case, we will raise that as a more specific error
            if lookuperror:
                raise lookuperror
            raise FontNotFound('Can\'t open Windows font registry key')

    def get_char_size(self):
        """
        Get the character size.
        """
        return self.get_text_size('M')

    def get_text_size(self, text):
        """
        Get the text size (width, height).
        """
        font = self.fonts['NORMAL']
        if hasattr(font, 'getbbox'):  # Pillow >= 9.2.0
            return font.getbbox(text)[2:4]
        else:
            return font.getsize(text)

    def get_font(self, bold, oblique):
        """
        Get the font based on bold and italic flags.
        """
        if bold and oblique:
            if self.variable:
                return self.get_style('BOLDITALIC')

            return self.fonts['BOLDITALIC']
        elif bold:
            if self.variable:
                return self.get_style('BOLD')

            return self.fonts['BOLD']
        elif oblique:
            if self.variable:
                return self.get_style('ITALIC')

            return self.fonts['ITALIC']
        else:
            if self.variable:
                return self.get_style('NORMAL')

            return self.fonts['NORMAL']

    def get_style(self, style):
        """
        Get the specified style of the font if it is a variable font.
        If not found, return the normal font.
        """
        font = self.fonts[style]
        for style_name in STYLES[style]:
            try:
                font.set_variation_by_name(style_name)
                return font
            except ValueError:
                pass
            except OSError:
                return font

        return font


class ImageFormatter(Formatter):
    """
    Create a PNG image from source code. This uses the Python Imaging Library to
    generate a pixmap from the source code.

    .. versionadded:: 0.10

    Additional options accepted:

    `image_format`
        An image format to output to that is recognised by PIL, these include:

        * "PNG" (default)
        * "JPEG"
        * "BMP"
        * "GIF"

    `line_pad`
        The extra spacing (in pixels) between each line of text.

        Default: 2

    `font_name`
        The font name to be used as the base font from which others, such as
        bold and italic fonts will be generated.  This really should be a
        monospace font to look sane.
        If a filename or a file-like object is specified, the user must
        provide different styles of the font.

        Default: "Courier New" on Windows, "Menlo" on Mac OS, and
                 "DejaVu Sans Mono" on \\*nix

    `font_size`
        The font size in points to be used.

        Default: 14

    `image_pad`
        The padding, in pixels to be used at each edge of the resulting image.

        Default: 10

    `line_numbers`
        Whether line numbers should be shown: True/False

        Default: True

    `line_number_start`
        The line number of the first line.

        Default: 1

    `line_number_step`
        The step used when printing line numbers.

        Default: 1

    `line_number_bg`
        The background colour (in "#123456" format) of the line number bar, or
        None to use the style background color.

        Default: "#eed"

    `line_number_fg`
        The text color of the line numbers (in "#123456"-like format).

        Default: "#886"

    `line_number_chars`
        The number of columns of line numbers allowable in the line number
        margin.

        Default: 2

    `line_number_bold`
        Whether line numbers will be bold: True/False

        Default: False

    `line_number_italic`
        Whether line numbers will be italicized: True/False

        Default: False

    `line_number_separator`
        Whether a line will be drawn between the line number area and the
        source code area: True/False

        Default: True

    `line_number_pad`
        The horizontal padding (in pixels) between the line number margin, and
        the source code area.

        Default: 6

    `hl_lines`
        Specify a list of lines to be highlighted.

        .. versionadded:: 1.2

        Default: empty list

    `hl_color`
        Specify the color for highlighting lines.

        .. versionadded:: 1.2

        Default: highlight color of the selected style
    """

    # Required by the pygments mapper
    name = 'img'
    aliases = ['img', 'IMG', 'png']
    filenames = ['*.png']

    unicodeoutput = False

    default_image_format = 'png'

    def __init__(self, **options):
        """
        See the class docstring for explanation of options.
        """
        if not pil_available:
            raise PilNotAvailable(
                'Python Imaging Library is required for this formatter')
        Formatter.__init__(self, **options)
        self.encoding = 'latin1'  # let pygments.format() do the right thing
        # Read the style
        self.styles = dict(self.style)
        if self.style.background_color is None:
            self.background_color = '#fff'
        else:
            self.background_color = self.style.background_color
        # Image options
        self.image_format = get_choice_opt(
            options, 'image_format', ['png', 'jpeg', 'gif', 'bmp'],
            self.default_image_format, normcase=True)
        self.image_pad = get_int_opt(options, 'image_pad', 10)
        self.line_pad = get_int_opt(options, 'line_pad', 2)
        # The fonts
        fontsize = get_int_opt(options, 'font_size', 14)
        self.fonts = FontManager(options.get('font_name', ''), fontsize)
        self.fontw, self.fonth = self.fonts.get_char_size()
        # Line number options
        self.line_number_fg = options.get('line_number_fg', '#886')
        self.line_number_bg = options.get('line_number_bg', '#eed')
        self.line_number_chars = get_int_opt(options,
                                             'line_number_chars', 2)
        self.line_number_bold = get_bool_opt(options,
                                             'line_number_bold', False)
        self.line_number_italic = get_bool_opt(options,
                                               'line_number_italic', False)
        self.line_number_pad = get_int_opt(options, 'line_number_pad', 6)
        self.line_numbers = get_bool_opt(options, 'line_numbers', True)
        self.line_number_separator = get_bool_opt(options,
                                                  'line_number_separator', True)
        self.line_number_step = get_int_opt(options, 'line_number_step', 1)
        self.line_number_start = get_int_opt(options, 'line_number_start', 1)
        if self.line_numbers:
            self.line_number_width = (self.fontw * self.line_number_chars +
                                      self.line_number_pad * 2)
        else:
            self.line_number_width = 0
        self.hl_lines = []
        hl_lines_str = get_list_opt(options, 'hl_lines', [])
        for line in hl_lines_str:
            try:
                self.hl_lines.append(int(line))
            except ValueError:
                pass
        self.hl_color = options.get('hl_color',
                                    self.style.highlight_color) or '#f90'
        self.drawables = []

    def get_style_defs(self, arg=''):
        raise NotImplementedError('The -S option is meaningless for the image '
                                  'formatter. Use -O style=<stylename> instead.')

    def _get_line_height(self):
        """
        Get the height of a line.
        """
        return self.fonth + self.line_pad

    def _get_line_y(self, lineno):
        """
        Get the Y coordinate of a line number.
        """
        return lineno * self._get_line_height() + self.image_pad

    def _get_char_width(self):
        """
        Get the width of a character.
        """
        return self.fontw

    def _get_char_x(self, linelength):
        """
        Get the X coordinate of a character position.
        """
        return linelength + self.image_pad + self.line_number_width

    def _get_text_pos(self, linelength, lineno):
        """
        Get the actual position for a character and line position.
        """
        return self._get_char_x(linelength), self._get_line_y(lineno)

    def _get_linenumber_pos(self, lineno):
        """
        Get the actual position for the start of a line number.
        """
        return (self.image_pad, self._get_line_y(lineno))

    def _get_text_color(self, style):
        """
        Get the correct color for the token from the style.
        """
        if style['color'] is not None:
            fill = '#' + style['color']
        else:
            fill = '#000'
        return fill

    def _get_text_bg_color(self, style):
        """
        Get the correct background color for the token from the style.
        """
        if style['bgcolor'] is not None:
            bg_color = '#' + style['bgcolor']
        else:
            bg_color = None
        return bg_color

    def _get_style_font(self, style):
        """
        Get the correct font for the style.
        """
        return self.fonts.get_font(style['bold'], style['italic'])

    def _get_image_size(self, maxlinelength, maxlineno):
        """
        Get the required image size.
        """
        return (self._get_char_x(maxlinelength) + self.image_pad,
                self._get_line_y(maxlineno + 0) + self.image_pad)

    def _draw_linenumber(self, posno, lineno):
        """
        Remember a line number drawable to paint later.
        """
        self._draw_text(
            self._get_linenumber_pos(posno),
            str(lineno).rjust(self.line_number_chars),
            font=self.fonts.get_font(self.line_number_bold,
                                     self.line_number_italic),
            text_fg=self.line_number_fg,
            text_bg=None,
        )

    def _draw_text(self, pos, text, font, text_fg, text_bg):
        """
        Remember a single drawable tuple to paint later.
        """
        self.drawables.append((pos, text, font, text_fg, text_bg))

    def _create_drawables(self, tokensource):
        """
        Create drawables for the token content.
        """
        lineno = charno = maxcharno = 0
        maxlinelength = linelength = 0
        for ttype, value in tokensource:
            while ttype not in self.styles:
                ttype = ttype.parent
            style = self.styles[ttype]
            # TODO: make sure tab expansion happens earlier in the chain.  It
            # really ought to be done on the input, as to do it right here is
            # quite complex.
            value = value.expandtabs(4)
            lines = value.splitlines(True)
            # print lines
            for i, line in enumerate(lines):
                temp = line.rstrip('\n')
                if temp:
                    self._draw_text(
                        self._get_text_pos(linelength, lineno),
                        temp,
                        font = self._get_style_font(style),
                        text_fg = self._get_text_color(style),
                        text_bg = self._get_text_bg_color(style),
                    )
                    temp_width, _ = self.fonts.get_text_size(temp)
                    linelength += temp_width
                    maxlinelength = max(maxlinelength, linelength)
                    charno += len(temp)
                    maxcharno = max(maxcharno, charno)
                if line.endswith('\n'):
                    # add a line for each extra line in the value
                    linelength = 0
                    charno = 0
                    lineno += 1
        self.maxlinelength = maxlinelength
        self.maxcharno = maxcharno
        self.maxlineno = lineno

    def _draw_line_numbers(self):
        """
        Create drawables for the line numbers.
        """
        if not self.line_numbers:
            return
        for p in range(self.maxlineno):
            n = p + self.line_number_start
            if (n % self.line_number_step) == 0:
                self._draw_linenumber(p, n)

    def _paint_line_number_bg(self, im):
        """
        Paint the line number background on the image.
        """
        if not self.line_numbers:
            return
        if self.line_number_fg is None:
            return
        draw = ImageDraw.Draw(im)
        recth = im.size[-1]
        rectw = self.image_pad + self.line_number_width - self.line_number_pad
        draw.rectangle([(0, 0), (rectw, recth)],
                       fill=self.line_number_bg)
        if self.line_number_separator:
            draw.line([(rectw, 0), (rectw, recth)], fill=self.line_number_fg)
        del draw

    def format(self, tokensource, outfile):
        """
        Format ``tokensource``, an iterable of ``(tokentype, tokenstring)``
        tuples and write it into ``outfile``.

        This implementation calculates where it should draw each token on the
        pixmap, then calculates the required pixmap size and draws the items.
        """
        self._create_drawables(tokensource)
        self._draw_line_numbers()
        im = Image.new(
            'RGB',
            self._get_image_size(self.maxlinelength, self.maxlineno),
            self.background_color
        )
        self._paint_line_number_bg(im)
        draw = ImageDraw.Draw(im)
        # Highlight
        if self.hl_lines:
            x = self.image_pad + self.line_number_width - self.line_number_pad + 1
            recth = self._get_line_height()
            rectw = im.size[0] - x
            for linenumber in self.hl_lines:
                y = self._get_line_y(linenumber - 1)
                draw.rectangle([(x, y), (x + rectw, y + recth)],
                               fill=self.hl_color)
        for pos, value, font, text_fg, text_bg in self.drawables:
            if text_bg:
                # see deprecations https://pillow.readthedocs.io/en/stable/releasenotes/9.2.0.html#font-size-and-offset-methods
                if hasattr(draw, 'textsize'):
                    text_size = draw.textsize(text=value, font=font)
                else:
                    text_size = font.getbbox(value)[2:]
                draw.rectangle([pos[0], pos[1], pos[0] + text_size[0], pos[1] + text_size[1]], fill=text_bg)
            draw.text(pos, value, font=font, fill=text_fg)
        im.save(outfile, self.image_format.upper())


# Add one formatter per format, so that the "-f gif" option gives the correct result
# when used in pygmentize.

class GifImageFormatter(ImageFormatter):
    """
    Create a GIF image from source code. This uses the Python Imaging Library to
    generate a pixmap from the source code.

    .. versionadded:: 1.0
    """

    name = 'img_gif'
    aliases = ['gif']
    filenames = ['*.gif']
    default_image_format = 'gif'


class JpgImageFormatter(ImageFormatter):
    """
    Create a JPEG image from source code. This uses the Python Imaging Library to
    generate a pixmap from the source code.

    .. versionadded:: 1.0
    """

    name = 'img_jpg'
    aliases = ['jpg', 'jpeg']
    filenames = ['*.jpg']
    default_image_format = 'jpeg'


class BmpImageFormatter(ImageFormatter):
    """
    Create a bitmap image from source code. This uses the Python Imaging Library to
    generate a pixmap from the source code.

    .. versionadded:: 1.0
    """

    name = 'img_bmp'
    aliases = ['bmp', 'bitmap']
    filenames = ['*.bmp']
    default_image_format = 'bmp'

# === NexusCore/openenv\Lib\site-packages\google\generativeai\types\generation_types.py ===
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

import collections
import contextlib
import sys
from collections.abc import Iterable, AsyncIterable, Mapping
import dataclasses
import itertools
import json
import sys
import textwrap
from typing import Union, Any
from typing_extensions import TypedDict
import types

import google.protobuf.json_format
import google.api_core.exceptions

from google.generativeai import protos
from google.generativeai import string_utils
from google.generativeai.types import content_types
from google.generativeai.responder import _rename_schema_fields

__all__ = [
    "AsyncGenerateContentResponse",
    "BlockedPromptException",
    "StopCandidateException",
    "IncompleteIterationError",
    "BrokenResponseError",
    "GenerationConfigDict",
    "GenerationConfigType",
    "GenerationConfig",
    "GenerateContentResponse",
]

if sys.version_info < (3, 10):

    def aiter(obj):
        return obj.__aiter__()

    async def anext(obj, default=None):
        try:
            return await obj.__anext__()
        except StopAsyncIteration:
            if default is not None:
                return default
            else:
                raise


class BlockedPromptException(Exception):
    pass


class StopCandidateException(Exception):
    pass


class IncompleteIterationError(Exception):
    pass


class BrokenResponseError(Exception):
    pass


class GenerationConfigDict(TypedDict, total=False):
    # TODO(markdaoust): Python 3.11+ use `NotRequired`, ref: https://peps.python.org/pep-0655/
    candidate_count: int
    stop_sequences: Iterable[str]
    max_output_tokens: int
    temperature: float
    response_mime_type: str
    response_schema: protos.Schema | Mapping[str, Any]  # fmt: off


@dataclasses.dataclass
class GenerationConfig:
    """A simple dataclass used to configure the generation parameters of `GenerativeModel.generate_content`.

    Attributes:
        candidate_count:
            Number of generated responses to return.
        stop_sequences:
            The set of character sequences (up
            to 5) that will stop output generation. If
            specified, the API will stop at the first
            appearance of a stop sequence. The stop sequence
            will not be included as part of the response.
        max_output_tokens:
            The maximum number of tokens to include in a
            candidate.

            If unset, this will default to output_token_limit specified
            in the model's specification.
        temperature:
            Controls the randomness of the output. Note: The
            default value varies by model, see the `Model.temperature`
            attribute of the `Model` returned the `genai.get_model`
            function.

            Values can range from [0.0,1.0], inclusive. A value closer
            to 1.0 will produce responses that are more varied and
            creative, while a value closer to 0.0 will typically result
            in more straightforward responses from the model.
        top_p:
            Optional. The maximum cumulative probability of tokens to
            consider when sampling.

            The model uses combined Top-k and nucleus sampling.

            Tokens are sorted based on their assigned probabilities so
            that only the most likely tokens are considered. Top-k
            sampling directly limits the maximum number of tokens to
            consider, while Nucleus sampling limits number of tokens
            based on the cumulative probability.

            Note: The default value varies by model, see the
            `Model.top_p` attribute of the `Model` returned the
            `genai.get_model` function.

        top_k (int):
            Optional. The maximum number of tokens to consider when
            sampling.

            The model uses combined Top-k and nucleus sampling.

            Top-k sampling considers the set of `top_k` most probable
            tokens. Defaults to 40.

            Note: The default value varies by model, see the
            `Model.top_k` attribute of the `Model` returned the
            `genai.get_model` function.

        response_mime_type:
            Optional. Output response mimetype of the generated candidate text.

            Supported mimetype:
                `text/plain`: (default) Text output.
                `application/json`: JSON response in the candidates.

        response_schema:
            Optional. Specifies the format of the JSON requested if response_mime_type is
            `application/json`.
    """

    candidate_count: int | None = None
    stop_sequences: Iterable[str] | None = None
    max_output_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    response_mime_type: str | None = None
    response_schema: protos.Schema | Mapping[str, Any] | None = None


GenerationConfigType = Union[protos.GenerationConfig, GenerationConfigDict, GenerationConfig]


def _normalize_schema(generation_config):
    # Convert response_schema to protos.Schema for request
    response_schema = generation_config.get("response_schema", None)
    if response_schema is None:
        return

    if isinstance(response_schema, protos.Schema):
        return

    if isinstance(response_schema, type):
        response_schema = content_types._schema_for_class(response_schema)
    elif isinstance(response_schema, types.GenericAlias):
        if not str(response_schema).startswith("list["):
            raise ValueError(
                f"Invalid input: Could not understand the type of '{response_schema}'. "
                "Expected one of the following types: `int`, `float`, `str`, `bool`, `typing_extensions.TypedDict`, `dataclass`, or `list[...]`."
            )
        response_schema = content_types._schema_for_class(response_schema)

    response_schema = _rename_schema_fields(response_schema)
    generation_config["response_schema"] = protos.Schema(response_schema)


def to_generation_config_dict(generation_config: GenerationConfigType):
    if generation_config is None:
        return {}
    elif isinstance(generation_config, protos.GenerationConfig):
        schema = generation_config.response_schema
        generation_config = type(generation_config).to_dict(
            generation_config
        )  # pytype: disable=attribute-error
        generation_config["response_schema"] = schema
        return generation_config
    elif isinstance(generation_config, GenerationConfig):
        generation_config = dataclasses.asdict(generation_config)
        _normalize_schema(generation_config)
        return {key: value for key, value in generation_config.items() if value is not None}
    elif hasattr(generation_config, "keys"):
        generation_config = dict(generation_config)
        _normalize_schema(generation_config)
        return generation_config
    else:
        raise TypeError(
            "Invalid input type. Expected a `dict` or `GenerationConfig` for `generation_config`.\n"
            f"However, received an object of type: {type(generation_config)}.\n"
            f"Object Value: {generation_config}"
        )


def _join_citation_metadatas(
    citation_metadatas: Iterable[protos.CitationMetadata],
):
    citation_metadatas = list(citation_metadatas)
    return citation_metadatas[-1]


def _join_safety_ratings_lists(
    safety_ratings_lists: Iterable[list[protos.SafetyRating]],
):
    ratings = {}
    blocked = collections.defaultdict(list)

    for safety_ratings_list in safety_ratings_lists:
        for rating in safety_ratings_list:
            ratings[rating.category] = rating.probability
            blocked[rating.category].append(rating.blocked)

    blocked = {category: any(blocked) for category, blocked in blocked.items()}

    safety_list = []
    for (category, probability), blocked in zip(ratings.items(), blocked.values()):
        safety_list.append(
            protos.SafetyRating(category=category, probability=probability, blocked=blocked)
        )

    return safety_list


def _join_contents(contents: Iterable[protos.Content]):
    contents = tuple(contents)
    roles = [c.role for c in contents if c.role]
    if roles:
        role = roles[0]
    else:
        role = ""

    parts = []
    for content in contents:
        parts.extend(content.parts)

    merged_parts = []
    last = parts[0]
    for part in parts[1:]:
        if "text" in last and "text" in part:
            last = protos.Part(text=last.text + part.text)
            continue

        # Can we merge the new thing into last?
        # If not, put last in list of parts, and new thing becomes last
        if "executable_code" in last and "executable_code" in part:
            last = protos.Part(
                executable_code=_join_executable_code(last.executable_code, part.executable_code)
            )
            continue

        if "code_execution_result" in last and "code_execution_result" in part:
            last = protos.Part(
                code_execution_result=_join_code_execution_result(
                    last.code_execution_result, part.code_execution_result
                )
            )
            continue

        merged_parts.append(last)
        last = part

    merged_parts.append(last)

    return protos.Content(
        role=role,
        parts=merged_parts,
    )


def _join_executable_code(code_1, code_2):
    return protos.ExecutableCode(language=code_1.language, code=code_1.code + code_2.code)


def _join_code_execution_result(result_1, result_2):
    return protos.CodeExecutionResult(
        outcome=result_2.outcome, output=result_1.output + result_2.output
    )


def _join_candidates(candidates: Iterable[protos.Candidate]):
    candidates = tuple(candidates)

    index = candidates[0].index  # These should all be the same.

    return protos.Candidate(
        index=index,
        content=_join_contents([c.content for c in candidates]),
        finish_reason=candidates[-1].finish_reason,
        safety_ratings=_join_safety_ratings_lists([c.safety_ratings for c in candidates]),
        citation_metadata=_join_citation_metadatas([c.citation_metadata for c in candidates]),
        token_count=candidates[-1].token_count,
    )


def _join_candidate_lists(candidate_lists: Iterable[list[protos.Candidate]]):
    # Assuming that is a candidate ends, it is no longer returned in the list of
    # candidates and that's why candidates have an index
    candidates = collections.defaultdict(list)
    for candidate_list in candidate_lists:
        for candidate in candidate_list:
            candidates[candidate.index].append(candidate)

    new_candidates = []
    for index, candidate_parts in sorted(candidates.items()):
        new_candidates.append(_join_candidates(candidate_parts))

    return new_candidates


def _join_prompt_feedbacks(
    prompt_feedbacks: Iterable[protos.GenerateContentResponse.PromptFeedback],
):
    # Always return the first prompt feedback.
    return next(iter(prompt_feedbacks))


def _join_chunks(chunks: Iterable[protos.GenerateContentResponse]):
    chunks = tuple(chunks)
    return protos.GenerateContentResponse(
        candidates=_join_candidate_lists(c.candidates for c in chunks),
        prompt_feedback=_join_prompt_feedbacks(c.prompt_feedback for c in chunks),
        usage_metadata=chunks[-1].usage_metadata,
    )


_INCOMPLETE_ITERATION_MESSAGE = """\
Please let the response complete iteration before accessing the final accumulated
attributes (or call `response.resolve()`)"""


class BaseGenerateContentResponse:
    def __init__(
        self,
        done: bool,
        iterator: (
            None
            | Iterable[protos.GenerateContentResponse]
            | AsyncIterable[protos.GenerateContentResponse]
        ),
        result: protos.GenerateContentResponse,
        chunks: Iterable[protos.GenerateContentResponse] | None = None,
    ):
        self._done = done
        self._iterator = iterator
        self._result = result
        if chunks is None:
            self._chunks = [result]
        else:
            self._chunks = list(chunks)
        if result.prompt_feedback.block_reason:
            self._error = BlockedPromptException(result)
        else:
            self._error = None

    def to_dict(self):
        """Returns the result as a JSON-compatible dict.

        Note: This doesn't capture the iterator state when streaming, it only captures the accumulated
        `GenerateContentResponse` fields.

        >>> import json
        >>> response = model.generate_content('Hello?')
        >>> json.dumps(response.to_dict())
        """
        return type(self._result).to_dict(self._result)

    @property
    def candidates(self):
        """The list of candidate responses.

        Raises:
            IncompleteIterationError: With `stream=True` if iteration over the stream was not completed.
        """
        if not self._done:
            raise IncompleteIterationError(_INCOMPLETE_ITERATION_MESSAGE)
        return self._result.candidates

    @property
    def parts(self):
        """A quick accessor equivalent to `self.candidates[0].content.parts`

        Raises:
            ValueError: If the candidate list does not contain exactly one candidate.
        """
        candidates = self.candidates
        if not candidates:
            raise ValueError(
                "Invalid operation: The `response.parts` quick accessor requires a single candidate, "
                "but none were returned. Please check the `response.prompt_feedback` to determine if the prompt was blocked."
            )
        if len(candidates) > 1:
            raise ValueError(
                "Invalid operation: The `response.parts` quick accessor requires a single candidate. "
                "For multiple candidates, please use `result.candidates[index].text`."
            )
        parts = candidates[0].content.parts
        return parts

    @property
    def text(self):
        """A quick accessor equivalent to `self.candidates[0].content.parts[0].text`

        Raises:
            ValueError: If the candidate list or parts list does not contain exactly one entry.
        """
        parts = self.parts
        if not parts:
            raise ValueError(
                "Invalid operation: The `response.text` quick accessor requires the response to contain a valid `Part`, "
                "but none were returned. Please check the `candidate.safety_ratings` to determine if the response was blocked."
            )

        texts = []
        for part in parts:
            if "text" in part:
                texts.append(part.text)
                continue
            if "executable_code" in part:
                language = part.executable_code.language.name.lower()
                if language == "language_unspecified":
                    language = ""
                else:
                    language = f" {language}"
                texts.extend([f"```{language}", part.executable_code.code.lstrip("\n"), "```"])
                continue
            if "code_execution_result" in part:
                outcome_result = part.code_execution_result.outcome.name.lower().replace(
                    "outcome_", ""
                )
                if outcome_result == "ok" or outcome_result == "unspecified":
                    outcome_result = ""
                else:
                    outcome_result = f" {outcome_result}"
                texts.extend([f"```{outcome_result}", part.code_execution_result.output, "```"])
                continue

            part_type = protos.Part.pb(part).whichOneof("data")
            raise ValueError(f"Could not convert `part.{part_type}` to text.")

        return "\n".join(texts)

    @property
    def prompt_feedback(self):
        return self._result.prompt_feedback

    @property
    def usage_metadata(self):
        return self._result.usage_metadata

    def __str__(self) -> str:
        if self._done:
            _iterator = "None"
        else:
            _iterator = f"<{self._iterator.__class__.__name__}>"

        as_dict = type(self._result).to_dict(
            self._result, use_integers_for_enums=False, including_default_value_fields=False
        )
        json_str = json.dumps(as_dict, indent=2)

        _result = f"protos.GenerateContentResponse({json_str})"
        _result = _result.replace("\n", "\n                    ")

        if self._error:
            _error = f",\nerror=<{self._error.__class__.__name__}> {self._error}"
        else:
            _error = ""

        return (
            textwrap.dedent(
                f"""\
                response:
                {type(self).__name__}(
                    done={self._done},
                    iterator={_iterator},
                    result={_result},
                )"""
            )
            + _error
        )

    __repr__ = __str__


@contextlib.contextmanager
def rewrite_stream_error():
    try:
        yield
    except (google.protobuf.json_format.ParseError, AttributeError) as e:
        raise google.api_core.exceptions.BadRequest(
            "Unknown error trying to retrieve streaming response. "
            "Please retry with `stream=False` for more details."
        )


GENERATE_CONTENT_RESPONSE_DOC = """Instances of this class manage the response of the `generate_content` method.

    These are returned by `GenerativeModel.generate_content` and `ChatSession.send_message`.
    This object is based on the low level `protos.GenerateContentResponse` class which just has `prompt_feedback`
    and `candidates` attributes. This class adds several quick accessors for common use cases.

    The same object type is returned for both `stream=True/False`.

    ### Streaming

    When you pass `stream=True` to `GenerativeModel.generate_content` or `ChatSession.send_message`,
    iterate over this object to receive chunks of the response:

    ```
    response = model.generate_content(..., stream=True):
    for chunk in response:
      print(chunk.text)
    ```

    `GenerateContentResponse.prompt_feedback` is available immediately but
    `GenerateContentResponse.candidates`, and all the attributes derived from them (`.text`, `.parts`),
    are only available after the iteration is complete.
    """

ASYNC_GENERATE_CONTENT_RESPONSE_DOC = (
    """This is the async version of `genai.GenerateContentResponse`."""
)


@string_utils.set_doc(GENERATE_CONTENT_RESPONSE_DOC)
class GenerateContentResponse(BaseGenerateContentResponse):
    @classmethod
    def from_iterator(cls, iterator: Iterable[protos.GenerateContentResponse]):
        iterator = iter(iterator)
        with rewrite_stream_error():
            response = next(iterator)

        return cls(
            done=False,
            iterator=iterator,
            result=response,
        )

    @classmethod
    def from_response(cls, response: protos.GenerateContentResponse):
        return cls(
            done=True,
            iterator=None,
            result=response,
        )

    def __iter__(self):
        # This is not thread safe.
        if self._done:
            for chunk in self._chunks:
                yield GenerateContentResponse.from_response(chunk)
            return

        # Always have the next chunk available.
        if len(self._chunks) == 0:
            self._chunks.append(next(self._iterator))

        for n in itertools.count():
            if self._error:
                raise self._error

            if n >= len(self._chunks) - 1:
                # Look ahead for a new item, so that you know the stream is done
                # when you yield the last item.
                if self._done:
                    return

                try:
                    item = next(self._iterator)
                except StopIteration:
                    self._done = True
                except Exception as e:
                    self._error = e
                    self._done = True
                else:
                    self._chunks.append(item)
                    self._result = _join_chunks([self._result, item])

            item = self._chunks[n]

            item = GenerateContentResponse.from_response(item)
            yield item

    def resolve(self):
        if self._done:
            return

        for _ in self:
            pass


@string_utils.set_doc(ASYNC_GENERATE_CONTENT_RESPONSE_DOC)
class AsyncGenerateContentResponse(BaseGenerateContentResponse):
    @classmethod
    async def from_aiterator(cls, iterator: AsyncIterable[protos.GenerateContentResponse]):
        iterator = aiter(iterator)  # type: ignore
        with rewrite_stream_error():
            response = await anext(iterator)  # type: ignore

        return cls(
            done=False,
            iterator=iterator,
            result=response,
        )

    @classmethod
    def from_response(cls, response: protos.GenerateContentResponse):
        return cls(
            done=True,
            iterator=None,
            result=response,
        )

    async def __aiter__(self):
        # This is not thread safe.
        if self._done:
            for chunk in self._chunks:
                yield GenerateContentResponse.from_response(chunk)
            return

        # Always have the next chunk available.
        if len(self._chunks) == 0:
            self._chunks.append(await anext(self._iterator))  # type: ignore

        for n in itertools.count():
            if self._error:
                raise self._error

            if n >= len(self._chunks) - 1:
                # Look ahead for a new item, so that you know the stream is done
                # when you yield the last item.
                if self._done:
                    return

                try:
                    item = await anext(self._iterator)  # type: ignore
                except StopAsyncIteration:
                    self._done = True
                except Exception as e:
                    self._error = e
                    self._done = True
                else:
                    self._chunks.append(item)
                    self._result = _join_chunks([self._result, item])

            item = self._chunks[n]

            item = GenerateContentResponse.from_response(item)
            yield item

    async def resolve(self):
        if self._done:
            return

        async for _ in self:
            pass

# === NexusCore/openenv\Lib\site-packages\nltk\parse\recursivedescent.py ===
# Natural Language Toolkit: Recursive Descent Parser
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.grammar import Nonterminal
from nltk.parse.api import ParserI
from nltk.tree import ImmutableTree, Tree


##//////////////////////////////////////////////////////
##  Recursive Descent Parser
##//////////////////////////////////////////////////////
class RecursiveDescentParser(ParserI):
    """
    A simple top-down CFG parser that parses texts by recursively
    expanding the fringe of a Tree, and matching it against a
    text.

    ``RecursiveDescentParser`` uses a list of tree locations called a
    "frontier" to remember which subtrees have not yet been expanded
    and which leaves have not yet been matched against the text.  Each
    tree location consists of a list of child indices specifying the
    path from the root of the tree to a subtree or a leaf; see the
    reference documentation for Tree for more information
    about tree locations.

    When the parser begins parsing a text, it constructs a tree
    containing only the start symbol, and a frontier containing the
    location of the tree's root node.  It then extends the tree to
    cover the text, using the following recursive procedure:

      - If the frontier is empty, and the text is covered by the tree,
        then return the tree as a possible parse.
      - If the frontier is empty, and the text is not covered by the
        tree, then return no parses.
      - If the first element of the frontier is a subtree, then
        use CFG productions to "expand" it.  For each applicable
        production, add the expanded subtree's children to the
        frontier, and recursively find all parses that can be
        generated by the new tree and frontier.
      - If the first element of the frontier is a token, then "match"
        it against the next token from the text.  Remove the token
        from the frontier, and recursively find all parses that can be
        generated by the new tree and frontier.

    :see: ``nltk.grammar``
    """

    def __init__(self, grammar, trace=0):
        """
        Create a new ``RecursiveDescentParser``, that uses ``grammar``
        to parse texts.

        :type grammar: CFG
        :param grammar: The grammar used to parse texts.
        :type trace: int
        :param trace: The level of tracing that should be used when
            parsing a text.  ``0`` will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        """
        self._grammar = grammar
        self._trace = trace

    def grammar(self):
        return self._grammar

    def parse(self, tokens):
        # Inherit docs from ParserI

        tokens = list(tokens)
        self._grammar.check_coverage(tokens)

        # Start a recursive descent parse, with an initial tree
        # containing just the start symbol.
        start = self._grammar.start().symbol()
        initial_tree = Tree(start, [])
        frontier = [()]
        if self._trace:
            self._trace_start(initial_tree, frontier, tokens)
        return self._parse(tokens, initial_tree, frontier)

    def _parse(self, remaining_text, tree, frontier):
        """
        Recursively expand and match each elements of ``tree``
        specified by ``frontier``, to cover ``remaining_text``.  Return
        a list of all parses found.

        :return: An iterator of all parses that can be generated by
            matching and expanding the elements of ``tree``
            specified by ``frontier``.
        :rtype: iter(Tree)
        :type tree: Tree
        :param tree: A partial structure for the text that is
            currently being parsed.  The elements of ``tree``
            that are specified by ``frontier`` have not yet been
            expanded or matched.
        :type remaining_text: list(str)
        :param remaining_text: The portion of the text that is not yet
            covered by ``tree``.
        :type frontier: list(tuple(int))
        :param frontier: A list of the locations within ``tree`` of
            all subtrees that have not yet been expanded, and all
            leaves that have not yet been matched.  This list sorted
            in left-to-right order of location within the tree.
        """

        # If the tree covers the text, and there's nothing left to
        # expand, then we've found a complete parse; return it.
        if len(remaining_text) == 0 and len(frontier) == 0:
            if self._trace:
                self._trace_succeed(tree, frontier)
            yield tree

        # If there's still text, but nothing left to expand, we failed.
        elif len(frontier) == 0:
            if self._trace:
                self._trace_backtrack(tree, frontier)

        # If the next element on the frontier is a tree, expand it.
        elif isinstance(tree[frontier[0]], Tree):
            yield from self._expand(remaining_text, tree, frontier)

        # If the next element on the frontier is a token, match it.
        else:
            yield from self._match(remaining_text, tree, frontier)

    def _match(self, rtext, tree, frontier):
        """
        :rtype: iter(Tree)
        :return: an iterator of all parses that can be generated by
            matching the first element of ``frontier`` against the
            first token in ``rtext``.  In particular, if the first
            element of ``frontier`` has the same type as the first
            token in ``rtext``, then substitute the token into
            ``tree``; and return all parses that can be generated by
            matching and expanding the remaining elements of
            ``frontier``.  If the first element of ``frontier`` does not
            have the same type as the first token in ``rtext``, then
            return empty list.

        :type tree: Tree
        :param tree: A partial structure for the text that is
            currently being parsed.  The elements of ``tree``
            that are specified by ``frontier`` have not yet been
            expanded or matched.
        :type rtext: list(str)
        :param rtext: The portion of the text that is not yet
            covered by ``tree``.
        :type frontier: list of tuple of int
        :param frontier: A list of the locations within ``tree`` of
            all subtrees that have not yet been expanded, and all
            leaves that have not yet been matched.
        """

        tree_leaf = tree[frontier[0]]
        if len(rtext) > 0 and tree_leaf == rtext[0]:
            # If it's a terminal that matches rtext[0], then substitute
            # in the token, and continue parsing.
            newtree = tree.copy(deep=True)
            newtree[frontier[0]] = rtext[0]
            if self._trace:
                self._trace_match(newtree, frontier[1:], rtext[0])
            yield from self._parse(rtext[1:], newtree, frontier[1:])
        else:
            # If it's a non-matching terminal, fail.
            if self._trace:
                self._trace_backtrack(tree, frontier, rtext[:1])

    def _expand(self, remaining_text, tree, frontier, production=None):
        """
        :rtype: iter(Tree)
        :return: An iterator of all parses that can be generated by
            expanding the first element of ``frontier`` with
            ``production``.  In particular, if the first element of
            ``frontier`` is a subtree whose node type is equal to
            ``production``'s left hand side, then add a child to that
            subtree for each element of ``production``'s right hand
            side; and return all parses that can be generated by
            matching and expanding the remaining elements of
            ``frontier``.  If the first element of ``frontier`` is not a
            subtree whose node type is equal to ``production``'s left
            hand side, then return an empty list.  If ``production`` is
            not specified, then return a list of all parses that can
            be generated by expanding the first element of ``frontier``
            with *any* CFG production.

        :type tree: Tree
        :param tree: A partial structure for the text that is
            currently being parsed.  The elements of ``tree``
            that are specified by ``frontier`` have not yet been
            expanded or matched.
        :type remaining_text: list(str)
        :param remaining_text: The portion of the text that is not yet
            covered by ``tree``.
        :type frontier: list(tuple(int))
        :param frontier: A list of the locations within ``tree`` of
            all subtrees that have not yet been expanded, and all
            leaves that have not yet been matched.
        """

        if production is None:
            productions = self._grammar.productions()
        else:
            productions = [production]

        for production in productions:
            lhs = production.lhs().symbol()
            if lhs == tree[frontier[0]].label():
                subtree = self._production_to_tree(production)
                if frontier[0] == ():
                    newtree = subtree
                else:
                    newtree = tree.copy(deep=True)
                    newtree[frontier[0]] = subtree
                new_frontier = [
                    frontier[0] + (i,) for i in range(len(production.rhs()))
                ]
                if self._trace:
                    self._trace_expand(newtree, new_frontier, production)
                yield from self._parse(
                    remaining_text, newtree, new_frontier + frontier[1:]
                )

    def _production_to_tree(self, production):
        """
        :rtype: Tree
        :return: The Tree that is licensed by ``production``.
            In particular, given the production ``[lhs -> elt[1] ... elt[n]]``
            return a tree that has a node ``lhs.symbol``, and
            ``n`` children.  For each nonterminal element
            ``elt[i]`` in the production, the tree token has a
            childless subtree with node value ``elt[i].symbol``; and
            for each terminal element ``elt[j]``, the tree token has
            a leaf token with type ``elt[j]``.

        :param production: The CFG production that licenses the tree
            token that should be returned.
        :type production: Production
        """
        children = []
        for elt in production.rhs():
            if isinstance(elt, Nonterminal):
                children.append(Tree(elt.symbol(), []))
            else:
                # This will be matched.
                children.append(elt)
        return Tree(production.lhs().symbol(), children)

    def trace(self, trace=2):
        """
        Set the level of tracing output that should be generated when
        parsing a text.

        :type trace: int
        :param trace: The trace level.  A trace level of ``0`` will
            generate no tracing output; and higher trace levels will
            produce more verbose tracing output.
        :rtype: None
        """
        self._trace = trace

    def _trace_fringe(self, tree, treeloc=None):
        """
        Print trace output displaying the fringe of ``tree``.  The
        fringe of ``tree`` consists of all of its leaves and all of
        its childless subtrees.

        :rtype: None
        """

        if treeloc == ():
            print("*", end=" ")
        if isinstance(tree, Tree):
            if len(tree) == 0:
                print(repr(Nonterminal(tree.label())), end=" ")
            for i in range(len(tree)):
                if treeloc is not None and i == treeloc[0]:
                    self._trace_fringe(tree[i], treeloc[1:])
                else:
                    self._trace_fringe(tree[i])
        else:
            print(repr(tree), end=" ")

    def _trace_tree(self, tree, frontier, operation):
        """
        Print trace output displaying the parser's current state.

        :param operation: A character identifying the operation that
            generated the current state.
        :rtype: None
        """
        if self._trace == 2:
            print("  %c [" % operation, end=" ")
        else:
            print("    [", end=" ")
        if len(frontier) > 0:
            self._trace_fringe(tree, frontier[0])
        else:
            self._trace_fringe(tree)
        print("]")

    def _trace_start(self, tree, frontier, text):
        print("Parsing %r" % " ".join(text))
        if self._trace > 2:
            print("Start:")
        if self._trace > 1:
            self._trace_tree(tree, frontier, " ")

    def _trace_expand(self, tree, frontier, production):
        if self._trace > 2:
            print("Expand: %s" % production)
        if self._trace > 1:
            self._trace_tree(tree, frontier, "E")

    def _trace_match(self, tree, frontier, tok):
        if self._trace > 2:
            print("Match: %r" % tok)
        if self._trace > 1:
            self._trace_tree(tree, frontier, "M")

    def _trace_succeed(self, tree, frontier):
        if self._trace > 2:
            print("GOOD PARSE:")
        if self._trace == 1:
            print("Found a parse:\n%s" % tree)
        if self._trace > 1:
            self._trace_tree(tree, frontier, "+")

    def _trace_backtrack(self, tree, frontier, toks=None):
        if self._trace > 2:
            if toks:
                print("Backtrack: %r match failed" % toks[0])
            else:
                print("Backtrack")


##//////////////////////////////////////////////////////
##  Stepping Recursive Descent Parser
##//////////////////////////////////////////////////////
class SteppingRecursiveDescentParser(RecursiveDescentParser):
    """
    A ``RecursiveDescentParser`` that allows you to step through the
    parsing process, performing a single operation at a time.

    The ``initialize`` method is used to start parsing a text.
    ``expand`` expands the first element on the frontier using a single
    CFG production, and ``match`` matches the first element on the
    frontier against the next text token. ``backtrack`` undoes the most
    recent expand or match operation.  ``step`` performs a single
    expand, match, or backtrack operation.  ``parses`` returns the set
    of parses that have been found by the parser.

    :ivar _history: A list of ``(rtext, tree, frontier)`` tripples,
        containing the previous states of the parser.  This history is
        used to implement the ``backtrack`` operation.
    :ivar _tried_e: A record of all productions that have been tried
        for a given tree.  This record is used by ``expand`` to perform
        the next untried production.
    :ivar _tried_m: A record of what tokens have been matched for a
        given tree.  This record is used by ``step`` to decide whether
        or not to match a token.
    :see: ``nltk.grammar``
    """

    def __init__(self, grammar, trace=0):
        super().__init__(grammar, trace)
        self._rtext = None
        self._tree = None
        self._frontier = [()]
        self._tried_e = {}
        self._tried_m = {}
        self._history = []
        self._parses = []

    # [XX] TEMPORARY HACK WARNING!  This should be replaced with
    # something nicer when we get the chance.
    def _freeze(self, tree):
        c = tree.copy()
        #        for pos in c.treepositions('leaves'):
        #            c[pos] = c[pos].freeze()
        return ImmutableTree.convert(c)

    def parse(self, tokens):
        tokens = list(tokens)
        self.initialize(tokens)
        while self.step() is not None:
            pass
        return self.parses()

    def initialize(self, tokens):
        """
        Start parsing a given text.  This sets the parser's tree to
        the start symbol, its frontier to the root node, and its
        remaining text to ``token['SUBTOKENS']``.
        """

        self._rtext = tokens
        start = self._grammar.start().symbol()
        self._tree = Tree(start, [])
        self._frontier = [()]
        self._tried_e = {}
        self._tried_m = {}
        self._history = []
        self._parses = []
        if self._trace:
            self._trace_start(self._tree, self._frontier, self._rtext)

    def remaining_text(self):
        """
        :return: The portion of the text that is not yet covered by the
            tree.
        :rtype: list(str)
        """
        return self._rtext

    def frontier(self):
        """
        :return: A list of the tree locations of all subtrees that
            have not yet been expanded, and all leaves that have not
            yet been matched.
        :rtype: list(tuple(int))
        """
        return self._frontier

    def tree(self):
        """
        :return: A partial structure for the text that is
            currently being parsed.  The elements specified by the
            frontier have not yet been expanded or matched.
        :rtype: Tree
        """
        return self._tree

    def step(self):
        """
        Perform a single parsing operation.  If an untried match is
        possible, then perform the match, and return the matched
        token.  If an untried expansion is possible, then perform the
        expansion, and return the production that it is based on.  If
        backtracking is possible, then backtrack, and return True.
        Otherwise, return None.

        :return: None if no operation was performed; a token if a match
            was performed; a production if an expansion was performed;
            and True if a backtrack operation was performed.
        :rtype: Production or String or bool
        """
        # Try matching (if we haven't already)
        if self.untried_match():
            token = self.match()
            if token is not None:
                return token

        # Try expanding.
        production = self.expand()
        if production is not None:
            return production

        # Try backtracking
        if self.backtrack():
            self._trace_backtrack(self._tree, self._frontier)
            return True

        # Nothing left to do.
        return None

    def expand(self, production=None):
        """
        Expand the first element of the frontier.  In particular, if
        the first element of the frontier is a subtree whose node type
        is equal to ``production``'s left hand side, then add a child
        to that subtree for each element of ``production``'s right hand
        side.  If ``production`` is not specified, then use the first
        untried expandable production.  If all expandable productions
        have been tried, do nothing.

        :return: The production used to expand the frontier, if an
           expansion was performed.  If no expansion was performed,
           return None.
        :rtype: Production or None
        """

        # Make sure we *can* expand.
        if len(self._frontier) == 0:
            return None
        if not isinstance(self._tree[self._frontier[0]], Tree):
            return None

        # If they didn't specify a production, check all untried ones.
        if production is None:
            productions = self.untried_expandable_productions()
        else:
            productions = [production]

        parses = []
        for prod in productions:
            # Record that we've tried this production now.
            self._tried_e.setdefault(self._freeze(self._tree), []).append(prod)

            # Try expanding.
            for _result in self._expand(self._rtext, self._tree, self._frontier, prod):
                return prod

        # We didn't expand anything.
        return None

    def match(self):
        """
        Match the first element of the frontier.  In particular, if
        the first element of the frontier has the same type as the
        next text token, then substitute the text token into the tree.

        :return: The token matched, if a match operation was
            performed.  If no match was performed, return None
        :rtype: str or None
        """

        # Record that we've tried matching this token.
        tok = self._rtext[0]
        self._tried_m.setdefault(self._freeze(self._tree), []).append(tok)

        # Make sure we *can* match.
        if len(self._frontier) == 0:
            return None
        if isinstance(self._tree[self._frontier[0]], Tree):
            return None

        for _result in self._match(self._rtext, self._tree, self._frontier):
            # Return the token we just matched.
            return self._history[-1][0][0]
        return None

    def backtrack(self):
        """
        Return the parser to its state before the most recent
        match or expand operation.  Calling ``undo`` repeatedly return
        the parser to successively earlier states.  If no match or
        expand operations have been performed, ``undo`` will make no
        changes.

        :return: true if an operation was successfully undone.
        :rtype: bool
        """
        if len(self._history) == 0:
            return False
        (self._rtext, self._tree, self._frontier) = self._history.pop()
        return True

    def expandable_productions(self):
        """
        :return: A list of all the productions for which expansions
            are available for the current parser state.
        :rtype: list(Production)
        """
        # Make sure we *can* expand.
        if len(self._frontier) == 0:
            return []
        frontier_child = self._tree[self._frontier[0]]
        if len(self._frontier) == 0 or not isinstance(frontier_child, Tree):
            return []

        return [
            p
            for p in self._grammar.productions()
            if p.lhs().symbol() == frontier_child.label()
        ]

    def untried_expandable_productions(self):
        """
        :return: A list of all the untried productions for which
            expansions are available for the current parser state.
        :rtype: list(Production)
        """

        tried_expansions = self._tried_e.get(self._freeze(self._tree), [])
        return [p for p in self.expandable_productions() if p not in tried_expansions]

    def untried_match(self):
        """
        :return: Whether the first element of the frontier is a token
            that has not yet been matched.
        :rtype: bool
        """

        if len(self._rtext) == 0:
            return False
        tried_matches = self._tried_m.get(self._freeze(self._tree), [])
        return self._rtext[0] not in tried_matches

    def currently_complete(self):
        """
        :return: Whether the parser's current state represents a
            complete parse.
        :rtype: bool
        """
        return len(self._frontier) == 0 and len(self._rtext) == 0

    def _parse(self, remaining_text, tree, frontier):
        """
        A stub version of ``_parse`` that sets the parsers current
        state to the given arguments.  In ``RecursiveDescentParser``,
        the ``_parse`` method is used to recursively continue parsing a
        text.  ``SteppingRecursiveDescentParser`` overrides it to
        capture these recursive calls.  It records the parser's old
        state in the history (to allow for backtracking), and updates
        the parser's new state using the given arguments.  Finally, it
        returns ``[1]``, which is used by ``match`` and ``expand`` to
        detect whether their operations were successful.

        :return: ``[1]``
        :rtype: list of int
        """
        self._history.append((self._rtext, self._tree, self._frontier))
        self._rtext = remaining_text
        self._tree = tree
        self._frontier = frontier

        # Is it a good parse?  If so, record it.
        if len(frontier) == 0 and len(remaining_text) == 0:
            self._parses.append(tree)
            self._trace_succeed(self._tree, self._frontier)

        return [1]

    def parses(self):
        """
        :return: An iterator of the parses that have been found by this
            parser so far.
        :rtype: list of Tree
        """
        return iter(self._parses)

    def set_grammar(self, grammar):
        """
        Change the grammar used to parse texts.

        :param grammar: The new grammar.
        :type grammar: CFG
        """
        self._grammar = grammar


##//////////////////////////////////////////////////////
##  Demonstration Code
##//////////////////////////////////////////////////////


def demo():
    """
    A demonstration of the recursive descent parser.
    """

    from nltk import CFG, parse

    grammar = CFG.fromstring(
        """
    S -> NP VP
    NP -> Det N | Det N PP
    VP -> V NP | V NP PP
    PP -> P NP
    NP -> 'I'
    N -> 'man' | 'park' | 'telescope' | 'dog'
    Det -> 'the' | 'a'
    P -> 'in' | 'with'
    V -> 'saw'
    """
    )

    for prod in grammar.productions():
        print(prod)

    sent = "I saw a man in the park".split()
    parser = parse.RecursiveDescentParser(grammar, trace=2)
    for p in parser.parse(sent):
        print(p)


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\scriptutils.py ===
"""
Various utilities for running/importing a script
"""

import bdb
import linecache
import os
import sys
import traceback

import __main__
import win32api
import win32con
import win32ui
from pywin.mfc import dialog
from pywin.mfc.docview import TreeView

from .cmdline import ParseArgs

RS_DEBUGGER_NONE = 0  # Don't run under the debugger.
RS_DEBUGGER_STEP = 1  # Start stepping under the debugger
RS_DEBUGGER_GO = 2  # Just run under the debugger, stopping only at break-points.
RS_DEBUGGER_PM = (
    3  # Don't run under debugger, but do post-mortem analysis on exception.
)

debugging_options = """No debugging
Step-through in the debugger
Run in the debugger
Post-Mortem of unhandled exceptions""".split("\n")

byte_cr = b"\r"
byte_lf = b"\n"
byte_crlf = b"\r\n"


# A dialog box for the "Run Script" command.
class DlgRunScript(dialog.Dialog):
    "A class for the 'run script' dialog"

    def __init__(self, bHaveDebugger):
        dialog.Dialog.__init__(self, win32ui.IDD_RUN_SCRIPT)
        self.AddDDX(win32ui.IDC_EDIT1, "script")
        self.AddDDX(win32ui.IDC_EDIT2, "args")
        self.AddDDX(win32ui.IDC_COMBO1, "debuggingType", "i")
        self.HookCommand(self.OnBrowse, win32ui.IDC_BUTTON2)
        self.bHaveDebugger = bHaveDebugger

    def OnInitDialog(self):
        rc = dialog.Dialog.OnInitDialog(self)
        cbo = self.GetDlgItem(win32ui.IDC_COMBO1)
        for o in debugging_options:
            cbo.AddString(o)
        cbo.SetCurSel(self["debuggingType"])
        if not self.bHaveDebugger:
            cbo.EnableWindow(0)

    def OnBrowse(self, id, code):
        if code != 0:  # BN_CLICKED
            return 1
        openFlags = win32con.OFN_OVERWRITEPROMPT | win32con.OFN_FILEMUSTEXIST
        dlg = win32ui.CreateFileDialog(
            1, None, None, openFlags, "Python Scripts (*.py)|*.py||", self
        )
        dlg.SetOFNTitle("Run Script")
        if dlg.DoModal() != win32con.IDOK:
            return 0
        self["script"] = dlg.GetPathName()
        self.UpdateData(0)
        return 0


def GetDebugger():
    """Get the default Python debugger.  Returns the debugger, or None.

    It is assumed the debugger has a standard "pdb" defined interface.
    Currently always returns the 'pywin.debugger' debugger, or None
    (pdb is _not_ returned as it is not effective in this GUI environment)
    """
    try:
        import pywin.debugger

        return pywin.debugger
    except ImportError:
        return None


def IsOnPythonPath(path):
    "Given a path only, see if it is on the Pythonpath.  Assumes path is a full path spec."
    # must check that the command line arg's path is in sys.path
    for syspath in sys.path:
        try:
            # sys.path can have an empty entry.
            if syspath and win32ui.FullPath(syspath) == path:
                return 1
        except win32ui.error as details:
            print(f"Warning: The sys.path entry '{syspath}' is invalid\n{details}")
    return 0


def GetPackageModuleName(fileName):
    r"""Given a filename, return (module name, new path).
    eg - given "c:\a\b\c\my.py", return ("b.c.my",None) if "c:\a" is on sys.path.
    If no package found, will return ("my", "c:\a\b\c")
    """
    path, fname = os.path.split(fileName)
    path = origPath = win32ui.FullPath(path)
    fname = os.path.splitext(fname)[0]
    modBits = []
    newPathReturn = None
    if not IsOnPythonPath(path):
        # Module not directly on the search path - see if under a package.
        while len(path) > 3:  # ie 'C:\'
            path, modBit = os.path.split(path)
            modBits.append(modBit)
            # If on path, _and_ existing package of that name loaded.
            if (
                IsOnPythonPath(path)
                and modBit in sys.modules
                and (
                    os.path.exists(os.path.join(path, modBit, "__init__.py"))
                    or os.path.exists(os.path.join(path, modBit, "__init__.pyc"))
                    or os.path.exists(os.path.join(path, modBit, "__init__.pyo"))
                )
            ):
                modBits.reverse()
                return ".".join(modBits) + "." + fname, newPathReturn
            # Not found - look a level higher
        else:
            newPathReturn = origPath

    return fname, newPathReturn


def GetActiveView():
    """Gets the edit control (eg, EditView) with the focus, or None"""
    try:
        childFrame, bIsMaximised = win32ui.GetMainFrame().MDIGetActive()
        return childFrame.GetActiveView()
    except win32ui.error:
        return None


def GetActiveEditControl():
    view = GetActiveView()
    if view is None:
        return None
    if hasattr(view, "SCIAddText"):  # Is it a scintilla control?
        return view
    try:
        return view.GetRichEditCtrl()
    except AttributeError:
        pass
    try:
        return view.GetEditCtrl()
    except AttributeError:
        pass


def GetActiveEditorDocument():
    """Returns the active editor document and view, or (None,None) if no
    active document or it's not an editor document.
    """
    view = GetActiveView()
    if view is None or isinstance(view, TreeView):
        return (None, None)
    doc = view.GetDocument()
    if hasattr(doc, "MarkerAdd"):  # Is it an Editor document?
        return doc, view
    return (None, None)


def GetActiveFileName(bAutoSave=1):
    """Gets the file name for the active frame, saving it if necessary.

    Returns None if it can't be found, or raises KeyboardInterrupt.
    """
    pathName = None
    active = GetActiveView()
    if active is None:
        return None
    try:
        doc = active.GetDocument()
        pathName = doc.GetPathName()

        if bAutoSave and (
            len(pathName) > 0
            or doc.GetTitle()[:8] == "Untitled"
            or doc.GetTitle()[:6] == "Script"
        ):  # if not a special purpose window
            if doc.IsModified():
                try:
                    doc.OnSaveDocument(pathName)
                    pathName = doc.GetPathName()

                    # clear the linecache buffer
                    linecache.clearcache()

                except win32ui.error:
                    raise KeyboardInterrupt

    except (win32ui.error, AttributeError):
        pass
    if not pathName:
        return None
    return pathName


lastScript = ""
lastArgs = ""
lastDebuggingType = RS_DEBUGGER_NONE


def RunScript(defName=None, defArgs=None, bShowDialog=1, debuggingType=None):
    global lastScript, lastArgs, lastDebuggingType
    _debugger_stop_frame_ = 1  # Magic variable so the debugger will hide me!

    # Get the debugger - may be None!
    debugger = GetDebugger()

    if defName is None:
        try:
            pathName = GetActiveFileName()
        except KeyboardInterrupt:
            return  # User cancelled save.
    else:
        pathName = defName
    if not pathName:
        pathName = lastScript
    if defArgs is None:
        args = ""
        if pathName == lastScript:
            args = lastArgs
    else:
        args = defArgs
    if debuggingType is None:
        debuggingType = lastDebuggingType

    if not pathName or bShowDialog:
        dlg = DlgRunScript(debugger is not None)
        dlg["script"] = pathName
        dlg["args"] = args
        dlg["debuggingType"] = debuggingType
        if dlg.DoModal() != win32con.IDOK:
            return
        script = dlg["script"]
        args = dlg["args"]
        debuggingType = dlg["debuggingType"]
        if not script:
            return
        if debuggingType == RS_DEBUGGER_GO and debugger is not None:
            # This may surprise users - they select "Run under debugger", but
            # it appears not to!  Only warn when they pick from the dialog!
            # First - ensure the debugger is activated to pickup any break-points
            # set in the editor.
            try:
                # Create the debugger, but _dont_ init the debugger GUI.
                rd = debugger._GetCurrentDebugger()
            except AttributeError:
                rd = None
            if rd is not None and len(rd.breaks) == 0:
                msg = "There are no active break-points.\r\n\r\nSelecting this debug option without any\r\nbreak-points is unlikely to have the desired effect\r\nas the debugger is unlikely to be invoked..\r\n\r\nWould you like to step-through in the debugger instead?"
                rc = win32ui.MessageBox(
                    msg,
                    win32ui.LoadString(win32ui.IDR_DEBUGGER),
                    win32con.MB_YESNOCANCEL | win32con.MB_ICONINFORMATION,
                )
                if rc == win32con.IDCANCEL:
                    return
                if rc == win32con.IDYES:
                    debuggingType = RS_DEBUGGER_STEP

        lastDebuggingType = debuggingType
        lastScript = script
        lastArgs = args
    else:
        script = pathName

    # try and open the script.
    if (
        len(os.path.splitext(script)[1]) == 0
    ):  # check if no extension supplied, and give one.
        script += ".py"
    # If no path specified, try and locate the file
    path, fnameonly = os.path.split(script)
    if len(path) == 0:
        try:
            os.stat(fnameonly)  # See if it is OK as is...
            script = fnameonly
        except OSError:
            fullScript = LocatePythonFile(script)
            if fullScript is None:
                win32ui.MessageBox("The file '%s' can not be located" % script)
                return
            script = fullScript
    else:
        path = win32ui.FullPath(path)
        if not IsOnPythonPath(path):
            sys.path.append(path)

    # py3k fun: If we use text mode to open the file, we get \r\n
    # translated so Python allows the syntax (good!), but we get back
    # text already decoded from the default encoding (bad!) and Python
    # ignores any encoding decls (bad!).  If we use binary mode we get
    # the raw bytes and Python looks at the encoding (good!) but \r\n
    # chars stay in place so Python throws a syntax error (bad!).
    # So: do the binary thing and manually normalize \r\n.
    try:
        f = open(script, "rb")
    except OSError as exc:
        win32ui.MessageBox(
            "The file could not be opened - %s (%d)" % (exc.strerror, exc.errno)
        )
        return

    # Get the source-code - as above, normalize \r\n
    code = f.read().replace(byte_crlf, byte_lf).replace(byte_cr, byte_lf) + byte_lf

    # Remember and hack sys.argv for the script.
    oldArgv = sys.argv
    sys.argv = ParseArgs(args)
    sys.argv.insert(0, script)
    # sys.path[0] is the path of the script
    oldPath0 = sys.path[0]
    newPath0 = os.path.split(script)[0]
    if not oldPath0:  # if sys.path[0] is empty
        sys.path[0] = newPath0
        insertedPath0 = 0
    else:
        sys.path.insert(0, newPath0)
        insertedPath0 = 1
    bWorked = 0
    win32ui.DoWaitCursor(1)
    base = os.path.split(script)[1]
    # Allow windows to repaint before starting.
    win32ui.PumpWaitingMessages()
    win32ui.SetStatusText("Running script %s..." % base, 1)
    exitCode = 0
    from pywin.framework import interact

    # Check the debugger flags
    if debugger is None and (debuggingType != RS_DEBUGGER_NONE):
        win32ui.MessageBox(
            "No debugger is installed.  Debugging options have been ignored!"
        )
        debuggingType = RS_DEBUGGER_NONE

    # Get a code object - ignore the debugger for this, as it is probably a syntax error
    # at this point
    try:
        codeObject = compile(code, script, "exec")
    except:
        # Almost certainly a syntax error!
        _HandlePythonFailure("run script", script)
        # No code object which to run/debug.
        return
    __main__.__file__ = script
    try:
        if debuggingType == RS_DEBUGGER_STEP:
            debugger.run(codeObject, __main__.__dict__, start_stepping=1)
        elif debuggingType == RS_DEBUGGER_GO:
            debugger.run(codeObject, __main__.__dict__, start_stepping=0)
        else:
            # Post mortem or no debugging
            exec(codeObject, __main__.__dict__)
        bWorked = 1
    except bdb.BdbQuit:
        # Don't print tracebacks when the debugger quit, but do print a message.
        print("Debugging session cancelled.")
        exitCode = 1
        bWorked = 1
    except SystemExit as code:
        exitCode = code
        bWorked = 1
    except KeyboardInterrupt:
        # Consider this successful, as we don't want the debugger.
        # (but we do want a traceback!)
        if interact.edit and interact.edit.currentView:
            interact.edit.currentView.EnsureNoPrompt()
        traceback.print_exc()
        if interact.edit and interact.edit.currentView:
            interact.edit.currentView.AppendToPrompt([])
        bWorked = 1
    except:
        if interact.edit and interact.edit.currentView:
            interact.edit.currentView.EnsureNoPrompt()
        traceback.print_exc()
        if interact.edit and interact.edit.currentView:
            interact.edit.currentView.AppendToPrompt([])
        if debuggingType == RS_DEBUGGER_PM:
            debugger.pm()
    del __main__.__file__
    sys.argv = oldArgv
    if insertedPath0:
        del sys.path[0]
    else:
        sys.path[0] = oldPath0
    f.close()
    if bWorked:
        win32ui.SetStatusText(f"Script '{script}' returned exit code {exitCode}")
    else:
        win32ui.SetStatusText("Exception raised while running script  %s" % base)
    try:
        sys.stdout.flush()
    except AttributeError:
        pass

    win32ui.DoWaitCursor(0)


def ImportFile():
    """This code looks for the current window, and determines if it can be imported.  If not,
    it will prompt for a file name, and allow it to be imported."""
    try:
        pathName = GetActiveFileName()
    except KeyboardInterrupt:
        pathName = None

    if pathName is not None:
        if os.path.splitext(pathName)[1].lower() not in (".py", ".pyw", ".pyx"):
            pathName = None

    if pathName is None:
        openFlags = win32con.OFN_OVERWRITEPROMPT | win32con.OFN_FILEMUSTEXIST
        dlg = win32ui.CreateFileDialog(
            1, None, None, openFlags, "Python Scripts (*.py;*.pyw)|*.py;*.pyw;*.pyx||"
        )
        dlg.SetOFNTitle("Import Script")
        if dlg.DoModal() != win32con.IDOK:
            return 0

        pathName = dlg.GetPathName()

    # If already imported, don't look for package
    path, modName = os.path.split(pathName)
    modName, modExt = os.path.splitext(modName)
    newPath = None
    # note that some packages (*cough* email *cough*) use "lazy importers"
    # meaning sys.modules can change as a side-effect of looking at
    # module.__file__ - so we must take a copy (ie, list(items()))
    for key, mod in sys.modules.items():
        if getattr(mod, "__file__", None):
            fname = mod.__file__
            base, ext = os.path.splitext(fname)
            if ext.lower() in (".pyo", ".pyc"):
                ext = ".py"
            fname = base + ext
            if win32ui.ComparePath(fname, pathName):
                modName = key
                break
    else:  # for not broken
        modName, newPath = GetPackageModuleName(pathName)
        if newPath:
            sys.path.append(newPath)

    if modName in sys.modules:
        bNeedReload = 1
        what = "reload"
    else:
        what = "import"
        bNeedReload = 0

    win32ui.SetStatusText(what.capitalize() + "ing module...", 1)
    win32ui.DoWaitCursor(1)
    # 	win32ui.GetMainFrame().BeginWaitCursor()

    try:
        # always do an import, as it is cheap if it's already loaded.  This ensures
        # it is in our name space.
        codeObj = compile("import " + modName, "<auto import>", "exec")
    except SyntaxError:
        win32ui.SetStatusText('Invalid filename for import: "' + modName + '"')
        return
    try:
        exec(codeObj, __main__.__dict__)
        mod = sys.modules.get(modName)
        if bNeedReload:
            from importlib import reload

            mod = reload(sys.modules[modName])
        win32ui.SetStatusText(
            "Successfully "
            + what
            + "ed module '"
            + modName
            + "': %s" % getattr(mod, "__file__", "<unkown file>")
        )
    except:
        _HandlePythonFailure(what)
    win32ui.DoWaitCursor(0)


def CheckFile():
    """This code looks for the current window, and gets Python to check it
    without actually executing any code (ie, by compiling only)
    """
    try:
        pathName = GetActiveFileName()
    except KeyboardInterrupt:
        return

    what = "check"
    win32ui.SetStatusText(what.capitalize() + "ing module...", 1)
    win32ui.DoWaitCursor(1)
    try:
        f = open(pathName)
    except OSError as details:
        print(f"Can't open file '{pathName}' - {details}")
        return
    try:
        code = f.read() + "\n"
    finally:
        f.close()
    try:
        codeObj = compile(code, pathName, "exec")
        if RunTabNanny(pathName):
            win32ui.SetStatusText(
                "Python and the TabNanny successfully checked the file '"
                + os.path.basename(pathName)
                + "'"
            )
    except SyntaxError:
        _HandlePythonFailure(what, pathName)
    except:
        traceback.print_exc()
        _HandlePythonFailure(what)
    win32ui.DoWaitCursor(0)


def RunTabNanny(filename):
    import io

    tabnanny = FindTabNanny()
    if tabnanny is None:
        win32ui.MessageBox("The TabNanny is not around, so the children can run amok!")
        return

    # Capture the tab-nanny output
    newout = io.StringIO()
    old_out = sys.stderr, sys.stdout
    sys.stderr = sys.stdout = newout
    try:
        tabnanny.check(filename)
    finally:
        # Restore output
        sys.stderr, sys.stdout = old_out
    data = newout.getvalue()
    if data:
        try:
            lineno = data.split()[1]
            lineno = int(lineno)
            _JumpToPosition(filename, lineno)
            try:  # Try and display whitespace
                GetActiveEditControl().SCISetViewWS(1)
            except:
                pass
            win32ui.SetStatusText("The TabNanny found trouble at line %d" % lineno)
        except (IndexError, TypeError, ValueError):
            print("The tab nanny complained, but I can't see where!")
            print(data)
        return 0
    return 1


def _JumpToPosition(fileName, lineno, col=1):
    JumpToDocument(fileName, lineno, col)


def JumpToDocument(fileName, lineno=0, col=1, nChars=0, bScrollToTop=0):
    # Jump to the position in a file.
    # If lineno is <= 0, don't move the position - just open/restore.
    # if nChars > 0, select that many characters.
    # if bScrollToTop, the specified line will be moved to the top of the window
    #  (eg, bScrollToTop should be false when jumping to an error line to retain the
    #  context, but true when jumping to a method defn, where we want the full body.
    # Return the view which is editing the file, or None on error.
    doc = win32ui.GetApp().OpenDocumentFile(fileName)
    if doc is None:
        return None
    frame = doc.GetFirstView().GetParentFrame()
    try:
        view = frame.GetEditorView()
        if frame.GetActiveView() != view:
            frame.SetActiveView(view)
        frame.AutoRestore()
    except AttributeError:  # Not an editor frame??
        view = doc.GetFirstView()
    if lineno > 0:
        charNo = view.LineIndex(lineno - 1)
        start = charNo + col - 1
        size = view.GetTextLength()
        try:
            view.EnsureCharsVisible(charNo)
        except AttributeError:
            print("Doesn't appear to be one of our views?")
        view.SetSel(min(start, size), min(start + nChars, size))
    if bScrollToTop:
        curTop = view.GetFirstVisibleLine()
        nScroll = (lineno - 1) - curTop
        view.LineScroll(nScroll, 0)
    view.SetFocus()
    return view


def _HandlePythonFailure(what, syntaxErrorPathName=None):
    typ, details, tb = sys.exc_info()
    if isinstance(details, SyntaxError):
        try:
            msg, (fileName, line, col, text) = details
            if (not fileName or fileName == "<string>") and syntaxErrorPathName:
                fileName = syntaxErrorPathName
            _JumpToPosition(fileName, line, col)
        except (TypeError, ValueError):
            msg = str(details)
        win32ui.SetStatusText(f"Failed to {what} - syntax error - {msg}")
    else:
        traceback.print_exc()
        win32ui.SetStatusText(f"Failed to {what} - {details}")
    tb = None  # Clean up a cycle.


# Find the Python TabNanny in either the standard library or the Python Tools/Scripts directory.
def FindTabNanny():
    try:
        return __import__("tabnanny")
    except ImportError:
        pass
    # OK - not in the standard library - go looking.
    filename = "tabnanny.py"
    try:
        path = win32api.RegQueryValue(
            win32con.HKEY_LOCAL_MACHINE,
            "SOFTWARE\\Python\\PythonCore\\%s\\InstallPath" % (sys.winver),
        )
    except win32api.error:
        print("WARNING - The Python registry does not have an 'InstallPath' setting")
        print("          The file '%s' can not be located" % (filename))
        return None
    fname = os.path.join(path, "Tools\\Scripts\\%s" % filename)
    try:
        os.stat(fname)
    except OSError:
        print(f"WARNING - The file '{filename}' can not be located in path '{path}'")
        return None

    tabnannyhome, tabnannybase = os.path.split(fname)
    tabnannybase = os.path.splitext(tabnannybase)[0]
    # Put tab nanny at the top of the path.
    sys.path.insert(0, tabnannyhome)
    try:
        return __import__(tabnannybase)
    finally:
        # remove the tab-nanny from the path
        del sys.path[0]


def LocatePythonFile(fileName, bBrowseIfDir=1):
    "Given a file name, return a fully qualified file name, or None"
    # first look for the exact file as specified
    if not os.path.isfile(fileName):
        # Go looking!
        baseName = fileName
        for path in sys.path:
            fileName = os.path.abspath(os.path.join(path, baseName))
            if os.path.isdir(fileName):
                if bBrowseIfDir:
                    d = win32ui.CreateFileDialog(
                        1, "*.py", None, 0, "Python Files (*.py)|*.py|All files|*.*"
                    )
                    d.SetOFNInitialDir(fileName)
                    rc = d.DoModal()
                    if rc == win32con.IDOK:
                        fileName = d.GetPathName()
                        break
                    else:
                        return None
            else:
                fileName += ".py"
                if os.path.isfile(fileName):
                    break  # Found it!

        else:  # for not broken out of
            return None
    return win32ui.FullPath(fileName)

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_testing.py ===
from __future__ import annotations

# XX this should get broken up, like testing.py did
import tempfile
from typing import TYPE_CHECKING

import pytest

from trio.testing import RaisesGroup

from .. import _core, sleep, socket as tsocket
from .._core._tests.tutil import can_bind_ipv6
from .._highlevel_generic import StapledStream, aclose_forcefully
from .._highlevel_socket import SocketListener
from ..testing import *
from ..testing._check_streams import _assert_raises
from ..testing._memory_streams import _UnboundedByteQueue

if TYPE_CHECKING:
    from trio import Nursery
    from trio.abc import ReceiveStream, SendStream


async def test_wait_all_tasks_blocked() -> None:
    record = []

    async def busy_bee() -> None:
        for _ in range(10):
            await _core.checkpoint()
        record.append("busy bee exhausted")

    async def waiting_for_bee_to_leave() -> None:
        await wait_all_tasks_blocked()
        record.append("quiet at last!")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(busy_bee)
        nursery.start_soon(waiting_for_bee_to_leave)
        nursery.start_soon(waiting_for_bee_to_leave)

    # check cancellation
    record = []

    async def cancelled_while_waiting() -> None:
        try:
            await wait_all_tasks_blocked()
        except _core.Cancelled:
            record.append("ok")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(cancelled_while_waiting)
        nursery.cancel_scope.cancel()
    assert record == ["ok"]


async def test_wait_all_tasks_blocked_with_timeouts(mock_clock: MockClock) -> None:
    record = []

    async def timeout_task() -> None:
        record.append("tt start")
        await sleep(5)
        record.append("tt finished")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(timeout_task)
        await wait_all_tasks_blocked()
        assert record == ["tt start"]
        mock_clock.jump(10)
        await wait_all_tasks_blocked()
        assert record == ["tt start", "tt finished"]


async def test_wait_all_tasks_blocked_with_cushion() -> None:
    record = []

    async def blink() -> None:
        record.append("blink start")
        await sleep(0.01)
        await sleep(0.01)
        await sleep(0.01)
        record.append("blink end")

    async def wait_no_cushion() -> None:
        await wait_all_tasks_blocked()
        record.append("wait_no_cushion end")

    async def wait_small_cushion() -> None:
        await wait_all_tasks_blocked(0.02)
        record.append("wait_small_cushion end")

    async def wait_big_cushion() -> None:
        await wait_all_tasks_blocked(0.03)
        record.append("wait_big_cushion end")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(blink)
        nursery.start_soon(wait_no_cushion)
        nursery.start_soon(wait_small_cushion)
        nursery.start_soon(wait_small_cushion)
        nursery.start_soon(wait_big_cushion)

    assert record == [
        "blink start",
        "wait_no_cushion end",
        "blink end",
        "wait_small_cushion end",
        "wait_small_cushion end",
        "wait_big_cushion end",
    ]


################################################################


async def test_assert_checkpoints(recwarn: pytest.WarningsRecorder) -> None:
    with assert_checkpoints():
        await _core.checkpoint()

    with pytest.raises(AssertionError):
        with assert_checkpoints():
            1 + 1  # noqa: B018  # "useless expression"

    # partial yield cases
    # if you have a schedule point but not a cancel point, or vice-versa, then
    # that's not a checkpoint.
    for partial_yield in [
        _core.checkpoint_if_cancelled,
        _core.cancel_shielded_checkpoint,
    ]:
        print(partial_yield)
        with pytest.raises(AssertionError):
            with assert_checkpoints():
                await partial_yield()

    # But both together count as a checkpoint
    with assert_checkpoints():
        await _core.checkpoint_if_cancelled()
        await _core.cancel_shielded_checkpoint()


async def test_assert_no_checkpoints(recwarn: pytest.WarningsRecorder) -> None:
    with assert_no_checkpoints():
        1 + 1  # noqa: B018  # "useless expression"

    with pytest.raises(AssertionError):
        with assert_no_checkpoints():
            await _core.checkpoint()

    # partial yield cases
    # if you have a schedule point but not a cancel point, or vice-versa, then
    # that doesn't make *either* version of assert_{no_,}yields happy.
    for partial_yield in [
        _core.checkpoint_if_cancelled,
        _core.cancel_shielded_checkpoint,
    ]:
        print(partial_yield)
        with pytest.raises(AssertionError):
            with assert_no_checkpoints():
                await partial_yield()

    # And both together also count as a checkpoint
    with pytest.raises(AssertionError):
        with assert_no_checkpoints():
            await _core.checkpoint_if_cancelled()
            await _core.cancel_shielded_checkpoint()


################################################################


async def test_Sequencer() -> None:
    record = []

    def t(val: object) -> None:
        print(val)
        record.append(val)

    async def f1(seq: Sequencer) -> None:
        async with seq(1):
            t(("f1", 1))
        async with seq(3):
            t(("f1", 3))
        async with seq(4):
            t(("f1", 4))

    async def f2(seq: Sequencer) -> None:
        async with seq(0):
            t(("f2", 0))
        async with seq(2):
            t(("f2", 2))

    seq = Sequencer()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(f1, seq)
        nursery.start_soon(f2, seq)
        async with seq(5):
            await wait_all_tasks_blocked()
        assert record == [("f2", 0), ("f1", 1), ("f2", 2), ("f1", 3), ("f1", 4)]

    seq = Sequencer()
    # Catches us if we try to reuse a sequence point:
    async with seq(0):
        pass
    with pytest.raises(RuntimeError):
        async with seq(0):
            pass  # pragma: no cover


async def test_Sequencer_cancel() -> None:
    # Killing a blocked task makes everything blow up
    record = []
    seq = Sequencer()

    async def child(i: int) -> None:
        with _core.CancelScope() as scope:
            if i == 1:
                scope.cancel()
            try:
                async with seq(i):
                    pass  # pragma: no cover
            except RuntimeError:
                record.append(f"seq({i}) RuntimeError")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(child, 1)
        nursery.start_soon(child, 2)
        async with seq(0):
            pass  # pragma: no cover

    assert record == ["seq(1) RuntimeError", "seq(2) RuntimeError"]

    # Late arrivals also get errors
    with pytest.raises(RuntimeError):
        async with seq(3):
            pass  # pragma: no cover


################################################################
def test__assert_raises() -> None:
    with pytest.raises(AssertionError):
        with _assert_raises(RuntimeError):
            1 + 1  # noqa: B018  # "useless expression"

    with pytest.raises(TypeError):
        with _assert_raises(RuntimeError):
            "foo" + 1  # type: ignore[operator] # noqa: B018  # "useless expression"

    with _assert_raises(RuntimeError):
        raise RuntimeError


# This is a private implementation detail, but it's complex enough to be worth
# testing directly
async def test__UnboundeByteQueue() -> None:
    ubq = _UnboundedByteQueue()

    ubq.put(b"123")
    ubq.put(b"456")
    assert ubq.get_nowait(1) == b"1"
    assert ubq.get_nowait(10) == b"23456"
    ubq.put(b"789")
    assert ubq.get_nowait() == b"789"

    with pytest.raises(_core.WouldBlock):
        ubq.get_nowait(10)
    with pytest.raises(_core.WouldBlock):
        ubq.get_nowait()

    with pytest.raises(TypeError):
        ubq.put("string")  # type: ignore[arg-type]

    ubq.put(b"abc")
    with assert_checkpoints():
        assert await ubq.get(10) == b"abc"
    ubq.put(b"def")
    ubq.put(b"ghi")
    with assert_checkpoints():
        assert await ubq.get(1) == b"d"
    with assert_checkpoints():
        assert await ubq.get() == b"efghi"

    async def putter(data: bytes) -> None:
        await wait_all_tasks_blocked()
        ubq.put(data)

    async def getter(expect: bytes) -> None:
        with assert_checkpoints():
            assert await ubq.get() == expect

    async with _core.open_nursery() as nursery:
        nursery.start_soon(getter, b"xyz")
        nursery.start_soon(putter, b"xyz")

    # Two gets at the same time -> BusyResourceError
    with RaisesGroup(_core.BusyResourceError):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(getter, b"asdf")
            nursery.start_soon(getter, b"asdf")

    # Closing

    ubq.close()
    with pytest.raises(_core.ClosedResourceError):
        ubq.put(b"---")

    assert ubq.get_nowait(10) == b""
    assert ubq.get_nowait() == b""
    assert await ubq.get(10) == b""
    assert await ubq.get() == b""

    # close is idempotent
    ubq.close()

    # close wakes up blocked getters
    ubq2 = _UnboundedByteQueue()

    async def closer() -> None:
        await wait_all_tasks_blocked()
        ubq2.close()

    async with _core.open_nursery() as nursery:
        nursery.start_soon(getter, b"")
        nursery.start_soon(closer)


async def test_MemorySendStream() -> None:
    mss = MemorySendStream()

    async def do_send_all(data: bytes) -> None:
        with assert_checkpoints():
            await mss.send_all(data)

    await do_send_all(b"123")
    assert mss.get_data_nowait(1) == b"1"
    assert mss.get_data_nowait() == b"23"

    with assert_checkpoints():
        await mss.wait_send_all_might_not_block()

    with pytest.raises(_core.WouldBlock):
        mss.get_data_nowait()
    with pytest.raises(_core.WouldBlock):
        mss.get_data_nowait(10)

    await do_send_all(b"456")
    with assert_checkpoints():
        assert await mss.get_data() == b"456"

    # Call send_all twice at once; one should get BusyResourceError and one
    # should succeed. But we can't let the error propagate, because it might
    # cause the other to be cancelled before it can finish doing its thing,
    # and we don't know which one will get the error.
    resource_busy_count = 0

    async def do_send_all_count_resourcebusy() -> None:
        nonlocal resource_busy_count
        try:
            await do_send_all(b"xxx")
        except _core.BusyResourceError:
            resource_busy_count += 1

    async with _core.open_nursery() as nursery:
        nursery.start_soon(do_send_all_count_resourcebusy)
        nursery.start_soon(do_send_all_count_resourcebusy)

    assert resource_busy_count == 1

    with assert_checkpoints():
        await mss.aclose()

    assert await mss.get_data() == b"xxx"
    assert await mss.get_data() == b""
    with pytest.raises(_core.ClosedResourceError):
        await do_send_all(b"---")

    # hooks

    assert mss.send_all_hook is None
    assert mss.wait_send_all_might_not_block_hook is None
    assert mss.close_hook is None

    record = []

    async def send_all_hook() -> None:
        # hook runs after send_all does its work (can pull data out)
        assert mss2.get_data_nowait() == b"abc"
        record.append("send_all_hook")

    async def wait_send_all_might_not_block_hook() -> None:
        record.append("wait_send_all_might_not_block_hook")

    def close_hook() -> None:
        record.append("close_hook")

    mss2 = MemorySendStream(
        send_all_hook,
        wait_send_all_might_not_block_hook,
        close_hook,
    )

    assert mss2.send_all_hook is send_all_hook
    assert mss2.wait_send_all_might_not_block_hook is wait_send_all_might_not_block_hook
    assert mss2.close_hook is close_hook

    await mss2.send_all(b"abc")
    await mss2.wait_send_all_might_not_block()
    await aclose_forcefully(mss2)
    mss2.close()

    assert record == [
        "send_all_hook",
        "wait_send_all_might_not_block_hook",
        "close_hook",
        "close_hook",
    ]


async def test_MemoryReceiveStream() -> None:
    mrs = MemoryReceiveStream()

    async def do_receive_some(max_bytes: int | None) -> bytes:
        with assert_checkpoints():
            return await mrs.receive_some(max_bytes)

    mrs.put_data(b"abc")
    assert await do_receive_some(1) == b"a"
    assert await do_receive_some(10) == b"bc"
    mrs.put_data(b"abc")
    assert await do_receive_some(None) == b"abc"

    with RaisesGroup(_core.BusyResourceError):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(do_receive_some, 10)
            nursery.start_soon(do_receive_some, 10)

    assert mrs.receive_some_hook is None

    mrs.put_data(b"def")
    mrs.put_eof()
    mrs.put_eof()

    assert await do_receive_some(10) == b"def"
    assert await do_receive_some(10) == b""
    assert await do_receive_some(10) == b""

    with pytest.raises(_core.ClosedResourceError):
        mrs.put_data(b"---")

    async def receive_some_hook() -> None:
        mrs2.put_data(b"xxx")

    record = []

    def close_hook() -> None:
        record.append("closed")

    mrs2 = MemoryReceiveStream(receive_some_hook, close_hook)
    assert mrs2.receive_some_hook is receive_some_hook
    assert mrs2.close_hook is close_hook

    mrs2.put_data(b"yyy")
    assert await mrs2.receive_some(10) == b"yyyxxx"
    assert await mrs2.receive_some(10) == b"xxx"
    assert await mrs2.receive_some(10) == b"xxx"

    mrs2.put_data(b"zzz")
    mrs2.receive_some_hook = None
    assert await mrs2.receive_some(10) == b"zzz"

    mrs2.put_data(b"lost on close")
    with assert_checkpoints():
        await mrs2.aclose()
    assert record == ["closed"]

    with pytest.raises(_core.ClosedResourceError):
        await mrs2.receive_some(10)


async def test_MemoryRecvStream_closing() -> None:
    mrs = MemoryReceiveStream()
    # close with no pending data
    mrs.close()
    with pytest.raises(_core.ClosedResourceError):
        assert await mrs.receive_some(10) == b""
    # repeated closes ok
    mrs.close()
    # put_data now fails
    with pytest.raises(_core.ClosedResourceError):
        mrs.put_data(b"123")

    mrs2 = MemoryReceiveStream()
    # close with pending data
    mrs2.put_data(b"xyz")
    mrs2.close()
    with pytest.raises(_core.ClosedResourceError):
        await mrs2.receive_some(10)


async def test_memory_stream_pump() -> None:
    mss = MemorySendStream()
    mrs = MemoryReceiveStream()

    # no-op if no data present
    memory_stream_pump(mss, mrs)

    await mss.send_all(b"123")
    memory_stream_pump(mss, mrs)
    assert await mrs.receive_some(10) == b"123"

    await mss.send_all(b"456")
    assert memory_stream_pump(mss, mrs, max_bytes=1)
    assert await mrs.receive_some(10) == b"4"
    assert memory_stream_pump(mss, mrs, max_bytes=1)
    assert memory_stream_pump(mss, mrs, max_bytes=1)
    assert not memory_stream_pump(mss, mrs, max_bytes=1)
    assert await mrs.receive_some(10) == b"56"

    mss.close()
    memory_stream_pump(mss, mrs)
    assert await mrs.receive_some(10) == b""


async def test_memory_stream_one_way_pair() -> None:
    s, r = memory_stream_one_way_pair()
    assert s.send_all_hook is not None
    assert s.wait_send_all_might_not_block_hook is None
    assert s.close_hook is not None
    assert r.receive_some_hook is None
    await s.send_all(b"123")
    assert await r.receive_some(10) == b"123"

    async def receiver(expected: bytes) -> None:
        assert await r.receive_some(10) == expected

    # This fails if we pump on r.receive_some_hook; we need to pump on s.send_all_hook
    async with _core.open_nursery() as nursery:
        nursery.start_soon(receiver, b"abc")
        await wait_all_tasks_blocked()
        await s.send_all(b"abc")

    # And this fails if we don't pump from close_hook
    async with _core.open_nursery() as nursery:
        nursery.start_soon(receiver, b"")
        await wait_all_tasks_blocked()
        await s.aclose()

    s, r = memory_stream_one_way_pair()

    async with _core.open_nursery() as nursery:
        nursery.start_soon(receiver, b"")
        await wait_all_tasks_blocked()
        s.close()

    s, r = memory_stream_one_way_pair()

    old = s.send_all_hook
    s.send_all_hook = None
    await s.send_all(b"456")

    async def cancel_after_idle(nursery: Nursery) -> None:
        await wait_all_tasks_blocked()
        nursery.cancel_scope.cancel()

    async def check_for_cancel() -> None:
        with pytest.raises(_core.Cancelled):
            # This should block forever... or until cancelled. Even though we
            # sent some data on the send stream.
            await r.receive_some(10)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(cancel_after_idle, nursery)
        nursery.start_soon(check_for_cancel)

    s.send_all_hook = old
    await s.send_all(b"789")
    assert await r.receive_some(10) == b"456789"


async def test_memory_stream_pair() -> None:
    a, b = memory_stream_pair()
    await a.send_all(b"123")
    await b.send_all(b"abc")
    assert await b.receive_some(10) == b"123"
    assert await a.receive_some(10) == b"abc"

    await a.send_eof()
    assert await b.receive_some(10) == b""

    async def sender() -> None:
        await wait_all_tasks_blocked()
        await b.send_all(b"xyz")

    async def receiver() -> None:
        assert await a.receive_some(10) == b"xyz"

    async with _core.open_nursery() as nursery:
        nursery.start_soon(receiver)
        nursery.start_soon(sender)


async def test_memory_streams_with_generic_tests() -> None:
    async def one_way_stream_maker() -> tuple[MemorySendStream, MemoryReceiveStream]:
        return memory_stream_one_way_pair()

    await check_one_way_stream(one_way_stream_maker, None)

    async def half_closeable_stream_maker() -> tuple[
        StapledStream[MemorySendStream, MemoryReceiveStream],
        StapledStream[MemorySendStream, MemoryReceiveStream],
    ]:
        return memory_stream_pair()

    await check_half_closeable_stream(half_closeable_stream_maker, None)


async def test_lockstep_streams_with_generic_tests() -> None:
    async def one_way_stream_maker() -> tuple[SendStream, ReceiveStream]:
        return lockstep_stream_one_way_pair()

    await check_one_way_stream(one_way_stream_maker, one_way_stream_maker)

    async def two_way_stream_maker() -> tuple[
        StapledStream[SendStream, ReceiveStream],
        StapledStream[SendStream, ReceiveStream],
    ]:
        return lockstep_stream_pair()

    await check_two_way_stream(two_way_stream_maker, two_way_stream_maker)


async def test_open_stream_to_socket_listener() -> None:
    async def check(listener: SocketListener) -> None:
        async with listener:
            client_stream = await open_stream_to_socket_listener(listener)
            async with client_stream:
                server_stream = await listener.accept()
                async with server_stream:
                    await client_stream.send_all(b"x")
                    assert await server_stream.receive_some(1) == b"x"

    # Listener bound to localhost
    sock = tsocket.socket()
    await sock.bind(("127.0.0.1", 0))
    sock.listen(10)
    await check(SocketListener(sock))

    # Listener bound to IPv4 wildcard (needs special handling)
    sock = tsocket.socket()
    await sock.bind(("0.0.0.0", 0))
    sock.listen(10)
    await check(SocketListener(sock))

    # true on all CI systems
    if can_bind_ipv6:  # pragma: no branch
        # Listener bound to IPv6 wildcard (needs special handling)
        sock = tsocket.socket(family=tsocket.AF_INET6)
        await sock.bind(("::", 0))
        sock.listen(10)
        await check(SocketListener(sock))

    if hasattr(tsocket, "AF_UNIX"):
        # Listener bound to Unix-domain socket
        sock = tsocket.socket(family=tsocket.AF_UNIX)
        # can't use pytest's tmpdir; if we try then macOS says "OSError:
        # AF_UNIX path too long"
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/sock"
            await sock.bind(path)
            sock.listen(10)
            await check(SocketListener(sock))


def test_trio_test() -> None:
    async def busy_kitchen(
        *,
        mock_clock: object,
        autojump_clock: object,
    ) -> None: ...  # pragma: no cover

    with pytest.raises(ValueError, match=r"^too many clocks spoil the broth!$"):
        trio_test(busy_kitchen)(
            mock_clock=MockClock(),
            autojump_clock=MockClock(autojump_threshold=0),
        )