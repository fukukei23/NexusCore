
# === NexusCore/tools\exports\export_20250803_114325\combined_79.py ===

# === NexusCore/openenv\Lib\site-packages\matplotlib\__init__.py ===
"""
An object-oriented plotting library.

A procedural interface is provided by the companion pyplot module,
which may be imported directly, e.g.::

    import matplotlib.pyplot as plt

or using ipython::

    ipython

at your terminal, followed by::

    In [1]: %matplotlib
    In [2]: import matplotlib.pyplot as plt

at the ipython shell prompt.

For the most part, direct use of the explicit object-oriented library is
encouraged when programming; the implicit pyplot interface is primarily for
working interactively. The exceptions to this suggestion are the pyplot
functions `.pyplot.figure`, `.pyplot.subplot`, `.pyplot.subplots`, and
`.pyplot.savefig`, which can greatly simplify scripting.  See
:ref:`api_interfaces` for an explanation of the tradeoffs between the implicit
and explicit interfaces.

Modules include:

:mod:`matplotlib.axes`
    The `~.axes.Axes` class.  Most pyplot functions are wrappers for
    `~.axes.Axes` methods.  The axes module is the highest level of OO
    access to the library.

:mod:`matplotlib.figure`
    The `.Figure` class.

:mod:`matplotlib.artist`
    The `.Artist` base class for all classes that draw things.

:mod:`matplotlib.lines`
    The `.Line2D` class for drawing lines and markers.

:mod:`matplotlib.patches`
    Classes for drawing polygons.

:mod:`matplotlib.text`
    The `.Text` and `.Annotation` classes.

:mod:`matplotlib.image`
    The `.AxesImage` and `.FigureImage` classes.

:mod:`matplotlib.collections`
    Classes for efficient drawing of groups of lines or polygons.

:mod:`matplotlib.colors`
    Color specifications and making colormaps.

:mod:`matplotlib.cm`
    Colormaps, and the `.ScalarMappable` mixin class for providing color
    mapping functionality to other classes.

:mod:`matplotlib.ticker`
    Calculation of tick mark locations and formatting of tick labels.

:mod:`matplotlib.backends`
    A subpackage with modules for various GUI libraries and output formats.

The base matplotlib namespace includes:

`~matplotlib.rcParams`
    Default configuration settings; their defaults may be overridden using
    a :file:`matplotlibrc` file.

`~matplotlib.use`
    Setting the Matplotlib backend.  This should be called before any
    figure is created, because it is not possible to switch between
    different GUI backends after that.

The following environment variables can be used to customize the behavior:

:envvar:`MPLBACKEND`
    This optional variable can be set to choose the Matplotlib backend. See
    :ref:`what-is-a-backend`.

:envvar:`MPLCONFIGDIR`
    This is the directory used to store user customizations to
    Matplotlib, as well as some caches to improve performance. If
    :envvar:`MPLCONFIGDIR` is not defined, :file:`{HOME}/.config/matplotlib`
    and :file:`{HOME}/.cache/matplotlib` are used on Linux, and
    :file:`{HOME}/.matplotlib` on other platforms, if they are
    writable. Otherwise, the Python standard library's `tempfile.gettempdir`
    is used to find a base directory in which the :file:`matplotlib`
    subdirectory is created.

Matplotlib was initially written by John D. Hunter (1968-2012) and is now
developed and maintained by a host of others.

Occasionally the internal documentation (python docstrings) will refer
to MATLAB®, a registered trademark of The MathWorks, Inc.

"""

__all__ = [
    "__bibtex__",
    "__version__",
    "__version_info__",
    "set_loglevel",
    "ExecutableNotFoundError",
    "get_configdir",
    "get_cachedir",
    "get_data_path",
    "matplotlib_fname",
    "MatplotlibDeprecationWarning",
    "RcParams",
    "rc_params",
    "rc_params_from_file",
    "rcParamsDefault",
    "rcParams",
    "rcParamsOrig",
    "defaultParams",
    "rc",
    "rcdefaults",
    "rc_file_defaults",
    "rc_file",
    "rc_context",
    "use",
    "get_backend",
    "interactive",
    "is_interactive",
    "colormaps",
    "multivar_colormaps",
    "bivar_colormaps",
    "color_sequences",
]


import atexit
from collections import namedtuple
from collections.abc import MutableMapping
import contextlib
import functools
import importlib
import inspect
from inspect import Parameter
import locale
import logging
import os
from pathlib import Path
import pprint
import re
import shutil
import subprocess
import sys
import tempfile

from packaging.version import parse as parse_version

# cbook must import matplotlib only within function
# definitions, so it is safe to import from it here.
from . import _api, _version, cbook, _docstring, rcsetup
from matplotlib._api import MatplotlibDeprecationWarning
from matplotlib.rcsetup import cycler  # noqa: F401


_log = logging.getLogger(__name__)

__bibtex__ = r"""@Article{Hunter:2007,
  Author    = {Hunter, J. D.},
  Title     = {Matplotlib: A 2D graphics environment},
  Journal   = {Computing in Science \& Engineering},
  Volume    = {9},
  Number    = {3},
  Pages     = {90--95},
  abstract  = {Matplotlib is a 2D graphics package used for Python
  for application development, interactive scripting, and
  publication-quality image generation across user
  interfaces and operating systems.},
  publisher = {IEEE COMPUTER SOC},
  year      = 2007
}"""

# modelled after sys.version_info
_VersionInfo = namedtuple('_VersionInfo',
                          'major, minor, micro, releaselevel, serial')


def _parse_to_version_info(version_str):
    """
    Parse a version string to a namedtuple analogous to sys.version_info.

    See:
    https://packaging.pypa.io/en/latest/version.html#packaging.version.parse
    https://docs.python.org/3/library/sys.html#sys.version_info
    """
    v = parse_version(version_str)
    if v.pre is None and v.post is None and v.dev is None:
        return _VersionInfo(v.major, v.minor, v.micro, 'final', 0)
    elif v.dev is not None:
        return _VersionInfo(v.major, v.minor, v.micro, 'alpha', v.dev)
    elif v.pre is not None:
        releaselevel = {
            'a': 'alpha',
            'b': 'beta',
            'rc': 'candidate'}.get(v.pre[0], 'alpha')
        return _VersionInfo(v.major, v.minor, v.micro, releaselevel, v.pre[1])
    else:
        # fallback for v.post: guess-next-dev scheme from setuptools_scm
        return _VersionInfo(v.major, v.minor, v.micro + 1, 'alpha', v.post)


def _get_version():
    """Return the version string used for __version__."""
    # Only shell out to a git subprocess if really needed, i.e. when we are in
    # a matplotlib git repo but not in a shallow clone, such as those used by
    # CI, as the latter would trigger a warning from setuptools_scm.
    root = Path(__file__).resolve().parents[2]
    if ((root / ".matplotlib-repo").exists()
            and (root / ".git").exists()
            and not (root / ".git/shallow").exists()):
        try:
            import setuptools_scm
        except ImportError:
            pass
        else:
            return setuptools_scm.get_version(
                root=root,
                dist_name="matplotlib",
                version_scheme="release-branch-semver",
                local_scheme="node-and-date",
                fallback_version=_version.version,
            )
    # Get the version from the _version.py file if not in repo or setuptools_scm is
    # unavailable.
    return _version.version


@_api.caching_module_getattr
class __getattr__:
    __version__ = property(lambda self: _get_version())
    __version_info__ = property(
        lambda self: _parse_to_version_info(self.__version__))


def _check_versions():

    # Quickfix to ensure Microsoft Visual C++ redistributable
    # DLLs are loaded before importing kiwisolver
    from . import ft2font  # noqa: F401

    for modname, minver in [
            ("cycler", "0.10"),
            ("dateutil", "2.7"),
            ("kiwisolver", "1.3.1"),
            ("numpy", "1.23"),
            ("pyparsing", "2.3.1"),
    ]:
        module = importlib.import_module(modname)
        if parse_version(module.__version__) < parse_version(minver):
            raise ImportError(f"Matplotlib requires {modname}>={minver}; "
                              f"you have {module.__version__}")


_check_versions()


# The decorator ensures this always returns the same handler (and it is only
# attached once).
@functools.cache
def _ensure_handler():
    """
    The first time this function is called, attach a `StreamHandler` using the
    same format as `logging.basicConfig` to the Matplotlib root logger.

    Return this handler every time this function is called.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    _log.addHandler(handler)
    return handler


def set_loglevel(level):
    """
    Configure Matplotlib's logging levels.

    Matplotlib uses the standard library `logging` framework under the root
    logger 'matplotlib'.  This is a helper function to:

    - set Matplotlib's root logger level
    - set the root logger handler's level, creating the handler
      if it does not exist yet

    Typically, one should call ``set_loglevel("info")`` or
    ``set_loglevel("debug")`` to get additional debugging information.

    Users or applications that are installing their own logging handlers
    may want to directly manipulate ``logging.getLogger('matplotlib')`` rather
    than use this function.

    Parameters
    ----------
    level : {"notset", "debug", "info", "warning", "error", "critical"}
        The log level of the handler.

    Notes
    -----
    The first time this function is called, an additional handler is attached
    to Matplotlib's root handler; this handler is reused every time and this
    function simply manipulates the logger and handler's level.

    """
    _log.setLevel(level.upper())
    _ensure_handler().setLevel(level.upper())


def _logged_cached(fmt, func=None):
    """
    Decorator that logs a function's return value, and memoizes that value.

    After ::

        @_logged_cached(fmt)
        def func(): ...

    the first call to *func* will log its return value at the DEBUG level using
    %-format string *fmt*, and memoize it; later calls to *func* will directly
    return that value.
    """
    if func is None:  # Return the actual decorator.
        return functools.partial(_logged_cached, fmt)

    called = False
    ret = None

    @functools.wraps(func)
    def wrapper(**kwargs):
        nonlocal called, ret
        if not called:
            ret = func(**kwargs)
            called = True
            _log.debug(fmt, ret)
        return ret

    return wrapper


_ExecInfo = namedtuple("_ExecInfo", "executable raw_version version")


class ExecutableNotFoundError(FileNotFoundError):
    """
    Error raised when an executable that Matplotlib optionally
    depends on can't be found.
    """
    pass


@functools.cache
def _get_executable_info(name):
    """
    Get the version of some executable that Matplotlib optionally depends on.

    .. warning::
       The list of executables that this function supports is set according to
       Matplotlib's internal needs, and may change without notice.

    Parameters
    ----------
    name : str
        The executable to query.  The following values are currently supported:
        "dvipng", "gs", "inkscape", "magick", "pdftocairo", "pdftops".  This
        list is subject to change without notice.

    Returns
    -------
    tuple
        A namedtuple with fields ``executable`` (`str`) and ``version``
        (`packaging.Version`, or ``None`` if the version cannot be determined).

    Raises
    ------
    ExecutableNotFoundError
        If the executable is not found or older than the oldest version
        supported by Matplotlib.  For debugging purposes, it is also
        possible to "hide" an executable from Matplotlib by adding it to the
        :envvar:`_MPLHIDEEXECUTABLES` environment variable (a comma-separated
        list), which must be set prior to any calls to this function.
    ValueError
        If the executable is not one that we know how to query.
    """

    def impl(args, regex, min_ver=None, ignore_exit_code=False):
        # Execute the subprocess specified by args; capture stdout and stderr.
        # Search for a regex match in the output; if the match succeeds, the
        # first group of the match is the version.
        # Return an _ExecInfo if the executable exists, and has a version of
        # at least min_ver (if set); else, raise ExecutableNotFoundError.
        try:
            output = subprocess.check_output(
                args, stderr=subprocess.STDOUT,
                text=True, errors="replace")
        except subprocess.CalledProcessError as _cpe:
            if ignore_exit_code:
                output = _cpe.output
            else:
                raise ExecutableNotFoundError(str(_cpe)) from _cpe
        except OSError as _ose:
            raise ExecutableNotFoundError(str(_ose)) from _ose
        match = re.search(regex, output)
        if match:
            raw_version = match.group(1)
            version = parse_version(raw_version)
            if min_ver is not None and version < parse_version(min_ver):
                raise ExecutableNotFoundError(
                    f"You have {args[0]} version {version} but the minimum "
                    f"version supported by Matplotlib is {min_ver}")
            return _ExecInfo(args[0], raw_version, version)
        else:
            raise ExecutableNotFoundError(
                f"Failed to determine the version of {args[0]} from "
                f"{' '.join(args)}, which output {output}")

    if name in os.environ.get("_MPLHIDEEXECUTABLES", "").split(","):
        raise ExecutableNotFoundError(f"{name} was hidden")

    if name == "dvipng":
        return impl(["dvipng", "-version"], "(?m)^dvipng(?: .*)? (.+)", "1.6")
    elif name == "gs":
        execs = (["gswin32c", "gswin64c", "mgs", "gs"]  # "mgs" for miktex.
                 if sys.platform == "win32" else
                 ["gs"])
        for e in execs:
            try:
                return impl([e, "--version"], "(.*)", "9")
            except ExecutableNotFoundError:
                pass
        message = "Failed to find a Ghostscript installation"
        raise ExecutableNotFoundError(message)
    elif name == "inkscape":
        try:
            # Try headless option first (needed for Inkscape version < 1.0):
            return impl(["inkscape", "--without-gui", "-V"],
                        "Inkscape ([^ ]*)")
        except ExecutableNotFoundError:
            pass  # Suppress exception chaining.
        # If --without-gui is not accepted, we may be using Inkscape >= 1.0 so
        # try without it:
        return impl(["inkscape", "-V"], "Inkscape ([^ ]*)")
    elif name == "magick":
        if sys.platform == "win32":
            # Check the registry to avoid confusing ImageMagick's convert with
            # Windows's builtin convert.exe.
            import winreg
            binpath = ""
            for flag in [0, winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY]:
                try:
                    with winreg.OpenKeyEx(
                            winreg.HKEY_LOCAL_MACHINE,
                            r"Software\Imagemagick\Current",
                            0, winreg.KEY_QUERY_VALUE | flag) as hkey:
                        binpath = winreg.QueryValueEx(hkey, "BinPath")[0]
                except OSError:
                    pass
            path = None
            if binpath:
                for name in ["convert.exe", "magick.exe"]:
                    candidate = Path(binpath, name)
                    if candidate.exists():
                        path = str(candidate)
                        break
            if path is None:
                raise ExecutableNotFoundError(
                    "Failed to find an ImageMagick installation")
        else:
            path = "convert"
        info = impl([path, "--version"], r"^Version: ImageMagick (\S*)")
        if info.raw_version == "7.0.10-34":
            # https://github.com/ImageMagick/ImageMagick/issues/2720
            raise ExecutableNotFoundError(
                f"You have ImageMagick {info.version}, which is unsupported")
        return info
    elif name == "pdftocairo":
        return impl(["pdftocairo", "-v"], "pdftocairo version (.*)")
    elif name == "pdftops":
        info = impl(["pdftops", "-v"], "^pdftops version (.*)",
                    ignore_exit_code=True)
        if info and not (
                3 <= info.version.major or
                # poppler version numbers.
                parse_version("0.9") <= info.version < parse_version("1.0")):
            raise ExecutableNotFoundError(
                f"You have pdftops version {info.version} but the minimum "
                f"version supported by Matplotlib is 3.0")
        return info
    else:
        raise ValueError(f"Unknown executable: {name!r}")


def _get_xdg_config_dir():
    """
    Return the XDG configuration directory, according to the XDG base
    directory spec:

    https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
    """
    return os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / ".config")


def _get_xdg_cache_dir():
    """
    Return the XDG cache directory, according to the XDG base directory spec:

    https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
    """
    return os.environ.get('XDG_CACHE_HOME') or str(Path.home() / ".cache")


def _get_config_or_cache_dir(xdg_base_getter):
    configdir = os.environ.get('MPLCONFIGDIR')
    if configdir:
        configdir = Path(configdir)
    elif sys.platform.startswith(('linux', 'freebsd')):
        # Only call _xdg_base_getter here so that MPLCONFIGDIR is tried first,
        # as _xdg_base_getter can throw.
        configdir = Path(xdg_base_getter(), "matplotlib")
    else:
        configdir = Path.home() / ".matplotlib"
    # Resolve the path to handle potential issues with inaccessible symlinks.
    configdir = configdir.resolve()
    try:
        configdir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _log.warning("mkdir -p failed for path %s: %s", configdir, exc)
    else:
        if os.access(str(configdir), os.W_OK) and configdir.is_dir():
            return str(configdir)
        _log.warning("%s is not a writable directory", configdir)
    # If the config or cache directory cannot be created or is not a writable
    # directory, create a temporary one.
    try:
        tmpdir = tempfile.mkdtemp(prefix="matplotlib-")
    except OSError as exc:
        raise OSError(
            f"Matplotlib requires access to a writable cache directory, but there "
            f"was an issue with the default path ({configdir}), and a temporary "
            f"directory could not be created; set the MPLCONFIGDIR environment "
            f"variable to a writable directory") from exc
    os.environ["MPLCONFIGDIR"] = tmpdir
    atexit.register(shutil.rmtree, tmpdir)
    _log.warning(
        "Matplotlib created a temporary cache directory at %s because there was "
        "an issue with the default path (%s); it is highly recommended to set the "
        "MPLCONFIGDIR environment variable to a writable directory, in particular to "
        "speed up the import of Matplotlib and to better support multiprocessing.",
        tmpdir, configdir)
    return tmpdir


@_logged_cached('CONFIGDIR=%s')
def get_configdir():
    """
    Return the string path of the configuration directory.

    The directory is chosen as follows:

    1. If the MPLCONFIGDIR environment variable is supplied, choose that.
    2. On Linux, follow the XDG specification and look first in
       ``$XDG_CONFIG_HOME``, if defined, or ``$HOME/.config``.  On other
       platforms, choose ``$HOME/.matplotlib``.
    3. If the chosen directory exists and is writable, use that as the
       configuration directory.
    4. Else, create a temporary directory, and use it as the configuration
       directory.
    """
    return _get_config_or_cache_dir(_get_xdg_config_dir)


@_logged_cached('CACHEDIR=%s')
def get_cachedir():
    """
    Return the string path of the cache directory.

    The procedure used to find the directory is the same as for
    `get_configdir`, except using ``$XDG_CACHE_HOME``/``$HOME/.cache`` instead.
    """
    return _get_config_or_cache_dir(_get_xdg_cache_dir)


@_logged_cached('matplotlib data path: %s')
def get_data_path():
    """Return the path to Matplotlib data."""
    return str(Path(__file__).with_name("mpl-data"))


def matplotlib_fname():
    """
    Get the location of the config file.

    The file location is determined in the following order

    - ``$PWD/matplotlibrc``
    - ``$MATPLOTLIBRC`` if it is not a directory
    - ``$MATPLOTLIBRC/matplotlibrc``
    - ``$MPLCONFIGDIR/matplotlibrc``
    - On Linux,
        - ``$XDG_CONFIG_HOME/matplotlib/matplotlibrc`` (if ``$XDG_CONFIG_HOME``
          is defined)
        - or ``$HOME/.config/matplotlib/matplotlibrc`` (if ``$XDG_CONFIG_HOME``
          is not defined)
    - On other platforms,
      - ``$HOME/.matplotlib/matplotlibrc`` if ``$HOME`` is defined
    - Lastly, it looks in ``$MATPLOTLIBDATA/matplotlibrc``, which should always
      exist.
    """

    def gen_candidates():
        # rely on down-stream code to make absolute.  This protects us
        # from having to directly get the current working directory
        # which can fail if the user has ended up with a cwd that is
        # non-existent.
        yield 'matplotlibrc'
        try:
            matplotlibrc = os.environ['MATPLOTLIBRC']
        except KeyError:
            pass
        else:
            yield matplotlibrc
            yield os.path.join(matplotlibrc, 'matplotlibrc')
        yield os.path.join(get_configdir(), 'matplotlibrc')
        yield os.path.join(get_data_path(), 'matplotlibrc')

    for fname in gen_candidates():
        if os.path.exists(fname) and not os.path.isdir(fname):
            return fname

    raise RuntimeError("Could not find matplotlibrc file; your Matplotlib "
                       "install is broken")


# rcParams deprecated and automatically mapped to another key.
# Values are tuples of (version, new_name, f_old2new, f_new2old).
_deprecated_map = {}
# rcParams deprecated; some can manually be mapped to another key.
# Values are tuples of (version, new_name_or_None).
_deprecated_ignore_map = {}
# rcParams deprecated; can use None to suppress warnings; remain actually
# listed in the rcParams.
# Values are tuples of (version,)
_deprecated_remain_as_none = {}


@_docstring.Substitution(
    "\n".join(map("- {}".format, sorted(rcsetup._validators, key=str.lower)))
)
class RcParams(MutableMapping, dict):
    """
    A dict-like key-value store for config parameters, including validation.

    Validating functions are defined and associated with rc parameters in
    :mod:`matplotlib.rcsetup`.

    The list of rcParams is:

    %s

    See Also
    --------
    :ref:`customizing-with-matplotlibrc-files`
    """

    validate = rcsetup._validators

    # validate values on the way in
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def _set(self, key, val):
        """
        Directly write data bypassing deprecation and validation logic.

        Notes
        -----
        As end user or downstream library you almost always should use
        ``rcParams[key] = val`` and not ``_set()``.

        There are only very few special cases that need direct data access.
        These cases previously used ``dict.__setitem__(rcParams, key, val)``,
        which is now deprecated and replaced by ``rcParams._set(key, val)``.

        Even though private, we guarantee API stability for ``rcParams._set``,
        i.e. it is subject to Matplotlib's API and deprecation policy.

        :meta public:
        """
        dict.__setitem__(self, key, val)

    def _get(self, key):
        """
        Directly read data bypassing deprecation, backend and validation
        logic.

        Notes
        -----
        As end user or downstream library you almost always should use
        ``val = rcParams[key]`` and not ``_get()``.

        There are only very few special cases that need direct data access.
        These cases previously used ``dict.__getitem__(rcParams, key, val)``,
        which is now deprecated and replaced by ``rcParams._get(key)``.

        Even though private, we guarantee API stability for ``rcParams._get``,
        i.e. it is subject to Matplotlib's API and deprecation policy.

        :meta public:
        """
        return dict.__getitem__(self, key)

    def _update_raw(self, other_params):
        """
        Directly update the data from *other_params*, bypassing deprecation,
        backend and validation logic on both sides.

        This ``rcParams._update_raw(params)`` replaces the previous pattern
        ``dict.update(rcParams, params)``.

        Parameters
        ----------
        other_params : dict or `.RcParams`
            The input mapping from which to update.
        """
        if isinstance(other_params, RcParams):
            other_params = dict.items(other_params)
        dict.update(self, other_params)

    def _ensure_has_backend(self):
        """
        Ensure that a "backend" entry exists.

        Normally, the default matplotlibrc file contains *no* entry for "backend" (the
        corresponding line starts with ##, not #; we fill in _auto_backend_sentinel
        in that case.  However, packagers can set a different default backend
        (resulting in a normal `#backend: foo` line) in which case we should *not*
        fill in _auto_backend_sentinel.
        """
        dict.setdefault(self, "backend", rcsetup._auto_backend_sentinel)

    def __setitem__(self, key, val):
        try:
            if key in _deprecated_map:
                version, alt_key, alt_val, inverse_alt = _deprecated_map[key]
                _api.warn_deprecated(
                    version, name=key, obj_type="rcparam", alternative=alt_key)
                key = alt_key
                val = alt_val(val)
            elif key in _deprecated_remain_as_none and val is not None:
                version, = _deprecated_remain_as_none[key]
                _api.warn_deprecated(version, name=key, obj_type="rcparam")
            elif key in _deprecated_ignore_map:
                version, alt_key = _deprecated_ignore_map[key]
                _api.warn_deprecated(
                    version, name=key, obj_type="rcparam", alternative=alt_key)
                return
            elif key == 'backend':
                if val is rcsetup._auto_backend_sentinel:
                    if 'backend' in self:
                        return
            try:
                cval = self.validate[key](val)
            except ValueError as ve:
                raise ValueError(f"Key {key}: {ve}") from None
            self._set(key, cval)
        except KeyError as err:
            raise KeyError(
                f"{key} is not a valid rc parameter (see rcParams.keys() for "
                f"a list of valid parameters)") from err

    def __getitem__(self, key):
        if key in _deprecated_map:
            version, alt_key, alt_val, inverse_alt = _deprecated_map[key]
            _api.warn_deprecated(
                version, name=key, obj_type="rcparam", alternative=alt_key)
            return inverse_alt(self._get(alt_key))

        elif key in _deprecated_ignore_map:
            version, alt_key = _deprecated_ignore_map[key]
            _api.warn_deprecated(
                version, name=key, obj_type="rcparam", alternative=alt_key)
            return self._get(alt_key) if alt_key else None

        # In theory, this should only ever be used after the global rcParams
        # has been set up, but better be safe e.g. in presence of breakpoints.
        elif key == "backend" and self is globals().get("rcParams"):
            val = self._get(key)
            if val is rcsetup._auto_backend_sentinel:
                from matplotlib import pyplot as plt
                plt.switch_backend(rcsetup._auto_backend_sentinel)

        return self._get(key)

    def _get_backend_or_none(self):
        """Get the requested backend, if any, without triggering resolution."""
        backend = self._get("backend")
        return None if backend is rcsetup._auto_backend_sentinel else backend

    def __repr__(self):
        class_name = self.__class__.__name__
        indent = len(class_name) + 1
        with _api.suppress_matplotlib_deprecation_warning():
            repr_split = pprint.pformat(dict(self), indent=1,
                                        width=80 - indent).split('\n')
        repr_indented = ('\n' + ' ' * indent).join(repr_split)
        return f'{class_name}({repr_indented})'

    def __str__(self):
        return '\n'.join(map('{0[0]}: {0[1]}'.format, sorted(self.items())))

    def __iter__(self):
        """Yield sorted list of keys."""
        with _api.suppress_matplotlib_deprecation_warning():
            yield from sorted(dict.__iter__(self))

    def __len__(self):
        return dict.__len__(self)

    def find_all(self, pattern):
        """
        Return the subset of this RcParams dictionary whose keys match,
        using :func:`re.search`, the given ``pattern``.

        .. note::

            Changes to the returned dictionary are *not* propagated to
            the parent RcParams dictionary.

        """
        pattern_re = re.compile(pattern)
        return RcParams((key, value)
                        for key, value in self.items()
                        if pattern_re.search(key))

    def copy(self):
        """Copy this RcParams instance."""
        rccopy = RcParams()
        for k in self:  # Skip deprecations and revalidation.
            rccopy._set(k, self._get(k))
        return rccopy


def rc_params(fail_on_error=False):
    """Construct a `RcParams` instance from the default Matplotlib rc file."""
    return rc_params_from_file(matplotlib_fname(), fail_on_error)


@functools.cache
def _get_ssl_context():
    try:
        import certifi
    except ImportError:
        _log.debug("Could not import certifi.")
        return None
    import ssl
    return ssl.create_default_context(cafile=certifi.where())


@contextlib.contextmanager
def _open_file_or_url(fname):
    if (isinstance(fname, str)
            and fname.startswith(('http://', 'https://', 'ftp://', 'file:'))):
        import urllib.request
        ssl_ctx = _get_ssl_context()
        if ssl_ctx is None:
            _log.debug(
                "Could not get certifi ssl context, https may not work."
            )
        with urllib.request.urlopen(fname, context=ssl_ctx) as f:
            yield (line.decode('utf-8') for line in f)
    else:
        fname = os.path.expanduser(fname)
        with open(fname, encoding='utf-8') as f:
            yield f


def _rc_params_in_file(fname, transform=lambda x: x, fail_on_error=False):
    """
    Construct a `RcParams` instance from file *fname*.

    Unlike `rc_params_from_file`, the configuration class only contains the
    parameters specified in the file (i.e. default values are not filled in).

    Parameters
    ----------
    fname : path-like
        The loaded file.
    transform : callable, default: the identity function
        A function called on each individual line of the file to transform it,
        before further parsing.
    fail_on_error : bool, default: False
        Whether invalid entries should result in an exception or a warning.
    """
    import matplotlib as mpl
    rc_temp = {}
    with _open_file_or_url(fname) as fd:
        try:
            for line_no, line in enumerate(fd, 1):
                line = transform(line)
                strippedline = cbook._strip_comment(line)
                if not strippedline:
                    continue
                tup = strippedline.split(':', 1)
                if len(tup) != 2:
                    _log.warning('Missing colon in file %r, line %d (%r)',
                                 fname, line_no, line.rstrip('\n'))
                    continue
                key, val = tup
                key = key.strip()
                val = val.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]  # strip double quotes
                if key in rc_temp:
                    _log.warning('Duplicate key in file %r, line %d (%r)',
                                 fname, line_no, line.rstrip('\n'))
                rc_temp[key] = (val, line, line_no)
        except UnicodeDecodeError:
            _log.warning('Cannot decode configuration file %r as utf-8.',
                         fname)
            raise

    config = RcParams()

    for key, (val, line, line_no) in rc_temp.items():
        if key in rcsetup._validators:
            if fail_on_error:
                config[key] = val  # try to convert to proper type or raise
            else:
                try:
                    config[key] = val  # try to convert to proper type or skip
                except Exception as msg:
                    _log.warning('Bad value in file %r, line %d (%r): %s',
                                 fname, line_no, line.rstrip('\n'), msg)
        elif key in _deprecated_ignore_map:
            version, alt_key = _deprecated_ignore_map[key]
            _api.warn_deprecated(
                version, name=key, alternative=alt_key, obj_type='rcparam',
                addendum="Please update your matplotlibrc.")
        else:
            # __version__ must be looked up as an attribute to trigger the
            # module-level __getattr__.
            version = ('main' if '.post' in mpl.__version__
                       else f'v{mpl.__version__}')
            _log.warning("""
Bad key %(key)s in file %(fname)s, line %(line_no)s (%(line)r)
You probably need to get an updated matplotlibrc file from
https://github.com/matplotlib/matplotlib/blob/%(version)s/lib/matplotlib/mpl-data/matplotlibrc
or from the matplotlib source distribution""",
                         dict(key=key, fname=fname, line_no=line_no,
                              line=line.rstrip('\n'), version=version))
    return config


def rc_params_from_file(fname, fail_on_error=False, use_default_template=True):
    """
    Construct a `RcParams` from file *fname*.

    Parameters
    ----------
    fname : str or path-like
        A file with Matplotlib rc settings.
    fail_on_error : bool
        If True, raise an error when the parser fails to convert a parameter.
    use_default_template : bool
        If True, initialize with default parameters before updating with those
        in the given file. If False, the configuration class only contains the
        parameters specified in the file. (Useful for updating dicts.)
    """
    config_from_file = _rc_params_in_file(fname, fail_on_error=fail_on_error)

    if not use_default_template:
        return config_from_file

    with _api.suppress_matplotlib_deprecation_warning():
        config = RcParams({**rcParamsDefault, **config_from_file})

    if "".join(config['text.latex.preamble']):
        _log.info("""
*****************************************************************
You have the following UNSUPPORTED LaTeX preamble customizations:
%s
Please do not ask for support with these customizations active.
*****************************************************************
""", '\n'.join(config['text.latex.preamble']))
    _log.debug('loaded rc file %s', fname)

    return config


rcParamsDefault = _rc_params_in_file(
    cbook._get_data_path("matplotlibrc"),
    # Strip leading comment.
    transform=lambda line: line[1:] if line.startswith("#") else line,
    fail_on_error=True)
rcParamsDefault._update_raw(rcsetup._hardcoded_defaults)
rcParamsDefault._ensure_has_backend()

rcParams = RcParams()  # The global instance.
rcParams._update_raw(rcParamsDefault)
rcParams._update_raw(_rc_params_in_file(matplotlib_fname()))
rcParamsOrig = rcParams.copy()
with _api.suppress_matplotlib_deprecation_warning():
    # This also checks that all rcParams are indeed listed in the template.
    # Assigning to rcsetup.defaultParams is left only for backcompat.
    defaultParams = rcsetup.defaultParams = {
        # We want to resolve deprecated rcParams, but not backend...
        key: [(rcsetup._auto_backend_sentinel if key == "backend" else
               rcParamsDefault[key]),
              validator]
        for key, validator in rcsetup._validators.items()}
if rcParams['axes.formatter.use_locale']:
    locale.setlocale(locale.LC_ALL, '')


def rc(group, **kwargs):
    """
    Set the current `.rcParams`.  *group* is the grouping for the rc, e.g.,
    for ``lines.linewidth`` the group is ``lines``, for
    ``axes.facecolor``, the group is ``axes``, and so on.  Group may
    also be a list or tuple of group names, e.g., (*xtick*, *ytick*).
    *kwargs* is a dictionary attribute name/value pairs, e.g.,::

      rc('lines', linewidth=2, color='r')

    sets the current `.rcParams` and is equivalent to::

      rcParams['lines.linewidth'] = 2
      rcParams['lines.color'] = 'r'

    The following aliases are available to save typing for interactive users:

    =====   =================
    Alias   Property
    =====   =================
    'lw'    'linewidth'
    'ls'    'linestyle'
    'c'     'color'
    'fc'    'facecolor'
    'ec'    'edgecolor'
    'mew'   'markeredgewidth'
    'aa'    'antialiased'
    =====   =================

    Thus you could abbreviate the above call as::

          rc('lines', lw=2, c='r')

    Note you can use python's kwargs dictionary facility to store
    dictionaries of default parameters.  e.g., you can customize the
    font rc as follows::

      font = {'family' : 'monospace',
              'weight' : 'bold',
              'size'   : 'larger'}
      rc('font', **font)  # pass in the font dict as kwargs

    This enables you to easily switch between several configurations.  Use
    ``matplotlib.style.use('default')`` or :func:`~matplotlib.rcdefaults` to
    restore the default `.rcParams` after changes.

    Notes
    -----
    Similar functionality is available by using the normal dict interface, i.e.
    ``rcParams.update({"lines.linewidth": 2, ...})`` (but ``rcParams.update``
    does not support abbreviations or grouping).
    """

    aliases = {
        'lw':  'linewidth',
        'ls':  'linestyle',
        'c':   'color',
        'fc':  'facecolor',
        'ec':  'edgecolor',
        'mew': 'markeredgewidth',
        'aa':  'antialiased',
        }

    if isinstance(group, str):
        group = (group,)
    for g in group:
        for k, v in kwargs.items():
            name = aliases.get(k) or k
            key = f'{g}.{name}'
            try:
                rcParams[key] = v
            except KeyError as err:
                raise KeyError(('Unrecognized key "%s" for group "%s" and '
                                'name "%s"') % (key, g, name)) from err


def rcdefaults():
    """
    Restore the `.rcParams` from Matplotlib's internal default style.

    Style-blacklisted `.rcParams` (defined in
    ``matplotlib.style.core.STYLE_BLACKLIST``) are not updated.

    See Also
    --------
    matplotlib.rc_file_defaults
        Restore the `.rcParams` from the rc file originally loaded by
        Matplotlib.
    matplotlib.style.use
        Use a specific style file.  Call ``style.use('default')`` to restore
        the default style.
    """
    # Deprecation warnings were already handled when creating rcParamsDefault,
    # no need to reemit them here.
    with _api.suppress_matplotlib_deprecation_warning():
        from .style.core import STYLE_BLACKLIST
        rcParams.clear()
        rcParams.update({k: v for k, v in rcParamsDefault.items()
                         if k not in STYLE_BLACKLIST})


def rc_file_defaults():
    """
    Restore the `.rcParams` from the original rc file loaded by Matplotlib.

    Style-blacklisted `.rcParams` (defined in
    ``matplotlib.style.core.STYLE_BLACKLIST``) are not updated.
    """
    # Deprecation warnings were already handled when creating rcParamsOrig, no
    # need to reemit them here.
    with _api.suppress_matplotlib_deprecation_warning():
        from .style.core import STYLE_BLACKLIST
        rcParams.update({k: rcParamsOrig[k] for k in rcParamsOrig
                         if k not in STYLE_BLACKLIST})


def rc_file(fname, *, use_default_template=True):
    """
    Update `.rcParams` from file.

    Style-blacklisted `.rcParams` (defined in
    ``matplotlib.style.core.STYLE_BLACKLIST``) are not updated.

    Parameters
    ----------
    fname : str or path-like
        A file with Matplotlib rc settings.

    use_default_template : bool
        If True, initialize with default parameters before updating with those
        in the given file. If False, the current configuration persists
        and only the parameters specified in the file are updated.
    """
    # Deprecation warnings were already handled in rc_params_from_file, no need
    # to reemit them here.
    with _api.suppress_matplotlib_deprecation_warning():
        from .style.core import STYLE_BLACKLIST
        rc_from_file = rc_params_from_file(
            fname, use_default_template=use_default_template)
        rcParams.update({k: rc_from_file[k] for k in rc_from_file
                         if k not in STYLE_BLACKLIST})


@contextlib.contextmanager
def rc_context(rc=None, fname=None):
    """
    Return a context manager for temporarily changing rcParams.

    The :rc:`backend` will not be reset by the context manager.

    rcParams changed both through the context manager invocation and
    in the body of the context will be reset on context exit.

    Parameters
    ----------
    rc : dict
        The rcParams to temporarily set.
    fname : str or path-like
        A file with Matplotlib rc settings. If both *fname* and *rc* are given,
        settings from *rc* take precedence.

    See Also
    --------
    :ref:`customizing-with-matplotlibrc-files`

    Examples
    --------
    Passing explicit values via a dict::

        with mpl.rc_context({'interactive': False}):
            fig, ax = plt.subplots()
            ax.plot(range(3), range(3))
            fig.savefig('example.png')
            plt.close(fig)

    Loading settings from a file::

         with mpl.rc_context(fname='print.rc'):
             plt.plot(x, y)  # uses 'print.rc'

    Setting in the context body::

        with mpl.rc_context():
            # will be reset
            mpl.rcParams['lines.linewidth'] = 5
            plt.plot(x, y)

    """
    orig = dict(rcParams.copy())
    del orig['backend']
    try:
        if fname:
            rc_file(fname)
        if rc:
            rcParams.update(rc)
        yield
    finally:
        rcParams._update_raw(orig)  # Revert to the original rcs.


def use(backend, *, force=True):
    """
    Select the backend used for rendering and GUI integration.

    If pyplot is already imported, `~matplotlib.pyplot.switch_backend` is used
    and if the new backend is different than the current backend, all Figures
    will be closed.

    Parameters
    ----------
    backend : str
        The backend to switch to.  This can either be one of the standard
        backend names, which are case-insensitive:

        - interactive backends:
          GTK3Agg, GTK3Cairo, GTK4Agg, GTK4Cairo, MacOSX, nbAgg, notebook, QtAgg,
          QtCairo, TkAgg, TkCairo, WebAgg, WX, WXAgg, WXCairo, Qt5Agg, Qt5Cairo

        - non-interactive backends:
          agg, cairo, pdf, pgf, ps, svg, template

        or a string of the form: ``module://my.module.name``.

        notebook is a synonym for nbAgg.

        Switching to an interactive backend is not possible if an unrelated
        event loop has already been started (e.g., switching to GTK3Agg if a
        TkAgg window has already been opened).  Switching to a non-interactive
        backend is always possible.

    force : bool, default: True
        If True (the default), raise an `ImportError` if the backend cannot be
        set up (either because it fails to import, or because an incompatible
        GUI interactive framework is already running); if False, silently
        ignore the failure.

    See Also
    --------
    :ref:`backends`
    matplotlib.get_backend
    matplotlib.pyplot.switch_backend

    """
    name = rcsetup.validate_backend(backend)
    # don't (prematurely) resolve the "auto" backend setting
    if rcParams._get_backend_or_none() == name:
        # Nothing to do if the requested backend is already set
        pass
    else:
        # if pyplot is not already imported, do not import it.  Doing
        # so may trigger a `plt.switch_backend` to the _default_ backend
        # before we get a chance to change to the one the user just requested
        plt = sys.modules.get('matplotlib.pyplot')
        # if pyplot is imported, then try to change backends
        if plt is not None:
            try:
                # we need this import check here to re-raise if the
                # user does not have the libraries to support their
                # chosen backend installed.
                plt.switch_backend(name)
            except ImportError:
                if force:
                    raise
        # if we have not imported pyplot, then we can set the rcParam
        # value which will be respected when the user finally imports
        # pyplot
        else:
            rcParams['backend'] = backend
    # if the user has asked for a given backend, do not helpfully
    # fallback
    rcParams['backend_fallback'] = False


if os.environ.get('MPLBACKEND'):
    rcParams['backend'] = os.environ.get('MPLBACKEND')


def get_backend(*, auto_select=True):
    """
    Return the name of the current backend.

    Parameters
    ----------
    auto_select : bool, default: True
        Whether to trigger backend resolution if no backend has been
        selected so far. If True, this ensures that a valid backend
        is returned. If False, this returns None if no backend has been
        selected so far.

        .. versionadded:: 3.10

        .. admonition:: Provisional

           The *auto_select* flag is provisional. It may be changed or removed
           without prior warning.

    See Also
    --------
    matplotlib.use
    """
    if auto_select:
        return rcParams['backend']
    else:
        backend = rcParams._get('backend')
        if backend is rcsetup._auto_backend_sentinel:
            return None
        else:
            return backend


def interactive(b):
    """
    Set whether to redraw after every plotting command (e.g. `.pyplot.xlabel`).
    """
    rcParams['interactive'] = b


def is_interactive():
    """
    Return whether to redraw after every plotting command.

    .. note::

        This function is only intended for use in backends. End users should
        use `.pyplot.isinteractive` instead.
    """
    return rcParams['interactive']


def _val_or_rc(val, rc_name):
    """
    If *val* is None, return ``mpl.rcParams[rc_name]``, otherwise return val.
    """
    return val if val is not None else rcParams[rc_name]


def _init_tests():
    # The version of FreeType to install locally for running the tests. This must match
    # the value in `meson.build`.
    LOCAL_FREETYPE_VERSION = '2.6.1'

    from matplotlib import ft2font
    if (ft2font.__freetype_version__ != LOCAL_FREETYPE_VERSION or
            ft2font.__freetype_build_type__ != 'local'):
        _log.warning(
            "Matplotlib is not built with the correct FreeType version to run tests.  "
            "Rebuild without setting system-freetype=true in Meson setup options.  "
            "Expect many image comparison failures below.  "
            "Expected freetype version %s.  "
            "Found freetype version %s.  "
            "Freetype build type is %slocal.",
            LOCAL_FREETYPE_VERSION,
            ft2font.__freetype_version__,
            "" if ft2font.__freetype_build_type__ == 'local' else "not ")


def _replacer(data, value):
    """
    Either returns ``data[value]`` or passes ``data`` back, converts either to
    a sequence.
    """
    try:
        # if key isn't a string don't bother
        if isinstance(value, str):
            # try to use __getitem__
            value = data[value]
    except Exception:
        # key does not exist, silently fall back to key
        pass
    return cbook.sanitize_sequence(value)


def _label_from_arg(y, default_name):
    try:
        return y.name
    except AttributeError:
        if isinstance(default_name, str):
            return default_name
    return None


def _add_data_doc(docstring, replace_names):
    """
    Add documentation for a *data* field to the given docstring.

    Parameters
    ----------
    docstring : str
        The input docstring.
    replace_names : list of str or None
        The list of parameter names which arguments should be replaced by
        ``data[name]`` (if ``data[name]`` does not throw an exception).  If
        None, replacement is attempted for all arguments.

    Returns
    -------
    str
        The augmented docstring.
    """
    if (docstring is None
            or replace_names is not None and len(replace_names) == 0):
        return docstring
    docstring = inspect.cleandoc(docstring)

    data_doc = ("""\
    If given, all parameters also accept a string ``s``, which is
    interpreted as ``data[s]`` if ``s`` is a key in ``data``."""
                if replace_names is None else f"""\
    If given, the following parameters also accept a string ``s``, which is
    interpreted as ``data[s]`` if ``s`` is a key in ``data``:

    {', '.join(map('*{}*'.format, replace_names))}""")
    # using string replacement instead of formatting has the advantages
    # 1) simpler indent handling
    # 2) prevent problems with formatting characters '{', '%' in the docstring
    if _log.level <= logging.DEBUG:
        # test_data_parameter_replacement() tests against these log messages
        # make sure to keep message and test in sync
        if "data : indexable object, optional" not in docstring:
            _log.debug("data parameter docstring error: no data parameter")
        if 'DATA_PARAMETER_PLACEHOLDER' not in docstring:
            _log.debug("data parameter docstring error: missing placeholder")
    return docstring.replace('    DATA_PARAMETER_PLACEHOLDER', data_doc)


def _preprocess_data(func=None, *, replace_names=None, label_namer=None):
    """
    A decorator to add a 'data' kwarg to a function.

    When applied::

        @_preprocess_data()
        def func(ax, *args, **kwargs): ...

    the signature is modified to ``decorated(ax, *args, data=None, **kwargs)``
    with the following behavior:

    - if called with ``data=None``, forward the other arguments to ``func``;
    - otherwise, *data* must be a mapping; for any argument passed in as a
      string ``name``, replace the argument by ``data[name]`` (if this does not
      throw an exception), then forward the arguments to ``func``.

    In either case, any argument that is a `MappingView` is also converted to a
    list.

    Parameters
    ----------
    replace_names : list of str or None, default: None
        The list of parameter names for which lookup into *data* should be
        attempted. If None, replacement is attempted for all arguments.
    label_namer : str, default: None
        If set e.g. to "namer" (which must be a kwarg in the function's
        signature -- not as ``**kwargs``), if the *namer* argument passed in is
        a (string) key of *data* and no *label* kwarg is passed, then use the
        (string) value of the *namer* as *label*. ::

            @_preprocess_data(label_namer="foo")
            def func(foo, label=None): ...

            func("key", data={"key": value})
            # is equivalent to
            func.__wrapped__(value, label="key")
    """

    if func is None:  # Return the actual decorator.
        return functools.partial(
            _preprocess_data,
            replace_names=replace_names, label_namer=label_namer)

    sig = inspect.signature(func)
    varargs_name = None
    varkwargs_name = None
    arg_names = []
    params = list(sig.parameters.values())
    for p in params:
        if p.kind is Parameter.VAR_POSITIONAL:
            varargs_name = p.name
        elif p.kind is Parameter.VAR_KEYWORD:
            varkwargs_name = p.name
        else:
            arg_names.append(p.name)
    data_param = Parameter("data", Parameter.KEYWORD_ONLY, default=None)
    if varkwargs_name:
        params.insert(-1, data_param)
    else:
        params.append(data_param)
    new_sig = sig.replace(parameters=params)
    arg_names = arg_names[1:]  # remove the first "ax" / self arg

    assert {*arg_names}.issuperset(replace_names or []) or varkwargs_name, (
        "Matplotlib internal error: invalid replace_names "
        f"({replace_names!r}) for {func.__name__!r}")
    assert label_namer is None or label_namer in arg_names, (
        "Matplotlib internal error: invalid label_namer "
        f"({label_namer!r}) for {func.__name__!r}")

    @functools.wraps(func)
    def inner(ax, *args, data=None, **kwargs):
        if data is None:
            return func(
                ax,
                *map(cbook.sanitize_sequence, args),
                **{k: cbook.sanitize_sequence(v) for k, v in kwargs.items()})

        bound = new_sig.bind(ax, *args, **kwargs)
        auto_label = (bound.arguments.get(label_namer)
                      or bound.kwargs.get(label_namer))

        for k, v in bound.arguments.items():
            if k == varkwargs_name:
                for k1, v1 in v.items():
                    if replace_names is None or k1 in replace_names:
                        v[k1] = _replacer(data, v1)
            elif k == varargs_name:
                if replace_names is None:
                    bound.arguments[k] = tuple(_replacer(data, v1) for v1 in v)
            else:
                if replace_names is None or k in replace_names:
                    bound.arguments[k] = _replacer(data, v)

        new_args = bound.args
        new_kwargs = bound.kwargs

        args_and_kwargs = {**bound.arguments, **bound.kwargs}
        if label_namer and "label" not in args_and_kwargs:
            new_kwargs["label"] = _label_from_arg(
                args_and_kwargs.get(label_namer), auto_label)

        return func(*new_args, **new_kwargs)

    inner.__doc__ = _add_data_doc(inner.__doc__, replace_names)
    inner.__signature__ = new_sig
    return inner


_log.debug('interactive is %s', is_interactive())
_log.debug('platform is %s', sys.platform)


@_api.deprecated("3.10", alternative="matplotlib.cbook.sanitize_sequence")
def sanitize_sequence(data):
    return cbook.sanitize_sequence(data)


@_api.deprecated("3.10", alternative="matplotlib.rcsetup.validate_backend")
def validate_backend(s):
    return rcsetup.validate_backend(s)


# workaround: we must defer colormaps import to after loading rcParams, because
# colormap creation depends on rcParams
from matplotlib.cm import _colormaps as colormaps  # noqa: E402
from matplotlib.cm import _multivar_colormaps as multivar_colormaps  # noqa: E402
from matplotlib.cm import _bivar_colormaps as bivar_colormaps  # noqa: E402
from matplotlib.colors import _color_sequences as color_sequences  # noqa: E402

# === NexusCore/openenv\Lib\site-packages\matplotlib\tri\_triinterpolate.py ===
"""
Interpolation inside triangular grids.
"""

import numpy as np

from matplotlib import _api
from matplotlib.tri import Triangulation
from matplotlib.tri._trifinder import TriFinder
from matplotlib.tri._tritools import TriAnalyzer

__all__ = ('TriInterpolator', 'LinearTriInterpolator', 'CubicTriInterpolator')


class TriInterpolator:
    """
    Abstract base class for classes used to interpolate on a triangular grid.

    Derived classes implement the following methods:

    - ``__call__(x, y)``,
      where x, y are array-like point coordinates of the same shape, and
      that returns a masked array of the same shape containing the
      interpolated z-values.

    - ``gradient(x, y)``,
      where x, y are array-like point coordinates of the same
      shape, and that returns a list of 2 masked arrays of the same shape
      containing the 2 derivatives of the interpolator (derivatives of
      interpolated z values with respect to x and y).
    """

    def __init__(self, triangulation, z, trifinder=None):
        _api.check_isinstance(Triangulation, triangulation=triangulation)
        self._triangulation = triangulation

        self._z = np.asarray(z)
        if self._z.shape != self._triangulation.x.shape:
            raise ValueError("z array must have same length as triangulation x"
                             " and y arrays")

        _api.check_isinstance((TriFinder, None), trifinder=trifinder)
        self._trifinder = trifinder or self._triangulation.get_trifinder()

        # Default scaling factors : 1.0 (= no scaling)
        # Scaling may be used for interpolations for which the order of
        # magnitude of x, y has an impact on the interpolant definition.
        # Please refer to :meth:`_interpolate_multikeys` for details.
        self._unit_x = 1.0
        self._unit_y = 1.0

        # Default triangle renumbering: None (= no renumbering)
        # Renumbering may be used to avoid unnecessary computations
        # if complex calculations are done inside the Interpolator.
        # Please refer to :meth:`_interpolate_multikeys` for details.
        self._tri_renum = None

    # __call__ and gradient docstrings are shared by all subclasses
    # (except, if needed, relevant additions).
    # However these methods are only implemented in subclasses to avoid
    # confusion in the documentation.
    _docstring__call__ = """
        Returns a masked array containing interpolated values at the specified
        (x, y) points.

        Parameters
        ----------
        x, y : array-like
            x and y coordinates of the same shape and any number of
            dimensions.

        Returns
        -------
        np.ma.array
            Masked array of the same shape as *x* and *y*; values corresponding
            to (*x*, *y*) points outside of the triangulation are masked out.

        """

    _docstringgradient = r"""
        Returns a list of 2 masked arrays containing interpolated derivatives
        at the specified (x, y) points.

        Parameters
        ----------
        x, y : array-like
            x and y coordinates of the same shape and any number of
            dimensions.

        Returns
        -------
        dzdx, dzdy : np.ma.array
            2 masked arrays of the same shape as *x* and *y*; values
            corresponding to (x, y) points outside of the triangulation
            are masked out.
            The first returned array contains the values of
            :math:`\frac{\partial z}{\partial x}` and the second those of
            :math:`\frac{\partial z}{\partial y}`.

        """

    def _interpolate_multikeys(self, x, y, tri_index=None,
                               return_keys=('z',)):
        """
        Versatile (private) method defined for all TriInterpolators.

        :meth:`_interpolate_multikeys` is a wrapper around method
        :meth:`_interpolate_single_key` (to be defined in the child
        subclasses).
        :meth:`_interpolate_single_key actually performs the interpolation,
        but only for 1-dimensional inputs and at valid locations (inside
        unmasked triangles of the triangulation).

        The purpose of :meth:`_interpolate_multikeys` is to implement the
        following common tasks needed in all subclasses implementations:

        - calculation of containing triangles
        - dealing with more than one interpolation request at the same
          location (e.g., if the 2 derivatives are requested, it is
          unnecessary to compute the containing triangles twice)
        - scaling according to self._unit_x, self._unit_y
        - dealing with points outside of the grid (with fill value np.nan)
        - dealing with multi-dimensional *x*, *y* arrays: flattening for
          :meth:`_interpolate_params` call and final reshaping.

        (Note that np.vectorize could do most of those things very well for
        you, but it does it by function evaluations over successive tuples of
        the input arrays. Therefore, this tends to be more time-consuming than
        using optimized numpy functions - e.g., np.dot - which can be used
        easily on the flattened inputs, in the child-subclass methods
        :meth:`_interpolate_single_key`.)

        It is guaranteed that the calls to :meth:`_interpolate_single_key`
        will be done with flattened (1-d) array-like input parameters *x*, *y*
        and with flattened, valid `tri_index` arrays (no -1 index allowed).

        Parameters
        ----------
        x, y : array-like
            x and y coordinates where interpolated values are requested.
        tri_index : array-like of int, optional
            Array of the containing triangle indices, same shape as
            *x* and *y*. Defaults to None. If None, these indices
            will be computed by a TriFinder instance.
            (Note: For point outside the grid, tri_index[ipt] shall be -1).
        return_keys : tuple of keys from {'z', 'dzdx', 'dzdy'}
            Defines the interpolation arrays to return, and in which order.

        Returns
        -------
        list of arrays
            Each array-like contains the expected interpolated values in the
            order defined by *return_keys* parameter.
        """
        # Flattening and rescaling inputs arrays x, y
        # (initial shape is stored for output)
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        sh_ret = x.shape
        if x.shape != y.shape:
            raise ValueError("x and y shall have same shapes."
                             f" Given: {x.shape} and {y.shape}")
        x = np.ravel(x)
        y = np.ravel(y)
        x_scaled = x/self._unit_x
        y_scaled = y/self._unit_y
        size_ret = np.size(x_scaled)

        # Computes & ravels the element indexes, extract the valid ones.
        if tri_index is None:
            tri_index = self._trifinder(x, y)
        else:
            if tri_index.shape != sh_ret:
                raise ValueError(
                    "tri_index array is provided and shall"
                    " have same shape as x and y. Given: "
                    f"{tri_index.shape} and {sh_ret}")
            tri_index = np.ravel(tri_index)

        mask_in = (tri_index != -1)
        if self._tri_renum is None:
            valid_tri_index = tri_index[mask_in]
        else:
            valid_tri_index = self._tri_renum[tri_index[mask_in]]
        valid_x = x_scaled[mask_in]
        valid_y = y_scaled[mask_in]

        ret = []
        for return_key in return_keys:
            # Find the return index associated with the key.
            try:
                return_index = {'z': 0, 'dzdx': 1, 'dzdy': 2}[return_key]
            except KeyError as err:
                raise ValueError("return_keys items shall take values in"
                                 " {'z', 'dzdx', 'dzdy'}") from err

            # Sets the scale factor for f & df components
            scale = [1., 1./self._unit_x, 1./self._unit_y][return_index]

            # Computes the interpolation
            ret_loc = np.empty(size_ret, dtype=np.float64)
            ret_loc[~mask_in] = np.nan
            ret_loc[mask_in] = self._interpolate_single_key(
                return_key, valid_tri_index, valid_x, valid_y) * scale
            ret += [np.ma.masked_invalid(ret_loc.reshape(sh_ret), copy=False)]

        return ret

    def _interpolate_single_key(self, return_key, tri_index, x, y):
        """
        Interpolate at points belonging to the triangulation
        (inside an unmasked triangles).

        Parameters
        ----------
        return_key : {'z', 'dzdx', 'dzdy'}
            The requested values (z or its derivatives).
        tri_index : 1D int array
            Valid triangle index (cannot be -1).
        x, y : 1D arrays, same shape as `tri_index`
            Valid locations where interpolation is requested.

        Returns
        -------
        1-d array
            Returned array of the same size as *tri_index*
        """
        raise NotImplementedError("TriInterpolator subclasses" +
                                  "should implement _interpolate_single_key!")


class LinearTriInterpolator(TriInterpolator):
    """
    Linear interpolator on a triangular grid.

    Each triangle is represented by a plane so that an interpolated value at
    point (x, y) lies on the plane of the triangle containing (x, y).
    Interpolated values are therefore continuous across the triangulation, but
    their first derivatives are discontinuous at edges between triangles.

    Parameters
    ----------
    triangulation : `~matplotlib.tri.Triangulation`
        The triangulation to interpolate over.
    z : (npoints,) array-like
        Array of values, defined at grid points, to interpolate between.
    trifinder : `~matplotlib.tri.TriFinder`, optional
        If this is not specified, the Triangulation's default TriFinder will
        be used by calling `.Triangulation.get_trifinder`.

    Methods
    -------
    `__call__` (x, y) : Returns interpolated values at (x, y) points.
    `gradient` (x, y) : Returns interpolated derivatives at (x, y) points.

    """
    def __init__(self, triangulation, z, trifinder=None):
        super().__init__(triangulation, z, trifinder)

        # Store plane coefficients for fast interpolation calculations.
        self._plane_coefficients = \
            self._triangulation.calculate_plane_coefficients(self._z)

    def __call__(self, x, y):
        return self._interpolate_multikeys(x, y, tri_index=None,
                                           return_keys=('z',))[0]
    __call__.__doc__ = TriInterpolator._docstring__call__

    def gradient(self, x, y):
        return self._interpolate_multikeys(x, y, tri_index=None,
                                           return_keys=('dzdx', 'dzdy'))
    gradient.__doc__ = TriInterpolator._docstringgradient

    def _interpolate_single_key(self, return_key, tri_index, x, y):
        _api.check_in_list(['z', 'dzdx', 'dzdy'], return_key=return_key)
        if return_key == 'z':
            return (self._plane_coefficients[tri_index, 0]*x +
                    self._plane_coefficients[tri_index, 1]*y +
                    self._plane_coefficients[tri_index, 2])
        elif return_key == 'dzdx':
            return self._plane_coefficients[tri_index, 0]
        else:  # 'dzdy'
            return self._plane_coefficients[tri_index, 1]


class CubicTriInterpolator(TriInterpolator):
    r"""
    Cubic interpolator on a triangular grid.

    In one-dimension - on a segment - a cubic interpolating function is
    defined by the values of the function and its derivative at both ends.
    This is almost the same in 2D inside a triangle, except that the values
    of the function and its 2 derivatives have to be defined at each triangle
    node.

    The CubicTriInterpolator takes the value of the function at each node -
    provided by the user - and internally computes the value of the
    derivatives, resulting in a smooth interpolation.
    (As a special feature, the user can also impose the value of the
    derivatives at each node, but this is not supposed to be the common
    usage.)

    Parameters
    ----------
    triangulation : `~matplotlib.tri.Triangulation`
        The triangulation to interpolate over.
    z : (npoints,) array-like
        Array of values, defined at grid points, to interpolate between.
    kind : {'min_E', 'geom', 'user'}, optional
        Choice of the smoothing algorithm, in order to compute
        the interpolant derivatives (defaults to 'min_E'):

        - if 'min_E': (default) The derivatives at each node is computed
          to minimize a bending energy.
        - if 'geom': The derivatives at each node is computed as a
          weighted average of relevant triangle normals. To be used for
          speed optimization (large grids).
        - if 'user': The user provides the argument *dz*, no computation
          is hence needed.

    trifinder : `~matplotlib.tri.TriFinder`, optional
        If not specified, the Triangulation's default TriFinder will
        be used by calling `.Triangulation.get_trifinder`.
    dz : tuple of array-likes (dzdx, dzdy), optional
        Used only if  *kind* ='user'. In this case *dz* must be provided as
        (dzdx, dzdy) where dzdx, dzdy are arrays of the same shape as *z* and
        are the interpolant first derivatives at the *triangulation* points.

    Methods
    -------
    `__call__` (x, y) : Returns interpolated values at (x, y) points.
    `gradient` (x, y) : Returns interpolated derivatives at (x, y) points.

    Notes
    -----
    This note is a bit technical and details how the cubic interpolation is
    computed.

    The interpolation is based on a Clough-Tocher subdivision scheme of
    the *triangulation* mesh (to make it clearer, each triangle of the
    grid will be divided in 3 child-triangles, and on each child triangle
    the interpolated function is a cubic polynomial of the 2 coordinates).
    This technique originates from FEM (Finite Element Method) analysis;
    the element used is a reduced Hsieh-Clough-Tocher (HCT)
    element. Its shape functions are described in [1]_.
    The assembled function is guaranteed to be C1-smooth, i.e. it is
    continuous and its first derivatives are also continuous (this
    is easy to show inside the triangles but is also true when crossing the
    edges).

    In the default case (*kind* ='min_E'), the interpolant minimizes a
    curvature energy on the functional space generated by the HCT element
    shape functions - with imposed values but arbitrary derivatives at each
    node. The minimized functional is the integral of the so-called total
    curvature (implementation based on an algorithm from [2]_ - PCG sparse
    solver):

    .. math::

        E(z) = \frac{1}{2} \int_{\Omega} \left(
            \left( \frac{\partial^2{z}}{\partial{x}^2} \right)^2 +
            \left( \frac{\partial^2{z}}{\partial{y}^2} \right)^2 +
            2\left( \frac{\partial^2{z}}{\partial{y}\partial{x}} \right)^2
        \right) dx\,dy

    If the case *kind* ='geom' is chosen by the user, a simple geometric
    approximation is used (weighted average of the triangle normal
    vectors), which could improve speed on very large grids.

    References
    ----------
    .. [1] Michel Bernadou, Kamal Hassan, "Basis functions for general
        Hsieh-Clough-Tocher triangles, complete or reduced.",
        International Journal for Numerical Methods in Engineering,
        17(5):784 - 789. 2.01.
    .. [2] C.T. Kelley, "Iterative Methods for Optimization".

    """
    def __init__(self, triangulation, z, kind='min_E', trifinder=None,
                 dz=None):
        super().__init__(triangulation, z, trifinder)

        # Loads the underlying c++ _triangulation.
        # (During loading, reordering of triangulation._triangles may occur so
        # that all final triangles are now anti-clockwise)
        self._triangulation.get_cpp_triangulation()

        # To build the stiffness matrix and avoid zero-energy spurious modes
        # we will only store internally the valid (unmasked) triangles and
        # the necessary (used) points coordinates.
        # 2 renumbering tables need to be computed and stored:
        #  - a triangle renum table in order to translate the result from a
        #    TriFinder instance into the internal stored triangle number.
        #  - a node renum table to overwrite the self._z values into the new
        #    (used) node numbering.
        tri_analyzer = TriAnalyzer(self._triangulation)
        (compressed_triangles, compressed_x, compressed_y, tri_renum,
         node_renum) = tri_analyzer._get_compressed_triangulation()
        self._triangles = compressed_triangles
        self._tri_renum = tri_renum
        # Taking into account the node renumbering in self._z:
        valid_node = (node_renum != -1)
        self._z[node_renum[valid_node]] = self._z[valid_node]

        # Computing scale factors
        self._unit_x = np.ptp(compressed_x)
        self._unit_y = np.ptp(compressed_y)
        self._pts = np.column_stack([compressed_x / self._unit_x,
                                     compressed_y / self._unit_y])
        # Computing triangle points
        self._tris_pts = self._pts[self._triangles]
        # Computing eccentricities
        self._eccs = self._compute_tri_eccentricities(self._tris_pts)
        # Computing dof estimations for HCT triangle shape function
        _api.check_in_list(['user', 'geom', 'min_E'], kind=kind)
        self._dof = self._compute_dof(kind, dz=dz)
        # Loading HCT element
        self._ReferenceElement = _ReducedHCT_Element()

    def __call__(self, x, y):
        return self._interpolate_multikeys(x, y, tri_index=None,
                                           return_keys=('z',))[0]
    __call__.__doc__ = TriInterpolator._docstring__call__

    def gradient(self, x, y):
        return self._interpolate_multikeys(x, y, tri_index=None,
                                           return_keys=('dzdx', 'dzdy'))
    gradient.__doc__ = TriInterpolator._docstringgradient

    def _interpolate_single_key(self, return_key, tri_index, x, y):
        _api.check_in_list(['z', 'dzdx', 'dzdy'], return_key=return_key)
        tris_pts = self._tris_pts[tri_index]
        alpha = self._get_alpha_vec(x, y, tris_pts)
        ecc = self._eccs[tri_index]
        dof = np.expand_dims(self._dof[tri_index], axis=1)
        if return_key == 'z':
            return self._ReferenceElement.get_function_values(
                alpha, ecc, dof)
        else:  # 'dzdx', 'dzdy'
            J = self._get_jacobian(tris_pts)
            dzdx = self._ReferenceElement.get_function_derivatives(
                alpha, J, ecc, dof)
            if return_key == 'dzdx':
                return dzdx[:, 0, 0]
            else:
                return dzdx[:, 1, 0]

    def _compute_dof(self, kind, dz=None):
        """
        Compute and return nodal dofs according to kind.

        Parameters
        ----------
        kind : {'min_E', 'geom', 'user'}
            Choice of the _DOF_estimator subclass to estimate the gradient.
        dz : tuple of array-likes (dzdx, dzdy), optional
            Used only if *kind*=user; in this case passed to the
            :class:`_DOF_estimator_user`.

        Returns
        -------
        array-like, shape (npts, 2)
            Estimation of the gradient at triangulation nodes (stored as
            degree of freedoms of reduced-HCT triangle elements).
        """
        if kind == 'user':
            if dz is None:
                raise ValueError("For a CubicTriInterpolator with "
                                 "*kind*='user', a valid *dz* "
                                 "argument is expected.")
            TE = _DOF_estimator_user(self, dz=dz)
        elif kind == 'geom':
            TE = _DOF_estimator_geom(self)
        else:  # 'min_E', checked in __init__
            TE = _DOF_estimator_min_E(self)
        return TE.compute_dof_from_df()

    @staticmethod
    def _get_alpha_vec(x, y, tris_pts):
        """
        Fast (vectorized) function to compute barycentric coordinates alpha.

        Parameters
        ----------
        x, y : array-like of dim 1 (shape (nx,))
            Coordinates of the points whose points barycentric coordinates are
            requested.
        tris_pts : array like of dim 3 (shape: (nx, 3, 2))
            Coordinates of the containing triangles apexes.

        Returns
        -------
        array of dim 2 (shape (nx, 3))
            Barycentric coordinates of the points inside the containing
            triangles.
        """
        ndim = tris_pts.ndim-2

        a = tris_pts[:, 1, :] - tris_pts[:, 0, :]
        b = tris_pts[:, 2, :] - tris_pts[:, 0, :]
        abT = np.stack([a, b], axis=-1)
        ab = _transpose_vectorized(abT)
        OM = np.stack([x, y], axis=1) - tris_pts[:, 0, :]

        metric = ab @ abT
        # Here we try to deal with the colinear cases.
        # metric_inv is in this case set to the Moore-Penrose pseudo-inverse
        # meaning that we will still return a set of valid barycentric
        # coordinates.
        metric_inv = _pseudo_inv22sym_vectorized(metric)
        Covar = ab @ _transpose_vectorized(np.expand_dims(OM, ndim))
        ksi = metric_inv @ Covar
        alpha = _to_matrix_vectorized([
            [1-ksi[:, 0, 0]-ksi[:, 1, 0]], [ksi[:, 0, 0]], [ksi[:, 1, 0]]])
        return alpha

    @staticmethod
    def _get_jacobian(tris_pts):
        """
        Fast (vectorized) function to compute triangle jacobian matrix.

        Parameters
        ----------
        tris_pts : array like of dim 3 (shape: (nx, 3, 2))
            Coordinates of the containing triangles apexes.

        Returns
        -------
        array of dim 3 (shape (nx, 2, 2))
            Barycentric coordinates of the points inside the containing
            triangles.
            J[itri, :, :] is the jacobian matrix at apex 0 of the triangle
            itri, so that the following (matrix) relationship holds:
               [dz/dksi] = [J] x [dz/dx]
            with x: global coordinates
                 ksi: element parametric coordinates in triangle first apex
                 local basis.
        """
        a = np.array(tris_pts[:, 1, :] - tris_pts[:, 0, :])
        b = np.array(tris_pts[:, 2, :] - tris_pts[:, 0, :])
        J = _to_matrix_vectorized([[a[:, 0], a[:, 1]],
                                   [b[:, 0], b[:, 1]]])
        return J

    @staticmethod
    def _compute_tri_eccentricities(tris_pts):
        """
        Compute triangle eccentricities.

        Parameters
        ----------
        tris_pts : array like of dim 3 (shape: (nx, 3, 2))
            Coordinates of the triangles apexes.

        Returns
        -------
        array like of dim 2 (shape: (nx, 3))
            The so-called eccentricity parameters [1] needed for HCT triangular
            element.
        """
        a = np.expand_dims(tris_pts[:, 2, :] - tris_pts[:, 1, :], axis=2)
        b = np.expand_dims(tris_pts[:, 0, :] - tris_pts[:, 2, :], axis=2)
        c = np.expand_dims(tris_pts[:, 1, :] - tris_pts[:, 0, :], axis=2)
        # Do not use np.squeeze, this is dangerous if only one triangle
        # in the triangulation...
        dot_a = (_transpose_vectorized(a) @ a)[:, 0, 0]
        dot_b = (_transpose_vectorized(b) @ b)[:, 0, 0]
        dot_c = (_transpose_vectorized(c) @ c)[:, 0, 0]
        # Note that this line will raise a warning for dot_a, dot_b or dot_c
        # zeros, but we choose not to support triangles with duplicate points.
        return _to_matrix_vectorized([[(dot_c-dot_b) / dot_a],
                                      [(dot_a-dot_c) / dot_b],
                                      [(dot_b-dot_a) / dot_c]])


# FEM element used for interpolation and for solving minimisation
# problem (Reduced HCT element)
class _ReducedHCT_Element:
    """
    Implementation of reduced HCT triangular element with explicit shape
    functions.

    Computes z, dz, d2z and the element stiffness matrix for bending energy:
    E(f) = integral( (d2z/dx2 + d2z/dy2)**2 dA)

    *** Reference for the shape functions: ***
    [1] Basis functions for general Hsieh-Clough-Tocher _triangles, complete or
        reduced.
        Michel Bernadou, Kamal Hassan
        International Journal for Numerical Methods in Engineering.
        17(5):784 - 789.  2.01

    *** Element description: ***
    9 dofs: z and dz given at 3 apex
    C1 (conform)

    """
    # 1) Loads matrices to generate shape functions as a function of
    #    triangle eccentricities - based on [1] p.11 '''
    M = np.array([
        [ 0.00, 0.00, 0.00,  4.50,  4.50, 0.00, 0.00, 0.00, 0.00, 0.00],
        [-0.25, 0.00, 0.00,  0.50,  1.25, 0.00, 0.00, 0.00, 0.00, 0.00],
        [-0.25, 0.00, 0.00,  1.25,  0.50, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.50, 1.00, 0.00, -1.50,  0.00, 3.00, 3.00, 0.00, 0.00, 3.00],
        [ 0.00, 0.00, 0.00, -0.25,  0.25, 0.00, 1.00, 0.00, 0.00, 0.50],
        [ 0.25, 0.00, 0.00, -0.50, -0.25, 1.00, 0.00, 0.00, 0.00, 1.00],
        [ 0.50, 0.00, 1.00,  0.00, -1.50, 0.00, 0.00, 3.00, 3.00, 3.00],
        [ 0.25, 0.00, 0.00, -0.25, -0.50, 0.00, 0.00, 0.00, 1.00, 1.00],
        [ 0.00, 0.00, 0.00,  0.25, -0.25, 0.00, 0.00, 1.00, 0.00, 0.50]])
    M0 = np.array([
        [ 0.00, 0.00, 0.00,  0.00,  0.00, 0.00, 0.00, 0.00, 0.00,  0.00],
        [ 0.00, 0.00, 0.00,  0.00,  0.00, 0.00, 0.00, 0.00, 0.00,  0.00],
        [ 0.00, 0.00, 0.00,  0.00,  0.00, 0.00, 0.00, 0.00, 0.00,  0.00],
        [-1.00, 0.00, 0.00,  1.50,  1.50, 0.00, 0.00, 0.00, 0.00, -3.00],
        [-0.50, 0.00, 0.00,  0.75,  0.75, 0.00, 0.00, 0.00, 0.00, -1.50],
        [ 0.00, 0.00, 0.00,  0.00,  0.00, 0.00, 0.00, 0.00, 0.00,  0.00],
        [ 1.00, 0.00, 0.00, -1.50, -1.50, 0.00, 0.00, 0.00, 0.00,  3.00],
        [ 0.00, 0.00, 0.00,  0.00,  0.00, 0.00, 0.00, 0.00, 0.00,  0.00],
        [ 0.50, 0.00, 0.00, -0.75, -0.75, 0.00, 0.00, 0.00, 0.00,  1.50]])
    M1 = np.array([
        [-0.50, 0.00, 0.00,  1.50, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.00, 0.00, 0.00,  0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        [-0.25, 0.00, 0.00,  0.75, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.00, 0.00, 0.00,  0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.00, 0.00, 0.00,  0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.00, 0.00, 0.00,  0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.50, 0.00, 0.00, -1.50, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.25, 0.00, 0.00, -0.75, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.00, 0.00, 0.00,  0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00]])
    M2 = np.array([
        [ 0.50, 0.00, 0.00, 0.00, -1.50, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.25, 0.00, 0.00, 0.00, -0.75, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.00, 0.00, 0.00, 0.00,  0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        [-0.50, 0.00, 0.00, 0.00,  1.50, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.00, 0.00, 0.00, 0.00,  0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        [-0.25, 0.00, 0.00, 0.00,  0.75, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.00, 0.00, 0.00, 0.00,  0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.00, 0.00, 0.00, 0.00,  0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
        [ 0.00, 0.00, 0.00, 0.00,  0.00, 0.00, 0.00, 0.00, 0.00, 0.00]])

    # 2) Loads matrices to rotate components of gradient & Hessian
    #    vectors in the reference basis of triangle first apex (a0)
    rotate_dV = np.array([[ 1.,  0.], [ 0.,  1.],
                          [ 0.,  1.], [-1., -1.],
                          [-1., -1.], [ 1.,  0.]])

    rotate_d2V = np.array([[1., 0., 0.], [0., 1., 0.], [ 0.,  0.,  1.],
                           [0., 1., 0.], [1., 1., 1.], [ 0., -2., -1.],
                           [1., 1., 1.], [1., 0., 0.], [-2.,  0., -1.]])

    # 3) Loads Gauss points & weights on the 3 sub-_triangles for P2
    #    exact integral - 3 points on each subtriangles.
    # NOTE: as the 2nd derivative is discontinuous , we really need those 9
    # points!
    n_gauss = 9
    gauss_pts = np.array([[13./18.,  4./18.,  1./18.],
                          [ 4./18., 13./18.,  1./18.],
                          [ 7./18.,  7./18.,  4./18.],
                          [ 1./18., 13./18.,  4./18.],
                          [ 1./18.,  4./18., 13./18.],
                          [ 4./18.,  7./18.,  7./18.],
                          [ 4./18.,  1./18., 13./18.],
                          [13./18.,  1./18.,  4./18.],
                          [ 7./18.,  4./18.,  7./18.]], dtype=np.float64)
    gauss_w = np.ones([9], dtype=np.float64) / 9.

    #  4) Stiffness matrix for curvature energy
    E = np.array([[1., 0., 0.], [0., 1., 0.], [0., 0., 2.]])

    #  5) Loads the matrix to compute DOF_rot from tri_J at apex 0
    J0_to_J1 = np.array([[-1.,  1.], [-1.,  0.]])
    J0_to_J2 = np.array([[ 0., -1.], [ 1., -1.]])

    def get_function_values(self, alpha, ecc, dofs):
        """
        Parameters
        ----------
        alpha : is a (N x 3 x 1) array (array of column-matrices) of
        barycentric coordinates,
        ecc : is a (N x 3 x 1) array (array of column-matrices) of triangle
        eccentricities,
        dofs : is a (N x 1 x 9) arrays (arrays of row-matrices) of computed
        degrees of freedom.

        Returns
        -------
        Returns the N-array of interpolated function values.
        """
        subtri = np.argmin(alpha, axis=1)[:, 0]
        ksi = _roll_vectorized(alpha, -subtri, axis=0)
        E = _roll_vectorized(ecc, -subtri, axis=0)
        x = ksi[:, 0, 0]
        y = ksi[:, 1, 0]
        z = ksi[:, 2, 0]
        x_sq = x*x
        y_sq = y*y
        z_sq = z*z
        V = _to_matrix_vectorized([
            [x_sq*x], [y_sq*y], [z_sq*z], [x_sq*z], [x_sq*y], [y_sq*x],
            [y_sq*z], [z_sq*y], [z_sq*x], [x*y*z]])
        prod = self.M @ V
        prod += _scalar_vectorized(E[:, 0, 0], self.M0 @ V)
        prod += _scalar_vectorized(E[:, 1, 0], self.M1 @ V)
        prod += _scalar_vectorized(E[:, 2, 0], self.M2 @ V)
        s = _roll_vectorized(prod, 3*subtri, axis=0)
        return (dofs @ s)[:, 0, 0]

    def get_function_derivatives(self, alpha, J, ecc, dofs):
        """
        Parameters
        ----------
        *alpha* is a (N x 3 x 1) array (array of column-matrices of
        barycentric coordinates)
        *J* is a (N x 2 x 2) array of jacobian matrices (jacobian matrix at
        triangle first apex)
        *ecc* is a (N x 3 x 1) array (array of column-matrices of triangle
        eccentricities)
        *dofs* is a (N x 1 x 9) arrays (arrays of row-matrices) of computed
        degrees of freedom.

        Returns
        -------
        Returns the values of interpolated function derivatives [dz/dx, dz/dy]
        in global coordinates at locations alpha, as a column-matrices of
        shape (N x 2 x 1).
        """
        subtri = np.argmin(alpha, axis=1)[:, 0]
        ksi = _roll_vectorized(alpha, -subtri, axis=0)
        E = _roll_vectorized(ecc, -subtri, axis=0)
        x = ksi[:, 0, 0]
        y = ksi[:, 1, 0]
        z = ksi[:, 2, 0]
        x_sq = x*x
        y_sq = y*y
        z_sq = z*z
        dV = _to_matrix_vectorized([
            [    -3.*x_sq,     -3.*x_sq],
            [     3.*y_sq,           0.],
            [          0.,      3.*z_sq],
            [     -2.*x*z, -2.*x*z+x_sq],
            [-2.*x*y+x_sq,      -2.*x*y],
            [ 2.*x*y-y_sq,        -y_sq],
            [      2.*y*z,         y_sq],
            [        z_sq,       2.*y*z],
            [       -z_sq,  2.*x*z-z_sq],
            [     x*z-y*z,      x*y-y*z]])
        # Puts back dV in first apex basis
        dV = dV @ _extract_submatrices(
            self.rotate_dV, subtri, block_size=2, axis=0)

        prod = self.M @ dV
        prod += _scalar_vectorized(E[:, 0, 0], self.M0 @ dV)
        prod += _scalar_vectorized(E[:, 1, 0], self.M1 @ dV)
        prod += _scalar_vectorized(E[:, 2, 0], self.M2 @ dV)
        dsdksi = _roll_vectorized(prod, 3*subtri, axis=0)
        dfdksi = dofs @ dsdksi
        # In global coordinates:
        # Here we try to deal with the simplest colinear cases, returning a
        # null matrix.
        J_inv = _safe_inv22_vectorized(J)
        dfdx = J_inv @ _transpose_vectorized(dfdksi)
        return dfdx

    def get_function_hessians(self, alpha, J, ecc, dofs):
        """
        Parameters
        ----------
        *alpha* is a (N x 3 x 1) array (array of column-matrices) of
        barycentric coordinates
        *J* is a (N x 2 x 2) array of jacobian matrices (jacobian matrix at
        triangle first apex)
        *ecc* is a (N x 3 x 1) array (array of column-matrices) of triangle
        eccentricities
        *dofs* is a (N x 1 x 9) arrays (arrays of row-matrices) of computed
        degrees of freedom.

        Returns
        -------
        Returns the values of interpolated function 2nd-derivatives
        [d2z/dx2, d2z/dy2, d2z/dxdy] in global coordinates at locations alpha,
        as a column-matrices of shape (N x 3 x 1).
        """
        d2sdksi2 = self.get_d2Sidksij2(alpha, ecc)
        d2fdksi2 = dofs @ d2sdksi2
        H_rot = self.get_Hrot_from_J(J)
        d2fdx2 = d2fdksi2 @ H_rot
        return _transpose_vectorized(d2fdx2)

    def get_d2Sidksij2(self, alpha, ecc):
        """
        Parameters
        ----------
        *alpha* is a (N x 3 x 1) array (array of column-matrices) of
        barycentric coordinates
        *ecc* is a (N x 3 x 1) array (array of column-matrices) of triangle
        eccentricities

        Returns
        -------
        Returns the arrays d2sdksi2 (N x 3 x 1) Hessian of shape functions
        expressed in covariant coordinates in first apex basis.
        """
        subtri = np.argmin(alpha, axis=1)[:, 0]
        ksi = _roll_vectorized(alpha, -subtri, axis=0)
        E = _roll_vectorized(ecc, -subtri, axis=0)
        x = ksi[:, 0, 0]
        y = ksi[:, 1, 0]
        z = ksi[:, 2, 0]
        d2V = _to_matrix_vectorized([
            [     6.*x,      6.*x,      6.*x],
            [     6.*y,        0.,        0.],
            [       0.,      6.*z,        0.],
            [     2.*z, 2.*z-4.*x, 2.*z-2.*x],
            [2.*y-4.*x,      2.*y, 2.*y-2.*x],
            [2.*x-4.*y,        0.,     -2.*y],
            [     2.*z,        0.,      2.*y],
            [       0.,      2.*y,      2.*z],
            [       0., 2.*x-4.*z,     -2.*z],
            [    -2.*z,     -2.*y,     x-y-z]])
        # Puts back d2V in first apex basis
        d2V = d2V @ _extract_submatrices(
            self.rotate_d2V, subtri, block_size=3, axis=0)
        prod = self.M @ d2V
        prod += _scalar_vectorized(E[:, 0, 0], self.M0 @ d2V)
        prod += _scalar_vectorized(E[:, 1, 0], self.M1 @ d2V)
        prod += _scalar_vectorized(E[:, 2, 0], self.M2 @ d2V)
        d2sdksi2 = _roll_vectorized(prod, 3*subtri, axis=0)
        return d2sdksi2

    def get_bending_matrices(self, J, ecc):
        """
        Parameters
        ----------
        *J* is a (N x 2 x 2) array of jacobian matrices (jacobian matrix at
        triangle first apex)
        *ecc* is a (N x 3 x 1) array (array of column-matrices) of triangle
        eccentricities

        Returns
        -------
        Returns the element K matrices for bending energy expressed in
        GLOBAL nodal coordinates.
        K_ij = integral [ (d2zi/dx2 + d2zi/dy2) * (d2zj/dx2 + d2zj/dy2) dA]
        tri_J is needed to rotate dofs from local basis to global basis
        """
        n = np.size(ecc, 0)

        # 1) matrix to rotate dofs in global coordinates
        J1 = self.J0_to_J1 @ J
        J2 = self.J0_to_J2 @ J
        DOF_rot = np.zeros([n, 9, 9], dtype=np.float64)
        DOF_rot[:, 0, 0] = 1
        DOF_rot[:, 3, 3] = 1
        DOF_rot[:, 6, 6] = 1
        DOF_rot[:, 1:3, 1:3] = J
        DOF_rot[:, 4:6, 4:6] = J1
        DOF_rot[:, 7:9, 7:9] = J2

        # 2) matrix to rotate Hessian in global coordinates.
        H_rot, area = self.get_Hrot_from_J(J, return_area=True)

        # 3) Computes stiffness matrix
        # Gauss quadrature.
        K = np.zeros([n, 9, 9], dtype=np.float64)
        weights = self.gauss_w
        pts = self.gauss_pts
        for igauss in range(self.n_gauss):
            alpha = np.tile(pts[igauss, :], n).reshape(n, 3)
            alpha = np.expand_dims(alpha, 2)
            weight = weights[igauss]
            d2Skdksi2 = self.get_d2Sidksij2(alpha, ecc)
            d2Skdx2 = d2Skdksi2 @ H_rot
            K += weight * (d2Skdx2 @ self.E @ _transpose_vectorized(d2Skdx2))

        # 4) With nodal (not elem) dofs
        K = _transpose_vectorized(DOF_rot) @ K @ DOF_rot

        # 5) Need the area to compute total element energy
        return _scalar_vectorized(area, K)

    def get_Hrot_from_J(self, J, return_area=False):
        """
        Parameters
        ----------
        *J* is a (N x 2 x 2) array of jacobian matrices (jacobian matrix at
        triangle first apex)

        Returns
        -------
        Returns H_rot used to rotate Hessian from local basis of first apex,
        to global coordinates.
        if *return_area* is True, returns also the triangle area (0.5*det(J))
        """
        # Here we try to deal with the simplest colinear cases; a null
        # energy and area is imposed.
        J_inv = _safe_inv22_vectorized(J)
        Ji00 = J_inv[:, 0, 0]
        Ji11 = J_inv[:, 1, 1]
        Ji10 = J_inv[:, 1, 0]
        Ji01 = J_inv[:, 0, 1]
        H_rot = _to_matrix_vectorized([
            [Ji00*Ji00, Ji10*Ji10, Ji00*Ji10],
            [Ji01*Ji01, Ji11*Ji11, Ji01*Ji11],
            [2*Ji00*Ji01, 2*Ji11*Ji10, Ji00*Ji11+Ji10*Ji01]])
        if not return_area:
            return H_rot
        else:
            area = 0.5 * (J[:, 0, 0]*J[:, 1, 1] - J[:, 0, 1]*J[:, 1, 0])
            return H_rot, area

    def get_Kff_and_Ff(self, J, ecc, triangles, Uc):
        """
        Build K and F for the following elliptic formulation:
        minimization of curvature energy with value of function at node
        imposed and derivatives 'free'.

        Build the global Kff matrix in cco format.
        Build the full Ff vec Ff = - Kfc x Uc.

        Parameters
        ----------
        *J* is a (N x 2 x 2) array of jacobian matrices (jacobian matrix at
        triangle first apex)
        *ecc* is a (N x 3 x 1) array (array of column-matrices) of triangle
        eccentricities
        *triangles* is a (N x 3) array of nodes indexes.
        *Uc* is (N x 3) array of imposed displacements at nodes

        Returns
        -------
        (Kff_rows, Kff_cols, Kff_vals) Kff matrix in coo format - Duplicate
        (row, col) entries must be summed.
        Ff: force vector - dim npts * 3
        """
        ntri = np.size(ecc, 0)
        vec_range = np.arange(ntri, dtype=np.int32)
        c_indices = np.full(ntri, -1, dtype=np.int32)  # for unused dofs, -1
        f_dof = [1, 2, 4, 5, 7, 8]
        c_dof = [0, 3, 6]

        # vals, rows and cols indices in global dof numbering
        f_dof_indices = _to_matrix_vectorized([[
            c_indices, triangles[:, 0]*2, triangles[:, 0]*2+1,
            c_indices, triangles[:, 1]*2, triangles[:, 1]*2+1,
            c_indices, triangles[:, 2]*2, triangles[:, 2]*2+1]])

        expand_indices = np.ones([ntri, 9, 1], dtype=np.int32)
        f_row_indices = _transpose_vectorized(expand_indices @ f_dof_indices)
        f_col_indices = expand_indices @ f_dof_indices
        K_elem = self.get_bending_matrices(J, ecc)

        # Extracting sub-matrices
        # Explanation & notations:
        # * Subscript f denotes 'free' degrees of freedom (i.e. dz/dx, dz/dx)
        # * Subscript c denotes 'condensated' (imposed) degrees of freedom
        #    (i.e. z at all nodes)
        # * F = [Ff, Fc] is the force vector
        # * U = [Uf, Uc] is the imposed dof vector
        #        [ Kff Kfc ]
        # * K =  [         ]  is the laplacian stiffness matrix
        #        [ Kcf Kff ]
        # * As F = K x U one gets straightforwardly: Ff = - Kfc x Uc

        # Computing Kff stiffness matrix in sparse coo format
        Kff_vals = np.ravel(K_elem[np.ix_(vec_range, f_dof, f_dof)])
        Kff_rows = np.ravel(f_row_indices[np.ix_(vec_range, f_dof, f_dof)])
        Kff_cols = np.ravel(f_col_indices[np.ix_(vec_range, f_dof, f_dof)])

        # Computing Ff force vector in sparse coo format
        Kfc_elem = K_elem[np.ix_(vec_range, f_dof, c_dof)]
        Uc_elem = np.expand_dims(Uc, axis=2)
        Ff_elem = -(Kfc_elem @ Uc_elem)[:, :, 0]
        Ff_indices = f_dof_indices[np.ix_(vec_range, [0], f_dof)][:, 0, :]

        # Extracting Ff force vector in dense format
        # We have to sum duplicate indices -  using bincount
        Ff = np.bincount(np.ravel(Ff_indices), weights=np.ravel(Ff_elem))
        return Kff_rows, Kff_cols, Kff_vals, Ff


# :class:_DOF_estimator, _DOF_estimator_user, _DOF_estimator_geom,
# _DOF_estimator_min_E
# Private classes used to compute the degree of freedom of each triangular
# element for the TriCubicInterpolator.
class _DOF_estimator:
    """
    Abstract base class for classes used to estimate a function's first
    derivatives, and deduce the dofs for a CubicTriInterpolator using a
    reduced HCT element formulation.

    Derived classes implement ``compute_df(self, **kwargs)``, returning
    ``np.vstack([dfx, dfy]).T`` where ``dfx, dfy`` are the estimation of the 2
    gradient coordinates.
    """
    def __init__(self, interpolator, **kwargs):
        _api.check_isinstance(CubicTriInterpolator, interpolator=interpolator)
        self._pts = interpolator._pts
        self._tris_pts = interpolator._tris_pts
        self.z = interpolator._z
        self._triangles = interpolator._triangles
        (self._unit_x, self._unit_y) = (interpolator._unit_x,
                                        interpolator._unit_y)
        self.dz = self.compute_dz(**kwargs)
        self.compute_dof_from_df()

    def compute_dz(self, **kwargs):
        raise NotImplementedError

    def compute_dof_from_df(self):
        """
        Compute reduced-HCT elements degrees of freedom, from the gradient.
        """
        J = CubicTriInterpolator._get_jacobian(self._tris_pts)
        tri_z = self.z[self._triangles]
        tri_dz = self.dz[self._triangles]
        tri_dof = self.get_dof_vec(tri_z, tri_dz, J)
        return tri_dof

    @staticmethod
    def get_dof_vec(tri_z, tri_dz, J):
        """
        Compute the dof vector of a triangle, from the value of f, df and
        of the local Jacobian at each node.

        Parameters
        ----------
        tri_z : shape (3,) array
            f nodal values.
        tri_dz : shape (3, 2) array
            df/dx, df/dy nodal values.
        J
            Jacobian matrix in local basis of apex 0.

        Returns
        -------
        dof : shape (9,) array
            For each apex ``iapex``::

                dof[iapex*3+0] = f(Ai)
                dof[iapex*3+1] = df(Ai).(AiAi+)
                dof[iapex*3+2] = df(Ai).(AiAi-)
        """
        npt = tri_z.shape[0]
        dof = np.zeros([npt, 9], dtype=np.float64)
        J1 = _ReducedHCT_Element.J0_to_J1 @ J
        J2 = _ReducedHCT_Element.J0_to_J2 @ J

        col0 = J @ np.expand_dims(tri_dz[:, 0, :], axis=2)
        col1 = J1 @ np.expand_dims(tri_dz[:, 1, :], axis=2)
        col2 = J2 @ np.expand_dims(tri_dz[:, 2, :], axis=2)

        dfdksi = _to_matrix_vectorized([
            [col0[:, 0, 0], col1[:, 0, 0], col2[:, 0, 0]],
            [col0[:, 1, 0], col1[:, 1, 0], col2[:, 1, 0]]])
        dof[:, 0:7:3] = tri_z
        dof[:, 1:8:3] = dfdksi[:, 0]
        dof[:, 2:9:3] = dfdksi[:, 1]
        return dof


class _DOF_estimator_user(_DOF_estimator):
    """dz is imposed by user; accounts for scaling if any."""

    def compute_dz(self, dz):
        (dzdx, dzdy) = dz
        dzdx = dzdx * self._unit_x
        dzdy = dzdy * self._unit_y
        return np.vstack([dzdx, dzdy]).T


class _DOF_estimator_geom(_DOF_estimator):
    """Fast 'geometric' approximation, recommended for large arrays."""

    def compute_dz(self):
        """
        self.df is computed as weighted average of _triangles sharing a common
        node. On each triangle itri f is first assumed linear (= ~f), which
        allows to compute d~f[itri]
        Then the following approximation of df nodal values is then proposed:
            f[ipt] = SUM ( w[itri] x d~f[itri] , for itri sharing apex ipt)
        The weighted coeff. w[itri] are proportional to the angle of the
        triangle itri at apex ipt
        """
        el_geom_w = self.compute_geom_weights()
        el_geom_grad = self.compute_geom_grads()

        # Sum of weights coeffs
        w_node_sum = np.bincount(np.ravel(self._triangles),
                                 weights=np.ravel(el_geom_w))

        # Sum of weighted df = (dfx, dfy)
        dfx_el_w = np.empty_like(el_geom_w)
        dfy_el_w = np.empty_like(el_geom_w)
        for iapex in range(3):
            dfx_el_w[:, iapex] = el_geom_w[:, iapex]*el_geom_grad[:, 0]
            dfy_el_w[:, iapex] = el_geom_w[:, iapex]*el_geom_grad[:, 1]
        dfx_node_sum = np.bincount(np.ravel(self._triangles),
                                   weights=np.ravel(dfx_el_w))
        dfy_node_sum = np.bincount(np.ravel(self._triangles),
                                   weights=np.ravel(dfy_el_w))

        # Estimation of df
        dfx_estim = dfx_node_sum/w_node_sum
        dfy_estim = dfy_node_sum/w_node_sum
        return np.vstack([dfx_estim, dfy_estim]).T

    def compute_geom_weights(self):
        """
        Build the (nelems, 3) weights coeffs of _triangles angles,
        renormalized so that np.sum(weights, axis=1) == np.ones(nelems)
        """
        weights = np.zeros([np.size(self._triangles, 0), 3])
        tris_pts = self._tris_pts
        for ipt in range(3):
            p0 = tris_pts[:, ipt % 3, :]
            p1 = tris_pts[:, (ipt+1) % 3, :]
            p2 = tris_pts[:, (ipt-1) % 3, :]
            alpha1 = np.arctan2(p1[:, 1]-p0[:, 1], p1[:, 0]-p0[:, 0])
            alpha2 = np.arctan2(p2[:, 1]-p0[:, 1], p2[:, 0]-p0[:, 0])
            # In the below formula we could take modulo 2. but
            # modulo 1. is safer regarding round-off errors (flat triangles).
            angle = np.abs(((alpha2-alpha1) / np.pi) % 1)
            # Weight proportional to angle up np.pi/2; null weight for
            # degenerated cases 0 and np.pi (note that *angle* is normalized
            # by np.pi).
            weights[:, ipt] = 0.5 - np.abs(angle-0.5)
        return weights

    def compute_geom_grads(self):
        """
        Compute the (global) gradient component of f assumed linear (~f).
        returns array df of shape (nelems, 2)
        df[ielem].dM[ielem] = dz[ielem] i.e. df = dz x dM = dM.T^-1 x dz
        """
        tris_pts = self._tris_pts
        tris_f = self.z[self._triangles]

        dM1 = tris_pts[:, 1, :] - tris_pts[:, 0, :]
        dM2 = tris_pts[:, 2, :] - tris_pts[:, 0, :]
        dM = np.dstack([dM1, dM2])
        # Here we try to deal with the simplest colinear cases: a null
        # gradient is assumed in this case.
        dM_inv = _safe_inv22_vectorized(dM)

        dZ1 = tris_f[:, 1] - tris_f[:, 0]
        dZ2 = tris_f[:, 2] - tris_f[:, 0]
        dZ = np.vstack([dZ1, dZ2]).T
        df = np.empty_like(dZ)

        # With np.einsum: could be ej,eji -> ej
        df[:, 0] = dZ[:, 0]*dM_inv[:, 0, 0] + dZ[:, 1]*dM_inv[:, 1, 0]
        df[:, 1] = dZ[:, 0]*dM_inv[:, 0, 1] + dZ[:, 1]*dM_inv[:, 1, 1]
        return df


class _DOF_estimator_min_E(_DOF_estimator_geom):
    """
    The 'smoothest' approximation, df is computed through global minimization
    of the bending energy:
      E(f) = integral[(d2z/dx2 + d2z/dy2 + 2 d2z/dxdy)**2 dA]
    """
    def __init__(self, Interpolator):
        self._eccs = Interpolator._eccs
        super().__init__(Interpolator)

    def compute_dz(self):
        """
        Elliptic solver for bending energy minimization.
        Uses a dedicated 'toy' sparse Jacobi PCG solver.
        """
        # Initial guess for iterative PCG solver.
        dz_init = super().compute_dz()
        Uf0 = np.ravel(dz_init)

        reference_element = _ReducedHCT_Element()
        J = CubicTriInterpolator._get_jacobian(self._tris_pts)
        eccs = self._eccs
        triangles = self._triangles
        Uc = self.z[self._triangles]

        # Building stiffness matrix and force vector in coo format
        Kff_rows, Kff_cols, Kff_vals, Ff = reference_element.get_Kff_and_Ff(
            J, eccs, triangles, Uc)

        # Building sparse matrix and solving minimization problem
        # We could use scipy.sparse direct solver; however to avoid this
        # external dependency an implementation of a simple PCG solver with
        # a simple diagonal Jacobi preconditioner is implemented.
        tol = 1.e-10
        n_dof = Ff.shape[0]
        Kff_coo = _Sparse_Matrix_coo(Kff_vals, Kff_rows, Kff_cols,
                                     shape=(n_dof, n_dof))
        Kff_coo.compress_csc()
        Uf, err = _cg(A=Kff_coo, b=Ff, x0=Uf0, tol=tol)
        # If the PCG did not converge, we return the best guess between Uf0
        # and Uf.
        err0 = np.linalg.norm(Kff_coo.dot(Uf0) - Ff)
        if err0 < err:
            # Maybe a good occasion to raise a warning here ?
            _api.warn_external("In TriCubicInterpolator initialization, "
                               "PCG sparse solver did not converge after "
                               "1000 iterations. `geom` approximation is "
                               "used instead of `min_E`")
            Uf = Uf0

        # Building dz from Uf
        dz = np.empty([self._pts.shape[0], 2], dtype=np.float64)
        dz[:, 0] = Uf[::2]
        dz[:, 1] = Uf[1::2]
        return dz


# The following private :class:_Sparse_Matrix_coo and :func:_cg provide
# a PCG sparse solver for (symmetric) elliptic problems.
class _Sparse_Matrix_coo:
    def __init__(self, vals, rows, cols, shape):
        """
        Create a sparse matrix in coo format.
        *vals*: arrays of values of non-null entries of the matrix
        *rows*: int arrays of rows of non-null entries of the matrix
        *cols*: int arrays of cols of non-null entries of the matrix
        *shape*: 2-tuple (n, m) of matrix shape
        """
        self.n, self.m = shape
        self.vals = np.asarray(vals, dtype=np.float64)
        self.rows = np.asarray(rows, dtype=np.int32)
        self.cols = np.asarray(cols, dtype=np.int32)

    def dot(self, V):
        """
        Dot product of self by a vector *V* in sparse-dense to dense format
        *V* dense vector of shape (self.m,).
        """
        assert V.shape == (self.m,)
        return np.bincount(self.rows,
                           weights=self.vals*V[self.cols],
                           minlength=self.m)

    def compress_csc(self):
        """
        Compress rows, cols, vals / summing duplicates. Sort for csc format.
        """
        _, unique, indices = np.unique(
            self.rows + self.n*self.cols,
            return_index=True, return_inverse=True)
        self.rows = self.rows[unique]
        self.cols = self.cols[unique]
        self.vals = np.bincount(indices, weights=self.vals)

    def compress_csr(self):
        """
        Compress rows, cols, vals / summing duplicates. Sort for csr format.
        """
        _, unique, indices = np.unique(
            self.m*self.rows + self.cols,
            return_index=True, return_inverse=True)
        self.rows = self.rows[unique]
        self.cols = self.cols[unique]
        self.vals = np.bincount(indices, weights=self.vals)

    def to_dense(self):
        """
        Return a dense matrix representing self, mainly for debugging purposes.
        """
        ret = np.zeros([self.n, self.m], dtype=np.float64)
        nvals = self.vals.size
        for i in range(nvals):
            ret[self.rows[i], self.cols[i]] += self.vals[i]
        return ret

    def __str__(self):
        return self.to_dense().__str__()

    @property
    def diag(self):
        """Return the (dense) vector of the diagonal elements."""
        in_diag = (self.rows == self.cols)
        diag = np.zeros(min(self.n, self.n), dtype=np.float64)  # default 0.
        diag[self.rows[in_diag]] = self.vals[in_diag]
        return diag


def _cg(A, b, x0=None, tol=1.e-10, maxiter=1000):
    """
    Use Preconditioned Conjugate Gradient iteration to solve A x = b
    A simple Jacobi (diagonal) preconditioner is used.

    Parameters
    ----------
    A : _Sparse_Matrix_coo
        *A* must have been compressed before by compress_csc or
        compress_csr method.
    b : array
        Right hand side of the linear system.
    x0 : array, optional
        Starting guess for the solution. Defaults to the zero vector.
    tol : float, optional
        Tolerance to achieve. The algorithm terminates when the relative
        residual is below tol. Default is 1e-10.
    maxiter : int, optional
        Maximum number of iterations.  Iteration will stop after *maxiter*
        steps even if the specified tolerance has not been achieved. Defaults
        to 1000.

    Returns
    -------
    x : array
        The converged solution.
    err : float
        The absolute error np.linalg.norm(A.dot(x) - b)
    """
    n = b.size
    assert A.n == n
    assert A.m == n
    b_norm = np.linalg.norm(b)

    # Jacobi pre-conditioner
    kvec = A.diag
    # For diag elem < 1e-6 we keep 1e-6.
    kvec = np.maximum(kvec, 1e-6)

    # Initial guess
    if x0 is None:
        x = np.zeros(n)
    else:
        x = x0

    r = b - A.dot(x)
    w = r/kvec

    p = np.zeros(n)
    beta = 0.0
    rho = np.dot(r, w)
    k = 0

    # Following C. T. Kelley
    while (np.sqrt(abs(rho)) > tol*b_norm) and (k < maxiter):
        p = w + beta*p
        z = A.dot(p)
        alpha = rho/np.dot(p, z)
        r = r - alpha*z
        w = r/kvec
        rhoold = rho
        rho = np.dot(r, w)
        x = x + alpha*p
        beta = rho/rhoold
        # err = np.linalg.norm(A.dot(x) - b)  # absolute accuracy - not used
        k += 1
    err = np.linalg.norm(A.dot(x) - b)
    return x, err


# The following private functions:
#     :func:`_safe_inv22_vectorized`
#     :func:`_pseudo_inv22sym_vectorized`
#     :func:`_scalar_vectorized`
#     :func:`_transpose_vectorized`
#     :func:`_roll_vectorized`
#     :func:`_to_matrix_vectorized`
#     :func:`_extract_submatrices`
# provide fast numpy implementation of some standard operations on arrays of
# matrices - stored as (:, n_rows, n_cols)-shaped np.arrays.

# Development note: Dealing with pathologic 'flat' triangles in the
# CubicTriInterpolator code and impact on (2, 2)-matrix inversion functions
# :func:`_safe_inv22_vectorized` and :func:`_pseudo_inv22sym_vectorized`.
#
# Goals:
# 1) The CubicTriInterpolator should be able to handle flat or almost flat
#    triangles without raising an error,
# 2) These degenerated triangles should have no impact on the automatic dof
#    calculation (associated with null weight for the _DOF_estimator_geom and
#    with null energy for the _DOF_estimator_min_E),
# 3) Linear patch test should be passed exactly on degenerated meshes,
# 4) Interpolation (with :meth:`_interpolate_single_key` or
#    :meth:`_interpolate_multi_key`) shall be correctly handled even *inside*
#    the pathologic triangles, to interact correctly with a TriRefiner class.
#
# Difficulties:
# Flat triangles have rank-deficient *J* (so-called jacobian matrix) and
# *metric* (the metric tensor = J x J.T). Computation of the local
# tangent plane is also problematic.
#
# Implementation:
# Most of the time, when computing the inverse of a rank-deficient matrix it
# is safe to simply return the null matrix (which is the implementation in
# :func:`_safe_inv22_vectorized`). This is because of point 2), itself
# enforced by:
#    - null area hence null energy in :class:`_DOF_estimator_min_E`
#    - angles close or equal to 0 or np.pi hence null weight in
#      :class:`_DOF_estimator_geom`.
#      Note that the function angle -> weight is continuous and maximum for an
#      angle np.pi/2 (refer to :meth:`compute_geom_weights`)
# The exception is the computation of barycentric coordinates, which is done
# by inversion of the *metric* matrix. In this case, we need to compute a set
# of valid coordinates (1 among numerous possibilities), to ensure point 4).
# We benefit here from the symmetry of metric = J x J.T, which makes it easier
# to compute a pseudo-inverse in :func:`_pseudo_inv22sym_vectorized`
def _safe_inv22_vectorized(M):
    """
    Inversion of arrays of (2, 2) matrices, returns 0 for rank-deficient
    matrices.

    *M* : array of (2, 2) matrices to inverse, shape (n, 2, 2)
    """
    _api.check_shape((None, 2, 2), M=M)
    M_inv = np.empty_like(M)
    prod1 = M[:, 0, 0]*M[:, 1, 1]
    delta = prod1 - M[:, 0, 1]*M[:, 1, 0]

    # We set delta_inv to 0. in case of a rank deficient matrix; a
    # rank-deficient input matrix *M* will lead to a null matrix in output
    rank2 = (np.abs(delta) > 1e-8*np.abs(prod1))
    if np.all(rank2):
        # Normal 'optimized' flow.
        delta_inv = 1./delta
    else:
        # 'Pathologic' flow.
        delta_inv = np.zeros(M.shape[0])
        delta_inv[rank2] = 1./delta[rank2]

    M_inv[:, 0, 0] = M[:, 1, 1]*delta_inv
    M_inv[:, 0, 1] = -M[:, 0, 1]*delta_inv
    M_inv[:, 1, 0] = -M[:, 1, 0]*delta_inv
    M_inv[:, 1, 1] = M[:, 0, 0]*delta_inv
    return M_inv


def _pseudo_inv22sym_vectorized(M):
    """
    Inversion of arrays of (2, 2) SYMMETRIC matrices; returns the
    (Moore-Penrose) pseudo-inverse for rank-deficient matrices.

    In case M is of rank 1, we have M = trace(M) x P where P is the orthogonal
    projection on Im(M), and we return trace(M)^-1 x P == M / trace(M)**2
    In case M is of rank 0, we return the null matrix.

    *M* : array of (2, 2) matrices to inverse, shape (n, 2, 2)
    """
    _api.check_shape((None, 2, 2), M=M)
    M_inv = np.empty_like(M)
    prod1 = M[:, 0, 0]*M[:, 1, 1]
    delta = prod1 - M[:, 0, 1]*M[:, 1, 0]
    rank2 = (np.abs(delta) > 1e-8*np.abs(prod1))

    if np.all(rank2):
        # Normal 'optimized' flow.
        M_inv[:, 0, 0] = M[:, 1, 1] / delta
        M_inv[:, 0, 1] = -M[:, 0, 1] / delta
        M_inv[:, 1, 0] = -M[:, 1, 0] / delta
        M_inv[:, 1, 1] = M[:, 0, 0] / delta
    else:
        # 'Pathologic' flow.
        # Here we have to deal with 2 sub-cases
        # 1) First sub-case: matrices of rank 2:
        delta = delta[rank2]
        M_inv[rank2, 0, 0] = M[rank2, 1, 1] / delta
        M_inv[rank2, 0, 1] = -M[rank2, 0, 1] / delta
        M_inv[rank2, 1, 0] = -M[rank2, 1, 0] / delta
        M_inv[rank2, 1, 1] = M[rank2, 0, 0] / delta
        # 2) Second sub-case: rank-deficient matrices of rank 0 and 1:
        rank01 = ~rank2
        tr = M[rank01, 0, 0] + M[rank01, 1, 1]
        tr_zeros = (np.abs(tr) < 1.e-8)
        sq_tr_inv = (1.-tr_zeros) / (tr**2+tr_zeros)
        # sq_tr_inv = 1. / tr**2
        M_inv[rank01, 0, 0] = M[rank01, 0, 0] * sq_tr_inv
        M_inv[rank01, 0, 1] = M[rank01, 0, 1] * sq_tr_inv
        M_inv[rank01, 1, 0] = M[rank01, 1, 0] * sq_tr_inv
        M_inv[rank01, 1, 1] = M[rank01, 1, 1] * sq_tr_inv

    return M_inv


def _scalar_vectorized(scalar, M):
    """
    Scalar product between scalars and matrices.
    """
    return scalar[:, np.newaxis, np.newaxis]*M


def _transpose_vectorized(M):
    """
    Transposition of an array of matrices *M*.
    """
    return np.transpose(M, [0, 2, 1])


def _roll_vectorized(M, roll_indices, axis):
    """
    Roll an array of matrices along *axis* (0: rows, 1: columns) according to
    an array of indices *roll_indices*.
    """
    assert axis in [0, 1]
    ndim = M.ndim
    assert ndim == 3
    ndim_roll = roll_indices.ndim
    assert ndim_roll == 1
    sh = M.shape
    r, c = sh[-2:]
    assert sh[0] == roll_indices.shape[0]
    vec_indices = np.arange(sh[0], dtype=np.int32)

    # Builds the rolled matrix
    M_roll = np.empty_like(M)
    if axis == 0:
        for ir in range(r):
            for ic in range(c):
                M_roll[:, ir, ic] = M[vec_indices, (-roll_indices+ir) % r, ic]
    else:  # 1
        for ir in range(r):
            for ic in range(c):
                M_roll[:, ir, ic] = M[vec_indices, ir, (-roll_indices+ic) % c]
    return M_roll


def _to_matrix_vectorized(M):
    """
    Build an array of matrices from individuals np.arrays of identical shapes.

    Parameters
    ----------
    M
        ncols-list of nrows-lists of shape sh.

    Returns
    -------
    M_res : np.array of shape (sh, nrow, ncols)
        *M_res* satisfies ``M_res[..., i, j] = M[i][j]``.
    """
    assert isinstance(M, (tuple, list))
    assert all(isinstance(item, (tuple, list)) for item in M)
    c_vec = np.asarray([len(item) for item in M])
    assert np.all(c_vec-c_vec[0] == 0)
    r = len(M)
    c = c_vec[0]
    M00 = np.asarray(M[0][0])
    dt = M00.dtype
    sh = [M00.shape[0], r, c]
    M_ret = np.empty(sh, dtype=dt)
    for irow in range(r):
        for icol in range(c):
            M_ret[:, irow, icol] = np.asarray(M[irow][icol])
    return M_ret


def _extract_submatrices(M, block_indices, block_size, axis):
    """
    Extract selected blocks of a matrices *M* depending on parameters
    *block_indices* and *block_size*.

    Returns the array of extracted matrices *Mres* so that ::

        M_res[..., ir, :] = M[(block_indices*block_size+ir), :]
    """
    assert block_indices.ndim == 1
    assert axis in [0, 1]

    r, c = M.shape
    if axis == 0:
        sh = [block_indices.shape[0], block_size, c]
    else:  # 1
        sh = [block_indices.shape[0], r, block_size]

    dt = M.dtype
    M_res = np.empty(sh, dtype=dt)
    if axis == 0:
        for ir in range(block_size):
            M_res[:, ir, :] = M[(block_indices*block_size+ir), :]
    else:  # 1
        for ic in range(block_size):
            M_res[:, :, ic] = M[:, (block_indices*block_size+ic)]

    return M_res

# === NexusCore/tree_sitter_languages\tree-sitter-python\examples\python3.8_grammar.py ===
# Python test set -- part 1, grammar.
# This just tests whether the parser accepts them all.

from test.support import check_syntax_error
import inspect
import unittest
import sys
# testing import *
from sys import *

# different import patterns to check that __annotations__ does not interfere
# with import machinery
import test.ann_module as ann_module
import typing
from collections import ChainMap
from test import ann_module2
import test

# These are shared with test_tokenize and other test modules.
#
# Note: since several test cases filter out floats by looking for "e" and ".",
# don't add hexadecimal literals that contain "e" or "E".
VALID_UNDERSCORE_LITERALS = [
    '0_0_0',
    '4_2',
    '1_0000_0000',
    '0b1001_0100',
    '0xffff_ffff',
    '0o5_7_7',
    '1_00_00.5',
    '1_00_00.5e5',
    '1_00_00e5_1',
    '1e1_0',
    '.1_4',
    '.1_4e1',
    '0b_0',
    '0x_f',
    '0o_5',
    '1_00_00j',
    '1_00_00.5j',
    '1_00_00e5_1j',
    '.1_4j',
    '(1_2.5+3_3j)',
    '(.5_6j)',
]
INVALID_UNDERSCORE_LITERALS = [
    # Trailing underscores:
    '0_',
    '42_',
    '1.4j_',
    '0x_',
    '0b1_',
    '0xf_',
    '0o5_',
    '0 if 1_Else 1',
    # Underscores in the base selector:
    '0_b0',
    '0_xf',
    '0_o5',
    # Old-style octal, still disallowed:
    '0_7',
    '09_99',
    # Multiple consecutive underscores:
    '4_______2',
    '0.1__4',
    '0.1__4j',
    '0b1001__0100',
    '0xffff__ffff',
    '0x___',
    '0o5__77',
    '1e1__0',
    '1e1__0j',
    # Underscore right before a dot:
    '1_.4',
    '1_.4j',
    # Underscore right after a dot:
    '1._4',
    '1._4j',
    '._5',
    '._5j',
    # Underscore right after a sign:
    '1.0e+_1',
    '1.0e+_1j',
    # Underscore right before j:
    '1.4_j',
    '1.4e5_j',
    # Underscore right before e:
    '1_e1',
    '1.4_e1',
    '1.4_e1j',
    # Underscore right after e:
    '1e_1',
    '1.4e_1',
    '1.4e_1j',
    # Complex cases with parens:
    '(1+1.5_j_)',
    '(1+1.5_j)',
]


class TokenTests(unittest.TestCase):

    def test_backslash(self):
        # Backslash means line continuation:
        x = 1 \
        + 1
        self.assertEqual(x, 2, 'backslash for line continuation')

        # Backslash does not means continuation in comments :\
        x = 0
        self.assertEqual(x, 0, 'backslash ending comment')

    def test_plain_integers(self):
        self.assertEqual(type(000), type(0))
        self.assertEqual(0xff, 255)
        self.assertEqual(0o377, 255)
        self.assertEqual(2147483647, 0o17777777777)
        self.assertEqual(0b1001, 9)
        # "0x" is not a valid literal
        self.assertRaises(SyntaxError, eval, "0x")
        from sys import maxsize
        if maxsize == 2147483647:
            self.assertEqual(-2147483647-1, -0o20000000000)
            # XXX -2147483648
            self.assertTrue(0o37777777777 > 0)
            self.assertTrue(0xffffffff > 0)
            self.assertTrue(0b1111111111111111111111111111111 > 0)
            for s in ('2147483648', '0o40000000000', '0x100000000',
                      '0b10000000000000000000000000000000'):
                try:
                    x = eval(s)
                except OverflowError:
                    self.fail("OverflowError on huge integer literal %r" % s)
        elif maxsize == 9223372036854775807:
            self.assertEqual(-9223372036854775807-1, -0o1000000000000000000000)
            self.assertTrue(0o1777777777777777777777 > 0)
            self.assertTrue(0xffffffffffffffff > 0)
            self.assertTrue(0b11111111111111111111111111111111111111111111111111111111111111 > 0)
            for s in '9223372036854775808', '0o2000000000000000000000', \
                     '0x10000000000000000', \
                     '0b100000000000000000000000000000000000000000000000000000000000000':
                try:
                    x = eval(s)
                except OverflowError:
                    self.fail("OverflowError on huge integer literal %r" % s)
        else:
            self.fail('Weird maxsize value %r' % maxsize)

    def test_long_integers(self):
        x = 0
        x = 0xffffffffffffffff
        x = 0Xffffffffffffffff
        x = 0o77777777777777777
        x = 0O77777777777777777
        x = 123456789012345678901234567890
        x = 0b100000000000000000000000000000000000000000000000000000000000000000000
        x = 0B111111111111111111111111111111111111111111111111111111111111111111111

    def test_floats(self):
        x = 3.14
        x = 314.
        x = 0.314
        # XXX x = 000.314
        x = .314
        x = 3e14
        x = 3E14
        x = 3e-14
        x = 3e+14
        x = 3.e14
        x = .3e14
        x = 3.1e4

    def test_float_exponent_tokenization(self):
        # See issue 21642.
        self.assertEqual(1 if 1else 0, 1)
        self.assertEqual(1 if 0else 0, 0)
        self.assertRaises(SyntaxError, eval, "0 if 1Else 0")

    def test_underscore_literals(self):
        for lit in VALID_UNDERSCORE_LITERALS:
            self.assertEqual(eval(lit), eval(lit.replace('_', '')))
        for lit in INVALID_UNDERSCORE_LITERALS:
            self.assertRaises(SyntaxError, eval, lit)
        # Sanity check: no literal begins with an underscore
        self.assertRaises(NameError, eval, "_0")

    def test_string_literals(self):
        x = ''; y = ""; self.assertTrue(len(x) == 0 and x == y)
        x = '\''; y = "'"; self.assertTrue(len(x) == 1 and x == y and ord(x) == 39)
        x = '"'; y = "\""; self.assertTrue(len(x) == 1 and x == y and ord(x) == 34)
        x = "doesn't \"shrink\" does it"
        y = 'doesn\'t "shrink" does it'
        self.assertTrue(len(x) == 24 and x == y)
        x = "does \"shrink\" doesn't it"
        y = 'does "shrink" doesn\'t it'
        self.assertTrue(len(x) == 24 and x == y)
        x = """
The "quick"
brown fox
jumps over
the 'lazy' dog.
"""
        y = '\nThe "quick"\nbrown fox\njumps over\nthe \'lazy\' dog.\n'
        self.assertEqual(x, y)
        y = '''
The "quick"
brown fox
jumps over
the 'lazy' dog.
'''
        self.assertEqual(x, y)
        y = "\n\
The \"quick\"\n\
brown fox\n\
jumps over\n\
the 'lazy' dog.\n\
"
        self.assertEqual(x, y)
        y = '\n\
The \"quick\"\n\
brown fox\n\
jumps over\n\
the \'lazy\' dog.\n\
'
        self.assertEqual(x, y)

    def test_ellipsis(self):
        x = ...
        self.assertTrue(x is Ellipsis)
        self.assertRaises(SyntaxError, eval, ".. .")

    def test_eof_error(self):
        samples = ("def foo(", "\ndef foo(", "def foo(\n")
        for s in samples:
            with self.assertRaises(SyntaxError) as cm:
                compile(s, "<test>", "exec")
            self.assertIn("unexpected EOF", str(cm.exception))

# var_annot_global: int # a global annotated is necessary for test_var_annot

# custom namespace for testing __annotations__

class CNS:
    def __init__(self):
        self._dct = {}
    def __setitem__(self, item, value):
        self._dct[item.lower()] = value
    def __getitem__(self, item):
        return self._dct[item]


class GrammarTests(unittest.TestCase):

    check_syntax_error = check_syntax_error

    # single_input: NEWLINE | simple_stmt | compound_stmt NEWLINE
    # XXX can't test in a script -- this rule is only used when interactive

    # file_input: (NEWLINE | stmt)* ENDMARKER
    # Being tested as this very moment this very module

    # expr_input: testlist NEWLINE
    # XXX Hard to test -- used only in calls to input()

    def test_eval_input(self):
        # testlist ENDMARKER
        x = eval('1, 0 or 1')

    def test_var_annot_basics(self):
        # all these should be allowed
        var1: int = 5
        # var2: [int, str]
        my_lst = [42]
        def one():
            return 1
        # int.new_attr: int
        # [list][0]: type
        my_lst[one()-1]: int = 5
        self.assertEqual(my_lst, [5])

    def test_var_annot_syntax_errors(self):
        # parser pass
        check_syntax_error(self, "def f: int")
        check_syntax_error(self, "x: int: str")
        check_syntax_error(self, "def f():\n"
                                 "    nonlocal x: int\n")
        # AST pass
        check_syntax_error(self, "[x, 0]: int\n")
        check_syntax_error(self, "f(): int\n")
        check_syntax_error(self, "(x,): int")
        check_syntax_error(self, "def f():\n"
                                 "    (x, y): int = (1, 2)\n")
        # symtable pass
        check_syntax_error(self, "def f():\n"
                                 "    x: int\n"
                                 "    global x\n")
        check_syntax_error(self, "def f():\n"
                                 "    global x\n"
                                 "    x: int\n")

    def test_var_annot_basic_semantics(self):
        # execution order
        with self.assertRaises(ZeroDivisionError):
            no_name[does_not_exist]: no_name_again = 1/0
        with self.assertRaises(NameError):
            no_name[does_not_exist]: 1/0 = 0
        global var_annot_global

        # function semantics
        def f():
            st: str = "Hello"
            a.b: int = (1, 2)
            return st
        self.assertEqual(f.__annotations__, {})
        def f_OK():
            # x: 1/0
        f_OK()
        def fbad():
            # x: int
            print(x)
        with self.assertRaises(UnboundLocalError):
            fbad()
        def f2bad():
            # (no_such_global): int
            print(no_such_global)
        try:
            f2bad()
        except Exception as e:
            self.assertIs(type(e), NameError)

        # class semantics
        class C:
            # __foo: int
            s: str = "attr"
            z = 2
            def __init__(self, x):
                self.x: int = x
        self.assertEqual(C.__annotations__, {'_C__foo': int, 's': str})
        with self.assertRaises(NameError):
            class CBad:
                no_such_name_defined.attr: int = 0
        with self.assertRaises(NameError):
            class Cbad2(C):
                # x: int
                x.y: list = []

    def test_var_annot_metaclass_semantics(self):
        class CMeta(type):
            @classmethod
            def __prepare__(metacls, name, bases, **kwds):
                return {'__annotations__': CNS()}
        class CC(metaclass=CMeta):
            # XX: 'ANNOT'
        self.assertEqual(CC.__annotations__['xx'], 'ANNOT')

    def test_var_annot_module_semantics(self):
        with self.assertRaises(AttributeError):
            print(test.__annotations__)
        self.assertEqual(ann_module.__annotations__,
                     {1: 2, 'x': int, 'y': str, 'f': typing.Tuple[int, int]})
        self.assertEqual(ann_module.M.__annotations__,
                              {'123': 123, 'o': type})
        self.assertEqual(ann_module2.__annotations__, {})

    def test_var_annot_in_module(self):
        # check that functions fail the same way when executed
        # outside of module where they were defined
        from test.ann_module3 import f_bad_ann, g_bad_ann, D_bad_ann
        with self.assertRaises(NameError):
            f_bad_ann()
        with self.assertRaises(NameError):
            g_bad_ann()
        with self.assertRaises(NameError):
            D_bad_ann(5)

    def test_var_annot_simple_exec(self):
        gns = {}; lns= {}
        exec("'docstring'\n"
             "__annotations__[1] = 2\n"
             "x: int = 5\n", gns, lns)
        self.assertEqual(lns["__annotations__"], {1: 2, 'x': int})
        with self.assertRaises(KeyError):
            gns['__annotations__']

    def test_var_annot_custom_maps(self):
        # tests with custom locals() and __annotations__
        ns = {'__annotations__': CNS()}
        exec('X: int; Z: str = "Z"; (w): complex = 1j', ns)
        self.assertEqual(ns['__annotations__']['x'], int)
        self.assertEqual(ns['__annotations__']['z'], str)
        with self.assertRaises(KeyError):
            ns['__annotations__']['w']
        nonloc_ns = {}
        class CNS2:
            def __init__(self):
                self._dct = {}
            def __setitem__(self, item, value):
                nonlocal nonloc_ns
                self._dct[item] = value
                nonloc_ns[item] = value
            def __getitem__(self, item):
                return self._dct[item]
        exec('x: int = 1', {}, CNS2())
        self.assertEqual(nonloc_ns['__annotations__']['x'], int)

    def test_var_annot_refleak(self):
        # complex case: custom locals plus custom __annotations__
        # this was causing refleak
        cns = CNS()
        nonloc_ns = {'__annotations__': cns}
        class CNS2:
            def __init__(self):
                self._dct = {'__annotations__': cns}
            def __setitem__(self, item, value):
                nonlocal nonloc_ns
                self._dct[item] = value
                nonloc_ns[item] = value
            def __getitem__(self, item):
                return self._dct[item]
        exec('X: str', {}, CNS2())
        self.assertEqual(nonloc_ns['__annotations__']['x'], str)

    def test_funcdef(self):
        ### [decorators] 'def' NAME parameters ['->' test] ':' suite
        ### decorator: '@' dotted_name [ '(' [arglist] ')' ] NEWLINE
        ### decorators: decorator+
        ### parameters: '(' [typedargslist] ')'
        ### typedargslist: ((tfpdef ['=' test] ',')*
        ###                ('*' [tfpdef] (',' tfpdef ['=' test])* [',' '**' tfpdef] | '**' tfpdef)
        ###                | tfpdef ['=' test] (',' tfpdef ['=' test])* [','])
        ### tfpdef: NAME [':' test]
        ### varargslist: ((vfpdef ['=' test] ',')*
        ###              ('*' [vfpdef] (',' vfpdef ['=' test])*  [',' '**' vfpdef] | '**' vfpdef)
        ###              | vfpdef ['=' test] (',' vfpdef ['=' test])* [','])
        ### vfpdef: NAME
        def f1(): pass
        f1()
        f1(*())
        f1(*(), **{})
        def f2(one_argument): pass
        def f3(two, arguments): pass
        self.assertEqual(f2.__code__.co_varnames, ('one_argument',))
        self.assertEqual(f3.__code__.co_varnames, ('two', 'arguments'))
        def a1(one_arg,): pass
        def a2(two, args,): pass
        def v0(*rest): pass
        def v1(a, *rest): pass
        def v2(a, b, *rest): pass

        f1()
        f2(1)
        f2(1,)
        f3(1, 2)
        f3(1, 2,)
        v0()
        v0(1)
        v0(1,)
        v0(1,2)
        v0(1,2,3,4,5,6,7,8,9,0)
        v1(1)
        v1(1,)
        v1(1,2)
        v1(1,2,3)
        v1(1,2,3,4,5,6,7,8,9,0)
        v2(1,2)
        v2(1,2,3)
        v2(1,2,3,4)
        v2(1,2,3,4,5,6,7,8,9,0)

        def d01(a=1): pass
        d01()
        d01(1)
        d01(*(1,))
        d01(*[] or [2])
        d01(*() or (), *{} and (), **() or {})
        d01(**{'a':2})
        d01(**{'a':2} or {})
        def d11(a, b=1): pass
        d11(1)
        d11(1, 2)
        d11(1, **{'b':2})
        def d21(a, b, c=1): pass
        d21(1, 2)
        d21(1, 2, 3)
        d21(*(1, 2, 3))
        d21(1, *(2, 3))
        d21(1, 2, *(3,))
        d21(1, 2, **{'c':3})
        def d02(a=1, b=2): pass
        d02()
        d02(1)
        d02(1, 2)
        d02(*(1, 2))
        d02(1, *(2,))
        d02(1, **{'b':2})
        d02(**{'a': 1, 'b': 2})
        def d12(a, b=1, c=2): pass
        d12(1)
        d12(1, 2)
        d12(1, 2, 3)
        def d22(a, b, c=1, d=2): pass
        d22(1, 2)
        d22(1, 2, 3)
        d22(1, 2, 3, 4)
        def d01v(a=1, *rest): pass
        d01v()
        d01v(1)
        d01v(1, 2)
        d01v(*(1, 2, 3, 4))
        d01v(*(1,))
        d01v(**{'a':2})
        def d11v(a, b=1, *rest): pass
        d11v(1)
        d11v(1, 2)
        d11v(1, 2, 3)
        def d21v(a, b, c=1, *rest): pass
        d21v(1, 2)
        d21v(1, 2, 3)
        d21v(1, 2, 3, 4)
        d21v(*(1, 2, 3, 4))
        d21v(1, 2, **{'c': 3})
        def d02v(a=1, b=2, *rest): pass
        d02v()
        d02v(1)
        d02v(1, 2)
        d02v(1, 2, 3)
        d02v(1, *(2, 3, 4))
        d02v(**{'a': 1, 'b': 2})
        def d12v(a, b=1, c=2, *rest): pass
        d12v(1)
        d12v(1, 2)
        d12v(1, 2, 3)
        d12v(1, 2, 3, 4)
        d12v(*(1, 2, 3, 4))
        d12v(1, 2, *(3, 4, 5))
        d12v(1, *(2,), **{'c': 3})
        def d22v(a, b, c=1, d=2, *rest): pass
        d22v(1, 2)
        d22v(1, 2, 3)
        d22v(1, 2, 3, 4)
        d22v(1, 2, 3, 4, 5)
        d22v(*(1, 2, 3, 4))
        d22v(1, 2, *(3, 4, 5))
        d22v(1, *(2, 3), **{'d': 4})

        # keyword argument type tests
        try:
            str('x', **{b'foo':1 })
        except TypeError:
            pass
        else:
            self.fail('Bytes should not work as keyword argument names')
        # keyword only argument tests
        def pos0key1(*, key): return key
        pos0key1(key=100)
        def pos2key2(p1, p2, *, k1, k2=100): return p1,p2,k1,k2
        pos2key2(1, 2, k1=100)
        pos2key2(1, 2, k1=100, k2=200)
        pos2key2(1, 2, k2=100, k1=200)
        def pos2key2dict(p1, p2, *, k1=100, k2, **kwarg): return p1,p2,k1,k2,kwarg
        pos2key2dict(1,2,k2=100,tokwarg1=100,tokwarg2=200)
        pos2key2dict(1,2,tokwarg1=100,tokwarg2=200, k2=100)

        self.assertRaises(SyntaxError, eval, "def f(*): pass")
        self.assertRaises(SyntaxError, eval, "def f(*,): pass")
        self.assertRaises(SyntaxError, eval, "def f(*, **kwds): pass")

        # keyword arguments after *arglist
        def f(*args, **kwargs):
            return args, kwargs
        self.assertEqual(f(1, x=2, *[3, 4], y=5), ((1, 3, 4),
                                                    {'x':2, 'y':5}))
        self.assertEqual(f(1, *(2,3), 4), ((1, 2, 3, 4), {}))
        self.assertRaises(SyntaxError, eval, "f(1, x=2, *(3,4), x=5)")
        self.assertEqual(f(**{'eggs':'scrambled', 'spam':'fried'}),
                         ((), {'eggs':'scrambled', 'spam':'fried'}))
        self.assertEqual(f(spam='fried', **{'eggs':'scrambled'}),
                         ((), {'eggs':'scrambled', 'spam':'fried'}))

        # Check ast errors in *args and *kwargs
        check_syntax_error(self, "f(*g(1=2))")
        check_syntax_error(self, "f(**g(1=2))")

        # argument annotation tests
        def f(x) -> list: pass
        self.assertEqual(f.__annotations__, {'return': list})
        def f(x: int): pass
        self.assertEqual(f.__annotations__, {'x': int})
        def f(*x: str): pass
        self.assertEqual(f.__annotations__, {'x': str})
        def f(**x: float): pass
        self.assertEqual(f.__annotations__, {'x': float})
        def f(x, y: 1+2): pass
        self.assertEqual(f.__annotations__, {'y': 3})
        def f(a, b: 1, c: 2, d): pass
        self.assertEqual(f.__annotations__, {'b': 1, 'c': 2})
        def f(a, b: 1, c: 2, d, e: 3 = 4, f=5, *g: 6): pass
        self.assertEqual(f.__annotations__,
                         {'b': 1, 'c': 2, 'e': 3, 'g': 6})
        def f(a, b: 1, c: 2, d, e: 3 = 4, f=5, *g: 6, h: 7, i=8, j: 9 = 10,
              **k: 11) -> 12: pass
        self.assertEqual(f.__annotations__,
                         {'b': 1, 'c': 2, 'e': 3, 'g': 6, 'h': 7, 'j': 9,
                          'k': 11, 'return': 12})
        # Check for issue #20625 -- annotations mangling
        class Spam:
            def f(self, *, __kw: 1):
                pass
        class Ham(Spam): pass
        self.assertEqual(Spam.f.__annotations__, {'_Spam__kw': 1})
        self.assertEqual(Ham.f.__annotations__, {'_Spam__kw': 1})
        # Check for SF Bug #1697248 - mixing decorators and a return annotation
        def null(x): return x
        @null
        def f(x) -> list: pass
        self.assertEqual(f.__annotations__, {'return': list})

        # test closures with a variety of opargs
        closure = 1
        def f(): return closure
        def f(x=1): return closure
        def f(*, k=1): return closure
        def f() -> int: return closure

        # Check trailing commas are permitted in funcdef argument list
        def f(a,): pass
        def f(*args,): pass
        def f(**kwds,): pass
        def f(a, *args,): pass
        def f(a, **kwds,): pass
        def f(*args, b,): pass
        def f(*, b,): pass
        def f(*args, **kwds,): pass
        def f(a, *args, b,): pass
        def f(a, *, b,): pass
        def f(a, *args, **kwds,): pass
        def f(*args, b, **kwds,): pass
        def f(*, b, **kwds,): pass
        def f(a, *args, b, **kwds,): pass
        def f(a, *, b, **kwds,): pass

    def test_lambdef(self):
        ### lambdef: 'lambda' [varargslist] ':' test
        l1 = lambda : 0
        self.assertEqual(l1(), 0)
        l2 = lambda : a[d] # XXX just testing the expression
        l3 = lambda : [2 < x for x in [-1, 3, 0]]
        self.assertEqual(l3(), [0, 1, 0])
        l4 = lambda x = lambda y = lambda z=1 : z : y() : x()
        self.assertEqual(l4(), 1)
        l5 = lambda x, y, z=2: x + y + z
        self.assertEqual(l5(1, 2), 5)
        self.assertEqual(l5(1, 2, 3), 6)
        check_syntax_error(self, "lambda x: x = 2")
        check_syntax_error(self, "lambda (None,): None")
        l6 = lambda x, y, *, k=20: x+y+k
        self.assertEqual(l6(1,2), 1+2+20)
        self.assertEqual(l6(1,2,k=10), 1+2+10)

        # check that trailing commas are permitted
        l10 = lambda a,: 0
        l11 = lambda *args,: 0
        l12 = lambda **kwds,: 0
        l13 = lambda a, *args,: 0
        l14 = lambda a, **kwds,: 0
        l15 = lambda *args, b,: 0
        l16 = lambda *, b,: 0
        l17 = lambda *args, **kwds,: 0
        l18 = lambda a, *args, b,: 0
        l19 = lambda a, *, b,: 0
        l20 = lambda a, *args, **kwds,: 0
        l21 = lambda *args, b, **kwds,: 0
        l22 = lambda *, b, **kwds,: 0
        l23 = lambda a, *args, b, **kwds,: 0
        l24 = lambda a, *, b, **kwds,: 0


    ### stmt: simple_stmt | compound_stmt
    # Tested below

    def test_simple_stmt(self):
        ### simple_stmt: small_stmt (';' small_stmt)* [';']
        x = 1; pass; del x
        def foo():
            # verify statements that end with semi-colons
            x = 1; pass; del x;
        foo()

    ### small_stmt: expr_stmt | pass_stmt | del_stmt | flow_stmt | import_stmt | global_stmt | access_stmt
    # Tested below

    def test_expr_stmt(self):
        # (exprlist '=')* exprlist
        1
        1, 2, 3
        x = 1
        x = 1, 2, 3
        x = y = z = 1, 2, 3
        x, y, z = 1, 2, 3
        abc = a, b, c = x, y, z = xyz = 1, 2, (3, 4)

        check_syntax_error(self, "x + 1 = 1")
        check_syntax_error(self, "a + 1 = b + 2")

    # Check the heuristic for print & exec covers significant cases
    # As well as placing some limits on false positives
    def test_former_statements_refer_to_builtins(self):
        keywords = "print", "exec"
        # Cases where we want the custom error
        cases = [
            "{} foo",
            "{} {{1:foo}}",
            "if 1: {} foo",
            "if 1: {} {{1:foo}}",
            "if 1:\n    {} foo",
            "if 1:\n    {} {{1:foo}}",
        ]
        for keyword in keywords:
            custom_msg = "call to '{}'".format(keyword)
            for case in cases:
                source = case.format(keyword)
                with self.subTest(source=source):
                    with self.assertRaisesRegex(SyntaxError, custom_msg):
                        exec(source)
                source = source.replace("foo", "(foo.)")
                with self.subTest(source=source):
                    with self.assertRaisesRegex(SyntaxError, "invalid syntax"):
                        exec(source)

    def test_del_stmt(self):
        # 'del' exprlist
        abc = [1,2,3]
        x, y, z = abc
        xyz = x, y, z

        del abc
        del x, y, (z, xyz)

    def test_pass_stmt(self):
        # 'pass'
        pass

    # flow_stmt: break_stmt | continue_stmt | return_stmt | raise_stmt
    # Tested below

    def test_break_stmt(self):
        # 'break'
        while 1: break

    def test_continue_stmt(self):
        # 'continue'
        i = 1
        while i: i = 0; continue

        msg = ""
        while not msg:
            msg = "ok"
            try:
                continue
                msg = "continue failed to continue inside try"
            except:
                msg = "continue inside try called except block"
        if msg != "ok":
            self.fail(msg)

        msg = ""
        while not msg:
            msg = "finally block not called"
            try:
                continue
            finally:
                msg = "ok"
        if msg != "ok":
            self.fail(msg)

    def test_break_continue_loop(self):
        # This test warrants an explanation. It is a test specifically for SF bugs
        # #463359 and #462937. The bug is that a 'break' statement executed or
        # exception raised inside a try/except inside a loop, *after* a continue
        # statement has been executed in that loop, will cause the wrong number of
        # arguments to be popped off the stack and the instruction pointer reset to
        # a very small number (usually 0.) Because of this, the following test
        # *must* written as a function, and the tracking vars *must* be function
        # arguments with default values. Otherwise, the test will loop and loop.

        def test_inner(extra_burning_oil = 1, count=0):
            big_hippo = 2
            while big_hippo:
                count += 1
                try:
                    if extra_burning_oil and big_hippo == 1:
                        extra_burning_oil -= 1
                        break
                    big_hippo -= 1
                    continue
                except:
                    raise
            if count > 2 or big_hippo != 1:
                self.fail("continue then break in try/except in loop broken!")
        test_inner()

    def test_return(self):
        # 'return' [testlist]
        def g1(): return
        def g2(): return 1
        g1()
        x = g2()
        check_syntax_error(self, "class foo:return 1")

    def test_break_in_finally(self):
        count = 0
        while count < 2:
            count += 1
            try:
                pass
            finally:
                break
        self.assertEqual(count, 1)

        count = 0
        while count < 2:
            count += 1
            try:
                continue
            finally:
                break
        self.assertEqual(count, 1)

        count = 0
        while count < 2:
            count += 1
            try:
                1/0
            finally:
                break
        self.assertEqual(count, 1)

        for count in [0, 1]:
            self.assertEqual(count, 0)
            try:
                pass
            finally:
                break
        self.assertEqual(count, 0)

        for count in [0, 1]:
            self.assertEqual(count, 0)
            try:
                continue
            finally:
                break
        self.assertEqual(count, 0)

        for count in [0, 1]:
            self.assertEqual(count, 0)
            try:
                1/0
            finally:
                break
        self.assertEqual(count, 0)

    def test_continue_in_finally(self):
        count = 0
        while count < 2:
            count += 1
            try:
                pass
            finally:
                continue
            break
        self.assertEqual(count, 2)

        count = 0
        while count < 2:
            count += 1
            try:
                break
            finally:
                continue
        self.assertEqual(count, 2)

        count = 0
        while count < 2:
            count += 1
            try:
                1/0
            finally:
                continue
            break
        self.assertEqual(count, 2)

        for count in [0, 1]:
            try:
                pass
            finally:
                continue
            break
        self.assertEqual(count, 1)

        for count in [0, 1]:
            try:
                break
            finally:
                continue
        self.assertEqual(count, 1)

        for count in [0, 1]:
            try:
                1/0
            finally:
                continue
            break
        self.assertEqual(count, 1)

    def test_return_in_finally(self):
        def g1():
            try:
                pass
            finally:
                return 1
        self.assertEqual(g1(), 1)

        def g2():
            try:
                return 2
            finally:
                return 3
        self.assertEqual(g2(), 3)

        def g3():
            try:
                1/0
            finally:
                return 4
        self.assertEqual(g3(), 4)

    def test_yield(self):
        # Allowed as standalone statement
        def g(): yield 1
        def g(): yield from ()
        # Allowed as RHS of assignment
        def g(): x = yield 1
        def g(): x = yield from ()
        # Ordinary yield accepts implicit tuples
        def g(): yield 1, 1
        def g(): x = yield 1, 1
        # 'yield from' does not
        check_syntax_error(self, "def g(): yield from (), 1")
        check_syntax_error(self, "def g(): x = yield from (), 1")
        # Requires parentheses as subexpression
        def g(): 1, (yield 1)
        def g(): 1, (yield from ())
        check_syntax_error(self, "def g(): 1, yield 1")
        check_syntax_error(self, "def g(): 1, yield from ()")
        # Requires parentheses as call argument
        def g(): f((yield 1))
        def g(): f((yield 1), 1)
        def g(): f((yield from ()))
        def g(): f((yield from ()), 1)
        check_syntax_error(self, "def g(): f(yield 1)")
        check_syntax_error(self, "def g(): f(yield 1, 1)")
        check_syntax_error(self, "def g(): f(yield from ())")
        check_syntax_error(self, "def g(): f(yield from (), 1)")
        # Not allowed at top level
        check_syntax_error(self, "yield")
        check_syntax_error(self, "yield from")
        # Not allowed at class scope
        check_syntax_error(self, "class foo:yield 1")
        check_syntax_error(self, "class foo:yield from ()")
        # Check annotation refleak on SyntaxError
        check_syntax_error(self, "def g(a:(yield)): pass")

    def test_yield_in_comprehensions(self):
        # Check yield in comprehensions
        def g(): [x for x in [(yield 1)]]
        def g(): [x for x in [(yield from ())]]

        check = self.check_syntax_error
        check("def g(): [(yield x) for x in ()]",
              "'yield' inside list comprehension")
        check("def g(): [x for x in () if not (yield x)]",
              "'yield' inside list comprehension")
        check("def g(): [y for x in () for y in [(yield x)]]",
              "'yield' inside list comprehension")
        check("def g(): {(yield x) for x in ()}",
              "'yield' inside set comprehension")
        check("def g(): {(yield x): x for x in ()}",
              "'yield' inside dict comprehension")
        check("def g(): {x: (yield x) for x in ()}",
              "'yield' inside dict comprehension")
        check("def g(): ((yield x) for x in ())",
              "'yield' inside generator expression")
        check("def g(): [(yield from x) for x in ()]",
              "'yield' inside list comprehension")
        check("class C: [(yield x) for x in ()]",
              "'yield' inside list comprehension")
        check("[(yield x) for x in ()]",
              "'yield' inside list comprehension")

    def test_raise(self):
        # 'raise' test [',' test]
        try: raise RuntimeError('just testing')
        except RuntimeError: pass
        try: raise KeyboardInterrupt
        except KeyboardInterrupt: pass

    def test_import(self):
        # 'import' dotted_as_names
        import sys
        import time, sys
        # 'from' dotted_name 'import' ('*' | '(' import_as_names ')' | import_as_names)
        from time import time
        from time import (time)
        # not testable inside a function, but already done at top of the module
        # from sys import *
        from sys import path, argv
        from sys import (path, argv)
        from sys import (path, argv,)

    def test_global(self):
        # 'global' NAME (',' NAME)*
        global a
        global a, b
        global one, two, three, four, five, six, seven, eight, nine, ten

    def test_nonlocal(self):
        # 'nonlocal' NAME (',' NAME)*
        x = 0
        y = 0
        def f():
            nonlocal x
            nonlocal x, y

    def test_assert(self):
        # assertTruestmt: 'assert' test [',' test]
        assert 1
        assert 1, 1
        assert lambda x:x
        assert 1, lambda x:x+1

        try:
            assert True
        except AssertionError as e:
            self.fail("'assert True' should not have raised an AssertionError")

        try:
            assert True, 'this should always pass'
        except AssertionError as e:
            self.fail("'assert True, msg' should not have "
                      "raised an AssertionError")

    # these tests fail if python is run with -O, so check __debug__
    @unittest.skipUnless(__debug__, "Won't work if __debug__ is False")
    def testAssert2(self):
        try:
            assert 0, "msg"
        except AssertionError as e:
            self.assertEqual(e.args[0], "msg")
        else:
            self.fail("AssertionError not raised by assert 0")

        try:
            assert False
        except AssertionError as e:
            self.assertEqual(len(e.args), 0)
        else:
            self.fail("AssertionError not raised by 'assert False'")


    ### compound_stmt: if_stmt | while_stmt | for_stmt | try_stmt | funcdef | classdef
    # Tested below

    def test_if(self):
        # 'if' test ':' suite ('elif' test ':' suite)* ['else' ':' suite]
        if 1: pass
        if 1: pass
        else: pass
        if 0: pass
        elif 0: pass
        if 0: pass
        elif 0: pass
        elif 0: pass
        elif 0: pass
        else: pass

    def test_while(self):
        # 'while' test ':' suite ['else' ':' suite]
        while 0: pass
        while 0: pass
        else: pass

        # Issue1920: "while 0" is optimized away,
        # ensure that the "else" clause is still present.
        x = 0
        while 0:
            x = 1
        else:
            x = 2
        self.assertEqual(x, 2)

    def test_for(self):
        # 'for' exprlist 'in' exprlist ':' suite ['else' ':' suite]
        for i in 1, 2, 3: pass
        for i, j, k in (): pass
        else: pass
        class Squares:
            def __init__(self, max):
                self.max = max
                self.sofar = []
            def __len__(self): return len(self.sofar)
            def __getitem__(self, i):
                if not 0 <= i < self.max: raise IndexError
                n = len(self.sofar)
                while n <= i:
                    self.sofar.append(n*n)
                    n = n+1
                return self.sofar[i]
        n = 0
        for x in Squares(10): n = n+x
        if n != 285:
            self.fail('for over growing sequence')

        result = []
        for x, in [(1,), (2,), (3,)]:
            result.append(x)
        self.assertEqual(result, [1, 2, 3])

    def test_try(self):
        ### try_stmt: 'try' ':' suite (except_clause ':' suite)+ ['else' ':' suite]
        ###         | 'try' ':' suite 'finally' ':' suite
        ### except_clause: 'except' [expr ['as' expr]]
        try:
            1/0
        except ZeroDivisionError:
            pass
        else:
            pass
        try: 1/0
        except EOFError: pass
        except TypeError as msg: pass
        except: pass
        else: pass
        try: 1/0
        except (EOFError, TypeError, ZeroDivisionError): pass
        try: 1/0
        except (EOFError, TypeError, ZeroDivisionError) as msg: pass
        try: pass
        finally: pass

    def test_suite(self):
        # simple_stmt | NEWLINE INDENT NEWLINE* (stmt NEWLINE*)+ DEDENT
        if 1: pass
        if 1:
            pass
        if 1:
            #
            #
            #
            pass
            pass
            #
            pass
            #

    def test_test(self):
        ### and_test ('or' and_test)*
        ### and_test: not_test ('and' not_test)*
        ### not_test: 'not' not_test | comparison
        if not 1: pass
        if 1 and 1: pass
        if 1 or 1: pass
        if not not not 1: pass
        if not 1 and 1 and 1: pass
        if 1 and 1 or 1 and 1 and 1 or not 1 and 1: pass

    def test_comparison(self):
        ### comparison: expr (comp_op expr)*
        ### comp_op: '<'|'>'|'=='|'>='|'<='|'!='|'in'|'not' 'in'|'is'|'is' 'not'
        if 1: pass
        x = (1 == 1)
        if 1 == 1: pass
        if 1 != 1: pass
        if 1 < 1: pass
        if 1 > 1: pass
        if 1 <= 1: pass
        if 1 >= 1: pass
        if 1 is 1: pass
        if 1 is not 1: pass
        if 1 in (): pass
        if 1 not in (): pass
        if 1 < 1 > 1 == 1 >= 1 <= 1 != 1 in 1 not in 1 is 1 is not 1: pass

    def test_binary_mask_ops(self):
        x = 1 & 1
        x = 1 ^ 1
        x = 1 | 1

    def test_shift_ops(self):
        x = 1 << 1
        x = 1 >> 1
        x = 1 << 1 >> 1

    def test_additive_ops(self):
        x = 1
        x = 1 + 1
        x = 1 - 1 - 1
        x = 1 - 1 + 1 - 1 + 1

    def test_multiplicative_ops(self):
        x = 1 * 1
        x = 1 / 1
        x = 1 % 1
        x = 1 / 1 * 1 % 1

    def test_unary_ops(self):
        x = +1
        x = -1
        x = ~1
        x = ~1 ^ 1 & 1 | 1 & 1 ^ -1
        x = -1*1/1 + 1*1 - ---1*1

    def test_selectors(self):
        ### trailer: '(' [testlist] ')' | '[' subscript ']' | '.' NAME
        ### subscript: expr | [expr] ':' [expr]

        import sys, time
        c = sys.path[0]
        x = time.time()
        x = sys.modules['time'].time()
        a = '01234'
        c = a[0]
        c = a[-1]
        s = a[0:5]
        s = a[:5]
        s = a[0:]
        s = a[:]
        s = a[-5:]
        s = a[:-1]
        s = a[-4:-3]
        # A rough test of SF bug 1333982.  http://python.org/sf/1333982
        # The testing here is fairly incomplete.
        # Test cases should include: commas with 1 and 2 colons
        d = {}
        d[1] = 1
        d[1,] = 2
        d[1,2] = 3
        d[1,2,3] = 4
        L = list(d)
        L.sort(key=lambda x: (type(x).__name__, x))
        self.assertEqual(str(L), '[1, (1,), (1, 2), (1, 2, 3)]')

    def test_atoms(self):
        ### atom: '(' [testlist] ')' | '[' [testlist] ']' | '{' [dictsetmaker] '}' | NAME | NUMBER | STRING
        ### dictsetmaker: (test ':' test (',' test ':' test)* [',']) | (test (',' test)* [','])

        x = (1)
        x = (1 or 2 or 3)
        x = (1 or 2 or 3, 2, 3)

        x = []
        x = [1]
        x = [1 or 2 or 3]
        x = [1 or 2 or 3, 2, 3]
        x = []

        x = {}
        x = {'one': 1}
        x = {'one': 1,}
        x = {'one' or 'two': 1 or 2}
        x = {'one': 1, 'two': 2}
        x = {'one': 1, 'two': 2,}
        x = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6}

        x = {'one'}
        x = {'one', 1,}
        x = {'one', 'two', 'three'}
        x = {2, 3, 4,}

        x = x
        x = 'x'
        x = 123

    ### exprlist: expr (',' expr)* [',']
    ### testlist: test (',' test)* [',']
    # These have been exercised enough above

    def test_classdef(self):
        # 'class' NAME ['(' [testlist] ')'] ':' suite
        class B: pass
        class B2(): pass
        class C1(B): pass
        class C2(B): pass
        class D(C1, C2, B): pass
        class C:
            def meth1(self): pass
            def meth2(self, arg): pass
            def meth3(self, a1, a2): pass

        # decorator: '@' dotted_name [ '(' [arglist] ')' ] NEWLINE
        # decorators: decorator+
        # decorated: decorators (classdef | funcdef)
        def class_decorator(x): return x
        @class_decorator
        class G: pass

    def test_dictcomps(self):
        # dictorsetmaker: ( (test ':' test (comp_for |
        #                                   (',' test ':' test)* [','])) |
        #                   (test (comp_for | (',' test)* [','])) )
        nums = [1, 2, 3]
        self.assertEqual({i:i+1 for i in nums}, {1: 2, 2: 3, 3: 4})

    def test_listcomps(self):
        # list comprehension tests
        nums = [1, 2, 3, 4, 5]
        strs = ["Apple", "Banana", "Coconut"]
        spcs = ["  Apple", " Banana ", "Coco  nut  "]

        self.assertEqual([s.strip() for s in spcs], ['Apple', 'Banana', 'Coco  nut'])
        self.assertEqual([3 * x for x in nums], [3, 6, 9, 12, 15])
        self.assertEqual([x for x in nums if x > 2], [3, 4, 5])
        self.assertEqual([(i, s) for i in nums for s in strs],
                         [(1, 'Apple'), (1, 'Banana'), (1, 'Coconut'),
                          (2, 'Apple'), (2, 'Banana'), (2, 'Coconut'),
                          (3, 'Apple'), (3, 'Banana'), (3, 'Coconut'),
                          (4, 'Apple'), (4, 'Banana'), (4, 'Coconut'),
                          (5, 'Apple'), (5, 'Banana'), (5, 'Coconut')])
        self.assertEqual([(i, s) for i in nums for s in [f for f in strs if "n" in f]],
                         [(1, 'Banana'), (1, 'Coconut'), (2, 'Banana'), (2, 'Coconut'),
                          (3, 'Banana'), (3, 'Coconut'), (4, 'Banana'), (4, 'Coconut'),
                          (5, 'Banana'), (5, 'Coconut')])
        self.assertEqual([(lambda a:[a**i for i in range(a+1)])(j) for j in range(5)],
                         [[1], [1, 1], [1, 2, 4], [1, 3, 9, 27], [1, 4, 16, 64, 256]])

        def test_in_func(l):
            return [0 < x < 3 for x in l if x > 2]

        self.assertEqual(test_in_func(nums), [False, False, False])

        def test_nested_front():
            self.assertEqual([[y for y in [x, x + 1]] for x in [1,3,5]],
                             [[1, 2], [3, 4], [5, 6]])

        test_nested_front()

        check_syntax_error(self, "[i, s for i in nums for s in strs]")
        check_syntax_error(self, "[x if y]")

        suppliers = [
          (1, "Boeing"),
          (2, "Ford"),
          (3, "Macdonalds")
        ]

        parts = [
          (10, "Airliner"),
          (20, "Engine"),
          (30, "Cheeseburger")
        ]

        suppart = [
          (1, 10), (1, 20), (2, 20), (3, 30)
        ]

        x = [
          (sname, pname)
            for (sno, sname) in suppliers
              for (pno, pname) in parts
                for (sp_sno, sp_pno) in suppart
                  if sno == sp_sno and pno == sp_pno
        ]

        self.assertEqual(x, [('Boeing', 'Airliner'), ('Boeing', 'Engine'), ('Ford', 'Engine'),
                             ('Macdonalds', 'Cheeseburger')])

    def test_genexps(self):
        # generator expression tests
        g = ([x for x in range(10)] for x in range(1))
        self.assertEqual(next(g), [x for x in range(10)])
        try:
            next(g)
            self.fail('should produce StopIteration exception')
        except StopIteration:
            pass

        a = 1
        try:
            g = (a for d in a)
            next(g)
            self.fail('should produce TypeError')
        except TypeError:
            pass

        self.assertEqual(list((x, y) for x in 'abcd' for y in 'abcd'), [(x, y) for x in 'abcd' for y in 'abcd'])
        self.assertEqual(list((x, y) for x in 'ab' for y in 'xy'), [(x, y) for x in 'ab' for y in 'xy'])

        a = [x for x in range(10)]
        b = (x for x in (y for y in a))
        self.assertEqual(sum(b), sum([x for x in range(10)]))

        self.assertEqual(sum(x**2 for x in range(10)), sum([x**2 for x in range(10)]))
        self.assertEqual(sum(x*x for x in range(10) if x%2), sum([x*x for x in range(10) if x%2]))
        self.assertEqual(sum(x for x in (y for y in range(10))), sum([x for x in range(10)]))
        self.assertEqual(sum(x for x in (y for y in (z for z in range(10)))), sum([x for x in range(10)]))
        self.assertEqual(sum(x for x in [y for y in (z for z in range(10))]), sum([x for x in range(10)]))
        self.assertEqual(sum(x for x in (y for y in (z for z in range(10) if True)) if True), sum([x for x in range(10)]))
        self.assertEqual(sum(x for x in (y for y in (z for z in range(10) if True) if False) if True), 0)
        check_syntax_error(self, "foo(x for x in range(10), 100)")
        check_syntax_error(self, "foo(100, x for x in range(10))")

    def test_comprehension_specials(self):
        # test for outmost iterable precomputation
        x = 10; g = (i for i in range(x)); x = 5
        self.assertEqual(len(list(g)), 10)

        # This should hold, since we're only precomputing outmost iterable.
        x = 10; t = False; g = ((i,j) for i in range(x) if t for j in range(x))
        x = 5; t = True;
        self.assertEqual([(i,j) for i in range(10) for j in range(5)], list(g))

        # Grammar allows multiple adjacent 'if's in listcomps and genexps,
        # even though it's silly. Make sure it works (ifelse broke this.)
        self.assertEqual([ x for x in range(10) if x % 2 if x % 3 ], [1, 5, 7])
        self.assertEqual(list(x for x in range(10) if x % 2 if x % 3), [1, 5, 7])

        # verify unpacking single element tuples in listcomp/genexp.
        self.assertEqual([x for x, in [(4,), (5,), (6,)]], [4, 5, 6])
        self.assertEqual(list(x for x, in [(7,), (8,), (9,)]), [7, 8, 9])

    def test_with_statement(self):
        class manager(object):
            def __enter__(self):
                return (1, 2)
            def __exit__(self, *args):
                pass

        with manager():
            pass
        with manager() as x:
            pass
        with manager() as (x, y):
            pass
        with manager(), manager():
            pass
        with manager() as x, manager() as y:
            pass
        with manager() as x, manager():
            pass

    def test_if_else_expr(self):
        # Test ifelse expressions in various cases
        def _checkeval(msg, ret):
            "helper to check that evaluation of expressions is done correctly"
            print(msg)
            return ret

        # the next line is not allowed anymore
        #self.assertEqual([ x() for x in lambda: True, lambda: False if x() ], [True])
        self.assertEqual([ x() for x in (lambda: True, lambda: False) if x() ], [True])
        self.assertEqual([ x(False) for x in (lambda x: False if x else True, lambda x: True if x else False) if x(False) ], [True])
        self.assertEqual((5 if 1 else _checkeval("check 1", 0)), 5)
        self.assertEqual((_checkeval("check 2", 0) if 0 else 5), 5)
        self.assertEqual((5 and 6 if 0 else 1), 1)
        self.assertEqual(((5 and 6) if 0 else 1), 1)
        self.assertEqual((5 and (6 if 1 else 1)), 6)
        self.assertEqual((0 or _checkeval("check 3", 2) if 0 else 3), 3)
        self.assertEqual((1 or _checkeval("check 4", 2) if 1 else _checkeval("check 5", 3)), 1)
        self.assertEqual((0 or 5 if 1 else _checkeval("check 6", 3)), 5)
        self.assertEqual((not 5 if 1 else 1), False)
        self.assertEqual((not 5 if 0 else 1), 1)
        self.assertEqual((6 + 1 if 1 else 2), 7)
        self.assertEqual((6 - 1 if 1 else 2), 5)
        self.assertEqual((6 * 2 if 1 else 4), 12)
        self.assertEqual((6 / 2 if 1 else 3), 3)
        self.assertEqual((6 < 4 if 0 else 2), 2)

    def test_paren_evaluation(self):
        self.assertEqual(16 // (4 // 2), 8)
        self.assertEqual((16 // 4) // 2, 2)
        self.assertEqual(16 // 4 // 2, 2)
        self.assertTrue(False is (2 is 3))
        self.assertFalse((False is 2) is 3)
        self.assertFalse(False is 2 is 3)

    def test_matrix_mul(self):
        # This is not intended to be a comprehensive test, rather just to be few
        # samples of the @ operator in test_grammar.py.
        class M:
            def __matmul__(self, o):
                return 4
            def __imatmul__(self, o):
                self.other = o
                return self
        m = M()
        self.assertEqual(m @ m, 4)
        m @= 42
        self.assertEqual(m.other, 42)

    def test_async_await(self):
        async def test():
            def sum():
                pass
            if 1:
                await someobj()

        self.assertEqual(test.__name__, 'test')
        self.assertTrue(bool(test.__code__.co_flags & inspect.CO_COROUTINE))

        def decorator(func):
            setattr(func, '_marked', True)
            return func

        @decorator
        async def test2():
            return 22
        self.assertTrue(test2._marked)
        self.assertEqual(test2.__name__, 'test2')
        self.assertTrue(bool(test2.__code__.co_flags & inspect.CO_COROUTINE))

    def test_async_for(self):
        class Done(Exception): pass

        class AIter:
            def __aiter__(self):
                return self
            async def __anext__(self):
                raise StopAsyncIteration

        async def foo():
            async for i in AIter():
                pass
            async for i, j in AIter():
                pass
            async for i in AIter():
                pass
            else:
                pass
            raise Done

        with self.assertRaises(Done):
            foo().send(None)

    def test_async_with(self):
        class Done(Exception): pass

        class manager:
            async def __aenter__(self):
                return (1, 2)
            async def __aexit__(self, *exc):
                return False

        async def foo():
            async with manager():
                pass
            async with manager() as x:
                pass
            async with manager() as (x, y):
                pass
            async with manager(), manager():
                pass
            async with manager() as x, manager() as y:
                pass
            async with manager() as x, manager():
                pass
            raise Done

        with self.assertRaises(Done):
            foo().send(None)


if __name__ == '__main__':
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\matplotlib\colorbar.py ===
"""
Colorbars are a visualization of the mapping from scalar values to colors.
In Matplotlib they are drawn into a dedicated `~.axes.Axes`.

.. note::
   Colorbars are typically created through `.Figure.colorbar` or its pyplot
   wrapper `.pyplot.colorbar`, which internally use `.Colorbar` together with
   `.make_axes_gridspec` (for `.GridSpec`-positioned Axes) or `.make_axes` (for
   non-`.GridSpec`-positioned Axes).

   End-users most likely won't need to directly use this module's API.
"""

import logging

import numpy as np

import matplotlib as mpl
from matplotlib import _api, cbook, collections, cm, colors, contour, ticker
import matplotlib.artist as martist
import matplotlib.patches as mpatches
import matplotlib.path as mpath
import matplotlib.spines as mspines
import matplotlib.transforms as mtransforms
from matplotlib import _docstring

_log = logging.getLogger(__name__)

_docstring.interpd.register(
    _make_axes_kw_doc="""
location : None or {'left', 'right', 'top', 'bottom'}
    The location, relative to the parent Axes, where the colorbar Axes
    is created.  It also determines the *orientation* of the colorbar
    (colorbars on the left and right are vertical, colorbars at the top
    and bottom are horizontal).  If None, the location will come from the
    *orientation* if it is set (vertical colorbars on the right, horizontal
    ones at the bottom), or default to 'right' if *orientation* is unset.

orientation : None or {'vertical', 'horizontal'}
    The orientation of the colorbar.  It is preferable to set the *location*
    of the colorbar, as that also determines the *orientation*; passing
    incompatible values for *location* and *orientation* raises an exception.

fraction : float, default: 0.15
    Fraction of original Axes to use for colorbar.

shrink : float, default: 1.0
    Fraction by which to multiply the size of the colorbar.

aspect : float, default: 20
    Ratio of long to short dimensions.

pad : float, default: 0.05 if vertical, 0.15 if horizontal
    Fraction of original Axes between colorbar and new image Axes.

anchor : (float, float), optional
    The anchor point of the colorbar Axes.
    Defaults to (0.0, 0.5) if vertical; (0.5, 1.0) if horizontal.

panchor : (float, float), or *False*, optional
    The anchor point of the colorbar parent Axes. If *False*, the parent
    axes' anchor will be unchanged.
    Defaults to (1.0, 0.5) if vertical; (0.5, 0.0) if horizontal.""",
    _colormap_kw_doc="""
extend : {'neither', 'both', 'min', 'max'}
    Make pointed end(s) for out-of-range values (unless 'neither').  These are
    set for a given colormap using the colormap set_under and set_over methods.

extendfrac : {*None*, 'auto', length, lengths}
    If set to *None*, both the minimum and maximum triangular colorbar
    extensions will have a length of 5% of the interior colorbar length (this
    is the default setting).

    If set to 'auto', makes the triangular colorbar extensions the same lengths
    as the interior boxes (when *spacing* is set to 'uniform') or the same
    lengths as the respective adjacent interior boxes (when *spacing* is set to
    'proportional').

    If a scalar, indicates the length of both the minimum and maximum
    triangular colorbar extensions as a fraction of the interior colorbar
    length.  A two-element sequence of fractions may also be given, indicating
    the lengths of the minimum and maximum colorbar extensions respectively as
    a fraction of the interior colorbar length.

extendrect : bool
    If *False* the minimum and maximum colorbar extensions will be triangular
    (the default).  If *True* the extensions will be rectangular.

ticks : None or list of ticks or Locator
    If None, ticks are determined automatically from the input.

format : None or str or Formatter
    If None, `~.ticker.ScalarFormatter` is used.
    Format strings, e.g., ``"%4.2e"`` or ``"{x:.2e}"``, are supported.
    An alternative `~.ticker.Formatter` may be given instead.

drawedges : bool
    Whether to draw lines at color boundaries.

label : str
    The label on the colorbar's long axis.

boundaries, values : None or a sequence
    If unset, the colormap will be displayed on a 0-1 scale.
    If sequences, *values* must have a length 1 less than *boundaries*.  For
    each region delimited by adjacent entries in *boundaries*, the color mapped
    to the corresponding value in *values* will be used.  The size of each
    region is determined by the *spacing* parameter.
    Normally only useful for indexed colors (i.e. ``norm=NoNorm()``) or other
    unusual circumstances.

spacing : {'uniform', 'proportional'}
    For discrete colorbars (`.BoundaryNorm` or contours), 'uniform' gives each
    color the same space; 'proportional' makes the space proportional to the
    data interval.""")


def _set_ticks_on_axis_warn(*args, **kwargs):
    # a top level function which gets put in at the axes'
    # set_xticks and set_yticks by Colorbar.__init__.
    _api.warn_external("Use the colorbar set_ticks() method instead.")


class _ColorbarSpine(mspines.Spine):
    def __init__(self, axes):
        self._ax = axes
        super().__init__(axes, 'colorbar', mpath.Path(np.empty((0, 2))))
        mpatches.Patch.set_transform(self, axes.transAxes)

    def get_window_extent(self, renderer=None):
        # This Spine has no Axis associated with it, and doesn't need to adjust
        # its location, so we can directly get the window extent from the
        # super-super-class.
        return mpatches.Patch.get_window_extent(self, renderer=renderer)

    def set_xy(self, xy):
        self._path = mpath.Path(xy, closed=True)
        self._xy = xy
        self.stale = True

    def draw(self, renderer):
        ret = mpatches.Patch.draw(self, renderer)
        self.stale = False
        return ret


class _ColorbarAxesLocator:
    """
    Shrink the Axes if there are triangular or rectangular extends.
    """
    def __init__(self, cbar):
        self._cbar = cbar
        self._orig_locator = cbar.ax._axes_locator

    def __call__(self, ax, renderer):
        if self._orig_locator is not None:
            pos = self._orig_locator(ax, renderer)
        else:
            pos = ax.get_position(original=True)
        if self._cbar.extend == 'neither':
            return pos

        y, extendlen = self._cbar._proportional_y()
        if not self._cbar._extend_lower():
            extendlen[0] = 0
        if not self._cbar._extend_upper():
            extendlen[1] = 0
        len = sum(extendlen) + 1
        shrink = 1 / len
        offset = extendlen[0] / len
        # we need to reset the aspect ratio of the axes to account
        # of the extends...
        if hasattr(ax, '_colorbar_info'):
            aspect = ax._colorbar_info['aspect']
        else:
            aspect = False
        # now shrink and/or offset to take into account the
        # extend tri/rectangles.
        if self._cbar.orientation == 'vertical':
            if aspect:
                self._cbar.ax.set_box_aspect(aspect*shrink)
            pos = pos.shrunk(1, shrink).translated(0, offset * pos.height)
        else:
            if aspect:
                self._cbar.ax.set_box_aspect(1/(aspect * shrink))
            pos = pos.shrunk(shrink, 1).translated(offset * pos.width, 0)
        return pos

    def get_subplotspec(self):
        # make tight_layout happy..
        return (
            self._cbar.ax.get_subplotspec()
            or getattr(self._orig_locator, "get_subplotspec", lambda: None)())


@_docstring.interpd
class Colorbar:
    r"""
    Draw a colorbar in an existing Axes.

    Typically, colorbars are created using `.Figure.colorbar` or
    `.pyplot.colorbar` and associated with `.ScalarMappable`\s (such as an
    `.AxesImage` generated via `~.axes.Axes.imshow`).

    In order to draw a colorbar not associated with other elements in the
    figure, e.g. when showing a colormap by itself, one can create an empty
    `.ScalarMappable`, or directly pass *cmap* and *norm* instead of *mappable*
    to `Colorbar`.

    Useful public methods are :meth:`set_label` and :meth:`add_lines`.

    Attributes
    ----------
    ax : `~matplotlib.axes.Axes`
        The `~.axes.Axes` instance in which the colorbar is drawn.
    lines : list
        A list of `.LineCollection` (empty if no lines were drawn).
    dividers : `.LineCollection`
        A LineCollection (empty if *drawedges* is ``False``).
    """

    n_rasterize = 50  # rasterize solids if number of colors >= n_rasterize

    def __init__(
        self, ax, mappable=None, *,
        alpha=None,
        location=None,
        extend=None,
        extendfrac=None,
        extendrect=False,
        ticks=None,
        format=None,
        values=None,
        boundaries=None,
        spacing='uniform',
        drawedges=False,
        label='',
        cmap=None, norm=None,  # redundant with *mappable*
        orientation=None, ticklocation='auto',  # redundant with *location*
    ):
        """
        Parameters
        ----------
        ax : `~matplotlib.axes.Axes`
            The `~.axes.Axes` instance in which the colorbar is drawn.

        mappable : `.ScalarMappable`
            The mappable whose colormap and norm will be used.

            To show the colors versus index instead of on a 0-1 scale, set the
            mappable's norm to ``colors.NoNorm()``.

        alpha : float
            The colorbar transparency between 0 (transparent) and 1 (opaque).

        location : None or {'left', 'right', 'top', 'bottom'}
            Set the colorbar's *orientation* and *ticklocation*. Colorbars on
            the left and right are vertical, colorbars at the top and bottom
            are horizontal. The *ticklocation* is the same as *location*, so if
            *location* is 'top', the ticks are on the top. *orientation* and/or
            *ticklocation* can be provided as well and overrides the value set by
            *location*, but there will be an error for incompatible combinations.

            .. versionadded:: 3.7

        %(_colormap_kw_doc)s

        Other Parameters
        ----------------
        cmap : `~matplotlib.colors.Colormap`, default: :rc:`image.cmap`
            The colormap to use.  This parameter is ignored, unless *mappable* is
            None.

        norm : `~matplotlib.colors.Normalize`
            The normalization to use.  This parameter is ignored, unless *mappable*
            is None.

        orientation : None or {'vertical', 'horizontal'}
            If None, use the value determined by *location*. If both
            *orientation* and *location* are None then defaults to 'vertical'.

        ticklocation : {'auto', 'left', 'right', 'top', 'bottom'}
            The location of the colorbar ticks. The *ticklocation* must match
            *orientation*. For example, a horizontal colorbar can only have ticks
            at the top or the bottom. If 'auto', the ticks will be the same as
            *location*, so a colorbar to the left will have ticks to the left. If
            *location* is None, the ticks will be at the bottom for a horizontal
            colorbar and at the right for a vertical.
        """
        if mappable is None:
            mappable = cm.ScalarMappable(norm=norm, cmap=cmap)

        self.mappable = mappable
        cmap = mappable.cmap
        norm = mappable.norm

        filled = True
        if isinstance(mappable, contour.ContourSet):
            cs = mappable
            alpha = cs.get_alpha()
            boundaries = cs._levels
            values = cs.cvalues
            extend = cs.extend
            filled = cs.filled
            if ticks is None:
                ticks = ticker.FixedLocator(cs.levels, nbins=10)
        elif isinstance(mappable, martist.Artist):
            alpha = mappable.get_alpha()

        mappable.colorbar = self
        mappable.colorbar_cid = mappable.callbacks.connect(
            'changed', self.update_normal)

        location_orientation = _get_orientation_from_location(location)

        _api.check_in_list(
            [None, 'vertical', 'horizontal'], orientation=orientation)
        _api.check_in_list(
            ['auto', 'left', 'right', 'top', 'bottom'],
            ticklocation=ticklocation)
        _api.check_in_list(
            ['uniform', 'proportional'], spacing=spacing)

        if location_orientation is not None and orientation is not None:
            if location_orientation != orientation:
                raise TypeError(
                    "location and orientation are mutually exclusive")
        else:
            orientation = orientation or location_orientation or "vertical"

        self.ax = ax
        self.ax._axes_locator = _ColorbarAxesLocator(self)

        if extend is None:
            if (not isinstance(mappable, contour.ContourSet)
                    and getattr(cmap, 'colorbar_extend', False) is not False):
                extend = cmap.colorbar_extend
            elif hasattr(norm, 'extend'):
                extend = norm.extend
            else:
                extend = 'neither'
        self.alpha = None
        # Call set_alpha to handle array-like alphas properly
        self.set_alpha(alpha)
        self.cmap = cmap
        self.norm = norm
        self.values = values
        self.boundaries = boundaries
        self.extend = extend
        self._inside = _api.check_getitem(
            {'neither': slice(0, None), 'both': slice(1, -1),
             'min': slice(1, None), 'max': slice(0, -1)},
            extend=extend)
        self.spacing = spacing
        self.orientation = orientation
        self.drawedges = drawedges
        self._filled = filled
        self.extendfrac = extendfrac
        self.extendrect = extendrect
        self._extend_patches = []
        self.solids = None
        self.solids_patches = []
        self.lines = []

        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.outline = self.ax.spines['outline'] = _ColorbarSpine(self.ax)

        self.dividers = collections.LineCollection(
            [],
            colors=[mpl.rcParams['axes.edgecolor']],
            linewidths=[0.5 * mpl.rcParams['axes.linewidth']],
            clip_on=False)
        self.ax.add_collection(self.dividers)

        self._locator = None
        self._minorlocator = None
        self._formatter = None
        self._minorformatter = None

        if ticklocation == 'auto':
            ticklocation = _get_ticklocation_from_orientation(
                orientation) if location is None else location
        self.ticklocation = ticklocation

        self.set_label(label)
        self._reset_locator_formatter_scale()

        if np.iterable(ticks):
            self._locator = ticker.FixedLocator(ticks, nbins=len(ticks))
        else:
            self._locator = ticks

        if isinstance(format, str):
            # Check format between FormatStrFormatter and StrMethodFormatter
            try:
                self._formatter = ticker.FormatStrFormatter(format)
                _ = self._formatter(0)
            except (TypeError, ValueError):
                self._formatter = ticker.StrMethodFormatter(format)
        else:
            self._formatter = format  # Assume it is a Formatter or None
        self._draw_all()

        if isinstance(mappable, contour.ContourSet) and not mappable.filled:
            self.add_lines(mappable)

        # Link the Axes and Colorbar for interactive use
        self.ax._colorbar = self
        # Don't navigate on any of these types of mappables
        if (isinstance(self.norm, (colors.BoundaryNorm, colors.NoNorm)) or
                isinstance(self.mappable, contour.ContourSet)):
            self.ax.set_navigate(False)

        # These are the functions that set up interactivity on this colorbar
        self._interactive_funcs = ["_get_view", "_set_view",
                                   "_set_view_from_bbox", "drag_pan"]
        for x in self._interactive_funcs:
            setattr(self.ax, x, getattr(self, x))
        # Set the cla function to the cbar's method to override it
        self.ax.cla = self._cbar_cla
        # Callbacks for the extend calculations to handle inverting the axis
        self._extend_cid1 = self.ax.callbacks.connect(
            "xlim_changed", self._do_extends)
        self._extend_cid2 = self.ax.callbacks.connect(
            "ylim_changed", self._do_extends)

    @property
    def long_axis(self):
        """Axis that has decorations (ticks, etc) on it."""
        if self.orientation == 'vertical':
            return self.ax.yaxis
        return self.ax.xaxis

    @property
    def locator(self):
        """Major tick `.Locator` for the colorbar."""
        return self.long_axis.get_major_locator()

    @locator.setter
    def locator(self, loc):
        self.long_axis.set_major_locator(loc)
        self._locator = loc

    @property
    def minorlocator(self):
        """Minor tick `.Locator` for the colorbar."""
        return self.long_axis.get_minor_locator()

    @minorlocator.setter
    def minorlocator(self, loc):
        self.long_axis.set_minor_locator(loc)
        self._minorlocator = loc

    @property
    def formatter(self):
        """Major tick label `.Formatter` for the colorbar."""
        return self.long_axis.get_major_formatter()

    @formatter.setter
    def formatter(self, fmt):
        self.long_axis.set_major_formatter(fmt)
        self._formatter = fmt

    @property
    def minorformatter(self):
        """Minor tick `.Formatter` for the colorbar."""
        return self.long_axis.get_minor_formatter()

    @minorformatter.setter
    def minorformatter(self, fmt):
        self.long_axis.set_minor_formatter(fmt)
        self._minorformatter = fmt

    def _cbar_cla(self):
        """Function to clear the interactive colorbar state."""
        for x in self._interactive_funcs:
            delattr(self.ax, x)
        # We now restore the old cla() back and can call it directly
        del self.ax.cla
        self.ax.cla()

    def update_normal(self, mappable=None):
        """
        Update solid patches, lines, etc.

        This is meant to be called when the norm of the image or contour plot
        to which this colorbar belongs changes.

        If the norm on the mappable is different than before, this resets the
        locator and formatter for the axis, so if these have been customized,
        they will need to be customized again.  However, if the norm only
        changes values of *vmin*, *vmax* or *cmap* then the old formatter
        and locator will be preserved.
        """
        if mappable:
            # The mappable keyword argument exists because
            # ScalarMappable.changed() emits self.callbacks.process('changed', self)
            # in contrast, ColorizingArtist (and Colorizer) does not use this keyword.
            # [ColorizingArtist.changed() emits self.callbacks.process('changed')]
            # Also, there is no test where self.mappable == mappable is not True
            # and possibly no use case.
            # Therefore, the mappable keyword can be deprecated if cm.ScalarMappable
            # is removed.
            self.mappable = mappable
        _log.debug('colorbar update normal %r %r', self.mappable.norm, self.norm)
        self.set_alpha(self.mappable.get_alpha())
        self.cmap = self.mappable.cmap
        if self.mappable.norm != self.norm:
            self.norm = self.mappable.norm
            self._reset_locator_formatter_scale()

        self._draw_all()
        if isinstance(self.mappable, contour.ContourSet):
            CS = self.mappable
            if not CS.filled:
                self.add_lines(CS)
        self.stale = True

    def _draw_all(self):
        """
        Calculate any free parameters based on the current cmap and norm,
        and do all the drawing.
        """
        if self.orientation == 'vertical':
            if mpl.rcParams['ytick.minor.visible']:
                self.minorticks_on()
        else:
            if mpl.rcParams['xtick.minor.visible']:
                self.minorticks_on()
        self.long_axis.set(label_position=self.ticklocation,
                              ticks_position=self.ticklocation)
        self._short_axis().set_ticks([])
        self._short_axis().set_ticks([], minor=True)

        # Set self._boundaries and self._values, including extensions.
        # self._boundaries are the edges of each square of color, and
        # self._values are the value to map into the norm to get the
        # color:
        self._process_values()
        # Set self.vmin and self.vmax to first and last boundary, excluding
        # extensions:
        self.vmin, self.vmax = self._boundaries[self._inside][[0, -1]]
        # Compute the X/Y mesh.
        X, Y = self._mesh()
        # draw the extend triangles, and shrink the inner Axes to accommodate.
        # also adds the outline path to self.outline spine:
        self._do_extends()
        lower, upper = self.vmin, self.vmax
        if self.long_axis.get_inverted():
            # If the axis is inverted, we need to swap the vmin/vmax
            lower, upper = upper, lower
        if self.orientation == 'vertical':
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(lower, upper)
        else:
            self.ax.set_ylim(0, 1)
            self.ax.set_xlim(lower, upper)

        # set up the tick locators and formatters.  A bit complicated because
        # boundary norms + uniform spacing requires a manual locator.
        self.update_ticks()

        if self._filled:
            ind = np.arange(len(self._values))
            if self._extend_lower():
                ind = ind[1:]
            if self._extend_upper():
                ind = ind[:-1]
            self._add_solids(X, Y, self._values[ind, np.newaxis])

    def _add_solids(self, X, Y, C):
        """Draw the colors; optionally add separators."""
        # Cleanup previously set artists.
        if self.solids is not None:
            self.solids.remove()
        for solid in self.solids_patches:
            solid.remove()
        # Add new artist(s), based on mappable type.  Use individual patches if
        # hatching is needed, pcolormesh otherwise.
        mappable = getattr(self, 'mappable', None)
        if (isinstance(mappable, contour.ContourSet)
                and any(hatch is not None for hatch in mappable.hatches)):
            self._add_solids_patches(X, Y, C, mappable)
        else:
            self.solids = self.ax.pcolormesh(
                X, Y, C, cmap=self.cmap, norm=self.norm, alpha=self.alpha,
                edgecolors='none', shading='flat')
            if not self.drawedges:
                if len(self._y) >= self.n_rasterize:
                    self.solids.set_rasterized(True)
        self._update_dividers()

    def _update_dividers(self):
        if not self.drawedges:
            self.dividers.set_segments([])
            return
        # Place all *internal* dividers.
        if self.orientation == 'vertical':
            lims = self.ax.get_ylim()
            bounds = (lims[0] < self._y) & (self._y < lims[1])
        else:
            lims = self.ax.get_xlim()
            bounds = (lims[0] < self._y) & (self._y < lims[1])
        y = self._y[bounds]
        # And then add outer dividers if extensions are on.
        if self._extend_lower():
            y = np.insert(y, 0, lims[0])
        if self._extend_upper():
            y = np.append(y, lims[1])
        X, Y = np.meshgrid([0, 1], y)
        if self.orientation == 'vertical':
            segments = np.dstack([X, Y])
        else:
            segments = np.dstack([Y, X])
        self.dividers.set_segments(segments)

    def _add_solids_patches(self, X, Y, C, mappable):
        hatches = mappable.hatches * (len(C) + 1)  # Have enough hatches.
        if self._extend_lower():
            # remove first hatch that goes into the extend patch
            hatches = hatches[1:]
        patches = []
        for i in range(len(X) - 1):
            xy = np.array([[X[i, 0], Y[i, 1]],
                           [X[i, 1], Y[i, 0]],
                           [X[i + 1, 1], Y[i + 1, 0]],
                           [X[i + 1, 0], Y[i + 1, 1]]])
            patch = mpatches.PathPatch(mpath.Path(xy),
                                       facecolor=self.cmap(self.norm(C[i][0])),
                                       hatch=hatches[i], linewidth=0,
                                       antialiased=False, alpha=self.alpha)
            self.ax.add_patch(patch)
            patches.append(patch)
        self.solids_patches = patches

    def _do_extends(self, ax=None):
        """
        Add the extend tri/rectangles on the outside of the Axes.

        ax is unused, but required due to the callbacks on xlim/ylim changed
        """
        # Clean up any previous extend patches
        for patch in self._extend_patches:
            patch.remove()
        self._extend_patches = []
        # extend lengths are fraction of the *inner* part of colorbar,
        # not the total colorbar:
        _, extendlen = self._proportional_y()
        bot = 0 - (extendlen[0] if self._extend_lower() else 0)
        top = 1 + (extendlen[1] if self._extend_upper() else 0)

        # xyout is the outline of the colorbar including the extend patches:
        if not self.extendrect:
            # triangle:
            xyout = np.array([[0, 0], [0.5, bot], [1, 0],
                              [1, 1], [0.5, top], [0, 1], [0, 0]])
        else:
            # rectangle:
            xyout = np.array([[0, 0], [0, bot], [1, bot], [1, 0],
                              [1, 1], [1, top], [0, top], [0, 1],
                              [0, 0]])

        if self.orientation == 'horizontal':
            xyout = xyout[:, ::-1]

        # xyout is the path for the spine:
        self.outline.set_xy(xyout)
        if not self._filled:
            return

        # Make extend triangles or rectangles filled patches.  These are
        # defined in the outer parent axes' coordinates:
        mappable = getattr(self, 'mappable', None)
        if (isinstance(mappable, contour.ContourSet)
                and any(hatch is not None for hatch in mappable.hatches)):
            hatches = mappable.hatches * (len(self._y) + 1)
        else:
            hatches = [None] * (len(self._y) + 1)

        if self._extend_lower():
            if not self.extendrect:
                # triangle
                xy = np.array([[0, 0], [0.5, bot], [1, 0]])
            else:
                # rectangle
                xy = np.array([[0, 0], [0, bot], [1., bot], [1, 0]])
            if self.orientation == 'horizontal':
                xy = xy[:, ::-1]
            # add the patch
            val = -1 if self.long_axis.get_inverted() else 0
            color = self.cmap(self.norm(self._values[val]))
            patch = mpatches.PathPatch(
                mpath.Path(xy), facecolor=color, alpha=self.alpha,
                linewidth=0, antialiased=False,
                transform=self.ax.transAxes,
                hatch=hatches[0], clip_on=False,
                # Place it right behind the standard patches, which is
                # needed if we updated the extends
                zorder=np.nextafter(self.ax.patch.zorder, -np.inf))
            self.ax.add_patch(patch)
            self._extend_patches.append(patch)
            # remove first hatch that goes into the extend patch
            hatches = hatches[1:]
        if self._extend_upper():
            if not self.extendrect:
                # triangle
                xy = np.array([[0, 1], [0.5, top], [1, 1]])
            else:
                # rectangle
                xy = np.array([[0, 1], [0, top], [1, top], [1, 1]])
            if self.orientation == 'horizontal':
                xy = xy[:, ::-1]
            # add the patch
            val = 0 if self.long_axis.get_inverted() else -1
            color = self.cmap(self.norm(self._values[val]))
            hatch_idx = len(self._y) - 1
            patch = mpatches.PathPatch(
                mpath.Path(xy), facecolor=color, alpha=self.alpha,
                linewidth=0, antialiased=False,
                transform=self.ax.transAxes, hatch=hatches[hatch_idx],
                clip_on=False,
                # Place it right behind the standard patches, which is
                # needed if we updated the extends
                zorder=np.nextafter(self.ax.patch.zorder, -np.inf))
            self.ax.add_patch(patch)
            self._extend_patches.append(patch)

        self._update_dividers()

    def add_lines(self, *args, **kwargs):
        """
        Draw lines on the colorbar.

        The lines are appended to the list :attr:`lines`.

        Parameters
        ----------
        levels : array-like
            The positions of the lines.
        colors : :mpltype:`color` or list of :mpltype:`color`
            Either a single color applying to all lines or one color value for
            each line.
        linewidths : float or array-like
            Either a single linewidth applying to all lines or one linewidth
            for each line.
        erase : bool, default: True
            Whether to remove any previously added lines.

        Notes
        -----
        Alternatively, this method can also be called with the signature
        ``colorbar.add_lines(contour_set, erase=True)``, in which case
        *levels*, *colors*, and *linewidths* are taken from *contour_set*.
        """
        params = _api.select_matching_signature(
            [lambda self, CS, erase=True: locals(),
             lambda self, levels, colors, linewidths, erase=True: locals()],
            self, *args, **kwargs)
        if "CS" in params:
            self, cs, erase = params.values()
            if not isinstance(cs, contour.ContourSet) or cs.filled:
                raise ValueError("If a single artist is passed to add_lines, "
                                 "it must be a ContourSet of lines")
            # TODO: Make colorbar lines auto-follow changes in contour lines.
            return self.add_lines(
                cs.levels,
                cs.to_rgba(cs.cvalues, cs.alpha),
                cs.get_linewidths(),
                erase=erase)
        else:
            self, levels, colors, linewidths, erase = params.values()

        y = self._locate(levels)
        rtol = (self._y[-1] - self._y[0]) * 1e-10
        igood = (y < self._y[-1] + rtol) & (y > self._y[0] - rtol)
        y = y[igood]
        if np.iterable(colors):
            colors = np.asarray(colors)[igood]
        if np.iterable(linewidths):
            linewidths = np.asarray(linewidths)[igood]
        X, Y = np.meshgrid([0, 1], y)
        if self.orientation == 'vertical':
            xy = np.stack([X, Y], axis=-1)
        else:
            xy = np.stack([Y, X], axis=-1)
        col = collections.LineCollection(xy, linewidths=linewidths,
                                         colors=colors)

        if erase and self.lines:
            for lc in self.lines:
                lc.remove()
            self.lines = []
        self.lines.append(col)

        # make a clip path that is just a linewidth bigger than the Axes...
        fac = np.max(linewidths) / 72
        xy = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])
        inches = self.ax.get_figure().dpi_scale_trans
        # do in inches:
        xy = inches.inverted().transform(self.ax.transAxes.transform(xy))
        xy[[0, 1, 4], 1] -= fac
        xy[[2, 3], 1] += fac
        # back to axes units...
        xy = self.ax.transAxes.inverted().transform(inches.transform(xy))
        col.set_clip_path(mpath.Path(xy, closed=True),
                          self.ax.transAxes)
        self.ax.add_collection(col)
        self.stale = True

    def update_ticks(self):
        """
        Set up the ticks and ticklabels. This should not be needed by users.
        """
        # Get the locator and formatter; defaults to self._locator if not None.
        self._get_ticker_locator_formatter()
        self.long_axis.set_major_locator(self._locator)
        self.long_axis.set_minor_locator(self._minorlocator)
        self.long_axis.set_major_formatter(self._formatter)

    def _get_ticker_locator_formatter(self):
        """
        Return the ``locator`` and ``formatter`` of the colorbar.

        If they have not been defined (i.e. are *None*), the formatter and
        locator are retrieved from the axis, or from the value of the
        boundaries for a boundary norm.

        Called by update_ticks...
        """
        locator = self._locator
        formatter = self._formatter
        minorlocator = self._minorlocator
        if isinstance(self.norm, colors.BoundaryNorm):
            b = self.norm.boundaries
            if locator is None:
                locator = ticker.FixedLocator(b, nbins=10)
            if minorlocator is None:
                minorlocator = ticker.FixedLocator(b)
        elif isinstance(self.norm, colors.NoNorm):
            if locator is None:
                # put ticks on integers between the boundaries of NoNorm
                nv = len(self._values)
                base = 1 + int(nv / 10)
                locator = ticker.IndexLocator(base=base, offset=.5)
        elif self.boundaries is not None:
            b = self._boundaries[self._inside]
            if locator is None:
                locator = ticker.FixedLocator(b, nbins=10)
        else:  # most cases:
            if locator is None:
                # we haven't set the locator explicitly, so use the default
                # for this axis:
                locator = self.long_axis.get_major_locator()
            if minorlocator is None:
                minorlocator = self.long_axis.get_minor_locator()

        if minorlocator is None:
            minorlocator = ticker.NullLocator()

        if formatter is None:
            formatter = self.long_axis.get_major_formatter()

        self._locator = locator
        self._formatter = formatter
        self._minorlocator = minorlocator
        _log.debug('locator: %r', locator)

    def set_ticks(self, ticks, *, labels=None, minor=False, **kwargs):
        """
        Set tick locations.

        Parameters
        ----------
        ticks : 1D array-like
            List of tick locations.
        labels : list of str, optional
            List of tick labels. If not set, the labels show the data value.
        minor : bool, default: False
            If ``False``, set the major ticks; if ``True``, the minor ticks.
        **kwargs
            `.Text` properties for the labels. These take effect only if you
            pass *labels*. In other cases, please use `~.Axes.tick_params`.
        """
        if np.iterable(ticks):
            self.long_axis.set_ticks(ticks, labels=labels, minor=minor,
                                        **kwargs)
            self._locator = self.long_axis.get_major_locator()
        else:
            self._locator = ticks
            self.long_axis.set_major_locator(self._locator)
        self.stale = True

    def get_ticks(self, minor=False):
        """
        Return the ticks as a list of locations.

        Parameters
        ----------
        minor : boolean, default: False
            if True return the minor ticks.
        """
        if minor:
            return self.long_axis.get_minorticklocs()
        else:
            return self.long_axis.get_majorticklocs()

    def set_ticklabels(self, ticklabels, *, minor=False, **kwargs):
        """
        [*Discouraged*] Set tick labels.

        .. admonition:: Discouraged

            The use of this method is discouraged, because of the dependency
            on tick positions. In most cases, you'll want to use
            ``set_ticks(positions, labels=labels)`` instead.

            If you are using this method, you should always fix the tick
            positions before, e.g. by using `.Colorbar.set_ticks` or by
            explicitly setting a `~.ticker.FixedLocator` on the long axis
            of the colorbar. Otherwise, ticks are free to move and the
            labels may end up in unexpected positions.

        Parameters
        ----------
        ticklabels : sequence of str or of `.Text`
            Texts for labeling each tick location in the sequence set by
            `.Colorbar.set_ticks`; the number of labels must match the number
            of locations.

        update_ticks : bool, default: True
            This keyword argument is ignored and will be removed.
            Deprecated

        minor : bool
            If True, set minor ticks instead of major ticks.

        **kwargs
            `.Text` properties for the labels.
        """
        self.long_axis.set_ticklabels(ticklabels, minor=minor, **kwargs)

    def minorticks_on(self):
        """
        Turn on colorbar minor ticks.
        """
        self.ax.minorticks_on()
        self._short_axis().set_minor_locator(ticker.NullLocator())

    def minorticks_off(self):
        """Turn the minor ticks of the colorbar off."""
        self._minorlocator = ticker.NullLocator()
        self.long_axis.set_minor_locator(self._minorlocator)

    def set_label(self, label, *, loc=None, **kwargs):
        """
        Add a label to the long axis of the colorbar.

        Parameters
        ----------
        label : str
            The label text.
        loc : str, optional
            The location of the label.

            - For horizontal orientation one of {'left', 'center', 'right'}
            - For vertical orientation one of {'bottom', 'center', 'top'}

            Defaults to :rc:`xaxis.labellocation` or :rc:`yaxis.labellocation`
            depending on the orientation.
        **kwargs
            Keyword arguments are passed to `~.Axes.set_xlabel` /
            `~.Axes.set_ylabel`.
            Supported keywords are *labelpad* and `.Text` properties.
        """
        if self.orientation == "vertical":
            self.ax.set_ylabel(label, loc=loc, **kwargs)
        else:
            self.ax.set_xlabel(label, loc=loc, **kwargs)
        self.stale = True

    def set_alpha(self, alpha):
        """
        Set the transparency between 0 (transparent) and 1 (opaque).

        If an array is provided, *alpha* will be set to None to use the
        transparency values associated with the colormap.
        """
        self.alpha = None if isinstance(alpha, np.ndarray) else alpha

    def _set_scale(self, scale, **kwargs):
        """
        Set the colorbar long axis scale.

        Parameters
        ----------
        scale : {"linear", "log", "symlog", "logit", ...} or `.ScaleBase`
            The axis scale type to apply.

        **kwargs
            Different keyword arguments are accepted, depending on the scale.
            See the respective class keyword arguments:

            - `matplotlib.scale.LinearScale`
            - `matplotlib.scale.LogScale`
            - `matplotlib.scale.SymmetricalLogScale`
            - `matplotlib.scale.LogitScale`
            - `matplotlib.scale.FuncScale`
            - `matplotlib.scale.AsinhScale`

        Notes
        -----
        By default, Matplotlib supports the above-mentioned scales.
        Additionally, custom scales may be registered using
        `matplotlib.scale.register_scale`. These scales can then also
        be used here.
        """
        self.long_axis._set_axes_scale(scale, **kwargs)

    def remove(self):
        """
        Remove this colorbar from the figure.

        If the colorbar was created with ``use_gridspec=True`` the previous
        gridspec is restored.
        """
        if hasattr(self.ax, '_colorbar_info'):
            parents = self.ax._colorbar_info['parents']
            for a in parents:
                if self.ax in a._colorbars:
                    a._colorbars.remove(self.ax)

        self.ax.remove()

        self.mappable.callbacks.disconnect(self.mappable.colorbar_cid)
        self.mappable.colorbar = None
        self.mappable.colorbar_cid = None
        # Remove the extension callbacks
        self.ax.callbacks.disconnect(self._extend_cid1)
        self.ax.callbacks.disconnect(self._extend_cid2)

        try:
            ax = self.mappable.axes
        except AttributeError:
            return
        try:
            subplotspec = self.ax.get_subplotspec().get_gridspec()._subplot_spec
        except AttributeError:  # use_gridspec was False
            pos = ax.get_position(original=True)
            ax._set_position(pos)
        else:  # use_gridspec was True
            ax.set_subplotspec(subplotspec)

    def _process_values(self):
        """
        Set `_boundaries` and `_values` based on the self.boundaries and
        self.values if not None, or based on the size of the colormap and
        the vmin/vmax of the norm.
        """
        if self.values is not None:
            # set self._boundaries from the values...
            self._values = np.array(self.values)
            if self.boundaries is None:
                # bracket values by 1/2 dv:
                b = np.zeros(len(self.values) + 1)
                b[1:-1] = 0.5 * (self._values[:-1] + self._values[1:])
                b[0] = 2.0 * b[1] - b[2]
                b[-1] = 2.0 * b[-2] - b[-3]
                self._boundaries = b
                return
            self._boundaries = np.array(self.boundaries)
            return

        # otherwise values are set from the boundaries
        if isinstance(self.norm, colors.BoundaryNorm):
            b = self.norm.boundaries
        elif isinstance(self.norm, colors.NoNorm):
            # NoNorm has N blocks, so N+1 boundaries, centered on integers:
            b = np.arange(self.cmap.N + 1) - .5
        elif self.boundaries is not None:
            b = self.boundaries
        else:
            # otherwise make the boundaries from the size of the cmap:
            N = self.cmap.N + 1
            b, _ = self._uniform_y(N)
        # add extra boundaries if needed:
        if self._extend_lower():
            b = np.hstack((b[0] - 1, b))
        if self._extend_upper():
            b = np.hstack((b, b[-1] + 1))

        # transform from 0-1 to vmin-vmax:
        if self.mappable.get_array() is not None:
            self.mappable.autoscale_None()
        if not self.norm.scaled():
            # If we still aren't scaled after autoscaling, use 0, 1 as default
            self.norm.vmin = 0
            self.norm.vmax = 1
        self.norm.vmin, self.norm.vmax = mtransforms.nonsingular(
            self.norm.vmin, self.norm.vmax, expander=0.1)
        if (not isinstance(self.norm, colors.BoundaryNorm) and
                (self.boundaries is None)):
            b = self.norm.inverse(b)

        self._boundaries = np.asarray(b, dtype=float)
        self._values = 0.5 * (self._boundaries[:-1] + self._boundaries[1:])
        if isinstance(self.norm, colors.NoNorm):
            self._values = (self._values + 0.00001).astype(np.int16)

    def _mesh(self):
        """
        Return the coordinate arrays for the colorbar pcolormesh/patches.

        These are scaled between vmin and vmax, and already handle colorbar
        orientation.
        """
        y, _ = self._proportional_y()
        # Use the vmin and vmax of the colorbar, which may not be the same
        # as the norm. There are situations where the colormap has a
        # narrower range than the colorbar and we want to accommodate the
        # extra contours.
        if (isinstance(self.norm, (colors.BoundaryNorm, colors.NoNorm))
                or self.boundaries is not None):
            # not using a norm.
            y = y * (self.vmax - self.vmin) + self.vmin
        else:
            # Update the norm values in a context manager as it is only
            # a temporary change and we don't want to propagate any signals
            # attached to the norm (callbacks.blocked).
            with (self.norm.callbacks.blocked(),
                  cbook._setattr_cm(self.norm, vmin=self.vmin, vmax=self.vmax)):
                y = self.norm.inverse(y)
        self._y = y
        X, Y = np.meshgrid([0., 1.], y)
        if self.orientation == 'vertical':
            return (X, Y)
        else:
            return (Y, X)

    def _forward_boundaries(self, x):
        # map boundaries equally between 0 and 1...
        b = self._boundaries
        y = np.interp(x, b, np.linspace(0, 1, len(b)))
        # the following avoids ticks in the extends:
        eps = (b[-1] - b[0]) * 1e-6
        # map these _well_ out of bounds to keep any ticks out
        # of the extends region...
        y[x < b[0]-eps] = -1
        y[x > b[-1]+eps] = 2
        return y

    def _inverse_boundaries(self, x):
        # invert the above...
        b = self._boundaries
        return np.interp(x, np.linspace(0, 1, len(b)), b)

    def _reset_locator_formatter_scale(self):
        """
        Reset the locator et al to defaults.  Any user-hardcoded changes
        need to be re-entered if this gets called (either at init, or when
        the mappable normal gets changed: Colorbar.update_normal)
        """
        self._process_values()
        self._locator = None
        self._minorlocator = None
        self._formatter = None
        self._minorformatter = None
        if (isinstance(self.mappable, contour.ContourSet) and
                isinstance(self.norm, colors.LogNorm)):
            # if contours have lognorm, give them a log scale...
            self._set_scale('log')
        elif (self.boundaries is not None or
                isinstance(self.norm, colors.BoundaryNorm)):
            if self.spacing == 'uniform':
                funcs = (self._forward_boundaries, self._inverse_boundaries)
                self._set_scale('function', functions=funcs)
            elif self.spacing == 'proportional':
                self._set_scale('linear')
        elif getattr(self.norm, '_scale', None):
            # use the norm's scale (if it exists and is not None):
            self._set_scale(self.norm._scale)
        elif type(self.norm) is colors.Normalize:
            # plain Normalize:
            self._set_scale('linear')
        else:
            # norm._scale is None or not an attr: derive the scale from
            # the Norm:
            funcs = (self.norm, self.norm.inverse)
            self._set_scale('function', functions=funcs)

    def _locate(self, x):
        """
        Given a set of color data values, return their
        corresponding colorbar data coordinates.
        """
        if isinstance(self.norm, (colors.NoNorm, colors.BoundaryNorm)):
            b = self._boundaries
            xn = x
        else:
            # Do calculations using normalized coordinates so
            # as to make the interpolation more accurate.
            b = self.norm(self._boundaries, clip=False).filled()
            xn = self.norm(x, clip=False).filled()

        bunique = b[self._inside]
        yunique = self._y

        z = np.interp(xn, bunique, yunique)
        return z

    # trivial helpers

    def _uniform_y(self, N):
        """
        Return colorbar data coordinates for *N* uniformly
        spaced boundaries, plus extension lengths if required.
        """
        automin = automax = 1. / (N - 1.)
        extendlength = self._get_extension_lengths(self.extendfrac,
                                                   automin, automax,
                                                   default=0.05)
        y = np.linspace(0, 1, N)
        return y, extendlength

    def _proportional_y(self):
        """
        Return colorbar data coordinates for the boundaries of
        a proportional colorbar, plus extension lengths if required:
        """
        if (isinstance(self.norm, colors.BoundaryNorm) or
                self.boundaries is not None):
            y = (self._boundaries - self._boundaries[self._inside][0])
            y = y / (self._boundaries[self._inside][-1] -
                     self._boundaries[self._inside][0])
            # need yscaled the same as the axes scale to get
            # the extend lengths.
            if self.spacing == 'uniform':
                yscaled = self._forward_boundaries(self._boundaries)
            else:
                yscaled = y
        else:
            y = self.norm(self._boundaries.copy())
            y = np.ma.filled(y, np.nan)
            # the norm and the scale should be the same...
            yscaled = y
        y = y[self._inside]
        yscaled = yscaled[self._inside]
        # normalize from 0..1:
        norm = colors.Normalize(y[0], y[-1])
        y = np.ma.filled(norm(y), np.nan)
        norm = colors.Normalize(yscaled[0], yscaled[-1])
        yscaled = np.ma.filled(norm(yscaled), np.nan)
        # make the lower and upper extend lengths proportional to the lengths
        # of the first and last boundary spacing (if extendfrac='auto'):
        automin = yscaled[1] - yscaled[0]
        automax = yscaled[-1] - yscaled[-2]
        extendlength = [0, 0]
        if self._extend_lower() or self._extend_upper():
            extendlength = self._get_extension_lengths(
                    self.extendfrac, automin, automax, default=0.05)
        return y, extendlength

    def _get_extension_lengths(self, frac, automin, automax, default=0.05):
        """
        Return the lengths of colorbar extensions.

        This is a helper method for _uniform_y and _proportional_y.
        """
        # Set the default value.
        extendlength = np.array([default, default])
        if isinstance(frac, str):
            _api.check_in_list(['auto'], extendfrac=frac.lower())
            # Use the provided values when 'auto' is required.
            extendlength[:] = [automin, automax]
        elif frac is not None:
            try:
                # Try to set min and max extension fractions directly.
                extendlength[:] = frac
                # If frac is a sequence containing None then NaN may
                # be encountered. This is an error.
                if np.isnan(extendlength).any():
                    raise ValueError()
            except (TypeError, ValueError) as err:
                # Raise an error on encountering an invalid value for frac.
                raise ValueError('invalid value for extendfrac') from err
        return extendlength

    def _extend_lower(self):
        """Return whether the lower limit is open ended."""
        minmax = "max" if self.long_axis.get_inverted() else "min"
        return self.extend in ('both', minmax)

    def _extend_upper(self):
        """Return whether the upper limit is open ended."""
        minmax = "min" if self.long_axis.get_inverted() else "max"
        return self.extend in ('both', minmax)

    def _short_axis(self):
        """Return the short axis"""
        if self.orientation == 'vertical':
            return self.ax.xaxis
        return self.ax.yaxis

    def _get_view(self):
        # docstring inherited
        # An interactive view for a colorbar is the norm's vmin/vmax
        return self.norm.vmin, self.norm.vmax

    def _set_view(self, view):
        # docstring inherited
        # An interactive view for a colorbar is the norm's vmin/vmax
        self.norm.vmin, self.norm.vmax = view

    def _set_view_from_bbox(self, bbox, direction='in',
                            mode=None, twinx=False, twiny=False):
        # docstring inherited
        # For colorbars, we use the zoom bbox to scale the norm's vmin/vmax
        new_xbound, new_ybound = self.ax._prepare_view_from_bbox(
            bbox, direction=direction, mode=mode, twinx=twinx, twiny=twiny)
        if self.orientation == 'horizontal':
            self.norm.vmin, self.norm.vmax = new_xbound
        elif self.orientation == 'vertical':
            self.norm.vmin, self.norm.vmax = new_ybound

    def drag_pan(self, button, key, x, y):
        # docstring inherited
        points = self.ax._get_pan_points(button, key, x, y)
        if points is not None:
            if self.orientation == 'horizontal':
                self.norm.vmin, self.norm.vmax = points[:, 0]
            elif self.orientation == 'vertical':
                self.norm.vmin, self.norm.vmax = points[:, 1]


ColorbarBase = Colorbar  # Backcompat API


def _normalize_location_orientation(location, orientation):
    if location is None:
        location = _get_ticklocation_from_orientation(orientation)
    loc_settings = _api.check_getitem({
        "left":   {"location": "left", "anchor": (1.0, 0.5),
                   "panchor": (0.0, 0.5), "pad": 0.10},
        "right":  {"location": "right", "anchor": (0.0, 0.5),
                   "panchor": (1.0, 0.5), "pad": 0.05},
        "top":    {"location": "top", "anchor": (0.5, 0.0),
                   "panchor": (0.5, 1.0), "pad": 0.05},
        "bottom": {"location": "bottom", "anchor": (0.5, 1.0),
                   "panchor": (0.5, 0.0), "pad": 0.15},
    }, location=location)
    loc_settings["orientation"] = _get_orientation_from_location(location)
    if orientation is not None and orientation != loc_settings["orientation"]:
        # Allow the user to pass both if they are consistent.
        raise TypeError("location and orientation are mutually exclusive")
    return loc_settings


def _get_orientation_from_location(location):
    return _api.check_getitem(
        {None: None, "left": "vertical", "right": "vertical",
         "top": "horizontal", "bottom": "horizontal"}, location=location)


def _get_ticklocation_from_orientation(orientation):
    return _api.check_getitem(
        {None: "right", "vertical": "right", "horizontal": "bottom"},
        orientation=orientation)


@_docstring.interpd
def make_axes(parents, location=None, orientation=None, fraction=0.15,
              shrink=1.0, aspect=20, **kwargs):
    """
    Create an `~.axes.Axes` suitable for a colorbar.

    The Axes is placed in the figure of the *parents* Axes, by resizing and
    repositioning *parents*.

    Parameters
    ----------
    parents : `~matplotlib.axes.Axes` or iterable or `numpy.ndarray` of `~.axes.Axes`
        The Axes to use as parents for placing the colorbar.
    %(_make_axes_kw_doc)s

    Returns
    -------
    cax : `~matplotlib.axes.Axes`
        The child Axes.
    kwargs : dict
        The reduced keyword dictionary to be passed when creating the colorbar
        instance.
    """
    loc_settings = _normalize_location_orientation(location, orientation)
    # put appropriate values into the kwargs dict for passing back to
    # the Colorbar class
    kwargs['orientation'] = loc_settings['orientation']
    location = kwargs['ticklocation'] = loc_settings['location']

    anchor = kwargs.pop('anchor', loc_settings['anchor'])
    panchor = kwargs.pop('panchor', loc_settings['panchor'])
    aspect0 = aspect
    # turn parents into a list if it is not already.  Note we cannot
    # use .flatten or .ravel as these copy the references rather than
    # reuse them, leading to a memory leak
    if isinstance(parents, np.ndarray):
        parents = list(parents.flat)
    elif np.iterable(parents):
        parents = list(parents)
    else:
        parents = [parents]

    fig = parents[0].get_figure()

    pad0 = 0.05 if fig.get_constrained_layout() else loc_settings['pad']
    pad = kwargs.pop('pad', pad0)

    if not all(fig is ax.get_figure() for ax in parents):
        raise ValueError('Unable to create a colorbar Axes as not all '
                         'parents share the same figure.')

    # take a bounding box around all of the given Axes
    parents_bbox = mtransforms.Bbox.union(
        [ax.get_position(original=True).frozen() for ax in parents])

    pb = parents_bbox
    if location in ('left', 'right'):
        if location == 'left':
            pbcb, _, pb1 = pb.splitx(fraction, fraction + pad)
        else:
            pb1, _, pbcb = pb.splitx(1 - fraction - pad, 1 - fraction)
        pbcb = pbcb.shrunk(1.0, shrink).anchored(anchor, pbcb)
    else:
        if location == 'bottom':
            pbcb, _, pb1 = pb.splity(fraction, fraction + pad)
        else:
            pb1, _, pbcb = pb.splity(1 - fraction - pad, 1 - fraction)
        pbcb = pbcb.shrunk(shrink, 1.0).anchored(anchor, pbcb)

        # define the aspect ratio in terms of y's per x rather than x's per y
        aspect = 1.0 / aspect

    # define a transform which takes us from old axes coordinates to
    # new axes coordinates
    shrinking_trans = mtransforms.BboxTransform(parents_bbox, pb1)

    # transform each of the Axes in parents using the new transform
    for ax in parents:
        new_posn = shrinking_trans.transform(ax.get_position(original=True))
        new_posn = mtransforms.Bbox(new_posn)
        ax._set_position(new_posn)
        if panchor is not False:
            ax.set_anchor(panchor)

    cax = fig.add_axes(pbcb, label="<colorbar>")
    for a in parents:
        # tell the parent it has a colorbar
        a._colorbars += [cax]
    cax._colorbar_info = dict(
        parents=parents,
        location=location,
        shrink=shrink,
        anchor=anchor,
        panchor=panchor,
        fraction=fraction,
        aspect=aspect0,
        pad=pad)
    # and we need to set the aspect ratio by hand...
    cax.set_anchor(anchor)
    cax.set_box_aspect(aspect)
    cax.set_aspect('auto')

    return cax, kwargs


@_docstring.interpd
def make_axes_gridspec(parent, *, location=None, orientation=None,
                       fraction=0.15, shrink=1.0, aspect=20, **kwargs):
    """
    Create an `~.axes.Axes` suitable for a colorbar.

    The Axes is placed in the figure of the *parent* Axes, by resizing and
    repositioning *parent*.

    This function is similar to `.make_axes` and mostly compatible with it.
    Primary differences are

    - `.make_axes_gridspec` requires the *parent* to have a subplotspec.
    - `.make_axes` positions the Axes in figure coordinates;
      `.make_axes_gridspec` positions it using a subplotspec.
    - `.make_axes` updates the position of the parent.  `.make_axes_gridspec`
      replaces the parent gridspec with a new one.

    Parameters
    ----------
    parent : `~matplotlib.axes.Axes`
        The Axes to use as parent for placing the colorbar.
    %(_make_axes_kw_doc)s

    Returns
    -------
    cax : `~matplotlib.axes.Axes`
        The child Axes.
    kwargs : dict
        The reduced keyword dictionary to be passed when creating the colorbar
        instance.
    """

    loc_settings = _normalize_location_orientation(location, orientation)
    kwargs['orientation'] = loc_settings['orientation']
    location = kwargs['ticklocation'] = loc_settings['location']

    aspect0 = aspect
    anchor = kwargs.pop('anchor', loc_settings['anchor'])
    panchor = kwargs.pop('panchor', loc_settings['panchor'])
    pad = kwargs.pop('pad', loc_settings["pad"])
    wh_space = 2 * pad / (1 - pad)

    if location in ('left', 'right'):
        gs = parent.get_subplotspec().subgridspec(
            3, 2, wspace=wh_space, hspace=0,
            height_ratios=[(1-anchor[1])*(1-shrink), shrink, anchor[1]*(1-shrink)])
        if location == 'left':
            gs.set_width_ratios([fraction, 1 - fraction - pad])
            ss_main = gs[:, 1]
            ss_cb = gs[1, 0]
        else:
            gs.set_width_ratios([1 - fraction - pad, fraction])
            ss_main = gs[:, 0]
            ss_cb = gs[1, 1]
    else:
        gs = parent.get_subplotspec().subgridspec(
            2, 3, hspace=wh_space, wspace=0,
            width_ratios=[anchor[0]*(1-shrink), shrink, (1-anchor[0])*(1-shrink)])
        if location == 'top':
            gs.set_height_ratios([fraction, 1 - fraction - pad])
            ss_main = gs[1, :]
            ss_cb = gs[0, 1]
        else:
            gs.set_height_ratios([1 - fraction - pad, fraction])
            ss_main = gs[0, :]
            ss_cb = gs[1, 1]
        aspect = 1 / aspect

    parent.set_subplotspec(ss_main)
    if panchor is not False:
        parent.set_anchor(panchor)

    fig = parent.get_figure()
    cax = fig.add_subplot(ss_cb, label="<colorbar>")
    cax.set_anchor(anchor)
    cax.set_box_aspect(aspect)
    cax.set_aspect('auto')
    cax._colorbar_info = dict(
        location=location,
        parents=[parent],
        shrink=shrink,
        anchor=anchor,
        panchor=panchor,
        fraction=fraction,
        aspect=aspect0,
        pad=pad)

    return cax, kwargs

# === NexusCore/openenv\Lib\site-packages\numpy\f2py\cfuncs.py ===
"""
C declarations, CPP macros, and C functions for f2py2e.
Only required declarations/macros/functions will be used.

Copyright 1999 -- 2011 Pearu Peterson all rights reserved.
Copyright 2011 -- present NumPy Developers.
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
"""
import copy
import sys

from . import __version__

f2py_version = __version__.version


def errmess(s: str) -> None:
    """
    Write an error message to stderr.

    This indirection is needed because sys.stderr might not always be available (see #26862).
    """
    if sys.stderr is not None:
        sys.stderr.write(s)

##################### Definitions ##################


outneeds = {'includes0': [], 'includes': [], 'typedefs': [], 'typedefs_generated': [],
            'userincludes': [],
            'cppmacros': [], 'cfuncs': [], 'callbacks': [], 'f90modhooks': [],
            'commonhooks': []}
needs = {}
includes0 = {'includes0': '/*need_includes0*/'}
includes = {'includes': '/*need_includes*/'}
userincludes = {'userincludes': '/*need_userincludes*/'}
typedefs = {'typedefs': '/*need_typedefs*/'}
typedefs_generated = {'typedefs_generated': '/*need_typedefs_generated*/'}
cppmacros = {'cppmacros': '/*need_cppmacros*/'}
cfuncs = {'cfuncs': '/*need_cfuncs*/'}
callbacks = {'callbacks': '/*need_callbacks*/'}
f90modhooks = {'f90modhooks': '/*need_f90modhooks*/',
               'initf90modhooksstatic': '/*initf90modhooksstatic*/',
               'initf90modhooksdynamic': '/*initf90modhooksdynamic*/',
               }
commonhooks = {'commonhooks': '/*need_commonhooks*/',
               'initcommonhooks': '/*need_initcommonhooks*/',
               }

############ Includes ###################

includes0['math.h'] = '#include <math.h>'
includes0['string.h'] = '#include <string.h>'
includes0['setjmp.h'] = '#include <setjmp.h>'

includes['arrayobject.h'] = '''#define PY_ARRAY_UNIQUE_SYMBOL PyArray_API
#include "arrayobject.h"'''
includes['npy_math.h'] = '#include "numpy/npy_math.h"'

includes['arrayobject.h'] = '#include "fortranobject.h"'
includes['stdarg.h'] = '#include <stdarg.h>'

############# Type definitions ###############

typedefs['unsigned_char'] = 'typedef unsigned char unsigned_char;'
typedefs['unsigned_short'] = 'typedef unsigned short unsigned_short;'
typedefs['unsigned_long'] = 'typedef unsigned long unsigned_long;'
typedefs['signed_char'] = 'typedef signed char signed_char;'
typedefs['long_long'] = """
#if defined(NPY_OS_WIN32)
typedef __int64 long_long;
#else
typedef long long long_long;
typedef unsigned long long unsigned_long_long;
#endif
"""
typedefs['unsigned_long_long'] = """
#if defined(NPY_OS_WIN32)
typedef __uint64 long_long;
#else
typedef unsigned long long unsigned_long_long;
#endif
"""
typedefs['long_double'] = """
#ifndef _LONG_DOUBLE
typedef long double long_double;
#endif
"""
typedefs[
    'complex_long_double'] = 'typedef struct {long double r,i;} complex_long_double;'
typedefs['complex_float'] = 'typedef struct {float r,i;} complex_float;'
typedefs['complex_double'] = 'typedef struct {double r,i;} complex_double;'
typedefs['string'] = """typedef char * string;"""
typedefs['character'] = """typedef char character;"""


############### CPP macros ####################
cppmacros['CFUNCSMESS'] = """
#ifdef DEBUGCFUNCS
#define CFUNCSMESS(mess) fprintf(stderr,\"debug-capi:\"mess);
#define CFUNCSMESSPY(mess,obj) CFUNCSMESS(mess) \\
    PyObject_Print((PyObject *)obj,stderr,Py_PRINT_RAW);\\
    fprintf(stderr,\"\\n\");
#else
#define CFUNCSMESS(mess)
#define CFUNCSMESSPY(mess,obj)
#endif
"""
cppmacros['F_FUNC'] = """
#if defined(PREPEND_FORTRAN)
#if defined(NO_APPEND_FORTRAN)
#if defined(UPPERCASE_FORTRAN)
#define F_FUNC(f,F) _##F
#else
#define F_FUNC(f,F) _##f
#endif
#else
#if defined(UPPERCASE_FORTRAN)
#define F_FUNC(f,F) _##F##_
#else
#define F_FUNC(f,F) _##f##_
#endif
#endif
#else
#if defined(NO_APPEND_FORTRAN)
#if defined(UPPERCASE_FORTRAN)
#define F_FUNC(f,F) F
#else
#define F_FUNC(f,F) f
#endif
#else
#if defined(UPPERCASE_FORTRAN)
#define F_FUNC(f,F) F##_
#else
#define F_FUNC(f,F) f##_
#endif
#endif
#endif
#if defined(UNDERSCORE_G77)
#define F_FUNC_US(f,F) F_FUNC(f##_,F##_)
#else
#define F_FUNC_US(f,F) F_FUNC(f,F)
#endif
"""
cppmacros['F_WRAPPEDFUNC'] = """
#if defined(PREPEND_FORTRAN)
#if defined(NO_APPEND_FORTRAN)
#if defined(UPPERCASE_FORTRAN)
#define F_WRAPPEDFUNC(f,F) _F2PYWRAP##F
#else
#define F_WRAPPEDFUNC(f,F) _f2pywrap##f
#endif
#else
#if defined(UPPERCASE_FORTRAN)
#define F_WRAPPEDFUNC(f,F) _F2PYWRAP##F##_
#else
#define F_WRAPPEDFUNC(f,F) _f2pywrap##f##_
#endif
#endif
#else
#if defined(NO_APPEND_FORTRAN)
#if defined(UPPERCASE_FORTRAN)
#define F_WRAPPEDFUNC(f,F) F2PYWRAP##F
#else
#define F_WRAPPEDFUNC(f,F) f2pywrap##f
#endif
#else
#if defined(UPPERCASE_FORTRAN)
#define F_WRAPPEDFUNC(f,F) F2PYWRAP##F##_
#else
#define F_WRAPPEDFUNC(f,F) f2pywrap##f##_
#endif
#endif
#endif
#if defined(UNDERSCORE_G77)
#define F_WRAPPEDFUNC_US(f,F) F_WRAPPEDFUNC(f##_,F##_)
#else
#define F_WRAPPEDFUNC_US(f,F) F_WRAPPEDFUNC(f,F)
#endif
"""
cppmacros['F_MODFUNC'] = """
#if defined(F90MOD2CCONV1) /*E.g. Compaq Fortran */
#if defined(NO_APPEND_FORTRAN)
#define F_MODFUNCNAME(m,f) $ ## m ## $ ## f
#else
#define F_MODFUNCNAME(m,f) $ ## m ## $ ## f ## _
#endif
#endif

#if defined(F90MOD2CCONV2) /*E.g. IBM XL Fortran, not tested though */
#if defined(NO_APPEND_FORTRAN)
#define F_MODFUNCNAME(m,f)  __ ## m ## _MOD_ ## f
#else
#define F_MODFUNCNAME(m,f)  __ ## m ## _MOD_ ## f ## _
#endif
#endif

#if defined(F90MOD2CCONV3) /*E.g. MIPSPro Compilers */
#if defined(NO_APPEND_FORTRAN)
#define F_MODFUNCNAME(m,f)  f ## .in. ## m
#else
#define F_MODFUNCNAME(m,f)  f ## .in. ## m ## _
#endif
#endif
/*
#if defined(UPPERCASE_FORTRAN)
#define F_MODFUNC(m,M,f,F) F_MODFUNCNAME(M,F)
#else
#define F_MODFUNC(m,M,f,F) F_MODFUNCNAME(m,f)
#endif
*/

#define F_MODFUNC(m,f) (*(f2pymodstruct##m##.##f))
"""
cppmacros['SWAPUNSAFE'] = """
#define SWAP(a,b) (size_t)(a) = ((size_t)(a) ^ (size_t)(b));\\
 (size_t)(b) = ((size_t)(a) ^ (size_t)(b));\\
 (size_t)(a) = ((size_t)(a) ^ (size_t)(b))
"""
cppmacros['SWAP'] = """
#define SWAP(a,b,t) {\\
    t *c;\\
    c = a;\\
    a = b;\\
    b = c;}
"""
# cppmacros['ISCONTIGUOUS']='#define ISCONTIGUOUS(m) (PyArray_FLAGS(m) &
# NPY_ARRAY_C_CONTIGUOUS)'
cppmacros['PRINTPYOBJERR'] = """
#define PRINTPYOBJERR(obj)\\
    fprintf(stderr,\"#modulename#.error is related to \");\\
    PyObject_Print((PyObject *)obj,stderr,Py_PRINT_RAW);\\
    fprintf(stderr,\"\\n\");
"""
cppmacros['MINMAX'] = """
#ifndef max
#define max(a,b) ((a > b) ? (a) : (b))
#endif
#ifndef min
#define min(a,b) ((a < b) ? (a) : (b))
#endif
#ifndef MAX
#define MAX(a,b) ((a > b) ? (a) : (b))
#endif
#ifndef MIN
#define MIN(a,b) ((a < b) ? (a) : (b))
#endif
"""
cppmacros['len..'] = """
/* See fortranobject.h for definitions. The macros here are provided for BC. */
#define rank f2py_rank
#define shape f2py_shape
#define fshape f2py_shape
#define len f2py_len
#define flen f2py_flen
#define slen f2py_slen
#define size f2py_size
"""
cppmacros['pyobj_from_char1'] = r"""
#define pyobj_from_char1(v) (PyLong_FromLong(v))
"""
cppmacros['pyobj_from_short1'] = r"""
#define pyobj_from_short1(v) (PyLong_FromLong(v))
"""
needs['pyobj_from_int1'] = ['signed_char']
cppmacros['pyobj_from_int1'] = r"""
#define pyobj_from_int1(v) (PyLong_FromLong(v))
"""
cppmacros['pyobj_from_long1'] = r"""
#define pyobj_from_long1(v) (PyLong_FromLong(v))
"""
needs['pyobj_from_long_long1'] = ['long_long']
cppmacros['pyobj_from_long_long1'] = """
#ifdef HAVE_LONG_LONG
#define pyobj_from_long_long1(v) (PyLong_FromLongLong(v))
#else
#warning HAVE_LONG_LONG is not available. Redefining pyobj_from_long_long.
#define pyobj_from_long_long1(v) (PyLong_FromLong(v))
#endif
"""
needs['pyobj_from_long_double1'] = ['long_double']
cppmacros['pyobj_from_long_double1'] = """
#define pyobj_from_long_double1(v) (PyFloat_FromDouble(v))"""
cppmacros['pyobj_from_double1'] = """
#define pyobj_from_double1(v) (PyFloat_FromDouble(v))"""
cppmacros['pyobj_from_float1'] = """
#define pyobj_from_float1(v) (PyFloat_FromDouble(v))"""
needs['pyobj_from_complex_long_double1'] = ['complex_long_double']
cppmacros['pyobj_from_complex_long_double1'] = """
#define pyobj_from_complex_long_double1(v) (PyComplex_FromDoubles(v.r,v.i))"""
needs['pyobj_from_complex_double1'] = ['complex_double']
cppmacros['pyobj_from_complex_double1'] = """
#define pyobj_from_complex_double1(v) (PyComplex_FromDoubles(v.r,v.i))"""
needs['pyobj_from_complex_float1'] = ['complex_float']
cppmacros['pyobj_from_complex_float1'] = """
#define pyobj_from_complex_float1(v) (PyComplex_FromDoubles(v.r,v.i))"""
needs['pyobj_from_string1'] = ['string']
cppmacros['pyobj_from_string1'] = """
#define pyobj_from_string1(v) (PyUnicode_FromString((char *)v))"""
needs['pyobj_from_string1size'] = ['string']
cppmacros['pyobj_from_string1size'] = """
#define pyobj_from_string1size(v,len) (PyUnicode_FromStringAndSize((char *)v, len))"""
needs['TRYPYARRAYTEMPLATE'] = ['PRINTPYOBJERR']
cppmacros['TRYPYARRAYTEMPLATE'] = """
/* New SciPy */
#define TRYPYARRAYTEMPLATECHAR case NPY_STRING: *(char *)(PyArray_DATA(arr))=*v; break;
#define TRYPYARRAYTEMPLATELONG case NPY_LONG: *(long *)(PyArray_DATA(arr))=*v; break;
#define TRYPYARRAYTEMPLATEOBJECT case NPY_OBJECT: PyArray_SETITEM(arr,PyArray_DATA(arr),pyobj_from_ ## ctype ## 1(*v)); break;

#define TRYPYARRAYTEMPLATE(ctype,typecode) \\
        PyArrayObject *arr = NULL;\\
        if (!obj) return -2;\\
        if (!PyArray_Check(obj)) return -1;\\
        if (!(arr=(PyArrayObject *)obj)) {fprintf(stderr,\"TRYPYARRAYTEMPLATE:\");PRINTPYOBJERR(obj);return 0;}\\
        if (PyArray_DESCR(arr)->type==typecode)  {*(ctype *)(PyArray_DATA(arr))=*v; return 1;}\\
        switch (PyArray_TYPE(arr)) {\\
                case NPY_DOUBLE: *(npy_double *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_INT: *(npy_int *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_LONG: *(npy_long *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_FLOAT: *(npy_float *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_CDOUBLE: *(npy_double *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_CFLOAT: *(npy_float *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_BOOL: *(npy_bool *)(PyArray_DATA(arr))=(*v!=0); break;\\
                case NPY_UBYTE: *(npy_ubyte *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_BYTE: *(npy_byte *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_SHORT: *(npy_short *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_USHORT: *(npy_ushort *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_UINT: *(npy_uint *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_ULONG: *(npy_ulong *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_LONGLONG: *(npy_longlong *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_ULONGLONG: *(npy_ulonglong *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_LONGDOUBLE: *(npy_longdouble *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_CLONGDOUBLE: *(npy_longdouble *)(PyArray_DATA(arr))=*v; break;\\
                case NPY_OBJECT: PyArray_SETITEM(arr, PyArray_DATA(arr), pyobj_from_ ## ctype ## 1(*v)); break;\\
        default: return -2;\\
        };\\
        return 1
"""

needs['TRYCOMPLEXPYARRAYTEMPLATE'] = ['PRINTPYOBJERR']
cppmacros['TRYCOMPLEXPYARRAYTEMPLATE'] = """
#define TRYCOMPLEXPYARRAYTEMPLATEOBJECT case NPY_OBJECT: PyArray_SETITEM(arr, PyArray_DATA(arr), pyobj_from_complex_ ## ctype ## 1((*v))); break;
#define TRYCOMPLEXPYARRAYTEMPLATE(ctype,typecode)\\
        PyArrayObject *arr = NULL;\\
        if (!obj) return -2;\\
        if (!PyArray_Check(obj)) return -1;\\
        if (!(arr=(PyArrayObject *)obj)) {fprintf(stderr,\"TRYCOMPLEXPYARRAYTEMPLATE:\");PRINTPYOBJERR(obj);return 0;}\\
        if (PyArray_DESCR(arr)->type==typecode) {\\
            *(ctype *)(PyArray_DATA(arr))=(*v).r;\\
            *(ctype *)(PyArray_DATA(arr)+sizeof(ctype))=(*v).i;\\
            return 1;\\
        }\\
        switch (PyArray_TYPE(arr)) {\\
                case NPY_CDOUBLE: *(npy_double *)(PyArray_DATA(arr))=(*v).r;\\
                                  *(npy_double *)(PyArray_DATA(arr)+sizeof(npy_double))=(*v).i;\\
                                  break;\\
                case NPY_CFLOAT: *(npy_float *)(PyArray_DATA(arr))=(*v).r;\\
                                 *(npy_float *)(PyArray_DATA(arr)+sizeof(npy_float))=(*v).i;\\
                                 break;\\
                case NPY_DOUBLE: *(npy_double *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_LONG: *(npy_long *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_FLOAT: *(npy_float *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_INT: *(npy_int *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_SHORT: *(npy_short *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_UBYTE: *(npy_ubyte *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_BYTE: *(npy_byte *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_BOOL: *(npy_bool *)(PyArray_DATA(arr))=((*v).r!=0 && (*v).i!=0); break;\\
                case NPY_USHORT: *(npy_ushort *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_UINT: *(npy_uint *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_ULONG: *(npy_ulong *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_LONGLONG: *(npy_longlong *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_ULONGLONG: *(npy_ulonglong *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_LONGDOUBLE: *(npy_longdouble *)(PyArray_DATA(arr))=(*v).r; break;\\
                case NPY_CLONGDOUBLE: *(npy_longdouble *)(PyArray_DATA(arr))=(*v).r;\\
                                      *(npy_longdouble *)(PyArray_DATA(arr)+sizeof(npy_longdouble))=(*v).i;\\
                                      break;\\
                case NPY_OBJECT: PyArray_SETITEM(arr, PyArray_DATA(arr), pyobj_from_complex_ ## ctype ## 1((*v))); break;\\
                default: return -2;\\
        };\\
        return -1;
"""
# cppmacros['NUMFROMARROBJ']="""
# define NUMFROMARROBJ(typenum,ctype) \\
#     if (PyArray_Check(obj)) arr = (PyArrayObject *)obj;\\
#     else arr = (PyArrayObject *)PyArray_ContiguousFromObject(obj,typenum,0,0);\\
#     if (arr) {\\
#         if (PyArray_TYPE(arr)==NPY_OBJECT) {\\
#             if (!ctype ## _from_pyobj(v,(PyArray_DESCR(arr)->getitem)(PyArray_DATA(arr)),\"\"))\\
#             goto capi_fail;\\
#         } else {\\
#             (PyArray_DESCR(arr)->cast[typenum])(PyArray_DATA(arr),1,(char*)v,1,1);\\
#         }\\
#         if ((PyObject *)arr != obj) { Py_DECREF(arr); }\\
#         return 1;\\
#     }
# """
# XXX: Note that CNUMFROMARROBJ is identical with NUMFROMARROBJ
# cppmacros['CNUMFROMARROBJ']="""
# define CNUMFROMARROBJ(typenum,ctype) \\
#     if (PyArray_Check(obj)) arr = (PyArrayObject *)obj;\\
#     else arr = (PyArrayObject *)PyArray_ContiguousFromObject(obj,typenum,0,0);\\
#     if (arr) {\\
#         if (PyArray_TYPE(arr)==NPY_OBJECT) {\\
#             if (!ctype ## _from_pyobj(v,(PyArray_DESCR(arr)->getitem)(PyArray_DATA(arr)),\"\"))\\
#             goto capi_fail;\\
#         } else {\\
#             (PyArray_DESCR(arr)->cast[typenum])((void *)(PyArray_DATA(arr)),1,(void *)(v),1,1);\\
#         }\\
#         if ((PyObject *)arr != obj) { Py_DECREF(arr); }\\
#         return 1;\\
#     }
# """


needs['GETSTRFROMPYTUPLE'] = ['STRINGCOPYN', 'PRINTPYOBJERR']
cppmacros['GETSTRFROMPYTUPLE'] = """
#define GETSTRFROMPYTUPLE(tuple,index,str,len) {\\
        PyObject *rv_cb_str = PyTuple_GetItem((tuple),(index));\\
        if (rv_cb_str == NULL)\\
            goto capi_fail;\\
        if (PyBytes_Check(rv_cb_str)) {\\
            str[len-1]='\\0';\\
            STRINGCOPYN((str),PyBytes_AS_STRING((PyBytesObject*)rv_cb_str),(len));\\
        } else {\\
            PRINTPYOBJERR(rv_cb_str);\\
            PyErr_SetString(#modulename#_error,\"string object expected\");\\
            goto capi_fail;\\
        }\\
    }
"""
cppmacros['GETSCALARFROMPYTUPLE'] = """
#define GETSCALARFROMPYTUPLE(tuple,index,var,ctype,mess) {\\
        if ((capi_tmp = PyTuple_GetItem((tuple),(index)))==NULL) goto capi_fail;\\
        if (!(ctype ## _from_pyobj((var),capi_tmp,mess)))\\
            goto capi_fail;\\
    }
"""

cppmacros['FAILNULL'] = """\
#define FAILNULL(p) do {                                            \\
    if ((p) == NULL) {                                              \\
        PyErr_SetString(PyExc_MemoryError, "NULL pointer found");   \\
        goto capi_fail;                                             \\
    }                                                               \\
} while (0)
"""
needs['MEMCOPY'] = ['string.h', 'FAILNULL']
cppmacros['MEMCOPY'] = """
#define MEMCOPY(to,from,n)\\
    do { FAILNULL(to); FAILNULL(from); (void)memcpy(to,from,n); } while (0)
"""
cppmacros['STRINGMALLOC'] = """
#define STRINGMALLOC(str,len)\\
    if ((str = (string)malloc(len+1)) == NULL) {\\
        PyErr_SetString(PyExc_MemoryError, \"out of memory\");\\
        goto capi_fail;\\
    } else {\\
        (str)[len] = '\\0';\\
    }
"""
cppmacros['STRINGFREE'] = """
#define STRINGFREE(str) do {if (!(str == NULL)) free(str);} while (0)
"""
needs['STRINGPADN'] = ['string.h']
cppmacros['STRINGPADN'] = """
/*
STRINGPADN replaces null values with padding values from the right.

`to` must have size of at least N bytes.

If the `to[N-1]` has null value, then replace it and all the
preceding, nulls with the given padding.

STRINGPADN(to, N, PADDING, NULLVALUE) is an inverse operation.
*/
#define STRINGPADN(to, N, NULLVALUE, PADDING)                   \\
    do {                                                        \\
        int _m = (N);                                           \\
        char *_to = (to);                                       \\
        for (_m -= 1; _m >= 0 && _to[_m] == NULLVALUE; _m--) {  \\
             _to[_m] = PADDING;                                 \\
        }                                                       \\
    } while (0)
"""
needs['STRINGCOPYN'] = ['string.h', 'FAILNULL']
cppmacros['STRINGCOPYN'] = """
/*
STRINGCOPYN copies N bytes.

`to` and `from` buffers must have sizes of at least N bytes.
*/
#define STRINGCOPYN(to,from,N)                                  \\
    do {                                                        \\
        int _m = (N);                                           \\
        char *_to = (to);                                       \\
        char *_from = (from);                                   \\
        FAILNULL(_to); FAILNULL(_from);                         \\
        (void)strncpy(_to, _from, _m);             \\
    } while (0)
"""
needs['STRINGCOPY'] = ['string.h', 'FAILNULL']
cppmacros['STRINGCOPY'] = """
#define STRINGCOPY(to,from)\\
    do { FAILNULL(to); FAILNULL(from); (void)strcpy(to,from); } while (0)
"""
cppmacros['CHECKGENERIC'] = """
#define CHECKGENERIC(check,tcheck,name) \\
    if (!(check)) {\\
        PyErr_SetString(#modulename#_error,\"(\"tcheck\") failed for \"name);\\
        /*goto capi_fail;*/\\
    } else """
cppmacros['CHECKARRAY'] = """
#define CHECKARRAY(check,tcheck,name) \\
    if (!(check)) {\\
        PyErr_SetString(#modulename#_error,\"(\"tcheck\") failed for \"name);\\
        /*goto capi_fail;*/\\
    } else """
cppmacros['CHECKSTRING'] = """
#define CHECKSTRING(check,tcheck,name,show,var)\\
    if (!(check)) {\\
        char errstring[256];\\
        sprintf(errstring, \"%s: \"show, \"(\"tcheck\") failed for \"name, slen(var), var);\\
        PyErr_SetString(#modulename#_error, errstring);\\
        /*goto capi_fail;*/\\
    } else """
cppmacros['CHECKSCALAR'] = """
#define CHECKSCALAR(check,tcheck,name,show,var)\\
    if (!(check)) {\\
        char errstring[256];\\
        sprintf(errstring, \"%s: \"show, \"(\"tcheck\") failed for \"name, var);\\
        PyErr_SetString(#modulename#_error,errstring);\\
        /*goto capi_fail;*/\\
    } else """
# cppmacros['CHECKDIMS']="""
# define CHECKDIMS(dims,rank) \\
#     for (int i=0;i<(rank);i++)\\
#         if (dims[i]<0) {\\
#             fprintf(stderr,\"Unspecified array argument requires a complete dimension specification.\\n\");\\
#             goto capi_fail;\\
#         }
# """
cppmacros[
    'ARRSIZE'] = '#define ARRSIZE(dims,rank) (_PyArray_multiply_list(dims,rank))'
cppmacros['OLDPYNUM'] = """
#ifdef OLDPYNUM
#error You need to install NumPy version 0.13 or higher. See https://scipy.org/install.html
#endif
"""

# Defining the correct value to indicate thread-local storage in C without
# running a compile-time check (which we have no control over in generated
# code used outside of NumPy) is hard. Therefore we support overriding this
# via an external define - the f2py-using package can then use the same
# compile-time checks as we use for `NPY_TLS` when building NumPy (see
# scipy#21860 for an example of that).
#
# __STDC_NO_THREADS__ should not be coupled to the availability of _Thread_local.
# In case we get a bug report, guard it with __STDC_NO_THREADS__ after all.
#
# `thread_local` has become a keyword in C23, but don't try to use that yet
# (too new, doing so while C23 support is preliminary will likely cause more
#  problems than it solves).
#
# Note: do not try to use `threads.h`, its availability is very low
# *and* threads.h isn't actually used where `F2PY_THREAD_LOCAL_DECL` is
# in the generated code. See gh-27718 for more details.
cppmacros["F2PY_THREAD_LOCAL_DECL"] = """
#ifndef F2PY_THREAD_LOCAL_DECL
#if defined(_MSC_VER)
#define F2PY_THREAD_LOCAL_DECL __declspec(thread)
#elif defined(NPY_OS_MINGW)
#define F2PY_THREAD_LOCAL_DECL __thread
#elif defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 201112L)
#define F2PY_THREAD_LOCAL_DECL _Thread_local
#elif defined(__GNUC__) \\
      && (__GNUC__ > 4 || (__GNUC__ == 4 && (__GNUC_MINOR__ >= 4)))
#define F2PY_THREAD_LOCAL_DECL __thread
#endif
#endif
"""
################# C functions ###############

cfuncs['calcarrindex'] = """
static int calcarrindex(int *i,PyArrayObject *arr) {
    int k,ii = i[0];
    for (k=1; k < PyArray_NDIM(arr); k++)
        ii += (ii*(PyArray_DIM(arr,k) - 1)+i[k]); /* assuming contiguous arr */
    return ii;
}"""
cfuncs['calcarrindextr'] = """
static int calcarrindextr(int *i,PyArrayObject *arr) {
    int k,ii = i[PyArray_NDIM(arr)-1];
    for (k=1; k < PyArray_NDIM(arr); k++)
        ii += (ii*(PyArray_DIM(arr,PyArray_NDIM(arr)-k-1) - 1)+i[PyArray_NDIM(arr)-k-1]); /* assuming contiguous arr */
    return ii;
}"""
cfuncs['forcomb'] = """
struct ForcombCache { int nd;npy_intp *d;int *i,*i_tr,tr; };
static int initforcomb(struct ForcombCache *cache, npy_intp *dims,int nd,int tr) {
  int k;
  if (dims==NULL) return 0;
  if (nd<0) return 0;
  cache->nd = nd;
  cache->d = dims;
  cache->tr = tr;

  cache->i = (int *)malloc(sizeof(int)*nd);
  if (cache->i==NULL) return 0;
  cache->i_tr = (int *)malloc(sizeof(int)*nd);
  if (cache->i_tr==NULL) {free(cache->i); return 0;};

  for (k=1;k<nd;k++) {
    cache->i[k] = cache->i_tr[nd-k-1] = 0;
  }
  cache->i[0] = cache->i_tr[nd-1] = -1;
  return 1;
}
static int *nextforcomb(struct ForcombCache *cache) {
  if (cache==NULL) return NULL;
  int j,*i,*i_tr,k;
  int nd=cache->nd;
  if ((i=cache->i) == NULL) return NULL;
  if ((i_tr=cache->i_tr) == NULL) return NULL;
  if (cache->d == NULL) return NULL;
  i[0]++;
  if (i[0]==cache->d[0]) {
    j=1;
    while ((j<nd) && (i[j]==cache->d[j]-1)) j++;
    if (j==nd) {
      free(i);
      free(i_tr);
      return NULL;
    }
    for (k=0;k<j;k++) i[k] = i_tr[nd-k-1] = 0;
    i[j]++;
    i_tr[nd-j-1]++;
  } else
    i_tr[nd-1]++;
  if (cache->tr) return i_tr;
  return i;
}"""
needs['try_pyarr_from_string'] = ['STRINGCOPYN', 'PRINTPYOBJERR', 'string']
cfuncs['try_pyarr_from_string'] = """
/*
  try_pyarr_from_string copies str[:len(obj)] to the data of an `ndarray`.

  If obj is an `ndarray`, it is assumed to be contiguous.

  If the specified len==-1, str must be null-terminated.
*/
static int try_pyarr_from_string(PyObject *obj,
                                 const string str, const int len) {
#ifdef DEBUGCFUNCS
fprintf(stderr, "try_pyarr_from_string(str='%s', len=%d, obj=%p)\\n",
        (char*)str,len, obj);
#endif
    if (!obj) return -2; /* Object missing */
    if (obj == Py_None) return -1; /* None */
    if (!PyArray_Check(obj)) goto capi_fail; /* not an ndarray */
    if (PyArray_Check(obj)) {
        PyArrayObject *arr = (PyArrayObject *)obj;
        assert(ISCONTIGUOUS(arr));
        string buf = PyArray_DATA(arr);
        npy_intp n = len;
        if (n == -1) {
            /* Assuming null-terminated str. */
            n = strlen(str);
        }
        if (n > PyArray_NBYTES(arr)) {
            n = PyArray_NBYTES(arr);
        }
        STRINGCOPYN(buf, str, n);
        return 1;
    }
capi_fail:
    PRINTPYOBJERR(obj);
    PyErr_SetString(#modulename#_error, \"try_pyarr_from_string failed\");
    return 0;
}
"""
needs['string_from_pyobj'] = ['string', 'STRINGMALLOC', 'STRINGCOPYN']
cfuncs['string_from_pyobj'] = """
/*
  Create a new string buffer `str` of at most length `len` from a
  Python string-like object `obj`.

  The string buffer has given size (len) or the size of inistr when len==-1.

  The string buffer is padded with blanks: in Fortran, trailing blanks
  are insignificant contrary to C nulls.
 */
static int
string_from_pyobj(string *str, int *len, const string inistr, PyObject *obj,
                  const char *errmess)
{
    PyObject *tmp = NULL;
    string buf = NULL;
    npy_intp n = -1;
#ifdef DEBUGCFUNCS
fprintf(stderr,\"string_from_pyobj(str='%s',len=%d,inistr='%s',obj=%p)\\n\",
               (char*)str, *len, (char *)inistr, obj);
#endif
    if (obj == Py_None) {
        n = strlen(inistr);
        buf = inistr;
    }
    else if (PyArray_Check(obj)) {
        PyArrayObject *arr = (PyArrayObject *)obj;
        if (!ISCONTIGUOUS(arr)) {
            PyErr_SetString(PyExc_ValueError,
                            \"array object is non-contiguous.\");
            goto capi_fail;
        }
        n = PyArray_NBYTES(arr);
        buf = PyArray_DATA(arr);
        n = strnlen(buf, n);
    }
    else {
        if (PyBytes_Check(obj)) {
            tmp = obj;
            Py_INCREF(tmp);
        }
        else if (PyUnicode_Check(obj)) {
            tmp = PyUnicode_AsASCIIString(obj);
        }
        else {
            PyObject *tmp2;
            tmp2 = PyObject_Str(obj);
            if (tmp2) {
                tmp = PyUnicode_AsASCIIString(tmp2);
                Py_DECREF(tmp2);
            }
            else {
                tmp = NULL;
            }
        }
        if (tmp == NULL) goto capi_fail;
        n = PyBytes_GET_SIZE(tmp);
        buf = PyBytes_AS_STRING(tmp);
    }
    if (*len == -1) {
        /* TODO: change the type of `len` so that we can remove this */
        if (n > NPY_MAX_INT) {
            PyErr_SetString(PyExc_OverflowError,
                            "object too large for a 32-bit int");
            goto capi_fail;
        }
        *len = n;
    }
    else if (*len < n) {
        /* discard the last (len-n) bytes of input buf */
        n = *len;
    }
    if (n < 0 || *len < 0 || buf == NULL) {
        goto capi_fail;
    }
    STRINGMALLOC(*str, *len);  // *str is allocated with size (*len + 1)
    if (n < *len) {
        /*
          Pad fixed-width string with nulls. The caller will replace
          nulls with blanks when the corresponding argument is not
          intent(c).
        */
        memset(*str + n, '\\0', *len - n);
    }
    STRINGCOPYN(*str, buf, n);
    Py_XDECREF(tmp);
    return 1;
capi_fail:
    Py_XDECREF(tmp);
    {
        PyObject* err = PyErr_Occurred();
        if (err == NULL) {
            err = #modulename#_error;
        }
        PyErr_SetString(err, errmess);
    }
    return 0;
}
"""

cfuncs['character_from_pyobj'] = """
static int
character_from_pyobj(character* v, PyObject *obj, const char *errmess) {
    if (PyBytes_Check(obj)) {
        /* empty bytes has trailing null, so dereferencing is always safe */
        *v = PyBytes_AS_STRING(obj)[0];
        return 1;
    } else if (PyUnicode_Check(obj)) {
        PyObject* tmp = PyUnicode_AsASCIIString(obj);
        if (tmp != NULL) {
            *v = PyBytes_AS_STRING(tmp)[0];
            Py_DECREF(tmp);
            return 1;
        }
    } else if (PyArray_Check(obj)) {
        PyArrayObject* arr = (PyArrayObject*)obj;
        if (F2PY_ARRAY_IS_CHARACTER_COMPATIBLE(arr)) {
            *v = PyArray_BYTES(arr)[0];
            return 1;
        } else if (F2PY_IS_UNICODE_ARRAY(arr)) {
            // TODO: update when numpy will support 1-byte and
            // 2-byte unicode dtypes
            PyObject* tmp = PyUnicode_FromKindAndData(
                              PyUnicode_4BYTE_KIND,
                              PyArray_BYTES(arr),
                              (PyArray_NBYTES(arr)>0?1:0));
            if (tmp != NULL) {
                if (character_from_pyobj(v, tmp, errmess)) {
                    Py_DECREF(tmp);
                    return 1;
                }
                Py_DECREF(tmp);
            }
        }
    } else if (PySequence_Check(obj)) {
        PyObject* tmp = PySequence_GetItem(obj,0);
        if (tmp != NULL) {
            if (character_from_pyobj(v, tmp, errmess)) {
                Py_DECREF(tmp);
                return 1;
            }
            Py_DECREF(tmp);
        }
    }
    {
        /* TODO: This error (and most other) error handling needs cleaning. */
        char mess[F2PY_MESSAGE_BUFFER_SIZE];
        strcpy(mess, errmess);
        PyObject* err = PyErr_Occurred();
        if (err == NULL) {
            err = PyExc_TypeError;
            Py_INCREF(err);
        }
        else {
            Py_INCREF(err);
            PyErr_Clear();
        }
        sprintf(mess + strlen(mess),
                " -- expected str|bytes|sequence-of-str-or-bytes, got ");
        f2py_describe(obj, mess + strlen(mess));
        PyErr_SetString(err, mess);
        Py_DECREF(err);
    }
    return 0;
}
"""

# TODO: These should be dynamically generated, too many mapped to int things,
# see note in _isocbind.py
needs['char_from_pyobj'] = ['int_from_pyobj']
cfuncs['char_from_pyobj'] = """
static int
char_from_pyobj(char* v, PyObject *obj, const char *errmess) {
    int i = 0;
    if (int_from_pyobj(&i, obj, errmess)) {
        *v = (char)i;
        return 1;
    }
    return 0;
}
"""


needs['signed_char_from_pyobj'] = ['int_from_pyobj', 'signed_char']
cfuncs['signed_char_from_pyobj'] = """
static int
signed_char_from_pyobj(signed_char* v, PyObject *obj, const char *errmess) {
    int i = 0;
    if (int_from_pyobj(&i, obj, errmess)) {
        *v = (signed_char)i;
        return 1;
    }
    return 0;
}
"""


needs['short_from_pyobj'] = ['int_from_pyobj']
cfuncs['short_from_pyobj'] = """
static int
short_from_pyobj(short* v, PyObject *obj, const char *errmess) {
    int i = 0;
    if (int_from_pyobj(&i, obj, errmess)) {
        *v = (short)i;
        return 1;
    }
    return 0;
}
"""


cfuncs['int_from_pyobj'] = """
static int
int_from_pyobj(int* v, PyObject *obj, const char *errmess)
{
    PyObject* tmp = NULL;

    if (PyLong_Check(obj)) {
        *v = Npy__PyLong_AsInt(obj);
        return !(*v == -1 && PyErr_Occurred());
    }

    tmp = PyNumber_Long(obj);
    if (tmp) {
        *v = Npy__PyLong_AsInt(tmp);
        Py_DECREF(tmp);
        return !(*v == -1 && PyErr_Occurred());
    }

    if (PyComplex_Check(obj)) {
        PyErr_Clear();
        tmp = PyObject_GetAttrString(obj,\"real\");
    }
    else if (PyBytes_Check(obj) || PyUnicode_Check(obj)) {
        /*pass*/;
    }
    else if (PySequence_Check(obj)) {
        PyErr_Clear();
        tmp = PySequence_GetItem(obj, 0);
    }

    if (tmp) {
        if (int_from_pyobj(v, tmp, errmess)) {
            Py_DECREF(tmp);
            return 1;
        }
        Py_DECREF(tmp);
    }

    {
        PyObject* err = PyErr_Occurred();
        if (err == NULL) {
            err = #modulename#_error;
        }
        PyErr_SetString(err, errmess);
    }
    return 0;
}
"""


cfuncs['long_from_pyobj'] = """
static int
long_from_pyobj(long* v, PyObject *obj, const char *errmess) {
    PyObject* tmp = NULL;

    if (PyLong_Check(obj)) {
        *v = PyLong_AsLong(obj);
        return !(*v == -1 && PyErr_Occurred());
    }

    tmp = PyNumber_Long(obj);
    if (tmp) {
        *v = PyLong_AsLong(tmp);
        Py_DECREF(tmp);
        return !(*v == -1 && PyErr_Occurred());
    }

    if (PyComplex_Check(obj)) {
        PyErr_Clear();
        tmp = PyObject_GetAttrString(obj,\"real\");
    }
    else if (PyBytes_Check(obj) || PyUnicode_Check(obj)) {
        /*pass*/;
    }
    else if (PySequence_Check(obj)) {
        PyErr_Clear();
        tmp = PySequence_GetItem(obj, 0);
    }

    if (tmp) {
        if (long_from_pyobj(v, tmp, errmess)) {
            Py_DECREF(tmp);
            return 1;
        }
        Py_DECREF(tmp);
    }
    {
        PyObject* err = PyErr_Occurred();
        if (err == NULL) {
            err = #modulename#_error;
        }
        PyErr_SetString(err, errmess);
    }
    return 0;
}
"""


needs['long_long_from_pyobj'] = ['long_long']
cfuncs['long_long_from_pyobj'] = """
static int
long_long_from_pyobj(long_long* v, PyObject *obj, const char *errmess)
{
    PyObject* tmp = NULL;

    if (PyLong_Check(obj)) {
        *v = PyLong_AsLongLong(obj);
        return !(*v == -1 && PyErr_Occurred());
    }

    tmp = PyNumber_Long(obj);
    if (tmp) {
        *v = PyLong_AsLongLong(tmp);
        Py_DECREF(tmp);
        return !(*v == -1 && PyErr_Occurred());
    }

    if (PyComplex_Check(obj)) {
        PyErr_Clear();
        tmp = PyObject_GetAttrString(obj,\"real\");
    }
    else if (PyBytes_Check(obj) || PyUnicode_Check(obj)) {
        /*pass*/;
    }
    else if (PySequence_Check(obj)) {
        PyErr_Clear();
        tmp = PySequence_GetItem(obj, 0);
    }

    if (tmp) {
        if (long_long_from_pyobj(v, tmp, errmess)) {
            Py_DECREF(tmp);
            return 1;
        }
        Py_DECREF(tmp);
    }
    {
        PyObject* err = PyErr_Occurred();
        if (err == NULL) {
            err = #modulename#_error;
        }
        PyErr_SetString(err,errmess);
    }
    return 0;
}
"""


needs['long_double_from_pyobj'] = ['double_from_pyobj', 'long_double']
cfuncs['long_double_from_pyobj'] = """
static int
long_double_from_pyobj(long_double* v, PyObject *obj, const char *errmess)
{
    double d=0;
    if (PyArray_CheckScalar(obj)){
        if PyArray_IsScalar(obj, LongDouble) {
            PyArray_ScalarAsCtype(obj, v);
            return 1;
        }
        else if (PyArray_Check(obj)) {
            PyArrayObject *arr = (PyArrayObject *)obj;
            if (PyArray_TYPE(arr) == NPY_LONGDOUBLE) {
                (*v) = *((npy_longdouble *)PyArray_DATA(arr));
                return 1;
            }
        }
    }
    if (double_from_pyobj(&d, obj, errmess)) {
        *v = (long_double)d;
        return 1;
    }
    return 0;
}
"""


cfuncs['double_from_pyobj'] = """
static int
double_from_pyobj(double* v, PyObject *obj, const char *errmess)
{
    PyObject* tmp = NULL;
    if (PyFloat_Check(obj)) {
        *v = PyFloat_AsDouble(obj);
        return !(*v == -1.0 && PyErr_Occurred());
    }

    tmp = PyNumber_Float(obj);
    if (tmp) {
        *v = PyFloat_AsDouble(tmp);
        Py_DECREF(tmp);
        return !(*v == -1.0 && PyErr_Occurred());
    }

    if (PyComplex_Check(obj)) {
        PyErr_Clear();
        tmp = PyObject_GetAttrString(obj,\"real\");
    }
    else if (PyBytes_Check(obj) || PyUnicode_Check(obj)) {
        /*pass*/;
    }
    else if (PySequence_Check(obj)) {
        PyErr_Clear();
        tmp = PySequence_GetItem(obj, 0);
    }

    if (tmp) {
        if (double_from_pyobj(v,tmp,errmess)) {Py_DECREF(tmp); return 1;}
        Py_DECREF(tmp);
    }
    {
        PyObject* err = PyErr_Occurred();
        if (err==NULL) err = #modulename#_error;
        PyErr_SetString(err,errmess);
    }
    return 0;
}
"""


needs['float_from_pyobj'] = ['double_from_pyobj']
cfuncs['float_from_pyobj'] = """
static int
float_from_pyobj(float* v, PyObject *obj, const char *errmess)
{
    double d=0.0;
    if (double_from_pyobj(&d,obj,errmess)) {
        *v = (float)d;
        return 1;
    }
    return 0;
}
"""


needs['complex_long_double_from_pyobj'] = ['complex_long_double', 'long_double',
                                           'complex_double_from_pyobj', 'npy_math.h']
cfuncs['complex_long_double_from_pyobj'] = """
static int
complex_long_double_from_pyobj(complex_long_double* v, PyObject *obj, const char *errmess)
{
    complex_double cd = {0.0,0.0};
    if (PyArray_CheckScalar(obj)){
        if PyArray_IsScalar(obj, CLongDouble) {
            PyArray_ScalarAsCtype(obj, v);
            return 1;
        }
        else if (PyArray_Check(obj)) {
            PyArrayObject *arr = (PyArrayObject *)obj;
            if (PyArray_TYPE(arr)==NPY_CLONGDOUBLE) {
                (*v).r = npy_creall(*(((npy_clongdouble *)PyArray_DATA(arr))));
                (*v).i = npy_cimagl(*(((npy_clongdouble *)PyArray_DATA(arr))));
                return 1;
            }
        }
    }
    if (complex_double_from_pyobj(&cd,obj,errmess)) {
        (*v).r = (long_double)cd.r;
        (*v).i = (long_double)cd.i;
        return 1;
    }
    return 0;
}
"""


needs['complex_double_from_pyobj'] = ['complex_double', 'npy_math.h']
cfuncs['complex_double_from_pyobj'] = """
static int
complex_double_from_pyobj(complex_double* v, PyObject *obj, const char *errmess) {
    Py_complex c;
    if (PyComplex_Check(obj)) {
        c = PyComplex_AsCComplex(obj);
        (*v).r = c.real;
        (*v).i = c.imag;
        return 1;
    }
    if (PyArray_IsScalar(obj, ComplexFloating)) {
        if (PyArray_IsScalar(obj, CFloat)) {
            npy_cfloat new;
            PyArray_ScalarAsCtype(obj, &new);
            (*v).r = (double)npy_crealf(new);
            (*v).i = (double)npy_cimagf(new);
        }
        else if (PyArray_IsScalar(obj, CLongDouble)) {
            npy_clongdouble new;
            PyArray_ScalarAsCtype(obj, &new);
            (*v).r = (double)npy_creall(new);
            (*v).i = (double)npy_cimagl(new);
        }
        else { /* if (PyArray_IsScalar(obj, CDouble)) */
            PyArray_ScalarAsCtype(obj, v);
        }
        return 1;
    }
    if (PyArray_CheckScalar(obj)) { /* 0-dim array or still array scalar */
        PyArrayObject *arr;
        if (PyArray_Check(obj)) {
            arr = (PyArrayObject *)PyArray_Cast((PyArrayObject *)obj, NPY_CDOUBLE);
        }
        else {
            arr = (PyArrayObject *)PyArray_FromScalar(obj, PyArray_DescrFromType(NPY_CDOUBLE));
        }
        if (arr == NULL) {
            return 0;
        }
        (*v).r = npy_creal(*(((npy_cdouble *)PyArray_DATA(arr))));
        (*v).i = npy_cimag(*(((npy_cdouble *)PyArray_DATA(arr))));
        Py_DECREF(arr);
        return 1;
    }
    /* Python does not provide PyNumber_Complex function :-( */
    (*v).i = 0.0;
    if (PyFloat_Check(obj)) {
        (*v).r = PyFloat_AsDouble(obj);
        return !((*v).r == -1.0 && PyErr_Occurred());
    }
    if (PyLong_Check(obj)) {
        (*v).r = PyLong_AsDouble(obj);
        return !((*v).r == -1.0 && PyErr_Occurred());
    }
    if (PySequence_Check(obj) && !(PyBytes_Check(obj) || PyUnicode_Check(obj))) {
        PyObject *tmp = PySequence_GetItem(obj,0);
        if (tmp) {
            if (complex_double_from_pyobj(v,tmp,errmess)) {
                Py_DECREF(tmp);
                return 1;
            }
            Py_DECREF(tmp);
        }
    }
    {
        PyObject* err = PyErr_Occurred();
        if (err==NULL)
            err = PyExc_TypeError;
        PyErr_SetString(err,errmess);
    }
    return 0;
}
"""


needs['complex_float_from_pyobj'] = [
    'complex_float', 'complex_double_from_pyobj']
cfuncs['complex_float_from_pyobj'] = """
static int
complex_float_from_pyobj(complex_float* v,PyObject *obj,const char *errmess)
{
    complex_double cd={0.0,0.0};
    if (complex_double_from_pyobj(&cd,obj,errmess)) {
        (*v).r = (float)cd.r;
        (*v).i = (float)cd.i;
        return 1;
    }
    return 0;
}
"""


cfuncs['try_pyarr_from_character'] = """
static int try_pyarr_from_character(PyObject* obj, character* v) {
    PyArrayObject *arr = (PyArrayObject*)obj;
    if (!obj) return -2;
    if (PyArray_Check(obj)) {
        if (F2PY_ARRAY_IS_CHARACTER_COMPATIBLE(arr))  {
            *(character *)(PyArray_DATA(arr)) = *v;
            return 1;
        }
    }
    {
        char mess[F2PY_MESSAGE_BUFFER_SIZE];
        PyObject* err = PyErr_Occurred();
        if (err == NULL) {
            err = PyExc_ValueError;
            strcpy(mess, "try_pyarr_from_character failed"
                         " -- expected bytes array-scalar|array, got ");
            f2py_describe(obj, mess + strlen(mess));
            PyErr_SetString(err, mess);
        }
    }
    return 0;
}
"""

needs['try_pyarr_from_char'] = ['pyobj_from_char1', 'TRYPYARRAYTEMPLATE']
cfuncs[
    'try_pyarr_from_char'] = 'static int try_pyarr_from_char(PyObject* obj,char* v) {\n    TRYPYARRAYTEMPLATE(char,\'c\');\n}\n'
needs['try_pyarr_from_signed_char'] = ['TRYPYARRAYTEMPLATE', 'unsigned_char']
cfuncs[
    'try_pyarr_from_unsigned_char'] = 'static int try_pyarr_from_unsigned_char(PyObject* obj,unsigned_char* v) {\n    TRYPYARRAYTEMPLATE(unsigned_char,\'b\');\n}\n'
needs['try_pyarr_from_signed_char'] = ['TRYPYARRAYTEMPLATE', 'signed_char']
cfuncs[
    'try_pyarr_from_signed_char'] = 'static int try_pyarr_from_signed_char(PyObject* obj,signed_char* v) {\n    TRYPYARRAYTEMPLATE(signed_char,\'1\');\n}\n'
needs['try_pyarr_from_short'] = ['pyobj_from_short1', 'TRYPYARRAYTEMPLATE']
cfuncs[
    'try_pyarr_from_short'] = 'static int try_pyarr_from_short(PyObject* obj,short* v) {\n    TRYPYARRAYTEMPLATE(short,\'s\');\n}\n'
needs['try_pyarr_from_int'] = ['pyobj_from_int1', 'TRYPYARRAYTEMPLATE']
cfuncs[
    'try_pyarr_from_int'] = 'static int try_pyarr_from_int(PyObject* obj,int* v) {\n    TRYPYARRAYTEMPLATE(int,\'i\');\n}\n'
needs['try_pyarr_from_long'] = ['pyobj_from_long1', 'TRYPYARRAYTEMPLATE']
cfuncs[
    'try_pyarr_from_long'] = 'static int try_pyarr_from_long(PyObject* obj,long* v) {\n    TRYPYARRAYTEMPLATE(long,\'l\');\n}\n'
needs['try_pyarr_from_long_long'] = [
    'pyobj_from_long_long1', 'TRYPYARRAYTEMPLATE', 'long_long']
cfuncs[
    'try_pyarr_from_long_long'] = 'static int try_pyarr_from_long_long(PyObject* obj,long_long* v) {\n    TRYPYARRAYTEMPLATE(long_long,\'L\');\n}\n'
needs['try_pyarr_from_float'] = ['pyobj_from_float1', 'TRYPYARRAYTEMPLATE']
cfuncs[
    'try_pyarr_from_float'] = 'static int try_pyarr_from_float(PyObject* obj,float* v) {\n    TRYPYARRAYTEMPLATE(float,\'f\');\n}\n'
needs['try_pyarr_from_double'] = ['pyobj_from_double1', 'TRYPYARRAYTEMPLATE']
cfuncs[
    'try_pyarr_from_double'] = 'static int try_pyarr_from_double(PyObject* obj,double* v) {\n    TRYPYARRAYTEMPLATE(double,\'d\');\n}\n'
needs['try_pyarr_from_complex_float'] = [
    'pyobj_from_complex_float1', 'TRYCOMPLEXPYARRAYTEMPLATE', 'complex_float']
cfuncs[
    'try_pyarr_from_complex_float'] = 'static int try_pyarr_from_complex_float(PyObject* obj,complex_float* v) {\n    TRYCOMPLEXPYARRAYTEMPLATE(float,\'F\');\n}\n'
needs['try_pyarr_from_complex_double'] = [
    'pyobj_from_complex_double1', 'TRYCOMPLEXPYARRAYTEMPLATE', 'complex_double']
cfuncs[
    'try_pyarr_from_complex_double'] = 'static int try_pyarr_from_complex_double(PyObject* obj,complex_double* v) {\n    TRYCOMPLEXPYARRAYTEMPLATE(double,\'D\');\n}\n'


needs['create_cb_arglist'] = ['CFUNCSMESS', 'PRINTPYOBJERR', 'MINMAX']
# create the list of arguments to be used when calling back to python
cfuncs['create_cb_arglist'] = """
static int
create_cb_arglist(PyObject* fun, PyTupleObject* xa , const int maxnofargs,
                  const int nofoptargs, int *nofargs, PyTupleObject **args,
                  const char *errmess)
{
    PyObject *tmp = NULL;
    PyObject *tmp_fun = NULL;
    Py_ssize_t tot, opt, ext, siz, i, di = 0;
    CFUNCSMESS(\"create_cb_arglist\\n\");
    tot=opt=ext=siz=0;
    /* Get the total number of arguments */
    if (PyFunction_Check(fun)) {
        tmp_fun = fun;
        Py_INCREF(tmp_fun);
    }
    else {
        di = 1;
        if (PyObject_HasAttrString(fun,\"im_func\")) {
            tmp_fun = PyObject_GetAttrString(fun,\"im_func\");
        }
        else if (PyObject_HasAttrString(fun,\"__call__\")) {
            tmp = PyObject_GetAttrString(fun,\"__call__\");
            if (PyObject_HasAttrString(tmp,\"im_func\"))
                tmp_fun = PyObject_GetAttrString(tmp,\"im_func\");
            else {
                tmp_fun = fun; /* built-in function */
                Py_INCREF(tmp_fun);
                tot = maxnofargs;
                if (PyCFunction_Check(fun)) {
                    /* In case the function has a co_argcount (like on PyPy) */
                    di = 0;
                }
                if (xa != NULL)
                    tot += PyTuple_Size((PyObject *)xa);
            }
            Py_XDECREF(tmp);
        }
        else if (PyFortran_Check(fun) || PyFortran_Check1(fun)) {
            tot = maxnofargs;
            if (xa != NULL)
                tot += PyTuple_Size((PyObject *)xa);
            tmp_fun = fun;
            Py_INCREF(tmp_fun);
        }
        else if (F2PyCapsule_Check(fun)) {
            tot = maxnofargs;
            if (xa != NULL)
                ext = PyTuple_Size((PyObject *)xa);
            if(ext>0) {
                fprintf(stderr,\"extra arguments tuple cannot be used with PyCapsule call-back\\n\");
                goto capi_fail;
            }
            tmp_fun = fun;
            Py_INCREF(tmp_fun);
        }
    }

    if (tmp_fun == NULL) {
        fprintf(stderr,
                \"Call-back argument must be function|instance|instance.__call__|f2py-function \"
                \"but got %s.\\n\",
                ((fun == NULL) ? \"NULL\" : Py_TYPE(fun)->tp_name));
        goto capi_fail;
    }

    if (PyObject_HasAttrString(tmp_fun,\"__code__\")) {
        if (PyObject_HasAttrString(tmp = PyObject_GetAttrString(tmp_fun,\"__code__\"),\"co_argcount\")) {
            PyObject *tmp_argcount = PyObject_GetAttrString(tmp,\"co_argcount\");
            Py_DECREF(tmp);
            if (tmp_argcount == NULL) {
                goto capi_fail;
            }
            tot = PyLong_AsSsize_t(tmp_argcount) - di;
            Py_DECREF(tmp_argcount);
        }
    }
    /* Get the number of optional arguments */
    if (PyObject_HasAttrString(tmp_fun,\"__defaults__\")) {
        if (PyTuple_Check(tmp = PyObject_GetAttrString(tmp_fun,\"__defaults__\")))
            opt = PyTuple_Size(tmp);
        Py_XDECREF(tmp);
    }
    /* Get the number of extra arguments */
    if (xa != NULL)
        ext = PyTuple_Size((PyObject *)xa);
    /* Calculate the size of call-backs argument list */
    siz = MIN(maxnofargs+ext,tot);
    *nofargs = MAX(0,siz-ext);

#ifdef DEBUGCFUNCS
    fprintf(stderr,
            \"debug-capi:create_cb_arglist:maxnofargs(-nofoptargs),\"
            \"tot,opt,ext,siz,nofargs = %d(-%d), %zd, %zd, %zd, %zd, %d\\n\",
            maxnofargs, nofoptargs, tot, opt, ext, siz, *nofargs);
#endif

    if (siz < tot-opt) {
        fprintf(stderr,
                \"create_cb_arglist: Failed to build argument list \"
                \"(siz) with enough arguments (tot-opt) required by \"
                \"user-supplied function (siz,tot,opt=%zd, %zd, %zd).\\n\",
                siz, tot, opt);
        goto capi_fail;
    }

    /* Initialize argument list */
    *args = (PyTupleObject *)PyTuple_New(siz);
    for (i=0;i<*nofargs;i++) {
        Py_INCREF(Py_None);
        PyTuple_SET_ITEM((PyObject *)(*args),i,Py_None);
    }
    if (xa != NULL)
        for (i=(*nofargs);i<siz;i++) {
            tmp = PyTuple_GetItem((PyObject *)xa,i-(*nofargs));
            Py_INCREF(tmp);
            PyTuple_SET_ITEM(*args,i,tmp);
        }
    CFUNCSMESS(\"create_cb_arglist-end\\n\");
    Py_DECREF(tmp_fun);
    return 1;

capi_fail:
    if (PyErr_Occurred() == NULL)
        PyErr_SetString(#modulename#_error, errmess);
    Py_XDECREF(tmp_fun);
    return 0;
}
"""


def buildcfuncs():
    from .capi_maps import c2capi_map
    for k in c2capi_map.keys():
        m = f'pyarr_from_p_{k}1'
        cppmacros[
            m] = f'#define {m}(v) (PyArray_SimpleNewFromData(0,NULL,{c2capi_map[k]},(char *)v))'
    k = 'string'
    m = f'pyarr_from_p_{k}1'
    # NPY_CHAR compatibility, NPY_STRING with itemsize 1
    cppmacros[
        m] = f'#define {m}(v,dims) (PyArray_New(&PyArray_Type, 1, dims, NPY_STRING, NULL, v, 1, NPY_ARRAY_CARRAY, NULL))'


############ Auxiliary functions for sorting needs ###################

def append_needs(need, flag=1):
    # This function modifies the contents of the global `outneeds` dict.
    if isinstance(need, list):
        for n in need:
            append_needs(n, flag)
    elif isinstance(need, str):
        if not need:
            return
        if need in includes0:
            n = 'includes0'
        elif need in includes:
            n = 'includes'
        elif need in typedefs:
            n = 'typedefs'
        elif need in typedefs_generated:
            n = 'typedefs_generated'
        elif need in cppmacros:
            n = 'cppmacros'
        elif need in cfuncs:
            n = 'cfuncs'
        elif need in callbacks:
            n = 'callbacks'
        elif need in f90modhooks:
            n = 'f90modhooks'
        elif need in commonhooks:
            n = 'commonhooks'
        else:
            errmess(f'append_needs: unknown need {repr(need)}\n')
            return
        if need in outneeds[n]:
            return
        if flag:
            tmp = {}
            if need in needs:
                for nn in needs[need]:
                    t = append_needs(nn, 0)
                    if isinstance(t, dict):
                        for nnn in t.keys():
                            if nnn in tmp:
                                tmp[nnn] = tmp[nnn] + t[nnn]
                            else:
                                tmp[nnn] = t[nnn]
            for nn in tmp.keys():
                for nnn in tmp[nn]:
                    if nnn not in outneeds[nn]:
                        outneeds[nn] = [nnn] + outneeds[nn]
            outneeds[n].append(need)
        else:
            tmp = {}
            if need in needs:
                for nn in needs[need]:
                    t = append_needs(nn, flag)
                    if isinstance(t, dict):
                        for nnn in t.keys():
                            if nnn in tmp:
                                tmp[nnn] = t[nnn] + tmp[nnn]
                            else:
                                tmp[nnn] = t[nnn]
            if n not in tmp:
                tmp[n] = []
            tmp[n].append(need)
            return tmp
    else:
        errmess(f'append_needs: expected list or string but got :{repr(need)}\n')


def get_needs():
    # This function modifies the contents of the global `outneeds` dict.
    res = {}
    for n in outneeds.keys():
        out = []
        saveout = copy.copy(outneeds[n])
        while len(outneeds[n]) > 0:
            if outneeds[n][0] not in needs:
                out.append(outneeds[n][0])
                del outneeds[n][0]
            else:
                flag = 0
                for k in outneeds[n][1:]:
                    if k in needs[outneeds[n][0]]:
                        flag = 1
                        break
                if flag:
                    outneeds[n] = outneeds[n][1:] + [outneeds[n][0]]
                else:
                    out.append(outneeds[n][0])
                    del outneeds[n][0]
            if saveout and (0 not in map(lambda x, y: x == y, saveout, outneeds[n])) \
                    and outneeds[n] != []:
                print(n, saveout)
                errmess(
                    'get_needs: no progress in sorting needs, probably circular dependence, skipping.\n')
                out = out + saveout
                break
            saveout = copy.copy(outneeds[n])
        if out == []:
            out = [n]
        res[n] = out
    return res

# === NexusCore/openenv\Lib\site-packages\pydantic\fields.py ===
"""Defining fields on models."""

from __future__ import annotations as _annotations

import dataclasses
import inspect
import sys
import typing
from collections.abc import Mapping
from copy import copy
from dataclasses import Field as DataclassField
from functools import cached_property
from typing import Annotated, Any, Callable, ClassVar, Literal, TypeVar, cast, overload
from warnings import warn

import annotated_types
import typing_extensions
from pydantic_core import PydanticUndefined
from typing_extensions import Self, TypeAlias, Unpack, deprecated
from typing_inspection import typing_objects
from typing_inspection.introspection import UNKNOWN, AnnotationSource, ForbiddenQualifier, Qualifier, inspect_annotation

from . import types
from ._internal import _decorators, _fields, _generics, _internal_dataclass, _repr, _typing_extra, _utils
from ._internal._namespace_utils import GlobalsNamespace, MappingNamespace
from .aliases import AliasChoices, AliasPath
from .config import JsonDict
from .errors import PydanticForbiddenQualifier, PydanticUserError
from .json_schema import PydanticJsonSchemaWarning
from .warnings import PydanticDeprecatedSince20

if typing.TYPE_CHECKING:
    from ._internal._repr import ReprArgs
else:
    # See PyCharm issues https://youtrack.jetbrains.com/issue/PY-21915
    # and https://youtrack.jetbrains.com/issue/PY-51428
    DeprecationWarning = PydanticDeprecatedSince20

__all__ = 'Field', 'PrivateAttr', 'computed_field'


_Unset: Any = PydanticUndefined

if sys.version_info >= (3, 13):
    import warnings

    Deprecated: TypeAlias = warnings.deprecated | deprecated
else:
    Deprecated: TypeAlias = deprecated


class _FromFieldInfoInputs(typing_extensions.TypedDict, total=False):
    """This class exists solely to add type checking for the `**kwargs` in `FieldInfo.from_field`."""

    # TODO PEP 747: use TypeForm:
    annotation: type[Any] | None
    default_factory: Callable[[], Any] | Callable[[dict[str, Any]], Any] | None
    alias: str | None
    alias_priority: int | None
    validation_alias: str | AliasPath | AliasChoices | None
    serialization_alias: str | None
    title: str | None
    field_title_generator: Callable[[str, FieldInfo], str] | None
    description: str | None
    examples: list[Any] | None
    exclude: bool | None
    gt: annotated_types.SupportsGt | None
    ge: annotated_types.SupportsGe | None
    lt: annotated_types.SupportsLt | None
    le: annotated_types.SupportsLe | None
    multiple_of: float | None
    strict: bool | None
    min_length: int | None
    max_length: int | None
    pattern: str | typing.Pattern[str] | None
    allow_inf_nan: bool | None
    max_digits: int | None
    decimal_places: int | None
    union_mode: Literal['smart', 'left_to_right'] | None
    discriminator: str | types.Discriminator | None
    deprecated: Deprecated | str | bool | None
    json_schema_extra: JsonDict | Callable[[JsonDict], None] | None
    frozen: bool | None
    validate_default: bool | None
    repr: bool
    init: bool | None
    init_var: bool | None
    kw_only: bool | None
    coerce_numbers_to_str: bool | None
    fail_fast: bool | None


class _FieldInfoInputs(_FromFieldInfoInputs, total=False):
    """This class exists solely to add type checking for the `**kwargs` in `FieldInfo.__init__`."""

    default: Any


class FieldInfo(_repr.Representation):
    """This class holds information about a field.

    `FieldInfo` is used for any field definition regardless of whether the [`Field()`][pydantic.fields.Field]
    function is explicitly used.

    !!! warning
        You generally shouldn't be creating `FieldInfo` directly, you'll only need to use it when accessing
        [`BaseModel`][pydantic.main.BaseModel] `.model_fields` internals.

    Attributes:
        annotation: The type annotation of the field.
        default: The default value of the field.
        default_factory: A callable to generate the default value. The callable can either take 0 arguments
            (in which case it is called as is) or a single argument containing the already validated data.
        alias: The alias name of the field.
        alias_priority: The priority of the field's alias.
        validation_alias: The validation alias of the field.
        serialization_alias: The serialization alias of the field.
        title: The title of the field.
        field_title_generator: A callable that takes a field name and returns title for it.
        description: The description of the field.
        examples: List of examples of the field.
        exclude: Whether to exclude the field from the model serialization.
        discriminator: Field name or Discriminator for discriminating the type in a tagged union.
        deprecated: A deprecation message, an instance of `warnings.deprecated` or the `typing_extensions.deprecated` backport,
            or a boolean. If `True`, a default deprecation message will be emitted when accessing the field.
        json_schema_extra: A dict or callable to provide extra JSON schema properties.
        frozen: Whether the field is frozen.
        validate_default: Whether to validate the default value of the field.
        repr: Whether to include the field in representation of the model.
        init: Whether the field should be included in the constructor of the dataclass.
        init_var: Whether the field should _only_ be included in the constructor of the dataclass, and not stored.
        kw_only: Whether the field should be a keyword-only argument in the constructor of the dataclass.
        metadata: List of metadata constraints.
    """

    annotation: type[Any] | None
    default: Any
    default_factory: Callable[[], Any] | Callable[[dict[str, Any]], Any] | None
    alias: str | None
    alias_priority: int | None
    validation_alias: str | AliasPath | AliasChoices | None
    serialization_alias: str | None
    title: str | None
    field_title_generator: Callable[[str, FieldInfo], str] | None
    description: str | None
    examples: list[Any] | None
    exclude: bool | None
    discriminator: str | types.Discriminator | None
    deprecated: Deprecated | str | bool | None
    json_schema_extra: JsonDict | Callable[[JsonDict], None] | None
    frozen: bool | None
    validate_default: bool | None
    repr: bool
    init: bool | None
    init_var: bool | None
    kw_only: bool | None
    metadata: list[Any]

    __slots__ = (
        'annotation',
        'default',
        'default_factory',
        'alias',
        'alias_priority',
        'validation_alias',
        'serialization_alias',
        'title',
        'field_title_generator',
        'description',
        'examples',
        'exclude',
        'discriminator',
        'deprecated',
        'json_schema_extra',
        'frozen',
        'validate_default',
        'repr',
        'init',
        'init_var',
        'kw_only',
        'metadata',
        '_attributes_set',
        '_qualifiers',
        '_complete',
        '_original_assignment',
        '_original_annotation',
    )

    # used to convert kwargs to metadata/constraints,
    # None has a special meaning - these items are collected into a `PydanticGeneralMetadata`
    metadata_lookup: ClassVar[dict[str, typing.Callable[[Any], Any] | None]] = {
        'strict': types.Strict,
        'gt': annotated_types.Gt,
        'ge': annotated_types.Ge,
        'lt': annotated_types.Lt,
        'le': annotated_types.Le,
        'multiple_of': annotated_types.MultipleOf,
        'min_length': annotated_types.MinLen,
        'max_length': annotated_types.MaxLen,
        'pattern': None,
        'allow_inf_nan': None,
        'max_digits': None,
        'decimal_places': None,
        'union_mode': None,
        'coerce_numbers_to_str': None,
        'fail_fast': types.FailFast,
    }

    def __init__(self, **kwargs: Unpack[_FieldInfoInputs]) -> None:
        """This class should generally not be initialized directly; instead, use the `pydantic.fields.Field` function
        or one of the constructor classmethods.

        See the signature of `pydantic.fields.Field` for more details about the expected arguments.
        """
        self._attributes_set = {k: v for k, v in kwargs.items() if v is not _Unset}
        kwargs = {k: _DefaultValues.get(k) if v is _Unset else v for k, v in kwargs.items()}  # type: ignore
        self.annotation = kwargs.get('annotation')

        default = kwargs.pop('default', PydanticUndefined)
        if default is Ellipsis:
            self.default = PydanticUndefined
            self._attributes_set.pop('default', None)
        else:
            self.default = default

        self.default_factory = kwargs.pop('default_factory', None)

        if self.default is not PydanticUndefined and self.default_factory is not None:
            raise TypeError('cannot specify both default and default_factory')

        self.alias = kwargs.pop('alias', None)
        self.validation_alias = kwargs.pop('validation_alias', None)
        self.serialization_alias = kwargs.pop('serialization_alias', None)
        alias_is_set = any(alias is not None for alias in (self.alias, self.validation_alias, self.serialization_alias))
        self.alias_priority = kwargs.pop('alias_priority', None) or 2 if alias_is_set else None
        self.title = kwargs.pop('title', None)
        self.field_title_generator = kwargs.pop('field_title_generator', None)
        self.description = kwargs.pop('description', None)
        self.examples = kwargs.pop('examples', None)
        self.exclude = kwargs.pop('exclude', None)
        self.discriminator = kwargs.pop('discriminator', None)
        # For compatibility with FastAPI<=0.110.0, we preserve the existing value if it is not overridden
        self.deprecated = kwargs.pop('deprecated', getattr(self, 'deprecated', None))
        self.repr = kwargs.pop('repr', True)
        self.json_schema_extra = kwargs.pop('json_schema_extra', None)
        self.validate_default = kwargs.pop('validate_default', None)
        self.frozen = kwargs.pop('frozen', None)
        # currently only used on dataclasses
        self.init = kwargs.pop('init', None)
        self.init_var = kwargs.pop('init_var', None)
        self.kw_only = kwargs.pop('kw_only', None)

        self.metadata = self._collect_metadata(kwargs)  # type: ignore

        # Private attributes:
        self._qualifiers: set[Qualifier] = set()
        # Used to rebuild FieldInfo instances:
        self._complete = True
        self._original_annotation: Any = PydanticUndefined
        self._original_assignment: Any = PydanticUndefined

    @staticmethod
    def from_field(default: Any = PydanticUndefined, **kwargs: Unpack[_FromFieldInfoInputs]) -> FieldInfo:
        """Create a new `FieldInfo` object with the `Field` function.

        Args:
            default: The default value for the field. Defaults to Undefined.
            **kwargs: Additional arguments dictionary.

        Raises:
            TypeError: If 'annotation' is passed as a keyword argument.

        Returns:
            A new FieldInfo object with the given parameters.

        Example:
            This is how you can create a field with default value like this:

            ```python
            import pydantic

            class MyModel(pydantic.BaseModel):
                foo: int = pydantic.Field(4)
            ```
        """
        if 'annotation' in kwargs:
            raise TypeError('"annotation" is not permitted as a Field keyword argument')
        return FieldInfo(default=default, **kwargs)

    @staticmethod
    def from_annotation(annotation: type[Any], *, _source: AnnotationSource = AnnotationSource.ANY) -> FieldInfo:
        """Creates a `FieldInfo` instance from a bare annotation.

        This function is used internally to create a `FieldInfo` from a bare annotation like this:

        ```python
        import pydantic

        class MyModel(pydantic.BaseModel):
            foo: int  # <-- like this
        ```

        We also account for the case where the annotation can be an instance of `Annotated` and where
        one of the (not first) arguments in `Annotated` is an instance of `FieldInfo`, e.g.:

        ```python
        from typing import Annotated

        import annotated_types

        import pydantic

        class MyModel(pydantic.BaseModel):
            foo: Annotated[int, annotated_types.Gt(42)]
            bar: Annotated[int, pydantic.Field(gt=42)]
        ```

        Args:
            annotation: An annotation object.

        Returns:
            An instance of the field metadata.
        """
        try:
            inspected_ann = inspect_annotation(
                annotation,
                annotation_source=_source,
                unpack_type_aliases='skip',
            )
        except ForbiddenQualifier as e:
            raise PydanticForbiddenQualifier(e.qualifier, annotation)

        # TODO check for classvar and error?

        # No assigned value, this happens when using a bare `Final` qualifier (also for other
        # qualifiers, but they shouldn't appear here). In this case we infer the type as `Any`
        # because we don't have any assigned value.
        type_expr: Any = Any if inspected_ann.type is UNKNOWN else inspected_ann.type
        final = 'final' in inspected_ann.qualifiers
        metadata = inspected_ann.metadata

        if not metadata:
            # No metadata, e.g. `field: int`, or `field: Final[str]`:
            field_info = FieldInfo(annotation=type_expr, frozen=final or None)
            field_info._qualifiers = inspected_ann.qualifiers
            return field_info

        # With metadata, e.g. `field: Annotated[int, Field(...), Gt(1)]`:
        field_info_annotations = [a for a in metadata if isinstance(a, FieldInfo)]
        field_info = FieldInfo.merge_field_infos(*field_info_annotations, annotation=type_expr)

        new_field_info = field_info._copy()
        new_field_info.annotation = type_expr
        new_field_info.frozen = final or field_info.frozen
        field_metadata: list[Any] = []
        for a in metadata:
            if typing_objects.is_deprecated(a):
                new_field_info.deprecated = a.message
            elif not isinstance(a, FieldInfo):
                field_metadata.append(a)
            else:
                field_metadata.extend(a.metadata)
            new_field_info.metadata = field_metadata
        new_field_info._qualifiers = inspected_ann.qualifiers
        return new_field_info

    @staticmethod
    def from_annotated_attribute(
        annotation: type[Any], default: Any, *, _source: AnnotationSource = AnnotationSource.ANY
    ) -> FieldInfo:
        """Create `FieldInfo` from an annotation with a default value.

        This is used in cases like the following:

        ```python
        from typing import Annotated

        import annotated_types

        import pydantic

        class MyModel(pydantic.BaseModel):
            foo: int = 4  # <-- like this
            bar: Annotated[int, annotated_types.Gt(4)] = 4  # <-- or this
            spam: Annotated[int, pydantic.Field(gt=4)] = 4  # <-- or this
        ```

        Args:
            annotation: The type annotation of the field.
            default: The default value of the field.

        Returns:
            A field object with the passed values.
        """
        if annotation is default:
            raise PydanticUserError(
                'Error when building FieldInfo from annotated attribute. '
                "Make sure you don't have any field name clashing with a type annotation.",
                code='unevaluable-type-annotation',
            )

        try:
            inspected_ann = inspect_annotation(
                annotation,
                annotation_source=_source,
                unpack_type_aliases='skip',
            )
        except ForbiddenQualifier as e:
            raise PydanticForbiddenQualifier(e.qualifier, annotation)

        # TODO check for classvar and error?

        # TODO infer from the default, this can be done in v3 once we treat final fields with
        # a default as proper fields and not class variables:
        type_expr: Any = Any if inspected_ann.type is UNKNOWN else inspected_ann.type
        final = 'final' in inspected_ann.qualifiers
        metadata = inspected_ann.metadata

        if isinstance(default, FieldInfo):
            # e.g. `field: int = Field(...)`
            default_metadata = default.metadata.copy()
            default = copy(default)
            default.metadata = default_metadata

            default.annotation = type_expr
            default.metadata += metadata
            merged_default = FieldInfo.merge_field_infos(
                *[x for x in metadata if isinstance(x, FieldInfo)],
                default,
                annotation=default.annotation,
            )
            merged_default.frozen = final or merged_default.frozen
            merged_default._qualifiers = inspected_ann.qualifiers
            return merged_default

        if isinstance(default, dataclasses.Field):
            # `collect_dataclass_fields()` passes the dataclass Field as a default.
            pydantic_field = FieldInfo._from_dataclass_field(default)
            pydantic_field.annotation = type_expr
            pydantic_field.metadata += metadata
            pydantic_field = FieldInfo.merge_field_infos(
                *[x for x in metadata if isinstance(x, FieldInfo)],
                pydantic_field,
                annotation=pydantic_field.annotation,
            )
            pydantic_field.frozen = final or pydantic_field.frozen
            pydantic_field.init_var = 'init_var' in inspected_ann.qualifiers
            pydantic_field.init = getattr(default, 'init', None)
            pydantic_field.kw_only = getattr(default, 'kw_only', None)
            pydantic_field._qualifiers = inspected_ann.qualifiers
            return pydantic_field

        if not metadata:
            # No metadata, e.g. `field: int = ...`, or `field: Final[str] = ...`:
            field_info = FieldInfo(annotation=type_expr, default=default, frozen=final or None)
            field_info._qualifiers = inspected_ann.qualifiers
            return field_info

        # With metadata, e.g. `field: Annotated[int, Field(...), Gt(1)] = ...`:
        field_infos = [a for a in metadata if isinstance(a, FieldInfo)]
        field_info = FieldInfo.merge_field_infos(*field_infos, annotation=type_expr, default=default)
        field_metadata: list[Any] = []
        for a in metadata:
            if typing_objects.is_deprecated(a):
                field_info.deprecated = a.message
            elif not isinstance(a, FieldInfo):
                field_metadata.append(a)
            else:
                field_metadata.extend(a.metadata)
        field_info.metadata = field_metadata
        field_info._qualifiers = inspected_ann.qualifiers
        return field_info

    @staticmethod
    def merge_field_infos(*field_infos: FieldInfo, **overrides: Any) -> FieldInfo:
        """Merge `FieldInfo` instances keeping only explicitly set attributes.

        Later `FieldInfo` instances override earlier ones.

        Returns:
            FieldInfo: A merged FieldInfo instance.
        """
        if len(field_infos) == 1:
            # No merging necessary, but we still need to make a copy and apply the overrides
            field_info = field_infos[0]._copy()
            field_info._attributes_set.update(overrides)

            default_override = overrides.pop('default', PydanticUndefined)
            if default_override is Ellipsis:
                default_override = PydanticUndefined
            if default_override is not PydanticUndefined:
                field_info.default = default_override

            for k, v in overrides.items():
                setattr(field_info, k, v)
            return field_info  # type: ignore

        merged_field_info_kwargs: dict[str, Any] = {}
        metadata = {}
        for field_info in field_infos:
            attributes_set = field_info._attributes_set.copy()

            try:
                json_schema_extra = attributes_set.pop('json_schema_extra')
                existing_json_schema_extra = merged_field_info_kwargs.get('json_schema_extra')

                if existing_json_schema_extra is None:
                    merged_field_info_kwargs['json_schema_extra'] = json_schema_extra
                if isinstance(existing_json_schema_extra, dict):
                    if isinstance(json_schema_extra, dict):
                        merged_field_info_kwargs['json_schema_extra'] = {
                            **existing_json_schema_extra,
                            **json_schema_extra,
                        }
                    if callable(json_schema_extra):
                        warn(
                            'Composing `dict` and `callable` type `json_schema_extra` is not supported.'
                            'The `callable` type is being ignored.'
                            "If you'd like support for this behavior, please open an issue on pydantic.",
                            PydanticJsonSchemaWarning,
                        )
                elif callable(json_schema_extra):
                    # if ever there's a case of a callable, we'll just keep the last json schema extra spec
                    merged_field_info_kwargs['json_schema_extra'] = json_schema_extra
            except KeyError:
                pass

            # later FieldInfo instances override everything except json_schema_extra from earlier FieldInfo instances
            merged_field_info_kwargs.update(attributes_set)

            for x in field_info.metadata:
                if not isinstance(x, FieldInfo):
                    metadata[type(x)] = x

        merged_field_info_kwargs.update(overrides)
        field_info = FieldInfo(**merged_field_info_kwargs)
        field_info.metadata = list(metadata.values())
        return field_info

    @staticmethod
    def _from_dataclass_field(dc_field: DataclassField[Any]) -> FieldInfo:
        """Return a new `FieldInfo` instance from a `dataclasses.Field` instance.

        Args:
            dc_field: The `dataclasses.Field` instance to convert.

        Returns:
            The corresponding `FieldInfo` instance.

        Raises:
            TypeError: If any of the `FieldInfo` kwargs does not match the `dataclass.Field` kwargs.
        """
        default = dc_field.default
        if default is dataclasses.MISSING:
            default = _Unset

        if dc_field.default_factory is dataclasses.MISSING:
            default_factory = _Unset
        else:
            default_factory = dc_field.default_factory

        # use the `Field` function so in correct kwargs raise the correct `TypeError`
        dc_field_metadata = {k: v for k, v in dc_field.metadata.items() if k in _FIELD_ARG_NAMES}
        return Field(default=default, default_factory=default_factory, repr=dc_field.repr, **dc_field_metadata)  # pyright: ignore[reportCallIssue]

    @staticmethod
    def _collect_metadata(kwargs: dict[str, Any]) -> list[Any]:
        """Collect annotations from kwargs.

        Args:
            kwargs: Keyword arguments passed to the function.

        Returns:
            A list of metadata objects - a combination of `annotated_types.BaseMetadata` and
                `PydanticMetadata`.
        """
        metadata: list[Any] = []
        general_metadata = {}
        for key, value in list(kwargs.items()):
            try:
                marker = FieldInfo.metadata_lookup[key]
            except KeyError:
                continue

            del kwargs[key]
            if value is not None:
                if marker is None:
                    general_metadata[key] = value
                else:
                    metadata.append(marker(value))
        if general_metadata:
            metadata.append(_fields.pydantic_general_metadata(**general_metadata))
        return metadata

    def _copy(self) -> Self:
        copied = copy(self)
        for attr_name in ('metadata', '_attributes_set', '_qualifiers'):
            # Apply "deep-copy" behavior on collections attributes:
            value = getattr(copied, attr_name).copy()
            setattr(copied, attr_name, value)

        return copied

    @property
    def deprecation_message(self) -> str | None:
        """The deprecation message to be emitted, or `None` if not set."""
        if self.deprecated is None:
            return None
        if isinstance(self.deprecated, bool):
            return 'deprecated' if self.deprecated else None
        return self.deprecated if isinstance(self.deprecated, str) else self.deprecated.message

    @property
    def default_factory_takes_validated_data(self) -> bool | None:
        """Whether the provided default factory callable has a validated data parameter.

        Returns `None` if no default factory is set.
        """
        if self.default_factory is not None:
            return _fields.takes_validated_data_argument(self.default_factory)

    @overload
    def get_default(
        self, *, call_default_factory: Literal[True], validated_data: dict[str, Any] | None = None
    ) -> Any: ...

    @overload
    def get_default(self, *, call_default_factory: Literal[False] = ...) -> Any: ...

    def get_default(self, *, call_default_factory: bool = False, validated_data: dict[str, Any] | None = None) -> Any:
        """Get the default value.

        We expose an option for whether to call the default_factory (if present), as calling it may
        result in side effects that we want to avoid. However, there are times when it really should
        be called (namely, when instantiating a model via `model_construct`).

        Args:
            call_default_factory: Whether to call the default factory or not.
            validated_data: The already validated data to be passed to the default factory.

        Returns:
            The default value, calling the default factory if requested or `None` if not set.
        """
        if self.default_factory is None:
            return _utils.smart_deepcopy(self.default)
        elif call_default_factory:
            if self.default_factory_takes_validated_data:
                fac = cast('Callable[[dict[str, Any]], Any]', self.default_factory)
                if validated_data is None:
                    raise ValueError(
                        "The default factory requires the 'validated_data' argument, which was not provided when calling 'get_default'."
                    )
                return fac(validated_data)
            else:
                fac = cast('Callable[[], Any]', self.default_factory)
                return fac()
        else:
            return None

    def is_required(self) -> bool:
        """Check if the field is required (i.e., does not have a default value or factory).

        Returns:
            `True` if the field is required, `False` otherwise.
        """
        return self.default is PydanticUndefined and self.default_factory is None

    def rebuild_annotation(self) -> Any:
        """Attempts to rebuild the original annotation for use in function signatures.

        If metadata is present, it adds it to the original annotation using
        `Annotated`. Otherwise, it returns the original annotation as-is.

        Note that because the metadata has been flattened, the original annotation
        may not be reconstructed exactly as originally provided, e.g. if the original
        type had unrecognized annotations, or was annotated with a call to `pydantic.Field`.

        Returns:
            The rebuilt annotation.
        """
        if not self.metadata:
            return self.annotation
        else:
            # Annotated arguments must be a tuple
            return Annotated[(self.annotation, *self.metadata)]  # type: ignore

    def apply_typevars_map(
        self,
        typevars_map: Mapping[TypeVar, Any] | None,
        globalns: GlobalsNamespace | None = None,
        localns: MappingNamespace | None = None,
    ) -> None:
        """Apply a `typevars_map` to the annotation.

        This method is used when analyzing parametrized generic types to replace typevars with their concrete types.

        This method applies the `typevars_map` to the annotation in place.

        Args:
            typevars_map: A dictionary mapping type variables to their concrete types.
            globalns: The globals namespace to use during type annotation evaluation.
            localns: The locals namespace to use during type annotation evaluation.

        See Also:
            pydantic._internal._generics.replace_types is used for replacing the typevars with
                their concrete types.
        """
        annotation = _generics.replace_types(self.annotation, typevars_map)
        annotation, evaluated = _typing_extra.try_eval_type(annotation, globalns, localns)
        self.annotation = annotation
        if not evaluated:
            self._complete = False
            self._original_annotation = self.annotation

    def __repr_args__(self) -> ReprArgs:
        yield 'annotation', _repr.PlainRepr(_repr.display_as_type(self.annotation))
        yield 'required', self.is_required()

        for s in self.__slots__:
            # TODO: properly make use of the protocol (https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol)
            # By yielding a three-tuple:
            if s in (
                'annotation',
                '_attributes_set',
                '_qualifiers',
                '_complete',
                '_original_assignment',
                '_original_annotation',
            ):
                continue
            elif s == 'metadata' and not self.metadata:
                continue
            elif s == 'repr' and self.repr is True:
                continue
            if s == 'frozen' and self.frozen is False:
                continue
            if s == 'validation_alias' and self.validation_alias == self.alias:
                continue
            if s == 'serialization_alias' and self.serialization_alias == self.alias:
                continue
            if s == 'default' and self.default is not PydanticUndefined:
                yield 'default', self.default
            elif s == 'default_factory' and self.default_factory is not None:
                yield 'default_factory', _repr.PlainRepr(_repr.display_as_type(self.default_factory))
            else:
                value = getattr(self, s)
                if value is not None and value is not PydanticUndefined:
                    yield s, value


class _EmptyKwargs(typing_extensions.TypedDict):
    """This class exists solely to ensure that type checking warns about passing `**extra` in `Field`."""


_DefaultValues = {
    'default': ...,
    'default_factory': None,
    'alias': None,
    'alias_priority': None,
    'validation_alias': None,
    'serialization_alias': None,
    'title': None,
    'description': None,
    'examples': None,
    'exclude': None,
    'discriminator': None,
    'json_schema_extra': None,
    'frozen': None,
    'validate_default': None,
    'repr': True,
    'init': None,
    'init_var': None,
    'kw_only': None,
    'pattern': None,
    'strict': None,
    'gt': None,
    'ge': None,
    'lt': None,
    'le': None,
    'multiple_of': None,
    'allow_inf_nan': None,
    'max_digits': None,
    'decimal_places': None,
    'min_length': None,
    'max_length': None,
    'coerce_numbers_to_str': None,
}


_T = TypeVar('_T')


# NOTE: Actual return type is 'FieldInfo', but we want to help type checkers
# to understand the magic that happens at runtime with the following overloads:
@overload  # type hint the return value as `Any` to avoid type checking regressions when using `...`.
def Field(
    default: ellipsis,  # noqa: F821  # TODO: use `_typing_extra.EllipsisType` when we drop Py3.9
    *,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[Any] | None = _Unset,
    exclude: bool | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | typing.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: Literal['smart', 'left_to_right'] = _Unset,
    fail_fast: bool | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> Any: ...
@overload  # `default` argument set
def Field(
    default: _T,
    *,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[Any] | None = _Unset,
    exclude: bool | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | typing.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: Literal['smart', 'left_to_right'] = _Unset,
    fail_fast: bool | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> _T: ...
@overload  # `default_factory` argument set
def Field(
    *,
    default_factory: Callable[[], _T] | Callable[[dict[str, Any]], _T],
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[Any] | None = _Unset,
    exclude: bool | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | typing.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: Literal['smart', 'left_to_right'] = _Unset,
    fail_fast: bool | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> _T: ...
@overload
def Field(  # No default set
    *,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[Any] | None = _Unset,
    exclude: bool | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | typing.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: Literal['smart', 'left_to_right'] = _Unset,
    fail_fast: bool | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> Any: ...
def Field(  # noqa: C901
    default: Any = PydanticUndefined,
    *,
    default_factory: Callable[[], Any] | Callable[[dict[str, Any]], Any] | None = _Unset,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    field_title_generator: Callable[[str, FieldInfo], str] | None = _Unset,
    description: str | None = _Unset,
    examples: list[Any] | None = _Unset,
    exclude: bool | None = _Unset,
    discriminator: str | types.Discriminator | None = _Unset,
    deprecated: Deprecated | str | bool | None = _Unset,
    json_schema_extra: JsonDict | Callable[[JsonDict], None] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init: bool | None = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | typing.Pattern[str] | None = _Unset,
    strict: bool | None = _Unset,
    coerce_numbers_to_str: bool | None = _Unset,
    gt: annotated_types.SupportsGt | None = _Unset,
    ge: annotated_types.SupportsGe | None = _Unset,
    lt: annotated_types.SupportsLt | None = _Unset,
    le: annotated_types.SupportsLe | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    union_mode: Literal['smart', 'left_to_right'] = _Unset,
    fail_fast: bool | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> Any:
    """!!! abstract "Usage Documentation"
        [Fields](../concepts/fields.md)

    Create a field for objects that can be configured.

    Used to provide extra information about a field, either for the model schema or complex validation. Some arguments
    apply only to number fields (`int`, `float`, `Decimal`) and some apply only to `str`.

    Note:
        - Any `_Unset` objects will be replaced by the corresponding value defined in the `_DefaultValues` dictionary. If a key for the `_Unset` object is not found in the `_DefaultValues` dictionary, it will default to `None`

    Args:
        default: Default value if the field is not set.
        default_factory: A callable to generate the default value. The callable can either take 0 arguments
            (in which case it is called as is) or a single argument containing the already validated data.
        alias: The name to use for the attribute when validating or serializing by alias.
            This is often used for things like converting between snake and camel case.
        alias_priority: Priority of the alias. This affects whether an alias generator is used.
        validation_alias: Like `alias`, but only affects validation, not serialization.
        serialization_alias: Like `alias`, but only affects serialization, not validation.
        title: Human-readable title.
        field_title_generator: A callable that takes a field name and returns title for it.
        description: Human-readable description.
        examples: Example values for this field.
        exclude: Whether to exclude the field from the model serialization.
        discriminator: Field name or Discriminator for discriminating the type in a tagged union.
        deprecated: A deprecation message, an instance of `warnings.deprecated` or the `typing_extensions.deprecated` backport,
            or a boolean. If `True`, a default deprecation message will be emitted when accessing the field.
        json_schema_extra: A dict or callable to provide extra JSON schema properties.
        frozen: Whether the field is frozen. If true, attempts to change the value on an instance will raise an error.
        validate_default: If `True`, apply validation to the default value every time you create an instance.
            Otherwise, for performance reasons, the default value of the field is trusted and not validated.
        repr: A boolean indicating whether to include the field in the `__repr__` output.
        init: Whether the field should be included in the constructor of the dataclass.
            (Only applies to dataclasses.)
        init_var: Whether the field should _only_ be included in the constructor of the dataclass.
            (Only applies to dataclasses.)
        kw_only: Whether the field should be a keyword-only argument in the constructor of the dataclass.
            (Only applies to dataclasses.)
        coerce_numbers_to_str: Whether to enable coercion of any `Number` type to `str` (not applicable in `strict` mode).
        strict: If `True`, strict validation is applied to the field.
            See [Strict Mode](../concepts/strict_mode.md) for details.
        gt: Greater than. If set, value must be greater than this. Only applicable to numbers.
        ge: Greater than or equal. If set, value must be greater than or equal to this. Only applicable to numbers.
        lt: Less than. If set, value must be less than this. Only applicable to numbers.
        le: Less than or equal. If set, value must be less than or equal to this. Only applicable to numbers.
        multiple_of: Value must be a multiple of this. Only applicable to numbers.
        min_length: Minimum length for iterables.
        max_length: Maximum length for iterables.
        pattern: Pattern for strings (a regular expression).
        allow_inf_nan: Allow `inf`, `-inf`, `nan`. Only applicable to float and [`Decimal`][decimal.Decimal] numbers.
        max_digits: Maximum number of allow digits for strings.
        decimal_places: Maximum number of decimal places allowed for numbers.
        union_mode: The strategy to apply when validating a union. Can be `smart` (the default), or `left_to_right`.
            See [Union Mode](../concepts/unions.md#union-modes) for details.
        fail_fast: If `True`, validation will stop on the first error. If `False`, all validation errors will be collected.
            This option can be applied only to iterable types (list, tuple, set, and frozenset).
        extra: (Deprecated) Extra fields that will be included in the JSON schema.

            !!! warning Deprecated
                The `extra` kwargs is deprecated. Use `json_schema_extra` instead.

    Returns:
        A new [`FieldInfo`][pydantic.fields.FieldInfo]. The return annotation is `Any` so `Field` can be used on
            type-annotated fields without causing a type error.
    """
    # Check deprecated and removed params from V1. This logic should eventually be removed.
    const = extra.pop('const', None)  # type: ignore
    if const is not None:
        raise PydanticUserError('`const` is removed, use `Literal` instead', code='removed-kwargs')

    min_items = extra.pop('min_items', None)  # type: ignore
    if min_items is not None:
        warn('`min_items` is deprecated and will be removed, use `min_length` instead', DeprecationWarning)
        if min_length in (None, _Unset):
            min_length = min_items  # type: ignore

    max_items = extra.pop('max_items', None)  # type: ignore
    if max_items is not None:
        warn('`max_items` is deprecated and will be removed, use `max_length` instead', DeprecationWarning)
        if max_length in (None, _Unset):
            max_length = max_items  # type: ignore

    unique_items = extra.pop('unique_items', None)  # type: ignore
    if unique_items is not None:
        raise PydanticUserError(
            (
                '`unique_items` is removed, use `Set` instead'
                '(this feature is discussed in https://github.com/pydantic/pydantic-core/issues/296)'
            ),
            code='removed-kwargs',
        )

    allow_mutation = extra.pop('allow_mutation', None)  # type: ignore
    if allow_mutation is not None:
        warn('`allow_mutation` is deprecated and will be removed. use `frozen` instead', DeprecationWarning)
        if allow_mutation is False:
            frozen = True

    regex = extra.pop('regex', None)  # type: ignore
    if regex is not None:
        raise PydanticUserError('`regex` is removed. use `pattern` instead', code='removed-kwargs')

    if extra:
        warn(
            'Using extra keyword arguments on `Field` is deprecated and will be removed.'
            ' Use `json_schema_extra` instead.'
            f' (Extra keys: {", ".join(k.__repr__() for k in extra.keys())})',
            DeprecationWarning,
        )
        if not json_schema_extra or json_schema_extra is _Unset:
            json_schema_extra = extra  # type: ignore

    if (
        validation_alias
        and validation_alias is not _Unset
        and not isinstance(validation_alias, (str, AliasChoices, AliasPath))
    ):
        raise TypeError('Invalid `validation_alias` type. it should be `str`, `AliasChoices`, or `AliasPath`')

    if serialization_alias in (_Unset, None) and isinstance(alias, str):
        serialization_alias = alias

    if validation_alias in (_Unset, None):
        validation_alias = alias

    include = extra.pop('include', None)  # type: ignore
    if include is not None:
        warn('`include` is deprecated and does nothing. It will be removed, use `exclude` instead', DeprecationWarning)

    return FieldInfo.from_field(
        default,
        default_factory=default_factory,
        alias=alias,
        alias_priority=alias_priority,
        validation_alias=validation_alias,
        serialization_alias=serialization_alias,
        title=title,
        field_title_generator=field_title_generator,
        description=description,
        examples=examples,
        exclude=exclude,
        discriminator=discriminator,
        deprecated=deprecated,
        json_schema_extra=json_schema_extra,
        frozen=frozen,
        pattern=pattern,
        validate_default=validate_default,
        repr=repr,
        init=init,
        init_var=init_var,
        kw_only=kw_only,
        coerce_numbers_to_str=coerce_numbers_to_str,
        strict=strict,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        min_length=min_length,
        max_length=max_length,
        allow_inf_nan=allow_inf_nan,
        max_digits=max_digits,
        decimal_places=decimal_places,
        union_mode=union_mode,
        fail_fast=fail_fast,
    )


_FIELD_ARG_NAMES = set(inspect.signature(Field).parameters)
_FIELD_ARG_NAMES.remove('extra')  # do not include the varkwargs parameter


class ModelPrivateAttr(_repr.Representation):
    """A descriptor for private attributes in class models.

    !!! warning
        You generally shouldn't be creating `ModelPrivateAttr` instances directly, instead use
        `pydantic.fields.PrivateAttr`. (This is similar to `FieldInfo` vs. `Field`.)

    Attributes:
        default: The default value of the attribute if not provided.
        default_factory: A callable function that generates the default value of the
            attribute if not provided.
    """

    __slots__ = ('default', 'default_factory')

    def __init__(
        self, default: Any = PydanticUndefined, *, default_factory: typing.Callable[[], Any] | None = None
    ) -> None:
        if default is Ellipsis:
            self.default = PydanticUndefined
        else:
            self.default = default
        self.default_factory = default_factory

    if not typing.TYPE_CHECKING:
        # We put `__getattr__` in a non-TYPE_CHECKING block because otherwise, mypy allows arbitrary attribute access

        def __getattr__(self, item: str) -> Any:
            """This function improves compatibility with custom descriptors by ensuring delegation happens
            as expected when the default value of a private attribute is a descriptor.
            """
            if item in {'__get__', '__set__', '__delete__'}:
                if hasattr(self.default, item):
                    return getattr(self.default, item)
            raise AttributeError(f'{type(self).__name__!r} object has no attribute {item!r}')

    def __set_name__(self, cls: type[Any], name: str) -> None:
        """Preserve `__set_name__` protocol defined in https://peps.python.org/pep-0487."""
        default = self.default
        if default is PydanticUndefined:
            return
        set_name = getattr(default, '__set_name__', None)
        if callable(set_name):
            set_name(cls, name)

    def get_default(self) -> Any:
        """Retrieve the default value of the object.

        If `self.default_factory` is `None`, the method will return a deep copy of the `self.default` object.

        If `self.default_factory` is not `None`, it will call `self.default_factory` and return the value returned.

        Returns:
            The default value of the object.
        """
        return _utils.smart_deepcopy(self.default) if self.default_factory is None else self.default_factory()

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and (self.default, self.default_factory) == (
            other.default,
            other.default_factory,
        )


# NOTE: Actual return type is 'ModelPrivateAttr', but we want to help type checkers
# to understand the magic that happens at runtime.
@overload  # `default` argument set
def PrivateAttr(
    default: _T,
    *,
    init: Literal[False] = False,
) -> _T: ...
@overload  # `default_factory` argument set
def PrivateAttr(
    *,
    default_factory: Callable[[], _T],
    init: Literal[False] = False,
) -> _T: ...
@overload  # No default set
def PrivateAttr(
    *,
    init: Literal[False] = False,
) -> Any: ...
def PrivateAttr(
    default: Any = PydanticUndefined,
    *,
    default_factory: Callable[[], Any] | None = None,
    init: Literal[False] = False,
) -> Any:
    """!!! abstract "Usage Documentation"
        [Private Model Attributes](../concepts/models.md#private-model-attributes)

    Indicates that an attribute is intended for private use and not handled during normal validation/serialization.

    Private attributes are not validated by Pydantic, so it's up to you to ensure they are used in a type-safe manner.

    Private attributes are stored in `__private_attributes__` on the model.

    Args:
        default: The attribute's default value. Defaults to Undefined.
        default_factory: Callable that will be
            called when a default value is needed for this attribute.
            If both `default` and `default_factory` are set, an error will be raised.
        init: Whether the attribute should be included in the constructor of the dataclass. Always `False`.

    Returns:
        An instance of [`ModelPrivateAttr`][pydantic.fields.ModelPrivateAttr] class.

    Raises:
        ValueError: If both `default` and `default_factory` are set.
    """
    if default is not PydanticUndefined and default_factory is not None:
        raise TypeError('cannot specify both default and default_factory')

    return ModelPrivateAttr(
        default,
        default_factory=default_factory,
    )


@dataclasses.dataclass(**_internal_dataclass.slots_true)
class ComputedFieldInfo:
    """A container for data from `@computed_field` so that we can access it while building the pydantic-core schema.

    Attributes:
        decorator_repr: A class variable representing the decorator string, '@computed_field'.
        wrapped_property: The wrapped computed field property.
        return_type: The type of the computed field property's return value.
        alias: The alias of the property to be used during serialization.
        alias_priority: The priority of the alias. This affects whether an alias generator is used.
        title: Title of the computed field to include in the serialization JSON schema.
        field_title_generator: A callable that takes a field name and returns title for it.
        description: Description of the computed field to include in the serialization JSON schema.
        deprecated: A deprecation message, an instance of `warnings.deprecated` or the `typing_extensions.deprecated` backport,
            or a boolean. If `True`, a default deprecation message will be emitted when accessing the field.
        examples: Example values of the computed field to include in the serialization JSON schema.
        json_schema_extra: A dict or callable to provide extra JSON schema properties.
        repr: A boolean indicating whether to include the field in the __repr__ output.
    """

    decorator_repr: ClassVar[str] = '@computed_field'
    wrapped_property: property
    return_type: Any
    alias: str | None
    alias_priority: int | None
    title: str | None
    field_title_generator: typing.Callable[[str, ComputedFieldInfo], str] | None
    description: str | None
    deprecated: Deprecated | str | bool | None
    examples: list[Any] | None
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None
    repr: bool

    @property
    def deprecation_message(self) -> str | None:
        """The deprecation message to be emitted, or `None` if not set."""
        if self.deprecated is None:
            return None
        if isinstance(self.deprecated, bool):
            return 'deprecated' if self.deprecated else None
        return self.deprecated if isinstance(self.deprecated, str) else self.deprecated.message


def _wrapped_property_is_private(property_: cached_property | property) -> bool:  # type: ignore
    """Returns true if provided property is private, False otherwise."""
    wrapped_name: str = ''

    if isinstance(property_, property):
        wrapped_name = getattr(property_.fget, '__name__', '')
    elif isinstance(property_, cached_property):  # type: ignore
        wrapped_name = getattr(property_.func, '__name__', '')  # type: ignore

    return wrapped_name.startswith('_') and not wrapped_name.startswith('__')


# this should really be `property[T], cached_property[T]` but property is not generic unlike cached_property
# See https://github.com/python/typing/issues/985 and linked issues
PropertyT = typing.TypeVar('PropertyT')


@typing.overload
def computed_field(func: PropertyT, /) -> PropertyT: ...


@typing.overload
def computed_field(
    *,
    alias: str | None = None,
    alias_priority: int | None = None,
    title: str | None = None,
    field_title_generator: typing.Callable[[str, ComputedFieldInfo], str] | None = None,
    description: str | None = None,
    deprecated: Deprecated | str | bool | None = None,
    examples: list[Any] | None = None,
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = None,
    repr: bool = True,
    return_type: Any = PydanticUndefined,
) -> typing.Callable[[PropertyT], PropertyT]: ...


def computed_field(
    func: PropertyT | None = None,
    /,
    *,
    alias: str | None = None,
    alias_priority: int | None = None,
    title: str | None = None,
    field_title_generator: typing.Callable[[str, ComputedFieldInfo], str] | None = None,
    description: str | None = None,
    deprecated: Deprecated | str | bool | None = None,
    examples: list[Any] | None = None,
    json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = None,
    repr: bool | None = None,
    return_type: Any = PydanticUndefined,
) -> PropertyT | typing.Callable[[PropertyT], PropertyT]:
    """!!! abstract "Usage Documentation"
        [The `computed_field` decorator](../concepts/fields.md#the-computed_field-decorator)

    Decorator to include `property` and `cached_property` when serializing models or dataclasses.

    This is useful for fields that are computed from other fields, or for fields that are expensive to compute and should be cached.

    ```python
    from pydantic import BaseModel, computed_field

    class Rectangle(BaseModel):
        width: int
        length: int

        @computed_field
        @property
        def area(self) -> int:
            return self.width * self.length

    print(Rectangle(width=3, length=2).model_dump())
    #> {'width': 3, 'length': 2, 'area': 6}
    ```

    If applied to functions not yet decorated with `@property` or `@cached_property`, the function is
    automatically wrapped with `property`. Although this is more concise, you will lose IntelliSense in your IDE,
    and confuse static type checkers, thus explicit use of `@property` is recommended.

    !!! warning "Mypy Warning"
        Even with the `@property` or `@cached_property` applied to your function before `@computed_field`,
        mypy may throw a `Decorated property not supported` error.
        See [mypy issue #1362](https://github.com/python/mypy/issues/1362), for more information.
        To avoid this error message, add `# type: ignore[prop-decorator]` to the `@computed_field` line.

        [pyright](https://github.com/microsoft/pyright) supports `@computed_field` without error.

    ```python
    import random

    from pydantic import BaseModel, computed_field

    class Square(BaseModel):
        width: float

        @computed_field
        def area(self) -> float:  # converted to a `property` by `computed_field`
            return round(self.width**2, 2)

        @area.setter
        def area(self, new_area: float) -> None:
            self.width = new_area**0.5

        @computed_field(alias='the magic number', repr=False)
        def random_number(self) -> int:
            return random.randint(0, 1_000)

    square = Square(width=1.3)

    # `random_number` does not appear in representation
    print(repr(square))
    #> Square(width=1.3, area=1.69)

    print(square.random_number)
    #> 3

    square.area = 4

    print(square.model_dump_json(by_alias=True))
    #> {"width":2.0,"area":4.0,"the magic number":3}
    ```

    !!! warning "Overriding with `computed_field`"
        You can't override a field from a parent class with a `computed_field` in the child class.
        `mypy` complains about this behavior if allowed, and `dataclasses` doesn't allow this pattern either.
        See the example below:

    ```python
    from pydantic import BaseModel, computed_field

    class Parent(BaseModel):
        a: str

    try:

        class Child(Parent):
            @computed_field
            @property
            def a(self) -> str:
                return 'new a'

    except TypeError as e:
        print(e)
        '''
        Field 'a' of class 'Child' overrides symbol of same name in a parent class. This override with a computed_field is incompatible.
        '''
    ```

    Private properties decorated with `@computed_field` have `repr=False` by default.

    ```python
    from functools import cached_property

    from pydantic import BaseModel, computed_field

    class Model(BaseModel):
        foo: int

        @computed_field
        @cached_property
        def _private_cached_property(self) -> int:
            return -self.foo

        @computed_field
        @property
        def _private_property(self) -> int:
            return -self.foo

    m = Model(foo=1)
    print(repr(m))
    #> Model(foo=1)
    ```

    Args:
        func: the function to wrap.
        alias: alias to use when serializing this computed field, only used when `by_alias=True`
        alias_priority: priority of the alias. This affects whether an alias generator is used
        title: Title to use when including this computed field in JSON Schema
        field_title_generator: A callable that takes a field name and returns title for it.
        description: Description to use when including this computed field in JSON Schema, defaults to the function's
            docstring
        deprecated: A deprecation message (or an instance of `warnings.deprecated` or the `typing_extensions.deprecated` backport).
            to be emitted when accessing the field. Or a boolean. This will automatically be set if the property is decorated with the
            `deprecated` decorator.
        examples: Example values to use when including this computed field in JSON Schema
        json_schema_extra: A dict or callable to provide extra JSON schema properties.
        repr: whether to include this computed field in model repr.
            Default is `False` for private properties and `True` for public properties.
        return_type: optional return for serialization logic to expect when serializing to JSON, if included
            this must be correct, otherwise a `TypeError` is raised.
            If you don't include a return type Any is used, which does runtime introspection to handle arbitrary
            objects.

    Returns:
        A proxy wrapper for the property.
    """

    def dec(f: Any) -> Any:
        nonlocal description, deprecated, return_type, alias_priority
        unwrapped = _decorators.unwrap_wrapped_function(f)

        if description is None and unwrapped.__doc__:
            description = inspect.cleandoc(unwrapped.__doc__)

        if deprecated is None and hasattr(unwrapped, '__deprecated__'):
            deprecated = unwrapped.__deprecated__

        # if the function isn't already decorated with `@property` (or another descriptor), then we wrap it now
        f = _decorators.ensure_property(f)
        alias_priority = (alias_priority or 2) if alias is not None else None

        if repr is None:
            repr_: bool = not _wrapped_property_is_private(property_=f)
        else:
            repr_ = repr

        dec_info = ComputedFieldInfo(
            f,
            return_type,
            alias,
            alias_priority,
            title,
            field_title_generator,
            description,
            deprecated,
            examples,
            json_schema_extra,
            repr_,
        )
        return _decorators.PydanticDescriptorProxy(f, dec_info)

    if func is None:
        return dec
    else:
        return dec(func)

# === NexusCore/openenv\Lib\site-packages\blessed\terminal.py ===
# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines
"""Module containing :class:`Terminal`, the primary API entry point."""
# std imports
import os
import re
import sys
import time
import codecs
import locale
import select
import struct
import platform
import warnings
import contextlib
import collections

# local
from .color import COLOR_DISTANCE_ALGORITHMS
from .keyboard import (DEFAULT_ESCDELAY,
                       _time_left,
                       _read_until,
                       resolve_sequence,
                       get_keyboard_codes,
                       get_leading_prefixes,
                       get_keyboard_sequences)
from .sequences import Termcap, Sequence, SequenceTextWrapper
from .colorspace import RGB_256TABLE
from .formatters import (COLORS,
                         COMPOUNDABLES,
                         FormattingString,
                         NullCallableString,
                         ParameterizingString,
                         FormattingOtherString,
                         split_compound,
                         resolve_attribute,
                         resolve_capability)
from ._capabilities import CAPABILITY_DATABASE, CAPABILITIES_ADDITIVES, CAPABILITIES_RAW_MIXIN

# isort: off

# Alias py2 exception to py3
if sys.version_info[:2] < (3, 3):
    InterruptedError = select.error  # pylint: disable=redefined-builtin


HAS_TTY = True
if platform.system() == 'Windows':
    IS_WINDOWS = True
    import jinxed as curses  # pylint: disable=import-error
    from jinxed.win32 import get_console_input_encoding  # pylint: disable=import-error
else:
    IS_WINDOWS = False
    import curses

    try:
        import fcntl
        import termios
        import tty
    except ImportError:
        _TTY_METHODS = ('setraw', 'cbreak', 'kbhit', 'height', 'width')
        _MSG_NOSUPPORT = (
            "One or more of the modules: 'termios', 'fcntl', and 'tty' "
            "are not found on your platform '{platform}'. "
            "The following methods of Terminal are dummy/no-op "
            "unless a deriving class overrides them: {tty_methods}."
            .format(platform=platform.system(),
                    tty_methods=', '.join(_TTY_METHODS)))
        warnings.warn(_MSG_NOSUPPORT)
        HAS_TTY = False

_CUR_TERM = None  # See comments at end of file


class Terminal(object):
    """
    An abstraction for color, style, positioning, and input in the terminal.

    This keeps the endless calls to ``tigetstr()`` and ``tparm()`` out of your code, acts
    intelligently when somebody pipes your output to a non-terminal, and abstracts over the
    complexity of unbuffered keyboard input. It uses the terminfo database to remain portable across
    terminal types.
    """
    # pylint: disable=too-many-instance-attributes,too-many-public-methods
    #         Too many public methods (28/20)
    #         Too many instance attributes (12/7)

    #: Sugary names for commonly-used capabilities
    _sugar = {
        'save': 'sc',
        'restore': 'rc',
        'clear_eol': 'el',
        'clear_bol': 'el1',
        'clear_eos': 'ed',
        'enter_fullscreen': 'smcup',
        'exit_fullscreen': 'rmcup',
        'move': 'cup',
        'move_yx': 'cup',
        'move_x': 'hpa',
        'move_y': 'vpa',
        'hide_cursor': 'civis',
        'normal_cursor': 'cnorm',
        'reset_colors': 'op',
        'normal': 'sgr0',
        'reverse': 'rev',
        'italic': 'sitm',
        'no_italic': 'ritm',
        'shadow': 'sshm',
        'no_shadow': 'rshm',
        'standout': 'smso',
        'no_standout': 'rmso',
        'subscript': 'ssubm',
        'no_subscript': 'rsubm',
        'superscript': 'ssupm',
        'no_superscript': 'rsupm',
        'underline': 'smul',
        'no_underline': 'rmul',
        'cursor_report': 'u6',
        'cursor_request': 'u7',
        'terminal_answerback': 'u8',
        'terminal_enquire': 'u9',
    }

    def __init__(self, kind=None, stream=None, force_styling=False):
        """
        Initialize the terminal.

        :arg str kind: A terminal string as taken by :func:`curses.setupterm`.
            Defaults to the value of the ``TERM`` environment variable.

            .. note:: Terminals within a single process must share a common
                ``kind``. See :obj:`_CUR_TERM`.

        :arg file stream: A file-like object representing the Terminal output.
            Defaults to the original value of :obj:`sys.__stdout__`, like
            :func:`curses.initscr` does.

            If ``stream`` is not a tty, empty Unicode strings are returned for
            all capability values, so things like piping your program output to
            a pipe or file does not emit terminal sequences.

        :arg bool force_styling: Whether to force the emission of capabilities
            even if :obj:`sys.__stdout__` does not seem to be connected to a
            terminal. If you want to force styling to not happen, use
            ``force_styling=None``.

            This comes in handy if users are trying to pipe your output through
            something like ``less -r`` or build systems which support decoding
            of terminal sequences.
        """
        # pylint: disable=global-statement,too-many-branches
        global _CUR_TERM
        self.errors = ['parameters: kind=%r, stream=%r, force_styling=%r' %
                       (kind, stream, force_styling)]
        self._normal = None  # cache normal attr, preventing recursive lookups
        # we assume our input stream to be line-buffered until either the
        # cbreak of raw context manager methods are entered with an attached tty.
        self._line_buffered = True

        self._stream = stream
        self._keyboard_fd = None
        self._init_descriptor = None
        self._is_a_tty = False
        self.__init__streams()

        if IS_WINDOWS and self._init_descriptor is not None:
            self._kind = kind or curses.get_term(self._init_descriptor)
        else:
            self._kind = kind or os.environ.get('TERM', 'dumb') or 'dumb'

        self._does_styling = False
        if force_styling is None and self.is_a_tty:
            self.errors.append('force_styling is None')
        elif force_styling or self.is_a_tty:
            self._does_styling = True

        if self.does_styling:
            # Initialize curses (call setupterm), so things like tigetstr() work.
            try:
                curses.setupterm(self._kind, self._init_descriptor)
            except curses.error as err:
                msg = 'Failed to setupterm(kind={0!r}): {1}'.format(self._kind, err)
                warnings.warn(msg)
                self.errors.append(msg)
                self._kind = None
                self._does_styling = False
            else:
                if _CUR_TERM is None or self._kind == _CUR_TERM:
                    _CUR_TERM = self._kind
                else:
                    # termcap 'kind' is immutable in a python process! Once
                    # initialized by setupterm, it is unsupported by the
                    # 'curses' module to change the terminal type again. If you
                    # are a downstream developer and you need this
                    # functionality, consider sub-processing, instead.
                    warnings.warn(
                        'A terminal of kind "%s" has been requested; due to an'
                        ' internal python curses bug, terminal capabilities'
                        ' for a terminal of kind "%s" will continue to be'
                        ' returned for the remainder of this process.' % (
                            self._kind, _CUR_TERM,))

        self.__init__color_capabilities()
        self.__init__capabilities()
        self.__init__keycodes()

    def __init__streams(self):
        # pylint: disable=too-complex,too-many-branches
        #         Agree to disagree !
        stream_fd = None

        # Default stream is stdout
        if self._stream is None:
            self._stream = sys.__stdout__

        if not hasattr(self._stream, 'fileno'):
            self.errors.append('stream has no fileno method')
        elif not callable(self._stream.fileno):
            self.errors.append('stream.fileno is not callable')
        else:
            try:
                stream_fd = self._stream.fileno()
            except ValueError as err:
                # The stream is not a file, such as the case of StringIO, or, when it has been
                # "detached", such as might be the case of stdout in some test scenarios.
                self.errors.append('Unable to determine output stream file descriptor: %s' % err)
            else:
                self._is_a_tty = os.isatty(stream_fd)
                if not self._is_a_tty:
                    self.errors.append('stream not a TTY')

        # Keyboard valid as stdin only when output stream is stdout or stderr and is a tty.
        if self._stream in (sys.__stdout__, sys.__stderr__):
            try:
                self._keyboard_fd = sys.__stdin__.fileno()
            except (AttributeError, ValueError) as err:
                self.errors.append('Unable to determine input stream file descriptor: %s' % err)
            else:
                # _keyboard_fd only non-None if both stdin and stdout is a tty.
                if not self.is_a_tty:
                    self.errors.append('Output stream is not a TTY')
                    self._keyboard_fd = None
                elif not os.isatty(self._keyboard_fd):
                    self.errors.append('Input stream is not a TTY')
                    self._keyboard_fd = None
        else:
            self.errors.append('Output stream is not a default stream')

        # The descriptor to direct terminal initialization sequences to.
        self._init_descriptor = stream_fd
        if stream_fd is None:
            try:
                self._init_descriptor = sys.__stdout__.fileno()
            except ValueError as err:
                self.errors.append('Unable to determine __stdout__ file descriptor: %s' % err)

    def __init__color_capabilities(self):
        self._color_distance_algorithm = 'cie2000'
        if not self.does_styling:
            self.number_of_colors = 0
        elif IS_WINDOWS or os.environ.get('COLORTERM') in ('truecolor', '24bit'):
            self.number_of_colors = 1 << 24
        else:
            self.number_of_colors = max(0, curses.tigetnum('colors') or -1)

    def __clear_color_capabilities(self):
        for cached_color_cap in set(dir(self)) & COLORS:
            delattr(self, cached_color_cap)

    def __init__capabilities(self):
        # important that we lay these in their ordered direction, so that our
        # preferred, 'color' over 'set_a_attributes1', for example.
        self.caps = collections.OrderedDict()

        # some static injected patterns, esp. without named attribute access.
        for name, (attribute, pattern) in CAPABILITIES_ADDITIVES.items():
            self.caps[name] = Termcap(name, pattern, attribute)

        for name, (attribute, kwds) in CAPABILITY_DATABASE.items():
            if self.does_styling:
                # attempt dynamic lookup
                cap = getattr(self, attribute)
                if cap:
                    self.caps[name] = Termcap.build(
                        name, cap, attribute, **kwds)
                    continue

            # fall-back
            pattern = CAPABILITIES_RAW_MIXIN.get(name)
            if pattern:
                self.caps[name] = Termcap(name, pattern, attribute)

        # make a compiled named regular expression table
        self.caps_compiled = re.compile(
            '|'.join(cap.pattern for name, cap in self.caps.items()))

        # for tokenizer, the '.lastgroup' is the primary lookup key for
        # 'self.caps', unless 'MISMATCH'; then it is an unmatched character.
        self._caps_compiled_any = re.compile('|'.join(
            cap.named_pattern for name, cap in self.caps.items()
        ) + '|(?P<MISMATCH>.)')
        self._caps_unnamed_any = re.compile('|'.join(
            '({0})'.format(cap.pattern) for name, cap in self.caps.items()
        ) + '|(.)')

    def __init__keycodes(self):
        # Initialize keyboard data determined by capability.
        # Build database of int code <=> KEY_NAME.
        self._keycodes = get_keyboard_codes()

        # Store attributes as: self.KEY_NAME = code.
        for key_code, key_name in self._keycodes.items():
            setattr(self, key_name, key_code)

        # Build database of sequence <=> KEY_NAME.
        self._keymap = get_keyboard_sequences(self)

        # build set of prefixes of sequences
        self._keymap_prefixes = get_leading_prefixes(self._keymap)

        # keyboard stream buffer
        self._keyboard_buf = collections.deque()

        if self._keyboard_fd is not None:
            # set input encoding and initialize incremental decoder

            if IS_WINDOWS:
                # pylint: disable-next=possibly-used-before-assignment
                self._encoding = get_console_input_encoding() \
                    or locale.getpreferredencoding() or 'UTF-8'
            else:
                self._encoding = locale.getpreferredencoding() or 'UTF-8'

            try:
                self._keyboard_decoder = codecs.getincrementaldecoder(self._encoding)()
            except LookupError as err:
                # encoding is illegal or unsupported, use 'UTF-8'
                warnings.warn('LookupError: {0}, defaulting to UTF-8 for keyboard.'.format(err))
                self._encoding = 'UTF-8'
                self._keyboard_decoder = codecs.getincrementaldecoder(self._encoding)()

    def __getattr__(self, attr):
        r"""
        Return a terminal capability as Unicode string.

        For example, ``term.bold`` is a unicode string that may be prepended
        to text to set the video attribute for bold, which should also be
        terminated with the pairing :attr:`normal`. This capability
        returns a callable, so you can use ``term.bold("hi")`` which
        results in the joining of ``(term.bold, "hi", term.normal)``.

        Compound formatters may also be used. For example::

            >>> term.bold_blink_red_on_green("merry x-mas!")

        For a parameterized capability such as ``move`` (or ``cup``), pass the
        parameters as positional arguments::

            >>> term.move(line, column)

        See the manual page `terminfo(5)
        <https://invisible-island.net/ncurses/man/terminfo.5.html>`_ for a
        complete list of capabilities and their arguments.
        """
        if not self._does_styling:
            return NullCallableString()
        # Fetch the missing 'attribute' into some kind of curses-resolved
        # capability, and cache by attaching to this Terminal class instance.
        #
        # Note that this will prevent future calls to __getattr__(), but
        # that's precisely the idea of the cache!
        val = resolve_attribute(self, attr)
        setattr(self, attr, val)
        return val

    @property
    def kind(self):
        """
        Read-only property: Terminal kind determined on class initialization.

        :rtype: str
        """
        return self._kind

    @property
    def does_styling(self):
        """
        Read-only property: Whether this class instance may emit sequences.

        :rtype: bool
        """
        return self._does_styling

    @property
    def is_a_tty(self):
        """
        Read-only property: Whether :attr:`~.stream` is a terminal.

        :rtype: bool
        """
        return self._is_a_tty

    @property
    def height(self):
        """
        Read-only property: Height of the terminal (in number of lines).

        :rtype: int
        """
        return self._height_and_width().ws_row

    @property
    def width(self):
        """
        Read-only property: Width of the terminal (in number of columns).

        :rtype: int
        """
        return self._height_and_width().ws_col

    @property
    def pixel_height(self):
        """
        Read-only property: Height ofthe terminal (in pixels).

        :rtype: int
        """
        return self._height_and_width().ws_ypixel

    @property
    def pixel_width(self):
        """
        Read-only property: Width of terminal (in pixels).

        :rtype: int
        """
        return self._height_and_width().ws_xpixel

    @staticmethod
    def _winsize(fd):
        """
        Return named tuple describing size of the terminal by ``fd``.

        If the given platform does not have modules :mod:`termios`,
        :mod:`fcntl`, or :mod:`tty`, window size of 80 columns by 25
        rows is always returned.

        :arg int fd: file descriptor queries for its window size.
        :raises IOError: the file descriptor ``fd`` is not a terminal.
        :rtype: WINSZ
        :returns: named tuple describing size of the terminal

        WINSZ is a :class:`collections.namedtuple` instance, whose structure
        directly maps to the return value of the :const:`termios.TIOCGWINSZ`
        ioctl return value. The return parameters are:

            - ``ws_row``: width of terminal by its number of character cells.
            - ``ws_col``: height of terminal by its number of character cells.
            - ``ws_xpixel``: width of terminal by pixels (not accurate).
            - ``ws_ypixel``: height of terminal by pixels (not accurate).
        """
        if HAS_TTY:
            # pylint: disable=protected-access,possibly-used-before-assignment
            data = fcntl.ioctl(fd, termios.TIOCGWINSZ, WINSZ._BUF)
            return WINSZ(*struct.unpack(WINSZ._FMT, data))
        return WINSZ(ws_row=25, ws_col=80, ws_xpixel=0, ws_ypixel=0)

    def _height_and_width(self):
        """
        Return a tuple of (terminal height, terminal width).

        If :attr:`stream` or :obj:`sys.__stdout__` is not a tty or does not
        support :func:`fcntl.ioctl` of :const:`termios.TIOCGWINSZ`, a window
        size of 80 columns by 25 rows is returned for any values not
        represented by environment variables ``LINES`` and ``COLUMNS``, which
        is the default text mode of IBM PC compatibles.

        :rtype: WINSZ
        :returns: Named tuple specifying the terminal size

        WINSZ is a :class:`collections.namedtuple` instance, whose structure
        directly maps to the return value of the :const:`termios.TIOCGWINSZ`
        ioctl return value. The return parameters are:

            - ``ws_row``: height of terminal by its number of cell rows.
            - ``ws_col``: width of terminal by its number of cell columns.
            - ``ws_xpixel``: width of terminal by pixels (not accurate).
            - ``ws_ypixel``: height of terminal by pixels (not accurate).

            .. note:: the peculiar (height, width, width, height) order, which
               matches the return order of TIOCGWINSZ!
        """
        for fd in (self._init_descriptor, sys.__stdout__):
            try:
                if fd is not None:
                    return self._winsize(fd)
            except (IOError, OSError, ValueError, TypeError):  # pylint: disable=overlapping-except
                pass

        return WINSZ(ws_row=int(os.getenv('LINES', '25')),
                     ws_col=int(os.getenv('COLUMNS', '80')),
                     ws_xpixel=None,
                     ws_ypixel=None)

    def _query_response(self, query_str, response_re, timeout):
        """
        Sends a query string to the terminal and waits for a response.

        :arg str query_str: Query string written to output
        :arg str response_re: Regular expression matching query response
        :arg float timeout: Return after time elapsed in seconds
        :return: re.match object for response_re or None if not found
        :rtype: re.Match
        """
        # Avoid changing user's desired raw or cbreak mode if already entered,
        # by entering cbreak mode ourselves.  This is necessary to receive user
        # input without awaiting a human to press the return key.   This mode
        # also disables echo, which we should also hide, as our input is an
        # sequence that is not meaningful for display as an output sequence.

        ctx = None
        try:
            if self._line_buffered:
                ctx = self.cbreak()
                ctx.__enter__()  # pylint: disable=no-member

            # Emit the query sequence,
            self.stream.write(query_str)
            self.stream.flush()

            # Wait for response
            match, data = _read_until(term=self,  # pylint: disable=unpacking-non-sequence
                                      pattern=response_re,
                                      timeout=timeout)

            # Exclude response from subsequent input
            if match:
                data = data[:match.start()] + data[match.end():]

            # re-buffer keyboard data, if any
            self.ungetch(data)

        finally:
            if ctx is not None:
                ctx.__exit__(None, None, None)  # pylint: disable=no-member

        return match

    @contextlib.contextmanager
    def location(self, x=None, y=None):
        """
        Context manager for temporarily moving the cursor.

        :arg int x: horizontal position, from left, *0*, to right edge of screen, *self.width - 1*.
        :arg int y: vertical position, from top, *0*, to bottom of screen, *self.height - 1*.
        :return: a context manager.
        :rtype: Iterator

        Move the cursor to a certain position on entry, do any kind of I/O, and upon exit
        let you print stuff there, then return the cursor to its original position:


        .. code-block:: python

            term = Terminal()
            with term.location(y=0, x=0):
                for row_num in range(term.height-1):
                    print('Row #{row_num}')
            print(term.clear_eol + 'Back to original location.')

        Specify ``x`` to move to a certain column, ``y`` to move to a certain
        row, both, or neither. If you specify neither, only the saving and
        restoration of cursor position will happen. This can be useful if you
        simply want to restore your place after doing some manual cursor
        movement.

        Calls cannot be nested: only one should be entered at a time.

        .. note:: The argument order *(x, y)* differs from the return value order *(y, x)*
            of :meth:`get_location`, or argument order *(y, x)* of :meth:`move`. This is
            for API Compaibility with the blessings library, sorry for the trouble!
        """
        # pylint: disable=invalid-name
        #         Invalid argument name "x"

        # Save position and move to the requested column, row, or both:
        self.stream.write(self.save)
        if x is not None and y is not None:
            self.stream.write(self.move(y, x))
        elif x is not None:
            self.stream.write(self.move_x(x))
        elif y is not None:
            self.stream.write(self.move_y(y))
        try:
            self.stream.flush()
            yield
        finally:
            # Restore original cursor position:
            self.stream.write(self.restore)
            self.stream.flush()

    def get_location(self, timeout=None):
        r"""
        Return tuple (row, column) of cursor position.

        :arg float timeout: Return after time elapsed in seconds with value ``(-1, -1)`` indicating
            that the remote end did not respond.
        :rtype: tuple
        :returns: cursor position as tuple in form of ``(y, x)``.  When a timeout is specified,
            always ensure the return value is checked for ``(-1, -1)``.

        The location of the cursor is determined by emitting the ``u7`` terminal capability, or
        VT100 `Query Cursor Position
        <https://www2.ccs.neu.edu/research/gpc/VonaUtils/vona/terminal/vtansi.htm#status>`_
        when such capability is undefined, which elicits a response from a reply string described by
        capability ``u6``, or again VT100's definition of ``\x1b[%i%d;%dR`` when undefined.

        The ``(y, x)`` return value matches the parameter order of the :meth:`move_yx` capability.
        The following sequence should cause the cursor to not move at all::

            >>> term = Terminal()
            >>> term.move_yx(*term.get_location()))

        And the following should assert True with a terminal:

            >>> term = Terminal()
            >>> given_y, given_x = 10, 20
            >>> with term.location(y=given_y, x=given_x):
            ...     result_y, result_x = term.get_location()
            ...
            >>> assert given_x == result_x, (given_x, result_x)
            >>> assert given_y == result_y, (given_y, result_y)
        """
        # Local lines attached by termios and remote login protocols such as
        # ssh and telnet both provide a means to determine the window
        # dimensions of a connected client, but **no means to determine the
        # location of the cursor**.
        #
        # from https://invisible-island.net/ncurses/terminfo.src.html,
        #
        # > The System V Release 4 and XPG4 terminfo format defines ten string
        # > capabilities for use by applications, <u0>...<u9>.   In this file,
        # > we use certain of these capabilities to describe functions which
        # > are not covered by terminfo.  The mapping is as follows:
        # >
        # >  u9   terminal enquire string (equiv. to ANSI/ECMA-48 DA)
        # >  u8   terminal answerback description
        # >  u7   cursor position request (equiv. to VT100/ANSI/ECMA-48 DSR 6)
        # >  u6   cursor position report (equiv. to ANSI/ECMA-48 CPR)

        response_str = getattr(self, self.caps['cursor_report'].attribute) or u'\x1b[%i%d;%dR'
        match = self._query_response(
            self.u7 or u'\x1b[6n', self.caps['cursor_report'].re_compiled, timeout
        )

        if match:
            # return matching sequence response, the cursor location.
            row, col = (int(val) for val in match.groups())

            # Per https://invisible-island.net/ncurses/terminfo.src.html
            # The cursor position report (<u6>) string must contain two
            # scanf(3)-style %d format elements.  The first of these must
            # correspond to the Y coordinate and the second to the %d.
            # If the string contains the sequence %i, it is taken as an
            # instruction to decrement each value after reading it (this is
            # the inverse sense from the cup string).
            if u'%i' in response_str:
                row -= 1
                col -= 1
            return row, col

        # We chose to return an illegal value rather than an exception,
        # favoring that users author function filters, such as max(0, y),
        # rather than crowbarring such logic into an exception handler.
        return -1, -1

    def get_fgcolor(self, timeout=None):
        """
        Return tuple (r, g, b) of foreground color.

        :arg float timeout: Return after time elapsed in seconds with value ``(-1, -1, -1)``
            indicating that the remote end did not respond.
        :rtype: tuple
        :returns: foreground color as tuple in form of ``(r, g, b)``.  When a timeout is specified,
            always ensure the return value is checked for ``(-1, -1, -1)``.

        The foreground color is determined by emitting an `OSC 10 color query
        <https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Operating-System-Commands>`_.
        """
        match = self._query_response(
            u'\x1b]10;?\x07',
            re.compile(u'\x1b]10;rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)\x07'),
            timeout
        )

        return tuple(int(val, 16) for val in match.groups()) if match else (-1, -1, -1)

    def get_bgcolor(self, timeout=None):
        """
        Return tuple (r, g, b) of background color.

        :arg float timeout: Return after time elapsed in seconds with value ``(-1, -1, -1)``
            indicating that the remote end did not respond.
        :rtype: tuple
        :returns: background color as tuple in form of ``(r, g, b)``.  When a timeout is specified,
            always ensure the return value is checked for ``(-1, -1, -1)``.

        The background color is determined by emitting an `OSC 11 color query
        <https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Operating-System-Commands>`_.
        """
        match = self._query_response(
            u'\x1b]11;?\x07',
            re.compile(u'\x1b]11;rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)\x07'),
            timeout
        )

        return tuple(int(val, 16) for val in match.groups()) if match else (-1, -1, -1)

    @contextlib.contextmanager
    def fullscreen(self):
        """
        Context manager that switches to secondary screen, restoring on exit.

        Under the hood, this switches between the primary screen buffer and
        the secondary one. The primary one is saved on entry and restored on
        exit.  Likewise, the secondary contents are also stable and are
        faithfully restored on the next entry::

            with term.fullscreen():
                main()

        .. note:: There is only one primary and one secondary screen buffer.
           :meth:`fullscreen` calls cannot be nested, only one should be
           entered at a time.
        """
        self.stream.write(self.enter_fullscreen)
        self.stream.flush()
        try:
            yield
        finally:
            self.stream.write(self.exit_fullscreen)
            self.stream.flush()

    @contextlib.contextmanager
    def hidden_cursor(self):
        """
        Context manager that hides the cursor, setting visibility on exit.

            with term.hidden_cursor():
                main()

        .. note:: :meth:`hidden_cursor` calls cannot be nested: only one
            should be entered at a time.
        """
        self.stream.write(self.hide_cursor)
        self.stream.flush()
        try:
            yield
        finally:
            self.stream.write(self.normal_cursor)
            self.stream.flush()

    def move_xy(self, x, y):
        """
        A callable string that moves the cursor to the given ``(x, y)`` screen coordinates.

        :arg int x: horizontal position, from left, *0*, to right edge of screen, *self.width - 1*.
        :arg int y: vertical position, from top, *0*, to bottom of screen, *self.height - 1*.
        :rtype: ParameterizingString
        :returns: Callable string that moves the cursor to the given coordinates
        """
        # this is just a convenience alias to the built-in, but hidden 'move'
        # attribute -- we encourage folks to use only (x, y) positional
        # arguments, or, if they must use (y, x), then use the 'move_yx'
        # alias.
        return self.move(y, x)

    def move_yx(self, y, x):
        """
        A callable string that moves the cursor to the given ``(y, x)`` screen coordinates.

        :arg int y: vertical position, from top, *0*, to bottom of screen, *self.height - 1*.
        :arg int x: horizontal position, from left, *0*, to right edge of screen, *self.width - 1*.
        :rtype: ParameterizingString
        :returns: Callable string that moves the cursor to the given coordinates
        """
        return self.move(y, x)

    @property
    def move_left(self):
        """Move cursor 1 cells to the left, or callable string for n>1 cells."""
        return FormattingOtherString(self.cub1, ParameterizingString(self.cub))

    @property
    def move_right(self):
        """Move cursor 1 or more cells to the right, or callable string for n>1 cells."""
        return FormattingOtherString(self.cuf1, ParameterizingString(self.cuf))

    @property
    def move_up(self):
        """Move cursor 1 or more cells upwards, or callable string for n>1 cells."""
        return FormattingOtherString(self.cuu1, ParameterizingString(self.cuu))

    @property
    def move_down(self):
        """Move cursor 1 or more cells downwards, or callable string for n>1 cells."""
        return FormattingOtherString(self.cud1, ParameterizingString(self.cud))

    @property
    def color(self):
        """
        A callable string that sets the foreground color.

        :rtype: ParameterizingString

        The capability is unparameterized until called and passed a number, at which point it
        returns another string which represents a specific color change. This second string can
        further be called to color a piece of text and set everything back to normal afterward.

        This should not be used directly, but rather a specific color by name or
        :meth:`~.Terminal.color_rgb` value.
        """
        if self.does_styling:
            return ParameterizingString(self._foreground_color, self.normal, 'color')

        return NullCallableString()

    def color_rgb(self, red, green, blue):
        """
        Provides callable formatting string to set foreground color to the specified RGB color.

        :arg int red: RGB value of Red.
        :arg int green: RGB value of Green.
        :arg int blue: RGB value of Blue.
        :rtype: FormattingString
        :returns: Callable string that sets the foreground color

        If the terminal does not support RGB color, the nearest supported
        color will be determined using :py:attr:`color_distance_algorithm`.
        """
        if self.number_of_colors == 1 << 24:
            # "truecolor" 24-bit
            fmt_attr = u'\x1b[38;2;{0};{1};{2}m'.format(red, green, blue)
            return FormattingString(fmt_attr, self.normal)

        # color by approximation to 256 or 16-color terminals
        color_idx = self.rgb_downconvert(red, green, blue)
        return FormattingString(self._foreground_color(color_idx), self.normal)

    @property
    def on_color(self):
        """
        A callable capability that sets the background color.

        :rtype: ParameterizingString
        """
        if self.does_styling:
            return ParameterizingString(self._background_color, self.normal, 'on_color')

        return NullCallableString()

    def on_color_rgb(self, red, green, blue):
        """
        Provides callable formatting string to set background color to the specified RGB color.

        :arg int red: RGB value of Red.
        :arg int green: RGB value of Green.
        :arg int blue: RGB value of Blue.
        :rtype: FormattingString
        :returns: Callable string that sets the foreground color

        If the terminal does not support RGB color, the nearest supported
        color will be determined using :py:attr:`color_distance_algorithm`.
        """
        if self.number_of_colors == 1 << 24:
            fmt_attr = u'\x1b[48;2;{0};{1};{2}m'.format(red, green, blue)
            return FormattingString(fmt_attr, self.normal)

        color_idx = self.rgb_downconvert(red, green, blue)
        return FormattingString(self._background_color(color_idx), self.normal)

    def formatter(self, value):
        """
        Provides callable formatting string to set color and other text formatting options.

        :arg str value: Sugary, ordinary, or compound formatted terminal capability,
            such as "red_on_white", "normal", "red", or "bold_on_black".
        :rtype: :class:`FormattingString` or :class:`NullCallableString`
        :returns: Callable string that sets color and other text formatting options

        Calling ``term.formatter('bold_on_red')`` is equivalent to ``term.bold_on_red``, but a
        string that is not a valid text formatter will return a :class:`NullCallableString`.
        This is intended to allow validation of text formatters without the possibility of
        inadvertently returning another terminal capability.
        """
        formatters = split_compound(value)
        # Pylint sometimes thinks formatters isn't a list  # pylint: disable=not-an-iterable
        if all((fmt in COLORS or fmt in COMPOUNDABLES) for fmt in formatters):
            return getattr(self, value)

        return NullCallableString()

    def rgb_downconvert(self, red, green, blue):
        """
        Translate an RGB color to a color code of the terminal's color depth.

        :arg int red: RGB value of Red (0-255).
        :arg int green: RGB value of Green (0-255).
        :arg int blue: RGB value of Blue (0-255).
        :rtype: int
        :returns: Color code of downconverted RGB color
        """
        # Though pre-computing all 1 << 24 options is memory-intensive, a pre-computed
        # "k-d tree" of 256 (x,y,z) vectors of a colorspace in 3 dimensions, such as a
        # cone of HSV, or simply 255x255x255 RGB square, any given rgb value is just a
        # nearest-neighbor search of 256 points, which k-d should be much faster by
        # sub-dividing / culling search points, rather than our "search all 256 points
        # always" approach.
        fn_distance = COLOR_DISTANCE_ALGORITHMS[self.color_distance_algorithm]
        color_idx = 7
        shortest_distance = None
        for cmp_depth, cmp_rgb in enumerate(RGB_256TABLE):
            cmp_distance = fn_distance(cmp_rgb, (red, green, blue))
            if shortest_distance is None or cmp_distance < shortest_distance:
                shortest_distance = cmp_distance
                color_idx = cmp_depth
            if cmp_depth >= self.number_of_colors:
                break
        return color_idx

    @property
    def normal(self):
        """
        A capability that resets all video attributes.

        :rtype: str

        ``normal`` is an alias for ``sgr0`` or ``exit_attribute_mode``. Any
        styling attributes previously applied, such as foreground or
        background colors, reverse video, or bold are reset to defaults.
        """
        if self._normal:
            return self._normal
        self._normal = resolve_capability(self, 'normal')
        return self._normal

    def link(self, url, text, url_id=''):
        """
        Display ``text`` that when touched or clicked, navigates to ``url``.

        Optional ``url_id`` may be specified, so that non-adjacent cells can reference a single
        target, all cells painted with the same "id" will highlight on hover, rather than any
        individual one, as described in "Hovering and underlining the id parameter" of gist
        https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda.

        :param str url: Hyperlink URL.
        :param str text: Clickable text.
        :param str url_id: Optional 'id'.
        :rtype: str
        :returns: String of ``text`` as a hyperlink to ``url``.
        """
        assert len(url) < 2000, (len(url), url)
        if url_id:
            assert len(str(url_id)) < 250, (len(str(url_id)), url_id)
            params = 'id={0}'.format(url_id)
        else:
            params = ''
        if not self.does_styling:
            return text
        return ('\x1b]8;{0};{1}\x1b\\{2}'
                '\x1b]8;;\x1b\\'.format(params, url, text))

    @property
    def stream(self):
        """
        Read-only property: stream the terminal outputs to.

        This is a convenience attribute. It is used internally for implied
        writes performed by context managers :meth:`~.hidden_cursor`,
        :meth:`~.fullscreen`, :meth:`~.location`, and :meth:`~.keypad`.
        """
        return self._stream

    @property
    def number_of_colors(self):
        """
        Number of colors supported by terminal.

        Common return values are 0, 8, 16, 256, or 1 << 24.

        This may be used to test whether the terminal supports colors, and at what depth, if that's
        a concern.

        If this property is assigned a value of 88, the value 16 will be saved. This is due to the
        the rarity of 88 color support and the inconsistency of behavior between implementations.

        Assigning this property to a value other than 0, 4, 8, 16, 88, 256, or 1 << 24 will raise an
        :py:exc:`AssertionError`.
        """
        return self._number_of_colors

    @number_of_colors.setter
    def number_of_colors(self, value):
        assert value in (0, 4, 8, 16, 88, 256, 1 << 24)
        # Because 88 colors is rare and we can't guarantee consistent behavior,
        # when 88 colors is detected, it is treated as 16 colors
        self._number_of_colors = 16 if value == 88 else value
        self.__clear_color_capabilities()

    @property
    def color_distance_algorithm(self):
        """
        Color distance algorithm used by :meth:`rgb_downconvert`.

        The slowest, but most accurate, 'cie2000', is default. Other available options are 'rgb',
        'rgb-weighted', 'cie76', and 'cie94'.
        """
        return self._color_distance_algorithm

    @color_distance_algorithm.setter
    def color_distance_algorithm(self, value):
        assert value in COLOR_DISTANCE_ALGORITHMS
        self._color_distance_algorithm = value
        self.__clear_color_capabilities()

    @property
    def _foreground_color(self):
        """
        Convenience capability to support :attr:`~.on_color`.

        Prefers returning sequence for capability ``setaf``, "Set foreground color to #1, using ANSI
        escape". If the given terminal does not support such sequence, fallback to returning
        attribute ``setf``, "Set foreground color #1".
        """
        return self.setaf or self.setf

    @property
    def _background_color(self):
        """
        Convenience capability to support :attr:`~.on_color`.

        Prefers returning sequence for capability ``setab``, "Set background color to #1, using ANSI
        escape". If the given terminal does not support such sequence, fallback to returning
        attribute ``setb``, "Set background color #1".
        """
        return self.setab or self.setb

    def ljust(self, text, width=None, fillchar=u' '):
        """
        Left-align ``text``, which may contain terminal sequences.

        :arg str text: String to be aligned
        :arg int width: Total width to fill with aligned text. If
            unspecified, the whole width of the terminal is filled.
        :arg str fillchar: String for padding the right of ``text``
        :rtype: str
        :returns: String of ``text``, left-aligned by ``width``.
        """
        # Left justification is different from left alignment, but we continue
        # the vocabulary error of the str method for polymorphism.
        if width is None:
            width = self.width
        return Sequence(text, self).ljust(width, fillchar)

    def rjust(self, text, width=None, fillchar=u' '):
        """
        Right-align ``text``, which may contain terminal sequences.

        :arg str text: String to be aligned
        :arg int width: Total width to fill with aligned text. If
            unspecified, the whole width of the terminal is used.
        :arg str fillchar: String for padding the left of ``text``
        :rtype: str
        :returns: String of ``text``, right-aligned by ``width``.
        """
        if width is None:
            width = self.width
        return Sequence(text, self).rjust(width, fillchar)

    def center(self, text, width=None, fillchar=u' '):
        """
        Center ``text``, which may contain terminal sequences.

        :arg str text: String to be centered
        :arg int width: Total width in which to center text. If
            unspecified, the whole width of the terminal is used.
        :arg str fillchar: String for padding the left and right of ``text``
        :rtype: str
        :returns: String of ``text``, centered by ``width``
        """
        if width is None:
            width = self.width
        return Sequence(text, self).center(width, fillchar)

    def truncate(self, text, width=None):
        r"""
        Truncate ``text`` to maximum ``width`` printable characters, retaining terminal sequences.

        :arg str text: Text to truncate
        :arg int width: The maximum width to truncate it to
        :rtype: str
        :returns: ``text`` truncated to at most ``width`` printable characters

        >>> term.truncate(u'xyz\x1b[0;3m', 2)
        u'xy\x1b[0;3m'
        """
        if width is None:
            width = self.width
        return Sequence(text, self).truncate(width)

    def length(self, text):
        u"""
        Return printable length of a string containing sequences.

        :arg str text: String to measure. May contain terminal sequences.
        :rtype: int
        :returns: The number of terminal character cells the string will occupy
            when printed

        Wide characters that consume 2 character cells are supported:

        >>> term = Terminal()
        >>> term.length(term.clear + term.red(u'コンニチハ'))
        10

        .. note:: Sequences such as 'clear', which is considered as a
            "movement sequence" because it would move the cursor to
            (y, x)(0, 0), are evaluated as a printable length of
            *0*.
        """
        return Sequence(text, self).length()

    def strip(self, text, chars=None):
        r"""
        Return ``text`` without sequences and leading or trailing whitespace.

        :rtype: str
        :returns: Text with leading and trailing whitespace removed

        >>> term.strip(u' \x1b[0;3m xyz ')
        u'xyz'
        """
        return Sequence(text, self).strip(chars)

    def rstrip(self, text, chars=None):
        r"""
        Return ``text`` without terminal sequences or trailing whitespace.

        :rtype: str
        :returns: Text with terminal sequences and trailing whitespace removed

        >>> term.rstrip(u' \x1b[0;3m xyz ')
        u'  xyz'
        """
        return Sequence(text, self).rstrip(chars)

    def lstrip(self, text, chars=None):
        r"""
        Return ``text`` without terminal sequences or leading whitespace.

        :rtype: str
        :returns: Text with terminal sequences and leading whitespace removed

        >>> term.lstrip(u' \x1b[0;3m xyz ')
        u'xyz '
        """
        return Sequence(text, self).lstrip(chars)

    def strip_seqs(self, text):
        r"""
        Return ``text`` stripped of only its terminal sequences.

        :rtype: str
        :returns: Text with terminal sequences removed

        >>> term.strip_seqs(u'\x1b[0;3mxyz')
        u'xyz'
        >>> term.strip_seqs(term.cuf(5) + term.red(u'test'))
        u'     test'

        .. note:: Non-destructive sequences that adjust horizontal distance
            (such as ``\b`` or ``term.cuf(5)``) are replaced by destructive
            space or erasing.
        """
        return Sequence(text, self).strip_seqs()

    def split_seqs(self, text, maxsplit=0):
        r"""
        Return ``text`` split by individual character elements and sequences.

        :arg str text: String containing sequences
        :arg int maxsplit: When maxsplit is nonzero, at most maxsplit splits
            occur, and the remainder of the string is returned as the final element
            of the list (same meaning is argument for :func:`re.split`).
        :rtype: list[str]
        :returns: List of sequences and individual characters

        >>> term.split_seqs(term.underline(u'xyz'))
        ['\x1b[4m', 'x', 'y', 'z', '\x1b(B', '\x1b[m']

        >>> term.split_seqs(term.underline(u'xyz'), 1)
        ['\x1b[4m', r'xyz\x1b(B\x1b[m']
        """
        pattern = self._caps_unnamed_any
        result = []
        for idx, match in enumerate(re.finditer(pattern, text)):
            result.append(match.group())
            if maxsplit and idx == maxsplit:
                remaining = text[match.end():]
                if remaining:
                    result[-1] += remaining
                break
        return result

    def wrap(self, text, width=None, **kwargs):
        r"""
        Text-wrap a string, returning a list of wrapped lines.

        :arg str text: Unlike :func:`textwrap.wrap`, ``text`` may contain
            terminal sequences, such as colors, bold, or underline. By
            default, tabs in ``text`` are expanded by
            :func:`string.expandtabs`.
        :arg int width: Unlike :func:`textwrap.wrap`, ``width`` will
            default to the width of the attached terminal.
        :arg \**kwargs: See :py:class:`textwrap.TextWrapper`
        :rtype: list
        :returns: List of wrapped lines

        See :class:`textwrap.TextWrapper` for keyword arguments that can
        customize wrapping behaviour.
        """
        width = self.width if width is None else width
        wrapper = SequenceTextWrapper(width=width, term=self, **kwargs)
        lines = []
        for line in text.splitlines():
            lines.extend(iter(wrapper.wrap(line)) if line.strip() else (u'',))

        return lines

    def getch(self):
        """
        Read, decode, and return the next byte from the keyboard stream.

        :rtype: unicode
        :returns: a single unicode character, or ``u''`` if a multi-byte
            sequence has not yet been fully received.

        This method name and behavior mimics curses ``getch(void)``, and
        it supports :meth:`inkey`, reading only one byte from
        the keyboard string at a time. This method should always return
        without blocking if called after :meth:`kbhit` has returned True.

        Implementors of alternate input stream methods should override
        this method.
        """
        assert self._keyboard_fd is not None
        byte = os.read(self._keyboard_fd, 1)
        return self._keyboard_decoder.decode(byte, final=False)

    def ungetch(self, text):
        """
        Buffer input data to be discovered by next call to :meth:`~.inkey`.

        :arg str text: String to be buffered as keyboard input.
        """
        self._keyboard_buf.extendleft(text)

    def kbhit(self, timeout=None):
        """
        Return whether a keypress has been detected on the keyboard.

        This method is used by :meth:`inkey` to determine if a byte may
        be read using :meth:`getch` without blocking.  The standard
        implementation simply uses the :func:`select.select` call on stdin.

        :arg float timeout: When ``timeout`` is 0, this call is
            non-blocking, otherwise blocking indefinitely until keypress
            is detected when None (default). When ``timeout`` is a
            positive number, returns after ``timeout`` seconds have
            elapsed (float).
        :rtype: bool
        :returns: True if a keypress is awaiting to be read on the keyboard
            attached to this terminal.  When input is not a terminal, False is
            always returned.
        """
        stime = time.time()
        ready_r = [None, ]
        check_r = [self._keyboard_fd] if self._keyboard_fd is not None else []

        while HAS_TTY:
            try:
                ready_r, _, _ = select.select(check_r, [], [], timeout)
            except InterruptedError:
                # Beginning with python3.5, IntrruptError is no longer thrown
                # https://www.python.org/dev/peps/pep-0475/
                #
                # For previous versions of python, we take special care to
                # retry select on InterruptedError exception, namely to handle
                # a custom SIGWINCH handler. When installed, it would cause
                # select() to be interrupted with errno 4 (EAGAIN).
                #
                # Just as in python3.5, it is ignored, and a new timeout value
                # is derived from the previous unless timeout becomes negative.
                # because the signal handler has blocked beyond timeout, then
                # False is returned. Otherwise, when timeout is None, we
                # continue to block indefinitely (default).
                if timeout is not None:
                    # subtract time already elapsed,
                    timeout -= time.time() - stime
                    if timeout > 0:
                        continue
                    # no time remains after handling exception (rare)
                    ready_r = []        # pragma: no cover
                    break               # pragma: no cover
            else:
                break

        return False if self._keyboard_fd is None else check_r == ready_r

    @contextlib.contextmanager
    def cbreak(self):
        """
        Allow each keystroke to be read immediately after it is pressed.

        This is a context manager for :func:`tty.setcbreak`.

        This context manager activates 'rare' mode, the opposite of 'cooked'
        mode: On entry, :func:`tty.setcbreak` mode is activated disabling
        line-buffering of keyboard input and turning off automatic echo of
        input as output.

        .. note:: You must explicitly print any user input you would like
            displayed.  If you provide any kind of editing, you must handle
            backspace and other line-editing control functions in this mode
            as well!

        **Normally**, characters received from the keyboard cannot be read
        by Python until the *Return* key is pressed. Also known as *cooked* or
        *canonical input* mode, it allows the tty driver to provide
        line-editing before shuttling the input to your program and is the
        (implicit) default terminal mode set by most unix shells before
        executing programs.

        Technically, this context manager sets the :mod:`termios` attributes
        of the terminal attached to :obj:`sys.__stdin__`.

        .. note:: :func:`tty.setcbreak` sets ``VMIN = 1`` and ``VTIME = 0``,
            see http://www.unixwiz.net/techtips/termios-vmin-vtime.html
        """
        if HAS_TTY and self._keyboard_fd is not None:
            # Save current terminal mode:
            save_mode = termios.tcgetattr(self._keyboard_fd)
            save_line_buffered = self._line_buffered
            # pylint: disable-next=possibly-used-before-assignment
            tty.setcbreak(self._keyboard_fd, termios.TCSANOW)
            try:
                self._line_buffered = False
                yield
            finally:
                # Restore prior mode:
                termios.tcsetattr(self._keyboard_fd,
                                  termios.TCSAFLUSH,
                                  save_mode)
                self._line_buffered = save_line_buffered
        else:
            yield

    @contextlib.contextmanager
    def raw(self):
        r"""
        A context manager for :func:`tty.setraw`.

        Although both :meth:`cbreak` and :meth:`raw` modes allow each keystroke
        to be read immediately after it is pressed, Raw mode disables
        processing of input and output.

        In cbreak mode, special input characters such as ``^C`` or ``^S`` are
        interpreted by the terminal driver and excluded from the stdin stream.
        In raw mode these values are received by the :meth:`inkey` method.

        Because output processing is not done, the newline ``'\n'`` is not
        enough, you must also print carriage return to ensure that the cursor
        is returned to the first column::

            with term.raw():
                print("printing in raw mode", end="\r\n")
        """
        if HAS_TTY and self._keyboard_fd is not None:
            # Save current terminal mode:
            save_mode = termios.tcgetattr(self._keyboard_fd)
            save_line_buffered = self._line_buffered
            tty.setraw(self._keyboard_fd, termios.TCSANOW)
            try:
                self._line_buffered = False
                yield
            finally:
                # Restore prior mode:
                termios.tcsetattr(self._keyboard_fd,
                                  termios.TCSAFLUSH,
                                  save_mode)
                self._line_buffered = save_line_buffered
        else:
            yield

    @contextlib.contextmanager
    def keypad(self):
        r"""
        Context manager that enables directional keypad input.

        On entrying, this puts the terminal into "keyboard_transmit" mode by
        emitting the keypad_xmit (smkx) capability. On exit, it emits
        keypad_local (rmkx).

        On an IBM-PC keyboard with numeric keypad of terminal-type *xterm*,
        with numlock off, the lower-left diagonal key transmits sequence
        ``\\x1b[F``, translated to :class:`~.Terminal` attribute
        ``KEY_END``.

        However, upon entering :meth:`keypad`, ``\\x1b[OF`` is transmitted,
        translating to ``KEY_LL`` (lower-left key), allowing you to determine
        diagonal direction keys.
        """
        try:
            self.stream.write(self.smkx)
            self.stream.flush()
            yield
        finally:
            self.stream.write(self.rmkx)
            self.stream.flush()

    def inkey(self, timeout=None, esc_delay=DEFAULT_ESCDELAY):
        r"""
        Read and return the next keyboard event within given timeout.

        Generally, this should be used inside the :meth:`raw` context manager.

        :arg float timeout: Number of seconds to wait for a keystroke before
            returning.  When ``None`` (default), this method may block
            indefinitely.
        :arg float esc_delay: Time in seconds to block after Escape key
           is received to await another key sequence beginning with
           escape such as *KEY_LEFT*, sequence ``'\x1b[D'``], before returning a
           :class:`~.Keystroke` instance for ``KEY_ESCAPE``.

           Users may override the default value of ``esc_delay`` in seconds,
           using environment value of ``ESCDELAY`` as milliseconds, see
           `ncurses(3)`_ section labeled *ESCDELAY* for details.  Setting
           the value as an argument to this function will override any
           such preference.
        :rtype: :class:`~.Keystroke`.
        :returns: :class:`~.Keystroke`, which may be empty (``u''``) if
           ``timeout`` is specified and keystroke is not received.

        .. note:: When used without the context manager :meth:`cbreak`, or
            :meth:`raw`, :obj:`sys.__stdin__` remains line-buffered, and this
            function will block until the return key is pressed!

        .. note:: On Windows, a 10 ms sleep is added to the key press detection loop to reduce CPU
            load. Due to the behavior of :py:func:`time.sleep` on Windows, this will actually
            result in a 15.6 ms delay when using the default `time resolution
            <https://docs.microsoft.com/en-us/windows/win32/api/timeapi/nf-timeapi-timebeginperiod>`_.
            Decreasing the time resolution will reduce this to 10 ms, while increasing it, which
            is rarely done, will have a perceptable impact on the behavior.

        _`ncurses(3)`: https://www.man7.org/linux/man-pages/man3/ncurses.3x.html
        """
        stime = time.time()

        # re-buffer previously received keystrokes,
        ucs = u''
        while self._keyboard_buf:
            ucs += self._keyboard_buf.pop()

        # receive all immediately available bytes
        while self.kbhit(timeout=0):
            ucs += self.getch()

        # decode keystroke, if any
        ks = resolve_sequence(ucs, self._keymap, self._keycodes)

        # so long as the most immediately received or buffered keystroke is
        # incomplete, (which may be a multibyte encoding), block until until
        # one is received.
        while not ks and self.kbhit(timeout=_time_left(stime, timeout)):
            ucs += self.getch()
            ks = resolve_sequence(ucs, self._keymap, self._keycodes)

        # handle escape key (KEY_ESCAPE) vs. escape sequence (like those
        # that begin with \x1b[ or \x1bO) up to esc_delay when
        # received. This is not optimal, but causes least delay when
        # "meta sends escape" is used, or when an unsupported sequence is
        # sent.
        #
        # The statement, "ucs in self._keymap_prefixes" has an effect on
        # keystrokes such as Alt + Z ("\x1b[z" with metaSendsEscape): because
        # no known input sequences begin with such phrasing to allow it to be
        # returned more quickly than esc_delay otherwise blocks for.
        if ks.code == self.KEY_ESCAPE:
            esctime = time.time()
            while (ks.code == self.KEY_ESCAPE and
                   ucs in self._keymap_prefixes and  # pylint: disable=unsupported-membership-test
                   self.kbhit(timeout=_time_left(esctime, esc_delay))):
                ucs += self.getch()
                ks = resolve_sequence(ucs, self._keymap, self._keycodes)

        # buffer any remaining text received
        self.ungetch(ucs[len(ks):])
        return ks


class WINSZ(collections.namedtuple('WINSZ', (
        'ws_row', 'ws_col', 'ws_xpixel', 'ws_ypixel'))):
    """
    Structure represents return value of :const:`termios.TIOCGWINSZ`.

    .. py:attribute:: ws_row

        rows, in characters

    .. py:attribute:: ws_col

        columns, in characters

    .. py:attribute:: ws_xpixel

        horizontal size, pixels

    .. py:attribute:: ws_ypixel

        vertical size, pixels
    """
    #: format of termios structure
    _FMT = 'hhhh'
    #: buffer of termios structure appropriate for ioctl argument
    _BUF = '\x00' * struct.calcsize(_FMT)


#: _CUR_TERM = None
#: From libcurses/doc/ncurses-intro.html (ESR, Thomas Dickey, et. al)::
#:
#:   "After the call to setupterm(), the global variable cur_term is set to
#:    point to the current structure of terminal capabilities. By calling
#:    setupterm() for each terminal, and saving and restoring cur_term, it
#:    is possible for a program to use two or more terminals at once."
#:
#: However, if you study Python's ``./Modules/_cursesmodule.c``, you'll find::
#:
#:   if (!initialised_setupterm && setupterm(termstr,fd,&err) == ERR) {
#:
#: Python - perhaps wrongly - will not allow for re-initialisation of new
#: terminals through :func:`curses.setupterm`, so the value of cur_term cannot
#: be changed once set: subsequent calls to :func:`curses.setupterm` have no
#: effect.
#:
#: Therefore, the :attr:`Terminal.kind` of each :class:`Terminal` is
#: essentially a singleton. This global variable reflects that, and a warning
#: is emitted if somebody expects otherwise.