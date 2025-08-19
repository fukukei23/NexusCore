
# === NexusCore/openenv\Lib\site-packages\selenium\common\exceptions.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Exceptions that may happen in all the webdriver code."""

from typing import Optional, Sequence

SUPPORT_MSG = "For documentation on this error, please visit:"
ERROR_URL = "https://www.selenium.dev/documentation/webdriver/troubleshooting/errors"


class WebDriverException(Exception):
    """Base webdriver exception."""

    def __init__(
        self, msg: Optional[str] = None, screen: Optional[str] = None, stacktrace: Optional[Sequence[str]] = None
    ) -> None:
        super().__init__()
        self.msg = msg
        self.screen = screen
        self.stacktrace = stacktrace

    def __str__(self) -> str:
        exception_msg = f"Message: {self.msg}\n"
        if self.screen:
            exception_msg += "Screenshot: available via screen\n"
        if self.stacktrace:
            stacktrace = "\n".join(self.stacktrace)
            exception_msg += f"Stacktrace:\n{stacktrace}"
        return exception_msg


class InvalidSwitchToTargetException(WebDriverException):
    """Thrown when frame or window target to be switched doesn't exist."""


class NoSuchFrameException(InvalidSwitchToTargetException):
    """Thrown when frame target to be switched doesn't exist."""


class NoSuchWindowException(InvalidSwitchToTargetException):
    """Thrown when window target to be switched doesn't exist.

    To find the current set of active window handles, you can get a list
    of the active window handles in the following way::

        print driver.window_handles
    """


class NoSuchElementException(WebDriverException):
    """Thrown when element could not be found.

    If you encounter this exception, you may want to check the following:
        * Check your selector used in your find_by...
        * Element may not yet be on the screen at the time of the find operation,
          (webpage is still loading) see selenium.webdriver.support.wait.WebDriverWait()
          for how to write a wait wrapper to wait for an element to appear.
    """

    def __init__(
        self, msg: Optional[str] = None, screen: Optional[str] = None, stacktrace: Optional[Sequence[str]] = None
    ) -> None:
        with_support = f"{msg}; {SUPPORT_MSG} {ERROR_URL}#no-such-element-exception"

        super().__init__(with_support, screen, stacktrace)


class NoSuchAttributeException(WebDriverException):
    """Thrown when the attribute of element could not be found.

    You may want to check if the attribute exists in the particular
    browser you are testing against.  Some browsers may have different
    property names for the same property.  (IE8's .innerText vs. Firefox
    .textContent)
    """


class NoSuchShadowRootException(WebDriverException):
    """Thrown when trying to access the shadow root of an element when it does
    not have a shadow root attached."""


class StaleElementReferenceException(WebDriverException):
    """Thrown when a reference to an element is now "stale".

    Stale means the element no longer appears on the DOM of the page.


    Possible causes of StaleElementReferenceException include, but not limited to:
        * You are no longer on the same page, or the page may have refreshed since the element
          was located.
        * The element may have been removed and re-added to the screen, since it was located.
          Such as an element being relocated.
          This can happen typically with a javascript framework when values are updated and the
          node is rebuilt.
        * Element may have been inside an iframe or another context which was refreshed.
    """

    def __init__(
        self, msg: Optional[str] = None, screen: Optional[str] = None, stacktrace: Optional[Sequence[str]] = None
    ) -> None:
        with_support = f"{msg}; {SUPPORT_MSG} {ERROR_URL}#stale-element-reference-exception"

        super().__init__(with_support, screen, stacktrace)


class InvalidElementStateException(WebDriverException):
    """Thrown when a command could not be completed because the element is in
    an invalid state.

    This can be caused by attempting to clear an element that isn't both
    editable and resettable.
    """


class UnexpectedAlertPresentException(WebDriverException):
    """Thrown when an unexpected alert has appeared.

    Usually raised when  an unexpected modal is blocking the webdriver
    from executing commands.
    """

    def __init__(
        self,
        msg: Optional[str] = None,
        screen: Optional[str] = None,
        stacktrace: Optional[Sequence[str]] = None,
        alert_text: Optional[str] = None,
    ) -> None:
        super().__init__(msg, screen, stacktrace)
        self.alert_text = alert_text

    def __str__(self) -> str:
        return f"Alert Text: {self.alert_text}\n{super().__str__()}"


class NoAlertPresentException(WebDriverException):
    """Thrown when switching to no presented alert.

    This can be caused by calling an operation on the Alert() class when
    an alert is not yet on the screen.
    """


class ElementNotVisibleException(InvalidElementStateException):
    """Thrown when an element is present on the DOM, but it is not visible, and
    so is not able to be interacted with.

    Most commonly encountered when trying to click or read text of an
    element that is hidden from view.
    """


class ElementNotInteractableException(InvalidElementStateException):
    """Thrown when an element is present in the DOM but interactions with that
    element will hit another element due to paint order."""


class ElementNotSelectableException(InvalidElementStateException):
    """Thrown when trying to select an unselectable element.

    For example, selecting a 'script' element.
    """


class InvalidCookieDomainException(WebDriverException):
    """Thrown when attempting to add a cookie under a different domain than the
    current URL."""


class UnableToSetCookieException(WebDriverException):
    """Thrown when a driver fails to set a cookie."""


class TimeoutException(WebDriverException):
    """Thrown when a command does not complete in enough time."""


class MoveTargetOutOfBoundsException(WebDriverException):
    """Thrown when the target provided to the `ActionsChains` move() method is
    invalid, i.e. out of document."""


class UnexpectedTagNameException(WebDriverException):
    """Thrown when a support class did not get an expected web element."""


class InvalidSelectorException(WebDriverException):
    """Thrown when the selector which is used to find an element does not
    return a WebElement.

    Currently this only happens when the selector is an xpath expression
    and it is either syntactically invalid (i.e. it is not a xpath
    expression) or the expression does not select WebElements (e.g.
    "count(//input)").
    """

    def __init__(
        self, msg: Optional[str] = None, screen: Optional[str] = None, stacktrace: Optional[Sequence[str]] = None
    ) -> None:
        with_support = f"{msg}; {SUPPORT_MSG} {ERROR_URL}#invalid-selector-exception"

        super().__init__(with_support, screen, stacktrace)


class ImeNotAvailableException(WebDriverException):
    """Thrown when IME support is not available.

    This exception is thrown for every IME-related method call if IME
    support is not available on the machine.
    """


class ImeActivationFailedException(WebDriverException):
    """Thrown when activating an IME engine has failed."""


class InvalidArgumentException(WebDriverException):
    """The arguments passed to a command are either invalid or malformed."""


class JavascriptException(WebDriverException):
    """An error occurred while executing JavaScript supplied by the user."""


class NoSuchCookieException(WebDriverException):
    """No cookie matching the given path name was found amongst the associated
    cookies of the current browsing context's active document."""


class ScreenshotException(WebDriverException):
    """A screen capture was made impossible."""


class ElementClickInterceptedException(WebDriverException):
    """The Element Click command could not be completed because the element
    receiving the events is obscuring the element that was requested to be
    clicked."""


class InsecureCertificateException(WebDriverException):
    """Navigation caused the user agent to hit a certificate warning, which is
    usually the result of an expired or invalid TLS certificate."""


class InvalidCoordinatesException(WebDriverException):
    """The coordinates provided to an interaction's operation are invalid."""


class InvalidSessionIdException(WebDriverException):
    """Occurs if the given session id is not in the list of active sessions,
    meaning the session either does not exist or that it's not active."""


class SessionNotCreatedException(WebDriverException):
    """A new session could not be created."""


class UnknownMethodException(WebDriverException):
    """The requested command matched a known URL but did not match any methods
    for that URL."""


class NoSuchDriverException(WebDriverException):
    """Raised when driver is not specified and cannot be located."""

    def __init__(
        self, msg: Optional[str] = None, screen: Optional[str] = None, stacktrace: Optional[Sequence[str]] = None
    ) -> None:
        with_support = f"{msg}; {SUPPORT_MSG} {ERROR_URL}/driver_location"

        super().__init__(with_support, screen, stacktrace)


class DetachedShadowRootException(WebDriverException):
    """Raised when referenced shadow root is no longer attached to the DOM."""

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\setup_pydevd_cython.py ===
"""
A simpler setup version just to compile the speedup module.

It should be used as:

python setup_pydevd_cython build_ext --inplace

Note: the .c file and other generated files are regenerated from
the .pyx file by running "python build_tools/build.py"
"""

import os
import sys
from setuptools import setup

os.chdir(os.path.dirname(os.path.abspath(__file__)))

IS_PY36_OR_GREATER = sys.version_info[:2] >= (3, 6)
IS_PY311_ONWARDS = sys.version_info[:2] >= (3, 11)
IS_PY312_ONWARDS = sys.version_info[:2] >= (3, 12)


def process_args():
    extension_folder = None
    target_pydevd_name = None
    target_frame_eval = None
    force_cython = False

    for i, arg in enumerate(sys.argv[:]):
        if arg == "--build-lib":
            extension_folder = sys.argv[i + 1]
            # It shouldn't be removed from sys.argv (among with --build-temp) because they're passed further to setup()
        if arg.startswith("--target-pyd-name="):
            sys.argv.remove(arg)
            target_pydevd_name = arg[len("--target-pyd-name=") :]
        if arg.startswith("--target-pyd-frame-eval="):
            sys.argv.remove(arg)
            target_frame_eval = arg[len("--target-pyd-frame-eval=") :]
        if arg == "--force-cython":
            sys.argv.remove(arg)
            force_cython = True

    return extension_folder, target_pydevd_name, target_frame_eval, force_cython


def process_template_lines(template_lines):
    # Create 2 versions of the template, one for Python 3.8 and another for Python 3.9
    for version in ("38", "39"):
        yield "### WARNING: GENERATED CODE, DO NOT EDIT!"
        yield "### WARNING: GENERATED CODE, DO NOT EDIT!"
        yield "### WARNING: GENERATED CODE, DO NOT EDIT!"

        for line in template_lines:
            if version == "38":
                line = line.replace(
                    "get_bytecode_while_frame_eval(PyFrameObject * frame_obj, int exc)",
                    "get_bytecode_while_frame_eval_38(PyFrameObject * frame_obj, int exc)",
                )
                line = line.replace("CALL_EvalFrameDefault", "CALL_EvalFrameDefault_38(frame_obj, exc)")
            else:  # 3.9
                line = line.replace(
                    "get_bytecode_while_frame_eval(PyFrameObject * frame_obj, int exc)",
                    "get_bytecode_while_frame_eval_39(PyThreadState* tstate, PyFrameObject * frame_obj, int exc)",
                )
                line = line.replace("CALL_EvalFrameDefault", "CALL_EvalFrameDefault_39(tstate, frame_obj, exc)")

            yield line

        yield "### WARNING: GENERATED CODE, DO NOT EDIT!"
        yield "### WARNING: GENERATED CODE, DO NOT EDIT!"
        yield "### WARNING: GENERATED CODE, DO NOT EDIT!"
        yield ""
        yield ""


def process_template_file(contents):
    ret = []
    template_lines = []

    append_to = ret
    for line in contents.splitlines(keepends=False):
        if line.strip() == "### TEMPLATE_START":
            append_to = template_lines
        elif line.strip() == "### TEMPLATE_END":
            append_to = ret
            for line in process_template_lines(template_lines):
                ret.append(line)
        else:
            append_to.append(line)

    return "\n".join(ret)


def build_extension(dir_name, extension_name, target_pydevd_name, force_cython, extended=False, has_pxd=False, template=False):
    pyx_file = os.path.join(os.path.dirname(__file__), dir_name, "%s.pyx" % (extension_name,))

    if template:
        pyx_template_file = os.path.join(os.path.dirname(__file__), dir_name, "%s.template.pyx" % (extension_name,))
        with open(pyx_template_file, "r") as stream:
            contents = stream.read()

        contents = process_template_file(contents)

        with open(pyx_file, "w") as stream:
            stream.write(contents)

    if target_pydevd_name != extension_name:
        # It MUST be there in this case!
        # (otherwise we'll have unresolved externals because the .c file had another name initially).
        import shutil

        # We must force cython in this case (but only in this case -- for the regular setup in the user machine, we
        # should always compile the .c file).
        force_cython = True

        new_pyx_file = os.path.join(os.path.dirname(__file__), dir_name, "%s.pyx" % (target_pydevd_name,))
        new_c_file = os.path.join(os.path.dirname(__file__), dir_name, "%s.c" % (target_pydevd_name,))
        shutil.copy(pyx_file, new_pyx_file)
        pyx_file = new_pyx_file
        if has_pxd:
            pxd_file = os.path.join(os.path.dirname(__file__), dir_name, "%s.pxd" % (extension_name,))
            new_pxd_file = os.path.join(os.path.dirname(__file__), dir_name, "%s.pxd" % (target_pydevd_name,))
            shutil.copy(pxd_file, new_pxd_file)
        assert os.path.exists(pyx_file)

    try:
        c_files = [
            os.path.join(dir_name, "%s.c" % target_pydevd_name),
        ]
        if force_cython:
            for c_file in c_files:
                try:
                    os.remove(c_file)
                except:
                    pass
            from Cython.Build import cythonize  # @UnusedImport
            # Generate the .c files in cythonize (will not compile at this point).

            target = "%s/%s.pyx" % (
                dir_name,
                target_pydevd_name,
            )
            cythonize([target])

            # Workarounds needed in CPython 3.8 and 3.9 to access PyInterpreterState.eval_frame.
            for c_file in c_files:
                with open(c_file, "r") as stream:
                    c_file_contents = stream.read()

                if '#include "internal/pycore_gc.h"' not in c_file_contents:
                    c_file_contents = c_file_contents.replace(
                        '#include "Python.h"',
                        """#include "Python.h"
#if PY_VERSION_HEX >= 0x03090000
#include "internal/pycore_gc.h"
#include "internal/pycore_interp.h"
#endif
""",
                    )

                if '#include "internal/pycore_pystate.h"' not in c_file_contents:
                    c_file_contents = c_file_contents.replace(
                        '#include "pystate.h"',
                        """#include "pystate.h"
#if PY_VERSION_HEX >= 0x03080000
#include "internal/pycore_pystate.h"
#endif
""",
                    )

                # We want the same output on Windows and Linux.
                c_file_contents = c_file_contents.replace("\r\n", "\n").replace("\r", "\n")
                c_file_contents = c_file_contents.replace(r"_pydevd_frame_eval\\release_mem.h", "_pydevd_frame_eval/release_mem.h")
                c_file_contents = c_file_contents.replace(
                    r"_pydevd_frame_eval\\pydevd_frame_evaluator.pyx", "_pydevd_frame_eval/pydevd_frame_evaluator.pyx"
                )
                c_file_contents = c_file_contents.replace(r"_pydevd_bundle\\pydevd_cython.pxd", "_pydevd_bundle/pydevd_cython.pxd")
                c_file_contents = c_file_contents.replace(r"_pydevd_bundle\\pydevd_cython.pyx", "_pydevd_bundle/pydevd_cython.pyx")

                with open(c_file, "w") as stream:
                    stream.write(c_file_contents)

        # Always compile the .c (and not the .pyx) file (which we should keep up-to-date by running build_tools/build.py).
        from distutils.extension import Extension

        extra_compile_args = []
        extra_link_args = []

        if "linux" in sys.platform:
            # Enabling -flto brings executable from 4MB to 0.56MB and -Os to 0.41MB
            # Profiling shows an execution around 3-5% slower with -Os vs -O3,
            # so, kept only -flto.
            extra_compile_args = ["-flto", "-O3"]
            extra_link_args = extra_compile_args[:]

            # Note: also experimented with profile-guided optimization. The executable
            # size became a bit smaller (from 0.56MB to 0.5MB) but this would add an
            # extra step to run the debugger to obtain the optimizations
            # so, skipped it for now (note: the actual benchmarks time was in the
            # margin of a 0-1% improvement, which is probably not worth it for
            # speed increments).
            # extra_compile_args = ["-flto", "-fprofile-generate"]
            # ... Run benchmarks ...
            # extra_compile_args = ["-flto", "-fprofile-use", "-fprofile-correction"]
        elif "win32" in sys.platform:
            pass
            # uncomment to generate pdbs for visual studio.
            # extra_compile_args=["-Zi", "/Od"]
            # extra_link_args=["-debug"]
            extra_compile_args = ["/guard:cf"]
            extra_link_args = ["/guard:cf", "/DYNAMICBASE"]
            if IS_PY311_ONWARDS:
                # On py311 we need to add the CPython include folder to the include path.
                extra_compile_args.append("-I%s\\include\\CPython" % sys.exec_prefix)

        kwargs = {}
        if extra_link_args:
            kwargs["extra_link_args"] = extra_link_args
        if extra_compile_args:
            kwargs["extra_compile_args"] = extra_compile_args

        ext_modules = [
            Extension(
                "%s%s.%s"
                % (
                    dir_name,
                    "_ext" if extended else "",
                    target_pydevd_name,
                ),
                c_files,
                **kwargs,
            )
        ]

        # This is needed in CPython 3.8 to be able to include internal/pycore_pystate.h
        # (needed to set PyInterpreterState.eval_frame).
        for module in ext_modules:
            module.define_macros = [("Py_BUILD_CORE_MODULE", "1")]
        setup(name="Cythonize", ext_modules=ext_modules)
    finally:
        if target_pydevd_name != extension_name:
            try:
                os.remove(new_pyx_file)
            except:
                import traceback

                traceback.print_exc()
            try:
                os.remove(new_c_file)
            except:
                import traceback

                traceback.print_exc()
            if has_pxd:
                try:
                    os.remove(new_pxd_file)
                except:
                    import traceback

                    traceback.print_exc()


extension_folder, target_pydevd_name, target_frame_eval, force_cython = process_args()

FORCE_BUILD_ALL = os.environ.get("PYDEVD_FORCE_BUILD_ALL", "").lower() in ("true", "1")

extension_name = "pydevd_cython"
if target_pydevd_name is None:
    target_pydevd_name = extension_name
build_extension("_pydevd_bundle", extension_name, target_pydevd_name, force_cython, extension_folder, True)

if IS_PY36_OR_GREATER and not IS_PY311_ONWARDS or FORCE_BUILD_ALL:
    extension_name = "pydevd_frame_evaluator"
    if target_frame_eval is None:
        target_frame_eval = extension_name
    build_extension("_pydevd_frame_eval", extension_name, target_frame_eval, force_cython, extension_folder, True, template=True)

if IS_PY312_ONWARDS or FORCE_BUILD_ALL:
    extension_name = "_pydevd_sys_monitoring_cython"
    build_extension("_pydevd_sys_monitoring", extension_name, extension_name, force_cython, extension_folder, True)

if extension_folder:
    os.chdir(extension_folder)
    for folder in [
        file for file in os.listdir(extension_folder) if file != "build" and os.path.isdir(os.path.join(extension_folder, file))
    ]:
        file = os.path.join(folder, "__init__.py")
        if not os.path.exists(file):
            open(file, "a").close()

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_k_e_r_n.py ===
from fontTools.ttLib import getSearchRange
from fontTools.misc.textTools import safeEval, readHex
from fontTools.misc.fixedTools import fixedToFloat as fi2fl, floatToFixed as fl2fi
from . import DefaultTable
import struct
import sys
import array
import logging


log = logging.getLogger(__name__)


class table__k_e_r_n(DefaultTable.DefaultTable):
    """Kerning table

    The ``kern`` table contains values that contextually adjust the inter-glyph
    spacing for the glyphs in a ``glyf`` table.

    Note that similar contextual spacing adjustments can also be stored
    in the "kern" feature of a ``GPOS`` table.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/kern
    """

    def getkern(self, format):
        for subtable in self.kernTables:
            if subtable.format == format:
                return subtable
        return None  # not found

    def decompile(self, data, ttFont):
        version, nTables = struct.unpack(">HH", data[:4])
        apple = False
        if (len(data) >= 8) and (version == 1):
            # AAT Apple's "new" format. Hm.
            version, nTables = struct.unpack(">LL", data[:8])
            self.version = fi2fl(version, 16)
            data = data[8:]
            apple = True
        else:
            self.version = version
            data = data[4:]
        self.kernTables = []
        for i in range(nTables):
            if self.version == 1.0:
                # Apple
                length, coverage, subtableFormat = struct.unpack(">LBB", data[:6])
            else:
                # in OpenType spec the "version" field refers to the common
                # subtable header; the actual subtable format is stored in
                # the 8-15 mask bits of "coverage" field.
                # This "version" is always 0 so we ignore it here
                _, length, subtableFormat, coverage = struct.unpack(">HHBB", data[:6])
                if nTables == 1 and subtableFormat == 0:
                    # The "length" value is ignored since some fonts
                    # (like OpenSans and Calibri) have a subtable larger than
                    # its value.
                    (nPairs,) = struct.unpack(">H", data[6:8])
                    calculated_length = (nPairs * 6) + 14
                    if length != calculated_length:
                        log.warning(
                            "'kern' subtable longer than defined: "
                            "%d bytes instead of %d bytes" % (calculated_length, length)
                        )
                    length = calculated_length
            if subtableFormat not in kern_classes:
                subtable = KernTable_format_unkown(subtableFormat)
            else:
                subtable = kern_classes[subtableFormat](apple)
            subtable.decompile(data[:length], ttFont)
            self.kernTables.append(subtable)
            data = data[length:]

    def compile(self, ttFont):
        if hasattr(self, "kernTables"):
            nTables = len(self.kernTables)
        else:
            nTables = 0
        if self.version == 1.0:
            # AAT Apple's "new" format.
            data = struct.pack(">LL", fl2fi(self.version, 16), nTables)
        else:
            data = struct.pack(">HH", self.version, nTables)
        if hasattr(self, "kernTables"):
            for subtable in self.kernTables:
                data = data + subtable.compile(ttFont)
        return data

    def toXML(self, writer, ttFont):
        writer.simpletag("version", value=self.version)
        writer.newline()
        for subtable in self.kernTables:
            subtable.toXML(writer, ttFont)

    def fromXML(self, name, attrs, content, ttFont):
        if name == "version":
            self.version = safeEval(attrs["value"])
            return
        if name != "kernsubtable":
            return
        if not hasattr(self, "kernTables"):
            self.kernTables = []
        format = safeEval(attrs["format"])
        if format not in kern_classes:
            subtable = KernTable_format_unkown(format)
        else:
            apple = self.version == 1.0
            subtable = kern_classes[format](apple)
        self.kernTables.append(subtable)
        subtable.fromXML(name, attrs, content, ttFont)


class KernTable_format_0(object):
    # 'version' is kept for backward compatibility
    version = format = 0

    def __init__(self, apple=False):
        self.apple = apple

    def decompile(self, data, ttFont):
        if not self.apple:
            version, length, subtableFormat, coverage = struct.unpack(">HHBB", data[:6])
            if version != 0:
                from fontTools.ttLib import TTLibError

                raise TTLibError("unsupported kern subtable version: %d" % version)
            tupleIndex = None
            # Should we also assert length == len(data)?
            data = data[6:]
        else:
            length, coverage, subtableFormat, tupleIndex = struct.unpack(
                ">LBBH", data[:8]
            )
            data = data[8:]
        assert self.format == subtableFormat, "unsupported format"
        self.coverage = coverage
        self.tupleIndex = tupleIndex

        self.kernTable = kernTable = {}

        nPairs, searchRange, entrySelector, rangeShift = struct.unpack(
            ">HHHH", data[:8]
        )
        data = data[8:]

        datas = array.array("H", data[: 6 * nPairs])
        if sys.byteorder != "big":
            datas.byteswap()
        it = iter(datas)
        glyphOrder = ttFont.getGlyphOrder()
        for k in range(nPairs):
            left, right, value = next(it), next(it), next(it)
            if value >= 32768:
                value -= 65536
            try:
                kernTable[(glyphOrder[left], glyphOrder[right])] = value
            except IndexError:
                # Slower, but will not throw an IndexError on an invalid
                # glyph id.
                kernTable[(ttFont.getGlyphName(left), ttFont.getGlyphName(right))] = (
                    value
                )
        if len(data) > 6 * nPairs + 4:  # Ignore up to 4 bytes excess
            log.warning(
                "excess data in 'kern' subtable: %d bytes", len(data) - 6 * nPairs
            )

    def compile(self, ttFont):
        nPairs = min(len(self.kernTable), 0xFFFF)
        searchRange, entrySelector, rangeShift = getSearchRange(nPairs, 6)
        searchRange &= 0xFFFF
        entrySelector = min(entrySelector, 0xFFFF)
        rangeShift = min(rangeShift, 0xFFFF)
        data = struct.pack(">HHHH", nPairs, searchRange, entrySelector, rangeShift)

        # yeehee! (I mean, turn names into indices)
        try:
            reverseOrder = ttFont.getReverseGlyphMap()
            kernTable = sorted(
                (reverseOrder[left], reverseOrder[right], value)
                for ((left, right), value) in self.kernTable.items()
            )
        except KeyError:
            # Slower, but will not throw KeyError on invalid glyph id.
            getGlyphID = ttFont.getGlyphID
            kernTable = sorted(
                (getGlyphID(left), getGlyphID(right), value)
                for ((left, right), value) in self.kernTable.items()
            )

        for left, right, value in kernTable:
            data = data + struct.pack(">HHh", left, right, value)

        if not self.apple:
            version = 0
            length = len(data) + 6
            if length >= 0x10000:
                log.warning(
                    '"kern" subtable overflow, '
                    "truncating length value while preserving pairs."
                )
                length &= 0xFFFF
            header = struct.pack(">HHBB", version, length, self.format, self.coverage)
        else:
            if self.tupleIndex is None:
                # sensible default when compiling a TTX from an old fonttools
                # or when inserting a Windows-style format 0 subtable into an
                # Apple version=1.0 kern table
                log.warning("'tupleIndex' is None; default to 0")
                self.tupleIndex = 0
            length = len(data) + 8
            header = struct.pack(
                ">LBBH", length, self.coverage, self.format, self.tupleIndex
            )
        return header + data

    def toXML(self, writer, ttFont):
        attrs = dict(coverage=self.coverage, format=self.format)
        if self.apple:
            if self.tupleIndex is None:
                log.warning("'tupleIndex' is None; default to 0")
                attrs["tupleIndex"] = 0
            else:
                attrs["tupleIndex"] = self.tupleIndex
        writer.begintag("kernsubtable", **attrs)
        writer.newline()
        items = sorted(self.kernTable.items())
        for (left, right), value in items:
            writer.simpletag("pair", [("l", left), ("r", right), ("v", value)])
            writer.newline()
        writer.endtag("kernsubtable")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        self.coverage = safeEval(attrs["coverage"])
        subtableFormat = safeEval(attrs["format"])
        if self.apple:
            if "tupleIndex" in attrs:
                self.tupleIndex = safeEval(attrs["tupleIndex"])
            else:
                # previous fontTools versions didn't export tupleIndex
                log.warning("Apple kern subtable is missing 'tupleIndex' attribute")
                self.tupleIndex = None
        else:
            self.tupleIndex = None
        assert subtableFormat == self.format, "unsupported format"
        if not hasattr(self, "kernTable"):
            self.kernTable = {}
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            self.kernTable[(attrs["l"], attrs["r"])] = safeEval(attrs["v"])

    def __getitem__(self, pair):
        return self.kernTable[pair]

    def __setitem__(self, pair, value):
        self.kernTable[pair] = value

    def __delitem__(self, pair):
        del self.kernTable[pair]


class KernTable_format_unkown(object):
    def __init__(self, format):
        self.format = format

    def decompile(self, data, ttFont):
        self.data = data

    def compile(self, ttFont):
        return self.data

    def toXML(self, writer, ttFont):
        writer.begintag("kernsubtable", format=self.format)
        writer.newline()
        writer.comment("unknown 'kern' subtable format")
        writer.newline()
        writer.dumphex(self.data)
        writer.endtag("kernsubtable")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        self.decompile(readHex(content), ttFont)


kern_classes = {0: KernTable_format_0}

# === NexusCore/openenv\Lib\site-packages\interpreter\core\llm\utils\convert_to_openai_messages.py ===
import base64
import io
import json
import sys

from PIL import Image


def convert_to_openai_messages(
    messages,
    function_calling=True,
    vision=False,
    shrink_images=True,
    interpreter=None,
):
    """
    Converts LMC messages into OpenAI messages
    """
    new_messages = []

    # if function_calling == False:
    #     prev_message = None
    #     for message in messages:
    #         if message.get("type") == "code":
    #             if prev_message and prev_message.get("role") == "assistant":
    #                 prev_message["content"] += "\n```" + message.get("format", "") + "\n" + message.get("content").strip("\n`") + "\n```"
    #             else:
    #                 message["type"] = "message"
    #                 message["content"] = "```" + message.get("format", "") + "\n" + message.get("content").strip("\n`") + "\n```"
    #         prev_message = message

    #     messages = [message for message in messages if message.get("type") != "code"]

    for message in messages:
        # Is this for thine eyes?
        if "recipient" in message and message["recipient"] != "assistant":
            continue

        new_message = {}

        if message["type"] == "message":
            new_message["role"] = message[
                "role"
            ]  # This should never be `computer`, right?

            if message["role"] == "user" and (
                message == [m for m in messages if m["role"] == "user"][-1]
                or interpreter.always_apply_user_message_template
            ):
                # Only add the template for the last message?
                new_message["content"] = interpreter.user_message_template.replace(
                    "{content}", message["content"]
                )
            else:
                new_message["content"] = message["content"]

        elif message["type"] == "code":
            new_message["role"] = "assistant"
            if function_calling:
                new_message["function_call"] = {
                    "name": "execute",
                    "arguments": json.dumps(
                        {"language": message["format"], "code": message["content"]}
                    ),
                    # parsed_arguments isn't actually an OpenAI thing, it's an OI thing.
                    # but it's soo useful!
                    # "parsed_arguments": {
                    #     "language": message["format"],
                    #     "code": message["content"],
                    # },
                }
                # Add empty content to avoid error "openai.error.InvalidRequestError: 'content' is a required property - 'messages.*'"
                # especially for the OpenAI service hosted on Azure
                new_message["content"] = ""
            else:
                new_message[
                    "content"
                ] = f"""```{message["format"]}\n{message["content"]}\n```"""

        elif message["type"] == "console" and message["format"] == "output":
            if function_calling:
                new_message["role"] = "function"
                new_message["name"] = "execute"
                if "content" not in message:
                    print("What is this??", content)
                if type(message["content"]) != str:
                    if interpreter.debug:
                        print("\n\n\nStrange chunk found:", message, "\n\n\n")
                    message["content"] = str(message["content"])
                if message["content"].strip() == "":
                    new_message[
                        "content"
                    ] = "No output"  # I think it's best to be explicit, but we should test this.
                else:
                    new_message["content"] = message["content"]

            else:
                # This should be experimented with.
                if interpreter.code_output_sender == "user":
                    if message["content"].strip() == "":
                        content = interpreter.empty_code_output_template
                    else:
                        content = interpreter.code_output_template.replace(
                            "{content}", message["content"]
                        )

                    new_message["role"] = "user"
                    new_message["content"] = content
                elif interpreter.code_output_sender == "assistant":
                    new_message["role"] = "assistant"
                    new_message["content"] = (
                        "\n```output\n" + message["content"] + "\n```"
                    )

        elif message["type"] == "image":
            if message.get("format") == "description":
                new_message["role"] = message["role"]
                new_message["content"] = message["content"]
            else:
                if vision == False:
                    # If no vision, we only support the format of "description"
                    continue

                if "base64" in message["format"]:
                    # Extract the extension from the format, default to 'png' if not specified
                    if "." in message["format"]:
                        extension = message["format"].split(".")[-1]
                    else:
                        extension = "png"

                    encoded_string = message["content"]

                elif message["format"] == "path":
                    # Convert to base64
                    image_path = message["content"]
                    extension = image_path.split(".")[-1]

                    with open(image_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode(
                            "utf-8"
                        )

                else:
                    # Probably would be better to move this to a validation pass
                    # Near core, through the whole messages object
                    if "format" not in message:
                        raise Exception("Format of the image is not specified.")
                    else:
                        raise Exception(
                            f"Unrecognized image format: {message['format']}"
                        )

                content = f"data:image/{extension};base64,{encoded_string}"

                if shrink_images:
                    # Shrink to less than 5mb

                    # Calculate size
                    content_size_bytes = sys.getsizeof(str(content))

                    # Convert the size to MB
                    content_size_mb = content_size_bytes / (1024 * 1024)

                    # If the content size is greater than 5 MB, resize the image
                    if content_size_mb > 5:
                        # Decode the base64 image
                        img_data = base64.b64decode(encoded_string)
                        img = Image.open(io.BytesIO(img_data))

                        # Run in a loop to make SURE it's less than 5mb
                        for _ in range(10):
                            # Calculate the scale factor needed to reduce the image size to 4.9 MB
                            scale_factor = (4.9 / content_size_mb) ** 0.5

                            # Calculate the new dimensions
                            new_width = int(img.width * scale_factor)
                            new_height = int(img.height * scale_factor)

                            # Resize the image
                            img = img.resize((new_width, new_height))

                            # Convert the image back to base64
                            buffered = io.BytesIO()
                            img.save(buffered, format=extension)
                            encoded_string = base64.b64encode(
                                buffered.getvalue()
                            ).decode("utf-8")

                            # Set the content
                            content = f"data:image/{extension};base64,{encoded_string}"

                            # Recalculate the size of the content in bytes
                            content_size_bytes = sys.getsizeof(str(content))

                            # Convert the size to MB
                            content_size_mb = content_size_bytes / (1024 * 1024)

                            if content_size_mb < 5:
                                break
                        else:
                            print(
                                "Attempted to shrink the image but failed. Sending to the LLM anyway."
                            )

                new_message = {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": content, "detail": "low"},
                        }
                    ],
                }

                if message["role"] == "computer":
                    new_message["content"].append(
                        {
                            "type": "text",
                            "text": "This image is the result of the last tool output. What does it mean / are we done?",
                        }
                    )
                if message.get("format") == "path":
                    if any(
                        content.get("type") == "text"
                        for content in new_message["content"]
                    ):
                        for content in new_message["content"]:
                            if content.get("type") == "text":
                                content["text"] += (
                                    "\nThis image is at this path: "
                                    + message["content"]
                                )
                    else:
                        new_message["content"].append(
                            {
                                "type": "text",
                                "text": "This image is at this path: "
                                + message["content"],
                            }
                        )

        elif message["type"] == "file":
            new_message = {"role": "user", "content": message["content"]}
        elif message["type"] == "error":
            print("Ignoring 'type' == 'error' messages.")
            continue
        else:
            raise Exception(f"Unable to convert this message type: {message}")

        if isinstance(new_message["content"], str):
            new_message["content"] = new_message["content"].strip()

        new_messages.append(new_message)

    if function_calling == False:
        combined_messages = []
        current_role = None
        current_content = []

        for message in new_messages:
            if isinstance(message["content"], str):
                if current_role is None:
                    current_role = message["role"]
                    current_content.append(message["content"])
                elif current_role == message["role"]:
                    current_content.append(message["content"])
                else:
                    combined_messages.append(
                        {"role": current_role, "content": "\n".join(current_content)}
                    )
                    current_role = message["role"]
                    current_content = [message["content"]]
            else:
                if current_content:
                    combined_messages.append(
                        {"role": current_role, "content": "\n".join(current_content)}
                    )
                    current_content = []
                combined_messages.append(message)

        # Add the last message
        if current_content:
            combined_messages.append(
                {"role": current_role, "content": " ".join(current_content)}
            )

        new_messages = combined_messages

    return new_messages

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\core.py ===
"""distutils.core

The only module that needs to be imported to use the Distutils; provides
the 'setup' function (which is to be called from the setup script).  Also
indirectly provides the Distribution and Command classes, although they are
really defined in distutils.dist and distutils.cmd.
"""

from __future__ import annotations

import os
import sys
import tokenize
from collections.abc import Iterable

from .cmd import Command
from .debug import DEBUG

# Mainly import these so setup scripts can "from distutils.core import" them.
from .dist import Distribution
from .errors import (
    CCompilerError,
    DistutilsArgError,
    DistutilsError,
    DistutilsSetupError,
)
from .extension import Extension

__all__ = ['Distribution', 'Command', 'Extension', 'setup']

# This is a barebones help message generated displayed when the user
# runs the setup script with no arguments at all.  More useful help
# is generated with various --help options: global help, list commands,
# and per-command help.
USAGE = """\
usage: %(script)s [global_opts] cmd1 [cmd1_opts] [cmd2 [cmd2_opts] ...]
   or: %(script)s --help [cmd1 cmd2 ...]
   or: %(script)s --help-commands
   or: %(script)s cmd --help
"""


def gen_usage(script_name):
    script = os.path.basename(script_name)
    return USAGE % locals()


# Some mild magic to control the behaviour of 'setup()' from 'run_setup()'.
_setup_stop_after = None
_setup_distribution = None

# Legal keyword arguments for the setup() function
setup_keywords = (
    'distclass',
    'script_name',
    'script_args',
    'options',
    'name',
    'version',
    'author',
    'author_email',
    'maintainer',
    'maintainer_email',
    'url',
    'license',
    'description',
    'long_description',
    'keywords',
    'platforms',
    'classifiers',
    'download_url',
    'requires',
    'provides',
    'obsoletes',
)

# Legal keyword arguments for the Extension constructor
extension_keywords = (
    'name',
    'sources',
    'include_dirs',
    'define_macros',
    'undef_macros',
    'library_dirs',
    'libraries',
    'runtime_library_dirs',
    'extra_objects',
    'extra_compile_args',
    'extra_link_args',
    'swig_opts',
    'export_symbols',
    'depends',
    'language',
)


def setup(**attrs):  # noqa: C901
    """The gateway to the Distutils: do everything your setup script needs
    to do, in a highly flexible and user-driven way.  Briefly: create a
    Distribution instance; find and parse config files; parse the command
    line; run each Distutils command found there, customized by the options
    supplied to 'setup()' (as keyword arguments), in config files, and on
    the command line.

    The Distribution instance might be an instance of a class supplied via
    the 'distclass' keyword argument to 'setup'; if no such class is
    supplied, then the Distribution class (in dist.py) is instantiated.
    All other arguments to 'setup' (except for 'cmdclass') are used to set
    attributes of the Distribution instance.

    The 'cmdclass' argument, if supplied, is a dictionary mapping command
    names to command classes.  Each command encountered on the command line
    will be turned into a command class, which is in turn instantiated; any
    class found in 'cmdclass' is used in place of the default, which is
    (for command 'foo_bar') class 'foo_bar' in module
    'distutils.command.foo_bar'.  The command class must provide a
    'user_options' attribute which is a list of option specifiers for
    'distutils.fancy_getopt'.  Any command-line options between the current
    and the next command are used to set attributes of the current command
    object.

    When the entire command-line has been successfully parsed, calls the
    'run()' method on each command object in turn.  This method will be
    driven entirely by the Distribution object (which each command object
    has a reference to, thanks to its constructor), and the
    command-specific options that became attributes of each command
    object.
    """

    global _setup_stop_after, _setup_distribution

    # Determine the distribution class -- either caller-supplied or
    # our Distribution (see below).
    klass = attrs.get('distclass')
    if klass:
        attrs.pop('distclass')
    else:
        klass = Distribution

    if 'script_name' not in attrs:
        attrs['script_name'] = os.path.basename(sys.argv[0])
    if 'script_args' not in attrs:
        attrs['script_args'] = sys.argv[1:]

    # Create the Distribution instance, using the remaining arguments
    # (ie. everything except distclass) to initialize it
    try:
        _setup_distribution = dist = klass(attrs)
    except DistutilsSetupError as msg:
        if 'name' not in attrs:
            raise SystemExit(f"error in setup command: {msg}")
        else:
            raise SystemExit("error in {} setup command: {}".format(attrs['name'], msg))

    if _setup_stop_after == "init":
        return dist

    # Find and parse the config file(s): they will override options from
    # the setup script, but be overridden by the command line.
    dist.parse_config_files()

    if DEBUG:
        print("options (after parsing config files):")
        dist.dump_option_dicts()

    if _setup_stop_after == "config":
        return dist

    # Parse the command line and override config files; any
    # command-line errors are the end user's fault, so turn them into
    # SystemExit to suppress tracebacks.
    try:
        ok = dist.parse_command_line()
    except DistutilsArgError as msg:
        raise SystemExit(gen_usage(dist.script_name) + f"\nerror: {msg}")

    if DEBUG:
        print("options (after parsing command line):")
        dist.dump_option_dicts()

    if _setup_stop_after == "commandline":
        return dist

    # And finally, run all the commands found on the command line.
    if ok:
        return run_commands(dist)

    return dist


# setup ()


def run_commands(dist):
    """Given a Distribution object run all the commands,
    raising ``SystemExit`` errors in the case of failure.

    This function assumes that either ``sys.argv`` or ``dist.script_args``
    is already set accordingly.
    """
    try:
        dist.run_commands()
    except KeyboardInterrupt:
        raise SystemExit("interrupted")
    except OSError as exc:
        if DEBUG:
            sys.stderr.write(f"error: {exc}\n")
            raise
        else:
            raise SystemExit(f"error: {exc}")

    except (DistutilsError, CCompilerError) as msg:
        if DEBUG:
            raise
        else:
            raise SystemExit("error: " + str(msg))

    return dist


def run_setup(script_name, script_args: Iterable[str] | None = None, stop_after="run"):
    """Run a setup script in a somewhat controlled environment, and
    return the Distribution instance that drives things.  This is useful
    if you need to find out the distribution meta-data (passed as
    keyword args from 'script' to 'setup()', or the contents of the
    config files or command-line.

    'script_name' is a file that will be read and run with 'exec()';
    'sys.argv[0]' will be replaced with 'script' for the duration of the
    call.  'script_args' is a list of strings; if supplied,
    'sys.argv[1:]' will be replaced by 'script_args' for the duration of
    the call.

    'stop_after' tells 'setup()' when to stop processing; possible
    values:
      init
        stop after the Distribution instance has been created and
        populated with the keyword arguments to 'setup()'
      config
        stop after config files have been parsed (and their data
        stored in the Distribution instance)
      commandline
        stop after the command-line ('sys.argv[1:]' or 'script_args')
        have been parsed (and the data stored in the Distribution)
      run [default]
        stop after all commands have been run (the same as if 'setup()'
        had been called in the usual way

    Returns the Distribution instance, which provides all information
    used to drive the Distutils.
    """
    if stop_after not in ('init', 'config', 'commandline', 'run'):
        raise ValueError(f"invalid value for 'stop_after': {stop_after!r}")

    global _setup_stop_after, _setup_distribution
    _setup_stop_after = stop_after

    save_argv = sys.argv.copy()
    g = {'__file__': script_name, '__name__': '__main__'}
    try:
        try:
            sys.argv[0] = script_name
            if script_args is not None:
                sys.argv[1:] = script_args
            # tokenize.open supports automatic encoding detection
            with tokenize.open(script_name) as f:
                code = f.read().replace(r'\r\n', r'\n')
                exec(code, g)
        finally:
            sys.argv = save_argv
            _setup_stop_after = None
    except SystemExit:
        # Hmm, should we do something if exiting with a non-zero code
        # (ie. error)?
        pass

    if _setup_distribution is None:
        raise RuntimeError(
            "'distutils.core.setup()' was never called -- "
            f"perhaps '{script_name}' is not a Distutils setup script?"
        )

    # I wonder if the setup script's namespace -- g and l -- would be of
    # any interest to callers?
    # print "_setup_distribution:", _setup_distribution
    return _setup_distribution


# run_setup ()

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_deprecate.py ===
from __future__ import annotations

import inspect
import warnings
from types import ModuleType

import pytest

from .._deprecate import (
    TrioDeprecationWarning,
    deprecated,
    deprecated_alias,
    warn_deprecated,
)
from . import module_with_deprecations


@pytest.fixture
def recwarn_always(recwarn: pytest.WarningsRecorder) -> pytest.WarningsRecorder:
    warnings.simplefilter("always")
    # ResourceWarnings about unclosed sockets can occur nondeterministically
    # (during GC) which throws off the tests in this file
    warnings.simplefilter("ignore", ResourceWarning)
    return recwarn


def _here() -> tuple[str, int]:
    frame = inspect.currentframe()
    assert frame is not None
    assert frame.f_back is not None
    info = inspect.getframeinfo(frame.f_back)
    return (info.filename, info.lineno)


def test_warn_deprecated(recwarn_always: pytest.WarningsRecorder) -> None:
    def deprecated_thing() -> None:
        warn_deprecated("ice", "1.2", issue=1, instead="water")

    deprecated_thing()
    filename, lineno = _here()
    assert len(recwarn_always) == 1
    got = recwarn_always.pop(DeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "ice is deprecated" in got.message.args[0]
    assert "Trio 1.2" in got.message.args[0]
    assert "water instead" in got.message.args[0]
    assert "/issues/1" in got.message.args[0]
    assert got.filename == filename
    assert got.lineno == lineno - 1


def test_warn_deprecated_no_instead_or_issue(
    recwarn_always: pytest.WarningsRecorder,
) -> None:
    # Explicitly no instead or issue
    warn_deprecated("water", "1.3", issue=None, instead=None)
    assert len(recwarn_always) == 1
    got = recwarn_always.pop(DeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "water is deprecated" in got.message.args[0]
    assert "no replacement" in got.message.args[0]
    assert "Trio 1.3" in got.message.args[0]


def test_warn_deprecated_stacklevel(recwarn_always: pytest.WarningsRecorder) -> None:
    def nested1() -> None:
        nested2()

    def nested2() -> None:
        warn_deprecated("x", "1.3", issue=7, instead="y", stacklevel=3)

    filename, lineno = _here()
    nested1()
    got = recwarn_always.pop(DeprecationWarning)
    assert got.filename == filename
    assert got.lineno == lineno + 1


def old() -> None:  # pragma: no cover
    pass


def new() -> None:  # pragma: no cover
    pass


def test_warn_deprecated_formatting(recwarn_always: pytest.WarningsRecorder) -> None:
    warn_deprecated(old, "1.0", issue=1, instead=new)
    got = recwarn_always.pop(DeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "test_deprecate.old is deprecated" in got.message.args[0]
    assert "test_deprecate.new instead" in got.message.args[0]


@deprecated("1.5", issue=123, instead=new)
def deprecated_old() -> int:
    return 3


def test_deprecated_decorator(recwarn_always: pytest.WarningsRecorder) -> None:
    assert deprecated_old() == 3
    got = recwarn_always.pop(DeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "test_deprecate.deprecated_old is deprecated" in got.message.args[0]
    assert "1.5" in got.message.args[0]
    assert "test_deprecate.new" in got.message.args[0]
    assert "issues/123" in got.message.args[0]


class Foo:
    @deprecated("1.0", issue=123, instead="crying")
    def method(self) -> int:
        return 7


def test_deprecated_decorator_method(recwarn_always: pytest.WarningsRecorder) -> None:
    f = Foo()
    assert f.method() == 7
    got = recwarn_always.pop(DeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "test_deprecate.Foo.method is deprecated" in got.message.args[0]


@deprecated("1.2", thing="the thing", issue=None, instead=None)
def deprecated_with_thing() -> int:
    return 72


def test_deprecated_decorator_with_explicit_thing(
    recwarn_always: pytest.WarningsRecorder,
) -> None:
    assert deprecated_with_thing() == 72
    got = recwarn_always.pop(DeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "the thing is deprecated" in got.message.args[0]


def new_hotness() -> str:
    return "new hotness"


old_hotness = deprecated_alias("old_hotness", new_hotness, "1.23", issue=1)


def test_deprecated_alias(recwarn_always: pytest.WarningsRecorder) -> None:
    assert old_hotness() == "new hotness"
    got = recwarn_always.pop(DeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "test_deprecate.old_hotness is deprecated" in got.message.args[0]
    assert "1.23" in got.message.args[0]
    assert "test_deprecate.new_hotness instead" in got.message.args[0]
    assert "issues/1" in got.message.args[0]

    assert isinstance(old_hotness.__doc__, str)
    assert ".. deprecated:: 1.23" in old_hotness.__doc__
    assert "test_deprecate.new_hotness instead" in old_hotness.__doc__
    assert "issues/1>`__" in old_hotness.__doc__


class Alias:
    def new_hotness_method(self) -> str:
        return "new hotness method"

    old_hotness_method = deprecated_alias(
        "Alias.old_hotness_method",
        new_hotness_method,
        "3.21",
        issue=1,
    )


def test_deprecated_alias_method(recwarn_always: pytest.WarningsRecorder) -> None:
    obj = Alias()
    assert obj.old_hotness_method() == "new hotness method"
    got = recwarn_always.pop(DeprecationWarning)
    assert isinstance(got.message, Warning)
    msg = got.message.args[0]
    assert "test_deprecate.Alias.old_hotness_method is deprecated" in msg
    assert "test_deprecate.Alias.new_hotness_method instead" in msg


@deprecated("2.1", issue=1, instead="hi")
def docstring_test1() -> None:  # pragma: no cover
    """Hello!"""


@deprecated("2.1", issue=None, instead="hi")
def docstring_test2() -> None:  # pragma: no cover
    """Hello!"""


@deprecated("2.1", issue=1, instead=None)
def docstring_test3() -> None:  # pragma: no cover
    """Hello!"""


@deprecated("2.1", issue=None, instead=None)
def docstring_test4() -> None:  # pragma: no cover
    """Hello!"""


def test_deprecated_docstring_munging() -> None:
    assert (
        docstring_test1.__doc__
        == """Hello!

.. deprecated:: 2.1
   Use hi instead.
   For details, see `issue #1 <https://github.com/python-trio/trio/issues/1>`__.

"""
    )

    assert (
        docstring_test2.__doc__
        == """Hello!

.. deprecated:: 2.1
   Use hi instead.

"""
    )

    assert (
        docstring_test3.__doc__
        == """Hello!

.. deprecated:: 2.1
   For details, see `issue #1 <https://github.com/python-trio/trio/issues/1>`__.

"""
    )

    assert (
        docstring_test4.__doc__
        == """Hello!

.. deprecated:: 2.1

"""
    )


def test_module_with_deprecations(recwarn_always: pytest.WarningsRecorder) -> None:
    assert module_with_deprecations.regular == "hi"
    assert len(recwarn_always) == 0

    assert type(module_with_deprecations) is ModuleType

    filename, lineno = _here()
    assert module_with_deprecations.dep1 == "value1"  # type: ignore[attr-defined]
    got = recwarn_always.pop(DeprecationWarning)
    assert isinstance(got.message, Warning)
    assert got.filename == filename
    assert got.lineno == lineno + 1

    assert "module_with_deprecations.dep1" in got.message.args[0]
    assert "Trio 1.1" in got.message.args[0]
    assert "/issues/1" in got.message.args[0]
    assert "value1 instead" in got.message.args[0]

    assert module_with_deprecations.dep2 == "value2"  # type: ignore[attr-defined]
    got = recwarn_always.pop(DeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "instead-string instead" in got.message.args[0]

    with pytest.raises(AttributeError):
        module_with_deprecations.asdf  # type: ignore[attr-defined]  # noqa: B018  # "useless expression"


def test_warning_class() -> None:
    with pytest.deprecated_call():
        warn_deprecated("foo", "bar", issue=None, instead=None)

    # essentially the same as the above check
    with pytest.warns(
        DeprecationWarning,
        match="^foo is deprecated since Trio bar with no replacement$",
    ):
        warn_deprecated("foo", "bar", issue=None, instead=None)

    with pytest.warns(TrioDeprecationWarning):
        warn_deprecated(
            "foo",
            "bar",
            issue=None,
            instead=None,
            use_triodeprecationwarning=True,
        )

# === NexusCore/evaluation\evalplus\evalplus\eval\__init__.py ===
# The MIT License
#
# Copyright (c) OpenAI (https://openai.com)
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

import itertools
import multiprocessing
import os
import time
from multiprocessing import Array, Value
from typing import Any, Dict, List, Tuple, Union

import numpy as np

from evalplus.eval._special_oracle import (
    MBPP_OUTPUT_NOT_NONE_TASKS,
    MBPP_OUTPUT_SET_EQ_TASKS,
    _poly,
)
from evalplus.eval.utils import (
    create_tempdir,
    reliability_guard,
    swallow_io,
    time_limit,
)


def compatible_eval_result(results: Dict) -> Dict:
    # compatibility
    for task_results in results["eval"].values():
        # update the "files" field to "nfiles"
        if "files" in task_results and "nfiles" not in task_results:
            task_results["nfiles"] = len(task_results.pop("files"))
    return results


# unbiased estimator from https://github.com/openai/human-eval
def estimate_pass_at_k(
    num_samples: Union[int, List[int], np.ndarray],
    num_correct: Union[List[int], np.ndarray],
    k: int,
) -> np.ndarray:
    """
    Estimates pass@k of each problem and returns them in an array.
    """

    def estimator(n: int, c: int, k: int) -> float:
        """
        Calculates 1 - comb(n - c, k) / comb(n, k).
        """
        if n - c < k:
            return 1.0
        return 1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))

    if isinstance(num_samples, int):
        num_samples_it = itertools.repeat(num_samples, len(num_correct))
    else:
        assert len(num_samples) == len(num_correct)
        num_samples_it = iter(num_samples)

    return np.array(
        [estimator(int(n), int(c), k) for n, c in zip(num_samples_it, num_correct)]
    )


PASS = "pass"
FAIL = "fail"
TIMEOUT = "timeout"

_SUCCESS = 0
_FAILED = 1
_TIMEOUT = 2
_UNKNOWN = 3

_mapping = {_SUCCESS: PASS, _FAILED: FAIL, _TIMEOUT: TIMEOUT, _UNKNOWN: None}


def is_floats(x) -> bool:
    # check if it is float; List[float]; Tuple[float]
    if isinstance(x, float):
        return True
    if isinstance(x, (list, tuple)):
        return all(isinstance(i, float) for i in x)
    if isinstance(x, np.ndarray):
        return x.dtype == np.float64 or x.dtype == np.float32
    return False


def unsafe_execute(
    dataset: str,
    entry_point: str,
    code: str,
    inputs,
    expected: List,
    time_limits,
    atol,
    fast_check,
    stat,  # Value
    details,  # Array
    progress,  # Value
):
    with create_tempdir():
        # These system calls are needed when cleaning up tempdir.
        import os
        import shutil

        rmtree = shutil.rmtree
        rmdir = os.rmdir
        chdir = os.chdir
        # Disable functionalities that can make destructive changes to the test.
        # allow only 4GB memory usage
        maximum_memory_bytes = 4 * 1024 * 1024 * 1024
        reliability_guard(maximum_memory_bytes=maximum_memory_bytes)
        exec_globals = {}
        try:
            with swallow_io():
                exec(code, exec_globals)
                fn = exec_globals[entry_point]

            for i, inp in enumerate(inputs):
                try:
                    with time_limit(time_limits[i]):
                        with swallow_io():
                            out = fn(*inp)

                    exp = expected[i]
                    exact_match = out == exp

                    # ================================================ #
                    # ============== special oracles ================= #
                    if dataset == "mbpp":
                        if "are_equivalent" == entry_point:  # Mbpp/164 special oracle
                            exact_match = exact_match or True
                        elif "sum_div" == entry_point:  # Mbpp/295 special oracle
                            exact_match = exact_match or out == 0
                        elif entry_point in MBPP_OUTPUT_SET_EQ_TASKS:
                            exact_match = set(out) == set(exp)
                        elif entry_point in MBPP_OUTPUT_NOT_NONE_TASKS:
                            # exp is True  if not None
                            #        False if None
                            if isinstance(out, bool):
                                exact_match = out == exp
                            else:
                                exact_match = exp == (out is not None)

                    if dataset == "humaneval":
                        if "find_zero" == entry_point:
                            assert _poly(*inp, out) <= atol
                    # ============== special oracles ================= #
                    # ================================================ #

                    if atol == 0 and is_floats(exp):
                        atol = 1e-6  # enforce atol for float comparison
                    if not exact_match and atol != 0:
                        # explicitly set rtol=1e-07
                        # to match `np.testing.assert_allclose`'s default values
                        assert np.allclose(out, exp, rtol=1e-07, atol=atol)
                    else:
                        assert exact_match
                except BaseException:
                    if fast_check:
                        raise

                    details[i] = False
                    progress.value += 1
                    continue

                details[i] = True
                progress.value += 1

            stat.value = _SUCCESS
        except BaseException:
            stat.value = _FAILED
        # Needed for cleaning up.
        shutil.rmtree = rmtree
        os.rmdir = rmdir
        os.chdir = chdir


def untrusted_check(
    dataset: str,
    code: str,
    inputs: List[Any],
    entry_point: str,
    expected,
    atol,
    ref_time: List[float],
    fast_check: bool = False,
    min_time_limit: float = 0.1,
    gt_time_limit_factor: float = 2.0,
) -> Tuple[str, np.ndarray]:
    time_limits = [max(min_time_limit, gt_time_limit_factor * t) for t in ref_time]
    timeout = min(os.getenv("EVALPLUS_TIMEOUT_PER_TASK", 60), sum(time_limits)) + 1
    if not fast_check:
        timeout += 1  # extra time for data collection

    # shared memory objects
    progress = Value("i", 0)
    stat = Value("i", _UNKNOWN)
    details = Array("b", [False for _ in range(len(inputs))])

    p = multiprocessing.Process(
        target=unsafe_execute,
        args=(
            dataset,
            entry_point,
            code,
            inputs,
            expected,
            time_limits,
            atol,
            fast_check,
            # return values
            stat,
            details,
            progress,
        ),
    )
    p.start()
    p.join(timeout=timeout + 1)
    if p.is_alive():
        p.terminate()
        time.sleep(0.1)
    if p.is_alive():
        p.kill()
        time.sleep(0.1)

    stat = _mapping[stat.value]
    details = details[: progress.value]

    if not stat:
        stat = TIMEOUT

    if stat == PASS:
        if len(details) != len(inputs) or not all(details):
            stat = FAIL

    return stat, details


def evaluate_files(
    dataset: str,
    files: List[str],
    inputs: List,
    expected: List,
    entry_point: str,
    atol: float,
    ref_time: List[float],
    fast_check: bool = False,
    min_time_limit: float = 0.1,
    gt_time_limit_factor: float = 2.0,
) -> List[Tuple[str, List[bool]]]:
    ret = []
    # sort files by the id in name (i.e., "../n.py")
    files = sorted(files, key=lambda x: int(x.split("/")[-1].split(".")[0]))
    for file in files:
        code = open(file, "r").read()
        stat, det = untrusted_check(
            dataset,
            code,
            inputs,
            entry_point,
            expected=expected,
            atol=atol,
            ref_time=ref_time,
            fast_check=fast_check,
            min_time_limit=min_time_limit,
            gt_time_limit_factor=gt_time_limit_factor,
        )
        ret.append((stat, det.tolist()))
    return ret

# === NexusCore/openenv\Lib\site-packages\inquirer\questions.py ===
"""Module that implements the questions types."""

from __future__ import annotations

import json
import pathlib

import inquirer.errors as errors
from inquirer.render.console._other import GLOBAL_OTHER_CHOICE


class TaggedValue:
    def __init__(self, tag, value):
        self.tag = tag
        self.value = value
        self.tuple = (tag, value)

    def __str__(self):
        return self.tag

    def __repr__(self):
        return repr(self.value)

    def __eq__(self, other):
        if isinstance(other, TaggedValue):
            return other.value == self.value
        if isinstance(other, tuple):
            return other == self.tuple
        return other == self.value

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.tuple)


class Question:
    kind = "base question"

    def __init__(
        self,
        name,
        message="",
        choices=None,
        default=None,
        ignore=False,
        validate=True,
        show_default=False,
        hints=None,
        other=False,
    ):
        self.name = name
        self._message = message
        self._choices = choices or []
        self._default = default
        self._ignore = ignore
        self._validate = validate
        self.answers = {}
        self.show_default = show_default
        self.hints = hints
        self._other = other

        if self._other:
            self._choices.append(GLOBAL_OTHER_CHOICE)

    def add_choice(self, choice):
        try:
            index = self._choices.index(choice)
            return index
        except ValueError:
            if self._other:
                self._choices.insert(-1, choice)
                return len(self._choices) - 2

            self._choices.append(choice)
            return len(self._choices) - 1

    @property
    def ignore(self):
        return bool(self._solve(self._ignore))

    @property
    def message(self):
        return self._solve(self._message)

    @property
    def default(self):
        return self.answers.get(self.name) or self._solve(self._default)

    @property
    def choices_generator(self):
        for choice in self._solve(self._choices):
            yield (TaggedValue(*choice) if isinstance(choice, tuple) and len(choice) == 2 else choice)

    @property
    def choices(self):
        return list(self.choices_generator)

    def validate(self, current):
        try:
            if self._solve(self._validate, current):
                return
        except errors.ValidationError as e:
            raise e
        raise errors.ValidationError(current)

    def _solve(self, prop, *args, **kwargs):
        if callable(prop):
            return prop(self.answers, *args, **kwargs)
        if isinstance(prop, str):
            return prop.format(**self.answers)
        return prop


class Text(Question):
    kind = "text"

    def __init__(self, name, message="", default=None, autocomplete=None, **kwargs):
        super().__init__(
            name, message=message, default=str(default) if default and not callable(default) else default, **kwargs
        )
        self.autocomplete = autocomplete


class Password(Text):
    kind = "password"

    def __init__(self, name, echo="*", **kwargs):
        super().__init__(name, **kwargs)
        self.echo = echo


class Editor(Text):
    kind = "editor"


class Confirm(Question):
    kind = "confirm"

    def __init__(self, name, default=False, **kwargs):
        super().__init__(name, default=default, **kwargs)


class List(Question):
    kind = "list"

    def __init__(
        self,
        name,
        message="",
        choices=None,
        hints=None,
        default=None,
        ignore=False,
        validate=True,
        carousel=False,
        other=False,
        autocomplete=None,
    ):
        super().__init__(name, message, choices, default, ignore, validate, hints=hints, other=other)
        self.carousel = carousel
        self.autocomplete = autocomplete


class Checkbox(Question):
    kind = "checkbox"

    def __init__(
        self,
        name,
        message="",
        choices=None,
        hints=None,
        locked=None,
        default=None,
        ignore=False,
        validate=True,
        carousel=False,
        other=False,
        autocomplete=None,
    ):
        super().__init__(name, message, choices, default, ignore, validate, hints=hints, other=other)
        self.locked = locked
        self.carousel = carousel
        self.autocomplete = autocomplete


class Path(Text):
    ANY = "any"
    FILE = "file"
    DIRECTORY = "directory"

    kind = "path"

    def __init__(self, name, default=None, path_type="any", exists=None, **kwargs):
        super().__init__(name, default=default, **kwargs)

        if path_type in (Path.ANY, Path.FILE, Path.DIRECTORY):
            self._path_type = path_type
        else:
            raise ValueError("'path_type' must be one of [ANY, FILE, DIRECTORY]")

        self._exists = exists

        if default is not None:
            try:
                self.validate(default)
            except errors.ValidationError:
                raise ValueError("Default value '{}' is not valid based on " "your Path's criteria".format(default))

    def validate(self, current: str):
        super().validate(current)

        if current is None:
            raise errors.ValidationError(current)

        path = pathlib.Path(current)

        # this block validates the path in correspondence with the OS
        # it will error if the path contains invalid characters
        try:
            path.lstat()
        except FileNotFoundError:
            pass
        except (ValueError, OSError) as e:
            raise errors.ValidationError(e)

        if (self._exists is True and not path.exists()) or (self._exists is False and path.exists()):
            raise errors.ValidationError(current)

        # os.path.isdir and isfile check also existence of the path,
        # which might not be desirable
        if self._path_type == Path.FILE:
            if current.endswith(("\\", "/")):
                raise errors.ValidationError(current)
            if path.exists() and not path.is_file():
                raise errors.ValidationError(current)

        if self._path_type == Path.DIRECTORY:
            if current == "":
                raise errors.ValidationError(current)
            if path.exists() and not path.is_dir():
                raise errors.ValidationError(current)


def question_factory(kind, *args, **kwargs):
    for cl in (Text, Editor, Password, Confirm, List, Checkbox, Path):
        if cl.kind == kind:
            return cl(*args, **kwargs)
    raise errors.UnknownQuestionTypeError()


def load_from_dict(question_dict) -> Question:
    """Load one question from a dict.

    It requires the keys 'name' and 'kind'.

    Returns:
        The Question object with associated data.
    """
    return question_factory(**question_dict)


def load_from_list(question_list) -> list[Question]:
    """Load a list of questions from a list of dicts.

    It requires the keys 'name' and 'kind' for each dict.

    Returns:
        A list of Question objects with associated data.
    """
    return [load_from_dict(q) for q in question_list]


def load_from_json(question_json) -> list | dict:
    """Load Questions from a JSON string.

    Returns:
        A list of Question objects with associated data if the JSON
        contains a list or a Question if the JSON contains a dict.
    """
    data = json.loads(question_json)
    if isinstance(data, list):
        return load_from_list(data)
    if isinstance(data, dict):
        return load_from_dict(data)
    raise TypeError("Json contained a %s variable when a dict or list was expected", type(data))

# === NexusCore/openenv\Lib\site-packages\pyasn1\type\char.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import sys

from pyasn1 import error
from pyasn1.type import tag
from pyasn1.type import univ

__all__ = ['NumericString', 'PrintableString', 'TeletexString', 'T61String', 'VideotexString',
           'IA5String', 'GraphicString', 'VisibleString', 'ISO646String',
           'GeneralString', 'UniversalString', 'BMPString', 'UTF8String']

NoValue = univ.NoValue
noValue = univ.noValue


class AbstractCharacterString(univ.OctetString):
    """Creates |ASN.1| schema or value object.

    |ASN.1| class is based on :class:`~pyasn1.type.base.SimpleAsn1Type`,
    its objects are immutable and duck-type :class:`bytes`.
    When used in octet-stream context, |ASN.1| type assumes
    "|encoding|" encoding.

    Keyword Args
    ------------
    value: :class:`str`, :class:`bytes` or |ASN.1| object
        :class:`str`, alternatively :class:`bytes`
        representing octet-stream of serialised unicode string
        (note `encoding` parameter) or |ASN.1| class instance.
        If `value` is not given, schema object will be created.

    tagSet: :py:class:`~pyasn1.type.tag.TagSet`
        Object representing non-default ASN.1 tag(s)

    subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
        Object representing non-default ASN.1 subtype constraint(s). Constraints
        verification for |ASN.1| type occurs automatically on object
        instantiation.

    encoding: :py:class:`str`
        Unicode codec ID to encode/decode
        :class:`str` the payload when |ASN.1| object is used
        in octet-stream context.

    Raises
    ------
    ~pyasn1.error.ValueConstraintError, ~pyasn1.error.PyAsn1Error
        On constraint violation or bad initializer.
    """

    def __str__(self):
        return str(self._value)

    def __bytes__(self):
        try:
            return self._value.encode(self.encoding)
        except UnicodeEncodeError as exc:
            raise error.PyAsn1UnicodeEncodeError(
                "Can't encode string '%s' with codec "
                "%s" % (self._value, self.encoding), exc
            )

    def prettyIn(self, value):
        try:
            if isinstance(value, str):
                return value
            elif isinstance(value, bytes):
                return value.decode(self.encoding)
            elif isinstance(value, (tuple, list)):
                return self.prettyIn(bytes(value))
            elif isinstance(value, univ.OctetString):
                return value.asOctets().decode(self.encoding)
            else:
                return str(value)

        except (UnicodeDecodeError, LookupError) as exc:
            raise error.PyAsn1UnicodeDecodeError(
                "Can't decode string '%s' with codec "
                "%s" % (value, self.encoding), exc
            )

    def asOctets(self, padding=True):
        return bytes(self)

    def asNumbers(self, padding=True):
        return tuple(bytes(self))

    #
    # See OctetString.prettyPrint() for the explanation
    #

    def prettyOut(self, value):
        return value

    def prettyPrint(self, scope=0):
        # first see if subclass has its own .prettyOut()
        value = self.prettyOut(self._value)

        if value is not self._value:
            return value

        return AbstractCharacterString.__str__(self)

    def __reversed__(self):
        return reversed(self._value)


class NumericString(AbstractCharacterString):
    __doc__ = AbstractCharacterString.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = AbstractCharacterString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 18)
    )
    encoding = 'us-ascii'

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()


class PrintableString(AbstractCharacterString):
    __doc__ = AbstractCharacterString.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = AbstractCharacterString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 19)
    )
    encoding = 'us-ascii'

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()


class TeletexString(AbstractCharacterString):
    __doc__ = AbstractCharacterString.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = AbstractCharacterString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 20)
    )
    encoding = 'iso-8859-1'

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()


class T61String(TeletexString):
    __doc__ = TeletexString.__doc__

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()


class VideotexString(AbstractCharacterString):
    __doc__ = AbstractCharacterString.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = AbstractCharacterString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 21)
    )
    encoding = 'iso-8859-1'

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()


class IA5String(AbstractCharacterString):
    __doc__ = AbstractCharacterString.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = AbstractCharacterString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 22)
    )
    encoding = 'us-ascii'

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()


class GraphicString(AbstractCharacterString):
    __doc__ = AbstractCharacterString.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = AbstractCharacterString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 25)
    )
    encoding = 'iso-8859-1'

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()


class VisibleString(AbstractCharacterString):
    __doc__ = AbstractCharacterString.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = AbstractCharacterString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 26)
    )
    encoding = 'us-ascii'

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()


class ISO646String(VisibleString):
    __doc__ = VisibleString.__doc__

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()

class GeneralString(AbstractCharacterString):
    __doc__ = AbstractCharacterString.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = AbstractCharacterString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 27)
    )
    encoding = 'iso-8859-1'

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()


class UniversalString(AbstractCharacterString):
    __doc__ = AbstractCharacterString.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = AbstractCharacterString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 28)
    )
    encoding = "utf-32-be"

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()


class BMPString(AbstractCharacterString):
    __doc__ = AbstractCharacterString.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = AbstractCharacterString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 30)
    )
    encoding = "utf-16-be"

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()


class UTF8String(AbstractCharacterString):
    __doc__ = AbstractCharacterString.__doc__

    #: Set (on class, not on instance) or return a
    #: :py:class:`~pyasn1.type.tag.TagSet` object representing ASN.1 tag(s)
    #: associated with |ASN.1| type.
    tagSet = AbstractCharacterString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 12)
    )
    encoding = "utf-8"

    # Optimization for faster codec lookup
    typeId = AbstractCharacterString.getTypeId()

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\media.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Media (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class PlayerId(str):
    '''
    Players will get an ID that is unique within the agent context.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> PlayerId:
        return cls(json)

    def __repr__(self):
        return 'PlayerId({})'.format(super().__repr__())


class Timestamp(float):
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> Timestamp:
        return cls(json)

    def __repr__(self):
        return 'Timestamp({})'.format(super().__repr__())


@dataclass
class PlayerMessage:
    '''
    Have one type per entry in MediaLogRecord::Type
    Corresponds to kMessage
    '''
    #: Keep in sync with MediaLogMessageLevel
    #: We are currently keeping the message level 'error' separate from the
    #: PlayerError type because right now they represent different things,
    #: this one being a DVLOG(ERROR) style log message that gets printed
    #: based on what log level is selected in the UI, and the other is a
    #: representation of a media::PipelineStatus object. Soon however we're
    #: going to be moving away from using PipelineStatus for errors and
    #: introducing a new error type which should hopefully let us integrate
    #: the error log level into the PlayerError type.
    level: str

    message: str

    def to_json(self):
        json = dict()
        json['level'] = self.level
        json['message'] = self.message
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            level=str(json['level']),
            message=str(json['message']),
        )


@dataclass
class PlayerProperty:
    '''
    Corresponds to kMediaPropertyChange
    '''
    name: str

    value: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
        )


@dataclass
class PlayerEvent:
    '''
    Corresponds to kMediaEventTriggered
    '''
    timestamp: Timestamp

    value: str

    def to_json(self):
        json = dict()
        json['timestamp'] = self.timestamp.to_json()
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            timestamp=Timestamp.from_json(json['timestamp']),
            value=str(json['value']),
        )


@dataclass
class PlayerErrorSourceLocation:
    '''
    Represents logged source line numbers reported in an error.
    NOTE: file and line are from chromium c++ implementation code, not js.
    '''
    file: str

    line: int

    def to_json(self):
        json = dict()
        json['file'] = self.file
        json['line'] = self.line
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            file=str(json['file']),
            line=int(json['line']),
        )


@dataclass
class PlayerError:
    '''
    Corresponds to kMediaError
    '''
    error_type: str

    #: Code is the numeric enum entry for a specific set of error codes, such
    #: as PipelineStatusCodes in media/base/pipeline_status.h
    code: int

    #: A trace of where this error was caused / where it passed through.
    stack: typing.List[PlayerErrorSourceLocation]

    #: Errors potentially have a root cause error, ie, a DecoderError might be
    #: caused by an WindowsError
    cause: typing.List[PlayerError]

    #: Extra data attached to an error, such as an HRESULT, Video Codec, etc.
    data: dict

    def to_json(self):
        json = dict()
        json['errorType'] = self.error_type
        json['code'] = self.code
        json['stack'] = [i.to_json() for i in self.stack]
        json['cause'] = [i.to_json() for i in self.cause]
        json['data'] = self.data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error_type=str(json['errorType']),
            code=int(json['code']),
            stack=[PlayerErrorSourceLocation.from_json(i) for i in json['stack']],
            cause=[PlayerError.from_json(i) for i in json['cause']],
            data=dict(json['data']),
        )


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables the Media domain
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Media.enable',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables the Media domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Media.disable',
    }
    json = yield cmd_dict


@event_class('Media.playerPropertiesChanged')
@dataclass
class PlayerPropertiesChanged:
    '''
    This can be called multiple times, and can be used to set / override /
    remove player properties. A null propValue indicates removal.
    '''
    player_id: PlayerId
    properties: typing.List[PlayerProperty]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayerPropertiesChanged:
        return cls(
            player_id=PlayerId.from_json(json['playerId']),
            properties=[PlayerProperty.from_json(i) for i in json['properties']]
        )


@event_class('Media.playerEventsAdded')
@dataclass
class PlayerEventsAdded:
    '''
    Send events as a list, allowing them to be batched on the browser for less
    congestion. If batched, events must ALWAYS be in chronological order.
    '''
    player_id: PlayerId
    events: typing.List[PlayerEvent]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayerEventsAdded:
        return cls(
            player_id=PlayerId.from_json(json['playerId']),
            events=[PlayerEvent.from_json(i) for i in json['events']]
        )


@event_class('Media.playerMessagesLogged')
@dataclass
class PlayerMessagesLogged:
    '''
    Send a list of any messages that need to be delivered.
    '''
    player_id: PlayerId
    messages: typing.List[PlayerMessage]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayerMessagesLogged:
        return cls(
            player_id=PlayerId.from_json(json['playerId']),
            messages=[PlayerMessage.from_json(i) for i in json['messages']]
        )


@event_class('Media.playerErrorsRaised')
@dataclass
class PlayerErrorsRaised:
    '''
    Send a list of any errors that need to be delivered.
    '''
    player_id: PlayerId
    errors: typing.List[PlayerError]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayerErrorsRaised:
        return cls(
            player_id=PlayerId.from_json(json['playerId']),
            errors=[PlayerError.from_json(i) for i in json['errors']]
        )


@event_class('Media.playersCreated')
@dataclass
class PlayersCreated:
    '''
    Called whenever a player is created, or when a new agent joins and receives
    a list of active players. If an agent is restored, it will receive the full
    list of player ids and all events again.
    '''
    players: typing.List[PlayerId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayersCreated:
        return cls(
            players=[PlayerId.from_json(i) for i in json['players']]
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\media.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Media (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class PlayerId(str):
    '''
    Players will get an ID that is unique within the agent context.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> PlayerId:
        return cls(json)

    def __repr__(self):
        return 'PlayerId({})'.format(super().__repr__())


class Timestamp(float):
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> Timestamp:
        return cls(json)

    def __repr__(self):
        return 'Timestamp({})'.format(super().__repr__())


@dataclass
class PlayerMessage:
    '''
    Have one type per entry in MediaLogRecord::Type
    Corresponds to kMessage
    '''
    #: Keep in sync with MediaLogMessageLevel
    #: We are currently keeping the message level 'error' separate from the
    #: PlayerError type because right now they represent different things,
    #: this one being a DVLOG(ERROR) style log message that gets printed
    #: based on what log level is selected in the UI, and the other is a
    #: representation of a media::PipelineStatus object. Soon however we're
    #: going to be moving away from using PipelineStatus for errors and
    #: introducing a new error type which should hopefully let us integrate
    #: the error log level into the PlayerError type.
    level: str

    message: str

    def to_json(self):
        json = dict()
        json['level'] = self.level
        json['message'] = self.message
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            level=str(json['level']),
            message=str(json['message']),
        )


@dataclass
class PlayerProperty:
    '''
    Corresponds to kMediaPropertyChange
    '''
    name: str

    value: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
        )


@dataclass
class PlayerEvent:
    '''
    Corresponds to kMediaEventTriggered
    '''
    timestamp: Timestamp

    value: str

    def to_json(self):
        json = dict()
        json['timestamp'] = self.timestamp.to_json()
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            timestamp=Timestamp.from_json(json['timestamp']),
            value=str(json['value']),
        )


@dataclass
class PlayerErrorSourceLocation:
    '''
    Represents logged source line numbers reported in an error.
    NOTE: file and line are from chromium c++ implementation code, not js.
    '''
    file: str

    line: int

    def to_json(self):
        json = dict()
        json['file'] = self.file
        json['line'] = self.line
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            file=str(json['file']),
            line=int(json['line']),
        )


@dataclass
class PlayerError:
    '''
    Corresponds to kMediaError
    '''
    error_type: str

    #: Code is the numeric enum entry for a specific set of error codes, such
    #: as PipelineStatusCodes in media/base/pipeline_status.h
    code: int

    #: A trace of where this error was caused / where it passed through.
    stack: typing.List[PlayerErrorSourceLocation]

    #: Errors potentially have a root cause error, ie, a DecoderError might be
    #: caused by an WindowsError
    cause: typing.List[PlayerError]

    #: Extra data attached to an error, such as an HRESULT, Video Codec, etc.
    data: dict

    def to_json(self):
        json = dict()
        json['errorType'] = self.error_type
        json['code'] = self.code
        json['stack'] = [i.to_json() for i in self.stack]
        json['cause'] = [i.to_json() for i in self.cause]
        json['data'] = self.data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error_type=str(json['errorType']),
            code=int(json['code']),
            stack=[PlayerErrorSourceLocation.from_json(i) for i in json['stack']],
            cause=[PlayerError.from_json(i) for i in json['cause']],
            data=dict(json['data']),
        )


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables the Media domain
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Media.enable',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables the Media domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Media.disable',
    }
    json = yield cmd_dict


@event_class('Media.playerPropertiesChanged')
@dataclass
class PlayerPropertiesChanged:
    '''
    This can be called multiple times, and can be used to set / override /
    remove player properties. A null propValue indicates removal.
    '''
    player_id: PlayerId
    properties: typing.List[PlayerProperty]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayerPropertiesChanged:
        return cls(
            player_id=PlayerId.from_json(json['playerId']),
            properties=[PlayerProperty.from_json(i) for i in json['properties']]
        )


@event_class('Media.playerEventsAdded')
@dataclass
class PlayerEventsAdded:
    '''
    Send events as a list, allowing them to be batched on the browser for less
    congestion. If batched, events must ALWAYS be in chronological order.
    '''
    player_id: PlayerId
    events: typing.List[PlayerEvent]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayerEventsAdded:
        return cls(
            player_id=PlayerId.from_json(json['playerId']),
            events=[PlayerEvent.from_json(i) for i in json['events']]
        )


@event_class('Media.playerMessagesLogged')
@dataclass
class PlayerMessagesLogged:
    '''
    Send a list of any messages that need to be delivered.
    '''
    player_id: PlayerId
    messages: typing.List[PlayerMessage]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayerMessagesLogged:
        return cls(
            player_id=PlayerId.from_json(json['playerId']),
            messages=[PlayerMessage.from_json(i) for i in json['messages']]
        )


@event_class('Media.playerErrorsRaised')
@dataclass
class PlayerErrorsRaised:
    '''
    Send a list of any errors that need to be delivered.
    '''
    player_id: PlayerId
    errors: typing.List[PlayerError]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayerErrorsRaised:
        return cls(
            player_id=PlayerId.from_json(json['playerId']),
            errors=[PlayerError.from_json(i) for i in json['errors']]
        )


@event_class('Media.playersCreated')
@dataclass
class PlayersCreated:
    '''
    Called whenever a player is created, or when a new agent joins and receives
    a list of active players. If an agent is restored, it will receive the full
    list of player ids and all events again.
    '''
    players: typing.List[PlayerId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayersCreated:
        return cls(
            players=[PlayerId.from_json(i) for i in json['players']]
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\media.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Media (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class PlayerId(str):
    '''
    Players will get an ID that is unique within the agent context.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> PlayerId:
        return cls(json)

    def __repr__(self):
        return 'PlayerId({})'.format(super().__repr__())


class Timestamp(float):
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> Timestamp:
        return cls(json)

    def __repr__(self):
        return 'Timestamp({})'.format(super().__repr__())


@dataclass
class PlayerMessage:
    '''
    Have one type per entry in MediaLogRecord::Type
    Corresponds to kMessage
    '''
    #: Keep in sync with MediaLogMessageLevel
    #: We are currently keeping the message level 'error' separate from the
    #: PlayerError type because right now they represent different things,
    #: this one being a DVLOG(ERROR) style log message that gets printed
    #: based on what log level is selected in the UI, and the other is a
    #: representation of a media::PipelineStatus object. Soon however we're
    #: going to be moving away from using PipelineStatus for errors and
    #: introducing a new error type which should hopefully let us integrate
    #: the error log level into the PlayerError type.
    level: str

    message: str

    def to_json(self):
        json = dict()
        json['level'] = self.level
        json['message'] = self.message
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            level=str(json['level']),
            message=str(json['message']),
        )


@dataclass
class PlayerProperty:
    '''
    Corresponds to kMediaPropertyChange
    '''
    name: str

    value: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
        )


@dataclass
class PlayerEvent:
    '''
    Corresponds to kMediaEventTriggered
    '''
    timestamp: Timestamp

    value: str

    def to_json(self):
        json = dict()
        json['timestamp'] = self.timestamp.to_json()
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            timestamp=Timestamp.from_json(json['timestamp']),
            value=str(json['value']),
        )


@dataclass
class PlayerErrorSourceLocation:
    '''
    Represents logged source line numbers reported in an error.
    NOTE: file and line are from chromium c++ implementation code, not js.
    '''
    file: str

    line: int

    def to_json(self):
        json = dict()
        json['file'] = self.file
        json['line'] = self.line
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            file=str(json['file']),
            line=int(json['line']),
        )


@dataclass
class PlayerError:
    '''
    Corresponds to kMediaError
    '''
    error_type: str

    #: Code is the numeric enum entry for a specific set of error codes, such
    #: as PipelineStatusCodes in media/base/pipeline_status.h
    code: int

    #: A trace of where this error was caused / where it passed through.
    stack: typing.List[PlayerErrorSourceLocation]

    #: Errors potentially have a root cause error, ie, a DecoderError might be
    #: caused by an WindowsError
    cause: typing.List[PlayerError]

    #: Extra data attached to an error, such as an HRESULT, Video Codec, etc.
    data: dict

    def to_json(self):
        json = dict()
        json['errorType'] = self.error_type
        json['code'] = self.code
        json['stack'] = [i.to_json() for i in self.stack]
        json['cause'] = [i.to_json() for i in self.cause]
        json['data'] = self.data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error_type=str(json['errorType']),
            code=int(json['code']),
            stack=[PlayerErrorSourceLocation.from_json(i) for i in json['stack']],
            cause=[PlayerError.from_json(i) for i in json['cause']],
            data=dict(json['data']),
        )


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables the Media domain
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Media.enable',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables the Media domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Media.disable',
    }
    json = yield cmd_dict


@event_class('Media.playerPropertiesChanged')
@dataclass
class PlayerPropertiesChanged:
    '''
    This can be called multiple times, and can be used to set / override /
    remove player properties. A null propValue indicates removal.
    '''
    player_id: PlayerId
    properties: typing.List[PlayerProperty]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayerPropertiesChanged:
        return cls(
            player_id=PlayerId.from_json(json['playerId']),
            properties=[PlayerProperty.from_json(i) for i in json['properties']]
        )


@event_class('Media.playerEventsAdded')
@dataclass
class PlayerEventsAdded:
    '''
    Send events as a list, allowing them to be batched on the browser for less
    congestion. If batched, events must ALWAYS be in chronological order.
    '''
    player_id: PlayerId
    events: typing.List[PlayerEvent]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayerEventsAdded:
        return cls(
            player_id=PlayerId.from_json(json['playerId']),
            events=[PlayerEvent.from_json(i) for i in json['events']]
        )


@event_class('Media.playerMessagesLogged')
@dataclass
class PlayerMessagesLogged:
    '''
    Send a list of any messages that need to be delivered.
    '''
    player_id: PlayerId
    messages: typing.List[PlayerMessage]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayerMessagesLogged:
        return cls(
            player_id=PlayerId.from_json(json['playerId']),
            messages=[PlayerMessage.from_json(i) for i in json['messages']]
        )


@event_class('Media.playerErrorsRaised')
@dataclass
class PlayerErrorsRaised:
    '''
    Send a list of any errors that need to be delivered.
    '''
    player_id: PlayerId
    errors: typing.List[PlayerError]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayerErrorsRaised:
        return cls(
            player_id=PlayerId.from_json(json['playerId']),
            errors=[PlayerError.from_json(i) for i in json['errors']]
        )


@event_class('Media.playersCreated')
@dataclass
class PlayersCreated:
    '''
    Called whenever a player is created, or when a new agent joins and receives
    a list of active players. If an agent is restored, it will receive the full
    list of player ids and all events again.
    '''
    players: typing.List[PlayerId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PlayersCreated:
        return cls(
            players=[PlayerId.from_json(i) for i in json['players']]
        )

# === NexusCore/openenv\Lib\site-packages\fontTools\feaLib\lexer.py ===
from fontTools.feaLib.error import FeatureLibError, IncludedFeaNotFound
from fontTools.feaLib.location import FeatureLibLocation
import re
import os

try:
    import cython
except ImportError:
    # if cython not installed, use mock module with no-op decorators and types
    from fontTools.misc import cython


class Lexer(object):
    NUMBER = "NUMBER"
    HEXADECIMAL = "HEXADECIMAL"
    OCTAL = "OCTAL"
    NUMBERS = (NUMBER, HEXADECIMAL, OCTAL)
    FLOAT = "FLOAT"
    STRING = "STRING"
    NAME = "NAME"
    FILENAME = "FILENAME"
    GLYPHCLASS = "GLYPHCLASS"
    CID = "CID"
    SYMBOL = "SYMBOL"
    COMMENT = "COMMENT"
    NEWLINE = "NEWLINE"
    ANONYMOUS_BLOCK = "ANONYMOUS_BLOCK"

    CHAR_WHITESPACE_ = " \t"
    CHAR_NEWLINE_ = "\r\n"
    CHAR_SYMBOL_ = ",;:-+'{}[]<>()="
    CHAR_DIGIT_ = "0123456789"
    CHAR_HEXDIGIT_ = "0123456789ABCDEFabcdef"
    CHAR_LETTER_ = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    CHAR_NAME_START_ = CHAR_LETTER_ + "_+*:.^~!\\"
    CHAR_NAME_CONTINUATION_ = CHAR_LETTER_ + CHAR_DIGIT_ + "_.+*:^~!/-"

    RE_GLYPHCLASS = re.compile(r"^[A-Za-z_0-9.\-]+$")

    MODE_NORMAL_ = "NORMAL"
    MODE_FILENAME_ = "FILENAME"

    def __init__(self, text, filename):
        self.filename_ = filename
        self.line_ = 1
        self.pos_ = 0
        self.line_start_ = 0
        self.text_ = text
        self.text_length_ = len(text)
        self.mode_ = Lexer.MODE_NORMAL_

    def __iter__(self):
        return self

    def next(self):  # Python 2
        return self.__next__()

    def __next__(self):  # Python 3
        while True:
            token_type, token, location = self.next_()
            if token_type != Lexer.NEWLINE:
                return (token_type, token, location)

    def location_(self):
        column = self.pos_ - self.line_start_ + 1
        return FeatureLibLocation(self.filename_ or "<features>", self.line_, column)

    def next_(self):
        self.scan_over_(Lexer.CHAR_WHITESPACE_)
        location = self.location_()
        start = self.pos_
        text = self.text_
        limit = len(text)
        if start >= limit:
            raise StopIteration()
        cur_char = text[start]
        next_char = text[start + 1] if start + 1 < limit else None

        if cur_char == "\n":
            self.pos_ += 1
            self.line_ += 1
            self.line_start_ = self.pos_
            return (Lexer.NEWLINE, None, location)
        if cur_char == "\r":
            self.pos_ += 2 if next_char == "\n" else 1
            self.line_ += 1
            self.line_start_ = self.pos_
            return (Lexer.NEWLINE, None, location)
        if cur_char == "#":
            self.scan_until_(Lexer.CHAR_NEWLINE_)
            return (Lexer.COMMENT, text[start : self.pos_], location)

        if self.mode_ is Lexer.MODE_FILENAME_:
            if cur_char != "(":
                raise FeatureLibError("Expected '(' before file name", location)
            self.scan_until_(")")
            cur_char = text[self.pos_] if self.pos_ < limit else None
            if cur_char != ")":
                raise FeatureLibError("Expected ')' after file name", location)
            self.pos_ += 1
            self.mode_ = Lexer.MODE_NORMAL_
            return (Lexer.FILENAME, text[start + 1 : self.pos_ - 1], location)

        if cur_char == "\\" and next_char in Lexer.CHAR_DIGIT_:
            self.pos_ += 1
            self.scan_over_(Lexer.CHAR_DIGIT_)
            return (Lexer.CID, int(text[start + 1 : self.pos_], 10), location)
        if cur_char == "@":
            self.pos_ += 1
            self.scan_over_(Lexer.CHAR_NAME_CONTINUATION_)
            glyphclass = text[start + 1 : self.pos_]
            if len(glyphclass) < 1:
                raise FeatureLibError("Expected glyph class name", location)
            if not Lexer.RE_GLYPHCLASS.match(glyphclass):
                raise FeatureLibError(
                    "Glyph class names must consist of letters, digits, "
                    "underscore, period or hyphen",
                    location,
                )
            return (Lexer.GLYPHCLASS, glyphclass, location)
        if cur_char in Lexer.CHAR_NAME_START_:
            self.pos_ += 1
            self.scan_over_(Lexer.CHAR_NAME_CONTINUATION_)
            token = text[start : self.pos_]
            if token == "include":
                self.mode_ = Lexer.MODE_FILENAME_
            return (Lexer.NAME, token, location)
        if cur_char == "0" and next_char in "xX":
            self.pos_ += 2
            self.scan_over_(Lexer.CHAR_HEXDIGIT_)
            return (Lexer.HEXADECIMAL, int(text[start : self.pos_], 16), location)
        if cur_char == "0" and next_char in Lexer.CHAR_DIGIT_:
            self.scan_over_(Lexer.CHAR_DIGIT_)
            return (Lexer.OCTAL, int(text[start : self.pos_], 8), location)
        if cur_char in Lexer.CHAR_DIGIT_:
            self.scan_over_(Lexer.CHAR_DIGIT_)
            if self.pos_ >= limit or text[self.pos_] != ".":
                return (Lexer.NUMBER, int(text[start : self.pos_], 10), location)
            self.scan_over_(".")
            self.scan_over_(Lexer.CHAR_DIGIT_)
            return (Lexer.FLOAT, float(text[start : self.pos_]), location)
        if cur_char == "-" and next_char in Lexer.CHAR_DIGIT_:
            self.pos_ += 1
            self.scan_over_(Lexer.CHAR_DIGIT_)
            if self.pos_ >= limit or text[self.pos_] != ".":
                return (Lexer.NUMBER, int(text[start : self.pos_], 10), location)
            self.scan_over_(".")
            self.scan_over_(Lexer.CHAR_DIGIT_)
            return (Lexer.FLOAT, float(text[start : self.pos_]), location)
        if cur_char in Lexer.CHAR_SYMBOL_:
            self.pos_ += 1
            return (Lexer.SYMBOL, cur_char, location)
        if cur_char == '"':
            self.pos_ += 1
            self.scan_until_('"')
            if self.pos_ < self.text_length_ and self.text_[self.pos_] == '"':
                self.pos_ += 1
                # strip newlines embedded within a string
                string = re.sub("[\r\n]", "", text[start + 1 : self.pos_ - 1])
                return (Lexer.STRING, string, location)
            else:
                raise FeatureLibError("Expected '\"' to terminate string", location)
        raise FeatureLibError("Unexpected character: %r" % cur_char, location)

    def scan_over_(self, valid):
        p = self.pos_
        while p < self.text_length_ and self.text_[p] in valid:
            p += 1
        self.pos_ = p

    def scan_until_(self, stop_at):
        p = self.pos_
        while p < self.text_length_ and self.text_[p] not in stop_at:
            p += 1
        self.pos_ = p

    def scan_anonymous_block(self, tag):
        location = self.location_()
        tag = tag.strip()
        self.scan_until_(Lexer.CHAR_NEWLINE_)
        self.scan_over_(Lexer.CHAR_NEWLINE_)
        regexp = r"}\s*" + tag + r"\s*;"
        split = re.split(regexp, self.text_[self.pos_ :], maxsplit=1)
        if len(split) != 2:
            raise FeatureLibError(
                "Expected '} %s;' to terminate anonymous block" % tag, location
            )
        self.pos_ += len(split[0])
        return (Lexer.ANONYMOUS_BLOCK, split[0], location)


class IncludingLexer(object):
    """A Lexer that follows include statements.

    The OpenType feature file specification states that due to
    historical reasons, relative imports should be resolved in this
    order:

    1. If the source font is UFO format, then relative to the UFO's
       font directory
    2. relative to the top-level include file
    3. relative to the parent include file

    We only support 1 (via includeDir) and 2.
    """

    def __init__(self, featurefile, *, includeDir=None):
        """Initializes an IncludingLexer.

        Behavior:
            If includeDir is passed, it will be used to determine the top-level
            include directory to use for all encountered include statements. If it is
            not passed, ``os.path.dirname(featurefile)`` will be considered the
            include directory.
        """

        self.lexers_ = [self.make_lexer_(featurefile)]
        self.featurefilepath = self.lexers_[0].filename_
        self.includeDir = includeDir

    def __iter__(self):
        return self

    def next(self):  # Python 2
        return self.__next__()

    def __next__(self):  # Python 3
        while self.lexers_:
            lexer = self.lexers_[-1]
            try:
                token_type, token, location = next(lexer)
            except StopIteration:
                self.lexers_.pop()
                continue
            if token_type is Lexer.NAME and token == "include":
                fname_type, fname_token, fname_location = lexer.next()
                if fname_type is not Lexer.FILENAME:
                    raise FeatureLibError("Expected file name", fname_location)
                # semi_type, semi_token, semi_location = lexer.next()
                # if semi_type is not Lexer.SYMBOL or semi_token != ";":
                #    raise FeatureLibError("Expected ';'", semi_location)
                if os.path.isabs(fname_token):
                    path = fname_token
                else:
                    if self.includeDir is not None:
                        curpath = self.includeDir
                    elif self.featurefilepath is not None:
                        curpath = os.path.dirname(self.featurefilepath)
                    else:
                        # if the IncludingLexer was initialized from an in-memory
                        # file-like stream, it doesn't have a 'name' pointing to
                        # its filesystem path, therefore we fall back to using the
                        # current working directory to resolve relative includes
                        curpath = os.getcwd()
                    path = os.path.join(curpath, fname_token)
                if len(self.lexers_) >= 5:
                    raise FeatureLibError("Too many recursive includes", fname_location)
                try:
                    self.lexers_.append(self.make_lexer_(path))
                except FileNotFoundError as err:
                    raise IncludedFeaNotFound(fname_token, fname_location) from err
            else:
                return (token_type, token, location)
        raise StopIteration()

    @staticmethod
    def make_lexer_(file_or_path):
        if hasattr(file_or_path, "read"):
            fileobj, closing = file_or_path, False
        else:
            filename, closing = file_or_path, True
            fileobj = open(filename, "r", encoding="utf-8-sig")
        data = fileobj.read()
        filename = getattr(fileobj, "name", None)
        if closing:
            fileobj.close()
        return Lexer(data, filename)

    def scan_anonymous_block(self, tag):
        return self.lexers_[-1].scan_anonymous_block(tag)


class NonIncludingLexer(IncludingLexer):
    """Lexer that does not follow `include` statements, emits them as-is."""

    def __next__(self):  # Python 3
        return next(self.lexers_[0])

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\arize\_utils.py ===
import json
from typing import TYPE_CHECKING, Any, Optional, Union

from litellm._logging import verbose_logger
from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
from litellm.types.utils import StandardLoggingPayload

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    Span = Union[_Span, Any]
else:
    Span = Any


def cast_as_primitive_value_type(value) -> Union[str, bool, int, float]:
    """
    Converts a value to an OTEL-supported primitive for Arize/Phoenix observability.
    """
    if value is None:
        return ""
    if isinstance(value, (str, bool, int, float)):
        return value
    try:
        return str(value)
    except Exception:
        return ""


def safe_set_attribute(span: Span, key: str, value: Any):
    """
    Sets a span attribute safely with OTEL-compliant primitive typing for Arize/Phoenix.
    """
    primitive_value = cast_as_primitive_value_type(value)
    span.set_attribute(key, primitive_value)


def set_attributes(span: Span, kwargs, response_obj):  # noqa: PLR0915
    """
    Populates span with OpenInference-compliant LLM attributes for Arize and Phoenix tracing.
    """
    from litellm.integrations._types.open_inference import (
        MessageAttributes,
        OpenInferenceSpanKindValues,
        SpanAttributes,
        ToolCallAttributes,
    )

    try:
        optional_params = kwargs.get("optional_params", {})
        litellm_params = kwargs.get("litellm_params", {})
        standard_logging_payload: Optional[StandardLoggingPayload] = kwargs.get(
            "standard_logging_object"
        )
        if standard_logging_payload is None:
            raise ValueError("standard_logging_object not found in kwargs")

        #############################################
        ############ LLM CALL METADATA ##############
        #############################################

        # Set custom metadata for observability and trace enrichment.
        metadata = (
            standard_logging_payload.get("metadata")
            if standard_logging_payload
            else None
        )
        if metadata is not None:
            safe_set_attribute(span, SpanAttributes.METADATA, safe_dumps(metadata))

        #############################################
        ########## LLM Request Attributes ###########
        #############################################

        # The name of the LLM a request is being made to.
        if kwargs.get("model"):
            safe_set_attribute(
                span,
                SpanAttributes.LLM_MODEL_NAME,
                kwargs.get("model"),
            )

        # The LLM request type.
        safe_set_attribute(
            span,
            "llm.request.type",
            standard_logging_payload["call_type"],
        )

        # The Generative AI Provider: Azure, OpenAI, etc.
        safe_set_attribute(
            span,
            SpanAttributes.LLM_PROVIDER,
            litellm_params.get("custom_llm_provider", "Unknown"),
        )

        # The maximum number of tokens the LLM generates for a request.
        if optional_params.get("max_tokens"):
            safe_set_attribute(
                span,
                "llm.request.max_tokens",
                optional_params.get("max_tokens"),
            )

        # The temperature setting for the LLM request.
        if optional_params.get("temperature"):
            safe_set_attribute(
                span,
                "llm.request.temperature",
                optional_params.get("temperature"),
            )

        # The top_p sampling setting for the LLM request.
        if optional_params.get("top_p"):
            safe_set_attribute(
                span,
                "llm.request.top_p",
                optional_params.get("top_p"),
            )

        # Indicates whether response is streamed.
        safe_set_attribute(
            span,
            "llm.is_streaming",
            str(optional_params.get("stream", False)),
        )

        # Logs the user ID if present.
        if optional_params.get("user"):
            safe_set_attribute(
                span,
                "llm.user",
                optional_params.get("user"),
            )

        # The unique identifier for the completion.
        if response_obj and response_obj.get("id"):
            safe_set_attribute(span, "llm.response.id", response_obj.get("id"))

        # The model used to generate the response.
        if response_obj and response_obj.get("model"):
            safe_set_attribute(
                span,
                "llm.response.model",
                response_obj.get("model"),
            )

        # Required by OpenInference to mark span as LLM kind.
        safe_set_attribute(
            span,
            SpanAttributes.OPENINFERENCE_SPAN_KIND,
            OpenInferenceSpanKindValues.LLM.value,
        )
        messages = kwargs.get("messages")

        # for /chat/completions
        # https://docs.arize.com/arize/large-language-models/tracing/semantic-conventions
        if messages:
            last_message = messages[-1]
            safe_set_attribute(
                span,
                SpanAttributes.INPUT_VALUE,
                last_message.get("content", ""),
            )

            # LLM_INPUT_MESSAGES shows up under `input_messages` tab on the span page.
            for idx, msg in enumerate(messages):
                prefix = f"{SpanAttributes.LLM_INPUT_MESSAGES}.{idx}"
                # Set the role per message.
                safe_set_attribute(
                    span, f"{prefix}.{MessageAttributes.MESSAGE_ROLE}", msg.get("role")
                )
                # Set the content per message.
                safe_set_attribute(
                    span,
                    f"{prefix}.{MessageAttributes.MESSAGE_CONTENT}",
                    msg.get("content", ""),
                )

        # Capture tools (function definitions) used in the LLM call.
        tools = optional_params.get("tools")
        if tools:
            for idx, tool in enumerate(tools):
                function = tool.get("function")
                if not function:
                    continue
                prefix = f"{SpanAttributes.LLM_TOOLS}.{idx}"
                safe_set_attribute(
                    span, f"{prefix}.{SpanAttributes.TOOL_NAME}", function.get("name")
                )
                safe_set_attribute(
                    span,
                    f"{prefix}.{SpanAttributes.TOOL_DESCRIPTION}",
                    function.get("description"),
                )
                safe_set_attribute(
                    span,
                    f"{prefix}.{SpanAttributes.TOOL_PARAMETERS}",
                    json.dumps(function.get("parameters")),
                )

        # Capture tool calls made during function-calling LLM flows.
        functions = optional_params.get("functions")
        if functions:
            for idx, function in enumerate(functions):
                prefix = f"{MessageAttributes.MESSAGE_TOOL_CALLS}.{idx}"
                safe_set_attribute(
                    span,
                    f"{prefix}.{ToolCallAttributes.TOOL_CALL_FUNCTION_NAME}",
                    function.get("name"),
                )

        # Capture invocation parameters and user ID if available.
        model_params = (
            standard_logging_payload.get("model_parameters")
            if standard_logging_payload
            else None
        )
        if model_params:
            # The Generative AI Provider: Azure, OpenAI, etc.
            safe_set_attribute(
                span,
                SpanAttributes.LLM_INVOCATION_PARAMETERS,
                safe_dumps(model_params),
            )

            if model_params.get("user"):
                user_id = model_params.get("user")
                if user_id is not None:
                    safe_set_attribute(span, SpanAttributes.USER_ID, user_id)

        #############################################
        ########## LLM Response Attributes ##########
        #############################################

        # Captures response tokens, message, and content.
        if hasattr(response_obj, "get"):
            for idx, choice in enumerate(response_obj.get("choices", [])):
                response_message = choice.get("message", {})
                safe_set_attribute(
                    span,
                    SpanAttributes.OUTPUT_VALUE,
                    response_message.get("content", ""),
                )

                # This shows up under `output_messages` tab on the span page.
                prefix = f"{SpanAttributes.LLM_OUTPUT_MESSAGES}.{idx}"
                safe_set_attribute(
                    span,
                    f"{prefix}.{MessageAttributes.MESSAGE_ROLE}",
                    response_message.get("role"),
                )
                safe_set_attribute(
                    span,
                    f"{prefix}.{MessageAttributes.MESSAGE_CONTENT}",
                    response_message.get("content", ""),
                )

            # Token usage info.
            usage = response_obj and response_obj.get("usage")
            if usage:
                safe_set_attribute(
                    span,
                    SpanAttributes.LLM_TOKEN_COUNT_TOTAL,
                    usage.get("total_tokens"),
                )

                # The number of tokens used in the LLM response (completion).
                safe_set_attribute(
                    span,
                    SpanAttributes.LLM_TOKEN_COUNT_COMPLETION,
                    usage.get("completion_tokens"),
                )

                # The number of tokens used in the LLM prompt.
                safe_set_attribute(
                    span,
                    SpanAttributes.LLM_TOKEN_COUNT_PROMPT,
                    usage.get("prompt_tokens"),
                )

    except Exception as e:
        verbose_logger.error(
            f"[Arize/Phoenix] Failed to set OpenInference span attributes: {e}"
        )
        if hasattr(span, "record_exception"):
            span.record_exception(e)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\client\models.py ===
import requests
from typing import List, Dict, Any, Optional, Union
from .exceptions import UnauthorizedError, NotFoundError


class ModelsManagementClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        Initialize the ModelsManagementClient.

        Args:
            base_url (str): The base URL of the LiteLLM proxy server (e.g., "http://localhost:8000")
            api_key (Optional[str]): API key for authentication. If provided, it will be sent as a Bearer token.
        """
        self._base_url = base_url.rstrip("/")  # Remove trailing slash if present
        self._api_key = api_key

    def _get_headers(self) -> Dict[str, str]:
        """
        Get the headers for API requests, including authorization if api_key is set.

        Returns:
            Dict[str, str]: Headers to use for API requests
        """
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def list(self, return_request: bool = False) -> Union[List[Dict[str, Any]], requests.Request]:
        """
        Get the list of models supported by the server.

        Args:
            return_request (bool): If True, returns the prepared request object instead of executing it.
                                 Useful for inspection or modification before sending.

        Returns:
            Union[List[Dict[str, Any]], requests.Request]: Either a list of model information dictionaries
            or a prepared request object if return_request is True.

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/models"
        request = requests.Request("GET", url, headers=self._get_headers())

        if return_request:
            return request

        # Prepare and send the request
        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()["data"]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            raise

    def new(
        self,
        model_name: str,
        model_params: Dict[str, Any],
        model_info: Optional[Dict[str, Any]] = None,
        return_request: bool = False,
    ) -> Union[Dict[str, Any], requests.Request]:
        """
        Add a new model to the proxy.

        Args:
            model_name (str): Name of the model to add
            model_params (Dict[str, Any]): Parameters for the model (e.g., model type, api_base, api_key)
            model_info (Optional[Dict[str, Any]]): Additional information about the model
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[Dict[str, Any], requests.Request]: Either the response from the server or
            a prepared request object if return_request is True

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/model/new"

        data = {
            "model_name": model_name,
            "litellm_params": model_params,
        }
        if model_info:
            data["model_info"] = model_info

        request = requests.Request("POST", url, headers=self._get_headers(), json=data)

        if return_request:
            return request

        # Prepare and send the request
        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            raise

    def delete(self, model_id: str, return_request: bool = False) -> Union[Dict[str, Any], requests.Request]:
        """
        Delete a model from the proxy.

        Args:
            model_id (str): ID of the model to delete (e.g., "2f23364f-4579-4d79-a43a-2d48dd551c2e")
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[Dict[str, Any], requests.Request]: Either the response from the server or
            a prepared request object if return_request is True

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            NotFoundError: If the request fails with a 404 status code or indicates the model was not found
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/model/delete"
        data = {"id": model_id}

        request = requests.Request("POST", url, headers=self._get_headers(), json=data)

        if return_request:
            return request

        # Prepare and send the request
        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            if e.response.status_code == 404 or "not found" in e.response.text.lower():
                raise NotFoundError(e)
            raise

    def get(
        self, model_id: Optional[str] = None, model_name: Optional[str] = None, return_request: bool = False
    ) -> Union[Dict[str, Any], requests.Request]:
        """
        Get information about a specific model by its ID or name.

        Args:
            model_id (Optional[str]): ID of the model to retrieve
            model_name (Optional[str]): Name of the model to retrieve
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[Dict[str, Any], requests.Request]: Either the model information from the server or
            a prepared request object if return_request is True

        Raises:
            ValueError: If neither model_id nor model_name is provided, or if both are provided
            UnauthorizedError: If the request fails with a 401 status code
            NotFoundError: If the model is not found
            requests.exceptions.RequestException: If the request fails with any other error
        """
        if (model_id is None and model_name is None) or (model_id is not None and model_name is not None):
            raise ValueError("Exactly one of model_id or model_name must be provided")

        # If return_request is True, delegate to info
        if return_request:
            result = self.info(return_request=True)
            assert isinstance(result, requests.Request)
            return result

        # Get all models and filter
        models = self.info()
        assert isinstance(models, List)

        # Find the matching model
        for model in models:
            if (model_id and model.get("model_info", {}).get("id") == model_id) or (
                model_name and model.get("model_name") == model_name
            ):
                return model

        # If we get here, no model was found
        if model_id:
            msg = f"Model with id={model_id} not found"
        elif model_name:
            msg = f"Model with model_name={model_name} not found"
        else:
            msg = "Unknown error trying to find model"
        raise NotFoundError(
            requests.exceptions.HTTPError(
                msg,
                response=requests.Response(),  # Empty response since we didn't make a direct request
            )
        )

    def info(self, return_request: bool = False) -> Union[List[Dict[str, Any]], requests.Request]:
        """
        Get detailed information about all models from the server.

        Args:
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[List[Dict[str, Any]], requests.Request]: Either a list of model information dictionaries
            or a prepared request object if return_request is True

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/v1/model/info"
        request = requests.Request("GET", url, headers=self._get_headers())

        if return_request:
            return request

        # Prepare and send the request
        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()["data"]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            raise

    def update(
        self,
        model_id: str,
        model_params: Dict[str, Any],
        model_info: Optional[Dict[str, Any]] = None,
        return_request: bool = False,
    ) -> Union[Dict[str, Any], requests.Request]:
        """
        Update an existing model's configuration.

        Args:
            model_id (str): ID of the model to update
            model_params (Dict[str, Any]): New parameters for the model (e.g., model type, api_base, api_key)
            model_info (Optional[Dict[str, Any]]): Additional information about the model
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[Dict[str, Any], requests.Request]: Either the response from the server or
            a prepared request object if return_request is True

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            NotFoundError: If the model is not found
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/model/update"

        data = {
            "id": model_id,
            "litellm_params": model_params,
        }
        if model_info:
            data["model_info"] = model_info

        request = requests.Request("POST", url, headers=self._get_headers(), json=data)

        if return_request:
            return request

        # Prepare and send the request
        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            if e.response.status_code == 404 or "not found" in e.response.text.lower():
                raise NotFoundError(e)
            raise

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\response_api_endpoints\endpoints.py ===
from fastapi import APIRouter, Depends, Request, Response

from litellm.proxy._types import *
from litellm.proxy.auth.user_api_key_auth import UserAPIKeyAuth, user_api_key_auth
from litellm.proxy.common_request_processing import ProxyBaseLLMRequestProcessing

router = APIRouter()


@router.post(
    "/v1/responses",
    dependencies=[Depends(user_api_key_auth)],
    tags=["responses"],
)
@router.post(
    "/responses",
    dependencies=[Depends(user_api_key_auth)],
    tags=["responses"],
)
async def responses_api(
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Follows the OpenAI Responses API spec: https://platform.openai.com/docs/api-reference/responses

    ```bash
    curl -X POST http://localhost:4000/v1/responses \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer sk-1234" \
    -d '{
        "model": "gpt-4o",
        "input": "Tell me about AI"
    }'
    ```
    """
    from litellm.proxy.proxy_server import (
        _read_request_body,
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        select_data_generator,
        user_api_base,
        user_max_tokens,
        user_model,
        user_request_timeout,
        user_temperature,
        version,
    )

    data = await _read_request_body(request=request)
    processor = ProxyBaseLLMRequestProcessing(data=data)
    try:
        return await processor.base_process_llm_request(
            request=request,
            fastapi_response=fastapi_response,
            user_api_key_dict=user_api_key_dict,
            route_type="aresponses",
            proxy_logging_obj=proxy_logging_obj,
            llm_router=llm_router,
            general_settings=general_settings,
            proxy_config=proxy_config,
            select_data_generator=select_data_generator,
            model=None,
            user_model=user_model,
            user_temperature=user_temperature,
            user_request_timeout=user_request_timeout,
            user_max_tokens=user_max_tokens,
            user_api_base=user_api_base,
            version=version,
        )
    except Exception as e:
        raise await processor._handle_llm_api_exception(
            e=e,
            user_api_key_dict=user_api_key_dict,
            proxy_logging_obj=proxy_logging_obj,
            version=version,
        )


@router.get(
    "/v1/responses/{response_id}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["responses"],
)
@router.get(
    "/responses/{response_id}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["responses"],
)
async def get_response(
    response_id: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get a response by ID.
    
    Follows the OpenAI Responses API spec: https://platform.openai.com/docs/api-reference/responses/get
    
    ```bash
    curl -X GET http://localhost:4000/v1/responses/resp_abc123 \
    -H "Authorization: Bearer sk-1234"
    ```
    """
    from litellm.proxy.proxy_server import (
        _read_request_body,
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        select_data_generator,
        user_api_base,
        user_max_tokens,
        user_model,
        user_request_timeout,
        user_temperature,
        version,
    )

    data = await _read_request_body(request=request)
    data["response_id"] = response_id
    processor = ProxyBaseLLMRequestProcessing(data=data)
    try:
        return await processor.base_process_llm_request(
            request=request,
            fastapi_response=fastapi_response,
            user_api_key_dict=user_api_key_dict,
            route_type="aget_responses",
            proxy_logging_obj=proxy_logging_obj,
            llm_router=llm_router,
            general_settings=general_settings,
            proxy_config=proxy_config,
            select_data_generator=select_data_generator,
            model=None,
            user_model=user_model,
            user_temperature=user_temperature,
            user_request_timeout=user_request_timeout,
            user_max_tokens=user_max_tokens,
            user_api_base=user_api_base,
            version=version,
        )
    except Exception as e:
        raise await processor._handle_llm_api_exception(
            e=e,
            user_api_key_dict=user_api_key_dict,
            proxy_logging_obj=proxy_logging_obj,
            version=version,
        )


@router.delete(
    "/v1/responses/{response_id}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["responses"],
)
@router.delete(
    "/responses/{response_id}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["responses"],
)
async def delete_response(
    response_id: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Delete a response by ID.
    
    Follows the OpenAI Responses API spec: https://platform.openai.com/docs/api-reference/responses/delete
    
    ```bash
    curl -X DELETE http://localhost:4000/v1/responses/resp_abc123 \
    -H "Authorization: Bearer sk-1234"
    ```
    """
    from litellm.proxy.proxy_server import (
        _read_request_body,
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        select_data_generator,
        user_api_base,
        user_max_tokens,
        user_model,
        user_request_timeout,
        user_temperature,
        version,
    )

    data = await _read_request_body(request=request)
    data["response_id"] = response_id
    processor = ProxyBaseLLMRequestProcessing(data=data)
    try:
        return await processor.base_process_llm_request(
            request=request,
            fastapi_response=fastapi_response,
            user_api_key_dict=user_api_key_dict,
            route_type="adelete_responses",
            proxy_logging_obj=proxy_logging_obj,
            llm_router=llm_router,
            general_settings=general_settings,
            proxy_config=proxy_config,
            select_data_generator=select_data_generator,
            model=None,
            user_model=user_model,
            user_temperature=user_temperature,
            user_request_timeout=user_request_timeout,
            user_max_tokens=user_max_tokens,
            user_api_base=user_api_base,
            version=version,
        )
    except Exception as e:
        raise await processor._handle_llm_api_exception(
            e=e,
            user_api_key_dict=user_api_key_dict,
            proxy_logging_obj=proxy_logging_obj,
            version=version,
        )


@router.get(
    "/v1/responses/{response_id}/input_items",
    dependencies=[Depends(user_api_key_auth)],
    tags=["responses"],
)
@router.get(
    "/responses/{response_id}/input_items",
    dependencies=[Depends(user_api_key_auth)],
    tags=["responses"],
)
async def get_response_input_items(
    response_id: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """List input items for a response."""
    from litellm.proxy.proxy_server import (
        _read_request_body,
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        select_data_generator,
        user_api_base,
        user_max_tokens,
        user_model,
        user_request_timeout,
        user_temperature,
        version,
    )

    data = await _read_request_body(request=request)
    data["response_id"] = response_id
    processor = ProxyBaseLLMRequestProcessing(data=data)
    try:
        return await processor.base_process_llm_request(
            request=request,
            fastapi_response=fastapi_response,
            user_api_key_dict=user_api_key_dict,
            route_type="alist_input_items",
            proxy_logging_obj=proxy_logging_obj,
            llm_router=llm_router,
            general_settings=general_settings,
            proxy_config=proxy_config,
            select_data_generator=select_data_generator,
            model=None,
            user_model=user_model,
            user_temperature=user_temperature,
            user_request_timeout=user_request_timeout,
            user_max_tokens=user_max_tokens,
            user_api_base=user_api_base,
            version=version,
        )
    except Exception as e:
        raise await processor._handle_llm_api_exception(
            e=e,
            user_api_key_dict=user_api_key_dict,
            proxy_logging_obj=proxy_logging_obj,
            version=version,
        )

# === NexusCore/openenv\Lib\site-packages\openai\lib\streaming\__init__.py ===
from ._assistants import (
    AssistantEventHandler as AssistantEventHandler,
    AssistantEventHandlerT as AssistantEventHandlerT,
    AssistantStreamManager as AssistantStreamManager,
    AsyncAssistantEventHandler as AsyncAssistantEventHandler,
    AsyncAssistantEventHandlerT as AsyncAssistantEventHandlerT,
    AsyncAssistantStreamManager as AsyncAssistantStreamManager,
)

# === NexusCore/openenv\Lib\site-packages\win32\lib\afxres.py ===
import warnings

from pywin.mfc.afxres import *

warnings.warn(
    "Importing the global `afxres` module is deprecated. Import from `pywin.mfc.afxres` instead.",
    category=DeprecationWarning,
)

# === NexusCore/openenv\Lib\site-packages\win32\lib\winxptheme.py ===
"""A useful wrapper around the "_winxptheme" module.

Originally used when we couldn't be sure Windows XP apis were going to
be available. In 2022, it's safe to assume they are, so this is just a wrapper
around _winxptheme.
"""

from _winxptheme import *  # nopycln: import

# === NexusCore/openenv\Lib\site-packages\PIL\ImagePalette.py ===
#
# The Python Imaging Library.
# $Id$
#
# image palette object
#
# History:
# 1996-03-11 fl   Rewritten.
# 1997-01-03 fl   Up and running.
# 1997-08-23 fl   Added load hack
# 2001-04-16 fl   Fixed randint shadow bug in random()
#
# Copyright (c) 1997-2001 by Secret Labs AB
# Copyright (c) 1996-1997 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import array
from collections.abc import Sequence
from typing import IO

from . import GimpGradientFile, GimpPaletteFile, ImageColor, PaletteFile

TYPE_CHECKING = False
if TYPE_CHECKING:
    from . import Image


class ImagePalette:
    """
    Color palette for palette mapped images

    :param mode: The mode to use for the palette. See:
        :ref:`concept-modes`. Defaults to "RGB"
    :param palette: An optional palette. If given, it must be a bytearray,
        an array or a list of ints between 0-255. The list must consist of
        all channels for one color followed by the next color (e.g. RGBRGBRGB).
        Defaults to an empty palette.
    """

    def __init__(
        self,
        mode: str = "RGB",
        palette: Sequence[int] | bytes | bytearray | None = None,
    ) -> None:
        self.mode = mode
        self.rawmode: str | None = None  # if set, palette contains raw data
        self.palette = palette or bytearray()
        self.dirty: int | None = None

    @property
    def palette(self) -> Sequence[int] | bytes | bytearray:
        return self._palette

    @palette.setter
    def palette(self, palette: Sequence[int] | bytes | bytearray) -> None:
        self._colors: dict[tuple[int, ...], int] | None = None
        self._palette = palette

    @property
    def colors(self) -> dict[tuple[int, ...], int]:
        if self._colors is None:
            mode_len = len(self.mode)
            self._colors = {}
            for i in range(0, len(self.palette), mode_len):
                color = tuple(self.palette[i : i + mode_len])
                if color in self._colors:
                    continue
                self._colors[color] = i // mode_len
        return self._colors

    @colors.setter
    def colors(self, colors: dict[tuple[int, ...], int]) -> None:
        self._colors = colors

    def copy(self) -> ImagePalette:
        new = ImagePalette()

        new.mode = self.mode
        new.rawmode = self.rawmode
        if self.palette is not None:
            new.palette = self.palette[:]
        new.dirty = self.dirty

        return new

    def getdata(self) -> tuple[str, Sequence[int] | bytes | bytearray]:
        """
        Get palette contents in format suitable for the low-level
        ``im.putpalette`` primitive.

        .. warning:: This method is experimental.
        """
        if self.rawmode:
            return self.rawmode, self.palette
        return self.mode, self.tobytes()

    def tobytes(self) -> bytes:
        """Convert palette to bytes.

        .. warning:: This method is experimental.
        """
        if self.rawmode:
            msg = "palette contains raw palette data"
            raise ValueError(msg)
        if isinstance(self.palette, bytes):
            return self.palette
        arr = array.array("B", self.palette)
        return arr.tobytes()

    # Declare tostring as an alias for tobytes
    tostring = tobytes

    def _new_color_index(
        self, image: Image.Image | None = None, e: Exception | None = None
    ) -> int:
        if not isinstance(self.palette, bytearray):
            self._palette = bytearray(self.palette)
        index = len(self.palette) // 3
        special_colors: tuple[int | tuple[int, ...] | None, ...] = ()
        if image:
            special_colors = (
                image.info.get("background"),
                image.info.get("transparency"),
            )
            while index in special_colors:
                index += 1
        if index >= 256:
            if image:
                # Search for an unused index
                for i, count in reversed(list(enumerate(image.histogram()))):
                    if count == 0 and i not in special_colors:
                        index = i
                        break
            if index >= 256:
                msg = "cannot allocate more than 256 colors"
                raise ValueError(msg) from e
        return index

    def getcolor(
        self,
        color: tuple[int, ...],
        image: Image.Image | None = None,
    ) -> int:
        """Given an rgb tuple, allocate palette entry.

        .. warning:: This method is experimental.
        """
        if self.rawmode:
            msg = "palette contains raw palette data"
            raise ValueError(msg)
        if isinstance(color, tuple):
            if self.mode == "RGB":
                if len(color) == 4:
                    if color[3] != 255:
                        msg = "cannot add non-opaque RGBA color to RGB palette"
                        raise ValueError(msg)
                    color = color[:3]
            elif self.mode == "RGBA":
                if len(color) == 3:
                    color += (255,)
            try:
                return self.colors[color]
            except KeyError as e:
                # allocate new color slot
                index = self._new_color_index(image, e)
                assert isinstance(self._palette, bytearray)
                self.colors[color] = index
                if index * 3 < len(self.palette):
                    self._palette = (
                        self._palette[: index * 3]
                        + bytes(color)
                        + self._palette[index * 3 + 3 :]
                    )
                else:
                    self._palette += bytes(color)
                self.dirty = 1
                return index
        else:
            msg = f"unknown color specifier: {repr(color)}"  # type: ignore[unreachable]
            raise ValueError(msg)

    def save(self, fp: str | IO[str]) -> None:
        """Save palette to text file.

        .. warning:: This method is experimental.
        """
        if self.rawmode:
            msg = "palette contains raw palette data"
            raise ValueError(msg)
        if isinstance(fp, str):
            fp = open(fp, "w")
        fp.write("# Palette\n")
        fp.write(f"# Mode: {self.mode}\n")
        for i in range(256):
            fp.write(f"{i}")
            for j in range(i * len(self.mode), (i + 1) * len(self.mode)):
                try:
                    fp.write(f" {self.palette[j]}")
                except IndexError:
                    fp.write(" 0")
            fp.write("\n")
        fp.close()


# --------------------------------------------------------------------
# Internal


def raw(rawmode: str, data: Sequence[int] | bytes | bytearray) -> ImagePalette:
    palette = ImagePalette()
    palette.rawmode = rawmode
    palette.palette = data
    palette.dirty = 1
    return palette


# --------------------------------------------------------------------
# Factories


def make_linear_lut(black: int, white: float) -> list[int]:
    if black == 0:
        return [int(white * i // 255) for i in range(256)]

    msg = "unavailable when black is non-zero"
    raise NotImplementedError(msg)  # FIXME


def make_gamma_lut(exp: float) -> list[int]:
    return [int(((i / 255.0) ** exp) * 255.0 + 0.5) for i in range(256)]


def negative(mode: str = "RGB") -> ImagePalette:
    palette = list(range(256 * len(mode)))
    palette.reverse()
    return ImagePalette(mode, [i // len(mode) for i in palette])


def random(mode: str = "RGB") -> ImagePalette:
    from random import randint

    palette = [randint(0, 255) for _ in range(256 * len(mode))]
    return ImagePalette(mode, palette)


def sepia(white: str = "#fff0c0") -> ImagePalette:
    bands = [make_linear_lut(0, band) for band in ImageColor.getrgb(white)]
    return ImagePalette("RGB", [bands[i % 3][i // 3] for i in range(256 * 3)])


def wedge(mode: str = "RGB") -> ImagePalette:
    palette = list(range(256 * len(mode)))
    return ImagePalette(mode, [i // len(mode) for i in palette])


def load(filename: str) -> tuple[bytes, str]:
    # FIXME: supports GIMP gradients only

    with open(filename, "rb") as fp:
        paletteHandlers: list[
            type[
                GimpPaletteFile.GimpPaletteFile
                | GimpGradientFile.GimpGradientFile
                | PaletteFile.PaletteFile
            ]
        ] = [
            GimpPaletteFile.GimpPaletteFile,
            GimpGradientFile.GimpGradientFile,
            PaletteFile.PaletteFile,
        ]
        for paletteHandler in paletteHandlers:
            try:
                fp.seek(0)
                lut = paletteHandler(fp).getpalette()
                if lut:
                    break
            except (SyntaxError, ValueError):
                pass
        else:
            msg = "cannot load palette"
            raise OSError(msg)

    return lut  # data, rawmode

# === NexusCore/openenv\Lib\site-packages\google\oauth2\_client_async.py ===
# Copyright 2020 Google LLC
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

"""OAuth 2.0 async client.

This is a client for interacting with an OAuth 2.0 authorization server's
token endpoint.

For more information about the token endpoint, see
`Section 3.1 of rfc6749`_

.. _Section 3.1 of rfc6749: https://tools.ietf.org/html/rfc6749#section-3.2
"""

import datetime
import http.client as http_client
import json
import urllib

from google.auth import _exponential_backoff
from google.auth import exceptions
from google.auth import jwt
from google.oauth2 import _client as client


async def _token_endpoint_request_no_throw(
    request, token_uri, body, access_token=None, use_json=False, can_retry=True
):
    """Makes a request to the OAuth 2.0 authorization server's token endpoint.
    This function doesn't throw on response errors.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        body (Mapping[str, str]): The parameters to send in the request body.
        access_token (Optional(str)): The access token needed to make the request.
        use_json (Optional(bool)): Use urlencoded format or json format for the
            content type. The default value is False.
        can_retry (bool): Enable or disable request retry behavior.

    Returns:
        Tuple(bool, Mapping[str, str], Optional[bool]): A boolean indicating
          if the request is successful, a mapping for the JSON-decoded response
          data and in the case of an error a boolean indicating if the error
          is retryable.
    """
    if use_json:
        headers = {"Content-Type": client._JSON_CONTENT_TYPE}
        body = json.dumps(body).encode("utf-8")
    else:
        headers = {"Content-Type": client._URLENCODED_CONTENT_TYPE}
        body = urllib.parse.urlencode(body).encode("utf-8")

    if access_token:
        headers["Authorization"] = "Bearer {}".format(access_token)

    response_data = {}
    retryable_error = False

    retries = _exponential_backoff.ExponentialBackoff()
    for _ in retries:
        response = await request(
            method="POST", url=token_uri, headers=headers, body=body
        )

        # Using data.read() resulted in zlib decompression errors. This may require future investigation.
        response_body1 = await response.content()

        response_body = (
            response_body1.decode("utf-8")
            if hasattr(response_body1, "decode")
            else response_body1
        )

        try:
            response_data = json.loads(response_body)
        except ValueError:
            response_data = response_body

        if response.status == http_client.OK:
            return True, response_data, None

        retryable_error = client._can_retry(
            status_code=response.status, response_data=response_data
        )

        if not can_retry or not retryable_error:
            return False, response_data, retryable_error

    return False, response_data, retryable_error


async def _token_endpoint_request(
    request, token_uri, body, access_token=None, use_json=False, can_retry=True
):
    """Makes a request to the OAuth 2.0 authorization server's token endpoint.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        body (Mapping[str, str]): The parameters to send in the request body.
        access_token (Optional(str)): The access token needed to make the request.
        use_json (Optional(bool)): Use urlencoded format or json format for the
            content type. The default value is False.
        can_retry (bool): Enable or disable request retry behavior.

    Returns:
        Mapping[str, str]: The JSON-decoded response data.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.
    """

    response_status_ok, response_data, retryable_error = await _token_endpoint_request_no_throw(
        request,
        token_uri,
        body,
        access_token=access_token,
        use_json=use_json,
        can_retry=can_retry,
    )
    if not response_status_ok:
        client._handle_error_response(response_data, retryable_error)
    return response_data


async def jwt_grant(request, token_uri, assertion, can_retry=True):
    """Implements the JWT Profile for OAuth 2.0 Authorization Grants.

    For more details, see `rfc7523 section 4`_.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        assertion (str): The OAuth 2.0 assertion.
        can_retry (bool): Enable or disable request retry behavior.

    Returns:
        Tuple[str, Optional[datetime], Mapping[str, str]]: The access token,
            expiration, and additional data returned by the token endpoint.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.

    .. _rfc7523 section 4: https://tools.ietf.org/html/rfc7523#section-4
    """
    body = {"assertion": assertion, "grant_type": client._JWT_GRANT_TYPE}

    response_data = await _token_endpoint_request(
        request, token_uri, body, can_retry=can_retry
    )

    try:
        access_token = response_data["access_token"]
    except KeyError as caught_exc:
        new_exc = exceptions.RefreshError(
            "No access token in response.", response_data, retryable=False
        )
        raise new_exc from caught_exc

    expiry = client._parse_expiry(response_data)

    return access_token, expiry, response_data


async def id_token_jwt_grant(request, token_uri, assertion, can_retry=True):
    """Implements the JWT Profile for OAuth 2.0 Authorization Grants, but
    requests an OpenID Connect ID Token instead of an access token.

    This is a variant on the standard JWT Profile that is currently unique
    to Google. This was added for the benefit of authenticating to services
    that require ID Tokens instead of access tokens or JWT bearer tokens.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorization server's token endpoint
            URI.
        assertion (str): JWT token signed by a service account. The token's
            payload must include a ``target_audience`` claim.
        can_retry (bool): Enable or disable request retry behavior.

    Returns:
        Tuple[str, Optional[datetime], Mapping[str, str]]:
            The (encoded) Open ID Connect ID Token, expiration, and additional
            data returned by the endpoint.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.
    """
    body = {"assertion": assertion, "grant_type": client._JWT_GRANT_TYPE}

    response_data = await _token_endpoint_request(
        request, token_uri, body, can_retry=can_retry
    )

    try:
        id_token = response_data["id_token"]
    except KeyError as caught_exc:
        new_exc = exceptions.RefreshError(
            "No ID token in response.", response_data, retryable=False
        )
        raise new_exc from caught_exc

    payload = jwt.decode(id_token, verify=False)
    expiry = datetime.datetime.utcfromtimestamp(payload["exp"])

    return id_token, expiry, response_data


async def refresh_grant(
    request,
    token_uri,
    refresh_token,
    client_id,
    client_secret,
    scopes=None,
    rapt_token=None,
    can_retry=True,
):
    """Implements the OAuth 2.0 refresh token grant.

    For more details, see `rfc678 section 6`_.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        refresh_token (str): The refresh token to use to get a new access
            token.
        client_id (str): The OAuth 2.0 application's client ID.
        client_secret (str): The Oauth 2.0 appliaction's client secret.
        scopes (Optional(Sequence[str])): Scopes to request. If present, all
            scopes must be authorized for the refresh token. Useful if refresh
            token has a wild card scope (e.g.
            'https://www.googleapis.com/auth/any-api').
        rapt_token (Optional(str)): The reauth Proof Token.
        can_retry (bool): Enable or disable request retry behavior.

    Returns:
        Tuple[str, Optional[str], Optional[datetime], Mapping[str, str]]: The
            access token, new or current refresh token, expiration, and additional data
            returned by the token endpoint.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.

    .. _rfc6748 section 6: https://tools.ietf.org/html/rfc6749#section-6
    """
    body = {
        "grant_type": client._REFRESH_GRANT_TYPE,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    if scopes:
        body["scope"] = " ".join(scopes)
    if rapt_token:
        body["rapt"] = rapt_token

    response_data = await _token_endpoint_request(
        request, token_uri, body, can_retry=can_retry
    )
    return client._handle_refresh_grant_response(response_data, refresh_token)

# === NexusCore/openenv\Lib\site-packages\google\generativeai\types\palm_safety_types.py ===
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

from collections.abc import Mapping

import enum
import typing
from typing import Dict, Iterable, List, Union

from typing_extensions import TypedDict


from google.generativeai import protos
from google.generativeai import string_utils


__all__ = [
    "HarmCategory",
    "HarmProbability",
    "HarmBlockThreshold",
    "BlockedReason",
    "ContentFilterDict",
    "SafetyRatingDict",
    "SafetySettingDict",
    "SafetyFeedbackDict",
]

# These are basic python enums, it's okay to expose them
HarmProbability = protos.SafetyRating.HarmProbability
HarmBlockThreshold = protos.SafetySetting.HarmBlockThreshold
BlockedReason = protos.ContentFilter.BlockedReason


class HarmCategory:
    """
    Harm Categories supported by the palm-family models
    """

    HARM_CATEGORY_UNSPECIFIED = protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED.value
    HARM_CATEGORY_DEROGATORY = protos.HarmCategory.HARM_CATEGORY_DEROGATORY.value
    HARM_CATEGORY_TOXICITY = protos.HarmCategory.HARM_CATEGORY_TOXICITY.value
    HARM_CATEGORY_VIOLENCE = protos.HarmCategory.HARM_CATEGORY_VIOLENCE.value
    HARM_CATEGORY_SEXUAL = protos.HarmCategory.HARM_CATEGORY_SEXUAL.value
    HARM_CATEGORY_MEDICAL = protos.HarmCategory.HARM_CATEGORY_MEDICAL.value
    HARM_CATEGORY_DANGEROUS = protos.HarmCategory.HARM_CATEGORY_DANGEROUS.value


HarmCategoryOptions = Union[str, int, HarmCategory]

# fmt: off
_HARM_CATEGORIES: Dict[HarmCategoryOptions, protos.HarmCategory] = {
    protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED: protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
    0: protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
    "harm_category_unspecified": protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
    "unspecified": protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED,

    protos.HarmCategory.HARM_CATEGORY_DEROGATORY: protos.HarmCategory.HARM_CATEGORY_DEROGATORY,
    HarmCategory.HARM_CATEGORY_DEROGATORY: protos.HarmCategory.HARM_CATEGORY_DEROGATORY,
    1: protos.HarmCategory.HARM_CATEGORY_DEROGATORY,
    "harm_category_derogatory": protos.HarmCategory.HARM_CATEGORY_DEROGATORY,
    "derogatory": protos.HarmCategory.HARM_CATEGORY_DEROGATORY,

    protos.HarmCategory.HARM_CATEGORY_TOXICITY: protos.HarmCategory.HARM_CATEGORY_TOXICITY,
    HarmCategory.HARM_CATEGORY_TOXICITY: protos.HarmCategory.HARM_CATEGORY_TOXICITY,
    2: protos.HarmCategory.HARM_CATEGORY_TOXICITY,
    "harm_category_toxicity": protos.HarmCategory.HARM_CATEGORY_TOXICITY,
    "toxicity": protos.HarmCategory.HARM_CATEGORY_TOXICITY,
    "toxic": protos.HarmCategory.HARM_CATEGORY_TOXICITY,

    protos.HarmCategory.HARM_CATEGORY_VIOLENCE: protos.HarmCategory.HARM_CATEGORY_VIOLENCE,
    HarmCategory.HARM_CATEGORY_VIOLENCE: protos.HarmCategory.HARM_CATEGORY_VIOLENCE,
    3: protos.HarmCategory.HARM_CATEGORY_VIOLENCE,
    "harm_category_violence": protos.HarmCategory.HARM_CATEGORY_VIOLENCE,
    "violence": protos.HarmCategory.HARM_CATEGORY_VIOLENCE,
    "violent": protos.HarmCategory.HARM_CATEGORY_VIOLENCE,

    protos.HarmCategory.HARM_CATEGORY_SEXUAL: protos.HarmCategory.HARM_CATEGORY_SEXUAL,
    HarmCategory.HARM_CATEGORY_SEXUAL: protos.HarmCategory.HARM_CATEGORY_SEXUAL,
    4: protos.HarmCategory.HARM_CATEGORY_SEXUAL,
    "harm_category_sexual": protos.HarmCategory.HARM_CATEGORY_SEXUAL,
    "sexual": protos.HarmCategory.HARM_CATEGORY_SEXUAL,
    "sex": protos.HarmCategory.HARM_CATEGORY_SEXUAL,

    protos.HarmCategory.HARM_CATEGORY_MEDICAL: protos.HarmCategory.HARM_CATEGORY_MEDICAL,
    HarmCategory.HARM_CATEGORY_MEDICAL: protos.HarmCategory.HARM_CATEGORY_MEDICAL,
    5: protos.HarmCategory.HARM_CATEGORY_MEDICAL,
    "harm_category_medical": protos.HarmCategory.HARM_CATEGORY_MEDICAL,
    "medical": protos.HarmCategory.HARM_CATEGORY_MEDICAL,
    "med": protos.HarmCategory.HARM_CATEGORY_MEDICAL,

    protos.HarmCategory.HARM_CATEGORY_DANGEROUS: protos.HarmCategory.HARM_CATEGORY_DANGEROUS,
    HarmCategory.HARM_CATEGORY_DANGEROUS: protos.HarmCategory.HARM_CATEGORY_DANGEROUS,
    6: protos.HarmCategory.HARM_CATEGORY_DANGEROUS,
    "harm_category_dangerous": protos.HarmCategory.HARM_CATEGORY_DANGEROUS,
    "dangerous": protos.HarmCategory.HARM_CATEGORY_DANGEROUS,
    "danger": protos.HarmCategory.HARM_CATEGORY_DANGEROUS,
}
# fmt: on


def to_harm_category(x: HarmCategoryOptions) -> protos.HarmCategory:
    if isinstance(x, str):
        x = x.lower()
    return _HARM_CATEGORIES[x]


HarmBlockThresholdOptions = Union[str, int, HarmBlockThreshold]

# fmt: off
_BLOCK_THRESHOLDS: Dict[HarmBlockThresholdOptions, HarmBlockThreshold] = {
    HarmBlockThreshold.HARM_BLOCK_THRESHOLD_UNSPECIFIED: HarmBlockThreshold.HARM_BLOCK_THRESHOLD_UNSPECIFIED,
    0: HarmBlockThreshold.HARM_BLOCK_THRESHOLD_UNSPECIFIED,
    "harm_block_threshold_unspecified": HarmBlockThreshold.HARM_BLOCK_THRESHOLD_UNSPECIFIED,
    "block_threshold_unspecified": HarmBlockThreshold.HARM_BLOCK_THRESHOLD_UNSPECIFIED,
    "unspecified": HarmBlockThreshold.HARM_BLOCK_THRESHOLD_UNSPECIFIED,

    HarmBlockThreshold.BLOCK_LOW_AND_ABOVE: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    1: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    "block_low_and_above": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    "low": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,

    HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    2: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "block_medium_and_above": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "medium": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "med": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,

    HarmBlockThreshold.BLOCK_ONLY_HIGH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    3: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "block_only_high": HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "high": HarmBlockThreshold.BLOCK_ONLY_HIGH,

    HarmBlockThreshold.BLOCK_NONE: HarmBlockThreshold.BLOCK_NONE,
    4: HarmBlockThreshold.BLOCK_NONE,
    "block_none": HarmBlockThreshold.BLOCK_NONE,
}
# fmt: on


def to_block_threshold(x: HarmBlockThresholdOptions) -> HarmBlockThreshold:
    if isinstance(x, str):
        x = x.lower()
    return _BLOCK_THRESHOLDS[x]


class ContentFilterDict(TypedDict):
    reason: BlockedReason
    message: str

    __doc__ = string_utils.strip_oneof(protos.ContentFilter.__doc__)


def convert_filters_to_enums(
    filters: Iterable[dict],
) -> List[ContentFilterDict]:
    result = []
    for f in filters:
        f = f.copy()
        f["reason"] = BlockedReason(f["reason"])
        f = typing.cast(ContentFilterDict, f)
        result.append(f)
    return result


class SafetyRatingDict(TypedDict):
    category: protos.HarmCategory
    probability: HarmProbability

    __doc__ = string_utils.strip_oneof(protos.SafetyRating.__doc__)


def convert_rating_to_enum(rating: dict) -> SafetyRatingDict:
    return {
        "category": protos.HarmCategory(rating["category"]),
        "probability": HarmProbability(rating["probability"]),
    }


def convert_ratings_to_enum(ratings: Iterable[dict]) -> List[SafetyRatingDict]:
    result = []
    for r in ratings:
        result.append(convert_rating_to_enum(r))
    return result


class SafetySettingDict(TypedDict):
    category: protos.HarmCategory
    threshold: HarmBlockThreshold

    __doc__ = string_utils.strip_oneof(protos.SafetySetting.__doc__)


class LooseSafetySettingDict(TypedDict):
    category: HarmCategoryOptions
    threshold: HarmBlockThresholdOptions


EasySafetySetting = Mapping[HarmCategoryOptions, HarmBlockThresholdOptions]
EasySafetySettingDict = dict[HarmCategoryOptions, HarmBlockThresholdOptions]

SafetySettingOptions = Union[EasySafetySetting, Iterable[LooseSafetySettingDict], None]


def to_easy_safety_dict(settings: SafetySettingOptions) -> EasySafetySettingDict:
    if settings is None:
        return {}
    elif isinstance(settings, Mapping):
        return {to_harm_category(key): to_block_threshold(value) for key, value in settings.items()}
    else:  # Iterable
        return {
            to_harm_category(d["category"]): to_block_threshold(d["threshold"]) for d in settings
        }


def normalize_safety_settings(
    settings: SafetySettingOptions,
) -> list[SafetySettingDict] | None:
    if settings is None:
        return None
    if isinstance(settings, Mapping):
        return [
            {
                "category": to_harm_category(key),
                "threshold": to_block_threshold(value),
            }
            for key, value in settings.items()
        ]
    else:
        return [
            {
                "category": to_harm_category(d["category"]),
                "threshold": to_block_threshold(d["threshold"]),
            }
            for d in settings
        ]


def convert_setting_to_enum(setting: dict) -> SafetySettingDict:
    return {
        "category": protos.HarmCategory(setting["category"]),
        "threshold": HarmBlockThreshold(setting["threshold"]),
    }


class SafetyFeedbackDict(TypedDict):
    rating: SafetyRatingDict
    setting: SafetySettingDict

    __doc__ = string_utils.strip_oneof(protos.SafetyFeedback.__doc__)


def convert_safety_feedback_to_enums(
    safety_feedback: Iterable[dict],
) -> List[SafetyFeedbackDict]:
    result = []
    for sf in safety_feedback:
        result.append(
            {
                "rating": convert_rating_to_enum(sf["rating"]),
                "setting": convert_setting_to_enum(sf["setting"]),
            }
        )
    return result


def convert_candidate_enums(candidates):
    result = []
    for candidate in candidates:
        candidate = candidate.copy()
        candidate["safety_ratings"] = convert_ratings_to_enum(candidate["safety_ratings"])
        result.append(candidate)
    return result

# === NexusCore/openenv\Lib\site-packages\jedi\inference\docstrings.py ===
"""
Docstrings are another source of information for functions and classes.
:mod:`jedi.inference.dynamic_params` tries to find all executions of functions,
while the docstring parsing is much easier. There are three different types of
docstrings that |jedi| understands:

- `Sphinx <http://sphinx-doc.org/markup/desc.html#info-field-lists>`_
- `Epydoc <http://epydoc.sourceforge.net/manual-fields.html>`_
- `Numpydoc <https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt>`_

For example, the sphinx annotation ``:type foo: str`` clearly states that the
type of ``foo`` is ``str``.

As an addition to parameter searching, this module also provides return
annotations.
"""

import re
import warnings

from parso import parse, ParserSyntaxError

from jedi import debug
from jedi.inference.cache import inference_state_method_cache
from jedi.inference.base_value import iterator_to_value_set, ValueSet, \
    NO_VALUES
from jedi.inference.lazy_value import LazyKnownValues


DOCSTRING_PARAM_PATTERNS = [
    r'\s*:type\s+%s:\s*([^\n]+)',  # Sphinx
    r'\s*:param\s+(\w+)\s+%s:[^\n]*',  # Sphinx param with type
    r'\s*@type\s+%s:\s*([^\n]+)',  # Epydoc
]

DOCSTRING_RETURN_PATTERNS = [
    re.compile(r'\s*:rtype:\s*([^\n]+)', re.M),  # Sphinx
    re.compile(r'\s*@rtype:\s*([^\n]+)', re.M),  # Epydoc
]

REST_ROLE_PATTERN = re.compile(r':[^`]+:`([^`]+)`')


_numpy_doc_string_cache = None


def _get_numpy_doc_string_cls():
    global _numpy_doc_string_cache
    if isinstance(_numpy_doc_string_cache, (ImportError, SyntaxError)):
        raise _numpy_doc_string_cache
    from numpydoc.docscrape import NumpyDocString  # type: ignore[import]
    _numpy_doc_string_cache = NumpyDocString
    return _numpy_doc_string_cache


def _search_param_in_numpydocstr(docstr, param_str):
    """Search `docstr` (in numpydoc format) for type(-s) of `param_str`."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            # This is a non-public API. If it ever changes we should be
            # prepared and return gracefully.
            params = _get_numpy_doc_string_cls()(docstr)._parsed_data['Parameters']
        except Exception:
            return []
    for p_name, p_type, p_descr in params:
        if p_name == param_str:
            m = re.match(r'([^,]+(,[^,]+)*?)(,[ ]*optional)?$', p_type)
            if m:
                p_type = m.group(1)
            return list(_expand_typestr(p_type))
    return []


def _search_return_in_numpydocstr(docstr):
    """
    Search `docstr` (in numpydoc format) for type(-s) of function returns.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            doc = _get_numpy_doc_string_cls()(docstr)
        except Exception:
            return
    try:
        # This is a non-public API. If it ever changes we should be
        # prepared and return gracefully.
        returns = doc._parsed_data['Returns']
        returns += doc._parsed_data['Yields']
    except Exception:
        return
    for r_name, r_type, r_descr in returns:
        # Return names are optional and if so the type is in the name
        if not r_type:
            r_type = r_name
        yield from _expand_typestr(r_type)


def _expand_typestr(type_str):
    """
    Attempts to interpret the possible types in `type_str`
    """
    # Check if alternative types are specified with 'or'
    if re.search(r'\bor\b', type_str):
        for t in type_str.split('or'):
            yield t.split('of')[0].strip()
    # Check if like "list of `type`" and set type to list
    elif re.search(r'\bof\b', type_str):
        yield type_str.split('of')[0]
    # Check if type has is a set of valid literal values eg: {'C', 'F', 'A'}
    elif type_str.startswith('{'):
        node = parse(type_str, version='3.7').children[0]
        if node.type == 'atom':
            for leaf in getattr(node.children[1], "children", []):
                if leaf.type == 'number':
                    if '.' in leaf.value:
                        yield 'float'
                    else:
                        yield 'int'
                elif leaf.type == 'string':
                    if 'b' in leaf.string_prefix.lower():
                        yield 'bytes'
                    else:
                        yield 'str'
                # Ignore everything else.

    # Otherwise just work with what we have.
    else:
        yield type_str


def _search_param_in_docstr(docstr, param_str):
    """
    Search `docstr` for type(-s) of `param_str`.

    >>> _search_param_in_docstr(':type param: int', 'param')
    ['int']
    >>> _search_param_in_docstr('@type param: int', 'param')
    ['int']
    >>> _search_param_in_docstr(
    ...   ':type param: :class:`threading.Thread`', 'param')
    ['threading.Thread']
    >>> bool(_search_param_in_docstr('no document', 'param'))
    False
    >>> _search_param_in_docstr(':param int param: some description', 'param')
    ['int']

    """
    # look at #40 to see definitions of those params
    patterns = [re.compile(p % re.escape(param_str))
                for p in DOCSTRING_PARAM_PATTERNS]
    for pattern in patterns:
        match = pattern.search(docstr)
        if match:
            return [_strip_rst_role(match.group(1))]

    return _search_param_in_numpydocstr(docstr, param_str)


def _strip_rst_role(type_str):
    """
    Strip off the part looks like a ReST role in `type_str`.

    >>> _strip_rst_role(':class:`ClassName`')  # strip off :class:
    'ClassName'
    >>> _strip_rst_role(':py:obj:`module.Object`')  # works with domain
    'module.Object'
    >>> _strip_rst_role('ClassName')  # do nothing when not ReST role
    'ClassName'

    See also:
    http://sphinx-doc.org/domains.html#cross-referencing-python-objects

    """
    match = REST_ROLE_PATTERN.match(type_str)
    if match:
        return match.group(1)
    else:
        return type_str


def _infer_for_statement_string(module_context, string):
    if string is None:
        return []

    potential_imports = re.findall(r'((?:\w+\.)*\w+)\.', string)
    # Try to import module part in dotted name.
    # (e.g., 'threading' in 'threading.Thread').
    imports = "\n".join(f"import {p}" for p in potential_imports)
    string = f'{imports}\n{string}'

    debug.dbg('Parse docstring code %s', string, color='BLUE')
    grammar = module_context.inference_state.grammar
    try:
        module = grammar.parse(string, error_recovery=False)
    except ParserSyntaxError:
        return []
    try:
        # It's not the last item, because that's an end marker.
        stmt = module.children[-2]
    except (AttributeError, IndexError):
        return []

    if stmt.type not in ('name', 'atom', 'atom_expr'):
        return []

    # Here we basically use a fake module that also uses the filters in
    # the actual module.
    from jedi.inference.docstring_utils import DocstringModule
    m = DocstringModule(
        in_module_context=module_context,
        inference_state=module_context.inference_state,
        module_node=module,
        code_lines=[],
    )
    return list(_execute_types_in_stmt(m.as_context(), stmt))


def _execute_types_in_stmt(module_context, stmt):
    """
    Executing all types or general elements that we find in a statement. This
    doesn't include tuple, list and dict literals, because the stuff they
    contain is executed. (Used as type information).
    """
    definitions = module_context.infer_node(stmt)
    return ValueSet.from_sets(
        _execute_array_values(module_context.inference_state, d)
        for d in definitions
    )


def _execute_array_values(inference_state, array):
    """
    Tuples indicate that there's not just one return value, but the listed
    ones.  `(str, int)` means that it returns a tuple with both types.
    """
    from jedi.inference.value.iterable import SequenceLiteralValue, FakeTuple, FakeList
    if isinstance(array, SequenceLiteralValue) and array.array_type in ('tuple', 'list'):
        values = []
        for lazy_value in array.py__iter__():
            objects = ValueSet.from_sets(
                _execute_array_values(inference_state, typ)
                for typ in lazy_value.infer()
            )
            values.append(LazyKnownValues(objects))
        cls = FakeTuple if array.array_type == 'tuple' else FakeList
        return {cls(inference_state, values)}
    else:
        return array.execute_annotation()


@inference_state_method_cache()
def infer_param(function_value, param):
    def infer_docstring(docstring):
        return ValueSet(
            p
            for param_str in _search_param_in_docstr(docstring, param.name.value)
            for p in _infer_for_statement_string(module_context, param_str)
        )
    module_context = function_value.get_root_context()
    func = param.get_parent_function()
    if func.type == 'lambdef':
        return NO_VALUES

    types = infer_docstring(function_value.py__doc__())
    if function_value.is_bound_method() \
            and function_value.py__name__() == '__init__':
        types |= infer_docstring(function_value.class_context.py__doc__())

    debug.dbg('Found param types for docstring: %s', types, color='BLUE')
    return types


@inference_state_method_cache()
@iterator_to_value_set
def infer_return_types(function_value):
    def search_return_in_docstr(code):
        for p in DOCSTRING_RETURN_PATTERNS:
            match = p.search(code)
            if match:
                yield _strip_rst_role(match.group(1))
        # Check for numpy style return hint
        yield from _search_return_in_numpydocstr(code)

    for type_str in search_return_in_docstr(function_value.py__doc__()):
        yield from _infer_for_statement_string(function_value.get_root_context(), type_str)

# === NexusCore/openenv\Lib\site-packages\matplotlib\sphinxext\figmpl_directive.py ===
"""
Add a ``figure-mpl`` directive that is a responsive version of ``figure``.

This implementation is very similar to ``.. figure::``, except it also allows a
``srcset=`` argument to be passed to the image tag, hence allowing responsive
resolution images.

There is no particular reason this could not be used standalone, but is meant
to be used with :doc:`/api/sphinxext_plot_directive_api`.

Note that the directory organization is a bit different than ``.. figure::``.
See the *FigureMpl* documentation below.

"""
import os
from os.path import relpath
from pathlib import PurePath, Path
import shutil

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.images import Figure, Image
from sphinx.errors import ExtensionError

import matplotlib


class figmplnode(nodes.General, nodes.Element):
    pass


class FigureMpl(Figure):
    """
    Implements a directive to allow an optional hidpi image.

    Meant to be used with the *plot_srcset* configuration option in conf.py,
    and gets set in the TEMPLATE of plot_directive.py

    e.g.::

        .. figure-mpl:: plot_directive/some_plots-1.png
            :alt: bar
            :srcset: plot_directive/some_plots-1.png,
                     plot_directive/some_plots-1.2x.png 2.00x
            :class: plot-directive

    The resulting html (at ``some_plots.html``) is::

        <img src="sphx_glr_bar_001_hidpi.png"
            srcset="_images/some_plot-1.png,
                    _images/some_plots-1.2x.png 2.00x",
            alt="bar"
            class="plot_directive" />

    Note that the handling of subdirectories is different than that used by the sphinx
    figure directive::

        .. figure-mpl:: plot_directive/nestedpage/index-1.png
            :alt: bar
            :srcset: plot_directive/nestedpage/index-1.png
                     plot_directive/nestedpage/index-1.2x.png 2.00x
            :class: plot_directive

    The resulting html (at ``nestedpage/index.html``)::

        <img src="../_images/nestedpage-index-1.png"
            srcset="../_images/nestedpage-index-1.png,
                    ../_images/_images/nestedpage-index-1.2x.png 2.00x",
            alt="bar"
            class="sphx-glr-single-img" />

    where the subdirectory is included in the image name for uniqueness.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 2
    final_argument_whitespace = False
    option_spec = {
        'alt': directives.unchanged,
        'height': directives.length_or_unitless,
        'width': directives.length_or_percentage_or_unitless,
        'scale': directives.nonnegative_int,
        'align': Image.align,
        'class': directives.class_option,
        'caption': directives.unchanged,
        'srcset': directives.unchanged,
    }

    def run(self):

        image_node = figmplnode()

        imagenm = self.arguments[0]
        image_node['alt'] = self.options.get('alt', '')
        image_node['align'] = self.options.get('align', None)
        image_node['class'] = self.options.get('class', None)
        image_node['width'] = self.options.get('width', None)
        image_node['height'] = self.options.get('height', None)
        image_node['scale'] = self.options.get('scale', None)
        image_node['caption'] = self.options.get('caption', None)

        # we would like uri to be the highest dpi version so that
        # latex etc will use that.  But for now, lets just make
        # imagenm... maybe pdf one day?

        image_node['uri'] = imagenm
        image_node['srcset'] = self.options.get('srcset', None)

        return [image_node]


def _parse_srcsetNodes(st):
    """
    parse srcset...
    """
    entries = st.split(',')
    srcset = {}
    for entry in entries:
        spl = entry.strip().split(' ')
        if len(spl) == 1:
            srcset[0] = spl[0]
        elif len(spl) == 2:
            mult = spl[1][:-1]
            srcset[float(mult)] = spl[0]
        else:
            raise ExtensionError(f'srcset argument "{entry}" is invalid.')
    return srcset


def _copy_images_figmpl(self, node):

    # these will be the temporary place the plot-directive put the images eg:
    # ../../../build/html/plot_directive/users/explain/artists/index-1.png
    if node['srcset']:
        srcset = _parse_srcsetNodes(node['srcset'])
    else:
        srcset = None

    # the rst file's location:  eg /Users/username/matplotlib/doc/users/explain/artists
    docsource = PurePath(self.document['source']).parent

    # get the relpath relative to root:
    srctop = self.builder.srcdir
    rel = relpath(docsource, srctop).replace('.', '').replace(os.sep, '-')
    if len(rel):
        rel += '-'
    # eg: users/explain/artists

    imagedir = PurePath(self.builder.outdir, self.builder.imagedir)
    # eg: /Users/username/matplotlib/doc/build/html/_images/users/explain/artists

    Path(imagedir).mkdir(parents=True, exist_ok=True)

    # copy all the sources to the imagedir:
    if srcset:
        for src in srcset.values():
            # the entries in srcset are relative to docsource's directory
            abspath = PurePath(docsource, src)
            name = rel + abspath.name
            shutil.copyfile(abspath, imagedir / name)
    else:
        abspath = PurePath(docsource, node['uri'])
        name = rel + abspath.name
        shutil.copyfile(abspath, imagedir / name)

    return imagedir, srcset, rel


def visit_figmpl_html(self, node):

    imagedir, srcset, rel = _copy_images_figmpl(self, node)

    # /doc/examples/subd/plot_1.rst
    docsource = PurePath(self.document['source'])
    # /doc/
    # make sure to add the trailing slash:
    srctop = PurePath(self.builder.srcdir, '')
    # examples/subd/plot_1.rst
    relsource = relpath(docsource, srctop)
    # /doc/build/html
    desttop = PurePath(self.builder.outdir, '')
    # /doc/build/html/examples/subd
    dest = desttop / relsource

    # ../../_images/ for dirhtml and ../_images/ for html
    imagerel = PurePath(relpath(imagedir, dest.parent)).as_posix()
    if self.builder.name == "dirhtml":
        imagerel = f'..{imagerel}'

    # make uri also be relative...
    nm = PurePath(node['uri'][1:]).name
    uri = f'{imagerel}/{rel}{nm}'
    img_attrs = {'src': uri, 'alt': node['alt']}

    # make srcset str.  Need to change all the prefixes!
    maxsrc = uri
    if srcset:
        maxmult = -1
        srcsetst = ''
        for mult, src in srcset.items():
            nm = PurePath(src[1:]).name
            # ../../_images/plot_1_2_0x.png
            path = f'{imagerel}/{rel}{nm}'
            srcsetst += path
            if mult == 0:
                srcsetst += ', '
            else:
                srcsetst += f' {mult:1.2f}x, '

            if mult > maxmult:
                maxmult = mult
                maxsrc = path

        # trim trailing comma and space...
        img_attrs['srcset'] = srcsetst[:-2]

    if node['class'] is not None:
        img_attrs['class'] = ' '.join(node['class'])
    for style in ['width', 'height', 'scale']:
        if node[style]:
            if 'style' not in img_attrs:
                img_attrs['style'] = f'{style}: {node[style]};'
            else:
                img_attrs['style'] += f'{style}: {node[style]};'

    # <figure class="align-default" id="id1">
    # <a class="reference internal image-reference" href="_images/index-1.2x.png">
    # <img alt="_images/index-1.2x.png"
    #  src="_images/index-1.2x.png" style="width: 53%;" />
    # </a>
    # <figcaption>
    # <p><span class="caption-text">Figure caption is here....</span>
    # <a class="headerlink" href="#id1" title="Permalink to this image">#</a></p>
    # </figcaption>
    # </figure>
    self.body.append(
        self.starttag(
            node, 'figure',
            CLASS=f'align-{node["align"]}' if node['align'] else 'align-center'))
    self.body.append(
        self.starttag(node, 'a', CLASS='reference internal image-reference',
                      href=maxsrc) +
        self.emptytag(node, 'img', **img_attrs) +
        '</a>\n')
    if node['caption']:
        self.body.append(self.starttag(node, 'figcaption'))
        self.body.append(self.starttag(node, 'p'))
        self.body.append(self.starttag(node, 'span', CLASS='caption-text'))
        self.body.append(node['caption'])
        self.body.append('</span></p></figcaption>\n')
    self.body.append('</figure>\n')


def visit_figmpl_latex(self, node):

    if node['srcset'] is not None:
        imagedir, srcset = _copy_images_figmpl(self, node)
        maxmult = -1
        # choose the highest res version for latex:
        maxmult = max(srcset, default=-1)
        node['uri'] = PurePath(srcset[maxmult]).name

    self.visit_figure(node)


def depart_figmpl_html(self, node):
    pass


def depart_figmpl_latex(self, node):
    self.depart_figure(node)


def figurempl_addnode(app):
    app.add_node(figmplnode,
                 html=(visit_figmpl_html, depart_figmpl_html),
                 latex=(visit_figmpl_latex, depart_figmpl_latex))


def setup(app):
    app.add_directive("figure-mpl", FigureMpl)
    figurempl_addnode(app)
    metadata = {'parallel_read_safe': True, 'parallel_write_safe': True,
                'version': matplotlib.__version__}
    return metadata

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\text_file.py ===
"""text_file

provides the TextFile class, which gives an interface to text files
that (optionally) takes care of stripping comments, ignoring blank
lines, and joining lines with backslashes."""

import sys


class TextFile:
    """Provides a file-like object that takes care of all the things you
    commonly want to do when processing a text file that has some
    line-by-line syntax: strip comments (as long as "#" is your
    comment character), skip blank lines, join adjacent lines by
    escaping the newline (ie. backslash at end of line), strip
    leading and/or trailing whitespace.  All of these are optional
    and independently controllable.

    Provides a 'warn()' method so you can generate warning messages that
    report physical line number, even if the logical line in question
    spans multiple physical lines.  Also provides 'unreadline()' for
    implementing line-at-a-time lookahead.

    Constructor is called as:

        TextFile (filename=None, file=None, **options)

    It bombs (RuntimeError) if both 'filename' and 'file' are None;
    'filename' should be a string, and 'file' a file object (or
    something that provides 'readline()' and 'close()' methods).  It is
    recommended that you supply at least 'filename', so that TextFile
    can include it in warning messages.  If 'file' is not supplied,
    TextFile creates its own using 'io.open()'.

    The options are all boolean, and affect the value returned by
    'readline()':
      strip_comments [default: true]
        strip from "#" to end-of-line, as well as any whitespace
        leading up to the "#" -- unless it is escaped by a backslash
      lstrip_ws [default: false]
        strip leading whitespace from each line before returning it
      rstrip_ws [default: true]
        strip trailing whitespace (including line terminator!) from
        each line before returning it
      skip_blanks [default: true}
        skip lines that are empty *after* stripping comments and
        whitespace.  (If both lstrip_ws and rstrip_ws are false,
        then some lines may consist of solely whitespace: these will
        *not* be skipped, even if 'skip_blanks' is true.)
      join_lines [default: false]
        if a backslash is the last non-newline character on a line
        after stripping comments and whitespace, join the following line
        to it to form one "logical line"; if N consecutive lines end
        with a backslash, then N+1 physical lines will be joined to
        form one logical line.
      collapse_join [default: false]
        strip leading whitespace from lines that are joined to their
        predecessor; only matters if (join_lines and not lstrip_ws)
      errors [default: 'strict']
        error handler used to decode the file content

    Note that since 'rstrip_ws' can strip the trailing newline, the
    semantics of 'readline()' must differ from those of the builtin file
    object's 'readline()' method!  In particular, 'readline()' returns
    None for end-of-file: an empty string might just be a blank line (or
    an all-whitespace line), if 'rstrip_ws' is true but 'skip_blanks' is
    not."""

    default_options = {
        'strip_comments': 1,
        'skip_blanks': 1,
        'lstrip_ws': 0,
        'rstrip_ws': 1,
        'join_lines': 0,
        'collapse_join': 0,
        'errors': 'strict',
    }

    def __init__(self, filename=None, file=None, **options):
        """Construct a new TextFile object.  At least one of 'filename'
        (a string) and 'file' (a file-like object) must be supplied.
        They keyword argument options are described above and affect
        the values returned by 'readline()'."""
        if filename is None and file is None:
            raise RuntimeError(
                "you must supply either or both of 'filename' and 'file'"
            )

        # set values for all options -- either from client option hash
        # or fallback to default_options
        for opt in self.default_options.keys():
            if opt in options:
                setattr(self, opt, options[opt])
            else:
                setattr(self, opt, self.default_options[opt])

        # sanity check client option hash
        for opt in options.keys():
            if opt not in self.default_options:
                raise KeyError(f"invalid TextFile option '{opt}'")

        if file is None:
            self.open(filename)
        else:
            self.filename = filename
            self.file = file
            self.current_line = 0  # assuming that file is at BOF!

        # 'linebuf' is a stack of lines that will be emptied before we
        # actually read from the file; it's only populated by an
        # 'unreadline()' operation
        self.linebuf = []

    def open(self, filename):
        """Open a new file named 'filename'.  This overrides both the
        'filename' and 'file' arguments to the constructor."""
        self.filename = filename
        self.file = open(self.filename, errors=self.errors, encoding='utf-8')
        self.current_line = 0

    def close(self):
        """Close the current file and forget everything we know about it
        (filename, current line number)."""
        file = self.file
        self.file = None
        self.filename = None
        self.current_line = None
        file.close()

    def gen_error(self, msg, line=None):
        outmsg = []
        if line is None:
            line = self.current_line
        outmsg.append(self.filename + ", ")
        if isinstance(line, (list, tuple)):
            outmsg.append("lines {}-{}: ".format(*line))
        else:
            outmsg.append(f"line {int(line)}: ")
        outmsg.append(str(msg))
        return "".join(outmsg)

    def error(self, msg, line=None):
        raise ValueError("error: " + self.gen_error(msg, line))

    def warn(self, msg, line=None):
        """Print (to stderr) a warning message tied to the current logical
        line in the current file.  If the current logical line in the
        file spans multiple physical lines, the warning refers to the
        whole range, eg. "lines 3-5".  If 'line' supplied, it overrides
        the current line number; it may be a list or tuple to indicate a
        range of physical lines, or an integer for a single physical
        line."""
        sys.stderr.write("warning: " + self.gen_error(msg, line) + "\n")

    def readline(self):  # noqa: C901
        """Read and return a single logical line from the current file (or
        from an internal buffer if lines have previously been "unread"
        with 'unreadline()').  If the 'join_lines' option is true, this
        may involve reading multiple physical lines concatenated into a
        single string.  Updates the current line number, so calling
        'warn()' after 'readline()' emits a warning about the physical
        line(s) just read.  Returns None on end-of-file, since the empty
        string can occur if 'rstrip_ws' is true but 'strip_blanks' is
        not."""
        # If any "unread" lines waiting in 'linebuf', return the top
        # one.  (We don't actually buffer read-ahead data -- lines only
        # get put in 'linebuf' if the client explicitly does an
        # 'unreadline()'.
        if self.linebuf:
            line = self.linebuf[-1]
            del self.linebuf[-1]
            return line

        buildup_line = ''

        while True:
            # read the line, make it None if EOF
            line = self.file.readline()
            if line == '':
                line = None

            if self.strip_comments and line:
                # Look for the first "#" in the line.  If none, never
                # mind.  If we find one and it's the first character, or
                # is not preceded by "\", then it starts a comment --
                # strip the comment, strip whitespace before it, and
                # carry on.  Otherwise, it's just an escaped "#", so
                # unescape it (and any other escaped "#"'s that might be
                # lurking in there) and otherwise leave the line alone.

                pos = line.find("#")
                if pos == -1:  # no "#" -- no comments
                    pass

                # It's definitely a comment -- either "#" is the first
                # character, or it's elsewhere and unescaped.
                elif pos == 0 or line[pos - 1] != "\\":
                    # Have to preserve the trailing newline, because it's
                    # the job of a later step (rstrip_ws) to remove it --
                    # and if rstrip_ws is false, we'd better preserve it!
                    # (NB. this means that if the final line is all comment
                    # and has no trailing newline, we will think that it's
                    # EOF; I think that's OK.)
                    eol = (line[-1] == '\n') and '\n' or ''
                    line = line[0:pos] + eol

                    # If all that's left is whitespace, then skip line
                    # *now*, before we try to join it to 'buildup_line' --
                    # that way constructs like
                    #   hello \\
                    #   # comment that should be ignored
                    #   there
                    # result in "hello there".
                    if line.strip() == "":
                        continue
                else:  # it's an escaped "#"
                    line = line.replace("\\#", "#")

            # did previous line end with a backslash? then accumulate
            if self.join_lines and buildup_line:
                # oops: end of file
                if line is None:
                    self.warn("continuation line immediately precedes end-of-file")
                    return buildup_line

                if self.collapse_join:
                    line = line.lstrip()
                line = buildup_line + line

                # careful: pay attention to line number when incrementing it
                if isinstance(self.current_line, list):
                    self.current_line[1] = self.current_line[1] + 1
                else:
                    self.current_line = [self.current_line, self.current_line + 1]
            # just an ordinary line, read it as usual
            else:
                if line is None:  # eof
                    return None

                # still have to be careful about incrementing the line number!
                if isinstance(self.current_line, list):
                    self.current_line = self.current_line[1] + 1
                else:
                    self.current_line = self.current_line + 1

            # strip whitespace however the client wants (leading and
            # trailing, or one or the other, or neither)
            if self.lstrip_ws and self.rstrip_ws:
                line = line.strip()
            elif self.lstrip_ws:
                line = line.lstrip()
            elif self.rstrip_ws:
                line = line.rstrip()

            # blank line (whether we rstrip'ed or not)? skip to next line
            # if appropriate
            if line in ('', '\n') and self.skip_blanks:
                continue

            if self.join_lines:
                if line[-1] == '\\':
                    buildup_line = line[:-1]
                    continue

                if line[-2:] == '\\\n':
                    buildup_line = line[0:-2] + '\n'
                    continue

            # well, I guess there's some actual content there: return it
            return line

    def readlines(self):
        """Read and return the list of all logical lines remaining in the
        current file."""
        lines = []
        while True:
            line = self.readline()
            if line is None:
                return lines
            lines.append(line)

    def unreadline(self, line):
        """Push 'line' (a string) onto an internal buffer that will be
        checked by future 'readline()' calls.  Handy for implementing
        a parser with line-at-a-time lookahead."""
        self.linebuf.append(line)

# === NexusCore/openenv\Lib\site-packages\contourpy\__init__.py ===
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from contourpy._contourpy import (
    ContourGenerator,
    FillType,
    LineType,
    Mpl2005ContourGenerator,
    Mpl2014ContourGenerator,
    SerialContourGenerator,
    ThreadedContourGenerator,
    ZInterp,
    max_threads,
)
from contourpy._version import __version__
from contourpy.chunk import calc_chunk_sizes
from contourpy.convert import (
    convert_filled,
    convert_lines,
    convert_multi_filled,
    convert_multi_lines,
)
from contourpy.dechunk import (
    dechunk_filled,
    dechunk_lines,
    dechunk_multi_filled,
    dechunk_multi_lines,
)
from contourpy.enum_util import as_fill_type, as_line_type, as_z_interp

if TYPE_CHECKING:
    from typing import Any

    from numpy.typing import ArrayLike

    from ._contourpy import CoordinateArray, MaskArray

__all__ = [
    "__version__",
    "contour_generator",
    "convert_filled",
    "convert_lines",
    "convert_multi_filled",
    "convert_multi_lines",
    "dechunk_filled",
    "dechunk_lines",
    "dechunk_multi_filled",
    "dechunk_multi_lines",
    "max_threads",
    "FillType",
    "LineType",
    "ContourGenerator",
    "Mpl2005ContourGenerator",
    "Mpl2014ContourGenerator",
    "SerialContourGenerator",
    "ThreadedContourGenerator",
    "ZInterp",
]


# Simple mapping of algorithm name to class name.
_class_lookup: dict[str, type[ContourGenerator]] = {
    "mpl2005": Mpl2005ContourGenerator,
    "mpl2014": Mpl2014ContourGenerator,
    "serial": SerialContourGenerator,
    "threaded": ThreadedContourGenerator,
}


def _remove_z_mask(
    z: ArrayLike | np.ma.MaskedArray[Any, Any] | None,
) -> tuple[CoordinateArray, MaskArray | None]:
    # Preserve mask if present.
    z_array = np.ma.asarray(z, dtype=np.float64)  # type: ignore[no-untyped-call]
    z_masked = np.ma.masked_invalid(z_array, copy=False)  # type: ignore[no-untyped-call]

    if np.ma.is_masked(z_masked):  # type: ignore[no-untyped-call]
        mask = np.ma.getmask(z_masked)  # type: ignore[no-untyped-call]
    else:
        mask = None

    return np.ma.getdata(z_masked), mask  # type: ignore[no-untyped-call]


def contour_generator(
    x: ArrayLike | None = None,
    y: ArrayLike | None = None,
    z: ArrayLike | np.ma.MaskedArray[Any, Any] | None = None,
    *,
    name: str = "serial",
    corner_mask: bool | None = None,
    line_type: LineType | str | None = None,
    fill_type: FillType | str | None = None,
    chunk_size: int | tuple[int, int] | None = None,
    chunk_count: int | tuple[int, int] | None = None,
    total_chunk_count: int | None = None,
    quad_as_tri: bool = False,
    z_interp: ZInterp | str | None = ZInterp.Linear,
    thread_count: int = 0,
) -> ContourGenerator:
    """Create and return a :class:`~.ContourGenerator` object.

    The class and properties of the returned :class:`~.ContourGenerator` are determined by the
    function arguments, with sensible defaults.

    Args:
        x (array-like of shape (ny, nx) or (nx,), optional): The x-coordinates of the ``z`` values.
            May be 2D with the same shape as ``z.shape``, or 1D with length ``nx = z.shape[1]``.
            If not specified are assumed to be ``np.arange(nx)``. Must be ordered monotonically.
        y (array-like of shape (ny, nx) or (ny,), optional): The y-coordinates of the ``z`` values.
            May be 2D with the same shape as ``z.shape``, or 1D with length ``ny = z.shape[0]``.
            If not specified are assumed to be ``np.arange(ny)``. Must be ordered monotonically.
        z (array-like of shape (ny, nx), may be a masked array): The 2D gridded values to calculate
            the contours of.  May be a masked array, and any invalid values (``np.inf`` or
            ``np.nan``) will also be masked out.
        name (str): Algorithm name, one of ``"serial"``, ``"threaded"``, ``"mpl2005"`` or
            ``"mpl2014"``, default ``"serial"``.
        corner_mask (bool, optional): Enable/disable corner masking, which only has an effect if
            ``z`` is a masked array. If ``False``, any quad touching a masked point is masked out.
            If ``True``, only the triangular corners of quads nearest these points are always masked
            out, other triangular corners comprising three unmasked points are contoured as usual.
            If not specified, uses the default provided by the algorithm ``name``.
        line_type (LineType or str, optional): The format of contour line data returned from calls
            to :meth:`~.ContourGenerator.lines`, specified either as a :class:`~.LineType` or its
            string equivalent such as ``"SeparateCode"``.
            If not specified, uses the default provided by the algorithm ``name``.
            The relationship between the :class:`~.LineType` enum and the data format returned from
            :meth:`~.ContourGenerator.lines` is explained at :ref:`line_type`.
        fill_type (FillType or str, optional): The format of filled contour data returned from calls
            to :meth:`~.ContourGenerator.filled`, specified either as a :class:`~.FillType` or its
            string equivalent such as ``"OuterOffset"``.
            If not specified, uses the default provided by the algorithm ``name``.
            The relationship between the :class:`~.FillType` enum and the data format returned from
            :meth:`~.ContourGenerator.filled` is explained at :ref:`fill_type`.
        chunk_size (int or tuple(int, int), optional): Chunk size in (y, x) directions, or the same
            size in both directions if only one value is specified.
        chunk_count (int or tuple(int, int), optional): Chunk count in (y, x) directions, or the
            same count in both directions if only one value is specified.
        total_chunk_count (int, optional): Total number of chunks.
        quad_as_tri (bool): Enable/disable treating quads as 4 triangles, default ``False``.
            If ``False``, a contour line within a quad is a straight line between points on two of
            its edges. If ``True``, each full quad is divided into 4 triangles using a virtual point
            at the centre (mean x, y of the corner points) and a contour line is piecewise linear
            within those triangles. Corner-masked triangles are not affected by this setting, only
            full unmasked quads.
        z_interp (ZInterp or str, optional): How to interpolate ``z`` values when determining where
            contour lines intersect the edges of quads and the ``z`` values of the central points of
            quads, specified either as a :class:`~contourpy.ZInterp` or its string equivalent such
            as ``"Log"``. Default is ``ZInterp.Linear``.
        thread_count (int): Number of threads to use for contour calculation, default 0. Threads can
            only be used with an algorithm ``name`` that supports threads (currently only
            ``name="threaded"``) and there must be at least the same number of chunks as threads.
            If ``thread_count=0`` and ``name="threaded"`` then it uses the maximum number of threads
            as determined by the C++11 call ``std::thread::hardware_concurrency()``. If ``name`` is
            something other than ``"threaded"`` then the ``thread_count`` will be set to ``1``.

    Return:
        :class:`~.ContourGenerator`.

    Note:
        A maximum of one of ``chunk_size``, ``chunk_count`` and ``total_chunk_count`` may be
        specified.

    Warning:
        The ``name="mpl2005"`` algorithm does not implement chunking for contour lines.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    z, mask = _remove_z_mask(z)

    # Check arguments: z.
    if z.ndim != 2:
        raise TypeError(f"Input z must be 2D, not {z.ndim}D")

    if z.shape[0] < 2 or z.shape[1] < 2:
        raise TypeError(f"Input z must be at least a (2, 2) shaped array, but has shape {z.shape}")

    ny, nx = z.shape

    # Check arguments: x and y.
    if x.ndim != y.ndim:
        raise TypeError(f"Number of dimensions of x ({x.ndim}) and y ({y.ndim}) do not match")

    if x.ndim == 0:
        x = np.arange(nx, dtype=np.float64)
        y = np.arange(ny, dtype=np.float64)
        x, y = np.meshgrid(x, y)
    elif x.ndim == 1:
        if len(x) != nx:
            raise TypeError(f"Length of x ({len(x)}) must match number of columns in z ({nx})")
        if len(y) != ny:
            raise TypeError(f"Length of y ({len(y)}) must match number of rows in z ({ny})")
        x, y = np.meshgrid(x, y)
    elif x.ndim == 2:
        if x.shape != z.shape:
            raise TypeError(f"Shapes of x {x.shape} and z {z.shape} do not match")
        if y.shape != z.shape:
            raise TypeError(f"Shapes of y {y.shape} and z {z.shape} do not match")
    else:
        raise TypeError(f"Inputs x and y must be None, 1D or 2D, not {x.ndim}D")

    # Check mask shape just in case.
    if mask is not None and mask.shape != z.shape:
        raise ValueError("If mask is set it must be a 2D array with the same shape as z")

    # Check arguments: name.
    if name not in _class_lookup:
        raise ValueError(f"Unrecognised contour generator name: {name}")

    # Check arguments: chunk_size, chunk_count and total_chunk_count.
    y_chunk_size, x_chunk_size = calc_chunk_sizes(
        chunk_size, chunk_count, total_chunk_count, ny, nx)

    cls = _class_lookup[name]

    # Check arguments: corner_mask.
    if corner_mask is None:
        # Set it to default, which is True if the algorithm supports it.
        corner_mask = cls.supports_corner_mask()
    elif corner_mask and not cls.supports_corner_mask():
        raise ValueError(f"{name} contour generator does not support corner_mask=True")

    # Check arguments: line_type.
    if line_type is None:
        line_type = cls.default_line_type
    else:
        line_type = as_line_type(line_type)

    if not cls.supports_line_type(line_type):
        raise ValueError(f"{name} contour generator does not support line_type {line_type}")

    # Check arguments: fill_type.
    if fill_type is None:
        fill_type = cls.default_fill_type
    else:
        fill_type = as_fill_type(fill_type)

    if not cls.supports_fill_type(fill_type):
        raise ValueError(f"{name} contour generator does not support fill_type {fill_type}")

    # Check arguments: quad_as_tri.
    if quad_as_tri and not cls.supports_quad_as_tri():
        raise ValueError(f"{name} contour generator does not support quad_as_tri=True")

    # Check arguments: z_interp.
    if z_interp is None:
        z_interp = ZInterp.Linear
    else:
        z_interp = as_z_interp(z_interp)

    if z_interp != ZInterp.Linear and not cls.supports_z_interp():
        raise ValueError(f"{name} contour generator does not support z_interp {z_interp}")

    # Check arguments: thread_count.
    if thread_count not in (0, 1) and not cls.supports_threads():
        raise ValueError(f"{name} contour generator does not support thread_count {thread_count}")

    # Prepare args and kwargs for contour generator constructor.
    args = [x, y, z, mask]
    kwargs: dict[str, int | bool | LineType | FillType | ZInterp] = {
        "x_chunk_size": x_chunk_size,
        "y_chunk_size": y_chunk_size,
    }

    if name not in ("mpl2005", "mpl2014"):
        kwargs["line_type"] = line_type
        kwargs["fill_type"] = fill_type

    if cls.supports_corner_mask():
        kwargs["corner_mask"] = corner_mask

    if cls.supports_quad_as_tri():
        kwargs["quad_as_tri"] = quad_as_tri

    if cls.supports_z_interp():
        kwargs["z_interp"] = z_interp

    if cls.supports_threads():
        kwargs["thread_count"] = thread_count

    # Create contour generator.
    return cls(*args, **kwargs)

# === NexusCore/openenv\Lib\site-packages\git\types.py ===
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

import os
import sys
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NoReturn,
    Optional,
    Sequence as Sequence,
    Tuple,
    TYPE_CHECKING,
    Type,
    TypeVar,
    Union,
)
import warnings

if sys.version_info >= (3, 8):
    from typing import (
        Literal,
        Protocol,
        SupportsIndex as SupportsIndex,
        TypedDict,
        runtime_checkable,
    )
else:
    from typing_extensions import (
        Literal,
        Protocol,
        SupportsIndex as SupportsIndex,
        TypedDict,
        runtime_checkable,
    )

if TYPE_CHECKING:
    from git.objects import Commit, Tree, TagObject, Blob
    from git.repo import Repo

PathLike = Union[str, "os.PathLike[str]"]
"""A :class:`str` (Unicode) based file or directory path."""

TBD = Any
"""Alias of :class:`~typing.Any`, when a type hint is meant to become more specific."""

_T = TypeVar("_T")
"""Type variable used internally in GitPython."""

AnyGitObject = Union["Commit", "Tree", "TagObject", "Blob"]
"""Union of the :class:`~git.objects.base.Object`-based types that represent actual git
object types.

As noted in :class:`~git.objects.base.Object`, which has further details, these are:

* :class:`Blob <git.objects.blob.Blob>`
* :class:`Tree <git.objects.tree.Tree>`
* :class:`Commit <git.objects.commit.Commit>`
* :class:`TagObject <git.objects.tag.TagObject>`

Those GitPython classes represent the four git object types, per
:manpage:`gitglossary(7)`:

* "blob": https://git-scm.com/docs/gitglossary#def_blob_object
* "tree object": https://git-scm.com/docs/gitglossary#def_tree_object
* "commit object": https://git-scm.com/docs/gitglossary#def_commit_object
* "tag object": https://git-scm.com/docs/gitglossary#def_tag_object

For more general information on git objects and their types as git understands them:

* "object": https://git-scm.com/docs/gitglossary#def_object
* "object type": https://git-scm.com/docs/gitglossary#def_object_type

:note:
    See also the :class:`Tree_ish` and :class:`Commit_ish` unions.
"""

Tree_ish = Union["Commit", "Tree", "TagObject"]
"""Union of :class:`~git.objects.base.Object`-based types that are typically tree-ish.

See :manpage:`gitglossary(7)` on "tree-ish":
https://git-scm.com/docs/gitglossary#def_tree-ish

:note:
    :class:`~git.objects.tree.Tree` and :class:`~git.objects.commit.Commit` are the
    classes whose instances are all tree-ish. This union includes them, but also
    :class:`~git.objects.tag.TagObject`, only **most** of whose instances are tree-ish.
    Whether a particular :class:`~git.objects.tag.TagObject` peels (recursively
    dereferences) to a tree or commit, rather than a blob, can in general only be known
    at runtime. In practice, git tag objects are nearly always used for tagging commits,
    and such tags are tree-ish because commits are tree-ish.

:note:
    See also the :class:`AnyGitObject` union of all four classes corresponding to git
    object types.
"""

Commit_ish = Union["Commit", "TagObject"]
"""Union of :class:`~git.objects.base.Object`-based types that are typically commit-ish.

See :manpage:`gitglossary(7)` on "commit-ish":
https://git-scm.com/docs/gitglossary#def_commit-ish

:note:
    :class:`~git.objects.commit.Commit` is the only class whose instances are all
    commit-ish. This union type includes :class:`~git.objects.commit.Commit`, but also
    :class:`~git.objects.tag.TagObject`, only **most** of whose instances are
    commit-ish. Whether a particular :class:`~git.objects.tag.TagObject` peels
    (recursively dereferences) to a commit, rather than a tree or blob, can in general
    only be known at runtime. In practice, git tag objects are nearly always used for
    tagging commits, and such tags are of course commit-ish.

:note:
    See also the :class:`AnyGitObject` union of all four classes corresponding to git
    object types.
"""

GitObjectTypeString = Literal["commit", "tag", "blob", "tree"]
"""Literal strings identifying git object types and the
:class:`~git.objects.base.Object`-based types that represent them.

See the :attr:`Object.type <git.objects.base.Object.type>` attribute. These are its
values in :class:`~git.objects.base.Object` subclasses that represent git objects. These
literals therefore correspond to the types in the :class:`AnyGitObject` union.

These are the same strings git itself uses to identify its four object types.
See :manpage:`gitglossary(7)` on "object type":
https://git-scm.com/docs/gitglossary#def_object_type
"""

Lit_commit_ish: Type[Literal["commit", "tag"]]
"""Deprecated. Type of literal strings identifying typically-commitish git object types.

Prior to a bugfix, this type had been defined more broadly. Any usage is in practice
ambiguous and likely to be incorrect. This type has therefore been made a static type
error to appear in annotations. It is preserved, with a deprecated status, to avoid
introducing runtime errors in code that refers to it, but it should not be used.

Instead of this type:

* For the type of the string literals associated with :class:`Commit_ish`, use
  ``Literal["commit", "tag"]`` or create a new type alias for it. That is equivalent to
  this type as currently defined (but usable in statically checked type annotations).

* For the type of all four string literals associated with :class:`AnyGitObject`, use
  :class:`GitObjectTypeString`. That is equivalent to the old definition of this type
  prior to the bugfix (and is also usable in statically checked type annotations).
"""


def _getattr(name: str) -> Any:
    if name != "Lit_commit_ish":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    warnings.warn(
        "Lit_commit_ish is deprecated. It is currently defined as "
        '`Literal["commit", "tag"]`, which should be used in its place if desired. It '
        'had previously been defined as `Literal["commit", "tag", "blob", "tree"]`, '
        "covering all four git object type strings including those that are never "
        "commit-ish. For that, use the GitObjectTypeString type instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return Literal["commit", "tag"]


if not TYPE_CHECKING:  # Preserve static checking for undefined/misspelled attributes.
    __getattr__ = _getattr


def __dir__() -> List[str]:
    return [*globals(), "Lit_commit_ish"]


# Config_levels ---------------------------------------------------------

Lit_config_levels = Literal["system", "global", "user", "repository"]
"""Type of literal strings naming git configuration levels.

These strings relate to which file a git configuration variable is in.
"""

ConfigLevels_Tup = Tuple[Literal["system"], Literal["user"], Literal["global"], Literal["repository"]]
"""Static type of a tuple of the four strings representing configuration levels."""

# Progress parameter type alias -----------------------------------------

CallableProgress = Optional[Callable[[int, Union[str, float], Union[str, float, None], str], None]]
"""General type of a function or other callable used as a progress reporter for cloning.

This is the type of a function or other callable that reports the progress of a clone,
when passed as a ``progress`` argument to :meth:`Repo.clone <git.repo.base.Repo.clone>`
or :meth:`Repo.clone_from <git.repo.base.Repo.clone_from>`.

:note:
    Those :meth:`~git.repo.base.Repo.clone` and :meth:`~git.repo.base.Repo.clone_from`
    methods also accept :meth:`~git.util.RemoteProgress` instances, including instances
    of its :meth:`~git.util.CallableRemoteProgress` subclass.

:note:
    Unlike objects that match this type, :meth:`~git.util.RemoteProgress` instances are
    not directly callable, not even when they are instances of
    :meth:`~git.util.CallableRemoteProgress`, which wraps a callable and forwards
    information to it but is not itself callable.

:note:
    This type also allows ``None``, for cloning without reporting progress.
"""

# -----------------------------------------------------------------------------------


def assert_never(inp: NoReturn, raise_error: bool = True, exc: Union[Exception, None] = None) -> None:
    """For use in exhaustive checking of a literal or enum in if/else chains.

    A call to this function should only be reached if not all members are handled, or if
    an attempt is made to pass non-members through the chain.

    :param inp:
        If all members are handled, the argument for `inp` will have the
        :class:`~typing.Never`/:class:`~typing.NoReturn` type.
        Otherwise, the type will mismatch and cause a mypy error.

    :param raise_error:
        If ``True``, will also raise :exc:`ValueError` with a general
        "unhandled literal" message, or the exception object passed as `exc`.

    :param exc:
        It not ``None``, this should be an already-constructed exception object, to be
        raised if `raise_error` is ``True``.
    """
    if raise_error:
        if exc is None:
            raise ValueError(f"An unhandled literal ({inp!r}) in an if/else chain was found")
        else:
            raise exc


class Files_TD(TypedDict):
    """Dictionary with stat counts for the diff of a particular file.

    For the :class:`~git.util.Stats.files` attribute of :class:`~git.util.Stats`
    objects.
    """

    insertions: int
    deletions: int
    lines: int
    change_type: str


class Total_TD(TypedDict):
    """Dictionary with total stats from any number of files.

    For the :class:`~git.util.Stats.total` attribute of :class:`~git.util.Stats`
    objects.
    """

    insertions: int
    deletions: int
    lines: int
    files: int


class HSH_TD(TypedDict):
    """Dictionary carrying the same information as a :class:`~git.util.Stats` object."""

    total: Total_TD
    files: Dict[PathLike, Files_TD]


@runtime_checkable
class Has_Repo(Protocol):
    """Protocol for having a :attr:`repo` attribute, the repository to operate on."""

    repo: "Repo"


@runtime_checkable
class Has_id_attribute(Protocol):
    """Protocol for having :attr:`_id_attribute_` used in iteration and traversal."""

    _id_attribute_: str

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\reorderGlyphs.py ===
"""Reorder glyphs in a font."""

__author__ = "Rod Sheeter"

# See https://docs.google.com/document/d/1h9O-C_ndods87uY0QeIIcgAMiX2gDTpvO_IhMJsKAqs/
# for details.


from fontTools import ttLib
from fontTools.ttLib.tables import otBase
from fontTools.ttLib.tables import otTables as ot
from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections import deque
from typing import (
    Optional,
    Any,
    Callable,
    Deque,
    Iterable,
    List,
    Tuple,
)


_COVERAGE_ATTR = "Coverage"  # tables that have one coverage use this name


def _sort_by_gid(
    get_glyph_id: Callable[[str], int],
    glyphs: List[str],
    parallel_list: Optional[List[Any]],
):
    if parallel_list:
        reordered = sorted(
            ((g, e) for g, e in zip(glyphs, parallel_list)),
            key=lambda t: get_glyph_id(t[0]),
        )
        sorted_glyphs, sorted_parallel_list = map(list, zip(*reordered))
        parallel_list[:] = sorted_parallel_list
    else:
        sorted_glyphs = sorted(glyphs, key=get_glyph_id)

    glyphs[:] = sorted_glyphs


def _get_dotted_attr(value: Any, dotted_attr: str) -> Any:
    attr_names = dotted_attr.split(".")
    assert attr_names

    while attr_names:
        attr_name = attr_names.pop(0)
        value = getattr(value, attr_name)
    return value


class ReorderRule(ABC):
    """A rule to reorder something in a font to match the fonts glyph order."""

    @abstractmethod
    def apply(self, font: ttLib.TTFont, value: otBase.BaseTable) -> None: ...


@dataclass(frozen=True)
class ReorderCoverage(ReorderRule):
    """Reorder a Coverage table, and optionally a list that is sorted parallel to it."""

    # A list that is parallel to Coverage
    parallel_list_attr: Optional[str] = None
    coverage_attr: str = _COVERAGE_ATTR

    def apply(self, font: ttLib.TTFont, value: otBase.BaseTable) -> None:
        coverage = _get_dotted_attr(value, self.coverage_attr)

        if type(coverage) is not list:
            # Normal path, process one coverage that might have a parallel list
            parallel_list = None
            if self.parallel_list_attr:
                parallel_list = _get_dotted_attr(value, self.parallel_list_attr)
                assert (
                    type(parallel_list) is list
                ), f"{self.parallel_list_attr} should be a list"
                assert len(parallel_list) == len(coverage.glyphs), "Nothing makes sense"

            _sort_by_gid(font.getGlyphID, coverage.glyphs, parallel_list)

        else:
            # A few tables have a list of coverage. No parallel list can exist.
            assert (
                not self.parallel_list_attr
            ), f"Can't have multiple coverage AND a parallel list; {self}"
            for coverage_entry in coverage:
                _sort_by_gid(font.getGlyphID, coverage_entry.glyphs, None)


@dataclass(frozen=True)
class ReorderList(ReorderRule):
    """Reorder the items within a list to match the updated glyph order.

    Useful when a list ordered by coverage itself contains something ordered by a gid.
    For example, the PairSet table of https://docs.microsoft.com/en-us/typography/opentype/spec/gpos#lookup-type-2-pair-adjustment-positioning-subtable.
    """

    list_attr: str
    key: str

    def apply(self, font: ttLib.TTFont, value: otBase.BaseTable) -> None:
        lst = _get_dotted_attr(value, self.list_attr)
        assert isinstance(lst, list), f"{self.list_attr} should be a list"
        lst.sort(key=lambda v: font.getGlyphID(getattr(v, self.key)))


# (Type, Optional Format) => List[ReorderRule]
# Encodes the relationships Cosimo identified
_REORDER_RULES = {
    # GPOS
    (ot.SinglePos, 1): [ReorderCoverage()],
    (ot.SinglePos, 2): [ReorderCoverage(parallel_list_attr="Value")],
    (ot.PairPos, 1): [ReorderCoverage(parallel_list_attr="PairSet")],
    (ot.PairSet, None): [ReorderList("PairValueRecord", key="SecondGlyph")],
    (ot.PairPos, 2): [ReorderCoverage()],
    (ot.CursivePos, 1): [ReorderCoverage(parallel_list_attr="EntryExitRecord")],
    (ot.MarkBasePos, 1): [
        ReorderCoverage(
            coverage_attr="MarkCoverage", parallel_list_attr="MarkArray.MarkRecord"
        ),
        ReorderCoverage(
            coverage_attr="BaseCoverage", parallel_list_attr="BaseArray.BaseRecord"
        ),
    ],
    (ot.MarkLigPos, 1): [
        ReorderCoverage(
            coverage_attr="MarkCoverage", parallel_list_attr="MarkArray.MarkRecord"
        ),
        ReorderCoverage(
            coverage_attr="LigatureCoverage",
            parallel_list_attr="LigatureArray.LigatureAttach",
        ),
    ],
    (ot.MarkMarkPos, 1): [
        ReorderCoverage(
            coverage_attr="Mark1Coverage", parallel_list_attr="Mark1Array.MarkRecord"
        ),
        ReorderCoverage(
            coverage_attr="Mark2Coverage", parallel_list_attr="Mark2Array.Mark2Record"
        ),
    ],
    (ot.ContextPos, 1): [ReorderCoverage(parallel_list_attr="PosRuleSet")],
    (ot.ContextPos, 2): [ReorderCoverage()],
    (ot.ContextPos, 3): [ReorderCoverage()],
    (ot.ChainContextPos, 1): [ReorderCoverage(parallel_list_attr="ChainPosRuleSet")],
    (ot.ChainContextPos, 2): [ReorderCoverage()],
    (ot.ChainContextPos, 3): [
        ReorderCoverage(coverage_attr="BacktrackCoverage"),
        ReorderCoverage(coverage_attr="InputCoverage"),
        ReorderCoverage(coverage_attr="LookAheadCoverage"),
    ],
    # GSUB
    (ot.ContextSubst, 1): [ReorderCoverage(parallel_list_attr="SubRuleSet")],
    (ot.ContextSubst, 2): [ReorderCoverage()],
    (ot.ContextSubst, 3): [ReorderCoverage()],
    (ot.ChainContextSubst, 1): [ReorderCoverage(parallel_list_attr="ChainSubRuleSet")],
    (ot.ChainContextSubst, 2): [ReorderCoverage()],
    (ot.ChainContextSubst, 3): [
        ReorderCoverage(coverage_attr="BacktrackCoverage"),
        ReorderCoverage(coverage_attr="InputCoverage"),
        ReorderCoverage(coverage_attr="LookAheadCoverage"),
    ],
    (ot.ReverseChainSingleSubst, 1): [
        ReorderCoverage(parallel_list_attr="Substitute"),
        ReorderCoverage(coverage_attr="BacktrackCoverage"),
        ReorderCoverage(coverage_attr="LookAheadCoverage"),
    ],
    # GDEF
    (ot.AttachList, None): [ReorderCoverage(parallel_list_attr="AttachPoint")],
    (ot.LigCaretList, None): [ReorderCoverage(parallel_list_attr="LigGlyph")],
    (ot.MarkGlyphSetsDef, None): [ReorderCoverage()],
    # MATH
    (ot.MathGlyphInfo, None): [ReorderCoverage(coverage_attr="ExtendedShapeCoverage")],
    (ot.MathItalicsCorrectionInfo, None): [
        ReorderCoverage(parallel_list_attr="ItalicsCorrection")
    ],
    (ot.MathTopAccentAttachment, None): [
        ReorderCoverage(
            coverage_attr="TopAccentCoverage", parallel_list_attr="TopAccentAttachment"
        )
    ],
    (ot.MathKernInfo, None): [
        ReorderCoverage(
            coverage_attr="MathKernCoverage", parallel_list_attr="MathKernInfoRecords"
        )
    ],
    (ot.MathVariants, None): [
        ReorderCoverage(
            coverage_attr="VertGlyphCoverage",
            parallel_list_attr="VertGlyphConstruction",
        ),
        ReorderCoverage(
            coverage_attr="HorizGlyphCoverage",
            parallel_list_attr="HorizGlyphConstruction",
        ),
    ],
}


# TODO Port to otTraverse

SubTablePath = Tuple[otBase.BaseTable.SubTableEntry, ...]


def _bfs_base_table(
    root: otBase.BaseTable, root_accessor: str
) -> Iterable[SubTablePath]:
    yield from _traverse_ot_data(
        root, root_accessor, lambda frontier, new: frontier.extend(new)
    )


# Given f(current frontier, new entries) add new entries to frontier
AddToFrontierFn = Callable[[Deque[SubTablePath], List[SubTablePath]], None]


def _traverse_ot_data(
    root: otBase.BaseTable, root_accessor: str, add_to_frontier_fn: AddToFrontierFn
) -> Iterable[SubTablePath]:
    # no visited because general otData is forward-offset only and thus cannot cycle

    frontier: Deque[SubTablePath] = deque()
    frontier.append((otBase.BaseTable.SubTableEntry(root_accessor, root),))
    while frontier:
        # path is (value, attr_name) tuples. attr_name is attr of parent to get value
        path = frontier.popleft()
        current = path[-1].value

        yield path

        new_entries = []
        for subtable_entry in current.iterSubTables():
            new_entries.append(path + (subtable_entry,))

        add_to_frontier_fn(frontier, new_entries)


def reorderGlyphs(font: ttLib.TTFont, new_glyph_order: List[str]):
    old_glyph_order = font.getGlyphOrder()
    if len(new_glyph_order) != len(old_glyph_order):
        raise ValueError(
            f"New glyph order contains {len(new_glyph_order)} glyphs, "
            f"but font has {len(old_glyph_order)} glyphs"
        )

    if set(old_glyph_order) != set(new_glyph_order):
        raise ValueError(
            "New glyph order does not contain the same set of glyphs as the font:\n"
            f"* only in new: {set(new_glyph_order) - set(old_glyph_order)}\n"
            f"* only in old: {set(old_glyph_order) - set(new_glyph_order)}"
        )

    # Changing the order of glyphs in a TTFont requires that all tables that use
    # glyph indexes have been fully.
    # Cf. https://github.com/fonttools/fonttools/issues/2060
    font.ensureDecompiled()
    not_loaded = sorted(t for t in font.keys() if not font.isLoaded(t))
    if not_loaded:
        raise ValueError(f"Everything should be loaded, following aren't: {not_loaded}")

    font.setGlyphOrder(new_glyph_order)

    coverage_containers = {"GDEF", "GPOS", "GSUB", "MATH"}
    for tag in coverage_containers:
        if tag in font.keys():
            for path in _bfs_base_table(font[tag].table, f'font["{tag}"]'):
                value = path[-1].value
                reorder_key = (type(value), getattr(value, "Format", None))
                for reorder in _REORDER_RULES.get(reorder_key, []):
                    reorder.apply(font, value)

    for tag in ["CFF ", "CFF2"]:
        if tag in font:
            cff_table = font[tag]
            charstrings = cff_table.cff.topDictIndex[0].CharStrings.charStrings
            cff_table.cff.topDictIndex[0].charset = new_glyph_order
            cff_table.cff.topDictIndex[0].CharStrings.charStrings = {
                k: charstrings.get(k) for k in new_glyph_order
            }

# === NexusCore/openenv\Lib\site-packages\google\api_core\page_iterator_async.py ===
# Copyright 2020 Google LLC
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

"""AsyncIO iterators for paging through paged API methods.

These iterators simplify the process of paging through API responses
where the request takes a page token and the response is a list of results with
a token for the next page. See `list pagination`_ in the Google API Style Guide
for more details.

.. _list pagination:
    https://cloud.google.com/apis/design/design_patterns#list_pagination

API clients that have methods that follow the list pagination pattern can
return an :class:`.AsyncIterator`:

    >>> results_iterator = await client.list_resources()

Or you can walk your way through items and call off the search early if
you find what you're looking for (resulting in possibly fewer requests)::

    >>> async for resource in results_iterator:
    ...     print(resource.name)
    ...     if not resource.is_valid:
    ...         break

At any point, you may check the number of items consumed by referencing the
``num_results`` property of the iterator::

    >>> async for my_item in results_iterator:
    ...     if results_iterator.num_results >= 10:
    ...         break

When iterating, not every new item will send a request to the server.
To iterate based on each page of items (where a page corresponds to
a request)::

    >>> async for page in results_iterator.pages:
    ...     print('=' * 20)
    ...     print('    Page number: {:d}'.format(iterator.page_number))
    ...     print('  Items in page: {:d}'.format(page.num_items))
    ...     print('     First item: {!r}'.format(next(page)))
    ...     print('Items remaining: {:d}'.format(page.remaining))
    ...     print('Next page token: {}'.format(iterator.next_page_token))
    ====================
        Page number: 1
      Items in page: 1
         First item: <MyItemClass at 0x7f1d3cccf690>
    Items remaining: 0
    Next page token: eav1OzQB0OM8rLdGXOEsyQWSG
    ====================
        Page number: 2
      Items in page: 19
         First item: <MyItemClass at 0x7f1d3cccffd0>
    Items remaining: 18
    Next page token: None
"""

import abc

from google.api_core.page_iterator import Page


def _item_to_value_identity(iterator, item):
    """An item to value transformer that returns the item un-changed."""
    # pylint: disable=unused-argument
    # We are conforming to the interface defined by Iterator.
    return item


class AsyncIterator(abc.ABC):
    """A generic class for iterating through API list responses.

    Args:
        client(google.cloud.client.Client): The API client.
        item_to_value (Callable[google.api_core.page_iterator_async.AsyncIterator, Any]):
            Callable to convert an item from the type in the raw API response
            into the native object. Will be called with the iterator and a
            single item.
        page_token (str): A token identifying a page in a result set to start
            fetching results from.
        max_results (int): The maximum number of results to fetch.
    """

    def __init__(
        self,
        client,
        item_to_value=_item_to_value_identity,
        page_token=None,
        max_results=None,
    ):
        self._started = False
        self.__active_aiterator = None

        self.client = client
        """Optional[Any]: The client that created this iterator."""
        self.item_to_value = item_to_value
        """Callable[Iterator, Any]: Callable to convert an item from the type
            in the raw API response into the native object. Will be called with
            the iterator and a
            single item.
        """
        self.max_results = max_results
        """int: The maximum number of results to fetch."""

        # The attributes below will change over the life of the iterator.
        self.page_number = 0
        """int: The current page of results."""
        self.next_page_token = page_token
        """str: The token for the next page of results. If this is set before
            the iterator starts, it effectively offsets the iterator to a
            specific starting point."""
        self.num_results = 0
        """int: The total number of results fetched so far."""

    @property
    def pages(self):
        """Iterator of pages in the response.

        returns:
            types.GeneratorType[google.api_core.page_iterator.Page]: A
                generator of page instances.

        raises:
            ValueError: If the iterator has already been started.
        """
        if self._started:
            raise ValueError("Iterator has already started", self)
        self._started = True
        return self._page_aiter(increment=True)

    async def _items_aiter(self):
        """Iterator for each item returned."""
        async for page in self._page_aiter(increment=False):
            for item in page:
                self.num_results += 1
                yield item

    def __aiter__(self):
        """Iterator for each item returned.

        Returns:
            types.GeneratorType[Any]: A generator of items from the API.

        Raises:
            ValueError: If the iterator has already been started.
        """
        if self._started:
            raise ValueError("Iterator has already started", self)
        self._started = True
        return self._items_aiter()

    async def __anext__(self):
        if self.__active_aiterator is None:
            self.__active_aiterator = self.__aiter__()
        return await self.__active_aiterator.__anext__()

    async def _page_aiter(self, increment):
        """Generator of pages of API responses.

        Args:
            increment (bool): Flag indicating if the total number of results
                should be incremented on each page. This is useful since a page
                iterator will want to increment by results per page while an
                items iterator will want to increment per item.

        Yields:
            Page: each page of items from the API.
        """
        page = await self._next_page()
        while page is not None:
            self.page_number += 1
            if increment:
                self.num_results += page.num_items
            yield page
            page = await self._next_page()

    @abc.abstractmethod
    async def _next_page(self):
        """Get the next page in the iterator.

        This does nothing and is intended to be over-ridden by subclasses
        to return the next :class:`Page`.

        Raises:
            NotImplementedError: Always, this method is abstract.
        """
        raise NotImplementedError


class AsyncGRPCIterator(AsyncIterator):
    """A generic class for iterating through gRPC list responses.

    .. note:: The class does not take a ``page_token`` argument because it can
        just be specified in the ``request``.

    Args:
        client (google.cloud.client.Client): The API client. This unused by
            this class, but kept to satisfy the :class:`Iterator` interface.
        method (Callable[protobuf.Message]): A bound gRPC method that should
            take a single message for the request.
        request (protobuf.Message): The request message.
        items_field (str): The field in the response message that has the
            items for the page.
        item_to_value (Callable[GRPCIterator, Any]): Callable to convert an
            item from the type in the JSON response into a native object. Will
            be called with the iterator and a single item.
        request_token_field (str): The field in the request message used to
            specify the page token.
        response_token_field (str): The field in the response message that has
            the token for the next page.
        max_results (int): The maximum number of results to fetch.

    .. autoattribute:: pages
    """

    _DEFAULT_REQUEST_TOKEN_FIELD = "page_token"
    _DEFAULT_RESPONSE_TOKEN_FIELD = "next_page_token"

    def __init__(
        self,
        client,
        method,
        request,
        items_field,
        item_to_value=_item_to_value_identity,
        request_token_field=_DEFAULT_REQUEST_TOKEN_FIELD,
        response_token_field=_DEFAULT_RESPONSE_TOKEN_FIELD,
        max_results=None,
    ):
        super().__init__(client, item_to_value, max_results=max_results)
        self._method = method
        self._request = request
        self._items_field = items_field
        self._request_token_field = request_token_field
        self._response_token_field = response_token_field

    async def _next_page(self):
        """Get the next page in the iterator.

        Returns:
            Page: The next page in the iterator or :data:`None` if
                there are no pages left.
        """
        if not self._has_next_page():
            return None

        if self.next_page_token is not None:
            setattr(self._request, self._request_token_field, self.next_page_token)

        response = await self._method(self._request)

        self.next_page_token = getattr(response, self._response_token_field)
        items = getattr(response, self._items_field)
        page = Page(self, items, self.item_to_value, raw_page=response)

        return page

    def _has_next_page(self):
        """Determines whether or not there are more pages with results.

        Returns:
            bool: Whether the iterator has more pages.
        """
        if self.page_number == 0:
            return True

        # Note: intentionally a falsy check instead of a None check. The RPC
        # can return an empty string indicating no more pages.
        if self.max_results is not None:
            if self.num_results >= self.max_results:
                return False

        return True if self.next_page_token else False

# === NexusCore/openenv\Lib\site-packages\google\oauth2\_id_token_async.py ===
# Copyright 2020 Google LLC
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

"""Google ID Token helpers.

Provides support for verifying `OpenID Connect ID Tokens`_, especially ones
generated by Google infrastructure.

To parse and verify an ID Token issued by Google's OAuth 2.0 authorization
server use :func:`verify_oauth2_token`. To verify an ID Token issued by
Firebase, use :func:`verify_firebase_token`.

A general purpose ID Token verifier is available as :func:`verify_token`.

Example::

    from google.oauth2 import _id_token_async
    from google.auth.transport import aiohttp_requests

    request = aiohttp_requests.Request()

    id_info = await _id_token_async.verify_oauth2_token(
        token, request, 'my-client-id.example.com')

    if id_info['iss'] != 'https://accounts.google.com':
        raise ValueError('Wrong issuer.')

    userid = id_info['sub']

By default, this will re-fetch certificates for each verification. Because
Google's public keys are only changed infrequently (on the order of once per
day), you may wish to take advantage of caching to reduce latency and the
potential for network errors. This can be accomplished using an external
library like `CacheControl`_ to create a cache-aware
:class:`google.auth.transport.Request`::

    import cachecontrol
    import google.auth.transport.requests
    import requests

    session = requests.session()
    cached_session = cachecontrol.CacheControl(session)
    request = google.auth.transport.requests.Request(session=cached_session)

.. _OpenID Connect ID Token:
    http://openid.net/specs/openid-connect-core-1_0.html#IDToken
.. _CacheControl: https://cachecontrol.readthedocs.io
"""

import http.client as http_client
import json
import os

from google.auth import environment_vars
from google.auth import exceptions
from google.auth import jwt
from google.auth.transport import requests
from google.oauth2 import id_token as sync_id_token


async def _fetch_certs(request, certs_url):
    """Fetches certificates.

    Google-style cerificate endpoints return JSON in the format of
    ``{'key id': 'x509 certificate'}``.

    Args:
        request (google.auth.transport.Request): The object used to make
            HTTP requests. This must be an aiohttp request.
        certs_url (str): The certificate endpoint URL.

    Returns:
        Mapping[str, str]: A mapping of public key ID to x.509 certificate
            data.
    """
    response = await request(certs_url, method="GET")

    if response.status != http_client.OK:
        raise exceptions.TransportError(
            "Could not fetch certificates at {}".format(certs_url)
        )

    data = await response.content()

    return json.loads(data)


async def verify_token(
    id_token,
    request,
    audience=None,
    certs_url=sync_id_token._GOOGLE_OAUTH2_CERTS_URL,
    clock_skew_in_seconds=0,
):
    """Verifies an ID token and returns the decoded token.

    Args:
        id_token (Union[str, bytes]): The encoded token.
        request (google.auth.transport.Request): The object used to make
            HTTP requests. This must be an aiohttp request.
        audience (str): The audience that this token is intended for. If None
            then the audience is not verified.
        certs_url (str): The URL that specifies the certificates to use to
            verify the token. This URL should return JSON in the format of
            ``{'key id': 'x509 certificate'}``.
        clock_skew_in_seconds (int): The clock skew used for `iat` and `exp`
            validation.

    Returns:
        Mapping[str, Any]: The decoded token.
    """
    certs = await _fetch_certs(request, certs_url)

    return jwt.decode(
        id_token,
        certs=certs,
        audience=audience,
        clock_skew_in_seconds=clock_skew_in_seconds,
    )


async def verify_oauth2_token(
    id_token, request, audience=None, clock_skew_in_seconds=0
):
    """Verifies an ID Token issued by Google's OAuth 2.0 authorization server.

    Args:
        id_token (Union[str, bytes]): The encoded token.
        request (google.auth.transport.Request): The object used to make
            HTTP requests. This must be an aiohttp request.
        audience (str): The audience that this token is intended for. This is
            typically your application's OAuth 2.0 client ID. If None then the
            audience is not verified.
        clock_skew_in_seconds (int): The clock skew used for `iat` and `exp`
            validation.

    Returns:
        Mapping[str, Any]: The decoded token.

    Raises:
        exceptions.GoogleAuthError: If the issuer is invalid.
    """
    idinfo = await verify_token(
        id_token,
        request,
        audience=audience,
        certs_url=sync_id_token._GOOGLE_OAUTH2_CERTS_URL,
        clock_skew_in_seconds=clock_skew_in_seconds,
    )

    if idinfo["iss"] not in sync_id_token._GOOGLE_ISSUERS:
        raise exceptions.GoogleAuthError(
            "Wrong issuer. 'iss' should be one of the following: {}".format(
                sync_id_token._GOOGLE_ISSUERS
            )
        )

    return idinfo


async def verify_firebase_token(
    id_token, request, audience=None, clock_skew_in_seconds=0
):
    """Verifies an ID Token issued by Firebase Authentication.

    Args:
        id_token (Union[str, bytes]): The encoded token.
        request (google.auth.transport.Request): The object used to make
            HTTP requests. This must be an aiohttp request.
        audience (str): The audience that this token is intended for. This is
            typically your Firebase application ID. If None then the audience
            is not verified.
        clock_skew_in_seconds (int): The clock skew used for `iat` and `exp`
            validation.

    Returns:
        Mapping[str, Any]: The decoded token.
    """
    return await verify_token(
        id_token,
        request,
        audience=audience,
        certs_url=sync_id_token._GOOGLE_APIS_CERTS_URL,
        clock_skew_in_seconds=clock_skew_in_seconds,
    )


async def fetch_id_token(request, audience):
    """Fetch the ID Token from the current environment.

    This function acquires ID token from the environment in the following order.
    See https://google.aip.dev/auth/4110.

    1. If the environment variable ``GOOGLE_APPLICATION_CREDENTIALS`` is set
       to the path of a valid service account JSON file, then ID token is
       acquired using this service account credentials.
    2. If the application is running in Compute Engine, App Engine or Cloud Run,
       then the ID token are obtained from the metadata server.
    3. If metadata server doesn't exist and no valid service account credentials
       are found, :class:`~google.auth.exceptions.DefaultCredentialsError` will
       be raised.

    Example::

        import google.oauth2._id_token_async
        import google.auth.transport.aiohttp_requests

        request = google.auth.transport.aiohttp_requests.Request()
        target_audience = "https://pubsub.googleapis.com"

        id_token = await google.oauth2._id_token_async.fetch_id_token(request, target_audience)

    Args:
        request (google.auth.transport.aiohttp_requests.Request): A callable used to make
            HTTP requests.
        audience (str): The audience that this ID token is intended for.

    Returns:
        str: The ID token.

    Raises:
        ~google.auth.exceptions.DefaultCredentialsError:
            If metadata server doesn't exist and no valid service account
            credentials are found.
    """
    # 1. Try to get credentials from the GOOGLE_APPLICATION_CREDENTIALS environment
    # variable.
    credentials_filename = os.environ.get(environment_vars.CREDENTIALS)
    if credentials_filename:
        if not (
            os.path.exists(credentials_filename)
            and os.path.isfile(credentials_filename)
        ):
            raise exceptions.DefaultCredentialsError(
                "GOOGLE_APPLICATION_CREDENTIALS path is either not found or invalid."
            )

        try:
            with open(credentials_filename, "r") as f:
                from google.oauth2 import _service_account_async as service_account

                info = json.load(f)
                if info.get("type") == "service_account":
                    credentials = service_account.IDTokenCredentials.from_service_account_info(
                        info, target_audience=audience
                    )
                    await credentials.refresh(request)
                    return credentials.token
        except ValueError as caught_exc:
            new_exc = exceptions.DefaultCredentialsError(
                "GOOGLE_APPLICATION_CREDENTIALS is not valid service account credentials.",
                caught_exc,
            )
            raise new_exc from caught_exc

    # 2. Try to fetch ID token from metada server if it exists. The code works
    # for GAE and Cloud Run metadata server as well.
    try:
        from google.auth import compute_engine
        from google.auth.compute_engine import _metadata

        request_new = requests.Request()
        if _metadata.ping(request_new):
            credentials = compute_engine.IDTokenCredentials(
                request_new, audience, use_metadata_identity_endpoint=True
            )
            credentials.refresh(request_new)
            return credentials.token
    except (ImportError, exceptions.TransportError):
        pass

    raise exceptions.DefaultCredentialsError(
        "Neither metadata server or valid service account credentials are found."
    )

# === NexusCore/openenv\Lib\site-packages\pyasn1\codec\native\encoder.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
from collections import OrderedDict
import warnings

from pyasn1 import debug
from pyasn1 import error
from pyasn1.compat import _MISSING
from pyasn1.type import base
from pyasn1.type import char
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

__all__ = ['encode']

LOG = debug.registerLoggee(__name__, flags=debug.DEBUG_ENCODER)


class AbstractItemEncoder(object):
    def encode(self, value, encodeFun, **options):
        raise error.PyAsn1Error('Not implemented')


class BooleanEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return bool(value)


class IntegerEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return int(value)


class BitStringEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return str(value)


class OctetStringEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return value.asOctets()


class TextStringEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return str(value)


class NullEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return None


class ObjectIdentifierEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return str(value)


class RelativeOIDEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return str(value)


class RealEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return float(value)


class SetEncoder(AbstractItemEncoder):
    protoDict = dict

    def encode(self, value, encodeFun, **options):
        inconsistency = value.isInconsistent
        if inconsistency:
            raise error.PyAsn1Error(
                f"ASN.1 object {value.__class__.__name__} is inconsistent")

        namedTypes = value.componentType
        substrate = self.protoDict()

        for idx, (key, subValue) in enumerate(value.items()):
            if namedTypes and namedTypes[idx].isOptional and not value[idx].isValue:
                continue
            substrate[key] = encodeFun(subValue, **options)
        return substrate


class SequenceEncoder(SetEncoder):
    protoDict = OrderedDict


class SequenceOfEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        inconsistency = value.isInconsistent
        if inconsistency:
            raise error.PyAsn1Error(
                f"ASN.1 object {value.__class__.__name__} is inconsistent")
        return [encodeFun(x, **options) for x in value]


class ChoiceEncoder(SequenceEncoder):
    pass


class AnyEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return value.asOctets()


TAG_MAP = {
    univ.Boolean.tagSet: BooleanEncoder(),
    univ.Integer.tagSet: IntegerEncoder(),
    univ.BitString.tagSet: BitStringEncoder(),
    univ.OctetString.tagSet: OctetStringEncoder(),
    univ.Null.tagSet: NullEncoder(),
    univ.ObjectIdentifier.tagSet: ObjectIdentifierEncoder(),
    univ.RelativeOID.tagSet: RelativeOIDEncoder(),
    univ.Enumerated.tagSet: IntegerEncoder(),
    univ.Real.tagSet: RealEncoder(),
    # Sequence & Set have same tags as SequenceOf & SetOf
    univ.SequenceOf.tagSet: SequenceOfEncoder(),
    univ.SetOf.tagSet: SequenceOfEncoder(),
    univ.Choice.tagSet: ChoiceEncoder(),
    # character string types
    char.UTF8String.tagSet: TextStringEncoder(),
    char.NumericString.tagSet: TextStringEncoder(),
    char.PrintableString.tagSet: TextStringEncoder(),
    char.TeletexString.tagSet: TextStringEncoder(),
    char.VideotexString.tagSet: TextStringEncoder(),
    char.IA5String.tagSet: TextStringEncoder(),
    char.GraphicString.tagSet: TextStringEncoder(),
    char.VisibleString.tagSet: TextStringEncoder(),
    char.GeneralString.tagSet: TextStringEncoder(),
    char.UniversalString.tagSet: TextStringEncoder(),
    char.BMPString.tagSet: TextStringEncoder(),
    # useful types
    useful.ObjectDescriptor.tagSet: OctetStringEncoder(),
    useful.GeneralizedTime.tagSet: OctetStringEncoder(),
    useful.UTCTime.tagSet: OctetStringEncoder()
}

# Put in ambiguous & non-ambiguous types for faster codec lookup
TYPE_MAP = {
    univ.Boolean.typeId: BooleanEncoder(),
    univ.Integer.typeId: IntegerEncoder(),
    univ.BitString.typeId: BitStringEncoder(),
    univ.OctetString.typeId: OctetStringEncoder(),
    univ.Null.typeId: NullEncoder(),
    univ.ObjectIdentifier.typeId: ObjectIdentifierEncoder(),
    univ.RelativeOID.typeId: RelativeOIDEncoder(),
    univ.Enumerated.typeId: IntegerEncoder(),
    univ.Real.typeId: RealEncoder(),
    # Sequence & Set have same tags as SequenceOf & SetOf
    univ.Set.typeId: SetEncoder(),
    univ.SetOf.typeId: SequenceOfEncoder(),
    univ.Sequence.typeId: SequenceEncoder(),
    univ.SequenceOf.typeId: SequenceOfEncoder(),
    univ.Choice.typeId: ChoiceEncoder(),
    univ.Any.typeId: AnyEncoder(),
    # character string types
    char.UTF8String.typeId: OctetStringEncoder(),
    char.NumericString.typeId: OctetStringEncoder(),
    char.PrintableString.typeId: OctetStringEncoder(),
    char.TeletexString.typeId: OctetStringEncoder(),
    char.VideotexString.typeId: OctetStringEncoder(),
    char.IA5String.typeId: OctetStringEncoder(),
    char.GraphicString.typeId: OctetStringEncoder(),
    char.VisibleString.typeId: OctetStringEncoder(),
    char.GeneralString.typeId: OctetStringEncoder(),
    char.UniversalString.typeId: OctetStringEncoder(),
    char.BMPString.typeId: OctetStringEncoder(),
    # useful types
    useful.ObjectDescriptor.typeId: OctetStringEncoder(),
    useful.GeneralizedTime.typeId: OctetStringEncoder(),
    useful.UTCTime.typeId: OctetStringEncoder()
}


class SingleItemEncoder(object):

    TAG_MAP = TAG_MAP
    TYPE_MAP = TYPE_MAP

    def __init__(self, tagMap=_MISSING, typeMap=_MISSING, **ignored):
        self._tagMap = tagMap if tagMap is not _MISSING else self.TAG_MAP
        self._typeMap = typeMap if typeMap is not _MISSING else self.TYPE_MAP

    def __call__(self, value, **options):
        if not isinstance(value, base.Asn1Item):
            raise error.PyAsn1Error(
                'value is not valid (should be an instance of an ASN.1 Item)')

        if LOG:
            debug.scope.push(type(value).__name__)
            LOG('encoder called for type %s '
                '<%s>' % (type(value).__name__, value.prettyPrint()))

        tagSet = value.tagSet

        try:
            concreteEncoder = self._typeMap[value.typeId]

        except KeyError:
            # use base type for codec lookup to recover untagged types
            baseTagSet = tag.TagSet(
                value.tagSet.baseTag, value.tagSet.baseTag)

            try:
                concreteEncoder = self._tagMap[baseTagSet]

            except KeyError:
                raise error.PyAsn1Error('No encoder for %s' % (value,))

        if LOG:
            LOG('using value codec %s chosen by '
                '%s' % (concreteEncoder.__class__.__name__, tagSet))

        pyObject = concreteEncoder.encode(value, self, **options)

        if LOG:
            LOG('encoder %s produced: '
                '%s' % (type(concreteEncoder).__name__, repr(pyObject)))
            debug.scope.pop()

        return pyObject


class Encoder(object):
    SINGLE_ITEM_ENCODER = SingleItemEncoder

    def __init__(self, **options):
        self._singleItemEncoder = self.SINGLE_ITEM_ENCODER(**options)

    def __call__(self, pyObject, asn1Spec=None, **options):
        return self._singleItemEncoder(
            pyObject, asn1Spec=asn1Spec, **options)


#: Turns ASN.1 object into a Python built-in type object(s).
#:
#: Takes any ASN.1 object (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative)
#: walks all its components recursively and produces a Python built-in type or a tree
#: of those.
#:
#: One exception is that instead of :py:class:`dict`, the :py:class:`OrderedDict`
#: is used to preserve ordering of the components in ASN.1 SEQUENCE.
#:
#: Parameters
#: ----------
#  asn1Value: any pyasn1 object (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative)
#:     pyasn1 object to encode (or a tree of them)
#:
#: Returns
#: -------
#: : :py:class:`object`
#:     Python built-in type instance (or a tree of them)
#:
#: Raises
#: ------
#: ~pyasn1.error.PyAsn1Error
#:     On encoding errors
#:
#: Examples
#: --------
#: Encode ASN.1 value object into native Python types
#:
#: .. code-block:: pycon
#:
#:    >>> seq = SequenceOf(componentType=Integer())
#:    >>> seq.extend([1, 2, 3])
#:    >>> encode(seq)
#:    [1, 2, 3]
#:
encode = SingleItemEncoder()

def __getattr__(attr: str):
    if newAttr := {"tagMap": "TAG_MAP", "typeMap": "TYPE_MAP"}.get(attr):
        warnings.warn(f"{attr} is deprecated. Please use {newAttr} instead.", DeprecationWarning)
        return globals()[newAttr]
    raise AttributeError(attr)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_lua_builtins.py ===
"""
    pygments.lexers._lua_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This file contains the names and modules of lua functions
    It is able to re-generate itself, but for adding new functions you
    probably have to add some callbacks (see function module_callbacks).

    Do not edit the MODULES dict by hand.

    Run with `python -I` to regenerate.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

MODULES = {'basic': ('_G',
           '_VERSION',
           'assert',
           'collectgarbage',
           'dofile',
           'error',
           'getmetatable',
           'ipairs',
           'load',
           'loadfile',
           'next',
           'pairs',
           'pcall',
           'print',
           'rawequal',
           'rawget',
           'rawlen',
           'rawset',
           'select',
           'setmetatable',
           'tonumber',
           'tostring',
           'type',
           'warn',
           'xpcall'),
 'bit32': ('bit32.arshift',
           'bit32.band',
           'bit32.bnot',
           'bit32.bor',
           'bit32.btest',
           'bit32.bxor',
           'bit32.extract',
           'bit32.lrotate',
           'bit32.lshift',
           'bit32.replace',
           'bit32.rrotate',
           'bit32.rshift'),
 'coroutine': ('coroutine.close',
               'coroutine.create',
               'coroutine.isyieldable',
               'coroutine.resume',
               'coroutine.running',
               'coroutine.status',
               'coroutine.wrap',
               'coroutine.yield'),
 'debug': ('debug.debug',
           'debug.gethook',
           'debug.getinfo',
           'debug.getlocal',
           'debug.getmetatable',
           'debug.getregistry',
           'debug.getupvalue',
           'debug.getuservalue',
           'debug.sethook',
           'debug.setlocal',
           'debug.setmetatable',
           'debug.setupvalue',
           'debug.setuservalue',
           'debug.traceback',
           'debug.upvalueid',
           'debug.upvaluejoin'),
 'io': ('io.close',
        'io.flush',
        'io.input',
        'io.lines',
        'io.open',
        'io.output',
        'io.popen',
        'io.read',
        'io.stderr',
        'io.stdin',
        'io.stdout',
        'io.tmpfile',
        'io.type',
        'io.write'),
 'math': ('math.abs',
          'math.acos',
          'math.asin',
          'math.atan',
          'math.atan2',
          'math.ceil',
          'math.cos',
          'math.cosh',
          'math.deg',
          'math.exp',
          'math.floor',
          'math.fmod',
          'math.frexp',
          'math.huge',
          'math.ldexp',
          'math.log',
          'math.max',
          'math.maxinteger',
          'math.min',
          'math.mininteger',
          'math.modf',
          'math.pi',
          'math.pow',
          'math.rad',
          'math.random',
          'math.randomseed',
          'math.sin',
          'math.sinh',
          'math.sqrt',
          'math.tan',
          'math.tanh',
          'math.tointeger',
          'math.type',
          'math.ult'),
 'modules': ('package.config',
             'package.cpath',
             'package.loaded',
             'package.loadlib',
             'package.path',
             'package.preload',
             'package.searchers',
             'package.searchpath',
             'require'),
 'os': ('os.clock',
        'os.date',
        'os.difftime',
        'os.execute',
        'os.exit',
        'os.getenv',
        'os.remove',
        'os.rename',
        'os.setlocale',
        'os.time',
        'os.tmpname'),
 'string': ('string.byte',
            'string.char',
            'string.dump',
            'string.find',
            'string.format',
            'string.gmatch',
            'string.gsub',
            'string.len',
            'string.lower',
            'string.match',
            'string.pack',
            'string.packsize',
            'string.rep',
            'string.reverse',
            'string.sub',
            'string.unpack',
            'string.upper'),
 'table': ('table.concat',
           'table.insert',
           'table.move',
           'table.pack',
           'table.remove',
           'table.sort',
           'table.unpack'),
 'utf8': ('utf8.char',
          'utf8.charpattern',
          'utf8.codepoint',
          'utf8.codes',
          'utf8.len',
          'utf8.offset')}

if __name__ == '__main__':  # pragma: no cover
    import re
    from urllib.request import urlopen
    import pprint

    # you can't generally find out what module a function belongs to if you
    # have only its name. Because of this, here are some callback functions
    # that recognize if a gioven function belongs to a specific module
    def module_callbacks():
        def is_in_coroutine_module(name):
            return name.startswith('coroutine.')

        def is_in_modules_module(name):
            if name in ['require', 'module'] or name.startswith('package'):
                return True
            else:
                return False

        def is_in_string_module(name):
            return name.startswith('string.')

        def is_in_table_module(name):
            return name.startswith('table.')

        def is_in_math_module(name):
            return name.startswith('math')

        def is_in_io_module(name):
            return name.startswith('io.')

        def is_in_os_module(name):
            return name.startswith('os.')

        def is_in_debug_module(name):
            return name.startswith('debug.')

        return {'coroutine': is_in_coroutine_module,
                'modules': is_in_modules_module,
                'string': is_in_string_module,
                'table': is_in_table_module,
                'math': is_in_math_module,
                'io': is_in_io_module,
                'os': is_in_os_module,
                'debug': is_in_debug_module}



    def get_newest_version():
        f = urlopen('http://www.lua.org/manual/')
        r = re.compile(r'^<A HREF="(\d\.\d)/">(Lua )?\1</A>')
        for line in f:
            m = r.match(line.decode('iso-8859-1'))
            if m is not None:
                return m.groups()[0]

    def get_lua_functions(version):
        f = urlopen(f'http://www.lua.org/manual/{version}/')
        r = re.compile(r'^<A HREF="manual.html#pdf-(?!lua|LUA)([^:]+)">\1</A>')
        functions = []
        for line in f:
            m = r.match(line.decode('iso-8859-1'))
            if m is not None:
                functions.append(m.groups()[0])
        return functions

    def get_function_module(name):
        for mod, cb in module_callbacks().items():
            if cb(name):
                return mod
        if '.' in name:
            return name.split('.')[0]
        else:
            return 'basic'

    def regenerate(filename, modules):
        with open(filename, encoding='utf-8') as fp:
            content = fp.read()

        header = content[:content.find('MODULES = {')]
        footer = content[content.find("if __name__ == '__main__':"):]


        with open(filename, 'w', encoding='utf-8') as fp:
            fp.write(header)
            fp.write(f'MODULES = {pprint.pformat(modules)}\n\n')
            fp.write(footer)

    def run():
        version = get_newest_version()
        functions = set()
        for v in ('5.2', version):
            print(f'> Downloading function index for Lua {v}')
            f = get_lua_functions(v)
            print('> %d functions found, %d new:' %
                  (len(f), len(set(f) - functions)))
            functions |= set(f)

        functions = sorted(functions)

        modules = {}
        for full_function_name in functions:
            print(f'>> {full_function_name}')
            m = get_function_module(full_function_name)
            modules.setdefault(m, []).append(full_function_name)
        modules = {k: tuple(v) for k, v in modules.items()}

        regenerate(__file__, modules)

    run()

# === NexusCore/myenv\Lib\site-packages\pip\_internal\index\sources.py ===
import logging
import mimetypes
import os
from collections import defaultdict
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from pip._vendor.packaging.utils import (
    InvalidSdistFilename,
    InvalidWheelFilename,
    canonicalize_name,
    parse_sdist_filename,
    parse_wheel_filename,
)

from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link
from pip._internal.utils.urls import path_to_url, url_to_path
from pip._internal.vcs import is_url

logger = logging.getLogger(__name__)

FoundCandidates = Iterable[InstallationCandidate]
FoundLinks = Iterable[Link]
CandidatesFromPage = Callable[[Link], Iterable[InstallationCandidate]]
PageValidator = Callable[[Link], bool]


class LinkSource:
    @property
    def link(self) -> Optional[Link]:
        """Returns the underlying link, if there's one."""
        raise NotImplementedError()

    def page_candidates(self) -> FoundCandidates:
        """Candidates found by parsing an archive listing HTML file."""
        raise NotImplementedError()

    def file_links(self) -> FoundLinks:
        """Links found by specifying archives directly."""
        raise NotImplementedError()


def _is_html_file(file_url: str) -> bool:
    return mimetypes.guess_type(file_url, strict=False)[0] == "text/html"


class _FlatDirectoryToUrls:
    """Scans directory and caches results"""

    def __init__(self, path: str) -> None:
        self._path = path
        self._page_candidates: List[str] = []
        self._project_name_to_urls: Dict[str, List[str]] = defaultdict(list)
        self._scanned_directory = False

    def _scan_directory(self) -> None:
        """Scans directory once and populates both page_candidates
        and project_name_to_urls at the same time
        """
        for entry in os.scandir(self._path):
            url = path_to_url(entry.path)
            if _is_html_file(url):
                self._page_candidates.append(url)
                continue

            # File must have a valid wheel or sdist name,
            # otherwise not worth considering as a package
            try:
                project_filename = parse_wheel_filename(entry.name)[0]
            except InvalidWheelFilename:
                try:
                    project_filename = parse_sdist_filename(entry.name)[0]
                except InvalidSdistFilename:
                    continue

            self._project_name_to_urls[project_filename].append(url)
        self._scanned_directory = True

    @property
    def page_candidates(self) -> List[str]:
        if not self._scanned_directory:
            self._scan_directory()

        return self._page_candidates

    @property
    def project_name_to_urls(self) -> Dict[str, List[str]]:
        if not self._scanned_directory:
            self._scan_directory()

        return self._project_name_to_urls


class _FlatDirectorySource(LinkSource):
    """Link source specified by ``--find-links=<path-to-dir>``.

    This looks the content of the directory, and returns:

    * ``page_candidates``: Links listed on each HTML file in the directory.
    * ``file_candidates``: Archives in the directory.
    """

    _paths_to_urls: Dict[str, _FlatDirectoryToUrls] = {}

    def __init__(
        self,
        candidates_from_page: CandidatesFromPage,
        path: str,
        project_name: str,
    ) -> None:
        self._candidates_from_page = candidates_from_page
        self._project_name = canonicalize_name(project_name)

        # Get existing instance of _FlatDirectoryToUrls if it exists
        if path in self._paths_to_urls:
            self._path_to_urls = self._paths_to_urls[path]
        else:
            self._path_to_urls = _FlatDirectoryToUrls(path=path)
            self._paths_to_urls[path] = self._path_to_urls

    @property
    def link(self) -> Optional[Link]:
        return None

    def page_candidates(self) -> FoundCandidates:
        for url in self._path_to_urls.page_candidates:
            yield from self._candidates_from_page(Link(url))

    def file_links(self) -> FoundLinks:
        for url in self._path_to_urls.project_name_to_urls[self._project_name]:
            yield Link(url)


class _LocalFileSource(LinkSource):
    """``--find-links=<path-or-url>`` or ``--[extra-]index-url=<path-or-url>``.

    If a URL is supplied, it must be a ``file:`` URL. If a path is supplied to
    the option, it is converted to a URL first. This returns:

    * ``page_candidates``: Links listed on an HTML file.
    * ``file_candidates``: The non-HTML file.
    """

    def __init__(
        self,
        candidates_from_page: CandidatesFromPage,
        link: Link,
    ) -> None:
        self._candidates_from_page = candidates_from_page
        self._link = link

    @property
    def link(self) -> Optional[Link]:
        return self._link

    def page_candidates(self) -> FoundCandidates:
        if not _is_html_file(self._link.url):
            return
        yield from self._candidates_from_page(self._link)

    def file_links(self) -> FoundLinks:
        if _is_html_file(self._link.url):
            return
        yield self._link


class _RemoteFileSource(LinkSource):
    """``--find-links=<url>`` or ``--[extra-]index-url=<url>``.

    This returns:

    * ``page_candidates``: Links listed on an HTML file.
    * ``file_candidates``: The non-HTML file.
    """

    def __init__(
        self,
        candidates_from_page: CandidatesFromPage,
        page_validator: PageValidator,
        link: Link,
    ) -> None:
        self._candidates_from_page = candidates_from_page
        self._page_validator = page_validator
        self._link = link

    @property
    def link(self) -> Optional[Link]:
        return self._link

    def page_candidates(self) -> FoundCandidates:
        if not self._page_validator(self._link):
            return
        yield from self._candidates_from_page(self._link)

    def file_links(self) -> FoundLinks:
        yield self._link


class _IndexDirectorySource(LinkSource):
    """``--[extra-]index-url=<path-to-directory>``.

    This is treated like a remote URL; ``candidates_from_page`` contains logic
    for this by appending ``index.html`` to the link.
    """

    def __init__(
        self,
        candidates_from_page: CandidatesFromPage,
        link: Link,
    ) -> None:
        self._candidates_from_page = candidates_from_page
        self._link = link

    @property
    def link(self) -> Optional[Link]:
        return self._link

    def page_candidates(self) -> FoundCandidates:
        yield from self._candidates_from_page(self._link)

    def file_links(self) -> FoundLinks:
        return ()


def build_source(
    location: str,
    *,
    candidates_from_page: CandidatesFromPage,
    page_validator: PageValidator,
    expand_dir: bool,
    cache_link_parsing: bool,
    project_name: str,
) -> Tuple[Optional[str], Optional[LinkSource]]:
    path: Optional[str] = None
    url: Optional[str] = None
    if os.path.exists(location):  # Is a local path.
        url = path_to_url(location)
        path = location
    elif location.startswith("file:"):  # A file: URL.
        url = location
        path = url_to_path(location)
    elif is_url(location):
        url = location

    if url is None:
        msg = (
            "Location '%s' is ignored: "
            "it is either a non-existing path or lacks a specific scheme."
        )
        logger.warning(msg, location)
        return (None, None)

    if path is None:
        source: LinkSource = _RemoteFileSource(
            candidates_from_page=candidates_from_page,
            page_validator=page_validator,
            link=Link(url, cache_link_parsing=cache_link_parsing),
        )
        return (url, source)

    if os.path.isdir(path):
        if expand_dir:
            source = _FlatDirectorySource(
                candidates_from_page=candidates_from_page,
                path=path,
                project_name=project_name,
            )
        else:
            source = _IndexDirectorySource(
                candidates_from_page=candidates_from_page,
                link=Link(url, cache_link_parsing=cache_link_parsing),
            )
        return (url, source)
    elif os.path.isfile(path):
        source = _LocalFileSource(
            candidates_from_page=candidates_from_page,
            link=Link(url, cache_link_parsing=cache_link_parsing),
        )
        return (url, source)
    logger.warning(
        "Location '%s' is ignored: it is neither a file nor a directory.",
        location,
    )
    return (url, None)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\pydev_log.py ===
from _pydevd_bundle.pydevd_constants import DebugInfoHolder, SHOW_COMPILE_CYTHON_COMMAND_LINE, NULL, LOG_TIME, ForkSafeLock
from contextlib import contextmanager
import traceback
import os
import sys


class _LoggingGlobals(object):
    _warn_once_map = {}
    _debug_stream_filename = None
    _debug_stream = NULL
    _debug_stream_initialized = False
    _initialize_lock = ForkSafeLock()


def initialize_debug_stream(reinitialize=False):
    """
    :param bool reinitialize:
        Reinitialize is used to update the debug stream after a fork (thus, if it wasn't
        initialized, we don't need to do anything, just wait for the first regular log call
        to initialize).
    """
    if reinitialize:
        if not _LoggingGlobals._debug_stream_initialized:
            return
    else:
        if _LoggingGlobals._debug_stream_initialized:
            return

    with _LoggingGlobals._initialize_lock:
        # Initialization is done lazilly, so, it's possible that multiple threads try to initialize
        # logging.

        # Check initial conditions again after obtaining the lock.
        if reinitialize:
            if not _LoggingGlobals._debug_stream_initialized:
                return
        else:
            if _LoggingGlobals._debug_stream_initialized:
                return

        _LoggingGlobals._debug_stream_initialized = True

        # Note: we cannot initialize with sys.stderr because when forking we may end up logging things in 'os' calls.
        _LoggingGlobals._debug_stream = NULL
        _LoggingGlobals._debug_stream_filename = None

        if not DebugInfoHolder.PYDEVD_DEBUG_FILE:
            _LoggingGlobals._debug_stream = sys.stderr
        else:
            # Add pid to the filename.
            try:
                target_file = DebugInfoHolder.PYDEVD_DEBUG_FILE
                debug_file = _compute_filename_with_pid(target_file)
                _LoggingGlobals._debug_stream = open(debug_file, "w")
                _LoggingGlobals._debug_stream_filename = debug_file
            except Exception:
                _LoggingGlobals._debug_stream = sys.stderr
                # Don't fail when trying to setup logging, just show the exception.
                traceback.print_exc()


def _compute_filename_with_pid(target_file, pid=None):
    # Note: used in tests.
    dirname = os.path.dirname(target_file)
    basename = os.path.basename(target_file)
    try:
        os.makedirs(dirname)
    except Exception:
        pass  # Ignore error if it already exists.

    name, ext = os.path.splitext(basename)
    if pid is None:
        pid = os.getpid()
    return os.path.join(dirname, "%s.%s%s" % (name, pid, ext))


def log_to(log_file: str, log_level: int = 3) -> None:
    with _LoggingGlobals._initialize_lock:
        # Can be set directly.
        DebugInfoHolder.DEBUG_TRACE_LEVEL = log_level

        if DebugInfoHolder.PYDEVD_DEBUG_FILE != log_file:
            # Note that we don't need to reset it unless it actually changed
            # (would be the case where it's set as an env var in a new process
            # and a subprocess initializes logging to the same value).
            _LoggingGlobals._debug_stream = NULL
            _LoggingGlobals._debug_stream_filename = None

            DebugInfoHolder.PYDEVD_DEBUG_FILE = log_file

            _LoggingGlobals._debug_stream_initialized = False


def list_log_files(pydevd_debug_file):
    log_files = []
    dirname = os.path.dirname(pydevd_debug_file)
    basename = os.path.basename(pydevd_debug_file)
    if os.path.isdir(dirname):
        name, ext = os.path.splitext(basename)
        for f in os.listdir(dirname):
            if f.startswith(name) and f.endswith(ext):
                log_files.append(os.path.join(dirname, f))
    return log_files


@contextmanager
def log_context(trace_level, stream):
    """
    To be used to temporarily change the logging settings.
    """
    with _LoggingGlobals._initialize_lock:
        original_trace_level = DebugInfoHolder.DEBUG_TRACE_LEVEL
        original_debug_stream = _LoggingGlobals._debug_stream
        original_pydevd_debug_file = DebugInfoHolder.PYDEVD_DEBUG_FILE
        original_debug_stream_filename = _LoggingGlobals._debug_stream_filename
        original_initialized = _LoggingGlobals._debug_stream_initialized

        DebugInfoHolder.DEBUG_TRACE_LEVEL = trace_level
        _LoggingGlobals._debug_stream = stream
        _LoggingGlobals._debug_stream_initialized = True
    try:
        yield
    finally:
        with _LoggingGlobals._initialize_lock:
            DebugInfoHolder.DEBUG_TRACE_LEVEL = original_trace_level
            _LoggingGlobals._debug_stream = original_debug_stream
            DebugInfoHolder.PYDEVD_DEBUG_FILE = original_pydevd_debug_file
            _LoggingGlobals._debug_stream_filename = original_debug_stream_filename
            _LoggingGlobals._debug_stream_initialized = original_initialized


import time

_last_log_time = time.time()

# Set to True to show pid in each logged message (usually the file has it, but sometimes it's handy).
_LOG_PID = False


def _pydevd_log(level, msg, *args):
    """
    Levels are:

    0 most serious warnings/errors (always printed)
    1 warnings/significant events
    2 informational trace
    3 verbose mode
    """
    if level <= DebugInfoHolder.DEBUG_TRACE_LEVEL:
        # yes, we can have errors printing if the console of the program has been finished (and we're still trying to print something)
        try:
            try:
                if args:
                    msg = msg % args
            except:
                msg = "%s - %s" % (msg, args)

            if LOG_TIME:
                global _last_log_time
                new_log_time = time.time()
                time_diff = new_log_time - _last_log_time
                _last_log_time = new_log_time
                msg = "%.2fs - %s\n" % (
                    time_diff,
                    msg,
                )
            else:
                msg = "%s\n" % (msg,)

            if _LOG_PID:
                msg = "<%s> - %s\n" % (
                    os.getpid(),
                    msg,
                )

            try:
                try:
                    initialize_debug_stream()  # Do it as late as possible
                    _LoggingGlobals._debug_stream.write(msg)
                except TypeError:
                    if isinstance(msg, bytes):
                        # Depending on the StringIO flavor, it may only accept unicode.
                        msg = msg.decode("utf-8", "replace")
                        _LoggingGlobals._debug_stream.write(msg)
            except UnicodeEncodeError:
                # When writing to the stream it's possible that the string can't be represented
                # in the encoding expected (in this case, convert it to the stream encoding
                # or ascii if we can't find one suitable using a suitable replace).
                encoding = getattr(_LoggingGlobals._debug_stream, "encoding", "ascii")
                msg = msg.encode(encoding, "backslashreplace")
                msg = msg.decode(encoding)
                _LoggingGlobals._debug_stream.write(msg)

            _LoggingGlobals._debug_stream.flush()
        except:
            pass
        return True


def _pydevd_log_exception(msg="", *args):
    if msg or args:
        _pydevd_log(0, msg, *args)
    try:
        initialize_debug_stream()  # Do it as late as possible
        traceback.print_exc(file=_LoggingGlobals._debug_stream)
        _LoggingGlobals._debug_stream.flush()
    except:
        raise


def verbose(msg, *args):
    if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 3:
        _pydevd_log(3, msg, *args)


def debug(msg, *args):
    if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 2:
        _pydevd_log(2, msg, *args)


def info(msg, *args):
    if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 1:
        _pydevd_log(1, msg, *args)


warn = info


def critical(msg, *args):
    _pydevd_log(0, msg, *args)


def exception(msg="", *args):
    try:
        _pydevd_log_exception(msg, *args)
    except:
        pass  # Should never fail (even at interpreter shutdown).


error = exception


def error_once(msg, *args):
    try:
        if args:
            message = msg % args
        else:
            message = str(msg)
    except:
        message = "%s - %s" % (msg, args)

    if message not in _LoggingGlobals._warn_once_map:
        _LoggingGlobals._warn_once_map[message] = True
        critical(message)


def exception_once(msg, *args):
    try:
        if args:
            message = msg % args
        else:
            message = str(msg)
    except:
        message = "%s - %s" % (msg, args)

    if message not in _LoggingGlobals._warn_once_map:
        _LoggingGlobals._warn_once_map[message] = True
        exception(message)


def debug_once(msg, *args):
    if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 3:
        error_once(msg, *args)


def show_compile_cython_command_line():
    if SHOW_COMPILE_CYTHON_COMMAND_LINE:
        dirname = os.path.dirname(os.path.dirname(__file__))
        error_once(
            'warning: Debugger speedups using cython not found. Run \'"%s" "%s" build_ext --inplace\' to build.',
            sys.executable,
            os.path.join(dirname, "setup_pydevd_cython.py"),
        )

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\permission_service\transports\base.py ===
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
from google.ai.generativelanguage_v1beta.types import permission as gag_permission
from google.ai.generativelanguage_v1beta.types import permission
from google.ai.generativelanguage_v1beta.types import permission_service

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class PermissionServiceTransport(abc.ABC):
    """Abstract transport class for PermissionService."""

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
            self.create_permission: gapic_v1.method.wrap_method(
                self.create_permission,
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
            self.get_permission: gapic_v1.method.wrap_method(
                self.get_permission,
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
            self.list_permissions: gapic_v1.method.wrap_method(
                self.list_permissions,
                default_timeout=None,
                client_info=client_info,
            ),
            self.update_permission: gapic_v1.method.wrap_method(
                self.update_permission,
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
            self.delete_permission: gapic_v1.method.wrap_method(
                self.delete_permission,
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
            self.transfer_ownership: gapic_v1.method.wrap_method(
                self.transfer_ownership,
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
    def create_permission(
        self,
    ) -> Callable[
        [permission_service.CreatePermissionRequest],
        Union[gag_permission.Permission, Awaitable[gag_permission.Permission]],
    ]:
        raise NotImplementedError()

    @property
    def get_permission(
        self,
    ) -> Callable[
        [permission_service.GetPermissionRequest],
        Union[permission.Permission, Awaitable[permission.Permission]],
    ]:
        raise NotImplementedError()

    @property
    def list_permissions(
        self,
    ) -> Callable[
        [permission_service.ListPermissionsRequest],
        Union[
            permission_service.ListPermissionsResponse,
            Awaitable[permission_service.ListPermissionsResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def update_permission(
        self,
    ) -> Callable[
        [permission_service.UpdatePermissionRequest],
        Union[gag_permission.Permission, Awaitable[gag_permission.Permission]],
    ]:
        raise NotImplementedError()

    @property
    def delete_permission(
        self,
    ) -> Callable[
        [permission_service.DeletePermissionRequest],
        Union[empty_pb2.Empty, Awaitable[empty_pb2.Empty]],
    ]:
        raise NotImplementedError()

    @property
    def transfer_ownership(
        self,
    ) -> Callable[
        [permission_service.TransferOwnershipRequest],
        Union[
            permission_service.TransferOwnershipResponse,
            Awaitable[permission_service.TransferOwnershipResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("PermissionServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\common_utils\html_forms\jwt_display_template.py ===
# JWT display template for SSO debug callback
jwt_display_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LiteLLM SSO Debug - JWT Information</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: #f8fafc;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            color: #333;
        }

        .container {
            background-color: #fff;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            width: 800px;
            max-width: 100%;
        }
        
        .logo-container {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .logo {
            font-size: 24px;
            font-weight: 600;
            color: #1e293b;
        }
        
        h2 {
            margin: 0 0 10px;
            color: #1e293b;
            font-size: 28px;
            font-weight: 600;
            text-align: center;
        }
        
        .subtitle {
            color: #64748b;
            margin: 0 0 20px;
            font-size: 16px;
            text-align: center;
        }

        .info-box {
            background-color: #f1f5f9;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 30px;
            border-left: 4px solid #2563eb;
        }
        
        .success-box {
            background-color: #f0fdf4;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 30px;
            border-left: 4px solid #16a34a;
        }

        .info-header {
            display: flex;
            align-items: center;
            margin-bottom: 12px;
            color: #1e40af;
            font-weight: 600;
            font-size: 16px;
        }
        
        .success-header {
            display: flex;
            align-items: center;
            margin-bottom: 12px;
            color: #166534;
            font-weight: 600;
            font-size: 16px;
        }
        
        .info-header svg, .success-header svg {
            margin-right: 8px;
        }
        
        .data-container {
            margin-top: 20px;
        }
        
        .data-row {
            display: flex;
            border-bottom: 1px solid #e2e8f0;
            padding: 12px 0;
        }
        
        .data-row:last-child {
            border-bottom: none;
        }
        
        .data-label {
            font-weight: 500;
            color: #334155;
            width: 180px;
            flex-shrink: 0;
        }
        
        .data-value {
            color: #475569;
            word-break: break-all;
        }
        
        .jwt-container {
            background-color: #f8fafc;
            border-radius: 6px;
            padding: 15px;
            margin-top: 20px;
            overflow-x: auto;
            border: 1px solid #e2e8f0;
        }
        
        .jwt-text {
            font-family: monospace;
            white-space: pre-wrap;
            word-break: break-all;
            margin: 0;
            color: #334155;
        }
        
        .back-button {
            display: inline-block;
            background-color: #6466E9;
            color: #fff;
            text-decoration: none;
            padding: 10px 16px;
            border-radius: 6px;
            font-weight: 500;
            margin-top: 20px;
            text-align: center;
        }
        
        .back-button:hover {
            background-color: #4138C2;
            text-decoration: none;
        }
        
        .buttons {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        .copy-button {
            background-color: #e2e8f0;
            color: #334155;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
        }
        
        .copy-button:hover {
            background-color: #cbd5e1;
        }
        
        .copy-button svg {
            margin-right: 6px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-container">
            <div class="logo">
                🚅 LiteLLM
            </div>
        </div>
        <h2>SSO Debug Information</h2>
        <p class="subtitle">Results from the SSO authentication process.</p>
        
        <div class="success-box">
            <div class="success-header">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                Authentication Successful
            </div>
            <p>The SSO authentication completed successfully. Below is the information returned by the provider.</p>
        </div>
        
        <div class="data-container" id="userData">
            <!-- Data will be inserted here by JavaScript -->
        </div>
        
        <div class="info-box">
            <div class="info-header">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="16" x2="12" y2="12"></line>
                    <line x1="12" y1="8" x2="12.01" y2="8"></line>
                </svg>
                JSON Representation
            </div>
            <div class="jwt-container">
                <pre class="jwt-text" id="jsonData">Loading...</pre>
            </div>
            <div class="buttons">
                <button class="copy-button" onclick="copyToClipboard('jsonData')">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    Copy to Clipboard
                </button>
            </div>
        </div>
        
        <a href="/sso/debug/login" class="back-button">
            Try Another SSO Login
        </a>
    </div>

    <script>
        // This will be populated with the actual data from the server
        const userData = SSO_DATA;
        
        function renderUserData() {
            const container = document.getElementById('userData');
            const jsonDisplay = document.getElementById('jsonData');
            
            // Format JSON with indentation for display
            jsonDisplay.textContent = JSON.stringify(userData, null, 2);
            
            // Clear container
            container.innerHTML = '';
            
            // Add each key-value pair to the UI
            for (const [key, value] of Object.entries(userData)) {
                if (typeof value !== 'object' || value === null) {
                    const row = document.createElement('div');
                    row.className = 'data-row';
                    
                    const label = document.createElement('div');
                    label.className = 'data-label';
                    label.textContent = key;
                    
                    const dataValue = document.createElement('div');
                    dataValue.className = 'data-value';
                    dataValue.textContent = value !== null ? value : 'null';
                    
                    row.appendChild(label);
                    row.appendChild(dataValue);
                    container.appendChild(row);
                }
            }
        }
        
        function copyToClipboard(elementId) {
            const text = document.getElementById(elementId).textContent;
            navigator.clipboard.writeText(text).then(() => {
                alert('Copied to clipboard!');
            }).catch(err => {
                console.error('Could not copy text: ', err);
            });
        }
        
        // Render the data when the page loads
        document.addEventListener('DOMContentLoaded', renderUserData);
    </script>
</body>
</html>
"""

# === NexusCore/openenv\Lib\site-packages\pip\_internal\index\sources.py ===
import logging
import mimetypes
import os
from collections import defaultdict
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from pip._vendor.packaging.utils import (
    InvalidSdistFilename,
    InvalidWheelFilename,
    canonicalize_name,
    parse_sdist_filename,
    parse_wheel_filename,
)

from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link
from pip._internal.utils.urls import path_to_url, url_to_path
from pip._internal.vcs import is_url

logger = logging.getLogger(__name__)

FoundCandidates = Iterable[InstallationCandidate]
FoundLinks = Iterable[Link]
CandidatesFromPage = Callable[[Link], Iterable[InstallationCandidate]]
PageValidator = Callable[[Link], bool]


class LinkSource:
    @property
    def link(self) -> Optional[Link]:
        """Returns the underlying link, if there's one."""
        raise NotImplementedError()

    def page_candidates(self) -> FoundCandidates:
        """Candidates found by parsing an archive listing HTML file."""
        raise NotImplementedError()

    def file_links(self) -> FoundLinks:
        """Links found by specifying archives directly."""
        raise NotImplementedError()


def _is_html_file(file_url: str) -> bool:
    return mimetypes.guess_type(file_url, strict=False)[0] == "text/html"


class _FlatDirectoryToUrls:
    """Scans directory and caches results"""

    def __init__(self, path: str) -> None:
        self._path = path
        self._page_candidates: List[str] = []
        self._project_name_to_urls: Dict[str, List[str]] = defaultdict(list)
        self._scanned_directory = False

    def _scan_directory(self) -> None:
        """Scans directory once and populates both page_candidates
        and project_name_to_urls at the same time
        """
        for entry in os.scandir(self._path):
            url = path_to_url(entry.path)
            if _is_html_file(url):
                self._page_candidates.append(url)
                continue

            # File must have a valid wheel or sdist name,
            # otherwise not worth considering as a package
            try:
                project_filename = parse_wheel_filename(entry.name)[0]
            except InvalidWheelFilename:
                try:
                    project_filename = parse_sdist_filename(entry.name)[0]
                except InvalidSdistFilename:
                    continue

            self._project_name_to_urls[project_filename].append(url)
        self._scanned_directory = True

    @property
    def page_candidates(self) -> List[str]:
        if not self._scanned_directory:
            self._scan_directory()

        return self._page_candidates

    @property
    def project_name_to_urls(self) -> Dict[str, List[str]]:
        if not self._scanned_directory:
            self._scan_directory()

        return self._project_name_to_urls


class _FlatDirectorySource(LinkSource):
    """Link source specified by ``--find-links=<path-to-dir>``.

    This looks the content of the directory, and returns:

    * ``page_candidates``: Links listed on each HTML file in the directory.
    * ``file_candidates``: Archives in the directory.
    """

    _paths_to_urls: Dict[str, _FlatDirectoryToUrls] = {}

    def __init__(
        self,
        candidates_from_page: CandidatesFromPage,
        path: str,
        project_name: str,
    ) -> None:
        self._candidates_from_page = candidates_from_page
        self._project_name = canonicalize_name(project_name)

        # Get existing instance of _FlatDirectoryToUrls if it exists
        if path in self._paths_to_urls:
            self._path_to_urls = self._paths_to_urls[path]
        else:
            self._path_to_urls = _FlatDirectoryToUrls(path=path)
            self._paths_to_urls[path] = self._path_to_urls

    @property
    def link(self) -> Optional[Link]:
        return None

    def page_candidates(self) -> FoundCandidates:
        for url in self._path_to_urls.page_candidates:
            yield from self._candidates_from_page(Link(url))

    def file_links(self) -> FoundLinks:
        for url in self._path_to_urls.project_name_to_urls[self._project_name]:
            yield Link(url)


class _LocalFileSource(LinkSource):
    """``--find-links=<path-or-url>`` or ``--[extra-]index-url=<path-or-url>``.

    If a URL is supplied, it must be a ``file:`` URL. If a path is supplied to
    the option, it is converted to a URL first. This returns:

    * ``page_candidates``: Links listed on an HTML file.
    * ``file_candidates``: The non-HTML file.
    """

    def __init__(
        self,
        candidates_from_page: CandidatesFromPage,
        link: Link,
    ) -> None:
        self._candidates_from_page = candidates_from_page
        self._link = link

    @property
    def link(self) -> Optional[Link]:
        return self._link

    def page_candidates(self) -> FoundCandidates:
        if not _is_html_file(self._link.url):
            return
        yield from self._candidates_from_page(self._link)

    def file_links(self) -> FoundLinks:
        if _is_html_file(self._link.url):
            return
        yield self._link


class _RemoteFileSource(LinkSource):
    """``--find-links=<url>`` or ``--[extra-]index-url=<url>``.

    This returns:

    * ``page_candidates``: Links listed on an HTML file.
    * ``file_candidates``: The non-HTML file.
    """

    def __init__(
        self,
        candidates_from_page: CandidatesFromPage,
        page_validator: PageValidator,
        link: Link,
    ) -> None:
        self._candidates_from_page = candidates_from_page
        self._page_validator = page_validator
        self._link = link

    @property
    def link(self) -> Optional[Link]:
        return self._link

    def page_candidates(self) -> FoundCandidates:
        if not self._page_validator(self._link):
            return
        yield from self._candidates_from_page(self._link)

    def file_links(self) -> FoundLinks:
        yield self._link


class _IndexDirectorySource(LinkSource):
    """``--[extra-]index-url=<path-to-directory>``.

    This is treated like a remote URL; ``candidates_from_page`` contains logic
    for this by appending ``index.html`` to the link.
    """

    def __init__(
        self,
        candidates_from_page: CandidatesFromPage,
        link: Link,
    ) -> None:
        self._candidates_from_page = candidates_from_page
        self._link = link

    @property
    def link(self) -> Optional[Link]:
        return self._link

    def page_candidates(self) -> FoundCandidates:
        yield from self._candidates_from_page(self._link)

    def file_links(self) -> FoundLinks:
        return ()


def build_source(
    location: str,
    *,
    candidates_from_page: CandidatesFromPage,
    page_validator: PageValidator,
    expand_dir: bool,
    cache_link_parsing: bool,
    project_name: str,
) -> Tuple[Optional[str], Optional[LinkSource]]:
    path: Optional[str] = None
    url: Optional[str] = None
    if os.path.exists(location):  # Is a local path.
        url = path_to_url(location)
        path = location
    elif location.startswith("file:"):  # A file: URL.
        url = location
        path = url_to_path(location)
    elif is_url(location):
        url = location

    if url is None:
        msg = (
            "Location '%s' is ignored: "
            "it is either a non-existing path or lacks a specific scheme."
        )
        logger.warning(msg, location)
        return (None, None)

    if path is None:
        source: LinkSource = _RemoteFileSource(
            candidates_from_page=candidates_from_page,
            page_validator=page_validator,
            link=Link(url, cache_link_parsing=cache_link_parsing),
        )
        return (url, source)

    if os.path.isdir(path):
        if expand_dir:
            source = _FlatDirectorySource(
                candidates_from_page=candidates_from_page,
                path=path,
                project_name=project_name,
            )
        else:
            source = _IndexDirectorySource(
                candidates_from_page=candidates_from_page,
                link=Link(url, cache_link_parsing=cache_link_parsing),
            )
        return (url, source)
    elif os.path.isfile(path):
        source = _LocalFileSource(
            candidates_from_page=candidates_from_page,
            link=Link(url, cache_link_parsing=cache_link_parsing),
        )
        return (url, source)
    logger.warning(
        "Location '%s' is ignored: it is neither a file nor a directory.",
        location,
    )
    return (url, None)

# === NexusCore/openenv\Lib\site-packages\pydantic\deprecated\decorator.py ===
import warnings
from collections.abc import Mapping
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar, Union, overload

from typing_extensions import deprecated

from .._internal import _config, _typing_extra
from ..alias_generators import to_pascal
from ..errors import PydanticUserError
from ..functional_validators import field_validator
from ..main import BaseModel, create_model
from ..warnings import PydanticDeprecatedSince20

if not TYPE_CHECKING:
    # See PyCharm issues https://youtrack.jetbrains.com/issue/PY-21915
    # and https://youtrack.jetbrains.com/issue/PY-51428
    DeprecationWarning = PydanticDeprecatedSince20

__all__ = ('validate_arguments',)

if TYPE_CHECKING:
    AnyCallable = Callable[..., Any]

    AnyCallableT = TypeVar('AnyCallableT', bound=AnyCallable)
    ConfigType = Union[None, type[Any], dict[str, Any]]


@overload
def validate_arguments(
    func: None = None, *, config: 'ConfigType' = None
) -> Callable[['AnyCallableT'], 'AnyCallableT']: ...


@overload
def validate_arguments(func: 'AnyCallableT') -> 'AnyCallableT': ...


@deprecated(
    'The `validate_arguments` method is deprecated; use `validate_call` instead.',
    category=None,
)
def validate_arguments(func: Optional['AnyCallableT'] = None, *, config: 'ConfigType' = None) -> Any:
    """Decorator to validate the arguments passed to a function."""
    warnings.warn(
        'The `validate_arguments` method is deprecated; use `validate_call` instead.',
        PydanticDeprecatedSince20,
        stacklevel=2,
    )

    def validate(_func: 'AnyCallable') -> 'AnyCallable':
        vd = ValidatedFunction(_func, config)

        @wraps(_func)
        def wrapper_function(*args: Any, **kwargs: Any) -> Any:
            return vd.call(*args, **kwargs)

        wrapper_function.vd = vd  # type: ignore
        wrapper_function.validate = vd.init_model_instance  # type: ignore
        wrapper_function.raw_function = vd.raw_function  # type: ignore
        wrapper_function.model = vd.model  # type: ignore
        return wrapper_function

    if func:
        return validate(func)
    else:
        return validate


ALT_V_ARGS = 'v__args'
ALT_V_KWARGS = 'v__kwargs'
V_POSITIONAL_ONLY_NAME = 'v__positional_only'
V_DUPLICATE_KWARGS = 'v__duplicate_kwargs'


class ValidatedFunction:
    def __init__(self, function: 'AnyCallable', config: 'ConfigType'):
        from inspect import Parameter, signature

        parameters: Mapping[str, Parameter] = signature(function).parameters

        if parameters.keys() & {ALT_V_ARGS, ALT_V_KWARGS, V_POSITIONAL_ONLY_NAME, V_DUPLICATE_KWARGS}:
            raise PydanticUserError(
                f'"{ALT_V_ARGS}", "{ALT_V_KWARGS}", "{V_POSITIONAL_ONLY_NAME}" and "{V_DUPLICATE_KWARGS}" '
                f'are not permitted as argument names when using the "{validate_arguments.__name__}" decorator',
                code=None,
            )

        self.raw_function = function
        self.arg_mapping: dict[int, str] = {}
        self.positional_only_args: set[str] = set()
        self.v_args_name = 'args'
        self.v_kwargs_name = 'kwargs'

        type_hints = _typing_extra.get_type_hints(function, include_extras=True)
        takes_args = False
        takes_kwargs = False
        fields: dict[str, tuple[Any, Any]] = {}
        for i, (name, p) in enumerate(parameters.items()):
            if p.annotation is p.empty:
                annotation = Any
            else:
                annotation = type_hints[name]

            default = ... if p.default is p.empty else p.default
            if p.kind == Parameter.POSITIONAL_ONLY:
                self.arg_mapping[i] = name
                fields[name] = annotation, default
                fields[V_POSITIONAL_ONLY_NAME] = list[str], None
                self.positional_only_args.add(name)
            elif p.kind == Parameter.POSITIONAL_OR_KEYWORD:
                self.arg_mapping[i] = name
                fields[name] = annotation, default
                fields[V_DUPLICATE_KWARGS] = list[str], None
            elif p.kind == Parameter.KEYWORD_ONLY:
                fields[name] = annotation, default
            elif p.kind == Parameter.VAR_POSITIONAL:
                self.v_args_name = name
                fields[name] = tuple[annotation, ...], None
                takes_args = True
            else:
                assert p.kind == Parameter.VAR_KEYWORD, p.kind
                self.v_kwargs_name = name
                fields[name] = dict[str, annotation], None
                takes_kwargs = True

        # these checks avoid a clash between "args" and a field with that name
        if not takes_args and self.v_args_name in fields:
            self.v_args_name = ALT_V_ARGS

        # same with "kwargs"
        if not takes_kwargs and self.v_kwargs_name in fields:
            self.v_kwargs_name = ALT_V_KWARGS

        if not takes_args:
            # we add the field so validation below can raise the correct exception
            fields[self.v_args_name] = list[Any], None

        if not takes_kwargs:
            # same with kwargs
            fields[self.v_kwargs_name] = dict[Any, Any], None

        self.create_model(fields, takes_args, takes_kwargs, config)

    def init_model_instance(self, *args: Any, **kwargs: Any) -> BaseModel:
        values = self.build_values(args, kwargs)
        return self.model(**values)

    def call(self, *args: Any, **kwargs: Any) -> Any:
        m = self.init_model_instance(*args, **kwargs)
        return self.execute(m)

    def build_values(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
        values: dict[str, Any] = {}
        if args:
            arg_iter = enumerate(args)
            while True:
                try:
                    i, a = next(arg_iter)
                except StopIteration:
                    break
                arg_name = self.arg_mapping.get(i)
                if arg_name is not None:
                    values[arg_name] = a
                else:
                    values[self.v_args_name] = [a] + [a for _, a in arg_iter]
                    break

        var_kwargs: dict[str, Any] = {}
        wrong_positional_args = []
        duplicate_kwargs = []
        fields_alias = [
            field.alias
            for name, field in self.model.__pydantic_fields__.items()
            if name not in (self.v_args_name, self.v_kwargs_name)
        ]
        non_var_fields = set(self.model.__pydantic_fields__) - {self.v_args_name, self.v_kwargs_name}
        for k, v in kwargs.items():
            if k in non_var_fields or k in fields_alias:
                if k in self.positional_only_args:
                    wrong_positional_args.append(k)
                if k in values:
                    duplicate_kwargs.append(k)
                values[k] = v
            else:
                var_kwargs[k] = v

        if var_kwargs:
            values[self.v_kwargs_name] = var_kwargs
        if wrong_positional_args:
            values[V_POSITIONAL_ONLY_NAME] = wrong_positional_args
        if duplicate_kwargs:
            values[V_DUPLICATE_KWARGS] = duplicate_kwargs
        return values

    def execute(self, m: BaseModel) -> Any:
        d = {
            k: v
            for k, v in m.__dict__.items()
            if k in m.__pydantic_fields_set__ or m.__pydantic_fields__[k].default_factory
        }
        var_kwargs = d.pop(self.v_kwargs_name, {})

        if self.v_args_name in d:
            args_: list[Any] = []
            in_kwargs = False
            kwargs = {}
            for name, value in d.items():
                if in_kwargs:
                    kwargs[name] = value
                elif name == self.v_args_name:
                    args_ += value
                    in_kwargs = True
                else:
                    args_.append(value)
            return self.raw_function(*args_, **kwargs, **var_kwargs)
        elif self.positional_only_args:
            args_ = []
            kwargs = {}
            for name, value in d.items():
                if name in self.positional_only_args:
                    args_.append(value)
                else:
                    kwargs[name] = value
            return self.raw_function(*args_, **kwargs, **var_kwargs)
        else:
            return self.raw_function(**d, **var_kwargs)

    def create_model(self, fields: dict[str, Any], takes_args: bool, takes_kwargs: bool, config: 'ConfigType') -> None:
        pos_args = len(self.arg_mapping)

        config_wrapper = _config.ConfigWrapper(config)

        if config_wrapper.alias_generator:
            raise PydanticUserError(
                'Setting the "alias_generator" property on custom Config for '
                '@validate_arguments is not yet supported, please remove.',
                code=None,
            )
        if config_wrapper.extra is None:
            config_wrapper.config_dict['extra'] = 'forbid'

        class DecoratorBaseModel(BaseModel):
            @field_validator(self.v_args_name, check_fields=False)
            @classmethod
            def check_args(cls, v: Optional[list[Any]]) -> Optional[list[Any]]:
                if takes_args or v is None:
                    return v

                raise TypeError(f'{pos_args} positional arguments expected but {pos_args + len(v)} given')

            @field_validator(self.v_kwargs_name, check_fields=False)
            @classmethod
            def check_kwargs(cls, v: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
                if takes_kwargs or v is None:
                    return v

                plural = '' if len(v) == 1 else 's'
                keys = ', '.join(map(repr, v.keys()))
                raise TypeError(f'unexpected keyword argument{plural}: {keys}')

            @field_validator(V_POSITIONAL_ONLY_NAME, check_fields=False)
            @classmethod
            def check_positional_only(cls, v: Optional[list[str]]) -> None:
                if v is None:
                    return

                plural = '' if len(v) == 1 else 's'
                keys = ', '.join(map(repr, v))
                raise TypeError(f'positional-only argument{plural} passed as keyword argument{plural}: {keys}')

            @field_validator(V_DUPLICATE_KWARGS, check_fields=False)
            @classmethod
            def check_duplicate_kwargs(cls, v: Optional[list[str]]) -> None:
                if v is None:
                    return

                plural = '' if len(v) == 1 else 's'
                keys = ', '.join(map(repr, v))
                raise TypeError(f'multiple values for argument{plural}: {keys}')

            model_config = config_wrapper.config_dict

        self.model = create_model(to_pascal(self.raw_function.__name__), __base__=DecoratorBaseModel, **fields)