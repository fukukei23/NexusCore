
# === NexusCore/openenv\Lib\site-packages\termcolor\termcolor.py ===
# Copyright (c) 2008-2011 Volvox Development Team
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Author: Konstantin Lepa <konstantin.lepa@gmail.com>

"""ANSI color formatting for output in terminal."""

from __future__ import annotations

import os
import sys
import warnings
from typing import Any, Iterable


def __getattr__(name: str) -> list[str]:
    if name == "__ALL__":
        warnings.warn(
            "__ALL__ is deprecated and will be removed in termcolor 3. "
            "Use __all__ instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return ["colored", "cprint"]
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)


ATTRIBUTES = {
    "bold": 1,
    "dark": 2,
    "underline": 4,
    "blink": 5,
    "reverse": 7,
    "concealed": 8,
}


HIGHLIGHTS = {
    "on_black": 40,
    "on_grey": 40,  # Actually black but kept for backwards compatibility
    "on_red": 41,
    "on_green": 42,
    "on_yellow": 43,
    "on_blue": 44,
    "on_magenta": 45,
    "on_cyan": 46,
    "on_light_grey": 47,
    "on_dark_grey": 100,
    "on_light_red": 101,
    "on_light_green": 102,
    "on_light_yellow": 103,
    "on_light_blue": 104,
    "on_light_magenta": 105,
    "on_light_cyan": 106,
    "on_white": 107,
}

COLORS = {
    "black": 30,
    "grey": 30,  # Actually black but kept for backwards compatibility
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "light_grey": 37,
    "dark_grey": 90,
    "light_red": 91,
    "light_green": 92,
    "light_yellow": 93,
    "light_blue": 94,
    "light_magenta": 95,
    "light_cyan": 96,
    "white": 97,
}


RESET = "\033[0m"


def _can_do_colour(
    *, no_color: bool | None = None, force_color: bool | None = None
) -> bool:
    """Check env vars and for tty/dumb terminal"""
    # First check overrides:
    # "User-level configuration files and per-instance command-line arguments should
    # override $NO_COLOR. A user should be able to export $NO_COLOR in their shell
    # configuration file as a default, but configure a specific program in its
    # configuration file to specifically enable color."
    # https://no-color.org
    if no_color is not None and no_color:
        return False
    if force_color is not None and force_color:
        return True

    # Then check env vars:
    if "ANSI_COLORS_DISABLED" in os.environ:
        return False
    if "NO_COLOR" in os.environ:
        return False
    if "FORCE_COLOR" in os.environ:
        return True
    return (
        hasattr(sys.stdout, "isatty")
        and sys.stdout.isatty()
        and os.environ.get("TERM") != "dumb"
    )


def colored(
    text: str,
    color: str | None = None,
    on_color: str | None = None,
    attrs: Iterable[str] | None = None,
    *,
    no_color: bool | None = None,
    force_color: bool | None = None,
) -> str:
    """Colorize text.

    Available text colors:
        black, red, green, yellow, blue, magenta, cyan, white,
        light_grey, dark_grey, light_red, light_green, light_yellow, light_blue,
        light_magenta, light_cyan.

    Available text highlights:
        on_black, on_red, on_green, on_yellow, on_blue, on_magenta, on_cyan, on_white,
        on_light_grey, on_dark_grey, on_light_red, on_light_green, on_light_yellow,
        on_light_blue, on_light_magenta, on_light_cyan.

    Available attributes:
        bold, dark, underline, blink, reverse, concealed.

    Example:
        colored('Hello, World!', 'red', 'on_black', ['bold', 'blink'])
        colored('Hello, World!', 'green')
    """
    if not _can_do_colour(no_color=no_color, force_color=force_color):
        return text

    fmt_str = "\033[%dm%s"
    if color is not None:
        text = fmt_str % (COLORS[color], text)

    if on_color is not None:
        text = fmt_str % (HIGHLIGHTS[on_color], text)

    if attrs is not None:
        for attr in attrs:
            text = fmt_str % (ATTRIBUTES[attr], text)

    return text + RESET


def cprint(
    text: str,
    color: str | None = None,
    on_color: str | None = None,
    attrs: Iterable[str] | None = None,
    *,
    no_color: bool | None = None,
    force_color: bool | None = None,
    **kwargs: Any,
) -> None:
    """Print colorized text.

    It accepts arguments of print function.
    """

    print(
        (
            colored(
                text,
                color,
                on_color,
                attrs,
                no_color=no_color,
                force_color=force_color,
            )
        ),
        **kwargs,
    )

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\attach_script.py ===
def get_main_thread_instance(threading):
    if hasattr(threading, "main_thread"):
        return threading.main_thread()
    else:
        # On Python 2 we don't really have an API to get the main thread,
        # so, we just get it from the 'shutdown' bound method.
        return threading._shutdown.im_self


def get_main_thread_id(unlikely_thread_id=None):
    """
    :param unlikely_thread_id:
        Pass to mark some thread id as not likely the main thread.

    :return tuple(thread_id, critical_warning)
    """
    import sys
    import os

    current_frames = sys._current_frames()
    possible_thread_ids = []
    for thread_ident, frame in current_frames.items():
        while frame.f_back is not None:
            frame = frame.f_back

        basename = os.path.basename(frame.f_code.co_filename)
        if basename.endswith((".pyc", ".pyo")):
            basename = basename[:-1]

        if (frame.f_code.co_name, basename) in [
            ("_run_module_as_main", "runpy.py"),
            ("_run_module_as_main", "<frozen runpy>"),
            ("run_module_as_main", "runpy.py"),
            ("run_module", "runpy.py"),
            ("run_path", "runpy.py"),
        ]:
            # This is the case for python -m <module name> (this is an ideal match, so,
            # let's return it).
            return thread_ident, ""

        if frame.f_code.co_name == "<module>":
            if frame.f_globals.get("__name__") == "__main__":
                possible_thread_ids.insert(0, thread_ident)  # Add with higher priority
                continue

            # Usually the main thread will be started in the <module>, whereas others would
            # be started in another place (but when Python is embedded, this may not be
            # correct, so, just add to the available possibilities as we'll have to choose
            # one if there are multiple).
            possible_thread_ids.append(thread_ident)

    if len(possible_thread_ids) > 0:
        if len(possible_thread_ids) == 1:
            return possible_thread_ids[0], ""  # Ideal: only one match

        while unlikely_thread_id in possible_thread_ids:
            possible_thread_ids.remove(unlikely_thread_id)

        if len(possible_thread_ids) == 1:
            return possible_thread_ids[0], ""  # Ideal: only one match

        elif len(possible_thread_ids) > 1:
            # Bad: we can't really be certain of anything at this point.
            return possible_thread_ids[0], "Multiple thread ids found (%s). Choosing main thread id randomly (%s)." % (
                possible_thread_ids,
                possible_thread_ids[0],
            )

    # If we got here we couldn't discover the main thread id.
    return None, "Unable to discover main thread id."


def fix_main_thread_id(on_warn=lambda msg: None, on_exception=lambda msg: None, on_critical=lambda msg: None):
    # This means that we weren't able to import threading in the main thread (which most
    # likely means that the main thread is paused or in some very long operation).
    # In this case we'll import threading here and hotfix what may be wrong in the threading
    # module (if we're on Windows where we create a thread to do the attach and on Linux
    # we are not certain on which thread we're executing this code).
    #
    # The code below is a workaround for https://bugs.python.org/issue37416
    import sys
    import threading

    # This is no longer needed in Py 3.13 (as the related issue is already fixed).
    if sys.version_info[:2] >= (3, 13):
        return

    try:
        with threading._active_limbo_lock:
            main_thread_instance = get_main_thread_instance(threading)

            if sys.platform == "win32":
                # On windows this code would be called in a secondary thread, so,
                # the current thread is unlikely to be the main thread.
                if hasattr(threading, "_get_ident"):
                    unlikely_thread_id = threading._get_ident()  # py2
                else:
                    unlikely_thread_id = threading.get_ident()  # py3
            else:
                unlikely_thread_id = None

            main_thread_id, critical_warning = get_main_thread_id(unlikely_thread_id)

            if main_thread_id is not None:
                main_thread_id_attr = "_ident"
                if not hasattr(main_thread_instance, main_thread_id_attr):
                    main_thread_id_attr = "_Thread__ident"
                    assert hasattr(main_thread_instance, main_thread_id_attr)

                if main_thread_id != getattr(main_thread_instance, main_thread_id_attr):
                    # Note that we also have to reset the '_tstack_lock' for a regular lock.
                    # This is needed to avoid an error on shutdown because this lock is bound
                    # to the thread state and will be released when the secondary thread
                    # that initialized the lock is finished -- making an assert fail during
                    # process shutdown.
                    main_thread_instance._tstate_lock = threading._allocate_lock()
                    main_thread_instance._tstate_lock.acquire()

                    # Actually patch the thread ident as well as the threading._active dict
                    # (we should have the _active_limbo_lock to do that).
                    threading._active.pop(getattr(main_thread_instance, main_thread_id_attr), None)
                    setattr(main_thread_instance, main_thread_id_attr, main_thread_id)
                    threading._active[getattr(main_thread_instance, main_thread_id_attr)] = main_thread_instance

        # Note: only import from pydevd after the patching is done (we want to do the minimum
        # possible when doing that patching).
        on_warn(
            "The threading module was not imported by user code in the main thread. The debugger will attempt to work around https://bugs.python.org/issue37416."
        )

        if critical_warning:
            on_critical("Issue found when debugger was trying to work around https://bugs.python.org/issue37416:\n%s" % (critical_warning,))
    except:
        on_exception("Error patching main thread id.")


def attach(port, host, protocol="", debug_mode=""):
    try:
        import sys

        fix_main_thread = "threading" not in sys.modules

        if fix_main_thread:

            def on_warn(msg):
                from _pydev_bundle import pydev_log

                pydev_log.warn(msg)

            def on_exception(msg):
                from _pydev_bundle import pydev_log

                pydev_log.exception(msg)

            def on_critical(msg):
                from _pydev_bundle import pydev_log

                pydev_log.critical(msg)

            fix_main_thread_id(on_warn=on_warn, on_exception=on_exception, on_critical=on_critical)

        else:
            from _pydev_bundle import pydev_log  # @Reimport

            pydev_log.debug("The threading module is already imported by user code.")

        if protocol:
            from _pydevd_bundle import pydevd_defaults

            pydevd_defaults.PydevdCustomization.DEFAULT_PROTOCOL = protocol

        if debug_mode:
            from _pydevd_bundle import pydevd_defaults

            pydevd_defaults.PydevdCustomization.DEBUG_MODE = debug_mode

        import pydevd

        # I.e.: disconnect/reset if already connected.

        pydevd.SetupHolder.setup = None

        py_db = pydevd.get_global_debugger()
        if py_db is not None:
            py_db.dispose_and_kill_all_pydevd_threads(wait=False)

        # pydevd.DebugInfoHolder.DEBUG_TRACE_LEVEL = 3
        pydevd.settrace(
            port=port,
            host=host,
            stdoutToServer=True,
            stderrToServer=True,
            overwrite_prev_trace=True,
            suspend=False,
            trace_only_current_thread=False,
            patch_multiprocessing=False,
        )
    except:
        import traceback

        traceback.print_exc()

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydev_ipython\inputhookqt5.py ===
# -*- coding: utf-8 -*-
"""
Qt5's inputhook support function

Author: Christian Boos
"""

# -----------------------------------------------------------------------------
#  Copyright (C) 2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import os
import signal

from _pydev_bundle._pydev_saved_modules import threading

from pydev_ipython.qt_for_kernel import QtCore, QtGui
from pydev_ipython.inputhook import allow_CTRL_C, ignore_CTRL_C, stdin_ready


# To minimise future merging complexity, rather than edit the entire code base below
# we fake InteractiveShell here
class InteractiveShell:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_hook(self, *args, **kwargs):
        # We don't consider the pre_prompt_hook because we don't have
        # KeyboardInterrupts to consider since we are running under PyDev
        pass


# -----------------------------------------------------------------------------
# Module Globals
# -----------------------------------------------------------------------------


got_kbdint = False
sigint_timer = None

# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


def create_inputhook_qt5(mgr, app=None):
    """Create an input hook for running the Qt5 application event loop.

    Parameters
    ----------
    mgr : an InputHookManager

    app : Qt Application, optional.
        Running application to use.  If not given, we probe Qt for an
        existing application object, and create a new one if none is found.

    Returns
    -------
    A pair consisting of a Qt Application (either the one given or the
    one found or created) and a inputhook.

    Notes
    -----
    We use a custom input hook instead of PyQt5's default one, as it
    interacts better with the readline packages (issue #481).

    The inputhook function works in tandem with a 'pre_prompt_hook'
    which automatically restores the hook as an inputhook in case the
    latter has been temporarily disabled after having intercepted a
    KeyboardInterrupt.
    """

    if app is None:
        app = QtCore.QCoreApplication.instance()
        if app is None:
            from PyQt5 import QtWidgets

            app = QtWidgets.QApplication([" "])

    # Re-use previously created inputhook if any
    ip = InteractiveShell.instance()
    if hasattr(ip, "_inputhook_qt5"):
        return app, ip._inputhook_qt5

    # Otherwise create the inputhook_qt5/preprompthook_qt5 pair of
    # hooks (they both share the got_kbdint flag)

    def inputhook_qt5():
        """PyOS_InputHook python hook for Qt5.

        Process pending Qt events and if there's no pending keyboard
        input, spend a short slice of time (50ms) running the Qt event
        loop.

        As a Python ctypes callback can't raise an exception, we catch
        the KeyboardInterrupt and temporarily deactivate the hook,
        which will let a *second* CTRL+C be processed normally and go
        back to a clean prompt line.
        """
        try:
            allow_CTRL_C()
            app = QtCore.QCoreApplication.instance()
            if not app:  # shouldn't happen, but safer if it happens anyway...
                return 0
            app.processEvents(QtCore.QEventLoop.AllEvents, 300)
            if not stdin_ready():
                # Generally a program would run QCoreApplication::exec()
                # from main() to enter and process the Qt event loop until
                # quit() or exit() is called and the program terminates.
                #
                # For our input hook integration, we need to repeatedly
                # enter and process the Qt event loop for only a short
                # amount of time (say 50ms) to ensure that Python stays
                # responsive to other user inputs.
                #
                # A naive approach would be to repeatedly call
                # QCoreApplication::exec(), using a timer to quit after a
                # short amount of time. Unfortunately, QCoreApplication
                # emits an aboutToQuit signal before stopping, which has
                # the undesirable effect of closing all modal windows.
                #
                # To work around this problem, we instead create a
                # QEventLoop and call QEventLoop::exec(). Other than
                # setting some state variables which do not seem to be
                # used anywhere, the only thing QCoreApplication adds is
                # the aboutToQuit signal which is precisely what we are
                # trying to avoid.
                timer = QtCore.QTimer()
                event_loop = QtCore.QEventLoop()
                timer.timeout.connect(event_loop.quit)
                while not stdin_ready():
                    timer.start(50)
                    event_loop.exec_()
                    timer.stop()
        except KeyboardInterrupt:
            global got_kbdint, sigint_timer

            ignore_CTRL_C()
            got_kbdint = True
            mgr.clear_inputhook()

            # This generates a second SIGINT so the user doesn't have to
            # press CTRL+C twice to get a clean prompt.
            #
            # Since we can't catch the resulting KeyboardInterrupt here
            # (because this is a ctypes callback), we use a timer to
            # generate the SIGINT after we leave this callback.
            #
            # Unfortunately this doesn't work on Windows (SIGINT kills
            # Python and CTRL_C_EVENT doesn't work).
            if os.name == "posix":
                pid = os.getpid()
                if not sigint_timer:
                    sigint_timer = threading.Timer(0.01, os.kill, args=[pid, signal.SIGINT])
                    sigint_timer.start()
            else:
                print("\nKeyboardInterrupt - Ctrl-C again for new prompt")

        except:  # NO exceptions are allowed to escape from a ctypes callback
            ignore_CTRL_C()
            from traceback import print_exc

            print_exc()
            print("Got exception from inputhook_qt5, unregistering.")
            mgr.clear_inputhook()
        finally:
            allow_CTRL_C()
        return 0

    def preprompthook_qt5(ishell):
        """'pre_prompt_hook' used to restore the Qt5 input hook

        (in case the latter was temporarily deactivated after a
        CTRL+C)
        """
        global got_kbdint, sigint_timer

        if sigint_timer:
            sigint_timer.cancel()
            sigint_timer = None

        if got_kbdint:
            mgr.set_inputhook(inputhook_qt5)
        got_kbdint = False

    ip._inputhook_qt5 = inputhook_qt5
    ip.set_hook("pre_prompt_hook", preprompthook_qt5)

    return app, inputhook_qt5

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydev_ipython\inputhookqt6.py ===
# -*- coding: utf-8 -*-
"""
Qt6's inputhook support function

Author: Christian Boos, Marijn van Vliet
"""

# -----------------------------------------------------------------------------
#  Copyright (C) 2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import os
import signal

from _pydev_bundle._pydev_saved_modules import threading

from pydev_ipython.qt_for_kernel import QtCore, QtGui
from pydev_ipython.inputhook import allow_CTRL_C, ignore_CTRL_C, stdin_ready


# To minimise future merging complexity, rather than edit the entire code base below
# we fake InteractiveShell here
class InteractiveShell:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_hook(self, *args, **kwargs):
        # We don't consider the pre_prompt_hook because we don't have
        # KeyboardInterrupts to consider since we are running under PyDev
        pass


# -----------------------------------------------------------------------------
# Module Globals
# -----------------------------------------------------------------------------


got_kbdint = False
sigint_timer = None

# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


def create_inputhook_qt6(mgr, app=None):
    """Create an input hook for running the Qt6 application event loop.

    Parameters
    ----------
    mgr : an InputHookManager

    app : Qt Application, optional.
        Running application to use.  If not given, we probe Qt for an
        existing application object, and create a new one if none is found.

    Returns
    -------
    A pair consisting of a Qt Application (either the one given or the
    one found or created) and a inputhook.

    Notes
    -----
    We use a custom input hook instead of PyQt6's default one, as it
    interacts better with the readline packages (issue #481).

    The inputhook function works in tandem with a 'pre_prompt_hook'
    which automatically restores the hook as an inputhook in case the
    latter has been temporarily disabled after having intercepted a
    KeyboardInterrupt.
    """

    if app is None:
        app = QtCore.QCoreApplication.instance()
        if app is None:
            from PyQt6 import QtWidgets

            app = QtWidgets.QApplication([" "])

    # Re-use previously created inputhook if any
    ip = InteractiveShell.instance()
    if hasattr(ip, "_inputhook_qt6"):
        return app, ip._inputhook_qt6

    # Otherwise create the inputhook_qt6/preprompthook_qt6 pair of
    # hooks (they both share the got_kbdint flag)

    def inputhook_qt6():
        """PyOS_InputHook python hook for Qt6.

        Process pending Qt events and if there's no pending keyboard
        input, spend a short slice of time (50ms) running the Qt event
        loop.

        As a Python ctypes callback can't raise an exception, we catch
        the KeyboardInterrupt and temporarily deactivate the hook,
        which will let a *second* CTRL+C be processed normally and go
        back to a clean prompt line.
        """
        try:
            allow_CTRL_C()
            app = QtCore.QCoreApplication.instance()
            if not app:  # shouldn't happen, but safer if it happens anyway...
                return 0
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 300)
            if not stdin_ready():
                # Generally a program would run QCoreApplication::exec()
                # from main() to enter and process the Qt event loop until
                # quit() or exit() is called and the program terminates.
                #
                # For our input hook integration, we need to repeatedly
                # enter and process the Qt event loop for only a short
                # amount of time (say 50ms) to ensure that Python stays
                # responsive to other user inputs.
                #
                # A naive approach would be to repeatedly call
                # QCoreApplication::exec(), using a timer to quit after a
                # short amount of time. Unfortunately, QCoreApplication
                # emits an aboutToQuit signal before stopping, which has
                # the undesirable effect of closing all modal windows.
                #
                # To work around this problem, we instead create a
                # QEventLoop and call QEventLoop::exec(). Other than
                # setting some state variables which do not seem to be
                # used anywhere, the only thing QCoreApplication adds is
                # the aboutToQuit signal which is precisely what we are
                # trying to avoid.
                timer = QtCore.QTimer()
                event_loop = QtCore.QEventLoop()
                timer.timeout.connect(event_loop.quit)
                while not stdin_ready():
                    timer.start(50)
                    event_loop.exec()
                    timer.stop()
        except KeyboardInterrupt:
            global got_kbdint, sigint_timer

            ignore_CTRL_C()
            got_kbdint = True
            mgr.clear_inputhook()

            # This generates a second SIGINT so the user doesn't have to
            # press CTRL+C twice to get a clean prompt.
            #
            # Since we can't catch the resulting KeyboardInterrupt here
            # (because this is a ctypes callback), we use a timer to
            # generate the SIGINT after we leave this callback.
            #
            # Unfortunately this doesn't work on Windows (SIGINT kills
            # Python and CTRL_C_EVENT doesn't work).
            if os.name == "posix":
                pid = os.getpid()
                if not sigint_timer:
                    sigint_timer = threading.Timer(0.01, os.kill, args=[pid, signal.SIGINT])
                    sigint_timer.start()
            else:
                print("\nKeyboardInterrupt - Ctrl-C again for new prompt")

        except:  # NO exceptions are allowed to escape from a ctypes callback
            ignore_CTRL_C()
            from traceback import print_exc

            print_exc()
            print("Got exception from inputhook_qt6, unregistering.")
            mgr.clear_inputhook()
        finally:
            allow_CTRL_C()
        return 0

    def preprompthook_qt6(ishell):
        """'pre_prompt_hook' used to restore the Qt6 input hook

        (in case the latter was temporarily deactivated after a
        CTRL+C)
        """
        global got_kbdint, sigint_timer

        if sigint_timer:
            sigint_timer.cancel()
            sigint_timer = None

        if got_kbdint:
            mgr.set_inputhook(inputhook_qt6)
        got_kbdint = False

    ip._inputhook_qt6 = inputhook_qt6
    ip.set_hook("pre_prompt_hook", preprompthook_qt6)

    return app, inputhook_qt6

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_signature.py ===
from _pydev_bundle import pydev_log

try:
    import trace
except ImportError:
    pass
else:
    trace._warn = lambda *args: None  # workaround for http://bugs.python.org/issue17143 (PY-8706)

import os
from _pydevd_bundle.pydevd_comm import CMD_SIGNATURE_CALL_TRACE, NetCommand
from _pydevd_bundle import pydevd_xml
from _pydevd_bundle.pydevd_utils import get_clsname_for_code


class Signature(object):
    def __init__(self, file, name):
        self.file = file
        self.name = name
        self.args = []
        self.args_str = []
        self.return_type = None

    def add_arg(self, name, type):
        self.args.append((name, type))
        self.args_str.append("%s:%s" % (name, type))

    def set_args(self, frame, recursive=False):
        self.args = []

        code = frame.f_code
        locals = frame.f_locals

        for i in range(0, code.co_argcount):
            name = code.co_varnames[i]
            class_name = get_type_of_value(locals[name], recursive=recursive)

            self.add_arg(name, class_name)

    def __str__(self):
        return "%s %s(%s)" % (self.file, self.name, ", ".join(self.args_str))


def get_type_of_value(value, ignore_module_name=("__main__", "__builtin__", "builtins"), recursive=False):
    tp = type(value)
    class_name = tp.__name__
    if class_name == "instance":  # old-style classes
        tp = value.__class__
        class_name = tp.__name__

    if hasattr(tp, "__module__") and tp.__module__ and tp.__module__ not in ignore_module_name:
        class_name = "%s.%s" % (tp.__module__, class_name)

    if class_name == "list":
        class_name = "List"
        if len(value) > 0 and recursive:
            class_name += "[%s]" % get_type_of_value(value[0], recursive=recursive)
        return class_name

    if class_name == "dict":
        class_name = "Dict"
        if len(value) > 0 and recursive:
            for k, v in value.items():
                class_name += "[%s, %s]" % (get_type_of_value(k, recursive=recursive), get_type_of_value(v, recursive=recursive))
                break
        return class_name

    if class_name == "tuple":
        class_name = "Tuple"
        if len(value) > 0 and recursive:
            class_name += "["
            class_name += ", ".join(get_type_of_value(v, recursive=recursive) for v in value)
            class_name += "]"

    return class_name


def _modname(path):
    """Return a plausible module name for the path"""
    base = os.path.basename(path)
    filename, ext = os.path.splitext(base)
    return filename


class SignatureFactory(object):
    def __init__(self):
        self._caller_cache = {}
        self.cache = CallSignatureCache()

    def create_signature(self, frame, filename, with_args=True):
        try:
            _, modulename, funcname = self.file_module_function_of(frame)
            signature = Signature(filename, funcname)
            if with_args:
                signature.set_args(frame, recursive=True)
            return signature
        except:
            pydev_log.exception()

    def file_module_function_of(self, frame):  # this code is take from trace module and fixed to work with new-style classes
        code = frame.f_code
        filename = code.co_filename
        if filename:
            modulename = _modname(filename)
        else:
            modulename = None

        funcname = code.co_name
        clsname = None
        if code in self._caller_cache:
            if self._caller_cache[code] is not None:
                clsname = self._caller_cache[code]
        else:
            self._caller_cache[code] = None
            clsname = get_clsname_for_code(code, frame)
            if clsname is not None:
                # cache the result - assumption is that new.* is
                # not called later to disturb this relationship
                # _caller_cache could be flushed if functions in
                # the new module get called.
                self._caller_cache[code] = clsname

        if clsname is not None:
            funcname = "%s.%s" % (clsname, funcname)

        return filename, modulename, funcname


def get_signature_info(signature):
    return signature.file, signature.name, " ".join([arg[1] for arg in signature.args])


def get_frame_info(frame):
    co = frame.f_code
    return co.co_name, frame.f_lineno, co.co_filename


class CallSignatureCache(object):
    def __init__(self):
        self.cache = {}

    def add(self, signature):
        filename, name, args_type = get_signature_info(signature)
        calls_from_file = self.cache.setdefault(filename, {})
        name_calls = calls_from_file.setdefault(name, {})
        name_calls[args_type] = None

    def is_in_cache(self, signature):
        filename, name, args_type = get_signature_info(signature)
        if args_type in self.cache.get(filename, {}).get(name, {}):
            return True
        return False


def create_signature_message(signature):
    cmdTextList = ["<xml>"]

    cmdTextList.append(
        '<call_signature file="%s" name="%s">'
        % (pydevd_xml.make_valid_xml_value(signature.file), pydevd_xml.make_valid_xml_value(signature.name))
    )

    for arg in signature.args:
        cmdTextList.append(
            '<arg name="%s" type="%s"></arg>' % (pydevd_xml.make_valid_xml_value(arg[0]), pydevd_xml.make_valid_xml_value(arg[1]))
        )

    if signature.return_type is not None:
        cmdTextList.append('<return type="%s"></return>' % (pydevd_xml.make_valid_xml_value(signature.return_type)))

    cmdTextList.append("</call_signature></xml>")
    cmdText = "".join(cmdTextList)
    return NetCommand(CMD_SIGNATURE_CALL_TRACE, 0, cmdText)


def send_signature_call_trace(dbg, frame, filename):
    if dbg.signature_factory and dbg.in_project_scope(frame):
        signature = dbg.signature_factory.create_signature(frame, filename)
        if signature is not None:
            if dbg.signature_factory.cache is not None:
                if not dbg.signature_factory.cache.is_in_cache(signature):
                    dbg.signature_factory.cache.add(signature)
                    dbg.writer.add_command(create_signature_message(signature))
                    return True
                else:
                    # we don't send signature if it is cached
                    return False
            else:
                dbg.writer.add_command(create_signature_message(signature))
                return True
    return False


def send_signature_return_trace(dbg, frame, filename, return_value):
    if dbg.signature_factory and dbg.in_project_scope(frame):
        signature = dbg.signature_factory.create_signature(frame, filename, with_args=False)
        signature.return_type = get_type_of_value(return_value, recursive=True)
        dbg.writer.add_command(create_signature_message(signature))
        return True

    return False

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\compat.py ===
# Partial copy of https://bitbucket.org/gutworth/six/src/8e634686c53a35092dd705172440a9231c90ddd1/six.py?at=default
# With some differences to take into account that the iterXXX version may be defined in user code.

# Original __author__ = "Benjamin Peterson <benjamin@python.org>"
# Base __version__ = "1.7.3"

# Copyright (c) 2010-2014 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import types


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = (str,)
    integer_types = (int,)
    class_types = (type,)
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = (basestring,)
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31

        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X


if PY3:
    xrange = range
    unicode = str
    bytes = bytes

    def iterkeys(d, **kw):
        if hasattr(d, "iterkeys"):
            return iter(d.iterkeys(**kw))
        return iter(d.keys(**kw))

    def itervalues(d, **kw):
        if hasattr(d, "itervalues"):
            return iter(d.itervalues(**kw))
        return iter(d.values(**kw))

    def iteritems(d, **kw):
        if hasattr(d, "iteritems"):
            return iter(d.iteritems(**kw))
        return iter(d.items(**kw))

    def iterlists(d, **kw):
        if hasattr(d, "iterlists"):
            return iter(d.iterlists(**kw))
        return iter(d.lists(**kw))

    def keys(d, **kw):
        return list(iterkeys(d, **kw))
else:
    unicode = unicode
    xrange = xrange
    bytes = str

    def keys(d, **kw):
        return d.keys(**kw)

    def iterkeys(d, **kw):
        return iter(d.iterkeys(**kw))

    def itervalues(d, **kw):
        return iter(d.itervalues(**kw))

    def iteritems(d, **kw):
        return iter(d.iteritems(**kw))

    def iterlists(d, **kw):
        return iter(d.iterlists(**kw))


if PY3:
    import builtins

    exec_ = getattr(builtins, "exec")

    def reraise(tp, value, tb=None):
        if value is None:
            value = tp()
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else:

    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")

    exec_(
        """def reraise(tp, value, tb=None):
    raise tp, value, tb
"""
    )


if PY3:
    import operator

    def b(s):
        if isinstance(s, str):
            return s.encode("latin-1")
        assert isinstance(s, bytes)
        return s

    def u(s):
        return s

    unichr = chr
    if sys.version_info[1] <= 1:

        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io

    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:

    def b(s):
        return s

    # Workaround for standalone backslash
    def u(s):
        return unicode(s.replace(r"\\", r"\\\\"), "unicode_escape")

    unichr = unichr
    int2byte = chr

    def byte2int(bs):
        return ord(bs[0])

    def indexbytes(buf, i):
        return ord(buf[i])

    def iterbytes(buf):
        return (ord(byte) for byte in buf)

    import StringIO

    StringIO = BytesIO = StringIO.StringIO

# === NexusCore/openenv\Lib\site-packages\litellm\llms\deprecated_providers\palm.py ===
import copy
import time
import traceback
import types
from typing import Callable, Optional

import httpx

import litellm
from litellm.utils import Choices, Message, ModelResponse, Usage


class PalmError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        self.request = httpx.Request(
            method="POST",
            url="https://developers.generativeai.google/api/python/google/generativeai/chat",
        )
        self.response = httpx.Response(status_code=status_code, request=self.request)
        super().__init__(
            self.message
        )  # Call the base class constructor with the parameters it needs


class PalmConfig:
    """
    Reference: https://developers.generativeai.google/api/python/google/generativeai/chat

    The class `PalmConfig` provides configuration for the Palm's API interface. Here are the parameters:

    - `context` (string): Text that should be provided to the model first, to ground the response. This could be a prompt to guide the model's responses.

    - `examples` (list): Examples of what the model should generate. They are treated identically to conversation messages except that they take precedence over the history in messages if the total input size exceeds the model's input_token_limit.

    - `temperature` (float): Controls the randomness of the output. Must be positive. Higher values produce a more random and varied response. A temperature of zero will be deterministic.

    - `candidate_count` (int): Maximum number of generated response messages to return. This value must be between [1, 8], inclusive. Only unique candidates are returned.

    - `top_k` (int): The API uses combined nucleus and top-k sampling. `top_k` sets the maximum number of tokens to sample from on each step.

    - `top_p` (float): The API uses combined nucleus and top-k sampling. `top_p` configures the nucleus sampling. It sets the maximum cumulative probability of tokens to sample from.

    - `max_output_tokens` (int): Sets the maximum number of tokens to be returned in the output
    """

    context: Optional[str] = None
    examples: Optional[list] = None
    temperature: Optional[float] = None
    candidate_count: Optional[int] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    max_output_tokens: Optional[int] = None

    def __init__(
        self,
        context: Optional[str] = None,
        examples: Optional[list] = None,
        temperature: Optional[float] = None,
        candidate_count: Optional[int] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return {
            k: v
            for k, v in cls.__dict__.items()
            if not k.startswith("__")
            and not isinstance(
                v,
                (
                    types.FunctionType,
                    types.BuiltinFunctionType,
                    classmethod,
                    staticmethod,
                ),
            )
            and v is not None
        }


def completion(
    model: str,
    messages: list,
    model_response: ModelResponse,
    print_verbose: Callable,
    api_key,
    encoding,
    logging_obj,
    optional_params: dict,
    litellm_params=None,
    logger_fn=None,
):
    try:
        import google.generativeai as palm  # type: ignore
    except Exception:
        raise Exception(
            "Importing google.generativeai failed, please run 'pip install -q google-generativeai"
        )
    palm.configure(api_key=api_key)

    model = model

    ## Load Config
    inference_params = copy.deepcopy(optional_params)
    inference_params.pop(
        "stream", None
    )  # palm does not support streaming, so we handle this by fake streaming in main.py
    config = litellm.PalmConfig.get_config()
    for k, v in config.items():
        if (
            k not in inference_params
        ):  # completion(top_k=3) > palm_config(top_k=3) <- allows for dynamic variables to be passed in
            inference_params[k] = v

    prompt = ""
    for message in messages:
        if "role" in message:
            if message["role"] == "user":
                prompt += f"{message['content']}"
            else:
                prompt += f"{message['content']}"
        else:
            prompt += f"{message['content']}"

    ## LOGGING
    logging_obj.pre_call(
        input=prompt,
        api_key="",
        additional_args={"complete_input_dict": {"inference_params": inference_params}},
    )
    ## COMPLETION CALL
    try:
        response = palm.generate_text(prompt=prompt, **inference_params)
    except Exception as e:
        raise PalmError(
            message=str(e),
            status_code=500,
        )

    ## LOGGING
    logging_obj.post_call(
        input=prompt,
        api_key="",
        original_response=response,
        additional_args={"complete_input_dict": {}},
    )
    print_verbose(f"raw model_response: {response}")
    ## RESPONSE OBJECT
    completion_response = response
    try:
        choices_list = []
        for idx, item in enumerate(completion_response.candidates):
            if len(item["output"]) > 0:
                message_obj = Message(content=item["output"])
            else:
                message_obj = Message(content=None)
            choice_obj = Choices(index=idx + 1, message=message_obj)
            choices_list.append(choice_obj)
        model_response.choices = choices_list  # type: ignore
    except Exception:
        raise PalmError(
            message=traceback.format_exc(), status_code=response.status_code
        )

    try:
        completion_response = model_response["choices"][0]["message"].get("content")
    except Exception:
        raise PalmError(
            status_code=400,
            message=f"No response received. Original response - {response}",
        )

    ## CALCULATING USAGE - baseten charges on time, not tokens - have some mapping of cost here.
    prompt_tokens = len(encoding.encode(prompt))
    completion_tokens = len(
        encoding.encode(model_response["choices"][0]["message"].get("content", ""))
    )

    model_response.created = int(time.time())
    model_response.model = "palm/" + model
    usage = Usage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    setattr(model_response, "usage", usage)
    return model_response


def embedding():
    # logic for parsing in - calling - parsing out model embedding calls
    pass

# === NexusCore/openenv\Lib\site-packages\numpy\typing\__init__.py ===
"""
============================
Typing (:mod:`numpy.typing`)
============================

.. versionadded:: 1.20

Large parts of the NumPy API have :pep:`484`-style type annotations. In
addition a number of type aliases are available to users, most prominently
the two below:

- `ArrayLike`: objects that can be converted to arrays
- `DTypeLike`: objects that can be converted to dtypes

.. _typing-extensions: https://pypi.org/project/typing-extensions/

Mypy plugin
-----------

.. versionadded:: 1.21

.. automodule:: numpy.typing.mypy_plugin

.. currentmodule:: numpy.typing

Differences from the runtime NumPy API
--------------------------------------

NumPy is very flexible. Trying to describe the full range of
possibilities statically would result in types that are not very
helpful. For that reason, the typed NumPy API is often stricter than
the runtime NumPy API. This section describes some notable
differences.

ArrayLike
~~~~~~~~~

The `ArrayLike` type tries to avoid creating object arrays. For
example,

.. code-block:: python

    >>> np.array(x**2 for x in range(10))
    array(<generator object <genexpr> at ...>, dtype=object)

is valid NumPy code which will create a 0-dimensional object
array. Type checkers will complain about the above example when using
the NumPy types however. If you really intended to do the above, then
you can either use a ``# type: ignore`` comment:

.. code-block:: python

    >>> np.array(x**2 for x in range(10))  # type: ignore

or explicitly type the array like object as `~typing.Any`:

.. code-block:: python

    >>> from typing import Any
    >>> array_like: Any = (x**2 for x in range(10))
    >>> np.array(array_like)
    array(<generator object <genexpr> at ...>, dtype=object)

ndarray
~~~~~~~

It's possible to mutate the dtype of an array at runtime. For example,
the following code is valid:

.. code-block:: python

    >>> x = np.array([1, 2])
    >>> x.dtype = np.bool

This sort of mutation is not allowed by the types. Users who want to
write statically typed code should instead use the `numpy.ndarray.view`
method to create a view of the array with a different dtype.

DTypeLike
~~~~~~~~~

The `DTypeLike` type tries to avoid creation of dtype objects using
dictionary of fields like below:

.. code-block:: python

    >>> x = np.dtype({"field1": (float, 1), "field2": (int, 3)})

Although this is valid NumPy code, the type checker will complain about it,
since its usage is discouraged.
Please see : :ref:`Data type objects <arrays.dtypes>`

Number precision
~~~~~~~~~~~~~~~~

The precision of `numpy.number` subclasses is treated as a invariant generic
parameter (see :class:`~NBitBase`), simplifying the annotating of processes
involving precision-based casting.

.. code-block:: python

    >>> from typing import TypeVar
    >>> import numpy as np
    >>> import numpy.typing as npt

    >>> T = TypeVar("T", bound=npt.NBitBase)
    >>> def func(a: "np.floating[T]", b: "np.floating[T]") -> "np.floating[T]":
    ...     ...

Consequently, the likes of `~numpy.float16`, `~numpy.float32` and
`~numpy.float64` are still sub-types of `~numpy.floating`, but, contrary to
runtime, they're not necessarily considered as sub-classes.

Timedelta64
~~~~~~~~~~~

The `~numpy.timedelta64` class is not considered a subclass of
`~numpy.signedinteger`, the former only inheriting from `~numpy.generic`
while static type checking.

0D arrays
~~~~~~~~~

During runtime numpy aggressively casts any passed 0D arrays into their
corresponding `~numpy.generic` instance. Until the introduction of shape
typing (see :pep:`646`) it is unfortunately not possible to make the
necessary distinction between 0D and >0D arrays. While thus not strictly
correct, all operations that can potentially perform a 0D-array -> scalar
cast are currently annotated as exclusively returning an `~numpy.ndarray`.

If it is known in advance that an operation *will* perform a
0D-array -> scalar cast, then one can consider manually remedying the
situation with either `typing.cast` or a ``# type: ignore`` comment.

Record array dtypes
~~~~~~~~~~~~~~~~~~~

The dtype of `numpy.recarray`, and the :ref:`routines.array-creation.rec`
functions in general, can be specified in one of two ways:

* Directly via the ``dtype`` argument.
* With up to five helper arguments that operate via `numpy.rec.format_parser`:
  ``formats``, ``names``, ``titles``, ``aligned`` and ``byteorder``.

These two approaches are currently typed as being mutually exclusive,
*i.e.* if ``dtype`` is specified than one may not specify ``formats``.
While this mutual exclusivity is not (strictly) enforced during runtime,
combining both dtype specifiers can lead to unexpected or even downright
buggy behavior.

API
---

"""
# NOTE: The API section will be appended with additional entries
# further down in this file

# pyright: reportDeprecated=false

from numpy._typing import ArrayLike, DTypeLike, NBitBase, NDArray

__all__ = ["ArrayLike", "DTypeLike", "NBitBase", "NDArray"]


__DIR = __all__ + [k for k in globals() if k.startswith("__") and k.endswith("__")]
__DIR_SET = frozenset(__DIR)


def __dir__() -> list[str]:
    return __DIR

def __getattr__(name: str):
    if name == "NBitBase":
        import warnings

        # Deprecated in NumPy 2.3, 2025-05-01
        warnings.warn(
            "`NBitBase` is deprecated and will be removed from numpy.typing in the "
            "future. Use `@typing.overload` or a `TypeVar` with a scalar-type as upper "
            "bound, instead. (deprecated in NumPy 2.3)",
            DeprecationWarning,
            stacklevel=2,
        )
        return NBitBase

    if name in __DIR_SET:
        return globals()[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __doc__ is not None:
    from numpy._typing._add_docstring import _docstrings
    __doc__ += _docstrings
    __doc__ += '\n.. autoclass:: numpy.typing.NBitBase\n'
    del _docstrings

from numpy._pytesttester import PytestTester

test = PytestTester(__name__)
del PytestTester

# === NexusCore/openenv\Lib\site-packages\pip\_internal\commands\debug.py ===
import locale
import logging
import os
import sys
from optparse import Values
from types import ModuleType
from typing import Any, Dict, List, Optional

import pip._vendor
from pip._vendor.certifi import where
from pip._vendor.packaging.version import parse as parse_version

from pip._internal.cli import cmdoptions
from pip._internal.cli.base_command import Command
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.configuration import Configuration
from pip._internal.metadata import get_environment
from pip._internal.utils.compat import open_text_resource
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import get_pip_version

logger = logging.getLogger(__name__)


def show_value(name: str, value: Any) -> None:
    logger.info("%s: %s", name, value)


def show_sys_implementation() -> None:
    logger.info("sys.implementation:")
    implementation_name = sys.implementation.name
    with indent_log():
        show_value("name", implementation_name)


def create_vendor_txt_map() -> Dict[str, str]:
    with open_text_resource("pip._vendor", "vendor.txt") as f:
        # Purge non version specifying lines.
        # Also, remove any space prefix or suffixes (including comments).
        lines = [
            line.strip().split(" ", 1)[0] for line in f.readlines() if "==" in line
        ]

    # Transform into "module" -> version dict.
    return dict(line.split("==", 1) for line in lines)


def get_module_from_module_name(module_name: str) -> Optional[ModuleType]:
    # Module name can be uppercase in vendor.txt for some reason...
    module_name = module_name.lower().replace("-", "_")
    # PATCH: setuptools is actually only pkg_resources.
    if module_name == "setuptools":
        module_name = "pkg_resources"

    try:
        __import__(f"pip._vendor.{module_name}", globals(), locals(), level=0)
        return getattr(pip._vendor, module_name)
    except ImportError:
        # We allow 'truststore' to fail to import due
        # to being unavailable on Python 3.9 and earlier.
        if module_name == "truststore" and sys.version_info < (3, 10):
            return None
        raise


def get_vendor_version_from_module(module_name: str) -> Optional[str]:
    module = get_module_from_module_name(module_name)
    version = getattr(module, "__version__", None)

    if module and not version:
        # Try to find version in debundled module info.
        assert module.__file__ is not None
        env = get_environment([os.path.dirname(module.__file__)])
        dist = env.get_distribution(module_name)
        if dist:
            version = str(dist.version)

    return version


def show_actual_vendor_versions(vendor_txt_versions: Dict[str, str]) -> None:
    """Log the actual version and print extra info if there is
    a conflict or if the actual version could not be imported.
    """
    for module_name, expected_version in vendor_txt_versions.items():
        extra_message = ""
        actual_version = get_vendor_version_from_module(module_name)
        if not actual_version:
            extra_message = (
                " (Unable to locate actual module version, using"
                " vendor.txt specified version)"
            )
            actual_version = expected_version
        elif parse_version(actual_version) != parse_version(expected_version):
            extra_message = (
                " (CONFLICT: vendor.txt suggests version should"
                f" be {expected_version})"
            )
        logger.info("%s==%s%s", module_name, actual_version, extra_message)


def show_vendor_versions() -> None:
    logger.info("vendored library versions:")

    vendor_txt_versions = create_vendor_txt_map()
    with indent_log():
        show_actual_vendor_versions(vendor_txt_versions)


def show_tags(options: Values) -> None:
    tag_limit = 10

    target_python = make_target_python(options)
    tags = target_python.get_sorted_tags()

    # Display the target options that were explicitly provided.
    formatted_target = target_python.format_given()
    suffix = ""
    if formatted_target:
        suffix = f" (target: {formatted_target})"

    msg = f"Compatible tags: {len(tags)}{suffix}"
    logger.info(msg)

    if options.verbose < 1 and len(tags) > tag_limit:
        tags_limited = True
        tags = tags[:tag_limit]
    else:
        tags_limited = False

    with indent_log():
        for tag in tags:
            logger.info(str(tag))

        if tags_limited:
            msg = f"...\n[First {tag_limit} tags shown. Pass --verbose to show all.]"
            logger.info(msg)


def ca_bundle_info(config: Configuration) -> str:
    levels = {key.split(".", 1)[0] for key, _ in config.items()}
    if not levels:
        return "Not specified"

    levels_that_override_global = ["install", "wheel", "download"]
    global_overriding_level = [
        level for level in levels if level in levels_that_override_global
    ]
    if not global_overriding_level:
        return "global"

    if "global" in levels:
        levels.remove("global")
    return ", ".join(levels)


class DebugCommand(Command):
    """
    Display debug information.
    """

    usage = """
      %prog <options>"""
    ignore_require_venv = True

    def add_options(self) -> None:
        cmdoptions.add_target_python_options(self.cmd_opts)
        self.parser.insert_option_group(0, self.cmd_opts)
        self.parser.config.load()

    def run(self, options: Values, args: List[str]) -> int:
        logger.warning(
            "This command is only meant for debugging. "
            "Do not use this with automation for parsing and getting these "
            "details, since the output and options of this command may "
            "change without notice."
        )
        show_value("pip version", get_pip_version())
        show_value("sys.version", sys.version)
        show_value("sys.executable", sys.executable)
        show_value("sys.getdefaultencoding", sys.getdefaultencoding())
        show_value("sys.getfilesystemencoding", sys.getfilesystemencoding())
        show_value(
            "locale.getpreferredencoding",
            locale.getpreferredencoding(),
        )
        show_value("sys.platform", sys.platform)
        show_sys_implementation()

        show_value("'cert' config value", ca_bundle_info(self.parser.config))
        show_value("REQUESTS_CA_BUNDLE", os.environ.get("REQUESTS_CA_BUNDLE"))
        show_value("CURL_CA_BUNDLE", os.environ.get("CURL_CA_BUNDLE"))
        show_value("pip._vendor.certifi.where()", where())
        show_value("pip._vendor.DEBUNDLED", pip._vendor.DEBUNDLED)

        show_vendor_versions()

        show_tags(options)

        return SUCCESS

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\command\build_clib.py ===
"""distutils.command.build_clib

Implements the Distutils 'build_clib' command, to build a C/C++ library
that is included in the module distribution and needed by an extension
module."""

# XXX this module has *lots* of code ripped-off quite transparently from
# build_ext.py -- not surprisingly really, as the work required to build
# a static library from a collection of C source files is not really all
# that different from what's required to build a shared object file from
# a collection of C source files.  Nevertheless, I haven't done the
# necessary refactoring to account for the overlap in code between the
# two modules, mainly because a number of subtle details changed in the
# cut 'n paste.  Sigh.
from __future__ import annotations

import os
from collections.abc import Callable
from distutils._log import log
from typing import ClassVar

from ..ccompiler import new_compiler, show_compilers
from ..core import Command
from ..errors import DistutilsSetupError
from ..sysconfig import customize_compiler


class build_clib(Command):
    description = "build C/C++ libraries used by Python extensions"

    user_options: ClassVar[list[tuple[str, str, str]]] = [
        ('build-clib=', 'b', "directory to build C/C++ libraries to"),
        ('build-temp=', 't', "directory to put temporary build by-products"),
        ('debug', 'g', "compile with debugging information"),
        ('force', 'f', "forcibly build everything (ignore file timestamps)"),
        ('compiler=', 'c', "specify the compiler type"),
    ]

    boolean_options: ClassVar[list[str]] = ['debug', 'force']

    help_options: ClassVar[list[tuple[str, str | None, str, Callable[[], object]]]] = [
        ('help-compiler', None, "list available compilers", show_compilers),
    ]

    def initialize_options(self):
        self.build_clib = None
        self.build_temp = None

        # List of libraries to build
        self.libraries = None

        # Compilation options for all libraries
        self.include_dirs = None
        self.define = None
        self.undef = None
        self.debug = None
        self.force = False
        self.compiler = None

    def finalize_options(self) -> None:
        # This might be confusing: both build-clib and build-temp default
        # to build-temp as defined by the "build" command.  This is because
        # I think that C libraries are really just temporary build
        # by-products, at least from the point of view of building Python
        # extensions -- but I want to keep my options open.
        self.set_undefined_options(
            'build',
            ('build_temp', 'build_clib'),
            ('build_temp', 'build_temp'),
            ('compiler', 'compiler'),
            ('debug', 'debug'),
            ('force', 'force'),
        )

        self.libraries = self.distribution.libraries
        if self.libraries:
            self.check_library_list(self.libraries)

        if self.include_dirs is None:
            self.include_dirs = self.distribution.include_dirs or []
        if isinstance(self.include_dirs, str):
            self.include_dirs = self.include_dirs.split(os.pathsep)

        # XXX same as for build_ext -- what about 'self.define' and
        # 'self.undef' ?

    def run(self) -> None:
        if not self.libraries:
            return

        self.compiler = new_compiler(
            compiler=self.compiler, dry_run=self.dry_run, force=self.force
        )
        customize_compiler(self.compiler)

        if self.include_dirs is not None:
            self.compiler.set_include_dirs(self.include_dirs)
        if self.define is not None:
            # 'define' option is a list of (name,value) tuples
            for name, value in self.define:
                self.compiler.define_macro(name, value)
        if self.undef is not None:
            for macro in self.undef:
                self.compiler.undefine_macro(macro)

        self.build_libraries(self.libraries)

    def check_library_list(self, libraries) -> None:
        """Ensure that the list of libraries is valid.

        `library` is presumably provided as a command option 'libraries'.
        This method checks that it is a list of 2-tuples, where the tuples
        are (library_name, build_info_dict).

        Raise DistutilsSetupError if the structure is invalid anywhere;
        just returns otherwise.
        """
        if not isinstance(libraries, list):
            raise DistutilsSetupError("'libraries' option must be a list of tuples")

        for lib in libraries:
            if not isinstance(lib, tuple) and len(lib) != 2:
                raise DistutilsSetupError("each element of 'libraries' must a 2-tuple")

            name, build_info = lib

            if not isinstance(name, str):
                raise DistutilsSetupError(
                    "first element of each tuple in 'libraries' "
                    "must be a string (the library name)"
                )

            if '/' in name or (os.sep != '/' and os.sep in name):
                raise DistutilsSetupError(
                    f"bad library name '{lib[0]}': may not contain directory separators"
                )

            if not isinstance(build_info, dict):
                raise DistutilsSetupError(
                    "second element of each tuple in 'libraries' "
                    "must be a dictionary (build info)"
                )

    def get_library_names(self):
        # Assume the library list is valid -- 'check_library_list()' is
        # called from 'finalize_options()', so it should be!
        if not self.libraries:
            return None

        lib_names = []
        for lib_name, _build_info in self.libraries:
            lib_names.append(lib_name)
        return lib_names

    def get_source_files(self):
        self.check_library_list(self.libraries)
        filenames = []
        for lib_name, build_info in self.libraries:
            sources = build_info.get('sources')
            if sources is None or not isinstance(sources, (list, tuple)):
                raise DistutilsSetupError(
                    f"in 'libraries' option (library '{lib_name}'), "
                    "'sources' must be present and must be "
                    "a list of source filenames"
                )

            filenames.extend(sources)
        return filenames

    def build_libraries(self, libraries) -> None:
        for lib_name, build_info in libraries:
            sources = build_info.get('sources')
            if sources is None or not isinstance(sources, (list, tuple)):
                raise DistutilsSetupError(
                    f"in 'libraries' option (library '{lib_name}'), "
                    "'sources' must be present and must be "
                    "a list of source filenames"
                )
            sources = list(sources)

            log.info("building '%s' library", lib_name)

            # First, compile the source code to object files in the library
            # directory.  (This should probably change to putting object
            # files in a temporary build directory.)
            macros = build_info.get('macros')
            include_dirs = build_info.get('include_dirs')
            objects = self.compiler.compile(
                sources,
                output_dir=self.build_temp,
                macros=macros,
                include_dirs=include_dirs,
                debug=self.debug,
            )

            # Now "link" the object files together into a static library.
            # (On Unix at least, this isn't really linking -- it just
            # builds an archive.  Whatever.)
            self.compiler.create_static_lib(
                objects, lib_name, output_dir=self.build_clib, debug=self.debug
            )

# === NexusCore/openenv\Lib\site-packages\win32\scripts\VersionStamp\vssutil.py ===
import time
import traceback

import pythoncom
import win32com.client
import win32com.client.gencache
import win32con

constants = win32com.client.constants

win32com.client.gencache.EnsureModule("{783CD4E0-9D54-11CF-B8EE-00608CC9A71F}", 0, 5, 0)


def GetSS():
    ss = win32com.client.Dispatch("SourceSafe")
    # SS seems a bit weird.  It defaults the arguments as empty strings, but
    # then complains when they are used - so we pass "Missing"
    ss.Open(pythoncom.Missing, pythoncom.Missing, pythoncom.Missing)
    return ss


def test(projectName):
    ss = GetSS()
    project = ss.VSSItem(projectName)

    for item in project.GetVersions(constants.VSSFLAG_RECURSYES):
        print(item.VSSItem.Name, item.VersionNumber, item.Action)

    # item=i.Versions[0].VSSItem
    # for h in i.Versions:
    #     print("h.Comment", h.Action, h.VSSItem.Name)


def SubstituteInString(inString, evalEnv):
    substChar = "$"
    fields = inString.split(substChar)
    newFields = []
    for i in range(len(fields)):
        didSubst = 0
        strVal = fields[i]
        if i % 2 != 0:
            try:
                strVal = eval(strVal, evalEnv[0], evalEnv[1])
                newFields.append(strVal)
                didSubst = 1
            except:
                traceback.print_exc()
                print("Could not substitute", strVal)
        if not didSubst:
            newFields.append(strVal)
    return "".join(map(str, newFields))


def SubstituteInFile(inName, outName, evalEnv):
    inFile = open(inName, "r")
    try:
        outFile = open(outName, "w")
        try:
            while 1:
                line = inFile.read()
                if not line:
                    break
                outFile.write(SubstituteInString(line, evalEnv))
        finally:
            outFile.close()
    finally:
        inFile.close()


def VssLog(project, linePrefix="", noLabels=5, maxItems=150):
    lines = []
    num = 0
    labelNum = 0
    for i in project.GetVersions(constants.VSSFLAG_RECURSYES):
        num += 1
        if num > maxItems:
            break
        commentDesc = itemDesc = ""
        if i.Action[:5] == "Added":
            continue
        if len(i.Label):
            labelNum += 1
            itemDesc = i.Action
        else:
            itemDesc = i.VSSItem.Name
            if str(itemDesc[-4:]) == ".dsp":
                continue
        if i.Comment:
            commentDesc = f"\n{linePrefix}\t{i.Comment}"
        lines.append(
            "{}{}\t{}{}".format(
                linePrefix,
                time.asctime(time.localtime(int(i.Date))),
                itemDesc,
                commentDesc,
            )
        )
        if labelNum > noLabels:
            break
    return "\n".join(lines)


def SubstituteVSSInFile(projectName, inName, outName):
    import win32api

    if win32api.GetFullPathName(inName) == win32api.GetFullPathName(outName):
        raise RuntimeError("The input and output filenames can not be the same")
    sourceSafe = GetSS()
    project = sourceSafe.VSSItem(projectName)
    # Find the last label
    label = None
    for version in project.Versions:
        if version.Label:
            break
    else:
        print("Couldn't find a label in the sourcesafe project!")
        return
    # Setup some local helpers for the conversion strings.
    vss_label = version.Label
    vss_date = time.asctime(time.localtime(int(version.Date)))
    now = time.asctime(time.localtime(time.time()))
    SubstituteInFile(inName, outName, (locals(), globals()))


def CountCheckouts(item):
    num = 0
    if item.Type == constants.VSSITEM_PROJECT:
        for sub in item.Items:
            num += CountCheckouts(sub)
    else:
        if item.IsCheckedOut:
            num += 1
    return num


def GetLastBuildNo(project):
    i = GetSS().VSSItem(project)
    # Find the last label
    lab = None
    for version in i.Versions:
        lab = str(version.Label)
        if lab:
            return lab
    return None


def MakeNewBuildNo(project, buildDesc=None, auto=0, bRebrand=0):
    if buildDesc is None:
        buildDesc = "Created by Python"
    ss = GetSS()
    i = ss.VSSItem(project)
    num = CountCheckouts(i)
    if num > 0:
        msg = (
            "This project has %d items checked out\r\n\r\nDo you still want to continue?"
            % num
        )
        import win32ui

        if win32ui.MessageBox(msg, project, win32con.MB_YESNO) != win32con.IDYES:
            return

    oldBuild = buildNo = GetLastBuildNo(project)
    if buildNo is None:
        buildNo = "1"
        oldBuild = "<None>"
    else:
        try:
            buildNo = int(buildNo)
            if not bRebrand:
                buildNo += 1
            buildNo = str(buildNo)
        except ValueError as error:
            raise ValueError(
                f"The previous label could not be incremented: {oldBuild}"
            ) from error

    if not auto:
        from pywin.mfc import dialog

        buildNo = dialog.GetSimpleInput(
            "Enter new build number", buildNo, f"{project} - Prev: {oldBuild}"
        )
        if buildNo is None:
            return
    i.Label(buildNo, f"Build {buildNo}: {buildDesc}")
    if auto:
        print(f"Branded project {project} with label {buildNo}")
    return buildNo


if __name__ == "__main__":
    # 	UpdateWiseExeName("PyWiseTest.wse", "PyWiseTest-10.exe")

    # 	MakeVersion()
    # 	test(tp)
    # 	MakeNewBuildNo(tp)
    tp = "\\Python\\Python Win32 Extensions"
    SubstituteVSSInFile(
        tp, "d:\\src\\pythonex\\win32\\win32.txt", "d:\\temp\\win32.txt"
    )

# === NexusCore/openenv\Lib\site-packages\PIL\MspImagePlugin.py ===
#
# The Python Imaging Library.
#
# MSP file handling
#
# This is the format used by the Paint program in Windows 1 and 2.
#
# History:
#       95-09-05 fl     Created
#       97-01-03 fl     Read/write MSP images
#       17-02-21 es     Fixed RLE interpretation
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1995-97.
# Copyright (c) Eric Soroos 2017.
#
# See the README file for information on usage and redistribution.
#
# More info on this format: https://archive.org/details/gg243631
# Page 313:
# Figure 205. Windows Paint Version 1: "DanM" Format
# Figure 206. Windows Paint Version 2: "LinS" Format. Used in Windows V2.03
#
# See also: https://www.fileformat.info/format/mspaint/egff.htm
from __future__ import annotations

import io
import struct
from typing import IO

from . import Image, ImageFile
from ._binary import i16le as i16
from ._binary import o16le as o16

#
# read MSP files


def _accept(prefix: bytes) -> bool:
    return prefix.startswith((b"DanM", b"LinS"))


##
# Image plugin for Windows MSP images.  This plugin supports both
# uncompressed (Windows 1.0).


class MspImageFile(ImageFile.ImageFile):
    format = "MSP"
    format_description = "Windows Paint"

    def _open(self) -> None:
        # Header
        assert self.fp is not None

        s = self.fp.read(32)
        if not _accept(s):
            msg = "not an MSP file"
            raise SyntaxError(msg)

        # Header checksum
        checksum = 0
        for i in range(0, 32, 2):
            checksum = checksum ^ i16(s, i)
        if checksum != 0:
            msg = "bad MSP checksum"
            raise SyntaxError(msg)

        self._mode = "1"
        self._size = i16(s, 4), i16(s, 6)

        if s.startswith(b"DanM"):
            self.tile = [ImageFile._Tile("raw", (0, 0) + self.size, 32, "1")]
        else:
            self.tile = [ImageFile._Tile("MSP", (0, 0) + self.size, 32)]


class MspDecoder(ImageFile.PyDecoder):
    # The algo for the MSP decoder is from
    # https://www.fileformat.info/format/mspaint/egff.htm
    # cc-by-attribution -- That page references is taken from the
    # Encyclopedia of Graphics File Formats and is licensed by
    # O'Reilly under the Creative Common/Attribution license
    #
    # For RLE encoded files, the 32byte header is followed by a scan
    # line map, encoded as one 16bit word of encoded byte length per
    # line.
    #
    # NOTE: the encoded length of the line can be 0. This was not
    # handled in the previous version of this encoder, and there's no
    # mention of how to handle it in the documentation. From the few
    # examples I've seen, I've assumed that it is a fill of the
    # background color, in this case, white.
    #
    #
    # Pseudocode of the decoder:
    # Read a BYTE value as the RunType
    #  If the RunType value is zero
    #   Read next byte as the RunCount
    #   Read the next byte as the RunValue
    #   Write the RunValue byte RunCount times
    #  If the RunType value is non-zero
    #   Use this value as the RunCount
    #   Read and write the next RunCount bytes literally
    #
    #  e.g.:
    #  0x00 03 ff 05 00 01 02 03 04
    #  would yield the bytes:
    #  0xff ff ff 00 01 02 03 04
    #
    # which are then interpreted as a bit packed mode '1' image

    _pulls_fd = True

    def decode(self, buffer: bytes | Image.SupportsArrayInterface) -> tuple[int, int]:
        assert self.fd is not None

        img = io.BytesIO()
        blank_line = bytearray((0xFF,) * ((self.state.xsize + 7) // 8))
        try:
            self.fd.seek(32)
            rowmap = struct.unpack_from(
                f"<{self.state.ysize}H", self.fd.read(self.state.ysize * 2)
            )
        except struct.error as e:
            msg = "Truncated MSP file in row map"
            raise OSError(msg) from e

        for x, rowlen in enumerate(rowmap):
            try:
                if rowlen == 0:
                    img.write(blank_line)
                    continue
                row = self.fd.read(rowlen)
                if len(row) != rowlen:
                    msg = f"Truncated MSP file, expected {rowlen} bytes on row {x}"
                    raise OSError(msg)
                idx = 0
                while idx < rowlen:
                    runtype = row[idx]
                    idx += 1
                    if runtype == 0:
                        (runcount, runval) = struct.unpack_from("Bc", row, idx)
                        img.write(runval * runcount)
                        idx += 2
                    else:
                        runcount = runtype
                        img.write(row[idx : idx + runcount])
                        idx += runcount

            except struct.error as e:
                msg = f"Corrupted MSP file in row {x}"
                raise OSError(msg) from e

        self.set_as_raw(img.getvalue(), "1")

        return -1, 0


Image.register_decoder("MSP", MspDecoder)


#
# write MSP files (uncompressed only)


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    if im.mode != "1":
        msg = f"cannot write mode {im.mode} as MSP"
        raise OSError(msg)

    # create MSP header
    header = [0] * 16

    header[0], header[1] = i16(b"Da"), i16(b"nM")  # version 1
    header[2], header[3] = im.size
    header[4], header[5] = 1, 1
    header[6], header[7] = 1, 1
    header[8], header[9] = im.size

    checksum = 0
    for h in header:
        checksum = checksum ^ h
    header[12] = checksum  # FIXME: is this the right field?

    # header
    for h in header:
        fp.write(o16(h))

    # image body
    ImageFile._save(im, fp, [ImageFile._Tile("raw", (0, 0) + im.size, 32, "1")])


#
# registry

Image.register_open(MspImageFile.format, MspImageFile, _accept)
Image.register_save(MspImageFile.format, _save)

Image.register_extension(MspImageFile.format, ".msp")

# === NexusCore/openenv\Lib\site-packages\starlette\status.py ===
"""
HTTP codes
See HTTP Status Code Registry:
https://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml

And RFC 2324 - https://tools.ietf.org/html/rfc2324
"""
from __future__ import annotations

import warnings

__all__ = (
    "HTTP_100_CONTINUE",
    "HTTP_101_SWITCHING_PROTOCOLS",
    "HTTP_102_PROCESSING",
    "HTTP_103_EARLY_HINTS",
    "HTTP_200_OK",
    "HTTP_201_CREATED",
    "HTTP_202_ACCEPTED",
    "HTTP_203_NON_AUTHORITATIVE_INFORMATION",
    "HTTP_204_NO_CONTENT",
    "HTTP_205_RESET_CONTENT",
    "HTTP_206_PARTIAL_CONTENT",
    "HTTP_207_MULTI_STATUS",
    "HTTP_208_ALREADY_REPORTED",
    "HTTP_226_IM_USED",
    "HTTP_300_MULTIPLE_CHOICES",
    "HTTP_301_MOVED_PERMANENTLY",
    "HTTP_302_FOUND",
    "HTTP_303_SEE_OTHER",
    "HTTP_304_NOT_MODIFIED",
    "HTTP_305_USE_PROXY",
    "HTTP_306_RESERVED",
    "HTTP_307_TEMPORARY_REDIRECT",
    "HTTP_308_PERMANENT_REDIRECT",
    "HTTP_400_BAD_REQUEST",
    "HTTP_401_UNAUTHORIZED",
    "HTTP_402_PAYMENT_REQUIRED",
    "HTTP_403_FORBIDDEN",
    "HTTP_404_NOT_FOUND",
    "HTTP_405_METHOD_NOT_ALLOWED",
    "HTTP_406_NOT_ACCEPTABLE",
    "HTTP_407_PROXY_AUTHENTICATION_REQUIRED",
    "HTTP_408_REQUEST_TIMEOUT",
    "HTTP_409_CONFLICT",
    "HTTP_410_GONE",
    "HTTP_411_LENGTH_REQUIRED",
    "HTTP_412_PRECONDITION_FAILED",
    "HTTP_413_REQUEST_ENTITY_TOO_LARGE",
    "HTTP_414_REQUEST_URI_TOO_LONG",
    "HTTP_415_UNSUPPORTED_MEDIA_TYPE",
    "HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE",
    "HTTP_417_EXPECTATION_FAILED",
    "HTTP_418_IM_A_TEAPOT",
    "HTTP_421_MISDIRECTED_REQUEST",
    "HTTP_422_UNPROCESSABLE_ENTITY",
    "HTTP_423_LOCKED",
    "HTTP_424_FAILED_DEPENDENCY",
    "HTTP_425_TOO_EARLY",
    "HTTP_426_UPGRADE_REQUIRED",
    "HTTP_428_PRECONDITION_REQUIRED",
    "HTTP_429_TOO_MANY_REQUESTS",
    "HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE",
    "HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS",
    "HTTP_500_INTERNAL_SERVER_ERROR",
    "HTTP_501_NOT_IMPLEMENTED",
    "HTTP_502_BAD_GATEWAY",
    "HTTP_503_SERVICE_UNAVAILABLE",
    "HTTP_504_GATEWAY_TIMEOUT",
    "HTTP_505_HTTP_VERSION_NOT_SUPPORTED",
    "HTTP_506_VARIANT_ALSO_NEGOTIATES",
    "HTTP_507_INSUFFICIENT_STORAGE",
    "HTTP_508_LOOP_DETECTED",
    "HTTP_510_NOT_EXTENDED",
    "HTTP_511_NETWORK_AUTHENTICATION_REQUIRED",
    "WS_1000_NORMAL_CLOSURE",
    "WS_1001_GOING_AWAY",
    "WS_1002_PROTOCOL_ERROR",
    "WS_1003_UNSUPPORTED_DATA",
    "WS_1005_NO_STATUS_RCVD",
    "WS_1006_ABNORMAL_CLOSURE",
    "WS_1007_INVALID_FRAME_PAYLOAD_DATA",
    "WS_1008_POLICY_VIOLATION",
    "WS_1009_MESSAGE_TOO_BIG",
    "WS_1010_MANDATORY_EXT",
    "WS_1011_INTERNAL_ERROR",
    "WS_1012_SERVICE_RESTART",
    "WS_1013_TRY_AGAIN_LATER",
    "WS_1014_BAD_GATEWAY",
    "WS_1015_TLS_HANDSHAKE",
)

HTTP_100_CONTINUE = 100
HTTP_101_SWITCHING_PROTOCOLS = 101
HTTP_102_PROCESSING = 102
HTTP_103_EARLY_HINTS = 103
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_202_ACCEPTED = 202
HTTP_203_NON_AUTHORITATIVE_INFORMATION = 203
HTTP_204_NO_CONTENT = 204
HTTP_205_RESET_CONTENT = 205
HTTP_206_PARTIAL_CONTENT = 206
HTTP_207_MULTI_STATUS = 207
HTTP_208_ALREADY_REPORTED = 208
HTTP_226_IM_USED = 226
HTTP_300_MULTIPLE_CHOICES = 300
HTTP_301_MOVED_PERMANENTLY = 301
HTTP_302_FOUND = 302
HTTP_303_SEE_OTHER = 303
HTTP_304_NOT_MODIFIED = 304
HTTP_305_USE_PROXY = 305
HTTP_306_RESERVED = 306
HTTP_307_TEMPORARY_REDIRECT = 307
HTTP_308_PERMANENT_REDIRECT = 308
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_402_PAYMENT_REQUIRED = 402
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_405_METHOD_NOT_ALLOWED = 405
HTTP_406_NOT_ACCEPTABLE = 406
HTTP_407_PROXY_AUTHENTICATION_REQUIRED = 407
HTTP_408_REQUEST_TIMEOUT = 408
HTTP_409_CONFLICT = 409
HTTP_410_GONE = 410
HTTP_411_LENGTH_REQUIRED = 411
HTTP_412_PRECONDITION_FAILED = 412
HTTP_413_REQUEST_ENTITY_TOO_LARGE = 413
HTTP_414_REQUEST_URI_TOO_LONG = 414
HTTP_415_UNSUPPORTED_MEDIA_TYPE = 415
HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE = 416
HTTP_417_EXPECTATION_FAILED = 417
HTTP_418_IM_A_TEAPOT = 418
HTTP_421_MISDIRECTED_REQUEST = 421
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_423_LOCKED = 423
HTTP_424_FAILED_DEPENDENCY = 424
HTTP_425_TOO_EARLY = 425
HTTP_426_UPGRADE_REQUIRED = 426
HTTP_428_PRECONDITION_REQUIRED = 428
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE = 431
HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS = 451
HTTP_500_INTERNAL_SERVER_ERROR = 500
HTTP_501_NOT_IMPLEMENTED = 501
HTTP_502_BAD_GATEWAY = 502
HTTP_503_SERVICE_UNAVAILABLE = 503
HTTP_504_GATEWAY_TIMEOUT = 504
HTTP_505_HTTP_VERSION_NOT_SUPPORTED = 505
HTTP_506_VARIANT_ALSO_NEGOTIATES = 506
HTTP_507_INSUFFICIENT_STORAGE = 507
HTTP_508_LOOP_DETECTED = 508
HTTP_510_NOT_EXTENDED = 510
HTTP_511_NETWORK_AUTHENTICATION_REQUIRED = 511


"""
WebSocket codes
https://www.iana.org/assignments/websocket/websocket.xml#close-code-number
https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent
"""
WS_1000_NORMAL_CLOSURE = 1000
WS_1001_GOING_AWAY = 1001
WS_1002_PROTOCOL_ERROR = 1002
WS_1003_UNSUPPORTED_DATA = 1003
WS_1005_NO_STATUS_RCVD = 1005
WS_1006_ABNORMAL_CLOSURE = 1006
WS_1007_INVALID_FRAME_PAYLOAD_DATA = 1007
WS_1008_POLICY_VIOLATION = 1008
WS_1009_MESSAGE_TOO_BIG = 1009
WS_1010_MANDATORY_EXT = 1010
WS_1011_INTERNAL_ERROR = 1011
WS_1012_SERVICE_RESTART = 1012
WS_1013_TRY_AGAIN_LATER = 1013
WS_1014_BAD_GATEWAY = 1014
WS_1015_TLS_HANDSHAKE = 1015


__deprecated__ = {"WS_1004_NO_STATUS_RCVD": 1004, "WS_1005_ABNORMAL_CLOSURE": 1005}


def __getattr__(name: str) -> int:
    deprecation_changes = {
        "WS_1004_NO_STATUS_RCVD": "WS_1005_NO_STATUS_RCVD",
        "WS_1005_ABNORMAL_CLOSURE": "WS_1006_ABNORMAL_CLOSURE",
    }
    deprecated = __deprecated__.get(name)
    if deprecated:
        warnings.warn(
            f"'{name}' is deprecated. Use '{deprecation_changes[name]}' instead.",
            category=DeprecationWarning,
            stacklevel=3,
        )
        return deprecated
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    return sorted(list(__all__) + list(__deprecated__.keys()))  # pragma: no cover

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_comm_constants.py ===
CMD_RUN = 101
CMD_LIST_THREADS = 102
CMD_THREAD_CREATE = 103
CMD_THREAD_KILL = 104
CMD_THREAD_SUSPEND = 105
CMD_THREAD_RUN = 106
CMD_STEP_INTO = 107
CMD_STEP_OVER = 108
CMD_STEP_RETURN = 109
CMD_GET_VARIABLE = 110
CMD_SET_BREAK = 111
CMD_REMOVE_BREAK = 112
CMD_EVALUATE_EXPRESSION = 113
CMD_GET_FRAME = 114
CMD_EXEC_EXPRESSION = 115
CMD_WRITE_TO_CONSOLE = 116
CMD_CHANGE_VARIABLE = 117
CMD_RUN_TO_LINE = 118
CMD_RELOAD_CODE = 119
CMD_GET_COMPLETIONS = 120

# Note: renumbered (conflicted on merge)
CMD_CONSOLE_EXEC = 121
CMD_ADD_EXCEPTION_BREAK = 122
CMD_REMOVE_EXCEPTION_BREAK = 123
CMD_LOAD_SOURCE = 124
CMD_ADD_DJANGO_EXCEPTION_BREAK = 125
CMD_REMOVE_DJANGO_EXCEPTION_BREAK = 126
CMD_SET_NEXT_STATEMENT = 127
CMD_SMART_STEP_INTO = 128
CMD_EXIT = 129
CMD_SIGNATURE_CALL_TRACE = 130

CMD_SET_PY_EXCEPTION = 131
CMD_GET_FILE_CONTENTS = 132
CMD_SET_PROPERTY_TRACE = 133
# Pydev debug console commands
CMD_EVALUATE_CONSOLE_EXPRESSION = 134
CMD_RUN_CUSTOM_OPERATION = 135
CMD_GET_BREAKPOINT_EXCEPTION = 136
CMD_STEP_CAUGHT_EXCEPTION = 137
CMD_SEND_CURR_EXCEPTION_TRACE = 138
CMD_SEND_CURR_EXCEPTION_TRACE_PROCEEDED = 139
CMD_IGNORE_THROWN_EXCEPTION_AT = 140
CMD_ENABLE_DONT_TRACE = 141
CMD_SHOW_CONSOLE = 142

CMD_GET_ARRAY = 143
CMD_STEP_INTO_MY_CODE = 144
CMD_GET_CONCURRENCY_EVENT = 145
CMD_SHOW_RETURN_VALUES = 146
CMD_INPUT_REQUESTED = 147
CMD_GET_DESCRIPTION = 148

CMD_PROCESS_CREATED = 149
CMD_SHOW_CYTHON_WARNING = 150
CMD_LOAD_FULL_VALUE = 151

CMD_GET_THREAD_STACK = 152

# This is mostly for unit-tests to diagnose errors on ci.
CMD_THREAD_DUMP_TO_STDERR = 153

# Sent from the client to signal that we should stop when we start executing user code.
CMD_STOP_ON_START = 154

# When the debugger is stopped in an exception, this command will provide the details of the current exception (in the current thread).
CMD_GET_EXCEPTION_DETAILS = 155

# Allows configuring pydevd settings (can be called multiple times and only keys
# available in the json will be configured -- keys not passed will not change the
# previous configuration).
CMD_PYDEVD_JSON_CONFIG = 156

CMD_THREAD_SUSPEND_SINGLE_NOTIFICATION = 157
CMD_THREAD_RESUME_SINGLE_NOTIFICATION = 158

CMD_STEP_OVER_MY_CODE = 159
CMD_STEP_RETURN_MY_CODE = 160

CMD_SET_PY_EXCEPTION_JSON = 161
CMD_SET_PATH_MAPPING_JSON = 162

CMD_GET_SMART_STEP_INTO_VARIANTS = 163  # XXX: PyCharm has 160 for this (we're currently incompatible anyways).

CMD_REDIRECT_OUTPUT = 200
CMD_GET_NEXT_STATEMENT_TARGETS = 201
CMD_SET_PROJECT_ROOTS = 202

CMD_MODULE_EVENT = 203
CMD_PROCESS_EVENT = 204

CMD_AUTHENTICATE = 205

CMD_STEP_INTO_COROUTINE = 206

CMD_LOAD_SOURCE_FROM_FRAME_ID = 207

CMD_SET_FUNCTION_BREAK = 208

CMD_VERSION = 501
CMD_RETURN = 502
CMD_SET_PROTOCOL = 503
CMD_ERROR = 901

# this number can be changed if there's need to do so
# if the io is too big, we'll not send all (could make the debugger too non-responsive)
MAX_IO_MSG_SIZE = 10000

VERSION_STRING = "@@BUILD_NUMBER@@"

from _pydev_bundle._pydev_filesystem_encoding import getfilesystemencoding

file_system_encoding = getfilesystemencoding()
filesystem_encoding_is_utf8 = file_system_encoding.lower() in ("utf-8", "utf_8", "utf8")

ID_TO_MEANING = {
    "101": "CMD_RUN",
    "102": "CMD_LIST_THREADS",
    "103": "CMD_THREAD_CREATE",
    "104": "CMD_THREAD_KILL",
    "105": "CMD_THREAD_SUSPEND",
    "106": "CMD_THREAD_RUN",
    "107": "CMD_STEP_INTO",
    "108": "CMD_STEP_OVER",
    "109": "CMD_STEP_RETURN",
    "110": "CMD_GET_VARIABLE",
    "111": "CMD_SET_BREAK",
    "112": "CMD_REMOVE_BREAK",
    "113": "CMD_EVALUATE_EXPRESSION",
    "114": "CMD_GET_FRAME",
    "115": "CMD_EXEC_EXPRESSION",
    "116": "CMD_WRITE_TO_CONSOLE",
    "117": "CMD_CHANGE_VARIABLE",
    "118": "CMD_RUN_TO_LINE",
    "119": "CMD_RELOAD_CODE",
    "120": "CMD_GET_COMPLETIONS",
    "121": "CMD_CONSOLE_EXEC",
    "122": "CMD_ADD_EXCEPTION_BREAK",
    "123": "CMD_REMOVE_EXCEPTION_BREAK",
    "124": "CMD_LOAD_SOURCE",
    "125": "CMD_ADD_DJANGO_EXCEPTION_BREAK",
    "126": "CMD_REMOVE_DJANGO_EXCEPTION_BREAK",
    "127": "CMD_SET_NEXT_STATEMENT",
    "128": "CMD_SMART_STEP_INTO",
    "129": "CMD_EXIT",
    "130": "CMD_SIGNATURE_CALL_TRACE",
    "131": "CMD_SET_PY_EXCEPTION",
    "132": "CMD_GET_FILE_CONTENTS",
    "133": "CMD_SET_PROPERTY_TRACE",
    "134": "CMD_EVALUATE_CONSOLE_EXPRESSION",
    "135": "CMD_RUN_CUSTOM_OPERATION",
    "136": "CMD_GET_BREAKPOINT_EXCEPTION",
    "137": "CMD_STEP_CAUGHT_EXCEPTION",
    "138": "CMD_SEND_CURR_EXCEPTION_TRACE",
    "139": "CMD_SEND_CURR_EXCEPTION_TRACE_PROCEEDED",
    "140": "CMD_IGNORE_THROWN_EXCEPTION_AT",
    "141": "CMD_ENABLE_DONT_TRACE",
    "142": "CMD_SHOW_CONSOLE",
    "143": "CMD_GET_ARRAY",
    "144": "CMD_STEP_INTO_MY_CODE",
    "145": "CMD_GET_CONCURRENCY_EVENT",
    "146": "CMD_SHOW_RETURN_VALUES",
    "147": "CMD_INPUT_REQUESTED",
    "148": "CMD_GET_DESCRIPTION",
    "149": "CMD_PROCESS_CREATED",  # Note: this is actually a notification of a sub-process created.
    "150": "CMD_SHOW_CYTHON_WARNING",
    "151": "CMD_LOAD_FULL_VALUE",
    "152": "CMD_GET_THREAD_STACK",
    "153": "CMD_THREAD_DUMP_TO_STDERR",
    "154": "CMD_STOP_ON_START",
    "155": "CMD_GET_EXCEPTION_DETAILS",
    "156": "CMD_PYDEVD_JSON_CONFIG",
    "157": "CMD_THREAD_SUSPEND_SINGLE_NOTIFICATION",
    "158": "CMD_THREAD_RESUME_SINGLE_NOTIFICATION",
    "159": "CMD_STEP_OVER_MY_CODE",
    "160": "CMD_STEP_RETURN_MY_CODE",
    "161": "CMD_SET_PY_EXCEPTION_JSON",
    "162": "CMD_SET_PATH_MAPPING_JSON",
    "163": "CMD_GET_SMART_STEP_INTO_VARIANTS",
    "200": "CMD_REDIRECT_OUTPUT",
    "201": "CMD_GET_NEXT_STATEMENT_TARGETS",
    "202": "CMD_SET_PROJECT_ROOTS",
    "203": "CMD_MODULE_EVENT",
    "204": "CMD_PROCESS_EVENT",  # DAP process event.
    "205": "CMD_AUTHENTICATE",
    "206": "CMD_STEP_INTO_COROUTINE",
    "207": "CMD_LOAD_SOURCE_FROM_FRAME_ID",
    "501": "CMD_VERSION",
    "502": "CMD_RETURN",
    "503": "CMD_SET_PROTOCOL",
    "901": "CMD_ERROR",
}


def constant_to_str(constant):
    s = ID_TO_MEANING.get(str(constant))
    if not s:
        s = "<Unknown: %s>" % (constant,)
    return s

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_json_debug_options.py ===
import json
import urllib.parse as urllib_parse


class DebugOptions(object):
    __slots__ = [
        "just_my_code",
        "redirect_output",
        "show_return_value",
        "break_system_exit_zero",
        "django_debug",
        "flask_debug",
        "stop_on_entry",
        "max_exception_stack_frames",
        "gui_event_loop",
        "client_os",
    ]

    def __init__(self):
        self.just_my_code = True
        self.redirect_output = False
        self.show_return_value = False
        self.break_system_exit_zero = False
        self.django_debug = False
        self.flask_debug = False
        self.stop_on_entry = False
        self.max_exception_stack_frames = 0
        self.gui_event_loop = "matplotlib"
        self.client_os = None

    def to_json(self):
        dct = {}
        for s in self.__slots__:
            dct[s] = getattr(self, s)
        return json.dumps(dct)

    def update_fom_debug_options(self, debug_options):
        if "DEBUG_STDLIB" in debug_options:
            self.just_my_code = not debug_options.get("DEBUG_STDLIB")

        if "REDIRECT_OUTPUT" in debug_options:
            self.redirect_output = debug_options.get("REDIRECT_OUTPUT")

        if "SHOW_RETURN_VALUE" in debug_options:
            self.show_return_value = debug_options.get("SHOW_RETURN_VALUE")

        if "BREAK_SYSTEMEXIT_ZERO" in debug_options:
            self.break_system_exit_zero = debug_options.get("BREAK_SYSTEMEXIT_ZERO")

        if "DJANGO_DEBUG" in debug_options:
            self.django_debug = debug_options.get("DJANGO_DEBUG")

        if "FLASK_DEBUG" in debug_options:
            self.flask_debug = debug_options.get("FLASK_DEBUG")

        if "STOP_ON_ENTRY" in debug_options:
            self.stop_on_entry = debug_options.get("STOP_ON_ENTRY")

        if "CLIENT_OS_TYPE" in debug_options:
            self.client_os = debug_options.get("CLIENT_OS_TYPE")

        # Note: _max_exception_stack_frames cannot be set by debug options.

    def update_from_args(self, args):
        if "justMyCode" in args:
            self.just_my_code = bool_parser(args["justMyCode"])
        else:
            # i.e.: if justMyCode is provided, don't check the deprecated value
            if "debugStdLib" in args:
                self.just_my_code = not bool_parser(args["debugStdLib"])

        if "redirectOutput" in args:
            self.redirect_output = bool_parser(args["redirectOutput"])

        if "showReturnValue" in args:
            self.show_return_value = bool_parser(args["showReturnValue"])

        if "breakOnSystemExitZero" in args:
            self.break_system_exit_zero = bool_parser(args["breakOnSystemExitZero"])

        if "django" in args:
            self.django_debug = bool_parser(args["django"])

        if "flask" in args:
            self.flask_debug = bool_parser(args["flask"])

        if "jinja" in args:
            self.flask_debug = bool_parser(args["jinja"])

        if "stopOnEntry" in args:
            self.stop_on_entry = bool_parser(args["stopOnEntry"])

        self.max_exception_stack_frames = int_parser(args.get("maxExceptionStackFrames", 0))

        if "guiEventLoop" in args:
            self.gui_event_loop = str(args["guiEventLoop"])

        if "clientOS" in args:
            self.client_os = str(args["clientOS"]).upper()


def int_parser(s, default_value=0):
    try:
        return int(s)
    except Exception:
        return default_value


def bool_parser(s):
    return s in ("True", "true", "1", True, 1)


def unquote(s):
    return None if s is None else urllib_parse.unquote(s)


DEBUG_OPTIONS_PARSER = {
    "WAIT_ON_ABNORMAL_EXIT": bool_parser,
    "WAIT_ON_NORMAL_EXIT": bool_parser,
    "BREAK_SYSTEMEXIT_ZERO": bool_parser,
    "REDIRECT_OUTPUT": bool_parser,
    "DJANGO_DEBUG": bool_parser,
    "FLASK_DEBUG": bool_parser,
    "FIX_FILE_PATH_CASE": bool_parser,
    "CLIENT_OS_TYPE": unquote,
    "DEBUG_STDLIB": bool_parser,
    "STOP_ON_ENTRY": bool_parser,
    "SHOW_RETURN_VALUE": bool_parser,
    "MULTIPROCESS": bool_parser,
}

DEBUG_OPTIONS_BY_FLAG = {
    "RedirectOutput": "REDIRECT_OUTPUT=True",
    "WaitOnNormalExit": "WAIT_ON_NORMAL_EXIT=True",
    "WaitOnAbnormalExit": "WAIT_ON_ABNORMAL_EXIT=True",
    "BreakOnSystemExitZero": "BREAK_SYSTEMEXIT_ZERO=True",
    "Django": "DJANGO_DEBUG=True",
    "Flask": "FLASK_DEBUG=True",
    "Jinja": "FLASK_DEBUG=True",
    "FixFilePathCase": "FIX_FILE_PATH_CASE=True",
    "DebugStdLib": "DEBUG_STDLIB=True",
    "WindowsClient": "CLIENT_OS_TYPE=WINDOWS",
    "UnixClient": "CLIENT_OS_TYPE=UNIX",
    "StopOnEntry": "STOP_ON_ENTRY=True",
    "ShowReturnValue": "SHOW_RETURN_VALUE=True",
    "Multiprocess": "MULTIPROCESS=True",
}


def _build_debug_options(flags):
    """Build string representation of debug options from the launch config."""
    return ";".join(DEBUG_OPTIONS_BY_FLAG[flag] for flag in flags or [] if flag in DEBUG_OPTIONS_BY_FLAG)


def _parse_debug_options(opts):
    """Debug options are semicolon separated key=value pairs"""
    options = {}
    if not opts:
        return options

    for opt in opts.split(";"):
        try:
            key, value = opt.split("=")
        except ValueError:
            continue
        try:
            options[key] = DEBUG_OPTIONS_PARSER[key](value)
        except KeyError:
            continue

    return options


def _extract_debug_options(opts, flags=None):
    """Return the debug options encoded in the given value.

    "opts" is a semicolon-separated string of "key=value" pairs.
    "flags" is a list of strings.

    If flags is provided then it is used as a fallback.

    The values come from the launch config:

     {
         type:'python',
         request:'launch'|'attach',
         name:'friendly name for debug config',
         debugOptions:[
             'RedirectOutput', 'Django'
         ],
         options:'REDIRECT_OUTPUT=True;DJANGO_DEBUG=True'
     }

    Further information can be found here:

    https://code.visualstudio.com/docs/editor/debugging#_launchjson-attributes
    """
    if not opts:
        opts = _build_debug_options(flags)
    return _parse_debug_options(opts)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\commands\download.py ===
# coding=utf-8
# Copyright 2023-present, the HuggingFace Inc. team.
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
"""Contains command to download files from the Hub with the CLI.

Usage:
    huggingface-cli download --help

    # Download file
    huggingface-cli download gpt2 config.json

    # Download entire repo
    huggingface-cli download fffiloni/zeroscope --repo-type=space --revision=refs/pr/78

    # Download repo with filters
    huggingface-cli download gpt2 --include="*.safetensors"

    # Download with token
    huggingface-cli download Wauplin/private-model --token=hf_***

    # Download quietly (no progress bar, no warnings, only the returned path)
    huggingface-cli download gpt2 config.json --quiet

    # Download to local dir
    huggingface-cli download gpt2 --local-dir=./models/gpt2
"""

import warnings
from argparse import Namespace, _SubParsersAction
from typing import List, Optional

from huggingface_hub import logging
from huggingface_hub._snapshot_download import snapshot_download
from huggingface_hub.commands import BaseHuggingfaceCLICommand
from huggingface_hub.file_download import hf_hub_download
from huggingface_hub.utils import disable_progress_bars, enable_progress_bars


logger = logging.get_logger(__name__)


class DownloadCommand(BaseHuggingfaceCLICommand):
    @staticmethod
    def register_subcommand(parser: _SubParsersAction):
        download_parser = parser.add_parser("download", help="Download files from the Hub")
        download_parser.add_argument(
            "repo_id", type=str, help="ID of the repo to download from (e.g. `username/repo-name`)."
        )
        download_parser.add_argument(
            "filenames", type=str, nargs="*", help="Files to download (e.g. `config.json`, `data/metadata.jsonl`)."
        )
        download_parser.add_argument(
            "--repo-type",
            choices=["model", "dataset", "space"],
            default="model",
            help="Type of repo to download from (defaults to 'model').",
        )
        download_parser.add_argument(
            "--revision",
            type=str,
            help="An optional Git revision id which can be a branch name, a tag, or a commit hash.",
        )
        download_parser.add_argument(
            "--include", nargs="*", type=str, help="Glob patterns to match files to download."
        )
        download_parser.add_argument(
            "--exclude", nargs="*", type=str, help="Glob patterns to exclude from files to download."
        )
        download_parser.add_argument(
            "--cache-dir", type=str, help="Path to the directory where to save the downloaded files."
        )
        download_parser.add_argument(
            "--local-dir",
            type=str,
            help=(
                "If set, the downloaded file will be placed under this directory. Check out"
                " https://huggingface.co/docs/huggingface_hub/guides/download#download-files-to-local-folder for more"
                " details."
            ),
        )
        download_parser.add_argument(
            "--local-dir-use-symlinks",
            choices=["auto", "True", "False"],
            help=("Deprecated and ignored. Downloading to a local directory does not use symlinks anymore."),
        )
        download_parser.add_argument(
            "--force-download",
            action="store_true",
            help="If True, the files will be downloaded even if they are already cached.",
        )
        download_parser.add_argument(
            "--resume-download",
            action="store_true",
            help="Deprecated and ignored. Downloading a file to local dir always attempts to resume previously interrupted downloads (unless hf-transfer is enabled).",
        )
        download_parser.add_argument(
            "--token", type=str, help="A User Access Token generated from https://huggingface.co/settings/tokens"
        )
        download_parser.add_argument(
            "--quiet",
            action="store_true",
            help="If True, progress bars are disabled and only the path to the download files is printed.",
        )
        download_parser.add_argument(
            "--max-workers",
            type=int,
            default=8,
            help="Maximum number of workers to use for downloading files. Default is 8.",
        )
        download_parser.set_defaults(func=DownloadCommand)

    def __init__(self, args: Namespace) -> None:
        self.token = args.token
        self.repo_id: str = args.repo_id
        self.filenames: List[str] = args.filenames
        self.repo_type: str = args.repo_type
        self.revision: Optional[str] = args.revision
        self.include: Optional[List[str]] = args.include
        self.exclude: Optional[List[str]] = args.exclude
        self.cache_dir: Optional[str] = args.cache_dir
        self.local_dir: Optional[str] = args.local_dir
        self.force_download: bool = args.force_download
        self.resume_download: Optional[bool] = args.resume_download or None
        self.quiet: bool = args.quiet
        self.max_workers: int = args.max_workers

        if args.local_dir_use_symlinks is not None:
            warnings.warn(
                "Ignoring --local-dir-use-symlinks. Downloading to a local directory does not use symlinks anymore.",
                FutureWarning,
            )

    def run(self) -> None:
        if self.quiet:
            disable_progress_bars()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                print(self._download())  # Print path to downloaded files
            enable_progress_bars()
        else:
            logging.set_verbosity_info()
            print(self._download())  # Print path to downloaded files
            logging.set_verbosity_warning()

    def _download(self) -> str:
        # Warn user if patterns are ignored
        if len(self.filenames) > 0:
            if self.include is not None and len(self.include) > 0:
                warnings.warn("Ignoring `--include` since filenames have being explicitly set.")
            if self.exclude is not None and len(self.exclude) > 0:
                warnings.warn("Ignoring `--exclude` since filenames have being explicitly set.")

        # Single file to download: use `hf_hub_download`
        if len(self.filenames) == 1:
            return hf_hub_download(
                repo_id=self.repo_id,
                repo_type=self.repo_type,
                revision=self.revision,
                filename=self.filenames[0],
                cache_dir=self.cache_dir,
                resume_download=self.resume_download,
                force_download=self.force_download,
                token=self.token,
                local_dir=self.local_dir,
                library_name="huggingface-cli",
            )

        # Otherwise: use `snapshot_download` to ensure all files comes from same revision
        elif len(self.filenames) == 0:
            allow_patterns = self.include
            ignore_patterns = self.exclude
        else:
            allow_patterns = self.filenames
            ignore_patterns = None

        return snapshot_download(
            repo_id=self.repo_id,
            repo_type=self.repo_type,
            revision=self.revision,
            allow_patterns=allow_patterns,
            ignore_patterns=ignore_patterns,
            resume_download=self.resume_download,
            force_download=self.force_download,
            cache_dir=self.cache_dir,
            token=self.token,
            local_dir=self.local_dir,
            library_name="huggingface-cli",
            max_workers=self.max_workers,
        )

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\commands\lfs.py ===
"""
Implementation of a custom transfer agent for the transfer type "multipart" for
git-lfs.

Inspired by:
github.com/cbartz/git-lfs-swift-transfer-agent/blob/master/git_lfs_swift_transfer.py

Spec is: github.com/git-lfs/git-lfs/blob/master/docs/custom-transfers.md


To launch debugger while developing:

``` [lfs "customtransfer.multipart"]
path = /path/to/huggingface_hub/.env/bin/python args = -m debugpy --listen 5678
--wait-for-client
/path/to/huggingface_hub/src/huggingface_hub/commands/huggingface_cli.py
lfs-multipart-upload ```"""

import json
import os
import subprocess
import sys
from argparse import _SubParsersAction
from typing import Dict, List, Optional

from huggingface_hub.commands import BaseHuggingfaceCLICommand
from huggingface_hub.lfs import LFS_MULTIPART_UPLOAD_COMMAND

from ..utils import get_session, hf_raise_for_status, logging
from ..utils._lfs import SliceFileObj


logger = logging.get_logger(__name__)


class LfsCommands(BaseHuggingfaceCLICommand):
    """
    Implementation of a custom transfer agent for the transfer type "multipart"
    for git-lfs. This lets users upload large files >5GB 🔥. Spec for LFS custom
    transfer agent is:
    https://github.com/git-lfs/git-lfs/blob/master/docs/custom-transfers.md

    This introduces two commands to the CLI:

    1. $ huggingface-cli lfs-enable-largefiles

    This should be executed once for each model repo that contains a model file
    >5GB. It's documented in the error message you get if you just try to git
    push a 5GB file without having enabled it before.

    2. $ huggingface-cli lfs-multipart-upload

    This command is called by lfs directly and is not meant to be called by the
    user.
    """

    @staticmethod
    def register_subcommand(parser: _SubParsersAction):
        enable_parser = parser.add_parser(
            "lfs-enable-largefiles", help="Configure your repository to enable upload of files > 5GB."
        )
        enable_parser.add_argument("path", type=str, help="Local path to repository you want to configure.")
        enable_parser.set_defaults(func=lambda args: LfsEnableCommand(args))

        # Command will get called by git-lfs, do not call it directly.
        upload_parser = parser.add_parser(LFS_MULTIPART_UPLOAD_COMMAND, add_help=False)
        upload_parser.set_defaults(func=lambda args: LfsUploadCommand(args))


class LfsEnableCommand:
    def __init__(self, args):
        self.args = args

    def run(self):
        local_path = os.path.abspath(self.args.path)
        if not os.path.isdir(local_path):
            print("This does not look like a valid git repo.")
            exit(1)
        subprocess.run(
            "git config lfs.customtransfer.multipart.path huggingface-cli".split(),
            check=True,
            cwd=local_path,
        )
        subprocess.run(
            f"git config lfs.customtransfer.multipart.args {LFS_MULTIPART_UPLOAD_COMMAND}".split(),
            check=True,
            cwd=local_path,
        )
        print("Local repo set up for largefiles")


def write_msg(msg: Dict):
    """Write out the message in Line delimited JSON."""
    msg_str = json.dumps(msg) + "\n"
    sys.stdout.write(msg_str)
    sys.stdout.flush()


def read_msg() -> Optional[Dict]:
    """Read Line delimited JSON from stdin."""
    msg = json.loads(sys.stdin.readline().strip())

    if "terminate" in (msg.get("type"), msg.get("event")):
        # terminate message received
        return None

    if msg.get("event") not in ("download", "upload"):
        logger.critical("Received unexpected message")
        sys.exit(1)

    return msg


class LfsUploadCommand:
    def __init__(self, args) -> None:
        self.args = args

    def run(self) -> None:
        # Immediately after invoking a custom transfer process, git-lfs
        # sends initiation data to the process over stdin.
        # This tells the process useful information about the configuration.
        init_msg = json.loads(sys.stdin.readline().strip())
        if not (init_msg.get("event") == "init" and init_msg.get("operation") == "upload"):
            write_msg({"error": {"code": 32, "message": "Wrong lfs init operation"}})
            sys.exit(1)

        # The transfer process should use the information it needs from the
        # initiation structure, and also perform any one-off setup tasks it
        # needs to do. It should then respond on stdout with a simple empty
        # confirmation structure, as follows:
        write_msg({})

        # After the initiation exchange, git-lfs will send any number of
        # transfer requests to the stdin of the transfer process, in a serial sequence.
        while True:
            msg = read_msg()
            if msg is None:
                # When all transfers have been processed, git-lfs will send
                # a terminate event to the stdin of the transfer process.
                # On receiving this message the transfer process should
                # clean up and terminate. No response is expected.
                sys.exit(0)

            oid = msg["oid"]
            filepath = msg["path"]
            completion_url = msg["action"]["href"]
            header = msg["action"]["header"]
            chunk_size = int(header.pop("chunk_size"))
            presigned_urls: List[str] = list(header.values())

            # Send a "started" progress event to allow other workers to start.
            # Otherwise they're delayed until first "progress" event is reported,
            # i.e. after the first 5GB by default (!)
            write_msg(
                {
                    "event": "progress",
                    "oid": oid,
                    "bytesSoFar": 1,
                    "bytesSinceLast": 0,
                }
            )

            parts = []
            with open(filepath, "rb") as file:
                for i, presigned_url in enumerate(presigned_urls):
                    with SliceFileObj(
                        file,
                        seek_from=i * chunk_size,
                        read_limit=chunk_size,
                    ) as data:
                        r = get_session().put(presigned_url, data=data)
                        hf_raise_for_status(r)
                        parts.append(
                            {
                                "etag": r.headers.get("etag"),
                                "partNumber": i + 1,
                            }
                        )
                        # In order to support progress reporting while data is uploading / downloading,
                        # the transfer process should post messages to stdout
                        write_msg(
                            {
                                "event": "progress",
                                "oid": oid,
                                "bytesSoFar": (i + 1) * chunk_size,
                                "bytesSinceLast": chunk_size,
                            }
                        )
                        # Not precise but that's ok.

            r = get_session().post(
                completion_url,
                json={
                    "oid": oid,
                    "parts": parts,
                },
            )
            hf_raise_for_status(r)

            write_msg({"event": "complete", "oid": oid})

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_providers\hf_inference.py ===
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Union

from huggingface_hub import constants
from huggingface_hub.hf_api import InferenceProviderMapping
from huggingface_hub.inference._common import RequestParameters, _b64_encode, _bytes_to_dict, _open_as_binary
from huggingface_hub.inference._providers._common import TaskProviderHelper, filter_none
from huggingface_hub.utils import build_hf_headers, get_session, get_token, hf_raise_for_status


class HFInferenceTask(TaskProviderHelper):
    """Base class for HF Inference API tasks."""

    def __init__(self, task: str):
        super().__init__(
            provider="hf-inference",
            base_url=constants.INFERENCE_PROXY_TEMPLATE.format(provider="hf-inference"),
            task=task,
        )

    def _prepare_api_key(self, api_key: Optional[str]) -> str:
        # special case: for HF Inference we allow not providing an API key
        return api_key or get_token()  # type: ignore[return-value]

    def _prepare_mapping_info(self, model: Optional[str]) -> InferenceProviderMapping:
        if model is not None and model.startswith(("http://", "https://")):
            return InferenceProviderMapping(
                provider="hf-inference", providerId=model, hf_model_id=model, task=self.task, status="live"
            )
        model_id = model if model is not None else _fetch_recommended_models().get(self.task)
        if model_id is None:
            raise ValueError(
                f"Task {self.task} has no recommended model for HF Inference. Please specify a model"
                " explicitly. Visit https://huggingface.co/tasks for more info."
            )
        _check_supported_task(model_id, self.task)
        return InferenceProviderMapping(
            provider="hf-inference", providerId=model_id, hf_model_id=model_id, task=self.task, status="live"
        )

    def _prepare_url(self, api_key: str, mapped_model: str) -> str:
        # hf-inference provider can handle URLs (e.g. Inference Endpoints or TGI deployment)
        if mapped_model.startswith(("http://", "https://")):
            return mapped_model
        return (
            # Feature-extraction and sentence-similarity are the only cases where we handle models with several tasks.
            f"{self.base_url}/models/{mapped_model}/pipeline/{self.task}"
            if self.task in ("feature-extraction", "sentence-similarity")
            # Otherwise, we use the default endpoint
            else f"{self.base_url}/models/{mapped_model}"
        )

    def _prepare_payload_as_dict(
        self, inputs: Any, parameters: Dict, provider_mapping_info: InferenceProviderMapping
    ) -> Optional[Dict]:
        if isinstance(inputs, bytes):
            raise ValueError(f"Unexpected binary input for task {self.task}.")
        if isinstance(inputs, Path):
            raise ValueError(f"Unexpected path input for task {self.task} (got {inputs})")
        return {"inputs": inputs, "parameters": filter_none(parameters)}


class HFInferenceBinaryInputTask(HFInferenceTask):
    def _prepare_payload_as_dict(
        self, inputs: Any, parameters: Dict, provider_mapping_info: InferenceProviderMapping
    ) -> Optional[Dict]:
        return None

    def _prepare_payload_as_bytes(
        self,
        inputs: Any,
        parameters: Dict,
        provider_mapping_info: InferenceProviderMapping,
        extra_payload: Optional[Dict],
    ) -> Optional[bytes]:
        parameters = filter_none({k: v for k, v in parameters.items() if v is not None})
        extra_payload = extra_payload or {}
        has_parameters = len(parameters) > 0 or len(extra_payload) > 0

        # Raise if not a binary object or a local path or a URL.
        if not isinstance(inputs, (bytes, Path)) and not isinstance(inputs, str):
            raise ValueError(f"Expected binary inputs or a local path or a URL. Got {inputs}")

        # Send inputs as raw content when no parameters are provided
        if not has_parameters:
            with _open_as_binary(inputs) as data:
                data_as_bytes = data if isinstance(data, bytes) else data.read()
                return data_as_bytes

        # Otherwise encode as b64
        return json.dumps({"inputs": _b64_encode(inputs), "parameters": parameters, **extra_payload}).encode("utf-8")


class HFInferenceConversational(HFInferenceTask):
    def __init__(self):
        super().__init__("conversational")

    def _prepare_payload_as_dict(
        self, inputs: Any, parameters: Dict, provider_mapping_info: InferenceProviderMapping
    ) -> Optional[Dict]:
        payload = filter_none(parameters)
        mapped_model = provider_mapping_info.provider_id
        payload_model = parameters.get("model") or mapped_model

        if payload_model is None or payload_model.startswith(("http://", "https://")):
            payload_model = "dummy"

        response_format = parameters.get("response_format")
        if isinstance(response_format, dict) and response_format.get("type") == "json_schema":
            payload["response_format"] = {
                "type": "json_object",
                "value": response_format["json_schema"]["schema"],
            }
        return {**payload, "model": payload_model, "messages": inputs}

    def _prepare_url(self, api_key: str, mapped_model: str) -> str:
        base_url = (
            mapped_model
            if mapped_model.startswith(("http://", "https://"))
            else f"{constants.INFERENCE_PROXY_TEMPLATE.format(provider='hf-inference')}/models/{mapped_model}"
        )
        return _build_chat_completion_url(base_url)


def _build_chat_completion_url(model_url: str) -> str:
    # Strip trailing /
    model_url = model_url.rstrip("/")

    # Append /chat/completions if not already present
    if model_url.endswith("/v1"):
        model_url += "/chat/completions"

    # Append /v1/chat/completions if not already present
    if not model_url.endswith("/chat/completions"):
        model_url += "/v1/chat/completions"

    return model_url


@lru_cache(maxsize=1)
def _fetch_recommended_models() -> Dict[str, Optional[str]]:
    response = get_session().get(f"{constants.ENDPOINT}/api/tasks", headers=build_hf_headers())
    hf_raise_for_status(response)
    return {task: next(iter(details["widgetModels"]), None) for task, details in response.json().items()}


@lru_cache(maxsize=None)
def _check_supported_task(model: str, task: str) -> None:
    from huggingface_hub.hf_api import HfApi

    model_info = HfApi().model_info(model)
    pipeline_tag = model_info.pipeline_tag
    tags = model_info.tags or []
    is_conversational = "conversational" in tags
    if task in ("text-generation", "conversational"):
        if pipeline_tag == "text-generation":
            # text-generation + conversational tag -> both tasks allowed
            if is_conversational:
                return
            # text-generation without conversational tag -> only text-generation allowed
            if task == "text-generation":
                return
            raise ValueError(f"Model '{model}' doesn't support task '{task}'.")

    if pipeline_tag == "text2text-generation":
        if task == "text-generation":
            return
        raise ValueError(f"Model '{model}' doesn't support task '{task}'.")

    if pipeline_tag == "image-text-to-text":
        if is_conversational and task == "conversational":
            return  # Only conversational allowed if tagged as conversational
        raise ValueError("Non-conversational image-text-to-text task is not supported.")

    if (
        task in ("feature-extraction", "sentence-similarity")
        and pipeline_tag in ("feature-extraction", "sentence-similarity")
        and task in tags
    ):
        # feature-extraction and sentence-similarity are interchangeable for HF Inference
        return

    # For all other tasks, just check pipeline tag
    if pipeline_tag != task:
        raise ValueError(
            f"Model '{model}' doesn't support task '{task}'. Supported tasks: '{pipeline_tag}', got: '{task}'"
        )
    return


class HFInferenceFeatureExtractionTask(HFInferenceTask):
    def __init__(self):
        super().__init__("feature-extraction")

    def get_response(self, response: Union[bytes, Dict], request_params: Optional[RequestParameters] = None) -> Any:
        if isinstance(response, bytes):
            return _bytes_to_dict(response)
        return response

# === NexusCore/openenv\Lib\site-packages\jedi\inference\value\dynamic_arrays.py ===
"""
A module to deal with stuff like `list.append` and `set.add`.

Array modifications
*******************

If the content of an array (``set``/``list``) is requested somewhere, the
current module will be checked for appearances of ``arr.append``,
``arr.insert``, etc.  If the ``arr`` name points to an actual array, the
content will be added

This can be really cpu intensive, as you can imagine. Because |jedi| has to
follow **every** ``append`` and check whether it's the right array. However this
works pretty good, because in *slow* cases, the recursion detector and other
settings will stop this process.

It is important to note that:

1. Array modifications work only in the current module.
2. Jedi only checks Array additions; ``list.pop``, etc are ignored.
"""
from jedi import debug
from jedi import settings
from jedi.inference import recursion
from jedi.inference.base_value import ValueSet, NO_VALUES, HelperValueMixin, \
    ValueWrapper
from jedi.inference.lazy_value import LazyKnownValues
from jedi.inference.helpers import infer_call_of_leaf
from jedi.inference.cache import inference_state_method_cache

_sentinel = object()


def check_array_additions(context, sequence):
    """ Just a mapper function for the internal _internal_check_array_additions """
    if sequence.array_type not in ('list', 'set'):
        # TODO also check for dict updates
        return NO_VALUES

    return _internal_check_array_additions(context, sequence)


@inference_state_method_cache(default=NO_VALUES)
@debug.increase_indent
def _internal_check_array_additions(context, sequence):
    """
    Checks if a `Array` has "add" (append, insert, extend) statements:

    >>> a = [""]
    >>> a.append(1)
    """
    from jedi.inference import arguments

    debug.dbg('Dynamic array search for %s' % sequence, color='MAGENTA')
    module_context = context.get_root_context()
    if not settings.dynamic_array_additions or module_context.is_compiled():
        debug.dbg('Dynamic array search aborted.', color='MAGENTA')
        return NO_VALUES

    def find_additions(context, arglist, add_name):
        params = list(arguments.TreeArguments(context.inference_state, context, arglist).unpack())
        result = set()
        if add_name in ['insert']:
            params = params[1:]
        if add_name in ['append', 'add', 'insert']:
            for key, lazy_value in params:
                result.add(lazy_value)
        elif add_name in ['extend', 'update']:
            for key, lazy_value in params:
                result |= set(lazy_value.infer().iterate())
        return result

    temp_param_add, settings.dynamic_params_for_other_modules = \
        settings.dynamic_params_for_other_modules, False

    is_list = sequence.name.string_name == 'list'
    search_names = (['append', 'extend', 'insert'] if is_list else ['add', 'update'])

    added_types = set()
    for add_name in search_names:
        try:
            possible_names = module_context.tree_node.get_used_names()[add_name]
        except KeyError:
            continue
        else:
            for name in possible_names:
                value_node = context.tree_node
                if not (value_node.start_pos < name.start_pos < value_node.end_pos):
                    continue
                trailer = name.parent
                power = trailer.parent
                trailer_pos = power.children.index(trailer)
                try:
                    execution_trailer = power.children[trailer_pos + 1]
                except IndexError:
                    continue
                else:
                    if execution_trailer.type != 'trailer' \
                            or execution_trailer.children[0] != '(' \
                            or execution_trailer.children[1] == ')':
                        continue

                random_context = context.create_context(name)

                with recursion.execution_allowed(context.inference_state, power) as allowed:
                    if allowed:
                        found = infer_call_of_leaf(
                            random_context,
                            name,
                            cut_own_trailer=True
                        )
                        if sequence in found:
                            # The arrays match. Now add the results
                            added_types |= find_additions(
                                random_context,
                                execution_trailer.children[1],
                                add_name
                            )

    # reset settings
    settings.dynamic_params_for_other_modules = temp_param_add
    debug.dbg('Dynamic array result %s', added_types, color='MAGENTA')
    return added_types


def get_dynamic_array_instance(instance, arguments):
    """Used for set() and list() instances."""
    ai = _DynamicArrayAdditions(instance, arguments)
    from jedi.inference import arguments
    return arguments.ValuesArguments([ValueSet([ai])])


class _DynamicArrayAdditions(HelperValueMixin):
    """
    Used for the usage of set() and list().
    This is definitely a hack, but a good one :-)
    It makes it possible to use set/list conversions.

    This is not a proper context, because it doesn't have to be. It's not used
    in the wild, it's just used within typeshed as an argument to `__init__`
    for set/list and never used in any other place.
    """
    def __init__(self, instance, arguments):
        self._instance = instance
        self._arguments = arguments

    def py__class__(self):
        tuple_, = self._instance.inference_state.builtins_module.py__getattribute__('tuple')
        return tuple_

    def py__iter__(self, contextualized_node=None):
        arguments = self._arguments
        try:
            _, lazy_value = next(arguments.unpack())
        except StopIteration:
            pass
        else:
            yield from lazy_value.infer().iterate()

        from jedi.inference.arguments import TreeArguments
        if isinstance(arguments, TreeArguments):
            additions = _internal_check_array_additions(arguments.context, self._instance)
            yield from additions

    def iterate(self, contextualized_node=None, is_async=False):
        return self.py__iter__(contextualized_node)


class _Modification(ValueWrapper):
    def __init__(self, wrapped_value, assigned_values, contextualized_key):
        super().__init__(wrapped_value)
        self._assigned_values = assigned_values
        self._contextualized_key = contextualized_key

    def py__getitem__(self, *args, **kwargs):
        return self._wrapped_value.py__getitem__(*args, **kwargs) | self._assigned_values

    def py__simple_getitem__(self, index):
        actual = [
            v.get_safe_value(_sentinel)
            for v in self._contextualized_key.infer()
        ]
        if index in actual:
            return self._assigned_values
        return self._wrapped_value.py__simple_getitem__(index)


class DictModification(_Modification):
    def py__iter__(self, contextualized_node=None):
        yield from self._wrapped_value.py__iter__(contextualized_node)
        yield self._contextualized_key

    def get_key_values(self):
        return self._wrapped_value.get_key_values() | self._contextualized_key.infer()


class ListModification(_Modification):
    def py__iter__(self, contextualized_node=None):
        yield from self._wrapped_value.py__iter__(contextualized_node)
        yield LazyKnownValues(self._assigned_values)

# === NexusCore/openenv\Lib\site-packages\jupyter_client\provisioning\factory.py ===
"""Kernel Provisioner Classes"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import glob
import sys
from os import getenv, path
from typing import Any, Dict, List

# See compatibility note on `group` keyword in https://docs.python.org/3/library/importlib.metadata.html#entry-points
if sys.version_info < (3, 10):  # pragma: no cover
    from importlib_metadata import EntryPoint, entry_points  # type:ignore[import-not-found]
else:  # pragma: no cover
    from importlib.metadata import EntryPoint, entry_points

from traitlets.config import SingletonConfigurable, Unicode, default

from .provisioner_base import KernelProvisionerBase


class KernelProvisionerFactory(SingletonConfigurable):
    """
    :class:`KernelProvisionerFactory` is responsible for creating provisioner instances.

    A singleton instance, `KernelProvisionerFactory` is also used by the :class:`KernelSpecManager`
    to validate `kernel_provisioner` references found in kernel specifications to confirm their
    availability (in cases where the kernel specification references a kernel provisioner that has
    not been installed into the current Python environment).

    It's ``default_provisioner_name`` attribute can be used to specify the default provisioner
    to use when a kernel_spec is found to not reference a provisioner.  It's value defaults to
    `"local-provisioner"` which identifies the local provisioner implemented by
    :class:`LocalProvisioner`.
    """

    GROUP_NAME = "jupyter_client.kernel_provisioners"
    provisioners: Dict[str, EntryPoint] = {}

    default_provisioner_name_env = "JUPYTER_DEFAULT_PROVISIONER_NAME"
    default_provisioner_name = Unicode(
        config=True,
        help="""Indicates the name of the provisioner to use when no kernel_provisioner
                                       entry is present in the kernelspec.""",
    )

    @default("default_provisioner_name")
    def _default_provisioner_name_default(self) -> str:
        """The default provisioner name."""
        return getenv(self.default_provisioner_name_env, "local-provisioner")

    def __init__(self, **kwargs: Any) -> None:
        """Initialize a kernel provisioner factory."""
        super().__init__(**kwargs)

        for ep in KernelProvisionerFactory._get_all_provisioners():
            self.provisioners[ep.name] = ep

    def is_provisioner_available(self, kernel_spec: Any) -> bool:
        """
        Reads the associated ``kernel_spec`` to determine the provisioner and returns whether it
        exists as an entry_point (True) or not (False).  If the referenced provisioner is not
        in the current cache or cannot be loaded via entry_points, a warning message is issued
        indicating it is not available.
        """
        is_available: bool = True
        provisioner_cfg = self._get_provisioner_config(kernel_spec)
        provisioner_name = str(provisioner_cfg.get("provisioner_name"))
        if not self._check_availability(provisioner_name):
            is_available = False
            self.log.warning(
                f"Kernel '{kernel_spec.display_name}' is referencing a kernel "
                f"provisioner ('{provisioner_name}') that is not available.  "
                f"Ensure the appropriate package has been installed and retry."
            )
        return is_available

    def create_provisioner_instance(
        self, kernel_id: str, kernel_spec: Any, parent: Any
    ) -> KernelProvisionerBase:
        """
        Reads the associated ``kernel_spec`` to see if it has a `kernel_provisioner` stanza.
        If one exists, it instantiates an instance.  If a kernel provisioner is not
        specified in the kernel specification, a default provisioner stanza is fabricated
        and instantiated corresponding to the current value of ``default_provisioner_name`` trait.
        The instantiated instance is returned.

        If the provisioner is found to not exist (not registered via entry_points),
        `ModuleNotFoundError` is raised.
        """
        provisioner_cfg = self._get_provisioner_config(kernel_spec)
        provisioner_name = str(provisioner_cfg.get("provisioner_name"))
        if not self._check_availability(provisioner_name):
            msg = f"Kernel provisioner '{provisioner_name}' has not been registered."
            raise ModuleNotFoundError(msg)

        self.log.debug(
            f"Instantiating kernel '{kernel_spec.display_name}' with "
            f"kernel provisioner: {provisioner_name}"
        )
        provisioner_class = self.provisioners[provisioner_name].load()
        provisioner_config = provisioner_cfg.get("config")
        provisioner: KernelProvisionerBase = provisioner_class(
            kernel_id=kernel_id, kernel_spec=kernel_spec, parent=parent, **provisioner_config
        )
        return provisioner

    def _check_availability(self, provisioner_name: str) -> bool:
        """
        Checks that the given provisioner is available.

        If the given provisioner is not in the current set of loaded provisioners an attempt
        is made to fetch the named entry point and, if successful, loads it into the cache.

        :param provisioner_name:
        :return:
        """
        is_available = True
        if provisioner_name not in self.provisioners:
            try:
                ep = self._get_provisioner(provisioner_name)
                self.provisioners[provisioner_name] = ep  # Update cache
            except Exception:
                is_available = False
        return is_available

    def _get_provisioner_config(self, kernel_spec: Any) -> Dict[str, Any]:
        """
        Return the kernel_provisioner stanza from the kernel_spec.

        Checks the kernel_spec's metadata dictionary for a kernel_provisioner entry.
        If found, it is returned, else one is created relative to the DEFAULT_PROVISIONER
        and returned.

        Parameters
        ----------
        kernel_spec : Any - this is a KernelSpec type but listed as Any to avoid circular import
            The kernel specification object from which the provisioner dictionary is derived.

        Returns
        -------
        dict
            The provisioner portion of the kernel_spec.  If one does not exist, it will contain
            the default information.  If no `config` sub-dictionary exists, an empty `config`
            dictionary will be added.
        """
        env_provisioner = kernel_spec.metadata.get("kernel_provisioner", {})
        if "provisioner_name" in env_provisioner:  # If no provisioner_name, return default
            if (
                "config" not in env_provisioner
            ):  # if provisioner_name, but no config stanza, add one
                env_provisioner.update({"config": {}})
            return env_provisioner  # Return what we found (plus config stanza if necessary)
        return {"provisioner_name": self.default_provisioner_name, "config": {}}

    def get_provisioner_entries(self) -> Dict[str, str]:
        """
        Returns a dictionary of provisioner entries.

        The key is the provisioner name for its entry point.  The value is the colon-separated
        string of the entry point's module name and object name.
        """
        entries = {}
        for name, ep in self.provisioners.items():
            entries[name] = ep.value
        return entries

    @staticmethod
    def _get_all_provisioners() -> List[EntryPoint]:
        """Wrapper around entry_points (to fetch the set of provisioners) - primarily to facilitate testing."""
        return entry_points(group=KernelProvisionerFactory.GROUP_NAME)

    def _get_provisioner(self, name: str) -> EntryPoint:
        """Wrapper around entry_points (to fetch a single provisioner) - primarily to facilitate testing."""
        eps = entry_points(group=KernelProvisionerFactory.GROUP_NAME, name=name)
        if eps:
            return eps[0]

        # Check if the entrypoint name is 'local-provisioner'.  Although this should never
        # happen, we have seen cases where the previous distribution of jupyter_client has
        # remained which doesn't include kernel-provisioner entrypoints (so 'local-provisioner'
        # is deemed not found even though its definition is in THIS package).  In such cases,
        # the entrypoints package uses what it first finds - which is the older distribution
        # resulting in a violation of a supposed invariant condition.  To address this scenario,
        # we will log a warning message indicating this situation, then build the entrypoint
        # instance ourselves - since we have that information.
        if name == "local-provisioner":
            distros = glob.glob(f"{path.dirname(path.dirname(__file__))}-*")
            self.log.warning(
                f"Kernel Provisioning: The 'local-provisioner' is not found.  This is likely "
                f"due to the presence of multiple jupyter_client distributions and a previous "
                f"distribution is being used as the source for entrypoints - which does not "
                f"include 'local-provisioner'.  That distribution should be removed such that "
                f"only the version-appropriate distribution remains (version >= 7).  Until "
                f"then, a 'local-provisioner' entrypoint will be automatically constructed "
                f"and used.\nThe candidate distribution locations are: {distros}"
            )
            return EntryPoint(
                "local-provisioner", "jupyter_client.provisioning", "LocalProvisioner"
            )

        raise

# === NexusCore/openenv\Lib\site-packages\litellm\types\integrations\slack_alerting.py ===
import os
from datetime import datetime as dt
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Set, TypedDict

from pydantic import BaseModel, Field

from litellm.types.utils import LiteLLMPydanticObjectBase

SLACK_ALERTING_THRESHOLD_5_PERCENT = 0.05
SLACK_ALERTING_THRESHOLD_15_PERCENT = 0.15
MAX_OLDEST_HANGING_REQUESTS_TO_CHECK = 20
HANGING_ALERT_BUFFER_TIME_SECONDS = 60


class BaseOutageModel(TypedDict):
    alerts: List[int]
    minor_alert_sent: bool
    major_alert_sent: bool
    last_updated_at: float


class OutageModel(BaseOutageModel):
    model_id: str


class ProviderRegionOutageModel(BaseOutageModel):
    provider_region_id: str
    deployment_ids: Set[str]


# we use this for the email header, please send a test email if you change this. verify it looks good on email
LITELLM_LOGO_URL = "https://litellm-listing.s3.amazonaws.com/litellm_logo.png"
LITELLM_SUPPORT_CONTACT = "support@berri.ai"


class SlackAlertingArgsEnum(Enum):
    daily_report_frequency = 12 * 60 * 60
    report_check_interval = 5 * 60
    budget_alert_ttl = 24 * 60 * 60
    outage_alert_ttl = 1 * 60
    region_outage_alert_ttl = 1 * 60
    minor_outage_alert_threshold = 1 * 5
    major_outage_alert_threshold = 1 * 10
    max_outage_alert_list_size = 1 * 10


class SlackAlertingArgs(LiteLLMPydanticObjectBase):
    daily_report_frequency: int = Field(
        default=int(
            os.getenv(
                "SLACK_DAILY_REPORT_FREQUENCY",
                int(SlackAlertingArgsEnum.daily_report_frequency.value),
            )
        ),
        description="Frequency of receiving deployment latency/failure reports. Default is 12hours. Value is in seconds.",
    )
    report_check_interval: int = Field(
        default=SlackAlertingArgsEnum.report_check_interval.value,
        description="Frequency of checking cache if report should be sent. Background process. Default is once per hour. Value is in seconds.",
    )  # 5 minutes
    budget_alert_ttl: int = Field(
        default=SlackAlertingArgsEnum.budget_alert_ttl.value,
        description="Cache ttl for budgets alerts. Prevents spamming same alert, each time budget is crossed. Value is in seconds.",
    )  # 24 hours
    outage_alert_ttl: int = Field(
        default=SlackAlertingArgsEnum.outage_alert_ttl.value,
        description="Cache ttl for model outage alerts. Sets time-window for errors. Default is 1 minute. Value is in seconds.",
    )  # 1 minute ttl
    region_outage_alert_ttl: int = Field(
        default=SlackAlertingArgsEnum.region_outage_alert_ttl.value,
        description="Cache ttl for provider-region based outage alerts. Alert sent if 2+ models in same region report errors. Sets time-window for errors. Default is 1 minute. Value is in seconds.",
    )  # 1 minute ttl
    minor_outage_alert_threshold: int = Field(
        default=SlackAlertingArgsEnum.minor_outage_alert_threshold.value,
        description="The number of errors that count as a model/region minor outage. ('400' error code is not counted).",
    )
    major_outage_alert_threshold: int = Field(
        default=SlackAlertingArgsEnum.major_outage_alert_threshold.value,
        description="The number of errors that countas a model/region major outage. ('400' error code is not counted).",
    )
    max_outage_alert_list_size: int = Field(
        default=SlackAlertingArgsEnum.max_outage_alert_list_size.value,
        description="Maximum number of errors to store in cache. For a given model/region. Prevents memory leaks.",
    )  # prevent memory leak
    log_to_console: bool = Field(
        default=False,
        description="If true, the alerting payload will be printed to the console.",
    )


class DeploymentMetrics(LiteLLMPydanticObjectBase):
    """
    Metrics per deployment, stored in cache

    Used for daily reporting
    """

    id: str
    """id of deployment in router model list"""

    failed_request: bool
    """did it fail the request?"""

    latency_per_output_token: Optional[float]
    """latency/output token of deployment"""

    updated_at: dt
    """Current time of deployment being updated"""


class SlackAlertingCacheKeys(Enum):
    """
    Enum for deployment daily metrics keys - {deployment_id}:{enum}
    """

    failed_requests_key = "failed_requests_daily_metrics"
    latency_key = "latency_daily_metrics"
    report_sent_key = "daily_metrics_report_sent"


class AlertType(str, Enum):
    """
    Enum for alert types and management event types
    """

    # LLM-related alerts
    llm_exceptions = "llm_exceptions"
    llm_too_slow = "llm_too_slow"
    llm_requests_hanging = "llm_requests_hanging"

    # Budget and spend alerts
    budget_alerts = "budget_alerts"
    spend_reports = "spend_reports"
    failed_tracking_spend = "failed_tracking_spend"

    # Database alerts
    db_exceptions = "db_exceptions"

    # Report alerts
    daily_reports = "daily_reports"

    # Deployment alerts
    cooldown_deployment = "cooldown_deployment"
    new_model_added = "new_model_added"

    # Outage alerts
    outage_alerts = "outage_alerts"
    region_outage_alerts = "region_outage_alerts"

    # Fallback alerts
    fallback_reports = "fallback_reports"

    # Virtual Key Events
    new_virtual_key_created = "new_virtual_key_created"
    virtual_key_updated = "virtual_key_updated"
    virtual_key_deleted = "virtual_key_deleted"

    # Team Events
    new_team_created = "new_team_created"
    team_updated = "team_updated"
    team_deleted = "team_deleted"

    # Internal User Events
    new_internal_user_created = "new_internal_user_created"
    internal_user_updated = "internal_user_updated"
    internal_user_deleted = "internal_user_deleted"


DEFAULT_ALERT_TYPES: List[AlertType] = [
    # LLM related alerts
    AlertType.llm_exceptions,
    AlertType.llm_too_slow,
    AlertType.llm_requests_hanging,
    # Budget and spend alerts
    AlertType.budget_alerts,
    AlertType.spend_reports,
    AlertType.failed_tracking_spend,
    # Database alerts
    AlertType.db_exceptions,
    # Report alerts
    AlertType.daily_reports,
    # Deployment alerts
    AlertType.cooldown_deployment,
    AlertType.new_model_added,
    # Outage alerts
    AlertType.outage_alerts,
    AlertType.region_outage_alerts,
    # Fallback alerts
    AlertType.fallback_reports,
]


class HangingRequestData(BaseModel):
    request_id: str
    model: str
    api_base: Optional[str] = None
    key_alias: Optional[str] = None
    team_alias: Optional[str] = None
    alerting_metadata: Optional[dict] = None

# === NexusCore/openenv\Lib\site-packages\openai\types\evals\create_eval_completions_run_data_source.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Dict, List, Union, Optional
from typing_extensions import Literal, Annotated, TypeAlias

from ..._utils import PropertyInfo
from ..._models import BaseModel
from ..shared.metadata import Metadata
from ..chat.chat_completion_tool import ChatCompletionTool
from ..shared.response_format_text import ResponseFormatText
from ..responses.easy_input_message import EasyInputMessage
from ..responses.response_input_text import ResponseInputText
from ..shared.response_format_json_object import ResponseFormatJSONObject
from ..shared.response_format_json_schema import ResponseFormatJSONSchema

__all__ = [
    "CreateEvalCompletionsRunDataSource",
    "Source",
    "SourceFileContent",
    "SourceFileContentContent",
    "SourceFileID",
    "SourceStoredCompletions",
    "InputMessages",
    "InputMessagesTemplate",
    "InputMessagesTemplateTemplate",
    "InputMessagesTemplateTemplateMessage",
    "InputMessagesTemplateTemplateMessageContent",
    "InputMessagesTemplateTemplateMessageContentOutputText",
    "InputMessagesItemReference",
    "SamplingParams",
    "SamplingParamsResponseFormat",
]


class SourceFileContentContent(BaseModel):
    item: Dict[str, object]

    sample: Optional[Dict[str, object]] = None


class SourceFileContent(BaseModel):
    content: List[SourceFileContentContent]
    """The content of the jsonl file."""

    type: Literal["file_content"]
    """The type of jsonl source. Always `file_content`."""


class SourceFileID(BaseModel):
    id: str
    """The identifier of the file."""

    type: Literal["file_id"]
    """The type of jsonl source. Always `file_id`."""


class SourceStoredCompletions(BaseModel):
    type: Literal["stored_completions"]
    """The type of source. Always `stored_completions`."""

    created_after: Optional[int] = None
    """An optional Unix timestamp to filter items created after this time."""

    created_before: Optional[int] = None
    """An optional Unix timestamp to filter items created before this time."""

    limit: Optional[int] = None
    """An optional maximum number of items to return."""

    metadata: Optional[Metadata] = None
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    model: Optional[str] = None
    """An optional model to filter by (e.g., 'gpt-4o')."""


Source: TypeAlias = Annotated[
    Union[SourceFileContent, SourceFileID, SourceStoredCompletions], PropertyInfo(discriminator="type")
]


class InputMessagesTemplateTemplateMessageContentOutputText(BaseModel):
    text: str
    """The text output from the model."""

    type: Literal["output_text"]
    """The type of the output text. Always `output_text`."""


InputMessagesTemplateTemplateMessageContent: TypeAlias = Union[
    str, ResponseInputText, InputMessagesTemplateTemplateMessageContentOutputText
]


class InputMessagesTemplateTemplateMessage(BaseModel):
    content: InputMessagesTemplateTemplateMessageContent
    """Text inputs to the model - can contain template strings."""

    role: Literal["user", "assistant", "system", "developer"]
    """The role of the message input.

    One of `user`, `assistant`, `system`, or `developer`.
    """

    type: Optional[Literal["message"]] = None
    """The type of the message input. Always `message`."""


InputMessagesTemplateTemplate: TypeAlias = Annotated[
    Union[EasyInputMessage, InputMessagesTemplateTemplateMessage], PropertyInfo(discriminator="type")
]


class InputMessagesTemplate(BaseModel):
    template: List[InputMessagesTemplateTemplate]
    """A list of chat messages forming the prompt or context.

    May include variable references to the `item` namespace, ie {{item.name}}.
    """

    type: Literal["template"]
    """The type of input messages. Always `template`."""


class InputMessagesItemReference(BaseModel):
    item_reference: str
    """A reference to a variable in the `item` namespace. Ie, "item.input_trajectory" """

    type: Literal["item_reference"]
    """The type of input messages. Always `item_reference`."""


InputMessages: TypeAlias = Annotated[
    Union[InputMessagesTemplate, InputMessagesItemReference], PropertyInfo(discriminator="type")
]

SamplingParamsResponseFormat: TypeAlias = Union[ResponseFormatText, ResponseFormatJSONSchema, ResponseFormatJSONObject]


class SamplingParams(BaseModel):
    max_completion_tokens: Optional[int] = None
    """The maximum number of tokens in the generated output."""

    response_format: Optional[SamplingParamsResponseFormat] = None
    """An object specifying the format that the model must output.

    Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
    Outputs which ensures the model will match your supplied JSON schema. Learn more
    in the
    [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

    Setting to `{ "type": "json_object" }` enables the older JSON mode, which
    ensures the message the model generates is valid JSON. Using `json_schema` is
    preferred for models that support it.
    """

    seed: Optional[int] = None
    """A seed value to initialize the randomness, during sampling."""

    temperature: Optional[float] = None
    """A higher temperature increases randomness in the outputs."""

    tools: Optional[List[ChatCompletionTool]] = None
    """A list of tools the model may call.

    Currently, only functions are supported as a tool. Use this to provide a list of
    functions the model may generate JSON inputs for. A max of 128 functions are
    supported.
    """

    top_p: Optional[float] = None
    """An alternative to temperature for nucleus sampling; 1.0 includes all tokens."""


class CreateEvalCompletionsRunDataSource(BaseModel):
    source: Source
    """Determines what populates the `item` namespace in this run's data source."""

    type: Literal["completions"]
    """The type of run data source. Always `completions`."""

    input_messages: Optional[InputMessages] = None
    """Used when sampling from a model.

    Dictates the structure of the messages passed into the model. Can either be a
    reference to a prebuilt trajectory (ie, `item.input_trajectory`), or a template
    with variable references to the `item` namespace.
    """

    model: Optional[str] = None
    """The name of the model to use for generating completions (e.g. "o3-mini")."""

    sampling_params: Optional[SamplingParams] = None

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc5035.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
# Modified by Russ Housley to add a map for use with opentypes.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Update to Enhanced Security Services for S/MIME
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc5035.txt
#

from pyasn1.codec.der.encoder import encode as der_encode

from pyasn1.type import namedtype
from pyasn1.type import univ

from pyasn1_modules import rfc2634
from pyasn1_modules import rfc4055
from pyasn1_modules import rfc5652
from pyasn1_modules import rfc5280

ContentType = rfc5652.ContentType

IssuerAndSerialNumber = rfc5652.IssuerAndSerialNumber

SubjectKeyIdentifier = rfc5652.SubjectKeyIdentifier

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier

PolicyInformation = rfc5280.PolicyInformation

GeneralNames = rfc5280.GeneralNames

CertificateSerialNumber = rfc5280.CertificateSerialNumber


# Signing Certificate Attribute V1 and V2

id_aa_signingCertificate = rfc2634.id_aa_signingCertificate

id_aa_signingCertificateV2 = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.47')

Hash = rfc2634.Hash

IssuerSerial = rfc2634.IssuerSerial

ESSCertID = rfc2634.ESSCertID

SigningCertificate = rfc2634.SigningCertificate


sha256AlgId = AlgorithmIdentifier()
sha256AlgId['algorithm'] = rfc4055.id_sha256
# A non-schema object for sha256AlgId['parameters'] as absent
sha256AlgId['parameters'] = der_encode(univ.OctetString(''))


class ESSCertIDv2(univ.Sequence):
    pass

ESSCertIDv2.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('hashAlgorithm', sha256AlgId),
    namedtype.NamedType('certHash', Hash()),
    namedtype.OptionalNamedType('issuerSerial', IssuerSerial())
)


class SigningCertificateV2(univ.Sequence):
    pass

SigningCertificateV2.componentType = namedtype.NamedTypes(
    namedtype.NamedType('certs', univ.SequenceOf(
        componentType=ESSCertIDv2())),
    namedtype.OptionalNamedType('policies', univ.SequenceOf(
        componentType=PolicyInformation()))
)


# Mail List Expansion History Attribute

id_aa_mlExpandHistory = rfc2634.id_aa_mlExpandHistory

ub_ml_expansion_history = rfc2634.ub_ml_expansion_history

EntityIdentifier = rfc2634.EntityIdentifier

MLReceiptPolicy = rfc2634.MLReceiptPolicy

MLData = rfc2634.MLData

MLExpansionHistory = rfc2634.MLExpansionHistory


# ESS Security Label Attribute

id_aa_securityLabel = rfc2634.id_aa_securityLabel

ub_privacy_mark_length = rfc2634.ub_privacy_mark_length

ub_security_categories = rfc2634.ub_security_categories

ub_integer_options = rfc2634.ub_integer_options

ESSPrivacyMark = rfc2634.ESSPrivacyMark

SecurityClassification = rfc2634.SecurityClassification

SecurityPolicyIdentifier = rfc2634.SecurityPolicyIdentifier

SecurityCategory = rfc2634.SecurityCategory

SecurityCategories = rfc2634.SecurityCategories

ESSSecurityLabel = rfc2634.ESSSecurityLabel


# Equivalent Labels Attribute

id_aa_equivalentLabels = rfc2634.id_aa_equivalentLabels

EquivalentLabels = rfc2634.EquivalentLabels


# Content Identifier Attribute

id_aa_contentIdentifier = rfc2634.id_aa_contentIdentifier

ContentIdentifier = rfc2634.ContentIdentifier


# Content Reference Attribute

id_aa_contentReference = rfc2634.id_aa_contentReference

ContentReference = rfc2634.ContentReference


# Message Signature Digest Attribute

id_aa_msgSigDigest = rfc2634.id_aa_msgSigDigest

MsgSigDigest = rfc2634.MsgSigDigest


# Content Hints Attribute

id_aa_contentHint = rfc2634.id_aa_contentHint

ContentHints = rfc2634.ContentHints


# Receipt Request Attribute

AllOrFirstTier = rfc2634.AllOrFirstTier

ReceiptsFrom = rfc2634.ReceiptsFrom

id_aa_receiptRequest = rfc2634.id_aa_receiptRequest

ub_receiptsTo = rfc2634.ub_receiptsTo

ReceiptRequest = rfc2634.ReceiptRequest


# Receipt Content Type

ESSVersion = rfc2634.ESSVersion

id_ct_receipt = rfc2634.id_ct_receipt

Receipt = rfc2634.Receipt

ub_receiptsTo = rfc2634.ub_receiptsTo

ReceiptRequest = rfc2634.ReceiptRequest


# Map of Attribute Type to the Attribute structure is added to the
# ones that are in rfc5652.py

_cmsAttributesMapUpdate = {
    id_aa_signingCertificateV2: SigningCertificateV2(),
}

rfc5652.cmsAttributesMap.update(_cmsAttributesMapUpdate)


# Map of Content Type OIDs to Content Types is added to the
# ones that are in rfc5652.py

_cmsContentTypesMapUpdate = {
    id_ct_receipt: Receipt(),
}

rfc5652.cmsContentTypesMap.update(_cmsContentTypesMapUpdate)

# === NexusCore/openenv\Lib\site-packages\IPython\utils\tokenutil.py ===
"""Token-related utilities"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import itertools
import tokenize
from io import StringIO
from keyword import iskeyword
from tokenize import TokenInfo
from typing import Generator, NamedTuple


class Token(NamedTuple):
    token: int
    text: str
    start: int
    end: int
    line: str


def generate_tokens(readline) -> Generator[TokenInfo, None, None]:
    """wrap generate_tkens to catch EOF errors"""
    try:
        yield from tokenize.generate_tokens(readline)
    except tokenize.TokenError:
        # catch EOF error
        return


def generate_tokens_catch_errors(
    readline, extra_errors_to_catch: list[str] | None = None
):
    default_errors_to_catch = [
        "unterminated string literal",
        "invalid non-printable character",
        "after line continuation character",
    ]
    assert extra_errors_to_catch is None or isinstance(extra_errors_to_catch, list)
    errors_to_catch = default_errors_to_catch + (extra_errors_to_catch or [])

    tokens: list[TokenInfo] = []
    try:
        for token in tokenize.generate_tokens(readline):
            tokens.append(token)
            yield token
    except tokenize.TokenError as exc:
        if any(error in exc.args[0] for error in errors_to_catch):
            if tokens:
                start = tokens[-1].start[0], tokens[-1].end[0]
                end = start
                line = tokens[-1].line
            else:
                start = end = (1, 0)
                line = ""
            yield TokenInfo(tokenize.ERRORTOKEN, "", start, end, line)
        else:
            # Catch EOF
            raise


def line_at_cursor(cell: str, cursor_pos: int = 0) -> tuple[str, int]:
    """Return the line in a cell at a given cursor position

    Used for calling line-based APIs that don't support multi-line input, yet.

    Parameters
    ----------
    cell : str
        multiline block of text
    cursor_pos : integer
        the cursor position

    Returns
    -------
    (line, offset): (string, integer)
        The line with the current cursor, and the character offset of the start of the line.
    """
    offset = 0
    lines = cell.splitlines(True)
    for line in lines:
        next_offset = offset + len(line)
        if not line.endswith("\n"):
            # If the last line doesn't have a trailing newline, treat it as if
            # it does so that the cursor at the end of the line still counts
            # as being on that line.
            next_offset += 1
        if next_offset > cursor_pos:
            break
        offset = next_offset
    else:
        line = ""
    return line, offset


def token_at_cursor(cell: str, cursor_pos: int = 0) -> str:
    """Get the token at a given cursor

    Used for introspection.

    Function calls are prioritized, so the token for the callable will be returned
    if the cursor is anywhere inside the call.

    Parameters
    ----------
    cell : str
        A block of Python code
    cursor_pos : int
        The location of the cursor in the block where the token should be found
    """
    names: list[str] = []
    call_names: list[str] = []
    closing_call_name: str | None = None
    most_recent_outer_name: str | None = None

    offsets = {1: 0}  # lines start at 1
    intersects_with_cursor = False
    cur_token_is_name = False
    tokens: list[Token | None] = [
        Token(*tup) for tup in generate_tokens(StringIO(cell).readline)
    ]
    if not tokens:
        return ""
    for prev_tok, (tok, next_tok) in zip(
        [None] + tokens, itertools.pairwise(tokens + [None])
    ):
        # token, text, start, end, line = tup
        start_line, start_col = tok.start
        end_line, end_col = tok.end
        if end_line + 1 not in offsets:
            # keep track of offsets for each line
            lines = tok.line.splitlines(True)
            for lineno, line in enumerate(lines, start_line + 1):
                if lineno not in offsets:
                    offsets[lineno] = offsets[lineno - 1] + len(line)

        closing_call_name = None

        offset = offsets[start_line]
        if offset + start_col > cursor_pos:
            # current token starts after the cursor,
            # don't consume it
            break

        if cur_token_is_name := tok.token == tokenize.NAME and not iskeyword(tok.text):
            if (
                names
                and prev_tok
                and prev_tok.token == tokenize.OP
                and prev_tok.text == "."
            ):
                names[-1] = "%s.%s" % (names[-1], tok.text)
            else:
                names.append(tok.text)
            if (
                next_tok is not None
                and next_tok.token == tokenize.OP
                and next_tok.text == "="
            ):
                # don't inspect the lhs of an assignment
                names.pop(-1)
                cur_token_is_name = False
            if not call_names:
                most_recent_outer_name = names[-1] if names else None
        elif tok.token == tokenize.OP:
            if tok.text == "(" and names:
                # if we are inside a function call, inspect the function
                call_names.append(names[-1])
            elif tok.text == ")" and call_names:
                # keep track of the most recently popped call_name from the stack
                closing_call_name = call_names.pop(-1)

        if offsets[end_line] + end_col > cursor_pos:
            # we found the cursor, stop reading
            # if the current token intersects directly, use it instead of the call token
            intersects_with_cursor = offsets[start_line] + start_col <= cursor_pos
            break

    if cur_token_is_name and intersects_with_cursor:
        return names[-1]
    # if the cursor isn't directly over a name token, use the most recent
    # call name if we can find one
    elif closing_call_name:
        # if we're on a ")", use the most recently popped call name
        return closing_call_name
    elif call_names:
        # otherwise, look for the most recent call name in the stack
        return call_names[-1]
    elif most_recent_outer_name:
        # if we've popped all the call names, use the most recently-seen
        # outer name
        return most_recent_outer_name
    elif names:
        # failing that, use the most recently seen name
        return names[-1]
    else:
        # give up
        return ""

# === NexusCore/openenv\Lib\site-packages\jedi\inference\__init__.py ===
"""
Type inference of Python code in |jedi| is based on three assumptions:

* The code uses as least side effects as possible. Jedi understands certain
  list/tuple/set modifications, but there's no guarantee that Jedi detects
  everything (list.append in different modules for example).
* No magic is being used:

  - metaclasses
  - ``setattr()`` / ``__import__()``
  - writing to ``globals()``, ``locals()``, ``object.__dict__``
* The programmer is not a total dick, e.g. like `this
  <https://github.com/davidhalter/jedi/issues/24>`_ :-)

The actual algorithm is based on a principle I call lazy type inference.  That
said, the typical entry point for static analysis is calling
``infer_expr_stmt``. There's separate logic for autocompletion in the API, the
inference_state is all about inferring an expression.

TODO this paragraph is not what jedi does anymore, it's similar, but not the
same.

Now you need to understand what follows after ``infer_expr_stmt``. Let's
make an example::

    import datetime
    datetime.date.toda# <-- cursor here

First of all, this module doesn't care about completion. It really just cares
about ``datetime.date``. At the end of the procedure ``infer_expr_stmt`` will
return the ``date`` class.

To *visualize* this (simplified):

- ``InferenceState.infer_expr_stmt`` doesn't do much, because there's no assignment.
- ``Context.infer_node`` cares for resolving the dotted path
- ``InferenceState.find_types`` searches for global definitions of datetime, which
  it finds in the definition of an import, by scanning the syntax tree.
- Using the import logic, the datetime module is found.
- Now ``find_types`` is called again by ``infer_node`` to find ``date``
  inside the datetime module.

Now what would happen if we wanted ``datetime.date.foo.bar``? Two more
calls to ``find_types``. However the second call would be ignored, because the
first one would return nothing (there's no foo attribute in ``date``).

What if the import would contain another ``ExprStmt`` like this::

    from foo import bar
    Date = bar.baz

Well... You get it. Just another ``infer_expr_stmt`` recursion. It's really
easy. Python can obviously get way more complicated then this. To understand
tuple assignments, list comprehensions and everything else, a lot more code had
to be written.

Jedi has been tested very well, so you can just start modifying code. It's best
to write your own test first for your "new" feature. Don't be scared of
breaking stuff. As long as the tests pass, you're most likely to be fine.

I need to mention now that lazy type inference is really good because it
only *inferes* what needs to be *inferred*. All the statements and modules
that are not used are just being ignored.
"""
import parso
from jedi.file_io import FileIO

from jedi import debug
from jedi import settings
from jedi.inference import imports
from jedi.inference import recursion
from jedi.inference.cache import inference_state_function_cache
from jedi.inference import helpers
from jedi.inference.names import TreeNameDefinition
from jedi.inference.base_value import ContextualizedNode, \
    ValueSet, iterate_values
from jedi.inference.value import ClassValue, FunctionValue
from jedi.inference.syntax_tree import infer_expr_stmt, \
    check_tuple_assignments, tree_name_to_values
from jedi.inference.imports import follow_error_node_imports_if_possible
from jedi.plugins import plugin_manager


class InferenceState:
    def __init__(self, project, environment=None, script_path=None):
        if environment is None:
            environment = project.get_environment()
        self.environment = environment
        self.script_path = script_path
        self.compiled_subprocess = environment.get_inference_state_subprocess(self)
        self.grammar = environment.get_grammar()

        self.latest_grammar = parso.load_grammar(version='3.13')
        self.memoize_cache = {}  # for memoize decorators
        self.module_cache = imports.ModuleCache()  # does the job of `sys.modules`.
        self.stub_module_cache = {}  # Dict[Tuple[str, ...], Optional[ModuleValue]]
        self.compiled_cache = {}  # see `inference.compiled.create()`
        self.inferred_element_counts = {}
        self.mixed_cache = {}  # see `inference.compiled.mixed._create()`
        self.analysis = []
        self.dynamic_params_depth = 0
        self.do_dynamic_params_search = settings.dynamic_params
        self.is_analysis = False
        self.project = project
        self.access_cache = {}
        self.allow_unsafe_executions = False
        self.flow_analysis_enabled = True

        self.reset_recursion_limitations()

    def import_module(self, import_names, sys_path=None, prefer_stubs=True):
        return imports.import_module_by_names(
            self, import_names, sys_path, prefer_stubs=prefer_stubs)

    @staticmethod
    @plugin_manager.decorate()
    def execute(value, arguments):
        debug.dbg('execute: %s %s', value, arguments)
        with debug.increase_indent_cm():
            value_set = value.py__call__(arguments=arguments)
        debug.dbg('execute result: %s in %s', value_set, value)
        return value_set

    # mypy doesn't suppport decorated propeties (https://github.com/python/mypy/issues/1362)
    @property  # type: ignore[misc]
    @inference_state_function_cache()
    def builtins_module(self):
        module_name = 'builtins'
        builtins_module, = self.import_module((module_name,), sys_path=[])
        return builtins_module

    @property  # type: ignore[misc]
    @inference_state_function_cache()
    def typing_module(self):
        typing_module, = self.import_module(('typing',))
        return typing_module

    def reset_recursion_limitations(self):
        self.recursion_detector = recursion.RecursionDetector()
        self.execution_recursion_detector = recursion.ExecutionRecursionDetector(self)

    def get_sys_path(self, **kwargs):
        """Convenience function"""
        return self.project._get_sys_path(self, **kwargs)

    def infer(self, context, name):
        def_ = name.get_definition(import_name_always=True)
        if def_ is not None:
            type_ = def_.type
            is_classdef = type_ == 'classdef'
            if is_classdef or type_ == 'funcdef':
                if is_classdef:
                    c = ClassValue(self, context, name.parent)
                else:
                    c = FunctionValue.from_context(context, name.parent)
                return ValueSet([c])

            if type_ == 'expr_stmt':
                is_simple_name = name.parent.type not in ('power', 'trailer')
                if is_simple_name:
                    return infer_expr_stmt(context, def_, name)
            if type_ == 'for_stmt':
                container_types = context.infer_node(def_.children[3])
                cn = ContextualizedNode(context, def_.children[3])
                for_types = iterate_values(container_types, cn)
                n = TreeNameDefinition(context, name)
                return check_tuple_assignments(n, for_types)
            if type_ in ('import_from', 'import_name'):
                return imports.infer_import(context, name)
            if type_ == 'with_stmt':
                return tree_name_to_values(self, context, name)
            elif type_ == 'param':
                return context.py__getattribute__(name.value, position=name.end_pos)
            elif type_ == 'namedexpr_test':
                return context.infer_node(def_)
        else:
            result = follow_error_node_imports_if_possible(context, name)
            if result is not None:
                return result

        return helpers.infer_call_of_leaf(context, name)

    def parse_and_get_code(self, code=None, path=None,
                           use_latest_grammar=False, file_io=None, **kwargs):
        if code is None:
            if file_io is None:
                file_io = FileIO(path)
            code = file_io.read()
        # We cannot just use parso, because it doesn't use errors='replace'.
        code = parso.python_bytes_to_unicode(code, encoding='utf-8', errors='replace')

        if len(code) > settings._cropped_file_size:
            code = code[:settings._cropped_file_size]

        grammar = self.latest_grammar if use_latest_grammar else self.grammar
        return grammar.parse(code=code, path=path, file_io=file_io, **kwargs), code

    def parse(self, *args, **kwargs):
        return self.parse_and_get_code(*args, **kwargs)[0]

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\_experimental\mcp_server\auth\user_api_key_auth_mcp.py ===
from typing import List, Optional, Tuple

from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.types import Scope

from litellm._logging import verbose_logger
from litellm.proxy._types import LiteLLM_TeamTable, SpecialHeaders, UserAPIKeyAuth
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth


class UserAPIKeyAuthMCP:
    """
    Class to handle Authentication for MCP requests

    Utilizes the main `user_api_key_auth` function to validate the request
    """

    LITELLM_API_KEY_HEADER_NAME_PRIMARY = SpecialHeaders.custom_litellm_api_key.value
    LITELLM_API_KEY_HEADER_NAME_SECONDARY = SpecialHeaders.openai_authorization.value

    # This is the header to use if you want LiteLLM to use this header for authenticating to the MCP server
    LITELLM_MCP_AUTH_HEADER_NAME = SpecialHeaders.mcp_auth.value

    @staticmethod
    async def user_api_key_auth_mcp(scope: Scope) -> Tuple[UserAPIKeyAuth, Optional[str]]:
        """
        Validate and extract headers from the ASGI scope for MCP requests.

        Args:
            scope: ASGI scope containing request information

        Returns:
            UserAPIKeyAuth containing validated authentication information
            mcp_auth_header: Optional[str] MCP auth header to be passed to the MCP server

        Raises:
            HTTPException: If headers are invalid or missing required headers
        """
        headers = UserAPIKeyAuthMCP._safe_get_headers_from_scope(scope)
        litellm_api_key = (
            UserAPIKeyAuthMCP.get_litellm_api_key_from_headers(headers) or ""
        )
        mcp_auth_header = headers.get(UserAPIKeyAuthMCP.LITELLM_MCP_AUTH_HEADER_NAME)

        # Create a proper Request object with mock body method to avoid ASGI receive channel issues
        request = Request(scope=scope)

        # Mock the body method to return empty dict as JSON bytes
        # This prevents "Receive channel has not been made available" error
        async def mock_body():
            return b"{}"  # Empty JSON object as bytes

        request.body = mock_body  # type: ignore

        validated_user_api_key_auth = await user_api_key_auth(
            api_key=litellm_api_key, request=request
        )

        return validated_user_api_key_auth, mcp_auth_header

    @staticmethod
    def get_litellm_api_key_from_headers(headers: Headers) -> Optional[str]:
        """
        Get the Litellm API key from the headers using case-insensitive lookup

        1. Check if `x-litellm-api-key` is in the headers
        2. If not, check if `Authorization` is in the headers

        Args:
            headers: Starlette Headers object that handles case insensitivity
        """
        # Headers object handles case insensitivity automatically
        api_key = headers.get(UserAPIKeyAuthMCP.LITELLM_API_KEY_HEADER_NAME_PRIMARY)
        if api_key:
            return api_key

        auth_header = headers.get(
            UserAPIKeyAuthMCP.LITELLM_API_KEY_HEADER_NAME_SECONDARY
        )
        if auth_header:
            return auth_header

        return None

    @staticmethod
    def _safe_get_headers_from_scope(scope: Scope) -> Headers:
        """
        Safely extract headers from ASGI scope using Starlette's Headers class
        which handles case insensitivity and proper header parsing.

        ASGI headers are in format: List[List[bytes, bytes]]
        We need to convert them to the format Headers expects.
        """
        try:
            # ASGI headers are list of [name: bytes, value: bytes] pairs
            raw_headers = scope.get("headers", [])
            # Convert bytes to strings and create dict for Headers constructor
            headers_dict = {
                name.decode("latin-1"): value.decode("latin-1")
                for name, value in raw_headers
            }
            return Headers(headers_dict)
        except Exception as e:
            verbose_logger.exception(f"Error getting headers from scope: {e}")
            # Return empty Headers object with empty dict
            return Headers({})

    @staticmethod
    async def get_allowed_mcp_servers(
        user_api_key_auth: Optional[UserAPIKeyAuth] = None,
    ) -> List[str]:
        """
        Apply least privilege
        """
        from typing import List

        allowed_mcp_servers: List[str] = []
        allowed_mcp_servers_for_key = (
            await UserAPIKeyAuthMCP._get_allowed_mcp_servers_for_key(user_api_key_auth)
        )
        allowed_mcp_servers_for_team = (
            await UserAPIKeyAuthMCP._get_allowed_mcp_servers_for_team(user_api_key_auth)
        )

        #########################################################
        # If team has mcp_servers, then key must have a subset of the team's mcp_servers
        #########################################################
        if len(allowed_mcp_servers_for_team) > 0:
            for _mcp_server in allowed_mcp_servers_for_key:
                if _mcp_server in allowed_mcp_servers_for_team:
                    allowed_mcp_servers.append(_mcp_server)
        else:
            allowed_mcp_servers = allowed_mcp_servers_for_key

        return list(set(allowed_mcp_servers))

    @staticmethod
    async def _get_allowed_mcp_servers_for_key(
        user_api_key_auth: Optional[UserAPIKeyAuth] = None,
    ) -> List[str]:
        from litellm.proxy.proxy_server import prisma_client

        if user_api_key_auth is None:
            return []

        if user_api_key_auth.object_permission_id is None:
            return []

        if prisma_client is None:
            verbose_logger.debug("prisma_client is None")
            return []

        key_object_permission = (
            await prisma_client.db.litellm_objectpermissiontable.find_unique(
                where={"object_permission_id": user_api_key_auth.object_permission_id},
            )
        )
        if key_object_permission is None:
            return []

        return key_object_permission.mcp_servers or []

    @staticmethod
    async def _get_allowed_mcp_servers_for_team(
        user_api_key_auth: Optional[UserAPIKeyAuth] = None,
    ) -> List[str]:
        """
        The `object_permission` for a team is not stored on the user_api_key_auth object

        first we check if the team has a object_permission_id attached
            - if it does then we look up the object_permission for the team
        """
        from litellm.proxy.proxy_server import prisma_client

        if user_api_key_auth is None:
            return []

        if user_api_key_auth.team_id is None:
            return []

        if prisma_client is None:
            verbose_logger.debug("prisma_client is None")
            return []

        team_obj: Optional[LiteLLM_TeamTable] = (
            await prisma_client.db.litellm_teamtable.find_unique(
                where={"team_id": user_api_key_auth.team_id},
            )
        )
        if team_obj is None:
            verbose_logger.debug("team_obj is None")
            return []

        object_permissions = team_obj.object_permission
        if object_permissions is None:
            return []

        return object_permissions.mcp_servers or []

# === NexusCore/openenv\Lib\site-packages\openai\resources\fine_tuning\jobs\checkpoints.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import maybe_transform
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ....pagination import SyncCursorPage, AsyncCursorPage
from ...._base_client import (
    AsyncPaginator,
    make_request_options,
)
from ....types.fine_tuning.jobs import checkpoint_list_params
from ....types.fine_tuning.jobs.fine_tuning_job_checkpoint import FineTuningJobCheckpoint

__all__ = ["Checkpoints", "AsyncCheckpoints"]


class Checkpoints(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> CheckpointsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return CheckpointsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> CheckpointsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return CheckpointsWithStreamingResponse(self)

    def list(
        self,
        fine_tuning_job_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[FineTuningJobCheckpoint]:
        """
        List checkpoints for a fine-tuning job.

        Args:
          after: Identifier for the last checkpoint ID from the previous pagination request.

          limit: Number of checkpoints to retrieve.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuning_job_id:
            raise ValueError(f"Expected a non-empty value for `fine_tuning_job_id` but received {fine_tuning_job_id!r}")
        return self._get_api_list(
            f"/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints",
            page=SyncCursorPage[FineTuningJobCheckpoint],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                    },
                    checkpoint_list_params.CheckpointListParams,
                ),
            ),
            model=FineTuningJobCheckpoint,
        )


class AsyncCheckpoints(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncCheckpointsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncCheckpointsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncCheckpointsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncCheckpointsWithStreamingResponse(self)

    def list(
        self,
        fine_tuning_job_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[FineTuningJobCheckpoint, AsyncCursorPage[FineTuningJobCheckpoint]]:
        """
        List checkpoints for a fine-tuning job.

        Args:
          after: Identifier for the last checkpoint ID from the previous pagination request.

          limit: Number of checkpoints to retrieve.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuning_job_id:
            raise ValueError(f"Expected a non-empty value for `fine_tuning_job_id` but received {fine_tuning_job_id!r}")
        return self._get_api_list(
            f"/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints",
            page=AsyncCursorPage[FineTuningJobCheckpoint],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                    },
                    checkpoint_list_params.CheckpointListParams,
                ),
            ),
            model=FineTuningJobCheckpoint,
        )


class CheckpointsWithRawResponse:
    def __init__(self, checkpoints: Checkpoints) -> None:
        self._checkpoints = checkpoints

        self.list = _legacy_response.to_raw_response_wrapper(
            checkpoints.list,
        )


class AsyncCheckpointsWithRawResponse:
    def __init__(self, checkpoints: AsyncCheckpoints) -> None:
        self._checkpoints = checkpoints

        self.list = _legacy_response.async_to_raw_response_wrapper(
            checkpoints.list,
        )


class CheckpointsWithStreamingResponse:
    def __init__(self, checkpoints: Checkpoints) -> None:
        self._checkpoints = checkpoints

        self.list = to_streamed_response_wrapper(
            checkpoints.list,
        )


class AsyncCheckpointsWithStreamingResponse:
    def __init__(self, checkpoints: AsyncCheckpoints) -> None:
        self._checkpoints = checkpoints

        self.list = async_to_streamed_response_wrapper(
            checkpoints.list,
        )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\nimrod.py ===
"""
    pygments.lexers.nimrod
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Nim language (formerly known as Nimrod).

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, default, bygroups
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Error

__all__ = ['NimrodLexer']


class NimrodLexer(RegexLexer):
    """
    For Nim source code.
    """

    name = 'Nimrod'
    url = 'http://nim-lang.org/'
    aliases = ['nimrod', 'nim']
    filenames = ['*.nim', '*.nimrod']
    mimetypes = ['text/x-nim']
    version_added = '1.5'

    flags = re.MULTILINE | re.IGNORECASE

    def underscorize(words):
        newWords = []
        new = []
        for word in words:
            for ch in word:
                new.append(ch)
                new.append("_?")
            newWords.append(''.join(new))
            new = []
        return "|".join(newWords)

    keywords = [
        'addr', 'and', 'as', 'asm', 'bind', 'block', 'break', 'case',
        'cast', 'concept', 'const', 'continue', 'converter', 'defer', 'discard',
        'distinct', 'div', 'do', 'elif', 'else', 'end', 'enum', 'except',
        'export', 'finally', 'for', 'if', 'in', 'yield', 'interface',
        'is', 'isnot', 'iterator', 'let', 'mixin', 'mod',
        'not', 'notin', 'object', 'of', 'or', 'out', 'ptr', 'raise',
        'ref', 'return', 'shl', 'shr', 'static', 'try',
        'tuple', 'type', 'using', 'when', 'while', 'xor'
    ]

    keywordsPseudo = [
        'nil', 'true', 'false'
    ]

    opWords = [
        'and', 'or', 'not', 'xor', 'shl', 'shr', 'div', 'mod', 'in',
        'notin', 'is', 'isnot'
    ]

    types = [
        'int', 'int8', 'int16', 'int32', 'int64', 'float', 'float32', 'float64',
        'bool', 'char', 'range', 'array', 'seq', 'set', 'string'
    ]

    tokens = {
        'root': [
            # Comments
            (r'##\[', String.Doc, 'doccomment'),
            (r'##.*$', String.Doc),
            (r'#\[', Comment.Multiline, 'comment'),
            (r'#.*$', Comment),

            # Pragmas
            (r'\{\.', String.Other, 'pragma'),

            # Operators
            (r'[*=><+\-/@$~&%!?|\\\[\]]', Operator),
            (r'\.\.|\.|,|\[\.|\.\]|\{\.|\.\}|\(\.|\.\)|\{|\}|\(|\)|:|\^|`|;',
             Punctuation),

            # Case statement branch
            (r'(\n\s*)(of)(\s)', bygroups(Text.Whitespace, Keyword,
                                          Text.Whitespace), 'casebranch'),

            # Strings
            (r'(?:[\w]+)"', String, 'rdqs'),
            (r'"""', String.Double, 'tdqs'),
            ('"', String, 'dqs'),

            # Char
            ("'", String.Char, 'chars'),

            # Keywords
            (rf'({underscorize(opWords)})\b', Operator.Word),
            (r'(proc|func|method|macro|template)(\s)(?![(\[\]])',
             bygroups(Keyword, Text.Whitespace), 'funcname'),
            (rf'({underscorize(keywords)})\b', Keyword),
            (r'({})\b'.format(underscorize(['from', 'import', 'include', 'export'])),
             Keyword.Namespace),
            (r'(v_?a_?r)\b', Keyword.Declaration),
            (rf'({underscorize(types)})\b', Name.Builtin),
            (rf'({underscorize(keywordsPseudo)})\b', Keyword.Pseudo),

            # Identifiers
            (r'\b((?![_\d])\w)(((?!_)\w)|(_(?!_)\w))*', Name),

            # Numbers
            (r'[0-9][0-9_]*(?=([e.]|\'f(32|64)))',
             Number.Float, ('float-suffix', 'float-number')),
            (r'0x[a-f0-9][a-f0-9_]*', Number.Hex, 'int-suffix'),
            (r'0b[01][01_]*', Number.Bin, 'int-suffix'),
            (r'0o[0-7][0-7_]*', Number.Oct, 'int-suffix'),
            (r'[0-9][0-9_]*', Number.Integer, 'int-suffix'),

            # Whitespace
            (r'\s+', Text.Whitespace),
            (r'.+$', Error),
        ],
        'chars': [
            (r'\\([\\abcefnrtvl"\']|x[a-f0-9]{2}|[0-9]{1,3})', String.Escape),
            (r"'", String.Char, '#pop'),
            (r".", String.Char)
        ],
        'strings': [
            (r'(?<!\$)\$(\d+|#|\w+)+', String.Interpol),
            (r'[^\\\'"$\n]+', String),
            # quotes, dollars and backslashes must be parsed one at a time
            (r'[\'"\\]', String),
            # unhandled string formatting sign
            (r'\$', String)
            # newlines are an error (use "nl" state)
        ],
        'doccomment': [
            (r'[^\]#]+', String.Doc),
            (r'##\[', String.Doc, '#push'),
            (r'\]##', String.Doc, '#pop'),
            (r'[\]#]', String.Doc),
        ],
        'comment': [
            (r'[^\]#]+', Comment.Multiline),
            (r'#\[', Comment.Multiline, '#push'),
            (r'\]#', Comment.Multiline, '#pop'),
            (r'[\]#]', Comment.Multiline),
        ],
        'dqs': [
            (r'\\([\\abcefnrtvl"\']|\n|x[a-f0-9]{2}|[0-9]{1,3})',
             String.Escape),
            (r'"', String, '#pop'),
            include('strings')
        ],
        'rdqs': [
            (r'"(?!")', String, '#pop'),
            (r'""', String.Escape),
            include('strings')
        ],
        'tdqs': [
            (r'"""', String.Double, '#pop'),
            include('strings'),
            (r'\n', String.Double)
        ],
        'funcname': [
            (r'((?![\d_])\w)(((?!_)\w)|(_(?!_)\w))*', Name.Function, '#pop'),
            (r'`.+`', Name.Function, '#pop')
        ],
        'nl': [
            (r'\n', String)
        ],
        'float-number': [
            (r'\.(?!\.)[0-9_]*[f]*', Number.Float),
            (r'e[+-]?[0-9][0-9_]*', Number.Float),
            default('#pop')
        ],
        'float-suffix': [
            (r'\'f(32|64)', Number.Float),
            default('#pop')
        ],
        'int-suffix': [
            (r'\'i(32|64)', Number.Integer.Long),
            (r'\'i(8|16)', Number.Integer),
            default('#pop')
        ],
        'casebranch': [
            (r',', Punctuation),
            (r'[\n ]+', Text.Whitespace),
            (r':', Operator, '#pop'),
            (r'\w+|[^:]', Name.Label),
        ],
        'pragma': [
            (r'[:,]', Text),
            (r'[\n ]+', Text.Whitespace),
            (r'\.\}', String.Other, '#pop'),
            (r'\w+|\W+|[^.}]', String.Other),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\win32\Demos\security\sspi\socket_server.py ===
"""A sample socket server and client using SSPI authentication and encryption.

You must run with either 'client' or 'server' as arguments.  A server must be
running before a client can connect.

To use with Kerberos you should include in the client options
--target-spn=username, where 'username' is the user under which the server is
being run.

Running either the client or server as a different user can be informative.
A command-line such as the following may be useful:
`runas /user:{user} {fqp}\\python.exe {fqp}\\socket_server.py --wait client|server`

{fqp} should specify the relevant fully-qualified path names.

To use 'runas' with Kerberos, the client program will need to
specify --target-spn with the username under which the *server* is running.

See the SSPI documentation for more details.
"""

import http.client  # sorry, this demo needs 2.3+
import optparse
import socketserver
import struct
import traceback

import sspi
import win32api

options = None  # set to optparse object.


def GetUserName():
    try:
        return win32api.GetUserName()
    except win32api.error as details:
        # Seeing 'access denied' errors here for non-local users (presumably
        # without permission to login locally).  Get the fully-qualified
        # username, although a side-effect of these permission-denied errors
        # is a lack of Python codecs - so printing the Unicode value fails.
        # So just return the repr(), and avoid codecs completely.
        return repr(win32api.GetUserNameEx(win32api.NameSamCompatible))


# Send a simple "message" over a socket - send the number of bytes first,
# then the string.  Ditto for receive.
def _send_msg(s, m):
    s.send(struct.pack("i", len(m)))
    s.send(m)


def _get_msg(s):
    size_data = s.recv(struct.calcsize("i"))
    if not size_data:
        return None
    cb = struct.unpack("i", size_data)[0]
    return s.recv(cb)


class SSPISocketServer(socketserver.TCPServer):
    def __init__(self, *args, **kw):
        socketserver.TCPServer.__init__(self, *args, **kw)
        self.sa = sspi.ServerAuth(options.package)

    def verify_request(self, sock, ca):
        # Do the sspi auth dance
        self.sa.reset()
        while 1:
            data = _get_msg(sock)
            if data is None:
                return False
            try:
                err, sec_buffer = self.sa.authorize(data)
            except sspi.error as details:
                print("FAILED to authorize client:", details)
                return False

            if err == 0:
                break
            _send_msg(sock, sec_buffer[0].Buffer)
        return True

    def process_request(self, request, client_address):
        # An example using the connection once it is established.
        print("The server is running as user", GetUserName())
        self.sa.ctxt.ImpersonateSecurityContext()
        try:
            print("Having conversation with client as user", GetUserName())
            while 1:
                # we need to grab 2 bits of data - the encrypted data, and the
                # 'key'
                data = _get_msg(request)
                key = _get_msg(request)
                if data is None or key is None:
                    break
                data = self.sa.decrypt(data, key)
                print(f"Client sent: {data!r}")
        finally:
            self.sa.ctxt.RevertSecurityContext()
        self.close_request(request)
        print("The server is back to user", GetUserName())


def serve():
    s = SSPISocketServer(("localhost", options.port), None)
    print("Running test server...")
    s.serve_forever()


def sspi_client():
    c = http.client.HTTPConnection("localhost", options.port)
    c.connect()
    # Do the auth dance.
    ca = sspi.ClientAuth(options.package, targetspn=options.target_spn)
    data = None
    while 1:
        err, out_buf = ca.authorize(data)
        _send_msg(c.sock, out_buf[0].Buffer)
        if err == 0:
            break
        data = _get_msg(c.sock)
    print("Auth dance complete - sending a few encryted messages")
    # Assume out data is sensitive - encrypt the message.
    for data in "Hello from the client".split():
        blob, key = ca.encrypt(data)
        _send_msg(c.sock, blob)
        _send_msg(c.sock, key)
    c.sock.close()
    print("Client completed.")


if __name__ == "__main__":
    parser = optparse.OptionParser("%prog [options] client|server", description=__doc__)

    parser.add_option(
        "",
        "--package",
        action="store",
        default="NTLM",
        help="The SSPI package to use (eg, Kerberos) - default is NTLM",
    )

    parser.add_option(
        "",
        "--target-spn",
        action="store",
        help="""The target security provider name to use. The
                      string contents are security-package specific.  For
                      example, 'Kerberos' or 'Negotiate' require the server
                      principal name (SPN) (ie, the username) of the remote
                      process.  For NTLM this must be blank.""",
    )

    parser.add_option(
        "",
        "--port",
        action="store",
        default="8181",
        help="The port number to use (default=8181)",
    )

    parser.add_option(
        "",
        "--wait",
        action="store_true",
        help="""Cause the program to wait for input just before
                              terminating. Useful when using via runas to see
                              any error messages before termination.
                           """,
    )

    options, args = parser.parse_args()
    try:
        options.port = int(options.port)
    except (ValueError, TypeError):
        parser.error("--port must be an integer")

    try:
        try:
            if not args:
                args = [""]
            if args[0] == "client":
                sspi_client()
            elif args[0] == "server":
                serve()
            else:
                parser.error(
                    "You must supply 'client' or 'server' - use --help for details"
                )
        except KeyboardInterrupt:
            pass
        except SystemExit:
            pass
        except:
            traceback.print_exc()
    finally:
        if options.wait:
            input("Press enter to continue")

# === NexusCore/evaluation\evalplus\tools\mbpp\init_plus.py ===
import json
import os
import pathlib
import shutil
from importlib import util
from inspect import getmembers, isfunction
from typing import Tuple

from tempdir import TempDir

from evalplus.data.mbpp import get_mbpp, mbpp_serialize_inputs

MBPP_PLUS_PATH = pathlib.Path(__file__).parent.parent.parent / "MbppBase.jsonl"

GROUNDTRUTH_MBPP_PATH = pathlib.Path(__file__).parent.parent.parent / "groundtruth/mbpp"


def _ret(entry_point) -> str:
    """
    This is a hacky function to return some garbages so that we can
    successfully run the function .
    """
    set_assertion_func = [
        "similar_elements",
        "find_char_long",
        "common_in_nested_lists",
        "extract_singly",
        "larg_nnum",
        "intersection_array",
        "k_smallest_pairs",
    ]
    if entry_point in set_assertion_func:
        return "()"
    return "1"


def get_entry_point(task_id: int, assertion: str) -> str:
    py_file_path = str(GROUNDTRUTH_MBPP_PATH) + f"/{str(task_id).zfill(3)}.py"
    spec = util.spec_from_file_location("inspect_module", py_file_path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    functions = [name for name, value in getmembers(module, isfunction)]

    # maybe exist some helper functions, filter them
    functions = [func for func in functions if func in assertion]
    if len(functions) > 1:
        print("more than one function: ", functions)

    return functions[0] if len(functions) > 0 else None


def get_code_and_contract_and_assertion(task_id: id) -> Tuple[str, str, str]:
    py_file_path = str(GROUNDTRUTH_MBPP_PATH) + f"/{str(task_id).zfill(3)}.py"
    with open(py_file_path) as reader:
        text = reader.read()
        # remove docstring
        start_index = text.find('"""')
        end_index = text.find('"""', start_index + 3)
        if start_index != -1 and end_index != -1:
            text = text[:start_index] + text[end_index + 3 :]

        lines = text.splitlines()
        assertion = ""
        contract = ""

        for i in range(len(lines)):
            if "$_CONTRACT_$" in lines[i]:
                contract += lines[i] + "\n"
            elif lines[i].startswith("assert"):
                assertion += lines[i] + "\n"

        for i in range(len(lines) - 1, -1, -1):
            if (
                "$_CONTRACT_$" in lines[i]
                or lines[i].startswith("assert")
                or lines[i] == ""
            ):
                del lines[i]

        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith("import"):
                del lines[i]
            else:
                break

        code = "\n".join(lines)
        return "\n" + code + "\n", "\n" + contract, "\n" + assertion


def instrument_inputs(code, entry_point, test_code) -> str:
    globals()["_inputs"] = []
    fn_text = f"""{code.split(f"def {entry_point}")[0]}

def {entry_point}(*args):
    _inputs.append(args)
    return {_ret(entry_point)}
"""
    exec(fn_text + "\n" + test_code.replace("assert ", ""), globals())
    print(fn_text + "\n" + test_code.replace("assert ", ""))
    print(globals()["_inputs"])
    return globals()["_inputs"]


def get_atol(task_id: int) -> float:
    float_ans_list = [
        82,
        85,
        98,
        120,
        124,
        137,
        139,
        163,
        233,
        246,
        248,
        276,
        293,
        300,
        312,
        442,
        574,
        742,
        746,
    ]
    if task_id in float_ans_list:
        return 1e-4
    return 0


if __name__ == "__main__":
    assert not MBPP_PLUS_PATH.exists(), f"{MBPP_PLUS_PATH} already exists!"

    mbpp = get_mbpp()

    with TempDir() as temp_dir:
        tmp_file = os.path.join(temp_dir, MBPP_PLUS_PATH)
        with open(tmp_file, "w") as writer:
            for task in mbpp.values():
                task_id = int(task["task_id"])

                if task_id in [
                    163,
                    228,
                    304,
                    408,
                    776,
                    307,
                    417,
                    443,
                    444,
                    452,
                    464,
                    617,
                    627,
                    738,
                    747,
                    802,
                    393,
                    411,
                    584,
                    625,
                    756,
                    779,
                ]:
                    continue

                task["task_id"] = f"Mbpp/{task_id}"
                task["entry_point"] = get_entry_point(task_id, task["test_list"][0])
                task["prompt"] = f'"""\n{task["prompt"]}\n{task["test_list"][0]}\n"""\n'

                (
                    task["canonical_solution"],
                    task["contract"],
                    task["assertion"],
                ) = get_code_and_contract_and_assertion(task_id)
                if len(task["test_imports"]):
                    task["assertion"] = (
                        "\n".join(task["test_imports"]) + "\n" + task["assertion"]
                    )

                task["base_input"] = instrument_inputs(
                    task["canonical_solution"], task["entry_point"], task["assertion"]
                )

                task["atol"] = get_atol(task_id)

                del task["source_file"]
                del task["code"]
                del task["test_list"]
                del task["test_imports"]
                del task["assertion"]

                task["base_input"] = mbpp_serialize_inputs(task_id, task["base_input"])

                writer.write(json.dumps(task) + "\n")

        shutil.copy2(tmp_file, MBPP_PLUS_PATH)

# === NexusCore/openenv\Lib\site-packages\parso\normalizer.py ===
from contextlib import contextmanager
from typing import Dict, List


class _NormalizerMeta(type):
    def __new__(cls, name, bases, dct):
        new_cls = type.__new__(cls, name, bases, dct)
        new_cls.rule_value_classes = {}
        new_cls.rule_type_classes = {}
        return new_cls


class Normalizer(metaclass=_NormalizerMeta):
    _rule_type_instances: Dict[str, List[type]] = {}
    _rule_value_instances: Dict[str, List[type]] = {}

    def __init__(self, grammar, config):
        self.grammar = grammar
        self._config = config
        self.issues = []

        self._rule_type_instances = self._instantiate_rules('rule_type_classes')
        self._rule_value_instances = self._instantiate_rules('rule_value_classes')

    def _instantiate_rules(self, attr):
        dct = {}
        for base in type(self).mro():
            rules_map = getattr(base, attr, {})
            for type_, rule_classes in rules_map.items():
                new = [rule_cls(self) for rule_cls in rule_classes]
                dct.setdefault(type_, []).extend(new)
        return dct

    def walk(self, node):
        self.initialize(node)
        value = self.visit(node)
        self.finalize()
        return value

    def visit(self, node):
        try:
            children = node.children
        except AttributeError:
            return self.visit_leaf(node)
        else:
            with self.visit_node(node):
                return ''.join(self.visit(child) for child in children)

    @contextmanager
    def visit_node(self, node):
        self._check_type_rules(node)
        yield

    def _check_type_rules(self, node):
        for rule in self._rule_type_instances.get(node.type, []):
            rule.feed_node(node)

    def visit_leaf(self, leaf):
        self._check_type_rules(leaf)

        for rule in self._rule_value_instances.get(leaf.value, []):
            rule.feed_node(leaf)

        return leaf.prefix + leaf.value

    def initialize(self, node):
        pass

    def finalize(self):
        pass

    def add_issue(self, node, code, message):
        issue = Issue(node, code, message)
        if issue not in self.issues:
            self.issues.append(issue)
        return True

    @classmethod
    def register_rule(cls, *, value=None, values=(), type=None, types=()):
        """
        Use it as a class decorator::

            normalizer = Normalizer('grammar', 'config')
            @normalizer.register_rule(value='foo')
            class MyRule(Rule):
                error_code = 42
        """
        values = list(values)
        types = list(types)
        if value is not None:
            values.append(value)
        if type is not None:
            types.append(type)

        if not values and not types:
            raise ValueError("You must register at least something.")

        def decorator(rule_cls):
            for v in values:
                cls.rule_value_classes.setdefault(v, []).append(rule_cls)
            for t in types:
                cls.rule_type_classes.setdefault(t, []).append(rule_cls)
            return rule_cls

        return decorator


class NormalizerConfig:
    normalizer_class = Normalizer

    def create_normalizer(self, grammar):
        if self.normalizer_class is None:
            return None

        return self.normalizer_class(grammar, self)


class Issue:
    def __init__(self, node, code, message):
        self.code = code
        """
        An integer code that stands for the type of error.
        """
        self.message = message
        """
        A message (string) for the issue.
        """
        self.start_pos = node.start_pos
        """
        The start position position of the error as a tuple (line, column). As
        always in |parso| the first line is 1 and the first column 0.
        """
        self.end_pos = node.end_pos

    def __eq__(self, other):
        return self.start_pos == other.start_pos and self.code == other.code

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.code, self.start_pos))

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.code)


class Rule:
    code: int
    message: str

    def __init__(self, normalizer):
        self._normalizer = normalizer

    def is_issue(self, node):
        raise NotImplementedError()

    def get_node(self, node):
        return node

    def _get_message(self, message, node):
        if message is None:
            message = self.message
            if message is None:
                raise ValueError("The message on the class is not set.")
        return message

    def add_issue(self, node, code=None, message=None):
        if code is None:
            code = self.code
            if code is None:
                raise ValueError("The error code on the class is not set.")

        message = self._get_message(message, node)

        self._normalizer.add_issue(node, code, message)

    def feed_node(self, node):
        if self.is_issue(node):
            issue_node = self.get_node(node)
            self.add_issue(issue_node)


class RefactoringNormalizer(Normalizer):
    def __init__(self, node_to_str_map):
        self._node_to_str_map = node_to_str_map

    def visit(self, node):
        try:
            return self._node_to_str_map[node]
        except KeyError:
            return super().visit(node)

    def visit_leaf(self, leaf):
        try:
            return self._node_to_str_map[leaf]
        except KeyError:
            return super().visit_leaf(leaf)

# === NexusCore/openenv\Lib\site-packages\rsa\prime.py ===
#  Copyright 2011 Sybren A. Stüvel <sybren@stuvel.eu>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Numerical functions related to primes.

Implementation based on the book Algorithm Design by Michael T. Goodrich and
Roberto Tamassia, 2002.
"""

import rsa.common
import rsa.randnum

__all__ = ["getprime", "are_relatively_prime"]


def gcd(p: int, q: int) -> int:
    """Returns the greatest common divisor of p and q

    >>> gcd(48, 180)
    12
    """

    while q != 0:
        (p, q) = (q, p % q)
    return p


def get_primality_testing_rounds(number: int) -> int:
    """Returns minimum number of rounds for Miller-Rabing primality testing,
    based on number bitsize.

    According to NIST FIPS 186-4, Appendix C, Table C.3, minimum number of
    rounds of M-R testing, using an error probability of 2 ** (-100), for
    different p, q bitsizes are:
      * p, q bitsize: 512; rounds: 7
      * p, q bitsize: 1024; rounds: 4
      * p, q bitsize: 1536; rounds: 3
    See: http://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf
    """

    # Calculate number bitsize.
    bitsize = rsa.common.bit_size(number)
    # Set number of rounds.
    if bitsize >= 1536:
        return 3
    if bitsize >= 1024:
        return 4
    if bitsize >= 512:
        return 7
    # For smaller bitsizes, set arbitrary number of rounds.
    return 10


def miller_rabin_primality_testing(n: int, k: int) -> bool:
    """Calculates whether n is composite (which is always correct) or prime
    (which theoretically is incorrect with error probability 4**-k), by
    applying Miller-Rabin primality testing.

    For reference and implementation example, see:
    https://en.wikipedia.org/wiki/Miller%E2%80%93Rabin_primality_test

    :param n: Integer to be tested for primality.
    :type n: int
    :param k: Number of rounds (witnesses) of Miller-Rabin testing.
    :type k: int
    :return: False if the number is composite, True if it's probably prime.
    :rtype: bool
    """

    # prevent potential infinite loop when d = 0
    if n < 2:
        return False

    # Decompose (n - 1) to write it as (2 ** r) * d
    # While d is even, divide it by 2 and increase the exponent.
    d = n - 1
    r = 0

    while not (d & 1):
        r += 1
        d >>= 1

    # Test k witnesses.
    for _ in range(k):
        # Generate random integer a, where 2 <= a <= (n - 2)
        a = rsa.randnum.randint(n - 3) + 1

        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue

        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == 1:
                # n is composite.
                return False
            if x == n - 1:
                # Exit inner loop and continue with next witness.
                break
        else:
            # If loop doesn't break, n is composite.
            return False

    return True


def is_prime(number: int) -> bool:
    """Returns True if the number is prime, and False otherwise.

    >>> is_prime(2)
    True
    >>> is_prime(42)
    False
    >>> is_prime(41)
    True
    """

    # Check for small numbers.
    if number < 10:
        return number in {2, 3, 5, 7}

    # Check for even numbers.
    if not (number & 1):
        return False

    # Calculate minimum number of rounds.
    k = get_primality_testing_rounds(number)

    # Run primality testing with (minimum + 1) rounds.
    return miller_rabin_primality_testing(number, k + 1)


def getprime(nbits: int) -> int:
    """Returns a prime number that can be stored in 'nbits' bits.

    >>> p = getprime(128)
    >>> is_prime(p-1)
    False
    >>> is_prime(p)
    True
    >>> is_prime(p+1)
    False

    >>> from rsa import common
    >>> common.bit_size(p) == 128
    True
    """

    assert nbits > 3  # the loop will hang on too small numbers

    while True:
        integer = rsa.randnum.read_random_odd_int(nbits)

        # Test for primeness
        if is_prime(integer):
            return integer

            # Retry if not prime


def are_relatively_prime(a: int, b: int) -> bool:
    """Returns True if a and b are relatively prime, and False if they
    are not.

    >>> are_relatively_prime(2, 3)
    True
    >>> are_relatively_prime(2, 4)
    False
    """

    d = gcd(a, b)
    return d == 1


if __name__ == "__main__":
    print("Running doctests 1000x or until failure")
    import doctest

    for count in range(1000):
        (failures, tests) = doctest.testmod()
        if failures:
            break

        if count % 100 == 0 and count:
            print("%i times" % count)

    print("Doctests done")

# === NexusCore/openenv\Lib\site-packages\debugpy\adapter\launchers.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

import os
import subprocess
import sys

from debugpy import adapter, common
from debugpy.common import log, messaging, sockets
from debugpy.adapter import components, servers, sessions

listener = None


class Launcher(components.Component):
    """Handles the launcher side of a debug session."""

    message_handler = components.Component.message_handler

    def __init__(self, session, stream):
        with session:
            assert not session.launcher
            super().__init__(session, stream)

            self.pid = None
            """Process ID of the debuggee process, as reported by the launcher."""

            self.exit_code = None
            """Exit code of the debuggee process."""

            session.launcher = self

    @message_handler
    def process_event(self, event):
        self.pid = event("systemProcessId", int)
        self.client.propagate_after_start(event)

    @message_handler
    def output_event(self, event):
        self.client.propagate_after_start(event)

    @message_handler
    def exited_event(self, event):
        self.exit_code = event("exitCode", int)
        # We don't want to tell the client about this just yet, because it will then
        # want to disconnect, and the launcher might still be waiting for keypress
        # (if wait-on-exit was enabled). Instead, we'll report the event when we
        # receive "terminated" from the launcher, right before it exits.

    @message_handler
    def terminated_event(self, event):
        try:
            self.client.channel.send_event("exited", {"exitCode": self.exit_code})
        except Exception:
            pass
        self.channel.close()

    def terminate_debuggee(self):
        with self.session:
            if self.exit_code is None:
                try:
                    self.channel.request("terminate")
                except Exception:
                    pass


def spawn_debuggee(
    session,
    start_request,
    python,
    launcher_path,
    adapter_host,
    args,
    shell_expand_args,
    cwd,
    console,
    console_title,
    sudo,
):
    global listener

    # -E tells sudo to propagate environment variables to the target process - this
    # is necessary for launcher to get DEBUGPY_LAUNCHER_PORT and DEBUGPY_LOG_DIR.
    cmdline = ["sudo", "-E"] if sudo else []
    cmdline += python
    cmdline += [launcher_path]
    env = {}

    arguments = dict(start_request.arguments)
    if not session.no_debug:
        _, arguments["port"] = servers.listener.getsockname()
        arguments["adapterAccessToken"] = adapter.access_token

    def on_launcher_connected(sock):
        listener.close()
        stream = messaging.JsonIOStream.from_socket(sock)
        Launcher(session, stream)

    try:
        listener = sockets.serve(
            "Launcher", on_launcher_connected, adapter_host, backlog=1
        )
    except Exception as exc:
        raise start_request.cant_handle(
            "{0} couldn't create listener socket for launcher: {1}", session, exc
        )
    sessions.report_sockets()

    try:
        launcher_host, launcher_port = listener.getsockname()
        launcher_addr = (
            launcher_port
            if launcher_host == "127.0.0.1"
            else f"{launcher_host}:{launcher_port}"
        )
        cmdline += [str(launcher_addr), "--"]
        cmdline += args

        if log.log_dir is not None:
            env[str("DEBUGPY_LOG_DIR")] = log.log_dir
        if log.stderr.levels != {"warning", "error"}:
            env[str("DEBUGPY_LOG_STDERR")] = str(" ".join(log.stderr.levels))

        if console == "internalConsole":
            log.info("{0} spawning launcher: {1!r}", session, cmdline)
            try:
                # If we are talking to the client over stdio, sys.stdin and sys.stdout
                # are redirected to avoid mangling the DAP message stream. Make sure
                # the launcher also respects that.
                subprocess.Popen(
                    cmdline,
                    cwd=cwd,
                    env=dict(list(os.environ.items()) + list(env.items())),
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
            except Exception as exc:
                raise start_request.cant_handle("Failed to spawn launcher: {0}", exc)
        else:
            log.info('{0} spawning launcher via "runInTerminal" request.', session)
            session.client.capabilities.require("supportsRunInTerminalRequest")
            kinds = {"integratedTerminal": "integrated", "externalTerminal": "external"}
            request_args = {
                "kind": kinds[console],
                "title": console_title,
                "args": cmdline,
                "env": env,
            }
            if cwd is not None:
                request_args["cwd"] = cwd
            if shell_expand_args:
                request_args["argsCanBeInterpretedByShell"] = True
            try:
                # It is unspecified whether this request receives a response immediately, or only
                # after the spawned command has completed running, so do not block waiting for it.
                session.client.channel.send_request("runInTerminal", request_args)
            except messaging.MessageHandlingError as exc:
                exc.propagate(start_request)

        # If using sudo, it might prompt for password, and launcher won't start running
        # until the user enters it, so don't apply timeout in that case.
        if not session.wait_for(
            lambda: session.launcher,
            timeout=(None if sudo else common.PROCESS_SPAWN_TIMEOUT),
        ):
            raise start_request.cant_handle("Timed out waiting for launcher to connect")

        try:
            session.launcher.channel.request(start_request.command, arguments)
        except messaging.MessageHandlingError as exc:
            exc.propagate(start_request)

        if not session.wait_for(
            lambda: session.launcher.pid is not None,
            timeout=common.PROCESS_SPAWN_TIMEOUT,
        ):
            raise start_request.cant_handle(
                'Timed out waiting for "process" event from launcher'
            )

        if session.no_debug:
            return

        # Wait for the first incoming connection regardless of the PID - it won't
        # necessarily match due to the use of stubs like py.exe or "conda run".
        conn = servers.wait_for_connection(
            session, lambda conn: True, timeout=common.PROCESS_SPAWN_TIMEOUT
        )
        if conn is None:
            raise start_request.cant_handle("Timed out waiting for debuggee to spawn")
        conn.attach_to_session(session)

    finally:
        listener.close()
        listener = None
        sessions.report_sockets()

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydev_ipython\inputhookqt4.py ===
# -*- coding: utf-8 -*-
"""
Qt4's inputhook support function

Author: Christian Boos
"""

# -----------------------------------------------------------------------------
#  Copyright (C) 2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import os
import signal

from _pydev_bundle._pydev_saved_modules import threading

from pydev_ipython.qt_for_kernel import QtCore, QtGui
from pydev_ipython.inputhook import allow_CTRL_C, ignore_CTRL_C, stdin_ready


# To minimise future merging complexity, rather than edit the entire code base below
# we fake InteractiveShell here
class InteractiveShell:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_hook(self, *args, **kwargs):
        # We don't consider the pre_prompt_hook because we don't have
        # KeyboardInterrupts to consider since we are running under PyDev
        pass


# -----------------------------------------------------------------------------
# Module Globals
# -----------------------------------------------------------------------------

got_kbdint = False
sigint_timer = None

# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


def create_inputhook_qt4(mgr, app=None):
    """Create an input hook for running the Qt4 application event loop.

    Parameters
    ----------
    mgr : an InputHookManager

    app : Qt Application, optional.
        Running application to use.  If not given, we probe Qt for an
        existing application object, and create a new one if none is found.

    Returns
    -------
    A pair consisting of a Qt Application (either the one given or the
    one found or created) and a inputhook.

    Notes
    -----
    We use a custom input hook instead of PyQt4's default one, as it
    interacts better with the readline packages (issue #481).

    The inputhook function works in tandem with a 'pre_prompt_hook'
    which automatically restores the hook as an inputhook in case the
    latter has been temporarily disabled after having intercepted a
    KeyboardInterrupt.
    """

    if app is None:
        app = QtCore.QCoreApplication.instance()
        if app is None:
            app = QtGui.QApplication([" "])

    # Re-use previously created inputhook if any
    ip = InteractiveShell.instance()
    if hasattr(ip, "_inputhook_qt4"):
        return app, ip._inputhook_qt4

    # Otherwise create the inputhook_qt4/preprompthook_qt4 pair of
    # hooks (they both share the got_kbdint flag)

    def inputhook_qt4():
        """PyOS_InputHook python hook for Qt4.

        Process pending Qt events and if there's no pending keyboard
        input, spend a short slice of time (50ms) running the Qt event
        loop.

        As a Python ctypes callback can't raise an exception, we catch
        the KeyboardInterrupt and temporarily deactivate the hook,
        which will let a *second* CTRL+C be processed normally and go
        back to a clean prompt line.
        """
        try:
            allow_CTRL_C()
            app = QtCore.QCoreApplication.instance()
            if not app:  # shouldn't happen, but safer if it happens anyway...
                return 0
            app.processEvents(QtCore.QEventLoop.AllEvents, 300)
            if not stdin_ready():
                # Generally a program would run QCoreApplication::exec()
                # from main() to enter and process the Qt event loop until
                # quit() or exit() is called and the program terminates.
                #
                # For our input hook integration, we need to repeatedly
                # enter and process the Qt event loop for only a short
                # amount of time (say 50ms) to ensure that Python stays
                # responsive to other user inputs.
                #
                # A naive approach would be to repeatedly call
                # QCoreApplication::exec(), using a timer to quit after a
                # short amount of time. Unfortunately, QCoreApplication
                # emits an aboutToQuit signal before stopping, which has
                # the undesirable effect of closing all modal windows.
                #
                # To work around this problem, we instead create a
                # QEventLoop and call QEventLoop::exec(). Other than
                # setting some state variables which do not seem to be
                # used anywhere, the only thing QCoreApplication adds is
                # the aboutToQuit signal which is precisely what we are
                # trying to avoid.
                timer = QtCore.QTimer()
                event_loop = QtCore.QEventLoop()
                timer.timeout.connect(event_loop.quit)
                while not stdin_ready():
                    timer.start(50)
                    event_loop.exec_()
                    timer.stop()
        except KeyboardInterrupt:
            global got_kbdint, sigint_timer

            ignore_CTRL_C()
            got_kbdint = True
            mgr.clear_inputhook()

            # This generates a second SIGINT so the user doesn't have to
            # press CTRL+C twice to get a clean prompt.
            #
            # Since we can't catch the resulting KeyboardInterrupt here
            # (because this is a ctypes callback), we use a timer to
            # generate the SIGINT after we leave this callback.
            #
            # Unfortunately this doesn't work on Windows (SIGINT kills
            # Python and CTRL_C_EVENT doesn't work).
            if os.name == "posix":
                pid = os.getpid()
                if not sigint_timer:
                    sigint_timer = threading.Timer(0.01, os.kill, args=[pid, signal.SIGINT])
                    sigint_timer.start()
            else:
                print("\nKeyboardInterrupt - Ctrl-C again for new prompt")

        except:  # NO exceptions are allowed to escape from a ctypes callback
            ignore_CTRL_C()
            from traceback import print_exc

            print_exc()
            print("Got exception from inputhook_qt4, unregistering.")
            mgr.clear_inputhook()
        finally:
            allow_CTRL_C()
        return 0

    def preprompthook_qt4(ishell):
        """'pre_prompt_hook' used to restore the Qt4 input hook

        (in case the latter was temporarily deactivated after a
        CTRL+C)
        """
        global got_kbdint, sigint_timer

        if sigint_timer:
            sigint_timer.cancel()
            sigint_timer = None

        if got_kbdint:
            mgr.set_inputhook(inputhook_qt4)
        got_kbdint = False

    ip._inputhook_qt4 = inputhook_qt4
    ip.set_hook("pre_prompt_hook", preprompthook_qt4)

    return app, inputhook_qt4

# === NexusCore/openenv\Lib\site-packages\fontTools\cu2qu\cli.py ===
import os
import argparse
import logging
import shutil
import multiprocessing as mp
from contextlib import closing
from functools import partial

import fontTools
from .ufo import font_to_quadratic, fonts_to_quadratic

ufo_module = None
try:
    import ufoLib2 as ufo_module
except ImportError:
    try:
        import defcon as ufo_module
    except ImportError as e:
        pass


logger = logging.getLogger("fontTools.cu2qu")


def _cpu_count():
    try:
        return mp.cpu_count()
    except NotImplementedError:  # pragma: no cover
        return 1


def open_ufo(path):
    if hasattr(ufo_module.Font, "open"):  # ufoLib2
        return ufo_module.Font.open(path)
    return ufo_module.Font(path)  # defcon


def _font_to_quadratic(input_path, output_path=None, **kwargs):
    ufo = open_ufo(input_path)
    logger.info("Converting curves for %s", input_path)
    if font_to_quadratic(ufo, **kwargs):
        logger.info("Saving %s", output_path)
        if output_path:
            ufo.save(output_path)
        else:
            ufo.save()  # save in-place
    elif output_path:
        _copytree(input_path, output_path)


def _samepath(path1, path2):
    # TODO on python3+, there's os.path.samefile
    path1 = os.path.normcase(os.path.abspath(os.path.realpath(path1)))
    path2 = os.path.normcase(os.path.abspath(os.path.realpath(path2)))
    return path1 == path2


def _copytree(input_path, output_path):
    if _samepath(input_path, output_path):
        logger.debug("input and output paths are the same file; skipped copy")
        return
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    shutil.copytree(input_path, output_path)


def _main(args=None):
    """Convert a UFO font from cubic to quadratic curves"""
    parser = argparse.ArgumentParser(prog="cu2qu")
    parser.add_argument("--version", action="version", version=fontTools.__version__)
    parser.add_argument(
        "infiles",
        nargs="+",
        metavar="INPUT",
        help="one or more input UFO source file(s).",
    )
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument(
        "-e",
        "--conversion-error",
        type=float,
        metavar="ERROR",
        default=None,
        help="maxiumum approximation error measured in EM (default: 0.001)",
    )
    parser.add_argument(
        "-m",
        "--mixed",
        default=False,
        action="store_true",
        help="whether to used mixed quadratic and cubic curves",
    )
    parser.add_argument(
        "--keep-direction",
        dest="reverse_direction",
        action="store_false",
        help="do not reverse the contour direction",
    )

    mode_parser = parser.add_mutually_exclusive_group()
    mode_parser.add_argument(
        "-i",
        "--interpolatable",
        action="store_true",
        help="whether curve conversion should keep interpolation compatibility",
    )
    mode_parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        nargs="?",
        default=1,
        const=_cpu_count(),
        metavar="N",
        help="Convert using N multiple processes (default: %(default)s)",
    )

    output_parser = parser.add_mutually_exclusive_group()
    output_parser.add_argument(
        "-o",
        "--output-file",
        default=None,
        metavar="OUTPUT",
        help=(
            "output filename for the converted UFO. By default fonts are "
            "modified in place. This only works with a single input."
        ),
    )
    output_parser.add_argument(
        "-d",
        "--output-dir",
        default=None,
        metavar="DIRECTORY",
        help="output directory where to save converted UFOs",
    )

    options = parser.parse_args(args)

    if ufo_module is None:
        parser.error("Either ufoLib2 or defcon are required to run this script.")

    if not options.verbose:
        level = "WARNING"
    elif options.verbose == 1:
        level = "INFO"
    else:
        level = "DEBUG"
    logging.basicConfig(level=level)

    if len(options.infiles) > 1 and options.output_file:
        parser.error("-o/--output-file can't be used with multile inputs")

    if options.output_dir:
        output_dir = options.output_dir
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        elif not os.path.isdir(output_dir):
            parser.error("'%s' is not a directory" % output_dir)
        output_paths = [
            os.path.join(output_dir, os.path.basename(p)) for p in options.infiles
        ]
    elif options.output_file:
        output_paths = [options.output_file]
    else:
        # save in-place
        output_paths = [None] * len(options.infiles)

    kwargs = dict(
        dump_stats=options.verbose > 0,
        max_err_em=options.conversion_error,
        reverse_direction=options.reverse_direction,
        all_quadratic=False if options.mixed else True,
    )

    if options.interpolatable:
        logger.info("Converting curves compatibly")
        ufos = [open_ufo(infile) for infile in options.infiles]
        if fonts_to_quadratic(ufos, **kwargs):
            for ufo, output_path in zip(ufos, output_paths):
                logger.info("Saving %s", output_path)
                if output_path:
                    ufo.save(output_path)
                else:
                    ufo.save()
        else:
            for input_path, output_path in zip(options.infiles, output_paths):
                if output_path:
                    _copytree(input_path, output_path)
    else:
        jobs = min(len(options.infiles), options.jobs) if options.jobs > 1 else 1
        if jobs > 1:
            func = partial(_font_to_quadratic, **kwargs)
            logger.info("Running %d parallel processes", jobs)
            with closing(mp.Pool(jobs)) as pool:
                pool.starmap(func, zip(options.infiles, output_paths))
        else:
            for input_path, output_path in zip(options.infiles, output_paths):
                _font_to_quadratic(input_path, output_path, **kwargs)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\discuss_service\transports\base.py ===
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

from google.ai.generativelanguage_v1beta import gapic_version as package_version
from google.ai.generativelanguage_v1beta.types import discuss_service

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class DiscussServiceTransport(abc.ABC):
    """Abstract transport class for DiscussService."""

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
            self.generate_message: gapic_v1.method.wrap_method(
                self.generate_message,
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
            self.count_message_tokens: gapic_v1.method.wrap_method(
                self.count_message_tokens,
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
        }

    def close(self):
        """Closes resources associated with the transport.

        .. warning::
             Only call this method if the transport is NOT shared
             with other clients - this may cause errors in other clients!
        """
        raise NotImplementedError()

    @property
    def generate_message(
        self,
    ) -> Callable[
        [discuss_service.GenerateMessageRequest],
        Union[
            discuss_service.GenerateMessageResponse,
            Awaitable[discuss_service.GenerateMessageResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def count_message_tokens(
        self,
    ) -> Callable[
        [discuss_service.CountMessageTokensRequest],
        Union[
            discuss_service.CountMessageTokensResponse,
            Awaitable[discuss_service.CountMessageTokensResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("DiscussServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\commands\user.py ===
# Copyright 2020 The HuggingFace Team. All rights reserved.
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
"""Contains commands to authenticate to the Hugging Face Hub and interact with your repositories.

Usage:
    # login and save token locally.
    huggingface-cli login --token=hf_*** --add-to-git-credential

    # switch between tokens
    huggingface-cli auth switch

    # list all tokens
    huggingface-cli auth list

    # logout from a specific token, if no token-name is provided, all tokens will be deleted from your machine.
    huggingface-cli logout --token-name=your_token_name

    # find out which huggingface.co account you are logged in as
    huggingface-cli whoami
"""

from argparse import _SubParsersAction
from typing import List, Optional

from requests.exceptions import HTTPError

from huggingface_hub.commands import BaseHuggingfaceCLICommand
from huggingface_hub.constants import ENDPOINT
from huggingface_hub.hf_api import HfApi

from .._login import auth_list, auth_switch, login, logout
from ..utils import get_stored_tokens, get_token, logging
from ._cli_utils import ANSI


logger = logging.get_logger(__name__)

try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice

    _inquirer_py_available = True
except ImportError:
    _inquirer_py_available = False


class UserCommands(BaseHuggingfaceCLICommand):
    @staticmethod
    def register_subcommand(parser: _SubParsersAction):
        login_parser = parser.add_parser("login", help="Log in using a token from huggingface.co/settings/tokens")
        login_parser.add_argument(
            "--token",
            type=str,
            help="Token generated from https://huggingface.co/settings/tokens",
        )
        login_parser.add_argument(
            "--add-to-git-credential",
            action="store_true",
            help="Optional: Save token to git credential helper.",
        )
        login_parser.set_defaults(func=lambda args: LoginCommand(args))
        whoami_parser = parser.add_parser("whoami", help="Find out which huggingface.co account you are logged in as.")
        whoami_parser.set_defaults(func=lambda args: WhoamiCommand(args))

        logout_parser = parser.add_parser("logout", help="Log out")
        logout_parser.add_argument(
            "--token-name",
            type=str,
            help="Optional: Name of the access token to log out from.",
        )
        logout_parser.set_defaults(func=lambda args: LogoutCommand(args))

        auth_parser = parser.add_parser("auth", help="Other authentication related commands")
        auth_subparsers = auth_parser.add_subparsers(help="Authentication subcommands")
        auth_switch_parser = auth_subparsers.add_parser("switch", help="Switch between access tokens")
        auth_switch_parser.add_argument(
            "--token-name",
            type=str,
            help="Optional: Name of the access token to switch to.",
        )
        auth_switch_parser.add_argument(
            "--add-to-git-credential",
            action="store_true",
            help="Optional: Save token to git credential helper.",
        )
        auth_switch_parser.set_defaults(func=lambda args: AuthSwitchCommand(args))
        auth_list_parser = auth_subparsers.add_parser("list", help="List all stored access tokens")
        auth_list_parser.set_defaults(func=lambda args: AuthListCommand(args))


class BaseUserCommand:
    def __init__(self, args):
        self.args = args
        self._api = HfApi()


class LoginCommand(BaseUserCommand):
    def run(self):
        logging.set_verbosity_info()
        login(
            token=self.args.token,
            add_to_git_credential=self.args.add_to_git_credential,
        )


class LogoutCommand(BaseUserCommand):
    def run(self):
        logging.set_verbosity_info()
        logout(token_name=self.args.token_name)


class AuthSwitchCommand(BaseUserCommand):
    def run(self):
        logging.set_verbosity_info()
        token_name = self.args.token_name
        if token_name is None:
            token_name = self._select_token_name()

        if token_name is None:
            print("No token name provided. Aborting.")
            exit()
        auth_switch(token_name, add_to_git_credential=self.args.add_to_git_credential)

    def _select_token_name(self) -> Optional[str]:
        token_names = list(get_stored_tokens().keys())

        if not token_names:
            logger.error("No stored tokens found. Please login first.")
            return None

        if _inquirer_py_available:
            return self._select_token_name_tui(token_names)
        # if inquirer is not available, use a simpler terminal UI
        print("Available stored tokens:")
        for i, token_name in enumerate(token_names, 1):
            print(f"{i}. {token_name}")
        while True:
            try:
                choice = input("Enter the number of the token to switch to (or 'q' to quit): ")
                if choice.lower() == "q":
                    return None
                index = int(choice) - 1
                if 0 <= index < len(token_names):
                    return token_names[index]
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number or 'q' to quit.")

    def _select_token_name_tui(self, token_names: List[str]) -> Optional[str]:
        choices = [Choice(token_name, name=token_name) for token_name in token_names]
        try:
            return inquirer.select(
                message="Select a token to switch to:",
                choices=choices,
                default=None,
            ).execute()
        except KeyboardInterrupt:
            logger.info("Token selection cancelled.")
            return None


class AuthListCommand(BaseUserCommand):
    def run(self):
        logging.set_verbosity_info()
        auth_list()


class WhoamiCommand(BaseUserCommand):
    def run(self):
        token = get_token()
        if token is None:
            print("Not logged in")
            exit()
        try:
            info = self._api.whoami(token)
            print(info["name"])
            orgs = [org["name"] for org in info["orgs"]]
            if orgs:
                print(ANSI.bold("orgs: "), ",".join(orgs))

            if ENDPOINT != "https://huggingface.co":
                print(f"Authenticated through private endpoint: {ENDPOINT}")
        except HTTPError as e:
            print(e)
            print(ANSI.red(e.response.text))
            exit(1)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\azure\audio_transcriptions.py ===
import uuid
from typing import Any, Coroutine, Optional, Union

from openai import AsyncAzureOpenAI, AzureOpenAI
from pydantic import BaseModel

from litellm.litellm_core_utils.audio_utils.utils import get_audio_file_name
from litellm.types.utils import FileTypes
from litellm.utils import (
    TranscriptionResponse,
    convert_to_model_response_object,
    extract_duration_from_srt_or_vtt,
)

from .azure import AzureChatCompletion
from .common_utils import AzureOpenAIError


class AzureAudioTranscription(AzureChatCompletion):
    def audio_transcriptions(
        self,
        model: str,
        audio_file: FileTypes,
        optional_params: dict,
        logging_obj: Any,
        model_response: TranscriptionResponse,
        timeout: float,
        max_retries: int,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        api_version: Optional[str] = None,
        client=None,
        azure_ad_token: Optional[str] = None,
        atranscription: bool = False,
        litellm_params: Optional[dict] = None,
    ) -> Union[TranscriptionResponse, Coroutine[Any, Any, TranscriptionResponse]]:
        data = {"model": model, "file": audio_file, **optional_params}

        if atranscription is True:
            return self.async_audio_transcriptions(
                audio_file=audio_file,
                data=data,
                model_response=model_response,
                timeout=timeout,
                api_key=api_key,
                api_base=api_base,
                client=client,
                max_retries=max_retries,
                logging_obj=logging_obj,
                model=model,
                litellm_params=litellm_params,
            )

        azure_client = self.get_azure_openai_client(
            api_version=api_version,
            api_base=api_base,
            api_key=api_key,
            model=model,
            _is_async=False,
            client=client,
            litellm_params=litellm_params,
        )
        if not isinstance(azure_client, AzureOpenAI):
            raise AzureOpenAIError(
                status_code=500,
                message="azure_client is not an instance of AzureOpenAI",
            )

        ## LOGGING
        logging_obj.pre_call(
            input=f"audio_file_{uuid.uuid4()}",
            api_key=azure_client.api_key,
            additional_args={
                "headers": {"Authorization": f"Bearer {azure_client.api_key}"},
                "api_base": azure_client._base_url._uri_reference,
                "atranscription": True,
                "complete_input_dict": data,
            },
        )

        response = azure_client.audio.transcriptions.create(
            **data, timeout=timeout  # type: ignore
        )

        if isinstance(response, BaseModel):
            stringified_response = response.model_dump()
        else:
            stringified_response = TranscriptionResponse(text=response).model_dump()

        ## LOGGING
        logging_obj.post_call(
            input=get_audio_file_name(audio_file),
            api_key=api_key,
            additional_args={"complete_input_dict": data},
            original_response=stringified_response,
        )
        hidden_params = {"model": model, "custom_llm_provider": "azure"}
        final_response: TranscriptionResponse = convert_to_model_response_object(response_object=stringified_response, model_response_object=model_response, hidden_params=hidden_params, response_type="audio_transcription")  # type: ignore
        return final_response

    async def async_audio_transcriptions(
        self,
        audio_file: FileTypes,
        model: str,
        data: dict,
        model_response: TranscriptionResponse,
        timeout: float,
        logging_obj: Any,
        api_version: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        client=None,
        max_retries=None,
        litellm_params: Optional[dict] = None,
    ) -> TranscriptionResponse:
        response = None
        try:
            async_azure_client = self.get_azure_openai_client(
                api_version=api_version,
                api_base=api_base,
                api_key=api_key,
                model=model,
                _is_async=True,
                client=client,
                litellm_params=litellm_params,
            )
            if not isinstance(async_azure_client, AsyncAzureOpenAI):
                raise AzureOpenAIError(
                    status_code=500,
                    message="async_azure_client is not an instance of AsyncAzureOpenAI",
                )

            ## LOGGING
            logging_obj.pre_call(
                input=f"audio_file_{uuid.uuid4()}",
                api_key=async_azure_client.api_key,
                additional_args={
                    "headers": {
                        "Authorization": f"Bearer {async_azure_client.api_key}"
                    },
                    "api_base": async_azure_client._base_url._uri_reference,
                    "atranscription": True,
                    "complete_input_dict": data,
                },
            )

            raw_response = (
                await async_azure_client.audio.transcriptions.with_raw_response.create(
                    **data, timeout=timeout
                )
            )  # type: ignore

            headers = dict(raw_response.headers)
            response = raw_response.parse()

            if isinstance(response, BaseModel):
                stringified_response = response.model_dump()
            else:
                stringified_response = TranscriptionResponse(text=response).model_dump()
                duration = extract_duration_from_srt_or_vtt(response)
                stringified_response["duration"] = duration

            ## LOGGING
            logging_obj.post_call(
                input=get_audio_file_name(audio_file),
                api_key=api_key,
                additional_args={
                    "headers": {
                        "Authorization": f"Bearer {async_azure_client.api_key}"
                    },
                    "api_base": async_azure_client._base_url._uri_reference,
                    "atranscription": True,
                    "complete_input_dict": data,
                },
                original_response=stringified_response,
            )
            hidden_params = {"model": model, "custom_llm_provider": "azure"}
            response = convert_to_model_response_object(
                _response_headers=headers,
                response_object=stringified_response,
                model_response_object=model_response,
                hidden_params=hidden_params,
                response_type="audio_transcription",
            )
            if not isinstance(response, TranscriptionResponse):
                raise AzureOpenAIError(
                    status_code=500,
                    message="response is not an instance of TranscriptionResponse",
                )
            return response
        except Exception as e:
            ## LOGGING
            logging_obj.post_call(
                input=input,
                api_key=api_key,
                original_response=str(e),
            )
            raise e

# === NexusCore/openenv\Lib\site-packages\playwright\async_api\__init__.py ===
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

"""
Python package `playwright` is a Python library to automate Chromium,
Firefox and WebKit with a single API. Playwright is built to enable cross-browser
web automation that is ever-green, capable, reliable and fast.
"""

from typing import Any, Optional, Union, overload

import playwright._impl._api_structures
import playwright._impl._errors
import playwright.async_api._generated
from playwright._impl._assertions import (
    APIResponseAssertions as APIResponseAssertionsImpl,
)
from playwright._impl._assertions import LocatorAssertions as LocatorAssertionsImpl
from playwright._impl._assertions import PageAssertions as PageAssertionsImpl
from playwright.async_api._context_manager import PlaywrightContextManager
from playwright.async_api._generated import (
    Accessibility,
    APIRequest,
    APIRequestContext,
    APIResponse,
    APIResponseAssertions,
    Browser,
    BrowserContext,
    BrowserType,
    CDPSession,
    ConsoleMessage,
    Dialog,
    Download,
    ElementHandle,
    FileChooser,
    Frame,
    FrameLocator,
    JSHandle,
    Keyboard,
    Locator,
    LocatorAssertions,
    Mouse,
    Page,
    PageAssertions,
    Playwright,
    Request,
    Response,
    Route,
    Selectors,
    Touchscreen,
    Video,
    WebError,
    WebSocket,
    WebSocketRoute,
    Worker,
)

ChromiumBrowserContext = BrowserContext

Cookie = playwright._impl._api_structures.Cookie
FilePayload = playwright._impl._api_structures.FilePayload
FloatRect = playwright._impl._api_structures.FloatRect
Geolocation = playwright._impl._api_structures.Geolocation
HttpCredentials = playwright._impl._api_structures.HttpCredentials
PdfMargins = playwright._impl._api_structures.PdfMargins
Position = playwright._impl._api_structures.Position
ProxySettings = playwright._impl._api_structures.ProxySettings
ResourceTiming = playwright._impl._api_structures.ResourceTiming
SourceLocation = playwright._impl._api_structures.SourceLocation
StorageState = playwright._impl._api_structures.StorageState
ViewportSize = playwright._impl._api_structures.ViewportSize

Error = playwright._impl._errors.Error
TimeoutError = playwright._impl._errors.TimeoutError


def async_playwright() -> PlaywrightContextManager:
    return PlaywrightContextManager()


class Expect:
    _unset: Any = object()

    def __init__(self) -> None:
        self._timeout: Optional[float] = None

    def set_options(self, timeout: Optional[float] = _unset) -> None:
        """
        This method sets global `expect()` options.

        Args:
            timeout (float): Timeout value in milliseconds. Default to 5000 milliseconds.

        Returns:
            None
        """
        if timeout is not self._unset:
            self._timeout = timeout

    @overload
    def __call__(
        self, actual: Page, message: Optional[str] = None
    ) -> PageAssertions: ...

    @overload
    def __call__(
        self, actual: Locator, message: Optional[str] = None
    ) -> LocatorAssertions: ...

    @overload
    def __call__(
        self, actual: APIResponse, message: Optional[str] = None
    ) -> APIResponseAssertions: ...

    def __call__(
        self, actual: Union[Page, Locator, APIResponse], message: Optional[str] = None
    ) -> Union[PageAssertions, LocatorAssertions, APIResponseAssertions]:
        if isinstance(actual, Page):
            return PageAssertions(
                PageAssertionsImpl(actual._impl_obj, self._timeout, message=message)
            )
        elif isinstance(actual, Locator):
            return LocatorAssertions(
                LocatorAssertionsImpl(actual._impl_obj, self._timeout, message=message)
            )
        elif isinstance(actual, APIResponse):
            return APIResponseAssertions(
                APIResponseAssertionsImpl(
                    actual._impl_obj, self._timeout, message=message
                )
            )
        raise ValueError(f"Unsupported type: {type(actual)}")


expect = Expect()


__all__ = [
    "expect",
    "async_playwright",
    "Accessibility",
    "APIRequest",
    "APIRequestContext",
    "APIResponse",
    "Browser",
    "BrowserContext",
    "BrowserType",
    "CDPSession",
    "ChromiumBrowserContext",
    "ConsoleMessage",
    "Cookie",
    "Dialog",
    "Download",
    "ElementHandle",
    "Error",
    "FileChooser",
    "FilePayload",
    "FloatRect",
    "Frame",
    "FrameLocator",
    "Geolocation",
    "HttpCredentials",
    "JSHandle",
    "Keyboard",
    "Locator",
    "Mouse",
    "Page",
    "PdfMargins",
    "Position",
    "Playwright",
    "ProxySettings",
    "Request",
    "ResourceTiming",
    "Response",
    "Route",
    "Selectors",
    "SourceLocation",
    "StorageState",
    "TimeoutError",
    "Touchscreen",
    "Video",
    "ViewportSize",
    "WebError",
    "WebSocket",
    "WebSocketRoute",
    "Worker",
]

# === NexusCore/openenv\Lib\site-packages\playwright\sync_api\__init__.py ===
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

"""
Python package `playwright` is a Python library to automate Chromium,
Firefox and WebKit with a single API. Playwright is built to enable cross-browser
web automation that is ever-green, capable, reliable and fast.
"""

from typing import Any, Optional, Union, overload

import playwright._impl._api_structures
import playwright._impl._errors
import playwright.sync_api._generated
from playwright._impl._assertions import (
    APIResponseAssertions as APIResponseAssertionsImpl,
)
from playwright._impl._assertions import LocatorAssertions as LocatorAssertionsImpl
from playwright._impl._assertions import PageAssertions as PageAssertionsImpl
from playwright.sync_api._context_manager import PlaywrightContextManager
from playwright.sync_api._generated import (
    Accessibility,
    APIRequest,
    APIRequestContext,
    APIResponse,
    APIResponseAssertions,
    Browser,
    BrowserContext,
    BrowserType,
    CDPSession,
    ConsoleMessage,
    Dialog,
    Download,
    ElementHandle,
    FileChooser,
    Frame,
    FrameLocator,
    JSHandle,
    Keyboard,
    Locator,
    LocatorAssertions,
    Mouse,
    Page,
    PageAssertions,
    Playwright,
    Request,
    Response,
    Route,
    Selectors,
    Touchscreen,
    Video,
    WebError,
    WebSocket,
    WebSocketRoute,
    Worker,
)

ChromiumBrowserContext = BrowserContext

Cookie = playwright._impl._api_structures.Cookie
FilePayload = playwright._impl._api_structures.FilePayload
FloatRect = playwright._impl._api_structures.FloatRect
Geolocation = playwright._impl._api_structures.Geolocation
HttpCredentials = playwright._impl._api_structures.HttpCredentials
PdfMargins = playwright._impl._api_structures.PdfMargins
Position = playwright._impl._api_structures.Position
ProxySettings = playwright._impl._api_structures.ProxySettings
ResourceTiming = playwright._impl._api_structures.ResourceTiming
SourceLocation = playwright._impl._api_structures.SourceLocation
StorageState = playwright._impl._api_structures.StorageState
ViewportSize = playwright._impl._api_structures.ViewportSize

Error = playwright._impl._errors.Error
TimeoutError = playwright._impl._errors.TimeoutError


def sync_playwright() -> PlaywrightContextManager:
    return PlaywrightContextManager()


class Expect:
    _unset: Any = object()

    def __init__(self) -> None:
        self._timeout: Optional[float] = None

    def set_options(self, timeout: Optional[float] = _unset) -> None:
        """
        This method sets global `expect()` options.

        Args:
            timeout (float): Timeout value in milliseconds. Default to 5000 milliseconds.

        Returns:
            None
        """
        if timeout is not self._unset:
            self._timeout = timeout

    @overload
    def __call__(
        self, actual: Page, message: Optional[str] = None
    ) -> PageAssertions: ...

    @overload
    def __call__(
        self, actual: Locator, message: Optional[str] = None
    ) -> LocatorAssertions: ...

    @overload
    def __call__(
        self, actual: APIResponse, message: Optional[str] = None
    ) -> APIResponseAssertions: ...

    def __call__(
        self, actual: Union[Page, Locator, APIResponse], message: Optional[str] = None
    ) -> Union[PageAssertions, LocatorAssertions, APIResponseAssertions]:
        if isinstance(actual, Page):
            return PageAssertions(
                PageAssertionsImpl(actual._impl_obj, self._timeout, message=message)
            )
        elif isinstance(actual, Locator):
            return LocatorAssertions(
                LocatorAssertionsImpl(actual._impl_obj, self._timeout, message=message)
            )
        elif isinstance(actual, APIResponse):
            return APIResponseAssertions(
                APIResponseAssertionsImpl(
                    actual._impl_obj, self._timeout, message=message
                )
            )
        raise ValueError(f"Unsupported type: {type(actual)}")


expect = Expect()


__all__ = [
    "expect",
    "Accessibility",
    "APIRequest",
    "APIRequestContext",
    "APIResponse",
    "Browser",
    "BrowserContext",
    "BrowserType",
    "CDPSession",
    "ChromiumBrowserContext",
    "ConsoleMessage",
    "Cookie",
    "Dialog",
    "Download",
    "ElementHandle",
    "Error",
    "FileChooser",
    "FilePayload",
    "FloatRect",
    "Frame",
    "FrameLocator",
    "Geolocation",
    "HttpCredentials",
    "JSHandle",
    "Keyboard",
    "Locator",
    "Mouse",
    "Page",
    "PdfMargins",
    "Position",
    "Playwright",
    "ProxySettings",
    "Request",
    "ResourceTiming",
    "Response",
    "Route",
    "Selectors",
    "SourceLocation",
    "StorageState",
    "sync_playwright",
    "TimeoutError",
    "Touchscreen",
    "Video",
    "ViewportSize",
    "WebError",
    "WebSocket",
    "WebSocketRoute",
    "Worker",
]

# === NexusCore/openenv\Lib\site-packages\pyreadline3\keysyms\common.py ===
# -*- coding: utf-8 -*-
# *****************************************************************************
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006-2020 Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#       Copyright (C) 2020 Bassem Girgis. <brgirgis@gmail.com>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# *****************************************************************************
# table for translating virtual keys to X windows key symbols


try:
    set
except NameError:
    from sets import Set as set

from pyreadline3.unicode_helper import ensure_unicode

validkey = set(
    [
        "cancel",
        "backspace",
        "tab",
        "clear",
        "return",
        "shift_l",
        "control_l",
        "alt_l",
        "pause",
        "caps_lock",
        "escape",
        "space",
        "prior",
        "next",
        "end",
        "home",
        "left",
        "up",
        "right",
        "down",
        "select",
        "print",
        "execute",
        "snapshot",
        "insert",
        "delete",
        "help",
        "f1",
        "f2",
        "f3",
        "f4",
        "f5",
        "f6",
        "f7",
        "f8",
        "f9",
        "f10",
        "f11",
        "f12",
        "f13",
        "f14",
        "f15",
        "f16",
        "f17",
        "f18",
        "f19",
        "f20",
        "f21",
        "f22",
        "f23",
        "f24",
        "num_lock",
        "scroll_lock",
        "vk_apps",
        "vk_processkey",
        "vk_attn",
        "vk_crsel",
        "vk_exsel",
        "vk_ereof",
        "vk_play",
        "vk_zoom",
        "vk_noname",
        "vk_pa1",
        "vk_oem_clear",
        "numpad0",
        "numpad1",
        "numpad2",
        "numpad3",
        "numpad4",
        "numpad5",
        "numpad6",
        "numpad7",
        "numpad8",
        "numpad9",
        "divide",
        "multiply",
        "add",
        "subtract",
        "vk_decimal",
    ]
)

escape_sequence_to_special_key = {
    "\\e[a": "up",
    "\\e[b": "down",
    "del": "delete",
}


class KeyPress(object):
    def __init__(self, char="", shift=False, control=False, meta=False, keyname=""):
        if control or meta or shift:
            char = char.upper()
        self.info = dict(
            char=char, shift=shift, control=control, meta=meta, keyname=keyname
        )

    def create(name):
        def get(self):
            return self.info[name]

        def set(self, value):
            self.info[name] = value

        return property(get, set)

    char = create("char")
    shift = create("shift")
    control = create("control")
    meta = create("meta")
    keyname = create("keyname")

    def __repr__(self):
        return "(%s,%s,%s,%s)" % tuple(map(ensure_unicode, self.tuple()))

    def tuple(self):
        if self.keyname:
            return (self.control, self.meta, self.shift, self.keyname)
        else:
            if self.control or self.meta or self.shift:
                return (self.control, self.meta, self.shift, self.char.upper())
            else:
                return (self.control, self.meta, self.shift, self.char)

    def __eq__(self, other):
        if isinstance(other, KeyPress):
            s = self.tuple()
            o = other.tuple()
            return s == o
        else:
            return False


def make_KeyPress_from_keydescr(keydescr):
    keyinfo = KeyPress()
    if len(keydescr) > 2 and keydescr[:1] == '"' and keydescr[-1:] == '"':
        keydescr = keydescr[1:-1]

    while True:
        lkeyname = keydescr.lower()
        if lkeyname.startswith("control-"):
            keyinfo.control = True
            keydescr = keydescr[8:]
        elif lkeyname.startswith("ctrl-"):
            keyinfo.control = True
            keydescr = keydescr[5:]
        elif keydescr.lower().startswith("\\c-"):
            keyinfo.control = True
            keydescr = keydescr[3:]
        elif keydescr.lower().startswith("\\m-"):
            keyinfo.meta = True
            keydescr = keydescr[3:]
        elif keydescr in escape_sequence_to_special_key:
            keydescr = escape_sequence_to_special_key[keydescr]
        elif lkeyname.startswith("meta-"):
            keyinfo.meta = True
            keydescr = keydescr[5:]
        elif lkeyname.startswith("alt-"):
            keyinfo.meta = True
            keydescr = keydescr[4:]
        elif lkeyname.startswith("shift-"):
            keyinfo.shift = True
            keydescr = keydescr[6:]
        else:
            if len(keydescr) > 1:
                if keydescr.strip().lower() in validkey:
                    keyinfo.keyname = keydescr.strip().lower()
                    keyinfo.char = ""
                else:
                    raise IndexError("Not a valid key: '%s'" % keydescr)
            else:
                keyinfo.char = keydescr
            return keyinfo


if __name__ == "__main__":
    import startup

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\performance_timeline.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: PerformanceTimeline (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import network
from . import page


@dataclass
class LargestContentfulPaint:
    '''
    See https://github.com/WICG/LargestContentfulPaint and largest_contentful_paint.idl
    '''
    render_time: network.TimeSinceEpoch

    load_time: network.TimeSinceEpoch

    #: The number of pixels being painted.
    size: float

    #: The id attribute of the element, if available.
    element_id: typing.Optional[str] = None

    #: The URL of the image (may be trimmed).
    url: typing.Optional[str] = None

    node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['renderTime'] = self.render_time.to_json()
        json['loadTime'] = self.load_time.to_json()
        json['size'] = self.size
        if self.element_id is not None:
            json['elementId'] = self.element_id
        if self.url is not None:
            json['url'] = self.url
        if self.node_id is not None:
            json['nodeId'] = self.node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            render_time=network.TimeSinceEpoch.from_json(json['renderTime']),
            load_time=network.TimeSinceEpoch.from_json(json['loadTime']),
            size=float(json['size']),
            element_id=str(json['elementId']) if 'elementId' in json else None,
            url=str(json['url']) if 'url' in json else None,
            node_id=dom.BackendNodeId.from_json(json['nodeId']) if 'nodeId' in json else None,
        )


@dataclass
class LayoutShiftAttribution:
    previous_rect: dom.Rect

    current_rect: dom.Rect

    node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['previousRect'] = self.previous_rect.to_json()
        json['currentRect'] = self.current_rect.to_json()
        if self.node_id is not None:
            json['nodeId'] = self.node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            previous_rect=dom.Rect.from_json(json['previousRect']),
            current_rect=dom.Rect.from_json(json['currentRect']),
            node_id=dom.BackendNodeId.from_json(json['nodeId']) if 'nodeId' in json else None,
        )


@dataclass
class LayoutShift:
    '''
    See https://wicg.github.io/layout-instability/#sec-layout-shift and layout_shift.idl
    '''
    #: Score increment produced by this event.
    value: float

    had_recent_input: bool

    last_input_time: network.TimeSinceEpoch

    sources: typing.List[LayoutShiftAttribution]

    def to_json(self):
        json = dict()
        json['value'] = self.value
        json['hadRecentInput'] = self.had_recent_input
        json['lastInputTime'] = self.last_input_time.to_json()
        json['sources'] = [i.to_json() for i in self.sources]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=float(json['value']),
            had_recent_input=bool(json['hadRecentInput']),
            last_input_time=network.TimeSinceEpoch.from_json(json['lastInputTime']),
            sources=[LayoutShiftAttribution.from_json(i) for i in json['sources']],
        )


@dataclass
class TimelineEvent:
    #: Identifies the frame that this event is related to. Empty for non-frame targets.
    frame_id: page.FrameId

    #: The event type, as specified in https://w3c.github.io/performance-timeline/#dom-performanceentry-entrytype
    #: This determines which of the optional "details" fields is present.
    type_: str

    #: Name may be empty depending on the type.
    name: str

    #: Time in seconds since Epoch, monotonically increasing within document lifetime.
    time: network.TimeSinceEpoch

    #: Event duration, if applicable.
    duration: typing.Optional[float] = None

    lcp_details: typing.Optional[LargestContentfulPaint] = None

    layout_shift_details: typing.Optional[LayoutShift] = None

    def to_json(self):
        json = dict()
        json['frameId'] = self.frame_id.to_json()
        json['type'] = self.type_
        json['name'] = self.name
        json['time'] = self.time.to_json()
        if self.duration is not None:
            json['duration'] = self.duration
        if self.lcp_details is not None:
            json['lcpDetails'] = self.lcp_details.to_json()
        if self.layout_shift_details is not None:
            json['layoutShiftDetails'] = self.layout_shift_details.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            frame_id=page.FrameId.from_json(json['frameId']),
            type_=str(json['type']),
            name=str(json['name']),
            time=network.TimeSinceEpoch.from_json(json['time']),
            duration=float(json['duration']) if 'duration' in json else None,
            lcp_details=LargestContentfulPaint.from_json(json['lcpDetails']) if 'lcpDetails' in json else None,
            layout_shift_details=LayoutShift.from_json(json['layoutShiftDetails']) if 'layoutShiftDetails' in json else None,
        )


def enable(
        event_types: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Previously buffered events would be reported before method returns.
    See also: timelineEventAdded

    :param event_types: The types of event to report, as specified in https://w3c.github.io/performance-timeline/#dom-performanceentry-entrytype The specified filter overrides any previous filters, passing empty filter disables recording. Note that not all types exposed to the web platform are currently supported.
    '''
    params: T_JSON_DICT = dict()
    params['eventTypes'] = [i for i in event_types]
    cmd_dict: T_JSON_DICT = {
        'method': 'PerformanceTimeline.enable',
        'params': params,
    }
    json = yield cmd_dict


@event_class('PerformanceTimeline.timelineEventAdded')
@dataclass
class TimelineEventAdded:
    '''
    Sent when a performance timeline event is added. See reportPerformanceTimeline method.
    '''
    event: TimelineEvent

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TimelineEventAdded:
        return cls(
            event=TimelineEvent.from_json(json['event'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\performance_timeline.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: PerformanceTimeline (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import network
from . import page


@dataclass
class LargestContentfulPaint:
    '''
    See https://github.com/WICG/LargestContentfulPaint and largest_contentful_paint.idl
    '''
    render_time: network.TimeSinceEpoch

    load_time: network.TimeSinceEpoch

    #: The number of pixels being painted.
    size: float

    #: The id attribute of the element, if available.
    element_id: typing.Optional[str] = None

    #: The URL of the image (may be trimmed).
    url: typing.Optional[str] = None

    node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['renderTime'] = self.render_time.to_json()
        json['loadTime'] = self.load_time.to_json()
        json['size'] = self.size
        if self.element_id is not None:
            json['elementId'] = self.element_id
        if self.url is not None:
            json['url'] = self.url
        if self.node_id is not None:
            json['nodeId'] = self.node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            render_time=network.TimeSinceEpoch.from_json(json['renderTime']),
            load_time=network.TimeSinceEpoch.from_json(json['loadTime']),
            size=float(json['size']),
            element_id=str(json['elementId']) if 'elementId' in json else None,
            url=str(json['url']) if 'url' in json else None,
            node_id=dom.BackendNodeId.from_json(json['nodeId']) if 'nodeId' in json else None,
        )


@dataclass
class LayoutShiftAttribution:
    previous_rect: dom.Rect

    current_rect: dom.Rect

    node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['previousRect'] = self.previous_rect.to_json()
        json['currentRect'] = self.current_rect.to_json()
        if self.node_id is not None:
            json['nodeId'] = self.node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            previous_rect=dom.Rect.from_json(json['previousRect']),
            current_rect=dom.Rect.from_json(json['currentRect']),
            node_id=dom.BackendNodeId.from_json(json['nodeId']) if 'nodeId' in json else None,
        )


@dataclass
class LayoutShift:
    '''
    See https://wicg.github.io/layout-instability/#sec-layout-shift and layout_shift.idl
    '''
    #: Score increment produced by this event.
    value: float

    had_recent_input: bool

    last_input_time: network.TimeSinceEpoch

    sources: typing.List[LayoutShiftAttribution]

    def to_json(self):
        json = dict()
        json['value'] = self.value
        json['hadRecentInput'] = self.had_recent_input
        json['lastInputTime'] = self.last_input_time.to_json()
        json['sources'] = [i.to_json() for i in self.sources]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=float(json['value']),
            had_recent_input=bool(json['hadRecentInput']),
            last_input_time=network.TimeSinceEpoch.from_json(json['lastInputTime']),
            sources=[LayoutShiftAttribution.from_json(i) for i in json['sources']],
        )


@dataclass
class TimelineEvent:
    #: Identifies the frame that this event is related to. Empty for non-frame targets.
    frame_id: page.FrameId

    #: The event type, as specified in https://w3c.github.io/performance-timeline/#dom-performanceentry-entrytype
    #: This determines which of the optional "details" fields is present.
    type_: str

    #: Name may be empty depending on the type.
    name: str

    #: Time in seconds since Epoch, monotonically increasing within document lifetime.
    time: network.TimeSinceEpoch

    #: Event duration, if applicable.
    duration: typing.Optional[float] = None

    lcp_details: typing.Optional[LargestContentfulPaint] = None

    layout_shift_details: typing.Optional[LayoutShift] = None

    def to_json(self):
        json = dict()
        json['frameId'] = self.frame_id.to_json()
        json['type'] = self.type_
        json['name'] = self.name
        json['time'] = self.time.to_json()
        if self.duration is not None:
            json['duration'] = self.duration
        if self.lcp_details is not None:
            json['lcpDetails'] = self.lcp_details.to_json()
        if self.layout_shift_details is not None:
            json['layoutShiftDetails'] = self.layout_shift_details.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            frame_id=page.FrameId.from_json(json['frameId']),
            type_=str(json['type']),
            name=str(json['name']),
            time=network.TimeSinceEpoch.from_json(json['time']),
            duration=float(json['duration']) if 'duration' in json else None,
            lcp_details=LargestContentfulPaint.from_json(json['lcpDetails']) if 'lcpDetails' in json else None,
            layout_shift_details=LayoutShift.from_json(json['layoutShiftDetails']) if 'layoutShiftDetails' in json else None,
        )


def enable(
        event_types: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Previously buffered events would be reported before method returns.
    See also: timelineEventAdded

    :param event_types: The types of event to report, as specified in https://w3c.github.io/performance-timeline/#dom-performanceentry-entrytype The specified filter overrides any previous filters, passing empty filter disables recording. Note that not all types exposed to the web platform are currently supported.
    '''
    params: T_JSON_DICT = dict()
    params['eventTypes'] = [i for i in event_types]
    cmd_dict: T_JSON_DICT = {
        'method': 'PerformanceTimeline.enable',
        'params': params,
    }
    json = yield cmd_dict


@event_class('PerformanceTimeline.timelineEventAdded')
@dataclass
class TimelineEventAdded:
    '''
    Sent when a performance timeline event is added. See reportPerformanceTimeline method.
    '''
    event: TimelineEvent

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TimelineEventAdded:
        return cls(
            event=TimelineEvent.from_json(json['event'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\performance_timeline.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: PerformanceTimeline (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import network
from . import page


@dataclass
class LargestContentfulPaint:
    '''
    See https://github.com/WICG/LargestContentfulPaint and largest_contentful_paint.idl
    '''
    render_time: network.TimeSinceEpoch

    load_time: network.TimeSinceEpoch

    #: The number of pixels being painted.
    size: float

    #: The id attribute of the element, if available.
    element_id: typing.Optional[str] = None

    #: The URL of the image (may be trimmed).
    url: typing.Optional[str] = None

    node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['renderTime'] = self.render_time.to_json()
        json['loadTime'] = self.load_time.to_json()
        json['size'] = self.size
        if self.element_id is not None:
            json['elementId'] = self.element_id
        if self.url is not None:
            json['url'] = self.url
        if self.node_id is not None:
            json['nodeId'] = self.node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            render_time=network.TimeSinceEpoch.from_json(json['renderTime']),
            load_time=network.TimeSinceEpoch.from_json(json['loadTime']),
            size=float(json['size']),
            element_id=str(json['elementId']) if 'elementId' in json else None,
            url=str(json['url']) if 'url' in json else None,
            node_id=dom.BackendNodeId.from_json(json['nodeId']) if 'nodeId' in json else None,
        )


@dataclass
class LayoutShiftAttribution:
    previous_rect: dom.Rect

    current_rect: dom.Rect

    node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['previousRect'] = self.previous_rect.to_json()
        json['currentRect'] = self.current_rect.to_json()
        if self.node_id is not None:
            json['nodeId'] = self.node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            previous_rect=dom.Rect.from_json(json['previousRect']),
            current_rect=dom.Rect.from_json(json['currentRect']),
            node_id=dom.BackendNodeId.from_json(json['nodeId']) if 'nodeId' in json else None,
        )


@dataclass
class LayoutShift:
    '''
    See https://wicg.github.io/layout-instability/#sec-layout-shift and layout_shift.idl
    '''
    #: Score increment produced by this event.
    value: float

    had_recent_input: bool

    last_input_time: network.TimeSinceEpoch

    sources: typing.List[LayoutShiftAttribution]

    def to_json(self):
        json = dict()
        json['value'] = self.value
        json['hadRecentInput'] = self.had_recent_input
        json['lastInputTime'] = self.last_input_time.to_json()
        json['sources'] = [i.to_json() for i in self.sources]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=float(json['value']),
            had_recent_input=bool(json['hadRecentInput']),
            last_input_time=network.TimeSinceEpoch.from_json(json['lastInputTime']),
            sources=[LayoutShiftAttribution.from_json(i) for i in json['sources']],
        )


@dataclass
class TimelineEvent:
    #: Identifies the frame that this event is related to. Empty for non-frame targets.
    frame_id: page.FrameId

    #: The event type, as specified in https://w3c.github.io/performance-timeline/#dom-performanceentry-entrytype
    #: This determines which of the optional "details" fields is present.
    type_: str

    #: Name may be empty depending on the type.
    name: str

    #: Time in seconds since Epoch, monotonically increasing within document lifetime.
    time: network.TimeSinceEpoch

    #: Event duration, if applicable.
    duration: typing.Optional[float] = None

    lcp_details: typing.Optional[LargestContentfulPaint] = None

    layout_shift_details: typing.Optional[LayoutShift] = None

    def to_json(self):
        json = dict()
        json['frameId'] = self.frame_id.to_json()
        json['type'] = self.type_
        json['name'] = self.name
        json['time'] = self.time.to_json()
        if self.duration is not None:
            json['duration'] = self.duration
        if self.lcp_details is not None:
            json['lcpDetails'] = self.lcp_details.to_json()
        if self.layout_shift_details is not None:
            json['layoutShiftDetails'] = self.layout_shift_details.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            frame_id=page.FrameId.from_json(json['frameId']),
            type_=str(json['type']),
            name=str(json['name']),
            time=network.TimeSinceEpoch.from_json(json['time']),
            duration=float(json['duration']) if 'duration' in json else None,
            lcp_details=LargestContentfulPaint.from_json(json['lcpDetails']) if 'lcpDetails' in json else None,
            layout_shift_details=LayoutShift.from_json(json['layoutShiftDetails']) if 'layoutShiftDetails' in json else None,
        )


def enable(
        event_types: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Previously buffered events would be reported before method returns.
    See also: timelineEventAdded

    :param event_types: The types of event to report, as specified in https://w3c.github.io/performance-timeline/#dom-performanceentry-entrytype The specified filter overrides any previous filters, passing empty filter disables recording. Note that not all types exposed to the web platform are currently supported.
    '''
    params: T_JSON_DICT = dict()
    params['eventTypes'] = [i for i in event_types]
    cmd_dict: T_JSON_DICT = {
        'method': 'PerformanceTimeline.enable',
        'params': params,
    }
    json = yield cmd_dict


@event_class('PerformanceTimeline.timelineEventAdded')
@dataclass
class TimelineEventAdded:
    '''
    Sent when a performance timeline event is added. See reportPerformanceTimeline method.
    '''
    event: TimelineEvent

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TimelineEventAdded:
        return cls(
            event=TimelineEvent.from_json(json['event'])
        )

# === NexusCore/openenv\Lib\site-packages\googleapiclient\errors.py ===
# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Errors for the library.

All exceptions defined by the library
should be defined in this file.
"""
from __future__ import absolute_import

__author__ = "jcgregorio@google.com (Joe Gregorio)"

import json

from googleapiclient import _helpers as util


class Error(Exception):
    """Base error for this module."""

    pass


class HttpError(Error):
    """HTTP data was invalid or unexpected."""

    @util.positional(3)
    def __init__(self, resp, content, uri=None):
        self.resp = resp
        if not isinstance(content, bytes):
            raise TypeError("HTTP content should be bytes")
        self.content = content
        self.uri = uri
        self.error_details = ""
        self.reason = self._get_reason()

    @property
    def status_code(self):
        """Return the HTTP status code from the response content."""
        return self.resp.status

    def _get_reason(self):
        """Calculate the reason for the error from the response content."""
        reason = self.resp.reason
        try:
            try:
                data = json.loads(self.content.decode("utf-8"))
            except json.JSONDecodeError:
                # In case it is not json
                data = self.content.decode("utf-8")
            if isinstance(data, dict):
                reason = data["error"]["message"]
                error_detail_keyword = next(
                    (
                        kw
                        for kw in ["detail", "details", "errors", "message"]
                        if kw in data["error"]
                    ),
                    "",
                )
                if error_detail_keyword:
                    self.error_details = data["error"][error_detail_keyword]
            elif isinstance(data, list) and len(data) > 0:
                first_error = data[0]
                reason = first_error["error"]["message"]
                if "details" in first_error["error"]:
                    self.error_details = first_error["error"]["details"]
            else:
                self.error_details = data
        except (ValueError, KeyError, TypeError):
            pass
        if reason is None:
            reason = ""
        return reason.strip()

    def __repr__(self):
        if self.error_details:
            return '<HttpError %s when requesting %s returned "%s". Details: "%s">' % (
                self.resp.status,
                self.uri,
                self.reason,
                self.error_details,
            )
        elif self.uri:
            return '<HttpError %s when requesting %s returned "%s">' % (
                self.resp.status,
                self.uri,
                self.reason,
            )
        else:
            return '<HttpError %s "%s">' % (self.resp.status, self.reason)

    __str__ = __repr__


class InvalidJsonError(Error):
    """The JSON returned could not be parsed."""

    pass


class UnknownFileType(Error):
    """File type unknown or unexpected."""

    pass


class UnknownLinkType(Error):
    """Link type unknown or unexpected."""

    pass


class UnknownApiNameOrVersion(Error):
    """No API with that name and version exists."""

    pass


class UnacceptableMimeTypeError(Error):
    """That is an unacceptable mimetype for this operation."""

    pass


class MediaUploadSizeError(Error):
    """Media is larger than the method can accept."""

    pass


class ResumableUploadError(HttpError):
    """Error occurred during resumable upload."""

    pass


class InvalidChunkSizeError(Error):
    """The given chunksize is not valid."""

    pass


class InvalidNotificationError(Error):
    """The channel Notification is invalid."""

    pass


class BatchError(HttpError):
    """Error occurred during batch operations."""

    @util.positional(2)
    def __init__(self, reason, resp=None, content=None):
        self.resp = resp
        self.content = content
        self.reason = reason

    def __repr__(self):
        if getattr(self.resp, "status", None) is None:
            return '<BatchError "%s">' % (self.reason)
        else:
            return '<BatchError %s "%s">' % (self.resp.status, self.reason)

    __str__ = __repr__


class UnexpectedMethodError(Error):
    """Exception raised by RequestMockBuilder on unexpected calls."""

    @util.positional(1)
    def __init__(self, methodId=None):
        """Constructor for an UnexpectedMethodError."""
        super(UnexpectedMethodError, self).__init__(
            "Received unexpected call %s" % methodId
        )


class UnexpectedBodyError(Error):
    """Exception raised by RequestMockBuilder on unexpected bodies."""

    def __init__(self, expected, provided):
        """Constructor for an UnexpectedMethodError."""
        super(UnexpectedBodyError, self).__init__(
            "Expected: [%s] - Provided: [%s]" % (expected, provided)
        )

# === NexusCore/openenv\Lib\site-packages\trio\_timeouts.py ===
from __future__ import annotations

import math
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, NoReturn

import trio

if TYPE_CHECKING:
    from collections.abc import Generator


def move_on_at(deadline: float, *, shield: bool = False) -> trio.CancelScope:
    """Use as a context manager to create a cancel scope with the given
    absolute deadline.

    Args:
      deadline (float): The deadline.
      shield (bool): Initial value for the `~trio.CancelScope.shield` attribute
          of the newly created cancel scope.

    Raises:
      ValueError: if deadline is NaN.

    """
    # CancelScope validates that deadline isn't math.nan
    return trio.CancelScope(deadline=deadline, shield=shield)


def move_on_after(
    seconds: float,
    *,
    shield: bool = False,
) -> trio.CancelScope:
    """Use as a context manager to create a cancel scope whose deadline is
    set to now + *seconds*.

    The deadline of the cancel scope is calculated upon entering.

    Args:
      seconds (float): The timeout.
      shield (bool): Initial value for the `~trio.CancelScope.shield` attribute
          of the newly created cancel scope.

    Raises:
      ValueError: if ``seconds`` is less than zero or NaN.

    """
    # duplicate validation logic to have the correct parameter name
    if seconds < 0:
        raise ValueError("`seconds` must be non-negative")
    if math.isnan(seconds):
        raise ValueError("`seconds` must not be NaN")
    return trio.CancelScope(
        shield=shield,
        relative_deadline=seconds,
    )


async def sleep_forever() -> NoReturn:
    """Pause execution of the current task forever (or until cancelled).

    Equivalent to calling ``await sleep(math.inf)``, except that if manually
    rescheduled this will raise a `RuntimeError`.

    Raises:
      RuntimeError: if rescheduled

    """
    await trio.lowlevel.wait_task_rescheduled(lambda _: trio.lowlevel.Abort.SUCCEEDED)
    raise RuntimeError("Should never have been rescheduled!")


async def sleep_until(deadline: float) -> None:
    """Pause execution of the current task until the given time.

    The difference between :func:`sleep` and :func:`sleep_until` is that the
    former takes a relative time and the latter takes an absolute time
    according to Trio's internal clock (as returned by :func:`current_time`).

    Args:
        deadline (float): The time at which we should wake up again. May be in
            the past, in which case this function executes a checkpoint but
            does not block.

    Raises:
      ValueError: if deadline is NaN.

    """
    with move_on_at(deadline):
        await sleep_forever()


async def sleep(seconds: float) -> None:
    """Pause execution of the current task for the given number of seconds.

    Args:
        seconds (float): The number of seconds to sleep. May be zero to
            insert a checkpoint without actually blocking.

    Raises:
        ValueError: if *seconds* is negative or NaN.

    """
    if seconds < 0:
        raise ValueError("`seconds` must be non-negative")
    if seconds == 0:
        await trio.lowlevel.checkpoint()
    else:
        await sleep_until(trio.current_time() + seconds)


class TooSlowError(Exception):
    """Raised by :func:`fail_after` and :func:`fail_at` if the timeout
    expires.

    """


@contextmanager
def fail_at(
    deadline: float,
    *,
    shield: bool = False,
) -> Generator[trio.CancelScope, None, None]:
    """Creates a cancel scope with the given deadline, and raises an error if it
    is actually cancelled.

    This function and :func:`move_on_at` are similar in that both create a
    cancel scope with a given absolute deadline, and if the deadline expires
    then both will cause :exc:`Cancelled` to be raised within the scope. The
    difference is that when the :exc:`Cancelled` exception reaches
    :func:`move_on_at`, it's caught and discarded. When it reaches
    :func:`fail_at`, then it's caught and :exc:`TooSlowError` is raised in its
    place.

    Args:
      deadline (float): The deadline.
      shield (bool): Initial value for the `~trio.CancelScope.shield` attribute
          of the newly created cancel scope.

    Raises:
      TooSlowError: if a :exc:`Cancelled` exception is raised in this scope
        and caught by the context manager.
      ValueError: if deadline is NaN.

    """
    with move_on_at(deadline, shield=shield) as scope:
        yield scope
    if scope.cancelled_caught:
        raise TooSlowError


@contextmanager
def fail_after(
    seconds: float,
    *,
    shield: bool = False,
) -> Generator[trio.CancelScope, None, None]:
    """Creates a cancel scope with the given timeout, and raises an error if
    it is actually cancelled.

    This function and :func:`move_on_after` are similar in that both create a
    cancel scope with a given timeout, and if the timeout expires then both
    will cause :exc:`Cancelled` to be raised within the scope. The difference
    is that when the :exc:`Cancelled` exception reaches :func:`move_on_after`,
    it's caught and discarded. When it reaches :func:`fail_after`, then it's
    caught and :exc:`TooSlowError` is raised in its place.

    The deadline of the cancel scope is calculated upon entering.

    Args:
      seconds (float): The timeout.
      shield (bool): Initial value for the `~trio.CancelScope.shield` attribute
          of the newly created cancel scope.

    Raises:
      TooSlowError: if a :exc:`Cancelled` exception is raised in this scope
        and caught by the context manager.
      ValueError: if *seconds* is less than zero or NaN.

    """
    with move_on_after(seconds, shield=shield) as scope:
        yield scope
    if scope.cancelled_caught:
        raise TooSlowError


# Users don't need to know that fail_at & fail_after wraps move_on_at and move_on_after
# and there is no functional difference. So we replace the return value when generating
# documentation.
if "sphinx" in sys.modules:  # pragma: no cover
    import inspect

    for c in (fail_at, fail_after):
        c.__signature__ = inspect.Signature.from_callable(c).replace(return_annotation=trio.CancelScope)  # type: ignore[union-attr]

# === NexusCore/openenv\Lib\site-packages\google\protobuf\symbol_database.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""A database of Python protocol buffer generated symbols.

SymbolDatabase is the MessageFactory for messages generated at compile time,
and makes it easy to create new instances of a registered type, given only the
type's protocol buffer symbol name.

Example usage::

  db = symbol_database.SymbolDatabase()

  # Register symbols of interest, from one or multiple files.
  db.RegisterFileDescriptor(my_proto_pb2.DESCRIPTOR)
  db.RegisterMessage(my_proto_pb2.MyMessage)
  db.RegisterEnumDescriptor(my_proto_pb2.MyEnum.DESCRIPTOR)

  # The database can be used as a MessageFactory, to generate types based on
  # their name:
  types = db.GetMessages(['my_proto.proto'])
  my_message_instance = types['MyMessage']()

  # The database's underlying descriptor pool can be queried, so it's not
  # necessary to know a type's filename to be able to generate it:
  filename = db.pool.FindFileContainingSymbol('MyMessage')
  my_message_instance = db.GetMessages([filename])['MyMessage']()

  # This functionality is also provided directly via a convenience method:
  my_message_instance = db.GetSymbol('MyMessage')()
"""

import warnings

from google.protobuf.internal import api_implementation
from google.protobuf import descriptor_pool
from google.protobuf import message_factory


class SymbolDatabase():
  """A database of Python generated symbols."""

  # local cache of registered classes.
  _classes = {}

  def __init__(self, pool=None):
    """Initializes a new SymbolDatabase."""
    self.pool = pool or descriptor_pool.DescriptorPool()

  def GetPrototype(self, descriptor):
    warnings.warn('SymbolDatabase.GetPrototype() is deprecated. Please '
                  'use message_factory.GetMessageClass() instead. '
                  'SymbolDatabase.GetPrototype() will be removed soon.')
    return message_factory.GetMessageClass(descriptor)

  def CreatePrototype(self, descriptor):
    warnings.warn('Directly call CreatePrototype() is wrong. Please use '
                  'message_factory.GetMessageClass() instead. '
                  'SymbolDatabase.CreatePrototype() will be removed soon.')
    return message_factory._InternalCreateMessageClass(descriptor)

  def GetMessages(self, files):
    warnings.warn('SymbolDatabase.GetMessages() is deprecated. Please use '
                  'message_factory.GetMessageClassedForFiles() instead. '
                  'SymbolDatabase.GetMessages() will be removed soon.')
    return message_factory.GetMessageClassedForFiles(files, self.pool)

  def RegisterMessage(self, message):
    """Registers the given message type in the local database.

    Calls to GetSymbol() and GetMessages() will return messages registered here.

    Args:
      message: A :class:`google.protobuf.message.Message` subclass (or
        instance); its descriptor will be registered.

    Returns:
      The provided message.
    """

    desc = message.DESCRIPTOR
    self._classes[desc] = message
    self.RegisterMessageDescriptor(desc)
    return message

  def RegisterMessageDescriptor(self, message_descriptor):
    """Registers the given message descriptor in the local database.

    Args:
      message_descriptor (Descriptor): the message descriptor to add.
    """
    if api_implementation.Type() == 'python':
      # pylint: disable=protected-access
      self.pool._AddDescriptor(message_descriptor)

  def RegisterEnumDescriptor(self, enum_descriptor):
    """Registers the given enum descriptor in the local database.

    Args:
      enum_descriptor (EnumDescriptor): The enum descriptor to register.

    Returns:
      EnumDescriptor: The provided descriptor.
    """
    if api_implementation.Type() == 'python':
      # pylint: disable=protected-access
      self.pool._AddEnumDescriptor(enum_descriptor)
    return enum_descriptor

  def RegisterServiceDescriptor(self, service_descriptor):
    """Registers the given service descriptor in the local database.

    Args:
      service_descriptor (ServiceDescriptor): the service descriptor to
        register.
    """
    if api_implementation.Type() == 'python':
      # pylint: disable=protected-access
      self.pool._AddServiceDescriptor(service_descriptor)

  def RegisterFileDescriptor(self, file_descriptor):
    """Registers the given file descriptor in the local database.

    Args:
      file_descriptor (FileDescriptor): The file descriptor to register.
    """
    if api_implementation.Type() == 'python':
      # pylint: disable=protected-access
      self.pool._InternalAddFileDescriptor(file_descriptor)

  def GetSymbol(self, symbol):
    """Tries to find a symbol in the local database.

    Currently, this method only returns message.Message instances, however, if
    may be extended in future to support other symbol types.

    Args:
      symbol (str): a protocol buffer symbol.

    Returns:
      A Python class corresponding to the symbol.

    Raises:
      KeyError: if the symbol could not be found.
    """

    return self._classes[self.pool.FindMessageTypeByName(symbol)]

  def GetMessages(self, files):
    # TODO: Fix the differences with MessageFactory.
    """Gets all registered messages from a specified file.

    Only messages already created and registered will be returned; (this is the
    case for imported _pb2 modules)
    But unlike MessageFactory, this version also returns already defined nested
    messages, but does not register any message extensions.

    Args:
      files (list[str]): The file names to extract messages from.

    Returns:
      A dictionary mapping proto names to the message classes.

    Raises:
      KeyError: if a file could not be found.
    """

    def _GetAllMessages(desc):
      """Walk a message Descriptor and recursively yields all message names."""
      yield desc
      for msg_desc in desc.nested_types:
        for nested_desc in _GetAllMessages(msg_desc):
          yield nested_desc

    result = {}
    for file_name in files:
      file_desc = self.pool.FindFileByName(file_name)
      for msg_desc in file_desc.message_types_by_name.values():
        for desc in _GetAllMessages(msg_desc):
          try:
            result[desc.full_name] = self._classes[desc]
          except KeyError:
            # This descriptor has no registered class, skip it.
            pass
    return result


_DEFAULT = SymbolDatabase(pool=descriptor_pool.Default())


def Default():
  """Returns the default SymbolDatabase."""
  return _DEFAULT

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\discuss_service\transports\base.py ===
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
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta2 import gapic_version as package_version
from google.ai.generativelanguage_v1beta2.types import discuss_service

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class DiscussServiceTransport(abc.ABC):
    """Abstract transport class for DiscussService."""

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
            self.generate_message: gapic_v1.method.wrap_method(
                self.generate_message,
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
            self.count_message_tokens: gapic_v1.method.wrap_method(
                self.count_message_tokens,
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
        }

    def close(self):
        """Closes resources associated with the transport.

        .. warning::
             Only call this method if the transport is NOT shared
             with other clients - this may cause errors in other clients!
        """
        raise NotImplementedError()

    @property
    def generate_message(
        self,
    ) -> Callable[
        [discuss_service.GenerateMessageRequest],
        Union[
            discuss_service.GenerateMessageResponse,
            Awaitable[discuss_service.GenerateMessageResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def count_message_tokens(
        self,
    ) -> Callable[
        [discuss_service.CountMessageTokensRequest],
        Union[
            discuss_service.CountMessageTokensResponse,
            Awaitable[discuss_service.CountMessageTokensResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("DiscussServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\html2image\browsers\chrome.py ===
from .chromium import ChromiumHeadless
from .search_utils import get_command_origin, find_first_defined_env_var

import subprocess
import os
import shutil
import platform

ENV_VAR_LOOKUP_TOGGLE = 'HTML2IMAGE_TOGGLE_ENV_VAR_LOOKUP'

CHROME_EXECUTABLE_ENV_VAR_CANDIDATES = [
    'HTML2IMAGE_CHROME_BIN',
    'HTML2IMAGE_CHROME_EXE',
    'CHROME_BIN',
    'CHROME_EXE',
]

def _find_chrome(user_given_executable=None):
    """ Finds a Chrome executable.

    Search Chrome on a given path. If no path given,
    try to find Chrome or Chromium-browser on a Windows or Unix system.

    Parameters
    ----------
    - `user_given_executable`: str (optional)
        + A filepath leading to a Chrome/ Chromium executable
        + Or a filename found in the current working directory
        + Or a keyword that executes Chrome/ Chromium, ex:
            - 'chromium' on linux systems
            - 'chrome' on windows (if typing `start chrome` in a cmd works)

    Raises
    ------
    - `FileNotFoundError`
        + If a suitable chrome executable could not be found.

    Returns
    -------
    - str
        + Path of the chrome executable on the current machine.
    """

    # try to find a chrome bin/exe in ENV
    path_from_env = find_first_defined_env_var(
        env_var_list=CHROME_EXECUTABLE_ENV_VAR_CANDIDATES,
        toggle=ENV_VAR_LOOKUP_TOGGLE
    )

    if path_from_env:
        print(
            f'Found a potential chrome executable in the {path_from_env} '
            f'environment variable:\n{path_from_env}\n'
        )
        return path_from_env

    # if an executable is given, try to use it
    if user_given_executable is not None:

        # On Windows, we cannot "safely" validate that user_given_executable
        # seems to be a chrome executable, as we cannot run it with
        # the --version flag.
        # https://bugs.chromium.org/p/chromium/issues/detail?id=158372
        #
        # We thus do the "bare minimum" and check if user_given_executable
        # is a file, a filepath, or corresponds to a keyword that can be used
        # with the start command, like so: `start user_given_executable`
        if platform.system() == 'Windows':
            command_origin = get_command_origin(user_given_executable)
            if command_origin:
                return command_origin

            # cannot validate user_given_executable
            raise FileNotFoundError()

        # On a non-Windows OS, we can validate in a basic way that
        # user_given_executable leads to a Chrome / Chromium executable,
        # or is a command, using the --version flag
        else:
            try:
                if 'chrom' in subprocess.check_output(
                    [user_given_executable, '--version']
                ).decode('utf-8').lower():
                    return user_given_executable
            except Exception:
                pass

        # We got a user_given_executable but couldn't validate it
        raise FileNotFoundError(
            'Failed to find a seemingly valid chrome executable '
            'in the given path.'
        )

    # Executable not in ENV or given by the user, try to find it
    # Search for executable on a Windows OS
    if platform.system() == 'Windows':
        prefixes = [
            os.getenv('PROGRAMFILES(X86)'),
            os.getenv('PROGRAMFILES'),
            os.getenv('LOCALAPPDATA'),
        ]

        suffix = "Google\\Chrome\\Application\\chrome.exe"

        for prefix in prefixes:
            path_candidate = os.path.join(prefix, suffix)
            if os.path.isfile(path_candidate):
                return path_candidate

    # Search for executable on a Linux OS
    elif platform.system() == "Linux":

        chrome_commands = [
            'chromium',
            'chromium-browser',
            'chrome',
            'google-chrome',
            'google-chrome-stable'
        ]

        for chrome_command in chrome_commands:
            if shutil.which(chrome_command):
                # check the --version for "chrom" ?
                return chrome_command

        # snap seems to be a special case?
        # see https://stackoverflow.com/q/63375327/12182226

        try:
            version_result = subprocess.check_output(
                ["chromium-browser", "--version"]
            )
            if 'snap' in str(version_result):
                chrome_snap = (
                    '/snap/chromium/current/usr/lib/chromium-browser/chrome'
                )
                if os.path.isfile(chrome_snap):
                    return chrome_snap
        except Exception:
            pass

    # Search for executable on MacOS
    elif platform.system() == "Darwin":
        # MacOS system
        chrome_app = (
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        )

        try:
            version_result = subprocess.check_output(
                [chrome_app, "--version"]
            )
            if "Google Chrome" in str(version_result):
                return chrome_app
        except Exception:
            pass

    # Couldn't find an executable (or OS not in Windows, Linux or Mac)
    raise FileNotFoundError(
        'Could not find a Chrome executable on this '
        'machine, please specify it yourself.'
    )

class ChromeHeadless(ChromiumHeadless):
    """
        Chrome/Chromium browser wrapper.

        Parameters
        ----------
        - `executable` : str, optional
            + Path to a chrome executable.

        - `flags` : list of str
            + Flags to be used by the headless browser.
            + Default flags are :
                - '--default-background-color=00000000'
                - '--hide-scrollbars'
        - `print_command` : bool
            + Whether or not to print the command used to take a screenshot.
        - `disable_logging` : bool
            + Whether or not to disable Chrome's output.
        - `use_new_headless` : bool, optional
            + Whether or not to use the new headless mode.
            + By default, the old headless mode is used.
            + You can also keep the original behavior to backward compatibility by setting this to `None`.
    """

    def __init__(self, executable=None, flags=None, print_command=False, disable_logging=False, use_new_headless=None,):
        super().__init__(executable=executable, flags=flags, print_command=print_command, disable_logging=disable_logging, use_new_headless=use_new_headless)

    @property
    def executable(self):
        return self._executable

    @executable.setter
    def executable(self, value):
        self._executable = _find_chrome(value)

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\humanloop.py ===
"""
Humanloop integration

https://humanloop.com/
"""

from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union, cast

import httpx

import litellm
from litellm.caching import DualCache
from litellm.llms.custom_httpx.http_handler import _get_httpx_client
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import StandardCallbackDynamicParams

from .custom_logger import CustomLogger


class PromptManagementClient(TypedDict):
    prompt_id: str
    prompt_template: List[AllMessageValues]
    model: Optional[str]
    optional_params: Optional[Dict[str, Any]]


class HumanLoopPromptManager(DualCache):
    @property
    def integration_name(self):
        return "humanloop"

    def _get_prompt_from_id_cache(
        self, humanloop_prompt_id: str
    ) -> Optional[PromptManagementClient]:
        return cast(
            Optional[PromptManagementClient], self.get_cache(key=humanloop_prompt_id)
        )

    def _compile_prompt_helper(
        self, prompt_template: List[AllMessageValues], prompt_variables: Dict[str, Any]
    ) -> List[AllMessageValues]:
        """
        Helper function to compile the prompt by substituting variables in the template.

        Args:
            prompt_template: List[AllMessageValues]
            prompt_variables (dict): A dictionary of variables to substitute into the prompt template.

        Returns:
            list: A list of dictionaries with variables substituted.
        """
        compiled_prompts: List[AllMessageValues] = []

        for template in prompt_template:
            tc = template.get("content")
            if tc and isinstance(tc, str):
                formatted_template = tc.replace("{{", "{").replace("}}", "}")
                compiled_content = formatted_template.format(**prompt_variables)
                template["content"] = compiled_content
            compiled_prompts.append(template)

        return compiled_prompts

    def _get_prompt_from_id_api(
        self, humanloop_prompt_id: str, humanloop_api_key: str
    ) -> PromptManagementClient:
        client = _get_httpx_client()

        base_url = "https://api.humanloop.com/v5/prompts/{}".format(humanloop_prompt_id)

        response = client.get(
            url=base_url,
            headers={
                "X-Api-Key": humanloop_api_key,
                "Content-Type": "application/json",
            },
        )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise Exception(f"Error getting prompt from Humanloop: {e.response.text}")

        json_response = response.json()
        template_message = json_response["template"]
        if isinstance(template_message, dict):
            template_messages = [template_message]
        elif isinstance(template_message, list):
            template_messages = template_message
        else:
            raise ValueError(f"Invalid template message type: {type(template_message)}")
        template_model = json_response["model"]
        optional_params = {}
        for k, v in json_response.items():
            if k in litellm.OPENAI_CHAT_COMPLETION_PARAMS:
                optional_params[k] = v
        return PromptManagementClient(
            prompt_id=humanloop_prompt_id,
            prompt_template=cast(List[AllMessageValues], template_messages),
            model=template_model,
            optional_params=optional_params,
        )

    def _get_prompt_from_id(
        self, humanloop_prompt_id: str, humanloop_api_key: str
    ) -> PromptManagementClient:
        prompt = self._get_prompt_from_id_cache(humanloop_prompt_id)
        if prompt is None:
            prompt = self._get_prompt_from_id_api(
                humanloop_prompt_id, humanloop_api_key
            )
            self.set_cache(
                key=humanloop_prompt_id,
                value=prompt,
                ttl=litellm.HUMANLOOP_PROMPT_CACHE_TTL_SECONDS,
            )
        return prompt

    def compile_prompt(
        self,
        prompt_template: List[AllMessageValues],
        prompt_variables: Optional[dict],
    ) -> List[AllMessageValues]:
        compiled_prompt: Optional[Union[str, list]] = None

        if prompt_variables is None:
            prompt_variables = {}

        compiled_prompt = self._compile_prompt_helper(
            prompt_template=prompt_template,
            prompt_variables=prompt_variables,
        )

        return compiled_prompt

    def _get_model_from_prompt(
        self, prompt_management_client: PromptManagementClient, model: str
    ) -> str:
        if prompt_management_client["model"] is not None:
            return prompt_management_client["model"]
        else:
            return model.replace("{}/".format(self.integration_name), "")


prompt_manager = HumanLoopPromptManager()


class HumanloopLogger(CustomLogger):
    def get_chat_completion_prompt(
        self,
        model: str,
        messages: List[AllMessageValues],
        non_default_params: dict,
        prompt_id: Optional[str],
        prompt_variables: Optional[dict],
        dynamic_callback_params: StandardCallbackDynamicParams,
        prompt_label: Optional[str] = None,
    ) -> Tuple[str, List[AllMessageValues], dict,]:
        humanloop_api_key = dynamic_callback_params.get(
            "humanloop_api_key"
        ) or get_secret_str("HUMANLOOP_API_KEY")

        if prompt_id is None:
            raise ValueError("prompt_id is required for Humanloop integration")

        if humanloop_api_key is None:
            return super().get_chat_completion_prompt(
                model=model,
                messages=messages,
                non_default_params=non_default_params,
                prompt_id=prompt_id,
                prompt_variables=prompt_variables,
                dynamic_callback_params=dynamic_callback_params,
            )

        prompt_template = prompt_manager._get_prompt_from_id(
            humanloop_prompt_id=prompt_id, humanloop_api_key=humanloop_api_key
        )

        updated_messages = prompt_manager.compile_prompt(
            prompt_template=prompt_template["prompt_template"],
            prompt_variables=prompt_variables,
        )

        prompt_template_optional_params = prompt_template["optional_params"] or {}

        updated_non_default_params = {
            **non_default_params,
            **prompt_template_optional_params,
        }

        model = prompt_manager._get_model_from_prompt(
            prompt_management_client=prompt_template, model=model
        )

        return model, updated_messages, updated_non_default_params