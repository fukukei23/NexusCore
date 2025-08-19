
# === NexusCore/tools\exports\export_20250803_114325\combined_131.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\exceptions.py ===
"""Exceptions used throughout package.

This module MUST NOT try to import from anything within `pip._internal` to
operate. This is expected to be importable from any/all files within the
subpackage and, thus, should not depend on them.
"""

import configparser
import contextlib
import locale
import logging
import pathlib
import re
import sys
from itertools import chain, groupby, repeat
from typing import TYPE_CHECKING, Dict, Iterator, List, Literal, Optional, Union

from pip._vendor.packaging.requirements import InvalidRequirement
from pip._vendor.packaging.version import InvalidVersion
from pip._vendor.rich.console import Console, ConsoleOptions, RenderResult
from pip._vendor.rich.markup import escape
from pip._vendor.rich.text import Text

if TYPE_CHECKING:
    from hashlib import _Hash

    from pip._vendor.requests.models import Request, Response

    from pip._internal.metadata import BaseDistribution
    from pip._internal.req.req_install import InstallRequirement

logger = logging.getLogger(__name__)


#
# Scaffolding
#
def _is_kebab_case(s: str) -> bool:
    return re.match(r"^[a-z]+(-[a-z]+)*$", s) is not None


def _prefix_with_indent(
    s: Union[Text, str],
    console: Console,
    *,
    prefix: str,
    indent: str,
) -> Text:
    if isinstance(s, Text):
        text = s
    else:
        text = console.render_str(s)

    return console.render_str(prefix, overflow="ignore") + console.render_str(
        f"\n{indent}", overflow="ignore"
    ).join(text.split(allow_blank=True))


class PipError(Exception):
    """The base pip error."""


class DiagnosticPipError(PipError):
    """An error, that presents diagnostic information to the user.

    This contains a bunch of logic, to enable pretty presentation of our error
    messages. Each error gets a unique reference. Each error can also include
    additional context, a hint and/or a note -- which are presented with the
    main error message in a consistent style.

    This is adapted from the error output styling in `sphinx-theme-builder`.
    """

    reference: str

    def __init__(
        self,
        *,
        kind: 'Literal["error", "warning"]' = "error",
        reference: Optional[str] = None,
        message: Union[str, Text],
        context: Optional[Union[str, Text]],
        hint_stmt: Optional[Union[str, Text]],
        note_stmt: Optional[Union[str, Text]] = None,
        link: Optional[str] = None,
    ) -> None:
        # Ensure a proper reference is provided.
        if reference is None:
            assert hasattr(self, "reference"), "error reference not provided!"
            reference = self.reference
        assert _is_kebab_case(reference), "error reference must be kebab-case!"

        self.kind = kind
        self.reference = reference

        self.message = message
        self.context = context

        self.note_stmt = note_stmt
        self.hint_stmt = hint_stmt

        self.link = link

        super().__init__(f"<{self.__class__.__name__}: {self.reference}>")

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"reference={self.reference!r}, "
            f"message={self.message!r}, "
            f"context={self.context!r}, "
            f"note_stmt={self.note_stmt!r}, "
            f"hint_stmt={self.hint_stmt!r}"
            ")>"
        )

    def __rich_console__(
        self,
        console: Console,
        options: ConsoleOptions,
    ) -> RenderResult:
        colour = "red" if self.kind == "error" else "yellow"

        yield f"[{colour} bold]{self.kind}[/]: [bold]{self.reference}[/]"
        yield ""

        if not options.ascii_only:
            # Present the main message, with relevant context indented.
            if self.context is not None:
                yield _prefix_with_indent(
                    self.message,
                    console,
                    prefix=f"[{colour}]×[/] ",
                    indent=f"[{colour}]│[/] ",
                )
                yield _prefix_with_indent(
                    self.context,
                    console,
                    prefix=f"[{colour}]╰─>[/] ",
                    indent=f"[{colour}]   [/] ",
                )
            else:
                yield _prefix_with_indent(
                    self.message,
                    console,
                    prefix="[red]×[/] ",
                    indent="  ",
                )
        else:
            yield self.message
            if self.context is not None:
                yield ""
                yield self.context

        if self.note_stmt is not None or self.hint_stmt is not None:
            yield ""

        if self.note_stmt is not None:
            yield _prefix_with_indent(
                self.note_stmt,
                console,
                prefix="[magenta bold]note[/]: ",
                indent="      ",
            )
        if self.hint_stmt is not None:
            yield _prefix_with_indent(
                self.hint_stmt,
                console,
                prefix="[cyan bold]hint[/]: ",
                indent="      ",
            )

        if self.link is not None:
            yield ""
            yield f"Link: {self.link}"


#
# Actual Errors
#
class ConfigurationError(PipError):
    """General exception in configuration"""


class InstallationError(PipError):
    """General exception during installation"""


class MissingPyProjectBuildRequires(DiagnosticPipError):
    """Raised when pyproject.toml has `build-system`, but no `build-system.requires`."""

    reference = "missing-pyproject-build-system-requires"

    def __init__(self, *, package: str) -> None:
        super().__init__(
            message=f"Can not process {escape(package)}",
            context=Text(
                "This package has an invalid pyproject.toml file.\n"
                "The [build-system] table is missing the mandatory `requires` key."
            ),
            note_stmt="This is an issue with the package mentioned above, not pip.",
            hint_stmt=Text("See PEP 518 for the detailed specification."),
        )


class InvalidPyProjectBuildRequires(DiagnosticPipError):
    """Raised when pyproject.toml an invalid `build-system.requires`."""

    reference = "invalid-pyproject-build-system-requires"

    def __init__(self, *, package: str, reason: str) -> None:
        super().__init__(
            message=f"Can not process {escape(package)}",
            context=Text(
                "This package has an invalid `build-system.requires` key in "
                f"pyproject.toml.\n{reason}"
            ),
            note_stmt="This is an issue with the package mentioned above, not pip.",
            hint_stmt=Text("See PEP 518 for the detailed specification."),
        )


class NoneMetadataError(PipError):
    """Raised when accessing a Distribution's "METADATA" or "PKG-INFO".

    This signifies an inconsistency, when the Distribution claims to have
    the metadata file (if not, raise ``FileNotFoundError`` instead), but is
    not actually able to produce its content. This may be due to permission
    errors.
    """

    def __init__(
        self,
        dist: "BaseDistribution",
        metadata_name: str,
    ) -> None:
        """
        :param dist: A Distribution object.
        :param metadata_name: The name of the metadata being accessed
            (can be "METADATA" or "PKG-INFO").
        """
        self.dist = dist
        self.metadata_name = metadata_name

    def __str__(self) -> str:
        # Use `dist` in the error message because its stringification
        # includes more information, like the version and location.
        return f"None {self.metadata_name} metadata found for distribution: {self.dist}"


class UserInstallationInvalid(InstallationError):
    """A --user install is requested on an environment without user site."""

    def __str__(self) -> str:
        return "User base directory is not specified"


class InvalidSchemeCombination(InstallationError):
    def __str__(self) -> str:
        before = ", ".join(str(a) for a in self.args[:-1])
        return f"Cannot set {before} and {self.args[-1]} together"


class DistributionNotFound(InstallationError):
    """Raised when a distribution cannot be found to satisfy a requirement"""


class RequirementsFileParseError(InstallationError):
    """Raised when a general error occurs parsing a requirements file line."""


class BestVersionAlreadyInstalled(PipError):
    """Raised when the most up-to-date version of a package is already
    installed."""


class BadCommand(PipError):
    """Raised when virtualenv or a command is not found"""


class CommandError(PipError):
    """Raised when there is an error in command-line arguments"""


class PreviousBuildDirError(PipError):
    """Raised when there's a previous conflicting build directory"""


class NetworkConnectionError(PipError):
    """HTTP connection error"""

    def __init__(
        self,
        error_msg: str,
        response: Optional["Response"] = None,
        request: Optional["Request"] = None,
    ) -> None:
        """
        Initialize NetworkConnectionError with  `request` and `response`
        objects.
        """
        self.response = response
        self.request = request
        self.error_msg = error_msg
        if (
            self.response is not None
            and not self.request
            and hasattr(response, "request")
        ):
            self.request = self.response.request
        super().__init__(error_msg, response, request)

    def __str__(self) -> str:
        return str(self.error_msg)


class InvalidWheelFilename(InstallationError):
    """Invalid wheel filename."""


class UnsupportedWheel(InstallationError):
    """Unsupported wheel."""


class InvalidWheel(InstallationError):
    """Invalid (e.g. corrupt) wheel."""

    def __init__(self, location: str, name: str):
        self.location = location
        self.name = name

    def __str__(self) -> str:
        return f"Wheel '{self.name}' located at {self.location} is invalid."


class MetadataInconsistent(InstallationError):
    """Built metadata contains inconsistent information.

    This is raised when the metadata contains values (e.g. name and version)
    that do not match the information previously obtained from sdist filename,
    user-supplied ``#egg=`` value, or an install requirement name.
    """

    def __init__(
        self, ireq: "InstallRequirement", field: str, f_val: str, m_val: str
    ) -> None:
        self.ireq = ireq
        self.field = field
        self.f_val = f_val
        self.m_val = m_val

    def __str__(self) -> str:
        return (
            f"Requested {self.ireq} has inconsistent {self.field}: "
            f"expected {self.f_val!r}, but metadata has {self.m_val!r}"
        )


class MetadataInvalid(InstallationError):
    """Metadata is invalid."""

    def __init__(self, ireq: "InstallRequirement", error: str) -> None:
        self.ireq = ireq
        self.error = error

    def __str__(self) -> str:
        return f"Requested {self.ireq} has invalid metadata: {self.error}"


class InstallationSubprocessError(DiagnosticPipError, InstallationError):
    """A subprocess call failed."""

    reference = "subprocess-exited-with-error"

    def __init__(
        self,
        *,
        command_description: str,
        exit_code: int,
        output_lines: Optional[List[str]],
    ) -> None:
        if output_lines is None:
            output_prompt = Text("See above for output.")
        else:
            output_prompt = (
                Text.from_markup(f"[red][{len(output_lines)} lines of output][/]\n")
                + Text("".join(output_lines))
                + Text.from_markup(R"[red]\[end of output][/]")
            )

        super().__init__(
            message=(
                f"[green]{escape(command_description)}[/] did not run successfully.\n"
                f"exit code: {exit_code}"
            ),
            context=output_prompt,
            hint_stmt=None,
            note_stmt=(
                "This error originates from a subprocess, and is likely not a "
                "problem with pip."
            ),
        )

        self.command_description = command_description
        self.exit_code = exit_code

    def __str__(self) -> str:
        return f"{self.command_description} exited with {self.exit_code}"


class MetadataGenerationFailed(InstallationSubprocessError, InstallationError):
    reference = "metadata-generation-failed"

    def __init__(
        self,
        *,
        package_details: str,
    ) -> None:
        super(InstallationSubprocessError, self).__init__(
            message="Encountered error while generating package metadata.",
            context=escape(package_details),
            hint_stmt="See above for details.",
            note_stmt="This is an issue with the package mentioned above, not pip.",
        )

    def __str__(self) -> str:
        return "metadata generation failed"


class HashErrors(InstallationError):
    """Multiple HashError instances rolled into one for reporting"""

    def __init__(self) -> None:
        self.errors: List[HashError] = []

    def append(self, error: "HashError") -> None:
        self.errors.append(error)

    def __str__(self) -> str:
        lines = []
        self.errors.sort(key=lambda e: e.order)
        for cls, errors_of_cls in groupby(self.errors, lambda e: e.__class__):
            lines.append(cls.head)
            lines.extend(e.body() for e in errors_of_cls)
        if lines:
            return "\n".join(lines)
        return ""

    def __bool__(self) -> bool:
        return bool(self.errors)


class HashError(InstallationError):
    """
    A failure to verify a package against known-good hashes

    :cvar order: An int sorting hash exception classes by difficulty of
        recovery (lower being harder), so the user doesn't bother fretting
        about unpinned packages when he has deeper issues, like VCS
        dependencies, to deal with. Also keeps error reports in a
        deterministic order.
    :cvar head: A section heading for display above potentially many
        exceptions of this kind
    :ivar req: The InstallRequirement that triggered this error. This is
        pasted on after the exception is instantiated, because it's not
        typically available earlier.

    """

    req: Optional["InstallRequirement"] = None
    head = ""
    order: int = -1

    def body(self) -> str:
        """Return a summary of me for display under the heading.

        This default implementation simply prints a description of the
        triggering requirement.

        :param req: The InstallRequirement that provoked this error, with
            its link already populated by the resolver's _populate_link().

        """
        return f"    {self._requirement_name()}"

    def __str__(self) -> str:
        return f"{self.head}\n{self.body()}"

    def _requirement_name(self) -> str:
        """Return a description of the requirement that triggered me.

        This default implementation returns long description of the req, with
        line numbers

        """
        return str(self.req) if self.req else "unknown package"


class VcsHashUnsupported(HashError):
    """A hash was provided for a version-control-system-based requirement, but
    we don't have a method for hashing those."""

    order = 0
    head = (
        "Can't verify hashes for these requirements because we don't "
        "have a way to hash version control repositories:"
    )


class DirectoryUrlHashUnsupported(HashError):
    """A hash was provided for a version-control-system-based requirement, but
    we don't have a method for hashing those."""

    order = 1
    head = (
        "Can't verify hashes for these file:// requirements because they "
        "point to directories:"
    )


class HashMissing(HashError):
    """A hash was needed for a requirement but is absent."""

    order = 2
    head = (
        "Hashes are required in --require-hashes mode, but they are "
        "missing from some requirements. Here is a list of those "
        "requirements along with the hashes their downloaded archives "
        "actually had. Add lines like these to your requirements files to "
        "prevent tampering. (If you did not enable --require-hashes "
        "manually, note that it turns on automatically when any package "
        "has a hash.)"
    )

    def __init__(self, gotten_hash: str) -> None:
        """
        :param gotten_hash: The hash of the (possibly malicious) archive we
            just downloaded
        """
        self.gotten_hash = gotten_hash

    def body(self) -> str:
        # Dodge circular import.
        from pip._internal.utils.hashes import FAVORITE_HASH

        package = None
        if self.req:
            # In the case of URL-based requirements, display the original URL
            # seen in the requirements file rather than the package name,
            # so the output can be directly copied into the requirements file.
            package = (
                self.req.original_link
                if self.req.is_direct
                # In case someone feeds something downright stupid
                # to InstallRequirement's constructor.
                else getattr(self.req, "req", None)
            )
        return "    {} --hash={}:{}".format(
            package or "unknown package", FAVORITE_HASH, self.gotten_hash
        )


class HashUnpinned(HashError):
    """A requirement had a hash specified but was not pinned to a specific
    version."""

    order = 3
    head = (
        "In --require-hashes mode, all requirements must have their "
        "versions pinned with ==. These do not:"
    )


class HashMismatch(HashError):
    """
    Distribution file hash values don't match.

    :ivar package_name: The name of the package that triggered the hash
        mismatch. Feel free to write to this after the exception is raise to
        improve its error message.

    """

    order = 4
    head = (
        "THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS "
        "FILE. If you have updated the package versions, please update "
        "the hashes. Otherwise, examine the package contents carefully; "
        "someone may have tampered with them."
    )

    def __init__(self, allowed: Dict[str, List[str]], gots: Dict[str, "_Hash"]) -> None:
        """
        :param allowed: A dict of algorithm names pointing to lists of allowed
            hex digests
        :param gots: A dict of algorithm names pointing to hashes we
            actually got from the files under suspicion
        """
        self.allowed = allowed
        self.gots = gots

    def body(self) -> str:
        return f"    {self._requirement_name()}:\n{self._hash_comparison()}"

    def _hash_comparison(self) -> str:
        """
        Return a comparison of actual and expected hash values.

        Example::

               Expected sha256 abcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcde
                            or 123451234512345123451234512345123451234512345
                    Got        bcdefbcdefbcdefbcdefbcdefbcdefbcdefbcdefbcdef

        """

        def hash_then_or(hash_name: str) -> "chain[str]":
            # For now, all the decent hashes have 6-char names, so we can get
            # away with hard-coding space literals.
            return chain([hash_name], repeat("    or"))

        lines: List[str] = []
        for hash_name, expecteds in self.allowed.items():
            prefix = hash_then_or(hash_name)
            lines.extend((f"        Expected {next(prefix)} {e}") for e in expecteds)
            lines.append(
                f"             Got        {self.gots[hash_name].hexdigest()}\n"
            )
        return "\n".join(lines)


class UnsupportedPythonVersion(InstallationError):
    """Unsupported python version according to Requires-Python package
    metadata."""


class ConfigurationFileCouldNotBeLoaded(ConfigurationError):
    """When there are errors while loading a configuration file"""

    def __init__(
        self,
        reason: str = "could not be loaded",
        fname: Optional[str] = None,
        error: Optional[configparser.Error] = None,
    ) -> None:
        super().__init__(error)
        self.reason = reason
        self.fname = fname
        self.error = error

    def __str__(self) -> str:
        if self.fname is not None:
            message_part = f" in {self.fname}."
        else:
            assert self.error is not None
            message_part = f".\n{self.error}\n"
        return f"Configuration file {self.reason}{message_part}"


_DEFAULT_EXTERNALLY_MANAGED_ERROR = f"""\
The Python environment under {sys.prefix} is managed externally, and may not be
manipulated by the user. Please use specific tooling from the distributor of
the Python installation to interact with this environment instead.
"""


class ExternallyManagedEnvironment(DiagnosticPipError):
    """The current environment is externally managed.

    This is raised when the current environment is externally managed, as
    defined by `PEP 668`_. The ``EXTERNALLY-MANAGED`` configuration is checked
    and displayed when the error is bubbled up to the user.

    :param error: The error message read from ``EXTERNALLY-MANAGED``.
    """

    reference = "externally-managed-environment"

    def __init__(self, error: Optional[str]) -> None:
        if error is None:
            context = Text(_DEFAULT_EXTERNALLY_MANAGED_ERROR)
        else:
            context = Text(error)
        super().__init__(
            message="This environment is externally managed",
            context=context,
            note_stmt=(
                "If you believe this is a mistake, please contact your "
                "Python installation or OS distribution provider. "
                "You can override this, at the risk of breaking your Python "
                "installation or OS, by passing --break-system-packages."
            ),
            hint_stmt=Text("See PEP 668 for the detailed specification."),
        )

    @staticmethod
    def _iter_externally_managed_error_keys() -> Iterator[str]:
        # LC_MESSAGES is in POSIX, but not the C standard. The most common
        # platform that does not implement this category is Windows, where
        # using other categories for console message localization is equally
        # unreliable, so we fall back to the locale-less vendor message. This
        # can always be re-evaluated when a vendor proposes a new alternative.
        try:
            category = locale.LC_MESSAGES
        except AttributeError:
            lang: Optional[str] = None
        else:
            lang, _ = locale.getlocale(category)
        if lang is not None:
            yield f"Error-{lang}"
            for sep in ("-", "_"):
                before, found, _ = lang.partition(sep)
                if not found:
                    continue
                yield f"Error-{before}"
        yield "Error"

    @classmethod
    def from_config(
        cls,
        config: Union[pathlib.Path, str],
    ) -> "ExternallyManagedEnvironment":
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(config, encoding="utf-8")
            section = parser["externally-managed"]
            for key in cls._iter_externally_managed_error_keys():
                with contextlib.suppress(KeyError):
                    return cls(section[key])
        except KeyError:
            pass
        except (OSError, UnicodeDecodeError, configparser.ParsingError):
            from pip._internal.utils._log import VERBOSE

            exc_info = logger.isEnabledFor(VERBOSE)
            logger.warning("Failed to read %s", config, exc_info=exc_info)
        return cls(None)


class UninstallMissingRecord(DiagnosticPipError):
    reference = "uninstall-no-record-file"

    def __init__(self, *, distribution: "BaseDistribution") -> None:
        installer = distribution.installer
        if not installer or installer == "pip":
            dep = f"{distribution.raw_name}=={distribution.version}"
            hint = Text.assemble(
                "You might be able to recover from this via: ",
                (f"pip install --force-reinstall --no-deps {dep}", "green"),
            )
        else:
            hint = Text(
                f"The package was installed by {installer}. "
                "You should check if it can uninstall the package."
            )

        super().__init__(
            message=Text(f"Cannot uninstall {distribution}"),
            context=(
                "The package's contents are unknown: "
                f"no RECORD file was found for {distribution.raw_name}."
            ),
            hint_stmt=hint,
        )


class LegacyDistutilsInstall(DiagnosticPipError):
    reference = "uninstall-distutils-installed-package"

    def __init__(self, *, distribution: "BaseDistribution") -> None:
        super().__init__(
            message=Text(f"Cannot uninstall {distribution}"),
            context=(
                "It is a distutils installed project and thus we cannot accurately "
                "determine which files belong to it which would lead to only a partial "
                "uninstall."
            ),
            hint_stmt=None,
        )


class InvalidInstalledPackage(DiagnosticPipError):
    reference = "invalid-installed-package"

    def __init__(
        self,
        *,
        dist: "BaseDistribution",
        invalid_exc: Union[InvalidRequirement, InvalidVersion],
    ) -> None:
        installed_location = dist.installed_location

        if isinstance(invalid_exc, InvalidRequirement):
            invalid_type = "requirement"
        else:
            invalid_type = "version"

        super().__init__(
            message=Text(
                f"Cannot process installed package {dist} "
                + (f"in {installed_location!r} " if installed_location else "")
                + f"because it has an invalid {invalid_type}:\n{invalid_exc.args[0]}"
            ),
            context=(
                "Starting with pip 24.1, packages with invalid "
                f"{invalid_type}s can not be processed."
            ),
            hint_stmt="To proceed this package must be uninstalled.",
        )

# === NexusCore/openenv\Lib\site-packages\isapi\install.py ===
"""Installation utilities for Python ISAPI filters and extensions."""

# this code adapted from "Tomcat JK2 ISAPI redirector", part of Apache
# Created July 2004, Mark Hammond.
from __future__ import annotations

import importlib.machinery
import os
import shutil
import stat
import sys
import traceback
from collections.abc import Mapping

import pythoncom
import win32api
import winerror
from win32com.client import GetObject

_APP_INPROC = 0
_APP_OUTPROC = 1
_APP_POOLED = 2
_IIS_OBJECT = "IIS://LocalHost/W3SVC"
_IIS_SERVER = "IIsWebServer"
_IIS_WEBDIR = "IIsWebDirectory"
_IIS_WEBVIRTUALDIR = "IIsWebVirtualDir"
_IIS_FILTERS = "IIsFilters"
_IIS_FILTER = "IIsFilter"

_DEFAULT_SERVER_NAME = "Default Web Site"
_DEFAULT_HEADERS = "X-Powered-By: Python"
_DEFAULT_PROTECTION = _APP_POOLED

# Default is for 'execute' only access - ie, only the extension
# can be used.  This can be overridden via your install script.
_DEFAULT_ACCESS_EXECUTE = True
_DEFAULT_ACCESS_READ = False
_DEFAULT_ACCESS_WRITE = False
_DEFAULT_ACCESS_SCRIPT = False
_DEFAULT_CONTENT_INDEXED = False
_DEFAULT_ENABLE_DIR_BROWSING = False
_DEFAULT_ENABLE_DEFAULT_DOC = False

this_dir = os.path.abspath(os.path.dirname(__file__))


class FilterParameters:
    Name = None
    Description = None
    Path = None
    Server = None
    # Params that control if/how AddExtensionFile is called.
    AddExtensionFile = True
    AddExtensionFile_Enabled = True
    AddExtensionFile_GroupID = None  # defaults to Name
    AddExtensionFile_CanDelete = True
    AddExtensionFile_Description = None  # defaults to Description.

    def __init__(self, **kw):
        self.__dict__.update(kw)


class VirtualDirParameters:
    Name = None  # Must be provided.
    Description = None  # defaults to Name
    AppProtection = _DEFAULT_PROTECTION
    Headers = _DEFAULT_HEADERS
    Path = None  # defaults to WWW root.
    Type = _IIS_WEBVIRTUALDIR
    AccessExecute = _DEFAULT_ACCESS_EXECUTE
    AccessRead = _DEFAULT_ACCESS_READ
    AccessWrite = _DEFAULT_ACCESS_WRITE
    AccessScript = _DEFAULT_ACCESS_SCRIPT
    ContentIndexed = _DEFAULT_CONTENT_INDEXED
    EnableDirBrowsing = _DEFAULT_ENABLE_DIR_BROWSING
    EnableDefaultDoc = _DEFAULT_ENABLE_DEFAULT_DOC
    DefaultDoc = None  # Only set in IIS if not None
    ScriptMaps: list[ScriptMapParams] = []
    ScriptMapUpdate = "end"  # can be 'start', 'end', 'replace'
    Server = None

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def is_root(self):
        "This virtual directory is a root directory if parent and name are blank"
        parent, name = self.split_path()
        return not parent and not name

    def split_path(self):
        return split_path(self.Name)


class ScriptMapParams:
    Extension = None
    Module = None
    Flags = 5
    Verbs = ""
    # Params that control if/how AddExtensionFile is called.
    AddExtensionFile = True
    AddExtensionFile_Enabled = True
    AddExtensionFile_GroupID = None  # defaults to Name
    AddExtensionFile_CanDelete = True
    AddExtensionFile_Description = None  # defaults to Description.

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __str__(self):
        "Format this parameter suitable for IIS"
        items = [self.Extension, self.Module, self.Flags]
        # IIS gets upset if there is a trailing verb comma, but no verbs
        if self.Verbs:
            items.append(self.Verbs)
        items = [str(item) for item in items]
        return ",".join(items)


class ISAPIParameters:
    ServerName = _DEFAULT_SERVER_NAME
    # Description = None
    Filters: list[FilterParameters] = []
    VirtualDirs: list[VirtualDirParameters] = []

    def __init__(self, **kw):
        self.__dict__.update(kw)


verbose = 1  # The level - 0 is quiet.


def log(level, what):
    if verbose >= level:
        print(what)


# Convert an ADSI COM exception to the Win32 error code embedded in it.
def _GetWin32ErrorCode(com_exc):
    hr = com_exc.hresult
    # If we have more details in the 'excepinfo' struct, use it.
    if com_exc.excepinfo:
        hr = com_exc.excepinfo[-1]
    if winerror.HRESULT_FACILITY(hr) != winerror.FACILITY_WIN32:
        raise
    return winerror.SCODE_CODE(hr)


class InstallationError(Exception):
    pass


class ItemNotFound(InstallationError):
    pass


class ConfigurationError(InstallationError):
    pass


def FindPath(options, server, name):
    if name.lower().startswith("iis://"):
        return name
    else:
        if name and name[0] != "/":
            name = "/" + name
        return FindWebServer(options, server) + "/ROOT" + name


def LocateWebServerPath(description):
    """
    Find an IIS web server whose name or comment matches the provided
    description (case-insensitive).

    >>> LocateWebServerPath('Default Web Site') # doctest: +SKIP

    or

    >>> LocateWebServerPath('1') #doctest: +SKIP
    """
    assert len(description) >= 1, "Server name or comment is required"
    iis = GetObject(_IIS_OBJECT)
    description = description.lower().strip()
    for site in iis:
        # Name is generally a number, but no need to assume that.
        site_attributes = [
            getattr(site, attr, "").lower().strip()
            for attr in ("Name", "ServerComment")
        ]
        if description in site_attributes:
            return site.AdsPath
    msg = "No web sites match the description '%s'" % description
    raise ItemNotFound(msg)


def GetWebServer(description=None):
    """
    Load the web server instance (COM object) for a given instance
    or description.
    If None is specified, the default website is retrieved (indicated
    by the identifier 1.
    """
    description = description or "1"
    path = LocateWebServerPath(description)
    server = LoadWebServer(path)
    return server


def LoadWebServer(path):
    try:
        server = GetObject(path)
    except pythoncom.com_error as exc:
        msg = exc.strerror
        if exc.excepinfo and exc.excepinfo[2]:
            msg = exc.excepinfo[2]
        msg = f"WebServer {path}: {msg}"
        raise ItemNotFound(msg)
    return server


def FindWebServer(options, server_desc):
    """
    Legacy function to allow options to define a .server property
    to override the other parameter.  Use GetWebServer instead.
    """
    # options takes precedence
    server_desc = options.server or server_desc
    # make sure server_desc is unicode (could be mbcs if passed in
    #  sys.argv).
    if server_desc and not isinstance(server_desc, str):
        server_desc = server_desc.decode("mbcs")

    # get the server (if server_desc is None, the default site is acquired)
    server = GetWebServer(server_desc)
    return server.adsPath


def split_path(path):
    """
    Get the parent path and basename.

    >>> split_path('/')
    ['', '']

    >>> split_path('')
    ['', '']

    >>> split_path('foo')
    ['', 'foo']

    >>> split_path('/foo')
    ['', 'foo']

    >>> split_path('/foo/bar')
    ['/foo', 'bar']

    >>> split_path('foo/bar')
    ['/foo', 'bar']
    """

    if not path.startswith("/"):
        path = "/" + path
    return path.rsplit("/", 1)


def _CreateDirectory(iis_dir, name, params):
    # We used to go to lengths to keep an existing virtual directory
    # in place.  However, in some cases the existing directories got
    # into a bad state, and an update failed to get them working.
    # So we nuke it first.  If this is a problem, we could consider adding
    # a --keep-existing option.
    try:
        # Also seen the Class change to a generic IISObject - so nuke
        # *any* existing object, regardless of Class
        assert name.strip("/"), "mustn't delete the root!"
        iis_dir.Delete("", name)
        log(2, f"Deleted old directory '{name}'")
    except pythoncom.com_error:
        pass

    newDir = iis_dir.Create(params.Type, name)
    log(2, f"Creating new directory '{name}' in {iis_dir.Name}...")

    friendly = params.Description or params.Name
    newDir.AppFriendlyName = friendly

    # Note that the new directory won't be visible in the IIS UI
    # unless the directory exists on the filesystem.
    try:
        path = params.Path or iis_dir.Path
        newDir.Path = path
    except AttributeError:
        # If params.Type is IIS_WEBDIRECTORY, an exception is thrown
        pass
    newDir.AppCreate2(params.AppProtection)
    # XXX - note that these Headers only work in IIS6 and earlier.  IIS7
    # only supports them on the w3svc node - not even on individial sites,
    # let alone individual extensions in the site!
    if params.Headers:
        newDir.HttpCustomHeaders = params.Headers

    log(2, "Setting directory options...")
    newDir.AccessExecute = params.AccessExecute
    newDir.AccessRead = params.AccessRead
    newDir.AccessWrite = params.AccessWrite
    newDir.AccessScript = params.AccessScript
    newDir.ContentIndexed = params.ContentIndexed
    newDir.EnableDirBrowsing = params.EnableDirBrowsing
    newDir.EnableDefaultDoc = params.EnableDefaultDoc
    if params.DefaultDoc is not None:
        newDir.DefaultDoc = params.DefaultDoc
    newDir.SetInfo()
    return newDir


def CreateDirectory(params, options):
    _CallHook(params, "PreInstall", options)
    if not params.Name:
        raise ConfigurationError("No Name param")
    parent, name = params.split_path()
    target_dir = GetObject(FindPath(options, params.Server, parent))

    if not params.is_root():
        target_dir = _CreateDirectory(target_dir, name, params)

    AssignScriptMaps(params.ScriptMaps, target_dir, params.ScriptMapUpdate)

    _CallHook(params, "PostInstall", options, target_dir)
    log(1, f"Configured Virtual Directory: {params.Name}")
    return target_dir


def AssignScriptMaps(script_maps, target, update="replace"):
    """Updates IIS with the supplied script map information.

    script_maps is a list of ScriptMapParameter objects

    target is an IIS Virtual Directory to assign the script maps to

    update is a string indicating how to update the maps, one of  ('start',
    'end', or 'replace')
    """
    # determine which function to use to assign script maps
    script_map_func = "_AssignScriptMaps" + update.capitalize()
    try:
        script_map_func = eval(script_map_func)
    except NameError:
        msg = "Unknown ScriptMapUpdate option '%s'" % update
        raise ConfigurationError(msg)
    # use the str method to format the script maps for IIS
    script_maps = [str(s) for s in script_maps]
    # call the correct function
    script_map_func(target, script_maps)
    target.SetInfo()


def get_unique_items(sequence, reference):
    "Return items in sequence that can't be found in reference."
    return tuple([item for item in sequence if item not in reference])


def _AssignScriptMapsReplace(target, script_maps):
    target.ScriptMaps = script_maps


def _AssignScriptMapsEnd(target, script_maps):
    unique_new_maps = get_unique_items(script_maps, target.ScriptMaps)
    target.ScriptMaps += unique_new_maps


def _AssignScriptMapsStart(target, script_maps):
    unique_new_maps = get_unique_items(script_maps, target.ScriptMaps)
    target.ScriptMaps = unique_new_maps + target.ScriptMaps


def CreateISAPIFilter(filterParams, options):
    server = FindWebServer(options, filterParams.Server)
    _CallHook(filterParams, "PreInstall", options)
    try:
        filters = GetObject(server + "/Filters")
    except pythoncom.com_error as exc:
        # Brand new sites don't have the '/Filters' collection - create it.
        # Any errors other than 'not found' we shouldn't ignore.
        if (
            winerror.HRESULT_FACILITY(exc.hresult) != winerror.FACILITY_WIN32
            or winerror.HRESULT_CODE(exc.hresult) != winerror.ERROR_PATH_NOT_FOUND
        ):
            raise
        server_ob = GetObject(server)
        filters = server_ob.Create(_IIS_FILTERS, "Filters")
        filters.FilterLoadOrder = ""
        filters.SetInfo()

    # As for VirtualDir, delete an existing one.
    assert filterParams.Name.strip("/"), "mustn't delete the root!"
    try:
        filters.Delete(_IIS_FILTER, filterParams.Name)
        log(2, f"Deleted old filter '{filterParams.Name}'")
    except pythoncom.com_error:
        pass
    newFilter = filters.Create(_IIS_FILTER, filterParams.Name)
    log(2, "Created new ISAPI filter...")
    assert os.path.isfile(filterParams.Path)
    newFilter.FilterPath = filterParams.Path
    newFilter.FilterDescription = filterParams.Description
    newFilter.SetInfo()
    load_order = [b.strip() for b in filters.FilterLoadOrder.split(",") if b]
    if filterParams.Name not in load_order:
        load_order.append(filterParams.Name)
        filters.FilterLoadOrder = ",".join(load_order)
        filters.SetInfo()
    _CallHook(filterParams, "PostInstall", options, newFilter)
    log(1, f"Configured Filter: {filterParams.Name}")
    return newFilter


def DeleteISAPIFilter(filterParams, options):
    _CallHook(filterParams, "PreRemove", options)
    server = FindWebServer(options, filterParams.Server)
    ob_path = server + "/Filters"
    try:
        filters = GetObject(ob_path)
    except pythoncom.com_error as details:
        # failure to open the filters just means a totally clean IIS install
        # (IIS5 at least has no 'Filters' key when freshly installed).
        log(2, f"ISAPI filter path '{ob_path}' did not exist.")
        return
    try:
        assert filterParams.Name.strip("/"), "mustn't delete the root!"
        filters.Delete(_IIS_FILTER, filterParams.Name)
        log(2, f"Deleted ISAPI filter '{filterParams.Name}'")
    except pythoncom.com_error as details:
        rc = _GetWin32ErrorCode(details)
        if rc != winerror.ERROR_PATH_NOT_FOUND:
            raise
        log(2, f"ISAPI filter '{filterParams.Name}' did not exist.")
    # Remove from the load order
    load_order = [b.strip() for b in filters.FilterLoadOrder.split(",") if b]
    if filterParams.Name in load_order:
        load_order.remove(filterParams.Name)
        filters.FilterLoadOrder = ",".join(load_order)
        filters.SetInfo()
    _CallHook(filterParams, "PostRemove", options)
    log(1, f"Deleted Filter: {filterParams.Name}")


def _AddExtensionFile(module, def_groupid, def_desc, params, options):
    group_id = params.AddExtensionFile_GroupID or def_groupid
    desc = params.AddExtensionFile_Description or def_desc
    try:
        ob = GetObject(_IIS_OBJECT)
        ob.AddExtensionFile(
            module,
            params.AddExtensionFile_Enabled,
            group_id,
            params.AddExtensionFile_CanDelete,
            desc,
        )
        log(2, f"Added extension file '{module}' ({desc})")
    except (pythoncom.com_error, AttributeError) as details:
        # IIS5 always fails.  Probably should upgrade this to
        # complain more loudly if IIS6 fails.
        log(2, f"Failed to add extension file '{module}': {details}")


def AddExtensionFiles(params, options):
    """Register the modules used by the filters/extensions as a trusted
    'extension module' - required by the default IIS6 security settings."""
    # Add each module only once.
    added = {}
    for vd in params.VirtualDirs:
        for smp in vd.ScriptMaps:
            if smp.Module not in added and smp.AddExtensionFile:
                _AddExtensionFile(smp.Module, vd.Name, vd.Description, smp, options)
                added[smp.Module] = True

    for fd in params.Filters:
        if fd.Path not in added and fd.AddExtensionFile:
            _AddExtensionFile(fd.Path, fd.Name, fd.Description, fd, options)
            added[fd.Path] = True


def _DeleteExtensionFileRecord(module, options):
    try:
        ob = GetObject(_IIS_OBJECT)
        ob.DeleteExtensionFileRecord(module)
        log(2, "Deleted extension file record for '%s'" % module)
    except (pythoncom.com_error, AttributeError) as details:
        log(2, f"Failed to remove extension file '{module}': {details}")


def DeleteExtensionFileRecords(params, options):
    deleted = {}  # only remove each .dll once.
    for vd in params.VirtualDirs:
        for smp in vd.ScriptMaps:
            if smp.Module not in deleted and smp.AddExtensionFile:
                _DeleteExtensionFileRecord(smp.Module, options)
                deleted[smp.Module] = True

    for filter_def in params.Filters:
        if filter_def.Path not in deleted and filter_def.AddExtensionFile:
            _DeleteExtensionFileRecord(filter_def.Path, options)
            deleted[filter_def.Path] = True


def CheckLoaderModule(dll_name):
    suffix = "_d" if "_d.pyd" in importlib.machinery.EXTENSION_SUFFIXES else ""
    template = os.path.join(this_dir, "PyISAPI_loader" + suffix + ".dll")
    if not os.path.isfile(template):
        raise ConfigurationError(f"Template loader '{template}' does not exist")
    # We can't do a simple "is newer" check, as the DLL is specific to the
    # Python version.  So we check the date-time and size are identical,
    # and skip the copy in that case.
    src_stat = os.stat(template)
    try:
        dest_stat = os.stat(dll_name)
    except OSError:
        same = 0
    else:
        same = (
            src_stat[stat.ST_SIZE] == dest_stat[stat.ST_SIZE]
            and src_stat[stat.ST_MTIME] == dest_stat[stat.ST_MTIME]
        )
    if not same:
        log(2, f"Updating {template}->{dll_name}")
        shutil.copyfile(template, dll_name)
        shutil.copystat(template, dll_name)
    else:
        log(2, f"{dll_name} is up to date.")


def _CallHook(ob, hook_name, options, *extra_args):
    func = getattr(ob, hook_name, None)
    if func is not None:
        args = (ob, options) + extra_args
        func(*args)


def Install(params, options):
    _CallHook(params, "PreInstall", options)
    for vd in params.VirtualDirs:
        CreateDirectory(vd, options)

    for filter_def in params.Filters:
        CreateISAPIFilter(filter_def, options)

    AddExtensionFiles(params, options)

    _CallHook(params, "PostInstall", options)


def RemoveDirectory(params, options):
    if params.is_root():
        return
    try:
        directory = GetObject(FindPath(options, params.Server, params.Name))
    except pythoncom.com_error as details:
        rc = _GetWin32ErrorCode(details)
        if rc != winerror.ERROR_PATH_NOT_FOUND:
            raise
        log(2, "VirtualDirectory '%s' did not exist" % params.Name)
        directory = None
    if directory is not None:
        # Be robust should IIS get upset about unloading.
        try:
            directory.AppUnLoad()
        except:
            exc_val = sys.exc_info()[1]
            log(2, f"AppUnLoad() for {params.Name} failed: {exc_val}")
        # Continue trying to delete it.
        try:
            parent = GetObject(directory.Parent)
            parent.Delete(directory.Class, directory.Name)
            log(1, f"Deleted Virtual Directory: {params.Name}")
        except:
            exc_val = sys.exc_info()[1]
            log(1, f"Failed to remove directory {params.Name}: {exc_val}")


def RemoveScriptMaps(vd_params, options):
    "Remove script maps from the already installed virtual directory"
    parent, name = vd_params.split_path()
    target_dir = GetObject(FindPath(options, vd_params.Server, parent))
    installed_maps = list(target_dir.ScriptMaps)
    for _map in map(str, vd_params.ScriptMaps):
        if _map in installed_maps:
            installed_maps.remove(_map)
    target_dir.ScriptMaps = installed_maps
    target_dir.SetInfo()


def Uninstall(params, options):
    _CallHook(params, "PreRemove", options)

    DeleteExtensionFileRecords(params, options)

    for vd in params.VirtualDirs:
        _CallHook(vd, "PreRemove", options)

        RemoveDirectory(vd, options)
        if vd.is_root():
            # if this is installed to the root virtual directory, we can't delete it
            #  so remove the script maps.
            RemoveScriptMaps(vd, options)

        _CallHook(vd, "PostRemove", options)

    for filter_def in params.Filters:
        DeleteISAPIFilter(filter_def, options)
    _CallHook(params, "PostRemove", options)


# Patch up any missing module names in the params, replacing them with
# the DLL name that hosts this extension/filter.
def _PatchParamsModule(params, dll_name, file_must_exist=True):
    if file_must_exist:
        if not os.path.isfile(dll_name):
            raise ConfigurationError(f"{dll_name} does not exist")

    # Patch up all references to the DLL.
    for f in params.Filters:
        if f.Path is None:
            f.Path = dll_name
    for d in params.VirtualDirs:
        for sm in d.ScriptMaps:
            if sm.Module is None:
                sm.Module = dll_name


def GetLoaderModuleName(mod_name, check_module=None):
    # find the name of the DLL hosting us.
    # By default, this is "_{module_base_name}.dll"
    if hasattr(sys, "frozen"):
        # What to do?  The .dll knows its name, but this is likely to be
        # executed via a .exe, which does not know.
        base, ext = os.path.splitext(mod_name)
        path, base = os.path.split(base)
        # handle the common case of 'foo.exe'/'foow.exe'
        if base.endswith("w"):
            base = base[:-1]
        # For py2exe, we have '_foo.dll' as the standard pyisapi loader - but
        # 'foo.dll' is what we use (it just delegates).
        # So no leading '_' on the installed name.
        dll_name = os.path.abspath(os.path.join(path, base + ".dll"))
    else:
        base, ext = os.path.splitext(mod_name)
        path, base = os.path.split(base)
        dll_name = os.path.abspath(os.path.join(path, "_" + base + ".dll"))
    # Check we actually have it.
    if check_module is None:
        check_module = not hasattr(sys, "frozen")
    if check_module:
        CheckLoaderModule(dll_name)
    return dll_name


# Note the 'log' params to these 'builtin' args - old versions of pywin32
# didn't log at all in this function (by intent; anyone calling this was
# responsible). So existing code that calls this function with the old
# signature (ie, without a 'log' param) still gets the same behaviour as
# before...


def InstallModule(conf_module_name, params, options, log=lambda *args: None):
    "Install the extension"
    if not hasattr(sys, "frozen"):
        conf_module_name = os.path.abspath(conf_module_name)
        if not os.path.isfile(conf_module_name):
            raise ConfigurationError(f"{conf_module_name} does not exist")

    loader_dll = GetLoaderModuleName(conf_module_name)
    _PatchParamsModule(params, loader_dll)
    Install(params, options)
    log(1, "Installation complete.")


def UninstallModule(conf_module_name, params, options, log=lambda *args: None):
    "Remove the extension"
    loader_dll = GetLoaderModuleName(conf_module_name, False)
    _PatchParamsModule(params, loader_dll, False)
    Uninstall(params, options)
    log(1, "Uninstallation complete.")


standard_arguments = {
    "install": InstallModule,
    "remove": UninstallModule,
}


def build_usage(handler_map: Mapping[str, object]) -> str:
    arg_names = "|".join(handler_map)
    lines = [
        " %-10s: %s" % (arg, handler.__doc__) for arg, handler in handler_map.items()
    ]
    return f"%prog [options] [{arg_names}]\ncommands:\n" + "\n".join(lines)


def MergeStandardOptions(options, params):
    """
    Take an options object generated by the command line and merge
    the values into the IISParameters object.
    """
    pass


# We support 2 ways of extending our command-line/install support.
# * Many of the installation items allow you to specify "PreInstall",
#   "PostInstall", "PreRemove" and "PostRemove" hooks
#   All hooks are called with the 'params' object being operated on, and
#   the 'optparser' options for this session (ie, the command-line options)
#   PostInstall for VirtualDirectories and Filters both have an additional
#   param - the ADSI object just created.
# * You can pass your own option parser for us to use, and/or define a map
#   with your own custom arg handlers.  It is a map of 'arg'->function.
#   The function is called with (options, log_fn, arg).  The function's
#   docstring is used in the usage output.
def HandleCommandLine(
    params,
    argv=None,
    conf_module_name=None,
    default_arg="install",
    opt_parser=None,
    custom_arg_handlers={},
):
    """Perform installation or removal of an ISAPI filter or extension.

    This module handles standard command-line options and configuration
    information, and installs, removes or updates the configuration of an
    ISAPI filter or extension.

    You must pass your configuration information in params - all other
    arguments are optional, and allow you to configure the installation
    process.
    """
    global verbose
    from optparse import OptionParser

    argv = argv or sys.argv
    if not conf_module_name:
        conf_module_name = sys.argv[0]
        # convert to a long name so that if we were somehow registered with
        # the "short" version but unregistered with the "long" version we
        # still work (that will depend on exactly how the installer was
        # started)
        try:
            conf_module_name = win32api.GetLongPathName(conf_module_name)
        except win32api.error as exc:
            log(
                2,
                f"Couldn't determine the long name for {conf_module_name!r}: {exc}",
            )

    if opt_parser is None:
        # Build our own parser.
        parser = OptionParser(usage="")
    else:
        # The caller is providing their own filter, presumably with their
        # own options all setup.
        parser = opt_parser

    # build a usage string if we don't have one.
    if not parser.get_usage():
        all_handlers = standard_arguments.copy()
        all_handlers.update(custom_arg_handlers)
        parser.set_usage(build_usage(all_handlers))

    # allow the user to use uninstall as a synonym for remove if it wasn't
    #  defined by the custom arg handlers.
    all_handlers.setdefault("uninstall", all_handlers["remove"])

    parser.add_option(
        "-q",
        "--quiet",
        action="store_false",
        dest="verbose",
        default=True,
        help="don't print status messages to stdout",
    )
    parser.add_option(
        "-v",
        "--verbosity",
        action="count",
        dest="verbose",
        default=1,
        help="increase the verbosity of status messages",
    )
    parser.add_option(
        "",
        "--server",
        action="store",
        help="Specifies the IIS server to install/uninstall on."
        f" Default is '{_IIS_OBJECT}/1'",
    )

    (options, args) = parser.parse_args(argv[1:])
    MergeStandardOptions(options, params)
    verbose = options.verbose
    if not args:
        args = [default_arg]
    try:
        for arg in args:
            handler = all_handlers[arg]
            handler(conf_module_name, params, options, log)
    except (ItemNotFound, InstallationError) as details:
        if options.verbose > 1:
            traceback.print_exc()
        print(f"{details.__class__.__name__}: {details}")
    except KeyError:
        parser.error("Invalid arg '%s'" % arg)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\exceptions.py ===
"""Exceptions used throughout package.

This module MUST NOT try to import from anything within `pip._internal` to
operate. This is expected to be importable from any/all files within the
subpackage and, thus, should not depend on them.
"""

import configparser
import contextlib
import locale
import logging
import pathlib
import re
import sys
from itertools import chain, groupby, repeat
from typing import TYPE_CHECKING, Dict, Iterator, List, Literal, Optional, Union

from pip._vendor.packaging.requirements import InvalidRequirement
from pip._vendor.packaging.version import InvalidVersion
from pip._vendor.rich.console import Console, ConsoleOptions, RenderResult
from pip._vendor.rich.markup import escape
from pip._vendor.rich.text import Text

if TYPE_CHECKING:
    from hashlib import _Hash

    from pip._vendor.requests.models import Request, Response

    from pip._internal.metadata import BaseDistribution
    from pip._internal.req.req_install import InstallRequirement

logger = logging.getLogger(__name__)


#
# Scaffolding
#
def _is_kebab_case(s: str) -> bool:
    return re.match(r"^[a-z]+(-[a-z]+)*$", s) is not None


def _prefix_with_indent(
    s: Union[Text, str],
    console: Console,
    *,
    prefix: str,
    indent: str,
) -> Text:
    if isinstance(s, Text):
        text = s
    else:
        text = console.render_str(s)

    return console.render_str(prefix, overflow="ignore") + console.render_str(
        f"\n{indent}", overflow="ignore"
    ).join(text.split(allow_blank=True))


class PipError(Exception):
    """The base pip error."""


class DiagnosticPipError(PipError):
    """An error, that presents diagnostic information to the user.

    This contains a bunch of logic, to enable pretty presentation of our error
    messages. Each error gets a unique reference. Each error can also include
    additional context, a hint and/or a note -- which are presented with the
    main error message in a consistent style.

    This is adapted from the error output styling in `sphinx-theme-builder`.
    """

    reference: str

    def __init__(
        self,
        *,
        kind: 'Literal["error", "warning"]' = "error",
        reference: Optional[str] = None,
        message: Union[str, Text],
        context: Optional[Union[str, Text]],
        hint_stmt: Optional[Union[str, Text]],
        note_stmt: Optional[Union[str, Text]] = None,
        link: Optional[str] = None,
    ) -> None:
        # Ensure a proper reference is provided.
        if reference is None:
            assert hasattr(self, "reference"), "error reference not provided!"
            reference = self.reference
        assert _is_kebab_case(reference), "error reference must be kebab-case!"

        self.kind = kind
        self.reference = reference

        self.message = message
        self.context = context

        self.note_stmt = note_stmt
        self.hint_stmt = hint_stmt

        self.link = link

        super().__init__(f"<{self.__class__.__name__}: {self.reference}>")

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"reference={self.reference!r}, "
            f"message={self.message!r}, "
            f"context={self.context!r}, "
            f"note_stmt={self.note_stmt!r}, "
            f"hint_stmt={self.hint_stmt!r}"
            ")>"
        )

    def __rich_console__(
        self,
        console: Console,
        options: ConsoleOptions,
    ) -> RenderResult:
        colour = "red" if self.kind == "error" else "yellow"

        yield f"[{colour} bold]{self.kind}[/]: [bold]{self.reference}[/]"
        yield ""

        if not options.ascii_only:
            # Present the main message, with relevant context indented.
            if self.context is not None:
                yield _prefix_with_indent(
                    self.message,
                    console,
                    prefix=f"[{colour}]×[/] ",
                    indent=f"[{colour}]│[/] ",
                )
                yield _prefix_with_indent(
                    self.context,
                    console,
                    prefix=f"[{colour}]╰─>[/] ",
                    indent=f"[{colour}]   [/] ",
                )
            else:
                yield _prefix_with_indent(
                    self.message,
                    console,
                    prefix="[red]×[/] ",
                    indent="  ",
                )
        else:
            yield self.message
            if self.context is not None:
                yield ""
                yield self.context

        if self.note_stmt is not None or self.hint_stmt is not None:
            yield ""

        if self.note_stmt is not None:
            yield _prefix_with_indent(
                self.note_stmt,
                console,
                prefix="[magenta bold]note[/]: ",
                indent="      ",
            )
        if self.hint_stmt is not None:
            yield _prefix_with_indent(
                self.hint_stmt,
                console,
                prefix="[cyan bold]hint[/]: ",
                indent="      ",
            )

        if self.link is not None:
            yield ""
            yield f"Link: {self.link}"


#
# Actual Errors
#
class ConfigurationError(PipError):
    """General exception in configuration"""


class InstallationError(PipError):
    """General exception during installation"""


class MissingPyProjectBuildRequires(DiagnosticPipError):
    """Raised when pyproject.toml has `build-system`, but no `build-system.requires`."""

    reference = "missing-pyproject-build-system-requires"

    def __init__(self, *, package: str) -> None:
        super().__init__(
            message=f"Can not process {escape(package)}",
            context=Text(
                "This package has an invalid pyproject.toml file.\n"
                "The [build-system] table is missing the mandatory `requires` key."
            ),
            note_stmt="This is an issue with the package mentioned above, not pip.",
            hint_stmt=Text("See PEP 518 for the detailed specification."),
        )


class InvalidPyProjectBuildRequires(DiagnosticPipError):
    """Raised when pyproject.toml an invalid `build-system.requires`."""

    reference = "invalid-pyproject-build-system-requires"

    def __init__(self, *, package: str, reason: str) -> None:
        super().__init__(
            message=f"Can not process {escape(package)}",
            context=Text(
                "This package has an invalid `build-system.requires` key in "
                f"pyproject.toml.\n{reason}"
            ),
            note_stmt="This is an issue with the package mentioned above, not pip.",
            hint_stmt=Text("See PEP 518 for the detailed specification."),
        )


class NoneMetadataError(PipError):
    """Raised when accessing a Distribution's "METADATA" or "PKG-INFO".

    This signifies an inconsistency, when the Distribution claims to have
    the metadata file (if not, raise ``FileNotFoundError`` instead), but is
    not actually able to produce its content. This may be due to permission
    errors.
    """

    def __init__(
        self,
        dist: "BaseDistribution",
        metadata_name: str,
    ) -> None:
        """
        :param dist: A Distribution object.
        :param metadata_name: The name of the metadata being accessed
            (can be "METADATA" or "PKG-INFO").
        """
        self.dist = dist
        self.metadata_name = metadata_name

    def __str__(self) -> str:
        # Use `dist` in the error message because its stringification
        # includes more information, like the version and location.
        return f"None {self.metadata_name} metadata found for distribution: {self.dist}"


class UserInstallationInvalid(InstallationError):
    """A --user install is requested on an environment without user site."""

    def __str__(self) -> str:
        return "User base directory is not specified"


class InvalidSchemeCombination(InstallationError):
    def __str__(self) -> str:
        before = ", ".join(str(a) for a in self.args[:-1])
        return f"Cannot set {before} and {self.args[-1]} together"


class DistributionNotFound(InstallationError):
    """Raised when a distribution cannot be found to satisfy a requirement"""


class RequirementsFileParseError(InstallationError):
    """Raised when a general error occurs parsing a requirements file line."""


class BestVersionAlreadyInstalled(PipError):
    """Raised when the most up-to-date version of a package is already
    installed."""


class BadCommand(PipError):
    """Raised when virtualenv or a command is not found"""


class CommandError(PipError):
    """Raised when there is an error in command-line arguments"""


class PreviousBuildDirError(PipError):
    """Raised when there's a previous conflicting build directory"""


class NetworkConnectionError(PipError):
    """HTTP connection error"""

    def __init__(
        self,
        error_msg: str,
        response: Optional["Response"] = None,
        request: Optional["Request"] = None,
    ) -> None:
        """
        Initialize NetworkConnectionError with  `request` and `response`
        objects.
        """
        self.response = response
        self.request = request
        self.error_msg = error_msg
        if (
            self.response is not None
            and not self.request
            and hasattr(response, "request")
        ):
            self.request = self.response.request
        super().__init__(error_msg, response, request)

    def __str__(self) -> str:
        return str(self.error_msg)


class InvalidWheelFilename(InstallationError):
    """Invalid wheel filename."""


class UnsupportedWheel(InstallationError):
    """Unsupported wheel."""


class InvalidWheel(InstallationError):
    """Invalid (e.g. corrupt) wheel."""

    def __init__(self, location: str, name: str):
        self.location = location
        self.name = name

    def __str__(self) -> str:
        return f"Wheel '{self.name}' located at {self.location} is invalid."


class MetadataInconsistent(InstallationError):
    """Built metadata contains inconsistent information.

    This is raised when the metadata contains values (e.g. name and version)
    that do not match the information previously obtained from sdist filename,
    user-supplied ``#egg=`` value, or an install requirement name.
    """

    def __init__(
        self, ireq: "InstallRequirement", field: str, f_val: str, m_val: str
    ) -> None:
        self.ireq = ireq
        self.field = field
        self.f_val = f_val
        self.m_val = m_val

    def __str__(self) -> str:
        return (
            f"Requested {self.ireq} has inconsistent {self.field}: "
            f"expected {self.f_val!r}, but metadata has {self.m_val!r}"
        )


class MetadataInvalid(InstallationError):
    """Metadata is invalid."""

    def __init__(self, ireq: "InstallRequirement", error: str) -> None:
        self.ireq = ireq
        self.error = error

    def __str__(self) -> str:
        return f"Requested {self.ireq} has invalid metadata: {self.error}"


class InstallationSubprocessError(DiagnosticPipError, InstallationError):
    """A subprocess call failed."""

    reference = "subprocess-exited-with-error"

    def __init__(
        self,
        *,
        command_description: str,
        exit_code: int,
        output_lines: Optional[List[str]],
    ) -> None:
        if output_lines is None:
            output_prompt = Text("See above for output.")
        else:
            output_prompt = (
                Text.from_markup(f"[red][{len(output_lines)} lines of output][/]\n")
                + Text("".join(output_lines))
                + Text.from_markup(R"[red]\[end of output][/]")
            )

        super().__init__(
            message=(
                f"[green]{escape(command_description)}[/] did not run successfully.\n"
                f"exit code: {exit_code}"
            ),
            context=output_prompt,
            hint_stmt=None,
            note_stmt=(
                "This error originates from a subprocess, and is likely not a "
                "problem with pip."
            ),
        )

        self.command_description = command_description
        self.exit_code = exit_code

    def __str__(self) -> str:
        return f"{self.command_description} exited with {self.exit_code}"


class MetadataGenerationFailed(InstallationSubprocessError, InstallationError):
    reference = "metadata-generation-failed"

    def __init__(
        self,
        *,
        package_details: str,
    ) -> None:
        super(InstallationSubprocessError, self).__init__(
            message="Encountered error while generating package metadata.",
            context=escape(package_details),
            hint_stmt="See above for details.",
            note_stmt="This is an issue with the package mentioned above, not pip.",
        )

    def __str__(self) -> str:
        return "metadata generation failed"


class HashErrors(InstallationError):
    """Multiple HashError instances rolled into one for reporting"""

    def __init__(self) -> None:
        self.errors: List[HashError] = []

    def append(self, error: "HashError") -> None:
        self.errors.append(error)

    def __str__(self) -> str:
        lines = []
        self.errors.sort(key=lambda e: e.order)
        for cls, errors_of_cls in groupby(self.errors, lambda e: e.__class__):
            lines.append(cls.head)
            lines.extend(e.body() for e in errors_of_cls)
        if lines:
            return "\n".join(lines)
        return ""

    def __bool__(self) -> bool:
        return bool(self.errors)


class HashError(InstallationError):
    """
    A failure to verify a package against known-good hashes

    :cvar order: An int sorting hash exception classes by difficulty of
        recovery (lower being harder), so the user doesn't bother fretting
        about unpinned packages when he has deeper issues, like VCS
        dependencies, to deal with. Also keeps error reports in a
        deterministic order.
    :cvar head: A section heading for display above potentially many
        exceptions of this kind
    :ivar req: The InstallRequirement that triggered this error. This is
        pasted on after the exception is instantiated, because it's not
        typically available earlier.

    """

    req: Optional["InstallRequirement"] = None
    head = ""
    order: int = -1

    def body(self) -> str:
        """Return a summary of me for display under the heading.

        This default implementation simply prints a description of the
        triggering requirement.

        :param req: The InstallRequirement that provoked this error, with
            its link already populated by the resolver's _populate_link().

        """
        return f"    {self._requirement_name()}"

    def __str__(self) -> str:
        return f"{self.head}\n{self.body()}"

    def _requirement_name(self) -> str:
        """Return a description of the requirement that triggered me.

        This default implementation returns long description of the req, with
        line numbers

        """
        return str(self.req) if self.req else "unknown package"


class VcsHashUnsupported(HashError):
    """A hash was provided for a version-control-system-based requirement, but
    we don't have a method for hashing those."""

    order = 0
    head = (
        "Can't verify hashes for these requirements because we don't "
        "have a way to hash version control repositories:"
    )


class DirectoryUrlHashUnsupported(HashError):
    """A hash was provided for a version-control-system-based requirement, but
    we don't have a method for hashing those."""

    order = 1
    head = (
        "Can't verify hashes for these file:// requirements because they "
        "point to directories:"
    )


class HashMissing(HashError):
    """A hash was needed for a requirement but is absent."""

    order = 2
    head = (
        "Hashes are required in --require-hashes mode, but they are "
        "missing from some requirements. Here is a list of those "
        "requirements along with the hashes their downloaded archives "
        "actually had. Add lines like these to your requirements files to "
        "prevent tampering. (If you did not enable --require-hashes "
        "manually, note that it turns on automatically when any package "
        "has a hash.)"
    )

    def __init__(self, gotten_hash: str) -> None:
        """
        :param gotten_hash: The hash of the (possibly malicious) archive we
            just downloaded
        """
        self.gotten_hash = gotten_hash

    def body(self) -> str:
        # Dodge circular import.
        from pip._internal.utils.hashes import FAVORITE_HASH

        package = None
        if self.req:
            # In the case of URL-based requirements, display the original URL
            # seen in the requirements file rather than the package name,
            # so the output can be directly copied into the requirements file.
            package = (
                self.req.original_link
                if self.req.is_direct
                # In case someone feeds something downright stupid
                # to InstallRequirement's constructor.
                else getattr(self.req, "req", None)
            )
        return "    {} --hash={}:{}".format(
            package or "unknown package", FAVORITE_HASH, self.gotten_hash
        )


class HashUnpinned(HashError):
    """A requirement had a hash specified but was not pinned to a specific
    version."""

    order = 3
    head = (
        "In --require-hashes mode, all requirements must have their "
        "versions pinned with ==. These do not:"
    )


class HashMismatch(HashError):
    """
    Distribution file hash values don't match.

    :ivar package_name: The name of the package that triggered the hash
        mismatch. Feel free to write to this after the exception is raise to
        improve its error message.

    """

    order = 4
    head = (
        "THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS "
        "FILE. If you have updated the package versions, please update "
        "the hashes. Otherwise, examine the package contents carefully; "
        "someone may have tampered with them."
    )

    def __init__(self, allowed: Dict[str, List[str]], gots: Dict[str, "_Hash"]) -> None:
        """
        :param allowed: A dict of algorithm names pointing to lists of allowed
            hex digests
        :param gots: A dict of algorithm names pointing to hashes we
            actually got from the files under suspicion
        """
        self.allowed = allowed
        self.gots = gots

    def body(self) -> str:
        return f"    {self._requirement_name()}:\n{self._hash_comparison()}"

    def _hash_comparison(self) -> str:
        """
        Return a comparison of actual and expected hash values.

        Example::

               Expected sha256 abcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcde
                            or 123451234512345123451234512345123451234512345
                    Got        bcdefbcdefbcdefbcdefbcdefbcdefbcdefbcdefbcdef

        """

        def hash_then_or(hash_name: str) -> "chain[str]":
            # For now, all the decent hashes have 6-char names, so we can get
            # away with hard-coding space literals.
            return chain([hash_name], repeat("    or"))

        lines: List[str] = []
        for hash_name, expecteds in self.allowed.items():
            prefix = hash_then_or(hash_name)
            lines.extend((f"        Expected {next(prefix)} {e}") for e in expecteds)
            lines.append(
                f"             Got        {self.gots[hash_name].hexdigest()}\n"
            )
        return "\n".join(lines)


class UnsupportedPythonVersion(InstallationError):
    """Unsupported python version according to Requires-Python package
    metadata."""


class ConfigurationFileCouldNotBeLoaded(ConfigurationError):
    """When there are errors while loading a configuration file"""

    def __init__(
        self,
        reason: str = "could not be loaded",
        fname: Optional[str] = None,
        error: Optional[configparser.Error] = None,
    ) -> None:
        super().__init__(error)
        self.reason = reason
        self.fname = fname
        self.error = error

    def __str__(self) -> str:
        if self.fname is not None:
            message_part = f" in {self.fname}."
        else:
            assert self.error is not None
            message_part = f".\n{self.error}\n"
        return f"Configuration file {self.reason}{message_part}"


_DEFAULT_EXTERNALLY_MANAGED_ERROR = f"""\
The Python environment under {sys.prefix} is managed externally, and may not be
manipulated by the user. Please use specific tooling from the distributor of
the Python installation to interact with this environment instead.
"""


class ExternallyManagedEnvironment(DiagnosticPipError):
    """The current environment is externally managed.

    This is raised when the current environment is externally managed, as
    defined by `PEP 668`_. The ``EXTERNALLY-MANAGED`` configuration is checked
    and displayed when the error is bubbled up to the user.

    :param error: The error message read from ``EXTERNALLY-MANAGED``.
    """

    reference = "externally-managed-environment"

    def __init__(self, error: Optional[str]) -> None:
        if error is None:
            context = Text(_DEFAULT_EXTERNALLY_MANAGED_ERROR)
        else:
            context = Text(error)
        super().__init__(
            message="This environment is externally managed",
            context=context,
            note_stmt=(
                "If you believe this is a mistake, please contact your "
                "Python installation or OS distribution provider. "
                "You can override this, at the risk of breaking your Python "
                "installation or OS, by passing --break-system-packages."
            ),
            hint_stmt=Text("See PEP 668 for the detailed specification."),
        )

    @staticmethod
    def _iter_externally_managed_error_keys() -> Iterator[str]:
        # LC_MESSAGES is in POSIX, but not the C standard. The most common
        # platform that does not implement this category is Windows, where
        # using other categories for console message localization is equally
        # unreliable, so we fall back to the locale-less vendor message. This
        # can always be re-evaluated when a vendor proposes a new alternative.
        try:
            category = locale.LC_MESSAGES
        except AttributeError:
            lang: Optional[str] = None
        else:
            lang, _ = locale.getlocale(category)
        if lang is not None:
            yield f"Error-{lang}"
            for sep in ("-", "_"):
                before, found, _ = lang.partition(sep)
                if not found:
                    continue
                yield f"Error-{before}"
        yield "Error"

    @classmethod
    def from_config(
        cls,
        config: Union[pathlib.Path, str],
    ) -> "ExternallyManagedEnvironment":
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(config, encoding="utf-8")
            section = parser["externally-managed"]
            for key in cls._iter_externally_managed_error_keys():
                with contextlib.suppress(KeyError):
                    return cls(section[key])
        except KeyError:
            pass
        except (OSError, UnicodeDecodeError, configparser.ParsingError):
            from pip._internal.utils._log import VERBOSE

            exc_info = logger.isEnabledFor(VERBOSE)
            logger.warning("Failed to read %s", config, exc_info=exc_info)
        return cls(None)


class UninstallMissingRecord(DiagnosticPipError):
    reference = "uninstall-no-record-file"

    def __init__(self, *, distribution: "BaseDistribution") -> None:
        installer = distribution.installer
        if not installer or installer == "pip":
            dep = f"{distribution.raw_name}=={distribution.version}"
            hint = Text.assemble(
                "You might be able to recover from this via: ",
                (f"pip install --force-reinstall --no-deps {dep}", "green"),
            )
        else:
            hint = Text(
                f"The package was installed by {installer}. "
                "You should check if it can uninstall the package."
            )

        super().__init__(
            message=Text(f"Cannot uninstall {distribution}"),
            context=(
                "The package's contents are unknown: "
                f"no RECORD file was found for {distribution.raw_name}."
            ),
            hint_stmt=hint,
        )


class LegacyDistutilsInstall(DiagnosticPipError):
    reference = "uninstall-distutils-installed-package"

    def __init__(self, *, distribution: "BaseDistribution") -> None:
        super().__init__(
            message=Text(f"Cannot uninstall {distribution}"),
            context=(
                "It is a distutils installed project and thus we cannot accurately "
                "determine which files belong to it which would lead to only a partial "
                "uninstall."
            ),
            hint_stmt=None,
        )


class InvalidInstalledPackage(DiagnosticPipError):
    reference = "invalid-installed-package"

    def __init__(
        self,
        *,
        dist: "BaseDistribution",
        invalid_exc: Union[InvalidRequirement, InvalidVersion],
    ) -> None:
        installed_location = dist.installed_location

        if isinstance(invalid_exc, InvalidRequirement):
            invalid_type = "requirement"
        else:
            invalid_type = "version"

        super().__init__(
            message=Text(
                f"Cannot process installed package {dist} "
                + (f"in {installed_location!r} " if installed_location else "")
                + f"because it has an invalid {invalid_type}:\n{invalid_exc.args[0]}"
            ),
            context=(
                "Starting with pip 24.1, packages with invalid "
                f"{invalid_type}s can not be processed."
            ),
            hint_stmt="To proceed this package must be uninstalled.",
        )

# === NexusCore/openenv\Lib\site-packages\IPython\core\inputtransformer2.py ===
"""Input transformer machinery to support IPython special syntax.

This includes the machinery to recognise and transform ``%magic`` commands,
``!system`` commands, ``help?`` querying, prompt stripping, and so forth.

Added: IPython 7.0. Replaces inputsplitter and inputtransformer which were
deprecated in 7.0 and removed in 9.0
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import ast
from codeop import CommandCompiler, Compile
import re
import sys
import tokenize
from typing import List, Tuple, Optional, Any
import warnings
from textwrap import dedent

from IPython.utils import tokenutil

_indent_re = re.compile(r'^[ \t]+')

def leading_empty_lines(lines):
    """Remove leading empty lines

    If the leading lines are empty or contain only whitespace, they will be
    removed.
    """
    if not lines:
        return lines
    for i, line in enumerate(lines):
        if line and not line.isspace():
            return lines[i:]
    return lines

def leading_indent(lines):
    """Remove leading indentation.

    Removes the minimum common leading indentation from all lines.
    """
    if not lines:
        return lines
    return dedent("".join(lines)).splitlines(keepends=True)

class PromptStripper:
    """Remove matching input prompts from a block of input.

    Parameters
    ----------
    prompt_re : regular expression
        A regular expression matching any input prompt (including continuation,
        e.g. ``...``)
    initial_re : regular expression, optional
        A regular expression matching only the initial prompt, but not continuation.
        If no initial expression is given, prompt_re will be used everywhere.
        Used mainly for plain Python prompts (``>>>``), where the continuation prompt
        ``...`` is a valid Python expression in Python 3, so shouldn't be stripped.

    Notes
    -----

    If initial_re and prompt_re differ,
    only initial_re will be tested against the first line.
    If any prompt is found on the first two lines,
    prompts will be stripped from the rest of the block.
    """
    def __init__(self, prompt_re, initial_re=None):
        self.prompt_re = prompt_re
        self.initial_re = initial_re or prompt_re

    def _strip(self, lines):
        return [self.prompt_re.sub('', l, count=1) for l in lines]

    def __call__(self, lines):
        if not lines:
            return lines
        if self.initial_re.match(lines[0]) or \
                (len(lines) > 1 and self.prompt_re.match(lines[1])):
            return self._strip(lines)
        return lines

classic_prompt = PromptStripper(
    prompt_re=re.compile(r'^(>>>|\.\.\.)( |$)'),
    initial_re=re.compile(r'^>>>( |$)')
)

ipython_prompt = PromptStripper(
    re.compile(
        r"""
        ^(                         # Match from the beginning of a line, either:

                                   # 1. First-line prompt:
        ((\[nav\]|\[ins\])?\ )?    # Vi editing mode prompt, if it's there
        In\                        # The 'In' of the prompt, with a space
        \[\d+\]:                   # Command index, as displayed in the prompt
        \                          # With a mandatory trailing space

        |                          # ... or ...

                                   # 2. The three dots of the multiline prompt
        \s*                        # All leading whitespace characters
        \.{3,}:                    # The three (or more) dots
        \ ?                        # With an optional trailing space

        )
        """,
        re.VERBOSE,
    )
)


def cell_magic(lines):
    if not lines or not lines[0].startswith('%%'):
        return lines
    if re.match(r'%%\w+\?', lines[0]):
        # This case will be handled by help_end
        return lines
    magic_name, _, first_line = lines[0][2:].rstrip().partition(' ')
    body = ''.join(lines[1:])
    return ['get_ipython().run_cell_magic(%r, %r, %r)\n'
            % (magic_name, first_line, body)]


def _find_assign_op(token_line) -> Optional[int]:
    """Get the index of the first assignment in the line ('=' not inside brackets)

    Note: We don't try to support multiple special assignment (a = b = %foo)
    """
    paren_level = 0
    for i, ti in enumerate(token_line):
        s = ti.string
        if s == '=' and paren_level == 0:
            return i
        if s in {'(','[','{'}:
            paren_level += 1
        elif s in {')', ']', '}'}:
            if paren_level > 0:
                paren_level -= 1
    return None

def find_end_of_continued_line(lines, start_line: int):
    """Find the last line of a line explicitly extended using backslashes.

    Uses 0-indexed line numbers.
    """
    end_line = start_line
    while lines[end_line].endswith('\\\n'):
        end_line += 1
        if end_line >= len(lines):
            break
    return end_line

def assemble_continued_line(lines, start: Tuple[int, int], end_line: int):
    r"""Assemble a single line from multiple continued line pieces

    Continued lines are lines ending in ``\``, and the line following the last
    ``\`` in the block.

    For example, this code continues over multiple lines::

        if (assign_ix is not None) \
             and (len(line) >= assign_ix + 2) \
             and (line[assign_ix+1].string == '%') \
             and (line[assign_ix+2].type == tokenize.NAME):

    This statement contains four continued line pieces.
    Assembling these pieces into a single line would give::

        if (assign_ix is not None) and (len(line) >= assign_ix + 2) and (line[...

    This uses 0-indexed line numbers. *start* is (lineno, colno).

    Used to allow ``%magic`` and ``!system`` commands to be continued over
    multiple lines.
    """
    parts = [lines[start[0]][start[1]:]] + lines[start[0]+1:end_line+1]
    return ' '.join([p.rstrip()[:-1] for p in parts[:-1]]  # Strip backslash+newline
                    + [parts[-1].rstrip()])         # Strip newline from last line

class TokenTransformBase:
    """Base class for transformations which examine tokens.

    Special syntax should not be transformed when it occurs inside strings or
    comments. This is hard to reliably avoid with regexes. The solution is to
    tokenise the code as Python, and recognise the special syntax in the tokens.

    IPython's special syntax is not valid Python syntax, so tokenising may go
    wrong after the special syntax starts. These classes therefore find and
    transform *one* instance of special syntax at a time into regular Python
    syntax. After each transformation, tokens are regenerated to find the next
    piece of special syntax.

    Subclasses need to implement one class method (find)
    and one regular method (transform).

    The priority attribute can select which transformation to apply if multiple
    transformers match in the same place. Lower numbers have higher priority.
    This allows "%magic?" to be turned into a help call rather than a magic call.
    """
    # Lower numbers -> higher priority (for matches in the same location)
    priority = 10

    def sortby(self):
        return self.start_line, self.start_col, self.priority

    def __init__(self, start):
        self.start_line = start[0] - 1   # Shift from 1-index to 0-index
        self.start_col = start[1]

    @classmethod
    def find(cls, tokens_by_line):
        """Find one instance of special syntax in the provided tokens.

        Tokens are grouped into logical lines for convenience,
        so it is easy to e.g. look at the first token of each line.
        *tokens_by_line* is a list of lists of tokenize.TokenInfo objects.

        This should return an instance of its class, pointing to the start
        position it has found, or None if it found no match.
        """
        raise NotImplementedError

    def transform(self, lines: List[str]):
        """Transform one instance of special syntax found by ``find()``

        Takes a list of strings representing physical lines,
        returns a similar list of transformed lines.
        """
        raise NotImplementedError

class MagicAssign(TokenTransformBase):
    """Transformer for assignments from magics (a = %foo)"""
    @classmethod
    def find(cls, tokens_by_line):
        """Find the first magic assignment (a = %foo) in the cell.
        """
        for line in tokens_by_line:
            assign_ix = _find_assign_op(line)
            if (assign_ix is not None) \
                    and (len(line) >= assign_ix + 2) \
                    and (line[assign_ix+1].string == '%') \
                    and (line[assign_ix+2].type == tokenize.NAME):
                return cls(line[assign_ix+1].start)

    def transform(self, lines: List[str]):
        """Transform a magic assignment found by the ``find()`` classmethod.
        """
        start_line, start_col = self.start_line, self.start_col
        lhs = lines[start_line][:start_col]
        end_line = find_end_of_continued_line(lines, start_line)
        rhs = assemble_continued_line(lines, (start_line, start_col), end_line)
        assert rhs.startswith('%'), rhs
        magic_name, _, args = rhs[1:].partition(' ')

        lines_before = lines[:start_line]
        call = "get_ipython().run_line_magic({!r}, {!r})".format(magic_name, args)
        new_line = lhs + call + '\n'
        lines_after = lines[end_line+1:]

        return lines_before + [new_line] + lines_after


class SystemAssign(TokenTransformBase):
    """Transformer for assignments from system commands (a = !foo)"""
    @classmethod
    def find_pre_312(cls, tokens_by_line):
        for line in tokens_by_line:
            assign_ix = _find_assign_op(line)
            if (assign_ix is not None) \
                    and not line[assign_ix].line.strip().startswith('=') \
                    and (len(line) >= assign_ix + 2) \
                    and (line[assign_ix + 1].type == tokenize.ERRORTOKEN):
                ix = assign_ix + 1

                while ix < len(line) and line[ix].type == tokenize.ERRORTOKEN:
                    if line[ix].string == '!':
                        return cls(line[ix].start)
                    elif not line[ix].string.isspace():
                        break
                    ix += 1

    @classmethod
    def find_post_312(cls, tokens_by_line):
        for line in tokens_by_line:
            assign_ix = _find_assign_op(line)
            if (
                (assign_ix is not None)
                and not line[assign_ix].line.strip().startswith("=")
                and (len(line) >= assign_ix + 2)
                and (line[assign_ix + 1].type == tokenize.OP)
                and (line[assign_ix + 1].string == "!")
            ):
                return cls(line[assign_ix + 1].start)

    @classmethod
    def find(cls, tokens_by_line):
        """Find the first system assignment (a = !foo) in the cell."""
        if sys.version_info < (3, 12):
            return cls.find_pre_312(tokens_by_line)
        return cls.find_post_312(tokens_by_line)

    def transform(self, lines: List[str]):
        """Transform a system assignment found by the ``find()`` classmethod.
        """
        start_line, start_col = self.start_line, self.start_col

        lhs = lines[start_line][:start_col]
        end_line = find_end_of_continued_line(lines, start_line)
        rhs = assemble_continued_line(lines, (start_line, start_col), end_line)
        assert rhs.startswith('!'), rhs
        cmd = rhs[1:]

        lines_before = lines[:start_line]
        call = "get_ipython().getoutput({!r})".format(cmd)
        new_line = lhs + call + '\n'
        lines_after = lines[end_line + 1:]

        return lines_before + [new_line] + lines_after

# The escape sequences that define the syntax transformations IPython will
# apply to user input.  These can NOT be just changed here: many regular
# expressions and other parts of the code may use their hardcoded values, and
# for all intents and purposes they constitute the 'IPython syntax', so they
# should be considered fixed.

ESC_SHELL  = '!'     # Send line to underlying system shell
ESC_SH_CAP = '!!'    # Send line to system shell and capture output
ESC_HELP   = '?'     # Find information about object
ESC_HELP2  = '??'    # Find extra-detailed information about object
ESC_MAGIC  = '%'     # Call magic function
ESC_MAGIC2 = '%%'    # Call cell-magic function
ESC_QUOTE  = ','     # Split args on whitespace, quote each as string and call
ESC_QUOTE2 = ';'     # Quote all args as a single string, call
ESC_PAREN  = '/'     # Call first argument with rest of line as arguments

ESCAPE_SINGLES = {'!', '?', '%', ',', ';', '/'}
ESCAPE_DOUBLES = {'!!', '??'}  # %% (cell magic) is handled separately

def _make_help_call(target, esc):
    """Prepares a pinfo(2)/psearch call from a target name and the escape
    (i.e. ? or ??)"""
    method  = 'pinfo2' if esc == '??' \
                else 'psearch' if '*' in target \
                else 'pinfo'
    arg = " ".join([method, target])
    #Prepare arguments for get_ipython().run_line_magic(magic_name, magic_args)
    t_magic_name, _, t_magic_arg_s = arg.partition(' ')
    t_magic_name = t_magic_name.lstrip(ESC_MAGIC)
    return "get_ipython().run_line_magic(%r, %r)" % (t_magic_name, t_magic_arg_s)


def _tr_help(content):
    """Translate lines escaped with: ?

    A naked help line should fire the intro help screen (shell.show_usage())
    """
    if not content:
        return 'get_ipython().show_usage()'

    return _make_help_call(content, '?')

def _tr_help2(content):
    """Translate lines escaped with: ??

    A naked help line should fire the intro help screen (shell.show_usage())
    """
    if not content:
        return 'get_ipython().show_usage()'

    return _make_help_call(content, '??')

def _tr_magic(content):
    "Translate lines escaped with a percent sign: %"
    name, _, args = content.partition(' ')
    return 'get_ipython().run_line_magic(%r, %r)' % (name, args)

def _tr_quote(content):
    "Translate lines escaped with a comma: ,"
    name, _, args = content.partition(' ')
    return '%s("%s")' % (name, '", "'.join(args.split()) )

def _tr_quote2(content):
    "Translate lines escaped with a semicolon: ;"
    name, _, args = content.partition(' ')
    return '%s("%s")' % (name, args)

def _tr_paren(content):
    "Translate lines escaped with a slash: /"
    name, _, args = content.partition(" ")
    if name == "":
        raise SyntaxError(f'"{ESC_SHELL}" must be followed by a callable name')

    return '%s(%s)' % (name, ", ".join(args.split()))

tr = { ESC_SHELL  : 'get_ipython().system({!r})'.format,
       ESC_SH_CAP : 'get_ipython().getoutput({!r})'.format,
       ESC_HELP   : _tr_help,
       ESC_HELP2  : _tr_help2,
       ESC_MAGIC  : _tr_magic,
       ESC_QUOTE  : _tr_quote,
       ESC_QUOTE2 : _tr_quote2,
       ESC_PAREN  : _tr_paren }

class EscapedCommand(TokenTransformBase):
    """Transformer for escaped commands like %foo, !foo, or /foo"""
    @classmethod
    def find(cls, tokens_by_line):
        """Find the first escaped command (%foo, !foo, etc.) in the cell.
        """
        for line in tokens_by_line:
            if not line:
                continue
            ix = 0
            ll = len(line)
            while ll > ix and line[ix].type in {tokenize.INDENT, tokenize.DEDENT}:
                ix += 1
            if ix >= ll:
                continue
            if line[ix].string in ESCAPE_SINGLES:
                return cls(line[ix].start)

    def transform(self, lines):
        """Transform an escaped line found by the ``find()`` classmethod.
        """
        start_line, start_col = self.start_line, self.start_col

        indent = lines[start_line][:start_col]
        end_line = find_end_of_continued_line(lines, start_line)
        line = assemble_continued_line(lines, (start_line, start_col), end_line)

        if len(line) > 1 and line[:2] in ESCAPE_DOUBLES:
            escape, content = line[:2], line[2:]
        else:
            escape, content = line[:1], line[1:]

        if escape in tr:
            call = tr[escape](content)
        else:
            call = ''

        lines_before = lines[:start_line]
        new_line = indent + call + '\n'
        lines_after = lines[end_line + 1:]

        return lines_before + [new_line] + lines_after


_help_end_re = re.compile(
    r"""(%{0,2}
    (?!\d)[\w*]+            # Variable name
    (\.(?!\d)[\w*]+|\[-?[0-9]+\])*       # .etc.etc or [0], we only support literal integers.
    )
    (\?\??)$                # ? or ??
    """,
    re.VERBOSE,
)


class HelpEnd(TokenTransformBase):
    """Transformer for help syntax: obj? and obj??"""
    # This needs to be higher priority (lower number) than EscapedCommand so
    # that inspecting magics (%foo?) works.
    priority = 5

    def __init__(self, start, q_locn):
        super().__init__(start)
        self.q_line = q_locn[0] - 1  # Shift from 1-indexed to 0-indexed
        self.q_col = q_locn[1]

    @classmethod
    def find(cls, tokens_by_line):
        """Find the first help command (foo?) in the cell.
        """
        for line in tokens_by_line:
            # Last token is NEWLINE; look at last but one
            if len(line) > 2 and line[-2].string == '?':
                # Find the first token that's not INDENT/DEDENT
                ix = 0
                while line[ix].type in {tokenize.INDENT, tokenize.DEDENT}:
                    ix += 1
                return cls(line[ix].start, line[-2].start)

    def transform(self, lines):
        """Transform a help command found by the ``find()`` classmethod.
        """

        piece = "".join(lines[self.start_line : self.q_line + 1])
        indent, content = piece[: self.start_col], piece[self.start_col :]
        lines_before = lines[: self.start_line]
        lines_after = lines[self.q_line + 1 :]

        m = _help_end_re.search(content)
        if not m:
            raise SyntaxError(content)
        assert m is not None, content
        target = m.group(1)
        esc = m.group(3)


        call = _make_help_call(target, esc)
        new_line = indent + call + '\n'

        return lines_before + [new_line] + lines_after

def make_tokens_by_line(lines:List[str]):
    """Tokenize a series of lines and group tokens by line.

    The tokens for a multiline Python string or expression are grouped as one
    line. All lines except the last lines should keep their line ending ('\\n',
    '\\r\\n') for this to properly work. Use `.splitlines(keeplineending=True)`
    for example when passing block of text to this function.

    """
    # NL tokens are used inside multiline expressions, but also after blank
    # lines or comments. This is intentional - see https://bugs.python.org/issue17061
    # We want to group the former case together but split the latter, so we
    # track parentheses level, similar to the internals of tokenize.

    #   reexported from token on 3.7+
    NEWLINE, NL = tokenize.NEWLINE, tokenize.NL  # type: ignore
    tokens_by_line: List[List[Any]] = [[]]
    if len(lines) > 1 and not lines[0].endswith(("\n", "\r", "\r\n", "\x0b", "\x0c")):
        warnings.warn(
            "`make_tokens_by_line` received a list of lines which do not have lineending markers ('\\n', '\\r', '\\r\\n', '\\x0b', '\\x0c'), behavior will be unspecified",
            stacklevel=2,
        )
    parenlev = 0
    try:
        for token in tokenutil.generate_tokens_catch_errors(
            iter(lines).__next__, extra_errors_to_catch=["expected EOF"]
        ):
            tokens_by_line[-1].append(token)
            if (token.type == NEWLINE) \
                    or ((token.type == NL) and (parenlev <= 0)):
                tokens_by_line.append([])
            elif token.string in {'(', '[', '{'}:
                parenlev += 1
            elif token.string in {')', ']', '}'}:
                if parenlev > 0:
                    parenlev -= 1
    except tokenize.TokenError:
        # Input ended in a multiline string or expression. That's OK for us.
        pass


    if not tokens_by_line[-1]:
        tokens_by_line.pop()


    return tokens_by_line


def has_sunken_brackets(tokens: List[tokenize.TokenInfo]):
    """Check if the depth of brackets in the list of tokens drops below 0"""
    parenlev = 0
    for token in tokens:
        if token.string in {"(", "[", "{"}:
            parenlev += 1
        elif token.string in {")", "]", "}"}:
            parenlev -= 1
            if parenlev < 0:
                return True
    return False

# Arbitrary limit to prevent getting stuck in infinite loops
TRANSFORM_LOOP_LIMIT = 500

class TransformerManager:
    """Applies various transformations to a cell or code block.

    The key methods for external use are ``transform_cell()``
    and ``check_complete()``.
    """
    def __init__(self):
        self.cleanup_transforms = [
            leading_empty_lines,
            leading_indent,
            classic_prompt,
            ipython_prompt,
        ]
        self.line_transforms = [
            cell_magic,
        ]
        self.token_transformers = [
            MagicAssign,
            SystemAssign,
            EscapedCommand,
            HelpEnd,
        ]

    def do_one_token_transform(self, lines):
        """Find and run the transform earliest in the code.

        Returns (changed, lines).

        This method is called repeatedly until changed is False, indicating
        that all available transformations are complete.

        The tokens following IPython special syntax might not be valid, so
        the transformed code is retokenised every time to identify the next
        piece of special syntax. Hopefully long code cells are mostly valid
        Python, not using lots of IPython special syntax, so this shouldn't be
        a performance issue.
        """
        tokens_by_line = make_tokens_by_line(lines)
        candidates = []
        for transformer_cls in self.token_transformers:
            transformer = transformer_cls.find(tokens_by_line)
            if transformer:
                candidates.append(transformer)

        if not candidates:
            # Nothing to transform
            return False, lines
        ordered_transformers = sorted(candidates, key=TokenTransformBase.sortby)
        for transformer in ordered_transformers:
            try:
                return True, transformer.transform(lines)
            except SyntaxError:
                pass
        return False, lines

    def do_token_transforms(self, lines):
        for _ in range(TRANSFORM_LOOP_LIMIT):
            changed, lines = self.do_one_token_transform(lines)
            if not changed:
                return lines

        raise RuntimeError("Input transformation still changing after "
                           "%d iterations. Aborting." % TRANSFORM_LOOP_LIMIT)

    def transform_cell(self, cell: str) -> str:
        """Transforms a cell of input code"""
        if not cell.endswith('\n'):
            cell += '\n'  # Ensure the cell has a trailing newline
        lines = cell.splitlines(keepends=True)
        for transform in self.cleanup_transforms + self.line_transforms:
            lines = transform(lines)

        lines = self.do_token_transforms(lines)
        return ''.join(lines)

    def check_complete(self, cell: str):
        """Return whether a block of code is ready to execute, or should be continued

        Parameters
        ----------
        cell : string
            Python input code, which can be multiline.

        Returns
        -------
        status : str
            One of 'complete', 'incomplete', or 'invalid' if source is not a
            prefix of valid code.
        indent_spaces : int or None
            The number of spaces by which to indent the next line of code. If
            status is not 'incomplete', this is None.
        """
        # Remember if the lines ends in a new line.
        ends_with_newline = False
        for character in reversed(cell):
            if character == '\n':
                ends_with_newline = True
                break
            elif character.strip():
                break
            else:
                continue

        if not ends_with_newline:
            # Append an newline for consistent tokenization
            # See https://bugs.python.org/issue33899
            cell += '\n'

        lines = cell.splitlines(keepends=True)

        if not lines:
            return 'complete', None

        for line in reversed(lines):
            if not line.strip():
                continue
            elif line.strip("\n").endswith("\\"):
                return "incomplete", find_last_indent(lines)
            else:
                break

        try:
            for transform in self.cleanup_transforms:
                if not getattr(transform, 'has_side_effects', False):
                    lines = transform(lines)
        except SyntaxError:
            return 'invalid', None

        if lines[0].startswith('%%'):
            # Special case for cell magics - completion marked by blank line
            if lines[-1].strip():
                return 'incomplete', find_last_indent(lines)
            else:
                return 'complete', None

        try:
            for transform in self.line_transforms:
                if not getattr(transform, 'has_side_effects', False):
                    lines = transform(lines)
            lines = self.do_token_transforms(lines)
        except SyntaxError:
            return 'invalid', None

        tokens_by_line = make_tokens_by_line(lines)

        # Bail if we got one line and there are more closing parentheses than
        # the opening ones
        if (
            len(lines) == 1
            and tokens_by_line
            and has_sunken_brackets(tokens_by_line[0])
        ):
            return "invalid", None

        if not tokens_by_line:
            return 'incomplete', find_last_indent(lines)

        if (
            tokens_by_line[-1][-1].type != tokenize.ENDMARKER
            and tokens_by_line[-1][-1].type != tokenize.ERRORTOKEN
        ):
            # We're in a multiline string or expression
            return 'incomplete', find_last_indent(lines)

        newline_types = {tokenize.NEWLINE, tokenize.COMMENT, tokenize.ENDMARKER} # type: ignore

        # Pop the last line which only contains DEDENTs and ENDMARKER
        last_token_line = None
        if {t.type for t in tokens_by_line[-1]} in [
            {tokenize.DEDENT, tokenize.ENDMARKER},
            {tokenize.ENDMARKER}
        ] and len(tokens_by_line) > 1:
            last_token_line = tokens_by_line.pop()

        while tokens_by_line[-1] and tokens_by_line[-1][-1].type in newline_types:
            tokens_by_line[-1].pop()

        if not tokens_by_line[-1]:
            return 'incomplete', find_last_indent(lines)

        if tokens_by_line[-1][-1].string == ':':
            # The last line starts a block (e.g. 'if foo:')
            ix = 0
            while tokens_by_line[-1][ix].type in {tokenize.INDENT, tokenize.DEDENT}:
                ix += 1

            indent = tokens_by_line[-1][ix].start[1]
            return 'incomplete', indent + 4

        if tokens_by_line[-1][0].line.endswith('\\'):
            return 'incomplete', None

        # At this point, our checks think the code is complete (or invalid).
        # We'll use codeop.compile_command to check this with the real parser
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', SyntaxWarning)
                res = compile_command(''.join(lines), symbol='exec')
        except (SyntaxError, OverflowError, ValueError, TypeError,
                MemoryError, SyntaxWarning):
            return 'invalid', None
        else:
            if res is None:
                return 'incomplete', find_last_indent(lines)

        if last_token_line and last_token_line[0].type == tokenize.DEDENT:
            if ends_with_newline:
                return 'complete', None
            return 'incomplete', find_last_indent(lines)

        # If there's a blank line at the end, assume we're ready to execute
        if not lines[-1].strip():
            return 'complete', None

        return 'complete', None


def find_last_indent(lines):
    m = _indent_re.match(lines[-1])
    if not m:
        return 0
    return len(m.group(0).replace('\t', ' '*4))


class MaybeAsyncCompile(Compile):
    def __init__(self, extra_flags=0):
        super().__init__()
        self.flags |= extra_flags


class MaybeAsyncCommandCompiler(CommandCompiler):
    def __init__(self, extra_flags=0):
        self.compiler = MaybeAsyncCompile(extra_flags=extra_flags)


_extra_flags = ast.PyCF_ALLOW_TOP_LEVEL_AWAIT

compile_command = MaybeAsyncCommandCompiler(extra_flags=_extra_flags)

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_frame.py ===
# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Pattern,
    Sequence,
    Set,
    Union,
    cast,
)

from pyee import EventEmitter

from playwright._impl._api_structures import AriaRole, FilePayload, Position
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._element_handle import ElementHandle, convert_select_option_values
from playwright._impl._errors import Error
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._helper import (
    DocumentLoadState,
    FrameNavigatedEvent,
    KeyboardModifier,
    Literal,
    MouseButton,
    URLMatch,
    async_readfile,
    locals_to_params,
    monotonic_time,
    url_matches,
)
from playwright._impl._js_handle import (
    JSHandle,
    Serializable,
    add_source_url_to_script,
    parse_result,
    serialize_argument,
)
from playwright._impl._locator import (
    FrameLocator,
    Locator,
    get_by_alt_text_selector,
    get_by_label_selector,
    get_by_placeholder_selector,
    get_by_role_selector,
    get_by_test_id_selector,
    get_by_text_selector,
    get_by_title_selector,
    test_id_attribute_name,
)
from playwright._impl._network import Response
from playwright._impl._set_input_files_helpers import convert_input_files
from playwright._impl._waiter import Waiter

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._page import Page


class Frame(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._parent_frame = from_nullable_channel(initializer.get("parentFrame"))
        if self._parent_frame:
            self._parent_frame._child_frames.append(self)
        self._name = initializer["name"]
        self._url = initializer["url"]
        self._detached = False
        self._child_frames: List[Frame] = []
        self._page: Optional[Page] = None
        self._load_states: Set[str] = set(initializer["loadStates"])
        self._event_emitter = EventEmitter()
        self._channel.on(
            "loadstate",
            lambda params: self._on_load_state(params.get("add"), params.get("remove")),
        )
        self._channel.on(
            "navigated",
            lambda params: self._on_frame_navigated(params),
        )

    def __repr__(self) -> str:
        return f"<Frame name={self.name} url={self.url!r}>"

    def _on_load_state(
        self, add: DocumentLoadState = None, remove: DocumentLoadState = None
    ) -> None:
        if add:
            self._load_states.add(add)
            self._event_emitter.emit("loadstate", add)
        elif remove and remove in self._load_states:
            self._load_states.remove(remove)
        if not self._parent_frame and add == "load" and self._page:
            self._page.emit("load", self._page)
        if not self._parent_frame and add == "domcontentloaded" and self._page:
            self._page.emit("domcontentloaded", self._page)

    def _on_frame_navigated(self, event: FrameNavigatedEvent) -> None:
        self._url = event["url"]
        self._name = event["name"]
        self._event_emitter.emit("navigated", event)
        if "error" not in event and self._page:
            self._page.emit("framenavigated", self)

    async def _query_count(self, selector: str) -> int:
        return await self._channel.send("queryCount", {"selector": selector})

    @property
    def page(self) -> "Page":
        assert self._page
        return self._page

    async def goto(
        self,
        url: str,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
        referer: str = None,
    ) -> Optional[Response]:
        return cast(
            Optional[Response],
            from_nullable_channel(
                await self._channel.send("goto", locals_to_params(locals()))
            ),
        )

    def _setup_navigation_waiter(self, wait_name: str, timeout: float = None) -> Waiter:
        assert self._page
        waiter = Waiter(self._page, f"frame.{wait_name}")
        waiter.reject_on_event(
            self._page,
            "close",
            lambda: cast("Page", self._page)._close_error_with_reason(),
        )
        waiter.reject_on_event(
            self._page, "crash", Error("Navigation failed because page crashed!")
        )
        waiter.reject_on_event(
            self._page,
            "framedetached",
            Error("Navigating frame was detached!"),
            lambda frame: frame == self,
        )
        if timeout is None:
            timeout = self._page._timeout_settings.navigation_timeout()
        waiter.reject_on_timeout(timeout, f"Timeout {timeout}ms exceeded.")
        return waiter

    def expect_navigation(
        self,
        url: URLMatch = None,
        waitUntil: DocumentLoadState = None,
        timeout: float = None,
    ) -> EventContextManagerImpl[Response]:
        assert self._page
        if not waitUntil:
            waitUntil = "load"

        if timeout is None:
            timeout = self._page._timeout_settings.navigation_timeout()
        deadline = monotonic_time() + timeout
        waiter = self._setup_navigation_waiter("expect_navigation", timeout)

        to_url = f' to "{url}"' if url else ""
        waiter.log(f"waiting for navigation{to_url} until '{waitUntil}'")

        def predicate(event: Any) -> bool:
            # Any failed navigation results in a rejection.
            if event.get("error"):
                return True
            waiter.log(f'  navigated to "{event["url"]}"')
            return url_matches(
                cast("Page", self._page)._browser_context._options.get("baseURL"),
                event["url"],
                url,
            )

        waiter.wait_for_event(
            self._event_emitter,
            "navigated",
            predicate=predicate,
        )

        async def continuation() -> Optional[Response]:
            event = await waiter.result()
            if "error" in event:
                raise Error(event["error"])
            if waitUntil not in self._load_states:
                t = deadline - monotonic_time()
                if t > 0:
                    await self._wait_for_load_state_impl(state=waitUntil, timeout=t)
            if "newDocument" in event and "request" in event["newDocument"]:
                request = from_channel(event["newDocument"]["request"])
                return await request.response()
            return None

        return EventContextManagerImpl(asyncio.create_task(continuation()))

    async def wait_for_url(
        self,
        url: URLMatch,
        waitUntil: DocumentLoadState = None,
        timeout: float = None,
    ) -> None:
        assert self._page
        if url_matches(
            self._page._browser_context._options.get("baseURL"), self.url, url
        ):
            await self._wait_for_load_state_impl(state=waitUntil, timeout=timeout)
            return
        async with self.expect_navigation(
            url=url, waitUntil=waitUntil, timeout=timeout
        ):
            pass

    async def wait_for_load_state(
        self,
        state: Literal["domcontentloaded", "load", "networkidle"] = None,
        timeout: float = None,
    ) -> None:
        return await self._wait_for_load_state_impl(state, timeout)

    async def _wait_for_load_state_impl(
        self, state: DocumentLoadState = None, timeout: float = None
    ) -> None:
        if not state:
            state = "load"
        if state not in ("load", "domcontentloaded", "networkidle", "commit"):
            raise Error(
                "state: expected one of (load|domcontentloaded|networkidle|commit)"
            )
        waiter = self._setup_navigation_waiter("wait_for_load_state", timeout)

        if state in self._load_states:
            waiter.log(f'  not waiting, "{state}" event already fired')
            # TODO: align with upstream
            waiter._fulfill(None)
        else:

            def handle_load_state_event(actual_state: str) -> bool:
                waiter.log(f'"{actual_state}" event fired')
                return actual_state == state

            waiter.wait_for_event(
                self._event_emitter,
                "loadstate",
                handle_load_state_event,
            )
        await waiter.result()

    async def frame_element(self) -> ElementHandle:
        return from_channel(await self._channel.send("frameElement"))

    async def evaluate(self, expression: str, arg: Serializable = None) -> Any:
        return parse_result(
            await self._channel.send(
                "evaluateExpression",
                dict(
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def evaluate_handle(
        self, expression: str, arg: Serializable = None
    ) -> JSHandle:
        return from_channel(
            await self._channel.send(
                "evaluateExpressionHandle",
                dict(
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def query_selector(
        self, selector: str, strict: bool = None
    ) -> Optional[ElementHandle]:
        return from_nullable_channel(
            await self._channel.send("querySelector", locals_to_params(locals()))
        )

    async def query_selector_all(self, selector: str) -> List[ElementHandle]:
        return list(
            map(
                from_channel,
                await self._channel.send("querySelectorAll", dict(selector=selector)),
            )
        )

    async def wait_for_selector(
        self,
        selector: str,
        strict: bool = None,
        timeout: float = None,
        state: Literal["attached", "detached", "hidden", "visible"] = None,
    ) -> Optional[ElementHandle]:
        return from_nullable_channel(
            await self._channel.send("waitForSelector", locals_to_params(locals()))
        )

    async def is_checked(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._channel.send("isChecked", locals_to_params(locals()))

    async def is_disabled(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._channel.send("isDisabled", locals_to_params(locals()))

    async def is_editable(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._channel.send("isEditable", locals_to_params(locals()))

    async def is_enabled(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._channel.send("isEnabled", locals_to_params(locals()))

    async def is_hidden(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._channel.send("isHidden", locals_to_params(locals()))

    async def is_visible(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> bool:
        return await self._channel.send("isVisible", locals_to_params(locals()))

    async def dispatch_event(
        self,
        selector: str,
        type: str,
        eventInit: Dict = None,
        strict: bool = None,
        timeout: float = None,
    ) -> None:
        await self._channel.send(
            "dispatchEvent",
            locals_to_params(
                dict(
                    selector=selector,
                    type=type,
                    eventInit=serialize_argument(eventInit),
                    strict=strict,
                    timeout=timeout,
                ),
            ),
        )

    async def eval_on_selector(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
        strict: bool = None,
    ) -> Any:
        return parse_result(
            await self._channel.send(
                "evalOnSelector",
                locals_to_params(
                    dict(
                        selector=selector,
                        expression=expression,
                        arg=serialize_argument(arg),
                        strict=strict,
                    )
                ),
            )
        )

    async def eval_on_selector_all(
        self,
        selector: str,
        expression: str,
        arg: Serializable = None,
    ) -> Any:
        return parse_result(
            await self._channel.send(
                "evalOnSelectorAll",
                dict(
                    selector=selector,
                    expression=expression,
                    arg=serialize_argument(arg),
                ),
            )
        )

    async def content(self) -> str:
        return await self._channel.send("content")

    async def set_content(
        self,
        html: str,
        timeout: float = None,
        waitUntil: DocumentLoadState = None,
    ) -> None:
        await self._channel.send("setContent", locals_to_params(locals()))

    @property
    def name(self) -> str:
        return self._name or ""

    @property
    def url(self) -> str:
        return self._url or ""

    @property
    def parent_frame(self) -> Optional["Frame"]:
        return self._parent_frame

    @property
    def child_frames(self) -> List["Frame"]:
        return self._child_frames.copy()

    def is_detached(self) -> bool:
        return self._detached

    async def add_script_tag(
        self,
        url: str = None,
        path: Union[str, Path] = None,
        content: str = None,
        type: str = None,
    ) -> ElementHandle:
        params = locals_to_params(locals())
        if path:
            params["content"] = add_source_url_to_script(
                (await async_readfile(path)).decode(), path
            )
            del params["path"]
        return from_channel(await self._channel.send("addScriptTag", params))

    async def add_style_tag(
        self, url: str = None, path: Union[str, Path] = None, content: str = None
    ) -> ElementHandle:
        params = locals_to_params(locals())
        if path:
            params["content"] = (
                (await async_readfile(path)).decode()
                + "\n/*# sourceURL="
                + str(Path(path))
                + "*/"
            )
            del params["path"]
        return from_channel(await self._channel.send("addStyleTag", params))

    async def click(
        self,
        selector: str,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("click", locals_to_params(locals()))

    async def dblclick(
        self,
        selector: str,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        delay: float = None,
        button: MouseButton = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("dblclick", locals_to_params(locals()))

    async def tap(
        self,
        selector: str,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("tap", locals_to_params(locals()))

    async def fill(
        self,
        selector: str,
        value: str,
        timeout: float = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        force: bool = None,
    ) -> None:
        await self._channel.send("fill", locals_to_params(locals()))

    def locator(
        self,
        selector: str,
        hasText: Union[str, Pattern[str]] = None,
        hasNotText: Union[str, Pattern[str]] = None,
        has: Locator = None,
        hasNot: Locator = None,
    ) -> Locator:
        return Locator(
            self,
            selector,
            has_text=hasText,
            has_not_text=hasNotText,
            has=has,
            has_not=hasNot,
        )

    def get_by_alt_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_alt_text_selector(text, exact=exact))

    def get_by_label(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_label_selector(text, exact=exact))

    def get_by_placeholder(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_placeholder_selector(text, exact=exact))

    def get_by_role(
        self,
        role: AriaRole,
        checked: bool = None,
        disabled: bool = None,
        expanded: bool = None,
        includeHidden: bool = None,
        level: int = None,
        name: Union[str, Pattern[str]] = None,
        pressed: bool = None,
        selected: bool = None,
        exact: bool = None,
    ) -> "Locator":
        return self.locator(
            get_by_role_selector(
                role,
                checked=checked,
                disabled=disabled,
                expanded=expanded,
                includeHidden=includeHidden,
                level=level,
                name=name,
                pressed=pressed,
                selected=selected,
                exact=exact,
            )
        )

    def get_by_test_id(self, testId: Union[str, Pattern[str]]) -> "Locator":
        return self.locator(get_by_test_id_selector(test_id_attribute_name(), testId))

    def get_by_text(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_text_selector(text, exact=exact))

    def get_by_title(
        self, text: Union[str, Pattern[str]], exact: bool = None
    ) -> "Locator":
        return self.locator(get_by_title_selector(text, exact=exact))

    def frame_locator(self, selector: str) -> FrameLocator:
        return FrameLocator(self, selector)

    async def focus(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> None:
        await self._channel.send("focus", locals_to_params(locals()))

    async def text_content(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> Optional[str]:
        return await self._channel.send("textContent", locals_to_params(locals()))

    async def inner_text(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> str:
        return await self._channel.send("innerText", locals_to_params(locals()))

    async def inner_html(
        self, selector: str, strict: bool = None, timeout: float = None
    ) -> str:
        return await self._channel.send("innerHTML", locals_to_params(locals()))

    async def get_attribute(
        self, selector: str, name: str, strict: bool = None, timeout: float = None
    ) -> Optional[str]:
        return await self._channel.send("getAttribute", locals_to_params(locals()))

    async def hover(
        self,
        selector: str,
        modifiers: Sequence[KeyboardModifier] = None,
        position: Position = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        force: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("hover", locals_to_params(locals()))

    async def drag_and_drop(
        self,
        source: str,
        target: str,
        sourcePosition: Position = None,
        targetPosition: Position = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        timeout: float = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("dragAndDrop", locals_to_params(locals()))

    async def select_option(
        self,
        selector: str,
        value: Union[str, Sequence[str]] = None,
        index: Union[int, Sequence[int]] = None,
        label: Union[str, Sequence[str]] = None,
        element: Union["ElementHandle", Sequence["ElementHandle"]] = None,
        timeout: float = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        force: bool = None,
    ) -> List[str]:
        params = locals_to_params(
            dict(
                selector=selector,
                timeout=timeout,
                strict=strict,
                force=force,
                **convert_select_option_values(value, index, label, element),
            )
        )
        return await self._channel.send("selectOption", params)

    async def input_value(
        self,
        selector: str,
        strict: bool = None,
        timeout: float = None,
    ) -> str:
        return await self._channel.send("inputValue", locals_to_params(locals()))

    async def set_input_files(
        self,
        selector: str,
        files: Union[
            str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
        ],
        strict: bool = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        converted = await convert_input_files(files, self.page.context)
        await self._channel.send(
            "setInputFiles",
            {
                "selector": selector,
                "strict": strict,
                "timeout": timeout,
                **converted,
            },
        )

    async def type(
        self,
        selector: str,
        text: str,
        delay: float = None,
        strict: bool = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("type", locals_to_params(locals()))

    async def press(
        self,
        selector: str,
        key: str,
        delay: float = None,
        strict: bool = None,
        timeout: float = None,
        noWaitAfter: bool = None,
    ) -> None:
        await self._channel.send("press", locals_to_params(locals()))

    async def check(
        self,
        selector: str,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("check", locals_to_params(locals()))

    async def uncheck(
        self,
        selector: str,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        await self._channel.send("uncheck", locals_to_params(locals()))

    async def wait_for_timeout(self, timeout: float) -> None:
        await self._channel.send("waitForTimeout", locals_to_params(locals()))

    async def wait_for_function(
        self,
        expression: str,
        arg: Serializable = None,
        timeout: float = None,
        polling: Union[float, Literal["raf"]] = None,
    ) -> JSHandle:
        if isinstance(polling, str) and polling != "raf":
            raise Error(f"Unknown polling option: {polling}")
        params = locals_to_params(locals())
        params["arg"] = serialize_argument(arg)
        if polling is not None and polling != "raf":
            params["pollingInterval"] = polling
        return from_channel(await self._channel.send("waitForFunction", params))

    async def title(self) -> str:
        return await self._channel.send("title")

    async def set_checked(
        self,
        selector: str,
        checked: bool,
        position: Position = None,
        timeout: float = None,
        force: bool = None,
        noWaitAfter: bool = None,
        strict: bool = None,
        trial: bool = None,
    ) -> None:
        if checked:
            await self.check(
                selector=selector,
                position=position,
                timeout=timeout,
                force=force,
                strict=strict,
                trial=trial,
            )
        else:
            await self.uncheck(
                selector=selector,
                position=position,
                timeout=timeout,
                force=force,
                strict=strict,
                trial=trial,
            )

    async def _highlight(self, selector: str) -> None:
        await self._channel.send("highlight", {"selector": selector})

# === NexusCore/openenv\Lib\site-packages\jupyter_client\manager.py ===
"""Base class to manage a running kernel"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import functools
import os
import re
import signal
import sys
import typing as t
import uuid
import warnings
from asyncio.futures import Future
from concurrent.futures import Future as CFuture
from contextlib import contextmanager
from enum import Enum

import zmq
from jupyter_core.utils import run_sync
from traitlets import (
    Any,
    Bool,
    Dict,
    DottedObjectName,
    Float,
    Instance,
    Type,
    Unicode,
    default,
    observe,
    observe_compat,
)
from traitlets.utils.importstring import import_item

from . import kernelspec
from .asynchronous import AsyncKernelClient
from .blocking import BlockingKernelClient
from .client import KernelClient
from .connect import ConnectionFileMixin
from .managerabc import KernelManagerABC
from .provisioning import KernelProvisionerBase
from .provisioning import KernelProvisionerFactory as KPF  # noqa


class _ShutdownStatus(Enum):
    """

    This is so far used only for testing in order to track the internal state of
    the shutdown logic, and verifying which path is taken for which
    missbehavior.

    """

    Unset = None
    ShutdownRequest = "ShutdownRequest"
    SigtermRequest = "SigtermRequest"
    SigkillRequest = "SigkillRequest"


F = t.TypeVar("F", bound=t.Callable[..., t.Any])


def _get_future() -> t.Union[Future, CFuture]:
    """Get an appropriate Future object"""
    try:
        asyncio.get_running_loop()
        return Future()
    except RuntimeError:
        # No event loop running, use concurrent future
        return CFuture()


def in_pending_state(method: F) -> F:
    """Sets the kernel to a pending state by
    creating a fresh Future for the KernelManager's `ready`
    attribute. Once the method is finished, set the Future's results.
    """

    @t.no_type_check
    @functools.wraps(method)
    async def wrapper(self: t.Any, *args: t.Any, **kwargs: t.Any) -> t.Any:
        """Create a future for the decorated method."""
        if self._attempted_start or not self._ready:
            self._ready = _get_future()
        try:
            # call wrapped method, await, and set the result or exception.
            out = await method(self, *args, **kwargs)
            # Add a small sleep to ensure tests can capture the state before done
            await asyncio.sleep(0.01)
            if self.owns_kernel:
                self._ready.set_result(None)
            return out
        except Exception as e:
            self._ready.set_exception(e)
            self.log.exception(self._ready.exception())
            raise e

    return t.cast(F, wrapper)


class KernelManager(ConnectionFileMixin):
    """Manages a single kernel in a subprocess on this host.

    This version starts kernels with Popen.
    """

    _ready: t.Optional[t.Union[Future, CFuture]]

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Initialize a kernel manager."""
        if args:
            warnings.warn(
                "Passing positional only arguments to "
                "`KernelManager.__init__` is deprecated since jupyter_client"
                " 8.6, and will become an error on future versions. Positional "
                " arguments have been ignored since jupyter_client 7.0",
                DeprecationWarning,
                stacklevel=2,
            )
        self._owns_kernel = kwargs.pop("owns_kernel", True)
        super().__init__(**kwargs)
        self._shutdown_status = _ShutdownStatus.Unset
        self._attempted_start = False
        self._ready = None

    _created_context: Bool = Bool(False)

    # The PyZMQ Context to use for communication with the kernel.
    context: Instance = Instance(zmq.Context)

    @default("context")
    def _context_default(self) -> zmq.Context:
        self._created_context = True
        return zmq.Context()

    # the class to create with our `client` method
    client_class: DottedObjectName = DottedObjectName(
        "jupyter_client.blocking.BlockingKernelClient"
    )
    client_factory: Type = Type(klass=KernelClient)

    @default("client_factory")
    def _client_factory_default(self) -> Type:
        return import_item(self.client_class)

    @observe("client_class")
    def _client_class_changed(self, change: t.Dict[str, DottedObjectName]) -> None:
        self.client_factory = import_item(str(change["new"]))

    kernel_id: t.Union[str, Unicode] = Unicode(None, allow_none=True)

    # The kernel provisioner with which this KernelManager is communicating.
    # This will generally be a LocalProvisioner instance unless the kernelspec
    # indicates otherwise.
    provisioner: t.Optional[KernelProvisionerBase] = None

    kernel_spec_manager: Instance = Instance(kernelspec.KernelSpecManager)

    @default("kernel_spec_manager")
    def _kernel_spec_manager_default(self) -> kernelspec.KernelSpecManager:
        return kernelspec.KernelSpecManager(data_dir=self.data_dir)

    @observe("kernel_spec_manager")
    @observe_compat
    def _kernel_spec_manager_changed(self, change: t.Dict[str, Instance]) -> None:
        self._kernel_spec = None

    shutdown_wait_time: Float = Float(
        5.0,
        config=True,
        help="Time to wait for a kernel to terminate before killing it, "
        "in seconds. When a shutdown request is initiated, the kernel "
        "will be immediately sent an interrupt (SIGINT), followed"
        "by a shutdown_request message, after 1/2 of `shutdown_wait_time`"
        "it will be sent a terminate (SIGTERM) request, and finally at "
        "the end of `shutdown_wait_time` will be killed (SIGKILL). terminate "
        "and kill may be equivalent on windows.  Note that this value can be"
        "overridden by the in-use kernel provisioner since shutdown times may"
        "vary by provisioned environment.",
    )

    kernel_name: t.Union[str, Unicode] = Unicode(kernelspec.NATIVE_KERNEL_NAME)

    @observe("kernel_name")
    def _kernel_name_changed(self, change: t.Dict[str, str]) -> None:
        self._kernel_spec = None
        if change["new"] == "python":
            self.kernel_name = kernelspec.NATIVE_KERNEL_NAME

    _kernel_spec: t.Optional[kernelspec.KernelSpec] = None

    @property
    def kernel_spec(self) -> t.Optional[kernelspec.KernelSpec]:
        if self._kernel_spec is None and self.kernel_name != "":
            self._kernel_spec = self.kernel_spec_manager.get_kernel_spec(self.kernel_name)
        return self._kernel_spec

    cache_ports: Bool = Bool(
        False,
        config=True,
        help="True if the MultiKernelManager should cache ports for this KernelManager instance",
    )

    @default("cache_ports")
    def _default_cache_ports(self) -> bool:
        return self.transport == "tcp"

    @property
    def ready(self) -> t.Union[CFuture, Future]:
        """A future that resolves when the kernel process has started for the first time"""
        if not self._ready:
            self._ready = _get_future()
        return self._ready

    @property
    def ipykernel(self) -> bool:
        return self.kernel_name in {"python", "python2", "python3"}

    # Protected traits
    _launch_args: t.Optional["Dict[str, Any]"] = Dict(allow_none=True)
    _control_socket: Any = Any()

    _restarter: Any = Any()

    autorestart: Bool = Bool(
        True, config=True, help="""Should we autorestart the kernel if it dies."""
    )

    shutting_down: bool = False

    def __del__(self) -> None:
        self._close_control_socket()
        self.cleanup_connection_file()

    # --------------------------------------------------------------------------
    # Kernel restarter
    # --------------------------------------------------------------------------

    def start_restarter(self) -> None:
        """Start the kernel restarter."""
        pass

    def stop_restarter(self) -> None:
        """Stop the kernel restarter."""
        pass

    def add_restart_callback(self, callback: t.Callable, event: str = "restart") -> None:
        """Register a callback to be called when a kernel is restarted"""
        if self._restarter is None:
            return
        self._restarter.add_callback(callback, event)

    def remove_restart_callback(self, callback: t.Callable, event: str = "restart") -> None:
        """Unregister a callback to be called when a kernel is restarted"""
        if self._restarter is None:
            return
        self._restarter.remove_callback(callback, event)

    # --------------------------------------------------------------------------
    # create a Client connected to our Kernel
    # --------------------------------------------------------------------------

    def client(self, **kwargs: t.Any) -> BlockingKernelClient:
        """Create a client configured to connect to our kernel"""
        kw: dict = {}
        kw.update(self.get_connection_info(session=True))
        kw.update(
            {
                "connection_file": self.connection_file,
                "parent": self,
            }
        )

        # add kwargs last, for manual overrides
        kw.update(kwargs)
        return self.client_factory(**kw)

    # --------------------------------------------------------------------------
    # Kernel management
    # --------------------------------------------------------------------------

    def update_env(self, *, env: t.Dict[str, str]) -> None:
        """
        Allow to update the environment of a kernel manager.

        This will take effect only after kernel restart when the new env is
        passed to the new kernel.

        This is useful as some of the information of the current kernel reflect
        the state of the session that started it, and those session information
        (like the attach file path, or name), are mutable.

        .. version-added: 8.5
        """
        # Mypy think this is unreachable as it see _launch_args as Dict, not t.Dict
        if (
            isinstance(self._launch_args, dict)
            and "env" in self._launch_args
            and isinstance(self._launch_args["env"], dict)  # type: ignore [unreachable]
        ):
            self._launch_args["env"].update(env)  # type: ignore [unreachable]

    def format_kernel_cmd(self, extra_arguments: t.Optional[t.List[str]] = None) -> t.List[str]:
        """Replace templated args (e.g. {connection_file})"""
        extra_arguments = extra_arguments or []
        assert self.kernel_spec is not None
        cmd = self.kernel_spec.argv + extra_arguments

        if cmd and cmd[0] in {
            "python",
            "python%i" % sys.version_info[0],
            "python%i.%i" % sys.version_info[:2],
        }:
            # executable is 'python' or 'python3', use sys.executable.
            # These will typically be the same,
            # but if the current process is in an env
            # and has been launched by abspath without
            # activating the env, python on PATH may not be sys.executable,
            # but it should be.
            cmd[0] = sys.executable

        # Make sure to use the realpath for the connection_file
        # On windows, when running with the store python, the connection_file path
        # is not usable by non python kernels because the path is being rerouted when
        # inside of a store app.
        # See this bug here: https://bugs.python.org/issue41196
        ns: t.Dict[str, t.Any] = {
            "connection_file": os.path.realpath(self.connection_file),
            "prefix": sys.prefix,
        }

        if self.kernel_spec:  # type:ignore[truthy-bool]
            ns["resource_dir"] = self.kernel_spec.resource_dir
        assert isinstance(self._launch_args, dict)

        ns.update(self._launch_args)

        pat = re.compile(r"\{([A-Za-z0-9_]+)\}")

        def from_ns(match: t.Any) -> t.Any:
            """Get the key out of ns if it's there, otherwise no change."""
            return ns.get(match.group(1), match.group())

        return [pat.sub(from_ns, arg) for arg in cmd]

    async def _async_launch_kernel(self, kernel_cmd: t.List[str], **kw: t.Any) -> None:
        """actually launch the kernel

        override in a subclass to launch kernel subprocesses differently
        Note that provisioners can now be used to customize kernel environments
        and
        """
        assert self.provisioner is not None
        connection_info = await self.provisioner.launch_kernel(kernel_cmd, **kw)
        assert self.provisioner.has_process
        # Provisioner provides the connection information.  Load into kernel manager
        # and write the connection file, if not already done.
        self._reconcile_connection_info(connection_info)

    _launch_kernel = run_sync(_async_launch_kernel)

    # Control socket used for polite kernel shutdown

    def _connect_control_socket(self) -> None:
        if self._control_socket is None:
            self._control_socket = self._create_connected_socket("control")
            self._control_socket.linger = 100

    def _close_control_socket(self) -> None:
        if self._control_socket is None:
            return
        self._control_socket.close()
        self._control_socket = None

    async def _async_pre_start_kernel(
        self, **kw: t.Any
    ) -> t.Tuple[t.List[str], t.Dict[str, t.Any]]:
        """Prepares a kernel for startup in a separate process.

        If random ports (port=0) are being used, this method must be called
        before the channels are created.

        Parameters
        ----------
        `**kw` : optional
             keyword arguments that are passed down to build the kernel_cmd
             and launching the kernel (e.g. Popen kwargs).
        """
        self.shutting_down = False
        self.kernel_id = self.kernel_id or kw.pop("kernel_id", str(uuid.uuid4()))
        # save kwargs for use in restart
        # assigning Traitlets Dicts to Dict make mypy unhappy but is ok
        self._launch_args = kw.copy()  # type:ignore [assignment]
        if self.provisioner is None:  # will not be None on restarts
            self.provisioner = KPF.instance(parent=self.parent).create_provisioner_instance(
                self.kernel_id,
                self.kernel_spec,
                parent=self,
            )
        kw = await self.provisioner.pre_launch(**kw)
        kernel_cmd = kw.pop("cmd")
        return kernel_cmd, kw

    pre_start_kernel = run_sync(_async_pre_start_kernel)

    async def _async_post_start_kernel(self, **kw: t.Any) -> None:
        """Performs any post startup tasks relative to the kernel.

        Parameters
        ----------
        `**kw` : optional
             keyword arguments that were used in the kernel process's launch.
        """
        self.start_restarter()
        self._connect_control_socket()
        assert self.provisioner is not None
        await self.provisioner.post_launch(**kw)

    post_start_kernel = run_sync(_async_post_start_kernel)

    @in_pending_state
    async def _async_start_kernel(self, **kw: t.Any) -> None:
        """Starts a kernel on this host in a separate process.

        If random ports (port=0) are being used, this method must be called
        before the channels are created.

        Parameters
        ----------
        `**kw` : optional
             keyword arguments that are passed down to build the kernel_cmd
             and launching the kernel (e.g. Popen kwargs).
        """
        self._attempted_start = True
        kernel_cmd, kw = await self._async_pre_start_kernel(**kw)

        # launch the kernel subprocess
        self.log.debug("Starting kernel: %s", kernel_cmd)
        await self._async_launch_kernel(kernel_cmd, **kw)
        await self._async_post_start_kernel(**kw)

    start_kernel = run_sync(_async_start_kernel)

    async def _async_request_shutdown(self, restart: bool = False) -> None:
        """Send a shutdown request via control channel"""
        content = {"restart": restart}
        msg = self.session.msg("shutdown_request", content=content)
        # ensure control socket is connected
        self._connect_control_socket()
        self.session.send(self._control_socket, msg)
        assert self.provisioner is not None
        await self.provisioner.shutdown_requested(restart=restart)
        self._shutdown_status = _ShutdownStatus.ShutdownRequest

    request_shutdown = run_sync(_async_request_shutdown)

    async def _async_finish_shutdown(
        self,
        waittime: t.Optional[float] = None,
        pollinterval: float = 0.1,
        restart: bool = False,
    ) -> None:
        """Wait for kernel shutdown, then kill process if it doesn't shutdown.

        This does not send shutdown requests - use :meth:`request_shutdown`
        first.
        """
        if waittime is None:
            waittime = max(self.shutdown_wait_time, 0)
        if self.provisioner:  # Allow provisioner to override
            waittime = self.provisioner.get_shutdown_wait_time(recommended=waittime)

        try:
            await asyncio.wait_for(
                self._async_wait(pollinterval=pollinterval), timeout=waittime / 2
            )
        except asyncio.TimeoutError:
            self.log.debug("Kernel is taking too long to finish, terminating")
            self._shutdown_status = _ShutdownStatus.SigtermRequest
            await self._async_send_kernel_sigterm()

        try:
            await asyncio.wait_for(
                self._async_wait(pollinterval=pollinterval), timeout=waittime / 2
            )
        except asyncio.TimeoutError:
            self.log.debug("Kernel is taking too long to finish, killing")
            self._shutdown_status = _ShutdownStatus.SigkillRequest
            await self._async_kill_kernel(restart=restart)
        else:
            # Process is no longer alive, wait and clear
            if self.has_kernel:
                assert self.provisioner is not None
                await self.provisioner.wait()

    finish_shutdown = run_sync(_async_finish_shutdown)

    async def _async_cleanup_resources(self, restart: bool = False) -> None:
        """Clean up resources when the kernel is shut down"""
        if not restart:
            self.cleanup_connection_file()

        self.cleanup_ipc_files()
        self._close_control_socket()
        self.session.parent = None

        if self._created_context and not restart:
            self.context.destroy(linger=100)

        if self.provisioner:
            await self.provisioner.cleanup(restart=restart)

    cleanup_resources = run_sync(_async_cleanup_resources)

    @in_pending_state
    async def _async_shutdown_kernel(self, now: bool = False, restart: bool = False) -> None:
        """Attempts to stop the kernel process cleanly.

        This attempts to shutdown the kernels cleanly by:

        1. Sending it a shutdown message over the control channel.
        2. If that fails, the kernel is shutdown forcibly by sending it
           a signal.

        Parameters
        ----------
        now : bool
            Should the kernel be forcible killed *now*. This skips the
            first, nice shutdown attempt.
        restart: bool
            Will this kernel be restarted after it is shutdown. When this
            is True, connection files will not be cleaned up.
        """
        if not self.owns_kernel:
            return

        self.shutting_down = True  # Used by restarter to prevent race condition
        # Stop monitoring for restarting while we shutdown.
        self.stop_restarter()

        if self.has_kernel:
            await self._async_interrupt_kernel()

        if now:
            await self._async_kill_kernel()
        else:
            await self._async_request_shutdown(restart=restart)
            # Don't send any additional kernel kill messages immediately, to give
            # the kernel a chance to properly execute shutdown actions. Wait for at
            # most 1s, checking every 0.1s.
            await self._async_finish_shutdown(restart=restart)

        await self._async_cleanup_resources(restart=restart)

    shutdown_kernel = run_sync(_async_shutdown_kernel)

    async def _async_restart_kernel(
        self, now: bool = False, newports: bool = False, **kw: t.Any
    ) -> None:
        """Restarts a kernel with the arguments that were used to launch it.

        Parameters
        ----------
        now : bool, optional
            If True, the kernel is forcefully restarted *immediately*, without
            having a chance to do any cleanup action.  Otherwise the kernel is
            given 1s to clean up before a forceful restart is issued.

            In all cases the kernel is restarted, the only difference is whether
            it is given a chance to perform a clean shutdown or not.

        newports : bool, optional
            If the old kernel was launched with random ports, this flag decides
            whether the same ports and connection file will be used again.
            If False, the same ports and connection file are used. This is
            the default. If True, new random port numbers are chosen and a
            new connection file is written. It is still possible that the newly
            chosen random port numbers happen to be the same as the old ones.

        `**kw` : optional
            Any options specified here will overwrite those used to launch the
            kernel.
        """
        if self._launch_args is None:
            msg = "Cannot restart the kernel. No previous call to 'start_kernel'."
            raise RuntimeError(msg)

        # Stop currently running kernel.
        await self._async_shutdown_kernel(now=now, restart=True)

        if newports:
            self.cleanup_random_ports()

        # Start new kernel.
        self._launch_args.update(kw)
        await self._async_start_kernel(**self._launch_args)

    restart_kernel = run_sync(_async_restart_kernel)

    @property
    def owns_kernel(self) -> bool:
        return self._owns_kernel

    @property
    def has_kernel(self) -> bool:
        """Has a kernel process been started that we are actively managing."""
        return self.provisioner is not None and self.provisioner.has_process

    async def _async_send_kernel_sigterm(self, restart: bool = False) -> None:
        """similar to _kill_kernel, but with sigterm (not sigkill), but do not block"""
        if self.has_kernel:
            assert self.provisioner is not None
            await self.provisioner.terminate(restart=restart)

    _send_kernel_sigterm = run_sync(_async_send_kernel_sigterm)

    async def _async_kill_kernel(self, restart: bool = False) -> None:
        """Kill the running kernel.

        This is a private method, callers should use shutdown_kernel(now=True).
        """
        if self.has_kernel:
            assert self.provisioner is not None
            await self.provisioner.kill(restart=restart)

            # Wait until the kernel terminates.
            try:
                await asyncio.wait_for(self._async_wait(), timeout=5.0)
            except asyncio.TimeoutError:
                # Wait timed out, just log warning but continue - not much more we can do.
                self.log.warning("Wait for final termination of kernel timed out - continuing...")
                pass
            else:
                # Process is no longer alive, wait and clear
                if self.has_kernel:
                    await self.provisioner.wait()

    _kill_kernel = run_sync(_async_kill_kernel)

    async def _async_interrupt_kernel(self) -> None:
        """Interrupts the kernel by sending it a signal.

        Unlike ``signal_kernel``, this operation is well supported on all
        platforms.
        """
        if not self.has_kernel and self._ready is not None:
            if isinstance(self._ready, CFuture):
                ready = asyncio.ensure_future(t.cast(Future[t.Any], self._ready))
            else:
                ready = self._ready
            # Wait for a shutdown if one is in progress.
            if self.shutting_down:
                await ready
            # Wait for a startup.
            await ready

        if self.has_kernel:
            assert self.kernel_spec is not None
            interrupt_mode = self.kernel_spec.interrupt_mode
            if interrupt_mode == "signal":
                await self._async_signal_kernel(signal.SIGINT)

            elif interrupt_mode == "message":
                msg = self.session.msg("interrupt_request", content={})
                self._connect_control_socket()
                self.session.send(self._control_socket, msg)
        else:
            msg = "Cannot interrupt kernel. No kernel is running!"
            raise RuntimeError(msg)

    interrupt_kernel = run_sync(_async_interrupt_kernel)

    async def _async_signal_kernel(self, signum: int) -> None:
        """Sends a signal to the process group of the kernel (this
        usually includes the kernel and any subprocesses spawned by
        the kernel).

        Note that since only SIGTERM is supported on Windows, this function is
        only useful on Unix systems.
        """
        if self.has_kernel:
            assert self.provisioner is not None
            await self.provisioner.send_signal(signum)
        else:
            msg = "Cannot signal kernel. No kernel is running!"
            raise RuntimeError(msg)

    signal_kernel = run_sync(_async_signal_kernel)

    async def _async_is_alive(self) -> bool:
        """Is the kernel process still running?"""
        if not self.owns_kernel:
            return True

        if self.has_kernel:
            assert self.provisioner is not None
            ret = await self.provisioner.poll()
            if ret is None:
                return True
        return False

    is_alive = run_sync(_async_is_alive)

    async def _async_wait(self, pollinterval: float = 0.1) -> None:
        # Use busy loop at 100ms intervals, polling until the process is
        # not alive.  If we find the process is no longer alive, complete
        # its cleanup via the blocking wait().  Callers are responsible for
        # issuing calls to wait() using a timeout (see _kill_kernel()).
        while await self._async_is_alive():
            await asyncio.sleep(pollinterval)


class AsyncKernelManager(KernelManager):
    """An async kernel manager."""

    # the class to create with our `client` method
    client_class: DottedObjectName = DottedObjectName(
        "jupyter_client.asynchronous.AsyncKernelClient"
    )
    client_factory: Type = Type(klass="jupyter_client.asynchronous.AsyncKernelClient")

    # The PyZMQ Context to use for communication with the kernel.
    context: Instance = Instance(zmq.asyncio.Context)

    @default("context")
    def _context_default(self) -> zmq.asyncio.Context:
        self._created_context = True
        return zmq.asyncio.Context()

    def client(  # type:ignore[override]
        self, **kwargs: t.Any
    ) -> AsyncKernelClient:
        """Get a client for the manager."""
        return super().client(**kwargs)  # type:ignore[return-value]

    _launch_kernel = KernelManager._async_launch_kernel  # type:ignore[assignment]
    start_kernel: t.Callable[..., t.Awaitable] = KernelManager._async_start_kernel  # type:ignore[assignment]
    pre_start_kernel: t.Callable[..., t.Awaitable] = KernelManager._async_pre_start_kernel  # type:ignore[assignment]
    post_start_kernel: t.Callable[..., t.Awaitable] = KernelManager._async_post_start_kernel  # type:ignore[assignment]
    request_shutdown: t.Callable[..., t.Awaitable] = KernelManager._async_request_shutdown  # type:ignore[assignment]
    finish_shutdown: t.Callable[..., t.Awaitable] = KernelManager._async_finish_shutdown  # type:ignore[assignment]
    cleanup_resources: t.Callable[..., t.Awaitable] = KernelManager._async_cleanup_resources  # type:ignore[assignment]
    shutdown_kernel: t.Callable[..., t.Awaitable] = KernelManager._async_shutdown_kernel  # type:ignore[assignment]
    restart_kernel: t.Callable[..., t.Awaitable] = KernelManager._async_restart_kernel  # type:ignore[assignment]
    _send_kernel_sigterm = KernelManager._async_send_kernel_sigterm  # type:ignore[assignment]
    _kill_kernel = KernelManager._async_kill_kernel  # type:ignore[assignment]
    interrupt_kernel: t.Callable[..., t.Awaitable] = KernelManager._async_interrupt_kernel  # type:ignore[assignment]
    signal_kernel: t.Callable[..., t.Awaitable] = KernelManager._async_signal_kernel  # type:ignore[assignment]
    is_alive: t.Callable[..., t.Awaitable] = KernelManager._async_is_alive  # type:ignore[assignment]


KernelManagerABC.register(KernelManager)


def start_new_kernel(
    startup_timeout: float = 60, kernel_name: str = "python", **kwargs: t.Any
) -> t.Tuple[KernelManager, BlockingKernelClient]:
    """Start a new kernel, and return its Manager and Client"""
    km = KernelManager(kernel_name=kernel_name)
    km.start_kernel(**kwargs)
    kc = km.client()
    kc.start_channels()
    try:
        kc.wait_for_ready(timeout=startup_timeout)
    except RuntimeError:
        kc.stop_channels()
        km.shutdown_kernel()
        raise

    return km, kc


async def start_new_async_kernel(
    startup_timeout: float = 60, kernel_name: str = "python", **kwargs: t.Any
) -> t.Tuple[AsyncKernelManager, AsyncKernelClient]:
    """Start a new kernel, and return its Manager and Client"""
    km = AsyncKernelManager(kernel_name=kernel_name)
    await km.start_kernel(**kwargs)
    kc = km.client()
    kc.start_channels()
    try:
        await kc.wait_for_ready(timeout=startup_timeout)
    except RuntimeError:
        kc.stop_channels()
        await km.shutdown_kernel()
        raise

    return (km, kc)


@contextmanager
def run_kernel(**kwargs: t.Any) -> t.Iterator[KernelClient]:
    """Context manager to create a kernel in a subprocess.

    The kernel is shut down when the context exits.

    Returns
    -------
    kernel_client: connected KernelClient instance
    """
    km, kc = start_new_kernel(**kwargs)
    try:
        yield kc
    finally:
        kc.stop_channels()
        km.shutdown_kernel(now=True)

# === NexusCore/openenv\Lib\site-packages\google\protobuf\internal\encoder.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Code for encoding protocol message primitives.

Contains the logic for encoding every logical protocol field type
into one of the 5 physical wire types.

This code is designed to push the Python interpreter's performance to the
limits.

The basic idea is that at startup time, for every field (i.e. every
FieldDescriptor) we construct two functions:  a "sizer" and an "encoder".  The
sizer takes a value of this field's type and computes its byte size.  The
encoder takes a writer function and a value.  It encodes the value into byte
strings and invokes the writer function to write those strings.  Typically the
writer function is the write() method of a BytesIO.

We try to do as much work as possible when constructing the writer and the
sizer rather than when calling them.  In particular:
* We copy any needed global functions to local variables, so that we do not need
  to do costly global table lookups at runtime.
* Similarly, we try to do any attribute lookups at startup time if possible.
* Every field's tag is encoded to bytes at startup, since it can't change at
  runtime.
* Whatever component of the field size we can compute at startup, we do.
* We *avoid* sharing code if doing so would make the code slower and not sharing
  does not burden us too much.  For example, encoders for repeated fields do
  not just call the encoders for singular fields in a loop because this would
  add an extra function call overhead for every loop iteration; instead, we
  manually inline the single-value encoder into the loop.
* If a Python function lacks a return statement, Python actually generates
  instructions to pop the result of the last statement off the stack, push
  None onto the stack, and then return that.  If we really don't care what
  value is returned, then we can save two instructions by returning the
  result of the last statement.  It looks funny but it helps.
* We assume that type and bounds checking has happened at a higher level.
"""

__author__ = 'kenton@google.com (Kenton Varda)'

import struct

from google.protobuf.internal import wire_format


# This will overflow and thus become IEEE-754 "infinity".  We would use
# "float('inf')" but it doesn't work on Windows pre-Python-2.6.
_POS_INF = 1e10000
_NEG_INF = -_POS_INF


def _VarintSize(value):
  """Compute the size of a varint value."""
  if value <= 0x7f: return 1
  if value <= 0x3fff: return 2
  if value <= 0x1fffff: return 3
  if value <= 0xfffffff: return 4
  if value <= 0x7ffffffff: return 5
  if value <= 0x3ffffffffff: return 6
  if value <= 0x1ffffffffffff: return 7
  if value <= 0xffffffffffffff: return 8
  if value <= 0x7fffffffffffffff: return 9
  return 10


def _SignedVarintSize(value):
  """Compute the size of a signed varint value."""
  if value < 0: return 10
  if value <= 0x7f: return 1
  if value <= 0x3fff: return 2
  if value <= 0x1fffff: return 3
  if value <= 0xfffffff: return 4
  if value <= 0x7ffffffff: return 5
  if value <= 0x3ffffffffff: return 6
  if value <= 0x1ffffffffffff: return 7
  if value <= 0xffffffffffffff: return 8
  if value <= 0x7fffffffffffffff: return 9
  return 10


def _TagSize(field_number):
  """Returns the number of bytes required to serialize a tag with this field
  number."""
  # Just pass in type 0, since the type won't affect the tag+type size.
  return _VarintSize(wire_format.PackTag(field_number, 0))


# --------------------------------------------------------------------
# In this section we define some generic sizers.  Each of these functions
# takes parameters specific to a particular field type, e.g. int32 or fixed64.
# It returns another function which in turn takes parameters specific to a
# particular field, e.g. the field number and whether it is repeated or packed.
# Look at the next section to see how these are used.


def _SimpleSizer(compute_value_size):
  """A sizer which uses the function compute_value_size to compute the size of
  each value.  Typically compute_value_size is _VarintSize."""

  def SpecificSizer(field_number, is_repeated, is_packed):
    tag_size = _TagSize(field_number)
    if is_packed:
      local_VarintSize = _VarintSize
      def PackedFieldSize(value):
        result = 0
        for element in value:
          result += compute_value_size(element)
        return result + local_VarintSize(result) + tag_size
      return PackedFieldSize
    elif is_repeated:
      def RepeatedFieldSize(value):
        result = tag_size * len(value)
        for element in value:
          result += compute_value_size(element)
        return result
      return RepeatedFieldSize
    else:
      def FieldSize(value):
        return tag_size + compute_value_size(value)
      return FieldSize

  return SpecificSizer


def _ModifiedSizer(compute_value_size, modify_value):
  """Like SimpleSizer, but modify_value is invoked on each value before it is
  passed to compute_value_size.  modify_value is typically ZigZagEncode."""

  def SpecificSizer(field_number, is_repeated, is_packed):
    tag_size = _TagSize(field_number)
    if is_packed:
      local_VarintSize = _VarintSize
      def PackedFieldSize(value):
        result = 0
        for element in value:
          result += compute_value_size(modify_value(element))
        return result + local_VarintSize(result) + tag_size
      return PackedFieldSize
    elif is_repeated:
      def RepeatedFieldSize(value):
        result = tag_size * len(value)
        for element in value:
          result += compute_value_size(modify_value(element))
        return result
      return RepeatedFieldSize
    else:
      def FieldSize(value):
        return tag_size + compute_value_size(modify_value(value))
      return FieldSize

  return SpecificSizer


def _FixedSizer(value_size):
  """Like _SimpleSizer except for a fixed-size field.  The input is the size
  of one value."""

  def SpecificSizer(field_number, is_repeated, is_packed):
    tag_size = _TagSize(field_number)
    if is_packed:
      local_VarintSize = _VarintSize
      def PackedFieldSize(value):
        result = len(value) * value_size
        return result + local_VarintSize(result) + tag_size
      return PackedFieldSize
    elif is_repeated:
      element_size = value_size + tag_size
      def RepeatedFieldSize(value):
        return len(value) * element_size
      return RepeatedFieldSize
    else:
      field_size = value_size + tag_size
      def FieldSize(value):
        return field_size
      return FieldSize

  return SpecificSizer


# ====================================================================
# Here we declare a sizer constructor for each field type.  Each "sizer
# constructor" is a function that takes (field_number, is_repeated, is_packed)
# as parameters and returns a sizer, which in turn takes a field value as
# a parameter and returns its encoded size.


Int32Sizer = Int64Sizer = EnumSizer = _SimpleSizer(_SignedVarintSize)

UInt32Sizer = UInt64Sizer = _SimpleSizer(_VarintSize)

SInt32Sizer = SInt64Sizer = _ModifiedSizer(
    _SignedVarintSize, wire_format.ZigZagEncode)

Fixed32Sizer = SFixed32Sizer = FloatSizer  = _FixedSizer(4)
Fixed64Sizer = SFixed64Sizer = DoubleSizer = _FixedSizer(8)

BoolSizer = _FixedSizer(1)


def StringSizer(field_number, is_repeated, is_packed):
  """Returns a sizer for a string field."""

  tag_size = _TagSize(field_number)
  local_VarintSize = _VarintSize
  local_len = len
  assert not is_packed
  if is_repeated:
    def RepeatedFieldSize(value):
      result = tag_size * len(value)
      for element in value:
        l = local_len(element.encode('utf-8'))
        result += local_VarintSize(l) + l
      return result
    return RepeatedFieldSize
  else:
    def FieldSize(value):
      l = local_len(value.encode('utf-8'))
      return tag_size + local_VarintSize(l) + l
    return FieldSize


def BytesSizer(field_number, is_repeated, is_packed):
  """Returns a sizer for a bytes field."""

  tag_size = _TagSize(field_number)
  local_VarintSize = _VarintSize
  local_len = len
  assert not is_packed
  if is_repeated:
    def RepeatedFieldSize(value):
      result = tag_size * len(value)
      for element in value:
        l = local_len(element)
        result += local_VarintSize(l) + l
      return result
    return RepeatedFieldSize
  else:
    def FieldSize(value):
      l = local_len(value)
      return tag_size + local_VarintSize(l) + l
    return FieldSize


def GroupSizer(field_number, is_repeated, is_packed):
  """Returns a sizer for a group field."""

  tag_size = _TagSize(field_number) * 2
  assert not is_packed
  if is_repeated:
    def RepeatedFieldSize(value):
      result = tag_size * len(value)
      for element in value:
        result += element.ByteSize()
      return result
    return RepeatedFieldSize
  else:
    def FieldSize(value):
      return tag_size + value.ByteSize()
    return FieldSize


def MessageSizer(field_number, is_repeated, is_packed):
  """Returns a sizer for a message field."""

  tag_size = _TagSize(field_number)
  local_VarintSize = _VarintSize
  assert not is_packed
  if is_repeated:
    def RepeatedFieldSize(value):
      result = tag_size * len(value)
      for element in value:
        l = element.ByteSize()
        result += local_VarintSize(l) + l
      return result
    return RepeatedFieldSize
  else:
    def FieldSize(value):
      l = value.ByteSize()
      return tag_size + local_VarintSize(l) + l
    return FieldSize


# --------------------------------------------------------------------
# MessageSet is special: it needs custom logic to compute its size properly.


def MessageSetItemSizer(field_number):
  """Returns a sizer for extensions of MessageSet.

  The message set message looks like this:
    message MessageSet {
      repeated group Item = 1 {
        required int32 type_id = 2;
        required string message = 3;
      }
    }
  """
  static_size = (_TagSize(1) * 2 + _TagSize(2) + _VarintSize(field_number) +
                 _TagSize(3))
  local_VarintSize = _VarintSize

  def FieldSize(value):
    l = value.ByteSize()
    return static_size + local_VarintSize(l) + l

  return FieldSize


# --------------------------------------------------------------------
# Map is special: it needs custom logic to compute its size properly.


def MapSizer(field_descriptor, is_message_map):
  """Returns a sizer for a map field."""

  # Can't look at field_descriptor.message_type._concrete_class because it may
  # not have been initialized yet.
  message_type = field_descriptor.message_type
  message_sizer = MessageSizer(field_descriptor.number, False, False)

  def FieldSize(map_value):
    total = 0
    for key in map_value:
      value = map_value[key]
      # It's wasteful to create the messages and throw them away one second
      # later since we'll do the same for the actual encode.  But there's not an
      # obvious way to avoid this within the current design without tons of code
      # duplication. For message map, value.ByteSize() should be called to
      # update the status.
      entry_msg = message_type._concrete_class(key=key, value=value)
      total += message_sizer(entry_msg)
      if is_message_map:
        value.ByteSize()
    return total

  return FieldSize

# ====================================================================
# Encoders!


def _VarintEncoder():
  """Return an encoder for a basic varint value (does not include tag)."""

  local_int2byte = struct.Struct('>B').pack

  def EncodeVarint(write, value, unused_deterministic=None):
    bits = value & 0x7f
    value >>= 7
    while value:
      write(local_int2byte(0x80|bits))
      bits = value & 0x7f
      value >>= 7
    return write(local_int2byte(bits))

  return EncodeVarint


def _SignedVarintEncoder():
  """Return an encoder for a basic signed varint value (does not include
  tag)."""

  local_int2byte = struct.Struct('>B').pack

  def EncodeSignedVarint(write, value, unused_deterministic=None):
    if value < 0:
      value += (1 << 64)
    bits = value & 0x7f
    value >>= 7
    while value:
      write(local_int2byte(0x80|bits))
      bits = value & 0x7f
      value >>= 7
    return write(local_int2byte(bits))

  return EncodeSignedVarint


_EncodeVarint = _VarintEncoder()
_EncodeSignedVarint = _SignedVarintEncoder()


def _VarintBytes(value):
  """Encode the given integer as a varint and return the bytes.  This is only
  called at startup time so it doesn't need to be fast."""

  pieces = []
  _EncodeVarint(pieces.append, value, True)
  return b"".join(pieces)


def TagBytes(field_number, wire_type):
  """Encode the given tag and return the bytes.  Only called at startup."""

  return bytes(_VarintBytes(wire_format.PackTag(field_number, wire_type)))

# --------------------------------------------------------------------
# As with sizers (see above), we have a number of common encoder
# implementations.


def _SimpleEncoder(wire_type, encode_value, compute_value_size):
  """Return a constructor for an encoder for fields of a particular type.

  Args:
      wire_type:  The field's wire type, for encoding tags.
      encode_value:  A function which encodes an individual value, e.g.
        _EncodeVarint().
      compute_value_size:  A function which computes the size of an individual
        value, e.g. _VarintSize().
  """

  def SpecificEncoder(field_number, is_repeated, is_packed):
    if is_packed:
      tag_bytes = TagBytes(field_number, wire_format.WIRETYPE_LENGTH_DELIMITED)
      local_EncodeVarint = _EncodeVarint
      def EncodePackedField(write, value, deterministic):
        write(tag_bytes)
        size = 0
        for element in value:
          size += compute_value_size(element)
        local_EncodeVarint(write, size, deterministic)
        for element in value:
          encode_value(write, element, deterministic)
      return EncodePackedField
    elif is_repeated:
      tag_bytes = TagBytes(field_number, wire_type)
      def EncodeRepeatedField(write, value, deterministic):
        for element in value:
          write(tag_bytes)
          encode_value(write, element, deterministic)
      return EncodeRepeatedField
    else:
      tag_bytes = TagBytes(field_number, wire_type)
      def EncodeField(write, value, deterministic):
        write(tag_bytes)
        return encode_value(write, value, deterministic)
      return EncodeField

  return SpecificEncoder


def _ModifiedEncoder(wire_type, encode_value, compute_value_size, modify_value):
  """Like SimpleEncoder but additionally invokes modify_value on every value
  before passing it to encode_value.  Usually modify_value is ZigZagEncode."""

  def SpecificEncoder(field_number, is_repeated, is_packed):
    if is_packed:
      tag_bytes = TagBytes(field_number, wire_format.WIRETYPE_LENGTH_DELIMITED)
      local_EncodeVarint = _EncodeVarint
      def EncodePackedField(write, value, deterministic):
        write(tag_bytes)
        size = 0
        for element in value:
          size += compute_value_size(modify_value(element))
        local_EncodeVarint(write, size, deterministic)
        for element in value:
          encode_value(write, modify_value(element), deterministic)
      return EncodePackedField
    elif is_repeated:
      tag_bytes = TagBytes(field_number, wire_type)
      def EncodeRepeatedField(write, value, deterministic):
        for element in value:
          write(tag_bytes)
          encode_value(write, modify_value(element), deterministic)
      return EncodeRepeatedField
    else:
      tag_bytes = TagBytes(field_number, wire_type)
      def EncodeField(write, value, deterministic):
        write(tag_bytes)
        return encode_value(write, modify_value(value), deterministic)
      return EncodeField

  return SpecificEncoder


def _StructPackEncoder(wire_type, format):
  """Return a constructor for an encoder for a fixed-width field.

  Args:
      wire_type:  The field's wire type, for encoding tags.
      format:  The format string to pass to struct.pack().
  """

  value_size = struct.calcsize(format)

  def SpecificEncoder(field_number, is_repeated, is_packed):
    local_struct_pack = struct.pack
    if is_packed:
      tag_bytes = TagBytes(field_number, wire_format.WIRETYPE_LENGTH_DELIMITED)
      local_EncodeVarint = _EncodeVarint
      def EncodePackedField(write, value, deterministic):
        write(tag_bytes)
        local_EncodeVarint(write, len(value) * value_size, deterministic)
        for element in value:
          write(local_struct_pack(format, element))
      return EncodePackedField
    elif is_repeated:
      tag_bytes = TagBytes(field_number, wire_type)
      def EncodeRepeatedField(write, value, unused_deterministic=None):
        for element in value:
          write(tag_bytes)
          write(local_struct_pack(format, element))
      return EncodeRepeatedField
    else:
      tag_bytes = TagBytes(field_number, wire_type)
      def EncodeField(write, value, unused_deterministic=None):
        write(tag_bytes)
        return write(local_struct_pack(format, value))
      return EncodeField

  return SpecificEncoder


def _FloatingPointEncoder(wire_type, format):
  """Return a constructor for an encoder for float fields.

  This is like StructPackEncoder, but catches errors that may be due to
  passing non-finite floating-point values to struct.pack, and makes a
  second attempt to encode those values.

  Args:
      wire_type:  The field's wire type, for encoding tags.
      format:  The format string to pass to struct.pack().
  """

  value_size = struct.calcsize(format)
  if value_size == 4:
    def EncodeNonFiniteOrRaise(write, value):
      # Remember that the serialized form uses little-endian byte order.
      if value == _POS_INF:
        write(b'\x00\x00\x80\x7F')
      elif value == _NEG_INF:
        write(b'\x00\x00\x80\xFF')
      elif value != value:           # NaN
        write(b'\x00\x00\xC0\x7F')
      else:
        raise
  elif value_size == 8:
    def EncodeNonFiniteOrRaise(write, value):
      if value == _POS_INF:
        write(b'\x00\x00\x00\x00\x00\x00\xF0\x7F')
      elif value == _NEG_INF:
        write(b'\x00\x00\x00\x00\x00\x00\xF0\xFF')
      elif value != value:                         # NaN
        write(b'\x00\x00\x00\x00\x00\x00\xF8\x7F')
      else:
        raise
  else:
    raise ValueError('Can\'t encode floating-point values that are '
                     '%d bytes long (only 4 or 8)' % value_size)

  def SpecificEncoder(field_number, is_repeated, is_packed):
    local_struct_pack = struct.pack
    if is_packed:
      tag_bytes = TagBytes(field_number, wire_format.WIRETYPE_LENGTH_DELIMITED)
      local_EncodeVarint = _EncodeVarint
      def EncodePackedField(write, value, deterministic):
        write(tag_bytes)
        local_EncodeVarint(write, len(value) * value_size, deterministic)
        for element in value:
          # This try/except block is going to be faster than any code that
          # we could write to check whether element is finite.
          try:
            write(local_struct_pack(format, element))
          except SystemError:
            EncodeNonFiniteOrRaise(write, element)
      return EncodePackedField
    elif is_repeated:
      tag_bytes = TagBytes(field_number, wire_type)
      def EncodeRepeatedField(write, value, unused_deterministic=None):
        for element in value:
          write(tag_bytes)
          try:
            write(local_struct_pack(format, element))
          except SystemError:
            EncodeNonFiniteOrRaise(write, element)
      return EncodeRepeatedField
    else:
      tag_bytes = TagBytes(field_number, wire_type)
      def EncodeField(write, value, unused_deterministic=None):
        write(tag_bytes)
        try:
          write(local_struct_pack(format, value))
        except SystemError:
          EncodeNonFiniteOrRaise(write, value)
      return EncodeField

  return SpecificEncoder


# ====================================================================
# Here we declare an encoder constructor for each field type.  These work
# very similarly to sizer constructors, described earlier.


Int32Encoder = Int64Encoder = EnumEncoder = _SimpleEncoder(
    wire_format.WIRETYPE_VARINT, _EncodeSignedVarint, _SignedVarintSize)

UInt32Encoder = UInt64Encoder = _SimpleEncoder(
    wire_format.WIRETYPE_VARINT, _EncodeVarint, _VarintSize)

SInt32Encoder = SInt64Encoder = _ModifiedEncoder(
    wire_format.WIRETYPE_VARINT, _EncodeVarint, _VarintSize,
    wire_format.ZigZagEncode)

# Note that Python conveniently guarantees that when using the '<' prefix on
# formats, they will also have the same size across all platforms (as opposed
# to without the prefix, where their sizes depend on the C compiler's basic
# type sizes).
Fixed32Encoder  = _StructPackEncoder(wire_format.WIRETYPE_FIXED32, '<I')
Fixed64Encoder  = _StructPackEncoder(wire_format.WIRETYPE_FIXED64, '<Q')
SFixed32Encoder = _StructPackEncoder(wire_format.WIRETYPE_FIXED32, '<i')
SFixed64Encoder = _StructPackEncoder(wire_format.WIRETYPE_FIXED64, '<q')
FloatEncoder    = _FloatingPointEncoder(wire_format.WIRETYPE_FIXED32, '<f')
DoubleEncoder   = _FloatingPointEncoder(wire_format.WIRETYPE_FIXED64, '<d')


def BoolEncoder(field_number, is_repeated, is_packed):
  """Returns an encoder for a boolean field."""

  false_byte = b'\x00'
  true_byte = b'\x01'
  if is_packed:
    tag_bytes = TagBytes(field_number, wire_format.WIRETYPE_LENGTH_DELIMITED)
    local_EncodeVarint = _EncodeVarint
    def EncodePackedField(write, value, deterministic):
      write(tag_bytes)
      local_EncodeVarint(write, len(value), deterministic)
      for element in value:
        if element:
          write(true_byte)
        else:
          write(false_byte)
    return EncodePackedField
  elif is_repeated:
    tag_bytes = TagBytes(field_number, wire_format.WIRETYPE_VARINT)
    def EncodeRepeatedField(write, value, unused_deterministic=None):
      for element in value:
        write(tag_bytes)
        if element:
          write(true_byte)
        else:
          write(false_byte)
    return EncodeRepeatedField
  else:
    tag_bytes = TagBytes(field_number, wire_format.WIRETYPE_VARINT)
    def EncodeField(write, value, unused_deterministic=None):
      write(tag_bytes)
      if value:
        return write(true_byte)
      return write(false_byte)
    return EncodeField


def StringEncoder(field_number, is_repeated, is_packed):
  """Returns an encoder for a string field."""

  tag = TagBytes(field_number, wire_format.WIRETYPE_LENGTH_DELIMITED)
  local_EncodeVarint = _EncodeVarint
  local_len = len
  assert not is_packed
  if is_repeated:
    def EncodeRepeatedField(write, value, deterministic):
      for element in value:
        encoded = element.encode('utf-8')
        write(tag)
        local_EncodeVarint(write, local_len(encoded), deterministic)
        write(encoded)
    return EncodeRepeatedField
  else:
    def EncodeField(write, value, deterministic):
      encoded = value.encode('utf-8')
      write(tag)
      local_EncodeVarint(write, local_len(encoded), deterministic)
      return write(encoded)
    return EncodeField


def BytesEncoder(field_number, is_repeated, is_packed):
  """Returns an encoder for a bytes field."""

  tag = TagBytes(field_number, wire_format.WIRETYPE_LENGTH_DELIMITED)
  local_EncodeVarint = _EncodeVarint
  local_len = len
  assert not is_packed
  if is_repeated:
    def EncodeRepeatedField(write, value, deterministic):
      for element in value:
        write(tag)
        local_EncodeVarint(write, local_len(element), deterministic)
        write(element)
    return EncodeRepeatedField
  else:
    def EncodeField(write, value, deterministic):
      write(tag)
      local_EncodeVarint(write, local_len(value), deterministic)
      return write(value)
    return EncodeField


def GroupEncoder(field_number, is_repeated, is_packed):
  """Returns an encoder for a group field."""

  start_tag = TagBytes(field_number, wire_format.WIRETYPE_START_GROUP)
  end_tag = TagBytes(field_number, wire_format.WIRETYPE_END_GROUP)
  assert not is_packed
  if is_repeated:
    def EncodeRepeatedField(write, value, deterministic):
      for element in value:
        write(start_tag)
        element._InternalSerialize(write, deterministic)
        write(end_tag)
    return EncodeRepeatedField
  else:
    def EncodeField(write, value, deterministic):
      write(start_tag)
      value._InternalSerialize(write, deterministic)
      return write(end_tag)
    return EncodeField


def MessageEncoder(field_number, is_repeated, is_packed):
  """Returns an encoder for a message field."""

  tag = TagBytes(field_number, wire_format.WIRETYPE_LENGTH_DELIMITED)
  local_EncodeVarint = _EncodeVarint
  assert not is_packed
  if is_repeated:
    def EncodeRepeatedField(write, value, deterministic):
      for element in value:
        write(tag)
        local_EncodeVarint(write, element.ByteSize(), deterministic)
        element._InternalSerialize(write, deterministic)
    return EncodeRepeatedField
  else:
    def EncodeField(write, value, deterministic):
      write(tag)
      local_EncodeVarint(write, value.ByteSize(), deterministic)
      return value._InternalSerialize(write, deterministic)
    return EncodeField


# --------------------------------------------------------------------
# As before, MessageSet is special.


def MessageSetItemEncoder(field_number):
  """Encoder for extensions of MessageSet.

  The message set message looks like this:
    message MessageSet {
      repeated group Item = 1 {
        required int32 type_id = 2;
        required string message = 3;
      }
    }
  """
  start_bytes = b"".join([
      TagBytes(1, wire_format.WIRETYPE_START_GROUP),
      TagBytes(2, wire_format.WIRETYPE_VARINT),
      _VarintBytes(field_number),
      TagBytes(3, wire_format.WIRETYPE_LENGTH_DELIMITED)])
  end_bytes = TagBytes(1, wire_format.WIRETYPE_END_GROUP)
  local_EncodeVarint = _EncodeVarint

  def EncodeField(write, value, deterministic):
    write(start_bytes)
    local_EncodeVarint(write, value.ByteSize(), deterministic)
    value._InternalSerialize(write, deterministic)
    return write(end_bytes)

  return EncodeField


# --------------------------------------------------------------------
# As before, Map is special.


def MapEncoder(field_descriptor):
  """Encoder for extensions of MessageSet.

  Maps always have a wire format like this:
    message MapEntry {
      key_type key = 1;
      value_type value = 2;
    }
    repeated MapEntry map = N;
  """
  # Can't look at field_descriptor.message_type._concrete_class because it may
  # not have been initialized yet.
  message_type = field_descriptor.message_type
  encode_message = MessageEncoder(field_descriptor.number, False, False)

  def EncodeField(write, value, deterministic):
    value_keys = sorted(value.keys()) if deterministic else value
    for key in value_keys:
      entry_msg = message_type._concrete_class(key=key, value=value[key])
      encode_message(write, entry_msg, deterministic)

  return EncodeField

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\utils.py ===
import keyword
import warnings
import weakref
from collections import OrderedDict, defaultdict, deque
from copy import deepcopy
from itertools import islice, zip_longest
from types import BuiltinFunctionType, CodeType, FunctionType, GeneratorType, LambdaType, ModuleType
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Callable,
    Collection,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    Mapping,
    NoReturn,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from typing_extensions import Annotated

from pydantic.v1.errors import ConfigError
from pydantic.v1.typing import (
    NoneType,
    WithArgsTypes,
    all_literal_values,
    display_as_type,
    get_args,
    get_origin,
    is_literal_type,
    is_union,
)
from pydantic.v1.version import version_info

if TYPE_CHECKING:
    from inspect import Signature
    from pathlib import Path

    from pydantic.v1.config import BaseConfig
    from pydantic.v1.dataclasses import Dataclass
    from pydantic.v1.fields import ModelField
    from pydantic.v1.main import BaseModel
    from pydantic.v1.typing import AbstractSetIntStr, DictIntStrAny, IntStr, MappingIntStrAny, ReprArgs

    RichReprResult = Iterable[Union[Any, Tuple[Any], Tuple[str, Any], Tuple[str, Any, Any]]]

__all__ = (
    'import_string',
    'sequence_like',
    'validate_field_name',
    'lenient_isinstance',
    'lenient_issubclass',
    'in_ipython',
    'is_valid_identifier',
    'deep_update',
    'update_not_none',
    'almost_equal_floats',
    'get_model',
    'to_camel',
    'to_lower_camel',
    'is_valid_field',
    'smart_deepcopy',
    'PyObjectStr',
    'Representation',
    'GetterDict',
    'ValueItems',
    'version_info',  # required here to match behaviour in v1.3
    'ClassAttribute',
    'path_type',
    'ROOT_KEY',
    'get_unique_discriminator_alias',
    'get_discriminator_alias_and_values',
    'DUNDER_ATTRIBUTES',
)

ROOT_KEY = '__root__'
# these are types that are returned unchanged by deepcopy
IMMUTABLE_NON_COLLECTIONS_TYPES: Set[Type[Any]] = {
    int,
    float,
    complex,
    str,
    bool,
    bytes,
    type,
    NoneType,
    FunctionType,
    BuiltinFunctionType,
    LambdaType,
    weakref.ref,
    CodeType,
    # note: including ModuleType will differ from behaviour of deepcopy by not producing error.
    # It might be not a good idea in general, but considering that this function used only internally
    # against default values of fields, this will allow to actually have a field with module as default value
    ModuleType,
    NotImplemented.__class__,
    Ellipsis.__class__,
}

# these are types that if empty, might be copied with simple copy() instead of deepcopy()
BUILTIN_COLLECTIONS: Set[Type[Any]] = {
    list,
    set,
    tuple,
    frozenset,
    dict,
    OrderedDict,
    defaultdict,
    deque,
}


def import_string(dotted_path: str) -> Any:
    """
    Stolen approximately from django. Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import fails.
    """
    from importlib import import_module

    try:
        module_path, class_name = dotted_path.strip(' ').rsplit('.', 1)
    except ValueError as e:
        raise ImportError(f'"{dotted_path}" doesn\'t look like a module path') from e

    module = import_module(module_path)
    try:
        return getattr(module, class_name)
    except AttributeError as e:
        raise ImportError(f'Module "{module_path}" does not define a "{class_name}" attribute') from e


def truncate(v: Union[str], *, max_len: int = 80) -> str:
    """
    Truncate a value and add a unicode ellipsis (three dots) to the end if it was too long
    """
    warnings.warn('`truncate` is no-longer used by pydantic and is deprecated', DeprecationWarning)
    if isinstance(v, str) and len(v) > (max_len - 2):
        # -3 so quote + string + … + quote has correct length
        return (v[: (max_len - 3)] + '…').__repr__()
    try:
        v = v.__repr__()
    except TypeError:
        v = v.__class__.__repr__(v)  # in case v is a type
    if len(v) > max_len:
        v = v[: max_len - 1] + '…'
    return v


def sequence_like(v: Any) -> bool:
    return isinstance(v, (list, tuple, set, frozenset, GeneratorType, deque))


def validate_field_name(bases: Iterable[Type[Any]], field_name: str) -> None:
    """
    Ensure that the field's name does not shadow an existing attribute of the model.
    """
    for base in bases:
        if getattr(base, field_name, None):
            raise NameError(
                f'Field name "{field_name}" shadows a BaseModel attribute; '
                f'use a different field name with "alias=\'{field_name}\'".'
            )


def lenient_isinstance(o: Any, class_or_tuple: Union[Type[Any], Tuple[Type[Any], ...], None]) -> bool:
    try:
        return isinstance(o, class_or_tuple)  # type: ignore[arg-type]
    except TypeError:
        return False


def lenient_issubclass(cls: Any, class_or_tuple: Union[Type[Any], Tuple[Type[Any], ...], None]) -> bool:
    try:
        return isinstance(cls, type) and issubclass(cls, class_or_tuple)  # type: ignore[arg-type]
    except TypeError:
        if isinstance(cls, WithArgsTypes):
            return False
        raise  # pragma: no cover


def in_ipython() -> bool:
    """
    Check whether we're in an ipython environment, including jupyter notebooks.
    """
    try:
        eval('__IPYTHON__')
    except NameError:
        return False
    else:  # pragma: no cover
        return True


def is_valid_identifier(identifier: str) -> bool:
    """
    Checks that a string is a valid identifier and not a Python keyword.
    :param identifier: The identifier to test.
    :return: True if the identifier is valid.
    """
    return identifier.isidentifier() and not keyword.iskeyword(identifier)


KeyType = TypeVar('KeyType')


def deep_update(mapping: Dict[KeyType, Any], *updating_mappings: Dict[KeyType, Any]) -> Dict[KeyType, Any]:
    updated_mapping = mapping.copy()
    for updating_mapping in updating_mappings:
        for k, v in updating_mapping.items():
            if k in updated_mapping and isinstance(updated_mapping[k], dict) and isinstance(v, dict):
                updated_mapping[k] = deep_update(updated_mapping[k], v)
            else:
                updated_mapping[k] = v
    return updated_mapping


def update_not_none(mapping: Dict[Any, Any], **update: Any) -> None:
    mapping.update({k: v for k, v in update.items() if v is not None})


def almost_equal_floats(value_1: float, value_2: float, *, delta: float = 1e-8) -> bool:
    """
    Return True if two floats are almost equal
    """
    return abs(value_1 - value_2) <= delta


def generate_model_signature(
    init: Callable[..., None], fields: Dict[str, 'ModelField'], config: Type['BaseConfig']
) -> 'Signature':
    """
    Generate signature for model based on its fields
    """
    from inspect import Parameter, Signature, signature

    from pydantic.v1.config import Extra

    present_params = signature(init).parameters.values()
    merged_params: Dict[str, Parameter] = {}
    var_kw = None
    use_var_kw = False

    for param in islice(present_params, 1, None):  # skip self arg
        if param.kind is param.VAR_KEYWORD:
            var_kw = param
            continue
        merged_params[param.name] = param

    if var_kw:  # if custom init has no var_kw, fields which are not declared in it cannot be passed through
        allow_names = config.allow_population_by_field_name
        for field_name, field in fields.items():
            param_name = field.alias
            if field_name in merged_params or param_name in merged_params:
                continue
            elif not is_valid_identifier(param_name):
                if allow_names and is_valid_identifier(field_name):
                    param_name = field_name
                else:
                    use_var_kw = True
                    continue

            # TODO: replace annotation with actual expected types once #1055 solved
            kwargs = {'default': field.default} if not field.required else {}
            merged_params[param_name] = Parameter(
                param_name, Parameter.KEYWORD_ONLY, annotation=field.annotation, **kwargs
            )

    if config.extra is Extra.allow:
        use_var_kw = True

    if var_kw and use_var_kw:
        # Make sure the parameter for extra kwargs
        # does not have the same name as a field
        default_model_signature = [
            ('__pydantic_self__', Parameter.POSITIONAL_OR_KEYWORD),
            ('data', Parameter.VAR_KEYWORD),
        ]
        if [(p.name, p.kind) for p in present_params] == default_model_signature:
            # if this is the standard model signature, use extra_data as the extra args name
            var_kw_name = 'extra_data'
        else:
            # else start from var_kw
            var_kw_name = var_kw.name

        # generate a name that's definitely unique
        while var_kw_name in fields:
            var_kw_name += '_'
        merged_params[var_kw_name] = var_kw.replace(name=var_kw_name)

    return Signature(parameters=list(merged_params.values()), return_annotation=None)


def get_model(obj: Union[Type['BaseModel'], Type['Dataclass']]) -> Type['BaseModel']:
    from pydantic.v1.main import BaseModel

    try:
        model_cls = obj.__pydantic_model__  # type: ignore
    except AttributeError:
        model_cls = obj

    if not issubclass(model_cls, BaseModel):
        raise TypeError('Unsupported type, must be either BaseModel or dataclass')
    return model_cls


def to_camel(string: str) -> str:
    return ''.join(word.capitalize() for word in string.split('_'))


def to_lower_camel(string: str) -> str:
    if len(string) >= 1:
        pascal_string = to_camel(string)
        return pascal_string[0].lower() + pascal_string[1:]
    return string.lower()


T = TypeVar('T')


def unique_list(
    input_list: Union[List[T], Tuple[T, ...]],
    *,
    name_factory: Callable[[T], str] = str,
) -> List[T]:
    """
    Make a list unique while maintaining order.
    We update the list if another one with the same name is set
    (e.g. root validator overridden in subclass)
    """
    result: List[T] = []
    result_names: List[str] = []
    for v in input_list:
        v_name = name_factory(v)
        if v_name not in result_names:
            result_names.append(v_name)
            result.append(v)
        else:
            result[result_names.index(v_name)] = v

    return result


class PyObjectStr(str):
    """
    String class where repr doesn't include quotes. Useful with Representation when you want to return a string
    representation of something that valid (or pseudo-valid) python.
    """

    def __repr__(self) -> str:
        return str(self)


class Representation:
    """
    Mixin to provide __str__, __repr__, and __pretty__ methods. See #884 for more details.

    __pretty__ is used by [devtools](https://python-devtools.helpmanual.io/) to provide human readable representations
    of objects.
    """

    __slots__: Tuple[str, ...] = tuple()

    def __repr_args__(self) -> 'ReprArgs':
        """
        Returns the attributes to show in __str__, __repr__, and __pretty__ this is generally overridden.

        Can either return:
        * name - value pairs, e.g.: `[('foo_name', 'foo'), ('bar_name', ['b', 'a', 'r'])]`
        * or, just values, e.g.: `[(None, 'foo'), (None, ['b', 'a', 'r'])]`
        """
        attrs = ((s, getattr(self, s)) for s in self.__slots__)
        return [(a, v) for a, v in attrs if v is not None]

    def __repr_name__(self) -> str:
        """
        Name of the instance's class, used in __repr__.
        """
        return self.__class__.__name__

    def __repr_str__(self, join_str: str) -> str:
        return join_str.join(repr(v) if a is None else f'{a}={v!r}' for a, v in self.__repr_args__())

    def __pretty__(self, fmt: Callable[[Any], Any], **kwargs: Any) -> Generator[Any, None, None]:
        """
        Used by devtools (https://python-devtools.helpmanual.io/) to provide a human readable representations of objects
        """
        yield self.__repr_name__() + '('
        yield 1
        for name, value in self.__repr_args__():
            if name is not None:
                yield name + '='
            yield fmt(value)
            yield ','
            yield 0
        yield -1
        yield ')'

    def __str__(self) -> str:
        return self.__repr_str__(' ')

    def __repr__(self) -> str:
        return f'{self.__repr_name__()}({self.__repr_str__(", ")})'

    def __rich_repr__(self) -> 'RichReprResult':
        """Get fields for Rich library"""
        for name, field_repr in self.__repr_args__():
            if name is None:
                yield field_repr
            else:
                yield name, field_repr


class GetterDict(Representation):
    """
    Hack to make object's smell just enough like dicts for validate_model.

    We can't inherit from Mapping[str, Any] because it upsets cython so we have to implement all methods ourselves.
    """

    __slots__ = ('_obj',)

    def __init__(self, obj: Any):
        self._obj = obj

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self._obj, key)
        except AttributeError as e:
            raise KeyError(key) from e

    def get(self, key: Any, default: Any = None) -> Any:
        return getattr(self._obj, key, default)

    def extra_keys(self) -> Set[Any]:
        """
        We don't want to get any other attributes of obj if the model didn't explicitly ask for them
        """
        return set()

    def keys(self) -> List[Any]:
        """
        Keys of the pseudo dictionary, uses a list not set so order information can be maintained like python
        dictionaries.
        """
        return list(self)

    def values(self) -> List[Any]:
        return [self[k] for k in self]

    def items(self) -> Iterator[Tuple[str, Any]]:
        for k in self:
            yield k, self.get(k)

    def __iter__(self) -> Iterator[str]:
        for name in dir(self._obj):
            if not name.startswith('_'):
                yield name

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __contains__(self, item: Any) -> bool:
        return item in self.keys()

    def __eq__(self, other: Any) -> bool:
        return dict(self) == dict(other.items())

    def __repr_args__(self) -> 'ReprArgs':
        return [(None, dict(self))]

    def __repr_name__(self) -> str:
        return f'GetterDict[{display_as_type(self._obj)}]'


class ValueItems(Representation):
    """
    Class for more convenient calculation of excluded or included fields on values.
    """

    __slots__ = ('_items', '_type')

    def __init__(self, value: Any, items: Union['AbstractSetIntStr', 'MappingIntStrAny']) -> None:
        items = self._coerce_items(items)

        if isinstance(value, (list, tuple)):
            items = self._normalize_indexes(items, len(value))

        self._items: 'MappingIntStrAny' = items

    def is_excluded(self, item: Any) -> bool:
        """
        Check if item is fully excluded.

        :param item: key or index of a value
        """
        return self.is_true(self._items.get(item))

    def is_included(self, item: Any) -> bool:
        """
        Check if value is contained in self._items

        :param item: key or index of value
        """
        return item in self._items

    def for_element(self, e: 'IntStr') -> Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']]:
        """
        :param e: key or index of element on value
        :return: raw values for element if self._items is dict and contain needed element
        """

        item = self._items.get(e)
        return item if not self.is_true(item) else None

    def _normalize_indexes(self, items: 'MappingIntStrAny', v_length: int) -> 'DictIntStrAny':
        """
        :param items: dict or set of indexes which will be normalized
        :param v_length: length of sequence indexes of which will be

        >>> self._normalize_indexes({0: True, -2: True, -1: True}, 4)
        {0: True, 2: True, 3: True}
        >>> self._normalize_indexes({'__all__': True}, 4)
        {0: True, 1: True, 2: True, 3: True}
        """

        normalized_items: 'DictIntStrAny' = {}
        all_items = None
        for i, v in items.items():
            if not (isinstance(v, Mapping) or isinstance(v, AbstractSet) or self.is_true(v)):
                raise TypeError(f'Unexpected type of exclude value for index "{i}" {v.__class__}')
            if i == '__all__':
                all_items = self._coerce_value(v)
                continue
            if not isinstance(i, int):
                raise TypeError(
                    'Excluding fields from a sequence of sub-models or dicts must be performed index-wise: '
                    'expected integer keys or keyword "__all__"'
                )
            normalized_i = v_length + i if i < 0 else i
            normalized_items[normalized_i] = self.merge(v, normalized_items.get(normalized_i))

        if not all_items:
            return normalized_items
        if self.is_true(all_items):
            for i in range(v_length):
                normalized_items.setdefault(i, ...)
            return normalized_items
        for i in range(v_length):
            normalized_item = normalized_items.setdefault(i, {})
            if not self.is_true(normalized_item):
                normalized_items[i] = self.merge(all_items, normalized_item)
        return normalized_items

    @classmethod
    def merge(cls, base: Any, override: Any, intersect: bool = False) -> Any:
        """
        Merge a ``base`` item with an ``override`` item.

        Both ``base`` and ``override`` are converted to dictionaries if possible.
        Sets are converted to dictionaries with the sets entries as keys and
        Ellipsis as values.

        Each key-value pair existing in ``base`` is merged with ``override``,
        while the rest of the key-value pairs are updated recursively with this function.

        Merging takes place based on the "union" of keys if ``intersect`` is
        set to ``False`` (default) and on the intersection of keys if
        ``intersect`` is set to ``True``.
        """
        override = cls._coerce_value(override)
        base = cls._coerce_value(base)
        if override is None:
            return base
        if cls.is_true(base) or base is None:
            return override
        if cls.is_true(override):
            return base if intersect else override

        # intersection or union of keys while preserving ordering:
        if intersect:
            merge_keys = [k for k in base if k in override] + [k for k in override if k in base]
        else:
            merge_keys = list(base) + [k for k in override if k not in base]

        merged: 'DictIntStrAny' = {}
        for k in merge_keys:
            merged_item = cls.merge(base.get(k), override.get(k), intersect=intersect)
            if merged_item is not None:
                merged[k] = merged_item

        return merged

    @staticmethod
    def _coerce_items(items: Union['AbstractSetIntStr', 'MappingIntStrAny']) -> 'MappingIntStrAny':
        if isinstance(items, Mapping):
            pass
        elif isinstance(items, AbstractSet):
            items = dict.fromkeys(items, ...)
        else:
            class_name = getattr(items, '__class__', '???')
            assert_never(
                items,
                f'Unexpected type of exclude value {class_name}',
            )
        return items

    @classmethod
    def _coerce_value(cls, value: Any) -> Any:
        if value is None or cls.is_true(value):
            return value
        return cls._coerce_items(value)

    @staticmethod
    def is_true(v: Any) -> bool:
        return v is True or v is ...

    def __repr_args__(self) -> 'ReprArgs':
        return [(None, self._items)]


class ClassAttribute:
    """
    Hide class attribute from its instances
    """

    __slots__ = (
        'name',
        'value',
    )

    def __init__(self, name: str, value: Any) -> None:
        self.name = name
        self.value = value

    def __get__(self, instance: Any, owner: Type[Any]) -> None:
        if instance is None:
            return self.value
        raise AttributeError(f'{self.name!r} attribute of {owner.__name__!r} is class-only')


path_types = {
    'is_dir': 'directory',
    'is_file': 'file',
    'is_mount': 'mount point',
    'is_symlink': 'symlink',
    'is_block_device': 'block device',
    'is_char_device': 'char device',
    'is_fifo': 'FIFO',
    'is_socket': 'socket',
}


def path_type(p: 'Path') -> str:
    """
    Find out what sort of thing a path is.
    """
    assert p.exists(), 'path does not exist'
    for method, name in path_types.items():
        if getattr(p, method)():
            return name

    return 'unknown'


Obj = TypeVar('Obj')


def smart_deepcopy(obj: Obj) -> Obj:
    """
    Return type as is for immutable built-in types
    Use obj.copy() for built-in empty collections
    Use copy.deepcopy() for non-empty collections and unknown objects
    """

    obj_type = obj.__class__
    if obj_type in IMMUTABLE_NON_COLLECTIONS_TYPES:
        return obj  # fastest case: obj is immutable and not collection therefore will not be copied anyway
    try:
        if not obj and obj_type in BUILTIN_COLLECTIONS:
            # faster way for empty collections, no need to copy its members
            return obj if obj_type is tuple else obj.copy()  # type: ignore  # tuple doesn't have copy method
    except (TypeError, ValueError, RuntimeError):
        # do we really dare to catch ALL errors? Seems a bit risky
        pass

    return deepcopy(obj)  # slowest way when we actually might need a deepcopy


def is_valid_field(name: str) -> bool:
    if not name.startswith('_'):
        return True
    return ROOT_KEY == name


DUNDER_ATTRIBUTES = {
    '__annotations__',
    '__classcell__',
    '__doc__',
    '__module__',
    '__orig_bases__',
    '__orig_class__',
    '__qualname__',
    '__firstlineno__',
    '__static_attributes__',
}


def is_valid_private_name(name: str) -> bool:
    return not is_valid_field(name) and name not in DUNDER_ATTRIBUTES


_EMPTY = object()


def all_identical(left: Iterable[Any], right: Iterable[Any]) -> bool:
    """
    Check that the items of `left` are the same objects as those in `right`.

    >>> a, b = object(), object()
    >>> all_identical([a, b, a], [a, b, a])
    True
    >>> all_identical([a, b, [a]], [a, b, [a]])  # new list object, while "equal" is not "identical"
    False
    """
    for left_item, right_item in zip_longest(left, right, fillvalue=_EMPTY):
        if left_item is not right_item:
            return False
    return True


def assert_never(obj: NoReturn, msg: str) -> NoReturn:
    """
    Helper to make sure that we have covered all possible types.

    This is mostly useful for ``mypy``, docs:
    https://mypy.readthedocs.io/en/latest/literal_types.html#exhaustive-checks
    """
    raise TypeError(msg)


def get_unique_discriminator_alias(all_aliases: Collection[str], discriminator_key: str) -> str:
    """Validate that all aliases are the same and if that's the case return the alias"""
    unique_aliases = set(all_aliases)
    if len(unique_aliases) > 1:
        raise ConfigError(
            f'Aliases for discriminator {discriminator_key!r} must be the same (got {", ".join(sorted(all_aliases))})'
        )
    return unique_aliases.pop()


def get_discriminator_alias_and_values(tp: Any, discriminator_key: str) -> Tuple[str, Tuple[str, ...]]:
    """
    Get alias and all valid values in the `Literal` type of the discriminator field
    `tp` can be a `BaseModel` class or directly an `Annotated` `Union` of many.
    """
    is_root_model = getattr(tp, '__custom_root_type__', False)

    if get_origin(tp) is Annotated:
        tp = get_args(tp)[0]

    if hasattr(tp, '__pydantic_model__'):
        tp = tp.__pydantic_model__

    if is_union(get_origin(tp)):
        alias, all_values = _get_union_alias_and_all_values(tp, discriminator_key)
        return alias, tuple(v for values in all_values for v in values)
    elif is_root_model:
        union_type = tp.__fields__[ROOT_KEY].type_
        alias, all_values = _get_union_alias_and_all_values(union_type, discriminator_key)

        if len(set(all_values)) > 1:
            raise ConfigError(
                f'Field {discriminator_key!r} is not the same for all submodels of {display_as_type(tp)!r}'
            )

        return alias, all_values[0]

    else:
        try:
            t_discriminator_type = tp.__fields__[discriminator_key].type_
        except AttributeError as e:
            raise TypeError(f'Type {tp.__name__!r} is not a valid `BaseModel` or `dataclass`') from e
        except KeyError as e:
            raise ConfigError(f'Model {tp.__name__!r} needs a discriminator field for key {discriminator_key!r}') from e

        if not is_literal_type(t_discriminator_type):
            raise ConfigError(f'Field {discriminator_key!r} of model {tp.__name__!r} needs to be a `Literal`')

        return tp.__fields__[discriminator_key].alias, all_literal_values(t_discriminator_type)


def _get_union_alias_and_all_values(
    union_type: Type[Any], discriminator_key: str
) -> Tuple[str, Tuple[Tuple[str, ...], ...]]:
    zipped_aliases_values = [get_discriminator_alias_and_values(t, discriminator_key) for t in get_args(union_type)]
    # unzip: [('alias_a',('v1', 'v2)), ('alias_b', ('v3',))] => [('alias_a', 'alias_b'), (('v1', 'v2'), ('v3',))]
    all_aliases, all_values = zip(*zipped_aliases_values)
    return get_unique_discriminator_alias(all_aliases, discriminator_key), all_values

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_process_net_command.py ===
import json
import os
import sys
import traceback

from _pydev_bundle import pydev_log
from _pydev_bundle.pydev_log import exception as pydev_log_exception
from _pydevd_bundle import pydevd_traceproperty, pydevd_dont_trace, pydevd_utils
from _pydevd_bundle.pydevd_additional_thread_info import set_additional_thread_info
from _pydevd_bundle.pydevd_breakpoints import get_exception_class
from _pydevd_bundle.pydevd_comm import (
    InternalEvaluateConsoleExpression,
    InternalConsoleGetCompletions,
    InternalRunCustomOperation,
    internal_get_next_statement_targets,
    internal_get_smart_step_into_variants,
)
from _pydevd_bundle.pydevd_constants import NEXT_VALUE_SEPARATOR, IS_WINDOWS, NULL
from _pydevd_bundle.pydevd_comm_constants import ID_TO_MEANING, CMD_EXEC_EXPRESSION, CMD_AUTHENTICATE
from _pydevd_bundle.pydevd_api import PyDevdAPI
from io import StringIO
from _pydevd_bundle.pydevd_net_command import NetCommand
from _pydevd_bundle.pydevd_thread_lifecycle import pydevd_find_thread_by_id
import pydevd_file_utils


class _PyDevCommandProcessor(object):
    def __init__(self):
        self.api = PyDevdAPI()

    def process_net_command(self, py_db, cmd_id, seq, text):
        """Processes a command received from the Java side

        @param cmd_id: the id of the command
        @param seq: the sequence of the command
        @param text: the text received in the command
        """

        # We can only proceed if the client is already authenticated or if it's the
        # command to authenticate.
        if cmd_id != CMD_AUTHENTICATE and not py_db.authentication.is_authenticated():
            cmd = py_db.cmd_factory.make_error_message(seq, "Client not authenticated.")
            py_db.writer.add_command(cmd)
            return

        meaning = ID_TO_MEANING[str(cmd_id)]

        # print('Handling %s (%s)' % (meaning, text))

        method_name = meaning.lower()

        on_command = getattr(self, method_name.lower(), None)
        if on_command is None:
            # I have no idea what this is all about
            cmd = py_db.cmd_factory.make_error_message(seq, "unexpected command " + str(cmd_id))
            py_db.writer.add_command(cmd)
            return

        lock = py_db._main_lock
        if method_name == "cmd_thread_dump_to_stderr":
            # We can skip the main debugger locks for cases where we know it's not needed.
            lock = NULL

        with lock:
            try:
                cmd = on_command(py_db, cmd_id, seq, text)
                if cmd is not None:
                    py_db.writer.add_command(cmd)
            except:
                if traceback is not None and sys is not None and pydev_log_exception is not None:
                    pydev_log_exception()

                    stream = StringIO()
                    traceback.print_exc(file=stream)
                    cmd = py_db.cmd_factory.make_error_message(
                        seq,
                        "Unexpected exception in process_net_command.\nInitial params: %s. Exception: %s"
                        % (((cmd_id, seq, text), stream.getvalue())),
                    )
                    if cmd is not None:
                        py_db.writer.add_command(cmd)

    def cmd_authenticate(self, py_db, cmd_id, seq, text):
        access_token = text
        py_db.authentication.login(access_token)
        if py_db.authentication.is_authenticated():
            return NetCommand(cmd_id, seq, py_db.authentication.client_access_token)

        return py_db.cmd_factory.make_error_message(seq, "Client not authenticated.")

    def cmd_run(self, py_db, cmd_id, seq, text):
        return self.api.run(py_db)

    def cmd_list_threads(self, py_db, cmd_id, seq, text):
        return self.api.list_threads(py_db, seq)

    def cmd_get_completions(self, py_db, cmd_id, seq, text):
        # we received some command to get a variable
        # the text is: thread_id\tframe_id\tactivation token
        thread_id, frame_id, _scope, act_tok = text.split("\t", 3)

        return self.api.request_completions(py_db, seq, thread_id, frame_id, act_tok)

    def cmd_get_thread_stack(self, py_db, cmd_id, seq, text):
        # Receives a thread_id and a given timeout, which is the time we should
        # wait to the provide the stack if a given thread is still not suspended.
        if "\t" in text:
            thread_id, timeout = text.split("\t")
            timeout = float(timeout)
        else:
            thread_id = text
            timeout = 0.5  # Default timeout is .5 seconds

        return self.api.request_stack(py_db, seq, thread_id, fmt={}, timeout=timeout)

    def cmd_set_protocol(self, py_db, cmd_id, seq, text):
        return self.api.set_protocol(py_db, seq, text.strip())

    def cmd_thread_suspend(self, py_db, cmd_id, seq, text):
        return self.api.request_suspend_thread(py_db, text.strip())

    def cmd_version(self, py_db, cmd_id, seq, text):
        # Default based on server process (although ideally the IDE should
        # provide it).
        if IS_WINDOWS:
            ide_os = "WINDOWS"
        else:
            ide_os = "UNIX"

        # Breakpoints can be grouped by 'LINE' or by 'ID'.
        breakpoints_by = "LINE"

        splitted = text.split("\t")
        if len(splitted) == 1:
            _local_version = splitted

        elif len(splitted) == 2:
            _local_version, ide_os = splitted

        elif len(splitted) == 3:
            _local_version, ide_os, breakpoints_by = splitted

        version_msg = self.api.set_ide_os_and_breakpoints_by(py_db, seq, ide_os, breakpoints_by)

        # Enable thread notifications after the version command is completed.
        self.api.set_enable_thread_notifications(py_db, True)

        return version_msg

    def cmd_thread_run(self, py_db, cmd_id, seq, text):
        return self.api.request_resume_thread(text.strip())

    def _cmd_step(self, py_db, cmd_id, seq, text):
        return self.api.request_step(py_db, text.strip(), cmd_id)

    cmd_step_into = _cmd_step
    cmd_step_into_my_code = _cmd_step
    cmd_step_over = _cmd_step
    cmd_step_over_my_code = _cmd_step
    cmd_step_return = _cmd_step
    cmd_step_return_my_code = _cmd_step

    def _cmd_set_next(self, py_db, cmd_id, seq, text):
        thread_id, line, func_name = text.split("\t", 2)
        return self.api.request_set_next(py_db, seq, thread_id, cmd_id, None, line, func_name)

    cmd_run_to_line = _cmd_set_next
    cmd_set_next_statement = _cmd_set_next

    def cmd_smart_step_into(self, py_db, cmd_id, seq, text):
        thread_id, line_or_bytecode_offset, func_name = text.split("\t", 2)
        if line_or_bytecode_offset.startswith("offset="):
            # In this case we request the smart step into to stop given the parent frame
            # and the location of the parent frame bytecode offset and not just the func_name
            # (this implies that `CMD_GET_SMART_STEP_INTO_VARIANTS` was previously used
            # to know what are the valid stop points).

            temp = line_or_bytecode_offset[len("offset=") :]
            if ";" in temp:
                offset, child_offset = temp.split(";")
                offset = int(offset)
                child_offset = int(child_offset)
            else:
                child_offset = -1
                offset = int(temp)
            return self.api.request_smart_step_into(py_db, seq, thread_id, offset, child_offset)
        else:
            # If the offset wasn't passed, just use the line/func_name to do the stop.
            return self.api.request_smart_step_into_by_func_name(py_db, seq, thread_id, line_or_bytecode_offset, func_name)

    def cmd_reload_code(self, py_db, cmd_id, seq, text):
        text = text.strip()
        if "\t" not in text:
            module_name = text.strip()
            filename = None
        else:
            module_name, filename = text.split("\t", 1)
        self.api.request_reload_code(py_db, seq, module_name, filename)

    def cmd_change_variable(self, py_db, cmd_id, seq, text):
        # the text is: thread\tstackframe\tFRAME|GLOBAL\tattribute_to_change\tvalue_to_change
        thread_id, frame_id, scope, attr_and_value = text.split("\t", 3)

        tab_index = attr_and_value.rindex("\t")
        attr = attr_and_value[0:tab_index].replace("\t", ".")
        value = attr_and_value[tab_index + 1 :]
        self.api.request_change_variable(py_db, seq, thread_id, frame_id, scope, attr, value)

    def cmd_get_variable(self, py_db, cmd_id, seq, text):
        # we received some command to get a variable
        # the text is: thread_id\tframe_id\tFRAME|GLOBAL\tattributes*
        thread_id, frame_id, scopeattrs = text.split("\t", 2)

        if scopeattrs.find("\t") != -1:  # there are attributes beyond scope
            scope, attrs = scopeattrs.split("\t", 1)
        else:
            scope, attrs = (scopeattrs, None)

        self.api.request_get_variable(py_db, seq, thread_id, frame_id, scope, attrs)

    def cmd_get_array(self, py_db, cmd_id, seq, text):
        # Note: untested and unused in pydev
        # we received some command to get an array variable
        # the text is: thread_id\tframe_id\tFRAME|GLOBAL\tname\ttemp\troffs\tcoffs\trows\tcols\tformat
        roffset, coffset, rows, cols, format, thread_id, frame_id, scopeattrs = text.split("\t", 7)

        if scopeattrs.find("\t") != -1:  # there are attributes beyond scope
            scope, attrs = scopeattrs.split("\t", 1)
        else:
            scope, attrs = (scopeattrs, None)

        self.api.request_get_array(py_db, seq, roffset, coffset, rows, cols, format, thread_id, frame_id, scope, attrs)

    def cmd_show_return_values(self, py_db, cmd_id, seq, text):
        show_return_values = text.split("\t")[1]
        self.api.set_show_return_values(py_db, int(show_return_values) == 1)

    def cmd_load_full_value(self, py_db, cmd_id, seq, text):
        # Note: untested and unused in pydev
        thread_id, frame_id, scopeattrs = text.split("\t", 2)
        vars = scopeattrs.split(NEXT_VALUE_SEPARATOR)

        self.api.request_load_full_value(py_db, seq, thread_id, frame_id, vars)

    def cmd_get_description(self, py_db, cmd_id, seq, text):
        # Note: untested and unused in pydev
        thread_id, frame_id, expression = text.split("\t", 2)
        self.api.request_get_description(py_db, seq, thread_id, frame_id, expression)

    def cmd_get_frame(self, py_db, cmd_id, seq, text):
        thread_id, frame_id, scope = text.split("\t", 2)
        self.api.request_get_frame(py_db, seq, thread_id, frame_id)

    def cmd_set_break(self, py_db, cmd_id, seq, text):
        # func name: 'None': match anything. Empty: match global, specified: only method context.
        # command to add some breakpoint.
        # text is filename\tline. Add to breakpoints dictionary
        suspend_policy = "NONE"  # Can be 'NONE' or 'ALL'
        is_logpoint = False
        hit_condition = None
        if py_db._set_breakpoints_with_id:
            try:
                try:
                    (
                        breakpoint_id,
                        btype,
                        filename,
                        line,
                        func_name,
                        condition,
                        expression,
                        hit_condition,
                        is_logpoint,
                        suspend_policy,
                    ) = text.split("\t", 9)
                except ValueError:  # not enough values to unpack
                    # No suspend_policy passed (use default).
                    breakpoint_id, btype, filename, line, func_name, condition, expression, hit_condition, is_logpoint = text.split("\t", 8)
                is_logpoint = is_logpoint == "True"
            except ValueError:  # not enough values to unpack
                breakpoint_id, btype, filename, line, func_name, condition, expression = text.split("\t", 6)

            breakpoint_id = int(breakpoint_id)
            line = int(line)

            # We must restore new lines and tabs as done in
            # AbstractDebugTarget.breakpointAdded
            condition = condition.replace("@_@NEW_LINE_CHAR@_@", "\n").replace("@_@TAB_CHAR@_@", "\t").strip()

            expression = expression.replace("@_@NEW_LINE_CHAR@_@", "\n").replace("@_@TAB_CHAR@_@", "\t").strip()
        else:
            # Note: this else should be removed after PyCharm migrates to setting
            # breakpoints by id (and ideally also provides func_name).
            btype, filename, line, func_name, suspend_policy, condition, expression = text.split("\t", 6)
            # If we don't have an id given for each breakpoint, consider
            # the id to be the line.
            breakpoint_id = line = int(line)

            condition = condition.replace("@_@NEW_LINE_CHAR@_@", "\n").replace("@_@TAB_CHAR@_@", "\t").strip()

            expression = expression.replace("@_@NEW_LINE_CHAR@_@", "\n").replace("@_@TAB_CHAR@_@", "\t").strip()

        if condition is not None and (len(condition) <= 0 or condition == "None"):
            condition = None

        if expression is not None and (len(expression) <= 0 or expression == "None"):
            expression = None

        if hit_condition is not None and (len(hit_condition) <= 0 or hit_condition == "None"):
            hit_condition = None

        def on_changed_breakpoint_state(breakpoint_id, add_breakpoint_result):
            error_code = add_breakpoint_result.error_code

            translated_line = add_breakpoint_result.translated_line
            translated_filename = add_breakpoint_result.translated_filename
            msg = ""
            if error_code:
                if error_code == self.api.ADD_BREAKPOINT_FILE_NOT_FOUND:
                    msg = "pydev debugger: Trying to add breakpoint to file that does not exist: %s (will have no effect).\n" % (
                        translated_filename,
                    )

                elif error_code == self.api.ADD_BREAKPOINT_FILE_EXCLUDED_BY_FILTERS:
                    msg = "pydev debugger: Trying to add breakpoint to file that is excluded by filters: %s (will have no effect).\n" % (
                        translated_filename,
                    )

                elif error_code == self.api.ADD_BREAKPOINT_LAZY_VALIDATION:
                    msg = ""  # Ignore this here (if/when loaded, it'll call on_changed_breakpoint_state again accordingly).

                elif error_code == self.api.ADD_BREAKPOINT_INVALID_LINE:
                    msg = "pydev debugger: Trying to add breakpoint to line (%s) that is not valid in: %s.\n" % (
                        translated_line,
                        translated_filename,
                    )

                else:
                    # Shouldn't get here.
                    msg = "pydev debugger: Breakpoint not validated (reason unknown -- please report as error): %s (%s).\n" % (
                        translated_filename,
                        translated_line,
                    )

            else:
                if add_breakpoint_result.original_line != translated_line:
                    msg = "pydev debugger (info): Breakpoint in line: %s moved to line: %s (in %s).\n" % (
                        add_breakpoint_result.original_line,
                        translated_line,
                        translated_filename,
                    )

            if msg:
                py_db.writer.add_command(py_db.cmd_factory.make_warning_message(msg))

        result = self.api.add_breakpoint(
            py_db,
            self.api.filename_to_str(filename),
            btype,
            breakpoint_id,
            line,
            condition,
            func_name,
            expression,
            suspend_policy,
            hit_condition,
            is_logpoint,
            on_changed_breakpoint_state=on_changed_breakpoint_state,
        )

        on_changed_breakpoint_state(breakpoint_id, result)

    def cmd_remove_break(self, py_db, cmd_id, seq, text):
        # command to remove some breakpoint
        # text is type\file\tid. Remove from breakpoints dictionary
        breakpoint_type, filename, breakpoint_id = text.split("\t", 2)

        filename = self.api.filename_to_str(filename)

        try:
            breakpoint_id = int(breakpoint_id)
        except ValueError:
            pydev_log.critical("Error removing breakpoint. Expected breakpoint_id to be an int. Found: %s", breakpoint_id)

        else:
            self.api.remove_breakpoint(py_db, filename, breakpoint_type, breakpoint_id)

    def _cmd_exec_or_evaluate_expression(self, py_db, cmd_id, seq, text):
        # command to evaluate the given expression
        # text is: thread\tstackframe\tLOCAL\texpression
        attr_to_set_result = ""
        try:
            thread_id, frame_id, scope, expression, trim, attr_to_set_result = text.split("\t", 5)
        except ValueError:
            thread_id, frame_id, scope, expression, trim = text.split("\t", 4)
        is_exec = cmd_id == CMD_EXEC_EXPRESSION
        trim_if_too_big = int(trim) == 1

        self.api.request_exec_or_evaluate(py_db, seq, thread_id, frame_id, expression, is_exec, trim_if_too_big, attr_to_set_result)

    cmd_evaluate_expression = _cmd_exec_or_evaluate_expression
    cmd_exec_expression = _cmd_exec_or_evaluate_expression

    def cmd_console_exec(self, py_db, cmd_id, seq, text):
        # command to exec expression in console, in case expression is only partially valid 'False' is returned
        # text is: thread\tstackframe\tLOCAL\texpression

        thread_id, frame_id, scope, expression = text.split("\t", 3)
        self.api.request_console_exec(py_db, seq, thread_id, frame_id, expression)

    def cmd_set_path_mapping_json(self, py_db, cmd_id, seq, text):
        """
        :param text:
            Json text. Something as:

            {
                "pathMappings": [
                    {
                        "localRoot": "c:/temp",
                        "remoteRoot": "/usr/temp"
                    }
                ],
                "debug": true,
                "force": false
            }
        """
        as_json = json.loads(text)
        force = as_json.get("force", False)

        path_mappings = []
        for pathMapping in as_json.get("pathMappings", []):
            localRoot = pathMapping.get("localRoot", "")
            remoteRoot = pathMapping.get("remoteRoot", "")
            if (localRoot != "") and (remoteRoot != ""):
                path_mappings.append((localRoot, remoteRoot))

        if bool(path_mappings) or force:
            pydevd_file_utils.setup_client_server_paths(path_mappings)

        debug = as_json.get("debug", False)
        if debug or force:
            pydevd_file_utils.DEBUG_CLIENT_SERVER_TRANSLATION = debug

    def cmd_set_py_exception_json(self, py_db, cmd_id, seq, text):
        # This API is optional and works 'in bulk' -- it's possible
        # to get finer-grained control with CMD_ADD_EXCEPTION_BREAK/CMD_REMOVE_EXCEPTION_BREAK
        # which allows setting caught/uncaught per exception, although global settings such as:
        # - skip_on_exceptions_thrown_in_same_context
        # - ignore_exceptions_thrown_in_lines_with_ignore_exception
        # must still be set through this API (before anything else as this clears all existing
        # exception breakpoints).
        try:
            py_db.break_on_uncaught_exceptions = {}
            py_db.break_on_caught_exceptions = {}
            py_db.break_on_user_uncaught_exceptions = {}

            as_json = json.loads(text)
            break_on_uncaught = as_json.get("break_on_uncaught", False)
            break_on_caught = as_json.get("break_on_caught", False)
            break_on_user_caught = as_json.get("break_on_user_caught", False)
            py_db.skip_on_exceptions_thrown_in_same_context = as_json.get("skip_on_exceptions_thrown_in_same_context", False)
            py_db.ignore_exceptions_thrown_in_lines_with_ignore_exception = as_json.get(
                "ignore_exceptions_thrown_in_lines_with_ignore_exception", False
            )
            ignore_libraries = as_json.get("ignore_libraries", False)
            exception_types = as_json.get("exception_types", [])

            for exception_type in exception_types:
                if not exception_type:
                    continue

                py_db.add_break_on_exception(
                    exception_type,
                    condition=None,
                    expression=None,
                    notify_on_handled_exceptions=break_on_caught,
                    notify_on_unhandled_exceptions=break_on_uncaught,
                    notify_on_user_unhandled_exceptions=break_on_user_caught,
                    notify_on_first_raise_only=True,
                    ignore_libraries=ignore_libraries,
                )

                py_db.on_breakpoints_changed()
        except:
            pydev_log.exception("Error when setting exception list. Received: %s", text)

    def cmd_set_py_exception(self, py_db, cmd_id, seq, text):
        # DEPRECATED. Use cmd_set_py_exception_json instead.
        try:
            splitted = text.split(";")
            py_db.break_on_uncaught_exceptions = {}
            py_db.break_on_caught_exceptions = {}
            py_db.break_on_user_uncaught_exceptions = {}
            if len(splitted) >= 5:
                if splitted[0] == "true":
                    break_on_uncaught = True
                else:
                    break_on_uncaught = False

                if splitted[1] == "true":
                    break_on_caught = True
                else:
                    break_on_caught = False

                if splitted[2] == "true":
                    py_db.skip_on_exceptions_thrown_in_same_context = True
                else:
                    py_db.skip_on_exceptions_thrown_in_same_context = False

                if splitted[3] == "true":
                    py_db.ignore_exceptions_thrown_in_lines_with_ignore_exception = True
                else:
                    py_db.ignore_exceptions_thrown_in_lines_with_ignore_exception = False

                if splitted[4] == "true":
                    ignore_libraries = True
                else:
                    ignore_libraries = False

                for exception_type in splitted[5:]:
                    exception_type = exception_type.strip()
                    if not exception_type:
                        continue

                    py_db.add_break_on_exception(
                        exception_type,
                        condition=None,
                        expression=None,
                        notify_on_handled_exceptions=break_on_caught,
                        notify_on_unhandled_exceptions=break_on_uncaught,
                        notify_on_user_unhandled_exceptions=False,  # TODO (not currently supported in this API).
                        notify_on_first_raise_only=True,
                        ignore_libraries=ignore_libraries,
                    )
            else:
                pydev_log.exception("Expected to have at least 5 ';' separated items. Received: %s", text)

        except:
            pydev_log.exception("Error when setting exception list. Received: %s", text)

    def _load_source(self, py_db, cmd_id, seq, text):
        filename = text
        filename = self.api.filename_to_str(filename)
        self.api.request_load_source(py_db, seq, filename)

    cmd_load_source = _load_source
    cmd_get_file_contents = _load_source

    def cmd_load_source_from_frame_id(self, py_db, cmd_id, seq, text):
        frame_id = text
        self.api.request_load_source_from_frame_id(py_db, seq, frame_id)

    def cmd_set_property_trace(self, py_db, cmd_id, seq, text):
        # Command which receives whether to trace property getter/setter/deleter
        # text is feature_state(true/false);disable_getter/disable_setter/disable_deleter
        if text:
            splitted = text.split(";")
            if len(splitted) >= 3:
                if not py_db.disable_property_trace and splitted[0] == "true":
                    # Replacing property by custom property only when the debugger starts
                    pydevd_traceproperty.replace_builtin_property()
                    py_db.disable_property_trace = True
                # Enable/Disable tracing of the property getter
                if splitted[1] == "true":
                    py_db.disable_property_getter_trace = True
                else:
                    py_db.disable_property_getter_trace = False
                # Enable/Disable tracing of the property setter
                if splitted[2] == "true":
                    py_db.disable_property_setter_trace = True
                else:
                    py_db.disable_property_setter_trace = False
                # Enable/Disable tracing of the property deleter
                if splitted[3] == "true":
                    py_db.disable_property_deleter_trace = True
                else:
                    py_db.disable_property_deleter_trace = False

    def cmd_add_exception_break(self, py_db, cmd_id, seq, text):
        # Note that this message has some idiosyncrasies...
        #
        # notify_on_handled_exceptions can be 0, 1 or 2
        # 0 means we should not stop on handled exceptions.
        # 1 means we should stop on handled exceptions showing it on all frames where the exception passes.
        # 2 means we should stop on handled exceptions but we should only notify about it once.
        #
        # To ignore_libraries properly, besides setting ignore_libraries to 1, the IDE_PROJECT_ROOTS environment
        # variable must be set (so, we'll ignore anything not below IDE_PROJECT_ROOTS) -- this is not ideal as
        # the environment variable may not be properly set if it didn't start from the debugger (we should
        # create a custom message for that).
        #
        # There are 2 global settings which can only be set in CMD_SET_PY_EXCEPTION. Namely:
        #
        # py_db.skip_on_exceptions_thrown_in_same_context
        # - If True, we should only show the exception in a caller, not where it was first raised.
        #
        # py_db.ignore_exceptions_thrown_in_lines_with_ignore_exception
        # - If True exceptions thrown in lines with '@IgnoreException' will not be shown.

        condition = ""
        expression = ""
        if text.find("\t") != -1:
            try:
                (
                    exception,
                    condition,
                    expression,
                    notify_on_handled_exceptions,
                    notify_on_unhandled_exceptions,
                    ignore_libraries,
                ) = text.split("\t", 5)
            except:
                exception, notify_on_handled_exceptions, notify_on_unhandled_exceptions, ignore_libraries = text.split("\t", 3)
        else:
            exception, notify_on_handled_exceptions, notify_on_unhandled_exceptions, ignore_libraries = text, 0, 0, 0

        condition = condition.replace("@_@NEW_LINE_CHAR@_@", "\n").replace("@_@TAB_CHAR@_@", "\t").strip()

        if condition is not None and (len(condition) == 0 or condition == "None"):
            condition = None

        expression = expression.replace("@_@NEW_LINE_CHAR@_@", "\n").replace("@_@TAB_CHAR@_@", "\t").strip()

        if expression is not None and (len(expression) == 0 or expression == "None"):
            expression = None

        if exception.find("-") != -1:
            breakpoint_type, exception = exception.split("-")
        else:
            breakpoint_type = "python"

        if breakpoint_type == "python":
            self.api.add_python_exception_breakpoint(
                py_db,
                exception,
                condition,
                expression,
                notify_on_handled_exceptions=int(notify_on_handled_exceptions) > 0,
                notify_on_unhandled_exceptions=int(notify_on_unhandled_exceptions) == 1,
                notify_on_user_unhandled_exceptions=0,  # TODO (not currently supported in this API).
                notify_on_first_raise_only=int(notify_on_handled_exceptions) == 2,
                ignore_libraries=int(ignore_libraries) > 0,
            )
        else:
            self.api.add_plugins_exception_breakpoint(py_db, breakpoint_type, exception)

    def cmd_remove_exception_break(self, py_db, cmd_id, seq, text):
        exception = text
        if exception.find("-") != -1:
            exception_type, exception = exception.split("-")
        else:
            exception_type = "python"

        if exception_type == "python":
            self.api.remove_python_exception_breakpoint(py_db, exception)
        else:
            self.api.remove_plugins_exception_breakpoint(py_db, exception_type, exception)

    def cmd_add_django_exception_break(self, py_db, cmd_id, seq, text):
        self.api.add_plugins_exception_breakpoint(py_db, breakpoint_type="django", exception=text)

    def cmd_remove_django_exception_break(self, py_db, cmd_id, seq, text):
        self.api.remove_plugins_exception_breakpoint(py_db, exception_type="django", exception=text)

    def cmd_evaluate_console_expression(self, py_db, cmd_id, seq, text):
        # Command which takes care for the debug console communication
        if text != "":
            thread_id, frame_id, console_command = text.split("\t", 2)
            console_command, line = console_command.split("\t")

            if console_command == "EVALUATE":
                int_cmd = InternalEvaluateConsoleExpression(seq, thread_id, frame_id, line, buffer_output=True)

            elif console_command == "EVALUATE_UNBUFFERED":
                int_cmd = InternalEvaluateConsoleExpression(seq, thread_id, frame_id, line, buffer_output=False)

            elif console_command == "GET_COMPLETIONS":
                int_cmd = InternalConsoleGetCompletions(seq, thread_id, frame_id, line)

            else:
                raise ValueError("Unrecognized command: %s" % (console_command,))

            py_db.post_internal_command(int_cmd, thread_id)

    def cmd_run_custom_operation(self, py_db, cmd_id, seq, text):
        # Command which runs a custom operation
        if text != "":
            try:
                location, custom = text.split("||", 1)
            except:
                sys.stderr.write("Custom operation now needs a || separator. Found: %s\n" % (text,))
                raise

            thread_id, frame_id, scopeattrs = location.split("\t", 2)

            if scopeattrs.find("\t") != -1:  # there are attributes beyond scope
                scope, attrs = scopeattrs.split("\t", 1)
            else:
                scope, attrs = (scopeattrs, None)

            # : style: EXECFILE or EXEC
            # : encoded_code_or_file: file to execute or code
            # : fname: name of function to be executed in the resulting namespace
            style, encoded_code_or_file, fnname = custom.split("\t", 3)
            int_cmd = InternalRunCustomOperation(seq, thread_id, frame_id, scope, attrs, style, encoded_code_or_file, fnname)
            py_db.post_internal_command(int_cmd, thread_id)

    def cmd_ignore_thrown_exception_at(self, py_db, cmd_id, seq, text):
        if text:
            replace = "REPLACE:"  # Not all 3.x versions support u'REPLACE:', so, doing workaround.
            if text.startswith(replace):
                text = text[8:]
                py_db.filename_to_lines_where_exceptions_are_ignored.clear()

            if text:
                for line in text.split("||"):  # Can be bulk-created (one in each line)
                    original_filename, line_number = line.split("|")
                    original_filename = self.api.filename_to_server(original_filename)

                    canonical_normalized_filename = pydevd_file_utils.canonical_normalized_path(original_filename)
                    absolute_filename = pydevd_file_utils.absolute_path(original_filename)

                    if os.path.exists(absolute_filename):
                        lines_ignored = py_db.filename_to_lines_where_exceptions_are_ignored.get(canonical_normalized_filename)
                        if lines_ignored is None:
                            lines_ignored = py_db.filename_to_lines_where_exceptions_are_ignored[canonical_normalized_filename] = {}
                        lines_ignored[int(line_number)] = 1
                    else:
                        sys.stderr.write(
                            "pydev debugger: warning: trying to ignore exception thrown"
                            " on file that does not exist: %s (will have no effect)\n" % (absolute_filename,)
                        )

    def cmd_enable_dont_trace(self, py_db, cmd_id, seq, text):
        if text:
            true_str = "true"  # Not all 3.x versions support u'str', so, doing workaround.
            mode = text.strip() == true_str
            pydevd_dont_trace.trace_filter(mode)

    def cmd_redirect_output(self, py_db, cmd_id, seq, text):
        if text:
            py_db.enable_output_redirection("STDOUT" in text, "STDERR" in text)

    def cmd_get_next_statement_targets(self, py_db, cmd_id, seq, text):
        thread_id, frame_id = text.split("\t", 1)

        py_db.post_method_as_internal_command(thread_id, internal_get_next_statement_targets, seq, thread_id, frame_id)

    def cmd_get_smart_step_into_variants(self, py_db, cmd_id, seq, text):
        thread_id, frame_id, start_line, end_line = text.split("\t", 3)

        py_db.post_method_as_internal_command(
            thread_id,
            internal_get_smart_step_into_variants,
            seq,
            thread_id,
            frame_id,
            start_line,
            end_line,
            set_additional_thread_info=set_additional_thread_info,
        )

    def cmd_set_project_roots(self, py_db, cmd_id, seq, text):
        self.api.set_project_roots(py_db, text.split("\t"))

    def cmd_thread_dump_to_stderr(self, py_db, cmd_id, seq, text):
        pydevd_utils.dump_threads()

    def cmd_stop_on_start(self, py_db, cmd_id, seq, text):
        if text.strip() in ("True", "true", "1"):
            self.api.stop_on_entry()

    def cmd_pydevd_json_config(self, py_db, cmd_id, seq, text):
        # Expected to receive a json string as:
        # {
        #     'skip_suspend_on_breakpoint_exception': [<exception names where we should suspend>],
        #     'skip_print_breakpoint_exception': [<exception names where we should print>],
        #     'multi_threads_single_notification': bool,
        # }
        msg = json.loads(text.strip())
        if "skip_suspend_on_breakpoint_exception" in msg:
            py_db.skip_suspend_on_breakpoint_exception = tuple(get_exception_class(x) for x in msg["skip_suspend_on_breakpoint_exception"])

        if "skip_print_breakpoint_exception" in msg:
            py_db.skip_print_breakpoint_exception = tuple(get_exception_class(x) for x in msg["skip_print_breakpoint_exception"])

        if "multi_threads_single_notification" in msg:
            py_db.multi_threads_single_notification = msg["multi_threads_single_notification"]

    def cmd_get_exception_details(self, py_db, cmd_id, seq, text):
        thread_id = text
        t = pydevd_find_thread_by_id(thread_id)
        frame = None
        if t is not None and not getattr(t, "pydev_do_not_trace", None):
            additional_info = set_additional_thread_info(t)
            frame = additional_info.get_topmost_frame(t)
        try:
            # Note: provide the return even if the thread is empty.
            return py_db.cmd_factory.make_get_exception_details_message(py_db, seq, thread_id, frame)
        finally:
            frame = None
            t = None


process_net_command = _PyDevCommandProcessor().process_net_command

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\command\install.py ===
"""distutils.command.install

Implements the Distutils 'install' command."""

from __future__ import annotations

import collections
import contextlib
import itertools
import os
import sys
import sysconfig
from distutils._log import log
from site import USER_BASE, USER_SITE
from typing import ClassVar

from ..core import Command
from ..debug import DEBUG
from ..errors import DistutilsOptionError, DistutilsPlatformError
from ..file_util import write_file
from ..sysconfig import get_config_vars
from ..util import change_root, convert_path, get_platform, subst_vars
from . import _framework_compat as fw

HAS_USER_SITE = True

WINDOWS_SCHEME = {
    'purelib': '{base}/Lib/site-packages',
    'platlib': '{base}/Lib/site-packages',
    'headers': '{base}/Include/{dist_name}',
    'scripts': '{base}/Scripts',
    'data': '{base}',
}

INSTALL_SCHEMES = {
    'posix_prefix': {
        'purelib': '{base}/lib/{implementation_lower}{py_version_short}/site-packages',
        'platlib': '{platbase}/{platlibdir}/{implementation_lower}'
        '{py_version_short}/site-packages',
        'headers': '{base}/include/{implementation_lower}'
        '{py_version_short}{abiflags}/{dist_name}',
        'scripts': '{base}/bin',
        'data': '{base}',
    },
    'posix_home': {
        'purelib': '{base}/lib/{implementation_lower}',
        'platlib': '{base}/{platlibdir}/{implementation_lower}',
        'headers': '{base}/include/{implementation_lower}/{dist_name}',
        'scripts': '{base}/bin',
        'data': '{base}',
    },
    'nt': WINDOWS_SCHEME,
    'pypy': {
        'purelib': '{base}/site-packages',
        'platlib': '{base}/site-packages',
        'headers': '{base}/include/{dist_name}',
        'scripts': '{base}/bin',
        'data': '{base}',
    },
    'pypy_nt': {
        'purelib': '{base}/site-packages',
        'platlib': '{base}/site-packages',
        'headers': '{base}/include/{dist_name}',
        'scripts': '{base}/Scripts',
        'data': '{base}',
    },
}

# user site schemes
if HAS_USER_SITE:
    INSTALL_SCHEMES['nt_user'] = {
        'purelib': '{usersite}',
        'platlib': '{usersite}',
        'headers': '{userbase}/{implementation}{py_version_nodot_plat}'
        '/Include/{dist_name}',
        'scripts': '{userbase}/{implementation}{py_version_nodot_plat}/Scripts',
        'data': '{userbase}',
    }

    INSTALL_SCHEMES['posix_user'] = {
        'purelib': '{usersite}',
        'platlib': '{usersite}',
        'headers': '{userbase}/include/{implementation_lower}'
        '{py_version_short}{abiflags}/{dist_name}',
        'scripts': '{userbase}/bin',
        'data': '{userbase}',
    }


INSTALL_SCHEMES.update(fw.schemes)


# The keys to an installation scheme; if any new types of files are to be
# installed, be sure to add an entry to every installation scheme above,
# and to SCHEME_KEYS here.
SCHEME_KEYS = ('purelib', 'platlib', 'headers', 'scripts', 'data')


def _load_sysconfig_schemes():
    with contextlib.suppress(AttributeError):
        return {
            scheme: sysconfig.get_paths(scheme, expand=False)
            for scheme in sysconfig.get_scheme_names()
        }


def _load_schemes():
    """
    Extend default schemes with schemes from sysconfig.
    """

    sysconfig_schemes = _load_sysconfig_schemes() or {}

    return {
        scheme: {
            **INSTALL_SCHEMES.get(scheme, {}),
            **sysconfig_schemes.get(scheme, {}),
        }
        for scheme in set(itertools.chain(INSTALL_SCHEMES, sysconfig_schemes))
    }


def _get_implementation():
    if hasattr(sys, 'pypy_version_info'):
        return 'PyPy'
    else:
        return 'Python'


def _select_scheme(ob, name):
    scheme = _inject_headers(name, _load_scheme(_resolve_scheme(name)))
    vars(ob).update(_remove_set(ob, _scheme_attrs(scheme)))


def _remove_set(ob, attrs):
    """
    Include only attrs that are None in ob.
    """
    return {key: value for key, value in attrs.items() if getattr(ob, key) is None}


def _resolve_scheme(name):
    os_name, sep, key = name.partition('_')
    try:
        resolved = sysconfig.get_preferred_scheme(key)
    except Exception:
        resolved = fw.scheme(name)
    return resolved


def _load_scheme(name):
    return _load_schemes()[name]


def _inject_headers(name, scheme):
    """
    Given a scheme name and the resolved scheme,
    if the scheme does not include headers, resolve
    the fallback scheme for the name and use headers
    from it. pypa/distutils#88
    """
    # Bypass the preferred scheme, which may not
    # have defined headers.
    fallback = _load_scheme(name)
    scheme.setdefault('headers', fallback['headers'])
    return scheme


def _scheme_attrs(scheme):
    """Resolve install directories by applying the install schemes."""
    return {f'install_{key}': scheme[key] for key in SCHEME_KEYS}


class install(Command):
    description = "install everything from build directory"

    user_options = [
        # Select installation scheme and set base director(y|ies)
        ('prefix=', None, "installation prefix"),
        ('exec-prefix=', None, "(Unix only) prefix for platform-specific files"),
        ('home=', None, "(Unix only) home directory to install under"),
        # Or, just set the base director(y|ies)
        (
            'install-base=',
            None,
            "base installation directory (instead of --prefix or --home)",
        ),
        (
            'install-platbase=',
            None,
            "base installation directory for platform-specific files (instead of --exec-prefix or --home)",
        ),
        ('root=', None, "install everything relative to this alternate root directory"),
        # Or, explicitly set the installation scheme
        (
            'install-purelib=',
            None,
            "installation directory for pure Python module distributions",
        ),
        (
            'install-platlib=',
            None,
            "installation directory for non-pure module distributions",
        ),
        (
            'install-lib=',
            None,
            "installation directory for all module distributions (overrides --install-purelib and --install-platlib)",
        ),
        ('install-headers=', None, "installation directory for C/C++ headers"),
        ('install-scripts=', None, "installation directory for Python scripts"),
        ('install-data=', None, "installation directory for data files"),
        # Byte-compilation options -- see install_lib.py for details, as
        # these are duplicated from there (but only install_lib does
        # anything with them).
        ('compile', 'c', "compile .py to .pyc [default]"),
        ('no-compile', None, "don't compile .py files"),
        (
            'optimize=',
            'O',
            "also compile with optimization: -O1 for \"python -O\", "
            "-O2 for \"python -OO\", and -O0 to disable [default: -O0]",
        ),
        # Miscellaneous control options
        ('force', 'f', "force installation (overwrite any existing files)"),
        ('skip-build', None, "skip rebuilding everything (for testing/debugging)"),
        # Where to install documentation (eventually!)
        # ('doc-format=', None, "format of documentation to generate"),
        # ('install-man=', None, "directory for Unix man pages"),
        # ('install-html=', None, "directory for HTML documentation"),
        # ('install-info=', None, "directory for GNU info files"),
        ('record=', None, "filename in which to record list of installed files"),
    ]

    boolean_options: ClassVar[list[str]] = ['compile', 'force', 'skip-build']

    if HAS_USER_SITE:
        user_options.append((
            'user',
            None,
            f"install in user site-package '{USER_SITE}'",
        ))
        boolean_options.append('user')

    negative_opt: ClassVar[dict[str, str]] = {'no-compile': 'compile'}

    def initialize_options(self) -> None:
        """Initializes options."""
        # High-level options: these select both an installation base
        # and scheme.
        self.prefix: str | None = None
        self.exec_prefix: str | None = None
        self.home: str | None = None
        self.user = False

        # These select only the installation base; it's up to the user to
        # specify the installation scheme (currently, that means supplying
        # the --install-{platlib,purelib,scripts,data} options).
        self.install_base = None
        self.install_platbase = None
        self.root: str | None = None

        # These options are the actual installation directories; if not
        # supplied by the user, they are filled in using the installation
        # scheme implied by prefix/exec-prefix/home and the contents of
        # that installation scheme.
        self.install_purelib = None  # for pure module distributions
        self.install_platlib = None  # non-pure (dists w/ extensions)
        self.install_headers = None  # for C/C++ headers
        self.install_lib: str | None = None  # set to either purelib or platlib
        self.install_scripts = None
        self.install_data = None
        self.install_userbase = USER_BASE
        self.install_usersite = USER_SITE

        self.compile = None
        self.optimize = None

        # Deprecated
        # These two are for putting non-packagized distributions into their
        # own directory and creating a .pth file if it makes sense.
        # 'extra_path' comes from the setup file; 'install_path_file' can
        # be turned off if it makes no sense to install a .pth file.  (But
        # better to install it uselessly than to guess wrong and not
        # install it when it's necessary and would be used!)  Currently,
        # 'install_path_file' is always true unless some outsider meddles
        # with it.
        self.extra_path = None
        self.install_path_file = True

        # 'force' forces installation, even if target files are not
        # out-of-date.  'skip_build' skips running the "build" command,
        # handy if you know it's not necessary.  'warn_dir' (which is *not*
        # a user option, it's just there so the bdist_* commands can turn
        # it off) determines whether we warn about installing to a
        # directory not in sys.path.
        self.force = False
        self.skip_build = False
        self.warn_dir = True

        # These are only here as a conduit from the 'build' command to the
        # 'install_*' commands that do the real work.  ('build_base' isn't
        # actually used anywhere, but it might be useful in future.)  They
        # are not user options, because if the user told the install
        # command where the build directory is, that wouldn't affect the
        # build command.
        self.build_base = None
        self.build_lib = None

        # Not defined yet because we don't know anything about
        # documentation yet.
        # self.install_man = None
        # self.install_html = None
        # self.install_info = None

        self.record = None

    # -- Option finalizing methods -------------------------------------
    # (This is rather more involved than for most commands,
    # because this is where the policy for installing third-
    # party Python modules on various platforms given a wide
    # array of user input is decided.  Yes, it's quite complex!)

    def finalize_options(self) -> None:  # noqa: C901
        """Finalizes options."""
        # This method (and its helpers, like 'finalize_unix()',
        # 'finalize_other()', and 'select_scheme()') is where the default
        # installation directories for modules, extension modules, and
        # anything else we care to install from a Python module
        # distribution.  Thus, this code makes a pretty important policy
        # statement about how third-party stuff is added to a Python
        # installation!  Note that the actual work of installation is done
        # by the relatively simple 'install_*' commands; they just take
        # their orders from the installation directory options determined
        # here.

        # Check for errors/inconsistencies in the options; first, stuff
        # that's wrong on any platform.

        if (self.prefix or self.exec_prefix or self.home) and (
            self.install_base or self.install_platbase
        ):
            raise DistutilsOptionError(
                "must supply either prefix/exec-prefix/home or install-base/install-platbase -- not both"
            )

        if self.home and (self.prefix or self.exec_prefix):
            raise DistutilsOptionError(
                "must supply either home or prefix/exec-prefix -- not both"
            )

        if self.user and (
            self.prefix
            or self.exec_prefix
            or self.home
            or self.install_base
            or self.install_platbase
        ):
            raise DistutilsOptionError(
                "can't combine user with prefix, "
                "exec_prefix/home, or install_(plat)base"
            )

        # Next, stuff that's wrong (or dubious) only on certain platforms.
        if os.name != "posix":
            if self.exec_prefix:
                self.warn("exec-prefix option ignored on this platform")
                self.exec_prefix = None

        # Now the interesting logic -- so interesting that we farm it out
        # to other methods.  The goal of these methods is to set the final
        # values for the install_{lib,scripts,data,...}  options, using as
        # input a heady brew of prefix, exec_prefix, home, install_base,
        # install_platbase, user-supplied versions of
        # install_{purelib,platlib,lib,scripts,data,...}, and the
        # install schemes.  Phew!

        self.dump_dirs("pre-finalize_{unix,other}")

        if os.name == 'posix':
            self.finalize_unix()
        else:
            self.finalize_other()

        self.dump_dirs("post-finalize_{unix,other}()")

        # Expand configuration variables, tilde, etc. in self.install_base
        # and self.install_platbase -- that way, we can use $base or
        # $platbase in the other installation directories and not worry
        # about needing recursive variable expansion (shudder).

        py_version = sys.version.split()[0]
        (prefix, exec_prefix) = get_config_vars('prefix', 'exec_prefix')
        try:
            abiflags = sys.abiflags
        except AttributeError:
            # sys.abiflags may not be defined on all platforms.
            abiflags = ''
        local_vars = {
            'dist_name': self.distribution.get_name(),
            'dist_version': self.distribution.get_version(),
            'dist_fullname': self.distribution.get_fullname(),
            'py_version': py_version,
            'py_version_short': f'{sys.version_info.major}.{sys.version_info.minor}',
            'py_version_nodot': f'{sys.version_info.major}{sys.version_info.minor}',
            'sys_prefix': prefix,
            'prefix': prefix,
            'sys_exec_prefix': exec_prefix,
            'exec_prefix': exec_prefix,
            'abiflags': abiflags,
            'platlibdir': getattr(sys, 'platlibdir', 'lib'),
            'implementation_lower': _get_implementation().lower(),
            'implementation': _get_implementation(),
        }

        # vars for compatibility on older Pythons
        compat_vars = dict(
            # Python 3.9 and earlier
            py_version_nodot_plat=getattr(sys, 'winver', '').replace('.', ''),
        )

        if HAS_USER_SITE:
            local_vars['userbase'] = self.install_userbase
            local_vars['usersite'] = self.install_usersite

        self.config_vars = collections.ChainMap(
            local_vars,
            sysconfig.get_config_vars(),
            compat_vars,
            fw.vars(),
        )

        self.expand_basedirs()

        self.dump_dirs("post-expand_basedirs()")

        # Now define config vars for the base directories so we can expand
        # everything else.
        local_vars['base'] = self.install_base
        local_vars['platbase'] = self.install_platbase

        if DEBUG:
            from pprint import pprint

            print("config vars:")
            pprint(dict(self.config_vars))

        # Expand "~" and configuration variables in the installation
        # directories.
        self.expand_dirs()

        self.dump_dirs("post-expand_dirs()")

        # Create directories in the home dir:
        if self.user:
            self.create_home_path()

        # Pick the actual directory to install all modules to: either
        # install_purelib or install_platlib, depending on whether this
        # module distribution is pure or not.  Of course, if the user
        # already specified install_lib, use their selection.
        if self.install_lib is None:
            if self.distribution.has_ext_modules():  # has extensions: non-pure
                self.install_lib = self.install_platlib
            else:
                self.install_lib = self.install_purelib

        # Convert directories from Unix /-separated syntax to the local
        # convention.
        self.convert_paths(
            'lib',
            'purelib',
            'platlib',
            'scripts',
            'data',
            'headers',
            'userbase',
            'usersite',
        )

        # Deprecated
        # Well, we're not actually fully completely finalized yet: we still
        # have to deal with 'extra_path', which is the hack for allowing
        # non-packagized module distributions (hello, Numerical Python!) to
        # get their own directories.
        self.handle_extra_path()
        self.install_libbase = self.install_lib  # needed for .pth file
        self.install_lib = os.path.join(self.install_lib, self.extra_dirs)

        # If a new root directory was supplied, make all the installation
        # dirs relative to it.
        if self.root is not None:
            self.change_roots(
                'libbase', 'lib', 'purelib', 'platlib', 'scripts', 'data', 'headers'
            )

        self.dump_dirs("after prepending root")

        # Find out the build directories, ie. where to install from.
        self.set_undefined_options(
            'build', ('build_base', 'build_base'), ('build_lib', 'build_lib')
        )

        # Punt on doc directories for now -- after all, we're punting on
        # documentation completely!

    def dump_dirs(self, msg) -> None:
        """Dumps the list of user options."""
        if not DEBUG:
            return
        from ..fancy_getopt import longopt_xlate

        log.debug(msg + ":")
        for opt in self.user_options:
            opt_name = opt[0]
            if opt_name[-1] == "=":
                opt_name = opt_name[0:-1]
            if opt_name in self.negative_opt:
                opt_name = self.negative_opt[opt_name]
                opt_name = opt_name.translate(longopt_xlate)
                val = not getattr(self, opt_name)
            else:
                opt_name = opt_name.translate(longopt_xlate)
                val = getattr(self, opt_name)
            log.debug("  %s: %s", opt_name, val)

    def finalize_unix(self) -> None:
        """Finalizes options for posix platforms."""
        if self.install_base is not None or self.install_platbase is not None:
            incomplete_scheme = (
                (
                    self.install_lib is None
                    and self.install_purelib is None
                    and self.install_platlib is None
                )
                or self.install_headers is None
                or self.install_scripts is None
                or self.install_data is None
            )
            if incomplete_scheme:
                raise DistutilsOptionError(
                    "install-base or install-platbase supplied, but "
                    "installation scheme is incomplete"
                )
            return

        if self.user:
            if self.install_userbase is None:
                raise DistutilsPlatformError("User base directory is not specified")
            self.install_base = self.install_platbase = self.install_userbase
            self.select_scheme("posix_user")
        elif self.home is not None:
            self.install_base = self.install_platbase = self.home
            self.select_scheme("posix_home")
        else:
            if self.prefix is None:
                if self.exec_prefix is not None:
                    raise DistutilsOptionError(
                        "must not supply exec-prefix without prefix"
                    )

                # Allow Fedora to add components to the prefix
                _prefix_addition = getattr(sysconfig, '_prefix_addition', "")

                self.prefix = os.path.normpath(sys.prefix) + _prefix_addition
                self.exec_prefix = os.path.normpath(sys.exec_prefix) + _prefix_addition

            else:
                if self.exec_prefix is None:
                    self.exec_prefix = self.prefix

            self.install_base = self.prefix
            self.install_platbase = self.exec_prefix
            self.select_scheme("posix_prefix")

    def finalize_other(self) -> None:
        """Finalizes options for non-posix platforms"""
        if self.user:
            if self.install_userbase is None:
                raise DistutilsPlatformError("User base directory is not specified")
            self.install_base = self.install_platbase = self.install_userbase
            self.select_scheme(os.name + "_user")
        elif self.home is not None:
            self.install_base = self.install_platbase = self.home
            self.select_scheme("posix_home")
        else:
            if self.prefix is None:
                self.prefix = os.path.normpath(sys.prefix)

            self.install_base = self.install_platbase = self.prefix
            try:
                self.select_scheme(os.name)
            except KeyError:
                raise DistutilsPlatformError(
                    f"I don't know how to install stuff on '{os.name}'"
                )

    def select_scheme(self, name) -> None:
        _select_scheme(self, name)

    def _expand_attrs(self, attrs):
        for attr in attrs:
            val = getattr(self, attr)
            if val is not None:
                if os.name in ('posix', 'nt'):
                    val = os.path.expanduser(val)
                val = subst_vars(val, self.config_vars)
                setattr(self, attr, val)

    def expand_basedirs(self) -> None:
        """Calls `os.path.expanduser` on install_base, install_platbase and
        root."""
        self._expand_attrs(['install_base', 'install_platbase', 'root'])

    def expand_dirs(self) -> None:
        """Calls `os.path.expanduser` on install dirs."""
        self._expand_attrs([
            'install_purelib',
            'install_platlib',
            'install_lib',
            'install_headers',
            'install_scripts',
            'install_data',
        ])

    def convert_paths(self, *names) -> None:
        """Call `convert_path` over `names`."""
        for name in names:
            attr = "install_" + name
            setattr(self, attr, convert_path(getattr(self, attr)))

    def handle_extra_path(self) -> None:
        """Set `path_file` and `extra_dirs` using `extra_path`."""
        if self.extra_path is None:
            self.extra_path = self.distribution.extra_path

        if self.extra_path is not None:
            log.warning(
                "Distribution option extra_path is deprecated. "
                "See issue27919 for details."
            )
            if isinstance(self.extra_path, str):
                self.extra_path = self.extra_path.split(',')

            if len(self.extra_path) == 1:
                path_file = extra_dirs = self.extra_path[0]
            elif len(self.extra_path) == 2:
                path_file, extra_dirs = self.extra_path
            else:
                raise DistutilsOptionError(
                    "'extra_path' option must be a list, tuple, or "
                    "comma-separated string with 1 or 2 elements"
                )

            # convert to local form in case Unix notation used (as it
            # should be in setup scripts)
            extra_dirs = convert_path(extra_dirs)
        else:
            path_file = None
            extra_dirs = ''

        # XXX should we warn if path_file and not extra_dirs? (in which
        # case the path file would be harmless but pointless)
        self.path_file = path_file
        self.extra_dirs = extra_dirs

    def change_roots(self, *names) -> None:
        """Change the install directories pointed by name using root."""
        for name in names:
            attr = "install_" + name
            setattr(self, attr, change_root(self.root, getattr(self, attr)))

    def create_home_path(self) -> None:
        """Create directories under ~."""
        if not self.user:
            return
        home = convert_path(os.path.expanduser("~"))
        for path in self.config_vars.values():
            if str(path).startswith(home) and not os.path.isdir(path):
                self.debug_print(f"os.makedirs('{path}', 0o700)")
                os.makedirs(path, 0o700)

    # -- Command execution methods -------------------------------------

    def run(self):
        """Runs the command."""
        # Obviously have to build before we can install
        if not self.skip_build:
            self.run_command('build')
            # If we built for any other platform, we can't install.
            build_plat = self.distribution.get_command_obj('build').plat_name
            # check warn_dir - it is a clue that the 'install' is happening
            # internally, and not to sys.path, so we don't check the platform
            # matches what we are running.
            if self.warn_dir and build_plat != get_platform():
                raise DistutilsPlatformError("Can't install when cross-compiling")

        # Run all sub-commands (at least those that need to be run)
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)

        if self.path_file:
            self.create_path_file()

        # write list of installed files, if requested.
        if self.record:
            outputs = self.get_outputs()
            if self.root:  # strip any package prefix
                root_len = len(self.root)
                for counter in range(len(outputs)):
                    outputs[counter] = outputs[counter][root_len:]
            self.execute(
                write_file,
                (self.record, outputs),
                f"writing list of installed files to '{self.record}'",
            )

        sys_path = map(os.path.normpath, sys.path)
        sys_path = map(os.path.normcase, sys_path)
        install_lib = os.path.normcase(os.path.normpath(self.install_lib))
        if (
            self.warn_dir
            and not (self.path_file and self.install_path_file)
            and install_lib not in sys_path
        ):
            log.debug(
                (
                    "modules installed to '%s', which is not in "
                    "Python's module search path (sys.path) -- "
                    "you'll have to change the search path yourself"
                ),
                self.install_lib,
            )

    def create_path_file(self):
        """Creates the .pth file"""
        filename = os.path.join(self.install_libbase, self.path_file + ".pth")
        if self.install_path_file:
            self.execute(
                write_file, (filename, [self.extra_dirs]), f"creating {filename}"
            )
        else:
            self.warn(f"path file '{filename}' not created")

    # -- Reporting methods ---------------------------------------------

    def get_outputs(self):
        """Assembles the outputs of all the sub-commands."""
        outputs = []
        for cmd_name in self.get_sub_commands():
            cmd = self.get_finalized_command(cmd_name)
            # Add the contents of cmd.get_outputs(), ensuring
            # that outputs doesn't contain duplicate entries
            for filename in cmd.get_outputs():
                if filename not in outputs:
                    outputs.append(filename)

        if self.path_file and self.install_path_file:
            outputs.append(os.path.join(self.install_libbase, self.path_file + ".pth"))

        return outputs

    def get_inputs(self):
        """Returns the inputs of all the sub-commands"""
        # XXX gee, this looks familiar ;-(
        inputs = []
        for cmd_name in self.get_sub_commands():
            cmd = self.get_finalized_command(cmd_name)
            inputs.extend(cmd.get_inputs())

        return inputs

    # -- Predicates for sub-command list -------------------------------

    def has_lib(self):
        """Returns true if the current distribution has any Python
        modules to install."""
        return (
            self.distribution.has_pure_modules() or self.distribution.has_ext_modules()
        )

    def has_headers(self):
        """Returns true if the current distribution has any headers to
        install."""
        return self.distribution.has_headers()

    def has_scripts(self):
        """Returns true if the current distribution has any scripts to.
        install."""
        return self.distribution.has_scripts()

    def has_data(self):
        """Returns true if the current distribution has any data to.
        install."""
        return self.distribution.has_data_files()

    # 'sub_commands': a list of commands this command might have to run to
    # get its work done.  See cmd.py for more info.
    sub_commands = [
        ('install_lib', has_lib),
        ('install_headers', has_headers),
        ('install_scripts', has_scripts),
        ('install_data', has_data),
        ('install_egg_info', lambda self: True),
    ]

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc4210.py ===
#
# This file is part of pyasn1-modules software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# Certificate Management Protocol structures as per RFC4210
#
# Based on Alex Railean's work
#
from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc2314
from pyasn1_modules import rfc2459
from pyasn1_modules import rfc2511

MAX = float('inf')


class KeyIdentifier(univ.OctetString):
    pass


class CMPCertificate(rfc2459.Certificate):
    pass


class OOBCert(CMPCertificate):
    pass


class CertAnnContent(CMPCertificate):
    pass


class PKIFreeText(univ.SequenceOf):
    """
    PKIFreeText ::= SEQUENCE SIZE (1..MAX) OF UTF8String
    """
    componentType = char.UTF8String()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


class PollRepContent(univ.SequenceOf):
    """
         PollRepContent ::= SEQUENCE OF SEQUENCE {
         certReqId              INTEGER,
         checkAfter             INTEGER,  -- time in seconds
         reason                 PKIFreeText OPTIONAL
     }
    """

    class CertReq(univ.Sequence):
        componentType = namedtype.NamedTypes(
            namedtype.NamedType('certReqId', univ.Integer()),
            namedtype.NamedType('checkAfter', univ.Integer()),
            namedtype.OptionalNamedType('reason', PKIFreeText())
        )

    componentType = CertReq()


class PollReqContent(univ.SequenceOf):
    """
         PollReqContent ::= SEQUENCE OF SEQUENCE {
         certReqId              INTEGER
     }

    """

    class CertReq(univ.Sequence):
        componentType = namedtype.NamedTypes(
            namedtype.NamedType('certReqId', univ.Integer())
        )

    componentType = CertReq()


class InfoTypeAndValue(univ.Sequence):
    """
    InfoTypeAndValue ::= SEQUENCE {
     infoType               OBJECT IDENTIFIER,
     infoValue              ANY DEFINED BY infoType  OPTIONAL
    }"""
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('infoType', univ.ObjectIdentifier()),
        namedtype.OptionalNamedType('infoValue', univ.Any())
    )


class GenRepContent(univ.SequenceOf):
    componentType = InfoTypeAndValue()


class GenMsgContent(univ.SequenceOf):
    componentType = InfoTypeAndValue()


class PKIConfirmContent(univ.Null):
    pass


class CRLAnnContent(univ.SequenceOf):
    componentType = rfc2459.CertificateList()


class CAKeyUpdAnnContent(univ.Sequence):
    """
    CAKeyUpdAnnContent ::= SEQUENCE {
         oldWithNew   CMPCertificate,
         newWithOld   CMPCertificate,
         newWithNew   CMPCertificate
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('oldWithNew', CMPCertificate()),
        namedtype.NamedType('newWithOld', CMPCertificate()),
        namedtype.NamedType('newWithNew', CMPCertificate())
    )


class RevDetails(univ.Sequence):
    """
    RevDetails ::= SEQUENCE {
         certDetails         CertTemplate,
         crlEntryDetails     Extensions       OPTIONAL
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('certDetails', rfc2511.CertTemplate()),
        namedtype.OptionalNamedType('crlEntryDetails', rfc2459.Extensions())
    )


class RevReqContent(univ.SequenceOf):
    componentType = RevDetails()


class CertOrEncCert(univ.Choice):
    """
     CertOrEncCert ::= CHOICE {
         certificate     [0] CMPCertificate,
         encryptedCert   [1] EncryptedValue
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('certificate', CMPCertificate().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.NamedType('encryptedCert', rfc2511.EncryptedValue().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
    )


class CertifiedKeyPair(univ.Sequence):
    """
    CertifiedKeyPair ::= SEQUENCE {
         certOrEncCert       CertOrEncCert,
         privateKey      [0] EncryptedValue      OPTIONAL,
         publicationInfo [1] PKIPublicationInfo  OPTIONAL
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('certOrEncCert', CertOrEncCert()),
        namedtype.OptionalNamedType('privateKey', rfc2511.EncryptedValue().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.OptionalNamedType('publicationInfo', rfc2511.PKIPublicationInfo().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
    )


class POPODecKeyRespContent(univ.SequenceOf):
    componentType = univ.Integer()


class Challenge(univ.Sequence):
    """
    Challenge ::= SEQUENCE {
         owf                 AlgorithmIdentifier  OPTIONAL,
         witness             OCTET STRING,
         challenge           OCTET STRING
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('owf', rfc2459.AlgorithmIdentifier()),
        namedtype.NamedType('witness', univ.OctetString()),
        namedtype.NamedType('challenge', univ.OctetString())
    )


class PKIStatus(univ.Integer):
    """
    PKIStatus ::= INTEGER {
         accepted                (0),
         grantedWithMods        (1),
         rejection              (2),
         waiting                (3),
         revocationWarning      (4),
         revocationNotification (5),
         keyUpdateWarning       (6)
     }
    """
    namedValues = namedval.NamedValues(
        ('accepted', 0),
        ('grantedWithMods', 1),
        ('rejection', 2),
        ('waiting', 3),
        ('revocationWarning', 4),
        ('revocationNotification', 5),
        ('keyUpdateWarning', 6)
    )


class PKIFailureInfo(univ.BitString):
    """
    PKIFailureInfo ::= BIT STRING {
         badAlg              (0),
         badMessageCheck     (1),
         badRequest          (2),
         badTime             (3),
         badCertId           (4),
         badDataFormat       (5),
         wrongAuthority      (6),
         incorrectData       (7),
         missingTimeStamp    (8),
         badPOP              (9),
         certRevoked         (10),
         certConfirmed       (11),
         wrongIntegrity      (12),
         badRecipientNonce   (13),
         timeNotAvailable    (14),
         unacceptedPolicy    (15),
         unacceptedExtension (16),
         addInfoNotAvailable (17),
         badSenderNonce      (18),
         badCertTemplate     (19),
         signerNotTrusted    (20),
         transactionIdInUse  (21),
         unsupportedVersion  (22),
         notAuthorized       (23),
         systemUnavail       (24),
         systemFailure       (25),
         duplicateCertReq    (26)
    """
    namedValues = namedval.NamedValues(
        ('badAlg', 0),
        ('badMessageCheck', 1),
        ('badRequest', 2),
        ('badTime', 3),
        ('badCertId', 4),
        ('badDataFormat', 5),
        ('wrongAuthority', 6),
        ('incorrectData', 7),
        ('missingTimeStamp', 8),
        ('badPOP', 9),
        ('certRevoked', 10),
        ('certConfirmed', 11),
        ('wrongIntegrity', 12),
        ('badRecipientNonce', 13),
        ('timeNotAvailable', 14),
        ('unacceptedPolicy', 15),
        ('unacceptedExtension', 16),
        ('addInfoNotAvailable', 17),
        ('badSenderNonce', 18),
        ('badCertTemplate', 19),
        ('signerNotTrusted', 20),
        ('transactionIdInUse', 21),
        ('unsupportedVersion', 22),
        ('notAuthorized', 23),
        ('systemUnavail', 24),
        ('systemFailure', 25),
        ('duplicateCertReq', 26)
    )


class PKIStatusInfo(univ.Sequence):
    """
    PKIStatusInfo ::= SEQUENCE {
         status        PKIStatus,
         statusString  PKIFreeText     OPTIONAL,
         failInfo      PKIFailureInfo  OPTIONAL
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('status', PKIStatus()),
        namedtype.OptionalNamedType('statusString', PKIFreeText()),
        namedtype.OptionalNamedType('failInfo', PKIFailureInfo())
    )


class ErrorMsgContent(univ.Sequence):
    """
    ErrorMsgContent ::= SEQUENCE {
         pKIStatusInfo          PKIStatusInfo,
         errorCode              INTEGER           OPTIONAL,
         -- implementation-specific error codes
         errorDetails           PKIFreeText       OPTIONAL
         -- implementation-specific error details
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('pKIStatusInfo', PKIStatusInfo()),
        namedtype.OptionalNamedType('errorCode', univ.Integer()),
        namedtype.OptionalNamedType('errorDetails', PKIFreeText())
    )


class CertStatus(univ.Sequence):
    """
    CertStatus ::= SEQUENCE {
        certHash    OCTET STRING,
        certReqId   INTEGER,
        statusInfo  PKIStatusInfo OPTIONAL
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('certHash', univ.OctetString()),
        namedtype.NamedType('certReqId', univ.Integer()),
        namedtype.OptionalNamedType('statusInfo', PKIStatusInfo())
    )


class CertConfirmContent(univ.SequenceOf):
    componentType = CertStatus()


class RevAnnContent(univ.Sequence):
    """
    RevAnnContent ::= SEQUENCE {
         status              PKIStatus,
         certId              CertId,
         willBeRevokedAt     GeneralizedTime,
         badSinceDate        GeneralizedTime,
         crlDetails          Extensions  OPTIONAL
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('status', PKIStatus()),
        namedtype.NamedType('certId', rfc2511.CertId()),
        namedtype.NamedType('willBeRevokedAt', useful.GeneralizedTime()),
        namedtype.NamedType('badSinceDate', useful.GeneralizedTime()),
        namedtype.OptionalNamedType('crlDetails', rfc2459.Extensions())
    )


class RevRepContent(univ.Sequence):
    """
    RevRepContent ::= SEQUENCE {
         status       SEQUENCE SIZE (1..MAX) OF PKIStatusInfo,
         revCerts [0] SEQUENCE SIZE (1..MAX) OF CertId
                                             OPTIONAL,
         crls     [1] SEQUENCE SIZE (1..MAX) OF CertificateList
                                             OPTIONAL
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType(
            'status', univ.SequenceOf(
                componentType=PKIStatusInfo(),
                sizeSpec=constraint.ValueSizeConstraint(1, MAX)
            )
        ),
        namedtype.OptionalNamedType(
            'revCerts', univ.SequenceOf(componentType=rfc2511.CertId()).subtype(
                sizeSpec=constraint.ValueSizeConstraint(1, MAX),
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)
            )
        ),
        namedtype.OptionalNamedType(
            'crls', univ.SequenceOf(componentType=rfc2459.CertificateList()).subtype(
                sizeSpec=constraint.ValueSizeConstraint(1, MAX),
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)
            )
        )
    )


class KeyRecRepContent(univ.Sequence):
    """
    KeyRecRepContent ::= SEQUENCE {
         status                  PKIStatusInfo,
         newSigCert          [0] CMPCertificate OPTIONAL,
         caCerts             [1] SEQUENCE SIZE (1..MAX) OF
                                             CMPCertificate OPTIONAL,
         keyPairHist         [2] SEQUENCE SIZE (1..MAX) OF
                                             CertifiedKeyPair OPTIONAL
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('status', PKIStatusInfo()),
        namedtype.OptionalNamedType(
            'newSigCert', CMPCertificate().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)
            )
        ),
        namedtype.OptionalNamedType(
            'caCerts', univ.SequenceOf(componentType=CMPCertificate()).subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1),
                sizeSpec=constraint.ValueSizeConstraint(1, MAX)
            )
        ),
        namedtype.OptionalNamedType('keyPairHist', univ.SequenceOf(componentType=CertifiedKeyPair()).subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2),
            sizeSpec=constraint.ValueSizeConstraint(1, MAX))
        )
    )


class CertResponse(univ.Sequence):
    """
    CertResponse ::= SEQUENCE {
         certReqId           INTEGER,
         status              PKIStatusInfo,
         certifiedKeyPair    CertifiedKeyPair    OPTIONAL,
         rspInfo             OCTET STRING        OPTIONAL
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('certReqId', univ.Integer()),
        namedtype.NamedType('status', PKIStatusInfo()),
        namedtype.OptionalNamedType('certifiedKeyPair', CertifiedKeyPair()),
        namedtype.OptionalNamedType('rspInfo', univ.OctetString())
    )


class CertRepMessage(univ.Sequence):
    """
    CertRepMessage ::= SEQUENCE {
         caPubs       [1] SEQUENCE SIZE (1..MAX) OF CMPCertificate
                          OPTIONAL,
         response         SEQUENCE OF CertResponse
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType(
            'caPubs', univ.SequenceOf(
                componentType=CMPCertificate()
            ).subtype(sizeSpec=constraint.ValueSizeConstraint(1, MAX),
                      explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))
        ),
        namedtype.NamedType('response', univ.SequenceOf(componentType=CertResponse()))
    )


class POPODecKeyChallContent(univ.SequenceOf):
    componentType = Challenge()


class OOBCertHash(univ.Sequence):
    """
    OOBCertHash ::= SEQUENCE {
         hashAlg     [0] AlgorithmIdentifier     OPTIONAL,
         certId      [1] CertId                  OPTIONAL,
         hashVal         BIT STRING
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType(
            'hashAlg', rfc2459.AlgorithmIdentifier().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))
        ),
        namedtype.OptionalNamedType(
            'certId', rfc2511.CertId().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))
        ),
        namedtype.NamedType('hashVal', univ.BitString())
    )


# pyasn1 does not naturally handle recursive definitions, thus this hack:
# NestedMessageContent ::= PKIMessages
class NestedMessageContent(univ.SequenceOf):
    """
    NestedMessageContent ::= PKIMessages
    """
    componentType = univ.Any()


class DHBMParameter(univ.Sequence):
    """
    DHBMParameter ::= SEQUENCE {
         owf                 AlgorithmIdentifier,
         -- AlgId for a One-Way Function (SHA-1 recommended)
         mac                 AlgorithmIdentifier
         -- the MAC AlgId (e.g., DES-MAC, Triple-DES-MAC [PKCS11],
     }   -- or HMAC [RFC2104, RFC2202])
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('owf', rfc2459.AlgorithmIdentifier()),
        namedtype.NamedType('mac', rfc2459.AlgorithmIdentifier())
    )


id_DHBasedMac = univ.ObjectIdentifier('1.2.840.113533.7.66.30')


class PBMParameter(univ.Sequence):
    """
    PBMParameter ::= SEQUENCE {
         salt                OCTET STRING,
         owf                 AlgorithmIdentifier,
         iterationCount      INTEGER,
         mac                 AlgorithmIdentifier
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType(
            'salt', univ.OctetString().subtype(subtypeSpec=constraint.ValueSizeConstraint(0, 128))
        ),
        namedtype.NamedType('owf', rfc2459.AlgorithmIdentifier()),
        namedtype.NamedType('iterationCount', univ.Integer()),
        namedtype.NamedType('mac', rfc2459.AlgorithmIdentifier())
    )


id_PasswordBasedMac = univ.ObjectIdentifier('1.2.840.113533.7.66.13')


class PKIProtection(univ.BitString):
    pass


# pyasn1 does not naturally handle recursive definitions, thus this hack:
# NestedMessageContent ::= PKIMessages
nestedMessageContent = NestedMessageContent().subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 20))


class PKIBody(univ.Choice):
    """
    PKIBody ::= CHOICE {       -- message-specific body elements
         ir       [0]  CertReqMessages,        --Initialization Request
         ip       [1]  CertRepMessage,         --Initialization Response
         cr       [2]  CertReqMessages,        --Certification Request
         cp       [3]  CertRepMessage,         --Certification Response
         p10cr    [4]  CertificationRequest,   --imported from [PKCS10]
         popdecc  [5]  POPODecKeyChallContent, --pop Challenge
         popdecr  [6]  POPODecKeyRespContent,  --pop Response
         kur      [7]  CertReqMessages,        --Key Update Request
         kup      [8]  CertRepMessage,         --Key Update Response
         krr      [9]  CertReqMessages,        --Key Recovery Request
         krp      [10] KeyRecRepContent,       --Key Recovery Response
         rr       [11] RevReqContent,          --Revocation Request
         rp       [12] RevRepContent,          --Revocation Response
         ccr      [13] CertReqMessages,        --Cross-Cert. Request
         ccp      [14] CertRepMessage,         --Cross-Cert. Response
         ckuann   [15] CAKeyUpdAnnContent,     --CA Key Update Ann.
         cann     [16] CertAnnContent,         --Certificate Ann.
         rann     [17] RevAnnContent,          --Revocation Ann.
         crlann   [18] CRLAnnContent,          --CRL Announcement
         pkiconf  [19] PKIConfirmContent,      --Confirmation
         nested   [20] NestedMessageContent,   --Nested Message
         genm     [21] GenMsgContent,          --General Message
         genp     [22] GenRepContent,          --General Response
         error    [23] ErrorMsgContent,        --Error Message
         certConf [24] CertConfirmContent,     --Certificate confirm
         pollReq  [25] PollReqContent,         --Polling request
         pollRep  [26] PollRepContent          --Polling response

    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType(
            'ir', rfc2511.CertReqMessages().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)
            )
        ),
        namedtype.NamedType(
            'ip', CertRepMessage().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)
            )
        ),
        namedtype.NamedType(
            'cr', rfc2511.CertReqMessages().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2)
            )
        ),
        namedtype.NamedType(
            'cp', CertRepMessage().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3)
            )
        ),
        namedtype.NamedType(
            'p10cr', rfc2314.CertificationRequest().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4)
            )
        ),
        namedtype.NamedType(
            'popdecc', POPODecKeyChallContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5)
            )
        ),
        namedtype.NamedType(
            'popdecr', POPODecKeyRespContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6)
            )
        ),
        namedtype.NamedType(
            'kur', rfc2511.CertReqMessages().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 7)
            )
        ),
        namedtype.NamedType(
            'kup', CertRepMessage().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 8)
            )
        ),
        namedtype.NamedType(
            'krr', rfc2511.CertReqMessages().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 9)
            )
        ),
        namedtype.NamedType(
            'krp', KeyRecRepContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 10)
            )
        ),
        namedtype.NamedType(
            'rr', RevReqContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 11)
            )
        ),
        namedtype.NamedType(
            'rp', RevRepContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 12)
            )
        ),
        namedtype.NamedType(
            'ccr', rfc2511.CertReqMessages().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 13)
            )
        ),
        namedtype.NamedType(
            'ccp', CertRepMessage().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 14)
            )
        ),
        namedtype.NamedType(
            'ckuann', CAKeyUpdAnnContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 15)
            )
        ),
        namedtype.NamedType(
            'cann', CertAnnContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 16)
            )
        ),
        namedtype.NamedType(
            'rann', RevAnnContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 17)
            )
        ),
        namedtype.NamedType(
            'crlann', CRLAnnContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 18)
            )
        ),
        namedtype.NamedType(
            'pkiconf', PKIConfirmContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 19)
            )
        ),
        namedtype.NamedType(
            'nested', nestedMessageContent
        ),
        #        namedtype.NamedType('nested', NestedMessageContent().subtype(
        #            explicitTag=tag.Tag(tag.tagClassContext,tag.tagFormatConstructed,20)
        #            )
        #        ),
        namedtype.NamedType(
            'genm', GenMsgContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 21)
            )
        ),
        namedtype.NamedType(
            'gen', GenRepContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 22)
            )
        ),
        namedtype.NamedType(
            'error', ErrorMsgContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 23)
            )
        ),
        namedtype.NamedType(
            'certConf', CertConfirmContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 24)
            )
        ),
        namedtype.NamedType(
            'pollReq', PollReqContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 25)
            )
        ),
        namedtype.NamedType(
            'pollRep', PollRepContent().subtype(
                explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 26)
            )
        )
    )


class PKIHeader(univ.Sequence):
    """
    PKIHeader ::= SEQUENCE {
    pvno                INTEGER     { cmp1999(1), cmp2000(2) },
    sender              GeneralName,
    recipient           GeneralName,
    messageTime     [0] GeneralizedTime         OPTIONAL,
    protectionAlg   [1] AlgorithmIdentifier     OPTIONAL,
    senderKID       [2] KeyIdentifier           OPTIONAL,
    recipKID        [3] KeyIdentifier           OPTIONAL,
    transactionID   [4] OCTET STRING            OPTIONAL,
    senderNonce     [5] OCTET STRING            OPTIONAL,
    recipNonce      [6] OCTET STRING            OPTIONAL,
    freeText        [7] PKIFreeText             OPTIONAL,
    generalInfo     [8] SEQUENCE SIZE (1..MAX) OF
                     InfoTypeAndValue     OPTIONAL
    }

    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType(
            'pvno', univ.Integer(
                namedValues=namedval.NamedValues(('cmp1999', 1), ('cmp2000', 2))
            )
        ),
        namedtype.NamedType('sender', rfc2459.GeneralName()),
        namedtype.NamedType('recipient', rfc2459.GeneralName()),
        namedtype.OptionalNamedType('messageTime', useful.GeneralizedTime().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('protectionAlg', rfc2459.AlgorithmIdentifier().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.OptionalNamedType('senderKID', rfc2459.KeyIdentifier().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.OptionalNamedType('recipKID', rfc2459.KeyIdentifier().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
        namedtype.OptionalNamedType('transactionID', univ.OctetString().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))),
        namedtype.OptionalNamedType('senderNonce', univ.OctetString().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 5))),
        namedtype.OptionalNamedType('recipNonce', univ.OctetString().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 6))),
        namedtype.OptionalNamedType('freeText', PKIFreeText().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 7))),
        namedtype.OptionalNamedType('generalInfo',
                                    univ.SequenceOf(
                                        componentType=InfoTypeAndValue().subtype(
                                            sizeSpec=constraint.ValueSizeConstraint(1, MAX)
                                        )
                                    ).subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 8))
        )
    )


class ProtectedPart(univ.Sequence):
    """
     ProtectedPart ::= SEQUENCE {
         header    PKIHeader,
         body      PKIBody
     }
    """
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('header', PKIHeader()),
        namedtype.NamedType('infoValue', PKIBody())
    )


class PKIMessage(univ.Sequence):
    """
    PKIMessage ::= SEQUENCE {
    header           PKIHeader,
    body             PKIBody,
    protection   [0] PKIProtection OPTIONAL,
    extraCerts   [1] SEQUENCE SIZE (1..MAX) OF CMPCertificate
                  OPTIONAL
     }"""
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('header', PKIHeader()),
        namedtype.NamedType('body', PKIBody()),
        namedtype.OptionalNamedType('protection', PKIProtection().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('extraCerts',
                                    univ.SequenceOf(
                                        componentType=CMPCertificate()
                                    ).subtype(
                                        sizeSpec=constraint.ValueSizeConstraint(1, MAX),
                                        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)
                                    )
                                    )
    )


class PKIMessages(univ.SequenceOf):
    """
    PKIMessages ::= SEQUENCE SIZE (1..MAX) OF PKIMessage
    """
    componentType = PKIMessage()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


# pyasn1 does not naturally handle recursive definitions, thus this hack:
# NestedMessageContent ::= PKIMessages
NestedMessageContent._componentType = PKIMessages()
nestedMessageContent._componentType = PKIMessages()

# === NexusCore/openenv\Lib\site-packages\win32com\server\policy.py ===
"""Policies

Note that Dispatchers are now implemented in "dispatcher.py", but
are still documented here.

Policies

 A policy is an object which manages the interaction between a public
 Python object, and COM .  In simple terms, the policy object is the
 object which is actually called by COM, and it invokes the requested
 method, fetches/sets the requested property, etc.  See the
 @win32com.server.policy.CreateInstance@ method for a description of
 how a policy is specified or created.

 Exactly how a policy determines which underlying object method/property
 is obtained is up to the policy.  A few policies are provided, but you
 can build your own.  See each policy class for a description of how it
 implements its policy.

 There is a policy that allows the object to specify exactly which
 methods and properties will be exposed.  There is also a policy that
 will dynamically expose all Python methods and properties - even those
 added after the object has been instantiated.

Dispatchers

 A Dispatcher is a level in front of a Policy.  A dispatcher is the
 thing which actually receives the COM calls, and passes them to the
 policy object (which in turn somehow does something with the wrapped
 object).

 It is important to note that a policy does not need to have a dispatcher.
 A dispatcher has the same interface as a policy, and simply steps in its
 place, delegating to the real policy.  The primary use for a Dispatcher
 is to support debugging when necessary, but without imposing overheads
 when not (ie, by not using a dispatcher at all).

 There are a few dispatchers provided - "tracing" dispatchers which simply
 prints calls and args (including a variation which uses
 win32api.OutputDebugString), and a "debugger" dispatcher, which can
 invoke the debugger when necessary.

Error Handling

 It is important to realise that the caller of these interfaces may
 not be Python.  Therefore, general Python exceptions and tracebacks aren't
 much use.

 In general, there is an COMException class that should be raised, to allow
 the framework to extract rich COM type error information.

 The general rule is that the **only** exception returned from Python COM
 Server code should be an COMException instance.  Any other Python exception
 should be considered an implementation bug in the server (if not, it
 should be handled, and an appropriate COMException instance raised).  Any
 other exception is considered "unexpected", and a dispatcher may take
 special action (see Dispatchers above)

 Occasionally, the implementation will raise the policy.error error.
 This usually means there is a problem in the implementation that the
 Python programmer should fix.

 For example, if policy is asked to wrap an object which it can not
 support (because, eg, it does not provide _public_methods_ or _dynamic_)
 then policy.error will be raised, indicating it is a Python programmers
 problem, rather than a COM error.
"""

import sys
import types

import pythoncom
import pywintypes
import win32api
import win32con
import winerror

# Import a few important constants to speed lookups.
from pythoncom import (
    DISPATCH_METHOD,
    DISPATCH_PROPERTYGET,
    DISPATCH_PROPERTYPUT,
    DISPATCH_PROPERTYPUTREF,
    DISPID_EVALUATE,
    DISPID_NEWENUM,
    DISPID_PROPERTYPUT,
    DISPID_STARTENUM,
    DISPID_VALUE,
)

from .exception import COMException

__author__ = "Greg Stein and Mark Hammond"

S_OK = 0

# Few more globals to speed things.
IDispatchType = pythoncom.TypeIIDs[pythoncom.IID_IDispatch]
IUnknownType = pythoncom.TypeIIDs[pythoncom.IID_IUnknown]


regSpec = "CLSID\\%s\\PythonCOM"
regPolicy = "CLSID\\%s\\PythonCOMPolicy"
regDispatcher = "CLSID\\%s\\PythonCOMDispatcher"
regAddnPath = "CLSID\\%s\\PythonCOMPath"


def CreateInstance(clsid, reqIID):
    """Create a new instance of the specified IID

    The COM framework **always** calls this function to create a new
    instance for the specified CLSID.  This function looks up the
    registry for the name of a policy, creates the policy, and asks the
    policy to create the specified object by calling the _CreateInstance_ method.

    Exactly how the policy creates the instance is up to the policy.  See the
    specific policy documentation for more details.
    """
    # First see is sys.path should have something on it.
    try:
        addnPaths = win32api.RegQueryValue(
            win32con.HKEY_CLASSES_ROOT, regAddnPath % clsid
        ).split(";")
        for newPath in addnPaths:
            if newPath not in sys.path:
                sys.path.insert(0, newPath)
    except win32api.error:
        pass
    try:
        policy = win32api.RegQueryValue(win32con.HKEY_CLASSES_ROOT, regPolicy % clsid)
        policy = resolve_func(policy)
    except win32api.error:
        policy = DefaultPolicy

    try:
        dispatcher = win32api.RegQueryValue(
            win32con.HKEY_CLASSES_ROOT, regDispatcher % clsid
        )
        if dispatcher:
            dispatcher = resolve_func(dispatcher)
    except win32api.error:
        dispatcher = None

    if dispatcher:
        retObj = dispatcher(policy, None)
    else:
        retObj = policy(None)
    return retObj._CreateInstance_(clsid, reqIID)


class BasicWrapPolicy:
    """The base class of policies.

    Normally not used directly (use a child class, instead)

    This policy assumes we are wrapping another object
    as the COM server.  This supports the delegation of the core COM entry points
    to either the wrapped object, or to a child class.

    This policy supports the following special attributes on the wrapped object

    _query_interface_ -- A handler which can respond to the COM 'QueryInterface' call.
    _com_interfaces_ -- An optional list of IIDs which the interface will assume are
        valid for the object.
    _invoke_ -- A handler which can respond to the COM 'Invoke' call.  If this attribute
        is not provided, then the default policy implementation is used.  If this attribute
        does exist, it is responsible for providing all required functionality - ie, the
        policy _invoke_ method is not invoked at all (and nor are you able to call it!)
    _getidsofnames_ -- A handler which can respond to the COM 'GetIDsOfNames' call.  If this attribute
        is not provided, then the default policy implementation is used.  If this attribute
        does exist, it is responsible for providing all required functionality - ie, the
        policy _getidsofnames_ method is not invoked at all (and nor are you able to call it!)

    IDispatchEx functionality:

    _invokeex_ -- Very similar to _invoke_, except slightly different arguments are used.
        And the result is just the _real_ result (rather than the (hresult, argErr, realResult)
        tuple that _invoke_ uses.
        This is the new, prefered handler (the default _invoke_ handler simply called _invokeex_)
    _getdispid_ -- Very similar to _getidsofnames_, except slightly different arguments are used,
        and only 1 property at a time can be fetched (which is all we support in getidsofnames anyway!)
        This is the new, prefered handler (the default _invoke_ handler simply called _invokeex_)
    _getnextdispid_- uses self._name_to_dispid_ to enumerate the DISPIDs
    """

    def __init__(self, object):
        """Initialise the policy object

        Params:

        object -- The object to wrap.  May be None *iff* @BasicWrapPolicy._CreateInstance_@ will be
        called immediately after this to setup a brand new object
        """
        if object is not None:
            self._wrap_(object)

    def _CreateInstance_(self, clsid, reqIID):
        """Creates a new instance of a **wrapped** object

        This method looks up a "@win32com.server.policy.regSpec@" % clsid entry
        in the registry (using @DefaultPolicy@)
        """
        try:
            classSpec = win32api.RegQueryValue(
                win32con.HKEY_CLASSES_ROOT, regSpec % clsid
            )
        except win32api.error:
            raise ValueError(
                f"The object is not correctly registered - {regSpec % clsid} key can not be read"
            )
        myob = call_func(classSpec)
        self._wrap_(myob)
        try:
            return pythoncom.WrapObject(self, reqIID)
        except pythoncom.com_error as xxx_todo_changeme:
            (hr, desc, exc, arg) = xxx_todo_changeme.args
            from win32com.util import IIDToInterfaceName

            desc = (
                f"The object '{myob!r}' was created, but does not support the "
                f"interface '{IIDToInterfaceName(reqIID)}'({reqIID}): {desc}"
            )
            raise pythoncom.com_error(hr, desc, exc, arg)

    def _wrap_(self, object):
        """Wraps up the specified object.

        This function keeps a reference to the passed
        object, and may interogate it to determine how to respond to COM requests, etc.
        """
        # We "clobber" certain of our own methods with ones
        # provided by the wrapped object, iff they exist.
        self._name_to_dispid_ = {}
        ob = self._obj_ = object
        if hasattr(ob, "_query_interface_"):
            self._query_interface_ = ob._query_interface_

        if hasattr(ob, "_invoke_"):
            self._invoke_ = ob._invoke_

        if hasattr(ob, "_invokeex_"):
            self._invokeex_ = ob._invokeex_

        if hasattr(ob, "_getidsofnames_"):
            self._getidsofnames_ = ob._getidsofnames_

        if hasattr(ob, "_getdispid_"):
            self._getdispid_ = ob._getdispid_

        # Allow for override of certain special attributes.
        if hasattr(ob, "_com_interfaces_"):
            self._com_interfaces_ = []
            # Allow interfaces to be specified by name.
            for i in ob._com_interfaces_:
                if not isinstance(i, pywintypes.IIDType):
                    # Prolly a string!
                    if i[0] != "{":
                        i = pythoncom.InterfaceNames[i]
                    else:
                        i = pythoncom.MakeIID(i)
                self._com_interfaces_.append(i)
        else:
            self._com_interfaces_ = []

    # "QueryInterface" handling.
    def _QueryInterface_(self, iid):
        """The main COM entry-point for QueryInterface.

        This checks the _com_interfaces_ attribute and if the interface is not specified
        there, it calls the derived helper _query_interface_
        """
        if iid in self._com_interfaces_:
            return 1
        return self._query_interface_(iid)

    def _query_interface_(self, iid):
        """Called if the object does not provide the requested interface in _com_interfaces_,
        and does not provide a _query_interface_ handler.

        Returns a result to the COM framework indicating the interface is not supported.
        """
        return 0

    # "Invoke" handling.
    def _Invoke_(self, dispid, lcid, wFlags, args):
        """The main COM entry-point for Invoke.

        This calls the _invoke_ helper.
        """
        # Translate a possible string dispid to real dispid.
        if isinstance(dispid, str):
            try:
                dispid = self._name_to_dispid_[dispid.lower()]
            except KeyError:
                raise COMException(
                    scode=winerror.DISP_E_MEMBERNOTFOUND, desc="Member not found"
                )
        return self._invoke_(dispid, lcid, wFlags, args)

    def _invoke_(self, dispid, lcid, wFlags, args):
        # Delegates to the _invokeex_ implementation.  This allows
        # a custom policy to define _invokeex_, and automatically get _invoke_ too.
        return S_OK, -1, self._invokeex_(dispid, lcid, wFlags, args, None, None)

    # "GetIDsOfNames" handling.
    def _GetIDsOfNames_(self, names, lcid):
        """The main COM entry-point for GetIDsOfNames.

        This checks the validity of the arguments, and calls the _getidsofnames_ helper.
        """
        if len(names) > 1:
            raise COMException(
                scode=winerror.DISP_E_INVALID,
                desc="Cannot support member argument names",
            )
        return self._getidsofnames_(names, lcid)

    def _getidsofnames_(self, names, lcid):
        ### note: lcid is being ignored...
        return (self._getdispid_(names[0], 0),)

    # IDispatchEx support for policies.  Most of the IDispathEx functionality
    # by default will raise E_NOTIMPL.  Thus it is not necessary for derived
    # policies to explicitly implement all this functionality just to not implement it!

    def _GetDispID_(self, name, fdex):
        return self._getdispid_(name, fdex)

    def _getdispid_(self, name, fdex):
        try:
            ### TODO - look at the fdex flags!!!
            return self._name_to_dispid_[name.lower()]
        except KeyError:
            raise COMException(scode=winerror.DISP_E_UNKNOWNNAME)

    # "InvokeEx" handling.
    def _InvokeEx_(self, dispid, lcid, wFlags, args, kwargs, serviceProvider):
        """The main COM entry-point for InvokeEx.

        This calls the _invokeex_ helper.
        """
        # Translate a possible string dispid to real dispid.
        if isinstance(dispid, str):
            try:
                dispid = self._name_to_dispid_[dispid.lower()]
            except KeyError:
                raise COMException(
                    scode=winerror.DISP_E_MEMBERNOTFOUND, desc="Member not found"
                )
        return self._invokeex_(dispid, lcid, wFlags, args, kwargs, serviceProvider)

    def _invokeex_(self, dispid, lcid, wFlags, args, kwargs, serviceProvider):
        """A stub for _invokeex_ - should never be called.

        Simply raises an exception.
        """
        # Base classes should override this method (and not call the base)
        raise NotImplementedError("This class does not provide _invokeex_ semantics")

    def _DeleteMemberByName_(self, name, fdex):
        return self._deletememberbyname_(name, fdex)

    def _deletememberbyname_(self, name, fdex):
        raise COMException(scode=winerror.E_NOTIMPL)

    def _DeleteMemberByDispID_(self, id):
        return self._deletememberbydispid(id)

    def _deletememberbydispid_(self, id):
        raise COMException(scode=winerror.E_NOTIMPL)

    def _GetMemberProperties_(self, id, fdex):
        return self._getmemberproperties_(id, fdex)

    def _getmemberproperties_(self, id, fdex):
        raise COMException(scode=winerror.E_NOTIMPL)

    def _GetMemberName_(self, dispid):
        return self._getmembername_(dispid)

    def _getmembername_(self, dispid):
        raise COMException(scode=winerror.E_NOTIMPL)

    def _GetNextDispID_(self, fdex, dispid):
        return self._getnextdispid_(fdex, dispid)

    def _getnextdispid_(self, fdex, dispid):
        ids = [id for id in self._name_to_dispid_.values() if id != DISPID_STARTENUM]
        ids.sort()
        if dispid == DISPID_STARTENUM:
            return ids[0]
        else:
            try:
                return ids[ids.index(dispid) + 1]
            except ValueError:  # dispid not in list?
                raise COMException(scode=winerror.E_UNEXPECTED)
            except IndexError:  # No more items
                raise COMException(scode=winerror.S_FALSE)

    def _GetNameSpaceParent_(self):
        return self._getnamespaceparent()

    def _getnamespaceparent_(self):
        raise COMException(scode=winerror.E_NOTIMPL)


class MappedWrapPolicy(BasicWrapPolicy):
    """Wraps an object using maps to do its magic

    This policy wraps up a Python object, using a number of maps
    which translate from a Dispatch ID and flags, into an object to call/getattr, etc.

    It is the responsibility of derived classes to determine exactly how the
    maps are filled (ie, the derived classes determine the map filling policy.

    This policy supports the following special attributes on the wrapped object

    _dispid_to_func_/_dispid_to_get_/_dispid_to_put_ -- These are dictionaries
      (keyed by integer dispid, values are string attribute names) which the COM
      implementation uses when it is processing COM requests.  Note that the implementation
      uses this dictionary for its own purposes - not a copy - which means the contents of
      these dictionaries will change as the object is used.

    """

    def _wrap_(self, object):
        BasicWrapPolicy._wrap_(self, object)
        ob = self._obj_
        if hasattr(ob, "_dispid_to_func_"):
            self._dispid_to_func_ = ob._dispid_to_func_
        else:
            self._dispid_to_func_ = {}
        if hasattr(ob, "_dispid_to_get_"):
            self._dispid_to_get_ = ob._dispid_to_get_
        else:
            self._dispid_to_get_ = {}
        if hasattr(ob, "_dispid_to_put_"):
            self._dispid_to_put_ = ob._dispid_to_put_
        else:
            self._dispid_to_put_ = {}

    def _getmembername_(self, dispid):
        if dispid in self._dispid_to_func_:
            return self._dispid_to_func_[dispid]
        elif dispid in self._dispid_to_get_:
            return self._dispid_to_get_[dispid]
        elif dispid in self._dispid_to_put_:
            return self._dispid_to_put_[dispid]
        else:
            raise COMException(scode=winerror.DISP_E_MEMBERNOTFOUND)


class DesignatedWrapPolicy(MappedWrapPolicy):
    """A policy which uses a mapping to link functions and dispid

     A MappedWrappedPolicy which allows the wrapped object to specify, via certain
     special named attributes, exactly which methods and properties are exposed.

     All a wrapped object need do is provide the special attributes, and the policy
     will handle everything else.

     Attributes:

     _public_methods_ -- Required, unless a typelib GUID is given -- A list
                  of strings, which must be the names of methods the object
                  provides.  These methods will be exposed and callable
                  from other COM hosts.
     _public_attrs_ A list of strings, which must be the names of attributes on the object.
                  These attributes will be exposed and readable and possibly writeable from other COM hosts.
     _readonly_attrs_ -- A list of strings, which must also appear in _public_attrs.  These
                  attributes will be readable, but not writable, by other COM hosts.
     _value_ -- A method that will be called if the COM host requests the "default" method
                  (ie, calls Invoke with dispid==DISPID_VALUE)
     _NewEnum -- A method that will be called if the COM host requests an enumerator on the
                  object (ie, calls Invoke with dispid==DISPID_NEWENUM.)
                  It is the responsibility of the method to ensure the returned
                  object conforms to the required Enum interface.

    _typelib_guid_ -- The GUID of the typelibrary with interface definitions we use.
    _typelib_version_ -- A tuple of (major, minor) with a default of 1,1
    _typelib_lcid_ -- The LCID of the typelib, default = LOCALE_USER_DEFAULT

     _Evaluate -- Dunno what this means, except the host has called Invoke with dispid==DISPID_EVALUATE!
                  See the COM documentation for details.
    """

    def _wrap_(self, ob):
        # If we have nominated universal interfaces to support, load them now
        tlb_guid = getattr(ob, "_typelib_guid_", None)
        if tlb_guid is not None:
            tlb_major, tlb_minor = getattr(ob, "_typelib_version_", (1, 0))
            tlb_lcid = getattr(ob, "_typelib_lcid_", 0)
            from win32com import universal

            # XXX - what if the user wants to implement interfaces from multiple
            # typelibs?
            # Filter out all 'normal' IIDs (ie, IID objects and strings starting with {
            interfaces = [
                i
                for i in getattr(ob, "_com_interfaces_", [])
                if not isinstance(i, pywintypes.IIDType) and not i.startswith("{")
            ]
            universal_data = universal.RegisterInterfaces(
                tlb_guid, tlb_lcid, tlb_major, tlb_minor, interfaces
            )
        else:
            universal_data = []
        MappedWrapPolicy._wrap_(self, ob)
        if not hasattr(ob, "_public_methods_") and not hasattr(ob, "_typelib_guid_"):
            raise ValueError(
                "Object does not support DesignatedWrapPolicy, "
                + "as it does not have either _public_methods_ or _typelib_guid_ attributes.",
            )

        # Copy existing _dispid_to_func_ entries to _name_to_dispid_
        for dispid, name in self._dispid_to_func_.items():
            self._name_to_dispid_[name.lower()] = dispid
        for dispid, name in self._dispid_to_get_.items():
            self._name_to_dispid_[name.lower()] = dispid
        for dispid, name in self._dispid_to_put_.items():
            self._name_to_dispid_[name.lower()] = dispid

        # Patch up the universal stuff.
        for dispid, invkind, name in universal_data:
            self._name_to_dispid_[name.lower()] = dispid
            if invkind == DISPATCH_METHOD:
                self._dispid_to_func_[dispid] = name
            elif invkind in (DISPATCH_PROPERTYPUT, DISPATCH_PROPERTYPUTREF):
                self._dispid_to_put_[dispid] = name
            elif invkind == DISPATCH_PROPERTYGET:
                self._dispid_to_get_[dispid] = name
            else:
                raise ValueError("unexpected invkind: %d (%s)" % (invkind, name))

        # look for reserved methods
        if hasattr(ob, "_value_"):
            self._dispid_to_get_[DISPID_VALUE] = "_value_"
            self._dispid_to_put_[DISPID_PROPERTYPUT] = "_value_"
        if hasattr(ob, "_NewEnum"):
            self._name_to_dispid_["_newenum"] = DISPID_NEWENUM
            self._dispid_to_func_[DISPID_NEWENUM] = "_NewEnum"
        if hasattr(ob, "_Evaluate"):
            self._name_to_dispid_["_evaluate"] = DISPID_EVALUATE
            self._dispid_to_func_[DISPID_EVALUATE] = "_Evaluate"

        next_dispid = self._allocnextdispid(999)
        # note: funcs have precedence over attrs (install attrs first)
        if hasattr(ob, "_public_attrs_"):
            if hasattr(ob, "_readonly_attrs_"):
                readonly = ob._readonly_attrs_
            else:
                readonly = []
            for name in ob._public_attrs_:
                dispid = self._name_to_dispid_.get(name.lower())
                if dispid is None:
                    dispid = next_dispid
                    self._name_to_dispid_[name.lower()] = dispid
                    next_dispid = self._allocnextdispid(next_dispid)
                self._dispid_to_get_[dispid] = name
                if name not in readonly:
                    self._dispid_to_put_[dispid] = name
        for name in getattr(ob, "_public_methods_", []):
            dispid = self._name_to_dispid_.get(name.lower())
            if dispid is None:
                dispid = next_dispid
                self._name_to_dispid_[name.lower()] = dispid
                next_dispid = self._allocnextdispid(next_dispid)
            self._dispid_to_func_[dispid] = name
        self._typeinfos_ = None  # load these on demand.

    def _build_typeinfos_(self):
        # Can only ever be one for now.
        tlb_guid = getattr(self._obj_, "_typelib_guid_", None)
        if tlb_guid is None:
            return []
        tlb_major, tlb_minor = getattr(self._obj_, "_typelib_version_", (1, 0))
        tlb = pythoncom.LoadRegTypeLib(tlb_guid, tlb_major, tlb_minor)
        typecomp = tlb.GetTypeComp()
        # Not 100% sure what semantics we should use for the default interface.
        # Look for the first name in _com_interfaces_ that exists in the typelib.
        for iname in self._obj_._com_interfaces_:
            try:
                type_info, type_comp = typecomp.BindType(iname)
                if type_info is not None:
                    return [type_info]
            except pythoncom.com_error:
                pass
        return []

    def _GetTypeInfoCount_(self):
        if self._typeinfos_ is None:
            self._typeinfos_ = self._build_typeinfos_()
        return len(self._typeinfos_)

    def _GetTypeInfo_(self, index, lcid):
        if self._typeinfos_ is None:
            self._typeinfos_ = self._build_typeinfos_()
        if index < 0 or index >= len(self._typeinfos_):
            raise COMException(scode=winerror.DISP_E_BADINDEX)
        return 0, self._typeinfos_[index]

    def _allocnextdispid(self, last_dispid):
        while 1:
            last_dispid += 1
            if (
                last_dispid not in self._dispid_to_func_
                and last_dispid not in self._dispid_to_get_
                and last_dispid not in self._dispid_to_put_
            ):
                return last_dispid

    def _invokeex_(self, dispid, lcid, wFlags, args, kwArgs, serviceProvider):
        ### note: lcid is being ignored...

        if wFlags & DISPATCH_METHOD:
            try:
                funcname = self._dispid_to_func_[dispid]
            except KeyError:
                if not wFlags & DISPATCH_PROPERTYGET:
                    raise COMException(
                        scode=winerror.DISP_E_MEMBERNOTFOUND
                    )  # not found
            else:
                try:
                    func = getattr(self._obj_, funcname)
                except AttributeError:
                    # May have a dispid, but that doesn't mean we have the function!
                    raise COMException(scode=winerror.DISP_E_MEMBERNOTFOUND)
                # Should check callable here
                try:
                    return func(*args)
                except TypeError as v:
                    # Particularly nasty is "wrong number of args" type error
                    # This helps you see what 'func' and 'args' actually is
                    if str(v).find("arguments") >= 0:
                        print(f"** TypeError {v} calling function {func!r}({args!r})")
                    raise

        if wFlags & DISPATCH_PROPERTYGET:
            try:
                name = self._dispid_to_get_[dispid]
            except KeyError:
                raise COMException(scode=winerror.DISP_E_MEMBERNOTFOUND)  # not found
            retob = getattr(self._obj_, name)
            if isinstance(retob, types.MethodType):  # a method as a property - call it.
                retob = retob(*args)
            return retob

        if wFlags & (DISPATCH_PROPERTYPUT | DISPATCH_PROPERTYPUTREF):  ### correct?
            try:
                name = self._dispid_to_put_[dispid]
            except KeyError:
                raise COMException(scode=winerror.DISP_E_MEMBERNOTFOUND)  # read-only
            # If we have a method of that name (ie, a property get function), and
            # we have an equiv. property set function, use that instead.
            fn = getattr(self._obj_, "Set" + name, None)
            if isinstance(fn, types.MethodType) and isinstance(
                getattr(self._obj_, name, None), types.MethodType
            ):
                fn(*args)
            else:
                # just set the attribute
                setattr(self._obj_, name, args[0])
            return

        raise COMException(scode=winerror.E_INVALIDARG, desc="invalid wFlags")


class EventHandlerPolicy(DesignatedWrapPolicy):
    """The default policy used by event handlers in the win32com.client package.

    In addition to the base policy, this provides argument conversion semantics for
    params: dispatch params are converted to dispatch objects

    NOTE: Later, we may allow the object to override this process??
    """

    def _transform_args_(self, args, kwArgs, dispid, lcid, wFlags, serviceProvider):
        ret = []
        for arg in args:
            if isinstance(arg, IDispatchType):
                import win32com.client

                arg = win32com.client.Dispatch(arg)
            elif isinstance(arg, IUnknownType):
                try:
                    import win32com.client

                    arg = win32com.client.Dispatch(
                        arg.QueryInterface(pythoncom.IID_IDispatch)
                    )
                except pythoncom.error:
                    pass  # Keep it as IUnknown
            ret.append(arg)
        return tuple(ret), kwArgs

    def _invokeex_(self, dispid, lcid, wFlags, args, kwArgs, serviceProvider):
        # transform the args.
        args, kwArgs = self._transform_args_(
            args, kwArgs, dispid, lcid, wFlags, serviceProvider
        )
        return DesignatedWrapPolicy._invokeex_(
            self, dispid, lcid, wFlags, args, kwArgs, serviceProvider
        )


class DynamicPolicy(BasicWrapPolicy):
    """A policy which dynamically (ie, at run-time) determines public interfaces.

    A dynamic policy is used to dynamically dispatch methods and properties to the
    wrapped object.  The list of objects and properties does not need to be known in
    advance, and methods or properties added to the wrapped object after construction
    are also handled.

    The wrapped object must provide the following attributes:

    _dynamic_ -- A method that will be called whenever an invoke on the object
           is called.  The method is called with the name of the underlying method/property
           (ie, the mapping of dispid to/from name has been resolved.)  This name property
           may also be '_value_' to indicate the default, and '_NewEnum' to indicate a new
           enumerator is requested.

    """

    def _wrap_(self, object):
        BasicWrapPolicy._wrap_(self, object)
        if not hasattr(self._obj_, "_dynamic_"):
            raise ValueError("Object does not support Dynamic COM Policy")
        self._next_dynamic_ = self._min_dynamic_ = 1000
        self._dyn_dispid_to_name_ = {
            DISPID_VALUE: "_value_",
            DISPID_NEWENUM: "_NewEnum",
        }

    def _getdispid_(self, name, fdex):
        # TODO - Look at fdex flags.
        lname = name.lower()
        try:
            return self._name_to_dispid_[lname]
        except KeyError:
            dispid = self._next_dynamic_ = self._next_dynamic_ + 1
            self._name_to_dispid_[lname] = dispid
            self._dyn_dispid_to_name_[dispid] = name  # Keep case in this map...
            return dispid

    def _invoke_(self, dispid, lcid, wFlags, args):
        return S_OK, -1, self._invokeex_(dispid, lcid, wFlags, args, None, None)

    def _invokeex_(self, dispid, lcid, wFlags, args, kwargs, serviceProvider):
        ### note: lcid is being ignored...
        ### note: kwargs is being ignored...
        ### note: serviceProvider is being ignored...
        ### there might be assigned DISPID values to properties, too...
        try:
            name = self._dyn_dispid_to_name_[dispid]
        except KeyError:
            raise COMException(
                scode=winerror.DISP_E_MEMBERNOTFOUND, desc="Member not found"
            )
        return self._obj_._dynamic_(name, lcid, wFlags, args)


DefaultPolicy = DesignatedWrapPolicy


def resolve_func(spec):
    """Resolve a function by name

    Given a function specified by 'module.function', return a callable object
    (ie, the function itself)
    """
    try:
        idx = spec.rindex(".")
        mname = spec[:idx]
        fname = spec[idx + 1 :]
        # Don't attempt to optimize by looking in sys.modules,
        # as another thread may also be performing the import - this
        # way we take advantage of the built-in import lock.
        module = _import_module(mname)
        return getattr(module, fname)
    except ValueError:  # No "." in name - assume in this module
        return globals()[spec]


def call_func(spec, *args):
    """Call a function specified by name.

    Call a function specified by 'module.function' and return the result.
    """

    return resolve_func(spec)(*args)


def _import_module(mname):
    """Import a module just like the 'import' statement.

    Having this function is much nicer for importing arbitrary modules than
    using the 'exec' keyword.  It is more efficient and obvious to the reader.
    """
    __import__(mname)
    # Eeek - result of _import_ is "win32com" - not "win32com.a.b.c"
    # Get the full module from sys.modules
    return sys.modules[mname]

# === NexusCore/openenv\Lib\site-packages\matplotlib\_constrained_layout.py ===
"""
Adjust subplot layouts so that there are no overlapping Axes or Axes
decorations.  All Axes decorations are dealt with (labels, ticks, titles,
ticklabels) and some dependent artists are also dealt with (colorbar,
suptitle).

Layout is done via `~matplotlib.gridspec`, with one constraint per gridspec,
so it is possible to have overlapping Axes if the gridspecs overlap (i.e.
using `~matplotlib.gridspec.GridSpecFromSubplotSpec`).  Axes placed using
``figure.subplots()`` or ``figure.add_subplots()`` will participate in the
layout.  Axes manually placed via ``figure.add_axes()`` will not.

See Tutorial: :ref:`constrainedlayout_guide`

General idea:
-------------

First, a figure has a gridspec that divides the figure into nrows and ncols,
with heights and widths set by ``height_ratios`` and ``width_ratios``,
often just set to 1 for an equal grid.

Subplotspecs that are derived from this gridspec can contain either a
``SubPanel``, a ``GridSpecFromSubplotSpec``, or an ``Axes``.  The ``SubPanel``
and ``GridSpecFromSubplotSpec`` are dealt with recursively and each contain an
analogous layout.

Each ``GridSpec`` has a ``_layoutgrid`` attached to it.  The ``_layoutgrid``
has the same logical layout as the ``GridSpec``.   Each row of the grid spec
has a top and bottom "margin" and each column has a left and right "margin".
The "inner" height of each row is constrained to be the same (or as modified
by ``height_ratio``), and the "inner" width of each column is
constrained to be the same (as modified by ``width_ratio``), where "inner"
is the width or height of each column/row minus the size of the margins.

Then the size of the margins for each row and column are determined as the
max width of the decorators on each Axes that has decorators in that margin.
For instance, a normal Axes would have a left margin that includes the
left ticklabels, and the ylabel if it exists.  The right margin may include a
colorbar, the bottom margin the xaxis decorations, and the top margin the
title.

With these constraints, the solver then finds appropriate bounds for the
columns and rows.  It's possible that the margins take up the whole figure,
in which case the algorithm is not applied and a warning is raised.

See the tutorial :ref:`constrainedlayout_guide`
for more discussion of the algorithm with examples.
"""

import logging

import numpy as np

from matplotlib import _api, artist as martist
import matplotlib.transforms as mtransforms
import matplotlib._layoutgrid as mlayoutgrid


_log = logging.getLogger(__name__)


######################################################
def do_constrained_layout(fig, h_pad, w_pad,
                          hspace=None, wspace=None, rect=(0, 0, 1, 1),
                          compress=False):
    """
    Do the constrained_layout.  Called at draw time in
     ``figure.constrained_layout()``

    Parameters
    ----------
    fig : `~matplotlib.figure.Figure`
        `.Figure` instance to do the layout in.

    h_pad, w_pad : float
      Padding around the Axes elements in figure-normalized units.

    hspace, wspace : float
       Fraction of the figure to dedicate to space between the
       Axes.  These are evenly spread between the gaps between the Axes.
       A value of 0.2 for a three-column layout would have a space
       of 0.1 of the figure width between each column.
       If h/wspace < h/w_pad, then the pads are used instead.

    rect : tuple of 4 floats
        Rectangle in figure coordinates to perform constrained layout in
        [left, bottom, width, height], each from 0-1.

    compress : bool
        Whether to shift Axes so that white space in between them is
        removed. This is useful for simple grids of fixed-aspect Axes (e.g.
        a grid of images).

    Returns
    -------
    layoutgrid : private debugging structure
    """

    renderer = fig._get_renderer()
    # make layoutgrid tree...
    layoutgrids = make_layoutgrids(fig, None, rect=rect)
    if not layoutgrids['hasgrids']:
        _api.warn_external('There are no gridspecs with layoutgrids. '
                           'Possibly did not call parent GridSpec with the'
                           ' "figure" keyword')
        return

    for _ in range(2):
        # do the algorithm twice.  This has to be done because decorations
        # change size after the first re-position (i.e. x/yticklabels get
        # larger/smaller).  This second reposition tends to be much milder,
        # so doing twice makes things work OK.

        # make margins for all the Axes and subfigures in the
        # figure.  Add margins for colorbars...
        make_layout_margins(layoutgrids, fig, renderer, h_pad=h_pad,
                            w_pad=w_pad, hspace=hspace, wspace=wspace)
        make_margin_suptitles(layoutgrids, fig, renderer, h_pad=h_pad,
                              w_pad=w_pad)

        # if a layout is such that a columns (or rows) margin has no
        # constraints, we need to make all such instances in the grid
        # match in margin size.
        match_submerged_margins(layoutgrids, fig)

        # update all the variables in the layout.
        layoutgrids[fig].update_variables()

        warn_collapsed = ('constrained_layout not applied because '
                          'axes sizes collapsed to zero.  Try making '
                          'figure larger or Axes decorations smaller.')
        if check_no_collapsed_axes(layoutgrids, fig):
            reposition_axes(layoutgrids, fig, renderer, h_pad=h_pad,
                            w_pad=w_pad, hspace=hspace, wspace=wspace)
            if compress:
                layoutgrids = compress_fixed_aspect(layoutgrids, fig)
                layoutgrids[fig].update_variables()
                if check_no_collapsed_axes(layoutgrids, fig):
                    reposition_axes(layoutgrids, fig, renderer, h_pad=h_pad,
                                    w_pad=w_pad, hspace=hspace, wspace=wspace)
                else:
                    _api.warn_external(warn_collapsed)

                if ((suptitle := fig._suptitle) is not None and
                        suptitle.get_in_layout() and suptitle._autopos):
                    x, _ = suptitle.get_position()
                    suptitle.set_position(
                        (x, layoutgrids[fig].get_inner_bbox().y1 + h_pad))
                    suptitle.set_verticalalignment('bottom')
        else:
            _api.warn_external(warn_collapsed)
        reset_margins(layoutgrids, fig)
    return layoutgrids


def make_layoutgrids(fig, layoutgrids, rect=(0, 0, 1, 1)):
    """
    Make the layoutgrid tree.

    (Sub)Figures get a layoutgrid so we can have figure margins.

    Gridspecs that are attached to Axes get a layoutgrid so Axes
    can have margins.
    """

    if layoutgrids is None:
        layoutgrids = dict()
        layoutgrids['hasgrids'] = False
    if not hasattr(fig, '_parent'):
        # top figure;  pass rect as parent to allow user-specified
        # margins
        layoutgrids[fig] = mlayoutgrid.LayoutGrid(parent=rect, name='figlb')
    else:
        # subfigure
        gs = fig._subplotspec.get_gridspec()
        # it is possible the gridspec containing this subfigure hasn't
        # been added to the tree yet:
        layoutgrids = make_layoutgrids_gs(layoutgrids, gs)
        # add the layoutgrid for the subfigure:
        parentlb = layoutgrids[gs]
        layoutgrids[fig] = mlayoutgrid.LayoutGrid(
            parent=parentlb,
            name='panellb',
            parent_inner=True,
            nrows=1, ncols=1,
            parent_pos=(fig._subplotspec.rowspan,
                        fig._subplotspec.colspan))
    # recursively do all subfigures in this figure...
    for sfig in fig.subfigs:
        layoutgrids = make_layoutgrids(sfig, layoutgrids)

    # for each Axes at the local level add its gridspec:
    for ax in fig._localaxes:
        gs = ax.get_gridspec()
        if gs is not None:
            layoutgrids = make_layoutgrids_gs(layoutgrids, gs)

    return layoutgrids


def make_layoutgrids_gs(layoutgrids, gs):
    """
    Make the layoutgrid for a gridspec (and anything nested in the gridspec)
    """

    if gs in layoutgrids or gs.figure is None:
        return layoutgrids
    # in order to do constrained_layout there has to be at least *one*
    # gridspec in the tree:
    layoutgrids['hasgrids'] = True
    if not hasattr(gs, '_subplot_spec'):
        # normal gridspec
        parent = layoutgrids[gs.figure]
        layoutgrids[gs] = mlayoutgrid.LayoutGrid(
                parent=parent,
                parent_inner=True,
                name='gridspec',
                ncols=gs._ncols, nrows=gs._nrows,
                width_ratios=gs.get_width_ratios(),
                height_ratios=gs.get_height_ratios())
    else:
        # this is a gridspecfromsubplotspec:
        subplot_spec = gs._subplot_spec
        parentgs = subplot_spec.get_gridspec()
        # if a nested gridspec it is possible the parent is not in there yet:
        if parentgs not in layoutgrids:
            layoutgrids = make_layoutgrids_gs(layoutgrids, parentgs)
        subspeclb = layoutgrids[parentgs]
        # gridspecfromsubplotspec need an outer container:
        # get a unique representation:
        rep = (gs, 'top')
        if rep not in layoutgrids:
            layoutgrids[rep] = mlayoutgrid.LayoutGrid(
                parent=subspeclb,
                name='top',
                nrows=1, ncols=1,
                parent_pos=(subplot_spec.rowspan, subplot_spec.colspan))
        layoutgrids[gs] = mlayoutgrid.LayoutGrid(
                parent=layoutgrids[rep],
                name='gridspec',
                nrows=gs._nrows, ncols=gs._ncols,
                width_ratios=gs.get_width_ratios(),
                height_ratios=gs.get_height_ratios())
    return layoutgrids


def check_no_collapsed_axes(layoutgrids, fig):
    """
    Check that no Axes have collapsed to zero size.
    """
    for sfig in fig.subfigs:
        ok = check_no_collapsed_axes(layoutgrids, sfig)
        if not ok:
            return False
    for ax in fig.axes:
        gs = ax.get_gridspec()
        if gs in layoutgrids:  # also implies gs is not None.
            lg = layoutgrids[gs]
            for i in range(gs.nrows):
                for j in range(gs.ncols):
                    bb = lg.get_inner_bbox(i, j)
                    if bb.width <= 0 or bb.height <= 0:
                        return False
    return True


def compress_fixed_aspect(layoutgrids, fig):
    gs = None
    for ax in fig.axes:
        if ax.get_subplotspec() is None:
            continue
        ax.apply_aspect()
        sub = ax.get_subplotspec()
        _gs = sub.get_gridspec()
        if gs is None:
            gs = _gs
            extraw = np.zeros(gs.ncols)
            extrah = np.zeros(gs.nrows)
        elif _gs != gs:
            raise ValueError('Cannot do compressed layout if Axes are not'
                             'all from the same gridspec')
        orig = ax.get_position(original=True)
        actual = ax.get_position(original=False)
        dw = orig.width - actual.width
        if dw > 0:
            extraw[sub.colspan] = np.maximum(extraw[sub.colspan], dw)
        dh = orig.height - actual.height
        if dh > 0:
            extrah[sub.rowspan] = np.maximum(extrah[sub.rowspan], dh)

    if gs is None:
        raise ValueError('Cannot do compressed layout if no Axes '
                         'are part of a gridspec.')
    w = np.sum(extraw) / 2
    layoutgrids[fig].edit_margin_min('left', w)
    layoutgrids[fig].edit_margin_min('right', w)

    h = np.sum(extrah) / 2
    layoutgrids[fig].edit_margin_min('top', h)
    layoutgrids[fig].edit_margin_min('bottom', h)
    return layoutgrids


def get_margin_from_padding(obj, *, w_pad=0, h_pad=0,
                            hspace=0, wspace=0):

    ss = obj._subplotspec
    gs = ss.get_gridspec()

    if hasattr(gs, 'hspace'):
        _hspace = (gs.hspace if gs.hspace is not None else hspace)
        _wspace = (gs.wspace if gs.wspace is not None else wspace)
    else:
        _hspace = (gs._hspace if gs._hspace is not None else hspace)
        _wspace = (gs._wspace if gs._wspace is not None else wspace)

    _wspace = _wspace / 2
    _hspace = _hspace / 2

    nrows, ncols = gs.get_geometry()
    # there are two margins for each direction.  The "cb"
    # margins are for pads and colorbars, the non-"cb" are
    # for the Axes decorations (labels etc).
    margin = {'leftcb': w_pad, 'rightcb': w_pad,
              'bottomcb': h_pad, 'topcb': h_pad,
              'left': 0, 'right': 0,
              'top': 0, 'bottom': 0}
    if _wspace / ncols > w_pad:
        if ss.colspan.start > 0:
            margin['leftcb'] = _wspace / ncols
        if ss.colspan.stop < ncols:
            margin['rightcb'] = _wspace / ncols
    if _hspace / nrows > h_pad:
        if ss.rowspan.stop < nrows:
            margin['bottomcb'] = _hspace / nrows
        if ss.rowspan.start > 0:
            margin['topcb'] = _hspace / nrows

    return margin


def make_layout_margins(layoutgrids, fig, renderer, *, w_pad=0, h_pad=0,
                        hspace=0, wspace=0):
    """
    For each Axes, make a margin between the *pos* layoutbox and the
    *axes* layoutbox be a minimum size that can accommodate the
    decorations on the axis.

    Then make room for colorbars.

    Parameters
    ----------
    layoutgrids : dict
    fig : `~matplotlib.figure.Figure`
        `.Figure` instance to do the layout in.
    renderer : `~matplotlib.backend_bases.RendererBase` subclass.
        The renderer to use.
    w_pad, h_pad : float, default: 0
        Width and height padding (in fraction of figure).
    hspace, wspace : float, default: 0
        Width and height padding as fraction of figure size divided by
        number of columns or rows.
    """
    for sfig in fig.subfigs:  # recursively make child panel margins
        ss = sfig._subplotspec
        gs = ss.get_gridspec()

        make_layout_margins(layoutgrids, sfig, renderer,
                            w_pad=w_pad, h_pad=h_pad,
                            hspace=hspace, wspace=wspace)

        margins = get_margin_from_padding(sfig, w_pad=0, h_pad=0,
                                          hspace=hspace, wspace=wspace)
        layoutgrids[gs].edit_outer_margin_mins(margins, ss)

    for ax in fig._localaxes:
        if not ax.get_subplotspec() or not ax.get_in_layout():
            continue

        ss = ax.get_subplotspec()
        gs = ss.get_gridspec()

        if gs not in layoutgrids:
            return

        margin = get_margin_from_padding(ax, w_pad=w_pad, h_pad=h_pad,
                                         hspace=hspace, wspace=wspace)
        pos, bbox = get_pos_and_bbox(ax, renderer)
        # the margin is the distance between the bounding box of the Axes
        # and its position (plus the padding from above)
        margin['left'] += pos.x0 - bbox.x0
        margin['right'] += bbox.x1 - pos.x1
        # remember that rows are ordered from top:
        margin['bottom'] += pos.y0 - bbox.y0
        margin['top'] += bbox.y1 - pos.y1

        # make margin for colorbars.  These margins go in the
        # padding margin, versus the margin for Axes decorators.
        for cbax in ax._colorbars:
            # note pad is a fraction of the parent width...
            pad = colorbar_get_pad(layoutgrids, cbax)
            # colorbars can be child of more than one subplot spec:
            cbp_rspan, cbp_cspan = get_cb_parent_spans(cbax)
            loc = cbax._colorbar_info['location']
            cbpos, cbbbox = get_pos_and_bbox(cbax, renderer)
            if loc == 'right':
                if cbp_cspan.stop == ss.colspan.stop:
                    # only increase if the colorbar is on the right edge
                    margin['rightcb'] += cbbbox.width + pad
            elif loc == 'left':
                if cbp_cspan.start == ss.colspan.start:
                    # only increase if the colorbar is on the left edge
                    margin['leftcb'] += cbbbox.width + pad
            elif loc == 'top':
                if cbp_rspan.start == ss.rowspan.start:
                    margin['topcb'] += cbbbox.height + pad
            else:
                if cbp_rspan.stop == ss.rowspan.stop:
                    margin['bottomcb'] += cbbbox.height + pad
            # If the colorbars are wider than the parent box in the
            # cross direction
            if loc in ['top', 'bottom']:
                if (cbp_cspan.start == ss.colspan.start and
                        cbbbox.x0 < bbox.x0):
                    margin['left'] += bbox.x0 - cbbbox.x0
                if (cbp_cspan.stop == ss.colspan.stop and
                        cbbbox.x1 > bbox.x1):
                    margin['right'] += cbbbox.x1 - bbox.x1
            # or taller:
            if loc in ['left', 'right']:
                if (cbp_rspan.stop == ss.rowspan.stop and
                        cbbbox.y0 < bbox.y0):
                    margin['bottom'] += bbox.y0 - cbbbox.y0
                if (cbp_rspan.start == ss.rowspan.start and
                        cbbbox.y1 > bbox.y1):
                    margin['top'] += cbbbox.y1 - bbox.y1
        # pass the new margins down to the layout grid for the solution...
        layoutgrids[gs].edit_outer_margin_mins(margin, ss)

    # make margins for figure-level legends:
    for leg in fig.legends:
        inv_trans_fig = None
        if leg._outside_loc and leg._bbox_to_anchor is None:
            if inv_trans_fig is None:
                inv_trans_fig = fig.transFigure.inverted().transform_bbox
            bbox = inv_trans_fig(leg.get_tightbbox(renderer))
            w = bbox.width + 2 * w_pad
            h = bbox.height + 2 * h_pad
            legendloc = leg._outside_loc
            if legendloc == 'lower':
                layoutgrids[fig].edit_margin_min('bottom', h)
            elif legendloc == 'upper':
                layoutgrids[fig].edit_margin_min('top', h)
            if legendloc == 'right':
                layoutgrids[fig].edit_margin_min('right', w)
            elif legendloc == 'left':
                layoutgrids[fig].edit_margin_min('left', w)


def make_margin_suptitles(layoutgrids, fig, renderer, *, w_pad=0, h_pad=0):
    # Figure out how large the suptitle is and make the
    # top level figure margin larger.

    inv_trans_fig = fig.transFigure.inverted().transform_bbox
    # get the h_pad and w_pad as distances in the local subfigure coordinates:
    padbox = mtransforms.Bbox([[0, 0], [w_pad, h_pad]])
    padbox = (fig.transFigure -
              fig.transSubfigure).transform_bbox(padbox)
    h_pad_local = padbox.height
    w_pad_local = padbox.width

    for sfig in fig.subfigs:
        make_margin_suptitles(layoutgrids, sfig, renderer,
                              w_pad=w_pad, h_pad=h_pad)

    if fig._suptitle is not None and fig._suptitle.get_in_layout():
        p = fig._suptitle.get_position()
        if getattr(fig._suptitle, '_autopos', False):
            fig._suptitle.set_position((p[0], 1 - h_pad_local))
            bbox = inv_trans_fig(fig._suptitle.get_tightbbox(renderer))
            layoutgrids[fig].edit_margin_min('top', bbox.height + 2 * h_pad)

    if fig._supxlabel is not None and fig._supxlabel.get_in_layout():
        p = fig._supxlabel.get_position()
        if getattr(fig._supxlabel, '_autopos', False):
            fig._supxlabel.set_position((p[0], h_pad_local))
            bbox = inv_trans_fig(fig._supxlabel.get_tightbbox(renderer))
            layoutgrids[fig].edit_margin_min('bottom',
                                             bbox.height + 2 * h_pad)

    if fig._supylabel is not None and fig._supylabel.get_in_layout():
        p = fig._supylabel.get_position()
        if getattr(fig._supylabel, '_autopos', False):
            fig._supylabel.set_position((w_pad_local, p[1]))
            bbox = inv_trans_fig(fig._supylabel.get_tightbbox(renderer))
            layoutgrids[fig].edit_margin_min('left', bbox.width + 2 * w_pad)


def match_submerged_margins(layoutgrids, fig):
    """
    Make the margins that are submerged inside an Axes the same size.

    This allows Axes that span two columns (or rows) that are offset
    from one another to have the same size.

    This gives the proper layout for something like::
        fig = plt.figure(constrained_layout=True)
        axs = fig.subplot_mosaic("AAAB\nCCDD")

    Without this routine, the Axes D will be wider than C, because the
    margin width between the two columns in C has no width by default,
    whereas the margins between the two columns of D are set by the
    width of the margin between A and B. However, obviously the user would
    like C and D to be the same size, so we need to add constraints to these
    "submerged" margins.

    This routine makes all the interior margins the same, and the spacing
    between the three columns in A and the two column in C are all set to the
    margins between the two columns of D.

    See test_constrained_layout::test_constrained_layout12 for an example.
    """

    for sfig in fig.subfigs:
        match_submerged_margins(layoutgrids, sfig)

    axs = [a for a in fig.get_axes()
           if a.get_subplotspec() is not None and a.get_in_layout()]

    for ax1 in axs:
        ss1 = ax1.get_subplotspec()
        if ss1.get_gridspec() not in layoutgrids:
            axs.remove(ax1)
            continue
        lg1 = layoutgrids[ss1.get_gridspec()]

        # interior columns:
        if len(ss1.colspan) > 1:
            maxsubl = np.max(
                lg1.margin_vals['left'][ss1.colspan[1:]] +
                lg1.margin_vals['leftcb'][ss1.colspan[1:]]
            )
            maxsubr = np.max(
                lg1.margin_vals['right'][ss1.colspan[:-1]] +
                lg1.margin_vals['rightcb'][ss1.colspan[:-1]]
            )
            for ax2 in axs:
                ss2 = ax2.get_subplotspec()
                lg2 = layoutgrids[ss2.get_gridspec()]
                if lg2 is not None and len(ss2.colspan) > 1:
                    maxsubl2 = np.max(
                        lg2.margin_vals['left'][ss2.colspan[1:]] +
                        lg2.margin_vals['leftcb'][ss2.colspan[1:]])
                    if maxsubl2 > maxsubl:
                        maxsubl = maxsubl2
                    maxsubr2 = np.max(
                        lg2.margin_vals['right'][ss2.colspan[:-1]] +
                        lg2.margin_vals['rightcb'][ss2.colspan[:-1]])
                    if maxsubr2 > maxsubr:
                        maxsubr = maxsubr2
            for i in ss1.colspan[1:]:
                lg1.edit_margin_min('left', maxsubl, cell=i)
            for i in ss1.colspan[:-1]:
                lg1.edit_margin_min('right', maxsubr, cell=i)

        # interior rows:
        if len(ss1.rowspan) > 1:
            maxsubt = np.max(
                lg1.margin_vals['top'][ss1.rowspan[1:]] +
                lg1.margin_vals['topcb'][ss1.rowspan[1:]]
            )
            maxsubb = np.max(
                lg1.margin_vals['bottom'][ss1.rowspan[:-1]] +
                lg1.margin_vals['bottomcb'][ss1.rowspan[:-1]]
            )

            for ax2 in axs:
                ss2 = ax2.get_subplotspec()
                lg2 = layoutgrids[ss2.get_gridspec()]
                if lg2 is not None:
                    if len(ss2.rowspan) > 1:
                        maxsubt = np.max([np.max(
                            lg2.margin_vals['top'][ss2.rowspan[1:]] +
                            lg2.margin_vals['topcb'][ss2.rowspan[1:]]
                        ), maxsubt])
                        maxsubb = np.max([np.max(
                            lg2.margin_vals['bottom'][ss2.rowspan[:-1]] +
                            lg2.margin_vals['bottomcb'][ss2.rowspan[:-1]]
                        ), maxsubb])
            for i in ss1.rowspan[1:]:
                lg1.edit_margin_min('top', maxsubt, cell=i)
            for i in ss1.rowspan[:-1]:
                lg1.edit_margin_min('bottom', maxsubb, cell=i)


def get_cb_parent_spans(cbax):
    """
    Figure out which subplotspecs this colorbar belongs to.

    Parameters
    ----------
    cbax : `~matplotlib.axes.Axes`
        Axes for the colorbar.
    """
    rowstart = np.inf
    rowstop = -np.inf
    colstart = np.inf
    colstop = -np.inf
    for parent in cbax._colorbar_info['parents']:
        ss = parent.get_subplotspec()
        rowstart = min(ss.rowspan.start, rowstart)
        rowstop = max(ss.rowspan.stop, rowstop)
        colstart = min(ss.colspan.start, colstart)
        colstop = max(ss.colspan.stop, colstop)

    rowspan = range(rowstart, rowstop)
    colspan = range(colstart, colstop)
    return rowspan, colspan


def get_pos_and_bbox(ax, renderer):
    """
    Get the position and the bbox for the Axes.

    Parameters
    ----------
    ax : `~matplotlib.axes.Axes`
    renderer : `~matplotlib.backend_bases.RendererBase` subclass.

    Returns
    -------
    pos : `~matplotlib.transforms.Bbox`
        Position in figure coordinates.
    bbox : `~matplotlib.transforms.Bbox`
        Tight bounding box in figure coordinates.
    """
    fig = ax.get_figure(root=False)
    pos = ax.get_position(original=True)
    # pos is in panel co-ords, but we need in figure for the layout
    pos = pos.transformed(fig.transSubfigure - fig.transFigure)
    tightbbox = martist._get_tightbbox_for_layout_only(ax, renderer)
    if tightbbox is None:
        bbox = pos
    else:
        bbox = tightbbox.transformed(fig.transFigure.inverted())
    return pos, bbox


def reposition_axes(layoutgrids, fig, renderer, *,
                    w_pad=0, h_pad=0, hspace=0, wspace=0):
    """
    Reposition all the Axes based on the new inner bounding box.
    """
    trans_fig_to_subfig = fig.transFigure - fig.transSubfigure
    for sfig in fig.subfigs:
        bbox = layoutgrids[sfig].get_outer_bbox()
        sfig._redo_transform_rel_fig(
            bbox=bbox.transformed(trans_fig_to_subfig))
        reposition_axes(layoutgrids, sfig, renderer,
                        w_pad=w_pad, h_pad=h_pad,
                        wspace=wspace, hspace=hspace)

    for ax in fig._localaxes:
        if ax.get_subplotspec() is None or not ax.get_in_layout():
            continue

        # grid bbox is in Figure coordinates, but we specify in panel
        # coordinates...
        ss = ax.get_subplotspec()
        gs = ss.get_gridspec()
        if gs not in layoutgrids:
            return

        bbox = layoutgrids[gs].get_inner_bbox(rows=ss.rowspan,
                                              cols=ss.colspan)

        # transform from figure to panel for set_position:
        newbbox = trans_fig_to_subfig.transform_bbox(bbox)
        ax._set_position(newbbox)

        # move the colorbars:
        # we need to keep track of oldw and oldh if there is more than
        # one colorbar:
        offset = {'left': 0, 'right': 0, 'bottom': 0, 'top': 0}
        for nn, cbax in enumerate(ax._colorbars[::-1]):
            if ax == cbax._colorbar_info['parents'][0]:
                reposition_colorbar(layoutgrids, cbax, renderer,
                                    offset=offset)


def reposition_colorbar(layoutgrids, cbax, renderer, *, offset=None):
    """
    Place the colorbar in its new place.

    Parameters
    ----------
    layoutgrids : dict
    cbax : `~matplotlib.axes.Axes`
        Axes for the colorbar.
    renderer : `~matplotlib.backend_bases.RendererBase` subclass.
        The renderer to use.
    offset : array-like
        Offset the colorbar needs to be pushed to in order to
        account for multiple colorbars.
    """

    parents = cbax._colorbar_info['parents']
    gs = parents[0].get_gridspec()
    fig = cbax.get_figure(root=False)
    trans_fig_to_subfig = fig.transFigure - fig.transSubfigure

    cb_rspans, cb_cspans = get_cb_parent_spans(cbax)
    bboxparent = layoutgrids[gs].get_bbox_for_cb(rows=cb_rspans,
                                                 cols=cb_cspans)
    pb = layoutgrids[gs].get_inner_bbox(rows=cb_rspans, cols=cb_cspans)

    location = cbax._colorbar_info['location']
    anchor = cbax._colorbar_info['anchor']
    fraction = cbax._colorbar_info['fraction']
    aspect = cbax._colorbar_info['aspect']
    shrink = cbax._colorbar_info['shrink']

    cbpos, cbbbox = get_pos_and_bbox(cbax, renderer)

    # Colorbar gets put at extreme edge of outer bbox of the subplotspec
    # It needs to be moved in by: 1) a pad 2) its "margin" 3) by
    # any colorbars already added at this location:
    cbpad = colorbar_get_pad(layoutgrids, cbax)
    if location in ('left', 'right'):
        # fraction and shrink are fractions of parent
        pbcb = pb.shrunk(fraction, shrink).anchored(anchor, pb)
        # The colorbar is at the left side of the parent.  Need
        # to translate to right (or left)
        if location == 'right':
            lmargin = cbpos.x0 - cbbbox.x0
            dx = bboxparent.x1 - pbcb.x0 + offset['right']
            dx += cbpad + lmargin
            offset['right'] += cbbbox.width + cbpad
            pbcb = pbcb.translated(dx, 0)
        else:
            lmargin = cbpos.x0 - cbbbox.x0
            dx = bboxparent.x0 - pbcb.x0  # edge of parent
            dx += -cbbbox.width - cbpad + lmargin - offset['left']
            offset['left'] += cbbbox.width + cbpad
            pbcb = pbcb.translated(dx, 0)
    else:  # horizontal axes:
        pbcb = pb.shrunk(shrink, fraction).anchored(anchor, pb)
        if location == 'top':
            bmargin = cbpos.y0 - cbbbox.y0
            dy = bboxparent.y1 - pbcb.y0 + offset['top']
            dy += cbpad + bmargin
            offset['top'] += cbbbox.height + cbpad
            pbcb = pbcb.translated(0, dy)
        else:
            bmargin = cbpos.y0 - cbbbox.y0
            dy = bboxparent.y0 - pbcb.y0
            dy += -cbbbox.height - cbpad + bmargin - offset['bottom']
            offset['bottom'] += cbbbox.height + cbpad
            pbcb = pbcb.translated(0, dy)

    pbcb = trans_fig_to_subfig.transform_bbox(pbcb)
    cbax.set_transform(fig.transSubfigure)
    cbax._set_position(pbcb)
    cbax.set_anchor(anchor)
    if location in ['bottom', 'top']:
        aspect = 1 / aspect
    cbax.set_box_aspect(aspect)
    cbax.set_aspect('auto')
    return offset


def reset_margins(layoutgrids, fig):
    """
    Reset the margins in the layoutboxes of *fig*.

    Margins are usually set as a minimum, so if the figure gets smaller
    the minimum needs to be zero in order for it to grow again.
    """
    for sfig in fig.subfigs:
        reset_margins(layoutgrids, sfig)
    for ax in fig.axes:
        if ax.get_in_layout():
            gs = ax.get_gridspec()
            if gs in layoutgrids:  # also implies gs is not None.
                layoutgrids[gs].reset_margins()
    layoutgrids[fig].reset_margins()


def colorbar_get_pad(layoutgrids, cax):
    parents = cax._colorbar_info['parents']
    gs = parents[0].get_gridspec()

    cb_rspans, cb_cspans = get_cb_parent_spans(cax)
    bboxouter = layoutgrids[gs].get_inner_bbox(rows=cb_rspans, cols=cb_cspans)

    if cax._colorbar_info['location'] in ['right', 'left']:
        size = bboxouter.width
    else:
        size = bboxouter.height

    return cax._colorbar_info['pad'] * size