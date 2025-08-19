
# === NexusCore/openenv\Lib\site-packages\setuptools\command\egg_info.py ===
"""setuptools.command.egg_info

Create a distribution's .egg-info directory and contents"""

import functools
import os
import re
import sys
import time
from collections.abc import Callable

import packaging
import packaging.requirements
import packaging.version

import setuptools.unicode_utils as unicode_utils
from setuptools import Command
from setuptools.command import bdist_egg
from setuptools.command.sdist import sdist, walk_revctrl
from setuptools.command.setopt import edit_config
from setuptools.glob import glob

from .. import _entry_points, _normalization
from .._importlib import metadata
from ..warnings import SetuptoolsDeprecationWarning
from . import _requirestxt

import distutils.errors
import distutils.filelist
from distutils import log
from distutils.errors import DistutilsInternalError
from distutils.filelist import FileList as _FileList
from distutils.util import convert_path

PY_MAJOR = f'{sys.version_info.major}.{sys.version_info.minor}'


def translate_pattern(glob):  # noqa: C901  # is too complex (14)  # FIXME
    """
    Translate a file path glob like '*.txt' in to a regular expression.
    This differs from fnmatch.translate which allows wildcards to match
    directory separators. It also knows about '**/' which matches any number of
    directories.
    """
    pat = ''

    # This will split on '/' within [character classes]. This is deliberate.
    chunks = glob.split(os.path.sep)

    sep = re.escape(os.sep)
    valid_char = f'[^{sep}]'

    for c, chunk in enumerate(chunks):
        last_chunk = c == len(chunks) - 1

        # Chunks that are a literal ** are globstars. They match anything.
        if chunk == '**':
            if last_chunk:
                # Match anything if this is the last component
                pat += '.*'
            else:
                # Match '(name/)*'
                pat += f'(?:{valid_char}+{sep})*'
            continue  # Break here as the whole path component has been handled

        # Find any special characters in the remainder
        i = 0
        chunk_len = len(chunk)
        while i < chunk_len:
            char = chunk[i]
            if char == '*':
                # Match any number of name characters
                pat += valid_char + '*'
            elif char == '?':
                # Match a name character
                pat += valid_char
            elif char == '[':
                # Character class
                inner_i = i + 1
                # Skip initial !/] chars
                if inner_i < chunk_len and chunk[inner_i] == '!':
                    inner_i = inner_i + 1
                if inner_i < chunk_len and chunk[inner_i] == ']':
                    inner_i = inner_i + 1

                # Loop till the closing ] is found
                while inner_i < chunk_len and chunk[inner_i] != ']':
                    inner_i = inner_i + 1

                if inner_i >= chunk_len:
                    # Got to the end of the string without finding a closing ]
                    # Do not treat this as a matching group, but as a literal [
                    pat += re.escape(char)
                else:
                    # Grab the insides of the [brackets]
                    inner = chunk[i + 1 : inner_i]
                    char_class = ''

                    # Class negation
                    if inner[0] == '!':
                        char_class = '^'
                        inner = inner[1:]

                    char_class += re.escape(inner)
                    pat += f'[{char_class}]'

                    # Skip to the end ]
                    i = inner_i
            else:
                pat += re.escape(char)
            i += 1

        # Join each chunk with the dir separator
        if not last_chunk:
            pat += sep

    pat += r'\Z'
    return re.compile(pat, flags=re.MULTILINE | re.DOTALL)


class InfoCommon:
    tag_build = None
    tag_date = None

    @property
    def name(self):
        return _normalization.safe_name(self.distribution.get_name())

    def tagged_version(self):
        tagged = self._maybe_tag(self.distribution.get_version())
        return _normalization.safe_version(tagged)

    def _maybe_tag(self, version):
        """
        egg_info may be called more than once for a distribution,
        in which case the version string already contains all tags.
        """
        return (
            version
            if self.vtags and self._already_tagged(version)
            else version + self.vtags
        )

    def _already_tagged(self, version: str) -> bool:
        # Depending on their format, tags may change with version normalization.
        # So in addition the regular tags, we have to search for the normalized ones.
        return version.endswith(self.vtags) or version.endswith(self._safe_tags())

    def _safe_tags(self) -> str:
        # To implement this we can rely on `safe_version` pretending to be version 0
        # followed by tags. Then we simply discard the starting 0 (fake version number)
        try:
            return _normalization.safe_version(f"0{self.vtags}")[1:]
        except packaging.version.InvalidVersion:
            return _normalization.safe_name(self.vtags.replace(' ', '.'))

    def tags(self) -> str:
        version = ''
        if self.tag_build:
            version += self.tag_build
        if self.tag_date:
            version += time.strftime("%Y%m%d")
        return version

    vtags = property(tags)


class egg_info(InfoCommon, Command):
    description = "create a distribution's .egg-info directory"

    user_options = [
        (
            'egg-base=',
            'e',
            "directory containing .egg-info directories"
            " [default: top of the source tree]",
        ),
        ('tag-date', 'd', "Add date stamp (e.g. 20050528) to version number"),
        ('tag-build=', 'b', "Specify explicit tag to add to version number"),
        ('no-date', 'D', "Don't include date stamp [default]"),
    ]

    boolean_options = ['tag-date']
    negative_opt = {
        'no-date': 'tag-date',
    }

    def initialize_options(self):
        self.egg_base = None
        self.egg_name = None
        self.egg_info = None
        self.egg_version = None
        self.ignore_egg_info_in_manifest = False

    ####################################
    # allow the 'tag_svn_revision' to be detected and
    # set, supporting sdists built on older Setuptools.
    @property
    def tag_svn_revision(self) -> None:
        pass

    @tag_svn_revision.setter
    def tag_svn_revision(self, value):
        pass

    ####################################

    def save_version_info(self, filename) -> None:
        """
        Materialize the value of date into the
        build tag. Install build keys in a deterministic order
        to avoid arbitrary reordering on subsequent builds.
        """
        # follow the order these keys would have been added
        # when PYTHONHASHSEED=0
        egg_info = dict(tag_build=self.tags(), tag_date=0)
        edit_config(filename, dict(egg_info=egg_info))

    def finalize_options(self) -> None:
        # Note: we need to capture the current value returned
        # by `self.tagged_version()`, so we can later update
        # `self.distribution.metadata.version` without
        # repercussions.
        self.egg_name = self.name
        self.egg_version = self.tagged_version()
        parsed_version = packaging.version.Version(self.egg_version)

        try:
            is_version = isinstance(parsed_version, packaging.version.Version)
            spec = "%s==%s" if is_version else "%s===%s"
            packaging.requirements.Requirement(spec % (self.egg_name, self.egg_version))
        except ValueError as e:
            raise distutils.errors.DistutilsOptionError(
                f"Invalid distribution name or version syntax: {self.egg_name}-{self.egg_version}"
            ) from e

        if self.egg_base is None:
            dirs = self.distribution.package_dir
            self.egg_base = (dirs or {}).get('', os.curdir)

        self.ensure_dirname('egg_base')
        self.egg_info = _normalization.filename_component(self.egg_name) + '.egg-info'
        if self.egg_base != os.curdir:
            self.egg_info = os.path.join(self.egg_base, self.egg_info)

        # Set package version for the benefit of dumber commands
        # (e.g. sdist, bdist_wininst, etc.)
        #
        self.distribution.metadata.version = self.egg_version

    def _get_egg_basename(self, py_version=PY_MAJOR, platform=None):
        """Compute filename of the output egg. Private API."""
        return _egg_basename(self.egg_name, self.egg_version, py_version, platform)

    def write_or_delete_file(self, what, filename, data, force: bool = False) -> None:
        """Write `data` to `filename` or delete if empty

        If `data` is non-empty, this routine is the same as ``write_file()``.
        If `data` is empty but not ``None``, this is the same as calling
        ``delete_file(filename)`.  If `data` is ``None``, then this is a no-op
        unless `filename` exists, in which case a warning is issued about the
        orphaned file (if `force` is false), or deleted (if `force` is true).
        """
        if data:
            self.write_file(what, filename, data)
        elif os.path.exists(filename):
            if data is None and not force:
                log.warn("%s not set in setup(), but %s exists", what, filename)
                return
            else:
                self.delete_file(filename)

    def write_file(self, what, filename, data) -> None:
        """Write `data` to `filename` (if not a dry run) after announcing it

        `what` is used in a log message to identify what is being written
        to the file.
        """
        log.info("writing %s to %s", what, filename)
        data = data.encode("utf-8")
        if not self.dry_run:
            f = open(filename, 'wb')
            f.write(data)
            f.close()

    def delete_file(self, filename) -> None:
        """Delete `filename` (if not a dry run) after announcing it"""
        log.info("deleting %s", filename)
        if not self.dry_run:
            os.unlink(filename)

    def run(self) -> None:
        # Pre-load to avoid iterating over entry-points while an empty .egg-info
        # exists in sys.path. See pypa/pyproject-hooks#206
        writers = list(metadata.entry_points(group='egg_info.writers'))

        self.mkpath(self.egg_info)
        try:
            os.utime(self.egg_info, None)
        except OSError as e:
            msg = f"Cannot update time stamp of directory '{self.egg_info}'"
            raise distutils.errors.DistutilsFileError(msg) from e
        for ep in writers:
            writer = ep.load()
            writer(self, ep.name, os.path.join(self.egg_info, ep.name))

        # Get rid of native_libs.txt if it was put there by older bdist_egg
        nl = os.path.join(self.egg_info, "native_libs.txt")
        if os.path.exists(nl):
            self.delete_file(nl)

        self.find_sources()

    def find_sources(self) -> None:
        """Generate SOURCES.txt manifest file"""
        manifest_filename = os.path.join(self.egg_info, "SOURCES.txt")
        mm = manifest_maker(self.distribution)
        mm.ignore_egg_info_dir = self.ignore_egg_info_in_manifest
        mm.manifest = manifest_filename
        mm.run()
        self.filelist = mm.filelist


class FileList(_FileList):
    # Implementations of the various MANIFEST.in commands

    def __init__(
        self, warn=None, debug_print=None, ignore_egg_info_dir: bool = False
    ) -> None:
        super().__init__(warn, debug_print)
        self.ignore_egg_info_dir = ignore_egg_info_dir

    def process_template_line(self, line) -> None:
        # Parse the line: split it up, make sure the right number of words
        # is there, and return the relevant words.  'action' is always
        # defined: it's the first word of the line.  Which of the other
        # three are defined depends on the action; it'll be either
        # patterns, (dir and patterns), or (dir_pattern).
        (action, patterns, dir, dir_pattern) = self._parse_template_line(line)

        action_map: dict[str, Callable] = {
            'include': self.include,
            'exclude': self.exclude,
            'global-include': self.global_include,
            'global-exclude': self.global_exclude,
            'recursive-include': functools.partial(
                self.recursive_include,
                dir,
            ),
            'recursive-exclude': functools.partial(
                self.recursive_exclude,
                dir,
            ),
            'graft': self.graft,
            'prune': self.prune,
        }
        log_map = {
            'include': "warning: no files found matching '%s'",
            'exclude': ("warning: no previously-included files found matching '%s'"),
            'global-include': (
                "warning: no files found matching '%s' anywhere in distribution"
            ),
            'global-exclude': (
                "warning: no previously-included files matching "
                "'%s' found anywhere in distribution"
            ),
            'recursive-include': (
                "warning: no files found matching '%s' under directory '%s'"
            ),
            'recursive-exclude': (
                "warning: no previously-included files matching "
                "'%s' found under directory '%s'"
            ),
            'graft': "warning: no directories found matching '%s'",
            'prune': "no previously-included directories found matching '%s'",
        }

        try:
            process_action = action_map[action]
        except KeyError:
            msg = f"Invalid MANIFEST.in: unknown action {action!r} in {line!r}"
            raise DistutilsInternalError(msg) from None

        # OK, now we know that the action is valid and we have the
        # right number of words on the line for that action -- so we
        # can proceed with minimal error-checking.

        action_is_recursive = action.startswith('recursive-')
        if action in {'graft', 'prune'}:
            patterns = [dir_pattern]
        extra_log_args = (dir,) if action_is_recursive else ()
        log_tmpl = log_map[action]

        self.debug_print(
            ' '.join(
                [action] + ([dir] if action_is_recursive else []) + patterns,
            )
        )
        for pattern in patterns:
            if not process_action(pattern):
                log.warn(log_tmpl, pattern, *extra_log_args)

    def _remove_files(self, predicate):
        """
        Remove all files from the file list that match the predicate.
        Return True if any matching files were removed
        """
        found = False
        for i in range(len(self.files) - 1, -1, -1):
            if predicate(self.files[i]):
                self.debug_print(" removing " + self.files[i])
                del self.files[i]
                found = True
        return found

    def include(self, pattern):
        """Include files that match 'pattern'."""
        found = [f for f in glob(pattern) if not os.path.isdir(f)]
        self.extend(found)
        return bool(found)

    def exclude(self, pattern):
        """Exclude files that match 'pattern'."""
        match = translate_pattern(pattern)
        return self._remove_files(match.match)

    def recursive_include(self, dir, pattern):
        """
        Include all files anywhere in 'dir/' that match the pattern.
        """
        full_pattern = os.path.join(dir, '**', pattern)
        found = [f for f in glob(full_pattern, recursive=True) if not os.path.isdir(f)]
        self.extend(found)
        return bool(found)

    def recursive_exclude(self, dir, pattern):
        """
        Exclude any file anywhere in 'dir/' that match the pattern.
        """
        match = translate_pattern(os.path.join(dir, '**', pattern))
        return self._remove_files(match.match)

    def graft(self, dir):
        """Include all files from 'dir/'."""
        found = [
            item
            for match_dir in glob(dir)
            for item in distutils.filelist.findall(match_dir)
        ]
        self.extend(found)
        return bool(found)

    def prune(self, dir):
        """Filter out files from 'dir/'."""
        match = translate_pattern(os.path.join(dir, '**'))
        return self._remove_files(match.match)

    def global_include(self, pattern):
        """
        Include all files anywhere in the current directory that match the
        pattern. This is very inefficient on large file trees.
        """
        if self.allfiles is None:
            self.findall()
        match = translate_pattern(os.path.join('**', pattern))
        found = [f for f in self.allfiles if match.match(f)]
        self.extend(found)
        return bool(found)

    def global_exclude(self, pattern):
        """
        Exclude all files anywhere that match the pattern.
        """
        match = translate_pattern(os.path.join('**', pattern))
        return self._remove_files(match.match)

    def append(self, item) -> None:
        if item.endswith('\r'):  # Fix older sdists built on Windows
            item = item[:-1]
        path = convert_path(item)

        if self._safe_path(path):
            self.files.append(path)

    def extend(self, paths) -> None:
        self.files.extend(filter(self._safe_path, paths))

    def _repair(self):
        """
        Replace self.files with only safe paths

        Because some owners of FileList manipulate the underlying
        ``files`` attribute directly, this method must be called to
        repair those paths.
        """
        self.files = list(filter(self._safe_path, self.files))

    def _safe_path(self, path):
        enc_warn = "'%s' not %s encodable -- skipping"

        # To avoid accidental trans-codings errors, first to unicode
        u_path = unicode_utils.filesys_decode(path)
        if u_path is None:
            log.warn(f"'{path}' in unexpected encoding -- skipping")
            return False

        # Must ensure utf-8 encodability
        utf8_path = unicode_utils.try_encode(u_path, "utf-8")
        if utf8_path is None:
            log.warn(enc_warn, path, 'utf-8')
            return False

        try:
            # ignore egg-info paths
            is_egg_info = ".egg-info" in u_path or b".egg-info" in utf8_path
            if self.ignore_egg_info_dir and is_egg_info:
                return False
            # accept is either way checks out
            if os.path.exists(u_path) or os.path.exists(utf8_path):
                return True
        # this will catch any encode errors decoding u_path
        except UnicodeEncodeError:
            log.warn(enc_warn, path, sys.getfilesystemencoding())


class manifest_maker(sdist):
    template = "MANIFEST.in"

    def initialize_options(self) -> None:
        self.use_defaults = True
        self.prune = True
        self.manifest_only = True
        self.force_manifest = True
        self.ignore_egg_info_dir = False

    def finalize_options(self) -> None:
        pass

    def run(self) -> None:
        self.filelist = FileList(ignore_egg_info_dir=self.ignore_egg_info_dir)
        if not os.path.exists(self.manifest):
            self.write_manifest()  # it must exist so it'll get in the list
        self.add_defaults()
        if os.path.exists(self.template):
            self.read_template()
        self.add_license_files()
        self._add_referenced_files()
        self.prune_file_list()
        self.filelist.sort()
        self.filelist.remove_duplicates()
        self.write_manifest()

    def _manifest_normalize(self, path):
        path = unicode_utils.filesys_decode(path)
        return path.replace(os.sep, '/')

    def write_manifest(self) -> None:
        """
        Write the file list in 'self.filelist' to the manifest file
        named by 'self.manifest'.
        """
        self.filelist._repair()

        # Now _repairs should encodability, but not unicode
        files = [self._manifest_normalize(f) for f in self.filelist.files]
        msg = f"writing manifest file '{self.manifest}'"
        self.execute(write_file, (self.manifest, files), msg)

    def warn(self, msg) -> None:
        if not self._should_suppress_warning(msg):
            sdist.warn(self, msg)

    @staticmethod
    def _should_suppress_warning(msg):
        """
        suppress missing-file warnings from sdist
        """
        return re.match(r"standard file .*not found", msg)

    def add_defaults(self) -> None:
        sdist.add_defaults(self)
        self.filelist.append(self.template)
        self.filelist.append(self.manifest)
        rcfiles = list(walk_revctrl())
        if rcfiles:
            self.filelist.extend(rcfiles)
        elif os.path.exists(self.manifest):
            self.read_manifest()

        if os.path.exists("setup.py"):
            # setup.py should be included by default, even if it's not
            # the script called to create the sdist
            self.filelist.append("setup.py")

        ei_cmd = self.get_finalized_command('egg_info')
        self.filelist.graft(ei_cmd.egg_info)

    def add_license_files(self) -> None:
        license_files = self.distribution.metadata.license_files or []
        for lf in license_files:
            log.info("adding license file '%s'", lf)
        self.filelist.extend(license_files)

    def _add_referenced_files(self):
        """Add files referenced by the config (e.g. `file:` directive) to filelist"""
        referenced = getattr(self.distribution, '_referenced_files', [])
        # ^-- fallback if dist comes from distutils or is a custom class
        for rf in referenced:
            log.debug("adding file referenced by config '%s'", rf)
        self.filelist.extend(referenced)

    def _safe_data_files(self, build_py):
        """
        The parent class implementation of this method
        (``sdist``) will try to include data files, which
        might cause recursion problems when
        ``include_package_data=True``.

        Therefore, avoid triggering any attempt of
        analyzing/building the manifest again.
        """
        if hasattr(build_py, 'get_data_files_without_manifest'):
            return build_py.get_data_files_without_manifest()

        SetuptoolsDeprecationWarning.emit(
            "`build_py` command does not inherit from setuptools' `build_py`.",
            """
            Custom 'build_py' does not implement 'get_data_files_without_manifest'.
            Please extend command classes from setuptools instead of distutils.
            """,
            see_url="https://peps.python.org/pep-0632/",
            # due_date not defined yet, old projects might still do it?
        )
        return build_py.get_data_files()


def write_file(filename, contents) -> None:
    """Create a file with the specified name and write 'contents' (a
    sequence of strings without line terminators) to it.
    """
    contents = "\n".join(contents)

    # assuming the contents has been vetted for utf-8 encoding
    contents = contents.encode("utf-8")

    with open(filename, "wb") as f:  # always write POSIX-style manifest
        f.write(contents)


def write_pkg_info(cmd, basename, filename) -> None:
    log.info("writing %s", filename)
    if not cmd.dry_run:
        metadata = cmd.distribution.metadata
        metadata.version, oldver = cmd.egg_version, metadata.version
        metadata.name, oldname = cmd.egg_name, metadata.name

        try:
            metadata.write_pkg_info(cmd.egg_info)
        finally:
            metadata.name, metadata.version = oldname, oldver

        safe = getattr(cmd.distribution, 'zip_safe', None)

        bdist_egg.write_safety_flag(cmd.egg_info, safe)


def warn_depends_obsolete(cmd, basename, filename) -> None:
    """
    Unused: left to avoid errors when updating (from source) from <= 67.8.
    Old installations have a .dist-info directory with the entry-point
    ``depends.txt = setuptools.command.egg_info:warn_depends_obsolete``.
    This may trigger errors when running the first egg_info in build_meta.
    TODO: Remove this function in a version sufficiently > 68.
    """


# Export API used in entry_points
write_requirements = _requirestxt.write_requirements
write_setup_requirements = _requirestxt.write_setup_requirements


def write_toplevel_names(cmd, basename, filename) -> None:
    pkgs = dict.fromkeys([
        k.split('.', 1)[0] for k in cmd.distribution.iter_distribution_names()
    ])
    cmd.write_file("top-level names", filename, '\n'.join(sorted(pkgs)) + '\n')


def overwrite_arg(cmd, basename, filename) -> None:
    write_arg(cmd, basename, filename, True)


def write_arg(cmd, basename, filename, force: bool = False) -> None:
    argname = os.path.splitext(basename)[0]
    value = getattr(cmd.distribution, argname, None)
    if value is not None:
        value = '\n'.join(value) + '\n'
    cmd.write_or_delete_file(argname, filename, value, force)


def write_entries(cmd, basename, filename) -> None:
    eps = _entry_points.load(cmd.distribution.entry_points)
    defn = _entry_points.render(eps)
    cmd.write_or_delete_file('entry points', filename, defn, True)


def _egg_basename(egg_name, egg_version, py_version=None, platform=None):
    """Compute filename of the output egg. Private API."""
    name = _normalization.filename_component(egg_name)
    version = _normalization.filename_component(egg_version)
    egg = f"{name}-{version}-py{py_version or PY_MAJOR}"
    if platform:
        egg += f"-{platform}"
    return egg


class EggInfoDeprecationWarning(SetuptoolsDeprecationWarning):
    """Deprecated behavior warning for EggInfo, bypassing suppression."""

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\disasm.py ===
#!~/.wine/drive_c/Python25/python.exe
# -*- coding: utf-8 -*-

# Copyright (c) 2009-2014, Mario Vilas
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice,this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Binary code disassembly.

@group Disassembler loader:
    Disassembler, Engine

@group Disassembler engines:
    BeaEngine, CapstoneEngine, DistormEngine,
    LibdisassembleEngine, PyDasmEngine
"""

from __future__ import with_statement

__revision__ = "$Id$"

__all__ = [
    "Disassembler",
    "Engine",
    "BeaEngine",
    "CapstoneEngine",
    "DistormEngine",
    "LibdisassembleEngine",
    "PyDasmEngine",
]

from winappdbg.textio import HexDump
from winappdbg import win32

import ctypes
import warnings

# lazy imports
BeaEnginePython = None
distorm3 = None
pydasm = None
libdisassemble = None
capstone = None

# ==============================================================================


class Engine(object):
    """
    Base class for disassembly engine adaptors.

    @type name: str
    @cvar name: Engine name to use with the L{Disassembler} class.

    @type desc: str
    @cvar desc: User friendly name of the disassembler engine.

    @type url: str
    @cvar url: Download URL.

    @type supported: set(str)
    @cvar supported: Set of supported processor architectures.
        For more details see L{win32.version._get_arch}.

    @type arch: str
    @ivar arch: Name of the processor architecture.
    """

    name = "<insert engine name here>"
    desc = "<insert engine description here>"
    url = "<insert download url here>"
    supported = set()

    def __init__(self, arch=None):
        """
        @type  arch: str
        @param arch: Name of the processor architecture.
            If not provided the current processor architecture is assumed.
            For more details see L{win32.version._get_arch}.

        @raise NotImplementedError: This disassembler doesn't support the
            requested processor architecture.
        """
        self.arch = self._validate_arch(arch)
        try:
            self._import_dependencies()
        except ImportError:
            msg = "%s is not installed or can't be found. Download it from: %s"
            msg = msg % (self.name, self.url)
            raise NotImplementedError(msg)

    def _validate_arch(self, arch=None):
        """
        @type  arch: str
        @param arch: Name of the processor architecture.
            If not provided the current processor architecture is assumed.
            For more details see L{win32.version._get_arch}.

        @rtype:  str
        @return: Name of the processor architecture.
            If not provided the current processor architecture is assumed.
            For more details see L{win32.version._get_arch}.

        @raise NotImplementedError: This disassembler doesn't support the
            requested processor architecture.
        """

        # Use the default architecture if none specified.
        if not arch:
            arch = win32.arch

        # Validate the architecture.
        if arch not in self.supported:
            msg = "The %s engine cannot decode %s code."
            msg = msg % (self.name, arch)
            raise NotImplementedError(msg)

        # Return the architecture.
        return arch

    def _import_dependencies(self):
        """
        Loads the dependencies for this disassembler.

        @raise ImportError: This disassembler cannot find or load the
            necessary dependencies to make it work.
        """
        raise SyntaxError("Subclasses MUST implement this method!")

    def decode(self, address, code):
        """
        @type  address: int
        @param address: Memory address where the code was read from.

        @type  code: str
        @param code: Machine code to disassemble.

        @rtype:  list of tuple( long, int, str, str )
        @return: List of tuples. Each tuple represents an assembly instruction
            and contains:
             - Memory address of instruction.
             - Size of instruction in bytes.
             - Disassembly line of instruction.
             - Hexadecimal dump of instruction.

        @raise NotImplementedError: This disassembler could not be loaded.
            This may be due to missing dependencies.
        """
        raise NotImplementedError()


# ==============================================================================


class BeaEngine(Engine):
    """
    Integration with the BeaEngine disassembler by Beatrix.

    @see: U{https://sourceforge.net/projects/winappdbg/files/additional%20packages/BeaEngine/}
    """

    name = "BeaEngine"
    desc = "BeaEngine disassembler by Beatrix"
    url = "https://sourceforge.net/projects/winappdbg/files/additional%20packages/BeaEngine/"

    supported = set(
        (
            win32.ARCH_I386,
            win32.ARCH_AMD64,
        )
    )

    def _import_dependencies(self):
        # Load the BeaEngine ctypes wrapper.
        global BeaEnginePython
        if BeaEnginePython is None:
            import BeaEnginePython

    def decode(self, address, code):
        addressof = ctypes.addressof

        # Instance the code buffer.
        buffer = ctypes.create_string_buffer(code)
        buffer_ptr = addressof(buffer)

        # Instance the disassembler structure.
        Instruction = BeaEnginePython.DISASM()
        Instruction.VirtualAddr = address
        Instruction.EIP = buffer_ptr
        Instruction.SecurityBlock = buffer_ptr + len(code)
        if self.arch == win32.ARCH_I386:
            Instruction.Archi = 0
        else:
            Instruction.Archi = 0x40
        Instruction.Options = (
            BeaEnginePython.Tabulation + BeaEnginePython.NasmSyntax + BeaEnginePython.SuffixedNumeral + BeaEnginePython.ShowSegmentRegs
        )

        # Prepare for looping over each instruction.
        result = []
        Disasm = BeaEnginePython.Disasm
        InstructionPtr = addressof(Instruction)
        hexdump = HexDump.hexadecimal
        append = result.append
        OUT_OF_BLOCK = BeaEnginePython.OUT_OF_BLOCK
        UNKNOWN_OPCODE = BeaEnginePython.UNKNOWN_OPCODE

        # For each decoded instruction...
        while True:
            # Calculate the current offset into the buffer.
            offset = Instruction.EIP - buffer_ptr

            # If we've gone past the buffer, break the loop.
            if offset >= len(code):
                break

            # Decode the current instruction.
            InstrLength = Disasm(InstructionPtr)

            # If BeaEngine detects we've gone past the buffer, break the loop.
            if InstrLength == OUT_OF_BLOCK:
                break

            # The instruction could not be decoded.
            if InstrLength == UNKNOWN_OPCODE:
                # Output a single byte as a "db" instruction.
                char = "%.2X" % ord(buffer[offset])
                result.append(
                    (
                        Instruction.VirtualAddr,
                        1,
                        "db %sh" % char,
                        char,
                    )
                )
                Instruction.VirtualAddr += 1
                Instruction.EIP += 1

            # The instruction was decoded but reading past the buffer's end.
            # This can happen when the last instruction is a prefix without an
            # opcode. For example: decode(0, '\x66')
            elif offset + InstrLength > len(code):
                # Output each byte as a "db" instruction.
                for char in buffer[offset : offset + len(code)]:
                    char = "%.2X" % ord(char)
                    result.append(
                        (
                            Instruction.VirtualAddr,
                            1,
                            "db %sh" % char,
                            char,
                        )
                    )
                    Instruction.VirtualAddr += 1
                    Instruction.EIP += 1

            # The instruction was decoded correctly.
            else:
                # Output the decoded instruction.
                append(
                    (
                        Instruction.VirtualAddr,
                        InstrLength,
                        Instruction.CompleteInstr.strip(),
                        hexdump(buffer.raw[offset : offset + InstrLength]),
                    )
                )
                Instruction.VirtualAddr += InstrLength
                Instruction.EIP += InstrLength

        # Return the list of decoded instructions.
        return result


# ==============================================================================


class DistormEngine(Engine):
    """
    Integration with the diStorm disassembler by Gil Dabah.

    @see: U{https://code.google.com/p/distorm3}
    """

    name = "diStorm"
    desc = "diStorm disassembler by Gil Dabah"
    url = "https://code.google.com/p/distorm3"

    supported = set(
        (
            win32.ARCH_I386,
            win32.ARCH_AMD64,
        )
    )

    def _import_dependencies(self):
        # Load the distorm bindings.
        global distorm3
        if distorm3 is None:
            try:
                import distorm3
            except ImportError:
                import distorm as distorm3

        # Load the decoder function.
        self.__decode = distorm3.Decode

        # Load the bits flag.
        self.__flag = {
            win32.ARCH_I386: distorm3.Decode32Bits,
            win32.ARCH_AMD64: distorm3.Decode64Bits,
        }[self.arch]

    def decode(self, address, code):
        return self.__decode(address, code, self.__flag)


# ==============================================================================


class PyDasmEngine(Engine):
    """
    Integration with PyDasm: Python bindings to libdasm.

    @see: U{https://code.google.com/p/libdasm/}
    """

    name = "PyDasm"
    desc = "PyDasm: Python bindings to libdasm"
    url = "https://code.google.com/p/libdasm/"

    supported = set((win32.ARCH_I386,))

    def _import_dependencies(self):
        # Load the libdasm bindings.
        global pydasm
        if pydasm is None:
            import pydasm

    def decode(self, address, code):
        # Decode each instruction in the buffer.
        result = []
        offset = 0
        while offset < len(code):
            # Try to decode the current instruction.
            instruction = pydasm.get_instruction(code[offset : offset + 32], pydasm.MODE_32)

            # Get the memory address of the current instruction.
            current = address + offset

            # Illegal opcode or opcode longer than remaining buffer.
            if not instruction or instruction.length + offset > len(code):
                hexdump = "%.2X" % ord(code[offset])
                disasm = "db 0x%s" % hexdump
                ilen = 1

            # Correctly decoded instruction.
            else:
                disasm = pydasm.get_instruction_string(instruction, pydasm.FORMAT_INTEL, current)
                ilen = instruction.length
                hexdump = HexDump.hexadecimal(code[offset : offset + ilen])

            # Add the decoded instruction to the list.
            result.append(
                (
                    current,
                    ilen,
                    disasm,
                    hexdump,
                )
            )

            # Move to the next instruction.
            offset += ilen

        # Return the list of decoded instructions.
        return result


# ==============================================================================


class LibdisassembleEngine(Engine):
    """
    Integration with Immunity libdisassemble.

    @see: U{http://www.immunitysec.com/resources-freesoftware.shtml}
    """

    name = "Libdisassemble"
    desc = "Immunity libdisassemble"
    url = "http://www.immunitysec.com/resources-freesoftware.shtml"

    supported = set((win32.ARCH_I386,))

    def _import_dependencies(self):
        # Load the libdisassemble module.
        # Since it doesn't come with an installer or an __init__.py file
        # users can only install it manually however they feel like it,
        # so we'll have to do a bit of guessing to find it.

        global libdisassemble
        if libdisassemble is None:
            try:
                # If installed properly with __init__.py
                import libdisassemble.disassemble as libdisassemble

            except ImportError:
                # If installed by just copying and pasting the files
                import disassemble as libdisassemble

    def decode(self, address, code):
        # Decode each instruction in the buffer.
        result = []
        offset = 0
        while offset < len(code):
            # Decode the current instruction.
            opcode = libdisassemble.Opcode(code[offset : offset + 32])
            length = opcode.getSize()
            disasm = opcode.printOpcode("INTEL")
            hexdump = HexDump.hexadecimal(code[offset : offset + length])

            # Add the decoded instruction to the list.
            result.append(
                (
                    address + offset,
                    length,
                    disasm,
                    hexdump,
                )
            )

            # Move to the next instruction.
            offset += length

        # Return the list of decoded instructions.
        return result


# ==============================================================================


class CapstoneEngine(Engine):
    """
    Integration with the Capstone disassembler by Nguyen Anh Quynh.

    @see: U{http://www.capstone-engine.org/}
    """

    name = "Capstone"
    desc = "Capstone disassembler by Nguyen Anh Quynh"
    url = "http://www.capstone-engine.org/"

    supported = set(
        (
            win32.ARCH_I386,
            win32.ARCH_AMD64,
            win32.ARCH_THUMB,
            win32.ARCH_ARM,
            win32.ARCH_ARM64,
        )
    )

    def _import_dependencies(self):
        # Load the Capstone bindings.
        global capstone
        if capstone is None:
            import capstone

        # Load the constants for the requested architecture.
        self.__constants = {
            win32.ARCH_I386: (capstone.CS_ARCH_X86, capstone.CS_MODE_32),
            win32.ARCH_AMD64: (capstone.CS_ARCH_X86, capstone.CS_MODE_64),
            win32.ARCH_THUMB: (capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB),
            win32.ARCH_ARM: (capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM),
            win32.ARCH_ARM64: (capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM),
        }

        # Test for the bug in early versions of Capstone.
        # If found, warn the user about it.
        try:
            self.__bug = not isinstance(
                capstone.cs_disasm_quick(capstone.CS_ARCH_X86, capstone.CS_MODE_32, "\x90", 1)[0], capstone.capstone.CsInsn
            )
        except AttributeError:
            self.__bug = False
        if self.__bug:
            warnings.warn(
                "This version of the Capstone bindings is unstable," " please upgrade to a newer one!", RuntimeWarning, stacklevel=4
            )

    def decode(self, address, code):
        # Get the constants for the requested architecture.
        arch, mode = self.__constants[self.arch]

        # Get the decoder function outside the loop.
        decoder = capstone.cs_disasm_quick

        # If the buggy version of the bindings are being used, we need to catch
        # all exceptions broadly. If not, we only need to catch CsError.
        if self.__bug:
            CsError = Exception
        else:
            CsError = capstone.CsError

        # Create the variables for the instruction length, mnemonic and
        # operands. That way they won't be created within the loop,
        # minimizing the chances data might be overwritten.
        # This only makes sense for the buggy vesion of the bindings, normally
        # memory accesses are safe).
        length = mnemonic = op_str = None

        # For each instruction...
        result = []
        offset = 0
        while offset < len(code):
            # Disassemble a single instruction, because disassembling multiple
            # instructions may cause excessive memory usage (Capstone allocates
            # approximately 1K of metadata per each decoded instruction).
            instr = None
            try:
                instr = decoder(arch, mode, code[offset : offset + 16], address + offset, 1)[0]
            except IndexError:
                pass  # No instructions decoded.
            except CsError:
                pass  # Any other error.

            # On success add the decoded instruction.
            if instr is not None:
                # Get the instruction length, mnemonic and operands.
                # Copy the values quickly before someone overwrites them,
                # if using the buggy version of the bindings (otherwise it's
                # irrelevant in which order we access the properties).
                length = instr.size
                mnemonic = instr.mnemonic
                op_str = instr.op_str

                # Concatenate the mnemonic and the operands.
                if op_str:
                    disasm = "%s %s" % (mnemonic, op_str)
                else:
                    disasm = mnemonic

                # Get the instruction bytes as a hexadecimal dump.
                hexdump = HexDump.hexadecimal(code[offset : offset + length])

            # On error add a "define constant" instruction.
            # The exact instruction depends on the architecture.
            else:
                # The number of bytes to skip depends on the architecture.
                # On Intel processors we'll skip one byte, since we can't
                # really know the instruction length. On the rest of the
                # architectures we always know the instruction length.
                if self.arch in (win32.ARCH_I386, win32.ARCH_AMD64):
                    length = 1
                else:
                    length = 4

                # Get the skipped bytes as a hexadecimal dump.
                skipped = code[offset : offset + length]
                hexdump = HexDump.hexadecimal(skipped)

                # Build the "define constant" instruction.
                # On Intel processors it's "db".
                # On ARM processors it's "dcb".
                if self.arch in (win32.ARCH_I386, win32.ARCH_AMD64):
                    mnemonic = "db "
                else:
                    mnemonic = "dcb "
                bytes = []
                for b in skipped:
                    if b.isalpha():
                        bytes.append("'%s'" % b)
                    else:
                        bytes.append("0x%x" % ord(b))
                op_str = ", ".join(bytes)
                disasm = mnemonic + op_str

            # Add the decoded instruction to the list.
            result.append(
                (
                    address + offset,
                    length,
                    disasm,
                    hexdump,
                )
            )

            # Update the offset.
            offset += length

        # Return the list of decoded instructions.
        return result


# ==============================================================================

# TODO: use a lock to access __decoder
# TODO: look in sys.modules for whichever disassembler is already loaded


class Disassembler(object):
    """
    Generic disassembler. Uses a set of adapters to decide which library to
    load for which supported platform.

    @type engines: tuple( L{Engine} )
    @cvar engines: Set of supported engines. If you implement your own adapter
        you can add its class here to make it available to L{Disassembler}.
        Supported disassemblers are:
    """

    engines = (
        DistormEngine,  # diStorm engine goes first for backwards compatibility
        BeaEngine,
        CapstoneEngine,
        LibdisassembleEngine,
        PyDasmEngine,
    )

    # Add the list of supported disassemblers to the docstring.
    __doc__ += "\n"
    for e in engines:
        __doc__ += "         - %s - %s (U{%s})\n" % (e.name, e.desc, e.url)
    del e

    # Cache of already loaded disassemblers.
    __decoder = {}

    def __new__(cls, arch=None, engine=None):
        """
        Factory class. You can't really instance a L{Disassembler} object,
        instead one of the adapter L{Engine} subclasses is returned.

        @type  arch: str
        @param arch: (Optional) Name of the processor architecture.
            If not provided the current processor architecture is assumed.
            For more details see L{win32.version._get_arch}.

        @type  engine: str
        @param engine: (Optional) Name of the disassembler engine.
            If not provided a compatible one is loaded automatically.
            See: L{Engine.name}

        @raise NotImplementedError: No compatible disassembler was found that
            could decode machine code for the requested architecture. This may
            be due to missing dependencies.

        @raise ValueError: An unknown engine name was supplied.
        """

        # Use the default architecture if none specified.
        if not arch:
            arch = win32.arch

        # Return a compatible engine if none specified.
        if not engine:
            found = False
            for clazz in cls.engines:
                try:
                    if arch in clazz.supported:
                        selected = (clazz.name, arch)
                        try:
                            decoder = cls.__decoder[selected]
                        except KeyError:
                            decoder = clazz(arch)
                            cls.__decoder[selected] = decoder
                        return decoder
                except NotImplementedError:
                    pass
            msg = "No disassembler engine available for %s code." % arch
            raise NotImplementedError(msg)

        # Return the specified engine.
        selected = (engine, arch)
        try:
            decoder = cls.__decoder[selected]
        except KeyError:
            found = False
            engineLower = engine.lower()
            for clazz in cls.engines:
                if clazz.name.lower() == engineLower:
                    found = True
                    break
            if not found:
                msg = "Unsupported disassembler engine: %s" % engine
                raise ValueError(msg)
            if arch not in clazz.supported:
                msg = "The %s engine cannot decode %s code." % selected
                raise NotImplementedError(msg)
            decoder = clazz(arch)
            cls.__decoder[selected] = decoder
        return decoder

# === NexusCore/openenv\Lib\site-packages\nltk\stem\porter.py ===
"""
Porter Stemmer

This is the Porter stemming algorithm. It follows the algorithm
presented in

Porter, M. "An algorithm for suffix stripping." Program 14.3 (1980): 130-137.

with some optional deviations that can be turned on or off with the
`mode` argument to the constructor.

Martin Porter, the algorithm's inventor, maintains a web page about the
algorithm at

    https://www.tartarus.org/~martin/PorterStemmer/

which includes another Python implementation and other implementations
in many languages.
"""

__docformat__ = "plaintext"

import re

from nltk.stem.api import StemmerI


class PorterStemmer(StemmerI):
    """
    A word stemmer based on the Porter stemming algorithm.

        Porter, M. "An algorithm for suffix stripping."
        Program 14.3 (1980): 130-137.

    See https://www.tartarus.org/~martin/PorterStemmer/ for the homepage
    of the algorithm.

    Martin Porter has endorsed several modifications to the Porter
    algorithm since writing his original paper, and those extensions are
    included in the implementations on his website. Additionally, others
    have proposed further improvements to the algorithm, including NLTK
    contributors. There are thus three modes that can be selected by
    passing the appropriate constant to the class constructor's `mode`
    attribute:

    - PorterStemmer.ORIGINAL_ALGORITHM

        An implementation that is faithful to the original paper.

        Note that Martin Porter has deprecated this version of the
        algorithm. Martin distributes implementations of the Porter
        Stemmer in many languages, hosted at:

        https://www.tartarus.org/~martin/PorterStemmer/

        and all of these implementations include his extensions. He
        strongly recommends against using the original, published
        version of the algorithm; only use this mode if you clearly
        understand why you are choosing to do so.

    - PorterStemmer.MARTIN_EXTENSIONS

        An implementation that only uses the modifications to the
        algorithm that are included in the implementations on Martin
        Porter's website. He has declared Porter frozen, so the
        behaviour of those implementations should never change.

    - PorterStemmer.NLTK_EXTENSIONS (default)

        An implementation that includes further improvements devised by
        NLTK contributors or taken from other modified implementations
        found on the web.

    For the best stemming, you should use the default NLTK_EXTENSIONS
    version. However, if you need to get the same results as either the
    original algorithm or one of Martin Porter's hosted versions for
    compatibility with an existing implementation or dataset, you can use
    one of the other modes instead.
    """

    # Modes the Stemmer can be instantiated in
    NLTK_EXTENSIONS = "NLTK_EXTENSIONS"
    MARTIN_EXTENSIONS = "MARTIN_EXTENSIONS"
    ORIGINAL_ALGORITHM = "ORIGINAL_ALGORITHM"

    def __init__(self, mode=NLTK_EXTENSIONS):
        if mode not in (
            self.NLTK_EXTENSIONS,
            self.MARTIN_EXTENSIONS,
            self.ORIGINAL_ALGORITHM,
        ):
            raise ValueError(
                "Mode must be one of PorterStemmer.NLTK_EXTENSIONS, "
                "PorterStemmer.MARTIN_EXTENSIONS, or "
                "PorterStemmer.ORIGINAL_ALGORITHM"
            )

        self.mode = mode

        if self.mode == self.NLTK_EXTENSIONS:
            # This is a table of irregular forms. It is quite short,
            # but still reflects the errors actually drawn to Martin
            # Porter's attention over a 20 year period!
            irregular_forms = {
                "sky": ["sky", "skies"],
                "die": ["dying"],
                "lie": ["lying"],
                "tie": ["tying"],
                "news": ["news"],
                "inning": ["innings", "inning"],
                "outing": ["outings", "outing"],
                "canning": ["cannings", "canning"],
                "howe": ["howe"],
                "proceed": ["proceed"],
                "exceed": ["exceed"],
                "succeed": ["succeed"],
            }

            self.pool = {}
            for key in irregular_forms:
                for val in irregular_forms[key]:
                    self.pool[val] = key

        self.vowels = frozenset(["a", "e", "i", "o", "u"])

    def _is_consonant(self, word, i):
        """Returns True if word[i] is a consonant, False otherwise

        A consonant is defined in the paper as follows:

            A consonant in a word is a letter other than A, E, I, O or
            U, and other than Y preceded by a consonant. (The fact that
            the term `consonant' is defined to some extent in terms of
            itself does not make it ambiguous.) So in TOY the consonants
            are T and Y, and in SYZYGY they are S, Z and G. If a letter
            is not a consonant it is a vowel.
        """
        if word[i] in self.vowels:
            return False
        if word[i] == "y":
            if i == 0:
                return True
            else:
                return not self._is_consonant(word, i - 1)
        return True

    def _measure(self, stem):
        r"""Returns the 'measure' of stem, per definition in the paper

        From the paper:

            A consonant will be denoted by c, a vowel by v. A list
            ccc... of length greater than 0 will be denoted by C, and a
            list vvv... of length greater than 0 will be denoted by V.
            Any word, or part of a word, therefore has one of the four
            forms:

                CVCV ... C
                CVCV ... V
                VCVC ... C
                VCVC ... V

            These may all be represented by the single form

                [C]VCVC ... [V]

            where the square brackets denote arbitrary presence of their
            contents. Using (VC){m} to denote VC repeated m times, this
            may again be written as

                [C](VC){m}[V].

            m will be called the \measure\ of any word or word part when
            represented in this form. The case m = 0 covers the null
            word. Here are some examples:

                m=0    TR,  EE,  TREE,  Y,  BY.
                m=1    TROUBLE,  OATS,  TREES,  IVY.
                m=2    TROUBLES,  PRIVATE,  OATEN,  ORRERY.
        """
        cv_sequence = ""

        # Construct a string of 'c's and 'v's representing whether each
        # character in `stem` is a consonant or a vowel.
        # e.g. 'falafel' becomes 'cvcvcvc',
        #      'architecture' becomes 'vcccvcvccvcv'
        for i in range(len(stem)):
            if self._is_consonant(stem, i):
                cv_sequence += "c"
            else:
                cv_sequence += "v"

        # Count the number of 'vc' occurrences, which is equivalent to
        # the number of 'VC' occurrences in Porter's reduced form in the
        # docstring above, which is in turn equivalent to `m`
        return cv_sequence.count("vc")

    def _has_positive_measure(self, stem):
        return self._measure(stem) > 0

    def _contains_vowel(self, stem):
        """Returns True if stem contains a vowel, else False"""
        for i in range(len(stem)):
            if not self._is_consonant(stem, i):
                return True
        return False

    def _ends_double_consonant(self, word):
        """Implements condition *d from the paper

        Returns True if word ends with a double consonant
        """
        return (
            len(word) >= 2
            and word[-1] == word[-2]
            and self._is_consonant(word, len(word) - 1)
        )

    def _ends_cvc(self, word):
        """Implements condition *o from the paper

        From the paper:

            *o  - the stem ends cvc, where the second c is not W, X or Y
                  (e.g. -WIL, -HOP).
        """
        return (
            len(word) >= 3
            and self._is_consonant(word, len(word) - 3)
            and not self._is_consonant(word, len(word) - 2)
            and self._is_consonant(word, len(word) - 1)
            and word[-1] not in ("w", "x", "y")
        ) or (
            self.mode == self.NLTK_EXTENSIONS
            and len(word) == 2
            and not self._is_consonant(word, 0)
            and self._is_consonant(word, 1)
        )

    def _replace_suffix(self, word, suffix, replacement):
        """Replaces `suffix` of `word` with `replacement"""
        assert word.endswith(suffix), "Given word doesn't end with given suffix"
        if suffix == "":
            return word + replacement
        else:
            return word[: -len(suffix)] + replacement

    def _apply_rule_list(self, word, rules):
        """Applies the first applicable suffix-removal rule to the word

        Takes a word and a list of suffix-removal rules represented as
        3-tuples, with the first element being the suffix to remove,
        the second element being the string to replace it with, and the
        final element being the condition for the rule to be applicable,
        or None if the rule is unconditional.
        """
        for rule in rules:
            suffix, replacement, condition = rule
            if suffix == "*d" and self._ends_double_consonant(word):
                stem = word[:-2]
                if condition is None or condition(stem):
                    return stem + replacement
                else:
                    # Don't try any further rules
                    return word
            if word.endswith(suffix):
                stem = self._replace_suffix(word, suffix, "")
                if condition is None or condition(stem):
                    return stem + replacement
                else:
                    # Don't try any further rules
                    return word

        return word

    def _step1a(self, word):
        """Implements Step 1a from "An algorithm for suffix stripping"

        From the paper:

            SSES -> SS                         caresses  ->  caress
            IES  -> I                          ponies    ->  poni
                                               ties      ->  ti
            SS   -> SS                         caress    ->  caress
            S    ->                            cats      ->  cat
        """
        # this NLTK-only rule extends the original algorithm, so
        # that 'flies'->'fli' but 'dies'->'die' etc
        if self.mode == self.NLTK_EXTENSIONS:
            if word.endswith("ies") and len(word) == 4:
                return self._replace_suffix(word, "ies", "ie")

        return self._apply_rule_list(
            word,
            [
                ("sses", "ss", None),  # SSES -> SS
                ("ies", "i", None),  # IES  -> I
                ("ss", "ss", None),  # SS   -> SS
                ("s", "", None),  # S    ->
            ],
        )

    def _step1b(self, word):
        """Implements Step 1b from "An algorithm for suffix stripping"

        From the paper:

            (m>0) EED -> EE                    feed      ->  feed
                                               agreed    ->  agree
            (*v*) ED  ->                       plastered ->  plaster
                                               bled      ->  bled
            (*v*) ING ->                       motoring  ->  motor
                                               sing      ->  sing

        If the second or third of the rules in Step 1b is successful,
        the following is done:

            AT -> ATE                       conflat(ed)  ->  conflate
            BL -> BLE                       troubl(ed)   ->  trouble
            IZ -> IZE                       siz(ed)      ->  size
            (*d and not (*L or *S or *Z))
               -> single letter
                                            hopp(ing)    ->  hop
                                            tann(ed)     ->  tan
                                            fall(ing)    ->  fall
                                            hiss(ing)    ->  hiss
                                            fizz(ed)     ->  fizz
            (m=1 and *o) -> E               fail(ing)    ->  fail
                                            fil(ing)     ->  file

        The rule to map to a single letter causes the removal of one of
        the double letter pair. The -E is put back on -AT, -BL and -IZ,
        so that the suffixes -ATE, -BLE and -IZE can be recognised
        later. This E may be removed in step 4.
        """
        # this NLTK-only block extends the original algorithm, so that
        # 'spied'->'spi' but 'died'->'die' etc
        if self.mode == self.NLTK_EXTENSIONS:
            if word.endswith("ied"):
                if len(word) == 4:
                    return self._replace_suffix(word, "ied", "ie")
                else:
                    return self._replace_suffix(word, "ied", "i")

        # (m>0) EED -> EE
        if word.endswith("eed"):
            stem = self._replace_suffix(word, "eed", "")
            if self._measure(stem) > 0:
                return stem + "ee"
            else:
                return word

        rule_2_or_3_succeeded = False

        for suffix in ["ed", "ing"]:
            if word.endswith(suffix):
                intermediate_stem = self._replace_suffix(word, suffix, "")
                if self._contains_vowel(intermediate_stem):
                    rule_2_or_3_succeeded = True
                    break

        if not rule_2_or_3_succeeded:
            return word

        return self._apply_rule_list(
            intermediate_stem,
            [
                ("at", "ate", None),  # AT -> ATE
                ("bl", "ble", None),  # BL -> BLE
                ("iz", "ize", None),  # IZ -> IZE
                # (*d and not (*L or *S or *Z))
                # -> single letter
                (
                    "*d",
                    intermediate_stem[-1],
                    lambda stem: intermediate_stem[-1] not in ("l", "s", "z"),
                ),
                # (m=1 and *o) -> E
                (
                    "",
                    "e",
                    lambda stem: (self._measure(stem) == 1 and self._ends_cvc(stem)),
                ),
            ],
        )

    def _step1c(self, word):
        """Implements Step 1c from "An algorithm for suffix stripping"

        From the paper:

        Step 1c

            (*v*) Y -> I                    happy        ->  happi
                                            sky          ->  sky
        """

        def nltk_condition(stem):
            """
            This has been modified from the original Porter algorithm so
            that y->i is only done when y is preceded by a consonant,
            but not if the stem is only a single consonant, i.e.

               (*c and not c) Y -> I

            So 'happy' -> 'happi', but
               'enjoy' -> 'enjoy'  etc

            This is a much better rule. Formerly 'enjoy'->'enjoi' and
            'enjoyment'->'enjoy'. Step 1c is perhaps done too soon; but
            with this modification that no longer really matters.

            Also, the removal of the contains_vowel(z) condition means
            that 'spy', 'fly', 'try' ... stem to 'spi', 'fli', 'tri' and
            conflate with 'spied', 'tried', 'flies' ...
            """
            return len(stem) > 1 and self._is_consonant(stem, len(stem) - 1)

        def original_condition(stem):
            return self._contains_vowel(stem)

        return self._apply_rule_list(
            word,
            [
                (
                    "y",
                    "i",
                    (
                        nltk_condition
                        if self.mode == self.NLTK_EXTENSIONS
                        else original_condition
                    ),
                )
            ],
        )

    def _step2(self, word):
        """Implements Step 2 from "An algorithm for suffix stripping"

        From the paper:

        Step 2

            (m>0) ATIONAL ->  ATE       relational     ->  relate
            (m>0) TIONAL  ->  TION      conditional    ->  condition
                                        rational       ->  rational
            (m>0) ENCI    ->  ENCE      valenci        ->  valence
            (m>0) ANCI    ->  ANCE      hesitanci      ->  hesitance
            (m>0) IZER    ->  IZE       digitizer      ->  digitize
            (m>0) ABLI    ->  ABLE      conformabli    ->  conformable
            (m>0) ALLI    ->  AL        radicalli      ->  radical
            (m>0) ENTLI   ->  ENT       differentli    ->  different
            (m>0) ELI     ->  E         vileli        - >  vile
            (m>0) OUSLI   ->  OUS       analogousli    ->  analogous
            (m>0) IZATION ->  IZE       vietnamization ->  vietnamize
            (m>0) ATION   ->  ATE       predication    ->  predicate
            (m>0) ATOR    ->  ATE       operator       ->  operate
            (m>0) ALISM   ->  AL        feudalism      ->  feudal
            (m>0) IVENESS ->  IVE       decisiveness   ->  decisive
            (m>0) FULNESS ->  FUL       hopefulness    ->  hopeful
            (m>0) OUSNESS ->  OUS       callousness    ->  callous
            (m>0) ALITI   ->  AL        formaliti      ->  formal
            (m>0) IVITI   ->  IVE       sensitiviti    ->  sensitive
            (m>0) BILITI  ->  BLE       sensibiliti    ->  sensible
        """

        if self.mode == self.NLTK_EXTENSIONS:
            # Instead of applying the ALLI -> AL rule after '(a)bli' per
            # the published algorithm, instead we apply it first, and,
            # if it succeeds, run the result through step2 again.
            if word.endswith("alli") and self._has_positive_measure(
                self._replace_suffix(word, "alli", "")
            ):
                return self._step2(self._replace_suffix(word, "alli", "al"))

        bli_rule = ("bli", "ble", self._has_positive_measure)
        abli_rule = ("abli", "able", self._has_positive_measure)

        rules = [
            ("ational", "ate", self._has_positive_measure),
            ("tional", "tion", self._has_positive_measure),
            ("enci", "ence", self._has_positive_measure),
            ("anci", "ance", self._has_positive_measure),
            ("izer", "ize", self._has_positive_measure),
            abli_rule if self.mode == self.ORIGINAL_ALGORITHM else bli_rule,
            ("alli", "al", self._has_positive_measure),
            ("entli", "ent", self._has_positive_measure),
            ("eli", "e", self._has_positive_measure),
            ("ousli", "ous", self._has_positive_measure),
            ("ization", "ize", self._has_positive_measure),
            ("ation", "ate", self._has_positive_measure),
            ("ator", "ate", self._has_positive_measure),
            ("alism", "al", self._has_positive_measure),
            ("iveness", "ive", self._has_positive_measure),
            ("fulness", "ful", self._has_positive_measure),
            ("ousness", "ous", self._has_positive_measure),
            ("aliti", "al", self._has_positive_measure),
            ("iviti", "ive", self._has_positive_measure),
            ("biliti", "ble", self._has_positive_measure),
        ]

        if self.mode == self.NLTK_EXTENSIONS:
            rules.append(("fulli", "ful", self._has_positive_measure))

            # The 'l' of the 'logi' -> 'log' rule is put with the stem,
            # so that short stems like 'geo' 'theo' etc work like
            # 'archaeo' 'philo' etc.
            rules.append(
                ("logi", "log", lambda stem: self._has_positive_measure(word[:-3]))
            )

        if self.mode == self.MARTIN_EXTENSIONS:
            rules.append(("logi", "log", self._has_positive_measure))

        return self._apply_rule_list(word, rules)

    def _step3(self, word):
        """Implements Step 3 from "An algorithm for suffix stripping"

        From the paper:

        Step 3

            (m>0) ICATE ->  IC              triplicate     ->  triplic
            (m>0) ATIVE ->                  formative      ->  form
            (m>0) ALIZE ->  AL              formalize      ->  formal
            (m>0) ICITI ->  IC              electriciti    ->  electric
            (m>0) ICAL  ->  IC              electrical     ->  electric
            (m>0) FUL   ->                  hopeful        ->  hope
            (m>0) NESS  ->                  goodness       ->  good
        """
        return self._apply_rule_list(
            word,
            [
                ("icate", "ic", self._has_positive_measure),
                ("ative", "", self._has_positive_measure),
                ("alize", "al", self._has_positive_measure),
                ("iciti", "ic", self._has_positive_measure),
                ("ical", "ic", self._has_positive_measure),
                ("ful", "", self._has_positive_measure),
                ("ness", "", self._has_positive_measure),
            ],
        )

    def _step4(self, word):
        """Implements Step 4 from "An algorithm for suffix stripping"

        Step 4

            (m>1) AL    ->                  revival        ->  reviv
            (m>1) ANCE  ->                  allowance      ->  allow
            (m>1) ENCE  ->                  inference      ->  infer
            (m>1) ER    ->                  airliner       ->  airlin
            (m>1) IC    ->                  gyroscopic     ->  gyroscop
            (m>1) ABLE  ->                  adjustable     ->  adjust
            (m>1) IBLE  ->                  defensible     ->  defens
            (m>1) ANT   ->                  irritant       ->  irrit
            (m>1) EMENT ->                  replacement    ->  replac
            (m>1) MENT  ->                  adjustment     ->  adjust
            (m>1) ENT   ->                  dependent      ->  depend
            (m>1 and (*S or *T)) ION ->     adoption       ->  adopt
            (m>1) OU    ->                  homologou      ->  homolog
            (m>1) ISM   ->                  communism      ->  commun
            (m>1) ATE   ->                  activate       ->  activ
            (m>1) ITI   ->                  angulariti     ->  angular
            (m>1) OUS   ->                  homologous     ->  homolog
            (m>1) IVE   ->                  effective      ->  effect
            (m>1) IZE   ->                  bowdlerize     ->  bowdler

        The suffixes are now removed. All that remains is a little
        tidying up.
        """
        measure_gt_1 = lambda stem: self._measure(stem) > 1

        return self._apply_rule_list(
            word,
            [
                ("al", "", measure_gt_1),
                ("ance", "", measure_gt_1),
                ("ence", "", measure_gt_1),
                ("er", "", measure_gt_1),
                ("ic", "", measure_gt_1),
                ("able", "", measure_gt_1),
                ("ible", "", measure_gt_1),
                ("ant", "", measure_gt_1),
                ("ement", "", measure_gt_1),
                ("ment", "", measure_gt_1),
                ("ent", "", measure_gt_1),
                # (m>1 and (*S or *T)) ION ->
                (
                    "ion",
                    "",
                    lambda stem: self._measure(stem) > 1 and stem[-1] in ("s", "t"),
                ),
                ("ou", "", measure_gt_1),
                ("ism", "", measure_gt_1),
                ("ate", "", measure_gt_1),
                ("iti", "", measure_gt_1),
                ("ous", "", measure_gt_1),
                ("ive", "", measure_gt_1),
                ("ize", "", measure_gt_1),
            ],
        )

    def _step5a(self, word):
        """Implements Step 5a from "An algorithm for suffix stripping"

        From the paper:

        Step 5a

            (m>1) E     ->                  probate        ->  probat
                                            rate           ->  rate
            (m=1 and not *o) E ->           cease          ->  ceas
        """
        # Note that Martin's test vocabulary and reference
        # implementations are inconsistent in how they handle the case
        # where two rules both refer to a suffix that matches the word
        # to be stemmed, but only the condition of the second one is
        # true.
        # Earlier in step2b we had the rules:
        #     (m>0) EED -> EE
        #     (*v*) ED  ->
        # but the examples in the paper included "feed"->"feed", even
        # though (*v*) is true for "fe" and therefore the second rule
        # alone would map "feed"->"fe".
        # However, in THIS case, we need to handle the consecutive rules
        # differently and try both conditions (obviously; the second
        # rule here would be redundant otherwise). Martin's paper makes
        # no explicit mention of the inconsistency; you have to infer it
        # from the examples.
        # For this reason, we can't use _apply_rule_list here.
        if word.endswith("e"):
            stem = self._replace_suffix(word, "e", "")
            if self._measure(stem) > 1:
                return stem
            if self._measure(stem) == 1 and not self._ends_cvc(stem):
                return stem
        return word

    def _step5b(self, word):
        """Implements Step 5a from "An algorithm for suffix stripping"

        From the paper:

        Step 5b

            (m > 1 and *d and *L) -> single letter
                                    controll       ->  control
                                    roll           ->  roll
        """
        return self._apply_rule_list(
            word, [("ll", "l", lambda stem: self._measure(word[:-1]) > 1)]
        )

    def stem(self, word, to_lowercase=True):
        """
        :param to_lowercase: if `to_lowercase=True` the word always lowercase
        """
        stem = word.lower() if to_lowercase else word

        if self.mode == self.NLTK_EXTENSIONS and word in self.pool:
            return self.pool[stem]

        if self.mode != self.ORIGINAL_ALGORITHM and len(word) <= 2:
            # With this line, strings of length 1 or 2 don't go through
            # the stemming process, although no mention is made of this
            # in the published algorithm.
            return stem

        stem = self._step1a(stem)
        stem = self._step1b(stem)
        stem = self._step1c(stem)
        stem = self._step2(stem)
        stem = self._step3(stem)
        stem = self._step4(stem)
        stem = self._step5a(stem)
        stem = self._step5b(stem)

        return stem

    def __repr__(self):
        return "<PorterStemmer>"


def demo():
    """
    A demonstration of the porter stemmer on a sample from
    the Penn Treebank corpus.
    """

    from nltk import stem
    from nltk.corpus import treebank

    stemmer = stem.PorterStemmer()

    orig = []
    stemmed = []
    for item in treebank.fileids()[:3]:
        for word, tag in treebank.tagged_words(item):
            orig.append(word)
            stemmed.append(stemmer.stem(word))

    # Convert the results to a string, and word-wrap them.
    results = " ".join(stemmed)
    results = re.sub(r"(.{,70})\s", r"\1\n", results + " ").rstrip()

    # Convert the original to a string, and word wrap it.
    original = " ".join(orig)
    original = re.sub(r"(.{,70})\s", r"\1\n", original + " ").rstrip()

    # Print the results.
    print("-Original-".center(70).replace(" ", "*").replace("-", " "))
    print(original)
    print("-Results-".center(70).replace(" ", "*").replace("-", " "))
    print(results)
    print("*" * 70)

# === NexusCore/openenv\Lib\site-packages\win32com\client\__init__.py ===
# This module exists to create the "best" dispatch object for a given
# object.  If "makepy" support for a given object is detected, it is
# used, otherwise a dynamic dispatch object.

# Note that if the unknown dispatch object then returns a known
# dispatch object, the known class will be used.  This contrasts
# with dynamic.Dispatch behaviour, where dynamic objects are always used.
from __future__ import annotations

import sys
from itertools import chain

import pythoncom
import pywintypes

from . import dynamic, gencache

_PyIDispatchType = pythoncom.TypeIIDs[pythoncom.IID_IDispatch]


def __WrapDispatch(
    dispatch,
    userName=None,
    resultCLSID=None,
    typeinfo=None,
    clsctx=pythoncom.CLSCTX_SERVER,
    WrapperClass=None,
):
    """
    Helper function to return a makepy generated class for a CLSID if it exists,
    otherwise cope by using CDispatch.
    """
    if resultCLSID is None:
        try:
            typeinfo = dispatch.GetTypeInfo()
            if (
                typeinfo is not None
            ):  # Some objects return NULL, some raise exceptions...
                resultCLSID = str(typeinfo.GetTypeAttr()[0])
        except (pythoncom.com_error, AttributeError):
            pass
    if resultCLSID is not None:
        from . import gencache

        # Attempt to load generated module support
        # This may load the module, and make it available
        klass = gencache.GetClassForCLSID(resultCLSID)
        if klass is not None:
            return klass(dispatch)

    # Return a "dynamic" object - best we can do!
    if WrapperClass is None:
        WrapperClass = CDispatch
    return dynamic.Dispatch(dispatch, userName, WrapperClass, typeinfo, clsctx=clsctx)


def GetObject(Pathname=None, Class=None, clsctx=None):
    r"""
    Mimic VB's GetObject() function.

    ob = GetObject(Class = "ProgID") or GetObject(Class = clsid) will
    connect to an already running instance of the COM object.

    ob = GetObject(r"c:\blah\blah\foo.xls") (aka the COM moniker syntax)
    will return a ready to use Python wrapping of the required COM object.

    Note: You must specifiy one or the other of these arguments. I know
    this isn't pretty, but it is what VB does. Blech. If you don't
    I'll throw ValueError at you. :)

    This will most likely throw pythoncom.com_error if anything fails.
    """
    if clsctx is None:
        clsctx = pythoncom.CLSCTX_ALL

    if (Pathname is None and Class is None) or (
        Pathname is not None and Class is not None
    ):
        raise ValueError(
            "You must specify a value for Pathname or Class, but not both."
        )

    if Class is not None:
        return GetActiveObject(Class, clsctx)
    else:
        return Moniker(Pathname, clsctx)


def GetActiveObject(Class, clsctx=pythoncom.CLSCTX_ALL):
    """
    Python friendly version of GetObject's ProgID/CLSID functionality.
    """
    resultCLSID = pywintypes.IID(Class)
    dispatch = pythoncom.GetActiveObject(resultCLSID)
    dispatch = dispatch.QueryInterface(pythoncom.IID_IDispatch)
    return __WrapDispatch(dispatch, Class, resultCLSID=resultCLSID, clsctx=clsctx)


def Moniker(Pathname, clsctx=pythoncom.CLSCTX_ALL):
    """
    Python friendly version of GetObject's moniker functionality.
    """
    moniker, i, bindCtx = pythoncom.MkParseDisplayName(Pathname)
    dispatch = moniker.BindToObject(bindCtx, None, pythoncom.IID_IDispatch)
    return __WrapDispatch(dispatch, Pathname, clsctx=clsctx)


def Dispatch(
    dispatch,
    userName=None,
    resultCLSID=None,
    typeinfo=None,
    clsctx=pythoncom.CLSCTX_SERVER,
):
    """Creates a Dispatch based COM object."""
    dispatch, userName = dynamic._GetGoodDispatchAndUserName(dispatch, userName, clsctx)
    return __WrapDispatch(dispatch, userName, resultCLSID, typeinfo, clsctx=clsctx)


def DispatchEx(
    clsid,
    machine=None,
    userName=None,
    resultCLSID=None,
    typeinfo=None,
    clsctx=None,
):
    """Creates a Dispatch based COM object on a specific machine."""
    # If InProc is registered, DCOM will use it regardless of the machine name
    # (and regardless of the DCOM config for the object.)  So unless the user
    # specifies otherwise, we exclude inproc apps when a remote machine is used.
    if clsctx is None:
        clsctx = pythoncom.CLSCTX_SERVER
        if machine is not None:
            clsctx &= ~pythoncom.CLSCTX_INPROC
    if machine is None:
        serverInfo = None
    else:
        serverInfo = (machine,)
    if userName is None:
        userName = clsid
    dispatch = pythoncom.CoCreateInstanceEx(
        clsid, None, clsctx, serverInfo, (pythoncom.IID_IDispatch,)
    )[0]
    return Dispatch(dispatch, userName, resultCLSID, typeinfo, clsctx=clsctx)


class CDispatch(dynamic.CDispatch):
    """
    The dynamic class used as a last resort.
    The purpose of this overriding of dynamic.CDispatch is to perpetuate the policy
    of using the makepy generated wrapper Python class instead of dynamic.CDispatch
    if/when possible.
    """

    def _wrap_dispatch_(self, ob, userName=None, returnCLSID=None):
        return Dispatch(ob, userName, returnCLSID)

    def __dir__(self):
        return dynamic.CDispatch.__dir__(self)


def CastTo(ob, target, typelib=None):
    """'Cast' a COM object to another interface"""
    # todo - should support target being an IID
    mod = None
    if (
        typelib is not None
    ):  # caller specified target typelib (TypelibSpec). See e.g. selecttlb.EnumTlbs().
        mod = gencache.MakeModuleForTypelib(
            typelib.clsid, typelib.lcid, int(typelib.major, 16), int(typelib.minor, 16)
        )
        if not hasattr(mod, target):
            raise ValueError(
                f"The interface name '{target}' does not appear in the "
                f"specified library {typelib.ver_desc!r}"
            )

    elif hasattr(target, "index"):  # string like
        # for now, we assume makepy for this to work.
        if "CLSID" not in ob.__class__.__dict__:
            # Eeek - no makepy support - try and build it.
            ob = gencache.EnsureDispatch(ob)
        if "CLSID" not in ob.__class__.__dict__:
            raise ValueError("Must be a makepy-able object for this to work")
        clsid = ob.CLSID
        # Lots of hoops to support "demand-build" - ie, generating
        # code for an interface first time it is used.  We assume the
        # interface name exists in the same library as the object.
        # This is generally the case - only referenced typelibs may be
        # a problem, and we can handle that later.  Maybe <wink>
        # So get the generated module for the library itself, then
        # find the interface CLSID there.
        mod = gencache.GetModuleForCLSID(clsid)
        # Get the 'root' module.
        mod = gencache.GetModuleForTypelib(
            mod.CLSID, mod.LCID, mod.MajorVersion, mod.MinorVersion
        )
        # Find the CLSID of the target
        target_clsid = mod.NamesToIIDMap.get(target)
        if target_clsid is None:
            raise ValueError(
                f"The interface name '{target}' does not appear in the "
                f"same library as object '{ob!r}'"
            )
        mod = gencache.GetModuleForCLSID(target_clsid)
    if mod is not None:
        target_class = getattr(mod, target)
        # resolve coclass to interface
        target_class = getattr(target_class, "default_interface", target_class)
        return target_class(ob)  # auto QI magic happens
    raise ValueError


class Constants:
    """A container for generated COM constants."""

    def __init__(self):
        self.__dicts__ = []  # A list of dictionaries

    def __getattr__(self, a):
        for d in self.__dicts__:
            if a in d:
                return d[a]
        raise AttributeError(a)


# And create an instance.
constants = Constants()


# A helpers for DispatchWithEvents - this becomes __setattr__ for the
# temporary class.
def _event_setattr_(self, attr, val):
    try:
        # Does the COM object have an attribute of this name?
        self.__class__.__bases__[0].__setattr__(self, attr, val)
    except AttributeError:
        # Otherwise just stash it away in the instance.
        self.__dict__[attr] = val


# An instance of this "proxy" is created to break the COM circular references
# that exist (ie, when we connect to the COM events, COM keeps a reference
# to the object.  Thus, the Event connection must be manually broken before
# our object can die.  This solves the problem by manually breaking the connection
# to the real object as the proxy dies.
class EventsProxy:
    def __init__(self, ob):
        self.__dict__["_obj_"] = ob

    def __del__(self):
        try:
            # If there is a COM error on disconnection we should
            # just ignore it - object probably already shut down...
            self._obj_.close()
        except pythoncom.com_error:
            pass

    def __getattr__(self, attr):
        return getattr(self._obj_, attr)

    def __setattr__(self, attr, val):
        setattr(self._obj_, attr, val)


def __get_disp_and_event_classes(dispatch):
    # Create/Get the object.
    disp = Dispatch(dispatch)

    if disp.__class__.__dict__.get("CLSID"):
        disp_class = disp.__class__
    else:
        # Eeek - no makepy support - try and build it.
        error_msg = "This COM object can not automate the makepy process - please run makepy manually for this object"
        try:
            ti = disp._oleobj_.GetTypeInfo()
            disp_clsid = ti.GetTypeAttr()[0]
            tlb, index = ti.GetContainingTypeLib()
            tla = tlb.GetLibAttr()
            gencache.EnsureModule(tla[0], tla[1], tla[3], tla[4], bValidateFile=0)
            # Get the class from the module.
            disp_class = gencache.GetClassForProgID(str(disp_clsid))
        except pythoncom.com_error as error:
            raise TypeError(error_msg) from error

        if disp_class is None:
            raise TypeError(error_msg)

    # Get the clsid
    clsid = disp_class.CLSID
    # Create a new class that derives from 2 classes:
    # the event sink class and the user class.
    events_class = getevents(clsid)
    if events_class is None:
        raise ValueError("This COM object does not support events.")
    return disp, disp_class, events_class


def DispatchWithEvents(clsid, user_event_class) -> EventsProxy:
    """Create a COM object that can fire events to a user defined class.
    clsid -- The ProgID or CLSID of the object to create.
    user_event_class -- A Python class object that responds to the events.

    This requires makepy support for the COM object being created.  If
    this support does not exist it will be automatically generated by
    this function.  If the object does not support makepy, a TypeError
    exception will be raised.

    The result is a class instance that both represents the COM object
    and handles events from the COM object.

    It is important to note that the returned instance is not a direct
    instance of the user_event_class, but an instance of a temporary
    class object that derives from three classes:
    * The makepy generated class for the COM object
    * The makepy generated class for the COM events
    * The user_event_class as passed to this function.

    If this is not suitable, see the getevents function for an alternative
    technique of handling events.

    Object Lifetimes:  Whenever the object returned from this function is
    cleaned-up by Python, the events will be disconnected from
    the COM object.  This is almost always what should happen,
    but see the documentation for getevents() for more details.

    Example:

    >>> class IEEvents:
    ...    def OnVisible(self, visible):
    ...       print("Visible changed:", visible)
    ...
    >>> ie = DispatchWithEvents("InternetExplorer.Application", IEEvents)
    >>> ie.Visible = 1
    Visible changed: 1
    """
    disp, disp_class, events_class = __get_disp_and_event_classes(clsid)
    result_class = type(
        "COMEventClass",
        (disp_class, events_class, user_event_class),
        {"__setattr__": _event_setattr_},
    )
    # This only calls the first base class __init__.
    instance = result_class(disp._oleobj_)
    events_class.__init__(instance, instance)
    if hasattr(user_event_class, "__init__"):
        user_event_class.__init__(instance)
    return EventsProxy(instance)


def WithEvents(disp, user_event_class):
    """Similar to DispatchWithEvents - except that the returned
    object is *not* also usable as the original Dispatch object - that is
    the returned object is not dispatchable.

    The difference is best summarised by example.

    >>> class IEEvents:
    ...    def OnVisible(self, visible):
    ...       print("Visible changed:", visible)
    ...
    >>> ie = Dispatch("InternetExplorer.Application")
    >>> ie_events = WithEvents(ie, IEEvents)
    >>> ie.Visible = 1
    Visible changed: 1

    Compare with the code sample for DispatchWithEvents, where you get a
    single object that is both the interface and the event handler.  Note that
    the event handler instance will *not* be able to use 'self.' to refer to
    IE's methods and properties.

    This is mainly useful where using DispatchWithEvents causes
    circular reference problems that the simple proxy doesn't deal with
    """
    disp, disp_class, events_class = __get_disp_and_event_classes(disp)
    result_class = type(
        "COMEventClass",
        (events_class, user_event_class),
        {},
    )
    # This only calls the first base class __init__.
    instance = result_class(disp)
    if hasattr(user_event_class, "__init__"):
        user_event_class.__init__(instance)
    return instance


def getevents(clsid):
    """Determine the default outgoing interface for a class, given
    either a clsid or progid. It returns a class - you can
    conveniently derive your own handler from this class and implement
    the appropriate methods.

    This method relies on the classes produced by makepy. You must use
    either makepy or the gencache module to ensure that the
    appropriate support classes have been generated for the com server
    that you will be handling events from.

    Beware of COM circular references.  When the Events class is connected
    to the COM object, the COM object itself keeps a reference to the Python
    events class.  Thus, neither the Events instance or the COM object will
    ever die by themselves.  The 'close' method on the events instance
    must be called to break this chain and allow standard Python collection
    rules to manage object lifetimes.  Note that DispatchWithEvents() does
    work around this problem by the use of a proxy object, but if you use
    the getevents() function yourself, you must make your own arrangements
    to manage this circular reference issue.

    Beware of creating Python circular references: this will happen if your
    handler has a reference to an object that has a reference back to
    the event source. Call the 'close' method to break the chain.

    Example:

    >>>win32com.client.gencache.EnsureModule('{EAB22AC0-30C1-11CF-A7EB-0000C05BAE0B}',0,1,1)
    <module 'win32com.gen_py.....
    >>>
    >>> class InternetExplorerEvents(win32com.client.getevents("InternetExplorer.Application.1")):
    ...    def OnVisible(self, Visible):
    ...        print("Visibility changed: ", Visible)
    ...
    >>>
    >>> ie=win32com.client.Dispatch("InternetExplorer.Application.1")
    >>> events=InternetExplorerEvents(ie)
    >>> ie.Visible=1
    Visibility changed:  1
    >>>
    """

    # find clsid given progid or clsid
    clsid = str(pywintypes.IID(clsid))
    # return default outgoing interface for that class
    klass = gencache.GetClassForCLSID(clsid)
    try:
        return klass.default_source
    except AttributeError:
        # See if we have a coclass for the interfaces.
        try:
            return gencache.GetClassForCLSID(klass.coclass_clsid).default_source
        except AttributeError:
            return None


# A Record object, as used by the COM struct support
def Record(name, object):
    """Creates a new record object, given the name of the record,
    and an object from the same type library.

    Example usage would be:
      app = win32com.client.Dispatch("Some.Application")
      point = win32com.client.Record("SomeAppPoint", app)
      point.x = 0
      point.y = 0
      app.MoveTo(point)
    """
    # XXX - to do - probably should allow "object" to already be a module object.
    from . import gencache

    object = gencache.EnsureDispatch(object)
    module = sys.modules[object.__class__.__module__]
    # to allow us to work correctly with "demand generated" code,
    # we must use the typelib CLSID to obtain the module
    # (otherwise we get the sub-module for the object, which
    # does not hold the records)
    # thus, package may be module, or may be module's parent if demand generated.
    package = gencache.GetModuleForTypelib(
        module.CLSID, module.LCID, module.MajorVersion, module.MinorVersion
    )
    try:
        struct_guid = package.RecordMap[name]
    except KeyError:
        raise ValueError(f"The structure '{name}' is not defined in module '{package}'")
    return pythoncom.GetRecordFromGuids(
        module.CLSID, module.MajorVersion, module.MinorVersion, module.LCID, struct_guid
    )


# Registration function for com_record subclasses.
def register_record_class(cls):
    """
    Register a subclass of com_record to enable creation of the represented record objects.

    A subclass of com_record requires the following class attributes to be instantiable:

        TLBID : The GUID of the containing TypeLibrary as a string.
        MJVER : The major version number of the TypeLibrary as an integer.
        MNVER : The minor version number of the TypeLibrary as an integer.
        LCID  : The LCID of the TypeLibrary as an integer.
        GUID  : The GUID of the COM Record as a string.

    with GUID strings in {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx} notation.

    To instantiate such a subclasses it has to be registered via this function.
    """
    if not issubclass(cls, pythoncom.com_record):
        raise TypeError("Only subclasses of 'com_record' can be registered.")
    try:
        TLBID = cls.TLBID
        MJVER = cls.MJVER
        MNVER = cls.MNVER
        LCID = cls.LCID
        GUID = cls.GUID
    except AttributeError as e:
        raise AttributeError(f"Class {cls.__name__} cannot be instantiated.") from e
    try:
        _ = pythoncom.GetRecordFromGuids(TLBID, MJVER, MNVER, LCID, GUID)
    except Exception as e:
        raise TypeError(f"Class {cls.__name__} cannot be instantiated.") from e
    # Since the class can be instantiated we know that it represents a valid COM Record
    # in a properly registered TypeLibrary and that it has a 'GUID' class attribute.
    if cls.GUID in pythoncom.RecordClasses:
        raise ValueError(
            f"Record class with same GUID {cls.GUID} "
            f"is already registered with name '{pythoncom.RecordClasses[cls.GUID].__name__}'."
        )
    pythoncom.RecordClasses[cls.GUID] = cls


############################################
# The base of all makepy generated classes
############################################
class DispatchBaseClass:
    def __init__(self, oobj=None):
        if oobj is None:
            oobj = pythoncom.new(self.CLSID)
        elif isinstance(oobj, DispatchBaseClass):
            try:
                oobj = oobj._oleobj_.QueryInterface(
                    self.CLSID, pythoncom.IID_IDispatch
                )  # Must be a valid COM instance
            except pythoncom.com_error as details:
                import winerror

                # Some stupid objects fail here, even tho it is _already_ IDispatch!!??
                # Eg, Lotus notes.
                # So just let it use the existing object if E_NOINTERFACE
                if details.hresult != winerror.E_NOINTERFACE:
                    raise
                oobj = oobj._oleobj_
        self.__dict__["_oleobj_"] = oobj  # so we don't call __setattr__

    def __dir__(self):
        attributes = chain(
            self.__dict__,
            dir(self.__class__),
            self._prop_map_get_,
            self._prop_map_put_,
        )

        try:
            attributes = chain(attributes, [p.Name for p in self.Properties_])
        except AttributeError:
            pass
        return list(set(attributes))

    # Provide a prettier name than the CLSID
    def __repr__(self):
        # Need to get the docstring for the module for this class.
        try:
            mod_doc = sys.modules[self.__class__.__module__].__doc__
            if mod_doc:
                mod_name = "win32com.gen_py." + mod_doc
            else:
                mod_name = sys.modules[self.__class__.__module__].__name__
        except KeyError:
            mod_name = "win32com.gen_py.unknown"
        return f"<{mod_name}.{self.__class__.__name__} instance at 0x{id(self)}>"

    # Delegate comparison to the oleobjs, as they know how to do identity.
    def __eq__(self, other):
        other = getattr(other, "_oleobj_", other)
        return self._oleobj_ == other

    def __ne__(self, other):
        other = getattr(other, "_oleobj_", other)
        return self._oleobj_ != other

    def _ApplyTypes_(self, dispid, wFlags, retType, argTypes, user, resultCLSID, *args):
        return self._get_good_object_(
            self._oleobj_.InvokeTypes(dispid, 0, wFlags, retType, argTypes, *args),
            user,
            resultCLSID,
        )

    def __getattr__(self, attr):
        args = self._prop_map_get_.get(attr)
        if args is None:
            raise AttributeError(f"'{self!r}' object has no attribute '{attr}'")
        return self._ApplyTypes_(*args)

    def __setattr__(self, attr, value):
        if attr in self.__dict__:
            self.__dict__[attr] = value
            return
        try:
            args, defArgs = self._prop_map_put_[attr]
        except KeyError:
            raise AttributeError(f"'{self!r}' object has no attribute '{attr}'")
        self._oleobj_.Invoke(*(args + (value,) + defArgs))

    def _get_good_single_object_(self, obj, obUserName=None, resultCLSID=None):
        return _get_good_single_object_(obj, obUserName, resultCLSID)

    def _get_good_object_(self, obj, obUserName=None, resultCLSID=None):
        return _get_good_object_(obj, obUserName, resultCLSID)


# XXX - These should be consolidated with dynamic.py versions.
def _get_good_single_object_(obj, obUserName=None, resultCLSID=None):
    if isinstance(obj, _PyIDispatchType):
        return Dispatch(obj, obUserName, resultCLSID)
    return obj


def _get_good_object_(obj, obUserName=None, resultCLSID=None):
    if obj is None:
        return None
    elif isinstance(obj, tuple):
        obUserNameTuple = (obUserName,) * len(obj)
        resultCLSIDTuple = (resultCLSID,) * len(obj)
        return tuple(map(_get_good_object_, obj, obUserNameTuple, resultCLSIDTuple))
    else:
        return _get_good_single_object_(obj, obUserName, resultCLSID)


class CoClassBaseClass:
    def __init__(self, oobj=None):
        if oobj is None:
            oobj = pythoncom.new(self.CLSID)
        dispobj = self.__dict__["_dispobj_"] = self.default_interface(oobj)
        # See comments below re the special methods.
        for maybe in [
            "__call__",
            "__str__",
            "__int__",
            "__iter__",
            "__len__",
            "__bool__",
        ]:
            if hasattr(dispobj, maybe):
                setattr(self, maybe, getattr(self, "__maybe" + maybe))

    def __repr__(self):
        return f"<win32com.gen_py.{__doc__}.{self.__class__.__name__}>"

    def __getattr__(self, attr):
        d = self.__dict__["_dispobj_"]
        if d is not None:
            return getattr(d, attr)
        raise AttributeError(attr)

    def __setattr__(self, attr, value):
        if attr in self.__dict__:
            self.__dict__[attr] = value
            return
        try:
            d = self.__dict__["_dispobj_"]
            if d is not None:
                d.__setattr__(attr, value)
                return
        except AttributeError:
            pass
        self.__dict__[attr] = value

        # Special methods don't use __getattr__ etc, so explicitly delegate here.
        # Note however, that not all are safe to let bubble up - things like
        # `bool(ob)` will break if the object defines __int__ but then raises an
        # attribute error - eg, see #1753.
        # It depends on what the wrapped COM object actually defines whether these
        # will exist on the underlying object, so __init__ explicitly checks if they
        # do and if so, wires them up.

    def __maybe__call__(self, *args, **kwargs):
        return self.__dict__["_dispobj_"].__call__(*args, **kwargs)

    def __maybe__str__(self, *args):
        return self.__dict__["_dispobj_"].__str__(*args)

    def __maybe__int__(self, *args):
        return self.__dict__["_dispobj_"].__int__(*args)

    def __maybe__iter__(self):
        return self.__dict__["_dispobj_"].__iter__()

    def __maybe__len__(self):
        return self.__dict__["_dispobj_"].__len__()

    def __maybe__bool__(self):
        return self.__dict__["_dispobj_"].__bool__()


# A very simple VARIANT class.  Only to be used with poorly-implemented COM
# objects.  If an object accepts an arg which is a simple "VARIANT", but still
# is very pickly about the actual variant type (eg, isn't happy with a VT_I4,
# which it would get from a Python integer), you can use this to force a
# particular VT.
class VARIANT:
    def __init__(self, vt, value):
        self.varianttype = vt
        self._value = value

    # 'value' is a property so when set by pythoncom it gets any magic wrapping
    # which normally happens for result objects
    def _get_value(self):
        return self._value

    def _set_value(self, newval):
        self._value = _get_good_object_(newval)

    def _del_value(self):
        del self._value

    value = property(_get_value, _set_value, _del_value)

    def __repr__(self):
        return f"win32com.client.VARIANT({self.varianttype!r}, {self._value!r})"

# === NexusCore/openenv\Lib\site-packages\nltk\parse\projectivedependencyparser.py ===
# Natural Language Toolkit: Dependency Grammars
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Jason Narad <jason.narad@gmail.com>
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#

from collections import defaultdict
from functools import total_ordering
from itertools import chain

from nltk.grammar import (
    DependencyGrammar,
    DependencyProduction,
    ProbabilisticDependencyGrammar,
)
from nltk.internals import raise_unorderable_types
from nltk.parse.dependencygraph import DependencyGraph

#################################################################
# Dependency Span
#################################################################


@total_ordering
class DependencySpan:
    """
    A contiguous span over some part of the input string representing
    dependency (head -> modifier) relationships amongst words.  An atomic
    span corresponds to only one word so it isn't a 'span' in the conventional
    sense, as its _start_index = _end_index = _head_index for concatenation
    purposes.  All other spans are assumed to have arcs between all nodes
    within the start and end indexes of the span, and one head index corresponding
    to the head word for the entire span.  This is the same as the root node if
    the dependency structure were depicted as a graph.
    """

    def __init__(self, start_index, end_index, head_index, arcs, tags):
        self._start_index = start_index
        self._end_index = end_index
        self._head_index = head_index
        self._arcs = arcs
        self._tags = tags
        self._comparison_key = (start_index, end_index, head_index, tuple(arcs))
        self._hash = hash(self._comparison_key)

    def head_index(self):
        """
        :return: An value indexing the head of the entire ``DependencySpan``.
        :rtype: int
        """
        return self._head_index

    def __repr__(self):
        """
        :return: A concise string representatino of the ``DependencySpan``.
        :rtype: str.
        """
        return "Span %d-%d; Head Index: %d" % (
            self._start_index,
            self._end_index,
            self._head_index,
        )

    def __str__(self):
        """
        :return: A verbose string representation of the ``DependencySpan``.
        :rtype: str
        """
        str = "Span %d-%d; Head Index: %d" % (
            self._start_index,
            self._end_index,
            self._head_index,
        )
        for i in range(len(self._arcs)):
            str += "\n%d <- %d, %s" % (i, self._arcs[i], self._tags[i])
        return str

    def __eq__(self, other):
        return (
            type(self) == type(other) and self._comparison_key == other._comparison_key
        )

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, DependencySpan):
            raise_unorderable_types("<", self, other)
        return self._comparison_key < other._comparison_key

    def __hash__(self):
        """
        :return: The hash value of this ``DependencySpan``.
        """
        return self._hash


#################################################################
# Chart Cell
#################################################################


class ChartCell:
    """
    A cell from the parse chart formed when performing the CYK algorithm.
    Each cell keeps track of its x and y coordinates (though this will probably
    be discarded), and a list of spans serving as the cell's entries.
    """

    def __init__(self, x, y):
        """
        :param x: This cell's x coordinate.
        :type x: int.
        :param y: This cell's y coordinate.
        :type y: int.
        """
        self._x = x
        self._y = y
        self._entries = set()

    def add(self, span):
        """
        Appends the given span to the list of spans
        representing the chart cell's entries.

        :param span: The span to add.
        :type span: DependencySpan
        """
        self._entries.add(span)

    def __str__(self):
        """
        :return: A verbose string representation of this ``ChartCell``.
        :rtype: str.
        """
        return "CC[%d,%d]: %s" % (self._x, self._y, self._entries)

    def __repr__(self):
        """
        :return: A concise string representation of this ``ChartCell``.
        :rtype: str.
        """
        return "%s" % self


#################################################################
# Parsing  with Dependency Grammars
#################################################################


class ProjectiveDependencyParser:
    """
    A projective, rule-based, dependency parser.  A ProjectiveDependencyParser
    is created with a DependencyGrammar, a set of productions specifying
    word-to-word dependency relations.  The parse() method will then
    return the set of all parses, in tree representation, for a given input
    sequence of tokens.  Each parse must meet the requirements of the both
    the grammar and the projectivity constraint which specifies that the
    branches of the dependency tree are not allowed to cross.  Alternatively,
    this can be understood as stating that each parent node and its children
    in the parse tree form a continuous substring of the input sequence.
    """

    def __init__(self, dependency_grammar):
        """
        Create a new ProjectiveDependencyParser, from a word-to-word
        dependency grammar ``DependencyGrammar``.

        :param dependency_grammar: A word-to-word relation dependencygrammar.
        :type dependency_grammar: DependencyGrammar
        """
        self._grammar = dependency_grammar

    def parse(self, tokens):
        """
        Performs a projective dependency parse on the list of tokens using
        a chart-based, span-concatenation algorithm similar to Eisner (1996).

        :param tokens: The list of input tokens.
        :type tokens: list(str)
        :return: An iterator over parse trees.
        :rtype: iter(Tree)
        """
        self._tokens = list(tokens)
        chart = []
        for i in range(0, len(self._tokens) + 1):
            chart.append([])
            for j in range(0, len(self._tokens) + 1):
                chart[i].append(ChartCell(i, j))
                if i == j + 1:
                    chart[i][j].add(DependencySpan(i - 1, i, i - 1, [-1], ["null"]))

        for i in range(1, len(self._tokens) + 1):
            for j in range(i - 2, -1, -1):
                for k in range(i - 1, j, -1):
                    for span1 in chart[k][j]._entries:
                        for span2 in chart[i][k]._entries:
                            for newspan in self.concatenate(span1, span2):
                                chart[i][j].add(newspan)

        for parse in chart[len(self._tokens)][0]._entries:
            conll_format = ""
            #            malt_format = ""
            for i in range(len(tokens)):
                #                malt_format += '%s\t%s\t%d\t%s\n' % (tokens[i], 'null', parse._arcs[i] + 1, 'null')
                # conll_format += '\t%d\t%s\t%s\t%s\t%s\t%s\t%d\t%s\t%s\t%s\n' % (i+1, tokens[i], tokens[i], 'null', 'null', 'null', parse._arcs[i] + 1, 'null', '-', '-')
                # Modify to comply with the new Dependency Graph requirement (at least must have an root elements)
                conll_format += "\t%d\t%s\t%s\t%s\t%s\t%s\t%d\t%s\t%s\t%s\n" % (
                    i + 1,
                    tokens[i],
                    tokens[i],
                    "null",
                    "null",
                    "null",
                    parse._arcs[i] + 1,
                    "ROOT",
                    "-",
                    "-",
                )
            dg = DependencyGraph(conll_format)
            #           if self.meets_arity(dg):
            yield dg.tree()

    def concatenate(self, span1, span2):
        """
        Concatenates the two spans in whichever way possible.  This
        includes rightward concatenation (from the leftmost word of the
        leftmost span to the rightmost word of the rightmost span) and
        leftward concatenation (vice-versa) between adjacent spans.  Unlike
        Eisner's presentation of span concatenation, these spans do not
        share or pivot on a particular word/word-index.

        :return: A list of new spans formed through concatenation.
        :rtype: list(DependencySpan)
        """
        spans = []
        if span1._start_index == span2._start_index:
            print("Error: Mismatched spans - replace this with thrown error")
        if span1._start_index > span2._start_index:
            temp_span = span1
            span1 = span2
            span2 = temp_span
        # adjacent rightward covered concatenation
        new_arcs = span1._arcs + span2._arcs
        new_tags = span1._tags + span2._tags
        if self._grammar.contains(
            self._tokens[span1._head_index], self._tokens[span2._head_index]
        ):
            #           print('Performing rightward cover %d to %d' % (span1._head_index, span2._head_index))
            new_arcs[span2._head_index - span1._start_index] = span1._head_index
            spans.append(
                DependencySpan(
                    span1._start_index,
                    span2._end_index,
                    span1._head_index,
                    new_arcs,
                    new_tags,
                )
            )
        # adjacent leftward covered concatenation
        new_arcs = span1._arcs + span2._arcs
        if self._grammar.contains(
            self._tokens[span2._head_index], self._tokens[span1._head_index]
        ):
            #           print('performing leftward cover %d to %d' % (span2._head_index, span1._head_index))
            new_arcs[span1._head_index - span1._start_index] = span2._head_index
            spans.append(
                DependencySpan(
                    span1._start_index,
                    span2._end_index,
                    span2._head_index,
                    new_arcs,
                    new_tags,
                )
            )
        return spans


#################################################################
# Parsing  with Probabilistic Dependency Grammars
#################################################################


class ProbabilisticProjectiveDependencyParser:
    """A probabilistic, projective dependency parser.

    This parser returns the most probable projective parse derived from the
    probabilistic dependency grammar derived from the train() method.  The
    probabilistic model is an implementation of Eisner's (1996) Model C, which
    conditions on head-word, head-tag, child-word, and child-tag.  The decoding
    uses a bottom-up chart-based span concatenation algorithm that's identical
    to the one utilized by the rule-based projective parser.

    Usage example

    >>> from nltk.parse.dependencygraph import conll_data2

    >>> graphs = [
    ... DependencyGraph(entry) for entry in conll_data2.split('\\n\\n') if entry
    ... ]

    >>> ppdp = ProbabilisticProjectiveDependencyParser()
    >>> ppdp.train(graphs)

    >>> sent = ['Cathy', 'zag', 'hen', 'wild', 'zwaaien', '.']
    >>> list(ppdp.parse(sent))
    [Tree('zag', ['Cathy', 'hen', Tree('zwaaien', ['wild', '.'])])]

    """

    def __init__(self):
        """
        Create a new probabilistic dependency parser.  No additional
        operations are necessary.
        """

    def parse(self, tokens):
        """
        Parses the list of tokens subject to the projectivity constraint
        and the productions in the parser's grammar.  This uses a method
        similar to the span-concatenation algorithm defined in Eisner (1996).
        It returns the most probable parse derived from the parser's
        probabilistic dependency grammar.
        """
        self._tokens = list(tokens)
        chart = []
        for i in range(0, len(self._tokens) + 1):
            chart.append([])
            for j in range(0, len(self._tokens) + 1):
                chart[i].append(ChartCell(i, j))
                if i == j + 1:
                    if tokens[i - 1] in self._grammar._tags:
                        for tag in self._grammar._tags[tokens[i - 1]]:
                            chart[i][j].add(
                                DependencySpan(i - 1, i, i - 1, [-1], [tag])
                            )
                    else:
                        print(
                            "No tag found for input token '%s', parse is impossible."
                            % tokens[i - 1]
                        )
                        return []
        for i in range(1, len(self._tokens) + 1):
            for j in range(i - 2, -1, -1):
                for k in range(i - 1, j, -1):
                    for span1 in chart[k][j]._entries:
                        for span2 in chart[i][k]._entries:
                            for newspan in self.concatenate(span1, span2):
                                chart[i][j].add(newspan)
        trees = []
        max_parse = None
        max_score = 0
        for parse in chart[len(self._tokens)][0]._entries:
            conll_format = ""
            malt_format = ""
            for i in range(len(tokens)):
                malt_format += "%s\t%s\t%d\t%s\n" % (
                    tokens[i],
                    "null",
                    parse._arcs[i] + 1,
                    "null",
                )
                # conll_format += '\t%d\t%s\t%s\t%s\t%s\t%s\t%d\t%s\t%s\t%s\n' % (i+1, tokens[i], tokens[i], parse._tags[i], parse._tags[i], 'null', parse._arcs[i] + 1, 'null', '-', '-')
                # Modify to comply with recent change in dependency graph such that there must be a ROOT element.
                conll_format += "\t%d\t%s\t%s\t%s\t%s\t%s\t%d\t%s\t%s\t%s\n" % (
                    i + 1,
                    tokens[i],
                    tokens[i],
                    parse._tags[i],
                    parse._tags[i],
                    "null",
                    parse._arcs[i] + 1,
                    "ROOT",
                    "-",
                    "-",
                )
            dg = DependencyGraph(conll_format)
            score = self.compute_prob(dg)
            trees.append((score, dg.tree()))
        trees.sort()
        return (tree for (score, tree) in trees)

    def concatenate(self, span1, span2):
        """
        Concatenates the two spans in whichever way possible.  This
        includes rightward concatenation (from the leftmost word of the
        leftmost span to the rightmost word of the rightmost span) and
        leftward concatenation (vice-versa) between adjacent spans.  Unlike
        Eisner's presentation of span concatenation, these spans do not
        share or pivot on a particular word/word-index.

        :return: A list of new spans formed through concatenation.
        :rtype: list(DependencySpan)
        """
        spans = []
        if span1._start_index == span2._start_index:
            print("Error: Mismatched spans - replace this with thrown error")
        if span1._start_index > span2._start_index:
            temp_span = span1
            span1 = span2
            span2 = temp_span
        # adjacent rightward covered concatenation
        new_arcs = span1._arcs + span2._arcs
        new_tags = span1._tags + span2._tags
        if self._grammar.contains(
            self._tokens[span1._head_index], self._tokens[span2._head_index]
        ):
            new_arcs[span2._head_index - span1._start_index] = span1._head_index
            spans.append(
                DependencySpan(
                    span1._start_index,
                    span2._end_index,
                    span1._head_index,
                    new_arcs,
                    new_tags,
                )
            )
        # adjacent leftward covered concatenation
        new_arcs = span1._arcs + span2._arcs
        new_tags = span1._tags + span2._tags
        if self._grammar.contains(
            self._tokens[span2._head_index], self._tokens[span1._head_index]
        ):
            new_arcs[span1._head_index - span1._start_index] = span2._head_index
            spans.append(
                DependencySpan(
                    span1._start_index,
                    span2._end_index,
                    span2._head_index,
                    new_arcs,
                    new_tags,
                )
            )
        return spans

    def train(self, graphs):
        """
        Trains a ProbabilisticDependencyGrammar based on the list of input
        DependencyGraphs.  This model is an implementation of Eisner's (1996)
        Model C, which derives its statistics from head-word, head-tag,
        child-word, and child-tag relationships.

        :param graphs: A list of dependency graphs to train from.
        :type: list(DependencyGraph)
        """
        productions = []
        events = defaultdict(int)
        tags = {}
        for dg in graphs:
            for node_index in range(1, len(dg.nodes)):
                # children = dg.nodes[node_index]['deps']
                children = list(
                    chain.from_iterable(dg.nodes[node_index]["deps"].values())
                )

                nr_left_children = dg.left_children(node_index)
                nr_right_children = dg.right_children(node_index)
                nr_children = nr_left_children + nr_right_children
                for child_index in range(
                    0 - (nr_left_children + 1), nr_right_children + 2
                ):
                    head_word = dg.nodes[node_index]["word"]
                    head_tag = dg.nodes[node_index]["tag"]
                    if head_word in tags:
                        tags[head_word].add(head_tag)
                    else:
                        tags[head_word] = {head_tag}
                    child = "STOP"
                    child_tag = "STOP"
                    prev_word = "START"
                    prev_tag = "START"
                    if child_index < 0:
                        array_index = child_index + nr_left_children
                        if array_index >= 0:
                            child = dg.nodes[children[array_index]]["word"]
                            child_tag = dg.nodes[children[array_index]]["tag"]
                        if child_index != -1:
                            prev_word = dg.nodes[children[array_index + 1]]["word"]
                            prev_tag = dg.nodes[children[array_index + 1]]["tag"]
                        if child != "STOP":
                            productions.append(DependencyProduction(head_word, [child]))
                        head_event = "(head ({} {}) (mods ({}, {}, {}) left))".format(
                            child,
                            child_tag,
                            prev_tag,
                            head_word,
                            head_tag,
                        )
                        mod_event = "(mods ({}, {}, {}) left))".format(
                            prev_tag,
                            head_word,
                            head_tag,
                        )
                        events[head_event] += 1
                        events[mod_event] += 1
                    elif child_index > 0:
                        array_index = child_index + nr_left_children - 1
                        if array_index < nr_children:
                            child = dg.nodes[children[array_index]]["word"]
                            child_tag = dg.nodes[children[array_index]]["tag"]
                        if child_index != 1:
                            prev_word = dg.nodes[children[array_index - 1]]["word"]
                            prev_tag = dg.nodes[children[array_index - 1]]["tag"]
                        if child != "STOP":
                            productions.append(DependencyProduction(head_word, [child]))
                        head_event = "(head ({} {}) (mods ({}, {}, {}) right))".format(
                            child,
                            child_tag,
                            prev_tag,
                            head_word,
                            head_tag,
                        )
                        mod_event = "(mods ({}, {}, {}) right))".format(
                            prev_tag,
                            head_word,
                            head_tag,
                        )
                        events[head_event] += 1
                        events[mod_event] += 1
        self._grammar = ProbabilisticDependencyGrammar(productions, events, tags)

    def compute_prob(self, dg):
        """
        Computes the probability of a dependency graph based
        on the parser's probability model (defined by the parser's
        statistical dependency grammar).

        :param dg: A dependency graph to score.
        :type dg: DependencyGraph
        :return: The probability of the dependency graph.
        :rtype: int
        """
        prob = 1.0
        for node_index in range(1, len(dg.nodes)):
            # children = dg.nodes[node_index]['deps']
            children = list(chain.from_iterable(dg.nodes[node_index]["deps"].values()))

            nr_left_children = dg.left_children(node_index)
            nr_right_children = dg.right_children(node_index)
            nr_children = nr_left_children + nr_right_children
            for child_index in range(0 - (nr_left_children + 1), nr_right_children + 2):
                head_word = dg.nodes[node_index]["word"]
                head_tag = dg.nodes[node_index]["tag"]
                child = "STOP"
                child_tag = "STOP"
                prev_word = "START"
                prev_tag = "START"
                if child_index < 0:
                    array_index = child_index + nr_left_children
                    if array_index >= 0:
                        child = dg.nodes[children[array_index]]["word"]
                        child_tag = dg.nodes[children[array_index]]["tag"]
                    if child_index != -1:
                        prev_word = dg.nodes[children[array_index + 1]]["word"]
                        prev_tag = dg.nodes[children[array_index + 1]]["tag"]
                    head_event = "(head ({} {}) (mods ({}, {}, {}) left))".format(
                        child,
                        child_tag,
                        prev_tag,
                        head_word,
                        head_tag,
                    )
                    mod_event = "(mods ({}, {}, {}) left))".format(
                        prev_tag,
                        head_word,
                        head_tag,
                    )
                    h_count = self._grammar._events[head_event]
                    m_count = self._grammar._events[mod_event]

                    # If the grammar is not covered
                    if m_count != 0:
                        prob *= h_count / m_count
                    else:
                        prob = 0.00000001  # Very small number

                elif child_index > 0:
                    array_index = child_index + nr_left_children - 1
                    if array_index < nr_children:
                        child = dg.nodes[children[array_index]]["word"]
                        child_tag = dg.nodes[children[array_index]]["tag"]
                    if child_index != 1:
                        prev_word = dg.nodes[children[array_index - 1]]["word"]
                        prev_tag = dg.nodes[children[array_index - 1]]["tag"]
                    head_event = "(head ({} {}) (mods ({}, {}, {}) right))".format(
                        child,
                        child_tag,
                        prev_tag,
                        head_word,
                        head_tag,
                    )
                    mod_event = "(mods ({}, {}, {}) right))".format(
                        prev_tag,
                        head_word,
                        head_tag,
                    )
                    h_count = self._grammar._events[head_event]
                    m_count = self._grammar._events[mod_event]

                    if m_count != 0:
                        prob *= h_count / m_count
                    else:
                        prob = 0.00000001  # Very small number

        return prob


#################################################################
# Demos
#################################################################


def demo():
    projective_rule_parse_demo()
    #    arity_parse_demo()
    projective_prob_parse_demo()


def projective_rule_parse_demo():
    """
    A demonstration showing the creation and use of a
    ``DependencyGrammar`` to perform a projective dependency
    parse.
    """
    grammar = DependencyGrammar.fromstring(
        """
    'scratch' -> 'cats' | 'walls'
    'walls' -> 'the'
    'cats' -> 'the'
    """
    )
    print(grammar)
    pdp = ProjectiveDependencyParser(grammar)
    trees = pdp.parse(["the", "cats", "scratch", "the", "walls"])
    for tree in trees:
        print(tree)


def arity_parse_demo():
    """
    A demonstration showing the creation of a ``DependencyGrammar``
    in which a specific number of modifiers is listed for a given
    head.  This can further constrain the number of possible parses
    created by a ``ProjectiveDependencyParser``.
    """
    print()
    print("A grammar with no arity constraints. Each DependencyProduction")
    print("specifies a relationship between one head word and only one")
    print("modifier word.")
    grammar = DependencyGrammar.fromstring(
        """
    'fell' -> 'price' | 'stock'
    'price' -> 'of' | 'the'
    'of' -> 'stock'
    'stock' -> 'the'
    """
    )
    print(grammar)

    print()
    print("For the sentence 'The price of the stock fell', this grammar")
    print("will produce the following three parses:")
    pdp = ProjectiveDependencyParser(grammar)
    trees = pdp.parse(["the", "price", "of", "the", "stock", "fell"])
    for tree in trees:
        print(tree)

    print()
    print("By contrast, the following grammar contains a ")
    print("DependencyProduction that specifies a relationship")
    print("between a single head word, 'price', and two modifier")
    print("words, 'of' and 'the'.")
    grammar = DependencyGrammar.fromstring(
        """
    'fell' -> 'price' | 'stock'
    'price' -> 'of' 'the'
    'of' -> 'stock'
    'stock' -> 'the'
    """
    )
    print(grammar)

    print()
    print(
        "This constrains the number of possible parses to just one:"
    )  # unimplemented, soon to replace
    pdp = ProjectiveDependencyParser(grammar)
    trees = pdp.parse(["the", "price", "of", "the", "stock", "fell"])
    for tree in trees:
        print(tree)


def projective_prob_parse_demo():
    """
    A demo showing the training and use of a projective
    dependency parser.
    """
    from nltk.parse.dependencygraph import conll_data2

    graphs = [DependencyGraph(entry) for entry in conll_data2.split("\n\n") if entry]
    ppdp = ProbabilisticProjectiveDependencyParser()
    print("Training Probabilistic Projective Dependency Parser...")
    ppdp.train(graphs)

    sent = ["Cathy", "zag", "hen", "wild", "zwaaien", "."]
    print("Parsing '", " ".join(sent), "'...")
    print("Parse:")
    for tree in ppdp.parse(sent):
        print(tree)


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pyreadline3\modes\emacs.py ===
# -*- coding: utf-8 -*-
# *****************************************************************************
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006-2020 Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#       Copyright (C) 2020 Bassem Girgis. <brgirgis@gmail.com>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# *****************************************************************************


import pyreadline3.lineeditor.lineobj as lineobj
from pyreadline3.lineeditor.lineobj import Point
from pyreadline3.logger import log

from . import basemode


class IncrementalSearchPromptMode(object):
    def __init__(self, rlobj):
        pass

    def _process_incremental_search_keyevent(self, keyinfo):
        log("_process_incremental_search_keyevent")
        keytuple = keyinfo.tuple()
        # dispatch_func = self.key_dispatch.get(keytuple, default)
        revtuples = []
        fwdtuples = []
        for ktuple, func in self.key_dispatch.items():
            if func == self.reverse_search_history:
                revtuples.append(ktuple)
            elif func == self.forward_search_history:
                fwdtuples.append(ktuple)

        log("IncrementalSearchPromptMode %s %s" % (keyinfo, keytuple))
        if keyinfo.keyname == "backspace":
            self.subsearch_query = self.subsearch_query[:-1]
            if len(self.subsearch_query) > 0:
                self.line = self.subsearch_fun(self.subsearch_query)
            else:
                self._bell()
                self.line = ""  # empty query means no search result
        elif keyinfo.keyname in ["return", "escape"]:
            self._bell()
            self.prompt = self.subsearch_oldprompt
            self.process_keyevent_queue = self.process_keyevent_queue[:-1]
            self._history.history_cursor = len(self._history.history)
            if keyinfo.keyname == "escape":
                self.l_buffer.set_line(self.subsearch_old_line)
            return True
        elif keyinfo.keyname:
            pass
        elif keytuple in revtuples:
            self.subsearch_fun = self._history.reverse_search_history
            self.subsearch_prompt = "reverse-i-search%d`%s': "
            self.line = self.subsearch_fun(self.subsearch_query)
        elif keytuple in fwdtuples:
            self.subsearch_fun = self._history.forward_search_history
            self.subsearch_prompt = "forward-i-search%d`%s': "
            self.line = self.subsearch_fun(self.subsearch_query)
        elif keyinfo.control == False and keyinfo.meta == False:
            self.subsearch_query += keyinfo.char
            self.line = self.subsearch_fun(self.subsearch_query)
        else:
            pass
        self.prompt = self.subsearch_prompt % (
            self._history.history_cursor,
            self.subsearch_query,
        )
        self.l_buffer.set_line(self.line)

    def _init_incremental_search(self, searchfun, init_event):
        """Initialize search prompt"""
        log("init_incremental_search")
        self.subsearch_query = ""
        self.subsearch_fun = searchfun
        self.subsearch_old_line = self.l_buffer.get_line_text()

        queue = self.process_keyevent_queue
        queue.append(self._process_incremental_search_keyevent)

        self.subsearch_oldprompt = self.prompt

        if (
            self.previous_func != self.reverse_search_history
            and self.previous_func != self.forward_search_history
        ):
            self.subsearch_query = self.l_buffer[0:Point].get_line_text()

        if self.subsearch_fun == self.reverse_search_history:
            self.subsearch_prompt = "reverse-i-search%d`%s': "
        else:
            self.subsearch_prompt = "forward-i-search%d`%s': "

        self.prompt = self.subsearch_prompt % (self._history.history_cursor, "")

        if self.subsearch_query:
            self.line = self._process_incremental_search_keyevent(init_event)
        else:
            self.line = ""


class SearchPromptMode(object):
    def __init__(self, rlobj):
        pass

    def _process_non_incremental_search_keyevent(self, keyinfo):
        keytuple = keyinfo.tuple()
        log("SearchPromptMode %s %s" % (keyinfo, keytuple))
        history = self._history

        if keyinfo.keyname == "backspace":
            self.non_inc_query = self.non_inc_query[:-1]
        elif keyinfo.keyname in ["return", "escape"]:
            if self.non_inc_query:
                if self.non_inc_direction == -1:
                    res = history.reverse_search_history(self.non_inc_query)
                else:
                    res = history.forward_search_history(self.non_inc_query)

            self._bell()
            self.prompt = self.non_inc_oldprompt
            self.process_keyevent_queue = self.process_keyevent_queue[:-1]
            self._history.history_cursor = len(self._history.history)
            if keyinfo.keyname == "escape":
                self.l_buffer = self.non_inc_oldline
            else:
                self.l_buffer.set_line(res)
            return False
        elif keyinfo.keyname:
            pass
        elif keyinfo.control == False and keyinfo.meta == False:
            self.non_inc_query += keyinfo.char
        else:
            pass
        self.prompt = self.non_inc_oldprompt + ":" + self.non_inc_query

    def _init_non_i_search(self, direction):
        self.non_inc_direction = direction
        self.non_inc_query = ""
        self.non_inc_oldprompt = self.prompt
        self.non_inc_oldline = self.l_buffer.copy()
        self.l_buffer.reset_line()
        self.prompt = self.non_inc_oldprompt + ":"
        queue = self.process_keyevent_queue
        queue.append(self._process_non_incremental_search_keyevent)

    def non_incremental_reverse_search_history(self, e):  # (M-p)
        """Search backward starting at the current line and moving up
        through the history as necessary using a non-incremental search for
        a string supplied by the user."""
        return self._init_non_i_search(-1)

    def non_incremental_forward_search_history(self, e):  # (M-n)
        """Search forward starting at the current line and moving down
        through the the history as necessary using a non-incremental search
        for a string supplied by the user."""
        return self._init_non_i_search(1)


class LeaveModeTryNext(Exception):
    pass


class DigitArgumentMode(object):
    def __init__(self, rlobj):
        pass

    def _process_digit_argument_keyevent(self, keyinfo):
        log("DigitArgumentMode.keyinfo %s" % keyinfo)
        keytuple = keyinfo.tuple()
        log("DigitArgumentMode.keytuple %s %s" % (keyinfo, keytuple))
        if keyinfo.keyname in ["return"]:
            self.prompt = self._digit_argument_oldprompt
            self.process_keyevent_queue = self.process_keyevent_queue[:-1]
            return True
        elif keyinfo.keyname:
            pass
        elif (
            keyinfo.char in "0123456789"
            and keyinfo.control == False
            and keyinfo.meta == False
        ):
            log("arg %s %s" % (self.argument, keyinfo.char))
            self.argument = self.argument * 10 + int(keyinfo.char)
        else:
            self.prompt = self._digit_argument_oldprompt
            raise LeaveModeTryNext
        self.prompt = "(arg: %s) " % self.argument

    def _init_digit_argument(self, keyinfo):
        """Initialize search prompt"""
        c = self.console
        line = self.l_buffer.get_line_text()
        self._digit_argument_oldprompt = self.prompt
        queue = self.process_keyevent_queue
        queue = self.process_keyevent_queue
        queue.append(self._process_digit_argument_keyevent)

        if keyinfo.char == "-":
            self.argument = -1
        elif keyinfo.char in "0123456789":
            self.argument = int(keyinfo.char)
        log("<%s> %s" % (self.argument, type(self.argument)))
        self.prompt = "(arg: %s) " % self.argument
        log("arg-init %s %s" % (self.argument, keyinfo.char))


class EmacsMode(
    DigitArgumentMode, IncrementalSearchPromptMode, SearchPromptMode, basemode.BaseMode
):
    mode = "emacs"

    def __init__(self, rlobj):
        basemode.BaseMode.__init__(self, rlobj)
        IncrementalSearchPromptMode.__init__(self, rlobj)
        SearchPromptMode.__init__(self, rlobj)
        DigitArgumentMode.__init__(self, rlobj)
        self._keylog = lambda x, y: None
        self.previous_func = None
        self.prompt = ">>> "
        self._insert_verbatim = False
        self.next_meta = False  # True to force meta on next character

        self.process_keyevent_queue = [self._process_keyevent]

    def __repr__(self):
        return "<EmacsMode>"

    def add_key_logger(self, logfun):
        """logfun should be function that takes disp_fun and line_""" """buffer object """
        self._keylog = logfun

    def process_keyevent(self, keyinfo):
        try:
            r = self.process_keyevent_queue[-1](keyinfo)
        except LeaveModeTryNext:
            self.process_keyevent_queue = self.process_keyevent_queue[:-1]
            r = self.process_keyevent(keyinfo)
        if r:
            self.add_history(self.l_buffer.copy())
            return True
        return False

    def _process_keyevent(self, keyinfo):
        """return True when line is final"""
        # Process exit keys. Only exit on empty line
        log("_process_keyevent <%s>" % keyinfo)

        def nop(e):
            pass

        if self.next_meta:
            self.next_meta = False
            keyinfo.meta = True
        keytuple = keyinfo.tuple()

        if self._insert_verbatim:
            self.insert_text(keyinfo)
            self._insert_verbatim = False
            self.argument = 0
            return False

        if keytuple in self.exit_dispatch:
            pars = (self.l_buffer, lineobj.EndOfLine(self.l_buffer))
            log("exit_dispatch:<%s, %s>" % pars)
            if lineobj.EndOfLine(self.l_buffer) == 0:
                raise EOFError
        if keyinfo.keyname or keyinfo.control or keyinfo.meta:
            default = nop
        else:
            default = self.self_insert
        dispatch_func = self.key_dispatch.get(keytuple, default)

        log("readline from keyboard:<%s,%s>" % (keytuple, dispatch_func))

        r = None
        if dispatch_func:
            r = dispatch_func(keyinfo)
            self._keylog(dispatch_func, self.l_buffer)
            self.l_buffer.push_undo()

        self.previous_func = dispatch_func
        return r

    # History commands
    def previous_history(self, e):  # (C-p)
        """Move back through the history list, fetching the previous
        command."""
        self._history.previous_history(self.l_buffer)
        self.l_buffer.point = lineobj.EndOfLine
        self.finalize()

    def next_history(self, e):  # (C-n)
        """Move forward through the history list, fetching the next
        command."""
        self._history.next_history(self.l_buffer)
        self.finalize()

    def beginning_of_history(self, e):  # (M-<)
        """Move to the first line in the history."""
        self._history.beginning_of_history()
        self.finalize()

    def end_of_history(self, e):  # (M->)
        """Move to the end of the input history, i.e., the line currently
        being entered."""
        self._history.end_of_history(self.l_buffer)
        self.finalize()

    def reverse_search_history(self, e):  # (C-r)
        """Search backward starting at the current line and moving up
        through the history as necessary. This is an incremental search."""
        log("rev_search_history")
        self._init_incremental_search(self._history.reverse_search_history, e)
        self.finalize()

    def forward_search_history(self, e):  # (C-s)
        """Search forward starting at the current line and moving down
        through the the history as necessary. This is an incremental
        search."""
        log("fwd_search_history")
        self._init_incremental_search(self._history.forward_search_history, e)
        self.finalize()

    def history_search_forward(self, e):  # ()
        """Search forward through the history for the string of characters
        between the start of the current line and the point. This is a
        non-incremental search. By default, this command is unbound."""
        if self.previous_func and hasattr(self._history, self.previous_func.__name__):
            self._history.lastcommand = getattr(
                self._history, self.previous_func.__name__
            )
        else:
            self._history.lastcommand = None
        q = self._history.history_search_forward(self.l_buffer)
        self.l_buffer = q
        self.l_buffer.point = q.point
        self.finalize()

    def history_search_backward(self, e):  # ()
        """Search backward through the history for the string of characters
        between the start of the current line and the point. This is a
        non-incremental search. By default, this command is unbound."""
        if self.previous_func and hasattr(self._history, self.previous_func.__name__):
            self._history.lastcommand = getattr(
                self._history, self.previous_func.__name__
            )
        else:
            self._history.lastcommand = None
        q = self._history.history_search_backward(self.l_buffer)
        self.l_buffer = q
        self.l_buffer.point = q.point
        self.finalize()

    def yank_nth_arg(self, e):  # (M-C-y)
        """Insert the first argument to the previous command (usually the
        second word on the previous line) at point. With an argument n,
        insert the nth word from the previous command (the words in the
        previous command begin with word 0). A negative argument inserts the
        nth word from the end of the previous command."""
        self.finalize()

    def yank_last_arg(self, e):  # (M-. or M-_)
        """Insert last argument to the previous command (the last word of
        the previous history entry). With an argument, behave exactly like
        yank-nth-arg. Successive calls to yank-last-arg move back through
        the history list, inserting the last argument of each line in turn."""
        self.finalize()

    def forward_backward_delete_char(self, e):  # ()
        """Delete the character under the cursor, unless the cursor is at
        the end of the line, in which case the character behind the cursor
        is deleted. By default, this is not bound to a key."""
        self.finalize()

    def quoted_insert(self, e):  # (C-q or C-v)
        """Add the next character typed to the line verbatim. This is how to
        insert key sequences like C-q, for example."""
        self._insert_verbatim = True
        self.finalize()

    def tab_insert(self, e):  # (M-TAB)
        """Insert a tab character."""
        cursor = min(self.l_buffer.point, len(self.l_buffer.line_buffer))
        ws = " " * (self.tabstop - (cursor % self.tabstop))
        self.insert_text(ws)
        self.finalize()

    def transpose_chars(self, e):  # (C-t)
        """Drag the character before the cursor forward over the character
        at the cursor, moving the cursor forward as well. If the insertion
        point is at the end of the line, then this transposes the last two
        characters of the line. Negative arguments have no effect."""
        self.l_buffer.transpose_chars()
        self.finalize()

    def transpose_words(self, e):  # (M-t)
        """Drag the word before point past the word after point, moving
        point past that word as well. If the insertion point is at the end
        of the line, this transposes the last two words on the line."""
        self.l_buffer.transpose_words()
        self.finalize()

    def overwrite_mode(self, e):  # ()
        """Toggle overwrite mode. With an explicit positive numeric
        argument, switches to overwrite mode. With an explicit non-positive
        numeric argument, switches to insert mode. This command affects only
        emacs mode; vi mode does overwrite differently. Each call to
        readline() starts in insert mode. In overwrite mode, characters
        bound to self-insert replace the text at point rather than pushing
        the text to the right. Characters bound to backward-delete-char
        replace the character before point with a space."""
        self.finalize()

    def kill_line(self, e):  # (C-k)
        """Kill the text from point to the end of the line."""
        self.l_buffer.kill_line()
        self.finalize()

    def backward_kill_line(self, e):  # (C-x Rubout)
        """Kill backward to the beginning of the line."""
        self.l_buffer.backward_kill_line()
        self.finalize()

    def unix_line_discard(self, e):  # (C-u)
        """Kill backward from the cursor to the beginning of the current
        line."""
        # how is this different from backward_kill_line?
        self.l_buffer.unix_line_discard()
        self.finalize()

    def kill_whole_line(self, e):  # ()
        """Kill all characters on the current line, no matter where point
        is. By default, this is unbound."""
        self.l_buffer.kill_whole_line()
        self.finalize()

    def kill_word(self, e):  # (M-d)
        """Kill from point to the end of the current word, or if between
        words, to the end of the next word. Word boundaries are the same as
        forward-word."""
        self.l_buffer.kill_word()
        self.finalize()

    forward_kill_word = kill_word

    def backward_kill_word(self, e):  # (M-DEL)
        """Kill the word behind point. Word boundaries are the same as
        backward-word."""
        self.l_buffer.backward_kill_word()
        self.finalize()

    def unix_word_rubout(self, e):  # (C-w)
        """Kill the word behind point, using white space as a word
        boundary. The killed text is saved on the kill-ring."""
        self.l_buffer.unix_word_rubout()
        self.finalize()

    def kill_region(self, e):  # ()
        """Kill the text in the current region. By default, this command is
        unbound."""
        self.finalize()

    def copy_region_as_kill(self, e):  # ()
        """Copy the text in the region to the kill buffer, so it can be
        yanked right away. By default, this command is unbound."""
        self.finalize()

    def copy_backward_word(self, e):  # ()
        """Copy the word before point to the kill buffer. The word
        boundaries are the same as backward-word. By default, this command
        is unbound."""
        self.finalize()

    def copy_forward_word(self, e):  # ()
        """Copy the word following point to the kill buffer. The word
        boundaries are the same as forward-word. By default, this command is
        unbound."""
        self.finalize()

    def yank(self, e):  # (C-y)
        """Yank the top of the kill ring into the buffer at point."""
        self.l_buffer.yank()
        self.finalize()

    def yank_pop(self, e):  # (M-y)
        """Rotate the kill-ring, and yank the new top. You can only do this
        if the prior command is yank or yank-pop."""
        self.l_buffer.yank_pop()
        self.finalize()

    def delete_char_or_list(self, e):  # ()
        """Deletes the character under the cursor if not at the beginning or
        end of the line (like delete-char). If at the end of the line,
        behaves identically to possible-completions. This command is unbound
        by default."""
        self.finalize()

    def start_kbd_macro(self, e):  # (C-x ()
        """Begin saving the characters typed into the current keyboard
        macro."""
        self.finalize()

    def end_kbd_macro(self, e):  # (C-x ))
        """Stop saving the characters typed into the current keyboard macro
        and save the definition."""
        self.finalize()

    def call_last_kbd_macro(self, e):  # (C-x e)
        """Re-execute the last keyboard macro defined, by making the
        characters in the macro appear as if typed at the keyboard."""
        self.finalize()

    def re_read_init_file(self, e):  # (C-x C-r)
        """Read in the contents of the inputrc file, and incorporate any
        bindings or variable assignments found there."""
        self.finalize()

    def abort(self, e):  # (C-g)
        """Abort the current editing command and ring the terminals bell
        (subject to the setting of bell-style)."""
        self._bell()
        self.finalize()

    def do_uppercase_version(self, e):  # (M-a, M-b, M-x, ...)
        """If the metafied character x is lowercase, run the command that is
        bound to the corresponding uppercase character."""
        self.finalize()

    def prefix_meta(self, e):  # (ESC)
        """Metafy the next character typed. This is for keyboards without a
        meta key. Typing ESC f is equivalent to typing M-f."""
        self.next_meta = True
        self.finalize()

    def undo(self, e):  # (C-_ or C-x C-u)
        """Incremental undo, separately remembered for each line."""
        self.l_buffer.pop_undo()
        self.finalize()

    def revert_line(self, e):  # (M-r)
        """Undo all changes made to this line. This is like executing the
        undo command enough times to get back to the beginning."""
        self.finalize()

    def tilde_expand(self, e):  # (M-~)
        """Perform tilde expansion on the current word."""
        self.finalize()

    def set_mark(self, e):  # (C-@)
        """Set the mark to the point. If a numeric argument is supplied, the
        mark is set to that position."""
        self.l_buffer.set_mark()
        self.finalize()

    def exchange_point_and_mark(self, e):  # (C-x C-x)
        """Swap the point with the mark. The current cursor position is set
        to the saved position, and the old cursor position is saved as the
        mark."""
        self.finalize()

    def character_search(self, e):  # (C-])
        """A character is read and point is moved to the next occurrence of
        that character. A negative count searches for previous occurrences."""
        self.finalize()

    def character_search_backward(self, e):  # (M-C-])
        """A character is read and point is moved to the previous occurrence
        of that character. A negative count searches for subsequent
        occurrences."""
        self.finalize()

    def insert_comment(self, e):  # (M-#)
        """Without a numeric argument, the value of the comment-begin
        variable is inserted at the beginning of the current line. If a
        numeric argument is supplied, this command acts as a toggle: if the
        characters at the beginning of the line do not match the value of
        comment-begin, the value is inserted, otherwise the characters in
        comment-begin are deleted from the beginning of the line. In either
        case, the line is accepted as if a newline had been typed."""
        self.finalize()

    def dump_variables(self, e):  # ()
        """Print all of the settable variables and their values to the
        Readline output stream. If a numeric argument is supplied, the
        output is formatted in such a way that it can be made part of an
        inputrc file. This command is unbound by default."""
        self.finalize()

    def dump_macros(self, e):  # ()
        """Print all of the Readline key sequences bound to macros and the
        strings they output. If a numeric argument is supplied, the output
        is formatted in such a way that it can be made part of an inputrc
        file. This command is unbound by default."""
        self.finalize()

    def digit_argument(self, e):  # (M-0, M-1, ... M--)
        """Add this digit to the argument already accumulating, or start a
        new argument. M-- starts a negative argument."""
        self._init_digit_argument(e)
        # Should not finalize

    def universal_argument(self, e):  # ()
        """This is another way to specify an argument. If this command is
        followed by one or more digits, optionally with a leading minus
        sign, those digits define the argument. If the command is followed
        by digits, executing universal-argument again ends the numeric
        argument, but is otherwise ignored. As a special case, if this
        command is immediately followed by a character that is neither a
        digit or minus sign, the argument count for the next command is
        multiplied by four. The argument count is initially one, so
        executing this function the first time makes the argument count
        four, a second time makes the argument count sixteen, and so on. By
        default, this is not bound to a key."""
        # Should not finalize

    # Create key bindings:
    def init_editing_mode(self, e):  # (C-e)
        """When in vi command mode, this causes a switch to emacs editing
        mode."""
        self._bind_exit_key("Control-d")
        self._bind_exit_key("Control-z")

        # I often accidentally hold the shift or control while typing space
        self._bind_key("space", self.self_insert)
        self._bind_key("Shift-space", self.self_insert)
        self._bind_key("Control-space", self.self_insert)
        self._bind_key("Return", self.accept_line)
        self._bind_key("Left", self.backward_char)
        self._bind_key("Control-b", self.backward_char)
        self._bind_key("Right", self.forward_char)
        self._bind_key("Control-f", self.forward_char)
        self._bind_key("Control-h", self.backward_delete_char)
        self._bind_key("BackSpace", self.backward_delete_char)
        self._bind_key("Control-BackSpace", self.backward_delete_word)

        self._bind_key("Home", self.beginning_of_line)
        self._bind_key("End", self.end_of_line)
        self._bind_key("Delete", self.delete_char)
        self._bind_key("Control-d", self.delete_char)
        self._bind_key("Clear", self.clear_screen)
        self._bind_key("Alt-f", self.forward_word)
        self._bind_key("Alt-b", self.backward_word)
        self._bind_key("Control-l", self.clear_screen)
        self._bind_key("Control-p", self.previous_history)
        self._bind_key("Up", self.history_search_backward)
        self._bind_key("Control-n", self.next_history)
        self._bind_key("Down", self.history_search_forward)
        self._bind_key("Control-a", self.beginning_of_line)
        self._bind_key("Control-e", self.end_of_line)
        self._bind_key("Alt-<", self.beginning_of_history)
        self._bind_key("Alt->", self.end_of_history)
        self._bind_key("Control-r", self.reverse_search_history)
        self._bind_key("Control-s", self.forward_search_history)
        self._bind_key("Control-Shift-r", self.forward_search_history)
        self._bind_key("Alt-p", self.non_incremental_reverse_search_history)
        self._bind_key("Alt-n", self.non_incremental_forward_search_history)
        self._bind_key("Control-z", self.undo)
        self._bind_key("Control-_", self.undo)
        self._bind_key("Escape", self.kill_whole_line)
        self._bind_key("Meta-d", self.kill_word)
        self._bind_key("Control-Delete", self.forward_delete_word)
        self._bind_key("Control-w", self.unix_word_rubout)
        # self._bind_key('Control-Shift-v',   self.quoted_insert)
        self._bind_key("Control-v", self.paste)
        self._bind_key("Alt-v", self.ipython_paste)
        self._bind_key("Control-y", self.yank)
        self._bind_key("Control-k", self.kill_line)
        self._bind_key("Control-m", self.set_mark)
        self._bind_key("Control-q", self.copy_region_to_clipboard)
        #        self._bind_key('Control-shift-k',  self.kill_whole_line)
        self._bind_key("Control-Shift-v", self.paste_mulitline_code)
        self._bind_key("Control-Right", self.forward_word_end)
        self._bind_key("Control-Left", self.backward_word)
        self._bind_key("Shift-Right", self.forward_char_extend_selection)
        self._bind_key("Shift-Left", self.backward_char_extend_selection)
        self._bind_key("Shift-Control-Right", self.forward_word_end_extend_selection)
        self._bind_key("Shift-Control-Left", self.backward_word_extend_selection)
        self._bind_key("Shift-Home", self.beginning_of_line_extend_selection)
        self._bind_key("Shift-End", self.end_of_line_extend_selection)
        self._bind_key("numpad0", self.self_insert)
        self._bind_key("numpad1", self.self_insert)
        self._bind_key("numpad2", self.self_insert)
        self._bind_key("numpad3", self.self_insert)
        self._bind_key("numpad4", self.self_insert)
        self._bind_key("numpad5", self.self_insert)
        self._bind_key("numpad6", self.self_insert)
        self._bind_key("numpad7", self.self_insert)
        self._bind_key("numpad8", self.self_insert)
        self._bind_key("numpad9", self.self_insert)
        self._bind_key("add", self.self_insert)
        self._bind_key("subtract", self.self_insert)
        self._bind_key("multiply", self.self_insert)
        self._bind_key("divide", self.self_insert)
        self._bind_key("vk_decimal", self.self_insert)
        log("RUNNING INIT EMACS")
        for i in range(0, 10):
            self._bind_key("alt-%d" % i, self.digit_argument)
        self._bind_key("alt--", self.digit_argument)


# make it case insensitive
def commonprefix(m):
    "Given a list of pathnames, returns the longest common leading component"
    if not m:
        return ""
    prefix = m[0]
    for item in m:
        for i in range(len(prefix)):
            if prefix[: i + 1].lower() != item[: i + 1].lower():
                prefix = prefix[:i]
                if i == 0:
                    return ""
                break
    return prefix

# === NexusCore/openenv\Lib\site-packages\joblib\_memmapping_reducer.py ===
"""
Reducer using memory mapping for numpy arrays
"""
# Author: Thomas Moreau <thomas.moreau.2010@gmail.com>
# Copyright: 2017, Thomas Moreau
# License: BSD 3 clause

import atexit
import errno
import os
import stat
import tempfile
import threading
import time
import warnings
import weakref
from mmap import mmap
from multiprocessing import util
from pickle import HIGHEST_PROTOCOL, PicklingError, dumps, loads, whichmodule
from uuid import uuid4

try:
    WindowsError
except NameError:
    WindowsError = type(None)

try:
    import numpy as np
    from numpy.lib.stride_tricks import as_strided
except ImportError:
    np = None

from .backports import make_memmap
from .disk import delete_folder
from .externals.loky.backend import resource_tracker
from .numpy_pickle import dump, load, load_temporary_memmap

# Some system have a ramdisk mounted by default, we can use it instead of /tmp
# as the default folder to dump big arrays to share with subprocesses.
SYSTEM_SHARED_MEM_FS = "/dev/shm"

# Minimal number of bytes available on SYSTEM_SHARED_MEM_FS to consider using
# it as the default folder to dump big arrays to share with subprocesses.
SYSTEM_SHARED_MEM_FS_MIN_SIZE = int(2e9)

# Folder and file permissions to chmod temporary files generated by the
# memmapping pool. Only the owner of the Python process can access the
# temporary files and folder.
FOLDER_PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
FILE_PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR

# Set used in joblib workers, referencing the filenames of temporary memmaps
# created by joblib to speed up data communication. In child processes, we add
# a finalizer to these memmaps that sends a maybe_unlink call to the
# resource_tracker, in order to free main memory as fast as possible.
JOBLIB_MMAPS = set()


def _log_and_unlink(filename):
    from .externals.loky.backend.resource_tracker import _resource_tracker

    util.debug(
        "[FINALIZER CALL] object mapping to {} about to be deleted,"
        " decrementing the refcount of the file (pid: {})".format(
            os.path.basename(filename), os.getpid()
        )
    )
    _resource_tracker.maybe_unlink(filename, "file")


def add_maybe_unlink_finalizer(memmap):
    util.debug(
        "[FINALIZER ADD] adding finalizer to {} (id {}, filename {}, pid  {})".format(
            type(memmap), id(memmap), os.path.basename(memmap.filename), os.getpid()
        )
    )
    weakref.finalize(memmap, _log_and_unlink, memmap.filename)


def unlink_file(filename):
    """Wrapper around os.unlink with a retry mechanism.

    The retry mechanism has been implemented primarily to overcome a race
    condition happening during the finalizer of a np.memmap: when a process
    holding the last reference to a mmap-backed np.memmap/np.array is about to
    delete this array (and close the reference), it sends a maybe_unlink
    request to the resource_tracker. This request can be processed faster than
    it takes for the last reference of the memmap to be closed, yielding (on
    Windows) a PermissionError in the resource_tracker loop.
    """
    NUM_RETRIES = 10
    for retry_no in range(1, NUM_RETRIES + 1):
        try:
            os.unlink(filename)
            break
        except PermissionError:
            util.debug(
                "[ResourceTracker] tried to unlink {}, got PermissionError".format(
                    filename
                )
            )
            if retry_no == NUM_RETRIES:
                raise
            else:
                time.sleep(0.2)
        except FileNotFoundError:
            # In case of a race condition when deleting the temporary folder,
            # avoid noisy FileNotFoundError exception in the resource tracker.
            pass


resource_tracker._CLEANUP_FUNCS["file"] = unlink_file


class _WeakArrayKeyMap:
    """A variant of weakref.WeakKeyDictionary for unhashable numpy arrays.

    This datastructure will be used with numpy arrays as obj keys, therefore we
    do not use the __get__ / __set__ methods to avoid any conflict with the
    numpy fancy indexing syntax.
    """

    def __init__(self):
        self._data = {}

    def get(self, obj):
        ref, val = self._data[id(obj)]
        if ref() is not obj:
            # In case of race condition with on_destroy: could never be
            # triggered by the joblib tests with CPython.
            raise KeyError(obj)
        return val

    def set(self, obj, value):
        key = id(obj)
        try:
            ref, _ = self._data[key]
            if ref() is not obj:
                # In case of race condition with on_destroy: could never be
                # triggered by the joblib tests with CPython.
                raise KeyError(obj)
        except KeyError:
            # Insert the new entry in the mapping along with a weakref
            # callback to automatically delete the entry from the mapping
            # as soon as the object used as key is garbage collected.
            def on_destroy(_):
                del self._data[key]

            ref = weakref.ref(obj, on_destroy)
        self._data[key] = ref, value

    def __getstate__(self):
        raise PicklingError("_WeakArrayKeyMap is not pickleable")


###############################################################################
# Support for efficient transient pickling of numpy data structures


def _get_backing_memmap(a):
    """Recursively look up the original np.memmap instance base if any."""
    b = getattr(a, "base", None)
    if b is None:
        # TODO: check scipy sparse datastructure if scipy is installed
        # a nor its descendants do not have a memmap base
        return None

    elif isinstance(b, mmap):
        # a is already a real memmap instance.
        return a

    else:
        # Recursive exploration of the base ancestry
        return _get_backing_memmap(b)


def _get_temp_dir(pool_folder_name, temp_folder=None):
    """Get the full path to a subfolder inside the temporary folder.

    Parameters
    ----------
    pool_folder_name : str
        Sub-folder name used for the serialization of a pool instance.

    temp_folder: str, optional
        Folder to be used by the pool for memmapping large arrays
        for sharing memory with worker processes. If None, this will try in
        order:

        - a folder pointed by the JOBLIB_TEMP_FOLDER environment
          variable,
        - /dev/shm if the folder exists and is writable: this is a
          RAMdisk filesystem available by default on modern Linux
          distributions,
        - the default system temporary folder that can be
          overridden with TMP, TMPDIR or TEMP environment
          variables, typically /tmp under Unix operating systems.

    Returns
    -------
    pool_folder : str
       full path to the temporary folder
    use_shared_mem : bool
       whether the temporary folder is written to the system shared memory
       folder or some other temporary folder.
    """
    use_shared_mem = False
    if temp_folder is None:
        temp_folder = os.environ.get("JOBLIB_TEMP_FOLDER", None)
    if temp_folder is None:
        if os.path.exists(SYSTEM_SHARED_MEM_FS) and hasattr(os, "statvfs"):
            try:
                shm_stats = os.statvfs(SYSTEM_SHARED_MEM_FS)
                available_nbytes = shm_stats.f_bsize * shm_stats.f_bavail
                if available_nbytes > SYSTEM_SHARED_MEM_FS_MIN_SIZE:
                    # Try to see if we have write access to the shared mem
                    # folder only if it is reasonably large (that is 2GB or
                    # more).
                    temp_folder = SYSTEM_SHARED_MEM_FS
                    pool_folder = os.path.join(temp_folder, pool_folder_name)
                    if not os.path.exists(pool_folder):
                        os.makedirs(pool_folder)
                    use_shared_mem = True
            except (IOError, OSError):
                # Missing rights in the /dev/shm partition, fallback to regular
                # temp folder.
                temp_folder = None
    if temp_folder is None:
        # Fallback to the default tmp folder, typically /tmp
        temp_folder = tempfile.gettempdir()
    temp_folder = os.path.abspath(os.path.expanduser(temp_folder))
    pool_folder = os.path.join(temp_folder, pool_folder_name)
    return pool_folder, use_shared_mem


def has_shareable_memory(a):
    """Return True if a is backed by some mmap buffer directly or not."""
    return _get_backing_memmap(a) is not None


def _strided_from_memmap(
    filename,
    dtype,
    mode,
    offset,
    order,
    shape,
    strides,
    total_buffer_len,
    unlink_on_gc_collect,
):
    """Reconstruct an array view on a memory mapped file."""
    if mode == "w+":
        # Do not zero the original data when unpickling
        mode = "r+"

    if strides is None:
        # Simple, contiguous memmap
        return make_memmap(
            filename,
            dtype=dtype,
            shape=shape,
            mode=mode,
            offset=offset,
            order=order,
            unlink_on_gc_collect=unlink_on_gc_collect,
        )
    else:
        # For non-contiguous data, memmap the total enclosing buffer and then
        # extract the non-contiguous view with the stride-tricks API
        base = make_memmap(
            filename,
            dtype=dtype,
            shape=total_buffer_len,
            offset=offset,
            mode=mode,
            order=order,
            unlink_on_gc_collect=unlink_on_gc_collect,
        )
        return as_strided(base, shape=shape, strides=strides)


def _reduce_memmap_backed(a, m):
    """Pickling reduction for memmap backed arrays.

    a is expected to be an instance of np.ndarray (or np.memmap)
    m is expected to be an instance of np.memmap on the top of the ``base``
    attribute ancestry of a. ``m.base`` should be the real python mmap object.
    """
    # offset that comes from the striding differences between a and m
    util.debug(
        "[MEMMAP REDUCE] reducing a memmap-backed array (shape, {}, pid: {})".format(
            a.shape, os.getpid()
        )
    )
    try:
        from numpy.lib.array_utils import byte_bounds
    except (ModuleNotFoundError, ImportError):
        # Backward-compat for numpy < 2.0
        from numpy import byte_bounds
    a_start, a_end = byte_bounds(a)
    m_start = byte_bounds(m)[0]
    offset = a_start - m_start

    # offset from the backing memmap
    offset += m.offset

    # 1D arrays are both F and C contiguous, so only set the flag in
    # higher dimensions. See https://github.com/joblib/joblib/pull/1704.
    if m.ndim > 1 and m.flags["F_CONTIGUOUS"]:
        order = "F"
    else:
        # The backing memmap buffer is necessarily contiguous hence C if not
        # Fortran
        order = "C"

    if a.flags["F_CONTIGUOUS"] or a.flags["C_CONTIGUOUS"]:
        # If the array is a contiguous view, no need to pass the strides
        strides = None
        total_buffer_len = None
    else:
        # Compute the total number of items to map from which the strided
        # view will be extracted.
        strides = a.strides
        total_buffer_len = (a_end - a_start) // a.itemsize

    return (
        _strided_from_memmap,
        (
            m.filename,
            a.dtype,
            m.mode,
            offset,
            order,
            a.shape,
            strides,
            total_buffer_len,
            False,
        ),
    )


def reduce_array_memmap_backward(a):
    """reduce a np.array or a np.memmap from a child process"""
    m = _get_backing_memmap(a)
    if isinstance(m, np.memmap) and m.filename not in JOBLIB_MMAPS:
        # if a is backed by a memmaped file, reconstruct a using the
        # memmaped file.
        return _reduce_memmap_backed(a, m)
    else:
        # a is either a regular (not memmap-backed) numpy array, or an array
        # backed by a shared temporary file created by joblib. In the latter
        # case, in order to limit the lifespan of these temporary files, we
        # serialize the memmap as a regular numpy array, and decref the
        # file backing the memmap (done implicitly in a previously registered
        # finalizer, see ``unlink_on_gc_collect`` for more details)
        return (loads, (dumps(np.asarray(a), protocol=HIGHEST_PROTOCOL),))


class ArrayMemmapForwardReducer(object):
    """Reducer callable to dump large arrays to memmap files.

    Parameters
    ----------
    max_nbytes: int
        Threshold to trigger memmapping of large arrays to files created
        a folder.
    temp_folder_resolver: callable
        An callable in charge of resolving a temporary folder name where files
        for backing memmapped arrays are created.
    mmap_mode: 'r', 'r+' or 'c'
        Mode for the created memmap datastructure. See the documentation of
        numpy.memmap for more details. Note: 'w+' is coerced to 'r+'
        automatically to avoid zeroing the data on unpickling.
    verbose: int, optional, 0 by default
        If verbose > 0, memmap creations are logged.
        If verbose > 1, both memmap creations, reuse and array pickling are
        logged.
    prewarm: bool, optional, False by default.
        Force a read on newly memmapped array to make sure that OS pre-cache it
        memory. This can be useful to avoid concurrent disk access when the
        same data array is passed to different worker processes.
    """

    def __init__(
        self,
        max_nbytes,
        temp_folder_resolver,
        mmap_mode,
        unlink_on_gc_collect,
        verbose=0,
        prewarm=True,
    ):
        self._max_nbytes = max_nbytes
        self._temp_folder_resolver = temp_folder_resolver
        self._mmap_mode = mmap_mode
        self.verbose = int(verbose)
        if prewarm == "auto":
            self._prewarm = not self._temp_folder.startswith(SYSTEM_SHARED_MEM_FS)
        else:
            self._prewarm = prewarm
        self._prewarm = prewarm
        self._memmaped_arrays = _WeakArrayKeyMap()
        self._temporary_memmaped_filenames = set()
        self._unlink_on_gc_collect = unlink_on_gc_collect

    @property
    def _temp_folder(self):
        return self._temp_folder_resolver()

    def __reduce__(self):
        # The ArrayMemmapForwardReducer is passed to the children processes: it
        # needs to be pickled but the _WeakArrayKeyMap need to be skipped as
        # it's only guaranteed to be consistent with the parent process memory
        # garbage collection.
        # Although this reducer is pickled, it is not needed in its destination
        # process (child processes), as we only use this reducer to send
        # memmaps from the parent process to the children processes. For this
        # reason, we can afford skipping the resolver, (which would otherwise
        # be unpicklable), and pass it as None instead.
        args = (self._max_nbytes, None, self._mmap_mode, self._unlink_on_gc_collect)
        kwargs = {
            "verbose": self.verbose,
            "prewarm": self._prewarm,
        }
        return ArrayMemmapForwardReducer, args, kwargs

    def __call__(self, a):
        m = _get_backing_memmap(a)
        if m is not None and isinstance(m, np.memmap):
            # a is already backed by a memmap file, let's reuse it directly
            return _reduce_memmap_backed(a, m)

        if (
            not a.dtype.hasobject
            and self._max_nbytes is not None
            and a.nbytes > self._max_nbytes
        ):
            # check that the folder exists (lazily create the pool temp folder
            # if required)
            try:
                os.makedirs(self._temp_folder)
                os.chmod(self._temp_folder, FOLDER_PERMISSIONS)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise e

            try:
                basename = self._memmaped_arrays.get(a)
            except KeyError:
                # Generate a new unique random filename. The process and thread
                # ids are only useful for debugging purpose and to make it
                # easier to cleanup orphaned files in case of hard process
                # kill (e.g. by "kill -9" or segfault).
                basename = "{}-{}-{}.pkl".format(
                    os.getpid(), id(threading.current_thread()), uuid4().hex
                )
                self._memmaped_arrays.set(a, basename)
            filename = os.path.join(self._temp_folder, basename)

            # In case the same array with the same content is passed several
            # times to the pool subprocess children, serialize it only once

            is_new_memmap = filename not in self._temporary_memmaped_filenames

            # add the memmap to the list of temporary memmaps created by joblib
            self._temporary_memmaped_filenames.add(filename)

            if self._unlink_on_gc_collect:
                # Bump reference count of the memmap by 1 to account for
                # shared usage of the memmap by a child process. The
                # corresponding decref call will be executed upon calling
                # resource_tracker.maybe_unlink, registered as a finalizer in
                # the child.
                # the incref/decref calls here are only possible when the child
                # and the parent share the same resource_tracker. It is not the
                # case for the multiprocessing backend, but it does not matter
                # because unlinking a memmap from a child process is only
                # useful to control the memory usage of long-lasting child
                # processes, while the multiprocessing-based pools terminate
                # their workers at the end of a map() call.
                resource_tracker.register(filename, "file")

            if is_new_memmap:
                # Incref each temporary memmap created by joblib one extra
                # time.  This means that these memmaps will only be deleted
                # once an extra maybe_unlink() is called, which is done once
                # all the jobs have completed (or been canceled) in the
                # Parallel._terminate_backend() method.
                resource_tracker.register(filename, "file")

            if not os.path.exists(filename):
                util.debug(
                    "[ARRAY DUMP] Pickling new array (shape={}, dtype={}) "
                    "creating a new memmap at {}".format(a.shape, a.dtype, filename)
                )
                for dumped_filename in dump(a, filename):
                    os.chmod(dumped_filename, FILE_PERMISSIONS)

                if self._prewarm:
                    # Warm up the data by accessing it. This operation ensures
                    # that the disk access required to create the memmapping
                    # file are performed in the reducing process and avoids
                    # concurrent memmap creation in multiple children
                    # processes.
                    load(filename, mmap_mode=self._mmap_mode).max()

            else:
                util.debug(
                    "[ARRAY DUMP] Pickling known array (shape={}, dtype={}) "
                    "reusing memmap file: {}".format(
                        a.shape, a.dtype, os.path.basename(filename)
                    )
                )

            # The worker process will use joblib.load to memmap the data
            return (
                load_temporary_memmap,
                (filename, self._mmap_mode, self._unlink_on_gc_collect),
            )
        else:
            # do not convert a into memmap, let pickler do its usual copy with
            # the default system pickler
            util.debug(
                "[ARRAY DUMP] Pickling array (NO MEMMAPPING) (shape={}, "
                " dtype={}).".format(a.shape, a.dtype)
            )
            return (loads, (dumps(a, protocol=HIGHEST_PROTOCOL),))


def get_memmapping_reducers(
    forward_reducers=None,
    backward_reducers=None,
    temp_folder_resolver=None,
    max_nbytes=1e6,
    mmap_mode="r",
    verbose=0,
    prewarm=False,
    unlink_on_gc_collect=True,
    **kwargs,
):
    """Construct a pair of memmapping reducer linked to a tmpdir.

    This function manage the creation and the clean up of the temporary folders
    underlying the memory maps and should be use to get the reducers necessary
    to construct joblib pool or executor.
    """
    if forward_reducers is None:
        forward_reducers = dict()
    if backward_reducers is None:
        backward_reducers = dict()

    if np is not None:
        # Register smart numpy.ndarray reducers that detects memmap backed
        # arrays and that is also able to dump to memmap large in-memory
        # arrays over the max_nbytes threshold
        forward_reduce_ndarray = ArrayMemmapForwardReducer(
            max_nbytes,
            temp_folder_resolver,
            mmap_mode,
            unlink_on_gc_collect,
            verbose,
            prewarm=prewarm,
        )
        forward_reducers[np.ndarray] = forward_reduce_ndarray
        forward_reducers[np.memmap] = forward_reduce_ndarray

        # Communication from child process to the parent process always
        # pickles in-memory numpy.ndarray without dumping them as memmap
        # to avoid confusing the caller and make it tricky to collect the
        # temporary folder
        backward_reducers[np.ndarray] = reduce_array_memmap_backward
        backward_reducers[np.memmap] = reduce_array_memmap_backward

    return forward_reducers, backward_reducers


class TemporaryResourcesManager(object):
    """Stateful object able to manage temporary folder and pickles

    It exposes:
    - a per-context folder name resolving API that memmap-based reducers will
      rely on to know where to pickle the temporary memmaps
    - a temporary file/folder management API that internally uses the
      resource_tracker.
    """

    def __init__(self, temp_folder_root=None, context_id=None):
        self._current_temp_folder = None
        self._temp_folder_root = temp_folder_root
        self._use_shared_mem = None
        self._cached_temp_folders = dict()
        self._id = uuid4().hex
        self._finalizers = {}
        if context_id is None:
            # It would be safer to not assign a default context id (less silent
            # bugs), but doing this while maintaining backward compatibility
            # with the previous, context-unaware version get_memmaping_executor
            # exposes too many low-level details.
            context_id = uuid4().hex
        self.set_current_context(context_id)

    def set_current_context(self, context_id):
        self._current_context_id = context_id
        self.register_new_context(context_id)

    def register_new_context(self, context_id):
        # Prepare a sub-folder name specific to a context (usually a unique id
        # generated by each instance of the Parallel class). Do not create in
        # advance to spare FS write access if no array is to be dumped).
        if context_id in self._cached_temp_folders:
            return
        else:
            # During its lifecycle, one Parallel object can have several
            # executors associated to it (for instance, if a loky worker raises
            # an exception, joblib shutdowns the executor and instantly
            # recreates a new one before raising the error - see
            # ``ensure_ready``.  Because we don't want two executors tied to
            # the same Parallel object (and thus the same context id) to
            # register/use/delete the same folder, we also add an id specific
            # to the current Manager (and thus specific to its associated
            # executor) to the folder name.
            new_folder_name = "joblib_memmapping_folder_{}_{}_{}".format(
                os.getpid(), self._id, context_id
            )
            new_folder_path, _ = _get_temp_dir(new_folder_name, self._temp_folder_root)
            self.register_folder_finalizer(new_folder_path, context_id)
            self._cached_temp_folders[context_id] = new_folder_path

    def resolve_temp_folder_name(self):
        """Return a folder name specific to the currently activated context"""
        return self._cached_temp_folders[self._current_context_id]

    # resource management API

    def register_folder_finalizer(self, pool_subfolder, context_id):
        # Register the garbage collector at program exit in case caller forgets
        # to call terminate explicitly: note we do not pass any reference to
        # ensure that this callback won't prevent garbage collection of
        # parallel instance and related file handler resources such as POSIX
        # semaphores and pipes
        pool_module_name = whichmodule(delete_folder, "delete_folder")
        resource_tracker.register(pool_subfolder, "folder")

        def _cleanup():
            # In some cases the Python runtime seems to set delete_folder to
            # None just before exiting when accessing the delete_folder
            # function from the closure namespace. So instead we reimport
            # the delete_folder function explicitly.
            # https://github.com/joblib/joblib/issues/328
            # We cannot just use from 'joblib.pool import delete_folder'
            # because joblib should only use relative imports to allow
            # easy vendoring.
            delete_folder = __import__(
                pool_module_name, fromlist=["delete_folder"]
            ).delete_folder
            try:
                delete_folder(pool_subfolder, allow_non_empty=True)
                resource_tracker.unregister(pool_subfolder, "folder")
            except OSError:
                warnings.warn(
                    "Failed to delete temporary folder: {}".format(pool_subfolder)
                )

        self._finalizers[context_id] = atexit.register(_cleanup)

    def _clean_temporary_resources(
        self, context_id=None, force=False, allow_non_empty=False
    ):
        """Clean temporary resources created by a process-based pool"""
        if context_id is None:
            # Iterates over a copy of the cache keys to avoid Error due to
            # iterating over a changing size dictionary.
            for context_id in list(self._cached_temp_folders):
                self._clean_temporary_resources(
                    context_id, force=force, allow_non_empty=allow_non_empty
                )
        else:
            temp_folder = self._cached_temp_folders.get(context_id)
            if temp_folder and os.path.exists(temp_folder):
                for filename in os.listdir(temp_folder):
                    if force:
                        # Some workers have failed and the ref counted might
                        # be off. The workers should have shut down by this
                        # time so forcefully clean up the files.
                        resource_tracker.unregister(
                            os.path.join(temp_folder, filename), "file"
                        )
                    else:
                        resource_tracker.maybe_unlink(
                            os.path.join(temp_folder, filename), "file"
                        )

                # When forcing clean-up, try to delete the folder even if some
                # files are still in it. Otherwise, try to delete the folder
                allow_non_empty |= force

                # Clean up the folder if possible, either if it is empty or
                # if none of the files in it are in used and allow_non_empty.
                try:
                    delete_folder(temp_folder, allow_non_empty=allow_non_empty)
                    # Forget the folder once it has been deleted
                    self._cached_temp_folders.pop(context_id, None)
                    resource_tracker.unregister(temp_folder, "folder")

                    # Also cancel the finalizers  that gets triggered at gc.
                    finalizer = self._finalizers.pop(context_id, None)
                    if finalizer is not None:
                        atexit.unregister(finalizer)

                except OSError:
                    # Temporary folder cannot be deleted right now.
                    # This folder will be cleaned up by an atexit
                    # finalizer registered by the memmapping_reducer.
                    pass

# === NexusCore/openenv\Lib\site-packages\trio\_abc.py ===
from __future__ import annotations

import socket
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

import trio

if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import Self

    # both of these introduce circular imports if outside a TYPE_CHECKING guard
    from ._socket import SocketType
    from .lowlevel import Task


class Clock(ABC):
    """The interface for custom run loop clocks."""

    __slots__ = ()

    @abstractmethod
    def start_clock(self) -> None:
        """Do any setup this clock might need.

        Called at the beginning of the run.

        """

    @abstractmethod
    def current_time(self) -> float:
        """Return the current time, according to this clock.

        This is used to implement functions like :func:`trio.current_time` and
        :func:`trio.move_on_after`.

        Returns:
            float: The current time.

        """

    @abstractmethod
    def deadline_to_sleep_time(self, deadline: float) -> float:
        """Compute the real time until the given deadline.

        This is called before we enter a system-specific wait function like
        :func:`select.select`, to get the timeout to pass.

        For a clock using wall-time, this should be something like::

           return deadline - self.current_time()

        but of course it may be different if you're implementing some kind of
        virtual clock.

        Args:
            deadline (float): The absolute time of the next deadline,
                according to this clock.

        Returns:
            float: The number of real seconds to sleep until the given
            deadline. May be :data:`math.inf`.

        """


class Instrument(ABC):  # noqa: B024  # conceptually is ABC
    """The interface for run loop instrumentation.

    Instruments don't have to inherit from this abstract base class, and all
    of these methods are optional. This class serves mostly as documentation.

    """

    __slots__ = ()

    def before_run(self) -> None:
        """Called at the beginning of :func:`trio.run`."""
        return

    def after_run(self) -> None:
        """Called just before :func:`trio.run` returns."""
        return

    def task_spawned(self, task: Task) -> None:
        """Called when the given task is created.

        Args:
            task (trio.lowlevel.Task): The new task.

        """
        return

    def task_scheduled(self, task: Task) -> None:
        """Called when the given task becomes runnable.

        It may still be some time before it actually runs, if there are other
        runnable tasks ahead of it.

        Args:
            task (trio.lowlevel.Task): The task that became runnable.

        """
        return

    def before_task_step(self, task: Task) -> None:
        """Called immediately before we resume running the given task.

        Args:
            task (trio.lowlevel.Task): The task that is about to run.

        """
        return

    def after_task_step(self, task: Task) -> None:
        """Called when we return to the main run loop after a task has yielded.

        Args:
            task (trio.lowlevel.Task): The task that just ran.

        """
        return

    def task_exited(self, task: Task) -> None:
        """Called when the given task exits.

        Args:
            task (trio.lowlevel.Task): The finished task.

        """
        return

    def before_io_wait(self, timeout: float) -> None:
        """Called before blocking to wait for I/O readiness.

        Args:
            timeout (float): The number of seconds we are willing to wait.

        """
        return

    def after_io_wait(self, timeout: float) -> None:
        """Called after handling pending I/O.

        Args:
            timeout (float): The number of seconds we were willing to
                wait. This much time may or may not have elapsed, depending on
                whether any I/O was ready.

        """
        return


class HostnameResolver(ABC):
    """If you have a custom hostname resolver, then implementing
    :class:`HostnameResolver` allows you to register this to be used by Trio.

    See :func:`trio.socket.set_custom_hostname_resolver`.

    """

    __slots__ = ()

    @abstractmethod
    async def getaddrinfo(
        self,
        host: bytes | None,
        port: bytes | str | int | None,
        family: int = 0,
        type: int = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> list[
        tuple[
            socket.AddressFamily,
            socket.SocketKind,
            int,
            str,
            tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes],
        ]
    ]:
        """A custom implementation of :func:`~trio.socket.getaddrinfo`.

        Called by :func:`trio.socket.getaddrinfo`.

        If ``host`` is given as a numeric IP address, then
        :func:`~trio.socket.getaddrinfo` may handle the request itself rather
        than calling this method.

        Any required IDNA encoding is handled before calling this function;
        your implementation can assume that it will never see U-labels like
        ``"café.com"``, and only needs to handle A-labels like
        ``b"xn--caf-dma.com"``."""  # spellchecker:disable-line

    @abstractmethod
    async def getnameinfo(
        self,
        sockaddr: tuple[str, int] | tuple[str, int, int, int],
        flags: int,
    ) -> tuple[str, str]:
        """A custom implementation of :func:`~trio.socket.getnameinfo`.

        Called by :func:`trio.socket.getnameinfo`.

        """


class SocketFactory(ABC):
    """If you write a custom class implementing the Trio socket interface,
    then you can use a :class:`SocketFactory` to get Trio to use it.

    See :func:`trio.socket.set_custom_socket_factory`.

    """

    __slots__ = ()

    @abstractmethod
    def socket(
        self,
        family: socket.AddressFamily | int = socket.AF_INET,
        type: socket.SocketKind | int = socket.SOCK_STREAM,
        proto: int = 0,
    ) -> SocketType:
        """Create and return a socket object.

        Your socket object must inherit from :class:`trio.socket.SocketType`,
        which is an empty class whose only purpose is to "mark" which classes
        should be considered valid Trio sockets.

        Called by :func:`trio.socket.socket`.

        Note that unlike :func:`trio.socket.socket`, this does not take a
        ``fileno=`` argument. If a ``fileno=`` is specified, then
        :func:`trio.socket.socket` returns a regular Trio socket object
        instead of calling this method.

        """


class AsyncResource(ABC):
    """A standard interface for resources that needs to be cleaned up, and
    where that cleanup may require blocking operations.

    This class distinguishes between "graceful" closes, which may perform I/O
    and thus block, and a "forceful" close, which cannot. For example, cleanly
    shutting down a TLS-encrypted connection requires sending a "goodbye"
    message; but if a peer has become non-responsive, then sending this
    message might block forever, so we may want to just drop the connection
    instead. Therefore the :meth:`aclose` method is unusual in that it
    should always close the connection (or at least make its best attempt)
    *even if it fails*; failure indicates a failure to achieve grace, not a
    failure to close the connection.

    Objects that implement this interface can be used as async context
    managers, i.e., you can write::

      async with create_resource() as some_async_resource:
          ...

    Entering the context manager is synchronous (not a checkpoint); exiting it
    calls :meth:`aclose`. The default implementations of
    ``__aenter__`` and ``__aexit__`` should be adequate for all subclasses.

    """

    __slots__ = ()

    @abstractmethod
    async def aclose(self) -> None:
        """Close this resource, possibly blocking.

        IMPORTANT: This method may block in order to perform a "graceful"
        shutdown. But, if this fails, then it still *must* close any
        underlying resources before returning. An error from this method
        indicates a failure to achieve grace, *not* a failure to close the
        connection.

        For example, suppose we call :meth:`aclose` on a TLS-encrypted
        connection. This requires sending a "goodbye" message; but if the peer
        has become non-responsive, then our attempt to send this message might
        block forever, and eventually time out and be cancelled. In this case
        the :meth:`aclose` method on :class:`~trio.SSLStream` will
        immediately close the underlying transport stream using
        :func:`trio.aclose_forcefully` before raising :exc:`~trio.Cancelled`.

        If the resource is already closed, then this method should silently
        succeed.

        Once this method completes, any other pending or future operations on
        this resource should generally raise :exc:`~trio.ClosedResourceError`,
        unless there's a good reason to do otherwise.

        See also: :func:`trio.aclose_forcefully`.

        """

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()


class SendStream(AsyncResource):
    """A standard interface for sending data on a byte stream.

    The underlying stream may be unidirectional, or bidirectional. If it's
    bidirectional, then you probably want to also implement
    :class:`ReceiveStream`, which makes your object a :class:`Stream`.

    :class:`SendStream` objects also implement the :class:`AsyncResource`
    interface, so they can be closed by calling :meth:`~AsyncResource.aclose`
    or using an ``async with`` block.

    If you want to send Python objects rather than raw bytes, see
    :class:`SendChannel`.

    """

    __slots__ = ()

    @abstractmethod
    async def send_all(self, data: bytes | bytearray | memoryview) -> None:
        """Sends the given data through the stream, blocking if necessary.

        Args:
          data (bytes, bytearray, or memoryview): The data to send.

        Raises:
          trio.BusyResourceError: if another task is already executing a
              :meth:`send_all`, :meth:`wait_send_all_might_not_block`, or
              :meth:`HalfCloseableStream.send_eof` on this stream.
          trio.BrokenResourceError: if something has gone wrong, and the stream
              is broken.
          trio.ClosedResourceError: if you previously closed this stream
              object, or if another task closes this stream object while
              :meth:`send_all` is running.

        Most low-level operations in Trio provide a guarantee: if they raise
        :exc:`trio.Cancelled`, this means that they had no effect, so the
        system remains in a known state. This is **not true** for
        :meth:`send_all`. If this operation raises :exc:`trio.Cancelled` (or
        any other exception for that matter), then it may have sent some, all,
        or none of the requested data, and there is no way to know which.

        """

    @abstractmethod
    async def wait_send_all_might_not_block(self) -> None:
        """Block until it's possible that :meth:`send_all` might not block.

        This method may return early: it's possible that after it returns,
        :meth:`send_all` will still block. (In the worst case, if no better
        implementation is available, then it might always return immediately
        without blocking. It's nice to do better than that when possible,
        though.)

        This method **must not** return *late*: if it's possible for
        :meth:`send_all` to complete without blocking, then it must
        return. When implementing it, err on the side of returning early.

        Raises:
          trio.BusyResourceError: if another task is already executing a
              :meth:`send_all`, :meth:`wait_send_all_might_not_block`, or
              :meth:`HalfCloseableStream.send_eof` on this stream.
          trio.BrokenResourceError: if something has gone wrong, and the stream
              is broken.
          trio.ClosedResourceError: if you previously closed this stream
              object, or if another task closes this stream object while
              :meth:`wait_send_all_might_not_block` is running.

        Note:

          This method is intended to aid in implementing protocols that want
          to delay choosing which data to send until the last moment. E.g.,
          suppose you're working on an implementation of a remote display server
          like `VNC
          <https://en.wikipedia.org/wiki/Virtual_Network_Computing>`__, and
          the network connection is currently backed up so that if you call
          :meth:`send_all` now then it will sit for 0.5 seconds before actually
          sending anything. In this case it doesn't make sense to take a
          screenshot, then wait 0.5 seconds, and then send it, because the
          screen will keep changing while you wait; it's better to wait 0.5
          seconds, then take the screenshot, and then send it, because this
          way the data you deliver will be more
          up-to-date. Using :meth:`wait_send_all_might_not_block` makes it
          possible to implement the better strategy.

          If you use this method, you might also want to read up on
          ``TCP_NOTSENT_LOWAT``.

          Further reading:

          * `Prioritization Only Works When There's Pending Data to Prioritize
            <https://insouciant.org/tech/prioritization-only-works-when-theres-pending-data-to-prioritize/>`__

          * WWDC 2015: Your App and Next Generation Networks: `slides
            <http://devstreaming.apple.com/videos/wwdc/2015/719ui2k57m/719/719_your_app_and_next_generation_networks.pdf?dl=1>`__,
            `video and transcript
            <https://developer.apple.com/videos/play/wwdc2015/719/>`__

        """


class ReceiveStream(AsyncResource):
    """A standard interface for receiving data on a byte stream.

    The underlying stream may be unidirectional, or bidirectional. If it's
    bidirectional, then you probably want to also implement
    :class:`SendStream`, which makes your object a :class:`Stream`.

    :class:`ReceiveStream` objects also implement the :class:`AsyncResource`
    interface, so they can be closed by calling :meth:`~AsyncResource.aclose`
    or using an ``async with`` block.

    If you want to receive Python objects rather than raw bytes, see
    :class:`ReceiveChannel`.

    `ReceiveStream` objects can be used in ``async for`` loops. Each iteration
    will produce an arbitrary sized chunk of bytes, like calling
    `receive_some` with no arguments. Every chunk will contain at least one
    byte, and the loop automatically exits when reaching end-of-file.

    """

    __slots__ = ()

    @abstractmethod
    async def receive_some(self, max_bytes: int | None = None) -> bytes | bytearray:
        """Wait until there is data available on this stream, and then return
        some of it.

        A return value of ``b""`` (an empty bytestring) indicates that the
        stream has reached end-of-file. Implementations should be careful that
        they return ``b""`` if, and only if, the stream has reached
        end-of-file!

        Args:
          max_bytes (int): The maximum number of bytes to return. Must be
              greater than zero. Optional; if omitted, then the stream object
              is free to pick a reasonable default.

        Returns:
          bytes or bytearray: The data received.

        Raises:
          trio.BusyResourceError: if two tasks attempt to call
              :meth:`receive_some` on the same stream at the same time.
          trio.BrokenResourceError: if something has gone wrong, and the stream
              is broken.
          trio.ClosedResourceError: if you previously closed this stream
              object, or if another task closes this stream object while
              :meth:`receive_some` is running.

        """

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> bytes | bytearray:
        data = await self.receive_some()
        if not data:
            raise StopAsyncIteration
        return data


class Stream(SendStream, ReceiveStream):
    """A standard interface for interacting with bidirectional byte streams.

    A :class:`Stream` is an object that implements both the
    :class:`SendStream` and :class:`ReceiveStream` interfaces.

    If implementing this interface, you should consider whether you can go one
    step further and implement :class:`HalfCloseableStream`.

    """

    __slots__ = ()


class HalfCloseableStream(Stream):
    """This interface extends :class:`Stream` to also allow closing the send
    part of the stream without closing the receive part.

    """

    __slots__ = ()

    @abstractmethod
    async def send_eof(self) -> None:
        """Send an end-of-file indication on this stream, if possible.

        The difference between :meth:`send_eof` and
        :meth:`~AsyncResource.aclose` is that :meth:`send_eof` is a
        *unidirectional* end-of-file indication. After you call this method,
        you shouldn't try sending any more data on this stream, and your
        remote peer should receive an end-of-file indication (eventually,
        after receiving all the data you sent before that). But, they may
        continue to send data to you, and you can continue to receive it by
        calling :meth:`~ReceiveStream.receive_some`. You can think of it as
        calling :meth:`~AsyncResource.aclose` on just the
        :class:`SendStream` "half" of the stream object (and in fact that's
        literally how :class:`trio.StapledStream` implements it).

        Examples:

        * On a socket, this corresponds to ``shutdown(..., SHUT_WR)`` (`man
          page <https://linux.die.net/man/2/shutdown>`__).

        * The SSH protocol provides the ability to multiplex bidirectional
          "channels" on top of a single encrypted connection. A Trio
          implementation of SSH could expose these channels as
          :class:`HalfCloseableStream` objects, and calling :meth:`send_eof`
          would send an ``SSH_MSG_CHANNEL_EOF`` request (see `RFC 4254 §5.3
          <https://tools.ietf.org/html/rfc4254#section-5.3>`__).

        * On an SSL/TLS-encrypted connection, the protocol doesn't provide any
          way to do a unidirectional shutdown without closing the connection
          entirely, so :class:`~trio.SSLStream` implements
          :class:`Stream`, not :class:`HalfCloseableStream`.

        If an EOF has already been sent, then this method should silently
        succeed.

        Raises:
          trio.BusyResourceError: if another task is already executing a
              :meth:`~SendStream.send_all`,
              :meth:`~SendStream.wait_send_all_might_not_block`, or
              :meth:`send_eof` on this stream.
          trio.BrokenResourceError: if something has gone wrong, and the stream
              is broken.
          trio.ClosedResourceError: if you previously closed this stream
              object, or if another task closes this stream object while
              :meth:`send_eof` is running.

        """


# A regular invariant generic type
T = TypeVar("T")

# The type of object produced by a ReceiveChannel (covariant because
# ReceiveChannel[Derived] can be passed to someone expecting
# ReceiveChannel[Base])
ReceiveType = TypeVar("ReceiveType", covariant=True)

# The type of object accepted by a SendChannel (contravariant because
# SendChannel[Base] can be passed to someone expecting
# SendChannel[Derived])
SendType = TypeVar("SendType", contravariant=True)

# The type of object produced by a Listener (covariant plus must be
# an AsyncResource)
T_resource = TypeVar("T_resource", bound=AsyncResource, covariant=True)


class Listener(AsyncResource, Generic[T_resource]):
    """A standard interface for listening for incoming connections.

    :class:`Listener` objects also implement the :class:`AsyncResource`
    interface, so they can be closed by calling :meth:`~AsyncResource.aclose`
    or using an ``async with`` block.

    """

    __slots__ = ()

    @abstractmethod
    async def accept(self) -> T_resource:
        """Wait until an incoming connection arrives, and then return it.

        Returns:
          AsyncResource: An object representing the incoming connection. In
          practice this is generally some kind of :class:`Stream`,
          but in principle you could also define a :class:`Listener` that
          returned, say, channel objects.

        Raises:
          trio.BusyResourceError: if two tasks attempt to call
              :meth:`accept` on the same listener at the same time.
          trio.ClosedResourceError: if you previously closed this listener
              object, or if another task closes this listener object while
              :meth:`accept` is running.

        Listeners don't generally raise :exc:`~trio.BrokenResourceError`,
        because for listeners there is no general condition of "the
        network/remote peer broke the connection" that can be handled in a
        generic way, like there is for streams. Other errors *can* occur and
        be raised from :meth:`accept` – for example, if you run out of file
        descriptors then you might get an :class:`OSError` with its errno set
        to ``EMFILE``.

        """


class SendChannel(AsyncResource, Generic[SendType]):
    """A standard interface for sending Python objects to some receiver.

    `SendChannel` objects also implement the `AsyncResource` interface, so
    they can be closed by calling `~AsyncResource.aclose` or using an ``async
    with`` block.

    If you want to send raw bytes rather than Python objects, see
    `SendStream`.

    """

    __slots__ = ()

    @abstractmethod
    async def send(self, value: SendType) -> None:
        """Attempt to send an object through the channel, blocking if necessary.

        Args:
          value (object): The object to send.

        Raises:
          trio.BrokenResourceError: if something has gone wrong, and the
              channel is broken. For example, you may get this if the receiver
              has already been closed.
          trio.ClosedResourceError: if you previously closed this
              :class:`SendChannel` object, or if another task closes it while
              :meth:`send` is running.
          trio.BusyResourceError: some channels allow multiple tasks to call
              `send` at the same time, but others don't. If you try to call
              `send` simultaneously from multiple tasks on a channel that
              doesn't support it, then you can get `~trio.BusyResourceError`.

        """


class ReceiveChannel(AsyncResource, Generic[ReceiveType]):
    """A standard interface for receiving Python objects from some sender.

    You can iterate over a :class:`ReceiveChannel` using an ``async for``
    loop::

       async for value in receive_channel:
           ...

    This is equivalent to calling :meth:`receive` repeatedly. The loop exits
    without error when `receive` raises `~trio.EndOfChannel`.

    `ReceiveChannel` objects also implement the `AsyncResource` interface, so
    they can be closed by calling `~AsyncResource.aclose` or using an ``async
    with`` block.

    If you want to receive raw bytes rather than Python objects, see
    `ReceiveStream`.

    """

    __slots__ = ()

    @abstractmethod
    async def receive(self) -> ReceiveType:
        """Attempt to receive an incoming object, blocking if necessary.

        Returns:
          object: Whatever object was received.

        Raises:
          trio.EndOfChannel: if the sender has been closed cleanly, and no
              more objects are coming. This is not an error condition.
          trio.ClosedResourceError: if you previously closed this
              :class:`ReceiveChannel` object.
          trio.BrokenResourceError: if something has gone wrong, and the
              channel is broken.
          trio.BusyResourceError: some channels allow multiple tasks to call
              `receive` at the same time, but others don't. If you try to call
              `receive` simultaneously from multiple tasks on a channel that
              doesn't support it, then you can get `~trio.BusyResourceError`.

        """

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> ReceiveType:
        try:
            return await self.receive()
        except trio.EndOfChannel:
            raise StopAsyncIteration from None


# these are necessary for Sphinx's :show-inheritance: with type args.
# (this should be removed if possible)
# see: https://github.com/python/cpython/issues/123250
SendChannel.__module__ = SendChannel.__module__.replace("_abc", "abc")
ReceiveChannel.__module__ = ReceiveChannel.__module__.replace("_abc", "abc")
Listener.__module__ = Listener.__module__.replace("_abc", "abc")


class Channel(SendChannel[T], ReceiveChannel[T]):
    """A standard interface for interacting with bidirectional channels.

    A `Channel` is an object that implements both the `SendChannel` and
    `ReceiveChannel` interfaces, so you can both send and receive objects.

    """

    __slots__ = ()


# see above
Channel.__module__ = Channel.__module__.replace("_abc", "abc")

# === NexusCore/openenv\Lib\site-packages\nltk\translate\bleu_score.py ===
# Natural Language Toolkit: BLEU Score
#
# Copyright (C) 2001-2024 NLTK Project
# Authors: Chin Yee Lee, Hengfeng Li, Ruxin Hou, Calvin Tanujaya Lim
# Contributors: Björn Mattsson, Dmitrijs Milajevs, Liling Tan
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""BLEU score implementation."""
import math
import sys
import warnings
from collections import Counter
from fractions import Fraction as _Fraction

from nltk.util import ngrams


class Fraction(_Fraction):
    """Fraction with _normalize=False support for 3.12"""

    def __new__(cls, numerator=0, denominator=None, _normalize=False):
        if sys.version_info >= (3, 12):
            self = super().__new__(cls, numerator, denominator)
        else:
            self = super().__new__(cls, numerator, denominator, _normalize=_normalize)
        self._normalize = _normalize
        self._original_numerator = numerator
        self._original_denominator = denominator
        return self

    @property
    def numerator(self):
        if not self._normalize:
            return self._original_numerator
        return super().numerator

    @property
    def denominator(self):
        if not self._normalize:
            return self._original_denominator
        return super().denominator


def sentence_bleu(
    references,
    hypothesis,
    weights=(0.25, 0.25, 0.25, 0.25),
    smoothing_function=None,
    auto_reweigh=False,
):
    """
    Calculate BLEU score (Bilingual Evaluation Understudy) from
    Papineni, Kishore, Salim Roukos, Todd Ward, and Wei-Jing Zhu. 2002.
    "BLEU: a method for automatic evaluation of machine translation."
    In Proceedings of ACL. https://www.aclweb.org/anthology/P02-1040.pdf

    >>> hypothesis1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
    ...               'ensures', 'that', 'the', 'military', 'always',
    ...               'obeys', 'the', 'commands', 'of', 'the', 'party']

    >>> hypothesis2 = ['It', 'is', 'to', 'insure', 'the', 'troops',
    ...               'forever', 'hearing', 'the', 'activity', 'guidebook',
    ...               'that', 'party', 'direct']

    >>> reference1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
    ...               'ensures', 'that', 'the', 'military', 'will', 'forever',
    ...               'heed', 'Party', 'commands']

    >>> reference2 = ['It', 'is', 'the', 'guiding', 'principle', 'which',
    ...               'guarantees', 'the', 'military', 'forces', 'always',
    ...               'being', 'under', 'the', 'command', 'of', 'the',
    ...               'Party']

    >>> reference3 = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
    ...               'army', 'always', 'to', 'heed', 'the', 'directions',
    ...               'of', 'the', 'party']

    >>> sentence_bleu([reference1, reference2, reference3], hypothesis1) # doctest: +ELLIPSIS
    0.5045...

    If there is no ngrams overlap for any order of n-grams, BLEU returns the
    value 0. This is because the precision for the order of n-grams without
    overlap is 0, and the geometric mean in the final BLEU score computation
    multiplies the 0 with the precision of other n-grams. This results in 0
    (independently of the precision of the other n-gram orders). The following
    example has zero 3-gram and 4-gram overlaps:

    >>> round(sentence_bleu([reference1, reference2, reference3], hypothesis2),4) # doctest: +ELLIPSIS
    0.0

    To avoid this harsh behaviour when no ngram overlaps are found a smoothing
    function can be used.

    >>> chencherry = SmoothingFunction()
    >>> sentence_bleu([reference1, reference2, reference3], hypothesis2,
    ...     smoothing_function=chencherry.method1) # doctest: +ELLIPSIS
    0.0370...

    The default BLEU calculates a score for up to 4-grams using uniform
    weights (this is called BLEU-4). To evaluate your translations with
    higher/lower order ngrams, use customized weights. E.g. when accounting
    for up to 5-grams with uniform weights (this is called BLEU-5) use:

    >>> weights = (1./5., 1./5., 1./5., 1./5., 1./5.)
    >>> sentence_bleu([reference1, reference2, reference3], hypothesis1, weights) # doctest: +ELLIPSIS
    0.3920...

    Multiple BLEU scores can be computed at once, by supplying a list of weights.
    E.g. for computing BLEU-2, BLEU-3 *and* BLEU-4 in one computation, use:
    >>> weights = [
    ...     (1./2., 1./2.),
    ...     (1./3., 1./3., 1./3.),
    ...     (1./4., 1./4., 1./4., 1./4.)
    ... ]
    >>> sentence_bleu([reference1, reference2, reference3], hypothesis1, weights) # doctest: +ELLIPSIS
    [0.7453..., 0.6240..., 0.5045...]

    :param references: reference sentences
    :type references: list(list(str))
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    :param weights: weights for unigrams, bigrams, trigrams and so on (one or a list of weights)
    :type weights: tuple(float) / list(tuple(float))
    :param smoothing_function:
    :type smoothing_function: SmoothingFunction
    :param auto_reweigh: Option to re-normalize the weights uniformly.
    :type auto_reweigh: bool
    :return: The sentence-level BLEU score. Returns a list if multiple weights were supplied.
    :rtype: float / list(float)
    """
    return corpus_bleu(
        [references], [hypothesis], weights, smoothing_function, auto_reweigh
    )


def corpus_bleu(
    list_of_references,
    hypotheses,
    weights=(0.25, 0.25, 0.25, 0.25),
    smoothing_function=None,
    auto_reweigh=False,
):
    """
    Calculate a single corpus-level BLEU score (aka. system-level BLEU) for all
    the hypotheses and their respective references.

    Instead of averaging the sentence level BLEU scores (i.e. macro-average
    precision), the original BLEU metric (Papineni et al. 2002) accounts for
    the micro-average precision (i.e. summing the numerators and denominators
    for each hypothesis-reference(s) pairs before the division).

    >>> hyp1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
    ...         'ensures', 'that', 'the', 'military', 'always',
    ...         'obeys', 'the', 'commands', 'of', 'the', 'party']
    >>> ref1a = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
    ...          'ensures', 'that', 'the', 'military', 'will', 'forever',
    ...          'heed', 'Party', 'commands']
    >>> ref1b = ['It', 'is', 'the', 'guiding', 'principle', 'which',
    ...          'guarantees', 'the', 'military', 'forces', 'always',
    ...          'being', 'under', 'the', 'command', 'of', 'the', 'Party']
    >>> ref1c = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
    ...          'army', 'always', 'to', 'heed', 'the', 'directions',
    ...          'of', 'the', 'party']

    >>> hyp2 = ['he', 'read', 'the', 'book', 'because', 'he', 'was',
    ...         'interested', 'in', 'world', 'history']
    >>> ref2a = ['he', 'was', 'interested', 'in', 'world', 'history',
    ...          'because', 'he', 'read', 'the', 'book']

    >>> list_of_references = [[ref1a, ref1b, ref1c], [ref2a]]
    >>> hypotheses = [hyp1, hyp2]
    >>> corpus_bleu(list_of_references, hypotheses) # doctest: +ELLIPSIS
    0.5920...

    The example below show that corpus_bleu() is different from averaging
    sentence_bleu() for hypotheses

    >>> score1 = sentence_bleu([ref1a, ref1b, ref1c], hyp1)
    >>> score2 = sentence_bleu([ref2a], hyp2)
    >>> (score1 + score2) / 2 # doctest: +ELLIPSIS
    0.6223...

    Custom weights may be supplied to fine-tune the BLEU score further.
    A tuple of float weights for unigrams, bigrams, trigrams and so on can be given.
    >>> weights = (0.1, 0.3, 0.5, 0.1)
    >>> corpus_bleu(list_of_references, hypotheses, weights=weights) # doctest: +ELLIPSIS
    0.5818...

    This particular weight gave extra value to trigrams.
    Furthermore, multiple weights can be given, resulting in multiple BLEU scores.
    >>> weights = [
    ...     (0.5, 0.5),
    ...     (0.333, 0.333, 0.334),
    ...     (0.25, 0.25, 0.25, 0.25),
    ...     (0.2, 0.2, 0.2, 0.2, 0.2)
    ... ]
    >>> corpus_bleu(list_of_references, hypotheses, weights=weights) # doctest: +ELLIPSIS
    [0.8242..., 0.7067..., 0.5920..., 0.4719...]

    :param list_of_references: a corpus of lists of reference sentences, w.r.t. hypotheses
    :type list_of_references: list(list(list(str)))
    :param hypotheses: a list of hypothesis sentences
    :type hypotheses: list(list(str))
    :param weights: weights for unigrams, bigrams, trigrams and so on (one or a list of weights)
    :type weights: tuple(float) / list(tuple(float))
    :param smoothing_function:
    :type smoothing_function: SmoothingFunction
    :param auto_reweigh: Option to re-normalize the weights uniformly.
    :type auto_reweigh: bool
    :return: The corpus-level BLEU score.
    :rtype: float
    """
    # Before proceeding to compute BLEU, perform sanity checks.

    p_numerators = Counter()  # Key = ngram order, and value = no. of ngram matches.
    p_denominators = Counter()  # Key = ngram order, and value = no. of ngram in ref.
    hyp_lengths, ref_lengths = 0, 0

    assert len(list_of_references) == len(hypotheses), (
        "The number of hypotheses and their reference(s) should be the " "same "
    )

    try:
        weights[0][0]
    except:
        weights = [weights]
    max_weight_length = max(len(weight) for weight in weights)

    # Iterate through each hypothesis and their corresponding references.
    for references, hypothesis in zip(list_of_references, hypotheses):
        # For each order of ngram, calculate the numerator and
        # denominator for the corpus-level modified precision.
        for i in range(1, max_weight_length + 1):
            p_i = modified_precision(references, hypothesis, i)
            p_numerators[i] += p_i.numerator
            p_denominators[i] += p_i.denominator

        # Calculate the hypothesis length and the closest reference length.
        # Adds them to the corpus-level hypothesis and reference counts.
        hyp_len = len(hypothesis)
        hyp_lengths += hyp_len
        ref_lengths += closest_ref_length(references, hyp_len)

    # Calculate corpus-level brevity penalty.
    bp = brevity_penalty(ref_lengths, hyp_lengths)

    # Collects the various precision values for the different ngram orders.
    p_n = [
        Fraction(p_numerators[i], p_denominators[i], _normalize=False)
        for i in range(1, max_weight_length + 1)
    ]

    # Returns 0 if there's no matching n-grams
    # We only need to check for p_numerators[1] == 0, since if there's
    # no unigrams, there won't be any higher order ngrams.
    if p_numerators[1] == 0:
        return 0 if len(weights) == 1 else [0] * len(weights)

    # If there's no smoothing, set use method0 from SmoothinFunction class.
    if not smoothing_function:
        smoothing_function = SmoothingFunction().method0
    # Smoothen the modified precision.
    # Note: smoothing_function() may convert values into floats;
    #       it tries to retain the Fraction object as much as the
    #       smoothing method allows.
    p_n = smoothing_function(
        p_n, references=references, hypothesis=hypothesis, hyp_len=hyp_lengths
    )

    bleu_scores = []
    for weight in weights:
        # Uniformly re-weighting based on maximum hypothesis lengths if largest
        # order of n-grams < 4 and weights is set at default.
        if auto_reweigh:
            if hyp_lengths < 4 and weight == (0.25, 0.25, 0.25, 0.25):
                weight = (1 / hyp_lengths,) * hyp_lengths

        s = (w_i * math.log(p_i) for w_i, p_i in zip(weight, p_n) if p_i > 0)
        s = bp * math.exp(math.fsum(s))
        bleu_scores.append(s)
    return bleu_scores[0] if len(weights) == 1 else bleu_scores


def modified_precision(references, hypothesis, n):
    """
    Calculate modified ngram precision.

    The normal precision method may lead to some wrong translations with
    high-precision, e.g., the translation, in which a word of reference
    repeats several times, has very high precision.

    This function only returns the Fraction object that contains the numerator
    and denominator necessary to calculate the corpus-level precision.
    To calculate the modified precision for a single pair of hypothesis and
    references, cast the Fraction object into a float.

    The famous "the the the ... " example shows that you can get BLEU precision
    by duplicating high frequency words.

        >>> reference1 = 'the cat is on the mat'.split()
        >>> reference2 = 'there is a cat on the mat'.split()
        >>> hypothesis1 = 'the the the the the the the'.split()
        >>> references = [reference1, reference2]
        >>> float(modified_precision(references, hypothesis1, n=1)) # doctest: +ELLIPSIS
        0.2857...

    In the modified n-gram precision, a reference word will be considered
    exhausted after a matching hypothesis word is identified, e.g.

        >>> reference1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
        ...               'ensures', 'that', 'the', 'military', 'will',
        ...               'forever', 'heed', 'Party', 'commands']
        >>> reference2 = ['It', 'is', 'the', 'guiding', 'principle', 'which',
        ...               'guarantees', 'the', 'military', 'forces', 'always',
        ...               'being', 'under', 'the', 'command', 'of', 'the',
        ...               'Party']
        >>> reference3 = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
        ...               'army', 'always', 'to', 'heed', 'the', 'directions',
        ...               'of', 'the', 'party']
        >>> hypothesis = 'of the'.split()
        >>> references = [reference1, reference2, reference3]
        >>> float(modified_precision(references, hypothesis, n=1))
        1.0
        >>> float(modified_precision(references, hypothesis, n=2))
        1.0

    An example of a normal machine translation hypothesis:

        >>> hypothesis1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
        ...               'ensures', 'that', 'the', 'military', 'always',
        ...               'obeys', 'the', 'commands', 'of', 'the', 'party']

        >>> hypothesis2 = ['It', 'is', 'to', 'insure', 'the', 'troops',
        ...               'forever', 'hearing', 'the', 'activity', 'guidebook',
        ...               'that', 'party', 'direct']

        >>> reference1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
        ...               'ensures', 'that', 'the', 'military', 'will',
        ...               'forever', 'heed', 'Party', 'commands']

        >>> reference2 = ['It', 'is', 'the', 'guiding', 'principle', 'which',
        ...               'guarantees', 'the', 'military', 'forces', 'always',
        ...               'being', 'under', 'the', 'command', 'of', 'the',
        ...               'Party']

        >>> reference3 = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
        ...               'army', 'always', 'to', 'heed', 'the', 'directions',
        ...               'of', 'the', 'party']
        >>> references = [reference1, reference2, reference3]
        >>> float(modified_precision(references, hypothesis1, n=1)) # doctest: +ELLIPSIS
        0.9444...
        >>> float(modified_precision(references, hypothesis2, n=1)) # doctest: +ELLIPSIS
        0.5714...
        >>> float(modified_precision(references, hypothesis1, n=2)) # doctest: +ELLIPSIS
        0.5882352941176471
        >>> float(modified_precision(references, hypothesis2, n=2)) # doctest: +ELLIPSIS
        0.07692...


    :param references: A list of reference translations.
    :type references: list(list(str))
    :param hypothesis: A hypothesis translation.
    :type hypothesis: list(str)
    :param n: The ngram order.
    :type n: int
    :return: BLEU's modified precision for the nth order ngram.
    :rtype: Fraction
    """
    # Extracts all ngrams in hypothesis
    # Set an empty Counter if hypothesis is empty.
    counts = Counter(ngrams(hypothesis, n)) if len(hypothesis) >= n else Counter()
    # Extract a union of references' counts.
    # max_counts = reduce(or_, [Counter(ngrams(ref, n)) for ref in references])
    max_counts = {}
    for reference in references:
        reference_counts = (
            Counter(ngrams(reference, n)) if len(reference) >= n else Counter()
        )
        for ngram in counts:
            max_counts[ngram] = max(max_counts.get(ngram, 0), reference_counts[ngram])

    # Assigns the intersection between hypothesis and references' counts.
    clipped_counts = {
        ngram: min(count, max_counts[ngram]) for ngram, count in counts.items()
    }

    numerator = sum(clipped_counts.values())
    # Ensures that denominator is minimum 1 to avoid ZeroDivisionError.
    # Usually this happens when the ngram order is > len(reference).
    denominator = max(1, sum(counts.values()))

    return Fraction(numerator, denominator, _normalize=False)


def closest_ref_length(references, hyp_len):
    """
    This function finds the reference that is the closest length to the
    hypothesis. The closest reference length is referred to as *r* variable
    from the brevity penalty formula in Papineni et. al. (2002)

    :param references: A list of reference translations.
    :type references: list(list(str))
    :param hyp_len: The length of the hypothesis.
    :type hyp_len: int
    :return: The length of the reference that's closest to the hypothesis.
    :rtype: int
    """
    ref_lens = (len(reference) for reference in references)
    closest_ref_len = min(
        ref_lens, key=lambda ref_len: (abs(ref_len - hyp_len), ref_len)
    )
    return closest_ref_len


def brevity_penalty(closest_ref_len, hyp_len):
    """
    Calculate brevity penalty.

    As the modified n-gram precision still has the problem from the short
    length sentence, brevity penalty is used to modify the overall BLEU
    score according to length.

    An example from the paper. There are three references with length 12, 15
    and 17. And a concise hypothesis of the length 12. The brevity penalty is 1.

    >>> reference1 = list('aaaaaaaaaaaa')      # i.e. ['a'] * 12
    >>> reference2 = list('aaaaaaaaaaaaaaa')   # i.e. ['a'] * 15
    >>> reference3 = list('aaaaaaaaaaaaaaaaa') # i.e. ['a'] * 17
    >>> hypothesis = list('aaaaaaaaaaaa')      # i.e. ['a'] * 12
    >>> references = [reference1, reference2, reference3]
    >>> hyp_len = len(hypothesis)
    >>> closest_ref_len =  closest_ref_length(references, hyp_len)
    >>> brevity_penalty(closest_ref_len, hyp_len)
    1.0

    In case a hypothesis translation is shorter than the references, penalty is
    applied.

    >>> references = [['a'] * 28, ['a'] * 28]
    >>> hypothesis = ['a'] * 12
    >>> hyp_len = len(hypothesis)
    >>> closest_ref_len =  closest_ref_length(references, hyp_len)
    >>> brevity_penalty(closest_ref_len, hyp_len)
    0.2635971381157267

    The length of the closest reference is used to compute the penalty. If the
    length of a hypothesis is 12, and the reference lengths are 13 and 2, the
    penalty is applied because the hypothesis length (12) is less then the
    closest reference length (13).

    >>> references = [['a'] * 13, ['a'] * 2]
    >>> hypothesis = ['a'] * 12
    >>> hyp_len = len(hypothesis)
    >>> closest_ref_len =  closest_ref_length(references, hyp_len)
    >>> brevity_penalty(closest_ref_len, hyp_len) # doctest: +ELLIPSIS
    0.9200...

    The brevity penalty doesn't depend on reference order. More importantly,
    when two reference sentences are at the same distance, the shortest
    reference sentence length is used.

    >>> references = [['a'] * 13, ['a'] * 11]
    >>> hypothesis = ['a'] * 12
    >>> hyp_len = len(hypothesis)
    >>> closest_ref_len =  closest_ref_length(references, hyp_len)
    >>> bp1 = brevity_penalty(closest_ref_len, hyp_len)
    >>> hyp_len = len(hypothesis)
    >>> closest_ref_len =  closest_ref_length(reversed(references), hyp_len)
    >>> bp2 = brevity_penalty(closest_ref_len, hyp_len)
    >>> bp1 == bp2 == 1
    True

    A test example from mteval-v13a.pl (starting from the line 705):

    >>> references = [['a'] * 11, ['a'] * 8]
    >>> hypothesis = ['a'] * 7
    >>> hyp_len = len(hypothesis)
    >>> closest_ref_len =  closest_ref_length(references, hyp_len)
    >>> brevity_penalty(closest_ref_len, hyp_len) # doctest: +ELLIPSIS
    0.8668...

    >>> references = [['a'] * 11, ['a'] * 8, ['a'] * 6, ['a'] * 7]
    >>> hypothesis = ['a'] * 7
    >>> hyp_len = len(hypothesis)
    >>> closest_ref_len =  closest_ref_length(references, hyp_len)
    >>> brevity_penalty(closest_ref_len, hyp_len)
    1.0

    :param hyp_len: The length of the hypothesis for a single sentence OR the
        sum of all the hypotheses' lengths for a corpus
    :type hyp_len: int
    :param closest_ref_len: The length of the closest reference for a single
        hypothesis OR the sum of all the closest references for every hypotheses.
    :type closest_ref_len: int
    :return: BLEU's brevity penalty.
    :rtype: float
    """
    if hyp_len > closest_ref_len:
        return 1
    # If hypothesis is empty, brevity penalty = 0 should result in BLEU = 0.0
    elif hyp_len == 0:
        return 0
    else:
        return math.exp(1 - closest_ref_len / hyp_len)


class SmoothingFunction:
    """
    This is an implementation of the smoothing techniques
    for segment-level BLEU scores that was presented in
    Boxing Chen and Collin Cherry (2014) A Systematic Comparison of
    Smoothing Techniques for Sentence-Level BLEU. In WMT14.
    http://acl2014.org/acl2014/W14-33/pdf/W14-3346.pdf
    """

    def __init__(self, epsilon=0.1, alpha=5, k=5):
        """
        This will initialize the parameters required for the various smoothing
        techniques, the default values are set to the numbers used in the
        experiments from Chen and Cherry (2014).

        >>> hypothesis1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which', 'ensures',
        ...                 'that', 'the', 'military', 'always', 'obeys', 'the',
        ...                 'commands', 'of', 'the', 'party']
        >>> reference1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that', 'ensures',
        ...               'that', 'the', 'military', 'will', 'forever', 'heed',
        ...               'Party', 'commands']

        >>> chencherry = SmoothingFunction()
        >>> print(sentence_bleu([reference1], hypothesis1)) # doctest: +ELLIPSIS
        0.4118...
        >>> print(sentence_bleu([reference1], hypothesis1, smoothing_function=chencherry.method0)) # doctest: +ELLIPSIS
        0.4118...
        >>> print(sentence_bleu([reference1], hypothesis1, smoothing_function=chencherry.method1)) # doctest: +ELLIPSIS
        0.4118...
        >>> print(sentence_bleu([reference1], hypothesis1, smoothing_function=chencherry.method2)) # doctest: +ELLIPSIS
        0.4452...
        >>> print(sentence_bleu([reference1], hypothesis1, smoothing_function=chencherry.method3)) # doctest: +ELLIPSIS
        0.4118...
        >>> print(sentence_bleu([reference1], hypothesis1, smoothing_function=chencherry.method4)) # doctest: +ELLIPSIS
        0.4118...
        >>> print(sentence_bleu([reference1], hypothesis1, smoothing_function=chencherry.method5)) # doctest: +ELLIPSIS
        0.4905...
        >>> print(sentence_bleu([reference1], hypothesis1, smoothing_function=chencherry.method6)) # doctest: +ELLIPSIS
        0.4135...
        >>> print(sentence_bleu([reference1], hypothesis1, smoothing_function=chencherry.method7)) # doctest: +ELLIPSIS
        0.4905...

        :param epsilon: the epsilon value use in method 1
        :type epsilon: float
        :param alpha: the alpha value use in method 6
        :type alpha: int
        :param k: the k value use in method 4
        :type k: int
        """
        self.epsilon = epsilon
        self.alpha = alpha
        self.k = k

    def method0(self, p_n, *args, **kwargs):
        """
        No smoothing.
        """
        p_n_new = []
        for i, p_i in enumerate(p_n):
            if p_i.numerator != 0:
                p_n_new.append(p_i)
            else:
                _msg = str(
                    "\nThe hypothesis contains 0 counts of {}-gram overlaps.\n"
                    "Therefore the BLEU score evaluates to 0, independently of\n"
                    "how many N-gram overlaps of lower order it contains.\n"
                    "Consider using lower n-gram order or use "
                    "SmoothingFunction()"
                ).format(i + 1)
                warnings.warn(_msg)
                # When numerator==0 where denonminator==0 or !=0, the result
                # for the precision score should be equal to 0 or undefined.
                # Due to BLEU geometric mean computation in logarithm space,
                # we we need to take the return sys.float_info.min such that
                # math.log(sys.float_info.min) returns a 0 precision score.
                p_n_new.append(sys.float_info.min)
        return p_n_new

    def method1(self, p_n, *args, **kwargs):
        """
        Smoothing method 1: Add *epsilon* counts to precision with 0 counts.
        """
        return [
            (
                (p_i.numerator + self.epsilon) / p_i.denominator
                if p_i.numerator == 0
                else p_i
            )
            for p_i in p_n
        ]

    def method2(self, p_n, *args, **kwargs):
        """
        Smoothing method 2: Add 1 to both numerator and denominator from
        Chin-Yew Lin and Franz Josef Och (2004) ORANGE: a Method for
        Evaluating Automatic Evaluation Metrics for Machine Translation.
        In COLING 2004.
        """
        return [
            (
                Fraction(p_n[i].numerator + 1, p_n[i].denominator + 1, _normalize=False)
                if i != 0
                else p_n[0]
            )
            for i in range(len(p_n))
        ]

    def method3(self, p_n, *args, **kwargs):
        """
        Smoothing method 3: NIST geometric sequence smoothing
        The smoothing is computed by taking 1 / ( 2^k ), instead of 0, for each
        precision score whose matching n-gram count is null.
        k is 1 for the first 'n' value for which the n-gram match count is null/

        For example, if the text contains:

        - one 2-gram match
        - and (consequently) two 1-gram matches

        the n-gram count for each individual precision score would be:

        - n=1  =>  prec_count = 2     (two unigrams)
        - n=2  =>  prec_count = 1     (one bigram)
        - n=3  =>  prec_count = 1/2   (no trigram,  taking 'smoothed' value of 1 / ( 2^k ), with k=1)
        - n=4  =>  prec_count = 1/4   (no fourgram, taking 'smoothed' value of 1 / ( 2^k ), with k=2)
        """
        incvnt = 1  # From the mteval-v13a.pl, it's referred to as k.
        for i, p_i in enumerate(p_n):
            if p_i.numerator == 0:
                p_n[i] = 1 / (2**incvnt * p_i.denominator)
                incvnt += 1
        return p_n

    def method4(self, p_n, references, hypothesis, hyp_len=None, *args, **kwargs):
        """
        Smoothing method 4:
        Shorter translations may have inflated precision values due to having
        smaller denominators; therefore, we give them proportionally
        smaller smoothed counts. Instead of scaling to 1/(2^k), Chen and Cherry
        suggests dividing by 1/ln(len(T)), where T is the length of the translation.
        """
        incvnt = 1
        hyp_len = hyp_len if hyp_len else len(hypothesis)
        for i, p_i in enumerate(p_n):
            if p_i.numerator == 0 and hyp_len > 1:
                # incvnt = i + 1 * self.k / math.log(
                #     hyp_len
                # )  # Note that this K is different from the K from NIST.
                # p_n[i] = incvnt / p_i.denominator\
                numerator = 1 / (2**incvnt * self.k / math.log(hyp_len))
                p_n[i] = numerator / p_i.denominator
                incvnt += 1
        return p_n

    def method5(self, p_n, references, hypothesis, hyp_len=None, *args, **kwargs):
        """
        Smoothing method 5:
        The matched counts for similar values of n should be similar. To a
        calculate the n-gram matched count, it averages the n−1, n and n+1 gram
        matched counts.
        """
        hyp_len = hyp_len if hyp_len else len(hypothesis)
        m = {}
        # Requires an precision value for an addition ngram order.
        p_n_plus1 = p_n + [modified_precision(references, hypothesis, 5)]
        m[-1] = p_n[0] + 1
        for i, p_i in enumerate(p_n):
            p_n[i] = (m[i - 1] + p_i + p_n_plus1[i + 1]) / 3
            m[i] = p_n[i]
        return p_n

    def method6(self, p_n, references, hypothesis, hyp_len=None, *args, **kwargs):
        """
        Smoothing method 6:
        Interpolates the maximum likelihood estimate of the precision *p_n* with
        a prior estimate *pi0*. The prior is estimated by assuming that the ratio
        between pn and pn−1 will be the same as that between pn−1 and pn−2; from
        Gao and He (2013) Training MRF-Based Phrase Translation Models using
        Gradient Ascent. In NAACL.
        """
        hyp_len = hyp_len if hyp_len else len(hypothesis)
        # This smoothing only works when p_1 and p_2 is non-zero.
        # Raise an error with an appropriate message when the input is too short
        # to use this smoothing technique.
        assert p_n[2], "This smoothing method requires non-zero precision for bigrams."
        for i, p_i in enumerate(p_n):
            if i in [0, 1]:  # Skips the first 2 orders of ngrams.
                continue
            else:
                pi0 = 0 if p_n[i - 2] == 0 else p_n[i - 1] ** 2 / p_n[i - 2]
                # No. of ngrams in translation that matches the reference.
                m = p_i.numerator
                # No. of ngrams in translation.
                l = sum(1 for _ in ngrams(hypothesis, i + 1))
                # Calculates the interpolated precision.
                p_n[i] = (m + self.alpha * pi0) / (l + self.alpha)
        return p_n

    def method7(self, p_n, references, hypothesis, hyp_len=None, *args, **kwargs):
        """
        Smoothing method 7:
        Interpolates methods 4 and 5.
        """
        hyp_len = hyp_len if hyp_len else len(hypothesis)
        p_n = self.method4(p_n, references, hypothesis, hyp_len)
        p_n = self.method5(p_n, references, hypothesis, hyp_len)
        return p_n

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_typing_extra.py ===
"""Logic for interacting with type annotations, mostly extensions, shims and hacks to wrap Python's typing module."""

from __future__ import annotations

import collections.abc
import re
import sys
import types
import typing
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, cast

import typing_extensions
from typing_extensions import deprecated, get_args, get_origin
from typing_inspection import typing_objects
from typing_inspection.introspection import is_union_origin

from pydantic.version import version_short

from ._namespace_utils import GlobalsNamespace, MappingNamespace, NsResolver, get_module_ns_of

if sys.version_info < (3, 10):
    NoneType = type(None)
    EllipsisType = type(Ellipsis)
else:
    from types import EllipsisType as EllipsisType
    from types import NoneType as NoneType

if TYPE_CHECKING:
    from pydantic import BaseModel

# As per https://typing-extensions.readthedocs.io/en/latest/#runtime-use-of-types,
# always check for both `typing` and `typing_extensions` variants of a typing construct.
# (this is implemented differently than the suggested approach in the `typing_extensions`
# docs for performance).


_t_annotated = typing.Annotated
_te_annotated = typing_extensions.Annotated


def is_annotated(tp: Any, /) -> bool:
    """Return whether the provided argument is a `Annotated` special form.

    ```python {test="skip" lint="skip"}
    is_annotated(Annotated[int, ...])
    #> True
    ```
    """
    origin = get_origin(tp)
    return origin is _t_annotated or origin is _te_annotated


def annotated_type(tp: Any, /) -> Any | None:
    """Return the type of the `Annotated` special form, or `None`."""
    return tp.__origin__ if typing_objects.is_annotated(get_origin(tp)) else None


def unpack_type(tp: Any, /) -> Any | None:
    """Return the type wrapped by the `Unpack` special form, or `None`."""
    return get_args(tp)[0] if typing_objects.is_unpack(get_origin(tp)) else None


def is_hashable(tp: Any, /) -> bool:
    """Return whether the provided argument is the `Hashable` class.

    ```python {test="skip" lint="skip"}
    is_hashable(Hashable)
    #> True
    ```
    """
    # `get_origin` is documented as normalizing any typing-module aliases to `collections` classes,
    # hence the second check:
    return tp is collections.abc.Hashable or get_origin(tp) is collections.abc.Hashable


def is_callable(tp: Any, /) -> bool:
    """Return whether the provided argument is a `Callable`, parametrized or not.

    ```python {test="skip" lint="skip"}
    is_callable(Callable[[int], str])
    #> True
    is_callable(typing.Callable)
    #> True
    is_callable(collections.abc.Callable)
    #> True
    ```
    """
    # `get_origin` is documented as normalizing any typing-module aliases to `collections` classes,
    # hence the second check:
    return tp is collections.abc.Callable or get_origin(tp) is collections.abc.Callable


_classvar_re = re.compile(r'((\w+\.)?Annotated\[)?(\w+\.)?ClassVar\[')


def is_classvar_annotation(tp: Any, /) -> bool:
    """Return whether the provided argument represents a class variable annotation.

    Although not explicitly stated by the typing specification, `ClassVar` can be used
    inside `Annotated` and as such, this function checks for this specific scenario.

    Because this function is used to detect class variables before evaluating forward references
    (or because evaluation failed), we also implement a naive regex match implementation. This is
    required because class variables are inspected before fields are collected, so we try to be
    as accurate as possible.
    """
    if typing_objects.is_classvar(tp):
        return True

    origin = get_origin(tp)

    if typing_objects.is_classvar(origin):
        return True

    if typing_objects.is_annotated(origin):
        annotated_type = tp.__origin__
        if typing_objects.is_classvar(annotated_type) or typing_objects.is_classvar(get_origin(annotated_type)):
            return True

    str_ann: str | None = None
    if isinstance(tp, typing.ForwardRef):
        str_ann = tp.__forward_arg__
    if isinstance(tp, str):
        str_ann = tp

    if str_ann is not None and _classvar_re.match(str_ann):
        # stdlib dataclasses do something similar, although a bit more advanced
        # (see `dataclass._is_type`).
        return True

    return False


_t_final = typing.Final
_te_final = typing_extensions.Final


# TODO implement `is_finalvar_annotation` as Final can be wrapped with other special forms:
def is_finalvar(tp: Any, /) -> bool:
    """Return whether the provided argument is a `Final` special form, parametrized or not.

    ```python {test="skip" lint="skip"}
    is_finalvar(Final[int])
    #> True
    is_finalvar(Final)
    #> True
    """
    # Final is not necessarily parametrized:
    if tp is _t_final or tp is _te_final:
        return True
    origin = get_origin(tp)
    return origin is _t_final or origin is _te_final


_NONE_TYPES: tuple[Any, ...] = (None, NoneType, typing.Literal[None], typing_extensions.Literal[None])


def is_none_type(tp: Any, /) -> bool:
    """Return whether the argument represents the `None` type as part of an annotation.

    ```python {test="skip" lint="skip"}
    is_none_type(None)
    #> True
    is_none_type(NoneType)
    #> True
    is_none_type(Literal[None])
    #> True
    is_none_type(type[None])
    #> False
    """
    return tp in _NONE_TYPES


def is_namedtuple(tp: Any, /) -> bool:
    """Return whether the provided argument is a named tuple class.

    The class can be created using `typing.NamedTuple` or `collections.namedtuple`.
    Parametrized generic classes are *not* assumed to be named tuples.
    """
    from ._utils import lenient_issubclass  # circ. import

    return lenient_issubclass(tp, tuple) and hasattr(tp, '_fields')


# TODO In 2.12, delete this export. It is currently defined only to not break
# pydantic-settings which relies on it:
origin_is_union = is_union_origin


def is_generic_alias(tp: Any, /) -> bool:
    return isinstance(tp, (types.GenericAlias, typing._GenericAlias))  # pyright: ignore[reportAttributeAccessIssue]


# TODO: Ideally, we should avoid relying on the private `typing` constructs:

if sys.version_info < (3, 10):
    WithArgsTypes: tuple[Any, ...] = (typing._GenericAlias, types.GenericAlias)  # pyright: ignore[reportAttributeAccessIssue]
else:
    WithArgsTypes: tuple[Any, ...] = (typing._GenericAlias, types.GenericAlias, types.UnionType)  # pyright: ignore[reportAttributeAccessIssue]


# Similarly, we shouldn't rely on this `_Final` class, which is even more private than `_GenericAlias`:
typing_base: Any = typing._Final  # pyright: ignore[reportAttributeAccessIssue]


### Annotation evaluations functions:


def parent_frame_namespace(*, parent_depth: int = 2, force: bool = False) -> dict[str, Any] | None:
    """Fetch the local namespace of the parent frame where this function is called.

    Using this function is mostly useful to resolve forward annotations pointing to members defined in a local namespace,
    such as assignments inside a function. Using the standard library tools, it is currently not possible to resolve
    such annotations:

    ```python {lint="skip" test="skip"}
    from typing import get_type_hints

    def func() -> None:
        Alias = int

        class C:
            a: 'Alias'

        # Raises a `NameError: 'Alias' is not defined`
        get_type_hints(C)
    ```

    Pydantic uses this function when a Pydantic model is being defined to fetch the parent frame locals. However,
    this only allows us to fetch the parent frame namespace and not other parents (e.g. a model defined in a function,
    itself defined in another function). Inspecting the next outer frames (using `f_back`) is not reliable enough
    (see https://discuss.python.org/t/20659).

    Because this function is mostly used to better resolve forward annotations, nothing is returned if the parent frame's
    code object is defined at the module level. In this case, the locals of the frame will be the same as the module
    globals where the class is defined (see `_namespace_utils.get_module_ns_of`). However, if you still want to fetch
    the module globals (e.g. when rebuilding a model, where the frame where the rebuild call is performed might contain
    members that you want to use for forward annotations evaluation), you can use the `force` parameter.

    Args:
        parent_depth: The depth at which to get the frame. Defaults to 2, meaning the parent frame where this function
            is called will be used.
        force: Whether to always return the frame locals, even if the frame's code object is defined at the module level.

    Returns:
        The locals of the namespace, or `None` if it was skipped as per the described logic.
    """
    frame = sys._getframe(parent_depth)

    if frame.f_code.co_name.startswith('<generic parameters of'):
        # As `parent_frame_namespace` is mostly called in `ModelMetaclass.__new__`,
        # the parent frame can be the annotation scope if the PEP 695 generic syntax is used.
        # (see https://docs.python.org/3/reference/executionmodel.html#annotation-scopes,
        # https://docs.python.org/3/reference/compound_stmts.html#generic-classes).
        # In this case, the code name is set to `<generic parameters of MyClass>`,
        # and we need to skip this frame as it is irrelevant.
        frame = cast(types.FrameType, frame.f_back)  # guaranteed to not be `None`

    # note, we don't copy frame.f_locals here (or during the last return call), because we don't expect the namespace to be
    # modified down the line if this becomes a problem, we could implement some sort of frozen mapping structure to enforce this.
    if force:
        return frame.f_locals

    # If either of the following conditions are true, the class is defined at the top module level.
    # To better understand why we need both of these checks, see
    # https://github.com/pydantic/pydantic/pull/10113#discussion_r1714981531.
    if frame.f_back is None or frame.f_code.co_name == '<module>':
        return None

    return frame.f_locals


def _type_convert(arg: Any) -> Any:
    """Convert `None` to `NoneType` and strings to `ForwardRef` instances.

    This is a backport of the private `typing._type_convert` function. When
    evaluating a type, `ForwardRef._evaluate` ends up being called, and is
    responsible for making this conversion. However, we still have to apply
    it for the first argument passed to our type evaluation functions, similarly
    to the `typing.get_type_hints` function.
    """
    if arg is None:
        return NoneType
    if isinstance(arg, str):
        # Like `typing.get_type_hints`, assume the arg can be in any context,
        # hence the proper `is_argument` and `is_class` args:
        return _make_forward_ref(arg, is_argument=False, is_class=True)
    return arg


def get_model_type_hints(
    obj: type[BaseModel],
    *,
    ns_resolver: NsResolver | None = None,
) -> dict[str, tuple[Any, bool]]:
    """Collect annotations from a Pydantic model class, including those from parent classes.

    Args:
        obj: The Pydantic model to inspect.
        ns_resolver: A namespace resolver instance to use. Defaults to an empty instance.

    Returns:
        A dictionary mapping annotation names to a two-tuple: the first element is the evaluated
        type or the original annotation if a `NameError` occurred, the second element is a boolean
        indicating if whether the evaluation succeeded.
    """
    hints: dict[str, Any] | dict[str, tuple[Any, bool]] = {}
    ns_resolver = ns_resolver or NsResolver()

    for base in reversed(obj.__mro__):
        ann: dict[str, Any] | None = base.__dict__.get('__annotations__')
        if not ann or isinstance(ann, types.GetSetDescriptorType):
            continue
        with ns_resolver.push(base):
            globalns, localns = ns_resolver.types_namespace
            for name, value in ann.items():
                if name.startswith('_'):
                    # For private attributes, we only need the annotation to detect the `ClassVar` special form.
                    # For this reason, we still try to evaluate it, but we also catch any possible exception (on
                    # top of the `NameError`s caught in `try_eval_type`) that could happen so that users are free
                    # to use any kind of forward annotation for private fields (e.g. circular imports, new typing
                    # syntax, etc).
                    try:
                        hints[name] = try_eval_type(value, globalns, localns)
                    except Exception:
                        hints[name] = (value, False)
                else:
                    hints[name] = try_eval_type(value, globalns, localns)
    return hints


def get_cls_type_hints(
    obj: type[Any],
    *,
    ns_resolver: NsResolver | None = None,
) -> dict[str, Any]:
    """Collect annotations from a class, including those from parent classes.

    Args:
        obj: The class to inspect.
        ns_resolver: A namespace resolver instance to use. Defaults to an empty instance.
    """
    hints: dict[str, Any] | dict[str, tuple[Any, bool]] = {}
    ns_resolver = ns_resolver or NsResolver()

    for base in reversed(obj.__mro__):
        ann: dict[str, Any] | None = base.__dict__.get('__annotations__')
        if not ann or isinstance(ann, types.GetSetDescriptorType):
            continue
        with ns_resolver.push(base):
            globalns, localns = ns_resolver.types_namespace
            for name, value in ann.items():
                hints[name] = eval_type(value, globalns, localns)
    return hints


def try_eval_type(
    value: Any,
    globalns: GlobalsNamespace | None = None,
    localns: MappingNamespace | None = None,
) -> tuple[Any, bool]:
    """Try evaluating the annotation using the provided namespaces.

    Args:
        value: The value to evaluate. If `None`, it will be replaced by `type[None]`. If an instance
            of `str`, it will be converted to a `ForwardRef`.
        localns: The global namespace to use during annotation evaluation.
        globalns: The local namespace to use during annotation evaluation.

    Returns:
        A two-tuple containing the possibly evaluated type and a boolean indicating
            whether the evaluation succeeded or not.
    """
    value = _type_convert(value)

    try:
        return eval_type_backport(value, globalns, localns), True
    except NameError:
        return value, False


def eval_type(
    value: Any,
    globalns: GlobalsNamespace | None = None,
    localns: MappingNamespace | None = None,
) -> Any:
    """Evaluate the annotation using the provided namespaces.

    Args:
        value: The value to evaluate. If `None`, it will be replaced by `type[None]`. If an instance
            of `str`, it will be converted to a `ForwardRef`.
        localns: The global namespace to use during annotation evaluation.
        globalns: The local namespace to use during annotation evaluation.
    """
    value = _type_convert(value)
    return eval_type_backport(value, globalns, localns)


@deprecated(
    '`eval_type_lenient` is deprecated, use `try_eval_type` instead.',
    category=None,
)
def eval_type_lenient(
    value: Any,
    globalns: GlobalsNamespace | None = None,
    localns: MappingNamespace | None = None,
) -> Any:
    ev, _ = try_eval_type(value, globalns, localns)
    return ev


def eval_type_backport(
    value: Any,
    globalns: GlobalsNamespace | None = None,
    localns: MappingNamespace | None = None,
    type_params: tuple[Any, ...] | None = None,
) -> Any:
    """An enhanced version of `typing._eval_type` which will fall back to using the `eval_type_backport`
    package if it's installed to let older Python versions use newer typing constructs.

    Specifically, this transforms `X | Y` into `typing.Union[X, Y]` and `list[X]` into `typing.List[X]`
    (as well as all the types made generic in PEP 585) if the original syntax is not supported in the
    current Python version.

    This function will also display a helpful error if the value passed fails to evaluate.
    """
    try:
        return _eval_type_backport(value, globalns, localns, type_params)
    except TypeError as e:
        if 'Unable to evaluate type annotation' in str(e):
            raise

        # If it is a `TypeError` and value isn't a `ForwardRef`, it would have failed during annotation definition.
        # Thus we assert here for type checking purposes:
        assert isinstance(value, typing.ForwardRef)

        message = f'Unable to evaluate type annotation {value.__forward_arg__!r}.'
        if sys.version_info >= (3, 11):
            e.add_note(message)
            raise
        else:
            raise TypeError(message) from e
    except RecursionError as e:
        # TODO ideally recursion errors should be checked in `eval_type` above, but `eval_type_backport`
        # is used directly in some places.
        message = (
            "If you made use of an implicit recursive type alias (e.g. `MyType = list['MyType']), "
            'consider using PEP 695 type aliases instead. For more details, refer to the documentation: '
            f'https://docs.pydantic.dev/{version_short()}/concepts/types/#named-recursive-types'
        )
        if sys.version_info >= (3, 11):
            e.add_note(message)
            raise
        else:
            raise RecursionError(f'{e.args[0]}\n{message}')


def _eval_type_backport(
    value: Any,
    globalns: GlobalsNamespace | None = None,
    localns: MappingNamespace | None = None,
    type_params: tuple[Any, ...] | None = None,
) -> Any:
    try:
        return _eval_type(value, globalns, localns, type_params)
    except TypeError as e:
        if not (isinstance(value, typing.ForwardRef) and is_backport_fixable_error(e)):
            raise

        try:
            from eval_type_backport import eval_type_backport
        except ImportError:
            raise TypeError(
                f'Unable to evaluate type annotation {value.__forward_arg__!r}. If you are making use '
                'of the new typing syntax (unions using `|` since Python 3.10 or builtins subscripting '
                'since Python 3.9), you should either replace the use of new syntax with the existing '
                '`typing` constructs or install the `eval_type_backport` package.'
            ) from e

        return eval_type_backport(
            value,
            globalns,
            localns,  # pyright: ignore[reportArgumentType], waiting on a new `eval_type_backport` release.
            try_default=False,
        )


def _eval_type(
    value: Any,
    globalns: GlobalsNamespace | None = None,
    localns: MappingNamespace | None = None,
    type_params: tuple[Any, ...] | None = None,
) -> Any:
    if sys.version_info >= (3, 13):
        return typing._eval_type(  # type: ignore
            value, globalns, localns, type_params=type_params
        )
    else:
        return typing._eval_type(  # type: ignore
            value, globalns, localns
        )


def is_backport_fixable_error(e: TypeError) -> bool:
    msg = str(e)

    return sys.version_info < (3, 10) and msg.startswith('unsupported operand type(s) for |: ')


def get_function_type_hints(
    function: Callable[..., Any],
    *,
    include_keys: set[str] | None = None,
    globalns: GlobalsNamespace | None = None,
    localns: MappingNamespace | None = None,
) -> dict[str, Any]:
    """Return type hints for a function.

    This is similar to the `typing.get_type_hints` function, with a few differences:
    - Support `functools.partial` by using the underlying `func` attribute.
    - Do not wrap type annotation of a parameter with `Optional` if it has a default value of `None`
      (related bug: https://github.com/python/cpython/issues/90353, only fixed in 3.11+).
    """
    try:
        if isinstance(function, partial):
            annotations = function.func.__annotations__
        else:
            annotations = function.__annotations__
    except AttributeError:
        # Some functions (e.g. builtins) don't have annotations:
        return {}

    if globalns is None:
        globalns = get_module_ns_of(function)
    type_params: tuple[Any, ...] | None = None
    if localns is None:
        # If localns was specified, it is assumed to already contain type params. This is because
        # Pydantic has more advanced logic to do so (see `_namespace_utils.ns_for_function`).
        type_params = getattr(function, '__type_params__', ())

    type_hints = {}
    for name, value in annotations.items():
        if include_keys is not None and name not in include_keys:
            continue
        if value is None:
            value = NoneType
        elif isinstance(value, str):
            value = _make_forward_ref(value)

        type_hints[name] = eval_type_backport(value, globalns, localns, type_params)

    return type_hints


if sys.version_info < (3, 9, 8) or (3, 10) <= sys.version_info < (3, 10, 1):

    def _make_forward_ref(
        arg: Any,
        is_argument: bool = True,
        *,
        is_class: bool = False,
    ) -> typing.ForwardRef:
        """Wrapper for ForwardRef that accounts for the `is_class` argument missing in older versions.
        The `module` argument is omitted as it breaks <3.9.8, =3.10.0 and isn't used in the calls below.

        See https://github.com/python/cpython/pull/28560 for some background.
        The backport happened on 3.9.8, see:
        https://github.com/pydantic/pydantic/discussions/6244#discussioncomment-6275458,
        and on 3.10.1 for the 3.10 branch, see:
        https://github.com/pydantic/pydantic/issues/6912

        Implemented as EAFP with memory.
        """
        return typing.ForwardRef(arg, is_argument)

else:
    _make_forward_ref = typing.ForwardRef


if sys.version_info >= (3, 10):
    get_type_hints = typing.get_type_hints

else:
    """
    For older versions of python, we have a custom implementation of `get_type_hints` which is a close as possible to
    the implementation in CPython 3.10.8.
    """

    @typing.no_type_check
    def get_type_hints(  # noqa: C901
        obj: Any,
        globalns: dict[str, Any] | None = None,
        localns: dict[str, Any] | None = None,
        include_extras: bool = False,
    ) -> dict[str, Any]:  # pragma: no cover
        """Taken verbatim from python 3.10.8 unchanged, except:
        * type annotations of the function definition above.
        * prefixing `typing.` where appropriate
        * Use `_make_forward_ref` instead of `typing.ForwardRef` to handle the `is_class` argument.

        https://github.com/python/cpython/blob/aaaf5174241496afca7ce4d4584570190ff972fe/Lib/typing.py#L1773-L1875

        DO NOT CHANGE THIS METHOD UNLESS ABSOLUTELY NECESSARY.
        ======================================================

        Return type hints for an object.

        This is often the same as obj.__annotations__, but it handles
        forward references encoded as string literals, adds Optional[t] if a
        default value equal to None is set and recursively replaces all
        'Annotated[T, ...]' with 'T' (unless 'include_extras=True').

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
          to have globals, an empty dictionary is used.  For classes, the search
          order is globals first then locals.

        - If one dict argument is passed, it is used for both globals and
          locals.

        - If two dict arguments are passed, they specify globals and
          locals, respectively.
        """
        if getattr(obj, '__no_type_check__', None):
            return {}
        # Classes require a special treatment.
        if isinstance(obj, type):
            hints = {}
            for base in reversed(obj.__mro__):
                if globalns is None:
                    base_globals = getattr(sys.modules.get(base.__module__, None), '__dict__', {})
                else:
                    base_globals = globalns
                ann = base.__dict__.get('__annotations__', {})
                if isinstance(ann, types.GetSetDescriptorType):
                    ann = {}
                base_locals = dict(vars(base)) if localns is None else localns
                if localns is None and globalns is None:
                    # This is surprising, but required.  Before Python 3.10,
                    # get_type_hints only evaluated the globalns of
                    # a class.  To maintain backwards compatibility, we reverse
                    # the globalns and localns order so that eval() looks into
                    # *base_globals* first rather than *base_locals*.
                    # This only affects ForwardRefs.
                    base_globals, base_locals = base_locals, base_globals
                for name, value in ann.items():
                    if value is None:
                        value = type(None)
                    if isinstance(value, str):
                        value = _make_forward_ref(value, is_argument=False, is_class=True)

                    value = eval_type_backport(value, base_globals, base_locals)
                    hints[name] = value
            if not include_extras and hasattr(typing, '_strip_annotations'):
                return {
                    k: typing._strip_annotations(t)  # type: ignore
                    for k, t in hints.items()
                }
            else:
                return hints

        if globalns is None:
            if isinstance(obj, types.ModuleType):
                globalns = obj.__dict__
            else:
                nsobj = obj
                # Find globalns for the unwrapped object.
                while hasattr(nsobj, '__wrapped__'):
                    nsobj = nsobj.__wrapped__
                globalns = getattr(nsobj, '__globals__', {})
            if localns is None:
                localns = globalns
        elif localns is None:
            localns = globalns
        hints = getattr(obj, '__annotations__', None)
        if hints is None:
            # Return empty annotations for something that _could_ have them.
            if isinstance(obj, typing._allowed_types):  # type: ignore
                return {}
            else:
                raise TypeError(f'{obj!r} is not a module, class, method, or function.')
        defaults = typing._get_defaults(obj)  # type: ignore
        hints = dict(hints)
        for name, value in hints.items():
            if value is None:
                value = type(None)
            if isinstance(value, str):
                # class-level forward refs were handled above, this must be either
                # a module-level annotation or a function argument annotation

                value = _make_forward_ref(
                    value,
                    is_argument=not isinstance(obj, types.ModuleType),
                    is_class=False,
                )
            value = eval_type_backport(value, globalns, localns)
            if name in defaults and defaults[name] is None:
                value = typing.Optional[value]
            hints[name] = value
        return hints if include_extras else {k: typing._strip_annotations(t) for k, t in hints.items()}  # type: ignore

# === NexusCore/openenv\Lib\site-packages\matplotlib\streamplot.py ===
"""
Streamline plotting for 2D vector fields.

"""

import numpy as np

import matplotlib as mpl
from matplotlib import _api, cm, patches
import matplotlib.colors as mcolors
import matplotlib.collections as mcollections
import matplotlib.lines as mlines


__all__ = ['streamplot']


def streamplot(axes, x, y, u, v, density=1, linewidth=None, color=None,
               cmap=None, norm=None, arrowsize=1, arrowstyle='-|>',
               minlength=0.1, transform=None, zorder=None, start_points=None,
               maxlength=4.0, integration_direction='both',
               broken_streamlines=True):
    """
    Draw streamlines of a vector flow.

    Parameters
    ----------
    x, y : 1D/2D arrays
        Evenly spaced strictly increasing arrays to make a grid.  If 2D, all
        rows of *x* must be equal and all columns of *y* must be equal; i.e.,
        they must be as if generated by ``np.meshgrid(x_1d, y_1d)``.
    u, v : 2D arrays
        *x* and *y*-velocities. The number of rows and columns must match
        the length of *y* and *x*, respectively.
    density : float or (float, float)
        Controls the closeness of streamlines. When ``density = 1``, the domain
        is divided into a 30x30 grid. *density* linearly scales this grid.
        Each cell in the grid can have, at most, one traversing streamline.
        For different densities in each direction, use a tuple
        (density_x, density_y).
    linewidth : float or 2D array
        The width of the streamlines. With a 2D array the line width can be
        varied across the grid. The array must have the same shape as *u*
        and *v*.
    color : :mpltype:`color` or 2D array
        The streamline color. If given an array, its values are converted to
        colors using *cmap* and *norm*.  The array must have the same shape
        as *u* and *v*.
    cmap, norm
        Data normalization and colormapping parameters for *color*; only used
        if *color* is an array of floats. See `~.Axes.imshow` for a detailed
        description.
    arrowsize : float
        Scaling factor for the arrow size.
    arrowstyle : str
        Arrow style specification.
        See `~matplotlib.patches.FancyArrowPatch`.
    minlength : float
        Minimum length of streamline in axes coordinates.
    start_points : (N, 2) array
        Coordinates of starting points for the streamlines in data coordinates
        (the same coordinates as the *x* and *y* arrays).
    zorder : float
        The zorder of the streamlines and arrows.
        Artists with lower zorder values are drawn first.
    maxlength : float
        Maximum length of streamline in axes coordinates.
    integration_direction : {'forward', 'backward', 'both'}, default: 'both'
        Integrate the streamline in forward, backward or both directions.
    data : indexable object, optional
        DATA_PARAMETER_PLACEHOLDER
    broken_streamlines : boolean, default: True
        If False, forces streamlines to continue until they
        leave the plot domain.  If True, they may be terminated if they
        come too close to another streamline.

    Returns
    -------
    StreamplotSet
        Container object with attributes

        - ``lines``: `.LineCollection` of streamlines

        - ``arrows``: `.PatchCollection` containing `.FancyArrowPatch`
          objects representing the arrows half-way along streamlines.

        This container will probably change in the future to allow changes
        to the colormap, alpha, etc. for both lines and arrows, but these
        changes should be backward compatible.
    """
    grid = Grid(x, y)
    mask = StreamMask(density)
    dmap = DomainMap(grid, mask)

    if zorder is None:
        zorder = mlines.Line2D.zorder

    # default to data coordinates
    if transform is None:
        transform = axes.transData

    if color is None:
        color = axes._get_lines.get_next_color()

    if linewidth is None:
        linewidth = mpl.rcParams['lines.linewidth']

    line_kw = {}
    arrow_kw = dict(arrowstyle=arrowstyle, mutation_scale=10 * arrowsize)

    _api.check_in_list(['both', 'forward', 'backward'],
                       integration_direction=integration_direction)

    if integration_direction == 'both':
        maxlength /= 2.

    use_multicolor_lines = isinstance(color, np.ndarray)
    if use_multicolor_lines:
        if color.shape != grid.shape:
            raise ValueError("If 'color' is given, it must match the shape of "
                             "the (x, y) grid")
        line_colors = [[]]  # Empty entry allows concatenation of zero arrays.
        color = np.ma.masked_invalid(color)
    else:
        line_kw['color'] = color
        arrow_kw['color'] = color

    if isinstance(linewidth, np.ndarray):
        if linewidth.shape != grid.shape:
            raise ValueError("If 'linewidth' is given, it must match the "
                             "shape of the (x, y) grid")
        line_kw['linewidth'] = []
    else:
        line_kw['linewidth'] = linewidth
        arrow_kw['linewidth'] = linewidth

    line_kw['zorder'] = zorder
    arrow_kw['zorder'] = zorder

    # Sanity checks.
    if u.shape != grid.shape or v.shape != grid.shape:
        raise ValueError("'u' and 'v' must match the shape of the (x, y) grid")

    u = np.ma.masked_invalid(u)
    v = np.ma.masked_invalid(v)

    integrate = _get_integrator(u, v, dmap, minlength, maxlength,
                                integration_direction)

    trajectories = []
    if start_points is None:
        for xm, ym in _gen_starting_points(mask.shape):
            if mask[ym, xm] == 0:
                xg, yg = dmap.mask2grid(xm, ym)
                t = integrate(xg, yg, broken_streamlines)
                if t is not None:
                    trajectories.append(t)
    else:
        sp2 = np.asanyarray(start_points, dtype=float).copy()

        # Check if start_points are outside the data boundaries
        for xs, ys in sp2:
            if not (grid.x_origin <= xs <= grid.x_origin + grid.width and
                    grid.y_origin <= ys <= grid.y_origin + grid.height):
                raise ValueError(f"Starting point ({xs}, {ys}) outside of "
                                 "data boundaries")

        # Convert start_points from data to array coords
        # Shift the seed points from the bottom left of the data so that
        # data2grid works properly.
        sp2[:, 0] -= grid.x_origin
        sp2[:, 1] -= grid.y_origin

        for xs, ys in sp2:
            xg, yg = dmap.data2grid(xs, ys)
            # Floating point issues can cause xg, yg to be slightly out of
            # bounds for xs, ys on the upper boundaries. Because we have
            # already checked that the starting points are within the original
            # grid, clip the xg, yg to the grid to work around this issue
            xg = np.clip(xg, 0, grid.nx - 1)
            yg = np.clip(yg, 0, grid.ny - 1)

            t = integrate(xg, yg, broken_streamlines)
            if t is not None:
                trajectories.append(t)

    if use_multicolor_lines:
        if norm is None:
            norm = mcolors.Normalize(color.min(), color.max())
        cmap = cm._ensure_cmap(cmap)

    streamlines = []
    arrows = []
    for t in trajectories:
        tgx, tgy = t.T
        # Rescale from grid-coordinates to data-coordinates.
        tx, ty = dmap.grid2data(tgx, tgy)
        tx += grid.x_origin
        ty += grid.y_origin

        # Create multiple tiny segments if varying width or color is given
        if isinstance(linewidth, np.ndarray) or use_multicolor_lines:
            points = np.transpose([tx, ty]).reshape(-1, 1, 2)
            streamlines.extend(np.hstack([points[:-1], points[1:]]))
        else:
            points = np.transpose([tx, ty])
            streamlines.append(points)

        # Add arrows halfway along each trajectory.
        s = np.cumsum(np.hypot(np.diff(tx), np.diff(ty)))
        n = np.searchsorted(s, s[-1] / 2.)
        arrow_tail = (tx[n], ty[n])
        arrow_head = (np.mean(tx[n:n + 2]), np.mean(ty[n:n + 2]))

        if isinstance(linewidth, np.ndarray):
            line_widths = interpgrid(linewidth, tgx, tgy)[:-1]
            line_kw['linewidth'].extend(line_widths)
            arrow_kw['linewidth'] = line_widths[n]

        if use_multicolor_lines:
            color_values = interpgrid(color, tgx, tgy)[:-1]
            line_colors.append(color_values)
            arrow_kw['color'] = cmap(norm(color_values[n]))

        p = patches.FancyArrowPatch(
            arrow_tail, arrow_head, transform=transform, **arrow_kw)
        arrows.append(p)

    lc = mcollections.LineCollection(
        streamlines, transform=transform, **line_kw)
    lc.sticky_edges.x[:] = [grid.x_origin, grid.x_origin + grid.width]
    lc.sticky_edges.y[:] = [grid.y_origin, grid.y_origin + grid.height]
    if use_multicolor_lines:
        lc.set_array(np.ma.hstack(line_colors))
        lc.set_cmap(cmap)
        lc.set_norm(norm)
    axes.add_collection(lc)

    ac = mcollections.PatchCollection(arrows)
    # Adding the collection itself is broken; see #2341.
    for p in arrows:
        axes.add_patch(p)

    axes.autoscale_view()
    stream_container = StreamplotSet(lc, ac)
    return stream_container


class StreamplotSet:

    def __init__(self, lines, arrows):
        self.lines = lines
        self.arrows = arrows


# Coordinate definitions
# ========================

class DomainMap:
    """
    Map representing different coordinate systems.

    Coordinate definitions:

    * axes-coordinates goes from 0 to 1 in the domain.
    * data-coordinates are specified by the input x-y coordinates.
    * grid-coordinates goes from 0 to N and 0 to M for an N x M grid,
      where N and M match the shape of the input data.
    * mask-coordinates goes from 0 to N and 0 to M for an N x M mask,
      where N and M are user-specified to control the density of streamlines.

    This class also has methods for adding trajectories to the StreamMask.
    Before adding a trajectory, run `start_trajectory` to keep track of regions
    crossed by a given trajectory. Later, if you decide the trajectory is bad
    (e.g., if the trajectory is very short) just call `undo_trajectory`.
    """

    def __init__(self, grid, mask):
        self.grid = grid
        self.mask = mask
        # Constants for conversion between grid- and mask-coordinates
        self.x_grid2mask = (mask.nx - 1) / (grid.nx - 1)
        self.y_grid2mask = (mask.ny - 1) / (grid.ny - 1)

        self.x_mask2grid = 1. / self.x_grid2mask
        self.y_mask2grid = 1. / self.y_grid2mask

        self.x_data2grid = 1. / grid.dx
        self.y_data2grid = 1. / grid.dy

    def grid2mask(self, xi, yi):
        """Return nearest space in mask-coords from given grid-coords."""
        return round(xi * self.x_grid2mask), round(yi * self.y_grid2mask)

    def mask2grid(self, xm, ym):
        return xm * self.x_mask2grid, ym * self.y_mask2grid

    def data2grid(self, xd, yd):
        return xd * self.x_data2grid, yd * self.y_data2grid

    def grid2data(self, xg, yg):
        return xg / self.x_data2grid, yg / self.y_data2grid

    def start_trajectory(self, xg, yg, broken_streamlines=True):
        xm, ym = self.grid2mask(xg, yg)
        self.mask._start_trajectory(xm, ym, broken_streamlines)

    def reset_start_point(self, xg, yg):
        xm, ym = self.grid2mask(xg, yg)
        self.mask._current_xy = (xm, ym)

    def update_trajectory(self, xg, yg, broken_streamlines=True):
        if not self.grid.within_grid(xg, yg):
            raise InvalidIndexError
        xm, ym = self.grid2mask(xg, yg)
        self.mask._update_trajectory(xm, ym, broken_streamlines)

    def undo_trajectory(self):
        self.mask._undo_trajectory()


class Grid:
    """Grid of data."""
    def __init__(self, x, y):

        if np.ndim(x) == 1:
            pass
        elif np.ndim(x) == 2:
            x_row = x[0]
            if not np.allclose(x_row, x):
                raise ValueError("The rows of 'x' must be equal")
            x = x_row
        else:
            raise ValueError("'x' can have at maximum 2 dimensions")

        if np.ndim(y) == 1:
            pass
        elif np.ndim(y) == 2:
            yt = np.transpose(y)  # Also works for nested lists.
            y_col = yt[0]
            if not np.allclose(y_col, yt):
                raise ValueError("The columns of 'y' must be equal")
            y = y_col
        else:
            raise ValueError("'y' can have at maximum 2 dimensions")

        if not (np.diff(x) > 0).all():
            raise ValueError("'x' must be strictly increasing")
        if not (np.diff(y) > 0).all():
            raise ValueError("'y' must be strictly increasing")

        self.nx = len(x)
        self.ny = len(y)

        self.dx = x[1] - x[0]
        self.dy = y[1] - y[0]

        self.x_origin = x[0]
        self.y_origin = y[0]

        self.width = x[-1] - x[0]
        self.height = y[-1] - y[0]

        if not np.allclose(np.diff(x), self.width / (self.nx - 1)):
            raise ValueError("'x' values must be equally spaced")
        if not np.allclose(np.diff(y), self.height / (self.ny - 1)):
            raise ValueError("'y' values must be equally spaced")

    @property
    def shape(self):
        return self.ny, self.nx

    def within_grid(self, xi, yi):
        """Return whether (*xi*, *yi*) is a valid index of the grid."""
        # Note that xi/yi can be floats; so, for example, we can't simply check
        # `xi < self.nx` since *xi* can be `self.nx - 1 < xi < self.nx`
        return 0 <= xi <= self.nx - 1 and 0 <= yi <= self.ny - 1


class StreamMask:
    """
    Mask to keep track of discrete regions crossed by streamlines.

    The resolution of this grid determines the approximate spacing between
    trajectories. Streamlines are only allowed to pass through zeroed cells:
    When a streamline enters a cell, that cell is set to 1, and no new
    streamlines are allowed to enter.
    """

    def __init__(self, density):
        try:
            self.nx, self.ny = (30 * np.broadcast_to(density, 2)).astype(int)
        except ValueError as err:
            raise ValueError("'density' must be a scalar or be of length "
                             "2") from err
        if self.nx < 0 or self.ny < 0:
            raise ValueError("'density' must be positive")
        self._mask = np.zeros((self.ny, self.nx))
        self.shape = self._mask.shape

        self._current_xy = None

    def __getitem__(self, args):
        return self._mask[args]

    def _start_trajectory(self, xm, ym, broken_streamlines=True):
        """Start recording streamline trajectory"""
        self._traj = []
        self._update_trajectory(xm, ym, broken_streamlines)

    def _undo_trajectory(self):
        """Remove current trajectory from mask"""
        for t in self._traj:
            self._mask[t] = 0

    def _update_trajectory(self, xm, ym, broken_streamlines=True):
        """
        Update current trajectory position in mask.

        If the new position has already been filled, raise `InvalidIndexError`.
        """
        if self._current_xy != (xm, ym):
            if self[ym, xm] == 0:
                self._traj.append((ym, xm))
                self._mask[ym, xm] = 1
                self._current_xy = (xm, ym)
            else:
                if broken_streamlines:
                    raise InvalidIndexError
                else:
                    pass


class InvalidIndexError(Exception):
    pass


class TerminateTrajectory(Exception):
    pass


# Integrator definitions
# =======================

def _get_integrator(u, v, dmap, minlength, maxlength, integration_direction):

    # rescale velocity onto grid-coordinates for integrations.
    u, v = dmap.data2grid(u, v)

    # speed (path length) will be in axes-coordinates
    u_ax = u / (dmap.grid.nx - 1)
    v_ax = v / (dmap.grid.ny - 1)
    speed = np.ma.sqrt(u_ax ** 2 + v_ax ** 2)

    def forward_time(xi, yi):
        if not dmap.grid.within_grid(xi, yi):
            raise OutOfBounds
        ds_dt = interpgrid(speed, xi, yi)
        if ds_dt == 0:
            raise TerminateTrajectory()
        dt_ds = 1. / ds_dt
        ui = interpgrid(u, xi, yi)
        vi = interpgrid(v, xi, yi)
        return ui * dt_ds, vi * dt_ds

    def backward_time(xi, yi):
        dxi, dyi = forward_time(xi, yi)
        return -dxi, -dyi

    def integrate(x0, y0, broken_streamlines=True):
        """
        Return x, y grid-coordinates of trajectory based on starting point.

        Integrate both forward and backward in time from starting point in
        grid coordinates.

        Integration is terminated when a trajectory reaches a domain boundary
        or when it crosses into an already occupied cell in the StreamMask. The
        resulting trajectory is None if it is shorter than `minlength`.
        """

        stotal, xy_traj = 0., []

        try:
            dmap.start_trajectory(x0, y0, broken_streamlines)
        except InvalidIndexError:
            return None
        if integration_direction in ['both', 'backward']:
            s, xyt = _integrate_rk12(x0, y0, dmap, backward_time, maxlength,
                                     broken_streamlines)
            stotal += s
            xy_traj += xyt[::-1]

        if integration_direction in ['both', 'forward']:
            dmap.reset_start_point(x0, y0)
            s, xyt = _integrate_rk12(x0, y0, dmap, forward_time, maxlength,
                                     broken_streamlines)
            stotal += s
            xy_traj += xyt[1:]

        if stotal > minlength:
            return np.broadcast_arrays(xy_traj, np.empty((1, 2)))[0]
        else:  # reject short trajectories
            dmap.undo_trajectory()
            return None

    return integrate


class OutOfBounds(IndexError):
    pass


def _integrate_rk12(x0, y0, dmap, f, maxlength, broken_streamlines=True):
    """
    2nd-order Runge-Kutta algorithm with adaptive step size.

    This method is also referred to as the improved Euler's method, or Heun's
    method. This method is favored over higher-order methods because:

    1. To get decent looking trajectories and to sample every mask cell
       on the trajectory we need a small timestep, so a lower order
       solver doesn't hurt us unless the data is *very* high resolution.
       In fact, for cases where the user inputs
       data smaller or of similar grid size to the mask grid, the higher
       order corrections are negligible because of the very fast linear
       interpolation used in `interpgrid`.

    2. For high resolution input data (i.e. beyond the mask
       resolution), we must reduce the timestep. Therefore, an adaptive
       timestep is more suited to the problem as this would be very hard
       to judge automatically otherwise.

    This integrator is about 1.5 - 2x as fast as RK4 and RK45 solvers (using
    similar Python implementations) in most setups.
    """
    # This error is below that needed to match the RK4 integrator. It
    # is set for visual reasons -- too low and corners start
    # appearing ugly and jagged. Can be tuned.
    maxerror = 0.003

    # This limit is important (for all integrators) to avoid the
    # trajectory skipping some mask cells. We could relax this
    # condition if we use the code which is commented out below to
    # increment the location gradually. However, due to the efficient
    # nature of the interpolation, this doesn't boost speed by much
    # for quite a bit of complexity.
    maxds = min(1. / dmap.mask.nx, 1. / dmap.mask.ny, 0.1)

    ds = maxds
    stotal = 0
    xi = x0
    yi = y0
    xyf_traj = []

    while True:
        try:
            if dmap.grid.within_grid(xi, yi):
                xyf_traj.append((xi, yi))
            else:
                raise OutOfBounds

            # Compute the two intermediate gradients.
            # f should raise OutOfBounds if the locations given are
            # outside the grid.
            k1x, k1y = f(xi, yi)
            k2x, k2y = f(xi + ds * k1x, yi + ds * k1y)

        except OutOfBounds:
            # Out of the domain during this step.
            # Take an Euler step to the boundary to improve neatness
            # unless the trajectory is currently empty.
            if xyf_traj:
                ds, xyf_traj = _euler_step(xyf_traj, dmap, f)
                stotal += ds
            break
        except TerminateTrajectory:
            break

        dx1 = ds * k1x
        dy1 = ds * k1y
        dx2 = ds * 0.5 * (k1x + k2x)
        dy2 = ds * 0.5 * (k1y + k2y)

        ny, nx = dmap.grid.shape
        # Error is normalized to the axes coordinates
        error = np.hypot((dx2 - dx1) / (nx - 1), (dy2 - dy1) / (ny - 1))

        # Only save step if within error tolerance
        if error < maxerror:
            xi += dx2
            yi += dy2
            try:
                dmap.update_trajectory(xi, yi, broken_streamlines)
            except InvalidIndexError:
                break
            if stotal + ds > maxlength:
                break
            stotal += ds

        # recalculate stepsize based on step error
        if error == 0:
            ds = maxds
        else:
            ds = min(maxds, 0.85 * ds * (maxerror / error) ** 0.5)

    return stotal, xyf_traj


def _euler_step(xyf_traj, dmap, f):
    """Simple Euler integration step that extends streamline to boundary."""
    ny, nx = dmap.grid.shape
    xi, yi = xyf_traj[-1]
    cx, cy = f(xi, yi)
    if cx == 0:
        dsx = np.inf
    elif cx < 0:
        dsx = xi / -cx
    else:
        dsx = (nx - 1 - xi) / cx
    if cy == 0:
        dsy = np.inf
    elif cy < 0:
        dsy = yi / -cy
    else:
        dsy = (ny - 1 - yi) / cy
    ds = min(dsx, dsy)
    xyf_traj.append((xi + cx * ds, yi + cy * ds))
    return ds, xyf_traj


# Utility functions
# ========================

def interpgrid(a, xi, yi):
    """Fast 2D, linear interpolation on an integer grid"""

    Ny, Nx = np.shape(a)
    if isinstance(xi, np.ndarray):
        x = xi.astype(int)
        y = yi.astype(int)
        # Check that xn, yn don't exceed max index
        xn = np.clip(x + 1, 0, Nx - 1)
        yn = np.clip(y + 1, 0, Ny - 1)
    else:
        x = int(xi)
        y = int(yi)
        # conditional is faster than clipping for integers
        if x == (Nx - 1):
            xn = x
        else:
            xn = x + 1
        if y == (Ny - 1):
            yn = y
        else:
            yn = y + 1

    a00 = a[y, x]
    a01 = a[y, xn]
    a10 = a[yn, x]
    a11 = a[yn, xn]
    xt = xi - x
    yt = yi - y
    a0 = a00 * (1 - xt) + a01 * xt
    a1 = a10 * (1 - xt) + a11 * xt
    ai = a0 * (1 - yt) + a1 * yt

    if not isinstance(xi, np.ndarray):
        if np.ma.is_masked(ai):
            raise TerminateTrajectory

    return ai


def _gen_starting_points(shape):
    """
    Yield starting points for streamlines.

    Trying points on the boundary first gives higher quality streamlines.
    This algorithm starts with a point on the mask corner and spirals inward.
    This algorithm is inefficient, but fast compared to rest of streamplot.
    """
    ny, nx = shape
    xfirst = 0
    yfirst = 1
    xlast = nx - 1
    ylast = ny - 1
    x, y = 0, 0
    direction = 'right'
    for i in range(nx * ny):
        yield x, y

        if direction == 'right':
            x += 1
            if x >= xlast:
                xlast -= 1
                direction = 'up'
        elif direction == 'up':
            y += 1
            if y >= ylast:
                ylast -= 1
                direction = 'left'
        elif direction == 'left':
            x -= 1
            if x <= xfirst:
                xfirst += 1
                direction = 'down'
        elif direction == 'down':
            y -= 1
            if y <= yfirst:
                yfirst += 1
                direction = 'right'

# === NexusCore/openenv\Lib\site-packages\nltk\inference\tableau.py ===
# Natural Language Toolkit: First-Order Tableau Theorem Prover
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Module for a tableau-based First Order theorem prover.
"""

from nltk.inference.api import BaseProverCommand, Prover
from nltk.internals import Counter
from nltk.sem.logic import (
    AbstractVariableExpression,
    AllExpression,
    AndExpression,
    ApplicationExpression,
    EqualityExpression,
    ExistsExpression,
    Expression,
    FunctionVariableExpression,
    IffExpression,
    ImpExpression,
    LambdaExpression,
    NegatedExpression,
    OrExpression,
    Variable,
    VariableExpression,
    unique_variable,
)

_counter = Counter()


class ProverParseError(Exception):
    pass


class TableauProver(Prover):
    _assume_false = False

    def _prove(self, goal=None, assumptions=None, verbose=False):
        if not assumptions:
            assumptions = []

        result = None
        try:
            agenda = Agenda()
            if goal:
                agenda.put(-goal)
            agenda.put_all(assumptions)
            debugger = Debug(verbose)
            result = self._attempt_proof(agenda, set(), set(), debugger)
        except RuntimeError as e:
            if self._assume_false and str(e).startswith(
                "maximum recursion depth exceeded"
            ):
                result = False
            else:
                if verbose:
                    print(e)
                else:
                    raise e
        return (result, "\n".join(debugger.lines))

    def _attempt_proof(self, agenda, accessible_vars, atoms, debug):
        (current, context), category = agenda.pop_first()

        # if there's nothing left in the agenda, and we haven't closed the path
        if not current:
            debug.line("AGENDA EMPTY")
            return False

        proof_method = {
            Categories.ATOM: self._attempt_proof_atom,
            Categories.PROP: self._attempt_proof_prop,
            Categories.N_ATOM: self._attempt_proof_n_atom,
            Categories.N_PROP: self._attempt_proof_n_prop,
            Categories.APP: self._attempt_proof_app,
            Categories.N_APP: self._attempt_proof_n_app,
            Categories.N_EQ: self._attempt_proof_n_eq,
            Categories.D_NEG: self._attempt_proof_d_neg,
            Categories.N_ALL: self._attempt_proof_n_all,
            Categories.N_EXISTS: self._attempt_proof_n_some,
            Categories.AND: self._attempt_proof_and,
            Categories.N_OR: self._attempt_proof_n_or,
            Categories.N_IMP: self._attempt_proof_n_imp,
            Categories.OR: self._attempt_proof_or,
            Categories.IMP: self._attempt_proof_imp,
            Categories.N_AND: self._attempt_proof_n_and,
            Categories.IFF: self._attempt_proof_iff,
            Categories.N_IFF: self._attempt_proof_n_iff,
            Categories.EQ: self._attempt_proof_eq,
            Categories.EXISTS: self._attempt_proof_some,
            Categories.ALL: self._attempt_proof_all,
        }[category]

        debug.line((current, context))
        return proof_method(current, context, agenda, accessible_vars, atoms, debug)

    def _attempt_proof_atom(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        # Check if the branch is closed.  Return 'True' if it is
        if (current, True) in atoms:
            debug.line("CLOSED", 1)
            return True

        if context:
            if isinstance(context.term, NegatedExpression):
                current = current.negate()
            agenda.put(context(current).simplify())
            return self._attempt_proof(agenda, accessible_vars, atoms, debug + 1)
        else:
            # mark all AllExpressions as 'not exhausted' into the agenda since we are (potentially) adding new accessible vars
            agenda.mark_alls_fresh()
            return self._attempt_proof(
                agenda,
                accessible_vars | set(current.args),
                atoms | {(current, False)},
                debug + 1,
            )

    def _attempt_proof_n_atom(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        # Check if the branch is closed.  Return 'True' if it is
        if (current.term, False) in atoms:
            debug.line("CLOSED", 1)
            return True

        if context:
            if isinstance(context.term, NegatedExpression):
                current = current.negate()
            agenda.put(context(current).simplify())
            return self._attempt_proof(agenda, accessible_vars, atoms, debug + 1)
        else:
            # mark all AllExpressions as 'not exhausted' into the agenda since we are (potentially) adding new accessible vars
            agenda.mark_alls_fresh()
            return self._attempt_proof(
                agenda,
                accessible_vars | set(current.term.args),
                atoms | {(current.term, True)},
                debug + 1,
            )

    def _attempt_proof_prop(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        # Check if the branch is closed.  Return 'True' if it is
        if (current, True) in atoms:
            debug.line("CLOSED", 1)
            return True

        # mark all AllExpressions as 'not exhausted' into the agenda since we are (potentially) adding new accessible vars
        agenda.mark_alls_fresh()
        return self._attempt_proof(
            agenda, accessible_vars, atoms | {(current, False)}, debug + 1
        )

    def _attempt_proof_n_prop(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        # Check if the branch is closed.  Return 'True' if it is
        if (current.term, False) in atoms:
            debug.line("CLOSED", 1)
            return True

        # mark all AllExpressions as 'not exhausted' into the agenda since we are (potentially) adding new accessible vars
        agenda.mark_alls_fresh()
        return self._attempt_proof(
            agenda, accessible_vars, atoms | {(current.term, True)}, debug + 1
        )

    def _attempt_proof_app(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        f, args = current.uncurry()
        for i, arg in enumerate(args):
            if not TableauProver.is_atom(arg):
                ctx = f
                nv = Variable("X%s" % _counter.get())
                for j, a in enumerate(args):
                    ctx = ctx(VariableExpression(nv)) if i == j else ctx(a)
                if context:
                    ctx = context(ctx).simplify()
                ctx = LambdaExpression(nv, ctx)
                agenda.put(arg, ctx)
                return self._attempt_proof(agenda, accessible_vars, atoms, debug + 1)
        raise Exception("If this method is called, there must be a non-atomic argument")

    def _attempt_proof_n_app(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        f, args = current.term.uncurry()
        for i, arg in enumerate(args):
            if not TableauProver.is_atom(arg):
                ctx = f
                nv = Variable("X%s" % _counter.get())
                for j, a in enumerate(args):
                    ctx = ctx(VariableExpression(nv)) if i == j else ctx(a)
                if context:
                    # combine new context with existing
                    ctx = context(ctx).simplify()
                ctx = LambdaExpression(nv, -ctx)
                agenda.put(-arg, ctx)
                return self._attempt_proof(agenda, accessible_vars, atoms, debug + 1)
        raise Exception("If this method is called, there must be a non-atomic argument")

    def _attempt_proof_n_eq(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        ###########################################################################
        # Since 'current' is of type '~(a=b)', the path is closed if 'a' == 'b'
        ###########################################################################
        if current.term.first == current.term.second:
            debug.line("CLOSED", 1)
            return True

        agenda[Categories.N_EQ].add((current, context))
        current._exhausted = True
        return self._attempt_proof(
            agenda,
            accessible_vars | {current.term.first, current.term.second},
            atoms,
            debug + 1,
        )

    def _attempt_proof_d_neg(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        agenda.put(current.term.term, context)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug + 1)

    def _attempt_proof_n_all(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        agenda[Categories.EXISTS].add(
            (ExistsExpression(current.term.variable, -current.term.term), context)
        )
        return self._attempt_proof(agenda, accessible_vars, atoms, debug + 1)

    def _attempt_proof_n_some(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        agenda[Categories.ALL].add(
            (AllExpression(current.term.variable, -current.term.term), context)
        )
        return self._attempt_proof(agenda, accessible_vars, atoms, debug + 1)

    def _attempt_proof_and(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        agenda.put(current.first, context)
        agenda.put(current.second, context)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug + 1)

    def _attempt_proof_n_or(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        agenda.put(-current.term.first, context)
        agenda.put(-current.term.second, context)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug + 1)

    def _attempt_proof_n_imp(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        agenda.put(current.term.first, context)
        agenda.put(-current.term.second, context)
        return self._attempt_proof(agenda, accessible_vars, atoms, debug + 1)

    def _attempt_proof_or(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        new_agenda = agenda.clone()
        agenda.put(current.first, context)
        new_agenda.put(current.second, context)
        return self._attempt_proof(
            agenda, accessible_vars, atoms, debug + 1
        ) and self._attempt_proof(new_agenda, accessible_vars, atoms, debug + 1)

    def _attempt_proof_imp(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        new_agenda = agenda.clone()
        agenda.put(-current.first, context)
        new_agenda.put(current.second, context)
        return self._attempt_proof(
            agenda, accessible_vars, atoms, debug + 1
        ) and self._attempt_proof(new_agenda, accessible_vars, atoms, debug + 1)

    def _attempt_proof_n_and(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        new_agenda = agenda.clone()
        agenda.put(-current.term.first, context)
        new_agenda.put(-current.term.second, context)
        return self._attempt_proof(
            agenda, accessible_vars, atoms, debug + 1
        ) and self._attempt_proof(new_agenda, accessible_vars, atoms, debug + 1)

    def _attempt_proof_iff(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        new_agenda = agenda.clone()
        agenda.put(current.first, context)
        agenda.put(current.second, context)
        new_agenda.put(-current.first, context)
        new_agenda.put(-current.second, context)
        return self._attempt_proof(
            agenda, accessible_vars, atoms, debug + 1
        ) and self._attempt_proof(new_agenda, accessible_vars, atoms, debug + 1)

    def _attempt_proof_n_iff(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        new_agenda = agenda.clone()
        agenda.put(current.term.first, context)
        agenda.put(-current.term.second, context)
        new_agenda.put(-current.term.first, context)
        new_agenda.put(current.term.second, context)
        return self._attempt_proof(
            agenda, accessible_vars, atoms, debug + 1
        ) and self._attempt_proof(new_agenda, accessible_vars, atoms, debug + 1)

    def _attempt_proof_eq(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        #########################################################################
        # Since 'current' is of the form '(a = b)', replace ALL free instances
        # of 'a' with 'b'
        #########################################################################
        agenda.put_atoms(atoms)
        agenda.replace_all(current.first, current.second)
        accessible_vars.discard(current.first)
        agenda.mark_neqs_fresh()
        return self._attempt_proof(agenda, accessible_vars, set(), debug + 1)

    def _attempt_proof_some(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        new_unique_variable = VariableExpression(unique_variable())
        agenda.put(current.term.replace(current.variable, new_unique_variable), context)
        agenda.mark_alls_fresh()
        return self._attempt_proof(
            agenda, accessible_vars | {new_unique_variable}, atoms, debug + 1
        )

    def _attempt_proof_all(
        self, current, context, agenda, accessible_vars, atoms, debug
    ):
        try:
            current._used_vars
        except AttributeError:
            current._used_vars = set()

        # if there are accessible_vars on the path
        if accessible_vars:
            # get the set of bound variables that have not be used by this AllExpression
            bv_available = accessible_vars - current._used_vars

            if bv_available:
                variable_to_use = list(bv_available)[0]
                debug.line("--> Using '%s'" % variable_to_use, 2)
                current._used_vars |= {variable_to_use}
                agenda.put(
                    current.term.replace(current.variable, variable_to_use), context
                )
                agenda[Categories.ALL].add((current, context))
                return self._attempt_proof(agenda, accessible_vars, atoms, debug + 1)

            else:
                # no more available variables to substitute
                debug.line("--> Variables Exhausted", 2)
                current._exhausted = True
                agenda[Categories.ALL].add((current, context))
                return self._attempt_proof(agenda, accessible_vars, atoms, debug + 1)

        else:
            new_unique_variable = VariableExpression(unique_variable())
            debug.line("--> Using '%s'" % new_unique_variable, 2)
            current._used_vars |= {new_unique_variable}
            agenda.put(
                current.term.replace(current.variable, new_unique_variable), context
            )
            agenda[Categories.ALL].add((current, context))
            agenda.mark_alls_fresh()
            return self._attempt_proof(
                agenda, accessible_vars | {new_unique_variable}, atoms, debug + 1
            )

    @staticmethod
    def is_atom(e):
        if isinstance(e, NegatedExpression):
            e = e.term

        if isinstance(e, ApplicationExpression):
            for arg in e.args:
                if not TableauProver.is_atom(arg):
                    return False
            return True
        elif isinstance(e, AbstractVariableExpression) or isinstance(
            e, LambdaExpression
        ):
            return True
        else:
            return False


class TableauProverCommand(BaseProverCommand):
    def __init__(self, goal=None, assumptions=None, prover=None):
        """
        :param goal: Input expression to prove
        :type goal: sem.Expression
        :param assumptions: Input expressions to use as assumptions in
            the proof.
        :type assumptions: list(sem.Expression)
        """
        if prover is not None:
            assert isinstance(prover, TableauProver)
        else:
            prover = TableauProver()

        BaseProverCommand.__init__(self, prover, goal, assumptions)


class Agenda:
    def __init__(self):
        self.sets = tuple(set() for i in range(21))

    def clone(self):
        new_agenda = Agenda()
        set_list = [s.copy() for s in self.sets]

        new_allExs = set()
        for allEx, _ in set_list[Categories.ALL]:
            new_allEx = AllExpression(allEx.variable, allEx.term)
            try:
                new_allEx._used_vars = {used for used in allEx._used_vars}
            except AttributeError:
                new_allEx._used_vars = set()
            new_allExs.add((new_allEx, None))
        set_list[Categories.ALL] = new_allExs

        set_list[Categories.N_EQ] = {
            (NegatedExpression(n_eq.term), ctx)
            for (n_eq, ctx) in set_list[Categories.N_EQ]
        }

        new_agenda.sets = tuple(set_list)
        return new_agenda

    def __getitem__(self, index):
        return self.sets[index]

    def put(self, expression, context=None):
        if isinstance(expression, AllExpression):
            ex_to_add = AllExpression(expression.variable, expression.term)
            try:
                ex_to_add._used_vars = {used for used in expression._used_vars}
            except AttributeError:
                ex_to_add._used_vars = set()
        else:
            ex_to_add = expression
        self.sets[self._categorize_expression(ex_to_add)].add((ex_to_add, context))

    def put_all(self, expressions):
        for expression in expressions:
            self.put(expression)

    def put_atoms(self, atoms):
        for atom, neg in atoms:
            if neg:
                self[Categories.N_ATOM].add((-atom, None))
            else:
                self[Categories.ATOM].add((atom, None))

    def pop_first(self):
        """Pop the first expression that appears in the agenda"""
        for i, s in enumerate(self.sets):
            if s:
                if i in [Categories.N_EQ, Categories.ALL]:
                    for ex in s:
                        try:
                            if not ex[0]._exhausted:
                                s.remove(ex)
                                return (ex, i)
                        except AttributeError:
                            s.remove(ex)
                            return (ex, i)
                else:
                    return (s.pop(), i)
        return ((None, None), None)

    def replace_all(self, old, new):
        for s in self.sets:
            for ex, ctx in s:
                ex.replace(old.variable, new)
                if ctx is not None:
                    ctx.replace(old.variable, new)

    def mark_alls_fresh(self):
        for u, _ in self.sets[Categories.ALL]:
            u._exhausted = False

    def mark_neqs_fresh(self):
        for neq, _ in self.sets[Categories.N_EQ]:
            neq._exhausted = False

    def _categorize_expression(self, current):
        if isinstance(current, NegatedExpression):
            return self._categorize_NegatedExpression(current)
        elif isinstance(current, FunctionVariableExpression):
            return Categories.PROP
        elif TableauProver.is_atom(current):
            return Categories.ATOM
        elif isinstance(current, AllExpression):
            return Categories.ALL
        elif isinstance(current, AndExpression):
            return Categories.AND
        elif isinstance(current, OrExpression):
            return Categories.OR
        elif isinstance(current, ImpExpression):
            return Categories.IMP
        elif isinstance(current, IffExpression):
            return Categories.IFF
        elif isinstance(current, EqualityExpression):
            return Categories.EQ
        elif isinstance(current, ExistsExpression):
            return Categories.EXISTS
        elif isinstance(current, ApplicationExpression):
            return Categories.APP
        else:
            raise ProverParseError("cannot categorize %s" % current.__class__.__name__)

    def _categorize_NegatedExpression(self, current):
        negated = current.term

        if isinstance(negated, NegatedExpression):
            return Categories.D_NEG
        elif isinstance(negated, FunctionVariableExpression):
            return Categories.N_PROP
        elif TableauProver.is_atom(negated):
            return Categories.N_ATOM
        elif isinstance(negated, AllExpression):
            return Categories.N_ALL
        elif isinstance(negated, AndExpression):
            return Categories.N_AND
        elif isinstance(negated, OrExpression):
            return Categories.N_OR
        elif isinstance(negated, ImpExpression):
            return Categories.N_IMP
        elif isinstance(negated, IffExpression):
            return Categories.N_IFF
        elif isinstance(negated, EqualityExpression):
            return Categories.N_EQ
        elif isinstance(negated, ExistsExpression):
            return Categories.N_EXISTS
        elif isinstance(negated, ApplicationExpression):
            return Categories.N_APP
        else:
            raise ProverParseError("cannot categorize %s" % negated.__class__.__name__)


class Debug:
    def __init__(self, verbose, indent=0, lines=None):
        self.verbose = verbose
        self.indent = indent

        if not lines:
            lines = []
        self.lines = lines

    def __add__(self, increment):
        return Debug(self.verbose, self.indent + 1, self.lines)

    def line(self, data, indent=0):
        if isinstance(data, tuple):
            ex, ctx = data
            if ctx:
                data = f"{ex}, {ctx}"
            else:
                data = "%s" % ex

            if isinstance(ex, AllExpression):
                try:
                    used_vars = "[%s]" % (
                        ",".join("%s" % ve.variable.name for ve in ex._used_vars)
                    )
                    data += ":   %s" % used_vars
                except AttributeError:
                    data += ":   []"

        newline = "{}{}".format("   " * (self.indent + indent), data)
        self.lines.append(newline)

        if self.verbose:
            print(newline)


class Categories:
    ATOM = 0
    PROP = 1
    N_ATOM = 2
    N_PROP = 3
    APP = 4
    N_APP = 5
    N_EQ = 6
    D_NEG = 7
    N_ALL = 8
    N_EXISTS = 9
    AND = 10
    N_OR = 11
    N_IMP = 12
    OR = 13
    IMP = 14
    N_AND = 15
    IFF = 16
    N_IFF = 17
    EQ = 18
    EXISTS = 19
    ALL = 20


def testTableauProver():
    tableau_test("P | -P")
    tableau_test("P & -P")
    tableau_test("Q", ["P", "(P -> Q)"])
    tableau_test("man(x)")
    tableau_test("(man(x) -> man(x))")
    tableau_test("(man(x) -> --man(x))")
    tableau_test("-(man(x) and -man(x))")
    tableau_test("(man(x) or -man(x))")
    tableau_test("(man(x) -> man(x))")
    tableau_test("-(man(x) and -man(x))")
    tableau_test("(man(x) or -man(x))")
    tableau_test("(man(x) -> man(x))")
    tableau_test("(man(x) iff man(x))")
    tableau_test("-(man(x) iff -man(x))")
    tableau_test("all x.man(x)")
    tableau_test("all x.all y.((x = y) -> (y = x))")
    tableau_test("all x.all y.all z.(((x = y) & (y = z)) -> (x = z))")
    #    tableau_test('-all x.some y.F(x,y) & some x.all y.(-F(x,y))')
    #    tableau_test('some x.all y.sees(x,y)')

    p1 = "all x.(man(x) -> mortal(x))"
    p2 = "man(Socrates)"
    c = "mortal(Socrates)"
    tableau_test(c, [p1, p2])

    p1 = "all x.(man(x) -> walks(x))"
    p2 = "man(John)"
    c = "some y.walks(y)"
    tableau_test(c, [p1, p2])

    p = "((x = y) & walks(y))"
    c = "walks(x)"
    tableau_test(c, [p])

    p = "((x = y) & ((y = z) & (z = w)))"
    c = "(x = w)"
    tableau_test(c, [p])

    p = "some e1.some e2.(believe(e1,john,e2) & walk(e2,mary))"
    c = "some e0.walk(e0,mary)"
    tableau_test(c, [p])

    c = "(exists x.exists z3.((x = Mary) & ((z3 = John) & sees(z3,x))) <-> exists x.exists z4.((x = John) & ((z4 = Mary) & sees(x,z4))))"
    tableau_test(c)


#    p = 'some e1.some e2.((believe e1 john e2) and (walk e2 mary))'
#    c = 'some x.some e3.some e4.((believe e3 x e4) and (walk e4 mary))'
#    tableau_test(c, [p])


def testHigherOrderTableauProver():
    tableau_test("believe(j, -lie(b))", ["believe(j, -lie(b) & -cheat(b))"])
    tableau_test("believe(j, lie(b) & cheat(b))", ["believe(j, lie(b))"])
    tableau_test(
        "believe(j, lie(b))", ["lie(b)"]
    )  # how do we capture that John believes all things that are true
    tableau_test(
        "believe(j, know(b, cheat(b)))",
        ["believe(j, know(b, lie(b)) & know(b, steals(b) & cheat(b)))"],
    )
    tableau_test("P(Q(y), R(y) & R(z))", ["P(Q(x) & Q(y), R(y) & R(z))"])

    tableau_test("believe(j, cheat(b) & lie(b))", ["believe(j, lie(b) & cheat(b))"])
    tableau_test("believe(j, -cheat(b) & -lie(b))", ["believe(j, -lie(b) & -cheat(b))"])


def tableau_test(c, ps=None, verbose=False):
    pc = Expression.fromstring(c)
    pps = [Expression.fromstring(p) for p in ps] if ps else []
    if not ps:
        ps = []
    print(
        "%s |- %s: %s"
        % (", ".join(ps), pc, TableauProver().prove(pc, pps, verbose=verbose))
    )


def demo():
    testTableauProver()
    testHigherOrderTableauProver()


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\typer\rich_utils.py ===
# Extracted and modified from https://github.com/ewels/rich-click

import inspect
import sys
from collections import defaultdict
from gettext import gettext as _
from os import getenv
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Union

import click
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, RenderableType, group
from rich.emoji import Emoji
from rich.highlighter import RegexHighlighter
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

# Default styles
STYLE_OPTION = "bold cyan"
STYLE_SWITCH = "bold green"
STYLE_NEGATIVE_OPTION = "bold magenta"
STYLE_NEGATIVE_SWITCH = "bold red"
STYLE_METAVAR = "bold yellow"
STYLE_METAVAR_SEPARATOR = "dim"
STYLE_USAGE = "yellow"
STYLE_USAGE_COMMAND = "bold"
STYLE_DEPRECATED = "red"
STYLE_DEPRECATED_COMMAND = "dim"
STYLE_HELPTEXT_FIRST_LINE = ""
STYLE_HELPTEXT = "dim"
STYLE_OPTION_HELP = ""
STYLE_OPTION_DEFAULT = "dim"
STYLE_OPTION_ENVVAR = "dim yellow"
STYLE_REQUIRED_SHORT = "red"
STYLE_REQUIRED_LONG = "dim red"
STYLE_OPTIONS_PANEL_BORDER = "dim"
ALIGN_OPTIONS_PANEL: Literal["left", "center", "right"] = "left"
STYLE_OPTIONS_TABLE_SHOW_LINES = False
STYLE_OPTIONS_TABLE_LEADING = 0
STYLE_OPTIONS_TABLE_PAD_EDGE = False
STYLE_OPTIONS_TABLE_PADDING = (0, 1)
STYLE_OPTIONS_TABLE_BOX = ""
STYLE_OPTIONS_TABLE_ROW_STYLES = None
STYLE_OPTIONS_TABLE_BORDER_STYLE = None
STYLE_COMMANDS_PANEL_BORDER = "dim"
ALIGN_COMMANDS_PANEL: Literal["left", "center", "right"] = "left"
STYLE_COMMANDS_TABLE_SHOW_LINES = False
STYLE_COMMANDS_TABLE_LEADING = 0
STYLE_COMMANDS_TABLE_PAD_EDGE = False
STYLE_COMMANDS_TABLE_PADDING = (0, 1)
STYLE_COMMANDS_TABLE_BOX = ""
STYLE_COMMANDS_TABLE_ROW_STYLES = None
STYLE_COMMANDS_TABLE_BORDER_STYLE = None
STYLE_ERRORS_PANEL_BORDER = "red"
ALIGN_ERRORS_PANEL: Literal["left", "center", "right"] = "left"
STYLE_ERRORS_SUGGESTION = "dim"
STYLE_ABORTED = "red"
_TERMINAL_WIDTH = getenv("TERMINAL_WIDTH")
MAX_WIDTH = int(_TERMINAL_WIDTH) if _TERMINAL_WIDTH else None
COLOR_SYSTEM: Optional[
    Literal["auto", "standard", "256", "truecolor", "windows"]
] = "auto"  # Set to None to disable colors
_TYPER_FORCE_DISABLE_TERMINAL = getenv("_TYPER_FORCE_DISABLE_TERMINAL")
FORCE_TERMINAL = (
    True
    if getenv("GITHUB_ACTIONS") or getenv("FORCE_COLOR") or getenv("PY_COLORS")
    else None
)
if _TYPER_FORCE_DISABLE_TERMINAL:
    FORCE_TERMINAL = False

# Fixed strings
DEPRECATED_STRING = _("(deprecated) ")
DEFAULT_STRING = _("[default: {}]")
ENVVAR_STRING = _("[env var: {}]")
REQUIRED_SHORT_STRING = "*"
REQUIRED_LONG_STRING = _("[required]")
RANGE_STRING = " [{}]"
ARGUMENTS_PANEL_TITLE = _("Arguments")
OPTIONS_PANEL_TITLE = _("Options")
COMMANDS_PANEL_TITLE = _("Commands")
ERRORS_PANEL_TITLE = _("Error")
ABORTED_TEXT = _("Aborted.")

MARKUP_MODE_MARKDOWN = "markdown"
MARKUP_MODE_RICH = "rich"
_RICH_HELP_PANEL_NAME = "rich_help_panel"

MarkupMode = Literal["markdown", "rich", None]


# Rich regex highlighter
class OptionHighlighter(RegexHighlighter):
    """Highlights our special options."""

    highlights = [
        r"(^|\W)(?P<switch>\-\w+)(?![a-zA-Z0-9])",
        r"(^|\W)(?P<option>\-\-[\w\-]+)(?![a-zA-Z0-9])",
        r"(?P<metavar>\<[^\>]+\>)",
        r"(?P<usage>Usage: )",
    ]


class NegativeOptionHighlighter(RegexHighlighter):
    highlights = [
        r"(^|\W)(?P<negative_switch>\-\w+)(?![a-zA-Z0-9])",
        r"(^|\W)(?P<negative_option>\-\-[\w\-]+)(?![a-zA-Z0-9])",
    ]


highlighter = OptionHighlighter()
negative_highlighter = NegativeOptionHighlighter()


def _get_rich_console(stderr: bool = False) -> Console:
    return Console(
        theme=Theme(
            {
                "option": STYLE_OPTION,
                "switch": STYLE_SWITCH,
                "negative_option": STYLE_NEGATIVE_OPTION,
                "negative_switch": STYLE_NEGATIVE_SWITCH,
                "metavar": STYLE_METAVAR,
                "metavar_sep": STYLE_METAVAR_SEPARATOR,
                "usage": STYLE_USAGE,
            },
        ),
        highlighter=highlighter,
        color_system=COLOR_SYSTEM,
        force_terminal=FORCE_TERMINAL,
        width=MAX_WIDTH,
        stderr=stderr,
    )


def _make_rich_rext(
    *, text: str, style: str = "", markup_mode: MarkupMode
) -> Union[Markdown, Text]:
    """Take a string, remove indentations, and return styled text.

    By default, return the text as a Rich Text with the request style.
    If `rich_markdown_enable` is `True`, also parse the text for Rich markup strings.
    If `rich_markup_enable` is `True`, parse as Markdown.

    Only one of `rich_markdown_enable` or `rich_markup_enable` can be True.
    If both are True, `rich_markdown_enable` takes precedence.
    """
    # Remove indentations from input text
    text = inspect.cleandoc(text)
    if markup_mode == MARKUP_MODE_MARKDOWN:
        text = Emoji.replace(text)
        return Markdown(text, style=style)
    if markup_mode == MARKUP_MODE_RICH:
        return highlighter(Text.from_markup(text, style=style))
    else:
        return highlighter(Text(text, style=style))


@group()
def _get_help_text(
    *,
    obj: Union[click.Command, click.Group],
    markup_mode: MarkupMode,
) -> Iterable[Union[Markdown, Text]]:
    """Build primary help text for a click command or group.

    Returns the prose help text for a command or group, rendered either as a
    Rich Text object or as Markdown.
    If the command is marked as deprecated, the deprecated string will be prepended.
    """
    # Prepend deprecated status
    if obj.deprecated:
        yield Text(DEPRECATED_STRING, style=STYLE_DEPRECATED)

    # Fetch and dedent the help text
    help_text = inspect.cleandoc(obj.help or "")

    # Trim off anything that comes after \f on its own line
    help_text = help_text.partition("\f")[0]

    # Get the first paragraph
    first_line = help_text.split("\n\n")[0]
    # Remove single linebreaks
    if markup_mode != MARKUP_MODE_MARKDOWN and not first_line.startswith("\b"):
        first_line = first_line.replace("\n", " ")
    yield _make_rich_rext(
        text=first_line.strip(),
        style=STYLE_HELPTEXT_FIRST_LINE,
        markup_mode=markup_mode,
    )

    # Get remaining lines, remove single line breaks and format as dim
    remaining_paragraphs = help_text.split("\n\n")[1:]
    if remaining_paragraphs:
        if markup_mode != MARKUP_MODE_RICH:
            # Remove single linebreaks
            remaining_paragraphs = [
                x.replace("\n", " ").strip()
                if not x.startswith("\b")
                else "{}\n".format(x.strip("\b\n"))
                for x in remaining_paragraphs
            ]
            # Join back together
            remaining_lines = "\n".join(remaining_paragraphs)
        else:
            # Join with double linebreaks if markdown
            remaining_lines = "\n\n".join(remaining_paragraphs)

        yield _make_rich_rext(
            text=remaining_lines,
            style=STYLE_HELPTEXT,
            markup_mode=markup_mode,
        )


def _get_parameter_help(
    *,
    param: Union[click.Option, click.Argument, click.Parameter],
    ctx: click.Context,
    markup_mode: MarkupMode,
) -> Columns:
    """Build primary help text for a click option or argument.

    Returns the prose help text for an option or argument, rendered either
    as a Rich Text object or as Markdown.
    Additional elements are appended to show the default and required status if
    applicable.
    """
    # import here to avoid cyclic imports
    from .core import TyperArgument, TyperOption

    items: List[Union[Text, Markdown]] = []

    # Get the environment variable first

    envvar = getattr(param, "envvar", None)
    var_str = ""
    # https://github.com/pallets/click/blob/0aec1168ac591e159baf6f61026d6ae322c53aaf/src/click/core.py#L2720-L2726
    if envvar is None:
        if (
            getattr(param, "allow_from_autoenv", None)
            and getattr(ctx, "auto_envvar_prefix", None) is not None
            and param.name is not None
        ):
            envvar = f"{ctx.auto_envvar_prefix}_{param.name.upper()}"
    if envvar is not None:
        var_str = (
            envvar if isinstance(envvar, str) else ", ".join(str(d) for d in envvar)
        )

    # Main help text
    help_value: Union[str, None] = getattr(param, "help", None)
    if help_value:
        paragraphs = help_value.split("\n\n")
        # Remove single linebreaks
        if markup_mode != MARKUP_MODE_MARKDOWN:
            paragraphs = [
                x.replace("\n", " ").strip()
                if not x.startswith("\b")
                else "{}\n".format(x.strip("\b\n"))
                for x in paragraphs
            ]
        items.append(
            _make_rich_rext(
                text="\n".join(paragraphs).strip(),
                style=STYLE_OPTION_HELP,
                markup_mode=markup_mode,
            )
        )

    # Environment variable AFTER help text
    if envvar and getattr(param, "show_envvar", None):
        items.append(Text(ENVVAR_STRING.format(var_str), style=STYLE_OPTION_ENVVAR))

    # Default value
    # This uses Typer's specific param._get_default_string
    if isinstance(param, (TyperOption, TyperArgument)):
        if param.show_default:
            show_default_is_str = isinstance(param.show_default, str)
            default_value = param._extract_default_help_str(ctx=ctx)
            default_str = param._get_default_string(
                ctx=ctx,
                show_default_is_str=show_default_is_str,
                default_value=default_value,
            )
            if default_str:
                items.append(
                    Text(
                        DEFAULT_STRING.format(default_str),
                        style=STYLE_OPTION_DEFAULT,
                    )
                )

    # Required?
    if param.required:
        items.append(Text(REQUIRED_LONG_STRING, style=STYLE_REQUIRED_LONG))

    # Use Columns - this allows us to group different renderable types
    # (Text, Markdown) onto a single line.
    return Columns(items)


def _make_command_help(
    *,
    help_text: str,
    markup_mode: MarkupMode,
) -> Union[Text, Markdown]:
    """Build cli help text for a click group command.

    That is, when calling help on groups with multiple subcommands
    (not the main help text when calling the subcommand help).

    Returns the first paragraph of help text for a command, rendered either as a
    Rich Text object or as Markdown.
    Ignores single newlines as paragraph markers, looks for double only.
    """
    paragraphs = inspect.cleandoc(help_text).split("\n\n")
    # Remove single linebreaks
    if markup_mode != MARKUP_MODE_RICH and not paragraphs[0].startswith("\b"):
        paragraphs[0] = paragraphs[0].replace("\n", " ")
    elif paragraphs[0].startswith("\b"):
        paragraphs[0] = paragraphs[0].replace("\b\n", "")
    return _make_rich_rext(
        text=paragraphs[0].strip(),
        style=STYLE_OPTION_HELP,
        markup_mode=markup_mode,
    )


def _print_options_panel(
    *,
    name: str,
    params: Union[List[click.Option], List[click.Argument]],
    ctx: click.Context,
    markup_mode: MarkupMode,
    console: Console,
) -> None:
    options_rows: List[List[RenderableType]] = []
    required_rows: List[Union[str, Text]] = []
    for param in params:
        # Short and long form
        opt_long_strs = []
        opt_short_strs = []
        secondary_opt_long_strs = []
        secondary_opt_short_strs = []
        for opt_str in param.opts:
            if "--" in opt_str:
                opt_long_strs.append(opt_str)
            else:
                opt_short_strs.append(opt_str)
        for opt_str in param.secondary_opts:
            if "--" in opt_str:
                secondary_opt_long_strs.append(opt_str)
            else:
                secondary_opt_short_strs.append(opt_str)

        # Column for a metavar, if we have one
        metavar = Text(style=STYLE_METAVAR, overflow="fold")
        metavar_str = param.make_metavar()

        # Do it ourselves if this is a positional argument
        if (
            isinstance(param, click.Argument)
            and param.name
            and metavar_str == param.name.upper()
        ):
            metavar_str = param.type.name.upper()

        # Skip booleans and choices (handled above)
        if metavar_str != "BOOLEAN":
            metavar.append(metavar_str)

        # Range - from
        # https://github.com/pallets/click/blob/c63c70dabd3f86ca68678b4f00951f78f52d0270/src/click/core.py#L2698-L2706  # noqa: E501
        # skip count with default range type
        if (
            isinstance(param.type, click.types._NumberRangeBase)
            and isinstance(param, click.Option)
            and not (param.count and param.type.min == 0 and param.type.max is None)
        ):
            range_str = param.type._describe_range()
            if range_str:
                metavar.append(RANGE_STRING.format(range_str))

        # Required asterisk
        required: Union[str, Text] = ""
        if param.required:
            required = Text(REQUIRED_SHORT_STRING, style=STYLE_REQUIRED_SHORT)

        # Highlighter to make [ | ] and <> dim
        class MetavarHighlighter(RegexHighlighter):
            highlights = [
                r"^(?P<metavar_sep>(\[|<))",
                r"(?P<metavar_sep>\|)",
                r"(?P<metavar_sep>(\]|>)$)",
            ]

        metavar_highlighter = MetavarHighlighter()

        required_rows.append(required)
        options_rows.append(
            [
                highlighter(",".join(opt_long_strs)),
                highlighter(",".join(opt_short_strs)),
                negative_highlighter(",".join(secondary_opt_long_strs)),
                negative_highlighter(",".join(secondary_opt_short_strs)),
                metavar_highlighter(metavar),
                _get_parameter_help(
                    param=param,
                    ctx=ctx,
                    markup_mode=markup_mode,
                ),
            ]
        )
    rows_with_required: List[List[RenderableType]] = []
    if any(required_rows):
        for required, row in zip(required_rows, options_rows):
            rows_with_required.append([required, *row])
    else:
        rows_with_required = options_rows
    if options_rows:
        t_styles: Dict[str, Any] = {
            "show_lines": STYLE_OPTIONS_TABLE_SHOW_LINES,
            "leading": STYLE_OPTIONS_TABLE_LEADING,
            "box": STYLE_OPTIONS_TABLE_BOX,
            "border_style": STYLE_OPTIONS_TABLE_BORDER_STYLE,
            "row_styles": STYLE_OPTIONS_TABLE_ROW_STYLES,
            "pad_edge": STYLE_OPTIONS_TABLE_PAD_EDGE,
            "padding": STYLE_OPTIONS_TABLE_PADDING,
        }
        box_style = getattr(box, t_styles.pop("box"), None)

        options_table = Table(
            highlight=True,
            show_header=False,
            expand=True,
            box=box_style,
            **t_styles,
        )
        for row in rows_with_required:
            options_table.add_row(*row)
        console.print(
            Panel(
                options_table,
                border_style=STYLE_OPTIONS_PANEL_BORDER,
                title=name,
                title_align=ALIGN_OPTIONS_PANEL,
            )
        )


def _print_commands_panel(
    *,
    name: str,
    commands: List[click.Command],
    markup_mode: MarkupMode,
    console: Console,
    cmd_len: int,
) -> None:
    t_styles: Dict[str, Any] = {
        "show_lines": STYLE_COMMANDS_TABLE_SHOW_LINES,
        "leading": STYLE_COMMANDS_TABLE_LEADING,
        "box": STYLE_COMMANDS_TABLE_BOX,
        "border_style": STYLE_COMMANDS_TABLE_BORDER_STYLE,
        "row_styles": STYLE_COMMANDS_TABLE_ROW_STYLES,
        "pad_edge": STYLE_COMMANDS_TABLE_PAD_EDGE,
        "padding": STYLE_COMMANDS_TABLE_PADDING,
    }
    box_style = getattr(box, t_styles.pop("box"), None)

    commands_table = Table(
        highlight=False,
        show_header=False,
        expand=True,
        box=box_style,
        **t_styles,
    )
    # Define formatting in first column, as commands don't match highlighter
    # regex
    commands_table.add_column(
        style="bold cyan",
        no_wrap=True,
        width=cmd_len,
    )

    # A big ratio makes the description column be greedy and take all the space
    # available instead of allowing the command column to grow and misalign with
    # other panels.
    commands_table.add_column("Description", justify="left", no_wrap=False, ratio=10)
    rows: List[List[Union[RenderableType, None]]] = []
    deprecated_rows: List[Union[RenderableType, None]] = []
    for command in commands:
        helptext = command.short_help or command.help or ""
        command_name = command.name or ""
        if command.deprecated:
            command_name_text = Text(f"{command_name}", style=STYLE_DEPRECATED_COMMAND)
            deprecated_rows.append(Text(DEPRECATED_STRING, style=STYLE_DEPRECATED))
        else:
            command_name_text = Text(command_name)
            deprecated_rows.append(None)
        rows.append(
            [
                command_name_text,
                _make_command_help(
                    help_text=helptext,
                    markup_mode=markup_mode,
                ),
            ]
        )
    rows_with_deprecated = rows
    if any(deprecated_rows):
        rows_with_deprecated = []
        for row, deprecated_text in zip(rows, deprecated_rows):
            rows_with_deprecated.append([*row, deprecated_text])
    for row in rows_with_deprecated:
        commands_table.add_row(*row)
    if commands_table.row_count:
        console.print(
            Panel(
                commands_table,
                border_style=STYLE_COMMANDS_PANEL_BORDER,
                title=name,
                title_align=ALIGN_COMMANDS_PANEL,
            )
        )


def rich_format_help(
    *,
    obj: Union[click.Command, click.Group],
    ctx: click.Context,
    markup_mode: MarkupMode,
) -> None:
    """Print nicely formatted help text using rich.

    Based on original code from rich-cli, by @willmcgugan.
    https://github.com/Textualize/rich-cli/blob/8a2767c7a340715fc6fbf4930ace717b9b2fc5e5/src/rich_cli/__main__.py#L162-L236

    Replacement for the click function format_help().
    Takes a command or group and builds the help text output.
    """
    console = _get_rich_console()

    # Print usage
    console.print(
        Padding(highlighter(obj.get_usage(ctx)), 1), style=STYLE_USAGE_COMMAND
    )

    # Print command / group help if we have some
    if obj.help:
        # Print with some padding
        console.print(
            Padding(
                Align(
                    _get_help_text(
                        obj=obj,
                        markup_mode=markup_mode,
                    ),
                    pad=False,
                ),
                (0, 1, 1, 1),
            )
        )
    panel_to_arguments: DefaultDict[str, List[click.Argument]] = defaultdict(list)
    panel_to_options: DefaultDict[str, List[click.Option]] = defaultdict(list)
    for param in obj.get_params(ctx):
        # Skip if option is hidden
        if getattr(param, "hidden", False):
            continue
        if isinstance(param, click.Argument):
            panel_name = (
                getattr(param, _RICH_HELP_PANEL_NAME, None) or ARGUMENTS_PANEL_TITLE
            )
            panel_to_arguments[panel_name].append(param)
        elif isinstance(param, click.Option):
            panel_name = (
                getattr(param, _RICH_HELP_PANEL_NAME, None) or OPTIONS_PANEL_TITLE
            )
            panel_to_options[panel_name].append(param)
    default_arguments = panel_to_arguments.get(ARGUMENTS_PANEL_TITLE, [])
    _print_options_panel(
        name=ARGUMENTS_PANEL_TITLE,
        params=default_arguments,
        ctx=ctx,
        markup_mode=markup_mode,
        console=console,
    )
    for panel_name, arguments in panel_to_arguments.items():
        if panel_name == ARGUMENTS_PANEL_TITLE:
            # Already printed above
            continue
        _print_options_panel(
            name=panel_name,
            params=arguments,
            ctx=ctx,
            markup_mode=markup_mode,
            console=console,
        )
    default_options = panel_to_options.get(OPTIONS_PANEL_TITLE, [])
    _print_options_panel(
        name=OPTIONS_PANEL_TITLE,
        params=default_options,
        ctx=ctx,
        markup_mode=markup_mode,
        console=console,
    )
    for panel_name, options in panel_to_options.items():
        if panel_name == OPTIONS_PANEL_TITLE:
            # Already printed above
            continue
        _print_options_panel(
            name=panel_name,
            params=options,
            ctx=ctx,
            markup_mode=markup_mode,
            console=console,
        )

    if isinstance(obj, click.Group):
        panel_to_commands: DefaultDict[str, List[click.Command]] = defaultdict(list)
        for command_name in obj.list_commands(ctx):
            command = obj.get_command(ctx, command_name)
            if command and not command.hidden:
                panel_name = (
                    getattr(command, _RICH_HELP_PANEL_NAME, None)
                    or COMMANDS_PANEL_TITLE
                )
                panel_to_commands[panel_name].append(command)

        # Identify the longest command name in all panels
        max_cmd_len = max(
            [
                len(command.name or "")
                for commands in panel_to_commands.values()
                for command in commands
            ],
            default=0,
        )

        # Print each command group panel
        default_commands = panel_to_commands.get(COMMANDS_PANEL_TITLE, [])
        _print_commands_panel(
            name=COMMANDS_PANEL_TITLE,
            commands=default_commands,
            markup_mode=markup_mode,
            console=console,
            cmd_len=max_cmd_len,
        )
        for panel_name, commands in panel_to_commands.items():
            if panel_name == COMMANDS_PANEL_TITLE:
                # Already printed above
                continue
            _print_commands_panel(
                name=panel_name,
                commands=commands,
                markup_mode=markup_mode,
                console=console,
                cmd_len=max_cmd_len,
            )

    # Epilogue if we have it
    if obj.epilog:
        # Remove single linebreaks, replace double with single
        lines = obj.epilog.split("\n\n")
        epilogue = "\n".join([x.replace("\n", " ").strip() for x in lines])
        epilogue_text = _make_rich_rext(text=epilogue, markup_mode=markup_mode)
        console.print(Padding(Align(epilogue_text, pad=False), 1))


def rich_format_error(self: click.ClickException) -> None:
    """Print richly formatted click errors.

    Called by custom exception handler to print richly formatted click errors.
    Mimics original click.ClickException.echo() function but with rich formatting.
    """
    console = _get_rich_console(stderr=True)
    ctx: Union[click.Context, None] = getattr(self, "ctx", None)
    if ctx is not None:
        console.print(ctx.get_usage())

    if ctx is not None and ctx.command.get_help_option(ctx) is not None:
        console.print(
            f"Try [blue]'{ctx.command_path} {ctx.help_option_names[0]}'[/] for help.",
            style=STYLE_ERRORS_SUGGESTION,
        )

    console.print(
        Panel(
            highlighter(self.format_message()),
            border_style=STYLE_ERRORS_PANEL_BORDER,
            title=ERRORS_PANEL_TITLE,
            title_align=ALIGN_ERRORS_PANEL,
        )
    )


def rich_abort_error() -> None:
    """Print richly formatted abort error."""
    console = _get_rich_console(stderr=True)
    console.print(ABORTED_TEXT, style=STYLE_ABORTED)

# === NexusCore/openenv\Lib\site-packages\IPython\core\magics\namespace.py ===
"""Implementation of namespace-related magic functions.
"""
#-----------------------------------------------------------------------------
#  Copyright (c) 2012 The IPython Development Team.
#
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib
import gc
import re
import sys

# Our own packages
from IPython.core import page
from IPython.core.error import StdinNotImplementedError, UsageError
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.testing.skipdoctest import skip_doctest
from IPython.utils.encoding import DEFAULT_ENCODING
from IPython.utils.openpy import read_py_file
from IPython.utils.path import get_py_filename

#-----------------------------------------------------------------------------
# Magic implementation classes
#-----------------------------------------------------------------------------

@magics_class
class NamespaceMagics(Magics):
    """Magics to manage various aspects of the user's namespace.

    These include listing variables, introspecting into them, etc.
    """

    @line_magic
    def pinfo(self, parameter_s='', namespaces=None):
        """Provide detailed information about an object.

        '%pinfo object' is just a synonym for object? or ?object."""

        # print('pinfo par: <%s>' % parameter_s)  # dbg
        # detail_level: 0 -> obj? , 1 -> obj??
        detail_level = 0
        # We need to detect if we got called as 'pinfo pinfo foo', which can
        # happen if the user types 'pinfo foo?' at the cmd line.
        pinfo,qmark1,oname,qmark2 = \
               re.match(r'(pinfo )?(\?*)(.*?)(\??$)',parameter_s).groups()
        if pinfo or qmark1 or qmark2:
            detail_level = 1
        if "*" in oname:
            self.psearch(oname)
        else:
            self.shell._inspect('pinfo', oname, detail_level=detail_level,
                                namespaces=namespaces)

    @line_magic
    def pinfo2(self, parameter_s='', namespaces=None):
        """Provide extra detailed information about an object.

        '%pinfo2 object' is just a synonym for object?? or ??object."""
        self.shell._inspect('pinfo', parameter_s, detail_level=1,
                            namespaces=namespaces)

    @skip_doctest
    @line_magic
    def pdef(self, parameter_s='', namespaces=None):
        """Print the call signature for any callable object.

        If the object is a class, print the constructor information.

        Examples
        --------
        ::

          In [3]: %pdef urllib.urlopen
          urllib.urlopen(url, data=None, proxies=None)
        """
        self.shell._inspect('pdef',parameter_s, namespaces)

    @line_magic
    def pdoc(self, parameter_s='', namespaces=None):
        """Print the docstring for an object.

        If the given object is a class, it will print both the class and the
        constructor docstrings."""
        self.shell._inspect('pdoc',parameter_s, namespaces)

    @line_magic
    def psource(self, parameter_s='', namespaces=None):
        """Print (or run through pager) the source code for an object."""
        if not parameter_s:
            raise UsageError('Missing object name.')
        self.shell._inspect('psource',parameter_s, namespaces)

    @line_magic
    def pfile(self, parameter_s='', namespaces=None):
        """Print (or run through pager) the file where an object is defined.

        The file opens at the line where the object definition begins. IPython
        will honor the environment variable PAGER if set, and otherwise will
        do its best to print the file in a convenient form.

        If the given argument is not an object currently defined, IPython will
        try to interpret it as a filename (automatically adding a .py extension
        if needed). You can thus use %pfile as a syntax highlighting code
        viewer."""

        # first interpret argument as an object name
        out = self.shell._inspect('pfile',parameter_s, namespaces)
        # if not, try the input as a filename
        if out == 'not found':
            try:
                filename = get_py_filename(parameter_s)
            except IOError as msg:
                print(msg)
                return
            page.page(self.shell.pycolorize(read_py_file(filename, skip_encoding_cookie=False)))

    @line_magic
    def psearch(self, parameter_s=''):
        """Search for object in namespaces by wildcard.

        %psearch [options] PATTERN [OBJECT TYPE]

        Note: ? can be used as a synonym for %psearch, at the beginning or at
        the end: both a*? and ?a* are equivalent to '%psearch a*'.  Still, the
        rest of the command line must be unchanged (options come first), so
        for example the following forms are equivalent

        %psearch -i a* function
        -i a* function?
        ?-i a* function

        Arguments:

          PATTERN

          where PATTERN is a string containing * as a wildcard similar to its
          use in a shell.  The pattern is matched in all namespaces on the
          search path. By default objects starting with a single _ are not
          matched, many IPython generated objects have a single
          underscore. The default is case insensitive matching. Matching is
          also done on the attributes of objects and not only on the objects
          in a module.

          [OBJECT TYPE]

          Is the name of a python type from the types module. The name is
          given in lowercase without the ending type, ex. StringType is
          written string. By adding a type here only objects matching the
          given type are matched. Using all here makes the pattern match all
          types (this is the default).

        Options:

          -a: makes the pattern match even objects whose names start with a
          single underscore.  These names are normally omitted from the
          search.

          -i/-c: make the pattern case insensitive/sensitive.  If neither of
          these options are given, the default is read from your configuration
          file, with the option ``InteractiveShell.wildcards_case_sensitive``.
          If this option is not specified in your configuration file, IPython's
          internal default is to do a case sensitive search.

          -e/-s NAMESPACE: exclude/search a given namespace.  The pattern you
          specify can be searched in any of the following namespaces:
          'builtin', 'user', 'user_global','internal', 'alias', where
          'builtin' and 'user' are the search defaults.  Note that you should
          not use quotes when specifying namespaces.

          -l: List all available object types for object matching. This function
          can be used without arguments.

          'Builtin' contains the python module builtin, 'user' contains all
          user data, 'alias' only contain the shell aliases and no python
          objects, 'internal' contains objects used by IPython.  The
          'user_global' namespace is only used by embedded IPython instances,
          and it contains module-level globals.  You can add namespaces to the
          search with -s or exclude them with -e (these options can be given
          more than once).

        Examples
        --------
        ::

          %psearch a*            -> objects beginning with an a
          %psearch -e builtin a* -> objects NOT in the builtin space starting in a
          %psearch a* function   -> all functions beginning with an a
          %psearch re.e*         -> objects beginning with an e in module re
          %psearch r*.e*         -> objects that start with e in modules starting in r
          %psearch r*.* string   -> all strings in modules beginning with r

        Case sensitive search::

          %psearch -c a*         list all object beginning with lower case a

        Show objects beginning with a single _::

          %psearch -a _*         list objects beginning with a single underscore

        List available objects::

          %psearch -l            list all available object types
        """
        # default namespaces to be searched
        def_search = ['user_local', 'user_global', 'builtin']

        # Process options/args
        opts,args = self.parse_options(parameter_s,'cias:e:l',list_all=True)
        opt = opts.get
        shell = self.shell
        psearch = shell.inspector.psearch
        
        # select list object types
        list_types = False
        if 'l' in opts:
            list_types = True

        # select case options
        if 'i' in opts:
            ignore_case = True
        elif 'c' in opts:
            ignore_case = False
        else:
            ignore_case = not shell.wildcards_case_sensitive

        # Build list of namespaces to search from user options
        def_search.extend(opt('s',[]))
        ns_exclude = ns_exclude=opt('e',[])
        ns_search = [nm for nm in def_search if nm not in ns_exclude]

        # Call the actual search
        try:
            psearch(args,shell.ns_table,ns_search,
                    show_all=opt('a'),ignore_case=ignore_case, list_types=list_types)
        except:
            shell.showtraceback()

    @skip_doctest
    @line_magic
    def who_ls(self, parameter_s=''):
        """Return a sorted list of all interactive variables.

        If arguments are given, only variables of types matching these
        arguments are returned.

        Examples
        --------
        Define two variables and list them with who_ls::

          In [1]: alpha = 123

          In [2]: beta = 'test'

          In [3]: %who_ls
          Out[3]: ['alpha', 'beta']

          In [4]: %who_ls int
          Out[4]: ['alpha']

          In [5]: %who_ls str
          Out[5]: ['beta']
        """

        user_ns = self.shell.user_ns
        user_ns_hidden = self.shell.user_ns_hidden
        nonmatching = object()  # This can never be in user_ns
        out = [ i for i in user_ns
                if not i.startswith('_') \
                and (user_ns[i] is not user_ns_hidden.get(i, nonmatching)) ]

        typelist = parameter_s.split()
        if typelist:
            typeset = set(typelist)
            out = [i for i in out if type(user_ns[i]).__name__ in typeset]

        out.sort()
        return out

    @skip_doctest
    @line_magic
    def who(self, parameter_s=''):
        """Print all interactive variables, with some minimal formatting.

        If any arguments are given, only variables whose type matches one of
        these are printed.  For example::

          %who function str

        will only list functions and strings, excluding all other types of
        variables.  To find the proper type names, simply use type(var) at a
        command line to see how python prints type names.  For example:

        ::

          In [1]: type('hello')\\
          Out[1]: <type 'str'>

        indicates that the type name for strings is 'str'.

        ``%who`` always excludes executed names loaded through your configuration
        file and things which are internal to IPython.

        This is deliberate, as typically you may load many modules and the
        purpose of %who is to show you only what you've manually defined.

        Examples
        --------

        Define two variables and list them with who::

          In [1]: alpha = 123

          In [2]: beta = 'test'

          In [3]: %who
          alpha   beta

          In [4]: %who int
          alpha

          In [5]: %who str
          beta
        """

        varlist = self.who_ls(parameter_s)
        if not varlist:
            if parameter_s:
                print('No variables match your requested type.')
            else:
                print('Interactive namespace is empty.')
            return

        # if we have variables, move on...
        count = 0
        for i in varlist:
            print(i+'\t', end=' ')
            count += 1
            if count > 8:
                count = 0
                print()
        print()

    @skip_doctest
    @line_magic
    def whos(self, parameter_s=''):
        """Like %who, but gives some extra information about each variable.

        The same type filtering of %who can be applied here.

        For all variables, the type is printed. Additionally it prints:

          - For {},[],(): their length.

          - For numpy arrays, a summary with shape, number of
            elements, typecode and size in memory.

          - Everything else: a string representation, snipping their middle if
            too long.

        Examples
        --------
        Define two variables and list them with whos::

          In [1]: alpha = 123

          In [2]: beta = 'test'

          In [3]: %whos
          Variable   Type        Data/Info
          --------------------------------
          alpha      int         123
          beta       str         test
        """

        varnames = self.who_ls(parameter_s)
        if not varnames:
            if parameter_s:
                print('No variables match your requested type.')
            else:
                print('Interactive namespace is empty.')
            return

        # if we have variables, move on...

        # for these types, show len() instead of data:
        seq_types = ['dict', 'list', 'tuple']

        # for numpy arrays, display summary info
        ndarray_type = None
        if 'numpy' in sys.modules:
            try:
                from numpy import ndarray
            except ImportError:
                pass
            else:
                ndarray_type = ndarray.__name__

        # Find all variable names and types so we can figure out column sizes

        # some types are well known and can be shorter
        abbrevs = {'IPython.core.macro.Macro' : 'Macro'}
        def type_name(v):
            tn = type(v).__name__
            return abbrevs.get(tn,tn)

        varlist = [self.shell.user_ns[n] for n in varnames]

        typelist = []
        for vv in varlist:
            tt = type_name(vv)

            if tt=='instance':
                typelist.append( abbrevs.get(str(vv.__class__),
                                             str(vv.__class__)))
            else:
                typelist.append(tt)

        # column labels and # of spaces as separator
        varlabel = 'Variable'
        typelabel = 'Type'
        datalabel = 'Data/Info'
        colsep = 3
        # variable format strings
        vformat    = "{0:<{varwidth}}{1:<{typewidth}}"
        aformat    = "%s: %s elems, type `%s`, %s bytes"
        # find the size of the columns to format the output nicely
        varwidth = max(max(map(len,varnames)), len(varlabel)) + colsep
        typewidth = max(max(map(len,typelist)), len(typelabel)) + colsep
        # table header
        print(varlabel.ljust(varwidth) + typelabel.ljust(typewidth) + \
              ' '+datalabel+'\n' + '-'*(varwidth+typewidth+len(datalabel)+1))
        # and the table itself
        kb = 1024
        Mb = 1048576  # kb**2
        for vname,var,vtype in zip(varnames,varlist,typelist):
            print(vformat.format(vname, vtype, varwidth=varwidth, typewidth=typewidth), end=' ')
            if vtype in seq_types:
                print("n="+str(len(var)))
            elif vtype == ndarray_type:
                vshape = str(var.shape).replace(',','').replace(' ','x')[1:-1]
                if vtype==ndarray_type:
                    # numpy
                    vsize  = var.size
                    vbytes = vsize*var.itemsize
                    vdtype = var.dtype

                if vbytes < 100000:
                    print(aformat % (vshape, vsize, vdtype, vbytes))
                else:
                    print(aformat % (vshape, vsize, vdtype, vbytes), end=' ')
                    if vbytes < Mb:
                        print('(%s kb)' % (vbytes/kb,))
                    else:
                        print('(%s Mb)' % (vbytes/Mb,))
            else:
                try:
                    vstr = str(var)
                except UnicodeEncodeError:
                    vstr = var.encode(DEFAULT_ENCODING,
                                      'backslashreplace')
                except:
                    vstr = "<object with id %d (str() failed)>" % id(var)
                vstr = vstr.replace('\n', '\\n')
                if len(vstr) < 50:
                    print(vstr)
                else:
                    print(vstr[:25] + "<...>" + vstr[-25:])

    @line_magic
    def reset(self, parameter_s=''):
        """Resets the namespace by removing all names defined by the user, if
        called without arguments, or by removing some types of objects, such
        as everything currently in IPython's In[] and Out[] containers (see
        the parameters for details).

        Parameters
        ----------
        -f
            force reset without asking for confirmation.
        -s
            'Soft' reset: Only clears your namespace, leaving history intact.
            References to objects may be kept. By default (without this option),
            we do a 'hard' reset, giving you a new session and removing all
            references to objects from the current session.
        --aggressive
            Try to aggressively remove modules from sys.modules ; this
            may allow you to reimport Python modules that have been updated and
            pick up changes, but can have unintended consequences.

        in
            reset input history
        out
            reset output history
        dhist
            reset directory history
        array
            reset only variables that are NumPy arrays

        See Also
        --------
        reset_selective : invoked as ``%reset_selective``

        Examples
        --------
        ::

          In [6]: a = 1

          In [7]: a
          Out[7]: 1

          In [8]: 'a' in get_ipython().user_ns
          Out[8]: True

          In [9]: %reset -f

          In [1]: 'a' in get_ipython().user_ns
          Out[1]: False

          In [2]: %reset -f in
          Flushing input history

          In [3]: %reset -f dhist in
          Flushing directory history
          Flushing input history

        Notes
        -----
        Calling this magic from clients that do not implement standard input,
        such as the ipython notebook interface, will reset the namespace
        without confirmation.
        """
        opts, args = self.parse_options(parameter_s, "sf", "aggressive", mode="list")
        if "f" in opts:
            ans = True
        else:
            try:
                ans = self.shell.ask_yes_no(
                "Once deleted, variables cannot be recovered. Proceed (y/[n])?",
                default='n')
            except StdinNotImplementedError:
                ans = True
        if not ans:
            print('Nothing done.')
            return

        if 's' in opts:                     # Soft reset
            user_ns = self.shell.user_ns
            for i in self.who_ls():
                del(user_ns[i])
        elif len(args) == 0:                # Hard reset
            self.shell.reset(new_session=False, aggressive=("aggressive" in opts))

        # reset in/out/dhist/array: previously extensinions/clearcmd.py
        ip = self.shell
        user_ns = self.shell.user_ns  # local lookup, heavily used

        for target in args:
            target = target.lower() # make matches case insensitive
            if target == 'out':
                print("Flushing output cache (%d entries)" % len(user_ns['_oh']))
                self.shell.displayhook.flush()

            elif target == 'in':
                print("Flushing input history")
                pc = self.shell.displayhook.prompt_count + 1
                for n in range(1, pc):
                    key = '_i'+repr(n)
                    user_ns.pop(key,None)
                user_ns.update(dict(_i=u'',_ii=u'',_iii=u''))
                hm = ip.history_manager
                # don't delete these, as %save and %macro depending on the
                # length of these lists to be preserved
                hm.input_hist_parsed[:] = [''] * pc
                hm.input_hist_raw[:] = [''] * pc
                # hm has internal machinery for _i,_ii,_iii, clear it out
                hm._i = hm._ii = hm._iii = hm._i00 =  u''

            elif target == 'array':
                # Support cleaning up numpy arrays
                try:
                    from numpy import ndarray
                    # This must be done with items and not iteritems because
                    # we're going to modify the dict in-place.
                    for x,val in list(user_ns.items()):
                        if isinstance(val,ndarray):
                            del user_ns[x]
                except ImportError:
                    print("reset array only works if Numpy is available.")

            elif target == 'dhist':
                print("Flushing directory history")
                del user_ns['_dh'][:]

            else:
                print("Don't know how to reset ", end=' ')
                print(target + ", please run `%reset?` for details")

        gc.collect()

    @line_magic
    def reset_selective(self, parameter_s=''):
        """Resets the namespace by removing names defined by the user.

        Input/Output history are left around in case you need them.

        %reset_selective [-f] regex

        No action is taken if regex is not included

        Options
          -f : force reset without asking for confirmation.

        See Also
        --------
        reset : invoked as ``%reset``

        Examples
        --------
        We first fully reset the namespace so your output looks identical to
        this example for pedagogical reasons; in practice you do not need a
        full reset::

          In [1]: %reset -f

        Now, with a clean namespace we can make a few variables and use
        ``%reset_selective`` to only delete names that match our regexp::

          In [2]: a=1; b=2; c=3; b1m=4; b2m=5; b3m=6; b4m=7; b2s=8

          In [3]: who_ls
          Out[3]: ['a', 'b', 'b1m', 'b2m', 'b2s', 'b3m', 'b4m', 'c']

          In [4]: %reset_selective -f b[2-3]m

          In [5]: who_ls
          Out[5]: ['a', 'b', 'b1m', 'b2s', 'b4m', 'c']

          In [6]: %reset_selective -f d

          In [7]: who_ls
          Out[7]: ['a', 'b', 'b1m', 'b2s', 'b4m', 'c']

          In [8]: %reset_selective -f c

          In [9]: who_ls
          Out[9]: ['a', 'b', 'b1m', 'b2s', 'b4m']

          In [10]: %reset_selective -f b

          In [11]: who_ls
          Out[11]: ['a']

        Notes
        -----
        Calling this magic from clients that do not implement standard input,
        such as the ipython notebook interface, will reset the namespace
        without confirmation.
        """

        opts, regex = self.parse_options(parameter_s,'f')

        if 'f' in opts:
            ans = True
        else:
            try:
                ans = self.shell.ask_yes_no(
                "Once deleted, variables cannot be recovered. Proceed (y/[n])? ",
                default='n')
            except StdinNotImplementedError:
                ans = True
        if not ans:
            print('Nothing done.')
            return
        user_ns = self.shell.user_ns
        if not regex:
            print('No regex pattern specified. Nothing done.')
            return
        else:
            try:
                m = re.compile(regex)
            except TypeError as e:
                raise TypeError('regex must be a string or compiled pattern') from e
            for i in self.who_ls():
                if m.search(i):
                    del(user_ns[i])

    @line_magic
    def xdel(self, parameter_s=''):
        """Delete a variable, trying to clear it from anywhere that
        IPython's machinery has references to it. By default, this uses
        the identity of the named object in the user namespace to remove
        references held under other names. The object is also removed
        from the output history.

        Options
          -n : Delete the specified name from all namespaces, without
          checking their identity.
        """
        opts, varname = self.parse_options(parameter_s,'n')
        try:
            self.shell.del_var(varname, ('n' in opts))
        except (NameError, ValueError) as e:
            print(type(e).__name__ +": "+ str(e))