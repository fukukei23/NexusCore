
# === NexusCore/openenv\Lib\site-packages\IPython\testing\plugin\pytest_ipdoctest.py ===
# Based on Pytest doctest.py
# Original license:
# The MIT License (MIT)
#
# Copyright (c) 2004-2021 Holger Krekel and others
"""Discover and run ipdoctests in modules and test files."""

import bdb
import builtins
import inspect
import os
import platform
import sys
import traceback
import types
import warnings
from contextlib import contextmanager
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Pattern,
    Sequence,
    Tuple,
    Type,
    Union,
)

import pytest
from _pytest import outcomes
from _pytest._code.code import ExceptionInfo, ReprFileLocation, TerminalRepr
from _pytest._io import TerminalWriter
from _pytest.compat import safe_getattr
from _pytest.config import Config
from _pytest.config.argparsing import Parser

try:
    from _pytest.fixtures import TopRequest as FixtureRequest
except ImportError:
    from _pytest.fixtures import FixtureRequest
from _pytest.nodes import Collector
from _pytest.outcomes import OutcomeException
from _pytest.pathlib import fnmatch_ex, import_path
from _pytest.python_api import approx
from _pytest.warning_types import PytestWarning

if TYPE_CHECKING:
    import doctest

    from .ipdoctest import IPDoctestOutputChecker

DOCTEST_REPORT_CHOICE_NONE = "none"
DOCTEST_REPORT_CHOICE_CDIFF = "cdiff"
DOCTEST_REPORT_CHOICE_NDIFF = "ndiff"
DOCTEST_REPORT_CHOICE_UDIFF = "udiff"
DOCTEST_REPORT_CHOICE_ONLY_FIRST_FAILURE = "only_first_failure"

DOCTEST_REPORT_CHOICES = (
    DOCTEST_REPORT_CHOICE_NONE,
    DOCTEST_REPORT_CHOICE_CDIFF,
    DOCTEST_REPORT_CHOICE_NDIFF,
    DOCTEST_REPORT_CHOICE_UDIFF,
    DOCTEST_REPORT_CHOICE_ONLY_FIRST_FAILURE,
)

# Lazy definition of runner class
RUNNER_CLASS = None
# Lazy definition of output checker class
CHECKER_CLASS: Optional[Type["IPDoctestOutputChecker"]] = None

pytest_version = tuple([int(part) for part in pytest.__version__.split(".")])


def pytest_addoption(parser: Parser) -> None:
    parser.addini(
        "ipdoctest_optionflags",
        "option flags for ipdoctests",
        type="args",
        default=["ELLIPSIS"],
    )
    parser.addini(
        "ipdoctest_encoding", "encoding used for ipdoctest files", default="utf-8"
    )
    group = parser.getgroup("collect")
    group.addoption(
        "--ipdoctest-modules",
        action="store_true",
        default=False,
        help="run ipdoctests in all .py modules",
        dest="ipdoctestmodules",
    )
    group.addoption(
        "--ipdoctest-report",
        type=str.lower,
        default="udiff",
        help="choose another output format for diffs on ipdoctest failure",
        choices=DOCTEST_REPORT_CHOICES,
        dest="ipdoctestreport",
    )
    group.addoption(
        "--ipdoctest-glob",
        action="append",
        default=[],
        metavar="pat",
        help="ipdoctests file matching pattern, default: test*.txt",
        dest="ipdoctestglob",
    )
    group.addoption(
        "--ipdoctest-ignore-import-errors",
        action="store_true",
        default=False,
        help="ignore ipdoctest ImportErrors",
        dest="ipdoctest_ignore_import_errors",
    )
    group.addoption(
        "--ipdoctest-continue-on-failure",
        action="store_true",
        default=False,
        help="for a given ipdoctest, continue to run after the first failure",
        dest="ipdoctest_continue_on_failure",
    )


def pytest_unconfigure() -> None:
    global RUNNER_CLASS

    RUNNER_CLASS = None


def pytest_collect_file(
    file_path: Path,
    parent: Collector,
) -> Optional[Union["IPDoctestModule", "IPDoctestTextfile"]]:
    config = parent.config
    if file_path.suffix == ".py":
        if config.option.ipdoctestmodules and not any(
            (_is_setup_py(file_path), _is_main_py(file_path))
        ):
            mod: IPDoctestModule = IPDoctestModule.from_parent(parent, path=file_path)
            return mod
    elif _is_ipdoctest(config, file_path, parent):
        txt: IPDoctestTextfile = IPDoctestTextfile.from_parent(parent, path=file_path)
        return txt
    return None


if pytest_version[0] < 7:
    _collect_file = pytest_collect_file

    def pytest_collect_file(
        path,
        parent: Collector,
    ) -> Optional[Union["IPDoctestModule", "IPDoctestTextfile"]]:
        return _collect_file(Path(path), parent)

    _import_path = import_path

    def import_path(path, root):
        import py.path

        return _import_path(py.path.local(path))


def _is_setup_py(path: Path) -> bool:
    if path.name != "setup.py":
        return False
    contents = path.read_bytes()
    return b"setuptools" in contents or b"distutils" in contents


def _is_ipdoctest(config: Config, path: Path, parent: Collector) -> bool:
    if path.suffix in (".txt", ".rst") and parent.session.isinitpath(path):
        return True
    globs = config.getoption("ipdoctestglob") or ["test*.txt"]
    return any(fnmatch_ex(glob, path) for glob in globs)


def _is_main_py(path: Path) -> bool:
    return path.name == "__main__.py"


class ReprFailDoctest(TerminalRepr):
    def __init__(
        self, reprlocation_lines: Sequence[Tuple[ReprFileLocation, Sequence[str]]]
    ) -> None:
        self.reprlocation_lines = reprlocation_lines

    def toterminal(self, tw: TerminalWriter) -> None:
        for reprlocation, lines in self.reprlocation_lines:
            for line in lines:
                tw.line(line)
            reprlocation.toterminal(tw)


class MultipleDoctestFailures(Exception):
    def __init__(self, failures: Sequence["doctest.DocTestFailure"]) -> None:
        super().__init__()
        self.failures = failures


def _init_runner_class() -> Type["IPDocTestRunner"]:
    import doctest
    from .ipdoctest import IPDocTestRunner

    class PytestDoctestRunner(IPDocTestRunner):
        """Runner to collect failures.

        Note that the out variable in this case is a list instead of a
        stdout-like object.
        """

        def __init__(
            self,
            checker: Optional["IPDoctestOutputChecker"] = None,
            verbose: Optional[bool] = None,
            optionflags: int = 0,
            continue_on_failure: bool = True,
        ) -> None:
            super().__init__(checker=checker, verbose=verbose, optionflags=optionflags)
            self.continue_on_failure = continue_on_failure

        def report_failure(
            self,
            out,
            test: "doctest.DocTest",
            example: "doctest.Example",
            got: str,
        ) -> None:
            failure = doctest.DocTestFailure(test, example, got)
            if self.continue_on_failure:
                out.append(failure)
            else:
                raise failure

        def report_unexpected_exception(
            self,
            out,
            test: "doctest.DocTest",
            example: "doctest.Example",
            exc_info: Tuple[Type[BaseException], BaseException, types.TracebackType],
        ) -> None:
            if isinstance(exc_info[1], OutcomeException):
                raise exc_info[1]
            if isinstance(exc_info[1], bdb.BdbQuit):
                outcomes.exit("Quitting debugger")
            failure = doctest.UnexpectedException(test, example, exc_info)
            if self.continue_on_failure:
                out.append(failure)
            else:
                raise failure

    return PytestDoctestRunner


def _get_runner(
    checker: Optional["IPDoctestOutputChecker"] = None,
    verbose: Optional[bool] = None,
    optionflags: int = 0,
    continue_on_failure: bool = True,
) -> "IPDocTestRunner":
    # We need this in order to do a lazy import on doctest
    global RUNNER_CLASS
    if RUNNER_CLASS is None:
        RUNNER_CLASS = _init_runner_class()
    # Type ignored because the continue_on_failure argument is only defined on
    # PytestDoctestRunner, which is lazily defined so can't be used as a type.
    return RUNNER_CLASS(  # type: ignore
        checker=checker,
        verbose=verbose,
        optionflags=optionflags,
        continue_on_failure=continue_on_failure,
    )


class IPDoctestItem(pytest.Item):
    _user_ns_orig: Dict[str, Any]

    def __init__(
        self,
        name: str,
        parent: "Union[IPDoctestTextfile, IPDoctestModule]",
        runner: Optional["IPDocTestRunner"] = None,
        dtest: Optional["doctest.DocTest"] = None,
    ) -> None:
        super().__init__(name, parent)
        self.runner = runner
        self.dtest = dtest
        self.obj = None
        self.fixture_request: Optional[FixtureRequest] = None
        self._user_ns_orig = {}

    @classmethod
    def from_parent(  # type: ignore
        cls,
        parent: "Union[IPDoctestTextfile, IPDoctestModule]",
        *,
        name: str,
        runner: "IPDocTestRunner",
        dtest: "doctest.DocTest",
    ):
        # incompatible signature due to imposed limits on subclass
        """The public named constructor."""
        return super().from_parent(name=name, parent=parent, runner=runner, dtest=dtest)

    def setup(self) -> None:
        if self.dtest is not None:
            self.fixture_request = _setup_fixtures(self)
            globs = dict(getfixture=self.fixture_request.getfixturevalue)
            for name, value in self.fixture_request.getfixturevalue(
                "ipdoctest_namespace"
            ).items():
                globs[name] = value
            self.dtest.globs.update(globs)

            from .ipdoctest import IPExample

            if isinstance(self.dtest.examples[0], IPExample):
                # for IPython examples *only*, we swap the globals with the ipython
                # namespace, after updating it with the globals (which doctest
                # fills with the necessary info from the module being tested).
                self._user_ns_orig = {}
                self._user_ns_orig.update(_ip.user_ns)
                _ip.user_ns.update(self.dtest.globs)
                # We must remove the _ key in the namespace, so that Python's
                # doctest code sets it naturally
                _ip.user_ns.pop("_", None)
                _ip.user_ns["__builtins__"] = builtins
                self.dtest.globs = _ip.user_ns

    def teardown(self) -> None:
        from .ipdoctest import IPExample

        # Undo the test.globs reassignment we made
        if isinstance(self.dtest.examples[0], IPExample):
            self.dtest.globs = {}
            _ip.user_ns.clear()
            _ip.user_ns.update(self._user_ns_orig)
            del self._user_ns_orig

        self.dtest.globs.clear()

    def runtest(self) -> None:
        assert self.dtest is not None
        assert self.runner is not None
        _check_all_skipped(self.dtest)
        self._disable_output_capturing_for_darwin()
        failures: List[doctest.DocTestFailure] = []

        # exec(compile(..., "single", ...), ...) puts result in builtins._
        had_underscore_value = hasattr(builtins, "_")
        underscore_original_value = getattr(builtins, "_", None)

        # Save our current directory and switch out to the one where the
        # test was originally created, in case another doctest did a
        # directory change.  We'll restore this in the finally clause.
        curdir = os.getcwd()
        os.chdir(self.fspath.dirname)
        try:
            # Type ignored because we change the type of `out` from what
            # ipdoctest expects.
            self.runner.run(self.dtest, out=failures, clear_globs=False)  # type: ignore[arg-type]
        finally:
            os.chdir(curdir)
            if had_underscore_value:
                setattr(builtins, "_", underscore_original_value)
            elif hasattr(builtins, "_"):
                delattr(builtins, "_")

        if failures:
            raise MultipleDoctestFailures(failures)

    def _disable_output_capturing_for_darwin(self) -> None:
        """Disable output capturing. Otherwise, stdout is lost to ipdoctest (pytest#985)."""
        if platform.system() != "Darwin":
            return
        capman = self.config.pluginmanager.getplugin("capturemanager")
        if capman:
            capman.suspend_global_capture(in_=True)
            out, err = capman.read_global_capture()
            sys.stdout.write(out)
            sys.stderr.write(err)

    # TODO: Type ignored -- breaks Liskov Substitution.
    def repr_failure(  # type: ignore[override]
        self,
        excinfo: ExceptionInfo[BaseException],
    ) -> Union[str, TerminalRepr]:
        import doctest

        failures: Optional[
            Sequence[Union[doctest.DocTestFailure, doctest.UnexpectedException]]
        ] = None
        if isinstance(
            excinfo.value, (doctest.DocTestFailure, doctest.UnexpectedException)
        ):
            failures = [excinfo.value]
        elif isinstance(excinfo.value, MultipleDoctestFailures):
            failures = excinfo.value.failures

        if failures is None:
            return super().repr_failure(excinfo)

        reprlocation_lines = []
        for failure in failures:
            example = failure.example
            test = failure.test
            filename = test.filename
            if test.lineno is None:
                lineno = None
            else:
                lineno = test.lineno + example.lineno + 1
            message = type(failure).__name__
            # TODO: ReprFileLocation doesn't expect a None lineno.
            reprlocation = ReprFileLocation(filename, lineno, message)  # type: ignore[arg-type]
            checker = _get_checker()
            report_choice = _get_report_choice(self.config.getoption("ipdoctestreport"))
            if lineno is not None:
                assert failure.test.docstring is not None
                lines = failure.test.docstring.splitlines(False)
                # add line numbers to the left of the error message
                assert test.lineno is not None
                lines = [
                    "%03d %s" % (i + test.lineno + 1, x) for (i, x) in enumerate(lines)
                ]
                # trim docstring error lines to 10
                lines = lines[max(example.lineno - 9, 0) : example.lineno + 1]
            else:
                lines = [
                    "EXAMPLE LOCATION UNKNOWN, not showing all tests of that example"
                ]
                indent = ">>>"
                for line in example.source.splitlines():
                    lines.append(f"??? {indent} {line}")
                    indent = "..."
            if isinstance(failure, doctest.DocTestFailure):
                lines += checker.output_difference(
                    example, failure.got, report_choice
                ).split("\n")
            else:
                inner_excinfo = ExceptionInfo.from_exc_info(failure.exc_info)
                lines += ["UNEXPECTED EXCEPTION: %s" % repr(inner_excinfo.value)]
                lines += [
                    x.strip("\n") for x in traceback.format_exception(*failure.exc_info)
                ]
            reprlocation_lines.append((reprlocation, lines))
        return ReprFailDoctest(reprlocation_lines)

    def reportinfo(self) -> Tuple[Union["os.PathLike[str]", str], Optional[int], str]:
        assert self.dtest is not None
        return self.path, self.dtest.lineno, "[ipdoctest] %s" % self.name

    if pytest_version[0] < 7:

        @property
        def path(self) -> Path:
            return Path(self.fspath)


def _get_flag_lookup() -> Dict[str, int]:
    import doctest

    return dict(
        DONT_ACCEPT_TRUE_FOR_1=doctest.DONT_ACCEPT_TRUE_FOR_1,
        DONT_ACCEPT_BLANKLINE=doctest.DONT_ACCEPT_BLANKLINE,
        NORMALIZE_WHITESPACE=doctest.NORMALIZE_WHITESPACE,
        ELLIPSIS=doctest.ELLIPSIS,
        IGNORE_EXCEPTION_DETAIL=doctest.IGNORE_EXCEPTION_DETAIL,
        COMPARISON_FLAGS=doctest.COMPARISON_FLAGS,
        ALLOW_UNICODE=_get_allow_unicode_flag(),
        ALLOW_BYTES=_get_allow_bytes_flag(),
        NUMBER=_get_number_flag(),
    )


def get_optionflags(parent):
    optionflags_str = parent.config.getini("ipdoctest_optionflags")
    flag_lookup_table = _get_flag_lookup()
    flag_acc = 0
    for flag in optionflags_str:
        flag_acc |= flag_lookup_table[flag]
    return flag_acc


def _get_continue_on_failure(config):
    continue_on_failure = config.getvalue("ipdoctest_continue_on_failure")
    if continue_on_failure:
        # We need to turn off this if we use pdb since we should stop at
        # the first failure.
        if config.getvalue("usepdb"):
            continue_on_failure = False
    return continue_on_failure


class IPDoctestTextfile(pytest.Module):
    obj = None

    def collect(self) -> Iterable[IPDoctestItem]:
        import doctest
        from .ipdoctest import IPDocTestParser

        # Inspired by doctest.testfile; ideally we would use it directly,
        # but it doesn't support passing a custom checker.
        encoding = self.config.getini("ipdoctest_encoding")
        text = self.path.read_text(encoding)
        filename = str(self.path)
        name = self.path.name
        globs = {"__name__": "__main__"}

        optionflags = get_optionflags(self)

        runner = _get_runner(
            verbose=False,
            optionflags=optionflags,
            checker=_get_checker(),
            continue_on_failure=_get_continue_on_failure(self.config),
        )

        parser = IPDocTestParser()
        test = parser.get_doctest(text, globs, name, filename, 0)
        if test.examples:
            yield IPDoctestItem.from_parent(
                self, name=test.name, runner=runner, dtest=test
            )

    if pytest_version[0] < 7:

        @property
        def path(self) -> Path:
            return Path(self.fspath)

        @classmethod
        def from_parent(
            cls,
            parent,
            *,
            fspath=None,
            path: Optional[Path] = None,
            **kw,
        ):
            if path is not None:
                import py.path

                fspath = py.path.local(path)
            return super().from_parent(parent=parent, fspath=fspath, **kw)


def _check_all_skipped(test: "doctest.DocTest") -> None:
    """Raise pytest.skip() if all examples in the given DocTest have the SKIP
    option set."""
    import doctest

    all_skipped = all(x.options.get(doctest.SKIP, False) for x in test.examples)
    if all_skipped:
        pytest.skip("all docstests skipped by +SKIP option")


def _is_mocked(obj: object) -> bool:
    """Return if an object is possibly a mock object by checking the
    existence of a highly improbable attribute."""
    return (
        safe_getattr(obj, "pytest_mock_example_attribute_that_shouldnt_exist", None)
        is not None
    )


@contextmanager
def _patch_unwrap_mock_aware() -> Generator[None, None, None]:
    """Context manager which replaces ``inspect.unwrap`` with a version
    that's aware of mock objects and doesn't recurse into them."""
    real_unwrap = inspect.unwrap

    def _mock_aware_unwrap(
        func: Callable[..., Any], *, stop: Optional[Callable[[Any], Any]] = None
    ) -> Any:
        try:
            if stop is None or stop is _is_mocked:
                return real_unwrap(func, stop=_is_mocked)
            _stop = stop
            return real_unwrap(func, stop=lambda obj: _is_mocked(obj) or _stop(func))
        except Exception as e:
            warnings.warn(
                "Got %r when unwrapping %r.  This is usually caused "
                "by a violation of Python's object protocol; see e.g. "
                "https://github.com/pytest-dev/pytest/issues/5080" % (e, func),
                PytestWarning,
            )
            raise

    inspect.unwrap = _mock_aware_unwrap
    try:
        yield
    finally:
        inspect.unwrap = real_unwrap


class IPDoctestModule(pytest.Module):
    def collect(self) -> Iterable[IPDoctestItem]:
        import doctest
        from .ipdoctest import DocTestFinder, IPDocTestParser

        class MockAwareDocTestFinder(DocTestFinder):
            """A hackish ipdoctest finder that overrides stdlib internals to fix a stdlib bug.

            https://github.com/pytest-dev/pytest/issues/3456
            https://bugs.python.org/issue25532
            """

            def _find_lineno(self, obj, source_lines):
                """Doctest code does not take into account `@property`, this
                is a hackish way to fix it. https://bugs.python.org/issue17446

                Wrapped Doctests will need to be unwrapped so the correct
                line number is returned. This will be reported upstream. #8796
                """
                if isinstance(obj, property):
                    obj = getattr(obj, "fget", obj)

                if hasattr(obj, "__wrapped__"):
                    # Get the main obj in case of it being wrapped
                    obj = inspect.unwrap(obj)

                # Type ignored because this is a private function.
                return super()._find_lineno(  # type:ignore[misc]
                    obj,
                    source_lines,
                )

            def _find(
                self, tests, obj, name, module, source_lines, globs, seen
            ) -> None:
                if _is_mocked(obj):
                    return
                with _patch_unwrap_mock_aware():
                    # Type ignored because this is a private function.
                    super()._find(  # type:ignore[misc]
                        tests, obj, name, module, source_lines, globs, seen
                    )

        if self.path.name == "conftest.py":
            if pytest_version[0] < 7:
                module = self.config.pluginmanager._importconftest(
                    self.path,
                    self.config.getoption("importmode"),
                )
            else:
                kwargs = {"rootpath": self.config.rootpath}
                if pytest_version >= (8, 1):
                    kwargs["consider_namespace_packages"] = False
                module = self.config.pluginmanager._importconftest(
                    self.path,
                    self.config.getoption("importmode"),
                    **kwargs,
                )
        else:
            try:
                kwargs = {"root": self.config.rootpath}
                if pytest_version >= (8, 1):
                    kwargs["consider_namespace_packages"] = False
                module = import_path(self.path, **kwargs)
            except ImportError:
                if self.config.getvalue("ipdoctest_ignore_import_errors"):
                    pytest.skip("unable to import module %r" % self.path)
                else:
                    raise
        # Uses internal doctest module parsing mechanism.
        finder = MockAwareDocTestFinder(parser=IPDocTestParser())
        optionflags = get_optionflags(self)
        runner = _get_runner(
            verbose=False,
            optionflags=optionflags,
            checker=_get_checker(),
            continue_on_failure=_get_continue_on_failure(self.config),
        )

        for test in finder.find(module, module.__name__):
            if test.examples:  # skip empty ipdoctests
                yield IPDoctestItem.from_parent(
                    self, name=test.name, runner=runner, dtest=test
                )

    if pytest_version[0] < 7:

        @property
        def path(self) -> Path:
            return Path(self.fspath)

        @classmethod
        def from_parent(
            cls,
            parent,
            *,
            fspath=None,
            path: Optional[Path] = None,
            **kw,
        ):
            if path is not None:
                import py.path

                fspath = py.path.local(path)
            return super().from_parent(parent=parent, fspath=fspath, **kw)


def _setup_fixtures(doctest_item: IPDoctestItem) -> FixtureRequest:
    """Used by IPDoctestTextfile and IPDoctestItem to setup fixture information."""

    def func() -> None:
        pass

    doctest_item.funcargs = {}  # type: ignore[attr-defined]
    fm = doctest_item.session._fixturemanager
    kwargs = {"node": doctest_item, "func": func, "cls": None}
    if pytest_version <= (8, 0):
        kwargs["funcargs"] = False
    doctest_item._fixtureinfo = fm.getfixtureinfo(  # type: ignore[attr-defined]
        **kwargs
    )
    fixture_request = FixtureRequest(doctest_item, _ispytest=True)
    if pytest_version <= (8, 0):
        fixture_request._fillfixtures()
    return fixture_request


def _init_checker_class() -> Type["IPDoctestOutputChecker"]:
    import doctest
    import re
    from .ipdoctest import IPDoctestOutputChecker

    class LiteralsOutputChecker(IPDoctestOutputChecker):
        # Based on doctest_nose_plugin.py from the nltk project
        # (https://github.com/nltk/nltk) and on the "numtest" doctest extension
        # by Sebastien Boisgerault (https://github.com/boisgera/numtest).

        _unicode_literal_re = re.compile(r"(\W|^)[uU]([rR]?[\'\"])", re.UNICODE)
        _bytes_literal_re = re.compile(r"(\W|^)[bB]([rR]?[\'\"])", re.UNICODE)
        _number_re = re.compile(
            r"""
            (?P<number>
              (?P<mantissa>
                (?P<integer1> [+-]?\d*)\.(?P<fraction>\d+)
                |
                (?P<integer2> [+-]?\d+)\.
              )
              (?:
                [Ee]
                (?P<exponent1> [+-]?\d+)
              )?
              |
              (?P<integer3> [+-]?\d+)
              (?:
                [Ee]
                (?P<exponent2> [+-]?\d+)
              )
            )
            """,
            re.VERBOSE,
        )

        def check_output(self, want: str, got: str, optionflags: int) -> bool:
            if super().check_output(want, got, optionflags):
                return True

            allow_unicode = optionflags & _get_allow_unicode_flag()
            allow_bytes = optionflags & _get_allow_bytes_flag()
            allow_number = optionflags & _get_number_flag()

            if not allow_unicode and not allow_bytes and not allow_number:
                return False

            def remove_prefixes(regex: Pattern[str], txt: str) -> str:
                return re.sub(regex, r"\1\2", txt)

            if allow_unicode:
                want = remove_prefixes(self._unicode_literal_re, want)
                got = remove_prefixes(self._unicode_literal_re, got)

            if allow_bytes:
                want = remove_prefixes(self._bytes_literal_re, want)
                got = remove_prefixes(self._bytes_literal_re, got)

            if allow_number:
                got = self._remove_unwanted_precision(want, got)

            return super().check_output(want, got, optionflags)

        def _remove_unwanted_precision(self, want: str, got: str) -> str:
            wants = list(self._number_re.finditer(want))
            gots = list(self._number_re.finditer(got))
            if len(wants) != len(gots):
                return got
            offset = 0
            for w, g in zip(wants, gots):
                fraction: Optional[str] = w.group("fraction")
                exponent: Optional[str] = w.group("exponent1")
                if exponent is None:
                    exponent = w.group("exponent2")
                precision = 0 if fraction is None else len(fraction)
                if exponent is not None:
                    precision -= int(exponent)
                if float(w.group()) == approx(float(g.group()), abs=10**-precision):
                    # They're close enough. Replace the text we actually
                    # got with the text we want, so that it will match when we
                    # check the string literally.
                    got = (
                        got[: g.start() + offset] + w.group() + got[g.end() + offset :]
                    )
                    offset += w.end() - w.start() - (g.end() - g.start())
            return got

    return LiteralsOutputChecker


def _get_checker() -> "IPDoctestOutputChecker":
    """Return a IPDoctestOutputChecker subclass that supports some
    additional options:

    * ALLOW_UNICODE and ALLOW_BYTES options to ignore u'' and b''
      prefixes (respectively) in string literals. Useful when the same
      ipdoctest should run in Python 2 and Python 3.

    * NUMBER to ignore floating-point differences smaller than the
      precision of the literal number in the ipdoctest.

    An inner class is used to avoid importing "ipdoctest" at the module
    level.
    """
    global CHECKER_CLASS
    if CHECKER_CLASS is None:
        CHECKER_CLASS = _init_checker_class()
    return CHECKER_CLASS()


def _get_allow_unicode_flag() -> int:
    """Register and return the ALLOW_UNICODE flag."""
    import doctest

    return doctest.register_optionflag("ALLOW_UNICODE")


def _get_allow_bytes_flag() -> int:
    """Register and return the ALLOW_BYTES flag."""
    import doctest

    return doctest.register_optionflag("ALLOW_BYTES")


def _get_number_flag() -> int:
    """Register and return the NUMBER flag."""
    import doctest

    return doctest.register_optionflag("NUMBER")


def _get_report_choice(key: str) -> int:
    """Return the actual `ipdoctest` module flag value.

    We want to do it as late as possible to avoid importing `ipdoctest` and all
    its dependencies when parsing options, as it adds overhead and breaks tests.
    """
    import doctest

    return {
        DOCTEST_REPORT_CHOICE_UDIFF: doctest.REPORT_UDIFF,
        DOCTEST_REPORT_CHOICE_CDIFF: doctest.REPORT_CDIFF,
        DOCTEST_REPORT_CHOICE_NDIFF: doctest.REPORT_NDIFF,
        DOCTEST_REPORT_CHOICE_ONLY_FIRST_FAILURE: doctest.REPORT_ONLY_FIRST_FAILURE,
        DOCTEST_REPORT_CHOICE_NONE: 0,
    }[key]


@pytest.fixture(scope="session")
def ipdoctest_namespace() -> Dict[str, Any]:
    """Fixture that returns a :py:class:`dict` that will be injected into the
    namespace of ipdoctests."""
    return dict()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\response.py ===
from __future__ import absolute_import

import io
import logging
import sys
import warnings
import zlib
from contextlib import contextmanager
from socket import error as SocketError
from socket import timeout as SocketTimeout

brotli = None

from . import util
from ._collections import HTTPHeaderDict
from .connection import BaseSSLError, HTTPException
from .exceptions import (
    BodyNotHttplibCompatible,
    DecodeError,
    HTTPError,
    IncompleteRead,
    InvalidChunkLength,
    InvalidHeader,
    ProtocolError,
    ReadTimeoutError,
    ResponseNotChunked,
    SSLError,
)
from .packages import six
from .util.response import is_fp_closed, is_response_to_head

log = logging.getLogger(__name__)


class DeflateDecoder(object):
    def __init__(self):
        self._first_try = True
        self._data = b""
        self._obj = zlib.decompressobj()

    def __getattr__(self, name):
        return getattr(self._obj, name)

    def decompress(self, data):
        if not data:
            return data

        if not self._first_try:
            return self._obj.decompress(data)

        self._data += data
        try:
            decompressed = self._obj.decompress(data)
            if decompressed:
                self._first_try = False
                self._data = None
            return decompressed
        except zlib.error:
            self._first_try = False
            self._obj = zlib.decompressobj(-zlib.MAX_WBITS)
            try:
                return self.decompress(self._data)
            finally:
                self._data = None


class GzipDecoderState(object):

    FIRST_MEMBER = 0
    OTHER_MEMBERS = 1
    SWALLOW_DATA = 2


class GzipDecoder(object):
    def __init__(self):
        self._obj = zlib.decompressobj(16 + zlib.MAX_WBITS)
        self._state = GzipDecoderState.FIRST_MEMBER

    def __getattr__(self, name):
        return getattr(self._obj, name)

    def decompress(self, data):
        ret = bytearray()
        if self._state == GzipDecoderState.SWALLOW_DATA or not data:
            return bytes(ret)
        while True:
            try:
                ret += self._obj.decompress(data)
            except zlib.error:
                previous_state = self._state
                # Ignore data after the first error
                self._state = GzipDecoderState.SWALLOW_DATA
                if previous_state == GzipDecoderState.OTHER_MEMBERS:
                    # Allow trailing garbage acceptable in other gzip clients
                    return bytes(ret)
                raise
            data = self._obj.unused_data
            if not data:
                return bytes(ret)
            self._state = GzipDecoderState.OTHER_MEMBERS
            self._obj = zlib.decompressobj(16 + zlib.MAX_WBITS)


if brotli is not None:

    class BrotliDecoder(object):
        # Supports both 'brotlipy' and 'Brotli' packages
        # since they share an import name. The top branches
        # are for 'brotlipy' and bottom branches for 'Brotli'
        def __init__(self):
            self._obj = brotli.Decompressor()
            if hasattr(self._obj, "decompress"):
                self.decompress = self._obj.decompress
            else:
                self.decompress = self._obj.process

        def flush(self):
            if hasattr(self._obj, "flush"):
                return self._obj.flush()
            return b""


class MultiDecoder(object):
    """
    From RFC7231:
        If one or more encodings have been applied to a representation, the
        sender that applied the encodings MUST generate a Content-Encoding
        header field that lists the content codings in the order in which
        they were applied.
    """

    def __init__(self, modes):
        self._decoders = [_get_decoder(m.strip()) for m in modes.split(",")]

    def flush(self):
        return self._decoders[0].flush()

    def decompress(self, data):
        for d in reversed(self._decoders):
            data = d.decompress(data)
        return data


def _get_decoder(mode):
    if "," in mode:
        return MultiDecoder(mode)

    if mode == "gzip":
        return GzipDecoder()

    if brotli is not None and mode == "br":
        return BrotliDecoder()

    return DeflateDecoder()


class HTTPResponse(io.IOBase):
    """
    HTTP Response container.

    Backwards-compatible with :class:`http.client.HTTPResponse` but the response ``body`` is
    loaded and decoded on-demand when the ``data`` property is accessed.  This
    class is also compatible with the Python standard library's :mod:`io`
    module, and can hence be treated as a readable object in the context of that
    framework.

    Extra parameters for behaviour not present in :class:`http.client.HTTPResponse`:

    :param preload_content:
        If True, the response's body will be preloaded during construction.

    :param decode_content:
        If True, will attempt to decode the body based on the
        'content-encoding' header.

    :param original_response:
        When this HTTPResponse wrapper is generated from an :class:`http.client.HTTPResponse`
        object, it's convenient to include the original for debug purposes. It's
        otherwise unused.

    :param retries:
        The retries contains the last :class:`~urllib3.util.retry.Retry` that
        was used during the request.

    :param enforce_content_length:
        Enforce content length checking. Body returned by server must match
        value of Content-Length header, if present. Otherwise, raise error.
    """

    CONTENT_DECODERS = ["gzip", "deflate"]
    if brotli is not None:
        CONTENT_DECODERS += ["br"]
    REDIRECT_STATUSES = [301, 302, 303, 307, 308]

    def __init__(
        self,
        body="",
        headers=None,
        status=0,
        version=0,
        reason=None,
        strict=0,
        preload_content=True,
        decode_content=True,
        original_response=None,
        pool=None,
        connection=None,
        msg=None,
        retries=None,
        enforce_content_length=False,
        request_method=None,
        request_url=None,
        auto_close=True,
    ):

        if isinstance(headers, HTTPHeaderDict):
            self.headers = headers
        else:
            self.headers = HTTPHeaderDict(headers)
        self.status = status
        self.version = version
        self.reason = reason
        self.strict = strict
        self.decode_content = decode_content
        self.retries = retries
        self.enforce_content_length = enforce_content_length
        self.auto_close = auto_close

        self._decoder = None
        self._body = None
        self._fp = None
        self._original_response = original_response
        self._fp_bytes_read = 0
        self.msg = msg
        self._request_url = request_url

        if body and isinstance(body, (six.string_types, bytes)):
            self._body = body

        self._pool = pool
        self._connection = connection

        if hasattr(body, "read"):
            self._fp = body

        # Are we using the chunked-style of transfer encoding?
        self.chunked = False
        self.chunk_left = None
        tr_enc = self.headers.get("transfer-encoding", "").lower()
        # Don't incur the penalty of creating a list and then discarding it
        encodings = (enc.strip() for enc in tr_enc.split(","))
        if "chunked" in encodings:
            self.chunked = True

        # Determine length of response
        self.length_remaining = self._init_length(request_method)

        # If requested, preload the body.
        if preload_content and not self._body:
            self._body = self.read(decode_content=decode_content)

    def get_redirect_location(self):
        """
        Should we redirect and where to?

        :returns: Truthy redirect location string if we got a redirect status
            code and valid location. ``None`` if redirect status and no
            location. ``False`` if not a redirect status code.
        """
        if self.status in self.REDIRECT_STATUSES:
            return self.headers.get("location")

        return False

    def release_conn(self):
        if not self._pool or not self._connection:
            return

        self._pool._put_conn(self._connection)
        self._connection = None

    def drain_conn(self):
        """
        Read and discard any remaining HTTP response data in the response connection.

        Unread data in the HTTPResponse connection blocks the connection from being released back to the pool.
        """
        try:
            self.read()
        except (HTTPError, SocketError, BaseSSLError, HTTPException):
            pass

    @property
    def data(self):
        # For backwards-compat with earlier urllib3 0.4 and earlier.
        if self._body:
            return self._body

        if self._fp:
            return self.read(cache_content=True)

    @property
    def connection(self):
        return self._connection

    def isclosed(self):
        return is_fp_closed(self._fp)

    def tell(self):
        """
        Obtain the number of bytes pulled over the wire so far. May differ from
        the amount of content returned by :meth:``urllib3.response.HTTPResponse.read``
        if bytes are encoded on the wire (e.g, compressed).
        """
        return self._fp_bytes_read

    def _init_length(self, request_method):
        """
        Set initial length value for Response content if available.
        """
        length = self.headers.get("content-length")

        if length is not None:
            if self.chunked:
                # This Response will fail with an IncompleteRead if it can't be
                # received as chunked. This method falls back to attempt reading
                # the response before raising an exception.
                log.warning(
                    "Received response with both Content-Length and "
                    "Transfer-Encoding set. This is expressly forbidden "
                    "by RFC 7230 sec 3.3.2. Ignoring Content-Length and "
                    "attempting to process response as Transfer-Encoding: "
                    "chunked."
                )
                return None

            try:
                # RFC 7230 section 3.3.2 specifies multiple content lengths can
                # be sent in a single Content-Length header
                # (e.g. Content-Length: 42, 42). This line ensures the values
                # are all valid ints and that as long as the `set` length is 1,
                # all values are the same. Otherwise, the header is invalid.
                lengths = set([int(val) for val in length.split(",")])
                if len(lengths) > 1:
                    raise InvalidHeader(
                        "Content-Length contained multiple "
                        "unmatching values (%s)" % length
                    )
                length = lengths.pop()
            except ValueError:
                length = None
            else:
                if length < 0:
                    length = None

        # Convert status to int for comparison
        # In some cases, httplib returns a status of "_UNKNOWN"
        try:
            status = int(self.status)
        except ValueError:
            status = 0

        # Check for responses that shouldn't include a body
        if status in (204, 304) or 100 <= status < 200 or request_method == "HEAD":
            length = 0

        return length

    def _init_decoder(self):
        """
        Set-up the _decoder attribute if necessary.
        """
        # Note: content-encoding value should be case-insensitive, per RFC 7230
        # Section 3.2
        content_encoding = self.headers.get("content-encoding", "").lower()
        if self._decoder is None:
            if content_encoding in self.CONTENT_DECODERS:
                self._decoder = _get_decoder(content_encoding)
            elif "," in content_encoding:
                encodings = [
                    e.strip()
                    for e in content_encoding.split(",")
                    if e.strip() in self.CONTENT_DECODERS
                ]
                if len(encodings):
                    self._decoder = _get_decoder(content_encoding)

    DECODER_ERROR_CLASSES = (IOError, zlib.error)
    if brotli is not None:
        DECODER_ERROR_CLASSES += (brotli.error,)

    def _decode(self, data, decode_content, flush_decoder):
        """
        Decode the data passed in and potentially flush the decoder.
        """
        if not decode_content:
            return data

        try:
            if self._decoder:
                data = self._decoder.decompress(data)
        except self.DECODER_ERROR_CLASSES as e:
            content_encoding = self.headers.get("content-encoding", "").lower()
            raise DecodeError(
                "Received response with content-encoding: %s, but "
                "failed to decode it." % content_encoding,
                e,
            )
        if flush_decoder:
            data += self._flush_decoder()

        return data

    def _flush_decoder(self):
        """
        Flushes the decoder. Should only be called if the decoder is actually
        being used.
        """
        if self._decoder:
            buf = self._decoder.decompress(b"")
            return buf + self._decoder.flush()

        return b""

    @contextmanager
    def _error_catcher(self):
        """
        Catch low-level python exceptions, instead re-raising urllib3
        variants, so that low-level exceptions are not leaked in the
        high-level api.

        On exit, release the connection back to the pool.
        """
        clean_exit = False

        try:
            try:
                yield

            except SocketTimeout:
                # FIXME: Ideally we'd like to include the url in the ReadTimeoutError but
                # there is yet no clean way to get at it from this context.
                raise ReadTimeoutError(self._pool, None, "Read timed out.")

            except BaseSSLError as e:
                # FIXME: Is there a better way to differentiate between SSLErrors?
                if "read operation timed out" not in str(e):
                    # SSL errors related to framing/MAC get wrapped and reraised here
                    raise SSLError(e)

                raise ReadTimeoutError(self._pool, None, "Read timed out.")

            except (HTTPException, SocketError) as e:
                # This includes IncompleteRead.
                raise ProtocolError("Connection broken: %r" % e, e)

            # If no exception is thrown, we should avoid cleaning up
            # unnecessarily.
            clean_exit = True
        finally:
            # If we didn't terminate cleanly, we need to throw away our
            # connection.
            if not clean_exit:
                # The response may not be closed but we're not going to use it
                # anymore so close it now to ensure that the connection is
                # released back to the pool.
                if self._original_response:
                    self._original_response.close()

                # Closing the response may not actually be sufficient to close
                # everything, so if we have a hold of the connection close that
                # too.
                if self._connection:
                    self._connection.close()

            # If we hold the original response but it's closed now, we should
            # return the connection back to the pool.
            if self._original_response and self._original_response.isclosed():
                self.release_conn()

    def _fp_read(self, amt):
        """
        Read a response with the thought that reading the number of bytes
        larger than can fit in a 32-bit int at a time via SSL in some
        known cases leads to an overflow error that has to be prevented
        if `amt` or `self.length_remaining` indicate that a problem may
        happen.

        The known cases:
          * 3.8 <= CPython < 3.9.7 because of a bug
            https://github.com/urllib3/urllib3/issues/2513#issuecomment-1152559900.
          * urllib3 injected with pyOpenSSL-backed SSL-support.
          * CPython < 3.10 only when `amt` does not fit 32-bit int.
        """
        assert self._fp
        c_int_max = 2 ** 31 - 1
        if (
            (
                (amt and amt > c_int_max)
                or (self.length_remaining and self.length_remaining > c_int_max)
            )
            and not util.IS_SECURETRANSPORT
            and (util.IS_PYOPENSSL or sys.version_info < (3, 10))
        ):
            buffer = io.BytesIO()
            # Besides `max_chunk_amt` being a maximum chunk size, it
            # affects memory overhead of reading a response by this
            # method in CPython.
            # `c_int_max` equal to 2 GiB - 1 byte is the actual maximum
            # chunk size that does not lead to an overflow error, but
            # 256 MiB is a compromise.
            max_chunk_amt = 2 ** 28
            while amt is None or amt != 0:
                if amt is not None:
                    chunk_amt = min(amt, max_chunk_amt)
                    amt -= chunk_amt
                else:
                    chunk_amt = max_chunk_amt
                data = self._fp.read(chunk_amt)
                if not data:
                    break
                buffer.write(data)
                del data  # to reduce peak memory usage by `max_chunk_amt`.
            return buffer.getvalue()
        else:
            # StringIO doesn't like amt=None
            return self._fp.read(amt) if amt is not None else self._fp.read()

    def read(self, amt=None, decode_content=None, cache_content=False):
        """
        Similar to :meth:`http.client.HTTPResponse.read`, but with two additional
        parameters: ``decode_content`` and ``cache_content``.

        :param amt:
            How much of the content to read. If specified, caching is skipped
            because it doesn't make sense to cache partial content as the full
            response.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.

        :param cache_content:
            If True, will save the returned data such that the same result is
            returned despite of the state of the underlying file object. This
            is useful if you want the ``.data`` property to continue working
            after having ``.read()`` the file object. (Overridden if ``amt`` is
            set.)
        """
        self._init_decoder()
        if decode_content is None:
            decode_content = self.decode_content

        if self._fp is None:
            return

        flush_decoder = False
        fp_closed = getattr(self._fp, "closed", False)

        with self._error_catcher():
            data = self._fp_read(amt) if not fp_closed else b""
            if amt is None:
                flush_decoder = True
            else:
                cache_content = False
                if (
                    amt != 0 and not data
                ):  # Platform-specific: Buggy versions of Python.
                    # Close the connection when no data is returned
                    #
                    # This is redundant to what httplib/http.client _should_
                    # already do.  However, versions of python released before
                    # December 15, 2012 (http://bugs.python.org/issue16298) do
                    # not properly close the connection in all cases. There is
                    # no harm in redundantly calling close.
                    self._fp.close()
                    flush_decoder = True
                    if self.enforce_content_length and self.length_remaining not in (
                        0,
                        None,
                    ):
                        # This is an edge case that httplib failed to cover due
                        # to concerns of backward compatibility. We're
                        # addressing it here to make sure IncompleteRead is
                        # raised during streaming, so all calls with incorrect
                        # Content-Length are caught.
                        raise IncompleteRead(self._fp_bytes_read, self.length_remaining)

        if data:
            self._fp_bytes_read += len(data)
            if self.length_remaining is not None:
                self.length_remaining -= len(data)

            data = self._decode(data, decode_content, flush_decoder)

            if cache_content:
                self._body = data

        return data

    def stream(self, amt=2 ** 16, decode_content=None):
        """
        A generator wrapper for the read() method. A call will block until
        ``amt`` bytes have been read from the connection or until the
        connection is closed.

        :param amt:
            How much of the content to read. The generator will return up to
            much data per iteration, but may return less. This is particularly
            likely when using compressed data. However, the empty string will
            never be returned.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.
        """
        if self.chunked and self.supports_chunked_reads():
            for line in self.read_chunked(amt, decode_content=decode_content):
                yield line
        else:
            while not is_fp_closed(self._fp):
                data = self.read(amt=amt, decode_content=decode_content)

                if data:
                    yield data

    @classmethod
    def from_httplib(ResponseCls, r, **response_kw):
        """
        Given an :class:`http.client.HTTPResponse` instance ``r``, return a
        corresponding :class:`urllib3.response.HTTPResponse` object.

        Remaining parameters are passed to the HTTPResponse constructor, along
        with ``original_response=r``.
        """
        headers = r.msg

        if not isinstance(headers, HTTPHeaderDict):
            if six.PY2:
                # Python 2.7
                headers = HTTPHeaderDict.from_httplib(headers)
            else:
                headers = HTTPHeaderDict(headers.items())

        # HTTPResponse objects in Python 3 don't have a .strict attribute
        strict = getattr(r, "strict", 0)
        resp = ResponseCls(
            body=r,
            headers=headers,
            status=r.status,
            version=r.version,
            reason=r.reason,
            strict=strict,
            original_response=r,
            **response_kw
        )
        return resp

    # Backwards-compatibility methods for http.client.HTTPResponse
    def getheaders(self):
        warnings.warn(
            "HTTPResponse.getheaders() is deprecated and will be removed "
            "in urllib3 v2.1.0. Instead access HTTPResponse.headers directly.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return self.headers

    def getheader(self, name, default=None):
        warnings.warn(
            "HTTPResponse.getheader() is deprecated and will be removed "
            "in urllib3 v2.1.0. Instead use HTTPResponse.headers.get(name, default).",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return self.headers.get(name, default)

    # Backwards compatibility for http.cookiejar
    def info(self):
        return self.headers

    # Overrides from io.IOBase
    def close(self):
        if not self.closed:
            self._fp.close()

        if self._connection:
            self._connection.close()

        if not self.auto_close:
            io.IOBase.close(self)

    @property
    def closed(self):
        if not self.auto_close:
            return io.IOBase.closed.__get__(self)
        elif self._fp is None:
            return True
        elif hasattr(self._fp, "isclosed"):
            return self._fp.isclosed()
        elif hasattr(self._fp, "closed"):
            return self._fp.closed
        else:
            return True

    def fileno(self):
        if self._fp is None:
            raise IOError("HTTPResponse has no file to get a fileno from")
        elif hasattr(self._fp, "fileno"):
            return self._fp.fileno()
        else:
            raise IOError(
                "The file-like object this HTTPResponse is wrapped "
                "around has no file descriptor"
            )

    def flush(self):
        if (
            self._fp is not None
            and hasattr(self._fp, "flush")
            and not getattr(self._fp, "closed", False)
        ):
            return self._fp.flush()

    def readable(self):
        # This method is required for `io` module compatibility.
        return True

    def readinto(self, b):
        # This method is required for `io` module compatibility.
        temp = self.read(len(b))
        if len(temp) == 0:
            return 0
        else:
            b[: len(temp)] = temp
            return len(temp)

    def supports_chunked_reads(self):
        """
        Checks if the underlying file-like object looks like a
        :class:`http.client.HTTPResponse` object. We do this by testing for
        the fp attribute. If it is present we assume it returns raw chunks as
        processed by read_chunked().
        """
        return hasattr(self._fp, "fp")

    def _update_chunk_length(self):
        # First, we'll figure out length of a chunk and then
        # we'll try to read it from socket.
        if self.chunk_left is not None:
            return
        line = self._fp.fp.readline()
        line = line.split(b";", 1)[0]
        try:
            self.chunk_left = int(line, 16)
        except ValueError:
            # Invalid chunked protocol response, abort.
            self.close()
            raise InvalidChunkLength(self, line)

    def _handle_chunk(self, amt):
        returned_chunk = None
        if amt is None:
            chunk = self._fp._safe_read(self.chunk_left)
            returned_chunk = chunk
            self._fp._safe_read(2)  # Toss the CRLF at the end of the chunk.
            self.chunk_left = None
        elif amt < self.chunk_left:
            value = self._fp._safe_read(amt)
            self.chunk_left = self.chunk_left - amt
            returned_chunk = value
        elif amt == self.chunk_left:
            value = self._fp._safe_read(amt)
            self._fp._safe_read(2)  # Toss the CRLF at the end of the chunk.
            self.chunk_left = None
            returned_chunk = value
        else:  # amt > self.chunk_left
            returned_chunk = self._fp._safe_read(self.chunk_left)
            self._fp._safe_read(2)  # Toss the CRLF at the end of the chunk.
            self.chunk_left = None
        return returned_chunk

    def read_chunked(self, amt=None, decode_content=None):
        """
        Similar to :meth:`HTTPResponse.read`, but with an additional
        parameter: ``decode_content``.

        :param amt:
            How much of the content to read. If specified, caching is skipped
            because it doesn't make sense to cache partial content as the full
            response.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.
        """
        self._init_decoder()
        # FIXME: Rewrite this method and make it a class with a better structured logic.
        if not self.chunked:
            raise ResponseNotChunked(
                "Response is not chunked. "
                "Header 'transfer-encoding: chunked' is missing."
            )
        if not self.supports_chunked_reads():
            raise BodyNotHttplibCompatible(
                "Body should be http.client.HTTPResponse like. "
                "It should have have an fp attribute which returns raw chunks."
            )

        with self._error_catcher():
            # Don't bother reading the body of a HEAD request.
            if self._original_response and is_response_to_head(self._original_response):
                self._original_response.close()
                return

            # If a response is already read and closed
            # then return immediately.
            if self._fp.fp is None:
                return

            while True:
                self._update_chunk_length()
                if self.chunk_left == 0:
                    break
                chunk = self._handle_chunk(amt)
                decoded = self._decode(
                    chunk, decode_content=decode_content, flush_decoder=False
                )
                if decoded:
                    yield decoded

            if decode_content:
                # On CPython and PyPy, we should never need to flush the
                # decoder. However, on Jython we *might* need to, so
                # lets defensively do it anyway.
                decoded = self._flush_decoder()
                if decoded:  # Platform-specific: Jython.
                    yield decoded

            # Chunk content ends with \r\n: discard it.
            while True:
                line = self._fp.fp.readline()
                if not line:
                    # Some sites may not end with '\r\n'.
                    break
                if line == b"\r\n":
                    break

            # We read everything; close the "file".
            if self._original_response:
                self._original_response.close()

    def geturl(self):
        """
        Returns the URL that was the source of this response.
        If the request that generated this response redirected, this method
        will return the final redirect location.
        """
        if self.retries is not None and len(self.retries.history):
            return self.retries.history[-1].redirect_location
        else:
            return self._request_url

    def __iter__(self):
        buffer = []
        for chunk in self.stream(decode_content=True):
            if b"\n" in chunk:
                chunk = chunk.split(b"\n")
                yield b"".join(buffer) + chunk[0] + b"\n"
                for x in chunk[1:-1]:
                    yield x + b"\n"
                if chunk[-1]:
                    buffer = [chunk[-1]]
                else:
                    buffer = []
            else:
                buffer.append(chunk)
        if buffer:
            yield b"".join(buffer)

# === NexusCore/openenv\Lib\site-packages\matplotlib\_type1font.py ===
"""
A class representing a Type 1 font.

This version reads pfa and pfb files and splits them for embedding in
pdf files. It also supports SlantFont and ExtendFont transformations,
similarly to pdfTeX and friends. There is no support yet for subsetting.

Usage::

    font = Type1Font(filename)
    clear_part, encrypted_part, finale = font.parts
    slanted_font = font.transform({'slant': 0.167})
    extended_font = font.transform({'extend': 1.2})

Sources:

* Adobe Technical Note #5040, Supporting Downloadable PostScript
  Language Fonts.

* Adobe Type 1 Font Format, Adobe Systems Incorporated, third printing,
  v1.1, 1993. ISBN 0-201-57044-0.
"""

from __future__ import annotations

import binascii
import functools
import logging
import re
import string
import struct
import typing as T

import numpy as np

from matplotlib.cbook import _format_approx
from . import _api

_log = logging.getLogger(__name__)


class _Token:
    """
    A token in a PostScript stream.

    Attributes
    ----------
    pos : int
        Position, i.e. offset from the beginning of the data.
    raw : str
        Raw text of the token.
    kind : str
        Description of the token (for debugging or testing).
    """
    __slots__ = ('pos', 'raw')
    kind = '?'

    def __init__(self, pos, raw):
        _log.debug('type1font._Token %s at %d: %r', self.kind, pos, raw)
        self.pos = pos
        self.raw = raw

    def __str__(self):
        return f"<{self.kind} {self.raw} @{self.pos}>"

    def endpos(self):
        """Position one past the end of the token"""
        return self.pos + len(self.raw)

    def is_keyword(self, *names):
        """Is this a name token with one of the names?"""
        return False

    def is_slash_name(self):
        """Is this a name token that starts with a slash?"""
        return False

    def is_delim(self):
        """Is this a delimiter token?"""
        return False

    def is_number(self):
        """Is this a number token?"""
        return False

    def value(self):
        return self.raw


class _NameToken(_Token):
    kind = 'name'

    def is_slash_name(self):
        return self.raw.startswith('/')

    def value(self):
        return self.raw[1:]


class _BooleanToken(_Token):
    kind = 'boolean'

    def value(self):
        return self.raw == 'true'


class _KeywordToken(_Token):
    kind = 'keyword'

    def is_keyword(self, *names):
        return self.raw in names


class _DelimiterToken(_Token):
    kind = 'delimiter'

    def is_delim(self):
        return True

    def opposite(self):
        return {'[': ']', ']': '[',
                '{': '}', '}': '{',
                '<<': '>>', '>>': '<<'
                }[self.raw]


class _WhitespaceToken(_Token):
    kind = 'whitespace'


class _StringToken(_Token):
    kind = 'string'
    _escapes_re = re.compile(r'\\([\\()nrtbf]|[0-7]{1,3})')
    _replacements = {'\\': '\\', '(': '(', ')': ')', 'n': '\n',
                     'r': '\r', 't': '\t', 'b': '\b', 'f': '\f'}
    _ws_re = re.compile('[\0\t\r\f\n ]')

    @classmethod
    def _escape(cls, match):
        group = match.group(1)
        try:
            return cls._replacements[group]
        except KeyError:
            return chr(int(group, 8))

    @functools.lru_cache
    def value(self):
        if self.raw[0] == '(':
            return self._escapes_re.sub(self._escape, self.raw[1:-1])
        else:
            data = self._ws_re.sub('', self.raw[1:-1])
            if len(data) % 2 == 1:
                data += '0'
            return binascii.unhexlify(data)


class _BinaryToken(_Token):
    kind = 'binary'

    def value(self):
        return self.raw[1:]


class _NumberToken(_Token):
    kind = 'number'

    def is_number(self):
        return True

    def value(self):
        if '.' not in self.raw:
            return int(self.raw)
        else:
            return float(self.raw)


def _tokenize(data: bytes, skip_ws: bool) -> T.Generator[_Token, int, None]:
    """
    A generator that produces _Token instances from Type-1 font code.

    The consumer of the generator may send an integer to the tokenizer to
    indicate that the next token should be _BinaryToken of the given length.

    Parameters
    ----------
    data : bytes
        The data of the font to tokenize.

    skip_ws : bool
        If true, the generator will drop any _WhitespaceTokens from the output.
    """

    text = data.decode('ascii', 'replace')
    whitespace_or_comment_re = re.compile(r'[\0\t\r\f\n ]+|%[^\r\n]*')
    token_re = re.compile(r'/{0,2}[^]\0\t\r\f\n ()<>{}/%[]+')
    instring_re = re.compile(r'[()\\]')
    hex_re = re.compile(r'^<[0-9a-fA-F\0\t\r\f\n ]*>$')
    oct_re = re.compile(r'[0-7]{1,3}')
    pos = 0
    next_binary: int | None = None

    while pos < len(text):
        if next_binary is not None:
            n = next_binary
            next_binary = (yield _BinaryToken(pos, data[pos:pos+n]))
            pos += n
            continue
        match = whitespace_or_comment_re.match(text, pos)
        if match:
            if not skip_ws:
                next_binary = (yield _WhitespaceToken(pos, match.group()))
            pos = match.end()
        elif text[pos] == '(':
            # PostScript string rules:
            # - parentheses must be balanced
            # - backslashes escape backslashes and parens
            # - also codes \n\r\t\b\f and octal escapes are recognized
            # - other backslashes do not escape anything
            start = pos
            pos += 1
            depth = 1
            while depth:
                match = instring_re.search(text, pos)
                if match is None:
                    raise ValueError(
                        f'Unterminated string starting at {start}')
                pos = match.end()
                if match.group() == '(':
                    depth += 1
                elif match.group() == ')':
                    depth -= 1
                else:  # a backslash
                    char = text[pos]
                    if char in r'\()nrtbf':
                        pos += 1
                    else:
                        octal = oct_re.match(text, pos)
                        if octal:
                            pos = octal.end()
                        else:
                            pass  # non-escaping backslash
            next_binary = (yield _StringToken(start, text[start:pos]))
        elif text[pos:pos + 2] in ('<<', '>>'):
            next_binary = (yield _DelimiterToken(pos, text[pos:pos + 2]))
            pos += 2
        elif text[pos] == '<':
            start = pos
            try:
                pos = text.index('>', pos) + 1
            except ValueError as e:
                raise ValueError(f'Unterminated hex string starting at {start}'
                                 ) from e
            if not hex_re.match(text[start:pos]):
                raise ValueError(f'Malformed hex string starting at {start}')
            next_binary = (yield _StringToken(pos, text[start:pos]))
        else:
            match = token_re.match(text, pos)
            if match:
                raw = match.group()
                if raw.startswith('/'):
                    next_binary = (yield _NameToken(pos, raw))
                elif match.group() in ('true', 'false'):
                    next_binary = (yield _BooleanToken(pos, raw))
                else:
                    try:
                        float(raw)
                        next_binary = (yield _NumberToken(pos, raw))
                    except ValueError:
                        next_binary = (yield _KeywordToken(pos, raw))
                pos = match.end()
            else:
                next_binary = (yield _DelimiterToken(pos, text[pos]))
                pos += 1


class _BalancedExpression(_Token):
    pass


def _expression(initial, tokens, data):
    """
    Consume some number of tokens and return a balanced PostScript expression.

    Parameters
    ----------
    initial : _Token
        The token that triggered parsing a balanced expression.
    tokens : iterator of _Token
        Following tokens.
    data : bytes
        Underlying data that the token positions point to.

    Returns
    -------
    _BalancedExpression
    """
    delim_stack = []
    token = initial
    while True:
        if token.is_delim():
            if token.raw in ('[', '{'):
                delim_stack.append(token)
            elif token.raw in (']', '}'):
                if not delim_stack:
                    raise RuntimeError(f"unmatched closing token {token}")
                match = delim_stack.pop()
                if match.raw != token.opposite():
                    raise RuntimeError(
                        f"opening token {match} closed by {token}"
                    )
                if not delim_stack:
                    break
            else:
                raise RuntimeError(f'unknown delimiter {token}')
        elif not delim_stack:
            break
        token = next(tokens)
    return _BalancedExpression(
        initial.pos,
        data[initial.pos:token.endpos()].decode('ascii', 'replace')
    )


class Type1Font:
    """
    A class representing a Type-1 font, for use by backends.

    Attributes
    ----------
    parts : tuple
        A 3-tuple of the cleartext part, the encrypted part, and the finale of
        zeros.

    decrypted : bytes
        The decrypted form of ``parts[1]``.

    prop : dict[str, Any]
        A dictionary of font properties. Noteworthy keys include:

        - FontName: PostScript name of the font
        - Encoding: dict from numeric codes to glyph names
        - FontMatrix: bytes object encoding a matrix
        - UniqueID: optional font identifier, dropped when modifying the font
        - CharStrings: dict from glyph names to byte code
        - Subrs: array of byte code subroutines
        - OtherSubrs: bytes object encoding some PostScript code
    """
    __slots__ = ('parts', 'decrypted', 'prop', '_pos', '_abbr')
    # the _pos dict contains (begin, end) indices to parts[0] + decrypted
    # so that they can be replaced when transforming the font;
    # but since sometimes a definition appears in both parts[0] and decrypted,
    # _pos[name] is an array of such pairs
    #
    # _abbr maps three standard abbreviations to their particular names in
    # this font (e.g. 'RD' is named '-|' in some fonts)

    def __init__(self, input):
        """
        Initialize a Type-1 font.

        Parameters
        ----------
        input : str or 3-tuple
            Either a pfb file name, or a 3-tuple of already-decoded Type-1
            font `~.Type1Font.parts`.
        """
        if isinstance(input, tuple) and len(input) == 3:
            self.parts = input
        else:
            with open(input, 'rb') as file:
                data = self._read(file)
            self.parts = self._split(data)

        self.decrypted = self._decrypt(self.parts[1], 'eexec')
        self._abbr = {'RD': 'RD', 'ND': 'ND', 'NP': 'NP'}
        self._parse()

    def _read(self, file):
        """Read the font from a file, decoding into usable parts."""
        rawdata = file.read()
        if not rawdata.startswith(b'\x80'):
            return rawdata

        data = b''
        while rawdata:
            if not rawdata.startswith(b'\x80'):
                raise RuntimeError('Broken pfb file (expected byte 128, '
                                   'got %d)' % rawdata[0])
            type = rawdata[1]
            if type in (1, 2):
                length, = struct.unpack('<i', rawdata[2:6])
                segment = rawdata[6:6 + length]
                rawdata = rawdata[6 + length:]

            if type == 1:       # ASCII text: include verbatim
                data += segment
            elif type == 2:     # binary data: encode in hexadecimal
                data += binascii.hexlify(segment)
            elif type == 3:     # end of file
                break
            else:
                raise RuntimeError('Unknown segment type %d in pfb file' % type)

        return data

    def _split(self, data):
        """
        Split the Type 1 font into its three main parts.

        The three parts are: (1) the cleartext part, which ends in a
        eexec operator; (2) the encrypted part; (3) the fixed part,
        which contains 512 ASCII zeros possibly divided on various
        lines, a cleartomark operator, and possibly something else.
        """

        # Cleartext part: just find the eexec and skip whitespace
        idx = data.index(b'eexec')
        idx += len(b'eexec')
        while data[idx] in b' \t\r\n':
            idx += 1
        len1 = idx

        # Encrypted part: find the cleartomark operator and count
        # zeros backward
        idx = data.rindex(b'cleartomark') - 1
        zeros = 512
        while zeros and data[idx] in b'0' or data[idx] in b'\r\n':
            if data[idx] in b'0':
                zeros -= 1
            idx -= 1
        if zeros:
            # this may have been a problem on old implementations that
            # used the zeros as necessary padding
            _log.info('Insufficiently many zeros in Type 1 font')

        # Convert encrypted part to binary (if we read a pfb file, we may end
        # up converting binary to hexadecimal to binary again; but if we read
        # a pfa file, this part is already in hex, and I am not quite sure if
        # even the pfb format guarantees that it will be in binary).
        idx1 = len1 + ((idx - len1 + 2) & ~1)  # ensure an even number of bytes
        binary = binascii.unhexlify(data[len1:idx1])

        return data[:len1], binary, data[idx+1:]

    @staticmethod
    def _decrypt(ciphertext, key, ndiscard=4):
        """
        Decrypt ciphertext using the Type-1 font algorithm.

        The algorithm is described in Adobe's "Adobe Type 1 Font Format".
        The key argument can be an integer, or one of the strings
        'eexec' and 'charstring', which map to the key specified for the
        corresponding part of Type-1 fonts.

        The ndiscard argument should be an integer, usually 4.
        That number of bytes is discarded from the beginning of plaintext.
        """

        key = _api.check_getitem({'eexec': 55665, 'charstring': 4330}, key=key)
        plaintext = []
        for byte in ciphertext:
            plaintext.append(byte ^ (key >> 8))
            key = ((key+byte) * 52845 + 22719) & 0xffff

        return bytes(plaintext[ndiscard:])

    @staticmethod
    def _encrypt(plaintext, key, ndiscard=4):
        """
        Encrypt plaintext using the Type-1 font algorithm.

        The algorithm is described in Adobe's "Adobe Type 1 Font Format".
        The key argument can be an integer, or one of the strings
        'eexec' and 'charstring', which map to the key specified for the
        corresponding part of Type-1 fonts.

        The ndiscard argument should be an integer, usually 4. That
        number of bytes is prepended to the plaintext before encryption.
        This function prepends NUL bytes for reproducibility, even though
        the original algorithm uses random bytes, presumably to avoid
        cryptanalysis.
        """

        key = _api.check_getitem({'eexec': 55665, 'charstring': 4330}, key=key)
        ciphertext = []
        for byte in b'\0' * ndiscard + plaintext:
            c = byte ^ (key >> 8)
            ciphertext.append(c)
            key = ((key + c) * 52845 + 22719) & 0xffff

        return bytes(ciphertext)

    def _parse(self):
        """
        Find the values of various font properties. This limited kind
        of parsing is described in Chapter 10 "Adobe Type Manager
        Compatibility" of the Type-1 spec.
        """
        # Start with reasonable defaults
        prop = {'Weight': 'Regular', 'ItalicAngle': 0.0, 'isFixedPitch': False,
                'UnderlinePosition': -100, 'UnderlineThickness': 50}
        pos = {}
        data = self.parts[0] + self.decrypted

        source = _tokenize(data, True)
        while True:
            # See if there is a key to be assigned a value
            # e.g. /FontName in /FontName /Helvetica def
            try:
                token = next(source)
            except StopIteration:
                break
            if token.is_delim():
                # skip over this - we want top-level keys only
                _expression(token, source, data)
            if token.is_slash_name():
                key = token.value()
                keypos = token.pos
            else:
                continue

            # Some values need special parsing
            if key in ('Subrs', 'CharStrings', 'Encoding', 'OtherSubrs'):
                prop[key], endpos = {
                    'Subrs': self._parse_subrs,
                    'CharStrings': self._parse_charstrings,
                    'Encoding': self._parse_encoding,
                    'OtherSubrs': self._parse_othersubrs
                }[key](source, data)
                pos.setdefault(key, []).append((keypos, endpos))
                continue

            try:
                token = next(source)
            except StopIteration:
                break

            if isinstance(token, _KeywordToken):
                # constructs like
                # FontDirectory /Helvetica known {...} {...} ifelse
                # mean the key was not really a key
                continue

            if token.is_delim():
                value = _expression(token, source, data).raw
            else:
                value = token.value()

            # look for a 'def' possibly preceded by access modifiers
            try:
                kw = next(
                    kw for kw in source
                    if not kw.is_keyword('readonly', 'noaccess', 'executeonly')
                )
            except StopIteration:
                break

            # sometimes noaccess def and readonly def are abbreviated
            if kw.is_keyword('def', self._abbr['ND'], self._abbr['NP']):
                prop[key] = value
                pos.setdefault(key, []).append((keypos, kw.endpos()))

            # detect the standard abbreviations
            if value == '{noaccess def}':
                self._abbr['ND'] = key
            elif value == '{noaccess put}':
                self._abbr['NP'] = key
            elif value == '{string currentfile exch readstring pop}':
                self._abbr['RD'] = key

        # Fill in the various *Name properties
        if 'FontName' not in prop:
            prop['FontName'] = (prop.get('FullName') or
                                prop.get('FamilyName') or
                                'Unknown')
        if 'FullName' not in prop:
            prop['FullName'] = prop['FontName']
        if 'FamilyName' not in prop:
            extras = ('(?i)([ -](regular|plain|italic|oblique|(semi)?bold|'
                      '(ultra)?light|extra|condensed))+$')
            prop['FamilyName'] = re.sub(extras, '', prop['FullName'])
        # Decrypt the encrypted parts
        ndiscard = prop.get('lenIV', 4)
        cs = prop['CharStrings']
        for key, value in cs.items():
            cs[key] = self._decrypt(value, 'charstring', ndiscard)
        if 'Subrs' in prop:
            prop['Subrs'] = [
                self._decrypt(value, 'charstring', ndiscard)
                for value in prop['Subrs']
            ]

        self.prop = prop
        self._pos = pos

    def _parse_subrs(self, tokens, _data):
        count_token = next(tokens)
        if not count_token.is_number():
            raise RuntimeError(
                f"Token following /Subrs must be a number, was {count_token}"
            )
        count = count_token.value()
        array = [None] * count
        next(t for t in tokens if t.is_keyword('array'))
        for _ in range(count):
            next(t for t in tokens if t.is_keyword('dup'))
            index_token = next(tokens)
            if not index_token.is_number():
                raise RuntimeError(
                    "Token following dup in Subrs definition must be a "
                    f"number, was {index_token}"
                )
            nbytes_token = next(tokens)
            if not nbytes_token.is_number():
                raise RuntimeError(
                    "Second token following dup in Subrs definition must "
                    f"be a number, was {nbytes_token}"
                )
            token = next(tokens)
            if not token.is_keyword(self._abbr['RD']):
                raise RuntimeError(
                    f"Token preceding subr must be {self._abbr['RD']}, "
                    f"was {token}"
                )
            binary_token = tokens.send(1+nbytes_token.value())
            array[index_token.value()] = binary_token.value()

        return array, next(tokens).endpos()

    @staticmethod
    def _parse_charstrings(tokens, _data):
        count_token = next(tokens)
        if not count_token.is_number():
            raise RuntimeError(
                "Token following /CharStrings must be a number, "
                f"was {count_token}"
            )
        count = count_token.value()
        charstrings = {}
        next(t for t in tokens if t.is_keyword('begin'))
        while True:
            token = next(t for t in tokens
                         if t.is_keyword('end') or t.is_slash_name())
            if token.raw == 'end':
                return charstrings, token.endpos()
            glyphname = token.value()
            nbytes_token = next(tokens)
            if not nbytes_token.is_number():
                raise RuntimeError(
                    f"Token following /{glyphname} in CharStrings definition "
                    f"must be a number, was {nbytes_token}"
                )
            next(tokens)  # usually RD or |-
            binary_token = tokens.send(1+nbytes_token.value())
            charstrings[glyphname] = binary_token.value()

    @staticmethod
    def _parse_encoding(tokens, _data):
        # this only works for encodings that follow the Adobe manual
        # but some old fonts include non-compliant data - we log a warning
        # and return a possibly incomplete encoding
        encoding = {}
        while True:
            token = next(t for t in tokens
                         if t.is_keyword('StandardEncoding', 'dup', 'def'))
            if token.is_keyword('StandardEncoding'):
                return _StandardEncoding, token.endpos()
            if token.is_keyword('def'):
                return encoding, token.endpos()
            index_token = next(tokens)
            if not index_token.is_number():
                _log.warning(
                    f"Parsing encoding: expected number, got {index_token}"
                )
                continue
            name_token = next(tokens)
            if not name_token.is_slash_name():
                _log.warning(
                    f"Parsing encoding: expected slash-name, got {name_token}"
                )
                continue
            encoding[index_token.value()] = name_token.value()

    @staticmethod
    def _parse_othersubrs(tokens, data):
        init_pos = None
        while True:
            token = next(tokens)
            if init_pos is None:
                init_pos = token.pos
            if token.is_delim():
                _expression(token, tokens, data)
            elif token.is_keyword('def', 'ND', '|-'):
                return data[init_pos:token.endpos()], token.endpos()

    def transform(self, effects):
        """
        Return a new font that is slanted and/or extended.

        Parameters
        ----------
        effects : dict
            A dict with optional entries:

            - 'slant' : float, default: 0
                Tangent of the angle that the font is to be slanted to the
                right. Negative values slant to the left.
            - 'extend' : float, default: 1
                Scaling factor for the font width. Values less than 1 condense
                the glyphs.

        Returns
        -------
        `Type1Font`
        """
        fontname = self.prop['FontName']
        italicangle = self.prop['ItalicAngle']

        array = [
            float(x) for x in (self.prop['FontMatrix']
                               .lstrip('[').rstrip(']').split())
        ]
        oldmatrix = np.eye(3, 3)
        oldmatrix[0:3, 0] = array[::2]
        oldmatrix[0:3, 1] = array[1::2]
        modifier = np.eye(3, 3)

        if 'slant' in effects:
            slant = effects['slant']
            fontname += f'_Slant_{int(1000 * slant)}'
            italicangle = round(
                float(italicangle) - np.arctan(slant) / np.pi * 180,
                5
            )
            modifier[1, 0] = slant

        if 'extend' in effects:
            extend = effects['extend']
            fontname += f'_Extend_{int(1000 * extend)}'
            modifier[0, 0] = extend

        newmatrix = np.dot(modifier, oldmatrix)
        array[::2] = newmatrix[0:3, 0]
        array[1::2] = newmatrix[0:3, 1]
        fontmatrix = (
            f"[{' '.join(_format_approx(x, 6) for x in array)}]"
        )
        replacements = (
            [(x, f'/FontName/{fontname} def')
             for x in self._pos['FontName']]
            + [(x, f'/ItalicAngle {italicangle} def')
               for x in self._pos['ItalicAngle']]
            + [(x, f'/FontMatrix {fontmatrix} readonly def')
               for x in self._pos['FontMatrix']]
            + [(x, '') for x in self._pos.get('UniqueID', [])]
        )

        data = bytearray(self.parts[0])
        data.extend(self.decrypted)
        len0 = len(self.parts[0])
        for (pos0, pos1), value in sorted(replacements, reverse=True):
            data[pos0:pos1] = value.encode('ascii', 'replace')
            if pos0 < len(self.parts[0]):
                if pos1 >= len(self.parts[0]):
                    raise RuntimeError(
                        f"text to be replaced with {value} spans "
                        "the eexec boundary"
                    )
                len0 += len(value) - pos1 + pos0

        data = bytes(data)
        return Type1Font((
            data[:len0],
            self._encrypt(data[len0:], 'eexec'),
            self.parts[2]
        ))


_StandardEncoding = {
    **{ord(letter): letter for letter in string.ascii_letters},
    0: '.notdef',
    32: 'space',
    33: 'exclam',
    34: 'quotedbl',
    35: 'numbersign',
    36: 'dollar',
    37: 'percent',
    38: 'ampersand',
    39: 'quoteright',
    40: 'parenleft',
    41: 'parenright',
    42: 'asterisk',
    43: 'plus',
    44: 'comma',
    45: 'hyphen',
    46: 'period',
    47: 'slash',
    48: 'zero',
    49: 'one',
    50: 'two',
    51: 'three',
    52: 'four',
    53: 'five',
    54: 'six',
    55: 'seven',
    56: 'eight',
    57: 'nine',
    58: 'colon',
    59: 'semicolon',
    60: 'less',
    61: 'equal',
    62: 'greater',
    63: 'question',
    64: 'at',
    91: 'bracketleft',
    92: 'backslash',
    93: 'bracketright',
    94: 'asciicircum',
    95: 'underscore',
    96: 'quoteleft',
    123: 'braceleft',
    124: 'bar',
    125: 'braceright',
    126: 'asciitilde',
    161: 'exclamdown',
    162: 'cent',
    163: 'sterling',
    164: 'fraction',
    165: 'yen',
    166: 'florin',
    167: 'section',
    168: 'currency',
    169: 'quotesingle',
    170: 'quotedblleft',
    171: 'guillemotleft',
    172: 'guilsinglleft',
    173: 'guilsinglright',
    174: 'fi',
    175: 'fl',
    177: 'endash',
    178: 'dagger',
    179: 'daggerdbl',
    180: 'periodcentered',
    182: 'paragraph',
    183: 'bullet',
    184: 'quotesinglbase',
    185: 'quotedblbase',
    186: 'quotedblright',
    187: 'guillemotright',
    188: 'ellipsis',
    189: 'perthousand',
    191: 'questiondown',
    193: 'grave',
    194: 'acute',
    195: 'circumflex',
    196: 'tilde',
    197: 'macron',
    198: 'breve',
    199: 'dotaccent',
    200: 'dieresis',
    202: 'ring',
    203: 'cedilla',
    205: 'hungarumlaut',
    206: 'ogonek',
    207: 'caron',
    208: 'emdash',
    225: 'AE',
    227: 'ordfeminine',
    232: 'Lslash',
    233: 'Oslash',
    234: 'OE',
    235: 'ordmasculine',
    241: 'ae',
    245: 'dotlessi',
    248: 'lslash',
    249: 'oslash',
    250: 'oe',
    251: 'germandbls',
}

# === NexusCore/openenv\Lib\site-packages\adodbapi\test\dbapi20.py ===
#!/usr/bin/env python
"""Python DB API 2.0 driver compliance unit test suite.

   This software is Public Domain and may be used without restrictions.

"Now we have booze and barflies entering the discussion, plus rumours of
 DBAs on drugs... and I won't tell you what flashes through my mind each
 time I read the subject line with 'Anal Compliance' in it.  All around
 this is turning out to be a thoroughly unwholesome unit test."

   -- Ian Bicking
"""

__version__ = "$Revision: 1.15.0 $"[11:-2]
__author__ = "Stuart Bishop <stuart@stuartbishop.net>"

import time
import unittest

# set this to "True" to follow API 2.0 to the letter
TEST_FOR_NON_IDEMPOTENT_CLOSE = False

# Revision 1.15  2019/11/22 00:50:00  kf7xm
# Make Turn off IDEMPOTENT_CLOSE a proper skipTest

# Revision 1.14  2013/05/20 11:02:05  kf7xm
# Add a literal string to the format insertion test to catch trivial re-format algorithms

# Revision 1.13  2013/05/08 14:31:50  kf7xm
# Quick switch to Turn off IDEMPOTENT_CLOSE test. Also: Silence teardown failure


# Revision 1.12  2009/02/06 03:35:11  kf7xm
# Tested okay with Python 3.0, includes last minute patches from Mark H.
#
# Revision 1.1.1.1.2.1  2008/09/20 19:54:59  rupole
# Include latest changes from main branch
# Updates for py3k
#
# Revision 1.11  2005/01/02 02:41:01  zenzen
# Update author email address
#
# Revision 1.10  2003/10/09 03:14:14  zenzen
# Add test for DB API 2.0 optional extension, where database exceptions
# are exposed as attributes on the Connection object.
#
# Revision 1.9  2003/08/13 01:16:36  zenzen
# Minor tweak from Stefan Fleiter
#
# Revision 1.8  2003/04/10 00:13:25  zenzen
# Changes, as per suggestions by M.-A. Lemburg
# - Add a table prefix, to ensure namespace collisions can always be avoided
#
# Revision 1.7  2003/02/26 23:33:37  zenzen
# Break out DDL into helper functions, as per request by David Rushby
#
# Revision 1.6  2003/02/21 03:04:33  zenzen
# Stuff from Henrik Ekelund:
#     added test_None
#     added test_nextset & hooks
#
# Revision 1.5  2003/02/17 22:08:43  zenzen
# Implement suggestions and code from Henrik Eklund - test that cursor.arraysize
# defaults to 1 & generic cursor.callproc test added
#
# Revision 1.4  2003/02/15 00:16:33  zenzen
# Changes, as per suggestions and bug reports by M.-A. Lemburg,
# Matthew T. Kromer, Federico Di Gregorio and Daniel Dittmar
# - Class renamed
# - Now a subclass of TestCase, to avoid requiring the driver stub
#   to use multiple inheritance
# - Reversed the polarity of buggy test in test_description
# - Test exception hierarchy correctly
# - self.populate is now self._populate(), so if a driver stub
#   overrides self.ddl1 this change propogates
# - VARCHAR columns now have a width, which will hopefully make the
#   DDL even more portible (this will be reversed if it causes more problems)
# - cursor.rowcount being checked after various execute and fetchXXX methods
# - Check for fetchall and fetchmany returning empty lists after results
#   are exhausted (already checking for empty lists if select retrieved
#   nothing
# - Fix bugs in test_setoutputsize_basic and test_setinputsizes
#


class DatabaseAPI20Test(unittest.TestCase):
    """Test a database self.driver for DB API 2.0 compatibility.
    This implementation tests Gadfly, but the TestCase
    is structured so that other self.drivers can subclass this
    test case to ensure compiliance with the DB-API. It is
    expected that this TestCase may be expanded in the future
    if ambiguities or edge conditions are discovered.

    The 'Optional Extensions' are not yet being tested.

    self.drivers should subclass this test, overriding setUp, tearDown,
    self.driver, connect_args and connect_kw_args. Class specification
    should be as follows:

    import dbapi20
    class mytest(dbapi20.DatabaseAPI20Test):
       [...]

    Don't 'import DatabaseAPI20Test from dbapi20', or you will
    confuse the unit tester - just 'import dbapi20'.
    """

    # The self.driver module. This should be the module where the 'connect'
    # method is to be found
    driver = None
    connect_args = ()  # List of arguments to pass to connect
    connect_kw_args = {}  # Keyword arguments for connect
    table_prefix = "dbapi20test_"  # If you need to specify a prefix for tables

    ddl1 = "create table %sbooze (name varchar(20))" % table_prefix
    ddl2 = "create table %sbarflys (name varchar(20), drink varchar(30))" % table_prefix
    xddl1 = "drop table %sbooze" % table_prefix
    xddl2 = "drop table %sbarflys" % table_prefix

    lowerfunc = "lower"  # Name of stored procedure to convert string->lowercase

    # Some drivers may need to override these helpers, for example adding
    # a 'commit' after the execute.
    def executeDDL1(self, cursor):
        cursor.execute(self.ddl1)

    def executeDDL2(self, cursor):
        cursor.execute(self.ddl2)

    def setUp(self):
        """self.drivers should override this method to perform required setup
        if any is necessary, such as creating the database.
        """
        pass

    def tearDown(self):
        """self.drivers should override this method to perform required cleanup
        if any is necessary, such as deleting the test database.
        The default drops the tables that may be created.
        """
        try:
            con = self._connect()
            try:
                cur = con.cursor()
                for ddl in (self.xddl1, self.xddl2):
                    try:
                        cur.execute(ddl)
                        con.commit()
                    except self.driver.Error:
                        # Assume table didn't exist. Other tests will check if
                        # execute is busted.
                        pass
            finally:
                con.close()
        except Exception:
            pass

    def _connect(self):
        try:
            r = self.driver.connect(*self.connect_args, **self.connect_kw_args)
        except AttributeError:
            self.fail("No connect method found in self.driver module")
        return r

    def test_connect(self):
        con = self._connect()
        con.close()

    def test_apilevel(self):
        try:
            # Must exist
            apilevel = self.driver.apilevel
            # Must equal 2.0
            self.assertEqual(apilevel, "2.0")
        except AttributeError:
            self.fail("Driver doesn't define apilevel")

    def test_threadsafety(self):
        try:
            # Must exist
            threadsafety = self.driver.threadsafety
            # Must be a valid value
            self.assertTrue(threadsafety in (0, 1, 2, 3))
        except AttributeError:
            self.fail("Driver doesn't define threadsafety")

    def test_paramstyle(self):
        try:
            # Must exist
            paramstyle = self.driver.paramstyle
            # Must be a valid value
            self.assertTrue(
                paramstyle in ("qmark", "numeric", "named", "format", "pyformat")
            )
        except AttributeError:
            self.fail("Driver doesn't define paramstyle")

    def test_Exceptions(self):
        # Make sure required exceptions exist, and are in the defined hierarchy.
        self.assertTrue(issubclass(self.driver.Warning, Exception))
        self.assertTrue(issubclass(self.driver.Error, Exception))

        self.assertTrue(issubclass(self.driver.InterfaceError, self.driver.Error))
        self.assertTrue(issubclass(self.driver.DatabaseError, self.driver.Error))
        self.assertTrue(issubclass(self.driver.OperationalError, self.driver.Error))
        self.assertTrue(issubclass(self.driver.IntegrityError, self.driver.Error))
        self.assertTrue(issubclass(self.driver.InternalError, self.driver.Error))
        self.assertTrue(issubclass(self.driver.ProgrammingError, self.driver.Error))
        self.assertTrue(issubclass(self.driver.NotSupportedError, self.driver.Error))

    def test_ExceptionsAsConnectionAttributes(self):
        # OPTIONAL EXTENSION
        # Test for the optional DB API 2.0 extension, where the exceptions
        # are exposed as attributes on the Connection object
        # I figure this optional extension will be implemented by any
        # driver author who is using this test suite, so it is enabled
        # by default.
        con = self._connect()
        drv = self.driver
        self.assertTrue(con.Warning is drv.Warning)
        self.assertTrue(con.Error is drv.Error)
        self.assertTrue(con.InterfaceError is drv.InterfaceError)
        self.assertTrue(con.DatabaseError is drv.DatabaseError)
        self.assertTrue(con.OperationalError is drv.OperationalError)
        self.assertTrue(con.IntegrityError is drv.IntegrityError)
        self.assertTrue(con.InternalError is drv.InternalError)
        self.assertTrue(con.ProgrammingError is drv.ProgrammingError)
        self.assertTrue(con.NotSupportedError is drv.NotSupportedError)

    def test_commit(self):
        con = self._connect()
        try:
            # Commit must work, even if it doesn't do anything
            con.commit()
        finally:
            con.close()

    def test_rollback(self):
        con = self._connect()
        # If rollback is defined, it should either work or throw
        # the documented exception
        if hasattr(con, "rollback"):
            try:
                con.rollback()
            except self.driver.NotSupportedError:
                pass

    def test_cursor(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

    def test_cursor_isolation(self):
        con = self._connect()
        try:
            # Make sure cursors created from the same connection have
            # the documented transaction isolation level
            cur1 = con.cursor()
            cur2 = con.cursor()
            self.executeDDL1(cur1)
            cur1.execute(
                "insert into %sbooze values ('Victoria Bitter')" % (self.table_prefix)
            )
            cur2.execute("select name from %sbooze" % self.table_prefix)
            booze = cur2.fetchall()
            self.assertEqual(len(booze), 1)
            self.assertEqual(len(booze[0]), 1)
            self.assertEqual(booze[0][0], "Victoria Bitter")
        finally:
            con.close()

    def test_description(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(
                cur.description,
                None,
                "cursor.description should be none after executing a "
                "statement that can return no rows (such as DDL)",
            )
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.assertEqual(
                len(cur.description), 1, "cursor.description describes too many columns"
            )
            self.assertEqual(
                len(cur.description[0]),
                7,
                "cursor.description[x] tuples must have 7 elements",
            )
            self.assertEqual(
                cur.description[0][0].lower(),
                "name",
                "cursor.description[x][0] must return column name",
            )
            self.assertEqual(
                cur.description[0][1],
                self.driver.STRING,
                "cursor.description[x][1] must return column type. Got %r"
                % cur.description[0][1],
            )

            # Make sure self.description gets reset
            self.executeDDL2(cur)
            self.assertEqual(
                cur.description,
                None,
                "cursor.description not being set to None when executing "
                "no-result statements (eg. DDL)",
            )
        finally:
            con.close()

    def test_rowcount(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertTrue(
                cur.rowcount in (-1, 0),  # Bug #543885
                "cursor.rowcount should be -1 or 0 after executing no-result "
                "statements",
            )
            cur.execute(
                "insert into %sbooze values ('Victoria Bitter')" % (self.table_prefix)
            )
            self.assertTrue(
                cur.rowcount in (-1, 1),
                "cursor.rowcount should == number or rows inserted, or "
                "set to -1 after executing an insert statement",
            )
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.assertTrue(
                cur.rowcount in (-1, 1),
                "cursor.rowcount should == number of rows returned, or "
                "set to -1 after executing a select statement",
            )
            self.executeDDL2(cur)
            self.assertEqual(
                cur.rowcount,
                -1,
                "cursor.rowcount not being reset to -1 after executing "
                "no-result statements",
            )
        finally:
            con.close()

    lower_func = "lower"

    def test_callproc(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if self.lower_func and hasattr(cur, "callproc"):
                r = cur.callproc(self.lower_func, ("FOO",))
                self.assertEqual(len(r), 1)
                self.assertEqual(r[0], "FOO")
                r = cur.fetchall()
                self.assertEqual(len(r), 1, "callproc produced no result set")
                self.assertEqual(len(r[0]), 1, "callproc produced invalid result set")
                self.assertEqual(r[0][0], "foo", "callproc produced invalid results")
        finally:
            con.close()

    def test_close(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

        # cursor.execute should raise an Error if called after connection
        # closed
        self.assertRaises(self.driver.Error, self.executeDDL1, cur)

        # connection.commit should raise an Error if called after connection'
        # closed.'
        self.assertRaises(self.driver.Error, con.commit)

        # connection.close should raise an Error if called more than once
        #!!! reasonable persons differ about the usefulness of this test and this feature !!!
        if TEST_FOR_NON_IDEMPOTENT_CLOSE:
            self.assertRaises(self.driver.Error, con.close)
        else:
            self.skipTest(
                "Non-idempotent close is considered a bad thing by some people."
            )

    def test_execute(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self._paraminsert(cur)
        finally:
            con.close()

    def _paraminsert(self, cur):
        self.executeDDL2(cur)
        cur.execute(
            "insert into %sbarflys values ('Victoria Bitter', 'thi%%s :may ca%%(u)se? troub:1e')"
            % (self.table_prefix)
        )
        self.assertTrue(cur.rowcount in (-1, 1))

        if self.driver.paramstyle == "qmark":
            cur.execute(
                "insert into %sbarflys values (?, 'thi%%s :may ca%%(u)se? troub:1e')"
                % self.table_prefix,
                ("Cooper's",),
            )
        elif self.driver.paramstyle == "numeric":
            cur.execute(
                "insert into %sbarflys values (:1, 'thi%%s :may ca%%(u)se? troub:1e')"
                % self.table_prefix,
                ("Cooper's",),
            )
        elif self.driver.paramstyle == "named":
            cur.execute(
                "insert into %sbarflys values (:beer, 'thi%%s :may ca%%(u)se? troub:1e')"
                % self.table_prefix,
                {"beer": "Cooper's"},
            )
        elif self.driver.paramstyle == "format":
            cur.execute(
                "insert into %sbarflys values (%%s, 'thi%%s :may ca%%(u)se? troub:1e')"
                % self.table_prefix,
                ("Cooper's",),
            )
        elif self.driver.paramstyle == "pyformat":
            cur.execute(
                "insert into %sbarflys values (%%(beer)s, 'thi%%s :may ca%%(u)se? troub:1e')"
                % self.table_prefix,
                {"beer": "Cooper's"},
            )
        else:
            self.fail("Invalid paramstyle")
        self.assertTrue(cur.rowcount in (-1, 1))

        cur.execute("select name, drink from %sbarflys" % self.table_prefix)
        res = cur.fetchall()
        self.assertEqual(len(res), 2, "cursor.fetchall returned too few rows")
        beers = [res[0][0], res[1][0]]
        beers.sort()
        self.assertEqual(
            beers[0],
            "Cooper's",
            "cursor.fetchall retrieved incorrect data, or data inserted incorrectly",
        )
        self.assertEqual(
            beers[1],
            "Victoria Bitter",
            "cursor.fetchall retrieved incorrect data, or data inserted incorrectly",
        )
        trouble = "thi%s :may ca%(u)se? troub:1e"
        self.assertEqual(
            res[0][1],
            trouble,
            "cursor.fetchall retrieved incorrect data, or data inserted "
            f"incorrectly. Got={res[0][1]!r}, Expected={trouble!r}",
        )
        self.assertEqual(
            res[1][1],
            trouble,
            "cursor.fetchall retrieved incorrect data, or data inserted "
            f"incorrectly. Got={res[1][1]!r}, Expected={trouble!r}",
        )

    def test_executemany(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            largs = [("Cooper's",), ("Boag's",)]
            margs = [{"beer": "Cooper's"}, {"beer": "Boag's"}]
            if self.driver.paramstyle == "qmark":
                cur.executemany(
                    "insert into %sbooze values (?)" % self.table_prefix, largs
                )
            elif self.driver.paramstyle == "numeric":
                cur.executemany(
                    "insert into %sbooze values (:1)" % self.table_prefix, largs
                )
            elif self.driver.paramstyle == "named":
                cur.executemany(
                    "insert into %sbooze values (:beer)" % self.table_prefix, margs
                )
            elif self.driver.paramstyle == "format":
                cur.executemany(
                    "insert into %sbooze values (%%s)" % self.table_prefix, largs
                )
            elif self.driver.paramstyle == "pyformat":
                cur.executemany(
                    "insert into %sbooze values (%%(beer)s)" % (self.table_prefix),
                    margs,
                )
            else:
                self.fail("Unknown paramstyle")
            self.assertTrue(
                cur.rowcount in (-1, 2),
                "insert using cursor.executemany set cursor.rowcount to "
                "incorrect value %r" % cur.rowcount,
            )
            cur.execute("select name from %sbooze" % self.table_prefix)
            res = cur.fetchall()
            self.assertEqual(
                len(res), 2, "cursor.fetchall retrieved incorrect number of rows"
            )
            beers = [res[0][0], res[1][0]]
            beers.sort()
            self.assertEqual(
                beers[0], "Boag's", 'incorrect data "%s" retrieved' % beers[0]
            )
            self.assertEqual(beers[1], "Cooper's", "incorrect data retrieved")
        finally:
            con.close()

    def test_fetchone(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchone should raise an Error if called before
            # executing a select-type query
            self.assertRaises(self.driver.Error, cur.fetchone)

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            self.executeDDL1(cur)
            self.assertRaises(self.driver.Error, cur.fetchone)

            cur.execute("select name from %sbooze" % self.table_prefix)
            self.assertEqual(
                cur.fetchone(),
                None,
                "cursor.fetchone should return None if a query retrieves no rows",
            )
            self.assertTrue(cur.rowcount in (-1, 0))

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            cur.execute(
                "insert into %sbooze values ('Victoria Bitter')" % (self.table_prefix)
            )
            self.assertRaises(self.driver.Error, cur.fetchone)

            cur.execute("select name from %sbooze" % self.table_prefix)
            r = cur.fetchone()
            self.assertEqual(
                len(r), 1, "cursor.fetchone should have retrieved a single row"
            )
            self.assertEqual(
                r[0], "Victoria Bitter", "cursor.fetchone retrieved incorrect data"
            )
            self.assertEqual(
                cur.fetchone(),
                None,
                "cursor.fetchone should return None if no more rows available",
            )
            self.assertTrue(cur.rowcount in (-1, 1))
        finally:
            con.close()

    samples = [
        "Carlton Cold",
        "Carlton Draft",
        "Mountain Goat",
        "Redback",
        "Victoria Bitter",
        "XXXX",
    ]

    def _populate(self):
        """Return a list of sql commands to setup the DB for the fetch
        tests.
        """
        populate = [
            "insert into %sbooze values ('%s')" % (self.table_prefix, s)
            for s in self.samples
        ]
        return populate

    def test_fetchmany(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchmany should raise an Error if called without
            # issuing a query
            self.assertRaises(self.driver.Error, cur.fetchmany, 4)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute("select name from %sbooze" % self.table_prefix)
            r = cur.fetchmany()
            self.assertEqual(
                len(r),
                1,
                "cursor.fetchmany retrieved incorrect number of rows, "
                "default of arraysize is one.",
            )
            cur.arraysize = 10
            r = cur.fetchmany(3)  # Should get 3 rows
            self.assertEqual(
                len(r), 3, "cursor.fetchmany retrieved incorrect number of rows"
            )
            r = cur.fetchmany(4)  # Should get 2 more
            self.assertEqual(
                len(r), 2, "cursor.fetchmany retrieved incorrect number of rows"
            )
            r = cur.fetchmany(4)  # Should be an empty sequence
            self.assertEqual(
                len(r),
                0,
                "cursor.fetchmany should return an empty sequence after "
                "results are exhausted",
            )
            self.assertTrue(cur.rowcount in (-1, 6))

            # Same as above, using cursor.arraysize
            cur.arraysize = 4
            cur.execute("select name from %sbooze" % self.table_prefix)
            r = cur.fetchmany()  # Should get 4 rows
            self.assertEqual(
                len(r), 4, "cursor.arraysize not being honoured by fetchmany"
            )
            r = cur.fetchmany()  # Should get 2 more
            self.assertEqual(len(r), 2)
            r = cur.fetchmany()  # Should be an empty sequence
            self.assertEqual(len(r), 0)
            self.assertTrue(cur.rowcount in (-1, 6))

            cur.arraysize = 6
            cur.execute("select name from %sbooze" % self.table_prefix)
            rows = cur.fetchmany()  # Should get all rows
            self.assertTrue(cur.rowcount in (-1, 6))
            self.assertEqual(len(rows), 6)
            self.assertEqual(len(rows), 6)
            rows = [r[0] for r in rows]
            rows.sort()

            # Make sure we get the right data back out
            for i in range(0, 6):
                self.assertEqual(
                    rows[i],
                    self.samples[i],
                    "incorrect data retrieved by cursor.fetchmany",
                )

            rows = cur.fetchmany()  # Should return an empty list
            self.assertEqual(
                len(rows),
                0,
                "cursor.fetchmany should return an empty sequence if "
                "called after the whole result set has been fetched",
            )
            self.assertTrue(cur.rowcount in (-1, 6))

            self.executeDDL2(cur)
            cur.execute("select name from %sbarflys" % self.table_prefix)
            r = cur.fetchmany()  # Should get empty sequence
            self.assertEqual(
                len(r),
                0,
                "cursor.fetchmany should return an empty sequence if "
                "query retrieved no rows",
            )
            self.assertTrue(cur.rowcount in (-1, 0))

        finally:
            con.close()

    def test_fetchall(self):
        con = self._connect()
        try:
            cur = con.cursor()
            # cursor.fetchall should raise an Error if called
            # without executing a query that may return rows (such
            # as a select)
            self.assertRaises(self.driver.Error, cur.fetchall)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            # cursor.fetchall should raise an Error if called
            # after executing a a statement that cannot return rows
            self.assertRaises(self.driver.Error, cur.fetchall)

            cur.execute("select name from %sbooze" % self.table_prefix)
            rows = cur.fetchall()
            self.assertTrue(cur.rowcount in (-1, len(self.samples)))
            self.assertEqual(
                len(rows),
                len(self.samples),
                "cursor.fetchall did not retrieve all rows",
            )
            rows = [r[0] for r in rows]
            rows.sort()
            for i in range(0, len(self.samples)):
                self.assertEqual(
                    rows[i], self.samples[i], "cursor.fetchall retrieved incorrect rows"
                )
            rows = cur.fetchall()
            self.assertEqual(
                len(rows),
                0,
                "cursor.fetchall should return an empty list if called "
                "after the whole result set has been fetched",
            )
            self.assertTrue(cur.rowcount in (-1, len(self.samples)))

            self.executeDDL2(cur)
            cur.execute("select name from %sbarflys" % self.table_prefix)
            rows = cur.fetchall()
            self.assertTrue(cur.rowcount in (-1, 0))
            self.assertEqual(
                len(rows),
                0,
                "cursor.fetchall should return an empty list if "
                "a select query returns no rows",
            )

        finally:
            con.close()

    def test_mixedfetch(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute("select name from %sbooze" % self.table_prefix)
            rows1 = cur.fetchone()
            rows23 = cur.fetchmany(2)
            rows4 = cur.fetchone()
            rows56 = cur.fetchall()
            self.assertTrue(cur.rowcount in (-1, 6))
            self.assertEqual(
                len(rows23), 2, "fetchmany returned incorrect number of rows"
            )
            self.assertEqual(
                len(rows56), 2, "fetchall returned incorrect number of rows"
            )

            rows = [rows1[0]]
            rows.extend([rows23[0][0], rows23[1][0]])
            rows.append(rows4[0])
            rows.extend([rows56[0][0], rows56[1][0]])
            rows.sort()
            for i in range(0, len(self.samples)):
                self.assertEqual(
                    rows[i], self.samples[i], "incorrect data retrieved or inserted"
                )
        finally:
            con.close()

    def help_nextset_setUp(self, cur):
        """Should create a procedure called deleteme
        that returns two result sets, first the
        number of rows in booze then "name from booze"
        """
        raise NotImplementedError("Helper not implemented")
        # sql="""
        #    create procedure deleteme as
        #    begin
        #        select count(*) from booze
        #        select name from booze
        #    end
        # """
        # cur.execute(sql)

    def help_nextset_tearDown(self, cur):
        "If cleaning up is needed after nextSetTest"
        raise NotImplementedError("Helper not implemented")
        # cur.execute("drop procedure deleteme")

    def test_nextset(self):
        raise NotImplementedError("Drivers need to override this test")

    def test_arraysize(self):
        # Not much here - rest of the tests for this are in test_fetchmany
        con = self._connect()
        try:
            cur = con.cursor()
            self.assertTrue(
                hasattr(cur, "arraysize"), "cursor.arraysize must be defined"
            )
        finally:
            con.close()

    def test_setinputsizes(self):
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setinputsizes((25,))
            self._paraminsert(cur)  # Make sure cursor still works
        finally:
            con.close()

    def test_setoutputsize_basic(self):
        # Basic test is to make sure setoutputsize doesn't blow up
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setoutputsize(1000)
            cur.setoutputsize(2000, 0)
            self._paraminsert(cur)  # Make sure the cursor still works
        finally:
            con.close()

    def test_setoutputsize(self):
        # Real test for setoutputsize is driver dependant
        raise NotImplementedError("Driver needed to override this test")

    def test_None(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            cur.execute("insert into %sbooze values (NULL)" % self.table_prefix)
            cur.execute("select name from %sbooze" % self.table_prefix)
            r = cur.fetchall()
            self.assertEqual(len(r), 1)
            self.assertEqual(len(r[0]), 1)
            self.assertEqual(r[0][0], None, "NULL value not returned as None")
        finally:
            con.close()

    def test_Date(self):
        d1 = self.driver.Date(2002, 12, 25)
        d2 = self.driver.DateFromTicks(time.mktime((2002, 12, 25, 0, 0, 0, 0, 0, 0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(d1),str(d2))

    def test_Time(self):
        t1 = self.driver.Time(13, 45, 30)
        t2 = self.driver.TimeFromTicks(time.mktime((2001, 1, 1, 13, 45, 30, 0, 0, 0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Timestamp(self):
        t1 = self.driver.Timestamp(2002, 12, 25, 13, 45, 30)
        t2 = self.driver.TimestampFromTicks(
            time.mktime((2002, 12, 25, 13, 45, 30, 0, 0, 0))
        )
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Binary(self):
        b = self.driver.Binary(b"Something")
        b = self.driver.Binary(b"")

    def test_STRING(self):
        self.assertTrue(hasattr(self.driver, "STRING"), "module.STRING must be defined")

    def test_BINARY(self):
        self.assertTrue(
            hasattr(self.driver, "BINARY"), "module.BINARY must be defined."
        )

    def test_NUMBER(self):
        self.assertTrue(
            hasattr(self.driver, "NUMBER"), "module.NUMBER must be defined."
        )

    def test_DATETIME(self):
        self.assertTrue(
            hasattr(self.driver, "DATETIME"), "module.DATETIME must be defined."
        )

    def test_ROWID(self):
        self.assertTrue(hasattr(self.driver, "ROWID"), "module.ROWID must be defined.")

# === NexusCore/openenv\Lib\site-packages\fontTools\pens\momentsPen.py ===
from fontTools.pens.basePen import BasePen, OpenContourError

try:
    import cython
except (AttributeError, ImportError):
    # if cython not installed, use mock module with no-op decorators and types
    from fontTools.misc import cython
COMPILED = cython.compiled


__all__ = ["MomentsPen"]


class MomentsPen(BasePen):

    def __init__(self, glyphset=None):
        BasePen.__init__(self, glyphset)

        self.area = 0
        self.momentX = 0
        self.momentY = 0
        self.momentXX = 0
        self.momentXY = 0
        self.momentYY = 0

    def _moveTo(self, p0):
        self._startPoint = p0

    def _closePath(self):
        p0 = self._getCurrentPoint()
        if p0 != self._startPoint:
            self._lineTo(self._startPoint)

    def _endPath(self):
        p0 = self._getCurrentPoint()
        if p0 != self._startPoint:
            raise OpenContourError("Glyph statistics is not defined on open contours.")

    @cython.locals(r0=cython.double)
    @cython.locals(r1=cython.double)
    @cython.locals(r2=cython.double)
    @cython.locals(r3=cython.double)
    @cython.locals(r4=cython.double)
    @cython.locals(r5=cython.double)
    @cython.locals(r6=cython.double)
    @cython.locals(r7=cython.double)
    @cython.locals(r8=cython.double)
    @cython.locals(r9=cython.double)
    @cython.locals(r10=cython.double)
    @cython.locals(r11=cython.double)
    @cython.locals(r12=cython.double)
    @cython.locals(x0=cython.double, y0=cython.double)
    @cython.locals(x1=cython.double, y1=cython.double)
    def _lineTo(self, p1):
        x0, y0 = self._getCurrentPoint()
        x1, y1 = p1

        r0 = x1 * y0
        r1 = x1 * y1
        r2 = x1**2
        r3 = r2 * y1
        r4 = y0 - y1
        r5 = r4 * x0
        r6 = x0**2
        r7 = 2 * y0
        r8 = y0**2
        r9 = y1**2
        r10 = x1**3
        r11 = y0**3
        r12 = y1**3

        self.area += -r0 / 2 - r1 / 2 + x0 * (y0 + y1) / 2
        self.momentX += -r2 * y0 / 6 - r3 / 3 - r5 * x1 / 6 + r6 * (r7 + y1) / 6
        self.momentY += (
            -r0 * y1 / 6 - r8 * x1 / 6 - r9 * x1 / 6 + x0 * (r8 + r9 + y0 * y1) / 6
        )
        self.momentXX += (
            -r10 * y0 / 12
            - r10 * y1 / 4
            - r2 * r5 / 12
            - r4 * r6 * x1 / 12
            + x0**3 * (3 * y0 + y1) / 12
        )
        self.momentXY += (
            -r2 * r8 / 24
            - r2 * r9 / 8
            - r3 * r7 / 24
            + r6 * (r7 * y1 + 3 * r8 + r9) / 24
            - x0 * x1 * (r8 - r9) / 12
        )
        self.momentYY += (
            -r0 * r9 / 12
            - r1 * r8 / 12
            - r11 * x1 / 12
            - r12 * x1 / 12
            + x0 * (r11 + r12 + r8 * y1 + r9 * y0) / 12
        )

    @cython.locals(r0=cython.double)
    @cython.locals(r1=cython.double)
    @cython.locals(r2=cython.double)
    @cython.locals(r3=cython.double)
    @cython.locals(r4=cython.double)
    @cython.locals(r5=cython.double)
    @cython.locals(r6=cython.double)
    @cython.locals(r7=cython.double)
    @cython.locals(r8=cython.double)
    @cython.locals(r9=cython.double)
    @cython.locals(r10=cython.double)
    @cython.locals(r11=cython.double)
    @cython.locals(r12=cython.double)
    @cython.locals(r13=cython.double)
    @cython.locals(r14=cython.double)
    @cython.locals(r15=cython.double)
    @cython.locals(r16=cython.double)
    @cython.locals(r17=cython.double)
    @cython.locals(r18=cython.double)
    @cython.locals(r19=cython.double)
    @cython.locals(r20=cython.double)
    @cython.locals(r21=cython.double)
    @cython.locals(r22=cython.double)
    @cython.locals(r23=cython.double)
    @cython.locals(r24=cython.double)
    @cython.locals(r25=cython.double)
    @cython.locals(r26=cython.double)
    @cython.locals(r27=cython.double)
    @cython.locals(r28=cython.double)
    @cython.locals(r29=cython.double)
    @cython.locals(r30=cython.double)
    @cython.locals(r31=cython.double)
    @cython.locals(r32=cython.double)
    @cython.locals(r33=cython.double)
    @cython.locals(r34=cython.double)
    @cython.locals(r35=cython.double)
    @cython.locals(r36=cython.double)
    @cython.locals(r37=cython.double)
    @cython.locals(r38=cython.double)
    @cython.locals(r39=cython.double)
    @cython.locals(r40=cython.double)
    @cython.locals(r41=cython.double)
    @cython.locals(r42=cython.double)
    @cython.locals(r43=cython.double)
    @cython.locals(r44=cython.double)
    @cython.locals(r45=cython.double)
    @cython.locals(r46=cython.double)
    @cython.locals(r47=cython.double)
    @cython.locals(r48=cython.double)
    @cython.locals(r49=cython.double)
    @cython.locals(r50=cython.double)
    @cython.locals(r51=cython.double)
    @cython.locals(r52=cython.double)
    @cython.locals(r53=cython.double)
    @cython.locals(x0=cython.double, y0=cython.double)
    @cython.locals(x1=cython.double, y1=cython.double)
    @cython.locals(x2=cython.double, y2=cython.double)
    def _qCurveToOne(self, p1, p2):
        x0, y0 = self._getCurrentPoint()
        x1, y1 = p1
        x2, y2 = p2

        r0 = 2 * y1
        r1 = r0 * x2
        r2 = x2 * y2
        r3 = 3 * r2
        r4 = 2 * x1
        r5 = 3 * y0
        r6 = x1**2
        r7 = x2**2
        r8 = 4 * y1
        r9 = 10 * y2
        r10 = 2 * y2
        r11 = r4 * x2
        r12 = x0**2
        r13 = 10 * y0
        r14 = r4 * y2
        r15 = x2 * y0
        r16 = 4 * x1
        r17 = r0 * x1 + r2
        r18 = r2 * r8
        r19 = y1**2
        r20 = 2 * r19
        r21 = y2**2
        r22 = r21 * x2
        r23 = 5 * r22
        r24 = y0**2
        r25 = y0 * y2
        r26 = 5 * r24
        r27 = x1**3
        r28 = x2**3
        r29 = 30 * y1
        r30 = 6 * y1
        r31 = 10 * r7 * x1
        r32 = 5 * y2
        r33 = 12 * r6
        r34 = 30 * x1
        r35 = x1 * y1
        r36 = r3 + 20 * r35
        r37 = 12 * x1
        r38 = 20 * r6
        r39 = 8 * r6 * y1
        r40 = r32 * r7
        r41 = 60 * y1
        r42 = 20 * r19
        r43 = 4 * r19
        r44 = 15 * r21
        r45 = 12 * x2
        r46 = 12 * y2
        r47 = 6 * x1
        r48 = 8 * r19 * x1 + r23
        r49 = 8 * y1**3
        r50 = y2**3
        r51 = y0**3
        r52 = 10 * y1
        r53 = 12 * y1

        self.area += (
            -r1 / 6
            - r3 / 6
            + x0 * (r0 + r5 + y2) / 6
            + x1 * y2 / 3
            - y0 * (r4 + x2) / 6
        )
        self.momentX += (
            -r11 * (-r10 + y1) / 30
            + r12 * (r13 + r8 + y2) / 30
            + r6 * y2 / 15
            - r7 * r8 / 30
            - r7 * r9 / 30
            + x0 * (r14 - r15 - r16 * y0 + r17) / 30
            - y0 * (r11 + 2 * r6 + r7) / 30
        )
        self.momentY += (
            -r18 / 30
            - r20 * x2 / 30
            - r23 / 30
            - r24 * (r16 + x2) / 30
            + x0 * (r0 * y2 + r20 + r21 + r25 + r26 + r8 * y0) / 30
            + x1 * y2 * (r10 + y1) / 15
            - y0 * (r1 + r17) / 30
        )
        self.momentXX += (
            r12 * (r1 - 5 * r15 - r34 * y0 + r36 + r9 * x1) / 420
            + 2 * r27 * y2 / 105
            - r28 * r29 / 420
            - r28 * y2 / 4
            - r31 * (r0 - 3 * y2) / 420
            - r6 * x2 * (r0 - r32) / 105
            + x0**3 * (r30 + 21 * y0 + y2) / 84
            - x0
            * (
                r0 * r7
                + r15 * r37
                - r2 * r37
                - r33 * y2
                + r38 * y0
                - r39
                - r40
                + r5 * r7
            )
            / 420
            - y0 * (8 * r27 + 5 * r28 + r31 + r33 * x2) / 420
        )
        self.momentXY += (
            r12 * (r13 * y2 + 3 * r21 + 105 * r24 + r41 * y0 + r42 + r46 * y1) / 840
            - r16 * x2 * (r43 - r44) / 840
            - r21 * r7 / 8
            - r24 * (r38 + r45 * x1 + 3 * r7) / 840
            - r41 * r7 * y2 / 840
            - r42 * r7 / 840
            + r6 * y2 * (r32 + r8) / 210
            + x0
            * (
                -r15 * r8
                + r16 * r25
                + r18
                + r21 * r47
                - r24 * r34
                - r26 * x2
                + r35 * r46
                + r48
            )
            / 420
            - y0 * (r16 * r2 + r30 * r7 + r35 * r45 + r39 + r40) / 420
        )
        self.momentYY += (
            -r2 * r42 / 420
            - r22 * r29 / 420
            - r24 * (r14 + r36 + r52 * x2) / 420
            - r49 * x2 / 420
            - r50 * x2 / 12
            - r51 * (r47 + x2) / 84
            + x0
            * (
                r19 * r46
                + r21 * r5
                + r21 * r52
                + r24 * r29
                + r25 * r53
                + r26 * y2
                + r42 * y0
                + r49
                + 5 * r50
                + 35 * r51
            )
            / 420
            + x1 * y2 * (r43 + r44 + r9 * y1) / 210
            - y0 * (r19 * r45 + r2 * r53 - r21 * r4 + r48) / 420
        )

    @cython.locals(r0=cython.double)
    @cython.locals(r1=cython.double)
    @cython.locals(r2=cython.double)
    @cython.locals(r3=cython.double)
    @cython.locals(r4=cython.double)
    @cython.locals(r5=cython.double)
    @cython.locals(r6=cython.double)
    @cython.locals(r7=cython.double)
    @cython.locals(r8=cython.double)
    @cython.locals(r9=cython.double)
    @cython.locals(r10=cython.double)
    @cython.locals(r11=cython.double)
    @cython.locals(r12=cython.double)
    @cython.locals(r13=cython.double)
    @cython.locals(r14=cython.double)
    @cython.locals(r15=cython.double)
    @cython.locals(r16=cython.double)
    @cython.locals(r17=cython.double)
    @cython.locals(r18=cython.double)
    @cython.locals(r19=cython.double)
    @cython.locals(r20=cython.double)
    @cython.locals(r21=cython.double)
    @cython.locals(r22=cython.double)
    @cython.locals(r23=cython.double)
    @cython.locals(r24=cython.double)
    @cython.locals(r25=cython.double)
    @cython.locals(r26=cython.double)
    @cython.locals(r27=cython.double)
    @cython.locals(r28=cython.double)
    @cython.locals(r29=cython.double)
    @cython.locals(r30=cython.double)
    @cython.locals(r31=cython.double)
    @cython.locals(r32=cython.double)
    @cython.locals(r33=cython.double)
    @cython.locals(r34=cython.double)
    @cython.locals(r35=cython.double)
    @cython.locals(r36=cython.double)
    @cython.locals(r37=cython.double)
    @cython.locals(r38=cython.double)
    @cython.locals(r39=cython.double)
    @cython.locals(r40=cython.double)
    @cython.locals(r41=cython.double)
    @cython.locals(r42=cython.double)
    @cython.locals(r43=cython.double)
    @cython.locals(r44=cython.double)
    @cython.locals(r45=cython.double)
    @cython.locals(r46=cython.double)
    @cython.locals(r47=cython.double)
    @cython.locals(r48=cython.double)
    @cython.locals(r49=cython.double)
    @cython.locals(r50=cython.double)
    @cython.locals(r51=cython.double)
    @cython.locals(r52=cython.double)
    @cython.locals(r53=cython.double)
    @cython.locals(r54=cython.double)
    @cython.locals(r55=cython.double)
    @cython.locals(r56=cython.double)
    @cython.locals(r57=cython.double)
    @cython.locals(r58=cython.double)
    @cython.locals(r59=cython.double)
    @cython.locals(r60=cython.double)
    @cython.locals(r61=cython.double)
    @cython.locals(r62=cython.double)
    @cython.locals(r63=cython.double)
    @cython.locals(r64=cython.double)
    @cython.locals(r65=cython.double)
    @cython.locals(r66=cython.double)
    @cython.locals(r67=cython.double)
    @cython.locals(r68=cython.double)
    @cython.locals(r69=cython.double)
    @cython.locals(r70=cython.double)
    @cython.locals(r71=cython.double)
    @cython.locals(r72=cython.double)
    @cython.locals(r73=cython.double)
    @cython.locals(r74=cython.double)
    @cython.locals(r75=cython.double)
    @cython.locals(r76=cython.double)
    @cython.locals(r77=cython.double)
    @cython.locals(r78=cython.double)
    @cython.locals(r79=cython.double)
    @cython.locals(r80=cython.double)
    @cython.locals(r81=cython.double)
    @cython.locals(r82=cython.double)
    @cython.locals(r83=cython.double)
    @cython.locals(r84=cython.double)
    @cython.locals(r85=cython.double)
    @cython.locals(r86=cython.double)
    @cython.locals(r87=cython.double)
    @cython.locals(r88=cython.double)
    @cython.locals(r89=cython.double)
    @cython.locals(r90=cython.double)
    @cython.locals(r91=cython.double)
    @cython.locals(r92=cython.double)
    @cython.locals(r93=cython.double)
    @cython.locals(r94=cython.double)
    @cython.locals(r95=cython.double)
    @cython.locals(r96=cython.double)
    @cython.locals(r97=cython.double)
    @cython.locals(r98=cython.double)
    @cython.locals(r99=cython.double)
    @cython.locals(r100=cython.double)
    @cython.locals(r101=cython.double)
    @cython.locals(r102=cython.double)
    @cython.locals(r103=cython.double)
    @cython.locals(r104=cython.double)
    @cython.locals(r105=cython.double)
    @cython.locals(r106=cython.double)
    @cython.locals(r107=cython.double)
    @cython.locals(r108=cython.double)
    @cython.locals(r109=cython.double)
    @cython.locals(r110=cython.double)
    @cython.locals(r111=cython.double)
    @cython.locals(r112=cython.double)
    @cython.locals(r113=cython.double)
    @cython.locals(r114=cython.double)
    @cython.locals(r115=cython.double)
    @cython.locals(r116=cython.double)
    @cython.locals(r117=cython.double)
    @cython.locals(r118=cython.double)
    @cython.locals(r119=cython.double)
    @cython.locals(r120=cython.double)
    @cython.locals(r121=cython.double)
    @cython.locals(r122=cython.double)
    @cython.locals(r123=cython.double)
    @cython.locals(r124=cython.double)
    @cython.locals(r125=cython.double)
    @cython.locals(r126=cython.double)
    @cython.locals(r127=cython.double)
    @cython.locals(r128=cython.double)
    @cython.locals(r129=cython.double)
    @cython.locals(r130=cython.double)
    @cython.locals(r131=cython.double)
    @cython.locals(r132=cython.double)
    @cython.locals(x0=cython.double, y0=cython.double)
    @cython.locals(x1=cython.double, y1=cython.double)
    @cython.locals(x2=cython.double, y2=cython.double)
    @cython.locals(x3=cython.double, y3=cython.double)
    def _curveToOne(self, p1, p2, p3):
        x0, y0 = self._getCurrentPoint()
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3

        r0 = 6 * y2
        r1 = r0 * x3
        r2 = 10 * y3
        r3 = r2 * x3
        r4 = 3 * y1
        r5 = 6 * x1
        r6 = 3 * x2
        r7 = 6 * y1
        r8 = 3 * y2
        r9 = x2**2
        r10 = 45 * r9
        r11 = r10 * y3
        r12 = x3**2
        r13 = r12 * y2
        r14 = r12 * y3
        r15 = 7 * y3
        r16 = 15 * x3
        r17 = r16 * x2
        r18 = x1**2
        r19 = 9 * r18
        r20 = x0**2
        r21 = 21 * y1
        r22 = 9 * r9
        r23 = r7 * x3
        r24 = 9 * y2
        r25 = r24 * x2 + r3
        r26 = 9 * x2
        r27 = x2 * y3
        r28 = -r26 * y1 + 15 * r27
        r29 = 3 * x1
        r30 = 45 * x1
        r31 = 12 * x3
        r32 = 45 * r18
        r33 = 5 * r12
        r34 = r8 * x3
        r35 = 105 * y0
        r36 = 30 * y0
        r37 = r36 * x2
        r38 = 5 * x3
        r39 = 15 * y3
        r40 = 5 * y3
        r41 = r40 * x3
        r42 = x2 * y2
        r43 = 18 * r42
        r44 = 45 * y1
        r45 = r41 + r43 + r44 * x1
        r46 = y2 * y3
        r47 = r46 * x3
        r48 = y2**2
        r49 = 45 * r48
        r50 = r49 * x3
        r51 = y3**2
        r52 = r51 * x3
        r53 = y1**2
        r54 = 9 * r53
        r55 = y0**2
        r56 = 21 * x1
        r57 = 6 * x2
        r58 = r16 * y2
        r59 = r39 * y2
        r60 = 9 * r48
        r61 = r6 * y3
        r62 = 3 * y3
        r63 = r36 * y2
        r64 = y1 * y3
        r65 = 45 * r53
        r66 = 5 * r51
        r67 = x2**3
        r68 = x3**3
        r69 = 630 * y2
        r70 = 126 * x3
        r71 = x1**3
        r72 = 126 * x2
        r73 = 63 * r9
        r74 = r73 * x3
        r75 = r15 * x3 + 15 * r42
        r76 = 630 * x1
        r77 = 14 * x3
        r78 = 21 * r27
        r79 = 42 * x1
        r80 = 42 * x2
        r81 = x1 * y2
        r82 = 63 * r42
        r83 = x1 * y1
        r84 = r41 + r82 + 378 * r83
        r85 = x2 * x3
        r86 = r85 * y1
        r87 = r27 * x3
        r88 = 27 * r9
        r89 = r88 * y2
        r90 = 42 * r14
        r91 = 90 * x1
        r92 = 189 * r18
        r93 = 378 * r18
        r94 = r12 * y1
        r95 = 252 * x1 * x2
        r96 = r79 * x3
        r97 = 30 * r85
        r98 = r83 * x3
        r99 = 30 * x3
        r100 = 42 * x3
        r101 = r42 * x1
        r102 = r10 * y2 + 14 * r14 + 126 * r18 * y1 + r81 * r99
        r103 = 378 * r48
        r104 = 18 * y1
        r105 = r104 * y2
        r106 = y0 * y1
        r107 = 252 * y2
        r108 = r107 * y0
        r109 = y0 * y3
        r110 = 42 * r64
        r111 = 378 * r53
        r112 = 63 * r48
        r113 = 27 * x2
        r114 = r27 * y2
        r115 = r113 * r48 + 42 * r52
        r116 = x3 * y3
        r117 = 54 * r42
        r118 = r51 * x1
        r119 = r51 * x2
        r120 = r48 * x1
        r121 = 21 * x3
        r122 = r64 * x1
        r123 = r81 * y3
        r124 = 30 * r27 * y1 + r49 * x2 + 14 * r52 + 126 * r53 * x1
        r125 = y2**3
        r126 = y3**3
        r127 = y1**3
        r128 = y0**3
        r129 = r51 * y2
        r130 = r112 * y3 + r21 * r51
        r131 = 189 * r53
        r132 = 90 * y2

        self.area += (
            -r1 / 20
            - r3 / 20
            - r4 * (x2 + x3) / 20
            + x0 * (r7 + r8 + 10 * y0 + y3) / 20
            + 3 * x1 * (y2 + y3) / 20
            + 3 * x2 * y3 / 10
            - y0 * (r5 + r6 + x3) / 20
        )
        self.momentX += (
            r11 / 840
            - r13 / 8
            - r14 / 3
            - r17 * (-r15 + r8) / 840
            + r19 * (r8 + 2 * y3) / 840
            + r20 * (r0 + r21 + 56 * y0 + y3) / 168
            + r29 * (-r23 + r25 + r28) / 840
            - r4 * (10 * r12 + r17 + r22) / 840
            + x0
            * (
                12 * r27
                + r30 * y2
                + r34
                - r35 * x1
                - r37
                - r38 * y0
                + r39 * x1
                - r4 * x3
                + r45
            )
            / 840
            - y0 * (r17 + r30 * x2 + r31 * x1 + r32 + r33 + 18 * r9) / 840
        )
        self.momentY += (
            -r4 * (r25 + r58) / 840
            - r47 / 8
            - r50 / 840
            - r52 / 6
            - r54 * (r6 + 2 * x3) / 840
            - r55 * (r56 + r57 + x3) / 168
            + x0
            * (
                r35 * y1
                + r40 * y0
                + r44 * y2
                + 18 * r48
                + 140 * r55
                + r59
                + r63
                + 12 * r64
                + r65
                + r66
            )
            / 840
            + x1 * (r24 * y1 + 10 * r51 + r59 + r60 + r7 * y3) / 280
            + x2 * y3 * (r15 + r8) / 56
            - y0 * (r16 * y1 + r31 * y2 + r44 * x2 + r45 + r61 - r62 * x1) / 840
        )
        self.momentXX += (
            -r12 * r72 * (-r40 + r8) / 9240
            + 3 * r18 * (r28 + r34 - r38 * y1 + r75) / 3080
            + r20
            * (
                r24 * x3
                - r72 * y0
                - r76 * y0
                - r77 * y0
                + r78
                + r79 * y3
                + r80 * y1
                + 210 * r81
                + r84
            )
            / 9240
            - r29
            * (
                r12 * r21
                + 14 * r13
                + r44 * r9
                - r73 * y3
                + 54 * r86
                - 84 * r87
                - r89
                - r90
            )
            / 9240
            - r4 * (70 * r12 * x2 + 27 * r67 + 42 * r68 + r74) / 9240
            + 3 * r67 * y3 / 220
            - r68 * r69 / 9240
            - r68 * y3 / 4
            - r70 * r9 * (-r62 + y2) / 9240
            + 3 * r71 * (r24 + r40) / 3080
            + x0**3 * (r24 + r44 + 165 * y0 + y3) / 660
            + x0
            * (
                r100 * r27
                + 162 * r101
                + r102
                + r11
                + 63 * r18 * y3
                + r27 * r91
                - r33 * y0
                - r37 * x3
                + r43 * x3
                - r73 * y0
                - r88 * y1
                + r92 * y2
                - r93 * y0
                - 9 * r94
                - r95 * y0
                - r96 * y0
                - r97 * y1
                - 18 * r98
                + r99 * x1 * y3
            )
            / 9240
            - y0
            * (
                r12 * r56
                + r12 * r80
                + r32 * x3
                + 45 * r67
                + 14 * r68
                + 126 * r71
                + r74
                + r85 * r91
                + 135 * r9 * x1
                + r92 * x2
            )
            / 9240
        )
        self.momentXY += (
            -r103 * r12 / 18480
            - r12 * r51 / 8
            - 3 * r14 * y2 / 44
            + 3 * r18 * (r105 + r2 * y1 + 18 * r46 + 15 * r48 + 7 * r51) / 6160
            + r20
            * (
                1260 * r106
                + r107 * y1
                + r108
                + 28 * r109
                + r110
                + r111
                + r112
                + 30 * r46
                + 2310 * r55
                + r66
            )
            / 18480
            - r54 * (7 * r12 + 18 * r85 + 15 * r9) / 18480
            - r55 * (r33 + r73 + r93 + r95 + r96 + r97) / 18480
            - r7 * (42 * r13 + r82 * x3 + 28 * r87 + r89 + r90) / 18480
            - 3 * r85 * (r48 - r66) / 220
            + 3 * r9 * y3 * (r62 + 2 * y2) / 440
            + x0
            * (
                -r1 * y0
                - 84 * r106 * x2
                + r109 * r56
                + 54 * r114
                + r117 * y1
                + 15 * r118
                + 21 * r119
                + 81 * r120
                + r121 * r46
                + 54 * r122
                + 60 * r123
                + r124
                - r21 * x3 * y0
                + r23 * y3
                - r54 * x3
                - r55 * r72
                - r55 * r76
                - r55 * r77
                + r57 * y0 * y3
                + r60 * x3
                + 84 * r81 * y0
                + 189 * r81 * y1
            )
            / 9240
            + x1
            * (
                r104 * r27
                - r105 * x3
                - r113 * r53
                + 63 * r114
                + r115
                - r16 * r53
                + 28 * r47
                + r51 * r80
            )
            / 3080
            - y0
            * (
                54 * r101
                + r102
                + r116 * r5
                + r117 * x3
                + 21 * r13
                - r19 * y3
                + r22 * y3
                + r78 * x3
                + 189 * r83 * x2
                + 60 * r86
                + 81 * r9 * y1
                + 15 * r94
                + 54 * r98
            )
            / 9240
        )
        self.momentYY += (
            -r103 * r116 / 9240
            - r125 * r70 / 9240
            - r126 * x3 / 12
            - 3 * r127 * (r26 + r38) / 3080
            - r128 * (r26 + r30 + x3) / 660
            - r4 * (r112 * x3 + r115 - 14 * r119 + 84 * r47) / 9240
            - r52 * r69 / 9240
            - r54 * (r58 + r61 + r75) / 9240
            - r55
            * (r100 * y1 + r121 * y2 + r26 * y3 + r79 * y2 + r84 + 210 * x2 * y1)
            / 9240
            + x0
            * (
                r108 * y1
                + r110 * y0
                + r111 * y0
                + r112 * y0
                + 45 * r125
                + 14 * r126
                + 126 * r127
                + 770 * r128
                + 42 * r129
                + r130
                + r131 * y2
                + r132 * r64
                + 135 * r48 * y1
                + 630 * r55 * y1
                + 126 * r55 * y2
                + 14 * r55 * y3
                + r63 * y3
                + r65 * y3
                + r66 * y0
            )
            / 9240
            + x1
            * (
                27 * r125
                + 42 * r126
                + 70 * r129
                + r130
                + r39 * r53
                + r44 * r48
                + 27 * r53 * y2
                + 54 * r64 * y2
            )
            / 3080
            + 3 * x2 * y3 * (r48 + r66 + r8 * y3) / 220
            - y0
            * (
                r100 * r46
                + 18 * r114
                - 9 * r118
                - 27 * r120
                - 18 * r122
                - 30 * r123
                + r124
                + r131 * x2
                + r132 * x3 * y1
                + 162 * r42 * y1
                + r50
                + 63 * r53 * x3
                + r64 * r99
            )
            / 9240
        )


if __name__ == "__main__":
    from fontTools.misc.symfont import x, y, printGreenPen

    printGreenPen(
        "MomentsPen",
        [
            ("area", 1),
            ("momentX", x),
            ("momentY", y),
            ("momentXX", x**2),
            ("momentXY", x * y),
            ("momentYY", y**2),
        ],
    )

# === NexusCore/openenv\Lib\site-packages\jedi\plugins\stdlib.py ===
"""
Implementations of standard library functions, because it's not possible to
understand them with Jedi.

To add a new implementation, create a function and add it to the
``_implemented`` dict at the bottom of this module.

Note that this module exists only to implement very specific functionality in
the standard library. The usual way to understand the standard library is the
compiled module that returns the types for C-builtins.
"""
import parso
import os
from inspect import Parameter

from jedi import debug
from jedi.inference.utils import safe_property
from jedi.inference.helpers import get_str_or_none
from jedi.inference.arguments import iterate_argument_clinic, ParamIssue, \
    repack_with_argument_clinic, AbstractArguments, TreeArgumentsWrapper
from jedi.inference import analysis
from jedi.inference import compiled
from jedi.inference.value.instance import \
    AnonymousMethodExecutionContext, MethodExecutionContext
from jedi.inference.base_value import ContextualizedNode, \
    NO_VALUES, ValueSet, ValueWrapper, LazyValueWrapper
from jedi.inference.value import ClassValue, ModuleValue
from jedi.inference.value.klass import ClassMixin
from jedi.inference.value.function import FunctionMixin
from jedi.inference.value import iterable
from jedi.inference.lazy_value import LazyTreeValue, LazyKnownValue, \
    LazyKnownValues
from jedi.inference.names import ValueName, BaseTreeParamName
from jedi.inference.filters import AttributeOverwrite, publish_method, \
    ParserTreeFilter, DictFilter
from jedi.inference.signature import AbstractSignature, SignatureWrapper


# Copied from Python 3.6's stdlib.
_NAMEDTUPLE_CLASS_TEMPLATE = """\
_property = property
_tuple = tuple
from operator import itemgetter as _itemgetter
from collections import OrderedDict

class {typename}(tuple):
    __slots__ = ()

    _fields = {field_names!r}

    def __new__(_cls, {arg_list}):
        'Create new instance of {typename}({arg_list})'
        return _tuple.__new__(_cls, ({arg_list}))

    @classmethod
    def _make(cls, iterable, new=tuple.__new__, len=len):
        'Make a new {typename} object from a sequence or iterable'
        result = new(cls, iterable)
        if len(result) != {num_fields:d}:
            raise TypeError('Expected {num_fields:d} arguments, got %d' % len(result))
        return result

    def _replace(_self, **kwds):
        'Return a new {typename} object replacing specified fields with new values'
        result = _self._make(map(kwds.pop, {field_names!r}, _self))
        if kwds:
            raise ValueError('Got unexpected field names: %r' % list(kwds))
        return result

    def __repr__(self):
        'Return a nicely formatted representation string'
        return self.__class__.__name__ + '({repr_fmt})' % self

    def _asdict(self):
        'Return a new OrderedDict which maps field names to their values.'
        return OrderedDict(zip(self._fields, self))

    def __getnewargs__(self):
        'Return self as a plain tuple.  Used by copy and pickle.'
        return tuple(self)

    # These methods were added by Jedi.
    # __new__ doesn't really work with Jedi. So adding this to nametuples seems
    # like the easiest way.
    def __init__(self, {arg_list}):
        'A helper function for namedtuple.'
        self.__iterable = ({arg_list})

    def __iter__(self):
        for i in self.__iterable:
            yield i

    def __getitem__(self, y):
        return self.__iterable[y]

{field_defs}
"""

_NAMEDTUPLE_FIELD_TEMPLATE = '''\
    {name} = _property(_itemgetter({index:d}), doc='Alias for field number {index:d}')
'''


def execute(callback):
    def wrapper(value, arguments):
        def call():
            return callback(value, arguments=arguments)

        try:
            obj_name = value.name.string_name
        except AttributeError:
            pass
        else:
            p = value.parent_context
            if p is not None and p.is_builtins_module():
                module_name = 'builtins'
            elif p is not None and p.is_module():
                module_name = p.py__name__()
            else:
                return call()

            if value.is_bound_method() or value.is_instance():
                # value can be an instance for example if it is a partial
                # object.
                return call()

            # for now we just support builtin functions.
            try:
                func = _implemented[module_name][obj_name]
            except KeyError:
                pass
            else:
                return func(value, arguments=arguments, callback=call)
        return call()

    return wrapper


def _follow_param(inference_state, arguments, index):
    try:
        key, lazy_value = list(arguments.unpack())[index]
    except IndexError:
        return NO_VALUES
    else:
        return lazy_value.infer()


def argument_clinic(clinic_string, want_value=False, want_context=False,
                    want_arguments=False, want_inference_state=False,
                    want_callback=False):
    """
    Works like Argument Clinic (PEP 436), to validate function params.
    """

    def f(func):
        def wrapper(value, arguments, callback):
            try:
                args = tuple(iterate_argument_clinic(
                    value.inference_state, arguments, clinic_string))
            except ParamIssue:
                return NO_VALUES

            debug.dbg('builtin start %s' % value, color='MAGENTA')
            kwargs = {}
            if want_context:
                kwargs['context'] = arguments.context
            if want_value:
                kwargs['value'] = value
            if want_inference_state:
                kwargs['inference_state'] = value.inference_state
            if want_arguments:
                kwargs['arguments'] = arguments
            if want_callback:
                kwargs['callback'] = callback
            result = func(*args, **kwargs)
            debug.dbg('builtin end: %s', result, color='MAGENTA')
            return result

        return wrapper
    return f


@argument_clinic('iterator[, default], /', want_inference_state=True)
def builtins_next(iterators, defaults, inference_state):
    # TODO theoretically we have to check here if something is an iterator.
    # That is probably done by checking if it's not a class.
    return defaults | iterators.py__getattribute__('__next__').execute_with_values()


@argument_clinic('iterator[, default], /')
def builtins_iter(iterators_or_callables, defaults):
    # TODO implement this if it's a callable.
    return iterators_or_callables.py__getattribute__('__iter__').execute_with_values()


@argument_clinic('object, name[, default], /')
def builtins_getattr(objects, names, defaults=None):
    # follow the first param
    for value in objects:
        for name in names:
            string = get_str_or_none(name)
            if string is None:
                debug.warning('getattr called without str')
                continue
            else:
                return value.py__getattribute__(string)
    return NO_VALUES


@argument_clinic('object[, bases, dict], /')
def builtins_type(objects, bases, dicts):
    if bases or dicts:
        # It's a type creation... maybe someday...
        return NO_VALUES
    else:
        return objects.py__class__()


class SuperInstance(LazyValueWrapper):
    """To be used like the object ``super`` returns."""
    def __init__(self, inference_state, instance):
        self.inference_state = inference_state
        self._instance = instance  # Corresponds to super().__self__

    def _get_bases(self):
        return self._instance.py__class__().py__bases__()

    def _get_wrapped_value(self):
        objs = self._get_bases()[0].infer().execute_with_values()
        if not objs:
            # This is just a fallback and will only be used, if it's not
            # possible to find a class
            return self._instance
        return next(iter(objs))

    def get_filters(self, origin_scope=None):
        for b in self._get_bases():
            for value in b.infer().execute_with_values():
                for f in value.get_filters():
                    yield f


@argument_clinic('[type[, value]], /', want_context=True)
def builtins_super(types, objects, context):
    instance = None
    if isinstance(context, AnonymousMethodExecutionContext):
        instance = context.instance
    elif isinstance(context, MethodExecutionContext):
        instance = context.instance
    if instance is None:
        return NO_VALUES
    return ValueSet({SuperInstance(instance.inference_state, instance)})


class ReversedObject(AttributeOverwrite):
    def __init__(self, reversed_obj, iter_list):
        super().__init__(reversed_obj)
        self._iter_list = iter_list

    def py__iter__(self, contextualized_node=None):
        return self._iter_list

    @publish_method('__next__')
    def _next(self, arguments):
        return ValueSet.from_sets(
            lazy_value.infer() for lazy_value in self._iter_list
        )


@argument_clinic('sequence, /', want_value=True, want_arguments=True)
def builtins_reversed(sequences, value, arguments):
    # While we could do without this variable (just by using sequences), we
    # want static analysis to work well. Therefore we need to generated the
    # values again.
    key, lazy_value = next(arguments.unpack())
    cn = None
    if isinstance(lazy_value, LazyTreeValue):
        cn = ContextualizedNode(lazy_value.context, lazy_value.data)
    ordered = list(sequences.iterate(cn))

    # Repack iterator values and then run it the normal way. This is
    # necessary, because `reversed` is a function and autocompletion
    # would fail in certain cases like `reversed(x).__iter__` if we
    # just returned the result directly.
    seq, = value.inference_state.typing_module.py__getattribute__('Iterator').execute_with_values()
    return ValueSet([ReversedObject(seq, list(reversed(ordered)))])


@argument_clinic('value, type, /', want_arguments=True, want_inference_state=True)
def builtins_isinstance(objects, types, arguments, inference_state):
    bool_results = set()
    for o in objects:
        cls = o.py__class__()
        try:
            cls.py__bases__
        except AttributeError:
            # This is temporary. Everything should have a class attribute in
            # Python?! Maybe we'll leave it here, because some numpy objects or
            # whatever might not.
            bool_results = set([True, False])
            break

        mro = list(cls.py__mro__())

        for cls_or_tup in types:
            if cls_or_tup.is_class():
                bool_results.add(cls_or_tup in mro)
            elif cls_or_tup.name.string_name == 'tuple' \
                    and cls_or_tup.get_root_context().is_builtins_module():
                # Check for tuples.
                classes = ValueSet.from_sets(
                    lazy_value.infer()
                    for lazy_value in cls_or_tup.iterate()
                )
                bool_results.add(any(cls in mro for cls in classes))
            else:
                _, lazy_value = list(arguments.unpack())[1]
                if isinstance(lazy_value, LazyTreeValue):
                    node = lazy_value.data
                    message = 'TypeError: isinstance() arg 2 must be a ' \
                              'class, type, or tuple of classes and types, ' \
                              'not %s.' % cls_or_tup
                    analysis.add(lazy_value.context, 'type-error-isinstance', node, message)

    return ValueSet(
        compiled.builtin_from_name(inference_state, str(b))
        for b in bool_results
    )


class StaticMethodObject(ValueWrapper):
    def py__get__(self, instance, class_value):
        return ValueSet([self._wrapped_value])


@argument_clinic('sequence, /')
def builtins_staticmethod(functions):
    return ValueSet(StaticMethodObject(f) for f in functions)


class ClassMethodObject(ValueWrapper):
    def __init__(self, class_method_obj, function):
        super().__init__(class_method_obj)
        self._function = function

    def py__get__(self, instance, class_value):
        return ValueSet([
            ClassMethodGet(__get__, class_value, self._function)
            for __get__ in self._wrapped_value.py__getattribute__('__get__')
        ])


class ClassMethodGet(ValueWrapper):
    def __init__(self, get_method, klass, function):
        super().__init__(get_method)
        self._class = klass
        self._function = function

    def get_signatures(self):
        return [sig.bind(self._function) for sig in self._function.get_signatures()]

    def py__call__(self, arguments):
        return self._function.execute(ClassMethodArguments(self._class, arguments))


class ClassMethodArguments(TreeArgumentsWrapper):
    def __init__(self, klass, arguments):
        super().__init__(arguments)
        self._class = klass

    def unpack(self, func=None):
        yield None, LazyKnownValue(self._class)
        for values in self._wrapped_arguments.unpack(func):
            yield values


@argument_clinic('sequence, /', want_value=True, want_arguments=True)
def builtins_classmethod(functions, value, arguments):
    return ValueSet(
        ClassMethodObject(class_method_object, function)
        for class_method_object in value.py__call__(arguments=arguments)
        for function in functions
    )


class PropertyObject(AttributeOverwrite, ValueWrapper):
    api_type = 'property'

    def __init__(self, property_obj, function):
        super().__init__(property_obj)
        self._function = function

    def py__get__(self, instance, class_value):
        if instance is None:
            return ValueSet([self])
        return self._function.execute_with_values(instance)

    @publish_method('deleter')
    @publish_method('getter')
    @publish_method('setter')
    def _return_self(self, arguments):
        return ValueSet({self})


@argument_clinic('func, /', want_callback=True)
def builtins_property(functions, callback):
    return ValueSet(
        PropertyObject(property_value, function)
        for property_value in callback()
        for function in functions
    )


def collections_namedtuple(value, arguments, callback):
    """
    Implementation of the namedtuple function.

    This has to be done by processing the namedtuple class template and
    inferring the result.

    """
    inference_state = value.inference_state

    # Process arguments
    name = 'jedi_unknown_namedtuple'
    for c in _follow_param(inference_state, arguments, 0):
        x = get_str_or_none(c)
        if x is not None:
            name = x
            break

    # TODO here we only use one of the types, we should use all.
    param_values = _follow_param(inference_state, arguments, 1)
    if not param_values:
        return NO_VALUES
    _fields = list(param_values)[0]
    string = get_str_or_none(_fields)
    if string is not None:
        fields = string.replace(',', ' ').split()
    elif isinstance(_fields, iterable.Sequence):
        fields = [
            get_str_or_none(v)
            for lazy_value in _fields.py__iter__()
            for v in lazy_value.infer()
        ]
        fields = [f for f in fields if f is not None]
    else:
        return NO_VALUES

    # Build source code
    code = _NAMEDTUPLE_CLASS_TEMPLATE.format(
        typename=name,
        field_names=tuple(fields),
        num_fields=len(fields),
        arg_list=repr(tuple(fields)).replace("'", "")[1:-1],
        repr_fmt='',
        field_defs='\n'.join(_NAMEDTUPLE_FIELD_TEMPLATE.format(index=index, name=name)
                             for index, name in enumerate(fields))
    )

    # Parse source code
    module = inference_state.grammar.parse(code)
    generated_class = next(module.iter_classdefs())
    parent_context = ModuleValue(
        inference_state, module,
        code_lines=parso.split_lines(code, keepends=True),
    ).as_context()

    return ValueSet([ClassValue(inference_state, parent_context, generated_class)])


class PartialObject(ValueWrapper):
    def __init__(self, actual_value, arguments, instance=None):
        super().__init__(actual_value)
        self._arguments = arguments
        self._instance = instance

    def _get_functions(self, unpacked_arguments):
        key, lazy_value = next(unpacked_arguments, (None, None))
        if key is not None or lazy_value is None:
            debug.warning("Partial should have a proper function %s", self._arguments)
            return None
        return lazy_value.infer()

    def get_signatures(self):
        unpacked_arguments = self._arguments.unpack()
        funcs = self._get_functions(unpacked_arguments)
        if funcs is None:
            return []

        arg_count = 0
        if self._instance is not None:
            arg_count = 1
        keys = set()
        for key, _ in unpacked_arguments:
            if key is None:
                arg_count += 1
            else:
                keys.add(key)
        return [PartialSignature(s, arg_count, keys) for s in funcs.get_signatures()]

    def py__call__(self, arguments):
        funcs = self._get_functions(self._arguments.unpack())
        if funcs is None:
            return NO_VALUES

        return funcs.execute(
            MergedPartialArguments(self._arguments, arguments, self._instance)
        )

    def py__doc__(self):
        """
        In CPython partial does not replace the docstring. However we are still
        imitating it here, because we want this docstring to be worth something
        for the user.
        """
        callables = self._get_functions(self._arguments.unpack())
        if callables is None:
            return ''
        for callable_ in callables:
            return callable_.py__doc__()
        return ''

    def py__get__(self, instance, class_value):
        return ValueSet([self])


class PartialMethodObject(PartialObject):
    def py__get__(self, instance, class_value):
        if instance is None:
            return ValueSet([self])
        return ValueSet([PartialObject(self._wrapped_value, self._arguments, instance)])


class PartialSignature(SignatureWrapper):
    def __init__(self, wrapped_signature, skipped_arg_count, skipped_arg_set):
        super().__init__(wrapped_signature)
        self._skipped_arg_count = skipped_arg_count
        self._skipped_arg_set = skipped_arg_set

    def get_param_names(self, resolve_stars=False):
        names = self._wrapped_signature.get_param_names()[self._skipped_arg_count:]
        return [n for n in names if n.string_name not in self._skipped_arg_set]


class MergedPartialArguments(AbstractArguments):
    def __init__(self, partial_arguments, call_arguments, instance=None):
        self._partial_arguments = partial_arguments
        self._call_arguments = call_arguments
        self._instance = instance

    def unpack(self, funcdef=None):
        unpacked = self._partial_arguments.unpack(funcdef)
        # Ignore this one, it's the function. It was checked before that it's
        # there.
        next(unpacked, None)
        if self._instance is not None:
            yield None, LazyKnownValue(self._instance)
        for key_lazy_value in unpacked:
            yield key_lazy_value
        for key_lazy_value in self._call_arguments.unpack(funcdef):
            yield key_lazy_value


def functools_partial(value, arguments, callback):
    return ValueSet(
        PartialObject(instance, arguments)
        for instance in value.py__call__(arguments)
    )


def functools_partialmethod(value, arguments, callback):
    return ValueSet(
        PartialMethodObject(instance, arguments)
        for instance in value.py__call__(arguments)
    )


@argument_clinic('first, /')
def _return_first_param(firsts):
    return firsts


@argument_clinic('seq')
def _random_choice(sequences):
    return ValueSet.from_sets(
        lazy_value.infer()
        for sequence in sequences
        for lazy_value in sequence.py__iter__()
    )


def _dataclass(value, arguments, callback):
    for c in _follow_param(value.inference_state, arguments, 0):
        if c.is_class():
            return ValueSet([DataclassWrapper(c)])
        else:
            return ValueSet([value])
    return NO_VALUES


class DataclassWrapper(ValueWrapper, ClassMixin):
    def get_signatures(self):
        param_names = []
        for cls in reversed(list(self.py__mro__())):
            if isinstance(cls, DataclassWrapper):
                filter_ = cls.as_context().get_global_filter()
                # .values ordering is not guaranteed, at least not in
                # Python < 3.6, when dicts where not ordered, which is an
                # implementation detail anyway.
                for name in sorted(filter_.values(), key=lambda name: name.start_pos):
                    d = name.tree_name.get_definition()
                    annassign = d.children[1]
                    if d.type == 'expr_stmt' and annassign.type == 'annassign':
                        if len(annassign.children) < 4:
                            default = None
                        else:
                            default = annassign.children[3]
                        param_names.append(DataclassParamName(
                            parent_context=cls.parent_context,
                            tree_name=name.tree_name,
                            annotation_node=annassign.children[1],
                            default_node=default,
                        ))
        return [DataclassSignature(cls, param_names)]


class DataclassSignature(AbstractSignature):
    def __init__(self, value, param_names):
        super().__init__(value)
        self._param_names = param_names

    def get_param_names(self, resolve_stars=False):
        return self._param_names


class DataclassParamName(BaseTreeParamName):
    def __init__(self, parent_context, tree_name, annotation_node, default_node):
        super().__init__(parent_context, tree_name)
        self.annotation_node = annotation_node
        self.default_node = default_node

    def get_kind(self):
        return Parameter.POSITIONAL_OR_KEYWORD

    def infer(self):
        if self.annotation_node is None:
            return NO_VALUES
        else:
            return self.parent_context.infer_node(self.annotation_node)


class ItemGetterCallable(ValueWrapper):
    def __init__(self, instance, args_value_set):
        super().__init__(instance)
        self._args_value_set = args_value_set

    @repack_with_argument_clinic('item, /')
    def py__call__(self, item_value_set):
        value_set = NO_VALUES
        for args_value in self._args_value_set:
            lazy_values = list(args_value.py__iter__())
            if len(lazy_values) == 1:
                # TODO we need to add the contextualized value.
                value_set |= item_value_set.get_item(lazy_values[0].infer(), None)
            else:
                value_set |= ValueSet([iterable.FakeList(
                    self._wrapped_value.inference_state,
                    [
                        LazyKnownValues(item_value_set.get_item(lazy_value.infer(), None))
                        for lazy_value in lazy_values
                    ],
                )])
        return value_set


@argument_clinic('func, /')
def _functools_wraps(funcs):
    return ValueSet(WrapsCallable(func) for func in funcs)


class WrapsCallable(ValueWrapper):
    # XXX this is not the correct wrapped value, it should be a weird
    #     partials object, but it doesn't matter, because it's always used as a
    #     decorator anyway.
    @repack_with_argument_clinic('func, /')
    def py__call__(self, funcs):
        return ValueSet({Wrapped(func, self._wrapped_value) for func in funcs})


class Wrapped(ValueWrapper, FunctionMixin):
    def __init__(self, func, original_function):
        super().__init__(func)
        self._original_function = original_function

    @property
    def name(self):
        return self._original_function.name

    def get_signature_functions(self):
        return [self]


@argument_clinic('*args, /', want_value=True, want_arguments=True)
def _operator_itemgetter(args_value_set, value, arguments):
    return ValueSet([
        ItemGetterCallable(instance, args_value_set)
        for instance in value.py__call__(arguments)
    ])


def _create_string_input_function(func):
    @argument_clinic('string, /', want_value=True, want_arguments=True)
    def wrapper(strings, value, arguments):
        def iterate():
            for value in strings:
                s = get_str_or_none(value)
                if s is not None:
                    s = func(s)
                    yield compiled.create_simple_object(value.inference_state, s)
        values = ValueSet(iterate())
        if values:
            return values
        return value.py__call__(arguments)
    return wrapper


@argument_clinic('*args, /', want_callback=True)
def _os_path_join(args_set, callback):
    if len(args_set) == 1:
        string = ''
        sequence, = args_set
        is_first = True
        for lazy_value in sequence.py__iter__():
            string_values = lazy_value.infer()
            if len(string_values) != 1:
                break
            s = get_str_or_none(next(iter(string_values)))
            if s is None:
                break
            if not is_first:
                string += os.path.sep
            string += s
            is_first = False
        else:
            return ValueSet([compiled.create_simple_object(sequence.inference_state, string)])
    return callback()


_implemented = {
    'builtins': {
        'getattr': builtins_getattr,
        'type': builtins_type,
        'super': builtins_super,
        'reversed': builtins_reversed,
        'isinstance': builtins_isinstance,
        'next': builtins_next,
        'iter': builtins_iter,
        'staticmethod': builtins_staticmethod,
        'classmethod': builtins_classmethod,
        'property': builtins_property,
    },
    'copy': {
        'copy': _return_first_param,
        'deepcopy': _return_first_param,
    },
    'json': {
        'load': lambda value, arguments, callback: NO_VALUES,
        'loads': lambda value, arguments, callback: NO_VALUES,
    },
    'collections': {
        'namedtuple': collections_namedtuple,
    },
    'functools': {
        'partial': functools_partial,
        'partialmethod': functools_partialmethod,
        'wraps': _functools_wraps,
    },
    '_weakref': {
        'proxy': _return_first_param,
    },
    'random': {
        'choice': _random_choice,
    },
    'operator': {
        'itemgetter': _operator_itemgetter,
    },
    'abc': {
        # Not sure if this is necessary, but it's used a lot in typeshed and
        # it's for now easier to just pass the function.
        'abstractmethod': _return_first_param,
    },
    'typing': {
        # The _alias function just leads to some annoying type inference.
        # Therefore, just make it return nothing, which leads to the stubs
        # being used instead. This only matters for 3.7+.
        '_alias': lambda value, arguments, callback: NO_VALUES,
        # runtime_checkable doesn't really change anything and is just
        # adding logs for infering stuff, so we can safely ignore it.
        'runtime_checkable': lambda value, arguments, callback: NO_VALUES,
    },
    'dataclasses': {
        # For now this works at least better than Jedi trying to understand it.
        'dataclass': _dataclass
    },
    # attrs exposes declaration interface roughly compatible with dataclasses
    # via attrs.define, attrs.frozen and attrs.mutable
    # https://www.attrs.org/en/stable/names.html
    'attr': {
        'define': _dataclass,
        'frozen': _dataclass,
    },
    'attrs': {
        'define': _dataclass,
        'frozen': _dataclass,
    },
    'os.path': {
        'dirname': _create_string_input_function(os.path.dirname),
        'abspath': _create_string_input_function(os.path.abspath),
        'relpath': _create_string_input_function(os.path.relpath),
        'join': _os_path_join,
    }
}


def get_metaclass_filters(func):
    def wrapper(cls, metaclasses, is_instance):
        for metaclass in metaclasses:
            if metaclass.py__name__() == 'EnumMeta' \
                    and metaclass.get_root_context().py__name__() == 'enum':
                filter_ = ParserTreeFilter(parent_context=cls.as_context())
                return [DictFilter({
                    name.string_name: EnumInstance(cls, name).name
                    for name in filter_.values()
                })]
        return func(cls, metaclasses, is_instance)
    return wrapper


class EnumInstance(LazyValueWrapper):
    def __init__(self, cls, name):
        self.inference_state = cls.inference_state
        self._cls = cls  # Corresponds to super().__self__
        self._name = name
        self.tree_node = self._name.tree_name

    @safe_property
    def name(self):
        return ValueName(self, self._name.tree_name)

    def _get_wrapped_value(self):
        n = self._name.string_name
        if n.startswith('__') and n.endswith('__') or self._name.api_type == 'function':
            inferred = self._name.infer()
            if inferred:
                return next(iter(inferred))
            o, = self.inference_state.builtins_module.py__getattribute__('object')
            return o

        value, = self._cls.execute_with_values()
        return value

    def get_filters(self, origin_scope=None):
        yield DictFilter(dict(
            name=compiled.create_simple_object(self.inference_state, self._name.string_name).name,
            value=self._name,
        ))
        for f in self._get_wrapped_value().get_filters():
            yield f


def tree_name_to_values(func):
    def wrapper(inference_state, context, tree_name):
        if tree_name.value == 'sep' and context.is_module() and context.py__name__() == 'os.path':
            return ValueSet({
                compiled.create_simple_object(inference_state, os.path.sep),
            })
        return func(inference_state, context, tree_name)
    return wrapper

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\response.py ===
from __future__ import absolute_import

import io
import logging
import sys
import warnings
import zlib
from contextlib import contextmanager
from socket import error as SocketError
from socket import timeout as SocketTimeout

brotli = None

from . import util
from ._collections import HTTPHeaderDict
from .connection import BaseSSLError, HTTPException
from .exceptions import (
    BodyNotHttplibCompatible,
    DecodeError,
    HTTPError,
    IncompleteRead,
    InvalidChunkLength,
    InvalidHeader,
    ProtocolError,
    ReadTimeoutError,
    ResponseNotChunked,
    SSLError,
)
from .packages import six
from .util.response import is_fp_closed, is_response_to_head

log = logging.getLogger(__name__)


class DeflateDecoder(object):
    def __init__(self):
        self._first_try = True
        self._data = b""
        self._obj = zlib.decompressobj()

    def __getattr__(self, name):
        return getattr(self._obj, name)

    def decompress(self, data):
        if not data:
            return data

        if not self._first_try:
            return self._obj.decompress(data)

        self._data += data
        try:
            decompressed = self._obj.decompress(data)
            if decompressed:
                self._first_try = False
                self._data = None
            return decompressed
        except zlib.error:
            self._first_try = False
            self._obj = zlib.decompressobj(-zlib.MAX_WBITS)
            try:
                return self.decompress(self._data)
            finally:
                self._data = None


class GzipDecoderState(object):

    FIRST_MEMBER = 0
    OTHER_MEMBERS = 1
    SWALLOW_DATA = 2


class GzipDecoder(object):
    def __init__(self):
        self._obj = zlib.decompressobj(16 + zlib.MAX_WBITS)
        self._state = GzipDecoderState.FIRST_MEMBER

    def __getattr__(self, name):
        return getattr(self._obj, name)

    def decompress(self, data):
        ret = bytearray()
        if self._state == GzipDecoderState.SWALLOW_DATA or not data:
            return bytes(ret)
        while True:
            try:
                ret += self._obj.decompress(data)
            except zlib.error:
                previous_state = self._state
                # Ignore data after the first error
                self._state = GzipDecoderState.SWALLOW_DATA
                if previous_state == GzipDecoderState.OTHER_MEMBERS:
                    # Allow trailing garbage acceptable in other gzip clients
                    return bytes(ret)
                raise
            data = self._obj.unused_data
            if not data:
                return bytes(ret)
            self._state = GzipDecoderState.OTHER_MEMBERS
            self._obj = zlib.decompressobj(16 + zlib.MAX_WBITS)


if brotli is not None:

    class BrotliDecoder(object):
        # Supports both 'brotlipy' and 'Brotli' packages
        # since they share an import name. The top branches
        # are for 'brotlipy' and bottom branches for 'Brotli'
        def __init__(self):
            self._obj = brotli.Decompressor()
            if hasattr(self._obj, "decompress"):
                self.decompress = self._obj.decompress
            else:
                self.decompress = self._obj.process

        def flush(self):
            if hasattr(self._obj, "flush"):
                return self._obj.flush()
            return b""


class MultiDecoder(object):
    """
    From RFC7231:
        If one or more encodings have been applied to a representation, the
        sender that applied the encodings MUST generate a Content-Encoding
        header field that lists the content codings in the order in which
        they were applied.
    """

    def __init__(self, modes):
        self._decoders = [_get_decoder(m.strip()) for m in modes.split(",")]

    def flush(self):
        return self._decoders[0].flush()

    def decompress(self, data):
        for d in reversed(self._decoders):
            data = d.decompress(data)
        return data


def _get_decoder(mode):
    if "," in mode:
        return MultiDecoder(mode)

    if mode == "gzip":
        return GzipDecoder()

    if brotli is not None and mode == "br":
        return BrotliDecoder()

    return DeflateDecoder()


class HTTPResponse(io.IOBase):
    """
    HTTP Response container.

    Backwards-compatible with :class:`http.client.HTTPResponse` but the response ``body`` is
    loaded and decoded on-demand when the ``data`` property is accessed.  This
    class is also compatible with the Python standard library's :mod:`io`
    module, and can hence be treated as a readable object in the context of that
    framework.

    Extra parameters for behaviour not present in :class:`http.client.HTTPResponse`:

    :param preload_content:
        If True, the response's body will be preloaded during construction.

    :param decode_content:
        If True, will attempt to decode the body based on the
        'content-encoding' header.

    :param original_response:
        When this HTTPResponse wrapper is generated from an :class:`http.client.HTTPResponse`
        object, it's convenient to include the original for debug purposes. It's
        otherwise unused.

    :param retries:
        The retries contains the last :class:`~urllib3.util.retry.Retry` that
        was used during the request.

    :param enforce_content_length:
        Enforce content length checking. Body returned by server must match
        value of Content-Length header, if present. Otherwise, raise error.
    """

    CONTENT_DECODERS = ["gzip", "deflate"]
    if brotli is not None:
        CONTENT_DECODERS += ["br"]
    REDIRECT_STATUSES = [301, 302, 303, 307, 308]

    def __init__(
        self,
        body="",
        headers=None,
        status=0,
        version=0,
        reason=None,
        strict=0,
        preload_content=True,
        decode_content=True,
        original_response=None,
        pool=None,
        connection=None,
        msg=None,
        retries=None,
        enforce_content_length=False,
        request_method=None,
        request_url=None,
        auto_close=True,
    ):

        if isinstance(headers, HTTPHeaderDict):
            self.headers = headers
        else:
            self.headers = HTTPHeaderDict(headers)
        self.status = status
        self.version = version
        self.reason = reason
        self.strict = strict
        self.decode_content = decode_content
        self.retries = retries
        self.enforce_content_length = enforce_content_length
        self.auto_close = auto_close

        self._decoder = None
        self._body = None
        self._fp = None
        self._original_response = original_response
        self._fp_bytes_read = 0
        self.msg = msg
        self._request_url = request_url

        if body and isinstance(body, (six.string_types, bytes)):
            self._body = body

        self._pool = pool
        self._connection = connection

        if hasattr(body, "read"):
            self._fp = body

        # Are we using the chunked-style of transfer encoding?
        self.chunked = False
        self.chunk_left = None
        tr_enc = self.headers.get("transfer-encoding", "").lower()
        # Don't incur the penalty of creating a list and then discarding it
        encodings = (enc.strip() for enc in tr_enc.split(","))
        if "chunked" in encodings:
            self.chunked = True

        # Determine length of response
        self.length_remaining = self._init_length(request_method)

        # If requested, preload the body.
        if preload_content and not self._body:
            self._body = self.read(decode_content=decode_content)

    def get_redirect_location(self):
        """
        Should we redirect and where to?

        :returns: Truthy redirect location string if we got a redirect status
            code and valid location. ``None`` if redirect status and no
            location. ``False`` if not a redirect status code.
        """
        if self.status in self.REDIRECT_STATUSES:
            return self.headers.get("location")

        return False

    def release_conn(self):
        if not self._pool or not self._connection:
            return

        self._pool._put_conn(self._connection)
        self._connection = None

    def drain_conn(self):
        """
        Read and discard any remaining HTTP response data in the response connection.

        Unread data in the HTTPResponse connection blocks the connection from being released back to the pool.
        """
        try:
            self.read()
        except (HTTPError, SocketError, BaseSSLError, HTTPException):
            pass

    @property
    def data(self):
        # For backwards-compat with earlier urllib3 0.4 and earlier.
        if self._body:
            return self._body

        if self._fp:
            return self.read(cache_content=True)

    @property
    def connection(self):
        return self._connection

    def isclosed(self):
        return is_fp_closed(self._fp)

    def tell(self):
        """
        Obtain the number of bytes pulled over the wire so far. May differ from
        the amount of content returned by :meth:``urllib3.response.HTTPResponse.read``
        if bytes are encoded on the wire (e.g, compressed).
        """
        return self._fp_bytes_read

    def _init_length(self, request_method):
        """
        Set initial length value for Response content if available.
        """
        length = self.headers.get("content-length")

        if length is not None:
            if self.chunked:
                # This Response will fail with an IncompleteRead if it can't be
                # received as chunked. This method falls back to attempt reading
                # the response before raising an exception.
                log.warning(
                    "Received response with both Content-Length and "
                    "Transfer-Encoding set. This is expressly forbidden "
                    "by RFC 7230 sec 3.3.2. Ignoring Content-Length and "
                    "attempting to process response as Transfer-Encoding: "
                    "chunked."
                )
                return None

            try:
                # RFC 7230 section 3.3.2 specifies multiple content lengths can
                # be sent in a single Content-Length header
                # (e.g. Content-Length: 42, 42). This line ensures the values
                # are all valid ints and that as long as the `set` length is 1,
                # all values are the same. Otherwise, the header is invalid.
                lengths = set([int(val) for val in length.split(",")])
                if len(lengths) > 1:
                    raise InvalidHeader(
                        "Content-Length contained multiple "
                        "unmatching values (%s)" % length
                    )
                length = lengths.pop()
            except ValueError:
                length = None
            else:
                if length < 0:
                    length = None

        # Convert status to int for comparison
        # In some cases, httplib returns a status of "_UNKNOWN"
        try:
            status = int(self.status)
        except ValueError:
            status = 0

        # Check for responses that shouldn't include a body
        if status in (204, 304) or 100 <= status < 200 or request_method == "HEAD":
            length = 0

        return length

    def _init_decoder(self):
        """
        Set-up the _decoder attribute if necessary.
        """
        # Note: content-encoding value should be case-insensitive, per RFC 7230
        # Section 3.2
        content_encoding = self.headers.get("content-encoding", "").lower()
        if self._decoder is None:
            if content_encoding in self.CONTENT_DECODERS:
                self._decoder = _get_decoder(content_encoding)
            elif "," in content_encoding:
                encodings = [
                    e.strip()
                    for e in content_encoding.split(",")
                    if e.strip() in self.CONTENT_DECODERS
                ]
                if len(encodings):
                    self._decoder = _get_decoder(content_encoding)

    DECODER_ERROR_CLASSES = (IOError, zlib.error)
    if brotli is not None:
        DECODER_ERROR_CLASSES += (brotli.error,)

    def _decode(self, data, decode_content, flush_decoder):
        """
        Decode the data passed in and potentially flush the decoder.
        """
        if not decode_content:
            return data

        try:
            if self._decoder:
                data = self._decoder.decompress(data)
        except self.DECODER_ERROR_CLASSES as e:
            content_encoding = self.headers.get("content-encoding", "").lower()
            raise DecodeError(
                "Received response with content-encoding: %s, but "
                "failed to decode it." % content_encoding,
                e,
            )
        if flush_decoder:
            data += self._flush_decoder()

        return data

    def _flush_decoder(self):
        """
        Flushes the decoder. Should only be called if the decoder is actually
        being used.
        """
        if self._decoder:
            buf = self._decoder.decompress(b"")
            return buf + self._decoder.flush()

        return b""

    @contextmanager
    def _error_catcher(self):
        """
        Catch low-level python exceptions, instead re-raising urllib3
        variants, so that low-level exceptions are not leaked in the
        high-level api.

        On exit, release the connection back to the pool.
        """
        clean_exit = False

        try:
            try:
                yield

            except SocketTimeout:
                # FIXME: Ideally we'd like to include the url in the ReadTimeoutError but
                # there is yet no clean way to get at it from this context.
                raise ReadTimeoutError(self._pool, None, "Read timed out.")

            except BaseSSLError as e:
                # FIXME: Is there a better way to differentiate between SSLErrors?
                if "read operation timed out" not in str(e):
                    # SSL errors related to framing/MAC get wrapped and reraised here
                    raise SSLError(e)

                raise ReadTimeoutError(self._pool, None, "Read timed out.")

            except (HTTPException, SocketError) as e:
                # This includes IncompleteRead.
                raise ProtocolError("Connection broken: %r" % e, e)

            # If no exception is thrown, we should avoid cleaning up
            # unnecessarily.
            clean_exit = True
        finally:
            # If we didn't terminate cleanly, we need to throw away our
            # connection.
            if not clean_exit:
                # The response may not be closed but we're not going to use it
                # anymore so close it now to ensure that the connection is
                # released back to the pool.
                if self._original_response:
                    self._original_response.close()

                # Closing the response may not actually be sufficient to close
                # everything, so if we have a hold of the connection close that
                # too.
                if self._connection:
                    self._connection.close()

            # If we hold the original response but it's closed now, we should
            # return the connection back to the pool.
            if self._original_response and self._original_response.isclosed():
                self.release_conn()

    def _fp_read(self, amt):
        """
        Read a response with the thought that reading the number of bytes
        larger than can fit in a 32-bit int at a time via SSL in some
        known cases leads to an overflow error that has to be prevented
        if `amt` or `self.length_remaining` indicate that a problem may
        happen.

        The known cases:
          * 3.8 <= CPython < 3.9.7 because of a bug
            https://github.com/urllib3/urllib3/issues/2513#issuecomment-1152559900.
          * urllib3 injected with pyOpenSSL-backed SSL-support.
          * CPython < 3.10 only when `amt` does not fit 32-bit int.
        """
        assert self._fp
        c_int_max = 2 ** 31 - 1
        if (
            (
                (amt and amt > c_int_max)
                or (self.length_remaining and self.length_remaining > c_int_max)
            )
            and not util.IS_SECURETRANSPORT
            and (util.IS_PYOPENSSL or sys.version_info < (3, 10))
        ):
            buffer = io.BytesIO()
            # Besides `max_chunk_amt` being a maximum chunk size, it
            # affects memory overhead of reading a response by this
            # method in CPython.
            # `c_int_max` equal to 2 GiB - 1 byte is the actual maximum
            # chunk size that does not lead to an overflow error, but
            # 256 MiB is a compromise.
            max_chunk_amt = 2 ** 28
            while amt is None or amt != 0:
                if amt is not None:
                    chunk_amt = min(amt, max_chunk_amt)
                    amt -= chunk_amt
                else:
                    chunk_amt = max_chunk_amt
                data = self._fp.read(chunk_amt)
                if not data:
                    break
                buffer.write(data)
                del data  # to reduce peak memory usage by `max_chunk_amt`.
            return buffer.getvalue()
        else:
            # StringIO doesn't like amt=None
            return self._fp.read(amt) if amt is not None else self._fp.read()

    def read(self, amt=None, decode_content=None, cache_content=False):
        """
        Similar to :meth:`http.client.HTTPResponse.read`, but with two additional
        parameters: ``decode_content`` and ``cache_content``.

        :param amt:
            How much of the content to read. If specified, caching is skipped
            because it doesn't make sense to cache partial content as the full
            response.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.

        :param cache_content:
            If True, will save the returned data such that the same result is
            returned despite of the state of the underlying file object. This
            is useful if you want the ``.data`` property to continue working
            after having ``.read()`` the file object. (Overridden if ``amt`` is
            set.)
        """
        self._init_decoder()
        if decode_content is None:
            decode_content = self.decode_content

        if self._fp is None:
            return

        flush_decoder = False
        fp_closed = getattr(self._fp, "closed", False)

        with self._error_catcher():
            data = self._fp_read(amt) if not fp_closed else b""
            if amt is None:
                flush_decoder = True
            else:
                cache_content = False
                if (
                    amt != 0 and not data
                ):  # Platform-specific: Buggy versions of Python.
                    # Close the connection when no data is returned
                    #
                    # This is redundant to what httplib/http.client _should_
                    # already do.  However, versions of python released before
                    # December 15, 2012 (http://bugs.python.org/issue16298) do
                    # not properly close the connection in all cases. There is
                    # no harm in redundantly calling close.
                    self._fp.close()
                    flush_decoder = True
                    if self.enforce_content_length and self.length_remaining not in (
                        0,
                        None,
                    ):
                        # This is an edge case that httplib failed to cover due
                        # to concerns of backward compatibility. We're
                        # addressing it here to make sure IncompleteRead is
                        # raised during streaming, so all calls with incorrect
                        # Content-Length are caught.
                        raise IncompleteRead(self._fp_bytes_read, self.length_remaining)

        if data:
            self._fp_bytes_read += len(data)
            if self.length_remaining is not None:
                self.length_remaining -= len(data)

            data = self._decode(data, decode_content, flush_decoder)

            if cache_content:
                self._body = data

        return data

    def stream(self, amt=2 ** 16, decode_content=None):
        """
        A generator wrapper for the read() method. A call will block until
        ``amt`` bytes have been read from the connection or until the
        connection is closed.

        :param amt:
            How much of the content to read. The generator will return up to
            much data per iteration, but may return less. This is particularly
            likely when using compressed data. However, the empty string will
            never be returned.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.
        """
        if self.chunked and self.supports_chunked_reads():
            for line in self.read_chunked(amt, decode_content=decode_content):
                yield line
        else:
            while not is_fp_closed(self._fp):
                data = self.read(amt=amt, decode_content=decode_content)

                if data:
                    yield data

    @classmethod
    def from_httplib(ResponseCls, r, **response_kw):
        """
        Given an :class:`http.client.HTTPResponse` instance ``r``, return a
        corresponding :class:`urllib3.response.HTTPResponse` object.

        Remaining parameters are passed to the HTTPResponse constructor, along
        with ``original_response=r``.
        """
        headers = r.msg

        if not isinstance(headers, HTTPHeaderDict):
            if six.PY2:
                # Python 2.7
                headers = HTTPHeaderDict.from_httplib(headers)
            else:
                headers = HTTPHeaderDict(headers.items())

        # HTTPResponse objects in Python 3 don't have a .strict attribute
        strict = getattr(r, "strict", 0)
        resp = ResponseCls(
            body=r,
            headers=headers,
            status=r.status,
            version=r.version,
            reason=r.reason,
            strict=strict,
            original_response=r,
            **response_kw
        )
        return resp

    # Backwards-compatibility methods for http.client.HTTPResponse
    def getheaders(self):
        warnings.warn(
            "HTTPResponse.getheaders() is deprecated and will be removed "
            "in urllib3 v2.1.0. Instead access HTTPResponse.headers directly.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return self.headers

    def getheader(self, name, default=None):
        warnings.warn(
            "HTTPResponse.getheader() is deprecated and will be removed "
            "in urllib3 v2.1.0. Instead use HTTPResponse.headers.get(name, default).",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return self.headers.get(name, default)

    # Backwards compatibility for http.cookiejar
    def info(self):
        return self.headers

    # Overrides from io.IOBase
    def close(self):
        if not self.closed:
            self._fp.close()

        if self._connection:
            self._connection.close()

        if not self.auto_close:
            io.IOBase.close(self)

    @property
    def closed(self):
        if not self.auto_close:
            return io.IOBase.closed.__get__(self)
        elif self._fp is None:
            return True
        elif hasattr(self._fp, "isclosed"):
            return self._fp.isclosed()
        elif hasattr(self._fp, "closed"):
            return self._fp.closed
        else:
            return True

    def fileno(self):
        if self._fp is None:
            raise IOError("HTTPResponse has no file to get a fileno from")
        elif hasattr(self._fp, "fileno"):
            return self._fp.fileno()
        else:
            raise IOError(
                "The file-like object this HTTPResponse is wrapped "
                "around has no file descriptor"
            )

    def flush(self):
        if (
            self._fp is not None
            and hasattr(self._fp, "flush")
            and not getattr(self._fp, "closed", False)
        ):
            return self._fp.flush()

    def readable(self):
        # This method is required for `io` module compatibility.
        return True

    def readinto(self, b):
        # This method is required for `io` module compatibility.
        temp = self.read(len(b))
        if len(temp) == 0:
            return 0
        else:
            b[: len(temp)] = temp
            return len(temp)

    def supports_chunked_reads(self):
        """
        Checks if the underlying file-like object looks like a
        :class:`http.client.HTTPResponse` object. We do this by testing for
        the fp attribute. If it is present we assume it returns raw chunks as
        processed by read_chunked().
        """
        return hasattr(self._fp, "fp")

    def _update_chunk_length(self):
        # First, we'll figure out length of a chunk and then
        # we'll try to read it from socket.
        if self.chunk_left is not None:
            return
        line = self._fp.fp.readline()
        line = line.split(b";", 1)[0]
        try:
            self.chunk_left = int(line, 16)
        except ValueError:
            # Invalid chunked protocol response, abort.
            self.close()
            raise InvalidChunkLength(self, line)

    def _handle_chunk(self, amt):
        returned_chunk = None
        if amt is None:
            chunk = self._fp._safe_read(self.chunk_left)
            returned_chunk = chunk
            self._fp._safe_read(2)  # Toss the CRLF at the end of the chunk.
            self.chunk_left = None
        elif amt < self.chunk_left:
            value = self._fp._safe_read(amt)
            self.chunk_left = self.chunk_left - amt
            returned_chunk = value
        elif amt == self.chunk_left:
            value = self._fp._safe_read(amt)
            self._fp._safe_read(2)  # Toss the CRLF at the end of the chunk.
            self.chunk_left = None
            returned_chunk = value
        else:  # amt > self.chunk_left
            returned_chunk = self._fp._safe_read(self.chunk_left)
            self._fp._safe_read(2)  # Toss the CRLF at the end of the chunk.
            self.chunk_left = None
        return returned_chunk

    def read_chunked(self, amt=None, decode_content=None):
        """
        Similar to :meth:`HTTPResponse.read`, but with an additional
        parameter: ``decode_content``.

        :param amt:
            How much of the content to read. If specified, caching is skipped
            because it doesn't make sense to cache partial content as the full
            response.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.
        """
        self._init_decoder()
        # FIXME: Rewrite this method and make it a class with a better structured logic.
        if not self.chunked:
            raise ResponseNotChunked(
                "Response is not chunked. "
                "Header 'transfer-encoding: chunked' is missing."
            )
        if not self.supports_chunked_reads():
            raise BodyNotHttplibCompatible(
                "Body should be http.client.HTTPResponse like. "
                "It should have have an fp attribute which returns raw chunks."
            )

        with self._error_catcher():
            # Don't bother reading the body of a HEAD request.
            if self._original_response and is_response_to_head(self._original_response):
                self._original_response.close()
                return

            # If a response is already read and closed
            # then return immediately.
            if self._fp.fp is None:
                return

            while True:
                self._update_chunk_length()
                if self.chunk_left == 0:
                    break
                chunk = self._handle_chunk(amt)
                decoded = self._decode(
                    chunk, decode_content=decode_content, flush_decoder=False
                )
                if decoded:
                    yield decoded

            if decode_content:
                # On CPython and PyPy, we should never need to flush the
                # decoder. However, on Jython we *might* need to, so
                # lets defensively do it anyway.
                decoded = self._flush_decoder()
                if decoded:  # Platform-specific: Jython.
                    yield decoded

            # Chunk content ends with \r\n: discard it.
            while True:
                line = self._fp.fp.readline()
                if not line:
                    # Some sites may not end with '\r\n'.
                    break
                if line == b"\r\n":
                    break

            # We read everything; close the "file".
            if self._original_response:
                self._original_response.close()

    def geturl(self):
        """
        Returns the URL that was the source of this response.
        If the request that generated this response redirected, this method
        will return the final redirect location.
        """
        if self.retries is not None and len(self.retries.history):
            return self.retries.history[-1].redirect_location
        else:
            return self._request_url

    def __iter__(self):
        buffer = []
        for chunk in self.stream(decode_content=True):
            if b"\n" in chunk:
                chunk = chunk.split(b"\n")
                yield b"".join(buffer) + chunk[0] + b"\n"
                for x in chunk[1:-1]:
                    yield x + b"\n"
                if chunk[-1]:
                    buffer = [chunk[-1]]
                else:
                    buffer = []
            else:
                buffer.append(chunk)
        if buffer:
            yield b"".join(buffer)

# === NexusCore/openenv\Lib\site-packages\google\auth\jwt.py ===
# Copyright 2016 Google LLC
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

"""JSON Web Tokens

Provides support for creating (encoding) and verifying (decoding) JWTs,
especially JWTs generated and consumed by Google infrastructure.

See `rfc7519`_ for more details on JWTs.

To encode a JWT use :func:`encode`::

    from google.auth import crypt
    from google.auth import jwt

    signer = crypt.Signer(private_key)
    payload = {'some': 'payload'}
    encoded = jwt.encode(signer, payload)

To decode a JWT and verify claims use :func:`decode`::

    claims = jwt.decode(encoded, certs=public_certs)

You can also skip verification::

    claims = jwt.decode(encoded, verify=False)

.. _rfc7519: https://tools.ietf.org/html/rfc7519

"""

try:
    from collections.abc import Mapping
# Python 2.7 compatibility
except ImportError:  # pragma: NO COVER
    from collections import Mapping  # type: ignore
import copy
import datetime
import json
import urllib

import cachetools

from google.auth import _helpers
from google.auth import _service_account_info
from google.auth import crypt
from google.auth import exceptions
import google.auth.credentials

try:
    from google.auth.crypt import es256
except ImportError:  # pragma: NO COVER
    es256 = None  # type: ignore

_DEFAULT_TOKEN_LIFETIME_SECS = 3600  # 1 hour in seconds
_DEFAULT_MAX_CACHE_SIZE = 10
_ALGORITHM_TO_VERIFIER_CLASS = {"RS256": crypt.RSAVerifier}
_CRYPTOGRAPHY_BASED_ALGORITHMS = frozenset(["ES256"])

if es256 is not None:  # pragma: NO COVER
    _ALGORITHM_TO_VERIFIER_CLASS["ES256"] = es256.ES256Verifier  # type: ignore


def encode(signer, payload, header=None, key_id=None):
    """Make a signed JWT.

    Args:
        signer (google.auth.crypt.Signer): The signer used to sign the JWT.
        payload (Mapping[str, str]): The JWT payload.
        header (Mapping[str, str]): Additional JWT header payload.
        key_id (str): The key id to add to the JWT header. If the
            signer has a key id it will be used as the default. If this is
            specified it will override the signer's key id.

    Returns:
        bytes: The encoded JWT.
    """
    if header is None:
        header = {}

    if key_id is None:
        key_id = signer.key_id

    header.update({"typ": "JWT"})

    if "alg" not in header:
        if es256 is not None and isinstance(signer, es256.ES256Signer):
            header.update({"alg": "ES256"})
        else:
            header.update({"alg": "RS256"})

    if key_id is not None:
        header["kid"] = key_id

    segments = [
        _helpers.unpadded_urlsafe_b64encode(json.dumps(header).encode("utf-8")),
        _helpers.unpadded_urlsafe_b64encode(json.dumps(payload).encode("utf-8")),
    ]

    signing_input = b".".join(segments)
    signature = signer.sign(signing_input)
    segments.append(_helpers.unpadded_urlsafe_b64encode(signature))

    return b".".join(segments)


def _decode_jwt_segment(encoded_section):
    """Decodes a single JWT segment."""
    section_bytes = _helpers.padded_urlsafe_b64decode(encoded_section)
    try:
        return json.loads(section_bytes.decode("utf-8"))
    except ValueError as caught_exc:
        new_exc = exceptions.MalformedError(
            "Can't parse segment: {0}".format(section_bytes)
        )
        raise new_exc from caught_exc


def _unverified_decode(token):
    """Decodes a token and does no verification.

    Args:
        token (Union[str, bytes]): The encoded JWT.

    Returns:
        Tuple[Mapping, Mapping, str, str]: header, payload, signed_section, and
            signature.

    Raises:
        google.auth.exceptions.MalformedError: if there are an incorrect amount of segments in the token or segments of the wrong type.
    """
    token = _helpers.to_bytes(token)

    if token.count(b".") != 2:
        raise exceptions.MalformedError(
            "Wrong number of segments in token: {0}".format(token)
        )

    encoded_header, encoded_payload, signature = token.split(b".")
    signed_section = encoded_header + b"." + encoded_payload
    signature = _helpers.padded_urlsafe_b64decode(signature)

    # Parse segments
    header = _decode_jwt_segment(encoded_header)
    payload = _decode_jwt_segment(encoded_payload)

    if not isinstance(header, Mapping):
        raise exceptions.MalformedError(
            "Header segment should be a JSON object: {0}".format(encoded_header)
        )

    if not isinstance(payload, Mapping):
        raise exceptions.MalformedError(
            "Payload segment should be a JSON object: {0}".format(encoded_payload)
        )

    return header, payload, signed_section, signature


def decode_header(token):
    """Return the decoded header of a token.

    No verification is done. This is useful to extract the key id from
    the header in order to acquire the appropriate certificate to verify
    the token.

    Args:
        token (Union[str, bytes]): the encoded JWT.

    Returns:
        Mapping: The decoded JWT header.
    """
    header, _, _, _ = _unverified_decode(token)
    return header


def _verify_iat_and_exp(payload, clock_skew_in_seconds=0):
    """Verifies the ``iat`` (Issued At) and ``exp`` (Expires) claims in a token
    payload.

    Args:
        payload (Mapping[str, str]): The JWT payload.
        clock_skew_in_seconds (int): The clock skew used for `iat` and `exp`
            validation.

    Raises:
        google.auth.exceptions.InvalidValue: if value validation failed.
        google.auth.exceptions.MalformedError: if schema validation failed.
    """
    now = _helpers.datetime_to_secs(_helpers.utcnow())

    # Make sure the iat and exp claims are present.
    for key in ("iat", "exp"):
        if key not in payload:
            raise exceptions.MalformedError(
                "Token does not contain required claim {}".format(key)
            )

    # Make sure the token wasn't issued in the future.
    iat = payload["iat"]
    # Err on the side of accepting a token that is slightly early to account
    # for clock skew.
    earliest = iat - clock_skew_in_seconds
    if now < earliest:
        raise exceptions.InvalidValue(
            "Token used too early, {} < {}. Check that your computer's clock is set correctly.".format(
                now, iat
            )
        )

    # Make sure the token wasn't issued in the past.
    exp = payload["exp"]
    # Err on the side of accepting a token that is slightly out of date
    # to account for clow skew.
    latest = exp + clock_skew_in_seconds
    if latest < now:
        raise exceptions.InvalidValue("Token expired, {} < {}".format(latest, now))


def decode(token, certs=None, verify=True, audience=None, clock_skew_in_seconds=0):
    """Decode and verify a JWT.

    Args:
        token (str): The encoded JWT.
        certs (Union[str, bytes, Mapping[str, Union[str, bytes]]]): The
            certificate used to validate the JWT signature. If bytes or string,
            it must the the public key certificate in PEM format. If a mapping,
            it must be a mapping of key IDs to public key certificates in PEM
            format. The mapping must contain the same key ID that's specified
            in the token's header.
        verify (bool): Whether to perform signature and claim validation.
            Verification is done by default.
        audience (str or list): The audience claim, 'aud', that this JWT should
            contain. Or a list of audience claims. If None then the JWT's 'aud'
            parameter is not verified.
        clock_skew_in_seconds (int): The clock skew used for `iat` and `exp`
            validation.

    Returns:
        Mapping[str, str]: The deserialized JSON payload in the JWT.

    Raises:
        google.auth.exceptions.InvalidValue: if value validation failed.
        google.auth.exceptions.MalformedError: if schema validation failed.
    """
    header, payload, signed_section, signature = _unverified_decode(token)

    if not verify:
        return payload

    # Pluck the key id and algorithm from the header and make sure we have
    # a verifier that can support it.
    key_alg = header.get("alg")
    key_id = header.get("kid")

    try:
        verifier_cls = _ALGORITHM_TO_VERIFIER_CLASS[key_alg]
    except KeyError as exc:
        if key_alg in _CRYPTOGRAPHY_BASED_ALGORITHMS:
            raise exceptions.InvalidValue(
                "The key algorithm {} requires the cryptography package to be installed.".format(
                    key_alg
                )
            ) from exc
        else:
            raise exceptions.InvalidValue(
                "Unsupported signature algorithm {}".format(key_alg)
            ) from exc
    # If certs is specified as a dictionary of key IDs to certificates, then
    # use the certificate identified by the key ID in the token header.
    if isinstance(certs, Mapping):
        if key_id:
            if key_id not in certs:
                raise exceptions.MalformedError(
                    "Certificate for key id {} not found.".format(key_id)
                )
            certs_to_check = [certs[key_id]]
        # If there's no key id in the header, check against all of the certs.
        else:
            certs_to_check = certs.values()
    else:
        certs_to_check = certs

    # Verify that the signature matches the message.
    if not crypt.verify_signature(
        signed_section, signature, certs_to_check, verifier_cls
    ):
        raise exceptions.MalformedError("Could not verify token signature.")

    # Verify the issued at and created times in the payload.
    _verify_iat_and_exp(payload, clock_skew_in_seconds)

    # Check audience.
    if audience is not None:
        claim_audience = payload.get("aud")
        if isinstance(audience, str):
            audience = [audience]
        if claim_audience not in audience:
            raise exceptions.InvalidValue(
                "Token has wrong audience {}, expected one of {}".format(
                    claim_audience, audience
                )
            )

    return payload


class Credentials(
    google.auth.credentials.Signing, google.auth.credentials.CredentialsWithQuotaProject
):
    """Credentials that use a JWT as the bearer token.

    These credentials require an "audience" claim. This claim identifies the
    intended recipient of the bearer token.

    The constructor arguments determine the claims for the JWT that is
    sent with requests. Usually, you'll construct these credentials with
    one of the helper constructors as shown in the next section.

    To create JWT credentials using a Google service account private key
    JSON file::

        audience = 'https://pubsub.googleapis.com/google.pubsub.v1.Publisher'
        credentials = jwt.Credentials.from_service_account_file(
            'service-account.json',
            audience=audience)

    If you already have the service account file loaded and parsed::

        service_account_info = json.load(open('service_account.json'))
        credentials = jwt.Credentials.from_service_account_info(
            service_account_info,
            audience=audience)

    Both helper methods pass on arguments to the constructor, so you can
    specify the JWT claims::

        credentials = jwt.Credentials.from_service_account_file(
            'service-account.json',
            audience=audience,
            additional_claims={'meta': 'data'})

    You can also construct the credentials directly if you have a
    :class:`~google.auth.crypt.Signer` instance::

        credentials = jwt.Credentials(
            signer,
            issuer='your-issuer',
            subject='your-subject',
            audience=audience)

    The claims are considered immutable. If you want to modify the claims,
    you can easily create another instance using :meth:`with_claims`::

        new_audience = (
            'https://pubsub.googleapis.com/google.pubsub.v1.Subscriber')
        new_credentials = credentials.with_claims(audience=new_audience)
    """

    def __init__(
        self,
        signer,
        issuer,
        subject,
        audience,
        additional_claims=None,
        token_lifetime=_DEFAULT_TOKEN_LIFETIME_SECS,
        quota_project_id=None,
    ):
        """
        Args:
            signer (google.auth.crypt.Signer): The signer used to sign JWTs.
            issuer (str): The `iss` claim.
            subject (str): The `sub` claim.
            audience (str): the `aud` claim. The intended audience for the
                credentials.
            additional_claims (Mapping[str, str]): Any additional claims for
                the JWT payload.
            token_lifetime (int): The amount of time in seconds for
                which the token is valid. Defaults to 1 hour.
            quota_project_id (Optional[str]): The project ID used for quota
                and billing.
        """
        super(Credentials, self).__init__()
        self._signer = signer
        self._issuer = issuer
        self._subject = subject
        self._audience = audience
        self._token_lifetime = token_lifetime
        self._quota_project_id = quota_project_id

        if additional_claims is None:
            additional_claims = {}

        self._additional_claims = additional_claims

    @classmethod
    def _from_signer_and_info(cls, signer, info, **kwargs):
        """Creates a Credentials instance from a signer and service account
        info.

        Args:
            signer (google.auth.crypt.Signer): The signer used to sign JWTs.
            info (Mapping[str, str]): The service account info.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.jwt.Credentials: The constructed credentials.

        Raises:
            google.auth.exceptions.MalformedError: If the info is not in the expected format.
        """
        kwargs.setdefault("subject", info["client_email"])
        kwargs.setdefault("issuer", info["client_email"])
        return cls(signer, **kwargs)

    @classmethod
    def from_service_account_info(cls, info, **kwargs):
        """Creates an Credentials instance from a dictionary.

        Args:
            info (Mapping[str, str]): The service account info in Google
                format.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.jwt.Credentials: The constructed credentials.

        Raises:
            google.auth.exceptions.MalformedError: If the info is not in the expected format.
        """
        signer = _service_account_info.from_dict(info, require=["client_email"])
        return cls._from_signer_and_info(signer, info, **kwargs)

    @classmethod
    def from_service_account_file(cls, filename, **kwargs):
        """Creates a Credentials instance from a service account .json file
        in Google format.

        Args:
            filename (str): The path to the service account .json file.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.jwt.Credentials: The constructed credentials.
        """
        info, signer = _service_account_info.from_filename(
            filename, require=["client_email"]
        )
        return cls._from_signer_and_info(signer, info, **kwargs)

    @classmethod
    def from_signing_credentials(cls, credentials, audience, **kwargs):
        """Creates a new :class:`google.auth.jwt.Credentials` instance from an
        existing :class:`google.auth.credentials.Signing` instance.

        The new instance will use the same signer as the existing instance and
        will use the existing instance's signer email as the issuer and
        subject by default.

        Example::

            svc_creds = service_account.Credentials.from_service_account_file(
                'service_account.json')
            audience = (
                'https://pubsub.googleapis.com/google.pubsub.v1.Publisher')
            jwt_creds = jwt.Credentials.from_signing_credentials(
                svc_creds, audience=audience)

        Args:
            credentials (google.auth.credentials.Signing): The credentials to
                use to construct the new credentials.
            audience (str): the `aud` claim. The intended audience for the
                credentials.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.jwt.Credentials: A new Credentials instance.
        """
        kwargs.setdefault("issuer", credentials.signer_email)
        kwargs.setdefault("subject", credentials.signer_email)
        return cls(credentials.signer, audience=audience, **kwargs)

    def with_claims(
        self, issuer=None, subject=None, audience=None, additional_claims=None
    ):
        """Returns a copy of these credentials with modified claims.

        Args:
            issuer (str): The `iss` claim. If unspecified the current issuer
                claim will be used.
            subject (str): The `sub` claim. If unspecified the current subject
                claim will be used.
            audience (str): the `aud` claim. If unspecified the current
                audience claim will be used.
            additional_claims (Mapping[str, str]): Any additional claims for
                the JWT payload. This will be merged with the current
                additional claims.

        Returns:
            google.auth.jwt.Credentials: A new credentials instance.
        """
        new_additional_claims = copy.deepcopy(self._additional_claims)
        new_additional_claims.update(additional_claims or {})

        return self.__class__(
            self._signer,
            issuer=issuer if issuer is not None else self._issuer,
            subject=subject if subject is not None else self._subject,
            audience=audience if audience is not None else self._audience,
            additional_claims=new_additional_claims,
            quota_project_id=self._quota_project_id,
        )

    @_helpers.copy_docstring(google.auth.credentials.CredentialsWithQuotaProject)
    def with_quota_project(self, quota_project_id):
        return self.__class__(
            self._signer,
            issuer=self._issuer,
            subject=self._subject,
            audience=self._audience,
            additional_claims=self._additional_claims,
            quota_project_id=quota_project_id,
        )

    def _make_jwt(self):
        """Make a signed JWT.

        Returns:
            Tuple[bytes, datetime]: The encoded JWT and the expiration.
        """
        now = _helpers.utcnow()
        lifetime = datetime.timedelta(seconds=self._token_lifetime)
        expiry = now + lifetime

        payload = {
            "iss": self._issuer,
            "sub": self._subject,
            "iat": _helpers.datetime_to_secs(now),
            "exp": _helpers.datetime_to_secs(expiry),
        }
        if self._audience:
            payload["aud"] = self._audience

        payload.update(self._additional_claims)

        jwt = encode(self._signer, payload)

        return jwt, expiry

    def refresh(self, request):
        """Refreshes the access token.

        Args:
            request (Any): Unused.
        """
        # pylint: disable=unused-argument
        # (pylint doesn't correctly recognize overridden methods.)
        self.token, self.expiry = self._make_jwt()

    @_helpers.copy_docstring(google.auth.credentials.Signing)
    def sign_bytes(self, message):
        return self._signer.sign(message)

    @property  # type: ignore
    @_helpers.copy_docstring(google.auth.credentials.Signing)
    def signer_email(self):
        return self._issuer

    @property  # type: ignore
    @_helpers.copy_docstring(google.auth.credentials.Signing)
    def signer(self):
        return self._signer

    @property  # type: ignore
    def additional_claims(self):
        """ Additional claims the JWT object was created with."""
        return self._additional_claims


class OnDemandCredentials(
    google.auth.credentials.Signing, google.auth.credentials.CredentialsWithQuotaProject
):
    """On-demand JWT credentials.

    Like :class:`Credentials`, this class uses a JWT as the bearer token for
    authentication. However, this class does not require the audience at
    construction time. Instead, it will generate a new token on-demand for
    each request using the request URI as the audience. It caches tokens
    so that multiple requests to the same URI do not incur the overhead
    of generating a new token every time.

    This behavior is especially useful for `gRPC`_ clients. A gRPC service may
    have multiple audience and gRPC clients may not know all of the audiences
    required for accessing a particular service. With these credentials,
    no knowledge of the audiences is required ahead of time.

    .. _grpc: http://www.grpc.io/
    """

    def __init__(
        self,
        signer,
        issuer,
        subject,
        additional_claims=None,
        token_lifetime=_DEFAULT_TOKEN_LIFETIME_SECS,
        max_cache_size=_DEFAULT_MAX_CACHE_SIZE,
        quota_project_id=None,
    ):
        """
        Args:
            signer (google.auth.crypt.Signer): The signer used to sign JWTs.
            issuer (str): The `iss` claim.
            subject (str): The `sub` claim.
            additional_claims (Mapping[str, str]): Any additional claims for
                the JWT payload.
            token_lifetime (int): The amount of time in seconds for
                which the token is valid. Defaults to 1 hour.
            max_cache_size (int): The maximum number of JWT tokens to keep in
                cache. Tokens are cached using :class:`cachetools.LRUCache`.
            quota_project_id (Optional[str]): The project ID used for quota
                and billing.

        """
        super(OnDemandCredentials, self).__init__()
        self._signer = signer
        self._issuer = issuer
        self._subject = subject
        self._token_lifetime = token_lifetime
        self._quota_project_id = quota_project_id

        if additional_claims is None:
            additional_claims = {}

        self._additional_claims = additional_claims
        self._cache = cachetools.LRUCache(maxsize=max_cache_size)

    @classmethod
    def _from_signer_and_info(cls, signer, info, **kwargs):
        """Creates an OnDemandCredentials instance from a signer and service
        account info.

        Args:
            signer (google.auth.crypt.Signer): The signer used to sign JWTs.
            info (Mapping[str, str]): The service account info.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.jwt.OnDemandCredentials: The constructed credentials.

        Raises:
            google.auth.exceptions.MalformedError: If the info is not in the expected format.
        """
        kwargs.setdefault("subject", info["client_email"])
        kwargs.setdefault("issuer", info["client_email"])
        return cls(signer, **kwargs)

    @classmethod
    def from_service_account_info(cls, info, **kwargs):
        """Creates an OnDemandCredentials instance from a dictionary.

        Args:
            info (Mapping[str, str]): The service account info in Google
                format.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.jwt.OnDemandCredentials: The constructed credentials.

        Raises:
            google.auth.exceptions.MalformedError: If the info is not in the expected format.
        """
        signer = _service_account_info.from_dict(info, require=["client_email"])
        return cls._from_signer_and_info(signer, info, **kwargs)

    @classmethod
    def from_service_account_file(cls, filename, **kwargs):
        """Creates an OnDemandCredentials instance from a service account .json
        file in Google format.

        Args:
            filename (str): The path to the service account .json file.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.jwt.OnDemandCredentials: The constructed credentials.
        """
        info, signer = _service_account_info.from_filename(
            filename, require=["client_email"]
        )
        return cls._from_signer_and_info(signer, info, **kwargs)

    @classmethod
    def from_signing_credentials(cls, credentials, **kwargs):
        """Creates a new :class:`google.auth.jwt.OnDemandCredentials` instance
        from an existing :class:`google.auth.credentials.Signing` instance.

        The new instance will use the same signer as the existing instance and
        will use the existing instance's signer email as the issuer and
        subject by default.

        Example::

            svc_creds = service_account.Credentials.from_service_account_file(
                'service_account.json')
            jwt_creds = jwt.OnDemandCredentials.from_signing_credentials(
                svc_creds)

        Args:
            credentials (google.auth.credentials.Signing): The credentials to
                use to construct the new credentials.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.jwt.Credentials: A new Credentials instance.
        """
        kwargs.setdefault("issuer", credentials.signer_email)
        kwargs.setdefault("subject", credentials.signer_email)
        return cls(credentials.signer, **kwargs)

    def with_claims(self, issuer=None, subject=None, additional_claims=None):
        """Returns a copy of these credentials with modified claims.

        Args:
            issuer (str): The `iss` claim. If unspecified the current issuer
                claim will be used.
            subject (str): The `sub` claim. If unspecified the current subject
                claim will be used.
            additional_claims (Mapping[str, str]): Any additional claims for
                the JWT payload. This will be merged with the current
                additional claims.

        Returns:
            google.auth.jwt.OnDemandCredentials: A new credentials instance.
        """
        new_additional_claims = copy.deepcopy(self._additional_claims)
        new_additional_claims.update(additional_claims or {})

        return self.__class__(
            self._signer,
            issuer=issuer if issuer is not None else self._issuer,
            subject=subject if subject is not None else self._subject,
            additional_claims=new_additional_claims,
            max_cache_size=self._cache.maxsize,
            quota_project_id=self._quota_project_id,
        )

    @_helpers.copy_docstring(google.auth.credentials.CredentialsWithQuotaProject)
    def with_quota_project(self, quota_project_id):

        return self.__class__(
            self._signer,
            issuer=self._issuer,
            subject=self._subject,
            additional_claims=self._additional_claims,
            max_cache_size=self._cache.maxsize,
            quota_project_id=quota_project_id,
        )

    @property
    def valid(self):
        """Checks the validity of the credentials.

        These credentials are always valid because it generates tokens on
        demand.
        """
        return True

    def _make_jwt_for_audience(self, audience):
        """Make a new JWT for the given audience.

        Args:
            audience (str): The intended audience.

        Returns:
            Tuple[bytes, datetime]: The encoded JWT and the expiration.
        """
        now = _helpers.utcnow()
        lifetime = datetime.timedelta(seconds=self._token_lifetime)
        expiry = now + lifetime

        payload = {
            "iss": self._issuer,
            "sub": self._subject,
            "iat": _helpers.datetime_to_secs(now),
            "exp": _helpers.datetime_to_secs(expiry),
            "aud": audience,
        }

        payload.update(self._additional_claims)

        jwt = encode(self._signer, payload)

        return jwt, expiry

    def _get_jwt_for_audience(self, audience):
        """Get a JWT For a given audience.

        If there is already an existing, non-expired token in the cache for
        the audience, that token is used. Otherwise, a new token will be
        created.

        Args:
            audience (str): The intended audience.

        Returns:
            bytes: The encoded JWT.
        """
        token, expiry = self._cache.get(audience, (None, None))

        if token is None or expiry < _helpers.utcnow():
            token, expiry = self._make_jwt_for_audience(audience)
            self._cache[audience] = token, expiry

        return token

    def refresh(self, request):
        """Raises an exception, these credentials can not be directly
        refreshed.

        Args:
            request (Any): Unused.

        Raises:
            google.auth.RefreshError
        """
        # pylint: disable=unused-argument
        # (pylint doesn't correctly recognize overridden methods.)
        raise exceptions.RefreshError(
            "OnDemandCredentials can not be directly refreshed."
        )

    def before_request(self, request, method, url, headers):
        """Performs credential-specific before request logic.

        Args:
            request (Any): Unused. JWT credentials do not need to make an
                HTTP request to refresh.
            method (str): The request's HTTP method.
            url (str): The request's URI. This is used as the audience claim
                when generating the JWT.
            headers (Mapping): The request's headers.
        """
        # pylint: disable=unused-argument
        # (pylint doesn't correctly recognize overridden methods.)
        parts = urllib.parse.urlsplit(url)
        # Strip query string and fragment
        audience = urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, parts.path, "", "")
        )
        token = self._get_jwt_for_audience(audience)
        self.apply(headers, token=token)

    @_helpers.copy_docstring(google.auth.credentials.Signing)
    def sign_bytes(self, message):
        return self._signer.sign(message)

    @property  # type: ignore
    @_helpers.copy_docstring(google.auth.credentials.Signing)
    def signer_email(self):
        return self._issuer

    @property  # type: ignore
    @_helpers.copy_docstring(google.auth.credentials.Signing)
    def signer(self):
        return self._signer

# === NexusCore/openenv\Lib\site-packages\click\termui.py ===
from __future__ import annotations

import collections.abc as cabc
import inspect
import io
import itertools
import sys
import typing as t
from contextlib import AbstractContextManager
from gettext import gettext as _

from ._compat import isatty
from ._compat import strip_ansi
from .exceptions import Abort
from .exceptions import UsageError
from .globals import resolve_color_default
from .types import Choice
from .types import convert_type
from .types import ParamType
from .utils import echo
from .utils import LazyFile

if t.TYPE_CHECKING:
    from ._termui_impl import ProgressBar

V = t.TypeVar("V")

# The prompt functions to use.  The doc tools currently override these
# functions to customize how they work.
visible_prompt_func: t.Callable[[str], str] = input

_ansi_colors = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "reset": 39,
    "bright_black": 90,
    "bright_red": 91,
    "bright_green": 92,
    "bright_yellow": 93,
    "bright_blue": 94,
    "bright_magenta": 95,
    "bright_cyan": 96,
    "bright_white": 97,
}
_ansi_reset_all = "\033[0m"


def hidden_prompt_func(prompt: str) -> str:
    import getpass

    return getpass.getpass(prompt)


def _build_prompt(
    text: str,
    suffix: str,
    show_default: bool = False,
    default: t.Any | None = None,
    show_choices: bool = True,
    type: ParamType | None = None,
) -> str:
    prompt = text
    if type is not None and show_choices and isinstance(type, Choice):
        prompt += f" ({', '.join(map(str, type.choices))})"
    if default is not None and show_default:
        prompt = f"{prompt} [{_format_default(default)}]"
    return f"{prompt}{suffix}"


def _format_default(default: t.Any) -> t.Any:
    if isinstance(default, (io.IOBase, LazyFile)) and hasattr(default, "name"):
        return default.name

    return default


def prompt(
    text: str,
    default: t.Any | None = None,
    hide_input: bool = False,
    confirmation_prompt: bool | str = False,
    type: ParamType | t.Any | None = None,
    value_proc: t.Callable[[str], t.Any] | None = None,
    prompt_suffix: str = ": ",
    show_default: bool = True,
    err: bool = False,
    show_choices: bool = True,
) -> t.Any:
    """Prompts a user for input.  This is a convenience function that can
    be used to prompt a user for input later.

    If the user aborts the input by sending an interrupt signal, this
    function will catch it and raise a :exc:`Abort` exception.

    :param text: the text to show for the prompt.
    :param default: the default value to use if no input happens.  If this
                    is not given it will prompt until it's aborted.
    :param hide_input: if this is set to true then the input value will
                       be hidden.
    :param confirmation_prompt: Prompt a second time to confirm the
        value. Can be set to a string instead of ``True`` to customize
        the message.
    :param type: the type to use to check the value against.
    :param value_proc: if this parameter is provided it's a function that
                       is invoked instead of the type conversion to
                       convert a value.
    :param prompt_suffix: a suffix that should be added to the prompt.
    :param show_default: shows or hides the default value in the prompt.
    :param err: if set to true the file defaults to ``stderr`` instead of
                ``stdout``, the same as with echo.
    :param show_choices: Show or hide choices if the passed type is a Choice.
                         For example if type is a Choice of either day or week,
                         show_choices is true and text is "Group by" then the
                         prompt will be "Group by (day, week): ".

    .. versionadded:: 8.0
        ``confirmation_prompt`` can be a custom string.

    .. versionadded:: 7.0
        Added the ``show_choices`` parameter.

    .. versionadded:: 6.0
        Added unicode support for cmd.exe on Windows.

    .. versionadded:: 4.0
        Added the `err` parameter.

    """

    def prompt_func(text: str) -> str:
        f = hidden_prompt_func if hide_input else visible_prompt_func
        try:
            # Write the prompt separately so that we get nice
            # coloring through colorama on Windows
            echo(text.rstrip(" "), nl=False, err=err)
            # Echo a space to stdout to work around an issue where
            # readline causes backspace to clear the whole line.
            return f(" ")
        except (KeyboardInterrupt, EOFError):
            # getpass doesn't print a newline if the user aborts input with ^C.
            # Allegedly this behavior is inherited from getpass(3).
            # A doc bug has been filed at https://bugs.python.org/issue24711
            if hide_input:
                echo(None, err=err)
            raise Abort() from None

    if value_proc is None:
        value_proc = convert_type(type, default)

    prompt = _build_prompt(
        text, prompt_suffix, show_default, default, show_choices, type
    )

    if confirmation_prompt:
        if confirmation_prompt is True:
            confirmation_prompt = _("Repeat for confirmation")

        confirmation_prompt = _build_prompt(confirmation_prompt, prompt_suffix)

    while True:
        while True:
            value = prompt_func(prompt)
            if value:
                break
            elif default is not None:
                value = default
                break
        try:
            result = value_proc(value)
        except UsageError as e:
            if hide_input:
                echo(_("Error: The value you entered was invalid."), err=err)
            else:
                echo(_("Error: {e.message}").format(e=e), err=err)
            continue
        if not confirmation_prompt:
            return result
        while True:
            value2 = prompt_func(confirmation_prompt)
            is_empty = not value and not value2
            if value2 or is_empty:
                break
        if value == value2:
            return result
        echo(_("Error: The two entered values do not match."), err=err)


def confirm(
    text: str,
    default: bool | None = False,
    abort: bool = False,
    prompt_suffix: str = ": ",
    show_default: bool = True,
    err: bool = False,
) -> bool:
    """Prompts for confirmation (yes/no question).

    If the user aborts the input by sending a interrupt signal this
    function will catch it and raise a :exc:`Abort` exception.

    :param text: the question to ask.
    :param default: The default value to use when no input is given. If
        ``None``, repeat until input is given.
    :param abort: if this is set to `True` a negative answer aborts the
                  exception by raising :exc:`Abort`.
    :param prompt_suffix: a suffix that should be added to the prompt.
    :param show_default: shows or hides the default value in the prompt.
    :param err: if set to true the file defaults to ``stderr`` instead of
                ``stdout``, the same as with echo.

    .. versionchanged:: 8.0
        Repeat until input is given if ``default`` is ``None``.

    .. versionadded:: 4.0
        Added the ``err`` parameter.
    """
    prompt = _build_prompt(
        text,
        prompt_suffix,
        show_default,
        "y/n" if default is None else ("Y/n" if default else "y/N"),
    )

    while True:
        try:
            # Write the prompt separately so that we get nice
            # coloring through colorama on Windows
            echo(prompt.rstrip(" "), nl=False, err=err)
            # Echo a space to stdout to work around an issue where
            # readline causes backspace to clear the whole line.
            value = visible_prompt_func(" ").lower().strip()
        except (KeyboardInterrupt, EOFError):
            raise Abort() from None
        if value in ("y", "yes"):
            rv = True
        elif value in ("n", "no"):
            rv = False
        elif default is not None and value == "":
            rv = default
        else:
            echo(_("Error: invalid input"), err=err)
            continue
        break
    if abort and not rv:
        raise Abort()
    return rv


def echo_via_pager(
    text_or_generator: cabc.Iterable[str] | t.Callable[[], cabc.Iterable[str]] | str,
    color: bool | None = None,
) -> None:
    """This function takes a text and shows it via an environment specific
    pager on stdout.

    .. versionchanged:: 3.0
       Added the `color` flag.

    :param text_or_generator: the text to page, or alternatively, a
                              generator emitting the text to page.
    :param color: controls if the pager supports ANSI colors or not.  The
                  default is autodetection.
    """
    color = resolve_color_default(color)

    if inspect.isgeneratorfunction(text_or_generator):
        i = t.cast("t.Callable[[], cabc.Iterable[str]]", text_or_generator)()
    elif isinstance(text_or_generator, str):
        i = [text_or_generator]
    else:
        i = iter(t.cast("cabc.Iterable[str]", text_or_generator))

    # convert every element of i to a text type if necessary
    text_generator = (el if isinstance(el, str) else str(el) for el in i)

    from ._termui_impl import pager

    return pager(itertools.chain(text_generator, "\n"), color)


@t.overload
def progressbar(
    *,
    length: int,
    label: str | None = None,
    hidden: bool = False,
    show_eta: bool = True,
    show_percent: bool | None = None,
    show_pos: bool = False,
    fill_char: str = "#",
    empty_char: str = "-",
    bar_template: str = "%(label)s  [%(bar)s]  %(info)s",
    info_sep: str = "  ",
    width: int = 36,
    file: t.TextIO | None = None,
    color: bool | None = None,
    update_min_steps: int = 1,
) -> ProgressBar[int]: ...


@t.overload
def progressbar(
    iterable: cabc.Iterable[V] | None = None,
    length: int | None = None,
    label: str | None = None,
    hidden: bool = False,
    show_eta: bool = True,
    show_percent: bool | None = None,
    show_pos: bool = False,
    item_show_func: t.Callable[[V | None], str | None] | None = None,
    fill_char: str = "#",
    empty_char: str = "-",
    bar_template: str = "%(label)s  [%(bar)s]  %(info)s",
    info_sep: str = "  ",
    width: int = 36,
    file: t.TextIO | None = None,
    color: bool | None = None,
    update_min_steps: int = 1,
) -> ProgressBar[V]: ...


def progressbar(
    iterable: cabc.Iterable[V] | None = None,
    length: int | None = None,
    label: str | None = None,
    hidden: bool = False,
    show_eta: bool = True,
    show_percent: bool | None = None,
    show_pos: bool = False,
    item_show_func: t.Callable[[V | None], str | None] | None = None,
    fill_char: str = "#",
    empty_char: str = "-",
    bar_template: str = "%(label)s  [%(bar)s]  %(info)s",
    info_sep: str = "  ",
    width: int = 36,
    file: t.TextIO | None = None,
    color: bool | None = None,
    update_min_steps: int = 1,
) -> ProgressBar[V]:
    """This function creates an iterable context manager that can be used
    to iterate over something while showing a progress bar.  It will
    either iterate over the `iterable` or `length` items (that are counted
    up).  While iteration happens, this function will print a rendered
    progress bar to the given `file` (defaults to stdout) and will attempt
    to calculate remaining time and more.  By default, this progress bar
    will not be rendered if the file is not a terminal.

    The context manager creates the progress bar.  When the context
    manager is entered the progress bar is already created.  With every
    iteration over the progress bar, the iterable passed to the bar is
    advanced and the bar is updated.  When the context manager exits,
    a newline is printed and the progress bar is finalized on screen.

    Note: The progress bar is currently designed for use cases where the
    total progress can be expected to take at least several seconds.
    Because of this, the ProgressBar class object won't display
    progress that is considered too fast, and progress where the time
    between steps is less than a second.

    No printing must happen or the progress bar will be unintentionally
    destroyed.

    Example usage::

        with progressbar(items) as bar:
            for item in bar:
                do_something_with(item)

    Alternatively, if no iterable is specified, one can manually update the
    progress bar through the `update()` method instead of directly
    iterating over the progress bar.  The update method accepts the number
    of steps to increment the bar with::

        with progressbar(length=chunks.total_bytes) as bar:
            for chunk in chunks:
                process_chunk(chunk)
                bar.update(chunks.bytes)

    The ``update()`` method also takes an optional value specifying the
    ``current_item`` at the new position. This is useful when used
    together with ``item_show_func`` to customize the output for each
    manual step::

        with click.progressbar(
            length=total_size,
            label='Unzipping archive',
            item_show_func=lambda a: a.filename
        ) as bar:
            for archive in zip_file:
                archive.extract()
                bar.update(archive.size, archive)

    :param iterable: an iterable to iterate over.  If not provided the length
                     is required.
    :param length: the number of items to iterate over.  By default the
                   progressbar will attempt to ask the iterator about its
                   length, which might or might not work.  If an iterable is
                   also provided this parameter can be used to override the
                   length.  If an iterable is not provided the progress bar
                   will iterate over a range of that length.
    :param label: the label to show next to the progress bar.
    :param hidden: hide the progressbar. Defaults to ``False``. When no tty is
        detected, it will only print the progressbar label. Setting this to
        ``False`` also disables that.
    :param show_eta: enables or disables the estimated time display.  This is
                     automatically disabled if the length cannot be
                     determined.
    :param show_percent: enables or disables the percentage display.  The
                         default is `True` if the iterable has a length or
                         `False` if not.
    :param show_pos: enables or disables the absolute position display.  The
                     default is `False`.
    :param item_show_func: A function called with the current item which
        can return a string to show next to the progress bar. If the
        function returns ``None`` nothing is shown. The current item can
        be ``None``, such as when entering and exiting the bar.
    :param fill_char: the character to use to show the filled part of the
                      progress bar.
    :param empty_char: the character to use to show the non-filled part of
                       the progress bar.
    :param bar_template: the format string to use as template for the bar.
                         The parameters in it are ``label`` for the label,
                         ``bar`` for the progress bar and ``info`` for the
                         info section.
    :param info_sep: the separator between multiple info items (eta etc.)
    :param width: the width of the progress bar in characters, 0 means full
                  terminal width
    :param file: The file to write to. If this is not a terminal then
        only the label is printed.
    :param color: controls if the terminal supports ANSI colors or not.  The
                  default is autodetection.  This is only needed if ANSI
                  codes are included anywhere in the progress bar output
                  which is not the case by default.
    :param update_min_steps: Render only when this many updates have
        completed. This allows tuning for very fast iterators.

    .. versionadded:: 8.2
        The ``hidden`` argument.

    .. versionchanged:: 8.0
        Output is shown even if execution time is less than 0.5 seconds.

    .. versionchanged:: 8.0
        ``item_show_func`` shows the current item, not the previous one.

    .. versionchanged:: 8.0
        Labels are echoed if the output is not a TTY. Reverts a change
        in 7.0 that removed all output.

    .. versionadded:: 8.0
       The ``update_min_steps`` parameter.

    .. versionadded:: 4.0
        The ``color`` parameter and ``update`` method.

    .. versionadded:: 2.0
    """
    from ._termui_impl import ProgressBar

    color = resolve_color_default(color)
    return ProgressBar(
        iterable=iterable,
        length=length,
        hidden=hidden,
        show_eta=show_eta,
        show_percent=show_percent,
        show_pos=show_pos,
        item_show_func=item_show_func,
        fill_char=fill_char,
        empty_char=empty_char,
        bar_template=bar_template,
        info_sep=info_sep,
        file=file,
        label=label,
        width=width,
        color=color,
        update_min_steps=update_min_steps,
    )


def clear() -> None:
    """Clears the terminal screen.  This will have the effect of clearing
    the whole visible space of the terminal and moving the cursor to the
    top left.  This does not do anything if not connected to a terminal.

    .. versionadded:: 2.0
    """
    if not isatty(sys.stdout):
        return

    # ANSI escape \033[2J clears the screen, \033[1;1H moves the cursor
    echo("\033[2J\033[1;1H", nl=False)


def _interpret_color(color: int | tuple[int, int, int] | str, offset: int = 0) -> str:
    if isinstance(color, int):
        return f"{38 + offset};5;{color:d}"

    if isinstance(color, (tuple, list)):
        r, g, b = color
        return f"{38 + offset};2;{r:d};{g:d};{b:d}"

    return str(_ansi_colors[color] + offset)


def style(
    text: t.Any,
    fg: int | tuple[int, int, int] | str | None = None,
    bg: int | tuple[int, int, int] | str | None = None,
    bold: bool | None = None,
    dim: bool | None = None,
    underline: bool | None = None,
    overline: bool | None = None,
    italic: bool | None = None,
    blink: bool | None = None,
    reverse: bool | None = None,
    strikethrough: bool | None = None,
    reset: bool = True,
) -> str:
    """Styles a text with ANSI styles and returns the new string.  By
    default the styling is self contained which means that at the end
    of the string a reset code is issued.  This can be prevented by
    passing ``reset=False``.

    Examples::

        click.echo(click.style('Hello World!', fg='green'))
        click.echo(click.style('ATTENTION!', blink=True))
        click.echo(click.style('Some things', reverse=True, fg='cyan'))
        click.echo(click.style('More colors', fg=(255, 12, 128), bg=117))

    Supported color names:

    * ``black`` (might be a gray)
    * ``red``
    * ``green``
    * ``yellow`` (might be an orange)
    * ``blue``
    * ``magenta``
    * ``cyan``
    * ``white`` (might be light gray)
    * ``bright_black``
    * ``bright_red``
    * ``bright_green``
    * ``bright_yellow``
    * ``bright_blue``
    * ``bright_magenta``
    * ``bright_cyan``
    * ``bright_white``
    * ``reset`` (reset the color code only)

    If the terminal supports it, color may also be specified as:

    -   An integer in the interval [0, 255]. The terminal must support
        8-bit/256-color mode.
    -   An RGB tuple of three integers in [0, 255]. The terminal must
        support 24-bit/true-color mode.

    See https://en.wikipedia.org/wiki/ANSI_color and
    https://gist.github.com/XVilka/8346728 for more information.

    :param text: the string to style with ansi codes.
    :param fg: if provided this will become the foreground color.
    :param bg: if provided this will become the background color.
    :param bold: if provided this will enable or disable bold mode.
    :param dim: if provided this will enable or disable dim mode.  This is
                badly supported.
    :param underline: if provided this will enable or disable underline.
    :param overline: if provided this will enable or disable overline.
    :param italic: if provided this will enable or disable italic.
    :param blink: if provided this will enable or disable blinking.
    :param reverse: if provided this will enable or disable inverse
                    rendering (foreground becomes background and the
                    other way round).
    :param strikethrough: if provided this will enable or disable
        striking through text.
    :param reset: by default a reset-all code is added at the end of the
                  string which means that styles do not carry over.  This
                  can be disabled to compose styles.

    .. versionchanged:: 8.0
        A non-string ``message`` is converted to a string.

    .. versionchanged:: 8.0
       Added support for 256 and RGB color codes.

    .. versionchanged:: 8.0
        Added the ``strikethrough``, ``italic``, and ``overline``
        parameters.

    .. versionchanged:: 7.0
        Added support for bright colors.

    .. versionadded:: 2.0
    """
    if not isinstance(text, str):
        text = str(text)

    bits = []

    if fg:
        try:
            bits.append(f"\033[{_interpret_color(fg)}m")
        except KeyError:
            raise TypeError(f"Unknown color {fg!r}") from None

    if bg:
        try:
            bits.append(f"\033[{_interpret_color(bg, 10)}m")
        except KeyError:
            raise TypeError(f"Unknown color {bg!r}") from None

    if bold is not None:
        bits.append(f"\033[{1 if bold else 22}m")
    if dim is not None:
        bits.append(f"\033[{2 if dim else 22}m")
    if underline is not None:
        bits.append(f"\033[{4 if underline else 24}m")
    if overline is not None:
        bits.append(f"\033[{53 if overline else 55}m")
    if italic is not None:
        bits.append(f"\033[{3 if italic else 23}m")
    if blink is not None:
        bits.append(f"\033[{5 if blink else 25}m")
    if reverse is not None:
        bits.append(f"\033[{7 if reverse else 27}m")
    if strikethrough is not None:
        bits.append(f"\033[{9 if strikethrough else 29}m")
    bits.append(text)
    if reset:
        bits.append(_ansi_reset_all)
    return "".join(bits)


def unstyle(text: str) -> str:
    """Removes ANSI styling information from a string.  Usually it's not
    necessary to use this function as Click's echo function will
    automatically remove styling if necessary.

    .. versionadded:: 2.0

    :param text: the text to remove style information from.
    """
    return strip_ansi(text)


def secho(
    message: t.Any | None = None,
    file: t.IO[t.AnyStr] | None = None,
    nl: bool = True,
    err: bool = False,
    color: bool | None = None,
    **styles: t.Any,
) -> None:
    """This function combines :func:`echo` and :func:`style` into one
    call.  As such the following two calls are the same::

        click.secho('Hello World!', fg='green')
        click.echo(click.style('Hello World!', fg='green'))

    All keyword arguments are forwarded to the underlying functions
    depending on which one they go with.

    Non-string types will be converted to :class:`str`. However,
    :class:`bytes` are passed directly to :meth:`echo` without applying
    style. If you want to style bytes that represent text, call
    :meth:`bytes.decode` first.

    .. versionchanged:: 8.0
        A non-string ``message`` is converted to a string. Bytes are
        passed through without style applied.

    .. versionadded:: 2.0
    """
    if message is not None and not isinstance(message, (bytes, bytearray)):
        message = style(message, **styles)

    return echo(message, file=file, nl=nl, err=err, color=color)


@t.overload
def edit(
    text: bytes | bytearray,
    editor: str | None = None,
    env: cabc.Mapping[str, str] | None = None,
    require_save: bool = False,
    extension: str = ".txt",
) -> bytes | None: ...


@t.overload
def edit(
    text: str,
    editor: str | None = None,
    env: cabc.Mapping[str, str] | None = None,
    require_save: bool = True,
    extension: str = ".txt",
) -> str | None: ...


@t.overload
def edit(
    text: None = None,
    editor: str | None = None,
    env: cabc.Mapping[str, str] | None = None,
    require_save: bool = True,
    extension: str = ".txt",
    filename: str | cabc.Iterable[str] | None = None,
) -> None: ...


def edit(
    text: str | bytes | bytearray | None = None,
    editor: str | None = None,
    env: cabc.Mapping[str, str] | None = None,
    require_save: bool = True,
    extension: str = ".txt",
    filename: str | cabc.Iterable[str] | None = None,
) -> str | bytes | bytearray | None:
    r"""Edits the given text in the defined editor.  If an editor is given
    (should be the full path to the executable but the regular operating
    system search path is used for finding the executable) it overrides
    the detected editor.  Optionally, some environment variables can be
    used.  If the editor is closed without changes, `None` is returned.  In
    case a file is edited directly the return value is always `None` and
    `require_save` and `extension` are ignored.

    If the editor cannot be opened a :exc:`UsageError` is raised.

    Note for Windows: to simplify cross-platform usage, the newlines are
    automatically converted from POSIX to Windows and vice versa.  As such,
    the message here will have ``\n`` as newline markers.

    :param text: the text to edit.
    :param editor: optionally the editor to use.  Defaults to automatic
                   detection.
    :param env: environment variables to forward to the editor.
    :param require_save: if this is true, then not saving in the editor
                         will make the return value become `None`.
    :param extension: the extension to tell the editor about.  This defaults
                      to `.txt` but changing this might change syntax
                      highlighting.
    :param filename: if provided it will edit this file instead of the
                     provided text contents.  It will not use a temporary
                     file as an indirection in that case. If the editor supports
                     editing multiple files at once, a sequence of files may be
                     passed as well. Invoke `click.file` once per file instead
                     if multiple files cannot be managed at once or editing the
                     files serially is desired.

    .. versionchanged:: 8.2.0
        ``filename`` now accepts any ``Iterable[str]`` in addition to a ``str``
        if the ``editor`` supports editing multiple files at once.

    """
    from ._termui_impl import Editor

    ed = Editor(editor=editor, env=env, require_save=require_save, extension=extension)

    if filename is None:
        return ed.edit(text)

    if isinstance(filename, str):
        filename = (filename,)

    ed.edit_files(filenames=filename)
    return None


def launch(url: str, wait: bool = False, locate: bool = False) -> int:
    """This function launches the given URL (or filename) in the default
    viewer application for this file type.  If this is an executable, it
    might launch the executable in a new session.  The return value is
    the exit code of the launched application.  Usually, ``0`` indicates
    success.

    Examples::

        click.launch('https://click.palletsprojects.com/')
        click.launch('/my/downloaded/file', locate=True)

    .. versionadded:: 2.0

    :param url: URL or filename of the thing to launch.
    :param wait: Wait for the program to exit before returning. This
        only works if the launched program blocks. In particular,
        ``xdg-open`` on Linux does not block.
    :param locate: if this is set to `True` then instead of launching the
                   application associated with the URL it will attempt to
                   launch a file manager with the file located.  This
                   might have weird effects if the URL does not point to
                   the filesystem.
    """
    from ._termui_impl import open_url

    return open_url(url, wait=wait, locate=locate)


# If this is provided, getchar() calls into this instead.  This is used
# for unittesting purposes.
_getchar: t.Callable[[bool], str] | None = None


def getchar(echo: bool = False) -> str:
    """Fetches a single character from the terminal and returns it.  This
    will always return a unicode character and under certain rare
    circumstances this might return more than one character.  The
    situations which more than one character is returned is when for
    whatever reason multiple characters end up in the terminal buffer or
    standard input was not actually a terminal.

    Note that this will always read from the terminal, even if something
    is piped into the standard input.

    Note for Windows: in rare cases when typing non-ASCII characters, this
    function might wait for a second character and then return both at once.
    This is because certain Unicode characters look like special-key markers.

    .. versionadded:: 2.0

    :param echo: if set to `True`, the character read will also show up on
                 the terminal.  The default is to not show it.
    """
    global _getchar

    if _getchar is None:
        from ._termui_impl import getchar as f

        _getchar = f

    return _getchar(echo)


def raw_terminal() -> AbstractContextManager[int]:
    from ._termui_impl import raw_terminal as f

    return f()


def pause(info: str | None = None, err: bool = False) -> None:
    """This command stops execution and waits for the user to press any
    key to continue.  This is similar to the Windows batch "pause"
    command.  If the program is not run through a terminal, this command
    will instead do nothing.

    .. versionadded:: 2.0

    .. versionadded:: 4.0
       Added the `err` parameter.

    :param info: The message to print before pausing. Defaults to
        ``"Press any key to continue..."``.
    :param err: if set to message goes to ``stderr`` instead of
                ``stdout``, the same as with echo.
    """
    if not isatty(sys.stdin) or not isatty(sys.stdout):
        return

    if info is None:
        info = _("Press any key to continue...")

    try:
        if info:
            echo(info, nl=False, err=err)
        try:
            getchar()
        except (KeyboardInterrupt, EOFError):
            pass
    finally:
        if info:
            echo(err=err)

# === NexusCore/openenv\Lib\site-packages\trio\_sync.py ===
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Protocol

import attrs

import trio

from . import _core
from ._core import (
    Abort,
    ParkingLot,
    RaiseCancelT,
    add_parking_lot_breaker,
    enable_ki_protection,
    remove_parking_lot_breaker,
)
from ._util import final

if TYPE_CHECKING:
    from types import TracebackType

    from ._core import Task
    from ._core._parking_lot import ParkingLotStatistics


@attrs.frozen
class EventStatistics:
    """An object containing debugging information.

    Currently the following fields are defined:

    * ``tasks_waiting``: The number of tasks blocked on this event's
      :meth:`trio.Event.wait` method.

    """

    tasks_waiting: int


@final
@attrs.define(repr=False, eq=False)
class Event:
    """A waitable boolean value useful for inter-task synchronization,
    inspired by :class:`threading.Event`.

    An event object has an internal boolean flag, representing whether
    the event has happened yet. The flag is initially False, and the
    :meth:`wait` method waits until the flag is True. If the flag is
    already True, then :meth:`wait` returns immediately. (If the event has
    already happened, there's nothing to wait for.) The :meth:`set` method
    sets the flag to True, and wakes up any waiters.

    This behavior is useful because it helps avoid race conditions and
    lost wakeups: it doesn't matter whether :meth:`set` gets called just
    before or after :meth:`wait`. If you want a lower-level wakeup
    primitive that doesn't have this protection, consider :class:`Condition`
    or :class:`trio.lowlevel.ParkingLot`.

    .. note:: Unlike `threading.Event`, `trio.Event` has no
       `~threading.Event.clear` method. In Trio, once an `Event` has happened,
       it cannot un-happen. If you need to represent a series of events,
       consider creating a new `Event` object for each one (they're cheap!),
       or other synchronization methods like :ref:`channels <channels>` or
       `trio.lowlevel.ParkingLot`.

    """

    _tasks: set[Task] = attrs.field(factory=set, init=False)
    _flag: bool = attrs.field(default=False, init=False)

    def is_set(self) -> bool:
        """Return the current value of the internal flag."""
        return self._flag

    @enable_ki_protection
    def set(self) -> None:
        """Set the internal flag value to True, and wake any waiting tasks."""
        if not self._flag:
            self._flag = True
            for task in self._tasks:
                _core.reschedule(task)
            self._tasks.clear()

    async def wait(self) -> None:
        """Block until the internal flag value becomes True.

        If it's already True, then this method returns immediately.

        """
        if self._flag:
            await trio.lowlevel.checkpoint()
        else:
            task = _core.current_task()
            self._tasks.add(task)

            def abort_fn(_: RaiseCancelT) -> Abort:
                self._tasks.remove(task)
                return _core.Abort.SUCCEEDED

            await _core.wait_task_rescheduled(abort_fn)

    def statistics(self) -> EventStatistics:
        """Return an object containing debugging information.

        Currently the following fields are defined:

        * ``tasks_waiting``: The number of tasks blocked on this event's
          :meth:`wait` method.

        """
        return EventStatistics(tasks_waiting=len(self._tasks))


class _HasAcquireRelease(Protocol):
    """Only classes with acquire() and release() can use the mixin's implementations."""

    async def acquire(self) -> object: ...

    def release(self) -> object: ...


class AsyncContextManagerMixin:
    @enable_ki_protection
    async def __aenter__(self: _HasAcquireRelease) -> None:
        await self.acquire()

    @enable_ki_protection
    async def __aexit__(
        self: _HasAcquireRelease,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()


@attrs.frozen
class CapacityLimiterStatistics:
    """An object containing debugging information.

    Currently the following fields are defined:

    * ``borrowed_tokens``: The number of tokens currently borrowed from
      the sack.
    * ``total_tokens``: The total number of tokens in the sack. Usually
      this will be larger than ``borrowed_tokens``, but it's possibly for
      it to be smaller if :attr:`trio.CapacityLimiter.total_tokens` was recently decreased.
    * ``borrowers``: A list of all tasks or other entities that currently
      hold a token.
    * ``tasks_waiting``: The number of tasks blocked on this
      :class:`CapacityLimiter`\'s :meth:`trio.CapacityLimiter.acquire` or
      :meth:`trio.CapacityLimiter.acquire_on_behalf_of` methods.

    """

    borrowed_tokens: int
    total_tokens: int | float
    borrowers: list[Task | object]
    tasks_waiting: int


# Can be a generic type with a default of Task if/when PEP 696 is released
# and implemented in type checkers. Making it fully generic would currently
# introduce a lot of unnecessary hassle.
@final
class CapacityLimiter(AsyncContextManagerMixin):
    """An object for controlling access to a resource with limited capacity.

    Sometimes you need to put a limit on how many tasks can do something at
    the same time. For example, you might want to use some threads to run
    multiple blocking I/O operations in parallel... but if you use too many
    threads at once, then your system can become overloaded and it'll actually
    make things slower. One popular solution is to impose a policy like "run
    up to 40 threads at the same time, but no more". But how do you implement
    a policy like this?

    That's what :class:`CapacityLimiter` is for. You can think of a
    :class:`CapacityLimiter` object as a sack that starts out holding some fixed
    number of tokens::

       limit = trio.CapacityLimiter(40)

    Then tasks can come along and borrow a token out of the sack::

       # Borrow a token:
       async with limit:
           # We are holding a token!
           await perform_expensive_operation()
       # Exiting the 'async with' block puts the token back into the sack

    And crucially, if you try to borrow a token but the sack is empty, then
    you have to wait for another task to finish what it's doing and put its
    token back first before you can take it and continue.

    Another way to think of it: a :class:`CapacityLimiter` is like a sofa with a
    fixed number of seats, and if they're all taken then you have to wait for
    someone to get up before you can sit down.

    By default, :func:`trio.to_thread.run_sync` uses a
    :class:`CapacityLimiter` to limit the number of threads running at once;
    see `trio.to_thread.current_default_thread_limiter` for details.

    If you're familiar with semaphores, then you can think of this as a
    restricted semaphore that's specialized for one common use case, with
    additional error checking. For a more traditional semaphore, see
    :class:`Semaphore`.

    .. note::

       Don't confuse this with the `"leaky bucket"
       <https://en.wikipedia.org/wiki/Leaky_bucket>`__ or `"token bucket"
       <https://en.wikipedia.org/wiki/Token_bucket>`__ algorithms used to
       limit bandwidth usage on networks. The basic idea of using tokens to
       track a resource limit is similar, but this is a very simple sack where
       tokens aren't automatically created or destroyed over time; they're
       just borrowed and then put back.

    """

    # total_tokens would ideally be int|Literal[math.inf] - but that's not valid typing
    def __init__(self, total_tokens: int | float) -> None:  # noqa: PYI041
        self._lot = ParkingLot()
        self._borrowers: set[Task | object] = set()
        # Maps tasks attempting to acquire -> borrower, to handle on-behalf-of
        self._pending_borrowers: dict[Task, Task | object] = {}
        # invoke the property setter for validation
        self.total_tokens: int | float = total_tokens
        assert self._total_tokens == total_tokens

    def __repr__(self) -> str:
        return f"<trio.CapacityLimiter at {id(self):#x}, {len(self._borrowers)}/{self._total_tokens} with {len(self._lot)} waiting>"

    @property
    def total_tokens(self) -> int | float:
        """The total capacity available.

        You can change :attr:`total_tokens` by assigning to this attribute. If
        you make it larger, then the appropriate number of waiting tasks will
        be woken immediately to take the new tokens. If you decrease
        total_tokens below the number of tasks that are currently using the
        resource, then all current tasks will be allowed to finish as normal,
        but no new tasks will be allowed in until the total number of tasks
        drops below the new total_tokens.

        """
        return self._total_tokens

    @total_tokens.setter
    def total_tokens(self, new_total_tokens: int | float) -> None:  # noqa: PYI041
        if not isinstance(new_total_tokens, int) and new_total_tokens != math.inf:
            raise TypeError("total_tokens must be an int or math.inf")
        if new_total_tokens < 1:
            raise ValueError("total_tokens must be >= 1")
        self._total_tokens = new_total_tokens
        self._wake_waiters()

    def _wake_waiters(self) -> None:
        available = self._total_tokens - len(self._borrowers)
        for woken in self._lot.unpark(count=available):
            self._borrowers.add(self._pending_borrowers.pop(woken))

    @property
    def borrowed_tokens(self) -> int:
        """The amount of capacity that's currently in use."""
        return len(self._borrowers)

    @property
    def available_tokens(self) -> int | float:
        """The amount of capacity that's available to use."""
        return self.total_tokens - self.borrowed_tokens

    @enable_ki_protection
    def acquire_nowait(self) -> None:
        """Borrow a token from the sack, without blocking.

        Raises:
          WouldBlock: if no tokens are available.
          RuntimeError: if the current task already holds one of this sack's
              tokens.

        """
        self.acquire_on_behalf_of_nowait(trio.lowlevel.current_task())

    @enable_ki_protection
    def acquire_on_behalf_of_nowait(self, borrower: Task | object) -> None:
        """Borrow a token from the sack on behalf of ``borrower``, without
        blocking.

        Args:
          borrower: A :class:`trio.lowlevel.Task` or arbitrary opaque object
             used to record who is borrowing this token. This is used by
             :func:`trio.to_thread.run_sync` to allow threads to "hold
             tokens", with the intention in the future of using it to `allow
             deadlock detection and other useful things
             <https://github.com/python-trio/trio/issues/182>`__

        Raises:
          WouldBlock: if no tokens are available.
          RuntimeError: if ``borrower`` already holds one of this sack's
              tokens.

        """
        if borrower in self._borrowers:
            raise RuntimeError(
                "this borrower is already holding one of this CapacityLimiter's tokens",
            )
        if len(self._borrowers) < self._total_tokens and not self._lot:
            self._borrowers.add(borrower)
        else:
            raise trio.WouldBlock

    @enable_ki_protection
    async def acquire(self) -> None:
        """Borrow a token from the sack, blocking if necessary.

        Raises:
          RuntimeError: if the current task already holds one of this sack's
              tokens.

        """
        await self.acquire_on_behalf_of(trio.lowlevel.current_task())

    @enable_ki_protection
    async def acquire_on_behalf_of(self, borrower: Task | object) -> None:
        """Borrow a token from the sack on behalf of ``borrower``, blocking if
        necessary.

        Args:
          borrower: A :class:`trio.lowlevel.Task` or arbitrary opaque object
             used to record who is borrowing this token; see
             :meth:`acquire_on_behalf_of_nowait` for details.

        Raises:
          RuntimeError: if ``borrower`` task already holds one of this sack's
             tokens.

        """
        await trio.lowlevel.checkpoint_if_cancelled()
        try:
            self.acquire_on_behalf_of_nowait(borrower)
        except trio.WouldBlock:
            task = trio.lowlevel.current_task()
            self._pending_borrowers[task] = borrower
            try:
                await self._lot.park()
            except trio.Cancelled:
                self._pending_borrowers.pop(task)
                raise
        else:
            await trio.lowlevel.cancel_shielded_checkpoint()

    @enable_ki_protection
    def release(self) -> None:
        """Put a token back into the sack.

        Raises:
          RuntimeError: if the current task has not acquired one of this
              sack's tokens.

        """
        self.release_on_behalf_of(trio.lowlevel.current_task())

    @enable_ki_protection
    def release_on_behalf_of(self, borrower: Task | object) -> None:
        """Put a token back into the sack on behalf of ``borrower``.

        Raises:
          RuntimeError: if the given borrower has not acquired one of this
              sack's tokens.

        """
        if borrower not in self._borrowers:
            raise RuntimeError(
                "this borrower isn't holding any of this CapacityLimiter's tokens",
            )
        self._borrowers.remove(borrower)
        self._wake_waiters()

    def statistics(self) -> CapacityLimiterStatistics:
        """Return an object containing debugging information.

        Currently the following fields are defined:

        * ``borrowed_tokens``: The number of tokens currently borrowed from
          the sack.
        * ``total_tokens``: The total number of tokens in the sack. Usually
          this will be larger than ``borrowed_tokens``, but it's possibly for
          it to be smaller if :attr:`total_tokens` was recently decreased.
        * ``borrowers``: A list of all tasks or other entities that currently
          hold a token.
        * ``tasks_waiting``: The number of tasks blocked on this
          :class:`CapacityLimiter`\'s :meth:`acquire` or
          :meth:`acquire_on_behalf_of` methods.

        """
        return CapacityLimiterStatistics(
            borrowed_tokens=len(self._borrowers),
            total_tokens=self._total_tokens,
            # Use a list instead of a frozenset just in case we start to allow
            # one borrower to hold multiple tokens in the future
            borrowers=list(self._borrowers),
            tasks_waiting=len(self._lot),
        )


@final
class Semaphore(AsyncContextManagerMixin):
    """A `semaphore <https://en.wikipedia.org/wiki/Semaphore_(programming)>`__.

    A semaphore holds an integer value, which can be incremented by
    calling :meth:`release` and decremented by calling :meth:`acquire` – but
    the value is never allowed to drop below zero. If the value is zero, then
    :meth:`acquire` will block until someone calls :meth:`release`.

    If you're looking for a :class:`Semaphore` to limit the number of tasks
    that can access some resource simultaneously, then consider using a
    :class:`CapacityLimiter` instead.

    This object's interface is similar to, but different from, that of
    :class:`threading.Semaphore`.

    A :class:`Semaphore` object can be used as an async context manager; it
    blocks on entry but not on exit.

    Args:
      initial_value (int): A non-negative integer giving semaphore's initial
        value.
      max_value (int or None): If given, makes this a "bounded" semaphore that
        raises an error if the value is about to exceed the given
        ``max_value``.

    """

    def __init__(self, initial_value: int, *, max_value: int | None = None) -> None:
        if not isinstance(initial_value, int):
            raise TypeError("initial_value must be an int")
        if initial_value < 0:
            raise ValueError("initial value must be >= 0")
        if max_value is not None:
            if not isinstance(max_value, int):
                raise TypeError("max_value must be None or an int")
            if max_value < initial_value:
                raise ValueError("max_values must be >= initial_value")

        # Invariants:
        # bool(self._lot) implies self._value == 0
        # (or equivalently: self._value > 0 implies not self._lot)
        self._lot = trio.lowlevel.ParkingLot()
        self._value = initial_value
        self._max_value = max_value

    def __repr__(self) -> str:
        if self._max_value is None:
            max_value_str = ""
        else:
            max_value_str = f", max_value={self._max_value}"
        return f"<trio.Semaphore({self._value}{max_value_str}) at {id(self):#x}>"

    @property
    def value(self) -> int:
        """The current value of the semaphore."""
        return self._value

    @property
    def max_value(self) -> int | None:
        """The maximum allowed value. May be None to indicate no limit."""
        return self._max_value

    @enable_ki_protection
    def acquire_nowait(self) -> None:
        """Attempt to decrement the semaphore value, without blocking.

        Raises:
          WouldBlock: if the value is zero.

        """
        if self._value > 0:
            assert not self._lot
            self._value -= 1
        else:
            raise trio.WouldBlock

    @enable_ki_protection
    async def acquire(self) -> None:
        """Decrement the semaphore value, blocking if necessary to avoid
        letting it drop below zero.

        """
        await trio.lowlevel.checkpoint_if_cancelled()
        try:
            self.acquire_nowait()
        except trio.WouldBlock:
            await self._lot.park()
        else:
            await trio.lowlevel.cancel_shielded_checkpoint()

    @enable_ki_protection
    def release(self) -> None:
        """Increment the semaphore value, possibly waking a task blocked in
        :meth:`acquire`.

        Raises:
          ValueError: if incrementing the value would cause it to exceed
              :attr:`max_value`.

        """
        if self._lot:
            assert self._value == 0
            self._lot.unpark(count=1)
        else:
            if self._max_value is not None and self._value == self._max_value:
                raise ValueError("semaphore released too many times")
            self._value += 1

    def statistics(self) -> ParkingLotStatistics:
        """Return an object containing debugging information.

        Currently the following fields are defined:

        * ``tasks_waiting``: The number of tasks blocked on this semaphore's
          :meth:`acquire` method.

        """
        return self._lot.statistics()


@attrs.frozen
class LockStatistics:
    """An object containing debugging information for a Lock.

    Currently the following fields are defined:

    * ``locked`` (boolean): indicating whether the lock is held.
    * ``owner``: the :class:`trio.lowlevel.Task` currently holding the lock,
      or None if the lock is not held.
    * ``tasks_waiting`` (int): The number of tasks blocked on this lock's
      :meth:`trio.Lock.acquire` method.

    """

    locked: bool
    owner: Task | None
    tasks_waiting: int


@attrs.define(eq=False, repr=False, slots=False)
class _LockImpl(AsyncContextManagerMixin):
    _lot: ParkingLot = attrs.field(factory=ParkingLot, init=False)
    _owner: Task | None = attrs.field(default=None, init=False)

    def __repr__(self) -> str:
        if self.locked():
            s1 = "locked"
            s2 = f" with {len(self._lot)} waiters"
        else:
            s1 = "unlocked"
            s2 = ""
        return f"<{s1} {self.__class__.__name__} object at {id(self):#x}{s2}>"

    def locked(self) -> bool:
        """Check whether the lock is currently held.

        Returns:
          bool: True if the lock is held, False otherwise.

        """
        return self._owner is not None

    @enable_ki_protection
    def acquire_nowait(self) -> None:
        """Attempt to acquire the lock, without blocking.

        Raises:
          WouldBlock: if the lock is held.

        """

        task = trio.lowlevel.current_task()
        if self._owner is task:
            raise RuntimeError("attempt to re-acquire an already held Lock")
        elif self._owner is None and not self._lot:
            # No-one owns it
            self._owner = task
            add_parking_lot_breaker(task, self._lot)
        else:
            raise trio.WouldBlock

    @enable_ki_protection
    async def acquire(self) -> None:
        """Acquire the lock, blocking if necessary.

        Raises:
          BrokenResourceError: if the owner of the lock exits without releasing.
        """
        await trio.lowlevel.checkpoint_if_cancelled()
        try:
            self.acquire_nowait()
        except trio.WouldBlock:
            try:
                # NOTE: it's important that the contended acquire path is just
                # "_lot.park()", because that's how Condition.wait() acquires the
                # lock as well.
                await self._lot.park()
            except trio.BrokenResourceError:
                raise trio.BrokenResourceError(
                    f"Owner of this lock exited without releasing: {self._owner}",
                ) from None
        else:
            await trio.lowlevel.cancel_shielded_checkpoint()

    @enable_ki_protection
    def release(self) -> None:
        """Release the lock.

        Raises:
          RuntimeError: if the calling task does not hold the lock.

        """
        task = trio.lowlevel.current_task()
        if task is not self._owner:
            raise RuntimeError("can't release a Lock you don't own")
        remove_parking_lot_breaker(self._owner, self._lot)
        if self._lot:
            (self._owner,) = self._lot.unpark(count=1)
            add_parking_lot_breaker(self._owner, self._lot)
        else:
            self._owner = None

    def statistics(self) -> LockStatistics:
        """Return an object containing debugging information.

        Currently the following fields are defined:

        * ``locked``: boolean indicating whether the lock is held.
        * ``owner``: the :class:`trio.lowlevel.Task` currently holding the lock,
          or None if the lock is not held.
        * ``tasks_waiting``: The number of tasks blocked on this lock's
          :meth:`acquire` method.

        """
        return LockStatistics(
            locked=self.locked(),
            owner=self._owner,
            tasks_waiting=len(self._lot),
        )


@final
class Lock(_LockImpl):
    """A classic `mutex
    <https://en.wikipedia.org/wiki/Lock_(computer_science)>`__.

    This is a non-reentrant, single-owner lock. Unlike
    :class:`threading.Lock`, only the owner of the lock is allowed to release
    it.

    A :class:`Lock` object can be used as an async context manager; it
    blocks on entry but not on exit.

    """


@final
class StrictFIFOLock(_LockImpl):
    r"""A variant of :class:`Lock` where tasks are guaranteed to acquire the
    lock in strict first-come-first-served order.

    An example of when this is useful is if you're implementing something like
    :class:`trio.SSLStream` or an HTTP/2 server using `h2
    <https://hyper-h2.readthedocs.io/>`__, where you have multiple concurrent
    tasks that are interacting with a shared state machine, and at
    unpredictable moments the state machine requests that a chunk of data be
    sent over the network. (For example, when using h2 simply reading incoming
    data can occasionally `create outgoing data to send
    <https://http2.github.io/http2-spec/#PING>`__.) The challenge is to make
    sure that these chunks are sent in the correct order, without being
    garbled.

    One option would be to use a regular :class:`Lock`, and wrap it around
    every interaction with the state machine::

        # This approach is sometimes workable but often sub-optimal; see below
        async with lock:
            state_machine.do_something()
            if state_machine.has_data_to_send():
                await conn.sendall(state_machine.get_data_to_send())

    But this can be problematic. If you're using h2 then *usually* reading
    incoming data doesn't create the need to send any data, so we don't want
    to force every task that tries to read from the network to sit and wait
    a potentially long time for ``sendall`` to finish. And in some situations
    this could even potentially cause a deadlock, if the remote peer is
    waiting for you to read some data before it accepts the data you're
    sending.

    :class:`StrictFIFOLock` provides an alternative. We can rewrite our
    example like::

        # Note: no awaits between when we start using the state machine and
        # when we block to take the lock!
        state_machine.do_something()
        if state_machine.has_data_to_send():
            # Notice that we fetch the data to send out of the state machine
            # *before* sleeping, so that other tasks won't see it.
            chunk = state_machine.get_data_to_send()
            async with strict_fifo_lock:
                await conn.sendall(chunk)

    First we do all our interaction with the state machine in a single
    scheduling quantum (notice there are no ``await``\s in there), so it's
    automatically atomic with respect to other tasks. And then if and only if
    we have data to send, we get in line to send it – and
    :class:`StrictFIFOLock` guarantees that each task will send its data in
    the same order that the state machine generated it.

    Currently, :class:`StrictFIFOLock` is identical to :class:`Lock`,
    but (a) this may not always be true in the future, especially if Trio ever
    implements `more sophisticated scheduling policies
    <https://github.com/python-trio/trio/issues/32>`__, and (b) the above code
    is relying on a pretty subtle property of its lock. Using a
    :class:`StrictFIFOLock` acts as an executable reminder that you're relying
    on this property.

    """


@attrs.frozen
class ConditionStatistics:
    r"""An object containing debugging information for a Condition.

    Currently the following fields are defined:

    * ``tasks_waiting`` (int): The number of tasks blocked on this condition's
      :meth:`trio.Condition.wait` method.
    * ``lock_statistics``: The result of calling the underlying
      :class:`Lock`\s  :meth:`~Lock.statistics` method.

    """

    tasks_waiting: int
    lock_statistics: LockStatistics


@final
class Condition(AsyncContextManagerMixin):
    """A classic `condition variable
    <https://en.wikipedia.org/wiki/Monitor_(synchronization)>`__, similar to
    :class:`threading.Condition`.

    A :class:`Condition` object can be used as an async context manager to
    acquire the underlying lock; it blocks on entry but not on exit.

    Args:
      lock (Lock): the lock object to use. If given, must be a
          :class:`trio.Lock`. If None, a new :class:`Lock` will be allocated
          and used.

    """

    def __init__(self, lock: Lock | None = None) -> None:
        if lock is None:
            lock = Lock()
        if type(lock) is not Lock:
            raise TypeError("lock must be a trio.Lock")
        self._lock = lock
        self._lot = trio.lowlevel.ParkingLot()

    def locked(self) -> bool:
        """Check whether the underlying lock is currently held.

        Returns:
          bool: True if the lock is held, False otherwise.

        """
        return self._lock.locked()

    def acquire_nowait(self) -> None:
        """Attempt to acquire the underlying lock, without blocking.

        Raises:
          WouldBlock: if the lock is currently held.

        """
        return self._lock.acquire_nowait()

    async def acquire(self) -> None:
        """Acquire the underlying lock, blocking if necessary.

        Raises:
          BrokenResourceError: if the owner of the underlying lock exits without releasing.
        """
        await self._lock.acquire()

    def release(self) -> None:
        """Release the underlying lock."""
        self._lock.release()

    @enable_ki_protection
    async def wait(self) -> None:
        """Wait for another task to call :meth:`notify` or
        :meth:`notify_all`.

        When calling this method, you must hold the lock. It releases the lock
        while waiting, and then re-acquires it before waking up.

        There is a subtlety with how this method interacts with cancellation:
        when cancelled it will block to re-acquire the lock before raising
        :exc:`Cancelled`. This may cause cancellation to be less prompt than
        expected. The advantage is that it makes code like this work::

           async with condition:
               await condition.wait()

        If we didn't re-acquire the lock before waking up, and :meth:`wait`
        were cancelled here, then we'd crash in ``condition.__aexit__`` when
        we tried to release the lock we no longer held.

        Raises:
          RuntimeError: if the calling task does not hold the lock.
          BrokenResourceError: if the owner of the lock exits without releasing, when attempting to re-acquire.

        """
        if trio.lowlevel.current_task() is not self._lock._owner:
            raise RuntimeError("must hold the lock to wait")
        self.release()
        # NOTE: we go to sleep on self._lot, but we'll wake up on
        # self._lock._lot. That's all that's required to acquire a Lock.
        try:
            await self._lot.park()
        except:
            with trio.CancelScope(shield=True):
                await self.acquire()
            raise

    def notify(self, n: int = 1) -> None:
        """Wake one or more tasks that are blocked in :meth:`wait`.

        Args:
          n (int): The number of tasks to wake.

        Raises:
          RuntimeError: if the calling task does not hold the lock.

        """
        if trio.lowlevel.current_task() is not self._lock._owner:
            raise RuntimeError("must hold the lock to notify")
        self._lot.repark(self._lock._lot, count=n)

    def notify_all(self) -> None:
        """Wake all tasks that are currently blocked in :meth:`wait`.

        Raises:
          RuntimeError: if the calling task does not hold the lock.

        """
        if trio.lowlevel.current_task() is not self._lock._owner:
            raise RuntimeError("must hold the lock to notify")
        self._lot.repark_all(self._lock._lot)

    def statistics(self) -> ConditionStatistics:
        r"""Return an object containing debugging information.

        Currently the following fields are defined:

        * ``tasks_waiting``: The number of tasks blocked on this condition's
          :meth:`wait` method.
        * ``lock_statistics``: The result of calling the underlying
          :class:`Lock`\s  :meth:`~Lock.statistics` method.

        """
        return ConditionStatistics(
            tasks_waiting=len(self._lot),
            lock_statistics=self._lock.statistics(),
        )

# === NexusCore/openenv\Lib\site-packages\google\generativeai\generative_models.py ===
"""Classes for working with the Gemini models."""

from __future__ import annotations

from collections.abc import Iterable
import textwrap
from typing import Any, Union, overload
import reprlib

# pylint: disable=bad-continuation, line-too-long


import google.api_core.exceptions
from google.generativeai import protos
from google.generativeai import client

from google.generativeai import caching
from google.generativeai.types import content_types
from google.generativeai.types import generation_types
from google.generativeai.types import helper_types
from google.generativeai.types import safety_types

_USER_ROLE = "user"
_MODEL_ROLE = "model"


class GenerativeModel:
    """
    The `genai.GenerativeModel` class wraps default parameters for calls to
    `GenerativeModel.generate_content`, `GenerativeModel.count_tokens`, and
    `GenerativeModel.start_chat`.

    This family of functionality is designed to support multi-turn conversations, and multimodal
    requests. What media-types are supported for input and output is model-dependant.

    >>> import google.generativeai as genai
    >>> import PIL.Image
    >>> genai.configure(api_key='YOUR_API_KEY')
    >>> model = genai.GenerativeModel('models/gemini-pro')
    >>> result = model.generate_content('Tell me a story about a magic backpack')
    >>> result.text
    "In the quaint little town of Lakeside, there lived a young girl named Lily..."

    Multimodal input:

    >>> model = genai.GenerativeModel('models/gemini-pro')
    >>> result = model.generate_content([
    ...     "Give me a recipe for these:", PIL.Image.open('scones.jpeg')])
    >>> result.text
    "**Blueberry Scones** ..."

    Multi-turn conversation:

    >>> chat = model.start_chat()
    >>> response = chat.send_message("Hi, I have some questions for you.")
    >>> response.text
    "Sure, I'll do my best to answer your questions..."

    To list the compatible model names use:

    >>> for m in genai.list_models():
    ...     if 'generateContent' in m.supported_generation_methods:
    ...         print(m.name)

    Arguments:
         model_name: The name of the model to query. To list compatible models use
         safety_settings: Sets the default safety filters. This controls which content is blocked
             by the api before being returned.
         generation_config: A `genai.GenerationConfig` setting the default generation parameters to
             use.
    """

    def __init__(
        self,
        model_name: str = "gemini-pro",
        safety_settings: safety_types.SafetySettingOptions | None = None,
        generation_config: generation_types.GenerationConfigType | None = None,
        tools: content_types.FunctionLibraryType | None = None,
        tool_config: content_types.ToolConfigType | None = None,
        system_instruction: content_types.ContentType | None = None,
    ):
        if "/" not in model_name:
            model_name = "models/" + model_name
        self._model_name = model_name
        self._safety_settings = safety_types.to_easy_safety_dict(safety_settings)
        self._generation_config = generation_types.to_generation_config_dict(generation_config)
        self._tools = content_types.to_function_library(tools)

        if tool_config is None:
            self._tool_config = None
        else:
            self._tool_config = content_types.to_tool_config(tool_config)

        if system_instruction is None:
            self._system_instruction = None
        else:
            self._system_instruction = content_types.to_content(system_instruction)

        self._client = None
        self._async_client = None

    @property
    def cached_content(self) -> str:
        return getattr(self, "_cached_content", None)

    @property
    def model_name(self):
        return self._model_name

    def __str__(self):
        def maybe_text(content):
            if content and len(content.parts) and (t := content.parts[0].text):
                return repr(t)
            return content

        return textwrap.dedent(
            f"""\
            genai.GenerativeModel(
                model_name='{self.model_name}',
                generation_config={self._generation_config},
                safety_settings={self._safety_settings},
                tools={self._tools},
                system_instruction={maybe_text(self._system_instruction)},
                cached_content={self.cached_content}
            )"""
        )

    __repr__ = __str__

    def _prepare_request(
        self,
        *,
        contents: content_types.ContentsType,
        generation_config: generation_types.GenerationConfigType | None = None,
        safety_settings: safety_types.SafetySettingOptions | None = None,
        tools: content_types.FunctionLibraryType | None,
        tool_config: content_types.ToolConfigType | None,
    ) -> protos.GenerateContentRequest:
        """Creates a `protos.GenerateContentRequest` from raw inputs."""
        if hasattr(self, "_cached_content") and any([self._system_instruction, tools, tool_config]):
            raise ValueError(
                "`tools`, `tool_config`, `system_instruction` cannot be set on a model instantiated with `cached_content` as its context."
            )

        tools_lib = self._get_tools_lib(tools)
        if tools_lib is not None:
            tools_lib = tools_lib.to_proto()

        if tool_config is None:
            tool_config = self._tool_config
        else:
            tool_config = content_types.to_tool_config(tool_config)

        contents = content_types.to_contents(contents)

        generation_config = generation_types.to_generation_config_dict(generation_config)
        merged_gc = self._generation_config.copy()
        merged_gc.update(generation_config)

        safety_settings = safety_types.to_easy_safety_dict(safety_settings)
        merged_ss = self._safety_settings.copy()
        merged_ss.update(safety_settings)
        merged_ss = safety_types.normalize_safety_settings(merged_ss)

        return protos.GenerateContentRequest(
            model=self._model_name,
            contents=contents,
            generation_config=merged_gc,
            safety_settings=merged_ss,
            tools=tools_lib,
            tool_config=tool_config,
            system_instruction=self._system_instruction,
            cached_content=self.cached_content,
        )

    def _get_tools_lib(
        self, tools: content_types.FunctionLibraryType
    ) -> content_types.FunctionLibrary | None:
        if tools is None:
            return self._tools
        else:
            return content_types.to_function_library(tools)

    @overload
    @classmethod
    def from_cached_content(
        cls,
        cached_content: str,
        *,
        generation_config: generation_types.GenerationConfigType | None = None,
        safety_settings: safety_types.SafetySettingOptions | None = None,
    ) -> GenerativeModel: ...

    @overload
    @classmethod
    def from_cached_content(
        cls,
        cached_content: caching.CachedContent,
        *,
        generation_config: generation_types.GenerationConfigType | None = None,
        safety_settings: safety_types.SafetySettingOptions | None = None,
    ) -> GenerativeModel: ...

    @classmethod
    def from_cached_content(
        cls,
        cached_content: str | caching.CachedContent,
        *,
        generation_config: generation_types.GenerationConfigType | None = None,
        safety_settings: safety_types.SafetySettingOptions | None = None,
    ) -> GenerativeModel:
        """Creates a model with `cached_content` as model's context.

        Args:
            cached_content: context for the model.
            generation_config: Overrides for the model's generation config.
            safety_settings: Overrides for the model's safety settings.

        Returns:
            `GenerativeModel` object with `cached_content` as its context.
        """
        if isinstance(cached_content, str):
            cached_content = caching.CachedContent.get(name=cached_content)

        # call __init__ to set the model's `generation_config`, `safety_settings`.
        # `model_name` will be the name of the model for which the `cached_content` was created.
        self = cls(
            model_name=cached_content.model,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

        # set the model's context.
        setattr(self, "_cached_content", cached_content.name)
        return self

    def generate_content(
        self,
        contents: content_types.ContentsType,
        *,
        generation_config: generation_types.GenerationConfigType | None = None,
        safety_settings: safety_types.SafetySettingOptions | None = None,
        stream: bool = False,
        tools: content_types.FunctionLibraryType | None = None,
        tool_config: content_types.ToolConfigType | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> generation_types.GenerateContentResponse:
        """A multipurpose function to generate responses from the model.

        This `GenerativeModel.generate_content` method can handle multimodal input, and multi-turn
        conversations.

        >>> model = genai.GenerativeModel('models/gemini-pro')
        >>> response = model.generate_content('Tell me a story about a magic backpack')
        >>> response.text

        ### Streaming

        This method supports streaming with the `stream=True`. The result has the same type as the non streaming case,
        but you can iterate over the response chunks as they become available:

        >>> response = model.generate_content('Tell me a story about a magic backpack', stream=True)
        >>> for chunk in response:
        ...   print(chunk.text)

        ### Multi-turn

        This method supports multi-turn chats but is **stateless**: the entire conversation history needs to be sent with each
        request. This takes some manual management but gives you complete control:

        >>> messages = [{'role':'user', 'parts': ['hello']}]
        >>> response = model.generate_content(messages) # "Hello, how can I help"
        >>> messages.append(response.candidates[0].content)
        >>> messages.append({'role':'user', 'parts': ['How does quantum physics work?']})
        >>> response = model.generate_content(messages)

        For a simpler multi-turn interface see `GenerativeModel.start_chat`.

        ### Input type flexibility

        While the underlying API strictly expects a `list[protos.Content]` objects, this method
        will convert the user input into the correct type. The hierarchy of types that can be
        converted is below. Any of these objects can be passed as an equivalent `dict`.

        * `Iterable[protos.Content]`
        * `protos.Content`
        * `Iterable[protos.Part]`
        * `protos.Part`
        * `str`, `Image`, or `protos.Blob`

        In an `Iterable[protos.Content]` each `content` is a separate message.
        But note that an `Iterable[protos.Part]` is taken as the parts of a single message.

        Arguments:
            contents: The contents serving as the model's prompt.
            generation_config: Overrides for the model's generation config.
            safety_settings: Overrides for the model's safety settings.
            stream: If True, yield response chunks as they are generated.
            tools: `protos.Tools` more info coming soon.
            request_options: Options for the request.
        """
        if not contents:
            raise TypeError("contents must not be empty")

        request = self._prepare_request(
            contents=contents,
            generation_config=generation_config,
            safety_settings=safety_settings,
            tools=tools,
            tool_config=tool_config,
        )

        if request.contents and not request.contents[-1].role:
            request.contents[-1].role = _USER_ROLE

        if self._client is None:
            self._client = client.get_default_generative_client()

        if request_options is None:
            request_options = {}

        try:
            if stream:
                with generation_types.rewrite_stream_error():
                    iterator = self._client.stream_generate_content(
                        request,
                        **request_options,
                    )
                return generation_types.GenerateContentResponse.from_iterator(iterator)
            else:
                response = self._client.generate_content(
                    request,
                    **request_options,
                )
                return generation_types.GenerateContentResponse.from_response(response)
        except google.api_core.exceptions.InvalidArgument as e:
            if e.message.startswith("Request payload size exceeds the limit:"):
                e.message += (
                    " The file size is too large. Please use the File API to upload your files instead. "
                    "Example: `f = genai.upload_file(path); m.generate_content(['tell me about this file:', f])`"
                )
            raise

    async def generate_content_async(
        self,
        contents: content_types.ContentsType,
        *,
        generation_config: generation_types.GenerationConfigType | None = None,
        safety_settings: safety_types.SafetySettingOptions | None = None,
        stream: bool = False,
        tools: content_types.FunctionLibraryType | None = None,
        tool_config: content_types.ToolConfigType | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> generation_types.AsyncGenerateContentResponse:
        """The async version of `GenerativeModel.generate_content`."""
        if not contents:
            raise TypeError("contents must not be empty")

        request = self._prepare_request(
            contents=contents,
            generation_config=generation_config,
            safety_settings=safety_settings,
            tools=tools,
            tool_config=tool_config,
        )

        if request.contents and not request.contents[-1].role:
            request.contents[-1].role = _USER_ROLE

        if self._async_client is None:
            self._async_client = client.get_default_generative_async_client()

        if request_options is None:
            request_options = {}

        try:
            if stream:
                with generation_types.rewrite_stream_error():
                    iterator = await self._async_client.stream_generate_content(
                        request,
                        **request_options,
                    )
                return await generation_types.AsyncGenerateContentResponse.from_aiterator(iterator)
            else:
                response = await self._async_client.generate_content(
                    request,
                    **request_options,
                )
                return generation_types.AsyncGenerateContentResponse.from_response(response)
        except google.api_core.exceptions.InvalidArgument as e:
            if e.message.startswith("Request payload size exceeds the limit:"):
                e.message += (
                    " The file size is too large. Please use the File API to upload your files instead. "
                    "Example: `f = genai.upload_file(path); m.generate_content(['tell me about this file:', f])`"
                )
            raise

    # fmt: off
    def count_tokens(
        self,
        contents: content_types.ContentsType = None,
        *,
        generation_config: generation_types.GenerationConfigType | None = None,
        safety_settings: safety_types.SafetySettingOptions | None = None,
        tools: content_types.FunctionLibraryType | None = None,
        tool_config: content_types.ToolConfigType | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> protos.CountTokensResponse:
        if request_options is None:
            request_options = {}

        if self._client is None:
            self._client = client.get_default_generative_client()

        request = protos.CountTokensRequest(
            model=self.model_name,
            generate_content_request=self._prepare_request(
                contents=contents,
                generation_config=generation_config,
                safety_settings=safety_settings,
                tools=tools,
                tool_config=tool_config,
        ))
        return self._client.count_tokens(request, **request_options)

    async def count_tokens_async(
        self,
        contents: content_types.ContentsType = None,
        *,
        generation_config: generation_types.GenerationConfigType | None = None,
        safety_settings: safety_types.SafetySettingOptions | None = None,
        tools: content_types.FunctionLibraryType | None = None,
        tool_config: content_types.ToolConfigType | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> protos.CountTokensResponse:
        if request_options is None:
            request_options = {}

        if self._async_client is None:
            self._async_client = client.get_default_generative_async_client()

        request = protos.CountTokensRequest(
            model=self.model_name,
            generate_content_request=self._prepare_request(
                contents=contents,
                generation_config=generation_config,
                safety_settings=safety_settings,
                tools=tools,
                tool_config=tool_config,
        ))
        return await self._async_client.count_tokens(request, **request_options)

    # fmt: on

    def start_chat(
        self,
        *,
        history: Iterable[content_types.StrictContentType] | None = None,
        enable_automatic_function_calling: bool = False,
    ) -> ChatSession:
        """Returns a `genai.ChatSession` attached to this model.

        >>> model = genai.GenerativeModel()
        >>> chat = model.start_chat(history=[...])
        >>> response = chat.send_message("Hello?")

        Arguments:
            history: An iterable of `protos.Content` objects, or equivalents to initialize the session.
        """
        if self._generation_config.get("candidate_count", 1) > 1:
            raise ValueError(
                "Invalid configuration: The chat functionality does not support `candidate_count` greater than 1."
            )
        return ChatSession(
            model=self,
            history=history,
            enable_automatic_function_calling=enable_automatic_function_calling,
        )


class ChatSession:
    """Contains an ongoing conversation with the model.

    >>> model = genai.GenerativeModel('models/gemini-pro')
    >>> chat = model.start_chat()
    >>> response = chat.send_message("Hello")
    >>> print(response.text)
    >>> response = chat.send_message("Hello again")
    >>> print(response.text)
    >>> response = chat.send_message(...

    This `ChatSession` object collects the messages sent and received, in its
    `ChatSession.history` attribute.

    Arguments:
        model: The model to use in the chat.
        history: A chat history to initialize the object with.
    """

    def __init__(
        self,
        model: GenerativeModel,
        history: Iterable[content_types.StrictContentType] | None = None,
        enable_automatic_function_calling: bool = False,
    ):
        self.model: GenerativeModel = model
        self._history: list[protos.Content] = content_types.to_contents(history)
        self._last_sent: protos.Content | None = None
        self._last_received: generation_types.BaseGenerateContentResponse | None = None
        self.enable_automatic_function_calling = enable_automatic_function_calling

    def send_message(
        self,
        content: content_types.ContentType,
        *,
        generation_config: generation_types.GenerationConfigType = None,
        safety_settings: safety_types.SafetySettingOptions = None,
        stream: bool = False,
        tools: content_types.FunctionLibraryType | None = None,
        tool_config: content_types.ToolConfigType | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> generation_types.GenerateContentResponse:
        """Sends the conversation history with the added message and returns the model's response.

        Appends the request and response to the conversation history.

        >>> model = genai.GenerativeModel('models/gemini-pro')
        >>> chat = model.start_chat()
        >>> response = chat.send_message("Hello")
        >>> print(response.text)
        "Hello! How can I assist you today?"
        >>> len(chat.history)
        2

        Call it with `stream=True` to receive response chunks as they are generated:

        >>> chat = model.start_chat()
        >>> response = chat.send_message("Explain quantum physics", stream=True)
        >>> for chunk in response:
        ...   print(chunk.text, end='')

        Once iteration over chunks is complete, the `response` and `ChatSession` are in states identical to the
        `stream=False` case. Some properties are not available until iteration is complete.

        Like `GenerativeModel.generate_content` this method lets you override the model's `generation_config` and
        `safety_settings`.

        Arguments:
             content: The message contents.
             generation_config: Overrides for the model's generation config.
             safety_settings: Overrides for the model's safety settings.
             stream: If True, yield response chunks as they are generated.
        """
        if request_options is None:
            request_options = {}

        if self.enable_automatic_function_calling and stream:
            raise NotImplementedError(
                "Unsupported configuration: The `google.generativeai` SDK currently does not support the combination of `stream=True` and `enable_automatic_function_calling=True`."
            )

        tools_lib = self.model._get_tools_lib(tools)

        content = content_types.to_content(content)

        if not content.role:
            content.role = _USER_ROLE

        history = self.history[:]
        history.append(content)

        generation_config = generation_types.to_generation_config_dict(generation_config)
        if generation_config.get("candidate_count", 1) > 1:
            raise ValueError(
                "Invalid configuration: The chat functionality does not support `candidate_count` greater than 1."
            )

        response = self.model.generate_content(
            contents=history,
            generation_config=generation_config,
            safety_settings=safety_settings,
            stream=stream,
            tools=tools_lib,
            tool_config=tool_config,
            request_options=request_options,
        )

        self._check_response(response=response, stream=stream)

        if self.enable_automatic_function_calling and tools_lib is not None:
            self.history, content, response = self._handle_afc(
                response=response,
                history=history,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=stream,
                tools_lib=tools_lib,
                request_options=request_options,
            )

        self._last_sent = content
        self._last_received = response

        return response

    def _check_response(self, *, response, stream):
        if response.prompt_feedback.block_reason:
            raise generation_types.BlockedPromptException(response.prompt_feedback)

        if not stream:
            if response.candidates[0].finish_reason not in (
                protos.Candidate.FinishReason.FINISH_REASON_UNSPECIFIED,
                protos.Candidate.FinishReason.STOP,
                protos.Candidate.FinishReason.MAX_TOKENS,
            ):
                raise generation_types.StopCandidateException(response.candidates[0])

    def _get_function_calls(self, response) -> list[protos.FunctionCall]:
        candidates = response.candidates
        if len(candidates) != 1:
            raise ValueError(
                f"Invalid number of candidates: Automatic function calling only works with 1 candidate, but {len(candidates)} were provided."
            )
        parts = candidates[0].content.parts
        function_calls = [part.function_call for part in parts if part and "function_call" in part]
        return function_calls

    def _handle_afc(
        self,
        *,
        response,
        history,
        generation_config,
        safety_settings,
        stream,
        tools_lib,
        request_options,
    ) -> tuple[list[protos.Content], protos.Content, generation_types.BaseGenerateContentResponse]:

        while function_calls := self._get_function_calls(response):
            if not all(callable(tools_lib[fc]) for fc in function_calls):
                break
            history.append(response.candidates[0].content)

            function_response_parts: list[protos.Part] = []
            for fc in function_calls:
                fr = tools_lib(fc)
                assert fr is not None, (
                    "Unexpected state: The function reference (fr) should never be None. It should only return None if the declaration "
                    "is not callable, which is checked earlier in the code."
                )
                function_response_parts.append(fr)

            send = protos.Content(role=_USER_ROLE, parts=function_response_parts)
            history.append(send)

            response = self.model.generate_content(
                contents=history,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=stream,
                tools=tools_lib,
                request_options=request_options,
            )

            self._check_response(response=response, stream=stream)

        *history, content = history
        return history, content, response

    async def send_message_async(
        self,
        content: content_types.ContentType,
        *,
        generation_config: generation_types.GenerationConfigType = None,
        safety_settings: safety_types.SafetySettingOptions = None,
        stream: bool = False,
        tools: content_types.FunctionLibraryType | None = None,
        tool_config: content_types.ToolConfigType | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> generation_types.AsyncGenerateContentResponse:
        """The async version of `ChatSession.send_message`."""
        if request_options is None:
            request_options = {}

        if self.enable_automatic_function_calling and stream:
            raise NotImplementedError(
                "Unsupported configuration: The `google.generativeai` SDK currently does not support the combination of `stream=True` and `enable_automatic_function_calling=True`."
            )

        tools_lib = self.model._get_tools_lib(tools)

        content = content_types.to_content(content)

        if not content.role:
            content.role = _USER_ROLE

        history = self.history[:]
        history.append(content)

        generation_config = generation_types.to_generation_config_dict(generation_config)
        if generation_config.get("candidate_count", 1) > 1:
            raise ValueError(
                "Invalid configuration: The chat functionality does not support `candidate_count` greater than 1."
            )

        response = await self.model.generate_content_async(
            contents=history,
            generation_config=generation_config,
            safety_settings=safety_settings,
            stream=stream,
            tools=tools_lib,
            tool_config=tool_config,
            request_options=request_options,
        )

        self._check_response(response=response, stream=stream)

        if self.enable_automatic_function_calling and tools_lib is not None:
            self.history, content, response = await self._handle_afc_async(
                response=response,
                history=history,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=stream,
                tools_lib=tools_lib,
                request_options=request_options,
            )

        self._last_sent = content
        self._last_received = response

        return response

    async def _handle_afc_async(
        self,
        *,
        response,
        history,
        generation_config,
        safety_settings,
        stream,
        tools_lib,
        request_options,
    ) -> tuple[list[protos.Content], protos.Content, generation_types.BaseGenerateContentResponse]:

        while function_calls := self._get_function_calls(response):
            if not all(callable(tools_lib[fc]) for fc in function_calls):
                break
            history.append(response.candidates[0].content)

            function_response_parts: list[protos.Part] = []
            for fc in function_calls:
                fr = tools_lib(fc)
                assert fr is not None, (
                    "Unexpected state: The function reference (fr) should never be None. It should only return None if the declaration "
                    "is not callable, which is checked earlier in the code."
                )
                function_response_parts.append(fr)

            send = protos.Content(role=_USER_ROLE, parts=function_response_parts)
            history.append(send)

            response = await self.model.generate_content_async(
                contents=history,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=stream,
                tools=tools_lib,
                request_options=request_options,
            )

            self._check_response(response=response, stream=stream)

        *history, content = history
        return history, content, response

    def __copy__(self):
        return ChatSession(
            model=self.model,
            # Be sure the copy doesn't share the history.
            history=list(self.history),
        )

    def rewind(self) -> tuple[protos.Content, protos.Content]:
        """Removes the last request/response pair from the chat history."""
        if self._last_received is None:
            result = self._history.pop(-2), self._history.pop()
            return result
        else:
            result = self._last_sent, self._last_received.candidates[0].content
            self._last_sent = None
            self._last_received = None
            return result

    @property
    def last(self) -> generation_types.BaseGenerateContentResponse | None:
        """returns the last received `genai.GenerateContentResponse`"""
        return self._last_received

    @property
    def history(self) -> list[protos.Content]:
        """The chat history."""
        last = self._last_received
        if last is None:
            return self._history

        if last.candidates[0].finish_reason not in (
            protos.Candidate.FinishReason.FINISH_REASON_UNSPECIFIED,
            protos.Candidate.FinishReason.STOP,
            protos.Candidate.FinishReason.MAX_TOKENS,
        ):
            error = generation_types.StopCandidateException(last.candidates[0])
            last._error = error

        if last._error is not None:
            raise generation_types.BrokenResponseError(
                "Unable to build a coherent chat history due to a broken streaming response. "
                "Refer to the previous exception for details. "
                "To inspect the last response object, use `chat.last`. "
                "To remove the last request/response `Content` objects from the chat, "
                "call `last_send, last_received = chat.rewind()` and continue without it."
            ) from last._error

        sent = self._last_sent
        received = last.candidates[0].content
        if not received.role:
            received.role = _MODEL_ROLE
        self._history.extend([sent, received])

        self._last_sent = None
        self._last_received = None

        return self._history

    @history.setter
    def history(self, history):
        self._history = content_types.to_contents(history)
        self._last_sent = None
        self._last_received = None

    def __repr__(self) -> str:
        _dict_repr = reprlib.Repr()
        _model = str(self.model).replace("\n", "\n" + " " * 4)

        def content_repr(x):
            return f"protos.Content({_dict_repr.repr(type(x).to_dict(x))})"

        try:
            history = list(self.history)
        except (generation_types.BrokenResponseError, generation_types.IncompleteIterationError):
            history = list(self._history)

        if self._last_sent is not None:
            history.append(self._last_sent)
        history = [content_repr(x) for x in history]

        last_received = self._last_received
        if last_received is not None:
            if last_received._error is not None:
                history.append("<STREAMING ERROR>")
            else:
                history.append("<STREAMING IN PROGRESS>")

        _history = ",\n    " + f"history=[{', '.join(history)}]\n)"

        return (
            textwrap.dedent(
                f"""\
                ChatSession(
                    model="""
            )
            + _model
            + _history
        )

# === NexusCore/openenv\Lib\site-packages\google\generativeai\types\content_types.py ===
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


from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import io
import inspect
import mimetypes
import typing
from typing import Any, Callable, Union
from typing_extensions import TypedDict

import pydantic

from google.generativeai.types import file_types
from google.generativeai import protos

if typing.TYPE_CHECKING:
    import PIL.Image
    import PIL.PngImagePlugin
    import IPython.display

    IMAGE_TYPES = (PIL.Image.Image, IPython.display.Image)
else:
    IMAGE_TYPES = ()
    try:
        import PIL.Image
        import PIL.PngImagePlugin

        IMAGE_TYPES = IMAGE_TYPES + (PIL.Image.Image,)
    except ImportError:
        PIL = None

    try:
        import IPython.display

        IMAGE_TYPES = IMAGE_TYPES + (IPython.display.Image,)
    except ImportError:
        IPython = None


__all__ = [
    "BlobDict",
    "BlobType",
    "PartDict",
    "PartType",
    "ContentDict",
    "ContentType",
    "StrictContentType",
    "ContentsType",
    "FunctionDeclaration",
    "CallableFunctionDeclaration",
    "FunctionDeclarationType",
    "Tool",
    "ToolDict",
    "ToolsType",
    "FunctionLibrary",
    "FunctionLibraryType",
]


def pil_to_blob(img):
    bytesio = io.BytesIO()
    if isinstance(img, PIL.PngImagePlugin.PngImageFile) or img.mode == "RGBA":
        img.save(bytesio, format="PNG")
        mime_type = "image/png"
    else:
        img.save(bytesio, format="JPEG")
        mime_type = "image/jpeg"
    bytesio.seek(0)
    data = bytesio.read()
    return protos.Blob(mime_type=mime_type, data=data)


def image_to_blob(image) -> protos.Blob:
    if PIL is not None:
        if isinstance(image, PIL.Image.Image):
            return pil_to_blob(image)

    if IPython is not None:
        if isinstance(image, IPython.display.Image):
            name = image.filename
            if name is None:
                raise ValueError(
                    "Conversion failed. The `IPython.display.Image` can only be converted if "
                    "it is constructed from a local file. Please ensure you are using the format: Image(filename='...')."
                )
            mime_type, _ = mimetypes.guess_type(name)
            if mime_type is None:
                mime_type = "image/unknown"

            return protos.Blob(mime_type=mime_type, data=image.data)

    raise TypeError(
        "Image conversion failed. The input was expected to be of type `Image` "
        "(either `PIL.Image.Image` or `IPython.display.Image`).\n"
        f"However, received an object of type: {type(image)}.\n"
        f"Object Value: {image}"
    )


class BlobDict(TypedDict):
    mime_type: str
    data: bytes


def _convert_dict(d: Mapping) -> protos.Content | protos.Part | protos.Blob:
    if is_content_dict(d):
        content = dict(d)
        if isinstance(parts := content["parts"], str):
            content["parts"] = [parts]
        content["parts"] = [to_part(part) for part in content["parts"]]
        return protos.Content(content)
    elif is_part_dict(d):
        part = dict(d)
        if "inline_data" in part:
            part["inline_data"] = to_blob(part["inline_data"])
        if "file_data" in part:
            part["file_data"] = file_types.to_file_data(part["file_data"])
        return protos.Part(part)
    elif is_blob_dict(d):
        blob = d
        return protos.Blob(blob)
    else:
        raise KeyError(
            "Unable to determine the intended type of the `dict`. "
            "For `Content`, a 'parts' key is expected. "
            "For `Part`, either an 'inline_data' or a 'text' key is expected. "
            "For `Blob`, both 'mime_type' and 'data' keys are expected. "
            f"However, the provided dictionary has the following keys: {list(d.keys())}"
        )


def is_blob_dict(d):
    return "mime_type" in d and "data" in d


if typing.TYPE_CHECKING:
    BlobType = Union[
        protos.Blob, BlobDict, PIL.Image.Image, IPython.display.Image
    ]  # Any for the images
else:
    BlobType = Union[protos.Blob, BlobDict, Any]


def to_blob(blob: BlobType) -> protos.Blob:
    if isinstance(blob, Mapping):
        blob = _convert_dict(blob)

    if isinstance(blob, protos.Blob):
        return blob
    elif isinstance(blob, IMAGE_TYPES):
        return image_to_blob(blob)
    else:
        if isinstance(blob, Mapping):
            raise KeyError(
                "Could not recognize the intended type of the `dict`\n" "A content should have "
            )
        raise TypeError(
            "Could not create `Blob`, expected `Blob`, `dict` or an `Image` type"
            "(`PIL.Image.Image` or `IPython.display.Image`).\n"
            f"Got a: {type(blob)}\n"
            f"Value: {blob}"
        )


class PartDict(TypedDict):
    text: str
    inline_data: BlobType


# When you need a `Part` accept a part object, part-dict, blob or string
PartType = Union[
    protos.Part,
    PartDict,
    BlobType,
    str,
    protos.FunctionCall,
    protos.FunctionResponse,
    file_types.FileDataType,
]


def is_part_dict(d):
    keys = list(d.keys())
    if len(keys) != 1:
        return False

    key = keys[0]

    return key in ["text", "inline_data", "function_call", "function_response", "file_data"]


def to_part(part: PartType):
    if isinstance(part, Mapping):
        part = _convert_dict(part)

    if isinstance(part, protos.Part):
        return part
    elif isinstance(part, str):
        return protos.Part(text=part)
    elif isinstance(part, protos.FileData):
        return protos.Part(file_data=part)
    elif isinstance(part, (protos.File, file_types.File)):
        return protos.Part(file_data=file_types.to_file_data(part))
    elif isinstance(part, protos.FunctionCall):
        return protos.Part(function_call=part)
    elif isinstance(part, protos.FunctionResponse):
        return protos.Part(function_response=part)

    else:
        # Maybe it can be turned into a blob?
        return protos.Part(inline_data=to_blob(part))


class ContentDict(TypedDict):
    parts: list[PartType]
    role: str


def is_content_dict(d):
    return "parts" in d


# When you need a message accept a `Content` object or dict, a list of parts,
# or a single part
ContentType = Union[protos.Content, ContentDict, Iterable[PartType], PartType]

# For generate_content, we're not guessing roles for [[parts],[parts],[parts]] yet.
StrictContentType = Union[protos.Content, ContentDict]


def to_content(content: ContentType):
    if not content:
        raise ValueError(
            "Invalid input: 'content' argument must not be empty. Please provide a non-empty value."
        )

    if isinstance(content, Mapping):
        content = _convert_dict(content)

    if isinstance(content, protos.Content):
        return content
    elif isinstance(content, Iterable) and not isinstance(content, str):
        return protos.Content(parts=[to_part(part) for part in content])
    else:
        # Maybe this is a Part?
        return protos.Content(parts=[to_part(content)])


def strict_to_content(content: StrictContentType):
    if isinstance(content, Mapping):
        content = _convert_dict(content)

    if isinstance(content, protos.Content):
        return content
    else:
        raise TypeError(
            "Invalid input type. Expected a `protos.Content` or a `dict` with a 'parts' key.\n"
            f"However, received an object of type: {type(content)}.\n"
            f"Object Value: {content}"
        )


ContentsType = Union[ContentType, Iterable[StrictContentType], None]


def to_contents(contents: ContentsType) -> list[protos.Content]:
    if contents is None:
        return []

    if isinstance(contents, Iterable) and not isinstance(contents, (str, Mapping)):
        try:
            # strict_to_content so [[parts], [parts]] doesn't assume roles.
            contents = [strict_to_content(c) for c in contents]
            return contents
        except TypeError:
            # If you get a TypeError here it's probably because that was a list
            # of parts, not a list of contents, so fall back to `to_content`.
            pass

    contents = [to_content(contents)]
    return contents


def _schema_for_class(cls: TypedDict) -> dict[str, Any]:
    schema = _build_schema("dummy", {"dummy": (cls, pydantic.Field())})
    return schema["properties"]["dummy"]


def _schema_for_function(
    f: Callable[..., Any],
    *,
    descriptions: Mapping[str, str] | None = None,
    required: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Generates the OpenAPI Schema for a python function.

    Args:
        f: The function to generate an OpenAPI Schema for.
        descriptions: Optional. A `{name: description}` mapping for annotating input
            arguments of the function with user-provided descriptions. It
            defaults to an empty dictionary (i.e. there will not be any
            description for any of the inputs).
        required: Optional. For the user to specify the set of required arguments in
            function calls to `f`. If unspecified, it will be automatically
            inferred from `f`.

    Returns:
        dict[str, Any]: The OpenAPI Schema for the function `f` in JSON format.
    """
    if descriptions is None:
        descriptions = {}
    defaults = dict(inspect.signature(f).parameters)

    fields_dict = {}
    for name, param in defaults.items():
        if param.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.POSITIONAL_ONLY,
        ):
            # We do not support default values for now.
            # default=(
            #     param.default if param.default != inspect.Parameter.empty
            #     else None
            # ),
            field = pydantic.Field(
                # We support user-provided descriptions.
                description=descriptions.get(name, None)
            )

            # 1. We infer the argument type here: use Any rather than None so
            # it will not try to auto-infer the type based on the default value.
            if param.annotation != inspect.Parameter.empty:
                fields_dict[name] = param.annotation, field
            else:
                fields_dict[name] = Any, field

    parameters = _build_schema(f.__name__, fields_dict)

    # 6. Annotate required fields.
    if required is not None:
        # We use the user-provided "required" fields if specified.
        parameters["required"] = required
    else:
        # Otherwise we infer it from the function signature.
        parameters["required"] = [
            k
            for k in defaults
            if (
                defaults[k].default == inspect.Parameter.empty
                and defaults[k].kind
                in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                    inspect.Parameter.POSITIONAL_ONLY,
                )
            )
        ]
    schema = dict(name=f.__name__, description=f.__doc__)
    if parameters["properties"]:
        schema["parameters"] = parameters

    return schema


def _build_schema(fname, fields_dict):
    parameters = pydantic.create_model(fname, **fields_dict).schema()
    defs = parameters.pop("$defs", {})
    # flatten the defs
    for name, value in defs.items():
        unpack_defs(value, defs)
    unpack_defs(parameters, defs)

    # 5. Nullable fields:
    #     * https://github.com/pydantic/pydantic/issues/1270
    #     * https://stackoverflow.com/a/58841311
    #     * https://github.com/pydantic/pydantic/discussions/4872
    convert_to_nullable(parameters)
    add_object_type(parameters)
    # Postprocessing
    # 4. Suppress unnecessary title generation:
    #    * https://github.com/pydantic/pydantic/issues/1051
    #    * http://cl/586221780
    strip_titles(parameters)
    return parameters


def unpack_defs(schema, defs):
    properties = schema["properties"]
    for name, value in properties.items():
        ref_key = value.get("$ref", None)
        if ref_key is not None:
            ref = defs[ref_key.split("defs/")[-1]]
            unpack_defs(ref, defs)
            properties[name] = ref
            continue

        anyof = value.get("anyOf", None)
        if anyof is not None:
            for i, atype in enumerate(anyof):
                ref_key = atype.get("$ref", None)
                if ref_key is not None:
                    ref = defs[ref_key.split("defs/")[-1]]
                    unpack_defs(ref, defs)
                    anyof[i] = ref
            continue

        items = value.get("items", None)
        if items is not None:
            ref_key = items.get("$ref", None)
            if ref_key is not None:
                ref = defs[ref_key.split("defs/")[-1]]
                unpack_defs(ref, defs)
                value["items"] = ref
                continue


def strip_titles(schema):
    title = schema.pop("title", None)

    properties = schema.get("properties", None)
    if properties is not None:
        for name, value in properties.items():
            strip_titles(value)

    items = schema.get("items", None)
    if items is not None:
        strip_titles(items)


def add_object_type(schema):
    properties = schema.get("properties", None)
    if properties is not None:
        schema.pop("required", None)
        schema["type"] = "object"
        for name, value in properties.items():
            add_object_type(value)

    items = schema.get("items", None)
    if items is not None:
        add_object_type(items)


def convert_to_nullable(schema):
    anyof = schema.pop("anyOf", None)
    if anyof is not None:
        if len(anyof) != 2:
            raise ValueError(
                "Invalid input: Type Unions are not supported, except for `Optional` types. "
                "Please provide an `Optional` type or a non-Union type."
            )
        a, b = anyof
        if a == {"type": "null"}:
            schema.update(b)
        elif b == {"type": "null"}:
            schema.update(a)
        else:
            raise ValueError(
                "Invalid input: Type Unions are not supported, except for `Optional` types. "
                "Please provide an `Optional` type or a non-Union type."
            )
        schema["nullable"] = True

    properties = schema.get("properties", None)
    if properties is not None:
        for name, value in properties.items():
            convert_to_nullable(value)

    items = schema.get("items", None)
    if items is not None:
        convert_to_nullable(items)


def _rename_schema_fields(schema):
    if schema is None:
        return schema

    schema = schema.copy()

    type_ = schema.pop("type", None)
    if type_ is not None:
        schema["type_"] = type_.upper()

    format_ = schema.pop("format", None)
    if format_ is not None:
        schema["format_"] = format_

    items = schema.pop("items", None)
    if items is not None:
        schema["items"] = _rename_schema_fields(items)

    properties = schema.pop("properties", None)
    if properties is not None:
        schema["properties"] = {k: _rename_schema_fields(v) for k, v in properties.items()}

    return schema


class FunctionDeclaration:
    def __init__(self, *, name: str, description: str, parameters: dict[str, Any] | None = None):
        """A  class wrapping a `protos.FunctionDeclaration`, describes a function for `genai.GenerativeModel`'s `tools`."""
        self._proto = protos.FunctionDeclaration(
            name=name, description=description, parameters=_rename_schema_fields(parameters)
        )

    @property
    def name(self) -> str:
        return self._proto.name

    @property
    def description(self) -> str:
        return self._proto.description

    @property
    def parameters(self) -> protos.Schema:
        return self._proto.parameters

    @classmethod
    def from_proto(cls, proto) -> FunctionDeclaration:
        self = cls(name="", description="", parameters={})
        self._proto = proto
        return self

    def to_proto(self) -> protos.FunctionDeclaration:
        return self._proto

    @staticmethod
    def from_function(function: Callable[..., Any], descriptions: dict[str, str] | None = None):
        """Builds a `CallableFunctionDeclaration` from a python function.

        The function should have type annotations.

        This method is able to generate the schema for arguments annotated with types:

        `AllowedTypes = float | int | str | list[AllowedTypes] | dict`

        This method does not yet build a schema for `TypedDict`, that would allow you to specify the dictionary
        contents. But you can build these manually.
        """

        if descriptions is None:
            descriptions = {}

        schema = _schema_for_function(function, descriptions=descriptions)

        return CallableFunctionDeclaration(**schema, function=function)


StructType = dict[str, "ValueType"]
ValueType = Union[float, str, bool, StructType, list["ValueType"], None]


class CallableFunctionDeclaration(FunctionDeclaration):
    """An extension of `FunctionDeclaration` that can be built from a python function, and is callable.

    Note: The python function must have type annotations.
    """

    def __init__(
        self,
        *,
        name: str,
        description: str,
        parameters: dict[str, Any] | None = None,
        function: Callable[..., Any],
    ):
        super().__init__(name=name, description=description, parameters=parameters)
        self.function = function

    def __call__(self, fc: protos.FunctionCall) -> protos.FunctionResponse:
        result = self.function(**fc.args)
        if not isinstance(result, dict):
            result = {"result": result}
        return protos.FunctionResponse(name=fc.name, response=result)


FunctionDeclarationType = Union[
    FunctionDeclaration,
    protos.FunctionDeclaration,
    dict[str, Any],
    Callable[..., Any],
]


def _make_function_declaration(
    fun: FunctionDeclarationType,
) -> FunctionDeclaration | protos.FunctionDeclaration:
    if isinstance(fun, (FunctionDeclaration, protos.FunctionDeclaration)):
        return fun
    elif isinstance(fun, dict):
        if "function" in fun:
            return CallableFunctionDeclaration(**fun)
        else:
            return FunctionDeclaration(**fun)
    elif callable(fun):
        return CallableFunctionDeclaration.from_function(fun)
    else:
        raise TypeError(
            "Invalid input type. Expected an instance of `genai.FunctionDeclarationType`.\n"
            f"However, received an object of type: {type(fun)}.\n"
            f"Object Value: {fun}"
        )


def _encode_fd(fd: FunctionDeclaration | protos.FunctionDeclaration) -> protos.FunctionDeclaration:
    if isinstance(fd, protos.FunctionDeclaration):
        return fd

    return fd.to_proto()


class Tool:
    """A wrapper for `protos.Tool`, Contains a collection of related `FunctionDeclaration` objects."""

    def __init__(
        self,
        function_declarations: Iterable[FunctionDeclarationType] | None = None,
        code_execution: protos.CodeExecution | None = None,
    ):
        # The main path doesn't use this but is seems useful.
        if function_declarations:
            self._function_declarations = [
                _make_function_declaration(f) for f in function_declarations
            ]
            self._index = {}
            for fd in self._function_declarations:
                name = fd.name
                if name in self._index:
                    raise ValueError("")
                self._index[fd.name] = fd
        else:
            # Consistent fields
            self._function_declarations = []
            self._index = {}

        self._proto = protos.Tool(
            function_declarations=[_encode_fd(fd) for fd in self._function_declarations],
            code_execution=code_execution,
        )

    @property
    def function_declarations(self) -> list[FunctionDeclaration | protos.FunctionDeclaration]:
        return self._function_declarations

    @property
    def code_execution(self) -> protos.CodeExecution:
        return self._proto.code_execution

    def __getitem__(
        self, name: str | protos.FunctionCall
    ) -> FunctionDeclaration | protos.FunctionDeclaration:
        if not isinstance(name, str):
            name = name.name

        return self._index[name]

    def __call__(self, fc: protos.FunctionCall) -> protos.FunctionResponse | None:
        declaration = self[fc]
        if not callable(declaration):
            return None

        return declaration(fc)

    def to_proto(self):
        return self._proto


class ToolDict(TypedDict):
    function_declarations: list[FunctionDeclarationType]


ToolType = Union[
    Tool, protos.Tool, ToolDict, Iterable[FunctionDeclarationType], FunctionDeclarationType
]


def _make_tool(tool: ToolType) -> Tool:
    if isinstance(tool, Tool):
        return tool
    elif isinstance(tool, protos.Tool):
        if "code_execution" in tool:
            code_execution = tool.code_execution
        else:
            code_execution = None
        return Tool(function_declarations=tool.function_declarations, code_execution=code_execution)
    elif isinstance(tool, dict):
        if "function_declarations" in tool or "code_execution" in tool:
            return Tool(**tool)
        else:
            fd = tool
            return Tool(function_declarations=[protos.FunctionDeclaration(**fd)])
    elif isinstance(tool, str):
        if tool.lower() == "code_execution":
            return Tool(code_execution=protos.CodeExecution())
        else:
            raise ValueError("The only string that can be passed as a tool is 'code_execution'.")
    elif isinstance(tool, protos.CodeExecution):
        return Tool(code_execution=tool)
    elif isinstance(tool, Iterable):
        return Tool(function_declarations=tool)
    else:
        try:
            return Tool(function_declarations=[tool])
        except Exception as e:
            raise TypeError(
                "Invalid input type. Expected an instance of `genai.ToolType`.\n"
                f"However, received an object of type: {type(tool)}.\n"
                f"Object Value: {tool}"
            ) from e


class FunctionLibrary:
    """A container for a set of `Tool` objects, manages lookup and execution of their functions."""

    def __init__(self, tools: Iterable[ToolType]):
        tools = _make_tools(tools)
        self._tools = list(tools)
        self._index = {}
        for tool in self._tools:
            for declaration in tool.function_declarations:
                name = declaration.name
                if name in self._index:
                    raise ValueError(
                        f"Invalid operation: A `FunctionDeclaration` named '{name}' is already defined. "
                        "Each `FunctionDeclaration` must have a unique name. Please use a different name."
                    )
                self._index[declaration.name] = declaration

    def __getitem__(
        self, name: str | protos.FunctionCall
    ) -> FunctionDeclaration | protos.FunctionDeclaration:
        if not isinstance(name, str):
            name = name.name

        return self._index[name]

    def __call__(self, fc: protos.FunctionCall) -> protos.Part | None:
        declaration = self[fc]
        if not callable(declaration):
            return None

        response = declaration(fc)
        return protos.Part(function_response=response)

    def to_proto(self):
        return [tool.to_proto() for tool in self._tools]


ToolsType = Union[Iterable[ToolType], ToolType]


def _make_tools(tools: ToolsType) -> list[Tool]:
    if isinstance(tools, str):
        if tools.lower() == "code_execution":
            return [_make_tool(tools)]
        else:
            raise ValueError("The only string that can be passed as a tool is 'code_execution'.")
    elif isinstance(tools, Iterable) and not isinstance(tools, Mapping):
        tools = [_make_tool(t) for t in tools]
        if len(tools) > 1 and all(len(t.function_declarations) == 1 for t in tools):
            # flatten into a single tool.
            tools = [_make_tool([t.function_declarations[0] for t in tools])]
        return tools
    else:
        tool = tools
        return [_make_tool(tool)]


FunctionLibraryType = Union[FunctionLibrary, ToolsType]


def to_function_library(lib: FunctionLibraryType | None) -> FunctionLibrary | None:
    if lib is None:
        return lib
    elif isinstance(lib, FunctionLibrary):
        return lib
    else:
        return FunctionLibrary(tools=lib)


FunctionCallingMode = protos.FunctionCallingConfig.Mode

# fmt: off
_FUNCTION_CALLING_MODE = {
    1: FunctionCallingMode.AUTO,
    FunctionCallingMode.AUTO: FunctionCallingMode.AUTO,
    "mode_auto": FunctionCallingMode.AUTO,
    "auto": FunctionCallingMode.AUTO,

    2: FunctionCallingMode.ANY,
    FunctionCallingMode.ANY: FunctionCallingMode.ANY,
    "mode_any": FunctionCallingMode.ANY,
    "any": FunctionCallingMode.ANY,

    3: FunctionCallingMode.NONE,
    FunctionCallingMode.NONE: FunctionCallingMode.NONE,
    "mode_none": FunctionCallingMode.NONE,
    "none": FunctionCallingMode.NONE,
}
# fmt: on

FunctionCallingModeType = Union[FunctionCallingMode, str, int]


def to_function_calling_mode(x: FunctionCallingModeType) -> FunctionCallingMode:
    if isinstance(x, str):
        x = x.lower()
    return _FUNCTION_CALLING_MODE[x]


class FunctionCallingConfigDict(TypedDict):
    mode: FunctionCallingModeType
    allowed_function_names: list[str]


FunctionCallingConfigType = Union[
    FunctionCallingModeType, FunctionCallingConfigDict, protos.FunctionCallingConfig
]


def to_function_calling_config(obj: FunctionCallingConfigType) -> protos.FunctionCallingConfig:
    if isinstance(obj, protos.FunctionCallingConfig):
        return obj
    elif isinstance(obj, (FunctionCallingMode, str, int)):
        obj = {"mode": to_function_calling_mode(obj)}
    elif isinstance(obj, dict):
        obj = obj.copy()
        mode = obj.pop("mode")
        obj["mode"] = to_function_calling_mode(mode)
    else:
        raise TypeError(
            "Invalid input type. Failed to convert input to `protos.FunctionCallingConfig`.\n"
            f"Received an object of type: {type(obj)}.\n"
            f"Object Value: {obj}"
        )

    return protos.FunctionCallingConfig(obj)


class ToolConfigDict:
    function_calling_config: FunctionCallingConfigType


ToolConfigType = Union[ToolConfigDict, protos.ToolConfig]


def to_tool_config(obj: ToolConfigType) -> protos.ToolConfig:
    if isinstance(obj, protos.ToolConfig):
        return obj
    elif isinstance(obj, dict):
        fcc = obj.pop("function_calling_config")
        fcc = to_function_calling_config(fcc)
        obj["function_calling_config"] = fcc
        return protos.ToolConfig(**obj)
    else:
        raise TypeError(
            "Invalid input type. Failed to convert input to `protos.ToolConfig`.\n"
            f"Received an object of type: {type(obj)}.\n"
            f"Object Value: {obj}"
        )