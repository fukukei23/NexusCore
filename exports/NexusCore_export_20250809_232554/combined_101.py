
# === NexusCore/tools\exports\export_20250803_114325\combined_30.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\lib\editorhooks.py ===
""" 'editor' hooks for common editors that work well with ipython

They should honor the line number argument, at least.

Contributions are *very* welcome.
"""

import os
import shlex
import subprocess
import sys

from IPython import get_ipython
from IPython.core.error import TryNext
from IPython.utils import py3compat


def install_editor(template, wait=False):
    """Installs the editor that is called by IPython for the %edit magic.

    This overrides the default editor, which is generally set by your EDITOR
    environment variable or is notepad (windows) or vi (linux). By supplying a
    template string `run_template`, you can control how the editor is invoked
    by IPython -- (e.g. the format in which it accepts command line options)

    Parameters
    ----------
    template : basestring
        run_template acts as a template for how your editor is invoked by
        the shell. It should contain '{filename}', which will be replaced on
        invocation with the file name, and '{line}', $line by line number
        (or 0) to invoke the file with.
    wait : bool
        If `wait` is true, wait until the user presses enter before returning,
        to facilitate non-blocking editors that exit immediately after
        the call.
    """

    # not all editors support $line, so we'll leave out this check
    # for substitution in ['$file', '$line']:
    #    if not substitution in run_template:
    #        raise ValueError(('run_template should contain %s'
    #        ' for string substitution. You supplied "%s"' % (substitution,
    #            run_template)))

    def call_editor(self, filename, line=0):
        if line is None:
            line = 0
        cmd = template.format(filename=shlex.quote(filename), line=line)
        print(">", cmd)
        # shlex.quote doesn't work right on Windows, but it does after splitting
        if sys.platform.startswith('win'):
            cmd = shlex.split(cmd)
        proc = subprocess.Popen(cmd, shell=True)
        if proc.wait() != 0:
            raise TryNext()
        if wait:
            py3compat.input("Press Enter when done editing:")

    get_ipython().set_hook('editor', call_editor)
    get_ipython().editor = template


# in these, exe is always the path/name of the executable. Useful
# if you don't have the editor directory in your path
def komodo(exe=u'komodo'):
    """ Activestate Komodo [Edit] """
    install_editor(exe + u' -l {line} {filename}', wait=True)


def scite(exe=u"scite"):
    """ SciTE or Sc1 """
    install_editor(exe + u' {filename} -goto:{line}')


def notepadplusplus(exe=u'notepad++'):
    """ Notepad++ http://notepad-plus.sourceforge.net """
    install_editor(exe + u' -n{line} {filename}')


def jed(exe=u'jed'):
    """ JED, the lightweight emacsish editor """
    install_editor(exe + u' +{line} {filename}')


def idle(exe=u'idle'):
    """ Idle, the editor bundled with python

    Parameters
    ----------
    exe : str, None
        If none, should be pretty smart about finding the executable.
    """
    if exe is None:
        import idlelib
        p = os.path.dirname(idlelib.__filename__)
        # i'm not sure if this actually works. Is this idle.py script
        # guaranteed to be executable?
        exe = os.path.join(p, 'idle.py')
    install_editor(exe + u' {filename}')


def mate(exe=u'mate'):
    """ TextMate, the missing editor"""
    # wait=True is not required since we're using the -w flag to mate
    install_editor(exe + u' -w -l {line} {filename}')


# ##########################################
# these are untested, report any problems
# ##########################################


def emacs(exe=u'emacs'):
    install_editor(exe + u' +{line} {filename}')


def gnuclient(exe=u'gnuclient'):
    install_editor(exe + u' -nw +{line} {filename}')


def crimson_editor(exe=u'cedt.exe'):
    install_editor(exe + u' /L:{line} {filename}')


def kate(exe=u'kate'):
    install_editor(exe + u' -u -l {line} {filename}')

# === NexusCore/src\sandbox_logs\repair_20250713_121031_fixed.py ===
申し訳ありませんが、元のコードが提供されていないため、具体的な修正案を提示することはできません。ただし、エラーメッセージから推測すると、Pythonコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。また、特殊文字'、' (U+3001)もPythonの構文には含まれていないため、エラーの原因となっています。

そのため、Pythonの構文に従ってコードを書き直す必要があります。具体的なコードの内容については、元のコードを参照しないと修正案を提示することはできません。

# === NexusCore/src\sandbox_logs\repair_20250713_173733_fixed.py ===
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes. Here is a general example of a pytest-style unit test.
```

# === NexusCore/src\sandbox_logs\repair_20250713_213522_fixed.py ===
エラー内容からすると、Pythonのコード自体に問題はなく、ユニットテストのファイルに非ASCII文字が含まれていることが原因のようです。PythonはデフォルトでUTF-8を使用していますが、非ASCII文字は直接コードに含めることができません。そのため、ユニットテストのファイルを英語またはASCII文字のみを使用するように修正する必要があります。

具体的な修正内容はエラーメッセージからは分からないため、具体的な修正コードは提供できません。ただし、非ASCII文字を含むコメントや文字列を削除または英語に置き換えることで問題は解決するはずです。

# === NexusCore/src\sandbox_logs\repair_20250713_213538_original.py ===
エラー内容からすると、Pythonのコード自体に問題はなく、ユニットテストのファイルに非ASCII文字が含まれていることが原因のようです。PythonはデフォルトでUTF-8を使用していますが、非ASCII文字は直接コードに含めることができません。そのため、ユニットテストのファイルを英語またはASCII文字のみを使用するように修正する必要があります。

具体的な修正内容はエラーメッセージからは分からないため、具体的な修正コードは提供できません。ただし、非ASCII文字を含むコメントや文字列を削除または英語に置き換えることで問題は解決するはずです。

# === NexusCore/openenv\Lib\site-packages\IPython\core\interactiveshell.py ===
"""Main IPython class."""

#-----------------------------------------------------------------------------
#  Copyright (C) 2001 Janko Hauser <jhauser@zscout.de>
#  Copyright (C) 2001-2007 Fernando Perez. <fperez@colorado.edu>
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------


import abc
import ast
import atexit
import bdb
import builtins as builtin_mod
import functools
import inspect
import os
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import traceback
import types
import warnings
from ast import stmt
from contextlib import contextmanager
from io import open as io_open
from logging import error
from pathlib import Path
from typing import Callable
from typing import List as ListType, Any as AnyType
from typing import Literal, Optional, Sequence, Tuple
from warnings import warn

from IPython.external.pickleshare import PickleShareDB

from tempfile import TemporaryDirectory
from traitlets import (
    Any,
    Bool,
    CaselessStrEnum,
    Dict,
    Enum,
    Instance,
    Integer,
    List,
    Type,
    Unicode,
    default,
    observe,
    validate,
)
from traitlets.config.configurable import SingletonConfigurable
from traitlets.utils.importstring import import_item

import IPython.core.hooks
from IPython.core import magic, oinspect, page, prefilter, ultratb
from IPython.core.alias import Alias, AliasManager
from IPython.core.autocall import ExitAutocall
from IPython.core.builtin_trap import BuiltinTrap
from IPython.core.compilerop import CachingCompiler
from IPython.core.debugger import InterruptiblePdb
from IPython.core.display_trap import DisplayTrap
from IPython.core.displayhook import DisplayHook
from IPython.core.displaypub import DisplayPublisher
from IPython.core.error import InputRejected, UsageError
from IPython.core.events import EventManager, available_events
from IPython.core.extensions import ExtensionManager
from IPython.core.formatters import DisplayFormatter
from IPython.core.history import HistoryManager, HistoryOutput
from IPython.core.inputtransformer2 import ESC_MAGIC, ESC_MAGIC2
from IPython.core.logger import Logger
from IPython.core.macro import Macro
from IPython.core.payload import PayloadManager
from IPython.core.prefilter import PrefilterManager
from IPython.core.profiledir import ProfileDir
from IPython.core.tips import pick_tip
from IPython.core.usage import default_banner
from IPython.display import display
from IPython.paths import get_ipython_dir
from IPython.testing.skipdoctest import skip_doctest
from IPython.utils import PyColorize, io, openpy, py3compat
from IPython.utils.decorators import undoc
from IPython.utils.io import ask_yes_no
from IPython.utils.ipstruct import Struct
from IPython.utils.path import ensure_dir_exists, get_home_dir, get_py_filename
from IPython.utils.process import getoutput, system
from IPython.utils.strdispatch import StrDispatch
from IPython.utils.syspathcontext import prepended_to_syspath
from IPython.utils.text import DollarFormatter, LSString, SList, format_screen
from IPython.core.oinspect import OInfo


sphinxify: Optional[Callable]

try:
    import docrepr.sphinxify as sphx

    def sphinxify(oinfo):
        wrapped_docstring = sphx.wrap_main_docstring(oinfo)

        def sphinxify_docstring(docstring):
            with TemporaryDirectory() as dirname:
                return {
                    "text/html": sphx.sphinxify(wrapped_docstring, dirname),
                    "text/plain": docstring,
                }

        return sphinxify_docstring
except ImportError:
    sphinxify = None


class ProvisionalWarning(DeprecationWarning):
    """
    Warning class for unstable features
    """
    pass

from ast import Module

_assign_nodes = (ast.AugAssign, ast.AnnAssign, ast.Assign)
_single_targets_nodes = (ast.AugAssign, ast.AnnAssign)

#-----------------------------------------------------------------------------
# Await Helpers
#-----------------------------------------------------------------------------

# we still need to run things using the asyncio eventloop, but there is no
# async integration
from .async_helpers import (
    _asyncio_runner,
    _curio_runner,
    _pseudo_sync_runner,
    _should_be_async,
    _trio_runner,
)

#-----------------------------------------------------------------------------
# Globals
#-----------------------------------------------------------------------------

# compiled regexps for autoindent management
dedent_re = re.compile(r'^\s+raise|^\s+return|^\s+pass')

#-----------------------------------------------------------------------------
# Utilities
#-----------------------------------------------------------------------------


def is_integer_string(s: str):
    """
    Variant of "str.isnumeric()" that allow negative values and other ints.
    """
    try:
        int(s)
        return True
    except ValueError:
        return False
    raise ValueError("Unexpected error")


@undoc
def softspace(file, newvalue):
    """Copied from code.py, to remove the dependency"""

    oldvalue = 0
    try:
        oldvalue = file.softspace
    except AttributeError:
        pass
    try:
        file.softspace = newvalue
    except (AttributeError, TypeError):
        # "attribute-less object" or "read-only attributes"
        pass
    return oldvalue

@undoc
def no_op(*a, **kw):
    pass


class SpaceInInput(Exception): pass


class SeparateUnicode(Unicode):
    r"""A Unicode subclass to validate separate_in, separate_out, etc.

    This is a Unicode based trait that converts '0'->'' and ``'\\n'->'\n'``.
    """

    def validate(self, obj, value):
        if value == '0': value = ''
        value = value.replace('\\n','\n')
        return super(SeparateUnicode, self).validate(obj, value)


class _IPythonMainModuleBase(types.ModuleType):
    def __init__(self) -> None:
        super().__init__(
            "__main__",
            doc="Automatically created module for the IPython interactive environment",
        )


def make_main_module_type(user_ns: dict[str, Any]) -> type[_IPythonMainModuleBase]:
    @undoc
    class IPythonMainModule(_IPythonMainModuleBase):
        """
        ModuleType that supports passing in a custom user namespace dictionary,
        to be used for the module's __dict__. This is enabled by shadowing the
        underlying __dict__ attribute of the module, and overriding getters and
        setters to point to the custom user namespace dictionary.
        The reason to do this is to allow the __main__ module to be an instance
        of ModuleType, while still allowing the user namespace to be custom.
        """

        @property
        def __dict__(self) -> dict[str, Any]:  # type: ignore[override]
            return user_ns

        def __setattr__(self, item: str, value: Any) -> None:
            if item == "__dict__":
                # Ignore this when IPython tries to set it, since we already provide it
                return
            user_ns[item] = value

        def __getattr__(self, item: str) -> Any:
            try:
                return user_ns[item]
            except KeyError:
                raise AttributeError(f"module {self.__name__} has no attribute {item}")

        def __delattr__(self, item: str) -> None:
            try:
                del user_ns[item]
            except KeyError:
                raise AttributeError(f"module {self.__name__} has no attribute {item}")

    return IPythonMainModule


class ExecutionInfo:
    """The arguments used for a call to :meth:`InteractiveShell.run_cell`

    Stores information about what is going to happen.
    """
    raw_cell = None
    store_history = False
    silent = False
    shell_futures = True
    cell_id = None

    def __init__(self, raw_cell, store_history, silent, shell_futures, cell_id):
        self.raw_cell = raw_cell
        self.store_history = store_history
        self.silent = silent
        self.shell_futures = shell_futures
        self.cell_id = cell_id

    def __repr__(self):
        name = self.__class__.__qualname__
        raw_cell = (
            (self.raw_cell[:50] + "..") if len(self.raw_cell) > 50 else self.raw_cell
        )
        return (
            '<%s object at %x, raw_cell="%s" store_history=%s silent=%s shell_futures=%s cell_id=%s>'
            % (
                name,
                id(self),
                raw_cell,
                self.store_history,
                self.silent,
                self.shell_futures,
                self.cell_id,
            )
        )


class ExecutionResult:
    """The result of a call to :meth:`InteractiveShell.run_cell`

    Stores information about what took place.
    """

    execution_count: Optional[int] = None
    error_before_exec: Optional[BaseException] = None
    error_in_exec: Optional[BaseException] = None
    info = None
    result = None

    def __init__(self, info):
        self.info = info

    @property
    def success(self):
        return (self.error_before_exec is None) and (self.error_in_exec is None)

    def raise_error(self):
        """Reraises error if `success` is `False`, otherwise does nothing"""
        if self.error_before_exec is not None:
            raise self.error_before_exec
        if self.error_in_exec is not None:
            raise self.error_in_exec

    def __repr__(self):
        name = self.__class__.__qualname__
        return '<%s object at %x, execution_count=%s error_before_exec=%s error_in_exec=%s info=%s result=%s>' %\
                (name, id(self), self.execution_count, self.error_before_exec, self.error_in_exec, repr(self.info), repr(self.result))


@functools.wraps(io_open)
def _modified_open(file, *args, **kwargs):
    if file in {0, 1, 2}:
        raise ValueError(
            f"IPython won't let you open fd={file} by default "
            "as it is likely to crash IPython. If you know what you are doing, "
            "you can use builtins' open."
        )

    return io_open(file, *args, **kwargs)


class InteractiveShell(SingletonConfigurable):
    """An enhanced, interactive shell for Python."""

    _instance = None
    _user_ns: dict
    _sys_modules_keys: set[str]

    inspector: oinspect.Inspector

    ast_transformers: List[ast.NodeTransformer] = List(
        [],
        help="""
        A list of ast.NodeTransformer subclass instances, which will be applied
        to user input before code is run.
        """,
    ).tag(config=True)

    autocall = Enum((0,1,2), default_value=0, help=
        """
        Make IPython automatically call any callable object even if you didn't
        type explicit parentheses. For example, 'str 43' becomes 'str(43)'
        automatically. The value can be '0' to disable the feature, '1' for
        'smart' autocall, where it is not applied if there are no more
        arguments on the line, and '2' for 'full' autocall, where all callable
        objects are automatically called (even if no arguments are present).
        """
    ).tag(config=True)

    autoindent = Bool(True, help=
        """
        Autoindent IPython code entered interactively.
        """
    ).tag(config=True)

    autoawait = Bool(True, help=
        """
        Automatically run await statement in the top level repl.
        """
    ).tag(config=True)

    loop_runner_map ={
        'asyncio':(_asyncio_runner, True),
        'curio':(_curio_runner, True),
        'trio':(_trio_runner, True),
        'sync': (_pseudo_sync_runner, False)
    }

    loop_runner = Any(default_value="IPython.core.interactiveshell._asyncio_runner",
        allow_none=True,
        help="""Select the loop runner that will be used to execute top-level asynchronous code"""
    ).tag(config=True)

    @default('loop_runner')
    def _default_loop_runner(self):
        return import_item("IPython.core.interactiveshell._asyncio_runner")

    @validate('loop_runner')
    def _import_runner(self, proposal):
        if isinstance(proposal.value, str):
            if proposal.value in self.loop_runner_map:
                runner, autoawait = self.loop_runner_map[proposal.value]
                self.autoawait = autoawait
                return runner
            runner = import_item(proposal.value)
            if not callable(runner):
                raise ValueError('loop_runner must be callable')
            return runner
        if not callable(proposal.value):
            raise ValueError('loop_runner must be callable')
        return proposal.value

    automagic = Bool(True, help=
        """
        Enable magic commands to be called without the leading %.
        """
    ).tag(config=True)

    enable_tip = Bool(
        True,
        help="""
        Set to show a tip when IPython starts.""",
    ).tag(config=True)

    banner1 = Unicode(default_banner,
        help="""The part of the banner to be printed before the profile"""
    ).tag(config=True)
    banner2 = Unicode('',
        help="""The part of the banner to be printed after the profile"""
    ).tag(config=True)

    cache_size = Integer(
        1000,
        help="""
        Set the size of the output cache.  The default is 1000, you can
        change it permanently in your config file.  Setting it to 0 completely
        disables the caching system, and the minimum value accepted is 3 (if
        you provide a value less than 3, it is reset to 0 and a warning is
        issued).  This limit is defined because otherwise you'll spend more
        time re-flushing a too small cache than working
        """,
    ).tag(config=True)
    debug = Bool(False).tag(config=True)
    display_formatter = Instance(DisplayFormatter, allow_none=True)
    displayhook_class = Type(DisplayHook)
    display_pub_class = Type(DisplayPublisher)
    compiler_class = Type(CachingCompiler)
    inspector_class = Type(
        oinspect.Inspector, help="Class to use to instantiate the shell inspector"
    ).tag(config=True)

    sphinxify_docstring = Bool(False, help=
        """
        Enables rich html representation of docstrings. (This requires the
        docrepr module).
        """).tag(config=True)

    @observe("sphinxify_docstring")
    def _sphinxify_docstring_changed(self, change):
        if change['new']:
            warn("`sphinxify_docstring` is provisional since IPython 5.0 and might change in future versions." , ProvisionalWarning)

    enable_html_pager = Bool(False, help=
        """
        (Provisional API) enables html representation in mime bundles sent
        to pagers.
        """).tag(config=True)

    @observe("enable_html_pager")
    def _enable_html_pager_changed(self, change):
        if change['new']:
            warn("`enable_html_pager` is provisional since IPython 5.0 and might change in future versions.", ProvisionalWarning)

    data_pub_class = None

    exit_now = Bool(False)
    exiter = Instance(ExitAutocall)
    @default('exiter')
    def _exiter_default(self):
        return ExitAutocall(self)
    # Monotonically increasing execution counter
    execution_count = Integer(1)
    filename = Unicode("<ipython console>")
    ipython_dir = Unicode("").tag(config=True)  # Set to get_ipython_dir() in __init__

    # Used to transform cells before running them, and check whether code is complete
    input_transformer_manager = Instance('IPython.core.inputtransformer2.TransformerManager',
                                         ())

    @property
    def input_transformers_cleanup(self):
        return self.input_transformer_manager.cleanup_transforms

    input_transformers_post: List = List(
        [],
        help="A list of string input transformers, to be applied after IPython's "
             "own input transformations."
    )

    logstart = Bool(False, help=
        """
        Start logging to the default log file in overwrite mode.
        Use `logappend` to specify a log file to **append** logs to.
        """
    ).tag(config=True)
    logfile = Unicode('', help=
        """
        The name of the logfile to use.
        """
    ).tag(config=True)
    logappend = Unicode('', help=
        """
        Start logging to the given file in append mode.
        Use `logfile` to specify a log file to **overwrite** logs to.
        """
    ).tag(config=True)
    object_info_string_level = Enum((0,1,2), default_value=0,
    ).tag(config=True)
    pdb = Bool(False, help=
        """
        Automatically call the pdb debugger after every exception.
        """
    ).tag(config=True)
    display_page = Bool(False,
        help="""If True, anything that would be passed to the pager
        will be displayed as regular output instead."""
    ).tag(config=True)


    show_rewritten_input = Bool(True,
        help="Show rewritten input, e.g. for autocall."
    ).tag(config=True)

    quiet = Bool(False).tag(config=True)

    history_length = Integer(10000,
        help='Total length of command history'
    ).tag(config=True)

    history_load_length = Integer(1000, help=
        """
        The number of saved history entries to be loaded
        into the history buffer at startup.
        """
    ).tag(config=True)

    ast_node_interactivity = Enum(['all', 'last', 'last_expr', 'none', 'last_expr_or_assign'],
                                  default_value='last_expr',
                                  help="""
        'all', 'last', 'last_expr' or 'none', 'last_expr_or_assign' specifying
        which nodes should be run interactively (displaying output from expressions).
        """
    ).tag(config=True)

    warn_venv = Bool(
        True,
        help="Warn if running in a virtual environment with no IPython installed (so IPython from the global environment is used).",
    ).tag(config=True)

    # TODO: this part of prompt management should be moved to the frontends.
    # Use custom TraitTypes that convert '0'->'' and '\\n'->'\n'
    separate_in = SeparateUnicode('\n').tag(config=True)
    separate_out = SeparateUnicode('').tag(config=True)
    separate_out2 = SeparateUnicode('').tag(config=True)
    wildcards_case_sensitive = Bool(True).tag(config=True)
    xmode = CaselessStrEnum(
        ("Context", "Plain", "Verbose", "Minimal", "Docs"),
        default_value="Context",
        help="Switch modes for the IPython exception handlers.",
    ).tag(config=True)

    # Subcomponents of InteractiveShell
    alias_manager = Instance("IPython.core.alias.AliasManager", allow_none=True)
    prefilter_manager = Instance(
        "IPython.core.prefilter.PrefilterManager", allow_none=True
    )
    builtin_trap = Instance("IPython.core.builtin_trap.BuiltinTrap")
    display_trap = Instance("IPython.core.display_trap.DisplayTrap")
    extension_manager = Instance(
        "IPython.core.extensions.ExtensionManager", allow_none=True
    )
    payload_manager = Instance("IPython.core.payload.PayloadManager", allow_none=True)
    history_manager = Instance(
        "IPython.core.history.HistoryAccessorBase", allow_none=True
    )
    magics_manager = Instance("IPython.core.magic.MagicsManager")

    profile_dir = Instance('IPython.core.application.ProfileDir', allow_none=True)
    @property
    def profile(self):
        if self.profile_dir is not None:
            name = os.path.basename(self.profile_dir.location)
            return name.replace('profile_','')


    # Private interface
    _post_execute = Dict()

    # Tracks any GUI loop loaded for pylab
    pylab_gui_select = None

    last_execution_succeeded = Bool(True, help='Did last executed command succeeded')

    last_execution_result = Instance('IPython.core.interactiveshell.ExecutionResult', help='Result of executing the last command', allow_none=True)

    def __init__(self, ipython_dir=None, profile_dir=None,
                 user_module=None, user_ns=None,
                 custom_exceptions=((), None), **kwargs):
        # This is where traits with a config_key argument are updated
        # from the values on config.
        super(InteractiveShell, self).__init__(**kwargs)
        self.configurables = [self]

        # These are relatively independent and stateless
        self.init_ipython_dir(ipython_dir)
        self.init_profile_dir(profile_dir)
        self.init_instance_attrs()
        self.init_environment()

        # Check if we're in a virtualenv, and set up sys.path.
        self.init_virtualenv()

        # Create namespaces (user_ns, user_global_ns, etc.)
        self.init_create_namespaces(user_module, user_ns)
        # This has to be done after init_create_namespaces because it uses
        # something in self.user_ns, but before init_sys_modules, which
        # is the first thing to modify sys.
        # TODO: When we override sys.stdout and sys.stderr before this class
        # is created, we are saving the overridden ones here. Not sure if this
        # is what we want to do.
        self.save_sys_module_state()
        self.init_sys_modules()

        # While we're trying to have each part of the code directly access what
        # it needs without keeping redundant references to objects, we have too
        # much legacy code that expects ip.db to exist.
        self.db = PickleShareDB(os.path.join(self.profile_dir.location, 'db'))

        self.init_history()
        self.init_encoding()
        self.init_prefilter()

        self.init_syntax_highlighting()
        self.init_hooks()
        self.init_events()
        self.init_pushd_popd_magic()
        self.init_user_ns()
        self.init_logger()
        self.init_builtins()

        # The following was in post_config_initialization
        self.raw_input_original = input
        self.init_completer()
        # TODO: init_io() needs to happen before init_traceback handlers
        # because the traceback handlers hardcode the stdout/stderr streams.
        # This logic in in debugger.Pdb and should eventually be changed.
        self.init_io()
        self.init_traceback_handlers(custom_exceptions)
        self.init_prompts()
        self.init_display_formatter()
        self.init_display_pub()
        self.init_data_pub()
        self.init_displayhook()
        self.init_magics()
        self.init_alias()
        self.init_logstart()
        self.init_pdb()
        self.init_extension_manager()
        self.init_payload()
        self.events.trigger('shell_initialized', self)
        atexit.register(self.atexit_operations)

        # The trio runner is used for running Trio in the foreground thread. It
        # is different from `_trio_runner(async_fn)` in `async_helpers.py`
        # which calls `trio.run()` for every cell. This runner runs all cells
        # inside a single Trio event loop. If used, it is set from
        # `ipykernel.kernelapp`.
        self.trio_runner = None
        self.showing_traceback = False

    @property
    def user_ns(self):
        return self._user_ns

    @user_ns.setter
    def user_ns(self, ns: dict):
        assert hasattr(ns, "clear")
        assert isinstance(ns, dict)
        self._user_ns = ns

    def get_ipython(self):
        """Return the currently running IPython instance."""
        return self

    #-------------------------------------------------------------------------
    # Trait changed handlers
    #-------------------------------------------------------------------------
    @observe('ipython_dir')
    def _ipython_dir_changed(self, change):
        ensure_dir_exists(change['new'])

    def set_autoindent(self,value=None):
        """Set the autoindent flag.

        If called with no arguments, it acts as a toggle."""
        if value is None:
            self.autoindent = not self.autoindent
        else:
            self.autoindent = value

    def set_trio_runner(self, tr):
        self.trio_runner = tr

    #-------------------------------------------------------------------------
    # init_* methods called by __init__
    #-------------------------------------------------------------------------

    def init_ipython_dir(self, ipython_dir):
        if ipython_dir is not None:
            self.ipython_dir = ipython_dir
            return

        self.ipython_dir = get_ipython_dir()

    def init_profile_dir(self, profile_dir):
        if profile_dir is not None:
            self.profile_dir = profile_dir
            return
        self.profile_dir = ProfileDir.create_profile_dir_by_name(
            self.ipython_dir, "default"
        )

    def init_instance_attrs(self):
        self.more = False

        # command compiler
        self.compile = self.compiler_class()

        # Make an empty namespace, which extension writers can rely on both
        # existing and NEVER being used by ipython itself.  This gives them a
        # convenient location for storing additional information and state
        # their extensions may require, without fear of collisions with other
        # ipython names that may develop later.
        self.meta = Struct()

        # Temporary files used for various purposes.  Deleted at exit.
        # The files here are stored with Path from Pathlib
        self.tempfiles = []
        self.tempdirs = []

        # keep track of where we started running (mainly for crash post-mortem)
        # This is not being used anywhere currently.
        self.starting_dir = os.getcwd()

        # Indentation management
        self.indent_current_nsp = 0

        # Dict to track post-execution functions that have been registered
        self._post_execute = {}

    def init_environment(self):
        """Any changes we need to make to the user's environment."""
        pass

    def init_encoding(self):
        # Get system encoding at startup time.  Certain terminals (like Emacs
        # under Win32 have it set to None, and we need to have a known valid
        # encoding to use in the raw_input() method
        try:
            self.stdin_encoding = sys.stdin.encoding or 'ascii'
        except AttributeError:
            self.stdin_encoding = 'ascii'

    colors = Unicode(
        "neutral", help="Set the color scheme (nocolor, neutral, linux, lightbg)."
    ).tag(config=True)

    @validate("colors")
    def _check_colors(self, proposal):
        new = proposal["value"]
        if not new == new.lower():
            warn(
                f"`TerminalInteractiveShell.colors` is now lowercase: `{new.lower()}`,"
                " non lowercase, may be invalid in the future.",
                DeprecationWarning,
                stacklevel=2,
            )
        return new.lower()

    @observe("colors")
    def init_syntax_highlighting(self, changes=None):
        # Python source parser/formatter for syntax highlighting
        pyformat = PyColorize.Parser(theme_name=self.colors).format
        self.pycolorize = lambda src: pyformat(src, "str")
        if not hasattr(self, "inspector"):
            self.inspector = self.inspector_class(
                theme_name=self.colors,
                str_detail_level=self.object_info_string_level,
                parent=self,
            )

        try:
            # Deprecation in 9.0, colors should always be lower
            self.inspector.set_theme_name(self.colors.lower())
        except Exception:
            warn(
                "Error changing object inspector color schemes.\n%s"
                % (sys.exc_info()[1]),
                stacklevel=2,
            )
        if hasattr(self, "InteractiveTB"):
            self.InteractiveTB.set_theme_name(self.colors)
        if hasattr(self, "SyntaxTB"):
            self.SyntaxTB.set_theme_name(self.colors)
        self.refresh_style()

    def refresh_style(self):
        # No-op here, used in subclass
        pass

    def init_pushd_popd_magic(self):
        # for pushd/popd management
        self.home_dir = get_home_dir()

        self.dir_stack = []

    def init_logger(self) -> None:
        self.logger = Logger(self.home_dir, logfname='ipython_log.py',
                             logmode='rotate')

    def init_logstart(self) -> None:
        """Initialize logging in case it was requested at the command line.
        """
        if self.logappend:
            self.run_line_magic("logstart", f"{self.logappend} append")
        elif self.logfile:
            self.run_line_magic("logstart", self.logfile)
        elif self.logstart:
            self.run_line_magic("logstart", "")

    def init_builtins(self):
        # A single, static flag that we set to True.  Its presence indicates
        # that an IPython shell has been created, and we make no attempts at
        # removing on exit or representing the existence of more than one
        # IPython at a time.
        builtin_mod.__dict__['__IPYTHON__'] = True
        builtin_mod.__dict__['display'] = display

        self.builtin_trap = BuiltinTrap(shell=self)


    def init_io(self):
        # implemented in subclasses, TerminalInteractiveShell does call
        # colorama.init().
        pass

    def init_prompts(self):
        # Set system prompts, so that scripts can decide if they are running
        # interactively.
        sys.ps1 = 'In : '
        sys.ps2 = '...: '
        sys.ps3 = 'Out: '

    def init_display_formatter(self):
        self.display_formatter = DisplayFormatter(parent=self)
        self.configurables.append(self.display_formatter)

    def init_display_pub(self):
        self.display_pub = self.display_pub_class(parent=self, shell=self)
        self.configurables.append(self.display_pub)

    def init_data_pub(self):
        if not self.data_pub_class:
            self.data_pub = None
            return
        self.data_pub = self.data_pub_class(parent=self)
        self.configurables.append(self.data_pub)

    def init_displayhook(self):
        # Initialize displayhook, set in/out prompts and printing system
        self.displayhook = self.displayhook_class(
            parent=self,
            shell=self,
            cache_size=self.cache_size,
        )
        self.configurables.append(self.displayhook)
        # This is a context manager that installs/removes the displayhook at
        # the appropriate time.
        self.display_trap = DisplayTrap(hook=self.displayhook)

    @staticmethod
    def get_path_links(p: Path):
        """Gets path links including all symlinks

        Examples
        --------
        In [1]: from IPython.core.interactiveshell import InteractiveShell

        In [2]: import sys, pathlib

        In [3]: paths = InteractiveShell.get_path_links(pathlib.Path(sys.executable))

        In [4]: len(paths) == len(set(paths))
        Out[4]: True

        In [5]: bool(paths)
        Out[5]: True
        """
        paths = [p]
        while p.is_symlink():
            new_path = Path(os.readlink(p))
            if not new_path.is_absolute():
                new_path = p.parent / new_path
            p = new_path
            paths.append(p)
        return paths

    def init_virtualenv(self):
        """Add the current virtualenv to sys.path so the user can import modules from it.
        This isn't perfect: it doesn't use the Python interpreter with which the
        virtualenv was built, and it ignores the --no-site-packages option. A
        warning will appear suggesting the user installs IPython in the
        virtualenv, but for many cases, it probably works well enough.

        Adapted from code snippets online.

        http://blog.ufsoft.org/2009/1/29/ipython-and-virtualenv
        """
        if 'VIRTUAL_ENV' not in os.environ:
            # Not in a virtualenv
            return
        elif os.environ["VIRTUAL_ENV"] == "":
            warn("Virtual env path set to '', please check if this is intended.")
            return

        p = Path(sys.executable)
        p_venv = Path(os.environ["VIRTUAL_ENV"]).resolve()

        # fallback venv detection:
        # stdlib venv may symlink sys.executable, so we can't use realpath.
        # but others can symlink *to* the venv Python, so we can't just use sys.executable.
        # So we just check every item in the symlink tree (generally <= 3)
        paths = self.get_path_links(p)

        # In Cygwin paths like "c:\..." and '\cygdrive\c\...' are possible
        if len(p_venv.parts) > 2 and p_venv.parts[1] == "cygdrive":
            drive_name = p_venv.parts[2]
            p_venv = (drive_name + ":/") / Path(*p_venv.parts[3:])

        if any(p_venv == p.parents[1].resolve() for p in paths):
            # Our exe is inside or has access to the virtualenv, don't need to do anything.
            return

        if sys.platform == "win32":
            virtual_env = str(Path(os.environ["VIRTUAL_ENV"], "Lib", "site-packages"))
        else:
            virtual_env_path = Path(
                os.environ["VIRTUAL_ENV"], "lib", "python{}.{}", "site-packages"
            )
            p_ver = sys.version_info[:2]

            # Predict version from py[thon]-x.x in the $VIRTUAL_ENV
            re_m = re.search(r"\bpy(?:thon)?([23])\.(\d+)\b", os.environ["VIRTUAL_ENV"])
            if re_m:
                predicted_path = Path(str(virtual_env_path).format(*re_m.groups()))
                if predicted_path.exists():
                    p_ver = re_m.groups()

            virtual_env = str(virtual_env_path).format(*p_ver)
        if self.warn_venv:
            warn(
                "Attempting to work in a virtualenv. If you encounter problems, "
                "please install IPython inside the virtualenv."
            )
        import site
        sys.path.insert(0, virtual_env)
        site.addsitedir(virtual_env)

    #-------------------------------------------------------------------------
    # Things related to injections into the sys module
    #-------------------------------------------------------------------------

    def save_sys_module_state(self):
        """Save the state of hooks in the sys module.

        This has to be called after self.user_module is created.
        """
        self._orig_sys_module_state = {'stdin': sys.stdin,
                                       'stdout': sys.stdout,
                                       'stderr': sys.stderr,
                                       'excepthook': sys.excepthook}
        self._orig_sys_modules_main_name = self.user_module.__name__
        self._orig_sys_modules_main_mod = sys.modules.get(self.user_module.__name__)

    def restore_sys_module_state(self):
        """Restore the state of the sys module."""
        try:
            for k, v in self._orig_sys_module_state.items():
                setattr(sys, k, v)
        except AttributeError:
            pass
        # Reset what what done in self.init_sys_modules
        if self._orig_sys_modules_main_mod is not None:
            sys.modules[self._orig_sys_modules_main_name] = self._orig_sys_modules_main_mod

    #-------------------------------------------------------------------------
    # Things related to the banner
    #-------------------------------------------------------------------------

    @property
    def banner(self):
        banner = self.banner1
        if self.profile and self.profile != 'default':
            banner += '\nIPython profile: %s\n' % self.profile
        if self.banner2:
            banner += '\n' + self.banner2
        elif self.enable_tip:
            banner += "Tip: {tip}\n".format(tip=pick_tip())
        return banner

    def show_banner(self, banner=None):
        if banner is None:
            banner = self.banner
        print(banner, end="")

    #-------------------------------------------------------------------------
    # Things related to hooks
    #-------------------------------------------------------------------------

    def init_hooks(self):
        # hooks holds pointers used for user-side customizations
        self.hooks = Struct()

        self.strdispatchers = {}

        # Set all default hooks, defined in the IPython.hooks module.
        hooks = IPython.core.hooks
        for hook_name in hooks.__all__:
            # default hooks have priority 100, i.e. low; user hooks should have
            # 0-100 priority
            self.set_hook(hook_name, getattr(hooks, hook_name), 100)

        if self.display_page:
            self.set_hook('show_in_pager', page.as_hook(page.display_page), 90)

    def set_hook(self, name, hook, priority=50, str_key=None, re_key=None):
        """set_hook(name,hook) -> sets an internal IPython hook.

        IPython exposes some of its internal API as user-modifiable hooks.  By
        adding your function to one of these hooks, you can modify IPython's
        behavior to call at runtime your own routines."""

        # At some point in the future, this should validate the hook before it
        # accepts it.  Probably at least check that the hook takes the number
        # of args it's supposed to.

        f = types.MethodType(hook,self)

        # check if the hook is for strdispatcher first
        if str_key is not None:
            sdp = self.strdispatchers.get(name, StrDispatch())
            sdp.add_s(str_key, f, priority )
            self.strdispatchers[name] = sdp
            return
        if re_key is not None:
            sdp = self.strdispatchers.get(name, StrDispatch())
            sdp.add_re(re.compile(re_key), f, priority )
            self.strdispatchers[name] = sdp
            return

        dp = getattr(self.hooks, name, None)
        if name not in IPython.core.hooks.__all__:
            print("Warning! Hook '%s' is not one of %s" % \
                  (name, IPython.core.hooks.__all__ ))

        if not dp:
            dp = IPython.core.hooks.CommandChainDispatcher()

        try:
            dp.add(f,priority)
        except AttributeError:
            # it was not commandchain, plain old func - replace
            dp = f

        setattr(self.hooks,name, dp)

    #-------------------------------------------------------------------------
    # Things related to events
    #-------------------------------------------------------------------------

    def init_events(self):
        self.events = EventManager(self, available_events)

        self.events.register("pre_execute", self._clear_warning_registry)

    def _clear_warning_registry(self):
        # clear the warning registry, so that different code blocks with
        # overlapping line number ranges don't cause spurious suppression of
        # warnings (see gh-6611 for details)
        if "__warningregistry__" in self.user_global_ns:
            del self.user_global_ns["__warningregistry__"]

    #-------------------------------------------------------------------------
    # Things related to the "main" module
    #-------------------------------------------------------------------------

    def new_main_mod(self, filename, modname):
        """Return a new 'main' module object for user code execution.

        ``filename`` should be the path of the script which will be run in the
        module. Requests with the same filename will get the same module, with
        its namespace cleared.

        ``modname`` should be the module name - normally either '__main__' or
        the basename of the file without the extension.

        When scripts are executed via %run, we must keep a reference to their
        __main__ module around so that Python doesn't
        clear it, rendering references to module globals useless.

        This method keeps said reference in a private dict, keyed by the
        absolute path of the script. This way, for multiple executions of the
        same script we only keep one copy of the namespace (the last one),
        thus preventing memory leaks from old references while allowing the
        objects from the last execution to be accessible.
        """
        filename = os.path.abspath(filename)
        try:
            main_mod = self._main_mod_cache[filename]
        except KeyError:
            main_mod = self._main_mod_cache[filename] = types.ModuleType(
                        modname,
                        doc="Module created for script run in IPython")
        else:
            main_mod.__dict__.clear()
            main_mod.__name__ = modname

        main_mod.__file__ = filename
        # It seems pydoc (and perhaps others) needs any module instance to
        # implement a __nonzero__ method
        main_mod.__nonzero__ = lambda : True

        return main_mod

    def clear_main_mod_cache(self):
        """Clear the cache of main modules.

        Mainly for use by utilities like %reset.

        Examples
        --------
        In [15]: import IPython

        In [16]: m = _ip.new_main_mod(IPython.__file__, 'IPython')

        In [17]: len(_ip._main_mod_cache) > 0
        Out[17]: True

        In [18]: _ip.clear_main_mod_cache()

        In [19]: len(_ip._main_mod_cache) == 0
        Out[19]: True
        """
        self._main_mod_cache.clear()

    #-------------------------------------------------------------------------
    # Things related to debugging
    #-------------------------------------------------------------------------

    def init_pdb(self):
        # Set calling of pdb on exceptions
        # self.call_pdb is a property
        self.call_pdb = self.pdb

    def _get_call_pdb(self):
        return self._call_pdb

    def _set_call_pdb(self,val):

        if val not in (0,1,False,True):
            raise ValueError('new call_pdb value must be boolean')

        # store value in instance
        self._call_pdb = val

        # notify the actual exception handlers
        self.InteractiveTB.call_pdb = val

    call_pdb = property(_get_call_pdb,_set_call_pdb,None,
                        'Control auto-activation of pdb at exceptions')

    def debugger(self,force=False):
        """Call the pdb debugger.

        Keywords:

          - force(False): by default, this routine checks the instance call_pdb
            flag and does not actually invoke the debugger if the flag is false.
            The 'force' option forces the debugger to activate even if the flag
            is false.
        """

        if not (force or self.call_pdb):
            return

        if not hasattr(sys,'last_traceback'):
            error('No traceback has been produced, nothing to debug.')
            return

        self.InteractiveTB.debugger(force=True)

    #-------------------------------------------------------------------------
    # Things related to IPython's various namespaces
    #-------------------------------------------------------------------------
    default_user_namespaces = True

    def init_create_namespaces(self, user_module=None, user_ns=None):
        # Create the namespace where the user will operate.  user_ns is
        # normally the only one used, and it is passed to the exec calls as
        # the locals argument.  But we do carry a user_global_ns namespace
        # given as the exec 'globals' argument,  This is useful in embedding
        # situations where the ipython shell opens in a context where the
        # distinction between locals and globals is meaningful.  For
        # non-embedded contexts, it is just the same object as the user_ns dict.

        # FIXME. For some strange reason, __builtins__ is showing up at user
        # level as a dict instead of a module. This is a manual fix, but I
        # should really track down where the problem is coming from. Alex
        # Schmolck reported this problem first.

        # A useful post by Alex Martelli on this topic:
        # Re: inconsistent value from __builtins__
        # Von: Alex Martelli <aleaxit@yahoo.com>
        # Datum: Freitag 01 Oktober 2004 04:45:34 nachmittags/abends
        # Gruppen: comp.lang.python

        # Michael Hohn <hohn@hooknose.lbl.gov> wrote:
        # > >>> print type(builtin_check.get_global_binding('__builtins__'))
        # > <type 'dict'>
        # > >>> print type(__builtins__)
        # > <type 'module'>
        # > Is this difference in return value intentional?

        # Well, it's documented that '__builtins__' can be either a dictionary
        # or a module, and it's been that way for a long time. Whether it's
        # intentional (or sensible), I don't know. In any case, the idea is
        # that if you need to access the built-in namespace directly, you
        # should start with "import __builtin__" (note, no 's') which will
        # definitely give you a module. Yeah, it's somewhat confusing:-(.

        # These routines return a properly built module and dict as needed by
        # the rest of the code, and can also be used by extension writers to
        # generate properly initialized namespaces.
        if (user_ns is not None) or (user_module is not None):
            self.default_user_namespaces = False
        self.user_module, self.user_ns = self.prepare_user_module(user_module, user_ns)

        # A record of hidden variables we have added to the user namespace, so
        # we can list later only variables defined in actual interactive use.
        self.user_ns_hidden = {}

        # Now that FakeModule produces a real module, we've run into a nasty
        # problem: after script execution (via %run), the module where the user
        # code ran is deleted.  Now that this object is a true module (needed
        # so doctest and other tools work correctly), the Python module
        # teardown mechanism runs over it, and sets to None every variable
        # present in that module.  Top-level references to objects from the
        # script survive, because the user_ns is updated with them.  However,
        # calling functions defined in the script that use other things from
        # the script will fail, because the function's closure had references
        # to the original objects, which are now all None.  So we must protect
        # these modules from deletion by keeping a cache.
        #
        # To avoid keeping stale modules around (we only need the one from the
        # last run), we use a dict keyed with the full path to the script, so
        # only the last version of the module is held in the cache.  Note,
        # however, that we must cache the module *namespace contents* (their
        # __dict__).  Because if we try to cache the actual modules, old ones
        # (uncached) could be destroyed while still holding references (such as
        # those held by GUI objects that tend to be long-lived)>
        #
        # The %reset command will flush this cache.  See the cache_main_mod()
        # and clear_main_mod_cache() methods for details on use.

        # This is the cache used for 'main' namespaces
        self._main_mod_cache = {}

        # A table holding all the namespaces IPython deals with, so that
        # introspection facilities can search easily.
        self.ns_table = {'user_global':self.user_module.__dict__,
                         'user_local':self.user_ns,
                         'builtin':builtin_mod.__dict__
                         }

    @property
    def user_global_ns(self):
        return self.user_module.__dict__

    def prepare_user_module(self, user_module=None, user_ns=None):
        """Prepare the module and namespace in which user code will be run.

        When IPython is started normally, both parameters are None: a new module
        is created automatically, and its __dict__ used as the namespace.

        If only user_module is provided, its __dict__ is used as the namespace.
        If only user_ns is provided, a dummy module is created, and user_ns
        becomes the global namespace. If both are provided (as they may be
        when embedding), user_ns is the local namespace, and user_module
        provides the global namespace.

        Parameters
        ----------
        user_module : module, optional
            The current user module in which IPython is being run. If None,
            a clean module will be created.
        user_ns : dict, optional
            A namespace in which to run interactive commands.

        Returns
        -------
        A tuple of user_module and user_ns, each properly initialised.
        """
        if user_module is None and user_ns is not None:
            user_ns.setdefault("__name__", "__main__")
            user_module = make_main_module_type(user_ns)()

        if user_module is None:
            user_module = types.ModuleType("__main__",
                doc="Automatically created module for IPython interactive environment")

        # We must ensure that __builtin__ (without the final 's') is always
        # available and pointing to the __builtin__ *module*.  For more details:
        # http://mail.python.org/pipermail/python-dev/2001-April/014068.html
        user_module.__dict__.setdefault('__builtin__', builtin_mod)
        user_module.__dict__.setdefault('__builtins__', builtin_mod)

        if user_ns is None:
            user_ns = user_module.__dict__
        return user_module, user_ns

    def init_sys_modules(self):
        # We need to insert into sys.modules something that looks like a
        # module but which accesses the IPython namespace, for shelve and
        # pickle to work interactively. Normally they rely on getting
        # everything out of __main__, but for embedding purposes each IPython
        # instance has its own private namespace, so we can't go shoving
        # everything into __main__.

        # note, however, that we should only do this for non-embedded
        # ipythons, which really mimic the __main__.__dict__ with their own
        # namespace.  Embedded instances, on the other hand, should not do
        # this because they need to manage the user local/global namespaces
        # only, but they live within a 'normal' __main__ (meaning, they
        # shouldn't overtake the execution environment of the script they're
        # embedded in).

        # This is overridden in the InteractiveShellEmbed subclass to a no-op.
        main_name = self.user_module.__name__
        sys.modules[main_name] = self.user_module

    def init_user_ns(self):
        """Initialize all user-visible namespaces to their minimum defaults.

        Certain history lists are also initialized here, as they effectively
        act as user namespaces.

        Notes
        -----
        All data structures here are only filled in, they are NOT reset by this
        method.  If they were not empty before, data will simply be added to
        them.
        """
        # This function works in two parts: first we put a few things in
        # user_ns, and we sync that contents into user_ns_hidden so that these
        # initial variables aren't shown by %who.  After the sync, we add the
        # rest of what we *do* want the user to see with %who even on a new
        # session (probably nothing, so they really only see their own stuff)

        # The user dict must *always* have a __builtin__ reference to the
        # Python standard __builtin__ namespace,  which must be imported.
        # This is so that certain operations in prompt evaluation can be
        # reliably executed with builtins.  Note that we can NOT use
        # __builtins__ (note the 's'),  because that can either be a dict or a
        # module, and can even mutate at runtime, depending on the context
        # (Python makes no guarantees on it).  In contrast, __builtin__ is
        # always a module object, though it must be explicitly imported.

        # For more details:
        # http://mail.python.org/pipermail/python-dev/2001-April/014068.html
        ns = {}

        # make global variables for user access to the histories
        if self.history_manager is not None:
            ns["_ih"] = self.history_manager.input_hist_parsed
            ns["_oh"] = self.history_manager.output_hist
            ns["_dh"] = self.history_manager.dir_hist

            # user aliases to input and output histories.  These shouldn't show up
            # in %who, as they can have very large reprs.
            ns["In"] = self.history_manager.input_hist_parsed
            ns["Out"] = self.history_manager.output_hist

        # Store myself as the public api!!!
        ns['get_ipython'] = self.get_ipython

        ns['exit'] = self.exiter
        ns['quit'] = self.exiter
        ns["open"] = _modified_open

        # Sync what we've added so far to user_ns_hidden so these aren't seen
        # by %who
        self.user_ns_hidden.update(ns)

        # Anything put into ns now would show up in %who.  Think twice before
        # putting anything here, as we really want %who to show the user their
        # stuff, not our variables.

        # Finally, update the real user's namespace
        self.user_ns.update(ns)

    @property
    def all_ns_refs(self):
        """Get a list of references to all the namespace dictionaries in which
        IPython might store a user-created object.

        Note that this does not include the displayhook, which also caches
        objects from the output."""
        return [self.user_ns, self.user_global_ns, self.user_ns_hidden] + \
               [m.__dict__ for m in self._main_mod_cache.values()]

    def reset(self, new_session=True, aggressive=False):
        """Clear all internal namespaces, and attempt to release references to
        user objects.

        If new_session is True, a new history session will be opened.
        """
        # Clear histories
        if self.history_manager is not None:
            self.history_manager.reset(new_session)
        # Reset counter used to index all histories
        if new_session:
            self.execution_count = 1

        # Reset last execution result
        self.last_execution_succeeded = True
        self.last_execution_result = None

        # Flush cached output items
        if self.displayhook.do_full_cache:
            self.displayhook.flush()

        # The main execution namespaces must be cleared very carefully,
        # skipping the deletion of the builtin-related keys, because doing so
        # would cause errors in many object's __del__ methods.
        if self.user_ns is not self.user_global_ns:
            self.user_ns.clear()
        ns = self.user_global_ns
        drop_keys = set(ns.keys())
        drop_keys.discard('__builtin__')
        drop_keys.discard('__builtins__')
        drop_keys.discard('__name__')
        for k in drop_keys:
            del ns[k]

        self.user_ns_hidden.clear()

        # Restore the user namespaces to minimal usability
        self.init_user_ns()
        if aggressive and not hasattr(self, "_sys_modules_keys"):
            print("Cannot restore sys.module, no snapshot")
        elif aggressive:
            print("culling sys module...")
            current_keys = set(sys.modules.keys())
            for k in current_keys - self._sys_modules_keys:
                if k.startswith("multiprocessing"):
                    continue
                del sys.modules[k]

        # Restore the default and user aliases
        self.alias_manager.clear_aliases()
        self.alias_manager.init_aliases()

        # Now define aliases that only make sense on the terminal, because they
        # need direct access to the console in a way that we can't emulate in
        # GUI or web frontend
        if os.name == 'posix':
            for cmd in ('clear', 'more', 'less', 'man'):
                if cmd not in self.magics_manager.magics['line']:
                    self.alias_manager.soft_define_alias(cmd, cmd)

        # Flush the private list of module references kept for script
        # execution protection
        self.clear_main_mod_cache()

    def del_var(self, varname, by_name=False):
        """Delete a variable from the various namespaces, so that, as
        far as possible, we're not keeping any hidden references to it.

        Parameters
        ----------
        varname : str
            The name of the variable to delete.
        by_name : bool
            If True, delete variables with the given name in each
            namespace. If False (default), find the variable in the user
            namespace, and delete references to it.
        """
        if varname in ('__builtin__', '__builtins__'):
            raise ValueError("Refusing to delete %s" % varname)

        ns_refs = self.all_ns_refs

        if by_name:                    # Delete by name
            for ns in ns_refs:
                try:
                    del ns[varname]
                except KeyError:
                    pass
        else:                         # Delete by object
            try:
                obj = self.user_ns[varname]
            except KeyError as e:
                raise NameError("name '%s' is not defined" % varname) from e
            # Also check in output history
            assert self.history_manager is not None
            ns_refs.append(self.history_manager.output_hist)
            for ns in ns_refs:
                to_delete = [n for n, o in ns.items() if o is obj]
                for name in to_delete:
                    del ns[name]

            # Ensure it is removed from the last execution result
            if self.last_execution_result.result is obj:
                self.last_execution_result = None

            # displayhook keeps extra references, but not in a dictionary
            for name in ('_', '__', '___'):
                if getattr(self.displayhook, name) is obj:
                    setattr(self.displayhook, name, None)

    def reset_selective(self, regex=None):
        """Clear selective variables from internal namespaces based on a
        specified regular expression.

        Parameters
        ----------
        regex : string or compiled pattern, optional
            A regular expression pattern that will be used in searching
            variable names in the users namespaces.
        """
        if regex is not None:
            try:
                m = re.compile(regex)
            except TypeError as e:
                raise TypeError('regex must be a string or compiled pattern') from e
            # Search for keys in each namespace that match the given regex
            # If a match is found, delete the key/value pair.
            for ns in self.all_ns_refs:
                for var in ns:
                    if m.search(var):
                        del ns[var]

    def push(self, variables, interactive=True):
        """Inject a group of variables into the IPython user namespace.

        Parameters
        ----------
        variables : dict, str or list/tuple of str
            The variables to inject into the user's namespace.  If a dict, a
            simple update is done.  If a str, the string is assumed to have
            variable names separated by spaces.  A list/tuple of str can also
            be used to give the variable names.  If just the variable names are
            give (list/tuple/str) then the variable values looked up in the
            callers frame.
        interactive : bool
            If True (default), the variables will be listed with the ``who``
            magic.
        """
        vdict = None

        # We need a dict of name/value pairs to do namespace updates.
        if isinstance(variables, dict):
            vdict = variables
        elif isinstance(variables, (str, list, tuple)):
            if isinstance(variables, str):
                vlist = variables.split()
            else:
                vlist = list(variables)
            vdict = {}
            cf = sys._getframe(1)
            for name in vlist:
                try:
                    vdict[name] = eval(name, cf.f_globals, cf.f_locals)
                except:
                    print('Could not get variable %s from %s' %
                           (name,cf.f_code.co_name))
        else:
            raise ValueError('variables must be a dict/str/list/tuple')

        # Propagate variables to user namespace
        self.user_ns.update(vdict)

        # And configure interactive visibility
        user_ns_hidden = self.user_ns_hidden
        if interactive:
            for name in vdict:
                user_ns_hidden.pop(name, None)
        else:
            user_ns_hidden.update(vdict)

    def drop_by_id(self, variables):
        """Remove a dict of variables from the user namespace, if they are the
        same as the values in the dictionary.

        This is intended for use by extensions: variables that they've added can
        be taken back out if they are unloaded, without removing any that the
        user has overwritten.

        Parameters
        ----------
        variables : dict
            A dictionary mapping object names (as strings) to the objects.
        """
        for name, obj in variables.items():
            if name in self.user_ns and self.user_ns[name] is obj:
                del self.user_ns[name]
                self.user_ns_hidden.pop(name, None)

    #-------------------------------------------------------------------------
    # Things related to object introspection
    #-------------------------------------------------------------------------
    @staticmethod
    def _find_parts(oname: str) -> Tuple[bool, ListType[str]]:
        """
        Given an object name, return a list of parts of this object name.

        Basically split on docs when using attribute access,
        and extract the value when using square bracket.


        For example foo.bar[3].baz[x] -> foo, bar, 3, baz, x


        Returns
        -------
        parts_ok: bool
            whether we were properly able to parse parts.
        parts: list of str
            extracted parts



        """
        raw_parts = oname.split(".")
        parts = []
        parts_ok = True
        for p in raw_parts:
            if p.endswith("]"):
                var, *indices = p.split("[")
                if not var.isidentifier():
                    parts_ok = False
                    break
                parts.append(var)
                for ind in indices:
                    if ind[-1] != "]" and not is_integer_string(ind[:-1]):
                        parts_ok = False
                        break
                    parts.append(ind[:-1])
                continue

            if not p.isidentifier():
                parts_ok = False
            parts.append(p)

        return parts_ok, parts

    def _ofind(
        self, oname: str, namespaces: Optional[Sequence[Tuple[str, AnyType]]] = None
    ) -> OInfo:
        """Find an object in the available namespaces.


        Returns
        -------
        OInfo with fields:
          - ismagic
          - isalias
          - found
          - obj
          - namespac
          - parent

        Has special code to detect magic functions.
        """
        oname = oname.strip()
        parts_ok, parts = self._find_parts(oname)

        if (
            not oname.startswith(ESC_MAGIC)
            and not oname.startswith(ESC_MAGIC2)
            and not parts_ok
        ):
            return OInfo(
                ismagic=False,
                isalias=False,
                found=False,
                obj=None,
                namespace=None,
                parent=None,
            )

        if namespaces is None:
            # Namespaces to search in:
            # Put them in a list. The order is important so that we
            # find things in the same order that Python finds them.
            namespaces = [ ('Interactive', self.user_ns),
                           ('Interactive (global)', self.user_global_ns),
                           ('Python builtin', builtin_mod.__dict__),
                           ]

        ismagic = False
        isalias = False
        found = False
        ospace = None
        parent = None
        obj = None


        # Look for the given name by splitting it in parts.  If the head is
        # found, then we look for all the remaining parts as members, and only
        # declare success if we can find them all.
        oname_parts = parts
        oname_head, oname_rest = oname_parts[0],oname_parts[1:]
        for nsname,ns in namespaces:
            try:
                obj = ns[oname_head]
            except KeyError:
                continue
            else:
                for idx, part in enumerate(oname_rest):
                    try:
                        parent = obj
                        # The last part is looked up in a special way to avoid
                        # descriptor invocation as it may raise or have side
                        # effects.
                        if idx == len(oname_rest) - 1:
                            obj = self._getattr_property(obj, part)
                        else:
                            if is_integer_string(part):
                                obj = obj[int(part)]
                            else:
                                obj = getattr(obj, part)
                    except:
                        # Blanket except b/c some badly implemented objects
                        # allow __getattr__ to raise exceptions other than
                        # AttributeError, which then crashes IPython.
                        break
                else:
                    # If we finish the for loop (no break), we got all members
                    found = True
                    ospace = nsname
                    break  # namespace loop

        # Try to see if it's magic
        if not found:
            obj = None
            if oname.startswith(ESC_MAGIC2):
                oname = oname.lstrip(ESC_MAGIC2)
                obj = self.find_cell_magic(oname)
            elif oname.startswith(ESC_MAGIC):
                oname = oname.lstrip(ESC_MAGIC)
                obj = self.find_line_magic(oname)
            else:
                # search without prefix, so run? will find %run?
                obj = self.find_line_magic(oname)
                if obj is None:
                    obj = self.find_cell_magic(oname)
            if obj is not None:
                found = True
                ospace = 'IPython internal'
                ismagic = True
                isalias = isinstance(obj, Alias)

        # Last try: special-case some literals like '', [], {}, etc:
        if not found and oname_head in ["''",'""','[]','{}','()']:
            obj = eval(oname_head)
            found = True
            ospace = 'Interactive'

        return OInfo(
            obj=obj,
            found=found,
            parent=parent,
            ismagic=ismagic,
            isalias=isalias,
            namespace=ospace,
        )

    @staticmethod
    def _getattr_property(obj, attrname):
        """Property-aware getattr to use in object finding.

        If attrname represents a property, return it unevaluated (in case it has
        side effects or raises an error.

        """
        if not isinstance(obj, type):
            try:
                # `getattr(type(obj), attrname)` is not guaranteed to return
                # `obj`, but does so for property:
                #
                # property.__get__(self, None, cls) -> self
                #
                # The universal alternative is to traverse the mro manually
                # searching for attrname in class dicts.
                if is_integer_string(attrname):
                    return obj[int(attrname)]
                else:
                    attr = getattr(type(obj), attrname)
            except AttributeError:
                pass
            else:
                # This relies on the fact that data descriptors (with both
                # __get__ & __set__ magic methods) take precedence over
                # instance-level attributes:
                #
                #    class A(object):
                #        @property
                #        def foobar(self): return 123
                #    a = A()
                #    a.__dict__['foobar'] = 345
                #    a.foobar  # == 123
                #
                # So, a property may be returned right away.
                if isinstance(attr, property):
                    return attr

        # Nothing helped, fall back.
        return getattr(obj, attrname)

    def _object_find(self, oname, namespaces=None) -> OInfo:
        """Find an object and return a struct with info about it."""
        return self._ofind(oname, namespaces)

    def _inspect(self, meth, oname: str, namespaces=None, **kw):
        """Generic interface to the inspector system.

        This function is meant to be called by pdef, pdoc & friends.
        """
        info: OInfo = self._object_find(oname, namespaces)
        if self.sphinxify_docstring:
            if sphinxify is None:
                raise ImportError("Module ``docrepr`` required but missing")
            docformat = sphinxify(self.object_inspect(oname))
        else:
            docformat = None
        if info.found or hasattr(info.parent, oinspect.HOOK_NAME):
            pmethod = getattr(self.inspector, meth)
            # TODO: only apply format_screen to the plain/text repr of the mime
            # bundle.
            formatter = format_screen if info.ismagic else docformat
            if meth == 'pdoc':
                pmethod(info.obj, oname, formatter)
            elif meth == 'pinfo':
                pmethod(
                    info.obj,
                    oname,
                    formatter,
                    info,
                    enable_html_pager=self.enable_html_pager,
                    **kw,
                )
            else:
                pmethod(info.obj, oname)
        else:
            print('Object `%s` not found.' % oname)
            return 'not found'  # so callers can take other action

    def object_inspect(self, oname, detail_level=0):
        """Get object info about oname"""
        with self.builtin_trap:
            info = self._object_find(oname)
            if info.found:
                return self.inspector.info(info.obj, oname, info=info,
                            detail_level=detail_level
                )
            else:
                return oinspect.object_info(name=oname, found=False)

    def object_inspect_text(self, oname, detail_level=0):
        """Get object info as formatted text"""
        return self.object_inspect_mime(oname, detail_level)['text/plain']

    def object_inspect_mime(self, oname, detail_level=0, omit_sections=()):
        """Get object info as a mimebundle of formatted representations.

        A mimebundle is a dictionary, keyed by mime-type.
        It must always have the key `'text/plain'`.
        """
        with self.builtin_trap:
            info = self._object_find(oname)
            if info.found:
                if self.sphinxify_docstring:
                    if sphinxify is None:
                        raise ImportError("Module ``docrepr`` required but missing")
                    docformat = sphinxify(self.object_inspect(oname))
                else:
                    docformat = None
                return self.inspector._get_info(
                    info.obj,
                    oname,
                    info=info,
                    detail_level=detail_level,
                    formatter=docformat,
                    omit_sections=omit_sections,
                )
            else:
                raise KeyError(oname)

    #-------------------------------------------------------------------------
    # Things related to history management
    #-------------------------------------------------------------------------

    def init_history(self):
        """Sets up the command history, and starts regular autosaves."""
        self.history_manager = HistoryManager(shell=self, parent=self)
        self.configurables.append(self.history_manager)

    #-------------------------------------------------------------------------
    # Things related to exception handling and tracebacks (not debugging)
    #-------------------------------------------------------------------------

    debugger_cls = InterruptiblePdb

    def init_traceback_handlers(self, custom_exceptions) -> None:
        # Syntax error handler.
        self.SyntaxTB = ultratb.SyntaxTB(theme_name=self.colors)

        # The interactive one is initialized with an offset, meaning we always
        # want to remove the topmost item in the traceback, which is our own
        # internal code. Valid modes: ['Plain','Context','Verbose','Minimal']
        self.InteractiveTB = ultratb.AutoFormattedTB(
            mode=self.xmode,
            theme_name=self.colors,
            tb_offset=1,
            debugger_cls=self.debugger_cls,
        )

        # The instance will store a pointer to the system-wide exception hook,
        # so that runtime code (such as magics) can access it.  This is because
        # during the read-eval loop, it may get temporarily overwritten.
        self.sys_excepthook = sys.excepthook

        # and add any custom exception handlers the user may have specified
        self.set_custom_exc(*custom_exceptions)

        # Set the exception mode
        self.InteractiveTB.set_mode(mode=self.xmode)

    def set_custom_exc(self, exc_tuple, handler):
        """set_custom_exc(exc_tuple, handler)

        Set a custom exception handler, which will be called if any of the
        exceptions in exc_tuple occur in the mainloop (specifically, in the
        run_code() method).

        Parameters
        ----------
        exc_tuple : tuple of exception classes
            A *tuple* of exception classes, for which to call the defined
            handler.  It is very important that you use a tuple, and NOT A
            LIST here, because of the way Python's except statement works.  If
            you only want to trap a single exception, use a singleton tuple::

                exc_tuple == (MyCustomException,)

        handler : callable
            handler must have the following signature::

                def my_handler(self, etype, value, tb, tb_offset=None):
                    ...
                    return structured_traceback

            Your handler must return a structured traceback (a list of strings),
            or None.

            This will be made into an instance method (via types.MethodType)
            of IPython itself, and it will be called if any of the exceptions
            listed in the exc_tuple are caught. If the handler is None, an
            internal basic one is used, which just prints basic info.

            To protect IPython from crashes, if your handler ever raises an
            exception or returns an invalid result, it will be immediately
            disabled.

        Notes
        -----
        WARNING: by putting in your own exception handler into IPython's main
        execution loop, you run a very good chance of nasty crashes.  This
        facility should only be used if you really know what you are doing.
        """

        if not isinstance(exc_tuple, tuple):
            raise TypeError("The custom exceptions must be given as a tuple.")

        def dummy_handler(self, etype, value, tb, tb_offset=None):
            print('*** Simple custom exception handler ***')
            print('Exception type :', etype)
            print('Exception value:', value)
            print('Traceback      :', tb)

        def validate_stb(stb):
            """validate structured traceback return type

            return type of CustomTB *should* be a list of strings, but allow
            single strings or None, which are harmless.

            This function will *always* return a list of strings,
            and will raise a TypeError if stb is inappropriate.
            """
            msg = "CustomTB must return list of strings, not %r" % stb
            if stb is None:
                return []
            elif isinstance(stb, str):
                return [stb]
            elif not isinstance(stb, list):
                raise TypeError(msg)
            # it's a list
            for line in stb:
                # check every element
                if not isinstance(line, str):
                    raise TypeError(msg)
            return stb

        if handler is None:
            wrapped = dummy_handler
        else:
            def wrapped(self,etype,value,tb,tb_offset=None):
                """wrap CustomTB handler, to protect IPython from user code

                This makes it harder (but not impossible) for custom exception
                handlers to crash IPython.
                """
                try:
                    stb = handler(self,etype,value,tb,tb_offset=tb_offset)
                    return validate_stb(stb)
                except:
                    # clear custom handler immediately
                    self.set_custom_exc((), None)
                    print("Custom TB Handler failed, unregistering", file=sys.stderr)
                    # show the exception in handler first
                    stb = self.InteractiveTB.structured_traceback(*sys.exc_info())
                    print(self.InteractiveTB.stb2text(stb))
                    print("The original exception:")
                    stb = self.InteractiveTB.structured_traceback(
                        etype, value, tb, tb_offset=tb_offset
                    )
                return stb

        self.CustomTB = types.MethodType(wrapped,self)
        self.custom_exceptions = exc_tuple

    def excepthook(self, etype, value, tb):
        """One more defense for GUI apps that call sys.excepthook.

        GUI frameworks like wxPython trap exceptions and call
        sys.excepthook themselves.  I guess this is a feature that
        enables them to keep running after exceptions that would
        otherwise kill their mainloop. This is a bother for IPython
        which expects to catch all of the program exceptions with a try:
        except: statement.

        Normally, IPython sets sys.excepthook to a CrashHandler instance, so if
        any app directly invokes sys.excepthook, it will look to the user like
        IPython crashed.  In order to work around this, we can disable the
        CrashHandler and replace it with this excepthook instead, which prints a
        regular traceback using our InteractiveTB.  In this fashion, apps which
        call sys.excepthook will generate a regular-looking exception from
        IPython, and the CrashHandler will only be triggered by real IPython
        crashes.

        This hook should be used sparingly, only in places which are not likely
        to be true IPython errors.
        """
        self.showtraceback((etype, value, tb), tb_offset=0)

    def _get_exc_info(self, exc_tuple=None):
        """get exc_info from a given tuple, sys.exc_info() or sys.last_type etc.

        Ensures sys.last_type,value,traceback hold the exc_info we found,
        from whichever source.

        raises ValueError if none of these contain any information
        """
        if exc_tuple is None:
            etype, value, tb = sys.exc_info()
        else:
            etype, value, tb = exc_tuple

        if etype is None:
            if hasattr(sys, 'last_type'):
                etype, value, tb = sys.last_type, sys.last_value, \
                                   sys.last_traceback

        if etype is None:
            raise ValueError("No exception to find")

        # Now store the exception info in sys.last_type etc.
        # WARNING: these variables are somewhat deprecated and not
        # necessarily safe to use in a threaded environment, but tools
        # like pdb depend on their existence, so let's set them.  If we
        # find problems in the field, we'll need to revisit their use.
        sys.last_type = etype
        sys.last_value = value
        sys.last_traceback = tb
        if sys.version_info >= (3, 12):
            sys.last_exc = value

        return etype, value, tb

    def show_usage_error(self, exc):
        """Show a short message for UsageErrors

        These are special exceptions that shouldn't show a traceback.
        """
        print("UsageError: %s" % exc, file=sys.stderr)

    def get_exception_only(self, exc_tuple=None):
        """
        Return as a string (ending with a newline) the exception that
        just occurred, without any traceback.
        """
        etype, value, tb = self._get_exc_info(exc_tuple)
        msg = traceback.format_exception_only(etype, value)
        return ''.join(msg)

    def showtraceback(self, exc_tuple=None, filename=None, tb_offset=None,
                      exception_only=False, running_compiled_code=False):
        """Display the exception that just occurred.

        If nothing is known about the exception, this is the method which
        should be used throughout the code for presenting user tracebacks,
        rather than directly invoking the InteractiveTB object.

        A specific showsyntaxerror() also exists, but this method can take
        care of calling it if needed, so unless you are explicitly catching a
        SyntaxError exception, don't try to analyze the stack manually and
        simply call this method."""

        try:
            try:
                etype, value, tb = self._get_exc_info(exc_tuple)
            except ValueError:
                print('No traceback available to show.', file=sys.stderr)
                return

            if issubclass(etype, SyntaxError):
                # Though this won't be called by syntax errors in the input
                # line, there may be SyntaxError cases with imported code.
                self.showsyntaxerror(filename, running_compiled_code)
            elif etype is UsageError:
                self.show_usage_error(value)
            else:
                if exception_only:
                    stb = ['An exception has occurred, use %tb to see '
                           'the full traceback.\n']
                    stb.extend(self.InteractiveTB.get_exception_only(etype,
                                                                     value))
                else:

                    def contains_exceptiongroup(val):
                        if val is None:
                            return False
                        return isinstance(
                            val, BaseExceptionGroup
                        ) or contains_exceptiongroup(val.__context__)

                    if contains_exceptiongroup(value):
                        # fall back to native exception formatting until ultratb
                        # supports exception groups
                        traceback.print_exc()
                    else:
                        try:
                            # Exception classes can customise their traceback - we
                            # use this in IPython.parallel for exceptions occurring
                            # in the engines. This should return a list of strings.
                            if hasattr(value, "_render_traceback_"):
                                stb = value._render_traceback_()
                            else:
                                stb = self.InteractiveTB.structured_traceback(
                                    etype, value, tb, tb_offset=tb_offset
                                )

                        except Exception:
                            print(
                                "Unexpected exception formatting exception. Falling back to standard exception"
                            )
                            traceback.print_exc()
                            return None

                        self._showtraceback(etype, value, stb)
                    if self.call_pdb:
                        # drop into debugger
                        self.debugger(force=True)
                    return

                # Actually show the traceback
                self._showtraceback(etype, value, stb)

        except KeyboardInterrupt:
            print('\n' + self.get_exception_only(), file=sys.stderr)

    def _showtraceback(self, etype, evalue, stb: list[str]):
        """Actually show a traceback.

        Subclasses may override this method to put the traceback on a different
        place, like a side channel.
        """
        val = self.InteractiveTB.stb2text(stb)
        self.showing_traceback = True
        try:
            print(val)
        except UnicodeEncodeError:
            print(val.encode("utf-8", "backslashreplace").decode())
        self.showing_traceback = False

    def showsyntaxerror(self, filename=None, running_compiled_code=False):
        """Display the syntax error that just occurred.

        This doesn't display a stack trace because there isn't one.

        If a filename is given, it is stuffed in the exception instead
        of what was there before (because Python's parser always uses
        "<string>" when reading from a string).

        If the syntax error occurred when running a compiled code (i.e. running_compile_code=True),
        longer stack trace will be displayed.
        """
        etype, value, last_traceback = self._get_exc_info()

        if filename and issubclass(etype, SyntaxError):
            try:
                value.filename = filename
            except:
                # Not the format we expect; leave it alone
                pass

        # If the error occurred when executing compiled code, we should provide full stacktrace.
        elist = traceback.extract_tb(last_traceback) if running_compiled_code else []
        stb = self.SyntaxTB.structured_traceback(etype, value, elist)
        self._showtraceback(etype, value, stb)

    # This is overridden in TerminalInteractiveShell to show a message about
    # the %paste magic.
    def showindentationerror(self):
        """Called by _run_cell when there's an IndentationError in code entered
        at the prompt.

        This is overridden in TerminalInteractiveShell to show a message about
        the %paste magic."""
        self.showsyntaxerror()

    @skip_doctest
    def set_next_input(self, s, replace=False):
        """ Sets the 'default' input string for the next command line.

        Example::

            In [1]: _ip.set_next_input("Hello Word")
            In [2]: Hello Word_  # cursor is here
        """
        self.rl_next_input = s

    #-------------------------------------------------------------------------
    # Things related to text completion
    #-------------------------------------------------------------------------

    def init_completer(self):
        """Initialize the completion machinery.

        This creates completion machinery that can be used by client code,
        either interactively in-process (typically triggered by the readline
        library), programmatically (such as in test suites) or out-of-process
        (typically over the network by remote frontends).
        """
        from IPython.core.completer import IPCompleter
        from IPython.core.completerlib import (
            cd_completer,
            magic_run_completer,
            module_completer,
            reset_completer,
        )

        self.Completer = IPCompleter(shell=self,
                                     namespace=self.user_ns,
                                     global_namespace=self.user_global_ns,
                                     parent=self,
                                     )
        self.configurables.append(self.Completer)

        # Add custom completers to the basic ones built into IPCompleter
        sdisp = self.strdispatchers.get('complete_command', StrDispatch())
        self.strdispatchers['complete_command'] = sdisp
        self.Completer.custom_completers = sdisp

        self.set_hook('complete_command', module_completer, str_key = 'import')
        self.set_hook('complete_command', module_completer, str_key = 'from')
        self.set_hook('complete_command', module_completer, str_key = '%aimport')
        self.set_hook('complete_command', magic_run_completer, str_key = '%run')
        self.set_hook('complete_command', cd_completer, str_key = '%cd')
        self.set_hook('complete_command', reset_completer, str_key = '%reset')

    @skip_doctest
    def complete(self, text, line=None, cursor_pos=None):
        """Return the completed text and a list of completions.

        Parameters
        ----------
        text : string
            A string of text to be completed on.  It can be given as empty and
            instead a line/position pair are given.  In this case, the
            completer itself will split the line like readline does.
        line : string, optional
            The complete line that text is part of.
        cursor_pos : int, optional
            The position of the cursor on the input line.

        Returns
        -------
        text : string
            The actual text that was completed.
        matches : list
            A sorted list with all possible completions.

        Notes
        -----
        The optional arguments allow the completion to take more context into
        account, and are part of the low-level completion API.

        This is a wrapper around the completion mechanism, similar to what
        readline does at the command line when the TAB key is hit.  By
        exposing it as a method, it can be used by other non-readline
        environments (such as GUIs) for text completion.

        Examples
        --------
        In [1]: x = 'hello'

        In [2]: _ip.complete('x.l')
        Out[2]: ('x.l', ['x.ljust', 'x.lower', 'x.lstrip'])
        """

        # Inject names into __builtin__ so we can complete on the added names.
        with self.builtin_trap:
            return self.Completer.complete(text, line, cursor_pos)

    def set_custom_completer(self, completer, pos=0) -> None:
        """Adds a new custom completer function.

        The position argument (defaults to 0) is the index in the completers
        list where you want the completer to be inserted.

        `completer` should have the following signature::

            def completion(self: Completer, text: string) -> List[str]:
                raise NotImplementedError

        It will be bound to the current Completer instance and pass some text
        and return a list with current completions to suggest to the user.
        """

        newcomp = types.MethodType(completer, self.Completer)
        self.Completer.custom_matchers.insert(pos,newcomp)

    def set_completer_frame(self, frame=None):
        """Set the frame of the completer."""
        if frame:
            self.Completer.namespace = frame.f_locals
            self.Completer.global_namespace = frame.f_globals
        else:
            self.Completer.namespace = self.user_ns
            self.Completer.global_namespace = self.user_global_ns

    #-------------------------------------------------------------------------
    # Things related to magics
    #-------------------------------------------------------------------------

    def init_magics(self):
        from IPython.core import magics as m
        self.magics_manager = magic.MagicsManager(shell=self,
                                   parent=self,
                                   user_magics=m.UserMagics(self))
        self.configurables.append(self.magics_manager)

        # Expose as public API from the magics manager
        self.register_magics = self.magics_manager.register

        self.register_magics(m.AutoMagics, m.BasicMagics, m.CodeMagics,
            m.ConfigMagics, m.DisplayMagics, m.ExecutionMagics,
            m.ExtensionMagics, m.HistoryMagics, m.LoggingMagics,
            m.NamespaceMagics, m.OSMagics, m.PackagingMagics,
            m.PylabMagics, m.ScriptMagics,
        )
        self.register_magics(m.AsyncMagics)

        # Register Magic Aliases
        mman = self.magics_manager
        # FIXME: magic aliases should be defined by the Magics classes
        # or in MagicsManager, not here
        mman.register_alias('ed', 'edit')
        mman.register_alias('hist', 'history')
        mman.register_alias('rep', 'recall')
        mman.register_alias('SVG', 'svg', 'cell')
        mman.register_alias('HTML', 'html', 'cell')
        mman.register_alias('file', 'writefile', 'cell')

        # FIXME: Move the color initialization to the DisplayHook, which
        # should be split into a prompt manager and displayhook. We probably
        # even need a centralize colors management object.
        self.run_line_magic('colors', self.colors)

    # Defined here so that it's included in the documentation
    @functools.wraps(magic.MagicsManager.register_function)
    def register_magic_function(self, func, magic_kind='line', magic_name=None):
        self.magics_manager.register_function(
            func, magic_kind=magic_kind, magic_name=magic_name
        )

    def _find_with_lazy_load(self, /, type_, magic_name: str):
        """
        Try to find a magic potentially lazy-loading it.

        Parameters
        ----------

        type_: "line"|"cell"
            the type of magics we are trying to find/lazy load.
        magic_name: str
            The name of the magic we are trying to find/lazy load


        Note that this may have any side effects
        """
        finder = {"line": self.find_line_magic, "cell": self.find_cell_magic}[type_]
        fn = finder(magic_name)
        if fn is not None:
            return fn
        lazy = self.magics_manager.lazy_magics.get(magic_name)
        if lazy is None:
            return None

        self.run_line_magic("load_ext", lazy)
        res = finder(magic_name)
        return res

    def run_line_magic(self, magic_name: str, line: str, _stack_depth=1):
        """Execute the given line magic.

        Parameters
        ----------
        magic_name : str
            Name of the desired magic function, without '%' prefix.
        line : str
            The rest of the input line as a single string.
        _stack_depth : int
            If run_line_magic() is called from magic() then _stack_depth=2.
            This is added to ensure backward compatibility for use of 'get_ipython().magic()'
        """
        fn = self._find_with_lazy_load("line", magic_name)
        if fn is None:
            lazy = self.magics_manager.lazy_magics.get(magic_name)
            if lazy:
                self.run_line_magic("load_ext", lazy)
                fn = self.find_line_magic(magic_name)
        if fn is None:
            cm = self.find_cell_magic(magic_name)
            etpl = "Line magic function `%%%s` not found%s."
            extra = '' if cm is None else (' (But cell magic `%%%%%s` exists, '
                                    'did you mean that instead?)' % magic_name )
            raise UsageError(etpl % (magic_name, extra))
        else:
            # Note: this is the distance in the stack to the user's frame.
            # This will need to be updated if the internal calling logic gets
            # refactored, or else we'll be expanding the wrong variables.

            # Determine stack_depth depending on where run_line_magic() has been called
            stack_depth = _stack_depth
            if getattr(fn, magic.MAGIC_NO_VAR_EXPAND_ATTR, False):
                # magic has opted out of var_expand
                magic_arg_s = line
            else:
                magic_arg_s = self.var_expand(line, stack_depth)
            # Put magic args in a list so we can call with f(*a) syntax
            args = [magic_arg_s]
            kwargs = {}
            # Grab local namespace if we need it:
            if getattr(fn, "needs_local_scope", False):
                kwargs['local_ns'] = self.get_local_scope(stack_depth)
            with self.builtin_trap:
                result = fn(*args, **kwargs)

            # The code below prevents the output from being displayed
            # when using magics with decorator @output_can_be_silenced
            # when the last Python token in the expression is a ';'.
            if getattr(fn, magic.MAGIC_OUTPUT_CAN_BE_SILENCED, False):
                if DisplayHook.semicolon_at_end_of_expression(magic_arg_s):
                    return None

            return result

    def get_local_scope(self, stack_depth):
        """Get local scope at given stack depth.

        Parameters
        ----------
        stack_depth : int
            Depth relative to calling frame
        """
        return sys._getframe(stack_depth + 1).f_locals

    def run_cell_magic(self, magic_name, line, cell):
        """Execute the given cell magic.

        Parameters
        ----------
        magic_name : str
            Name of the desired magic function, without '%' prefix.
        line : str
            The rest of the first input line as a single string.
        cell : str
            The body of the cell as a (possibly multiline) string.
        """
        fn = self._find_with_lazy_load("cell", magic_name)
        if fn is None:
            lm = self.find_line_magic(magic_name)
            etpl = "Cell magic `%%{0}` not found{1}."
            extra = '' if lm is None else (' (But line magic `%{0}` exists, '
                            'did you mean that instead?)'.format(magic_name))
            raise UsageError(etpl.format(magic_name, extra))
        elif cell == '':
            message = '%%{0} is a cell magic, but the cell body is empty.'.format(magic_name)
            if self.find_line_magic(magic_name) is not None:
                message += ' Did you mean the line magic %{0} (single %)?'.format(magic_name)
            raise UsageError(message)
        else:
            # Note: this is the distance in the stack to the user's frame.
            # This will need to be updated if the internal calling logic gets
            # refactored, or else we'll be expanding the wrong variables.
            stack_depth = 2
            if getattr(fn, magic.MAGIC_NO_VAR_EXPAND_ATTR, False):
                # magic has opted out of var_expand
                magic_arg_s = line
            else:
                magic_arg_s = self.var_expand(line, stack_depth)
            kwargs = {}
            if getattr(fn, "needs_local_scope", False):
                kwargs['local_ns'] = self.user_ns

            with self.builtin_trap:
                args = (magic_arg_s, cell)
                result = fn(*args, **kwargs)

            # The code below prevents the output from being displayed
            # when using magics with decorator @output_can_be_silenced
            # when the last Python token in the expression is a ';'.
            if getattr(fn, magic.MAGIC_OUTPUT_CAN_BE_SILENCED, False):
                if DisplayHook.semicolon_at_end_of_expression(cell):
                    return None

            return result

    def find_line_magic(self, magic_name):
        """Find and return a line magic by name.

        Returns None if the magic isn't found."""
        return self.magics_manager.magics['line'].get(magic_name)

    def find_cell_magic(self, magic_name):
        """Find and return a cell magic by name.

        Returns None if the magic isn't found."""
        return self.magics_manager.magics['cell'].get(magic_name)

    def find_magic(self, magic_name, magic_kind='line'):
        """Find and return a magic of the given type by name.

        Returns None if the magic isn't found."""
        return self.magics_manager.magics[magic_kind].get(magic_name)

    #-------------------------------------------------------------------------
    # Things related to macros
    #-------------------------------------------------------------------------

    def define_macro(self, name, themacro):
        """Define a new macro

        Parameters
        ----------
        name : str
            The name of the macro.
        themacro : str or Macro
            The action to do upon invoking the macro.  If a string, a new
            Macro object is created by passing the string to it.
        """

        from IPython.core import macro

        if isinstance(themacro, str):
            themacro = macro.Macro(themacro)
        if not isinstance(themacro, macro.Macro):
            raise ValueError('A macro must be a string or a Macro instance.')
        self.user_ns[name] = themacro

    #-------------------------------------------------------------------------
    # Things related to the running of system commands
    #-------------------------------------------------------------------------

    def system_piped(self, cmd):
        """Call the given cmd in a subprocess, piping stdout/err

        Parameters
        ----------
        cmd : str
            Command to execute (can not end in '&', as background processes are
            not supported.  Should not be a command that expects input
            other than simple text.
        """
        if cmd.rstrip().endswith('&'):
            # this is *far* from a rigorous test
            # We do not support backgrounding processes because we either use
            # pexpect or pipes to read from.  Users can always just call
            # os.system() or use ip.system=ip.system_raw
            # if they really want a background process.
            raise OSError("Background processes not supported.")

        # we explicitly do NOT return the subprocess status code, because
        # a non-None value would trigger :func:`sys.displayhook` calls.
        # Instead, we store the exit_code in user_ns.
        self.user_ns['_exit_code'] = system(self.var_expand(cmd, depth=1))

    def system_raw(self, cmd):
        """Call the given cmd in a subprocess using os.system on Windows or
        subprocess.call using the system shell on other platforms.

        Parameters
        ----------
        cmd : str
            Command to execute.
        """
        cmd = self.var_expand(cmd, depth=1)
        # warn if there is an IPython magic alternative.
        if cmd == "":
            main_cmd = ""
        else:
            main_cmd = cmd.split()[0]
        has_magic_alternatives = ("pip", "conda", "cd")

        if main_cmd in has_magic_alternatives:
            warnings.warn(
                (
                    "You executed the system command !{0} which may not work "
                    "as expected. Try the IPython magic %{0} instead."
                ).format(main_cmd)
            )

        # protect os.system from UNC paths on Windows, which it can't handle:
        if sys.platform == 'win32':
            from IPython.utils._process_win32 import AvoidUNCPath
            with AvoidUNCPath() as path:
                if path is not None:
                    cmd = '"pushd %s &&"%s' % (path, cmd)
                try:
                    ec = os.system(cmd)
                except KeyboardInterrupt:
                    print('\n' + self.get_exception_only(), file=sys.stderr)
                    ec = -2
        else:
            # For posix the result of the subprocess.call() below is an exit
            # code, which by convention is zero for success, positive for
            # program failure.  Exit codes above 128 are reserved for signals,
            # and the formula for converting a signal to an exit code is usually
            # signal_number+128.  To more easily differentiate between exit
            # codes and signals, ipython uses negative numbers.  For instance
            # since control-c is signal 2 but exit code 130, ipython's
            # _exit_code variable will read -2.  Note that some shells like
            # csh and fish don't follow sh/bash conventions for exit codes.
            executable = os.environ.get('SHELL', None)
            try:
                # Use env shell instead of default /bin/sh
                ec = subprocess.call(cmd, shell=True, executable=executable)
            except KeyboardInterrupt:
                # intercept control-C; a long traceback is not useful here
                print('\n' + self.get_exception_only(), file=sys.stderr)
                ec = 130
            if ec > 128:
                ec = -(ec - 128)

        # We explicitly do NOT return the subprocess status code, because
        # a non-None value would trigger :func:`sys.displayhook` calls.
        # Instead, we store the exit_code in user_ns.  Note the semantics
        # of _exit_code: for control-c, _exit_code == -signal.SIGNIT,
        # but raising SystemExit(_exit_code) will give status 254!
        self.user_ns['_exit_code'] = ec

    # use piped system by default, because it is better behaved
    system = system_piped

    def getoutput(self, cmd, split=True, depth=0):
        """Get output (possibly including stderr) from a subprocess.

        Parameters
        ----------
        cmd : str
            Command to execute (can not end in '&', as background processes are
            not supported.
        split : bool, optional
            If True, split the output into an IPython SList.  Otherwise, an
            IPython LSString is returned.  These are objects similar to normal
            lists and strings, with a few convenience attributes for easier
            manipulation of line-based output.  You can use '?' on them for
            details.
        depth : int, optional
            How many frames above the caller are the local variables which should
            be expanded in the command string? The default (0) assumes that the
            expansion variables are in the stack frame calling this function.
        """
        if cmd.rstrip().endswith('&'):
            # this is *far* from a rigorous test
            raise OSError("Background processes not supported.")
        out = getoutput(self.var_expand(cmd, depth=depth+1))
        if split:
            out = SList(out.splitlines())
        else:
            out = LSString(out)
        return out

    #-------------------------------------------------------------------------
    # Things related to aliases
    #-------------------------------------------------------------------------

    def init_alias(self):
        self.alias_manager = AliasManager(shell=self, parent=self)
        self.configurables.append(self.alias_manager)

    #-------------------------------------------------------------------------
    # Things related to extensions
    #-------------------------------------------------------------------------

    def init_extension_manager(self):
        self.extension_manager = ExtensionManager(shell=self, parent=self)
        self.configurables.append(self.extension_manager)

    #-------------------------------------------------------------------------
    # Things related to payloads
    #-------------------------------------------------------------------------

    def init_payload(self):
        self.payload_manager = PayloadManager(parent=self)
        self.configurables.append(self.payload_manager)

    #-------------------------------------------------------------------------
    # Things related to the prefilter
    #-------------------------------------------------------------------------

    def init_prefilter(self):
        self.prefilter_manager = PrefilterManager(shell=self, parent=self)
        self.configurables.append(self.prefilter_manager)
        # Ultimately this will be refactored in the new interpreter code, but
        # for now, we should expose the main prefilter method (there's legacy
        # code out there that may rely on this).
        self.prefilter = self.prefilter_manager.prefilter_lines

    def auto_rewrite_input(self, cmd):
        """Print to the screen the rewritten form of the user's command.

        This shows visual feedback by rewriting input lines that cause
        automatic calling to kick in, like::

          /f x

        into::

          ------> f(x)

        after the user's input prompt.  This helps the user understand that the
        input line was transformed automatically by IPython.
        """
        if not self.show_rewritten_input:
            return

        # This is overridden in TerminalInteractiveShell to use fancy prompts
        print("------> " + cmd)

    #-------------------------------------------------------------------------
    # Things related to extracting values/expressions from kernel and user_ns
    #-------------------------------------------------------------------------

    def _user_obj_error(self):
        """return simple exception dict

        for use in user_expressions
        """

        etype, evalue, tb = self._get_exc_info()
        stb = self.InteractiveTB.get_exception_only(etype, evalue)

        exc_info = {
            "status": "error",
            "traceback": stb,
            "ename": etype.__name__,
            "evalue": py3compat.safe_unicode(evalue),
        }

        return exc_info

    def _format_user_obj(self, obj):
        """format a user object to display dict

        for use in user_expressions
        """

        data, md = self.display_formatter.format(obj)
        value = {
            'status' : 'ok',
            'data' : data,
            'metadata' : md,
        }
        return value

    def user_expressions(self, expressions):
        """Evaluate a dict of expressions in the user's namespace.

        Parameters
        ----------
        expressions : dict
            A dict with string keys and string values.  The expression values
            should be valid Python expressions, each of which will be evaluated
            in the user namespace.

        Returns
        -------
        A dict, keyed like the input expressions dict, with the rich mime-typed
        display_data of each value.
        """
        out = {}
        user_ns = self.user_ns
        global_ns = self.user_global_ns

        for key, expr in expressions.items():
            try:
                value = self._format_user_obj(eval(expr, global_ns, user_ns))
            except:
                value = self._user_obj_error()
            out[key] = value
        return out

    #-------------------------------------------------------------------------
    # Things related to the running of code
    #-------------------------------------------------------------------------

    def ex(self, cmd):
        """Execute a normal python statement in user namespace."""
        with self.builtin_trap:
            exec(cmd, self.user_global_ns, self.user_ns)

    def ev(self, expr):
        """Evaluate python expression expr in user namespace.

        Returns the result of evaluation
        """
        with self.builtin_trap:
            return eval(expr, self.user_global_ns, self.user_ns)

    def safe_execfile(self, fname, *where, exit_ignore=False, raise_exceptions=False, shell_futures=False):
        """A safe version of the builtin execfile().

        This version will never throw an exception, but instead print
        helpful error messages to the screen.  This only works on pure
        Python files with the .py extension.

        Parameters
        ----------
        fname : string
            The name of the file to be executed.
        *where : tuple
            One or two namespaces, passed to execfile() as (globals,locals).
            If only one is given, it is passed as both.
        exit_ignore : bool (False)
            If True, then silence SystemExit for non-zero status (it is always
            silenced for zero status, as it is so common).
        raise_exceptions : bool (False)
            If True raise exceptions everywhere. Meant for testing.
        shell_futures : bool (False)
            If True, the code will share future statements with the interactive
            shell. It will both be affected by previous __future__ imports, and
            any __future__ imports in the code will affect the shell. If False,
            __future__ imports are not shared in either direction.

        """
        fname = Path(fname).expanduser().resolve()

        # Make sure we can open the file
        try:
            with fname.open("rb"):
                pass
        except:
            warn('Could not open file <%s> for safe execution.' % fname)
            return

        # Find things also in current directory.  This is needed to mimic the
        # behavior of running a script from the system command line, where
        # Python inserts the script's directory into sys.path
        dname = str(fname.parent)

        with prepended_to_syspath(dname), self.builtin_trap:
            try:
                glob, loc = (where + (None, ))[:2]
                py3compat.execfile(
                    fname, glob, loc,
                    self.compile if shell_futures else None)
            except SystemExit as status:
                # If the call was made with 0 or None exit status (sys.exit(0)
                # or sys.exit() ), don't bother showing a traceback, as both of
                # these are considered normal by the OS:
                # > python -c'import sys;sys.exit(0)'; echo $?
                # 0
                # > python -c'import sys;sys.exit()'; echo $?
                # 0
                # For other exit status, we show the exception unless
                # explicitly silenced, but only in short form.
                if status.code:
                    if raise_exceptions:
                        raise
                    if not exit_ignore:
                        self.showtraceback(exception_only=True)
            except:
                if raise_exceptions:
                    raise
                # tb offset is 2 because we wrap execfile
                self.showtraceback(tb_offset=2)

    def safe_execfile_ipy(self, fname, shell_futures=False, raise_exceptions=False):
        """Like safe_execfile, but for .ipy or .ipynb files with IPython syntax.

        Parameters
        ----------
        fname : str
            The name of the file to execute.  The filename must have a
            .ipy or .ipynb extension.
        shell_futures : bool (False)
            If True, the code will share future statements with the interactive
            shell. It will both be affected by previous __future__ imports, and
            any __future__ imports in the code will affect the shell. If False,
            __future__ imports are not shared in either direction.
        raise_exceptions : bool (False)
            If True raise exceptions everywhere.  Meant for testing.
        """
        fname = Path(fname).expanduser().resolve()

        # Make sure we can open the file
        try:
            with fname.open("rb"):
                pass
        except:
            warn('Could not open file <%s> for safe execution.' % fname)
            return

        # Find things also in current directory.  This is needed to mimic the
        # behavior of running a script from the system command line, where
        # Python inserts the script's directory into sys.path
        dname = str(fname.parent)

        def get_cells():
            """generator for sequence of code blocks to run"""
            if fname.suffix == ".ipynb":
                from nbformat import read
                nb = read(fname, as_version=4)
                if not nb.cells:
                    return
                for cell in nb.cells:
                    if cell.cell_type == 'code':
                        yield cell.source
            else:
                yield fname.read_text(encoding="utf-8")

        with prepended_to_syspath(dname):
            try:
                for cell in get_cells():
                    result = self.run_cell(cell, silent=True, shell_futures=shell_futures)
                    if raise_exceptions:
                        result.raise_error()
                    elif not result.success:
                        break
            except:
                if raise_exceptions:
                    raise
                self.showtraceback()
                warn('Unknown failure executing file: <%s>' % fname)

    def safe_run_module(self, mod_name, where):
        """A safe version of runpy.run_module().

        This version will never throw an exception, but instead print
        helpful error messages to the screen.

        `SystemExit` exceptions with status code 0 or None are ignored.

        Parameters
        ----------
        mod_name : string
            The name of the module to be executed.
        where : dict
            The globals namespace.
        """
        try:
            try:
                where.update(
                    runpy.run_module(str(mod_name), run_name="__main__",
                                     alter_sys=True)
                            )
            except SystemExit as status:
                if status.code:
                    raise
        except:
            self.showtraceback()
            warn('Unknown failure executing module: <%s>' % mod_name)

    @contextmanager
    def _tee(self, channel: Literal["stdout", "stderr"]):
        """Capture output of a given standard stream and store it in history.

        Uses patching of write method for maximal compatibility,
        because ipykernel checks for instances of the stream class,
        and stream classes in ipykernel implement more complex logic.
        """
        stream = getattr(sys, channel)
        original_write = stream.write

        def write(data, *args, **kwargs):
            """Write data to both the original destination and the capture dictionary."""
            result = original_write(data, *args, **kwargs)
            if any(
                [
                    self.display_pub.is_publishing,
                    self.displayhook.is_active,
                    self.showing_traceback,
                ]
            ):
                return result
            if not data:
                return result
            execution_count = self.execution_count
            output_stream = None
            outputs_by_counter = self.history_manager.outputs
            output_type = "out_stream" if channel == "stdout" else "err_stream"
            if execution_count in outputs_by_counter:
                outputs = outputs_by_counter[execution_count]
                if outputs[-1].output_type == output_type:
                    output_stream = outputs[-1]
            if output_stream is None:
                output_stream = HistoryOutput(
                    output_type=output_type, bundle={"stream": ""}
                )
                outputs_by_counter[execution_count].append(output_stream)

            output_stream.bundle["stream"] += data  # Append to existing stream
            return result

        stream.write = write
        yield
        stream.write = original_write

    def run_cell(
        self,
        raw_cell,
        store_history=False,
        silent=False,
        shell_futures=True,
        cell_id=None,
    ):
        """Run a complete IPython cell.

        Parameters
        ----------
        raw_cell : str
            The code (including IPython code such as %magic functions) to run.
        store_history : bool
            If True, the raw and translated cell will be stored in IPython's
            history. For user code calling back into IPython's machinery, this
            should be set to False.
        silent : bool
            If True, avoid side-effects, such as implicit displayhooks and
            and logging.  silent=True forces store_history=False.
        shell_futures : bool
            If True, the code will share future statements with the interactive
            shell. It will both be affected by previous __future__ imports, and
            any __future__ imports in the code will affect the shell. If False,
            __future__ imports are not shared in either direction.
        cell_id : str, optional
            A unique identifier for the cell. This is used in the messaging system
            to match output with execution requests and for tracking cell execution
            history across kernel restarts. In notebook contexts, this is typically
            a UUID generated by the frontend. If None, the kernel may generate an
            internal identifier or proceed without cell tracking capabilities.
        Returns
        -------
        result : :class:`ExecutionResult`
        """
        result = None
        with self._tee(channel="stdout"), self._tee(channel="stderr"):
            try:
                result = self._run_cell(
                    raw_cell, store_history, silent, shell_futures, cell_id
                )
            finally:
                self.events.trigger("post_execute")
                if not silent:
                    self.events.trigger("post_run_cell", result)
        return result

    def _run_cell(
        self,
        raw_cell: str,
        store_history: bool,
        silent: bool,
        shell_futures: bool,
        cell_id: str,
    ) -> ExecutionResult:
        """Internal method to run a complete IPython cell."""

        # we need to avoid calling self.transform_cell multiple time on the same thing
        # so we need to store some results:
        preprocessing_exc_tuple = None
        try:
            transformed_cell = self.transform_cell(raw_cell)
        except Exception:
            transformed_cell = raw_cell
            preprocessing_exc_tuple = sys.exc_info()

        assert transformed_cell is not None
        coro = self.run_cell_async(
            raw_cell,
            store_history=store_history,
            silent=silent,
            shell_futures=shell_futures,
            transformed_cell=transformed_cell,
            preprocessing_exc_tuple=preprocessing_exc_tuple,
            cell_id=cell_id,
        )

        # run_cell_async is async, but may not actually need an eventloop.
        # when this is the case, we want to run it using the pseudo_sync_runner
        # so that code can invoke eventloops (for example via the %run , and
        # `%paste` magic.
        if self.trio_runner:
            runner = self.trio_runner
        elif self.should_run_async(
            raw_cell,
            transformed_cell=transformed_cell,
            preprocessing_exc_tuple=preprocessing_exc_tuple,
        ):
            runner = self.loop_runner
        else:
            runner = _pseudo_sync_runner

        try:
            result = runner(coro)
        except BaseException as e:
            try:
                info = ExecutionInfo(
                    raw_cell, store_history, silent, shell_futures, cell_id
                )
                result = ExecutionResult(info)
                result.error_in_exec = e
                self.showtraceback(running_compiled_code=True)
            except:
                pass

        return result

    def should_run_async(
        self, raw_cell: str, *, transformed_cell=None, preprocessing_exc_tuple=None
    ) -> bool:
        """Return whether a cell should be run asynchronously via a coroutine runner

        Parameters
        ----------
        raw_cell : str
            The code to be executed

        Returns
        -------
        result: bool
            Whether the code needs to be run with a coroutine runner or not
        .. versionadded:: 7.0
        """
        if not self.autoawait:
            return False
        if preprocessing_exc_tuple is not None:
            return False
        assert preprocessing_exc_tuple is None
        if transformed_cell is None:
            warnings.warn(
                "`should_run_async` will not call `transform_cell`"
                " automatically in the future. Please pass the result to"
                " `transformed_cell` argument and any exception that happen"
                " during the"
                "transform in `preprocessing_exc_tuple` in"
                " IPython 7.17 and above.",
                DeprecationWarning,
                stacklevel=2,
            )
            try:
                cell = self.transform_cell(raw_cell)
            except Exception:
                # any exception during transform will be raised
                # prior to execution
                return False
        else:
            cell = transformed_cell
        return _should_be_async(cell)

    async def run_cell_async(
        self,
        raw_cell: str,
        store_history=False,
        silent=False,
        shell_futures=True,
        *,
        transformed_cell: Optional[str] = None,
        preprocessing_exc_tuple: Optional[AnyType] = None,
        cell_id=None,
    ) -> ExecutionResult:
        """Run a complete IPython cell asynchronously.

        Parameters
        ----------
        raw_cell : str
          The code (including IPython code such as %magic functions) to run.
        store_history : bool
          If True, the raw and translated cell will be stored in IPython's
          history. For user code calling back into IPython's machinery, this
          should be set to False.
        silent : bool
          If True, avoid side-effects, such as implicit displayhooks and
          and logging.  silent=True forces store_history=False.
        shell_futures : bool
          If True, the code will share future statements with the interactive
          shell. It will both be affected by previous __future__ imports, and
          any __future__ imports in the code will affect the shell. If False,
          __future__ imports are not shared in either direction.
        transformed_cell: str
          cell that was passed through transformers
        preprocessing_exc_tuple:
          trace if the transformation failed.

        Returns
        -------
        result : :class:`ExecutionResult`

        .. versionadded:: 7.0
        """
        info = ExecutionInfo(raw_cell, store_history, silent, shell_futures, cell_id)
        result = ExecutionResult(info)

        if (not raw_cell) or raw_cell.isspace():
            self.last_execution_succeeded = True
            self.last_execution_result = result
            return result

        if silent:
            store_history = False

        if store_history:
            result.execution_count = self.execution_count

        def error_before_exec(value):
            if store_history:
                if self.history_manager:
                    # Store formatted traceback and error details
                    self.history_manager.exceptions[self.execution_count] = (
                        self._format_exception_for_storage(value)
                    )
                self.execution_count += 1
            result.error_before_exec = value
            self.last_execution_succeeded = False
            self.last_execution_result = result
            return result

        self.events.trigger('pre_execute')
        if not silent:
            self.events.trigger('pre_run_cell', info)

        if transformed_cell is None:
            warnings.warn(
                "`run_cell_async` will not call `transform_cell`"
                " automatically in the future. Please pass the result to"
                " `transformed_cell` argument and any exception that happen"
                " during the"
                "transform in `preprocessing_exc_tuple` in"
                " IPython 7.17 and above.",
                DeprecationWarning,
                stacklevel=2,
            )
            # If any of our input transformation (input_transformer_manager or
            # prefilter_manager) raises an exception, we store it in this variable
            # so that we can display the error after logging the input and storing
            # it in the history.
            try:
                cell = self.transform_cell(raw_cell)
            except Exception:
                preprocessing_exc_tuple = sys.exc_info()
                cell = raw_cell  # cell has to exist so it can be stored/logged
            else:
                preprocessing_exc_tuple = None
        else:
            if preprocessing_exc_tuple is None:
                cell = transformed_cell
            else:
                cell = raw_cell

        # Do NOT store paste/cpaste magic history
        if "get_ipython().run_line_magic(" in cell and "paste" in cell:
            store_history = False

        # Store raw and processed history
        if store_history:
            assert self.history_manager is not None
            self.history_manager.store_inputs(self.execution_count, cell, raw_cell)
        if not silent:
            self.logger.log(cell, raw_cell)

        # Display the exception if input processing failed.
        if preprocessing_exc_tuple is not None:
            self.showtraceback(preprocessing_exc_tuple)
            if store_history:
                self.execution_count += 1
            return error_before_exec(preprocessing_exc_tuple[1])

        # Our own compiler remembers the __future__ environment. If we want to
        # run code with a separate __future__ environment, use the default
        # compiler
        compiler = self.compile if shell_futures else self.compiler_class()

        with self.builtin_trap:
            cell_name = compiler.cache(cell, self.execution_count, raw_code=raw_cell)

            with self.display_trap:
                # Compile to bytecode
                try:
                    code_ast = compiler.ast_parse(cell, filename=cell_name)
                except self.custom_exceptions as e:
                    etype, value, tb = sys.exc_info()
                    self.CustomTB(etype, value, tb)
                    return error_before_exec(e)
                except IndentationError as e:
                    self.showindentationerror()
                    return error_before_exec(e)
                except (OverflowError, SyntaxError, ValueError, TypeError,
                        MemoryError) as e:
                    self.showsyntaxerror()
                    return error_before_exec(e)

                # Apply AST transformations
                try:
                    code_ast = self.transform_ast(code_ast)
                except InputRejected as e:
                    self.showtraceback()
                    return error_before_exec(e)

                # Give the displayhook a reference to our ExecutionResult so it
                # can fill in the output value.
                self.displayhook.exec_result = result

                # Execute the user code
                interactivity = "none" if silent else self.ast_node_interactivity


                has_raised = await self.run_ast_nodes(code_ast.body, cell_name,
                       interactivity=interactivity, compiler=compiler, result=result)

                self.last_execution_succeeded = not has_raised
                self.last_execution_result = result

                # Reset this so later displayed values do not modify the
                # ExecutionResult
                self.displayhook.exec_result = None

        if store_history:
            assert self.history_manager is not None
            # Write output to the database. Does nothing unless
            # history output logging is enabled.
            self.history_manager.store_output(self.execution_count)
            exec_count = self.execution_count
            if result.error_in_exec:
                # Store formatted traceback and error details
                self.history_manager.exceptions[exec_count] = (
                    self._format_exception_for_storage(result.error_in_exec)
                )

            # Each cell is a *single* input, regardless of how many lines it has
            self.execution_count += 1

        return result

    def _format_exception_for_storage(
        self, exception, filename=None, running_compiled_code=False
    ):
        """
        Format an exception's traceback and details for storage, with special handling
        for different types of errors.
        """
        etype = type(exception)
        evalue = exception
        tb = exception.__traceback__

        # Handle SyntaxError and IndentationError with specific formatting
        if issubclass(etype, (SyntaxError, IndentationError)):
            if filename and isinstance(evalue, SyntaxError):
                try:
                    evalue.filename = filename
                except:
                    pass  # Keep the original filename if modification fails

            # Extract traceback if the error happened during compiled code execution
            elist = traceback.extract_tb(tb) if running_compiled_code else []
            stb = self.SyntaxTB.structured_traceback(etype, evalue, elist)

        # Handle UsageError with a simple message
        elif etype is UsageError:
            stb = [f"UsageError: {evalue}"]

        else:
            # Check if the exception (or its context) is an ExceptionGroup.
            def contains_exceptiongroup(val):
                if val is None:
                    return False
                return isinstance(val, BaseExceptionGroup) or contains_exceptiongroup(
                    val.__context__
                )

            if contains_exceptiongroup(evalue):
                # Fallback: use the standard library's formatting for exception groups.
                stb = traceback.format_exception(etype, evalue, tb)
            else:
                try:
                    # If the exception has a custom traceback renderer, use it.
                    if hasattr(evalue, "_render_traceback_"):
                        stb = evalue._render_traceback_()
                    else:
                        # Otherwise, use InteractiveTB to format the traceback.
                        stb = self.InteractiveTB.structured_traceback(
                            etype, evalue, tb, tb_offset=1
                        )
                except Exception:
                    # In case formatting fails, fallback to Python's built-in formatting.
                    stb = traceback.format_exception(etype, evalue, tb)

        return {"ename": etype.__name__, "evalue": str(evalue), "traceback": stb}

    def transform_cell(self, raw_cell):
        """Transform an input cell before parsing it.

        Static transformations, implemented in IPython.core.inputtransformer2,
        deal with things like ``%magic`` and ``!system`` commands.
        These run on all input.
        Dynamic transformations, for things like unescaped magics and the exit
        autocall, depend on the state of the interpreter.
        These only apply to single line inputs.

        These string-based transformations are followed by AST transformations;
        see :meth:`transform_ast`.
        """
        # Static input transformations
        cell = self.input_transformer_manager.transform_cell(raw_cell)

        if len(cell.splitlines()) == 1:
            # Dynamic transformations - only applied for single line commands
            with self.builtin_trap:
                # use prefilter_lines to handle trailing newlines
                # restore trailing newline for ast.parse
                cell = self.prefilter_manager.prefilter_lines(cell) + '\n'

        lines = cell.splitlines(keepends=True)
        for transform in self.input_transformers_post:
            lines = transform(lines)
        cell = ''.join(lines)

        return cell

    def transform_ast(self, node):
        """Apply the AST transformations from self.ast_transformers

        Parameters
        ----------
        node : ast.Node
            The root node to be transformed. Typically called with the ast.Module
            produced by parsing user input.

        Returns
        -------
        An ast.Node corresponding to the node it was called with. Note that it
        may also modify the passed object, so don't rely on references to the
        original AST.
        """
        for transformer in self.ast_transformers:
            try:
                node = transformer.visit(node)
            except InputRejected:
                # User-supplied AST transformers can reject an input by raising
                # an InputRejected.  Short-circuit in this case so that we
                # don't unregister the transform.
                raise
            except Exception as e:
                warn(
                    "AST transformer %r threw an error. It will be unregistered. %s"
                    % (transformer, e)
                )
                self.ast_transformers.remove(transformer)

        if self.ast_transformers:
            ast.fix_missing_locations(node)
        return node

    async def run_ast_nodes(
        self,
        nodelist: ListType[stmt],
        cell_name: str,
        interactivity="last_expr",
        compiler=compile,
        result=None,
    ):
        """Run a sequence of AST nodes. The execution mode depends on the
        interactivity parameter.

        Parameters
        ----------
        nodelist : list
          A sequence of AST nodes to run.
        cell_name : str
          Will be passed to the compiler as the filename of the cell. Typically
          the value returned by ip.compile.cache(cell).
        interactivity : str
          'all', 'last', 'last_expr' , 'last_expr_or_assign' or 'none',
          specifying which nodes should be run interactively (displaying output
          from expressions). 'last_expr' will run the last node interactively
          only if it is an expression (i.e. expressions in loops or other blocks
          are not displayed) 'last_expr_or_assign' will run the last expression
          or the last assignment. Other values for this parameter will raise a
          ValueError.

        compiler : callable
          A function with the same interface as the built-in compile(), to turn
          the AST nodes into code objects. Default is the built-in compile().
        result : ExecutionResult, optional
          An object to store exceptions that occur during execution.

        Returns
        -------
        True if an exception occurred while running code, False if it finished
        running.
        """
        if not nodelist:
            return


        if interactivity == 'last_expr_or_assign':
            if isinstance(nodelist[-1], _assign_nodes):
                asg = nodelist[-1]
                if isinstance(asg, ast.Assign) and len(asg.targets) == 1:
                    target = asg.targets[0]
                elif isinstance(asg, _single_targets_nodes):
                    target = asg.target
                else:
                    target = None
                if isinstance(target, ast.Name):
                    nnode = ast.Expr(ast.Name(target.id, ast.Load()))
                    ast.fix_missing_locations(nnode)
                    nodelist.append(nnode)
            interactivity = 'last_expr'

        _async = False
        if interactivity == 'last_expr':
            if isinstance(nodelist[-1], ast.Expr):
                interactivity = "last"
            else:
                interactivity = "none"

        if interactivity == 'none':
            to_run_exec, to_run_interactive = nodelist, []
        elif interactivity == 'last':
            to_run_exec, to_run_interactive = nodelist[:-1], nodelist[-1:]
        elif interactivity == 'all':
            to_run_exec, to_run_interactive = [], nodelist
        else:
            raise ValueError("Interactivity was %r" % interactivity)

        try:

            def compare(code):
                is_async = inspect.CO_COROUTINE & code.co_flags == inspect.CO_COROUTINE
                return is_async

            # refactor that to just change the mod constructor.
            to_run = []
            for node in to_run_exec:
                to_run.append((node, "exec"))

            for node in to_run_interactive:
                to_run.append((node, "single"))

            for node, mode in to_run:
                if mode == "exec":
                    mod = Module([node], [])
                elif mode == "single":
                    mod = ast.Interactive([node])
                with compiler.extra_flags(
                    getattr(ast, "PyCF_ALLOW_TOP_LEVEL_AWAIT", 0x0)
                    if self.autoawait
                    else 0x0
                ):
                    code = compiler(mod, cell_name, mode)
                    asy = compare(code)
                if await self.run_code(code, result, async_=asy):
                    return True

            # Flush softspace
            if softspace(sys.stdout, 0):
                print()

        except:
            # It's possible to have exceptions raised here, typically by
            # compilation of odd code (such as a naked 'return' outside a
            # function) that did parse but isn't valid. Typically the exception
            # is a SyntaxError, but it's safest just to catch anything and show
            # the user a traceback.

            # We do only one try/except outside the loop to minimize the impact
            # on runtime, and also because if any node in the node list is
            # broken, we should stop execution completely.
            if result:
                result.error_before_exec = sys.exc_info()[1]
            self.showtraceback()
            return True

        return False

    async def run_code(self, code_obj, result=None, *, async_=False):
        """Execute a code object.

        When an exception occurs, self.showtraceback() is called to display a
        traceback.

        Parameters
        ----------
        code_obj : code object
          A compiled code object, to be executed
        result : ExecutionResult, optional
          An object to store exceptions that occur during execution.
        async_ :  Bool (Experimental)
          Attempt to run top-level asynchronous code in a default loop.

        Returns
        -------
        False : successful execution.
        True : an error occurred.
        """
        # special value to say that anything above is IPython and should be
        # hidden.
        __tracebackhide__ = "__ipython_bottom__"
        # Set our own excepthook in case the user code tries to call it
        # directly, so that the IPython crash handler doesn't get triggered
        old_excepthook, sys.excepthook = sys.excepthook, self.excepthook

        # we save the original sys.excepthook in the instance, in case config
        # code (such as magics) needs access to it.
        self.sys_excepthook = old_excepthook
        outflag = True  # happens in more places, so it's easier as default
        try:
            try:
                if async_:
                    await eval(code_obj, self.user_global_ns, self.user_ns)
                else:
                    exec(code_obj, self.user_global_ns, self.user_ns)
            finally:
                # Reset our crash handler in place
                sys.excepthook = old_excepthook
        except SystemExit as e:
            if result is not None:
                result.error_in_exec = e
            self.showtraceback(exception_only=True)
            warn("To exit: use 'exit', 'quit', or Ctrl-D.", stacklevel=1)
        except bdb.BdbQuit:
            etype, value, tb = sys.exc_info()
            if result is not None:
                result.error_in_exec = value
            # the BdbQuit stops here
        except self.custom_exceptions:
            etype, value, tb = sys.exc_info()
            if result is not None:
                result.error_in_exec = value
            self.CustomTB(etype, value, tb)
        except:
            if result is not None:
                result.error_in_exec = sys.exc_info()[1]
            self.showtraceback(running_compiled_code=True)
        else:
            outflag = False
        return outflag

    # For backwards compatibility
    runcode = run_code

    def check_complete(self, code: str) -> Tuple[str, str]:
        """Return whether a block of code is ready to execute, or should be continued

        Parameters
        ----------
        code : string
            Python input code, which can be multiline.

        Returns
        -------
        status : str
            One of 'complete', 'incomplete', or 'invalid' if source is not a
            prefix of valid code.
        indent : str
            When status is 'incomplete', this is some whitespace to insert on
            the next line of the prompt.
        """
        status, nspaces = self.input_transformer_manager.check_complete(code)
        return status, ' ' * (nspaces or 0)

    #-------------------------------------------------------------------------
    # Things related to GUI support and pylab
    #-------------------------------------------------------------------------

    active_eventloop: Optional[str] = None

    def enable_gui(self, gui=None):
        raise NotImplementedError('Implement enable_gui in a subclass')

    def enable_matplotlib(self, gui=None):
        """Enable interactive matplotlib and inline figure support.

        This takes the following steps:

        1. select the appropriate eventloop and matplotlib backend
        2. set up matplotlib for interactive use with that backend
        3. configure formatters for inline figure display
        4. enable the selected gui eventloop

        Parameters
        ----------
        gui : optional, string
            If given, dictates the choice of matplotlib GUI backend to use
            (should be one of IPython's supported backends, 'qt', 'osx', 'tk',
            'gtk', 'wx' or 'inline'), otherwise we use the default chosen by
            matplotlib (as dictated by the matplotlib build-time options plus the
            user's matplotlibrc configuration file).  Note that not all backends
            make sense in all contexts, for example a terminal ipython can't
            display figures inline.
        """
        from .pylabtools import _matplotlib_manages_backends

        if not _matplotlib_manages_backends() and gui in (None, "auto"):
            # Early import of backend_inline required for its side effect of
            # calling _enable_matplotlib_integration()
            import matplotlib_inline.backend_inline

        from IPython.core import pylabtools as pt
        gui, backend = pt.find_gui_and_backend(gui, self.pylab_gui_select)

        if gui != None:
            # If we have our first gui selection, store it
            if self.pylab_gui_select is None:
                self.pylab_gui_select = gui
            # Otherwise if they are different
            elif gui != self.pylab_gui_select:
                print('Warning: Cannot change to a different GUI toolkit: %s.'
                        ' Using %s instead.' % (gui, self.pylab_gui_select))
                gui, backend = pt.find_gui_and_backend(self.pylab_gui_select)

        pt.activate_matplotlib(backend)

        from matplotlib_inline.backend_inline import configure_inline_support

        configure_inline_support(self, backend)

        # Now we must activate the gui pylab wants to use, and fix %run to take
        # plot updates into account
        self.enable_gui(gui)
        self.magics_manager.registry['ExecutionMagics'].default_runner = \
            pt.mpl_runner(self.safe_execfile)

        return gui, backend

    def enable_pylab(self, gui=None, import_all=True):
        """Activate pylab support at runtime.

        This turns on support for matplotlib, preloads into the interactive
        namespace all of numpy and pylab, and configures IPython to correctly
        interact with the GUI event loop.  The GUI backend to be used can be
        optionally selected with the optional ``gui`` argument.

        This method only adds preloading the namespace to InteractiveShell.enable_matplotlib.

        Parameters
        ----------
        gui : optional, string
            If given, dictates the choice of matplotlib GUI backend to use
            (should be one of IPython's supported backends, 'qt', 'osx', 'tk',
            'gtk', 'wx' or 'inline'), otherwise we use the default chosen by
            matplotlib (as dictated by the matplotlib build-time options plus the
            user's matplotlibrc configuration file).  Note that not all backends
            make sense in all contexts, for example a terminal ipython can't
            display figures inline.
        import_all : optional, bool, default: True
            Whether to do `from numpy import *` and `from pylab import *`
            in addition to module imports.
        """
        from IPython.core.pylabtools import import_pylab

        gui, backend = self.enable_matplotlib(gui)

        # We want to prevent the loading of pylab to pollute the user's
        # namespace as shown by the %who* magics, so we execute the activation
        # code in an empty namespace, and we update *both* user_ns and
        # user_ns_hidden with this information.
        ns = {}
        import_pylab(ns, import_all)
        # warn about clobbered names
        ignored = {"__builtins__"}
        both = set(ns).intersection(self.user_ns).difference(ignored)
        clobbered = [ name for name in both if self.user_ns[name] is not ns[name] ]
        self.user_ns.update(ns)
        self.user_ns_hidden.update(ns)
        return gui, backend, clobbered

    #-------------------------------------------------------------------------
    # Utilities
    #-------------------------------------------------------------------------

    def var_expand(self, cmd, depth=0, formatter=DollarFormatter()):
        """Expand python variables in a string.

        The depth argument indicates how many frames above the caller should
        be walked to look for the local namespace where to expand variables.

        The global namespace for expansion is always the user's interactive
        namespace.
        """
        ns = self.user_ns.copy()
        try:
            frame = sys._getframe(depth+1)
        except ValueError:
            # This is thrown if there aren't that many frames on the stack,
            # e.g. if a script called run_line_magic() directly.
            pass
        else:
            ns.update(frame.f_locals)

        try:
            # We have to use .vformat() here, because 'self' is a valid and common
            # name, and expanding **ns for .format() would make it collide with
            # the 'self' argument of the method.
            cmd = formatter.vformat(cmd, args=[], kwargs=ns)
        except Exception:
            # if formatter couldn't format, just let it go untransformed
            pass
        return cmd

    def mktempfile(self, data=None, prefix='ipython_edit_'):
        """Make a new tempfile and return its filename.

        This makes a call to tempfile.mkstemp (created in a tempfile.mkdtemp),
        but it registers the created filename internally so ipython cleans it up
        at exit time.

        Optional inputs:

          - data(None): if data is given, it gets written out to the temp file
            immediately, and the file is closed again."""

        dir_path = Path(tempfile.mkdtemp(prefix=prefix))
        self.tempdirs.append(dir_path)

        handle, filename = tempfile.mkstemp(".py", prefix, dir=str(dir_path))
        os.close(handle)  # On Windows, there can only be one open handle on a file

        file_path = Path(filename)
        self.tempfiles.append(file_path)

        if data:
            file_path.write_text(data, encoding="utf-8")
        return filename

    def ask_yes_no(self, prompt, default=None, interrupt=None):
        if self.quiet:
            return True
        return ask_yes_no(prompt,default,interrupt)

    def show_usage(self):
        """Show a usage message"""
        page.page(IPython.core.usage.interactive_usage)

    def extract_input_lines(self, range_str, raw=False):
        """Return as a string a set of input history slices.

        Parameters
        ----------
        range_str : str
            The set of slices is given as a string, like "~5/6-~4/2 4:8 9",
            since this function is for use by magic functions which get their
            arguments as strings. The number before the / is the session
            number: ~n goes n back from the current session.

            If empty string is given, returns history of current session
            without the last input.

        raw : bool, optional
            By default, the processed input is used.  If this is true, the raw
            input history is used instead.

        Notes
        -----
        Slices can be described with two notations:

        * ``N:M`` -> standard python form, means including items N...(M-1).
        * ``N-M`` -> include items N..M (closed endpoint).
        """
        lines = self.history_manager.get_range_by_str(range_str, raw=raw)
        text = "\n".join(x for _, _, x in lines)

        # Skip the last line, as it's probably the magic that called this
        if not range_str:
            if "\n" not in text:
                text = ""
            else:
                text = text[: text.rfind("\n")]

        return text

    def find_user_code(self, target, raw=True, py_only=False, skip_encoding_cookie=True, search_ns=False):
        """Get a code string from history, file, url, or a string or macro.

        This is mainly used by magic functions.

        Parameters
        ----------
        target : str
            A string specifying code to retrieve. This will be tried respectively
            as: ranges of input history (see %history for syntax), url,
            corresponding .py file, filename, or an expression evaluating to a
            string or Macro in the user namespace.

            If empty string is given, returns complete history of current
            session, without the last line.

        raw : bool
            If true (default), retrieve raw history. Has no effect on the other
            retrieval mechanisms.

        py_only : bool (default False)
            Only try to fetch python code, do not try alternative methods to decode file
            if unicode fails.

        Returns
        -------
        A string of code.
        ValueError is raised if nothing is found, and TypeError if it evaluates
        to an object of another type. In each case, .args[0] is a printable
        message.
        """
        code = self.extract_input_lines(target, raw=raw)  # Grab history
        if code:
            return code
        try:
            if target.startswith(('http://', 'https://')):
                return openpy.read_py_url(target, skip_encoding_cookie=skip_encoding_cookie)
        except UnicodeDecodeError as e:
            if not py_only :
                # Deferred import
                from urllib.request import urlopen
                response = urlopen(target)
                return response.read().decode('latin1')
            raise ValueError(("'%s' seem to be unreadable.") % target) from e

        potential_target = [target]
        try :
            potential_target.insert(0,get_py_filename(target))
        except IOError:
            pass

        for tgt in potential_target :
            if os.path.isfile(tgt):                        # Read file
                try :
                    return openpy.read_py_file(tgt, skip_encoding_cookie=skip_encoding_cookie)
                except UnicodeDecodeError as e:
                    if not py_only :
                        with io_open(tgt,'r', encoding='latin1') as f :
                            return f.read()
                    raise ValueError(("'%s' seem to be unreadable.") % target) from e
            elif os.path.isdir(os.path.expanduser(tgt)):
                raise ValueError("'%s' is a directory, not a regular file." % target)

        if search_ns:
            # Inspect namespace to load object source
            object_info = self.object_inspect(target, detail_level=1)
            if object_info['found'] and object_info['source']:
                return object_info['source']

        try:                                              # User namespace
            codeobj = eval(target, self.user_ns)
        except Exception as e:
            raise ValueError(("'%s' was not found in history, as a file, url, "
                                "nor in the user namespace.") % target) from e

        if isinstance(codeobj, str):
            return codeobj
        elif isinstance(codeobj, Macro):
            return codeobj.value

        raise TypeError("%s is neither a string nor a macro." % target,
                        codeobj)

    def _atexit_once(self):
        """
        At exist operation that need to be called at most once.
        Second call to this function per instance will do nothing.
        """

        if not getattr(self, "_atexit_once_called", False):
            self._atexit_once_called = True
            # Clear all user namespaces to release all references cleanly.
            self.reset(new_session=False)
            # Close the history session (this stores the end time and line count)
            # this must be *before* the tempfile cleanup, in case of temporary
            # history db
            if self.history_manager is not None:
                self.history_manager.end_session()
                self.history_manager = None

    #-------------------------------------------------------------------------
    # Things related to IPython exiting
    #-------------------------------------------------------------------------
    def atexit_operations(self):
        """This will be executed at the time of exit.

        Cleanup operations and saving of persistent data that is done
        unconditionally by IPython should be performed here.

        For things that may depend on startup flags or platform specifics (such
        as having readline or not), register a separate atexit function in the
        code that has the appropriate information, rather than trying to
        clutter
        """
        self._atexit_once()

        # Cleanup all tempfiles and folders left around
        for tfile in self.tempfiles:
            try:
                tfile.unlink()
                self.tempfiles.remove(tfile)
            except FileNotFoundError:
                pass
        del self.tempfiles
        for tdir in self.tempdirs:
            try:
                shutil.rmtree(tdir)
                self.tempdirs.remove(tdir)
            except FileNotFoundError:
                pass
        del self.tempdirs

        # Restore user's cursor
        if hasattr(self, "editing_mode") and self.editing_mode == "vi":
            sys.stdout.write("\x1b[0 q")
            sys.stdout.flush()

    def cleanup(self):
        self.restore_sys_module_state()


    # Overridden in terminal subclass to change prompts
    def switch_doctest_mode(self, mode):
        pass


class InteractiveShellABC(metaclass=abc.ABCMeta):
    """An abstract base class for InteractiveShell."""

InteractiveShellABC.register(InteractiveShell)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\network.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Network
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import debugger
from . import emulation
from . import io
from . import page
from . import runtime
from . import security


class ResourceType(enum.Enum):
    '''
    Resource type as it was perceived by the rendering engine.
    '''
    DOCUMENT = "Document"
    STYLESHEET = "Stylesheet"
    IMAGE = "Image"
    MEDIA = "Media"
    FONT = "Font"
    SCRIPT = "Script"
    TEXT_TRACK = "TextTrack"
    XHR = "XHR"
    FETCH = "Fetch"
    PREFETCH = "Prefetch"
    EVENT_SOURCE = "EventSource"
    WEB_SOCKET = "WebSocket"
    MANIFEST = "Manifest"
    SIGNED_EXCHANGE = "SignedExchange"
    PING = "Ping"
    CSP_VIOLATION_REPORT = "CSPViolationReport"
    PREFLIGHT = "Preflight"
    OTHER = "Other"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class LoaderId(str):
    '''
    Unique loader identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> LoaderId:
        return cls(json)

    def __repr__(self):
        return 'LoaderId({})'.format(super().__repr__())


class RequestId(str):
    '''
    Unique network request identifier.
    Note that this does not identify individual HTTP requests that are part of
    a network request.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RequestId:
        return cls(json)

    def __repr__(self):
        return 'RequestId({})'.format(super().__repr__())


class InterceptionId(str):
    '''
    Unique intercepted request identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> InterceptionId:
        return cls(json)

    def __repr__(self):
        return 'InterceptionId({})'.format(super().__repr__())


class ErrorReason(enum.Enum):
    '''
    Network level fetch failure reason.
    '''
    FAILED = "Failed"
    ABORTED = "Aborted"
    TIMED_OUT = "TimedOut"
    ACCESS_DENIED = "AccessDenied"
    CONNECTION_CLOSED = "ConnectionClosed"
    CONNECTION_RESET = "ConnectionReset"
    CONNECTION_REFUSED = "ConnectionRefused"
    CONNECTION_ABORTED = "ConnectionAborted"
    CONNECTION_FAILED = "ConnectionFailed"
    NAME_NOT_RESOLVED = "NameNotResolved"
    INTERNET_DISCONNECTED = "InternetDisconnected"
    ADDRESS_UNREACHABLE = "AddressUnreachable"
    BLOCKED_BY_CLIENT = "BlockedByClient"
    BLOCKED_BY_RESPONSE = "BlockedByResponse"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class TimeSinceEpoch(float):
    '''
    UTC time in seconds, counted from January 1, 1970.
    '''
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> TimeSinceEpoch:
        return cls(json)

    def __repr__(self):
        return 'TimeSinceEpoch({})'.format(super().__repr__())


class MonotonicTime(float):
    '''
    Monotonically increasing time in seconds since an arbitrary point in the past.
    '''
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> MonotonicTime:
        return cls(json)

    def __repr__(self):
        return 'MonotonicTime({})'.format(super().__repr__())


class Headers(dict):
    '''
    Request / response headers as keys / values of JSON object.
    '''
    def to_json(self) -> dict:
        return self

    @classmethod
    def from_json(cls, json: dict) -> Headers:
        return cls(json)

    def __repr__(self):
        return 'Headers({})'.format(super().__repr__())


class ConnectionType(enum.Enum):
    '''
    The underlying connection technology that the browser is supposedly using.
    '''
    NONE = "none"
    CELLULAR2G = "cellular2g"
    CELLULAR3G = "cellular3g"
    CELLULAR4G = "cellular4g"
    BLUETOOTH = "bluetooth"
    ETHERNET = "ethernet"
    WIFI = "wifi"
    WIMAX = "wimax"
    OTHER = "other"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieSameSite(enum.Enum):
    '''
    Represents the cookie's 'SameSite' status:
    https://tools.ietf.org/html/draft-west-first-party-cookies
    '''
    STRICT = "Strict"
    LAX = "Lax"
    NONE = "None"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookiePriority(enum.Enum):
    '''
    Represents the cookie's 'Priority' status:
    https://tools.ietf.org/html/draft-west-cookie-priority-00
    '''
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieSourceScheme(enum.Enum):
    '''
    Represents the source scheme of the origin that originally set the cookie.
    A value of "Unset" allows protocol clients to emulate legacy cookie scope for the scheme.
    This is a temporary ability and it will be removed in the future.
    '''
    UNSET = "Unset"
    NON_SECURE = "NonSecure"
    SECURE = "Secure"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ResourceTiming:
    '''
    Timing information for the request.
    '''
    #: Timing's requestTime is a baseline in seconds, while the other numbers are ticks in
    #: milliseconds relatively to this requestTime.
    request_time: float

    #: Started resolving proxy.
    proxy_start: float

    #: Finished resolving proxy.
    proxy_end: float

    #: Started DNS address resolve.
    dns_start: float

    #: Finished DNS address resolve.
    dns_end: float

    #: Started connecting to the remote host.
    connect_start: float

    #: Connected to the remote host.
    connect_end: float

    #: Started SSL handshake.
    ssl_start: float

    #: Finished SSL handshake.
    ssl_end: float

    #: Started running ServiceWorker.
    worker_start: float

    #: Finished Starting ServiceWorker.
    worker_ready: float

    #: Started fetch event.
    worker_fetch_start: float

    #: Settled fetch event respondWith promise.
    worker_respond_with_settled: float

    #: Started sending request.
    send_start: float

    #: Finished sending request.
    send_end: float

    #: Time the server started pushing request.
    push_start: float

    #: Time the server finished pushing request.
    push_end: float

    #: Started receiving response headers.
    receive_headers_start: float

    #: Finished receiving response headers.
    receive_headers_end: float

    #: Started ServiceWorker static routing source evaluation.
    worker_router_evaluation_start: typing.Optional[float] = None

    #: Started cache lookup when the source was evaluated to ``cache``.
    worker_cache_lookup_start: typing.Optional[float] = None

    def to_json(self):
        json = dict()
        json['requestTime'] = self.request_time
        json['proxyStart'] = self.proxy_start
        json['proxyEnd'] = self.proxy_end
        json['dnsStart'] = self.dns_start
        json['dnsEnd'] = self.dns_end
        json['connectStart'] = self.connect_start
        json['connectEnd'] = self.connect_end
        json['sslStart'] = self.ssl_start
        json['sslEnd'] = self.ssl_end
        json['workerStart'] = self.worker_start
        json['workerReady'] = self.worker_ready
        json['workerFetchStart'] = self.worker_fetch_start
        json['workerRespondWithSettled'] = self.worker_respond_with_settled
        json['sendStart'] = self.send_start
        json['sendEnd'] = self.send_end
        json['pushStart'] = self.push_start
        json['pushEnd'] = self.push_end
        json['receiveHeadersStart'] = self.receive_headers_start
        json['receiveHeadersEnd'] = self.receive_headers_end
        if self.worker_router_evaluation_start is not None:
            json['workerRouterEvaluationStart'] = self.worker_router_evaluation_start
        if self.worker_cache_lookup_start is not None:
            json['workerCacheLookupStart'] = self.worker_cache_lookup_start
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            request_time=float(json['requestTime']),
            proxy_start=float(json['proxyStart']),
            proxy_end=float(json['proxyEnd']),
            dns_start=float(json['dnsStart']),
            dns_end=float(json['dnsEnd']),
            connect_start=float(json['connectStart']),
            connect_end=float(json['connectEnd']),
            ssl_start=float(json['sslStart']),
            ssl_end=float(json['sslEnd']),
            worker_start=float(json['workerStart']),
            worker_ready=float(json['workerReady']),
            worker_fetch_start=float(json['workerFetchStart']),
            worker_respond_with_settled=float(json['workerRespondWithSettled']),
            send_start=float(json['sendStart']),
            send_end=float(json['sendEnd']),
            push_start=float(json['pushStart']),
            push_end=float(json['pushEnd']),
            receive_headers_start=float(json['receiveHeadersStart']),
            receive_headers_end=float(json['receiveHeadersEnd']),
            worker_router_evaluation_start=float(json['workerRouterEvaluationStart']) if 'workerRouterEvaluationStart' in json else None,
            worker_cache_lookup_start=float(json['workerCacheLookupStart']) if 'workerCacheLookupStart' in json else None,
        )


class ResourcePriority(enum.Enum):
    '''
    Loading priority of a resource request.
    '''
    VERY_LOW = "VeryLow"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "VeryHigh"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PostDataEntry:
    '''
    Post data entry for HTTP request
    '''
    bytes_: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        if self.bytes_ is not None:
            json['bytes'] = self.bytes_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            bytes_=str(json['bytes']) if 'bytes' in json else None,
        )


@dataclass
class Request:
    '''
    HTTP request data.
    '''
    #: Request URL (without fragment).
    url: str

    #: HTTP request method.
    method: str

    #: HTTP request headers.
    headers: Headers

    #: Priority of the resource request at the time request is sent.
    initial_priority: ResourcePriority

    #: The referrer policy of the request, as defined in https://www.w3.org/TR/referrer-policy/
    referrer_policy: str

    #: Fragment of the requested URL starting with hash, if present.
    url_fragment: typing.Optional[str] = None

    #: HTTP POST request data.
    #: Use postDataEntries instead.
    post_data: typing.Optional[str] = None

    #: True when the request has POST data. Note that postData might still be omitted when this flag is true when the data is too long.
    has_post_data: typing.Optional[bool] = None

    #: Request body elements (post data broken into individual entries).
    post_data_entries: typing.Optional[typing.List[PostDataEntry]] = None

    #: The mixed content type of the request.
    mixed_content_type: typing.Optional[security.MixedContentType] = None

    #: Whether is loaded via link preload.
    is_link_preload: typing.Optional[bool] = None

    #: Set for requests when the TrustToken API is used. Contains the parameters
    #: passed by the developer (e.g. via "fetch") as understood by the backend.
    trust_token_params: typing.Optional[TrustTokenParams] = None

    #: True if this resource request is considered to be the 'same site' as the
    #: request corresponding to the main frame.
    is_same_site: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['method'] = self.method
        json['headers'] = self.headers.to_json()
        json['initialPriority'] = self.initial_priority.to_json()
        json['referrerPolicy'] = self.referrer_policy
        if self.url_fragment is not None:
            json['urlFragment'] = self.url_fragment
        if self.post_data is not None:
            json['postData'] = self.post_data
        if self.has_post_data is not None:
            json['hasPostData'] = self.has_post_data
        if self.post_data_entries is not None:
            json['postDataEntries'] = [i.to_json() for i in self.post_data_entries]
        if self.mixed_content_type is not None:
            json['mixedContentType'] = self.mixed_content_type.to_json()
        if self.is_link_preload is not None:
            json['isLinkPreload'] = self.is_link_preload
        if self.trust_token_params is not None:
            json['trustTokenParams'] = self.trust_token_params.to_json()
        if self.is_same_site is not None:
            json['isSameSite'] = self.is_same_site
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            method=str(json['method']),
            headers=Headers.from_json(json['headers']),
            initial_priority=ResourcePriority.from_json(json['initialPriority']),
            referrer_policy=str(json['referrerPolicy']),
            url_fragment=str(json['urlFragment']) if 'urlFragment' in json else None,
            post_data=str(json['postData']) if 'postData' in json else None,
            has_post_data=bool(json['hasPostData']) if 'hasPostData' in json else None,
            post_data_entries=[PostDataEntry.from_json(i) for i in json['postDataEntries']] if 'postDataEntries' in json else None,
            mixed_content_type=security.MixedContentType.from_json(json['mixedContentType']) if 'mixedContentType' in json else None,
            is_link_preload=bool(json['isLinkPreload']) if 'isLinkPreload' in json else None,
            trust_token_params=TrustTokenParams.from_json(json['trustTokenParams']) if 'trustTokenParams' in json else None,
            is_same_site=bool(json['isSameSite']) if 'isSameSite' in json else None,
        )


@dataclass
class SignedCertificateTimestamp:
    '''
    Details of a signed certificate timestamp (SCT).
    '''
    #: Validation status.
    status: str

    #: Origin.
    origin: str

    #: Log name / description.
    log_description: str

    #: Log ID.
    log_id: str

    #: Issuance date. Unlike TimeSinceEpoch, this contains the number of
    #: milliseconds since January 1, 1970, UTC, not the number of seconds.
    timestamp: float

    #: Hash algorithm.
    hash_algorithm: str

    #: Signature algorithm.
    signature_algorithm: str

    #: Signature data.
    signature_data: str

    def to_json(self):
        json = dict()
        json['status'] = self.status
        json['origin'] = self.origin
        json['logDescription'] = self.log_description
        json['logId'] = self.log_id
        json['timestamp'] = self.timestamp
        json['hashAlgorithm'] = self.hash_algorithm
        json['signatureAlgorithm'] = self.signature_algorithm
        json['signatureData'] = self.signature_data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            status=str(json['status']),
            origin=str(json['origin']),
            log_description=str(json['logDescription']),
            log_id=str(json['logId']),
            timestamp=float(json['timestamp']),
            hash_algorithm=str(json['hashAlgorithm']),
            signature_algorithm=str(json['signatureAlgorithm']),
            signature_data=str(json['signatureData']),
        )


@dataclass
class SecurityDetails:
    '''
    Security details about a request.
    '''
    #: Protocol name (e.g. "TLS 1.2" or "QUIC").
    protocol: str

    #: Key Exchange used by the connection, or the empty string if not applicable.
    key_exchange: str

    #: Cipher name.
    cipher: str

    #: Certificate ID value.
    certificate_id: security.CertificateId

    #: Certificate subject name.
    subject_name: str

    #: Subject Alternative Name (SAN) DNS names and IP addresses.
    san_list: typing.List[str]

    #: Name of the issuing CA.
    issuer: str

    #: Certificate valid from date.
    valid_from: TimeSinceEpoch

    #: Certificate valid to (expiration) date
    valid_to: TimeSinceEpoch

    #: List of signed certificate timestamps (SCTs).
    signed_certificate_timestamp_list: typing.List[SignedCertificateTimestamp]

    #: Whether the request complied with Certificate Transparency policy
    certificate_transparency_compliance: CertificateTransparencyCompliance

    #: Whether the connection used Encrypted ClientHello
    encrypted_client_hello: bool

    #: (EC)DH group used by the connection, if applicable.
    key_exchange_group: typing.Optional[str] = None

    #: TLS MAC. Note that AEAD ciphers do not have separate MACs.
    mac: typing.Optional[str] = None

    #: The signature algorithm used by the server in the TLS server signature,
    #: represented as a TLS SignatureScheme code point. Omitted if not
    #: applicable or not known.
    server_signature_algorithm: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        json['protocol'] = self.protocol
        json['keyExchange'] = self.key_exchange
        json['cipher'] = self.cipher
        json['certificateId'] = self.certificate_id.to_json()
        json['subjectName'] = self.subject_name
        json['sanList'] = [i for i in self.san_list]
        json['issuer'] = self.issuer
        json['validFrom'] = self.valid_from.to_json()
        json['validTo'] = self.valid_to.to_json()
        json['signedCertificateTimestampList'] = [i.to_json() for i in self.signed_certificate_timestamp_list]
        json['certificateTransparencyCompliance'] = self.certificate_transparency_compliance.to_json()
        json['encryptedClientHello'] = self.encrypted_client_hello
        if self.key_exchange_group is not None:
            json['keyExchangeGroup'] = self.key_exchange_group
        if self.mac is not None:
            json['mac'] = self.mac
        if self.server_signature_algorithm is not None:
            json['serverSignatureAlgorithm'] = self.server_signature_algorithm
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            protocol=str(json['protocol']),
            key_exchange=str(json['keyExchange']),
            cipher=str(json['cipher']),
            certificate_id=security.CertificateId.from_json(json['certificateId']),
            subject_name=str(json['subjectName']),
            san_list=[str(i) for i in json['sanList']],
            issuer=str(json['issuer']),
            valid_from=TimeSinceEpoch.from_json(json['validFrom']),
            valid_to=TimeSinceEpoch.from_json(json['validTo']),
            signed_certificate_timestamp_list=[SignedCertificateTimestamp.from_json(i) for i in json['signedCertificateTimestampList']],
            certificate_transparency_compliance=CertificateTransparencyCompliance.from_json(json['certificateTransparencyCompliance']),
            encrypted_client_hello=bool(json['encryptedClientHello']),
            key_exchange_group=str(json['keyExchangeGroup']) if 'keyExchangeGroup' in json else None,
            mac=str(json['mac']) if 'mac' in json else None,
            server_signature_algorithm=int(json['serverSignatureAlgorithm']) if 'serverSignatureAlgorithm' in json else None,
        )


class CertificateTransparencyCompliance(enum.Enum):
    '''
    Whether the request complied with Certificate Transparency policy.
    '''
    UNKNOWN = "unknown"
    NOT_COMPLIANT = "not-compliant"
    COMPLIANT = "compliant"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class BlockedReason(enum.Enum):
    '''
    The reason why request was blocked.
    '''
    OTHER = "other"
    CSP = "csp"
    MIXED_CONTENT = "mixed-content"
    ORIGIN = "origin"
    INSPECTOR = "inspector"
    SUBRESOURCE_FILTER = "subresource-filter"
    CONTENT_TYPE = "content-type"
    COEP_FRAME_RESOURCE_NEEDS_COEP_HEADER = "coep-frame-resource-needs-coep-header"
    COOP_SANDBOXED_IFRAME_CANNOT_NAVIGATE_TO_COOP_PAGE = "coop-sandboxed-iframe-cannot-navigate-to-coop-page"
    CORP_NOT_SAME_ORIGIN = "corp-not-same-origin"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_COEP = "corp-not-same-origin-after-defaulted-to-same-origin-by-coep"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_DIP = "corp-not-same-origin-after-defaulted-to-same-origin-by-dip"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_COEP_AND_DIP = "corp-not-same-origin-after-defaulted-to-same-origin-by-coep-and-dip"
    CORP_NOT_SAME_SITE = "corp-not-same-site"
    SRI_MESSAGE_SIGNATURE_MISMATCH = "sri-message-signature-mismatch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CorsError(enum.Enum):
    '''
    The reason why request was blocked.
    '''
    DISALLOWED_BY_MODE = "DisallowedByMode"
    INVALID_RESPONSE = "InvalidResponse"
    WILDCARD_ORIGIN_NOT_ALLOWED = "WildcardOriginNotAllowed"
    MISSING_ALLOW_ORIGIN_HEADER = "MissingAllowOriginHeader"
    MULTIPLE_ALLOW_ORIGIN_VALUES = "MultipleAllowOriginValues"
    INVALID_ALLOW_ORIGIN_VALUE = "InvalidAllowOriginValue"
    ALLOW_ORIGIN_MISMATCH = "AllowOriginMismatch"
    INVALID_ALLOW_CREDENTIALS = "InvalidAllowCredentials"
    CORS_DISABLED_SCHEME = "CorsDisabledScheme"
    PREFLIGHT_INVALID_STATUS = "PreflightInvalidStatus"
    PREFLIGHT_DISALLOWED_REDIRECT = "PreflightDisallowedRedirect"
    PREFLIGHT_WILDCARD_ORIGIN_NOT_ALLOWED = "PreflightWildcardOriginNotAllowed"
    PREFLIGHT_MISSING_ALLOW_ORIGIN_HEADER = "PreflightMissingAllowOriginHeader"
    PREFLIGHT_MULTIPLE_ALLOW_ORIGIN_VALUES = "PreflightMultipleAllowOriginValues"
    PREFLIGHT_INVALID_ALLOW_ORIGIN_VALUE = "PreflightInvalidAllowOriginValue"
    PREFLIGHT_ALLOW_ORIGIN_MISMATCH = "PreflightAllowOriginMismatch"
    PREFLIGHT_INVALID_ALLOW_CREDENTIALS = "PreflightInvalidAllowCredentials"
    PREFLIGHT_MISSING_ALLOW_EXTERNAL = "PreflightMissingAllowExternal"
    PREFLIGHT_INVALID_ALLOW_EXTERNAL = "PreflightInvalidAllowExternal"
    PREFLIGHT_MISSING_ALLOW_PRIVATE_NETWORK = "PreflightMissingAllowPrivateNetwork"
    PREFLIGHT_INVALID_ALLOW_PRIVATE_NETWORK = "PreflightInvalidAllowPrivateNetwork"
    INVALID_ALLOW_METHODS_PREFLIGHT_RESPONSE = "InvalidAllowMethodsPreflightResponse"
    INVALID_ALLOW_HEADERS_PREFLIGHT_RESPONSE = "InvalidAllowHeadersPreflightResponse"
    METHOD_DISALLOWED_BY_PREFLIGHT_RESPONSE = "MethodDisallowedByPreflightResponse"
    HEADER_DISALLOWED_BY_PREFLIGHT_RESPONSE = "HeaderDisallowedByPreflightResponse"
    REDIRECT_CONTAINS_CREDENTIALS = "RedirectContainsCredentials"
    INSECURE_PRIVATE_NETWORK = "InsecurePrivateNetwork"
    INVALID_PRIVATE_NETWORK_ACCESS = "InvalidPrivateNetworkAccess"
    UNEXPECTED_PRIVATE_NETWORK_ACCESS = "UnexpectedPrivateNetworkAccess"
    NO_CORS_REDIRECT_MODE_NOT_FOLLOW = "NoCorsRedirectModeNotFollow"
    PREFLIGHT_MISSING_PRIVATE_NETWORK_ACCESS_ID = "PreflightMissingPrivateNetworkAccessId"
    PREFLIGHT_MISSING_PRIVATE_NETWORK_ACCESS_NAME = "PreflightMissingPrivateNetworkAccessName"
    PRIVATE_NETWORK_ACCESS_PERMISSION_UNAVAILABLE = "PrivateNetworkAccessPermissionUnavailable"
    PRIVATE_NETWORK_ACCESS_PERMISSION_DENIED = "PrivateNetworkAccessPermissionDenied"
    LOCAL_NETWORK_ACCESS_PERMISSION_DENIED = "LocalNetworkAccessPermissionDenied"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CorsErrorStatus:
    cors_error: CorsError

    failed_parameter: str

    def to_json(self):
        json = dict()
        json['corsError'] = self.cors_error.to_json()
        json['failedParameter'] = self.failed_parameter
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cors_error=CorsError.from_json(json['corsError']),
            failed_parameter=str(json['failedParameter']),
        )


class ServiceWorkerResponseSource(enum.Enum):
    '''
    Source of serviceworker response.
    '''
    CACHE_STORAGE = "cache-storage"
    HTTP_CACHE = "http-cache"
    FALLBACK_CODE = "fallback-code"
    NETWORK = "network"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class TrustTokenParams:
    '''
    Determines what type of Trust Token operation is executed and
    depending on the type, some additional parameters. The values
    are specified in third_party/blink/renderer/core/fetch/trust_token.idl.
    '''
    operation: TrustTokenOperationType

    #: Only set for "token-redemption" operation and determine whether
    #: to request a fresh SRR or use a still valid cached SRR.
    refresh_policy: str

    #: Origins of issuers from whom to request tokens or redemption
    #: records.
    issuers: typing.Optional[typing.List[str]] = None

    def to_json(self):
        json = dict()
        json['operation'] = self.operation.to_json()
        json['refreshPolicy'] = self.refresh_policy
        if self.issuers is not None:
            json['issuers'] = [i for i in self.issuers]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            operation=TrustTokenOperationType.from_json(json['operation']),
            refresh_policy=str(json['refreshPolicy']),
            issuers=[str(i) for i in json['issuers']] if 'issuers' in json else None,
        )


class TrustTokenOperationType(enum.Enum):
    ISSUANCE = "Issuance"
    REDEMPTION = "Redemption"
    SIGNING = "Signing"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AlternateProtocolUsage(enum.Enum):
    '''
    The reason why Chrome uses a specific transport protocol for HTTP semantics.
    '''
    ALTERNATIVE_JOB_WON_WITHOUT_RACE = "alternativeJobWonWithoutRace"
    ALTERNATIVE_JOB_WON_RACE = "alternativeJobWonRace"
    MAIN_JOB_WON_RACE = "mainJobWonRace"
    MAPPING_MISSING = "mappingMissing"
    BROKEN = "broken"
    DNS_ALPN_H3_JOB_WON_WITHOUT_RACE = "dnsAlpnH3JobWonWithoutRace"
    DNS_ALPN_H3_JOB_WON_RACE = "dnsAlpnH3JobWonRace"
    UNSPECIFIED_REASON = "unspecifiedReason"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ServiceWorkerRouterSource(enum.Enum):
    '''
    Source of service worker router.
    '''
    NETWORK = "network"
    CACHE = "cache"
    FETCH_EVENT = "fetch-event"
    RACE_NETWORK_AND_FETCH_HANDLER = "race-network-and-fetch-handler"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ServiceWorkerRouterInfo:
    #: ID of the rule matched. If there is a matched rule, this field will
    #: be set, otherwiser no value will be set.
    rule_id_matched: typing.Optional[int] = None

    #: The router source of the matched rule. If there is a matched rule, this
    #: field will be set, otherwise no value will be set.
    matched_source_type: typing.Optional[ServiceWorkerRouterSource] = None

    #: The actual router source used.
    actual_source_type: typing.Optional[ServiceWorkerRouterSource] = None

    def to_json(self):
        json = dict()
        if self.rule_id_matched is not None:
            json['ruleIdMatched'] = self.rule_id_matched
        if self.matched_source_type is not None:
            json['matchedSourceType'] = self.matched_source_type.to_json()
        if self.actual_source_type is not None:
            json['actualSourceType'] = self.actual_source_type.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            rule_id_matched=int(json['ruleIdMatched']) if 'ruleIdMatched' in json else None,
            matched_source_type=ServiceWorkerRouterSource.from_json(json['matchedSourceType']) if 'matchedSourceType' in json else None,
            actual_source_type=ServiceWorkerRouterSource.from_json(json['actualSourceType']) if 'actualSourceType' in json else None,
        )


@dataclass
class Response:
    '''
    HTTP response data.
    '''
    #: Response URL. This URL can be different from CachedResource.url in case of redirect.
    url: str

    #: HTTP response status code.
    status: int

    #: HTTP response status text.
    status_text: str

    #: HTTP response headers.
    headers: Headers

    #: Resource mimeType as determined by the browser.
    mime_type: str

    #: Resource charset as determined by the browser (if applicable).
    charset: str

    #: Specifies whether physical connection was actually reused for this request.
    connection_reused: bool

    #: Physical connection id that was actually used for this request.
    connection_id: float

    #: Total number of bytes received for this request so far.
    encoded_data_length: float

    #: Security state of the request resource.
    security_state: security.SecurityState

    #: HTTP response headers text. This has been replaced by the headers in Network.responseReceivedExtraInfo.
    headers_text: typing.Optional[str] = None

    #: Refined HTTP request headers that were actually transmitted over the network.
    request_headers: typing.Optional[Headers] = None

    #: HTTP request headers text. This has been replaced by the headers in Network.requestWillBeSentExtraInfo.
    request_headers_text: typing.Optional[str] = None

    #: Remote IP address.
    remote_ip_address: typing.Optional[str] = None

    #: Remote port.
    remote_port: typing.Optional[int] = None

    #: Specifies that the request was served from the disk cache.
    from_disk_cache: typing.Optional[bool] = None

    #: Specifies that the request was served from the ServiceWorker.
    from_service_worker: typing.Optional[bool] = None

    #: Specifies that the request was served from the prefetch cache.
    from_prefetch_cache: typing.Optional[bool] = None

    #: Specifies that the request was served from the prefetch cache.
    from_early_hints: typing.Optional[bool] = None

    #: Information about how ServiceWorker Static Router API was used. If this
    #: field is set with ``matchedSourceType`` field, a matching rule is found.
    #: If this field is set without ``matchedSource``, no matching rule is found.
    #: Otherwise, the API is not used.
    service_worker_router_info: typing.Optional[ServiceWorkerRouterInfo] = None

    #: Timing information for the given request.
    timing: typing.Optional[ResourceTiming] = None

    #: Response source of response from ServiceWorker.
    service_worker_response_source: typing.Optional[ServiceWorkerResponseSource] = None

    #: The time at which the returned response was generated.
    response_time: typing.Optional[TimeSinceEpoch] = None

    #: Cache Storage Cache Name.
    cache_storage_cache_name: typing.Optional[str] = None

    #: Protocol used to fetch this request.
    protocol: typing.Optional[str] = None

    #: The reason why Chrome uses a specific transport protocol for HTTP semantics.
    alternate_protocol_usage: typing.Optional[AlternateProtocolUsage] = None

    #: Security details for the request.
    security_details: typing.Optional[SecurityDetails] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['status'] = self.status
        json['statusText'] = self.status_text
        json['headers'] = self.headers.to_json()
        json['mimeType'] = self.mime_type
        json['charset'] = self.charset
        json['connectionReused'] = self.connection_reused
        json['connectionId'] = self.connection_id
        json['encodedDataLength'] = self.encoded_data_length
        json['securityState'] = self.security_state.to_json()
        if self.headers_text is not None:
            json['headersText'] = self.headers_text
        if self.request_headers is not None:
            json['requestHeaders'] = self.request_headers.to_json()
        if self.request_headers_text is not None:
            json['requestHeadersText'] = self.request_headers_text
        if self.remote_ip_address is not None:
            json['remoteIPAddress'] = self.remote_ip_address
        if self.remote_port is not None:
            json['remotePort'] = self.remote_port
        if self.from_disk_cache is not None:
            json['fromDiskCache'] = self.from_disk_cache
        if self.from_service_worker is not None:
            json['fromServiceWorker'] = self.from_service_worker
        if self.from_prefetch_cache is not None:
            json['fromPrefetchCache'] = self.from_prefetch_cache
        if self.from_early_hints is not None:
            json['fromEarlyHints'] = self.from_early_hints
        if self.service_worker_router_info is not None:
            json['serviceWorkerRouterInfo'] = self.service_worker_router_info.to_json()
        if self.timing is not None:
            json['timing'] = self.timing.to_json()
        if self.service_worker_response_source is not None:
            json['serviceWorkerResponseSource'] = self.service_worker_response_source.to_json()
        if self.response_time is not None:
            json['responseTime'] = self.response_time.to_json()
        if self.cache_storage_cache_name is not None:
            json['cacheStorageCacheName'] = self.cache_storage_cache_name
        if self.protocol is not None:
            json['protocol'] = self.protocol
        if self.alternate_protocol_usage is not None:
            json['alternateProtocolUsage'] = self.alternate_protocol_usage.to_json()
        if self.security_details is not None:
            json['securityDetails'] = self.security_details.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            status=int(json['status']),
            status_text=str(json['statusText']),
            headers=Headers.from_json(json['headers']),
            mime_type=str(json['mimeType']),
            charset=str(json['charset']),
            connection_reused=bool(json['connectionReused']),
            connection_id=float(json['connectionId']),
            encoded_data_length=float(json['encodedDataLength']),
            security_state=security.SecurityState.from_json(json['securityState']),
            headers_text=str(json['headersText']) if 'headersText' in json else None,
            request_headers=Headers.from_json(json['requestHeaders']) if 'requestHeaders' in json else None,
            request_headers_text=str(json['requestHeadersText']) if 'requestHeadersText' in json else None,
            remote_ip_address=str(json['remoteIPAddress']) if 'remoteIPAddress' in json else None,
            remote_port=int(json['remotePort']) if 'remotePort' in json else None,
            from_disk_cache=bool(json['fromDiskCache']) if 'fromDiskCache' in json else None,
            from_service_worker=bool(json['fromServiceWorker']) if 'fromServiceWorker' in json else None,
            from_prefetch_cache=bool(json['fromPrefetchCache']) if 'fromPrefetchCache' in json else None,
            from_early_hints=bool(json['fromEarlyHints']) if 'fromEarlyHints' in json else None,
            service_worker_router_info=ServiceWorkerRouterInfo.from_json(json['serviceWorkerRouterInfo']) if 'serviceWorkerRouterInfo' in json else None,
            timing=ResourceTiming.from_json(json['timing']) if 'timing' in json else None,
            service_worker_response_source=ServiceWorkerResponseSource.from_json(json['serviceWorkerResponseSource']) if 'serviceWorkerResponseSource' in json else None,
            response_time=TimeSinceEpoch.from_json(json['responseTime']) if 'responseTime' in json else None,
            cache_storage_cache_name=str(json['cacheStorageCacheName']) if 'cacheStorageCacheName' in json else None,
            protocol=str(json['protocol']) if 'protocol' in json else None,
            alternate_protocol_usage=AlternateProtocolUsage.from_json(json['alternateProtocolUsage']) if 'alternateProtocolUsage' in json else None,
            security_details=SecurityDetails.from_json(json['securityDetails']) if 'securityDetails' in json else None,
        )


@dataclass
class WebSocketRequest:
    '''
    WebSocket request data.
    '''
    #: HTTP request headers.
    headers: Headers

    def to_json(self):
        json = dict()
        json['headers'] = self.headers.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            headers=Headers.from_json(json['headers']),
        )


@dataclass
class WebSocketResponse:
    '''
    WebSocket response data.
    '''
    #: HTTP response status code.
    status: int

    #: HTTP response status text.
    status_text: str

    #: HTTP response headers.
    headers: Headers

    #: HTTP response headers text.
    headers_text: typing.Optional[str] = None

    #: HTTP request headers.
    request_headers: typing.Optional[Headers] = None

    #: HTTP request headers text.
    request_headers_text: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['status'] = self.status
        json['statusText'] = self.status_text
        json['headers'] = self.headers.to_json()
        if self.headers_text is not None:
            json['headersText'] = self.headers_text
        if self.request_headers is not None:
            json['requestHeaders'] = self.request_headers.to_json()
        if self.request_headers_text is not None:
            json['requestHeadersText'] = self.request_headers_text
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            status=int(json['status']),
            status_text=str(json['statusText']),
            headers=Headers.from_json(json['headers']),
            headers_text=str(json['headersText']) if 'headersText' in json else None,
            request_headers=Headers.from_json(json['requestHeaders']) if 'requestHeaders' in json else None,
            request_headers_text=str(json['requestHeadersText']) if 'requestHeadersText' in json else None,
        )


@dataclass
class WebSocketFrame:
    '''
    WebSocket message data. This represents an entire WebSocket message, not just a fragmented frame as the name suggests.
    '''
    #: WebSocket message opcode.
    opcode: float

    #: WebSocket message mask.
    mask: bool

    #: WebSocket message payload data.
    #: If the opcode is 1, this is a text message and payloadData is a UTF-8 string.
    #: If the opcode isn't 1, then payloadData is a base64 encoded string representing binary data.
    payload_data: str

    def to_json(self):
        json = dict()
        json['opcode'] = self.opcode
        json['mask'] = self.mask
        json['payloadData'] = self.payload_data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            opcode=float(json['opcode']),
            mask=bool(json['mask']),
            payload_data=str(json['payloadData']),
        )


@dataclass
class CachedResource:
    '''
    Information about the cached resource.
    '''
    #: Resource URL. This is the url of the original network request.
    url: str

    #: Type of this resource.
    type_: ResourceType

    #: Cached response body size.
    body_size: float

    #: Cached response data.
    response: typing.Optional[Response] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['type'] = self.type_.to_json()
        json['bodySize'] = self.body_size
        if self.response is not None:
            json['response'] = self.response.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            type_=ResourceType.from_json(json['type']),
            body_size=float(json['bodySize']),
            response=Response.from_json(json['response']) if 'response' in json else None,
        )


@dataclass
class Initiator:
    '''
    Information about the request initiator.
    '''
    #: Type of this initiator.
    type_: str

    #: Initiator JavaScript stack trace, set for Script only.
    #: Requires the Debugger domain to be enabled.
    stack: typing.Optional[runtime.StackTrace] = None

    #: Initiator URL, set for Parser type or for Script type (when script is importing module) or for SignedExchange type.
    url: typing.Optional[str] = None

    #: Initiator line number, set for Parser type or for Script type (when script is importing
    #: module) (0-based).
    line_number: typing.Optional[float] = None

    #: Initiator column number, set for Parser type or for Script type (when script is importing
    #: module) (0-based).
    column_number: typing.Optional[float] = None

    #: Set if another request triggered this request (e.g. preflight).
    request_id: typing.Optional[RequestId] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.stack is not None:
            json['stack'] = self.stack.to_json()
        if self.url is not None:
            json['url'] = self.url
        if self.line_number is not None:
            json['lineNumber'] = self.line_number
        if self.column_number is not None:
            json['columnNumber'] = self.column_number
        if self.request_id is not None:
            json['requestId'] = self.request_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            stack=runtime.StackTrace.from_json(json['stack']) if 'stack' in json else None,
            url=str(json['url']) if 'url' in json else None,
            line_number=float(json['lineNumber']) if 'lineNumber' in json else None,
            column_number=float(json['columnNumber']) if 'columnNumber' in json else None,
            request_id=RequestId.from_json(json['requestId']) if 'requestId' in json else None,
        )


@dataclass
class CookiePartitionKey:
    '''
    cookiePartitionKey object
    The representation of the components of the key that are created by the cookiePartitionKey class contained in net/cookies/cookie_partition_key.h.
    '''
    #: The site of the top-level URL the browser was visiting at the start
    #: of the request to the endpoint that set the cookie.
    top_level_site: str

    #: Indicates if the cookie has any ancestors that are cross-site to the topLevelSite.
    has_cross_site_ancestor: bool

    def to_json(self):
        json = dict()
        json['topLevelSite'] = self.top_level_site
        json['hasCrossSiteAncestor'] = self.has_cross_site_ancestor
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            top_level_site=str(json['topLevelSite']),
            has_cross_site_ancestor=bool(json['hasCrossSiteAncestor']),
        )


@dataclass
class Cookie:
    '''
    Cookie object
    '''
    #: Cookie name.
    name: str

    #: Cookie value.
    value: str

    #: Cookie domain.
    domain: str

    #: Cookie path.
    path: str

    #: Cookie expiration date as the number of seconds since the UNIX epoch.
    expires: float

    #: Cookie size.
    size: int

    #: True if cookie is http-only.
    http_only: bool

    #: True if cookie is secure.
    secure: bool

    #: True in case of session cookie.
    session: bool

    #: Cookie Priority
    priority: CookiePriority

    #: True if cookie is SameParty.
    same_party: bool

    #: Cookie source scheme type.
    source_scheme: CookieSourceScheme

    #: Cookie source port. Valid values are {-1, [1, 65535]}, -1 indicates an unspecified port.
    #: An unspecified port value allows protocol clients to emulate legacy cookie scope for the port.
    #: This is a temporary ability and it will be removed in the future.
    source_port: int

    #: Cookie SameSite type.
    same_site: typing.Optional[CookieSameSite] = None

    #: Cookie partition key.
    partition_key: typing.Optional[CookiePartitionKey] = None

    #: True if cookie partition key is opaque.
    partition_key_opaque: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        json['domain'] = self.domain
        json['path'] = self.path
        json['expires'] = self.expires
        json['size'] = self.size
        json['httpOnly'] = self.http_only
        json['secure'] = self.secure
        json['session'] = self.session
        json['priority'] = self.priority.to_json()
        json['sameParty'] = self.same_party
        json['sourceScheme'] = self.source_scheme.to_json()
        json['sourcePort'] = self.source_port
        if self.same_site is not None:
            json['sameSite'] = self.same_site.to_json()
        if self.partition_key is not None:
            json['partitionKey'] = self.partition_key.to_json()
        if self.partition_key_opaque is not None:
            json['partitionKeyOpaque'] = self.partition_key_opaque
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
            domain=str(json['domain']),
            path=str(json['path']),
            expires=float(json['expires']),
            size=int(json['size']),
            http_only=bool(json['httpOnly']),
            secure=bool(json['secure']),
            session=bool(json['session']),
            priority=CookiePriority.from_json(json['priority']),
            same_party=bool(json['sameParty']),
            source_scheme=CookieSourceScheme.from_json(json['sourceScheme']),
            source_port=int(json['sourcePort']),
            same_site=CookieSameSite.from_json(json['sameSite']) if 'sameSite' in json else None,
            partition_key=CookiePartitionKey.from_json(json['partitionKey']) if 'partitionKey' in json else None,
            partition_key_opaque=bool(json['partitionKeyOpaque']) if 'partitionKeyOpaque' in json else None,
        )


class SetCookieBlockedReason(enum.Enum):
    '''
    Types of reasons why a cookie may not be stored from a response.
    '''
    SECURE_ONLY = "SecureOnly"
    SAME_SITE_STRICT = "SameSiteStrict"
    SAME_SITE_LAX = "SameSiteLax"
    SAME_SITE_UNSPECIFIED_TREATED_AS_LAX = "SameSiteUnspecifiedTreatedAsLax"
    SAME_SITE_NONE_INSECURE = "SameSiteNoneInsecure"
    USER_PREFERENCES = "UserPreferences"
    THIRD_PARTY_PHASEOUT = "ThirdPartyPhaseout"
    THIRD_PARTY_BLOCKED_IN_FIRST_PARTY_SET = "ThirdPartyBlockedInFirstPartySet"
    SYNTAX_ERROR = "SyntaxError"
    SCHEME_NOT_SUPPORTED = "SchemeNotSupported"
    OVERWRITE_SECURE = "OverwriteSecure"
    INVALID_DOMAIN = "InvalidDomain"
    INVALID_PREFIX = "InvalidPrefix"
    UNKNOWN_ERROR = "UnknownError"
    SCHEMEFUL_SAME_SITE_STRICT = "SchemefulSameSiteStrict"
    SCHEMEFUL_SAME_SITE_LAX = "SchemefulSameSiteLax"
    SCHEMEFUL_SAME_SITE_UNSPECIFIED_TREATED_AS_LAX = "SchemefulSameSiteUnspecifiedTreatedAsLax"
    SAME_PARTY_FROM_CROSS_PARTY_CONTEXT = "SamePartyFromCrossPartyContext"
    SAME_PARTY_CONFLICTS_WITH_OTHER_ATTRIBUTES = "SamePartyConflictsWithOtherAttributes"
    NAME_VALUE_PAIR_EXCEEDS_MAX_SIZE = "NameValuePairExceedsMaxSize"
    DISALLOWED_CHARACTER = "DisallowedCharacter"
    NO_COOKIE_CONTENT = "NoCookieContent"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieBlockedReason(enum.Enum):
    '''
    Types of reasons why a cookie may not be sent with a request.
    '''
    SECURE_ONLY = "SecureOnly"
    NOT_ON_PATH = "NotOnPath"
    DOMAIN_MISMATCH = "DomainMismatch"
    SAME_SITE_STRICT = "SameSiteStrict"
    SAME_SITE_LAX = "SameSiteLax"
    SAME_SITE_UNSPECIFIED_TREATED_AS_LAX = "SameSiteUnspecifiedTreatedAsLax"
    SAME_SITE_NONE_INSECURE = "SameSiteNoneInsecure"
    USER_PREFERENCES = "UserPreferences"
    THIRD_PARTY_PHASEOUT = "ThirdPartyPhaseout"
    THIRD_PARTY_BLOCKED_IN_FIRST_PARTY_SET = "ThirdPartyBlockedInFirstPartySet"
    UNKNOWN_ERROR = "UnknownError"
    SCHEMEFUL_SAME_SITE_STRICT = "SchemefulSameSiteStrict"
    SCHEMEFUL_SAME_SITE_LAX = "SchemefulSameSiteLax"
    SCHEMEFUL_SAME_SITE_UNSPECIFIED_TREATED_AS_LAX = "SchemefulSameSiteUnspecifiedTreatedAsLax"
    SAME_PARTY_FROM_CROSS_PARTY_CONTEXT = "SamePartyFromCrossPartyContext"
    NAME_VALUE_PAIR_EXCEEDS_MAX_SIZE = "NameValuePairExceedsMaxSize"
    PORT_MISMATCH = "PortMismatch"
    SCHEME_MISMATCH = "SchemeMismatch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieExemptionReason(enum.Enum):
    '''
    Types of reasons why a cookie should have been blocked by 3PCD but is exempted for the request.
    '''
    NONE = "None"
    USER_SETTING = "UserSetting"
    TPCD_METADATA = "TPCDMetadata"
    TPCD_DEPRECATION_TRIAL = "TPCDDeprecationTrial"
    TOP_LEVEL_TPCD_DEPRECATION_TRIAL = "TopLevelTPCDDeprecationTrial"
    TPCD_HEURISTICS = "TPCDHeuristics"
    ENTERPRISE_POLICY = "EnterprisePolicy"
    STORAGE_ACCESS = "StorageAccess"
    TOP_LEVEL_STORAGE_ACCESS = "TopLevelStorageAccess"
    SCHEME = "Scheme"
    SAME_SITE_NONE_COOKIES_IN_SANDBOX = "SameSiteNoneCookiesInSandbox"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class BlockedSetCookieWithReason:
    '''
    A cookie which was not stored from a response with the corresponding reason.
    '''
    #: The reason(s) this cookie was blocked.
    blocked_reasons: typing.List[SetCookieBlockedReason]

    #: The string representing this individual cookie as it would appear in the header.
    #: This is not the entire "cookie" or "set-cookie" header which could have multiple cookies.
    cookie_line: str

    #: The cookie object which represents the cookie which was not stored. It is optional because
    #: sometimes complete cookie information is not available, such as in the case of parsing
    #: errors.
    cookie: typing.Optional[Cookie] = None

    def to_json(self):
        json = dict()
        json['blockedReasons'] = [i.to_json() for i in self.blocked_reasons]
        json['cookieLine'] = self.cookie_line
        if self.cookie is not None:
            json['cookie'] = self.cookie.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            blocked_reasons=[SetCookieBlockedReason.from_json(i) for i in json['blockedReasons']],
            cookie_line=str(json['cookieLine']),
            cookie=Cookie.from_json(json['cookie']) if 'cookie' in json else None,
        )


@dataclass
class ExemptedSetCookieWithReason:
    '''
    A cookie should have been blocked by 3PCD but is exempted and stored from a response with the
    corresponding reason. A cookie could only have at most one exemption reason.
    '''
    #: The reason the cookie was exempted.
    exemption_reason: CookieExemptionReason

    #: The string representing this individual cookie as it would appear in the header.
    cookie_line: str

    #: The cookie object representing the cookie.
    cookie: Cookie

    def to_json(self):
        json = dict()
        json['exemptionReason'] = self.exemption_reason.to_json()
        json['cookieLine'] = self.cookie_line
        json['cookie'] = self.cookie.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            exemption_reason=CookieExemptionReason.from_json(json['exemptionReason']),
            cookie_line=str(json['cookieLine']),
            cookie=Cookie.from_json(json['cookie']),
        )


@dataclass
class AssociatedCookie:
    '''
    A cookie associated with the request which may or may not be sent with it.
    Includes the cookies itself and reasons for blocking or exemption.
    '''
    #: The cookie object representing the cookie which was not sent.
    cookie: Cookie

    #: The reason(s) the cookie was blocked. If empty means the cookie is included.
    blocked_reasons: typing.List[CookieBlockedReason]

    #: The reason the cookie should have been blocked by 3PCD but is exempted. A cookie could
    #: only have at most one exemption reason.
    exemption_reason: typing.Optional[CookieExemptionReason] = None

    def to_json(self):
        json = dict()
        json['cookie'] = self.cookie.to_json()
        json['blockedReasons'] = [i.to_json() for i in self.blocked_reasons]
        if self.exemption_reason is not None:
            json['exemptionReason'] = self.exemption_reason.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cookie=Cookie.from_json(json['cookie']),
            blocked_reasons=[CookieBlockedReason.from_json(i) for i in json['blockedReasons']],
            exemption_reason=CookieExemptionReason.from_json(json['exemptionReason']) if 'exemptionReason' in json else None,
        )


@dataclass
class CookieParam:
    '''
    Cookie parameter object
    '''
    #: Cookie name.
    name: str

    #: Cookie value.
    value: str

    #: The request-URI to associate with the setting of the cookie. This value can affect the
    #: default domain, path, source port, and source scheme values of the created cookie.
    url: typing.Optional[str] = None

    #: Cookie domain.
    domain: typing.Optional[str] = None

    #: Cookie path.
    path: typing.Optional[str] = None

    #: True if cookie is secure.
    secure: typing.Optional[bool] = None

    #: True if cookie is http-only.
    http_only: typing.Optional[bool] = None

    #: Cookie SameSite type.
    same_site: typing.Optional[CookieSameSite] = None

    #: Cookie expiration date, session cookie if not set
    expires: typing.Optional[TimeSinceEpoch] = None

    #: Cookie Priority.
    priority: typing.Optional[CookiePriority] = None

    #: True if cookie is SameParty.
    same_party: typing.Optional[bool] = None

    #: Cookie source scheme type.
    source_scheme: typing.Optional[CookieSourceScheme] = None

    #: Cookie source port. Valid values are {-1, [1, 65535]}, -1 indicates an unspecified port.
    #: An unspecified port value allows protocol clients to emulate legacy cookie scope for the port.
    #: This is a temporary ability and it will be removed in the future.
    source_port: typing.Optional[int] = None

    #: Cookie partition key. If not set, the cookie will be set as not partitioned.
    partition_key: typing.Optional[CookiePartitionKey] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        if self.url is not None:
            json['url'] = self.url
        if self.domain is not None:
            json['domain'] = self.domain
        if self.path is not None:
            json['path'] = self.path
        if self.secure is not None:
            json['secure'] = self.secure
        if self.http_only is not None:
            json['httpOnly'] = self.http_only
        if self.same_site is not None:
            json['sameSite'] = self.same_site.to_json()
        if self.expires is not None:
            json['expires'] = self.expires.to_json()
        if self.priority is not None:
            json['priority'] = self.priority.to_json()
        if self.same_party is not None:
            json['sameParty'] = self.same_party
        if self.source_scheme is not None:
            json['sourceScheme'] = self.source_scheme.to_json()
        if self.source_port is not None:
            json['sourcePort'] = self.source_port
        if self.partition_key is not None:
            json['partitionKey'] = self.partition_key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
            url=str(json['url']) if 'url' in json else None,
            domain=str(json['domain']) if 'domain' in json else None,
            path=str(json['path']) if 'path' in json else None,
            secure=bool(json['secure']) if 'secure' in json else None,
            http_only=bool(json['httpOnly']) if 'httpOnly' in json else None,
            same_site=CookieSameSite.from_json(json['sameSite']) if 'sameSite' in json else None,
            expires=TimeSinceEpoch.from_json(json['expires']) if 'expires' in json else None,
            priority=CookiePriority.from_json(json['priority']) if 'priority' in json else None,
            same_party=bool(json['sameParty']) if 'sameParty' in json else None,
            source_scheme=CookieSourceScheme.from_json(json['sourceScheme']) if 'sourceScheme' in json else None,
            source_port=int(json['sourcePort']) if 'sourcePort' in json else None,
            partition_key=CookiePartitionKey.from_json(json['partitionKey']) if 'partitionKey' in json else None,
        )


@dataclass
class AuthChallenge:
    '''
    Authorization challenge for HTTP status code 401 or 407.
    '''
    #: Origin of the challenger.
    origin: str

    #: The authentication scheme used, such as basic or digest
    scheme: str

    #: The realm of the challenge. May be empty.
    realm: str

    #: Source of the authentication challenge.
    source: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['origin'] = self.origin
        json['scheme'] = self.scheme
        json['realm'] = self.realm
        if self.source is not None:
            json['source'] = self.source
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            origin=str(json['origin']),
            scheme=str(json['scheme']),
            realm=str(json['realm']),
            source=str(json['source']) if 'source' in json else None,
        )


@dataclass
class AuthChallengeResponse:
    '''
    Response to an AuthChallenge.
    '''
    #: The decision on what to do in response to the authorization challenge.  Default means
    #: deferring to the default behavior of the net stack, which will likely either the Cancel
    #: authentication or display a popup dialog box.
    response: str

    #: The username to provide, possibly empty. Should only be set if response is
    #: ProvideCredentials.
    username: typing.Optional[str] = None

    #: The password to provide, possibly empty. Should only be set if response is
    #: ProvideCredentials.
    password: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['response'] = self.response
        if self.username is not None:
            json['username'] = self.username
        if self.password is not None:
            json['password'] = self.password
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            response=str(json['response']),
            username=str(json['username']) if 'username' in json else None,
            password=str(json['password']) if 'password' in json else None,
        )


class InterceptionStage(enum.Enum):
    '''
    Stages of the interception to begin intercepting. Request will intercept before the request is
    sent. Response will intercept after the response is received.
    '''
    REQUEST = "Request"
    HEADERS_RECEIVED = "HeadersReceived"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class RequestPattern:
    '''
    Request pattern for interception.
    '''
    #: Wildcards (``'*'`` -> zero or more, ``'?'`` -> exactly one) are allowed. Escape character is
    #: backslash. Omitting is equivalent to ``"*"``.
    url_pattern: typing.Optional[str] = None

    #: If set, only requests for matching resource types will be intercepted.
    resource_type: typing.Optional[ResourceType] = None

    #: Stage at which to begin intercepting requests. Default is Request.
    interception_stage: typing.Optional[InterceptionStage] = None

    def to_json(self):
        json = dict()
        if self.url_pattern is not None:
            json['urlPattern'] = self.url_pattern
        if self.resource_type is not None:
            json['resourceType'] = self.resource_type.to_json()
        if self.interception_stage is not None:
            json['interceptionStage'] = self.interception_stage.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url_pattern=str(json['urlPattern']) if 'urlPattern' in json else None,
            resource_type=ResourceType.from_json(json['resourceType']) if 'resourceType' in json else None,
            interception_stage=InterceptionStage.from_json(json['interceptionStage']) if 'interceptionStage' in json else None,
        )


@dataclass
class SignedExchangeSignature:
    '''
    Information about a signed exchange signature.
    https://wicg.github.io/webpackage/draft-yasskin-httpbis-origin-signed-exchanges-impl.html#rfc.section.3.1
    '''
    #: Signed exchange signature label.
    label: str

    #: The hex string of signed exchange signature.
    signature: str

    #: Signed exchange signature integrity.
    integrity: str

    #: Signed exchange signature validity Url.
    validity_url: str

    #: Signed exchange signature date.
    date: int

    #: Signed exchange signature expires.
    expires: int

    #: Signed exchange signature cert Url.
    cert_url: typing.Optional[str] = None

    #: The hex string of signed exchange signature cert sha256.
    cert_sha256: typing.Optional[str] = None

    #: The encoded certificates.
    certificates: typing.Optional[typing.List[str]] = None

    def to_json(self):
        json = dict()
        json['label'] = self.label
        json['signature'] = self.signature
        json['integrity'] = self.integrity
        json['validityUrl'] = self.validity_url
        json['date'] = self.date
        json['expires'] = self.expires
        if self.cert_url is not None:
            json['certUrl'] = self.cert_url
        if self.cert_sha256 is not None:
            json['certSha256'] = self.cert_sha256
        if self.certificates is not None:
            json['certificates'] = [i for i in self.certificates]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            label=str(json['label']),
            signature=str(json['signature']),
            integrity=str(json['integrity']),
            validity_url=str(json['validityUrl']),
            date=int(json['date']),
            expires=int(json['expires']),
            cert_url=str(json['certUrl']) if 'certUrl' in json else None,
            cert_sha256=str(json['certSha256']) if 'certSha256' in json else None,
            certificates=[str(i) for i in json['certificates']] if 'certificates' in json else None,
        )


@dataclass
class SignedExchangeHeader:
    '''
    Information about a signed exchange header.
    https://wicg.github.io/webpackage/draft-yasskin-httpbis-origin-signed-exchanges-impl.html#cbor-representation
    '''
    #: Signed exchange request URL.
    request_url: str

    #: Signed exchange response code.
    response_code: int

    #: Signed exchange response headers.
    response_headers: Headers

    #: Signed exchange response signature.
    signatures: typing.List[SignedExchangeSignature]

    #: Signed exchange header integrity hash in the form of ``sha256-<base64-hash-value>``.
    header_integrity: str

    def to_json(self):
        json = dict()
        json['requestUrl'] = self.request_url
        json['responseCode'] = self.response_code
        json['responseHeaders'] = self.response_headers.to_json()
        json['signatures'] = [i.to_json() for i in self.signatures]
        json['headerIntegrity'] = self.header_integrity
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            request_url=str(json['requestUrl']),
            response_code=int(json['responseCode']),
            response_headers=Headers.from_json(json['responseHeaders']),
            signatures=[SignedExchangeSignature.from_json(i) for i in json['signatures']],
            header_integrity=str(json['headerIntegrity']),
        )


class SignedExchangeErrorField(enum.Enum):
    '''
    Field type for a signed exchange related error.
    '''
    SIGNATURE_SIG = "signatureSig"
    SIGNATURE_INTEGRITY = "signatureIntegrity"
    SIGNATURE_CERT_URL = "signatureCertUrl"
    SIGNATURE_CERT_SHA256 = "signatureCertSha256"
    SIGNATURE_VALIDITY_URL = "signatureValidityUrl"
    SIGNATURE_TIMESTAMPS = "signatureTimestamps"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SignedExchangeError:
    '''
    Information about a signed exchange response.
    '''
    #: Error message.
    message: str

    #: The index of the signature which caused the error.
    signature_index: typing.Optional[int] = None

    #: The field which caused the error.
    error_field: typing.Optional[SignedExchangeErrorField] = None

    def to_json(self):
        json = dict()
        json['message'] = self.message
        if self.signature_index is not None:
            json['signatureIndex'] = self.signature_index
        if self.error_field is not None:
            json['errorField'] = self.error_field.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            message=str(json['message']),
            signature_index=int(json['signatureIndex']) if 'signatureIndex' in json else None,
            error_field=SignedExchangeErrorField.from_json(json['errorField']) if 'errorField' in json else None,
        )


@dataclass
class SignedExchangeInfo:
    '''
    Information about a signed exchange response.
    '''
    #: The outer response of signed HTTP exchange which was received from network.
    outer_response: Response

    #: Information about the signed exchange header.
    header: typing.Optional[SignedExchangeHeader] = None

    #: Security details for the signed exchange header.
    security_details: typing.Optional[SecurityDetails] = None

    #: Errors occurred while handling the signed exchange.
    errors: typing.Optional[typing.List[SignedExchangeError]] = None

    def to_json(self):
        json = dict()
        json['outerResponse'] = self.outer_response.to_json()
        if self.header is not None:
            json['header'] = self.header.to_json()
        if self.security_details is not None:
            json['securityDetails'] = self.security_details.to_json()
        if self.errors is not None:
            json['errors'] = [i.to_json() for i in self.errors]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            outer_response=Response.from_json(json['outerResponse']),
            header=SignedExchangeHeader.from_json(json['header']) if 'header' in json else None,
            security_details=SecurityDetails.from_json(json['securityDetails']) if 'securityDetails' in json else None,
            errors=[SignedExchangeError.from_json(i) for i in json['errors']] if 'errors' in json else None,
        )


class ContentEncoding(enum.Enum):
    '''
    List of content encodings supported by the backend.
    '''
    DEFLATE = "deflate"
    GZIP = "gzip"
    BR = "br"
    ZSTD = "zstd"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PrivateNetworkRequestPolicy(enum.Enum):
    ALLOW = "Allow"
    BLOCK_FROM_INSECURE_TO_MORE_PRIVATE = "BlockFromInsecureToMorePrivate"
    WARN_FROM_INSECURE_TO_MORE_PRIVATE = "WarnFromInsecureToMorePrivate"
    PREFLIGHT_BLOCK = "PreflightBlock"
    PREFLIGHT_WARN = "PreflightWarn"
    PERMISSION_BLOCK = "PermissionBlock"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class IPAddressSpace(enum.Enum):
    LOCAL = "Local"
    PRIVATE = "Private"
    PUBLIC = "Public"
    UNKNOWN = "Unknown"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ConnectTiming:
    #: Timing's requestTime is a baseline in seconds, while the other numbers are ticks in
    #: milliseconds relatively to this requestTime. Matches ResourceTiming's requestTime for
    #: the same request (but not for redirected requests).
    request_time: float

    def to_json(self):
        json = dict()
        json['requestTime'] = self.request_time
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            request_time=float(json['requestTime']),
        )


@dataclass
class ClientSecurityState:
    initiator_is_secure_context: bool

    initiator_ip_address_space: IPAddressSpace

    private_network_request_policy: PrivateNetworkRequestPolicy

    def to_json(self):
        json = dict()
        json['initiatorIsSecureContext'] = self.initiator_is_secure_context
        json['initiatorIPAddressSpace'] = self.initiator_ip_address_space.to_json()
        json['privateNetworkRequestPolicy'] = self.private_network_request_policy.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            initiator_is_secure_context=bool(json['initiatorIsSecureContext']),
            initiator_ip_address_space=IPAddressSpace.from_json(json['initiatorIPAddressSpace']),
            private_network_request_policy=PrivateNetworkRequestPolicy.from_json(json['privateNetworkRequestPolicy']),
        )


class CrossOriginOpenerPolicyValue(enum.Enum):
    SAME_ORIGIN = "SameOrigin"
    SAME_ORIGIN_ALLOW_POPUPS = "SameOriginAllowPopups"
    RESTRICT_PROPERTIES = "RestrictProperties"
    UNSAFE_NONE = "UnsafeNone"
    SAME_ORIGIN_PLUS_COEP = "SameOriginPlusCoep"
    RESTRICT_PROPERTIES_PLUS_COEP = "RestrictPropertiesPlusCoep"
    NOOPENER_ALLOW_POPUPS = "NoopenerAllowPopups"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CrossOriginOpenerPolicyStatus:
    value: CrossOriginOpenerPolicyValue

    report_only_value: CrossOriginOpenerPolicyValue

    reporting_endpoint: typing.Optional[str] = None

    report_only_reporting_endpoint: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['value'] = self.value.to_json()
        json['reportOnlyValue'] = self.report_only_value.to_json()
        if self.reporting_endpoint is not None:
            json['reportingEndpoint'] = self.reporting_endpoint
        if self.report_only_reporting_endpoint is not None:
            json['reportOnlyReportingEndpoint'] = self.report_only_reporting_endpoint
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=CrossOriginOpenerPolicyValue.from_json(json['value']),
            report_only_value=CrossOriginOpenerPolicyValue.from_json(json['reportOnlyValue']),
            reporting_endpoint=str(json['reportingEndpoint']) if 'reportingEndpoint' in json else None,
            report_only_reporting_endpoint=str(json['reportOnlyReportingEndpoint']) if 'reportOnlyReportingEndpoint' in json else None,
        )


class CrossOriginEmbedderPolicyValue(enum.Enum):
    NONE = "None"
    CREDENTIALLESS = "Credentialless"
    REQUIRE_CORP = "RequireCorp"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CrossOriginEmbedderPolicyStatus:
    value: CrossOriginEmbedderPolicyValue

    report_only_value: CrossOriginEmbedderPolicyValue

    reporting_endpoint: typing.Optional[str] = None

    report_only_reporting_endpoint: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['value'] = self.value.to_json()
        json['reportOnlyValue'] = self.report_only_value.to_json()
        if self.reporting_endpoint is not None:
            json['reportingEndpoint'] = self.reporting_endpoint
        if self.report_only_reporting_endpoint is not None:
            json['reportOnlyReportingEndpoint'] = self.report_only_reporting_endpoint
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=CrossOriginEmbedderPolicyValue.from_json(json['value']),
            report_only_value=CrossOriginEmbedderPolicyValue.from_json(json['reportOnlyValue']),
            reporting_endpoint=str(json['reportingEndpoint']) if 'reportingEndpoint' in json else None,
            report_only_reporting_endpoint=str(json['reportOnlyReportingEndpoint']) if 'reportOnlyReportingEndpoint' in json else None,
        )


class ContentSecurityPolicySource(enum.Enum):
    HTTP = "HTTP"
    META = "Meta"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ContentSecurityPolicyStatus:
    effective_directives: str

    is_enforced: bool

    source: ContentSecurityPolicySource

    def to_json(self):
        json = dict()
        json['effectiveDirectives'] = self.effective_directives
        json['isEnforced'] = self.is_enforced
        json['source'] = self.source.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            effective_directives=str(json['effectiveDirectives']),
            is_enforced=bool(json['isEnforced']),
            source=ContentSecurityPolicySource.from_json(json['source']),
        )


@dataclass
class SecurityIsolationStatus:
    coop: typing.Optional[CrossOriginOpenerPolicyStatus] = None

    coep: typing.Optional[CrossOriginEmbedderPolicyStatus] = None

    csp: typing.Optional[typing.List[ContentSecurityPolicyStatus]] = None

    def to_json(self):
        json = dict()
        if self.coop is not None:
            json['coop'] = self.coop.to_json()
        if self.coep is not None:
            json['coep'] = self.coep.to_json()
        if self.csp is not None:
            json['csp'] = [i.to_json() for i in self.csp]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            coop=CrossOriginOpenerPolicyStatus.from_json(json['coop']) if 'coop' in json else None,
            coep=CrossOriginEmbedderPolicyStatus.from_json(json['coep']) if 'coep' in json else None,
            csp=[ContentSecurityPolicyStatus.from_json(i) for i in json['csp']] if 'csp' in json else None,
        )


class ReportStatus(enum.Enum):
    '''
    The status of a Reporting API report.
    '''
    QUEUED = "Queued"
    PENDING = "Pending"
    MARKED_FOR_REMOVAL = "MarkedForRemoval"
    SUCCESS = "Success"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ReportId(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> ReportId:
        return cls(json)

    def __repr__(self):
        return 'ReportId({})'.format(super().__repr__())


@dataclass
class ReportingApiReport:
    '''
    An object representing a report generated by the Reporting API.
    '''
    id_: ReportId

    #: The URL of the document that triggered the report.
    initiator_url: str

    #: The name of the endpoint group that should be used to deliver the report.
    destination: str

    #: The type of the report (specifies the set of data that is contained in the report body).
    type_: str

    #: When the report was generated.
    timestamp: network.TimeSinceEpoch

    #: How many uploads deep the related request was.
    depth: int

    #: The number of delivery attempts made so far, not including an active attempt.
    completed_attempts: int

    body: dict

    status: ReportStatus

    def to_json(self):
        json = dict()
        json['id'] = self.id_.to_json()
        json['initiatorUrl'] = self.initiator_url
        json['destination'] = self.destination
        json['type'] = self.type_
        json['timestamp'] = self.timestamp.to_json()
        json['depth'] = self.depth
        json['completedAttempts'] = self.completed_attempts
        json['body'] = self.body
        json['status'] = self.status.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=ReportId.from_json(json['id']),
            initiator_url=str(json['initiatorUrl']),
            destination=str(json['destination']),
            type_=str(json['type']),
            timestamp=network.TimeSinceEpoch.from_json(json['timestamp']),
            depth=int(json['depth']),
            completed_attempts=int(json['completedAttempts']),
            body=dict(json['body']),
            status=ReportStatus.from_json(json['status']),
        )


@dataclass
class ReportingApiEndpoint:
    #: The URL of the endpoint to which reports may be delivered.
    url: str

    #: Name of the endpoint group.
    group_name: str

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['groupName'] = self.group_name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            group_name=str(json['groupName']),
        )


@dataclass
class LoadNetworkResourcePageResult:
    '''
    An object providing the result of a network resource load.
    '''
    success: bool

    #: Optional values used for error reporting.
    net_error: typing.Optional[float] = None

    net_error_name: typing.Optional[str] = None

    http_status_code: typing.Optional[float] = None

    #: If successful, one of the following two fields holds the result.
    stream: typing.Optional[io.StreamHandle] = None

    #: Response headers.
    headers: typing.Optional[network.Headers] = None

    def to_json(self):
        json = dict()
        json['success'] = self.success
        if self.net_error is not None:
            json['netError'] = self.net_error
        if self.net_error_name is not None:
            json['netErrorName'] = self.net_error_name
        if self.http_status_code is not None:
            json['httpStatusCode'] = self.http_status_code
        if self.stream is not None:
            json['stream'] = self.stream.to_json()
        if self.headers is not None:
            json['headers'] = self.headers.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            success=bool(json['success']),
            net_error=float(json['netError']) if 'netError' in json else None,
            net_error_name=str(json['netErrorName']) if 'netErrorName' in json else None,
            http_status_code=float(json['httpStatusCode']) if 'httpStatusCode' in json else None,
            stream=io.StreamHandle.from_json(json['stream']) if 'stream' in json else None,
            headers=network.Headers.from_json(json['headers']) if 'headers' in json else None,
        )


@dataclass
class LoadNetworkResourceOptions:
    '''
    An options object that may be extended later to better support CORS,
    CORB and streaming.
    '''
    disable_cache: bool

    include_credentials: bool

    def to_json(self):
        json = dict()
        json['disableCache'] = self.disable_cache
        json['includeCredentials'] = self.include_credentials
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            disable_cache=bool(json['disableCache']),
            include_credentials=bool(json['includeCredentials']),
        )


def set_accepted_encodings(
        encodings: typing.List[ContentEncoding]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets a list of content encodings that will be accepted. Empty list means no encoding is accepted.

    **EXPERIMENTAL**

    :param encodings: List of accepted content encodings.
    '''
    params: T_JSON_DICT = dict()
    params['encodings'] = [i.to_json() for i in encodings]
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setAcceptedEncodings',
        'params': params,
    }
    json = yield cmd_dict


def clear_accepted_encodings_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears accepted encodings set by setAcceptedEncodings

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.clearAcceptedEncodingsOverride',
    }
    json = yield cmd_dict


def can_clear_browser_cache() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Tells whether clearing browser cache is supported.

    :returns: True if browser cache can be cleared.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.canClearBrowserCache',
    }
    json = yield cmd_dict
    return bool(json['result'])


def can_clear_browser_cookies() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Tells whether clearing browser cookies is supported.

    :returns: True if browser cookies can be cleared.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.canClearBrowserCookies',
    }
    json = yield cmd_dict
    return bool(json['result'])


def can_emulate_network_conditions() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Tells whether emulation of network conditions is supported.

    :returns: True if emulation of network conditions is supported.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.canEmulateNetworkConditions',
    }
    json = yield cmd_dict
    return bool(json['result'])


def clear_browser_cache() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears browser cache.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.clearBrowserCache',
    }
    json = yield cmd_dict


def clear_browser_cookies() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears browser cookies.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.clearBrowserCookies',
    }
    json = yield cmd_dict


def continue_intercepted_request(
        interception_id: InterceptionId,
        error_reason: typing.Optional[ErrorReason] = None,
        raw_response: typing.Optional[str] = None,
        url: typing.Optional[str] = None,
        method: typing.Optional[str] = None,
        post_data: typing.Optional[str] = None,
        headers: typing.Optional[Headers] = None,
        auth_challenge_response: typing.Optional[AuthChallengeResponse] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Response to Network.requestIntercepted which either modifies the request to continue with any
    modifications, or blocks it, or completes it with the provided response bytes. If a network
    fetch occurs as a result which encounters a redirect an additional Network.requestIntercepted
    event will be sent with the same InterceptionId.
    Deprecated, use Fetch.continueRequest, Fetch.fulfillRequest and Fetch.failRequest instead.

    **EXPERIMENTAL**

    :param interception_id:
    :param error_reason: *(Optional)* If set this causes the request to fail with the given reason. Passing ```Aborted```` for requests marked with ````isNavigationRequest``` also cancels the navigation. Must not be set in response to an authChallenge.
    :param raw_response: *(Optional)* If set the requests completes using with the provided base64 encoded raw response, including HTTP status line and headers etc... Must not be set in response to an authChallenge.
    :param url: *(Optional)* If set the request url will be modified in a way that's not observable by page. Must not be set in response to an authChallenge.
    :param method: *(Optional)* If set this allows the request method to be overridden. Must not be set in response to an authChallenge.
    :param post_data: *(Optional)* If set this allows postData to be set. Must not be set in response to an authChallenge.
    :param headers: *(Optional)* If set this allows the request headers to be changed. Must not be set in response to an authChallenge.
    :param auth_challenge_response: *(Optional)* Response to a requestIntercepted with an authChallenge. Must not be set otherwise.
    '''
    params: T_JSON_DICT = dict()
    params['interceptionId'] = interception_id.to_json()
    if error_reason is not None:
        params['errorReason'] = error_reason.to_json()
    if raw_response is not None:
        params['rawResponse'] = raw_response
    if url is not None:
        params['url'] = url
    if method is not None:
        params['method'] = method
    if post_data is not None:
        params['postData'] = post_data
    if headers is not None:
        params['headers'] = headers.to_json()
    if auth_challenge_response is not None:
        params['authChallengeResponse'] = auth_challenge_response.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.continueInterceptedRequest',
        'params': params,
    }
    json = yield cmd_dict


def delete_cookies(
        name: str,
        url: typing.Optional[str] = None,
        domain: typing.Optional[str] = None,
        path: typing.Optional[str] = None,
        partition_key: typing.Optional[CookiePartitionKey] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes browser cookies with matching name and url or domain/path/partitionKey pair.

    :param name: Name of the cookies to remove.
    :param url: *(Optional)* If specified, deletes all the cookies with the given name where domain and path match provided URL.
    :param domain: *(Optional)* If specified, deletes only cookies with the exact domain.
    :param path: *(Optional)* If specified, deletes only cookies with the exact path.
    :param partition_key: **(EXPERIMENTAL)** *(Optional)* If specified, deletes only cookies with the the given name and partitionKey where all partition key attributes match the cookie partition key attribute.
    '''
    params: T_JSON_DICT = dict()
    params['name'] = name
    if url is not None:
        params['url'] = url
    if domain is not None:
        params['domain'] = domain
    if path is not None:
        params['path'] = path
    if partition_key is not None:
        params['partitionKey'] = partition_key.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.deleteCookies',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables network tracking, prevents network events from being sent to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.disable',
    }
    json = yield cmd_dict


def emulate_network_conditions(
        offline: bool,
        latency: float,
        download_throughput: float,
        upload_throughput: float,
        connection_type: typing.Optional[ConnectionType] = None,
        packet_loss: typing.Optional[float] = None,
        packet_queue_length: typing.Optional[int] = None,
        packet_reordering: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Activates emulation of network conditions.

    :param offline: True to emulate internet disconnection.
    :param latency: Minimum latency from request sent to response headers received (ms).
    :param download_throughput: Maximal aggregated download throughput (bytes/sec). -1 disables download throttling.
    :param upload_throughput: Maximal aggregated upload throughput (bytes/sec).  -1 disables upload throttling.
    :param connection_type: *(Optional)* Connection type if known.
    :param packet_loss: **(EXPERIMENTAL)** *(Optional)* WebRTC packet loss (percent, 0-100). 0 disables packet loss emulation, 100 drops all the packets.
    :param packet_queue_length: **(EXPERIMENTAL)** *(Optional)* WebRTC packet queue length (packet). 0 removes any queue length limitations.
    :param packet_reordering: **(EXPERIMENTAL)** *(Optional)* WebRTC packetReordering feature.
    '''
    params: T_JSON_DICT = dict()
    params['offline'] = offline
    params['latency'] = latency
    params['downloadThroughput'] = download_throughput
    params['uploadThroughput'] = upload_throughput
    if connection_type is not None:
        params['connectionType'] = connection_type.to_json()
    if packet_loss is not None:
        params['packetLoss'] = packet_loss
    if packet_queue_length is not None:
        params['packetQueueLength'] = packet_queue_length
    if packet_reordering is not None:
        params['packetReordering'] = packet_reordering
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.emulateNetworkConditions',
        'params': params,
    }
    json = yield cmd_dict


def enable(
        max_total_buffer_size: typing.Optional[int] = None,
        max_resource_buffer_size: typing.Optional[int] = None,
        max_post_data_size: typing.Optional[int] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables network tracking, network events will now be delivered to the client.

    :param max_total_buffer_size: **(EXPERIMENTAL)** *(Optional)* Buffer size in bytes to use when preserving network payloads (XHRs, etc).
    :param max_resource_buffer_size: **(EXPERIMENTAL)** *(Optional)* Per-resource buffer size in bytes to use when preserving network payloads (XHRs, etc).
    :param max_post_data_size: *(Optional)* Longest post body size (in bytes) that would be included in requestWillBeSent notification
    '''
    params: T_JSON_DICT = dict()
    if max_total_buffer_size is not None:
        params['maxTotalBufferSize'] = max_total_buffer_size
    if max_resource_buffer_size is not None:
        params['maxResourceBufferSize'] = max_resource_buffer_size
    if max_post_data_size is not None:
        params['maxPostDataSize'] = max_post_data_size
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.enable',
        'params': params,
    }
    json = yield cmd_dict


def get_all_cookies() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Cookie]]:
    '''
    Returns all browser cookies. Depending on the backend support, will return detailed cookie
    information in the ``cookies`` field.
    Deprecated. Use Storage.getCookies instead.

    :returns: Array of cookie objects.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getAllCookies',
    }
    json = yield cmd_dict
    return [Cookie.from_json(i) for i in json['cookies']]


def get_certificate(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Returns the DER-encoded certificate.

    **EXPERIMENTAL**

    :param origin: Origin to get certificate for.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getCertificate',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['tableNames']]


def get_cookies(
        urls: typing.Optional[typing.List[str]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Cookie]]:
    '''
    Returns all browser cookies for the current URL. Depending on the backend support, will return
    detailed cookie information in the ``cookies`` field.

    :param urls: *(Optional)* The list of URLs for which applicable cookies will be fetched. If not specified, it's assumed to be set to the list containing the URLs of the page and all of its subframes.
    :returns: Array of cookie objects.
    '''
    params: T_JSON_DICT = dict()
    if urls is not None:
        params['urls'] = [i for i in urls]
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getCookies',
        'params': params,
    }
    json = yield cmd_dict
    return [Cookie.from_json(i) for i in json['cookies']]


def get_response_body(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, bool]]:
    '''
    Returns content served for the given request.

    :param request_id: Identifier of the network request to get content for.
    :returns: A tuple with the following items:

        0. **body** - Response body.
        1. **base64Encoded** - True, if content was sent as base64.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getResponseBody',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['body']),
        bool(json['base64Encoded'])
    )


def get_request_post_data(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Returns post data sent with the request. Returns an error when no data was sent with the request.

    :param request_id: Identifier of the network request to get content for.
    :returns: Request body string, omitting files from multipart requests
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getRequestPostData',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['postData'])


def get_response_body_for_interception(
        interception_id: InterceptionId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, bool]]:
    '''
    Returns content served for the given currently intercepted request.

    **EXPERIMENTAL**

    :param interception_id: Identifier for the intercepted request to get body for.
    :returns: A tuple with the following items:

        0. **body** - Response body.
        1. **base64Encoded** - True, if content was sent as base64.
    '''
    params: T_JSON_DICT = dict()
    params['interceptionId'] = interception_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getResponseBodyForInterception',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['body']),
        bool(json['base64Encoded'])
    )


def take_response_body_for_interception_as_stream(
        interception_id: InterceptionId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,io.StreamHandle]:
    '''
    Returns a handle to the stream representing the response body. Note that after this command,
    the intercepted request can't be continued as is -- you either need to cancel it or to provide
    the response body. The stream only supports sequential read, IO.read will fail if the position
    is specified.

    **EXPERIMENTAL**

    :param interception_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['interceptionId'] = interception_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.takeResponseBodyForInterceptionAsStream',
        'params': params,
    }
    json = yield cmd_dict
    return io.StreamHandle.from_json(json['stream'])


def replay_xhr(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    This method sends a new XMLHttpRequest which is identical to the original one. The following
    parameters should be identical: method, url, async, request body, extra headers, withCredentials
    attribute, user, password.

    **EXPERIMENTAL**

    :param request_id: Identifier of XHR to replay.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.replayXHR',
        'params': params,
    }
    json = yield cmd_dict


def search_in_response_body(
        request_id: RequestId,
        query: str,
        case_sensitive: typing.Optional[bool] = None,
        is_regex: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[debugger.SearchMatch]]:
    '''
    Searches for given string in response content.

    **EXPERIMENTAL**

    :param request_id: Identifier of the network response to search.
    :param query: String to search for.
    :param case_sensitive: *(Optional)* If true, search is case sensitive.
    :param is_regex: *(Optional)* If true, treats string parameter as regex.
    :returns: List of search matches.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['query'] = query
    if case_sensitive is not None:
        params['caseSensitive'] = case_sensitive
    if is_regex is not None:
        params['isRegex'] = is_regex
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.searchInResponseBody',
        'params': params,
    }
    json = yield cmd_dict
    return [debugger.SearchMatch.from_json(i) for i in json['result']]


def set_blocked_ur_ls(
        urls: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Blocks URLs from loading.

    **EXPERIMENTAL**

    :param urls: URL patterns to block. Wildcards ('*') are allowed.
    '''
    params: T_JSON_DICT = dict()
    params['urls'] = [i for i in urls]
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setBlockedURLs',
        'params': params,
    }
    json = yield cmd_dict


def set_bypass_service_worker(
        bypass: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Toggles ignoring of service worker for each request.

    :param bypass: Bypass service worker and load from network.
    '''
    params: T_JSON_DICT = dict()
    params['bypass'] = bypass
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setBypassServiceWorker',
        'params': params,
    }
    json = yield cmd_dict


def set_cache_disabled(
        cache_disabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Toggles ignoring cache for each request. If ``true``, cache will not be used.

    :param cache_disabled: Cache disabled state.
    '''
    params: T_JSON_DICT = dict()
    params['cacheDisabled'] = cache_disabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setCacheDisabled',
        'params': params,
    }
    json = yield cmd_dict


def set_cookie(
        name: str,
        value: str,
        url: typing.Optional[str] = None,
        domain: typing.Optional[str] = None,
        path: typing.Optional[str] = None,
        secure: typing.Optional[bool] = None,
        http_only: typing.Optional[bool] = None,
        same_site: typing.Optional[CookieSameSite] = None,
        expires: typing.Optional[TimeSinceEpoch] = None,
        priority: typing.Optional[CookiePriority] = None,
        same_party: typing.Optional[bool] = None,
        source_scheme: typing.Optional[CookieSourceScheme] = None,
        source_port: typing.Optional[int] = None,
        partition_key: typing.Optional[CookiePartitionKey] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Sets a cookie with the given cookie data; may overwrite equivalent cookies if they exist.

    :param name: Cookie name.
    :param value: Cookie value.
    :param url: *(Optional)* The request-URI to associate with the setting of the cookie. This value can affect the default domain, path, source port, and source scheme values of the created cookie.
    :param domain: *(Optional)* Cookie domain.
    :param path: *(Optional)* Cookie path.
    :param secure: *(Optional)* True if cookie is secure.
    :param http_only: *(Optional)* True if cookie is http-only.
    :param same_site: *(Optional)* Cookie SameSite type.
    :param expires: *(Optional)* Cookie expiration date, session cookie if not set
    :param priority: **(EXPERIMENTAL)** *(Optional)* Cookie Priority type.
    :param same_party: **(EXPERIMENTAL)** *(Optional)* True if cookie is SameParty.
    :param source_scheme: **(EXPERIMENTAL)** *(Optional)* Cookie source scheme type.
    :param source_port: **(EXPERIMENTAL)** *(Optional)* Cookie source port. Valid values are {-1, [1, 65535]}, -1 indicates an unspecified port. An unspecified port value allows protocol clients to emulate legacy cookie scope for the port. This is a temporary ability and it will be removed in the future.
    :param partition_key: **(EXPERIMENTAL)** *(Optional)* Cookie partition key. If not set, the cookie will be set as not partitioned.
    :returns: Always set to true. If an error occurs, the response indicates protocol error.
    '''
    params: T_JSON_DICT = dict()
    params['name'] = name
    params['value'] = value
    if url is not None:
        params['url'] = url
    if domain is not None:
        params['domain'] = domain
    if path is not None:
        params['path'] = path
    if secure is not None:
        params['secure'] = secure
    if http_only is not None:
        params['httpOnly'] = http_only
    if same_site is not None:
        params['sameSite'] = same_site.to_json()
    if expires is not None:
        params['expires'] = expires.to_json()
    if priority is not None:
        params['priority'] = priority.to_json()
    if same_party is not None:
        params['sameParty'] = same_party
    if source_scheme is not None:
        params['sourceScheme'] = source_scheme.to_json()
    if source_port is not None:
        params['sourcePort'] = source_port
    if partition_key is not None:
        params['partitionKey'] = partition_key.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setCookie',
        'params': params,
    }
    json = yield cmd_dict
    return bool(json['success'])


def set_cookies(
        cookies: typing.List[CookieParam]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets given cookies.

    :param cookies: Cookies to be set.
    '''
    params: T_JSON_DICT = dict()
    params['cookies'] = [i.to_json() for i in cookies]
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setCookies',
        'params': params,
    }
    json = yield cmd_dict


def set_extra_http_headers(
        headers: Headers
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Specifies whether to always send extra HTTP headers with the requests from this page.

    :param headers: Map with extra HTTP headers.
    '''
    params: T_JSON_DICT = dict()
    params['headers'] = headers.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setExtraHTTPHeaders',
        'params': params,
    }
    json = yield cmd_dict


def set_attach_debug_stack(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Specifies whether to attach a page script stack id in requests

    **EXPERIMENTAL**

    :param enabled: Whether to attach a page script stack for debugging purpose.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setAttachDebugStack',
        'params': params,
    }
    json = yield cmd_dict


def set_request_interception(
        patterns: typing.List[RequestPattern]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets the requests to intercept that match the provided patterns and optionally resource types.
    Deprecated, please use Fetch.enable instead.

    **EXPERIMENTAL**

    :param patterns: Requests matching any of these patterns will be forwarded and wait for the corresponding continueInterceptedRequest call.
    '''
    params: T_JSON_DICT = dict()
    params['patterns'] = [i.to_json() for i in patterns]
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setRequestInterception',
        'params': params,
    }
    json = yield cmd_dict


def set_user_agent_override(
        user_agent: str,
        accept_language: typing.Optional[str] = None,
        platform: typing.Optional[str] = None,
        user_agent_metadata: typing.Optional[emulation.UserAgentMetadata] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Allows overriding user agent with the given string.

    :param user_agent: User agent to use.
    :param accept_language: *(Optional)* Browser language to emulate.
    :param platform: *(Optional)* The platform navigator.platform should return.
    :param user_agent_metadata: **(EXPERIMENTAL)** *(Optional)* To be sent in Sec-CH-UA-* headers and returned in navigator.userAgentData
    '''
    params: T_JSON_DICT = dict()
    params['userAgent'] = user_agent
    if accept_language is not None:
        params['acceptLanguage'] = accept_language
    if platform is not None:
        params['platform'] = platform
    if user_agent_metadata is not None:
        params['userAgentMetadata'] = user_agent_metadata.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setUserAgentOverride',
        'params': params,
    }
    json = yield cmd_dict


def stream_resource_content(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Enables streaming of the response for the given requestId.
    If enabled, the dataReceived event contains the data that was received during streaming.

    **EXPERIMENTAL**

    :param request_id: Identifier of the request to stream.
    :returns: Data that has been buffered until streaming is enabled.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.streamResourceContent',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['bufferedData'])


def get_security_isolation_status(
        frame_id: typing.Optional[page.FrameId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SecurityIsolationStatus]:
    '''
    Returns information about the COEP/COOP isolation status.

    **EXPERIMENTAL**

    :param frame_id: *(Optional)* If no frameId is provided, the status of the target is provided.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getSecurityIsolationStatus',
        'params': params,
    }
    json = yield cmd_dict
    return SecurityIsolationStatus.from_json(json['status'])


def enable_reporting_api(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables tracking for the Reporting API, events generated by the Reporting API will now be delivered to the client.
    Enabling triggers 'reportingApiReportAdded' for all existing reports.

    **EXPERIMENTAL**

    :param enable: Whether to enable or disable events for the Reporting API
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.enableReportingApi',
        'params': params,
    }
    json = yield cmd_dict


def load_network_resource(
        frame_id: typing.Optional[page.FrameId] = None,
        url: str = None,
        options: LoadNetworkResourceOptions = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,LoadNetworkResourcePageResult]:
    '''
    Fetches the resource and returns the content.

    **EXPERIMENTAL**

    :param frame_id: *(Optional)* Frame id to get the resource for. Mandatory for frame targets, and should be omitted for worker targets.
    :param url: URL of the resource to get content for.
    :param options: Options for the request.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    params['url'] = url
    params['options'] = options.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.loadNetworkResource',
        'params': params,
    }
    json = yield cmd_dict
    return LoadNetworkResourcePageResult.from_json(json['resource'])


def set_cookie_controls(
        enable_third_party_cookie_restriction: bool,
        disable_third_party_cookie_metadata: bool,
        disable_third_party_cookie_heuristics: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets Controls for third-party cookie access
    Page reload is required before the new cookie bahavior will be observed

    **EXPERIMENTAL**

    :param enable_third_party_cookie_restriction: Whether 3pc restriction is enabled.
    :param disable_third_party_cookie_metadata: Whether 3pc grace period exception should be enabled; false by default.
    :param disable_third_party_cookie_heuristics: Whether 3pc heuristics exceptions should be enabled; false by default.
    '''
    params: T_JSON_DICT = dict()
    params['enableThirdPartyCookieRestriction'] = enable_third_party_cookie_restriction
    params['disableThirdPartyCookieMetadata'] = disable_third_party_cookie_metadata
    params['disableThirdPartyCookieHeuristics'] = disable_third_party_cookie_heuristics
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setCookieControls',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Network.dataReceived')
@dataclass
class DataReceived:
    '''
    Fired when data chunk was received over the network.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: Data chunk length.
    data_length: int
    #: Actual bytes received (might be less than dataLength for compressed encodings).
    encoded_data_length: int
    #: Data that was received.
    data: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DataReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            data_length=int(json['dataLength']),
            encoded_data_length=int(json['encodedDataLength']),
            data=str(json['data']) if 'data' in json else None
        )


@event_class('Network.eventSourceMessageReceived')
@dataclass
class EventSourceMessageReceived:
    '''
    Fired when EventSource message is received.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: Message type.
    event_name: str
    #: Message identifier.
    event_id: str
    #: Message content.
    data: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> EventSourceMessageReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            event_name=str(json['eventName']),
            event_id=str(json['eventId']),
            data=str(json['data'])
        )


@event_class('Network.loadingFailed')
@dataclass
class LoadingFailed:
    '''
    Fired when HTTP request has failed to load.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: Resource type.
    type_: ResourceType
    #: Error message. List of network errors: https://cs.chromium.org/chromium/src/net/base/net_error_list.h
    error_text: str
    #: True if loading was canceled.
    canceled: typing.Optional[bool]
    #: The reason why loading was blocked, if any.
    blocked_reason: typing.Optional[BlockedReason]
    #: The reason why loading was blocked by CORS, if any.
    cors_error_status: typing.Optional[CorsErrorStatus]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LoadingFailed:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            type_=ResourceType.from_json(json['type']),
            error_text=str(json['errorText']),
            canceled=bool(json['canceled']) if 'canceled' in json else None,
            blocked_reason=BlockedReason.from_json(json['blockedReason']) if 'blockedReason' in json else None,
            cors_error_status=CorsErrorStatus.from_json(json['corsErrorStatus']) if 'corsErrorStatus' in json else None
        )


@event_class('Network.loadingFinished')
@dataclass
class LoadingFinished:
    '''
    Fired when HTTP request has finished loading.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: Total number of bytes received for this request.
    encoded_data_length: float

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LoadingFinished:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            encoded_data_length=float(json['encodedDataLength'])
        )


@event_class('Network.requestIntercepted')
@dataclass
class RequestIntercepted:
    '''
    **EXPERIMENTAL**

    Details of an intercepted HTTP request, which must be either allowed, blocked, modified or
    mocked.
    Deprecated, use Fetch.requestPaused instead.
    '''
    #: Each request the page makes will have a unique id, however if any redirects are encountered
    #: while processing that fetch, they will be reported with the same id as the original fetch.
    #: Likewise if HTTP authentication is needed then the same fetch id will be used.
    interception_id: InterceptionId
    request: Request
    #: The id of the frame that initiated the request.
    frame_id: page.FrameId
    #: How the requested resource will be used.
    resource_type: ResourceType
    #: Whether this is a navigation request, which can abort the navigation completely.
    is_navigation_request: bool
    #: Set if the request is a navigation that will result in a download.
    #: Only present after response is received from the server (i.e. HeadersReceived stage).
    is_download: typing.Optional[bool]
    #: Redirect location, only sent if a redirect was intercepted.
    redirect_url: typing.Optional[str]
    #: Details of the Authorization Challenge encountered. If this is set then
    #: continueInterceptedRequest must contain an authChallengeResponse.
    auth_challenge: typing.Optional[AuthChallenge]
    #: Response error if intercepted at response stage or if redirect occurred while intercepting
    #: request.
    response_error_reason: typing.Optional[ErrorReason]
    #: Response code if intercepted at response stage or if redirect occurred while intercepting
    #: request or auth retry occurred.
    response_status_code: typing.Optional[int]
    #: Response headers if intercepted at the response stage or if redirect occurred while
    #: intercepting request or auth retry occurred.
    response_headers: typing.Optional[Headers]
    #: If the intercepted request had a corresponding requestWillBeSent event fired for it, then
    #: this requestId will be the same as the requestId present in the requestWillBeSent event.
    request_id: typing.Optional[RequestId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RequestIntercepted:
        return cls(
            interception_id=InterceptionId.from_json(json['interceptionId']),
            request=Request.from_json(json['request']),
            frame_id=page.FrameId.from_json(json['frameId']),
            resource_type=ResourceType.from_json(json['resourceType']),
            is_navigation_request=bool(json['isNavigationRequest']),
            is_download=bool(json['isDownload']) if 'isDownload' in json else None,
            redirect_url=str(json['redirectUrl']) if 'redirectUrl' in json else None,
            auth_challenge=AuthChallenge.from_json(json['authChallenge']) if 'authChallenge' in json else None,
            response_error_reason=ErrorReason.from_json(json['responseErrorReason']) if 'responseErrorReason' in json else None,
            response_status_code=int(json['responseStatusCode']) if 'responseStatusCode' in json else None,
            response_headers=Headers.from_json(json['responseHeaders']) if 'responseHeaders' in json else None,
            request_id=RequestId.from_json(json['requestId']) if 'requestId' in json else None
        )


@event_class('Network.requestServedFromCache')
@dataclass
class RequestServedFromCache:
    '''
    Fired if request ended up loading from cache.
    '''
    #: Request identifier.
    request_id: RequestId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RequestServedFromCache:
        return cls(
            request_id=RequestId.from_json(json['requestId'])
        )


@event_class('Network.requestWillBeSent')
@dataclass
class RequestWillBeSent:
    '''
    Fired when page is about to send HTTP request.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Loader identifier. Empty string if the request is fetched from worker.
    loader_id: LoaderId
    #: URL of the document this request is loaded for.
    document_url: str
    #: Request data.
    request: Request
    #: Timestamp.
    timestamp: MonotonicTime
    #: Timestamp.
    wall_time: TimeSinceEpoch
    #: Request initiator.
    initiator: Initiator
    #: In the case that redirectResponse is populated, this flag indicates whether
    #: requestWillBeSentExtraInfo and responseReceivedExtraInfo events will be or were emitted
    #: for the request which was just redirected.
    redirect_has_extra_info: bool
    #: Redirect response data.
    redirect_response: typing.Optional[Response]
    #: Type of this resource.
    type_: typing.Optional[ResourceType]
    #: Frame identifier.
    frame_id: typing.Optional[page.FrameId]
    #: Whether the request is initiated by a user gesture. Defaults to false.
    has_user_gesture: typing.Optional[bool]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RequestWillBeSent:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            loader_id=LoaderId.from_json(json['loaderId']),
            document_url=str(json['documentURL']),
            request=Request.from_json(json['request']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            wall_time=TimeSinceEpoch.from_json(json['wallTime']),
            initiator=Initiator.from_json(json['initiator']),
            redirect_has_extra_info=bool(json['redirectHasExtraInfo']),
            redirect_response=Response.from_json(json['redirectResponse']) if 'redirectResponse' in json else None,
            type_=ResourceType.from_json(json['type']) if 'type' in json else None,
            frame_id=page.FrameId.from_json(json['frameId']) if 'frameId' in json else None,
            has_user_gesture=bool(json['hasUserGesture']) if 'hasUserGesture' in json else None
        )


@event_class('Network.resourceChangedPriority')
@dataclass
class ResourceChangedPriority:
    '''
    **EXPERIMENTAL**

    Fired when resource loading priority is changed
    '''
    #: Request identifier.
    request_id: RequestId
    #: New priority
    new_priority: ResourcePriority
    #: Timestamp.
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ResourceChangedPriority:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            new_priority=ResourcePriority.from_json(json['newPriority']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.signedExchangeReceived')
@dataclass
class SignedExchangeReceived:
    '''
    **EXPERIMENTAL**

    Fired when a signed exchange was received over the network
    '''
    #: Request identifier.
    request_id: RequestId
    #: Information about the signed exchange response.
    info: SignedExchangeInfo

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SignedExchangeReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            info=SignedExchangeInfo.from_json(json['info'])
        )


@event_class('Network.responseReceived')
@dataclass
class ResponseReceived:
    '''
    Fired when HTTP response is available.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Loader identifier. Empty string if the request is fetched from worker.
    loader_id: LoaderId
    #: Timestamp.
    timestamp: MonotonicTime
    #: Resource type.
    type_: ResourceType
    #: Response data.
    response: Response
    #: Indicates whether requestWillBeSentExtraInfo and responseReceivedExtraInfo events will be
    #: or were emitted for this request.
    has_extra_info: bool
    #: Frame identifier.
    frame_id: typing.Optional[page.FrameId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ResponseReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            loader_id=LoaderId.from_json(json['loaderId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            type_=ResourceType.from_json(json['type']),
            response=Response.from_json(json['response']),
            has_extra_info=bool(json['hasExtraInfo']),
            frame_id=page.FrameId.from_json(json['frameId']) if 'frameId' in json else None
        )


@event_class('Network.webSocketClosed')
@dataclass
class WebSocketClosed:
    '''
    Fired when WebSocket is closed.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketClosed:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.webSocketCreated')
@dataclass
class WebSocketCreated:
    '''
    Fired upon WebSocket creation.
    '''
    #: Request identifier.
    request_id: RequestId
    #: WebSocket request URL.
    url: str
    #: Request initiator.
    initiator: typing.Optional[Initiator]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketCreated:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            url=str(json['url']),
            initiator=Initiator.from_json(json['initiator']) if 'initiator' in json else None
        )


@event_class('Network.webSocketFrameError')
@dataclass
class WebSocketFrameError:
    '''
    Fired when WebSocket message error occurs.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: WebSocket error message.
    error_message: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketFrameError:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            error_message=str(json['errorMessage'])
        )


@event_class('Network.webSocketFrameReceived')
@dataclass
class WebSocketFrameReceived:
    '''
    Fired when WebSocket message is received.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: WebSocket response data.
    response: WebSocketFrame

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketFrameReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            response=WebSocketFrame.from_json(json['response'])
        )


@event_class('Network.webSocketFrameSent')
@dataclass
class WebSocketFrameSent:
    '''
    Fired when WebSocket message is sent.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: WebSocket response data.
    response: WebSocketFrame

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketFrameSent:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            response=WebSocketFrame.from_json(json['response'])
        )


@event_class('Network.webSocketHandshakeResponseReceived')
@dataclass
class WebSocketHandshakeResponseReceived:
    '''
    Fired when WebSocket handshake response becomes available.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: WebSocket response data.
    response: WebSocketResponse

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketHandshakeResponseReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            response=WebSocketResponse.from_json(json['response'])
        )


@event_class('Network.webSocketWillSendHandshakeRequest')
@dataclass
class WebSocketWillSendHandshakeRequest:
    '''
    Fired when WebSocket is about to initiate handshake.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: UTC Timestamp.
    wall_time: TimeSinceEpoch
    #: WebSocket request data.
    request: WebSocketRequest

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketWillSendHandshakeRequest:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            wall_time=TimeSinceEpoch.from_json(json['wallTime']),
            request=WebSocketRequest.from_json(json['request'])
        )


@event_class('Network.webTransportCreated')
@dataclass
class WebTransportCreated:
    '''
    Fired upon WebTransport creation.
    '''
    #: WebTransport identifier.
    transport_id: RequestId
    #: WebTransport request URL.
    url: str
    #: Timestamp.
    timestamp: MonotonicTime
    #: Request initiator.
    initiator: typing.Optional[Initiator]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebTransportCreated:
        return cls(
            transport_id=RequestId.from_json(json['transportId']),
            url=str(json['url']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            initiator=Initiator.from_json(json['initiator']) if 'initiator' in json else None
        )


@event_class('Network.webTransportConnectionEstablished')
@dataclass
class WebTransportConnectionEstablished:
    '''
    Fired when WebTransport handshake is finished.
    '''
    #: WebTransport identifier.
    transport_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebTransportConnectionEstablished:
        return cls(
            transport_id=RequestId.from_json(json['transportId']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.webTransportClosed')
@dataclass
class WebTransportClosed:
    '''
    Fired when WebTransport is disposed.
    '''
    #: WebTransport identifier.
    transport_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebTransportClosed:
        return cls(
            transport_id=RequestId.from_json(json['transportId']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.requestWillBeSentExtraInfo')
@dataclass
class RequestWillBeSentExtraInfo:
    '''
    **EXPERIMENTAL**

    Fired when additional information about a requestWillBeSent event is available from the
    network stack. Not every requestWillBeSent event will have an additional
    requestWillBeSentExtraInfo fired for it, and there is no guarantee whether requestWillBeSent
    or requestWillBeSentExtraInfo will be fired first for the same request.
    '''
    #: Request identifier. Used to match this information to an existing requestWillBeSent event.
    request_id: RequestId
    #: A list of cookies potentially associated to the requested URL. This includes both cookies sent with
    #: the request and the ones not sent; the latter are distinguished by having blockedReasons field set.
    associated_cookies: typing.List[AssociatedCookie]
    #: Raw request headers as they will be sent over the wire.
    headers: Headers
    #: Connection timing information for the request.
    connect_timing: ConnectTiming
    #: The client security state set for the request.
    client_security_state: typing.Optional[ClientSecurityState]
    #: Whether the site has partitioned cookies stored in a partition different than the current one.
    site_has_cookie_in_other_partition: typing.Optional[bool]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RequestWillBeSentExtraInfo:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            associated_cookies=[AssociatedCookie.from_json(i) for i in json['associatedCookies']],
            headers=Headers.from_json(json['headers']),
            connect_timing=ConnectTiming.from_json(json['connectTiming']),
            client_security_state=ClientSecurityState.from_json(json['clientSecurityState']) if 'clientSecurityState' in json else None,
            site_has_cookie_in_other_partition=bool(json['siteHasCookieInOtherPartition']) if 'siteHasCookieInOtherPartition' in json else None
        )


@event_class('Network.responseReceivedExtraInfo')
@dataclass
class ResponseReceivedExtraInfo:
    '''
    **EXPERIMENTAL**

    Fired when additional information about a responseReceived event is available from the network
    stack. Not every responseReceived event will have an additional responseReceivedExtraInfo for
    it, and responseReceivedExtraInfo may be fired before or after responseReceived.
    '''
    #: Request identifier. Used to match this information to another responseReceived event.
    request_id: RequestId
    #: A list of cookies which were not stored from the response along with the corresponding
    #: reasons for blocking. The cookies here may not be valid due to syntax errors, which
    #: are represented by the invalid cookie line string instead of a proper cookie.
    blocked_cookies: typing.List[BlockedSetCookieWithReason]
    #: Raw response headers as they were received over the wire.
    #: Duplicate headers in the response are represented as a single key with their values
    #: concatentated using ``\n`` as the separator.
    #: See also ``headersText`` that contains verbatim text for HTTP/1.*.
    headers: Headers
    #: The IP address space of the resource. The address space can only be determined once the transport
    #: established the connection, so we can't send it in ``requestWillBeSentExtraInfo``.
    resource_ip_address_space: IPAddressSpace
    #: The status code of the response. This is useful in cases the request failed and no responseReceived
    #: event is triggered, which is the case for, e.g., CORS errors. This is also the correct status code
    #: for cached requests, where the status in responseReceived is a 200 and this will be 304.
    status_code: int
    #: Raw response header text as it was received over the wire. The raw text may not always be
    #: available, such as in the case of HTTP/2 or QUIC.
    headers_text: typing.Optional[str]
    #: The cookie partition key that will be used to store partitioned cookies set in this response.
    #: Only sent when partitioned cookies are enabled.
    cookie_partition_key: typing.Optional[CookiePartitionKey]
    #: True if partitioned cookies are enabled, but the partition key is not serializable to string.
    cookie_partition_key_opaque: typing.Optional[bool]
    #: A list of cookies which should have been blocked by 3PCD but are exempted and stored from
    #: the response with the corresponding reason.
    exempted_cookies: typing.Optional[typing.List[ExemptedSetCookieWithReason]]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ResponseReceivedExtraInfo:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            blocked_cookies=[BlockedSetCookieWithReason.from_json(i) for i in json['blockedCookies']],
            headers=Headers.from_json(json['headers']),
            resource_ip_address_space=IPAddressSpace.from_json(json['resourceIPAddressSpace']),
            status_code=int(json['statusCode']),
            headers_text=str(json['headersText']) if 'headersText' in json else None,
            cookie_partition_key=CookiePartitionKey.from_json(json['cookiePartitionKey']) if 'cookiePartitionKey' in json else None,
            cookie_partition_key_opaque=bool(json['cookiePartitionKeyOpaque']) if 'cookiePartitionKeyOpaque' in json else None,
            exempted_cookies=[ExemptedSetCookieWithReason.from_json(i) for i in json['exemptedCookies']] if 'exemptedCookies' in json else None
        )


@event_class('Network.responseReceivedEarlyHints')
@dataclass
class ResponseReceivedEarlyHints:
    '''
    **EXPERIMENTAL**

    Fired when 103 Early Hints headers is received in addition to the common response.
    Not every responseReceived event will have an responseReceivedEarlyHints fired.
    Only one responseReceivedEarlyHints may be fired for eached responseReceived event.
    '''
    #: Request identifier. Used to match this information to another responseReceived event.
    request_id: RequestId
    #: Raw response headers as they were received over the wire.
    #: Duplicate headers in the response are represented as a single key with their values
    #: concatentated using ``\n`` as the separator.
    #: See also ``headersText`` that contains verbatim text for HTTP/1.*.
    headers: Headers

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ResponseReceivedEarlyHints:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            headers=Headers.from_json(json['headers'])
        )


@event_class('Network.trustTokenOperationDone')
@dataclass
class TrustTokenOperationDone:
    '''
    **EXPERIMENTAL**

    Fired exactly once for each Trust Token operation. Depending on
    the type of the operation and whether the operation succeeded or
    failed, the event is fired before the corresponding request was sent
    or after the response was received.
    '''
    #: Detailed success or error status of the operation.
    #: 'AlreadyExists' also signifies a successful operation, as the result
    #: of the operation already exists und thus, the operation was abort
    #: preemptively (e.g. a cache hit).
    status: str
    type_: TrustTokenOperationType
    request_id: RequestId
    #: Top level origin. The context in which the operation was attempted.
    top_level_origin: typing.Optional[str]
    #: Origin of the issuer in case of a "Issuance" or "Redemption" operation.
    issuer_origin: typing.Optional[str]
    #: The number of obtained Trust Tokens on a successful "Issuance" operation.
    issued_token_count: typing.Optional[int]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TrustTokenOperationDone:
        return cls(
            status=str(json['status']),
            type_=TrustTokenOperationType.from_json(json['type']),
            request_id=RequestId.from_json(json['requestId']),
            top_level_origin=str(json['topLevelOrigin']) if 'topLevelOrigin' in json else None,
            issuer_origin=str(json['issuerOrigin']) if 'issuerOrigin' in json else None,
            issued_token_count=int(json['issuedTokenCount']) if 'issuedTokenCount' in json else None
        )


@event_class('Network.policyUpdated')
@dataclass
class PolicyUpdated:
    '''
    **EXPERIMENTAL**

    Fired once security policy has been updated.
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PolicyUpdated:
        return cls(

        )


@event_class('Network.subresourceWebBundleMetadataReceived')
@dataclass
class SubresourceWebBundleMetadataReceived:
    '''
    **EXPERIMENTAL**

    Fired once when parsing the .wbn file has succeeded.
    The event contains the information about the web bundle contents.
    '''
    #: Request identifier. Used to match this information to another event.
    request_id: RequestId
    #: A list of URLs of resources in the subresource Web Bundle.
    urls: typing.List[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SubresourceWebBundleMetadataReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            urls=[str(i) for i in json['urls']]
        )


@event_class('Network.subresourceWebBundleMetadataError')
@dataclass
class SubresourceWebBundleMetadataError:
    '''
    **EXPERIMENTAL**

    Fired once when parsing the .wbn file has failed.
    '''
    #: Request identifier. Used to match this information to another event.
    request_id: RequestId
    #: Error message
    error_message: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SubresourceWebBundleMetadataError:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            error_message=str(json['errorMessage'])
        )


@event_class('Network.subresourceWebBundleInnerResponseParsed')
@dataclass
class SubresourceWebBundleInnerResponseParsed:
    '''
    **EXPERIMENTAL**

    Fired when handling requests for resources within a .wbn file.
    Note: this will only be fired for resources that are requested by the webpage.
    '''
    #: Request identifier of the subresource request
    inner_request_id: RequestId
    #: URL of the subresource resource.
    inner_request_url: str
    #: Bundle request identifier. Used to match this information to another event.
    #: This made be absent in case when the instrumentation was enabled only
    #: after webbundle was parsed.
    bundle_request_id: typing.Optional[RequestId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SubresourceWebBundleInnerResponseParsed:
        return cls(
            inner_request_id=RequestId.from_json(json['innerRequestId']),
            inner_request_url=str(json['innerRequestURL']),
            bundle_request_id=RequestId.from_json(json['bundleRequestId']) if 'bundleRequestId' in json else None
        )


@event_class('Network.subresourceWebBundleInnerResponseError')
@dataclass
class SubresourceWebBundleInnerResponseError:
    '''
    **EXPERIMENTAL**

    Fired when request for resources within a .wbn file failed.
    '''
    #: Request identifier of the subresource request
    inner_request_id: RequestId
    #: URL of the subresource resource.
    inner_request_url: str
    #: Error message
    error_message: str
    #: Bundle request identifier. Used to match this information to another event.
    #: This made be absent in case when the instrumentation was enabled only
    #: after webbundle was parsed.
    bundle_request_id: typing.Optional[RequestId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SubresourceWebBundleInnerResponseError:
        return cls(
            inner_request_id=RequestId.from_json(json['innerRequestId']),
            inner_request_url=str(json['innerRequestURL']),
            error_message=str(json['errorMessage']),
            bundle_request_id=RequestId.from_json(json['bundleRequestId']) if 'bundleRequestId' in json else None
        )


@event_class('Network.reportingApiReportAdded')
@dataclass
class ReportingApiReportAdded:
    '''
    **EXPERIMENTAL**

    Is sent whenever a new report is added.
    And after 'enableReportingApi' for all existing reports.
    '''
    report: ReportingApiReport

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ReportingApiReportAdded:
        return cls(
            report=ReportingApiReport.from_json(json['report'])
        )


@event_class('Network.reportingApiReportUpdated')
@dataclass
class ReportingApiReportUpdated:
    '''
    **EXPERIMENTAL**


    '''
    report: ReportingApiReport

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ReportingApiReportUpdated:
        return cls(
            report=ReportingApiReport.from_json(json['report'])
        )


@event_class('Network.reportingApiEndpointsChangedForOrigin')
@dataclass
class ReportingApiEndpointsChangedForOrigin:
    '''
    **EXPERIMENTAL**


    '''
    #: Origin of the document(s) which configured the endpoints.
    origin: str
    endpoints: typing.List[ReportingApiEndpoint]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ReportingApiEndpointsChangedForOrigin:
        return cls(
            origin=str(json['origin']),
            endpoints=[ReportingApiEndpoint.from_json(i) for i in json['endpoints']]
        )

# === NexusCore/openenv\Lib\site-packages\win32\lib\pywintypes.py ===
# Magic utility that "redirects" to pywintypesXX.dll
import importlib.machinery
import importlib.util
import os
import sys


def __import_pywin32_system_module__(modname, globs):
    # This has been through a number of iterations.  The problem: how to
    # locate pywintypesXX.dll when it may be in a number of places, and how
    # to avoid ever loading it twice.  This problem is compounded by the
    # fact that the "right" way to do this requires win32api, but this
    # itself requires pywintypesXX.
    # And the killer problem is that someone may have done 'import win32api'
    # before this code is called.  In that case Windows will have already
    # loaded pywintypesXX as part of loading win32api - but by the time
    # we get here, we may locate a different one.  This appears to work, but
    # then starts raising bizarre TypeErrors complaining that something
    # is not a pywintypes type when it clearly is!

    # So in what we hope is the last major iteration of this, we now
    # rely on a _win32sysloader module, implemented in C but not relying
    # on pywintypesXX.dll.  It then can check if the DLL we are looking for
    # lib is already loaded.
    # See if this is a debug build.
    suffix = "_d" if "_d.pyd" in importlib.machinery.EXTENSION_SUFFIXES else ""
    filename = "%s%d%d%s.dll" % (
        modname,
        sys.version_info.major,
        sys.version_info.minor,
        suffix,
    )
    if hasattr(sys, "frozen"):
        # If we are running from a frozen program (py2exe, McMillan, freeze, PyInstaller)
        # then we try and load the DLL from our sys.path
        # XXX - This path may also benefit from _win32sysloader?  However,
        # MarkH has never seen the DLL load problem with py2exe programs...
        for look in sys.path:
            # If the sys.path entry is a (presumably) .zip file, use the
            # directory
            if os.path.isfile(look):
                look = os.path.dirname(look)
            found = os.path.join(look, filename)
            if os.path.isfile(found):
                break
        else:
            raise ImportError(f"Module '{modname}' isn't in frozen sys.path {sys.path}")
    else:
        # First see if it already in our process - if so, we must use that.
        import _win32sysloader

        found = _win32sysloader.GetModuleFilename(filename)
        if found is None:
            # We ask Windows to load it next.  This is in an attempt to
            # get the exact same module loaded should pywintypes be imported
            # first (which is how we are here) or if, eg, win32api was imported
            # first thereby implicitly loading the DLL.

            # Sadly though, it doesn't quite work - if pywintypesXX.dll
            # is in system32 *and* the executable's directory, on XP SP2, an
            # import of win32api will cause Windows to load pywintypes
            # from system32, where LoadLibrary for that name will
            # load the one in the exe's dir.
            # That shouldn't really matter though, so long as we only ever
            # get one loaded.
            found = _win32sysloader.LoadModule(filename)
        if found is None:
            # Windows can't find it - which although isn't relevent here,
            # means that we *must* be the first win32 import, as an attempt
            # to import win32api etc would fail when Windows attempts to
            # locate the DLL.
            # This is most likely to happen for "non-admin" installs, where
            # we can't put the files anywhere else on the global path.

            # If there is a version in our Python directory, use that
            if os.path.isfile(os.path.join(sys.prefix, filename)):
                found = os.path.join(sys.prefix, filename)
        if found is None:
            # Not in the Python directory?  Maybe we were installed via
            # easy_install...
            if os.path.isfile(os.path.join(os.path.dirname(__file__), filename)):
                found = os.path.join(os.path.dirname(__file__), filename)

        # There are 2 site-packages directories - one "global" and one "user".
        # We could be in either, or both (but with different versions!). Factors include
        # virtualenvs, post-install script being run or not, `pip install` flags, etc.

        # In a worst-case, it means, say 'python -c "import win32api"'
        # will not work but 'python -c "import pywintypes, win32api"' will,
        # but it's better than nothing.

        # We use the same logic as pywin32_bootstrap to find potential location for the dll
        # Simply import pywin32_system32 and look in the paths in pywin32_system32.__path__

        if found is None:
            import pywin32_system32

            for path in pywin32_system32.__path__:
                maybe = os.path.join(path, filename)
                if os.path.isfile(maybe):
                    found = maybe
                    break

        if found is None:
            # give up in disgust.
            raise ImportError(f"No system module '{modname}' ({filename})")
    # After importing the module, sys.modules is updated to the DLL we just
    # loaded - which isn't what we want. So we update sys.modules to refer to
    # this module, and update our globals from it.
    old_mod = sys.modules[modname]
    # Load the DLL.
    loader = importlib.machinery.ExtensionFileLoader(modname, found)
    spec = importlib.machinery.ModuleSpec(name=modname, loader=loader, origin=found)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Check the sys.modules[] behaviour we describe above is true...
    assert sys.modules[modname] is mod
    # as above - re-reset to the *old* module object then update globs.
    sys.modules[modname] = old_mod
    globs.update(mod.__dict__)


__import_pywin32_system_module__("pywintypes", globals())

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\inflect\__init__.py ===
"""
inflect: english language inflection
 - correctly generate plurals, ordinals, indefinite articles
 - convert numbers to words

Copyright (C) 2010 Paul Dyson

Based upon the Perl module
`Lingua::EN::Inflect <https://metacpan.org/pod/Lingua::EN::Inflect>`_.

methods:
    classical inflect
    plural plural_noun plural_verb plural_adj singular_noun no num a an
    compare compare_nouns compare_verbs compare_adjs
    present_participle
    ordinal
    number_to_words
    join
    defnoun defverb defadj defa defan

INFLECTIONS:
    classical inflect
    plural plural_noun plural_verb plural_adj singular_noun compare
    no num a an present_participle

PLURALS:
    classical inflect
    plural plural_noun plural_verb plural_adj singular_noun no num
    compare compare_nouns compare_verbs compare_adjs

COMPARISONS:
    classical
    compare compare_nouns compare_verbs compare_adjs

ARTICLES:
    classical inflect num a an

NUMERICAL:
    ordinal number_to_words

USER_DEFINED:
    defnoun defverb defadj defa defan

Exceptions:
 UnknownClassicalModeError
 BadNumValueError
 BadChunkingOptionError
 NumOutOfRangeError
 BadUserDefinedPatternError
 BadRcFileError
 BadGenderError

"""

from __future__ import annotations

import ast
import collections
import contextlib
import functools
import itertools
import re
from numbers import Number
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Match,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from more_itertools import windowed_complete
from typeguard import typechecked

from .compat.py38 import Annotated


class UnknownClassicalModeError(Exception):
    pass


class BadNumValueError(Exception):
    pass


class BadChunkingOptionError(Exception):
    pass


class NumOutOfRangeError(Exception):
    pass


class BadUserDefinedPatternError(Exception):
    pass


class BadRcFileError(Exception):
    pass


class BadGenderError(Exception):
    pass


def enclose(s: str) -> str:
    return f"(?:{s})"


def joinstem(cutpoint: Optional[int] = 0, words: Optional[Iterable[str]] = None) -> str:
    """
    Join stem of each word in words into a string for regex.

    Each word is truncated at cutpoint.

    Cutpoint is usually negative indicating the number of letters to remove
    from the end of each word.

    >>> joinstem(-2, ["ephemeris", "iris", ".*itis"])
    '(?:ephemer|ir|.*it)'

    >>> joinstem(None, ["ephemeris"])
    '(?:ephemeris)'

    >>> joinstem(5, None)
    '(?:)'
    """
    return enclose("|".join(w[:cutpoint] for w in words or []))


def bysize(words: Iterable[str]) -> Dict[int, set]:
    """
    From a list of words, return a dict of sets sorted by word length.

    >>> words = ['ant', 'cat', 'dog', 'pig', 'frog', 'goat', 'horse', 'elephant']
    >>> ret = bysize(words)
    >>> sorted(ret[3])
    ['ant', 'cat', 'dog', 'pig']
    >>> ret[5]
    {'horse'}
    """
    res: Dict[int, set] = collections.defaultdict(set)
    for w in words:
        res[len(w)].add(w)
    return res


def make_pl_si_lists(
    lst: Iterable[str],
    plending: str,
    siendingsize: Optional[int],
    dojoinstem: bool = True,
):
    """
    given a list of singular words: lst

    an ending to append to make the plural: plending

    the number of characters to remove from the singular
    before appending plending: siendingsize

    a flag whether to create a joinstem: dojoinstem

    return:
    a list of pluralised words: si_list (called si because this is what you need to
    look for to make the singular)

    the pluralised words as a dict of sets sorted by word length: si_bysize
    the singular words as a dict of sets sorted by word length: pl_bysize
    if dojoinstem is True: a regular expression that matches any of the stems: stem
    """
    if siendingsize is not None:
        siendingsize = -siendingsize
    si_list = [w[:siendingsize] + plending for w in lst]
    pl_bysize = bysize(lst)
    si_bysize = bysize(si_list)
    if dojoinstem:
        stem = joinstem(siendingsize, lst)
        return si_list, si_bysize, pl_bysize, stem
    else:
        return si_list, si_bysize, pl_bysize


# 1. PLURALS

pl_sb_irregular_s = {
    "corpus": "corpuses|corpora",
    "opus": "opuses|opera",
    "genus": "genera",
    "mythos": "mythoi",
    "penis": "penises|penes",
    "testis": "testes",
    "atlas": "atlases|atlantes",
    "yes": "yeses",
}

pl_sb_irregular = {
    "child": "children",
    "chili": "chilis|chilies",
    "brother": "brothers|brethren",
    "infinity": "infinities|infinity",
    "loaf": "loaves",
    "lore": "lores|lore",
    "hoof": "hoofs|hooves",
    "beef": "beefs|beeves",
    "thief": "thiefs|thieves",
    "money": "monies",
    "mongoose": "mongooses",
    "ox": "oxen",
    "cow": "cows|kine",
    "graffito": "graffiti",
    "octopus": "octopuses|octopodes",
    "genie": "genies|genii",
    "ganglion": "ganglions|ganglia",
    "trilby": "trilbys",
    "turf": "turfs|turves",
    "numen": "numina",
    "atman": "atmas",
    "occiput": "occiputs|occipita",
    "sabretooth": "sabretooths",
    "sabertooth": "sabertooths",
    "lowlife": "lowlifes",
    "flatfoot": "flatfoots",
    "tenderfoot": "tenderfoots",
    "romany": "romanies",
    "jerry": "jerries",
    "mary": "maries",
    "talouse": "talouses",
    "rom": "roma",
    "carmen": "carmina",
}

pl_sb_irregular.update(pl_sb_irregular_s)
# pl_sb_irregular_keys = enclose('|'.join(pl_sb_irregular.keys()))

pl_sb_irregular_caps = {
    "Romany": "Romanies",
    "Jerry": "Jerrys",
    "Mary": "Marys",
    "Rom": "Roma",
}

pl_sb_irregular_compound = {"prima donna": "prima donnas|prime donne"}

si_sb_irregular = {v: k for (k, v) in pl_sb_irregular.items()}
for k in list(si_sb_irregular):
    if "|" in k:
        k1, k2 = k.split("|")
        si_sb_irregular[k1] = si_sb_irregular[k2] = si_sb_irregular[k]
        del si_sb_irregular[k]
si_sb_irregular_caps = {v: k for (k, v) in pl_sb_irregular_caps.items()}
si_sb_irregular_compound = {v: k for (k, v) in pl_sb_irregular_compound.items()}
for k in list(si_sb_irregular_compound):
    if "|" in k:
        k1, k2 = k.split("|")
        si_sb_irregular_compound[k1] = si_sb_irregular_compound[k2] = (
            si_sb_irregular_compound[k]
        )
        del si_sb_irregular_compound[k]

# si_sb_irregular_keys = enclose('|'.join(si_sb_irregular.keys()))

# Z's that don't double

pl_sb_z_zes_list = ("quartz", "topaz")
pl_sb_z_zes_bysize = bysize(pl_sb_z_zes_list)

pl_sb_ze_zes_list = ("snooze",)
pl_sb_ze_zes_bysize = bysize(pl_sb_ze_zes_list)


# CLASSICAL "..is" -> "..ides"

pl_sb_C_is_ides_complete = [
    # GENERAL WORDS...
    "ephemeris",
    "iris",
    "clitoris",
    "chrysalis",
    "epididymis",
]

pl_sb_C_is_ides_endings = [
    # INFLAMATIONS...
    "itis"
]

pl_sb_C_is_ides = joinstem(
    -2, pl_sb_C_is_ides_complete + [f".*{w}" for w in pl_sb_C_is_ides_endings]
)

pl_sb_C_is_ides_list = pl_sb_C_is_ides_complete + pl_sb_C_is_ides_endings

(
    si_sb_C_is_ides_list,
    si_sb_C_is_ides_bysize,
    pl_sb_C_is_ides_bysize,
) = make_pl_si_lists(pl_sb_C_is_ides_list, "ides", 2, dojoinstem=False)


# CLASSICAL "..a" -> "..ata"

pl_sb_C_a_ata_list = (
    "anathema",
    "bema",
    "carcinoma",
    "charisma",
    "diploma",
    "dogma",
    "drama",
    "edema",
    "enema",
    "enigma",
    "lemma",
    "lymphoma",
    "magma",
    "melisma",
    "miasma",
    "oedema",
    "sarcoma",
    "schema",
    "soma",
    "stigma",
    "stoma",
    "trauma",
    "gumma",
    "pragma",
)

(
    si_sb_C_a_ata_list,
    si_sb_C_a_ata_bysize,
    pl_sb_C_a_ata_bysize,
    pl_sb_C_a_ata,
) = make_pl_si_lists(pl_sb_C_a_ata_list, "ata", 1)

# UNCONDITIONAL "..a" -> "..ae"

pl_sb_U_a_ae_list = (
    "alumna",
    "alga",
    "vertebra",
    "persona",
    "vita",
)
(
    si_sb_U_a_ae_list,
    si_sb_U_a_ae_bysize,
    pl_sb_U_a_ae_bysize,
    pl_sb_U_a_ae,
) = make_pl_si_lists(pl_sb_U_a_ae_list, "e", None)

# CLASSICAL "..a" -> "..ae"

pl_sb_C_a_ae_list = (
    "amoeba",
    "antenna",
    "formula",
    "hyperbola",
    "medusa",
    "nebula",
    "parabola",
    "abscissa",
    "hydra",
    "nova",
    "lacuna",
    "aurora",
    "umbra",
    "flora",
    "fauna",
)
(
    si_sb_C_a_ae_list,
    si_sb_C_a_ae_bysize,
    pl_sb_C_a_ae_bysize,
    pl_sb_C_a_ae,
) = make_pl_si_lists(pl_sb_C_a_ae_list, "e", None)


# CLASSICAL "..en" -> "..ina"

pl_sb_C_en_ina_list = ("stamen", "foramen", "lumen")

(
    si_sb_C_en_ina_list,
    si_sb_C_en_ina_bysize,
    pl_sb_C_en_ina_bysize,
    pl_sb_C_en_ina,
) = make_pl_si_lists(pl_sb_C_en_ina_list, "ina", 2)


# UNCONDITIONAL "..um" -> "..a"

pl_sb_U_um_a_list = (
    "bacterium",
    "agendum",
    "desideratum",
    "erratum",
    "stratum",
    "datum",
    "ovum",
    "extremum",
    "candelabrum",
)
(
    si_sb_U_um_a_list,
    si_sb_U_um_a_bysize,
    pl_sb_U_um_a_bysize,
    pl_sb_U_um_a,
) = make_pl_si_lists(pl_sb_U_um_a_list, "a", 2)

# CLASSICAL "..um" -> "..a"

pl_sb_C_um_a_list = (
    "maximum",
    "minimum",
    "momentum",
    "optimum",
    "quantum",
    "cranium",
    "curriculum",
    "dictum",
    "phylum",
    "aquarium",
    "compendium",
    "emporium",
    "encomium",
    "gymnasium",
    "honorarium",
    "interregnum",
    "lustrum",
    "memorandum",
    "millennium",
    "rostrum",
    "spectrum",
    "speculum",
    "stadium",
    "trapezium",
    "ultimatum",
    "medium",
    "vacuum",
    "velum",
    "consortium",
    "arboretum",
)

(
    si_sb_C_um_a_list,
    si_sb_C_um_a_bysize,
    pl_sb_C_um_a_bysize,
    pl_sb_C_um_a,
) = make_pl_si_lists(pl_sb_C_um_a_list, "a", 2)


# UNCONDITIONAL "..us" -> "i"

pl_sb_U_us_i_list = (
    "alumnus",
    "alveolus",
    "bacillus",
    "bronchus",
    "locus",
    "nucleus",
    "stimulus",
    "meniscus",
    "sarcophagus",
)
(
    si_sb_U_us_i_list,
    si_sb_U_us_i_bysize,
    pl_sb_U_us_i_bysize,
    pl_sb_U_us_i,
) = make_pl_si_lists(pl_sb_U_us_i_list, "i", 2)

# CLASSICAL "..us" -> "..i"

pl_sb_C_us_i_list = (
    "focus",
    "radius",
    "genius",
    "incubus",
    "succubus",
    "nimbus",
    "fungus",
    "nucleolus",
    "stylus",
    "torus",
    "umbilicus",
    "uterus",
    "hippopotamus",
    "cactus",
)

(
    si_sb_C_us_i_list,
    si_sb_C_us_i_bysize,
    pl_sb_C_us_i_bysize,
    pl_sb_C_us_i,
) = make_pl_si_lists(pl_sb_C_us_i_list, "i", 2)


# CLASSICAL "..us" -> "..us"  (ASSIMILATED 4TH DECLENSION LATIN NOUNS)

pl_sb_C_us_us = (
    "status",
    "apparatus",
    "prospectus",
    "sinus",
    "hiatus",
    "impetus",
    "plexus",
)
pl_sb_C_us_us_bysize = bysize(pl_sb_C_us_us)

# UNCONDITIONAL "..on" -> "a"

pl_sb_U_on_a_list = (
    "criterion",
    "perihelion",
    "aphelion",
    "phenomenon",
    "prolegomenon",
    "noumenon",
    "organon",
    "asyndeton",
    "hyperbaton",
)
(
    si_sb_U_on_a_list,
    si_sb_U_on_a_bysize,
    pl_sb_U_on_a_bysize,
    pl_sb_U_on_a,
) = make_pl_si_lists(pl_sb_U_on_a_list, "a", 2)

# CLASSICAL "..on" -> "..a"

pl_sb_C_on_a_list = ("oxymoron",)

(
    si_sb_C_on_a_list,
    si_sb_C_on_a_bysize,
    pl_sb_C_on_a_bysize,
    pl_sb_C_on_a,
) = make_pl_si_lists(pl_sb_C_on_a_list, "a", 2)


# CLASSICAL "..o" -> "..i"  (BUT NORMALLY -> "..os")

pl_sb_C_o_i = [
    "solo",
    "soprano",
    "basso",
    "alto",
    "contralto",
    "tempo",
    "piano",
    "virtuoso",
]  # list not tuple so can concat for pl_sb_U_o_os

pl_sb_C_o_i_bysize = bysize(pl_sb_C_o_i)
si_sb_C_o_i_bysize = bysize([f"{w[:-1]}i" for w in pl_sb_C_o_i])

pl_sb_C_o_i_stems = joinstem(-1, pl_sb_C_o_i)

# ALWAYS "..o" -> "..os"

pl_sb_U_o_os_complete = {"ado", "ISO", "NATO", "NCO", "NGO", "oto"}
si_sb_U_o_os_complete = {f"{w}s" for w in pl_sb_U_o_os_complete}


pl_sb_U_o_os_endings = [
    "aficionado",
    "aggro",
    "albino",
    "allegro",
    "ammo",
    "Antananarivo",
    "archipelago",
    "armadillo",
    "auto",
    "avocado",
    "Bamako",
    "Barquisimeto",
    "bimbo",
    "bingo",
    "Biro",
    "bolero",
    "Bolzano",
    "bongo",
    "Boto",
    "burro",
    "Cairo",
    "canto",
    "cappuccino",
    "casino",
    "cello",
    "Chicago",
    "Chimango",
    "cilantro",
    "cochito",
    "coco",
    "Colombo",
    "Colorado",
    "commando",
    "concertino",
    "contango",
    "credo",
    "crescendo",
    "cyano",
    "demo",
    "ditto",
    "Draco",
    "dynamo",
    "embryo",
    "Esperanto",
    "espresso",
    "euro",
    "falsetto",
    "Faro",
    "fiasco",
    "Filipino",
    "flamenco",
    "furioso",
    "generalissimo",
    "Gestapo",
    "ghetto",
    "gigolo",
    "gizmo",
    "Greensboro",
    "gringo",
    "Guaiabero",
    "guano",
    "gumbo",
    "gyro",
    "hairdo",
    "hippo",
    "Idaho",
    "impetigo",
    "inferno",
    "info",
    "intermezzo",
    "intertrigo",
    "Iquico",
    "jumbo",
    "junto",
    "Kakapo",
    "kilo",
    "Kinkimavo",
    "Kokako",
    "Kosovo",
    "Lesotho",
    "libero",
    "libido",
    "libretto",
    "lido",
    "Lilo",
    "limbo",
    "limo",
    "lineno",
    "lingo",
    "lino",
    "livedo",
    "loco",
    "logo",
    "lumbago",
    "macho",
    "macro",
    "mafioso",
    "magneto",
    "magnifico",
    "Majuro",
    "Malabo",
    "manifesto",
    "Maputo",
    "Maracaibo",
    "medico",
    "memo",
    "metro",
    "Mexico",
    "micro",
    "Milano",
    "Monaco",
    "mono",
    "Montenegro",
    "Morocco",
    "Muqdisho",
    "myo",
    "neutrino",
    "Ningbo",
    "octavo",
    "oregano",
    "Orinoco",
    "Orlando",
    "Oslo",
    "panto",
    "Paramaribo",
    "Pardusco",
    "pedalo",
    "photo",
    "pimento",
    "pinto",
    "pleco",
    "Pluto",
    "pogo",
    "polo",
    "poncho",
    "Porto-Novo",
    "Porto",
    "pro",
    "psycho",
    "pueblo",
    "quarto",
    "Quito",
    "repo",
    "rhino",
    "risotto",
    "rococo",
    "rondo",
    "Sacramento",
    "saddo",
    "sago",
    "salvo",
    "Santiago",
    "Sapporo",
    "Sarajevo",
    "scherzando",
    "scherzo",
    "silo",
    "sirocco",
    "sombrero",
    "staccato",
    "sterno",
    "stucco",
    "stylo",
    "sumo",
    "Taiko",
    "techno",
    "terrazzo",
    "testudo",
    "timpano",
    "tiro",
    "tobacco",
    "Togo",
    "Tokyo",
    "torero",
    "Torino",
    "Toronto",
    "torso",
    "tremolo",
    "typo",
    "tyro",
    "ufo",
    "UNESCO",
    "vaquero",
    "vermicello",
    "verso",
    "vibrato",
    "violoncello",
    "Virgo",
    "weirdo",
    "WHO",
    "WTO",
    "Yamoussoukro",
    "yo-yo",
    "zero",
    "Zibo",
] + pl_sb_C_o_i

pl_sb_U_o_os_bysize = bysize(pl_sb_U_o_os_endings)
si_sb_U_o_os_bysize = bysize([f"{w}s" for w in pl_sb_U_o_os_endings])


# UNCONDITIONAL "..ch" -> "..chs"

pl_sb_U_ch_chs_list = ("czech", "eunuch", "stomach")

(
    si_sb_U_ch_chs_list,
    si_sb_U_ch_chs_bysize,
    pl_sb_U_ch_chs_bysize,
    pl_sb_U_ch_chs,
) = make_pl_si_lists(pl_sb_U_ch_chs_list, "s", None)


# UNCONDITIONAL "..[ei]x" -> "..ices"

pl_sb_U_ex_ices_list = ("codex", "murex", "silex")
(
    si_sb_U_ex_ices_list,
    si_sb_U_ex_ices_bysize,
    pl_sb_U_ex_ices_bysize,
    pl_sb_U_ex_ices,
) = make_pl_si_lists(pl_sb_U_ex_ices_list, "ices", 2)

pl_sb_U_ix_ices_list = ("radix", "helix")
(
    si_sb_U_ix_ices_list,
    si_sb_U_ix_ices_bysize,
    pl_sb_U_ix_ices_bysize,
    pl_sb_U_ix_ices,
) = make_pl_si_lists(pl_sb_U_ix_ices_list, "ices", 2)

# CLASSICAL "..[ei]x" -> "..ices"

pl_sb_C_ex_ices_list = (
    "vortex",
    "vertex",
    "cortex",
    "latex",
    "pontifex",
    "apex",
    "index",
    "simplex",
)

(
    si_sb_C_ex_ices_list,
    si_sb_C_ex_ices_bysize,
    pl_sb_C_ex_ices_bysize,
    pl_sb_C_ex_ices,
) = make_pl_si_lists(pl_sb_C_ex_ices_list, "ices", 2)


pl_sb_C_ix_ices_list = ("appendix",)

(
    si_sb_C_ix_ices_list,
    si_sb_C_ix_ices_bysize,
    pl_sb_C_ix_ices_bysize,
    pl_sb_C_ix_ices,
) = make_pl_si_lists(pl_sb_C_ix_ices_list, "ices", 2)


# ARABIC: ".." -> "..i"

pl_sb_C_i_list = ("afrit", "afreet", "efreet")

(si_sb_C_i_list, si_sb_C_i_bysize, pl_sb_C_i_bysize, pl_sb_C_i) = make_pl_si_lists(
    pl_sb_C_i_list, "i", None
)


# HEBREW: ".." -> "..im"

pl_sb_C_im_list = ("goy", "seraph", "cherub")

(si_sb_C_im_list, si_sb_C_im_bysize, pl_sb_C_im_bysize, pl_sb_C_im) = make_pl_si_lists(
    pl_sb_C_im_list, "im", None
)


# UNCONDITIONAL "..man" -> "..mans"

pl_sb_U_man_mans_list = """
    ataman caiman cayman ceriman
    desman dolman farman harman hetman
    human leman ottoman shaman talisman
""".split()
pl_sb_U_man_mans_caps_list = """
    Alabaman Bahaman Burman German
    Hiroshiman Liman Nakayaman Norman Oklahoman
    Panaman Roman Selman Sonaman Tacoman Yakiman
    Yokohaman Yuman
""".split()

(
    si_sb_U_man_mans_list,
    si_sb_U_man_mans_bysize,
    pl_sb_U_man_mans_bysize,
) = make_pl_si_lists(pl_sb_U_man_mans_list, "s", None, dojoinstem=False)
(
    si_sb_U_man_mans_caps_list,
    si_sb_U_man_mans_caps_bysize,
    pl_sb_U_man_mans_caps_bysize,
) = make_pl_si_lists(pl_sb_U_man_mans_caps_list, "s", None, dojoinstem=False)

# UNCONDITIONAL "..louse" -> "..lice"
pl_sb_U_louse_lice_list = ("booklouse", "grapelouse", "louse", "woodlouse")

(
    si_sb_U_louse_lice_list,
    si_sb_U_louse_lice_bysize,
    pl_sb_U_louse_lice_bysize,
) = make_pl_si_lists(pl_sb_U_louse_lice_list, "lice", 5, dojoinstem=False)

pl_sb_uninflected_s_complete = [
    # PAIRS OR GROUPS SUBSUMED TO A SINGULAR...
    "breeches",
    "britches",
    "pajamas",
    "pyjamas",
    "clippers",
    "gallows",
    "hijinks",
    "headquarters",
    "pliers",
    "scissors",
    "testes",
    "herpes",
    "pincers",
    "shears",
    "proceedings",
    "trousers",
    # UNASSIMILATED LATIN 4th DECLENSION
    "cantus",
    "coitus",
    "nexus",
    # RECENT IMPORTS...
    "contretemps",
    "corps",
    "debris",
    "siemens",
    # DISEASES
    "mumps",
    # MISCELLANEOUS OTHERS...
    "diabetes",
    "jackanapes",
    "series",
    "species",
    "subspecies",
    "rabies",
    "chassis",
    "innings",
    "news",
    "mews",
    "haggis",
]

pl_sb_uninflected_s_endings = [
    # RECENT IMPORTS...
    "ois",
    # DISEASES
    "measles",
]

pl_sb_uninflected_s = pl_sb_uninflected_s_complete + [
    f".*{w}" for w in pl_sb_uninflected_s_endings
]

pl_sb_uninflected_herd = (
    # DON'T INFLECT IN CLASSICAL MODE, OTHERWISE NORMAL INFLECTION
    "wildebeest",
    "swine",
    "eland",
    "bison",
    "buffalo",
    "cattle",
    "elk",
    "rhinoceros",
    "zucchini",
    "caribou",
    "dace",
    "grouse",
    "guinea fowl",
    "guinea-fowl",
    "haddock",
    "hake",
    "halibut",
    "herring",
    "mackerel",
    "pickerel",
    "pike",
    "roe",
    "seed",
    "shad",
    "snipe",
    "teal",
    "turbot",
    "water fowl",
    "water-fowl",
)

pl_sb_uninflected_complete = [
    # SOME FISH AND HERD ANIMALS
    "tuna",
    "salmon",
    "mackerel",
    "trout",
    "bream",
    "sea-bass",
    "sea bass",
    "carp",
    "cod",
    "flounder",
    "whiting",
    "moose",
    # OTHER ODDITIES
    "graffiti",
    "djinn",
    "samuri",
    "offspring",
    "pence",
    "quid",
    "hertz",
] + pl_sb_uninflected_s_complete
# SOME WORDS ENDING IN ...s (OFTEN PAIRS TAKEN AS A WHOLE)

pl_sb_uninflected_caps = [
    # ALL NATIONALS ENDING IN -ese
    "Portuguese",
    "Amoyese",
    "Borghese",
    "Congoese",
    "Faroese",
    "Foochowese",
    "Genevese",
    "Genoese",
    "Gilbertese",
    "Hottentotese",
    "Kiplingese",
    "Kongoese",
    "Lucchese",
    "Maltese",
    "Nankingese",
    "Niasese",
    "Pekingese",
    "Piedmontese",
    "Pistoiese",
    "Sarawakese",
    "Shavese",
    "Vermontese",
    "Wenchowese",
    "Yengeese",
]


pl_sb_uninflected_endings = [
    # UNCOUNTABLE NOUNS
    "butter",
    "cash",
    "furniture",
    "information",
    # SOME FISH AND HERD ANIMALS
    "fish",
    "deer",
    "sheep",
    # ALL NATIONALS ENDING IN -ese
    "nese",
    "rese",
    "lese",
    "mese",
    # DISEASES
    "pox",
    # OTHER ODDITIES
    "craft",
] + pl_sb_uninflected_s_endings
# SOME WORDS ENDING IN ...s (OFTEN PAIRS TAKEN AS A WHOLE)


pl_sb_uninflected_bysize = bysize(pl_sb_uninflected_endings)


# SINGULAR WORDS ENDING IN ...s (ALL INFLECT WITH ...es)

pl_sb_singular_s_complete = [
    "acropolis",
    "aegis",
    "alias",
    "asbestos",
    "bathos",
    "bias",
    "bronchitis",
    "bursitis",
    "caddis",
    "cannabis",
    "canvas",
    "chaos",
    "cosmos",
    "dais",
    "digitalis",
    "epidermis",
    "ethos",
    "eyas",
    "gas",
    "glottis",
    "hubris",
    "ibis",
    "lens",
    "mantis",
    "marquis",
    "metropolis",
    "pathos",
    "pelvis",
    "polis",
    "rhinoceros",
    "sassafras",
    "trellis",
] + pl_sb_C_is_ides_complete


pl_sb_singular_s_endings = ["ss", "us"] + pl_sb_C_is_ides_endings

pl_sb_singular_s_bysize = bysize(pl_sb_singular_s_endings)

si_sb_singular_s_complete = [f"{w}es" for w in pl_sb_singular_s_complete]
si_sb_singular_s_endings = [f"{w}es" for w in pl_sb_singular_s_endings]
si_sb_singular_s_bysize = bysize(si_sb_singular_s_endings)

pl_sb_singular_s_es = ["[A-Z].*es"]

pl_sb_singular_s = enclose(
    "|".join(
        pl_sb_singular_s_complete
        + [f".*{w}" for w in pl_sb_singular_s_endings]
        + pl_sb_singular_s_es
    )
)


# PLURALS ENDING IN uses -> use


si_sb_ois_oi_case = ("Bolshois", "Hanois")

si_sb_uses_use_case = ("Betelgeuses", "Duses", "Meuses", "Syracuses", "Toulouses")

si_sb_uses_use = (
    "abuses",
    "applauses",
    "blouses",
    "carouses",
    "causes",
    "chartreuses",
    "clauses",
    "contuses",
    "douses",
    "excuses",
    "fuses",
    "grouses",
    "hypotenuses",
    "masseuses",
    "menopauses",
    "misuses",
    "muses",
    "overuses",
    "pauses",
    "peruses",
    "profuses",
    "recluses",
    "reuses",
    "ruses",
    "souses",
    "spouses",
    "suffuses",
    "transfuses",
    "uses",
)

si_sb_ies_ie_case = (
    "Addies",
    "Aggies",
    "Allies",
    "Amies",
    "Angies",
    "Annies",
    "Annmaries",
    "Archies",
    "Arties",
    "Aussies",
    "Barbies",
    "Barries",
    "Basies",
    "Bennies",
    "Bernies",
    "Berties",
    "Bessies",
    "Betties",
    "Billies",
    "Blondies",
    "Bobbies",
    "Bonnies",
    "Bowies",
    "Brandies",
    "Bries",
    "Brownies",
    "Callies",
    "Carnegies",
    "Carries",
    "Cassies",
    "Charlies",
    "Cheries",
    "Christies",
    "Connies",
    "Curies",
    "Dannies",
    "Debbies",
    "Dixies",
    "Dollies",
    "Donnies",
    "Drambuies",
    "Eddies",
    "Effies",
    "Ellies",
    "Elsies",
    "Eries",
    "Ernies",
    "Essies",
    "Eugenies",
    "Fannies",
    "Flossies",
    "Frankies",
    "Freddies",
    "Gillespies",
    "Goldies",
    "Gracies",
    "Guthries",
    "Hallies",
    "Hatties",
    "Hetties",
    "Hollies",
    "Jackies",
    "Jamies",
    "Janies",
    "Jannies",
    "Jeanies",
    "Jeannies",
    "Jennies",
    "Jessies",
    "Jimmies",
    "Jodies",
    "Johnies",
    "Johnnies",
    "Josies",
    "Julies",
    "Kalgoorlies",
    "Kathies",
    "Katies",
    "Kellies",
    "Kewpies",
    "Kristies",
    "Laramies",
    "Lassies",
    "Lauries",
    "Leslies",
    "Lessies",
    "Lillies",
    "Lizzies",
    "Lonnies",
    "Lories",
    "Lorries",
    "Lotties",
    "Louies",
    "Mackenzies",
    "Maggies",
    "Maisies",
    "Mamies",
    "Marcies",
    "Margies",
    "Maries",
    "Marjories",
    "Matties",
    "McKenzies",
    "Melanies",
    "Mickies",
    "Millies",
    "Minnies",
    "Mollies",
    "Mounties",
    "Nannies",
    "Natalies",
    "Nellies",
    "Netties",
    "Ollies",
    "Ozzies",
    "Pearlies",
    "Pottawatomies",
    "Reggies",
    "Richies",
    "Rickies",
    "Robbies",
    "Ronnies",
    "Rosalies",
    "Rosemaries",
    "Rosies",
    "Roxies",
    "Rushdies",
    "Ruthies",
    "Sadies",
    "Sallies",
    "Sammies",
    "Scotties",
    "Selassies",
    "Sherries",
    "Sophies",
    "Stacies",
    "Stefanies",
    "Stephanies",
    "Stevies",
    "Susies",
    "Sylvies",
    "Tammies",
    "Terries",
    "Tessies",
    "Tommies",
    "Tracies",
    "Trekkies",
    "Valaries",
    "Valeries",
    "Valkyries",
    "Vickies",
    "Virgies",
    "Willies",
    "Winnies",
    "Wylies",
    "Yorkies",
)

si_sb_ies_ie = (
    "aeries",
    "baggies",
    "belies",
    "biggies",
    "birdies",
    "bogies",
    "bonnies",
    "boogies",
    "bookies",
    "bourgeoisies",
    "brownies",
    "budgies",
    "caddies",
    "calories",
    "camaraderies",
    "cockamamies",
    "collies",
    "cookies",
    "coolies",
    "cooties",
    "coteries",
    "crappies",
    "curies",
    "cutesies",
    "dogies",
    "eyries",
    "floozies",
    "footsies",
    "freebies",
    "genies",
    "goalies",
    "groupies",
    "hies",
    "jalousies",
    "junkies",
    "kiddies",
    "laddies",
    "lassies",
    "lies",
    "lingeries",
    "magpies",
    "menageries",
    "mommies",
    "movies",
    "neckties",
    "newbies",
    "nighties",
    "oldies",
    "organdies",
    "overlies",
    "pies",
    "pinkies",
    "pixies",
    "potpies",
    "prairies",
    "quickies",
    "reveries",
    "rookies",
    "rotisseries",
    "softies",
    "sorties",
    "species",
    "stymies",
    "sweeties",
    "ties",
    "underlies",
    "unties",
    "veggies",
    "vies",
    "yuppies",
    "zombies",
)


si_sb_oes_oe_case = (
    "Chloes",
    "Crusoes",
    "Defoes",
    "Faeroes",
    "Ivanhoes",
    "Joes",
    "McEnroes",
    "Moes",
    "Monroes",
    "Noes",
    "Poes",
    "Roscoes",
    "Tahoes",
    "Tippecanoes",
    "Zoes",
)

si_sb_oes_oe = (
    "aloes",
    "backhoes",
    "canoes",
    "does",
    "floes",
    "foes",
    "hoes",
    "mistletoes",
    "oboes",
    "pekoes",
    "roes",
    "sloes",
    "throes",
    "tiptoes",
    "toes",
    "woes",
)

si_sb_z_zes = ("quartzes", "topazes")

si_sb_zzes_zz = ("buzzes", "fizzes", "frizzes", "razzes")

si_sb_ches_che_case = (
    "Andromaches",
    "Apaches",
    "Blanches",
    "Comanches",
    "Nietzsches",
    "Porsches",
    "Roches",
)

si_sb_ches_che = (
    "aches",
    "avalanches",
    "backaches",
    "bellyaches",
    "caches",
    "cloches",
    "creches",
    "douches",
    "earaches",
    "fiches",
    "headaches",
    "heartaches",
    "microfiches",
    "niches",
    "pastiches",
    "psyches",
    "quiches",
    "stomachaches",
    "toothaches",
    "tranches",
)

si_sb_xes_xe = ("annexes", "axes", "deluxes", "pickaxes")

si_sb_sses_sse_case = ("Hesses", "Jesses", "Larousses", "Matisses")
si_sb_sses_sse = (
    "bouillabaisses",
    "crevasses",
    "demitasses",
    "impasses",
    "mousses",
    "posses",
)

si_sb_ves_ve_case = (
    # *[nwl]ives -> [nwl]live
    "Clives",
    "Palmolives",
)
si_sb_ves_ve = (
    # *[^d]eaves -> eave
    "interweaves",
    "weaves",
    # *[nwl]ives -> [nwl]live
    "olives",
    # *[eoa]lves -> [eoa]lve
    "bivalves",
    "dissolves",
    "resolves",
    "salves",
    "twelves",
    "valves",
)


plverb_special_s = enclose(
    "|".join(
        [pl_sb_singular_s]
        + pl_sb_uninflected_s
        + list(pl_sb_irregular_s)
        + ["(.*[csx])is", "(.*)ceps", "[A-Z].*s"]
    )
)

_pl_sb_postfix_adj_defn = (
    ("general", enclose(r"(?!major|lieutenant|brigadier|adjutant|.*star)\S+")),
    ("martial", enclose("court")),
    ("force", enclose("pound")),
)

pl_sb_postfix_adj: Iterable[str] = (
    enclose(val + f"(?=(?:-|\\s+){key})") for key, val in _pl_sb_postfix_adj_defn
)

pl_sb_postfix_adj_stems = f"({'|'.join(pl_sb_postfix_adj)})(.*)"


# PLURAL WORDS ENDING IS es GO TO SINGULAR is

si_sb_es_is = (
    "amanuenses",
    "amniocenteses",
    "analyses",
    "antitheses",
    "apotheoses",
    "arterioscleroses",
    "atheroscleroses",
    "axes",
    # 'bases', # bases -> basis
    "catalyses",
    "catharses",
    "chasses",
    "cirrhoses",
    "cocces",
    "crises",
    "diagnoses",
    "dialyses",
    "diereses",
    "electrolyses",
    "emphases",
    "exegeses",
    "geneses",
    "halitoses",
    "hydrolyses",
    "hypnoses",
    "hypotheses",
    "hystereses",
    "metamorphoses",
    "metastases",
    "misdiagnoses",
    "mitoses",
    "mononucleoses",
    "narcoses",
    "necroses",
    "nemeses",
    "neuroses",
    "oases",
    "osmoses",
    "osteoporoses",
    "paralyses",
    "parentheses",
    "parthenogeneses",
    "periphrases",
    "photosyntheses",
    "probosces",
    "prognoses",
    "prophylaxes",
    "prostheses",
    "preces",
    "psoriases",
    "psychoanalyses",
    "psychokineses",
    "psychoses",
    "scleroses",
    "scolioses",
    "sepses",
    "silicoses",
    "symbioses",
    "synopses",
    "syntheses",
    "taxes",
    "telekineses",
    "theses",
    "thromboses",
    "tuberculoses",
    "urinalyses",
)

pl_prep_list = """
    about above across after among around at athwart before behind
    below beneath beside besides between betwixt beyond but by
    during except for from in into near of off on onto out over
    since till to under until unto upon with""".split()

pl_prep_list_da = pl_prep_list + ["de", "du", "da"]

pl_prep_bysize = bysize(pl_prep_list_da)

pl_prep = enclose("|".join(pl_prep_list_da))

pl_sb_prep_dual_compound = rf"(.*?)((?:-|\s+)(?:{pl_prep})(?:-|\s+))a(?:-|\s+)(.*)"


singular_pronoun_genders = {
    "neuter",
    "feminine",
    "masculine",
    "gender-neutral",
    "feminine or masculine",
    "masculine or feminine",
}

pl_pron_nom = {
    # NOMINATIVE    REFLEXIVE
    "i": "we",
    "myself": "ourselves",
    "you": "you",
    "yourself": "yourselves",
    "she": "they",
    "herself": "themselves",
    "he": "they",
    "himself": "themselves",
    "it": "they",
    "itself": "themselves",
    "they": "they",
    "themself": "themselves",
    #   POSSESSIVE
    "mine": "ours",
    "yours": "yours",
    "hers": "theirs",
    "his": "theirs",
    "its": "theirs",
    "theirs": "theirs",
}

si_pron: Dict[str, Dict[str, Union[str, Dict[str, str]]]] = {
    "nom": {v: k for (k, v) in pl_pron_nom.items()}
}
si_pron["nom"]["we"] = "I"


pl_pron_acc = {
    # ACCUSATIVE    REFLEXIVE
    "me": "us",
    "myself": "ourselves",
    "you": "you",
    "yourself": "yourselves",
    "her": "them",
    "herself": "themselves",
    "him": "them",
    "himself": "themselves",
    "it": "them",
    "itself": "themselves",
    "them": "them",
    "themself": "themselves",
}

pl_pron_acc_keys = enclose("|".join(pl_pron_acc))
pl_pron_acc_keys_bysize = bysize(pl_pron_acc)

si_pron["acc"] = {v: k for (k, v) in pl_pron_acc.items()}

for _thecase, _plur, _gend, _sing in (
    ("nom", "they", "neuter", "it"),
    ("nom", "they", "feminine", "she"),
    ("nom", "they", "masculine", "he"),
    ("nom", "they", "gender-neutral", "they"),
    ("nom", "they", "feminine or masculine", "she or he"),
    ("nom", "they", "masculine or feminine", "he or she"),
    ("nom", "themselves", "neuter", "itself"),
    ("nom", "themselves", "feminine", "herself"),
    ("nom", "themselves", "masculine", "himself"),
    ("nom", "themselves", "gender-neutral", "themself"),
    ("nom", "themselves", "feminine or masculine", "herself or himself"),
    ("nom", "themselves", "masculine or feminine", "himself or herself"),
    ("nom", "theirs", "neuter", "its"),
    ("nom", "theirs", "feminine", "hers"),
    ("nom", "theirs", "masculine", "his"),
    ("nom", "theirs", "gender-neutral", "theirs"),
    ("nom", "theirs", "feminine or masculine", "hers or his"),
    ("nom", "theirs", "masculine or feminine", "his or hers"),
    ("acc", "them", "neuter", "it"),
    ("acc", "them", "feminine", "her"),
    ("acc", "them", "masculine", "him"),
    ("acc", "them", "gender-neutral", "them"),
    ("acc", "them", "feminine or masculine", "her or him"),
    ("acc", "them", "masculine or feminine", "him or her"),
    ("acc", "themselves", "neuter", "itself"),
    ("acc", "themselves", "feminine", "herself"),
    ("acc", "themselves", "masculine", "himself"),
    ("acc", "themselves", "gender-neutral", "themself"),
    ("acc", "themselves", "feminine or masculine", "herself or himself"),
    ("acc", "themselves", "masculine or feminine", "himself or herself"),
):
    try:
        si_pron[_thecase][_plur][_gend] = _sing  # type: ignore
    except TypeError:
        si_pron[_thecase][_plur] = {}
        si_pron[_thecase][_plur][_gend] = _sing  # type: ignore


si_pron_acc_keys = enclose("|".join(si_pron["acc"]))
si_pron_acc_keys_bysize = bysize(si_pron["acc"])


def get_si_pron(thecase, word, gender) -> str:
    try:
        sing = si_pron[thecase][word]
    except KeyError:
        raise  # not a pronoun
    try:
        return sing[gender]  # has several types due to gender
    except TypeError:
        return cast(str, sing)  # answer independent of gender


# These dictionaries group verbs by first, second and third person
# conjugations.

plverb_irregular_pres = {
    "am": "are",
    "are": "are",
    "is": "are",
    "was": "were",
    "were": "were",
    "have": "have",
    "has": "have",
    "do": "do",
    "does": "do",
}

plverb_ambiguous_pres = {
    "act": "act",
    "acts": "act",
    "blame": "blame",
    "blames": "blame",
    "can": "can",
    "must": "must",
    "fly": "fly",
    "flies": "fly",
    "copy": "copy",
    "copies": "copy",
    "drink": "drink",
    "drinks": "drink",
    "fight": "fight",
    "fights": "fight",
    "fire": "fire",
    "fires": "fire",
    "like": "like",
    "likes": "like",
    "look": "look",
    "looks": "look",
    "make": "make",
    "makes": "make",
    "reach": "reach",
    "reaches": "reach",
    "run": "run",
    "runs": "run",
    "sink": "sink",
    "sinks": "sink",
    "sleep": "sleep",
    "sleeps": "sleep",
    "view": "view",
    "views": "view",
}

plverb_ambiguous_pres_keys = re.compile(
    rf"^({enclose('|'.join(plverb_ambiguous_pres))})((\s.*)?)$", re.IGNORECASE
)


plverb_irregular_non_pres = (
    "did",
    "had",
    "ate",
    "made",
    "put",
    "spent",
    "fought",
    "sank",
    "gave",
    "sought",
    "shall",
    "could",
    "ought",
    "should",
)

plverb_ambiguous_non_pres = re.compile(
    r"^((?:thought|saw|bent|will|might|cut))((\s.*)?)$", re.IGNORECASE
)

# "..oes" -> "..oe" (the rest are "..oes" -> "o")

pl_v_oes_oe = ("canoes", "floes", "oboes", "roes", "throes", "woes")
pl_v_oes_oe_endings_size4 = ("hoes", "toes")
pl_v_oes_oe_endings_size5 = ("shoes",)


pl_count_zero = ("0", "no", "zero", "nil")


pl_count_one = ("1", "a", "an", "one", "each", "every", "this", "that")

pl_adj_special = {"a": "some", "an": "some", "this": "these", "that": "those"}

pl_adj_special_keys = re.compile(
    rf"^({enclose('|'.join(pl_adj_special))})$", re.IGNORECASE
)

pl_adj_poss = {
    "my": "our",
    "your": "your",
    "its": "their",
    "her": "their",
    "his": "their",
    "their": "their",
}

pl_adj_poss_keys = re.compile(rf"^({enclose('|'.join(pl_adj_poss))})$", re.IGNORECASE)


# 2. INDEFINITE ARTICLES

# THIS PATTERN MATCHES STRINGS OF CAPITALS STARTING WITH A "VOWEL-SOUND"
# CONSONANT FOLLOWED BY ANOTHER CONSONANT, AND WHICH ARE NOT LIKELY
# TO BE REAL WORDS (OH, ALL RIGHT THEN, IT'S JUST MAGIC!)

A_abbrev = re.compile(
    r"""
^(?! FJO | [HLMNS]Y.  | RY[EO] | SQU
  | ( F[LR]? | [HL] | MN? | N | RH? | S[CHKLMNPTVW]? | X(YL)?) [AEIOU])
[FHLMNRSX][A-Z]
""",
    re.VERBOSE,
)

# THIS PATTERN CODES THE BEGINNINGS OF ALL ENGLISH WORDS BEGINING WITH A
# 'y' FOLLOWED BY A CONSONANT. ANY OTHER Y-CONSONANT PREFIX THEREFORE
# IMPLIES AN ABBREVIATION.

A_y_cons = re.compile(r"^(y(b[lor]|cl[ea]|fere|gg|p[ios]|rou|tt))", re.IGNORECASE)

# EXCEPTIONS TO EXCEPTIONS

A_explicit_a = re.compile(r"^((?:unabomber|unanimous|US))", re.IGNORECASE)

A_explicit_an = re.compile(
    r"^((?:euler|hour(?!i)|heir|honest|hono[ur]|mpeg))", re.IGNORECASE
)

A_ordinal_an = re.compile(r"^([aefhilmnorsx]-?th)", re.IGNORECASE)

A_ordinal_a = re.compile(r"^([bcdgjkpqtuvwyz]-?th)", re.IGNORECASE)


# NUMERICAL INFLECTIONS

nth = {
    0: "th",
    1: "st",
    2: "nd",
    3: "rd",
    4: "th",
    5: "th",
    6: "th",
    7: "th",
    8: "th",
    9: "th",
    11: "th",
    12: "th",
    13: "th",
}
nth_suff = set(nth.values())

ordinal = dict(
    ty="tieth",
    one="first",
    two="second",
    three="third",
    five="fifth",
    eight="eighth",
    nine="ninth",
    twelve="twelfth",
)

ordinal_suff = re.compile(rf"({'|'.join(ordinal)})\Z")


# NUMBERS

unit = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
teen = [
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
ten = [
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
]
mill = [
    " ",
    " thousand",
    " million",
    " billion",
    " trillion",
    " quadrillion",
    " quintillion",
    " sextillion",
    " septillion",
    " octillion",
    " nonillion",
    " decillion",
]


# SUPPORT CLASSICAL PLURALIZATIONS

def_classical = dict(
    all=False, zero=False, herd=False, names=True, persons=False, ancient=False
)

all_classical = {k: True for k in def_classical}
no_classical = {k: False for k in def_classical}


# Maps strings to built-in constant types
string_to_constant = {"True": True, "False": False, "None": None}


# Pre-compiled regular expression objects
DOLLAR_DIGITS = re.compile(r"\$(\d+)")
FUNCTION_CALL = re.compile(r"((\w+)\([^)]*\)*)", re.IGNORECASE)
PARTITION_WORD = re.compile(r"\A(\s*)(.+?)(\s*)\Z")
PL_SB_POSTFIX_ADJ_STEMS_RE = re.compile(
    rf"^(?:{pl_sb_postfix_adj_stems})$", re.IGNORECASE
)
PL_SB_PREP_DUAL_COMPOUND_RE = re.compile(
    rf"^(?:{pl_sb_prep_dual_compound})$", re.IGNORECASE
)
DENOMINATOR = re.compile(r"(?P<denominator>.+)( (per|a) .+)")
PLVERB_SPECIAL_S_RE = re.compile(rf"^({plverb_special_s})$")
WHITESPACE = re.compile(r"\s")
ENDS_WITH_S = re.compile(r"^(.*[^s])s$", re.IGNORECASE)
ENDS_WITH_APOSTROPHE_S = re.compile(r"^(.*)'s?$")
INDEFINITE_ARTICLE_TEST = re.compile(r"\A(\s*)(?:an?\s+)?(.+?)(\s*)\Z", re.IGNORECASE)
SPECIAL_AN = re.compile(r"^[aefhilmnorsx]$", re.IGNORECASE)
SPECIAL_A = re.compile(r"^[bcdgjkpqtuvwyz]$", re.IGNORECASE)
SPECIAL_ABBREV_AN = re.compile(r"^[aefhilmnorsx][.-]", re.IGNORECASE)
SPECIAL_ABBREV_A = re.compile(r"^[a-z][.-]", re.IGNORECASE)
CONSONANTS = re.compile(r"^[^aeiouy]", re.IGNORECASE)
ARTICLE_SPECIAL_EU = re.compile(r"^e[uw]", re.IGNORECASE)
ARTICLE_SPECIAL_ONCE = re.compile(r"^onc?e\b", re.IGNORECASE)
ARTICLE_SPECIAL_ONETIME = re.compile(r"^onetime\b", re.IGNORECASE)
ARTICLE_SPECIAL_UNIT = re.compile(r"^uni([^nmd]|mo)", re.IGNORECASE)
ARTICLE_SPECIAL_UBA = re.compile(r"^u[bcfghjkqrst][aeiou]", re.IGNORECASE)
ARTICLE_SPECIAL_UKR = re.compile(r"^ukr", re.IGNORECASE)
SPECIAL_CAPITALS = re.compile(r"^U[NK][AIEO]?")
VOWELS = re.compile(r"^[aeiou]", re.IGNORECASE)

DIGIT_GROUP = re.compile(r"(\d)")
TWO_DIGITS = re.compile(r"(\d)(\d)")
THREE_DIGITS = re.compile(r"(\d)(\d)(\d)")
THREE_DIGITS_WORD = re.compile(r"(\d)(\d)(\d)(?=\D*\Z)")
TWO_DIGITS_WORD = re.compile(r"(\d)(\d)(?=\D*\Z)")
ONE_DIGIT_WORD = re.compile(r"(\d)(?=\D*\Z)")

FOUR_DIGIT_COMMA = re.compile(r"(\d)(\d{3}(?:,|\Z))")
NON_DIGIT = re.compile(r"\D")
WHITESPACES_COMMA = re.compile(r"\s+,")
COMMA_WORD = re.compile(r", (\S+)\s+\Z")
WHITESPACES = re.compile(r"\s+")


PRESENT_PARTICIPLE_REPLACEMENTS = (
    (re.compile(r"ie$"), r"y"),
    (
        re.compile(r"ue$"),
        r"u",
    ),  # TODO: isn't ue$ -> u encompassed in the following rule?
    (re.compile(r"([auy])e$"), r"\g<1>"),
    (re.compile(r"ski$"), r"ski"),
    (re.compile(r"[^b]i$"), r""),
    (re.compile(r"^(are|were)$"), r"be"),
    (re.compile(r"^(had)$"), r"hav"),
    (re.compile(r"^(hoe)$"), r"\g<1>"),
    (re.compile(r"([^e])e$"), r"\g<1>"),
    (re.compile(r"er$"), r"er"),
    (re.compile(r"([^aeiou][aeiouy]([bdgmnprst]))$"), r"\g<1>\g<2>"),
)

DIGIT = re.compile(r"\d")


class Words(str):
    lowered: str
    split_: List[str]
    first: str
    last: str

    def __init__(self, orig) -> None:
        self.lowered = self.lower()
        self.split_ = self.split()
        self.first = self.split_[0]
        self.last = self.split_[-1]


Falsish = Any  # ideally, falsish would only validate on bool(value) is False


_STATIC_TYPE_CHECKING = TYPE_CHECKING
# ^-- Workaround for typeguard AST manipulation:
#     https://github.com/agronholm/typeguard/issues/353#issuecomment-1556306554

if _STATIC_TYPE_CHECKING:  # pragma: no cover
    Word = Annotated[str, "String with at least 1 character"]
else:

    class _WordMeta(type):  # Too dynamic to be supported by mypy...
        def __instancecheck__(self, instance: Any) -> bool:
            return isinstance(instance, str) and len(instance) >= 1

    class Word(metaclass=_WordMeta):  # type: ignore[no-redef]
        """String with at least 1 character"""


class engine:
    def __init__(self) -> None:
        self.classical_dict = def_classical.copy()
        self.persistent_count: Optional[int] = None
        self.mill_count = 0
        self.pl_sb_user_defined: List[Optional[Word]] = []
        self.pl_v_user_defined: List[Optional[Word]] = []
        self.pl_adj_user_defined: List[Optional[Word]] = []
        self.si_sb_user_defined: List[Optional[Word]] = []
        self.A_a_user_defined: List[Optional[Word]] = []
        self.thegender = "neuter"
        self.__number_args: Optional[Dict[str, str]] = None

    @property
    def _number_args(self):
        return cast(Dict[str, str], self.__number_args)

    @_number_args.setter
    def _number_args(self, val):
        self.__number_args = val

    @typechecked
    def defnoun(self, singular: Optional[Word], plural: Optional[Word]) -> int:
        """
        Set the noun plural of singular to plural.

        """
        self.checkpat(singular)
        self.checkpatplural(plural)
        self.pl_sb_user_defined.extend((singular, plural))
        self.si_sb_user_defined.extend((plural, singular))
        return 1

    @typechecked
    def defverb(
        self,
        s1: Optional[Word],
        p1: Optional[Word],
        s2: Optional[Word],
        p2: Optional[Word],
        s3: Optional[Word],
        p3: Optional[Word],
    ) -> int:
        """
        Set the verb plurals for s1, s2 and s3 to p1, p2 and p3 respectively.

        Where 1, 2 and 3 represent the 1st, 2nd and 3rd person forms of the verb.

        """
        self.checkpat(s1)
        self.checkpat(s2)
        self.checkpat(s3)
        self.checkpatplural(p1)
        self.checkpatplural(p2)
        self.checkpatplural(p3)
        self.pl_v_user_defined.extend((s1, p1, s2, p2, s3, p3))
        return 1

    @typechecked
    def defadj(self, singular: Optional[Word], plural: Optional[Word]) -> int:
        """
        Set the adjective plural of singular to plural.

        """
        self.checkpat(singular)
        self.checkpatplural(plural)
        self.pl_adj_user_defined.extend((singular, plural))
        return 1

    @typechecked
    def defa(self, pattern: Optional[Word]) -> int:
        """
        Define the indefinite article as 'a' for words matching pattern.

        """
        self.checkpat(pattern)
        self.A_a_user_defined.extend((pattern, "a"))
        return 1

    @typechecked
    def defan(self, pattern: Optional[Word]) -> int:
        """
        Define the indefinite article as 'an' for words matching pattern.

        """
        self.checkpat(pattern)
        self.A_a_user_defined.extend((pattern, "an"))
        return 1

    def checkpat(self, pattern: Optional[Word]) -> None:
        """
        check for errors in a regex pattern
        """
        if pattern is None:
            return
        try:
            re.match(pattern, "")
        except re.error as err:
            raise BadUserDefinedPatternError(pattern) from err

    def checkpatplural(self, pattern: Optional[Word]) -> None:
        """
        check for errors in a regex replace pattern
        """
        return

    @typechecked
    def ud_match(self, word: Word, wordlist: Sequence[Optional[Word]]) -> Optional[str]:
        for i in range(len(wordlist) - 2, -2, -2):  # backwards through even elements
            mo = re.search(rf"^{wordlist[i]}$", word, re.IGNORECASE)
            if mo:
                if wordlist[i + 1] is None:
                    return None
                pl = DOLLAR_DIGITS.sub(
                    r"\\1", cast(Word, wordlist[i + 1])
                )  # change $n to \n for expand
                return mo.expand(pl)
        return None

    def classical(self, **kwargs) -> None:
        """
        turn classical mode on and off for various categories

        turn on all classical modes:
        classical()
        classical(all=True)

        turn on or off specific claassical modes:
        e.g.
        classical(herd=True)
        classical(names=False)

        By default all classical modes are off except names.

        unknown value in args or key in kwargs raises
        exception: UnknownClasicalModeError

        """
        if not kwargs:
            self.classical_dict = all_classical.copy()
            return
        if "all" in kwargs:
            if kwargs["all"]:
                self.classical_dict = all_classical.copy()
            else:
                self.classical_dict = no_classical.copy()

        for k, v in kwargs.items():
            if k in def_classical:
                self.classical_dict[k] = v
            else:
                raise UnknownClassicalModeError

    def num(
        self, count: Optional[int] = None, show: Optional[int] = None
    ) -> str:  # (;$count,$show)
        """
        Set the number to be used in other method calls.

        Returns count.

        Set show to False to return '' instead.

        """
        if count is not None:
            try:
                self.persistent_count = int(count)
            except ValueError as err:
                raise BadNumValueError from err
            if (show is None) or show:
                return str(count)
        else:
            self.persistent_count = None
        return ""

    def gender(self, gender: str) -> None:
        """
        set the gender for the singular of plural pronouns

        can be one of:
        'neuter'                ('they' -> 'it')
        'feminine'              ('they' -> 'she')
        'masculine'             ('they' -> 'he')
        'gender-neutral'        ('they' -> 'they')
        'feminine or masculine' ('they' -> 'she or he')
        'masculine or feminine' ('they' -> 'he or she')
        """
        if gender in singular_pronoun_genders:
            self.thegender = gender
        else:
            raise BadGenderError

    def _get_value_from_ast(self, obj):
        """
        Return the value of the ast object.
        """
        if isinstance(obj, ast.Num):
            return obj.n
        elif isinstance(obj, ast.Str):
            return obj.s
        elif isinstance(obj, ast.List):
            return [self._get_value_from_ast(e) for e in obj.elts]
        elif isinstance(obj, ast.Tuple):
            return tuple([self._get_value_from_ast(e) for e in obj.elts])

        # None, True and False are NameConstants in Py3.4 and above.
        elif isinstance(obj, ast.NameConstant):
            return obj.value

        # Probably passed a variable name.
        # Or passed a single word without wrapping it in quotes as an argument
        # ex: p.inflect("I plural(see)") instead of p.inflect("I plural('see')")
        raise NameError(f"name '{obj.id}' is not defined")

    def _string_to_substitute(
        self, mo: Match, methods_dict: Dict[str, Callable]
    ) -> str:
        """
        Return the string to be substituted for the match.
        """
        matched_text, f_name = mo.groups()
        # matched_text is the complete match string. e.g. plural_noun(cat)
        # f_name is the function name. e.g. plural_noun

        # Return matched_text if function name is not in methods_dict
        if f_name not in methods_dict:
            return matched_text

        # Parse the matched text
        a_tree = ast.parse(matched_text)

        # get the args and kwargs from ast objects
        args_list = [
            self._get_value_from_ast(a)
            for a in a_tree.body[0].value.args  # type: ignore[attr-defined]
        ]
        kwargs_list = {
            kw.arg: self._get_value_from_ast(kw.value)
            for kw in a_tree.body[0].value.keywords  # type: ignore[attr-defined]
        }

        # Call the corresponding function
        return methods_dict[f_name](*args_list, **kwargs_list)

    # 0. PERFORM GENERAL INFLECTIONS IN A STRING

    @typechecked
    def inflect(self, text: Word) -> str:
        """
        Perform inflections in a string.

        e.g. inflect('The plural of cat is plural(cat)') returns
        'The plural of cat is cats'

        can use plural, plural_noun, plural_verb, plural_adj,
        singular_noun, a, an, no, ordinal, number_to_words,
        and prespart

        """
        save_persistent_count = self.persistent_count

        # Dictionary of allowed methods
        methods_dict: Dict[str, Callable] = {
            "plural": self.plural,
            "plural_adj": self.plural_adj,
            "plural_noun": self.plural_noun,
            "plural_verb": self.plural_verb,
            "singular_noun": self.singular_noun,
            "a": self.a,
            "an": self.a,
            "no": self.no,
            "ordinal": self.ordinal,
            "number_to_words": self.number_to_words,
            "present_participle": self.present_participle,
            "num": self.num,
        }

        # Regular expression to find Python's function call syntax
        output = FUNCTION_CALL.sub(
            lambda mo: self._string_to_substitute(mo, methods_dict), text
        )
        self.persistent_count = save_persistent_count
        return output

    # ## PLURAL SUBROUTINES

    def postprocess(self, orig: str, inflected) -> str:
        inflected = str(inflected)
        if "|" in inflected:
            word_options = inflected.split("|")
            # When two parts of a noun need to be pluralized
            if len(word_options[0].split(" ")) == len(word_options[1].split(" ")):
                result = inflected.split("|")[self.classical_dict["all"]].split(" ")
            # When only the last part of the noun needs to be pluralized
            else:
                result = inflected.split(" ")
                for index, word in enumerate(result):
                    if "|" in word:
                        result[index] = word.split("|")[self.classical_dict["all"]]
        else:
            result = inflected.split(" ")

        # Try to fix word wise capitalization
        for index, word in enumerate(orig.split(" ")):
            if word == "I":
                # Is this the only word for exceptions like this
                # Where the original is fully capitalized
                # without 'meaning' capitalization?
                # Also this fails to handle a capitalizaion in context
                continue
            if word.capitalize() == word:
                result[index] = result[index].capitalize()
            if word == word.upper():
                result[index] = result[index].upper()
        return " ".join(result)

    def partition_word(self, text: str) -> Tuple[str, str, str]:
        mo = PARTITION_WORD.search(text)
        if mo:
            return mo.group(1), mo.group(2), mo.group(3)
        else:
            return "", "", ""

    @typechecked
    def plural(self, text: Word, count: Optional[Union[str, int, Any]] = None) -> str:
        """
        Return the plural of text.

        If count supplied, then return text if count is one of:
            1, a, an, one, each, every, this, that

        otherwise return the plural.

        Whitespace at the start and end is preserved.

        """
        pre, word, post = self.partition_word(text)
        if not word:
            return text
        plural = self.postprocess(
            word,
            self._pl_special_adjective(word, count)
            or self._pl_special_verb(word, count)
            or self._plnoun(word, count),
        )
        return f"{pre}{plural}{post}"

    @typechecked
    def plural_noun(
        self, text: Word, count: Optional[Union[str, int, Any]] = None
    ) -> str:
        """
        Return the plural of text, where text is a noun.

        If count supplied, then return text if count is one of:
            1, a, an, one, each, every, this, that

        otherwise return the plural.

        Whitespace at the start and end is preserved.

        """
        pre, word, post = self.partition_word(text)
        if not word:
            return text
        plural = self.postprocess(word, self._plnoun(word, count))
        return f"{pre}{plural}{post}"

    @typechecked
    def plural_verb(
        self, text: Word, count: Optional[Union[str, int, Any]] = None
    ) -> str:
        """
        Return the plural of text, where text is a verb.

        If count supplied, then return text if count is one of:
            1, a, an, one, each, every, this, that

        otherwise return the plural.

        Whitespace at the start and end is preserved.

        """
        pre, word, post = self.partition_word(text)
        if not word:
            return text
        plural = self.postprocess(
            word,
            self._pl_special_verb(word, count) or self._pl_general_verb(word, count),
        )
        return f"{pre}{plural}{post}"

    @typechecked
    def plural_adj(
        self, text: Word, count: Optional[Union[str, int, Any]] = None
    ) -> str:
        """
        Return the plural of text, where text is an adjective.

        If count supplied, then return text if count is one of:
            1, a, an, one, each, every, this, that

        otherwise return the plural.

        Whitespace at the start and end is preserved.

        """
        pre, word, post = self.partition_word(text)
        if not word:
            return text
        plural = self.postprocess(word, self._pl_special_adjective(word, count) or word)
        return f"{pre}{plural}{post}"

    @typechecked
    def compare(self, word1: Word, word2: Word) -> Union[str, bool]:
        """
        compare word1 and word2 for equality regardless of plurality

        return values:
        eq - the strings are equal
        p:s - word1 is the plural of word2
        s:p - word2 is the plural of word1
        p:p - word1 and word2 are two different plural forms of the one word
        False - otherwise

        >>> compare = engine().compare
        >>> compare("egg", "eggs")
        's:p'
        >>> compare('egg', 'egg')
        'eq'

        Words should not be empty.

        >>> compare('egg', '')
        Traceback (most recent call last):
        ...
        typeguard.TypeCheckError:...is not an instance of inflect.Word
        """
        norms = self.plural_noun, self.plural_verb, self.plural_adj
        results = (self._plequal(word1, word2, norm) for norm in norms)
        return next(filter(None, results), False)

    @typechecked
    def compare_nouns(self, word1: Word, word2: Word) -> Union[str, bool]:
        """
        compare word1 and word2 for equality regardless of plurality
        word1 and word2 are to be treated as nouns

        return values:
        eq - the strings are equal
        p:s - word1 is the plural of word2
        s:p - word2 is the plural of word1
        p:p - word1 and word2 are two different plural forms of the one word
        False - otherwise

        """
        return self._plequal(word1, word2, self.plural_noun)

    @typechecked
    def compare_verbs(self, word1: Word, word2: Word) -> Union[str, bool]:
        """
        compare word1 and word2 for equality regardless of plurality
        word1 and word2 are to be treated as verbs

        return values:
        eq - the strings are equal
        p:s - word1 is the plural of word2
        s:p - word2 is the plural of word1
        p:p - word1 and word2 are two different plural forms of the one word
        False - otherwise

        """
        return self._plequal(word1, word2, self.plural_verb)

    @typechecked
    def compare_adjs(self, word1: Word, word2: Word) -> Union[str, bool]:
        """
        compare word1 and word2 for equality regardless of plurality
        word1 and word2 are to be treated as adjectives

        return values:
        eq - the strings are equal
        p:s - word1 is the plural of word2
        s:p - word2 is the plural of word1
        p:p - word1 and word2 are two different plural forms of the one word
        False - otherwise

        """
        return self._plequal(word1, word2, self.plural_adj)

    @typechecked
    def singular_noun(
        self,
        text: Word,
        count: Optional[Union[int, str, Any]] = None,
        gender: Optional[str] = None,
    ) -> Union[str, Literal[False]]:
        """
        Return the singular of text, where text is a plural noun.

        If count supplied, then return the singular if count is one of:
            1, a, an, one, each, every, this, that or if count is None

        otherwise return text unchanged.

        Whitespace at the start and end is preserved.

        >>> p = engine()
        >>> p.singular_noun('horses')
        'horse'
        >>> p.singular_noun('knights')
        'knight'

        Returns False when a singular noun is passed.

        >>> p.singular_noun('horse')
        False
        >>> p.singular_noun('knight')
        False
        >>> p.singular_noun('soldier')
        False

        """
        pre, word, post = self.partition_word(text)
        if not word:
            return text
        sing = self._sinoun(word, count=count, gender=gender)
        if sing is not False:
            plural = self.postprocess(word, sing)
            return f"{pre}{plural}{post}"
        return False

    def _plequal(self, word1: str, word2: str, pl) -> Union[str, bool]:  # noqa: C901
        classval = self.classical_dict.copy()
        self.classical_dict = all_classical.copy()
        if word1 == word2:
            return "eq"
        if word1 == pl(word2):
            return "p:s"
        if pl(word1) == word2:
            return "s:p"
        self.classical_dict = no_classical.copy()
        if word1 == pl(word2):
            return "p:s"
        if pl(word1) == word2:
            return "s:p"
        self.classical_dict = classval.copy()

        if pl == self.plural or pl == self.plural_noun:
            if self._pl_check_plurals_N(word1, word2):
                return "p:p"
            if self._pl_check_plurals_N(word2, word1):
                return "p:p"
        if pl == self.plural or pl == self.plural_adj:
            if self._pl_check_plurals_adj(word1, word2):
                return "p:p"
        return False

    def _pl_reg_plurals(self, pair: str, stems: str, end1: str, end2: str) -> bool:
        pattern = rf"({stems})({end1}\|\1{end2}|{end2}\|\1{end1})"
        return bool(re.search(pattern, pair))

    def _pl_check_plurals_N(self, word1: str, word2: str) -> bool:
        stem_endings = (
            (pl_sb_C_a_ata, "as", "ata"),
            (pl_sb_C_is_ides, "is", "ides"),
            (pl_sb_C_a_ae, "s", "e"),
            (pl_sb_C_en_ina, "ens", "ina"),
            (pl_sb_C_um_a, "ums", "a"),
            (pl_sb_C_us_i, "uses", "i"),
            (pl_sb_C_on_a, "ons", "a"),
            (pl_sb_C_o_i_stems, "os", "i"),
            (pl_sb_C_ex_ices, "exes", "ices"),
            (pl_sb_C_ix_ices, "ixes", "ices"),
            (pl_sb_C_i, "s", "i"),
            (pl_sb_C_im, "s", "im"),
            (".*eau", "s", "x"),
            (".*ieu", "s", "x"),
            (".*tri", "xes", "ces"),
            (".{2,}[yia]n", "xes", "ges"),
        )

        words = map(Words, (word1, word2))
        pair = "|".join(word.last for word in words)

        return (
            pair in pl_sb_irregular_s.values()
            or pair in pl_sb_irregular.values()
            or pair in pl_sb_irregular_caps.values()
            or any(
                self._pl_reg_plurals(pair, stems, end1, end2)
                for stems, end1, end2 in stem_endings
            )
        )

    def _pl_check_plurals_adj(self, word1: str, word2: str) -> bool:
        word1a = word1[: word1.rfind("'")] if word1.endswith(("'s", "'")) else ""
        word2a = word2[: word2.rfind("'")] if word2.endswith(("'s", "'")) else ""

        return (
            bool(word1a)
            and bool(word2a)
            and (
                self._pl_check_plurals_N(word1a, word2a)
                or self._pl_check_plurals_N(word2a, word1a)
            )
        )

    def get_count(self, count: Optional[Union[str, int]] = None) -> Union[str, int]:
        if count is None and self.persistent_count is not None:
            count = self.persistent_count

        if count is not None:
            count = (
                1
                if (
                    (str(count) in pl_count_one)
                    or (
                        self.classical_dict["zero"]
                        and str(count).lower() in pl_count_zero
                    )
                )
                else 2
            )
        else:
            count = ""
        return count

    # @profile
    def _plnoun(  # noqa: C901
        self, word: str, count: Optional[Union[str, int]] = None
    ) -> str:
        count = self.get_count(count)

        # DEFAULT TO PLURAL

        if count == 1:
            return word

        # HANDLE USER-DEFINED NOUNS

        value = self.ud_match(word, self.pl_sb_user_defined)
        if value is not None:
            return value

        # HANDLE EMPTY WORD, SINGULAR COUNT AND UNINFLECTED PLURALS

        if word == "":
            return word

        word = Words(word)

        if word.last.lower() in pl_sb_uninflected_complete:
            if len(word.split_) >= 3:
                return self._handle_long_compounds(word, count=2) or word
            return word

        if word in pl_sb_uninflected_caps:
            return word

        for k, v in pl_sb_uninflected_bysize.items():
            if word.lowered[-k:] in v:
                return word

        if self.classical_dict["herd"] and word.last.lower() in pl_sb_uninflected_herd:
            return word

        # HANDLE COMPOUNDS ("Governor General", "mother-in-law", "aide-de-camp", ETC.)

        mo = PL_SB_POSTFIX_ADJ_STEMS_RE.search(word)
        if mo and mo.group(2) != "":
            return f"{self._plnoun(mo.group(1), 2)}{mo.group(2)}"

        if " a " in word.lowered or "-a-" in word.lowered:
            mo = PL_SB_PREP_DUAL_COMPOUND_RE.search(word)
            if mo and mo.group(2) != "" and mo.group(3) != "":
                return (
                    f"{self._plnoun(mo.group(1), 2)}"
                    f"{mo.group(2)}"
                    f"{self._plnoun(mo.group(3))}"
                )

        if len(word.split_) >= 3:
            handled_words = self._handle_long_compounds(word, count=2)
            if handled_words is not None:
                return handled_words

        # only pluralize denominators in units
        mo = DENOMINATOR.search(word.lowered)
        if mo:
            index = len(mo.group("denominator"))
            return f"{self._plnoun(word[:index])}{word[index:]}"

        # handle units given in degrees (only accept if
        # there is no more than one word following)
        # degree Celsius => degrees Celsius but degree
        # fahrenheit hour => degree fahrenheit hours
        if len(word.split_) >= 2 and word.split_[-2] == "degree":
            return " ".join([self._plnoun(word.first)] + word.split_[1:])

        with contextlib.suppress(ValueError):
            return self._handle_prepositional_phrase(
                word.lowered,
                functools.partial(self._plnoun, count=2),
                '-',
            )

        # HANDLE PRONOUNS

        for k, v in pl_pron_acc_keys_bysize.items():
            if word.lowered[-k:] in v:  # ends with accusative pronoun
                for pk, pv in pl_prep_bysize.items():
                    if word.lowered[:pk] in pv:  # starts with a prep
                        if word.lowered.split() == [
                            word.lowered[:pk],
                            word.lowered[-k:],
                        ]:
                            # only whitespace in between
                            return word.lowered[:-k] + pl_pron_acc[word.lowered[-k:]]

        try:
            return pl_pron_nom[word.lowered]
        except KeyError:
            pass

        try:
            return pl_pron_acc[word.lowered]
        except KeyError:
            pass

        # HANDLE ISOLATED IRREGULAR PLURALS

        if word.last in pl_sb_irregular_caps:
            llen = len(word.last)
            return f"{word[:-llen]}{pl_sb_irregular_caps[word.last]}"

        lowered_last = word.last.lower()
        if lowered_last in pl_sb_irregular:
            llen = len(lowered_last)
            return f"{word[:-llen]}{pl_sb_irregular[lowered_last]}"

        dash_split = word.lowered.split('-')
        if (" ".join(dash_split[-2:])).lower() in pl_sb_irregular_compound:
            llen = len(
                " ".join(dash_split[-2:])
            )  # TODO: what if 2 spaces between these words?
            return (
                f"{word[:-llen]}"
                f"{pl_sb_irregular_compound[(' '.join(dash_split[-2:])).lower()]}"
            )

        if word.lowered[-3:] == "quy":
            return f"{word[:-1]}ies"

        if word.lowered[-6:] == "person":
            if self.classical_dict["persons"]:
                return f"{word}s"
            else:
                return f"{word[:-4]}ople"

        # HANDLE FAMILIES OF IRREGULAR PLURALS

        if word.lowered[-3:] == "man":
            for k, v in pl_sb_U_man_mans_bysize.items():
                if word.lowered[-k:] in v:
                    return f"{word}s"
            for k, v in pl_sb_U_man_mans_caps_bysize.items():
                if word[-k:] in v:
                    return f"{word}s"
            return f"{word[:-3]}men"
        if word.lowered[-5:] == "mouse":
            return f"{word[:-5]}mice"
        if word.lowered[-5:] == "louse":
            v = pl_sb_U_louse_lice_bysize.get(len(word))
            if v and word.lowered in v:
                return f"{word[:-5]}lice"
            return f"{word}s"
        if word.lowered[-5:] == "goose":
            return f"{word[:-5]}geese"
        if word.lowered[-5:] == "tooth":
            return f"{word[:-5]}teeth"
        if word.lowered[-4:] == "foot":
            return f"{word[:-4]}feet"
        if word.lowered[-4:] == "taco":
            return f"{word[:-5]}tacos"

        if word.lowered == "die":
            return "dice"

        # HANDLE UNASSIMILATED IMPORTS

        if word.lowered[-4:] == "ceps":
            return word
        if word.lowered[-4:] == "zoon":
            return f"{word[:-2]}a"
        if word.lowered[-3:] in ("cis", "sis", "xis"):
            return f"{word[:-2]}es"

        for lastlet, d, numend, post in (
            ("h", pl_sb_U_ch_chs_bysize, None, "s"),
            ("x", pl_sb_U_ex_ices_bysize, -2, "ices"),
            ("x", pl_sb_U_ix_ices_bysize, -2, "ices"),
            ("m", pl_sb_U_um_a_bysize, -2, "a"),
            ("s", pl_sb_U_us_i_bysize, -2, "i"),
            ("n", pl_sb_U_on_a_bysize, -2, "a"),
            ("a", pl_sb_U_a_ae_bysize, None, "e"),
        ):
            if word.lowered[-1] == lastlet:  # this test to add speed
                for k, v in d.items():
                    if word.lowered[-k:] in v:
                        return word[:numend] + post

        # HANDLE INCOMPLETELY ASSIMILATED IMPORTS

        if self.classical_dict["ancient"]:
            if word.lowered[-4:] == "trix":
                return f"{word[:-1]}ces"
            if word.lowered[-3:] in ("eau", "ieu"):
                return f"{word}x"
            if word.lowered[-3:] in ("ynx", "inx", "anx") and len(word) > 4:
                return f"{word[:-1]}ges"

            for lastlet, d, numend, post in (
                ("n", pl_sb_C_en_ina_bysize, -2, "ina"),
                ("x", pl_sb_C_ex_ices_bysize, -2, "ices"),
                ("x", pl_sb_C_ix_ices_bysize, -2, "ices"),
                ("m", pl_sb_C_um_a_bysize, -2, "a"),
                ("s", pl_sb_C_us_i_bysize, -2, "i"),
                ("s", pl_sb_C_us_us_bysize, None, ""),
                ("a", pl_sb_C_a_ae_bysize, None, "e"),
                ("a", pl_sb_C_a_ata_bysize, None, "ta"),
                ("s", pl_sb_C_is_ides_bysize, -1, "des"),
                ("o", pl_sb_C_o_i_bysize, -1, "i"),
                ("n", pl_sb_C_on_a_bysize, -2, "a"),
            ):
                if word.lowered[-1] == lastlet:  # this test to add speed
                    for k, v in d.items():
                        if word.lowered[-k:] in v:
                            return word[:numend] + post

            for d, numend, post in (
                (pl_sb_C_i_bysize, None, "i"),
                (pl_sb_C_im_bysize, None, "im"),
            ):
                for k, v in d.items():
                    if word.lowered[-k:] in v:
                        return word[:numend] + post

        # HANDLE SINGULAR NOUNS ENDING IN ...s OR OTHER SILIBANTS

        if lowered_last in pl_sb_singular_s_complete:
            return f"{word}es"

        for k, v in pl_sb_singular_s_bysize.items():
            if word.lowered[-k:] in v:
                return f"{word}es"

        if word.lowered[-2:] == "es" and word[0] == word[0].upper():
            return f"{word}es"

        if word.lowered[-1] == "z":
            for k, v in pl_sb_z_zes_bysize.items():
                if word.lowered[-k:] in v:
                    return f"{word}es"

            if word.lowered[-2:-1] != "z":
                return f"{word}zes"

        if word.lowered[-2:] == "ze":
            for k, v in pl_sb_ze_zes_bysize.items():
                if word.lowered[-k:] in v:
                    return f"{word}s"

        if word.lowered[-2:] in ("ch", "sh", "zz", "ss") or word.lowered[-1] == "x":
            return f"{word}es"

        # HANDLE ...f -> ...ves

        if word.lowered[-3:] in ("elf", "alf", "olf"):
            return f"{word[:-1]}ves"
        if word.lowered[-3:] == "eaf" and word.lowered[-4:-3] != "d":
            return f"{word[:-1]}ves"
        if word.lowered[-4:] in ("nife", "life", "wife"):
            return f"{word[:-2]}ves"
        if word.lowered[-3:] == "arf":
            return f"{word[:-1]}ves"

        # HANDLE ...y

        if word.lowered[-1] == "y":
            if word.lowered[-2:-1] in "aeiou" or len(word) == 1:
                return f"{word}s"

            if self.classical_dict["names"]:
                if word.lowered[-1] == "y" and word[0] == word[0].upper():
                    return f"{word}s"

            return f"{word[:-1]}ies"

        # HANDLE ...o

        if lowered_last in pl_sb_U_o_os_complete:
            return f"{word}s"

        for k, v in pl_sb_U_o_os_bysize.items():
            if word.lowered[-k:] in v:
                return f"{word}s"

        if word.lowered[-2:] in ("ao", "eo", "io", "oo", "uo"):
            return f"{word}s"

        if word.lowered[-1] == "o":
            return f"{word}es"

        # OTHERWISE JUST ADD ...s

        return f"{word}s"

    @classmethod
    def _handle_prepositional_phrase(cls, phrase, transform, sep):
        """
        Given a word or phrase possibly separated by sep, parse out
        the prepositional phrase and apply the transform to the word
        preceding the prepositional phrase.

        Raise ValueError if the pivot is not found or if at least two
        separators are not found.

        >>> engine._handle_prepositional_phrase("man-of-war", str.upper, '-')
        'MAN-of-war'
        >>> engine._handle_prepositional_phrase("man of war", str.upper, ' ')
        'MAN of war'
        """
        parts = phrase.split(sep)
        if len(parts) < 3:
            raise ValueError("Cannot handle words with fewer than two separators")

        pivot = cls._find_pivot(parts, pl_prep_list_da)

        transformed = transform(parts[pivot - 1]) or parts[pivot - 1]
        return " ".join(
            parts[: pivot - 1] + [sep.join([transformed, parts[pivot], ''])]
        ) + " ".join(parts[(pivot + 1) :])

    def _handle_long_compounds(self, word: Words, count: int) -> Union[str, None]:
        """
        Handles the plural and singular for compound `Words` that
        have three or more words, based on the given count.

        >>> engine()._handle_long_compounds(Words("pair of scissors"), 2)
        'pairs of scissors'
        >>> engine()._handle_long_compounds(Words("men beyond hills"), 1)
        'man beyond hills'
        """
        inflection = self._sinoun if count == 1 else self._plnoun
        solutions = (  # type: ignore
            " ".join(
                itertools.chain(
                    leader,
                    [inflection(cand, count), prep],  # type: ignore
                    trailer,
                )
            )
            for leader, (cand, prep), trailer in windowed_complete(word.split_, 2)
            if prep in pl_prep_list_da  # type: ignore
        )
        return next(solutions, None)

    @staticmethod
    def _find_pivot(words, candidates):
        pivots = (
            index for index in range(1, len(words) - 1) if words[index] in candidates
        )
        try:
            return next(pivots)
        except StopIteration:
            raise ValueError("No pivot found") from None

    def _pl_special_verb(  # noqa: C901
        self, word: str, count: Optional[Union[str, int]] = None
    ) -> Union[str, bool]:
        if self.classical_dict["zero"] and str(count).lower() in pl_count_zero:
            return False
        count = self.get_count(count)

        if count == 1:
            return word

        # HANDLE USER-DEFINED VERBS

        value = self.ud_match(word, self.pl_v_user_defined)
        if value is not None:
            return value

        # HANDLE IRREGULAR PRESENT TENSE (SIMPLE AND COMPOUND)

        try:
            words = Words(word)
        except IndexError:
            return False  # word is ''

        if words.first in plverb_irregular_pres:
            return f"{plverb_irregular_pres[words.first]}{words[len(words.first) :]}"

        # HANDLE IRREGULAR FUTURE, PRETERITE AND PERFECT TENSES

        if words.first in plverb_irregular_non_pres:
            return word

        # HANDLE PRESENT NEGATIONS (SIMPLE AND COMPOUND)

        if words.first.endswith("n't") and words.first[:-3] in plverb_irregular_pres:
            return (
                f"{plverb_irregular_pres[words.first[:-3]]}n't"
                f"{words[len(words.first) :]}"
            )

        if words.first.endswith("n't"):
            return word

        # HANDLE SPECIAL CASES

        mo = PLVERB_SPECIAL_S_RE.search(word)
        if mo:
            return False
        if WHITESPACE.search(word):
            return False

        if words.lowered == "quizzes":
            return "quiz"

        # HANDLE STANDARD 3RD PERSON (CHOP THE ...(e)s OFF SINGLE WORDS)

        if (
            words.lowered[-4:] in ("ches", "shes", "zzes", "sses")
            or words.lowered[-3:] == "xes"
        ):
            return words[:-2]

        if words.lowered[-3:] == "ies" and len(words) > 3:
            return words.lowered[:-3] + "y"

        if (
            words.last.lower() in pl_v_oes_oe
            or words.lowered[-4:] in pl_v_oes_oe_endings_size4
            or words.lowered[-5:] in pl_v_oes_oe_endings_size5
        ):
            return words[:-1]

        if words.lowered.endswith("oes") and len(words) > 3:
            return words.lowered[:-2]

        mo = ENDS_WITH_S.search(words)
        if mo:
            return mo.group(1)

        # OTHERWISE, A REGULAR VERB (HANDLE ELSEWHERE)

        return False

    def _pl_general_verb(
        self, word: str, count: Optional[Union[str, int]] = None
    ) -> str:
        count = self.get_count(count)

        if count == 1:
            return word

        # HANDLE AMBIGUOUS PRESENT TENSES  (SIMPLE AND COMPOUND)

        mo = plverb_ambiguous_pres_keys.search(word)
        if mo:
            return f"{plverb_ambiguous_pres[mo.group(1).lower()]}{mo.group(2)}"

        # HANDLE AMBIGUOUS PRETERITE AND PERFECT TENSES

        mo = plverb_ambiguous_non_pres.search(word)
        if mo:
            return word

        # OTHERWISE, 1st OR 2ND PERSON IS UNINFLECTED

        return word

    def _pl_special_adjective(
        self, word: str, count: Optional[Union[str, int]] = None
    ) -> Union[str, bool]:
        count = self.get_count(count)

        if count == 1:
            return word

        # HANDLE USER-DEFINED ADJECTIVES

        value = self.ud_match(word, self.pl_adj_user_defined)
        if value is not None:
            return value

        # HANDLE KNOWN CASES

        mo = pl_adj_special_keys.search(word)
        if mo:
            return pl_adj_special[mo.group(1).lower()]

        # HANDLE POSSESSIVES

        mo = pl_adj_poss_keys.search(word)
        if mo:
            return pl_adj_poss[mo.group(1).lower()]

        mo = ENDS_WITH_APOSTROPHE_S.search(word)
        if mo:
            pl = self.plural_noun(mo.group(1))
            trailing_s = "" if pl[-1] == "s" else "s"
            return f"{pl}'{trailing_s}"

        # OTHERWISE, NO IDEA

        return False

    # @profile
    def _sinoun(  # noqa: C901
        self,
        word: str,
        count: Optional[Union[str, int]] = None,
        gender: Optional[str] = None,
    ) -> Union[str, bool]:
        count = self.get_count(count)

        # DEFAULT TO PLURAL

        if count == 2:
            return word

        # SET THE GENDER

        try:
            if gender is None:
                gender = self.thegender
            elif gender not in singular_pronoun_genders:
                raise BadGenderError
        except (TypeError, IndexError) as err:
            raise BadGenderError from err

        # HANDLE USER-DEFINED NOUNS

        value = self.ud_match(word, self.si_sb_user_defined)
        if value is not None:
            return value

        # HANDLE EMPTY WORD, SINGULAR COUNT AND UNINFLECTED PLURALS

        if word == "":
            return word

        if word in si_sb_ois_oi_case:
            return word[:-1]

        words = Words(word)

        if words.last.lower() in pl_sb_uninflected_complete:
            if len(words.split_) >= 3:
                return self._handle_long_compounds(words, count=1) or word
            return word

        if word in pl_sb_uninflected_caps:
            return word

        for k, v in pl_sb_uninflected_bysize.items():
            if words.lowered[-k:] in v:
                return word

        if self.classical_dict["herd"] and words.last.lower() in pl_sb_uninflected_herd:
            return word

        if words.last.lower() in pl_sb_C_us_us:
            return word if self.classical_dict["ancient"] else False

        # HANDLE COMPOUNDS ("Governor General", "mother-in-law", "aide-de-camp", ETC.)

        mo = PL_SB_POSTFIX_ADJ_STEMS_RE.search(word)
        if mo and mo.group(2) != "":
            return f"{self._sinoun(mo.group(1), 1, gender=gender)}{mo.group(2)}"

        with contextlib.suppress(ValueError):
            return self._handle_prepositional_phrase(
                words.lowered,
                functools.partial(self._sinoun, count=1, gender=gender),
                ' ',
            )

        with contextlib.suppress(ValueError):
            return self._handle_prepositional_phrase(
                words.lowered,
                functools.partial(self._sinoun, count=1, gender=gender),
                '-',
            )

        # HANDLE PRONOUNS

        for k, v in si_pron_acc_keys_bysize.items():
            if words.lowered[-k:] in v:  # ends with accusative pronoun
                for pk, pv in pl_prep_bysize.items():
                    if words.lowered[:pk] in pv:  # starts with a prep
                        if words.lowered.split() == [
                            words.lowered[:pk],
                            words.lowered[-k:],
                        ]:
                            # only whitespace in between
                            return words.lowered[:-k] + get_si_pron(
                                "acc", words.lowered[-k:], gender
                            )

        try:
            return get_si_pron("nom", words.lowered, gender)
        except KeyError:
            pass

        try:
            return get_si_pron("acc", words.lowered, gender)
        except KeyError:
            pass

        # HANDLE ISOLATED IRREGULAR PLURALS

        if words.last in si_sb_irregular_caps:
            llen = len(words.last)
            return f"{word[:-llen]}{si_sb_irregular_caps[words.last]}"

        if words.last.lower() in si_sb_irregular:
            llen = len(words.last.lower())
            return f"{word[:-llen]}{si_sb_irregular[words.last.lower()]}"

        dash_split = words.lowered.split("-")
        if (" ".join(dash_split[-2:])).lower() in si_sb_irregular_compound:
            llen = len(
                " ".join(dash_split[-2:])
            )  # TODO: what if 2 spaces between these words?
            return "{}{}".format(
                word[:-llen],
                si_sb_irregular_compound[(" ".join(dash_split[-2:])).lower()],
            )

        if words.lowered[-5:] == "quies":
            return word[:-3] + "y"

        if words.lowered[-7:] == "persons":
            return word[:-1]
        if words.lowered[-6:] == "people":
            return word[:-4] + "rson"

        # HANDLE FAMILIES OF IRREGULAR PLURALS

        if words.lowered[-4:] == "mans":
            for k, v in si_sb_U_man_mans_bysize.items():
                if words.lowered[-k:] in v:
                    return word[:-1]
            for k, v in si_sb_U_man_mans_caps_bysize.items():
                if word[-k:] in v:
                    return word[:-1]
        if words.lowered[-3:] == "men":
            return word[:-3] + "man"
        if words.lowered[-4:] == "mice":
            return word[:-4] + "mouse"
        if words.lowered[-4:] == "lice":
            v = si_sb_U_louse_lice_bysize.get(len(word))
            if v and words.lowered in v:
                return word[:-4] + "louse"
        if words.lowered[-5:] == "geese":
            return word[:-5] + "goose"
        if words.lowered[-5:] == "teeth":
            return word[:-5] + "tooth"
        if words.lowered[-4:] == "feet":
            return word[:-4] + "foot"

        if words.lowered == "dice":
            return "die"

        # HANDLE UNASSIMILATED IMPORTS

        if words.lowered[-4:] == "ceps":
            return word
        if words.lowered[-3:] == "zoa":
            return word[:-1] + "on"

        for lastlet, d, unass_numend, post in (
            ("s", si_sb_U_ch_chs_bysize, -1, ""),
            ("s", si_sb_U_ex_ices_bysize, -4, "ex"),
            ("s", si_sb_U_ix_ices_bysize, -4, "ix"),
            ("a", si_sb_U_um_a_bysize, -1, "um"),
            ("i", si_sb_U_us_i_bysize, -1, "us"),
            ("a", si_sb_U_on_a_bysize, -1, "on"),
            ("e", si_sb_U_a_ae_bysize, -1, ""),
        ):
            if words.lowered[-1] == lastlet:  # this test to add speed
                for k, v in d.items():
                    if words.lowered[-k:] in v:
                        return word[:unass_numend] + post

        # HANDLE INCOMPLETELY ASSIMILATED IMPORTS

        if self.classical_dict["ancient"]:
            if words.lowered[-6:] == "trices":
                return word[:-3] + "x"
            if words.lowered[-4:] in ("eaux", "ieux"):
                return word[:-1]
            if words.lowered[-5:] in ("ynges", "inges", "anges") and len(word) > 6:
                return word[:-3] + "x"

            for lastlet, d, class_numend, post in (
                ("a", si_sb_C_en_ina_bysize, -3, "en"),
                ("s", si_sb_C_ex_ices_bysize, -4, "ex"),
                ("s", si_sb_C_ix_ices_bysize, -4, "ix"),
                ("a", si_sb_C_um_a_bysize, -1, "um"),
                ("i", si_sb_C_us_i_bysize, -1, "us"),
                ("s", pl_sb_C_us_us_bysize, None, ""),
                ("e", si_sb_C_a_ae_bysize, -1, ""),
                ("a", si_sb_C_a_ata_bysize, -2, ""),
                ("s", si_sb_C_is_ides_bysize, -3, "s"),
                ("i", si_sb_C_o_i_bysize, -1, "o"),
                ("a", si_sb_C_on_a_bysize, -1, "on"),
                ("m", si_sb_C_im_bysize, -2, ""),
                ("i", si_sb_C_i_bysize, -1, ""),
            ):
                if words.lowered[-1] == lastlet:  # this test to add speed
                    for k, v in d.items():
                        if words.lowered[-k:] in v:
                            return word[:class_numend] + post

        # HANDLE PLURLS ENDING IN uses -> use

        if (
            words.lowered[-6:] == "houses"
            or word in si_sb_uses_use_case
            or words.last.lower() in si_sb_uses_use
        ):
            return word[:-1]

        # HANDLE PLURLS ENDING IN ies -> ie

        if word in si_sb_ies_ie_case or words.last.lower() in si_sb_ies_ie:
            return word[:-1]

        # HANDLE PLURLS ENDING IN oes -> oe

        if (
            words.lowered[-5:] == "shoes"
            or word in si_sb_oes_oe_case
            or words.last.lower() in si_sb_oes_oe
        ):
            return word[:-1]

        # HANDLE SINGULAR NOUNS ENDING IN ...s OR OTHER SILIBANTS

        if word in si_sb_sses_sse_case or words.last.lower() in si_sb_sses_sse:
            return word[:-1]

        if words.last.lower() in si_sb_singular_s_complete:
            return word[:-2]

        for k, v in si_sb_singular_s_bysize.items():
            if words.lowered[-k:] in v:
                return word[:-2]

        if words.lowered[-4:] == "eses" and word[0] == word[0].upper():
            return word[:-2]

        if words.last.lower() in si_sb_z_zes:
            return word[:-2]

        if words.last.lower() in si_sb_zzes_zz:
            return word[:-2]

        if words.lowered[-4:] == "zzes":
            return word[:-3]

        if word in si_sb_ches_che_case or words.last.lower() in si_sb_ches_che:
            return word[:-1]

        if words.lowered[-4:] in ("ches", "shes"):
            return word[:-2]

        if words.last.lower() in si_sb_xes_xe:
            return word[:-1]

        if words.lowered[-3:] == "xes":
            return word[:-2]

        # HANDLE ...f -> ...ves

        if word in si_sb_ves_ve_case or words.last.lower() in si_sb_ves_ve:
            return word[:-1]

        if words.lowered[-3:] == "ves":
            if words.lowered[-5:-3] in ("el", "al", "ol"):
                return word[:-3] + "f"
            if words.lowered[-5:-3] == "ea" and word[-6:-5] != "d":
                return word[:-3] + "f"
            if words.lowered[-5:-3] in ("ni", "li", "wi"):
                return word[:-3] + "fe"
            if words.lowered[-5:-3] == "ar":
                return word[:-3] + "f"

        # HANDLE ...y

        if words.lowered[-2:] == "ys":
            if len(words.lowered) > 2 and words.lowered[-3] in "aeiou":
                return word[:-1]

            if self.classical_dict["names"]:
                if words.lowered[-2:] == "ys" and word[0] == word[0].upper():
                    return word[:-1]

        if words.lowered[-3:] == "ies":
            return word[:-3] + "y"

        # HANDLE ...o

        if words.lowered[-2:] == "os":
            if words.last.lower() in si_sb_U_o_os_complete:
                return word[:-1]

            for k, v in si_sb_U_o_os_bysize.items():
                if words.lowered[-k:] in v:
                    return word[:-1]

            if words.lowered[-3:] in ("aos", "eos", "ios", "oos", "uos"):
                return word[:-1]

        if words.lowered[-3:] == "oes":
            return word[:-2]

        # UNASSIMILATED IMPORTS FINAL RULE

        if word in si_sb_es_is:
            return word[:-2] + "is"

        # OTHERWISE JUST REMOVE ...s

        if words.lowered[-1] == "s":
            return word[:-1]

        # COULD NOT FIND SINGULAR

        return False

    # ADJECTIVES

    @typechecked
    def a(self, text: Word, count: Optional[Union[int, str, Any]] = 1) -> str:
        """
        Return the appropriate indefinite article followed by text.

        The indefinite article is either 'a' or 'an'.

        If count is not one, then return count followed by text
        instead of 'a' or 'an'.

        Whitespace at the start and end is preserved.

        """
        mo = INDEFINITE_ARTICLE_TEST.search(text)
        if mo:
            word = mo.group(2)
            if not word:
                return text
            pre = mo.group(1)
            post = mo.group(3)
            result = self._indef_article(word, count)
            return f"{pre}{result}{post}"
        return ""

    an = a

    _indef_article_cases = (
        # HANDLE ORDINAL FORMS
        (A_ordinal_a, "a"),
        (A_ordinal_an, "an"),
        # HANDLE SPECIAL CASES
        (A_explicit_an, "an"),
        (SPECIAL_AN, "an"),
        (SPECIAL_A, "a"),
        # HANDLE ABBREVIATIONS
        (A_abbrev, "an"),
        (SPECIAL_ABBREV_AN, "an"),
        (SPECIAL_ABBREV_A, "a"),
        # HANDLE CONSONANTS
        (CONSONANTS, "a"),
        # HANDLE SPECIAL VOWEL-FORMS
        (ARTICLE_SPECIAL_EU, "a"),
        (ARTICLE_SPECIAL_ONCE, "a"),
        (ARTICLE_SPECIAL_ONETIME, "a"),
        (ARTICLE_SPECIAL_UNIT, "a"),
        (ARTICLE_SPECIAL_UBA, "a"),
        (ARTICLE_SPECIAL_UKR, "a"),
        (A_explicit_a, "a"),
        # HANDLE SPECIAL CAPITALS
        (SPECIAL_CAPITALS, "a"),
        # HANDLE VOWELS
        (VOWELS, "an"),
        # HANDLE y...
        # (BEFORE CERTAIN CONSONANTS IMPLIES (UNNATURALIZED) "i.." SOUND)
        (A_y_cons, "an"),
    )

    def _indef_article(self, word: str, count: Union[int, str, Any]) -> str:
        mycount = self.get_count(count)

        if mycount != 1:
            return f"{count} {word}"

        # HANDLE USER-DEFINED VARIANTS

        value = self.ud_match(word, self.A_a_user_defined)
        if value is not None:
            return f"{value} {word}"

        matches = (
            f'{article} {word}'
            for regexen, article in self._indef_article_cases
            if regexen.search(word)
        )

        # OTHERWISE, GUESS "a"
        fallback = f'a {word}'
        return next(matches, fallback)

    # 2. TRANSLATE ZERO-QUANTIFIED $word TO "no plural($word)"

    @typechecked
    def no(self, text: Word, count: Optional[Union[int, str]] = None) -> str:
        """
        If count is 0, no, zero or nil, return 'no' followed by the plural
        of text.

        If count is one of:
            1, a, an, one, each, every, this, that
            return count followed by text.

        Otherwise return count follow by the plural of text.

        In the return value count is always followed by a space.

        Whitespace at the start and end is preserved.

        """
        if count is None and self.persistent_count is not None:
            count = self.persistent_count

        if count is None:
            count = 0
        mo = PARTITION_WORD.search(text)
        if mo:
            pre = mo.group(1)
            word = mo.group(2)
            post = mo.group(3)
        else:
            pre = ""
            word = ""
            post = ""

        if str(count).lower() in pl_count_zero:
            count = 'no'
        return f"{pre}{count} {self.plural(word, count)}{post}"

    # PARTICIPLES

    @typechecked
    def present_participle(self, word: Word) -> str:
        """
        Return the present participle for word.

        word is the 3rd person singular verb.

        """
        plv = self.plural_verb(word, 2)
        ans = plv

        for regexen, repl in PRESENT_PARTICIPLE_REPLACEMENTS:
            ans, num = regexen.subn(repl, plv)
            if num:
                return f"{ans}ing"
        return f"{ans}ing"

    # NUMERICAL INFLECTIONS

    @typechecked
    def ordinal(self, num: Union[Number, Word]) -> str:
        """
        Return the ordinal of num.

        >>> ordinal = engine().ordinal
        >>> ordinal(1)
        '1st'
        >>> ordinal('one')
        'first'
        """
        if DIGIT.match(str(num)):
            if isinstance(num, (float, int)) and int(num) == num:
                n = int(num)
            else:
                if "." in str(num):
                    try:
                        # numbers after decimal,
                        # so only need last one for ordinal
                        n = int(str(num)[-1])

                    except ValueError:  # ends with '.', so need to use whole string
                        n = int(str(num)[:-1])
                else:
                    n = int(num)  # type: ignore
            try:
                post = nth[n % 100]
            except KeyError:
                post = nth[n % 10]
            return f"{num}{post}"
        else:
            return self._sub_ord(num)

    def millfn(self, ind: int = 0) -> str:
        if ind > len(mill) - 1:
            raise NumOutOfRangeError
        return mill[ind]

    def unitfn(self, units: int, mindex: int = 0) -> str:
        return f"{unit[units]}{self.millfn(mindex)}"

    def tenfn(self, tens, units, mindex=0) -> str:
        if tens != 1:
            tens_part = ten[tens]
            if tens and units:
                hyphen = "-"
            else:
                hyphen = ""
            unit_part = unit[units]
            mill_part = self.millfn(mindex)
            return f"{tens_part}{hyphen}{unit_part}{mill_part}"
        return f"{teen[units]}{mill[mindex]}"

    def hundfn(self, hundreds: int, tens: int, units: int, mindex: int) -> str:
        if hundreds:
            andword = f" {self._number_args['andword']} " if tens or units else ""
            # use unit not unitfn as simpler
            return (
                f"{unit[hundreds]} hundred{andword}"
                f"{self.tenfn(tens, units)}{self.millfn(mindex)}, "
            )
        if tens or units:
            return f"{self.tenfn(tens, units)}{self.millfn(mindex)}, "
        return ""

    def group1sub(self, mo: Match) -> str:
        units = int(mo.group(1))
        if units == 1:
            return f" {self._number_args['one']}, "
        elif units:
            return f"{unit[units]}, "
        else:
            return f" {self._number_args['zero']}, "

    def group1bsub(self, mo: Match) -> str:
        units = int(mo.group(1))
        if units:
            return f"{unit[units]}, "
        else:
            return f" {self._number_args['zero']}, "

    def group2sub(self, mo: Match) -> str:
        tens = int(mo.group(1))
        units = int(mo.group(2))
        if tens:
            return f"{self.tenfn(tens, units)}, "
        if units:
            return f" {self._number_args['zero']} {unit[units]}, "
        return f" {self._number_args['zero']} {self._number_args['zero']}, "

    def group3sub(self, mo: Match) -> str:
        hundreds = int(mo.group(1))
        tens = int(mo.group(2))
        units = int(mo.group(3))
        if hundreds == 1:
            hunword = f" {self._number_args['one']}"
        elif hundreds:
            hunword = str(unit[hundreds])
        else:
            hunword = f" {self._number_args['zero']}"
        if tens:
            tenword = self.tenfn(tens, units)
        elif units:
            tenword = f" {self._number_args['zero']} {unit[units]}"
        else:
            tenword = f" {self._number_args['zero']} {self._number_args['zero']}"
        return f"{hunword} {tenword}, "

    def hundsub(self, mo: Match) -> str:
        ret = self.hundfn(
            int(mo.group(1)), int(mo.group(2)), int(mo.group(3)), self.mill_count
        )
        self.mill_count += 1
        return ret

    def tensub(self, mo: Match) -> str:
        return f"{self.tenfn(int(mo.group(1)), int(mo.group(2)), self.mill_count)}, "

    def unitsub(self, mo: Match) -> str:
        return f"{self.unitfn(int(mo.group(1)), self.mill_count)}, "

    def enword(self, num: str, group: int) -> str:
        # import pdb
        # pdb.set_trace()

        if group == 1:
            num = DIGIT_GROUP.sub(self.group1sub, num)
        elif group == 2:
            num = TWO_DIGITS.sub(self.group2sub, num)
            num = DIGIT_GROUP.sub(self.group1bsub, num, 1)
        elif group == 3:
            num = THREE_DIGITS.sub(self.group3sub, num)
            num = TWO_DIGITS.sub(self.group2sub, num, 1)
            num = DIGIT_GROUP.sub(self.group1sub, num, 1)
        elif int(num) == 0:
            num = self._number_args["zero"]
        elif int(num) == 1:
            num = self._number_args["one"]
        else:
            num = num.lstrip().lstrip("0")
            self.mill_count = 0
            # surely there's a better way to do the next bit
            mo = THREE_DIGITS_WORD.search(num)
            while mo:
                num = THREE_DIGITS_WORD.sub(self.hundsub, num, 1)
                mo = THREE_DIGITS_WORD.search(num)
            num = TWO_DIGITS_WORD.sub(self.tensub, num, 1)
            num = ONE_DIGIT_WORD.sub(self.unitsub, num, 1)
        return num

    @staticmethod
    def _sub_ord(val):
        new = ordinal_suff.sub(lambda match: ordinal[match.group(1)], val)
        return new + "th" * (new == val)

    @classmethod
    def _chunk_num(cls, num, decimal, group):
        if decimal:
            max_split = -1 if group != 0 else 1
            chunks = num.split(".", max_split)
        else:
            chunks = [num]
        return cls._remove_last_blank(chunks)

    @staticmethod
    def _remove_last_blank(chunks):
        """
        Remove the last item from chunks if it's a blank string.

        Return the resultant chunks and whether the last item was removed.
        """
        removed = chunks[-1] == ""
        result = chunks[:-1] if removed else chunks
        return result, removed

    @staticmethod
    def _get_sign(num):
        return {'+': 'plus', '-': 'minus'}.get(num.lstrip()[0], '')

    @typechecked
    def number_to_words(  # noqa: C901
        self,
        num: Union[Number, Word],
        wantlist: bool = False,
        group: int = 0,
        comma: Union[Falsish, str] = ",",
        andword: str = "and",
        zero: str = "zero",
        one: str = "one",
        decimal: Union[Falsish, str] = "point",
        threshold: Optional[int] = None,
    ) -> Union[str, List[str]]:
        """
        Return a number in words.

        group = 1, 2 or 3 to group numbers before turning into words
        comma: define comma

        andword:
            word for 'and'. Can be set to ''.
            e.g. "one hundred and one" vs "one hundred one"

        zero: word for '0'
        one: word for '1'
        decimal: word for decimal point
        threshold: numbers above threshold not turned into words

        parameters not remembered from last call. Departure from Perl version.
        """
        self._number_args = {"andword": andword, "zero": zero, "one": one}
        num = str(num)

        # Handle "stylistic" conversions (up to a given threshold)...
        if threshold is not None and float(num) > threshold:
            spnum = num.split(".", 1)
            while comma:
                (spnum[0], n) = FOUR_DIGIT_COMMA.subn(r"\1,\2", spnum[0])
                if n == 0:
                    break
            try:
                return f"{spnum[0]}.{spnum[1]}"
            except IndexError:
                return str(spnum[0])

        if group < 0 or group > 3:
            raise BadChunkingOptionError

        sign = self._get_sign(num)

        if num in nth_suff:
            num = zero

        myord = num[-2:] in nth_suff
        if myord:
            num = num[:-2]

        chunks, finalpoint = self._chunk_num(num, decimal, group)

        loopstart = chunks[0] == ""
        first: bool | None = not loopstart

        def _handle_chunk(chunk):
            nonlocal first

            # remove all non numeric \D
            chunk = NON_DIGIT.sub("", chunk)
            if chunk == "":
                chunk = "0"

            if group == 0 and not first:
                chunk = self.enword(chunk, 1)
            else:
                chunk = self.enword(chunk, group)

            if chunk[-2:] == ", ":
                chunk = chunk[:-2]
            chunk = WHITESPACES_COMMA.sub(",", chunk)

            if group == 0 and first:
                chunk = COMMA_WORD.sub(f" {andword} \\1", chunk)
            chunk = WHITESPACES.sub(" ", chunk)
            # chunk = re.sub(r"(\A\s|\s\Z)", self.blankfn, chunk)
            chunk = chunk.strip()
            if first:
                first = None
            return chunk

        chunks[loopstart:] = map(_handle_chunk, chunks[loopstart:])

        numchunks = []
        if first != 0:
            numchunks = chunks[0].split(f"{comma} ")

        if myord and numchunks:
            numchunks[-1] = self._sub_ord(numchunks[-1])

        for chunk in chunks[1:]:
            numchunks.append(decimal)
            numchunks.extend(chunk.split(f"{comma} "))

        if finalpoint:
            numchunks.append(decimal)

        if wantlist:
            return [sign] * bool(sign) + numchunks

        signout = f"{sign} " if sign else ""
        valout = (
            ', '.join(numchunks)
            if group
            else ''.join(self._render(numchunks, decimal, comma))
        )
        return signout + valout

    @staticmethod
    def _render(chunks, decimal, comma):
        first_item = chunks.pop(0)
        yield first_item
        first = decimal is None or not first_item.endswith(decimal)
        for nc in chunks:
            if nc == decimal:
                first = False
            elif first:
                yield comma
            yield f" {nc}"

    @typechecked
    def join(
        self,
        words: Optional[Sequence[Word]],
        sep: Optional[str] = None,
        sep_spaced: bool = True,
        final_sep: Optional[str] = None,
        conj: str = "and",
        conj_spaced: bool = True,
    ) -> str:
        """
        Join words into a list.

        e.g. join(['ant', 'bee', 'fly']) returns 'ant, bee, and fly'

        options:
        conj: replacement for 'and'
        sep: separator. default ',', unless ',' is in the list then ';'
        final_sep: final separator. default ',', unless ',' is in the list then ';'
        conj_spaced: boolean. Should conj have spaces around it

        """
        if not words:
            return ""
        if len(words) == 1:
            return words[0]

        if conj_spaced:
            if conj == "":
                conj = " "
            else:
                conj = f" {conj} "

        if len(words) == 2:
            return f"{words[0]}{conj}{words[1]}"

        if sep is None:
            if "," in "".join(words):
                sep = ";"
            else:
                sep = ","
        if final_sep is None:
            final_sep = sep

        final_sep = f"{final_sep}{conj}"

        if sep_spaced:
            sep += " "

        return f"{sep.join(words[0:-1])}{final_sep}{words[-1]}"