
# === NexusCore/tools\exports\export_20250803_114325\combined_105.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\distlib\wheel.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2023 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
from __future__ import unicode_literals

import base64
import codecs
import datetime
from email import message_from_file
import hashlib
import json
import logging
import os
import posixpath
import re
import shutil
import sys
import tempfile
import zipfile

from . import __version__, DistlibException
from .compat import sysconfig, ZipFile, fsdecode, text_type, filter
from .database import InstalledDistribution
from .metadata import Metadata, WHEEL_METADATA_FILENAME, LEGACY_METADATA_FILENAME
from .util import (FileOperator, convert_path, CSVReader, CSVWriter, Cache, cached_property, get_cache_base,
                   read_exports, tempdir, get_platform)
from .version import NormalizedVersion, UnsupportedVersionError

logger = logging.getLogger(__name__)

cache = None  # created when needed

if hasattr(sys, 'pypy_version_info'):  # pragma: no cover
    IMP_PREFIX = 'pp'
elif sys.platform.startswith('java'):  # pragma: no cover
    IMP_PREFIX = 'jy'
elif sys.platform == 'cli':  # pragma: no cover
    IMP_PREFIX = 'ip'
else:
    IMP_PREFIX = 'cp'

VER_SUFFIX = sysconfig.get_config_var('py_version_nodot')
if not VER_SUFFIX:  # pragma: no cover
    VER_SUFFIX = '%s%s' % sys.version_info[:2]
PYVER = 'py' + VER_SUFFIX
IMPVER = IMP_PREFIX + VER_SUFFIX

ARCH = get_platform().replace('-', '_').replace('.', '_')

ABI = sysconfig.get_config_var('SOABI')
if ABI and ABI.startswith('cpython-'):
    ABI = ABI.replace('cpython-', 'cp').split('-')[0]
else:

    def _derive_abi():
        parts = ['cp', VER_SUFFIX]
        if sysconfig.get_config_var('Py_DEBUG'):
            parts.append('d')
        if IMP_PREFIX == 'cp':
            vi = sys.version_info[:2]
            if vi < (3, 8):
                wpm = sysconfig.get_config_var('WITH_PYMALLOC')
                if wpm is None:
                    wpm = True
                if wpm:
                    parts.append('m')
                if vi < (3, 3):
                    us = sysconfig.get_config_var('Py_UNICODE_SIZE')
                    if us == 4 or (us is None and sys.maxunicode == 0x10FFFF):
                        parts.append('u')
        return ''.join(parts)

    ABI = _derive_abi()
    del _derive_abi

FILENAME_RE = re.compile(
    r'''
(?P<nm>[^-]+)
-(?P<vn>\d+[^-]*)
(-(?P<bn>\d+[^-]*))?
-(?P<py>\w+\d+(\.\w+\d+)*)
-(?P<bi>\w+)
-(?P<ar>\w+(\.\w+)*)
\.whl$
''', re.IGNORECASE | re.VERBOSE)

NAME_VERSION_RE = re.compile(r'''
(?P<nm>[^-]+)
-(?P<vn>\d+[^-]*)
(-(?P<bn>\d+[^-]*))?$
''', re.IGNORECASE | re.VERBOSE)

SHEBANG_RE = re.compile(br'\s*#![^\r\n]*')
SHEBANG_DETAIL_RE = re.compile(br'^(\s*#!("[^"]+"|\S+))\s+(.*)$')
SHEBANG_PYTHON = b'#!python'
SHEBANG_PYTHONW = b'#!pythonw'

if os.sep == '/':
    to_posix = lambda o: o
else:
    to_posix = lambda o: o.replace(os.sep, '/')

if sys.version_info[0] < 3:
    import imp
else:
    imp = None
    import importlib.machinery
    import importlib.util


def _get_suffixes():
    if imp:
        return [s[0] for s in imp.get_suffixes()]
    else:
        return importlib.machinery.EXTENSION_SUFFIXES


def _load_dynamic(name, path):
    # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    if imp:
        return imp.load_dynamic(name, path)
    else:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module


class Mounter(object):

    def __init__(self):
        self.impure_wheels = {}
        self.libs = {}

    def add(self, pathname, extensions):
        self.impure_wheels[pathname] = extensions
        self.libs.update(extensions)

    def remove(self, pathname):
        extensions = self.impure_wheels.pop(pathname)
        for k, v in extensions:
            if k in self.libs:
                del self.libs[k]

    def find_module(self, fullname, path=None):
        if fullname in self.libs:
            result = self
        else:
            result = None
        return result

    def load_module(self, fullname):
        if fullname in sys.modules:
            result = sys.modules[fullname]
        else:
            if fullname not in self.libs:
                raise ImportError('unable to find extension for %s' % fullname)
            result = _load_dynamic(fullname, self.libs[fullname])
            result.__loader__ = self
            parts = fullname.rsplit('.', 1)
            if len(parts) > 1:
                result.__package__ = parts[0]
        return result


_hook = Mounter()


class Wheel(object):
    """
    Class to build and install from Wheel files (PEP 427).
    """

    wheel_version = (1, 1)
    hash_kind = 'sha256'

    def __init__(self, filename=None, sign=False, verify=False):
        """
        Initialise an instance using a (valid) filename.
        """
        self.sign = sign
        self.should_verify = verify
        self.buildver = ''
        self.pyver = [PYVER]
        self.abi = ['none']
        self.arch = ['any']
        self.dirname = os.getcwd()
        if filename is None:
            self.name = 'dummy'
            self.version = '0.1'
            self._filename = self.filename
        else:
            m = NAME_VERSION_RE.match(filename)
            if m:
                info = m.groupdict('')
                self.name = info['nm']
                # Reinstate the local version separator
                self.version = info['vn'].replace('_', '-')
                self.buildver = info['bn']
                self._filename = self.filename
            else:
                dirname, filename = os.path.split(filename)
                m = FILENAME_RE.match(filename)
                if not m:
                    raise DistlibException('Invalid name or '
                                           'filename: %r' % filename)
                if dirname:
                    self.dirname = os.path.abspath(dirname)
                self._filename = filename
                info = m.groupdict('')
                self.name = info['nm']
                self.version = info['vn']
                self.buildver = info['bn']
                self.pyver = info['py'].split('.')
                self.abi = info['bi'].split('.')
                self.arch = info['ar'].split('.')

    @property
    def filename(self):
        """
        Build and return a filename from the various components.
        """
        if self.buildver:
            buildver = '-' + self.buildver
        else:
            buildver = ''
        pyver = '.'.join(self.pyver)
        abi = '.'.join(self.abi)
        arch = '.'.join(self.arch)
        # replace - with _ as a local version separator
        version = self.version.replace('-', '_')
        return '%s-%s%s-%s-%s-%s.whl' % (self.name, version, buildver, pyver, abi, arch)

    @property
    def exists(self):
        path = os.path.join(self.dirname, self.filename)
        return os.path.isfile(path)

    @property
    def tags(self):
        for pyver in self.pyver:
            for abi in self.abi:
                for arch in self.arch:
                    yield pyver, abi, arch

    @cached_property
    def metadata(self):
        pathname = os.path.join(self.dirname, self.filename)
        name_ver = '%s-%s' % (self.name, self.version)
        info_dir = '%s.dist-info' % name_ver
        wrapper = codecs.getreader('utf-8')
        with ZipFile(pathname, 'r') as zf:
            self.get_wheel_metadata(zf)
            # wv = wheel_metadata['Wheel-Version'].split('.', 1)
            # file_version = tuple([int(i) for i in wv])
            # if file_version < (1, 1):
            # fns = [WHEEL_METADATA_FILENAME, METADATA_FILENAME,
            # LEGACY_METADATA_FILENAME]
            # else:
            # fns = [WHEEL_METADATA_FILENAME, METADATA_FILENAME]
            fns = [WHEEL_METADATA_FILENAME, LEGACY_METADATA_FILENAME]
            result = None
            for fn in fns:
                try:
                    metadata_filename = posixpath.join(info_dir, fn)
                    with zf.open(metadata_filename) as bf:
                        wf = wrapper(bf)
                        result = Metadata(fileobj=wf)
                        if result:
                            break
                except KeyError:
                    pass
            if not result:
                raise ValueError('Invalid wheel, because metadata is '
                                 'missing: looked in %s' % ', '.join(fns))
        return result

    def get_wheel_metadata(self, zf):
        name_ver = '%s-%s' % (self.name, self.version)
        info_dir = '%s.dist-info' % name_ver
        metadata_filename = posixpath.join(info_dir, 'WHEEL')
        with zf.open(metadata_filename) as bf:
            wf = codecs.getreader('utf-8')(bf)
            message = message_from_file(wf)
        return dict(message)

    @cached_property
    def info(self):
        pathname = os.path.join(self.dirname, self.filename)
        with ZipFile(pathname, 'r') as zf:
            result = self.get_wheel_metadata(zf)
        return result

    def process_shebang(self, data):
        m = SHEBANG_RE.match(data)
        if m:
            end = m.end()
            shebang, data_after_shebang = data[:end], data[end:]
            # Preserve any arguments after the interpreter
            if b'pythonw' in shebang.lower():
                shebang_python = SHEBANG_PYTHONW
            else:
                shebang_python = SHEBANG_PYTHON
            m = SHEBANG_DETAIL_RE.match(shebang)
            if m:
                args = b' ' + m.groups()[-1]
            else:
                args = b''
            shebang = shebang_python + args
            data = shebang + data_after_shebang
        else:
            cr = data.find(b'\r')
            lf = data.find(b'\n')
            if cr < 0 or cr > lf:
                term = b'\n'
            else:
                if data[cr:cr + 2] == b'\r\n':
                    term = b'\r\n'
                else:
                    term = b'\r'
            data = SHEBANG_PYTHON + term + data
        return data

    def get_hash(self, data, hash_kind=None):
        if hash_kind is None:
            hash_kind = self.hash_kind
        try:
            hasher = getattr(hashlib, hash_kind)
        except AttributeError:
            raise DistlibException('Unsupported hash algorithm: %r' % hash_kind)
        result = hasher(data).digest()
        result = base64.urlsafe_b64encode(result).rstrip(b'=').decode('ascii')
        return hash_kind, result

    def write_record(self, records, record_path, archive_record_path):
        records = list(records)  # make a copy, as mutated
        records.append((archive_record_path, '', ''))
        with CSVWriter(record_path) as writer:
            for row in records:
                writer.writerow(row)

    def write_records(self, info, libdir, archive_paths):
        records = []
        distinfo, info_dir = info
        # hasher = getattr(hashlib, self.hash_kind)
        for ap, p in archive_paths:
            with open(p, 'rb') as f:
                data = f.read()
            digest = '%s=%s' % self.get_hash(data)
            size = os.path.getsize(p)
            records.append((ap, digest, size))

        p = os.path.join(distinfo, 'RECORD')
        ap = to_posix(os.path.join(info_dir, 'RECORD'))
        self.write_record(records, p, ap)
        archive_paths.append((ap, p))

    def build_zip(self, pathname, archive_paths):
        with ZipFile(pathname, 'w', zipfile.ZIP_DEFLATED) as zf:
            for ap, p in archive_paths:
                logger.debug('Wrote %s to %s in wheel', p, ap)
                zf.write(p, ap)

    def build(self, paths, tags=None, wheel_version=None):
        """
        Build a wheel from files in specified paths, and use any specified tags
        when determining the name of the wheel.
        """
        if tags is None:
            tags = {}

        libkey = list(filter(lambda o: o in paths, ('purelib', 'platlib')))[0]
        if libkey == 'platlib':
            is_pure = 'false'
            default_pyver = [IMPVER]
            default_abi = [ABI]
            default_arch = [ARCH]
        else:
            is_pure = 'true'
            default_pyver = [PYVER]
            default_abi = ['none']
            default_arch = ['any']

        self.pyver = tags.get('pyver', default_pyver)
        self.abi = tags.get('abi', default_abi)
        self.arch = tags.get('arch', default_arch)

        libdir = paths[libkey]

        name_ver = '%s-%s' % (self.name, self.version)
        data_dir = '%s.data' % name_ver
        info_dir = '%s.dist-info' % name_ver

        archive_paths = []

        # First, stuff which is not in site-packages
        for key in ('data', 'headers', 'scripts'):
            if key not in paths:
                continue
            path = paths[key]
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for fn in files:
                        p = fsdecode(os.path.join(root, fn))
                        rp = os.path.relpath(p, path)
                        ap = to_posix(os.path.join(data_dir, key, rp))
                        archive_paths.append((ap, p))
                        if key == 'scripts' and not p.endswith('.exe'):
                            with open(p, 'rb') as f:
                                data = f.read()
                            data = self.process_shebang(data)
                            with open(p, 'wb') as f:
                                f.write(data)

        # Now, stuff which is in site-packages, other than the
        # distinfo stuff.
        path = libdir
        distinfo = None
        for root, dirs, files in os.walk(path):
            if root == path:
                # At the top level only, save distinfo for later
                # and skip it for now
                for i, dn in enumerate(dirs):
                    dn = fsdecode(dn)
                    if dn.endswith('.dist-info'):
                        distinfo = os.path.join(root, dn)
                        del dirs[i]
                        break
                assert distinfo, '.dist-info directory expected, not found'

            for fn in files:
                # comment out next suite to leave .pyc files in
                if fsdecode(fn).endswith(('.pyc', '.pyo')):
                    continue
                p = os.path.join(root, fn)
                rp = to_posix(os.path.relpath(p, path))
                archive_paths.append((rp, p))

        # Now distinfo. Assumed to be flat, i.e. os.listdir is enough.
        files = os.listdir(distinfo)
        for fn in files:
            if fn not in ('RECORD', 'INSTALLER', 'SHARED', 'WHEEL'):
                p = fsdecode(os.path.join(distinfo, fn))
                ap = to_posix(os.path.join(info_dir, fn))
                archive_paths.append((ap, p))

        wheel_metadata = [
            'Wheel-Version: %d.%d' % (wheel_version or self.wheel_version),
            'Generator: distlib %s' % __version__,
            'Root-Is-Purelib: %s' % is_pure,
        ]
        for pyver, abi, arch in self.tags:
            wheel_metadata.append('Tag: %s-%s-%s' % (pyver, abi, arch))
        p = os.path.join(distinfo, 'WHEEL')
        with open(p, 'w') as f:
            f.write('\n'.join(wheel_metadata))
        ap = to_posix(os.path.join(info_dir, 'WHEEL'))
        archive_paths.append((ap, p))

        # sort the entries by archive path. Not needed by any spec, but it
        # keeps the archive listing and RECORD tidier than they would otherwise
        # be. Use the number of path segments to keep directory entries together,
        # and keep the dist-info stuff at the end.
        def sorter(t):
            ap = t[0]
            n = ap.count('/')
            if '.dist-info' in ap:
                n += 10000
            return (n, ap)

        archive_paths = sorted(archive_paths, key=sorter)

        # Now, at last, RECORD.
        # Paths in here are archive paths - nothing else makes sense.
        self.write_records((distinfo, info_dir), libdir, archive_paths)
        # Now, ready to build the zip file
        pathname = os.path.join(self.dirname, self.filename)
        self.build_zip(pathname, archive_paths)
        return pathname

    def skip_entry(self, arcname):
        """
        Determine whether an archive entry should be skipped when verifying
        or installing.
        """
        # The signature file won't be in RECORD,
        # and we  don't currently don't do anything with it
        # We also skip directories, as they won't be in RECORD
        # either. See:
        #
        # https://github.com/pypa/wheel/issues/294
        # https://github.com/pypa/wheel/issues/287
        # https://github.com/pypa/wheel/pull/289
        #
        return arcname.endswith(('/', '/RECORD.jws'))

    def install(self, paths, maker, **kwargs):
        """
        Install a wheel to the specified paths. If kwarg ``warner`` is
        specified, it should be a callable, which will be called with two
        tuples indicating the wheel version of this software and the wheel
        version in the file, if there is a discrepancy in the versions.
        This can be used to issue any warnings to raise any exceptions.
        If kwarg ``lib_only`` is True, only the purelib/platlib files are
        installed, and the headers, scripts, data and dist-info metadata are
        not written. If kwarg ``bytecode_hashed_invalidation`` is True, written
        bytecode will try to use file-hash based invalidation (PEP-552) on
        supported interpreter versions (CPython 3.7+).

        The return value is a :class:`InstalledDistribution` instance unless
        ``options.lib_only`` is True, in which case the return value is ``None``.
        """

        dry_run = maker.dry_run
        warner = kwargs.get('warner')
        lib_only = kwargs.get('lib_only', False)
        bc_hashed_invalidation = kwargs.get('bytecode_hashed_invalidation', False)

        pathname = os.path.join(self.dirname, self.filename)
        name_ver = '%s-%s' % (self.name, self.version)
        data_dir = '%s.data' % name_ver
        info_dir = '%s.dist-info' % name_ver

        metadata_name = posixpath.join(info_dir, LEGACY_METADATA_FILENAME)
        wheel_metadata_name = posixpath.join(info_dir, 'WHEEL')
        record_name = posixpath.join(info_dir, 'RECORD')

        wrapper = codecs.getreader('utf-8')

        with ZipFile(pathname, 'r') as zf:
            with zf.open(wheel_metadata_name) as bwf:
                wf = wrapper(bwf)
                message = message_from_file(wf)
            wv = message['Wheel-Version'].split('.', 1)
            file_version = tuple([int(i) for i in wv])
            if (file_version != self.wheel_version) and warner:
                warner(self.wheel_version, file_version)

            if message['Root-Is-Purelib'] == 'true':
                libdir = paths['purelib']
            else:
                libdir = paths['platlib']

            records = {}
            with zf.open(record_name) as bf:
                with CSVReader(stream=bf) as reader:
                    for row in reader:
                        p = row[0]
                        records[p] = row

            data_pfx = posixpath.join(data_dir, '')
            info_pfx = posixpath.join(info_dir, '')
            script_pfx = posixpath.join(data_dir, 'scripts', '')

            # make a new instance rather than a copy of maker's,
            # as we mutate it
            fileop = FileOperator(dry_run=dry_run)
            fileop.record = True  # so we can rollback if needed

            bc = not sys.dont_write_bytecode  # Double negatives. Lovely!

            outfiles = []  # for RECORD writing

            # for script copying/shebang processing
            workdir = tempfile.mkdtemp()
            # set target dir later
            # we default add_launchers to False, as the
            # Python Launcher should be used instead
            maker.source_dir = workdir
            maker.target_dir = None
            try:
                for zinfo in zf.infolist():
                    arcname = zinfo.filename
                    if isinstance(arcname, text_type):
                        u_arcname = arcname
                    else:
                        u_arcname = arcname.decode('utf-8')
                    if self.skip_entry(u_arcname):
                        continue
                    row = records[u_arcname]
                    if row[2] and str(zinfo.file_size) != row[2]:
                        raise DistlibException('size mismatch for '
                                               '%s' % u_arcname)
                    if row[1]:
                        kind, value = row[1].split('=', 1)
                        with zf.open(arcname) as bf:
                            data = bf.read()
                        _, digest = self.get_hash(data, kind)
                        if digest != value:
                            raise DistlibException('digest mismatch for '
                                                   '%s' % arcname)

                    if lib_only and u_arcname.startswith((info_pfx, data_pfx)):
                        logger.debug('lib_only: skipping %s', u_arcname)
                        continue
                    is_script = (u_arcname.startswith(script_pfx) and not u_arcname.endswith('.exe'))

                    if u_arcname.startswith(data_pfx):
                        _, where, rp = u_arcname.split('/', 2)
                        outfile = os.path.join(paths[where], convert_path(rp))
                    else:
                        # meant for site-packages.
                        if u_arcname in (wheel_metadata_name, record_name):
                            continue
                        outfile = os.path.join(libdir, convert_path(u_arcname))
                    if not is_script:
                        with zf.open(arcname) as bf:
                            fileop.copy_stream(bf, outfile)
                        # Issue #147: permission bits aren't preserved. Using
                        # zf.extract(zinfo, libdir) should have worked, but didn't,
                        # see https://www.thetopsites.net/article/53834422.shtml
                        # So ... manually preserve permission bits as given in zinfo
                        if os.name == 'posix':
                            # just set the normal permission bits
                            os.chmod(outfile, (zinfo.external_attr >> 16) & 0x1FF)
                        outfiles.append(outfile)
                        # Double check the digest of the written file
                        if not dry_run and row[1]:
                            with open(outfile, 'rb') as bf:
                                data = bf.read()
                                _, newdigest = self.get_hash(data, kind)
                                if newdigest != digest:
                                    raise DistlibException('digest mismatch '
                                                           'on write for '
                                                           '%s' % outfile)
                        if bc and outfile.endswith('.py'):
                            try:
                                pyc = fileop.byte_compile(outfile, hashed_invalidation=bc_hashed_invalidation)
                                outfiles.append(pyc)
                            except Exception:
                                # Don't give up if byte-compilation fails,
                                # but log it and perhaps warn the user
                                logger.warning('Byte-compilation failed', exc_info=True)
                    else:
                        fn = os.path.basename(convert_path(arcname))
                        workname = os.path.join(workdir, fn)
                        with zf.open(arcname) as bf:
                            fileop.copy_stream(bf, workname)

                        dn, fn = os.path.split(outfile)
                        maker.target_dir = dn
                        filenames = maker.make(fn)
                        fileop.set_executable_mode(filenames)
                        outfiles.extend(filenames)

                if lib_only:
                    logger.debug('lib_only: returning None')
                    dist = None
                else:
                    # Generate scripts

                    # Try to get pydist.json so we can see if there are
                    # any commands to generate. If this fails (e.g. because
                    # of a legacy wheel), log a warning but don't give up.
                    commands = None
                    file_version = self.info['Wheel-Version']
                    if file_version == '1.0':
                        # Use legacy info
                        ep = posixpath.join(info_dir, 'entry_points.txt')
                        try:
                            with zf.open(ep) as bwf:
                                epdata = read_exports(bwf)
                            commands = {}
                            for key in ('console', 'gui'):
                                k = '%s_scripts' % key
                                if k in epdata:
                                    commands['wrap_%s' % key] = d = {}
                                    for v in epdata[k].values():
                                        s = '%s:%s' % (v.prefix, v.suffix)
                                        if v.flags:
                                            s += ' [%s]' % ','.join(v.flags)
                                        d[v.name] = s
                        except Exception:
                            logger.warning('Unable to read legacy script '
                                           'metadata, so cannot generate '
                                           'scripts')
                    else:
                        try:
                            with zf.open(metadata_name) as bwf:
                                wf = wrapper(bwf)
                                commands = json.load(wf).get('extensions')
                                if commands:
                                    commands = commands.get('python.commands')
                        except Exception:
                            logger.warning('Unable to read JSON metadata, so '
                                           'cannot generate scripts')
                    if commands:
                        console_scripts = commands.get('wrap_console', {})
                        gui_scripts = commands.get('wrap_gui', {})
                        if console_scripts or gui_scripts:
                            script_dir = paths.get('scripts', '')
                            if not os.path.isdir(script_dir):
                                raise ValueError('Valid script path not '
                                                 'specified')
                            maker.target_dir = script_dir
                            for k, v in console_scripts.items():
                                script = '%s = %s' % (k, v)
                                filenames = maker.make(script)
                                fileop.set_executable_mode(filenames)

                            if gui_scripts:
                                options = {'gui': True}
                                for k, v in gui_scripts.items():
                                    script = '%s = %s' % (k, v)
                                    filenames = maker.make(script, options)
                                    fileop.set_executable_mode(filenames)

                    p = os.path.join(libdir, info_dir)
                    dist = InstalledDistribution(p)

                    # Write SHARED
                    paths = dict(paths)  # don't change passed in dict
                    del paths['purelib']
                    del paths['platlib']
                    paths['lib'] = libdir
                    p = dist.write_shared_locations(paths, dry_run)
                    if p:
                        outfiles.append(p)

                    # Write RECORD
                    dist.write_installed_files(outfiles, paths['prefix'], dry_run)
                return dist
            except Exception:  # pragma: no cover
                logger.exception('installation failed.')
                fileop.rollback()
                raise
            finally:
                shutil.rmtree(workdir)

    def _get_dylib_cache(self):
        global cache
        if cache is None:
            # Use native string to avoid issues on 2.x: see Python #20140.
            base = os.path.join(get_cache_base(), str('dylib-cache'), '%s.%s' % sys.version_info[:2])
            cache = Cache(base)
        return cache

    def _get_extensions(self):
        pathname = os.path.join(self.dirname, self.filename)
        name_ver = '%s-%s' % (self.name, self.version)
        info_dir = '%s.dist-info' % name_ver
        arcname = posixpath.join(info_dir, 'EXTENSIONS')
        wrapper = codecs.getreader('utf-8')
        result = []
        with ZipFile(pathname, 'r') as zf:
            try:
                with zf.open(arcname) as bf:
                    wf = wrapper(bf)
                    extensions = json.load(wf)
                    cache = self._get_dylib_cache()
                    prefix = cache.prefix_to_dir(self.filename, use_abspath=False)
                    cache_base = os.path.join(cache.base, prefix)
                    if not os.path.isdir(cache_base):
                        os.makedirs(cache_base)
                    for name, relpath in extensions.items():
                        dest = os.path.join(cache_base, convert_path(relpath))
                        if not os.path.exists(dest):
                            extract = True
                        else:
                            file_time = os.stat(dest).st_mtime
                            file_time = datetime.datetime.fromtimestamp(file_time)
                            info = zf.getinfo(relpath)
                            wheel_time = datetime.datetime(*info.date_time)
                            extract = wheel_time > file_time
                        if extract:
                            zf.extract(relpath, cache_base)
                        result.append((name, dest))
            except KeyError:
                pass
        return result

    def is_compatible(self):
        """
        Determine if a wheel is compatible with the running system.
        """
        return is_compatible(self)

    def is_mountable(self):
        """
        Determine if a wheel is asserted as mountable by its metadata.
        """
        return True  # for now - metadata details TBD

    def mount(self, append=False):
        pathname = os.path.abspath(os.path.join(self.dirname, self.filename))
        if not self.is_compatible():
            msg = 'Wheel %s not compatible with this Python.' % pathname
            raise DistlibException(msg)
        if not self.is_mountable():
            msg = 'Wheel %s is marked as not mountable.' % pathname
            raise DistlibException(msg)
        if pathname in sys.path:
            logger.debug('%s already in path', pathname)
        else:
            if append:
                sys.path.append(pathname)
            else:
                sys.path.insert(0, pathname)
            extensions = self._get_extensions()
            if extensions:
                if _hook not in sys.meta_path:
                    sys.meta_path.append(_hook)
                _hook.add(pathname, extensions)

    def unmount(self):
        pathname = os.path.abspath(os.path.join(self.dirname, self.filename))
        if pathname not in sys.path:
            logger.debug('%s not in path', pathname)
        else:
            sys.path.remove(pathname)
            if pathname in _hook.impure_wheels:
                _hook.remove(pathname)
            if not _hook.impure_wheels:
                if _hook in sys.meta_path:
                    sys.meta_path.remove(_hook)

    def verify(self):
        pathname = os.path.join(self.dirname, self.filename)
        name_ver = '%s-%s' % (self.name, self.version)
        # data_dir = '%s.data' % name_ver
        info_dir = '%s.dist-info' % name_ver

        # metadata_name = posixpath.join(info_dir, LEGACY_METADATA_FILENAME)
        wheel_metadata_name = posixpath.join(info_dir, 'WHEEL')
        record_name = posixpath.join(info_dir, 'RECORD')

        wrapper = codecs.getreader('utf-8')

        with ZipFile(pathname, 'r') as zf:
            with zf.open(wheel_metadata_name) as bwf:
                wf = wrapper(bwf)
                message_from_file(wf)
            # wv = message['Wheel-Version'].split('.', 1)
            # file_version = tuple([int(i) for i in wv])
            # TODO version verification

            records = {}
            with zf.open(record_name) as bf:
                with CSVReader(stream=bf) as reader:
                    for row in reader:
                        p = row[0]
                        records[p] = row

            for zinfo in zf.infolist():
                arcname = zinfo.filename
                if isinstance(arcname, text_type):
                    u_arcname = arcname
                else:
                    u_arcname = arcname.decode('utf-8')
                # See issue #115: some wheels have .. in their entries, but
                # in the filename ... e.g. __main__..py ! So the check is
                # updated to look for .. in the directory portions
                p = u_arcname.split('/')
                if '..' in p:
                    raise DistlibException('invalid entry in '
                                           'wheel: %r' % u_arcname)

                if self.skip_entry(u_arcname):
                    continue
                row = records[u_arcname]
                if row[2] and str(zinfo.file_size) != row[2]:
                    raise DistlibException('size mismatch for '
                                           '%s' % u_arcname)
                if row[1]:
                    kind, value = row[1].split('=', 1)
                    with zf.open(arcname) as bf:
                        data = bf.read()
                    _, digest = self.get_hash(data, kind)
                    if digest != value:
                        raise DistlibException('digest mismatch for '
                                               '%s' % arcname)

    def update(self, modifier, dest_dir=None, **kwargs):
        """
        Update the contents of a wheel in a generic way. The modifier should
        be a callable which expects a dictionary argument: its keys are
        archive-entry paths, and its values are absolute filesystem paths
        where the contents the corresponding archive entries can be found. The
        modifier is free to change the contents of the files pointed to, add
        new entries and remove entries, before returning. This method will
        extract the entire contents of the wheel to a temporary location, call
        the modifier, and then use the passed (and possibly updated)
        dictionary to write a new wheel. If ``dest_dir`` is specified, the new
        wheel is written there -- otherwise, the original wheel is overwritten.

        The modifier should return True if it updated the wheel, else False.
        This method returns the same value the modifier returns.
        """

        def get_version(path_map, info_dir):
            version = path = None
            key = '%s/%s' % (info_dir, LEGACY_METADATA_FILENAME)
            if key not in path_map:
                key = '%s/PKG-INFO' % info_dir
            if key in path_map:
                path = path_map[key]
                version = Metadata(path=path).version
            return version, path

        def update_version(version, path):
            updated = None
            try:
                NormalizedVersion(version)
                i = version.find('-')
                if i < 0:
                    updated = '%s+1' % version
                else:
                    parts = [int(s) for s in version[i + 1:].split('.')]
                    parts[-1] += 1
                    updated = '%s+%s' % (version[:i], '.'.join(str(i) for i in parts))
            except UnsupportedVersionError:
                logger.debug('Cannot update non-compliant (PEP-440) '
                             'version %r', version)
            if updated:
                md = Metadata(path=path)
                md.version = updated
                legacy = path.endswith(LEGACY_METADATA_FILENAME)
                md.write(path=path, legacy=legacy)
                logger.debug('Version updated from %r to %r', version, updated)

        pathname = os.path.join(self.dirname, self.filename)
        name_ver = '%s-%s' % (self.name, self.version)
        info_dir = '%s.dist-info' % name_ver
        record_name = posixpath.join(info_dir, 'RECORD')
        with tempdir() as workdir:
            with ZipFile(pathname, 'r') as zf:
                path_map = {}
                for zinfo in zf.infolist():
                    arcname = zinfo.filename
                    if isinstance(arcname, text_type):
                        u_arcname = arcname
                    else:
                        u_arcname = arcname.decode('utf-8')
                    if u_arcname == record_name:
                        continue
                    if '..' in u_arcname:
                        raise DistlibException('invalid entry in '
                                               'wheel: %r' % u_arcname)
                    zf.extract(zinfo, workdir)
                    path = os.path.join(workdir, convert_path(u_arcname))
                    path_map[u_arcname] = path

            # Remember the version.
            original_version, _ = get_version(path_map, info_dir)
            # Files extracted. Call the modifier.
            modified = modifier(path_map, **kwargs)
            if modified:
                # Something changed - need to build a new wheel.
                current_version, path = get_version(path_map, info_dir)
                if current_version and (current_version == original_version):
                    # Add or update local version to signify changes.
                    update_version(current_version, path)
                # Decide where the new wheel goes.
                if dest_dir is None:
                    fd, newpath = tempfile.mkstemp(suffix='.whl', prefix='wheel-update-', dir=workdir)
                    os.close(fd)
                else:
                    if not os.path.isdir(dest_dir):
                        raise DistlibException('Not a directory: %r' % dest_dir)
                    newpath = os.path.join(dest_dir, self.filename)
                archive_paths = list(path_map.items())
                distinfo = os.path.join(workdir, info_dir)
                info = distinfo, info_dir
                self.write_records(info, workdir, archive_paths)
                self.build_zip(newpath, archive_paths)
                if dest_dir is None:
                    shutil.copyfile(newpath, pathname)
        return modified


def _get_glibc_version():
    import platform
    ver = platform.libc_ver()
    result = []
    if ver[0] == 'glibc':
        for s in ver[1].split('.'):
            result.append(int(s) if s.isdigit() else 0)
        result = tuple(result)
    return result


def compatible_tags():
    """
    Return (pyver, abi, arch) tuples compatible with this Python.
    """
    class _Version:
        def __init__(self, major, minor):
            self.major = major
            self.major_minor = (major, minor)
            self.string = ''.join((str(major), str(minor)))

        def __str__(self):
            return self.string


    versions = [
        _Version(sys.version_info.major, minor_version)
        for minor_version in range(sys.version_info.minor, -1, -1)
    ]
    abis = []
    for suffix in _get_suffixes():
        if suffix.startswith('.abi'):
            abis.append(suffix.split('.', 2)[1])
    abis.sort()
    if ABI != 'none':
        abis.insert(0, ABI)
    abis.append('none')
    result = []

    arches = [ARCH]
    if sys.platform == 'darwin':
        m = re.match(r'(\w+)_(\d+)_(\d+)_(\w+)$', ARCH)
        if m:
            name, major, minor, arch = m.groups()
            minor = int(minor)
            matches = [arch]
            if arch in ('i386', 'ppc'):
                matches.append('fat')
            if arch in ('i386', 'ppc', 'x86_64'):
                matches.append('fat3')
            if arch in ('ppc64', 'x86_64'):
                matches.append('fat64')
            if arch in ('i386', 'x86_64'):
                matches.append('intel')
            if arch in ('i386', 'x86_64', 'intel', 'ppc', 'ppc64'):
                matches.append('universal')
            while minor >= 0:
                for match in matches:
                    s = '%s_%s_%s_%s' % (name, major, minor, match)
                    if s != ARCH:  # already there
                        arches.append(s)
                minor -= 1

    # Most specific - our Python version, ABI and arch
    for i, version_object in enumerate(versions):
        version = str(version_object)
        add_abis = []

        if i == 0:
            add_abis = abis

        if IMP_PREFIX == 'cp' and version_object.major_minor >= (3, 2):
            limited_api_abi = 'abi' + str(version_object.major)
            if limited_api_abi not in add_abis:
                add_abis.append(limited_api_abi)

        for abi in add_abis:
            for arch in arches:
                result.append((''.join((IMP_PREFIX, version)), abi, arch))
                # manylinux
                if abi != 'none' and sys.platform.startswith('linux'):
                    arch = arch.replace('linux_', '')
                    parts = _get_glibc_version()
                    if len(parts) == 2:
                        if parts >= (2, 5):
                            result.append((''.join((IMP_PREFIX, version)), abi, 'manylinux1_%s' % arch))
                        if parts >= (2, 12):
                            result.append((''.join((IMP_PREFIX, version)), abi, 'manylinux2010_%s' % arch))
                        if parts >= (2, 17):
                            result.append((''.join((IMP_PREFIX, version)), abi, 'manylinux2014_%s' % arch))
                        result.append((''.join(
                            (IMP_PREFIX, version)), abi, 'manylinux_%s_%s_%s' % (parts[0], parts[1], arch)))

    # where no ABI / arch dependency, but IMP_PREFIX dependency
    for i, version_object in enumerate(versions):
        version = str(version_object)
        result.append((''.join((IMP_PREFIX, version)), 'none', 'any'))
        if i == 0:
            result.append((''.join((IMP_PREFIX, version[0])), 'none', 'any'))

    # no IMP_PREFIX, ABI or arch dependency
    for i, version_object in enumerate(versions):
        version = str(version_object)
        result.append((''.join(('py', version)), 'none', 'any'))
        if i == 0:
            result.append((''.join(('py', version[0])), 'none', 'any'))

    return set(result)


COMPATIBLE_TAGS = compatible_tags()

del compatible_tags


def is_compatible(wheel, tags=None):
    if not isinstance(wheel, Wheel):
        wheel = Wheel(wheel)  # assume it's a filename
    result = False
    if tags is None:
        tags = COMPATIBLE_TAGS
    for ver, abi, arch in tags:
        if ver in wheel.pyver and abi in wheel.abi and arch in wheel.arch:
            result = True
            break
    return result

# === NexusCore/openenv\Lib\site-packages\pycparser\ply\lex.py ===
# -----------------------------------------------------------------------------
# ply: lex.py
#
# Copyright (C) 2001-2017
# David M. Beazley (Dabeaz LLC)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of the David Beazley or Dabeaz LLC may be used to
#   endorse or promote products derived from this software without
#  specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# -----------------------------------------------------------------------------

__version__    = '3.10'
__tabversion__ = '3.10'

import re
import sys
import types
import copy
import os
import inspect

# This tuple contains known string types
try:
    # Python 2.6
    StringTypes = (types.StringType, types.UnicodeType)
except AttributeError:
    # Python 3.0
    StringTypes = (str, bytes)

# This regular expression is used to match valid token names
_is_identifier = re.compile(r'^[a-zA-Z0-9_]+$')

# Exception thrown when invalid token encountered and no default error
# handler is defined.
class LexError(Exception):
    def __init__(self, message, s):
        self.args = (message,)
        self.text = s


# Token class.  This class is used to represent the tokens produced.
class LexToken(object):
    def __str__(self):
        return 'LexToken(%s,%r,%d,%d)' % (self.type, self.value, self.lineno, self.lexpos)

    def __repr__(self):
        return str(self)


# This object is a stand-in for a logging object created by the
# logging module.

class PlyLogger(object):
    def __init__(self, f):
        self.f = f

    def critical(self, msg, *args, **kwargs):
        self.f.write((msg % args) + '\n')

    def warning(self, msg, *args, **kwargs):
        self.f.write('WARNING: ' + (msg % args) + '\n')

    def error(self, msg, *args, **kwargs):
        self.f.write('ERROR: ' + (msg % args) + '\n')

    info = critical
    debug = critical


# Null logger is used when no output is generated. Does nothing.
class NullLogger(object):
    def __getattribute__(self, name):
        return self

    def __call__(self, *args, **kwargs):
        return self


# -----------------------------------------------------------------------------
#                        === Lexing Engine ===
#
# The following Lexer class implements the lexer runtime.   There are only
# a few public methods and attributes:
#
#    input()          -  Store a new string in the lexer
#    token()          -  Get the next token
#    clone()          -  Clone the lexer
#
#    lineno           -  Current line number
#    lexpos           -  Current position in the input string
# -----------------------------------------------------------------------------

class Lexer:
    def __init__(self):
        self.lexre = None             # Master regular expression. This is a list of
                                      # tuples (re, findex) where re is a compiled
                                      # regular expression and findex is a list
                                      # mapping regex group numbers to rules
        self.lexretext = None         # Current regular expression strings
        self.lexstatere = {}          # Dictionary mapping lexer states to master regexs
        self.lexstateretext = {}      # Dictionary mapping lexer states to regex strings
        self.lexstaterenames = {}     # Dictionary mapping lexer states to symbol names
        self.lexstate = 'INITIAL'     # Current lexer state
        self.lexstatestack = []       # Stack of lexer states
        self.lexstateinfo = None      # State information
        self.lexstateignore = {}      # Dictionary of ignored characters for each state
        self.lexstateerrorf = {}      # Dictionary of error functions for each state
        self.lexstateeoff = {}        # Dictionary of eof functions for each state
        self.lexreflags = 0           # Optional re compile flags
        self.lexdata = None           # Actual input data (as a string)
        self.lexpos = 0               # Current position in input text
        self.lexlen = 0               # Length of the input text
        self.lexerrorf = None         # Error rule (if any)
        self.lexeoff = None           # EOF rule (if any)
        self.lextokens = None         # List of valid tokens
        self.lexignore = ''           # Ignored characters
        self.lexliterals = ''         # Literal characters that can be passed through
        self.lexmodule = None         # Module
        self.lineno = 1               # Current line number
        self.lexoptimize = False      # Optimized mode

    def clone(self, object=None):
        c = copy.copy(self)

        # If the object parameter has been supplied, it means we are attaching the
        # lexer to a new object.  In this case, we have to rebind all methods in
        # the lexstatere and lexstateerrorf tables.

        if object:
            newtab = {}
            for key, ritem in self.lexstatere.items():
                newre = []
                for cre, findex in ritem:
                    newfindex = []
                    for f in findex:
                        if not f or not f[0]:
                            newfindex.append(f)
                            continue
                        newfindex.append((getattr(object, f[0].__name__), f[1]))
                newre.append((cre, newfindex))
                newtab[key] = newre
            c.lexstatere = newtab
            c.lexstateerrorf = {}
            for key, ef in self.lexstateerrorf.items():
                c.lexstateerrorf[key] = getattr(object, ef.__name__)
            c.lexmodule = object
        return c

    # ------------------------------------------------------------
    # writetab() - Write lexer information to a table file
    # ------------------------------------------------------------
    def writetab(self, lextab, outputdir=''):
        if isinstance(lextab, types.ModuleType):
            raise IOError("Won't overwrite existing lextab module")
        basetabmodule = lextab.split('.')[-1]
        filename = os.path.join(outputdir, basetabmodule) + '.py'
        with open(filename, 'w') as tf:
            tf.write('# %s.py. This file automatically created by PLY (version %s). Don\'t edit!\n' % (basetabmodule, __version__))
            tf.write('_tabversion   = %s\n' % repr(__tabversion__))
            tf.write('_lextokens    = set(%s)\n' % repr(tuple(sorted(self.lextokens))))
            tf.write('_lexreflags   = %s\n' % repr(self.lexreflags))
            tf.write('_lexliterals  = %s\n' % repr(self.lexliterals))
            tf.write('_lexstateinfo = %s\n' % repr(self.lexstateinfo))

            # Rewrite the lexstatere table, replacing function objects with function names
            tabre = {}
            for statename, lre in self.lexstatere.items():
                titem = []
                for (pat, func), retext, renames in zip(lre, self.lexstateretext[statename], self.lexstaterenames[statename]):
                    titem.append((retext, _funcs_to_names(func, renames)))
                tabre[statename] = titem

            tf.write('_lexstatere   = %s\n' % repr(tabre))
            tf.write('_lexstateignore = %s\n' % repr(self.lexstateignore))

            taberr = {}
            for statename, ef in self.lexstateerrorf.items():
                taberr[statename] = ef.__name__ if ef else None
            tf.write('_lexstateerrorf = %s\n' % repr(taberr))

            tabeof = {}
            for statename, ef in self.lexstateeoff.items():
                tabeof[statename] = ef.__name__ if ef else None
            tf.write('_lexstateeoff = %s\n' % repr(tabeof))

    # ------------------------------------------------------------
    # readtab() - Read lexer information from a tab file
    # ------------------------------------------------------------
    def readtab(self, tabfile, fdict):
        if isinstance(tabfile, types.ModuleType):
            lextab = tabfile
        else:
            exec('import %s' % tabfile)
            lextab = sys.modules[tabfile]

        if getattr(lextab, '_tabversion', '0.0') != __tabversion__:
            raise ImportError('Inconsistent PLY version')

        self.lextokens      = lextab._lextokens
        self.lexreflags     = lextab._lexreflags
        self.lexliterals    = lextab._lexliterals
        self.lextokens_all  = self.lextokens | set(self.lexliterals)
        self.lexstateinfo   = lextab._lexstateinfo
        self.lexstateignore = lextab._lexstateignore
        self.lexstatere     = {}
        self.lexstateretext = {}
        for statename, lre in lextab._lexstatere.items():
            titem = []
            txtitem = []
            for pat, func_name in lre:
                titem.append((re.compile(pat, lextab._lexreflags), _names_to_funcs(func_name, fdict)))

            self.lexstatere[statename] = titem
            self.lexstateretext[statename] = txtitem

        self.lexstateerrorf = {}
        for statename, ef in lextab._lexstateerrorf.items():
            self.lexstateerrorf[statename] = fdict[ef]

        self.lexstateeoff = {}
        for statename, ef in lextab._lexstateeoff.items():
            self.lexstateeoff[statename] = fdict[ef]

        self.begin('INITIAL')

    # ------------------------------------------------------------
    # input() - Push a new string into the lexer
    # ------------------------------------------------------------
    def input(self, s):
        # Pull off the first character to see if s looks like a string
        c = s[:1]
        if not isinstance(c, StringTypes):
            raise ValueError('Expected a string')
        self.lexdata = s
        self.lexpos = 0
        self.lexlen = len(s)

    # ------------------------------------------------------------
    # begin() - Changes the lexing state
    # ------------------------------------------------------------
    def begin(self, state):
        if state not in self.lexstatere:
            raise ValueError('Undefined state')
        self.lexre = self.lexstatere[state]
        self.lexretext = self.lexstateretext[state]
        self.lexignore = self.lexstateignore.get(state, '')
        self.lexerrorf = self.lexstateerrorf.get(state, None)
        self.lexeoff = self.lexstateeoff.get(state, None)
        self.lexstate = state

    # ------------------------------------------------------------
    # push_state() - Changes the lexing state and saves old on stack
    # ------------------------------------------------------------
    def push_state(self, state):
        self.lexstatestack.append(self.lexstate)
        self.begin(state)

    # ------------------------------------------------------------
    # pop_state() - Restores the previous state
    # ------------------------------------------------------------
    def pop_state(self):
        self.begin(self.lexstatestack.pop())

    # ------------------------------------------------------------
    # current_state() - Returns the current lexing state
    # ------------------------------------------------------------
    def current_state(self):
        return self.lexstate

    # ------------------------------------------------------------
    # skip() - Skip ahead n characters
    # ------------------------------------------------------------
    def skip(self, n):
        self.lexpos += n

    # ------------------------------------------------------------
    # opttoken() - Return the next token from the Lexer
    #
    # Note: This function has been carefully implemented to be as fast
    # as possible.  Don't make changes unless you really know what
    # you are doing
    # ------------------------------------------------------------
    def token(self):
        # Make local copies of frequently referenced attributes
        lexpos    = self.lexpos
        lexlen    = self.lexlen
        lexignore = self.lexignore
        lexdata   = self.lexdata

        while lexpos < lexlen:
            # This code provides some short-circuit code for whitespace, tabs, and other ignored characters
            if lexdata[lexpos] in lexignore:
                lexpos += 1
                continue

            # Look for a regular expression match
            for lexre, lexindexfunc in self.lexre:
                m = lexre.match(lexdata, lexpos)
                if not m:
                    continue

                # Create a token for return
                tok = LexToken()
                tok.value = m.group()
                tok.lineno = self.lineno
                tok.lexpos = lexpos

                i = m.lastindex
                func, tok.type = lexindexfunc[i]

                if not func:
                    # If no token type was set, it's an ignored token
                    if tok.type:
                        self.lexpos = m.end()
                        return tok
                    else:
                        lexpos = m.end()
                        break

                lexpos = m.end()

                # If token is processed by a function, call it

                tok.lexer = self      # Set additional attributes useful in token rules
                self.lexmatch = m
                self.lexpos = lexpos

                newtok = func(tok)

                # Every function must return a token, if nothing, we just move to next token
                if not newtok:
                    lexpos    = self.lexpos         # This is here in case user has updated lexpos.
                    lexignore = self.lexignore      # This is here in case there was a state change
                    break

                # Verify type of the token.  If not in the token map, raise an error
                if not self.lexoptimize:
                    if newtok.type not in self.lextokens_all:
                        raise LexError("%s:%d: Rule '%s' returned an unknown token type '%s'" % (
                            func.__code__.co_filename, func.__code__.co_firstlineno,
                            func.__name__, newtok.type), lexdata[lexpos:])

                return newtok
            else:
                # No match, see if in literals
                if lexdata[lexpos] in self.lexliterals:
                    tok = LexToken()
                    tok.value = lexdata[lexpos]
                    tok.lineno = self.lineno
                    tok.type = tok.value
                    tok.lexpos = lexpos
                    self.lexpos = lexpos + 1
                    return tok

                # No match. Call t_error() if defined.
                if self.lexerrorf:
                    tok = LexToken()
                    tok.value = self.lexdata[lexpos:]
                    tok.lineno = self.lineno
                    tok.type = 'error'
                    tok.lexer = self
                    tok.lexpos = lexpos
                    self.lexpos = lexpos
                    newtok = self.lexerrorf(tok)
                    if lexpos == self.lexpos:
                        # Error method didn't change text position at all. This is an error.
                        raise LexError("Scanning error. Illegal character '%s'" % (lexdata[lexpos]), lexdata[lexpos:])
                    lexpos = self.lexpos
                    if not newtok:
                        continue
                    return newtok

                self.lexpos = lexpos
                raise LexError("Illegal character '%s' at index %d" % (lexdata[lexpos], lexpos), lexdata[lexpos:])

        if self.lexeoff:
            tok = LexToken()
            tok.type = 'eof'
            tok.value = ''
            tok.lineno = self.lineno
            tok.lexpos = lexpos
            tok.lexer = self
            self.lexpos = lexpos
            newtok = self.lexeoff(tok)
            return newtok

        self.lexpos = lexpos + 1
        if self.lexdata is None:
            raise RuntimeError('No input string given with input()')
        return None

    # Iterator interface
    def __iter__(self):
        return self

    def next(self):
        t = self.token()
        if t is None:
            raise StopIteration
        return t

    __next__ = next

# -----------------------------------------------------------------------------
#                           ==== Lex Builder ===
#
# The functions and classes below are used to collect lexing information
# and build a Lexer object from it.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# _get_regex(func)
#
# Returns the regular expression assigned to a function either as a doc string
# or as a .regex attribute attached by the @TOKEN decorator.
# -----------------------------------------------------------------------------
def _get_regex(func):
    return getattr(func, 'regex', func.__doc__)

# -----------------------------------------------------------------------------
# get_caller_module_dict()
#
# This function returns a dictionary containing all of the symbols defined within
# a caller further down the call stack.  This is used to get the environment
# associated with the yacc() call if none was provided.
# -----------------------------------------------------------------------------
def get_caller_module_dict(levels):
    f = sys._getframe(levels)
    ldict = f.f_globals.copy()
    if f.f_globals != f.f_locals:
        ldict.update(f.f_locals)
    return ldict

# -----------------------------------------------------------------------------
# _funcs_to_names()
#
# Given a list of regular expression functions, this converts it to a list
# suitable for output to a table file
# -----------------------------------------------------------------------------
def _funcs_to_names(funclist, namelist):
    result = []
    for f, name in zip(funclist, namelist):
        if f and f[0]:
            result.append((name, f[1]))
        else:
            result.append(f)
    return result

# -----------------------------------------------------------------------------
# _names_to_funcs()
#
# Given a list of regular expression function names, this converts it back to
# functions.
# -----------------------------------------------------------------------------
def _names_to_funcs(namelist, fdict):
    result = []
    for n in namelist:
        if n and n[0]:
            result.append((fdict[n[0]], n[1]))
        else:
            result.append(n)
    return result

# -----------------------------------------------------------------------------
# _form_master_re()
#
# This function takes a list of all of the regex components and attempts to
# form the master regular expression.  Given limitations in the Python re
# module, it may be necessary to break the master regex into separate expressions.
# -----------------------------------------------------------------------------
def _form_master_re(relist, reflags, ldict, toknames):
    if not relist:
        return []
    regex = '|'.join(relist)
    try:
        lexre = re.compile(regex, reflags)

        # Build the index to function map for the matching engine
        lexindexfunc = [None] * (max(lexre.groupindex.values()) + 1)
        lexindexnames = lexindexfunc[:]

        for f, i in lexre.groupindex.items():
            handle = ldict.get(f, None)
            if type(handle) in (types.FunctionType, types.MethodType):
                lexindexfunc[i] = (handle, toknames[f])
                lexindexnames[i] = f
            elif handle is not None:
                lexindexnames[i] = f
                if f.find('ignore_') > 0:
                    lexindexfunc[i] = (None, None)
                else:
                    lexindexfunc[i] = (None, toknames[f])

        return [(lexre, lexindexfunc)], [regex], [lexindexnames]
    except Exception:
        m = int(len(relist)/2)
        if m == 0:
            m = 1
        llist, lre, lnames = _form_master_re(relist[:m], reflags, ldict, toknames)
        rlist, rre, rnames = _form_master_re(relist[m:], reflags, ldict, toknames)
        return (llist+rlist), (lre+rre), (lnames+rnames)

# -----------------------------------------------------------------------------
# def _statetoken(s,names)
#
# Given a declaration name s of the form "t_" and a dictionary whose keys are
# state names, this function returns a tuple (states,tokenname) where states
# is a tuple of state names and tokenname is the name of the token.  For example,
# calling this with s = "t_foo_bar_SPAM" might return (('foo','bar'),'SPAM')
# -----------------------------------------------------------------------------
def _statetoken(s, names):
    nonstate = 1
    parts = s.split('_')
    for i, part in enumerate(parts[1:], 1):
        if part not in names and part != 'ANY':
            break

    if i > 1:
        states = tuple(parts[1:i])
    else:
        states = ('INITIAL',)

    if 'ANY' in states:
        states = tuple(names)

    tokenname = '_'.join(parts[i:])
    return (states, tokenname)


# -----------------------------------------------------------------------------
# LexerReflect()
#
# This class represents information needed to build a lexer as extracted from a
# user's input file.
# -----------------------------------------------------------------------------
class LexerReflect(object):
    def __init__(self, ldict, log=None, reflags=0):
        self.ldict      = ldict
        self.error_func = None
        self.tokens     = []
        self.reflags    = reflags
        self.stateinfo  = {'INITIAL': 'inclusive'}
        self.modules    = set()
        self.error      = False
        self.log        = PlyLogger(sys.stderr) if log is None else log

    # Get all of the basic information
    def get_all(self):
        self.get_tokens()
        self.get_literals()
        self.get_states()
        self.get_rules()

    # Validate all of the information
    def validate_all(self):
        self.validate_tokens()
        self.validate_literals()
        self.validate_rules()
        return self.error

    # Get the tokens map
    def get_tokens(self):
        tokens = self.ldict.get('tokens', None)
        if not tokens:
            self.log.error('No token list is defined')
            self.error = True
            return

        if not isinstance(tokens, (list, tuple)):
            self.log.error('tokens must be a list or tuple')
            self.error = True
            return

        if not tokens:
            self.log.error('tokens is empty')
            self.error = True
            return

        self.tokens = tokens

    # Validate the tokens
    def validate_tokens(self):
        terminals = {}
        for n in self.tokens:
            if not _is_identifier.match(n):
                self.log.error("Bad token name '%s'", n)
                self.error = True
            if n in terminals:
                self.log.warning("Token '%s' multiply defined", n)
            terminals[n] = 1

    # Get the literals specifier
    def get_literals(self):
        self.literals = self.ldict.get('literals', '')
        if not self.literals:
            self.literals = ''

    # Validate literals
    def validate_literals(self):
        try:
            for c in self.literals:
                if not isinstance(c, StringTypes) or len(c) > 1:
                    self.log.error('Invalid literal %s. Must be a single character', repr(c))
                    self.error = True

        except TypeError:
            self.log.error('Invalid literals specification. literals must be a sequence of characters')
            self.error = True

    def get_states(self):
        self.states = self.ldict.get('states', None)
        # Build statemap
        if self.states:
            if not isinstance(self.states, (tuple, list)):
                self.log.error('states must be defined as a tuple or list')
                self.error = True
            else:
                for s in self.states:
                    if not isinstance(s, tuple) or len(s) != 2:
                        self.log.error("Invalid state specifier %s. Must be a tuple (statename,'exclusive|inclusive')", repr(s))
                        self.error = True
                        continue
                    name, statetype = s
                    if not isinstance(name, StringTypes):
                        self.log.error('State name %s must be a string', repr(name))
                        self.error = True
                        continue
                    if not (statetype == 'inclusive' or statetype == 'exclusive'):
                        self.log.error("State type for state %s must be 'inclusive' or 'exclusive'", name)
                        self.error = True
                        continue
                    if name in self.stateinfo:
                        self.log.error("State '%s' already defined", name)
                        self.error = True
                        continue
                    self.stateinfo[name] = statetype

    # Get all of the symbols with a t_ prefix and sort them into various
    # categories (functions, strings, error functions, and ignore characters)

    def get_rules(self):
        tsymbols = [f for f in self.ldict if f[:2] == 't_']

        # Now build up a list of functions and a list of strings
        self.toknames = {}        # Mapping of symbols to token names
        self.funcsym  = {}        # Symbols defined as functions
        self.strsym   = {}        # Symbols defined as strings
        self.ignore   = {}        # Ignore strings by state
        self.errorf   = {}        # Error functions by state
        self.eoff     = {}        # EOF functions by state

        for s in self.stateinfo:
            self.funcsym[s] = []
            self.strsym[s] = []

        if len(tsymbols) == 0:
            self.log.error('No rules of the form t_rulename are defined')
            self.error = True
            return

        for f in tsymbols:
            t = self.ldict[f]
            states, tokname = _statetoken(f, self.stateinfo)
            self.toknames[f] = tokname

            if hasattr(t, '__call__'):
                if tokname == 'error':
                    for s in states:
                        self.errorf[s] = t
                elif tokname == 'eof':
                    for s in states:
                        self.eoff[s] = t
                elif tokname == 'ignore':
                    line = t.__code__.co_firstlineno
                    file = t.__code__.co_filename
                    self.log.error("%s:%d: Rule '%s' must be defined as a string", file, line, t.__name__)
                    self.error = True
                else:
                    for s in states:
                        self.funcsym[s].append((f, t))
            elif isinstance(t, StringTypes):
                if tokname == 'ignore':
                    for s in states:
                        self.ignore[s] = t
                    if '\\' in t:
                        self.log.warning("%s contains a literal backslash '\\'", f)

                elif tokname == 'error':
                    self.log.error("Rule '%s' must be defined as a function", f)
                    self.error = True
                else:
                    for s in states:
                        self.strsym[s].append((f, t))
            else:
                self.log.error('%s not defined as a function or string', f)
                self.error = True

        # Sort the functions by line number
        for f in self.funcsym.values():
            f.sort(key=lambda x: x[1].__code__.co_firstlineno)

        # Sort the strings by regular expression length
        for s in self.strsym.values():
            s.sort(key=lambda x: len(x[1]), reverse=True)

    # Validate all of the t_rules collected
    def validate_rules(self):
        for state in self.stateinfo:
            # Validate all rules defined by functions

            for fname, f in self.funcsym[state]:
                line = f.__code__.co_firstlineno
                file = f.__code__.co_filename
                module = inspect.getmodule(f)
                self.modules.add(module)

                tokname = self.toknames[fname]
                if isinstance(f, types.MethodType):
                    reqargs = 2
                else:
                    reqargs = 1
                nargs = f.__code__.co_argcount
                if nargs > reqargs:
                    self.log.error("%s:%d: Rule '%s' has too many arguments", file, line, f.__name__)
                    self.error = True
                    continue

                if nargs < reqargs:
                    self.log.error("%s:%d: Rule '%s' requires an argument", file, line, f.__name__)
                    self.error = True
                    continue

                if not _get_regex(f):
                    self.log.error("%s:%d: No regular expression defined for rule '%s'", file, line, f.__name__)
                    self.error = True
                    continue

                try:
                    c = re.compile('(?P<%s>%s)' % (fname, _get_regex(f)), self.reflags)
                    if c.match(''):
                        self.log.error("%s:%d: Regular expression for rule '%s' matches empty string", file, line, f.__name__)
                        self.error = True
                except re.error as e:
                    self.log.error("%s:%d: Invalid regular expression for rule '%s'. %s", file, line, f.__name__, e)
                    if '#' in _get_regex(f):
                        self.log.error("%s:%d. Make sure '#' in rule '%s' is escaped with '\\#'", file, line, f.__name__)
                    self.error = True

            # Validate all rules defined by strings
            for name, r in self.strsym[state]:
                tokname = self.toknames[name]
                if tokname == 'error':
                    self.log.error("Rule '%s' must be defined as a function", name)
                    self.error = True
                    continue

                if tokname not in self.tokens and tokname.find('ignore_') < 0:
                    self.log.error("Rule '%s' defined for an unspecified token %s", name, tokname)
                    self.error = True
                    continue

                try:
                    c = re.compile('(?P<%s>%s)' % (name, r), self.reflags)
                    if (c.match('')):
                        self.log.error("Regular expression for rule '%s' matches empty string", name)
                        self.error = True
                except re.error as e:
                    self.log.error("Invalid regular expression for rule '%s'. %s", name, e)
                    if '#' in r:
                        self.log.error("Make sure '#' in rule '%s' is escaped with '\\#'", name)
                    self.error = True

            if not self.funcsym[state] and not self.strsym[state]:
                self.log.error("No rules defined for state '%s'", state)
                self.error = True

            # Validate the error function
            efunc = self.errorf.get(state, None)
            if efunc:
                f = efunc
                line = f.__code__.co_firstlineno
                file = f.__code__.co_filename
                module = inspect.getmodule(f)
                self.modules.add(module)

                if isinstance(f, types.MethodType):
                    reqargs = 2
                else:
                    reqargs = 1
                nargs = f.__code__.co_argcount
                if nargs > reqargs:
                    self.log.error("%s:%d: Rule '%s' has too many arguments", file, line, f.__name__)
                    self.error = True

                if nargs < reqargs:
                    self.log.error("%s:%d: Rule '%s' requires an argument", file, line, f.__name__)
                    self.error = True

        for module in self.modules:
            self.validate_module(module)

    # -----------------------------------------------------------------------------
    # validate_module()
    #
    # This checks to see if there are duplicated t_rulename() functions or strings
    # in the parser input file.  This is done using a simple regular expression
    # match on each line in the source code of the given module.
    # -----------------------------------------------------------------------------

    def validate_module(self, module):
        try:
            lines, linen = inspect.getsourcelines(module)
        except IOError:
            return

        fre = re.compile(r'\s*def\s+(t_[a-zA-Z_0-9]*)\(')
        sre = re.compile(r'\s*(t_[a-zA-Z_0-9]*)\s*=')

        counthash = {}
        linen += 1
        for line in lines:
            m = fre.match(line)
            if not m:
                m = sre.match(line)
            if m:
                name = m.group(1)
                prev = counthash.get(name)
                if not prev:
                    counthash[name] = linen
                else:
                    filename = inspect.getsourcefile(module)
                    self.log.error('%s:%d: Rule %s redefined. Previously defined on line %d', filename, linen, name, prev)
                    self.error = True
            linen += 1

# -----------------------------------------------------------------------------
# lex(module)
#
# Build all of the regular expression rules from definitions in the supplied module
# -----------------------------------------------------------------------------
def lex(module=None, object=None, debug=False, optimize=False, lextab='lextab',
        reflags=int(re.VERBOSE), nowarn=False, outputdir=None, debuglog=None, errorlog=None):

    if lextab is None:
        lextab = 'lextab'

    global lexer

    ldict = None
    stateinfo  = {'INITIAL': 'inclusive'}
    lexobj = Lexer()
    lexobj.lexoptimize = optimize
    global token, input

    if errorlog is None:
        errorlog = PlyLogger(sys.stderr)

    if debug:
        if debuglog is None:
            debuglog = PlyLogger(sys.stderr)

    # Get the module dictionary used for the lexer
    if object:
        module = object

    # Get the module dictionary used for the parser
    if module:
        _items = [(k, getattr(module, k)) for k in dir(module)]
        ldict = dict(_items)
        # If no __file__ attribute is available, try to obtain it from the __module__ instead
        if '__file__' not in ldict:
            ldict['__file__'] = sys.modules[ldict['__module__']].__file__
    else:
        ldict = get_caller_module_dict(2)

    # Determine if the module is package of a package or not.
    # If so, fix the tabmodule setting so that tables load correctly
    pkg = ldict.get('__package__')
    if pkg and isinstance(lextab, str):
        if '.' not in lextab:
            lextab = pkg + '.' + lextab

    # Collect parser information from the dictionary
    linfo = LexerReflect(ldict, log=errorlog, reflags=reflags)
    linfo.get_all()
    if not optimize:
        if linfo.validate_all():
            raise SyntaxError("Can't build lexer")

    if optimize and lextab:
        try:
            lexobj.readtab(lextab, ldict)
            token = lexobj.token
            input = lexobj.input
            lexer = lexobj
            return lexobj

        except ImportError:
            pass

    # Dump some basic debugging information
    if debug:
        debuglog.info('lex: tokens   = %r', linfo.tokens)
        debuglog.info('lex: literals = %r', linfo.literals)
        debuglog.info('lex: states   = %r', linfo.stateinfo)

    # Build a dictionary of valid token names
    lexobj.lextokens = set()
    for n in linfo.tokens:
        lexobj.lextokens.add(n)

    # Get literals specification
    if isinstance(linfo.literals, (list, tuple)):
        lexobj.lexliterals = type(linfo.literals[0])().join(linfo.literals)
    else:
        lexobj.lexliterals = linfo.literals

    lexobj.lextokens_all = lexobj.lextokens | set(lexobj.lexliterals)

    # Get the stateinfo dictionary
    stateinfo = linfo.stateinfo

    regexs = {}
    # Build the master regular expressions
    for state in stateinfo:
        regex_list = []

        # Add rules defined by functions first
        for fname, f in linfo.funcsym[state]:
            line = f.__code__.co_firstlineno
            file = f.__code__.co_filename
            regex_list.append('(?P<%s>%s)' % (fname, _get_regex(f)))
            if debug:
                debuglog.info("lex: Adding rule %s -> '%s' (state '%s')", fname, _get_regex(f), state)

        # Now add all of the simple rules
        for name, r in linfo.strsym[state]:
            regex_list.append('(?P<%s>%s)' % (name, r))
            if debug:
                debuglog.info("lex: Adding rule %s -> '%s' (state '%s')", name, r, state)

        regexs[state] = regex_list

    # Build the master regular expressions

    if debug:
        debuglog.info('lex: ==== MASTER REGEXS FOLLOW ====')

    for state in regexs:
        lexre, re_text, re_names = _form_master_re(regexs[state], reflags, ldict, linfo.toknames)
        lexobj.lexstatere[state] = lexre
        lexobj.lexstateretext[state] = re_text
        lexobj.lexstaterenames[state] = re_names
        if debug:
            for i, text in enumerate(re_text):
                debuglog.info("lex: state '%s' : regex[%d] = '%s'", state, i, text)

    # For inclusive states, we need to add the regular expressions from the INITIAL state
    for state, stype in stateinfo.items():
        if state != 'INITIAL' and stype == 'inclusive':
            lexobj.lexstatere[state].extend(lexobj.lexstatere['INITIAL'])
            lexobj.lexstateretext[state].extend(lexobj.lexstateretext['INITIAL'])
            lexobj.lexstaterenames[state].extend(lexobj.lexstaterenames['INITIAL'])

    lexobj.lexstateinfo = stateinfo
    lexobj.lexre = lexobj.lexstatere['INITIAL']
    lexobj.lexretext = lexobj.lexstateretext['INITIAL']
    lexobj.lexreflags = reflags

    # Set up ignore variables
    lexobj.lexstateignore = linfo.ignore
    lexobj.lexignore = lexobj.lexstateignore.get('INITIAL', '')

    # Set up error functions
    lexobj.lexstateerrorf = linfo.errorf
    lexobj.lexerrorf = linfo.errorf.get('INITIAL', None)
    if not lexobj.lexerrorf:
        errorlog.warning('No t_error rule is defined')

    # Set up eof functions
    lexobj.lexstateeoff = linfo.eoff
    lexobj.lexeoff = linfo.eoff.get('INITIAL', None)

    # Check state information for ignore and error rules
    for s, stype in stateinfo.items():
        if stype == 'exclusive':
            if s not in linfo.errorf:
                errorlog.warning("No error rule is defined for exclusive state '%s'", s)
            if s not in linfo.ignore and lexobj.lexignore:
                errorlog.warning("No ignore rule is defined for exclusive state '%s'", s)
        elif stype == 'inclusive':
            if s not in linfo.errorf:
                linfo.errorf[s] = linfo.errorf.get('INITIAL', None)
            if s not in linfo.ignore:
                linfo.ignore[s] = linfo.ignore.get('INITIAL', '')

    # Create global versions of the token() and input() functions
    token = lexobj.token
    input = lexobj.input
    lexer = lexobj

    # If in optimize mode, we write the lextab
    if lextab and optimize:
        if outputdir is None:
            # If no output directory is set, the location of the output files
            # is determined according to the following rules:
            #     - If lextab specifies a package, files go into that package directory
            #     - Otherwise, files go in the same directory as the specifying module
            if isinstance(lextab, types.ModuleType):
                srcfile = lextab.__file__
            else:
                if '.' not in lextab:
                    srcfile = ldict['__file__']
                else:
                    parts = lextab.split('.')
                    pkgname = '.'.join(parts[:-1])
                    exec('import %s' % pkgname)
                    srcfile = getattr(sys.modules[pkgname], '__file__', '')
            outputdir = os.path.dirname(srcfile)
        try:
            lexobj.writetab(lextab, outputdir)
        except IOError as e:
            errorlog.warning("Couldn't write lextab module %r. %s" % (lextab, e))

    return lexobj

# -----------------------------------------------------------------------------
# runmain()
#
# This runs the lexer as a main program
# -----------------------------------------------------------------------------

def runmain(lexer=None, data=None):
    if not data:
        try:
            filename = sys.argv[1]
            f = open(filename)
            data = f.read()
            f.close()
        except IndexError:
            sys.stdout.write('Reading from standard input (type EOF to end):\n')
            data = sys.stdin.read()

    if lexer:
        _input = lexer.input
    else:
        _input = input
    _input(data)
    if lexer:
        _token = lexer.token
    else:
        _token = token

    while True:
        tok = _token()
        if not tok:
            break
        sys.stdout.write('(%s,%r,%d,%d)\n' % (tok.type, tok.value, tok.lineno, tok.lexpos))

# -----------------------------------------------------------------------------
# @TOKEN(regex)
#
# This decorator function can be used to set the regex expression on a function
# when its docstring might need to be set in an alternative way
# -----------------------------------------------------------------------------

def TOKEN(r):
    def set_regex(f):
        if hasattr(r, '__call__'):
            f.regex = _get_regex(r)
        else:
            f.regex = r
        return f
    return set_regex

# Alternative spelling of the TOKEN decorator
Token = TOKEN

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\services\model_service\client.py ===
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
import os
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
    cast,
)
import warnings

from google.api_core import client_options as client_options_lib
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.exceptions import MutualTLSChannelError  # type: ignore
from google.auth.transport import mtls  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1.services.model_service import pagers
from google.ai.generativelanguage_v1.types import model, model_service

from .transports.base import DEFAULT_CLIENT_INFO, ModelServiceTransport
from .transports.grpc import ModelServiceGrpcTransport
from .transports.grpc_asyncio import ModelServiceGrpcAsyncIOTransport
from .transports.rest import ModelServiceRestTransport


class ModelServiceClientMeta(type):
    """Metaclass for the ModelService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = OrderedDict()  # type: Dict[str, Type[ModelServiceTransport]]
    _transport_registry["grpc"] = ModelServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = ModelServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = ModelServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[ModelServiceTransport]:
        """Returns an appropriate transport class.

        Args:
            label: The name of the desired transport. If none is
                provided, then the first transport in the registry is used.

        Returns:
            The transport class to use.
        """
        # If a specific transport is requested, return that one.
        if label:
            return cls._transport_registry[label]

        # No transport is requested; return the default (that is, the first one
        # in the dictionary).
        return next(iter(cls._transport_registry.values()))


class ModelServiceClient(metaclass=ModelServiceClientMeta):
    """Provides methods for getting metadata information about
    Generative Models.
    """

    @staticmethod
    def _get_default_mtls_endpoint(api_endpoint):
        """Converts api endpoint to mTLS endpoint.

        Convert "*.sandbox.googleapis.com" and "*.googleapis.com" to
        "*.mtls.sandbox.googleapis.com" and "*.mtls.googleapis.com" respectively.
        Args:
            api_endpoint (Optional[str]): the api endpoint to convert.
        Returns:
            str: converted mTLS api endpoint.
        """
        if not api_endpoint:
            return api_endpoint

        mtls_endpoint_re = re.compile(
            r"(?P<name>[^.]+)(?P<mtls>\.mtls)?(?P<sandbox>\.sandbox)?(?P<googledomain>\.googleapis\.com)?"
        )

        m = mtls_endpoint_re.match(api_endpoint)
        name, mtls, sandbox, googledomain = m.groups()
        if mtls or not googledomain:
            return api_endpoint

        if sandbox:
            return api_endpoint.replace(
                "sandbox.googleapis.com", "mtls.sandbox.googleapis.com"
            )

        return api_endpoint.replace(".googleapis.com", ".mtls.googleapis.com")

    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = "generativelanguage.googleapis.com"
    DEFAULT_MTLS_ENDPOINT = _get_default_mtls_endpoint.__func__(  # type: ignore
        DEFAULT_ENDPOINT
    )

    _DEFAULT_ENDPOINT_TEMPLATE = "generativelanguage.{UNIVERSE_DOMAIN}"
    _DEFAULT_UNIVERSE = "googleapis.com"

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            ModelServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_info(info)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

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
            ModelServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> ModelServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            ModelServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def model_path(
        model: str,
    ) -> str:
        """Returns a fully-qualified model string."""
        return "models/{model}".format(
            model=model,
        )

    @staticmethod
    def parse_model_path(path: str) -> Dict[str, str]:
        """Parses a model path into its component segments."""
        m = re.match(r"^models/(?P<model>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_billing_account_path(
        billing_account: str,
    ) -> str:
        """Returns a fully-qualified billing_account string."""
        return "billingAccounts/{billing_account}".format(
            billing_account=billing_account,
        )

    @staticmethod
    def parse_common_billing_account_path(path: str) -> Dict[str, str]:
        """Parse a billing_account path into its component segments."""
        m = re.match(r"^billingAccounts/(?P<billing_account>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_folder_path(
        folder: str,
    ) -> str:
        """Returns a fully-qualified folder string."""
        return "folders/{folder}".format(
            folder=folder,
        )

    @staticmethod
    def parse_common_folder_path(path: str) -> Dict[str, str]:
        """Parse a folder path into its component segments."""
        m = re.match(r"^folders/(?P<folder>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_organization_path(
        organization: str,
    ) -> str:
        """Returns a fully-qualified organization string."""
        return "organizations/{organization}".format(
            organization=organization,
        )

    @staticmethod
    def parse_common_organization_path(path: str) -> Dict[str, str]:
        """Parse a organization path into its component segments."""
        m = re.match(r"^organizations/(?P<organization>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_project_path(
        project: str,
    ) -> str:
        """Returns a fully-qualified project string."""
        return "projects/{project}".format(
            project=project,
        )

    @staticmethod
    def parse_common_project_path(path: str) -> Dict[str, str]:
        """Parse a project path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_location_path(
        project: str,
        location: str,
    ) -> str:
        """Returns a fully-qualified location string."""
        return "projects/{project}/locations/{location}".format(
            project=project,
            location=location,
        )

    @staticmethod
    def parse_common_location_path(path: str) -> Dict[str, str]:
        """Parse a location path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)/locations/(?P<location>.+?)$", path)
        return m.groupdict() if m else {}

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[client_options_lib.ClientOptions] = None
    ):
        """Deprecated. Return the API endpoint and client cert source for mutual TLS.

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

        warnings.warn(
            "get_mtls_endpoint_and_cert_source is deprecated. Use the api_endpoint property instead.",
            DeprecationWarning,
        )
        if client_options is None:
            client_options = client_options_lib.ClientOptions()
        use_client_cert = os.getenv("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )

        # Figure out the client cert source to use.
        client_cert_source = None
        if use_client_cert == "true":
            if client_options.client_cert_source:
                client_cert_source = client_options.client_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()

        # Figure out which api endpoint to use.
        if client_options.api_endpoint is not None:
            api_endpoint = client_options.api_endpoint
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            api_endpoint = cls.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = cls.DEFAULT_ENDPOINT

        return api_endpoint, client_cert_source

    @staticmethod
    def _read_environment_variables():
        """Returns the environment variables used by the client.

        Returns:
            Tuple[bool, str, str]: returns the GOOGLE_API_USE_CLIENT_CERTIFICATE,
            GOOGLE_API_USE_MTLS_ENDPOINT, and GOOGLE_CLOUD_UNIVERSE_DOMAIN environment variables.

        Raises:
            ValueError: If GOOGLE_API_USE_CLIENT_CERTIFICATE is not
                any of ["true", "false"].
            google.auth.exceptions.MutualTLSChannelError: If GOOGLE_API_USE_MTLS_ENDPOINT
                is not any of ["auto", "never", "always"].
        """
        use_client_cert = os.getenv(
            "GOOGLE_API_USE_CLIENT_CERTIFICATE", "false"
        ).lower()
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto").lower()
        universe_domain_env = os.getenv("GOOGLE_CLOUD_UNIVERSE_DOMAIN")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )
        return use_client_cert == "true", use_mtls_endpoint, universe_domain_env

    @staticmethod
    def _get_client_cert_source(provided_cert_source, use_cert_flag):
        """Return the client cert source to be used by the client.

        Args:
            provided_cert_source (bytes): The client certificate source provided.
            use_cert_flag (bool): A flag indicating whether to use the client certificate.

        Returns:
            bytes or None: The client cert source to be used by the client.
        """
        client_cert_source = None
        if use_cert_flag:
            if provided_cert_source:
                client_cert_source = provided_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()
        return client_cert_source

    @staticmethod
    def _get_api_endpoint(
        api_override, client_cert_source, universe_domain, use_mtls_endpoint
    ):
        """Return the API endpoint used by the client.

        Args:
            api_override (str): The API endpoint override. If specified, this is always
                the return value of this function and the other arguments are not used.
            client_cert_source (bytes): The client certificate source used by the client.
            universe_domain (str): The universe domain used by the client.
            use_mtls_endpoint (str): How to use the mTLS endpoint, which depends also on the other parameters.
                Possible values are "always", "auto", or "never".

        Returns:
            str: The API endpoint to be used by the client.
        """
        if api_override is not None:
            api_endpoint = api_override
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            _default_universe = ModelServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = ModelServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = ModelServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
                UNIVERSE_DOMAIN=universe_domain
            )
        return api_endpoint

    @staticmethod
    def _get_universe_domain(
        client_universe_domain: Optional[str], universe_domain_env: Optional[str]
    ) -> str:
        """Return the universe domain used by the client.

        Args:
            client_universe_domain (Optional[str]): The universe domain configured via the client options.
            universe_domain_env (Optional[str]): The universe domain configured via the "GOOGLE_CLOUD_UNIVERSE_DOMAIN" environment variable.

        Returns:
            str: The universe domain to be used by the client.

        Raises:
            ValueError: If the universe domain is an empty string.
        """
        universe_domain = ModelServiceClient._DEFAULT_UNIVERSE
        if client_universe_domain is not None:
            universe_domain = client_universe_domain
        elif universe_domain_env is not None:
            universe_domain = universe_domain_env
        if len(universe_domain.strip()) == 0:
            raise ValueError("Universe Domain cannot be an empty string.")
        return universe_domain

    @staticmethod
    def _compare_universes(
        client_universe: str, credentials: ga_credentials.Credentials
    ) -> bool:
        """Returns True iff the universe domains used by the client and credentials match.

        Args:
            client_universe (str): The universe domain configured via the client options.
            credentials (ga_credentials.Credentials): The credentials being used in the client.

        Returns:
            bool: True iff client_universe matches the universe in credentials.

        Raises:
            ValueError: when client_universe does not match the universe in credentials.
        """

        default_universe = ModelServiceClient._DEFAULT_UNIVERSE
        credentials_universe = getattr(credentials, "universe_domain", default_universe)

        if client_universe != credentials_universe:
            raise ValueError(
                "The configured universe domain "
                f"({client_universe}) does not match the universe domain "
                f"found in the credentials ({credentials_universe}). "
                "If you haven't configured the universe domain explicitly, "
                f"`{default_universe}` is the default."
            )
        return True

    def _validate_universe_domain(self):
        """Validates client's and credentials' universe domains are consistent.

        Returns:
            bool: True iff the configured universe domain is valid.

        Raises:
            ValueError: If the configured universe domain is not valid.
        """
        self._is_universe_domain_valid = (
            self._is_universe_domain_valid
            or ModelServiceClient._compare_universes(
                self.universe_domain, self.transport._credentials
            )
        )
        return self._is_universe_domain_valid

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used by the client instance.
        """
        return self._universe_domain

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, ModelServiceTransport, Callable[..., ModelServiceTransport]]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the model service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,ModelServiceTransport,Callable[..., ModelServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
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
                default "googleapis.com" universe. Note that the ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client_options = client_options
        if isinstance(self._client_options, dict):
            self._client_options = client_options_lib.from_dict(self._client_options)
        if self._client_options is None:
            self._client_options = client_options_lib.ClientOptions()
        self._client_options = cast(
            client_options_lib.ClientOptions, self._client_options
        )

        universe_domain_opt = getattr(self._client_options, "universe_domain", None)

        (
            self._use_client_cert,
            self._use_mtls_endpoint,
            self._universe_domain_env,
        ) = ModelServiceClient._read_environment_variables()
        self._client_cert_source = ModelServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = ModelServiceClient._get_universe_domain(
            universe_domain_opt, self._universe_domain_env
        )
        self._api_endpoint = None  # updated below, depending on `transport`

        # Initialize the universe domain validation.
        self._is_universe_domain_valid = False

        api_key_value = getattr(self._client_options, "api_key", None)
        if api_key_value and credentials:
            raise ValueError(
                "client_options.api_key and credentials are mutually exclusive"
            )

        # Save or instantiate the transport.
        # Ordinarily, we provide the transport, but allowing a custom transport
        # instance provides an extensibility point for unusual situations.
        transport_provided = isinstance(transport, ModelServiceTransport)
        if transport_provided:
            # transport is a ModelServiceTransport instance.
            if credentials or self._client_options.credentials_file or api_key_value:
                raise ValueError(
                    "When providing a transport instance, "
                    "provide its credentials directly."
                )
            if self._client_options.scopes:
                raise ValueError(
                    "When providing a transport instance, provide its scopes "
                    "directly."
                )
            self._transport = cast(ModelServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = self._api_endpoint or ModelServiceClient._get_api_endpoint(
            self._client_options.api_endpoint,
            self._client_cert_source,
            self._universe_domain,
            self._use_mtls_endpoint,
        )

        if not transport_provided:
            import google.auth._default  # type: ignore

            if api_key_value and hasattr(
                google.auth._default, "get_api_key_credentials"
            ):
                credentials = google.auth._default.get_api_key_credentials(
                    api_key_value
                )

            transport_init: Union[
                Type[ModelServiceTransport], Callable[..., ModelServiceTransport]
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., ModelServiceTransport], transport)
            )
            # initialize with the provided callable or the passed in class
            self._transport = transport_init(
                credentials=credentials,
                credentials_file=self._client_options.credentials_file,
                host=self._api_endpoint,
                scopes=self._client_options.scopes,
                client_cert_source_for_mtls=self._client_cert_source,
                quota_project_id=self._client_options.quota_project_id,
                client_info=client_info,
                always_use_jwt_access=True,
                api_audience=self._client_options.api_audience,
            )

    def get_model(
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

            def sample_get_model():
                # Create a client
                client = generativelanguage_v1.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1.GetModelRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1.types.GetModelRequest, dict]):
                The request object. Request for getting information about
                a specific Model.
            name (str):
                Required. The resource name of the model.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
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
        rpc = self._transport._wrapped_methods[self._transport.get_model]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def list_models(
        self,
        request: Optional[Union[model_service.ListModelsRequest, dict]] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListModelsPager:
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

            def sample_list_models():
                # Create a client
                client = generativelanguage_v1.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1.ListModelsRequest(
                )

                # Make the request
                page_result = client.list_models(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1.types.ListModelsRequest, dict]):
                The request object. Request for listing all Models.
            page_size (int):
                The maximum number of ``Models`` to return (per page).

                The service may return fewer models. If unspecified, at
                most 50 models will be returned per page. This method
                returns at most 1000 models per page, even if you pass a
                larger page_size.

                This corresponds to the ``page_size`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            page_token (str):
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
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1.services.model_service.pagers.ListModelsPager:
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
        rpc = self._transport._wrapped_methods[self._transport.list_models]

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__iter__` convenience method.
        response = pagers.ListModelsPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def __enter__(self) -> "ModelServiceClient":
        return self

    def __exit__(self, type, value, traceback):
        """Releases underlying transport's resources.

        .. warning::
            ONLY use as a context manager if the transport is NOT shared
            with other clients! Exiting the with block will CLOSE the transport
            and may cause errors in other clients!
        """
        self.transport.close()

    def list_operations(
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
            retry (google.api_core.retry.Retry): Designation of what errors,
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
        rpc = gapic_v1.method.wrap_method(
            self._transport.list_operations,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def get_operation(
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
            retry (google.api_core.retry.Retry): Designation of what errors,
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
        rpc = gapic_v1.method.wrap_method(
            self._transport.get_operation,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def cancel_operation(
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
            retry (google.api_core.retry.Retry): Designation of what errors,
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
        rpc = gapic_v1.method.wrap_method(
            self._transport.cancel_operation,
            default_timeout=None,
            client_info=DEFAULT_CLIENT_INFO,
        )

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("ModelServiceClient",)

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\debugger\debugger.py ===
# debugger.py

# A debugger for Pythonwin.  Built from pdb.

# Mark Hammond (MHammond@skippinet.com.au) - Dec 94.

# usage:
# >>> import pywin.debugger
# >>> pywin.debugger.GetDebugger().run("command")

import bdb
import os
import pdb
import string
import sys
import traceback
import types

import commctrl
import pywin.docking.DockingBar
import win32api
import win32con
import win32ui
from pywin.framework import app, editor, interact, scriptutils
from pywin.framework.editor.color.coloreditor import MARKER_BREAKPOINT, MARKER_CURRENT
from pywin.mfc import afxres, window
from pywin.tools import browser, hierlist

from .dbgcon import *

LVN_ENDLABELEDIT = commctrl.LVN_ENDLABELEDITW


def SetInteractiveContext(globs, locs):
    if interact.edit is not None and interact.edit.currentView is not None:
        interact.edit.currentView.SetContext(globs, locs)


def _LineStateToMarker(ls):
    if ls == LINESTATE_CURRENT:
        return MARKER_CURRENT
    # 	elif ls == LINESTATE_CALLSTACK:
    # 		return MARKER_CALLSTACK
    return MARKER_BREAKPOINT


class HierListItem(browser.HLIPythonObject):
    pass


class HierFrameItem(HierListItem):
    def __init__(self, frame, debugger):
        HierListItem.__init__(self, frame, repr(frame))
        self.debugger = debugger

    def GetText(self):
        name = self.myobject.f_code.co_name
        if not name or name == "?":
            # See if locals has a '__name__' (ie, a module)
            if "__name__" in self.myobject.f_locals:
                name = str(self.myobject.f_locals["__name__"]) + " module"
            else:
                name = "<Debugger Context>"

        return "%s   (%s:%d)" % (
            name,
            os.path.split(self.myobject.f_code.co_filename)[1],
            self.myobject.f_lineno,
        )

    def GetBitmapColumn(self):
        if self.debugger.curframe is self.myobject:
            return 7
        else:
            return 8

    def GetSubList(self):
        ret = []
        ret.append(HierFrameDict(self.myobject.f_locals, "Locals", 2))
        ret.append(HierFrameDict(self.myobject.f_globals, "Globals", 1))
        return ret

    def IsExpandable(self):
        return 1

    def TakeDefaultAction(self):
        # Set the default frame to be this frame.
        self.debugger.set_cur_frame(self.myobject)
        return 1


class HierFrameDict(browser.HLIDict):
    def __init__(self, dict, name, bitmapColumn):
        self.bitmapColumn = bitmapColumn
        browser.HLIDict.__init__(self, dict, name)

    def GetBitmapColumn(self):
        return self.bitmapColumn


class NoStackAvailableItem(HierListItem):
    def __init__(self, why):
        HierListItem.__init__(self, None, why)

    def IsExpandable(self):
        return 0

    def GetText(self):
        return self.name

    def GetBitmapColumn(self):
        return 8


class HierStackRoot(HierListItem):
    def __init__(self, debugger):
        HierListItem.__init__(self, debugger, None)
        self.last_stack = []

    # def __del__(self):
    #     print("HierStackRoot dieing")
    def GetSubList(self):
        debugger = self.myobject
        # print(self.debugger.stack, self.debugger.curframe)
        ret = []
        if debugger.debuggerState == DBGSTATE_BREAK:
            stackUse = debugger.stack[:]
            stackUse.reverse()
            self.last_stack = []
            for frame, lineno in stackUse:
                self.last_stack.append((frame, lineno))
                if (
                    frame is debugger.userbotframe
                ):  # Don't bother showing frames below our bottom frame.
                    break
        for frame, lineno in self.last_stack:
            ret.append(HierFrameItem(frame, debugger))
        ##		elif debugger.debuggerState==DBGSTATE_NOT_DEBUGGING:
        ##			ret.append(NoStackAvailableItem('<nothing is being debugged>'))
        ##		else:
        ##			ret.append(NoStackAvailableItem('<stack not available while running>'))
        return ret

    def GetText(self):
        return "root item"

    def IsExpandable(self):
        return 1


class HierListDebugger(hierlist.HierListWithItems):
    """Hier List of stack frames, breakpoints, whatever"""

    def __init__(self):
        hierlist.HierListWithItems.__init__(
            self, None, win32ui.IDB_DEBUGGER_HIER, None, win32api.RGB(255, 0, 0)
        )

    def Setup(self, debugger):
        root = HierStackRoot(debugger)
        self.AcceptRoot(root)


# 	def Refresh(self):
# 		self.Setup()


class DebuggerWindow(window.Wnd):
    def __init__(self, ob):
        window.Wnd.__init__(self, ob)
        self.debugger = None

    def Init(self, debugger):
        self.debugger = debugger

    def GetDefRect(self):
        defRect = app.LoadWindowSize("Debugger Windows\\" + self.title)
        if defRect[2] - defRect[0] == 0:
            defRect = 0, 0, 150, 150
        return defRect

    def OnDestroy(self, msg):
        newSize = self.GetWindowPlacement()[4]
        pywin.framework.app.SaveWindowSize("Debugger Windows\\" + self.title, newSize)
        return window.Wnd.OnDestroy(self, msg)

    def OnKeyDown(self, msg):
        key = msg[2]
        if key in (13, 27, 32):
            return 1
        if key in (46, 8):  # delete/BS key
            self.DeleteSelected()
            return 0
        view = scriptutils.GetActiveView()
        try:
            firer = view.bindings.fire_key_event
        except AttributeError:
            firer = None
        if firer is not None:
            return firer(msg)
        else:
            return 1

    def DeleteSelected(self):
        win32api.MessageBeep()

    def EditSelected(self):
        win32api.MessageBeep()


class DebuggerStackWindow(DebuggerWindow):
    title = "Stack"

    def __init__(self):
        DebuggerWindow.__init__(self, win32ui.CreateTreeCtrl())
        self.list = HierListDebugger()
        self.listOK = 0

    def SaveState(self):
        self.list.DeleteAllItems()
        self.listOK = 0
        win32ui.WriteProfileVal(
            "Debugger Windows\\" + self.title, "Visible", self.IsWindowVisible()
        )

    def CreateWindow(self, parent):
        style = (
            win32con.WS_CHILD
            | win32con.WS_VISIBLE
            | win32con.WS_BORDER
            | commctrl.TVS_HASLINES
            | commctrl.TVS_LINESATROOT
            | commctrl.TVS_HASBUTTONS
        )
        self._obj_.CreateWindow(style, self.GetDefRect(), parent, win32ui.IDC_LIST1)
        self.HookMessage(self.OnKeyDown, win32con.WM_KEYDOWN)
        self.HookMessage(self.OnKeyDown, win32con.WM_SYSKEYDOWN)
        self.list.HierInit(parent, self)
        self.listOK = 0  # delayed setup
        # self.list.Setup()

    def RespondDebuggerState(self, state):
        assert self.debugger is not None, "Init not called"
        if not self.listOK:
            self.listOK = 1
            self.list.Setup(self.debugger)
        else:
            self.list.Refresh()

    def RespondDebuggerData(self):
        try:
            handle = self.GetChildItem(0)
        except win32ui.error:
            return  # No items
        while 1:
            item = self.list.ItemFromHandle(handle)
            col = self.list.GetBitmapColumn(item)
            selCol = self.list.GetSelectedBitmapColumn(item)
            if selCol is None:
                selCol = col
            if self.list.GetItemImage(handle) != (col, selCol):
                self.list.SetItemImage(handle, col, selCol)
            try:
                handle = self.GetNextSiblingItem(handle)
            except win32ui.error:
                break


class DebuggerListViewWindow(DebuggerWindow):
    def __init__(self):
        DebuggerWindow.__init__(self, win32ui.CreateListCtrl())

    def CreateWindow(self, parent):
        list = self
        style = (
            win32con.WS_CHILD
            | win32con.WS_VISIBLE
            | win32con.WS_BORDER
            | commctrl.LVS_EDITLABELS
            | commctrl.LVS_REPORT
        )
        self._obj_.CreateWindow(style, self.GetDefRect(), parent, win32ui.IDC_LIST1)
        self.HookMessage(self.OnKeyDown, win32con.WM_KEYDOWN)
        self.HookMessage(self.OnKeyDown, win32con.WM_SYSKEYDOWN)
        list = self
        title, width = self.columns[0]
        itemDetails = (commctrl.LVCFMT_LEFT, width, title, 0)
        list.InsertColumn(0, itemDetails)
        col = 1
        for title, width in self.columns[1:]:
            col += 1
            itemDetails = (commctrl.LVCFMT_LEFT, width, title, 0)
            list.InsertColumn(col, itemDetails)
        parent.HookNotify(self.OnListEndLabelEdit, LVN_ENDLABELEDIT)
        parent.HookNotify(self.OnItemRightClick, commctrl.NM_RCLICK)
        parent.HookNotify(self.OnItemDoubleClick, commctrl.NM_DBLCLK)

    def RespondDebuggerData(self):
        pass

    def RespondDebuggerState(self, state):
        pass

    def EditSelected(self):
        try:
            sel = self.GetNextItem(-1, commctrl.LVNI_SELECTED)
        except win32ui.error:
            return
        self.EditLabel(sel)

    def OnKeyDown(self, msg):
        key = msg[2]
        # If someone starts typing, they probably are trying to edit the text!
        if chr(key) in string.ascii_uppercase:
            self.EditSelected()
            return 0
        return DebuggerWindow.OnKeyDown(self, msg)

    def OnItemDoubleClick(self, notify_data, extra):
        self.EditSelected()

    def OnItemRightClick(self, notify_data, extra):
        # First select the item we right-clicked on.
        pt = self.ScreenToClient(win32api.GetCursorPos())
        flags, hItem, subitem = self.HitTest(pt)
        if hItem == -1 or commctrl.TVHT_ONITEM & flags == 0:
            return None
        self.SetItemState(hItem, commctrl.LVIS_SELECTED, commctrl.LVIS_SELECTED)

        menu = win32ui.CreatePopupMenu()
        menu.AppendMenu(win32con.MF_STRING | win32con.MF_ENABLED, 1000, "Edit item")
        menu.AppendMenu(win32con.MF_STRING | win32con.MF_ENABLED, 1001, "Delete item")
        dockbar = self.GetParent()
        if dockbar.IsFloating():
            hook_parent = win32ui.GetMainFrame()
        else:
            hook_parent = self.GetParentFrame()
        hook_parent.HookCommand(self.OnEditItem, 1000)
        hook_parent.HookCommand(self.OnDeleteItem, 1001)
        menu.TrackPopupMenu(win32api.GetCursorPos())  # track at mouse position.
        return None

    def OnDeleteItem(self, command, code):
        self.DeleteSelected()

    def OnEditItem(self, command, code):
        self.EditSelected()


class DebuggerBreakpointsWindow(DebuggerListViewWindow):
    title = "Breakpoints"
    columns = [("Condition", 70), ("Location", 1024)]

    def SaveState(self):
        items = []
        for i in range(self.GetItemCount()):
            items.append(self.GetItemText(i, 0))
            items.append(self.GetItemText(i, 1))
        win32ui.WriteProfileVal(
            "Debugger Windows\\" + self.title, "BreakpointList", "\t".join(items)
        )
        win32ui.WriteProfileVal(
            "Debugger Windows\\" + self.title, "Visible", self.IsWindowVisible()
        )
        return 1

    def OnListEndLabelEdit(self, std, extra):
        item = extra[0]
        text = item[4]
        if text is None:
            return

        item_id = self.GetItem(item[0])[6]

        from bdb import Breakpoint

        for bplist in Breakpoint.bplist.values():
            for bp in bplist:
                if id(bp) == item_id:
                    if text.strip().lower() == "none":
                        text = None
                    bp.cond = text
                    break
        self.RespondDebuggerData()

    def DeleteSelected(self):
        try:
            num = self.GetNextItem(-1, commctrl.LVNI_SELECTED)
            item_id = self.GetItem(num)[6]
            from bdb import Breakpoint

            for bplist in Breakpoint.bplist.values():
                for bp in bplist:
                    if id(bp) == item_id:
                        self.debugger.clear_break(bp.file, bp.line)
                        break
        except win32ui.error:
            win32api.MessageBeep()
        self.RespondDebuggerData()

    def RespondDebuggerData(self):
        l = self
        l.DeleteAllItems()
        index = -1
        from bdb import Breakpoint

        for bplist in Breakpoint.bplist.values():
            for bp in bplist:
                baseName = os.path.split(bp.file)[1]
                cond = bp.cond
                item = index + 1, 0, 0, 0, str(cond), 0, id(bp)
                index = l.InsertItem(item)
                l.SetItemText(index, 1, f"{baseName}: {bp.line}")


class DebuggerWatchWindow(DebuggerListViewWindow):
    title = "Watch"
    columns = [("Expression", 70), ("Value", 1024)]

    def CreateWindow(self, parent):
        DebuggerListViewWindow.CreateWindow(self, parent)
        items = win32ui.GetProfileVal(
            "Debugger Windows\\" + self.title, "Items", ""
        ).split("\t")
        index = -1
        for item in items:
            if item:
                index = self.InsertItem(index + 1, item)
        self.InsertItem(index + 1, "<New Item>")

    def SaveState(self):
        items = []
        for i in range(self.GetItemCount() - 1):
            items.append(self.GetItemText(i, 0))
        win32ui.WriteProfileVal(
            "Debugger Windows\\" + self.title, "Items", "\t".join(items)
        )
        win32ui.WriteProfileVal(
            "Debugger Windows\\" + self.title, "Visible", self.IsWindowVisible()
        )
        return 1

    def OnListEndLabelEdit(self, std, extra):
        item = extra[0]
        itemno = item[0]
        text = item[4]
        if text is None:
            return
        self.SetItemText(itemno, 0, text)
        if itemno == self.GetItemCount() - 1:
            self.InsertItem(itemno + 1, "<New Item>")
        self.RespondDebuggerState(self.debugger.debuggerState)

    def DeleteSelected(self):
        try:
            num = self.GetNextItem(-1, commctrl.LVNI_SELECTED)
            if num < self.GetItemCount() - 1:  # We can't delete the last
                self.DeleteItem(num)
        except win32ui.error:
            win32api.MessageBeep()

    def RespondDebuggerState(self, state):
        globs = locs = None
        if state == DBGSTATE_BREAK:
            if self.debugger.curframe:
                globs = self.debugger.curframe.f_globals
                locs = self.debugger.curframe.f_locals
        elif state == DBGSTATE_NOT_DEBUGGING:
            import __main__

            globs = locs = __main__.__dict__
        for i in range(self.GetItemCount() - 1):
            text = self.GetItemText(i, 0)
            if globs is None:
                val = ""
            else:
                try:
                    val = repr(eval(text, globs, locs))
                except SyntaxError:
                    val = "Syntax Error"
                except:
                    t, v, tb = sys.exc_info()
                    val = traceback.format_exception_only(t, v)[0].strip()
                    tb = None  # prevent a cycle.
            self.SetItemText(i, 1, val)


def CreateDebuggerDialog(parent, klass):
    control = klass()
    control.CreateWindow(parent)
    return control


DebuggerDialogInfos = (
    (0xE810, DebuggerStackWindow, None),
    (0xE811, DebuggerBreakpointsWindow, (10, 10)),
    (0xE812, DebuggerWatchWindow, None),
)


# Prepare all the "control bars" for this package.
# If control bars are not all loaded when the toolbar-state functions are
# called, things go horribly wrong.
def PrepareControlBars(frame):
    style = (
        win32con.WS_CHILD
        | afxres.CBRS_SIZE_DYNAMIC
        | afxres.CBRS_TOP
        | afxres.CBRS_TOOLTIPS
        | afxres.CBRS_FLYBY
    )
    tbd = win32ui.CreateToolBar(frame, style, win32ui.ID_VIEW_TOOLBAR_DBG)
    tbd.ModifyStyle(0, commctrl.TBSTYLE_FLAT)
    tbd.LoadToolBar(win32ui.IDR_DEBUGGER)
    tbd.EnableDocking(afxres.CBRS_ALIGN_ANY)
    tbd.SetWindowText("Debugger")
    frame.DockControlBar(tbd)

    # and the other windows.
    for id, klass, float in DebuggerDialogInfos:
        try:
            frame.GetControlBar(id)
            exists = 1
        except win32ui.error:
            exists = 0
        if exists:
            continue
        bar = pywin.docking.DockingBar.DockingBar()
        style = win32con.WS_CHILD | afxres.CBRS_LEFT  # don't create visible.
        bar.CreateWindow(
            frame,
            CreateDebuggerDialog,
            klass.title,
            id,
            style,
            childCreatorArgs=(klass,),
        )
        bar.SetBarStyle(
            bar.GetBarStyle()
            | afxres.CBRS_TOOLTIPS
            | afxres.CBRS_FLYBY
            | afxres.CBRS_SIZE_DYNAMIC
        )
        bar.EnableDocking(afxres.CBRS_ALIGN_ANY)
        if float is None:
            frame.DockControlBar(bar)
        else:
            frame.FloatControlBar(bar, float, afxres.CBRS_ALIGN_ANY)

        ## frame.ShowControlBar(bar, 0, 1)


SKIP_NONE = 0
SKIP_STEP = 1
SKIP_RUN = 2

debugger_parent = pdb.Pdb


class Debugger(debugger_parent):
    def __init__(self):
        self.inited = 0
        self.skipBotFrame = SKIP_NONE
        self.userbotframe = None
        self.frameShutdown = 0
        self.pumping = 0
        self.debuggerState = DBGSTATE_NOT_DEBUGGING  # Assume so, anyway.
        self.shownLineCurrent = None  # The last filename I highlighted.
        self.shownLineCallstack = None  # The last filename I highlighted.
        self.last_cmd_debugged = ""
        self.abortClosed = 0
        self.isInitialBreakpoint = 0
        debugger_parent.__init__(self)

        # See if any break-points have been set in the editor
        for doc in editor.editorTemplate.GetDocumentList():
            lineNo = -1
            while 1:
                lineNo = doc.MarkerGetNext(lineNo + 1, MARKER_BREAKPOINT)
                if lineNo <= 0:
                    break
                self.set_break(doc.GetPathName(), lineNo)

        self.reset()
        self.inForcedGUI = win32ui.GetApp().IsInproc()
        self.options = LoadDebuggerOptions()
        self.bAtException = self.bAtPostMortem = 0

    def __del__(self):
        self.close()

    def close(self, frameShutdown=0):
        # abortClose indicates if we have total shutdown
        # (ie, main window is dieing)
        if self.pumping:
            # Can stop pump here, as it only posts a message, and
            # returns immediately.
            if not self.StopDebuggerPump():  # User cancelled close.
                return 0
            # NOTE - from this point on the close can not be
            # stopped - the WM_QUIT message is already in the queue.
        self.frameShutdown = frameShutdown
        if not self.inited:
            return 1
        self.inited = 0

        SetInteractiveContext(None, None)

        frame = win32ui.GetMainFrame()
        # Hide the debuger toolbars (as they won't normally form part of the main toolbar state.
        for id, klass, float in DebuggerDialogInfos:
            try:
                tb = frame.GetControlBar(id)
                if tb.dialog is not None:  # We may never have actually been shown.
                    tb.dialog.SaveState()
                    frame.ShowControlBar(tb, 0, 1)
            except win32ui.error:
                pass

        self._UnshowCurrentLine()
        self.set_quit()
        return 1

    def StopDebuggerPump(self):
        assert self.pumping, "Can't stop the debugger pump if I'm not pumping!"
        # After stopping a pump, I may never return.
        if self.GUIAboutToFinishInteract():
            self.pumping = 0
            win32ui.StopDebuggerPump()  # Posts a message, so we do return.
            return 1
        return 0

    def get_option(self, option):
        """Public interface into debugger options"""
        try:
            return self.options[option]
        except KeyError as error:
            raise KeyError(f"Option {option} is not a valid option") from error

    def prep_run(self, cmd):
        pass

    def done_run(self, cmd=None):
        self.RespondDebuggerState(DBGSTATE_NOT_DEBUGGING)
        self.close()

    def canonic(self, fname):
        return os.path.abspath(fname).lower()

    def reset(self):
        debugger_parent.reset(self)
        self.userbotframe = None
        self.UpdateAllLineStates()
        self._UnshowCurrentLine()

    def setup(self, f, t):
        debugger_parent.setup(self, f, t)
        self.bAtException = t is not None

    def set_break(self, filename, lineno, temporary=0, cond=None):
        filename = self.canonic(filename)
        self.SetLineState(filename, lineno, LINESTATE_BREAKPOINT)
        return debugger_parent.set_break(self, filename, lineno, temporary, cond)

    def clear_break(self, filename, lineno):
        filename = self.canonic(filename)
        self.ResetLineState(filename, lineno, LINESTATE_BREAKPOINT)
        return debugger_parent.clear_break(self, filename, lineno)

    def cmdloop(self):
        if self.frameShutdown:
            return  # App in the process of closing - never break in!
        self.GUIAboutToBreak()

    def print_stack_entry(self, frame):
        # We don't want a stack printed - our GUI is better :-)
        pass

    def user_return(self, frame, return_value):
        # Same as parent, just no "print"
        # This function is called when a return trap is set here
        frame.f_locals["__return__"] = return_value
        self.interaction(frame, None)

    def user_call(self, frame, args):
        # base class has an annoying 'print' that adds no value to us...
        if self.stop_here(frame):
            self.interaction(frame, None)

    def user_exception(self, frame, exc_info):
        # This function is called if an exception occurs,
        # but only if we are to stop at or just below this level
        (exc_type, exc_value, exc_traceback) = exc_info
        if self.get_option(OPT_STOP_EXCEPTIONS):
            frame.f_locals["__exception__"] = exc_type, exc_value
            print("Unhandled exception while debugging...")
            # We may be called with exc_value
            # being the args to the exception, or it may already be
            # instantiated (IOW, PyErr_Normalize() hasn't been
            # called on the args). traceback.print_exception fails.
            # So we instantiate an exception instance to print.
            if not isinstance(exc_value, BaseException):
                # they are args - may be a single item or already a tuple
                if not isinstance(exc_value, tuple):
                    exc_value = (exc_value,)
                exc_value = exc_type(*exc_value)

            traceback.print_exception(exc_type, exc_value, exc_traceback)
            self.interaction(frame, exc_traceback)

    def user_line(self, frame):
        if frame.f_lineno == 0:
            return
        debugger_parent.user_line(self, frame)

    def stop_here(self, frame):
        if self.isInitialBreakpoint:
            self.isInitialBreakpoint = 0
            self.set_continue()
            return 0
        if frame is self.botframe and self.skipBotFrame == SKIP_RUN:
            self.set_continue()
            return 0
        if frame is self.botframe and self.skipBotFrame == SKIP_STEP:
            self.set_step()
            return 0
        return debugger_parent.stop_here(self, frame)

    def run(self, cmd, globals=None, locals=None, start_stepping=1):
        if not isinstance(cmd, (str, types.CodeType)):
            raise TypeError("Only strings can be run")
        self.last_cmd_debugged = cmd
        if start_stepping:
            self.isInitialBreakpoint = 0
        else:
            self.isInitialBreakpoint = 1
        try:
            if globals is None:
                import __main__

                globals = __main__.__dict__
            if locals is None:
                locals = globals
            self.reset()
            self.prep_run(cmd)
            sys.settrace(self.trace_dispatch)
            if not isinstance(cmd, types.CodeType):
                cmd += "\n"
            try:
                try:
                    if start_stepping:
                        self.skipBotFrame = SKIP_STEP
                    else:
                        self.skipBotFrame = SKIP_RUN
                    exec(cmd, globals, locals)
                except bdb.BdbQuit:
                    pass
            finally:
                self.skipBotFrame = SKIP_NONE
                self.quitting = 1
                sys.settrace(None)

        finally:
            self.done_run(cmd)

    def runeval(self, expr, globals=None, locals=None):
        self.prep_run(expr)
        try:
            debugger_parent.runeval(self, expr, globals, locals)
        finally:
            self.done_run(expr)

    def runexec(self, what, globs=None, locs=None):
        self.reset()
        sys.settrace(self.trace_dispatch)
        try:
            try:
                exec(what, globs, locs)
            except bdb.BdbQuit:
                pass
        finally:
            self.quitting = 1
            sys.settrace(None)

    def do_set_step(self):
        if self.GUIAboutToRun():
            self.set_step()

    def do_set_next(self):
        if self.GUIAboutToRun():
            self.set_next(self.curframe)

    def do_set_return(self):
        if self.GUIAboutToRun():
            self.set_return(self.curframe)

    def do_set_continue(self):
        if self.GUIAboutToRun():
            self.set_continue()

    def set_quit(self):
        ok = 1
        if self.pumping:
            ok = self.StopDebuggerPump()
        if ok:
            debugger_parent.set_quit(self)

    def _dump_frame_(self, frame, name=None):
        if name is None:
            name = ""
        if frame:
            if frame.f_code and frame.f_code.co_filename:
                fname = os.path.split(frame.f_code.co_filename)[1]
            else:
                fname = "??"
            print(repr(name), fname, frame.f_lineno, frame)
        else:
            print(repr(name), "None")

    def set_trace(self):
        # Start debugging from _2_ levels up!
        try:
            1 + ""
        except:
            frame = sys.exc_info()[2].tb_frame.f_back.f_back
        self.reset()
        self.userbotframe = None
        while frame:
            # scriptutils.py creates a local variable with name
            # '_debugger_stop_frame_', and we don't go past it
            # (everything above this is Pythonwin framework code)
            if "_debugger_stop_frame_" in frame.f_locals:
                self.userbotframe = frame
                break

            frame.f_trace = self.trace_dispatch
            self.botframe = frame
            frame = frame.f_back
        self.set_step()
        sys.settrace(self.trace_dispatch)

    def set_cur_frame(self, frame):
        # Sets the "current" frame - ie, the frame with focus.  This is the
        # frame on which "step out" etc actions are taken.
        # This may or may not be the top of the stack.
        assert frame is not None, "You must pass a valid frame"
        self.curframe = frame
        for f, index in self.stack:
            if f is frame:
                self.curindex = index
                break
        else:
            assert False, "Can't find the frame in the stack."
        SetInteractiveContext(frame.f_globals, frame.f_locals)
        self.GUIRespondDebuggerData()
        self.ShowCurrentLine()

    def IsBreak(self):
        return self.debuggerState == DBGSTATE_BREAK

    def IsDebugging(self):
        return self.debuggerState != DBGSTATE_NOT_DEBUGGING

    def RespondDebuggerState(self, state):
        if state == self.debuggerState:
            return
        if state == DBGSTATE_NOT_DEBUGGING:  # Debugger exists, but not doing anything
            title = ""
        elif state == DBGSTATE_RUNNING:  # Code is running under the debugger.
            title = " - running"
        elif state == DBGSTATE_BREAK:  # We are at a breakpoint or stepping or whatever.
            if not self.bAtException:
                title = " - break"
            elif self.bAtPostMortem:
                title = " - post mortem exception"
            else:
                title = " - exception"
        else:
            raise ValueError("Invalid debugger state passed!")
        win32ui.GetMainFrame().SetWindowText(
            win32ui.LoadString(win32ui.IDR_MAINFRAME) + title
        )
        if self.debuggerState == DBGSTATE_QUITTING and state != DBGSTATE_NOT_DEBUGGING:
            print("Ignoring state change cos I'm trying to stop!", state)
            return
        self.debuggerState = state
        try:
            frame = win32ui.GetMainFrame()
        except win32ui.error:
            frame = None
        if frame is not None:
            for id, klass, float in DebuggerDialogInfos:
                cb = win32ui.GetMainFrame().GetControlBar(id).dialog
                cb.RespondDebuggerState(state)
        # Tell each open editor window about the state transition
        for doc in editor.editorTemplate.GetDocumentList():
            doc.OnDebuggerStateChange(state)
        self.ShowCurrentLine()

    #
    # GUI debugger interface.
    #
    def GUICheckInit(self):
        if self.inited:
            return
        self.inited = 1
        frame = win32ui.GetMainFrame()

        # Ensure the debugger windows are attached to the debugger.
        for id, klass, float in DebuggerDialogInfos:
            w = frame.GetControlBar(id)
            w.dialog.Init(self)
            # Show toolbar if it was visible during last debug session
            # This would be better done using a CDockState, but that class is not wrapped yet
            if win32ui.GetProfileVal(
                "Debugger Windows\\" + w.dialog.title, "Visible", 0
            ):
                frame.ShowControlBar(w, 1, 1)

        # ALWAYS show debugging toolbar, regardless of saved state
        tb = frame.GetControlBar(win32ui.ID_VIEW_TOOLBAR_DBG)
        frame.ShowControlBar(tb, 1, 1)
        self.GUIRespondDebuggerData()

    # 		frame.RecalcLayout()

    def GetDebuggerBar(self, barName):
        frame = win32ui.GetMainFrame()
        for id, klass, float in DebuggerDialogInfos:
            if klass.title == barName:
                return frame.GetControlBar(id)
        assert False, "Can't find a bar of that name!"

    def GUIRespondDebuggerData(self):
        if not self.inited:  # GUI not inited - no toolbars etc.
            return

        for id, klass, float in DebuggerDialogInfos:
            cb = win32ui.GetMainFrame().GetControlBar(id).dialog
            cb.RespondDebuggerData()

    def GUIAboutToRun(self):
        if not self.StopDebuggerPump():
            return 0
        self._UnshowCurrentLine()
        self.RespondDebuggerState(DBGSTATE_RUNNING)
        SetInteractiveContext(None, None)
        return 1

    def GUIAboutToBreak(self):
        "Called as the GUI debugger is about to get context, and take control of the running program."
        self.GUICheckInit()
        self.RespondDebuggerState(DBGSTATE_BREAK)
        self.GUIAboutToInteract()
        if self.pumping:
            print("!!! Already pumping - outa here")
            return
        self.pumping = 1
        win32ui.StartDebuggerPump()  # NOTE - This will NOT return until the user is finished interacting
        assert not self.pumping, "Should not be pumping once the pump has finished"
        if self.frameShutdown:  # User shut down app while debugging
            win32ui.GetMainFrame().PostMessage(win32con.WM_CLOSE)

    def GUIAboutToInteract(self):
        "Called as the GUI is about to perform any interaction with the user"
        frame = win32ui.GetMainFrame()
        # Remember the enabled state of our main frame
        # may be disabled primarily if a modal dialog is displayed.
        # Only get at enabled via GetWindowLong.
        self.bFrameEnabled = frame.IsWindowEnabled()
        self.oldForeground = None
        fw = win32ui.GetForegroundWindow()
        if fw is not frame:
            self.oldForeground = fw
            # 			fw.EnableWindow(0) Leave enabled for now?
            self.oldFrameEnableState = frame.IsWindowEnabled()
            frame.EnableWindow(1)
        if self.inForcedGUI and not frame.IsWindowVisible():
            frame.ShowWindow(win32con.SW_SHOW)
            frame.UpdateWindow()
        if self.curframe:
            SetInteractiveContext(self.curframe.f_globals, self.curframe.f_locals)
        else:
            SetInteractiveContext(None, None)
        self.GUIRespondDebuggerData()

    def GUIAboutToFinishInteract(self):
        """Called as the GUI is about to finish any interaction with the user
        Returns non zero if we are allowed to stop interacting"""
        if self.oldForeground is not None:
            try:
                win32ui.GetMainFrame().EnableWindow(self.oldFrameEnableState)
                self.oldForeground.EnableWindow(1)
            except win32ui.error:
                # old window may be dead.
                pass
        # 			self.oldForeground.SetForegroundWindow() - fails??
        if not self.inForcedGUI:
            return 1  # Never a problem, and nothing else to do.
        # If we are running a forced GUI, we may never get an opportunity
        # to interact again.  Therefore we perform a "SaveAll", to makesure that
        # any documents are saved before leaving.
        for template in win32ui.GetApp().GetDocTemplateList():
            for doc in template.GetDocumentList():
                if not doc.SaveModified():
                    return 0
        # All documents saved - now hide the app and debugger.
        if self.get_option(OPT_HIDE):
            frame = win32ui.GetMainFrame()
            frame.ShowWindow(win32con.SW_HIDE)
        return 1

    #
    # Pythonwin interface - all stuff to do with showing source files,
    # changing line states etc.
    #
    def ShowLineState(self, fileName, lineNo, lineState):
        # Set the state of a line, open if not already
        self.ShowLineNo(fileName, lineNo)
        self.SetLineState(fileName, lineNo, lineState)

    def SetLineState(self, fileName, lineNo, lineState):
        # Set the state of a line if the document is open.
        doc = editor.editorTemplate.FindOpenDocument(fileName)
        if doc is not None:
            marker = _LineStateToMarker(lineState)
            if not doc.MarkerCheck(lineNo, marker):
                doc.MarkerAdd(lineNo, marker)

    def ResetLineState(self, fileName, lineNo, lineState):
        # Set the state of a line if the document is open.
        doc = editor.editorTemplate.FindOpenDocument(fileName)
        if doc is not None:
            marker = _LineStateToMarker(lineState)
            doc.MarkerDelete(lineNo, marker)

    def UpdateDocumentLineStates(self, doc):
        # Show all lines in their special status color.  If the doc is open
        # all line states are reset.
        doc.MarkerDeleteAll(MARKER_BREAKPOINT)
        doc.MarkerDeleteAll(MARKER_CURRENT)
        fname = self.canonic(doc.GetPathName())
        # Now loop over all break-points
        for line in self.breaks.get(fname, []):
            doc.MarkerAdd(line, MARKER_BREAKPOINT)
        # And the current line if in this document.
        if self.shownLineCurrent and fname == self.shownLineCurrent[0]:
            lineNo = self.shownLineCurrent[1]
            if not doc.MarkerCheck(lineNo, MARKER_CURRENT):
                doc.MarkerAdd(lineNo, MARKER_CURRENT)

    # 		if self.shownLineCallstack and fname == self.shownLineCallstack[0]:
    # 			doc.MarkerAdd(self.shownLineCallstack[1], MARKER_CURRENT)

    def UpdateAllLineStates(self):
        for doc in editor.editorTemplate.GetDocumentList():
            self.UpdateDocumentLineStates(doc)

    def ShowCurrentLine(self):
        # Show the current line.  Only ever 1 current line - undoes last current
        # The "Current Line" is self.curframe.
        # The "Callstack Line" is the top of the stack.
        # If current == callstack, only show as current.
        self._UnshowCurrentLine()  # un-highlight the old one.
        if self.curframe:
            fileName = self.canonic(self.curframe.f_code.co_filename)
            lineNo = self.curframe.f_lineno
            self.shownLineCurrent = fileName, lineNo
            self.ShowLineState(fileName, lineNo, LINESTATE_CURRENT)

    def _UnshowCurrentLine(self):
        "Unshow the current line, and forget it"
        if self.shownLineCurrent is not None:
            fname, lineno = self.shownLineCurrent
            self.ResetLineState(fname, lineno, LINESTATE_CURRENT)
            self.shownLineCurrent = None

    def ShowLineNo(self, filename, lineno):
        wasOpen = editor.editorTemplate.FindOpenDocument(filename) is not None
        if os.path.isfile(filename) and scriptutils.JumpToDocument(filename, lineno):
            if not wasOpen:
                doc = editor.editorTemplate.FindOpenDocument(filename)
                if doc is not None:
                    self.UpdateDocumentLineStates(doc)
                    return 1
                return 0
            return 1
        else:
            # Can't find the source file - linecache may have it?
            import linecache

            line = linecache.getline(filename, lineno)
            print(
                "%s(%d): %s"
                % (os.path.basename(filename), lineno, line[:-1].expandtabs(4))
            )
            return 0

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\requests\utils.py ===
"""
requests.utils
~~~~~~~~~~~~~~

This module provides utility functions that are used within Requests
that are also useful for external consumption.
"""

import codecs
import contextlib
import io
import os
import re
import socket
import struct
import sys
import tempfile
import warnings
import zipfile
from collections import OrderedDict

from pip._vendor.urllib3.util import make_headers, parse_url

from . import certs
from .__version__ import __version__

# to_native_string is unused here, but imported here for backwards compatibility
from ._internal_utils import (  # noqa: F401
    _HEADER_VALIDATORS_BYTE,
    _HEADER_VALIDATORS_STR,
    HEADER_VALIDATORS,
    to_native_string,
)
from .compat import (
    Mapping,
    basestring,
    bytes,
    getproxies,
    getproxies_environment,
    integer_types,
)
from .compat import parse_http_list as _parse_list_header
from .compat import (
    proxy_bypass,
    proxy_bypass_environment,
    quote,
    str,
    unquote,
    urlparse,
    urlunparse,
)
from .cookies import cookiejar_from_dict
from .exceptions import (
    FileModeWarning,
    InvalidHeader,
    InvalidURL,
    UnrewindableBodyError,
)
from .structures import CaseInsensitiveDict

NETRC_FILES = (".netrc", "_netrc")

DEFAULT_CA_BUNDLE_PATH = certs.where()

DEFAULT_PORTS = {"http": 80, "https": 443}

# Ensure that ', ' is used to preserve previous delimiter behavior.
DEFAULT_ACCEPT_ENCODING = ", ".join(
    re.split(r",\s*", make_headers(accept_encoding=True)["accept-encoding"])
)


if sys.platform == "win32":
    # provide a proxy_bypass version on Windows without DNS lookups

    def proxy_bypass_registry(host):
        try:
            import winreg
        except ImportError:
            return False

        try:
            internetSettings = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            )
            # ProxyEnable could be REG_SZ or REG_DWORD, normalizing it
            proxyEnable = int(winreg.QueryValueEx(internetSettings, "ProxyEnable")[0])
            # ProxyOverride is almost always a string
            proxyOverride = winreg.QueryValueEx(internetSettings, "ProxyOverride")[0]
        except (OSError, ValueError):
            return False
        if not proxyEnable or not proxyOverride:
            return False

        # make a check value list from the registry entry: replace the
        # '<local>' string by the localhost entry and the corresponding
        # canonical entry.
        proxyOverride = proxyOverride.split(";")
        # filter out empty strings to avoid re.match return true in the following code.
        proxyOverride = filter(None, proxyOverride)
        # now check if we match one of the registry values.
        for test in proxyOverride:
            if test == "<local>":
                if "." not in host:
                    return True
            test = test.replace(".", r"\.")  # mask dots
            test = test.replace("*", r".*")  # change glob sequence
            test = test.replace("?", r".")  # change glob char
            if re.match(test, host, re.I):
                return True
        return False

    def proxy_bypass(host):  # noqa
        """Return True, if the host should be bypassed.

        Checks proxy settings gathered from the environment, if specified,
        or the registry.
        """
        if getproxies_environment():
            return proxy_bypass_environment(host)
        else:
            return proxy_bypass_registry(host)


def dict_to_sequence(d):
    """Returns an internal sequence dictionary update."""

    if hasattr(d, "items"):
        d = d.items()

    return d


def super_len(o):
    total_length = None
    current_position = 0

    if isinstance(o, str):
        o = o.encode("utf-8")

    if hasattr(o, "__len__"):
        total_length = len(o)

    elif hasattr(o, "len"):
        total_length = o.len

    elif hasattr(o, "fileno"):
        try:
            fileno = o.fileno()
        except (io.UnsupportedOperation, AttributeError):
            # AttributeError is a surprising exception, seeing as how we've just checked
            # that `hasattr(o, 'fileno')`.  It happens for objects obtained via
            # `Tarfile.extractfile()`, per issue 5229.
            pass
        else:
            total_length = os.fstat(fileno).st_size

            # Having used fstat to determine the file length, we need to
            # confirm that this file was opened up in binary mode.
            if "b" not in o.mode:
                warnings.warn(
                    (
                        "Requests has determined the content-length for this "
                        "request using the binary size of the file: however, the "
                        "file has been opened in text mode (i.e. without the 'b' "
                        "flag in the mode). This may lead to an incorrect "
                        "content-length. In Requests 3.0, support will be removed "
                        "for files in text mode."
                    ),
                    FileModeWarning,
                )

    if hasattr(o, "tell"):
        try:
            current_position = o.tell()
        except OSError:
            # This can happen in some weird situations, such as when the file
            # is actually a special file descriptor like stdin. In this
            # instance, we don't know what the length is, so set it to zero and
            # let requests chunk it instead.
            if total_length is not None:
                current_position = total_length
        else:
            if hasattr(o, "seek") and total_length is None:
                # StringIO and BytesIO have seek but no usable fileno
                try:
                    # seek to end of file
                    o.seek(0, 2)
                    total_length = o.tell()

                    # seek back to current position to support
                    # partially read file-like objects
                    o.seek(current_position or 0)
                except OSError:
                    total_length = 0

    if total_length is None:
        total_length = 0

    return max(0, total_length - current_position)


def get_netrc_auth(url, raise_errors=False):
    """Returns the Requests tuple auth for a given url from netrc."""

    netrc_file = os.environ.get("NETRC")
    if netrc_file is not None:
        netrc_locations = (netrc_file,)
    else:
        netrc_locations = (f"~/{f}" for f in NETRC_FILES)

    try:
        from netrc import NetrcParseError, netrc

        netrc_path = None

        for f in netrc_locations:
            try:
                loc = os.path.expanduser(f)
            except KeyError:
                # os.path.expanduser can fail when $HOME is undefined and
                # getpwuid fails. See https://bugs.python.org/issue20164 &
                # https://github.com/psf/requests/issues/1846
                return

            if os.path.exists(loc):
                netrc_path = loc
                break

        # Abort early if there isn't one.
        if netrc_path is None:
            return

        ri = urlparse(url)

        # Strip port numbers from netloc. This weird `if...encode`` dance is
        # used for Python 3.2, which doesn't support unicode literals.
        splitstr = b":"
        if isinstance(url, str):
            splitstr = splitstr.decode("ascii")
        host = ri.netloc.split(splitstr)[0]

        try:
            _netrc = netrc(netrc_path).authenticators(host)
            if _netrc:
                # Return with login / password
                login_i = 0 if _netrc[0] else 1
                return (_netrc[login_i], _netrc[2])
        except (NetrcParseError, OSError):
            # If there was a parsing error or a permissions issue reading the file,
            # we'll just skip netrc auth unless explicitly asked to raise errors.
            if raise_errors:
                raise

    # App Engine hackiness.
    except (ImportError, AttributeError):
        pass


def guess_filename(obj):
    """Tries to guess the filename of the given object."""
    name = getattr(obj, "name", None)
    if name and isinstance(name, basestring) and name[0] != "<" and name[-1] != ">":
        return os.path.basename(name)


def extract_zipped_paths(path):
    """Replace nonexistent paths that look like they refer to a member of a zip
    archive with the location of an extracted copy of the target, or else
    just return the provided path unchanged.
    """
    if os.path.exists(path):
        # this is already a valid path, no need to do anything further
        return path

    # find the first valid part of the provided path and treat that as a zip archive
    # assume the rest of the path is the name of a member in the archive
    archive, member = os.path.split(path)
    while archive and not os.path.exists(archive):
        archive, prefix = os.path.split(archive)
        if not prefix:
            # If we don't check for an empty prefix after the split (in other words, archive remains unchanged after the split),
            # we _can_ end up in an infinite loop on a rare corner case affecting a small number of users
            break
        member = "/".join([prefix, member])

    if not zipfile.is_zipfile(archive):
        return path

    zip_file = zipfile.ZipFile(archive)
    if member not in zip_file.namelist():
        return path

    # we have a valid zip archive and a valid member of that archive
    tmp = tempfile.gettempdir()
    extracted_path = os.path.join(tmp, member.split("/")[-1])
    if not os.path.exists(extracted_path):
        # use read + write to avoid the creating nested folders, we only want the file, avoids mkdir racing condition
        with atomic_open(extracted_path) as file_handler:
            file_handler.write(zip_file.read(member))
    return extracted_path


@contextlib.contextmanager
def atomic_open(filename):
    """Write a file to the disk in an atomic fashion"""
    tmp_descriptor, tmp_name = tempfile.mkstemp(dir=os.path.dirname(filename))
    try:
        with os.fdopen(tmp_descriptor, "wb") as tmp_handler:
            yield tmp_handler
        os.replace(tmp_name, filename)
    except BaseException:
        os.remove(tmp_name)
        raise


def from_key_val_list(value):
    """Take an object and test to see if it can be represented as a
    dictionary. Unless it can not be represented as such, return an
    OrderedDict, e.g.,

    ::

        >>> from_key_val_list([('key', 'val')])
        OrderedDict([('key', 'val')])
        >>> from_key_val_list('string')
        Traceback (most recent call last):
        ...
        ValueError: cannot encode objects that are not 2-tuples
        >>> from_key_val_list({'key': 'val'})
        OrderedDict([('key', 'val')])

    :rtype: OrderedDict
    """
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    return OrderedDict(value)


def to_key_val_list(value):
    """Take an object and test to see if it can be represented as a
    dictionary. If it can be, return a list of tuples, e.g.,

    ::

        >>> to_key_val_list([('key', 'val')])
        [('key', 'val')]
        >>> to_key_val_list({'key': 'val'})
        [('key', 'val')]
        >>> to_key_val_list('string')
        Traceback (most recent call last):
        ...
        ValueError: cannot encode objects that are not 2-tuples

    :rtype: list
    """
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    if isinstance(value, Mapping):
        value = value.items()

    return list(value)


# From mitsuhiko/werkzeug (used with permission).
def parse_list_header(value):
    """Parse lists as described by RFC 2068 Section 2.

    In particular, parse comma-separated lists where the elements of
    the list may include quoted-strings.  A quoted-string could
    contain a comma.  A non-quoted string could have quotes in the
    middle.  Quotes are removed automatically after parsing.

    It basically works like :func:`parse_set_header` just that items
    may appear multiple times and case sensitivity is preserved.

    The return value is a standard :class:`list`:

    >>> parse_list_header('token, "quoted value"')
    ['token', 'quoted value']

    To create a header from the :class:`list` again, use the
    :func:`dump_header` function.

    :param value: a string with a list header.
    :return: :class:`list`
    :rtype: list
    """
    result = []
    for item in _parse_list_header(value):
        if item[:1] == item[-1:] == '"':
            item = unquote_header_value(item[1:-1])
        result.append(item)
    return result


# From mitsuhiko/werkzeug (used with permission).
def parse_dict_header(value):
    """Parse lists of key, value pairs as described by RFC 2068 Section 2 and
    convert them into a python dict:

    >>> d = parse_dict_header('foo="is a fish", bar="as well"')
    >>> type(d) is dict
    True
    >>> sorted(d.items())
    [('bar', 'as well'), ('foo', 'is a fish')]

    If there is no value for a key it will be `None`:

    >>> parse_dict_header('key_without_value')
    {'key_without_value': None}

    To create a header from the :class:`dict` again, use the
    :func:`dump_header` function.

    :param value: a string with a dict header.
    :return: :class:`dict`
    :rtype: dict
    """
    result = {}
    for item in _parse_list_header(value):
        if "=" not in item:
            result[item] = None
            continue
        name, value = item.split("=", 1)
        if value[:1] == value[-1:] == '"':
            value = unquote_header_value(value[1:-1])
        result[name] = value
    return result


# From mitsuhiko/werkzeug (used with permission).
def unquote_header_value(value, is_filename=False):
    r"""Unquotes a header value.  (Reversal of :func:`quote_header_value`).
    This does not use the real unquoting but what browsers are actually
    using for quoting.

    :param value: the header value to unquote.
    :rtype: str
    """
    if value and value[0] == value[-1] == '"':
        # this is not the real unquoting, but fixing this so that the
        # RFC is met will result in bugs with internet explorer and
        # probably some other browsers as well.  IE for example is
        # uploading files with "C:\foo\bar.txt" as filename
        value = value[1:-1]

        # if this is a filename and the starting characters look like
        # a UNC path, then just return the value without quotes.  Using the
        # replace sequence below on a UNC path has the effect of turning
        # the leading double slash into a single slash and then
        # _fix_ie_filename() doesn't work correctly.  See #458.
        if not is_filename or value[:2] != "\\\\":
            return value.replace("\\\\", "\\").replace('\\"', '"')
    return value


def dict_from_cookiejar(cj):
    """Returns a key/value dictionary from a CookieJar.

    :param cj: CookieJar object to extract cookies from.
    :rtype: dict
    """

    cookie_dict = {cookie.name: cookie.value for cookie in cj}
    return cookie_dict


def add_dict_to_cookiejar(cj, cookie_dict):
    """Returns a CookieJar from a key/value dictionary.

    :param cj: CookieJar to insert cookies into.
    :param cookie_dict: Dict of key/values to insert into CookieJar.
    :rtype: CookieJar
    """

    return cookiejar_from_dict(cookie_dict, cj)


def get_encodings_from_content(content):
    """Returns encodings from given content string.

    :param content: bytestring to extract encodings from.
    """
    warnings.warn(
        (
            "In requests 3.0, get_encodings_from_content will be removed. For "
            "more information, please see the discussion on issue #2266. (This"
            " warning should only appear once.)"
        ),
        DeprecationWarning,
    )

    charset_re = re.compile(r'<meta.*?charset=["\']*(.+?)["\'>]', flags=re.I)
    pragma_re = re.compile(r'<meta.*?content=["\']*;?charset=(.+?)["\'>]', flags=re.I)
    xml_re = re.compile(r'^<\?xml.*?encoding=["\']*(.+?)["\'>]')

    return (
        charset_re.findall(content)
        + pragma_re.findall(content)
        + xml_re.findall(content)
    )


def _parse_content_type_header(header):
    """Returns content type and parameters from given header

    :param header: string
    :return: tuple containing content type and dictionary of
         parameters
    """

    tokens = header.split(";")
    content_type, params = tokens[0].strip(), tokens[1:]
    params_dict = {}
    items_to_strip = "\"' "

    for param in params:
        param = param.strip()
        if param:
            key, value = param, True
            index_of_equals = param.find("=")
            if index_of_equals != -1:
                key = param[:index_of_equals].strip(items_to_strip)
                value = param[index_of_equals + 1 :].strip(items_to_strip)
            params_dict[key.lower()] = value
    return content_type, params_dict


def get_encoding_from_headers(headers):
    """Returns encodings from given HTTP Header Dict.

    :param headers: dictionary to extract encoding from.
    :rtype: str
    """

    content_type = headers.get("content-type")

    if not content_type:
        return None

    content_type, params = _parse_content_type_header(content_type)

    if "charset" in params:
        return params["charset"].strip("'\"")

    if "text" in content_type:
        return "ISO-8859-1"

    if "application/json" in content_type:
        # Assume UTF-8 based on RFC 4627: https://www.ietf.org/rfc/rfc4627.txt since the charset was unset
        return "utf-8"


def stream_decode_response_unicode(iterator, r):
    """Stream decodes an iterator."""

    if r.encoding is None:
        yield from iterator
        return

    decoder = codecs.getincrementaldecoder(r.encoding)(errors="replace")
    for chunk in iterator:
        rv = decoder.decode(chunk)
        if rv:
            yield rv
    rv = decoder.decode(b"", final=True)
    if rv:
        yield rv


def iter_slices(string, slice_length):
    """Iterate over slices of a string."""
    pos = 0
    if slice_length is None or slice_length <= 0:
        slice_length = len(string)
    while pos < len(string):
        yield string[pos : pos + slice_length]
        pos += slice_length


def get_unicode_from_response(r):
    """Returns the requested content back in unicode.

    :param r: Response object to get unicode content from.

    Tried:

    1. charset from content-type
    2. fall back and replace all unicode characters

    :rtype: str
    """
    warnings.warn(
        (
            "In requests 3.0, get_unicode_from_response will be removed. For "
            "more information, please see the discussion on issue #2266. (This"
            " warning should only appear once.)"
        ),
        DeprecationWarning,
    )

    tried_encodings = []

    # Try charset from content-type
    encoding = get_encoding_from_headers(r.headers)

    if encoding:
        try:
            return str(r.content, encoding)
        except UnicodeError:
            tried_encodings.append(encoding)

    # Fall back:
    try:
        return str(r.content, encoding, errors="replace")
    except TypeError:
        return r.content


# The unreserved URI characters (RFC 3986)
UNRESERVED_SET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" + "0123456789-._~"
)


def unquote_unreserved(uri):
    """Un-escape any percent-escape sequences in a URI that are unreserved
    characters. This leaves all reserved, illegal and non-ASCII bytes encoded.

    :rtype: str
    """
    parts = uri.split("%")
    for i in range(1, len(parts)):
        h = parts[i][0:2]
        if len(h) == 2 and h.isalnum():
            try:
                c = chr(int(h, 16))
            except ValueError:
                raise InvalidURL(f"Invalid percent-escape sequence: '{h}'")

            if c in UNRESERVED_SET:
                parts[i] = c + parts[i][2:]
            else:
                parts[i] = f"%{parts[i]}"
        else:
            parts[i] = f"%{parts[i]}"
    return "".join(parts)


def requote_uri(uri):
    """Re-quote the given URI.

    This function passes the given URI through an unquote/quote cycle to
    ensure that it is fully and consistently quoted.

    :rtype: str
    """
    safe_with_percent = "!#$%&'()*+,/:;=?@[]~"
    safe_without_percent = "!#$&'()*+,/:;=?@[]~"
    try:
        # Unquote only the unreserved characters
        # Then quote only illegal characters (do not quote reserved,
        # unreserved, or '%')
        return quote(unquote_unreserved(uri), safe=safe_with_percent)
    except InvalidURL:
        # We couldn't unquote the given URI, so let's try quoting it, but
        # there may be unquoted '%'s in the URI. We need to make sure they're
        # properly quoted so they do not cause issues elsewhere.
        return quote(uri, safe=safe_without_percent)


def address_in_network(ip, net):
    """This function allows you to check if an IP belongs to a network subnet

    Example: returns True if ip = 192.168.1.1 and net = 192.168.1.0/24
             returns False if ip = 192.168.1.1 and net = 192.168.100.0/24

    :rtype: bool
    """
    ipaddr = struct.unpack("=L", socket.inet_aton(ip))[0]
    netaddr, bits = net.split("/")
    netmask = struct.unpack("=L", socket.inet_aton(dotted_netmask(int(bits))))[0]
    network = struct.unpack("=L", socket.inet_aton(netaddr))[0] & netmask
    return (ipaddr & netmask) == (network & netmask)


def dotted_netmask(mask):
    """Converts mask from /xx format to xxx.xxx.xxx.xxx

    Example: if mask is 24 function returns 255.255.255.0

    :rtype: str
    """
    bits = 0xFFFFFFFF ^ (1 << 32 - mask) - 1
    return socket.inet_ntoa(struct.pack(">I", bits))


def is_ipv4_address(string_ip):
    """
    :rtype: bool
    """
    try:
        socket.inet_aton(string_ip)
    except OSError:
        return False
    return True


def is_valid_cidr(string_network):
    """
    Very simple check of the cidr format in no_proxy variable.

    :rtype: bool
    """
    if string_network.count("/") == 1:
        try:
            mask = int(string_network.split("/")[1])
        except ValueError:
            return False

        if mask < 1 or mask > 32:
            return False

        try:
            socket.inet_aton(string_network.split("/")[0])
        except OSError:
            return False
    else:
        return False
    return True


@contextlib.contextmanager
def set_environ(env_name, value):
    """Set the environment variable 'env_name' to 'value'

    Save previous value, yield, and then restore the previous value stored in
    the environment variable 'env_name'.

    If 'value' is None, do nothing"""
    value_changed = value is not None
    if value_changed:
        old_value = os.environ.get(env_name)
        os.environ[env_name] = value
    try:
        yield
    finally:
        if value_changed:
            if old_value is None:
                del os.environ[env_name]
            else:
                os.environ[env_name] = old_value


def should_bypass_proxies(url, no_proxy):
    """
    Returns whether we should bypass proxies or not.

    :rtype: bool
    """

    # Prioritize lowercase environment variables over uppercase
    # to keep a consistent behaviour with other http projects (curl, wget).
    def get_proxy(key):
        return os.environ.get(key) or os.environ.get(key.upper())

    # First check whether no_proxy is defined. If it is, check that the URL
    # we're getting isn't in the no_proxy list.
    no_proxy_arg = no_proxy
    if no_proxy is None:
        no_proxy = get_proxy("no_proxy")
    parsed = urlparse(url)

    if parsed.hostname is None:
        # URLs don't always have hostnames, e.g. file:/// urls.
        return True

    if no_proxy:
        # We need to check whether we match here. We need to see if we match
        # the end of the hostname, both with and without the port.
        no_proxy = (host for host in no_proxy.replace(" ", "").split(",") if host)

        if is_ipv4_address(parsed.hostname):
            for proxy_ip in no_proxy:
                if is_valid_cidr(proxy_ip):
                    if address_in_network(parsed.hostname, proxy_ip):
                        return True
                elif parsed.hostname == proxy_ip:
                    # If no_proxy ip was defined in plain IP notation instead of cidr notation &
                    # matches the IP of the index
                    return True
        else:
            host_with_port = parsed.hostname
            if parsed.port:
                host_with_port += f":{parsed.port}"

            for host in no_proxy:
                if parsed.hostname.endswith(host) or host_with_port.endswith(host):
                    # The URL does match something in no_proxy, so we don't want
                    # to apply the proxies on this URL.
                    return True

    with set_environ("no_proxy", no_proxy_arg):
        # parsed.hostname can be `None` in cases such as a file URI.
        try:
            bypass = proxy_bypass(parsed.hostname)
        except (TypeError, socket.gaierror):
            bypass = False

    if bypass:
        return True

    return False


def get_environ_proxies(url, no_proxy=None):
    """
    Return a dict of environment proxies.

    :rtype: dict
    """
    if should_bypass_proxies(url, no_proxy=no_proxy):
        return {}
    else:
        return getproxies()


def select_proxy(url, proxies):
    """Select a proxy for the url, if applicable.

    :param url: The url being for the request
    :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs
    """
    proxies = proxies or {}
    urlparts = urlparse(url)
    if urlparts.hostname is None:
        return proxies.get(urlparts.scheme, proxies.get("all"))

    proxy_keys = [
        urlparts.scheme + "://" + urlparts.hostname,
        urlparts.scheme,
        "all://" + urlparts.hostname,
        "all",
    ]
    proxy = None
    for proxy_key in proxy_keys:
        if proxy_key in proxies:
            proxy = proxies[proxy_key]
            break

    return proxy


def resolve_proxies(request, proxies, trust_env=True):
    """This method takes proxy information from a request and configuration
    input to resolve a mapping of target proxies. This will consider settings
    such as NO_PROXY to strip proxy configurations.

    :param request: Request or PreparedRequest
    :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs
    :param trust_env: Boolean declaring whether to trust environment configs

    :rtype: dict
    """
    proxies = proxies if proxies is not None else {}
    url = request.url
    scheme = urlparse(url).scheme
    no_proxy = proxies.get("no_proxy")
    new_proxies = proxies.copy()

    if trust_env and not should_bypass_proxies(url, no_proxy=no_proxy):
        environ_proxies = get_environ_proxies(url, no_proxy=no_proxy)

        proxy = environ_proxies.get(scheme, environ_proxies.get("all"))

        if proxy:
            new_proxies.setdefault(scheme, proxy)
    return new_proxies


def default_user_agent(name="python-requests"):
    """
    Return a string representing the default user agent.

    :rtype: str
    """
    return f"{name}/{__version__}"


def default_headers():
    """
    :rtype: requests.structures.CaseInsensitiveDict
    """
    return CaseInsensitiveDict(
        {
            "User-Agent": default_user_agent(),
            "Accept-Encoding": DEFAULT_ACCEPT_ENCODING,
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
    )


def parse_header_links(value):
    """Return a list of parsed link headers proxies.

    i.e. Link: <http:/.../front.jpeg>; rel=front; type="image/jpeg",<http://.../back.jpeg>; rel=back;type="image/jpeg"

    :rtype: list
    """

    links = []

    replace_chars = " '\""

    value = value.strip(replace_chars)
    if not value:
        return links

    for val in re.split(", *<", value):
        try:
            url, params = val.split(";", 1)
        except ValueError:
            url, params = val, ""

        link = {"url": url.strip("<> '\"")}

        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break

            link[key.strip(replace_chars)] = value.strip(replace_chars)

        links.append(link)

    return links


# Null bytes; no need to recreate these on each call to guess_json_utf
_null = "\x00".encode("ascii")  # encoding to ASCII for Python 3
_null2 = _null * 2
_null3 = _null * 3


def guess_json_utf(data):
    """
    :rtype: str
    """
    # JSON always starts with two ASCII characters, so detection is as
    # easy as counting the nulls and from their location and count
    # determine the encoding. Also detect a BOM, if present.
    sample = data[:4]
    if sample in (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE):
        return "utf-32"  # BOM included
    if sample[:3] == codecs.BOM_UTF8:
        return "utf-8-sig"  # BOM included, MS style (discouraged)
    if sample[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
        return "utf-16"  # BOM included
    nullcount = sample.count(_null)
    if nullcount == 0:
        return "utf-8"
    if nullcount == 2:
        if sample[::2] == _null2:  # 1st and 3rd are null
            return "utf-16-be"
        if sample[1::2] == _null2:  # 2nd and 4th are null
            return "utf-16-le"
        # Did not detect 2 valid UTF-16 ascii-range characters
    if nullcount == 3:
        if sample[:3] == _null3:
            return "utf-32-be"
        if sample[1:] == _null3:
            return "utf-32-le"
        # Did not detect a valid UTF-32 ascii-range character
    return None


def prepend_scheme_if_needed(url, new_scheme):
    """Given a URL that may or may not have a scheme, prepend the given scheme.
    Does not replace a present scheme with the one provided as an argument.

    :rtype: str
    """
    parsed = parse_url(url)
    scheme, auth, host, port, path, query, fragment = parsed

    # A defect in urlparse determines that there isn't a netloc present in some
    # urls. We previously assumed parsing was overly cautious, and swapped the
    # netloc and path. Due to a lack of tests on the original defect, this is
    # maintained with parse_url for backwards compatibility.
    netloc = parsed.netloc
    if not netloc:
        netloc, path = path, netloc

    if auth:
        # parse_url doesn't provide the netloc with auth
        # so we'll add it ourselves.
        netloc = "@".join([auth, netloc])
    if scheme is None:
        scheme = new_scheme
    if path is None:
        path = ""

    return urlunparse((scheme, netloc, path, "", query, fragment))


def get_auth_from_url(url):
    """Given a url with authentication components, extract them into a tuple of
    username,password.

    :rtype: (str,str)
    """
    parsed = urlparse(url)

    try:
        auth = (unquote(parsed.username), unquote(parsed.password))
    except (AttributeError, TypeError):
        auth = ("", "")

    return auth


def check_header_validity(header):
    """Verifies that header parts don't contain leading whitespace
    reserved characters, or return characters.

    :param header: tuple, in the format (name, value).
    """
    name, value = header
    _validate_header_part(header, name, 0)
    _validate_header_part(header, value, 1)


def _validate_header_part(header, header_part, header_validator_index):
    if isinstance(header_part, str):
        validator = _HEADER_VALIDATORS_STR[header_validator_index]
    elif isinstance(header_part, bytes):
        validator = _HEADER_VALIDATORS_BYTE[header_validator_index]
    else:
        raise InvalidHeader(
            f"Header part ({header_part!r}) from {header} "
            f"must be of type str or bytes, not {type(header_part)}"
        )

    if not validator.match(header_part):
        header_kind = "name" if header_validator_index == 0 else "value"
        raise InvalidHeader(
            f"Invalid leading whitespace, reserved character(s), or return "
            f"character(s) in header {header_kind}: {header_part!r}"
        )


def urldefragauth(url):
    """
    Given a url remove the fragment and the authentication part.

    :rtype: str
    """
    scheme, netloc, path, params, query, fragment = urlparse(url)

    # see func:`prepend_scheme_if_needed`
    if not netloc:
        netloc, path = path, netloc

    netloc = netloc.rsplit("@", 1)[-1]

    return urlunparse((scheme, netloc, path, params, query, ""))


def rewind_body(prepared_request):
    """Move file pointer back to its recorded starting position
    so it can be read again on redirect.
    """
    body_seek = getattr(prepared_request.body, "seek", None)
    if body_seek is not None and isinstance(
        prepared_request._body_position, integer_types
    ):
        try:
            body_seek(prepared_request._body_position)
        except OSError:
            raise UnrewindableBodyError(
                "An error occurred when rewinding request body for redirect."
            )
    else:
        raise UnrewindableBodyError("Unable to rewind request body for redirect.")

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\requests\utils.py ===
"""
requests.utils
~~~~~~~~~~~~~~

This module provides utility functions that are used within Requests
that are also useful for external consumption.
"""

import codecs
import contextlib
import io
import os
import re
import socket
import struct
import sys
import tempfile
import warnings
import zipfile
from collections import OrderedDict

from pip._vendor.urllib3.util import make_headers, parse_url

from . import certs
from .__version__ import __version__

# to_native_string is unused here, but imported here for backwards compatibility
from ._internal_utils import (  # noqa: F401
    _HEADER_VALIDATORS_BYTE,
    _HEADER_VALIDATORS_STR,
    HEADER_VALIDATORS,
    to_native_string,
)
from .compat import (
    Mapping,
    basestring,
    bytes,
    getproxies,
    getproxies_environment,
    integer_types,
)
from .compat import parse_http_list as _parse_list_header
from .compat import (
    proxy_bypass,
    proxy_bypass_environment,
    quote,
    str,
    unquote,
    urlparse,
    urlunparse,
)
from .cookies import cookiejar_from_dict
from .exceptions import (
    FileModeWarning,
    InvalidHeader,
    InvalidURL,
    UnrewindableBodyError,
)
from .structures import CaseInsensitiveDict

NETRC_FILES = (".netrc", "_netrc")

DEFAULT_CA_BUNDLE_PATH = certs.where()

DEFAULT_PORTS = {"http": 80, "https": 443}

# Ensure that ', ' is used to preserve previous delimiter behavior.
DEFAULT_ACCEPT_ENCODING = ", ".join(
    re.split(r",\s*", make_headers(accept_encoding=True)["accept-encoding"])
)


if sys.platform == "win32":
    # provide a proxy_bypass version on Windows without DNS lookups

    def proxy_bypass_registry(host):
        try:
            import winreg
        except ImportError:
            return False

        try:
            internetSettings = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            )
            # ProxyEnable could be REG_SZ or REG_DWORD, normalizing it
            proxyEnable = int(winreg.QueryValueEx(internetSettings, "ProxyEnable")[0])
            # ProxyOverride is almost always a string
            proxyOverride = winreg.QueryValueEx(internetSettings, "ProxyOverride")[0]
        except (OSError, ValueError):
            return False
        if not proxyEnable or not proxyOverride:
            return False

        # make a check value list from the registry entry: replace the
        # '<local>' string by the localhost entry and the corresponding
        # canonical entry.
        proxyOverride = proxyOverride.split(";")
        # filter out empty strings to avoid re.match return true in the following code.
        proxyOverride = filter(None, proxyOverride)
        # now check if we match one of the registry values.
        for test in proxyOverride:
            if test == "<local>":
                if "." not in host:
                    return True
            test = test.replace(".", r"\.")  # mask dots
            test = test.replace("*", r".*")  # change glob sequence
            test = test.replace("?", r".")  # change glob char
            if re.match(test, host, re.I):
                return True
        return False

    def proxy_bypass(host):  # noqa
        """Return True, if the host should be bypassed.

        Checks proxy settings gathered from the environment, if specified,
        or the registry.
        """
        if getproxies_environment():
            return proxy_bypass_environment(host)
        else:
            return proxy_bypass_registry(host)


def dict_to_sequence(d):
    """Returns an internal sequence dictionary update."""

    if hasattr(d, "items"):
        d = d.items()

    return d


def super_len(o):
    total_length = None
    current_position = 0

    if isinstance(o, str):
        o = o.encode("utf-8")

    if hasattr(o, "__len__"):
        total_length = len(o)

    elif hasattr(o, "len"):
        total_length = o.len

    elif hasattr(o, "fileno"):
        try:
            fileno = o.fileno()
        except (io.UnsupportedOperation, AttributeError):
            # AttributeError is a surprising exception, seeing as how we've just checked
            # that `hasattr(o, 'fileno')`.  It happens for objects obtained via
            # `Tarfile.extractfile()`, per issue 5229.
            pass
        else:
            total_length = os.fstat(fileno).st_size

            # Having used fstat to determine the file length, we need to
            # confirm that this file was opened up in binary mode.
            if "b" not in o.mode:
                warnings.warn(
                    (
                        "Requests has determined the content-length for this "
                        "request using the binary size of the file: however, the "
                        "file has been opened in text mode (i.e. without the 'b' "
                        "flag in the mode). This may lead to an incorrect "
                        "content-length. In Requests 3.0, support will be removed "
                        "for files in text mode."
                    ),
                    FileModeWarning,
                )

    if hasattr(o, "tell"):
        try:
            current_position = o.tell()
        except OSError:
            # This can happen in some weird situations, such as when the file
            # is actually a special file descriptor like stdin. In this
            # instance, we don't know what the length is, so set it to zero and
            # let requests chunk it instead.
            if total_length is not None:
                current_position = total_length
        else:
            if hasattr(o, "seek") and total_length is None:
                # StringIO and BytesIO have seek but no usable fileno
                try:
                    # seek to end of file
                    o.seek(0, 2)
                    total_length = o.tell()

                    # seek back to current position to support
                    # partially read file-like objects
                    o.seek(current_position or 0)
                except OSError:
                    total_length = 0

    if total_length is None:
        total_length = 0

    return max(0, total_length - current_position)


def get_netrc_auth(url, raise_errors=False):
    """Returns the Requests tuple auth for a given url from netrc."""

    netrc_file = os.environ.get("NETRC")
    if netrc_file is not None:
        netrc_locations = (netrc_file,)
    else:
        netrc_locations = (f"~/{f}" for f in NETRC_FILES)

    try:
        from netrc import NetrcParseError, netrc

        netrc_path = None

        for f in netrc_locations:
            try:
                loc = os.path.expanduser(f)
            except KeyError:
                # os.path.expanduser can fail when $HOME is undefined and
                # getpwuid fails. See https://bugs.python.org/issue20164 &
                # https://github.com/psf/requests/issues/1846
                return

            if os.path.exists(loc):
                netrc_path = loc
                break

        # Abort early if there isn't one.
        if netrc_path is None:
            return

        ri = urlparse(url)

        # Strip port numbers from netloc. This weird `if...encode`` dance is
        # used for Python 3.2, which doesn't support unicode literals.
        splitstr = b":"
        if isinstance(url, str):
            splitstr = splitstr.decode("ascii")
        host = ri.netloc.split(splitstr)[0]

        try:
            _netrc = netrc(netrc_path).authenticators(host)
            if _netrc:
                # Return with login / password
                login_i = 0 if _netrc[0] else 1
                return (_netrc[login_i], _netrc[2])
        except (NetrcParseError, OSError):
            # If there was a parsing error or a permissions issue reading the file,
            # we'll just skip netrc auth unless explicitly asked to raise errors.
            if raise_errors:
                raise

    # App Engine hackiness.
    except (ImportError, AttributeError):
        pass


def guess_filename(obj):
    """Tries to guess the filename of the given object."""
    name = getattr(obj, "name", None)
    if name and isinstance(name, basestring) and name[0] != "<" and name[-1] != ">":
        return os.path.basename(name)


def extract_zipped_paths(path):
    """Replace nonexistent paths that look like they refer to a member of a zip
    archive with the location of an extracted copy of the target, or else
    just return the provided path unchanged.
    """
    if os.path.exists(path):
        # this is already a valid path, no need to do anything further
        return path

    # find the first valid part of the provided path and treat that as a zip archive
    # assume the rest of the path is the name of a member in the archive
    archive, member = os.path.split(path)
    while archive and not os.path.exists(archive):
        archive, prefix = os.path.split(archive)
        if not prefix:
            # If we don't check for an empty prefix after the split (in other words, archive remains unchanged after the split),
            # we _can_ end up in an infinite loop on a rare corner case affecting a small number of users
            break
        member = "/".join([prefix, member])

    if not zipfile.is_zipfile(archive):
        return path

    zip_file = zipfile.ZipFile(archive)
    if member not in zip_file.namelist():
        return path

    # we have a valid zip archive and a valid member of that archive
    tmp = tempfile.gettempdir()
    extracted_path = os.path.join(tmp, member.split("/")[-1])
    if not os.path.exists(extracted_path):
        # use read + write to avoid the creating nested folders, we only want the file, avoids mkdir racing condition
        with atomic_open(extracted_path) as file_handler:
            file_handler.write(zip_file.read(member))
    return extracted_path


@contextlib.contextmanager
def atomic_open(filename):
    """Write a file to the disk in an atomic fashion"""
    tmp_descriptor, tmp_name = tempfile.mkstemp(dir=os.path.dirname(filename))
    try:
        with os.fdopen(tmp_descriptor, "wb") as tmp_handler:
            yield tmp_handler
        os.replace(tmp_name, filename)
    except BaseException:
        os.remove(tmp_name)
        raise


def from_key_val_list(value):
    """Take an object and test to see if it can be represented as a
    dictionary. Unless it can not be represented as such, return an
    OrderedDict, e.g.,

    ::

        >>> from_key_val_list([('key', 'val')])
        OrderedDict([('key', 'val')])
        >>> from_key_val_list('string')
        Traceback (most recent call last):
        ...
        ValueError: cannot encode objects that are not 2-tuples
        >>> from_key_val_list({'key': 'val'})
        OrderedDict([('key', 'val')])

    :rtype: OrderedDict
    """
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    return OrderedDict(value)


def to_key_val_list(value):
    """Take an object and test to see if it can be represented as a
    dictionary. If it can be, return a list of tuples, e.g.,

    ::

        >>> to_key_val_list([('key', 'val')])
        [('key', 'val')]
        >>> to_key_val_list({'key': 'val'})
        [('key', 'val')]
        >>> to_key_val_list('string')
        Traceback (most recent call last):
        ...
        ValueError: cannot encode objects that are not 2-tuples

    :rtype: list
    """
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    if isinstance(value, Mapping):
        value = value.items()

    return list(value)


# From mitsuhiko/werkzeug (used with permission).
def parse_list_header(value):
    """Parse lists as described by RFC 2068 Section 2.

    In particular, parse comma-separated lists where the elements of
    the list may include quoted-strings.  A quoted-string could
    contain a comma.  A non-quoted string could have quotes in the
    middle.  Quotes are removed automatically after parsing.

    It basically works like :func:`parse_set_header` just that items
    may appear multiple times and case sensitivity is preserved.

    The return value is a standard :class:`list`:

    >>> parse_list_header('token, "quoted value"')
    ['token', 'quoted value']

    To create a header from the :class:`list` again, use the
    :func:`dump_header` function.

    :param value: a string with a list header.
    :return: :class:`list`
    :rtype: list
    """
    result = []
    for item in _parse_list_header(value):
        if item[:1] == item[-1:] == '"':
            item = unquote_header_value(item[1:-1])
        result.append(item)
    return result


# From mitsuhiko/werkzeug (used with permission).
def parse_dict_header(value):
    """Parse lists of key, value pairs as described by RFC 2068 Section 2 and
    convert them into a python dict:

    >>> d = parse_dict_header('foo="is a fish", bar="as well"')
    >>> type(d) is dict
    True
    >>> sorted(d.items())
    [('bar', 'as well'), ('foo', 'is a fish')]

    If there is no value for a key it will be `None`:

    >>> parse_dict_header('key_without_value')
    {'key_without_value': None}

    To create a header from the :class:`dict` again, use the
    :func:`dump_header` function.

    :param value: a string with a dict header.
    :return: :class:`dict`
    :rtype: dict
    """
    result = {}
    for item in _parse_list_header(value):
        if "=" not in item:
            result[item] = None
            continue
        name, value = item.split("=", 1)
        if value[:1] == value[-1:] == '"':
            value = unquote_header_value(value[1:-1])
        result[name] = value
    return result


# From mitsuhiko/werkzeug (used with permission).
def unquote_header_value(value, is_filename=False):
    r"""Unquotes a header value.  (Reversal of :func:`quote_header_value`).
    This does not use the real unquoting but what browsers are actually
    using for quoting.

    :param value: the header value to unquote.
    :rtype: str
    """
    if value and value[0] == value[-1] == '"':
        # this is not the real unquoting, but fixing this so that the
        # RFC is met will result in bugs with internet explorer and
        # probably some other browsers as well.  IE for example is
        # uploading files with "C:\foo\bar.txt" as filename
        value = value[1:-1]

        # if this is a filename and the starting characters look like
        # a UNC path, then just return the value without quotes.  Using the
        # replace sequence below on a UNC path has the effect of turning
        # the leading double slash into a single slash and then
        # _fix_ie_filename() doesn't work correctly.  See #458.
        if not is_filename or value[:2] != "\\\\":
            return value.replace("\\\\", "\\").replace('\\"', '"')
    return value


def dict_from_cookiejar(cj):
    """Returns a key/value dictionary from a CookieJar.

    :param cj: CookieJar object to extract cookies from.
    :rtype: dict
    """

    cookie_dict = {cookie.name: cookie.value for cookie in cj}
    return cookie_dict


def add_dict_to_cookiejar(cj, cookie_dict):
    """Returns a CookieJar from a key/value dictionary.

    :param cj: CookieJar to insert cookies into.
    :param cookie_dict: Dict of key/values to insert into CookieJar.
    :rtype: CookieJar
    """

    return cookiejar_from_dict(cookie_dict, cj)


def get_encodings_from_content(content):
    """Returns encodings from given content string.

    :param content: bytestring to extract encodings from.
    """
    warnings.warn(
        (
            "In requests 3.0, get_encodings_from_content will be removed. For "
            "more information, please see the discussion on issue #2266. (This"
            " warning should only appear once.)"
        ),
        DeprecationWarning,
    )

    charset_re = re.compile(r'<meta.*?charset=["\']*(.+?)["\'>]', flags=re.I)
    pragma_re = re.compile(r'<meta.*?content=["\']*;?charset=(.+?)["\'>]', flags=re.I)
    xml_re = re.compile(r'^<\?xml.*?encoding=["\']*(.+?)["\'>]')

    return (
        charset_re.findall(content)
        + pragma_re.findall(content)
        + xml_re.findall(content)
    )


def _parse_content_type_header(header):
    """Returns content type and parameters from given header

    :param header: string
    :return: tuple containing content type and dictionary of
         parameters
    """

    tokens = header.split(";")
    content_type, params = tokens[0].strip(), tokens[1:]
    params_dict = {}
    items_to_strip = "\"' "

    for param in params:
        param = param.strip()
        if param:
            key, value = param, True
            index_of_equals = param.find("=")
            if index_of_equals != -1:
                key = param[:index_of_equals].strip(items_to_strip)
                value = param[index_of_equals + 1 :].strip(items_to_strip)
            params_dict[key.lower()] = value
    return content_type, params_dict


def get_encoding_from_headers(headers):
    """Returns encodings from given HTTP Header Dict.

    :param headers: dictionary to extract encoding from.
    :rtype: str
    """

    content_type = headers.get("content-type")

    if not content_type:
        return None

    content_type, params = _parse_content_type_header(content_type)

    if "charset" in params:
        return params["charset"].strip("'\"")

    if "text" in content_type:
        return "ISO-8859-1"

    if "application/json" in content_type:
        # Assume UTF-8 based on RFC 4627: https://www.ietf.org/rfc/rfc4627.txt since the charset was unset
        return "utf-8"


def stream_decode_response_unicode(iterator, r):
    """Stream decodes an iterator."""

    if r.encoding is None:
        yield from iterator
        return

    decoder = codecs.getincrementaldecoder(r.encoding)(errors="replace")
    for chunk in iterator:
        rv = decoder.decode(chunk)
        if rv:
            yield rv
    rv = decoder.decode(b"", final=True)
    if rv:
        yield rv


def iter_slices(string, slice_length):
    """Iterate over slices of a string."""
    pos = 0
    if slice_length is None or slice_length <= 0:
        slice_length = len(string)
    while pos < len(string):
        yield string[pos : pos + slice_length]
        pos += slice_length


def get_unicode_from_response(r):
    """Returns the requested content back in unicode.

    :param r: Response object to get unicode content from.

    Tried:

    1. charset from content-type
    2. fall back and replace all unicode characters

    :rtype: str
    """
    warnings.warn(
        (
            "In requests 3.0, get_unicode_from_response will be removed. For "
            "more information, please see the discussion on issue #2266. (This"
            " warning should only appear once.)"
        ),
        DeprecationWarning,
    )

    tried_encodings = []

    # Try charset from content-type
    encoding = get_encoding_from_headers(r.headers)

    if encoding:
        try:
            return str(r.content, encoding)
        except UnicodeError:
            tried_encodings.append(encoding)

    # Fall back:
    try:
        return str(r.content, encoding, errors="replace")
    except TypeError:
        return r.content


# The unreserved URI characters (RFC 3986)
UNRESERVED_SET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" + "0123456789-._~"
)


def unquote_unreserved(uri):
    """Un-escape any percent-escape sequences in a URI that are unreserved
    characters. This leaves all reserved, illegal and non-ASCII bytes encoded.

    :rtype: str
    """
    parts = uri.split("%")
    for i in range(1, len(parts)):
        h = parts[i][0:2]
        if len(h) == 2 and h.isalnum():
            try:
                c = chr(int(h, 16))
            except ValueError:
                raise InvalidURL(f"Invalid percent-escape sequence: '{h}'")

            if c in UNRESERVED_SET:
                parts[i] = c + parts[i][2:]
            else:
                parts[i] = f"%{parts[i]}"
        else:
            parts[i] = f"%{parts[i]}"
    return "".join(parts)


def requote_uri(uri):
    """Re-quote the given URI.

    This function passes the given URI through an unquote/quote cycle to
    ensure that it is fully and consistently quoted.

    :rtype: str
    """
    safe_with_percent = "!#$%&'()*+,/:;=?@[]~"
    safe_without_percent = "!#$&'()*+,/:;=?@[]~"
    try:
        # Unquote only the unreserved characters
        # Then quote only illegal characters (do not quote reserved,
        # unreserved, or '%')
        return quote(unquote_unreserved(uri), safe=safe_with_percent)
    except InvalidURL:
        # We couldn't unquote the given URI, so let's try quoting it, but
        # there may be unquoted '%'s in the URI. We need to make sure they're
        # properly quoted so they do not cause issues elsewhere.
        return quote(uri, safe=safe_without_percent)


def address_in_network(ip, net):
    """This function allows you to check if an IP belongs to a network subnet

    Example: returns True if ip = 192.168.1.1 and net = 192.168.1.0/24
             returns False if ip = 192.168.1.1 and net = 192.168.100.0/24

    :rtype: bool
    """
    ipaddr = struct.unpack("=L", socket.inet_aton(ip))[0]
    netaddr, bits = net.split("/")
    netmask = struct.unpack("=L", socket.inet_aton(dotted_netmask(int(bits))))[0]
    network = struct.unpack("=L", socket.inet_aton(netaddr))[0] & netmask
    return (ipaddr & netmask) == (network & netmask)


def dotted_netmask(mask):
    """Converts mask from /xx format to xxx.xxx.xxx.xxx

    Example: if mask is 24 function returns 255.255.255.0

    :rtype: str
    """
    bits = 0xFFFFFFFF ^ (1 << 32 - mask) - 1
    return socket.inet_ntoa(struct.pack(">I", bits))


def is_ipv4_address(string_ip):
    """
    :rtype: bool
    """
    try:
        socket.inet_aton(string_ip)
    except OSError:
        return False
    return True


def is_valid_cidr(string_network):
    """
    Very simple check of the cidr format in no_proxy variable.

    :rtype: bool
    """
    if string_network.count("/") == 1:
        try:
            mask = int(string_network.split("/")[1])
        except ValueError:
            return False

        if mask < 1 or mask > 32:
            return False

        try:
            socket.inet_aton(string_network.split("/")[0])
        except OSError:
            return False
    else:
        return False
    return True


@contextlib.contextmanager
def set_environ(env_name, value):
    """Set the environment variable 'env_name' to 'value'

    Save previous value, yield, and then restore the previous value stored in
    the environment variable 'env_name'.

    If 'value' is None, do nothing"""
    value_changed = value is not None
    if value_changed:
        old_value = os.environ.get(env_name)
        os.environ[env_name] = value
    try:
        yield
    finally:
        if value_changed:
            if old_value is None:
                del os.environ[env_name]
            else:
                os.environ[env_name] = old_value


def should_bypass_proxies(url, no_proxy):
    """
    Returns whether we should bypass proxies or not.

    :rtype: bool
    """

    # Prioritize lowercase environment variables over uppercase
    # to keep a consistent behaviour with other http projects (curl, wget).
    def get_proxy(key):
        return os.environ.get(key) or os.environ.get(key.upper())

    # First check whether no_proxy is defined. If it is, check that the URL
    # we're getting isn't in the no_proxy list.
    no_proxy_arg = no_proxy
    if no_proxy is None:
        no_proxy = get_proxy("no_proxy")
    parsed = urlparse(url)

    if parsed.hostname is None:
        # URLs don't always have hostnames, e.g. file:/// urls.
        return True

    if no_proxy:
        # We need to check whether we match here. We need to see if we match
        # the end of the hostname, both with and without the port.
        no_proxy = (host for host in no_proxy.replace(" ", "").split(",") if host)

        if is_ipv4_address(parsed.hostname):
            for proxy_ip in no_proxy:
                if is_valid_cidr(proxy_ip):
                    if address_in_network(parsed.hostname, proxy_ip):
                        return True
                elif parsed.hostname == proxy_ip:
                    # If no_proxy ip was defined in plain IP notation instead of cidr notation &
                    # matches the IP of the index
                    return True
        else:
            host_with_port = parsed.hostname
            if parsed.port:
                host_with_port += f":{parsed.port}"

            for host in no_proxy:
                if parsed.hostname.endswith(host) or host_with_port.endswith(host):
                    # The URL does match something in no_proxy, so we don't want
                    # to apply the proxies on this URL.
                    return True

    with set_environ("no_proxy", no_proxy_arg):
        # parsed.hostname can be `None` in cases such as a file URI.
        try:
            bypass = proxy_bypass(parsed.hostname)
        except (TypeError, socket.gaierror):
            bypass = False

    if bypass:
        return True

    return False


def get_environ_proxies(url, no_proxy=None):
    """
    Return a dict of environment proxies.

    :rtype: dict
    """
    if should_bypass_proxies(url, no_proxy=no_proxy):
        return {}
    else:
        return getproxies()


def select_proxy(url, proxies):
    """Select a proxy for the url, if applicable.

    :param url: The url being for the request
    :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs
    """
    proxies = proxies or {}
    urlparts = urlparse(url)
    if urlparts.hostname is None:
        return proxies.get(urlparts.scheme, proxies.get("all"))

    proxy_keys = [
        urlparts.scheme + "://" + urlparts.hostname,
        urlparts.scheme,
        "all://" + urlparts.hostname,
        "all",
    ]
    proxy = None
    for proxy_key in proxy_keys:
        if proxy_key in proxies:
            proxy = proxies[proxy_key]
            break

    return proxy


def resolve_proxies(request, proxies, trust_env=True):
    """This method takes proxy information from a request and configuration
    input to resolve a mapping of target proxies. This will consider settings
    such as NO_PROXY to strip proxy configurations.

    :param request: Request or PreparedRequest
    :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs
    :param trust_env: Boolean declaring whether to trust environment configs

    :rtype: dict
    """
    proxies = proxies if proxies is not None else {}
    url = request.url
    scheme = urlparse(url).scheme
    no_proxy = proxies.get("no_proxy")
    new_proxies = proxies.copy()

    if trust_env and not should_bypass_proxies(url, no_proxy=no_proxy):
        environ_proxies = get_environ_proxies(url, no_proxy=no_proxy)

        proxy = environ_proxies.get(scheme, environ_proxies.get("all"))

        if proxy:
            new_proxies.setdefault(scheme, proxy)
    return new_proxies


def default_user_agent(name="python-requests"):
    """
    Return a string representing the default user agent.

    :rtype: str
    """
    return f"{name}/{__version__}"


def default_headers():
    """
    :rtype: requests.structures.CaseInsensitiveDict
    """
    return CaseInsensitiveDict(
        {
            "User-Agent": default_user_agent(),
            "Accept-Encoding": DEFAULT_ACCEPT_ENCODING,
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
    )


def parse_header_links(value):
    """Return a list of parsed link headers proxies.

    i.e. Link: <http:/.../front.jpeg>; rel=front; type="image/jpeg",<http://.../back.jpeg>; rel=back;type="image/jpeg"

    :rtype: list
    """

    links = []

    replace_chars = " '\""

    value = value.strip(replace_chars)
    if not value:
        return links

    for val in re.split(", *<", value):
        try:
            url, params = val.split(";", 1)
        except ValueError:
            url, params = val, ""

        link = {"url": url.strip("<> '\"")}

        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break

            link[key.strip(replace_chars)] = value.strip(replace_chars)

        links.append(link)

    return links


# Null bytes; no need to recreate these on each call to guess_json_utf
_null = "\x00".encode("ascii")  # encoding to ASCII for Python 3
_null2 = _null * 2
_null3 = _null * 3


def guess_json_utf(data):
    """
    :rtype: str
    """
    # JSON always starts with two ASCII characters, so detection is as
    # easy as counting the nulls and from their location and count
    # determine the encoding. Also detect a BOM, if present.
    sample = data[:4]
    if sample in (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE):
        return "utf-32"  # BOM included
    if sample[:3] == codecs.BOM_UTF8:
        return "utf-8-sig"  # BOM included, MS style (discouraged)
    if sample[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
        return "utf-16"  # BOM included
    nullcount = sample.count(_null)
    if nullcount == 0:
        return "utf-8"
    if nullcount == 2:
        if sample[::2] == _null2:  # 1st and 3rd are null
            return "utf-16-be"
        if sample[1::2] == _null2:  # 2nd and 4th are null
            return "utf-16-le"
        # Did not detect 2 valid UTF-16 ascii-range characters
    if nullcount == 3:
        if sample[:3] == _null3:
            return "utf-32-be"
        if sample[1:] == _null3:
            return "utf-32-le"
        # Did not detect a valid UTF-32 ascii-range character
    return None


def prepend_scheme_if_needed(url, new_scheme):
    """Given a URL that may or may not have a scheme, prepend the given scheme.
    Does not replace a present scheme with the one provided as an argument.

    :rtype: str
    """
    parsed = parse_url(url)
    scheme, auth, host, port, path, query, fragment = parsed

    # A defect in urlparse determines that there isn't a netloc present in some
    # urls. We previously assumed parsing was overly cautious, and swapped the
    # netloc and path. Due to a lack of tests on the original defect, this is
    # maintained with parse_url for backwards compatibility.
    netloc = parsed.netloc
    if not netloc:
        netloc, path = path, netloc

    if auth:
        # parse_url doesn't provide the netloc with auth
        # so we'll add it ourselves.
        netloc = "@".join([auth, netloc])
    if scheme is None:
        scheme = new_scheme
    if path is None:
        path = ""

    return urlunparse((scheme, netloc, path, "", query, fragment))


def get_auth_from_url(url):
    """Given a url with authentication components, extract them into a tuple of
    username,password.

    :rtype: (str,str)
    """
    parsed = urlparse(url)

    try:
        auth = (unquote(parsed.username), unquote(parsed.password))
    except (AttributeError, TypeError):
        auth = ("", "")

    return auth


def check_header_validity(header):
    """Verifies that header parts don't contain leading whitespace
    reserved characters, or return characters.

    :param header: tuple, in the format (name, value).
    """
    name, value = header
    _validate_header_part(header, name, 0)
    _validate_header_part(header, value, 1)


def _validate_header_part(header, header_part, header_validator_index):
    if isinstance(header_part, str):
        validator = _HEADER_VALIDATORS_STR[header_validator_index]
    elif isinstance(header_part, bytes):
        validator = _HEADER_VALIDATORS_BYTE[header_validator_index]
    else:
        raise InvalidHeader(
            f"Header part ({header_part!r}) from {header} "
            f"must be of type str or bytes, not {type(header_part)}"
        )

    if not validator.match(header_part):
        header_kind = "name" if header_validator_index == 0 else "value"
        raise InvalidHeader(
            f"Invalid leading whitespace, reserved character(s), or return "
            f"character(s) in header {header_kind}: {header_part!r}"
        )


def urldefragauth(url):
    """
    Given a url remove the fragment and the authentication part.

    :rtype: str
    """
    scheme, netloc, path, params, query, fragment = urlparse(url)

    # see func:`prepend_scheme_if_needed`
    if not netloc:
        netloc, path = path, netloc

    netloc = netloc.rsplit("@", 1)[-1]

    return urlunparse((scheme, netloc, path, params, query, ""))


def rewind_body(prepared_request):
    """Move file pointer back to its recorded starting position
    so it can be read again on redirect.
    """
    body_seek = getattr(prepared_request.body, "seek", None)
    if body_seek is not None and isinstance(
        prepared_request._body_position, integer_types
    ):
        try:
            body_seek(prepared_request._body_position)
        except OSError:
            raise UnrewindableBodyError(
                "An error occurred when rewinding request body for redirect."
            )
    else:
        raise UnrewindableBodyError("Unable to rewind request body for redirect.")

# === NexusCore/openenv\Lib\site-packages\win32\test\test_win32file.py ===
import datetime
import os
import random
import shutil
import socket
import tempfile
import threading
import time
import unittest

import ntsecuritycon
import pywintypes
import win32api
import win32con
import win32event
import win32file
import win32pipe
import win32timezone
import winerror
from pywin32_testutil import TestSkipped, testmain


class TestReadBuffer(unittest.TestCase):
    def testLen(self):
        buffer = win32file.AllocateReadBuffer(1)
        self.assertEqual(len(buffer), 1)

    def testSimpleIndex(self):
        buffer = win32file.AllocateReadBuffer(1)
        buffer[0] = 0xFF
        self.assertEqual(buffer[0], 0xFF)

    def testSimpleSlice(self):
        buffer = win32file.AllocateReadBuffer(2)
        val = b"\0\0"
        buffer[:2] = val
        self.assertEqual(buffer[0:2], val)


class TestSimpleOps(unittest.TestCase):
    def testSimpleFiles(self):
        fd, filename = tempfile.mkstemp()
        os.close(fd)
        os.unlink(filename)
        handle = win32file.CreateFile(
            filename, win32file.GENERIC_WRITE, 0, None, win32con.CREATE_NEW, 0, None
        )
        test_data = b"Hello\0there"
        try:
            win32file.WriteFile(handle, test_data)
            handle.Close()
            # Try and open for read
            handle = win32file.CreateFile(
                filename,
                win32file.GENERIC_READ,
                0,
                None,
                win32con.OPEN_EXISTING,
                0,
                None,
            )
            rc, data = win32file.ReadFile(handle, 1024)
            self.assertEqual(data, test_data)
        finally:
            handle.Close()
            try:
                os.unlink(filename)
            except OSError:
                pass

    # A simple test using normal read/write operations.
    def testMoreFiles(self):
        # Create a file in the %TEMP% directory.
        testName = os.path.join(win32api.GetTempPath(), "win32filetest.dat")
        desiredAccess = win32file.GENERIC_READ | win32file.GENERIC_WRITE
        # Set a flag to delete the file automatically when it is closed.
        fileFlags = win32file.FILE_FLAG_DELETE_ON_CLOSE
        h = win32file.CreateFile(
            testName,
            desiredAccess,
            win32file.FILE_SHARE_READ,
            None,
            win32file.CREATE_ALWAYS,
            fileFlags,
            0,
        )

        # Write a known number of bytes to the file.
        data = b"z" * 1025

        win32file.WriteFile(h, data)

        self.assertTrue(
            win32file.GetFileSize(h) == len(data),
            "WARNING: Written file does not have the same size as the length of the data in it!",
        )

        # Ensure we can read the data back.
        win32file.SetFilePointer(h, 0, win32file.FILE_BEGIN)
        hr, read_data = win32file.ReadFile(
            h, len(data) + 10
        )  # + 10 to get anything extra
        self.assertTrue(hr == 0, "Readfile returned %d" % hr)

        self.assertTrue(read_data == data, "Read data is not what we wrote!")

        # Now truncate the file at 1/2 its existing size.
        newSize = len(data) // 2
        win32file.SetFilePointer(h, newSize, win32file.FILE_BEGIN)
        win32file.SetEndOfFile(h)
        self.assertEqual(win32file.GetFileSize(h), newSize)

        # GetFileAttributesEx/GetFileAttributesExW tests.
        self.assertEqual(
            win32file.GetFileAttributesEx(testName),
            win32file.GetFileAttributesExW(testName),
        )

        attr, ct, at, wt, size = win32file.GetFileAttributesEx(testName)
        self.assertTrue(
            size == newSize,
            "Expected GetFileAttributesEx to return the same size as GetFileSize()",
        )
        self.assertTrue(
            attr == win32file.GetFileAttributes(testName),
            "Expected GetFileAttributesEx to return the same attributes as GetFileAttributes",
        )

        h = None  # Close the file by removing the last reference to the handle!

        self.assertTrue(
            not os.path.isfile(testName), "After closing the file, it still exists!"
        )

    def testFilePointer(self):
        # via [ 979270 ] SetFilePointer fails with negative offset

        # Create a file in the %TEMP% directory.
        filename = os.path.join(win32api.GetTempPath(), "win32filetest.dat")

        f = win32file.CreateFile(
            filename,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0,
            None,
            win32file.CREATE_ALWAYS,
            win32file.FILE_ATTRIBUTE_NORMAL,
            0,
        )
        try:
            # Write some data
            data = b"Some data"
            (res, written) = win32file.WriteFile(f, data)

            self.assertFalse(res)
            self.assertEqual(written, len(data))

            # Move at the beginning and read the data
            win32file.SetFilePointer(f, 0, win32file.FILE_BEGIN)
            (res, s) = win32file.ReadFile(f, len(data))

            self.assertFalse(res)
            self.assertEqual(s, data)

            # Move at the end and read the data
            win32file.SetFilePointer(f, -len(data), win32file.FILE_END)
            (res, s) = win32file.ReadFile(f, len(data))

            self.assertFalse(res)
            self.assertEqual(s, data)
        finally:
            f.Close()
            os.unlink(filename)

    def testFileTimesTimezones(self):
        filename = tempfile.mktemp("-testFileTimes")
        # now() is always returning a timestamp with microseconds but the
        # file APIs all have zero microseconds, so some comparisons fail.
        now_utc = win32timezone.utcnow().replace(microsecond=0)
        now_local = now_utc.astimezone(win32timezone.TimeZoneInfo.local())
        h = win32file.CreateFile(
            filename,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0,
            None,
            win32file.CREATE_ALWAYS,
            0,
            0,
        )
        try:
            win32file.SetFileTime(h, now_utc, now_utc, now_utc)
            ct, at, wt = win32file.GetFileTime(h)
            self.assertEqual(now_local, ct)
            self.assertEqual(now_local, at)
            self.assertEqual(now_local, wt)
            # and the reverse - set local, check against utc
            win32file.SetFileTime(h, now_local, now_local, now_local)
            ct, at, wt = win32file.GetFileTime(h)
            self.assertEqual(now_utc, ct)
            self.assertEqual(now_utc, at)
            self.assertEqual(now_utc, wt)
        finally:
            h.close()
            os.unlink(filename)

    def testFileTimes(self):
        from win32timezone import TimeZoneInfo

        # now() is always returning a timestamp with microseconds but the
        # file APIs all have zero microseconds, so some comparisons fail.
        now = datetime.datetime.now(tz=TimeZoneInfo.utc()).replace(microsecond=0)
        nowish = now + datetime.timedelta(seconds=1)
        later = now + datetime.timedelta(seconds=120)

        filename = tempfile.mktemp("-testFileTimes")
        # Windows docs the 'last time' isn't valid until the last write
        # handle is closed - so create the file, then re-open it to check.
        open(filename, "w").close()
        f = win32file.CreateFile(
            filename,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0,
            None,
            win32con.OPEN_EXISTING,
            0,
            None,
        )
        try:
            ct, at, wt = win32file.GetFileTime(f)
            # NOTE (Avasam): I've seen the time be off from -0.003 to +1.11 seconds,
            # so the above comment about microseconds might be wrong.
            # Let's standardize ms and avoid random CI failures
            # https://github.com/mhammond/pywin32/issues/2203
            ct = ct.replace(microsecond=0)
            at = at.replace(microsecond=0)
            wt = wt.replace(microsecond=0)
            self.assertGreaterEqual(
                ct,
                now,
                f"File was created in the past - now={now}, created={ct}",
            )
            self.assertTrue(now <= ct <= nowish, (now, ct, nowish))
            self.assertGreaterEqual(
                wt,
                now,
                f"File was written-to in the past now={now}, written={wt}",
            )
            self.assertTrue(now <= wt <= nowish, (now, wt, nowish))

            # Now set the times.
            win32file.SetFileTime(f, later, later, later, UTCTimes=True)
            # Get them back.
            ct, at, wt = win32file.GetFileTime(f)
            # XXX - the builtin PyTime type appears to be out by a dst offset.
            # just ignore that type here...
            self.assertEqual(ct, later)
            self.assertEqual(at, later)
            self.assertEqual(wt, later)

        finally:
            f.Close()
            os.unlink(filename)


class TestGetFileInfoByHandleEx(unittest.TestCase):
    __handle = __filename = None

    def setUp(self):
        fd, self.__filename = tempfile.mkstemp()
        os.close(fd)

    def tearDown(self):
        if self.__handle is not None:
            self.__handle.Close()
        if self.__filename is not None:
            try:
                os.unlink(self.__filename)
            except OSError:
                pass
        self.__handle = self.__filename = None

    def testFileBasicInfo(self):
        attr = win32file.GetFileAttributes(self.__filename)
        f = win32file.CreateFile(
            self.__filename,
            win32file.GENERIC_READ,
            0,
            None,
            win32con.OPEN_EXISTING,
            0,
            None,
        )
        self.__handle = f
        ct, at, wt = win32file.GetFileTime(f)

        # bug #752: this throws ERROR_BAD_LENGTH (24) in x86 binaries of build 221
        basic_info = win32file.GetFileInformationByHandleEx(f, win32file.FileBasicInfo)

        self.assertEqual(ct, basic_info["CreationTime"])
        self.assertEqual(at, basic_info["LastAccessTime"])
        self.assertEqual(wt, basic_info["LastWriteTime"])
        self.assertEqual(attr, basic_info["FileAttributes"])


class TestOverlapped(unittest.TestCase):
    def testSimpleOverlapped(self):
        # Create a file in the %TEMP% directory.
        import win32event

        testName = os.path.join(win32api.GetTempPath(), "win32filetest.dat")
        desiredAccess = win32file.GENERIC_WRITE
        overlapped = pywintypes.OVERLAPPED()
        evt = win32event.CreateEvent(None, 0, 0, None)
        overlapped.hEvent = evt
        # Create the file and write shit-loads of data to it.
        h = win32file.CreateFile(
            testName, desiredAccess, 0, None, win32file.CREATE_ALWAYS, 0, 0
        )
        chunk_data = b"z" * 0x8000
        num_loops = 512
        expected_size = num_loops * len(chunk_data)
        for i in range(num_loops):
            win32file.WriteFile(h, chunk_data, overlapped)
            win32event.WaitForSingleObject(overlapped.hEvent, win32event.INFINITE)
            overlapped.Offset += len(chunk_data)
        h.Close()
        # Now read the data back overlapped
        overlapped = pywintypes.OVERLAPPED()
        evt = win32event.CreateEvent(None, 0, 0, None)
        overlapped.hEvent = evt
        desiredAccess = win32file.GENERIC_READ
        h = win32file.CreateFile(
            testName, desiredAccess, 0, None, win32file.OPEN_EXISTING, 0, 0
        )
        buffer = win32file.AllocateReadBuffer(0xFFFF)
        while 1:
            try:
                hr, data = win32file.ReadFile(h, buffer, overlapped)
                win32event.WaitForSingleObject(overlapped.hEvent, win32event.INFINITE)
                overlapped.Offset += len(data)
                if not data is buffer:
                    self.fail(
                        "Unexpected result from ReadFile - should be the same buffer we passed it"
                    )
            except win32api.error:
                break
        h.Close()

    def testCompletionPortsMultiple(self):
        # Mainly checking that we can "associate" an existing handle.  This
        # failed in build 203.
        ioport = win32file.CreateIoCompletionPort(
            win32file.INVALID_HANDLE_VALUE, 0, 0, 0
        )
        socks = []
        for PORT in range(9123, 9125):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", PORT))
            sock.listen(1)
            socks.append(sock)
            new = win32file.CreateIoCompletionPort(sock.fileno(), ioport, PORT, 0)
            self.assertIs(new, ioport)
        for s in socks:
            s.close()
        hv = int(ioport)
        ioport = new = None
        # The handle itself should be closed now (unless we leak references!)
        # Check that.
        try:
            win32file.CloseHandle(hv)
            raise AssertionError("Expected close to fail!")
        except win32file.error as details:
            self.assertEqual(details.winerror, winerror.ERROR_INVALID_HANDLE)

    def testCompletionPortsQueued(self):
        class Foo:
            pass

        io_req_port = win32file.CreateIoCompletionPort(-1, None, 0, 0)
        overlapped = pywintypes.OVERLAPPED()
        overlapped.object = Foo()
        win32file.PostQueuedCompletionStatus(io_req_port, 0, 99, overlapped)
        errCode, bytes, key, overlapped = win32file.GetQueuedCompletionStatus(
            io_req_port, win32event.INFINITE
        )
        self.assertEqual(errCode, 0)
        self.assertTrue(isinstance(overlapped.object, Foo))

    def _IOCPServerThread(self, handle, port, drop_overlapped_reference):
        overlapped = pywintypes.OVERLAPPED()
        win32pipe.ConnectNamedPipe(handle, overlapped)
        if drop_overlapped_reference:
            # Be naughty - the overlapped object is now dead, but
            # GetQueuedCompletionStatus will still find it.  Our check of
            # reference counting should catch that error.
            overlapped = None
            # even if we fail, be sure to close the handle; prevents hangs
            # on Vista 64...
            try:
                self.assertRaises(
                    RuntimeError, win32file.GetQueuedCompletionStatus, port, -1
                )
            finally:
                handle.Close()
            return

        result = win32file.GetQueuedCompletionStatus(port, -1)
        ol2 = result[-1]
        self.assertTrue(ol2 is overlapped)
        data = win32file.ReadFile(handle, 512)[1]
        win32file.WriteFile(handle, data)

    def testCompletionPortsNonQueued(self, test_overlapped_death=0):
        # In 204 we had a reference count bug when OVERLAPPED objects were
        # associated with a completion port other than via
        # PostQueuedCompletionStatus.  This test is based on the reproduction
        # reported with that bug.
        # Create the pipe.
        BUFSIZE = 512
        pipe_name = r"\\.\pipe\pywin32_test_pipe"
        handle = win32pipe.CreateNamedPipe(
            pipe_name,
            win32pipe.PIPE_ACCESS_DUPLEX | win32file.FILE_FLAG_OVERLAPPED,
            win32pipe.PIPE_TYPE_MESSAGE
            | win32pipe.PIPE_READMODE_MESSAGE
            | win32pipe.PIPE_WAIT,
            1,
            BUFSIZE,
            BUFSIZE,
            win32pipe.NMPWAIT_WAIT_FOREVER,
            None,
        )
        # Create an IOCP and associate it with the handle.
        port = win32file.CreateIoCompletionPort(-1, 0, 0, 0)
        win32file.CreateIoCompletionPort(handle, port, 1, 0)

        t = threading.Thread(
            target=self._IOCPServerThread, args=(handle, port, test_overlapped_death)
        )
        t.setDaemon(True)  # avoid hanging entire test suite on failure.
        t.start()
        try:
            time.sleep(0.1)  # let thread do its thing.
            try:
                win32pipe.CallNamedPipe(
                    r"\\.\pipe\pywin32_test_pipe", b"Hello there", BUFSIZE, 0
                )
            except win32pipe.error:
                # Testing for overlapped death causes this
                if not test_overlapped_death:
                    raise
        finally:
            if not test_overlapped_death:
                handle.Close()
            t.join(3)
            self.assertFalse(t.is_alive(), "thread didn't finish")

    def testCompletionPortsNonQueuedBadReference(self):
        self.testCompletionPortsNonQueued(True)

    def testHashable(self):
        overlapped = pywintypes.OVERLAPPED()
        d = {}
        d[overlapped] = "hello"
        self.assertEqual(d[overlapped], "hello")

    def testComparable(self):
        overlapped = pywintypes.OVERLAPPED()
        self.assertEqual(overlapped, overlapped)
        # ensure we explicitly test the operators.
        self.assertTrue(overlapped == overlapped)
        self.assertFalse(overlapped != overlapped)

    def testComparable2(self):
        # 2 overlapped objects compare equal if their contents are the same.
        overlapped1 = pywintypes.OVERLAPPED()
        overlapped2 = pywintypes.OVERLAPPED()
        self.assertEqual(overlapped1, overlapped2)
        # ensure we explicitly test the operators.
        self.assertTrue(overlapped1 == overlapped2)
        self.assertFalse(overlapped1 != overlapped2)
        # now change something in one of them - should no longer be equal.
        overlapped1.hEvent = 1
        self.assertNotEqual(overlapped1, overlapped2)
        # ensure we explicitly test the operators.
        self.assertFalse(overlapped1 == overlapped2)
        self.assertTrue(overlapped1 != overlapped2)


class TestSocketExtensions(unittest.TestCase):
    def acceptWorker(self, port, running_event, stopped_event):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("", port))
        listener.listen(200)

        # create accept socket
        accepter = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # An overlapped
        overlapped = pywintypes.OVERLAPPED()
        overlapped.hEvent = win32event.CreateEvent(None, 0, 0, None)
        # accept the connection.
        # We used to allow strings etc to be passed here, and they would be
        # modified!  Obviously this is evil :)
        buffer = " " * 1024  # EVIL - SHOULD NOT BE ALLOWED.
        self.assertRaises(
            TypeError, win32file.AcceptEx, listener, accepter, buffer, overlapped
        )

        # This is the correct way to allocate the buffer...
        buffer = win32file.AllocateReadBuffer(1024)
        rc = win32file.AcceptEx(listener, accepter, buffer, overlapped)
        self.assertEqual(rc, winerror.ERROR_IO_PENDING)
        # Set the event to say we are all ready
        running_event.set()
        # and wait for the connection.
        rc = win32event.WaitForSingleObject(overlapped.hEvent, 2000)
        if rc == win32event.WAIT_TIMEOUT:
            self.fail("timed out waiting for a connection")
        nbytes = win32file.GetOverlappedResult(listener.fileno(), overlapped, False)
        # fam, loc, rem = win32file.GetAcceptExSockaddrs(accepter, buffer)
        accepter.send(buffer[:nbytes])
        # NOT set in a finally - this means *successfully* stopped!
        stopped_event.set()

    def testAcceptEx(self):
        port = 4680
        running = threading.Event()
        stopped = threading.Event()
        t = threading.Thread(target=self.acceptWorker, args=(port, running, stopped))
        t.start()
        running.wait(2)
        if not running.isSet():
            self.fail("AcceptEx Worker thread failed to start")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", port))
        win32file.WSASend(s, b"hello", None)
        overlapped = pywintypes.OVERLAPPED()
        overlapped.hEvent = win32event.CreateEvent(None, 0, 0, None)
        # Like above - WSARecv used to allow strings as the receive buffer!!
        buffer = " " * 10
        self.assertRaises(TypeError, win32file.WSARecv, s, buffer, overlapped)
        # This one should work :)
        buffer = win32file.AllocateReadBuffer(10)
        win32file.WSARecv(s, buffer, overlapped)
        nbytes = win32file.GetOverlappedResult(s.fileno(), overlapped, True)
        got = buffer[:nbytes]
        self.assertEqual(got, b"hello")
        # thread should have stopped
        stopped.wait(2)
        if not stopped.isSet():
            self.fail("AcceptEx Worker thread failed to successfully stop")


class TestFindFiles(unittest.TestCase):
    def testIter(self):
        dir = os.path.join(os.getcwd(), "*")
        files = win32file.FindFilesW(dir)
        set1 = set()
        set1.update(files)
        set2 = set()
        for file in win32file.FindFilesIterator(dir):
            set2.add(file)
        self.assertGreater(len(set2), 5, "This directory has less than 5 files!?")
        self.assertEqual(set1, set2)

    def testBadDir(self):
        dir = os.path.join(os.getcwd(), "a dir that doesn't exist", "*")
        self.assertRaises(win32file.error, win32file.FindFilesIterator, dir)

    def testEmptySpec(self):
        spec = os.path.join(os.getcwd(), "*.foo_bar")
        num = 0
        for i in win32file.FindFilesIterator(spec):
            num += 1
        self.assertEqual(0, num)

    def testEmptyDir(self):
        test_path = os.path.join(win32api.GetTempPath(), "win32file_test_directory")
        try:
            # Note: previously used shutil.rmtree, but when looking for
            # reference count leaks, that function showed leaks!  os.rmdir
            # doesn't have that problem.
            os.rmdir(test_path)
        except OSError:
            pass
        os.mkdir(test_path)
        try:
            num = 0
            for i in win32file.FindFilesIterator(os.path.join(test_path, "*")):
                num += 1
            # Expecting "." and ".." only
            self.assertEqual(2, num)
        finally:
            os.rmdir(test_path)


class TestDirectoryChanges(unittest.TestCase):
    num_test_dirs = 1

    def setUp(self):
        self.watcher_threads = []
        self.watcher_thread_changes = []
        self.dir_names = []
        self.dir_handles = []
        for i in range(self.num_test_dirs):
            td = tempfile.mktemp("-test-directory-changes-%d" % i)
            os.mkdir(td)
            self.dir_names.append(td)
            hdir = win32file.CreateFile(
                td,
                ntsecuritycon.FILE_LIST_DIRECTORY,
                win32con.FILE_SHARE_READ,
                None,  # security desc
                win32con.OPEN_EXISTING,
                win32con.FILE_FLAG_BACKUP_SEMANTICS | win32con.FILE_FLAG_OVERLAPPED,
                None,
            )
            self.dir_handles.append(hdir)

            changes = []
            t = threading.Thread(
                target=self._watcherThreadOverlapped, args=(td, hdir, changes)
            )
            t.start()
            self.watcher_threads.append(t)
            self.watcher_thread_changes.append(changes)

    def _watcherThread(self, dn, dh, changes):
        # A synchronous version:
        # XXX - not used - I was having a whole lot of problems trying to
        # get this to work.  Specifically:
        # * ReadDirectoryChangesW without an OVERLAPPED blocks infinitely.
        # * If another thread attempts to close the handle while
        #   ReadDirectoryChangesW is waiting on it, the ::CloseHandle() method
        #   blocks (which has nothing to do with the GIL - it is correctly
        #   managed)
        # Which ends up with no way to kill the thread!
        flags = win32con.FILE_NOTIFY_CHANGE_FILE_NAME
        while 1:
            try:
                print("waiting", dh)
                changes = win32file.ReadDirectoryChangesW(
                    dh,
                    8192,
                    False,  # sub-tree
                    flags,
                )
                print("got", changes)
            except:
                raise
            changes.extend(changes)

    def _watcherThreadOverlapped(self, dn, dh, changes):
        flags = win32con.FILE_NOTIFY_CHANGE_FILE_NAME
        buf = win32file.AllocateReadBuffer(8192)
        overlapped = pywintypes.OVERLAPPED()
        overlapped.hEvent = win32event.CreateEvent(None, 0, 0, None)
        while 1:
            win32file.ReadDirectoryChangesW(
                dh,
                buf,
                False,  # sub-tree
                flags,
                overlapped,
            )
            # Wait for our event, or for 5 seconds.
            rc = win32event.WaitForSingleObject(overlapped.hEvent, 5000)
            if rc == win32event.WAIT_OBJECT_0:
                # got some data!  Must use GetOverlappedResult to find out
                # how much is valid!  0 generally means the handle has
                # been closed.  Blocking is OK here, as the event has
                # already been set.
                nbytes = win32file.GetOverlappedResult(dh, overlapped, True)
                if nbytes:
                    bits = win32file.FILE_NOTIFY_INFORMATION(buf, nbytes)
                    changes.extend(bits)
                else:
                    # This is "normal" exit - our 'tearDown' closes the
                    # handle.
                    # print("looks like dir handle was closed!")
                    return
            else:
                print("ERROR: Watcher thread timed-out!")
                return  # kill the thread!

    def tearDown(self):
        # be careful about raising errors at teardown!
        for h in self.dir_handles:
            # See comments in _watcherThread above - this appears to
            # deadlock if a synchronous ReadDirectoryChangesW is waiting...
            # (No such problems with an asynch ReadDirectoryChangesW)
            h.Close()
        for dn in self.dir_names:
            try:
                shutil.rmtree(dn)
            except OSError:
                print("FAILED to remove directory", dn)

        for t in self.watcher_threads:
            # closing dir handle should have killed threads!
            t.join(5)
            if t.is_alive():
                print("FAILED to wait for thread termination")

    def stablize(self):
        time.sleep(0.5)

    def testSimple(self):
        self.stablize()
        for dn in self.dir_names:
            fn = os.path.join(dn, "test_file")
            open(fn, "w").close()

        self.stablize()
        changes = self.watcher_thread_changes[0]
        self.assertEqual(changes, [(1, "test_file")])

    def testSmall(self):
        self.stablize()
        for dn in self.dir_names:
            fn = os.path.join(dn, "x")
            open(fn, "w").close()

        self.stablize()
        changes = self.watcher_thread_changes[0]
        self.assertEqual(changes, [(1, "x")])


class TestEncrypt(unittest.TestCase):
    def testEncrypt(self):
        fname = tempfile.mktemp("win32file_test")
        f = open(fname, "wb")
        f.write(b"hello")
        f.close()
        f = None
        try:
            try:
                win32file.EncryptFile(fname)
            except win32file.error as details:
                if details.winerror != winerror.ERROR_ACCESS_DENIED:
                    raise
                print("It appears this is not NTFS - can't encrypt/decrypt")
            win32file.DecryptFile(fname)
        finally:
            if f is not None:
                f.close()
            os.unlink(fname)


class TestConnect(unittest.TestCase):
    def connect_thread_runner(self, expect_payload, giveup_event):
        # As Windows 2000 doesn't do ConnectEx, we need to use a non-blocking
        # accept, as our test connection may never come.  May as well use
        # AcceptEx for this...
        listener = socket.socket()
        self.addr = ("localhost", random.randint(10000, 64000))
        listener.bind(self.addr)
        listener.listen(1)

        # create accept socket
        accepter = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # An overlapped
        overlapped = pywintypes.OVERLAPPED()
        overlapped.hEvent = win32event.CreateEvent(None, 0, 0, None)
        # accept the connection.
        if expect_payload:
            buf_size = 1024
        else:
            # when we don't expect data we must be careful to only pass the
            # exact number of bytes for the endpoint data...
            buf_size = win32file.CalculateSocketEndPointSize(listener)

        buffer = win32file.AllocateReadBuffer(buf_size)
        win32file.AcceptEx(listener, accepter, buffer, overlapped)
        # wait for the connection or our test to fail.
        events = giveup_event, overlapped.hEvent
        rc = win32event.WaitForMultipleObjects(events, False, 2000)
        if rc == win32event.WAIT_TIMEOUT:
            self.fail("timed out waiting for a connection")
        if rc == win32event.WAIT_OBJECT_0:
            # Our main thread running the test failed and will never connect.
            return
        # must be a connection.
        nbytes = win32file.GetOverlappedResult(listener.fileno(), overlapped, False)
        if expect_payload:
            self.request = buffer[:nbytes]
        accepter.send(b"some expected response")

    def test_connect_with_payload(self):
        giveup_event = win32event.CreateEvent(None, 0, 0, None)
        t = threading.Thread(
            target=self.connect_thread_runner, args=(True, giveup_event)
        )
        t.start()
        time.sleep(0.1)
        s2 = socket.socket()
        ol = pywintypes.OVERLAPPED()
        s2.bind(("0.0.0.0", 0))  # connectex requires the socket be bound beforehand
        try:
            win32file.ConnectEx(s2, self.addr, ol, b"some expected request")
        except win32file.error as exc:
            win32event.SetEvent(giveup_event)
            if exc.winerror == 10022:  # WSAEINVAL
                raise TestSkipped("ConnectEx is not available on this platform")
            raise  # some error error we don't expect.
        # We occasionally see ERROR_CONNECTION_REFUSED in automation
        try:
            win32file.GetOverlappedResult(s2.fileno(), ol, 1)
        except win32file.error as exc:
            win32event.SetEvent(giveup_event)
            if exc.winerror == winerror.ERROR_CONNECTION_REFUSED:
                raise TestSkipped("Assuming ERROR_CONNECTION_REFUSED is transient")
            raise
        ol = pywintypes.OVERLAPPED()
        buff = win32file.AllocateReadBuffer(1024)
        win32file.WSARecv(s2, buff, ol, 0)
        length = win32file.GetOverlappedResult(s2.fileno(), ol, 1)
        self.response = buff[:length]
        self.assertEqual(self.response, b"some expected response")
        self.assertEqual(self.request, b"some expected request")
        t.join(5)
        self.assertFalse(t.is_alive(), "worker thread didn't terminate")

    def test_connect_without_payload(self):
        giveup_event = win32event.CreateEvent(None, 0, 0, None)
        t = threading.Thread(
            target=self.connect_thread_runner, args=(False, giveup_event)
        )
        t.start()
        time.sleep(0.1)
        s2 = socket.socket()
        ol = pywintypes.OVERLAPPED()
        s2.bind(("0.0.0.0", 0))  # connectex requires the socket be bound beforehand
        try:
            win32file.ConnectEx(s2, self.addr, ol)
        except win32file.error as exc:
            win32event.SetEvent(giveup_event)
            if exc.winerror == 10022:  # WSAEINVAL
                raise TestSkipped("ConnectEx is not available on this platform")
            raise  # some error error we don't expect.
        # We occasionally see ERROR_CONNECTION_REFUSED in automation
        try:
            win32file.GetOverlappedResult(s2.fileno(), ol, 1)
        except win32file.error as exc:
            win32event.SetEvent(giveup_event)
            if exc.winerror == winerror.ERROR_CONNECTION_REFUSED:
                raise TestSkipped("Assuming ERROR_CONNECTION_REFUSED is transient")
            raise

        ol = pywintypes.OVERLAPPED()
        buff = win32file.AllocateReadBuffer(1024)
        win32file.WSARecv(s2, buff, ol, 0)
        length = win32file.GetOverlappedResult(s2.fileno(), ol, 1)
        self.response = buff[:length]
        self.assertEqual(self.response, b"some expected response")
        t.join(5)
        self.assertFalse(t.is_alive(), "worker thread didn't terminate")


class TestTransmit(unittest.TestCase):
    def test_transmit(self):
        import binascii

        bytes = os.urandom(1024 * 1024)
        val = binascii.hexlify(bytes)
        val_length = len(val)
        f = tempfile.TemporaryFile()
        f.write(val)

        def runner():
            s1 = socket.socket()
            # binding fails occasionally on github CI with:
            # OSError: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
            # which probably just means the random port is already in use, so
            # let that happen a few times.
            for i in range(5):
                self.addr = ("localhost", random.randint(10000, 64000))
                try:
                    s1.bind(self.addr)
                    break
                except OSError as exc:
                    if exc.winerror != 10013:
                        raise
                    print("Failed to use port", self.addr, "trying another random one")
            else:
                raise AssertionError("Failed to find an available port to bind to.")
            s1.listen(1)
            cli, addr = s1.accept()
            buf = 1
            self.request = []
            while buf:
                buf = cli.recv(1024 * 100)
                self.request.append(buf)

        th = threading.Thread(target=runner)
        th.start()
        time.sleep(0.5)
        s2 = socket.socket()
        s2.connect(self.addr)

        length = 0
        aaa = b"[AAA]"
        bbb = b"[BBB]"
        ccc = b"[CCC]"
        ddd = b"[DDD]"
        empty = b""
        ol = pywintypes.OVERLAPPED()
        f.seek(0)
        win32file.TransmitFile(
            s2, win32file._get_osfhandle(f.fileno()), val_length, 0, ol, 0
        )
        length += win32file.GetOverlappedResult(s2.fileno(), ol, 1)

        ol = pywintypes.OVERLAPPED()
        f.seek(0)
        win32file.TransmitFile(
            s2, win32file._get_osfhandle(f.fileno()), val_length, 0, ol, 0, aaa, bbb
        )
        length += win32file.GetOverlappedResult(s2.fileno(), ol, 1)

        ol = pywintypes.OVERLAPPED()
        f.seek(0)
        win32file.TransmitFile(
            s2, win32file._get_osfhandle(f.fileno()), val_length, 0, ol, 0, empty, empty
        )
        length += win32file.GetOverlappedResult(s2.fileno(), ol, 1)

        ol = pywintypes.OVERLAPPED()
        f.seek(0)
        win32file.TransmitFile(
            s2, win32file._get_osfhandle(f.fileno()), val_length, 0, ol, 0, None, ccc
        )
        length += win32file.GetOverlappedResult(s2.fileno(), ol, 1)

        ol = pywintypes.OVERLAPPED()
        f.seek(0)
        win32file.TransmitFile(
            s2, win32file._get_osfhandle(f.fileno()), val_length, 0, ol, 0, ddd
        )
        length += win32file.GetOverlappedResult(s2.fileno(), ol, 1)

        s2.close()
        th.join()
        buf = b"".join(self.request)
        self.assertEqual(length, len(buf))
        expected = val + aaa + val + bbb + val + val + ccc + ddd + val
        self.assertEqual(type(expected), type(buf))
        self.assertEqual(expected, buf)


class TestWSAEnumNetworkEvents(unittest.TestCase):
    def test_basics(self):
        s = socket.socket()
        e = win32event.CreateEvent(None, 1, 0, None)
        win32file.WSAEventSelect(s, e, 0)
        self.assertEqual(win32file.WSAEnumNetworkEvents(s), {})
        self.assertEqual(win32file.WSAEnumNetworkEvents(s, e), {})
        self.assertRaises(TypeError, win32file.WSAEnumNetworkEvents, s, e, 3)
        self.assertRaises(TypeError, win32file.WSAEnumNetworkEvents, s, "spam")
        self.assertRaises(TypeError, win32file.WSAEnumNetworkEvents, "spam", e)
        self.assertRaises(TypeError, win32file.WSAEnumNetworkEvents, "spam")
        f = open("NUL")
        h = win32file._get_osfhandle(f.fileno())
        self.assertRaises(win32file.error, win32file.WSAEnumNetworkEvents, h)
        self.assertRaises(win32file.error, win32file.WSAEnumNetworkEvents, s, h)
        try:
            win32file.WSAEnumNetworkEvents(h)
        except win32file.error as e:
            self.assertEqual(e.winerror, win32file.WSAENOTSOCK)
        try:
            win32file.WSAEnumNetworkEvents(s, h)
        except win32file.error as e:
            # According to the docs it would seem reasonable that
            # this would fail with WSAEINVAL, but it doesn't.
            self.assertEqual(e.winerror, win32file.WSAENOTSOCK)

    def test_functional(self):
        # This is not really a unit test, but it does exercise the code
        # quite well and can serve as an example of WSAEventSelect and
        # WSAEnumNetworkEvents usage.
        port = socket.socket()
        port.setblocking(0)
        port_event = win32event.CreateEvent(None, 0, 0, None)
        win32file.WSAEventSelect(
            port, port_event, win32file.FD_ACCEPT | win32file.FD_CLOSE
        )
        port.bind(("127.0.0.1", 0))
        port.listen(10)

        client = socket.socket()
        client.setblocking(0)
        client_event = win32event.CreateEvent(None, 0, 0, None)
        win32file.WSAEventSelect(
            client,
            client_event,
            win32file.FD_CONNECT
            | win32file.FD_READ
            | win32file.FD_WRITE
            | win32file.FD_CLOSE,
        )
        err = client.connect_ex(port.getsockname())
        self.assertEqual(err, win32file.WSAEWOULDBLOCK)

        res = win32event.WaitForSingleObject(port_event, 1000)
        self.assertEqual(res, win32event.WAIT_OBJECT_0)
        events = win32file.WSAEnumNetworkEvents(port, port_event)
        self.assertEqual(events, {win32file.FD_ACCEPT: 0})

        server, addr = port.accept()
        server.setblocking(0)
        server_event = win32event.CreateEvent(None, 1, 0, None)
        win32file.WSAEventSelect(
            server,
            server_event,
            win32file.FD_READ | win32file.FD_WRITE | win32file.FD_CLOSE,
        )
        res = win32event.WaitForSingleObject(server_event, 1000)
        self.assertEqual(res, win32event.WAIT_OBJECT_0)
        events = win32file.WSAEnumNetworkEvents(server, server_event)
        self.assertEqual(events, {win32file.FD_WRITE: 0})

        res = win32event.WaitForSingleObject(client_event, 1000)
        self.assertEqual(res, win32event.WAIT_OBJECT_0)
        events = win32file.WSAEnumNetworkEvents(client, client_event)
        self.assertEqual(events, {win32file.FD_CONNECT: 0, win32file.FD_WRITE: 0})
        sent = 0
        data = b"x" * 16 * 1024
        while sent < 16 * 1024 * 1024:
            try:
                sent += client.send(data)
            except OSError as e:
                if e.args[0] == win32file.WSAEINTR:
                    continue
                elif e.args[0] in (win32file.WSAEWOULDBLOCK, win32file.WSAENOBUFS):
                    break
                else:
                    raise
        else:
            self.fail("could not find socket buffer limit")

        events = win32file.WSAEnumNetworkEvents(client)
        self.assertEqual(events, {})

        res = win32event.WaitForSingleObject(server_event, 1000)
        self.assertEqual(res, win32event.WAIT_OBJECT_0)
        events = win32file.WSAEnumNetworkEvents(server, server_event)
        self.assertEqual(events, {win32file.FD_READ: 0})

        received = 0
        while received < sent:
            try:
                received += len(server.recv(16 * 1024))
            except OSError as e:
                if e.args[0] in [win32file.WSAEINTR, win32file.WSAEWOULDBLOCK]:
                    continue
                else:
                    raise

        self.assertEqual(received, sent)
        events = win32file.WSAEnumNetworkEvents(server)
        self.assertEqual(events, {})

        res = win32event.WaitForSingleObject(client_event, 1000)
        self.assertEqual(res, win32event.WAIT_OBJECT_0)
        events = win32file.WSAEnumNetworkEvents(client, client_event)
        self.assertEqual(events, {win32file.FD_WRITE: 0})

        client.shutdown(socket.SHUT_WR)
        res = win32event.WaitForSingleObject(server_event, 1000)
        self.assertEqual(res, win32event.WAIT_OBJECT_0)
        # strange timing issues...
        for i in range(5):
            events = win32file.WSAEnumNetworkEvents(server, server_event)
            if events:
                break
            win32api.Sleep(100)
        else:
            raise AssertionError("failed to get events")
        self.assertEqual(events, {win32file.FD_CLOSE: 0})
        events = win32file.WSAEnumNetworkEvents(client)
        self.assertEqual(events, {})

        server.close()
        res = win32event.WaitForSingleObject(client_event, 1000)
        self.assertEqual(res, win32event.WAIT_OBJECT_0)
        events = win32file.WSAEnumNetworkEvents(client, client_event)
        self.assertEqual(events, {win32file.FD_CLOSE: 0})

        client.close()
        events = win32file.WSAEnumNetworkEvents(port)
        self.assertEqual(events, {})


if __name__ == "__main__":
    testmain()

# === NexusCore/openenv\Lib\site-packages\openai\_client.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Union, Mapping
from typing_extensions import Self, override

import httpx

from . import _exceptions
from ._qs import Querystring
from ._types import (
    NOT_GIVEN,
    Omit,
    Timeout,
    NotGiven,
    Transport,
    ProxiesTypes,
    RequestOptions,
)
from ._utils import (
    is_given,
    is_mapping,
    get_async_library,
)
from ._compat import cached_property
from ._version import __version__
from ._streaming import Stream as Stream, AsyncStream as AsyncStream
from ._exceptions import OpenAIError, APIStatusError
from ._base_client import (
    DEFAULT_MAX_RETRIES,
    SyncAPIClient,
    AsyncAPIClient,
)

if TYPE_CHECKING:
    from .resources import (
        beta,
        chat,
        audio,
        evals,
        files,
        images,
        models,
        batches,
        uploads,
        responses,
        containers,
        embeddings,
        completions,
        fine_tuning,
        moderations,
        vector_stores,
    )
    from .resources.files import Files, AsyncFiles
    from .resources.images import Images, AsyncImages
    from .resources.models import Models, AsyncModels
    from .resources.batches import Batches, AsyncBatches
    from .resources.beta.beta import Beta, AsyncBeta
    from .resources.chat.chat import Chat, AsyncChat
    from .resources.embeddings import Embeddings, AsyncEmbeddings
    from .resources.audio.audio import Audio, AsyncAudio
    from .resources.completions import Completions, AsyncCompletions
    from .resources.evals.evals import Evals, AsyncEvals
    from .resources.moderations import Moderations, AsyncModerations
    from .resources.uploads.uploads import Uploads, AsyncUploads
    from .resources.responses.responses import Responses, AsyncResponses
    from .resources.containers.containers import Containers, AsyncContainers
    from .resources.fine_tuning.fine_tuning import FineTuning, AsyncFineTuning
    from .resources.vector_stores.vector_stores import VectorStores, AsyncVectorStores

__all__ = ["Timeout", "Transport", "ProxiesTypes", "RequestOptions", "OpenAI", "AsyncOpenAI", "Client", "AsyncClient"]


class OpenAI(SyncAPIClient):
    # client options
    api_key: str
    organization: str | None
    project: str | None

    websocket_base_url: str | httpx.URL | None
    """Base URL for WebSocket connections.

    If not specified, the default base URL will be used, with 'wss://' replacing the
    'http://' or 'https://' scheme. For example: 'http://example.com' becomes
    'wss://example.com'
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        organization: str | None = None,
        project: str | None = None,
        base_url: str | httpx.URL | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        timeout: Union[float, Timeout, None, NotGiven] = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client.
        # We provide a `DefaultHttpxClient` class that you can pass to retain the default values we use for `limits`, `timeout` & `follow_redirects`.
        # See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.Client | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        """Construct a new synchronous OpenAI client instance.

        This automatically infers the following arguments from their corresponding environment variables if they are not provided:
        - `api_key` from `OPENAI_API_KEY`
        - `organization` from `OPENAI_ORG_ID`
        - `project` from `OPENAI_PROJECT_ID`
        """
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")
        if api_key is None:
            raise OpenAIError(
                "The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable"
            )
        self.api_key = api_key

        if organization is None:
            organization = os.environ.get("OPENAI_ORG_ID")
        self.organization = organization

        if project is None:
            project = os.environ.get("OPENAI_PROJECT_ID")
        self.project = project

        self.websocket_base_url = websocket_base_url

        if base_url is None:
            base_url = os.environ.get("OPENAI_BASE_URL")
        if base_url is None:
            base_url = f"https://api.openai.com/v1"

        super().__init__(
            version=__version__,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            http_client=http_client,
            custom_headers=default_headers,
            custom_query=default_query,
            _strict_response_validation=_strict_response_validation,
        )

        self._default_stream_cls = Stream

    @cached_property
    def completions(self) -> Completions:
        from .resources.completions import Completions

        return Completions(self)

    @cached_property
    def chat(self) -> Chat:
        from .resources.chat import Chat

        return Chat(self)

    @cached_property
    def embeddings(self) -> Embeddings:
        from .resources.embeddings import Embeddings

        return Embeddings(self)

    @cached_property
    def files(self) -> Files:
        from .resources.files import Files

        return Files(self)

    @cached_property
    def images(self) -> Images:
        from .resources.images import Images

        return Images(self)

    @cached_property
    def audio(self) -> Audio:
        from .resources.audio import Audio

        return Audio(self)

    @cached_property
    def moderations(self) -> Moderations:
        from .resources.moderations import Moderations

        return Moderations(self)

    @cached_property
    def models(self) -> Models:
        from .resources.models import Models

        return Models(self)

    @cached_property
    def fine_tuning(self) -> FineTuning:
        from .resources.fine_tuning import FineTuning

        return FineTuning(self)

    @cached_property
    def vector_stores(self) -> VectorStores:
        from .resources.vector_stores import VectorStores

        return VectorStores(self)

    @cached_property
    def beta(self) -> Beta:
        from .resources.beta import Beta

        return Beta(self)

    @cached_property
    def batches(self) -> Batches:
        from .resources.batches import Batches

        return Batches(self)

    @cached_property
    def uploads(self) -> Uploads:
        from .resources.uploads import Uploads

        return Uploads(self)

    @cached_property
    def responses(self) -> Responses:
        from .resources.responses import Responses

        return Responses(self)

    @cached_property
    def evals(self) -> Evals:
        from .resources.evals import Evals

        return Evals(self)

    @cached_property
    def containers(self) -> Containers:
        from .resources.containers import Containers

        return Containers(self)

    @cached_property
    def with_raw_response(self) -> OpenAIWithRawResponse:
        return OpenAIWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> OpenAIWithStreamedResponse:
        return OpenAIWithStreamedResponse(self)

    @property
    @override
    def qs(self) -> Querystring:
        return Querystring(array_format="brackets")

    @property
    @override
    def auth_headers(self) -> dict[str, str]:
        api_key = self.api_key
        return {"Authorization": f"Bearer {api_key}"}

    @property
    @override
    def default_headers(self) -> dict[str, str | Omit]:
        return {
            **super().default_headers,
            "X-Stainless-Async": "false",
            "OpenAI-Organization": self.organization if self.organization is not None else Omit(),
            "OpenAI-Project": self.project if self.project is not None else Omit(),
            **self._custom_headers,
        }

    def copy(
        self,
        *,
        api_key: str | None = None,
        organization: str | None = None,
        project: str | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.Client | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        http_client = http_client or self._client
        return self.__class__(
            api_key=api_key or self.api_key,
            organization=organization or self.organization,
            project=project or self.project,
            websocket_base_url=websocket_base_url or self.websocket_base_url,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy

    @override
    def _make_status_error(
        self,
        err_msg: str,
        *,
        body: object,
        response: httpx.Response,
    ) -> APIStatusError:
        data = body.get("error", body) if is_mapping(body) else body
        if response.status_code == 400:
            return _exceptions.BadRequestError(err_msg, response=response, body=data)

        if response.status_code == 401:
            return _exceptions.AuthenticationError(err_msg, response=response, body=data)

        if response.status_code == 403:
            return _exceptions.PermissionDeniedError(err_msg, response=response, body=data)

        if response.status_code == 404:
            return _exceptions.NotFoundError(err_msg, response=response, body=data)

        if response.status_code == 409:
            return _exceptions.ConflictError(err_msg, response=response, body=data)

        if response.status_code == 422:
            return _exceptions.UnprocessableEntityError(err_msg, response=response, body=data)

        if response.status_code == 429:
            return _exceptions.RateLimitError(err_msg, response=response, body=data)

        if response.status_code >= 500:
            return _exceptions.InternalServerError(err_msg, response=response, body=data)
        return APIStatusError(err_msg, response=response, body=data)


class AsyncOpenAI(AsyncAPIClient):
    # client options
    api_key: str
    organization: str | None
    project: str | None

    websocket_base_url: str | httpx.URL | None
    """Base URL for WebSocket connections.

    If not specified, the default base URL will be used, with 'wss://' replacing the
    'http://' or 'https://' scheme. For example: 'http://example.com' becomes
    'wss://example.com'
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        organization: str | None = None,
        project: str | None = None,
        base_url: str | httpx.URL | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        timeout: Union[float, Timeout, None, NotGiven] = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client.
        # We provide a `DefaultAsyncHttpxClient` class that you can pass to retain the default values we use for `limits`, `timeout` & `follow_redirects`.
        # See the [httpx documentation](https://www.python-httpx.org/api/#asyncclient) for more details.
        http_client: httpx.AsyncClient | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        """Construct a new async AsyncOpenAI client instance.

        This automatically infers the following arguments from their corresponding environment variables if they are not provided:
        - `api_key` from `OPENAI_API_KEY`
        - `organization` from `OPENAI_ORG_ID`
        - `project` from `OPENAI_PROJECT_ID`
        """
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")
        if api_key is None:
            raise OpenAIError(
                "The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable"
            )
        self.api_key = api_key

        if organization is None:
            organization = os.environ.get("OPENAI_ORG_ID")
        self.organization = organization

        if project is None:
            project = os.environ.get("OPENAI_PROJECT_ID")
        self.project = project

        self.websocket_base_url = websocket_base_url

        if base_url is None:
            base_url = os.environ.get("OPENAI_BASE_URL")
        if base_url is None:
            base_url = f"https://api.openai.com/v1"

        super().__init__(
            version=__version__,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            http_client=http_client,
            custom_headers=default_headers,
            custom_query=default_query,
            _strict_response_validation=_strict_response_validation,
        )

        self._default_stream_cls = AsyncStream

    @cached_property
    def completions(self) -> AsyncCompletions:
        from .resources.completions import AsyncCompletions

        return AsyncCompletions(self)

    @cached_property
    def chat(self) -> AsyncChat:
        from .resources.chat import AsyncChat

        return AsyncChat(self)

    @cached_property
    def embeddings(self) -> AsyncEmbeddings:
        from .resources.embeddings import AsyncEmbeddings

        return AsyncEmbeddings(self)

    @cached_property
    def files(self) -> AsyncFiles:
        from .resources.files import AsyncFiles

        return AsyncFiles(self)

    @cached_property
    def images(self) -> AsyncImages:
        from .resources.images import AsyncImages

        return AsyncImages(self)

    @cached_property
    def audio(self) -> AsyncAudio:
        from .resources.audio import AsyncAudio

        return AsyncAudio(self)

    @cached_property
    def moderations(self) -> AsyncModerations:
        from .resources.moderations import AsyncModerations

        return AsyncModerations(self)

    @cached_property
    def models(self) -> AsyncModels:
        from .resources.models import AsyncModels

        return AsyncModels(self)

    @cached_property
    def fine_tuning(self) -> AsyncFineTuning:
        from .resources.fine_tuning import AsyncFineTuning

        return AsyncFineTuning(self)

    @cached_property
    def vector_stores(self) -> AsyncVectorStores:
        from .resources.vector_stores import AsyncVectorStores

        return AsyncVectorStores(self)

    @cached_property
    def beta(self) -> AsyncBeta:
        from .resources.beta import AsyncBeta

        return AsyncBeta(self)

    @cached_property
    def batches(self) -> AsyncBatches:
        from .resources.batches import AsyncBatches

        return AsyncBatches(self)

    @cached_property
    def uploads(self) -> AsyncUploads:
        from .resources.uploads import AsyncUploads

        return AsyncUploads(self)

    @cached_property
    def responses(self) -> AsyncResponses:
        from .resources.responses import AsyncResponses

        return AsyncResponses(self)

    @cached_property
    def evals(self) -> AsyncEvals:
        from .resources.evals import AsyncEvals

        return AsyncEvals(self)

    @cached_property
    def containers(self) -> AsyncContainers:
        from .resources.containers import AsyncContainers

        return AsyncContainers(self)

    @cached_property
    def with_raw_response(self) -> AsyncOpenAIWithRawResponse:
        return AsyncOpenAIWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncOpenAIWithStreamedResponse:
        return AsyncOpenAIWithStreamedResponse(self)

    @property
    @override
    def qs(self) -> Querystring:
        return Querystring(array_format="brackets")

    @property
    @override
    def auth_headers(self) -> dict[str, str]:
        api_key = self.api_key
        return {"Authorization": f"Bearer {api_key}"}

    @property
    @override
    def default_headers(self) -> dict[str, str | Omit]:
        return {
            **super().default_headers,
            "X-Stainless-Async": f"async:{get_async_library()}",
            "OpenAI-Organization": self.organization if self.organization is not None else Omit(),
            "OpenAI-Project": self.project if self.project is not None else Omit(),
            **self._custom_headers,
        }

    def copy(
        self,
        *,
        api_key: str | None = None,
        organization: str | None = None,
        project: str | None = None,
        websocket_base_url: str | httpx.URL | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.AsyncClient | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        http_client = http_client or self._client
        return self.__class__(
            api_key=api_key or self.api_key,
            organization=organization or self.organization,
            project=project or self.project,
            websocket_base_url=websocket_base_url or self.websocket_base_url,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy

    @override
    def _make_status_error(
        self,
        err_msg: str,
        *,
        body: object,
        response: httpx.Response,
    ) -> APIStatusError:
        data = body.get("error", body) if is_mapping(body) else body
        if response.status_code == 400:
            return _exceptions.BadRequestError(err_msg, response=response, body=data)

        if response.status_code == 401:
            return _exceptions.AuthenticationError(err_msg, response=response, body=data)

        if response.status_code == 403:
            return _exceptions.PermissionDeniedError(err_msg, response=response, body=data)

        if response.status_code == 404:
            return _exceptions.NotFoundError(err_msg, response=response, body=data)

        if response.status_code == 409:
            return _exceptions.ConflictError(err_msg, response=response, body=data)

        if response.status_code == 422:
            return _exceptions.UnprocessableEntityError(err_msg, response=response, body=data)

        if response.status_code == 429:
            return _exceptions.RateLimitError(err_msg, response=response, body=data)

        if response.status_code >= 500:
            return _exceptions.InternalServerError(err_msg, response=response, body=data)
        return APIStatusError(err_msg, response=response, body=data)


class OpenAIWithRawResponse:
    _client: OpenAI

    def __init__(self, client: OpenAI) -> None:
        self._client = client

    @cached_property
    def completions(self) -> completions.CompletionsWithRawResponse:
        from .resources.completions import CompletionsWithRawResponse

        return CompletionsWithRawResponse(self._client.completions)

    @cached_property
    def chat(self) -> chat.ChatWithRawResponse:
        from .resources.chat import ChatWithRawResponse

        return ChatWithRawResponse(self._client.chat)

    @cached_property
    def embeddings(self) -> embeddings.EmbeddingsWithRawResponse:
        from .resources.embeddings import EmbeddingsWithRawResponse

        return EmbeddingsWithRawResponse(self._client.embeddings)

    @cached_property
    def files(self) -> files.FilesWithRawResponse:
        from .resources.files import FilesWithRawResponse

        return FilesWithRawResponse(self._client.files)

    @cached_property
    def images(self) -> images.ImagesWithRawResponse:
        from .resources.images import ImagesWithRawResponse

        return ImagesWithRawResponse(self._client.images)

    @cached_property
    def audio(self) -> audio.AudioWithRawResponse:
        from .resources.audio import AudioWithRawResponse

        return AudioWithRawResponse(self._client.audio)

    @cached_property
    def moderations(self) -> moderations.ModerationsWithRawResponse:
        from .resources.moderations import ModerationsWithRawResponse

        return ModerationsWithRawResponse(self._client.moderations)

    @cached_property
    def models(self) -> models.ModelsWithRawResponse:
        from .resources.models import ModelsWithRawResponse

        return ModelsWithRawResponse(self._client.models)

    @cached_property
    def fine_tuning(self) -> fine_tuning.FineTuningWithRawResponse:
        from .resources.fine_tuning import FineTuningWithRawResponse

        return FineTuningWithRawResponse(self._client.fine_tuning)

    @cached_property
    def vector_stores(self) -> vector_stores.VectorStoresWithRawResponse:
        from .resources.vector_stores import VectorStoresWithRawResponse

        return VectorStoresWithRawResponse(self._client.vector_stores)

    @cached_property
    def beta(self) -> beta.BetaWithRawResponse:
        from .resources.beta import BetaWithRawResponse

        return BetaWithRawResponse(self._client.beta)

    @cached_property
    def batches(self) -> batches.BatchesWithRawResponse:
        from .resources.batches import BatchesWithRawResponse

        return BatchesWithRawResponse(self._client.batches)

    @cached_property
    def uploads(self) -> uploads.UploadsWithRawResponse:
        from .resources.uploads import UploadsWithRawResponse

        return UploadsWithRawResponse(self._client.uploads)

    @cached_property
    def responses(self) -> responses.ResponsesWithRawResponse:
        from .resources.responses import ResponsesWithRawResponse

        return ResponsesWithRawResponse(self._client.responses)

    @cached_property
    def evals(self) -> evals.EvalsWithRawResponse:
        from .resources.evals import EvalsWithRawResponse

        return EvalsWithRawResponse(self._client.evals)

    @cached_property
    def containers(self) -> containers.ContainersWithRawResponse:
        from .resources.containers import ContainersWithRawResponse

        return ContainersWithRawResponse(self._client.containers)


class AsyncOpenAIWithRawResponse:
    _client: AsyncOpenAI

    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    @cached_property
    def completions(self) -> completions.AsyncCompletionsWithRawResponse:
        from .resources.completions import AsyncCompletionsWithRawResponse

        return AsyncCompletionsWithRawResponse(self._client.completions)

    @cached_property
    def chat(self) -> chat.AsyncChatWithRawResponse:
        from .resources.chat import AsyncChatWithRawResponse

        return AsyncChatWithRawResponse(self._client.chat)

    @cached_property
    def embeddings(self) -> embeddings.AsyncEmbeddingsWithRawResponse:
        from .resources.embeddings import AsyncEmbeddingsWithRawResponse

        return AsyncEmbeddingsWithRawResponse(self._client.embeddings)

    @cached_property
    def files(self) -> files.AsyncFilesWithRawResponse:
        from .resources.files import AsyncFilesWithRawResponse

        return AsyncFilesWithRawResponse(self._client.files)

    @cached_property
    def images(self) -> images.AsyncImagesWithRawResponse:
        from .resources.images import AsyncImagesWithRawResponse

        return AsyncImagesWithRawResponse(self._client.images)

    @cached_property
    def audio(self) -> audio.AsyncAudioWithRawResponse:
        from .resources.audio import AsyncAudioWithRawResponse

        return AsyncAudioWithRawResponse(self._client.audio)

    @cached_property
    def moderations(self) -> moderations.AsyncModerationsWithRawResponse:
        from .resources.moderations import AsyncModerationsWithRawResponse

        return AsyncModerationsWithRawResponse(self._client.moderations)

    @cached_property
    def models(self) -> models.AsyncModelsWithRawResponse:
        from .resources.models import AsyncModelsWithRawResponse

        return AsyncModelsWithRawResponse(self._client.models)

    @cached_property
    def fine_tuning(self) -> fine_tuning.AsyncFineTuningWithRawResponse:
        from .resources.fine_tuning import AsyncFineTuningWithRawResponse

        return AsyncFineTuningWithRawResponse(self._client.fine_tuning)

    @cached_property
    def vector_stores(self) -> vector_stores.AsyncVectorStoresWithRawResponse:
        from .resources.vector_stores import AsyncVectorStoresWithRawResponse

        return AsyncVectorStoresWithRawResponse(self._client.vector_stores)

    @cached_property
    def beta(self) -> beta.AsyncBetaWithRawResponse:
        from .resources.beta import AsyncBetaWithRawResponse

        return AsyncBetaWithRawResponse(self._client.beta)

    @cached_property
    def batches(self) -> batches.AsyncBatchesWithRawResponse:
        from .resources.batches import AsyncBatchesWithRawResponse

        return AsyncBatchesWithRawResponse(self._client.batches)

    @cached_property
    def uploads(self) -> uploads.AsyncUploadsWithRawResponse:
        from .resources.uploads import AsyncUploadsWithRawResponse

        return AsyncUploadsWithRawResponse(self._client.uploads)

    @cached_property
    def responses(self) -> responses.AsyncResponsesWithRawResponse:
        from .resources.responses import AsyncResponsesWithRawResponse

        return AsyncResponsesWithRawResponse(self._client.responses)

    @cached_property
    def evals(self) -> evals.AsyncEvalsWithRawResponse:
        from .resources.evals import AsyncEvalsWithRawResponse

        return AsyncEvalsWithRawResponse(self._client.evals)

    @cached_property
    def containers(self) -> containers.AsyncContainersWithRawResponse:
        from .resources.containers import AsyncContainersWithRawResponse

        return AsyncContainersWithRawResponse(self._client.containers)


class OpenAIWithStreamedResponse:
    _client: OpenAI

    def __init__(self, client: OpenAI) -> None:
        self._client = client

    @cached_property
    def completions(self) -> completions.CompletionsWithStreamingResponse:
        from .resources.completions import CompletionsWithStreamingResponse

        return CompletionsWithStreamingResponse(self._client.completions)

    @cached_property
    def chat(self) -> chat.ChatWithStreamingResponse:
        from .resources.chat import ChatWithStreamingResponse

        return ChatWithStreamingResponse(self._client.chat)

    @cached_property
    def embeddings(self) -> embeddings.EmbeddingsWithStreamingResponse:
        from .resources.embeddings import EmbeddingsWithStreamingResponse

        return EmbeddingsWithStreamingResponse(self._client.embeddings)

    @cached_property
    def files(self) -> files.FilesWithStreamingResponse:
        from .resources.files import FilesWithStreamingResponse

        return FilesWithStreamingResponse(self._client.files)

    @cached_property
    def images(self) -> images.ImagesWithStreamingResponse:
        from .resources.images import ImagesWithStreamingResponse

        return ImagesWithStreamingResponse(self._client.images)

    @cached_property
    def audio(self) -> audio.AudioWithStreamingResponse:
        from .resources.audio import AudioWithStreamingResponse

        return AudioWithStreamingResponse(self._client.audio)

    @cached_property
    def moderations(self) -> moderations.ModerationsWithStreamingResponse:
        from .resources.moderations import ModerationsWithStreamingResponse

        return ModerationsWithStreamingResponse(self._client.moderations)

    @cached_property
    def models(self) -> models.ModelsWithStreamingResponse:
        from .resources.models import ModelsWithStreamingResponse

        return ModelsWithStreamingResponse(self._client.models)

    @cached_property
    def fine_tuning(self) -> fine_tuning.FineTuningWithStreamingResponse:
        from .resources.fine_tuning import FineTuningWithStreamingResponse

        return FineTuningWithStreamingResponse(self._client.fine_tuning)

    @cached_property
    def vector_stores(self) -> vector_stores.VectorStoresWithStreamingResponse:
        from .resources.vector_stores import VectorStoresWithStreamingResponse

        return VectorStoresWithStreamingResponse(self._client.vector_stores)

    @cached_property
    def beta(self) -> beta.BetaWithStreamingResponse:
        from .resources.beta import BetaWithStreamingResponse

        return BetaWithStreamingResponse(self._client.beta)

    @cached_property
    def batches(self) -> batches.BatchesWithStreamingResponse:
        from .resources.batches import BatchesWithStreamingResponse

        return BatchesWithStreamingResponse(self._client.batches)

    @cached_property
    def uploads(self) -> uploads.UploadsWithStreamingResponse:
        from .resources.uploads import UploadsWithStreamingResponse

        return UploadsWithStreamingResponse(self._client.uploads)

    @cached_property
    def responses(self) -> responses.ResponsesWithStreamingResponse:
        from .resources.responses import ResponsesWithStreamingResponse

        return ResponsesWithStreamingResponse(self._client.responses)

    @cached_property
    def evals(self) -> evals.EvalsWithStreamingResponse:
        from .resources.evals import EvalsWithStreamingResponse

        return EvalsWithStreamingResponse(self._client.evals)

    @cached_property
    def containers(self) -> containers.ContainersWithStreamingResponse:
        from .resources.containers import ContainersWithStreamingResponse

        return ContainersWithStreamingResponse(self._client.containers)


class AsyncOpenAIWithStreamedResponse:
    _client: AsyncOpenAI

    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    @cached_property
    def completions(self) -> completions.AsyncCompletionsWithStreamingResponse:
        from .resources.completions import AsyncCompletionsWithStreamingResponse

        return AsyncCompletionsWithStreamingResponse(self._client.completions)

    @cached_property
    def chat(self) -> chat.AsyncChatWithStreamingResponse:
        from .resources.chat import AsyncChatWithStreamingResponse

        return AsyncChatWithStreamingResponse(self._client.chat)

    @cached_property
    def embeddings(self) -> embeddings.AsyncEmbeddingsWithStreamingResponse:
        from .resources.embeddings import AsyncEmbeddingsWithStreamingResponse

        return AsyncEmbeddingsWithStreamingResponse(self._client.embeddings)

    @cached_property
    def files(self) -> files.AsyncFilesWithStreamingResponse:
        from .resources.files import AsyncFilesWithStreamingResponse

        return AsyncFilesWithStreamingResponse(self._client.files)

    @cached_property
    def images(self) -> images.AsyncImagesWithStreamingResponse:
        from .resources.images import AsyncImagesWithStreamingResponse

        return AsyncImagesWithStreamingResponse(self._client.images)

    @cached_property
    def audio(self) -> audio.AsyncAudioWithStreamingResponse:
        from .resources.audio import AsyncAudioWithStreamingResponse

        return AsyncAudioWithStreamingResponse(self._client.audio)

    @cached_property
    def moderations(self) -> moderations.AsyncModerationsWithStreamingResponse:
        from .resources.moderations import AsyncModerationsWithStreamingResponse

        return AsyncModerationsWithStreamingResponse(self._client.moderations)

    @cached_property
    def models(self) -> models.AsyncModelsWithStreamingResponse:
        from .resources.models import AsyncModelsWithStreamingResponse

        return AsyncModelsWithStreamingResponse(self._client.models)

    @cached_property
    def fine_tuning(self) -> fine_tuning.AsyncFineTuningWithStreamingResponse:
        from .resources.fine_tuning import AsyncFineTuningWithStreamingResponse

        return AsyncFineTuningWithStreamingResponse(self._client.fine_tuning)

    @cached_property
    def vector_stores(self) -> vector_stores.AsyncVectorStoresWithStreamingResponse:
        from .resources.vector_stores import AsyncVectorStoresWithStreamingResponse

        return AsyncVectorStoresWithStreamingResponse(self._client.vector_stores)

    @cached_property
    def beta(self) -> beta.AsyncBetaWithStreamingResponse:
        from .resources.beta import AsyncBetaWithStreamingResponse

        return AsyncBetaWithStreamingResponse(self._client.beta)

    @cached_property
    def batches(self) -> batches.AsyncBatchesWithStreamingResponse:
        from .resources.batches import AsyncBatchesWithStreamingResponse

        return AsyncBatchesWithStreamingResponse(self._client.batches)

    @cached_property
    def uploads(self) -> uploads.AsyncUploadsWithStreamingResponse:
        from .resources.uploads import AsyncUploadsWithStreamingResponse

        return AsyncUploadsWithStreamingResponse(self._client.uploads)

    @cached_property
    def responses(self) -> responses.AsyncResponsesWithStreamingResponse:
        from .resources.responses import AsyncResponsesWithStreamingResponse

        return AsyncResponsesWithStreamingResponse(self._client.responses)

    @cached_property
    def evals(self) -> evals.AsyncEvalsWithStreamingResponse:
        from .resources.evals import AsyncEvalsWithStreamingResponse

        return AsyncEvalsWithStreamingResponse(self._client.evals)

    @cached_property
    def containers(self) -> containers.AsyncContainersWithStreamingResponse:
        from .resources.containers import AsyncContainersWithStreamingResponse

        return AsyncContainersWithStreamingResponse(self._client.containers)


Client = OpenAI

AsyncClient = AsyncOpenAI

# === NexusCore/openenv\Lib\site-packages\openai\resources\beta\realtime\realtime.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import json
import logging
from types import TracebackType
from typing import TYPE_CHECKING, Any, Iterator, cast
from typing_extensions import AsyncIterator

import httpx
from pydantic import BaseModel

from .sessions import (
    Sessions,
    AsyncSessions,
    SessionsWithRawResponse,
    AsyncSessionsWithRawResponse,
    SessionsWithStreamingResponse,
    AsyncSessionsWithStreamingResponse,
)
from ...._types import NOT_GIVEN, Query, Headers, NotGiven
from ...._utils import (
    is_azure_client,
    maybe_transform,
    strip_not_given,
    async_maybe_transform,
    is_async_azure_client,
)
from ...._compat import cached_property
from ...._models import construct_type_unchecked
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._exceptions import OpenAIError
from ...._base_client import _merge_mappings
from ....types.beta.realtime import (
    session_update_event_param,
    response_create_event_param,
    transcription_session_update_param,
)
from .transcription_sessions import (
    TranscriptionSessions,
    AsyncTranscriptionSessions,
    TranscriptionSessionsWithRawResponse,
    AsyncTranscriptionSessionsWithRawResponse,
    TranscriptionSessionsWithStreamingResponse,
    AsyncTranscriptionSessionsWithStreamingResponse,
)
from ....types.websocket_connection_options import WebsocketConnectionOptions
from ....types.beta.realtime.realtime_client_event import RealtimeClientEvent
from ....types.beta.realtime.realtime_server_event import RealtimeServerEvent
from ....types.beta.realtime.conversation_item_param import ConversationItemParam
from ....types.beta.realtime.realtime_client_event_param import RealtimeClientEventParam

if TYPE_CHECKING:
    from websockets.sync.client import ClientConnection as WebsocketConnection
    from websockets.asyncio.client import ClientConnection as AsyncWebsocketConnection

    from ...._client import OpenAI, AsyncOpenAI

__all__ = ["Realtime", "AsyncRealtime"]

log: logging.Logger = logging.getLogger(__name__)


class Realtime(SyncAPIResource):
    @cached_property
    def sessions(self) -> Sessions:
        return Sessions(self._client)

    @cached_property
    def transcription_sessions(self) -> TranscriptionSessions:
        return TranscriptionSessions(self._client)

    @cached_property
    def with_raw_response(self) -> RealtimeWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return RealtimeWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> RealtimeWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return RealtimeWithStreamingResponse(self)

    def connect(
        self,
        *,
        model: str,
        extra_query: Query = {},
        extra_headers: Headers = {},
        websocket_connection_options: WebsocketConnectionOptions = {},
    ) -> RealtimeConnectionManager:
        """
        The Realtime API enables you to build low-latency, multi-modal conversational experiences. It currently supports text and audio as both input and output, as well as function calling.

        Some notable benefits of the API include:

        - Native speech-to-speech: Skipping an intermediate text format means low latency and nuanced output.
        - Natural, steerable voices: The models have natural inflection and can laugh, whisper, and adhere to tone direction.
        - Simultaneous multimodal output: Text is useful for moderation; faster-than-realtime audio ensures stable playback.

        The Realtime API is a stateful, event-based API that communicates over a WebSocket.
        """
        return RealtimeConnectionManager(
            client=self._client,
            extra_query=extra_query,
            extra_headers=extra_headers,
            websocket_connection_options=websocket_connection_options,
            model=model,
        )


class AsyncRealtime(AsyncAPIResource):
    @cached_property
    def sessions(self) -> AsyncSessions:
        return AsyncSessions(self._client)

    @cached_property
    def transcription_sessions(self) -> AsyncTranscriptionSessions:
        return AsyncTranscriptionSessions(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncRealtimeWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncRealtimeWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncRealtimeWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncRealtimeWithStreamingResponse(self)

    def connect(
        self,
        *,
        model: str,
        extra_query: Query = {},
        extra_headers: Headers = {},
        websocket_connection_options: WebsocketConnectionOptions = {},
    ) -> AsyncRealtimeConnectionManager:
        """
        The Realtime API enables you to build low-latency, multi-modal conversational experiences. It currently supports text and audio as both input and output, as well as function calling.

        Some notable benefits of the API include:

        - Native speech-to-speech: Skipping an intermediate text format means low latency and nuanced output.
        - Natural, steerable voices: The models have natural inflection and can laugh, whisper, and adhere to tone direction.
        - Simultaneous multimodal output: Text is useful for moderation; faster-than-realtime audio ensures stable playback.

        The Realtime API is a stateful, event-based API that communicates over a WebSocket.
        """
        return AsyncRealtimeConnectionManager(
            client=self._client,
            extra_query=extra_query,
            extra_headers=extra_headers,
            websocket_connection_options=websocket_connection_options,
            model=model,
        )


class RealtimeWithRawResponse:
    def __init__(self, realtime: Realtime) -> None:
        self._realtime = realtime

    @cached_property
    def sessions(self) -> SessionsWithRawResponse:
        return SessionsWithRawResponse(self._realtime.sessions)

    @cached_property
    def transcription_sessions(self) -> TranscriptionSessionsWithRawResponse:
        return TranscriptionSessionsWithRawResponse(self._realtime.transcription_sessions)


class AsyncRealtimeWithRawResponse:
    def __init__(self, realtime: AsyncRealtime) -> None:
        self._realtime = realtime

    @cached_property
    def sessions(self) -> AsyncSessionsWithRawResponse:
        return AsyncSessionsWithRawResponse(self._realtime.sessions)

    @cached_property
    def transcription_sessions(self) -> AsyncTranscriptionSessionsWithRawResponse:
        return AsyncTranscriptionSessionsWithRawResponse(self._realtime.transcription_sessions)


class RealtimeWithStreamingResponse:
    def __init__(self, realtime: Realtime) -> None:
        self._realtime = realtime

    @cached_property
    def sessions(self) -> SessionsWithStreamingResponse:
        return SessionsWithStreamingResponse(self._realtime.sessions)

    @cached_property
    def transcription_sessions(self) -> TranscriptionSessionsWithStreamingResponse:
        return TranscriptionSessionsWithStreamingResponse(self._realtime.transcription_sessions)


class AsyncRealtimeWithStreamingResponse:
    def __init__(self, realtime: AsyncRealtime) -> None:
        self._realtime = realtime

    @cached_property
    def sessions(self) -> AsyncSessionsWithStreamingResponse:
        return AsyncSessionsWithStreamingResponse(self._realtime.sessions)

    @cached_property
    def transcription_sessions(self) -> AsyncTranscriptionSessionsWithStreamingResponse:
        return AsyncTranscriptionSessionsWithStreamingResponse(self._realtime.transcription_sessions)


class AsyncRealtimeConnection:
    """Represents a live websocket connection to the Realtime API"""

    session: AsyncRealtimeSessionResource
    response: AsyncRealtimeResponseResource
    input_audio_buffer: AsyncRealtimeInputAudioBufferResource
    conversation: AsyncRealtimeConversationResource
    output_audio_buffer: AsyncRealtimeOutputAudioBufferResource
    transcription_session: AsyncRealtimeTranscriptionSessionResource

    _connection: AsyncWebsocketConnection

    def __init__(self, connection: AsyncWebsocketConnection) -> None:
        self._connection = connection

        self.session = AsyncRealtimeSessionResource(self)
        self.response = AsyncRealtimeResponseResource(self)
        self.input_audio_buffer = AsyncRealtimeInputAudioBufferResource(self)
        self.conversation = AsyncRealtimeConversationResource(self)
        self.output_audio_buffer = AsyncRealtimeOutputAudioBufferResource(self)
        self.transcription_session = AsyncRealtimeTranscriptionSessionResource(self)

    async def __aiter__(self) -> AsyncIterator[RealtimeServerEvent]:
        """
        An infinite-iterator that will continue to yield events until
        the connection is closed.
        """
        from websockets.exceptions import ConnectionClosedOK

        try:
            while True:
                yield await self.recv()
        except ConnectionClosedOK:
            return

    async def recv(self) -> RealtimeServerEvent:
        """
        Receive the next message from the connection and parses it into a `RealtimeServerEvent` object.

        Canceling this method is safe. There's no risk of losing data.
        """
        return self.parse_event(await self.recv_bytes())

    async def recv_bytes(self) -> bytes:
        """Receive the next message from the connection as raw bytes.

        Canceling this method is safe. There's no risk of losing data.

        If you want to parse the message into a `RealtimeServerEvent` object like `.recv()` does,
        then you can call `.parse_event(data)`.
        """
        message = await self._connection.recv(decode=False)
        log.debug(f"Received websocket message: %s", message)
        return message

    async def send(self, event: RealtimeClientEvent | RealtimeClientEventParam) -> None:
        data = (
            event.to_json(use_api_names=True, exclude_defaults=True, exclude_unset=True)
            if isinstance(event, BaseModel)
            else json.dumps(await async_maybe_transform(event, RealtimeClientEventParam))
        )
        await self._connection.send(data)

    async def close(self, *, code: int = 1000, reason: str = "") -> None:
        await self._connection.close(code=code, reason=reason)

    def parse_event(self, data: str | bytes) -> RealtimeServerEvent:
        """
        Converts a raw `str` or `bytes` message into a `RealtimeServerEvent` object.

        This is helpful if you're using `.recv_bytes()`.
        """
        return cast(
            RealtimeServerEvent, construct_type_unchecked(value=json.loads(data), type_=cast(Any, RealtimeServerEvent))
        )


class AsyncRealtimeConnectionManager:
    """
    Context manager over a `AsyncRealtimeConnection` that is returned by `beta.realtime.connect()`

    This context manager ensures that the connection will be closed when it exits.

    ---

    Note that if your application doesn't work well with the context manager approach then you
    can call the `.enter()` method directly to initiate a connection.

    **Warning**: You must remember to close the connection with `.close()`.

    ```py
    connection = await client.beta.realtime.connect(...).enter()
    # ...
    await connection.close()
    ```
    """

    def __init__(
        self,
        *,
        client: AsyncOpenAI,
        model: str,
        extra_query: Query,
        extra_headers: Headers,
        websocket_connection_options: WebsocketConnectionOptions,
    ) -> None:
        self.__client = client
        self.__model = model
        self.__connection: AsyncRealtimeConnection | None = None
        self.__extra_query = extra_query
        self.__extra_headers = extra_headers
        self.__websocket_connection_options = websocket_connection_options

    async def __aenter__(self) -> AsyncRealtimeConnection:
        """
        👋 If your application doesn't work well with the context manager approach then you
        can call this method directly to initiate a connection.

        **Warning**: You must remember to close the connection with `.close()`.

        ```py
        connection = await client.beta.realtime.connect(...).enter()
        # ...
        await connection.close()
        ```
        """
        try:
            from websockets.asyncio.client import connect
        except ImportError as exc:
            raise OpenAIError("You need to install `openai[realtime]` to use this method") from exc

        extra_query = self.__extra_query
        auth_headers = self.__client.auth_headers
        if is_async_azure_client(self.__client):
            url, auth_headers = await self.__client._configure_realtime(self.__model, extra_query)
        else:
            url = self._prepare_url().copy_with(
                params={
                    **self.__client.base_url.params,
                    "model": self.__model,
                    **extra_query,
                },
            )
        log.debug("Connecting to %s", url)
        if self.__websocket_connection_options:
            log.debug("Connection options: %s", self.__websocket_connection_options)

        self.__connection = AsyncRealtimeConnection(
            await connect(
                str(url),
                user_agent_header=self.__client.user_agent,
                additional_headers=_merge_mappings(
                    {
                        **auth_headers,
                        "OpenAI-Beta": "realtime=v1",
                    },
                    self.__extra_headers,
                ),
                **self.__websocket_connection_options,
            )
        )

        return self.__connection

    enter = __aenter__

    def _prepare_url(self) -> httpx.URL:
        if self.__client.websocket_base_url is not None:
            base_url = httpx.URL(self.__client.websocket_base_url)
        else:
            base_url = self.__client._base_url.copy_with(scheme="wss")

        merge_raw_path = base_url.raw_path.rstrip(b"/") + b"/realtime"
        return base_url.copy_with(raw_path=merge_raw_path)

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        if self.__connection is not None:
            await self.__connection.close()


class RealtimeConnection:
    """Represents a live websocket connection to the Realtime API"""

    session: RealtimeSessionResource
    response: RealtimeResponseResource
    input_audio_buffer: RealtimeInputAudioBufferResource
    conversation: RealtimeConversationResource
    output_audio_buffer: RealtimeOutputAudioBufferResource
    transcription_session: RealtimeTranscriptionSessionResource

    _connection: WebsocketConnection

    def __init__(self, connection: WebsocketConnection) -> None:
        self._connection = connection

        self.session = RealtimeSessionResource(self)
        self.response = RealtimeResponseResource(self)
        self.input_audio_buffer = RealtimeInputAudioBufferResource(self)
        self.conversation = RealtimeConversationResource(self)
        self.output_audio_buffer = RealtimeOutputAudioBufferResource(self)
        self.transcription_session = RealtimeTranscriptionSessionResource(self)

    def __iter__(self) -> Iterator[RealtimeServerEvent]:
        """
        An infinite-iterator that will continue to yield events until
        the connection is closed.
        """
        from websockets.exceptions import ConnectionClosedOK

        try:
            while True:
                yield self.recv()
        except ConnectionClosedOK:
            return

    def recv(self) -> RealtimeServerEvent:
        """
        Receive the next message from the connection and parses it into a `RealtimeServerEvent` object.

        Canceling this method is safe. There's no risk of losing data.
        """
        return self.parse_event(self.recv_bytes())

    def recv_bytes(self) -> bytes:
        """Receive the next message from the connection as raw bytes.

        Canceling this method is safe. There's no risk of losing data.

        If you want to parse the message into a `RealtimeServerEvent` object like `.recv()` does,
        then you can call `.parse_event(data)`.
        """
        message = self._connection.recv(decode=False)
        log.debug(f"Received websocket message: %s", message)
        return message

    def send(self, event: RealtimeClientEvent | RealtimeClientEventParam) -> None:
        data = (
            event.to_json(use_api_names=True, exclude_defaults=True, exclude_unset=True)
            if isinstance(event, BaseModel)
            else json.dumps(maybe_transform(event, RealtimeClientEventParam))
        )
        self._connection.send(data)

    def close(self, *, code: int = 1000, reason: str = "") -> None:
        self._connection.close(code=code, reason=reason)

    def parse_event(self, data: str | bytes) -> RealtimeServerEvent:
        """
        Converts a raw `str` or `bytes` message into a `RealtimeServerEvent` object.

        This is helpful if you're using `.recv_bytes()`.
        """
        return cast(
            RealtimeServerEvent, construct_type_unchecked(value=json.loads(data), type_=cast(Any, RealtimeServerEvent))
        )


class RealtimeConnectionManager:
    """
    Context manager over a `RealtimeConnection` that is returned by `beta.realtime.connect()`

    This context manager ensures that the connection will be closed when it exits.

    ---

    Note that if your application doesn't work well with the context manager approach then you
    can call the `.enter()` method directly to initiate a connection.

    **Warning**: You must remember to close the connection with `.close()`.

    ```py
    connection = client.beta.realtime.connect(...).enter()
    # ...
    connection.close()
    ```
    """

    def __init__(
        self,
        *,
        client: OpenAI,
        model: str,
        extra_query: Query,
        extra_headers: Headers,
        websocket_connection_options: WebsocketConnectionOptions,
    ) -> None:
        self.__client = client
        self.__model = model
        self.__connection: RealtimeConnection | None = None
        self.__extra_query = extra_query
        self.__extra_headers = extra_headers
        self.__websocket_connection_options = websocket_connection_options

    def __enter__(self) -> RealtimeConnection:
        """
        👋 If your application doesn't work well with the context manager approach then you
        can call this method directly to initiate a connection.

        **Warning**: You must remember to close the connection with `.close()`.

        ```py
        connection = client.beta.realtime.connect(...).enter()
        # ...
        connection.close()
        ```
        """
        try:
            from websockets.sync.client import connect
        except ImportError as exc:
            raise OpenAIError("You need to install `openai[realtime]` to use this method") from exc

        extra_query = self.__extra_query
        auth_headers = self.__client.auth_headers
        if is_azure_client(self.__client):
            url, auth_headers = self.__client._configure_realtime(self.__model, extra_query)
        else:
            url = self._prepare_url().copy_with(
                params={
                    **self.__client.base_url.params,
                    "model": self.__model,
                    **extra_query,
                },
            )
        log.debug("Connecting to %s", url)
        if self.__websocket_connection_options:
            log.debug("Connection options: %s", self.__websocket_connection_options)

        self.__connection = RealtimeConnection(
            connect(
                str(url),
                user_agent_header=self.__client.user_agent,
                additional_headers=_merge_mappings(
                    {
                        **auth_headers,
                        "OpenAI-Beta": "realtime=v1",
                    },
                    self.__extra_headers,
                ),
                **self.__websocket_connection_options,
            )
        )

        return self.__connection

    enter = __enter__

    def _prepare_url(self) -> httpx.URL:
        if self.__client.websocket_base_url is not None:
            base_url = httpx.URL(self.__client.websocket_base_url)
        else:
            base_url = self.__client._base_url.copy_with(scheme="wss")

        merge_raw_path = base_url.raw_path.rstrip(b"/") + b"/realtime"
        return base_url.copy_with(raw_path=merge_raw_path)

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        if self.__connection is not None:
            self.__connection.close()


class BaseRealtimeConnectionResource:
    def __init__(self, connection: RealtimeConnection) -> None:
        self._connection = connection


class RealtimeSessionResource(BaseRealtimeConnectionResource):
    def update(self, *, session: session_update_event_param.Session, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """
        Send this event to update the session’s default configuration.
        The client may send this event at any time to update any field,
        except for `voice`. However, note that once a session has been
        initialized with a particular `model`, it can’t be changed to
        another model using `session.update`.

        When the server receives a `session.update`, it will respond
        with a `session.updated` event showing the full, effective configuration.
        Only the fields that are present are updated. To clear a field like
        `instructions`, pass an empty string.
        """
        self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "session.update", "session": session, "event_id": event_id}),
            )
        )


class RealtimeResponseResource(BaseRealtimeConnectionResource):
    def create(
        self,
        *,
        event_id: str | NotGiven = NOT_GIVEN,
        response: response_create_event_param.Response | NotGiven = NOT_GIVEN,
    ) -> None:
        """
        This event instructs the server to create a Response, which means triggering
        model inference. When in Server VAD mode, the server will create Responses
        automatically.

        A Response will include at least one Item, and may have two, in which case
        the second will be a function call. These Items will be appended to the
        conversation history.

        The server will respond with a `response.created` event, events for Items
        and content created, and finally a `response.done` event to indicate the
        Response is complete.

        The `response.create` event includes inference configuration like
        `instructions`, and `temperature`. These fields will override the Session's
        configuration for this Response only.
        """
        self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "response.create", "event_id": event_id, "response": response}),
            )
        )

    def cancel(self, *, event_id: str | NotGiven = NOT_GIVEN, response_id: str | NotGiven = NOT_GIVEN) -> None:
        """Send this event to cancel an in-progress response.

        The server will respond
        with a `response.cancelled` event or an error if there is no response to
        cancel.
        """
        self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "response.cancel", "event_id": event_id, "response_id": response_id}),
            )
        )


class RealtimeInputAudioBufferResource(BaseRealtimeConnectionResource):
    def clear(self, *, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """Send this event to clear the audio bytes in the buffer.

        The server will
        respond with an `input_audio_buffer.cleared` event.
        """
        self._connection.send(
            cast(RealtimeClientEventParam, strip_not_given({"type": "input_audio_buffer.clear", "event_id": event_id}))
        )

    def commit(self, *, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """
        Send this event to commit the user input audio buffer, which will create a
        new user message item in the conversation. This event will produce an error
        if the input audio buffer is empty. When in Server VAD mode, the client does
        not need to send this event, the server will commit the audio buffer
        automatically.

        Committing the input audio buffer will trigger input audio transcription
        (if enabled in session configuration), but it will not create a response
        from the model. The server will respond with an `input_audio_buffer.committed`
        event.
        """
        self._connection.send(
            cast(RealtimeClientEventParam, strip_not_given({"type": "input_audio_buffer.commit", "event_id": event_id}))
        )

    def append(self, *, audio: str, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """Send this event to append audio bytes to the input audio buffer.

        The audio
        buffer is temporary storage you can write to and later commit. In Server VAD
        mode, the audio buffer is used to detect speech and the server will decide
        when to commit. When Server VAD is disabled, you must commit the audio buffer
        manually.

        The client may choose how much audio to place in each event up to a maximum
        of 15 MiB, for example streaming smaller chunks from the client may allow the
        VAD to be more responsive. Unlike made other client events, the server will
        not send a confirmation response to this event.
        """
        self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "input_audio_buffer.append", "audio": audio, "event_id": event_id}),
            )
        )


class RealtimeConversationResource(BaseRealtimeConnectionResource):
    @cached_property
    def item(self) -> RealtimeConversationItemResource:
        return RealtimeConversationItemResource(self._connection)


class RealtimeConversationItemResource(BaseRealtimeConnectionResource):
    def delete(self, *, item_id: str, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """Send this event when you want to remove any item from the conversation
        history.

        The server will respond with a `conversation.item.deleted` event,
        unless the item does not exist in the conversation history, in which case the
        server will respond with an error.
        """
        self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "conversation.item.delete", "item_id": item_id, "event_id": event_id}),
            )
        )

    def create(
        self,
        *,
        item: ConversationItemParam,
        event_id: str | NotGiven = NOT_GIVEN,
        previous_item_id: str | NotGiven = NOT_GIVEN,
    ) -> None:
        """
        Add a new Item to the Conversation's context, including messages, function
        calls, and function call responses. This event can be used both to populate a
        "history" of the conversation and to add new items mid-stream, but has the
        current limitation that it cannot populate assistant audio messages.

        If successful, the server will respond with a `conversation.item.created`
        event, otherwise an `error` event will be sent.
        """
        self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given(
                    {
                        "type": "conversation.item.create",
                        "item": item,
                        "event_id": event_id,
                        "previous_item_id": previous_item_id,
                    }
                ),
            )
        )

    def truncate(
        self, *, audio_end_ms: int, content_index: int, item_id: str, event_id: str | NotGiven = NOT_GIVEN
    ) -> None:
        """Send this event to truncate a previous assistant message’s audio.

        The server
        will produce audio faster than realtime, so this event is useful when the user
        interrupts to truncate audio that has already been sent to the client but not
        yet played. This will synchronize the server's understanding of the audio with
        the client's playback.

        Truncating audio will delete the server-side text transcript to ensure there
        is not text in the context that hasn't been heard by the user.

        If successful, the server will respond with a `conversation.item.truncated`
        event.
        """
        self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given(
                    {
                        "type": "conversation.item.truncate",
                        "audio_end_ms": audio_end_ms,
                        "content_index": content_index,
                        "item_id": item_id,
                        "event_id": event_id,
                    }
                ),
            )
        )

    def retrieve(self, *, item_id: str, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """
        Send this event when you want to retrieve the server's representation of a specific item in the conversation history. This is useful, for example, to inspect user audio after noise cancellation and VAD.
        The server will respond with a `conversation.item.retrieved` event,
        unless the item does not exist in the conversation history, in which case the
        server will respond with an error.
        """
        self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "conversation.item.retrieve", "item_id": item_id, "event_id": event_id}),
            )
        )


class RealtimeOutputAudioBufferResource(BaseRealtimeConnectionResource):
    def clear(self, *, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """**WebRTC Only:** Emit to cut off the current audio response.

        This will trigger the server to
        stop generating audio and emit a `output_audio_buffer.cleared` event. This
        event should be preceded by a `response.cancel` client event to stop the
        generation of the current response.
        [Learn more](https://platform.openai.com/docs/guides/realtime-conversations#client-and-server-events-for-audio-in-webrtc).
        """
        self._connection.send(
            cast(RealtimeClientEventParam, strip_not_given({"type": "output_audio_buffer.clear", "event_id": event_id}))
        )


class RealtimeTranscriptionSessionResource(BaseRealtimeConnectionResource):
    def update(
        self, *, session: transcription_session_update_param.Session, event_id: str | NotGiven = NOT_GIVEN
    ) -> None:
        """Send this event to update a transcription session."""
        self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "transcription_session.update", "session": session, "event_id": event_id}),
            )
        )


class BaseAsyncRealtimeConnectionResource:
    def __init__(self, connection: AsyncRealtimeConnection) -> None:
        self._connection = connection


class AsyncRealtimeSessionResource(BaseAsyncRealtimeConnectionResource):
    async def update(
        self, *, session: session_update_event_param.Session, event_id: str | NotGiven = NOT_GIVEN
    ) -> None:
        """
        Send this event to update the session’s default configuration.
        The client may send this event at any time to update any field,
        except for `voice`. However, note that once a session has been
        initialized with a particular `model`, it can’t be changed to
        another model using `session.update`.

        When the server receives a `session.update`, it will respond
        with a `session.updated` event showing the full, effective configuration.
        Only the fields that are present are updated. To clear a field like
        `instructions`, pass an empty string.
        """
        await self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "session.update", "session": session, "event_id": event_id}),
            )
        )


class AsyncRealtimeResponseResource(BaseAsyncRealtimeConnectionResource):
    async def create(
        self,
        *,
        event_id: str | NotGiven = NOT_GIVEN,
        response: response_create_event_param.Response | NotGiven = NOT_GIVEN,
    ) -> None:
        """
        This event instructs the server to create a Response, which means triggering
        model inference. When in Server VAD mode, the server will create Responses
        automatically.

        A Response will include at least one Item, and may have two, in which case
        the second will be a function call. These Items will be appended to the
        conversation history.

        The server will respond with a `response.created` event, events for Items
        and content created, and finally a `response.done` event to indicate the
        Response is complete.

        The `response.create` event includes inference configuration like
        `instructions`, and `temperature`. These fields will override the Session's
        configuration for this Response only.
        """
        await self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "response.create", "event_id": event_id, "response": response}),
            )
        )

    async def cancel(self, *, event_id: str | NotGiven = NOT_GIVEN, response_id: str | NotGiven = NOT_GIVEN) -> None:
        """Send this event to cancel an in-progress response.

        The server will respond
        with a `response.cancelled` event or an error if there is no response to
        cancel.
        """
        await self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "response.cancel", "event_id": event_id, "response_id": response_id}),
            )
        )


class AsyncRealtimeInputAudioBufferResource(BaseAsyncRealtimeConnectionResource):
    async def clear(self, *, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """Send this event to clear the audio bytes in the buffer.

        The server will
        respond with an `input_audio_buffer.cleared` event.
        """
        await self._connection.send(
            cast(RealtimeClientEventParam, strip_not_given({"type": "input_audio_buffer.clear", "event_id": event_id}))
        )

    async def commit(self, *, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """
        Send this event to commit the user input audio buffer, which will create a
        new user message item in the conversation. This event will produce an error
        if the input audio buffer is empty. When in Server VAD mode, the client does
        not need to send this event, the server will commit the audio buffer
        automatically.

        Committing the input audio buffer will trigger input audio transcription
        (if enabled in session configuration), but it will not create a response
        from the model. The server will respond with an `input_audio_buffer.committed`
        event.
        """
        await self._connection.send(
            cast(RealtimeClientEventParam, strip_not_given({"type": "input_audio_buffer.commit", "event_id": event_id}))
        )

    async def append(self, *, audio: str, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """Send this event to append audio bytes to the input audio buffer.

        The audio
        buffer is temporary storage you can write to and later commit. In Server VAD
        mode, the audio buffer is used to detect speech and the server will decide
        when to commit. When Server VAD is disabled, you must commit the audio buffer
        manually.

        The client may choose how much audio to place in each event up to a maximum
        of 15 MiB, for example streaming smaller chunks from the client may allow the
        VAD to be more responsive. Unlike made other client events, the server will
        not send a confirmation response to this event.
        """
        await self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "input_audio_buffer.append", "audio": audio, "event_id": event_id}),
            )
        )


class AsyncRealtimeConversationResource(BaseAsyncRealtimeConnectionResource):
    @cached_property
    def item(self) -> AsyncRealtimeConversationItemResource:
        return AsyncRealtimeConversationItemResource(self._connection)


class AsyncRealtimeConversationItemResource(BaseAsyncRealtimeConnectionResource):
    async def delete(self, *, item_id: str, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """Send this event when you want to remove any item from the conversation
        history.

        The server will respond with a `conversation.item.deleted` event,
        unless the item does not exist in the conversation history, in which case the
        server will respond with an error.
        """
        await self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "conversation.item.delete", "item_id": item_id, "event_id": event_id}),
            )
        )

    async def create(
        self,
        *,
        item: ConversationItemParam,
        event_id: str | NotGiven = NOT_GIVEN,
        previous_item_id: str | NotGiven = NOT_GIVEN,
    ) -> None:
        """
        Add a new Item to the Conversation's context, including messages, function
        calls, and function call responses. This event can be used both to populate a
        "history" of the conversation and to add new items mid-stream, but has the
        current limitation that it cannot populate assistant audio messages.

        If successful, the server will respond with a `conversation.item.created`
        event, otherwise an `error` event will be sent.
        """
        await self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given(
                    {
                        "type": "conversation.item.create",
                        "item": item,
                        "event_id": event_id,
                        "previous_item_id": previous_item_id,
                    }
                ),
            )
        )

    async def truncate(
        self, *, audio_end_ms: int, content_index: int, item_id: str, event_id: str | NotGiven = NOT_GIVEN
    ) -> None:
        """Send this event to truncate a previous assistant message’s audio.

        The server
        will produce audio faster than realtime, so this event is useful when the user
        interrupts to truncate audio that has already been sent to the client but not
        yet played. This will synchronize the server's understanding of the audio with
        the client's playback.

        Truncating audio will delete the server-side text transcript to ensure there
        is not text in the context that hasn't been heard by the user.

        If successful, the server will respond with a `conversation.item.truncated`
        event.
        """
        await self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given(
                    {
                        "type": "conversation.item.truncate",
                        "audio_end_ms": audio_end_ms,
                        "content_index": content_index,
                        "item_id": item_id,
                        "event_id": event_id,
                    }
                ),
            )
        )

    async def retrieve(self, *, item_id: str, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """
        Send this event when you want to retrieve the server's representation of a specific item in the conversation history. This is useful, for example, to inspect user audio after noise cancellation and VAD.
        The server will respond with a `conversation.item.retrieved` event,
        unless the item does not exist in the conversation history, in which case the
        server will respond with an error.
        """
        await self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "conversation.item.retrieve", "item_id": item_id, "event_id": event_id}),
            )
        )


class AsyncRealtimeOutputAudioBufferResource(BaseAsyncRealtimeConnectionResource):
    async def clear(self, *, event_id: str | NotGiven = NOT_GIVEN) -> None:
        """**WebRTC Only:** Emit to cut off the current audio response.

        This will trigger the server to
        stop generating audio and emit a `output_audio_buffer.cleared` event. This
        event should be preceded by a `response.cancel` client event to stop the
        generation of the current response.
        [Learn more](https://platform.openai.com/docs/guides/realtime-conversations#client-and-server-events-for-audio-in-webrtc).
        """
        await self._connection.send(
            cast(RealtimeClientEventParam, strip_not_given({"type": "output_audio_buffer.clear", "event_id": event_id}))
        )


class AsyncRealtimeTranscriptionSessionResource(BaseAsyncRealtimeConnectionResource):
    async def update(
        self, *, session: transcription_session_update_param.Session, event_id: str | NotGiven = NOT_GIVEN
    ) -> None:
        """Send this event to update a transcription session."""
        await self._connection.send(
            cast(
                RealtimeClientEventParam,
                strip_not_given({"type": "transcription_session.update", "session": session, "event_id": event_id}),
            )
        )

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\jaraco\collections\__init__.py ===
from __future__ import annotations

import collections.abc
import copy
import functools
import itertools
import operator
import random
import re
from collections.abc import Container, Iterable, Mapping
from typing import TYPE_CHECKING, Any, Callable, Dict, TypeVar, Union, overload

import jaraco.text

if TYPE_CHECKING:
    from _operator import _SupportsComparison

    from _typeshed import SupportsKeysAndGetItem
    from typing_extensions import Self

    _RangeMapKT = TypeVar('_RangeMapKT', bound=_SupportsComparison)
else:
    # _SupportsComparison doesn't exist at runtime,
    # but _RangeMapKT is used in RangeMap's superclass' type parameters
    _RangeMapKT = TypeVar('_RangeMapKT')

_T = TypeVar('_T')
_VT = TypeVar('_VT')

_Matchable = Union[Callable, Container, Iterable, re.Pattern]


def _dispatch(obj: _Matchable) -> Callable:
    # can't rely on singledispatch for Union[Container, Iterable]
    # due to ambiguity
    # (https://peps.python.org/pep-0443/#abstract-base-classes).
    if isinstance(obj, re.Pattern):
        return obj.fullmatch
    # mypy issue: https://github.com/python/mypy/issues/11071
    if not isinstance(obj, Callable):  # type: ignore[arg-type]
        if not isinstance(obj, Container):
            obj = set(obj)  # type: ignore[arg-type]
        obj = obj.__contains__
    return obj  # type: ignore[return-value]


class Projection(collections.abc.Mapping):
    """
    Project a set of keys over a mapping

    >>> sample = {'a': 1, 'b': 2, 'c': 3}
    >>> prj = Projection(['a', 'c', 'd'], sample)
    >>> dict(prj)
    {'a': 1, 'c': 3}

    Projection also accepts an iterable or callable or pattern.

    >>> iter_prj = Projection(iter('acd'), sample)
    >>> call_prj = Projection(lambda k: ord(k) in (97, 99, 100), sample)
    >>> pat_prj = Projection(re.compile(r'[acd]'), sample)
    >>> prj == iter_prj == call_prj == pat_prj
    True

    Keys should only appear if they were specified and exist in the space.
    Order is retained.

    >>> list(prj)
    ['a', 'c']

    Attempting to access a key not in the projection
    results in a KeyError.

    >>> prj['b']
    Traceback (most recent call last):
    ...
    KeyError: 'b'

    Use the projection to update another dict.

    >>> target = {'a': 2, 'b': 2}
    >>> target.update(prj)
    >>> target
    {'a': 1, 'b': 2, 'c': 3}

    Projection keeps a reference to the original dict, so
    modifying the original dict may modify the Projection.

    >>> del sample['a']
    >>> dict(prj)
    {'c': 3}
    """

    def __init__(self, keys: _Matchable, space: Mapping):
        self._match = _dispatch(keys)
        self._space = space

    def __getitem__(self, key):
        if not self._match(key):
            raise KeyError(key)
        return self._space[key]

    def _keys_resolved(self):
        return filter(self._match, self._space)

    def __iter__(self):
        return self._keys_resolved()

    def __len__(self):
        return len(tuple(self._keys_resolved()))


class Mask(Projection):
    """
    The inverse of a :class:`Projection`, masking out keys.

    >>> sample = {'a': 1, 'b': 2, 'c': 3}
    >>> msk = Mask(['a', 'c', 'd'], sample)
    >>> dict(msk)
    {'b': 2}
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self._match = compose(operator.not_, self._match)
        self._match = lambda key, orig=self._match: not orig(key)


def dict_map(function, dictionary):
    """
    Return a new dict with function applied to values of dictionary.

    >>> dict_map(lambda x: x+1, dict(a=1, b=2))
    {'a': 2, 'b': 3}
    """
    return dict((key, function(value)) for key, value in dictionary.items())


class RangeMap(Dict[_RangeMapKT, _VT]):
    """
    A dictionary-like object that uses the keys as bounds for a range.
    Inclusion of the value for that range is determined by the
    key_match_comparator, which defaults to less-than-or-equal.
    A value is returned for a key if it is the first key that matches in
    the sorted list of keys.

    One may supply keyword parameters to be passed to the sort function used
    to sort keys (i.e. key, reverse) as sort_params.

    Create a map that maps 1-3 -> 'a', 4-6 -> 'b'

    >>> r = RangeMap({3: 'a', 6: 'b'})  # boy, that was easy
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    Even float values should work so long as the comparison operator
    supports it.

    >>> r[4.5]
    'b'

    Notice that the way rangemap is defined, it must be open-ended
    on one side.

    >>> r[0]
    'a'
    >>> r[-1]
    'a'

    One can close the open-end of the RangeMap by using undefined_value

    >>> r = RangeMap({0: RangeMap.undefined_value, 3: 'a', 6: 'b'})
    >>> r[0]
    Traceback (most recent call last):
    ...
    KeyError: 0

    One can get the first or last elements in the range by using RangeMap.Item

    >>> last_item = RangeMap.Item(-1)
    >>> r[last_item]
    'b'

    .last_item is a shortcut for Item(-1)

    >>> r[RangeMap.last_item]
    'b'

    Sometimes it's useful to find the bounds for a RangeMap

    >>> r.bounds()
    (0, 6)

    RangeMap supports .get(key, default)

    >>> r.get(0, 'not found')
    'not found'

    >>> r.get(7, 'not found')
    'not found'

    One often wishes to define the ranges by their left-most values,
    which requires use of sort params and a key_match_comparator.

    >>> r = RangeMap({1: 'a', 4: 'b'},
    ...     sort_params=dict(reverse=True),
    ...     key_match_comparator=operator.ge)
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    That wasn't nearly as easy as before, so an alternate constructor
    is provided:

    >>> r = RangeMap.left({1: 'a', 4: 'b', 7: RangeMap.undefined_value})
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    """

    def __init__(
        self,
        source: (
            SupportsKeysAndGetItem[_RangeMapKT, _VT] | Iterable[tuple[_RangeMapKT, _VT]]
        ),
        sort_params: Mapping[str, Any] = {},
        key_match_comparator: Callable[[_RangeMapKT, _RangeMapKT], bool] = operator.le,
    ):
        dict.__init__(self, source)
        self.sort_params = sort_params
        self.match = key_match_comparator

    @classmethod
    def left(
        cls,
        source: (
            SupportsKeysAndGetItem[_RangeMapKT, _VT] | Iterable[tuple[_RangeMapKT, _VT]]
        ),
    ) -> Self:
        return cls(
            source, sort_params=dict(reverse=True), key_match_comparator=operator.ge
        )

    def __getitem__(self, item: _RangeMapKT) -> _VT:
        sorted_keys = sorted(self.keys(), **self.sort_params)
        if isinstance(item, RangeMap.Item):
            result = self.__getitem__(sorted_keys[item])
        else:
            key = self._find_first_match_(sorted_keys, item)
            result = dict.__getitem__(self, key)
            if result is RangeMap.undefined_value:
                raise KeyError(key)
        return result

    @overload  # type: ignore[override] # Signature simplified over dict and Mapping
    def get(self, key: _RangeMapKT, default: _T) -> _VT | _T: ...
    @overload
    def get(self, key: _RangeMapKT, default: None = None) -> _VT | None: ...
    def get(self, key: _RangeMapKT, default: _T | None = None) -> _VT | _T | None:
        """
        Return the value for key if key is in the dictionary, else default.
        If default is not given, it defaults to None, so that this method
        never raises a KeyError.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def _find_first_match_(
        self, keys: Iterable[_RangeMapKT], item: _RangeMapKT
    ) -> _RangeMapKT:
        is_match = functools.partial(self.match, item)
        matches = filter(is_match, keys)
        try:
            return next(matches)
        except StopIteration:
            raise KeyError(item) from None

    def bounds(self) -> tuple[_RangeMapKT, _RangeMapKT]:
        sorted_keys = sorted(self.keys(), **self.sort_params)
        return (sorted_keys[RangeMap.first_item], sorted_keys[RangeMap.last_item])

    # some special values for the RangeMap
    undefined_value = type('RangeValueUndefined', (), {})()

    class Item(int):
        """RangeMap Item"""

    first_item = Item(0)
    last_item = Item(-1)


def __identity(x):
    return x


def sorted_items(d, key=__identity, reverse=False):
    """
    Return the items of the dictionary sorted by the keys.

    >>> sample = dict(foo=20, bar=42, baz=10)
    >>> tuple(sorted_items(sample))
    (('bar', 42), ('baz', 10), ('foo', 20))

    >>> reverse_string = lambda s: ''.join(reversed(s))
    >>> tuple(sorted_items(sample, key=reverse_string))
    (('foo', 20), ('bar', 42), ('baz', 10))

    >>> tuple(sorted_items(sample, reverse=True))
    (('foo', 20), ('baz', 10), ('bar', 42))
    """

    # wrap the key func so it operates on the first element of each item
    def pairkey_key(item):
        return key(item[0])

    return sorted(d.items(), key=pairkey_key, reverse=reverse)


class KeyTransformingDict(dict):
    """
    A dict subclass that transforms the keys before they're used.
    Subclasses may override the default transform_key to customize behavior.
    """

    @staticmethod
    def transform_key(key):  # pragma: nocover
        return key

    def __init__(self, *args, **kargs):
        super().__init__()
        # build a dictionary using the default constructs
        d = dict(*args, **kargs)
        # build this dictionary using transformed keys.
        for item in d.items():
            self.__setitem__(*item)

    def __setitem__(self, key, val):
        key = self.transform_key(key)
        super().__setitem__(key, val)

    def __getitem__(self, key):
        key = self.transform_key(key)
        return super().__getitem__(key)

    def __contains__(self, key):
        key = self.transform_key(key)
        return super().__contains__(key)

    def __delitem__(self, key):
        key = self.transform_key(key)
        return super().__delitem__(key)

    def get(self, key, *args, **kwargs):
        key = self.transform_key(key)
        return super().get(key, *args, **kwargs)

    def setdefault(self, key, *args, **kwargs):
        key = self.transform_key(key)
        return super().setdefault(key, *args, **kwargs)

    def pop(self, key, *args, **kwargs):
        key = self.transform_key(key)
        return super().pop(key, *args, **kwargs)

    def matching_key_for(self, key):
        """
        Given a key, return the actual key stored in self that matches.
        Raise KeyError if the key isn't found.
        """
        try:
            return next(e_key for e_key in self.keys() if e_key == key)
        except StopIteration as err:
            raise KeyError(key) from err


class FoldedCaseKeyedDict(KeyTransformingDict):
    """
    A case-insensitive dictionary (keys are compared as insensitive
    if they are strings).

    >>> d = FoldedCaseKeyedDict()
    >>> d['heLlo'] = 'world'
    >>> list(d.keys()) == ['heLlo']
    True
    >>> list(d.values()) == ['world']
    True
    >>> d['hello'] == 'world'
    True
    >>> 'hello' in d
    True
    >>> 'HELLO' in d
    True
    >>> print(repr(FoldedCaseKeyedDict({'heLlo': 'world'})))
    {'heLlo': 'world'}
    >>> d = FoldedCaseKeyedDict({'heLlo': 'world'})
    >>> print(d['hello'])
    world
    >>> print(d['Hello'])
    world
    >>> list(d.keys())
    ['heLlo']
    >>> d = FoldedCaseKeyedDict({'heLlo': 'world', 'Hello': 'world'})
    >>> list(d.values())
    ['world']
    >>> key, = d.keys()
    >>> key in ['heLlo', 'Hello']
    True
    >>> del d['HELLO']
    >>> d
    {}

    get should work

    >>> d['Sumthin'] = 'else'
    >>> d.get('SUMTHIN')
    'else'
    >>> d.get('OTHER', 'thing')
    'thing'
    >>> del d['sumthin']

    setdefault should also work

    >>> d['This'] = 'that'
    >>> print(d.setdefault('this', 'other'))
    that
    >>> len(d)
    1
    >>> print(d['this'])
    that
    >>> print(d.setdefault('That', 'other'))
    other
    >>> print(d['THAT'])
    other

    Make it pop!

    >>> print(d.pop('THAT'))
    other

    To retrieve the key in its originally-supplied form, use matching_key_for

    >>> print(d.matching_key_for('this'))
    This

    >>> d.matching_key_for('missing')
    Traceback (most recent call last):
    ...
    KeyError: 'missing'
    """

    @staticmethod
    def transform_key(key):
        return jaraco.text.FoldedCase(key)


class DictAdapter:
    """
    Provide a getitem interface for attributes of an object.

    Let's say you want to get at the string.lowercase property in a formatted
    string. It's easy with DictAdapter.

    >>> import string
    >>> print("lowercase is %(ascii_lowercase)s" % DictAdapter(string))
    lowercase is abcdefghijklmnopqrstuvwxyz
    """

    def __init__(self, wrapped_ob):
        self.object = wrapped_ob

    def __getitem__(self, name):
        return getattr(self.object, name)


class ItemsAsAttributes:
    """
    Mix-in class to enable a mapping object to provide items as
    attributes.

    >>> C = type('C', (dict, ItemsAsAttributes), dict())
    >>> i = C()
    >>> i['foo'] = 'bar'
    >>> i.foo
    'bar'

    Natural attribute access takes precedence

    >>> i.foo = 'henry'
    >>> i.foo
    'henry'

    But as you might expect, the mapping functionality is preserved.

    >>> i['foo']
    'bar'

    A normal attribute error should be raised if an attribute is
    requested that doesn't exist.

    >>> i.missing
    Traceback (most recent call last):
    ...
    AttributeError: 'C' object has no attribute 'missing'

    It also works on dicts that customize __getitem__

    >>> missing_func = lambda self, key: 'missing item'
    >>> C = type(
    ...     'C',
    ...     (dict, ItemsAsAttributes),
    ...     dict(__missing__ = missing_func),
    ... )
    >>> i = C()
    >>> i.missing
    'missing item'
    >>> i.foo
    'missing item'
    """

    def __getattr__(self, key):
        try:
            return getattr(super(), key)
        except AttributeError as e:
            # attempt to get the value from the mapping (return self[key])
            #  but be careful not to lose the original exception context.
            noval = object()

            def _safe_getitem(cont, key, missing_result):
                try:
                    return cont[key]
                except KeyError:
                    return missing_result

            result = _safe_getitem(self, key, noval)
            if result is not noval:
                return result
            # raise the original exception, but use the original class
            #  name, not 'super'.
            (message,) = e.args
            message = message.replace('super', self.__class__.__name__, 1)
            e.args = (message,)
            raise


def invert_map(map):
    """
    Given a dictionary, return another dictionary with keys and values
    switched. If any of the values resolve to the same key, raises
    a ValueError.

    >>> numbers = dict(a=1, b=2, c=3)
    >>> letters = invert_map(numbers)
    >>> letters[1]
    'a'
    >>> numbers['d'] = 3
    >>> invert_map(numbers)
    Traceback (most recent call last):
    ...
    ValueError: Key conflict in inverted mapping
    """
    res = dict((v, k) for k, v in map.items())
    if not len(res) == len(map):
        raise ValueError('Key conflict in inverted mapping')
    return res


class IdentityOverrideMap(dict):
    """
    A dictionary that by default maps each key to itself, but otherwise
    acts like a normal dictionary.

    >>> d = IdentityOverrideMap()
    >>> d[42]
    42
    >>> d['speed'] = 'speedo'
    >>> print(d['speed'])
    speedo
    """

    def __missing__(self, key):
        return key


class DictStack(list, collections.abc.MutableMapping):
    """
    A stack of dictionaries that behaves as a view on those dictionaries,
    giving preference to the last.

    >>> stack = DictStack([dict(a=1, c=2), dict(b=2, a=2)])
    >>> stack['a']
    2
    >>> stack['b']
    2
    >>> stack['c']
    2
    >>> len(stack)
    3
    >>> stack.push(dict(a=3))
    >>> stack['a']
    3
    >>> stack['a'] = 4
    >>> set(stack.keys()) == set(['a', 'b', 'c'])
    True
    >>> set(stack.items()) == set([('a', 4), ('b', 2), ('c', 2)])
    True
    >>> dict(**stack) == dict(stack) == dict(a=4, c=2, b=2)
    True
    >>> d = stack.pop()
    >>> stack['a']
    2
    >>> d = stack.pop()
    >>> stack['a']
    1
    >>> stack.get('b', None)
    >>> 'c' in stack
    True
    >>> del stack['c']
    >>> dict(stack)
    {'a': 1}
    """

    def __iter__(self):
        dicts = list.__iter__(self)
        return iter(set(itertools.chain.from_iterable(c.keys() for c in dicts)))

    def __getitem__(self, key):
        for scope in reversed(tuple(list.__iter__(self))):
            if key in scope:
                return scope[key]
        raise KeyError(key)

    push = list.append

    def __contains__(self, other):
        return collections.abc.Mapping.__contains__(self, other)

    def __len__(self):
        return len(list(iter(self)))

    def __setitem__(self, key, item):
        last = list.__getitem__(self, -1)
        return last.__setitem__(key, item)

    def __delitem__(self, key):
        last = list.__getitem__(self, -1)
        return last.__delitem__(key)

    # workaround for mypy confusion
    def pop(self, *args, **kwargs):
        return list.pop(self, *args, **kwargs)


class BijectiveMap(dict):
    """
    A Bijective Map (two-way mapping).

    Implemented as a simple dictionary of 2x the size, mapping values back
    to keys.

    Note, this implementation may be incomplete. If there's not a test for
    your use case below, it's likely to fail, so please test and send pull
    requests or patches for additional functionality needed.


    >>> m = BijectiveMap()
    >>> m['a'] = 'b'
    >>> m == {'a': 'b', 'b': 'a'}
    True
    >>> print(m['b'])
    a

    >>> m['c'] = 'd'
    >>> len(m)
    2

    Some weird things happen if you map an item to itself or overwrite a
    single key of a pair, so it's disallowed.

    >>> m['e'] = 'e'
    Traceback (most recent call last):
    ValueError: Key cannot map to itself

    >>> m['d'] = 'e'
    Traceback (most recent call last):
    ValueError: Key/Value pairs may not overlap

    >>> m['e'] = 'd'
    Traceback (most recent call last):
    ValueError: Key/Value pairs may not overlap

    >>> print(m.pop('d'))
    c

    >>> 'c' in m
    False

    >>> m = BijectiveMap(dict(a='b'))
    >>> len(m)
    1
    >>> print(m['b'])
    a

    >>> m = BijectiveMap()
    >>> m.update(a='b')
    >>> m['b']
    'a'

    >>> del m['b']
    >>> len(m)
    0
    >>> 'a' in m
    False
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.update(*args, **kwargs)

    def __setitem__(self, item, value):
        if item == value:
            raise ValueError("Key cannot map to itself")
        overlap = (
            item in self
            and self[item] != value
            or value in self
            and self[value] != item
        )
        if overlap:
            raise ValueError("Key/Value pairs may not overlap")
        super().__setitem__(item, value)
        super().__setitem__(value, item)

    def __delitem__(self, item):
        self.pop(item)

    def __len__(self):
        return super().__len__() // 2

    def pop(self, key, *args, **kwargs):
        mirror = self[key]
        super().__delitem__(mirror)
        return super().pop(key, *args, **kwargs)

    def update(self, *args, **kwargs):
        # build a dictionary using the default constructs
        d = dict(*args, **kwargs)
        # build this dictionary using transformed keys.
        for item in d.items():
            self.__setitem__(*item)


class FrozenDict(collections.abc.Mapping, collections.abc.Hashable):
    """
    An immutable mapping.

    >>> a = FrozenDict(a=1, b=2)
    >>> b = FrozenDict(a=1, b=2)
    >>> a == b
    True

    >>> a == dict(a=1, b=2)
    True
    >>> dict(a=1, b=2) == a
    True
    >>> 'a' in a
    True
    >>> type(hash(a)) is type(0)
    True
    >>> set(iter(a)) == {'a', 'b'}
    True
    >>> len(a)
    2
    >>> a['a'] == a.get('a') == 1
    True

    >>> a['c'] = 3
    Traceback (most recent call last):
    ...
    TypeError: 'FrozenDict' object does not support item assignment

    >>> a.update(y=3)
    Traceback (most recent call last):
    ...
    AttributeError: 'FrozenDict' object has no attribute 'update'

    Copies should compare equal

    >>> copy.copy(a) == a
    True

    Copies should be the same type

    >>> isinstance(copy.copy(a), FrozenDict)
    True

    FrozenDict supplies .copy(), even though
    collections.abc.Mapping doesn't demand it.

    >>> a.copy() == a
    True
    >>> a.copy() is not a
    True
    """

    __slots__ = ['__data']

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self.__data = dict(*args, **kwargs)
        return self

    # Container
    def __contains__(self, key):
        return key in self.__data

    # Hashable
    def __hash__(self):
        return hash(tuple(sorted(self.__data.items())))

    # Mapping
    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    def __getitem__(self, key):
        return self.__data[key]

    # override get for efficiency provided by dict
    def get(self, *args, **kwargs):
        return self.__data.get(*args, **kwargs)

    # override eq to recognize underlying implementation
    def __eq__(self, other):
        if isinstance(other, FrozenDict):
            other = other.__data
        return self.__data.__eq__(other)

    def copy(self):
        "Return a shallow copy of self"
        return copy.copy(self)


class Enumeration(ItemsAsAttributes, BijectiveMap):
    """
    A convenient way to provide enumerated values

    >>> e = Enumeration('a b c')
    >>> e['a']
    0

    >>> e.a
    0

    >>> e[1]
    'b'

    >>> set(e.names) == set('abc')
    True

    >>> set(e.codes) == set(range(3))
    True

    >>> e.get('d') is None
    True

    Codes need not start with 0

    >>> e = Enumeration('a b c', range(1, 4))
    >>> e['a']
    1

    >>> e[3]
    'c'
    """

    def __init__(self, names, codes=None):
        if isinstance(names, str):
            names = names.split()
        if codes is None:
            codes = itertools.count()
        super().__init__(zip(names, codes))

    @property
    def names(self):
        return (key for key in self if isinstance(key, str))

    @property
    def codes(self):
        return (self[name] for name in self.names)


class Everything:
    """
    A collection "containing" every possible thing.

    >>> 'foo' in Everything()
    True

    >>> import random
    >>> random.randint(1, 999) in Everything()
    True

    >>> random.choice([None, 'foo', 42, ('a', 'b', 'c')]) in Everything()
    True
    """

    def __contains__(self, other):
        return True


class InstrumentedDict(collections.UserDict):
    """
    Instrument an existing dictionary with additional
    functionality, but always reference and mutate
    the original dictionary.

    >>> orig = {'a': 1, 'b': 2}
    >>> inst = InstrumentedDict(orig)
    >>> inst['a']
    1
    >>> inst['c'] = 3
    >>> orig['c']
    3
    >>> inst.keys() == orig.keys()
    True
    """

    def __init__(self, data):
        super().__init__()
        self.data = data


class Least:
    """
    A value that is always lesser than any other

    >>> least = Least()
    >>> 3 < least
    False
    >>> 3 > least
    True
    >>> least < 3
    True
    >>> least <= 3
    True
    >>> least > 3
    False
    >>> 'x' > least
    True
    >>> None > least
    True
    """

    def __le__(self, other):
        return True

    __lt__ = __le__

    def __ge__(self, other):
        return False

    __gt__ = __ge__


class Greatest:
    """
    A value that is always greater than any other

    >>> greatest = Greatest()
    >>> 3 < greatest
    True
    >>> 3 > greatest
    False
    >>> greatest < 3
    False
    >>> greatest > 3
    True
    >>> greatest >= 3
    True
    >>> 'x' > greatest
    False
    >>> None > greatest
    False
    """

    def __ge__(self, other):
        return True

    __gt__ = __ge__

    def __le__(self, other):
        return False

    __lt__ = __le__


def pop_all(items):
    """
    Clear items in place and return a copy of items.

    >>> items = [1, 2, 3]
    >>> popped = pop_all(items)
    >>> popped is items
    False
    >>> popped
    [1, 2, 3]
    >>> items
    []
    """
    result, items[:] = items[:], []
    return result


class FreezableDefaultDict(collections.defaultdict):
    """
    Often it is desirable to prevent the mutation of
    a default dict after its initial construction, such
    as to prevent mutation during iteration.

    >>> dd = FreezableDefaultDict(list)
    >>> dd[0].append('1')
    >>> dd.freeze()
    >>> dd[1]
    []
    >>> len(dd)
    1
    """

    def __missing__(self, key):
        return getattr(self, '_frozen', super().__missing__)(key)

    def freeze(self):
        self._frozen = lambda key: self.default_factory()


class Accumulator:
    def __init__(self, initial=0):
        self.val = initial

    def __call__(self, val):
        self.val += val
        return self.val


class WeightedLookup(RangeMap):
    """
    Given parameters suitable for a dict representing keys
    and a weighted proportion, return a RangeMap representing
    spans of values proportial to the weights:

    >>> even = WeightedLookup(a=1, b=1)

    [0, 1) -> a
    [1, 2) -> b

    >>> lk = WeightedLookup(a=1, b=2)

    [0, 1) -> a
    [1, 3) -> b

    >>> lk[.5]
    'a'
    >>> lk[1.5]
    'b'

    Adds ``.random()`` to select a random weighted value:

    >>> lk.random() in ['a', 'b']
    True

    >>> choices = [lk.random() for x in range(1000)]

    Statistically speaking, choices should be .5 a:b
    >>> ratio = choices.count('a') / choices.count('b')
    >>> .4 < ratio < .6
    True
    """

    def __init__(self, *args, **kwargs):
        raw = dict(*args, **kwargs)

        # allocate keys by weight
        indexes = map(Accumulator(), raw.values())
        super().__init__(zip(indexes, raw.keys()), key_match_comparator=operator.lt)

    def random(self):
        lower, upper = self.bounds()
        selector = random.random() * upper
        return self[selector]