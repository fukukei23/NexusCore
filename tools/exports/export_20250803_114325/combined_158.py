
# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\command\bdist_rpm.py ===
"""distutils.command.bdist_rpm

Implements the Distutils 'bdist_rpm' command (create RPM source and binary
distributions)."""

import os
import subprocess
import sys
from distutils._log import log
from typing import ClassVar

from ..core import Command
from ..debug import DEBUG
from ..errors import (
    DistutilsExecError,
    DistutilsFileError,
    DistutilsOptionError,
    DistutilsPlatformError,
)
from ..file_util import write_file
from ..sysconfig import get_python_version


class bdist_rpm(Command):
    description = "create an RPM distribution"

    user_options = [
        ('bdist-base=', None, "base directory for creating built distributions"),
        (
            'rpm-base=',
            None,
            "base directory for creating RPMs (defaults to \"rpm\" under "
            "--bdist-base; must be specified for RPM 2)",
        ),
        (
            'dist-dir=',
            'd',
            "directory to put final RPM files in (and .spec files if --spec-only)",
        ),
        (
            'python=',
            None,
            "path to Python interpreter to hard-code in the .spec file "
            "[default: \"python\"]",
        ),
        (
            'fix-python',
            None,
            "hard-code the exact path to the current Python interpreter in "
            "the .spec file",
        ),
        ('spec-only', None, "only regenerate spec file"),
        ('source-only', None, "only generate source RPM"),
        ('binary-only', None, "only generate binary RPM"),
        ('use-bzip2', None, "use bzip2 instead of gzip to create source distribution"),
        # More meta-data: too RPM-specific to put in the setup script,
        # but needs to go in the .spec file -- so we make these options
        # to "bdist_rpm".  The idea is that packagers would put this
        # info in setup.cfg, although they are of course free to
        # supply it on the command line.
        (
            'distribution-name=',
            None,
            "name of the (Linux) distribution to which this "
            "RPM applies (*not* the name of the module distribution!)",
        ),
        ('group=', None, "package classification [default: \"Development/Libraries\"]"),
        ('release=', None, "RPM release number"),
        ('serial=', None, "RPM serial number"),
        (
            'vendor=',
            None,
            "RPM \"vendor\" (eg. \"Joe Blow <joe@example.com>\") "
            "[default: maintainer or author from setup script]",
        ),
        (
            'packager=',
            None,
            "RPM packager (eg. \"Jane Doe <jane@example.net>\") [default: vendor]",
        ),
        ('doc-files=', None, "list of documentation files (space or comma-separated)"),
        ('changelog=', None, "RPM changelog"),
        ('icon=', None, "name of icon file"),
        ('provides=', None, "capabilities provided by this package"),
        ('requires=', None, "capabilities required by this package"),
        ('conflicts=', None, "capabilities which conflict with this package"),
        ('build-requires=', None, "capabilities required to build this package"),
        ('obsoletes=', None, "capabilities made obsolete by this package"),
        ('no-autoreq', None, "do not automatically calculate dependencies"),
        # Actions to take when building RPM
        ('keep-temp', 'k', "don't clean up RPM build directory"),
        ('no-keep-temp', None, "clean up RPM build directory [default]"),
        (
            'use-rpm-opt-flags',
            None,
            "compile with RPM_OPT_FLAGS when building from source RPM",
        ),
        ('no-rpm-opt-flags', None, "do not pass any RPM CFLAGS to compiler"),
        ('rpm3-mode', None, "RPM 3 compatibility mode (default)"),
        ('rpm2-mode', None, "RPM 2 compatibility mode"),
        # Add the hooks necessary for specifying custom scripts
        ('prep-script=', None, "Specify a script for the PREP phase of RPM building"),
        ('build-script=', None, "Specify a script for the BUILD phase of RPM building"),
        (
            'pre-install=',
            None,
            "Specify a script for the pre-INSTALL phase of RPM building",
        ),
        (
            'install-script=',
            None,
            "Specify a script for the INSTALL phase of RPM building",
        ),
        (
            'post-install=',
            None,
            "Specify a script for the post-INSTALL phase of RPM building",
        ),
        (
            'pre-uninstall=',
            None,
            "Specify a script for the pre-UNINSTALL phase of RPM building",
        ),
        (
            'post-uninstall=',
            None,
            "Specify a script for the post-UNINSTALL phase of RPM building",
        ),
        ('clean-script=', None, "Specify a script for the CLEAN phase of RPM building"),
        (
            'verify-script=',
            None,
            "Specify a script for the VERIFY phase of the RPM build",
        ),
        # Allow a packager to explicitly force an architecture
        ('force-arch=', None, "Force an architecture onto the RPM build process"),
        ('quiet', 'q', "Run the INSTALL phase of RPM building in quiet mode"),
    ]

    boolean_options: ClassVar[list[str]] = [
        'keep-temp',
        'use-rpm-opt-flags',
        'rpm3-mode',
        'no-autoreq',
        'quiet',
    ]

    negative_opt: ClassVar[dict[str, str]] = {
        'no-keep-temp': 'keep-temp',
        'no-rpm-opt-flags': 'use-rpm-opt-flags',
        'rpm2-mode': 'rpm3-mode',
    }

    def initialize_options(self):
        self.bdist_base = None
        self.rpm_base = None
        self.dist_dir = None
        self.python = None
        self.fix_python = None
        self.spec_only = None
        self.binary_only = None
        self.source_only = None
        self.use_bzip2 = None

        self.distribution_name = None
        self.group = None
        self.release = None
        self.serial = None
        self.vendor = None
        self.packager = None
        self.doc_files = None
        self.changelog = None
        self.icon = None

        self.prep_script = None
        self.build_script = None
        self.install_script = None
        self.clean_script = None
        self.verify_script = None
        self.pre_install = None
        self.post_install = None
        self.pre_uninstall = None
        self.post_uninstall = None
        self.prep = None
        self.provides = None
        self.requires = None
        self.conflicts = None
        self.build_requires = None
        self.obsoletes = None

        self.keep_temp = False
        self.use_rpm_opt_flags = True
        self.rpm3_mode = True
        self.no_autoreq = False

        self.force_arch = None
        self.quiet = False

    def finalize_options(self) -> None:
        self.set_undefined_options('bdist', ('bdist_base', 'bdist_base'))
        if self.rpm_base is None:
            if not self.rpm3_mode:
                raise DistutilsOptionError("you must specify --rpm-base in RPM 2 mode")
            self.rpm_base = os.path.join(self.bdist_base, "rpm")

        if self.python is None:
            if self.fix_python:
                self.python = sys.executable
            else:
                self.python = "python3"
        elif self.fix_python:
            raise DistutilsOptionError(
                "--python and --fix-python are mutually exclusive options"
            )

        if os.name != 'posix':
            raise DistutilsPlatformError(
                f"don't know how to create RPM distributions on platform {os.name}"
            )
        if self.binary_only and self.source_only:
            raise DistutilsOptionError(
                "cannot supply both '--source-only' and '--binary-only'"
            )

        # don't pass CFLAGS to pure python distributions
        if not self.distribution.has_ext_modules():
            self.use_rpm_opt_flags = False

        self.set_undefined_options('bdist', ('dist_dir', 'dist_dir'))
        self.finalize_package_data()

    def finalize_package_data(self) -> None:
        self.ensure_string('group', "Development/Libraries")
        self.ensure_string(
            'vendor',
            f"{self.distribution.get_contact()} <{self.distribution.get_contact_email()}>",
        )
        self.ensure_string('packager')
        self.ensure_string_list('doc_files')
        if isinstance(self.doc_files, list):
            for readme in ('README', 'README.txt'):
                if os.path.exists(readme) and readme not in self.doc_files:
                    self.doc_files.append(readme)

        self.ensure_string('release', "1")
        self.ensure_string('serial')  # should it be an int?

        self.ensure_string('distribution_name')

        self.ensure_string('changelog')
        # Format changelog correctly
        self.changelog = self._format_changelog(self.changelog)

        self.ensure_filename('icon')

        self.ensure_filename('prep_script')
        self.ensure_filename('build_script')
        self.ensure_filename('install_script')
        self.ensure_filename('clean_script')
        self.ensure_filename('verify_script')
        self.ensure_filename('pre_install')
        self.ensure_filename('post_install')
        self.ensure_filename('pre_uninstall')
        self.ensure_filename('post_uninstall')

        # XXX don't forget we punted on summaries and descriptions -- they
        # should be handled here eventually!

        # Now *this* is some meta-data that belongs in the setup script...
        self.ensure_string_list('provides')
        self.ensure_string_list('requires')
        self.ensure_string_list('conflicts')
        self.ensure_string_list('build_requires')
        self.ensure_string_list('obsoletes')

        self.ensure_string('force_arch')

    def run(self) -> None:  # noqa: C901
        if DEBUG:
            print("before _get_package_data():")
            print("vendor =", self.vendor)
            print("packager =", self.packager)
            print("doc_files =", self.doc_files)
            print("changelog =", self.changelog)

        # make directories
        if self.spec_only:
            spec_dir = self.dist_dir
            self.mkpath(spec_dir)
        else:
            rpm_dir = {}
            for d in ('SOURCES', 'SPECS', 'BUILD', 'RPMS', 'SRPMS'):
                rpm_dir[d] = os.path.join(self.rpm_base, d)
                self.mkpath(rpm_dir[d])
            spec_dir = rpm_dir['SPECS']

        # Spec file goes into 'dist_dir' if '--spec-only specified',
        # build/rpm.<plat> otherwise.
        spec_path = os.path.join(spec_dir, f"{self.distribution.get_name()}.spec")
        self.execute(
            write_file, (spec_path, self._make_spec_file()), f"writing '{spec_path}'"
        )

        if self.spec_only:  # stop if requested
            return

        # Make a source distribution and copy to SOURCES directory with
        # optional icon.
        saved_dist_files = self.distribution.dist_files[:]
        sdist = self.reinitialize_command('sdist')
        if self.use_bzip2:
            sdist.formats = ['bztar']
        else:
            sdist.formats = ['gztar']
        self.run_command('sdist')
        self.distribution.dist_files = saved_dist_files

        source = sdist.get_archive_files()[0]
        source_dir = rpm_dir['SOURCES']
        self.copy_file(source, source_dir)

        if self.icon:
            if os.path.exists(self.icon):
                self.copy_file(self.icon, source_dir)
            else:
                raise DistutilsFileError(f"icon file '{self.icon}' does not exist")

        # build package
        log.info("building RPMs")
        rpm_cmd = ['rpmbuild']

        if self.source_only:  # what kind of RPMs?
            rpm_cmd.append('-bs')
        elif self.binary_only:
            rpm_cmd.append('-bb')
        else:
            rpm_cmd.append('-ba')
        rpm_cmd.extend(['--define', f'__python {self.python}'])
        if self.rpm3_mode:
            rpm_cmd.extend(['--define', f'_topdir {os.path.abspath(self.rpm_base)}'])
        if not self.keep_temp:
            rpm_cmd.append('--clean')

        if self.quiet:
            rpm_cmd.append('--quiet')

        rpm_cmd.append(spec_path)
        # Determine the binary rpm names that should be built out of this spec
        # file
        # Note that some of these may not be really built (if the file
        # list is empty)
        nvr_string = "%{name}-%{version}-%{release}"
        src_rpm = nvr_string + ".src.rpm"
        non_src_rpm = "%{arch}/" + nvr_string + ".%{arch}.rpm"
        q_cmd = rf"rpm -q --qf '{src_rpm} {non_src_rpm}\n' --specfile '{spec_path}'"

        out = os.popen(q_cmd)
        try:
            binary_rpms = []
            source_rpm = None
            while True:
                line = out.readline()
                if not line:
                    break
                ell = line.strip().split()
                assert len(ell) == 2
                binary_rpms.append(ell[1])
                # The source rpm is named after the first entry in the spec file
                if source_rpm is None:
                    source_rpm = ell[0]

            status = out.close()
            if status:
                raise DistutilsExecError(f"Failed to execute: {q_cmd!r}")

        finally:
            out.close()

        self.spawn(rpm_cmd)

        if not self.dry_run:
            if self.distribution.has_ext_modules():
                pyversion = get_python_version()
            else:
                pyversion = 'any'

            if not self.binary_only:
                srpm = os.path.join(rpm_dir['SRPMS'], source_rpm)
                assert os.path.exists(srpm)
                self.move_file(srpm, self.dist_dir)
                filename = os.path.join(self.dist_dir, source_rpm)
                self.distribution.dist_files.append(('bdist_rpm', pyversion, filename))

            if not self.source_only:
                for rpm in binary_rpms:
                    rpm = os.path.join(rpm_dir['RPMS'], rpm)
                    if os.path.exists(rpm):
                        self.move_file(rpm, self.dist_dir)
                        filename = os.path.join(self.dist_dir, os.path.basename(rpm))
                        self.distribution.dist_files.append((
                            'bdist_rpm',
                            pyversion,
                            filename,
                        ))

    def _dist_path(self, path):
        return os.path.join(self.dist_dir, os.path.basename(path))

    def _make_spec_file(self):  # noqa: C901
        """Generate the text of an RPM spec file and return it as a
        list of strings (one per line).
        """
        # definitions and headers
        spec_file = [
            '%define name ' + self.distribution.get_name(),
            '%define version ' + self.distribution.get_version().replace('-', '_'),
            '%define unmangled_version ' + self.distribution.get_version(),
            '%define release ' + self.release.replace('-', '_'),
            '',
            'Summary: ' + (self.distribution.get_description() or "UNKNOWN"),
        ]

        # Workaround for #14443 which affects some RPM based systems such as
        # RHEL6 (and probably derivatives)
        vendor_hook = subprocess.getoutput('rpm --eval %{__os_install_post}')
        # Generate a potential replacement value for __os_install_post (whilst
        # normalizing the whitespace to simplify the test for whether the
        # invocation of brp-python-bytecompile passes in __python):
        vendor_hook = '\n'.join([
            f'  {line.strip()} \\' for line in vendor_hook.splitlines()
        ])
        problem = "brp-python-bytecompile \\\n"
        fixed = "brp-python-bytecompile %{__python} \\\n"
        fixed_hook = vendor_hook.replace(problem, fixed)
        if fixed_hook != vendor_hook:
            spec_file.append('# Workaround for https://bugs.python.org/issue14443')
            spec_file.append('%define __os_install_post ' + fixed_hook + '\n')

        # put locale summaries into spec file
        # XXX not supported for now (hard to put a dictionary
        # in a config file -- arg!)
        # for locale in self.summaries.keys():
        #    spec_file.append('Summary(%s): %s' % (locale,
        #                                          self.summaries[locale]))

        spec_file.extend([
            'Name: %{name}',
            'Version: %{version}',
            'Release: %{release}',
        ])

        # XXX yuck! this filename is available from the "sdist" command,
        # but only after it has run: and we create the spec file before
        # running "sdist", in case of --spec-only.
        if self.use_bzip2:
            spec_file.append('Source0: %{name}-%{unmangled_version}.tar.bz2')
        else:
            spec_file.append('Source0: %{name}-%{unmangled_version}.tar.gz')

        spec_file.extend([
            'License: ' + (self.distribution.get_license() or "UNKNOWN"),
            'Group: ' + self.group,
            'BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot',
            'Prefix: %{_prefix}',
        ])

        if not self.force_arch:
            # noarch if no extension modules
            if not self.distribution.has_ext_modules():
                spec_file.append('BuildArch: noarch')
        else:
            spec_file.append(f'BuildArch: {self.force_arch}')

        for field in (
            'Vendor',
            'Packager',
            'Provides',
            'Requires',
            'Conflicts',
            'Obsoletes',
        ):
            val = getattr(self, field.lower())
            if isinstance(val, list):
                spec_file.append('{}: {}'.format(field, ' '.join(val)))
            elif val is not None:
                spec_file.append(f'{field}: {val}')

        if self.distribution.get_url():
            spec_file.append('Url: ' + self.distribution.get_url())

        if self.distribution_name:
            spec_file.append('Distribution: ' + self.distribution_name)

        if self.build_requires:
            spec_file.append('BuildRequires: ' + ' '.join(self.build_requires))

        if self.icon:
            spec_file.append('Icon: ' + os.path.basename(self.icon))

        if self.no_autoreq:
            spec_file.append('AutoReq: 0')

        spec_file.extend([
            '',
            '%description',
            self.distribution.get_long_description() or "",
        ])

        # put locale descriptions into spec file
        # XXX again, suppressed because config file syntax doesn't
        # easily support this ;-(
        # for locale in self.descriptions.keys():
        #    spec_file.extend([
        #        '',
        #        '%description -l ' + locale,
        #        self.descriptions[locale],
        #        ])

        # rpm scripts
        # figure out default build script
        def_setup_call = f"{self.python} {os.path.basename(sys.argv[0])}"
        def_build = f"{def_setup_call} build"
        if self.use_rpm_opt_flags:
            def_build = 'env CFLAGS="$RPM_OPT_FLAGS" ' + def_build

        # insert contents of files

        # XXX this is kind of misleading: user-supplied options are files
        # that we open and interpolate into the spec file, but the defaults
        # are just text that we drop in as-is.  Hmmm.

        install_cmd = f'{def_setup_call} install -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES'

        script_options = [
            ('prep', 'prep_script', "%setup -n %{name}-%{unmangled_version}"),
            ('build', 'build_script', def_build),
            ('install', 'install_script', install_cmd),
            ('clean', 'clean_script', "rm -rf $RPM_BUILD_ROOT"),
            ('verifyscript', 'verify_script', None),
            ('pre', 'pre_install', None),
            ('post', 'post_install', None),
            ('preun', 'pre_uninstall', None),
            ('postun', 'post_uninstall', None),
        ]

        for rpm_opt, attr, default in script_options:
            # Insert contents of file referred to, if no file is referred to
            # use 'default' as contents of script
            val = getattr(self, attr)
            if val or default:
                spec_file.extend([
                    '',
                    '%' + rpm_opt,
                ])
                if val:
                    with open(val) as f:
                        spec_file.extend(f.read().split('\n'))
                else:
                    spec_file.append(default)

        # files section
        spec_file.extend([
            '',
            '%files -f INSTALLED_FILES',
            '%defattr(-,root,root)',
        ])

        if self.doc_files:
            spec_file.append('%doc ' + ' '.join(self.doc_files))

        if self.changelog:
            spec_file.extend([
                '',
                '%changelog',
            ])
            spec_file.extend(self.changelog)

        return spec_file

    def _format_changelog(self, changelog):
        """Format the changelog correctly and convert it to a list of strings"""
        if not changelog:
            return changelog
        new_changelog = []
        for line in changelog.strip().split('\n'):
            line = line.strip()
            if line[0] == '*':
                new_changelog.extend(['', line])
            elif line[0] == '-':
                new_changelog.append(line)
            else:
                new_changelog.append('  ' + line)

        # strip trailing newline inserted by first changelog entry
        if not new_changelog[0]:
            del new_changelog[0]

        return new_changelog

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\legacy\resolver.py ===
"""Dependency Resolution

The dependency resolution in pip is performed as follows:

for top-level requirements:
    a. only one spec allowed per project, regardless of conflicts or not.
       otherwise a "double requirement" exception is raised
    b. they override sub-dependency requirements.
for sub-dependencies
    a. "first found, wins" (where the order is breadth first)
"""

import logging
import sys
from collections import defaultdict
from itertools import chain
from typing import DefaultDict, Iterable, List, Optional, Set, Tuple

from pip._vendor.packaging import specifiers
from pip._vendor.packaging.requirements import Requirement

from pip._internal.cache import WheelCache
from pip._internal.exceptions import (
    BestVersionAlreadyInstalled,
    DistributionNotFound,
    HashError,
    HashErrors,
    InstallationError,
    NoneMetadataError,
    UnsupportedPythonVersion,
)
from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata import BaseDistribution
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.req_install import (
    InstallRequirement,
    check_invalid_constraint_type,
)
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.base import BaseResolver, InstallRequirementProvider
from pip._internal.utils import compatibility_tags
from pip._internal.utils.compatibility_tags import get_supported
from pip._internal.utils.direct_url_helpers import direct_url_from_link
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import normalize_version_info
from pip._internal.utils.packaging import check_requires_python

logger = logging.getLogger(__name__)

DiscoveredDependencies = DefaultDict[Optional[str], List[InstallRequirement]]


def _check_dist_requires_python(
    dist: BaseDistribution,
    version_info: Tuple[int, int, int],
    ignore_requires_python: bool = False,
) -> None:
    """
    Check whether the given Python version is compatible with a distribution's
    "Requires-Python" value.

    :param version_info: A 3-tuple of ints representing the Python
        major-minor-micro version to check.
    :param ignore_requires_python: Whether to ignore the "Requires-Python"
        value if the given Python version isn't compatible.

    :raises UnsupportedPythonVersion: When the given Python version isn't
        compatible.
    """
    # This idiosyncratically converts the SpecifierSet to str and let
    # check_requires_python then parse it again into SpecifierSet. But this
    # is the legacy resolver so I'm just not going to bother refactoring.
    try:
        requires_python = str(dist.requires_python)
    except FileNotFoundError as e:
        raise NoneMetadataError(dist, str(e))
    try:
        is_compatible = check_requires_python(
            requires_python,
            version_info=version_info,
        )
    except specifiers.InvalidSpecifier as exc:
        logger.warning(
            "Package %r has an invalid Requires-Python: %s", dist.raw_name, exc
        )
        return

    if is_compatible:
        return

    version = ".".join(map(str, version_info))
    if ignore_requires_python:
        logger.debug(
            "Ignoring failed Requires-Python check for package %r: %s not in %r",
            dist.raw_name,
            version,
            requires_python,
        )
        return

    raise UnsupportedPythonVersion(
        f"Package {dist.raw_name!r} requires a different Python: "
        f"{version} not in {requires_python!r}"
    )


class Resolver(BaseResolver):
    """Resolves which packages need to be installed/uninstalled to perform \
    the requested operation without breaking the requirements of any package.
    """

    _allowed_strategies = {"eager", "only-if-needed", "to-satisfy-only"}

    def __init__(
        self,
        preparer: RequirementPreparer,
        finder: PackageFinder,
        wheel_cache: Optional[WheelCache],
        make_install_req: InstallRequirementProvider,
        use_user_site: bool,
        ignore_dependencies: bool,
        ignore_installed: bool,
        ignore_requires_python: bool,
        force_reinstall: bool,
        upgrade_strategy: str,
        py_version_info: Optional[Tuple[int, ...]] = None,
    ) -> None:
        super().__init__()
        assert upgrade_strategy in self._allowed_strategies

        if py_version_info is None:
            py_version_info = sys.version_info[:3]
        else:
            py_version_info = normalize_version_info(py_version_info)

        self._py_version_info = py_version_info

        self.preparer = preparer
        self.finder = finder
        self.wheel_cache = wheel_cache

        self.upgrade_strategy = upgrade_strategy
        self.force_reinstall = force_reinstall
        self.ignore_dependencies = ignore_dependencies
        self.ignore_installed = ignore_installed
        self.ignore_requires_python = ignore_requires_python
        self.use_user_site = use_user_site
        self._make_install_req = make_install_req

        self._discovered_dependencies: DiscoveredDependencies = defaultdict(list)

    def resolve(
        self, root_reqs: List[InstallRequirement], check_supported_wheels: bool
    ) -> RequirementSet:
        """Resolve what operations need to be done

        As a side-effect of this method, the packages (and their dependencies)
        are downloaded, unpacked and prepared for installation. This
        preparation is done by ``pip.operations.prepare``.

        Once PyPI has static dependency metadata available, it would be
        possible to move the preparation to become a step separated from
        dependency resolution.
        """
        requirement_set = RequirementSet(check_supported_wheels=check_supported_wheels)
        for req in root_reqs:
            if req.constraint:
                check_invalid_constraint_type(req)
            self._add_requirement_to_set(requirement_set, req)

        # Actually prepare the files, and collect any exceptions. Most hash
        # exceptions cannot be checked ahead of time, because
        # _populate_link() needs to be called before we can make decisions
        # based on link type.
        discovered_reqs: List[InstallRequirement] = []
        hash_errors = HashErrors()
        for req in chain(requirement_set.all_requirements, discovered_reqs):
            try:
                discovered_reqs.extend(self._resolve_one(requirement_set, req))
            except HashError as exc:
                exc.req = req
                hash_errors.append(exc)

        if hash_errors:
            raise hash_errors

        return requirement_set

    def _add_requirement_to_set(
        self,
        requirement_set: RequirementSet,
        install_req: InstallRequirement,
        parent_req_name: Optional[str] = None,
        extras_requested: Optional[Iterable[str]] = None,
    ) -> Tuple[List[InstallRequirement], Optional[InstallRequirement]]:
        """Add install_req as a requirement to install.

        :param parent_req_name: The name of the requirement that needed this
            added. The name is used because when multiple unnamed requirements
            resolve to the same name, we could otherwise end up with dependency
            links that point outside the Requirements set. parent_req must
            already be added. Note that None implies that this is a user
            supplied requirement, vs an inferred one.
        :param extras_requested: an iterable of extras used to evaluate the
            environment markers.
        :return: Additional requirements to scan. That is either [] if
            the requirement is not applicable, or [install_req] if the
            requirement is applicable and has just been added.
        """
        # If the markers do not match, ignore this requirement.
        if not install_req.match_markers(extras_requested):
            logger.info(
                "Ignoring %s: markers '%s' don't match your environment",
                install_req.name,
                install_req.markers,
            )
            return [], None

        # If the wheel is not supported, raise an error.
        # Should check this after filtering out based on environment markers to
        # allow specifying different wheels based on the environment/OS, in a
        # single requirements file.
        if install_req.link and install_req.link.is_wheel:
            wheel = Wheel(install_req.link.filename)
            tags = compatibility_tags.get_supported()
            if requirement_set.check_supported_wheels and not wheel.supported(tags):
                raise InstallationError(
                    f"{wheel.filename} is not a supported wheel on this platform."
                )

        # This next bit is really a sanity check.
        assert (
            not install_req.user_supplied or parent_req_name is None
        ), "a user supplied req shouldn't have a parent"

        # Unnamed requirements are scanned again and the requirement won't be
        # added as a dependency until after scanning.
        if not install_req.name:
            requirement_set.add_unnamed_requirement(install_req)
            return [install_req], None

        try:
            existing_req: Optional[InstallRequirement] = (
                requirement_set.get_requirement(install_req.name)
            )
        except KeyError:
            existing_req = None

        has_conflicting_requirement = (
            parent_req_name is None
            and existing_req
            and not existing_req.constraint
            and existing_req.extras == install_req.extras
            and existing_req.req
            and install_req.req
            and existing_req.req.specifier != install_req.req.specifier
        )
        if has_conflicting_requirement:
            raise InstallationError(
                f"Double requirement given: {install_req} "
                f"(already in {existing_req}, name={install_req.name!r})"
            )

        # When no existing requirement exists, add the requirement as a
        # dependency and it will be scanned again after.
        if not existing_req:
            requirement_set.add_named_requirement(install_req)
            # We'd want to rescan this requirement later
            return [install_req], install_req

        # Assume there's no need to scan, and that we've already
        # encountered this for scanning.
        if install_req.constraint or not existing_req.constraint:
            return [], existing_req

        does_not_satisfy_constraint = install_req.link and not (
            existing_req.link and install_req.link.path == existing_req.link.path
        )
        if does_not_satisfy_constraint:
            raise InstallationError(
                f"Could not satisfy constraints for '{install_req.name}': "
                "installation from path or url cannot be "
                "constrained to a version"
            )
        # If we're now installing a constraint, mark the existing
        # object for real installation.
        existing_req.constraint = False
        # If we're now installing a user supplied requirement,
        # mark the existing object as such.
        if install_req.user_supplied:
            existing_req.user_supplied = True
        existing_req.extras = tuple(
            sorted(set(existing_req.extras) | set(install_req.extras))
        )
        logger.debug(
            "Setting %s extras to: %s",
            existing_req,
            existing_req.extras,
        )
        # Return the existing requirement for addition to the parent and
        # scanning again.
        return [existing_req], existing_req

    def _is_upgrade_allowed(self, req: InstallRequirement) -> bool:
        if self.upgrade_strategy == "to-satisfy-only":
            return False
        elif self.upgrade_strategy == "eager":
            return True
        else:
            assert self.upgrade_strategy == "only-if-needed"
            return req.user_supplied or req.constraint

    def _set_req_to_reinstall(self, req: InstallRequirement) -> None:
        """
        Set a requirement to be installed.
        """
        # Don't uninstall the conflict if doing a user install and the
        # conflict is not a user install.
        assert req.satisfied_by is not None
        if not self.use_user_site or req.satisfied_by.in_usersite:
            req.should_reinstall = True
        req.satisfied_by = None

    def _check_skip_installed(
        self, req_to_install: InstallRequirement
    ) -> Optional[str]:
        """Check if req_to_install should be skipped.

        This will check if the req is installed, and whether we should upgrade
        or reinstall it, taking into account all the relevant user options.

        After calling this req_to_install will only have satisfied_by set to
        None if the req_to_install is to be upgraded/reinstalled etc. Any
        other value will be a dist recording the current thing installed that
        satisfies the requirement.

        Note that for vcs urls and the like we can't assess skipping in this
        routine - we simply identify that we need to pull the thing down,
        then later on it is pulled down and introspected to assess upgrade/
        reinstalls etc.

        :return: A text reason for why it was skipped, or None.
        """
        if self.ignore_installed:
            return None

        req_to_install.check_if_exists(self.use_user_site)
        if not req_to_install.satisfied_by:
            return None

        if self.force_reinstall:
            self._set_req_to_reinstall(req_to_install)
            return None

        if not self._is_upgrade_allowed(req_to_install):
            if self.upgrade_strategy == "only-if-needed":
                return "already satisfied, skipping upgrade"
            return "already satisfied"

        # Check for the possibility of an upgrade.  For link-based
        # requirements we have to pull the tree down and inspect to assess
        # the version #, so it's handled way down.
        if not req_to_install.link:
            try:
                self.finder.find_requirement(req_to_install, upgrade=True)
            except BestVersionAlreadyInstalled:
                # Then the best version is installed.
                return "already up-to-date"
            except DistributionNotFound:
                # No distribution found, so we squash the error.  It will
                # be raised later when we re-try later to do the install.
                # Why don't we just raise here?
                pass

        self._set_req_to_reinstall(req_to_install)
        return None

    def _find_requirement_link(self, req: InstallRequirement) -> Optional[Link]:
        upgrade = self._is_upgrade_allowed(req)
        best_candidate = self.finder.find_requirement(req, upgrade)
        if not best_candidate:
            return None

        # Log a warning per PEP 592 if necessary before returning.
        link = best_candidate.link
        if link.is_yanked:
            reason = link.yanked_reason or "<none given>"
            msg = (
                # Mark this as a unicode string to prevent
                # "UnicodeEncodeError: 'ascii' codec can't encode character"
                # in Python 2 when the reason contains non-ascii characters.
                "The candidate selected for download or install is a "
                f"yanked version: {best_candidate}\n"
                f"Reason for being yanked: {reason}"
            )
            logger.warning(msg)

        return link

    def _populate_link(self, req: InstallRequirement) -> None:
        """Ensure that if a link can be found for this, that it is found.

        Note that req.link may still be None - if the requirement is already
        installed and not needed to be upgraded based on the return value of
        _is_upgrade_allowed().

        If preparer.require_hashes is True, don't use the wheel cache, because
        cached wheels, always built locally, have different hashes than the
        files downloaded from the index server and thus throw false hash
        mismatches. Furthermore, cached wheels at present have undeterministic
        contents due to file modification times.
        """
        if req.link is None:
            req.link = self._find_requirement_link(req)

        if self.wheel_cache is None or self.preparer.require_hashes:
            return

        assert req.link is not None, "_find_requirement_link unexpectedly returned None"
        cache_entry = self.wheel_cache.get_cache_entry(
            link=req.link,
            package_name=req.name,
            supported_tags=get_supported(),
        )
        if cache_entry is not None:
            logger.debug("Using cached wheel link: %s", cache_entry.link)
            if req.link is req.original_link and cache_entry.persistent:
                req.cached_wheel_source_link = req.link
            if cache_entry.origin is not None:
                req.download_info = cache_entry.origin
            else:
                # Legacy cache entry that does not have origin.json.
                # download_info may miss the archive_info.hashes field.
                req.download_info = direct_url_from_link(
                    req.link, link_is_in_wheel_cache=cache_entry.persistent
                )
            req.link = cache_entry.link

    def _get_dist_for(self, req: InstallRequirement) -> BaseDistribution:
        """Takes a InstallRequirement and returns a single AbstractDist \
        representing a prepared variant of the same.
        """
        if req.editable:
            return self.preparer.prepare_editable_requirement(req)

        # satisfied_by is only evaluated by calling _check_skip_installed,
        # so it must be None here.
        assert req.satisfied_by is None
        skip_reason = self._check_skip_installed(req)

        if req.satisfied_by:
            return self.preparer.prepare_installed_requirement(req, skip_reason)

        # We eagerly populate the link, since that's our "legacy" behavior.
        self._populate_link(req)
        dist = self.preparer.prepare_linked_requirement(req)

        # NOTE
        # The following portion is for determining if a certain package is
        # going to be re-installed/upgraded or not and reporting to the user.
        # This should probably get cleaned up in a future refactor.

        # req.req is only avail after unpack for URL
        # pkgs repeat check_if_exists to uninstall-on-upgrade
        # (#14)
        if not self.ignore_installed:
            req.check_if_exists(self.use_user_site)

        if req.satisfied_by:
            should_modify = (
                self.upgrade_strategy != "to-satisfy-only"
                or self.force_reinstall
                or self.ignore_installed
                or req.link.scheme == "file"
            )
            if should_modify:
                self._set_req_to_reinstall(req)
            else:
                logger.info(
                    "Requirement already satisfied (use --upgrade to upgrade): %s",
                    req,
                )
        return dist

    def _resolve_one(
        self,
        requirement_set: RequirementSet,
        req_to_install: InstallRequirement,
    ) -> List[InstallRequirement]:
        """Prepare a single requirements file.

        :return: A list of additional InstallRequirements to also install.
        """
        # Tell user what we are doing for this requirement:
        # obtain (editable), skipping, processing (local url), collecting
        # (remote url or package name)
        if req_to_install.constraint or req_to_install.prepared:
            return []

        req_to_install.prepared = True

        # Parse and return dependencies
        dist = self._get_dist_for(req_to_install)
        # This will raise UnsupportedPythonVersion if the given Python
        # version isn't compatible with the distribution's Requires-Python.
        _check_dist_requires_python(
            dist,
            version_info=self._py_version_info,
            ignore_requires_python=self.ignore_requires_python,
        )

        more_reqs: List[InstallRequirement] = []

        def add_req(subreq: Requirement, extras_requested: Iterable[str]) -> None:
            # This idiosyncratically converts the Requirement to str and let
            # make_install_req then parse it again into Requirement. But this is
            # the legacy resolver so I'm just not going to bother refactoring.
            sub_install_req = self._make_install_req(str(subreq), req_to_install)
            parent_req_name = req_to_install.name
            to_scan_again, add_to_parent = self._add_requirement_to_set(
                requirement_set,
                sub_install_req,
                parent_req_name=parent_req_name,
                extras_requested=extras_requested,
            )
            if parent_req_name and add_to_parent:
                self._discovered_dependencies[parent_req_name].append(add_to_parent)
            more_reqs.extend(to_scan_again)

        with indent_log():
            # We add req_to_install before its dependencies, so that we
            # can refer to it when adding dependencies.
            assert req_to_install.name is not None
            if not requirement_set.has_requirement(req_to_install.name):
                # 'unnamed' requirements will get added here
                # 'unnamed' requirements can only come from being directly
                # provided by the user.
                assert req_to_install.user_supplied
                self._add_requirement_to_set(
                    requirement_set, req_to_install, parent_req_name=None
                )

            if not self.ignore_dependencies:
                if req_to_install.extras:
                    logger.debug(
                        "Installing extra requirements: %r",
                        ",".join(req_to_install.extras),
                    )
                missing_requested = sorted(
                    set(req_to_install.extras) - set(dist.iter_provided_extras())
                )
                for missing in missing_requested:
                    logger.warning(
                        "%s %s does not provide the extra '%s'",
                        dist.raw_name,
                        dist.version,
                        missing,
                    )

                available_requested = sorted(
                    set(dist.iter_provided_extras()) & set(req_to_install.extras)
                )
                for subreq in dist.iter_dependencies(available_requested):
                    add_req(subreq, extras_requested=available_requested)

        return more_reqs

    def get_installation_order(
        self, req_set: RequirementSet
    ) -> List[InstallRequirement]:
        """Create the installation order.

        The installation order is topological - requirements are installed
        before the requiring thing. We break cycles at an arbitrary point,
        and make no other guarantees.
        """
        # The current implementation, which we may change at any point
        # installs the user specified things in the order given, except when
        # dependencies must come earlier to achieve topological order.
        order = []
        ordered_reqs: Set[InstallRequirement] = set()

        def schedule(req: InstallRequirement) -> None:
            if req.satisfied_by or req in ordered_reqs:
                return
            if req.constraint:
                return
            ordered_reqs.add(req)
            for dep in self._discovered_dependencies[req.name]:
                schedule(dep)
            order.append(req)

        for install_req in req_set.requirements.values():
            schedule(install_req)
        return order

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\discuss_service\async_client.py ===
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

from google.ai.generativelanguage_v1beta import gapic_version as package_version

try:
    OptionalRetry = Union[retries.AsyncRetry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.AsyncRetry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.types import discuss_service, safety

from .client import DiscussServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, DiscussServiceTransport
from .transports.grpc_asyncio import DiscussServiceGrpcAsyncIOTransport


class DiscussServiceAsyncClient:
    """An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.
    """

    _client: DiscussServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = DiscussServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = DiscussServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = DiscussServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = DiscussServiceClient._DEFAULT_UNIVERSE

    model_path = staticmethod(DiscussServiceClient.model_path)
    parse_model_path = staticmethod(DiscussServiceClient.parse_model_path)
    common_billing_account_path = staticmethod(
        DiscussServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        DiscussServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(DiscussServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(
        DiscussServiceClient.parse_common_folder_path
    )
    common_organization_path = staticmethod(
        DiscussServiceClient.common_organization_path
    )
    parse_common_organization_path = staticmethod(
        DiscussServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(DiscussServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        DiscussServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(DiscussServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        DiscussServiceClient.parse_common_location_path
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
            DiscussServiceAsyncClient: The constructed client.
        """
        return DiscussServiceClient.from_service_account_info.__func__(DiscussServiceAsyncClient, info, *args, **kwargs)  # type: ignore

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
            DiscussServiceAsyncClient: The constructed client.
        """
        return DiscussServiceClient.from_service_account_file.__func__(DiscussServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

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
        return DiscussServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> DiscussServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            DiscussServiceTransport: The transport used by the client instance.
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
        type(DiscussServiceClient).get_transport_class, type(DiscussServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, DiscussServiceTransport, Callable[..., DiscussServiceTransport]]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the discuss service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,DiscussServiceTransport,Callable[..., DiscussServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the DiscussServiceTransport constructor.
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
        self._client = DiscussServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def generate_message(
        self,
        request: Optional[Union[discuss_service.GenerateMessageRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[discuss_service.MessagePrompt] = None,
        temperature: Optional[float] = None,
        candidate_count: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> discuss_service.GenerateMessageResponse:
        r"""Generates a response from the model given an input
        ``MessagePrompt``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_generate_message():
                # Create a client
                client = generativelanguage_v1beta.DiscussServiceAsyncClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta.MessagePrompt()
                prompt.messages.content = "content_value"

                request = generativelanguage_v1beta.GenerateMessageRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = await client.generate_message(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GenerateMessageRequest, dict]]):
                The request object. Request to generate a message
                response from the model.
            model (:class:`str`):
                Required. The name of the model to use.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (:class:`google.ai.generativelanguage_v1beta.types.MessagePrompt`):
                Required. The structured textual
                input given to the model as a prompt.
                Given a
                prompt, the model will return what it
                predicts is the next message in the
                discussion.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            temperature (:class:`float`):
                Optional. Controls the randomness of the output.

                Values can range over ``[0.0,1.0]``, inclusive. A value
                closer to ``1.0`` will produce responses that are more
                varied, while a value closer to ``0.0`` will typically
                result in less surprising responses from the model.

                This corresponds to the ``temperature`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            candidate_count (:class:`int`):
                Optional. The number of generated response messages to
                return.

                This value must be between ``[1, 8]``, inclusive. If
                unset, this will default to ``1``.

                This corresponds to the ``candidate_count`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_p (:class:`float`):
                Optional. The maximum cumulative probability of tokens
                to consider when sampling.

                The model uses combined Top-k and nucleus sampling.

                Nucleus sampling considers the smallest set of tokens
                whose probability sum is at least ``top_p``.

                This corresponds to the ``top_p`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_k (:class:`int`):
                Optional. The maximum number of tokens to consider when
                sampling.

                The model uses combined Top-k and nucleus sampling.

                Top-k sampling considers the set of ``top_k`` most
                probable tokens.

                This corresponds to the ``top_k`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.GenerateMessageResponse:
                The response from the model.

                This includes candidate messages and
                conversation history in the form of
                chronologically-ordered messages.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any(
            [model, prompt, temperature, candidate_count, top_p, top_k]
        )
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, discuss_service.GenerateMessageRequest):
            request = discuss_service.GenerateMessageRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if prompt is not None:
            request.prompt = prompt
        if temperature is not None:
            request.temperature = temperature
        if candidate_count is not None:
            request.candidate_count = candidate_count
        if top_p is not None:
            request.top_p = top_p
        if top_k is not None:
            request.top_k = top_k

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.generate_message
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    async def count_message_tokens(
        self,
        request: Optional[
            Union[discuss_service.CountMessageTokensRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[discuss_service.MessagePrompt] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> discuss_service.CountMessageTokensResponse:
        r"""Runs a model's tokenizer on a string and returns the
        token count.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_count_message_tokens():
                # Create a client
                client = generativelanguage_v1beta.DiscussServiceAsyncClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta.MessagePrompt()
                prompt.messages.content = "content_value"

                request = generativelanguage_v1beta.CountMessageTokensRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = await client.count_message_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.CountMessageTokensRequest, dict]]):
                The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
            model (:class:`str`):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (:class:`google.ai.generativelanguage_v1beta.types.MessagePrompt`):
                Required. The prompt, whose token
                count is to be returned.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CountMessageTokensResponse:
                A response from CountMessageTokens.

                   It returns the model's token_count for the prompt.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, prompt])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, discuss_service.CountMessageTokensRequest):
            request = discuss_service.CountMessageTokensRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if prompt is not None:
            request.prompt = prompt

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.count_message_tokens
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    async def __aenter__(self) -> "DiscussServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("DiscussServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\discuss_service\async_client.py ===
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

from google.ai.generativelanguage_v1beta3 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.AsyncRetry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.AsyncRetry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1beta3.types import discuss_service, safety

from .client import DiscussServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, DiscussServiceTransport
from .transports.grpc_asyncio import DiscussServiceGrpcAsyncIOTransport


class DiscussServiceAsyncClient:
    """An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.
    """

    _client: DiscussServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = DiscussServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = DiscussServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = DiscussServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = DiscussServiceClient._DEFAULT_UNIVERSE

    model_path = staticmethod(DiscussServiceClient.model_path)
    parse_model_path = staticmethod(DiscussServiceClient.parse_model_path)
    common_billing_account_path = staticmethod(
        DiscussServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        DiscussServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(DiscussServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(
        DiscussServiceClient.parse_common_folder_path
    )
    common_organization_path = staticmethod(
        DiscussServiceClient.common_organization_path
    )
    parse_common_organization_path = staticmethod(
        DiscussServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(DiscussServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        DiscussServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(DiscussServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        DiscussServiceClient.parse_common_location_path
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
            DiscussServiceAsyncClient: The constructed client.
        """
        return DiscussServiceClient.from_service_account_info.__func__(DiscussServiceAsyncClient, info, *args, **kwargs)  # type: ignore

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
            DiscussServiceAsyncClient: The constructed client.
        """
        return DiscussServiceClient.from_service_account_file.__func__(DiscussServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

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
        return DiscussServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> DiscussServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            DiscussServiceTransport: The transport used by the client instance.
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
        type(DiscussServiceClient).get_transport_class, type(DiscussServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, DiscussServiceTransport, Callable[..., DiscussServiceTransport]]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the discuss service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,DiscussServiceTransport,Callable[..., DiscussServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the DiscussServiceTransport constructor.
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
        self._client = DiscussServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def generate_message(
        self,
        request: Optional[Union[discuss_service.GenerateMessageRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[discuss_service.MessagePrompt] = None,
        temperature: Optional[float] = None,
        candidate_count: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> discuss_service.GenerateMessageResponse:
        r"""Generates a response from the model given an input
        ``MessagePrompt``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_generate_message():
                # Create a client
                client = generativelanguage_v1beta3.DiscussServiceAsyncClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta3.MessagePrompt()
                prompt.messages.content = "content_value"

                request = generativelanguage_v1beta3.GenerateMessageRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = await client.generate_message(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.GenerateMessageRequest, dict]]):
                The request object. Request to generate a message
                response from the model.
            model (:class:`str`):
                Required. The name of the model to use.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (:class:`google.ai.generativelanguage_v1beta3.types.MessagePrompt`):
                Required. The structured textual
                input given to the model as a prompt.
                Given a
                prompt, the model will return what it
                predicts is the next message in the
                discussion.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            temperature (:class:`float`):
                Optional. Controls the randomness of the output.

                Values can range over ``[0.0,1.0]``, inclusive. A value
                closer to ``1.0`` will produce responses that are more
                varied, while a value closer to ``0.0`` will typically
                result in less surprising responses from the model.

                This corresponds to the ``temperature`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            candidate_count (:class:`int`):
                Optional. The number of generated response messages to
                return.

                This value must be between ``[1, 8]``, inclusive. If
                unset, this will default to ``1``.

                This corresponds to the ``candidate_count`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_p (:class:`float`):
                Optional. The maximum cumulative probability of tokens
                to consider when sampling.

                The model uses combined Top-k and nucleus sampling.

                Nucleus sampling considers the smallest set of tokens
                whose probability sum is at least ``top_p``.

                This corresponds to the ``top_p`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_k (:class:`int`):
                Optional. The maximum number of tokens to consider when
                sampling.

                The model uses combined Top-k and nucleus sampling.

                Top-k sampling considers the set of ``top_k`` most
                probable tokens.

                This corresponds to the ``top_k`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.GenerateMessageResponse:
                The response from the model.

                This includes candidate messages and
                conversation history in the form of
                chronologically-ordered messages.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any(
            [model, prompt, temperature, candidate_count, top_p, top_k]
        )
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, discuss_service.GenerateMessageRequest):
            request = discuss_service.GenerateMessageRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if prompt is not None:
            request.prompt = prompt
        if temperature is not None:
            request.temperature = temperature
        if candidate_count is not None:
            request.candidate_count = candidate_count
        if top_p is not None:
            request.top_p = top_p
        if top_k is not None:
            request.top_k = top_k

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.generate_message
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    async def count_message_tokens(
        self,
        request: Optional[
            Union[discuss_service.CountMessageTokensRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[discuss_service.MessagePrompt] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> discuss_service.CountMessageTokensResponse:
        r"""Runs a model's tokenizer on a string and returns the
        token count.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_count_message_tokens():
                # Create a client
                client = generativelanguage_v1beta3.DiscussServiceAsyncClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta3.MessagePrompt()
                prompt.messages.content = "content_value"

                request = generativelanguage_v1beta3.CountMessageTokensRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = await client.count_message_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.CountMessageTokensRequest, dict]]):
                The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
            model (:class:`str`):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (:class:`google.ai.generativelanguage_v1beta3.types.MessagePrompt`):
                Required. The prompt, whose token
                count is to be returned.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.CountMessageTokensResponse:
                A response from CountMessageTokens.

                   It returns the model's token_count for the prompt.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, prompt])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, discuss_service.CountMessageTokensRequest):
            request = discuss_service.CountMessageTokensRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if prompt is not None:
            request.prompt = prompt

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.count_message_tokens
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    async def __aenter__(self) -> "DiscussServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("DiscussServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\legacy\resolver.py ===
"""Dependency Resolution

The dependency resolution in pip is performed as follows:

for top-level requirements:
    a. only one spec allowed per project, regardless of conflicts or not.
       otherwise a "double requirement" exception is raised
    b. they override sub-dependency requirements.
for sub-dependencies
    a. "first found, wins" (where the order is breadth first)
"""

import logging
import sys
from collections import defaultdict
from itertools import chain
from typing import DefaultDict, Iterable, List, Optional, Set, Tuple

from pip._vendor.packaging import specifiers
from pip._vendor.packaging.requirements import Requirement

from pip._internal.cache import WheelCache
from pip._internal.exceptions import (
    BestVersionAlreadyInstalled,
    DistributionNotFound,
    HashError,
    HashErrors,
    InstallationError,
    NoneMetadataError,
    UnsupportedPythonVersion,
)
from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata import BaseDistribution
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.req_install import (
    InstallRequirement,
    check_invalid_constraint_type,
)
from pip._internal.req.req_set import RequirementSet
from pip._internal.resolution.base import BaseResolver, InstallRequirementProvider
from pip._internal.utils import compatibility_tags
from pip._internal.utils.compatibility_tags import get_supported
from pip._internal.utils.direct_url_helpers import direct_url_from_link
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import normalize_version_info
from pip._internal.utils.packaging import check_requires_python

logger = logging.getLogger(__name__)

DiscoveredDependencies = DefaultDict[Optional[str], List[InstallRequirement]]


def _check_dist_requires_python(
    dist: BaseDistribution,
    version_info: Tuple[int, int, int],
    ignore_requires_python: bool = False,
) -> None:
    """
    Check whether the given Python version is compatible with a distribution's
    "Requires-Python" value.

    :param version_info: A 3-tuple of ints representing the Python
        major-minor-micro version to check.
    :param ignore_requires_python: Whether to ignore the "Requires-Python"
        value if the given Python version isn't compatible.

    :raises UnsupportedPythonVersion: When the given Python version isn't
        compatible.
    """
    # This idiosyncratically converts the SpecifierSet to str and let
    # check_requires_python then parse it again into SpecifierSet. But this
    # is the legacy resolver so I'm just not going to bother refactoring.
    try:
        requires_python = str(dist.requires_python)
    except FileNotFoundError as e:
        raise NoneMetadataError(dist, str(e))
    try:
        is_compatible = check_requires_python(
            requires_python,
            version_info=version_info,
        )
    except specifiers.InvalidSpecifier as exc:
        logger.warning(
            "Package %r has an invalid Requires-Python: %s", dist.raw_name, exc
        )
        return

    if is_compatible:
        return

    version = ".".join(map(str, version_info))
    if ignore_requires_python:
        logger.debug(
            "Ignoring failed Requires-Python check for package %r: %s not in %r",
            dist.raw_name,
            version,
            requires_python,
        )
        return

    raise UnsupportedPythonVersion(
        f"Package {dist.raw_name!r} requires a different Python: "
        f"{version} not in {requires_python!r}"
    )


class Resolver(BaseResolver):
    """Resolves which packages need to be installed/uninstalled to perform \
    the requested operation without breaking the requirements of any package.
    """

    _allowed_strategies = {"eager", "only-if-needed", "to-satisfy-only"}

    def __init__(
        self,
        preparer: RequirementPreparer,
        finder: PackageFinder,
        wheel_cache: Optional[WheelCache],
        make_install_req: InstallRequirementProvider,
        use_user_site: bool,
        ignore_dependencies: bool,
        ignore_installed: bool,
        ignore_requires_python: bool,
        force_reinstall: bool,
        upgrade_strategy: str,
        py_version_info: Optional[Tuple[int, ...]] = None,
    ) -> None:
        super().__init__()
        assert upgrade_strategy in self._allowed_strategies

        if py_version_info is None:
            py_version_info = sys.version_info[:3]
        else:
            py_version_info = normalize_version_info(py_version_info)

        self._py_version_info = py_version_info

        self.preparer = preparer
        self.finder = finder
        self.wheel_cache = wheel_cache

        self.upgrade_strategy = upgrade_strategy
        self.force_reinstall = force_reinstall
        self.ignore_dependencies = ignore_dependencies
        self.ignore_installed = ignore_installed
        self.ignore_requires_python = ignore_requires_python
        self.use_user_site = use_user_site
        self._make_install_req = make_install_req

        self._discovered_dependencies: DiscoveredDependencies = defaultdict(list)

    def resolve(
        self, root_reqs: List[InstallRequirement], check_supported_wheels: bool
    ) -> RequirementSet:
        """Resolve what operations need to be done

        As a side-effect of this method, the packages (and their dependencies)
        are downloaded, unpacked and prepared for installation. This
        preparation is done by ``pip.operations.prepare``.

        Once PyPI has static dependency metadata available, it would be
        possible to move the preparation to become a step separated from
        dependency resolution.
        """
        requirement_set = RequirementSet(check_supported_wheels=check_supported_wheels)
        for req in root_reqs:
            if req.constraint:
                check_invalid_constraint_type(req)
            self._add_requirement_to_set(requirement_set, req)

        # Actually prepare the files, and collect any exceptions. Most hash
        # exceptions cannot be checked ahead of time, because
        # _populate_link() needs to be called before we can make decisions
        # based on link type.
        discovered_reqs: List[InstallRequirement] = []
        hash_errors = HashErrors()
        for req in chain(requirement_set.all_requirements, discovered_reqs):
            try:
                discovered_reqs.extend(self._resolve_one(requirement_set, req))
            except HashError as exc:
                exc.req = req
                hash_errors.append(exc)

        if hash_errors:
            raise hash_errors

        return requirement_set

    def _add_requirement_to_set(
        self,
        requirement_set: RequirementSet,
        install_req: InstallRequirement,
        parent_req_name: Optional[str] = None,
        extras_requested: Optional[Iterable[str]] = None,
    ) -> Tuple[List[InstallRequirement], Optional[InstallRequirement]]:
        """Add install_req as a requirement to install.

        :param parent_req_name: The name of the requirement that needed this
            added. The name is used because when multiple unnamed requirements
            resolve to the same name, we could otherwise end up with dependency
            links that point outside the Requirements set. parent_req must
            already be added. Note that None implies that this is a user
            supplied requirement, vs an inferred one.
        :param extras_requested: an iterable of extras used to evaluate the
            environment markers.
        :return: Additional requirements to scan. That is either [] if
            the requirement is not applicable, or [install_req] if the
            requirement is applicable and has just been added.
        """
        # If the markers do not match, ignore this requirement.
        if not install_req.match_markers(extras_requested):
            logger.info(
                "Ignoring %s: markers '%s' don't match your environment",
                install_req.name,
                install_req.markers,
            )
            return [], None

        # If the wheel is not supported, raise an error.
        # Should check this after filtering out based on environment markers to
        # allow specifying different wheels based on the environment/OS, in a
        # single requirements file.
        if install_req.link and install_req.link.is_wheel:
            wheel = Wheel(install_req.link.filename)
            tags = compatibility_tags.get_supported()
            if requirement_set.check_supported_wheels and not wheel.supported(tags):
                raise InstallationError(
                    f"{wheel.filename} is not a supported wheel on this platform."
                )

        # This next bit is really a sanity check.
        assert (
            not install_req.user_supplied or parent_req_name is None
        ), "a user supplied req shouldn't have a parent"

        # Unnamed requirements are scanned again and the requirement won't be
        # added as a dependency until after scanning.
        if not install_req.name:
            requirement_set.add_unnamed_requirement(install_req)
            return [install_req], None

        try:
            existing_req: Optional[InstallRequirement] = (
                requirement_set.get_requirement(install_req.name)
            )
        except KeyError:
            existing_req = None

        has_conflicting_requirement = (
            parent_req_name is None
            and existing_req
            and not existing_req.constraint
            and existing_req.extras == install_req.extras
            and existing_req.req
            and install_req.req
            and existing_req.req.specifier != install_req.req.specifier
        )
        if has_conflicting_requirement:
            raise InstallationError(
                f"Double requirement given: {install_req} "
                f"(already in {existing_req}, name={install_req.name!r})"
            )

        # When no existing requirement exists, add the requirement as a
        # dependency and it will be scanned again after.
        if not existing_req:
            requirement_set.add_named_requirement(install_req)
            # We'd want to rescan this requirement later
            return [install_req], install_req

        # Assume there's no need to scan, and that we've already
        # encountered this for scanning.
        if install_req.constraint or not existing_req.constraint:
            return [], existing_req

        does_not_satisfy_constraint = install_req.link and not (
            existing_req.link and install_req.link.path == existing_req.link.path
        )
        if does_not_satisfy_constraint:
            raise InstallationError(
                f"Could not satisfy constraints for '{install_req.name}': "
                "installation from path or url cannot be "
                "constrained to a version"
            )
        # If we're now installing a constraint, mark the existing
        # object for real installation.
        existing_req.constraint = False
        # If we're now installing a user supplied requirement,
        # mark the existing object as such.
        if install_req.user_supplied:
            existing_req.user_supplied = True
        existing_req.extras = tuple(
            sorted(set(existing_req.extras) | set(install_req.extras))
        )
        logger.debug(
            "Setting %s extras to: %s",
            existing_req,
            existing_req.extras,
        )
        # Return the existing requirement for addition to the parent and
        # scanning again.
        return [existing_req], existing_req

    def _is_upgrade_allowed(self, req: InstallRequirement) -> bool:
        if self.upgrade_strategy == "to-satisfy-only":
            return False
        elif self.upgrade_strategy == "eager":
            return True
        else:
            assert self.upgrade_strategy == "only-if-needed"
            return req.user_supplied or req.constraint

    def _set_req_to_reinstall(self, req: InstallRequirement) -> None:
        """
        Set a requirement to be installed.
        """
        # Don't uninstall the conflict if doing a user install and the
        # conflict is not a user install.
        assert req.satisfied_by is not None
        if not self.use_user_site or req.satisfied_by.in_usersite:
            req.should_reinstall = True
        req.satisfied_by = None

    def _check_skip_installed(
        self, req_to_install: InstallRequirement
    ) -> Optional[str]:
        """Check if req_to_install should be skipped.

        This will check if the req is installed, and whether we should upgrade
        or reinstall it, taking into account all the relevant user options.

        After calling this req_to_install will only have satisfied_by set to
        None if the req_to_install is to be upgraded/reinstalled etc. Any
        other value will be a dist recording the current thing installed that
        satisfies the requirement.

        Note that for vcs urls and the like we can't assess skipping in this
        routine - we simply identify that we need to pull the thing down,
        then later on it is pulled down and introspected to assess upgrade/
        reinstalls etc.

        :return: A text reason for why it was skipped, or None.
        """
        if self.ignore_installed:
            return None

        req_to_install.check_if_exists(self.use_user_site)
        if not req_to_install.satisfied_by:
            return None

        if self.force_reinstall:
            self._set_req_to_reinstall(req_to_install)
            return None

        if not self._is_upgrade_allowed(req_to_install):
            if self.upgrade_strategy == "only-if-needed":
                return "already satisfied, skipping upgrade"
            return "already satisfied"

        # Check for the possibility of an upgrade.  For link-based
        # requirements we have to pull the tree down and inspect to assess
        # the version #, so it's handled way down.
        if not req_to_install.link:
            try:
                self.finder.find_requirement(req_to_install, upgrade=True)
            except BestVersionAlreadyInstalled:
                # Then the best version is installed.
                return "already up-to-date"
            except DistributionNotFound:
                # No distribution found, so we squash the error.  It will
                # be raised later when we re-try later to do the install.
                # Why don't we just raise here?
                pass

        self._set_req_to_reinstall(req_to_install)
        return None

    def _find_requirement_link(self, req: InstallRequirement) -> Optional[Link]:
        upgrade = self._is_upgrade_allowed(req)
        best_candidate = self.finder.find_requirement(req, upgrade)
        if not best_candidate:
            return None

        # Log a warning per PEP 592 if necessary before returning.
        link = best_candidate.link
        if link.is_yanked:
            reason = link.yanked_reason or "<none given>"
            msg = (
                # Mark this as a unicode string to prevent
                # "UnicodeEncodeError: 'ascii' codec can't encode character"
                # in Python 2 when the reason contains non-ascii characters.
                "The candidate selected for download or install is a "
                f"yanked version: {best_candidate}\n"
                f"Reason for being yanked: {reason}"
            )
            logger.warning(msg)

        return link

    def _populate_link(self, req: InstallRequirement) -> None:
        """Ensure that if a link can be found for this, that it is found.

        Note that req.link may still be None - if the requirement is already
        installed and not needed to be upgraded based on the return value of
        _is_upgrade_allowed().

        If preparer.require_hashes is True, don't use the wheel cache, because
        cached wheels, always built locally, have different hashes than the
        files downloaded from the index server and thus throw false hash
        mismatches. Furthermore, cached wheels at present have undeterministic
        contents due to file modification times.
        """
        if req.link is None:
            req.link = self._find_requirement_link(req)

        if self.wheel_cache is None or self.preparer.require_hashes:
            return

        assert req.link is not None, "_find_requirement_link unexpectedly returned None"
        cache_entry = self.wheel_cache.get_cache_entry(
            link=req.link,
            package_name=req.name,
            supported_tags=get_supported(),
        )
        if cache_entry is not None:
            logger.debug("Using cached wheel link: %s", cache_entry.link)
            if req.link is req.original_link and cache_entry.persistent:
                req.cached_wheel_source_link = req.link
            if cache_entry.origin is not None:
                req.download_info = cache_entry.origin
            else:
                # Legacy cache entry that does not have origin.json.
                # download_info may miss the archive_info.hashes field.
                req.download_info = direct_url_from_link(
                    req.link, link_is_in_wheel_cache=cache_entry.persistent
                )
            req.link = cache_entry.link

    def _get_dist_for(self, req: InstallRequirement) -> BaseDistribution:
        """Takes a InstallRequirement and returns a single AbstractDist \
        representing a prepared variant of the same.
        """
        if req.editable:
            return self.preparer.prepare_editable_requirement(req)

        # satisfied_by is only evaluated by calling _check_skip_installed,
        # so it must be None here.
        assert req.satisfied_by is None
        skip_reason = self._check_skip_installed(req)

        if req.satisfied_by:
            return self.preparer.prepare_installed_requirement(req, skip_reason)

        # We eagerly populate the link, since that's our "legacy" behavior.
        self._populate_link(req)
        dist = self.preparer.prepare_linked_requirement(req)

        # NOTE
        # The following portion is for determining if a certain package is
        # going to be re-installed/upgraded or not and reporting to the user.
        # This should probably get cleaned up in a future refactor.

        # req.req is only avail after unpack for URL
        # pkgs repeat check_if_exists to uninstall-on-upgrade
        # (#14)
        if not self.ignore_installed:
            req.check_if_exists(self.use_user_site)

        if req.satisfied_by:
            should_modify = (
                self.upgrade_strategy != "to-satisfy-only"
                or self.force_reinstall
                or self.ignore_installed
                or req.link.scheme == "file"
            )
            if should_modify:
                self._set_req_to_reinstall(req)
            else:
                logger.info(
                    "Requirement already satisfied (use --upgrade to upgrade): %s",
                    req,
                )
        return dist

    def _resolve_one(
        self,
        requirement_set: RequirementSet,
        req_to_install: InstallRequirement,
    ) -> List[InstallRequirement]:
        """Prepare a single requirements file.

        :return: A list of additional InstallRequirements to also install.
        """
        # Tell user what we are doing for this requirement:
        # obtain (editable), skipping, processing (local url), collecting
        # (remote url or package name)
        if req_to_install.constraint or req_to_install.prepared:
            return []

        req_to_install.prepared = True

        # Parse and return dependencies
        dist = self._get_dist_for(req_to_install)
        # This will raise UnsupportedPythonVersion if the given Python
        # version isn't compatible with the distribution's Requires-Python.
        _check_dist_requires_python(
            dist,
            version_info=self._py_version_info,
            ignore_requires_python=self.ignore_requires_python,
        )

        more_reqs: List[InstallRequirement] = []

        def add_req(subreq: Requirement, extras_requested: Iterable[str]) -> None:
            # This idiosyncratically converts the Requirement to str and let
            # make_install_req then parse it again into Requirement. But this is
            # the legacy resolver so I'm just not going to bother refactoring.
            sub_install_req = self._make_install_req(str(subreq), req_to_install)
            parent_req_name = req_to_install.name
            to_scan_again, add_to_parent = self._add_requirement_to_set(
                requirement_set,
                sub_install_req,
                parent_req_name=parent_req_name,
                extras_requested=extras_requested,
            )
            if parent_req_name and add_to_parent:
                self._discovered_dependencies[parent_req_name].append(add_to_parent)
            more_reqs.extend(to_scan_again)

        with indent_log():
            # We add req_to_install before its dependencies, so that we
            # can refer to it when adding dependencies.
            assert req_to_install.name is not None
            if not requirement_set.has_requirement(req_to_install.name):
                # 'unnamed' requirements will get added here
                # 'unnamed' requirements can only come from being directly
                # provided by the user.
                assert req_to_install.user_supplied
                self._add_requirement_to_set(
                    requirement_set, req_to_install, parent_req_name=None
                )

            if not self.ignore_dependencies:
                if req_to_install.extras:
                    logger.debug(
                        "Installing extra requirements: %r",
                        ",".join(req_to_install.extras),
                    )
                missing_requested = sorted(
                    set(req_to_install.extras) - set(dist.iter_provided_extras())
                )
                for missing in missing_requested:
                    logger.warning(
                        "%s %s does not provide the extra '%s'",
                        dist.raw_name,
                        dist.version,
                        missing,
                    )

                available_requested = sorted(
                    set(dist.iter_provided_extras()) & set(req_to_install.extras)
                )
                for subreq in dist.iter_dependencies(available_requested):
                    add_req(subreq, extras_requested=available_requested)

        return more_reqs

    def get_installation_order(
        self, req_set: RequirementSet
    ) -> List[InstallRequirement]:
        """Create the installation order.

        The installation order is topological - requirements are installed
        before the requiring thing. We break cycles at an arbitrary point,
        and make no other guarantees.
        """
        # The current implementation, which we may change at any point
        # installs the user specified things in the order given, except when
        # dependencies must come earlier to achieve topological order.
        order = []
        ordered_reqs: Set[InstallRequirement] = set()

        def schedule(req: InstallRequirement) -> None:
            if req.satisfied_by or req in ordered_reqs:
                return
            if req.constraint:
                return
            ordered_reqs.add(req)
            for dep in self._discovered_dependencies[req.name]:
                schedule(dep)
            order.append(req)

        for install_req in req_set.requirements.values():
            schedule(install_req)
        return order

# === NexusCore/openenv\Lib\site-packages\matplotlib\spines.py ===
from collections.abc import MutableMapping
import functools

import numpy as np

import matplotlib as mpl
from matplotlib import _api, _docstring
from matplotlib.artist import allow_rasterization
import matplotlib.transforms as mtransforms
import matplotlib.patches as mpatches
import matplotlib.path as mpath


class Spine(mpatches.Patch):
    """
    An axis spine -- the line noting the data area boundaries.

    Spines are the lines connecting the axis tick marks and noting the
    boundaries of the data area. They can be placed at arbitrary
    positions. See `~.Spine.set_position` for more information.

    The default position is ``('outward', 0)``.

    Spines are subclasses of `.Patch`, and inherit much of their behavior.

    Spines draw a line, a circle, or an arc depending on if
    `~.Spine.set_patch_line`, `~.Spine.set_patch_circle`, or
    `~.Spine.set_patch_arc` has been called. Line-like is the default.

    For examples see :ref:`spines_examples`.
    """
    def __str__(self):
        return "Spine"

    @_docstring.interpd
    def __init__(self, axes, spine_type, path, **kwargs):
        """
        Parameters
        ----------
        axes : `~matplotlib.axes.Axes`
            The `~.axes.Axes` instance containing the spine.
        spine_type : str
            The spine type.
        path : `~matplotlib.path.Path`
            The `.Path` instance used to draw the spine.

        Other Parameters
        ----------------
        **kwargs
            Valid keyword arguments are:

            %(Patch:kwdoc)s
        """
        super().__init__(**kwargs)
        self.axes = axes
        self.set_figure(self.axes.get_figure(root=False))
        self.spine_type = spine_type
        self.set_facecolor('none')
        self.set_edgecolor(mpl.rcParams['axes.edgecolor'])
        self.set_linewidth(mpl.rcParams['axes.linewidth'])
        self.set_capstyle('projecting')
        self.axis = None

        self.set_zorder(2.5)
        self.set_transform(self.axes.transData)  # default transform

        self._bounds = None  # default bounds

        # Defer initial position determination. (Not much support for
        # non-rectangular axes is currently implemented, and this lets
        # them pass through the spines machinery without errors.)
        self._position = None
        _api.check_isinstance(mpath.Path, path=path)
        self._path = path

        # To support drawing both linear and circular spines, this
        # class implements Patch behavior three ways. If
        # self._patch_type == 'line', behave like a mpatches.PathPatch
        # instance. If self._patch_type == 'circle', behave like a
        # mpatches.Ellipse instance. If self._patch_type == 'arc', behave like
        # a mpatches.Arc instance.
        self._patch_type = 'line'

        # Behavior copied from mpatches.Ellipse:
        # Note: This cannot be calculated until this is added to an Axes
        self._patch_transform = mtransforms.IdentityTransform()

    def set_patch_arc(self, center, radius, theta1, theta2):
        """Set the spine to be arc-like."""
        self._patch_type = 'arc'
        self._center = center
        self._width = radius * 2
        self._height = radius * 2
        self._theta1 = theta1
        self._theta2 = theta2
        self._path = mpath.Path.arc(theta1, theta2)
        # arc drawn on axes transform
        self.set_transform(self.axes.transAxes)
        self.stale = True

    def set_patch_circle(self, center, radius):
        """Set the spine to be circular."""
        self._patch_type = 'circle'
        self._center = center
        self._width = radius * 2
        self._height = radius * 2
        # circle drawn on axes transform
        self.set_transform(self.axes.transAxes)
        self.stale = True

    def set_patch_line(self):
        """Set the spine to be linear."""
        self._patch_type = 'line'
        self.stale = True

    # Behavior copied from mpatches.Ellipse:
    def _recompute_transform(self):
        """
        Notes
        -----
        This cannot be called until after this has been added to an Axes,
        otherwise unit conversion will fail. This makes it very important to
        call the accessor method and not directly access the transformation
        member variable.
        """
        assert self._patch_type in ('arc', 'circle')
        center = (self.convert_xunits(self._center[0]),
                  self.convert_yunits(self._center[1]))
        width = self.convert_xunits(self._width)
        height = self.convert_yunits(self._height)
        self._patch_transform = mtransforms.Affine2D() \
            .scale(width * 0.5, height * 0.5) \
            .translate(*center)

    def get_patch_transform(self):
        if self._patch_type in ('arc', 'circle'):
            self._recompute_transform()
            return self._patch_transform
        else:
            return super().get_patch_transform()

    def get_window_extent(self, renderer=None):
        """
        Return the window extent of the spines in display space, including
        padding for ticks (but not their labels)

        See Also
        --------
        matplotlib.axes.Axes.get_tightbbox
        matplotlib.axes.Axes.get_window_extent
        """
        # make sure the location is updated so that transforms etc are correct:
        self._adjust_location()
        bb = super().get_window_extent(renderer=renderer)
        if self.axis is None or not self.axis.get_visible():
            return bb
        bboxes = [bb]
        drawn_ticks = self.axis._update_ticks()

        major_tick = next(iter({*drawn_ticks} & {*self.axis.majorTicks}), None)
        minor_tick = next(iter({*drawn_ticks} & {*self.axis.minorTicks}), None)
        for tick in [major_tick, minor_tick]:
            if tick is None:
                continue
            bb0 = bb.frozen()
            tickl = tick._size
            tickdir = tick._tickdir
            if tickdir == 'out':
                padout = 1
                padin = 0
            elif tickdir == 'in':
                padout = 0
                padin = 1
            else:
                padout = 0.5
                padin = 0.5
            dpi = self.get_figure(root=True).dpi
            padout = padout * tickl / 72 * dpi
            padin = padin * tickl / 72 * dpi

            if tick.tick1line.get_visible():
                if self.spine_type == 'left':
                    bb0.x0 = bb0.x0 - padout
                    bb0.x1 = bb0.x1 + padin
                elif self.spine_type == 'bottom':
                    bb0.y0 = bb0.y0 - padout
                    bb0.y1 = bb0.y1 + padin

            if tick.tick2line.get_visible():
                if self.spine_type == 'right':
                    bb0.x1 = bb0.x1 + padout
                    bb0.x0 = bb0.x0 - padin
                elif self.spine_type == 'top':
                    bb0.y1 = bb0.y1 + padout
                    bb0.y0 = bb0.y0 - padout
            bboxes.append(bb0)

        return mtransforms.Bbox.union(bboxes)

    def get_path(self):
        return self._path

    def _ensure_position_is_set(self):
        if self._position is None:
            # default position
            self._position = ('outward', 0.0)  # in points
            self.set_position(self._position)

    def register_axis(self, axis):
        """
        Register an axis.

        An axis should be registered with its corresponding spine from
        the Axes instance. This allows the spine to clear any axis
        properties when needed.
        """
        self.axis = axis
        self.stale = True

    def clear(self):
        """Clear the current spine."""
        self._clear()
        if self.axis is not None:
            self.axis.clear()

    def _clear(self):
        """
        Clear things directly related to the spine.

        In this way it is possible to avoid clearing the Axis as well when calling
        from library code where it is known that the Axis is cleared separately.
        """
        self._position = None  # clear position

    def _adjust_location(self):
        """Automatically set spine bounds to the view interval."""

        if self.spine_type == 'circle':
            return

        if self._bounds is not None:
            low, high = self._bounds
        elif self.spine_type in ('left', 'right'):
            low, high = self.axes.viewLim.intervaly
        elif self.spine_type in ('top', 'bottom'):
            low, high = self.axes.viewLim.intervalx
        else:
            raise ValueError(f'unknown spine spine_type: {self.spine_type}')

        if self._patch_type == 'arc':
            if self.spine_type in ('bottom', 'top'):
                try:
                    direction = self.axes.get_theta_direction()
                except AttributeError:
                    direction = 1
                try:
                    offset = self.axes.get_theta_offset()
                except AttributeError:
                    offset = 0
                low = low * direction + offset
                high = high * direction + offset
                if low > high:
                    low, high = high, low

                self._path = mpath.Path.arc(np.rad2deg(low), np.rad2deg(high))

                if self.spine_type == 'bottom':
                    rmin, rmax = self.axes.viewLim.intervaly
                    try:
                        rorigin = self.axes.get_rorigin()
                    except AttributeError:
                        rorigin = rmin
                    scaled_diameter = (rmin - rorigin) / (rmax - rorigin)
                    self._height = scaled_diameter
                    self._width = scaled_diameter

            else:
                raise ValueError('unable to set bounds for spine "%s"' %
                                 self.spine_type)
        else:
            v1 = self._path.vertices
            assert v1.shape == (2, 2), 'unexpected vertices shape'
            if self.spine_type in ['left', 'right']:
                v1[0, 1] = low
                v1[1, 1] = high
            elif self.spine_type in ['bottom', 'top']:
                v1[0, 0] = low
                v1[1, 0] = high
            else:
                raise ValueError('unable to set bounds for spine "%s"' %
                                 self.spine_type)

    @allow_rasterization
    def draw(self, renderer):
        self._adjust_location()
        ret = super().draw(renderer)
        self.stale = False
        return ret

    def set_position(self, position):
        """
        Set the position of the spine.

        Spine position is specified by a 2 tuple of (position type,
        amount). The position types are:

        * 'outward': place the spine out from the data area by the specified
          number of points. (Negative values place the spine inwards.)
        * 'axes': place the spine at the specified Axes coordinate (0 to 1).
        * 'data': place the spine at the specified data coordinate.

        Additionally, shorthand notations define a special positions:

        * 'center' -> ``('axes', 0.5)``
        * 'zero' -> ``('data', 0.0)``

        Examples
        --------
        :doc:`/gallery/spines/spine_placement_demo`
        """
        if position in ('center', 'zero'):  # special positions
            pass
        else:
            if len(position) != 2:
                raise ValueError("position should be 'center' or 2-tuple")
            if position[0] not in ['outward', 'axes', 'data']:
                raise ValueError("position[0] should be one of 'outward', "
                                 "'axes', or 'data' ")
        self._position = position
        self.set_transform(self.get_spine_transform())
        if self.axis is not None:
            self.axis.reset_ticks()
        self.stale = True

    def get_position(self):
        """Return the spine position."""
        self._ensure_position_is_set()
        return self._position

    def get_spine_transform(self):
        """Return the spine transform."""
        self._ensure_position_is_set()

        position = self._position
        if isinstance(position, str):
            if position == 'center':
                position = ('axes', 0.5)
            elif position == 'zero':
                position = ('data', 0)
        assert len(position) == 2, 'position should be 2-tuple'
        position_type, amount = position
        _api.check_in_list(['axes', 'outward', 'data'],
                           position_type=position_type)
        if self.spine_type in ['left', 'right']:
            base_transform = self.axes.get_yaxis_transform(which='grid')
        elif self.spine_type in ['top', 'bottom']:
            base_transform = self.axes.get_xaxis_transform(which='grid')
        else:
            raise ValueError(f'unknown spine spine_type: {self.spine_type!r}')

        if position_type == 'outward':
            if amount == 0:  # short circuit commonest case
                return base_transform
            else:
                offset_vec = {'left': (-1, 0), 'right': (1, 0),
                              'bottom': (0, -1), 'top': (0, 1),
                              }[self.spine_type]
                # calculate x and y offset in dots
                offset_dots = amount * np.array(offset_vec) / 72
                return (base_transform
                        + mtransforms.ScaledTranslation(
                            *offset_dots, self.get_figure(root=False).dpi_scale_trans))
        elif position_type == 'axes':
            if self.spine_type in ['left', 'right']:
                # keep y unchanged, fix x at amount
                return (mtransforms.Affine2D.from_values(0, 0, 0, 1, amount, 0)
                        + base_transform)
            elif self.spine_type in ['bottom', 'top']:
                # keep x unchanged, fix y at amount
                return (mtransforms.Affine2D.from_values(1, 0, 0, 0, 0, amount)
                        + base_transform)
        elif position_type == 'data':
            if self.spine_type in ('right', 'top'):
                # The right and top spines have a default position of 1 in
                # axes coordinates.  When specifying the position in data
                # coordinates, we need to calculate the position relative to 0.
                amount -= 1
            if self.spine_type in ('left', 'right'):
                return mtransforms.blended_transform_factory(
                    mtransforms.Affine2D().translate(amount, 0)
                    + self.axes.transData,
                    self.axes.transData)
            elif self.spine_type in ('bottom', 'top'):
                return mtransforms.blended_transform_factory(
                    self.axes.transData,
                    mtransforms.Affine2D().translate(0, amount)
                    + self.axes.transData)

    def set_bounds(self, low=None, high=None):
        """
        Set the spine bounds.

        Parameters
        ----------
        low : float or None, optional
            The lower spine bound. Passing *None* leaves the limit unchanged.

            The bounds may also be passed as the tuple (*low*, *high*) as the
            first positional argument.

            .. ACCEPTS: (low: float, high: float)

        high : float or None, optional
            The higher spine bound. Passing *None* leaves the limit unchanged.
        """
        if self.spine_type == 'circle':
            raise ValueError(
                'set_bounds() method incompatible with circular spines')
        if high is None and np.iterable(low):
            low, high = low
        old_low, old_high = self.get_bounds() or (None, None)
        if low is None:
            low = old_low
        if high is None:
            high = old_high
        self._bounds = (low, high)
        self.stale = True

    def get_bounds(self):
        """Get the bounds of the spine."""
        return self._bounds

    @classmethod
    def linear_spine(cls, axes, spine_type, **kwargs):
        """Create and return a linear `Spine`."""
        # all values of 0.999 get replaced upon call to set_bounds()
        if spine_type == 'left':
            path = mpath.Path([(0.0, 0.999), (0.0, 0.999)])
        elif spine_type == 'right':
            path = mpath.Path([(1.0, 0.999), (1.0, 0.999)])
        elif spine_type == 'bottom':
            path = mpath.Path([(0.999, 0.0), (0.999, 0.0)])
        elif spine_type == 'top':
            path = mpath.Path([(0.999, 1.0), (0.999, 1.0)])
        else:
            raise ValueError('unable to make path for spine "%s"' % spine_type)
        result = cls(axes, spine_type, path, **kwargs)
        result.set_visible(mpl.rcParams[f'axes.spines.{spine_type}'])

        return result

    @classmethod
    def arc_spine(cls, axes, spine_type, center, radius, theta1, theta2,
                  **kwargs):
        """Create and return an arc `Spine`."""
        path = mpath.Path.arc(theta1, theta2)
        result = cls(axes, spine_type, path, **kwargs)
        result.set_patch_arc(center, radius, theta1, theta2)
        return result

    @classmethod
    def circular_spine(cls, axes, center, radius, **kwargs):
        """Create and return a circular `Spine`."""
        path = mpath.Path.unit_circle()
        spine_type = 'circle'
        result = cls(axes, spine_type, path, **kwargs)
        result.set_patch_circle(center, radius)
        return result

    def set_color(self, c):
        """
        Set the edgecolor.

        Parameters
        ----------
        c : :mpltype:`color`

        Notes
        -----
        This method does not modify the facecolor (which defaults to "none"),
        unlike the `.Patch.set_color` method defined in the parent class.  Use
        `.Patch.set_facecolor` to set the facecolor.
        """
        self.set_edgecolor(c)
        self.stale = True


class SpinesProxy:
    """
    A proxy to broadcast ``set_*()`` and ``set()`` method calls to contained `.Spines`.

    The proxy cannot be used for any other operations on its members.

    The supported methods are determined dynamically based on the contained
    spines. If not all spines support a given method, it's executed only on
    the subset of spines that support it.
    """
    def __init__(self, spine_dict):
        self._spine_dict = spine_dict

    def __getattr__(self, name):
        broadcast_targets = [spine for spine in self._spine_dict.values()
                             if hasattr(spine, name)]
        if (name != 'set' and not name.startswith('set_')) or not broadcast_targets:
            raise AttributeError(
                f"'SpinesProxy' object has no attribute '{name}'")

        def x(_targets, _funcname, *args, **kwargs):
            for spine in _targets:
                getattr(spine, _funcname)(*args, **kwargs)
        x = functools.partial(x, broadcast_targets, name)
        x.__doc__ = broadcast_targets[0].__doc__
        return x

    def __dir__(self):
        names = []
        for spine in self._spine_dict.values():
            names.extend(name
                         for name in dir(spine) if name.startswith('set_'))
        return list(sorted(set(names)))


class Spines(MutableMapping):
    r"""
    The container of all `.Spine`\s in an Axes.

    The interface is dict-like mapping names (e.g. 'left') to `.Spine` objects.
    Additionally, it implements some pandas.Series-like features like accessing
    elements by attribute::

        spines['top'].set_visible(False)
        spines.top.set_visible(False)

    Multiple spines can be addressed simultaneously by passing a list::

        spines[['top', 'right']].set_visible(False)

    Use an open slice to address all spines::

        spines[:].set_visible(False)

    The latter two indexing methods will return a `SpinesProxy` that broadcasts all
    ``set_*()`` and ``set()`` calls to its members, but cannot be used for any other
    operation.
    """
    def __init__(self, **kwargs):
        self._dict = kwargs

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    def __getstate__(self):
        return self._dict

    def __setstate__(self, state):
        self.__init__(**state)

    def __getattr__(self, name):
        try:
            return self._dict[name]
        except KeyError:
            raise AttributeError(
                f"'Spines' object does not contain a '{name}' spine")

    def __getitem__(self, key):
        if isinstance(key, list):
            unknown_keys = [k for k in key if k not in self._dict]
            if unknown_keys:
                raise KeyError(', '.join(unknown_keys))
            return SpinesProxy({k: v for k, v in self._dict.items()
                                if k in key})
        if isinstance(key, tuple):
            raise ValueError('Multiple spines must be passed as a single list')
        if isinstance(key, slice):
            if key.start is None and key.stop is None and key.step is None:
                return SpinesProxy(self._dict)
            else:
                raise ValueError(
                    'Spines does not support slicing except for the fully '
                    'open slice [:] to access all spines.')
        return self._dict[key]

    def __setitem__(self, key, value):
        # TODO: Do we want to deprecate adding spines?
        self._dict[key] = value

    def __delitem__(self, key):
        # TODO: Do we want to deprecate deleting spines?
        del self._dict[key]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

# === NexusCore/openenv\Lib\site-packages\typing_inspection\typing_objects.py ===
"""Low-level introspection utilities for [`typing`][] members.

The provided functions in this module check against both the [`typing`][] and [`typing_extensions`][]
variants, if they exists and are different.
"""
# ruff: noqa: UP006

import collections.abc
import contextlib
import re
import sys
import typing
import warnings
from textwrap import dedent
from types import FunctionType, GenericAlias
from typing import Any, Final

import typing_extensions
from typing_extensions import LiteralString, TypeAliasType, TypeIs, deprecated

__all__ = (
    'DEPRECATED_ALIASES',
    'NoneType',
    'is_annotated',
    'is_any',
    'is_classvar',
    'is_concatenate',
    'is_deprecated',
    'is_final',
    'is_forwardref',
    'is_generic',
    'is_literal',
    'is_literalstring',
    'is_namedtuple',
    'is_never',
    'is_newtype',
    'is_nodefault',
    'is_noreturn',
    'is_notrequired',
    'is_paramspec',
    'is_paramspecargs',
    'is_paramspeckwargs',
    'is_readonly',
    'is_required',
    'is_self',
    'is_typealias',
    'is_typealiastype',
    'is_typeguard',
    'is_typeis',
    'is_typevar',
    'is_typevartuple',
    'is_union',
    'is_unpack',
)

_IS_PY310 = sys.version_info[:2] == (3, 10)


def _compile_identity_check_function(member: LiteralString, function_name: LiteralString) -> FunctionType:
    """Create a function checking that the function argument is the (unparameterized) typing :paramref:`member`.

    The function will make sure to check against both the `typing` and `typing_extensions`
    variants as depending on the Python version, the `typing_extensions` variant might be different.
    For instance, on Python 3.9:

    ```pycon
    >>> from typing import Literal as t_Literal
    >>> from typing_extensions import Literal as te_Literal, get_origin

    >>> t_Literal is te_Literal
    False
    >>> get_origin(t_Literal[1])
    typing.Literal
    >>> get_origin(te_Literal[1])
    typing_extensions.Literal
    ```
    """
    in_typing = hasattr(typing, member)
    in_typing_extensions = hasattr(typing_extensions, member)

    if in_typing and in_typing_extensions:
        if getattr(typing, member) is getattr(typing_extensions, member):
            check_code = f'obj is typing.{member}'
        else:
            check_code = f'obj is typing.{member} or obj is typing_extensions.{member}'
    elif in_typing and not in_typing_extensions:
        check_code = f'obj is typing.{member}'
    elif not in_typing and in_typing_extensions:
        check_code = f'obj is typing_extensions.{member}'
    else:
        check_code = 'False'

    func_code = dedent(f"""
    def {function_name}(obj: Any, /) -> bool:
        return {check_code}
    """)

    locals_: dict[str, Any] = {}
    globals_: dict[str, Any] = {'Any': Any, 'typing': typing, 'typing_extensions': typing_extensions}
    exec(func_code, globals_, locals_)
    return locals_[function_name]


def _compile_isinstance_check_function(member: LiteralString, function_name: LiteralString) -> FunctionType:
    """Create a function checking that the function is an instance of the typing `member`.

    The function will make sure to check against both the `typing` and `typing_extensions`
    variants as depending on the Python version, the `typing_extensions` variant might be different.
    """
    in_typing = hasattr(typing, member)
    in_typing_extensions = hasattr(typing_extensions, member)

    if in_typing and in_typing_extensions:
        if getattr(typing, member) is getattr(typing_extensions, member):
            check_code = f'isinstance(obj, typing.{member})'
        else:
            check_code = f'isinstance(obj, (typing.{member}, typing_extensions.{member}))'
    elif in_typing and not in_typing_extensions:
        check_code = f'isinstance(obj, typing.{member})'
    elif not in_typing and in_typing_extensions:
        check_code = f'isinstance(obj, typing_extensions.{member})'
    else:
        check_code = 'False'

    func_code = dedent(f"""
    def {function_name}(obj: Any, /) -> 'TypeIs[{member}]':
        return {check_code}
    """)

    locals_: dict[str, Any] = {}
    globals_: dict[str, Any] = {'Any': Any, 'typing': typing, 'typing_extensions': typing_extensions}
    exec(func_code, globals_, locals_)
    return locals_[function_name]


if sys.version_info >= (3, 10):
    from types import NoneType
else:
    NoneType = type(None)

# Keep this ordered, as per `typing.__all__`:

is_annotated = _compile_identity_check_function('Annotated', 'is_annotated')
is_annotated.__doc__ = """
Return whether the argument is the [`Annotated`][typing.Annotated] [special form][].

```pycon
>>> is_annotated(Annotated)
True
>>> is_annotated(Annotated[int, ...])
False
```
"""

is_any = _compile_identity_check_function('Any', 'is_any')
is_any.__doc__ = """
Return whether the argument is the [`Any`][typing.Any] [special form][].

```pycon
>>> is_any(Any)
True
```
"""

is_classvar = _compile_identity_check_function('ClassVar', 'is_classvar')
is_classvar.__doc__ = """
Return whether the argument is the [`ClassVar`][typing.ClassVar] [type qualifier][].

```pycon
>>> is_classvar(ClassVar)
True
>>> is_classvar(ClassVar[int])
>>> False
```
"""

is_concatenate = _compile_identity_check_function('Concatenate', 'is_concatenate')
is_concatenate.__doc__ = """
Return whether the argument is the [`Concatenate`][typing.Concatenate] [special form][].

```pycon
>>> is_concatenate(Concatenate)
True
>>> is_concatenate(Concatenate[int, P])
False
```
"""

is_final = _compile_identity_check_function('Final', 'is_final')
is_final.__doc__ = """
Return whether the argument is the [`Final`][typing.Final] [type qualifier][].

```pycon
>>> is_final(Final)
True
>>> is_final(Final[int])
False
```
"""


# Unlikely to have a different version in `typing-extensions`, but keep it consistent.
# Also note that starting in 3.14, this is an alias to `annotationlib.ForwardRef`, but
# accessing it from `typing` doesn't seem to be deprecated.
is_forwardref = _compile_isinstance_check_function('ForwardRef', 'is_forwardref')
is_forwardref.__doc__ = """
Return whether the argument is an instance of [`ForwardRef`][typing.ForwardRef].

```pycon
>>> is_forwardref(ForwardRef('T'))
True
```
"""


is_generic = _compile_identity_check_function('Generic', 'is_generic')
is_generic.__doc__ = """
Return whether the argument is the [`Generic`][typing.Generic] [special form][].

```pycon
>>> is_generic(Generic)
True
>>> is_generic(Generic[T])
False
```
"""

is_literal = _compile_identity_check_function('Literal', 'is_literal')
is_literal.__doc__ = """
Return whether the argument is the [`Literal`][typing.Literal] [special form][].

```pycon
>>> is_literal(Literal)
True
>>> is_literal(Literal["a"])
False
```
"""


# `get_origin(Optional[int]) is Union`, so `is_optional()` isn't implemented.

is_paramspec = _compile_isinstance_check_function('ParamSpec', 'is_paramspec')
is_paramspec.__doc__ = """
Return whether the argument is an instance of [`ParamSpec`][typing.ParamSpec].

```pycon
>>> P = ParamSpec('P')
>>> is_paramspec(P)
True
```
"""

# Protocol?

is_typevar = _compile_isinstance_check_function('TypeVar', 'is_typevar')
is_typevar.__doc__ = """
Return whether the argument is an instance of [`TypeVar`][typing.TypeVar].

```pycon
>>> T = TypeVar('T')
>>> is_typevar(T)
True
```
"""

is_typevartuple = _compile_isinstance_check_function('TypeVarTuple', 'is_typevartuple')
is_typevartuple.__doc__ = """
Return whether the argument is an instance of [`TypeVarTuple`][typing.TypeVarTuple].

```pycon
>>> Ts = TypeVarTuple('Ts')
>>> is_typevartuple(Ts)
True
```
"""

is_union = _compile_identity_check_function('Union', 'is_union')
is_union.__doc__ = """
Return whether the argument is the [`Union`][typing.Union] [special form][].

This function can also be used to check for the [`Optional`][typing.Optional] [special form][],
as at runtime, `Optional[int]` is equivalent to `Union[int, None]`.

```pycon
>>> is_union(Union)
True
>>> is_union(Union[int, str])
False
```

!!! warning
    This does not check for unions using the [new syntax][types-union] (e.g. `int | str`).
"""


def is_namedtuple(obj: Any, /) -> bool:
    """Return whether the argument is a named tuple type.

    This includes [`NamedTuple`][typing.NamedTuple] subclasses and classes created from the
    [`collections.namedtuple`][] factory function.

    ```pycon
    >>> class User(NamedTuple):
    ...     name: str
    ...
    >>> is_namedtuple(User)
    True
    >>> City = collections.namedtuple('City', [])
    >>> is_namedtuple(City)
    True
    >>> is_namedtuple(NamedTuple)
    False
    ```
    """
    return isinstance(obj, type) and issubclass(obj, tuple) and hasattr(obj, '_fields')  # pyright: ignore[reportUnknownArgumentType]


# TypedDict?

# BinaryIO? IO? TextIO?

is_literalstring = _compile_identity_check_function('LiteralString', 'is_literalstring')
is_literalstring.__doc__ = """
Return whether the argument is the [`LiteralString`][typing.LiteralString] [special form][].

```pycon
>>> is_literalstring(LiteralString)
True
```
"""

is_never = _compile_identity_check_function('Never', 'is_never')
is_never.__doc__ = """
Return whether the argument is the [`Never`][typing.Never] [special form][].

```pycon
>>> is_never(Never)
True
```
"""

if sys.version_info >= (3, 10):
    is_newtype = _compile_isinstance_check_function('NewType', 'is_newtype')
else:  # On Python 3.10, `NewType` is a function.

    def is_newtype(obj: Any, /) -> bool:
        return hasattr(obj, '__supertype__')


is_newtype.__doc__ = """
Return whether the argument is a [`NewType`][typing.NewType].

```pycon
>>> UserId = NewType("UserId", int)
>>> is_newtype(UserId)
True
```
"""

is_nodefault = _compile_identity_check_function('NoDefault', 'is_nodefault')
is_nodefault.__doc__ = """
Return whether the argument is the [`NoDefault`][typing.NoDefault] sentinel object.

```pycon
>>> is_nodefault(NoDefault)
True
```
"""

is_noreturn = _compile_identity_check_function('NoReturn', 'is_noreturn')
is_noreturn.__doc__ = """
Return whether the argument is the [`NoReturn`][typing.NoReturn] [special form][].

```pycon
>>> is_noreturn(NoReturn)
True
>>> is_noreturn(Never)
False
```
"""

is_notrequired = _compile_identity_check_function('NotRequired', 'is_notrequired')
is_notrequired.__doc__ = """
Return whether the argument is the [`NotRequired`][typing.NotRequired] [special form][].

```pycon
>>> is_notrequired(NotRequired)
True
```
"""

is_paramspecargs = _compile_isinstance_check_function('ParamSpecArgs', 'is_paramspecargs')
is_paramspecargs.__doc__ = """
Return whether the argument is an instance of [`ParamSpecArgs`][typing.ParamSpecArgs].

```pycon
>>> P = ParamSpec('P')
>>> is_paramspecargs(P.args)
True
```
"""

is_paramspeckwargs = _compile_isinstance_check_function('ParamSpecKwargs', 'is_paramspeckwargs')
is_paramspeckwargs.__doc__ = """
Return whether the argument is an instance of [`ParamSpecKwargs`][typing.ParamSpecKwargs].

```pycon
>>> P = ParamSpec('P')
>>> is_paramspeckwargs(P.kwargs)
True
```
"""

is_readonly = _compile_identity_check_function('ReadOnly', 'is_readonly')
is_readonly.__doc__ = """
Return whether the argument is the [`ReadOnly`][typing.ReadOnly] [special form][].

```pycon
>>> is_readonly(ReadOnly)
True
```
"""

is_required = _compile_identity_check_function('Required', 'is_required')
is_required.__doc__ = """
Return whether the argument is the [`Required`][typing.Required] [special form][].

```pycon
>>> is_required(Required)
True
```
"""

is_self = _compile_identity_check_function('Self', 'is_self')
is_self.__doc__ = """
Return whether the argument is the [`Self`][typing.Self] [special form][].

```pycon
>>> is_self(Self)
True
```
"""

# TYPE_CHECKING?

is_typealias = _compile_identity_check_function('TypeAlias', 'is_typealias')
is_typealias.__doc__ = """
Return whether the argument is the [`TypeAlias`][typing.TypeAlias] [special form][].

```pycon
>>> is_typealias(TypeAlias)
True
```
"""

is_typeguard = _compile_identity_check_function('TypeGuard', 'is_typeguard')
is_typeguard.__doc__ = """
Return whether the argument is the [`TypeGuard`][typing.TypeGuard] [special form][].

```pycon
>>> is_typeguard(TypeGuard)
True
```
"""

is_typeis = _compile_identity_check_function('TypeIs', 'is_typeis')
is_typeis.__doc__ = """
Return whether the argument is the [`TypeIs`][typing.TypeIs] [special form][].

```pycon
>>> is_typeis(TypeIs)
True
```
"""

_is_typealiastype_inner = _compile_isinstance_check_function('TypeAliasType', '_is_typealiastype_inner')


if _IS_PY310:
    # Parameterized PEP 695 type aliases are instances of `types.GenericAlias` in typing_extensions>=4.13.0.
    # On Python 3.10, with `Alias[int]` being such an instance of `GenericAlias`,
    # `isinstance(Alias[int], TypeAliasType)` returns `True`.
    # See https://github.com/python/cpython/issues/89828.
    def is_typealiastype(obj: Any, /) -> 'TypeIs[TypeAliasType]':
        return type(obj) is not GenericAlias and _is_typealiastype_inner(obj)
else:
    is_typealiastype = _compile_isinstance_check_function('TypeAliasType', 'is_typealiastype')

is_typealiastype.__doc__ = """
Return whether the argument is a [`TypeAliasType`][typing.TypeAliasType] instance.

```pycon
>>> type MyInt = int
>>> is_typealiastype(MyInt)
True
>>> MyStr = TypeAliasType("MyStr", str)
>>> is_typealiastype(MyStr):
True
>>> type MyList[T] = list[T]
>>> is_typealiastype(MyList[int])
False
```
"""

is_unpack = _compile_identity_check_function('Unpack', 'is_unpack')
is_unpack.__doc__ = """
Return whether the argument is the [`Unpack`][typing.Unpack] [special form][].

```pycon
>>> is_unpack(Unpack)
True
>>> is_unpack(Unpack[Ts])
False
```
"""


if sys.version_info >= (3, 13):

    def is_deprecated(obj: Any, /) -> 'TypeIs[deprecated]':
        return isinstance(obj, (warnings.deprecated, typing_extensions.deprecated))

else:

    def is_deprecated(obj: Any, /) -> 'TypeIs[deprecated]':
        return isinstance(obj, typing_extensions.deprecated)


is_deprecated.__doc__ = """
Return whether the argument is a [`deprecated`][warnings.deprecated] instance.

This also includes the [`typing_extensions` backport][typing_extensions.deprecated].

```pycon
>>> is_deprecated(warnings.deprecated('message'))
True
>>> is_deprecated(typing_extensions.deprecated('message'))
True
```
"""


# Aliases defined in the `typing` module using `typing._SpecialGenericAlias` (itself aliased as `alias()`):
DEPRECATED_ALIASES: Final[dict[Any, type[Any]]] = {
    typing.Hashable: collections.abc.Hashable,
    typing.Awaitable: collections.abc.Awaitable,
    typing.Coroutine: collections.abc.Coroutine,
    typing.AsyncIterable: collections.abc.AsyncIterable,
    typing.AsyncIterator: collections.abc.AsyncIterator,
    typing.Iterable: collections.abc.Iterable,
    typing.Iterator: collections.abc.Iterator,
    typing.Reversible: collections.abc.Reversible,
    typing.Sized: collections.abc.Sized,
    typing.Container: collections.abc.Container,
    typing.Collection: collections.abc.Collection,
    # type ignore reason: https://github.com/python/typeshed/issues/6257:
    typing.Callable: collections.abc.Callable,  # pyright: ignore[reportAssignmentType, reportUnknownMemberType]
    typing.AbstractSet: collections.abc.Set,
    typing.MutableSet: collections.abc.MutableSet,
    typing.Mapping: collections.abc.Mapping,
    typing.MutableMapping: collections.abc.MutableMapping,
    typing.Sequence: collections.abc.Sequence,
    typing.MutableSequence: collections.abc.MutableSequence,
    typing.Tuple: tuple,
    typing.List: list,
    typing.Deque: collections.deque,
    typing.Set: set,
    typing.FrozenSet: frozenset,
    typing.MappingView: collections.abc.MappingView,
    typing.KeysView: collections.abc.KeysView,
    typing.ItemsView: collections.abc.ItemsView,
    typing.ValuesView: collections.abc.ValuesView,
    typing.Dict: dict,
    typing.DefaultDict: collections.defaultdict,
    typing.OrderedDict: collections.OrderedDict,
    typing.Counter: collections.Counter,
    typing.ChainMap: collections.ChainMap,
    typing.Generator: collections.abc.Generator,
    typing.AsyncGenerator: collections.abc.AsyncGenerator,
    typing.Type: type,
    # Defined in `typing.__getattr__`:
    typing.Pattern: re.Pattern,
    typing.Match: re.Match,
    typing.ContextManager: contextlib.AbstractContextManager,
    typing.AsyncContextManager: contextlib.AbstractAsyncContextManager,
    # Skipped: `ByteString` (deprecated, removed in 3.14)
}
"""A mapping between the deprecated typing aliases to their replacement, as per [PEP 585](https://peps.python.org/pep-0585/)."""


# Add the `typing_extensions` aliases:
for alias, target in list(DEPRECATED_ALIASES.items()):
    # Use `alias.__name__` when we drop support for Python 3.9
    if (te_alias := getattr(typing_extensions, alias._name, None)) is not None:
        DEPRECATED_ALIASES[te_alias] = target

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\backend_gtk3.py ===
import functools
import logging
import os
from pathlib import Path

import matplotlib as mpl
from matplotlib import _api, backend_tools, cbook
from matplotlib.backend_bases import (
    ToolContainerBase, MouseButton,
    CloseEvent, KeyEvent, LocationEvent, MouseEvent, ResizeEvent)

try:
    import gi
except ImportError as err:
    raise ImportError("The GTK3 backends require PyGObject") from err

try:
    # :raises ValueError: If module/version is already loaded, already
    # required, or unavailable.
    gi.require_version("Gtk", "3.0")
except ValueError as e:
    # in this case we want to re-raise as ImportError so the
    # auto-backend selection logic correctly skips.
    raise ImportError(e) from e

from gi.repository import Gio, GLib, GObject, Gtk, Gdk
from . import _backend_gtk
from ._backend_gtk import (  # noqa: F401 # pylint: disable=W0611
    _BackendGTK, _FigureCanvasGTK, _FigureManagerGTK, _NavigationToolbar2GTK,
    TimerGTK as TimerGTK3,
)


_log = logging.getLogger(__name__)


@functools.cache
def _mpl_to_gtk_cursor(mpl_cursor):
    return Gdk.Cursor.new_from_name(
        Gdk.Display.get_default(),
        _backend_gtk.mpl_to_gtk_cursor_name(mpl_cursor))


class FigureCanvasGTK3(_FigureCanvasGTK, Gtk.DrawingArea):
    required_interactive_framework = "gtk3"
    manager_class = _api.classproperty(lambda cls: FigureManagerGTK3)
    # Setting this as a static constant prevents
    # this resulting expression from leaking
    event_mask = (Gdk.EventMask.BUTTON_PRESS_MASK
                  | Gdk.EventMask.BUTTON_RELEASE_MASK
                  | Gdk.EventMask.EXPOSURE_MASK
                  | Gdk.EventMask.KEY_PRESS_MASK
                  | Gdk.EventMask.KEY_RELEASE_MASK
                  | Gdk.EventMask.ENTER_NOTIFY_MASK
                  | Gdk.EventMask.LEAVE_NOTIFY_MASK
                  | Gdk.EventMask.POINTER_MOTION_MASK
                  | Gdk.EventMask.SCROLL_MASK)

    def __init__(self, figure=None):
        super().__init__(figure=figure)

        self._idle_draw_id = 0
        self._rubberband_rect = None

        self.connect('scroll_event',         self.scroll_event)
        self.connect('button_press_event',   self.button_press_event)
        self.connect('button_release_event', self.button_release_event)
        self.connect('configure_event',      self.configure_event)
        self.connect('screen-changed',       self._update_device_pixel_ratio)
        self.connect('notify::scale-factor', self._update_device_pixel_ratio)
        self.connect('draw',                 self.on_draw_event)
        self.connect('draw',                 self._post_draw)
        self.connect('key_press_event',      self.key_press_event)
        self.connect('key_release_event',    self.key_release_event)
        self.connect('motion_notify_event',  self.motion_notify_event)
        self.connect('enter_notify_event',   self.enter_notify_event)
        self.connect('leave_notify_event',   self.leave_notify_event)
        self.connect('size_allocate',        self.size_allocate)

        self.set_events(self.__class__.event_mask)

        self.set_can_focus(True)

        css = Gtk.CssProvider()
        css.load_from_data(b".matplotlib-canvas { background-color: white; }")
        style_ctx = self.get_style_context()
        style_ctx.add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        style_ctx.add_class("matplotlib-canvas")

    def destroy(self):
        CloseEvent("close_event", self)._process()

    def set_cursor(self, cursor):
        # docstring inherited
        window = self.get_property("window")
        if window is not None:
            window.set_cursor(_mpl_to_gtk_cursor(cursor))
            context = GLib.MainContext.default()
            context.iteration(True)

    def _mpl_coords(self, event=None):
        """
        Convert the position of a GTK event, or of the current cursor position
        if *event* is None, to Matplotlib coordinates.

        GTK use logical pixels, but the figure is scaled to physical pixels for
        rendering.  Transform to physical pixels so that all of the down-stream
        transforms work as expected.

        Also, the origin is different and needs to be corrected.
        """
        if event is None:
            window = self.get_window()
            t, x, y, state = window.get_device_position(
                window.get_display().get_device_manager().get_client_pointer())
        else:
            x, y = event.x, event.y
        x = x * self.device_pixel_ratio
        # flip y so y=0 is bottom of canvas
        y = self.figure.bbox.height - y * self.device_pixel_ratio
        return x, y

    def scroll_event(self, widget, event):
        step = 1 if event.direction == Gdk.ScrollDirection.UP else -1
        MouseEvent("scroll_event", self,
                   *self._mpl_coords(event), step=step,
                   modifiers=self._mpl_modifiers(event.state),
                   guiEvent=event)._process()
        return False  # finish event propagation?

    def button_press_event(self, widget, event):
        MouseEvent("button_press_event", self,
                   *self._mpl_coords(event), event.button,
                   modifiers=self._mpl_modifiers(event.state),
                   guiEvent=event)._process()
        return False  # finish event propagation?

    def button_release_event(self, widget, event):
        MouseEvent("button_release_event", self,
                   *self._mpl_coords(event), event.button,
                   modifiers=self._mpl_modifiers(event.state),
                   guiEvent=event)._process()
        return False  # finish event propagation?

    def key_press_event(self, widget, event):
        KeyEvent("key_press_event", self,
                 self._get_key(event), *self._mpl_coords(),
                 guiEvent=event)._process()
        return True  # stop event propagation

    def key_release_event(self, widget, event):
        KeyEvent("key_release_event", self,
                 self._get_key(event), *self._mpl_coords(),
                 guiEvent=event)._process()
        return True  # stop event propagation

    def motion_notify_event(self, widget, event):
        MouseEvent("motion_notify_event", self, *self._mpl_coords(event),
                   buttons=self._mpl_buttons(event.state),
                   modifiers=self._mpl_modifiers(event.state),
                   guiEvent=event)._process()
        return False  # finish event propagation?

    def enter_notify_event(self, widget, event):
        gtk_mods = Gdk.Keymap.get_for_display(
            self.get_display()).get_modifier_state()
        LocationEvent("figure_enter_event", self, *self._mpl_coords(event),
                      modifiers=self._mpl_modifiers(gtk_mods),
                      guiEvent=event)._process()

    def leave_notify_event(self, widget, event):
        gtk_mods = Gdk.Keymap.get_for_display(
            self.get_display()).get_modifier_state()
        LocationEvent("figure_leave_event", self, *self._mpl_coords(event),
                      modifiers=self._mpl_modifiers(gtk_mods),
                      guiEvent=event)._process()

    def size_allocate(self, widget, allocation):
        dpival = self.figure.dpi
        winch = allocation.width * self.device_pixel_ratio / dpival
        hinch = allocation.height * self.device_pixel_ratio / dpival
        self.figure.set_size_inches(winch, hinch, forward=False)
        ResizeEvent("resize_event", self)._process()
        self.draw_idle()

    @staticmethod
    def _mpl_buttons(event_state):
        modifiers = [
            (MouseButton.LEFT, Gdk.ModifierType.BUTTON1_MASK),
            (MouseButton.MIDDLE, Gdk.ModifierType.BUTTON2_MASK),
            (MouseButton.RIGHT, Gdk.ModifierType.BUTTON3_MASK),
            (MouseButton.BACK, Gdk.ModifierType.BUTTON4_MASK),
            (MouseButton.FORWARD, Gdk.ModifierType.BUTTON5_MASK),
        ]
        # State *before* press/release.
        return [name for name, mask in modifiers if event_state & mask]

    @staticmethod
    def _mpl_modifiers(event_state, *, exclude=None):
        modifiers = [
            ("ctrl", Gdk.ModifierType.CONTROL_MASK, "control"),
            ("alt", Gdk.ModifierType.MOD1_MASK, "alt"),
            ("shift", Gdk.ModifierType.SHIFT_MASK, "shift"),
            ("super", Gdk.ModifierType.MOD4_MASK, "super"),
        ]
        return [name for name, mask, key in modifiers
                if exclude != key and event_state & mask]

    def _get_key(self, event):
        unikey = chr(Gdk.keyval_to_unicode(event.keyval))
        key = cbook._unikey_or_keysym_to_mplkey(
            unikey, Gdk.keyval_name(event.keyval))
        mods = self._mpl_modifiers(event.state, exclude=key)
        if "shift" in mods and unikey.isprintable():
            mods.remove("shift")
        return "+".join([*mods, key])

    def _update_device_pixel_ratio(self, *args, **kwargs):
        # We need to be careful in cases with mixed resolution displays if
        # device_pixel_ratio changes.
        if self._set_device_pixel_ratio(self.get_scale_factor()):
            # The easiest way to resize the canvas is to emit a resize event
            # since we implement all the logic for resizing the canvas for that
            # event.
            self.queue_resize()
            self.queue_draw()

    def configure_event(self, widget, event):
        if widget.get_property("window") is None:
            return
        w = event.width * self.device_pixel_ratio
        h = event.height * self.device_pixel_ratio
        if w < 3 or h < 3:
            return  # empty fig
        # resize the figure (in inches)
        dpi = self.figure.dpi
        self.figure.set_size_inches(w / dpi, h / dpi, forward=False)
        return False  # finish event propagation?

    def _draw_rubberband(self, rect):
        self._rubberband_rect = rect
        # TODO: Only update the rubberband area.
        self.queue_draw()

    def _post_draw(self, widget, ctx):
        if self._rubberband_rect is None:
            return

        x0, y0, w, h = (dim / self.device_pixel_ratio
                        for dim in self._rubberband_rect)
        x1 = x0 + w
        y1 = y0 + h

        # Draw the lines from x0, y0 towards x1, y1 so that the
        # dashes don't "jump" when moving the zoom box.
        ctx.move_to(x0, y0)
        ctx.line_to(x0, y1)
        ctx.move_to(x0, y0)
        ctx.line_to(x1, y0)
        ctx.move_to(x0, y1)
        ctx.line_to(x1, y1)
        ctx.move_to(x1, y0)
        ctx.line_to(x1, y1)

        ctx.set_antialias(1)
        ctx.set_line_width(1)
        ctx.set_dash((3, 3), 0)
        ctx.set_source_rgb(0, 0, 0)
        ctx.stroke_preserve()

        ctx.set_dash((3, 3), 3)
        ctx.set_source_rgb(1, 1, 1)
        ctx.stroke()

    def on_draw_event(self, widget, ctx):
        # to be overwritten by GTK3Agg or GTK3Cairo
        pass

    def draw(self):
        # docstring inherited
        if self.is_drawable():
            self.queue_draw()

    def draw_idle(self):
        # docstring inherited
        if self._idle_draw_id != 0:
            return
        def idle_draw(*args):
            try:
                self.draw()
            finally:
                self._idle_draw_id = 0
            return False
        self._idle_draw_id = GLib.idle_add(idle_draw)

    def flush_events(self):
        # docstring inherited
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(True)


class NavigationToolbar2GTK3(_NavigationToolbar2GTK, Gtk.Toolbar):
    def __init__(self, canvas):
        GObject.GObject.__init__(self)

        self.set_style(Gtk.ToolbarStyle.ICONS)

        self._gtk_ids = {}
        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                self.insert(Gtk.SeparatorToolItem(), -1)
                continue
            image = Gtk.Image.new_from_gicon(
                Gio.Icon.new_for_string(
                    str(cbook._get_data_path('images',
                                             f'{image_file}-symbolic.svg'))),
                Gtk.IconSize.LARGE_TOOLBAR)
            self._gtk_ids[text] = button = (
                Gtk.ToggleToolButton() if callback in ['zoom', 'pan'] else
                Gtk.ToolButton())
            button.set_label(text)
            button.set_icon_widget(image)
            # Save the handler id, so that we can block it as needed.
            button._signal_handler = button.connect(
                'clicked', getattr(self, callback))
            button.set_tooltip_text(tooltip_text)
            self.insert(button, -1)

        # This filler item ensures the toolbar is always at least two text
        # lines high. Otherwise the canvas gets redrawn as the mouse hovers
        # over images because those use two-line messages which resize the
        # toolbar.
        toolitem = Gtk.ToolItem()
        self.insert(toolitem, -1)
        label = Gtk.Label()
        label.set_markup(
            '<small>\N{NO-BREAK SPACE}\n\N{NO-BREAK SPACE}</small>')
        toolitem.set_expand(True)  # Push real message to the right.
        toolitem.add(label)

        toolitem = Gtk.ToolItem()
        self.insert(toolitem, -1)
        self.message = Gtk.Label()
        self.message.set_justify(Gtk.Justification.RIGHT)
        toolitem.add(self.message)

        self.show_all()

        _NavigationToolbar2GTK.__init__(self, canvas)

    def save_figure(self, *args):
        dialog = Gtk.FileChooserDialog(
            title="Save the figure",
            transient_for=self.canvas.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                     Gtk.STOCK_SAVE,   Gtk.ResponseType.OK),
        )
        for name, fmts \
                in self.canvas.get_supported_filetypes_grouped().items():
            ff = Gtk.FileFilter()
            ff.set_name(name)
            for fmt in fmts:
                ff.add_pattern(f'*.{fmt}')
            dialog.add_filter(ff)
            if self.canvas.get_default_filetype() in fmts:
                dialog.set_filter(ff)

        @functools.partial(dialog.connect, "notify::filter")
        def on_notify_filter(*args):
            name = dialog.get_filter().get_name()
            fmt = self.canvas.get_supported_filetypes_grouped()[name][0]
            dialog.set_current_name(
                str(Path(dialog.get_current_name()).with_suffix(f'.{fmt}')))

        dialog.set_current_folder(mpl.rcParams["savefig.directory"])
        dialog.set_current_name(self.canvas.get_default_filename())
        dialog.set_do_overwrite_confirmation(True)

        response = dialog.run()
        fname = dialog.get_filename()
        ff = dialog.get_filter()  # Doesn't autoadjust to filename :/
        fmt = self.canvas.get_supported_filetypes_grouped()[ff.get_name()][0]
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return None
        # Save dir for next time, unless empty str (which means use cwd).
        if mpl.rcParams['savefig.directory']:
            mpl.rcParams['savefig.directory'] = os.path.dirname(fname)
        try:
            self.canvas.figure.savefig(fname, format=fmt)
            return fname
        except Exception as e:
            dialog = Gtk.MessageDialog(
                transient_for=self.canvas.get_toplevel(), text=str(e),
                message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK)
            dialog.run()
            dialog.destroy()


class ToolbarGTK3(ToolContainerBase, Gtk.Box):
    _icon_extension = '-symbolic.svg'

    def __init__(self, toolmanager):
        ToolContainerBase.__init__(self, toolmanager)
        Gtk.Box.__init__(self)
        self.set_property('orientation', Gtk.Orientation.HORIZONTAL)
        self._message = Gtk.Label()
        self._message.set_justify(Gtk.Justification.RIGHT)
        self.pack_end(self._message, False, False, 0)
        self.show_all()
        self._groups = {}
        self._toolitems = {}

    def add_toolitem(self, name, group, position, image_file, description,
                     toggle):
        if toggle:
            button = Gtk.ToggleToolButton()
        else:
            button = Gtk.ToolButton()
        button.set_label(name)

        if image_file is not None:
            image = Gtk.Image.new_from_gicon(
                Gio.Icon.new_for_string(image_file),
                Gtk.IconSize.LARGE_TOOLBAR)
            button.set_icon_widget(image)

        if position is None:
            position = -1

        self._add_button(button, group, position)
        signal = button.connect('clicked', self._call_tool, name)
        button.set_tooltip_text(description)
        button.show_all()
        self._toolitems.setdefault(name, [])
        self._toolitems[name].append((button, signal))

    def _add_button(self, button, group, position):
        if group not in self._groups:
            if self._groups:
                self._add_separator()
            toolbar = Gtk.Toolbar()
            toolbar.set_style(Gtk.ToolbarStyle.ICONS)
            self.pack_start(toolbar, False, False, 0)
            toolbar.show_all()
            self._groups[group] = toolbar
        self._groups[group].insert(button, position)

    def _call_tool(self, btn, name):
        self.trigger_tool(name)

    def toggle_toolitem(self, name, toggled):
        if name not in self._toolitems:
            return
        for toolitem, signal in self._toolitems[name]:
            toolitem.handler_block(signal)
            toolitem.set_active(toggled)
            toolitem.handler_unblock(signal)

    def remove_toolitem(self, name):
        for toolitem, _signal in self._toolitems.pop(name, []):
            for group in self._groups:
                if toolitem in self._groups[group]:
                    self._groups[group].remove(toolitem)

    def _add_separator(self):
        sep = Gtk.Separator()
        sep.set_property("orientation", Gtk.Orientation.VERTICAL)
        self.pack_start(sep, False, True, 0)
        sep.show_all()

    def set_message(self, s):
        self._message.set_label(s)


@backend_tools._register_tool_class(FigureCanvasGTK3)
class SaveFigureGTK3(backend_tools.SaveFigureBase):
    def trigger(self, *args, **kwargs):
        NavigationToolbar2GTK3.save_figure(
            self._make_classic_style_pseudo_toolbar())


@backend_tools._register_tool_class(FigureCanvasGTK3)
class HelpGTK3(backend_tools.ToolHelpBase):
    def _normalize_shortcut(self, key):
        """
        Convert Matplotlib key presses to GTK+ accelerator identifiers.

        Related to `FigureCanvasGTK3._get_key`.
        """
        special = {
            'backspace': 'BackSpace',
            'pagedown': 'Page_Down',
            'pageup': 'Page_Up',
            'scroll_lock': 'Scroll_Lock',
        }

        parts = key.split('+')
        mods = ['<' + mod + '>' for mod in parts[:-1]]
        key = parts[-1]

        if key in special:
            key = special[key]
        elif len(key) > 1:
            key = key.capitalize()
        elif key.isupper():
            mods += ['<shift>']

        return ''.join(mods) + key

    def _is_valid_shortcut(self, key):
        """
        Check for a valid shortcut to be displayed.

        - GTK will never send 'cmd+' (see `FigureCanvasGTK3._get_key`).
        - The shortcut window only shows keyboard shortcuts, not mouse buttons.
        """
        return 'cmd+' not in key and not key.startswith('MouseButton.')

    def _show_shortcuts_window(self):
        section = Gtk.ShortcutsSection()

        for name, tool in sorted(self.toolmanager.tools.items()):
            if not tool.description:
                continue

            # Putting everything in a separate group allows GTK to
            # automatically split them into separate columns/pages, which is
            # useful because we have lots of shortcuts, some with many keys
            # that are very wide.
            group = Gtk.ShortcutsGroup()
            section.add(group)
            # A hack to remove the title since we have no group naming.
            group.forall(lambda widget, data: widget.set_visible(False), None)

            shortcut = Gtk.ShortcutsShortcut(
                accelerator=' '.join(
                    self._normalize_shortcut(key)
                    for key in self.toolmanager.get_tool_keymap(name)
                    if self._is_valid_shortcut(key)),
                title=tool.name,
                subtitle=tool.description)
            group.add(shortcut)

        window = Gtk.ShortcutsWindow(
            title='Help',
            modal=True,
            transient_for=self._figure.canvas.get_toplevel())
        section.show()  # Must be done explicitly before add!
        window.add(section)

        window.show_all()

    def _show_shortcuts_dialog(self):
        dialog = Gtk.MessageDialog(
            self._figure.canvas.get_toplevel(),
            0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, self._get_help_text(),
            title="Help")
        dialog.run()
        dialog.destroy()

    def trigger(self, *args):
        if Gtk.check_version(3, 20, 0) is None:
            self._show_shortcuts_window()
        else:
            self._show_shortcuts_dialog()


@backend_tools._register_tool_class(FigureCanvasGTK3)
class ToolCopyToClipboardGTK3(backend_tools.ToolCopyToClipboardBase):
    def trigger(self, *args, **kwargs):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        window = self.canvas.get_window()
        x, y, width, height = window.get_geometry()
        pb = Gdk.pixbuf_get_from_window(window, x, y, width, height)
        clipboard.set_image(pb)


Toolbar = ToolbarGTK3
backend_tools._register_tool_class(
    FigureCanvasGTK3, _backend_gtk.ConfigureSubplotsGTK)
backend_tools._register_tool_class(
    FigureCanvasGTK3, _backend_gtk.RubberbandGTK)


class FigureManagerGTK3(_FigureManagerGTK):
    _toolbar2_class = NavigationToolbar2GTK3
    _toolmanager_toolbar_class = ToolbarGTK3


@_BackendGTK.export
class _BackendGTK3(_BackendGTK):
    FigureCanvas = FigureCanvasGTK3
    FigureManager = FigureManagerGTK3

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\discuss_service\async_client.py ===
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

from google.ai.generativelanguage_v1beta2 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.AsyncRetry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.AsyncRetry, object, None]  # type: ignore

from google.ai.generativelanguage_v1beta2.types import discuss_service, safety

from .client import DiscussServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, DiscussServiceTransport
from .transports.grpc_asyncio import DiscussServiceGrpcAsyncIOTransport


class DiscussServiceAsyncClient:
    """An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.
    """

    _client: DiscussServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = DiscussServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = DiscussServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = DiscussServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = DiscussServiceClient._DEFAULT_UNIVERSE

    model_path = staticmethod(DiscussServiceClient.model_path)
    parse_model_path = staticmethod(DiscussServiceClient.parse_model_path)
    common_billing_account_path = staticmethod(
        DiscussServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        DiscussServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(DiscussServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(
        DiscussServiceClient.parse_common_folder_path
    )
    common_organization_path = staticmethod(
        DiscussServiceClient.common_organization_path
    )
    parse_common_organization_path = staticmethod(
        DiscussServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(DiscussServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        DiscussServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(DiscussServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        DiscussServiceClient.parse_common_location_path
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
            DiscussServiceAsyncClient: The constructed client.
        """
        return DiscussServiceClient.from_service_account_info.__func__(DiscussServiceAsyncClient, info, *args, **kwargs)  # type: ignore

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
            DiscussServiceAsyncClient: The constructed client.
        """
        return DiscussServiceClient.from_service_account_file.__func__(DiscussServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

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
        return DiscussServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> DiscussServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            DiscussServiceTransport: The transport used by the client instance.
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
        type(DiscussServiceClient).get_transport_class, type(DiscussServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, DiscussServiceTransport, Callable[..., DiscussServiceTransport]]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the discuss service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,DiscussServiceTransport,Callable[..., DiscussServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the DiscussServiceTransport constructor.
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
        self._client = DiscussServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def generate_message(
        self,
        request: Optional[Union[discuss_service.GenerateMessageRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[discuss_service.MessagePrompt] = None,
        temperature: Optional[float] = None,
        candidate_count: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> discuss_service.GenerateMessageResponse:
        r"""Generates a response from the model given an input
        ``MessagePrompt``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta2

            async def sample_generate_message():
                # Create a client
                client = generativelanguage_v1beta2.DiscussServiceAsyncClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta2.MessagePrompt()
                prompt.messages.content = "content_value"

                request = generativelanguage_v1beta2.GenerateMessageRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = await client.generate_message(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta2.types.GenerateMessageRequest, dict]]):
                The request object. Request to generate a message
                response from the model.
            model (:class:`str`):
                Required. The name of the model to use.

                Format: ``name=models/{model}``.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (:class:`google.ai.generativelanguage_v1beta2.types.MessagePrompt`):
                Required. The structured textual
                input given to the model as a prompt.
                Given a
                prompt, the model will return what it
                predicts is the next message in the
                discussion.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            temperature (:class:`float`):
                Optional. Controls the randomness of the output.

                Values can range over ``[0.0,1.0]``, inclusive. A value
                closer to ``1.0`` will produce responses that are more
                varied, while a value closer to ``0.0`` will typically
                result in less surprising responses from the model.

                This corresponds to the ``temperature`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            candidate_count (:class:`int`):
                Optional. The number of generated response messages to
                return.

                This value must be between ``[1, 8]``, inclusive. If
                unset, this will default to ``1``.

                This corresponds to the ``candidate_count`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_p (:class:`float`):
                Optional. The maximum cumulative probability of tokens
                to consider when sampling.

                The model uses combined Top-k and nucleus sampling.

                Nucleus sampling considers the smallest set of tokens
                whose probability sum is at least ``top_p``.

                This corresponds to the ``top_p`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_k (:class:`int`):
                Optional. The maximum number of tokens to consider when
                sampling.

                The model uses combined Top-k and nucleus sampling.

                Top-k sampling considers the set of ``top_k`` most
                probable tokens.

                This corresponds to the ``top_k`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta2.types.GenerateMessageResponse:
                The response from the model.

                This includes candidate messages and
                conversation history in the form of
                chronologically-ordered messages.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any(
            [model, prompt, temperature, candidate_count, top_p, top_k]
        )
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, discuss_service.GenerateMessageRequest):
            request = discuss_service.GenerateMessageRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if prompt is not None:
            request.prompt = prompt
        if temperature is not None:
            request.temperature = temperature
        if candidate_count is not None:
            request.candidate_count = candidate_count
        if top_p is not None:
            request.top_p = top_p
        if top_k is not None:
            request.top_k = top_k

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.generate_message
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    async def count_message_tokens(
        self,
        request: Optional[
            Union[discuss_service.CountMessageTokensRequest, dict]
        ] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[discuss_service.MessagePrompt] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> discuss_service.CountMessageTokensResponse:
        r"""Runs a model's tokenizer on a string and returns the
        token count.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta2

            async def sample_count_message_tokens():
                # Create a client
                client = generativelanguage_v1beta2.DiscussServiceAsyncClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta2.MessagePrompt()
                prompt.messages.content = "content_value"

                request = generativelanguage_v1beta2.CountMessageTokensRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = await client.count_message_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta2.types.CountMessageTokensRequest, dict]]):
                The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
            model (:class:`str`):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (:class:`google.ai.generativelanguage_v1beta2.types.MessagePrompt`):
                Required. The prompt, whose token
                count is to be returned.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta2.types.CountMessageTokensResponse:
                A response from CountMessageTokens.

                   It returns the model's token_count for the prompt.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, prompt])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, discuss_service.CountMessageTokensRequest):
            request = discuss_service.CountMessageTokensRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if prompt is not None:
            request.prompt = prompt

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.count_message_tokens
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    async def __aenter__(self) -> "DiscussServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("DiscussServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\ttProgram.py ===
"""ttLib.tables.ttProgram.py -- Assembler/disassembler for TrueType bytecode programs."""

from __future__ import annotations

from fontTools.misc.textTools import num2binary, binary2num, readHex, strjoin
import array
from io import StringIO
from typing import List
import re
import logging


log = logging.getLogger(__name__)

# fmt: off

# first, the list of instructions that eat bytes or words from the instruction stream

streamInstructions = [
#
#   opcode  mnemonic   argBits    descriptive name         pops  pushes         eats from instruction stream          pushes
#
    (0x40,  'NPUSHB',        0,   'PushNBytes',              0, -1),    #                      n, b1, b2,...bn      b1,b2...bn
    (0x41,  'NPUSHW',        0,   'PushNWords',              0, -1),    #                       n, w1, w2,...w      w1,w2...wn
    (0xb0,  'PUSHB',         3,   'PushBytes',               0, -1),    #                          b0, b1,..bn  b0, b1, ...,bn
    (0xb8,  'PUSHW',         3,   'PushWords',               0, -1),    #                           w0,w1,..wn   w0 ,w1, ...wn
]


# next,    the list of "normal" instructions

instructions = [
#
#   opcode  mnemonic   argBits     descriptive name        pops  pushes         eats from instruction stream          pushes
#
    (0x7f,  'AA',            0,    'AdjustAngle',            1,  0),    #                                    p               -
    (0x64,  'ABS',           0,    'Absolute',               1,  1),    #                                    n             |n|
    (0x60,  'ADD',           0,    'Add',                    2,  1),    #                               n2, n1       (n1 + n2)
    (0x27,  'ALIGNPTS',      0,    'AlignPts',               2,  0),    #                               p2, p1               -
    (0x3c,  'ALIGNRP',       0,    'AlignRelativePt',       -1,  0),    #             p1, p2, ... , ploopvalue               -
    (0x5a,  'AND',           0,    'LogicalAnd',             2,  1),    #                               e2, e1               b
    (0x2b,  'CALL',          0,    'CallFunction',           1,  0),    #                                    f               -
    (0x67,  'CEILING',       0,    'Ceiling',                1,  1),    #                                    n         ceil(n)
    (0x25,  'CINDEX',        0,    'CopyXToTopStack',        1,  1),    #                                    k              ek
    (0x22,  'CLEAR',         0,    'ClearStack',            -1,  0),    #               all items on the stack               -
    (0x4f,  'DEBUG',         0,    'DebugCall',              1,  0),    #                                    n               -
    (0x73,  'DELTAC1',       0,    'DeltaExceptionC1',      -1,  0),    #    argn, cn, argn-1,cn-1, , arg1, c1               -
    (0x74,  'DELTAC2',       0,    'DeltaExceptionC2',      -1,  0),    #    argn, cn, argn-1,cn-1, , arg1, c1               -
    (0x75,  'DELTAC3',       0,    'DeltaExceptionC3',      -1,  0),    #    argn, cn, argn-1,cn-1, , arg1, c1               -
    (0x5d,  'DELTAP1',       0,    'DeltaExceptionP1',      -1,  0),    #   argn, pn, argn-1, pn-1, , arg1, p1               -
    (0x71,  'DELTAP2',       0,    'DeltaExceptionP2',      -1,  0),    #   argn, pn, argn-1, pn-1, , arg1, p1               -
    (0x72,  'DELTAP3',       0,    'DeltaExceptionP3',      -1,  0),    #   argn, pn, argn-1, pn-1, , arg1, p1               -
    (0x24,  'DEPTH',         0,    'GetDepthStack',          0,  1),    #                                    -               n
    (0x62,  'DIV',           0,    'Divide',                 2,  1),    #                               n2, n1   (n1 * 64)/ n2
    (0x20,  'DUP',           0,    'DuplicateTopStack',      1,  2),    #                                    e            e, e
    (0x59,  'EIF',           0,    'EndIf',                  0,  0),    #                                    -               -
    (0x1b,  'ELSE',          0,    'Else',                   0,  0),    #                                    -               -
    (0x2d,  'ENDF',          0,    'EndFunctionDefinition',  0,  0),    #                                    -               -
    (0x54,  'EQ',            0,    'Equal',                  2,  1),    #                               e2, e1               b
    (0x57,  'EVEN',          0,    'Even',                   1,  1),    #                                    e               b
    (0x2c,  'FDEF',          0,    'FunctionDefinition',     1,  0),    #                                    f               -
    (0x4e,  'FLIPOFF',       0,    'SetAutoFlipOff',         0,  0),    #                                    -               -
    (0x4d,  'FLIPON',        0,    'SetAutoFlipOn',          0,  0),    #                                    -               -
    (0x80,  'FLIPPT',        0,    'FlipPoint',             -1,  0),    #              p1, p2, ..., ploopvalue               -
    (0x82,  'FLIPRGOFF',     0,    'FlipRangeOff',           2,  0),    #                                 h, l               -
    (0x81,  'FLIPRGON',      0,    'FlipRangeOn',            2,  0),    #                                 h, l               -
    (0x66,  'FLOOR',         0,    'Floor',                  1,  1),    #                                    n        floor(n)
    (0x46,  'GC',            1,    'GetCoordOnPVector',      1,  1),    #                                    p               c
    (0x88,  'GETINFO',       0,    'GetInfo',                1,  1),    #                             selector          result
    (0x91,  'GETVARIATION',  0,    'GetVariation',           0, -1),    #                                    -        a1,..,an
    (0x0d,  'GFV',           0,    'GetFVector',             0,  2),    #                                    -          px, py
    (0x0c,  'GPV',           0,    'GetPVector',             0,  2),    #                                    -          px, py
    (0x52,  'GT',            0,    'GreaterThan',            2,  1),    #                               e2, e1               b
    (0x53,  'GTEQ',          0,    'GreaterThanOrEqual',     2,  1),    #                               e2, e1               b
    (0x89,  'IDEF',          0,    'InstructionDefinition',  1,  0),    #                                    f               -
    (0x58,  'IF',            0,    'If',                     1,  0),    #                                    e               -
    (0x8e,  'INSTCTRL',      0,    'SetInstrExecControl',    2,  0),    #                                 s, v               -
    (0x39,  'IP',            0,    'InterpolatePts',        -1,  0),    #             p1, p2, ... , ploopvalue               -
    (0x0f,  'ISECT',         0,    'MovePtToIntersect',      5,  0),    #                    a1, a0, b1, b0, p               -
    (0x30,  'IUP',           1,    'InterpolateUntPts',      0,  0),    #                                    -               -
    (0x1c,  'JMPR',          0,    'Jump',                   1,  0),    #                               offset               -
    (0x79,  'JROF',          0,    'JumpRelativeOnFalse',    2,  0),    #                            e, offset               -
    (0x78,  'JROT',          0,    'JumpRelativeOnTrue',     2,  0),    #                            e, offset               -
    (0x2a,  'LOOPCALL',      0,    'LoopAndCallFunction',    2,  0),    #                             f, count               -
    (0x50,  'LT',            0,    'LessThan',               2,  1),    #                               e2, e1               b
    (0x51,  'LTEQ',          0,    'LessThenOrEqual',        2,  1),    #                               e2, e1               b
    (0x8b,  'MAX',           0,    'Maximum',                2,  1),    #                               e2, e1     max(e1, e2)
    (0x49,  'MD',            1,    'MeasureDistance',        2,  1),    #                                p2,p1               d
    (0x2e,  'MDAP',          1,    'MoveDirectAbsPt',        1,  0),    #                                    p               -
    (0xc0,  'MDRP',          5,    'MoveDirectRelPt',        1,  0),    #                                    p               -
    (0x3e,  'MIAP',          1,    'MoveIndirectAbsPt',      2,  0),    #                                 n, p               -
    (0x8c,  'MIN',           0,    'Minimum',                2,  1),    #                               e2, e1     min(e1, e2)
    (0x26,  'MINDEX',        0,    'MoveXToTopStack',        1,  1),    #                                    k              ek
    (0xe0,  'MIRP',          5,    'MoveIndirectRelPt',      2,  0),    #                                 n, p               -
    (0x4b,  'MPPEM',         0,    'MeasurePixelPerEm',      0,  1),    #                                    -            ppem
    (0x4c,  'MPS',           0,    'MeasurePointSize',       0,  1),    #                                    -       pointSize
    (0x3a,  'MSIRP',         1,    'MoveStackIndirRelPt',    2,  0),    #                                 d, p               -
    (0x63,  'MUL',           0,    'Multiply',               2,  1),    #                               n2, n1    (n1 * n2)/64
    (0x65,  'NEG',           0,    'Negate',                 1,  1),    #                                    n              -n
    (0x55,  'NEQ',           0,    'NotEqual',               2,  1),    #                               e2, e1               b
    (0x5c,  'NOT',           0,    'LogicalNot',             1,  1),    #                                    e       ( not e )
    (0x6c,  'NROUND',        2,    'NoRound',                1,  1),    #                                   n1              n2
    (0x56,  'ODD',           0,    'Odd',                    1,  1),    #                                    e               b
    (0x5b,  'OR',            0,    'LogicalOr',              2,  1),    #                               e2, e1               b
    (0x21,  'POP',           0,    'PopTopStack',            1,  0),    #                                    e               -
    (0x45,  'RCVT',          0,    'ReadCVT',                1,  1),    #                             location           value
    (0x7d,  'RDTG',          0,    'RoundDownToGrid',        0,  0),    #                                    -               -
    (0x7a,  'ROFF',          0,    'RoundOff',               0,  0),    #                                    -               -
    (0x8a,  'ROLL',          0,    'RollTopThreeStack',      3,  3),    #                                a,b,c           b,a,c
    (0x68,  'ROUND',         2,    'Round',                  1,  1),    #                                   n1              n2
    (0x43,  'RS',            0,    'ReadStore',              1,  1),    #                                    n               v
    (0x3d,  'RTDG',          0,    'RoundToDoubleGrid',      0,  0),    #                                    -               -
    (0x18,  'RTG',           0,    'RoundToGrid',            0,  0),    #                                    -               -
    (0x19,  'RTHG',          0,    'RoundToHalfGrid',        0,  0),    #                                    -               -
    (0x7c,  'RUTG',          0,    'RoundUpToGrid',          0,  0),    #                                    -               -
    (0x77,  'S45ROUND',      0,    'SuperRound45Degrees',    1,  0),    #                                    n               -
    (0x7e,  'SANGW',         0,    'SetAngleWeight',         1,  0),    #                               weight               -
    (0x85,  'SCANCTRL',      0,    'ScanConversionControl',  1,  0),    #                                    n               -
    (0x8d,  'SCANTYPE',      0,    'ScanType',               1,  0),    #                                    n               -
    (0x48,  'SCFS',          0,    'SetCoordFromStackFP',    2,  0),    #                                 c, p               -
    (0x1d,  'SCVTCI',        0,    'SetCVTCutIn',            1,  0),    #                                    n               -
    (0x5e,  'SDB',           0,    'SetDeltaBaseInGState',   1,  0),    #                                    n               -
    (0x86,  'SDPVTL',        1,    'SetDualPVectorToLine',   2,  0),    #                               p2, p1               -
    (0x5f,  'SDS',           0,    'SetDeltaShiftInGState',  1,  0),    #                                    n               -
    (0x0b,  'SFVFS',         0,    'SetFVectorFromStack',    2,  0),    #                                 y, x               -
    (0x04,  'SFVTCA',        1,    'SetFVectorToAxis',       0,  0),    #                                    -               -
    (0x08,  'SFVTL',         1,    'SetFVectorToLine',       2,  0),    #                               p2, p1               -
    (0x0e,  'SFVTPV',        0,    'SetFVectorToPVector',    0,  0),    #                                    -               -
    (0x34,  'SHC',           1,    'ShiftContourByLastPt',   1,  0),    #                                    c               -
    (0x32,  'SHP',           1,    'ShiftPointByLastPoint', -1,  0),    #              p1, p2, ..., ploopvalue               -
    (0x38,  'SHPIX',         0,    'ShiftZoneByPixel',      -1,  0),    #           d, p1, p2, ..., ploopvalue               -
    (0x36,  'SHZ',           1,    'ShiftZoneByLastPoint',   1,  0),    #                                    e               -
    (0x17,  'SLOOP',         0,    'SetLoopVariable',        1,  0),    #                                    n               -
    (0x1a,  'SMD',           0,    'SetMinimumDistance',     1,  0),    #                             distance               -
    (0x0a,  'SPVFS',         0,    'SetPVectorFromStack',    2,  0),    #                                 y, x               -
    (0x02,  'SPVTCA',        1,    'SetPVectorToAxis',       0,  0),    #                                    -               -
    (0x06,  'SPVTL',         1,    'SetPVectorToLine',       2,  0),    #                               p2, p1               -
    (0x76,  'SROUND',        0,    'SuperRound',             1,  0),    #                                    n               -
    (0x10,  'SRP0',          0,    'SetRefPoint0',           1,  0),    #                                    p               -
    (0x11,  'SRP1',          0,    'SetRefPoint1',           1,  0),    #                                    p               -
    (0x12,  'SRP2',          0,    'SetRefPoint2',           1,  0),    #                                    p               -
    (0x1f,  'SSW',           0,    'SetSingleWidth',         1,  0),    #                                    n               -
    (0x1e,  'SSWCI',         0,    'SetSingleWidthCutIn',    1,  0),    #                                    n               -
    (0x61,  'SUB',           0,    'Subtract',               2,  1),    #                               n2, n1       (n1 - n2)
    (0x00,  'SVTCA',         1,    'SetFPVectorToAxis',      0,  0),    #                                    -               -
    (0x23,  'SWAP',          0,    'SwapTopStack',           2,  2),    #                               e2, e1          e1, e2
    (0x13,  'SZP0',          0,    'SetZonePointer0',        1,  0),    #                                    n               -
    (0x14,  'SZP1',          0,    'SetZonePointer1',        1,  0),    #                                    n               -
    (0x15,  'SZP2',          0,    'SetZonePointer2',        1,  0),    #                                    n               -
    (0x16,  'SZPS',          0,    'SetZonePointerS',        1,  0),    #                                    n               -
    (0x29,  'UTP',           0,    'UnTouchPt',              1,  0),    #                                    p               -
    (0x70,  'WCVTF',         0,    'WriteCVTInFUnits',       2,  0),    #                                 n, l               -
    (0x44,  'WCVTP',         0,    'WriteCVTInPixels',       2,  0),    #                                 v, l               -
    (0x42,  'WS',            0,    'WriteStore',             2,  0),    #                                 v, l               -
]

# fmt: on


def bitRepr(value, bits):
    s = ""
    for i in range(bits):
        s = "01"[value & 0x1] + s
        value = value >> 1
    return s


_mnemonicPat = re.compile(r"[A-Z][A-Z0-9]*$")


def _makeDict(instructionList):
    opcodeDict = {}
    mnemonicDict = {}
    for op, mnemonic, argBits, name, pops, pushes in instructionList:
        assert _mnemonicPat.match(mnemonic)
        mnemonicDict[mnemonic] = op, argBits, name
        if argBits:
            argoffset = op
            for i in range(1 << argBits):
                opcodeDict[op + i] = mnemonic, argBits, argoffset, name
        else:
            opcodeDict[op] = mnemonic, 0, 0, name
    return opcodeDict, mnemonicDict


streamOpcodeDict, streamMnemonicDict = _makeDict(streamInstructions)
opcodeDict, mnemonicDict = _makeDict(instructions)


class tt_instructions_error(Exception):
    def __init__(self, error):
        self.error = error

    def __str__(self):
        return "TT instructions error: %s" % repr(self.error)


_comment = r"/\*.*?\*/"
_instruction = r"([A-Z][A-Z0-9]*)\s*\[(.*?)\]"
_number = r"-?[0-9]+"
_token = "(%s)|(%s)|(%s)" % (_instruction, _number, _comment)

_tokenRE = re.compile(_token)
_whiteRE = re.compile(r"\s*")

_pushCountPat = re.compile(r"[A-Z][A-Z0-9]*\s*\[.*?\]\s*/\* ([0-9]+).*?\*/")

_indentRE = re.compile(r"^FDEF|IF|ELSE\[ \]\t.+")
_unindentRE = re.compile(r"^ELSE|ENDF|EIF\[ \]\t.+")


def _skipWhite(data, pos):
    m = _whiteRE.match(data, pos)
    newPos = m.regs[0][1]
    assert newPos >= pos
    return newPos


class Program(object):
    def __init__(self) -> None:
        pass

    def fromBytecode(self, bytecode: bytes) -> None:
        self.bytecode = array.array("B", bytecode)
        if hasattr(self, "assembly"):
            del self.assembly

    def fromAssembly(self, assembly: List[str] | str) -> None:
        if isinstance(assembly, list):
            self.assembly = assembly
        elif isinstance(assembly, str):
            self.assembly = assembly.splitlines()
        else:
            raise TypeError(f"expected str or List[str], got {type(assembly).__name__}")
        if hasattr(self, "bytecode"):
            del self.bytecode

    def getBytecode(self) -> bytes:
        if not hasattr(self, "bytecode"):
            self._assemble()
        return self.bytecode.tobytes()

    def getAssembly(self, preserve=True) -> List[str]:
        if not hasattr(self, "assembly"):
            self._disassemble(preserve=preserve)
        return self.assembly

    def toXML(self, writer, ttFont) -> None:
        if (
            not hasattr(ttFont, "disassembleInstructions")
            or ttFont.disassembleInstructions
        ):
            try:
                assembly = self.getAssembly()
            except:
                import traceback

                tmp = StringIO()
                traceback.print_exc(file=tmp)
                msg = "An exception occurred during the decompilation of glyph program:\n\n"
                msg += tmp.getvalue()
                log.error(msg)
                writer.begintag("bytecode")
                writer.newline()
                writer.comment(msg.strip())
                writer.newline()
                writer.dumphex(self.getBytecode())
                writer.endtag("bytecode")
                writer.newline()
            else:
                if not assembly:
                    return
                writer.begintag("assembly")
                writer.newline()
                i = 0
                indent = 0
                nInstr = len(assembly)
                while i < nInstr:
                    instr = assembly[i]
                    if _unindentRE.match(instr):
                        indent -= 1
                    writer.write(writer.indentwhite * indent)
                    writer.write(instr)
                    writer.newline()
                    m = _pushCountPat.match(instr)
                    i = i + 1
                    if m:
                        nValues = int(m.group(1))
                        line: List[str] = []
                        j = 0
                        for j in range(nValues):
                            if j and not (j % 25):
                                writer.write(writer.indentwhite * indent)
                                writer.write(" ".join(line))
                                writer.newline()
                                line = []
                            line.append(assembly[i + j])
                        writer.write(writer.indentwhite * indent)
                        writer.write(" ".join(line))
                        writer.newline()
                        i = i + j + 1
                    if _indentRE.match(instr):
                        indent += 1
                writer.endtag("assembly")
                writer.newline()
        else:
            bytecode = self.getBytecode()
            if not bytecode:
                return
            writer.begintag("bytecode")
            writer.newline()
            writer.dumphex(bytecode)
            writer.endtag("bytecode")
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont) -> None:
        if name == "assembly":
            self.fromAssembly(strjoin(content))
            self._assemble()
            del self.assembly
        else:
            assert name == "bytecode"
            self.fromBytecode(readHex(content))

    def _assemble(self) -> None:
        assembly = " ".join(getattr(self, "assembly", []))
        bytecode: List[int] = []
        push = bytecode.append
        lenAssembly = len(assembly)
        pos = _skipWhite(assembly, 0)
        while pos < lenAssembly:
            m = _tokenRE.match(assembly, pos)
            if m is None:
                raise tt_instructions_error(
                    "Syntax error in TT program (%s)" % assembly[pos - 5 : pos + 15]
                )
            dummy, mnemonic, arg, number, comment = m.groups()
            pos = m.regs[0][1]
            if comment:
                pos = _skipWhite(assembly, pos)
                continue

            arg = arg.strip()
            if mnemonic.startswith("INSTR"):
                # Unknown instruction
                op = int(mnemonic[5:])
                push(op)
            elif mnemonic not in ("PUSH", "NPUSHB", "NPUSHW", "PUSHB", "PUSHW"):
                op, argBits, name = mnemonicDict[mnemonic]
                if len(arg) != argBits:
                    raise tt_instructions_error(
                        "Incorrect number of argument bits (%s[%s])" % (mnemonic, arg)
                    )
                if arg:
                    arg = binary2num(arg)
                    push(op + arg)
                else:
                    push(op)
            else:
                args = []
                pos = _skipWhite(assembly, pos)
                while pos < lenAssembly:
                    m = _tokenRE.match(assembly, pos)
                    if m is None:
                        raise tt_instructions_error(
                            "Syntax error in TT program (%s)" % assembly[pos : pos + 15]
                        )
                    dummy, _mnemonic, arg, number, comment = m.groups()
                    if number is None and comment is None:
                        break
                    pos = m.regs[0][1]
                    pos = _skipWhite(assembly, pos)
                    if comment is not None:
                        continue
                    args.append(int(number))
                nArgs = len(args)
                if mnemonic == "PUSH":
                    # Automatically choose the most compact representation
                    nWords = 0
                    while nArgs:
                        while (
                            nWords < nArgs
                            and nWords < 255
                            and not (0 <= args[nWords] <= 255)
                        ):
                            nWords += 1
                        nBytes = 0
                        while (
                            nWords + nBytes < nArgs
                            and nBytes < 255
                            and 0 <= args[nWords + nBytes] <= 255
                        ):
                            nBytes += 1
                        if (
                            nBytes < 2
                            and nWords + nBytes < 255
                            and nWords + nBytes != nArgs
                        ):
                            # Will write bytes as words
                            nWords += nBytes
                            continue

                        # Write words
                        if nWords:
                            if nWords <= 8:
                                op, argBits, name = streamMnemonicDict["PUSHW"]
                                op = op + nWords - 1
                                push(op)
                            else:
                                op, argBits, name = streamMnemonicDict["NPUSHW"]
                                push(op)
                                push(nWords)
                            for value in args[:nWords]:
                                assert -32768 <= value < 32768, (
                                    "PUSH value out of range %d" % value
                                )
                                push((value >> 8) & 0xFF)
                                push(value & 0xFF)

                        # Write bytes
                        if nBytes:
                            pass
                            if nBytes <= 8:
                                op, argBits, name = streamMnemonicDict["PUSHB"]
                                op = op + nBytes - 1
                                push(op)
                            else:
                                op, argBits, name = streamMnemonicDict["NPUSHB"]
                                push(op)
                                push(nBytes)
                            for value in args[nWords : nWords + nBytes]:
                                push(value)

                        nTotal = nWords + nBytes
                        args = args[nTotal:]
                        nArgs -= nTotal
                        nWords = 0
                else:
                    # Write exactly what we've been asked to
                    words = mnemonic[-1] == "W"
                    op, argBits, name = streamMnemonicDict[mnemonic]
                    if mnemonic[0] != "N":
                        assert nArgs <= 8, nArgs
                        op = op + nArgs - 1
                        push(op)
                    else:
                        assert nArgs < 256
                        push(op)
                        push(nArgs)
                    if words:
                        for value in args:
                            assert -32768 <= value < 32768, (
                                "PUSHW value out of range %d" % value
                            )
                            push((value >> 8) & 0xFF)
                            push(value & 0xFF)
                    else:
                        for value in args:
                            assert 0 <= value < 256, (
                                "PUSHB value out of range %d" % value
                            )
                            push(value)

            pos = _skipWhite(assembly, pos)

        if bytecode:
            assert max(bytecode) < 256 and min(bytecode) >= 0
        self.bytecode = array.array("B", bytecode)

    def _disassemble(self, preserve=False) -> None:
        assembly = []
        i = 0
        bytecode = getattr(self, "bytecode", [])
        numBytecode = len(bytecode)
        while i < numBytecode:
            op = bytecode[i]
            try:
                mnemonic, argBits, argoffset, name = opcodeDict[op]
            except KeyError:
                if op in streamOpcodeDict:
                    values = []

                    # Merge consecutive PUSH operations
                    while bytecode[i] in streamOpcodeDict:
                        op = bytecode[i]
                        mnemonic, argBits, argoffset, name = streamOpcodeDict[op]
                        words = mnemonic[-1] == "W"
                        if argBits:
                            nValues = op - argoffset + 1
                        else:
                            i = i + 1
                            nValues = bytecode[i]
                        i = i + 1
                        assert nValues > 0
                        if not words:
                            for j in range(nValues):
                                value = bytecode[i]
                                values.append(repr(value))
                                i = i + 1
                        else:
                            for j in range(nValues):
                                # cast to signed int16
                                value = (bytecode[i] << 8) | bytecode[i + 1]
                                if value >= 0x8000:
                                    value = value - 0x10000
                                values.append(repr(value))
                                i = i + 2
                        if preserve:
                            break

                    if not preserve:
                        mnemonic = "PUSH"
                    nValues = len(values)
                    if nValues == 1:
                        assembly.append("%s[ ]	/* 1 value pushed */" % mnemonic)
                    else:
                        assembly.append(
                            "%s[ ]	/* %s values pushed */" % (mnemonic, nValues)
                        )
                    assembly.extend(values)
                else:
                    assembly.append("INSTR%d[ ]" % op)
                    i = i + 1
            else:
                if argBits:
                    assembly.append(
                        mnemonic
                        + "[%s]	/* %s */" % (num2binary(op - argoffset, argBits), name)
                    )
                else:
                    assembly.append(mnemonic + "[ ]	/* %s */" % name)
                i = i + 1
        self.assembly = assembly

    def __bool__(self) -> bool:
        """
        >>> p = Program()
        >>> bool(p)
        False
        >>> bc = array.array("B", [0])
        >>> p.fromBytecode(bc)
        >>> bool(p)
        True
        >>> p.bytecode.pop()
        0
        >>> bool(p)
        False

        >>> p = Program()
        >>> asm = ['SVTCA[0]']
        >>> p.fromAssembly(asm)
        >>> bool(p)
        True
        >>> p.assembly.pop()
        'SVTCA[0]'
        >>> bool(p)
        False
        """
        return (hasattr(self, "assembly") and len(self.assembly) > 0) or (
            hasattr(self, "bytecode") and len(self.bytecode) > 0
        )

    __nonzero__ = __bool__

    def __eq__(self, other) -> bool:
        if type(self) != type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        result = self.__eq__(other)
        return result if result is NotImplemented else not result


def _test():
    """
    >>> _test()
    True
    """

    bc = b"""@;:9876543210/.-,+*)(\'&%$#"! \037\036\035\034\033\032\031\030\027\026\025\024\023\022\021\020\017\016\015\014\013\012\011\010\007\006\005\004\003\002\001\000,\001\260\030CXEj\260\031C`\260F#D#\020 \260FN\360M/\260\000\022\033!#\0213Y-,\001\260\030CX\260\005+\260\000\023K\260\024PX\261\000@8Y\260\006+\033!#\0213Y-,\001\260\030CXN\260\003%\020\362!\260\000\022M\033 E\260\004%\260\004%#Jad\260(RX!#\020\326\033\260\003%\020\362!\260\000\022YY-,\260\032CX!!\033\260\002%\260\002%I\260\003%\260\003%Ja d\260\020PX!!!\033\260\003%\260\003%I\260\000PX\260\000PX\270\377\3428!\033\260\0208!Y\033\260\000RX\260\0368!\033\270\377\3608!YYYY-,\001\260\030CX\260\005+\260\000\023K\260\024PX\271\000\000\377\3008Y\260\006+\033!#\0213Y-,N\001\212\020\261F\031CD\260\000\024\261\000F\342\260\000\025\271\000\000\377\3608\000\260\000<\260(+\260\002%\020\260\000<-,\001\030\260\000/\260\001\024\362\260\001\023\260\001\025M\260\000\022-,\001\260\030CX\260\005+\260\000\023\271\000\000\377\3408\260\006+\033!#\0213Y-,\001\260\030CXEdj#Edi\260\031Cd``\260F#D#\020 \260F\360/\260\000\022\033!! \212 \212RX\0213\033!!YY-,\001\261\013\012C#Ce\012-,\000\261\012\013C#C\013-,\000\260F#p\261\001F>\001\260F#p\261\002FE:\261\002\000\010\015-,\260\022+\260\002%E\260\002%Ej\260@\213`\260\002%#D!!!-,\260\023+\260\002%E\260\002%Ej\270\377\300\214`\260\002%#D!!!-,\260\000\260\022+!!!-,\260\000\260\023+!!!-,\001\260\006C\260\007Ce\012-, i\260@a\260\000\213 \261,\300\212\214\270\020\000b`+\014d#da\\X\260\003aY-,\261\000\003%EhT\260\034KPZX\260\003%E\260\003%E`h \260\004%#D\260\004%#D\033\260\003% Eh \212#D\260\003%Eh`\260\003%#DY-,\260\003% Eh \212#D\260\003%Edhe`\260\004%\260\001`#D-,\260\011CX\207!\300\033\260\022CX\207E\260\021+\260G#D\260Gz\344\033\003\212E\030i \260G#D\212\212\207 \260\240QX\260\021+\260G#D\260Gz\344\033!\260Gz\344YYY\030-, \212E#Eh`D-,EjB-,\001\030/-,\001\260\030CX\260\004%\260\004%Id#Edi\260@\213a \260\200bj\260\002%\260\002%a\214\260\031C`\260F#D!\212\020\260F\366!\033!!!!Y-,\001\260\030CX\260\002%E\260\002%Ed`j\260\003%Eja \260\004%Ej \212\213e\260\004%#D\214\260\003%#D!!\033 EjD EjDY-,\001 E\260\000U\260\030CZXEh#Ei\260@\213a \260\200bj \212#a \260\003%\213e\260\004%#D\214\260\003%#D!!\033!!\260\031+Y-,\001\212\212Ed#EdadB-,\260\004%\260\004%\260\031+\260\030CX\260\004%\260\004%\260\003%\260\033+\001\260\002%C\260@T\260\002%C\260\000TZX\260\003% E\260@aDY\260\002%C\260\000T\260\002%C\260@TZX\260\004% E\260@`DYY!!!!-,\001KRXC\260\002%E#aD\033!!Y-,\001KRXC\260\002%E#`D\033!!Y-,KRXED\033!!Y-,\001 \260\003%#I\260@`\260 c \260\000RX#\260\002%8#\260\002%e8\000\212c8\033!!!!!Y\001-,KPXED\033!!Y-,\001\260\005%\020# \212\365\000\260\001`#\355\354-,\001\260\005%\020# \212\365\000\260\001a#\355\354-,\001\260\006%\020\365\000\355\354-,F#F`\212\212F# F\212`\212a\270\377\200b# \020#\212\261KK\212pE` \260\000PX\260\001a\270\377\272\213\033\260F\214Y\260\020`h\001:-, E\260\003%FRX\260\002%F ha\260\003%\260\003%?#!8\033!\021Y-, E\260\003%FPX\260\002%F ha\260\003%\260\003%?#!8\033!\021Y-,\000\260\007C\260\006C\013-,\212\020\354-,\260\014CX!\033 F\260\000RX\270\377\3608\033\260\0208YY-, \260\000UX\270\020\000c\260\003%Ed\260\003%Eda\260\000SX\260\002\033\260@a\260\003Y%EiSXED\033!!Y\033!\260\002%E\260\002%Ead\260(QXED\033!!YY-,!!\014d#d\213\270@\000b-,!\260\200QX\014d#d\213\270 \000b\033\262\000@/+Y\260\002`-,!\260\300QX\014d#d\213\270\025Ub\033\262\000\200/+Y\260\002`-,\014d#d\213\270@\000b`#!-,KSX\260\004%\260\004%Id#Edi\260@\213a \260\200bj\260\002%\260\002%a\214\260F#D!\212\020\260F\366!\033!\212\021#\022 9/Y-,\260\002%\260\002%Id\260\300TX\270\377\3708\260\0108\033!!Y-,\260\023CX\003\033\002Y-,\260\023CX\002\033\003Y-,\260\012+#\020 <\260\027+-,\260\002%\270\377\3608\260(+\212\020# \320#\260\020+\260\005CX\300\033<Y \020\021\260\000\022\001-,KS#KQZX8\033!!Y-,\001\260\002%\020\320#\311\001\260\001\023\260\000\024\020\260\001<\260\001\026-,\001\260\000\023\260\001\260\003%I\260\003\0278\260\001\023-,KS#KQZX E\212`D\033!!Y-, 9/-"""

    p = Program()
    p.fromBytecode(bc)
    asm = p.getAssembly(preserve=True)
    p.fromAssembly(asm)
    print(bc == p.getBytecode())


if __name__ == "__main__":
    import sys
    import doctest

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\databricks\chat\transformation.py ===
"""
Translates from OpenAI's `/v1/chat/completions` to Databricks' `/chat/completions`
"""

from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Coroutine,
    Iterator,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    cast,
    overload,
)

import httpx
from pydantic import BaseModel

from litellm.constants import RESPONSE_FORMAT_TOOL_NAME
from litellm.litellm_core_utils.llm_response_utils.convert_dict_to_response import (
    _handle_invalid_parallel_tool_calls,
    _should_convert_tool_call_to_json_mode,
)
from litellm.litellm_core_utils.prompt_templates.common_utils import (
    handle_messages_with_content_list_to_str_conversion,
    strip_name_from_messages,
)
from litellm.llms.base_llm.base_model_iterator import BaseModelResponseIterator
from litellm.types.llms.anthropic import AllAnthropicToolsValues
from litellm.types.llms.databricks import (
    AllDatabricksContentValues,
    DatabricksChoice,
    DatabricksFunction,
    DatabricksResponse,
    DatabricksTool,
)
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionRedactedThinkingBlock,
    ChatCompletionThinkingBlock,
    ChatCompletionToolChoiceFunctionParam,
    ChatCompletionToolChoiceObjectParam,
)
from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Choices,
    Message,
    ModelResponse,
    ModelResponseStream,
    ProviderField,
    Usage,
)

from ...anthropic.chat.transformation import AnthropicConfig
from ...openai_like.chat.transformation import OpenAILikeChatConfig
from ..common_utils import DatabricksBase, DatabricksException

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class DatabricksConfig(DatabricksBase, OpenAILikeChatConfig, AnthropicConfig):
    """
    Reference: https://docs.databricks.com/en/machine-learning/foundation-models/api-reference.html#chat-request
    """

    max_tokens: Optional[int] = None
    temperature: Optional[int] = None
    top_p: Optional[int] = None
    top_k: Optional[int] = None
    stop: Optional[Union[List[str], str]] = None
    n: Optional[int] = None

    def __init__(
        self,
        max_tokens: Optional[int] = None,
        temperature: Optional[int] = None,
        top_p: Optional[int] = None,
        top_k: Optional[int] = None,
        stop: Optional[Union[List[str], str]] = None,
        n: Optional[int] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_required_params(self) -> List[ProviderField]:
        """For a given provider, return it's required fields with a description"""
        return [
            ProviderField(
                field_name="api_key",
                field_type="string",
                field_description="Your Databricks API Key.",
                field_value="dapi...",
            ),
            ProviderField(
                field_name="api_base",
                field_type="string",
                field_description="Your Databricks API Base.",
                field_value="https://adb-..",
            ),
        ]

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        api_base, headers = self.databricks_validate_environment(
            api_base=api_base,
            api_key=api_key,
            endpoint_type="chat_completions",
            custom_endpoint=False,
            headers=headers,
        )
        # Ensure Content-Type header is set
        headers["Content-Type"] = "application/json"
        return headers

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        api_base = self._get_api_base(api_base)
        complete_url = f"{api_base}/chat/completions"
        return complete_url

    def get_supported_openai_params(self, model: Optional[str] = None) -> list:
        return [
            "stream",
            "stop",
            "temperature",
            "top_p",
            "max_tokens",
            "max_completion_tokens",
            "n",
            "response_format",
            "tools",
            "tool_choice",
            "reasoning_effort",
            "thinking",
        ]

    def convert_anthropic_tool_to_databricks_tool(
        self, tool: Optional[AllAnthropicToolsValues]
    ) -> Optional[DatabricksTool]:
        if tool is None:
            return None

        return DatabricksTool(
            type="function",
            function=DatabricksFunction(
                name=tool["name"],
                parameters=cast(dict, tool.get("input_schema") or {}),
            ),
        )

    def _map_openai_to_dbrx_tool(self, model: str, tools: List) -> List[DatabricksTool]:
        # if not claude, send as is
        if "claude" not in model:
            return tools

        # if claude, convert to anthropic tool and then to databricks tool
        anthropic_tools, _ = self._map_tools(
            tools=tools
        )  # unclear how mcp tool calling on databricks works
        databricks_tools = [
            cast(DatabricksTool, self.convert_anthropic_tool_to_databricks_tool(tool))
            for tool in anthropic_tools
        ]
        return databricks_tools

    def map_response_format_to_databricks_tool(
        self,
        model: str,
        value: Optional[dict],
        optional_params: dict,
        is_thinking_enabled: bool,
    ) -> Optional[DatabricksTool]:
        if value is None:
            return None

        tool = self.map_response_format_to_anthropic_tool(
            value, optional_params, is_thinking_enabled
        )

        databricks_tool = self.convert_anthropic_tool_to_databricks_tool(tool)
        return databricks_tool

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
        replace_max_completion_tokens_with_max_tokens: bool = True,
    ) -> dict:
        is_thinking_enabled = self.is_thinking_enabled(non_default_params)
        mapped_params = super().map_openai_params(
            non_default_params, optional_params, model, drop_params
        )
        if "tools" in mapped_params:
            mapped_params["tools"] = self._map_openai_to_dbrx_tool(
                model=model, tools=mapped_params["tools"]
            )
        if (
            "max_completion_tokens" in non_default_params
            and replace_max_completion_tokens_with_max_tokens
        ):
            mapped_params["max_tokens"] = non_default_params[
                "max_completion_tokens"
            ]  # most openai-compatible providers support 'max_tokens' not 'max_completion_tokens'
            mapped_params.pop("max_completion_tokens", None)

        if "response_format" in non_default_params and "claude" in model:
            _tool = self.map_response_format_to_databricks_tool(
                model,
                non_default_params["response_format"],
                mapped_params,
                is_thinking_enabled,
            )

            if _tool is not None:
                self._add_tools_to_optional_params(
                    optional_params=optional_params, tools=[_tool]
                )
                optional_params["json_mode"] = True
                if not is_thinking_enabled:
                    _tool_choice = ChatCompletionToolChoiceObjectParam(
                        type="function",
                        function=ChatCompletionToolChoiceFunctionParam(
                            name=RESPONSE_FORMAT_TOOL_NAME
                        ),
                    )
                    optional_params["tool_choice"] = _tool_choice
            optional_params.pop(
                "response_format", None
            )  # unsupported for claude models - if json_schema -> convert to tool call

        if "reasoning_effort" in non_default_params and "claude" in model:
            optional_params["thinking"] = AnthropicConfig._map_reasoning_effort(
                non_default_params.get("reasoning_effort")
            )
            optional_params.pop("reasoning_effort", None)
        ## handle thinking tokens
        self.update_optional_params_with_thinking_tokens(
            non_default_params=non_default_params, optional_params=mapped_params
        )

        return mapped_params

    def _should_fake_stream(self, optional_params: dict) -> bool:
        """
        Databricks doesn't support 'response_format' while streaming
        """
        if optional_params.get("response_format") is not None:
            return True

        return False

    @overload
    def _transform_messages(
        self, messages: List[AllMessageValues], model: str, is_async: Literal[True]
    ) -> Coroutine[Any, Any, List[AllMessageValues]]:
        ...

    @overload
    def _transform_messages(
        self,
        messages: List[AllMessageValues],
        model: str,
        is_async: Literal[False] = False,
    ) -> List[AllMessageValues]:
        ...

    def _transform_messages(
        self, messages: List[AllMessageValues], model: str, is_async: bool = False
    ) -> Union[List[AllMessageValues], Coroutine[Any, Any, List[AllMessageValues]]]:
        """
        Databricks does not support:
        - content in list format.
        - 'name' in user message.
        """
        new_messages = []
        for idx, message in enumerate(messages):
            if isinstance(message, BaseModel):
                _message = message.model_dump(exclude_none=True)
            else:
                _message = message
            new_messages.append(_message)
        new_messages = handle_messages_with_content_list_to_str_conversion(new_messages)
        new_messages = strip_name_from_messages(new_messages)

        if is_async:
            return super()._transform_messages(
                messages=new_messages, model=model, is_async=cast(Literal[True], True)
            )
        else:
            return super()._transform_messages(
                messages=new_messages, model=model, is_async=cast(Literal[False], False)
            )

    @staticmethod
    def extract_content_str(
        content: Optional[AllDatabricksContentValues],
    ) -> Optional[str]:
        if content is None:
            return None
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            content_str = ""
            for item in content:
                if item["type"] == "text":
                    content_str += item["text"]
            return content_str
        else:
            raise Exception(f"Unsupported content type: {type(content)}")

    @staticmethod
    def extract_reasoning_content(
        content: Optional[AllDatabricksContentValues],
    ) -> Tuple[
        Optional[str],
        Optional[
            List[
                Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]
            ]
        ],
    ]:
        """
        Extract and return the reasoning content and thinking blocks
        """
        if content is None:
            return None, None
        thinking_blocks: Optional[
            List[
                Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]
            ]
        ] = None
        reasoning_content: Optional[str] = None
        if isinstance(content, list):
            for item in content:
                if item["type"] == "reasoning":
                    for sum in item["summary"]:
                        if reasoning_content is None:
                            reasoning_content = ""
                        reasoning_content += sum["text"]
                        thinking_block = ChatCompletionThinkingBlock(
                            type="thinking",
                            thinking=sum["text"],
                            signature=sum["signature"],
                        )
                        if thinking_blocks is None:
                            thinking_blocks = []
                        thinking_blocks.append(thinking_block)
        return reasoning_content, thinking_blocks

    def _transform_dbrx_choices(
        self, choices: List[DatabricksChoice], json_mode: Optional[bool] = None
    ) -> List[Choices]:
        transformed_choices = []

        for choice in choices:
            ## HANDLE JSON MODE - anthropic returns single function call]
            tool_calls = choice["message"].get("tool_calls", None)
            if tool_calls is not None:
                _openai_tool_calls = []
                for _tc in tool_calls:
                    _openai_tc = ChatCompletionMessageToolCall(**_tc)  # type: ignore
                    _openai_tool_calls.append(_openai_tc)
                fixed_tool_calls = _handle_invalid_parallel_tool_calls(
                    _openai_tool_calls
                )

                if fixed_tool_calls is not None:
                    tool_calls = fixed_tool_calls

            translated_message: Optional[Message] = None
            finish_reason: Optional[str] = None
            if tool_calls and _should_convert_tool_call_to_json_mode(
                tool_calls=tool_calls,
                convert_tool_call_to_json_mode=json_mode,
            ):
                # to support response_format on claude models
                json_mode_content_str: Optional[str] = (
                    str(tool_calls[0]["function"].get("arguments", "")) or None
                )
                if json_mode_content_str is not None:
                    translated_message = Message(content=json_mode_content_str)
                    finish_reason = "stop"

            if translated_message is None:
                ## get the content str
                content_str = DatabricksConfig.extract_content_str(
                    choice["message"]["content"]
                )

                ## get the reasoning content
                (
                    reasoning_content,
                    thinking_blocks,
                ) = DatabricksConfig.extract_reasoning_content(
                    choice["message"].get("content")
                )

                translated_message = Message(
                    role="assistant",
                    content=content_str,
                    reasoning_content=reasoning_content,
                    thinking_blocks=thinking_blocks,
                    tool_calls=choice["message"].get("tool_calls"),
                )

            if finish_reason is None:
                finish_reason = choice["finish_reason"]

            translated_choice = Choices(
                finish_reason=finish_reason,
                index=choice["index"],
                message=translated_message,
                logprobs=None,
                enhancements=None,
            )

            transformed_choices.append(translated_choice)

        return transformed_choices

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        ## LOGGING
        logging_obj.post_call(
            input=messages,
            api_key=api_key,
            original_response=raw_response.text,
            additional_args={"complete_input_dict": request_data},
        )

        ## RESPONSE OBJECT
        try:
            completion_response = DatabricksResponse(**raw_response.json())  # type: ignore
        except Exception as e:
            response_headers = getattr(raw_response, "headers", None)
            raise DatabricksException(
                message="Unable to get json response - {}, Original Response: {}".format(
                    str(e), raw_response.text
                ),
                status_code=raw_response.status_code,
                headers=response_headers,
            )

        model_response.model = completion_response["model"]
        model_response.id = completion_response["id"]
        model_response.created = completion_response["created"]
        setattr(model_response, "usage", Usage(**completion_response["usage"]))

        model_response.choices = self._transform_dbrx_choices(  # type: ignore
            choices=completion_response["choices"],
            json_mode=json_mode,
        )

        return model_response

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ):
        return DatabricksChatResponseIterator(
            streaming_response=streaming_response,
            sync_stream=sync_stream,
            json_mode=json_mode,
        )


class DatabricksChatResponseIterator(BaseModelResponseIterator):
    def __init__(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ):
        super().__init__(streaming_response, sync_stream)

        self.json_mode = json_mode
        self._last_function_name = None  # Track the last seen function name

    def chunk_parser(self, chunk: dict) -> ModelResponseStream:
        try:
            translated_choices = []
            for choice in chunk["choices"]:
                tool_calls = choice["delta"].get("tool_calls")
                if tool_calls and self.json_mode:
                    # 1. Check if the function name is set and == RESPONSE_FORMAT_TOOL_NAME
                    # 2. If no function name, just args -> check last function name (saved via state variable)
                    # 3. Convert args to json
                    # 4. Convert json to message
                    # 5. Set content to message.content
                    # 6. Set tool_calls to None
                    from litellm.constants import RESPONSE_FORMAT_TOOL_NAME
                    from litellm.llms.base_llm.base_utils import (
                        _convert_tool_response_to_message,
                    )

                    # Check if this chunk has a function name
                    function_name = tool_calls[0].get("function", {}).get("name")
                    if function_name is not None:
                        self._last_function_name = function_name

                    # If we have a saved function name that matches RESPONSE_FORMAT_TOOL_NAME
                    # or this chunk has the matching function name
                    if (
                        self._last_function_name == RESPONSE_FORMAT_TOOL_NAME
                        or function_name == RESPONSE_FORMAT_TOOL_NAME
                    ):
                        # Convert tool calls to message format
                        message = _convert_tool_response_to_message(tool_calls)
                        if message is not None:
                            if message.content == "{}":  # empty json
                                message.content = ""
                            choice["delta"]["content"] = message.content
                            choice["delta"]["tool_calls"] = None
                elif tool_calls:
                    for _tc in tool_calls:
                        if _tc.get("function", {}).get("arguments") == "{}":
                            _tc["function"]["arguments"] = ""  # avoid invalid json
                # extract the content str
                content_str = DatabricksConfig.extract_content_str(
                    choice["delta"].get("content")
                )

                # extract the reasoning content
                (
                    reasoning_content,
                    thinking_blocks,
                ) = DatabricksConfig.extract_reasoning_content(
                    choice["delta"].get("content")
                )

                choice["delta"]["content"] = content_str
                choice["delta"]["reasoning_content"] = reasoning_content
                choice["delta"]["thinking_blocks"] = thinking_blocks
                translated_choices.append(choice)
            return ModelResponseStream(
                id=chunk["id"],
                object="chat.completion.chunk",
                created=chunk["created"],
                model=chunk["model"],
                choices=translated_choices,
            )
        except KeyError as e:
            raise DatabricksException(
                message=f"KeyError: {e}, Got unexpected response from Databricks: {chunk}",
                status_code=400,
            )
        except Exception as e:
            raise e

# === NexusCore/openenv\Lib\site-packages\win32\scripts\ControlService.py ===
# ControlService.py
#
# A simple app which duplicates some of the functionality in the
# Services applet of the control panel.
#
# Suggested enhancements (in no particular order):
#
# 1. When changing the service status, continue to query the status
# of the service until the status change is complete.  Use this
# information to put up some kind of a progress dialog like the CP
# applet does.  Unlike the CP, allow canceling out in the event that
# the status change hangs.
# 2. When starting or stopping a service with dependencies, alert
# the user about the dependent services, then start (or stop) all
# dependent services as appropriate.
# 3. Allow toggling between service view and device view
# 4. Allow configuration of other service parameters such as startup
# name and password.
# 5. Allow connection to remote SCMs.  This is just a matter of
# reconnecting to the SCM on the remote machine; the rest of the
# code should still work the same.
# 6. Either implement the startup parameters or get rid of the editbox.
# 7. Either implement or get rid of "H/W Profiles".
# 8. Either implement or get rid of "Help".
# 9. Improve error handling.  Ideally, this would also include falling
# back to lower levels of functionality for users with less rights.
# Right now, we always try to get all the rights and fail when we can't


import win32con
import win32service
import win32ui
from pywin.mfc import dialog


class StartupDlg(dialog.Dialog):
    IDC_LABEL = 127
    IDC_DEVICE = 128
    IDC_BOOT = 129
    IDC_SYSTEM = 130
    IDC_AUTOMATIC = 131
    IDC_MANUAL = 132
    IDC_DISABLED = 133

    def __init__(self, displayname, service):
        dialog.Dialog.__init__(self, self.GetResource())
        self.name = displayname
        self.service = service

    def __del__(self):
        win32service.CloseServiceHandle(self.service)

    def OnInitDialog(self):
        cfg = win32service.QueryServiceConfig(self.service)
        self.GetDlgItem(self.IDC_BOOT + cfg[1]).SetCheck(1)

        status = win32service.QueryServiceStatus(self.service)
        if (status[0] & win32service.SERVICE_KERNEL_DRIVER) or (
            status[0] & win32service.SERVICE_FILE_SYSTEM_DRIVER
        ):
            # driver
            self.GetDlgItem(self.IDC_LABEL).SetWindowText("Device:")
        else:
            # service
            self.GetDlgItem(self.IDC_LABEL).SetWindowText("Service:")
            self.GetDlgItem(self.IDC_BOOT).EnableWindow(0)
            self.GetDlgItem(self.IDC_SYSTEM).EnableWindow(0)
        self.GetDlgItem(self.IDC_DEVICE).SetWindowText(str(self.name))

        return dialog.Dialog.OnInitDialog(self)

    def OnOK(self):
        self.BeginWaitCursor()
        starttype = (
            self.GetCheckedRadioButton(self.IDC_BOOT, self.IDC_DISABLED) - self.IDC_BOOT
        )
        try:
            win32service.ChangeServiceConfig(
                self.service,
                win32service.SERVICE_NO_CHANGE,
                starttype,
                win32service.SERVICE_NO_CHANGE,
                None,
                None,
                0,
                None,
                None,
                None,
                None,
            )
        except:
            self.MessageBox(
                "Unable to change startup configuration",
                None,
                win32con.MB_ICONEXCLAMATION,
            )
        self.EndWaitCursor()
        return dialog.Dialog.OnOK(self)

    def GetResource(self):
        style = (
            win32con.WS_POPUP
            | win32con.DS_SETFONT
            | win32con.WS_SYSMENU
            | win32con.WS_CAPTION
            | win32con.WS_VISIBLE
            | win32con.DS_MODALFRAME
        )
        exstyle = None
        t = [
            ["Service Startup", (6, 18, 188, 107), style, exstyle, (8, "MS Shell Dlg")],
        ]
        t.append(
            [
                130,
                "Device:",
                self.IDC_LABEL,
                (6, 7, 40, 8),
                win32con.WS_VISIBLE | win32con.WS_CHILD | win32con.SS_LEFT,
            ]
        )
        t.append(
            [
                130,
                "",
                self.IDC_DEVICE,
                (48, 7, 134, 8),
                win32con.WS_VISIBLE | win32con.WS_CHILD | win32con.SS_LEFT,
            ]
        )
        t.append(
            [
                128,
                "Startup Type",
                -1,
                (6, 21, 130, 80),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_GROUP
                | win32con.BS_GROUPBOX,
            ]
        )
        t.append(
            [
                128,
                "&Boot",
                self.IDC_BOOT,
                (12, 33, 39, 10),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_AUTORADIOBUTTON,
            ]
        )
        t.append(
            [
                128,
                "&System",
                self.IDC_SYSTEM,
                (12, 46, 39, 10),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_AUTORADIOBUTTON,
            ]
        )
        t.append(
            [
                128,
                "&Automatic",
                self.IDC_AUTOMATIC,
                (12, 59, 118, 10),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_AUTORADIOBUTTON,
            ]
        )
        t.append(
            [
                128,
                "&Manual",
                self.IDC_MANUAL,
                (12, 72, 118, 10),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_AUTORADIOBUTTON,
            ]
        )
        t.append(
            [
                128,
                "&Disabled",
                self.IDC_DISABLED,
                (12, 85, 118, 10),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_AUTORADIOBUTTON,
            ]
        )
        t.append(
            [
                128,
                "OK",
                win32con.IDOK,
                (142, 25, 40, 14),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.WS_GROUP
                | win32con.BS_DEFPUSHBUTTON,
            ]
        )
        t.append(
            [
                128,
                "Cancel",
                win32con.IDCANCEL,
                (142, 43, 40, 14),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_PUSHBUTTON,
            ]
        )
        t.append(
            [
                128,
                "&Help",
                win32con.IDHELP,
                (142, 61, 40, 14),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_PUSHBUTTON,
            ]
        )
        return t


class ServiceDlg(dialog.Dialog):
    IDC_LIST = 128
    IDC_START = 129
    IDC_STOP = 130
    IDC_PAUSE = 131
    IDC_CONTINUE = 132
    IDC_STARTUP = 133
    IDC_PROFILES = 134
    IDC_PARAMS = 135

    def __init__(self, machineName=""):
        dialog.Dialog.__init__(self, self.GetResource())
        self.HookCommand(self.OnListEvent, self.IDC_LIST)
        self.HookCommand(self.OnStartCmd, self.IDC_START)
        self.HookCommand(self.OnStopCmd, self.IDC_STOP)
        self.HookCommand(self.OnPauseCmd, self.IDC_PAUSE)
        self.HookCommand(self.OnContinueCmd, self.IDC_CONTINUE)
        self.HookCommand(self.OnStartupCmd, self.IDC_STARTUP)
        self.machineName = machineName
        self.scm = win32service.OpenSCManager(
            self.machineName, None, win32service.SC_MANAGER_ALL_ACCESS
        )

    def __del__(self):
        win32service.CloseServiceHandle(self.scm)

    def OnInitDialog(self):
        self.listCtrl = self.GetDlgItem(self.IDC_LIST)
        self.listCtrl.SetTabStops([158, 200])
        if self.machineName:
            self.SetWindowText("Services on %s" % self.machineName)
        self.ReloadData()
        return dialog.Dialog.OnInitDialog(self)

    def ReloadData(self):
        service = self.GetSelService()
        self.listCtrl.SetRedraw(0)
        self.listCtrl.ResetContent()
        svcs = win32service.EnumServicesStatus(self.scm)
        i = 0
        self.data = []
        for svc in svcs:
            try:
                status = (
                    "Unknown",
                    "Stopped",
                    "Starting",
                    "Stopping",
                    "Running",
                    "Continuing",
                    "Pausing",
                    "Paused",
                )[svc[2][1]]
            except:
                status = "Unknown"
            s = win32service.OpenService(
                self.scm, svc[0], win32service.SERVICE_ALL_ACCESS
            )
            cfg = win32service.QueryServiceConfig(s)
            try:
                startup = ("Boot", "System", "Automatic", "Manual", "Disabled")[cfg[1]]
            except:
                startup = "Unknown"
            win32service.CloseServiceHandle(s)

            # svc[2][2] control buttons
            pos = self.listCtrl.AddString(str(svc[1]) + "\t" + status + "\t" + startup)
            self.listCtrl.SetItemData(pos, i)
            self.data.append(
                tuple(svc[2])
                + (
                    svc[1],
                    svc[0],
                )
            )
            i += 1

            if service and service[1] == svc[0]:
                self.listCtrl.SetCurSel(pos)
        self.OnListEvent(self.IDC_LIST, win32con.LBN_SELCHANGE)
        self.listCtrl.SetRedraw(1)

    def OnListEvent(self, id, code):
        if code == win32con.LBN_SELCHANGE or code == win32con.LBN_SELCANCEL:
            pos = self.listCtrl.GetCurSel()
            if pos >= 0:
                data = self.data[self.listCtrl.GetItemData(pos)][2]
                canstart = (
                    self.data[self.listCtrl.GetItemData(pos)][1]
                    == win32service.SERVICE_STOPPED
                )
            else:
                data = 0
                canstart = 0
            self.GetDlgItem(self.IDC_START).EnableWindow(canstart)
            self.GetDlgItem(self.IDC_STOP).EnableWindow(
                data & win32service.SERVICE_ACCEPT_STOP
            )
            self.GetDlgItem(self.IDC_PAUSE).EnableWindow(
                data & win32service.SERVICE_ACCEPT_PAUSE_CONTINUE
            )
            self.GetDlgItem(self.IDC_CONTINUE).EnableWindow(
                data & win32service.SERVICE_ACCEPT_PAUSE_CONTINUE
            )

    def GetSelService(self):
        pos = self.listCtrl.GetCurSel()
        if pos < 0:
            return None
        pos = self.listCtrl.GetItemData(pos)
        return self.data[pos][-2:]

    def OnStartCmd(self, id, code):
        service = self.GetSelService()
        if not service:
            return
        s = win32service.OpenService(
            self.scm, service[1], win32service.SERVICE_ALL_ACCESS
        )
        win32service.StartService(s, None)
        win32service.CloseServiceHandle(s)
        self.ReloadData()

    def OnStopCmd(self, id, code):
        service = self.GetSelService()
        if not service:
            return
        s = win32service.OpenService(
            self.scm, service[1], win32service.SERVICE_ALL_ACCESS
        )
        win32service.ControlService(s, win32service.SERVICE_CONTROL_STOP)
        win32service.CloseServiceHandle(s)
        self.ReloadData()

    def OnPauseCmd(self, id, code):
        service = self.GetSelService()
        if not service:
            return
        s = win32service.OpenService(
            self.scm, service[1], win32service.SERVICE_ALL_ACCESS
        )
        win32service.ControlService(s, win32service.SERVICE_CONTROL_PAUSE)
        win32service.CloseServiceHandle(s)
        self.ReloadData()

    def OnContinueCmd(self, id, code):
        service = self.GetSelService()
        if not service:
            return
        s = win32service.OpenService(
            self.scm, service[1], win32service.SERVICE_ALL_ACCESS
        )
        win32service.ControlService(s, win32service.SERVICE_CONTROL_CONTINUE)
        win32service.CloseServiceHandle(s)
        self.ReloadData()

    def OnStartupCmd(self, id, code):
        service = self.GetSelService()
        if not service:
            return
        s = win32service.OpenService(
            self.scm, service[1], win32service.SERVICE_ALL_ACCESS
        )
        if StartupDlg(service[0], s).DoModal() == win32con.IDOK:
            self.ReloadData()

    def GetResource(self):
        style = (
            win32con.WS_POPUP
            | win32con.DS_SETFONT
            | win32con.WS_SYSMENU
            | win32con.WS_CAPTION
            | win32con.WS_VISIBLE
            | win32con.DS_MODALFRAME
        )
        exstyle = None
        t = [
            ["Services", (16, 16, 333, 157), style, exstyle, (8, "MS Shell Dlg")],
        ]
        t.append(
            [
                130,
                "Ser&vice",
                -1,
                (6, 6, 70, 8),
                win32con.WS_VISIBLE | win32con.WS_CHILD | win32con.SS_LEFT,
            ]
        )
        t.append(
            [
                130,
                "Status",
                -1,
                (164, 6, 42, 8),
                win32con.WS_VISIBLE | win32con.WS_CHILD | win32con.SS_LEFT,
            ]
        )
        t.append(
            [
                130,
                "Startup",
                -1,
                (206, 6, 50, 8),
                win32con.WS_VISIBLE | win32con.WS_CHILD | win32con.SS_LEFT,
            ]
        )
        t.append(
            [
                131,
                "",
                self.IDC_LIST,
                (6, 16, 255, 106),
                win32con.LBS_USETABSTOPS
                | win32con.LBS_SORT
                | win32con.LBS_NOINTEGRALHEIGHT
                | win32con.WS_BORDER
                | win32con.WS_CHILD
                | win32con.WS_VISIBLE
                | win32con.WS_TABSTOP
                | win32con.LBS_NOTIFY
                | win32con.WS_VSCROLL,
            ]
        )
        t.append(
            [
                128,
                "Close",
                win32con.IDOK,
                (267, 6, 60, 14),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_GROUP
                | win32con.WS_TABSTOP
                | win32con.BS_DEFPUSHBUTTON,
            ]
        )
        t.append(
            [
                128,
                "&Start",
                self.IDC_START,
                (267, 27, 60, 14),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_PUSHBUTTON,
            ]
        )
        t.append(
            [
                128,
                "S&top",
                self.IDC_STOP,
                (267, 44, 60, 14),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_PUSHBUTTON,
            ]
        )
        t.append(
            [
                128,
                "&Pause",
                self.IDC_PAUSE,
                (267, 61, 60, 14),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_PUSHBUTTON,
            ]
        )
        t.append(
            [
                128,
                "&Continue",
                self.IDC_CONTINUE,
                (267, 78, 60, 14),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_PUSHBUTTON,
            ]
        )
        t.append(
            [
                128,
                "Sta&rtup...",
                self.IDC_STARTUP,
                (267, 99, 60, 14),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_PUSHBUTTON,
            ]
        )
        t.append(
            [
                128,
                "H&W Profiles...",
                self.IDC_PROFILES,
                (267, 116, 60, 14),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_PUSHBUTTON,
            ]
        )
        t.append(
            [
                128,
                "&Help",
                win32con.IDHELP,
                (267, 137, 60, 14),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_TABSTOP
                | win32con.BS_PUSHBUTTON,
            ]
        )
        t.append(
            [
                130,
                "St&artup Parameters:",
                -1,
                (6, 128, 70, 8),
                win32con.WS_VISIBLE | win32con.WS_CHILD | win32con.SS_LEFT,
            ]
        )
        t.append(
            [
                129,
                "",
                self.IDC_PARAMS,
                (6, 139, 247, 12),
                win32con.WS_VISIBLE
                | win32con.WS_CHILD
                | win32con.WS_GROUP
                | win32con.WS_BORDER
                | win32con.ES_AUTOHSCROLL,
            ]
        )
        return t


if __name__ == "__main__":
    import sys

    machine = ""
    if len(sys.argv) > 1:
        machine = sys.argv[1]
    ServiceDlg(machine).DoModal()

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\apdlexer.py ===
"""
    pygments.lexers.apdlexer
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for ANSYS Parametric Design Language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, words, default
from pygments.token import Comment, Keyword, Name, Number, Operator, \
    String, Generic, Punctuation, Whitespace, Escape

__all__ = ['apdlexer']


class apdlexer(RegexLexer):
    """
    For APDL source code.
    """
    name = 'ANSYS parametric design language'
    aliases = ['ansys', 'apdl']
    filenames = ['*.ans']
    url = 'https://www.ansys.com'
    version_added = '2.9'

    flags = re.IGNORECASE

    # list of elements
    elafunb = ("SURF152", "SURF153", "SURF154", "SURF156", "SHELL157",
               "SURF159", "LINK160", "BEAM161", "PLANE162",
               "SHELL163", "SOLID164", "COMBI165", "MASS166",
               "LINK167", "SOLID168", "TARGE169", "TARGE170",
               "CONTA171", "CONTA172", "CONTA173", "CONTA174",
               "CONTA175", "CONTA176", "CONTA177", "CONTA178",
               "PRETS179", "LINK180", "SHELL181", "PLANE182",
               "PLANE183", "MPC184", "SOLID185", "SOLID186",
               "SOLID187", "BEAM188", "BEAM189", "SOLSH190",
               "INTER192", "INTER193", "INTER194", "INTER195",
               "MESH200", "FOLLW201", "INTER202", "INTER203",
               "INTER204", "INTER205", "SHELL208", "SHELL209",
               "CPT212", "CPT213", "COMBI214", "CPT215", "CPT216",
               "CPT217", "FLUID220", "FLUID221", "PLANE223",
               "SOLID226", "SOLID227", "PLANE230", "SOLID231",
               "SOLID232", "PLANE233", "SOLID236", "SOLID237",
               "PLANE238", "SOLID239", "SOLID240", "HSFLD241",
               "HSFLD242", "SURF251", "SURF252", "REINF263",
               "REINF264", "REINF265", "SOLID272", "SOLID273",
               "SOLID278", "SOLID279", "SHELL281", "SOLID285",
               "PIPE288", "PIPE289", "ELBOW290", "USER300", "BEAM3",
               "BEAM4", "BEAM23", "BEAM24", "BEAM44", "BEAM54",
               "COMBIN7", "FLUID79", "FLUID80", "FLUID81", "FLUID141",
               "FLUID142", "INFIN9", "INFIN47", "PLANE13", "PLANE25",
               "PLANE42", "PLANE53", "PLANE67", "PLANE82", "PLANE83",
               "PLANE145", "PLANE146", "CONTAC12", "CONTAC52",
               "LINK1", "LINK8", "LINK10", "LINK32", "PIPE16",
               "PIPE17", "PIPE18", "PIPE20", "PIPE59", "PIPE60",
               "SHELL41", "SHELL43", "SHELL57", "SHELL63", "SHELL91",
               "SHELL93", "SHELL99", "SHELL150", "SOLID5", "SOLID45",
               "SOLID46", "SOLID65", "SOLID69", "SOLID92", "SOLID95",
               "SOLID117", "SOLID127", "SOLID128", "SOLID147",
               "SOLID148", "SOLID191", "VISCO88", "VISCO89",
               "VISCO106", "VISCO107", "VISCO108", "TRANS109")

    elafunc = ("PGRAPH", "/VT", "VTIN", "VTRFIL", "VTTEMP", "PGRSET",
               "VTCLR", "VTMETH", "VTRSLT", "VTVMOD", "PGSELE",
               "VTDISC", "VTMP", "VTSEC", "PGWRITE", "VTEVAL", "VTOP",
               "VTSFE", "POUTRES", "VTFREQ", "VTPOST", "VTSL",
               "FLDATA1-40", "HFPCSWP", "MSDATA", "MSVARY", "QFACT",
               "FLOCHECK", "HFPOWER", "MSMASS", "PERI", "SPADP",
               "FLREAD", "HFPORT", "MSMETH", "PLFSS", "SPARM",
               "FLOTRAN", "HFSCAT", "MSMIR", "PLSCH", "SPFSS",
               "HFADP", "ICE", "MSNOMF", "PLSYZ", "SPICE", "HFARRAY",
               "ICEDELE", "MSPROP", "PLTD", "SPSCAN", "HFDEEM",
               "ICELIST", "MSQUAD", "PLTLINE", "SPSWP", "HFEIGOPT",
               "ICVFRC", "MSRELAX", "PLVFRC", "HFEREFINE", "LPRT",
               "MSSOLU", "/PICE", "HFMODPRT", "MSADV", "MSSPEC",
               "PLWAVE", "HFPA", "MSCAP", "MSTERM", "PRSYZ")

    elafund = ("*VOPER", "VOVLAP", "*VPLOT", "VPLOT", "VPTN", "*VPUT",
               "VPUT", "*VREAD", "VROTAT", "VSBA", "VSBV", "VSBW",
               "/VSCALE", "*VSCFUN", "VSEL", "VSLA", "*VSTAT", "VSUM",
               "VSWEEP", "VSYMM", "VTRAN", "VTYPE", "/VUP", "*VWRITE",
               "/WAIT", "WAVES", "WERASE", "WFRONT", "/WINDOW",
               "WMID", "WMORE", "WPAVE", "WPCSYS", "WPLANE", "WPOFFS",
               "WPROTA", "WPSTYL", "WRFULL", "WRITE", "WRITEMAP",
               "*WRK", "WSORT", "WSPRINGS", "WSTART", "WTBCREATE",
               "XFDATA", "XFENRICH", "XFLIST", "/XFRM", "/XRANGE",
               "XVAR", "/YRANGE", "/ZOOM", "/WB", "XMLO", "/XML",
               "CNTR", "EBLOCK", "CMBLOCK", "NBLOCK", "/TRACK",
               "CWZPLOT", "~EUI", "NELE", "EALL", "NALL", "FLITEM",
               "LSLN", "PSOLVE", "ASLN", "/VERIFY", "/SSS", "~CFIN",
               "*EVAL", "*MOONEY", "/RUNSTAT", "ALPFILL",
               "ARCOLLAPSE", "ARDETACH", "ARFILL", "ARMERGE",
               "ARSPLIT", "FIPLOT", "GAPFINISH", "GAPLIST",
               "GAPMERGE", "GAPOPT", "GAPPLOT", "LNCOLLAPSE",
               "LNDETACH", "LNFILL", "LNMERGE", "LNSPLIT", "PCONV",
               "PLCONV", "PEMOPTS", "PEXCLUDE", "PINCLUDE", "PMETH",
               "/PMETH", "PMOPTS", "PPLOT", "PPRANGE", "PRCONV",
               "PRECISION", "RALL", "RFILSZ", "RITER", "RMEMRY",
               "RSPEED", "RSTAT", "RTIMST", "/RUNST", "RWFRNT",
               "SARPLOT", "SHSD", "SLPPLOT", "SLSPLOT", "VCVFILL",
               "/OPT", "OPEQN", "OPFACT", "OPFRST", "OPGRAD",
               "OPKEEP", "OPLOOP", "OPPRNT", "OPRAND", "OPSUBP",
               "OPSWEEP", "OPTYPE", "OPUSER", "OPVAR", "OPADD",
               "OPCLR", "OPDEL", "OPMAKE", "OPSEL", "OPANL", "OPDATA",
               "OPRESU", "OPSAVE", "OPEXE", "OPLFA", "OPLGR",
               "OPLIST", "OPLSW", "OPRFA", "OPRGR", "OPRSW",
               "PILECALC", "PILEDISPSET", "PILEGEN", "PILELOAD",
               "PILEMASS", "PILERUN", "PILESEL", "PILESTIF",
               "PLVAROPT", "PRVAROPT", "TOCOMP", "TODEF", "TOFREQ",
               "TOTYPE", "TOVAR", "TOEXE", "TOLOOP", "TOGRAPH",
               "TOLIST", "TOPLOT", "TOPRINT", "TOSTAT", "TZAMESH",
               "TZDELE", "TZEGEN", "XVAROPT", "PGSAVE", "SOLCONTROL",
               "TOTAL", "VTGEOM", "VTREAL", "VTSTAT")

    elafune = ("/ANUM", "AOFFST", "AOVLAP", "APLOT", "APPEND", "APTN",
               "ARCLEN", "ARCTRM", "AREAS", "AREFINE", "AREMESH",
               "AREVERSE", "AROTAT", "ARSCALE", "ARSYM", "ASBA",
               "ASBL", "ASBV", "ASBW", "ASCRES", "ASEL", "ASIFILE",
               "*ASK", "ASKIN", "ASLL", "ASLV", "ASOL", "/ASSIGN",
               "ASUB", "ASUM", "ATAN", "ATRAN", "ATYPE", "/AUTO",
               "AUTOTS", "/AUX2", "/AUX3", "/AUX12", "/AUX15",
               "AVPRIN", "AVRES", "AWAVE", "/AXLAB", "*AXPY",
               "/BATCH", "BCSOPTION", "BETAD", "BF", "BFA", "BFADELE",
               "BFALIST", "BFCUM", "BFDELE", "BFE", "BFECUM",
               "BFEDELE", "BFELIST", "BFESCAL", "BFINT", "BFK",
               "BFKDELE", "BFKLIST", "BFL", "BFLDELE", "BFLIST",
               "BFLLIST", "BFSCALE", "BFTRAN", "BFUNIF", "BFV",
               "BFVDELE", "BFVLIST", "BIOOPT", "BIOT", "BLC4", "BLC5",
               "BLOCK", "BOOL", "BOPTN", "BSAX", "BSMD", "BSM1",
               "BSM2", "BSPLIN", "BSS1", "BSS2", "BSTE", "BSTQ",
               "BTOL", "BUCOPT", "C", "CALC", "CAMPBELL", "CBDOF",
               "CBMD", "CBMX", "CBTE", "CBTMP", "CDOPT", "CDREAD",
               "CDWRITE", "CE", "CECHECK", "CECMOD", "CECYC",
               "CEDELE", "CEINTF", "CELIST", "CENTER", "CEQN",
               "CERIG", "CESGEN", "CFACT", "*CFCLOS", "*CFOPEN",
               "*CFWRITE", "/CFORMAT", "CGLOC", "CGOMGA", "CGROW",
               "CHECK", "CHKMSH", "CINT", "CIRCLE", "CISOL",
               "/CLABEL", "/CLEAR", "CLOCAL", "CLOG", "/CLOG",
               "CLRMSHLN", "CM", "CMACEL", "/CMAP", "CMATRIX",
               "CMDELE", "CMDOMEGA", "CMEDIT", "CMGRP", "CMLIST",
               "CMMOD", "CMOMEGA", "CMPLOT", "CMROTATE", "CMSEL",
               "CMSFILE", "CMSOPT", "CMWRITE", "CNCHECK", "CNKMOD",
               "CNTR", "CNVTOL", "/COLOR", "*COMP", "COMBINE",
               "COMPRESS", "CON4", "CONE", "/CONFIG", "CONJUG",
               "/CONTOUR", "/COPY", "CORIOLIS", "COUPLE", "COVAL",
               "CP", "CPCYC", "CPDELE", "CPINTF", "/CPLANE", "CPLGEN",
               "CPLIST", "CPMERGE", "CPNGEN", "CPSGEN", "CQC",
               "*CREATE", "CRPLIM", "CS", "CSCIR", "CSDELE", "CSKP",
               "CSLIST", "CSWPLA", "CSYS", "/CTYPE", "CURR2D",
               "CUTCONTROL", "/CVAL", "CVAR", "/CWD", "CYCCALC",
               "/CYCEXPAND", "CYCFILES", "CYCFREQ", "*CYCLE",
               "CYCLIC", "CYCOPT", "CYCPHASE", "CYCSPEC", "CYL4",
               "CYL5", "CYLIND", "CZDEL", "CZMESH", "D", "DA",
               "DADELE", "DALIST", "DAMORPH", "DATA", "DATADEF",
               "DCGOMG", "DCUM", "DCVSWP", "DDASPEC", "DDELE",
               "DDOPTION", "DEACT", "DEFINE", "*DEL", "DELETE",
               "/DELETE", "DELTIM", "DELTIME", "DEMORPH", "DERIV", "DESIZE",
               "DESOL", "DETAB", "/DEVDISP", "/DEVICE", "/DFLAB",
               "DFLX", "DFSWAVE", "DIG", "DIGIT", "*DIM",
               "/DIRECTORY", "DISPLAY", "/DIST", "DJ", "DJDELE",
               "DJLIST", "DK", "DKDELE", "DKLIST", "DL", "DLDELE",
               "DLIST", "DLLIST", "*DMAT", "DMOVE", "DMPEXT",
               "DMPOPTION", "DMPRAT", "DMPSTR", "DNSOL", "*DO", "DOF",
               "DOFSEL", "DOMEGA", "*DOT", "*DOWHILE", "DSCALE",
               "/DSCALE", "DSET", "DSPOPTION", "DSUM", "DSURF",
               "DSYM", "DSYS", "DTRAN", "DUMP", "/DV3D", "DVAL",
               "DVMORPH", "DYNOPT", "E", "EALIVE", "EDADAPT", "EDALE",
               "EDASMP", "EDBOUND", "EDBX", "EDBVIS", "EDCADAPT",
               "EDCGEN", "EDCLIST", "EDCMORE", "EDCNSTR", "EDCONTACT",
               "EDCPU", "EDCRB", "EDCSC", "EDCTS", "EDCURVE",
               "EDDAMP", "EDDBL", "EDDC", "EDDRELAX", "EDDUMP",
               "EDELE", "EDENERGY", "EDFPLOT", "EDGCALE", "/EDGE",
               "EDHGLS", "EDHIST", "EDHTIME", "EDINT", "EDIPART",
               "EDIS", "EDLCS", "EDLOAD", "EDMP", "EDNB", "EDNDTSD",
               "EDNROT", "EDOPT", "EDOUT", "EDPART", "EDPC", "EDPL",
               "EDPVEL", "EDRC", "EDRD", "EDREAD", "EDRI", "EDRST",
               "EDRUN", "EDSHELL", "EDSOLV", "EDSP", "EDSTART",
               "EDTERM", "EDTP", "EDVEL", "EDWELD", "EDWRITE",
               "EEXTRUDE", "/EFACET", "EGEN", "*EIGEN", "EINFIN",
               "EINTF", "EKILL", "ELBOW", "ELEM", "ELIST", "*ELSE",
               "*ELSEIF", "EMAGERR", "EMATWRITE", "EMF", "EMFT",
               "EMID", "EMIS", "EMODIF", "EMORE", "EMSYM", "EMTGEN",
               "EMUNIT", "EN", "*END", "*ENDDO", "*ENDIF",
               "ENDRELEASE", "ENERSOL", "ENGEN", "ENORM", "ENSYM",
               "EORIENT", "EPLOT", "EQSLV", "ERASE", "/ERASE",
               "EREAD", "EREFINE", "EREINF", "ERESX", "ERNORM",
               "ERRANG", "ESCHECK", "ESEL", "/ESHAPE", "ESIZE",
               "ESLA", "ESLL", "ESLN", "ESLV", "ESOL", "ESORT",
               "ESSOLV", "ESTIF", "ESURF", "ESYM", "ESYS", "ET",
               "ETABLE", "ETCHG", "ETCONTROL", "ETDELE", "ETLIST",
               "ETYPE", "EUSORT", "EWRITE", "*EXIT", "/EXIT", "EXP",
               "EXPAND", "/EXPAND", "EXPASS", "*EXPORT", "EXPROFILE",
               "EXPSOL", "EXTOPT", "EXTREM", "EXUNIT", "F", "/FACET",
               "FATIGUE", "FC", "FCCHECK", "FCDELE", "FCLIST", "FCUM",
               "FCTYP", "FDELE", "/FDELE", "FE", "FEBODY", "FECONS",
               "FEFOR", "FELIST", "FESURF", "*FFT", "FILE",
               "FILEAUX2", "FILEAUX3", "FILEDISP", "FILL", "FILLDATA",
               "/FILNAME", "FINISH", "FITEM", "FJ", "FJDELE",
               "FJLIST", "FK", "FKDELE", "FKLIST", "FL", "FLIST",
               "FLLIST", "FLST", "FLUXV", "FLUREAD", "FMAGBC",
               "FMAGSUM", "/FOCUS", "FOR2D", "FORCE", "FORM",
               "/FORMAT", "FP", "FPLIST", "*FREE", "FREQ", "FRQSCL",
               "FS", "FSCALE", "FSDELE", "FSLIST", "FSNODE", "FSPLOT",
               "FSSECT", "FSSPARM", "FSUM", "FTCALC", "FTRAN",
               "FTSIZE", "FTWRITE", "FTYPE", "FVMESH", "GAP", "GAPF",
               "GAUGE", "GCDEF", "GCGEN", "/GCMD", "/GCOLUMN",
               "GENOPT", "GEOM", "GEOMETRY", "*GET", "/GFILE",
               "/GFORMAT", "/GLINE", "/GMARKER", "GMATRIX", "GMFACE",
               "*GO", "/GO", "/GOLIST", "/GOPR", "GP", "GPDELE",
               "GPLIST", "GPLOT", "/GRAPHICS", "/GRESUME", "/GRID",
               "/GROPT", "GRP", "/GRTYP", "/GSAVE", "GSBDATA",
               "GSGDATA", "GSLIST", "GSSOL", "/GST", "GSUM", "/GTHK",
               "/GTYPE", "HARFRQ", "/HBC", "HBMAT", "/HEADER", "HELP",
               "HELPDISP", "HEMIOPT", "HFANG", "HFSYM", "HMAGSOLV",
               "HPGL", "HPTCREATE", "HPTDELETE", "HRCPLX", "HREXP",
               "HROPT", "HROCEAN", "HROUT", "IC", "ICDELE", "ICLIST",
               "/ICLWID", "/ICSCALE", "*IF", "IGESIN", "IGESOUT",
               "/IMAGE", "IMAGIN", "IMESH", "IMMED", "IMPD",
               "INISTATE", "*INIT", "/INPUT", "/INQUIRE", "INRES",
               "INRTIA", "INT1", "INTSRF", "IOPTN", "IRLF", "IRLIST",
               "*ITENGINE", "JPEG", "JSOL", "K", "KATT", "KBC",
               "KBETW", "KCALC", "KCENTER", "KCLEAR", "KDELE",
               "KDIST", "KEEP", "KESIZE", "KEYOPT", "KEYPTS", "KEYW",
               "KFILL", "KGEN", "KL", "KLIST", "KMESH", "KMODIF",
               "KMOVE", "KNODE", "KPLOT", "KPSCALE", "KREFINE",
               "KSCALE", "KSCON", "KSEL", "KSLL", "KSLN", "KSUM",
               "KSYMM", "KTRAN", "KUSE", "KWPAVE", "KWPLAN", "L",
               "L2ANG", "L2TAN", "LANG", "LARC", "/LARC", "LAREA",
               "LARGE", "LATT", "LAYER", "LAYERP26", "LAYLIST",
               "LAYPLOT", "LCABS", "LCASE", "LCCALC", "LCCAT",
               "LCDEF", "LCFACT", "LCFILE", "LCLEAR", "LCOMB",
               "LCOPER", "LCSEL", "LCSL", "LCSUM", "LCWRITE",
               "LCZERO", "LDELE", "LDIV", "LDRAG", "LDREAD", "LESIZE",
               "LEXTND", "LFILLT", "LFSURF", "LGEN", "LGLUE",
               "LGWRITE", "/LIGHT", "LINA", "LINE", "/LINE", "LINES",
               "LINL", "LINP", "LINV", "LIST", "*LIST", "LLIST",
               "LMATRIX", "LMESH", "LNSRCH", "LOCAL", "LOVLAP",
               "LPLOT", "LPTN", "LREFINE", "LREVERSE", "LROTAT",
               "LSBA", "*LSBAC", "LSBL", "LSBV", "LSBW", "LSCLEAR",
               "LSDELE", "*LSDUMP", "LSEL", "*LSENGINE", "*LSFACTOR",
               "LSLA", "LSLK", "LSOPER", "/LSPEC", "LSREAD",
               "*LSRESTORE", "LSSCALE", "LSSOLVE", "LSTR", "LSUM",
               "LSWRITE", "/LSYMBOL", "LSYMM", "LTAN", "LTRAN",
               "LUMPM", "LVSCALE", "LWPLAN", "M", "MADAPT", "MAGOPT",
               "MAGSOLV", "/MAIL", "MAP", "/MAP", "MAP2DTO3D",
               "MAPSOLVE", "MAPVAR", "MASTER", "MAT", "MATER",
               "MCHECK", "MDAMP", "MDELE", "MDPLOT", "MEMM", "/MENU",
               "MESHING", "MFANALYSIS", "MFBUCKET", "MFCALC", "MFCI",
               "MFCLEAR", "MFCMMAND", "MFCONV", "MFDTIME", "MFELEM",
               "MFEM", "MFEXTER", "MFFNAME", "MFFR", "MFIMPORT",
               "MFINTER", "MFITER", "MFLCOMM", "MFLIST", "MFMAP",
               "MFORDER", "MFOUTPUT", "*MFOURI", "MFPSIMUL", "MFRC",
               "MFRELAX", "MFRSTART", "MFSORDER", "MFSURFACE",
               "MFTIME", "MFTOL", "*MFUN", "MFVOLUME", "MFWRITE",
               "MGEN", "MIDTOL", "/MKDIR", "MLIST", "MMASS", "MMF",
               "MODCONT", "MODE", "MODIFY", "MODMSH", "MODSELOPTION",
               "MODOPT", "MONITOR", "*MOPER", "MOPT", "MORPH", "MOVE",
               "MP", "MPAMOD", "MPCHG", "MPCOPY", "MPDATA", "MPDELE",
               "MPDRES", "/MPLIB", "MPLIST", "MPPLOT", "MPREAD",
               "MPRINT", "MPTEMP", "MPTGEN", "MPTRES", "MPWRITE",
               "/MREP", "MSAVE", "*MSG", "MSHAPE", "MSHCOPY",
               "MSHKEY", "MSHMID", "MSHPATTERN", "MSOLVE", "/MSTART",
               "MSTOLE", "*MULT", "*MWRITE", "MXPAND", "N", "NANG",
               "NAXIS", "NCNV", "NDELE", "NDIST", "NDSURF", "NEQIT",
               "/NERR", "NFORCE", "NGEN", "NKPT", "NLADAPTIVE",
               "NLDIAG", "NLDPOST", "NLGEOM", "NLHIST", "NLIST",
               "NLMESH", "NLOG", "NLOPT", "NMODIF", "NOCOLOR",
               "NODES", "/NOERASE", "/NOLIST", "NOOFFSET", "NOORDER",
               "/NOPR", "NORA", "NORL", "/NORMAL", "NPLOT", "NPRINT",
               "NREAD", "NREFINE", "NRLSUM", "*NRM", "NROPT",
               "NROTAT", "NRRANG", "NSCALE", "NSEL", "NSLA", "NSLE",
               "NSLK", "NSLL", "NSLV", "NSMOOTH", "NSOL", "NSORT",
               "NSTORE", "NSUBST", "NSVR", "NSYM", "/NUMBER",
               "NUMCMP", "NUMEXP", "NUMMRG", "NUMOFF", "NUMSTR",
               "NUMVAR", "NUSORT", "NWPAVE", "NWPLAN", "NWRITE",
               "OCDATA", "OCDELETE", "OCLIST", "OCREAD", "OCTABLE",
               "OCTYPE", "OCZONE", "OMEGA", "OPERATE", "OPNCONTROL",
               "OUTAERO", "OUTOPT", "OUTPR", "/OUTPUT", "OUTRES",
               "OVCHECK", "PADELE", "/PAGE", "PAGET", "PAPUT",
               "PARESU", "PARTSEL", "PARRES", "PARSAV", "PASAVE",
               "PATH", "PAUSE", "/PBC", "/PBF", "PCALC", "PCGOPT",
               "PCIRC", "/PCIRCLE", "/PCOPY", "PCROSS", "PDANL",
               "PDCDF", "PDCFLD", "PDCLR", "PDCMAT", "PDCORR",
               "PDDMCS", "PDDOEL", "PDEF", "PDEXE", "PDHIST",
               "PDINQR", "PDLHS", "PDMETH", "PDOT", "PDPINV",
               "PDPLOT", "PDPROB", "PDRESU", "PDROPT", "/PDS",
               "PDSAVE", "PDSCAT", "PDSENS", "PDSHIS", "PDUSER",
               "PDVAR", "PDWRITE", "PERBC2D", "PERTURB", "PFACT",
               "PHYSICS", "PIVCHECK", "PLCAMP", "PLCFREQ", "PLCHIST",
               "PLCINT", "PLCPLX", "PLCRACK", "PLDISP", "PLESOL",
               "PLETAB", "PLFAR", "PLF2D", "PLGEOM", "PLLS", "PLMAP",
               "PLMC", "PLNEAR", "PLNSOL", "/PLOPTS", "PLORB", "PLOT",
               "PLOTTING", "PLPAGM", "PLPATH", "PLSECT", "PLST",
               "PLTIME", "PLTRAC", "PLVAR", "PLVECT", "PLZZ",
               "/PMACRO", "PMAP", "PMGTRAN", "PMLOPT", "PMLSIZE",
               "/PMORE", "PNGR", "/PNUM", "POINT", "POLY", "/POLYGON",
               "/POST1", "/POST26", "POWERH", "PPATH", "PRANGE",
               "PRAS", "PRCAMP", "PRCINT", "PRCPLX", "PRED",
               "PRENERGY", "/PREP7", "PRERR", "PRESOL", "PRETAB",
               "PRFAR", "PRI2", "PRIM", "PRINT", "*PRINT", "PRISM",
               "PRITER", "PRJSOL", "PRNEAR", "PRNLD", "PRNSOL",
               "PROD", "PRORB", "PRPATH", "PRRFOR", "PRRSOL",
               "PRSCONTROL", "PRSECT", "PRTIME", "PRVAR", "PRVECT",
               "PSCONTROL", "PSCR", "PSDCOM", "PSDFRQ", "PSDGRAPH",
               "PSDRES", "PSDSPL", "PSDUNIT", "PSDVAL", "PSDWAV",
               "/PSEARCH", "PSEL", "/PSF", "PSMAT", "PSMESH",
               "/PSPEC", "/PSTATUS", "PSTRES", "/PSYMB", "PTR",
               "PTXY", "PVECT", "/PWEDGE", "QDVAL", "QRDOPT", "QSOPT",
               "QUAD", "/QUIT", "QUOT", "R", "RACE", "RADOPT",
               "RAPPND", "RATE", "/RATIO", "RBE3", "RCON", "RCYC",
               "RDEC", "RDELE", "READ", "REAL", "REALVAR", "RECTNG",
               "REMESH", "/RENAME", "REORDER", "*REPEAT", "/REPLOT",
               "RESCOMBINE", "RESCONTROL", "RESET", "/RESET", "RESP",
               "RESUME", "RESVEC", "RESWRITE", "*RETURN", "REXPORT",
               "REZONE", "RFORCE", "/RGB", "RIGID", "RIGRESP",
               "RIMPORT", "RLIST", "RMALIST", "RMANL", "RMASTER",
               "RMCAP", "RMCLIST", "/RMDIR", "RMFLVEC", "RMLVSCALE",
               "RMMLIST", "RMMRANGE", "RMMSELECT", "RMNDISP",
               "RMNEVEC", "RMODIF", "RMORE", "RMPORDER", "RMRESUME",
               "RMRGENERATE", "RMROPTIONS", "RMRPLOT", "RMRSTATUS",
               "RMSAVE", "RMSMPLE", "RMUSE", "RMXPORT", "ROCK",
               "ROSE", "RPOLY", "RPR4", "RPRISM", "RPSD", "RSFIT",
               "RSOPT", "RSPLIT", "RSPLOT", "RSPRNT", "RSSIMS",
               "RSTMAC", "RSTOFF", "RSURF", "RSYMM", "RSYS", "RTHICK",
               "SABS", "SADD", "SALLOW", "SAVE", "SBCLIST", "SBCTRAN",
               "SDELETE", "SE", "SECCONTROL", "SECDATA",
               "SECFUNCTION", "SECJOINT", "/SECLIB", "SECLOCK",
               "SECMODIF", "SECNUM", "SECOFFSET", "SECPLOT",
               "SECREAD", "SECSTOP", "SECTYPE", "SECWRITE", "SED",
               "SEDLIST", "SEEXP", "/SEG", "SEGEN", "SELIST", "SELM",
               "SELTOL", "SENERGY", "SEOPT", "SESYMM", "*SET", "SET",
               "SETFGAP", "SETRAN", "SEXP", "SF", "SFA", "SFACT",
               "SFADELE", "SFALIST", "SFBEAM", "SFCALC", "SFCUM",
               "SFDELE", "SFE", "SFEDELE", "SFELIST", "SFFUN",
               "SFGRAD", "SFL", "SFLDELE", "SFLEX", "SFLIST",
               "SFLLIST", "SFSCALE", "SFTRAN", "/SHADE", "SHELL",
               "/SHOW", "/SHOWDISP", "SHPP", "/SHRINK", "SLIST",
               "SLOAD", "SMALL", "*SMAT", "SMAX", "/SMBC", "SMBODY",
               "SMCONS", "SMFOR", "SMIN", "SMOOTH", "SMRTSIZE",
               "SMSURF", "SMULT", "SNOPTION", "SOLU", "/SOLU",
               "SOLUOPT", "SOLVE", "SORT", "SOURCE", "SPACE",
               "SPCNOD", "SPCTEMP", "SPDAMP", "SPEC", "SPFREQ",
               "SPGRAPH", "SPH4", "SPH5", "SPHERE", "SPLINE", "SPLOT",
               "SPMWRITE", "SPOINT", "SPOPT", "SPREAD", "SPTOPT",
               "SPOWER", "SPUNIT", "SPVAL", "SQRT", "*SREAD", "SRSS",
               "SSBT", "/SSCALE", "SSLN", "SSMT", "SSPA", "SSPB",
               "SSPD", "SSPE", "SSPM", "SSUM", "SSTATE", "STABILIZE",
               "STAOPT", "STAT", "*STATUS", "/STATUS", "STEF",
               "STORE", "SUBOPT", "SUBSET", "SUCALC",
               "SUCR", "SUDEL", "SUEVAL", "SUGET", "SUMAP", "SUMTYPE",
               "SUPL", "SUPR", "SURESU", "SUSAVE", "SUSEL", "SUVECT",
               "SV", "SVPLOT", "SVTYP", "SWADD", "SWDEL", "SWGEN",
               "SWLIST", "SYNCHRO", "/SYP", "/SYS", "TALLOW",
               "TARGET", "*TAXIS", "TB", "TBCOPY", "TBDATA", "TBDELE",
               "TBEO", "TBIN", "TBFIELD", "TBFT", "TBLE", "TBLIST",
               "TBMODIF", "TBPLOT", "TBPT", "TBTEMP", "TCHG", "/TEE",
               "TERM", "THEXPAND", "THOPT", "TIFF", "TIME",
               "TIMERANGE", "TIMINT", "TIMP", "TINTP",
               "/TLABEL", "TOFFST", "*TOPER", "TORQ2D", "TORQC2D",
               "TORQSUM", "TORUS", "TRANS", "TRANSFER", "*TREAD",
               "TREF", "/TRIAD", "/TRLCY", "TRNOPT", "TRPDEL",
               "TRPLIS", "TRPOIN", "TRTIME", "TSHAP", "/TSPEC",
               "TSRES", "TUNIF", "TVAR", "/TXTRE", "/TYPE", "TYPE",
               "/UCMD", "/UDOC", "/UI", "UIMP", "/UIS", "*ULIB", "/UPF",
               "UNDELETE", "UNDO", "/UNITS", "UNPAUSE", "UPCOORD",
               "UPGEOM", "*USE", "/USER", "USRCAL", "USRDOF",
               "USRELEM", "V", "V2DOPT", "VA", "*VABS", "VADD",
               "VARDEL", "VARNAM", "VATT", "VCLEAR", "*VCOL",
               "/VCONE", "VCROSS", "*VCUM", "VDDAM", "VDELE", "VDGL",
               "VDOT", "VDRAG", "*VEC", "*VEDIT", "VEORIENT", "VEXT",
               "*VFACT", "*VFILL", "VFOPT", "VFQUERY", "VFSM",
               "*VFUN", "VGEN", "*VGET", "VGET", "VGLUE", "/VIEW",
               "VIMP", "VINP", "VINV", "*VITRP", "*VLEN", "VLIST",
               "VLSCALE", "*VMASK", "VMESH", "VOFFST", "VOLUMES")

    # list of in-built () functions
    elafunf = ("NX()", "NY()", "NZ()", "KX()", "KY()", "KZ()", "LX()",
               "LY()", "LZ()", "LSX()", "LSY()", "LSZ()", "NODE()",
               "KP()", "DISTND()", "DISTKP()", "DISTEN()", "ANGLEN()",
               "ANGLEK()", "NNEAR()", "KNEAR()", "ENEARN()",
               "AREAND()", "AREAKP()", "ARNODE()", "NORMNX()",
               "NORMNY()", "NORMNZ()", "NORMKX()", "NORMKY()",
               "NORMKZ()", "ENEXTN()", "NELEM()", "NODEDOF()",
               "ELADJ()", "NDFACE()", "NMFACE()", "ARFACE()", "UX()",
               "UY()", "UZ()", "ROTX()", "ROTY()", "ROTZ()", "TEMP()",
               "PRES()", "VX()", "VY()", "VZ()", "ENKE()", "ENDS()",
               "VOLT()", "MAG()", "AX()", "AY()", "AZ()",
               "VIRTINQR()", "KWGET()", "VALCHR()", "VALHEX()",
               "CHRHEX()", "STRFILL()", "STRCOMP()", "STRPOS()",
               "STRLENG()", "UPCASE()", "LWCASE()", "JOIN()",
               "SPLIT()", "ABS()", "SIGN()", "CXABS()", "EXP()",
               "LOG()", "LOG10()", "SQRT()", "NINT()", "MOD()",
               "RAND()", "GDIS()", "SIN()", "COS()", "TAN()",
               "SINH()", "COSH()", "TANH()", "ASIN()", "ACOS()",
               "ATAN()", "ATAN2()")

    elafung = ("NSEL()", "ESEL()", "KSEL()", "LSEL()", "ASEL()",
               "VSEL()", "NDNEXT()", "ELNEXT()", "KPNEXT()",
               "LSNEXT()", "ARNEXT()", "VLNEXT()", "CENTRX()",
               "CENTRY()", "CENTRZ()")

    elafunh = ("~CAT5IN", "~CATIAIN", "~PARAIN", "~PROEIN", "~SATIN",
               "~UGIN", "A", "AADD", "AATT", "ABEXTRACT", "*ABBR",
               "ABBRES", "ABBSAV", "ABS", "ACCAT", "ACCOPTION",
               "ACEL", "ACLEAR", "ADAMS", "ADAPT", "ADD", "ADDAM",
               "ADELE", "ADGL", "ADRAG", "AESIZE", "AFILLT", "AFLIST",
               "AFSURF", "*AFUN", "AGEN", "AGLUE", "AINA", "AINP",
               "AINV", "AL", "ALIST", "ALLSEL", "ALPHAD", "AMAP",
               "AMESH", "/AN3D", "ANCNTR", "ANCUT", "ANCYC", "ANDATA",
               "ANDSCL", "ANDYNA", "/ANFILE", "ANFLOW", "/ANGLE",
               "ANHARM", "ANIM", "ANISOS", "ANMODE", "ANMRES",
               "/ANNOT", "ANORM", "ANPRES", "ANSOL", "ANSTOAQWA",
               "ANSTOASAS", "ANTIME", "ANTYPE")

    special = ("/COM", "/TITLE", "STITLE")

    elements = ("SOLID5",
                "LINK11",
                "PLANE13",
                "COMBIN14",
                "MASS2",
                "PLANE25",
                "MATRIX27",
                "FLUID29",
                "FLUID30",
                "LINK31",
                "LINK33",
                "LINK34",
                "PLANE35",
                "SOURC36",
                "COMBIN37",
                "FLUID38",
                "COMBIN39",
                "COMBIN40",
                "INFIN47",
                "MATRIX50",
                "PLANE55",
                "SHELL61",
                "LINK68",
                "SOLID70",
                "MASS71",
                "PLANE75",
                "PLANE77",
                "PLANE78",
                "PLANE83",
                "SOLID87",
                "SOLID90",
                "CIRCU94",
                "SOLID96",
                "SOLID98",
                "INFIN110",
                "INFIN111",
                "FLUID116",
                "PLANE121",
                "SOLID122",
                "SOLID123",
                "CIRCU124",
                "CIRCU125",
                "TRANS126",
                "FLUID129",
                "FLUID130",
                "SHELL131",
                "SHELL132",
                "FLUID136",
                "FLUID138",
                "FLUID139",
                "SURF151",
                "SURF152",
                "SURF153",
                "SURF154",
                "SURF155",
                "SURF156",
                "SHELL157",
                "SURF159",
                "TARGE169",
                "TARGE170",
                "CONTA172",
                "CONTA174",
                "CONTA175",
                "CONTA177",
                "CONTA178",
                "PRETS179",
                "LINK180",
                "SHELL181",
                "PLANE182",
                "PLANE183",
                "MPC184",
                "SOLID185",
                "SOLID186",
                "SOLID187",
                "BEAM188",
                "BEAM189",
                "SOLSH190",
                "INTER192",
                "INTER193",
                "INTER194",
                "INTER195",
                "MESH200",
                "FOLLW201",
                "INTER202",
                "INTER203",
                "INTER204",
                "INTER205",
                "SHELL208",
                "SHELL209",
                "CPT212",
                "CPT213",
                "COMBI214",
                "CPT215",
                "CPT216",
                "CPT217",
                "FLUID218",
                "FLUID220",
                "FLUID221",
                "PLANE222",
                "PLANE223",
                "SOLID225",
                "SOLID226",
                "SOLID227",
                "PLANE230",
                "SOLID231",
                "SOLID232",
                "PLANE233",
                "SOLID236",
                "SOLID237",
                "PLANE238",
                "SOLID239",
                "SOLID240",
                "HSFLD241",
                "HSFLD242",
                "COMBI250",
                "SURF251",
                "SURF252",
                "INFIN257",
                "REINF263",
                "REINF264",
                "REINF265",
                "SOLID272",
                "SOLID273",
                "SOLID278",
                "SOLID279",
                "CABLE280",
                "SHELL281",
                "SOLID285",
                "PIPE288",
                "PIPE289",
                "ELBOW290",
                "SOLID291",
                "PLANE292",
                "PLANE293",
                "USER300")

    tokens = {
        'root': [
            (r'[^\S\n]+', Whitespace),
            (words((elafunb+elafunc+elafund+elafune+elafunh+special), suffix=r'\b'), Keyword, 'non-keyword'),
            default('non-keyword'),
        ],
        'non-keyword': [
            (r'!.*\n', Comment, '#pop'),
            (r'%.*?%', Escape),
            include('strings'),
            include('nums'),
            (words((elafunf+elafung), suffix=r'\b'), Name.Builtin),
            (words((elements), suffix=r'\b'), Name.Property),
            include('core'),
            (r'AR[0-9]+', Name.Variable.Instance),
            (r'[a-z_][a-z0-9_]*', Name.Variable),
            (r'\n+', Whitespace, '#pop'),
            (r'[^\S\n]+', Whitespace),
        ],
        'core': [
            # Operators
            (r'(\*\*|\*|\+|-|\/|<|>|<=|>=|==|\/=|=|\(|\))', Operator),
            (r'/EOF', Generic.Emph),
            (r'[\.(),:&;]', Punctuation),
        ],
        'strings': [
            (r'(?s)"(\\\\|\\[0-7]+|\\.|[^"\\])*"', String.Double),
            (r"(?s)'(\\\\|\\[0-7]+|\\.|[^'\\])*'", String.Single),
            (r'[$%]', String.Symbol),
        ],
        'nums': [
            (r'[+-]?\d*\.\d+([efEF][-+]?\d+)?', Number.Float), # with dot
            (r'([+-]?\d+([efEF][-+]?\d+))', Number.Float), # With scientific notation
            (r'\b\d+(?![.ef])', Number.Integer), # integer simple
        ]
    }

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\scintilla\IDLEenvironment.py ===
# Code that allows Pythonwin to pretend it is IDLE
# (at least as far as most IDLE extensions are concerned)

import string
import sys

import win32api
import win32con
import win32ui
from pywin import default_scintilla_encoding
from pywin.mfc.dialog import GetSimpleInput

wordchars = string.ascii_uppercase + string.ascii_lowercase + string.digits


class TextError(Exception):  # When a TclError would normally be raised.
    pass


class EmptyRange(Exception):  # Internally raised.
    pass


def GetIDLEModule(module):
    try:
        # First get it from Pythonwin it is exists.
        modname = "pywin.idle." + module
        __import__(modname)
    except ImportError as details:
        msg = (
            f"The IDLE extension '{module}' can not be located.\r\n\r\n"
            "Please correct the installation and restart the"
            f" application.\r\n\r\n{details}"
        )
        win32ui.MessageBox(msg)
        return None
    mod = sys.modules[modname]
    mod.TclError = TextError  # A hack that can go soon!
    return mod


# A class that is injected into the IDLE auto-indent extension.
# It allows for decent performance when opening a new file,
# as auto-indent uses the tokenizer module to determine indents.
# The default AutoIndent readline method works OK, but it goes through
# this layer of Tk index indirection for every single line.  For large files
# without indents (and even small files with indents :-) it was pretty slow!
def fast_readline(self):
    if self.finished:
        val = ""
    else:
        if "_scint_lines" not in self.__dict__:
            # XXX - note - assumes this is only called once the file is loaded!
            self._scint_lines = self.text.edit.GetTextRange().split("\n")
        sl = self._scint_lines
        i = self.i = self.i + 1
        if i >= len(sl):
            val = ""
        else:
            val = sl[i] + "\n"
    return val.encode(default_scintilla_encoding)


try:
    GetIDLEModule("AutoIndent").IndentSearcher.readline = fast_readline
except AttributeError:  # GetIDLEModule may return None
    pass


# A class that attempts to emulate an IDLE editor window.
# Construct with a Pythonwin view.
class IDLEEditorWindow:
    def __init__(self, edit):
        self.edit = edit
        self.text = TkText(edit)
        self.extensions = {}
        self.extension_menus = {}

    def close(self):
        self.edit = self.text = None
        self.extension_menus = None
        try:
            for ext in self.extensions.values():
                closer = getattr(ext, "close", None)
                if closer is not None:
                    closer()
        finally:
            self.extensions = {}

    def IDLEExtension(self, extension):
        ext = self.extensions.get(extension)
        if ext is not None:
            return ext
        mod = GetIDLEModule(extension)
        if mod is None:
            return None
        klass = getattr(mod, extension)
        ext = self.extensions[extension] = klass(self)
        # Find and bind all the events defined in the extension.
        events = [item for item in dir(klass) if item[-6:] == "_event"]
        for event in events:
            name = "<<{}>>".format(event[:-6].replace("_", "-"))
            self.edit.bindings.bind(name, getattr(ext, event))
        return ext

    def GetMenuItems(self, menu_name):
        # Get all menu items for the menu name (eg, "edit")
        bindings = self.edit.bindings
        ret = []
        for ext in self.extensions.values():
            menudefs = getattr(ext, "menudefs", [])
            for name, items in menudefs:
                if name == menu_name:
                    for text, event in [item for item in items if item is not None]:
                        text = text.replace("&", "&&")
                        text = text.replace("_", "&")
                        ret.append((text, event))
        return ret

    ######################################################################
    # The IDLE "Virtual UI" methods that are exposed to the IDLE extensions.
    #
    def askinteger(
        self, caption, prompt, parent=None, initialvalue=0, minvalue=None, maxvalue=None
    ):
        while 1:
            rc = GetSimpleInput(prompt, str(initialvalue), caption)
            if rc is None:
                return 0  # Correct "cancel" semantics?
            err = None
            try:
                rc = int(rc)
            except ValueError:
                err = "Please enter an integer"
            if not err and minvalue is not None and rc < minvalue:
                err = f"Please enter an integer greater then or equal to {minvalue}"
            if not err and maxvalue is not None and rc > maxvalue:
                err = f"Please enter an integer less then or equal to {maxvalue}"
            if err:
                win32ui.MessageBox(err, caption, win32con.MB_OK)
                continue
            return rc

    def askyesno(self, caption, prompt, parent=None):
        return win32ui.MessageBox(prompt, caption, win32con.MB_YESNO) == win32con.IDYES

    ######################################################################
    # The IDLE "Virtual Text Widget" methods that are exposed to the IDLE extensions.
    #

    # Is character at text_index in a Python string?  Return 0 for
    # "guaranteed no", true for anything else.
    def is_char_in_string(self, text_index):
        # A helper for the code analyser - we need internal knowledge of
        # the colorizer to get this information
        # This assumes the colorizer has got to this point!
        text_index = self.text._getoffset(text_index)
        c = self.text.edit._GetColorizer()
        if c and c.GetStringStyle(text_index) is None:
            return 0
        return 1

    # If a selection is defined in the text widget, return
    # (start, end) as Tkinter text indices, otherwise return
    # (None, None)
    def get_selection_indices(self):
        try:
            first = self.text.index("sel.first")
            last = self.text.index("sel.last")
            return first, last
        except TextError:
            return None, None

    def set_tabwidth(self, width):
        self.edit.SCISetTabWidth(width)

    def get_tabwidth(self):
        return self.edit.GetTabWidth()


# A class providing the generic "Call Tips" interface
class CallTips:
    def __init__(self, edit):
        self.edit = edit

    def showtip(self, tip_text):
        self.edit.SCICallTipShow(tip_text)

    def hidetip(self):
        self.edit.SCICallTipCancel()


########################################
#
# Helpers for the TkText emulation.
def TkOffsetToIndex(offset, edit):
    lineoff = 0
    # May be 1 > actual end if we pretended there was a trailing '\n'
    offset = min(offset, edit.GetTextLength())
    line = edit.LineFromChar(offset)
    lineIndex = edit.LineIndex(line)
    return "%d.%d" % (line + 1, offset - lineIndex)


def _NextTok(str, pos):
    # Returns (token, endPos)
    end = len(str)
    if pos >= end:
        return None, 0
    while pos < end and str[pos] in string.whitespace:
        pos += 1
    # Special case for +-
    if str[pos] in "+-":
        return str[pos], pos + 1
    # Digits also a special case.
    endPos = pos
    while endPos < end and str[endPos] in string.digits + ".":
        endPos += 1
    if pos != endPos:
        return str[pos:endPos], endPos
    endPos = pos
    while endPos < end and str[endPos] not in string.whitespace + string.digits + "+-":
        endPos += 1
    if pos != endPos:
        return str[pos:endPos], endPos
    return None, 0


def TkIndexToOffset(bm, edit, marks):
    base, nextTokPos = _NextTok(bm, 0)
    if base is None:
        raise ValueError("Empty bookmark ID!")
    if base.find(".") > 0:
        try:
            line, col = base.split(".", 2)
            if col == "first" or col == "last":
                # Tag name
                if line != "sel":
                    raise ValueError("Tags aren't here!")
                sel = edit.GetSel()
                if sel[0] == sel[1]:
                    raise EmptyRange
                if col == "first":
                    pos = sel[0]
                else:
                    pos = sel[1]
            else:
                # Lines are 1 based for tkinter
                line = int(line) - 1
                if line > edit.GetLineCount():
                    pos = edit.GetTextLength() + 1
                else:
                    pos = edit.LineIndex(line)
                    if pos == -1:
                        pos = edit.GetTextLength()
                    pos += int(col)
        except (ValueError, IndexError):
            raise ValueError("Unexpected literal in '%s'" % base)
    elif base == "insert":
        pos = edit.GetSel()[0]
    elif base == "end":
        pos = edit.GetTextLength()
        # Pretend there is a trailing '\n' if necessary
        if pos and edit.SCIGetCharAt(pos - 1) != "\n":
            pos += 1
    else:
        try:
            pos = marks[base]
        except KeyError:
            raise ValueError("Unsupported base offset or undefined mark '%s'" % base)

    while 1:
        word, nextTokPos = _NextTok(bm, nextTokPos)
        if word is None:
            break
        if word in ("+", "-"):
            num, nextTokPos = _NextTok(bm, nextTokPos)
            if num is None:
                raise ValueError("+/- operator needs 2 args")
            what, nextTokPos = _NextTok(bm, nextTokPos)
            if what is None:
                raise ValueError("+/- operator needs 2 args")
            if what[0] != "c":
                raise ValueError("+/- only supports chars")
            if word == "+":
                pos += int(num)
            else:
                pos -= int(num)
        elif word == "wordstart":
            while pos > 0 and edit.SCIGetCharAt(pos - 1) in wordchars:
                pos -= 1
        elif word == "wordend":
            end = edit.GetTextLength()
            while pos < end and edit.SCIGetCharAt(pos) in wordchars:
                pos += 1
        elif word == "linestart":
            while pos > 0 and edit.SCIGetCharAt(pos - 1) not in "\n\r":
                pos -= 1
        elif word == "lineend":
            end = edit.GetTextLength()
            while pos < end and edit.SCIGetCharAt(pos) not in "\n\r":
                pos += 1
        else:
            raise ValueError("Unsupported relative offset '%s'" % word)
    return max(pos, 0)  # Tkinter is tollerant of -ve indexes - we aren't


# A class that resembles an IDLE (ie, a Tk) text widget.
# Construct with an edit object (eg, an editor view)
class TkText:
    def __init__(self, edit):
        self.calltips = None
        self.edit = edit
        self.marks = {}

    ##	def __getattr__(self, attr):
    ##		if attr=="tk": return self # So text.tk.call works.
    ##		if attr=="master": return None # ditto!
    ##		raise AttributeError, attr
    ##	def __getitem__(self, item):
    ##		if item=="tabs":
    ##			size = self.edit.GetTabWidth()
    ##			if size==8: return "" # Tk default
    ##			return size # correct semantics?
    ##		elif item=="font": # Used for measurements we don't need to do!
    ##			return "Don't know the font"
    ##		raise IndexError, "Invalid index '%s'" % item
    def make_calltip_window(self):
        if self.calltips is None:
            self.calltips = CallTips(self.edit)
        return self.calltips

    def _getoffset(self, index):
        return TkIndexToOffset(index, self.edit, self.marks)

    def _getindex(self, off):
        return TkOffsetToIndex(off, self.edit)

    def _fix_indexes(self, start, end):
        # first some magic to handle skipping over utf8 extended chars.
        while start > 0 and ord(self.edit.SCIGetCharAt(start)) & 0xC0 == 0x80:
            start -= 1
        while (
            end < self.edit.GetTextLength()
            and ord(self.edit.SCIGetCharAt(end)) & 0xC0 == 0x80
        ):
            end += 1
        # now handling fixing \r\n->\n disparities...
        if (
            start > 0
            and self.edit.SCIGetCharAt(start) == "\n"
            and self.edit.SCIGetCharAt(start - 1) == "\r"
        ):
            start -= 1
        if (
            end < self.edit.GetTextLength()
            and self.edit.SCIGetCharAt(end - 1) == "\r"
            and self.edit.SCIGetCharAt(end) == "\n"
        ):
            end += 1
        return start, end

    ##	def get_tab_width(self):
    ##		return self.edit.GetTabWidth()
    ##	def call(self, *rest):
    ##		# Crap to support Tk measurement hacks for tab widths
    ##		if rest[0] != "font" or rest[1] != "measure":
    ##			raise ValueError, "Unsupport call type"
    ##		return len(rest[5])
    ##	def configure(self, **kw):
    ##		for name, val in kw.items():
    ##			if name=="tabs":
    ##				self.edit.SCISetTabWidth(int(val))
    ##			else:
    ##				raise ValueError, "Unsupported configuration item %s" % kw
    def bind(self, binding, handler):
        self.edit.bindings.bind(binding, handler)

    def get(self, start, end=None):
        try:
            start = self._getoffset(start)
            if end is None:
                end = start + 1
            else:
                end = self._getoffset(end)
        except EmptyRange:
            return ""
        # Simple semantic checks to conform to the Tk text interface
        if end <= start:
            return ""
        max = self.edit.GetTextLength()
        checkEnd = 0
        if end > max:
            end = max
            checkEnd = 1
        start, end = self._fix_indexes(start, end)
        ret = self.edit.GetTextRange(start, end)
        # pretend a trailing '\n' exists if necessary.
        if checkEnd and (not ret or ret[-1] != "\n"):
            ret += "\n"
        return ret.replace("\r", "")

    def index(self, spec):
        try:
            return self._getindex(self._getoffset(spec))
        except EmptyRange:
            return ""

    def insert(self, pos, text):
        try:
            pos = self._getoffset(pos)
        except EmptyRange:
            raise TextError("Empty range")
        self.edit.SetSel((pos, pos))
        # IDLE only deals with "\n" - we will be nicer

        bits = text.split("\n")
        self.edit.SCIAddText(bits[0])
        for bit in bits[1:]:
            self.edit.SCINewline()
            self.edit.SCIAddText(bit)

    def delete(self, start, end=None):
        try:
            start = self._getoffset(start)
            if end is not None:
                end = self._getoffset(end)
        except EmptyRange:
            raise TextError("Empty range")
        # If end is specified and == start, then we must delete nothing.
        if start == end:
            return
        # If end is not specified, delete one char
        if end is None:
            end = start + 1
        else:
            # Tk says not to delete in this case, but our control would.
            if end < start:
                return
        if start == self.edit.GetTextLength():
            return  # Nothing to delete.
        old = self.edit.GetSel()[0]  # Lose a selection
        # Hack for partial '\r\n' and UTF-8 char removal
        start, end = self._fix_indexes(start, end)
        self.edit.SetSel((start, end))
        self.edit.Clear()
        if old >= start and old < end:
            old = start
        elif old >= end:
            old -= end - start
        self.edit.SetSel(old)

    def bell(self):
        win32api.MessageBeep()

    def see(self, pos):
        # Most commands we use in Scintilla actually force the selection
        # to be seen, making this unnecessary.
        pass

    def mark_set(self, name, pos):
        try:
            pos = self._getoffset(pos)
        except EmptyRange:
            raise TextError("Empty range '%s'" % pos)
        if name == "insert":
            self.edit.SetSel(pos)
        else:
            self.marks[name] = pos

    def tag_add(self, name, start, end):
        if name != "sel":
            raise ValueError("Only sel tag is supported")
        try:
            start = self._getoffset(start)
            end = self._getoffset(end)
        except EmptyRange:
            raise TextError("Empty range")
        self.edit.SetSel(start, end)

    def tag_remove(self, name, start, end):
        if name != "sel" or start != "1.0" or end != "end":
            raise ValueError("Can't remove this tag")
        # Turn the sel into a cursor
        self.edit.SetSel(self.edit.GetSel()[0])

    def compare(self, i1, op, i2):
        try:
            i1 = self._getoffset(i1)
        except EmptyRange:
            i1 = ""
        try:
            i2 = self._getoffset(i2)
        except EmptyRange:
            i2 = ""
        return eval("%d%s%d" % (i1, op, i2))

    def undo_block_start(self):
        self.edit.SCIBeginUndoAction()

    def undo_block_stop(self):
        self.edit.SCIEndUndoAction()


######################################################################
#
# Test related code.
#
######################################################################
def TestCheck(index, edit, expected=None):
    rc = TkIndexToOffset(index, edit, {})
    if rc != expected:
        print("ERROR: Index", index, ", expected", expected, "but got", rc)


def TestGet(fr, to, t, expected):
    got = t.get(fr, to)
    if got != expected:
        print(f"ERROR: get({fr!r}, {to!r}) expected {expected!r}, but got {got!r}")


def test():
    import pywin.framework.editor

    d = pywin.framework.editor.editorTemplate.OpenDocumentFile(None)
    e = d.GetFirstView()
    t = TkText(e)
    e.SCIAddText("hi there how\nare you today\r\nI hope you are well")
    e.SetSel((4, 4))

    skip = """
    TestCheck("insert", e, 4)
    TestCheck("insert wordstart", e, 3)
    TestCheck("insert wordend", e, 8)
    TestCheck("insert linestart", e, 0)
    TestCheck("insert lineend", e, 12)
    TestCheck("insert + 4 chars", e, 8)
    TestCheck("insert +4c", e, 8)
    TestCheck("insert - 2 chars", e, 2)
    TestCheck("insert -2c", e, 2)
    TestCheck("insert-2c", e, 2)
    TestCheck("insert-2 c", e, 2)
    TestCheck("insert- 2c", e, 2)
    TestCheck("1.1", e, 1)
    TestCheck("1.0", e, 0)
    TestCheck("2.0", e, 13)
    try:
        TestCheck("sel.first", e, 0)
        print("*** sel.first worked with an empty selection")
    except TextError:
        pass
    e.SetSel((4,5))
    TestCheck("sel.first- 2c", e, 2)
    TestCheck("sel.last- 2c", e, 3)
    """
    # Check EOL semantics
    e.SetSel((4, 4))
    TestGet("insert lineend", "insert lineend +1c", t, "\n")
    e.SetSel((20, 20))
    TestGet("insert lineend", "insert lineend +1c", t, "\n")
    e.SetSel((35, 35))
    TestGet("insert lineend", "insert lineend +1c", t, "\n")


class IDLEWrapper:
    def __init__(self, control):
        self.text = control


def IDLETest(extension):
    import os
    import sys

    modname = "pywin.idle." + extension
    __import__(modname)
    mod = sys.modules[modname]
    mod.TclError = TextError
    klass = getattr(mod, extension)

    # Create a new Scintilla Window.
    import pywin.framework.editor

    d = pywin.framework.editor.editorTemplate.OpenDocumentFile(None)
    v = d.GetFirstView()
    fname = os.path.splitext(__file__)[0] + ".py"
    v.SCIAddText(open(fname).read())
    d.SetModifiedFlag(0)
    r = klass(IDLEWrapper(TkText(v)))
    return r


if __name__ == "__main__":
    test()

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\retriever_service\transports\base.py ===
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
import abc
from typing import Awaitable, Callable, Dict, Optional, Sequence, Union

import google.api_core
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.oauth2 import service_account  # type: ignore
from google.protobuf import empty_pb2  # type: ignore

from google.ai.generativelanguage_v1beta import gapic_version as package_version
from google.ai.generativelanguage_v1beta.types import retriever, retriever_service

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class RetrieverServiceTransport(abc.ABC):
    """Abstract transport class for RetrieverService."""

    AUTH_SCOPES = ()

    DEFAULT_HOST: str = "generativelanguage.googleapis.com"

    def __init__(
        self,
        *,
        host: str = DEFAULT_HOST,
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
        **kwargs,
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
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A list of scopes.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
        """

        scopes_kwargs = {"scopes": scopes, "default_scopes": self.AUTH_SCOPES}

        # Save the scopes.
        self._scopes = scopes

        # If no credentials are provided, then determine the appropriate
        # defaults.
        if credentials and credentials_file:
            raise core_exceptions.DuplicateCredentialArgs(
                "'credentials_file' and 'credentials' are mutually exclusive"
            )

        if credentials_file is not None:
            credentials, _ = google.auth.load_credentials_from_file(
                credentials_file, **scopes_kwargs, quota_project_id=quota_project_id
            )
        elif credentials is None:
            credentials, _ = google.auth.default(
                **scopes_kwargs, quota_project_id=quota_project_id
            )
            # Don't apply audience if the credentials file passed from user.
            if hasattr(credentials, "with_gdch_audience"):
                credentials = credentials.with_gdch_audience(
                    api_audience if api_audience else host
                )

        # If the credentials are service account credentials, then always try to use self signed JWT.
        if (
            always_use_jwt_access
            and isinstance(credentials, service_account.Credentials)
            and hasattr(service_account.Credentials, "with_always_use_jwt_access")
        ):
            credentials = credentials.with_always_use_jwt_access(True)

        # Save the credentials.
        self._credentials = credentials

        # Save the hostname. Default to port 443 (HTTPS) if none is specified.
        if ":" not in host:
            host += ":443"
        self._host = host

    @property
    def host(self):
        return self._host

    def _prep_wrapped_messages(self, client_info):
        # Precompute the wrapped methods.
        self._wrapped_methods = {
            self.create_corpus: gapic_v1.method.wrap_method(
                self.create_corpus,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.get_corpus: gapic_v1.method.wrap_method(
                self.get_corpus,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.update_corpus: gapic_v1.method.wrap_method(
                self.update_corpus,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.delete_corpus: gapic_v1.method.wrap_method(
                self.delete_corpus,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.list_corpora: gapic_v1.method.wrap_method(
                self.list_corpora,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.query_corpus: gapic_v1.method.wrap_method(
                self.query_corpus,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.create_document: gapic_v1.method.wrap_method(
                self.create_document,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.get_document: gapic_v1.method.wrap_method(
                self.get_document,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.update_document: gapic_v1.method.wrap_method(
                self.update_document,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.delete_document: gapic_v1.method.wrap_method(
                self.delete_document,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.list_documents: gapic_v1.method.wrap_method(
                self.list_documents,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.query_document: gapic_v1.method.wrap_method(
                self.query_document,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.create_chunk: gapic_v1.method.wrap_method(
                self.create_chunk,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.batch_create_chunks: gapic_v1.method.wrap_method(
                self.batch_create_chunks,
                default_timeout=None,
                client_info=client_info,
            ),
            self.get_chunk: gapic_v1.method.wrap_method(
                self.get_chunk,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.update_chunk: gapic_v1.method.wrap_method(
                self.update_chunk,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.batch_update_chunks: gapic_v1.method.wrap_method(
                self.batch_update_chunks,
                default_timeout=None,
                client_info=client_info,
            ),
            self.delete_chunk: gapic_v1.method.wrap_method(
                self.delete_chunk,
                default_retry=retries.Retry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.batch_delete_chunks: gapic_v1.method.wrap_method(
                self.batch_delete_chunks,
                default_timeout=None,
                client_info=client_info,
            ),
            self.list_chunks: gapic_v1.method.wrap_method(
                self.list_chunks,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        """Closes resources associated with the transport.

        .. warning::
             Only call this method if the transport is NOT shared
             with other clients - this may cause errors in other clients!
        """
        raise NotImplementedError()

    @property
    def create_corpus(
        self,
    ) -> Callable[
        [retriever_service.CreateCorpusRequest],
        Union[retriever.Corpus, Awaitable[retriever.Corpus]],
    ]:
        raise NotImplementedError()

    @property
    def get_corpus(
        self,
    ) -> Callable[
        [retriever_service.GetCorpusRequest],
        Union[retriever.Corpus, Awaitable[retriever.Corpus]],
    ]:
        raise NotImplementedError()

    @property
    def update_corpus(
        self,
    ) -> Callable[
        [retriever_service.UpdateCorpusRequest],
        Union[retriever.Corpus, Awaitable[retriever.Corpus]],
    ]:
        raise NotImplementedError()

    @property
    def delete_corpus(
        self,
    ) -> Callable[
        [retriever_service.DeleteCorpusRequest],
        Union[empty_pb2.Empty, Awaitable[empty_pb2.Empty]],
    ]:
        raise NotImplementedError()

    @property
    def list_corpora(
        self,
    ) -> Callable[
        [retriever_service.ListCorporaRequest],
        Union[
            retriever_service.ListCorporaResponse,
            Awaitable[retriever_service.ListCorporaResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def query_corpus(
        self,
    ) -> Callable[
        [retriever_service.QueryCorpusRequest],
        Union[
            retriever_service.QueryCorpusResponse,
            Awaitable[retriever_service.QueryCorpusResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def create_document(
        self,
    ) -> Callable[
        [retriever_service.CreateDocumentRequest],
        Union[retriever.Document, Awaitable[retriever.Document]],
    ]:
        raise NotImplementedError()

    @property
    def get_document(
        self,
    ) -> Callable[
        [retriever_service.GetDocumentRequest],
        Union[retriever.Document, Awaitable[retriever.Document]],
    ]:
        raise NotImplementedError()

    @property
    def update_document(
        self,
    ) -> Callable[
        [retriever_service.UpdateDocumentRequest],
        Union[retriever.Document, Awaitable[retriever.Document]],
    ]:
        raise NotImplementedError()

    @property
    def delete_document(
        self,
    ) -> Callable[
        [retriever_service.DeleteDocumentRequest],
        Union[empty_pb2.Empty, Awaitable[empty_pb2.Empty]],
    ]:
        raise NotImplementedError()

    @property
    def list_documents(
        self,
    ) -> Callable[
        [retriever_service.ListDocumentsRequest],
        Union[
            retriever_service.ListDocumentsResponse,
            Awaitable[retriever_service.ListDocumentsResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def query_document(
        self,
    ) -> Callable[
        [retriever_service.QueryDocumentRequest],
        Union[
            retriever_service.QueryDocumentResponse,
            Awaitable[retriever_service.QueryDocumentResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def create_chunk(
        self,
    ) -> Callable[
        [retriever_service.CreateChunkRequest],
        Union[retriever.Chunk, Awaitable[retriever.Chunk]],
    ]:
        raise NotImplementedError()

    @property
    def batch_create_chunks(
        self,
    ) -> Callable[
        [retriever_service.BatchCreateChunksRequest],
        Union[
            retriever_service.BatchCreateChunksResponse,
            Awaitable[retriever_service.BatchCreateChunksResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def get_chunk(
        self,
    ) -> Callable[
        [retriever_service.GetChunkRequest],
        Union[retriever.Chunk, Awaitable[retriever.Chunk]],
    ]:
        raise NotImplementedError()

    @property
    def update_chunk(
        self,
    ) -> Callable[
        [retriever_service.UpdateChunkRequest],
        Union[retriever.Chunk, Awaitable[retriever.Chunk]],
    ]:
        raise NotImplementedError()

    @property
    def batch_update_chunks(
        self,
    ) -> Callable[
        [retriever_service.BatchUpdateChunksRequest],
        Union[
            retriever_service.BatchUpdateChunksResponse,
            Awaitable[retriever_service.BatchUpdateChunksResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def delete_chunk(
        self,
    ) -> Callable[
        [retriever_service.DeleteChunkRequest],
        Union[empty_pb2.Empty, Awaitable[empty_pb2.Empty]],
    ]:
        raise NotImplementedError()

    @property
    def batch_delete_chunks(
        self,
    ) -> Callable[
        [retriever_service.BatchDeleteChunksRequest],
        Union[empty_pb2.Empty, Awaitable[empty_pb2.Empty]],
    ]:
        raise NotImplementedError()

    @property
    def list_chunks(
        self,
    ) -> Callable[
        [retriever_service.ListChunksRequest],
        Union[
            retriever_service.ListChunksResponse,
            Awaitable[retriever_service.ListChunksResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("RetrieverServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\httpcore\_async\http2.py ===
from __future__ import annotations

import enum
import logging
import time
import types
import typing

import h2.config
import h2.connection
import h2.events
import h2.exceptions
import h2.settings

from .._backends.base import AsyncNetworkStream
from .._exceptions import (
    ConnectionNotAvailable,
    LocalProtocolError,
    RemoteProtocolError,
)
from .._models import Origin, Request, Response
from .._synchronization import AsyncLock, AsyncSemaphore, AsyncShieldCancellation
from .._trace import Trace
from .interfaces import AsyncConnectionInterface

logger = logging.getLogger("httpcore.http2")


def has_body_headers(request: Request) -> bool:
    return any(
        k.lower() == b"content-length" or k.lower() == b"transfer-encoding"
        for k, v in request.headers
    )


class HTTPConnectionState(enum.IntEnum):
    ACTIVE = 1
    IDLE = 2
    CLOSED = 3


class AsyncHTTP2Connection(AsyncConnectionInterface):
    READ_NUM_BYTES = 64 * 1024
    CONFIG = h2.config.H2Configuration(validate_inbound_headers=False)

    def __init__(
        self,
        origin: Origin,
        stream: AsyncNetworkStream,
        keepalive_expiry: float | None = None,
    ):
        self._origin = origin
        self._network_stream = stream
        self._keepalive_expiry: float | None = keepalive_expiry
        self._h2_state = h2.connection.H2Connection(config=self.CONFIG)
        self._state = HTTPConnectionState.IDLE
        self._expire_at: float | None = None
        self._request_count = 0
        self._init_lock = AsyncLock()
        self._state_lock = AsyncLock()
        self._read_lock = AsyncLock()
        self._write_lock = AsyncLock()
        self._sent_connection_init = False
        self._used_all_stream_ids = False
        self._connection_error = False

        # Mapping from stream ID to response stream events.
        self._events: dict[
            int,
            list[
                h2.events.ResponseReceived
                | h2.events.DataReceived
                | h2.events.StreamEnded
                | h2.events.StreamReset,
            ],
        ] = {}

        # Connection terminated events are stored as state since
        # we need to handle them for all streams.
        self._connection_terminated: h2.events.ConnectionTerminated | None = None

        self._read_exception: Exception | None = None
        self._write_exception: Exception | None = None

    async def handle_async_request(self, request: Request) -> Response:
        if not self.can_handle_request(request.url.origin):
            # This cannot occur in normal operation, since the connection pool
            # will only send requests on connections that handle them.
            # It's in place simply for resilience as a guard against incorrect
            # usage, for anyone working directly with httpcore connections.
            raise RuntimeError(
                f"Attempted to send request to {request.url.origin} on connection "
                f"to {self._origin}"
            )

        async with self._state_lock:
            if self._state in (HTTPConnectionState.ACTIVE, HTTPConnectionState.IDLE):
                self._request_count += 1
                self._expire_at = None
                self._state = HTTPConnectionState.ACTIVE
            else:
                raise ConnectionNotAvailable()

        async with self._init_lock:
            if not self._sent_connection_init:
                try:
                    sci_kwargs = {"request": request}
                    async with Trace(
                        "send_connection_init", logger, request, sci_kwargs
                    ):
                        await self._send_connection_init(**sci_kwargs)
                except BaseException as exc:
                    with AsyncShieldCancellation():
                        await self.aclose()
                    raise exc

                self._sent_connection_init = True

                # Initially start with just 1 until the remote server provides
                # its max_concurrent_streams value
                self._max_streams = 1

                local_settings_max_streams = (
                    self._h2_state.local_settings.max_concurrent_streams
                )
                self._max_streams_semaphore = AsyncSemaphore(local_settings_max_streams)

                for _ in range(local_settings_max_streams - self._max_streams):
                    await self._max_streams_semaphore.acquire()

        await self._max_streams_semaphore.acquire()

        try:
            stream_id = self._h2_state.get_next_available_stream_id()
            self._events[stream_id] = []
        except h2.exceptions.NoAvailableStreamIDError:  # pragma: nocover
            self._used_all_stream_ids = True
            self._request_count -= 1
            raise ConnectionNotAvailable()

        try:
            kwargs = {"request": request, "stream_id": stream_id}
            async with Trace("send_request_headers", logger, request, kwargs):
                await self._send_request_headers(request=request, stream_id=stream_id)
            async with Trace("send_request_body", logger, request, kwargs):
                await self._send_request_body(request=request, stream_id=stream_id)
            async with Trace(
                "receive_response_headers", logger, request, kwargs
            ) as trace:
                status, headers = await self._receive_response(
                    request=request, stream_id=stream_id
                )
                trace.return_value = (status, headers)

            return Response(
                status=status,
                headers=headers,
                content=HTTP2ConnectionByteStream(self, request, stream_id=stream_id),
                extensions={
                    "http_version": b"HTTP/2",
                    "network_stream": self._network_stream,
                    "stream_id": stream_id,
                },
            )
        except BaseException as exc:  # noqa: PIE786
            with AsyncShieldCancellation():
                kwargs = {"stream_id": stream_id}
                async with Trace("response_closed", logger, request, kwargs):
                    await self._response_closed(stream_id=stream_id)

            if isinstance(exc, h2.exceptions.ProtocolError):
                # One case where h2 can raise a protocol error is when a
                # closed frame has been seen by the state machine.
                #
                # This happens when one stream is reading, and encounters
                # a GOAWAY event. Other flows of control may then raise
                # a protocol error at any point they interact with the 'h2_state'.
                #
                # In this case we'll have stored the event, and should raise
                # it as a RemoteProtocolError.
                if self._connection_terminated:  # pragma: nocover
                    raise RemoteProtocolError(self._connection_terminated)
                # If h2 raises a protocol error in some other state then we
                # must somehow have made a protocol violation.
                raise LocalProtocolError(exc)  # pragma: nocover

            raise exc

    async def _send_connection_init(self, request: Request) -> None:
        """
        The HTTP/2 connection requires some initial setup before we can start
        using individual request/response streams on it.
        """
        # Need to set these manually here instead of manipulating via
        # __setitem__() otherwise the H2Connection will emit SettingsUpdate
        # frames in addition to sending the undesired defaults.
        self._h2_state.local_settings = h2.settings.Settings(
            client=True,
            initial_values={
                # Disable PUSH_PROMISE frames from the server since we don't do anything
                # with them for now.  Maybe when we support caching?
                h2.settings.SettingCodes.ENABLE_PUSH: 0,
                # These two are taken from h2 for safe defaults
                h2.settings.SettingCodes.MAX_CONCURRENT_STREAMS: 100,
                h2.settings.SettingCodes.MAX_HEADER_LIST_SIZE: 65536,
            },
        )

        # Some websites (*cough* Yahoo *cough*) balk at this setting being
        # present in the initial handshake since it's not defined in the original
        # RFC despite the RFC mandating ignoring settings you don't know about.
        del self._h2_state.local_settings[
            h2.settings.SettingCodes.ENABLE_CONNECT_PROTOCOL
        ]

        self._h2_state.initiate_connection()
        self._h2_state.increment_flow_control_window(2**24)
        await self._write_outgoing_data(request)

    # Sending the request...

    async def _send_request_headers(self, request: Request, stream_id: int) -> None:
        """
        Send the request headers to a given stream ID.
        """
        end_stream = not has_body_headers(request)

        # In HTTP/2 the ':authority' pseudo-header is used instead of 'Host'.
        # In order to gracefully handle HTTP/1.1 and HTTP/2 we always require
        # HTTP/1.1 style headers, and map them appropriately if we end up on
        # an HTTP/2 connection.
        authority = [v for k, v in request.headers if k.lower() == b"host"][0]

        headers = [
            (b":method", request.method),
            (b":authority", authority),
            (b":scheme", request.url.scheme),
            (b":path", request.url.target),
        ] + [
            (k.lower(), v)
            for k, v in request.headers
            if k.lower()
            not in (
                b"host",
                b"transfer-encoding",
            )
        ]

        self._h2_state.send_headers(stream_id, headers, end_stream=end_stream)
        self._h2_state.increment_flow_control_window(2**24, stream_id=stream_id)
        await self._write_outgoing_data(request)

    async def _send_request_body(self, request: Request, stream_id: int) -> None:
        """
        Iterate over the request body sending it to a given stream ID.
        """
        if not has_body_headers(request):
            return

        assert isinstance(request.stream, typing.AsyncIterable)
        async for data in request.stream:
            await self._send_stream_data(request, stream_id, data)
        await self._send_end_stream(request, stream_id)

    async def _send_stream_data(
        self, request: Request, stream_id: int, data: bytes
    ) -> None:
        """
        Send a single chunk of data in one or more data frames.
        """
        while data:
            max_flow = await self._wait_for_outgoing_flow(request, stream_id)
            chunk_size = min(len(data), max_flow)
            chunk, data = data[:chunk_size], data[chunk_size:]
            self._h2_state.send_data(stream_id, chunk)
            await self._write_outgoing_data(request)

    async def _send_end_stream(self, request: Request, stream_id: int) -> None:
        """
        Send an empty data frame on on a given stream ID with the END_STREAM flag set.
        """
        self._h2_state.end_stream(stream_id)
        await self._write_outgoing_data(request)

    # Receiving the response...

    async def _receive_response(
        self, request: Request, stream_id: int
    ) -> tuple[int, list[tuple[bytes, bytes]]]:
        """
        Return the response status code and headers for a given stream ID.
        """
        while True:
            event = await self._receive_stream_event(request, stream_id)
            if isinstance(event, h2.events.ResponseReceived):
                break

        status_code = 200
        headers = []
        assert event.headers is not None
        for k, v in event.headers:
            if k == b":status":
                status_code = int(v.decode("ascii", errors="ignore"))
            elif not k.startswith(b":"):
                headers.append((k, v))

        return (status_code, headers)

    async def _receive_response_body(
        self, request: Request, stream_id: int
    ) -> typing.AsyncIterator[bytes]:
        """
        Iterator that returns the bytes of the response body for a given stream ID.
        """
        while True:
            event = await self._receive_stream_event(request, stream_id)
            if isinstance(event, h2.events.DataReceived):
                assert event.flow_controlled_length is not None
                assert event.data is not None
                amount = event.flow_controlled_length
                self._h2_state.acknowledge_received_data(amount, stream_id)
                await self._write_outgoing_data(request)
                yield event.data
            elif isinstance(event, h2.events.StreamEnded):
                break

    async def _receive_stream_event(
        self, request: Request, stream_id: int
    ) -> h2.events.ResponseReceived | h2.events.DataReceived | h2.events.StreamEnded:
        """
        Return the next available event for a given stream ID.

        Will read more data from the network if required.
        """
        while not self._events.get(stream_id):
            await self._receive_events(request, stream_id)
        event = self._events[stream_id].pop(0)
        if isinstance(event, h2.events.StreamReset):
            raise RemoteProtocolError(event)
        return event

    async def _receive_events(
        self, request: Request, stream_id: int | None = None
    ) -> None:
        """
        Read some data from the network until we see one or more events
        for a given stream ID.
        """
        async with self._read_lock:
            if self._connection_terminated is not None:
                last_stream_id = self._connection_terminated.last_stream_id
                if stream_id and last_stream_id and stream_id > last_stream_id:
                    self._request_count -= 1
                    raise ConnectionNotAvailable()
                raise RemoteProtocolError(self._connection_terminated)

            # This conditional is a bit icky. We don't want to block reading if we've
            # actually got an event to return for a given stream. We need to do that
            # check *within* the atomic read lock. Though it also need to be optional,
            # because when we call it from `_wait_for_outgoing_flow` we *do* want to
            # block until we've available flow control, event when we have events
            # pending for the stream ID we're attempting to send on.
            if stream_id is None or not self._events.get(stream_id):
                events = await self._read_incoming_data(request)
                for event in events:
                    if isinstance(event, h2.events.RemoteSettingsChanged):
                        async with Trace(
                            "receive_remote_settings", logger, request
                        ) as trace:
                            await self._receive_remote_settings_change(event)
                            trace.return_value = event

                    elif isinstance(
                        event,
                        (
                            h2.events.ResponseReceived,
                            h2.events.DataReceived,
                            h2.events.StreamEnded,
                            h2.events.StreamReset,
                        ),
                    ):
                        if event.stream_id in self._events:
                            self._events[event.stream_id].append(event)

                    elif isinstance(event, h2.events.ConnectionTerminated):
                        self._connection_terminated = event

        await self._write_outgoing_data(request)

    async def _receive_remote_settings_change(
        self, event: h2.events.RemoteSettingsChanged
    ) -> None:
        max_concurrent_streams = event.changed_settings.get(
            h2.settings.SettingCodes.MAX_CONCURRENT_STREAMS
        )
        if max_concurrent_streams:
            new_max_streams = min(
                max_concurrent_streams.new_value,
                self._h2_state.local_settings.max_concurrent_streams,
            )
            if new_max_streams and new_max_streams != self._max_streams:
                while new_max_streams > self._max_streams:
                    await self._max_streams_semaphore.release()
                    self._max_streams += 1
                while new_max_streams < self._max_streams:
                    await self._max_streams_semaphore.acquire()
                    self._max_streams -= 1

    async def _response_closed(self, stream_id: int) -> None:
        await self._max_streams_semaphore.release()
        del self._events[stream_id]
        async with self._state_lock:
            if self._connection_terminated and not self._events:
                await self.aclose()

            elif self._state == HTTPConnectionState.ACTIVE and not self._events:
                self._state = HTTPConnectionState.IDLE
                if self._keepalive_expiry is not None:
                    now = time.monotonic()
                    self._expire_at = now + self._keepalive_expiry
                if self._used_all_stream_ids:  # pragma: nocover
                    await self.aclose()

    async def aclose(self) -> None:
        # Note that this method unilaterally closes the connection, and does
        # not have any kind of locking in place around it.
        self._h2_state.close_connection()
        self._state = HTTPConnectionState.CLOSED
        await self._network_stream.aclose()

    # Wrappers around network read/write operations...

    async def _read_incoming_data(self, request: Request) -> list[h2.events.Event]:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("read", None)

        if self._read_exception is not None:
            raise self._read_exception  # pragma: nocover

        try:
            data = await self._network_stream.read(self.READ_NUM_BYTES, timeout)
            if data == b"":
                raise RemoteProtocolError("Server disconnected")
        except Exception as exc:
            # If we get a network error we should:
            #
            # 1. Save the exception and just raise it immediately on any future reads.
            #    (For example, this means that a single read timeout or disconnect will
            #    immediately close all pending streams. Without requiring multiple
            #    sequential timeouts.)
            # 2. Mark the connection as errored, so that we don't accept any other
            #    incoming requests.
            self._read_exception = exc
            self._connection_error = True
            raise exc

        events: list[h2.events.Event] = self._h2_state.receive_data(data)

        return events

    async def _write_outgoing_data(self, request: Request) -> None:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("write", None)

        async with self._write_lock:
            data_to_send = self._h2_state.data_to_send()

            if self._write_exception is not None:
                raise self._write_exception  # pragma: nocover

            try:
                await self._network_stream.write(data_to_send, timeout)
            except Exception as exc:  # pragma: nocover
                # If we get a network error we should:
                #
                # 1. Save the exception and just raise it immediately on any future write.
                #    (For example, this means that a single write timeout or disconnect will
                #    immediately close all pending streams. Without requiring multiple
                #    sequential timeouts.)
                # 2. Mark the connection as errored, so that we don't accept any other
                #    incoming requests.
                self._write_exception = exc
                self._connection_error = True
                raise exc

    # Flow control...

    async def _wait_for_outgoing_flow(self, request: Request, stream_id: int) -> int:
        """
        Returns the maximum allowable outgoing flow for a given stream.

        If the allowable flow is zero, then waits on the network until
        WindowUpdated frames have increased the flow rate.
        https://tools.ietf.org/html/rfc7540#section-6.9
        """
        local_flow: int = self._h2_state.local_flow_control_window(stream_id)
        max_frame_size: int = self._h2_state.max_outbound_frame_size
        flow = min(local_flow, max_frame_size)
        while flow == 0:
            await self._receive_events(request)
            local_flow = self._h2_state.local_flow_control_window(stream_id)
            max_frame_size = self._h2_state.max_outbound_frame_size
            flow = min(local_flow, max_frame_size)
        return flow

    # Interface for connection pooling...

    def can_handle_request(self, origin: Origin) -> bool:
        return origin == self._origin

    def is_available(self) -> bool:
        return (
            self._state != HTTPConnectionState.CLOSED
            and not self._connection_error
            and not self._used_all_stream_ids
            and not (
                self._h2_state.state_machine.state
                == h2.connection.ConnectionState.CLOSED
            )
        )

    def has_expired(self) -> bool:
        now = time.monotonic()
        return self._expire_at is not None and now > self._expire_at

    def is_idle(self) -> bool:
        return self._state == HTTPConnectionState.IDLE

    def is_closed(self) -> bool:
        return self._state == HTTPConnectionState.CLOSED

    def info(self) -> str:
        origin = str(self._origin)
        return (
            f"{origin!r}, HTTP/2, {self._state.name}, "
            f"Request Count: {self._request_count}"
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        origin = str(self._origin)
        return (
            f"<{class_name} [{origin!r}, {self._state.name}, "
            f"Request Count: {self._request_count}]>"
        )

    # These context managers are not used in the standard flow, but are
    # useful for testing or working with connection instances directly.

    async def __aenter__(self) -> AsyncHTTP2Connection:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        await self.aclose()


class HTTP2ConnectionByteStream:
    def __init__(
        self, connection: AsyncHTTP2Connection, request: Request, stream_id: int
    ) -> None:
        self._connection = connection
        self._request = request
        self._stream_id = stream_id
        self._closed = False

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        kwargs = {"request": self._request, "stream_id": self._stream_id}
        try:
            async with Trace("receive_response_body", logger, self._request, kwargs):
                async for chunk in self._connection._receive_response_body(
                    request=self._request, stream_id=self._stream_id
                ):
                    yield chunk
        except BaseException as exc:
            # If we get an exception while streaming the response,
            # we want to close the response (and possibly the connection)
            # before raising that exception.
            with AsyncShieldCancellation():
                await self.aclose()
            raise exc

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            kwargs = {"stream_id": self._stream_id}
            async with Trace("response_closed", logger, self._request, kwargs):
                await self._connection._response_closed(stream_id=self._stream_id)

# === NexusCore/openenv\Lib\site-packages\httpcore\_sync\http2.py ===
from __future__ import annotations

import enum
import logging
import time
import types
import typing

import h2.config
import h2.connection
import h2.events
import h2.exceptions
import h2.settings

from .._backends.base import NetworkStream
from .._exceptions import (
    ConnectionNotAvailable,
    LocalProtocolError,
    RemoteProtocolError,
)
from .._models import Origin, Request, Response
from .._synchronization import Lock, Semaphore, ShieldCancellation
from .._trace import Trace
from .interfaces import ConnectionInterface

logger = logging.getLogger("httpcore.http2")


def has_body_headers(request: Request) -> bool:
    return any(
        k.lower() == b"content-length" or k.lower() == b"transfer-encoding"
        for k, v in request.headers
    )


class HTTPConnectionState(enum.IntEnum):
    ACTIVE = 1
    IDLE = 2
    CLOSED = 3


class HTTP2Connection(ConnectionInterface):
    READ_NUM_BYTES = 64 * 1024
    CONFIG = h2.config.H2Configuration(validate_inbound_headers=False)

    def __init__(
        self,
        origin: Origin,
        stream: NetworkStream,
        keepalive_expiry: float | None = None,
    ):
        self._origin = origin
        self._network_stream = stream
        self._keepalive_expiry: float | None = keepalive_expiry
        self._h2_state = h2.connection.H2Connection(config=self.CONFIG)
        self._state = HTTPConnectionState.IDLE
        self._expire_at: float | None = None
        self._request_count = 0
        self._init_lock = Lock()
        self._state_lock = Lock()
        self._read_lock = Lock()
        self._write_lock = Lock()
        self._sent_connection_init = False
        self._used_all_stream_ids = False
        self._connection_error = False

        # Mapping from stream ID to response stream events.
        self._events: dict[
            int,
            list[
                h2.events.ResponseReceived
                | h2.events.DataReceived
                | h2.events.StreamEnded
                | h2.events.StreamReset,
            ],
        ] = {}

        # Connection terminated events are stored as state since
        # we need to handle them for all streams.
        self._connection_terminated: h2.events.ConnectionTerminated | None = None

        self._read_exception: Exception | None = None
        self._write_exception: Exception | None = None

    def handle_request(self, request: Request) -> Response:
        if not self.can_handle_request(request.url.origin):
            # This cannot occur in normal operation, since the connection pool
            # will only send requests on connections that handle them.
            # It's in place simply for resilience as a guard against incorrect
            # usage, for anyone working directly with httpcore connections.
            raise RuntimeError(
                f"Attempted to send request to {request.url.origin} on connection "
                f"to {self._origin}"
            )

        with self._state_lock:
            if self._state in (HTTPConnectionState.ACTIVE, HTTPConnectionState.IDLE):
                self._request_count += 1
                self._expire_at = None
                self._state = HTTPConnectionState.ACTIVE
            else:
                raise ConnectionNotAvailable()

        with self._init_lock:
            if not self._sent_connection_init:
                try:
                    sci_kwargs = {"request": request}
                    with Trace(
                        "send_connection_init", logger, request, sci_kwargs
                    ):
                        self._send_connection_init(**sci_kwargs)
                except BaseException as exc:
                    with ShieldCancellation():
                        self.close()
                    raise exc

                self._sent_connection_init = True

                # Initially start with just 1 until the remote server provides
                # its max_concurrent_streams value
                self._max_streams = 1

                local_settings_max_streams = (
                    self._h2_state.local_settings.max_concurrent_streams
                )
                self._max_streams_semaphore = Semaphore(local_settings_max_streams)

                for _ in range(local_settings_max_streams - self._max_streams):
                    self._max_streams_semaphore.acquire()

        self._max_streams_semaphore.acquire()

        try:
            stream_id = self._h2_state.get_next_available_stream_id()
            self._events[stream_id] = []
        except h2.exceptions.NoAvailableStreamIDError:  # pragma: nocover
            self._used_all_stream_ids = True
            self._request_count -= 1
            raise ConnectionNotAvailable()

        try:
            kwargs = {"request": request, "stream_id": stream_id}
            with Trace("send_request_headers", logger, request, kwargs):
                self._send_request_headers(request=request, stream_id=stream_id)
            with Trace("send_request_body", logger, request, kwargs):
                self._send_request_body(request=request, stream_id=stream_id)
            with Trace(
                "receive_response_headers", logger, request, kwargs
            ) as trace:
                status, headers = self._receive_response(
                    request=request, stream_id=stream_id
                )
                trace.return_value = (status, headers)

            return Response(
                status=status,
                headers=headers,
                content=HTTP2ConnectionByteStream(self, request, stream_id=stream_id),
                extensions={
                    "http_version": b"HTTP/2",
                    "network_stream": self._network_stream,
                    "stream_id": stream_id,
                },
            )
        except BaseException as exc:  # noqa: PIE786
            with ShieldCancellation():
                kwargs = {"stream_id": stream_id}
                with Trace("response_closed", logger, request, kwargs):
                    self._response_closed(stream_id=stream_id)

            if isinstance(exc, h2.exceptions.ProtocolError):
                # One case where h2 can raise a protocol error is when a
                # closed frame has been seen by the state machine.
                #
                # This happens when one stream is reading, and encounters
                # a GOAWAY event. Other flows of control may then raise
                # a protocol error at any point they interact with the 'h2_state'.
                #
                # In this case we'll have stored the event, and should raise
                # it as a RemoteProtocolError.
                if self._connection_terminated:  # pragma: nocover
                    raise RemoteProtocolError(self._connection_terminated)
                # If h2 raises a protocol error in some other state then we
                # must somehow have made a protocol violation.
                raise LocalProtocolError(exc)  # pragma: nocover

            raise exc

    def _send_connection_init(self, request: Request) -> None:
        """
        The HTTP/2 connection requires some initial setup before we can start
        using individual request/response streams on it.
        """
        # Need to set these manually here instead of manipulating via
        # __setitem__() otherwise the H2Connection will emit SettingsUpdate
        # frames in addition to sending the undesired defaults.
        self._h2_state.local_settings = h2.settings.Settings(
            client=True,
            initial_values={
                # Disable PUSH_PROMISE frames from the server since we don't do anything
                # with them for now.  Maybe when we support caching?
                h2.settings.SettingCodes.ENABLE_PUSH: 0,
                # These two are taken from h2 for safe defaults
                h2.settings.SettingCodes.MAX_CONCURRENT_STREAMS: 100,
                h2.settings.SettingCodes.MAX_HEADER_LIST_SIZE: 65536,
            },
        )

        # Some websites (*cough* Yahoo *cough*) balk at this setting being
        # present in the initial handshake since it's not defined in the original
        # RFC despite the RFC mandating ignoring settings you don't know about.
        del self._h2_state.local_settings[
            h2.settings.SettingCodes.ENABLE_CONNECT_PROTOCOL
        ]

        self._h2_state.initiate_connection()
        self._h2_state.increment_flow_control_window(2**24)
        self._write_outgoing_data(request)

    # Sending the request...

    def _send_request_headers(self, request: Request, stream_id: int) -> None:
        """
        Send the request headers to a given stream ID.
        """
        end_stream = not has_body_headers(request)

        # In HTTP/2 the ':authority' pseudo-header is used instead of 'Host'.
        # In order to gracefully handle HTTP/1.1 and HTTP/2 we always require
        # HTTP/1.1 style headers, and map them appropriately if we end up on
        # an HTTP/2 connection.
        authority = [v for k, v in request.headers if k.lower() == b"host"][0]

        headers = [
            (b":method", request.method),
            (b":authority", authority),
            (b":scheme", request.url.scheme),
            (b":path", request.url.target),
        ] + [
            (k.lower(), v)
            for k, v in request.headers
            if k.lower()
            not in (
                b"host",
                b"transfer-encoding",
            )
        ]

        self._h2_state.send_headers(stream_id, headers, end_stream=end_stream)
        self._h2_state.increment_flow_control_window(2**24, stream_id=stream_id)
        self._write_outgoing_data(request)

    def _send_request_body(self, request: Request, stream_id: int) -> None:
        """
        Iterate over the request body sending it to a given stream ID.
        """
        if not has_body_headers(request):
            return

        assert isinstance(request.stream, typing.Iterable)
        for data in request.stream:
            self._send_stream_data(request, stream_id, data)
        self._send_end_stream(request, stream_id)

    def _send_stream_data(
        self, request: Request, stream_id: int, data: bytes
    ) -> None:
        """
        Send a single chunk of data in one or more data frames.
        """
        while data:
            max_flow = self._wait_for_outgoing_flow(request, stream_id)
            chunk_size = min(len(data), max_flow)
            chunk, data = data[:chunk_size], data[chunk_size:]
            self._h2_state.send_data(stream_id, chunk)
            self._write_outgoing_data(request)

    def _send_end_stream(self, request: Request, stream_id: int) -> None:
        """
        Send an empty data frame on on a given stream ID with the END_STREAM flag set.
        """
        self._h2_state.end_stream(stream_id)
        self._write_outgoing_data(request)

    # Receiving the response...

    def _receive_response(
        self, request: Request, stream_id: int
    ) -> tuple[int, list[tuple[bytes, bytes]]]:
        """
        Return the response status code and headers for a given stream ID.
        """
        while True:
            event = self._receive_stream_event(request, stream_id)
            if isinstance(event, h2.events.ResponseReceived):
                break

        status_code = 200
        headers = []
        assert event.headers is not None
        for k, v in event.headers:
            if k == b":status":
                status_code = int(v.decode("ascii", errors="ignore"))
            elif not k.startswith(b":"):
                headers.append((k, v))

        return (status_code, headers)

    def _receive_response_body(
        self, request: Request, stream_id: int
    ) -> typing.Iterator[bytes]:
        """
        Iterator that returns the bytes of the response body for a given stream ID.
        """
        while True:
            event = self._receive_stream_event(request, stream_id)
            if isinstance(event, h2.events.DataReceived):
                assert event.flow_controlled_length is not None
                assert event.data is not None
                amount = event.flow_controlled_length
                self._h2_state.acknowledge_received_data(amount, stream_id)
                self._write_outgoing_data(request)
                yield event.data
            elif isinstance(event, h2.events.StreamEnded):
                break

    def _receive_stream_event(
        self, request: Request, stream_id: int
    ) -> h2.events.ResponseReceived | h2.events.DataReceived | h2.events.StreamEnded:
        """
        Return the next available event for a given stream ID.

        Will read more data from the network if required.
        """
        while not self._events.get(stream_id):
            self._receive_events(request, stream_id)
        event = self._events[stream_id].pop(0)
        if isinstance(event, h2.events.StreamReset):
            raise RemoteProtocolError(event)
        return event

    def _receive_events(
        self, request: Request, stream_id: int | None = None
    ) -> None:
        """
        Read some data from the network until we see one or more events
        for a given stream ID.
        """
        with self._read_lock:
            if self._connection_terminated is not None:
                last_stream_id = self._connection_terminated.last_stream_id
                if stream_id and last_stream_id and stream_id > last_stream_id:
                    self._request_count -= 1
                    raise ConnectionNotAvailable()
                raise RemoteProtocolError(self._connection_terminated)

            # This conditional is a bit icky. We don't want to block reading if we've
            # actually got an event to return for a given stream. We need to do that
            # check *within* the atomic read lock. Though it also need to be optional,
            # because when we call it from `_wait_for_outgoing_flow` we *do* want to
            # block until we've available flow control, event when we have events
            # pending for the stream ID we're attempting to send on.
            if stream_id is None or not self._events.get(stream_id):
                events = self._read_incoming_data(request)
                for event in events:
                    if isinstance(event, h2.events.RemoteSettingsChanged):
                        with Trace(
                            "receive_remote_settings", logger, request
                        ) as trace:
                            self._receive_remote_settings_change(event)
                            trace.return_value = event

                    elif isinstance(
                        event,
                        (
                            h2.events.ResponseReceived,
                            h2.events.DataReceived,
                            h2.events.StreamEnded,
                            h2.events.StreamReset,
                        ),
                    ):
                        if event.stream_id in self._events:
                            self._events[event.stream_id].append(event)

                    elif isinstance(event, h2.events.ConnectionTerminated):
                        self._connection_terminated = event

        self._write_outgoing_data(request)

    def _receive_remote_settings_change(
        self, event: h2.events.RemoteSettingsChanged
    ) -> None:
        max_concurrent_streams = event.changed_settings.get(
            h2.settings.SettingCodes.MAX_CONCURRENT_STREAMS
        )
        if max_concurrent_streams:
            new_max_streams = min(
                max_concurrent_streams.new_value,
                self._h2_state.local_settings.max_concurrent_streams,
            )
            if new_max_streams and new_max_streams != self._max_streams:
                while new_max_streams > self._max_streams:
                    self._max_streams_semaphore.release()
                    self._max_streams += 1
                while new_max_streams < self._max_streams:
                    self._max_streams_semaphore.acquire()
                    self._max_streams -= 1

    def _response_closed(self, stream_id: int) -> None:
        self._max_streams_semaphore.release()
        del self._events[stream_id]
        with self._state_lock:
            if self._connection_terminated and not self._events:
                self.close()

            elif self._state == HTTPConnectionState.ACTIVE and not self._events:
                self._state = HTTPConnectionState.IDLE
                if self._keepalive_expiry is not None:
                    now = time.monotonic()
                    self._expire_at = now + self._keepalive_expiry
                if self._used_all_stream_ids:  # pragma: nocover
                    self.close()

    def close(self) -> None:
        # Note that this method unilaterally closes the connection, and does
        # not have any kind of locking in place around it.
        self._h2_state.close_connection()
        self._state = HTTPConnectionState.CLOSED
        self._network_stream.close()

    # Wrappers around network read/write operations...

    def _read_incoming_data(self, request: Request) -> list[h2.events.Event]:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("read", None)

        if self._read_exception is not None:
            raise self._read_exception  # pragma: nocover

        try:
            data = self._network_stream.read(self.READ_NUM_BYTES, timeout)
            if data == b"":
                raise RemoteProtocolError("Server disconnected")
        except Exception as exc:
            # If we get a network error we should:
            #
            # 1. Save the exception and just raise it immediately on any future reads.
            #    (For example, this means that a single read timeout or disconnect will
            #    immediately close all pending streams. Without requiring multiple
            #    sequential timeouts.)
            # 2. Mark the connection as errored, so that we don't accept any other
            #    incoming requests.
            self._read_exception = exc
            self._connection_error = True
            raise exc

        events: list[h2.events.Event] = self._h2_state.receive_data(data)

        return events

    def _write_outgoing_data(self, request: Request) -> None:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("write", None)

        with self._write_lock:
            data_to_send = self._h2_state.data_to_send()

            if self._write_exception is not None:
                raise self._write_exception  # pragma: nocover

            try:
                self._network_stream.write(data_to_send, timeout)
            except Exception as exc:  # pragma: nocover
                # If we get a network error we should:
                #
                # 1. Save the exception and just raise it immediately on any future write.
                #    (For example, this means that a single write timeout or disconnect will
                #    immediately close all pending streams. Without requiring multiple
                #    sequential timeouts.)
                # 2. Mark the connection as errored, so that we don't accept any other
                #    incoming requests.
                self._write_exception = exc
                self._connection_error = True
                raise exc

    # Flow control...

    def _wait_for_outgoing_flow(self, request: Request, stream_id: int) -> int:
        """
        Returns the maximum allowable outgoing flow for a given stream.

        If the allowable flow is zero, then waits on the network until
        WindowUpdated frames have increased the flow rate.
        https://tools.ietf.org/html/rfc7540#section-6.9
        """
        local_flow: int = self._h2_state.local_flow_control_window(stream_id)
        max_frame_size: int = self._h2_state.max_outbound_frame_size
        flow = min(local_flow, max_frame_size)
        while flow == 0:
            self._receive_events(request)
            local_flow = self._h2_state.local_flow_control_window(stream_id)
            max_frame_size = self._h2_state.max_outbound_frame_size
            flow = min(local_flow, max_frame_size)
        return flow

    # Interface for connection pooling...

    def can_handle_request(self, origin: Origin) -> bool:
        return origin == self._origin

    def is_available(self) -> bool:
        return (
            self._state != HTTPConnectionState.CLOSED
            and not self._connection_error
            and not self._used_all_stream_ids
            and not (
                self._h2_state.state_machine.state
                == h2.connection.ConnectionState.CLOSED
            )
        )

    def has_expired(self) -> bool:
        now = time.monotonic()
        return self._expire_at is not None and now > self._expire_at

    def is_idle(self) -> bool:
        return self._state == HTTPConnectionState.IDLE

    def is_closed(self) -> bool:
        return self._state == HTTPConnectionState.CLOSED

    def info(self) -> str:
        origin = str(self._origin)
        return (
            f"{origin!r}, HTTP/2, {self._state.name}, "
            f"Request Count: {self._request_count}"
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        origin = str(self._origin)
        return (
            f"<{class_name} [{origin!r}, {self._state.name}, "
            f"Request Count: {self._request_count}]>"
        )

    # These context managers are not used in the standard flow, but are
    # useful for testing or working with connection instances directly.

    def __enter__(self) -> HTTP2Connection:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        self.close()


class HTTP2ConnectionByteStream:
    def __init__(
        self, connection: HTTP2Connection, request: Request, stream_id: int
    ) -> None:
        self._connection = connection
        self._request = request
        self._stream_id = stream_id
        self._closed = False

    def __iter__(self) -> typing.Iterator[bytes]:
        kwargs = {"request": self._request, "stream_id": self._stream_id}
        try:
            with Trace("receive_response_body", logger, self._request, kwargs):
                for chunk in self._connection._receive_response_body(
                    request=self._request, stream_id=self._stream_id
                ):
                    yield chunk
        except BaseException as exc:
            # If we get an exception while streaming the response,
            # we want to close the response (and possibly the connection)
            # before raising that exception.
            with ShieldCancellation():
                self.close()
            raise exc

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            kwargs = {"stream_id": self._stream_id}
            with Trace("response_closed", logger, self._request, kwargs):
                self._connection._response_closed(stream_id=self._stream_id)