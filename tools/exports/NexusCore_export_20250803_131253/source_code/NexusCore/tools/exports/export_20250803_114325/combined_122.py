
# === NexusCore/openenv\Lib\site-packages\setuptools\command\editable_wheel.py ===
"""
Create a wheel that, when installed, will make the source package 'editable'
(add it to the interpreter's path, including metadata) per PEP 660. Replaces
'setup.py develop'.

.. note::
   One of the mechanisms briefly mentioned in PEP 660 to implement editable installs is
   to create a separated directory inside ``build`` and use a .pth file to point to that
   directory. In the context of this file such directory is referred as
   *auxiliary build directory* or ``auxiliary_dir``.
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import traceback
from collections.abc import Iterable, Iterator, Mapping
from contextlib import suppress
from enum import Enum
from inspect import cleandoc
from itertools import chain, starmap
from pathlib import Path
from tempfile import TemporaryDirectory
from types import TracebackType
from typing import TYPE_CHECKING, Protocol, TypeVar, cast

from .. import Command, _normalization, _path, _shutil, errors, namespaces
from .._path import StrPath
from ..compat import py310, py312
from ..discovery import find_package_path
from ..dist import Distribution
from ..warnings import InformationOnly, SetuptoolsDeprecationWarning
from .build import build as build_cls
from .build_py import build_py as build_py_cls
from .dist_info import dist_info as dist_info_cls
from .egg_info import egg_info as egg_info_cls
from .install import install as install_cls
from .install_scripts import install_scripts as install_scripts_cls

if TYPE_CHECKING:
    from typing_extensions import Self

    from .._vendor.wheel.wheelfile import WheelFile

_P = TypeVar("_P", bound=StrPath)
_logger = logging.getLogger(__name__)


class _EditableMode(Enum):
    """
    Possible editable installation modes:
    `lenient` (new files automatically added to the package - DEFAULT);
    `strict` (requires a new installation when files are added/removed); or
    `compat` (attempts to emulate `python setup.py develop` - DEPRECATED).
    """

    STRICT = "strict"
    LENIENT = "lenient"
    COMPAT = "compat"  # TODO: Remove `compat` after Dec/2022.

    @classmethod
    def convert(cls, mode: str | None) -> _EditableMode:
        if not mode:
            return _EditableMode.LENIENT  # default

        _mode = mode.upper()
        if _mode not in _EditableMode.__members__:
            raise errors.OptionError(f"Invalid editable mode: {mode!r}. Try: 'strict'.")

        if _mode == "COMPAT":
            SetuptoolsDeprecationWarning.emit(
                "Compat editable installs",
                """
                The 'compat' editable mode is transitional and will be removed
                in future versions of `setuptools`.
                Please adapt your code accordingly to use either the 'strict' or the
                'lenient' modes.
                """,
                see_docs="userguide/development_mode.html",
                # TODO: define due_date
                # There is a series of shortcomings with the available editable install
                # methods, and they are very controversial. This is something that still
                # needs work.
                # Moreover, `pip` is still hiding this warning, so users are not aware.
            )

        return _EditableMode[_mode]


_STRICT_WARNING = """
New or renamed files may not be automatically picked up without a new installation.
"""

_LENIENT_WARNING = """
Options like `package-data`, `include/exclude-package-data` or
`packages.find.exclude/include` may have no effect.
"""


class editable_wheel(Command):
    """Build 'editable' wheel for development.
    This command is private and reserved for internal use of setuptools,
    users should rely on ``setuptools.build_meta`` APIs.
    """

    description = "DO NOT CALL DIRECTLY, INTERNAL ONLY: create PEP 660 editable wheel"

    user_options = [
        ("dist-dir=", "d", "directory to put final built distributions in"),
        ("dist-info-dir=", "I", "path to a pre-build .dist-info directory"),
        ("mode=", None, cleandoc(_EditableMode.__doc__ or "")),
    ]

    def initialize_options(self):
        self.dist_dir = None
        self.dist_info_dir = None
        self.project_dir = None
        self.mode = None

    def finalize_options(self) -> None:
        dist = self.distribution
        self.project_dir = dist.src_root or os.curdir
        self.package_dir = dist.package_dir or {}
        self.dist_dir = Path(self.dist_dir or os.path.join(self.project_dir, "dist"))

    def run(self) -> None:
        try:
            self.dist_dir.mkdir(exist_ok=True)
            self._ensure_dist_info()

            # Add missing dist_info files
            self.reinitialize_command("bdist_wheel")
            bdist_wheel = self.get_finalized_command("bdist_wheel")
            bdist_wheel.write_wheelfile(self.dist_info_dir)

            self._create_wheel_file(bdist_wheel)
        except Exception as ex:
            project = self.distribution.name or self.distribution.get_name()
            py310.add_note(
                ex,
                f"An error occurred when building editable wheel for {project}.\n"
                "See debugging tips in: "
                "https://setuptools.pypa.io/en/latest/userguide/development_mode.html#debugging-tips",
            )
            raise

    def _ensure_dist_info(self):
        if self.dist_info_dir is None:
            dist_info = cast(dist_info_cls, self.reinitialize_command("dist_info"))
            dist_info.output_dir = self.dist_dir
            dist_info.ensure_finalized()
            dist_info.run()
            self.dist_info_dir = dist_info.dist_info_dir
        else:
            assert str(self.dist_info_dir).endswith(".dist-info")
            assert Path(self.dist_info_dir, "METADATA").exists()

    def _install_namespaces(self, installation_dir, pth_prefix):
        # XXX: Only required to support the deprecated namespace practice
        dist = self.distribution
        if not dist.namespace_packages:
            return

        src_root = Path(self.project_dir, self.package_dir.get("", ".")).resolve()
        installer = _NamespaceInstaller(dist, installation_dir, pth_prefix, src_root)
        installer.install_namespaces()

    def _find_egg_info_dir(self) -> str | None:
        parent_dir = Path(self.dist_info_dir).parent if self.dist_info_dir else Path()
        candidates = map(str, parent_dir.glob("*.egg-info"))
        return next(candidates, None)

    def _configure_build(
        self, name: str, unpacked_wheel: StrPath, build_lib: StrPath, tmp_dir: StrPath
    ):
        """Configure commands to behave in the following ways:

        - Build commands can write to ``build_lib`` if they really want to...
          (but this folder is expected to be ignored and modules are expected to live
          in the project directory...)
        - Binary extensions should be built in-place (editable_mode = True)
        - Data/header/script files are not part of the "editable" specification
          so they are written directly to the unpacked_wheel directory.
        """
        # Non-editable files (data, headers, scripts) are written directly to the
        # unpacked_wheel

        dist = self.distribution
        wheel = str(unpacked_wheel)
        build_lib = str(build_lib)
        data = str(Path(unpacked_wheel, f"{name}.data", "data"))
        headers = str(Path(unpacked_wheel, f"{name}.data", "headers"))
        scripts = str(Path(unpacked_wheel, f"{name}.data", "scripts"))

        # egg-info may be generated again to create a manifest (used for package data)
        egg_info = cast(
            egg_info_cls, dist.reinitialize_command("egg_info", reinit_subcommands=True)
        )
        egg_info.egg_base = str(tmp_dir)
        egg_info.ignore_egg_info_in_manifest = True

        build = cast(
            build_cls, dist.reinitialize_command("build", reinit_subcommands=True)
        )
        install = cast(
            install_cls, dist.reinitialize_command("install", reinit_subcommands=True)
        )

        build.build_platlib = build.build_purelib = build.build_lib = build_lib
        install.install_purelib = install.install_platlib = install.install_lib = wheel
        install.install_scripts = build.build_scripts = scripts
        install.install_headers = headers
        install.install_data = data

        # For portability, ensure scripts are built with #!python shebang
        # pypa/setuptools#4863
        build_scripts = dist.get_command_obj("build_scripts")
        build_scripts.executable = 'python'

        install_scripts = cast(
            install_scripts_cls, dist.get_command_obj("install_scripts")
        )
        install_scripts.no_ep = True

        build.build_temp = str(tmp_dir)

        build_py = cast(build_py_cls, dist.get_command_obj("build_py"))
        build_py.compile = False
        build_py.existing_egg_info_dir = self._find_egg_info_dir()

        self._set_editable_mode()

        build.ensure_finalized()
        install.ensure_finalized()

    def _set_editable_mode(self):
        """Set the ``editable_mode`` flag in the build sub-commands"""
        dist = self.distribution
        build = dist.get_command_obj("build")
        for cmd_name in build.get_sub_commands():
            cmd = dist.get_command_obj(cmd_name)
            if hasattr(cmd, "editable_mode"):
                cmd.editable_mode = True
            elif hasattr(cmd, "inplace"):
                cmd.inplace = True  # backward compatibility with distutils

    def _collect_build_outputs(self) -> tuple[list[str], dict[str, str]]:
        files: list[str] = []
        mapping: dict[str, str] = {}
        build = self.get_finalized_command("build")

        for cmd_name in build.get_sub_commands():
            cmd = self.get_finalized_command(cmd_name)
            if hasattr(cmd, "get_outputs"):
                files.extend(cmd.get_outputs() or [])
            if hasattr(cmd, "get_output_mapping"):
                mapping.update(cmd.get_output_mapping() or {})

        return files, mapping

    def _run_build_commands(
        self,
        dist_name: str,
        unpacked_wheel: StrPath,
        build_lib: StrPath,
        tmp_dir: StrPath,
    ) -> tuple[list[str], dict[str, str]]:
        self._configure_build(dist_name, unpacked_wheel, build_lib, tmp_dir)
        self._run_build_subcommands()
        files, mapping = self._collect_build_outputs()
        self._run_install("headers")
        self._run_install("scripts")
        self._run_install("data")
        return files, mapping

    def _run_build_subcommands(self) -> None:
        """
        Issue #3501 indicates that some plugins/customizations might rely on:

        1. ``build_py`` not running
        2. ``build_py`` always copying files to ``build_lib``

        However both these assumptions may be false in editable_wheel.
        This method implements a temporary workaround to support the ecosystem
        while the implementations catch up.
        """
        # TODO: Once plugins/customizations had the chance to catch up, replace
        #       `self._run_build_subcommands()` with `self.run_command("build")`.
        #       Also remove _safely_run, TestCustomBuildPy. Suggested date: Aug/2023.
        build = self.get_finalized_command("build")
        for name in build.get_sub_commands():
            cmd = self.get_finalized_command(name)
            if name == "build_py" and type(cmd) is not build_py_cls:
                self._safely_run(name)
            else:
                self.run_command(name)

    def _safely_run(self, cmd_name: str):
        try:
            return self.run_command(cmd_name)
        except Exception:
            SetuptoolsDeprecationWarning.emit(
                "Customization incompatible with editable install",
                f"""
                {traceback.format_exc()}

                If you are seeing this warning it is very likely that a setuptools
                plugin or customization overrides the `{cmd_name}` command, without
                taking into consideration how editable installs run build steps
                starting from setuptools v64.0.0.

                Plugin authors and developers relying on custom build steps are
                encouraged to update their `{cmd_name}` implementation considering the
                information about editable installs in
                https://setuptools.pypa.io/en/latest/userguide/extension.html.

                For the time being `setuptools` will silence this error and ignore
                the faulty command, but this behavior will change in future versions.
                """,
                # TODO: define due_date
                # There is a series of shortcomings with the available editable install
                # methods, and they are very controversial. This is something that still
                # needs work.
            )

    def _create_wheel_file(self, bdist_wheel):
        from wheel.wheelfile import WheelFile

        dist_info = self.get_finalized_command("dist_info")
        dist_name = dist_info.name
        tag = "-".join(bdist_wheel.get_tag())
        build_tag = "0.editable"  # According to PEP 427 needs to start with digit
        archive_name = f"{dist_name}-{build_tag}-{tag}.whl"
        wheel_path = Path(self.dist_dir, archive_name)
        if wheel_path.exists():
            wheel_path.unlink()

        unpacked_wheel = TemporaryDirectory(suffix=archive_name)
        build_lib = TemporaryDirectory(suffix=".build-lib")
        build_tmp = TemporaryDirectory(suffix=".build-temp")

        with unpacked_wheel as unpacked, build_lib as lib, build_tmp as tmp:
            unpacked_dist_info = Path(unpacked, Path(self.dist_info_dir).name)
            shutil.copytree(self.dist_info_dir, unpacked_dist_info)
            self._install_namespaces(unpacked, dist_name)
            files, mapping = self._run_build_commands(dist_name, unpacked, lib, tmp)
            strategy = self._select_strategy(dist_name, tag, lib)
            with strategy, WheelFile(wheel_path, "w") as wheel_obj:
                strategy(wheel_obj, files, mapping)
                wheel_obj.write_files(unpacked)

        return wheel_path

    def _run_install(self, category: str):
        has_category = getattr(self.distribution, f"has_{category}", None)
        if has_category and has_category():
            _logger.info(f"Installing {category} as non editable")
            self.run_command(f"install_{category}")

    def _select_strategy(
        self,
        name: str,
        tag: str,
        build_lib: StrPath,
    ) -> EditableStrategy:
        """Decides which strategy to use to implement an editable installation."""
        build_name = f"__editable__.{name}-{tag}"
        project_dir = Path(self.project_dir)
        mode = _EditableMode.convert(self.mode)

        if mode is _EditableMode.STRICT:
            auxiliary_dir = _empty_dir(Path(self.project_dir, "build", build_name))
            return _LinkTree(self.distribution, name, auxiliary_dir, build_lib)

        packages = _find_packages(self.distribution)
        has_simple_layout = _simple_layout(packages, self.package_dir, project_dir)
        is_compat_mode = mode is _EditableMode.COMPAT
        if set(self.package_dir) == {""} and has_simple_layout or is_compat_mode:
            # src-layout(ish) is relatively safe for a simple pth file
            src_dir = self.package_dir.get("", ".")
            return _StaticPth(self.distribution, name, [Path(project_dir, src_dir)])

        # Use a MetaPathFinder to avoid adding accidental top-level packages/modules
        return _TopLevelFinder(self.distribution, name)


class EditableStrategy(Protocol):
    def __call__(
        self, wheel: WheelFile, files: list[str], mapping: Mapping[str, str]
    ) -> object: ...
    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> object: ...


class _StaticPth:
    def __init__(self, dist: Distribution, name: str, path_entries: list[Path]) -> None:
        self.dist = dist
        self.name = name
        self.path_entries = path_entries

    def __call__(self, wheel: WheelFile, files: list[str], mapping: Mapping[str, str]):
        entries = "\n".join(str(p.resolve()) for p in self.path_entries)
        contents = _encode_pth(f"{entries}\n")
        wheel.writestr(f"__editable__.{self.name}.pth", contents)

    def __enter__(self) -> Self:
        msg = f"""
        Editable install will be performed using .pth file to extend `sys.path` with:
        {list(map(os.fspath, self.path_entries))!r}
        """
        _logger.warning(msg + _LENIENT_WARNING)
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        pass


class _LinkTree(_StaticPth):
    """
    Creates a ``.pth`` file that points to a link tree in the ``auxiliary_dir``.

    This strategy will only link files (not dirs), so it can be implemented in
    any OS, even if that means using hardlinks instead of symlinks.

    By collocating ``auxiliary_dir`` and the original source code, limitations
    with hardlinks should be avoided.
    """

    def __init__(
        self,
        dist: Distribution,
        name: str,
        auxiliary_dir: StrPath,
        build_lib: StrPath,
    ) -> None:
        self.auxiliary_dir = Path(auxiliary_dir)
        self.build_lib = Path(build_lib).resolve()
        self._file = dist.get_command_obj("build_py").copy_file
        super().__init__(dist, name, [self.auxiliary_dir])

    def __call__(self, wheel: WheelFile, files: list[str], mapping: Mapping[str, str]):
        self._create_links(files, mapping)
        super().__call__(wheel, files, mapping)

    def _normalize_output(self, file: str) -> str | None:
        # Files relative to build_lib will be normalized to None
        with suppress(ValueError):
            path = Path(file).resolve().relative_to(self.build_lib)
            return str(path).replace(os.sep, '/')
        return None

    def _create_file(self, relative_output: str, src_file: str, link=None):
        dest = self.auxiliary_dir / relative_output
        if not dest.parent.is_dir():
            dest.parent.mkdir(parents=True)
        self._file(src_file, dest, link=link)

    def _create_links(self, outputs, output_mapping: Mapping[str, str]):
        self.auxiliary_dir.mkdir(parents=True, exist_ok=True)
        link_type = "sym" if _can_symlink_files(self.auxiliary_dir) else "hard"
        normalised = ((self._normalize_output(k), v) for k, v in output_mapping.items())
        # remove files that are not relative to build_lib
        mappings = {k: v for k, v in normalised if k is not None}

        for output in outputs:
            relative = self._normalize_output(output)
            if relative and relative not in mappings:
                self._create_file(relative, output)

        for relative, src in mappings.items():
            self._create_file(relative, src, link=link_type)

    def __enter__(self) -> Self:
        msg = "Strict editable install will be performed using a link tree.\n"
        _logger.warning(msg + _STRICT_WARNING)
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        msg = f"""\n
        Strict editable installation performed using the auxiliary directory:
            {self.auxiliary_dir}

        Please be careful to not remove this directory, otherwise you might not be able
        to import/use your package.
        """
        InformationOnly.emit("Editable installation.", msg)


class _TopLevelFinder:
    def __init__(self, dist: Distribution, name: str) -> None:
        self.dist = dist
        self.name = name

    def template_vars(self) -> tuple[str, str, dict[str, str], dict[str, list[str]]]:
        src_root = self.dist.src_root or os.curdir
        top_level = chain(_find_packages(self.dist), _find_top_level_modules(self.dist))
        package_dir = self.dist.package_dir or {}
        roots = _find_package_roots(top_level, package_dir, src_root)

        namespaces_ = dict(
            chain(
                _find_namespaces(self.dist.packages or [], roots),
                ((ns, []) for ns in _find_virtual_namespaces(roots)),
            )
        )

        legacy_namespaces = {
            pkg: find_package_path(pkg, roots, self.dist.src_root or "")
            for pkg in self.dist.namespace_packages or []
        }

        mapping = {**roots, **legacy_namespaces}
        # ^-- We need to explicitly add the legacy_namespaces to the mapping to be
        #     able to import their modules even if another package sharing the same
        #     namespace is installed in a conventional (non-editable) way.

        name = f"__editable__.{self.name}.finder"
        finder = _normalization.safe_identifier(name)
        return finder, name, mapping, namespaces_

    def get_implementation(self) -> Iterator[tuple[str, bytes]]:
        finder, name, mapping, namespaces_ = self.template_vars()

        content = bytes(_finder_template(name, mapping, namespaces_), "utf-8")
        yield (f"{finder}.py", content)

        content = _encode_pth(f"import {finder}; {finder}.install()")
        yield (f"__editable__.{self.name}.pth", content)

    def __call__(self, wheel: WheelFile, files: list[str], mapping: Mapping[str, str]):
        for file, content in self.get_implementation():
            wheel.writestr(file, content)

    def __enter__(self) -> Self:
        msg = "Editable install will be performed using a meta path finder.\n"
        _logger.warning(msg + _LENIENT_WARNING)
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        msg = """\n
        Please be careful with folders in your working directory with the same
        name as your package as they may take precedence during imports.
        """
        InformationOnly.emit("Editable installation.", msg)


def _encode_pth(content: str) -> bytes:
    """
    Prior to Python 3.13 (see https://github.com/python/cpython/issues/77102),
    .pth files are always read with 'locale' encoding, the recommendation
    from the cpython core developers is to write them as ``open(path, "w")``
    and ignore warnings (see python/cpython#77102, pypa/setuptools#3937).
    This function tries to simulate this behavior without having to create an
    actual file, in a way that supports a range of active Python versions.
    (There seems to be some variety in the way different version of Python handle
    ``encoding=None``, not all of them use ``locale.getpreferredencoding(False)``
    or ``locale.getencoding()``).
    """
    with io.BytesIO() as buffer:
        wrapper = io.TextIOWrapper(buffer, encoding=py312.PTH_ENCODING)
        # TODO: Python 3.13 replace the whole function with `bytes(content, "utf-8")`
        wrapper.write(content)
        wrapper.flush()
        buffer.seek(0)
        return buffer.read()


def _can_symlink_files(base_dir: Path) -> bool:
    with TemporaryDirectory(dir=str(base_dir.resolve())) as tmp:
        path1, path2 = Path(tmp, "file1.txt"), Path(tmp, "file2.txt")
        path1.write_text("file1", encoding="utf-8")
        with suppress(AttributeError, NotImplementedError, OSError):
            os.symlink(path1, path2)
            if path2.is_symlink() and path2.read_text(encoding="utf-8") == "file1":
                return True

        try:
            os.link(path1, path2)  # Ensure hard links can be created
        except Exception as ex:
            msg = (
                "File system does not seem to support either symlinks or hard links. "
                "Strict editable installs require one of them to be supported."
            )
            raise LinksNotSupported(msg) from ex
        return False


def _simple_layout(
    packages: Iterable[str], package_dir: dict[str, str], project_dir: StrPath
) -> bool:
    """Return ``True`` if:
    - all packages are contained by the same parent directory, **and**
    - all packages become importable if the parent directory is added to ``sys.path``.

    >>> _simple_layout(['a'], {"": "src"}, "/tmp/myproj")
    True
    >>> _simple_layout(['a', 'a.b'], {"": "src"}, "/tmp/myproj")
    True
    >>> _simple_layout(['a', 'a.b'], {}, "/tmp/myproj")
    True
    >>> _simple_layout(['a', 'a.a1', 'a.a1.a2', 'b'], {"": "src"}, "/tmp/myproj")
    True
    >>> _simple_layout(['a', 'a.a1', 'a.a1.a2', 'b'], {"a": "a", "b": "b"}, ".")
    True
    >>> _simple_layout(['a', 'a.a1', 'a.a1.a2', 'b'], {"a": "_a", "b": "_b"}, ".")
    False
    >>> _simple_layout(['a', 'a.a1', 'a.a1.a2', 'b'], {"a": "_a"}, "/tmp/myproj")
    False
    >>> _simple_layout(['a', 'a.a1', 'a.a1.a2', 'b'], {"a.a1.a2": "_a2"}, ".")
    False
    >>> _simple_layout(['a', 'a.b'], {"": "src", "a.b": "_ab"}, "/tmp/myproj")
    False
    >>> # Special cases, no packages yet:
    >>> _simple_layout([], {"": "src"}, "/tmp/myproj")
    True
    >>> _simple_layout([], {"a": "_a", "": "src"}, "/tmp/myproj")
    False
    """
    layout = {pkg: find_package_path(pkg, package_dir, project_dir) for pkg in packages}
    if not layout:
        return set(package_dir) in ({}, {""})
    parent = os.path.commonpath(starmap(_parent_path, layout.items()))
    return all(
        _path.same_path(Path(parent, *key.split('.')), value)
        for key, value in layout.items()
    )


def _parent_path(pkg, pkg_path):
    """Infer the parent path containing a package, that if added to ``sys.path`` would
    allow importing that package.
    When ``pkg`` is directly mapped into a directory with a different name, return its
    own path.
    >>> _parent_path("a", "src/a")
    'src'
    >>> _parent_path("b", "src/c")
    'src/c'
    """
    parent = pkg_path[: -len(pkg)] if pkg_path.endswith(pkg) else pkg_path
    return parent.rstrip("/" + os.sep)


def _find_packages(dist: Distribution) -> Iterator[str]:
    yield from iter(dist.packages or [])

    py_modules = dist.py_modules or []
    nested_modules = [mod for mod in py_modules if "." in mod]
    if dist.ext_package:
        yield dist.ext_package
    else:
        ext_modules = dist.ext_modules or []
        nested_modules += [x.name for x in ext_modules if "." in x.name]

    for module in nested_modules:
        package, _, _ = module.rpartition(".")
        yield package


def _find_top_level_modules(dist: Distribution) -> Iterator[str]:
    py_modules = dist.py_modules or []
    yield from (mod for mod in py_modules if "." not in mod)

    if not dist.ext_package:
        ext_modules = dist.ext_modules or []
        yield from (x.name for x in ext_modules if "." not in x.name)


def _find_package_roots(
    packages: Iterable[str],
    package_dir: Mapping[str, str],
    src_root: StrPath,
) -> dict[str, str]:
    pkg_roots: dict[str, str] = {
        pkg: _absolute_root(find_package_path(pkg, package_dir, src_root))
        for pkg in sorted(packages)
    }

    return _remove_nested(pkg_roots)


def _absolute_root(path: StrPath) -> str:
    """Works for packages and top-level modules"""
    path_ = Path(path)
    parent = path_.parent

    if path_.exists():
        return str(path_.resolve())
    else:
        return str(parent.resolve() / path_.name)


def _find_virtual_namespaces(pkg_roots: dict[str, str]) -> Iterator[str]:
    """By carefully designing ``package_dir``, it is possible to implement the logical
    structure of PEP 420 in a package without the corresponding directories.

    Moreover a parent package can be purposefully/accidentally skipped in the discovery
    phase (e.g. ``find_packages(include=["mypkg.*"])``, when ``mypkg.foo`` is included
    by ``mypkg`` itself is not).
    We consider this case to also be a virtual namespace (ignoring the original
    directory) to emulate a non-editable installation.

    This function will try to find these kinds of namespaces.
    """
    for pkg in pkg_roots:
        if "." not in pkg:
            continue
        parts = pkg.split(".")
        for i in range(len(parts) - 1, 0, -1):
            partial_name = ".".join(parts[:i])
            path = Path(find_package_path(partial_name, pkg_roots, ""))
            if not path.exists() or partial_name not in pkg_roots:
                # partial_name not in pkg_roots ==> purposefully/accidentally skipped
                yield partial_name


def _find_namespaces(
    packages: list[str], pkg_roots: dict[str, str]
) -> Iterator[tuple[str, list[str]]]:
    for pkg in packages:
        path = find_package_path(pkg, pkg_roots, "")
        if Path(path).exists() and not Path(path, "__init__.py").exists():
            yield (pkg, [path])


def _remove_nested(pkg_roots: dict[str, str]) -> dict[str, str]:
    output = dict(pkg_roots.copy())

    for pkg, path in reversed(list(pkg_roots.items())):
        if any(
            pkg != other and _is_nested(pkg, path, other, other_path)
            for other, other_path in pkg_roots.items()
        ):
            output.pop(pkg)

    return output


def _is_nested(pkg: str, pkg_path: str, parent: str, parent_path: str) -> bool:
    """
    Return ``True`` if ``pkg`` is nested inside ``parent`` both logically and in the
    file system.
    >>> _is_nested("a.b", "path/a/b", "a", "path/a")
    True
    >>> _is_nested("a.b", "path/a/b", "a", "otherpath/a")
    False
    >>> _is_nested("a.b", "path/a/b", "c", "path/c")
    False
    >>> _is_nested("a.a", "path/a/a", "a", "path/a")
    True
    >>> _is_nested("b.a", "path/b/a", "a", "path/a")
    False
    """
    norm_pkg_path = _path.normpath(pkg_path)
    rest = pkg.replace(parent, "", 1).strip(".").split(".")
    return pkg.startswith(parent) and norm_pkg_path == _path.normpath(
        Path(parent_path, *rest)
    )


def _empty_dir(dir_: _P) -> _P:
    """Create a directory ensured to be empty. Existing files may be removed."""
    _shutil.rmtree(dir_, ignore_errors=True)
    os.makedirs(dir_)
    return dir_


class _NamespaceInstaller(namespaces.Installer):
    def __init__(self, distribution, installation_dir, editable_name, src_root) -> None:
        self.distribution = distribution
        self.src_root = src_root
        self.installation_dir = installation_dir
        self.editable_name = editable_name
        self.outputs: list[str] = []
        self.dry_run = False

    def _get_nspkg_file(self):
        """Installation target."""
        return os.path.join(self.installation_dir, self.editable_name + self.nspkg_ext)

    def _get_root(self):
        """Where the modules/packages should be loaded from."""
        return repr(str(self.src_root))


_FINDER_TEMPLATE = """\
from __future__ import annotations
import sys
from importlib.machinery import ModuleSpec, PathFinder
from importlib.machinery import all_suffixes as module_suffixes
from importlib.util import spec_from_file_location
from itertools import chain
from pathlib import Path

MAPPING: dict[str, str] = {mapping!r}
NAMESPACES: dict[str, list[str]] = {namespaces!r}
PATH_PLACEHOLDER = {name!r} + ".__path_hook__"


class _EditableFinder:  # MetaPathFinder
    @classmethod
    def find_spec(cls, fullname: str, path=None, target=None) -> ModuleSpec | None:  # type: ignore
        # Top-level packages and modules (we know these exist in the FS)
        if fullname in MAPPING:
            pkg_path = MAPPING[fullname]
            return cls._find_spec(fullname, Path(pkg_path))

        # Handle immediate children modules (required for namespaces to work)
        # To avoid problems with case sensitivity in the file system we delegate
        # to the importlib.machinery implementation.
        parent, _, child = fullname.rpartition(".")
        if parent and parent in MAPPING:
            return PathFinder.find_spec(fullname, path=[MAPPING[parent]])

        # Other levels of nesting should be handled automatically by importlib
        # using the parent path.
        return None

    @classmethod
    def _find_spec(cls, fullname: str, candidate_path: Path) -> ModuleSpec | None:
        init = candidate_path / "__init__.py"
        candidates = (candidate_path.with_suffix(x) for x in module_suffixes())
        for candidate in chain([init], candidates):
            if candidate.exists():
                return spec_from_file_location(fullname, candidate)
        return None


class _EditableNamespaceFinder:  # PathEntryFinder
    @classmethod
    def _path_hook(cls, path) -> type[_EditableNamespaceFinder]:
        if path == PATH_PLACEHOLDER:
            return cls
        raise ImportError

    @classmethod
    def _paths(cls, fullname: str) -> list[str]:
        paths = NAMESPACES[fullname]
        if not paths and fullname in MAPPING:
            paths = [MAPPING[fullname]]
        # Always add placeholder, for 2 reasons:
        # 1. __path__ cannot be empty for the spec to be considered namespace.
        # 2. In the case of nested namespaces, we need to force
        #    import machinery to query _EditableNamespaceFinder again.
        return [*paths, PATH_PLACEHOLDER]

    @classmethod
    def find_spec(cls, fullname: str, target=None) -> ModuleSpec | None:  # type: ignore
        if fullname in NAMESPACES:
            spec = ModuleSpec(fullname, None, is_package=True)
            spec.submodule_search_locations = cls._paths(fullname)
            return spec
        return None

    @classmethod
    def find_module(cls, _fullname) -> None:
        return None


def install():
    if not any(finder == _EditableFinder for finder in sys.meta_path):
        sys.meta_path.append(_EditableFinder)

    if not NAMESPACES:
        return

    if not any(hook == _EditableNamespaceFinder._path_hook for hook in sys.path_hooks):
        # PathEntryFinder is needed to create NamespaceSpec without private APIS
        sys.path_hooks.append(_EditableNamespaceFinder._path_hook)
    if PATH_PLACEHOLDER not in sys.path:
        sys.path.append(PATH_PLACEHOLDER)  # Used just to trigger the path hook
"""


def _finder_template(
    name: str, mapping: Mapping[str, str], namespaces: dict[str, list[str]]
) -> str:
    """Create a string containing the code for the``MetaPathFinder`` and
    ``PathEntryFinder``.
    """
    mapping = dict(sorted(mapping.items(), key=lambda p: p[0]))
    return _FINDER_TEMPLATE.format(name=name, mapping=mapping, namespaces=namespaces)


class LinksNotSupported(errors.FileError):
    """File system does not seem to support either symlinks or hard links."""

# === NexusCore/openenv\Lib\site-packages\PIL\JpegImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# JPEG (JFIF) file handling
#
# See "Digital Compression and Coding of Continuous-Tone Still Images,
# Part 1, Requirements and Guidelines" (CCITT T.81 / ISO 10918-1)
#
# History:
# 1995-09-09 fl   Created
# 1995-09-13 fl   Added full parser
# 1996-03-25 fl   Added hack to use the IJG command line utilities
# 1996-05-05 fl   Workaround Photoshop 2.5 CMYK polarity bug
# 1996-05-28 fl   Added draft support, JFIF version (0.1)
# 1996-12-30 fl   Added encoder options, added progression property (0.2)
# 1997-08-27 fl   Save mode 1 images as BW (0.3)
# 1998-07-12 fl   Added YCbCr to draft and save methods (0.4)
# 1998-10-19 fl   Don't hang on files using 16-bit DQT's (0.4.1)
# 2001-04-16 fl   Extract DPI settings from JFIF files (0.4.2)
# 2002-07-01 fl   Skip pad bytes before markers; identify Exif files (0.4.3)
# 2003-04-25 fl   Added experimental EXIF decoder (0.5)
# 2003-06-06 fl   Added experimental EXIF GPSinfo decoder
# 2003-09-13 fl   Extract COM markers
# 2009-09-06 fl   Added icc_profile support (from Florian Hoech)
# 2009-03-06 fl   Changed CMYK handling; always use Adobe polarity (0.6)
# 2009-03-08 fl   Added subsampling support (from Justin Huff).
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1995-1996 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import array
import io
import math
import os
import struct
import subprocess
import sys
import tempfile
import warnings
from typing import IO, Any

from . import Image, ImageFile
from ._binary import i16be as i16
from ._binary import i32be as i32
from ._binary import o8
from ._binary import o16be as o16
from ._deprecate import deprecate
from .JpegPresets import presets

TYPE_CHECKING = False
if TYPE_CHECKING:
    from .MpoImagePlugin import MpoImageFile

#
# Parser


def Skip(self: JpegImageFile, marker: int) -> None:
    n = i16(self.fp.read(2)) - 2
    ImageFile._safe_read(self.fp, n)


def APP(self: JpegImageFile, marker: int) -> None:
    #
    # Application marker.  Store these in the APP dictionary.
    # Also look for well-known application markers.

    n = i16(self.fp.read(2)) - 2
    s = ImageFile._safe_read(self.fp, n)

    app = f"APP{marker & 15}"

    self.app[app] = s  # compatibility
    self.applist.append((app, s))

    if marker == 0xFFE0 and s.startswith(b"JFIF"):
        # extract JFIF information
        self.info["jfif"] = version = i16(s, 5)  # version
        self.info["jfif_version"] = divmod(version, 256)
        # extract JFIF properties
        try:
            jfif_unit = s[7]
            jfif_density = i16(s, 8), i16(s, 10)
        except Exception:
            pass
        else:
            if jfif_unit == 1:
                self.info["dpi"] = jfif_density
            elif jfif_unit == 2:  # cm
                # 1 dpcm = 2.54 dpi
                self.info["dpi"] = tuple(d * 2.54 for d in jfif_density)
            self.info["jfif_unit"] = jfif_unit
            self.info["jfif_density"] = jfif_density
    elif marker == 0xFFE1 and s.startswith(b"Exif\0\0"):
        # extract EXIF information
        if "exif" in self.info:
            self.info["exif"] += s[6:]
        else:
            self.info["exif"] = s
            self._exif_offset = self.fp.tell() - n + 6
    elif marker == 0xFFE1 and s.startswith(b"http://ns.adobe.com/xap/1.0/\x00"):
        self.info["xmp"] = s.split(b"\x00", 1)[1]
    elif marker == 0xFFE2 and s.startswith(b"FPXR\0"):
        # extract FlashPix information (incomplete)
        self.info["flashpix"] = s  # FIXME: value will change
    elif marker == 0xFFE2 and s.startswith(b"ICC_PROFILE\0"):
        # Since an ICC profile can be larger than the maximum size of
        # a JPEG marker (64K), we need provisions to split it into
        # multiple markers. The format defined by the ICC specifies
        # one or more APP2 markers containing the following data:
        #   Identifying string      ASCII "ICC_PROFILE\0"  (12 bytes)
        #   Marker sequence number  1, 2, etc (1 byte)
        #   Number of markers       Total of APP2's used (1 byte)
        #   Profile data            (remainder of APP2 data)
        # Decoders should use the marker sequence numbers to
        # reassemble the profile, rather than assuming that the APP2
        # markers appear in the correct sequence.
        self.icclist.append(s)
    elif marker == 0xFFED and s.startswith(b"Photoshop 3.0\x00"):
        # parse the image resource block
        offset = 14
        photoshop = self.info.setdefault("photoshop", {})
        while s[offset : offset + 4] == b"8BIM":
            try:
                offset += 4
                # resource code
                code = i16(s, offset)
                offset += 2
                # resource name (usually empty)
                name_len = s[offset]
                # name = s[offset+1:offset+1+name_len]
                offset += 1 + name_len
                offset += offset & 1  # align
                # resource data block
                size = i32(s, offset)
                offset += 4
                data = s[offset : offset + size]
                if code == 0x03ED:  # ResolutionInfo
                    photoshop[code] = {
                        "XResolution": i32(data, 0) / 65536,
                        "DisplayedUnitsX": i16(data, 4),
                        "YResolution": i32(data, 8) / 65536,
                        "DisplayedUnitsY": i16(data, 12),
                    }
                else:
                    photoshop[code] = data
                offset += size
                offset += offset & 1  # align
            except struct.error:
                break  # insufficient data

    elif marker == 0xFFEE and s.startswith(b"Adobe"):
        self.info["adobe"] = i16(s, 5)
        # extract Adobe custom properties
        try:
            adobe_transform = s[11]
        except IndexError:
            pass
        else:
            self.info["adobe_transform"] = adobe_transform
    elif marker == 0xFFE2 and s.startswith(b"MPF\0"):
        # extract MPO information
        self.info["mp"] = s[4:]
        # offset is current location minus buffer size
        # plus constant header size
        self.info["mpoffset"] = self.fp.tell() - n + 4


def COM(self: JpegImageFile, marker: int) -> None:
    #
    # Comment marker.  Store these in the APP dictionary.
    n = i16(self.fp.read(2)) - 2
    s = ImageFile._safe_read(self.fp, n)

    self.info["comment"] = s
    self.app["COM"] = s  # compatibility
    self.applist.append(("COM", s))


def SOF(self: JpegImageFile, marker: int) -> None:
    #
    # Start of frame marker.  Defines the size and mode of the
    # image.  JPEG is colour blind, so we use some simple
    # heuristics to map the number of layers to an appropriate
    # mode.  Note that this could be made a bit brighter, by
    # looking for JFIF and Adobe APP markers.

    n = i16(self.fp.read(2)) - 2
    s = ImageFile._safe_read(self.fp, n)
    self._size = i16(s, 3), i16(s, 1)

    self.bits = s[0]
    if self.bits != 8:
        msg = f"cannot handle {self.bits}-bit layers"
        raise SyntaxError(msg)

    self.layers = s[5]
    if self.layers == 1:
        self._mode = "L"
    elif self.layers == 3:
        self._mode = "RGB"
    elif self.layers == 4:
        self._mode = "CMYK"
    else:
        msg = f"cannot handle {self.layers}-layer images"
        raise SyntaxError(msg)

    if marker in [0xFFC2, 0xFFC6, 0xFFCA, 0xFFCE]:
        self.info["progressive"] = self.info["progression"] = 1

    if self.icclist:
        # fixup icc profile
        self.icclist.sort()  # sort by sequence number
        if self.icclist[0][13] == len(self.icclist):
            profile = [p[14:] for p in self.icclist]
            icc_profile = b"".join(profile)
        else:
            icc_profile = None  # wrong number of fragments
        self.info["icc_profile"] = icc_profile
        self.icclist = []

    for i in range(6, len(s), 3):
        t = s[i : i + 3]
        # 4-tuples: id, vsamp, hsamp, qtable
        self.layer.append((t[0], t[1] // 16, t[1] & 15, t[2]))


def DQT(self: JpegImageFile, marker: int) -> None:
    #
    # Define quantization table.  Note that there might be more
    # than one table in each marker.

    # FIXME: The quantization tables can be used to estimate the
    # compression quality.

    n = i16(self.fp.read(2)) - 2
    s = ImageFile._safe_read(self.fp, n)
    while len(s):
        v = s[0]
        precision = 1 if (v // 16 == 0) else 2  # in bytes
        qt_length = 1 + precision * 64
        if len(s) < qt_length:
            msg = "bad quantization table marker"
            raise SyntaxError(msg)
        data = array.array("B" if precision == 1 else "H", s[1:qt_length])
        if sys.byteorder == "little" and precision > 1:
            data.byteswap()  # the values are always big-endian
        self.quantization[v & 15] = [data[i] for i in zigzag_index]
        s = s[qt_length:]


#
# JPEG marker table

MARKER = {
    0xFFC0: ("SOF0", "Baseline DCT", SOF),
    0xFFC1: ("SOF1", "Extended Sequential DCT", SOF),
    0xFFC2: ("SOF2", "Progressive DCT", SOF),
    0xFFC3: ("SOF3", "Spatial lossless", SOF),
    0xFFC4: ("DHT", "Define Huffman table", Skip),
    0xFFC5: ("SOF5", "Differential sequential DCT", SOF),
    0xFFC6: ("SOF6", "Differential progressive DCT", SOF),
    0xFFC7: ("SOF7", "Differential spatial", SOF),
    0xFFC8: ("JPG", "Extension", None),
    0xFFC9: ("SOF9", "Extended sequential DCT (AC)", SOF),
    0xFFCA: ("SOF10", "Progressive DCT (AC)", SOF),
    0xFFCB: ("SOF11", "Spatial lossless DCT (AC)", SOF),
    0xFFCC: ("DAC", "Define arithmetic coding conditioning", Skip),
    0xFFCD: ("SOF13", "Differential sequential DCT (AC)", SOF),
    0xFFCE: ("SOF14", "Differential progressive DCT (AC)", SOF),
    0xFFCF: ("SOF15", "Differential spatial (AC)", SOF),
    0xFFD0: ("RST0", "Restart 0", None),
    0xFFD1: ("RST1", "Restart 1", None),
    0xFFD2: ("RST2", "Restart 2", None),
    0xFFD3: ("RST3", "Restart 3", None),
    0xFFD4: ("RST4", "Restart 4", None),
    0xFFD5: ("RST5", "Restart 5", None),
    0xFFD6: ("RST6", "Restart 6", None),
    0xFFD7: ("RST7", "Restart 7", None),
    0xFFD8: ("SOI", "Start of image", None),
    0xFFD9: ("EOI", "End of image", None),
    0xFFDA: ("SOS", "Start of scan", Skip),
    0xFFDB: ("DQT", "Define quantization table", DQT),
    0xFFDC: ("DNL", "Define number of lines", Skip),
    0xFFDD: ("DRI", "Define restart interval", Skip),
    0xFFDE: ("DHP", "Define hierarchical progression", SOF),
    0xFFDF: ("EXP", "Expand reference component", Skip),
    0xFFE0: ("APP0", "Application segment 0", APP),
    0xFFE1: ("APP1", "Application segment 1", APP),
    0xFFE2: ("APP2", "Application segment 2", APP),
    0xFFE3: ("APP3", "Application segment 3", APP),
    0xFFE4: ("APP4", "Application segment 4", APP),
    0xFFE5: ("APP5", "Application segment 5", APP),
    0xFFE6: ("APP6", "Application segment 6", APP),
    0xFFE7: ("APP7", "Application segment 7", APP),
    0xFFE8: ("APP8", "Application segment 8", APP),
    0xFFE9: ("APP9", "Application segment 9", APP),
    0xFFEA: ("APP10", "Application segment 10", APP),
    0xFFEB: ("APP11", "Application segment 11", APP),
    0xFFEC: ("APP12", "Application segment 12", APP),
    0xFFED: ("APP13", "Application segment 13", APP),
    0xFFEE: ("APP14", "Application segment 14", APP),
    0xFFEF: ("APP15", "Application segment 15", APP),
    0xFFF0: ("JPG0", "Extension 0", None),
    0xFFF1: ("JPG1", "Extension 1", None),
    0xFFF2: ("JPG2", "Extension 2", None),
    0xFFF3: ("JPG3", "Extension 3", None),
    0xFFF4: ("JPG4", "Extension 4", None),
    0xFFF5: ("JPG5", "Extension 5", None),
    0xFFF6: ("JPG6", "Extension 6", None),
    0xFFF7: ("JPG7", "Extension 7", None),
    0xFFF8: ("JPG8", "Extension 8", None),
    0xFFF9: ("JPG9", "Extension 9", None),
    0xFFFA: ("JPG10", "Extension 10", None),
    0xFFFB: ("JPG11", "Extension 11", None),
    0xFFFC: ("JPG12", "Extension 12", None),
    0xFFFD: ("JPG13", "Extension 13", None),
    0xFFFE: ("COM", "Comment", COM),
}


def _accept(prefix: bytes) -> bool:
    # Magic number was taken from https://en.wikipedia.org/wiki/JPEG
    return prefix.startswith(b"\xff\xd8\xff")


##
# Image plugin for JPEG and JFIF images.


class JpegImageFile(ImageFile.ImageFile):
    format = "JPEG"
    format_description = "JPEG (ISO 10918)"

    def _open(self) -> None:
        s = self.fp.read(3)

        if not _accept(s):
            msg = "not a JPEG file"
            raise SyntaxError(msg)
        s = b"\xff"

        # Create attributes
        self.bits = self.layers = 0
        self._exif_offset = 0

        # JPEG specifics (internal)
        self.layer: list[tuple[int, int, int, int]] = []
        self._huffman_dc: dict[Any, Any] = {}
        self._huffman_ac: dict[Any, Any] = {}
        self.quantization: dict[int, list[int]] = {}
        self.app: dict[str, bytes] = {}  # compatibility
        self.applist: list[tuple[str, bytes]] = []
        self.icclist: list[bytes] = []

        while True:
            i = s[0]
            if i == 0xFF:
                s = s + self.fp.read(1)
                i = i16(s)
            else:
                # Skip non-0xFF junk
                s = self.fp.read(1)
                continue

            if i in MARKER:
                name, description, handler = MARKER[i]
                if handler is not None:
                    handler(self, i)
                if i == 0xFFDA:  # start of scan
                    rawmode = self.mode
                    if self.mode == "CMYK":
                        rawmode = "CMYK;I"  # assume adobe conventions
                    self.tile = [
                        ImageFile._Tile("jpeg", (0, 0) + self.size, 0, (rawmode, ""))
                    ]
                    # self.__offset = self.fp.tell()
                    break
                s = self.fp.read(1)
            elif i in {0, 0xFFFF}:
                # padded marker or junk; move on
                s = b"\xff"
            elif i == 0xFF00:  # Skip extraneous data (escaped 0xFF)
                s = self.fp.read(1)
            else:
                msg = "no marker found"
                raise SyntaxError(msg)

        self._read_dpi_from_exif()

    def __getattr__(self, name: str) -> Any:
        if name in ("huffman_ac", "huffman_dc"):
            deprecate(name, 12)
            return getattr(self, "_" + name)
        raise AttributeError(name)

    def __getstate__(self) -> list[Any]:
        return super().__getstate__() + [self.layers, self.layer]

    def __setstate__(self, state: list[Any]) -> None:
        self.layers, self.layer = state[6:]
        super().__setstate__(state)

    def load_read(self, read_bytes: int) -> bytes:
        """
        internal: read more image data
        For premature EOF and LOAD_TRUNCATED_IMAGES adds EOI marker
        so libjpeg can finish decoding
        """
        s = self.fp.read(read_bytes)

        if not s and ImageFile.LOAD_TRUNCATED_IMAGES and not hasattr(self, "_ended"):
            # Premature EOF.
            # Pretend file is finished adding EOI marker
            self._ended = True
            return b"\xff\xd9"

        return s

    def draft(
        self, mode: str | None, size: tuple[int, int] | None
    ) -> tuple[str, tuple[int, int, float, float]] | None:
        if len(self.tile) != 1:
            return None

        # Protect from second call
        if self.decoderconfig:
            return None

        d, e, o, a = self.tile[0]
        scale = 1
        original_size = self.size

        assert isinstance(a, tuple)
        if a[0] == "RGB" and mode in ["L", "YCbCr"]:
            self._mode = mode
            a = mode, ""

        if size:
            scale = min(self.size[0] // size[0], self.size[1] // size[1])
            for s in [8, 4, 2, 1]:
                if scale >= s:
                    break
            assert e is not None
            e = (
                e[0],
                e[1],
                (e[2] - e[0] + s - 1) // s + e[0],
                (e[3] - e[1] + s - 1) // s + e[1],
            )
            self._size = ((self.size[0] + s - 1) // s, (self.size[1] + s - 1) // s)
            scale = s

        self.tile = [ImageFile._Tile(d, e, o, a)]
        self.decoderconfig = (scale, 0)

        box = (0, 0, original_size[0] / scale, original_size[1] / scale)
        return self.mode, box

    def load_djpeg(self) -> None:
        # ALTERNATIVE: handle JPEGs via the IJG command line utilities

        f, path = tempfile.mkstemp()
        os.close(f)
        if os.path.exists(self.filename):
            subprocess.check_call(["djpeg", "-outfile", path, self.filename])
        else:
            try:
                os.unlink(path)
            except OSError:
                pass

            msg = "Invalid Filename"
            raise ValueError(msg)

        try:
            with Image.open(path) as _im:
                _im.load()
                self.im = _im.im
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

        self._mode = self.im.mode
        self._size = self.im.size

        self.tile = []

    def _getexif(self) -> dict[int, Any] | None:
        return _getexif(self)

    def _read_dpi_from_exif(self) -> None:
        # If DPI isn't in JPEG header, fetch from EXIF
        if "dpi" in self.info or "exif" not in self.info:
            return
        try:
            exif = self.getexif()
            resolution_unit = exif[0x0128]
            x_resolution = exif[0x011A]
            try:
                dpi = float(x_resolution[0]) / x_resolution[1]
            except TypeError:
                dpi = x_resolution
            if math.isnan(dpi):
                msg = "DPI is not a number"
                raise ValueError(msg)
            if resolution_unit == 3:  # cm
                # 1 dpcm = 2.54 dpi
                dpi *= 2.54
            self.info["dpi"] = dpi, dpi
        except (
            struct.error,  # truncated EXIF
            KeyError,  # dpi not included
            SyntaxError,  # invalid/unreadable EXIF
            TypeError,  # dpi is an invalid float
            ValueError,  # dpi is an invalid float
            ZeroDivisionError,  # invalid dpi rational value
        ):
            self.info["dpi"] = 72, 72

    def _getmp(self) -> dict[int, Any] | None:
        return _getmp(self)


def _getexif(self: JpegImageFile) -> dict[int, Any] | None:
    if "exif" not in self.info:
        return None
    return self.getexif()._get_merged_dict()


def _getmp(self: JpegImageFile) -> dict[int, Any] | None:
    # Extract MP information.  This method was inspired by the "highly
    # experimental" _getexif version that's been in use for years now,
    # itself based on the ImageFileDirectory class in the TIFF plugin.

    # The MP record essentially consists of a TIFF file embedded in a JPEG
    # application marker.
    try:
        data = self.info["mp"]
    except KeyError:
        return None
    file_contents = io.BytesIO(data)
    head = file_contents.read(8)
    endianness = ">" if head.startswith(b"\x4d\x4d\x00\x2a") else "<"
    # process dictionary
    from . import TiffImagePlugin

    try:
        info = TiffImagePlugin.ImageFileDirectory_v2(head)
        file_contents.seek(info.next)
        info.load(file_contents)
        mp = dict(info)
    except Exception as e:
        msg = "malformed MP Index (unreadable directory)"
        raise SyntaxError(msg) from e
    # it's an error not to have a number of images
    try:
        quant = mp[0xB001]
    except KeyError as e:
        msg = "malformed MP Index (no number of images)"
        raise SyntaxError(msg) from e
    # get MP entries
    mpentries = []
    try:
        rawmpentries = mp[0xB002]
        for entrynum in range(quant):
            unpackedentry = struct.unpack_from(
                f"{endianness}LLLHH", rawmpentries, entrynum * 16
            )
            labels = ("Attribute", "Size", "DataOffset", "EntryNo1", "EntryNo2")
            mpentry = dict(zip(labels, unpackedentry))
            mpentryattr = {
                "DependentParentImageFlag": bool(mpentry["Attribute"] & (1 << 31)),
                "DependentChildImageFlag": bool(mpentry["Attribute"] & (1 << 30)),
                "RepresentativeImageFlag": bool(mpentry["Attribute"] & (1 << 29)),
                "Reserved": (mpentry["Attribute"] & (3 << 27)) >> 27,
                "ImageDataFormat": (mpentry["Attribute"] & (7 << 24)) >> 24,
                "MPType": mpentry["Attribute"] & 0x00FFFFFF,
            }
            if mpentryattr["ImageDataFormat"] == 0:
                mpentryattr["ImageDataFormat"] = "JPEG"
            else:
                msg = "unsupported picture format in MPO"
                raise SyntaxError(msg)
            mptypemap = {
                0x000000: "Undefined",
                0x010001: "Large Thumbnail (VGA Equivalent)",
                0x010002: "Large Thumbnail (Full HD Equivalent)",
                0x020001: "Multi-Frame Image (Panorama)",
                0x020002: "Multi-Frame Image: (Disparity)",
                0x020003: "Multi-Frame Image: (Multi-Angle)",
                0x030000: "Baseline MP Primary Image",
            }
            mpentryattr["MPType"] = mptypemap.get(mpentryattr["MPType"], "Unknown")
            mpentry["Attribute"] = mpentryattr
            mpentries.append(mpentry)
        mp[0xB002] = mpentries
    except KeyError as e:
        msg = "malformed MP Index (bad MP Entry)"
        raise SyntaxError(msg) from e
    # Next we should try and parse the individual image unique ID list;
    # we don't because I've never seen this actually used in a real MPO
    # file and so can't test it.
    return mp


# --------------------------------------------------------------------
# stuff to save JPEG files

RAWMODE = {
    "1": "L",
    "L": "L",
    "RGB": "RGB",
    "RGBX": "RGB",
    "CMYK": "CMYK;I",  # assume adobe conventions
    "YCbCr": "YCbCr",
}

# fmt: off
zigzag_index = (
    0,  1,  5,  6, 14, 15, 27, 28,
    2,  4,  7, 13, 16, 26, 29, 42,
    3,  8, 12, 17, 25, 30, 41, 43,
    9, 11, 18, 24, 31, 40, 44, 53,
    10, 19, 23, 32, 39, 45, 52, 54,
    20, 22, 33, 38, 46, 51, 55, 60,
    21, 34, 37, 47, 50, 56, 59, 61,
    35, 36, 48, 49, 57, 58, 62, 63,
)

samplings = {
    (1, 1, 1, 1, 1, 1): 0,
    (2, 1, 1, 1, 1, 1): 1,
    (2, 2, 1, 1, 1, 1): 2,
}
# fmt: on


def get_sampling(im: Image.Image) -> int:
    # There's no subsampling when images have only 1 layer
    # (grayscale images) or when they are CMYK (4 layers),
    # so set subsampling to the default value.
    #
    # NOTE: currently Pillow can't encode JPEG to YCCK format.
    # If YCCK support is added in the future, subsampling code will have
    # to be updated (here and in JpegEncode.c) to deal with 4 layers.
    if not isinstance(im, JpegImageFile) or im.layers in (1, 4):
        return -1
    sampling = im.layer[0][1:3] + im.layer[1][1:3] + im.layer[2][1:3]
    return samplings.get(sampling, -1)


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    if im.width == 0 or im.height == 0:
        msg = "cannot write empty image as JPEG"
        raise ValueError(msg)

    try:
        rawmode = RAWMODE[im.mode]
    except KeyError as e:
        msg = f"cannot write mode {im.mode} as JPEG"
        raise OSError(msg) from e

    info = im.encoderinfo

    dpi = [round(x) for x in info.get("dpi", (0, 0))]

    quality = info.get("quality", -1)
    subsampling = info.get("subsampling", -1)
    qtables = info.get("qtables")

    if quality == "keep":
        quality = -1
        subsampling = "keep"
        qtables = "keep"
    elif quality in presets:
        preset = presets[quality]
        quality = -1
        subsampling = preset.get("subsampling", -1)
        qtables = preset.get("quantization")
    elif not isinstance(quality, int):
        msg = "Invalid quality setting"
        raise ValueError(msg)
    else:
        if subsampling in presets:
            subsampling = presets[subsampling].get("subsampling", -1)
        if isinstance(qtables, str) and qtables in presets:
            qtables = presets[qtables].get("quantization")

    if subsampling == "4:4:4":
        subsampling = 0
    elif subsampling == "4:2:2":
        subsampling = 1
    elif subsampling == "4:2:0":
        subsampling = 2
    elif subsampling == "4:1:1":
        # For compatibility. Before Pillow 4.3, 4:1:1 actually meant 4:2:0.
        # Set 4:2:0 if someone is still using that value.
        subsampling = 2
    elif subsampling == "keep":
        if im.format != "JPEG":
            msg = "Cannot use 'keep' when original image is not a JPEG"
            raise ValueError(msg)
        subsampling = get_sampling(im)

    def validate_qtables(
        qtables: (
            str | tuple[list[int], ...] | list[list[int]] | dict[int, list[int]] | None
        ),
    ) -> list[list[int]] | None:
        if qtables is None:
            return qtables
        if isinstance(qtables, str):
            try:
                lines = [
                    int(num)
                    for line in qtables.splitlines()
                    for num in line.split("#", 1)[0].split()
                ]
            except ValueError as e:
                msg = "Invalid quantization table"
                raise ValueError(msg) from e
            else:
                qtables = [lines[s : s + 64] for s in range(0, len(lines), 64)]
        if isinstance(qtables, (tuple, list, dict)):
            if isinstance(qtables, dict):
                qtables = [
                    qtables[key] for key in range(len(qtables)) if key in qtables
                ]
            elif isinstance(qtables, tuple):
                qtables = list(qtables)
            if not (0 < len(qtables) < 5):
                msg = "None or too many quantization tables"
                raise ValueError(msg)
            for idx, table in enumerate(qtables):
                try:
                    if len(table) != 64:
                        msg = "Invalid quantization table"
                        raise TypeError(msg)
                    table_array = array.array("H", table)
                except TypeError as e:
                    msg = "Invalid quantization table"
                    raise ValueError(msg) from e
                else:
                    qtables[idx] = list(table_array)
            return qtables

    if qtables == "keep":
        if im.format != "JPEG":
            msg = "Cannot use 'keep' when original image is not a JPEG"
            raise ValueError(msg)
        qtables = getattr(im, "quantization", None)
    qtables = validate_qtables(qtables)

    extra = info.get("extra", b"")

    MAX_BYTES_IN_MARKER = 65533
    xmp = info.get("xmp")
    if xmp:
        overhead_len = 29  # b"http://ns.adobe.com/xap/1.0/\x00"
        max_data_bytes_in_marker = MAX_BYTES_IN_MARKER - overhead_len
        if len(xmp) > max_data_bytes_in_marker:
            msg = "XMP data is too long"
            raise ValueError(msg)
        size = o16(2 + overhead_len + len(xmp))
        extra += b"\xff\xe1" + size + b"http://ns.adobe.com/xap/1.0/\x00" + xmp

    icc_profile = info.get("icc_profile")
    if icc_profile:
        overhead_len = 14  # b"ICC_PROFILE\0" + o8(i) + o8(len(markers))
        max_data_bytes_in_marker = MAX_BYTES_IN_MARKER - overhead_len
        markers = []
        while icc_profile:
            markers.append(icc_profile[:max_data_bytes_in_marker])
            icc_profile = icc_profile[max_data_bytes_in_marker:]
        i = 1
        for marker in markers:
            size = o16(2 + overhead_len + len(marker))
            extra += (
                b"\xff\xe2"
                + size
                + b"ICC_PROFILE\0"
                + o8(i)
                + o8(len(markers))
                + marker
            )
            i += 1

    comment = info.get("comment", im.info.get("comment"))

    # "progressive" is the official name, but older documentation
    # says "progression"
    # FIXME: issue a warning if the wrong form is used (post-1.1.7)
    progressive = info.get("progressive", False) or info.get("progression", False)

    optimize = info.get("optimize", False)

    exif = info.get("exif", b"")
    if isinstance(exif, Image.Exif):
        exif = exif.tobytes()
    if len(exif) > MAX_BYTES_IN_MARKER:
        msg = "EXIF data is too long"
        raise ValueError(msg)

    # get keyword arguments
    im.encoderconfig = (
        quality,
        progressive,
        info.get("smooth", 0),
        optimize,
        info.get("keep_rgb", False),
        info.get("streamtype", 0),
        dpi,
        subsampling,
        info.get("restart_marker_blocks", 0),
        info.get("restart_marker_rows", 0),
        qtables,
        comment,
        extra,
        exif,
    )

    # if we optimize, libjpeg needs a buffer big enough to hold the whole image
    # in a shot. Guessing on the size, at im.size bytes. (raw pixel size is
    # channels*size, this is a value that's been used in a django patch.
    # https://github.com/matthewwithanm/django-imagekit/issues/50
    bufsize = 0
    if optimize or progressive:
        # CMYK can be bigger
        if im.mode == "CMYK":
            bufsize = 4 * im.size[0] * im.size[1]
        # keep sets quality to -1, but the actual value may be high.
        elif quality >= 95 or quality == -1:
            bufsize = 2 * im.size[0] * im.size[1]
        else:
            bufsize = im.size[0] * im.size[1]
        if exif:
            bufsize += len(exif) + 5
        if extra:
            bufsize += len(extra) + 1
    else:
        # The EXIF info needs to be written as one block, + APP1, + one spare byte.
        # Ensure that our buffer is big enough. Same with the icc_profile block.
        bufsize = max(bufsize, len(exif) + 5, len(extra) + 1)

    ImageFile._save(
        im, fp, [ImageFile._Tile("jpeg", (0, 0) + im.size, 0, rawmode)], bufsize
    )


def _save_cjpeg(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    # ALTERNATIVE: handle JPEGs via the IJG command line utilities.
    tempfile = im._dump()
    subprocess.check_call(["cjpeg", "-outfile", filename, tempfile])
    try:
        os.unlink(tempfile)
    except OSError:
        pass


##
# Factory for making JPEG and MPO instances
def jpeg_factory(
    fp: IO[bytes], filename: str | bytes | None = None
) -> JpegImageFile | MpoImageFile:
    im = JpegImageFile(fp, filename)
    try:
        mpheader = im._getmp()
        if mpheader is not None and mpheader[45057] > 1:
            for segment, content in im.applist:
                if segment == "APP1" and b' hdrgm:Version="' in content:
                    # Ultra HDR images are not yet supported
                    return im
            # It's actually an MPO
            from .MpoImagePlugin import MpoImageFile

            # Don't reload everything, just convert it.
            im = MpoImageFile.adopt(im, mpheader)
    except (TypeError, IndexError):
        # It is really a JPEG
        pass
    except SyntaxError:
        warnings.warn(
            "Image appears to be a malformed MPO file, it will be "
            "interpreted as a base JPEG file"
        )
    return im


# ---------------------------------------------------------------------
# Registry stuff

Image.register_open(JpegImageFile.format, jpeg_factory, _accept)
Image.register_save(JpegImageFile.format, _save)

Image.register_extensions(JpegImageFile.format, [".jfif", ".jpe", ".jpg", ".jpeg"])

Image.register_mime(JpegImageFile.format, "image/jpeg")

# === NexusCore/openenv\Lib\site-packages\litellm\files\main.py ===
"""
Main File for Files API implementation

https://platform.openai.com/docs/api-reference/files

"""

import asyncio
import contextvars
import os
from functools import partial
from typing import Any, Coroutine, Dict, Literal, Optional, Union, cast

import httpx

import litellm
from litellm import get_secret_str
from litellm.litellm_core_utils.get_llm_provider_logic import get_llm_provider
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.azure.files.handler import AzureOpenAIFilesAPI
from litellm.llms.custom_httpx.llm_http_handler import BaseLLMHTTPHandler
from litellm.llms.openai.openai import FileDeleted, FileObject, OpenAIFilesAPI
from litellm.llms.vertex_ai.files.handler import VertexAIFilesHandler
from litellm.types.llms.openai import (
    CreateFileRequest,
    FileContentRequest,
    FileTypes,
    HttpxBinaryResponseContent,
    OpenAIFileObject,
)
from litellm.types.router import *
from litellm.types.utils import LlmProviders
from litellm.utils import (
    ProviderConfigManager,
    client,
    get_litellm_params,
    supports_httpx_timeout,
)

base_llm_http_handler = BaseLLMHTTPHandler()

####### ENVIRONMENT VARIABLES ###################
openai_files_instance = OpenAIFilesAPI()
azure_files_instance = AzureOpenAIFilesAPI()
vertex_ai_files_instance = VertexAIFilesHandler()
#################################################


@client
async def acreate_file(
    file: FileTypes,
    purpose: Literal["assistants", "batch", "fine-tune"],
    custom_llm_provider: Literal["openai", "azure", "vertex_ai"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> OpenAIFileObject:
    """
    Async: Files are used to upload documents that can be used with features like Assistants, Fine-tuning, and Batch API.

    LiteLLM Equivalent of POST: POST https://api.openai.com/v1/files
    """
    try:
        loop = asyncio.get_event_loop()
        kwargs["acreate_file"] = True

        call_args = {
            "file": file,
            "purpose": purpose,
            "custom_llm_provider": custom_llm_provider,
            "extra_headers": extra_headers,
            "extra_body": extra_body,
            **kwargs,
        }

        # Use a partial function to pass your keyword arguments
        func = partial(create_file, **call_args)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response  # type: ignore

        return response
    except Exception as e:
        raise e


@client
def create_file(
    file: FileTypes,
    purpose: Literal["assistants", "batch", "fine-tune"],
    custom_llm_provider: Optional[Literal["openai", "azure", "vertex_ai"]] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> Union[OpenAIFileObject, Coroutine[Any, Any, OpenAIFileObject]]:
    """
    Files are used to upload documents that can be used with features like Assistants, Fine-tuning, and Batch API.

    LiteLLM Equivalent of POST: POST https://api.openai.com/v1/files

    Specify either provider_list or custom_llm_provider.
    """
    try:
        _is_async = kwargs.pop("acreate_file", False) is True
        optional_params = GenericLiteLLMParams(**kwargs)
        litellm_params_dict = get_litellm_params(**kwargs)
        logging_obj = cast(
            Optional[LiteLLMLoggingObj], kwargs.get("litellm_logging_obj")
        )
        if logging_obj is None:
            raise ValueError("logging_obj is required")
        client = kwargs.get("client")

        ### TIMEOUT LOGIC ###
        timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
        # set timeout for 10 minutes by default

        if (
            timeout is not None
            and isinstance(timeout, httpx.Timeout)
            and supports_httpx_timeout(cast(str, custom_llm_provider)) is False
        ):
            read_timeout = timeout.read or 600
            timeout = read_timeout  # default 10 min timeout
        elif timeout is not None and not isinstance(timeout, httpx.Timeout):
            timeout = float(timeout)  # type: ignore
        elif timeout is None:
            timeout = 600.0

        _create_file_request = CreateFileRequest(
            file=file,
            purpose=purpose,
            extra_headers=extra_headers,
            extra_body=extra_body,
        )

        provider_config = ProviderConfigManager.get_provider_files_config(
            model="",
            provider=LlmProviders(custom_llm_provider),
        )
        if provider_config is not None:
            response = base_llm_http_handler.create_file(
                provider_config=provider_config,
                litellm_params=litellm_params_dict,
                create_file_data=_create_file_request,
                headers=extra_headers or {},
                api_base=optional_params.api_base,
                api_key=optional_params.api_key,
                logging_obj=logging_obj,
                _is_async=_is_async,
                client=client
                if client is not None
                and isinstance(client, (HTTPHandler, AsyncHTTPHandler))
                else None,
                timeout=timeout,
            )
        elif custom_llm_provider == "openai":
            # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            api_base = (
                optional_params.api_base
                or litellm.api_base
                or os.getenv("OPENAI_BASE_URL")
                or os.getenv("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )
            organization = (
                optional_params.organization
                or litellm.organization
                or os.getenv("OPENAI_ORGANIZATION", None)
                or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
            )
            # set API KEY
            api_key = (
                optional_params.api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
                or litellm.openai_key
                or os.getenv("OPENAI_API_KEY")
            )

            response = openai_files_instance.create_file(
                _is_async=_is_async,
                api_base=api_base,
                api_key=api_key,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                organization=organization,
                create_file_data=_create_file_request,
            )
        elif custom_llm_provider == "azure":
            api_base = optional_params.api_base or litellm.api_base or get_secret_str("AZURE_API_BASE")  # type: ignore
            api_version = (
                optional_params.api_version
                or litellm.api_version
                or get_secret_str("AZURE_API_VERSION")
            )  # type: ignore

            api_key = (
                optional_params.api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret_str("AZURE_OPENAI_API_KEY")
                or get_secret_str("AZURE_API_KEY")
            )  # type: ignore

            extra_body = optional_params.get("extra_body", {})
            if extra_body is not None:
                extra_body.pop("azure_ad_token", None)
            else:
                get_secret_str("AZURE_AD_TOKEN")  # type: ignore

            response = azure_files_instance.create_file(
                _is_async=_is_async,
                api_base=api_base,
                api_key=api_key,
                api_version=api_version,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                create_file_data=_create_file_request,
                litellm_params=litellm_params_dict,
            )
        elif custom_llm_provider == "vertex_ai":
            api_base = optional_params.api_base or ""
            vertex_ai_project = (
                optional_params.vertex_project
                or litellm.vertex_project
                or get_secret_str("VERTEXAI_PROJECT")
            )
            vertex_ai_location = (
                optional_params.vertex_location
                or litellm.vertex_location
                or get_secret_str("VERTEXAI_LOCATION")
            )
            vertex_credentials = optional_params.vertex_credentials or get_secret_str(
                "VERTEXAI_CREDENTIALS"
            )

            response = vertex_ai_files_instance.create_file(
                _is_async=_is_async,
                api_base=api_base,
                vertex_project=vertex_ai_project,
                vertex_location=vertex_ai_location,
                vertex_credentials=vertex_credentials,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                create_file_data=_create_file_request,
            )
        else:
            raise litellm.exceptions.BadRequestError(
                message="LiteLLM doesn't support {} for 'create_file'. Only ['openai', 'azure', 'vertex_ai'] are supported.".format(
                    custom_llm_provider
                ),
                model="n/a",
                llm_provider=custom_llm_provider,
                response=httpx.Response(
                    status_code=400,
                    content="Unsupported provider",
                    request=httpx.Request(method="create_file", url="https://github.com/BerriAI/litellm"),  # type: ignore
                ),
            )
        return response
    except Exception as e:
        raise e


async def afile_retrieve(
    file_id: str,
    custom_llm_provider: Literal["openai", "azure"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
):
    """
    Async: Get file contents

    LiteLLM Equivalent of GET https://api.openai.com/v1/files
    """
    try:
        loop = asyncio.get_event_loop()
        kwargs["is_async"] = True

        # Use a partial function to pass your keyword arguments
        func = partial(
            file_retrieve,
            file_id,
            custom_llm_provider,
            extra_headers,
            extra_body,
            **kwargs,
        )

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response

        return response
    except Exception as e:
        raise e


def file_retrieve(
    file_id: str,
    custom_llm_provider: Literal["openai", "azure"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> FileObject:
    """
    Returns the contents of the specified file.

    LiteLLM Equivalent of POST: POST https://api.openai.com/v1/files
    """
    try:
        optional_params = GenericLiteLLMParams(**kwargs)
        ### TIMEOUT LOGIC ###
        timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
        # set timeout for 10 minutes by default

        if (
            timeout is not None
            and isinstance(timeout, httpx.Timeout)
            and supports_httpx_timeout(custom_llm_provider) is False
        ):
            read_timeout = timeout.read or 600
            timeout = read_timeout  # default 10 min timeout
        elif timeout is not None and not isinstance(timeout, httpx.Timeout):
            timeout = float(timeout)  # type: ignore
        elif timeout is None:
            timeout = 600.0

        _is_async = kwargs.pop("is_async", False) is True

        if custom_llm_provider == "openai":
            # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            api_base = (
                optional_params.api_base
                or litellm.api_base
                or os.getenv("OPENAI_BASE_URL")
                or os.getenv("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )
            organization = (
                optional_params.organization
                or litellm.organization
                or os.getenv("OPENAI_ORGANIZATION", None)
                or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
            )
            # set API KEY
            api_key = (
                optional_params.api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
                or litellm.openai_key
                or os.getenv("OPENAI_API_KEY")
            )

            response = openai_files_instance.retrieve_file(
                file_id=file_id,
                _is_async=_is_async,
                api_base=api_base,
                api_key=api_key,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                organization=organization,
            )
        elif custom_llm_provider == "azure":
            api_base = optional_params.api_base or litellm.api_base or get_secret_str("AZURE_API_BASE")  # type: ignore
            api_version = (
                optional_params.api_version
                or litellm.api_version
                or get_secret_str("AZURE_API_VERSION")
            )  # type: ignore

            api_key = (
                optional_params.api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret_str("AZURE_OPENAI_API_KEY")
                or get_secret_str("AZURE_API_KEY")
            )  # type: ignore

            extra_body = optional_params.get("extra_body", {})
            if extra_body is not None:
                extra_body.pop("azure_ad_token", None)
            else:
                get_secret_str("AZURE_AD_TOKEN")  # type: ignore

            response = azure_files_instance.retrieve_file(
                _is_async=_is_async,
                api_base=api_base,
                api_key=api_key,
                api_version=api_version,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                file_id=file_id,
            )
        else:
            raise litellm.exceptions.BadRequestError(
                message="LiteLLM doesn't support {} for 'file_retrieve'. Only 'openai' and 'azure' are supported.".format(
                    custom_llm_provider
                ),
                model="n/a",
                llm_provider=custom_llm_provider,
                response=httpx.Response(
                    status_code=400,
                    content="Unsupported provider",
                    request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
                ),
            )
        return cast(FileObject, response)
    except Exception as e:
        raise e


# Delete file
async def afile_delete(
    file_id: str,
    custom_llm_provider: Literal["openai", "azure"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> Coroutine[Any, Any, FileObject]:
    """
    Async: Delete file

    LiteLLM Equivalent of DELETE https://api.openai.com/v1/files
    """
    try:
        loop = asyncio.get_event_loop()
        kwargs["is_async"] = True

        # Use a partial function to pass your keyword arguments
        func = partial(
            file_delete,
            file_id,
            custom_llm_provider,
            extra_headers,
            extra_body,
            **kwargs,
        )

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response  # type: ignore

        return cast(FileDeleted, response)  # type: ignore
    except Exception as e:
        raise e


def file_delete(
    file_id: str,
    custom_llm_provider: Literal["openai", "azure"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> FileDeleted:
    """
    Delete file

    LiteLLM Equivalent of DELETE https://api.openai.com/v1/files
    """
    try:
        optional_params = GenericLiteLLMParams(**kwargs)
        litellm_params_dict = get_litellm_params(**kwargs)
        ### TIMEOUT LOGIC ###
        timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
        # set timeout for 10 minutes by default
        client = kwargs.get("client")

        if (
            timeout is not None
            and isinstance(timeout, httpx.Timeout)
            and supports_httpx_timeout(custom_llm_provider) is False
        ):
            read_timeout = timeout.read or 600
            timeout = read_timeout  # default 10 min timeout
        elif timeout is not None and not isinstance(timeout, httpx.Timeout):
            timeout = float(timeout)  # type: ignore
        elif timeout is None:
            timeout = 600.0
        _is_async = kwargs.pop("is_async", False) is True
        if custom_llm_provider == "openai":
            # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            api_base = (
                optional_params.api_base
                or litellm.api_base
                or os.getenv("OPENAI_BASE_URL")
                or os.getenv("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )
            organization = (
                optional_params.organization
                or litellm.organization
                or os.getenv("OPENAI_ORGANIZATION", None)
                or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
            )
            # set API KEY
            api_key = (
                optional_params.api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
                or litellm.openai_key
                or os.getenv("OPENAI_API_KEY")
            )
            response = openai_files_instance.delete_file(
                file_id=file_id,
                _is_async=_is_async,
                api_base=api_base,
                api_key=api_key,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                organization=organization,
            )
        elif custom_llm_provider == "azure":
            api_base = optional_params.api_base or litellm.api_base or get_secret_str("AZURE_API_BASE")  # type: ignore
            api_version = (
                optional_params.api_version
                or litellm.api_version
                or get_secret_str("AZURE_API_VERSION")
            )  # type: ignore

            api_key = (
                optional_params.api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret_str("AZURE_OPENAI_API_KEY")
                or get_secret_str("AZURE_API_KEY")
            )  # type: ignore

            extra_body = optional_params.get("extra_body", {})
            if extra_body is not None:
                extra_body.pop("azure_ad_token", None)
            else:
                get_secret_str("AZURE_AD_TOKEN")  # type: ignore

            response = azure_files_instance.delete_file(
                _is_async=_is_async,
                api_base=api_base,
                api_key=api_key,
                api_version=api_version,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                file_id=file_id,
                client=client,
                litellm_params=litellm_params_dict,
            )
        else:
            raise litellm.exceptions.BadRequestError(
                message="LiteLLM doesn't support {} for 'create_batch'. Only 'openai' is supported.".format(
                    custom_llm_provider
                ),
                model="n/a",
                llm_provider=custom_llm_provider,
                response=httpx.Response(
                    status_code=400,
                    content="Unsupported provider",
                    request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
                ),
            )
        return cast(FileDeleted, response)
    except Exception as e:
        raise e


# List files
async def afile_list(
    custom_llm_provider: Literal["openai", "azure"] = "openai",
    purpose: Optional[str] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
):
    """
    Async: List files

    LiteLLM Equivalent of GET https://api.openai.com/v1/files
    """
    try:
        loop = asyncio.get_event_loop()
        kwargs["is_async"] = True

        # Use a partial function to pass your keyword arguments
        func = partial(
            file_list,
            custom_llm_provider,
            purpose,
            extra_headers,
            extra_body,
            **kwargs,
        )

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response  # type: ignore

        return response
    except Exception as e:
        raise e


def file_list(
    custom_llm_provider: Literal["openai", "azure"] = "openai",
    purpose: Optional[str] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
):
    """
    List files

    LiteLLM Equivalent of GET https://api.openai.com/v1/files
    """
    try:
        optional_params = GenericLiteLLMParams(**kwargs)
        ### TIMEOUT LOGIC ###
        timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
        # set timeout for 10 minutes by default

        if (
            timeout is not None
            and isinstance(timeout, httpx.Timeout)
            and supports_httpx_timeout(custom_llm_provider) is False
        ):
            read_timeout = timeout.read or 600
            timeout = read_timeout  # default 10 min timeout
        elif timeout is not None and not isinstance(timeout, httpx.Timeout):
            timeout = float(timeout)  # type: ignore
        elif timeout is None:
            timeout = 600.0

        _is_async = kwargs.pop("is_async", False) is True
        if custom_llm_provider == "openai":
            # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            api_base = (
                optional_params.api_base
                or litellm.api_base
                or os.getenv("OPENAI_BASE_URL")
                or os.getenv("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )
            organization = (
                optional_params.organization
                or litellm.organization
                or os.getenv("OPENAI_ORGANIZATION", None)
                or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
            )
            # set API KEY
            api_key = (
                optional_params.api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
                or litellm.openai_key
                or os.getenv("OPENAI_API_KEY")
            )

            response = openai_files_instance.list_files(
                purpose=purpose,
                _is_async=_is_async,
                api_base=api_base,
                api_key=api_key,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                organization=organization,
            )
        elif custom_llm_provider == "azure":
            api_base = optional_params.api_base or litellm.api_base or get_secret_str("AZURE_API_BASE")  # type: ignore
            api_version = (
                optional_params.api_version
                or litellm.api_version
                or get_secret_str("AZURE_API_VERSION")
            )  # type: ignore

            api_key = (
                optional_params.api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret_str("AZURE_OPENAI_API_KEY")
                or get_secret_str("AZURE_API_KEY")
            )  # type: ignore

            extra_body = optional_params.get("extra_body", {})
            if extra_body is not None:
                extra_body.pop("azure_ad_token", None)
            else:
                get_secret_str("AZURE_AD_TOKEN")  # type: ignore

            response = azure_files_instance.list_files(
                _is_async=_is_async,
                api_base=api_base,
                api_key=api_key,
                api_version=api_version,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                purpose=purpose,
            )
        else:
            raise litellm.exceptions.BadRequestError(
                message="LiteLLM doesn't support {} for 'file_list'. Only 'openai' and 'azure' are supported.".format(
                    custom_llm_provider
                ),
                model="n/a",
                llm_provider=custom_llm_provider,
                response=httpx.Response(
                    status_code=400,
                    content="Unsupported provider",
                    request=httpx.Request(method="file_list", url="https://github.com/BerriAI/litellm"),  # type: ignore
                ),
            )
        return response
    except Exception as e:
        raise e


async def afile_content(
    file_id: str,
    custom_llm_provider: Literal["openai", "azure"] = "openai",
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> HttpxBinaryResponseContent:
    """
    Async: Get file contents

    LiteLLM Equivalent of GET https://api.openai.com/v1/files
    """
    try:
        loop = asyncio.get_event_loop()
        kwargs["afile_content"] = True
        model = kwargs.pop("model", None)

        # Use a partial function to pass your keyword arguments
        func = partial(
            file_content,
            file_id,
            model,
            custom_llm_provider,
            extra_headers,
            extra_body,
            **kwargs,
        )

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response  # type: ignore

        return response
    except Exception as e:
        raise e


def file_content(
    file_id: str,
    model: Optional[str] = None,
    custom_llm_provider: Optional[
        Union[Literal["openai", "azure", "vertex_ai"], str]
    ] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    extra_body: Optional[Dict[str, str]] = None,
    **kwargs,
) -> Union[HttpxBinaryResponseContent, Coroutine[Any, Any, HttpxBinaryResponseContent]]:
    """
    Returns the contents of the specified file.

    LiteLLM Equivalent of POST: POST https://api.openai.com/v1/files
    """
    try:
        optional_params = GenericLiteLLMParams(**kwargs)
        litellm_params_dict = get_litellm_params(**kwargs)
        ### TIMEOUT LOGIC ###
        timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
        client = kwargs.get("client")
        # set timeout for 10 minutes by default

        try:
            if model is not None:
                _, custom_llm_provider, _, _ = get_llm_provider(
                    model, custom_llm_provider
                )
        except Exception:
            pass

        if (
            timeout is not None
            and isinstance(timeout, httpx.Timeout)
            and supports_httpx_timeout(cast(str, custom_llm_provider)) is False
        ):
            read_timeout = timeout.read or 600
            timeout = read_timeout  # default 10 min timeout
        elif timeout is not None and not isinstance(timeout, httpx.Timeout):
            timeout = float(timeout)  # type: ignore
        elif timeout is None:
            timeout = 600.0

        _file_content_request = FileContentRequest(
            file_id=file_id,
            extra_headers=extra_headers,
            extra_body=extra_body,
        )

        _is_async = kwargs.pop("afile_content", False) is True

        if custom_llm_provider == "openai":
            # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            api_base = (
                optional_params.api_base
                or litellm.api_base
                or os.getenv("OPENAI_BASE_URL")
                or os.getenv("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )
            organization = (
                optional_params.organization
                or litellm.organization
                or os.getenv("OPENAI_ORGANIZATION", None)
                or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
            )
            # set API KEY
            api_key = (
                optional_params.api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
                or litellm.openai_key
                or os.getenv("OPENAI_API_KEY")
            )

            response = openai_files_instance.file_content(
                _is_async=_is_async,
                file_content_request=_file_content_request,
                api_base=api_base,
                api_key=api_key,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                organization=organization,
            )
        elif custom_llm_provider == "azure":
            api_base = optional_params.api_base or litellm.api_base or get_secret_str("AZURE_API_BASE")  # type: ignore
            api_version = (
                optional_params.api_version
                or litellm.api_version
                or get_secret_str("AZURE_API_VERSION")
            )  # type: ignore

            api_key = (
                optional_params.api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret_str("AZURE_OPENAI_API_KEY")
                or get_secret_str("AZURE_API_KEY")
            )  # type: ignore

            extra_body = optional_params.get("extra_body", {})
            if extra_body is not None:
                extra_body.pop("azure_ad_token", None)
            else:
                get_secret_str("AZURE_AD_TOKEN")  # type: ignore

            response = azure_files_instance.file_content(
                _is_async=_is_async,
                api_base=api_base,
                api_key=api_key,
                api_version=api_version,
                timeout=timeout,
                max_retries=optional_params.max_retries,
                file_content_request=_file_content_request,
                client=client,
                litellm_params=litellm_params_dict,
            )
        else:
            raise litellm.exceptions.BadRequestError(
                message="LiteLLM doesn't support {} for 'custom_llm_provider'. Supported providers are 'openai', 'azure', 'vertex_ai'.".format(
                    custom_llm_provider
                ),
                model="n/a",
                llm_provider=custom_llm_provider,
                response=httpx.Response(
                    status_code=400,
                    content="Unsupported provider",
                    request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
                ),
            )
        return response
    except Exception as e:
        raise e

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\test_tokenize.py ===
"""
Unit tests for nltk.tokenize.
See also nltk/test/tokenize.doctest
"""

from typing import List, Tuple

import pytest

from nltk.tokenize import (
    LegalitySyllableTokenizer,
    StanfordSegmenter,
    SyllableTokenizer,
    TreebankWordTokenizer,
    TweetTokenizer,
    punkt,
    sent_tokenize,
    word_tokenize,
)
from nltk.tokenize.simple import CharTokenizer


def load_stanford_segmenter():
    try:
        seg = StanfordSegmenter()
        seg.default_config("ar")
        seg.default_config("zh")
        return True
    except LookupError:
        return False


check_stanford_segmenter = pytest.mark.skipif(
    not load_stanford_segmenter(),
    reason="NLTK was unable to find stanford-segmenter.jar.",
)


class TestTokenize:
    def test_tweet_tokenizer(self):
        """
        Test TweetTokenizer using words with special and accented characters.
        """

        tokenizer = TweetTokenizer(strip_handles=True, reduce_len=True)
        s9 = "@myke: Let's test these words: resumé España München français"
        tokens = tokenizer.tokenize(s9)
        expected = [
            ":",
            "Let's",
            "test",
            "these",
            "words",
            ":",
            "resumé",
            "España",
            "München",
            "français",
        ]
        assert tokens == expected

    @pytest.mark.parametrize(
        "test_input, expecteds",
        [
            (
                "My text 0106404243030 is great text",
                (
                    ["My", "text", "01064042430", "30", "is", "great", "text"],
                    ["My", "text", "0106404243030", "is", "great", "text"],
                ),
            ),
            (
                "My ticket id is 1234543124123",
                (
                    ["My", "ticket", "id", "is", "12345431241", "23"],
                    ["My", "ticket", "id", "is", "1234543124123"],
                ),
            ),
            (
                "@remy: This is waaaaayyyy too much for you!!!!!! 01064042430",
                (
                    [
                        ":",
                        "This",
                        "is",
                        "waaayyy",
                        "too",
                        "much",
                        "for",
                        "you",
                        "!",
                        "!",
                        "!",
                        "01064042430",
                    ],
                    [
                        ":",
                        "This",
                        "is",
                        "waaayyy",
                        "too",
                        "much",
                        "for",
                        "you",
                        "!",
                        "!",
                        "!",
                        "01064042430",
                    ],
                ),
            ),
            # Further tests from https://github.com/nltk/nltk/pull/2798#issuecomment-922533085,
            # showing the TweetTokenizer performance for `match_phone_numbers=True` and
            # `match_phone_numbers=False`.
            (
                # Some phone numbers are always tokenized, even with `match_phone_numbers=`False`
                "My number is 06-46124080, except it's not.",
                (
                    [
                        "My",
                        "number",
                        "is",
                        "06-46124080",
                        ",",
                        "except",
                        "it's",
                        "not",
                        ".",
                    ],
                    [
                        "My",
                        "number",
                        "is",
                        "06-46124080",
                        ",",
                        "except",
                        "it's",
                        "not",
                        ".",
                    ],
                ),
            ),
            (
                # Phone number here is only tokenized correctly if `match_phone_numbers=True`
                "My number is 601-984-4813, except it's not.",
                (
                    [
                        "My",
                        "number",
                        "is",
                        "601-984-4813",
                        ",",
                        "except",
                        "it's",
                        "not",
                        ".",
                    ],
                    [
                        "My",
                        "number",
                        "is",
                        "601-984-",
                        "4813",
                        ",",
                        "except",
                        "it's",
                        "not",
                        ".",
                    ],
                ),
            ),
            (
                # Phone number here is only tokenized correctly if `match_phone_numbers=True`
                "My number is (393)  928 -3010, except it's not.",
                (
                    [
                        "My",
                        "number",
                        "is",
                        "(393)  928 -3010",
                        ",",
                        "except",
                        "it's",
                        "not",
                        ".",
                    ],
                    [
                        "My",
                        "number",
                        "is",
                        "(",
                        "393",
                        ")",
                        "928",
                        "-",
                        "3010",
                        ",",
                        "except",
                        "it's",
                        "not",
                        ".",
                    ],
                ),
            ),
            (
                # A long number is tokenized correctly only if `match_phone_numbers=False`
                "The product identification number is 48103284512.",
                (
                    [
                        "The",
                        "product",
                        "identification",
                        "number",
                        "is",
                        "4810328451",
                        "2",
                        ".",
                    ],
                    [
                        "The",
                        "product",
                        "identification",
                        "number",
                        "is",
                        "48103284512",
                        ".",
                    ],
                ),
            ),
            (
                # `match_phone_numbers=True` can have some unforeseen
                "My favourite substraction is 240 - 1353.",
                (
                    ["My", "favourite", "substraction", "is", "240 - 1353", "."],
                    ["My", "favourite", "substraction", "is", "240", "-", "1353", "."],
                ),
            ),
        ],
    )
    def test_tweet_tokenizer_expanded(
        self, test_input: str, expecteds: Tuple[List[str], List[str]]
    ):
        """
        Test `match_phone_numbers` in TweetTokenizer.

        Note that TweetTokenizer is also passed the following for these tests:
            * strip_handles=True
            * reduce_len=True

        :param test_input: The input string to tokenize using TweetTokenizer.
        :type test_input: str
        :param expecteds: A 2-tuple of tokenized sentences. The first of the two
            tokenized is the expected output of tokenization with `match_phone_numbers=True`.
            The second of the two tokenized lists is the expected output of tokenization
            with `match_phone_numbers=False`.
        :type expecteds: Tuple[List[str], List[str]]
        """
        for match_phone_numbers, expected in zip([True, False], expecteds):
            tokenizer = TweetTokenizer(
                strip_handles=True,
                reduce_len=True,
                match_phone_numbers=match_phone_numbers,
            )
            predicted = tokenizer.tokenize(test_input)
            assert predicted == expected

    def test_sonority_sequencing_syllable_tokenizer(self):
        """
        Test SyllableTokenizer tokenizer.
        """
        tokenizer = SyllableTokenizer()
        tokens = tokenizer.tokenize("justification")
        assert tokens == ["jus", "ti", "fi", "ca", "tion"]

    def test_syllable_tokenizer_numbers(self):
        """
        Test SyllableTokenizer tokenizer.
        """
        tokenizer = SyllableTokenizer()
        text = "9" * 10000
        tokens = tokenizer.tokenize(text)
        assert tokens == [text]

    def test_legality_principle_syllable_tokenizer(self):
        """
        Test LegalitySyllableTokenizer tokenizer.
        """
        from nltk.corpus import words

        test_word = "wonderful"
        tokenizer = LegalitySyllableTokenizer(words.words())
        tokens = tokenizer.tokenize(test_word)
        assert tokens == ["won", "der", "ful"]

    @check_stanford_segmenter
    def test_stanford_segmenter_arabic(self):
        """
        Test the Stanford Word Segmenter for Arabic (default config)
        """
        seg = StanfordSegmenter()
        seg.default_config("ar")
        sent = "يبحث علم الحاسوب استخدام الحوسبة بجميع اشكالها لحل المشكلات"
        segmented_sent = seg.segment(sent.split())
        assert segmented_sent.split() == [
            "يبحث",
            "علم",
            "الحاسوب",
            "استخدام",
            "الحوسبة",
            "ب",
            "جميع",
            "اشكال",
            "ها",
            "ل",
            "حل",
            "المشكلات",
        ]

    @check_stanford_segmenter
    def test_stanford_segmenter_chinese(self):
        """
        Test the Stanford Word Segmenter for Chinese (default config)
        """
        seg = StanfordSegmenter()
        seg.default_config("zh")
        sent = "这是斯坦福中文分词器测试"
        segmented_sent = seg.segment(sent.split())
        assert segmented_sent.split() == [
            "这",
            "是",
            "斯坦福",
            "中文",
            "分词器",
            "测试",
        ]

    def test_phone_tokenizer(self):
        """
        Test a string that resembles a phone number but contains a newline
        """

        # Should be recognized as a phone number, albeit one with multiple spaces
        tokenizer = TweetTokenizer()
        test1 = "(393)  928 -3010"
        expected = ["(393)  928 -3010"]
        result = tokenizer.tokenize(test1)
        assert result == expected

        # Due to newline, first three elements aren't part of a phone number;
        # fourth is
        test2 = "(393)\n928 -3010"
        expected = ["(", "393", ")", "928 -3010"]
        result = tokenizer.tokenize(test2)
        assert result == expected

    def test_emoji_tokenizer(self):
        """
        Test a string that contains Emoji ZWJ Sequences and skin tone modifier
        """
        tokenizer = TweetTokenizer()

        # A Emoji ZWJ Sequences, they together build as a single emoji, should not be split.
        test1 = "👨‍👩‍👧‍👧"
        expected = ["👨‍👩‍👧‍👧"]
        result = tokenizer.tokenize(test1)
        assert result == expected

        # A Emoji with skin tone modifier, the two characters build a single emoji, should not be split.
        test2 = "👨🏿"
        expected = ["👨🏿"]
        result = tokenizer.tokenize(test2)
        assert result == expected

        # A string containing both skin tone modifier and ZWJ Sequences
        test3 = "🤔 🙈 me así, se😌 ds 💕👭👙 hello 👩🏾‍🎓 emoji hello 👨‍👩‍👦‍👦 how are 😊 you today🙅🏽🙅🏽"
        expected = [
            "🤔",
            "🙈",
            "me",
            "así",
            ",",
            "se",
            "😌",
            "ds",
            "💕",
            "👭",
            "👙",
            "hello",
            "👩🏾\u200d🎓",
            "emoji",
            "hello",
            "👨\u200d👩\u200d👦\u200d👦",
            "how",
            "are",
            "😊",
            "you",
            "today",
            "🙅🏽",
            "🙅🏽",
        ]
        result = tokenizer.tokenize(test3)
        assert result == expected

        # emoji flag sequences, including enclosed letter pairs
        # Expected behavior from #3034
        test4 = "🇦🇵🇵🇱🇪"
        expected = ["🇦🇵", "🇵🇱", "🇪"]
        result = tokenizer.tokenize(test4)
        assert result == expected

        test5 = "Hi 🇨🇦, 😍!!"
        expected = ["Hi", "🇨🇦", ",", "😍", "!", "!"]
        result = tokenizer.tokenize(test5)
        assert result == expected

        test6 = "<3 🇨🇦 🤝 🇵🇱 <3"
        expected = ["<3", "🇨🇦", "🤝", "🇵🇱", "<3"]
        result = tokenizer.tokenize(test6)
        assert result == expected

    def test_pad_asterisk(self):
        """
        Test padding of asterisk for word tokenization.
        """
        text = "This is a, *weird sentence with *asterisks in it."
        expected = [
            "This",
            "is",
            "a",
            ",",
            "*",
            "weird",
            "sentence",
            "with",
            "*",
            "asterisks",
            "in",
            "it",
            ".",
        ]
        assert word_tokenize(text) == expected

    def test_pad_dotdot(self):
        """
        Test padding of dotdot* for word tokenization.
        """
        text = "Why did dotdot.. not get tokenized but dotdotdot... did? How about manydots....."
        expected = [
            "Why",
            "did",
            "dotdot",
            "..",
            "not",
            "get",
            "tokenized",
            "but",
            "dotdotdot",
            "...",
            "did",
            "?",
            "How",
            "about",
            "manydots",
            ".....",
        ]
        assert word_tokenize(text) == expected

    def test_remove_handle(self):
        """
        Test remove_handle() from casual.py with specially crafted edge cases
        """

        tokenizer = TweetTokenizer(strip_handles=True)

        # Simple example. Handles with just numbers should be allowed
        test1 = "@twitter hello @twi_tter_. hi @12345 @123news"
        expected = ["hello", ".", "hi"]
        result = tokenizer.tokenize(test1)
        assert result == expected

        # Handles are allowed to follow any of the following characters
        test2 = "@n`@n~@n(@n)@n-@n=@n+@n\\@n|@n[@n]@n{@n}@n;@n:@n'@n\"@n/@n?@n.@n,@n<@n>@n @n\n@n ñ@n.ü@n.ç@n."
        expected = [
            "`",
            "~",
            "(",
            ")",
            "-",
            "=",
            "+",
            "\\",
            "|",
            "[",
            "]",
            "{",
            "}",
            ";",
            ":",
            "'",
            '"',
            "/",
            "?",
            ".",
            ",",
            "<",
            ">",
            "ñ",
            ".",
            "ü",
            ".",
            "ç",
            ".",
        ]
        result = tokenizer.tokenize(test2)
        assert result == expected

        # Handles are NOT allowed to follow any of the following characters
        test3 = "a@n j@n z@n A@n L@n Z@n 1@n 4@n 7@n 9@n 0@n _@n !@n @@n #@n $@n %@n &@n *@n"
        expected = [
            "a",
            "@n",
            "j",
            "@n",
            "z",
            "@n",
            "A",
            "@n",
            "L",
            "@n",
            "Z",
            "@n",
            "1",
            "@n",
            "4",
            "@n",
            "7",
            "@n",
            "9",
            "@n",
            "0",
            "@n",
            "_",
            "@n",
            "!",
            "@n",
            "@",
            "@n",
            "#",
            "@n",
            "$",
            "@n",
            "%",
            "@n",
            "&",
            "@n",
            "*",
            "@n",
        ]
        result = tokenizer.tokenize(test3)
        assert result == expected

        # Handles are allowed to precede the following characters
        test4 = "@n!a @n#a @n$a @n%a @n&a @n*a"
        expected = ["!", "a", "#", "a", "$", "a", "%", "a", "&", "a", "*", "a"]
        result = tokenizer.tokenize(test4)
        assert result == expected

        # Tests interactions with special symbols and multiple @
        test5 = "@n!@n @n#@n @n$@n @n%@n @n&@n @n*@n @n@n @@n @n@@n @n_@n @n7@n @nj@n"
        expected = [
            "!",
            "@n",
            "#",
            "@n",
            "$",
            "@n",
            "%",
            "@n",
            "&",
            "@n",
            "*",
            "@n",
            "@n",
            "@n",
            "@",
            "@n",
            "@n",
            "@",
            "@n",
            "@n_",
            "@n",
            "@n7",
            "@n",
            "@nj",
            "@n",
        ]
        result = tokenizer.tokenize(test5)
        assert result == expected

        # Tests that handles can have a max length of 15
        test6 = "@abcdefghijklmnopqrstuvwxyz @abcdefghijklmno1234 @abcdefghijklmno_ @abcdefghijklmnoendofhandle"
        expected = ["pqrstuvwxyz", "1234", "_", "endofhandle"]
        result = tokenizer.tokenize(test6)
        assert result == expected

        # Edge case where an @ comes directly after a long handle
        test7 = "@abcdefghijklmnop@abcde @abcdefghijklmno@abcde @abcdefghijklmno_@abcde @abcdefghijklmno5@abcde"
        expected = [
            "p",
            "@abcde",
            "@abcdefghijklmno",
            "@abcde",
            "_",
            "@abcde",
            "5",
            "@abcde",
        ]
        result = tokenizer.tokenize(test7)
        assert result == expected

    def test_treebank_span_tokenizer(self):
        """
        Test TreebankWordTokenizer.span_tokenize function
        """

        tokenizer = TreebankWordTokenizer()

        # Test case in the docstring
        test1 = "Good muffins cost $3.88\nin New (York).  Please (buy) me\ntwo of them.\n(Thanks)."
        expected = [
            (0, 4),
            (5, 12),
            (13, 17),
            (18, 19),
            (19, 23),
            (24, 26),
            (27, 30),
            (31, 32),
            (32, 36),
            (36, 37),
            (37, 38),
            (40, 46),
            (47, 48),
            (48, 51),
            (51, 52),
            (53, 55),
            (56, 59),
            (60, 62),
            (63, 68),
            (69, 70),
            (70, 76),
            (76, 77),
            (77, 78),
        ]
        result = list(tokenizer.span_tokenize(test1))
        assert result == expected

        # Test case with double quotation
        test2 = 'The DUP is similar to the "religious right" in the United States and takes a hardline stance on social issues'
        expected = [
            (0, 3),
            (4, 7),
            (8, 10),
            (11, 18),
            (19, 21),
            (22, 25),
            (26, 27),
            (27, 36),
            (37, 42),
            (42, 43),
            (44, 46),
            (47, 50),
            (51, 57),
            (58, 64),
            (65, 68),
            (69, 74),
            (75, 76),
            (77, 85),
            (86, 92),
            (93, 95),
            (96, 102),
            (103, 109),
        ]
        result = list(tokenizer.span_tokenize(test2))
        assert result == expected

        # Test case with double qoutation as well as converted quotations
        test3 = "The DUP is similar to the \"religious right\" in the United States and takes a ``hardline'' stance on social issues"
        expected = [
            (0, 3),
            (4, 7),
            (8, 10),
            (11, 18),
            (19, 21),
            (22, 25),
            (26, 27),
            (27, 36),
            (37, 42),
            (42, 43),
            (44, 46),
            (47, 50),
            (51, 57),
            (58, 64),
            (65, 68),
            (69, 74),
            (75, 76),
            (77, 79),
            (79, 87),
            (87, 89),
            (90, 96),
            (97, 99),
            (100, 106),
            (107, 113),
        ]
        result = list(tokenizer.span_tokenize(test3))
        assert result == expected

    def test_word_tokenize(self):
        """
        Test word_tokenize function
        """

        sentence = "The 'v', I've been fooled but I'll seek revenge."
        expected = [
            "The",
            "'",
            "v",
            "'",
            ",",
            "I",
            "'ve",
            "been",
            "fooled",
            "but",
            "I",
            "'ll",
            "seek",
            "revenge",
            ".",
        ]
        assert word_tokenize(sentence) == expected

        sentence = "'v' 're'"
        expected = ["'", "v", "'", "'re", "'"]
        assert word_tokenize(sentence) == expected

    def test_punkt_pair_iter(self):
        test_cases = [
            ("12", [("1", "2"), ("2", None)]),
            ("123", [("1", "2"), ("2", "3"), ("3", None)]),
            ("1234", [("1", "2"), ("2", "3"), ("3", "4"), ("4", None)]),
        ]

        for test_input, expected_output in test_cases:
            actual_output = [x for x in punkt._pair_iter(test_input)]

            assert actual_output == expected_output

    def test_punkt_pair_iter_handles_stop_iteration_exception(self):
        # test input to trigger StopIteration from next()
        it = iter([])
        # call method under test and produce a generator
        gen = punkt._pair_iter(it)
        # unpack generator, ensure that no error is raised
        list(gen)

    def test_punkt_tokenize_words_handles_stop_iteration_exception(self):
        obj = punkt.PunktBaseClass()

        class TestPunktTokenizeWordsMock:
            def word_tokenize(self, s):
                return iter([])

        obj._lang_vars = TestPunktTokenizeWordsMock()
        # unpack generator, ensure that no error is raised
        list(obj._tokenize_words("test"))

    def test_punkt_tokenize_custom_lang_vars(self):
        # Create LangVars including a full stop end character as used in Bengali
        class BengaliLanguageVars(punkt.PunktLanguageVars):
            sent_end_chars = (".", "?", "!", "\u0964")

        obj = punkt.PunktSentenceTokenizer(lang_vars=BengaliLanguageVars())

        # We now expect these sentences to be split up into the individual sentences
        sentences = "উপরাষ্ট্রপতি শ্রী এম ভেঙ্কাইয়া নাইডু সোমবার আই আই টি দিল্লির হীরক জয়ন্তী উদযাপনের উদ্বোধন করেছেন। অনলাইনের মাধ্যমে এই অনুষ্ঠানে কেন্দ্রীয় মানব সম্পদ উন্নয়নমন্ত্রী শ্রী রমেশ পোখরিয়াল ‘নিশাঙ্ক’  উপস্থিত ছিলেন। এই উপলক্ষ্যে উপরাষ্ট্রপতি হীরকজয়ন্তীর লোগো এবং ২০৩০-এর জন্য প্রতিষ্ঠানের লক্ষ্য ও পরিকল্পনার নথি প্রকাশ করেছেন।"
        expected = [
            "উপরাষ্ট্রপতি শ্রী এম ভেঙ্কাইয়া নাইডু সোমবার আই আই টি দিল্লির হীরক জয়ন্তী উদযাপনের উদ্বোধন করেছেন।",
            "অনলাইনের মাধ্যমে এই অনুষ্ঠানে কেন্দ্রীয় মানব সম্পদ উন্নয়নমন্ত্রী শ্রী রমেশ পোখরিয়াল ‘নিশাঙ্ক’  উপস্থিত ছিলেন।",
            "এই উপলক্ষ্যে উপরাষ্ট্রপতি হীরকজয়ন্তীর লোগো এবং ২০৩০-এর জন্য প্রতিষ্ঠানের লক্ষ্য ও পরিকল্পনার নথি প্রকাশ করেছেন।",
        ]

        assert obj.tokenize(sentences) == expected

    def test_punkt_tokenize_no_custom_lang_vars(self):
        obj = punkt.PunktSentenceTokenizer()

        # We expect these sentences to not be split properly, as the Bengali full stop '।' is not included in the default language vars
        sentences = "উপরাষ্ট্রপতি শ্রী এম ভেঙ্কাইয়া নাইডু সোমবার আই আই টি দিল্লির হীরক জয়ন্তী উদযাপনের উদ্বোধন করেছেন। অনলাইনের মাধ্যমে এই অনুষ্ঠানে কেন্দ্রীয় মানব সম্পদ উন্নয়নমন্ত্রী শ্রী রমেশ পোখরিয়াল ‘নিশাঙ্ক’  উপস্থিত ছিলেন। এই উপলক্ষ্যে উপরাষ্ট্রপতি হীরকজয়ন্তীর লোগো এবং ২০৩০-এর জন্য প্রতিষ্ঠানের লক্ষ্য ও পরিকল্পনার নথি প্রকাশ করেছেন।"
        expected = [
            "উপরাষ্ট্রপতি শ্রী এম ভেঙ্কাইয়া নাইডু সোমবার আই আই টি দিল্লির হীরক জয়ন্তী উদযাপনের উদ্বোধন করেছেন। অনলাইনের মাধ্যমে এই অনুষ্ঠানে কেন্দ্রীয় মানব সম্পদ উন্নয়নমন্ত্রী শ্রী রমেশ পোখরিয়াল ‘নিশাঙ্ক’  উপস্থিত ছিলেন। এই উপলক্ষ্যে উপরাষ্ট্রপতি হীরকজয়ন্তীর লোগো এবং ২০৩০-এর জন্য প্রতিষ্ঠানের লক্ষ্য ও পরিকল্পনার নথি প্রকাশ করেছেন।"
        ]

        assert obj.tokenize(sentences) == expected

    @pytest.mark.parametrize(
        "input_text,n_sents,n_splits,lang_vars",
        [
            # Test debug_decisions on a text with two sentences, split by a dot.
            ("Subject: Some subject. Attachments: Some attachments", 2, 1),
            # The sentence should be split into two sections,
            # with one split and hence one decision.
            # Test debug_decisions on a text with two sentences, split by an exclamation mark.
            ("Subject: Some subject! Attachments: Some attachments", 2, 1),
            # The sentence should be split into two sections,
            # with one split and hence one decision.
            # Test debug_decisions on a text with one sentences,
            # which is not split.
            ("This is just a normal sentence, just like any other.", 1, 0),
            # Hence just 1
        ],
    )
    def punkt_debug_decisions(self, input_text, n_sents, n_splits, lang_vars=None):
        tokenizer = punkt.PunktSentenceTokenizer()
        if lang_vars != None:
            tokenizer._lang_vars = lang_vars

        assert len(tokenizer.tokenize(input_text)) == n_sents
        assert len(list(tokenizer.debug_decisions(input_text))) == n_splits

    def test_punkt_debug_decisions_custom_end(self):
        # Test debug_decisions on a text with two sentences,
        # split by a custom end character, based on Issue #2519
        class ExtLangVars(punkt.PunktLanguageVars):
            sent_end_chars = (".", "?", "!", "^")

        self.punkt_debug_decisions(
            "Subject: Some subject^ Attachments: Some attachments",
            n_sents=2,
            n_splits=1,
            lang_vars=ExtLangVars(),
        )
        # The sentence should be split into two sections,
        # with one split and hence one decision.

    @pytest.mark.parametrize(
        "sentences, expected",
        [
            (
                "this is a test. . new sentence.",
                ["this is a test.", ".", "new sentence."],
            ),
            ("This. . . That", ["This.", ".", ".", "That"]),
            ("This..... That", ["This..... That"]),
            ("This... That", ["This... That"]),
            ("This.. . That", ["This.. .", "That"]),
            ("This. .. That", ["This.", ".. That"]),
            ("This. ,. That", ["This.", ",.", "That"]),
            ("This!!! That", ["This!!!", "That"]),
            ("This! That", ["This!", "That"]),
            (
                "1. This is R .\n2. This is A .\n3. That's all",
                ["1.", "This is R .", "2.", "This is A .", "3.", "That's all"],
            ),
            (
                "1. This is R .\t2. This is A .\t3. That's all",
                ["1.", "This is R .", "2.", "This is A .", "3.", "That's all"],
            ),
            ("Hello.\tThere", ["Hello.", "There"]),
        ],
    )
    def test_sent_tokenize(self, sentences: str, expected: List[str]):
        assert sent_tokenize(sentences) == expected

    def test_string_tokenizer(self) -> None:
        sentence = "Hello there"
        tokenizer = CharTokenizer()
        assert tokenizer.tokenize(sentence) == list(sentence)
        assert list(tokenizer.span_tokenize(sentence)) == [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 8),
            (8, 9),
            (9, 10),
            (10, 11),
        ]


class TestPunktTrainer:
    def test_punkt_train(self) -> None:
        trainer = punkt.PunktTrainer()
        trainer.train("This is a test.")

    def test_punkt_train_single_word(self) -> None:
        trainer = punkt.PunktTrainer()
        trainer.train("This.")

    def test_punkt_train_no_punc(self) -> None:
        trainer = punkt.PunktTrainer()
        trainer.train("This is a test")

# === NexusCore/openenv\Lib\site-packages\pycparser\ply\cpp.py ===
# -----------------------------------------------------------------------------
# cpp.py
#
# Author:  David Beazley (http://www.dabeaz.com)
# Copyright (C) 2017
# All rights reserved
#
# This module implements an ANSI-C style lexical preprocessor for PLY.
# -----------------------------------------------------------------------------
import sys

# Some Python 3 compatibility shims
if sys.version_info.major < 3:
    STRING_TYPES = (str, unicode)
else:
    STRING_TYPES = str
    xrange = range

# -----------------------------------------------------------------------------
# Default preprocessor lexer definitions.   These tokens are enough to get
# a basic preprocessor working.   Other modules may import these if they want
# -----------------------------------------------------------------------------

tokens = (
   'CPP_ID','CPP_INTEGER', 'CPP_FLOAT', 'CPP_STRING', 'CPP_CHAR', 'CPP_WS', 'CPP_COMMENT1', 'CPP_COMMENT2', 'CPP_POUND','CPP_DPOUND'
)

literals = "+-*/%|&~^<>=!?()[]{}.,;:\\\'\""

# Whitespace
def t_CPP_WS(t):
    r'\s+'
    t.lexer.lineno += t.value.count("\n")
    return t

t_CPP_POUND = r'\#'
t_CPP_DPOUND = r'\#\#'

# Identifier
t_CPP_ID = r'[A-Za-z_][\w_]*'

# Integer literal
def CPP_INTEGER(t):
    r'(((((0x)|(0X))[0-9a-fA-F]+)|(\d+))([uU][lL]|[lL][uU]|[uU]|[lL])?)'
    return t

t_CPP_INTEGER = CPP_INTEGER

# Floating literal
t_CPP_FLOAT = r'((\d+)(\.\d+)(e(\+|-)?(\d+))? | (\d+)e(\+|-)?(\d+))([lL]|[fF])?'

# String literal
def t_CPP_STRING(t):
    r'\"([^\\\n]|(\\(.|\n)))*?\"'
    t.lexer.lineno += t.value.count("\n")
    return t

# Character constant 'c' or L'c'
def t_CPP_CHAR(t):
    r'(L)?\'([^\\\n]|(\\(.|\n)))*?\''
    t.lexer.lineno += t.value.count("\n")
    return t

# Comment
def t_CPP_COMMENT1(t):
    r'(/\*(.|\n)*?\*/)'
    ncr = t.value.count("\n")
    t.lexer.lineno += ncr
    # replace with one space or a number of '\n'
    t.type = 'CPP_WS'; t.value = '\n' * ncr if ncr else ' '
    return t

# Line comment
def t_CPP_COMMENT2(t):
    r'(//.*?(\n|$))'
    # replace with '/n'
    t.type = 'CPP_WS'; t.value = '\n'
    return t

def t_error(t):
    t.type = t.value[0]
    t.value = t.value[0]
    t.lexer.skip(1)
    return t

import re
import copy
import time
import os.path

# -----------------------------------------------------------------------------
# trigraph()
#
# Given an input string, this function replaces all trigraph sequences.
# The following mapping is used:
#
#     ??=    #
#     ??/    \
#     ??'    ^
#     ??(    [
#     ??)    ]
#     ??!    |
#     ??<    {
#     ??>    }
#     ??-    ~
# -----------------------------------------------------------------------------

_trigraph_pat = re.compile(r'''\?\?[=/\'\(\)\!<>\-]''')
_trigraph_rep = {
    '=':'#',
    '/':'\\',
    "'":'^',
    '(':'[',
    ')':']',
    '!':'|',
    '<':'{',
    '>':'}',
    '-':'~'
}

def trigraph(input):
    return _trigraph_pat.sub(lambda g: _trigraph_rep[g.group()[-1]],input)

# ------------------------------------------------------------------
# Macro object
#
# This object holds information about preprocessor macros
#
#    .name      - Macro name (string)
#    .value     - Macro value (a list of tokens)
#    .arglist   - List of argument names
#    .variadic  - Boolean indicating whether or not variadic macro
#    .vararg    - Name of the variadic parameter
#
# When a macro is created, the macro replacement token sequence is
# pre-scanned and used to create patch lists that are later used
# during macro expansion
# ------------------------------------------------------------------

class Macro(object):
    def __init__(self,name,value,arglist=None,variadic=False):
        self.name = name
        self.value = value
        self.arglist = arglist
        self.variadic = variadic
        if variadic:
            self.vararg = arglist[-1]
        self.source = None

# ------------------------------------------------------------------
# Preprocessor object
#
# Object representing a preprocessor.  Contains macro definitions,
# include directories, and other information
# ------------------------------------------------------------------

class Preprocessor(object):
    def __init__(self,lexer=None):
        if lexer is None:
            lexer = lex.lexer
        self.lexer = lexer
        self.macros = { }
        self.path = []
        self.temp_path = []

        # Probe the lexer for selected tokens
        self.lexprobe()

        tm = time.localtime()
        self.define("__DATE__ \"%s\"" % time.strftime("%b %d %Y",tm))
        self.define("__TIME__ \"%s\"" % time.strftime("%H:%M:%S",tm))
        self.parser = None

    # -----------------------------------------------------------------------------
    # tokenize()
    #
    # Utility function. Given a string of text, tokenize into a list of tokens
    # -----------------------------------------------------------------------------

    def tokenize(self,text):
        tokens = []
        self.lexer.input(text)
        while True:
            tok = self.lexer.token()
            if not tok: break
            tokens.append(tok)
        return tokens

    # ---------------------------------------------------------------------
    # error()
    #
    # Report a preprocessor error/warning of some kind
    # ----------------------------------------------------------------------

    def error(self,file,line,msg):
        print("%s:%d %s" % (file,line,msg))

    # ----------------------------------------------------------------------
    # lexprobe()
    #
    # This method probes the preprocessor lexer object to discover
    # the token types of symbols that are important to the preprocessor.
    # If this works right, the preprocessor will simply "work"
    # with any suitable lexer regardless of how tokens have been named.
    # ----------------------------------------------------------------------

    def lexprobe(self):

        # Determine the token type for identifiers
        self.lexer.input("identifier")
        tok = self.lexer.token()
        if not tok or tok.value != "identifier":
            print("Couldn't determine identifier type")
        else:
            self.t_ID = tok.type

        # Determine the token type for integers
        self.lexer.input("12345")
        tok = self.lexer.token()
        if not tok or int(tok.value) != 12345:
            print("Couldn't determine integer type")
        else:
            self.t_INTEGER = tok.type
            self.t_INTEGER_TYPE = type(tok.value)

        # Determine the token type for strings enclosed in double quotes
        self.lexer.input("\"filename\"")
        tok = self.lexer.token()
        if not tok or tok.value != "\"filename\"":
            print("Couldn't determine string type")
        else:
            self.t_STRING = tok.type

        # Determine the token type for whitespace--if any
        self.lexer.input("  ")
        tok = self.lexer.token()
        if not tok or tok.value != "  ":
            self.t_SPACE = None
        else:
            self.t_SPACE = tok.type

        # Determine the token type for newlines
        self.lexer.input("\n")
        tok = self.lexer.token()
        if not tok or tok.value != "\n":
            self.t_NEWLINE = None
            print("Couldn't determine token for newlines")
        else:
            self.t_NEWLINE = tok.type

        self.t_WS = (self.t_SPACE, self.t_NEWLINE)

        # Check for other characters used by the preprocessor
        chars = [ '<','>','#','##','\\','(',')',',','.']
        for c in chars:
            self.lexer.input(c)
            tok = self.lexer.token()
            if not tok or tok.value != c:
                print("Unable to lex '%s' required for preprocessor" % c)

    # ----------------------------------------------------------------------
    # add_path()
    #
    # Adds a search path to the preprocessor.
    # ----------------------------------------------------------------------

    def add_path(self,path):
        self.path.append(path)

    # ----------------------------------------------------------------------
    # group_lines()
    #
    # Given an input string, this function splits it into lines.  Trailing whitespace
    # is removed.   Any line ending with \ is grouped with the next line.  This
    # function forms the lowest level of the preprocessor---grouping into text into
    # a line-by-line format.
    # ----------------------------------------------------------------------

    def group_lines(self,input):
        lex = self.lexer.clone()
        lines = [x.rstrip() for x in input.splitlines()]
        for i in xrange(len(lines)):
            j = i+1
            while lines[i].endswith('\\') and (j < len(lines)):
                lines[i] = lines[i][:-1]+lines[j]
                lines[j] = ""
                j += 1

        input = "\n".join(lines)
        lex.input(input)
        lex.lineno = 1

        current_line = []
        while True:
            tok = lex.token()
            if not tok:
                break
            current_line.append(tok)
            if tok.type in self.t_WS and '\n' in tok.value:
                yield current_line
                current_line = []

        if current_line:
            yield current_line

    # ----------------------------------------------------------------------
    # tokenstrip()
    #
    # Remove leading/trailing whitespace tokens from a token list
    # ----------------------------------------------------------------------

    def tokenstrip(self,tokens):
        i = 0
        while i < len(tokens) and tokens[i].type in self.t_WS:
            i += 1
        del tokens[:i]
        i = len(tokens)-1
        while i >= 0 and tokens[i].type in self.t_WS:
            i -= 1
        del tokens[i+1:]
        return tokens


    # ----------------------------------------------------------------------
    # collect_args()
    #
    # Collects comma separated arguments from a list of tokens.   The arguments
    # must be enclosed in parenthesis.  Returns a tuple (tokencount,args,positions)
    # where tokencount is the number of tokens consumed, args is a list of arguments,
    # and positions is a list of integers containing the starting index of each
    # argument.  Each argument is represented by a list of tokens.
    #
    # When collecting arguments, leading and trailing whitespace is removed
    # from each argument.
    #
    # This function properly handles nested parenthesis and commas---these do not
    # define new arguments.
    # ----------------------------------------------------------------------

    def collect_args(self,tokenlist):
        args = []
        positions = []
        current_arg = []
        nesting = 1
        tokenlen = len(tokenlist)

        # Search for the opening '('.
        i = 0
        while (i < tokenlen) and (tokenlist[i].type in self.t_WS):
            i += 1

        if (i < tokenlen) and (tokenlist[i].value == '('):
            positions.append(i+1)
        else:
            self.error(self.source,tokenlist[0].lineno,"Missing '(' in macro arguments")
            return 0, [], []

        i += 1

        while i < tokenlen:
            t = tokenlist[i]
            if t.value == '(':
                current_arg.append(t)
                nesting += 1
            elif t.value == ')':
                nesting -= 1
                if nesting == 0:
                    if current_arg:
                        args.append(self.tokenstrip(current_arg))
                        positions.append(i)
                    return i+1,args,positions
                current_arg.append(t)
            elif t.value == ',' and nesting == 1:
                args.append(self.tokenstrip(current_arg))
                positions.append(i+1)
                current_arg = []
            else:
                current_arg.append(t)
            i += 1

        # Missing end argument
        self.error(self.source,tokenlist[-1].lineno,"Missing ')' in macro arguments")
        return 0, [],[]

    # ----------------------------------------------------------------------
    # macro_prescan()
    #
    # Examine the macro value (token sequence) and identify patch points
    # This is used to speed up macro expansion later on---we'll know
    # right away where to apply patches to the value to form the expansion
    # ----------------------------------------------------------------------

    def macro_prescan(self,macro):
        macro.patch     = []             # Standard macro arguments
        macro.str_patch = []             # String conversion expansion
        macro.var_comma_patch = []       # Variadic macro comma patch
        i = 0
        while i < len(macro.value):
            if macro.value[i].type == self.t_ID and macro.value[i].value in macro.arglist:
                argnum = macro.arglist.index(macro.value[i].value)
                # Conversion of argument to a string
                if i > 0 and macro.value[i-1].value == '#':
                    macro.value[i] = copy.copy(macro.value[i])
                    macro.value[i].type = self.t_STRING
                    del macro.value[i-1]
                    macro.str_patch.append((argnum,i-1))
                    continue
                # Concatenation
                elif (i > 0 and macro.value[i-1].value == '##'):
                    macro.patch.append(('c',argnum,i-1))
                    del macro.value[i-1]
                    continue
                elif ((i+1) < len(macro.value) and macro.value[i+1].value == '##'):
                    macro.patch.append(('c',argnum,i))
                    i += 1
                    continue
                # Standard expansion
                else:
                    macro.patch.append(('e',argnum,i))
            elif macro.value[i].value == '##':
                if macro.variadic and (i > 0) and (macro.value[i-1].value == ',') and \
                        ((i+1) < len(macro.value)) and (macro.value[i+1].type == self.t_ID) and \
                        (macro.value[i+1].value == macro.vararg):
                    macro.var_comma_patch.append(i-1)
            i += 1
        macro.patch.sort(key=lambda x: x[2],reverse=True)

    # ----------------------------------------------------------------------
    # macro_expand_args()
    #
    # Given a Macro and list of arguments (each a token list), this method
    # returns an expanded version of a macro.  The return value is a token sequence
    # representing the replacement macro tokens
    # ----------------------------------------------------------------------

    def macro_expand_args(self,macro,args):
        # Make a copy of the macro token sequence
        rep = [copy.copy(_x) for _x in macro.value]

        # Make string expansion patches.  These do not alter the length of the replacement sequence

        str_expansion = {}
        for argnum, i in macro.str_patch:
            if argnum not in str_expansion:
                str_expansion[argnum] = ('"%s"' % "".join([x.value for x in args[argnum]])).replace("\\","\\\\")
            rep[i] = copy.copy(rep[i])
            rep[i].value = str_expansion[argnum]

        # Make the variadic macro comma patch.  If the variadic macro argument is empty, we get rid
        comma_patch = False
        if macro.variadic and not args[-1]:
            for i in macro.var_comma_patch:
                rep[i] = None
                comma_patch = True

        # Make all other patches.   The order of these matters.  It is assumed that the patch list
        # has been sorted in reverse order of patch location since replacements will cause the
        # size of the replacement sequence to expand from the patch point.

        expanded = { }
        for ptype, argnum, i in macro.patch:
            # Concatenation.   Argument is left unexpanded
            if ptype == 'c':
                rep[i:i+1] = args[argnum]
            # Normal expansion.  Argument is macro expanded first
            elif ptype == 'e':
                if argnum not in expanded:
                    expanded[argnum] = self.expand_macros(args[argnum])
                rep[i:i+1] = expanded[argnum]

        # Get rid of removed comma if necessary
        if comma_patch:
            rep = [_i for _i in rep if _i]

        return rep


    # ----------------------------------------------------------------------
    # expand_macros()
    #
    # Given a list of tokens, this function performs macro expansion.
    # The expanded argument is a dictionary that contains macros already
    # expanded.  This is used to prevent infinite recursion.
    # ----------------------------------------------------------------------

    def expand_macros(self,tokens,expanded=None):
        if expanded is None:
            expanded = {}
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t.type == self.t_ID:
                if t.value in self.macros and t.value not in expanded:
                    # Yes, we found a macro match
                    expanded[t.value] = True

                    m = self.macros[t.value]
                    if not m.arglist:
                        # A simple macro
                        ex = self.expand_macros([copy.copy(_x) for _x in m.value],expanded)
                        for e in ex:
                            e.lineno = t.lineno
                        tokens[i:i+1] = ex
                        i += len(ex)
                    else:
                        # A macro with arguments
                        j = i + 1
                        while j < len(tokens) and tokens[j].type in self.t_WS:
                            j += 1
                        if tokens[j].value == '(':
                            tokcount,args,positions = self.collect_args(tokens[j:])
                            if not m.variadic and len(args) !=  len(m.arglist):
                                self.error(self.source,t.lineno,"Macro %s requires %d arguments" % (t.value,len(m.arglist)))
                                i = j + tokcount
                            elif m.variadic and len(args) < len(m.arglist)-1:
                                if len(m.arglist) > 2:
                                    self.error(self.source,t.lineno,"Macro %s must have at least %d arguments" % (t.value, len(m.arglist)-1))
                                else:
                                    self.error(self.source,t.lineno,"Macro %s must have at least %d argument" % (t.value, len(m.arglist)-1))
                                i = j + tokcount
                            else:
                                if m.variadic:
                                    if len(args) == len(m.arglist)-1:
                                        args.append([])
                                    else:
                                        args[len(m.arglist)-1] = tokens[j+positions[len(m.arglist)-1]:j+tokcount-1]
                                        del args[len(m.arglist):]

                                # Get macro replacement text
                                rep = self.macro_expand_args(m,args)
                                rep = self.expand_macros(rep,expanded)
                                for r in rep:
                                    r.lineno = t.lineno
                                tokens[i:j+tokcount] = rep
                                i += len(rep)
                    del expanded[t.value]
                    continue
                elif t.value == '__LINE__':
                    t.type = self.t_INTEGER
                    t.value = self.t_INTEGER_TYPE(t.lineno)

            i += 1
        return tokens

    # ----------------------------------------------------------------------
    # evalexpr()
    #
    # Evaluate an expression token sequence for the purposes of evaluating
    # integral expressions.
    # ----------------------------------------------------------------------

    def evalexpr(self,tokens):
        # tokens = tokenize(line)
        # Search for defined macros
        i = 0
        while i < len(tokens):
            if tokens[i].type == self.t_ID and tokens[i].value == 'defined':
                j = i + 1
                needparen = False
                result = "0L"
                while j < len(tokens):
                    if tokens[j].type in self.t_WS:
                        j += 1
                        continue
                    elif tokens[j].type == self.t_ID:
                        if tokens[j].value in self.macros:
                            result = "1L"
                        else:
                            result = "0L"
                        if not needparen: break
                    elif tokens[j].value == '(':
                        needparen = True
                    elif tokens[j].value == ')':
                        break
                    else:
                        self.error(self.source,tokens[i].lineno,"Malformed defined()")
                    j += 1
                tokens[i].type = self.t_INTEGER
                tokens[i].value = self.t_INTEGER_TYPE(result)
                del tokens[i+1:j+1]
            i += 1
        tokens = self.expand_macros(tokens)
        for i,t in enumerate(tokens):
            if t.type == self.t_ID:
                tokens[i] = copy.copy(t)
                tokens[i].type = self.t_INTEGER
                tokens[i].value = self.t_INTEGER_TYPE("0L")
            elif t.type == self.t_INTEGER:
                tokens[i] = copy.copy(t)
                # Strip off any trailing suffixes
                tokens[i].value = str(tokens[i].value)
                while tokens[i].value[-1] not in "0123456789abcdefABCDEF":
                    tokens[i].value = tokens[i].value[:-1]

        expr = "".join([str(x.value) for x in tokens])
        expr = expr.replace("&&"," and ")
        expr = expr.replace("||"," or ")
        expr = expr.replace("!"," not ")
        try:
            result = eval(expr)
        except Exception:
            self.error(self.source,tokens[0].lineno,"Couldn't evaluate expression")
            result = 0
        return result

    # ----------------------------------------------------------------------
    # parsegen()
    #
    # Parse an input string/
    # ----------------------------------------------------------------------
    def parsegen(self,input,source=None):

        # Replace trigraph sequences
        t = trigraph(input)
        lines = self.group_lines(t)

        if not source:
            source = ""

        self.define("__FILE__ \"%s\"" % source)

        self.source = source
        chunk = []
        enable = True
        iftrigger = False
        ifstack = []

        for x in lines:
            for i,tok in enumerate(x):
                if tok.type not in self.t_WS: break
            if tok.value == '#':
                # Preprocessor directive

                # insert necessary whitespace instead of eaten tokens
                for tok in x:
                    if tok.type in self.t_WS and '\n' in tok.value:
                        chunk.append(tok)

                dirtokens = self.tokenstrip(x[i+1:])
                if dirtokens:
                    name = dirtokens[0].value
                    args = self.tokenstrip(dirtokens[1:])
                else:
                    name = ""
                    args = []

                if name == 'define':
                    if enable:
                        for tok in self.expand_macros(chunk):
                            yield tok
                        chunk = []
                        self.define(args)
                elif name == 'include':
                    if enable:
                        for tok in self.expand_macros(chunk):
                            yield tok
                        chunk = []
                        oldfile = self.macros['__FILE__']
                        for tok in self.include(args):
                            yield tok
                        self.macros['__FILE__'] = oldfile
                        self.source = source
                elif name == 'undef':
                    if enable:
                        for tok in self.expand_macros(chunk):
                            yield tok
                        chunk = []
                        self.undef(args)
                elif name == 'ifdef':
                    ifstack.append((enable,iftrigger))
                    if enable:
                        if not args[0].value in self.macros:
                            enable = False
                            iftrigger = False
                        else:
                            iftrigger = True
                elif name == 'ifndef':
                    ifstack.append((enable,iftrigger))
                    if enable:
                        if args[0].value in self.macros:
                            enable = False
                            iftrigger = False
                        else:
                            iftrigger = True
                elif name == 'if':
                    ifstack.append((enable,iftrigger))
                    if enable:
                        result = self.evalexpr(args)
                        if not result:
                            enable = False
                            iftrigger = False
                        else:
                            iftrigger = True
                elif name == 'elif':
                    if ifstack:
                        if ifstack[-1][0]:     # We only pay attention if outer "if" allows this
                            if enable:         # If already true, we flip enable False
                                enable = False
                            elif not iftrigger:   # If False, but not triggered yet, we'll check expression
                                result = self.evalexpr(args)
                                if result:
                                    enable  = True
                                    iftrigger = True
                    else:
                        self.error(self.source,dirtokens[0].lineno,"Misplaced #elif")

                elif name == 'else':
                    if ifstack:
                        if ifstack[-1][0]:
                            if enable:
                                enable = False
                            elif not iftrigger:
                                enable = True
                                iftrigger = True
                    else:
                        self.error(self.source,dirtokens[0].lineno,"Misplaced #else")

                elif name == 'endif':
                    if ifstack:
                        enable,iftrigger = ifstack.pop()
                    else:
                        self.error(self.source,dirtokens[0].lineno,"Misplaced #endif")
                else:
                    # Unknown preprocessor directive
                    pass

            else:
                # Normal text
                if enable:
                    chunk.extend(x)

        for tok in self.expand_macros(chunk):
            yield tok
        chunk = []

    # ----------------------------------------------------------------------
    # include()
    #
    # Implementation of file-inclusion
    # ----------------------------------------------------------------------

    def include(self,tokens):
        # Try to extract the filename and then process an include file
        if not tokens:
            return
        if tokens:
            if tokens[0].value != '<' and tokens[0].type != self.t_STRING:
                tokens = self.expand_macros(tokens)

            if tokens[0].value == '<':
                # Include <...>
                i = 1
                while i < len(tokens):
                    if tokens[i].value == '>':
                        break
                    i += 1
                else:
                    print("Malformed #include <...>")
                    return
                filename = "".join([x.value for x in tokens[1:i]])
                path = self.path + [""] + self.temp_path
            elif tokens[0].type == self.t_STRING:
                filename = tokens[0].value[1:-1]
                path = self.temp_path + [""] + self.path
            else:
                print("Malformed #include statement")
                return
        for p in path:
            iname = os.path.join(p,filename)
            try:
                data = open(iname,"r").read()
                dname = os.path.dirname(iname)
                if dname:
                    self.temp_path.insert(0,dname)
                for tok in self.parsegen(data,filename):
                    yield tok
                if dname:
                    del self.temp_path[0]
                break
            except IOError:
                pass
        else:
            print("Couldn't find '%s'" % filename)

    # ----------------------------------------------------------------------
    # define()
    #
    # Define a new macro
    # ----------------------------------------------------------------------

    def define(self,tokens):
        if isinstance(tokens,STRING_TYPES):
            tokens = self.tokenize(tokens)

        linetok = tokens
        try:
            name = linetok[0]
            if len(linetok) > 1:
                mtype = linetok[1]
            else:
                mtype = None
            if not mtype:
                m = Macro(name.value,[])
                self.macros[name.value] = m
            elif mtype.type in self.t_WS:
                # A normal macro
                m = Macro(name.value,self.tokenstrip(linetok[2:]))
                self.macros[name.value] = m
            elif mtype.value == '(':
                # A macro with arguments
                tokcount, args, positions = self.collect_args(linetok[1:])
                variadic = False
                for a in args:
                    if variadic:
                        print("No more arguments may follow a variadic argument")
                        break
                    astr = "".join([str(_i.value) for _i in a])
                    if astr == "...":
                        variadic = True
                        a[0].type = self.t_ID
                        a[0].value = '__VA_ARGS__'
                        variadic = True
                        del a[1:]
                        continue
                    elif astr[-3:] == "..." and a[0].type == self.t_ID:
                        variadic = True
                        del a[1:]
                        # If, for some reason, "." is part of the identifier, strip off the name for the purposes
                        # of macro expansion
                        if a[0].value[-3:] == '...':
                            a[0].value = a[0].value[:-3]
                        continue
                    if len(a) > 1 or a[0].type != self.t_ID:
                        print("Invalid macro argument")
                        break
                else:
                    mvalue = self.tokenstrip(linetok[1+tokcount:])
                    i = 0
                    while i < len(mvalue):
                        if i+1 < len(mvalue):
                            if mvalue[i].type in self.t_WS and mvalue[i+1].value == '##':
                                del mvalue[i]
                                continue
                            elif mvalue[i].value == '##' and mvalue[i+1].type in self.t_WS:
                                del mvalue[i+1]
                        i += 1
                    m = Macro(name.value,mvalue,[x[0].value for x in args],variadic)
                    self.macro_prescan(m)
                    self.macros[name.value] = m
            else:
                print("Bad macro definition")
        except LookupError:
            print("Bad macro definition")

    # ----------------------------------------------------------------------
    # undef()
    #
    # Undefine a macro
    # ----------------------------------------------------------------------

    def undef(self,tokens):
        id = tokens[0].value
        try:
            del self.macros[id]
        except LookupError:
            pass

    # ----------------------------------------------------------------------
    # parse()
    #
    # Parse input text.
    # ----------------------------------------------------------------------
    def parse(self,input,source=None,ignore={}):
        self.ignore = ignore
        self.parser = self.parsegen(input,source)

    # ----------------------------------------------------------------------
    # token()
    #
    # Method to return individual tokens
    # ----------------------------------------------------------------------
    def token(self):
        try:
            while True:
                tok = next(self.parser)
                if tok.type not in self.ignore: return tok
        except StopIteration:
            self.parser = None
            return None

if __name__ == '__main__':
    import ply.lex as lex
    lexer = lex.lex()

    # Run a preprocessor
    import sys
    f = open(sys.argv[1])
    input = f.read()

    p = Preprocessor(lexer)
    p.parse(input,sys.argv[1])
    while True:
        tok = p.token()
        if not tok: break
        print(p.source, tok)

# === NexusCore/openenv\Lib\site-packages\google\protobuf\json_format.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Contains routines for printing protocol messages in JSON format.

Simple usage example:

  # Create a proto object and serialize it to a json format string.
  message = my_proto_pb2.MyMessage(foo='bar')
  json_string = json_format.MessageToJson(message)

  # Parse a json format string to proto object.
  message = json_format.Parse(json_string, my_proto_pb2.MyMessage())
"""

__author__ = 'jieluo@google.com (Jie Luo)'


import base64
from collections import OrderedDict
import json
import math
from operator import methodcaller
import re

from google.protobuf.internal import type_checkers
from google.protobuf import descriptor
from google.protobuf import message_factory
from google.protobuf import symbol_database


_INT_TYPES = frozenset([descriptor.FieldDescriptor.CPPTYPE_INT32,
                        descriptor.FieldDescriptor.CPPTYPE_UINT32,
                        descriptor.FieldDescriptor.CPPTYPE_INT64,
                        descriptor.FieldDescriptor.CPPTYPE_UINT64])
_INT64_TYPES = frozenset([descriptor.FieldDescriptor.CPPTYPE_INT64,
                          descriptor.FieldDescriptor.CPPTYPE_UINT64])
_FLOAT_TYPES = frozenset([descriptor.FieldDescriptor.CPPTYPE_FLOAT,
                          descriptor.FieldDescriptor.CPPTYPE_DOUBLE])
_INFINITY = 'Infinity'
_NEG_INFINITY = '-Infinity'
_NAN = 'NaN'

_UNPAIRED_SURROGATE_PATTERN = re.compile(
    u'[\ud800-\udbff](?![\udc00-\udfff])|(?<![\ud800-\udbff])[\udc00-\udfff]')

_VALID_EXTENSION_NAME = re.compile(r'\[[a-zA-Z0-9\._]*\]$')


class Error(Exception):
  """Top-level module error for json_format."""


class SerializeToJsonError(Error):
  """Thrown if serialization to JSON fails."""


class ParseError(Error):
  """Thrown in case of parsing error."""


def MessageToJson(
    message,
    including_default_value_fields=False,
    preserving_proto_field_name=False,
    indent=2,
    sort_keys=False,
    use_integers_for_enums=False,
    descriptor_pool=None,
    float_precision=None,
    ensure_ascii=True):
  """Converts protobuf message to JSON format.

  Args:
    message: The protocol buffers message instance to serialize.
    including_default_value_fields: If True, singular primitive fields,
        repeated fields, and map fields will always be serialized.  If
        False, only serialize non-empty fields.  Singular message fields
        and oneof fields are not affected by this option.
    preserving_proto_field_name: If True, use the original proto field
        names as defined in the .proto file. If False, convert the field
        names to lowerCamelCase.
    indent: The JSON object will be pretty-printed with this indent level.
        An indent level of 0 or negative will only insert newlines. If the
        indent level is None, no newlines will be inserted.
    sort_keys: If True, then the output will be sorted by field names.
    use_integers_for_enums: If true, print integers instead of enum names.
    descriptor_pool: A Descriptor Pool for resolving types. If None use the
        default.
    float_precision: If set, use this to specify float field valid digits.
    ensure_ascii: If True, strings with non-ASCII characters are escaped.
        If False, Unicode strings are returned unchanged.

  Returns:
    A string containing the JSON formatted protocol buffer message.
  """
  printer = _Printer(
      including_default_value_fields,
      preserving_proto_field_name,
      use_integers_for_enums,
      descriptor_pool,
      float_precision=float_precision)
  return printer.ToJsonString(message, indent, sort_keys, ensure_ascii)


def MessageToDict(
    message,
    including_default_value_fields=False,
    preserving_proto_field_name=False,
    use_integers_for_enums=False,
    descriptor_pool=None,
    float_precision=None):
  """Converts protobuf message to a dictionary.

  When the dictionary is encoded to JSON, it conforms to proto3 JSON spec.

  Args:
    message: The protocol buffers message instance to serialize.
    including_default_value_fields: If True, singular primitive fields,
        repeated fields, and map fields will always be serialized.  If
        False, only serialize non-empty fields.  Singular message fields
        and oneof fields are not affected by this option.
    preserving_proto_field_name: If True, use the original proto field
        names as defined in the .proto file. If False, convert the field
        names to lowerCamelCase.
    use_integers_for_enums: If true, print integers instead of enum names.
    descriptor_pool: A Descriptor Pool for resolving types. If None use the
        default.
    float_precision: If set, use this to specify float field valid digits.

  Returns:
    A dict representation of the protocol buffer message.
  """
  printer = _Printer(
      including_default_value_fields,
      preserving_proto_field_name,
      use_integers_for_enums,
      descriptor_pool,
      float_precision=float_precision)
  # pylint: disable=protected-access
  return printer._MessageToJsonObject(message)


def _IsMapEntry(field):
  return (field.type == descriptor.FieldDescriptor.TYPE_MESSAGE and
          field.message_type.has_options and
          field.message_type.GetOptions().map_entry)


class _Printer(object):
  """JSON format printer for protocol message."""

  def __init__(
      self,
      including_default_value_fields=False,
      preserving_proto_field_name=False,
      use_integers_for_enums=False,
      descriptor_pool=None,
      float_precision=None):
    self.including_default_value_fields = including_default_value_fields
    self.preserving_proto_field_name = preserving_proto_field_name
    self.use_integers_for_enums = use_integers_for_enums
    self.descriptor_pool = descriptor_pool
    if float_precision:
      self.float_format = '.{}g'.format(float_precision)
    else:
      self.float_format = None

  def ToJsonString(self, message, indent, sort_keys, ensure_ascii):
    js = self._MessageToJsonObject(message)
    return json.dumps(
        js, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)

  def _MessageToJsonObject(self, message):
    """Converts message to an object according to Proto3 JSON Specification."""
    message_descriptor = message.DESCRIPTOR
    full_name = message_descriptor.full_name
    if _IsWrapperMessage(message_descriptor):
      return self._WrapperMessageToJsonObject(message)
    if full_name in _WKTJSONMETHODS:
      return methodcaller(_WKTJSONMETHODS[full_name][0], message)(self)
    js = {}
    return self._RegularMessageToJsonObject(message, js)

  def _RegularMessageToJsonObject(self, message, js):
    """Converts normal message according to Proto3 JSON Specification."""
    fields = message.ListFields()

    try:
      for field, value in fields:
        if self.preserving_proto_field_name:
          name = field.name
        else:
          name = field.json_name
        if _IsMapEntry(field):
          # Convert a map field.
          v_field = field.message_type.fields_by_name['value']
          js_map = {}
          for key in value:
            if isinstance(key, bool):
              if key:
                recorded_key = 'true'
              else:
                recorded_key = 'false'
            else:
              recorded_key = str(key)
            js_map[recorded_key] = self._FieldToJsonObject(
                v_field, value[key])
          js[name] = js_map
        elif field.label == descriptor.FieldDescriptor.LABEL_REPEATED:
          # Convert a repeated field.
          js[name] = [self._FieldToJsonObject(field, k)
                      for k in value]
        elif field.is_extension:
          name = '[%s]' % field.full_name
          js[name] = self._FieldToJsonObject(field, value)
        else:
          js[name] = self._FieldToJsonObject(field, value)

      # Serialize default value if including_default_value_fields is True.
      if self.including_default_value_fields:
        message_descriptor = message.DESCRIPTOR
        for field in message_descriptor.fields:
          # Singular message fields and oneof fields will not be affected.
          if ((field.label != descriptor.FieldDescriptor.LABEL_REPEATED and
               field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_MESSAGE) or
              field.containing_oneof):
            continue
          if self.preserving_proto_field_name:
            name = field.name
          else:
            name = field.json_name
          if name in js:
            # Skip the field which has been serialized already.
            continue
          if _IsMapEntry(field):
            js[name] = {}
          elif field.label == descriptor.FieldDescriptor.LABEL_REPEATED:
            js[name] = []
          else:
            js[name] = self._FieldToJsonObject(field, field.default_value)

    except ValueError as e:
      raise SerializeToJsonError(
          'Failed to serialize {0} field: {1}.'.format(field.name, e)) from e

    return js

  def _FieldToJsonObject(self, field, value):
    """Converts field value according to Proto3 JSON Specification."""
    if field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_MESSAGE:
      return self._MessageToJsonObject(value)
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_ENUM:
      if self.use_integers_for_enums:
        return value
      if field.enum_type.full_name == 'google.protobuf.NullValue':
        return None
      enum_value = field.enum_type.values_by_number.get(value, None)
      if enum_value is not None:
        return enum_value.name
      else:
        if field.enum_type.is_closed:
          raise SerializeToJsonError('Enum field contains an integer value '
                                     'which can not mapped to an enum value.')
        else:
          return value
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_STRING:
      if field.type == descriptor.FieldDescriptor.TYPE_BYTES:
        # Use base64 Data encoding for bytes
        return base64.b64encode(value).decode('utf-8')
      else:
        return value
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_BOOL:
      return bool(value)
    elif field.cpp_type in _INT64_TYPES:
      return str(value)
    elif field.cpp_type in _FLOAT_TYPES:
      if math.isinf(value):
        if value < 0.0:
          return _NEG_INFINITY
        else:
          return _INFINITY
      if math.isnan(value):
        return _NAN
      if field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_FLOAT:
        if self.float_format:
          return float(format(value, self.float_format))
        else:
          return type_checkers.ToShortestFloat(value)

    return value

  def _AnyMessageToJsonObject(self, message):
    """Converts Any message according to Proto3 JSON Specification."""
    if not message.ListFields():
      return {}
    # Must print @type first, use OrderedDict instead of {}
    js = OrderedDict()
    type_url = message.type_url
    js['@type'] = type_url
    sub_message = _CreateMessageFromTypeUrl(type_url, self.descriptor_pool)
    sub_message.ParseFromString(message.value)
    message_descriptor = sub_message.DESCRIPTOR
    full_name = message_descriptor.full_name
    if _IsWrapperMessage(message_descriptor):
      js['value'] = self._WrapperMessageToJsonObject(sub_message)
      return js
    if full_name in _WKTJSONMETHODS:
      js['value'] = methodcaller(_WKTJSONMETHODS[full_name][0],
                                 sub_message)(self)
      return js
    return self._RegularMessageToJsonObject(sub_message, js)

  def _GenericMessageToJsonObject(self, message):
    """Converts message according to Proto3 JSON Specification."""
    # Duration, Timestamp and FieldMask have ToJsonString method to do the
    # convert. Users can also call the method directly.
    return message.ToJsonString()

  def _ValueMessageToJsonObject(self, message):
    """Converts Value message according to Proto3 JSON Specification."""
    which = message.WhichOneof('kind')
    # If the Value message is not set treat as null_value when serialize
    # to JSON. The parse back result will be different from original message.
    if which is None or which == 'null_value':
      return None
    if which == 'list_value':
      return self._ListValueMessageToJsonObject(message.list_value)
    if which == 'number_value':
      value = message.number_value
      if math.isinf(value):
        raise ValueError('Fail to serialize Infinity for Value.number_value, '
                         'which would parse as string_value')
      if math.isnan(value):
        raise ValueError('Fail to serialize NaN for Value.number_value, '
                         'which would parse as string_value')
    else:
      value = getattr(message, which)
    oneof_descriptor = message.DESCRIPTOR.fields_by_name[which]
    return self._FieldToJsonObject(oneof_descriptor, value)

  def _ListValueMessageToJsonObject(self, message):
    """Converts ListValue message according to Proto3 JSON Specification."""
    return [self._ValueMessageToJsonObject(value)
            for value in message.values]

  def _StructMessageToJsonObject(self, message):
    """Converts Struct message according to Proto3 JSON Specification."""
    fields = message.fields
    ret = {}
    for key in fields:
      ret[key] = self._ValueMessageToJsonObject(fields[key])
    return ret

  def _WrapperMessageToJsonObject(self, message):
    return self._FieldToJsonObject(
        message.DESCRIPTOR.fields_by_name['value'], message.value)


def _IsWrapperMessage(message_descriptor):
  return message_descriptor.file.name == 'google/protobuf/wrappers.proto'


def _DuplicateChecker(js):
  result = {}
  for name, value in js:
    if name in result:
      raise ParseError('Failed to load JSON: duplicate key {0}.'.format(name))
    result[name] = value
  return result


def _CreateMessageFromTypeUrl(type_url, descriptor_pool):
  """Creates a message from a type URL."""
  db = symbol_database.Default()
  pool = db.pool if descriptor_pool is None else descriptor_pool
  type_name = type_url.split('/')[-1]
  try:
    message_descriptor = pool.FindMessageTypeByName(type_name)
  except KeyError as e:
    raise TypeError(
        'Can not find message descriptor by type_url: {0}'.format(type_url)
      ) from e
  message_class = message_factory.GetMessageClass(message_descriptor)
  return message_class()


def Parse(text,
          message,
          ignore_unknown_fields=False,
          descriptor_pool=None,
          max_recursion_depth=100):
  """Parses a JSON representation of a protocol message into a message.

  Args:
    text: Message JSON representation.
    message: A protocol buffer message to merge into.
    ignore_unknown_fields: If True, do not raise errors for unknown fields.
    descriptor_pool: A Descriptor Pool for resolving types. If None use the
      default.
    max_recursion_depth: max recursion depth of JSON message to be
      deserialized. JSON messages over this depth will fail to be
      deserialized. Default value is 100.

  Returns:
    The same message passed as argument.

  Raises::
    ParseError: On JSON parsing problems.
  """
  if not isinstance(text, str):
    text = text.decode('utf-8')
  try:
    js = json.loads(text, object_pairs_hook=_DuplicateChecker)
  except ValueError as e:
    raise ParseError('Failed to load JSON: {0}.'.format(str(e))) from e
  return ParseDict(js, message, ignore_unknown_fields, descriptor_pool,
                   max_recursion_depth)


def ParseDict(js_dict,
              message,
              ignore_unknown_fields=False,
              descriptor_pool=None,
              max_recursion_depth=100):
  """Parses a JSON dictionary representation into a message.

  Args:
    js_dict: Dict representation of a JSON message.
    message: A protocol buffer message to merge into.
    ignore_unknown_fields: If True, do not raise errors for unknown fields.
    descriptor_pool: A Descriptor Pool for resolving types. If None use the
      default.
    max_recursion_depth: max recursion depth of JSON message to be
      deserialized. JSON messages over this depth will fail to be
      deserialized. Default value is 100.

  Returns:
    The same message passed as argument.
  """
  parser = _Parser(ignore_unknown_fields, descriptor_pool, max_recursion_depth)
  parser.ConvertMessage(js_dict, message, '')
  return message


_INT_OR_FLOAT = (int, float)


class _Parser(object):
  """JSON format parser for protocol message."""

  def __init__(self, ignore_unknown_fields, descriptor_pool,
               max_recursion_depth):
    self.ignore_unknown_fields = ignore_unknown_fields
    self.descriptor_pool = descriptor_pool
    self.max_recursion_depth = max_recursion_depth
    self.recursion_depth = 0

  def ConvertMessage(self, value, message, path):
    """Convert a JSON object into a message.

    Args:
      value: A JSON object.
      message: A WKT or regular protocol message to record the data.
      path: parent path to log parse error info.

    Raises:
      ParseError: In case of convert problems.
    """
    self.recursion_depth += 1
    if self.recursion_depth > self.max_recursion_depth:
      raise ParseError('Message too deep. Max recursion depth is {0}'.format(
          self.max_recursion_depth))
    message_descriptor = message.DESCRIPTOR
    full_name = message_descriptor.full_name
    if not path:
      path = message_descriptor.name
    if _IsWrapperMessage(message_descriptor):
      self._ConvertWrapperMessage(value, message, path)
    elif full_name in _WKTJSONMETHODS:
      methodcaller(_WKTJSONMETHODS[full_name][1], value, message, path)(self)
    else:
      self._ConvertFieldValuePair(value, message, path)
    self.recursion_depth -= 1

  def _ConvertFieldValuePair(self, js, message, path):
    """Convert field value pairs into regular message.

    Args:
      js: A JSON object to convert the field value pairs.
      message: A regular protocol message to record the data.
      path: parent path to log parse error info.

    Raises:
      ParseError: In case of problems converting.
    """
    names = []
    message_descriptor = message.DESCRIPTOR
    fields_by_json_name = dict((f.json_name, f)
                               for f in message_descriptor.fields)
    for name in js:
      try:
        field = fields_by_json_name.get(name, None)
        if not field:
          field = message_descriptor.fields_by_name.get(name, None)
        if not field and _VALID_EXTENSION_NAME.match(name):
          if not message_descriptor.is_extendable:
            raise ParseError(
                'Message type {0} does not have extensions at {1}'.format(
                    message_descriptor.full_name, path))
          identifier = name[1:-1]  # strip [] brackets
          # pylint: disable=protected-access
          field = message.Extensions._FindExtensionByName(identifier)
          # pylint: enable=protected-access
          if not field:
            # Try looking for extension by the message type name, dropping the
            # field name following the final . separator in full_name.
            identifier = '.'.join(identifier.split('.')[:-1])
            # pylint: disable=protected-access
            field = message.Extensions._FindExtensionByName(identifier)
            # pylint: enable=protected-access
        if not field:
          if self.ignore_unknown_fields:
            continue
          raise ParseError(
              ('Message type "{0}" has no field named "{1}" at "{2}".\n'
               ' Available Fields(except extensions): "{3}"').format(
                   message_descriptor.full_name, name, path,
                   [f.json_name for f in message_descriptor.fields]))
        if name in names:
          raise ParseError('Message type "{0}" should not have multiple '
                           '"{1}" fields at "{2}".'.format(
                               message.DESCRIPTOR.full_name, name, path))
        names.append(name)
        value = js[name]
        # Check no other oneof field is parsed.
        if field.containing_oneof is not None and value is not None:
          oneof_name = field.containing_oneof.name
          if oneof_name in names:
            raise ParseError('Message type "{0}" should not have multiple '
                             '"{1}" oneof fields at "{2}".'.format(
                                 message.DESCRIPTOR.full_name, oneof_name,
                                 path))
          names.append(oneof_name)

        if value is None:
          if (field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_MESSAGE
              and field.message_type.full_name == 'google.protobuf.Value'):
            sub_message = getattr(message, field.name)
            sub_message.null_value = 0
          elif (field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_ENUM
                and field.enum_type.full_name == 'google.protobuf.NullValue'):
            setattr(message, field.name, 0)
          else:
            message.ClearField(field.name)
          continue

        # Parse field value.
        if _IsMapEntry(field):
          message.ClearField(field.name)
          self._ConvertMapFieldValue(value, message, field,
                                     '{0}.{1}'.format(path, name))
        elif field.label == descriptor.FieldDescriptor.LABEL_REPEATED:
          message.ClearField(field.name)
          if not isinstance(value, list):
            raise ParseError('repeated field {0} must be in [] which is '
                             '{1} at {2}'.format(name, value, path))
          if field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_MESSAGE:
            # Repeated message field.
            for index, item in enumerate(value):
              sub_message = getattr(message, field.name).add()
              # None is a null_value in Value.
              if (item is None and
                  sub_message.DESCRIPTOR.full_name != 'google.protobuf.Value'):
                raise ParseError('null is not allowed to be used as an element'
                                 ' in a repeated field at {0}.{1}[{2}]'.format(
                                     path, name, index))
              self.ConvertMessage(item, sub_message,
                                  '{0}.{1}[{2}]'.format(path, name, index))
          else:
            # Repeated scalar field.
            for index, item in enumerate(value):
              if item is None:
                raise ParseError('null is not allowed to be used as an element'
                                 ' in a repeated field at {0}.{1}[{2}]'.format(
                                     path, name, index))
              getattr(message, field.name).append(
                  _ConvertScalarFieldValue(
                      item, field, '{0}.{1}[{2}]'.format(path, name, index)))
        elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_MESSAGE:
          if field.is_extension:
            sub_message = message.Extensions[field]
          else:
            sub_message = getattr(message, field.name)
          sub_message.SetInParent()
          self.ConvertMessage(value, sub_message, '{0}.{1}'.format(path, name))
        else:
          if field.is_extension:
            message.Extensions[field] = _ConvertScalarFieldValue(
                value, field, '{0}.{1}'.format(path, name))
          else:
            setattr(
                message, field.name,
                _ConvertScalarFieldValue(value, field,
                                         '{0}.{1}'.format(path, name)))
      except ParseError as e:
        if field and field.containing_oneof is None:
          raise ParseError(
            'Failed to parse {0} field: {1}.'.format(name, e)
          ) from e
        else:
          raise ParseError(str(e)) from e
      except ValueError as e:
        raise ParseError(
          'Failed to parse {0} field: {1}.'.format(name, e)
        ) from e
      except TypeError as e:
        raise ParseError(
          'Failed to parse {0} field: {1}.'.format(name, e)
        ) from e

  def _ConvertAnyMessage(self, value, message, path):
    """Convert a JSON representation into Any message."""
    if isinstance(value, dict) and not value:
      return
    try:
      type_url = value['@type']
    except KeyError as e:
      raise ParseError(
        '@type is missing when parsing any message at {0}'.format(path)
      ) from e

    try:
      sub_message = _CreateMessageFromTypeUrl(type_url, self.descriptor_pool)
    except TypeError as e:
      raise ParseError('{0} at {1}'.format(e, path)) from e
    message_descriptor = sub_message.DESCRIPTOR
    full_name = message_descriptor.full_name
    if _IsWrapperMessage(message_descriptor):
      self._ConvertWrapperMessage(value['value'], sub_message,
                                  '{0}.value'.format(path))
    elif full_name in _WKTJSONMETHODS:
      methodcaller(_WKTJSONMETHODS[full_name][1], value['value'], sub_message,
                   '{0}.value'.format(path))(
                       self)
    else:
      del value['@type']
      self._ConvertFieldValuePair(value, sub_message, path)
      value['@type'] = type_url
    # Sets Any message
    message.value = sub_message.SerializeToString()
    message.type_url = type_url

  def _ConvertGenericMessage(self, value, message, path):
    """Convert a JSON representation into message with FromJsonString."""
    # Duration, Timestamp, FieldMask have a FromJsonString method to do the
    # conversion. Users can also call the method directly.
    try:
      message.FromJsonString(value)
    except ValueError as e:
      raise ParseError('{0} at {1}'.format(e, path)) from e

  def _ConvertValueMessage(self, value, message, path):
    """Convert a JSON representation into Value message."""
    if isinstance(value, dict):
      self._ConvertStructMessage(value, message.struct_value, path)
    elif isinstance(value, list):
      self._ConvertListValueMessage(value, message.list_value, path)
    elif value is None:
      message.null_value = 0
    elif isinstance(value, bool):
      message.bool_value = value
    elif isinstance(value, str):
      message.string_value = value
    elif isinstance(value, _INT_OR_FLOAT):
      message.number_value = value
    else:
      raise ParseError('Value {0} has unexpected type {1} at {2}'.format(
          value, type(value), path))

  def _ConvertListValueMessage(self, value, message, path):
    """Convert a JSON representation into ListValue message."""
    if not isinstance(value, list):
      raise ParseError('ListValue must be in [] which is {0} at {1}'.format(
          value, path))
    message.ClearField('values')
    for index, item in enumerate(value):
      self._ConvertValueMessage(item, message.values.add(),
                                '{0}[{1}]'.format(path, index))

  def _ConvertStructMessage(self, value, message, path):
    """Convert a JSON representation into Struct message."""
    if not isinstance(value, dict):
      raise ParseError('Struct must be in a dict which is {0} at {1}'.format(
          value, path))
    # Clear will mark the struct as modified so it will be created even if
    # there are no values.
    message.Clear()
    for key in value:
      self._ConvertValueMessage(value[key], message.fields[key],
                                '{0}.{1}'.format(path, key))
    return

  def _ConvertWrapperMessage(self, value, message, path):
    """Convert a JSON representation into Wrapper message."""
    field = message.DESCRIPTOR.fields_by_name['value']
    setattr(
        message, 'value',
        _ConvertScalarFieldValue(value, field, path='{0}.value'.format(path)))

  def _ConvertMapFieldValue(self, value, message, field, path):
    """Convert map field value for a message map field.

    Args:
      value: A JSON object to convert the map field value.
      message: A protocol message to record the converted data.
      field: The descriptor of the map field to be converted.
      path: parent path to log parse error info.

    Raises:
      ParseError: In case of convert problems.
    """
    if not isinstance(value, dict):
      raise ParseError(
          'Map field {0} must be in a dict which is {1} at {2}'.format(
              field.name, value, path))
    key_field = field.message_type.fields_by_name['key']
    value_field = field.message_type.fields_by_name['value']
    for key in value:
      key_value = _ConvertScalarFieldValue(key, key_field,
                                           '{0}.key'.format(path), True)
      if value_field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_MESSAGE:
        self.ConvertMessage(value[key],
                            getattr(message, field.name)[key_value],
                            '{0}[{1}]'.format(path, key_value))
      else:
        getattr(message, field.name)[key_value] = _ConvertScalarFieldValue(
            value[key], value_field, path='{0}[{1}]'.format(path, key_value))


def _ConvertScalarFieldValue(value, field, path, require_str=False):
  """Convert a single scalar field value.

  Args:
    value: A scalar value to convert the scalar field value.
    field: The descriptor of the field to convert.
    path: parent path to log parse error info.
    require_str: If True, the field value must be a str.

  Returns:
    The converted scalar field value

  Raises:
    ParseError: In case of convert problems.
  """
  try:
    if field.cpp_type in _INT_TYPES:
      return _ConvertInteger(value)
    elif field.cpp_type in _FLOAT_TYPES:
      return _ConvertFloat(value, field)
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_BOOL:
      return _ConvertBool(value, require_str)
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_STRING:
      if field.type == descriptor.FieldDescriptor.TYPE_BYTES:
        if isinstance(value, str):
          encoded = value.encode('utf-8')
        else:
          encoded = value
        # Add extra padding '='
        padded_value = encoded + b'=' * (4 - len(encoded) % 4)
        return base64.urlsafe_b64decode(padded_value)
      else:
        # Checking for unpaired surrogates appears to be unreliable,
        # depending on the specific Python version, so we check manually.
        if _UNPAIRED_SURROGATE_PATTERN.search(value):
          raise ParseError('Unpaired surrogate')
        return value
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_ENUM:
      # Convert an enum value.
      enum_value = field.enum_type.values_by_name.get(value, None)
      if enum_value is None:
        try:
          number = int(value)
          enum_value = field.enum_type.values_by_number.get(number, None)
        except ValueError as e:
          raise ParseError('Invalid enum value {0} for enum type {1}'.format(
              value, field.enum_type.full_name)) from e
        if enum_value is None:
          if field.enum_type.is_closed:
            raise ParseError('Invalid enum value {0} for enum type {1}'.format(
                value, field.enum_type.full_name))
          else:
            return number
      return enum_value.number
  except ParseError as e:
    raise ParseError('{0} at {1}'.format(e, path)) from e


def _ConvertInteger(value):
  """Convert an integer.

  Args:
    value: A scalar value to convert.

  Returns:
    The integer value.

  Raises:
    ParseError: If an integer couldn't be consumed.
  """
  if isinstance(value, float) and not value.is_integer():
    raise ParseError('Couldn\'t parse integer: {0}'.format(value))

  if isinstance(value, str) and value.find(' ') != -1:
    raise ParseError('Couldn\'t parse integer: "{0}"'.format(value))

  if isinstance(value, bool):
    raise ParseError('Bool value {0} is not acceptable for '
                     'integer field'.format(value))

  return int(value)


def _ConvertFloat(value, field):
  """Convert an floating point number."""
  if isinstance(value, float):
    if math.isnan(value):
      raise ParseError('Couldn\'t parse NaN, use quoted "NaN" instead')
    if math.isinf(value):
      if value > 0:
        raise ParseError('Couldn\'t parse Infinity or value too large, '
                         'use quoted "Infinity" instead')
      else:
        raise ParseError('Couldn\'t parse -Infinity or value too small, '
                         'use quoted "-Infinity" instead')
    if field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_FLOAT:
      # pylint: disable=protected-access
      if value > type_checkers._FLOAT_MAX:
        raise ParseError('Float value too large')
      # pylint: disable=protected-access
      if value < type_checkers._FLOAT_MIN:
        raise ParseError('Float value too small')
  if value == 'nan':
    raise ParseError('Couldn\'t parse float "nan", use "NaN" instead')
  try:
    # Assume Python compatible syntax.
    return float(value)
  except ValueError as e:
    # Check alternative spellings.
    if value == _NEG_INFINITY:
      return float('-inf')
    elif value == _INFINITY:
      return float('inf')
    elif value == _NAN:
      return float('nan')
    else:
      raise ParseError('Couldn\'t parse float: {0}'.format(value)) from e


def _ConvertBool(value, require_str):
  """Convert a boolean value.

  Args:
    value: A scalar value to convert.
    require_str: If True, value must be a str.

  Returns:
    The bool parsed.

  Raises:
    ParseError: If a boolean value couldn't be consumed.
  """
  if require_str:
    if value == 'true':
      return True
    elif value == 'false':
      return False
    else:
      raise ParseError('Expected "true" or "false", not {0}'.format(value))

  if not isinstance(value, bool):
    raise ParseError('Expected true or false without quotes')
  return value

_WKTJSONMETHODS = {
    'google.protobuf.Any': ['_AnyMessageToJsonObject',
                            '_ConvertAnyMessage'],
    'google.protobuf.Duration': ['_GenericMessageToJsonObject',
                                 '_ConvertGenericMessage'],
    'google.protobuf.FieldMask': ['_GenericMessageToJsonObject',
                                  '_ConvertGenericMessage'],
    'google.protobuf.ListValue': ['_ListValueMessageToJsonObject',
                                  '_ConvertListValueMessage'],
    'google.protobuf.Struct': ['_StructMessageToJsonObject',
                               '_ConvertStructMessage'],
    'google.protobuf.Timestamp': ['_GenericMessageToJsonObject',
                                  '_ConvertGenericMessage'],
    'google.protobuf.Value': ['_ValueMessageToJsonObject',
                              '_ConvertValueMessage']
}

# === NexusCore/openenv\Lib\site-packages\jedi\inference\syntax_tree.py ===
"""
Functions inferring the syntax tree.
"""
import copy
import itertools

from parso.python import tree

from jedi import debug
from jedi import parser_utils
from jedi.inference.base_value import ValueSet, NO_VALUES, ContextualizedNode, \
    iterator_to_value_set, iterate_values
from jedi.inference.lazy_value import LazyTreeValue
from jedi.inference import compiled
from jedi.inference import recursion
from jedi.inference import analysis
from jedi.inference import imports
from jedi.inference import arguments
from jedi.inference.value import ClassValue, FunctionValue
from jedi.inference.value import iterable
from jedi.inference.value.dynamic_arrays import ListModification, DictModification
from jedi.inference.value import TreeInstance
from jedi.inference.helpers import is_string, is_literal, is_number, \
    get_names_of_node, is_big_annoying_library
from jedi.inference.compiled.access import COMPARISON_OPERATORS
from jedi.inference.cache import inference_state_method_cache
from jedi.inference.gradual.stub_value import VersionInfo
from jedi.inference.gradual import annotation
from jedi.inference.names import TreeNameDefinition
from jedi.inference.context import CompForContext
from jedi.inference.value.decorator import Decoratee
from jedi.plugins import plugin_manager

operator_to_magic_method = {
    '+': '__add__',
    '-': '__sub__',
    '*': '__mul__',
    '@': '__matmul__',
    '/': '__truediv__',
    '//': '__floordiv__',
    '%': '__mod__',
    '**': '__pow__',
    '<<': '__lshift__',
    '>>': '__rshift__',
    '&': '__and__',
    '|': '__or__',
    '^': '__xor__',
}

reverse_operator_to_magic_method = {
    k: '__r' + v[2:] for k, v in operator_to_magic_method.items()
}


def _limit_value_infers(func):
    """
    This is for now the way how we limit type inference going wild. There are
    other ways to ensure recursion limits as well. This is mostly necessary
    because of instance (self) access that can be quite tricky to limit.

    I'm still not sure this is the way to go, but it looks okay for now and we
    can still go anther way in the future. Tests are there. ~ dave
    """
    def wrapper(context, *args, **kwargs):
        n = context.tree_node
        inference_state = context.inference_state
        try:
            inference_state.inferred_element_counts[n] += 1
            maximum = 300
            if context.parent_context is None \
                    and context.get_value() is inference_state.builtins_module:
                # Builtins should have a more generous inference limit.
                # It is important that builtins can be executed, otherwise some
                # functions that depend on certain builtins features would be
                # broken, see e.g. GH #1432
                maximum *= 100

            if inference_state.inferred_element_counts[n] > maximum:
                debug.warning('In value %s there were too many inferences.', n)
                return NO_VALUES
        except KeyError:
            inference_state.inferred_element_counts[n] = 1
        return func(context, *args, **kwargs)

    return wrapper


def infer_node(context, element):
    if isinstance(context, CompForContext):
        return _infer_node(context, element)

    if_stmt = element
    while if_stmt is not None:
        if_stmt = if_stmt.parent
        if if_stmt.type in ('if_stmt', 'for_stmt'):
            break
        if parser_utils.is_scope(if_stmt):
            if_stmt = None
            break
    predefined_if_name_dict = context.predefined_names.get(if_stmt)
    # TODO there's a lot of issues with this one. We actually should do
    # this in a different way. Caching should only be active in certain
    # cases and this all sucks.
    if predefined_if_name_dict is None and if_stmt \
            and if_stmt.type == 'if_stmt' and context.inference_state.is_analysis:
        if_stmt_test = if_stmt.children[1]
        name_dicts = [{}]
        # If we already did a check, we don't want to do it again -> If
        # value.predefined_names is filled, we stop.
        # We don't want to check the if stmt itself, it's just about
        # the content.
        if element.start_pos > if_stmt_test.end_pos:
            # Now we need to check if the names in the if_stmt match the
            # names in the suite.
            if_names = get_names_of_node(if_stmt_test)
            element_names = get_names_of_node(element)
            str_element_names = [e.value for e in element_names]
            if any(i.value in str_element_names for i in if_names):
                for if_name in if_names:
                    definitions = context.inference_state.infer(context, if_name)
                    # Every name that has multiple different definitions
                    # causes the complexity to rise. The complexity should
                    # never fall below 1.
                    if len(definitions) > 1:
                        if len(name_dicts) * len(definitions) > 16:
                            debug.dbg('Too many options for if branch inference %s.', if_stmt)
                            # There's only a certain amount of branches
                            # Jedi can infer, otherwise it will take to
                            # long.
                            name_dicts = [{}]
                            break

                        original_name_dicts = list(name_dicts)
                        name_dicts = []
                        for definition in definitions:
                            new_name_dicts = list(original_name_dicts)
                            for i, name_dict in enumerate(new_name_dicts):
                                new_name_dicts[i] = name_dict.copy()
                                new_name_dicts[i][if_name.value] = ValueSet([definition])

                            name_dicts += new_name_dicts
                    else:
                        for name_dict in name_dicts:
                            name_dict[if_name.value] = definitions
        if len(name_dicts) > 1:
            result = NO_VALUES
            for name_dict in name_dicts:
                with context.predefine_names(if_stmt, name_dict):
                    result |= _infer_node(context, element)
            return result
        else:
            return _infer_node_if_inferred(context, element)
    else:
        if predefined_if_name_dict:
            return _infer_node(context, element)
        else:
            return _infer_node_if_inferred(context, element)


def _infer_node_if_inferred(context, element):
    """
    TODO This function is temporary: Merge with infer_node.
    """
    parent = element
    while parent is not None:
        parent = parent.parent
        predefined_if_name_dict = context.predefined_names.get(parent)
        if predefined_if_name_dict is not None:
            return _infer_node(context, element)
    return _infer_node_cached(context, element)


@inference_state_method_cache(default=NO_VALUES)
def _infer_node_cached(context, element):
    return _infer_node(context, element)


@debug.increase_indent
@_limit_value_infers
def _infer_node(context, element):
    debug.dbg('infer_node %s@%s in %s', element, element.start_pos, context)
    inference_state = context.inference_state
    typ = element.type
    if typ in ('name', 'number', 'string', 'atom', 'strings', 'keyword', 'fstring'):
        return infer_atom(context, element)
    elif typ == 'lambdef':
        return ValueSet([FunctionValue.from_context(context, element)])
    elif typ == 'expr_stmt':
        return infer_expr_stmt(context, element)
    elif typ in ('power', 'atom_expr'):
        first_child = element.children[0]
        children = element.children[1:]
        had_await = False
        if first_child.type == 'keyword' and first_child.value == 'await':
            had_await = True
            first_child = children.pop(0)

        value_set = context.infer_node(first_child)
        for (i, trailer) in enumerate(children):
            if trailer == '**':  # has a power operation.
                right = context.infer_node(children[i + 1])
                value_set = _infer_comparison(
                    context,
                    value_set,
                    trailer,
                    right
                )
                break
            value_set = infer_trailer(context, value_set, trailer)

        if had_await:
            return value_set.py__await__().py__stop_iteration_returns()
        return value_set
    elif typ in ('testlist_star_expr', 'testlist',):
        # The implicit tuple in statements.
        return ValueSet([iterable.SequenceLiteralValue(inference_state, context, element)])
    elif typ in ('not_test', 'factor'):
        value_set = context.infer_node(element.children[-1])
        for operator in element.children[:-1]:
            value_set = infer_factor(value_set, operator)
        return value_set
    elif typ == 'test':
        # `x if foo else y` case.
        return (context.infer_node(element.children[0])
                | context.infer_node(element.children[-1]))
    elif typ == 'operator':
        # Must be an ellipsis, other operators are not inferred.
        if element.value != '...':
            origin = element.parent
            raise AssertionError("unhandled operator %s in %s " % (repr(element.value), origin))
        return ValueSet([compiled.builtin_from_name(inference_state, 'Ellipsis')])
    elif typ == 'dotted_name':
        value_set = infer_atom(context, element.children[0])
        for next_name in element.children[2::2]:
            value_set = value_set.py__getattribute__(next_name, name_context=context)
        return value_set
    elif typ == 'eval_input':
        return context.infer_node(element.children[0])
    elif typ == 'annassign':
        return annotation.infer_annotation(context, element.children[1]) \
            .execute_annotation()
    elif typ == 'yield_expr':
        if len(element.children) and element.children[1].type == 'yield_arg':
            # Implies that it's a yield from.
            element = element.children[1].children[1]
            generators = context.infer_node(element) \
                .py__getattribute__('__iter__').execute_with_values()
            return generators.py__stop_iteration_returns()

        # Generator.send() is not implemented.
        return NO_VALUES
    elif typ == 'namedexpr_test':
        return context.infer_node(element.children[2])
    else:
        return infer_or_test(context, element)


def infer_trailer(context, atom_values, trailer):
    trailer_op, node = trailer.children[:2]
    if node == ')':  # `arglist` is optional.
        node = None

    if trailer_op == '[':
        trailer_op, node, _ = trailer.children
        return atom_values.get_item(
            _infer_subscript_list(context, node),
            ContextualizedNode(context, trailer)
        )
    else:
        debug.dbg('infer_trailer: %s in %s', trailer, atom_values)
        if trailer_op == '.':
            return atom_values.py__getattribute__(
                name_context=context,
                name_or_str=node
            )
        else:
            assert trailer_op == '(', 'trailer_op is actually %s' % trailer_op
            args = arguments.TreeArguments(context.inference_state, context, node, trailer)
            return atom_values.execute(args)


def infer_atom(context, atom):
    """
    Basically to process ``atom`` nodes. The parser sometimes doesn't
    generate the node (because it has just one child). In that case an atom
    might be a name or a literal as well.
    """
    state = context.inference_state
    if atom.type == 'name':
        # This is the first global lookup.
        stmt = tree.search_ancestor(atom, 'expr_stmt', 'lambdef', 'if_stmt') or atom
        if stmt.type == 'if_stmt':
            if not any(n.start_pos <= atom.start_pos < n.end_pos for n in stmt.get_test_nodes()):
                stmt = atom
        elif stmt.type == 'lambdef':
            stmt = atom
        position = stmt.start_pos
        if _is_annotation_name(atom):
            # Since Python 3.7 (with from __future__ import annotations),
            # annotations are essentially strings and can reference objects
            # that are defined further down in code. Therefore just set the
            # position to None, so the finder will not try to stop at a certain
            # position in the module.
            position = None
        return context.py__getattribute__(atom, position=position)
    elif atom.type == 'keyword':
        # For False/True/None
        if atom.value in ('False', 'True', 'None'):
            return ValueSet([compiled.builtin_from_name(state, atom.value)])
        elif atom.value == 'yield':
            # Contrary to yield from, yield can just appear alone to return a
            # value when used with `.send()`.
            return NO_VALUES
        assert False, 'Cannot infer the keyword %s' % atom

    elif isinstance(atom, tree.Literal):
        string = state.compiled_subprocess.safe_literal_eval(atom.value)
        return ValueSet([compiled.create_simple_object(state, string)])
    elif atom.type == 'strings':
        # Will be multiple string.
        value_set = infer_atom(context, atom.children[0])
        for string in atom.children[1:]:
            right = infer_atom(context, string)
            value_set = _infer_comparison(context, value_set, '+', right)
        return value_set
    elif atom.type == 'fstring':
        return compiled.get_string_value_set(state)
    else:
        c = atom.children
        # Parentheses without commas are not tuples.
        if c[0] == '(' and not len(c) == 2 \
                and not (c[1].type == 'testlist_comp'
                         and len(c[1].children) > 1):
            return context.infer_node(c[1])

        try:
            comp_for = c[1].children[1]
        except (IndexError, AttributeError):
            pass
        else:
            if comp_for == ':':
                # Dict comprehensions have a colon at the 3rd index.
                try:
                    comp_for = c[1].children[3]
                except IndexError:
                    pass

            if comp_for.type in ('comp_for', 'sync_comp_for'):
                return ValueSet([iterable.comprehension_from_atom(
                    state, context, atom
                )])

        # It's a dict/list/tuple literal.
        array_node = c[1]
        try:
            array_node_c = array_node.children
        except AttributeError:
            array_node_c = []
        if c[0] == '{' and (array_node == '}' or ':' in array_node_c
                            or '**' in array_node_c):
            new_value = iterable.DictLiteralValue(state, context, atom)
        else:
            new_value = iterable.SequenceLiteralValue(state, context, atom)
        return ValueSet([new_value])


@_limit_value_infers
def infer_expr_stmt(context, stmt, seek_name=None):
    with recursion.execution_allowed(context.inference_state, stmt) as allowed:
        if allowed:
            if seek_name is not None:
                pep0484_values = \
                    annotation.find_type_from_comment_hint_assign(context, stmt, seek_name)
                if pep0484_values:
                    return pep0484_values

            return _infer_expr_stmt(context, stmt, seek_name)
    return NO_VALUES


@debug.increase_indent
def _infer_expr_stmt(context, stmt, seek_name=None):
    """
    The starting point of the completion. A statement always owns a call
    list, which are the calls, that a statement does. In case multiple
    names are defined in the statement, `seek_name` returns the result for
    this name.

    expr_stmt: testlist_star_expr (annassign | augassign (yield_expr|testlist) |
                     ('=' (yield_expr|testlist_star_expr))*)
    annassign: ':' test ['=' test]
    augassign: ('+=' | '-=' | '*=' | '@=' | '/=' | '%=' | '&=' | '|=' | '^=' |
                '<<=' | '>>=' | '**=' | '//=')

    :param stmt: A `tree.ExprStmt`.
    """
    def check_setitem(stmt):
        atom_expr = stmt.children[0]
        if atom_expr.type not in ('atom_expr', 'power'):
            return False, None
        name = atom_expr.children[0]
        if name.type != 'name' or len(atom_expr.children) != 2:
            return False, None
        trailer = atom_expr.children[-1]
        return trailer.children[0] == '[', trailer.children[1]

    debug.dbg('infer_expr_stmt %s (%s)', stmt, seek_name)
    rhs = stmt.get_rhs()

    value_set = context.infer_node(rhs)

    if seek_name:
        n = TreeNameDefinition(context, seek_name)
        value_set = check_tuple_assignments(n, value_set)

    first_operator = next(stmt.yield_operators(), None)
    is_setitem, subscriptlist = check_setitem(stmt)
    is_annassign = first_operator not in ('=', None) and first_operator.type == 'operator'
    if is_annassign or is_setitem:
        # `=` is always the last character in aug assignments -> -1
        name = stmt.get_defined_names(include_setitem=True)[0].value
        left_values = context.py__getattribute__(name, position=stmt.start_pos)

        if is_setitem:
            def to_mod(v):
                c = ContextualizedSubscriptListNode(context, subscriptlist)
                if v.array_type == 'dict':
                    return DictModification(v, value_set, c)
                elif v.array_type == 'list':
                    return ListModification(v, value_set, c)
                return v

            value_set = ValueSet(to_mod(v) for v in left_values)
        else:
            operator = copy.copy(first_operator)
            operator.value = operator.value[:-1]
            for_stmt = tree.search_ancestor(stmt, 'for_stmt')
            if for_stmt is not None and for_stmt.type == 'for_stmt' and value_set \
                    and parser_utils.for_stmt_defines_one_name(for_stmt):
                # Iterate through result and add the values, that's possible
                # only in for loops without clutter, because they are
                # predictable. Also only do it, if the variable is not a tuple.
                node = for_stmt.get_testlist()
                cn = ContextualizedNode(context, node)
                ordered = list(cn.infer().iterate(cn))

                for lazy_value in ordered:
                    dct = {for_stmt.children[1].value: lazy_value.infer()}
                    with context.predefine_names(for_stmt, dct):
                        t = context.infer_node(rhs)
                        left_values = _infer_comparison(context, left_values, operator, t)
                value_set = left_values
            else:
                value_set = _infer_comparison(context, left_values, operator, value_set)
    debug.dbg('infer_expr_stmt result %s', value_set)
    return value_set


def infer_or_test(context, or_test):
    iterator = iter(or_test.children)
    types = context.infer_node(next(iterator))
    for operator in iterator:
        right = next(iterator)
        if operator.type == 'comp_op':  # not in / is not
            operator = ' '.join(c.value for c in operator.children)

        # handle type inference of and/or here.
        if operator in ('and', 'or'):
            left_bools = set(left.py__bool__() for left in types)
            if left_bools == {True}:
                if operator == 'and':
                    types = context.infer_node(right)
            elif left_bools == {False}:
                if operator != 'and':
                    types = context.infer_node(right)
            # Otherwise continue, because of uncertainty.
        else:
            types = _infer_comparison(context, types, operator,
                                      context.infer_node(right))
    debug.dbg('infer_or_test types %s', types)
    return types


@iterator_to_value_set
def infer_factor(value_set, operator):
    """
    Calculates `+`, `-`, `~` and `not` prefixes.
    """
    for value in value_set:
        if operator == '-':
            if is_number(value):
                yield value.negate()
        elif operator == 'not':
            b = value.py__bool__()
            if b is None:  # Uncertainty.
                yield list(value.inference_state.builtins_module.py__getattribute__('bool')
                           .execute_annotation()).pop()
            else:
                yield compiled.create_simple_object(value.inference_state, not b)
        else:
            yield value


def _literals_to_types(inference_state, result):
    # Changes literals ('a', 1, 1.0, etc) to its type instances (str(),
    # int(), float(), etc).
    new_result = NO_VALUES
    for typ in result:
        if is_literal(typ):
            # Literals are only valid as long as the operations are
            # correct. Otherwise add a value-free instance.
            cls = compiled.builtin_from_name(inference_state, typ.name.string_name)
            new_result |= cls.execute_with_values()
        else:
            new_result |= ValueSet([typ])
    return new_result


def _infer_comparison(context, left_values, operator, right_values):
    state = context.inference_state
    if isinstance(operator, str):
        operator_str = operator
    else:
        operator_str = str(operator.value)
    if not left_values or not right_values:
        # illegal slices e.g. cause left/right_result to be None
        result = (left_values or NO_VALUES) | (right_values or NO_VALUES)
        return _literals_to_types(state, result)
    elif operator_str == "|" and all(
        value.is_class() or value.is_compiled()
        for value in itertools.chain(left_values, right_values)
    ):
        # ^^^ A naive hack for PEP 604
        return ValueSet.from_sets((left_values, right_values))
    else:
        # I don't think there's a reasonable chance that a string
        # operation is still correct, once we pass something like six
        # objects.
        if len(left_values) * len(right_values) > 6:
            return _literals_to_types(state, left_values | right_values)
        else:
            return ValueSet.from_sets(
                _infer_comparison_part(state, context, left, operator, right)
                for left in left_values
                for right in right_values
            )


def _is_annotation_name(name):
    ancestor = tree.search_ancestor(name, 'param', 'funcdef', 'expr_stmt')
    if ancestor is None:
        return False

    if ancestor.type in ('param', 'funcdef'):
        ann = ancestor.annotation
        if ann is not None:
            return ann.start_pos <= name.start_pos < ann.end_pos
    elif ancestor.type == 'expr_stmt':
        c = ancestor.children
        if len(c) > 1 and c[1].type == 'annassign':
            return c[1].start_pos <= name.start_pos < c[1].end_pos
    return False


def _is_list(value):
    return value.array_type == 'list'


def _is_tuple(value):
    return value.array_type == 'tuple'


def _bool_to_value(inference_state, bool_):
    return compiled.builtin_from_name(inference_state, str(bool_))


def _get_tuple_ints(value):
    if not isinstance(value, iterable.SequenceLiteralValue):
        return None
    numbers = []
    for lazy_value in value.py__iter__():
        if not isinstance(lazy_value, LazyTreeValue):
            return None
        node = lazy_value.data
        if node.type != 'number':
            return None
        try:
            numbers.append(int(node.value))
        except ValueError:
            return None
    return numbers


def _infer_comparison_part(inference_state, context, left, operator, right):
    l_is_num = is_number(left)
    r_is_num = is_number(right)
    if isinstance(operator, str):
        str_operator = operator
    else:
        str_operator = str(operator.value)

    if str_operator == '*':
        # for iterables, ignore * operations
        if isinstance(left, iterable.Sequence) or is_string(left):
            return ValueSet([left])
        elif isinstance(right, iterable.Sequence) or is_string(right):
            return ValueSet([right])
    elif str_operator == '+':
        if l_is_num and r_is_num or is_string(left) and is_string(right):
            return left.execute_operation(right, str_operator)
        elif _is_list(left) and _is_list(right) or _is_tuple(left) and _is_tuple(right):
            return ValueSet([iterable.MergedArray(inference_state, (left, right))])
    elif str_operator == '-':
        if l_is_num and r_is_num:
            return left.execute_operation(right, str_operator)
    elif str_operator == '%':
        # With strings and numbers the left type typically remains. Except for
        # `int() % float()`.
        return ValueSet([left])
    elif str_operator in COMPARISON_OPERATORS:
        if left.is_compiled() and right.is_compiled():
            # Possible, because the return is not an option. Just compare.
            result = left.execute_operation(right, str_operator)
            if result:
                return result
        else:
            if str_operator in ('is', '!=', '==', 'is not'):
                operation = COMPARISON_OPERATORS[str_operator]
                bool_ = operation(left, right)
                # Only if == returns True or != returns False, we can continue.
                # There's no guarantee that they are not equal. This can help
                # in some cases, but does not cover everything.
                if (str_operator in ('is', '==')) == bool_:
                    return ValueSet([_bool_to_value(inference_state, bool_)])

            if isinstance(left, VersionInfo):
                version_info = _get_tuple_ints(right)
                if version_info is not None:
                    bool_result = compiled.access.COMPARISON_OPERATORS[operator](
                        inference_state.environment.version_info,
                        tuple(version_info)
                    )
                    return ValueSet([_bool_to_value(inference_state, bool_result)])

        return ValueSet([
            _bool_to_value(inference_state, True),
            _bool_to_value(inference_state, False)
        ])
    elif str_operator in ('in', 'not in'):
        return inference_state.builtins_module.py__getattribute__('bool').execute_annotation()

    def check(obj):
        """Checks if a Jedi object is either a float or an int."""
        return isinstance(obj, TreeInstance) and \
            obj.name.string_name in ('int', 'float')

    # Static analysis, one is a number, the other one is not.
    if str_operator in ('+', '-') and l_is_num != r_is_num \
            and not (check(left) or check(right)):
        message = "TypeError: unsupported operand type(s) for +: %s and %s"
        analysis.add(context, 'type-error-operation', operator,
                     message % (left, right))

    if left.is_class() or right.is_class():
        return NO_VALUES

    method_name = operator_to_magic_method[str_operator]
    magic_methods = left.py__getattribute__(method_name)
    if magic_methods:
        result = magic_methods.execute_with_values(right)
        if result:
            return result

    if not magic_methods:
        reverse_method_name = reverse_operator_to_magic_method[str_operator]
        magic_methods = right.py__getattribute__(reverse_method_name)

        result = magic_methods.execute_with_values(left)
        if result:
            return result

    result = ValueSet([left, right])
    debug.dbg('Used operator %s resulting in %s', operator, result)
    return result


@plugin_manager.decorate()
def tree_name_to_values(inference_state, context, tree_name):
    value_set = NO_VALUES
    module_node = context.get_root_context().tree_node
    # First check for annotations, like: `foo: int = 3`
    if module_node is not None:
        names = module_node.get_used_names().get(tree_name.value, [])
        found_annotation = False
        for name in names:
            expr_stmt = name.parent

            if expr_stmt.type == "expr_stmt" and expr_stmt.children[1].type == "annassign":
                correct_scope = parser_utils.get_parent_scope(name) == context.tree_node
                ann_assign = expr_stmt.children[1]
                if correct_scope:
                    found_annotation = True
                    if (
                        (ann_assign.children[1].type == 'name')
                        and (ann_assign.children[1].value == tree_name.value)
                        and context.parent_context
                    ):
                        context = context.parent_context
                    value_set |= annotation.infer_annotation(
                        context, expr_stmt.children[1].children[1]
                    ).execute_annotation()
        if found_annotation:
            return value_set

    types = []
    node = tree_name.get_definition(import_name_always=True, include_setitem=True)
    if node is None:
        node = tree_name.parent
        if node.type == 'global_stmt':
            c = context.create_context(tree_name)
            if c.is_module():
                # In case we are already part of the module, there is no point
                # in looking up the global statement anymore, because it's not
                # valid at that point anyway.
                return NO_VALUES
            # For global_stmt lookups, we only need the first possible scope,
            # which means the function itself.
            filter = next(c.get_filters())
            names = filter.get(tree_name.value)
            return ValueSet.from_sets(name.infer() for name in names)
        elif node.type not in ('import_from', 'import_name'):
            c = context.create_context(tree_name)
            return infer_atom(c, tree_name)

    typ = node.type
    if typ == 'for_stmt':
        types = annotation.find_type_from_comment_hint_for(context, node, tree_name)
        if types:
            return types
    if typ == 'with_stmt':
        types = annotation.find_type_from_comment_hint_with(context, node, tree_name)
        if types:
            return types

    if typ in ('for_stmt', 'comp_for', 'sync_comp_for'):
        try:
            types = context.predefined_names[node][tree_name.value]
        except KeyError:
            cn = ContextualizedNode(context, node.children[3])
            for_types = iterate_values(
                cn.infer(),
                contextualized_node=cn,
                is_async=node.parent.type == 'async_stmt',
            )
            n = TreeNameDefinition(context, tree_name)
            types = check_tuple_assignments(n, for_types)
    elif typ == 'expr_stmt':
        types = infer_expr_stmt(context, node, tree_name)
    elif typ == 'with_stmt':
        value_managers = context.infer_node(node.get_test_node_from_name(tree_name))
        if node.parent.type == 'async_stmt':
            # In the case of `async with` statements, we need to
            # first get the coroutine from the `__aenter__` method,
            # then "unwrap" via the `__await__` method
            enter_methods = value_managers.py__getattribute__('__aenter__')
            coro = enter_methods.execute_with_values()
            return coro.py__await__().py__stop_iteration_returns()
        enter_methods = value_managers.py__getattribute__('__enter__')
        return enter_methods.execute_with_values()
    elif typ in ('import_from', 'import_name'):
        types = imports.infer_import(context, tree_name)
    elif typ in ('funcdef', 'classdef'):
        types = _apply_decorators(context, node)
    elif typ == 'try_stmt':
        # TODO an exception can also be a tuple. Check for those.
        # TODO check for types that are not classes and add it to
        # the static analysis report.
        exceptions = context.infer_node(tree_name.get_previous_sibling().get_previous_sibling())
        types = exceptions.execute_with_values()
    elif typ == 'param':
        types = NO_VALUES
    elif typ == 'del_stmt':
        types = NO_VALUES
    elif typ == 'namedexpr_test':
        types = infer_node(context, node)
    else:
        raise ValueError("Should not happen. type: %s" % typ)
    return types


# We don't want to have functions/classes that are created by the same
# tree_node.
@inference_state_method_cache()
def _apply_decorators(context, node):
    """
    Returns the function, that should to be executed in the end.
    This is also the places where the decorators are processed.
    """
    if node.type == 'classdef':
        decoratee_value = ClassValue(
            context.inference_state,
            parent_context=context,
            tree_node=node
        )
    else:
        decoratee_value = FunctionValue.from_context(context, node)
    initial = values = ValueSet([decoratee_value])

    if is_big_annoying_library(context):
        return values

    for dec in reversed(node.get_decorators()):
        debug.dbg('decorator: %s %s', dec, values, color="MAGENTA")
        with debug.increase_indent_cm():
            dec_values = context.infer_node(dec.children[1])
            trailer_nodes = dec.children[2:-1]
            if trailer_nodes:
                # Create a trailer and infer it.
                trailer = tree.PythonNode('trailer', trailer_nodes)
                trailer.parent = dec
                dec_values = infer_trailer(context, dec_values, trailer)

            if not len(dec_values):
                code = dec.get_code(include_prefix=False)
                # For the short future, we don't want to hear about the runtime
                # decorator in typing that was intentionally omitted. This is not
                # "correct", but helps with debugging.
                if code != '@runtime\n':
                    debug.warning('decorator not found: %s on %s', dec, node)
                return initial

            values = dec_values.execute(arguments.ValuesArguments([values]))
            if not len(values):
                debug.warning('not possible to resolve wrappers found %s', node)
                return initial

        debug.dbg('decorator end %s', values, color="MAGENTA")
    if values != initial:
        return ValueSet([Decoratee(c, decoratee_value) for c in values])
    return values


def check_tuple_assignments(name, value_set):
    """
    Checks if tuples are assigned.
    """
    lazy_value = None
    for index, node in name.assignment_indexes():
        cn = ContextualizedNode(name.parent_context, node)
        iterated = value_set.iterate(cn)
        if isinstance(index, slice):
            # For no star unpacking is not possible.
            return NO_VALUES
        i = 0
        while i <= index:
            try:
                lazy_value = next(iterated)
            except StopIteration:
                # We could do this with the default param in next. But this
                # would allow this loop to run for a very long time if the
                # index number is high. Therefore break if the loop is
                # finished.
                return NO_VALUES
            else:
                i += lazy_value.max
        value_set = lazy_value.infer()
    return value_set


class ContextualizedSubscriptListNode(ContextualizedNode):
    def infer(self):
        return _infer_subscript_list(self.context, self.node)


def _infer_subscript_list(context, index):
    """
    Handles slices in subscript nodes.
    """
    if index == ':':
        # Like array[:]
        return ValueSet([iterable.Slice(context, None, None, None)])

    elif index.type == 'subscript' and not index.children[0] == '.':
        # subscript basically implies a slice operation
        # e.g. array[:3]
        result = []
        for el in index.children:
            if el == ':':
                if not result:
                    result.append(None)
            elif el.type == 'sliceop':
                if len(el.children) == 2:
                    result.append(el.children[1])
            else:
                result.append(el)
        result += [None] * (3 - len(result))

        return ValueSet([iterable.Slice(context, *result)])
    elif index.type == 'subscriptlist':
        return ValueSet([iterable.SequenceLiteralValue(context.inference_state, context, index)])

    # No slices
    return context.infer_node(index)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\shell.py ===
"""
    pygments.lexers.shell
    ~~~~~~~~~~~~~~~~~~~~~

    Lexers for various shells.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer, RegexLexer, do_insertions, bygroups, \
    include, default, this, using, words, line_re
from pygments.token import Punctuation, Whitespace, \
    Text, Comment, Operator, Keyword, Name, String, Number, Generic
from pygments.util import shebang_matches

__all__ = ['BashLexer', 'BashSessionLexer', 'TcshLexer', 'BatchLexer',
           'SlurmBashLexer', 'MSDOSSessionLexer', 'PowerShellLexer',
           'PowerShellSessionLexer', 'TcshSessionLexer', 'FishShellLexer',
           'ExeclineLexer']


class BashLexer(RegexLexer):
    """
    Lexer for (ba|k|z|)sh shell scripts.
    """

    name = 'Bash'
    aliases = ['bash', 'sh', 'ksh', 'zsh', 'shell', 'openrc']
    filenames = ['*.sh', '*.ksh', '*.bash', '*.ebuild', '*.eclass',
                 '*.exheres-0', '*.exlib', '*.zsh',
                 '.bashrc', 'bashrc', '.bash_*', 'bash_*', 'zshrc', '.zshrc',
                 '.kshrc', 'kshrc',
                 'PKGBUILD']
    mimetypes = ['application/x-sh', 'application/x-shellscript', 'text/x-shellscript']
    url = 'https://en.wikipedia.org/wiki/Unix_shell'
    version_added = '0.6'

    tokens = {
        'root': [
            include('basic'),
            (r'`', String.Backtick, 'backticks'),
            include('data'),
            include('interp'),
        ],
        'interp': [
            (r'\$\(\(', Keyword, 'math'),
            (r'\$\(', Keyword, 'paren'),
            (r'\$\{#?', String.Interpol, 'curly'),
            (r'\$[a-zA-Z_]\w*', Name.Variable),  # user variable
            (r'\$(?:\d+|[#$?!_*@-])', Name.Variable),      # builtin
            (r'\$', Text),
        ],
        'basic': [
            (r'\b(if|fi|else|while|in|do|done|for|then|return|function|case|'
             r'select|break|continue|until|esac|elif)(\s*)\b',
             bygroups(Keyword, Whitespace)),
            (r'\b(alias|bg|bind|builtin|caller|cd|command|compgen|'
             r'complete|declare|dirs|disown|echo|enable|eval|exec|exit|'
             r'export|false|fc|fg|getopts|hash|help|history|jobs|kill|let|'
             r'local|logout|popd|printf|pushd|pwd|read|readonly|set|shift|'
             r'shopt|source|suspend|test|time|times|trap|true|type|typeset|'
             r'ulimit|umask|unalias|unset|wait)(?=[\s)`])',
             Name.Builtin),
            (r'\A#!.+\n', Comment.Hashbang),
            (r'#.*\n', Comment.Single),
            (r'\\[\w\W]', String.Escape),
            (r'(\b\w+)(\s*)(\+?=)', bygroups(Name.Variable, Whitespace, Operator)),
            (r'[\[\]{}()=]', Operator),
            (r'<<<', Operator),  # here-string
            (r'<<-?\s*(\'?)\\?(\w+)[\w\W]+?\2', String),
            (r'&&|\|\|', Operator),
        ],
        'data': [
            (r'(?s)\$?"(\\.|[^"\\$])*"', String.Double),
            (r'"', String.Double, 'string'),
            (r"(?s)\$'(\\\\|\\[0-7]+|\\.|[^'\\])*'", String.Single),
            (r"(?s)'.*?'", String.Single),
            (r';', Punctuation),
            (r'&', Punctuation),
            (r'\|', Punctuation),
            (r'\s+', Whitespace),
            (r'\d+\b', Number),
            (r'[^=\s\[\]{}()$"\'`\\<&|;]+', Text),
            (r'<', Text),
        ],
        'string': [
            (r'"', String.Double, '#pop'),
            (r'(?s)(\\\\|\\[0-7]+|\\.|[^"\\$])+', String.Double),
            include('interp'),
        ],
        'curly': [
            (r'\}', String.Interpol, '#pop'),
            (r':-', Keyword),
            (r'\w+', Name.Variable),
            (r'[^}:"\'`$\\]+', Punctuation),
            (r':', Punctuation),
            include('root'),
        ],
        'paren': [
            (r'\)', Keyword, '#pop'),
            include('root'),
        ],
        'math': [
            (r'\)\)', Keyword, '#pop'),
            (r'\*\*|\|\||<<|>>|[-+*/%^|&<>]', Operator),
            (r'\d+#[\da-zA-Z]+', Number),
            (r'\d+#(?! )', Number),
            (r'0[xX][\da-fA-F]+', Number),
            (r'\d+', Number),
            (r'[a-zA-Z_]\w*', Name.Variable),  # user variable
            include('root'),
        ],
        'backticks': [
            (r'`', String.Backtick, '#pop'),
            include('root'),
        ],
    }

    def analyse_text(text):
        if shebang_matches(text, r'(ba|z|)sh'):
            return 1
        if text.startswith('$ '):
            return 0.2


class SlurmBashLexer(BashLexer):
    """
    Lexer for (ba|k|z|)sh Slurm scripts.
    """

    name = 'Slurm'
    aliases = ['slurm', 'sbatch']
    filenames = ['*.sl']
    mimetypes = []
    version_added = '2.4'
    EXTRA_KEYWORDS = {'srun'}

    def get_tokens_unprocessed(self, text):
        for index, token, value in BashLexer.get_tokens_unprocessed(self, text):
            if token is Text and value in self.EXTRA_KEYWORDS:
                yield index, Name.Builtin, value
            elif token is Comment.Single and 'SBATCH' in value:
                yield index, Keyword.Pseudo, value
            else:
                yield index, token, value


class ShellSessionBaseLexer(Lexer):
    """
    Base lexer for shell sessions.

    .. versionadded:: 2.1
    """

    _bare_continuation = False
    _venv = re.compile(r'^(\([^)]*\))(\s*)')

    def get_tokens_unprocessed(self, text):
        innerlexer = self._innerLexerCls(**self.options)

        pos = 0
        curcode = ''
        insertions = []
        backslash_continuation = False

        for match in line_re.finditer(text):
            line = match.group()

            venv_match = self._venv.match(line)
            if venv_match:
                venv = venv_match.group(1)
                venv_whitespace = venv_match.group(2)
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt.VirtualEnv, venv)]))
                if venv_whitespace:
                    insertions.append((len(curcode),
                                       [(0, Text, venv_whitespace)]))
                line = line[venv_match.end():]

            m = self._ps1rgx.match(line)
            if m:
                # To support output lexers (say diff output), the output
                # needs to be broken by prompts whenever the output lexer
                # changes.
                if not insertions:
                    pos = match.start()

                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, m.group(1))]))
                curcode += m.group(2)
                backslash_continuation = curcode.endswith('\\\n')
            elif backslash_continuation:
                if line.startswith(self._ps2):
                    insertions.append((len(curcode),
                                       [(0, Generic.Prompt,
                                         line[:len(self._ps2)])]))
                    curcode += line[len(self._ps2):]
                else:
                    curcode += line
                backslash_continuation = curcode.endswith('\\\n')
            elif self._bare_continuation and line.startswith(self._ps2):
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt,
                                     line[:len(self._ps2)])]))
                curcode += line[len(self._ps2):]
            else:
                if insertions:
                    toks = innerlexer.get_tokens_unprocessed(curcode)
                    for i, t, v in do_insertions(insertions, toks):
                        yield pos+i, t, v
                yield match.start(), Generic.Output, line
                insertions = []
                curcode = ''
        if insertions:
            for i, t, v in do_insertions(insertions,
                                         innerlexer.get_tokens_unprocessed(curcode)):
                yield pos+i, t, v


class BashSessionLexer(ShellSessionBaseLexer):
    """
    Lexer for Bash shell sessions, i.e. command lines, including a
    prompt, interspersed with output.
    """

    name = 'Bash Session'
    aliases = ['console', 'shell-session']
    filenames = ['*.sh-session', '*.shell-session']
    mimetypes = ['application/x-shell-session', 'application/x-sh-session']
    url = 'https://en.wikipedia.org/wiki/Unix_shell'
    version_added = '1.1'
    _example = "console/example.sh-session"

    _innerLexerCls = BashLexer
    _ps1rgx = re.compile(
        r'^((?:(?:\[.*?\])|(?:\(\S+\))?(?:| |sh\S*?|\w+\S+[@:]\S+(?:\s+\S+)' \
        r'?|\[\S+[@:][^\n]+\].+))\s*[$#%]\s*)(.*\n?)')
    _ps2 = '> '


class BatchLexer(RegexLexer):
    """
    Lexer for the DOS/Windows Batch file format.
    """
    name = 'Batchfile'
    aliases = ['batch', 'bat', 'dosbatch', 'winbatch']
    filenames = ['*.bat', '*.cmd']
    mimetypes = ['application/x-dos-batch']
    url = 'https://en.wikipedia.org/wiki/Batch_file'
    version_added = '0.7'

    flags = re.MULTILINE | re.IGNORECASE

    _nl = r'\n\x1a'
    _punct = r'&<>|'
    _ws = r'\t\v\f\r ,;=\xa0'
    _nlws = r'\s\x1a\xa0,;='
    _space = rf'(?:(?:(?:\^[{_nl}])?[{_ws}])+)'
    _keyword_terminator = (rf'(?=(?:\^[{_nl}]?)?[{_ws}+./:[\\\]]|[{_nl}{_punct}(])')
    _token_terminator = rf'(?=\^?[{_ws}]|[{_punct}{_nl}])'
    _start_label = rf'((?:(?<=^[^:])|^[^:]?)[{_ws}]*)(:)'
    _label = rf'(?:(?:[^{_nlws}{_punct}+:^]|\^[{_nl}]?[\w\W])*)'
    _label_compound = rf'(?:(?:[^{_nlws}{_punct}+:^)]|\^[{_nl}]?[^)])*)'
    _number = rf'(?:-?(?:0[0-7]+|0x[\da-f]+|\d+){_token_terminator})'
    _opword = r'(?:equ|geq|gtr|leq|lss|neq)'
    _string = rf'(?:"[^{_nl}"]*(?:"|(?=[{_nl}])))'
    _variable = (r'(?:(?:%(?:\*|(?:~[a-z]*(?:\$[^:]+:)?)?\d|'
                 rf'[^%:{_nl}]+(?::(?:~(?:-?\d+)?(?:,(?:-?\d+)?)?|(?:[^%{_nl}^]|'
                 rf'\^[^%{_nl}])[^={_nl}]*=(?:[^%{_nl}^]|\^[^%{_nl}])*)?)?%))|'
                 rf'(?:\^?![^!:{_nl}]+(?::(?:~(?:-?\d+)?(?:,(?:-?\d+)?)?|(?:'
                 rf'[^!{_nl}^]|\^[^!{_nl}])[^={_nl}]*=(?:[^!{_nl}^]|\^[^!{_nl}])*)?)?\^?!))')
    _core_token = rf'(?:(?:(?:\^[{_nl}]?)?[^"{_nlws}{_punct}])+)'
    _core_token_compound = rf'(?:(?:(?:\^[{_nl}]?)?[^"{_nlws}{_punct})])+)'
    _token = rf'(?:[{_punct}]+|{_core_token})'
    _token_compound = rf'(?:[{_punct}]+|{_core_token_compound})'
    _stoken = (rf'(?:[{_punct}]+|(?:{_string}|{_variable}|{_core_token})+)')

    def _make_begin_state(compound, _core_token=_core_token,
                          _core_token_compound=_core_token_compound,
                          _keyword_terminator=_keyword_terminator,
                          _nl=_nl, _punct=_punct, _string=_string,
                          _space=_space, _start_label=_start_label,
                          _stoken=_stoken, _token_terminator=_token_terminator,
                          _variable=_variable, _ws=_ws):
        rest = '(?:{}|{}|[^"%{}{}{}])*'.format(_string, _variable, _nl, _punct,
                                            ')' if compound else '')
        rest_of_line = rf'(?:(?:[^{_nl}^]|\^[{_nl}]?[\w\W])*)'
        rest_of_line_compound = rf'(?:(?:[^{_nl}^)]|\^[{_nl}]?[^)])*)'
        set_space = rf'((?:(?:\^[{_nl}]?)?[^\S\n])*)'
        suffix = ''
        if compound:
            _keyword_terminator = rf'(?:(?=\))|{_keyword_terminator})'
            _token_terminator = rf'(?:(?=\))|{_token_terminator})'
            suffix = '/compound'
        return [
            ((r'\)', Punctuation, '#pop') if compound else
             (rf'\)((?=\()|{_token_terminator}){rest_of_line}',
              Comment.Single)),
            (rf'(?={_start_label})', Text, f'follow{suffix}'),
            (_space, using(this, state='text')),
            include(f'redirect{suffix}'),
            (rf'[{_nl}]+', Text),
            (r'\(', Punctuation, 'root/compound'),
            (r'@+', Punctuation),
            (rf'((?:for|if|rem)(?:(?=(?:\^[{_nl}]?)?/)|(?:(?!\^)|'
             rf'(?<=m))(?:(?=\()|{_token_terminator})))({_space}?{_core_token_compound if compound else _core_token}?(?:\^[{_nl}]?)?/(?:\^[{_nl}]?)?\?)',
             bygroups(Keyword, using(this, state='text')),
             f'follow{suffix}'),
            (rf'(goto{_keyword_terminator})({rest}(?:\^[{_nl}]?)?/(?:\^[{_nl}]?)?\?{rest})',
             bygroups(Keyword, using(this, state='text')),
             f'follow{suffix}'),
            (words(('assoc', 'break', 'cd', 'chdir', 'cls', 'color', 'copy',
                    'date', 'del', 'dir', 'dpath', 'echo', 'endlocal', 'erase',
                    'exit', 'ftype', 'keys', 'md', 'mkdir', 'mklink', 'move',
                    'path', 'pause', 'popd', 'prompt', 'pushd', 'rd', 'ren',
                    'rename', 'rmdir', 'setlocal', 'shift', 'start', 'time',
                    'title', 'type', 'ver', 'verify', 'vol'),
                   suffix=_keyword_terminator), Keyword, f'follow{suffix}'),
            (rf'(call)({_space}?)(:)',
             bygroups(Keyword, using(this, state='text'), Punctuation),
             f'call{suffix}'),
            (rf'call{_keyword_terminator}', Keyword),
            (rf'(for{_token_terminator}(?!\^))({_space})(/f{_token_terminator})',
             bygroups(Keyword, using(this, state='text'), Keyword),
             ('for/f', 'for')),
            (rf'(for{_token_terminator}(?!\^))({_space})(/l{_token_terminator})',
             bygroups(Keyword, using(this, state='text'), Keyword),
             ('for/l', 'for')),
            (rf'for{_token_terminator}(?!\^)', Keyword, ('for2', 'for')),
            (rf'(goto{_keyword_terminator})({_space}?)(:?)',
             bygroups(Keyword, using(this, state='text'), Punctuation),
             f'label{suffix}'),
            (rf'(if(?:(?=\()|{_token_terminator})(?!\^))({_space}?)((?:/i{_token_terminator})?)({_space}?)((?:not{_token_terminator})?)({_space}?)',
             bygroups(Keyword, using(this, state='text'), Keyword,
                      using(this, state='text'), Keyword,
                      using(this, state='text')), ('(?', 'if')),
            (rf'rem(((?=\()|{_token_terminator}){_space}?{_stoken}?.*|{_keyword_terminator}{rest_of_line_compound if compound else rest_of_line})',
             Comment.Single, f'follow{suffix}'),
            (rf'(set{_keyword_terminator}){set_space}(/a)',
             bygroups(Keyword, using(this, state='text'), Keyword),
             f'arithmetic{suffix}'),
            (r'(set{}){}((?:/p)?){}((?:(?:(?:\^[{}]?)?[^"{}{}^={}]|'
             r'\^[{}]?[^"=])+)?)((?:(?:\^[{}]?)?=)?)'.format(_keyword_terminator, set_space, set_space, _nl, _nl, _punct,
              ')' if compound else '', _nl, _nl),
             bygroups(Keyword, using(this, state='text'), Keyword,
                      using(this, state='text'), using(this, state='variable'),
                      Punctuation),
             f'follow{suffix}'),
            default(f'follow{suffix}')
        ]

    def _make_follow_state(compound, _label=_label,
                           _label_compound=_label_compound, _nl=_nl,
                           _space=_space, _start_label=_start_label,
                           _token=_token, _token_compound=_token_compound,
                           _ws=_ws):
        suffix = '/compound' if compound else ''
        state = []
        if compound:
            state.append((r'(?=\))', Text, '#pop'))
        state += [
            (rf'{_start_label}([{_ws}]*)({_label_compound if compound else _label})(.*)',
             bygroups(Text, Punctuation, Text, Name.Label, Comment.Single)),
            include(f'redirect{suffix}'),
            (rf'(?=[{_nl}])', Text, '#pop'),
            (r'\|\|?|&&?', Punctuation, '#pop'),
            include('text')
        ]
        return state

    def _make_arithmetic_state(compound, _nl=_nl, _punct=_punct,
                               _string=_string, _variable=_variable,
                               _ws=_ws, _nlws=_nlws):
        op = r'=+\-*/!~'
        state = []
        if compound:
            state.append((r'(?=\))', Text, '#pop'))
        state += [
            (r'0[0-7]+', Number.Oct),
            (r'0x[\da-f]+', Number.Hex),
            (r'\d+', Number.Integer),
            (r'[(),]+', Punctuation),
            (rf'([{op}]|%|\^\^)+', Operator),
            (r'({}|{}|(\^[{}]?)?[^(){}%\^"{}{}]|\^[{}]?{})+'.format(_string, _variable, _nl, op, _nlws, _punct, _nlws,
              r'[^)]' if compound else r'[\w\W]'),
             using(this, state='variable')),
            (r'(?=[\x00|&])', Text, '#pop'),
            include('follow')
        ]
        return state

    def _make_call_state(compound, _label=_label,
                         _label_compound=_label_compound):
        state = []
        if compound:
            state.append((r'(?=\))', Text, '#pop'))
        state.append((r'(:?)(%s)' % (_label_compound if compound else _label),
                      bygroups(Punctuation, Name.Label), '#pop'))
        return state

    def _make_label_state(compound, _label=_label,
                          _label_compound=_label_compound, _nl=_nl,
                          _punct=_punct, _string=_string, _variable=_variable):
        state = []
        if compound:
            state.append((r'(?=\))', Text, '#pop'))
        state.append((r'({}?)((?:{}|{}|\^[{}]?{}|[^"%^{}{}{}])*)'.format(_label_compound if compound else _label, _string,
                       _variable, _nl, r'[^)]' if compound else r'[\w\W]', _nl,
                       _punct, r')' if compound else ''),
                      bygroups(Name.Label, Comment.Single), '#pop'))
        return state

    def _make_redirect_state(compound,
                             _core_token_compound=_core_token_compound,
                             _nl=_nl, _punct=_punct, _stoken=_stoken,
                             _string=_string, _space=_space,
                             _variable=_variable, _nlws=_nlws):
        stoken_compound = (rf'(?:[{_punct}]+|(?:{_string}|{_variable}|{_core_token_compound})+)')
        return [
            (rf'((?:(?<=[{_nlws}])\d)?)(>>?&|<&)([{_nlws}]*)(\d)',
             bygroups(Number.Integer, Punctuation, Text, Number.Integer)),
            (rf'((?:(?<=[{_nlws}])(?<!\^[{_nl}])\d)?)(>>?|<)({_space}?{stoken_compound if compound else _stoken})',
             bygroups(Number.Integer, Punctuation, using(this, state='text')))
        ]

    tokens = {
        'root': _make_begin_state(False),
        'follow': _make_follow_state(False),
        'arithmetic': _make_arithmetic_state(False),
        'call': _make_call_state(False),
        'label': _make_label_state(False),
        'redirect': _make_redirect_state(False),
        'root/compound': _make_begin_state(True),
        'follow/compound': _make_follow_state(True),
        'arithmetic/compound': _make_arithmetic_state(True),
        'call/compound': _make_call_state(True),
        'label/compound': _make_label_state(True),
        'redirect/compound': _make_redirect_state(True),
        'variable-or-escape': [
            (_variable, Name.Variable),
            (rf'%%|\^[{_nl}]?(\^!|[\w\W])', String.Escape)
        ],
        'string': [
            (r'"', String.Double, '#pop'),
            (_variable, Name.Variable),
            (r'\^!|%%', String.Escape),
            (rf'[^"%^{_nl}]+|[%^]', String.Double),
            default('#pop')
        ],
        'sqstring': [
            include('variable-or-escape'),
            (r'[^%]+|%', String.Single)
        ],
        'bqstring': [
            include('variable-or-escape'),
            (r'[^%]+|%', String.Backtick)
        ],
        'text': [
            (r'"', String.Double, 'string'),
            include('variable-or-escape'),
            (rf'[^"%^{_nlws}{_punct}\d)]+|.', Text)
        ],
        'variable': [
            (r'"', String.Double, 'string'),
            include('variable-or-escape'),
            (rf'[^"%^{_nl}]+|.', Name.Variable)
        ],
        'for': [
            (rf'({_space})(in)({_space})(\()',
             bygroups(using(this, state='text'), Keyword,
                      using(this, state='text'), Punctuation), '#pop'),
            include('follow')
        ],
        'for2': [
            (r'\)', Punctuation),
            (rf'({_space})(do{_token_terminator})',
             bygroups(using(this, state='text'), Keyword), '#pop'),
            (rf'[{_nl}]+', Text),
            include('follow')
        ],
        'for/f': [
            (rf'(")((?:{_variable}|[^"])*?")([{_nlws}]*)(\))',
             bygroups(String.Double, using(this, state='string'), Text,
                      Punctuation)),
            (r'"', String.Double, ('#pop', 'for2', 'string')),
            (rf"('(?:%%|{_variable}|[\w\W])*?')([{_nlws}]*)(\))",
             bygroups(using(this, state='sqstring'), Text, Punctuation)),
            (rf'(`(?:%%|{_variable}|[\w\W])*?`)([{_nlws}]*)(\))',
             bygroups(using(this, state='bqstring'), Text, Punctuation)),
            include('for2')
        ],
        'for/l': [
            (r'-?\d+', Number.Integer),
            include('for2')
        ],
        'if': [
            (rf'((?:cmdextversion|errorlevel){_token_terminator})({_space})(\d+)',
             bygroups(Keyword, using(this, state='text'),
                      Number.Integer), '#pop'),
            (rf'(defined{_token_terminator})({_space})({_stoken})',
             bygroups(Keyword, using(this, state='text'),
                      using(this, state='variable')), '#pop'),
            (rf'(exist{_token_terminator})({_space}{_stoken})',
             bygroups(Keyword, using(this, state='text')), '#pop'),
            (rf'({_number}{_space})({_opword})({_space}{_number})',
             bygroups(using(this, state='arithmetic'), Operator.Word,
                      using(this, state='arithmetic')), '#pop'),
            (_stoken, using(this, state='text'), ('#pop', 'if2')),
        ],
        'if2': [
            (rf'({_space}?)(==)({_space}?{_stoken})',
             bygroups(using(this, state='text'), Operator,
                      using(this, state='text')), '#pop'),
            (rf'({_space})({_opword})({_space}{_stoken})',
             bygroups(using(this, state='text'), Operator.Word,
                      using(this, state='text')), '#pop')
        ],
        '(?': [
            (_space, using(this, state='text')),
            (r'\(', Punctuation, ('#pop', 'else?', 'root/compound')),
            default('#pop')
        ],
        'else?': [
            (_space, using(this, state='text')),
            (rf'else{_token_terminator}', Keyword, '#pop'),
            default('#pop')
        ]
    }


class MSDOSSessionLexer(ShellSessionBaseLexer):
    """
    Lexer for MS DOS shell sessions, i.e. command lines, including a
    prompt, interspersed with output.
    """

    name = 'MSDOS Session'
    aliases = ['doscon']
    filenames = []
    mimetypes = []
    url = 'https://en.wikipedia.org/wiki/MS-DOS'
    version_added = '2.1'
    _example = "doscon/session"

    _innerLexerCls = BatchLexer
    _ps1rgx = re.compile(r'^([^>]*>)(.*\n?)')
    _ps2 = 'More? '


class TcshLexer(RegexLexer):
    """
    Lexer for tcsh scripts.
    """

    name = 'Tcsh'
    aliases = ['tcsh', 'csh']
    filenames = ['*.tcsh', '*.csh']
    mimetypes = ['application/x-csh']
    url = 'https://www.tcsh.org'
    version_added = '0.10'

    tokens = {
        'root': [
            include('basic'),
            (r'\$\(', Keyword, 'paren'),
            (r'\$\{#?', Keyword, 'curly'),
            (r'`', String.Backtick, 'backticks'),
            include('data'),
        ],
        'basic': [
            (r'\b(if|endif|else|while|then|foreach|case|default|'
             r'break|continue|goto|breaksw|end|switch|endsw)\s*\b',
             Keyword),
            (r'\b(alias|alloc|bg|bindkey|builtins|bye|caller|cd|chdir|'
             r'complete|dirs|echo|echotc|eval|exec|exit|fg|filetest|getxvers|'
             r'glob|getspath|hashstat|history|hup|inlib|jobs|kill|'
             r'limit|log|login|logout|ls-F|migrate|newgrp|nice|nohup|notify|'
             r'onintr|popd|printenv|pushd|rehash|repeat|rootnode|popd|pushd|'
             r'set|shift|sched|setenv|setpath|settc|setty|setxvers|shift|'
             r'source|stop|suspend|source|suspend|telltc|time|'
             r'umask|unalias|uncomplete|unhash|universe|unlimit|unset|unsetenv|'
             r'ver|wait|warp|watchlog|where|which)\s*\b',
             Name.Builtin),
            (r'#.*', Comment),
            (r'\\[\w\W]', String.Escape),
            (r'(\b\w+)(\s*)(=)', bygroups(Name.Variable, Text, Operator)),
            (r'[\[\]{}()=]+', Operator),
            (r'<<\s*(\'?)\\?(\w+)[\w\W]+?\2', String),
            (r';', Punctuation),
        ],
        'data': [
            (r'(?s)"(\\\\|\\[0-7]+|\\.|[^"\\])*"', String.Double),
            (r"(?s)'(\\\\|\\[0-7]+|\\.|[^'\\])*'", String.Single),
            (r'\s+', Text),
            (r'[^=\s\[\]{}()$"\'`\\;#]+', Text),
            (r'\d+(?= |\Z)', Number),
            (r'\$#?(\w+|.)', Name.Variable),
        ],
        'curly': [
            (r'\}', Keyword, '#pop'),
            (r':-', Keyword),
            (r'\w+', Name.Variable),
            (r'[^}:"\'`$]+', Punctuation),
            (r':', Punctuation),
            include('root'),
        ],
        'paren': [
            (r'\)', Keyword, '#pop'),
            include('root'),
        ],
        'backticks': [
            (r'`', String.Backtick, '#pop'),
            include('root'),
        ],
    }


class TcshSessionLexer(ShellSessionBaseLexer):
    """
    Lexer for Tcsh sessions, i.e. command lines, including a
    prompt, interspersed with output.
    """

    name = 'Tcsh Session'
    aliases = ['tcshcon']
    filenames = []
    mimetypes = []
    url = 'https://www.tcsh.org'
    version_added = '2.1'
    _example = "tcshcon/session"

    _innerLexerCls = TcshLexer
    _ps1rgx = re.compile(r'^([^>]+>)(.*\n?)')
    _ps2 = '? '


class PowerShellLexer(RegexLexer):
    """
    For Windows PowerShell code.
    """
    name = 'PowerShell'
    aliases = ['powershell', 'pwsh', 'posh', 'ps1', 'psm1']
    filenames = ['*.ps1', '*.psm1']
    mimetypes = ['text/x-powershell']
    url = 'https://learn.microsoft.com/en-us/powershell'
    version_added = '1.5'

    flags = re.DOTALL | re.IGNORECASE | re.MULTILINE

    keywords = (
        'while validateset validaterange validatepattern validatelength '
        'validatecount until trap switch return ref process param parameter in '
        'if global: local: function foreach for finally filter end elseif else '
        'dynamicparam do default continue cmdletbinding break begin alias \\? '
        '% #script #private #local #global mandatory parametersetname position '
        'valuefrompipeline valuefrompipelinebypropertyname '
        'valuefromremainingarguments helpmessage try catch throw').split()

    operators = (
        'and as band bnot bor bxor casesensitive ccontains ceq cge cgt cle '
        'clike clt cmatch cne cnotcontains cnotlike cnotmatch contains '
        'creplace eq exact f file ge gt icontains ieq ige igt ile ilike ilt '
        'imatch ine inotcontains inotlike inotmatch ireplace is isnot le like '
        'lt match ne not notcontains notlike notmatch or regex replace '
        'wildcard').split()

    verbs = (
        'write where watch wait use update unregister unpublish unprotect '
        'unlock uninstall undo unblock trace test tee take sync switch '
        'suspend submit stop step start split sort skip show set send select '
        'search scroll save revoke resume restore restart resolve resize '
        'reset request repair rename remove register redo receive read push '
        'publish protect pop ping out optimize open new move mount merge '
        'measure lock limit join invoke install initialize import hide group '
        'grant get format foreach find export expand exit enter enable edit '
        'dismount disconnect disable deny debug cxnew copy convertto '
        'convertfrom convert connect confirm compress complete compare close '
        'clear checkpoint block backup assert approve aggregate add').split()

    aliases_ = (
        'ac asnp cat cd cfs chdir clc clear clhy cli clp cls clv cnsn '
        'compare copy cp cpi cpp curl cvpa dbp del diff dir dnsn ebp echo epal '
        'epcsv epsn erase etsn exsn fc fhx fl foreach ft fw gal gbp gc gci gcm '
        'gcs gdr ghy gi gjb gl gm gmo gp gps gpv group gsn gsnp gsv gu gv gwmi '
        'h history icm iex ihy ii ipal ipcsv ipmo ipsn irm ise iwmi iwr kill lp '
        'ls man md measure mi mount move mp mv nal ndr ni nmo npssc nsn nv ogv '
        'oh popd ps pushd pwd r rbp rcjb rcsn rd rdr ren ri rjb rm rmdir rmo '
        'rni rnp rp rsn rsnp rujb rv rvpa rwmi sajb sal saps sasv sbp sc select '
        'set shcm si sl sleep sls sort sp spjb spps spsv start sujb sv swmi tee '
        'trcm type wget where wjb write').split()

    commenthelp = (
        'component description example externalhelp forwardhelpcategory '
        'forwardhelptargetname functionality inputs link '
        'notes outputs parameter remotehelprunspace role synopsis').split()

    tokens = {
        'root': [
            # we need to count pairs of parentheses for correct highlight
            # of '$(...)' blocks in strings
            (r'\(', Punctuation, 'child'),
            (r'\s+', Text),
            (r'^(\s*#[#\s]*)(\.(?:{}))([^\n]*$)'.format('|'.join(commenthelp)),
             bygroups(Comment, String.Doc, Comment)),
            (r'#[^\n]*?$', Comment),
            (r'(&lt;|<)#', Comment.Multiline, 'multline'),
            (r'@"\n', String.Heredoc, 'heredoc-double'),
            (r"@'\n.*?\n'@", String.Heredoc),
            # escaped syntax
            (r'`[\'"$@-]', Punctuation),
            (r'"', String.Double, 'string'),
            (r"'([^']|'')*'", String.Single),
            (r'(\$|@@|@)((global|script|private|env):)?\w+',
             Name.Variable),
            (r'({})\b'.format('|'.join(keywords)), Keyword),
            (r'-({})\b'.format('|'.join(operators)), Operator),
            (r'({})-[a-z_]\w*\b'.format('|'.join(verbs)), Name.Builtin),
            (r'({})\s'.format('|'.join(aliases_)), Name.Builtin),
            (r'\[[a-z_\[][\w. `,\[\]]*\]', Name.Constant),  # .net [type]s
            (r'-[a-z_]\w*', Name),
            (r'\w+', Name),
            (r'[.,;:@{}\[\]$()=+*/\\&%!~?^`|<>-]', Punctuation),
        ],
        'child': [
            (r'\)', Punctuation, '#pop'),
            include('root'),
        ],
        'multline': [
            (r'[^#&.]+', Comment.Multiline),
            (r'#(>|&gt;)', Comment.Multiline, '#pop'),
            (r'\.({})'.format('|'.join(commenthelp)), String.Doc),
            (r'[#&.]', Comment.Multiline),
        ],
        'string': [
            (r"`[0abfnrtv'\"$`]", String.Escape),
            (r'[^$`"]+', String.Double),
            (r'\$\(', Punctuation, 'child'),
            (r'""', String.Double),
            (r'[`$]', String.Double),
            (r'"', String.Double, '#pop'),
        ],
        'heredoc-double': [
            (r'\n"@', String.Heredoc, '#pop'),
            (r'\$\(', Punctuation, 'child'),
            (r'[^@\n]+"]', String.Heredoc),
            (r".", String.Heredoc),
        ]
    }


class PowerShellSessionLexer(ShellSessionBaseLexer):
    """
    Lexer for PowerShell sessions, i.e. command lines, including a
    prompt, interspersed with output.
    """

    name = 'PowerShell Session'
    aliases = ['pwsh-session', 'ps1con']
    filenames = []
    mimetypes = []
    url = 'https://learn.microsoft.com/en-us/powershell'
    version_added = '2.1'
    _example = "pwsh-session/session"

    _innerLexerCls = PowerShellLexer
    _bare_continuation = True
    _ps1rgx = re.compile(r'^((?:\[[^]]+\]: )?PS[^>]*> ?)(.*\n?)')
    _ps2 = '> '


class FishShellLexer(RegexLexer):
    """
    Lexer for Fish shell scripts.
    """

    name = 'Fish'
    aliases = ['fish', 'fishshell']
    filenames = ['*.fish', '*.load']
    mimetypes = ['application/x-fish']
    url = 'https://fishshell.com'
    version_added = '2.1'

    tokens = {
        'root': [
            include('basic'),
            include('data'),
            include('interp'),
        ],
        'interp': [
            (r'\$\(\(', Keyword, 'math'),
            (r'\(', Keyword, 'paren'),
            (r'\$#?(\w+|.)', Name.Variable),
        ],
        'basic': [
            (r'\b(begin|end|if|else|while|break|for|in|return|function|block|'
             r'case|continue|switch|not|and|or|set|echo|exit|pwd|true|false|'
             r'cd|count|test)(\s*)\b',
             bygroups(Keyword, Text)),
            (r'\b(alias|bg|bind|breakpoint|builtin|command|commandline|'
             r'complete|contains|dirh|dirs|emit|eval|exec|fg|fish|fish_config|'
             r'fish_indent|fish_pager|fish_prompt|fish_right_prompt|'
             r'fish_update_completions|fishd|funced|funcsave|functions|help|'
             r'history|isatty|jobs|math|mimedb|nextd|open|popd|prevd|psub|'
             r'pushd|random|read|set_color|source|status|trap|type|ulimit|'
             r'umask|vared|fc|getopts|hash|kill|printf|time|wait)\s*\b(?!\.)',
             Name.Builtin),
            (r'#.*\n', Comment),
            (r'\\[\w\W]', String.Escape),
            (r'(\b\w+)(\s*)(=)', bygroups(Name.Variable, Whitespace, Operator)),
            (r'[\[\]()=]', Operator),
            (r'<<-?\s*(\'?)\\?(\w+)[\w\W]+?\2', String),
        ],
        'data': [
            (r'(?s)\$?"(\\\\|\\[0-7]+|\\.|[^"\\$])*"', String.Double),
            (r'"', String.Double, 'string'),
            (r"(?s)\$'(\\\\|\\[0-7]+|\\.|[^'\\])*'", String.Single),
            (r"(?s)'.*?'", String.Single),
            (r';', Punctuation),
            (r'&|\||\^|<|>', Operator),
            (r'\s+', Text),
            (r'\d+(?= |\Z)', Number),
            (r'[^=\s\[\]{}()$"\'`\\<&|;]+', Text),
        ],
        'string': [
            (r'"', String.Double, '#pop'),
            (r'(?s)(\\\\|\\[0-7]+|\\.|[^"\\$])+', String.Double),
            include('interp'),
        ],
        'paren': [
            (r'\)', Keyword, '#pop'),
            include('root'),
        ],
        'math': [
            (r'\)\)', Keyword, '#pop'),
            (r'[-+*/%^|&]|\*\*|\|\|', Operator),
            (r'\d+#\d+', Number),
            (r'\d+#(?! )', Number),
            (r'\d+', Number),
            include('root'),
        ],
    }

class ExeclineLexer(RegexLexer):
    """
    Lexer for Laurent Bercot's execline language.
    """

    name = 'execline'
    aliases = ['execline']
    filenames = ['*.exec']
    url = 'https://skarnet.org/software/execline'
    version_added = '2.7'

    tokens = {
        'root': [
            include('basic'),
            include('data'),
            include('interp')
        ],
        'interp': [
            (r'\$\{', String.Interpol, 'curly'),
            (r'\$[\w@#]+', Name.Variable),  # user variable
            (r'\$', Text),
        ],
        'basic': [
            (r'\b(background|backtick|cd|define|dollarat|elgetopt|'
             r'elgetpositionals|elglob|emptyenv|envfile|exec|execlineb|'
             r'exit|export|fdblock|fdclose|fdmove|fdreserve|fdswap|'
             r'forbacktickx|foreground|forstdin|forx|getcwd|getpid|heredoc|'
             r'homeof|if|ifelse|ifte|ifthenelse|importas|loopwhilex|'
             r'multidefine|multisubstitute|pipeline|piperw|posix-cd|'
             r'redirfd|runblock|shift|trap|tryexec|umask|unexport|wait|'
             r'withstdinas)\b', Name.Builtin),
            (r'\A#!.+\n', Comment.Hashbang),
            (r'#.*\n', Comment.Single),
            (r'[{}]', Operator)
        ],
        'data': [
            (r'(?s)"(\\.|[^"\\$])*"', String.Double),
            (r'"', String.Double, 'string'),
            (r'\s+', Text),
            (r'[^\s{}$"\\]+', Text)
        ],
        'string': [
            (r'"', String.Double, '#pop'),
            (r'(?s)(\\\\|\\.|[^"\\$])+', String.Double),
            include('interp'),
        ],
        'curly': [
            (r'\}', String.Interpol, '#pop'),
            (r'[\w#@]+', Name.Variable),
            include('root')
        ]

    }

    def analyse_text(text):
        if shebang_matches(text, r'execlineb'):
            return 1

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_dtls.py ===
from __future__ import annotations

import random
from contextlib import asynccontextmanager
from itertools import count
from typing import TYPE_CHECKING, NoReturn

import attrs
import pytest

from trio._tests.pytest_plugin import skip_if_optional_else_raise

try:
    import trustme
    from OpenSSL import SSL
except ImportError as error:
    skip_if_optional_else_raise(error)


import trio
import trio.testing
from trio import DTLSChannel, DTLSEndpoint
from trio.testing._fake_net import FakeNet, UDPPacket

from .._core._tests.tutil import binds_ipv6, gc_collect_harder, slow

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

ca = trustme.CA()
server_cert = ca.issue_cert("example.com")

server_ctx = SSL.Context(SSL.DTLS_METHOD)
server_cert.configure_cert(server_ctx)

client_ctx = SSL.Context(SSL.DTLS_METHOD)
ca.configure_trust(client_ctx)


parametrize_ipv6 = pytest.mark.parametrize(
    "ipv6",
    [False, pytest.param(True, marks=binds_ipv6)],
    ids=["ipv4", "ipv6"],
)


def endpoint(**kwargs: int | bool) -> DTLSEndpoint:
    ipv6 = kwargs.pop("ipv6", False)
    family = trio.socket.AF_INET6 if ipv6 else trio.socket.AF_INET
    sock = trio.socket.socket(type=trio.socket.SOCK_DGRAM, family=family)
    return DTLSEndpoint(sock, **kwargs)


@asynccontextmanager
async def dtls_echo_server(
    *,
    autocancel: bool = True,
    mtu: int | None = None,
    ipv6: bool = False,
) -> AsyncGenerator[tuple[DTLSEndpoint, tuple[str, int]], None]:
    with endpoint(ipv6=ipv6) as server:
        localhost = "::1" if ipv6 else "127.0.0.1"
        await server.socket.bind((localhost, 0))
        async with trio.open_nursery() as nursery:

            async def echo_handler(dtls_channel: DTLSChannel) -> None:
                print(
                    "echo handler started: "
                    f"server {dtls_channel.endpoint.socket.getsockname()!r} "
                    f"client {dtls_channel.peer_address!r}",
                )
                if mtu is not None:
                    dtls_channel.set_ciphertext_mtu(mtu)
                try:
                    print("server starting do_handshake")
                    await dtls_channel.do_handshake()
                    print("server finished do_handshake")
                    # no branch for leaving this for loop because we only leave
                    # a channel by cancellation.
                    async for packet in dtls_channel:  # pragma: no branch
                        print(f"echoing {packet!r} -> {dtls_channel.peer_address!r}")
                        await dtls_channel.send(packet)
                except trio.BrokenResourceError:  # pragma: no cover
                    print("echo handler channel broken")

            await nursery.start(server.serve, server_ctx, echo_handler)

            yield server, server.socket.getsockname()

            if autocancel:
                nursery.cancel_scope.cancel()


@parametrize_ipv6
async def test_smoke(ipv6: bool) -> None:
    async with dtls_echo_server(ipv6=ipv6) as (_server_endpoint, address):
        with endpoint(ipv6=ipv6) as client_endpoint:
            client_channel = client_endpoint.connect(address, client_ctx)
            with pytest.raises(trio.NeedHandshakeError):
                client_channel.get_cleartext_mtu()

            await client_channel.do_handshake()
            await client_channel.send(b"hello")
            assert await client_channel.receive() == b"hello"
            await client_channel.send(b"goodbye")
            assert await client_channel.receive() == b"goodbye"

            with pytest.raises(
                ValueError,
                match=r"^openssl doesn't support sending empty DTLS packets$",
            ):
                await client_channel.send(b"")

            client_channel.set_ciphertext_mtu(1234)
            cleartext_mtu_1234 = client_channel.get_cleartext_mtu()
            client_channel.set_ciphertext_mtu(4321)
            assert client_channel.get_cleartext_mtu() > cleartext_mtu_1234
            client_channel.set_ciphertext_mtu(1234)
            assert client_channel.get_cleartext_mtu() == cleartext_mtu_1234


@slow
async def test_handshake_over_terrible_network(
    autojump_clock: trio.testing.MockClock,
) -> None:
    HANDSHAKES = 100
    r = random.Random(0)
    fn = FakeNet()
    fn.enable()
    # avoid spurious timeouts on slow machines
    autojump_clock.autojump_threshold = 0.001

    async with dtls_echo_server() as (_, address):
        async with trio.open_nursery() as nursery:

            async def route_packet(packet: UDPPacket) -> None:
                while True:
                    op = r.choices(
                        ["deliver", "drop", "dupe", "delay"],
                        weights=[0.7, 0.1, 0.1, 0.1],
                    )[0]
                    print(f"{packet.source} -> {packet.destination}: {op}")
                    if op == "drop":
                        return
                    elif op == "dupe":
                        fn.send_packet(packet)
                    elif op == "delay":
                        await trio.sleep(r.random() * 3)
                    # I wanted to test random packet corruption too, but it turns out
                    # openssl has a bug in the following scenario:
                    #
                    # - client sends ClientHello
                    # - server sends HelloVerifyRequest with cookie -- but cookie is
                    #   invalid b/c either the ClientHello or HelloVerifyRequest was
                    #   corrupted
                    # - client re-sends ClientHello with invalid cookie
                    # - server replies with new HelloVerifyRequest and correct cookie
                    #
                    # At this point, the client *should* switch to the new, valid
                    # cookie. But OpenSSL doesn't; it stubbornly insists on re-sending
                    # the original, invalid cookie over and over. In theory we could
                    # work around this by detecting cookie changes and starting over
                    # with a whole new SSL object, but (a) it doesn't seem worth it, (b)
                    # when I tried then I ran into another issue where OpenSSL got stuck
                    # in an infinite loop sending alerts over and over, which I didn't
                    # dig into because see (a).
                    #
                    # elif op == "distort":
                    #     payload = bytearray(packet.payload)
                    #     payload[r.randrange(len(payload))] ^= 1 << r.randrange(8)
                    #     packet = attrs.evolve(packet, payload=payload)
                    else:
                        assert op == "deliver"
                        print(
                            f"{packet.source} -> {packet.destination}: delivered"
                            f" {packet.payload.hex()}",
                        )
                        fn.deliver_packet(packet)
                        break

            def route_packet_wrapper(packet: UDPPacket) -> None:
                try:  # noqa: SIM105  # suppressible-exception
                    nursery.start_soon(route_packet, packet)
                except RuntimeError:  # pragma: no cover
                    # We're exiting the nursery, so any remaining packets can just get
                    # dropped
                    pass

            fn.route_packet = route_packet_wrapper  # type: ignore[assignment]  # TODO: Fix FakeNet typing

            for i in range(HANDSHAKES):
                print("#" * 80)
                print("#" * 80)
                print("#" * 80)
                with endpoint() as client_endpoint:
                    client = client_endpoint.connect(address, client_ctx)
                    print("client starting do_handshake")
                    await client.do_handshake()
                    print("client finished do_handshake")
                    msg = str(i).encode()
                    # Make multiple attempts to send data, because the network might
                    # drop it
                    while True:
                        with trio.move_on_after(10) as cscope:
                            await client.send(msg)
                            assert await client.receive() == msg
                        if not cscope.cancelled_caught:
                            break


async def test_implicit_handshake() -> None:
    async with dtls_echo_server() as (_, address):
        with endpoint() as client_endpoint:
            client = client_endpoint.connect(address, client_ctx)

            # Implicit handshake
            await client.send(b"xyz")
            assert await client.receive() == b"xyz"


async def test_full_duplex() -> None:
    # Tests simultaneous send/receive, and also multiple methods implicitly invoking
    # do_handshake simultaneously.
    with endpoint() as server_endpoint, endpoint() as client_endpoint:
        await server_endpoint.socket.bind(("127.0.0.1", 0))
        async with trio.open_nursery() as server_nursery:

            async def handler(channel: DTLSChannel) -> None:
                async with trio.open_nursery() as nursery:
                    nursery.start_soon(channel.send, b"from server")
                    nursery.start_soon(channel.receive)

            await server_nursery.start(server_endpoint.serve, server_ctx, handler)

            client = client_endpoint.connect(
                server_endpoint.socket.getsockname(),
                client_ctx,
            )
            async with trio.open_nursery() as nursery:
                nursery.start_soon(client.send, b"from client")
                nursery.start_soon(client.receive)

            server_nursery.cancel_scope.cancel()


async def test_channel_closing() -> None:
    async with dtls_echo_server() as (_, address):
        with endpoint() as client_endpoint:
            client = client_endpoint.connect(address, client_ctx)
            await client.do_handshake()
            client.close()

            with pytest.raises(trio.ClosedResourceError):
                await client.send(b"abc")
            with pytest.raises(trio.ClosedResourceError):
                await client.receive()

            # close is idempotent
            client.close()
            # can also aclose
            await client.aclose()


async def test_serve_exits_cleanly_on_close() -> None:
    async with dtls_echo_server(autocancel=False) as (server_endpoint, _address):
        server_endpoint.close()
        # Testing that the nursery exits even without being cancelled
    # close is idempotent
    server_endpoint.close()


async def test_client_multiplex() -> None:
    async with dtls_echo_server() as (_, address1), dtls_echo_server() as (_, address2):
        with endpoint() as client_endpoint:
            client1 = client_endpoint.connect(address1, client_ctx)
            client2 = client_endpoint.connect(address2, client_ctx)

            await client1.send(b"abc")
            await client2.send(b"xyz")
            assert await client2.receive() == b"xyz"
            assert await client1.receive() == b"abc"

            client_endpoint.close()

            with pytest.raises(trio.ClosedResourceError):
                await client1.send(b"xxx")
            with pytest.raises(trio.ClosedResourceError):
                await client2.receive()
            with pytest.raises(trio.ClosedResourceError):
                client_endpoint.connect(address1, client_ctx)

            async def null_handler(_: object) -> None:  # pragma: no cover
                pass

            async with trio.open_nursery() as nursery:
                with pytest.raises(trio.ClosedResourceError):
                    await nursery.start(client_endpoint.serve, server_ctx, null_handler)


async def test_dtls_over_dgram_only() -> None:
    with trio.socket.socket() as s:
        with pytest.raises(ValueError, match=r"^DTLS requires a SOCK_DGRAM socket$"):
            DTLSEndpoint(s)


async def test_double_serve() -> None:
    async def null_handler(_: object) -> None:  # pragma: no cover
        pass

    with endpoint() as server_endpoint:
        await server_endpoint.socket.bind(("127.0.0.1", 0))
        async with trio.open_nursery() as nursery:
            await nursery.start(server_endpoint.serve, server_ctx, null_handler)
            with pytest.raises(trio.BusyResourceError):
                await nursery.start(server_endpoint.serve, server_ctx, null_handler)

            nursery.cancel_scope.cancel()

        async with trio.open_nursery() as nursery:
            await nursery.start(server_endpoint.serve, server_ctx, null_handler)
            nursery.cancel_scope.cancel()


async def test_connect_to_non_server(autojump_clock: trio.abc.Clock) -> None:
    fn = FakeNet()
    fn.enable()
    with endpoint() as client1, endpoint() as client2:
        await client1.socket.bind(("127.0.0.1", 0))
        # This should just time out
        with trio.move_on_after(100) as cscope:
            channel = client2.connect(client1.socket.getsockname(), client_ctx)
            await channel.do_handshake()
        assert cscope.cancelled_caught


async def test_incoming_buffer_overflow(autojump_clock: trio.abc.Clock) -> None:
    fn = FakeNet()
    fn.enable()
    for buffer_size in [10, 20]:
        async with dtls_echo_server() as (_, address):
            with endpoint(incoming_packets_buffer=buffer_size) as client_endpoint:
                assert client_endpoint.incoming_packets_buffer == buffer_size
                client = client_endpoint.connect(address, client_ctx)
                for i in range(buffer_size + 15):
                    await client.send(str(i).encode())
                    await trio.sleep(1)
                stats = client.statistics()
                assert stats.incoming_packets_dropped_in_trio == 15
                for i in range(buffer_size):
                    assert await client.receive() == str(i).encode()
                await client.send(b"buffer clear now")
                assert await client.receive() == b"buffer clear now"


async def test_server_socket_doesnt_crash_on_garbage(
    autojump_clock: trio.abc.Clock,
) -> None:
    fn = FakeNet()
    fn.enable()

    from trio._dtls import (
        ContentType,
        HandshakeFragment,
        HandshakeType,
        ProtocolVersion,
        Record,
        encode_handshake_fragment,
        encode_record,
    )

    client_hello = encode_record(
        Record(
            content_type=ContentType.handshake,
            version=ProtocolVersion.DTLS10,
            epoch_seqno=0,
            payload=encode_handshake_fragment(
                HandshakeFragment(
                    msg_type=HandshakeType.client_hello,
                    msg_len=10,
                    msg_seq=0,
                    frag_offset=0,
                    frag_len=10,
                    frag=bytes(10),
                ),
            ),
        ),
    )

    client_hello_extended = client_hello + b"\x00"
    client_hello_short = client_hello[:-1]
    # cuts off in middle of handshake message header
    client_hello_really_short = client_hello[:14]
    client_hello_corrupt_record_len = bytearray(client_hello)
    client_hello_corrupt_record_len[11] = 0xFF

    client_hello_fragmented = encode_record(
        Record(
            content_type=ContentType.handshake,
            version=ProtocolVersion.DTLS10,
            epoch_seqno=0,
            payload=encode_handshake_fragment(
                HandshakeFragment(
                    msg_type=HandshakeType.client_hello,
                    msg_len=20,
                    msg_seq=0,
                    frag_offset=0,
                    frag_len=10,
                    frag=bytes(10),
                ),
            ),
        ),
    )

    client_hello_trailing_data_in_record = encode_record(
        Record(
            content_type=ContentType.handshake,
            version=ProtocolVersion.DTLS10,
            epoch_seqno=0,
            payload=encode_handshake_fragment(
                HandshakeFragment(
                    msg_type=HandshakeType.client_hello,
                    msg_len=20,
                    msg_seq=0,
                    frag_offset=0,
                    frag_len=10,
                    frag=bytes(10),
                ),
            )
            + b"\x00",
        ),
    )

    handshake_empty = encode_record(
        Record(
            content_type=ContentType.handshake,
            version=ProtocolVersion.DTLS10,
            epoch_seqno=0,
            payload=b"",
        ),
    )

    client_hello_truncated_in_cookie = encode_record(
        Record(
            content_type=ContentType.handshake,
            version=ProtocolVersion.DTLS10,
            epoch_seqno=0,
            payload=bytes(2 + 32 + 1) + b"\xff",
        ),
    )

    async with dtls_echo_server() as (_, address):
        with trio.socket.socket(type=trio.socket.SOCK_DGRAM) as sock:
            for bad_packet in [
                b"",
                b"xyz",
                client_hello_extended,
                client_hello_short,
                client_hello_really_short,
                client_hello_corrupt_record_len,
                client_hello_fragmented,
                client_hello_trailing_data_in_record,
                handshake_empty,
                client_hello_truncated_in_cookie,
            ]:
                await sock.sendto(bad_packet, address)
                await trio.sleep(1)


async def test_invalid_cookie_rejected(autojump_clock: trio.abc.Clock) -> None:
    fn = FakeNet()
    fn.enable()

    from trio._dtls import BadPacket, decode_client_hello_untrusted

    with trio.CancelScope() as cscope:
        # the first 11 bytes of ClientHello aren't protected by the cookie, so only test
        # corrupting bytes after that.
        offset_to_corrupt = count(11)

        def route_packet(packet: UDPPacket) -> None:
            try:
                _, cookie, _ = decode_client_hello_untrusted(packet.payload)
            except BadPacket:
                pass
            else:
                if len(cookie) != 0:
                    # this is a challenge response packet
                    # let's corrupt the next offset so the handshake should fail
                    payload = bytearray(packet.payload)
                    offset = next(offset_to_corrupt)
                    if offset >= len(payload):
                        # We've tried all offsets. Clamp offset to the end of the
                        # payload, and terminate the test.
                        offset = len(payload) - 1
                        cscope.cancel()
                    payload[offset] ^= 0x01
                    packet = attrs.evolve(packet, payload=payload)

            fn.deliver_packet(packet)

        fn.route_packet = route_packet  # type: ignore[assignment]  # TODO: Fix FakeNet typing

        async with dtls_echo_server() as (_, address):
            while True:
                with endpoint() as client:
                    channel = client.connect(address, client_ctx)
                    await channel.do_handshake()
    assert cscope.cancelled_caught


async def test_client_cancels_handshake_and_starts_new_one(
    autojump_clock: trio.abc.Clock,
) -> None:
    # if a client disappears during the handshake, and then starts a new handshake from
    # scratch, then the first handler's channel should fail, and a new handler get
    # started
    fn = FakeNet()
    fn.enable()

    with endpoint() as server, endpoint() as client:
        await server.socket.bind(("127.0.0.1", 0))
        async with trio.open_nursery() as nursery:
            first_time = True

            async def handler(channel: DTLSChannel) -> None:
                nonlocal first_time
                if first_time:
                    first_time = False
                    print("handler: first time, cancelling connect")
                    connect_cscope.cancel()
                    await trio.sleep(0.5)
                    print("handler: handshake should fail now")
                    with pytest.raises(trio.BrokenResourceError):
                        await channel.do_handshake()
                else:
                    print("handler: not first time, sending hello")
                    await channel.send(b"hello")

            await nursery.start(server.serve, server_ctx, handler)

            print("client: starting first connect")
            with trio.CancelScope() as connect_cscope:
                channel = client.connect(server.socket.getsockname(), client_ctx)
                await channel.do_handshake()
            assert connect_cscope.cancelled_caught

            print("client: starting second connect")
            channel = client.connect(server.socket.getsockname(), client_ctx)
            assert await channel.receive() == b"hello"

            # Give handlers a chance to finish
            await trio.sleep(10)
            nursery.cancel_scope.cancel()


async def test_swap_client_server() -> None:
    with endpoint() as a, endpoint() as b:
        await a.socket.bind(("127.0.0.1", 0))
        await b.socket.bind(("127.0.0.1", 0))

        async def echo_handler(channel: DTLSChannel) -> None:
            async for packet in channel:
                await channel.send(packet)

        async def crashing_echo_handler(channel: DTLSChannel) -> None:
            with pytest.raises(trio.BrokenResourceError):
                await echo_handler(channel)

        async with trio.open_nursery() as nursery:
            await nursery.start(a.serve, server_ctx, crashing_echo_handler)
            await nursery.start(b.serve, server_ctx, echo_handler)

            b_to_a = b.connect(a.socket.getsockname(), client_ctx)
            await b_to_a.send(b"b as client")
            assert await b_to_a.receive() == b"b as client"

            a_to_b = a.connect(b.socket.getsockname(), client_ctx)
            await a_to_b.do_handshake()
            with pytest.raises(trio.BrokenResourceError):
                await b_to_a.send(b"association broken")
            await a_to_b.send(b"a as client")
            assert await a_to_b.receive() == b"a as client"

            nursery.cancel_scope.cancel()


@slow
async def test_openssl_retransmit_doesnt_break_stuff() -> None:
    # can't use autojump_clock here, because the point of the test is to wait for
    # openssl's built-in retransmit timer to expire, which is hard-coded to use
    # wall-clock time.
    fn = FakeNet()
    fn.enable()

    blackholed = True

    def route_packet(packet: UDPPacket) -> None:
        if blackholed:
            print("dropped packet", packet)
            return
        print("delivered packet", packet)
        # packets.append(
        #     scapy.all.IP(
        #         src=packet.source.ip.compressed, dst=packet.destination.ip.compressed
        #     )
        #     / scapy.all.UDP(sport=packet.source.port, dport=packet.destination.port)
        #     / packet.payload
        # )
        fn.deliver_packet(packet)

    fn.route_packet = route_packet  # type: ignore[assignment]  # TODO add type annotations for FakeNet

    async with dtls_echo_server() as (server_endpoint, address):
        with endpoint() as client_endpoint:
            async with trio.open_nursery() as nursery:

                async def connecter() -> None:
                    client = client_endpoint.connect(address, client_ctx)
                    await client.do_handshake(initial_retransmit_timeout=1.5)
                    await client.send(b"hi")
                    assert await client.receive() == b"hi"

                nursery.start_soon(connecter)

                # openssl's default timeout is 1 second, so this ensures that it thinks
                # the timeout has expired
                await trio.sleep(1.1)
                # disable blackholing and send a garbage packet to wake up openssl so it
                # notices the timeout has expired
                blackholed = False
                await server_endpoint.socket.sendto(
                    b"xxx",
                    client_endpoint.socket.getsockname(),
                )
                # now the client task should finish connecting and exit cleanly

    # scapy.all.wrpcap("/tmp/trace.pcap", packets)


async def test_initial_retransmit_timeout_configuration(
    autojump_clock: trio.abc.Clock,
) -> None:
    fn = FakeNet()
    fn.enable()

    blackholed = True

    def route_packet(packet: UDPPacket) -> None:
        nonlocal blackholed
        if blackholed:
            blackholed = False
        else:
            fn.deliver_packet(packet)

    fn.route_packet = route_packet  # type: ignore[assignment]  # TODO add type annotations for FakeNet

    async with dtls_echo_server() as (_, address):
        for t in [1, 2, 4]:
            with endpoint() as client:
                before = trio.current_time()
                blackholed = True
                channel = client.connect(address, client_ctx)
                await channel.do_handshake(initial_retransmit_timeout=t)
                after = trio.current_time()
                assert after - before == t


async def test_explicit_tiny_mtu_is_respected() -> None:
    # ClientHello is ~240 bytes, and it can't be fragmented, so our mtu has to
    # be larger than that. (300 is still smaller than any real network though.)
    MTU = 300

    fn = FakeNet()
    fn.enable()

    def route_packet(packet: UDPPacket) -> None:
        print(f"delivering {packet}")
        print(f"payload size: {len(packet.payload)}")
        assert len(packet.payload) <= MTU
        fn.deliver_packet(packet)

    fn.route_packet = route_packet  # type: ignore[assignment]  # TODO add type annotations for FakeNet

    async with dtls_echo_server(mtu=MTU) as (_server, address):
        with endpoint() as client:
            channel = client.connect(address, client_ctx)
            channel.set_ciphertext_mtu(MTU)
            await channel.do_handshake()
            await channel.send(b"hi")
            assert await channel.receive() == b"hi"


@parametrize_ipv6
async def test_handshake_handles_minimum_network_mtu(
    ipv6: bool,
    autojump_clock: trio.abc.Clock,
) -> None:
    # Fake network that has the minimum allowable MTU for whatever protocol we're using.
    fn = FakeNet()
    fn.enable()

    mtu = 1280 - 48 if ipv6 else 576 - 28

    def route_packet(packet: UDPPacket) -> None:
        if len(packet.payload) > mtu:
            print(f"dropping {packet}")
        else:
            print(f"delivering {packet}")
            fn.deliver_packet(packet)

    fn.route_packet = route_packet  # type: ignore[assignment]  # TODO add type annotations for FakeNet

    # See if we can successfully do a handshake -- some of the volleys will get dropped,
    # and the retransmit logic should detect this and back off the MTU to something
    # smaller until it succeeds.
    async with dtls_echo_server(ipv6=ipv6) as (_, address):
        with endpoint(ipv6=ipv6) as client_endpoint:
            client = client_endpoint.connect(address, client_ctx)
            # the handshake mtu backoff shouldn't affect the return value from
            # get_cleartext_mtu, b/c that's under the user's control via
            # set_ciphertext_mtu
            client.set_ciphertext_mtu(9999)
            await client.send(b"xyz")
            assert await client.receive() == b"xyz"
            assert client.get_cleartext_mtu() > 9000  # as vegeta said


@pytest.mark.filterwarnings("always:unclosed DTLS:ResourceWarning")
async def test_system_task_cleaned_up_on_gc() -> None:
    before_tasks = trio.lowlevel.current_statistics().tasks_living

    # We put this into a sub-function so that everything automatically becomes garbage
    # when the frame exits. For some reason just doing 'del e' wasn't enough on pypy
    # with coverage enabled -- I think we were hitting this bug:
    #     https://foss.heptapod.net/pypy/pypy/-/issues/3656
    async def start_and_forget_endpoint() -> int:
        e = endpoint()

        # This connection/handshake attempt can't succeed. The only purpose is to force
        # the endpoint to set up a receive loop.
        with trio.socket.socket(type=trio.socket.SOCK_DGRAM) as s:
            await s.bind(("127.0.0.1", 0))
            c = e.connect(s.getsockname(), client_ctx)
            async with trio.open_nursery() as nursery:
                nursery.start_soon(c.do_handshake)
                await trio.testing.wait_all_tasks_blocked()
                nursery.cancel_scope.cancel()

        during_tasks = trio.lowlevel.current_statistics().tasks_living
        return during_tasks

    with pytest.warns(ResourceWarning):  # noqa: PT031
        during_tasks = await start_and_forget_endpoint()
        await trio.testing.wait_all_tasks_blocked()
        gc_collect_harder()

    await trio.testing.wait_all_tasks_blocked()

    after_tasks = trio.lowlevel.current_statistics().tasks_living
    assert before_tasks < during_tasks
    assert before_tasks == after_tasks


@pytest.mark.filterwarnings("always:unclosed DTLS:ResourceWarning")
async def test_gc_before_system_task_starts() -> None:
    e = endpoint()

    with pytest.warns(ResourceWarning):  # noqa: PT031
        del e
        gc_collect_harder()

    await trio.testing.wait_all_tasks_blocked()


@pytest.mark.filterwarnings("always:unclosed DTLS:ResourceWarning")
async def test_gc_as_packet_received() -> None:
    fn = FakeNet()
    fn.enable()

    e = endpoint()
    await e.socket.bind(("127.0.0.1", 0))
    e._ensure_receive_loop()

    await trio.testing.wait_all_tasks_blocked()

    with trio.socket.socket(type=trio.socket.SOCK_DGRAM) as s:
        await s.sendto(b"xxx", e.socket.getsockname())
    # At this point, the endpoint's receive loop has been marked runnable because it
    # just received a packet; closing the endpoint socket won't interrupt that. But by
    # the time it wakes up to process the packet, the endpoint will be gone.
    with pytest.warns(ResourceWarning):  # noqa: PT031
        del e
        gc_collect_harder()


@pytest.mark.filterwarnings("always:unclosed DTLS:ResourceWarning")
def test_gc_after_trio_exits() -> None:
    async def main() -> DTLSEndpoint:
        # We use fakenet just to make sure no real sockets can leak out of the test
        # case - on pypy somehow the socket was outliving the gc_collect_harder call
        # below. Since the test is just making sure DTLSEndpoint.__del__ doesn't explode
        # when called after trio exits, it doesn't need a real socket.
        fn = FakeNet()
        fn.enable()
        return endpoint()

    e = trio.run(main)
    with pytest.warns(ResourceWarning):  # noqa: PT031
        del e
        gc_collect_harder()


async def test_already_closed_socket_doesnt_crash() -> None:
    with endpoint() as e:
        # We close the socket before checkpointing, so the socket will already be closed
        # when the system task starts up
        e.socket.close()
        # Now give it a chance to start up, and hopefully not crash
        await trio.testing.wait_all_tasks_blocked()


async def test_socket_closed_while_processing_clienthello(
    autojump_clock: trio.abc.Clock,
) -> None:
    fn = FakeNet()
    fn.enable()

    # Check what happens if the socket is discovered to be closed when sending a
    # HelloVerifyRequest, since that has its own sending logic
    async with dtls_echo_server() as (server, address):

        def route_packet(packet: UDPPacket) -> None:
            fn.deliver_packet(packet)
            server.socket.close()

        fn.route_packet = route_packet  # type: ignore[assignment]  # TODO add type annotations for FakeNet

        with endpoint() as client_endpoint:
            with trio.move_on_after(10):
                client = client_endpoint.connect(address, client_ctx)
                await client.do_handshake()


async def test_association_replaced_while_handshake_running(
    autojump_clock: trio.abc.Clock,
) -> None:
    fn = FakeNet()
    fn.enable()

    def route_packet(packet: UDPPacket) -> None:
        pass

    fn.route_packet = route_packet  # type: ignore[assignment]  # TODO add type annotations for FakeNet

    async with dtls_echo_server() as (_, address):
        with endpoint() as client_endpoint:
            c1 = client_endpoint.connect(address, client_ctx)
            async with trio.open_nursery() as nursery:

                async def doomed_handshake() -> None:
                    with pytest.raises(trio.BrokenResourceError):
                        await c1.do_handshake()

                nursery.start_soon(doomed_handshake)

                await trio.sleep(10)

                client_endpoint.connect(address, client_ctx)


async def test_association_replaced_before_handshake_starts() -> None:
    fn = FakeNet()
    fn.enable()

    # This test shouldn't send any packets
    def route_packet(packet: UDPPacket) -> NoReturn:  # pragma: no cover
        raise AssertionError()

    fn.route_packet = route_packet  # type: ignore[assignment]  # TODO add type annotations for FakeNet

    async with dtls_echo_server() as (_, address):
        with endpoint() as client_endpoint:
            c1 = client_endpoint.connect(address, client_ctx)
            client_endpoint.connect(address, client_ctx)
            with pytest.raises(trio.BrokenResourceError):
                await c1.do_handshake()


async def test_send_to_closed_local_port() -> None:
    # On Windows, sending a UDP packet to a closed local port can cause a weird
    # ECONNRESET error later, inside the receive task. Make sure we're handling it
    # properly.
    async with dtls_echo_server() as (_, address):
        with endpoint() as client_endpoint:
            async with trio.open_nursery() as nursery:
                for i in range(1, 10):
                    channel = client_endpoint.connect(("127.0.0.1", i), client_ctx)
                    nursery.start_soon(channel.do_handshake)
                channel = client_endpoint.connect(address, client_ctx)
                await channel.send(b"xxx")
                assert await channel.receive() == b"xxx"
                nursery.cancel_scope.cancel()

# === NexusCore/openenv\Lib\site-packages\astor\code_gen.py ===
# -*- coding: utf-8 -*-
"""
Part of the astor library for Python AST manipulation.

License: 3-clause BSD

Copyright (c) 2008      Armin Ronacher
Copyright (c) 2012-2017 Patrick Maupin
Copyright (c) 2013-2017 Berker Peksag

This module converts an AST into Python source code.

Before being version-controlled as part of astor,
this code came from here (in 2012):

    https://gist.github.com/1250562

"""

import ast
import inspect
import math
import sys

from .op_util import get_op_symbol, get_op_precedence, Precedence
from .node_util import ExplicitNodeVisitor
from .string_repr import pretty_string
from .source_repr import pretty_source


def to_source(node, indent_with=' ' * 4, add_line_information=False,
              pretty_string=pretty_string, pretty_source=pretty_source,
              source_generator_class=None):
    """This function can convert a node tree back into python sourcecode.
    This is useful for debugging purposes, especially if you're dealing with
    custom asts not generated by python itself.

    It could be that the sourcecode is evaluable when the AST itself is not
    compilable / evaluable.  The reason for this is that the AST contains some
    more data than regular sourcecode does, which is dropped during
    conversion.

    Each level of indentation is replaced with `indent_with`.  Per default this
    parameter is equal to four spaces as suggested by PEP 8, but it might be
    adjusted to match the application's styleguide.

    If `add_line_information` is set to `True` comments for the line numbers
    of the nodes are added to the output.  This can be used to spot wrong line
    number information of statement nodes.

    `source_generator_class` defaults to `SourceGenerator`, and specifies the
    class that will be instantiated and used to generate the source code.

    """
    if source_generator_class is None:
        source_generator_class = SourceGenerator
    elif not inspect.isclass(source_generator_class):
        raise TypeError('source_generator_class should be a class')
    elif not issubclass(source_generator_class, SourceGenerator):
        raise TypeError('source_generator_class should be a subclass of SourceGenerator')
    generator = source_generator_class(
        indent_with, add_line_information, pretty_string)
    generator.visit(node)
    generator.result.append('\n')
    if set(generator.result[0]) == set('\n'):
        generator.result[0] = ''
    return pretty_source(generator.result)


def precedence_setter(AST=ast.AST, get_op_precedence=get_op_precedence,
                      isinstance=isinstance, list=list):
    """ This only uses a closure for performance reasons,
        to reduce the number of attribute lookups.  (set_precedence
        is called a lot of times.)
    """

    def set_precedence(value, *nodes):
        """Set the precedence (of the parent) into the children.
        """
        if isinstance(value, AST):
            value = get_op_precedence(value)
        for node in nodes:
            if isinstance(node, AST):
                node._pp = value
            elif isinstance(node, list):
                set_precedence(value, *node)
            else:
                assert node is None, node

    return set_precedence


set_precedence = precedence_setter()


class Delimit(object):
    """A context manager that can add enclosing
       delimiters around the output of a
       SourceGenerator method.  By default, the
       parentheses are added, but the enclosed code
       may set discard=True to get rid of them.
    """

    discard = False

    def __init__(self, tree, *args):
        """ use write instead of using result directly
            for initial data, because it may flush
            preceding data into result.
        """
        delimiters = '()'
        node = None
        op = None
        for arg in args:
            if isinstance(arg, ast.AST):
                if node is None:
                    node = arg
                else:
                    op = arg
            else:
                delimiters = arg
        tree.write(delimiters[0])
        result = self.result = tree.result
        self.index = len(result)
        self.closing = delimiters[1]
        if node is not None:
            self.p = p = get_op_precedence(op or node)
            self.pp = pp = tree.get__pp(node)
            self.discard = p >= pp

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        result = self.result
        start = self.index - 1
        if self.discard:
            result[start] = ''
        else:
            result.append(self.closing)


class SourceGenerator(ExplicitNodeVisitor):
    """This visitor is able to transform a well formed syntax tree into Python
    sourcecode.

    For more details have a look at the docstring of the `node_to_source`
    function.

    """

    using_unicode_literals = False

    def __init__(self, indent_with, add_line_information=False,
                 pretty_string=pretty_string,
                 # constants
                 len=len, isinstance=isinstance, callable=callable):
        self.result = []
        self.indent_with = indent_with
        self.add_line_information = add_line_information
        self.indentation = 0  # Current indentation level
        self.new_lines = 0  # Number of lines to insert before next code
        self.colinfo = 0, 0  # index in result of string containing linefeed, and
                             # position of last linefeed in that string
        self.pretty_string = pretty_string
        AST = ast.AST

        visit = self.visit
        result = self.result
        append = result.append

        def write(*params):
            """ self.write is a closure for performance (to reduce the number
                of attribute lookups).
            """
            for item in params:
                if isinstance(item, AST):
                    visit(item)
                elif callable(item):
                    item()
                else:
                    if self.new_lines:
                        append('\n' * self.new_lines)
                        self.colinfo = len(result), 0
                        append(self.indent_with * self.indentation)
                        self.new_lines = 0
                    if item:
                        append(item)

        self.write = write

    def __getattr__(self, name, defaults=dict(keywords=(),
                    _pp=Precedence.highest).get):
        """ Get an attribute of the node.
            like dict.get (returns None if doesn't exist)
        """
        if not name.startswith('get_'):
            raise AttributeError
        geta = getattr
        shortname = name[4:]
        default = defaults(shortname)

        def getter(node):
            return geta(node, shortname, default)

        setattr(self, name, getter)
        return getter

    def delimit(self, *args):
        return Delimit(self, *args)

    def conditional_write(self, *stuff):
        if stuff[-1] is not None:
            self.write(*stuff)
            # Inform the caller that we wrote
            return True

    def newline(self, node=None, extra=0):
        self.new_lines = max(self.new_lines, 1 + extra)
        if node is not None and self.add_line_information:
            self.write('# line: %s' % node.lineno)
            self.new_lines = 1

    def body(self, statements):
        self.indentation += 1
        self.write(*statements)
        self.indentation -= 1

    def else_body(self, elsewhat):
        if elsewhat:
            self.write(self.newline, 'else:')
            self.body(elsewhat)

    def body_or_else(self, node):
        self.body(node.body)
        self.else_body(node.orelse)

    def visit_arguments(self, node):
        want_comma = []

        def write_comma():
            if want_comma:
                self.write(', ')
            else:
                want_comma.append(True)

        def loop_args(args, defaults):
            set_precedence(Precedence.Comma, defaults)
            padding = [None] * (len(args) - len(defaults))
            for arg, default in zip(args, padding + defaults):
                self.write(write_comma, arg)
                self.conditional_write('=', default)

        posonlyargs = getattr(node, 'posonlyargs', [])
        offset = 0
        if posonlyargs:
            offset += len(node.defaults) - len(node.args)
            loop_args(posonlyargs, node.defaults[:offset])
            self.write(write_comma, '/')

        loop_args(node.args, node.defaults[offset:])
        self.conditional_write(write_comma, '*', node.vararg)

        kwonlyargs = self.get_kwonlyargs(node)
        if kwonlyargs:
            if node.vararg is None:
                self.write(write_comma, '*')
            loop_args(kwonlyargs, node.kw_defaults)
        self.conditional_write(write_comma, '**', node.kwarg)

    def statement(self, node, *params, **kw):
        self.newline(node)
        self.write(*params)

    def decorators(self, node, extra):
        self.newline(extra=extra)
        for decorator in node.decorator_list:
            self.statement(decorator, '@', decorator)

    def comma_list(self, items, trailing=False):
        set_precedence(Precedence.Comma, *items)
        for idx, item in enumerate(items):
            self.write(', ' if idx else '', item)
        self.write(',' if trailing else '')

    # Statements

    def visit_Assign(self, node):
        set_precedence(node, node.value, *node.targets)
        self.newline(node)
        for target in node.targets:
            self.write(target, ' = ')
        self.visit(node.value)

    def visit_AugAssign(self, node):
        set_precedence(node, node.value, node.target)
        self.statement(node, node.target, get_op_symbol(node.op, ' %s= '),
                       node.value)

    def visit_AnnAssign(self, node):
        set_precedence(node, node.target, node.annotation)
        set_precedence(Precedence.Comma, node.value)
        need_parens = isinstance(node.target, ast.Name) and not node.simple
        begin = '(' if need_parens else ''
        end = ')' if need_parens else ''
        self.statement(node, begin, node.target, end, ': ', node.annotation)
        self.conditional_write(' = ', node.value)

    def visit_ImportFrom(self, node):
        self.statement(node, 'from ', node.level * '.',
                       node.module or '', ' import ')
        self.comma_list(node.names)
        # Goofy stuff for Python 2.7 _pyio module
        if node.module == '__future__' and 'unicode_literals' in (
                x.name for x in node.names):
            self.using_unicode_literals = True

    def visit_Import(self, node):
        self.statement(node, 'import ')
        self.comma_list(node.names)

    def visit_Expr(self, node):
        set_precedence(node, node.value)
        self.statement(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node, is_async=False):
        prefix = 'async ' if is_async else ''
        self.decorators(node, 1 if self.indentation else 2)
        self.statement(node, '%sdef %s' % (prefix, node.name), '(')
        self.visit_arguments(node.args)
        self.write(')')
        self.conditional_write(' ->', self.get_returns(node))
        self.write(':')
        self.body(node.body)
        if not self.indentation:
            self.newline(extra=2)

    # introduced in Python 3.5
    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node, is_async=True)

    def visit_ClassDef(self, node):
        have_args = []

        def paren_or_comma():
            if have_args:
                self.write(', ')
            else:
                have_args.append(True)
                self.write('(')

        self.decorators(node, 2)
        self.statement(node, 'class %s' % node.name)
        for base in node.bases:
            self.write(paren_or_comma, base)
        # keywords not available in early version
        for keyword in self.get_keywords(node):
            self.write(paren_or_comma, keyword.arg or '',
                       '=' if keyword.arg else '**', keyword.value)
        self.conditional_write(paren_or_comma, '*', self.get_starargs(node))
        self.conditional_write(paren_or_comma, '**', self.get_kwargs(node))
        self.write(have_args and '):' or ':')
        self.body(node.body)
        if not self.indentation:
            self.newline(extra=2)

    def visit_If(self, node):
        set_precedence(node, node.test)
        self.statement(node, 'if ', node.test, ':')
        self.body(node.body)
        while True:
            else_ = node.orelse
            if len(else_) == 1 and isinstance(else_[0], ast.If):
                node = else_[0]
                set_precedence(node, node.test)
                self.write(self.newline, 'elif ', node.test, ':')
                self.body(node.body)
            else:
                self.else_body(else_)
                break

    def visit_For(self, node, is_async=False):
        set_precedence(node, node.target)
        prefix = 'async ' if is_async else ''
        self.statement(node, '%sfor ' % prefix,
                       node.target, ' in ', node.iter, ':')
        self.body_or_else(node)

    # introduced in Python 3.5
    def visit_AsyncFor(self, node):
        self.visit_For(node, is_async=True)

    def visit_While(self, node):
        set_precedence(node, node.test)
        self.statement(node, 'while ', node.test, ':')
        self.body_or_else(node)

    def visit_With(self, node, is_async=False):
        prefix = 'async ' if is_async else ''
        self.statement(node, '%swith ' % prefix)
        if hasattr(node, "context_expr"):  # Python < 3.3
            self.visit_withitem(node)
        else:                              # Python >= 3.3
            self.comma_list(node.items)
        self.write(':')
        self.body(node.body)

    # new for Python 3.5
    def visit_AsyncWith(self, node):
        self.visit_With(node, is_async=True)

    # new for Python 3.3
    def visit_withitem(self, node):
        self.write(node.context_expr)
        self.conditional_write(' as ', node.optional_vars)

    # deprecated in Python 3.8
    def visit_NameConstant(self, node):
        self.write(repr(node.value))

    def visit_Pass(self, node):
        self.statement(node, 'pass')

    def visit_Print(self, node):
        # XXX: python 2.6 only
        self.statement(node, 'print ')
        values = node.values
        if node.dest is not None:
            self.write(' >> ')
            values = [node.dest] + node.values
        self.comma_list(values, not node.nl)

    def visit_Delete(self, node):
        self.statement(node, 'del ')
        self.comma_list(node.targets)

    def visit_TryExcept(self, node):
        self.statement(node, 'try:')
        self.body(node.body)
        self.write(*node.handlers)
        self.else_body(node.orelse)

    # new for Python 3.3
    def visit_Try(self, node):
        self.statement(node, 'try:')
        self.body(node.body)
        self.write(*node.handlers)
        self.else_body(node.orelse)
        if node.finalbody:
            self.statement(node, 'finally:')
            self.body(node.finalbody)

    def visit_ExceptHandler(self, node):
        self.statement(node, 'except')
        if self.conditional_write(' ', node.type):
            self.conditional_write(' as ', node.name)
        self.write(':')
        self.body(node.body)

    def visit_TryFinally(self, node):
        self.statement(node, 'try:')
        self.body(node.body)
        self.statement(node, 'finally:')
        self.body(node.finalbody)

    def visit_Exec(self, node):
        dicts = node.globals, node.locals
        dicts = dicts[::-1] if dicts[0] is None else dicts
        self.statement(node, 'exec ', node.body)
        self.conditional_write(' in ', dicts[0])
        self.conditional_write(', ', dicts[1])

    def visit_Assert(self, node):
        set_precedence(node, node.test, node.msg)
        self.statement(node, 'assert ', node.test)
        self.conditional_write(', ', node.msg)

    def visit_Global(self, node):
        self.statement(node, 'global ', ', '.join(node.names))

    def visit_Nonlocal(self, node):
        self.statement(node, 'nonlocal ', ', '.join(node.names))

    def visit_Return(self, node):
        set_precedence(node, node.value)
        self.statement(node, 'return')
        self.conditional_write(' ', node.value)

    def visit_Break(self, node):
        self.statement(node, 'break')

    def visit_Continue(self, node):
        self.statement(node, 'continue')

    def visit_Raise(self, node):
        # XXX: Python 2.6 / 3.0 compatibility
        self.statement(node, 'raise')
        if self.conditional_write(' ', self.get_exc(node)):
            self.conditional_write(' from ', node.cause)
        elif self.conditional_write(' ', self.get_type(node)):
            set_precedence(node, node.inst)
            self.conditional_write(', ', node.inst)
            self.conditional_write(', ', node.tback)

    # Expressions

    def visit_Attribute(self, node):
        self.write(node.value, '.', node.attr)

    def visit_Call(self, node, len=len):
        write = self.write
        want_comma = []

        def write_comma():
            if want_comma:
                write(', ')
            else:
                want_comma.append(True)

        args = node.args
        keywords = node.keywords
        starargs = self.get_starargs(node)
        kwargs = self.get_kwargs(node)
        numargs = len(args) + len(keywords)
        numargs += starargs is not None
        numargs += kwargs is not None
        p = Precedence.Comma if numargs > 1 else Precedence.call_one_arg
        set_precedence(p, *args)
        self.visit(node.func)
        write('(')
        for arg in args:
            write(write_comma, arg)

        set_precedence(Precedence.Comma, *(x.value for x in keywords))
        for keyword in keywords:
            # a keyword.arg of None indicates dictionary unpacking
            # (Python >= 3.5)
            arg = keyword.arg or ''
            write(write_comma, arg, '=' if arg else '**', keyword.value)
        # 3.5 no longer has these
        self.conditional_write(write_comma, '*', starargs)
        self.conditional_write(write_comma, '**', kwargs)
        write(')')

    def visit_Name(self, node):
        self.write(node.id)

    # ast.Constant is new in Python 3.6 and it replaces ast.Bytes,
    # ast.Ellipsis, ast.NameConstant, ast.Num, ast.Str in Python 3.8
    def visit_Constant(self, node):
        value = node.value

        if isinstance(value, (int, float, complex)):
            with self.delimit(node):
                self._handle_numeric_constant(value)
        elif isinstance(value, str):
            self._handle_string_constant(node, node.value)
        elif value is Ellipsis:
            self.write('...')
        else:
            self.write(repr(value))

    def visit_JoinedStr(self, node):
        self._handle_string_constant(node, None, is_joined=True)

    def _handle_string_constant(self, node, value, is_joined=False):
        # embedded is used to control when we might want
        # to use a triple-quoted string.  We determine
        # if we are in an assignment and/or in an expression
        precedence = self.get__pp(node)
        embedded = ((precedence > Precedence.Expr) +
                    (precedence >= Precedence.Assign))

        # Flush any pending newlines, because we're about
        # to severely abuse the result list.
        self.write('')
        result = self.result

        # Calculate the string representing the line
        # we are working on, up to but not including
        # the string we are adding.

        res_index, str_index = self.colinfo
        current_line = self.result[res_index:]
        if str_index:
            current_line[0] = current_line[0][str_index:]
        current_line = ''.join(current_line)

        has_ast_constant = sys.version_info >= (3, 6)

        if is_joined:
            # Handle new f-strings.  This is a bit complicated, because
            # the tree can contain subnodes that recurse back to JoinedStr
            # subnodes...

            def recurse(node):
                for value in node.values:
                    if isinstance(value, ast.Str):
                        # Double up braces to escape them.
                        self.write(value.s.replace('{', '{{').replace('}', '}}'))
                    elif isinstance(value, ast.FormattedValue):
                        with self.delimit('{}'):
                            # expr_text used for f-string debugging syntax.
                            if getattr(value, 'expr_text', None):
                                self.write(value.expr_text)
                            else:
                                set_precedence(value, value.value)
                                self.visit(value.value)
                            if value.conversion != -1:
                                self.write('!%s' % chr(value.conversion))
                            if value.format_spec is not None:
                                self.write(':')
                                recurse(value.format_spec)
                    elif has_ast_constant and isinstance(value, ast.Constant):
                        self.write(value.value)
                    else:
                        kind = type(value).__name__
                        assert False, 'Invalid node %s inside JoinedStr' % kind

            index = len(result)
            recurse(node)

            # Flush trailing newlines (so that they are part of mystr)
            self.write('')
            mystr = ''.join(result[index:])
            del result[index:]
            self.colinfo = res_index, str_index  # Put it back like we found it
            uni_lit = False  # No formatted byte strings

        else:
            assert value is not None, "Node value cannot be None"
            mystr = value
            uni_lit = self.using_unicode_literals

        mystr = self.pretty_string(mystr, embedded, current_line, uni_lit)

        if is_joined:
            mystr = 'f' + mystr
        elif getattr(node, 'kind', False):
            # Constant.kind is a Python 3.8 addition.
            mystr = node.kind + mystr

        self.write(mystr)

        lf = mystr.rfind('\n') + 1
        if lf:
            self.colinfo = len(result) - 1, lf

    # deprecated in Python 3.8
    def visit_Str(self, node):
        self._handle_string_constant(node, node.s)

    # deprecated in Python 3.8
    def visit_Bytes(self, node):
        self.write(repr(node.s))

    def _handle_numeric_constant(self, value):
        x = value

        def part(p, imaginary):
            # Represent infinity as 1e1000 and NaN as 1e1000-1e1000.
            s = 'j' if imaginary else ''
            try:
                if math.isinf(p):
                    if p < 0:
                        return '-1e1000' + s
                    return '1e1000' + s
                if math.isnan(p):
                    return '(1e1000%s-1e1000%s)' % (s, s)
            except OverflowError:
                # math.isinf will raise this when given an integer
                # that's too large to convert to a float.
                pass
            return repr(p) + s

        real = part(x.real if isinstance(x, complex) else x, imaginary=False)
        if isinstance(x, complex):
            imag = part(x.imag, imaginary=True)
            if x.real == 0:
                s = imag
            elif x.imag == 0:
                s = '(%s+0j)' % real
            else:
                # x has nonzero real and imaginary parts.
                s = '(%s%s%s)' % (real, ['+', ''][imag.startswith('-')], imag)
        else:
            s = real
        self.write(s)

    def visit_Num(self, node,
                  # constants
                  new=sys.version_info >= (3, 0)):
        with self.delimit(node) as delimiters:
            self._handle_numeric_constant(node.n)

            # We can leave the delimiters handling in visit_Num
            # since this is meant to handle a Python 2.x specific
            # issue and ast.Constant exists only in 3.6+

            # The Python 2.x compiler merges a unary minus
            # with a number.  This is a premature optimization
            # that we deal with here...
            if not new and delimiters.discard:
                if not isinstance(node.n, complex) and node.n < 0:
                    pow_lhs = Precedence.Pow + 1
                    delimiters.discard = delimiters.pp != pow_lhs
                else:
                    op = self.get__p_op(node)
                    delimiters.discard = not isinstance(op, ast.USub)

    def visit_Tuple(self, node):
        with self.delimit(node) as delimiters:
            # Two things are special about tuples:
            #   1) We cannot discard the enclosing parentheses if empty
            #   2) We need the trailing comma if only one item
            elts = node.elts
            delimiters.discard = delimiters.discard and elts
            self.comma_list(elts, len(elts) == 1)

    def visit_List(self, node):
        with self.delimit('[]'):
            self.comma_list(node.elts)

    def visit_Set(self, node):
        if node.elts:
            with self.delimit('{}'):
                self.comma_list(node.elts)
        else:
            # If we tried to use "{}" to represent an empty set, it would be
            # interpreted as an empty dictionary. We can't use "set()" either
            # because the name "set" might be rebound.
            self.write('{1}.__class__()')

    def visit_Dict(self, node):
        set_precedence(Precedence.Comma, *node.values)
        with self.delimit('{}'):
            for idx, (key, value) in enumerate(zip(node.keys, node.values)):
                self.write(', ' if idx else '',
                           key if key else '',
                           ': ' if key else '**', value)

    def visit_BinOp(self, node):
        op, left, right = node.op, node.left, node.right
        with self.delimit(node, op) as delimiters:
            ispow = isinstance(op, ast.Pow)
            p = delimiters.p
            set_precedence((Precedence.Pow + 1) if ispow else p, left)
            set_precedence(Precedence.PowRHS if ispow else (p + 1), right)
            self.write(left, get_op_symbol(op, ' %s '), right)

    def visit_BoolOp(self, node):
        with self.delimit(node, node.op) as delimiters:
            op = get_op_symbol(node.op, ' %s ')
            set_precedence(delimiters.p + 1, *node.values)
            for idx, value in enumerate(node.values):
                self.write(idx and op or '', value)

    def visit_Compare(self, node):
        with self.delimit(node, node.ops[0]) as delimiters:
            set_precedence(delimiters.p + 1, node.left, *node.comparators)
            self.visit(node.left)
            for op, right in zip(node.ops, node.comparators):
                self.write(get_op_symbol(op, ' %s '), right)

    # assignment expressions; new for Python 3.8
    def visit_NamedExpr(self, node):
        with self.delimit(node) as delimiters:
            p = delimiters.p
            set_precedence(p, node.target)
            set_precedence(p + 1, node.value)
            # Python is picky about delimiters for assignment
            # expressions: it requires at least one pair in any
            # statement that uses an assignment expression, even
            # when not necessary according to the precedence
            # rules. We address this with the kludge of forcing a
            # pair of parentheses around every assignment
            # expression.
            delimiters.discard = False
            self.write(node.target, ' := ', node.value)

    def visit_UnaryOp(self, node):
        with self.delimit(node, node.op) as delimiters:
            set_precedence(delimiters.p, node.operand)
            # In Python 2.x, a unary negative of a literal
            # number is merged into the number itself.  This
            # bit of ugliness means it is useful to know
            # what the parent operation was...
            node.operand._p_op = node.op
            sym = get_op_symbol(node.op)
            self.write(sym, ' ' if sym.isalpha() else '', node.operand)

    def visit_Subscript(self, node):
        set_precedence(node, node.slice)
        self.write(node.value, '[', node.slice, ']')

    def visit_Slice(self, node):
        set_precedence(node, node.lower, node.upper, node.step)
        self.conditional_write(node.lower)
        self.write(':')
        self.conditional_write(node.upper)
        if node.step is not None:
            self.write(':')
            if not (isinstance(node.step, ast.Name) and
                    node.step.id == 'None'):
                self.visit(node.step)

    def visit_Index(self, node):
        with self.delimit(node) as delimiters:
            set_precedence(delimiters.p, node.value)
            self.visit(node.value)

    def visit_ExtSlice(self, node):
        dims = node.dims
        set_precedence(node, *dims)
        self.comma_list(dims, len(dims) == 1)

    def visit_Yield(self, node):
        with self.delimit(node):
            set_precedence(get_op_precedence(node) + 1, node.value)
            self.write('yield')
            self.conditional_write(' ', node.value)

    # new for Python 3.3
    def visit_YieldFrom(self, node):
        with self.delimit(node):
            self.write('yield from ', node.value)

    # new for Python 3.5
    def visit_Await(self, node):
        with self.delimit(node):
            self.write('await ', node.value)

    def visit_Lambda(self, node):
        with self.delimit(node) as delimiters:
            set_precedence(delimiters.p, node.body)
            self.write('lambda ')
            self.visit_arguments(node.args)
            self.write(': ', node.body)

    def visit_Ellipsis(self, node):
        self.write('...')

    def visit_ListComp(self, node):
        with self.delimit('[]'):
            self.write(node.elt, *node.generators)

    def visit_GeneratorExp(self, node):
        with self.delimit(node) as delimiters:
            if delimiters.pp == Precedence.call_one_arg:
                delimiters.discard = True
            set_precedence(Precedence.Comma, node.elt)
            self.write(node.elt, *node.generators)

    def visit_SetComp(self, node):
        with self.delimit('{}'):
            self.write(node.elt, *node.generators)

    def visit_DictComp(self, node):
        with self.delimit('{}'):
            self.write(node.key, ': ', node.value, *node.generators)

    def visit_IfExp(self, node):
        with self.delimit(node) as delimiters:
            set_precedence(delimiters.p + 1, node.body, node.test)
            set_precedence(delimiters.p, node.orelse)
            self.write(node.body, ' if ', node.test, ' else ', node.orelse)

    def visit_Starred(self, node):
        self.write('*', node.value)

    def visit_Repr(self, node):
        # XXX: python 2.6 only
        with self.delimit('``'):
            self.visit(node.value)

    def visit_Module(self, node):
        self.write(*node.body)

    visit_Interactive = visit_Module

    def visit_Expression(self, node):
        self.visit(node.body)

    # Helper Nodes

    def visit_arg(self, node):
        self.write(node.arg)
        self.conditional_write(': ', node.annotation)

    def visit_alias(self, node):
        self.write(node.name)
        self.conditional_write(' as ', node.asname)

    def visit_comprehension(self, node):
        set_precedence(node, node.iter, *node.ifs)
        set_precedence(Precedence.comprehension_target, node.target)
        stmt = ' async for ' if self.get_is_async(node) else ' for '
        self.write(stmt, node.target, ' in ', node.iter)
        for if_ in node.ifs:
            self.write(' if ', if_)

# === NexusCore/openenv\Lib\site-packages\pyreadline3\console\console.py ===
# -*- coding: utf-8 -*-
# *****************************************************************************
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006-2020 Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#       Copyright (C) 2020 Bassem Girgis. <brgirgis@gmail.com>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# *****************************************************************************


from .event import Event

"""Cursor control and color for the Windows console.

This was modeled after the C extension of the same name by Fredrik Lundh.
"""

# primitive debug printing that won't interfere with the screen

import os
import re
import sys
import traceback

import pyreadline3.unicode_helper as unicode_helper
from pyreadline3.console.ansi import AnsiState, AnsiWriter
from pyreadline3.keysyms import KeyPress, make_KeyPress
from pyreadline3.logger import log
from pyreadline3.unicode_helper import ensure_str, ensure_unicode

try:
    import ctypes.util
    from ctypes import *
    from ctypes.wintypes import *

    from _ctypes import call_function
except ImportError:
    raise ImportError("You need ctypes to run this code")


def nolog(string):
    pass


log = nolog


# some constants we need
STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11
ENABLE_WINDOW_INPUT = 0x0008
ENABLE_MOUSE_INPUT = 0x0010
ENABLE_PROCESSED_INPUT = 0x0001
WHITE = 0x7
BLACK = 0
MENU_EVENT = 0x0008
KEY_EVENT = 0x0001
MOUSE_MOVED = 0x0001
MOUSE_EVENT = 0x0002
WINDOW_BUFFER_SIZE_EVENT = 0x0004
FOCUS_EVENT = 0x0010
MENU_EVENT = 0x0008
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
GENERIC_READ = int(0x80000000)
GENERIC_WRITE = 0x40000000

# Windows structures we'll need later


class COORD(Structure):
    _fields_ = [("X", c_short), ("Y", c_short)]


class SMALL_RECT(Structure):
    _fields_ = [
        ("Left", c_short),
        ("Top", c_short),
        ("Right", c_short),
        ("Bottom", c_short),
    ]


class CONSOLE_SCREEN_BUFFER_INFO(Structure):
    _fields_ = [
        ("dwSize", COORD),
        ("dwCursorPosition", COORD),
        ("wAttributes", c_short),
        ("srWindow", SMALL_RECT),
        ("dwMaximumWindowSize", COORD),
    ]


class CHAR_UNION(Union):
    _fields_ = [("UnicodeChar", c_wchar), ("AsciiChar", c_char)]


class CHAR_INFO(Structure):
    _fields_ = [("Char", CHAR_UNION), ("Attributes", c_short)]


class KEY_EVENT_RECORD(Structure):
    _fields_ = [
        ("bKeyDown", c_byte),
        ("pad2", c_byte),
        ("pad1", c_short),
        ("wRepeatCount", c_short),
        ("wVirtualKeyCode", c_short),
        ("wVirtualScanCode", c_short),
        ("uChar", CHAR_UNION),
        ("dwControlKeyState", c_int),
    ]


class MOUSE_EVENT_RECORD(Structure):
    _fields_ = [
        ("dwMousePosition", COORD),
        ("dwButtonState", c_int),
        ("dwControlKeyState", c_int),
        ("dwEventFlags", c_int),
    ]


class WINDOW_BUFFER_SIZE_RECORD(Structure):
    _fields_ = [("dwSize", COORD)]


class MENU_EVENT_RECORD(Structure):
    _fields_ = [("dwCommandId", c_uint)]


class FOCUS_EVENT_RECORD(Structure):
    _fields_ = [("bSetFocus", c_byte)]


class INPUT_UNION(Union):
    _fields_ = [
        ("KeyEvent", KEY_EVENT_RECORD),
        ("MouseEvent", MOUSE_EVENT_RECORD),
        ("WindowBufferSizeEvent", WINDOW_BUFFER_SIZE_RECORD),
        ("MenuEvent", MENU_EVENT_RECORD),
        ("FocusEvent", FOCUS_EVENT_RECORD),
    ]


class INPUT_RECORD(Structure):
    _fields_ = [("EventType", c_short), ("Event", INPUT_UNION)]


class CONSOLE_CURSOR_INFO(Structure):
    _fields_ = [("dwSize", c_int), ("bVisible", c_byte)]


# I didn't want to have to individually import these so I made a list, they are
# added to the Console class later in this file.

funcs = [
    "AllocConsole",
    "CreateConsoleScreenBuffer",
    "FillConsoleOutputAttribute",
    "FillConsoleOutputCharacterW",
    "FreeConsole",
    "GetConsoleCursorInfo",
    "GetConsoleMode",
    "GetConsoleScreenBufferInfo",
    "GetConsoleTitleW",
    "GetProcAddress",
    "GetStdHandle",
    "PeekConsoleInputW",
    "ReadConsoleInputW",
    "ScrollConsoleScreenBufferW",
    "SetConsoleActiveScreenBuffer",
    "SetConsoleCursorInfo",
    "SetConsoleCursorPosition",
    "SetConsoleMode",
    "SetConsoleScreenBufferSize",
    "SetConsoleTextAttribute",
    "SetConsoleTitleW",
    "SetConsoleWindowInfo",
    "WriteConsoleW",
    "WriteConsoleOutputCharacterW",
    "WriteFile",
]

# I don't want events for these keys, they are just a bother for my application
key_modifiers = {
    VK_SHIFT: 1,
    VK_CONTROL: 1,
    VK_MENU: 1,  # alt key
    0x5B: 1,  # windows key
}


def split_block(text, size=1000):
    return [text[start : start + size] for start in range(0, len(text), size)]


class Console(object):
    """Console driver for Windows."""

    def __init__(self, newbuffer=0):
        """Initialize the Console object.

        newbuffer=1 will allocate a new buffer so the old content will be restored
        on exit.
        """
        # Do I need the following line? It causes a console to be created whenever
        # readline is imported into a pythonw application which seems wrong. Things
        # seem to work without it...
        # self.AllocConsole()

        if newbuffer:
            self.hout = self.CreateConsoleScreenBuffer(
                GENERIC_READ | GENERIC_WRITE, 0, None, 1, None
            )
            self.SetConsoleActiveScreenBuffer(self.hout)
        else:
            self.hout = self.GetStdHandle(STD_OUTPUT_HANDLE)

        self.hin = self.GetStdHandle(STD_INPUT_HANDLE)
        self.inmode = DWORD(0)
        self.GetConsoleMode(self.hin, byref(self.inmode))
        self.SetConsoleMode(self.hin, 0xF)
        info = CONSOLE_SCREEN_BUFFER_INFO()
        self.GetConsoleScreenBufferInfo(self.hout, byref(info))
        self.attr = info.wAttributes
        self.saveattr = info.wAttributes  # remember the initial colors
        self.defaultstate = AnsiState()
        self.defaultstate.winattr = info.wAttributes
        self.ansiwriter = AnsiWriter(self.defaultstate)

        background = self.attr & 0xF0
        for escape in self.escape_to_color:
            if self.escape_to_color[escape] is not None:
                self.escape_to_color[escape] |= background
        log("initial attr=%x" % self.attr)
        self.softspace = 0  # this is for using it as a file-like object
        self.serial = 0

        self.pythondll = ctypes.pythonapi
        self.inputHookPtr = c_void_p.from_address(
            addressof(self.pythondll.PyOS_InputHook)
        ).value

        self.pythondll.PyMem_RawMalloc.restype = c_size_t
        self.pythondll.PyMem_RawMalloc.argtypes = [c_size_t]
        setattr(Console, "PyMem_Malloc", self.pythondll.PyMem_RawMalloc)

    def __del__(self):
        """Cleanup the console when finished."""
        # I don't think this ever gets called
        self.SetConsoleTextAttribute(self.hout, self.saveattr)
        self.SetConsoleMode(self.hin, self.inmode)
        self.FreeConsole()

    def _get_top_bot(self):
        info = CONSOLE_SCREEN_BUFFER_INFO()
        self.GetConsoleScreenBufferInfo(self.hout, byref(info))
        rect = info.srWindow
        top = rect.Top
        bot = rect.Bottom
        return top, bot

    def fixcoord(self, x, y):
        """Return a long with x and y packed inside,
        also handle negative x and y."""
        if x < 0 or y < 0:
            info = CONSOLE_SCREEN_BUFFER_INFO()
            self.GetConsoleScreenBufferInfo(self.hout, byref(info))
            if x < 0:
                x = info.srWindow.Right - x
                y = info.srWindow.Bottom + y

        # this is a hack! ctypes won't pass structures but COORD is
        # just like a long, so this works.
        return c_int(y << 16 | x)

    def pos(self, x=None, y=None):
        """Move or query the window cursor."""
        if x is None:
            info = CONSOLE_SCREEN_BUFFER_INFO()
            self.GetConsoleScreenBufferInfo(self.hout, byref(info))
            return (info.dwCursorPosition.X, info.dwCursorPosition.Y)
        else:
            return self.SetConsoleCursorPosition(self.hout, self.fixcoord(x, y))

    def home(self):
        """Move to home."""
        self.pos(0, 0)

    # Map ANSI color escape sequences into Windows Console Attributes

    terminal_escape = re.compile("(\001?\033\\[[0-9;]+m\002?)")
    escape_parts = re.compile("\001?\033\\[([0-9;]+)m\002?")
    escape_to_color = {
        "0;30": 0x0,  # black
        "0;31": 0x4,  # red
        "0;32": 0x2,  # green
        "0;33": 0x4 + 0x2,  # brown?
        "0;34": 0x1,  # blue
        "0;35": 0x1 + 0x4,  # purple
        "0;36": 0x2 + 0x4,  # cyan
        "0;37": 0x1 + 0x2 + 0x4,  # grey
        "1;30": 0x1 + 0x2 + 0x4,  # dark gray
        "1;31": 0x4 + 0x8,  # red
        "1;32": 0x2 + 0x8,  # light green
        "1;33": 0x4 + 0x2 + 0x8,  # yellow
        "1;34": 0x1 + 0x8,  # light blue
        "1;35": 0x1 + 0x4 + 0x8,  # light purple
        "1;36": 0x1 + 0x2 + 0x8,  # light cyan
        "1;37": 0x1 + 0x2 + 0x4 + 0x8,  # white
        "0": None,
    }

    # This pattern should match all characters that change the cursor position differently
    # than a normal character.
    motion_char_re = re.compile("([\n\r\t\010\007])")

    def write_scrolling(self, text, attr=None):
        """write text at current cursor position while watching for scrolling.

        If the window scrolls because you are at the bottom of the screen
        buffer, all positions that you are storing will be shifted by the
        scroll amount. For example, I remember the cursor position of the
        prompt so that I can redraw the line but if the window scrolls,
        the remembered position is off.

        This variant of write tries to keep track of the cursor position
        so that it will know when the screen buffer is scrolled. It
        returns the number of lines that the buffer scrolled.

        """
        text = ensure_unicode(text)
        x, y = self.pos()
        w, h = self.size()
        scroll = 0  # the result
        # split the string into ordinary characters and funny characters
        chunks = self.motion_char_re.split(text)
        for chunk in chunks:
            n = self.write_color(chunk, attr)
            if len(chunk) == 1:  # the funny characters will be alone
                if chunk[0] == "\n":  # newline
                    x = 0
                    y += 1
                elif chunk[0] == "\r":  # carriage return
                    x = 0
                elif chunk[0] == "\t":  # tab
                    x = 8 * (int(x / 8) + 1)
                    if x > w:  # newline
                        x -= w
                        y += 1
                elif chunk[0] == "\007":  # bell
                    pass
                elif chunk[0] == "\010":
                    x -= 1
                    if x < 0:
                        y -= 1  # backed up 1 line
                else:  # ordinary character
                    x += 1
                if x == w:  # wrap
                    x = 0
                    y += 1
                if y == h:  # scroll
                    scroll += 1
                    y = h - 1
            else:  # chunk of ordinary characters
                x += n
                l = int(x / w)  # lines we advanced
                x = x % w  # new x value
                y += l
                if y >= h:  # scroll
                    scroll += y - h + 1
                    y = h - 1
        return scroll

    def write_color(self, text, attr=None):
        text = ensure_unicode(text)
        n, res = self.ansiwriter.write_color(text, attr)
        junk = DWORD(0)
        for attr, chunk in res:
            log("console.attr:%s" % (attr))
            log("console.chunk:%s" % (chunk))
            self.SetConsoleTextAttribute(self.hout, attr.winattr)
            for short_chunk in split_block(chunk):
                self.WriteConsoleW(
                    self.hout, short_chunk, len(short_chunk), byref(junk), None
                )
        return n

    def write_plain(self, text, attr=None):
        """write text at current cursor position."""
        text = ensure_unicode(text)
        log('write("%s", %s)' % (text, attr))
        if attr is None:
            attr = self.attr
        junk = DWORD(0)
        self.SetConsoleTextAttribute(self.hout, attr)
        for short_chunk in split_block(chunk):
            self.WriteConsoleW(
                self.hout,
                ensure_unicode(short_chunk),
                len(short_chunk),
                byref(junk),
                None,
            )
        return len(text)

    # This function must be used to ensure functioning with EMACS
    # Emacs sets the EMACS environment variable
    if "EMACS" in os.environ:

        def write_color(self, text, attr=None):
            text = ensure_str(text)
            junk = DWORD(0)
            self.WriteFile(self.hout, text, len(text), byref(junk), None)
            return len(text)

        write_plain = write_color

    # make this class look like a file object
    def write(self, text):
        text = ensure_unicode(text)
        log('write("%s")' % text)
        return self.write_color(text)

    # write = write_scrolling

    def isatty(self):
        return True

    def flush(self):
        pass

    def page(self, attr=None, fill=" "):
        """Fill the entire screen."""
        if attr is None:
            attr = self.attr
        if len(fill) != 1:
            raise ValueError
        info = CONSOLE_SCREEN_BUFFER_INFO()
        self.GetConsoleScreenBufferInfo(self.hout, byref(info))
        if info.dwCursorPosition.X != 0 or info.dwCursorPosition.Y != 0:
            self.SetConsoleCursorPosition(self.hout, self.fixcoord(0, 0))

        w = info.dwSize.X
        n = DWORD(0)
        for y in range(info.dwSize.Y):
            self.FillConsoleOutputAttribute(
                self.hout, attr, w, self.fixcoord(0, y), byref(n)
            )
            self.FillConsoleOutputCharacterW(
                self.hout, ord(fill[0]), w, self.fixcoord(0, y), byref(n)
            )

        self.attr = attr

    def text(self, x, y, text, attr=None):
        """Write text at the given position."""
        if attr is None:
            attr = self.attr

        pos = self.fixcoord(x, y)
        n = DWORD(0)
        self.WriteConsoleOutputCharacterW(self.hout, text, len(text), pos, byref(n))
        self.FillConsoleOutputAttribute(self.hout, attr, n, pos, byref(n))

    def clear_to_end_of_window(self):
        top, bot = self._get_top_bot()
        pos = self.pos()
        w, h = self.size()
        self.rectangle((pos[0], pos[1], w, pos[1] + 1))
        if pos[1] < bot:
            self.rectangle((0, pos[1] + 1, w, bot + 1))

    def rectangle(self, rect, attr=None, fill=" "):
        """Fill Rectangle."""
        x0, y0, x1, y1 = rect
        n = DWORD(0)
        if attr is None:
            attr = self.attr
        for y in range(y0, y1):
            pos = self.fixcoord(x0, y)
            self.FillConsoleOutputAttribute(self.hout, attr, x1 - x0, pos, byref(n))
            self.FillConsoleOutputCharacterW(
                self.hout, ord(fill[0]), x1 - x0, pos, byref(n)
            )

    def scroll(self, rect, dx, dy, attr=None, fill=" "):
        """Scroll a rectangle."""
        if attr is None:
            attr = self.attr
        x0, y0, x1, y1 = rect
        source = SMALL_RECT(x0, y0, x1 - 1, y1 - 1)
        dest = self.fixcoord(x0 + dx, y0 + dy)
        style = CHAR_INFO()
        style.Char.AsciiChar = ensure_str(fill[0])
        style.Attributes = attr

        return self.ScrollConsoleScreenBufferW(
            self.hout, byref(source), byref(source), dest, byref(style)
        )

    def scroll_window(self, lines):
        """Scroll the window by the indicated number of lines."""
        info = CONSOLE_SCREEN_BUFFER_INFO()
        self.GetConsoleScreenBufferInfo(self.hout, byref(info))
        rect = info.srWindow
        log("sw: rtop=%d rbot=%d" % (rect.Top, rect.Bottom))
        top = rect.Top + lines
        bot = rect.Bottom + lines
        h = bot - top
        maxbot = info.dwSize.Y - 1
        if top < 0:
            top = 0
            bot = h
        if bot > maxbot:
            bot = maxbot
            top = bot - h

        nrect = SMALL_RECT()
        nrect.Top = top
        nrect.Bottom = bot
        nrect.Left = rect.Left
        nrect.Right = rect.Right
        log("sn: top=%d bot=%d" % (top, bot))
        r = self.SetConsoleWindowInfo(self.hout, True, byref(nrect))
        log("r=%d" % r)

    def get(self):
        """Get next event from queue."""
        inputHookFunc = c_void_p.from_address(self.inputHookPtr).value

        Cevent = INPUT_RECORD()
        count = DWORD(0)
        while True:
            if inputHookFunc:
                call_function(inputHookFunc, ())
            status = self.ReadConsoleInputW(self.hin, byref(Cevent), 1, byref(count))
            if status and count.value == 1:
                e = event(self, Cevent)
                return e

    def getkeypress(self):
        """Return next key press event from the queue, ignoring others."""
        while True:
            e = self.get()
            if e.type == "KeyPress" and e.keycode not in key_modifiers:
                log("console.getkeypress %s" % e)
                if e.keyinfo.keyname == "next":
                    self.scroll_window(12)
                elif e.keyinfo.keyname == "prior":
                    self.scroll_window(-12)
                else:
                    return e
            elif (e.type == "KeyRelease") and (
                e.keyinfo == KeyPress("S", False, True, False, "S")
                or e.keyinfo == KeyPress("C", False, True, False, "C")
            ):
                log("getKeypress:%s,%s,%s" % (e.keyinfo, e.keycode, e.type))
                return e

    def getchar(self):
        """Get next character from queue."""

        Cevent = INPUT_RECORD()
        count = DWORD(0)
        while True:
            status = self.ReadConsoleInputW(self.hin, byref(Cevent), 1, byref(count))
            if (
                status
                and (count.value == 1)
                and (Cevent.EventType == 1)
                and Cevent.Event.KeyEvent.bKeyDown
            ):
                sym = keysym(Cevent.Event.KeyEvent.wVirtualKeyCode)
                if len(sym) == 0:
                    sym = Cevent.Event.KeyEvent.uChar.AsciiChar
                return sym

    def peek(self):
        """Check event queue."""
        Cevent = INPUT_RECORD()
        count = DWORD(0)
        status = self.PeekConsoleInputW(self.hin, byref(Cevent), 1, byref(count))
        if status and count == 1:
            return event(self, Cevent)

    def title(self, txt=None):
        """Set/get title."""
        if txt:
            self.SetConsoleTitleW(txt)
        else:
            buffer = create_unicode_buffer(200)
            n = self.GetConsoleTitleW(buffer, 200)
            if n > 0:
                return buffer.value[:n]

    def size(self, width=None, height=None):
        """Set/get window size."""
        info = CONSOLE_SCREEN_BUFFER_INFO()
        status = self.GetConsoleScreenBufferInfo(self.hout, byref(info))
        if not status:
            return None
        if width is not None and height is not None:
            wmin = info.srWindow.Right - info.srWindow.Left + 1
            hmin = info.srWindow.Bottom - info.srWindow.Top + 1
            # print wmin, hmin
            width = max(width, wmin)
            height = max(height, hmin)
            # print width, height
            self.SetConsoleScreenBufferSize(self.hout, self.fixcoord(width, height))
        else:
            return (info.dwSize.X, info.dwSize.Y)

    def cursor(self, visible=None, size=None):
        """Set cursor on or off."""
        info = CONSOLE_CURSOR_INFO()
        if self.GetConsoleCursorInfo(self.hout, byref(info)):
            if visible is not None:
                info.bVisible = visible
            if size is not None:
                info.dwSize = size
            self.SetConsoleCursorInfo(self.hout, byref(info))

    def bell(self):
        self.write("\007")

    def next_serial(self):
        """Get next event serial number."""
        self.serial += 1
        return self.serial


# add the functions from the dll to the class
for func in funcs:
    setattr(Console, func, getattr(windll.kernel32, func))


_strncpy = ctypes.windll.kernel32.lstrcpynA
_strncpy.restype = c_char_p
_strncpy.argtypes = [c_char_p, c_char_p, c_size_t]


LPVOID = c_void_p
LPCVOID = c_void_p
FARPROC = c_void_p
LPDWORD = POINTER(DWORD)

Console.AllocConsole.restype = BOOL
Console.AllocConsole.argtypes = []  # void
Console.CreateConsoleScreenBuffer.restype = HANDLE
Console.CreateConsoleScreenBuffer.argtypes = [
    DWORD,
    DWORD,
    c_void_p,
    DWORD,
    LPVOID,
]  # DWORD, DWORD, SECURITY_ATTRIBUTES*, DWORD, LPVOID
Console.FillConsoleOutputAttribute.restype = BOOL
Console.FillConsoleOutputAttribute.argtypes = [
    HANDLE,
    WORD,
    DWORD,
    c_int,
    LPDWORD,
]  # HANDLE, WORD, DWORD, COORD, LPDWORD
Console.FillConsoleOutputCharacterW.restype = BOOL
Console.FillConsoleOutputCharacterW.argtypes = [
    HANDLE,
    c_ushort,
    DWORD,
    c_int,
    LPDWORD,
]  # HANDLE, TCHAR, DWORD, COORD, LPDWORD
Console.FreeConsole.restype = BOOL
Console.FreeConsole.argtypes = []  # void
Console.GetConsoleCursorInfo.restype = BOOL
Console.GetConsoleCursorInfo.argtypes = [
    HANDLE,
    c_void_p,
]  # HANDLE, PCONSOLE_CURSOR_INFO
Console.GetConsoleMode.restype = BOOL
Console.GetConsoleMode.argtypes = [HANDLE, LPDWORD]  # HANDLE, LPDWORD
Console.GetConsoleScreenBufferInfo.restype = BOOL
Console.GetConsoleScreenBufferInfo.argtypes = [
    HANDLE,
    c_void_p,
]  # HANDLE, PCONSOLE_SCREEN_BUFFER_INFO
Console.GetConsoleTitleW.restype = DWORD
Console.GetConsoleTitleW.argtypes = [c_wchar_p, DWORD]  # LPTSTR , DWORD
Console.GetProcAddress.restype = FARPROC
Console.GetProcAddress.argtypes = [HMODULE, c_char_p]  # HMODULE , LPCSTR
Console.GetStdHandle.restype = HANDLE
Console.GetStdHandle.argtypes = [DWORD]
Console.PeekConsoleInputW.restype = BOOL
# HANDLE, PINPUT_RECORD, DWORD, LPDWORD
Console.PeekConsoleInputW.argtypes = [HANDLE, c_void_p, DWORD, LPDWORD]
Console.ReadConsoleInputW.restype = BOOL
# HANDLE, PINPUT_RECORD, DWORD, LPDWORD
Console.ReadConsoleInputW.argtypes = [HANDLE, c_void_p, DWORD, LPDWORD]
Console.ScrollConsoleScreenBufferW.restype = BOOL
Console.ScrollConsoleScreenBufferW.argtypes = [
    HANDLE,
    c_void_p,
    c_void_p,
    c_int,
    c_void_p,
]  # HANDLE, SMALL_RECT*, SMALL_RECT*, COORD, LPDWORD
Console.SetConsoleActiveScreenBuffer.restype = BOOL
Console.SetConsoleActiveScreenBuffer.argtypes = [HANDLE]  # HANDLE
Console.SetConsoleCursorInfo.restype = BOOL
Console.SetConsoleCursorInfo.argtypes = [
    HANDLE,
    c_void_p,
]  # HANDLE, CONSOLE_CURSOR_INFO*
Console.SetConsoleCursorPosition.restype = BOOL
Console.SetConsoleCursorPosition.argtypes = [HANDLE, c_int]  # HANDLE, COORD
Console.SetConsoleMode.restype = BOOL
Console.SetConsoleMode.argtypes = [HANDLE, DWORD]  # HANDLE, DWORD
Console.SetConsoleScreenBufferSize.restype = BOOL
Console.SetConsoleScreenBufferSize.argtypes = [HANDLE, c_int]  # HANDLE, COORD
Console.SetConsoleTextAttribute.restype = BOOL
Console.SetConsoleTextAttribute.argtypes = [HANDLE, WORD]  # HANDLE, WORD
Console.SetConsoleTitleW.restype = BOOL
Console.SetConsoleTitleW.argtypes = [c_wchar_p]  # LPCTSTR
Console.SetConsoleWindowInfo.restype = BOOL
Console.SetConsoleWindowInfo.argtypes = [
    HANDLE,
    BOOL,
    c_void_p,
]  # HANDLE, BOOL, SMALL_RECT*
Console.WriteConsoleW.restype = BOOL
# HANDLE, VOID*, DWORD, LPDWORD, LPVOID
Console.WriteConsoleW.argtypes = [HANDLE, c_void_p, DWORD, LPDWORD, LPVOID]
Console.WriteConsoleOutputCharacterW.restype = BOOL
Console.WriteConsoleOutputCharacterW.argtypes = [
    HANDLE,
    c_wchar_p,
    DWORD,
    c_int,
    LPDWORD,
]  # HANDLE, LPCTSTR, DWORD, COORD, LPDWORD
Console.WriteFile.restype = BOOL
# HANDLE, LPCVOID , DWORD, LPDWORD , LPOVERLAPPED
Console.WriteFile.argtypes = [HANDLE, LPCVOID, DWORD, LPDWORD, c_void_p]


VkKeyScan = windll.user32.VkKeyScanA


class event(Event):
    """Represent events from the console."""

    def __init__(self, console, input):
        """Initialize an event from the Windows input structure."""
        self.type = "??"
        self.serial = console.next_serial()
        self.width = 0
        self.height = 0
        self.x = 0
        self.y = 0
        self.char = ""
        self.keycode = 0
        self.keysym = "??"
        # a tuple with (control, meta, shift, keycode) for dispatch
        self.keyinfo = None
        self.width = None

        if input.EventType == KEY_EVENT:
            if input.Event.KeyEvent.bKeyDown:
                self.type = "KeyPress"
            else:
                self.type = "KeyRelease"
            self.char = input.Event.KeyEvent.uChar.UnicodeChar
            self.keycode = input.Event.KeyEvent.wVirtualKeyCode
            self.state = input.Event.KeyEvent.dwControlKeyState
            self.keyinfo = make_KeyPress(self.char, self.state, self.keycode)

        elif input.EventType == MOUSE_EVENT:
            if input.Event.MouseEvent.dwEventFlags & MOUSE_MOVED:
                self.type = "Motion"
            else:
                self.type = "Button"
            self.x = input.Event.MouseEvent.dwMousePosition.X
            self.y = input.Event.MouseEvent.dwMousePosition.Y
            self.state = input.Event.MouseEvent.dwButtonState
        elif input.EventType == WINDOW_BUFFER_SIZE_EVENT:
            self.type = "Configure"
            self.width = input.Event.WindowBufferSizeEvent.dwSize.X
            self.height = input.Event.WindowBufferSizeEvent.dwSize.Y
        elif input.EventType == FOCUS_EVENT:
            if input.Event.FocusEvent.bSetFocus:
                self.type = "FocusIn"
            else:
                self.type = "FocusOut"
        elif input.EventType == MENU_EVENT:
            self.type = "Menu"
            self.state = input.Event.MenuEvent.dwCommandId


def getconsole(buffer=1):
    """Get a console handle.

    If buffer is non-zero, a new console buffer is allocated and
    installed.  Otherwise, this returns a handle to the current
    console buffer"""

    c = Console(buffer)

    return c


# The following code uses ctypes to allow a Python callable to
# substitute for GNU readline within the Python interpreter. Calling
# raw_input or other functions that do input, inside your callable
# might be a bad idea, then again, it might work.

# The Python callable can raise EOFError or KeyboardInterrupt and
# these will be translated into the appropriate outputs from readline
# so that they will then be translated back!

# If the Python callable raises any other exception, a traceback will
# be printed and readline will appear to return an empty line.

# I use ctypes to create a C-callable from a Python wrapper that
# handles the exceptions and gets the result into the right form.


# the type for our C-callable wrapper
HOOKFUNC23 = CFUNCTYPE(c_char_p, c_void_p, c_void_p, c_char_p)

readline_hook = None  # the python hook goes here
readline_ref = None  # reference to the c-callable to keep it alive


def hook_wrapper_23(stdin, stdout, prompt):
    """Wrap a Python readline so it behaves like GNU readline."""
    try:
        # call the Python hook
        res = ensure_str(readline_hook(prompt))
        # make sure it returned the right sort of thing
        if res and not isinstance(res, bytes):
            raise TypeError("readline must return a string.")
    except KeyboardInterrupt:
        # GNU readline returns 0 on keyboard interrupt
        return 0
    except EOFError:
        # It returns an empty string on EOF
        res = ensure_str("")
    except BaseException:
        print("Readline internal error", file=sys.stderr)
        traceback.print_exc()
        res = ensure_str("\n")
    # we have to make a copy because the caller expects to free the result
    n = len(res)
    p = Console.PyMem_Malloc(n + 1)
    _strncpy(cast(p, c_char_p), res, n + 1)
    return p


def install_readline(hook):
    """Set up things for the interpreter to call
    our function like GNU readline."""
    global readline_hook, readline_ref
    # save the hook so the wrapper can call it
    readline_hook = hook
    # get the address of PyOS_ReadlineFunctionPointer so we can update it
    PyOS_RFP = c_void_p.from_address(
        Console.GetProcAddress(
            sys.dllhandle, "PyOS_ReadlineFunctionPointer".encode("ascii")
        )
    )
    # save a reference to the generated C-callable so it doesn't go away
    readline_ref = HOOKFUNC23(hook_wrapper_23)
    # get the address of the function
    func_start = c_void_p.from_address(addressof(readline_ref)).value
    # write the function address into PyOS_ReadlineFunctionPointer
    PyOS_RFP.value = func_start


if __name__ == "__main__":
    import sys
    import time

    def p(char):
        return chr(VkKeyScan(ord(char)) & 0xFF)

    c = Console(0)
    sys.stdout = c
    sys.stderr = c
    c.page()
    print(p("d"), p("D"))
    c.pos(5, 10)
    c.write("hi there")
    print("some printed output")
    for i in range(10):
        q = c.getkeypress()
        print(q)
    del c

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\utils\_cache_manager.py ===
# coding=utf-8
# Copyright 2022-present, the HuggingFace Inc. team.
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
"""Contains utilities to manage the HF cache directory."""

import os
import shutil
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, List, Literal, Optional, Set, Union

from huggingface_hub.errors import CacheNotFound, CorruptedCacheException

from ..commands._cli_utils import tabulate
from ..constants import HF_HUB_CACHE
from . import logging


logger = logging.get_logger(__name__)

REPO_TYPE_T = Literal["model", "dataset", "space"]

# List of OS-created helper files that need to be ignored
FILES_TO_IGNORE = [".DS_Store"]


@dataclass(frozen=True)
class CachedFileInfo:
    """Frozen data structure holding information about a single cached file.

    Args:
        file_name (`str`):
            Name of the file. Example: `config.json`.
        file_path (`Path`):
            Path of the file in the `snapshots` directory. The file path is a symlink
            referring to a blob in the `blobs` folder.
        blob_path (`Path`):
            Path of the blob file. This is equivalent to `file_path.resolve()`.
        size_on_disk (`int`):
            Size of the blob file in bytes.
        blob_last_accessed (`float`):
            Timestamp of the last time the blob file has been accessed (from any
            revision).
        blob_last_modified (`float`):
            Timestamp of the last time the blob file has been modified/created.

    <Tip warning={true}>

    `blob_last_accessed` and `blob_last_modified` reliability can depend on the OS you
    are using. See [python documentation](https://docs.python.org/3/library/os.html#os.stat_result)
    for more details.

    </Tip>
    """

    file_name: str
    file_path: Path
    blob_path: Path
    size_on_disk: int

    blob_last_accessed: float
    blob_last_modified: float

    @property
    def blob_last_accessed_str(self) -> str:
        """
        (property) Timestamp of the last time the blob file has been accessed (from any
        revision), returned as a human-readable string.

        Example: "2 weeks ago".
        """
        return _format_timesince(self.blob_last_accessed)

    @property
    def blob_last_modified_str(self) -> str:
        """
        (property) Timestamp of the last time the blob file has been modified, returned
        as a human-readable string.

        Example: "2 weeks ago".
        """
        return _format_timesince(self.blob_last_modified)

    @property
    def size_on_disk_str(self) -> str:
        """
        (property) Size of the blob file as a human-readable string.

        Example: "42.2K".
        """
        return _format_size(self.size_on_disk)


@dataclass(frozen=True)
class CachedRevisionInfo:
    """Frozen data structure holding information about a revision.

    A revision correspond to a folder in the `snapshots` folder and is populated with
    the exact tree structure as the repo on the Hub but contains only symlinks. A
    revision can be either referenced by 1 or more `refs` or be "detached" (no refs).

    Args:
        commit_hash (`str`):
            Hash of the revision (unique).
            Example: `"9338f7b671827df886678df2bdd7cc7b4f36dffd"`.
        snapshot_path (`Path`):
            Path to the revision directory in the `snapshots` folder. It contains the
            exact tree structure as the repo on the Hub.
        files: (`FrozenSet[CachedFileInfo]`):
            Set of [`~CachedFileInfo`] describing all files contained in the snapshot.
        refs (`FrozenSet[str]`):
            Set of `refs` pointing to this revision. If the revision has no `refs`, it
            is considered detached.
            Example: `{"main", "2.4.0"}` or `{"refs/pr/1"}`.
        size_on_disk (`int`):
            Sum of the blob file sizes that are symlink-ed by the revision.
        last_modified (`float`):
            Timestamp of the last time the revision has been created/modified.

    <Tip warning={true}>

    `last_accessed` cannot be determined correctly on a single revision as blob files
    are shared across revisions.

    </Tip>

    <Tip warning={true}>

    `size_on_disk` is not necessarily the sum of all file sizes because of possible
    duplicated files. Besides, only blobs are taken into account, not the (negligible)
    size of folders and symlinks.

    </Tip>
    """

    commit_hash: str
    snapshot_path: Path
    size_on_disk: int
    files: FrozenSet[CachedFileInfo]
    refs: FrozenSet[str]

    last_modified: float

    @property
    def last_modified_str(self) -> str:
        """
        (property) Timestamp of the last time the revision has been modified, returned
        as a human-readable string.

        Example: "2 weeks ago".
        """
        return _format_timesince(self.last_modified)

    @property
    def size_on_disk_str(self) -> str:
        """
        (property) Sum of the blob file sizes as a human-readable string.

        Example: "42.2K".
        """
        return _format_size(self.size_on_disk)

    @property
    def nb_files(self) -> int:
        """
        (property) Total number of files in the revision.
        """
        return len(self.files)


@dataclass(frozen=True)
class CachedRepoInfo:
    """Frozen data structure holding information about a cached repository.

    Args:
        repo_id (`str`):
            Repo id of the repo on the Hub. Example: `"google/fleurs"`.
        repo_type (`Literal["dataset", "model", "space"]`):
            Type of the cached repo.
        repo_path (`Path`):
            Local path to the cached repo.
        size_on_disk (`int`):
            Sum of the blob file sizes in the cached repo.
        nb_files (`int`):
            Total number of blob files in the cached repo.
        revisions (`FrozenSet[CachedRevisionInfo]`):
            Set of [`~CachedRevisionInfo`] describing all revisions cached in the repo.
        last_accessed (`float`):
            Timestamp of the last time a blob file of the repo has been accessed.
        last_modified (`float`):
            Timestamp of the last time a blob file of the repo has been modified/created.

    <Tip warning={true}>

    `size_on_disk` is not necessarily the sum of all revisions sizes because of
    duplicated files. Besides, only blobs are taken into account, not the (negligible)
    size of folders and symlinks.

    </Tip>

    <Tip warning={true}>

    `last_accessed` and `last_modified` reliability can depend on the OS you are using.
    See [python documentation](https://docs.python.org/3/library/os.html#os.stat_result)
    for more details.

    </Tip>
    """

    repo_id: str
    repo_type: REPO_TYPE_T
    repo_path: Path
    size_on_disk: int
    nb_files: int
    revisions: FrozenSet[CachedRevisionInfo]

    last_accessed: float
    last_modified: float

    @property
    def last_accessed_str(self) -> str:
        """
        (property) Last time a blob file of the repo has been accessed, returned as a
        human-readable string.

        Example: "2 weeks ago".
        """
        return _format_timesince(self.last_accessed)

    @property
    def last_modified_str(self) -> str:
        """
        (property) Last time a blob file of the repo has been modified, returned as a
        human-readable string.

        Example: "2 weeks ago".
        """
        return _format_timesince(self.last_modified)

    @property
    def size_on_disk_str(self) -> str:
        """
        (property) Sum of the blob file sizes as a human-readable string.

        Example: "42.2K".
        """
        return _format_size(self.size_on_disk)

    @property
    def refs(self) -> Dict[str, CachedRevisionInfo]:
        """
        (property) Mapping between `refs` and revision data structures.
        """
        return {ref: revision for revision in self.revisions for ref in revision.refs}


@dataclass(frozen=True)
class DeleteCacheStrategy:
    """Frozen data structure holding the strategy to delete cached revisions.

    This object is not meant to be instantiated programmatically but to be returned by
    [`~utils.HFCacheInfo.delete_revisions`]. See documentation for usage example.

    Args:
        expected_freed_size (`float`):
            Expected freed size once strategy is executed.
        blobs (`FrozenSet[Path]`):
            Set of blob file paths to be deleted.
        refs (`FrozenSet[Path]`):
            Set of reference file paths to be deleted.
        repos (`FrozenSet[Path]`):
            Set of entire repo paths to be deleted.
        snapshots (`FrozenSet[Path]`):
            Set of snapshots to be deleted (directory of symlinks).
    """

    expected_freed_size: int
    blobs: FrozenSet[Path]
    refs: FrozenSet[Path]
    repos: FrozenSet[Path]
    snapshots: FrozenSet[Path]

    @property
    def expected_freed_size_str(self) -> str:
        """
        (property) Expected size that will be freed as a human-readable string.

        Example: "42.2K".
        """
        return _format_size(self.expected_freed_size)

    def execute(self) -> None:
        """Execute the defined strategy.

        <Tip warning={true}>

        If this method is interrupted, the cache might get corrupted. Deletion order is
        implemented so that references and symlinks are deleted before the actual blob
        files.

        </Tip>

        <Tip warning={true}>

        This method is irreversible. If executed, cached files are erased and must be
        downloaded again.

        </Tip>
        """
        # Deletion order matters. Blobs are deleted in last so that the user can't end
        # up in a state where a `ref`` refers to a missing snapshot or a snapshot
        # symlink refers to a deleted blob.

        # Delete entire repos
        for path in self.repos:
            _try_delete_path(path, path_type="repo")

        # Delete snapshot directories
        for path in self.snapshots:
            _try_delete_path(path, path_type="snapshot")

        # Delete refs files
        for path in self.refs:
            _try_delete_path(path, path_type="ref")

        # Delete blob files
        for path in self.blobs:
            _try_delete_path(path, path_type="blob")

        logger.info(f"Cache deletion done. Saved {self.expected_freed_size_str}.")


@dataclass(frozen=True)
class HFCacheInfo:
    """Frozen data structure holding information about the entire cache-system.

    This data structure is returned by [`scan_cache_dir`] and is immutable.

    Args:
        size_on_disk (`int`):
            Sum of all valid repo sizes in the cache-system.
        repos (`FrozenSet[CachedRepoInfo]`):
            Set of [`~CachedRepoInfo`] describing all valid cached repos found on the
            cache-system while scanning.
        warnings (`List[CorruptedCacheException]`):
            List of [`~CorruptedCacheException`] that occurred while scanning the cache.
            Those exceptions are captured so that the scan can continue. Corrupted repos
            are skipped from the scan.

    <Tip warning={true}>

    Here `size_on_disk` is equal to the sum of all repo sizes (only blobs). However if
    some cached repos are corrupted, their sizes are not taken into account.

    </Tip>
    """

    size_on_disk: int
    repos: FrozenSet[CachedRepoInfo]
    warnings: List[CorruptedCacheException]

    @property
    def size_on_disk_str(self) -> str:
        """
        (property) Sum of all valid repo sizes in the cache-system as a human-readable
        string.

        Example: "42.2K".
        """
        return _format_size(self.size_on_disk)

    def delete_revisions(self, *revisions: str) -> DeleteCacheStrategy:
        """Prepare the strategy to delete one or more revisions cached locally.

        Input revisions can be any revision hash. If a revision hash is not found in the
        local cache, a warning is thrown but no error is raised. Revisions can be from
        different cached repos since hashes are unique across repos,

        Examples:
        ```py
        >>> from huggingface_hub import scan_cache_dir
        >>> cache_info = scan_cache_dir()
        >>> delete_strategy = cache_info.delete_revisions(
        ...     "81fd1d6e7847c99f5862c9fb81387956d99ec7aa"
        ... )
        >>> print(f"Will free {delete_strategy.expected_freed_size_str}.")
        Will free 7.9K.
        >>> delete_strategy.execute()
        Cache deletion done. Saved 7.9K.
        ```

        ```py
        >>> from huggingface_hub import scan_cache_dir
        >>> scan_cache_dir().delete_revisions(
        ...     "81fd1d6e7847c99f5862c9fb81387956d99ec7aa",
        ...     "e2983b237dccf3ab4937c97fa717319a9ca1a96d",
        ...     "6c0e6080953db56375760c0471a8c5f2929baf11",
        ... ).execute()
        Cache deletion done. Saved 8.6G.
        ```

        <Tip warning={true}>

        `delete_revisions` returns a [`~utils.DeleteCacheStrategy`] object that needs to
        be executed. The [`~utils.DeleteCacheStrategy`] is not meant to be modified but
        allows having a dry run before actually executing the deletion.

        </Tip>
        """
        hashes_to_delete: Set[str] = set(revisions)

        repos_with_revisions: Dict[CachedRepoInfo, Set[CachedRevisionInfo]] = defaultdict(set)

        for repo in self.repos:
            for revision in repo.revisions:
                if revision.commit_hash in hashes_to_delete:
                    repos_with_revisions[repo].add(revision)
                    hashes_to_delete.remove(revision.commit_hash)

        if len(hashes_to_delete) > 0:
            logger.warning(f"Revision(s) not found - cannot delete them: {', '.join(hashes_to_delete)}")

        delete_strategy_blobs: Set[Path] = set()
        delete_strategy_refs: Set[Path] = set()
        delete_strategy_repos: Set[Path] = set()
        delete_strategy_snapshots: Set[Path] = set()
        delete_strategy_expected_freed_size = 0

        for affected_repo, revisions_to_delete in repos_with_revisions.items():
            other_revisions = affected_repo.revisions - revisions_to_delete

            # If no other revisions, it means all revisions are deleted
            # -> delete the entire cached repo
            if len(other_revisions) == 0:
                delete_strategy_repos.add(affected_repo.repo_path)
                delete_strategy_expected_freed_size += affected_repo.size_on_disk
                continue

            # Some revisions of the repo will be deleted but not all. We need to filter
            # which blob files will not be linked anymore.
            for revision_to_delete in revisions_to_delete:
                # Snapshot dir
                delete_strategy_snapshots.add(revision_to_delete.snapshot_path)

                # Refs dir
                for ref in revision_to_delete.refs:
                    delete_strategy_refs.add(affected_repo.repo_path / "refs" / ref)

                # Blobs dir
                for file in revision_to_delete.files:
                    if file.blob_path not in delete_strategy_blobs:
                        is_file_alone = True
                        for revision in other_revisions:
                            for rev_file in revision.files:
                                if file.blob_path == rev_file.blob_path:
                                    is_file_alone = False
                                    break
                            if not is_file_alone:
                                break

                        # Blob file not referenced by remaining revisions -> delete
                        if is_file_alone:
                            delete_strategy_blobs.add(file.blob_path)
                            delete_strategy_expected_freed_size += file.size_on_disk

        # Return the strategy instead of executing it.
        return DeleteCacheStrategy(
            blobs=frozenset(delete_strategy_blobs),
            refs=frozenset(delete_strategy_refs),
            repos=frozenset(delete_strategy_repos),
            snapshots=frozenset(delete_strategy_snapshots),
            expected_freed_size=delete_strategy_expected_freed_size,
        )

    def export_as_table(self, *, verbosity: int = 0) -> str:
        """Generate a table from the [`HFCacheInfo`] object.

        Pass `verbosity=0` to get a table with a single row per repo, with columns
        "repo_id", "repo_type", "size_on_disk", "nb_files", "last_accessed", "last_modified", "refs", "local_path".

        Pass `verbosity=1` to get a table with a row per repo and revision (thus multiple rows can appear for a single repo), with columns
        "repo_id", "repo_type", "revision", "size_on_disk", "nb_files", "last_modified", "refs", "local_path".

        Example:
        ```py
        >>> from huggingface_hub.utils import scan_cache_dir

        >>> hf_cache_info = scan_cache_dir()
        HFCacheInfo(...)

        >>> print(hf_cache_info.export_as_table())
        REPO ID                                             REPO TYPE SIZE ON DISK NB FILES LAST_ACCESSED LAST_MODIFIED REFS LOCAL PATH
        --------------------------------------------------- --------- ------------ -------- ------------- ------------- ---- --------------------------------------------------------------------------------------------------
        roberta-base                                        model             2.7M        5 1 day ago     1 week ago    main ~/.cache/huggingface/hub/models--roberta-base
        suno/bark                                           model             8.8K        1 1 week ago    1 week ago    main ~/.cache/huggingface/hub/models--suno--bark
        t5-base                                             model           893.8M        4 4 days ago    7 months ago  main ~/.cache/huggingface/hub/models--t5-base
        t5-large                                            model             3.0G        4 5 weeks ago   5 months ago  main ~/.cache/huggingface/hub/models--t5-large

        >>> print(hf_cache_info.export_as_table(verbosity=1))
        REPO ID                                             REPO TYPE REVISION                                 SIZE ON DISK NB FILES LAST_MODIFIED REFS LOCAL PATH
        --------------------------------------------------- --------- ---------------------------------------- ------------ -------- ------------- ---- -----------------------------------------------------------------------------------------------------------------------------------------------------
        roberta-base                                        model     e2da8e2f811d1448a5b465c236feacd80ffbac7b         2.7M        5 1 week ago    main ~/.cache/huggingface/hub/models--roberta-base/snapshots/e2da8e2f811d1448a5b465c236feacd80ffbac7b
        suno/bark                                           model     70a8a7d34168586dc5d028fa9666aceade177992         8.8K        1 1 week ago    main ~/.cache/huggingface/hub/models--suno--bark/snapshots/70a8a7d34168586dc5d028fa9666aceade177992
        t5-base                                             model     a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1       893.8M        4 7 months ago  main ~/.cache/huggingface/hub/models--t5-base/snapshots/a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1
        t5-large                                            model     150ebc2c4b72291e770f58e6057481c8d2ed331a         3.0G        4 5 months ago  main ~/.cache/huggingface/hub/models--t5-large/snapshots/150ebc2c4b72291e770f58e6057481c8d2ed331a
        ```

        Args:
            verbosity (`int`, *optional*):
                The verbosity level. Defaults to 0.

        Returns:
            `str`: The table as a string.
        """
        if verbosity == 0:
            return tabulate(
                rows=[
                    [
                        repo.repo_id,
                        repo.repo_type,
                        "{:>12}".format(repo.size_on_disk_str),
                        repo.nb_files,
                        repo.last_accessed_str,
                        repo.last_modified_str,
                        ", ".join(sorted(repo.refs)),
                        str(repo.repo_path),
                    ]
                    for repo in sorted(self.repos, key=lambda repo: repo.repo_path)
                ],
                headers=[
                    "REPO ID",
                    "REPO TYPE",
                    "SIZE ON DISK",
                    "NB FILES",
                    "LAST_ACCESSED",
                    "LAST_MODIFIED",
                    "REFS",
                    "LOCAL PATH",
                ],
            )
        else:
            return tabulate(
                rows=[
                    [
                        repo.repo_id,
                        repo.repo_type,
                        revision.commit_hash,
                        "{:>12}".format(revision.size_on_disk_str),
                        revision.nb_files,
                        revision.last_modified_str,
                        ", ".join(sorted(revision.refs)),
                        str(revision.snapshot_path),
                    ]
                    for repo in sorted(self.repos, key=lambda repo: repo.repo_path)
                    for revision in sorted(repo.revisions, key=lambda revision: revision.commit_hash)
                ],
                headers=[
                    "REPO ID",
                    "REPO TYPE",
                    "REVISION",
                    "SIZE ON DISK",
                    "NB FILES",
                    "LAST_MODIFIED",
                    "REFS",
                    "LOCAL PATH",
                ],
            )


def scan_cache_dir(cache_dir: Optional[Union[str, Path]] = None) -> HFCacheInfo:
    """Scan the entire HF cache-system and return a [`~HFCacheInfo`] structure.

    Use `scan_cache_dir` in order to programmatically scan your cache-system. The cache
    will be scanned repo by repo. If a repo is corrupted, a [`~CorruptedCacheException`]
    will be thrown internally but captured and returned in the [`~HFCacheInfo`]
    structure. Only valid repos get a proper report.

    ```py
    >>> from huggingface_hub import scan_cache_dir

    >>> hf_cache_info = scan_cache_dir()
    HFCacheInfo(
        size_on_disk=3398085269,
        repos=frozenset({
            CachedRepoInfo(
                repo_id='t5-small',
                repo_type='model',
                repo_path=PosixPath(...),
                size_on_disk=970726914,
                nb_files=11,
                revisions=frozenset({
                    CachedRevisionInfo(
                        commit_hash='d78aea13fa7ecd06c29e3e46195d6341255065d5',
                        size_on_disk=970726339,
                        snapshot_path=PosixPath(...),
                        files=frozenset({
                            CachedFileInfo(
                                file_name='config.json',
                                size_on_disk=1197
                                file_path=PosixPath(...),
                                blob_path=PosixPath(...),
                            ),
                            CachedFileInfo(...),
                            ...
                        }),
                    ),
                    CachedRevisionInfo(...),
                    ...
                }),
            ),
            CachedRepoInfo(...),
            ...
        }),
        warnings=[
            CorruptedCacheException("Snapshots dir doesn't exist in cached repo: ..."),
            CorruptedCacheException(...),
            ...
        ],
    )
    ```

    You can also print a detailed report directly from the `huggingface-cli` using:
    ```text
    > huggingface-cli scan-cache
    REPO ID                     REPO TYPE SIZE ON DISK NB FILES REFS                LOCAL PATH
    --------------------------- --------- ------------ -------- ------------------- -------------------------------------------------------------------------
    glue                        dataset         116.3K       15 1.17.0, main, 2.4.0 /Users/lucain/.cache/huggingface/hub/datasets--glue
    google/fleurs               dataset          64.9M        6 main, refs/pr/1     /Users/lucain/.cache/huggingface/hub/datasets--google--fleurs
    Jean-Baptiste/camembert-ner model           441.0M        7 main                /Users/lucain/.cache/huggingface/hub/models--Jean-Baptiste--camembert-ner
    bert-base-cased             model             1.9G       13 main                /Users/lucain/.cache/huggingface/hub/models--bert-base-cased
    t5-base                     model            10.1K        3 main                /Users/lucain/.cache/huggingface/hub/models--t5-base
    t5-small                    model           970.7M       11 refs/pr/1, main     /Users/lucain/.cache/huggingface/hub/models--t5-small

    Done in 0.0s. Scanned 6 repo(s) for a total of 3.4G.
    Got 1 warning(s) while scanning. Use -vvv to print details.
    ```

    Args:
        cache_dir (`str` or `Path`, `optional`):
            Cache directory to cache. Defaults to the default HF cache directory.

    <Tip warning={true}>

    Raises:

        `CacheNotFound`
          If the cache directory does not exist.

        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
          If the cache directory is a file, instead of a directory.

    </Tip>

    Returns: a [`~HFCacheInfo`] object.
    """
    if cache_dir is None:
        cache_dir = HF_HUB_CACHE

    cache_dir = Path(cache_dir).expanduser().resolve()
    if not cache_dir.exists():
        raise CacheNotFound(
            f"Cache directory not found: {cache_dir}. Please use `cache_dir` argument or set `HF_HUB_CACHE` environment variable.",
            cache_dir=cache_dir,
        )

    if cache_dir.is_file():
        raise ValueError(
            f"Scan cache expects a directory but found a file: {cache_dir}. Please use `cache_dir` argument or set `HF_HUB_CACHE` environment variable."
        )

    repos: Set[CachedRepoInfo] = set()
    warnings: List[CorruptedCacheException] = []
    for repo_path in cache_dir.iterdir():
        if repo_path.name == ".locks":  # skip './.locks/' folder
            continue
        try:
            repos.add(_scan_cached_repo(repo_path))
        except CorruptedCacheException as e:
            warnings.append(e)

    return HFCacheInfo(
        repos=frozenset(repos),
        size_on_disk=sum(repo.size_on_disk for repo in repos),
        warnings=warnings,
    )


def _scan_cached_repo(repo_path: Path) -> CachedRepoInfo:
    """Scan a single cache repo and return information about it.

    Any unexpected behavior will raise a [`~CorruptedCacheException`].
    """
    if not repo_path.is_dir():
        raise CorruptedCacheException(f"Repo path is not a directory: {repo_path}")

    if "--" not in repo_path.name:
        raise CorruptedCacheException(f"Repo path is not a valid HuggingFace cache directory: {repo_path}")

    repo_type, repo_id = repo_path.name.split("--", maxsplit=1)
    repo_type = repo_type[:-1]  # "models" -> "model"
    repo_id = repo_id.replace("--", "/")  # google/fleurs -> "google/fleurs"

    if repo_type not in {"dataset", "model", "space"}:
        raise CorruptedCacheException(
            f"Repo type must be `dataset`, `model` or `space`, found `{repo_type}` ({repo_path})."
        )

    blob_stats: Dict[Path, os.stat_result] = {}  # Key is blob_path, value is blob stats

    snapshots_path = repo_path / "snapshots"
    refs_path = repo_path / "refs"

    if not snapshots_path.exists() or not snapshots_path.is_dir():
        raise CorruptedCacheException(f"Snapshots dir doesn't exist in cached repo: {snapshots_path}")

    # Scan over `refs` directory

    # key is revision hash, value is set of refs
    refs_by_hash: Dict[str, Set[str]] = defaultdict(set)
    if refs_path.exists():
        # Example of `refs` directory
        # ── refs
        #     ├── main
        #     └── refs
        #         └── pr
        #             └── 1
        if refs_path.is_file():
            raise CorruptedCacheException(f"Refs directory cannot be a file: {refs_path}")

        for ref_path in refs_path.glob("**/*"):
            # glob("**/*") iterates over all files and directories -> skip directories
            if ref_path.is_dir() or ref_path.name in FILES_TO_IGNORE:
                continue

            ref_name = str(ref_path.relative_to(refs_path))
            with ref_path.open() as f:
                commit_hash = f.read()

            refs_by_hash[commit_hash].add(ref_name)

    # Scan snapshots directory
    cached_revisions: Set[CachedRevisionInfo] = set()
    for revision_path in snapshots_path.iterdir():
        # Ignore OS-created helper files
        if revision_path.name in FILES_TO_IGNORE:
            continue
        if revision_path.is_file():
            raise CorruptedCacheException(f"Snapshots folder corrupted. Found a file: {revision_path}")

        cached_files = set()
        for file_path in revision_path.glob("**/*"):
            # glob("**/*") iterates over all files and directories -> skip directories
            if file_path.is_dir():
                continue

            blob_path = Path(file_path).resolve()
            if not blob_path.exists():
                raise CorruptedCacheException(f"Blob missing (broken symlink): {blob_path}")

            if blob_path not in blob_stats:
                blob_stats[blob_path] = blob_path.stat()

            cached_files.add(
                CachedFileInfo(
                    file_name=file_path.name,
                    file_path=file_path,
                    size_on_disk=blob_stats[blob_path].st_size,
                    blob_path=blob_path,
                    blob_last_accessed=blob_stats[blob_path].st_atime,
                    blob_last_modified=blob_stats[blob_path].st_mtime,
                )
            )

        # Last modified is either the last modified blob file or the revision folder
        # itself if it is empty
        if len(cached_files) > 0:
            revision_last_modified = max(blob_stats[file.blob_path].st_mtime for file in cached_files)
        else:
            revision_last_modified = revision_path.stat().st_mtime

        cached_revisions.add(
            CachedRevisionInfo(
                commit_hash=revision_path.name,
                files=frozenset(cached_files),
                refs=frozenset(refs_by_hash.pop(revision_path.name, set())),
                size_on_disk=sum(
                    blob_stats[blob_path].st_size for blob_path in set(file.blob_path for file in cached_files)
                ),
                snapshot_path=revision_path,
                last_modified=revision_last_modified,
            )
        )

    # Check that all refs referred to an existing revision
    if len(refs_by_hash) > 0:
        raise CorruptedCacheException(
            f"Reference(s) refer to missing commit hashes: {dict(refs_by_hash)} ({repo_path})."
        )

    # Last modified is either the last modified blob file or the repo folder itself if
    # no blob files has been found. Same for last accessed.
    if len(blob_stats) > 0:
        repo_last_accessed = max(stat.st_atime for stat in blob_stats.values())
        repo_last_modified = max(stat.st_mtime for stat in blob_stats.values())
    else:
        repo_stats = repo_path.stat()
        repo_last_accessed = repo_stats.st_atime
        repo_last_modified = repo_stats.st_mtime

    # Build and return frozen structure
    return CachedRepoInfo(
        nb_files=len(blob_stats),
        repo_id=repo_id,
        repo_path=repo_path,
        repo_type=repo_type,  # type: ignore
        revisions=frozenset(cached_revisions),
        size_on_disk=sum(stat.st_size for stat in blob_stats.values()),
        last_accessed=repo_last_accessed,
        last_modified=repo_last_modified,
    )


def _format_size(num: int) -> str:
    """Format size in bytes into a human-readable string.

    Taken from https://stackoverflow.com/a/1094933
    """
    num_f = float(num)
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num_f) < 1000.0:
            return f"{num_f:3.1f}{unit}"
        num_f /= 1000.0
    return f"{num_f:.1f}Y"


_TIMESINCE_CHUNKS = (
    # Label, divider, max value
    ("second", 1, 60),
    ("minute", 60, 60),
    ("hour", 60 * 60, 24),
    ("day", 60 * 60 * 24, 6),
    ("week", 60 * 60 * 24 * 7, 6),
    ("month", 60 * 60 * 24 * 30, 11),
    ("year", 60 * 60 * 24 * 365, None),
)


def _format_timesince(ts: float) -> str:
    """Format timestamp in seconds into a human-readable string, relative to now.

    Vaguely inspired by Django's `timesince` formatter.
    """
    delta = time.time() - ts
    if delta < 20:
        return "a few seconds ago"
    for label, divider, max_value in _TIMESINCE_CHUNKS:  # noqa: B007
        value = round(delta / divider)
        if max_value is not None and value <= max_value:
            break
    return f"{value} {label}{'s' if value > 1 else ''} ago"


def _try_delete_path(path: Path, path_type: str) -> None:
    """Try to delete a local file or folder.

    If the path does not exists, error is logged as a warning and then ignored.

    Args:
        path (`Path`)
            Path to delete. Can be a file or a folder.
        path_type (`str`)
            What path are we deleting ? Only for logging purposes. Example: "snapshot".
    """
    logger.info(f"Delete {path_type}: {path}")
    try:
        if path.is_file():
            os.remove(path)
        else:
            shutil.rmtree(path)
    except FileNotFoundError:
        logger.warning(f"Couldn't delete {path_type}: file not found ({path})", exc_info=True)
    except PermissionError:
        logger.warning(f"Couldn't delete {path_type}: permission denied ({path})", exc_info=True)