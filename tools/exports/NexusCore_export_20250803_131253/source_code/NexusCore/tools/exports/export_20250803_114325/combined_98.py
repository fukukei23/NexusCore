
# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_api.py ===
import sys
import bisect
import types

from _pydev_bundle._pydev_saved_modules import threading
from _pydevd_bundle import pydevd_utils, pydevd_source_mapping
from _pydevd_bundle.pydevd_additional_thread_info import set_additional_thread_info
from _pydevd_bundle.pydevd_comm import (
    InternalGetThreadStack,
    internal_get_completions,
    InternalSetNextStatementThread,
    internal_reload_code,
    InternalGetVariable,
    InternalGetArray,
    InternalLoadFullValue,
    internal_get_description,
    internal_get_frame,
    internal_evaluate_expression,
    InternalConsoleExec,
    internal_get_variable_json,
    internal_change_variable,
    internal_change_variable_json,
    internal_evaluate_expression_json,
    internal_set_expression_json,
    internal_get_exception_details_json,
    internal_step_in_thread,
    internal_smart_step_into,
)
from _pydevd_bundle.pydevd_comm_constants import (
    CMD_THREAD_SUSPEND,
    file_system_encoding,
    CMD_STEP_INTO_MY_CODE,
    CMD_STOP_ON_START,
    CMD_SMART_STEP_INTO,
)
from _pydevd_bundle.pydevd_constants import (
    get_current_thread_id,
    set_protocol,
    get_protocol,
    HTTP_JSON_PROTOCOL,
    JSON_PROTOCOL,
    DebugInfoHolder,
    IS_WINDOWS,
    PYDEVD_USE_SYS_MONITORING,
)
from _pydevd_bundle.pydevd_net_command_factory_json import NetCommandFactoryJson
from _pydevd_bundle.pydevd_net_command_factory_xml import NetCommandFactory
import pydevd_file_utils
from _pydev_bundle import pydev_log
from _pydevd_bundle.pydevd_breakpoints import LineBreakpoint
from pydevd_tracing import get_exception_traceback_str
import os
import subprocess
import ctypes
from _pydevd_bundle.pydevd_collect_bytecode_info import code_to_bytecode_representation
import itertools
import linecache
from _pydevd_bundle.pydevd_utils import DAPGrouper, interrupt_main_thread
from _pydevd_bundle.pydevd_daemon_thread import run_as_pydevd_daemon_thread
from _pydevd_bundle.pydevd_thread_lifecycle import pydevd_find_thread_by_id, resume_threads
import tokenize
from _pydevd_sys_monitoring import pydevd_sys_monitoring

try:
    import dis
except ImportError:

    def _get_code_lines(code):
        raise NotImplementedError

else:

    def _get_code_lines(code):
        if not isinstance(code, types.CodeType):
            path = code
            with tokenize.open(path) as f:
                src = f.read()
            code = compile(src, path, "exec", 0, dont_inherit=True)
            return _get_code_lines(code)

        def iterate():
            # First, get all line starts for this code object. This does not include
            # bodies of nested class and function definitions, as they have their
            # own objects.
            for _, lineno in dis.findlinestarts(code):
                if lineno is not None:
                    yield lineno

            # For nested class and function definitions, their respective code objects
            # are constants referenced by this object.
            for const in code.co_consts:
                if isinstance(const, types.CodeType) and const.co_filename == code.co_filename:
                    for lineno in _get_code_lines(const):
                        yield lineno

        return iterate()


class PyDevdAPI(object):
    class VariablePresentation(object):
        def __init__(self, special="group", function="group", class_="group", protected="inline"):
            self._presentation = {
                DAPGrouper.SCOPE_SPECIAL_VARS: special,
                DAPGrouper.SCOPE_FUNCTION_VARS: function,
                DAPGrouper.SCOPE_CLASS_VARS: class_,
                DAPGrouper.SCOPE_PROTECTED_VARS: protected,
            }

        def get_presentation(self, scope):
            return self._presentation[scope]

    def run(self, py_db):
        py_db.ready_to_run = True

    def notify_initialize(self, py_db):
        py_db.on_initialize()

    def notify_configuration_done(self, py_db):
        py_db.on_configuration_done()

    def notify_disconnect(self, py_db):
        py_db.on_disconnect()

    def set_protocol(self, py_db, seq, protocol):
        set_protocol(protocol.strip())
        if get_protocol() in (HTTP_JSON_PROTOCOL, JSON_PROTOCOL):
            cmd_factory_class = NetCommandFactoryJson
        else:
            cmd_factory_class = NetCommandFactory

        if not isinstance(py_db.cmd_factory, cmd_factory_class):
            py_db.cmd_factory = cmd_factory_class()

        return py_db.cmd_factory.make_protocol_set_message(seq)

    def set_ide_os_and_breakpoints_by(self, py_db, seq, ide_os, breakpoints_by):
        """
        :param ide_os: 'WINDOWS' or 'UNIX'
        :param breakpoints_by: 'ID' or 'LINE'
        """
        if breakpoints_by == "ID":
            py_db._set_breakpoints_with_id = True
        else:
            py_db._set_breakpoints_with_id = False

        self.set_ide_os(ide_os)

        return py_db.cmd_factory.make_version_message(seq)

    def set_ide_os(self, ide_os):
        """
        :param ide_os: 'WINDOWS' or 'UNIX'
        """
        pydevd_file_utils.set_ide_os(ide_os)

    def set_gui_event_loop(self, py_db, gui_event_loop):
        py_db._gui_event_loop = gui_event_loop

    def send_error_message(self, py_db, msg):
        cmd = py_db.cmd_factory.make_warning_message("pydevd: %s\n" % (msg,))
        py_db.writer.add_command(cmd)

    def set_show_return_values(self, py_db, show_return_values):
        if show_return_values:
            py_db.show_return_values = True
        else:
            if py_db.show_return_values:
                # We should remove saved return values
                py_db.remove_return_values_flag = True
            py_db.show_return_values = False
        pydev_log.debug("Show return values: %s", py_db.show_return_values)

    def list_threads(self, py_db, seq):
        # Response is the command with the list of threads to be added to the writer thread.
        return py_db.cmd_factory.make_list_threads_message(py_db, seq)

    def request_suspend_thread(self, py_db, thread_id="*"):
        # Yes, thread suspend is done at this point, not through an internal command.
        threads = []
        suspend_all = thread_id.strip() == "*"
        if suspend_all:
            threads = pydevd_utils.get_non_pydevd_threads()

        elif thread_id.startswith("__frame__:"):
            sys.stderr.write("Can't suspend tasklet: %s\n" % (thread_id,))

        else:
            threads = [pydevd_find_thread_by_id(thread_id)]

        for t in threads:
            if t is None:
                continue
            py_db.set_suspend(
                t,
                CMD_THREAD_SUSPEND,
                suspend_other_threads=suspend_all,
                is_pause=True,
            )
            # Break here (even if it's suspend all) as py_db.set_suspend will
            # take care of suspending other threads.
            break

    def set_enable_thread_notifications(self, py_db, enable):
        """
        When disabled, no thread notifications (for creation/removal) will be
        issued until it's re-enabled.

        Note that when it's re-enabled, a creation notification will be sent for
        all existing threads even if it was previously sent (this is meant to
        be used on disconnect/reconnect).
        """
        py_db.set_enable_thread_notifications(enable)

    def request_disconnect(self, py_db, resume_threads):
        self.set_enable_thread_notifications(py_db, False)
        self.remove_all_breakpoints(py_db, "*")
        self.remove_all_exception_breakpoints(py_db)
        self.notify_disconnect(py_db)

        if resume_threads:
            self.request_resume_thread(thread_id="*")

    def request_resume_thread(self, thread_id):
        resume_threads(thread_id)

    def request_completions(self, py_db, seq, thread_id, frame_id, act_tok, line=-1, column=-1):
        py_db.post_method_as_internal_command(
            thread_id, internal_get_completions, seq, thread_id, frame_id, act_tok, line=line, column=column
        )

    def request_stack(self, py_db, seq, thread_id, fmt=None, timeout=0.5, start_frame=0, levels=0):
        # If it's already suspended, get it right away.
        internal_get_thread_stack = InternalGetThreadStack(
            seq, thread_id, py_db, set_additional_thread_info, fmt=fmt, timeout=timeout, start_frame=start_frame, levels=levels
        )
        if internal_get_thread_stack.can_be_executed_by(get_current_thread_id(threading.current_thread())):
            internal_get_thread_stack.do_it(py_db)
        else:
            py_db.post_internal_command(internal_get_thread_stack, "*")

    def request_exception_info_json(self, py_db, request, thread_id, thread, max_frames):
        py_db.post_method_as_internal_command(
            thread_id,
            internal_get_exception_details_json,
            request,
            thread_id,
            thread,
            max_frames,
            set_additional_thread_info=set_additional_thread_info,
            iter_visible_frames_info=py_db.cmd_factory._iter_visible_frames_info,
        )

    def request_step(self, py_db, thread_id, step_cmd_id):
        t = pydevd_find_thread_by_id(thread_id)
        if t:
            py_db.post_method_as_internal_command(
                thread_id,
                internal_step_in_thread,
                thread_id,
                step_cmd_id,
                set_additional_thread_info=set_additional_thread_info,
            )
        elif thread_id.startswith("__frame__:"):
            sys.stderr.write("Can't make tasklet step command: %s\n" % (thread_id,))

    def request_smart_step_into(self, py_db, seq, thread_id, offset, child_offset):
        t = pydevd_find_thread_by_id(thread_id)
        if t:
            py_db.post_method_as_internal_command(
                thread_id, internal_smart_step_into, thread_id, offset, child_offset, set_additional_thread_info=set_additional_thread_info
            )
        elif thread_id.startswith("__frame__:"):
            sys.stderr.write("Can't set next statement in tasklet: %s\n" % (thread_id,))

    def request_smart_step_into_by_func_name(self, py_db, seq, thread_id, line, func_name):
        # Same thing as set next, just with a different cmd id.
        self.request_set_next(py_db, seq, thread_id, CMD_SMART_STEP_INTO, None, line, func_name)

    def request_set_next(self, py_db, seq, thread_id, set_next_cmd_id, original_filename, line, func_name):
        """
        set_next_cmd_id may actually be one of:

        CMD_RUN_TO_LINE
        CMD_SET_NEXT_STATEMENT

        CMD_SMART_STEP_INTO -- note: request_smart_step_into is preferred if it's possible
                               to work with bytecode offset.

        :param Optional[str] original_filename:
            If available, the filename may be source translated, otherwise no translation will take
            place (the set next just needs the line afterwards as it executes locally, but for
            the Jupyter integration, the source mapping may change the actual lines and not only
            the filename).
        """
        t = pydevd_find_thread_by_id(thread_id)
        if t:
            if original_filename is not None:
                translated_filename = self.filename_to_server(original_filename)  # Apply user path mapping.
                pydev_log.debug("Set next (after path translation) in: %s line: %s", translated_filename, line)
                func_name = self.to_str(func_name)

                assert translated_filename.__class__ == str  # i.e.: bytes on py2 and str on py3
                assert func_name.__class__ == str  # i.e.: bytes on py2 and str on py3

                # Apply source mapping (i.e.: ipython).
                _source_mapped_filename, new_line, multi_mapping_applied = py_db.source_mapping.map_to_server(translated_filename, line)
                if multi_mapping_applied:
                    pydev_log.debug("Set next (after source mapping) in: %s line: %s", translated_filename, line)
                    line = new_line

            int_cmd = InternalSetNextStatementThread(thread_id, set_next_cmd_id, line, func_name, seq=seq)
            py_db.post_internal_command(int_cmd, thread_id)
        elif thread_id.startswith("__frame__:"):
            sys.stderr.write("Can't set next statement in tasklet: %s\n" % (thread_id,))

    def request_reload_code(self, py_db, seq, module_name, filename):
        """
        :param seq: if -1 no message will be sent back when the reload is done.

        Note: either module_name or filename may be None (but not both at the same time).
        """
        thread_id = "*"  # Any thread
        # Note: not going for the main thread because in this case it'd only do the load
        # when we stopped on a breakpoint.
        py_db.post_method_as_internal_command(thread_id, internal_reload_code, seq, module_name, filename)

    def request_change_variable(self, py_db, seq, thread_id, frame_id, scope, attr, value):
        """
        :param scope: 'FRAME' or 'GLOBAL'
        """
        py_db.post_method_as_internal_command(thread_id, internal_change_variable, seq, thread_id, frame_id, scope, attr, value)

    def request_get_variable(self, py_db, seq, thread_id, frame_id, scope, attrs):
        """
        :param scope: 'FRAME' or 'GLOBAL'
        """
        int_cmd = InternalGetVariable(seq, thread_id, frame_id, scope, attrs)
        py_db.post_internal_command(int_cmd, thread_id)

    def request_get_array(self, py_db, seq, roffset, coffset, rows, cols, fmt, thread_id, frame_id, scope, attrs):
        int_cmd = InternalGetArray(seq, roffset, coffset, rows, cols, fmt, thread_id, frame_id, scope, attrs)
        py_db.post_internal_command(int_cmd, thread_id)

    def request_load_full_value(self, py_db, seq, thread_id, frame_id, vars):
        int_cmd = InternalLoadFullValue(seq, thread_id, frame_id, vars)
        py_db.post_internal_command(int_cmd, thread_id)

    def request_get_description(self, py_db, seq, thread_id, frame_id, expression):
        py_db.post_method_as_internal_command(thread_id, internal_get_description, seq, thread_id, frame_id, expression)

    def request_get_frame(self, py_db, seq, thread_id, frame_id):
        py_db.post_method_as_internal_command(thread_id, internal_get_frame, seq, thread_id, frame_id)

    def to_str(self, s):
        """
        -- in py3 raises an error if it's not str already.
        """
        if s.__class__ != str:
            raise AssertionError("Expected to have str on Python 3. Found: %s (%s)" % (s, s.__class__))
        return s

    def filename_to_str(self, filename):
        """
        -- in py3 raises an error if it's not str already.
        """
        if filename.__class__ != str:
            raise AssertionError("Expected to have str on Python 3. Found: %s (%s)" % (filename, filename.__class__))
        return filename

    def filename_to_server(self, filename):
        filename = self.filename_to_str(filename)
        filename = pydevd_file_utils.map_file_to_server(filename)
        return filename

    class _DummyFrame(object):
        """
        Dummy frame to be used with PyDB.apply_files_filter (as we don't really have the
        related frame as breakpoints are added before execution).
        """

        class _DummyCode(object):
            def __init__(self, filename):
                self.co_firstlineno = 1
                self.co_filename = filename
                self.co_name = "invalid func name "

        def __init__(self, filename):
            self.f_code = self._DummyCode(filename)
            self.f_globals = {}

    ADD_BREAKPOINT_NO_ERROR = 0
    ADD_BREAKPOINT_FILE_NOT_FOUND = 1
    ADD_BREAKPOINT_FILE_EXCLUDED_BY_FILTERS = 2

    # This means that the breakpoint couldn't be fully validated (more runtime
    # information may be needed).
    ADD_BREAKPOINT_LAZY_VALIDATION = 3
    ADD_BREAKPOINT_INVALID_LINE = 4

    class _AddBreakpointResult(object):
        # :see: ADD_BREAKPOINT_NO_ERROR = 0
        # :see: ADD_BREAKPOINT_FILE_NOT_FOUND = 1
        # :see: ADD_BREAKPOINT_FILE_EXCLUDED_BY_FILTERS = 2
        # :see: ADD_BREAKPOINT_LAZY_VALIDATION = 3
        # :see: ADD_BREAKPOINT_INVALID_LINE = 4

        __slots__ = ["error_code", "breakpoint_id", "translated_filename", "translated_line", "original_line"]

        def __init__(self, breakpoint_id, translated_filename, translated_line, original_line):
            self.error_code = PyDevdAPI.ADD_BREAKPOINT_NO_ERROR
            self.breakpoint_id = breakpoint_id
            self.translated_filename = translated_filename
            self.translated_line = translated_line
            self.original_line = original_line

    def add_breakpoint(
        self,
        py_db,
        original_filename,
        breakpoint_type,
        breakpoint_id,
        line,
        condition,
        func_name,
        expression,
        suspend_policy,
        hit_condition,
        is_logpoint,
        adjust_line=False,
        on_changed_breakpoint_state=None,
    ):
        """
        :param str original_filename:
            Note: must be sent as it was received in the protocol. It may be translated in this
            function and its final value will be available in the returned _AddBreakpointResult.

        :param str breakpoint_type:
            One of: 'python-line', 'django-line', 'jinja2-line'.

        :param int breakpoint_id:

        :param int line:
            Note: it's possible that a new line was actually used. If that's the case its
            final value will be available in the returned _AddBreakpointResult.

        :param condition:
            Either None or the condition to activate the breakpoint.

        :param str func_name:
            If "None" (str), may hit in any context.
            Empty string will hit only top level.
            Any other value must match the scope of the method to be matched.

        :param str expression:
            None or the expression to be evaluated.

        :param suspend_policy:
            Either "NONE" (to suspend only the current thread when the breakpoint is hit) or
            "ALL" (to suspend all threads when a breakpoint is hit).

        :param str hit_condition:
            An expression where `@HIT@` will be replaced by the number of hits.
            i.e.: `@HIT@ == x` or `@HIT@ >= x`

        :param bool is_logpoint:
            If True and an expression is passed, pydevd will create an io message command with the
            result of the evaluation.

        :param bool adjust_line:
            If True, the breakpoint line should be adjusted if the current line doesn't really
            match an executable line (if possible).

        :param callable on_changed_breakpoint_state:
            This is called when something changed internally on the breakpoint after it was initially
            added (for instance, template file_to_line_to_breakpoints could be signaled as invalid initially and later
            when the related template is loaded, if the line is valid it could be marked as valid).

            The signature for the callback should be:
                on_changed_breakpoint_state(breakpoint_id: int, add_breakpoint_result: _AddBreakpointResult)

                Note that the add_breakpoint_result should not be modified by the callback (the
                implementation may internally reuse the same instance multiple times).

        :return _AddBreakpointResult:
        """
        assert original_filename.__class__ == str, "Expected str, found: %s" % (
            original_filename.__class__,
        )  # i.e.: bytes on py2 and str on py3

        original_filename_normalized = pydevd_file_utils.normcase_from_client(original_filename)

        pydev_log.debug("Request for breakpoint in: %s line: %s", original_filename, line)
        original_line = line
        # Parameters to reapply breakpoint.
        api_add_breakpoint_params = (
            original_filename,
            breakpoint_type,
            breakpoint_id,
            line,
            condition,
            func_name,
            expression,
            suspend_policy,
            hit_condition,
            is_logpoint,
        )

        translated_filename = self.filename_to_server(original_filename)  # Apply user path mapping.
        pydev_log.debug("Breakpoint (after path translation) in: %s line: %s", translated_filename, line)
        func_name = self.to_str(func_name)

        assert translated_filename.__class__ == str  # i.e.: bytes on py2 and str on py3
        assert func_name.__class__ == str  # i.e.: bytes on py2 and str on py3

        # Apply source mapping (i.e.: ipython).
        source_mapped_filename, new_line, multi_mapping_applied = py_db.source_mapping.map_to_server(translated_filename, line)

        if multi_mapping_applied:
            pydev_log.debug("Breakpoint (after source mapping) in: %s line: %s", source_mapped_filename, new_line)
            # Note that source mapping is internal and does not change the resulting filename nor line
            # (we want the outside world to see the line in the original file and not in the ipython
            # cell, otherwise the editor wouldn't be correct as the returned line is the line to
            # which the breakpoint will be moved in the editor).
            result = self._AddBreakpointResult(breakpoint_id, original_filename, line, original_line)

            # If a multi-mapping was applied, consider it the canonical / source mapped version (translated to ipython cell).
            translated_absolute_filename = source_mapped_filename
            canonical_normalized_filename = pydevd_file_utils.normcase(source_mapped_filename)
            line = new_line

        else:
            translated_absolute_filename = pydevd_file_utils.absolute_path(translated_filename)
            canonical_normalized_filename = pydevd_file_utils.canonical_normalized_path(translated_filename)

            if adjust_line and not translated_absolute_filename.startswith("<"):
                # Validate file_to_line_to_breakpoints and adjust their positions.
                try:
                    lines = sorted(_get_code_lines(translated_absolute_filename))
                except Exception:
                    pass
                else:
                    if line not in lines:
                        # Adjust to the first preceding valid line.
                        idx = bisect.bisect_left(lines, line)
                        if idx > 0:
                            line = lines[idx - 1]

            result = self._AddBreakpointResult(breakpoint_id, original_filename, line, original_line)

        py_db.api_received_breakpoints[(original_filename_normalized, breakpoint_id)] = (
            canonical_normalized_filename,
            api_add_breakpoint_params,
        )

        if not translated_absolute_filename.startswith("<"):
            # Note: if a mapping pointed to a file starting with '<', don't validate.

            if not pydevd_file_utils.exists(translated_absolute_filename):
                result.error_code = self.ADD_BREAKPOINT_FILE_NOT_FOUND
                return result

            if (
                py_db.is_files_filter_enabled
                and not py_db.get_require_module_for_filters()
                and py_db.apply_files_filter(self._DummyFrame(translated_absolute_filename), translated_absolute_filename, False)
            ):
                # Note that if `get_require_module_for_filters()` returns False, we don't do this check.
                # This is because we don't have the module name given a file at this point (in
                # runtime it's gotten from the frame.f_globals).
                # An option could be calculate it based on the filename and current sys.path,
                # but on some occasions that may be wrong (for instance with `__main__` or if
                # the user dynamically changes the PYTHONPATH).

                # Note: depending on the use-case, filters may be changed, so, keep on going and add the
                # breakpoint even with the error code.
                result.error_code = self.ADD_BREAKPOINT_FILE_EXCLUDED_BY_FILTERS

        if breakpoint_type == "python-line":
            added_breakpoint = LineBreakpoint(
                breakpoint_id, line, condition, func_name, expression, suspend_policy, hit_condition=hit_condition, is_logpoint=is_logpoint
            )

            file_to_line_to_breakpoints = py_db.breakpoints
            file_to_id_to_breakpoint = py_db.file_to_id_to_line_breakpoint
            supported_type = True

        else:
            add_plugin_breakpoint_result = None
            plugin = py_db.get_plugin_lazy_init()
            if plugin is not None:
                add_plugin_breakpoint_result = plugin.add_breakpoint(
                    "add_line_breakpoint",
                    py_db,
                    breakpoint_type,
                    canonical_normalized_filename,
                    breakpoint_id,
                    line,
                    condition,
                    expression,
                    func_name,
                    hit_condition=hit_condition,
                    is_logpoint=is_logpoint,
                    add_breakpoint_result=result,
                    on_changed_breakpoint_state=on_changed_breakpoint_state,
                )

            if add_plugin_breakpoint_result is not None:
                supported_type = True
                added_breakpoint, file_to_line_to_breakpoints = add_plugin_breakpoint_result
                file_to_id_to_breakpoint = py_db.file_to_id_to_plugin_breakpoint
            else:
                supported_type = False

        if not supported_type:
            raise NameError(breakpoint_type)

        pydev_log.debug("Added breakpoint:%s - line:%s - func_name:%s\n", canonical_normalized_filename, line, func_name)

        if canonical_normalized_filename in file_to_id_to_breakpoint:
            id_to_pybreakpoint = file_to_id_to_breakpoint[canonical_normalized_filename]
        else:
            id_to_pybreakpoint = file_to_id_to_breakpoint[canonical_normalized_filename] = {}

        id_to_pybreakpoint[breakpoint_id] = added_breakpoint
        py_db.consolidate_breakpoints(canonical_normalized_filename, id_to_pybreakpoint, file_to_line_to_breakpoints)
        if py_db.plugin is not None:
            py_db.has_plugin_line_breaks = py_db.plugin.has_line_breaks(py_db)
            py_db.plugin.after_breakpoints_consolidated(
                py_db, canonical_normalized_filename, id_to_pybreakpoint, file_to_line_to_breakpoints
            )

        py_db.on_breakpoints_changed()
        return result

    def reapply_breakpoints(self, py_db):
        """
        Reapplies all the received breakpoints as they were received by the API (so, new
        translations are applied).
        """
        pydev_log.debug("Reapplying breakpoints.")
        values = list(py_db.api_received_breakpoints.values())  # Create a copy with items to reapply.
        self.remove_all_breakpoints(py_db, "*")
        for val in values:
            _new_filename, api_add_breakpoint_params = val
            self.add_breakpoint(py_db, *api_add_breakpoint_params)

    def remove_all_breakpoints(self, py_db, received_filename):
        """
        Removes all the breakpoints from a given file or from all files if received_filename == '*'.

        :param str received_filename:
            Note: must be sent as it was received in the protocol. It may be translated in this
            function.
        """
        assert received_filename.__class__ == str  # i.e.: bytes on py2 and str on py3
        changed = False
        lst = [py_db.file_to_id_to_line_breakpoint, py_db.file_to_id_to_plugin_breakpoint, py_db.breakpoints]
        if hasattr(py_db, "django_breakpoints"):
            lst.append(py_db.django_breakpoints)

        if hasattr(py_db, "jinja2_breakpoints"):
            lst.append(py_db.jinja2_breakpoints)

        if received_filename == "*":
            py_db.api_received_breakpoints.clear()

            for file_to_id_to_breakpoint in lst:
                if file_to_id_to_breakpoint:
                    file_to_id_to_breakpoint.clear()
                    changed = True

        else:
            received_filename_normalized = pydevd_file_utils.normcase_from_client(received_filename)
            items = list(py_db.api_received_breakpoints.items())  # Create a copy to remove items.
            translated_filenames = []
            for key, val in items:
                original_filename_normalized, _breakpoint_id = key
                if original_filename_normalized == received_filename_normalized:
                    canonical_normalized_filename, _api_add_breakpoint_params = val
                    # Note: there can be actually 1:N mappings due to source mapping (i.e.: ipython).
                    translated_filenames.append(canonical_normalized_filename)
                    del py_db.api_received_breakpoints[key]

            for canonical_normalized_filename in translated_filenames:
                for file_to_id_to_breakpoint in lst:
                    if canonical_normalized_filename in file_to_id_to_breakpoint:
                        file_to_id_to_breakpoint.pop(canonical_normalized_filename, None)
                        changed = True

        if changed:
            py_db.on_breakpoints_changed(removed=True)

    def remove_breakpoint(self, py_db, received_filename, breakpoint_type, breakpoint_id):
        """
        :param str received_filename:
            Note: must be sent as it was received in the protocol. It may be translated in this
            function.

        :param str breakpoint_type:
            One of: 'python-line', 'django-line', 'jinja2-line'.

        :param int breakpoint_id:
        """
        received_filename_normalized = pydevd_file_utils.normcase_from_client(received_filename)
        for key, val in list(py_db.api_received_breakpoints.items()):
            original_filename_normalized, existing_breakpoint_id = key
            _new_filename, _api_add_breakpoint_params = val
            if received_filename_normalized == original_filename_normalized and existing_breakpoint_id == breakpoint_id:
                del py_db.api_received_breakpoints[key]
                break
        else:
            pydev_log.info("Did not find breakpoint to remove: %s (breakpoint id: %s)", received_filename, breakpoint_id)

        file_to_id_to_breakpoint = None
        received_filename = self.filename_to_server(received_filename)
        canonical_normalized_filename = pydevd_file_utils.canonical_normalized_path(received_filename)

        if breakpoint_type == "python-line":
            file_to_line_to_breakpoints = py_db.breakpoints
            file_to_id_to_breakpoint = py_db.file_to_id_to_line_breakpoint

        elif py_db.plugin is not None:
            result = py_db.plugin.get_breakpoints(py_db, breakpoint_type)
            if result is not None:
                file_to_id_to_breakpoint = py_db.file_to_id_to_plugin_breakpoint
                file_to_line_to_breakpoints = result

        if file_to_id_to_breakpoint is None:
            pydev_log.critical("Error removing breakpoint. Cannot handle breakpoint of type %s", breakpoint_type)

        else:
            try:
                id_to_pybreakpoint = file_to_id_to_breakpoint.get(canonical_normalized_filename, {})
                if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 1:
                    existing = id_to_pybreakpoint[breakpoint_id]
                    pydev_log.info(
                        "Removed breakpoint:%s - line:%s - func_name:%s (id: %s)\n"
                        % (canonical_normalized_filename, existing.line, existing.func_name, breakpoint_id)
                    )

                del id_to_pybreakpoint[breakpoint_id]
                py_db.consolidate_breakpoints(canonical_normalized_filename, id_to_pybreakpoint, file_to_line_to_breakpoints)
                if py_db.plugin is not None:
                    py_db.has_plugin_line_breaks = py_db.plugin.has_line_breaks(py_db)
                    py_db.plugin.after_breakpoints_consolidated(
                        py_db, canonical_normalized_filename, id_to_pybreakpoint, file_to_line_to_breakpoints
                    )

            except KeyError:
                pydev_log.info(
                    "Error removing breakpoint: Breakpoint id not found: %s id: %s. Available ids: %s\n",
                    canonical_normalized_filename,
                    breakpoint_id,
                    list(id_to_pybreakpoint),
                )

        py_db.on_breakpoints_changed(removed=True)

    def set_function_breakpoints(self, py_db, function_breakpoints):
        function_breakpoint_name_to_breakpoint = {}
        for function_breakpoint in function_breakpoints:
            function_breakpoint_name_to_breakpoint[function_breakpoint.func_name] = function_breakpoint

        py_db.function_breakpoint_name_to_breakpoint = function_breakpoint_name_to_breakpoint
        py_db.on_breakpoints_changed()

    def request_exec_or_evaluate(self, py_db, seq, thread_id, frame_id, expression, is_exec, trim_if_too_big, attr_to_set_result):
        py_db.post_method_as_internal_command(
            thread_id, internal_evaluate_expression, seq, thread_id, frame_id, expression, is_exec, trim_if_too_big, attr_to_set_result
        )

    def request_exec_or_evaluate_json(self, py_db, request, thread_id):
        py_db.post_method_as_internal_command(thread_id, internal_evaluate_expression_json, request, thread_id)

    def request_set_expression_json(self, py_db, request, thread_id):
        py_db.post_method_as_internal_command(thread_id, internal_set_expression_json, request, thread_id)

    def request_console_exec(self, py_db, seq, thread_id, frame_id, expression):
        int_cmd = InternalConsoleExec(seq, thread_id, frame_id, expression)
        py_db.post_internal_command(int_cmd, thread_id)

    def request_load_source(self, py_db, seq, filename):
        """
        :param str filename:
            Note: must be sent as it was received in the protocol. It may be translated in this
            function.
        """
        try:
            filename = self.filename_to_server(filename)
            assert filename.__class__ == str  # i.e.: bytes on py2 and str on py3

            with tokenize.open(filename) as stream:
                source = stream.read()
            cmd = py_db.cmd_factory.make_load_source_message(seq, source)
        except:
            cmd = py_db.cmd_factory.make_error_message(seq, get_exception_traceback_str())

        py_db.writer.add_command(cmd)

    def get_decompiled_source_from_frame_id(self, py_db, frame_id):
        """
        :param py_db:
        :param frame_id:
        :throws Exception:
            If unable to get the frame in the currently paused frames or if some error happened
            when decompiling.
        """
        variable = py_db.suspended_frames_manager.get_variable(int(frame_id))
        frame = variable.value

        # Check if it's in the linecache first.
        lines = (linecache.getline(frame.f_code.co_filename, i) for i in itertools.count(1))
        lines = itertools.takewhile(bool, lines)  # empty lines are '\n', EOF is ''

        source = "".join(lines)
        if not source:
            source = code_to_bytecode_representation(frame.f_code)

        return source

    def request_load_source_from_frame_id(self, py_db, seq, frame_id):
        try:
            source = self.get_decompiled_source_from_frame_id(py_db, frame_id)
            cmd = py_db.cmd_factory.make_load_source_from_frame_id_message(seq, source)
        except:
            cmd = py_db.cmd_factory.make_error_message(seq, get_exception_traceback_str())

        py_db.writer.add_command(cmd)

    def add_python_exception_breakpoint(
        self,
        py_db,
        exception,
        condition,
        expression,
        notify_on_handled_exceptions,
        notify_on_unhandled_exceptions,
        notify_on_user_unhandled_exceptions,
        notify_on_first_raise_only,
        ignore_libraries,
    ):
        exception_breakpoint = py_db.add_break_on_exception(
            exception,
            condition=condition,
            expression=expression,
            notify_on_handled_exceptions=notify_on_handled_exceptions,
            notify_on_unhandled_exceptions=notify_on_unhandled_exceptions,
            notify_on_user_unhandled_exceptions=notify_on_user_unhandled_exceptions,
            notify_on_first_raise_only=notify_on_first_raise_only,
            ignore_libraries=ignore_libraries,
        )

        if exception_breakpoint is not None:
            py_db.on_breakpoints_changed()

    def add_plugins_exception_breakpoint(self, py_db, breakpoint_type, exception):
        supported_type = False
        plugin = py_db.get_plugin_lazy_init()
        if plugin is not None:
            supported_type = plugin.add_breakpoint("add_exception_breakpoint", py_db, breakpoint_type, exception)

        if supported_type:
            py_db.has_plugin_exception_breaks = py_db.plugin.has_exception_breaks(py_db)
            py_db.on_breakpoints_changed()
        else:
            raise NameError(breakpoint_type)

    def remove_python_exception_breakpoint(self, py_db, exception):
        try:
            cp = py_db.break_on_uncaught_exceptions.copy()
            cp.pop(exception, None)
            py_db.break_on_uncaught_exceptions = cp

            cp = py_db.break_on_caught_exceptions.copy()
            cp.pop(exception, None)
            py_db.break_on_caught_exceptions = cp

            cp = py_db.break_on_user_uncaught_exceptions.copy()
            cp.pop(exception, None)
            py_db.break_on_user_uncaught_exceptions = cp
        except:
            pydev_log.exception("Error while removing exception %s", sys.exc_info()[0])

        py_db.on_breakpoints_changed(removed=True)

    def remove_plugins_exception_breakpoint(self, py_db, exception_type, exception):
        # I.e.: no need to initialize lazy (if we didn't have it in the first place, we can't remove
        # anything from it anyways).
        plugin = py_db.plugin
        if plugin is None:
            return

        supported_type = plugin.remove_exception_breakpoint(py_db, exception_type, exception)

        if supported_type:
            py_db.has_plugin_exception_breaks = py_db.plugin.has_exception_breaks(py_db)
        else:
            pydev_log.info("No exception of type: %s was previously registered.", exception_type)

        py_db.on_breakpoints_changed(removed=True)

    def remove_all_exception_breakpoints(self, py_db):
        py_db.break_on_uncaught_exceptions = {}
        py_db.break_on_caught_exceptions = {}
        py_db.break_on_user_uncaught_exceptions = {}

        plugin = py_db.plugin
        if plugin is not None:
            plugin.remove_all_exception_breakpoints(py_db)
        py_db.on_breakpoints_changed(removed=True)

    def set_project_roots(self, py_db, project_roots):
        """
        :param str project_roots:
        """
        py_db.set_project_roots(project_roots)

    def set_stepping_resumes_all_threads(self, py_db, stepping_resumes_all_threads):
        py_db.stepping_resumes_all_threads = stepping_resumes_all_threads

    # Add it to the namespace so that it's available as PyDevdAPI.ExcludeFilter
    from _pydevd_bundle.pydevd_filtering import ExcludeFilter  # noqa

    def set_exclude_filters(self, py_db, exclude_filters):
        """
        :param list(PyDevdAPI.ExcludeFilter) exclude_filters:
        """
        py_db.set_exclude_filters(exclude_filters)

    def set_use_libraries_filter(self, py_db, use_libraries_filter):
        py_db.set_use_libraries_filter(use_libraries_filter)

    def request_get_variable_json(self, py_db, request, thread_id):
        """
        :param VariablesRequest request:
        """
        py_db.post_method_as_internal_command(thread_id, internal_get_variable_json, request)

    def request_change_variable_json(self, py_db, request, thread_id):
        """
        :param SetVariableRequest request:
        """
        py_db.post_method_as_internal_command(thread_id, internal_change_variable_json, request)

    def set_dont_trace_start_end_patterns(self, py_db, start_patterns, end_patterns):
        # Note: start/end patterns normalized internally.
        start_patterns = tuple(pydevd_file_utils.normcase(x) for x in start_patterns)
        end_patterns = tuple(pydevd_file_utils.normcase(x) for x in end_patterns)

        # After it's set the first time, we can still change it, but we need to reset the
        # related caches.
        reset_caches = False
        dont_trace_start_end_patterns_previously_set = py_db.dont_trace_external_files.__name__ == "custom_dont_trace_external_files"

        if not dont_trace_start_end_patterns_previously_set and not start_patterns and not end_patterns:
            # If it wasn't set previously and start and end patterns are empty we don't need to do anything.
            return

        if not py_db.is_cache_file_type_empty():
            # i.e.: custom function set in set_dont_trace_start_end_patterns.
            if dont_trace_start_end_patterns_previously_set:
                reset_caches = (
                    py_db.dont_trace_external_files.start_patterns != start_patterns
                    or py_db.dont_trace_external_files.end_patterns != end_patterns
                )

            else:
                reset_caches = True

        def custom_dont_trace_external_files(abs_path):
            normalized_abs_path = pydevd_file_utils.normcase(abs_path)
            return normalized_abs_path.startswith(start_patterns) or normalized_abs_path.endswith(end_patterns)

        custom_dont_trace_external_files.start_patterns = start_patterns
        custom_dont_trace_external_files.end_patterns = end_patterns
        py_db.dont_trace_external_files = custom_dont_trace_external_files

        if reset_caches:
            py_db.clear_dont_trace_start_end_patterns_caches()

    def stop_on_entry(self):
        main_thread = pydevd_utils.get_main_thread()
        if main_thread is None:
            pydev_log.critical("Could not find main thread while setting Stop on Entry.")
        else:
            info = set_additional_thread_info(main_thread)
            info.pydev_original_step_cmd = CMD_STOP_ON_START
            info.pydev_step_cmd = CMD_STEP_INTO_MY_CODE
            info.update_stepping_info()
            if PYDEVD_USE_SYS_MONITORING:
                pydevd_sys_monitoring.update_monitor_events(suspend_requested=True)
                pydevd_sys_monitoring.restart_events()

    def set_ignore_system_exit_codes(self, py_db, ignore_system_exit_codes):
        py_db.set_ignore_system_exit_codes(ignore_system_exit_codes)

    SourceMappingEntry = pydevd_source_mapping.SourceMappingEntry

    def set_source_mapping(self, py_db, source_filename, mapping):
        """
        :param str source_filename:
            The filename for the source mapping (bytes on py2 and str on py3).
            This filename will be made absolute in this function.

        :param list(SourceMappingEntry) mapping:
            A list with the source mapping entries to be applied to the given filename.

        :return str:
            An error message if it was not possible to set the mapping or an empty string if
            everything is ok.
        """
        source_filename = self.filename_to_server(source_filename)
        absolute_source_filename = pydevd_file_utils.absolute_path(source_filename)
        for map_entry in mapping:
            map_entry.source_filename = absolute_source_filename
        error_msg = py_db.source_mapping.set_source_mapping(absolute_source_filename, mapping)
        if error_msg:
            return error_msg

        self.reapply_breakpoints(py_db)
        return ""

    def set_variable_presentation(self, py_db, variable_presentation):
        assert isinstance(variable_presentation, self.VariablePresentation)
        py_db.variable_presentation = variable_presentation

    def get_ppid(self):
        """
        Provides the parent pid (even for older versions of Python on Windows).
        """
        ppid = None

        try:
            ppid = os.getppid()
        except AttributeError:
            pass

        if ppid is None and IS_WINDOWS:
            ppid = self._get_windows_ppid()

        return ppid

    def _get_windows_ppid(self):
        this_pid = os.getpid()
        for ppid, pid in _list_ppid_and_pid():
            if pid == this_pid:
                return ppid

        return None

    def _terminate_child_processes_windows(self, dont_terminate_child_pids):
        this_pid = os.getpid()
        for _ in range(50):  # Try this at most 50 times before giving up.
            # Note: we can't kill the process itself with taskkill, so, we
            # list immediate children, kill that tree and then exit this process.

            children_pids = []
            for ppid, pid in _list_ppid_and_pid():
                if ppid == this_pid:
                    if pid not in dont_terminate_child_pids:
                        children_pids.append(pid)

            if not children_pids:
                break
            else:
                for pid in children_pids:
                    self._call(["taskkill", "/F", "/PID", str(pid), "/T"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                del children_pids[:]

    def _terminate_child_processes_linux_and_mac(self, dont_terminate_child_pids):
        this_pid = os.getpid()

        def list_children_and_stop_forking(initial_pid, stop=True):
            children_pids = []
            if stop:
                # Ask to stop forking (shouldn't be called for this process, only subprocesses).
                self._call(["kill", "-STOP", str(initial_pid)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            list_popen = self._popen(["pgrep", "-P", str(initial_pid)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if list_popen is not None:
                stdout, _ = list_popen.communicate()
                for line in stdout.splitlines():
                    line = line.decode("ascii").strip()
                    if line:
                        pid = str(line)
                        if pid in dont_terminate_child_pids:
                            continue
                        children_pids.append(pid)
                        # Recursively get children.
                        children_pids.extend(list_children_and_stop_forking(pid))
            return children_pids

        previously_found = set()

        for _ in range(50):  # Try this at most 50 times before giving up.
            children_pids = list_children_and_stop_forking(this_pid, stop=False)
            found_new = False

            for pid in children_pids:
                if pid not in previously_found:
                    found_new = True
                    previously_found.add(pid)
                    self._call(["kill", "-KILL", str(pid)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if not found_new:
                break

    def _popen(self, cmdline, **kwargs):
        try:
            return subprocess.Popen(cmdline, **kwargs)
        except:
            if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 1:
                pydev_log.exception("Error running: %s" % (" ".join(cmdline)))
            return None

    def _call(self, cmdline, **kwargs):
        try:
            subprocess.check_call(cmdline, **kwargs)
        except:
            if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 1:
                pydev_log.exception("Error running: %s" % (" ".join(cmdline)))

    def set_terminate_child_processes(self, py_db, terminate_child_processes):
        py_db.terminate_child_processes = terminate_child_processes

    def set_terminate_keyboard_interrupt(self, py_db, terminate_keyboard_interrupt):
        py_db.terminate_keyboard_interrupt = terminate_keyboard_interrupt

    def terminate_process(self, py_db):
        """
        Terminates the current process (and child processes if the option to also terminate
        child processes is enabled).
        """
        try:
            if py_db.terminate_child_processes:
                pydev_log.debug("Terminating child processes.")
                if IS_WINDOWS:
                    self._terminate_child_processes_windows(py_db.dont_terminate_child_pids)
                else:
                    self._terminate_child_processes_linux_and_mac(py_db.dont_terminate_child_pids)
        finally:
            pydev_log.debug("Exiting process (os._exit(0)).")
            os._exit(0)

    def _terminate_if_commands_processed(self, py_db):
        py_db.dispose_and_kill_all_pydevd_threads()
        self.terminate_process(py_db)

    def request_terminate_process(self, py_db):
        if py_db.terminate_keyboard_interrupt:
            if not py_db.keyboard_interrupt_requested:
                py_db.keyboard_interrupt_requested = True
                interrupt_main_thread()
                return

        # We mark with a terminate_requested to avoid that paused threads start running
        # (we should terminate as is without letting any paused thread run).
        py_db.terminate_requested = True
        run_as_pydevd_daemon_thread(py_db, self._terminate_if_commands_processed, py_db)

    def setup_auto_reload_watcher(self, py_db, enable_auto_reload, watch_dirs, poll_target_time, exclude_patterns, include_patterns):
        py_db.setup_auto_reload_watcher(enable_auto_reload, watch_dirs, poll_target_time, exclude_patterns, include_patterns)


def _list_ppid_and_pid():
    _TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_uint32),
            ("cntUsage", ctypes.c_uint32),
            ("th32ProcessID", ctypes.c_uint32),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", ctypes.c_uint32),
            ("cntThreads", ctypes.c_uint32),
            ("th32ParentProcessID", ctypes.c_uint32),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.c_uint32),
            ("szExeFile", ctypes.c_char * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    ppid_and_pids = []
    try:
        process_entry = PROCESSENTRY32()
        process_entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        if not kernel32.Process32First(ctypes.c_void_p(snapshot), ctypes.byref(process_entry)):
            pydev_log.critical("Process32First failed (getting process from CreateToolhelp32Snapshot).")
        else:
            while True:
                ppid_and_pids.append((process_entry.th32ParentProcessID, process_entry.th32ProcessID))
                if not kernel32.Process32Next(ctypes.c_void_p(snapshot), ctypes.byref(process_entry)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)

    return ppid_and_pids

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\lexers\python.py ===
"""
    pygments.lexers.python
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Python and related languages.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import keyword

from pip._vendor.pygments.lexer import DelegatingLexer, RegexLexer, include, \
    bygroups, using, default, words, combined, this
from pip._vendor.pygments.util import get_bool_opt, shebang_matches
from pip._vendor.pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic, Other, Error, Whitespace
from pip._vendor.pygments import unistring as uni

__all__ = ['PythonLexer', 'PythonConsoleLexer', 'PythonTracebackLexer',
           'Python2Lexer', 'Python2TracebackLexer',
           'CythonLexer', 'DgLexer', 'NumPyLexer']


class PythonLexer(RegexLexer):
    """
    For Python source code (version 3.x).

    .. versionchanged:: 2.5
       This is now the default ``PythonLexer``.  It is still available as the
       alias ``Python3Lexer``.
    """

    name = 'Python'
    url = 'https://www.python.org'
    aliases = ['python', 'py', 'sage', 'python3', 'py3', 'bazel', 'starlark']
    filenames = [
        '*.py',
        '*.pyw',
        # Type stubs
        '*.pyi',
        # Jython
        '*.jy',
        # Sage
        '*.sage',
        # SCons
        '*.sc',
        'SConstruct',
        'SConscript',
        # Skylark/Starlark (used by Bazel, Buck, and Pants)
        '*.bzl',
        'BUCK',
        'BUILD',
        'BUILD.bazel',
        'WORKSPACE',
        # Twisted Application infrastructure
        '*.tac',
    ]
    mimetypes = ['text/x-python', 'application/x-python',
                 'text/x-python3', 'application/x-python3']
    version_added = '0.10'

    uni_name = f"[{uni.xid_start}][{uni.xid_continue}]*"

    def innerstring_rules(ttype):
        return [
            # the old style '%s' % (...) string formatting (still valid in Py3)
            (r'%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsaux%]', String.Interpol),
            # the new style '{}'.format(...) string formatting
            (r'\{'
             r'((\w+)((\.\w+)|(\[[^\]]+\]))*)?'  # field name
             r'(\![sra])?'                       # conversion
             r'(\:(.?[<>=\^])?[-+ ]?#?0?(\d+)?,?(\.\d+)?[E-GXb-gnosx%]?)?'
             r'\}', String.Interpol),

            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"%{\n]+', ttype),
            (r'[\'"\\]', ttype),
            # unhandled string formatting sign
            (r'%|(\{{1,2})', ttype)
            # newlines are an error (use "nl" state)
        ]

    def fstring_rules(ttype):
        return [
            # Assuming that a '}' is the closing brace after format specifier.
            # Sadly, this means that we won't detect syntax error. But it's
            # more important to parse correct syntax correctly, than to
            # highlight invalid syntax.
            (r'\}', String.Interpol),
            (r'\{', String.Interpol, 'expr-inside-fstring'),
            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"{}\n]+', ttype),
            (r'[\'"\\]', ttype),
            # newlines are an error (use "nl" state)
        ]

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'^(\s*)([rRuUbB]{,2})("""(?:.|\n)*?""")',
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r"^(\s*)([rRuUbB]{,2})('''(?:.|\n)*?''')",
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r'\A#!.+$', Comment.Hashbang),
            (r'#.*$', Comment.Single),
            (r'\\\n', Text),
            (r'\\', Text),
            include('keywords'),
            include('soft-keywords'),
            (r'(def)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'funcname'),
            (r'(class)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'classname'),
            (r'(from)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Text),
             'fromimport'),
            (r'(import)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Text),
             'import'),
            include('expr'),
        ],
        'expr': [
            # raw f-strings
            ('(?i)(rf|fr)(""")',
             bygroups(String.Affix, String.Double),
             combined('rfstringescape', 'tdqf')),
            ("(?i)(rf|fr)(''')",
             bygroups(String.Affix, String.Single),
             combined('rfstringescape', 'tsqf')),
            ('(?i)(rf|fr)(")',
             bygroups(String.Affix, String.Double),
             combined('rfstringescape', 'dqf')),
            ("(?i)(rf|fr)(')",
             bygroups(String.Affix, String.Single),
             combined('rfstringescape', 'sqf')),
            # non-raw f-strings
            ('([fF])(""")', bygroups(String.Affix, String.Double),
             combined('fstringescape', 'tdqf')),
            ("([fF])(''')", bygroups(String.Affix, String.Single),
             combined('fstringescape', 'tsqf')),
            ('([fF])(")', bygroups(String.Affix, String.Double),
             combined('fstringescape', 'dqf')),
            ("([fF])(')", bygroups(String.Affix, String.Single),
             combined('fstringescape', 'sqf')),
            # raw bytes and strings
            ('(?i)(rb|br|r)(""")',
             bygroups(String.Affix, String.Double), 'tdqs'),
            ("(?i)(rb|br|r)(''')",
             bygroups(String.Affix, String.Single), 'tsqs'),
            ('(?i)(rb|br|r)(")',
             bygroups(String.Affix, String.Double), 'dqs'),
            ("(?i)(rb|br|r)(')",
             bygroups(String.Affix, String.Single), 'sqs'),
            # non-raw strings
            ('([uU]?)(""")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'tdqs')),
            ("([uU]?)(''')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'tsqs')),
            ('([uU]?)(")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'dqs')),
            ("([uU]?)(')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'sqs')),
            # non-raw bytes
            ('([bB])(""")', bygroups(String.Affix, String.Double),
             combined('bytesescape', 'tdqs')),
            ("([bB])(''')", bygroups(String.Affix, String.Single),
             combined('bytesescape', 'tsqs')),
            ('([bB])(")', bygroups(String.Affix, String.Double),
             combined('bytesescape', 'dqs')),
            ("([bB])(')", bygroups(String.Affix, String.Single),
             combined('bytesescape', 'sqs')),

            (r'[^\S\n]+', Text),
            include('numbers'),
            (r'!=|==|<<|>>|:=|[-~+/*%=<>&^|.]', Operator),
            (r'[]{}:(),;[]', Punctuation),
            (r'(in|is|and|or|not)\b', Operator.Word),
            include('expr-keywords'),
            include('builtins'),
            include('magicfuncs'),
            include('magicvars'),
            include('name'),
        ],
        'expr-inside-fstring': [
            (r'[{([]', Punctuation, 'expr-inside-fstring-inner'),
            # without format specifier
            (r'(=\s*)?'         # debug (https://bugs.python.org/issue36817)
             r'(\![sraf])?'     # conversion
             r'\}', String.Interpol, '#pop'),
            # with format specifier
            # we'll catch the remaining '}' in the outer scope
            (r'(=\s*)?'         # debug (https://bugs.python.org/issue36817)
             r'(\![sraf])?'     # conversion
             r':', String.Interpol, '#pop'),
            (r'\s+', Whitespace),  # allow new lines
            include('expr'),
        ],
        'expr-inside-fstring-inner': [
            (r'[{([]', Punctuation, 'expr-inside-fstring-inner'),
            (r'[])}]', Punctuation, '#pop'),
            (r'\s+', Whitespace),  # allow new lines
            include('expr'),
        ],
        'expr-keywords': [
            # Based on https://docs.python.org/3/reference/expressions.html
            (words((
                'async for', 'await', 'else', 'for', 'if', 'lambda',
                'yield', 'yield from'), suffix=r'\b'),
             Keyword),
            (words(('True', 'False', 'None'), suffix=r'\b'), Keyword.Constant),
        ],
        'keywords': [
            (words((
                'assert', 'async', 'await', 'break', 'continue', 'del', 'elif',
                'else', 'except', 'finally', 'for', 'global', 'if', 'lambda',
                'pass', 'raise', 'nonlocal', 'return', 'try', 'while', 'yield',
                'yield from', 'as', 'with'), suffix=r'\b'),
             Keyword),
            (words(('True', 'False', 'None'), suffix=r'\b'), Keyword.Constant),
        ],
        'soft-keywords': [
            # `match`, `case` and `_` soft keywords
            (r'(^[ \t]*)'              # at beginning of line + possible indentation
             r'(match|case)\b'         # a possible keyword
             r'(?![ \t]*(?:'           # not followed by...
             r'[:,;=^&|@~)\]}]|(?:' +  # characters and keywords that mean this isn't
                                       # pattern matching (but None/True/False is ok)
             r'|'.join(k for k in keyword.kwlist if k[0].islower()) + r')\b))',
             bygroups(Text, Keyword), 'soft-keywords-inner'),
        ],
        'soft-keywords-inner': [
            # optional `_` keyword
            (r'(\s+)([^\n_]*)(_\b)', bygroups(Whitespace, using(this), Keyword)),
            default('#pop')
        ],
        'builtins': [
            (words((
                '__import__', 'abs', 'aiter', 'all', 'any', 'bin', 'bool', 'bytearray',
                'breakpoint', 'bytes', 'callable', 'chr', 'classmethod', 'compile',
                'complex', 'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval',
                'filter', 'float', 'format', 'frozenset', 'getattr', 'globals',
                'hasattr', 'hash', 'hex', 'id', 'input', 'int', 'isinstance',
                'issubclass', 'iter', 'len', 'list', 'locals', 'map', 'max',
                'memoryview', 'min', 'next', 'object', 'oct', 'open', 'ord', 'pow',
                'print', 'property', 'range', 'repr', 'reversed', 'round', 'set',
                'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super',
                'tuple', 'type', 'vars', 'zip'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Builtin),
            (r'(?<!\.)(self|Ellipsis|NotImplemented|cls)\b', Name.Builtin.Pseudo),
            (words((
                'ArithmeticError', 'AssertionError', 'AttributeError',
                'BaseException', 'BufferError', 'BytesWarning', 'DeprecationWarning',
                'EOFError', 'EnvironmentError', 'Exception', 'FloatingPointError',
                'FutureWarning', 'GeneratorExit', 'IOError', 'ImportError',
                'ImportWarning', 'IndentationError', 'IndexError', 'KeyError',
                'KeyboardInterrupt', 'LookupError', 'MemoryError', 'NameError',
                'NotImplementedError', 'OSError', 'OverflowError',
                'PendingDeprecationWarning', 'ReferenceError', 'ResourceWarning',
                'RuntimeError', 'RuntimeWarning', 'StopIteration',
                'SyntaxError', 'SyntaxWarning', 'SystemError', 'SystemExit',
                'TabError', 'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
                'UnicodeEncodeError', 'UnicodeError', 'UnicodeTranslateError',
                'UnicodeWarning', 'UserWarning', 'ValueError', 'VMSError',
                'Warning', 'WindowsError', 'ZeroDivisionError',
                # new builtin exceptions from PEP 3151
                'BlockingIOError', 'ChildProcessError', 'ConnectionError',
                'BrokenPipeError', 'ConnectionAbortedError', 'ConnectionRefusedError',
                'ConnectionResetError', 'FileExistsError', 'FileNotFoundError',
                'InterruptedError', 'IsADirectoryError', 'NotADirectoryError',
                'PermissionError', 'ProcessLookupError', 'TimeoutError',
                # others new in Python 3
                'StopAsyncIteration', 'ModuleNotFoundError', 'RecursionError',
                'EncodingWarning'),
                prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Exception),
        ],
        'magicfuncs': [
            (words((
                '__abs__', '__add__', '__aenter__', '__aexit__', '__aiter__',
                '__and__', '__anext__', '__await__', '__bool__', '__bytes__',
                '__call__', '__complex__', '__contains__', '__del__', '__delattr__',
                '__delete__', '__delitem__', '__dir__', '__divmod__', '__enter__',
                '__eq__', '__exit__', '__float__', '__floordiv__', '__format__',
                '__ge__', '__get__', '__getattr__', '__getattribute__',
                '__getitem__', '__gt__', '__hash__', '__iadd__', '__iand__',
                '__ifloordiv__', '__ilshift__', '__imatmul__', '__imod__',
                '__imul__', '__index__', '__init__', '__instancecheck__',
                '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__',
                '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__',
                '__len__', '__length_hint__', '__lshift__', '__lt__', '__matmul__',
                '__missing__', '__mod__', '__mul__', '__ne__', '__neg__',
                '__new__', '__next__', '__or__', '__pos__', '__pow__',
                '__prepare__', '__radd__', '__rand__', '__rdivmod__', '__repr__',
                '__reversed__', '__rfloordiv__', '__rlshift__', '__rmatmul__',
                '__rmod__', '__rmul__', '__ror__', '__round__', '__rpow__',
                '__rrshift__', '__rshift__', '__rsub__', '__rtruediv__',
                '__rxor__', '__set__', '__setattr__', '__setitem__', '__str__',
                '__sub__', '__subclasscheck__', '__truediv__',
                '__xor__'), suffix=r'\b'),
             Name.Function.Magic),
        ],
        'magicvars': [
            (words((
                '__annotations__', '__bases__', '__class__', '__closure__',
                '__code__', '__defaults__', '__dict__', '__doc__', '__file__',
                '__func__', '__globals__', '__kwdefaults__', '__module__',
                '__mro__', '__name__', '__objclass__', '__qualname__',
                '__self__', '__slots__', '__weakref__'), suffix=r'\b'),
             Name.Variable.Magic),
        ],
        'numbers': [
            (r'(\d(?:_?\d)*\.(?:\d(?:_?\d)*)?|(?:\d(?:_?\d)*)?\.\d(?:_?\d)*)'
             r'([eE][+-]?\d(?:_?\d)*)?', Number.Float),
            (r'\d(?:_?\d)*[eE][+-]?\d(?:_?\d)*j?', Number.Float),
            (r'0[oO](?:_?[0-7])+', Number.Oct),
            (r'0[bB](?:_?[01])+', Number.Bin),
            (r'0[xX](?:_?[a-fA-F0-9])+', Number.Hex),
            (r'\d(?:_?\d)*', Number.Integer),
        ],
        'name': [
            (r'@' + uni_name, Name.Decorator),
            (r'@', Operator),  # new matrix multiplication operator
            (uni_name, Name),
        ],
        'funcname': [
            include('magicfuncs'),
            (uni_name, Name.Function, '#pop'),
            default('#pop'),
        ],
        'classname': [
            (uni_name, Name.Class, '#pop'),
        ],
        'import': [
            (r'(\s+)(as)(\s+)', bygroups(Text, Keyword, Text)),
            (r'\.', Name.Namespace),
            (uni_name, Name.Namespace),
            (r'(\s*)(,)(\s*)', bygroups(Text, Operator, Text)),
            default('#pop')  # all else: go back
        ],
        'fromimport': [
            (r'(\s+)(import)\b', bygroups(Text, Keyword.Namespace), '#pop'),
            (r'\.', Name.Namespace),
            # if None occurs here, it's "raise x from None", since None can
            # never be a module name
            (r'None\b', Keyword.Constant, '#pop'),
            (uni_name, Name.Namespace),
            default('#pop'),
        ],
        'rfstringescape': [
            (r'\{\{', String.Escape),
            (r'\}\}', String.Escape),
        ],
        'fstringescape': [
            include('rfstringescape'),
            include('stringescape'),
        ],
        'bytesescape': [
            (r'\\([\\abfnrtv"\']|\n|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'stringescape': [
            (r'\\(N\{.*?\}|u[a-fA-F0-9]{4}|U[a-fA-F0-9]{8})', String.Escape),
            include('bytesescape')
        ],
        'fstrings-single': fstring_rules(String.Single),
        'fstrings-double': fstring_rules(String.Double),
        'strings-single': innerstring_rules(String.Single),
        'strings-double': innerstring_rules(String.Double),
        'dqf': [
            (r'"', String.Double, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include('fstrings-double')
        ],
        'sqf': [
            (r"'", String.Single, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include('fstrings-single')
        ],
        'dqs': [
            (r'"', String.Double, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include('strings-double')
        ],
        'sqs': [
            (r"'", String.Single, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include('strings-single')
        ],
        'tdqf': [
            (r'"""', String.Double, '#pop'),
            include('fstrings-double'),
            (r'\n', String.Double)
        ],
        'tsqf': [
            (r"'''", String.Single, '#pop'),
            include('fstrings-single'),
            (r'\n', String.Single)
        ],
        'tdqs': [
            (r'"""', String.Double, '#pop'),
            include('strings-double'),
            (r'\n', String.Double)
        ],
        'tsqs': [
            (r"'''", String.Single, '#pop'),
            include('strings-single'),
            (r'\n', String.Single)
        ],
    }

    def analyse_text(text):
        return shebang_matches(text, r'pythonw?(3(\.\d)?)?') or \
            'import ' in text[:1000]


Python3Lexer = PythonLexer


class Python2Lexer(RegexLexer):
    """
    For Python 2.x source code.

    .. versionchanged:: 2.5
       This class has been renamed from ``PythonLexer``.  ``PythonLexer`` now
       refers to the Python 3 variant.  File name patterns like ``*.py`` have
       been moved to Python 3 as well.
    """

    name = 'Python 2.x'
    url = 'https://www.python.org'
    aliases = ['python2', 'py2']
    filenames = []  # now taken over by PythonLexer (3.x)
    mimetypes = ['text/x-python2', 'application/x-python2']
    version_added = ''

    def innerstring_rules(ttype):
        return [
            # the old style '%s' % (...) string formatting
            (r'%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsux%]', String.Interpol),
            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"%\n]+', ttype),
            (r'[\'"\\]', ttype),
            # unhandled string formatting sign
            (r'%', ttype),
            # newlines are an error (use "nl" state)
        ]

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'^(\s*)([rRuUbB]{,2})("""(?:.|\n)*?""")',
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r"^(\s*)([rRuUbB]{,2})('''(?:.|\n)*?''')",
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r'[^\S\n]+', Text),
            (r'\A#!.+$', Comment.Hashbang),
            (r'#.*$', Comment.Single),
            (r'[]{}:(),;[]', Punctuation),
            (r'\\\n', Text),
            (r'\\', Text),
            (r'(in|is|and|or|not)\b', Operator.Word),
            (r'!=|==|<<|>>|[-~+/*%=<>&^|.]', Operator),
            include('keywords'),
            (r'(def)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'funcname'),
            (r'(class)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'classname'),
            (r'(from)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Text),
             'fromimport'),
            (r'(import)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Text),
             'import'),
            include('builtins'),
            include('magicfuncs'),
            include('magicvars'),
            include('backtick'),
            ('([rR]|[uUbB][rR]|[rR][uUbB])(""")',
             bygroups(String.Affix, String.Double), 'tdqs'),
            ("([rR]|[uUbB][rR]|[rR][uUbB])(''')",
             bygroups(String.Affix, String.Single), 'tsqs'),
            ('([rR]|[uUbB][rR]|[rR][uUbB])(")',
             bygroups(String.Affix, String.Double), 'dqs'),
            ("([rR]|[uUbB][rR]|[rR][uUbB])(')",
             bygroups(String.Affix, String.Single), 'sqs'),
            ('([uUbB]?)(""")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'tdqs')),
            ("([uUbB]?)(''')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'tsqs')),
            ('([uUbB]?)(")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'dqs')),
            ("([uUbB]?)(')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'sqs')),
            include('name'),
            include('numbers'),
        ],
        'keywords': [
            (words((
                'assert', 'break', 'continue', 'del', 'elif', 'else', 'except',
                'exec', 'finally', 'for', 'global', 'if', 'lambda', 'pass',
                'print', 'raise', 'return', 'try', 'while', 'yield',
                'yield from', 'as', 'with'), suffix=r'\b'),
             Keyword),
        ],
        'builtins': [
            (words((
                '__import__', 'abs', 'all', 'any', 'apply', 'basestring', 'bin',
                'bool', 'buffer', 'bytearray', 'bytes', 'callable', 'chr', 'classmethod',
                'cmp', 'coerce', 'compile', 'complex', 'delattr', 'dict', 'dir', 'divmod',
                'enumerate', 'eval', 'execfile', 'exit', 'file', 'filter', 'float',
                'frozenset', 'getattr', 'globals', 'hasattr', 'hash', 'hex', 'id',
                'input', 'int', 'intern', 'isinstance', 'issubclass', 'iter', 'len',
                'list', 'locals', 'long', 'map', 'max', 'min', 'next', 'object',
                'oct', 'open', 'ord', 'pow', 'property', 'range', 'raw_input', 'reduce',
                'reload', 'repr', 'reversed', 'round', 'set', 'setattr', 'slice',
                'sorted', 'staticmethod', 'str', 'sum', 'super', 'tuple', 'type',
                'unichr', 'unicode', 'vars', 'xrange', 'zip'),
                prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Builtin),
            (r'(?<!\.)(self|None|Ellipsis|NotImplemented|False|True|cls'
             r')\b', Name.Builtin.Pseudo),
            (words((
                'ArithmeticError', 'AssertionError', 'AttributeError',
                'BaseException', 'DeprecationWarning', 'EOFError', 'EnvironmentError',
                'Exception', 'FloatingPointError', 'FutureWarning', 'GeneratorExit',
                'IOError', 'ImportError', 'ImportWarning', 'IndentationError',
                'IndexError', 'KeyError', 'KeyboardInterrupt', 'LookupError',
                'MemoryError', 'NameError',
                'NotImplementedError', 'OSError', 'OverflowError', 'OverflowWarning',
                'PendingDeprecationWarning', 'ReferenceError',
                'RuntimeError', 'RuntimeWarning', 'StandardError', 'StopIteration',
                'SyntaxError', 'SyntaxWarning', 'SystemError', 'SystemExit',
                'TabError', 'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
                'UnicodeEncodeError', 'UnicodeError', 'UnicodeTranslateError',
                'UnicodeWarning', 'UserWarning', 'ValueError', 'VMSError', 'Warning',
                'WindowsError', 'ZeroDivisionError'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Exception),
        ],
        'magicfuncs': [
            (words((
                '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__',
                '__complex__', '__contains__', '__del__', '__delattr__', '__delete__',
                '__delitem__', '__delslice__', '__div__', '__divmod__', '__enter__',
                '__eq__', '__exit__', '__float__', '__floordiv__', '__ge__', '__get__',
                '__getattr__', '__getattribute__', '__getitem__', '__getslice__', '__gt__',
                '__hash__', '__hex__', '__iadd__', '__iand__', '__idiv__', '__ifloordiv__',
                '__ilshift__', '__imod__', '__imul__', '__index__', '__init__',
                '__instancecheck__', '__int__', '__invert__', '__iop__', '__ior__',
                '__ipow__', '__irshift__', '__isub__', '__iter__', '__itruediv__',
                '__ixor__', '__le__', '__len__', '__long__', '__lshift__', '__lt__',
                '__missing__', '__mod__', '__mul__', '__ne__', '__neg__', '__new__',
                '__nonzero__', '__oct__', '__op__', '__or__', '__pos__', '__pow__',
                '__radd__', '__rand__', '__rcmp__', '__rdiv__', '__rdivmod__', '__repr__',
                '__reversed__', '__rfloordiv__', '__rlshift__', '__rmod__', '__rmul__',
                '__rop__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__',
                '__rtruediv__', '__rxor__', '__set__', '__setattr__', '__setitem__',
                '__setslice__', '__str__', '__sub__', '__subclasscheck__', '__truediv__',
                '__unicode__', '__xor__'), suffix=r'\b'),
             Name.Function.Magic),
        ],
        'magicvars': [
            (words((
                '__bases__', '__class__', '__closure__', '__code__', '__defaults__',
                '__dict__', '__doc__', '__file__', '__func__', '__globals__',
                '__metaclass__', '__module__', '__mro__', '__name__', '__self__',
                '__slots__', '__weakref__'),
                suffix=r'\b'),
             Name.Variable.Magic),
        ],
        'numbers': [
            (r'(\d+\.\d*|\d*\.\d+)([eE][+-]?[0-9]+)?j?', Number.Float),
            (r'\d+[eE][+-]?[0-9]+j?', Number.Float),
            (r'0[0-7]+j?', Number.Oct),
            (r'0[bB][01]+', Number.Bin),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (r'\d+L', Number.Integer.Long),
            (r'\d+j?', Number.Integer)
        ],
        'backtick': [
            ('`.*?`', String.Backtick),
        ],
        'name': [
            (r'@[\w.]+', Name.Decorator),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'funcname': [
            include('magicfuncs'),
            (r'[a-zA-Z_]\w*', Name.Function, '#pop'),
            default('#pop'),
        ],
        'classname': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'(?:[ \t]|\\\n)+', Text),
            (r'as\b', Keyword.Namespace),
            (r',', Operator),
            (r'[a-zA-Z_][\w.]*', Name.Namespace),
            default('#pop')  # all else: go back
        ],
        'fromimport': [
            (r'(?:[ \t]|\\\n)+', Text),
            (r'import\b', Keyword.Namespace, '#pop'),
            # if None occurs here, it's "raise x from None", since None can
            # never be a module name
            (r'None\b', Name.Builtin.Pseudo, '#pop'),
            # sadly, in "raise x from y" y will be highlighted as namespace too
            (r'[a-zA-Z_.][\w.]*', Name.Namespace),
            # anything else here also means "raise x from y" and is therefore
            # not an error
            default('#pop'),
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'strings-single': innerstring_rules(String.Single),
        'strings-double': innerstring_rules(String.Double),
        'dqs': [
            (r'"', String.Double, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include('strings-double')
        ],
        'sqs': [
            (r"'", String.Single, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include('strings-single')
        ],
        'tdqs': [
            (r'"""', String.Double, '#pop'),
            include('strings-double'),
            (r'\n', String.Double)
        ],
        'tsqs': [
            (r"'''", String.Single, '#pop'),
            include('strings-single'),
            (r'\n', String.Single)
        ],
    }

    def analyse_text(text):
        return shebang_matches(text, r'pythonw?2(\.\d)?')

class _PythonConsoleLexerBase(RegexLexer):
    name = 'Python console session'
    aliases = ['pycon', 'python-console']
    mimetypes = ['text/x-python-doctest']

    """Auxiliary lexer for `PythonConsoleLexer`.

    Code tokens are output as ``Token.Other.Code``, traceback tokens as
    ``Token.Other.Traceback``.
    """
    tokens = {
        'root': [
            (r'(>>> )(.*\n)', bygroups(Generic.Prompt, Other.Code), 'continuations'),
            # This happens, e.g., when tracebacks are embedded in documentation;
            # trailing whitespaces are often stripped in such contexts.
            (r'(>>>)(\n)', bygroups(Generic.Prompt, Whitespace)),
            (r'(\^C)?Traceback \(most recent call last\):\n', Other.Traceback, 'traceback'),
            # SyntaxError starts with this
            (r'  File "[^"]+", line \d+', Other.Traceback, 'traceback'),
            (r'.*\n', Generic.Output),
        ],
        'continuations': [
            (r'(\.\.\. )(.*\n)', bygroups(Generic.Prompt, Other.Code)),
            # See above.
            (r'(\.\.\.)(\n)', bygroups(Generic.Prompt, Whitespace)),
            default('#pop'),
        ],
        'traceback': [
            # As soon as we see a traceback, consume everything until the next
            # >>> prompt.
            (r'(?=>>>( |$))', Text, '#pop'),
            (r'(KeyboardInterrupt)(\n)', bygroups(Name.Class, Whitespace)),
            (r'.*\n', Other.Traceback),
        ],
    }

class PythonConsoleLexer(DelegatingLexer):
    """
    For Python console output or doctests, such as:

    .. sourcecode:: pycon

        >>> a = 'foo'
        >>> print(a)
        foo
        >>> 1 / 0
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        ZeroDivisionError: integer division or modulo by zero

    Additional options:

    `python3`
        Use Python 3 lexer for code.  Default is ``True``.

        .. versionadded:: 1.0
        .. versionchanged:: 2.5
           Now defaults to ``True``.
    """

    name = 'Python console session'
    aliases = ['pycon', 'python-console']
    mimetypes = ['text/x-python-doctest']
    url = 'https://python.org'
    version_added = ''

    def __init__(self, **options):
        python3 = get_bool_opt(options, 'python3', True)
        if python3:
            pylexer = PythonLexer
            tblexer = PythonTracebackLexer
        else:
            pylexer = Python2Lexer
            tblexer = Python2TracebackLexer
        # We have two auxiliary lexers. Use DelegatingLexer twice with
        # different tokens.  TODO: DelegatingLexer should support this
        # directly, by accepting a tuplet of auxiliary lexers and a tuple of
        # distinguishing tokens. Then we wouldn't need this intermediary
        # class.
        class _ReplaceInnerCode(DelegatingLexer):
            def __init__(self, **options):
                super().__init__(pylexer, _PythonConsoleLexerBase, Other.Code, **options)
        super().__init__(tblexer, _ReplaceInnerCode, Other.Traceback, **options)

class PythonTracebackLexer(RegexLexer):
    """
    For Python 3.x tracebacks, with support for chained exceptions.

    .. versionchanged:: 2.5
       This is now the default ``PythonTracebackLexer``.  It is still available
       as the alias ``Python3TracebackLexer``.
    """

    name = 'Python Traceback'
    aliases = ['pytb', 'py3tb']
    filenames = ['*.pytb', '*.py3tb']
    mimetypes = ['text/x-python-traceback', 'text/x-python3-traceback']
    url = 'https://python.org'
    version_added = '1.0'

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'^(\^C)?Traceback \(most recent call last\):\n', Generic.Traceback, 'intb'),
            (r'^During handling of the above exception, another '
             r'exception occurred:\n\n', Generic.Traceback),
            (r'^The above exception was the direct cause of the '
             r'following exception:\n\n', Generic.Traceback),
            (r'^(?=  File "[^"]+", line \d+)', Generic.Traceback, 'intb'),
            (r'^.*\n', Other),
        ],
        'intb': [
            (r'^(  File )("[^"]+")(, line )(\d+)(, in )(.+)(\n)',
             bygroups(Text, Name.Builtin, Text, Number, Text, Name, Whitespace)),
            (r'^(  File )("[^"]+")(, line )(\d+)(\n)',
             bygroups(Text, Name.Builtin, Text, Number, Whitespace)),
            (r'^(    )(.+)(\n)',
             bygroups(Whitespace, using(PythonLexer), Whitespace), 'markers'),
            (r'^([ \t]*)(\.\.\.)(\n)',
             bygroups(Whitespace, Comment, Whitespace)),  # for doctests...
            (r'^([^:]+)(: )(.+)(\n)',
             bygroups(Generic.Error, Text, Name, Whitespace), '#pop'),
            (r'^([a-zA-Z_][\w.]*)(:?\n)',
             bygroups(Generic.Error, Whitespace), '#pop'),
            default('#pop'),
        ],
        'markers': [
            # Either `PEP 657 <https://www.python.org/dev/peps/pep-0657/>`
            # error locations in Python 3.11+, or single-caret markers
            # for syntax errors before that.
            (r'^( {4,})([~^]+)(\n)',
             bygroups(Whitespace, Punctuation.Marker, Whitespace),
             '#pop'),
            default('#pop'),
        ],
    }


Python3TracebackLexer = PythonTracebackLexer


class Python2TracebackLexer(RegexLexer):
    """
    For Python tracebacks.

    .. versionchanged:: 2.5
       This class has been renamed from ``PythonTracebackLexer``.
       ``PythonTracebackLexer`` now refers to the Python 3 variant.
    """

    name = 'Python 2.x Traceback'
    aliases = ['py2tb']
    filenames = ['*.py2tb']
    mimetypes = ['text/x-python2-traceback']
    url = 'https://python.org'
    version_added = '0.7'

    tokens = {
        'root': [
            # Cover both (most recent call last) and (innermost last)
            # The optional ^C allows us to catch keyboard interrupt signals.
            (r'^(\^C)?(Traceback.*\n)',
             bygroups(Text, Generic.Traceback), 'intb'),
            # SyntaxError starts with this.
            (r'^(?=  File "[^"]+", line \d+)', Generic.Traceback, 'intb'),
            (r'^.*\n', Other),
        ],
        'intb': [
            (r'^(  File )("[^"]+")(, line )(\d+)(, in )(.+)(\n)',
             bygroups(Text, Name.Builtin, Text, Number, Text, Name, Whitespace)),
            (r'^(  File )("[^"]+")(, line )(\d+)(\n)',
             bygroups(Text, Name.Builtin, Text, Number, Whitespace)),
            (r'^(    )(.+)(\n)',
             bygroups(Text, using(Python2Lexer), Whitespace), 'marker'),
            (r'^([ \t]*)(\.\.\.)(\n)',
             bygroups(Text, Comment, Whitespace)),  # for doctests...
            (r'^([^:]+)(: )(.+)(\n)',
             bygroups(Generic.Error, Text, Name, Whitespace), '#pop'),
            (r'^([a-zA-Z_]\w*)(:?\n)',
             bygroups(Generic.Error, Whitespace), '#pop')
        ],
        'marker': [
            # For syntax errors.
            (r'( {4,})(\^)', bygroups(Text, Punctuation.Marker), '#pop'),
            default('#pop'),
        ],
    }


class CythonLexer(RegexLexer):
    """
    For Pyrex and Cython source code.
    """

    name = 'Cython'
    url = 'https://cython.org'
    aliases = ['cython', 'pyx', 'pyrex']
    filenames = ['*.pyx', '*.pxd', '*.pxi']
    mimetypes = ['text/x-cython', 'application/x-cython']
    version_added = '1.1'

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'^(\s*)("""(?:.|\n)*?""")', bygroups(Whitespace, String.Doc)),
            (r"^(\s*)('''(?:.|\n)*?''')", bygroups(Whitespace, String.Doc)),
            (r'[^\S\n]+', Text),
            (r'#.*$', Comment),
            (r'[]{}:(),;[]', Punctuation),
            (r'\\\n', Whitespace),
            (r'\\', Text),
            (r'(in|is|and|or|not)\b', Operator.Word),
            (r'(<)([a-zA-Z0-9.?]+)(>)',
             bygroups(Punctuation, Keyword.Type, Punctuation)),
            (r'!=|==|<<|>>|[-~+/*%=<>&^|.?]', Operator),
            (r'(from)(\d+)(<=)(\s+)(<)(\d+)(:)',
             bygroups(Keyword, Number.Integer, Operator, Name, Operator,
                      Name, Punctuation)),
            include('keywords'),
            (r'(def|property)(\s+)', bygroups(Keyword, Text), 'funcname'),
            (r'(cp?def)(\s+)', bygroups(Keyword, Text), 'cdef'),
            # (should actually start a block with only cdefs)
            (r'(cdef)(:)', bygroups(Keyword, Punctuation)),
            (r'(class|struct)(\s+)', bygroups(Keyword, Text), 'classname'),
            (r'(from)(\s+)', bygroups(Keyword, Text), 'fromimport'),
            (r'(c?import)(\s+)', bygroups(Keyword, Text), 'import'),
            include('builtins'),
            include('backtick'),
            ('(?:[rR]|[uU][rR]|[rR][uU])"""', String, 'tdqs'),
            ("(?:[rR]|[uU][rR]|[rR][uU])'''", String, 'tsqs'),
            ('(?:[rR]|[uU][rR]|[rR][uU])"', String, 'dqs'),
            ("(?:[rR]|[uU][rR]|[rR][uU])'", String, 'sqs'),
            ('[uU]?"""', String, combined('stringescape', 'tdqs')),
            ("[uU]?'''", String, combined('stringescape', 'tsqs')),
            ('[uU]?"', String, combined('stringescape', 'dqs')),
            ("[uU]?'", String, combined('stringescape', 'sqs')),
            include('name'),
            include('numbers'),
        ],
        'keywords': [
            (words((
                'assert', 'async', 'await', 'break', 'by', 'continue', 'ctypedef', 'del', 'elif',
                'else', 'except', 'except?', 'exec', 'finally', 'for', 'fused', 'gil',
                'global', 'if', 'include', 'lambda', 'nogil', 'pass', 'print',
                'raise', 'return', 'try', 'while', 'yield', 'as', 'with'), suffix=r'\b'),
             Keyword),
            (r'(DEF|IF|ELIF|ELSE)\b', Comment.Preproc),
        ],
        'builtins': [
            (words((
                '__import__', 'abs', 'all', 'any', 'apply', 'basestring', 'bin', 'bint',
                'bool', 'buffer', 'bytearray', 'bytes', 'callable', 'chr',
                'classmethod', 'cmp', 'coerce', 'compile', 'complex', 'delattr',
                'dict', 'dir', 'divmod', 'enumerate', 'eval', 'execfile', 'exit',
                'file', 'filter', 'float', 'frozenset', 'getattr', 'globals',
                'hasattr', 'hash', 'hex', 'id', 'input', 'int', 'intern', 'isinstance',
                'issubclass', 'iter', 'len', 'list', 'locals', 'long', 'map', 'max',
                'min', 'next', 'object', 'oct', 'open', 'ord', 'pow', 'property', 'Py_ssize_t',
                'range', 'raw_input', 'reduce', 'reload', 'repr', 'reversed',
                'round', 'set', 'setattr', 'slice', 'sorted', 'staticmethod',
                'str', 'sum', 'super', 'tuple', 'type', 'unichr', 'unicode', 'unsigned',
                'vars', 'xrange', 'zip'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Builtin),
            (r'(?<!\.)(self|None|Ellipsis|NotImplemented|False|True|NULL'
             r')\b', Name.Builtin.Pseudo),
            (words((
                'ArithmeticError', 'AssertionError', 'AttributeError',
                'BaseException', 'DeprecationWarning', 'EOFError', 'EnvironmentError',
                'Exception', 'FloatingPointError', 'FutureWarning', 'GeneratorExit',
                'IOError', 'ImportError', 'ImportWarning', 'IndentationError',
                'IndexError', 'KeyError', 'KeyboardInterrupt', 'LookupError',
                'MemoryError', 'NameError', 'NotImplemented', 'NotImplementedError',
                'OSError', 'OverflowError', 'OverflowWarning',
                'PendingDeprecationWarning', 'ReferenceError', 'RuntimeError',
                'RuntimeWarning', 'StandardError', 'StopIteration', 'SyntaxError',
                'SyntaxWarning', 'SystemError', 'SystemExit', 'TabError',
                'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
                'UnicodeEncodeError', 'UnicodeError', 'UnicodeTranslateError',
                'UnicodeWarning', 'UserWarning', 'ValueError', 'Warning',
                'ZeroDivisionError'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Exception),
        ],
        'numbers': [
            (r'(\d+\.?\d*|\d*\.\d+)([eE][+-]?[0-9]+)?', Number.Float),
            (r'0\d+', Number.Oct),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (r'\d+L', Number.Integer.Long),
            (r'\d+', Number.Integer)
        ],
        'backtick': [
            ('`.*?`', String.Backtick),
        ],
        'name': [
            (r'@\w+', Name.Decorator),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'funcname': [
            (r'[a-zA-Z_]\w*', Name.Function, '#pop')
        ],
        'cdef': [
            (r'(public|readonly|extern|api|inline)\b', Keyword.Reserved),
            (r'(struct|enum|union|class)\b', Keyword),
            (r'([a-zA-Z_]\w*)(\s*)(?=[(:#=]|$)',
             bygroups(Name.Function, Text), '#pop'),
            (r'([a-zA-Z_]\w*)(\s*)(,)',
             bygroups(Name.Function, Text, Punctuation)),
            (r'from\b', Keyword, '#pop'),
            (r'as\b', Keyword),
            (r':', Punctuation, '#pop'),
            (r'(?=["\'])', Text, '#pop'),
            (r'[a-zA-Z_]\w*', Keyword.Type),
            (r'.', Text),
        ],
        'classname': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'(\s+)(as)(\s+)', bygroups(Text, Keyword, Text)),
            (r'[a-zA-Z_][\w.]*', Name.Namespace),
            (r'(\s*)(,)(\s*)', bygroups(Text, Operator, Text)),
            default('#pop')  # all else: go back
        ],
        'fromimport': [
            (r'(\s+)(c?import)\b', bygroups(Text, Keyword), '#pop'),
            (r'[a-zA-Z_.][\w.]*', Name.Namespace),
            # ``cdef foo from "header"``, or ``for foo from 0 < i < 10``
            default('#pop'),
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'strings': [
            (r'%(\([a-zA-Z0-9]+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsux%]', String.Interpol),
            (r'[^\\\'"%\n]+', String),
            # quotes, percents and backslashes must be parsed one at a time
            (r'[\'"\\]', String),
            # unhandled string formatting sign
            (r'%', String)
            # newlines are an error (use "nl" state)
        ],
        'nl': [
            (r'\n', String)
        ],
        'dqs': [
            (r'"', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here again for raw strings
            include('strings')
        ],
        'sqs': [
            (r"'", String, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here again for raw strings
            include('strings')
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            include('strings'),
            include('nl')
        ],
        'tsqs': [
            (r"'''", String, '#pop'),
            include('strings'),
            include('nl')
        ],
    }


class DgLexer(RegexLexer):
    """
    Lexer for dg,
    a functional and object-oriented programming language
    running on the CPython 3 VM.
    """
    name = 'dg'
    aliases = ['dg']
    filenames = ['*.dg']
    mimetypes = ['text/x-dg']
    url = 'http://pyos.github.io/dg'
    version_added = '1.6'

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'#.*?$', Comment.Single),

            (r'(?i)0b[01]+', Number.Bin),
            (r'(?i)0o[0-7]+', Number.Oct),
            (r'(?i)0x[0-9a-f]+', Number.Hex),
            (r'(?i)[+-]?[0-9]+\.[0-9]+(e[+-]?[0-9]+)?j?', Number.Float),
            (r'(?i)[+-]?[0-9]+e[+-]?\d+j?', Number.Float),
            (r'(?i)[+-]?[0-9]+j?', Number.Integer),

            (r"(?i)(br|r?b?)'''", String, combined('stringescape', 'tsqs', 'string')),
            (r'(?i)(br|r?b?)"""', String, combined('stringescape', 'tdqs', 'string')),
            (r"(?i)(br|r?b?)'", String, combined('stringescape', 'sqs', 'string')),
            (r'(?i)(br|r?b?)"', String, combined('stringescape', 'dqs', 'string')),

            (r"`\w+'*`", Operator),
            (r'\b(and|in|is|or|where)\b', Operator.Word),
            (r'[!$%&*+\-./:<-@\\^|~;,]+', Operator),

            (words((
                'bool', 'bytearray', 'bytes', 'classmethod', 'complex', 'dict', 'dict\'',
                'float', 'frozenset', 'int', 'list', 'list\'', 'memoryview', 'object',
                'property', 'range', 'set', 'set\'', 'slice', 'staticmethod', 'str',
                'super', 'tuple', 'tuple\'', 'type'),
                   prefix=r'(?<!\.)', suffix=r'(?![\'\w])'),
             Name.Builtin),
            (words((
                '__import__', 'abs', 'all', 'any', 'bin', 'bind', 'chr', 'cmp', 'compile',
                'complex', 'delattr', 'dir', 'divmod', 'drop', 'dropwhile', 'enumerate',
                'eval', 'exhaust', 'filter', 'flip', 'foldl1?', 'format', 'fst',
                'getattr', 'globals', 'hasattr', 'hash', 'head', 'hex', 'id', 'init',
                'input', 'isinstance', 'issubclass', 'iter', 'iterate', 'last', 'len',
                'locals', 'map', 'max', 'min', 'next', 'oct', 'open', 'ord', 'pow',
                'print', 'repr', 'reversed', 'round', 'setattr', 'scanl1?', 'snd',
                'sorted', 'sum', 'tail', 'take', 'takewhile', 'vars', 'zip'),
                   prefix=r'(?<!\.)', suffix=r'(?![\'\w])'),
             Name.Builtin),
            (r"(?<!\.)(self|Ellipsis|NotImplemented|None|True|False)(?!['\w])",
             Name.Builtin.Pseudo),

            (r"(?<!\.)[A-Z]\w*(Error|Exception|Warning)'*(?!['\w])",
             Name.Exception),
            (r"(?<!\.)(Exception|GeneratorExit|KeyboardInterrupt|StopIteration|"
             r"SystemExit)(?!['\w])", Name.Exception),

            (r"(?<![\w.])(except|finally|for|if|import|not|otherwise|raise|"
             r"subclass|while|with|yield)(?!['\w])", Keyword.Reserved),

            (r"[A-Z_]+'*(?!['\w])", Name),
            (r"[A-Z]\w+'*(?!['\w])", Keyword.Type),
            (r"\w+'*", Name),

            (r'[()]', Punctuation),
            (r'.', Error),
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'string': [
            (r'%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsux%]', String.Interpol),
            (r'[^\\\'"%\n]+', String),
            # quotes, percents and backslashes must be parsed one at a time
            (r'[\'"\\]', String),
            # unhandled string formatting sign
            (r'%', String),
            (r'\n', String)
        ],
        'dqs': [
            (r'"', String, '#pop')
        ],
        'sqs': [
            (r"'", String, '#pop')
        ],
        'tdqs': [
            (r'"""', String, '#pop')
        ],
        'tsqs': [
            (r"'''", String, '#pop')
        ],
    }


class NumPyLexer(PythonLexer):
    """
    A Python lexer recognizing Numerical Python builtins.
    """

    name = 'NumPy'
    url = 'https://numpy.org/'
    aliases = ['numpy']
    version_added = '0.10'

    # override the mimetypes to not inherit them from python
    mimetypes = []
    filenames = []

    EXTRA_KEYWORDS = {
        'abs', 'absolute', 'accumulate', 'add', 'alen', 'all', 'allclose',
        'alltrue', 'alterdot', 'amax', 'amin', 'angle', 'any', 'append',
        'apply_along_axis', 'apply_over_axes', 'arange', 'arccos', 'arccosh',
        'arcsin', 'arcsinh', 'arctan', 'arctan2', 'arctanh', 'argmax', 'argmin',
        'argsort', 'argwhere', 'around', 'array', 'array2string', 'array_equal',
        'array_equiv', 'array_repr', 'array_split', 'array_str', 'arrayrange',
        'asanyarray', 'asarray', 'asarray_chkfinite', 'ascontiguousarray',
        'asfarray', 'asfortranarray', 'asmatrix', 'asscalar', 'astype',
        'atleast_1d', 'atleast_2d', 'atleast_3d', 'average', 'bartlett',
        'base_repr', 'beta', 'binary_repr', 'bincount', 'binomial',
        'bitwise_and', 'bitwise_not', 'bitwise_or', 'bitwise_xor', 'blackman',
        'bmat', 'broadcast', 'byte_bounds', 'bytes', 'byteswap', 'c_',
        'can_cast', 'ceil', 'choose', 'clip', 'column_stack', 'common_type',
        'compare_chararrays', 'compress', 'concatenate', 'conj', 'conjugate',
        'convolve', 'copy', 'corrcoef', 'correlate', 'cos', 'cosh', 'cov',
        'cross', 'cumprod', 'cumproduct', 'cumsum', 'delete', 'deprecate',
        'diag', 'diagflat', 'diagonal', 'diff', 'digitize', 'disp', 'divide',
        'dot', 'dsplit', 'dstack', 'dtype', 'dump', 'dumps', 'ediff1d', 'empty',
        'empty_like', 'equal', 'exp', 'expand_dims', 'expm1', 'extract', 'eye',
        'fabs', 'fastCopyAndTranspose', 'fft', 'fftfreq', 'fftshift', 'fill',
        'finfo', 'fix', 'flat', 'flatnonzero', 'flatten', 'fliplr', 'flipud',
        'floor', 'floor_divide', 'fmod', 'frexp', 'fromarrays', 'frombuffer',
        'fromfile', 'fromfunction', 'fromiter', 'frompyfunc', 'fromstring',
        'generic', 'get_array_wrap', 'get_include', 'get_numarray_include',
        'get_numpy_include', 'get_printoptions', 'getbuffer', 'getbufsize',
        'geterr', 'geterrcall', 'geterrobj', 'getfield', 'gradient', 'greater',
        'greater_equal', 'gumbel', 'hamming', 'hanning', 'histogram',
        'histogram2d', 'histogramdd', 'hsplit', 'hstack', 'hypot', 'i0',
        'identity', 'ifft', 'imag', 'index_exp', 'indices', 'inf', 'info',
        'inner', 'insert', 'int_asbuffer', 'interp', 'intersect1d',
        'intersect1d_nu', 'inv', 'invert', 'iscomplex', 'iscomplexobj',
        'isfinite', 'isfortran', 'isinf', 'isnan', 'isneginf', 'isposinf',
        'isreal', 'isrealobj', 'isscalar', 'issctype', 'issubclass_',
        'issubdtype', 'issubsctype', 'item', 'itemset', 'iterable', 'ix_',
        'kaiser', 'kron', 'ldexp', 'left_shift', 'less', 'less_equal', 'lexsort',
        'linspace', 'load', 'loads', 'loadtxt', 'log', 'log10', 'log1p', 'log2',
        'logical_and', 'logical_not', 'logical_or', 'logical_xor', 'logspace',
        'lstsq', 'mat', 'matrix', 'max', 'maximum', 'maximum_sctype',
        'may_share_memory', 'mean', 'median', 'meshgrid', 'mgrid', 'min',
        'minimum', 'mintypecode', 'mod', 'modf', 'msort', 'multiply', 'nan',
        'nan_to_num', 'nanargmax', 'nanargmin', 'nanmax', 'nanmin', 'nansum',
        'ndenumerate', 'ndim', 'ndindex', 'negative', 'newaxis', 'newbuffer',
        'newbyteorder', 'nonzero', 'not_equal', 'obj2sctype', 'ogrid', 'ones',
        'ones_like', 'outer', 'permutation', 'piecewise', 'pinv', 'pkgload',
        'place', 'poisson', 'poly', 'poly1d', 'polyadd', 'polyder', 'polydiv',
        'polyfit', 'polyint', 'polymul', 'polysub', 'polyval', 'power', 'prod',
        'product', 'ptp', 'put', 'putmask', 'r_', 'randint', 'random_integers',
        'random_sample', 'ranf', 'rank', 'ravel', 'real', 'real_if_close',
        'recarray', 'reciprocal', 'reduce', 'remainder', 'repeat', 'require',
        'reshape', 'resize', 'restoredot', 'right_shift', 'rint', 'roll',
        'rollaxis', 'roots', 'rot90', 'round', 'round_', 'row_stack', 's_',
        'sample', 'savetxt', 'sctype2char', 'searchsorted', 'seed', 'select',
        'set_numeric_ops', 'set_printoptions', 'set_string_function',
        'setbufsize', 'setdiff1d', 'seterr', 'seterrcall', 'seterrobj',
        'setfield', 'setflags', 'setmember1d', 'setxor1d', 'shape',
        'show_config', 'shuffle', 'sign', 'signbit', 'sin', 'sinc', 'sinh',
        'size', 'slice', 'solve', 'sometrue', 'sort', 'sort_complex', 'source',
        'split', 'sqrt', 'square', 'squeeze', 'standard_normal', 'std',
        'subtract', 'sum', 'svd', 'swapaxes', 'take', 'tan', 'tanh', 'tensordot',
        'test', 'tile', 'tofile', 'tolist', 'tostring', 'trace', 'transpose',
        'trapz', 'tri', 'tril', 'trim_zeros', 'triu', 'true_divide', 'typeDict',
        'typename', 'uniform', 'union1d', 'unique', 'unique1d', 'unravel_index',
        'unwrap', 'vander', 'var', 'vdot', 'vectorize', 'view', 'vonmises',
        'vsplit', 'vstack', 'weibull', 'where', 'who', 'zeros', 'zeros_like'
    }

    def get_tokens_unprocessed(self, text):
        for index, token, value in \
                PythonLexer.get_tokens_unprocessed(self, text):
            if token is Name and value in self.EXTRA_KEYWORDS:
                yield index, Keyword.Pseudo, value
            else:
                yield index, token, value

    def analyse_text(text):
        ltext = text[:1000]
        return (shebang_matches(text, r'pythonw?(3(\.\d)?)?') or
                'import ' in ltext) \
            and ('import numpy' in ltext or 'from numpy import' in ltext)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\lexers\python.py ===
"""
    pygments.lexers.python
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Python and related languages.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import keyword

from pip._vendor.pygments.lexer import DelegatingLexer, RegexLexer, include, \
    bygroups, using, default, words, combined, this
from pip._vendor.pygments.util import get_bool_opt, shebang_matches
from pip._vendor.pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic, Other, Error, Whitespace
from pip._vendor.pygments import unistring as uni

__all__ = ['PythonLexer', 'PythonConsoleLexer', 'PythonTracebackLexer',
           'Python2Lexer', 'Python2TracebackLexer',
           'CythonLexer', 'DgLexer', 'NumPyLexer']


class PythonLexer(RegexLexer):
    """
    For Python source code (version 3.x).

    .. versionchanged:: 2.5
       This is now the default ``PythonLexer``.  It is still available as the
       alias ``Python3Lexer``.
    """

    name = 'Python'
    url = 'https://www.python.org'
    aliases = ['python', 'py', 'sage', 'python3', 'py3', 'bazel', 'starlark']
    filenames = [
        '*.py',
        '*.pyw',
        # Type stubs
        '*.pyi',
        # Jython
        '*.jy',
        # Sage
        '*.sage',
        # SCons
        '*.sc',
        'SConstruct',
        'SConscript',
        # Skylark/Starlark (used by Bazel, Buck, and Pants)
        '*.bzl',
        'BUCK',
        'BUILD',
        'BUILD.bazel',
        'WORKSPACE',
        # Twisted Application infrastructure
        '*.tac',
    ]
    mimetypes = ['text/x-python', 'application/x-python',
                 'text/x-python3', 'application/x-python3']
    version_added = '0.10'

    uni_name = f"[{uni.xid_start}][{uni.xid_continue}]*"

    def innerstring_rules(ttype):
        return [
            # the old style '%s' % (...) string formatting (still valid in Py3)
            (r'%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsaux%]', String.Interpol),
            # the new style '{}'.format(...) string formatting
            (r'\{'
             r'((\w+)((\.\w+)|(\[[^\]]+\]))*)?'  # field name
             r'(\![sra])?'                       # conversion
             r'(\:(.?[<>=\^])?[-+ ]?#?0?(\d+)?,?(\.\d+)?[E-GXb-gnosx%]?)?'
             r'\}', String.Interpol),

            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"%{\n]+', ttype),
            (r'[\'"\\]', ttype),
            # unhandled string formatting sign
            (r'%|(\{{1,2})', ttype)
            # newlines are an error (use "nl" state)
        ]

    def fstring_rules(ttype):
        return [
            # Assuming that a '}' is the closing brace after format specifier.
            # Sadly, this means that we won't detect syntax error. But it's
            # more important to parse correct syntax correctly, than to
            # highlight invalid syntax.
            (r'\}', String.Interpol),
            (r'\{', String.Interpol, 'expr-inside-fstring'),
            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"{}\n]+', ttype),
            (r'[\'"\\]', ttype),
            # newlines are an error (use "nl" state)
        ]

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'^(\s*)([rRuUbB]{,2})("""(?:.|\n)*?""")',
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r"^(\s*)([rRuUbB]{,2})('''(?:.|\n)*?''')",
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r'\A#!.+$', Comment.Hashbang),
            (r'#.*$', Comment.Single),
            (r'\\\n', Text),
            (r'\\', Text),
            include('keywords'),
            include('soft-keywords'),
            (r'(def)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'funcname'),
            (r'(class)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'classname'),
            (r'(from)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Text),
             'fromimport'),
            (r'(import)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Text),
             'import'),
            include('expr'),
        ],
        'expr': [
            # raw f-strings
            ('(?i)(rf|fr)(""")',
             bygroups(String.Affix, String.Double),
             combined('rfstringescape', 'tdqf')),
            ("(?i)(rf|fr)(''')",
             bygroups(String.Affix, String.Single),
             combined('rfstringescape', 'tsqf')),
            ('(?i)(rf|fr)(")',
             bygroups(String.Affix, String.Double),
             combined('rfstringescape', 'dqf')),
            ("(?i)(rf|fr)(')",
             bygroups(String.Affix, String.Single),
             combined('rfstringescape', 'sqf')),
            # non-raw f-strings
            ('([fF])(""")', bygroups(String.Affix, String.Double),
             combined('fstringescape', 'tdqf')),
            ("([fF])(''')", bygroups(String.Affix, String.Single),
             combined('fstringescape', 'tsqf')),
            ('([fF])(")', bygroups(String.Affix, String.Double),
             combined('fstringescape', 'dqf')),
            ("([fF])(')", bygroups(String.Affix, String.Single),
             combined('fstringescape', 'sqf')),
            # raw bytes and strings
            ('(?i)(rb|br|r)(""")',
             bygroups(String.Affix, String.Double), 'tdqs'),
            ("(?i)(rb|br|r)(''')",
             bygroups(String.Affix, String.Single), 'tsqs'),
            ('(?i)(rb|br|r)(")',
             bygroups(String.Affix, String.Double), 'dqs'),
            ("(?i)(rb|br|r)(')",
             bygroups(String.Affix, String.Single), 'sqs'),
            # non-raw strings
            ('([uU]?)(""")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'tdqs')),
            ("([uU]?)(''')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'tsqs')),
            ('([uU]?)(")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'dqs')),
            ("([uU]?)(')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'sqs')),
            # non-raw bytes
            ('([bB])(""")', bygroups(String.Affix, String.Double),
             combined('bytesescape', 'tdqs')),
            ("([bB])(''')", bygroups(String.Affix, String.Single),
             combined('bytesescape', 'tsqs')),
            ('([bB])(")', bygroups(String.Affix, String.Double),
             combined('bytesescape', 'dqs')),
            ("([bB])(')", bygroups(String.Affix, String.Single),
             combined('bytesescape', 'sqs')),

            (r'[^\S\n]+', Text),
            include('numbers'),
            (r'!=|==|<<|>>|:=|[-~+/*%=<>&^|.]', Operator),
            (r'[]{}:(),;[]', Punctuation),
            (r'(in|is|and|or|not)\b', Operator.Word),
            include('expr-keywords'),
            include('builtins'),
            include('magicfuncs'),
            include('magicvars'),
            include('name'),
        ],
        'expr-inside-fstring': [
            (r'[{([]', Punctuation, 'expr-inside-fstring-inner'),
            # without format specifier
            (r'(=\s*)?'         # debug (https://bugs.python.org/issue36817)
             r'(\![sraf])?'     # conversion
             r'\}', String.Interpol, '#pop'),
            # with format specifier
            # we'll catch the remaining '}' in the outer scope
            (r'(=\s*)?'         # debug (https://bugs.python.org/issue36817)
             r'(\![sraf])?'     # conversion
             r':', String.Interpol, '#pop'),
            (r'\s+', Whitespace),  # allow new lines
            include('expr'),
        ],
        'expr-inside-fstring-inner': [
            (r'[{([]', Punctuation, 'expr-inside-fstring-inner'),
            (r'[])}]', Punctuation, '#pop'),
            (r'\s+', Whitespace),  # allow new lines
            include('expr'),
        ],
        'expr-keywords': [
            # Based on https://docs.python.org/3/reference/expressions.html
            (words((
                'async for', 'await', 'else', 'for', 'if', 'lambda',
                'yield', 'yield from'), suffix=r'\b'),
             Keyword),
            (words(('True', 'False', 'None'), suffix=r'\b'), Keyword.Constant),
        ],
        'keywords': [
            (words((
                'assert', 'async', 'await', 'break', 'continue', 'del', 'elif',
                'else', 'except', 'finally', 'for', 'global', 'if', 'lambda',
                'pass', 'raise', 'nonlocal', 'return', 'try', 'while', 'yield',
                'yield from', 'as', 'with'), suffix=r'\b'),
             Keyword),
            (words(('True', 'False', 'None'), suffix=r'\b'), Keyword.Constant),
        ],
        'soft-keywords': [
            # `match`, `case` and `_` soft keywords
            (r'(^[ \t]*)'              # at beginning of line + possible indentation
             r'(match|case)\b'         # a possible keyword
             r'(?![ \t]*(?:'           # not followed by...
             r'[:,;=^&|@~)\]}]|(?:' +  # characters and keywords that mean this isn't
                                       # pattern matching (but None/True/False is ok)
             r'|'.join(k for k in keyword.kwlist if k[0].islower()) + r')\b))',
             bygroups(Text, Keyword), 'soft-keywords-inner'),
        ],
        'soft-keywords-inner': [
            # optional `_` keyword
            (r'(\s+)([^\n_]*)(_\b)', bygroups(Whitespace, using(this), Keyword)),
            default('#pop')
        ],
        'builtins': [
            (words((
                '__import__', 'abs', 'aiter', 'all', 'any', 'bin', 'bool', 'bytearray',
                'breakpoint', 'bytes', 'callable', 'chr', 'classmethod', 'compile',
                'complex', 'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval',
                'filter', 'float', 'format', 'frozenset', 'getattr', 'globals',
                'hasattr', 'hash', 'hex', 'id', 'input', 'int', 'isinstance',
                'issubclass', 'iter', 'len', 'list', 'locals', 'map', 'max',
                'memoryview', 'min', 'next', 'object', 'oct', 'open', 'ord', 'pow',
                'print', 'property', 'range', 'repr', 'reversed', 'round', 'set',
                'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super',
                'tuple', 'type', 'vars', 'zip'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Builtin),
            (r'(?<!\.)(self|Ellipsis|NotImplemented|cls)\b', Name.Builtin.Pseudo),
            (words((
                'ArithmeticError', 'AssertionError', 'AttributeError',
                'BaseException', 'BufferError', 'BytesWarning', 'DeprecationWarning',
                'EOFError', 'EnvironmentError', 'Exception', 'FloatingPointError',
                'FutureWarning', 'GeneratorExit', 'IOError', 'ImportError',
                'ImportWarning', 'IndentationError', 'IndexError', 'KeyError',
                'KeyboardInterrupt', 'LookupError', 'MemoryError', 'NameError',
                'NotImplementedError', 'OSError', 'OverflowError',
                'PendingDeprecationWarning', 'ReferenceError', 'ResourceWarning',
                'RuntimeError', 'RuntimeWarning', 'StopIteration',
                'SyntaxError', 'SyntaxWarning', 'SystemError', 'SystemExit',
                'TabError', 'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
                'UnicodeEncodeError', 'UnicodeError', 'UnicodeTranslateError',
                'UnicodeWarning', 'UserWarning', 'ValueError', 'VMSError',
                'Warning', 'WindowsError', 'ZeroDivisionError',
                # new builtin exceptions from PEP 3151
                'BlockingIOError', 'ChildProcessError', 'ConnectionError',
                'BrokenPipeError', 'ConnectionAbortedError', 'ConnectionRefusedError',
                'ConnectionResetError', 'FileExistsError', 'FileNotFoundError',
                'InterruptedError', 'IsADirectoryError', 'NotADirectoryError',
                'PermissionError', 'ProcessLookupError', 'TimeoutError',
                # others new in Python 3
                'StopAsyncIteration', 'ModuleNotFoundError', 'RecursionError',
                'EncodingWarning'),
                prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Exception),
        ],
        'magicfuncs': [
            (words((
                '__abs__', '__add__', '__aenter__', '__aexit__', '__aiter__',
                '__and__', '__anext__', '__await__', '__bool__', '__bytes__',
                '__call__', '__complex__', '__contains__', '__del__', '__delattr__',
                '__delete__', '__delitem__', '__dir__', '__divmod__', '__enter__',
                '__eq__', '__exit__', '__float__', '__floordiv__', '__format__',
                '__ge__', '__get__', '__getattr__', '__getattribute__',
                '__getitem__', '__gt__', '__hash__', '__iadd__', '__iand__',
                '__ifloordiv__', '__ilshift__', '__imatmul__', '__imod__',
                '__imul__', '__index__', '__init__', '__instancecheck__',
                '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__',
                '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__',
                '__len__', '__length_hint__', '__lshift__', '__lt__', '__matmul__',
                '__missing__', '__mod__', '__mul__', '__ne__', '__neg__',
                '__new__', '__next__', '__or__', '__pos__', '__pow__',
                '__prepare__', '__radd__', '__rand__', '__rdivmod__', '__repr__',
                '__reversed__', '__rfloordiv__', '__rlshift__', '__rmatmul__',
                '__rmod__', '__rmul__', '__ror__', '__round__', '__rpow__',
                '__rrshift__', '__rshift__', '__rsub__', '__rtruediv__',
                '__rxor__', '__set__', '__setattr__', '__setitem__', '__str__',
                '__sub__', '__subclasscheck__', '__truediv__',
                '__xor__'), suffix=r'\b'),
             Name.Function.Magic),
        ],
        'magicvars': [
            (words((
                '__annotations__', '__bases__', '__class__', '__closure__',
                '__code__', '__defaults__', '__dict__', '__doc__', '__file__',
                '__func__', '__globals__', '__kwdefaults__', '__module__',
                '__mro__', '__name__', '__objclass__', '__qualname__',
                '__self__', '__slots__', '__weakref__'), suffix=r'\b'),
             Name.Variable.Magic),
        ],
        'numbers': [
            (r'(\d(?:_?\d)*\.(?:\d(?:_?\d)*)?|(?:\d(?:_?\d)*)?\.\d(?:_?\d)*)'
             r'([eE][+-]?\d(?:_?\d)*)?', Number.Float),
            (r'\d(?:_?\d)*[eE][+-]?\d(?:_?\d)*j?', Number.Float),
            (r'0[oO](?:_?[0-7])+', Number.Oct),
            (r'0[bB](?:_?[01])+', Number.Bin),
            (r'0[xX](?:_?[a-fA-F0-9])+', Number.Hex),
            (r'\d(?:_?\d)*', Number.Integer),
        ],
        'name': [
            (r'@' + uni_name, Name.Decorator),
            (r'@', Operator),  # new matrix multiplication operator
            (uni_name, Name),
        ],
        'funcname': [
            include('magicfuncs'),
            (uni_name, Name.Function, '#pop'),
            default('#pop'),
        ],
        'classname': [
            (uni_name, Name.Class, '#pop'),
        ],
        'import': [
            (r'(\s+)(as)(\s+)', bygroups(Text, Keyword, Text)),
            (r'\.', Name.Namespace),
            (uni_name, Name.Namespace),
            (r'(\s*)(,)(\s*)', bygroups(Text, Operator, Text)),
            default('#pop')  # all else: go back
        ],
        'fromimport': [
            (r'(\s+)(import)\b', bygroups(Text, Keyword.Namespace), '#pop'),
            (r'\.', Name.Namespace),
            # if None occurs here, it's "raise x from None", since None can
            # never be a module name
            (r'None\b', Keyword.Constant, '#pop'),
            (uni_name, Name.Namespace),
            default('#pop'),
        ],
        'rfstringescape': [
            (r'\{\{', String.Escape),
            (r'\}\}', String.Escape),
        ],
        'fstringescape': [
            include('rfstringescape'),
            include('stringescape'),
        ],
        'bytesescape': [
            (r'\\([\\abfnrtv"\']|\n|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'stringescape': [
            (r'\\(N\{.*?\}|u[a-fA-F0-9]{4}|U[a-fA-F0-9]{8})', String.Escape),
            include('bytesescape')
        ],
        'fstrings-single': fstring_rules(String.Single),
        'fstrings-double': fstring_rules(String.Double),
        'strings-single': innerstring_rules(String.Single),
        'strings-double': innerstring_rules(String.Double),
        'dqf': [
            (r'"', String.Double, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include('fstrings-double')
        ],
        'sqf': [
            (r"'", String.Single, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include('fstrings-single')
        ],
        'dqs': [
            (r'"', String.Double, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include('strings-double')
        ],
        'sqs': [
            (r"'", String.Single, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include('strings-single')
        ],
        'tdqf': [
            (r'"""', String.Double, '#pop'),
            include('fstrings-double'),
            (r'\n', String.Double)
        ],
        'tsqf': [
            (r"'''", String.Single, '#pop'),
            include('fstrings-single'),
            (r'\n', String.Single)
        ],
        'tdqs': [
            (r'"""', String.Double, '#pop'),
            include('strings-double'),
            (r'\n', String.Double)
        ],
        'tsqs': [
            (r"'''", String.Single, '#pop'),
            include('strings-single'),
            (r'\n', String.Single)
        ],
    }

    def analyse_text(text):
        return shebang_matches(text, r'pythonw?(3(\.\d)?)?') or \
            'import ' in text[:1000]


Python3Lexer = PythonLexer


class Python2Lexer(RegexLexer):
    """
    For Python 2.x source code.

    .. versionchanged:: 2.5
       This class has been renamed from ``PythonLexer``.  ``PythonLexer`` now
       refers to the Python 3 variant.  File name patterns like ``*.py`` have
       been moved to Python 3 as well.
    """

    name = 'Python 2.x'
    url = 'https://www.python.org'
    aliases = ['python2', 'py2']
    filenames = []  # now taken over by PythonLexer (3.x)
    mimetypes = ['text/x-python2', 'application/x-python2']
    version_added = ''

    def innerstring_rules(ttype):
        return [
            # the old style '%s' % (...) string formatting
            (r'%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsux%]', String.Interpol),
            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"%\n]+', ttype),
            (r'[\'"\\]', ttype),
            # unhandled string formatting sign
            (r'%', ttype),
            # newlines are an error (use "nl" state)
        ]

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'^(\s*)([rRuUbB]{,2})("""(?:.|\n)*?""")',
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r"^(\s*)([rRuUbB]{,2})('''(?:.|\n)*?''')",
             bygroups(Whitespace, String.Affix, String.Doc)),
            (r'[^\S\n]+', Text),
            (r'\A#!.+$', Comment.Hashbang),
            (r'#.*$', Comment.Single),
            (r'[]{}:(),;[]', Punctuation),
            (r'\\\n', Text),
            (r'\\', Text),
            (r'(in|is|and|or|not)\b', Operator.Word),
            (r'!=|==|<<|>>|[-~+/*%=<>&^|.]', Operator),
            include('keywords'),
            (r'(def)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'funcname'),
            (r'(class)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'classname'),
            (r'(from)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Text),
             'fromimport'),
            (r'(import)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Text),
             'import'),
            include('builtins'),
            include('magicfuncs'),
            include('magicvars'),
            include('backtick'),
            ('([rR]|[uUbB][rR]|[rR][uUbB])(""")',
             bygroups(String.Affix, String.Double), 'tdqs'),
            ("([rR]|[uUbB][rR]|[rR][uUbB])(''')",
             bygroups(String.Affix, String.Single), 'tsqs'),
            ('([rR]|[uUbB][rR]|[rR][uUbB])(")',
             bygroups(String.Affix, String.Double), 'dqs'),
            ("([rR]|[uUbB][rR]|[rR][uUbB])(')",
             bygroups(String.Affix, String.Single), 'sqs'),
            ('([uUbB]?)(""")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'tdqs')),
            ("([uUbB]?)(''')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'tsqs')),
            ('([uUbB]?)(")', bygroups(String.Affix, String.Double),
             combined('stringescape', 'dqs')),
            ("([uUbB]?)(')", bygroups(String.Affix, String.Single),
             combined('stringescape', 'sqs')),
            include('name'),
            include('numbers'),
        ],
        'keywords': [
            (words((
                'assert', 'break', 'continue', 'del', 'elif', 'else', 'except',
                'exec', 'finally', 'for', 'global', 'if', 'lambda', 'pass',
                'print', 'raise', 'return', 'try', 'while', 'yield',
                'yield from', 'as', 'with'), suffix=r'\b'),
             Keyword),
        ],
        'builtins': [
            (words((
                '__import__', 'abs', 'all', 'any', 'apply', 'basestring', 'bin',
                'bool', 'buffer', 'bytearray', 'bytes', 'callable', 'chr', 'classmethod',
                'cmp', 'coerce', 'compile', 'complex', 'delattr', 'dict', 'dir', 'divmod',
                'enumerate', 'eval', 'execfile', 'exit', 'file', 'filter', 'float',
                'frozenset', 'getattr', 'globals', 'hasattr', 'hash', 'hex', 'id',
                'input', 'int', 'intern', 'isinstance', 'issubclass', 'iter', 'len',
                'list', 'locals', 'long', 'map', 'max', 'min', 'next', 'object',
                'oct', 'open', 'ord', 'pow', 'property', 'range', 'raw_input', 'reduce',
                'reload', 'repr', 'reversed', 'round', 'set', 'setattr', 'slice',
                'sorted', 'staticmethod', 'str', 'sum', 'super', 'tuple', 'type',
                'unichr', 'unicode', 'vars', 'xrange', 'zip'),
                prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Builtin),
            (r'(?<!\.)(self|None|Ellipsis|NotImplemented|False|True|cls'
             r')\b', Name.Builtin.Pseudo),
            (words((
                'ArithmeticError', 'AssertionError', 'AttributeError',
                'BaseException', 'DeprecationWarning', 'EOFError', 'EnvironmentError',
                'Exception', 'FloatingPointError', 'FutureWarning', 'GeneratorExit',
                'IOError', 'ImportError', 'ImportWarning', 'IndentationError',
                'IndexError', 'KeyError', 'KeyboardInterrupt', 'LookupError',
                'MemoryError', 'NameError',
                'NotImplementedError', 'OSError', 'OverflowError', 'OverflowWarning',
                'PendingDeprecationWarning', 'ReferenceError',
                'RuntimeError', 'RuntimeWarning', 'StandardError', 'StopIteration',
                'SyntaxError', 'SyntaxWarning', 'SystemError', 'SystemExit',
                'TabError', 'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
                'UnicodeEncodeError', 'UnicodeError', 'UnicodeTranslateError',
                'UnicodeWarning', 'UserWarning', 'ValueError', 'VMSError', 'Warning',
                'WindowsError', 'ZeroDivisionError'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Exception),
        ],
        'magicfuncs': [
            (words((
                '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__',
                '__complex__', '__contains__', '__del__', '__delattr__', '__delete__',
                '__delitem__', '__delslice__', '__div__', '__divmod__', '__enter__',
                '__eq__', '__exit__', '__float__', '__floordiv__', '__ge__', '__get__',
                '__getattr__', '__getattribute__', '__getitem__', '__getslice__', '__gt__',
                '__hash__', '__hex__', '__iadd__', '__iand__', '__idiv__', '__ifloordiv__',
                '__ilshift__', '__imod__', '__imul__', '__index__', '__init__',
                '__instancecheck__', '__int__', '__invert__', '__iop__', '__ior__',
                '__ipow__', '__irshift__', '__isub__', '__iter__', '__itruediv__',
                '__ixor__', '__le__', '__len__', '__long__', '__lshift__', '__lt__',
                '__missing__', '__mod__', '__mul__', '__ne__', '__neg__', '__new__',
                '__nonzero__', '__oct__', '__op__', '__or__', '__pos__', '__pow__',
                '__radd__', '__rand__', '__rcmp__', '__rdiv__', '__rdivmod__', '__repr__',
                '__reversed__', '__rfloordiv__', '__rlshift__', '__rmod__', '__rmul__',
                '__rop__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__',
                '__rtruediv__', '__rxor__', '__set__', '__setattr__', '__setitem__',
                '__setslice__', '__str__', '__sub__', '__subclasscheck__', '__truediv__',
                '__unicode__', '__xor__'), suffix=r'\b'),
             Name.Function.Magic),
        ],
        'magicvars': [
            (words((
                '__bases__', '__class__', '__closure__', '__code__', '__defaults__',
                '__dict__', '__doc__', '__file__', '__func__', '__globals__',
                '__metaclass__', '__module__', '__mro__', '__name__', '__self__',
                '__slots__', '__weakref__'),
                suffix=r'\b'),
             Name.Variable.Magic),
        ],
        'numbers': [
            (r'(\d+\.\d*|\d*\.\d+)([eE][+-]?[0-9]+)?j?', Number.Float),
            (r'\d+[eE][+-]?[0-9]+j?', Number.Float),
            (r'0[0-7]+j?', Number.Oct),
            (r'0[bB][01]+', Number.Bin),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (r'\d+L', Number.Integer.Long),
            (r'\d+j?', Number.Integer)
        ],
        'backtick': [
            ('`.*?`', String.Backtick),
        ],
        'name': [
            (r'@[\w.]+', Name.Decorator),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'funcname': [
            include('magicfuncs'),
            (r'[a-zA-Z_]\w*', Name.Function, '#pop'),
            default('#pop'),
        ],
        'classname': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'(?:[ \t]|\\\n)+', Text),
            (r'as\b', Keyword.Namespace),
            (r',', Operator),
            (r'[a-zA-Z_][\w.]*', Name.Namespace),
            default('#pop')  # all else: go back
        ],
        'fromimport': [
            (r'(?:[ \t]|\\\n)+', Text),
            (r'import\b', Keyword.Namespace, '#pop'),
            # if None occurs here, it's "raise x from None", since None can
            # never be a module name
            (r'None\b', Name.Builtin.Pseudo, '#pop'),
            # sadly, in "raise x from y" y will be highlighted as namespace too
            (r'[a-zA-Z_.][\w.]*', Name.Namespace),
            # anything else here also means "raise x from y" and is therefore
            # not an error
            default('#pop'),
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'strings-single': innerstring_rules(String.Single),
        'strings-double': innerstring_rules(String.Double),
        'dqs': [
            (r'"', String.Double, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include('strings-double')
        ],
        'sqs': [
            (r"'", String.Single, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include('strings-single')
        ],
        'tdqs': [
            (r'"""', String.Double, '#pop'),
            include('strings-double'),
            (r'\n', String.Double)
        ],
        'tsqs': [
            (r"'''", String.Single, '#pop'),
            include('strings-single'),
            (r'\n', String.Single)
        ],
    }

    def analyse_text(text):
        return shebang_matches(text, r'pythonw?2(\.\d)?')

class _PythonConsoleLexerBase(RegexLexer):
    name = 'Python console session'
    aliases = ['pycon', 'python-console']
    mimetypes = ['text/x-python-doctest']

    """Auxiliary lexer for `PythonConsoleLexer`.

    Code tokens are output as ``Token.Other.Code``, traceback tokens as
    ``Token.Other.Traceback``.
    """
    tokens = {
        'root': [
            (r'(>>> )(.*\n)', bygroups(Generic.Prompt, Other.Code), 'continuations'),
            # This happens, e.g., when tracebacks are embedded in documentation;
            # trailing whitespaces are often stripped in such contexts.
            (r'(>>>)(\n)', bygroups(Generic.Prompt, Whitespace)),
            (r'(\^C)?Traceback \(most recent call last\):\n', Other.Traceback, 'traceback'),
            # SyntaxError starts with this
            (r'  File "[^"]+", line \d+', Other.Traceback, 'traceback'),
            (r'.*\n', Generic.Output),
        ],
        'continuations': [
            (r'(\.\.\. )(.*\n)', bygroups(Generic.Prompt, Other.Code)),
            # See above.
            (r'(\.\.\.)(\n)', bygroups(Generic.Prompt, Whitespace)),
            default('#pop'),
        ],
        'traceback': [
            # As soon as we see a traceback, consume everything until the next
            # >>> prompt.
            (r'(?=>>>( |$))', Text, '#pop'),
            (r'(KeyboardInterrupt)(\n)', bygroups(Name.Class, Whitespace)),
            (r'.*\n', Other.Traceback),
        ],
    }

class PythonConsoleLexer(DelegatingLexer):
    """
    For Python console output or doctests, such as:

    .. sourcecode:: pycon

        >>> a = 'foo'
        >>> print(a)
        foo
        >>> 1 / 0
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        ZeroDivisionError: integer division or modulo by zero

    Additional options:

    `python3`
        Use Python 3 lexer for code.  Default is ``True``.

        .. versionadded:: 1.0
        .. versionchanged:: 2.5
           Now defaults to ``True``.
    """

    name = 'Python console session'
    aliases = ['pycon', 'python-console']
    mimetypes = ['text/x-python-doctest']
    url = 'https://python.org'
    version_added = ''

    def __init__(self, **options):
        python3 = get_bool_opt(options, 'python3', True)
        if python3:
            pylexer = PythonLexer
            tblexer = PythonTracebackLexer
        else:
            pylexer = Python2Lexer
            tblexer = Python2TracebackLexer
        # We have two auxiliary lexers. Use DelegatingLexer twice with
        # different tokens.  TODO: DelegatingLexer should support this
        # directly, by accepting a tuplet of auxiliary lexers and a tuple of
        # distinguishing tokens. Then we wouldn't need this intermediary
        # class.
        class _ReplaceInnerCode(DelegatingLexer):
            def __init__(self, **options):
                super().__init__(pylexer, _PythonConsoleLexerBase, Other.Code, **options)
        super().__init__(tblexer, _ReplaceInnerCode, Other.Traceback, **options)

class PythonTracebackLexer(RegexLexer):
    """
    For Python 3.x tracebacks, with support for chained exceptions.

    .. versionchanged:: 2.5
       This is now the default ``PythonTracebackLexer``.  It is still available
       as the alias ``Python3TracebackLexer``.
    """

    name = 'Python Traceback'
    aliases = ['pytb', 'py3tb']
    filenames = ['*.pytb', '*.py3tb']
    mimetypes = ['text/x-python-traceback', 'text/x-python3-traceback']
    url = 'https://python.org'
    version_added = '1.0'

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'^(\^C)?Traceback \(most recent call last\):\n', Generic.Traceback, 'intb'),
            (r'^During handling of the above exception, another '
             r'exception occurred:\n\n', Generic.Traceback),
            (r'^The above exception was the direct cause of the '
             r'following exception:\n\n', Generic.Traceback),
            (r'^(?=  File "[^"]+", line \d+)', Generic.Traceback, 'intb'),
            (r'^.*\n', Other),
        ],
        'intb': [
            (r'^(  File )("[^"]+")(, line )(\d+)(, in )(.+)(\n)',
             bygroups(Text, Name.Builtin, Text, Number, Text, Name, Whitespace)),
            (r'^(  File )("[^"]+")(, line )(\d+)(\n)',
             bygroups(Text, Name.Builtin, Text, Number, Whitespace)),
            (r'^(    )(.+)(\n)',
             bygroups(Whitespace, using(PythonLexer), Whitespace), 'markers'),
            (r'^([ \t]*)(\.\.\.)(\n)',
             bygroups(Whitespace, Comment, Whitespace)),  # for doctests...
            (r'^([^:]+)(: )(.+)(\n)',
             bygroups(Generic.Error, Text, Name, Whitespace), '#pop'),
            (r'^([a-zA-Z_][\w.]*)(:?\n)',
             bygroups(Generic.Error, Whitespace), '#pop'),
            default('#pop'),
        ],
        'markers': [
            # Either `PEP 657 <https://www.python.org/dev/peps/pep-0657/>`
            # error locations in Python 3.11+, or single-caret markers
            # for syntax errors before that.
            (r'^( {4,})([~^]+)(\n)',
             bygroups(Whitespace, Punctuation.Marker, Whitespace),
             '#pop'),
            default('#pop'),
        ],
    }


Python3TracebackLexer = PythonTracebackLexer


class Python2TracebackLexer(RegexLexer):
    """
    For Python tracebacks.

    .. versionchanged:: 2.5
       This class has been renamed from ``PythonTracebackLexer``.
       ``PythonTracebackLexer`` now refers to the Python 3 variant.
    """

    name = 'Python 2.x Traceback'
    aliases = ['py2tb']
    filenames = ['*.py2tb']
    mimetypes = ['text/x-python2-traceback']
    url = 'https://python.org'
    version_added = '0.7'

    tokens = {
        'root': [
            # Cover both (most recent call last) and (innermost last)
            # The optional ^C allows us to catch keyboard interrupt signals.
            (r'^(\^C)?(Traceback.*\n)',
             bygroups(Text, Generic.Traceback), 'intb'),
            # SyntaxError starts with this.
            (r'^(?=  File "[^"]+", line \d+)', Generic.Traceback, 'intb'),
            (r'^.*\n', Other),
        ],
        'intb': [
            (r'^(  File )("[^"]+")(, line )(\d+)(, in )(.+)(\n)',
             bygroups(Text, Name.Builtin, Text, Number, Text, Name, Whitespace)),
            (r'^(  File )("[^"]+")(, line )(\d+)(\n)',
             bygroups(Text, Name.Builtin, Text, Number, Whitespace)),
            (r'^(    )(.+)(\n)',
             bygroups(Text, using(Python2Lexer), Whitespace), 'marker'),
            (r'^([ \t]*)(\.\.\.)(\n)',
             bygroups(Text, Comment, Whitespace)),  # for doctests...
            (r'^([^:]+)(: )(.+)(\n)',
             bygroups(Generic.Error, Text, Name, Whitespace), '#pop'),
            (r'^([a-zA-Z_]\w*)(:?\n)',
             bygroups(Generic.Error, Whitespace), '#pop')
        ],
        'marker': [
            # For syntax errors.
            (r'( {4,})(\^)', bygroups(Text, Punctuation.Marker), '#pop'),
            default('#pop'),
        ],
    }


class CythonLexer(RegexLexer):
    """
    For Pyrex and Cython source code.
    """

    name = 'Cython'
    url = 'https://cython.org'
    aliases = ['cython', 'pyx', 'pyrex']
    filenames = ['*.pyx', '*.pxd', '*.pxi']
    mimetypes = ['text/x-cython', 'application/x-cython']
    version_added = '1.1'

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'^(\s*)("""(?:.|\n)*?""")', bygroups(Whitespace, String.Doc)),
            (r"^(\s*)('''(?:.|\n)*?''')", bygroups(Whitespace, String.Doc)),
            (r'[^\S\n]+', Text),
            (r'#.*$', Comment),
            (r'[]{}:(),;[]', Punctuation),
            (r'\\\n', Whitespace),
            (r'\\', Text),
            (r'(in|is|and|or|not)\b', Operator.Word),
            (r'(<)([a-zA-Z0-9.?]+)(>)',
             bygroups(Punctuation, Keyword.Type, Punctuation)),
            (r'!=|==|<<|>>|[-~+/*%=<>&^|.?]', Operator),
            (r'(from)(\d+)(<=)(\s+)(<)(\d+)(:)',
             bygroups(Keyword, Number.Integer, Operator, Name, Operator,
                      Name, Punctuation)),
            include('keywords'),
            (r'(def|property)(\s+)', bygroups(Keyword, Text), 'funcname'),
            (r'(cp?def)(\s+)', bygroups(Keyword, Text), 'cdef'),
            # (should actually start a block with only cdefs)
            (r'(cdef)(:)', bygroups(Keyword, Punctuation)),
            (r'(class|struct)(\s+)', bygroups(Keyword, Text), 'classname'),
            (r'(from)(\s+)', bygroups(Keyword, Text), 'fromimport'),
            (r'(c?import)(\s+)', bygroups(Keyword, Text), 'import'),
            include('builtins'),
            include('backtick'),
            ('(?:[rR]|[uU][rR]|[rR][uU])"""', String, 'tdqs'),
            ("(?:[rR]|[uU][rR]|[rR][uU])'''", String, 'tsqs'),
            ('(?:[rR]|[uU][rR]|[rR][uU])"', String, 'dqs'),
            ("(?:[rR]|[uU][rR]|[rR][uU])'", String, 'sqs'),
            ('[uU]?"""', String, combined('stringescape', 'tdqs')),
            ("[uU]?'''", String, combined('stringescape', 'tsqs')),
            ('[uU]?"', String, combined('stringescape', 'dqs')),
            ("[uU]?'", String, combined('stringescape', 'sqs')),
            include('name'),
            include('numbers'),
        ],
        'keywords': [
            (words((
                'assert', 'async', 'await', 'break', 'by', 'continue', 'ctypedef', 'del', 'elif',
                'else', 'except', 'except?', 'exec', 'finally', 'for', 'fused', 'gil',
                'global', 'if', 'include', 'lambda', 'nogil', 'pass', 'print',
                'raise', 'return', 'try', 'while', 'yield', 'as', 'with'), suffix=r'\b'),
             Keyword),
            (r'(DEF|IF|ELIF|ELSE)\b', Comment.Preproc),
        ],
        'builtins': [
            (words((
                '__import__', 'abs', 'all', 'any', 'apply', 'basestring', 'bin', 'bint',
                'bool', 'buffer', 'bytearray', 'bytes', 'callable', 'chr',
                'classmethod', 'cmp', 'coerce', 'compile', 'complex', 'delattr',
                'dict', 'dir', 'divmod', 'enumerate', 'eval', 'execfile', 'exit',
                'file', 'filter', 'float', 'frozenset', 'getattr', 'globals',
                'hasattr', 'hash', 'hex', 'id', 'input', 'int', 'intern', 'isinstance',
                'issubclass', 'iter', 'len', 'list', 'locals', 'long', 'map', 'max',
                'min', 'next', 'object', 'oct', 'open', 'ord', 'pow', 'property', 'Py_ssize_t',
                'range', 'raw_input', 'reduce', 'reload', 'repr', 'reversed',
                'round', 'set', 'setattr', 'slice', 'sorted', 'staticmethod',
                'str', 'sum', 'super', 'tuple', 'type', 'unichr', 'unicode', 'unsigned',
                'vars', 'xrange', 'zip'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Builtin),
            (r'(?<!\.)(self|None|Ellipsis|NotImplemented|False|True|NULL'
             r')\b', Name.Builtin.Pseudo),
            (words((
                'ArithmeticError', 'AssertionError', 'AttributeError',
                'BaseException', 'DeprecationWarning', 'EOFError', 'EnvironmentError',
                'Exception', 'FloatingPointError', 'FutureWarning', 'GeneratorExit',
                'IOError', 'ImportError', 'ImportWarning', 'IndentationError',
                'IndexError', 'KeyError', 'KeyboardInterrupt', 'LookupError',
                'MemoryError', 'NameError', 'NotImplemented', 'NotImplementedError',
                'OSError', 'OverflowError', 'OverflowWarning',
                'PendingDeprecationWarning', 'ReferenceError', 'RuntimeError',
                'RuntimeWarning', 'StandardError', 'StopIteration', 'SyntaxError',
                'SyntaxWarning', 'SystemError', 'SystemExit', 'TabError',
                'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
                'UnicodeEncodeError', 'UnicodeError', 'UnicodeTranslateError',
                'UnicodeWarning', 'UserWarning', 'ValueError', 'Warning',
                'ZeroDivisionError'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Exception),
        ],
        'numbers': [
            (r'(\d+\.?\d*|\d*\.\d+)([eE][+-]?[0-9]+)?', Number.Float),
            (r'0\d+', Number.Oct),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (r'\d+L', Number.Integer.Long),
            (r'\d+', Number.Integer)
        ],
        'backtick': [
            ('`.*?`', String.Backtick),
        ],
        'name': [
            (r'@\w+', Name.Decorator),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'funcname': [
            (r'[a-zA-Z_]\w*', Name.Function, '#pop')
        ],
        'cdef': [
            (r'(public|readonly|extern|api|inline)\b', Keyword.Reserved),
            (r'(struct|enum|union|class)\b', Keyword),
            (r'([a-zA-Z_]\w*)(\s*)(?=[(:#=]|$)',
             bygroups(Name.Function, Text), '#pop'),
            (r'([a-zA-Z_]\w*)(\s*)(,)',
             bygroups(Name.Function, Text, Punctuation)),
            (r'from\b', Keyword, '#pop'),
            (r'as\b', Keyword),
            (r':', Punctuation, '#pop'),
            (r'(?=["\'])', Text, '#pop'),
            (r'[a-zA-Z_]\w*', Keyword.Type),
            (r'.', Text),
        ],
        'classname': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'(\s+)(as)(\s+)', bygroups(Text, Keyword, Text)),
            (r'[a-zA-Z_][\w.]*', Name.Namespace),
            (r'(\s*)(,)(\s*)', bygroups(Text, Operator, Text)),
            default('#pop')  # all else: go back
        ],
        'fromimport': [
            (r'(\s+)(c?import)\b', bygroups(Text, Keyword), '#pop'),
            (r'[a-zA-Z_.][\w.]*', Name.Namespace),
            # ``cdef foo from "header"``, or ``for foo from 0 < i < 10``
            default('#pop'),
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'strings': [
            (r'%(\([a-zA-Z0-9]+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsux%]', String.Interpol),
            (r'[^\\\'"%\n]+', String),
            # quotes, percents and backslashes must be parsed one at a time
            (r'[\'"\\]', String),
            # unhandled string formatting sign
            (r'%', String)
            # newlines are an error (use "nl" state)
        ],
        'nl': [
            (r'\n', String)
        ],
        'dqs': [
            (r'"', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here again for raw strings
            include('strings')
        ],
        'sqs': [
            (r"'", String, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here again for raw strings
            include('strings')
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            include('strings'),
            include('nl')
        ],
        'tsqs': [
            (r"'''", String, '#pop'),
            include('strings'),
            include('nl')
        ],
    }


class DgLexer(RegexLexer):
    """
    Lexer for dg,
    a functional and object-oriented programming language
    running on the CPython 3 VM.
    """
    name = 'dg'
    aliases = ['dg']
    filenames = ['*.dg']
    mimetypes = ['text/x-dg']
    url = 'http://pyos.github.io/dg'
    version_added = '1.6'

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'#.*?$', Comment.Single),

            (r'(?i)0b[01]+', Number.Bin),
            (r'(?i)0o[0-7]+', Number.Oct),
            (r'(?i)0x[0-9a-f]+', Number.Hex),
            (r'(?i)[+-]?[0-9]+\.[0-9]+(e[+-]?[0-9]+)?j?', Number.Float),
            (r'(?i)[+-]?[0-9]+e[+-]?\d+j?', Number.Float),
            (r'(?i)[+-]?[0-9]+j?', Number.Integer),

            (r"(?i)(br|r?b?)'''", String, combined('stringescape', 'tsqs', 'string')),
            (r'(?i)(br|r?b?)"""', String, combined('stringescape', 'tdqs', 'string')),
            (r"(?i)(br|r?b?)'", String, combined('stringescape', 'sqs', 'string')),
            (r'(?i)(br|r?b?)"', String, combined('stringescape', 'dqs', 'string')),

            (r"`\w+'*`", Operator),
            (r'\b(and|in|is|or|where)\b', Operator.Word),
            (r'[!$%&*+\-./:<-@\\^|~;,]+', Operator),

            (words((
                'bool', 'bytearray', 'bytes', 'classmethod', 'complex', 'dict', 'dict\'',
                'float', 'frozenset', 'int', 'list', 'list\'', 'memoryview', 'object',
                'property', 'range', 'set', 'set\'', 'slice', 'staticmethod', 'str',
                'super', 'tuple', 'tuple\'', 'type'),
                   prefix=r'(?<!\.)', suffix=r'(?![\'\w])'),
             Name.Builtin),
            (words((
                '__import__', 'abs', 'all', 'any', 'bin', 'bind', 'chr', 'cmp', 'compile',
                'complex', 'delattr', 'dir', 'divmod', 'drop', 'dropwhile', 'enumerate',
                'eval', 'exhaust', 'filter', 'flip', 'foldl1?', 'format', 'fst',
                'getattr', 'globals', 'hasattr', 'hash', 'head', 'hex', 'id', 'init',
                'input', 'isinstance', 'issubclass', 'iter', 'iterate', 'last', 'len',
                'locals', 'map', 'max', 'min', 'next', 'oct', 'open', 'ord', 'pow',
                'print', 'repr', 'reversed', 'round', 'setattr', 'scanl1?', 'snd',
                'sorted', 'sum', 'tail', 'take', 'takewhile', 'vars', 'zip'),
                   prefix=r'(?<!\.)', suffix=r'(?![\'\w])'),
             Name.Builtin),
            (r"(?<!\.)(self|Ellipsis|NotImplemented|None|True|False)(?!['\w])",
             Name.Builtin.Pseudo),

            (r"(?<!\.)[A-Z]\w*(Error|Exception|Warning)'*(?!['\w])",
             Name.Exception),
            (r"(?<!\.)(Exception|GeneratorExit|KeyboardInterrupt|StopIteration|"
             r"SystemExit)(?!['\w])", Name.Exception),

            (r"(?<![\w.])(except|finally|for|if|import|not|otherwise|raise|"
             r"subclass|while|with|yield)(?!['\w])", Keyword.Reserved),

            (r"[A-Z_]+'*(?!['\w])", Name),
            (r"[A-Z]\w+'*(?!['\w])", Keyword.Type),
            (r"\w+'*", Name),

            (r'[()]', Punctuation),
            (r'.', Error),
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'string': [
            (r'%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsux%]', String.Interpol),
            (r'[^\\\'"%\n]+', String),
            # quotes, percents and backslashes must be parsed one at a time
            (r'[\'"\\]', String),
            # unhandled string formatting sign
            (r'%', String),
            (r'\n', String)
        ],
        'dqs': [
            (r'"', String, '#pop')
        ],
        'sqs': [
            (r"'", String, '#pop')
        ],
        'tdqs': [
            (r'"""', String, '#pop')
        ],
        'tsqs': [
            (r"'''", String, '#pop')
        ],
    }


class NumPyLexer(PythonLexer):
    """
    A Python lexer recognizing Numerical Python builtins.
    """

    name = 'NumPy'
    url = 'https://numpy.org/'
    aliases = ['numpy']
    version_added = '0.10'

    # override the mimetypes to not inherit them from python
    mimetypes = []
    filenames = []

    EXTRA_KEYWORDS = {
        'abs', 'absolute', 'accumulate', 'add', 'alen', 'all', 'allclose',
        'alltrue', 'alterdot', 'amax', 'amin', 'angle', 'any', 'append',
        'apply_along_axis', 'apply_over_axes', 'arange', 'arccos', 'arccosh',
        'arcsin', 'arcsinh', 'arctan', 'arctan2', 'arctanh', 'argmax', 'argmin',
        'argsort', 'argwhere', 'around', 'array', 'array2string', 'array_equal',
        'array_equiv', 'array_repr', 'array_split', 'array_str', 'arrayrange',
        'asanyarray', 'asarray', 'asarray_chkfinite', 'ascontiguousarray',
        'asfarray', 'asfortranarray', 'asmatrix', 'asscalar', 'astype',
        'atleast_1d', 'atleast_2d', 'atleast_3d', 'average', 'bartlett',
        'base_repr', 'beta', 'binary_repr', 'bincount', 'binomial',
        'bitwise_and', 'bitwise_not', 'bitwise_or', 'bitwise_xor', 'blackman',
        'bmat', 'broadcast', 'byte_bounds', 'bytes', 'byteswap', 'c_',
        'can_cast', 'ceil', 'choose', 'clip', 'column_stack', 'common_type',
        'compare_chararrays', 'compress', 'concatenate', 'conj', 'conjugate',
        'convolve', 'copy', 'corrcoef', 'correlate', 'cos', 'cosh', 'cov',
        'cross', 'cumprod', 'cumproduct', 'cumsum', 'delete', 'deprecate',
        'diag', 'diagflat', 'diagonal', 'diff', 'digitize', 'disp', 'divide',
        'dot', 'dsplit', 'dstack', 'dtype', 'dump', 'dumps', 'ediff1d', 'empty',
        'empty_like', 'equal', 'exp', 'expand_dims', 'expm1', 'extract', 'eye',
        'fabs', 'fastCopyAndTranspose', 'fft', 'fftfreq', 'fftshift', 'fill',
        'finfo', 'fix', 'flat', 'flatnonzero', 'flatten', 'fliplr', 'flipud',
        'floor', 'floor_divide', 'fmod', 'frexp', 'fromarrays', 'frombuffer',
        'fromfile', 'fromfunction', 'fromiter', 'frompyfunc', 'fromstring',
        'generic', 'get_array_wrap', 'get_include', 'get_numarray_include',
        'get_numpy_include', 'get_printoptions', 'getbuffer', 'getbufsize',
        'geterr', 'geterrcall', 'geterrobj', 'getfield', 'gradient', 'greater',
        'greater_equal', 'gumbel', 'hamming', 'hanning', 'histogram',
        'histogram2d', 'histogramdd', 'hsplit', 'hstack', 'hypot', 'i0',
        'identity', 'ifft', 'imag', 'index_exp', 'indices', 'inf', 'info',
        'inner', 'insert', 'int_asbuffer', 'interp', 'intersect1d',
        'intersect1d_nu', 'inv', 'invert', 'iscomplex', 'iscomplexobj',
        'isfinite', 'isfortran', 'isinf', 'isnan', 'isneginf', 'isposinf',
        'isreal', 'isrealobj', 'isscalar', 'issctype', 'issubclass_',
        'issubdtype', 'issubsctype', 'item', 'itemset', 'iterable', 'ix_',
        'kaiser', 'kron', 'ldexp', 'left_shift', 'less', 'less_equal', 'lexsort',
        'linspace', 'load', 'loads', 'loadtxt', 'log', 'log10', 'log1p', 'log2',
        'logical_and', 'logical_not', 'logical_or', 'logical_xor', 'logspace',
        'lstsq', 'mat', 'matrix', 'max', 'maximum', 'maximum_sctype',
        'may_share_memory', 'mean', 'median', 'meshgrid', 'mgrid', 'min',
        'minimum', 'mintypecode', 'mod', 'modf', 'msort', 'multiply', 'nan',
        'nan_to_num', 'nanargmax', 'nanargmin', 'nanmax', 'nanmin', 'nansum',
        'ndenumerate', 'ndim', 'ndindex', 'negative', 'newaxis', 'newbuffer',
        'newbyteorder', 'nonzero', 'not_equal', 'obj2sctype', 'ogrid', 'ones',
        'ones_like', 'outer', 'permutation', 'piecewise', 'pinv', 'pkgload',
        'place', 'poisson', 'poly', 'poly1d', 'polyadd', 'polyder', 'polydiv',
        'polyfit', 'polyint', 'polymul', 'polysub', 'polyval', 'power', 'prod',
        'product', 'ptp', 'put', 'putmask', 'r_', 'randint', 'random_integers',
        'random_sample', 'ranf', 'rank', 'ravel', 'real', 'real_if_close',
        'recarray', 'reciprocal', 'reduce', 'remainder', 'repeat', 'require',
        'reshape', 'resize', 'restoredot', 'right_shift', 'rint', 'roll',
        'rollaxis', 'roots', 'rot90', 'round', 'round_', 'row_stack', 's_',
        'sample', 'savetxt', 'sctype2char', 'searchsorted', 'seed', 'select',
        'set_numeric_ops', 'set_printoptions', 'set_string_function',
        'setbufsize', 'setdiff1d', 'seterr', 'seterrcall', 'seterrobj',
        'setfield', 'setflags', 'setmember1d', 'setxor1d', 'shape',
        'show_config', 'shuffle', 'sign', 'signbit', 'sin', 'sinc', 'sinh',
        'size', 'slice', 'solve', 'sometrue', 'sort', 'sort_complex', 'source',
        'split', 'sqrt', 'square', 'squeeze', 'standard_normal', 'std',
        'subtract', 'sum', 'svd', 'swapaxes', 'take', 'tan', 'tanh', 'tensordot',
        'test', 'tile', 'tofile', 'tolist', 'tostring', 'trace', 'transpose',
        'trapz', 'tri', 'tril', 'trim_zeros', 'triu', 'true_divide', 'typeDict',
        'typename', 'uniform', 'union1d', 'unique', 'unique1d', 'unravel_index',
        'unwrap', 'vander', 'var', 'vdot', 'vectorize', 'view', 'vonmises',
        'vsplit', 'vstack', 'weibull', 'where', 'who', 'zeros', 'zeros_like'
    }

    def get_tokens_unprocessed(self, text):
        for index, token, value in \
                PythonLexer.get_tokens_unprocessed(self, text):
            if token is Name and value in self.EXTRA_KEYWORDS:
                yield index, Keyword.Pseudo, value
            else:
                yield index, token, value

    def analyse_text(text):
        ltext = text[:1000]
        return (shebang_matches(text, r'pythonw?(3(\.\d)?)?') or
                'import ' in ltext) \
            and ('import numpy' in ltext or 'from numpy import' in ltext)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\emulation.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Emulation
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import network
from . import page


@dataclass
class ScreenOrientation:
    '''
    Screen orientation.
    '''
    #: Orientation type.
    type_: str

    #: Orientation angle.
    angle: int

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['angle'] = self.angle
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            angle=int(json['angle']),
        )


@dataclass
class DisplayFeature:
    #: Orientation of a display feature in relation to screen
    orientation: str

    #: The offset from the screen origin in either the x (for vertical
    #: orientation) or y (for horizontal orientation) direction.
    offset: int

    #: A display feature may mask content such that it is not physically
    #: displayed - this length along with the offset describes this area.
    #: A display feature that only splits content will have a 0 mask_length.
    mask_length: int

    def to_json(self):
        json = dict()
        json['orientation'] = self.orientation
        json['offset'] = self.offset
        json['maskLength'] = self.mask_length
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            orientation=str(json['orientation']),
            offset=int(json['offset']),
            mask_length=int(json['maskLength']),
        )


@dataclass
class DevicePosture:
    #: Current posture of the device
    type_: str

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
        )


@dataclass
class MediaFeature:
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


class VirtualTimePolicy(enum.Enum):
    '''
    advance: If the scheduler runs out of immediate work, the virtual time base may fast forward to
    allow the next delayed task (if any) to run; pause: The virtual time base may not advance;
    pauseIfNetworkFetchesPending: The virtual time base may not advance if there are any pending
    resource fetches.
    '''
    ADVANCE = "advance"
    PAUSE = "pause"
    PAUSE_IF_NETWORK_FETCHES_PENDING = "pauseIfNetworkFetchesPending"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class UserAgentBrandVersion:
    '''
    Used to specify User Agent Client Hints to emulate. See https://wicg.github.io/ua-client-hints
    '''
    brand: str

    version: str

    def to_json(self):
        json = dict()
        json['brand'] = self.brand
        json['version'] = self.version
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            brand=str(json['brand']),
            version=str(json['version']),
        )


@dataclass
class UserAgentMetadata:
    '''
    Used to specify User Agent Client Hints to emulate. See https://wicg.github.io/ua-client-hints
    Missing optional values will be filled in by the target with what it would normally use.
    '''
    platform: str

    platform_version: str

    architecture: str

    model: str

    mobile: bool

    #: Brands appearing in Sec-CH-UA.
    brands: typing.Optional[typing.List[UserAgentBrandVersion]] = None

    #: Brands appearing in Sec-CH-UA-Full-Version-List.
    full_version_list: typing.Optional[typing.List[UserAgentBrandVersion]] = None

    full_version: typing.Optional[str] = None

    bitness: typing.Optional[str] = None

    wow64: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['platform'] = self.platform
        json['platformVersion'] = self.platform_version
        json['architecture'] = self.architecture
        json['model'] = self.model
        json['mobile'] = self.mobile
        if self.brands is not None:
            json['brands'] = [i.to_json() for i in self.brands]
        if self.full_version_list is not None:
            json['fullVersionList'] = [i.to_json() for i in self.full_version_list]
        if self.full_version is not None:
            json['fullVersion'] = self.full_version
        if self.bitness is not None:
            json['bitness'] = self.bitness
        if self.wow64 is not None:
            json['wow64'] = self.wow64
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            platform=str(json['platform']),
            platform_version=str(json['platformVersion']),
            architecture=str(json['architecture']),
            model=str(json['model']),
            mobile=bool(json['mobile']),
            brands=[UserAgentBrandVersion.from_json(i) for i in json['brands']] if 'brands' in json else None,
            full_version_list=[UserAgentBrandVersion.from_json(i) for i in json['fullVersionList']] if 'fullVersionList' in json else None,
            full_version=str(json['fullVersion']) if 'fullVersion' in json else None,
            bitness=str(json['bitness']) if 'bitness' in json else None,
            wow64=bool(json['wow64']) if 'wow64' in json else None,
        )


class SensorType(enum.Enum):
    '''
    Used to specify sensor types to emulate.
    See https://w3c.github.io/sensors/#automation for more information.
    '''
    ABSOLUTE_ORIENTATION = "absolute-orientation"
    ACCELEROMETER = "accelerometer"
    AMBIENT_LIGHT = "ambient-light"
    GRAVITY = "gravity"
    GYROSCOPE = "gyroscope"
    LINEAR_ACCELERATION = "linear-acceleration"
    MAGNETOMETER = "magnetometer"
    RELATIVE_ORIENTATION = "relative-orientation"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SensorMetadata:
    available: typing.Optional[bool] = None

    minimum_frequency: typing.Optional[float] = None

    maximum_frequency: typing.Optional[float] = None

    def to_json(self):
        json = dict()
        if self.available is not None:
            json['available'] = self.available
        if self.minimum_frequency is not None:
            json['minimumFrequency'] = self.minimum_frequency
        if self.maximum_frequency is not None:
            json['maximumFrequency'] = self.maximum_frequency
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            available=bool(json['available']) if 'available' in json else None,
            minimum_frequency=float(json['minimumFrequency']) if 'minimumFrequency' in json else None,
            maximum_frequency=float(json['maximumFrequency']) if 'maximumFrequency' in json else None,
        )


@dataclass
class SensorReadingSingle:
    value: float

    def to_json(self):
        json = dict()
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=float(json['value']),
        )


@dataclass
class SensorReadingXYZ:
    x: float

    y: float

    z: float

    def to_json(self):
        json = dict()
        json['x'] = self.x
        json['y'] = self.y
        json['z'] = self.z
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            x=float(json['x']),
            y=float(json['y']),
            z=float(json['z']),
        )


@dataclass
class SensorReadingQuaternion:
    x: float

    y: float

    z: float

    w: float

    def to_json(self):
        json = dict()
        json['x'] = self.x
        json['y'] = self.y
        json['z'] = self.z
        json['w'] = self.w
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            x=float(json['x']),
            y=float(json['y']),
            z=float(json['z']),
            w=float(json['w']),
        )


@dataclass
class SensorReading:
    single: typing.Optional[SensorReadingSingle] = None

    xyz: typing.Optional[SensorReadingXYZ] = None

    quaternion: typing.Optional[SensorReadingQuaternion] = None

    def to_json(self):
        json = dict()
        if self.single is not None:
            json['single'] = self.single.to_json()
        if self.xyz is not None:
            json['xyz'] = self.xyz.to_json()
        if self.quaternion is not None:
            json['quaternion'] = self.quaternion.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            single=SensorReadingSingle.from_json(json['single']) if 'single' in json else None,
            xyz=SensorReadingXYZ.from_json(json['xyz']) if 'xyz' in json else None,
            quaternion=SensorReadingQuaternion.from_json(json['quaternion']) if 'quaternion' in json else None,
        )


class PressureSource(enum.Enum):
    CPU = "cpu"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PressureState(enum.Enum):
    NOMINAL = "nominal"
    FAIR = "fair"
    SERIOUS = "serious"
    CRITICAL = "critical"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PressureMetadata:
    available: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        if self.available is not None:
            json['available'] = self.available
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            available=bool(json['available']) if 'available' in json else None,
        )


class DisabledImageType(enum.Enum):
    '''
    Enum of image types that can be disabled.
    '''
    AVIF = "avif"
    WEBP = "webp"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def can_emulate() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Tells whether emulation is supported.

    :returns: True if emulation is supported.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.canEmulate',
    }
    json = yield cmd_dict
    return bool(json['result'])


def clear_device_metrics_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears the overridden device metrics.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.clearDeviceMetricsOverride',
    }
    json = yield cmd_dict


def clear_geolocation_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears the overridden Geolocation Position and Error.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.clearGeolocationOverride',
    }
    json = yield cmd_dict


def reset_page_scale_factor() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Requests that page scale factor is reset to initial values.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.resetPageScaleFactor',
    }
    json = yield cmd_dict


def set_focus_emulation_enabled(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables or disables simulating a focused and active page.

    **EXPERIMENTAL**

    :param enabled: Whether to enable to disable focus emulation.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setFocusEmulationEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_auto_dark_mode_override(
        enabled: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Automatically render all web contents using a dark theme.

    **EXPERIMENTAL**

    :param enabled: *(Optional)* Whether to enable or disable automatic dark mode. If not specified, any existing override will be cleared.
    '''
    params: T_JSON_DICT = dict()
    if enabled is not None:
        params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setAutoDarkModeOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_cpu_throttling_rate(
        rate: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables CPU throttling to emulate slow CPUs.

    :param rate: Throttling rate as a slowdown factor (1 is no throttle, 2 is 2x slowdown, etc).
    '''
    params: T_JSON_DICT = dict()
    params['rate'] = rate
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setCPUThrottlingRate',
        'params': params,
    }
    json = yield cmd_dict


def set_default_background_color_override(
        color: typing.Optional[dom.RGBA] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets or clears an override of the default background color of the frame. This override is used
    if the content does not specify one.

    :param color: *(Optional)* RGBA of the default background color. If not specified, any existing override will be cleared.
    '''
    params: T_JSON_DICT = dict()
    if color is not None:
        params['color'] = color.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setDefaultBackgroundColorOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_device_metrics_override(
        width: int,
        height: int,
        device_scale_factor: float,
        mobile: bool,
        scale: typing.Optional[float] = None,
        screen_width: typing.Optional[int] = None,
        screen_height: typing.Optional[int] = None,
        position_x: typing.Optional[int] = None,
        position_y: typing.Optional[int] = None,
        dont_set_visible_size: typing.Optional[bool] = None,
        screen_orientation: typing.Optional[ScreenOrientation] = None,
        viewport: typing.Optional[page.Viewport] = None,
        display_feature: typing.Optional[DisplayFeature] = None,
        device_posture: typing.Optional[DevicePosture] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides the values of device screen dimensions (window.screen.width, window.screen.height,
    window.innerWidth, window.innerHeight, and "device-width"/"device-height"-related CSS media
    query results).

    :param width: Overriding width value in pixels (minimum 0, maximum 10000000). 0 disables the override.
    :param height: Overriding height value in pixels (minimum 0, maximum 10000000). 0 disables the override.
    :param device_scale_factor: Overriding device scale factor value. 0 disables the override.
    :param mobile: Whether to emulate mobile device. This includes viewport meta tag, overlay scrollbars, text autosizing and more.
    :param scale: **(EXPERIMENTAL)** *(Optional)* Scale to apply to resulting view image.
    :param screen_width: **(EXPERIMENTAL)** *(Optional)* Overriding screen width value in pixels (minimum 0, maximum 10000000).
    :param screen_height: **(EXPERIMENTAL)** *(Optional)* Overriding screen height value in pixels (minimum 0, maximum 10000000).
    :param position_x: **(EXPERIMENTAL)** *(Optional)* Overriding view X position on screen in pixels (minimum 0, maximum 10000000).
    :param position_y: **(EXPERIMENTAL)** *(Optional)* Overriding view Y position on screen in pixels (minimum 0, maximum 10000000).
    :param dont_set_visible_size: **(EXPERIMENTAL)** *(Optional)* Do not set visible view size, rely upon explicit setVisibleSize call.
    :param screen_orientation: *(Optional)* Screen orientation override.
    :param viewport: **(EXPERIMENTAL)** *(Optional)* If set, the visible area of the page will be overridden to this viewport. This viewport change is not observed by the page, e.g. viewport-relative elements do not change positions.
    :param display_feature: **(EXPERIMENTAL)** *(Optional)* If set, the display feature of a multi-segment screen. If not set, multi-segment support is turned-off.
    :param device_posture: **(EXPERIMENTAL)** *(Optional)* If set, the posture of a foldable device. If not set the posture is set to continuous. Deprecated, use Emulation.setDevicePostureOverride.
    '''
    params: T_JSON_DICT = dict()
    params['width'] = width
    params['height'] = height
    params['deviceScaleFactor'] = device_scale_factor
    params['mobile'] = mobile
    if scale is not None:
        params['scale'] = scale
    if screen_width is not None:
        params['screenWidth'] = screen_width
    if screen_height is not None:
        params['screenHeight'] = screen_height
    if position_x is not None:
        params['positionX'] = position_x
    if position_y is not None:
        params['positionY'] = position_y
    if dont_set_visible_size is not None:
        params['dontSetVisibleSize'] = dont_set_visible_size
    if screen_orientation is not None:
        params['screenOrientation'] = screen_orientation.to_json()
    if viewport is not None:
        params['viewport'] = viewport.to_json()
    if display_feature is not None:
        params['displayFeature'] = display_feature.to_json()
    if device_posture is not None:
        params['devicePosture'] = device_posture.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setDeviceMetricsOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_device_posture_override(
        posture: DevicePosture
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Start reporting the given posture value to the Device Posture API.
    This override can also be set in setDeviceMetricsOverride().

    **EXPERIMENTAL**

    :param posture:
    '''
    params: T_JSON_DICT = dict()
    params['posture'] = posture.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setDevicePostureOverride',
        'params': params,
    }
    json = yield cmd_dict


def clear_device_posture_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears a device posture override set with either setDeviceMetricsOverride()
    or setDevicePostureOverride() and starts using posture information from the
    platform again.
    Does nothing if no override is set.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.clearDevicePostureOverride',
    }
    json = yield cmd_dict


def set_scrollbars_hidden(
        hidden: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param hidden: Whether scrollbars should be always hidden.
    '''
    params: T_JSON_DICT = dict()
    params['hidden'] = hidden
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setScrollbarsHidden',
        'params': params,
    }
    json = yield cmd_dict


def set_document_cookie_disabled(
        disabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param disabled: Whether document.coookie API should be disabled.
    '''
    params: T_JSON_DICT = dict()
    params['disabled'] = disabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setDocumentCookieDisabled',
        'params': params,
    }
    json = yield cmd_dict


def set_emit_touch_events_for_mouse(
        enabled: bool,
        configuration: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param enabled: Whether touch emulation based on mouse input should be enabled.
    :param configuration: *(Optional)* Touch/gesture events configuration. Default: current platform.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    if configuration is not None:
        params['configuration'] = configuration
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setEmitTouchEventsForMouse',
        'params': params,
    }
    json = yield cmd_dict


def set_emulated_media(
        media: typing.Optional[str] = None,
        features: typing.Optional[typing.List[MediaFeature]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Emulates the given media type or media feature for CSS media queries.

    :param media: *(Optional)* Media type to emulate. Empty string disables the override.
    :param features: *(Optional)* Media features to emulate.
    '''
    params: T_JSON_DICT = dict()
    if media is not None:
        params['media'] = media
    if features is not None:
        params['features'] = [i.to_json() for i in features]
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setEmulatedMedia',
        'params': params,
    }
    json = yield cmd_dict


def set_emulated_vision_deficiency(
        type_: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Emulates the given vision deficiency.

    :param type_: Vision deficiency to emulate. Order: best-effort emulations come first, followed by any physiologically accurate emulations for medically recognized color vision deficiencies.
    '''
    params: T_JSON_DICT = dict()
    params['type'] = type_
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setEmulatedVisionDeficiency',
        'params': params,
    }
    json = yield cmd_dict


def set_geolocation_override(
        latitude: typing.Optional[float] = None,
        longitude: typing.Optional[float] = None,
        accuracy: typing.Optional[float] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides the Geolocation Position or Error. Omitting any of the parameters emulates position
    unavailable.

    :param latitude: *(Optional)* Mock latitude
    :param longitude: *(Optional)* Mock longitude
    :param accuracy: *(Optional)* Mock accuracy
    '''
    params: T_JSON_DICT = dict()
    if latitude is not None:
        params['latitude'] = latitude
    if longitude is not None:
        params['longitude'] = longitude
    if accuracy is not None:
        params['accuracy'] = accuracy
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setGeolocationOverride',
        'params': params,
    }
    json = yield cmd_dict


def get_overridden_sensor_information(
        type_: SensorType
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''


    **EXPERIMENTAL**

    :param type_:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['type'] = type_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.getOverriddenSensorInformation',
        'params': params,
    }
    json = yield cmd_dict
    return float(json['requestedSamplingFrequency'])


def set_sensor_override_enabled(
        enabled: bool,
        type_: SensorType,
        metadata: typing.Optional[SensorMetadata] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides a platform sensor of a given type. If ``enabled`` is true, calls to
    Sensor.start() will use a virtual sensor as backend rather than fetching
    data from a real hardware sensor. Otherwise, existing virtual
    sensor-backend Sensor objects will fire an error event and new calls to
    Sensor.start() will attempt to use a real sensor instead.

    **EXPERIMENTAL**

    :param enabled:
    :param type_:
    :param metadata: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    params['type'] = type_.to_json()
    if metadata is not None:
        params['metadata'] = metadata.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setSensorOverrideEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_sensor_override_readings(
        type_: SensorType,
        reading: SensorReading
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Updates the sensor readings reported by a sensor type previously overridden
    by setSensorOverrideEnabled.

    **EXPERIMENTAL**

    :param type_:
    :param reading:
    '''
    params: T_JSON_DICT = dict()
    params['type'] = type_.to_json()
    params['reading'] = reading.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setSensorOverrideReadings',
        'params': params,
    }
    json = yield cmd_dict


def set_pressure_source_override_enabled(
        enabled: bool,
        source: PressureSource,
        metadata: typing.Optional[PressureMetadata] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides a pressure source of a given type, as used by the Compute
    Pressure API, so that updates to PressureObserver.observe() are provided
    via setPressureStateOverride instead of being retrieved from
    platform-provided telemetry data.

    **EXPERIMENTAL**

    :param enabled:
    :param source:
    :param metadata: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    params['source'] = source.to_json()
    if metadata is not None:
        params['metadata'] = metadata.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setPressureSourceOverrideEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_pressure_state_override(
        source: PressureSource,
        state: PressureState
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Provides a given pressure state that will be processed and eventually be
    delivered to PressureObserver users. ``source`` must have been previously
    overridden by setPressureSourceOverrideEnabled.

    **EXPERIMENTAL**

    :param source:
    :param state:
    '''
    params: T_JSON_DICT = dict()
    params['source'] = source.to_json()
    params['state'] = state.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setPressureStateOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_idle_override(
        is_user_active: bool,
        is_screen_unlocked: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides the Idle state.

    :param is_user_active: Mock isUserActive
    :param is_screen_unlocked: Mock isScreenUnlocked
    '''
    params: T_JSON_DICT = dict()
    params['isUserActive'] = is_user_active
    params['isScreenUnlocked'] = is_screen_unlocked
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setIdleOverride',
        'params': params,
    }
    json = yield cmd_dict


def clear_idle_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears Idle state overrides.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.clearIdleOverride',
    }
    json = yield cmd_dict


def set_navigator_overrides(
        platform: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides value returned by the javascript navigator object.

    **EXPERIMENTAL**

    :param platform: The platform navigator.platform should return.
    '''
    params: T_JSON_DICT = dict()
    params['platform'] = platform
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setNavigatorOverrides',
        'params': params,
    }
    json = yield cmd_dict


def set_page_scale_factor(
        page_scale_factor: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets a specified page scale factor.

    **EXPERIMENTAL**

    :param page_scale_factor: Page scale factor.
    '''
    params: T_JSON_DICT = dict()
    params['pageScaleFactor'] = page_scale_factor
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setPageScaleFactor',
        'params': params,
    }
    json = yield cmd_dict


def set_script_execution_disabled(
        value: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Switches script execution in the page.

    :param value: Whether script execution should be disabled in the page.
    '''
    params: T_JSON_DICT = dict()
    params['value'] = value
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setScriptExecutionDisabled',
        'params': params,
    }
    json = yield cmd_dict


def set_touch_emulation_enabled(
        enabled: bool,
        max_touch_points: typing.Optional[int] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables touch on platforms which do not support them.

    :param enabled: Whether the touch event emulation should be enabled.
    :param max_touch_points: *(Optional)* Maximum touch points supported. Defaults to one.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    if max_touch_points is not None:
        params['maxTouchPoints'] = max_touch_points
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setTouchEmulationEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_virtual_time_policy(
        policy: VirtualTimePolicy,
        budget: typing.Optional[float] = None,
        max_virtual_time_task_starvation_count: typing.Optional[int] = None,
        initial_virtual_time: typing.Optional[network.TimeSinceEpoch] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''
    Turns on virtual time for all frames (replacing real-time with a synthetic time source) and sets
    the current virtual time policy.  Note this supersedes any previous time budget.

    **EXPERIMENTAL**

    :param policy:
    :param budget: *(Optional)* If set, after this many virtual milliseconds have elapsed virtual time will be paused and a virtualTimeBudgetExpired event is sent.
    :param max_virtual_time_task_starvation_count: *(Optional)* If set this specifies the maximum number of tasks that can be run before virtual is forced forwards to prevent deadlock.
    :param initial_virtual_time: *(Optional)* If set, base::Time::Now will be overridden to initially return this value.
    :returns: Absolute timestamp at which virtual time was first enabled (up time in milliseconds).
    '''
    params: T_JSON_DICT = dict()
    params['policy'] = policy.to_json()
    if budget is not None:
        params['budget'] = budget
    if max_virtual_time_task_starvation_count is not None:
        params['maxVirtualTimeTaskStarvationCount'] = max_virtual_time_task_starvation_count
    if initial_virtual_time is not None:
        params['initialVirtualTime'] = initial_virtual_time.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setVirtualTimePolicy',
        'params': params,
    }
    json = yield cmd_dict
    return float(json['virtualTimeTicksBase'])


def set_locale_override(
        locale: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides default host system locale with the specified one.

    **EXPERIMENTAL**

    :param locale: *(Optional)* ICU style C locale (e.g. "en_US"). If not specified or empty, disables the override and restores default host system locale.
    '''
    params: T_JSON_DICT = dict()
    if locale is not None:
        params['locale'] = locale
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setLocaleOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_timezone_override(
        timezone_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides default host system timezone with the specified one.

    :param timezone_id: The timezone identifier. List of supported timezones: https://source.chromium.org/chromium/chromium/deps/icu.git/+/faee8bc70570192d82d2978a71e2a615788597d1:source/data/misc/metaZones.txt If empty, disables the override and restores default host system timezone.
    '''
    params: T_JSON_DICT = dict()
    params['timezoneId'] = timezone_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setTimezoneOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_visible_size(
        width: int,
        height: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resizes the frame/viewport of the page. Note that this does not affect the frame's container
    (e.g. browser window). Can be used to produce screenshots of the specified size. Not supported
    on Android.

    **EXPERIMENTAL**

    :param width: Frame width (DIP).
    :param height: Frame height (DIP).
    '''
    params: T_JSON_DICT = dict()
    params['width'] = width
    params['height'] = height
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setVisibleSize',
        'params': params,
    }
    json = yield cmd_dict


def set_disabled_image_types(
        image_types: typing.List[DisabledImageType]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param image_types: Image types to disable.
    '''
    params: T_JSON_DICT = dict()
    params['imageTypes'] = [i.to_json() for i in image_types]
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setDisabledImageTypes',
        'params': params,
    }
    json = yield cmd_dict


def set_hardware_concurrency_override(
        hardware_concurrency: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param hardware_concurrency: Hardware concurrency to report
    '''
    params: T_JSON_DICT = dict()
    params['hardwareConcurrency'] = hardware_concurrency
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setHardwareConcurrencyOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_user_agent_override(
        user_agent: str,
        accept_language: typing.Optional[str] = None,
        platform: typing.Optional[str] = None,
        user_agent_metadata: typing.Optional[UserAgentMetadata] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Allows overriding user agent with the given string.
    ``userAgentMetadata`` must be set for Client Hint headers to be sent.

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
        'method': 'Emulation.setUserAgentOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_automation_override(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Allows overriding the automation flag.

    **EXPERIMENTAL**

    :param enabled: Whether the override should be enabled.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setAutomationOverride',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Emulation.virtualTimeBudgetExpired')
@dataclass
class VirtualTimeBudgetExpired:
    '''
    **EXPERIMENTAL**

    Notification sent after the virtual time budget for the current VirtualTimePolicy has run out.
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> VirtualTimeBudgetExpired:
        return cls(

        )

# === NexusCore/openenv\Lib\site-packages\numpy\polynomial\_polybase.py ===
"""
Abstract base class for the various polynomial Classes.

The ABCPolyBase class provides the methods needed to implement the common API
for the various polynomial classes. It operates as a mixin, but uses the
abc module from the stdlib, hence it is only available for Python >= 2.6.

"""
import abc
import numbers
import os
from collections.abc import Callable

import numpy as np

from . import polyutils as pu

__all__ = ['ABCPolyBase']

class ABCPolyBase(abc.ABC):
    """An abstract base class for immutable series classes.

    ABCPolyBase provides the standard Python numerical methods
    '+', '-', '*', '//', '%', 'divmod', '**', and '()' along with the
    methods listed below.

    Parameters
    ----------
    coef : array_like
        Series coefficients in order of increasing degree, i.e.,
        ``(1, 2, 3)`` gives ``1*P_0(x) + 2*P_1(x) + 3*P_2(x)``, where
        ``P_i`` is the basis polynomials of degree ``i``.
    domain : (2,) array_like, optional
        Domain to use. The interval ``[domain[0], domain[1]]`` is mapped
        to the interval ``[window[0], window[1]]`` by shifting and scaling.
        The default value is the derived class domain.
    window : (2,) array_like, optional
        Window, see domain for its use. The default value is the
        derived class window.
    symbol : str, optional
        Symbol used to represent the independent variable in string
        representations of the polynomial expression, e.g. for printing.
        The symbol must be a valid Python identifier. Default value is 'x'.

        .. versionadded:: 1.24

    Attributes
    ----------
    coef : (N,) ndarray
        Series coefficients in order of increasing degree.
    domain : (2,) ndarray
        Domain that is mapped to window.
    window : (2,) ndarray
        Window that domain is mapped to.
    symbol : str
        Symbol representing the independent variable.

    Class Attributes
    ----------------
    maxpower : int
        Maximum power allowed, i.e., the largest number ``n`` such that
        ``p(x)**n`` is allowed. This is to limit runaway polynomial size.
    domain : (2,) ndarray
        Default domain of the class.
    window : (2,) ndarray
        Default window of the class.

    """

    # Not hashable
    __hash__ = None

    # Opt out of numpy ufuncs and Python ops with ndarray subclasses.
    __array_ufunc__ = None

    # Limit runaway size. T_n^m has degree n*m
    maxpower = 100

    # Unicode character mappings for improved __str__
    _superscript_mapping = str.maketrans({
        "0": "⁰",
        "1": "¹",
        "2": "²",
        "3": "³",
        "4": "⁴",
        "5": "⁵",
        "6": "⁶",
        "7": "⁷",
        "8": "⁸",
        "9": "⁹"
    })
    _subscript_mapping = str.maketrans({
        "0": "₀",
        "1": "₁",
        "2": "₂",
        "3": "₃",
        "4": "₄",
        "5": "₅",
        "6": "₆",
        "7": "₇",
        "8": "₈",
        "9": "₉"
    })
    # Some fonts don't support full unicode character ranges necessary for
    # the full set of superscripts and subscripts, including common/default
    # fonts in Windows shells/terminals. Therefore, default to ascii-only
    # printing on windows.
    _use_unicode = not os.name == 'nt'

    @property
    def symbol(self):
        return self._symbol

    @property
    @abc.abstractmethod
    def domain(self):
        pass

    @property
    @abc.abstractmethod
    def window(self):
        pass

    @property
    @abc.abstractmethod
    def basis_name(self):
        pass

    @staticmethod
    @abc.abstractmethod
    def _add(c1, c2):
        pass

    @staticmethod
    @abc.abstractmethod
    def _sub(c1, c2):
        pass

    @staticmethod
    @abc.abstractmethod
    def _mul(c1, c2):
        pass

    @staticmethod
    @abc.abstractmethod
    def _div(c1, c2):
        pass

    @staticmethod
    @abc.abstractmethod
    def _pow(c, pow, maxpower=None):
        pass

    @staticmethod
    @abc.abstractmethod
    def _val(x, c):
        pass

    @staticmethod
    @abc.abstractmethod
    def _int(c, m, k, lbnd, scl):
        pass

    @staticmethod
    @abc.abstractmethod
    def _der(c, m, scl):
        pass

    @staticmethod
    @abc.abstractmethod
    def _fit(x, y, deg, rcond, full):
        pass

    @staticmethod
    @abc.abstractmethod
    def _line(off, scl):
        pass

    @staticmethod
    @abc.abstractmethod
    def _roots(c):
        pass

    @staticmethod
    @abc.abstractmethod
    def _fromroots(r):
        pass

    def has_samecoef(self, other):
        """Check if coefficients match.

        Parameters
        ----------
        other : class instance
            The other class must have the ``coef`` attribute.

        Returns
        -------
        bool : boolean
            True if the coefficients are the same, False otherwise.

        """
        return (
            len(self.coef) == len(other.coef)
            and np.all(self.coef == other.coef)
        )

    def has_samedomain(self, other):
        """Check if domains match.

        Parameters
        ----------
        other : class instance
            The other class must have the ``domain`` attribute.

        Returns
        -------
        bool : boolean
            True if the domains are the same, False otherwise.

        """
        return np.all(self.domain == other.domain)

    def has_samewindow(self, other):
        """Check if windows match.

        Parameters
        ----------
        other : class instance
            The other class must have the ``window`` attribute.

        Returns
        -------
        bool : boolean
            True if the windows are the same, False otherwise.

        """
        return np.all(self.window == other.window)

    def has_sametype(self, other):
        """Check if types match.

        Parameters
        ----------
        other : object
            Class instance.

        Returns
        -------
        bool : boolean
            True if other is same class as self

        """
        return isinstance(other, self.__class__)

    def _get_coefficients(self, other):
        """Interpret other as polynomial coefficients.

        The `other` argument is checked to see if it is of the same
        class as self with identical domain and window. If so,
        return its coefficients, otherwise return `other`.

        Parameters
        ----------
        other : anything
            Object to be checked.

        Returns
        -------
        coef
            The coefficients of`other` if it is a compatible instance,
            of ABCPolyBase, otherwise `other`.

        Raises
        ------
        TypeError
            When `other` is an incompatible instance of ABCPolyBase.

        """
        if isinstance(other, ABCPolyBase):
            if not isinstance(other, self.__class__):
                raise TypeError("Polynomial types differ")
            elif not np.all(self.domain == other.domain):
                raise TypeError("Domains differ")
            elif not np.all(self.window == other.window):
                raise TypeError("Windows differ")
            elif self.symbol != other.symbol:
                raise ValueError("Polynomial symbols differ")
            return other.coef
        return other

    def __init__(self, coef, domain=None, window=None, symbol='x'):
        [coef] = pu.as_series([coef], trim=False)
        self.coef = coef

        if domain is not None:
            [domain] = pu.as_series([domain], trim=False)
            if len(domain) != 2:
                raise ValueError("Domain has wrong number of elements.")
            self.domain = domain

        if window is not None:
            [window] = pu.as_series([window], trim=False)
            if len(window) != 2:
                raise ValueError("Window has wrong number of elements.")
            self.window = window

        # Validation for symbol
        try:
            if not symbol.isidentifier():
                raise ValueError(
                    "Symbol string must be a valid Python identifier"
                )
        # If a user passes in something other than a string, the above
        # results in an AttributeError. Catch this and raise a more
        # informative exception
        except AttributeError:
            raise TypeError("Symbol must be a non-empty string")

        self._symbol = symbol

    def __repr__(self):
        coef = repr(self.coef)[6:-1]
        domain = repr(self.domain)[6:-1]
        window = repr(self.window)[6:-1]
        name = self.__class__.__name__
        return (f"{name}({coef}, domain={domain}, window={window}, "
                f"symbol='{self.symbol}')")

    def __format__(self, fmt_str):
        if fmt_str == '':
            return self.__str__()
        if fmt_str not in ('ascii', 'unicode'):
            raise ValueError(
                f"Unsupported format string '{fmt_str}' passed to "
                f"{self.__class__}.__format__. Valid options are "
                f"'ascii' and 'unicode'"
            )
        if fmt_str == 'ascii':
            return self._generate_string(self._str_term_ascii)
        return self._generate_string(self._str_term_unicode)

    def __str__(self):
        if self._use_unicode:
            return self._generate_string(self._str_term_unicode)
        return self._generate_string(self._str_term_ascii)

    def _generate_string(self, term_method):
        """
        Generate the full string representation of the polynomial, using
        ``term_method`` to generate each polynomial term.
        """
        # Get configuration for line breaks
        linewidth = np.get_printoptions().get('linewidth', 75)
        if linewidth < 1:
            linewidth = 1
        out = pu.format_float(self.coef[0])

        off, scale = self.mapparms()

        scaled_symbol, needs_parens = self._format_term(pu.format_float,
                                                        off, scale)
        if needs_parens:
            scaled_symbol = '(' + scaled_symbol + ')'

        for i, coef in enumerate(self.coef[1:]):
            out += " "
            power = str(i + 1)
            # Polynomial coefficient
            # The coefficient array can be an object array with elements that
            # will raise a TypeError with >= 0 (e.g. strings or Python
            # complex). In this case, represent the coefficient as-is.
            try:
                if coef >= 0:
                    next_term = "+ " + pu.format_float(coef, parens=True)
                else:
                    next_term = "- " + pu.format_float(-coef, parens=True)
            except TypeError:
                next_term = f"+ {coef}"
            # Polynomial term
            next_term += term_method(power, scaled_symbol)
            # Length of the current line with next term added
            line_len = len(out.split('\n')[-1]) + len(next_term)
            # If not the last term in the polynomial, it will be two
            # characters longer due to the +/- with the next term
            if i < len(self.coef[1:]) - 1:
                line_len += 2
            # Handle linebreaking
            if line_len >= linewidth:
                next_term = next_term.replace(" ", "\n", 1)
            out += next_term
        return out

    @classmethod
    def _str_term_unicode(cls, i, arg_str):
        """
        String representation of single polynomial term using unicode
        characters for superscripts and subscripts.
        """
        if cls.basis_name is None:
            raise NotImplementedError(
                "Subclasses must define either a basis_name, or override "
                "_str_term_unicode(cls, i, arg_str)"
            )
        return (f"·{cls.basis_name}{i.translate(cls._subscript_mapping)}"
                f"({arg_str})")

    @classmethod
    def _str_term_ascii(cls, i, arg_str):
        """
        String representation of a single polynomial term using ** and _ to
        represent superscripts and subscripts, respectively.
        """
        if cls.basis_name is None:
            raise NotImplementedError(
                "Subclasses must define either a basis_name, or override "
                "_str_term_ascii(cls, i, arg_str)"
            )
        return f" {cls.basis_name}_{i}({arg_str})"

    @classmethod
    def _repr_latex_term(cls, i, arg_str, needs_parens):
        if cls.basis_name is None:
            raise NotImplementedError(
                "Subclasses must define either a basis name, or override "
                "_repr_latex_term(i, arg_str, needs_parens)")
        # since we always add parens, we don't care if the expression needs them
        return f"{{{cls.basis_name}}}_{{{i}}}({arg_str})"

    @staticmethod
    def _repr_latex_scalar(x, parens=False):
        # TODO: we're stuck with disabling math formatting until we handle
        # exponents in this function
        return fr'\text{{{pu.format_float(x, parens=parens)}}}'

    def _format_term(self, scalar_format: Callable, off: float, scale: float):
        """ Format a single term in the expansion """
        if off == 0 and scale == 1:
            term = self.symbol
            needs_parens = False
        elif scale == 1:
            term = f"{scalar_format(off)} + {self.symbol}"
            needs_parens = True
        elif off == 0:
            term = f"{scalar_format(scale)}{self.symbol}"
            needs_parens = True
        else:
            term = (
                f"{scalar_format(off)} + "
                f"{scalar_format(scale)}{self.symbol}"
            )
            needs_parens = True
        return term, needs_parens

    def _repr_latex_(self):
        # get the scaled argument string to the basis functions
        off, scale = self.mapparms()
        term, needs_parens = self._format_term(self._repr_latex_scalar,
                                               off, scale)

        mute = r"\color{{LightGray}}{{{}}}".format

        parts = []
        for i, c in enumerate(self.coef):
            # prevent duplication of + and - signs
            if i == 0:
                coef_str = f"{self._repr_latex_scalar(c)}"
            elif not isinstance(c, numbers.Real):
                coef_str = f" + ({self._repr_latex_scalar(c)})"
            elif c >= 0:
                coef_str = f" + {self._repr_latex_scalar(c, parens=True)}"
            else:
                coef_str = f" - {self._repr_latex_scalar(-c, parens=True)}"

            # produce the string for the term
            term_str = self._repr_latex_term(i, term, needs_parens)
            if term_str == '1':
                part = coef_str
            else:
                part = rf"{coef_str}\,{term_str}"

            if c == 0:
                part = mute(part)

            parts.append(part)

        if parts:
            body = ''.join(parts)
        else:
            # in case somehow there are no coefficients at all
            body = '0'

        return rf"${self.symbol} \mapsto {body}$"

    # Pickle and copy

    def __getstate__(self):
        ret = self.__dict__.copy()
        ret['coef'] = self.coef.copy()
        ret['domain'] = self.domain.copy()
        ret['window'] = self.window.copy()
        ret['symbol'] = self.symbol
        return ret

    def __setstate__(self, dict):
        self.__dict__ = dict

    # Call

    def __call__(self, arg):
        arg = pu.mapdomain(arg, self.domain, self.window)
        return self._val(arg, self.coef)

    def __iter__(self):
        return iter(self.coef)

    def __len__(self):
        return len(self.coef)

    # Numeric properties.

    def __neg__(self):
        return self.__class__(
            -self.coef, self.domain, self.window, self.symbol
        )

    def __pos__(self):
        return self

    def __add__(self, other):
        othercoef = self._get_coefficients(other)
        try:
            coef = self._add(self.coef, othercoef)
        except Exception:
            return NotImplemented
        return self.__class__(coef, self.domain, self.window, self.symbol)

    def __sub__(self, other):
        othercoef = self._get_coefficients(other)
        try:
            coef = self._sub(self.coef, othercoef)
        except Exception:
            return NotImplemented
        return self.__class__(coef, self.domain, self.window, self.symbol)

    def __mul__(self, other):
        othercoef = self._get_coefficients(other)
        try:
            coef = self._mul(self.coef, othercoef)
        except Exception:
            return NotImplemented
        return self.__class__(coef, self.domain, self.window, self.symbol)

    def __truediv__(self, other):
        # there is no true divide if the rhs is not a Number, although it
        # could return the first n elements of an infinite series.
        # It is hard to see where n would come from, though.
        if not isinstance(other, numbers.Number) or isinstance(other, bool):
            raise TypeError(
                f"unsupported types for true division: "
                f"'{type(self)}', '{type(other)}'"
            )
        return self.__floordiv__(other)

    def __floordiv__(self, other):
        res = self.__divmod__(other)
        if res is NotImplemented:
            return res
        return res[0]

    def __mod__(self, other):
        res = self.__divmod__(other)
        if res is NotImplemented:
            return res
        return res[1]

    def __divmod__(self, other):
        othercoef = self._get_coefficients(other)
        try:
            quo, rem = self._div(self.coef, othercoef)
        except ZeroDivisionError:
            raise
        except Exception:
            return NotImplemented
        quo = self.__class__(quo, self.domain, self.window, self.symbol)
        rem = self.__class__(rem, self.domain, self.window, self.symbol)
        return quo, rem

    def __pow__(self, other):
        coef = self._pow(self.coef, other, maxpower=self.maxpower)
        res = self.__class__(coef, self.domain, self.window, self.symbol)
        return res

    def __radd__(self, other):
        try:
            coef = self._add(other, self.coef)
        except Exception:
            return NotImplemented
        return self.__class__(coef, self.domain, self.window, self.symbol)

    def __rsub__(self, other):
        try:
            coef = self._sub(other, self.coef)
        except Exception:
            return NotImplemented
        return self.__class__(coef, self.domain, self.window, self.symbol)

    def __rmul__(self, other):
        try:
            coef = self._mul(other, self.coef)
        except Exception:
            return NotImplemented
        return self.__class__(coef, self.domain, self.window, self.symbol)

    def __rtruediv__(self, other):
        # An instance of ABCPolyBase is not considered a
        # Number.
        return NotImplemented

    def __rfloordiv__(self, other):
        res = self.__rdivmod__(other)
        if res is NotImplemented:
            return res
        return res[0]

    def __rmod__(self, other):
        res = self.__rdivmod__(other)
        if res is NotImplemented:
            return res
        return res[1]

    def __rdivmod__(self, other):
        try:
            quo, rem = self._div(other, self.coef)
        except ZeroDivisionError:
            raise
        except Exception:
            return NotImplemented
        quo = self.__class__(quo, self.domain, self.window, self.symbol)
        rem = self.__class__(rem, self.domain, self.window, self.symbol)
        return quo, rem

    def __eq__(self, other):
        res = (isinstance(other, self.__class__) and
               np.all(self.domain == other.domain) and
               np.all(self.window == other.window) and
               (self.coef.shape == other.coef.shape) and
               np.all(self.coef == other.coef) and
               (self.symbol == other.symbol))
        return res

    def __ne__(self, other):
        return not self.__eq__(other)

    #
    # Extra methods.
    #

    def copy(self):
        """Return a copy.

        Returns
        -------
        new_series : series
            Copy of self.

        """
        return self.__class__(self.coef, self.domain, self.window, self.symbol)

    def degree(self):
        """The degree of the series.

        Returns
        -------
        degree : int
            Degree of the series, one less than the number of coefficients.

        Examples
        --------

        Create a polynomial object for ``1 + 7*x + 4*x**2``:

        >>> np.polynomial.set_default_printstyle("unicode")
        >>> poly = np.polynomial.Polynomial([1, 7, 4])
        >>> print(poly)
        1.0 + 7.0·x + 4.0·x²
        >>> poly.degree()
        2

        Note that this method does not check for non-zero coefficients.
        You must trim the polynomial to remove any trailing zeroes:

        >>> poly = np.polynomial.Polynomial([1, 7, 0])
        >>> print(poly)
        1.0 + 7.0·x + 0.0·x²
        >>> poly.degree()
        2
        >>> poly.trim().degree()
        1

        """
        return len(self) - 1

    def cutdeg(self, deg):
        """Truncate series to the given degree.

        Reduce the degree of the series to `deg` by discarding the
        high order terms. If `deg` is greater than the current degree a
        copy of the current series is returned. This can be useful in least
        squares where the coefficients of the high degree terms may be very
        small.

        Parameters
        ----------
        deg : non-negative int
            The series is reduced to degree `deg` by discarding the high
            order terms. The value of `deg` must be a non-negative integer.

        Returns
        -------
        new_series : series
            New instance of series with reduced degree.

        """
        return self.truncate(deg + 1)

    def trim(self, tol=0):
        """Remove trailing coefficients

        Remove trailing coefficients until a coefficient is reached whose
        absolute value greater than `tol` or the beginning of the series is
        reached. If all the coefficients would be removed the series is set
        to ``[0]``. A new series instance is returned with the new
        coefficients.  The current instance remains unchanged.

        Parameters
        ----------
        tol : non-negative number.
            All trailing coefficients less than `tol` will be removed.

        Returns
        -------
        new_series : series
            New instance of series with trimmed coefficients.

        """
        coef = pu.trimcoef(self.coef, tol)
        return self.__class__(coef, self.domain, self.window, self.symbol)

    def truncate(self, size):
        """Truncate series to length `size`.

        Reduce the series to length `size` by discarding the high
        degree terms. The value of `size` must be a positive integer. This
        can be useful in least squares where the coefficients of the
        high degree terms may be very small.

        Parameters
        ----------
        size : positive int
            The series is reduced to length `size` by discarding the high
            degree terms. The value of `size` must be a positive integer.

        Returns
        -------
        new_series : series
            New instance of series with truncated coefficients.

        """
        isize = int(size)
        if isize != size or isize < 1:
            raise ValueError("size must be a positive integer")
        if isize >= len(self.coef):
            coef = self.coef
        else:
            coef = self.coef[:isize]
        return self.__class__(coef, self.domain, self.window, self.symbol)

    def convert(self, domain=None, kind=None, window=None):
        """Convert series to a different kind and/or domain and/or window.

        Parameters
        ----------
        domain : array_like, optional
            The domain of the converted series. If the value is None,
            the default domain of `kind` is used.
        kind : class, optional
            The polynomial series type class to which the current instance
            should be converted. If kind is None, then the class of the
            current instance is used.
        window : array_like, optional
            The window of the converted series. If the value is None,
            the default window of `kind` is used.

        Returns
        -------
        new_series : series
            The returned class can be of different type than the current
            instance and/or have a different domain and/or different
            window.

        Notes
        -----
        Conversion between domains and class types can result in
        numerically ill defined series.

        """
        if kind is None:
            kind = self.__class__
        if domain is None:
            domain = kind.domain
        if window is None:
            window = kind.window
        return self(kind.identity(domain, window=window, symbol=self.symbol))

    def mapparms(self):
        """Return the mapping parameters.

        The returned values define a linear map ``off + scl*x`` that is
        applied to the input arguments before the series is evaluated. The
        map depends on the ``domain`` and ``window``; if the current
        ``domain`` is equal to the ``window`` the resulting map is the
        identity.  If the coefficients of the series instance are to be
        used by themselves outside this class, then the linear function
        must be substituted for the ``x`` in the standard representation of
        the base polynomials.

        Returns
        -------
        off, scl : float or complex
            The mapping function is defined by ``off + scl*x``.

        Notes
        -----
        If the current domain is the interval ``[l1, r1]`` and the window
        is ``[l2, r2]``, then the linear mapping function ``L`` is
        defined by the equations::

            L(l1) = l2
            L(r1) = r2

        """
        return pu.mapparms(self.domain, self.window)

    def integ(self, m=1, k=[], lbnd=None):
        """Integrate.

        Return a series instance that is the definite integral of the
        current series.

        Parameters
        ----------
        m : non-negative int
            The number of integrations to perform.
        k : array_like
            Integration constants. The first constant is applied to the
            first integration, the second to the second, and so on. The
            list of values must less than or equal to `m` in length and any
            missing values are set to zero.
        lbnd : Scalar
            The lower bound of the definite integral.

        Returns
        -------
        new_series : series
            A new series representing the integral. The domain is the same
            as the domain of the integrated series.

        """
        off, scl = self.mapparms()
        if lbnd is None:
            lbnd = 0
        else:
            lbnd = off + scl * lbnd
        coef = self._int(self.coef, m, k, lbnd, 1. / scl)
        return self.__class__(coef, self.domain, self.window, self.symbol)

    def deriv(self, m=1):
        """Differentiate.

        Return a series instance of that is the derivative of the current
        series.

        Parameters
        ----------
        m : non-negative int
            Find the derivative of order `m`.

        Returns
        -------
        new_series : series
            A new series representing the derivative. The domain is the same
            as the domain of the differentiated series.

        """
        off, scl = self.mapparms()
        coef = self._der(self.coef, m, scl)
        return self.__class__(coef, self.domain, self.window, self.symbol)

    def roots(self):
        """Return the roots of the series polynomial.

        Compute the roots for the series. Note that the accuracy of the
        roots decreases the further outside the `domain` they lie.

        Returns
        -------
        roots : ndarray
            Array containing the roots of the series.

        """
        roots = self._roots(self.coef)
        return pu.mapdomain(roots, self.window, self.domain)

    def linspace(self, n=100, domain=None):
        """Return x, y values at equally spaced points in domain.

        Returns the x, y values at `n` linearly spaced points across the
        domain.  Here y is the value of the polynomial at the points x. By
        default the domain is the same as that of the series instance.
        This method is intended mostly as a plotting aid.

        Parameters
        ----------
        n : int, optional
            Number of point pairs to return. The default value is 100.
        domain : {None, array_like}, optional
            If not None, the specified domain is used instead of that of
            the calling instance. It should be of the form ``[beg,end]``.
            The default is None which case the class domain is used.

        Returns
        -------
        x, y : ndarray
            x is equal to linspace(self.domain[0], self.domain[1], n) and
            y is the series evaluated at element of x.

        """
        if domain is None:
            domain = self.domain
        x = np.linspace(domain[0], domain[1], n)
        y = self(x)
        return x, y

    @classmethod
    def fit(cls, x, y, deg, domain=None, rcond=None, full=False, w=None,
        window=None, symbol='x'):
        """Least squares fit to data.

        Return a series instance that is the least squares fit to the data
        `y` sampled at `x`. The domain of the returned instance can be
        specified and this will often result in a superior fit with less
        chance of ill conditioning.

        Parameters
        ----------
        x : array_like, shape (M,)
            x-coordinates of the M sample points ``(x[i], y[i])``.
        y : array_like, shape (M,)
            y-coordinates of the M sample points ``(x[i], y[i])``.
        deg : int or 1-D array_like
            Degree(s) of the fitting polynomials. If `deg` is a single integer
            all terms up to and including the `deg`'th term are included in the
            fit. For NumPy versions >= 1.11.0 a list of integers specifying the
            degrees of the terms to include may be used instead.
        domain : {None, [beg, end], []}, optional
            Domain to use for the returned series. If ``None``,
            then a minimal domain that covers the points `x` is chosen.  If
            ``[]`` the class domain is used. The default value was the
            class domain in NumPy 1.4 and ``None`` in later versions.
            The ``[]`` option was added in numpy 1.5.0.
        rcond : float, optional
            Relative condition number of the fit. Singular values smaller
            than this relative to the largest singular value will be
            ignored. The default value is ``len(x)*eps``, where eps is the
            relative precision of the float type, about 2e-16 in most
            cases.
        full : bool, optional
            Switch determining nature of return value. When it is False
            (the default) just the coefficients are returned, when True
            diagnostic information from the singular value decomposition is
            also returned.
        w : array_like, shape (M,), optional
            Weights. If not None, the weight ``w[i]`` applies to the unsquared
            residual ``y[i] - y_hat[i]`` at ``x[i]``. Ideally the weights are
            chosen so that the errors of the products ``w[i]*y[i]`` all have
            the same variance.  When using inverse-variance weighting, use
            ``w[i] = 1/sigma(y[i])``.  The default value is None.
        window : {[beg, end]}, optional
            Window to use for the returned series. The default
            value is the default class domain
        symbol : str, optional
            Symbol representing the independent variable. Default is 'x'.

        Returns
        -------
        new_series : series
            A series that represents the least squares fit to the data and
            has the domain and window specified in the call. If the
            coefficients for the unscaled and unshifted basis polynomials are
            of interest, do ``new_series.convert().coef``.

        [resid, rank, sv, rcond] : list
            These values are only returned if ``full == True``

            - resid -- sum of squared residuals of the least squares fit
            - rank -- the numerical rank of the scaled Vandermonde matrix
            - sv -- singular values of the scaled Vandermonde matrix
            - rcond -- value of `rcond`.

            For more details, see `linalg.lstsq`.

        """
        if domain is None:
            domain = pu.getdomain(x)
            if domain[0] == domain[1]:
                domain[0] -= 1
                domain[1] += 1
        elif isinstance(domain, list) and len(domain) == 0:
            domain = cls.domain

        if window is None:
            window = cls.window

        xnew = pu.mapdomain(x, domain, window)
        res = cls._fit(xnew, y, deg, w=w, rcond=rcond, full=full)
        if full:
            [coef, status] = res
            return (
                cls(coef, domain=domain, window=window, symbol=symbol), status
            )
        else:
            coef = res
            return cls(coef, domain=domain, window=window, symbol=symbol)

    @classmethod
    def fromroots(cls, roots, domain=[], window=None, symbol='x'):
        """Return series instance that has the specified roots.

        Returns a series representing the product
        ``(x - r[0])*(x - r[1])*...*(x - r[n-1])``, where ``r`` is a
        list of roots.

        Parameters
        ----------
        roots : array_like
            List of roots.
        domain : {[], None, array_like}, optional
            Domain for the resulting series. If None the domain is the
            interval from the smallest root to the largest. If [] the
            domain is the class domain. The default is [].
        window : {None, array_like}, optional
            Window for the returned series. If None the class window is
            used. The default is None.
        symbol : str, optional
            Symbol representing the independent variable. Default is 'x'.

        Returns
        -------
        new_series : series
            Series with the specified roots.

        """
        [roots] = pu.as_series([roots], trim=False)
        if domain is None:
            domain = pu.getdomain(roots)
        elif isinstance(domain, list) and len(domain) == 0:
            domain = cls.domain

        if window is None:
            window = cls.window

        deg = len(roots)
        off, scl = pu.mapparms(domain, window)
        rnew = off + scl * roots
        coef = cls._fromroots(rnew) / scl**deg
        return cls(coef, domain=domain, window=window, symbol=symbol)

    @classmethod
    def identity(cls, domain=None, window=None, symbol='x'):
        """Identity function.

        If ``p`` is the returned series, then ``p(x) == x`` for all
        values of x.

        Parameters
        ----------
        domain : {None, array_like}, optional
            If given, the array must be of the form ``[beg, end]``, where
            ``beg`` and ``end`` are the endpoints of the domain. If None is
            given then the class domain is used. The default is None.
        window : {None, array_like}, optional
            If given, the resulting array must be if the form
            ``[beg, end]``, where ``beg`` and ``end`` are the endpoints of
            the window. If None is given then the class window is used. The
            default is None.
        symbol : str, optional
            Symbol representing the independent variable. Default is 'x'.

        Returns
        -------
        new_series : series
             Series of representing the identity.

        """
        if domain is None:
            domain = cls.domain
        if window is None:
            window = cls.window
        off, scl = pu.mapparms(window, domain)
        coef = cls._line(off, scl)
        return cls(coef, domain, window, symbol)

    @classmethod
    def basis(cls, deg, domain=None, window=None, symbol='x'):
        """Series basis polynomial of degree `deg`.

        Returns the series representing the basis polynomial of degree `deg`.

        Parameters
        ----------
        deg : int
            Degree of the basis polynomial for the series. Must be >= 0.
        domain : {None, array_like}, optional
            If given, the array must be of the form ``[beg, end]``, where
            ``beg`` and ``end`` are the endpoints of the domain. If None is
            given then the class domain is used. The default is None.
        window : {None, array_like}, optional
            If given, the resulting array must be if the form
            ``[beg, end]``, where ``beg`` and ``end`` are the endpoints of
            the window. If None is given then the class window is used. The
            default is None.
        symbol : str, optional
            Symbol representing the independent variable. Default is 'x'.

        Returns
        -------
        new_series : series
            A series with the coefficient of the `deg` term set to one and
            all others zero.

        """
        if domain is None:
            domain = cls.domain
        if window is None:
            window = cls.window
        ideg = int(deg)

        if ideg != deg or ideg < 0:
            raise ValueError("deg must be non-negative integer")
        return cls([0] * ideg + [1], domain, window, symbol)

    @classmethod
    def cast(cls, series, domain=None, window=None):
        """Convert series to series of this class.

        The `series` is expected to be an instance of some polynomial
        series of one of the types supported by by the numpy.polynomial
        module, but could be some other class that supports the convert
        method.

        Parameters
        ----------
        series : series
            The series instance to be converted.
        domain : {None, array_like}, optional
            If given, the array must be of the form ``[beg, end]``, where
            ``beg`` and ``end`` are the endpoints of the domain. If None is
            given then the class domain is used. The default is None.
        window : {None, array_like}, optional
            If given, the resulting array must be if the form
            ``[beg, end]``, where ``beg`` and ``end`` are the endpoints of
            the window. If None is given then the class window is used. The
            default is None.

        Returns
        -------
        new_series : series
            A series of the same kind as the calling class and equal to
            `series` when evaluated.

        See Also
        --------
        convert : similar instance method

        """
        if domain is None:
            domain = cls.domain
        if window is None:
            window = cls.window
        return series.convert(domain, cls, window)

# === NexusCore/openenv\Lib\site-packages\trio\_subprocess.py ===
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import warnings
from contextlib import ExitStack
from functools import partial
from typing import (
    TYPE_CHECKING,
    Final,
    Literal,
    Protocol,
    TypedDict,
    Union,
    overload,
)

import trio

from ._core import ClosedResourceError, TaskStatus
from ._highlevel_generic import StapledStream
from ._subprocess_platform import (
    create_pipe_from_child_output,
    create_pipe_to_child_stdin,
    wait_child_exiting,
)
from ._sync import Lock
from ._util import NoPublicConstructor, final

if TYPE_CHECKING:
    import signal
    from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
    from io import TextIOWrapper

    from typing_extensions import TypeAlias, Unpack

    from ._abc import ReceiveStream, SendStream


# Sphinx cannot parse the stringified version
StrOrBytesPath: TypeAlias = Union[str, bytes, os.PathLike[str], os.PathLike[bytes]]


# Linux-specific, but has complex lifetime management stuff so we hard-code it
# here instead of hiding it behind the _subprocess_platform abstraction
can_try_pidfd_open: bool
if TYPE_CHECKING:

    def pidfd_open(fd: int, flags: int) -> int: ...

    from ._subprocess_platform import ClosableReceiveStream, ClosableSendStream

else:
    can_try_pidfd_open = True
    try:
        from os import pidfd_open
    except ImportError:
        if sys.platform == "linux":
            # this workaround is needed on:
            #  - CPython <= 3.8
            #  - non-CPython (maybe?)
            #  - Anaconda's interpreter (as it is built to assume an older
            #    than current linux kernel)
            #
            # The last point implies that other custom builds might not work;
            # therefore, no assertion should be here.
            import ctypes

            _cdll_for_pidfd_open = ctypes.CDLL(None, use_errno=True)
            _cdll_for_pidfd_open.syscall.restype = ctypes.c_long
            # pid and flags are actually int-sized, but the syscall() function
            # always takes longs. (Except on x32 where long is 32-bits and syscall
            # takes 64-bit arguments. But in the unlikely case that anyone is
            # using x32, this will still work, b/c we only need to pass in 32 bits
            # of data, and the C ABI doesn't distinguish between passing 32-bit vs
            # 64-bit integers; our 32-bit values will get loaded into 64-bit
            # registers where syscall() will find them.)
            _cdll_for_pidfd_open.syscall.argtypes = [
                ctypes.c_long,  # syscall number
                ctypes.c_long,  # pid
                ctypes.c_long,  # flags
            ]
            __NR_pidfd_open = 434

            def pidfd_open(fd: int, flags: int) -> int:
                result = _cdll_for_pidfd_open.syscall(__NR_pidfd_open, fd, flags)
                if result < 0:  # pragma: no cover
                    err = ctypes.get_errno()
                    raise OSError(err, os.strerror(err))
                return result

        else:
            can_try_pidfd_open = False


class HasFileno(Protocol):
    """Represents any file-like object that has a file descriptor."""

    def fileno(self) -> int: ...


@final
class Process(metaclass=NoPublicConstructor):
    r"""A child process. Like :class:`subprocess.Popen`, but async.

    This class has no public constructor. The most common way to get a
    `Process` object is to combine `Nursery.start` with `run_process`::

       process_object = await nursery.start(run_process, ...)

    This way, `run_process` supervises the process and makes sure that it is
    cleaned up properly, while optionally checking the return value, feeding
    it input, and so on.

    If you need more control – for example, because you want to spawn a child
    process that outlives your program – then another option is to use
    `trio.lowlevel.open_process`::

       process_object = await trio.lowlevel.open_process(...)

    Attributes:
      args (str or list): The ``command`` passed at construction time,
          specifying the process to execute and its arguments.
      pid (int): The process ID of the child process managed by this object.
      stdin (trio.abc.SendStream or None): A stream connected to the child's
          standard input stream: when you write bytes here, they become available
          for the child to read. Only available if the :class:`Process`
          was constructed using ``stdin=PIPE``; otherwise this will be None.
      stdout (trio.abc.ReceiveStream or None): A stream connected to
          the child's standard output stream: when the child writes to
          standard output, the written bytes become available for you
          to read here. Only available if the :class:`Process` was
          constructed using ``stdout=PIPE``; otherwise this will be None.
      stderr (trio.abc.ReceiveStream or None): A stream connected to
          the child's standard error stream: when the child writes to
          standard error, the written bytes become available for you
          to read here. Only available if the :class:`Process` was
          constructed using ``stderr=PIPE``; otherwise this will be None.
      stdio (trio.StapledStream or None): A stream that sends data to
          the child's standard input and receives from the child's standard
          output. Only available if both :attr:`stdin` and :attr:`stdout` are
          available; otherwise this will be None.

    """

    # We're always in binary mode.
    universal_newlines: Final = False
    encoding: Final = None
    errors: Final = None

    # Available for the per-platform wait_child_exiting() implementations
    # to stash some state; waitid platforms use this to avoid spawning
    # arbitrarily many threads if wait() keeps getting cancelled.
    _wait_for_exit_data: object = None

    def __init__(
        self,
        popen: subprocess.Popen[bytes],
        stdin: SendStream | None,
        stdout: ReceiveStream | None,
        stderr: ReceiveStream | None,
    ) -> None:
        self._proc = popen
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

        self.stdio: StapledStream[SendStream, ReceiveStream] | None = None
        if self.stdin is not None and self.stdout is not None:
            self.stdio = StapledStream(self.stdin, self.stdout)

        self._wait_lock: Lock = Lock()

        self._pidfd: TextIOWrapper | None = None
        if can_try_pidfd_open:
            try:
                fd: int = pidfd_open(self._proc.pid, 0)
            except OSError:  # pragma: no cover
                # Well, we tried, but it didn't work (probably because we're
                # running on an older kernel, or in an older sandbox, that
                # hasn't been updated to support pidfd_open). We'll fall back
                # on waitid instead.
                pass
            else:
                # It worked! Wrap the raw fd up in a Python file object to
                # make sure it'll get closed.
                # SIM115: open-file-with-context-handler
                self._pidfd = open(fd)  # noqa: SIM115

        self.args: StrOrBytesPath | Sequence[StrOrBytesPath] = self._proc.args
        self.pid: int = self._proc.pid

    def __repr__(self) -> str:
        returncode = self.returncode
        if returncode is None:
            status = f"running with PID {self.pid}"
        else:
            if returncode < 0:
                status = f"exited with signal {-returncode}"
            else:
                status = f"exited with status {returncode}"
        return f"<trio.Process {self.args!r}: {status}>"

    @property
    def returncode(self) -> int | None:
        """The exit status of the process (an integer), or ``None`` if it's
        still running.

        By convention, a return code of zero indicates success.  On
        UNIX, negative values indicate termination due to a signal,
        e.g., -11 if terminated by signal 11 (``SIGSEGV``).  On
        Windows, a process that exits due to a call to
        :meth:`Process.terminate` will have an exit status of 1.

        Unlike the standard library `subprocess.Popen.returncode`, you don't
        have to call `poll` or `wait` to update this attribute; it's
        automatically updated as needed, and will always give you the latest
        information.

        """
        result = self._proc.poll()
        if result is not None:
            self._close_pidfd()
        return result

    def _close_pidfd(self) -> None:
        if self._pidfd is not None:
            trio.lowlevel.notify_closing(self._pidfd.fileno())
            self._pidfd.close()
            self._pidfd = None

    async def wait(self) -> int:
        """Block until the process exits.

        Returns:
          The exit status of the process; see :attr:`returncode`.
        """
        async with self._wait_lock:
            if self.poll() is None:
                if self._pidfd is not None:
                    with contextlib.suppress(
                        ClosedResourceError,
                    ):  # something else (probably a call to poll) already closed the pidfd
                        await trio.lowlevel.wait_readable(self._pidfd.fileno())
                else:
                    await wait_child_exiting(self)
                # We have to use .wait() here, not .poll(), because on macOS
                # (and maybe other systems, who knows), there's a race
                # condition inside the kernel that creates a tiny window where
                # kqueue reports that the process has exited, but
                # waitpid(WNOHANG) can't yet reap it. So this .wait() may
                # actually block for a tiny fraction of a second.
                self._proc.wait()
                self._close_pidfd()
        assert self._proc.returncode is not None
        return self._proc.returncode

    def poll(self) -> int | None:
        """Returns the exit status of the process (an integer), or ``None`` if
        it's still running.

        Note that on Trio (unlike the standard library `subprocess.Popen`),
        ``process.poll()`` and ``process.returncode`` always give the same
        result. See `returncode` for more details. This method is only
        included to make it easier to port code from `subprocess`.

        """
        return self.returncode

    def send_signal(self, sig: signal.Signals | int) -> None:
        """Send signal ``sig`` to the process.

        On UNIX, ``sig`` may be any signal defined in the
        :mod:`signal` module, such as ``signal.SIGINT`` or
        ``signal.SIGTERM``. On Windows, it may be anything accepted by
        the standard library :meth:`subprocess.Popen.send_signal`.
        """
        self._proc.send_signal(sig)

    def terminate(self) -> None:
        """Terminate the process, politely if possible.

        On UNIX, this is equivalent to
        ``send_signal(signal.SIGTERM)``; by convention this requests
        graceful termination, but a misbehaving or buggy process might
        ignore it. On Windows, :meth:`terminate` forcibly terminates the
        process in the same manner as :meth:`kill`.
        """
        self._proc.terminate()

    def kill(self) -> None:
        """Immediately terminate the process.

        On UNIX, this is equivalent to
        ``send_signal(signal.SIGKILL)``.  On Windows, it calls
        ``TerminateProcess``. In both cases, the process cannot
        prevent itself from being killed, but the termination will be
        delivered asynchronously; use :meth:`wait` if you want to
        ensure the process is actually dead before proceeding.
        """
        self._proc.kill()


async def _open_process(
    command: StrOrBytesPath | Sequence[StrOrBytesPath],
    *,
    stdin: int | HasFileno | None = None,
    stdout: int | HasFileno | None = None,
    stderr: int | HasFileno | None = None,
    **options: object,
) -> Process:
    r"""Execute a child program in a new process.

    After construction, you can interact with the child process by writing data to its
    `~trio.Process.stdin` stream (a `~trio.abc.SendStream`), reading data from its
    `~trio.Process.stdout` and/or `~trio.Process.stderr` streams (both
    `~trio.abc.ReceiveStream`\s), sending it signals using `~trio.Process.terminate`,
    `~trio.Process.kill`, or `~trio.Process.send_signal`, and waiting for it to exit
    using `~trio.Process.wait`. See `trio.Process` for details.

    Each standard stream is only available if you specify that a pipe should be created
    for it. For example, if you pass ``stdin=subprocess.PIPE``, you can write to the
    `~trio.Process.stdin` stream, else `~trio.Process.stdin` will be ``None``.

    Unlike `trio.run_process`, this function doesn't do any kind of automatic
    management of the child process. It's up to you to implement whatever semantics you
    want.

    Args:
      command: The command to run. Typically this is a sequence of strings or
          bytes such as ``['ls', '-l', 'directory with spaces']``, where the
          first element names the executable to invoke and the other elements
          specify its arguments. With ``shell=True`` in the ``**options``, or on
          Windows, ``command`` can be a string or bytes, which will be parsed
          following platform-dependent :ref:`quoting rules
          <subprocess-quoting>`. In all cases ``command`` can be a path or a
          sequence of paths.
      stdin: Specifies what the child process's standard input
          stream should connect to: output written by the parent
          (``subprocess.PIPE``), nothing (``subprocess.DEVNULL``),
          or an open file (pass a file descriptor or something whose
          ``fileno`` method returns one). If ``stdin`` is unspecified,
          the child process will have the same standard input stream
          as its parent.
      stdout: Like ``stdin``, but for the child process's standard output
          stream.
      stderr: Like ``stdin``, but for the child process's standard error
          stream. An additional value ``subprocess.STDOUT`` is supported,
          which causes the child's standard output and standard error
          messages to be intermixed on a single standard output stream,
          attached to whatever the ``stdout`` option says to attach it to.
      **options: Other :ref:`general subprocess options <subprocess-options>`
          are also accepted.

    Returns:
      A new `trio.Process` object.

    Raises:
      OSError: if the process spawning fails, for example because the
         specified command could not be found.

    """
    for key in ("universal_newlines", "text", "encoding", "errors", "bufsize"):
        if options.get(key):
            raise TypeError(
                "trio.Process only supports communicating over "
                f"unbuffered byte streams; the '{key}' option is not supported",
            )

    if os.name == "posix":
        # TODO: how do paths and sequences thereof play with `shell=True`?
        if isinstance(command, (str, bytes)) and not options.get("shell"):
            raise TypeError(
                "command must be a sequence (not a string or bytes) if "
                "shell=False on UNIX systems",
            )
        if not isinstance(command, (str, bytes)) and options.get("shell"):
            raise TypeError(
                "command must be a string or bytes (not a sequence) if "
                "shell=True on UNIX systems",
            )

    trio_stdin: ClosableSendStream | None = None
    trio_stdout: ClosableReceiveStream | None = None
    trio_stderr: ClosableReceiveStream | None = None
    # Close the parent's handle for each child side of a pipe; we want the child to
    # have the only copy, so that when it exits we can read EOF on our side. The
    # trio ends of pipes will be transferred to the Process object, which will be
    # responsible for their lifetime. If process spawning fails, though, we still
    # want to close them before letting the failure bubble out
    with ExitStack() as always_cleanup, ExitStack() as cleanup_on_fail:
        if stdin == subprocess.PIPE:
            trio_stdin, stdin = create_pipe_to_child_stdin()
            always_cleanup.callback(os.close, stdin)
            cleanup_on_fail.callback(trio_stdin.close)
        if stdout == subprocess.PIPE:
            trio_stdout, stdout = create_pipe_from_child_output()
            always_cleanup.callback(os.close, stdout)
            cleanup_on_fail.callback(trio_stdout.close)
        if stderr == subprocess.STDOUT:
            # If we created a pipe for stdout, pass the same pipe for
            # stderr.  If stdout was some non-pipe thing (DEVNULL or a
            # given FD), pass the same thing. If stdout was passed as
            # None, keep stderr as STDOUT to allow subprocess to dup
            # our stdout. Regardless of which of these is applicable,
            # don't create a new Trio stream for stderr -- if stdout
            # is piped, stderr will be intermixed on the stdout stream.
            if stdout is not None:
                stderr = stdout
        elif stderr == subprocess.PIPE:
            trio_stderr, stderr = create_pipe_from_child_output()
            always_cleanup.callback(os.close, stderr)
            cleanup_on_fail.callback(trio_stderr.close)

        popen = await trio.to_thread.run_sync(
            partial(
                subprocess.Popen,
                command,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                **options,
            ),
        )
        # We did not fail, so dismiss the stack for the trio ends
        cleanup_on_fail.pop_all()

    return Process._create(popen, trio_stdin, trio_stdout, trio_stderr)


# async function missing await
async def _windows_deliver_cancel(p: Process) -> None:  # noqa: RUF029
    try:
        p.terminate()
    except OSError as exc:
        warnings.warn(
            RuntimeWarning(f"TerminateProcess on {p!r} failed with: {exc!r}"),
            stacklevel=1,
        )


async def _posix_deliver_cancel(p: Process) -> None:
    try:
        p.terminate()
        await trio.sleep(5)
        warnings.warn(
            RuntimeWarning(
                f"process {p!r} ignored SIGTERM for 5 seconds. "
                "(Maybe you should pass a custom deliver_cancel?) "
                "Trying SIGKILL.",
            ),
            stacklevel=1,
        )
        p.kill()
    except OSError as exc:
        warnings.warn(
            RuntimeWarning(f"tried to kill process {p!r}, but failed with: {exc!r}"),
            stacklevel=1,
        )


# Use a private name, so we can declare platform-specific stubs below.
# This is also the signature read by Sphinx
async def _run_process(
    command: StrOrBytesPath | Sequence[StrOrBytesPath],
    *,
    stdin: bytes | bytearray | memoryview | int | HasFileno | None = b"",
    capture_stdout: bool = False,
    capture_stderr: bool = False,
    check: bool = True,
    deliver_cancel: Callable[[Process], Awaitable[object]] | None = None,
    task_status: TaskStatus[Process] = trio.TASK_STATUS_IGNORED,
    **options: object,
) -> subprocess.CompletedProcess[bytes]:
    """Run ``command`` in a subprocess and wait for it to complete.

    This function can be called in two different ways.

    One option is a direct call, like::

        completed_process_info = await trio.run_process(...)

    In this case, it returns a :class:`subprocess.CompletedProcess` instance
    describing the results. Use this if you want to treat a process like a
    function call.

    The other option is to run it as a task using `Nursery.start` – the enhanced version
    of `~Nursery.start_soon` that lets a task pass back a value during startup::

        process = await nursery.start(trio.run_process, ...)

    In this case, `~Nursery.start` returns a `Process` object that you can use
    to interact with the process while it's running. Use this if you want to
    treat a process like a background task.

    Either way, `run_process` makes sure that the process has exited before
    returning, handles cancellation, optionally checks for errors, and
    provides some convenient shorthands for dealing with the child's
    input/output.

    **Input:** `run_process` supports all the same ``stdin=`` arguments as
    `subprocess.Popen`. In addition, if you simply want to pass in some fixed
    data, you can pass a plain `bytes` object, and `run_process` will take
    care of setting up a pipe, feeding in the data you gave, and then sending
    end-of-file. The default is ``b""``, which means that the child will receive
    an empty stdin. If you want the child to instead read from the parent's
    stdin, use ``stdin=None``.

    **Output:** By default, any output produced by the subprocess is
    passed through to the standard output and error streams of the
    parent Trio process.

    When calling `run_process` directly, you can capture the subprocess's output by
    passing ``capture_stdout=True`` to capture the subprocess's standard output, and/or
    ``capture_stderr=True`` to capture its standard error. Captured data is collected up
    by Trio into an in-memory buffer, and then provided as the
    :attr:`~subprocess.CompletedProcess.stdout` and/or
    :attr:`~subprocess.CompletedProcess.stderr` attributes of the returned
    :class:`~subprocess.CompletedProcess` object. The value for any stream that was not
    captured will be ``None``.

    If you want to capture both stdout and stderr while keeping them
    separate, pass ``capture_stdout=True, capture_stderr=True``.

    If you want to capture both stdout and stderr but mixed together
    in the order they were printed, use: ``capture_stdout=True, stderr=subprocess.STDOUT``.
    This directs the child's stderr into its stdout, so the combined
    output will be available in the `~subprocess.CompletedProcess.stdout`
    attribute.

    If you're using ``await nursery.start(trio.run_process, ...)`` and want to capture
    the subprocess's output for further processing, then use ``stdout=subprocess.PIPE``
    and then make sure to read the data out of the `Process.stdout` stream. If you want
    to capture stderr separately, use ``stderr=subprocess.PIPE``. If you want to capture
    both, but mixed together in the correct order, use ``stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT``.

    **Error checking:** If the subprocess exits with a nonzero status
    code, indicating failure, :func:`run_process` raises a
    :exc:`subprocess.CalledProcessError` exception rather than
    returning normally. The captured outputs are still available as
    the :attr:`~subprocess.CalledProcessError.stdout` and
    :attr:`~subprocess.CalledProcessError.stderr` attributes of that
    exception.  To disable this behavior, so that :func:`run_process`
    returns normally even if the subprocess exits abnormally, pass ``check=False``.

    Note that this can make the ``capture_stdout`` and ``capture_stderr``
    arguments useful even when starting `run_process` as a task: if you only
    care about the output if the process fails, then you can enable capturing
    and then read the output off of the `~subprocess.CalledProcessError`.

    **Cancellation:** If cancelled, `run_process` sends a termination
    request to the subprocess, then waits for it to fully exit. The
    ``deliver_cancel`` argument lets you control how the process is terminated.

    .. note:: `run_process` is intentionally similar to the standard library
       `subprocess.run`, but some of the defaults are different. Specifically, we
       default to:

       - ``check=True``, because `"errors should never pass silently / unless
         explicitly silenced" <https://www.python.org/dev/peps/pep-0020/>`__.

       - ``stdin=b""``, because it produces less-confusing results if a subprocess
         unexpectedly tries to read from stdin.

       To get the `subprocess.run` semantics, use ``check=False, stdin=None``.

    Args:
      command (list or str): The command to run. Typically this is a
          sequence of strings such as ``['ls', '-l', 'directory with spaces']``,
          where the first element names the executable to invoke and the other
          elements specify its arguments. With ``shell=True`` in the
          ``**options``, or on Windows, ``command`` may alternatively
          be a string, which will be parsed following platform-dependent
          :ref:`quoting rules <subprocess-quoting>`.

      stdin (:obj:`bytes`, subprocess.PIPE, file descriptor, or None): The
          bytes to provide to the subprocess on its standard input stream, or
          ``None`` if the subprocess's standard input should come from the
          same place as the parent Trio process's standard input. As is the
          case with the :mod:`subprocess` module, you can also pass a file
          descriptor or an object with a ``fileno()`` method, in which case
          the subprocess's standard input will come from that file.

          When starting `run_process` as a background task, you can also use
          ``stdin=subprocess.PIPE``, in which case `Process.stdin` will be a
          `~trio.abc.SendStream` that you can use to send data to the child.

      capture_stdout (bool): If true, capture the bytes that the subprocess
          writes to its standard output stream and return them in the
          `~subprocess.CompletedProcess.stdout` attribute of the returned
          `subprocess.CompletedProcess` or `subprocess.CalledProcessError`.

      capture_stderr (bool): If true, capture the bytes that the subprocess
          writes to its standard error stream and return them in the
          `~subprocess.CompletedProcess.stderr` attribute of the returned
          `~subprocess.CompletedProcess` or `subprocess.CalledProcessError`.

      check (bool): If false, don't validate that the subprocess exits
          successfully. You should be sure to check the
          ``returncode`` attribute of the returned object if you pass
          ``check=False``, so that errors don't pass silently.

      deliver_cancel (async function or None): If `run_process` is cancelled,
          then it needs to kill the child process. There are multiple ways to
          do this, so we let you customize it.

          If you pass None (the default), then the behavior depends on the
          platform:

          - On Windows, Trio calls ``TerminateProcess``, which should kill the
            process immediately.

          - On Unix-likes, the default behavior is to send a ``SIGTERM``, wait
            5 seconds, and send a ``SIGKILL``.

          Alternatively, you can customize this behavior by passing in an
          arbitrary async function, which will be called with the `Process`
          object as an argument. For example, the default Unix behavior could
          be implemented like this::

             async def my_deliver_cancel(process):
                 process.send_signal(signal.SIGTERM)
                 await trio.sleep(5)
                 process.send_signal(signal.SIGKILL)

          When the process actually exits, the ``deliver_cancel`` function
          will automatically be cancelled – so if the process exits after
          ``SIGTERM``, then we'll never reach the ``SIGKILL``.

          In any case, `run_process` will always wait for the child process to
          exit before raising `Cancelled`.

      **options: :func:`run_process` also accepts any :ref:`general subprocess
          options <subprocess-options>` and passes them on to the
          :class:`~trio.Process` constructor. This includes the
          ``stdout`` and ``stderr`` options, which provide additional
          redirection possibilities such as ``stderr=subprocess.STDOUT``,
          ``stdout=subprocess.DEVNULL``, or file descriptors.

    Returns:

      When called normally – a `subprocess.CompletedProcess` instance
      describing the return code and outputs.

      When called via `Nursery.start` – a `trio.Process` instance.

    Raises:
      UnicodeError: if ``stdin`` is specified as a Unicode string, rather
          than bytes
      ValueError: if multiple redirections are specified for the same
          stream, e.g., both ``capture_stdout=True`` and
          ``stdout=subprocess.DEVNULL``
      subprocess.CalledProcessError: if ``check=False`` is not passed
          and the process exits with a nonzero exit status
      OSError: if an error is encountered starting or communicating with
          the process
      ExceptionGroup: if exceptions occur in ``deliver_cancel``,
          or when exceptions occur when communicating with the subprocess.
          If strict_exception_groups is set to false in the global context,
          which is deprecated, then single exceptions will be collapsed.

    .. note:: The child process runs in the same process group as the parent
       Trio process, so a Ctrl+C will be delivered simultaneously to both
       parent and child. If you don't want this behavior, consult your
       platform's documentation for starting child processes in a different
       process group.

    """

    if isinstance(stdin, str):
        raise UnicodeError("process stdin must be bytes, not str")
    if task_status is trio.TASK_STATUS_IGNORED:
        if stdin is subprocess.PIPE:
            raise ValueError(
                "stdout=subprocess.PIPE is only valid with nursery.start, "
                "since that's the only way to access the pipe; use nursery.start "
                "or pass the data you want to write directly",
            )
        if options.get("stdout") is subprocess.PIPE:
            raise ValueError(
                "stdout=subprocess.PIPE is only valid with nursery.start, "
                "since that's the only way to access the pipe",
            )
        if options.get("stderr") is subprocess.PIPE:
            raise ValueError(
                "stderr=subprocess.PIPE is only valid with nursery.start, "
                "since that's the only way to access the pipe",
            )
    if isinstance(stdin, (bytes, bytearray, memoryview)):
        input_ = stdin
        options["stdin"] = subprocess.PIPE
    else:
        # stdin should be something acceptable to Process
        # (None, DEVNULL, a file descriptor, etc) and Process
        # will raise if it's not
        input_ = None
        options["stdin"] = stdin

    if capture_stdout:
        if "stdout" in options:
            raise ValueError("can't specify both stdout and capture_stdout")
        options["stdout"] = subprocess.PIPE
    if capture_stderr:
        if "stderr" in options:
            raise ValueError("can't specify both stderr and capture_stderr")
        options["stderr"] = subprocess.PIPE

    if deliver_cancel is None:
        if os.name == "nt":
            deliver_cancel = _windows_deliver_cancel
        else:
            assert os.name == "posix"
            deliver_cancel = _posix_deliver_cancel

    stdout_chunks: list[bytes | bytearray] = []
    stderr_chunks: list[bytes | bytearray] = []

    async def feed_input(stream: SendStream) -> None:
        async with stream:
            try:
                assert input_ is not None
                await stream.send_all(input_)
            except trio.BrokenResourceError:
                pass

    async def read_output(
        stream: ReceiveStream,
        chunks: list[bytes | bytearray],
    ) -> None:
        async with stream:
            async for chunk in stream:
                chunks.append(chunk)  # noqa: PERF401

    # Opening the process does not need to be inside the nursery, so we put it outside
    # so any exceptions get directly seen by users.
    # options needs a complex TypedDict. The overload error only occurs on Unix.
    proc = await open_process(command, **options)  # type: ignore[arg-type, call-overload, unused-ignore]
    async with trio.open_nursery() as nursery:
        try:
            if input_ is not None:
                assert proc.stdin is not None
                nursery.start_soon(feed_input, proc.stdin)
                proc.stdin = None
                proc.stdio = None
            if capture_stdout:
                assert proc.stdout is not None
                nursery.start_soon(read_output, proc.stdout, stdout_chunks)
                proc.stdout = None
                proc.stdio = None
            if capture_stderr:
                assert proc.stderr is not None
                nursery.start_soon(read_output, proc.stderr, stderr_chunks)
                proc.stderr = None
            task_status.started(proc)
            await proc.wait()
        except BaseException:
            with trio.CancelScope(shield=True):
                killer_cscope = trio.CancelScope(shield=True)

                async def killer() -> None:
                    with killer_cscope:
                        await deliver_cancel(proc)

                nursery.start_soon(killer)
                await proc.wait()
                killer_cscope.cancel()
                raise

    stdout = b"".join(stdout_chunks) if capture_stdout else None
    stderr = b"".join(stderr_chunks) if capture_stderr else None

    if proc.returncode and check:
        raise subprocess.CalledProcessError(
            proc.returncode,
            proc.args,
            output=stdout,
            stderr=stderr,
        )
    else:
        assert proc.returncode is not None
        return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)


# There's a lot of duplication here because type checkers don't
# have a good way to represent overloads that differ only
# slightly. A cheat sheet:
#
# - on Windows, command is Union[str, Sequence[str]];
#   on Unix, command is str if shell=True and Sequence[str] otherwise
#
# - on Windows, there are startupinfo and creationflags options;
#   on Unix, there are preexec_fn, restore_signals, start_new_session,
#            pass_fds, group (3.9+), extra_groups (3.9+), user (3.9+),
#            umask (3.9+), pipesize (3.10+), process_group (3.11+)
#
# - run_process() has the signature of open_process() plus arguments
#   capture_stdout, capture_stderr, check, deliver_cancel, the ability
#   to pass bytes as stdin, and the ability to run in `nursery.start`


class GeneralProcessArgs(TypedDict, total=False):
    """Arguments shared between all runs."""

    stdout: int | HasFileno | None
    stderr: int | HasFileno | None
    close_fds: bool
    cwd: StrOrBytesPath | None
    env: Mapping[str, str] | None
    executable: StrOrBytesPath | None


if TYPE_CHECKING:
    if sys.platform == "win32":

        class WindowsProcessArgs(GeneralProcessArgs, total=False):
            """Arguments shared between all Windows runs."""

            shell: bool
            startupinfo: subprocess.STARTUPINFO | None
            creationflags: int

        async def open_process(
            command: StrOrBytesPath | Sequence[StrOrBytesPath],
            *,
            stdin: int | HasFileno | None = None,
            **kwargs: Unpack[WindowsProcessArgs],
        ) -> trio.Process:
            r"""Execute a child program in a new process.

            After construction, you can interact with the child process by writing data to its
            `~trio.Process.stdin` stream (a `~trio.abc.SendStream`), reading data from its
            `~trio.Process.stdout` and/or `~trio.Process.stderr` streams (both
            `~trio.abc.ReceiveStream`\s), sending it signals using `~trio.Process.terminate`,
            `~trio.Process.kill`, or `~trio.Process.send_signal`, and waiting for it to exit
            using `~trio.Process.wait`. See `trio.Process` for details.

            Each standard stream is only available if you specify that a pipe should be created
            for it. For example, if you pass ``stdin=subprocess.PIPE``, you can write to the
            `~trio.Process.stdin` stream, else `~trio.Process.stdin` will be ``None``.

            Unlike `trio.run_process`, this function doesn't do any kind of automatic
            management of the child process. It's up to you to implement whatever semantics you
            want.

            Args:
              command (list or str): The command to run. Typically this is a
                  sequence of strings such as ``['ls', '-l', 'directory with spaces']``,
                  where the first element names the executable to invoke and the other
                  elements specify its arguments. With ``shell=True`` in the
                  ``**options``, or on Windows, ``command`` may alternatively
                  be a string, which will be parsed following platform-dependent
                  :ref:`quoting rules <subprocess-quoting>`.
              stdin: Specifies what the child process's standard input
                  stream should connect to: output written by the parent
                  (``subprocess.PIPE``), nothing (``subprocess.DEVNULL``),
                  or an open file (pass a file descriptor or something whose
                  ``fileno`` method returns one). If ``stdin`` is unspecified,
                  the child process will have the same standard input stream
                  as its parent.
              stdout: Like ``stdin``, but for the child process's standard output
                  stream.
              stderr: Like ``stdin``, but for the child process's standard error
                  stream. An additional value ``subprocess.STDOUT`` is supported,
                  which causes the child's standard output and standard error
                  messages to be intermixed on a single standard output stream,
                  attached to whatever the ``stdout`` option says to attach it to.
              **options: Other :ref:`general subprocess options <subprocess-options>`
                  are also accepted.

            Returns:
              A new `trio.Process` object.

            Raises:
              OSError: if the process spawning fails, for example because the
                 specified command could not be found.

            """
            ...

        async def run_process(
            command: StrOrBytesPath | Sequence[StrOrBytesPath],
            *,
            task_status: TaskStatus[Process] = trio.TASK_STATUS_IGNORED,
            stdin: bytes | bytearray | memoryview | int | HasFileno | None = None,
            capture_stdout: bool = False,
            capture_stderr: bool = False,
            check: bool = True,
            deliver_cancel: Callable[[Process], Awaitable[object]] | None = None,
            **kwargs: Unpack[WindowsProcessArgs],
        ) -> subprocess.CompletedProcess[bytes]:
            """Run ``command`` in a subprocess and wait for it to complete.

            This function can be called in two different ways.

            One option is a direct call, like::

                completed_process_info = await trio.run_process(...)

            In this case, it returns a :class:`subprocess.CompletedProcess` instance
            describing the results. Use this if you want to treat a process like a
            function call.

            The other option is to run it as a task using `Nursery.start` – the enhanced version
            of `~Nursery.start_soon` that lets a task pass back a value during startup::

                process = await nursery.start(trio.run_process, ...)

            In this case, `~Nursery.start` returns a `Process` object that you can use
            to interact with the process while it's running. Use this if you want to
            treat a process like a background task.

            Either way, `run_process` makes sure that the process has exited before
            returning, handles cancellation, optionally checks for errors, and
            provides some convenient shorthands for dealing with the child's
            input/output.

            **Input:** `run_process` supports all the same ``stdin=`` arguments as
            `subprocess.Popen`. In addition, if you simply want to pass in some fixed
            data, you can pass a plain `bytes` object, and `run_process` will take
            care of setting up a pipe, feeding in the data you gave, and then sending
            end-of-file. The default is ``b""``, which means that the child will receive
            an empty stdin. If you want the child to instead read from the parent's
            stdin, use ``stdin=None``.

            **Output:** By default, any output produced by the subprocess is
            passed through to the standard output and error streams of the
            parent Trio process.

            When calling `run_process` directly, you can capture the subprocess's output by
            passing ``capture_stdout=True`` to capture the subprocess's standard output, and/or
            ``capture_stderr=True`` to capture its standard error. Captured data is collected up
            by Trio into an in-memory buffer, and then provided as the
            :attr:`~subprocess.CompletedProcess.stdout` and/or
            :attr:`~subprocess.CompletedProcess.stderr` attributes of the returned
            :class:`~subprocess.CompletedProcess` object. The value for any stream that was not
            captured will be ``None``.

            If you want to capture both stdout and stderr while keeping them
            separate, pass ``capture_stdout=True, capture_stderr=True``.

            If you want to capture both stdout and stderr but mixed together
            in the order they were printed, use: ``capture_stdout=True, stderr=subprocess.STDOUT``.
            This directs the child's stderr into its stdout, so the combined
            output will be available in the `~subprocess.CompletedProcess.stdout`
            attribute.

            If you're using ``await nursery.start(trio.run_process, ...)`` and want to capture
            the subprocess's output for further processing, then use ``stdout=subprocess.PIPE``
            and then make sure to read the data out of the `Process.stdout` stream. If you want
            to capture stderr separately, use ``stderr=subprocess.PIPE``. If you want to capture
            both, but mixed together in the correct order, use ``stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT``.

            **Error checking:** If the subprocess exits with a nonzero status
            code, indicating failure, :func:`run_process` raises a
            :exc:`subprocess.CalledProcessError` exception rather than
            returning normally. The captured outputs are still available as
            the :attr:`~subprocess.CalledProcessError.stdout` and
            :attr:`~subprocess.CalledProcessError.stderr` attributes of that
            exception.  To disable this behavior, so that :func:`run_process`
            returns normally even if the subprocess exits abnormally, pass ``check=False``.

            Note that this can make the ``capture_stdout`` and ``capture_stderr``
            arguments useful even when starting `run_process` as a task: if you only
            care about the output if the process fails, then you can enable capturing
            and then read the output off of the `~subprocess.CalledProcessError`.

            **Cancellation:** If cancelled, `run_process` sends a termination
            request to the subprocess, then waits for it to fully exit. The
            ``deliver_cancel`` argument lets you control how the process is terminated.

            .. note:: `run_process` is intentionally similar to the standard library
               `subprocess.run`, but some of the defaults are different. Specifically, we
               default to:

               - ``check=True``, because `"errors should never pass silently / unless
                 explicitly silenced" <https://www.python.org/dev/peps/pep-0020/>`__.

               - ``stdin=b""``, because it produces less-confusing results if a subprocess
                 unexpectedly tries to read from stdin.

               To get the `subprocess.run` semantics, use ``check=False, stdin=None``.

            Args:
              command (list or str): The command to run. Typically this is a
                  sequence of strings such as ``['ls', '-l', 'directory with spaces']``,
                  where the first element names the executable to invoke and the other
                  elements specify its arguments. With ``shell=True`` in the
                  ``**options``, or on Windows, ``command`` may alternatively
                  be a string, which will be parsed following platform-dependent
                  :ref:`quoting rules <subprocess-quoting>`.

              stdin (:obj:`bytes`, subprocess.PIPE, file descriptor, or None): The
                  bytes to provide to the subprocess on its standard input stream, or
                  ``None`` if the subprocess's standard input should come from the
                  same place as the parent Trio process's standard input. As is the
                  case with the :mod:`subprocess` module, you can also pass a file
                  descriptor or an object with a ``fileno()`` method, in which case
                  the subprocess's standard input will come from that file.

                  When starting `run_process` as a background task, you can also use
                  ``stdin=subprocess.PIPE``, in which case `Process.stdin` will be a
                  `~trio.abc.SendStream` that you can use to send data to the child.

              capture_stdout (bool): If true, capture the bytes that the subprocess
                  writes to its standard output stream and return them in the
                  `~subprocess.CompletedProcess.stdout` attribute of the returned
                  `subprocess.CompletedProcess` or `subprocess.CalledProcessError`.

              capture_stderr (bool): If true, capture the bytes that the subprocess
                  writes to its standard error stream and return them in the
                  `~subprocess.CompletedProcess.stderr` attribute of the returned
                  `~subprocess.CompletedProcess` or `subprocess.CalledProcessError`.

              check (bool): If false, don't validate that the subprocess exits
                  successfully. You should be sure to check the
                  ``returncode`` attribute of the returned object if you pass
                  ``check=False``, so that errors don't pass silently.

              deliver_cancel (async function or None): If `run_process` is cancelled,
                  then it needs to kill the child process. There are multiple ways to
                  do this, so we let you customize it.

                  If you pass None (the default), then the behavior depends on the
                  platform:

                  - On Windows, Trio calls ``TerminateProcess``, which should kill the
                    process immediately.

                  - On Unix-likes, the default behavior is to send a ``SIGTERM``, wait
                    5 seconds, and send a ``SIGKILL``.

                  Alternatively, you can customize this behavior by passing in an
                  arbitrary async function, which will be called with the `Process`
                  object as an argument. For example, the default Unix behavior could
                  be implemented like this::

                     async def my_deliver_cancel(process):
                         process.send_signal(signal.SIGTERM)
                         await trio.sleep(5)
                         process.send_signal(signal.SIGKILL)

                  When the process actually exits, the ``deliver_cancel`` function
                  will automatically be cancelled – so if the process exits after
                  ``SIGTERM``, then we'll never reach the ``SIGKILL``.

                  In any case, `run_process` will always wait for the child process to
                  exit before raising `Cancelled`.

              **options: :func:`run_process` also accepts any :ref:`general subprocess
                  options <subprocess-options>` and passes them on to the
                  :class:`~trio.Process` constructor. This includes the
                  ``stdout`` and ``stderr`` options, which provide additional
                  redirection possibilities such as ``stderr=subprocess.STDOUT``,
                  ``stdout=subprocess.DEVNULL``, or file descriptors.

            Returns:

              When called normally – a `subprocess.CompletedProcess` instance
              describing the return code and outputs.

              When called via `Nursery.start` – a `trio.Process` instance.

            Raises:
              UnicodeError: if ``stdin`` is specified as a Unicode string, rather
                  than bytes
              ValueError: if multiple redirections are specified for the same
                  stream, e.g., both ``capture_stdout=True`` and
                  ``stdout=subprocess.DEVNULL``
              subprocess.CalledProcessError: if ``check=False`` is not passed
                  and the process exits with a nonzero exit status
              OSError: if an error is encountered starting or communicating with
                  the process

            .. note:: The child process runs in the same process group as the parent
               Trio process, so a Ctrl+C will be delivered simultaneously to both
               parent and child. If you don't want this behavior, consult your
               platform's documentation for starting child processes in a different
               process group.

            """
            ...

    else:  # Unix
        # pyright doesn't give any error about overloads missing docstrings as they're
        # overloads. But might still be a problem for other static analyzers / docstring
        # readers (?)

        class UnixProcessArgs3_9(GeneralProcessArgs, total=False):
            """Arguments shared between all Unix runs."""

            preexec_fn: Callable[[], object] | None
            restore_signals: bool
            start_new_session: bool
            pass_fds: Sequence[int]

            # 3.9+
            group: str | int | None
            extra_groups: Iterable[str | int] | None
            user: str | int | None
            umask: int

        class UnixProcessArgs3_10(UnixProcessArgs3_9, total=False):
            """Arguments shared between all Unix runs on 3.10+."""

            pipesize: int

        class UnixProcessArgs3_11(UnixProcessArgs3_10, total=False):
            """Arguments shared between all Unix runs on 3.11+."""

            process_group: int | None

        class UnixRunProcessMixin(TypedDict, total=False):
            """Arguments unique to run_process on Unix."""

            task_status: TaskStatus[Process]
            capture_stdout: bool
            capture_stderr: bool
            check: bool
            deliver_cancel: Callable[[Process], Awaitable[None]] | None

        # TODO: once https://github.com/python/mypy/issues/18692 is
        #       fixed, move the `UnixRunProcessArgs` definition down.
        if sys.version_info >= (3, 11):
            UnixProcessArgs = UnixProcessArgs3_11

            class UnixRunProcessArgs(UnixProcessArgs3_11, UnixRunProcessMixin):
                """Arguments for run_process on Unix with 3.11+"""

        elif sys.version_info >= (3, 10):
            UnixProcessArgs = UnixProcessArgs3_10

            class UnixRunProcessArgs(UnixProcessArgs3_10, UnixRunProcessMixin):
                """Arguments for run_process on Unix with 3.10+"""

        else:
            UnixProcessArgs = UnixProcessArgs3_9

            class UnixRunProcessArgs(UnixProcessArgs3_9, UnixRunProcessMixin):
                """Arguments for run_process on Unix with 3.9+"""

        @overload  # type: ignore[no-overload-impl]
        async def open_process(
            command: StrOrBytesPath,
            *,
            stdin: int | HasFileno | None = None,
            shell: Literal[True],
            **kwargs: Unpack[UnixProcessArgs],
        ) -> trio.Process: ...

        @overload
        async def open_process(
            command: Sequence[StrOrBytesPath],
            *,
            stdin: int | HasFileno | None = None,
            shell: bool = False,
            **kwargs: Unpack[UnixProcessArgs],
        ) -> trio.Process: ...

        @overload  # type: ignore[no-overload-impl]
        async def run_process(
            command: StrOrBytesPath,
            *,
            stdin: bytes | bytearray | memoryview | int | HasFileno | None = None,
            shell: Literal[True],
            **kwargs: Unpack[UnixRunProcessArgs],
        ) -> subprocess.CompletedProcess[bytes]: ...

        @overload
        async def run_process(
            command: Sequence[StrOrBytesPath],
            *,
            stdin: bytes | bytearray | memoryview | int | HasFileno | None = None,
            shell: bool = False,
            **kwargs: Unpack[UnixRunProcessArgs],
        ) -> subprocess.CompletedProcess[bytes]: ...

else:
    # At runtime, use the actual implementations.
    open_process = _open_process
    open_process.__name__ = open_process.__qualname__ = "open_process"

    run_process = _run_process
    run_process.__name__ = run_process.__qualname__ = "run_process"

# === NexusCore/openenv\Lib\site-packages\fontTools\ufoLib\validators.py ===
"""Various low level data validators."""

import calendar
from io import open
import fs.base
import fs.osfs

from collections.abc import Mapping
from fontTools.ufoLib.utils import numberTypes


# -------
# Generic
# -------


def isDictEnough(value):
    """
    Some objects will likely come in that aren't
    dicts but are dict-ish enough.
    """
    if isinstance(value, Mapping):
        return True
    for attr in ("keys", "values", "items"):
        if not hasattr(value, attr):
            return False
    return True


def genericTypeValidator(value, typ):
    """
    Generic. (Added at version 2.)
    """
    return isinstance(value, typ)


def genericIntListValidator(values, validValues):
    """
    Generic. (Added at version 2.)
    """
    if not isinstance(values, (list, tuple)):
        return False
    valuesSet = set(values)
    validValuesSet = set(validValues)
    if valuesSet - validValuesSet:
        return False
    for value in values:
        if not isinstance(value, int):
            return False
    return True


def genericNonNegativeIntValidator(value):
    """
    Generic. (Added at version 3.)
    """
    if not isinstance(value, int):
        return False
    if value < 0:
        return False
    return True


def genericNonNegativeNumberValidator(value):
    """
    Generic. (Added at version 3.)
    """
    if not isinstance(value, numberTypes):
        return False
    if value < 0:
        return False
    return True


def genericDictValidator(value, prototype):
    """
    Generic. (Added at version 3.)
    """
    # not a dict
    if not isinstance(value, Mapping):
        return False
    # missing required keys
    for key, (typ, required) in prototype.items():
        if not required:
            continue
        if key not in value:
            return False
    # unknown keys
    for key in value.keys():
        if key not in prototype:
            return False
    # incorrect types
    for key, v in value.items():
        prototypeType, required = prototype[key]
        if v is None and not required:
            continue
        if not isinstance(v, prototypeType):
            return False
    return True


# --------------
# fontinfo.plist
# --------------

# Data Validators


def fontInfoStyleMapStyleNameValidator(value):
    """
    Version 2+.
    """
    options = ["regular", "italic", "bold", "bold italic"]
    return value in options


def fontInfoOpenTypeGaspRangeRecordsValidator(value):
    """
    Version 3+.
    """
    if not isinstance(value, list):
        return False
    if len(value) == 0:
        return True
    validBehaviors = [0, 1, 2, 3]
    dictPrototype = dict(rangeMaxPPEM=(int, True), rangeGaspBehavior=(list, True))
    ppemOrder = []
    for rangeRecord in value:
        if not genericDictValidator(rangeRecord, dictPrototype):
            return False
        ppem = rangeRecord["rangeMaxPPEM"]
        behavior = rangeRecord["rangeGaspBehavior"]
        ppemValidity = genericNonNegativeIntValidator(ppem)
        if not ppemValidity:
            return False
        behaviorValidity = genericIntListValidator(behavior, validBehaviors)
        if not behaviorValidity:
            return False
        ppemOrder.append(ppem)
    if ppemOrder != sorted(ppemOrder):
        return False
    return True


def fontInfoOpenTypeHeadCreatedValidator(value):
    """
    Version 2+.
    """
    # format: 0000/00/00 00:00:00
    if not isinstance(value, str):
        return False
    # basic formatting
    if not len(value) == 19:
        return False
    if value.count(" ") != 1:
        return False
    date, time = value.split(" ")
    if date.count("/") != 2:
        return False
    if time.count(":") != 2:
        return False
    # date
    year, month, day = date.split("/")
    if len(year) != 4:
        return False
    if len(month) != 2:
        return False
    if len(day) != 2:
        return False
    try:
        year = int(year)
        month = int(month)
        day = int(day)
    except ValueError:
        return False
    if month < 1 or month > 12:
        return False
    monthMaxDay = calendar.monthrange(year, month)[1]
    if day < 1 or day > monthMaxDay:
        return False
    # time
    hour, minute, second = time.split(":")
    if len(hour) != 2:
        return False
    if len(minute) != 2:
        return False
    if len(second) != 2:
        return False
    try:
        hour = int(hour)
        minute = int(minute)
        second = int(second)
    except ValueError:
        return False
    if hour < 0 or hour > 23:
        return False
    if minute < 0 or minute > 59:
        return False
    if second < 0 or second > 59:
        return False
    # fallback
    return True


def fontInfoOpenTypeNameRecordsValidator(value):
    """
    Version 3+.
    """
    if not isinstance(value, list):
        return False
    dictPrototype = dict(
        nameID=(int, True),
        platformID=(int, True),
        encodingID=(int, True),
        languageID=(int, True),
        string=(str, True),
    )
    for nameRecord in value:
        if not genericDictValidator(nameRecord, dictPrototype):
            return False
    return True


def fontInfoOpenTypeOS2WeightClassValidator(value):
    """
    Version 2+.
    """
    if not isinstance(value, int):
        return False
    if value < 0:
        return False
    return True


def fontInfoOpenTypeOS2WidthClassValidator(value):
    """
    Version 2+.
    """
    if not isinstance(value, int):
        return False
    if value < 1:
        return False
    if value > 9:
        return False
    return True


def fontInfoVersion2OpenTypeOS2PanoseValidator(values):
    """
    Version 2.
    """
    if not isinstance(values, (list, tuple)):
        return False
    if len(values) != 10:
        return False
    for value in values:
        if not isinstance(value, int):
            return False
    # XXX further validation?
    return True


def fontInfoVersion3OpenTypeOS2PanoseValidator(values):
    """
    Version 3+.
    """
    if not isinstance(values, (list, tuple)):
        return False
    if len(values) != 10:
        return False
    for value in values:
        if not isinstance(value, int):
            return False
        if value < 0:
            return False
    # XXX further validation?
    return True


def fontInfoOpenTypeOS2FamilyClassValidator(values):
    """
    Version 2+.
    """
    if not isinstance(values, (list, tuple)):
        return False
    if len(values) != 2:
        return False
    for value in values:
        if not isinstance(value, int):
            return False
    classID, subclassID = values
    if classID < 0 or classID > 14:
        return False
    if subclassID < 0 or subclassID > 15:
        return False
    return True


def fontInfoPostscriptBluesValidator(values):
    """
    Version 2+.
    """
    if not isinstance(values, (list, tuple)):
        return False
    if len(values) > 14:
        return False
    if len(values) % 2:
        return False
    for value in values:
        if not isinstance(value, numberTypes):
            return False
    return True


def fontInfoPostscriptOtherBluesValidator(values):
    """
    Version 2+.
    """
    if not isinstance(values, (list, tuple)):
        return False
    if len(values) > 10:
        return False
    if len(values) % 2:
        return False
    for value in values:
        if not isinstance(value, numberTypes):
            return False
    return True


def fontInfoPostscriptStemsValidator(values):
    """
    Version 2+.
    """
    if not isinstance(values, (list, tuple)):
        return False
    if len(values) > 12:
        return False
    for value in values:
        if not isinstance(value, numberTypes):
            return False
    return True


def fontInfoPostscriptWindowsCharacterSetValidator(value):
    """
    Version 2+.
    """
    validValues = list(range(1, 21))
    if value not in validValues:
        return False
    return True


def fontInfoWOFFMetadataUniqueIDValidator(value):
    """
    Version 3+.
    """
    dictPrototype = dict(id=(str, True))
    if not genericDictValidator(value, dictPrototype):
        return False
    return True


def fontInfoWOFFMetadataVendorValidator(value):
    """
    Version 3+.
    """
    dictPrototype = {
        "name": (str, True),
        "url": (str, False),
        "dir": (str, False),
        "class": (str, False),
    }
    if not genericDictValidator(value, dictPrototype):
        return False
    if "dir" in value and value.get("dir") not in ("ltr", "rtl"):
        return False
    return True


def fontInfoWOFFMetadataCreditsValidator(value):
    """
    Version 3+.
    """
    dictPrototype = dict(credits=(list, True))
    if not genericDictValidator(value, dictPrototype):
        return False
    if not len(value["credits"]):
        return False
    dictPrototype = {
        "name": (str, True),
        "url": (str, False),
        "role": (str, False),
        "dir": (str, False),
        "class": (str, False),
    }
    for credit in value["credits"]:
        if not genericDictValidator(credit, dictPrototype):
            return False
        if "dir" in credit and credit.get("dir") not in ("ltr", "rtl"):
            return False
    return True


def fontInfoWOFFMetadataDescriptionValidator(value):
    """
    Version 3+.
    """
    dictPrototype = dict(url=(str, False), text=(list, True))
    if not genericDictValidator(value, dictPrototype):
        return False
    for text in value["text"]:
        if not fontInfoWOFFMetadataTextValue(text):
            return False
    return True


def fontInfoWOFFMetadataLicenseValidator(value):
    """
    Version 3+.
    """
    dictPrototype = dict(url=(str, False), text=(list, False), id=(str, False))
    if not genericDictValidator(value, dictPrototype):
        return False
    if "text" in value:
        for text in value["text"]:
            if not fontInfoWOFFMetadataTextValue(text):
                return False
    return True


def fontInfoWOFFMetadataTrademarkValidator(value):
    """
    Version 3+.
    """
    dictPrototype = dict(text=(list, True))
    if not genericDictValidator(value, dictPrototype):
        return False
    for text in value["text"]:
        if not fontInfoWOFFMetadataTextValue(text):
            return False
    return True


def fontInfoWOFFMetadataCopyrightValidator(value):
    """
    Version 3+.
    """
    dictPrototype = dict(text=(list, True))
    if not genericDictValidator(value, dictPrototype):
        return False
    for text in value["text"]:
        if not fontInfoWOFFMetadataTextValue(text):
            return False
    return True


def fontInfoWOFFMetadataLicenseeValidator(value):
    """
    Version 3+.
    """
    dictPrototype = {"name": (str, True), "dir": (str, False), "class": (str, False)}
    if not genericDictValidator(value, dictPrototype):
        return False
    if "dir" in value and value.get("dir") not in ("ltr", "rtl"):
        return False
    return True


def fontInfoWOFFMetadataTextValue(value):
    """
    Version 3+.
    """
    dictPrototype = {
        "text": (str, True),
        "language": (str, False),
        "dir": (str, False),
        "class": (str, False),
    }
    if not genericDictValidator(value, dictPrototype):
        return False
    if "dir" in value and value.get("dir") not in ("ltr", "rtl"):
        return False
    return True


def fontInfoWOFFMetadataExtensionsValidator(value):
    """
    Version 3+.
    """
    if not isinstance(value, list):
        return False
    if not value:
        return False
    for extension in value:
        if not fontInfoWOFFMetadataExtensionValidator(extension):
            return False
    return True


def fontInfoWOFFMetadataExtensionValidator(value):
    """
    Version 3+.
    """
    dictPrototype = dict(names=(list, False), items=(list, True), id=(str, False))
    if not genericDictValidator(value, dictPrototype):
        return False
    if "names" in value:
        for name in value["names"]:
            if not fontInfoWOFFMetadataExtensionNameValidator(name):
                return False
    for item in value["items"]:
        if not fontInfoWOFFMetadataExtensionItemValidator(item):
            return False
    return True


def fontInfoWOFFMetadataExtensionItemValidator(value):
    """
    Version 3+.
    """
    dictPrototype = dict(id=(str, False), names=(list, True), values=(list, True))
    if not genericDictValidator(value, dictPrototype):
        return False
    for name in value["names"]:
        if not fontInfoWOFFMetadataExtensionNameValidator(name):
            return False
    for val in value["values"]:
        if not fontInfoWOFFMetadataExtensionValueValidator(val):
            return False
    return True


def fontInfoWOFFMetadataExtensionNameValidator(value):
    """
    Version 3+.
    """
    dictPrototype = {
        "text": (str, True),
        "language": (str, False),
        "dir": (str, False),
        "class": (str, False),
    }
    if not genericDictValidator(value, dictPrototype):
        return False
    if "dir" in value and value.get("dir") not in ("ltr", "rtl"):
        return False
    return True


def fontInfoWOFFMetadataExtensionValueValidator(value):
    """
    Version 3+.
    """
    dictPrototype = {
        "text": (str, True),
        "language": (str, False),
        "dir": (str, False),
        "class": (str, False),
    }
    if not genericDictValidator(value, dictPrototype):
        return False
    if "dir" in value and value.get("dir") not in ("ltr", "rtl"):
        return False
    return True


# ----------
# Guidelines
# ----------


def guidelinesValidator(value, identifiers=None):
    """
    Version 3+.
    """
    if not isinstance(value, list):
        return False
    if identifiers is None:
        identifiers = set()
    for guide in value:
        if not guidelineValidator(guide):
            return False
        identifier = guide.get("identifier")
        if identifier is not None:
            if identifier in identifiers:
                return False
            identifiers.add(identifier)
    return True


_guidelineDictPrototype = dict(
    x=((int, float), False),
    y=((int, float), False),
    angle=((int, float), False),
    name=(str, False),
    color=(str, False),
    identifier=(str, False),
)


def guidelineValidator(value):
    """
    Version 3+.
    """
    if not genericDictValidator(value, _guidelineDictPrototype):
        return False
    x = value.get("x")
    y = value.get("y")
    angle = value.get("angle")
    # x or y must be present
    if x is None and y is None:
        return False
    # if x or y are None, angle must not be present
    if x is None or y is None:
        if angle is not None:
            return False
    # if x and y are defined, angle must be defined
    if x is not None and y is not None and angle is None:
        return False
    # angle must be between 0 and 360
    if angle is not None:
        if angle < 0:
            return False
        if angle > 360:
            return False
    # identifier must be 1 or more characters
    identifier = value.get("identifier")
    if identifier is not None and not identifierValidator(identifier):
        return False
    # color must follow the proper format
    color = value.get("color")
    if color is not None and not colorValidator(color):
        return False
    return True


# -------
# Anchors
# -------


def anchorsValidator(value, identifiers=None):
    """
    Version 3+.
    """
    if not isinstance(value, list):
        return False
    if identifiers is None:
        identifiers = set()
    for anchor in value:
        if not anchorValidator(anchor):
            return False
        identifier = anchor.get("identifier")
        if identifier is not None:
            if identifier in identifiers:
                return False
            identifiers.add(identifier)
    return True


_anchorDictPrototype = dict(
    x=((int, float), False),
    y=((int, float), False),
    name=(str, False),
    color=(str, False),
    identifier=(str, False),
)


def anchorValidator(value):
    """
    Version 3+.
    """
    if not genericDictValidator(value, _anchorDictPrototype):
        return False
    x = value.get("x")
    y = value.get("y")
    # x and y must be present
    if x is None or y is None:
        return False
    # identifier must be 1 or more characters
    identifier = value.get("identifier")
    if identifier is not None and not identifierValidator(identifier):
        return False
    # color must follow the proper format
    color = value.get("color")
    if color is not None and not colorValidator(color):
        return False
    return True


# ----------
# Identifier
# ----------


def identifierValidator(value):
    """
    Version 3+.

    >>> identifierValidator("a")
    True
    >>> identifierValidator("")
    False
    >>> identifierValidator("a" * 101)
    False
    """
    validCharactersMin = 0x20
    validCharactersMax = 0x7E
    if not isinstance(value, str):
        return False
    if not value:
        return False
    if len(value) > 100:
        return False
    for c in value:
        c = ord(c)
        if c < validCharactersMin or c > validCharactersMax:
            return False
    return True


# -----
# Color
# -----


def colorValidator(value):
    """
    Version 3+.

    >>> colorValidator("0,0,0,0")
    True
    >>> colorValidator(".5,.5,.5,.5")
    True
    >>> colorValidator("0.5,0.5,0.5,0.5")
    True
    >>> colorValidator("1,1,1,1")
    True

    >>> colorValidator("2,0,0,0")
    False
    >>> colorValidator("0,2,0,0")
    False
    >>> colorValidator("0,0,2,0")
    False
    >>> colorValidator("0,0,0,2")
    False

    >>> colorValidator("1r,1,1,1")
    False
    >>> colorValidator("1,1g,1,1")
    False
    >>> colorValidator("1,1,1b,1")
    False
    >>> colorValidator("1,1,1,1a")
    False

    >>> colorValidator("1 1 1 1")
    False
    >>> colorValidator("1 1,1,1")
    False
    >>> colorValidator("1,1 1,1")
    False
    >>> colorValidator("1,1,1 1")
    False

    >>> colorValidator("1, 1, 1, 1")
    True
    """
    if not isinstance(value, str):
        return False
    parts = value.split(",")
    if len(parts) != 4:
        return False
    for part in parts:
        part = part.strip()
        converted = False
        try:
            part = int(part)
            converted = True
        except ValueError:
            pass
        if not converted:
            try:
                part = float(part)
                converted = True
            except ValueError:
                pass
        if not converted:
            return False
        if part < 0:
            return False
        if part > 1:
            return False
    return True


# -----
# image
# -----

pngSignature = b"\x89PNG\r\n\x1a\n"

_imageDictPrototype = dict(
    fileName=(str, True),
    xScale=((int, float), False),
    xyScale=((int, float), False),
    yxScale=((int, float), False),
    yScale=((int, float), False),
    xOffset=((int, float), False),
    yOffset=((int, float), False),
    color=(str, False),
)


def imageValidator(value):
    """
    Version 3+.
    """
    if not genericDictValidator(value, _imageDictPrototype):
        return False
    # fileName must be one or more characters
    if not value["fileName"]:
        return False
    # color must follow the proper format
    color = value.get("color")
    if color is not None and not colorValidator(color):
        return False
    return True


def pngValidator(path=None, data=None, fileObj=None):
    """
    Version 3+.

    This checks the signature of the image data.
    """
    assert path is not None or data is not None or fileObj is not None
    if path is not None:
        with open(path, "rb") as f:
            signature = f.read(8)
    elif data is not None:
        signature = data[:8]
    elif fileObj is not None:
        pos = fileObj.tell()
        signature = fileObj.read(8)
        fileObj.seek(pos)
    if signature != pngSignature:
        return False, "Image does not begin with the PNG signature."
    return True, None


# -------------------
# layercontents.plist
# -------------------


def layerContentsValidator(value, ufoPathOrFileSystem):
    """
    Check the validity of layercontents.plist.
    Version 3+.
    """
    if isinstance(ufoPathOrFileSystem, fs.base.FS):
        fileSystem = ufoPathOrFileSystem
    else:
        fileSystem = fs.osfs.OSFS(ufoPathOrFileSystem)

    bogusFileMessage = "layercontents.plist in not in the correct format."
    # file isn't in the right format
    if not isinstance(value, list):
        return False, bogusFileMessage
    # work through each entry
    usedLayerNames = set()
    usedDirectories = set()
    contents = {}
    for entry in value:
        # layer entry in the incorrect format
        if not isinstance(entry, list):
            return False, bogusFileMessage
        if not len(entry) == 2:
            return False, bogusFileMessage
        for i in entry:
            if not isinstance(i, str):
                return False, bogusFileMessage
        layerName, directoryName = entry
        # check directory naming
        if directoryName != "glyphs":
            if not directoryName.startswith("glyphs."):
                return (
                    False,
                    "Invalid directory name (%s) in layercontents.plist."
                    % directoryName,
                )
        if len(layerName) == 0:
            return False, "Empty layer name in layercontents.plist."
        # directory doesn't exist
        if not fileSystem.exists(directoryName):
            return False, "A glyphset does not exist at %s." % directoryName
        # default layer name
        if layerName == "public.default" and directoryName != "glyphs":
            return (
                False,
                "The name public.default is being used by a layer that is not the default.",
            )
        # check usage
        if layerName in usedLayerNames:
            return (
                False,
                "The layer name %s is used by more than one layer." % layerName,
            )
        usedLayerNames.add(layerName)
        if directoryName in usedDirectories:
            return (
                False,
                "The directory %s is used by more than one layer." % directoryName,
            )
        usedDirectories.add(directoryName)
        # store
        contents[layerName] = directoryName
    # missing default layer
    foundDefault = "glyphs" in contents.values()
    if not foundDefault:
        return False, "The required default glyph set is not in the UFO."
    return True, None


# ------------
# groups.plist
# ------------


def groupsValidator(value):
    """
    Check the validity of the groups.
    Version 3+ (though it's backwards compatible with UFO 1 and UFO 2).

    >>> groups = {"A" : ["A", "A"], "A2" : ["A"]}
    >>> groupsValidator(groups)
    (True, None)

    >>> groups = {"" : ["A"]}
    >>> valid, msg = groupsValidator(groups)
    >>> valid
    False
    >>> print(msg)
    A group has an empty name.

    >>> groups = {"public.awesome" : ["A"]}
    >>> groupsValidator(groups)
    (True, None)

    >>> groups = {"public.kern1." : ["A"]}
    >>> valid, msg = groupsValidator(groups)
    >>> valid
    False
    >>> print(msg)
    The group data contains a kerning group with an incomplete name.
    >>> groups = {"public.kern2." : ["A"]}
    >>> valid, msg = groupsValidator(groups)
    >>> valid
    False
    >>> print(msg)
    The group data contains a kerning group with an incomplete name.

    >>> groups = {"public.kern1.A" : ["A"], "public.kern2.A" : ["A"]}
    >>> groupsValidator(groups)
    (True, None)

    >>> groups = {"public.kern1.A1" : ["A"], "public.kern1.A2" : ["A"]}
    >>> valid, msg = groupsValidator(groups)
    >>> valid
    False
    >>> print(msg)
    The glyph "A" occurs in too many kerning groups.
    """
    bogusFormatMessage = "The group data is not in the correct format."
    if not isDictEnough(value):
        return False, bogusFormatMessage
    firstSideMapping = {}
    secondSideMapping = {}
    for groupName, glyphList in value.items():
        if not isinstance(groupName, (str)):
            return False, bogusFormatMessage
        if not isinstance(glyphList, (list, tuple)):
            return False, bogusFormatMessage
        if not groupName:
            return False, "A group has an empty name."
        if groupName.startswith("public."):
            if not groupName.startswith("public.kern1.") and not groupName.startswith(
                "public.kern2."
            ):
                # unknown public.* name. silently skip.
                continue
            else:
                if len("public.kernN.") == len(groupName):
                    return (
                        False,
                        "The group data contains a kerning group with an incomplete name.",
                    )
            if groupName.startswith("public.kern1."):
                d = firstSideMapping
            else:
                d = secondSideMapping
            for glyphName in glyphList:
                if not isinstance(glyphName, str):
                    return (
                        False,
                        "The group data %s contains an invalid member." % groupName,
                    )
                if glyphName in d:
                    return (
                        False,
                        'The glyph "%s" occurs in too many kerning groups.' % glyphName,
                    )
                d[glyphName] = groupName
    return True, None


# -------------
# kerning.plist
# -------------


def kerningValidator(data):
    """
    Check the validity of the kerning data structure.
    Version 3+ (though it's backwards compatible with UFO 1 and UFO 2).

    >>> kerning = {"A" : {"B" : 100}}
    >>> kerningValidator(kerning)
    (True, None)

    >>> kerning = {"A" : ["B"]}
    >>> valid, msg = kerningValidator(kerning)
    >>> valid
    False
    >>> print(msg)
    The kerning data is not in the correct format.

    >>> kerning = {"A" : {"B" : "100"}}
    >>> valid, msg = kerningValidator(kerning)
    >>> valid
    False
    >>> print(msg)
    The kerning data is not in the correct format.
    """
    bogusFormatMessage = "The kerning data is not in the correct format."
    if not isinstance(data, Mapping):
        return False, bogusFormatMessage
    for first, secondDict in data.items():
        if not isinstance(first, str):
            return False, bogusFormatMessage
        elif not isinstance(secondDict, Mapping):
            return False, bogusFormatMessage
        for second, value in secondDict.items():
            if not isinstance(second, str):
                return False, bogusFormatMessage
            elif not isinstance(value, numberTypes):
                return False, bogusFormatMessage
    return True, None


# -------------
# lib.plist/lib
# -------------

_bogusLibFormatMessage = "The lib data is not in the correct format: %s"


def fontLibValidator(value):
    """
    Check the validity of the lib.
    Version 3+ (though it's backwards compatible with UFO 1 and UFO 2).

    >>> lib = {"foo" : "bar"}
    >>> fontLibValidator(lib)
    (True, None)

    >>> lib = {"public.awesome" : "hello"}
    >>> fontLibValidator(lib)
    (True, None)

    >>> lib = {"public.glyphOrder" : ["A", "C", "B"]}
    >>> fontLibValidator(lib)
    (True, None)

    >>> lib = "hello"
    >>> valid, msg = fontLibValidator(lib)
    >>> valid
    False
    >>> print(msg)  # doctest: +ELLIPSIS
    The lib data is not in the correct format: expected a dictionary, ...

    >>> lib = {1: "hello"}
    >>> valid, msg = fontLibValidator(lib)
    >>> valid
    False
    >>> print(msg)
    The lib key is not properly formatted: expected str, found int: 1

    >>> lib = {"public.glyphOrder" : "hello"}
    >>> valid, msg = fontLibValidator(lib)
    >>> valid
    False
    >>> print(msg)  # doctest: +ELLIPSIS
    public.glyphOrder is not properly formatted: expected list or tuple,...

    >>> lib = {"public.glyphOrder" : ["A", 1, "B"]}
    >>> valid, msg = fontLibValidator(lib)
    >>> valid
    False
    >>> print(msg)  # doctest: +ELLIPSIS
    public.glyphOrder is not properly formatted: expected str,...
    """
    if not isDictEnough(value):
        reason = "expected a dictionary, found %s" % type(value).__name__
        return False, _bogusLibFormatMessage % reason
    for key, value in value.items():
        if not isinstance(key, str):
            return False, (
                "The lib key is not properly formatted: expected str, found %s: %r"
                % (type(key).__name__, key)
            )
        # public.glyphOrder
        if key == "public.glyphOrder":
            bogusGlyphOrderMessage = "public.glyphOrder is not properly formatted: %s"
            if not isinstance(value, (list, tuple)):
                reason = "expected list or tuple, found %s" % type(value).__name__
                return False, bogusGlyphOrderMessage % reason
            for glyphName in value:
                if not isinstance(glyphName, str):
                    reason = "expected str, found %s" % type(glyphName).__name__
                    return False, bogusGlyphOrderMessage % reason
    return True, None


# --------
# GLIF lib
# --------


def glyphLibValidator(value):
    """
    Check the validity of the lib.
    Version 3+ (though it's backwards compatible with UFO 1 and UFO 2).

    >>> lib = {"foo" : "bar"}
    >>> glyphLibValidator(lib)
    (True, None)

    >>> lib = {"public.awesome" : "hello"}
    >>> glyphLibValidator(lib)
    (True, None)

    >>> lib = {"public.markColor" : "1,0,0,0.5"}
    >>> glyphLibValidator(lib)
    (True, None)

    >>> lib = {"public.markColor" : 1}
    >>> valid, msg = glyphLibValidator(lib)
    >>> valid
    False
    >>> print(msg)
    public.markColor is not properly formatted.
    """
    if not isDictEnough(value):
        reason = "expected a dictionary, found %s" % type(value).__name__
        return False, _bogusLibFormatMessage % reason
    for key, value in value.items():
        if not isinstance(key, str):
            reason = "key (%s) should be a string" % key
            return False, _bogusLibFormatMessage % reason
        # public.markColor
        if key == "public.markColor":
            if not colorValidator(value):
                return False, "public.markColor is not properly formatted."
    return True, None


if __name__ == "__main__":
    import doctest

    doctest.testmod()

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\document.py ===
"""
The `Document` that implements all the text operations/querying.
"""

from __future__ import annotations

import bisect
import re
import string
import weakref
from typing import Callable, Dict, Iterable, List, NoReturn, Pattern, cast

from .clipboard import ClipboardData
from .filters import vi_mode
from .selection import PasteMode, SelectionState, SelectionType

__all__ = [
    "Document",
]


# Regex for finding "words" in documents. (We consider a group of alnum
# characters a word, but also a group of special characters a word, as long as
# it doesn't contain a space.)
# (This is a 'word' in Vi.)
_FIND_WORD_RE = re.compile(r"([a-zA-Z0-9_]+|[^a-zA-Z0-9_\s]+)")
_FIND_CURRENT_WORD_RE = re.compile(r"^([a-zA-Z0-9_]+|[^a-zA-Z0-9_\s]+)")
_FIND_CURRENT_WORD_INCLUDE_TRAILING_WHITESPACE_RE = re.compile(
    r"^(([a-zA-Z0-9_]+|[^a-zA-Z0-9_\s]+)\s*)"
)

# Regex for finding "WORDS" in documents.
# (This is a 'WORD in Vi.)
_FIND_BIG_WORD_RE = re.compile(r"([^\s]+)")
_FIND_CURRENT_BIG_WORD_RE = re.compile(r"^([^\s]+)")
_FIND_CURRENT_BIG_WORD_INCLUDE_TRAILING_WHITESPACE_RE = re.compile(r"^([^\s]+\s*)")

# Share the Document._cache between all Document instances.
# (Document instances are considered immutable. That means that if another
# `Document` is constructed with the same text, it should have the same
# `_DocumentCache`.)
_text_to_document_cache: dict[str, _DocumentCache] = cast(
    Dict[str, "_DocumentCache"],
    weakref.WeakValueDictionary(),  # Maps document.text to DocumentCache instance.
)


class _ImmutableLineList(List[str]):
    """
    Some protection for our 'lines' list, which is assumed to be immutable in the cache.
    (Useful for detecting obvious bugs.)
    """

    def _error(self, *a: object, **kw: object) -> NoReturn:
        raise NotImplementedError("Attempt to modify an immutable list.")

    __setitem__ = _error  # type: ignore
    append = _error
    clear = _error
    extend = _error
    insert = _error
    pop = _error
    remove = _error
    reverse = _error
    sort = _error  # type: ignore


class _DocumentCache:
    def __init__(self) -> None:
        #: List of lines for the Document text.
        self.lines: _ImmutableLineList | None = None

        #: List of index positions, pointing to the start of all the lines.
        self.line_indexes: list[int] | None = None


class Document:
    """
    This is a immutable class around the text and cursor position, and contains
    methods for querying this data, e.g. to give the text before the cursor.

    This class is usually instantiated by a :class:`~prompt_toolkit.buffer.Buffer`
    object, and accessed as the `document` property of that class.

    :param text: string
    :param cursor_position: int
    :param selection: :class:`.SelectionState`
    """

    __slots__ = ("_text", "_cursor_position", "_selection", "_cache")

    def __init__(
        self,
        text: str = "",
        cursor_position: int | None = None,
        selection: SelectionState | None = None,
    ) -> None:
        # Check cursor position. It can also be right after the end. (Where we
        # insert text.)
        assert cursor_position is None or cursor_position <= len(text), AssertionError(
            f"cursor_position={cursor_position!r}, len_text={len(text)!r}"
        )

        # By default, if no cursor position was given, make sure to put the
        # cursor position is at the end of the document. This is what makes
        # sense in most places.
        if cursor_position is None:
            cursor_position = len(text)

        # Keep these attributes private. A `Document` really has to be
        # considered to be immutable, because otherwise the caching will break
        # things. Because of that, we wrap these into read-only properties.
        self._text = text
        self._cursor_position = cursor_position
        self._selection = selection

        # Cache for lines/indexes. (Shared with other Document instances that
        # contain the same text.
        try:
            self._cache = _text_to_document_cache[self.text]
        except KeyError:
            self._cache = _DocumentCache()
            _text_to_document_cache[self.text] = self._cache

        # XX: For some reason, above, we can't use 'WeakValueDictionary.setdefault'.
        #     This fails in Pypy3. `self._cache` becomes None, because that's what
        #     'setdefault' returns.
        # self._cache = _text_to_document_cache.setdefault(self.text, _DocumentCache())
        # assert self._cache

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.text!r}, {self.cursor_position!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Document):
            return False

        return (
            self.text == other.text
            and self.cursor_position == other.cursor_position
            and self.selection == other.selection
        )

    @property
    def text(self) -> str:
        "The document text."
        return self._text

    @property
    def cursor_position(self) -> int:
        "The document cursor position."
        return self._cursor_position

    @property
    def selection(self) -> SelectionState | None:
        ":class:`.SelectionState` object."
        return self._selection

    @property
    def current_char(self) -> str:
        """Return character under cursor or an empty string."""
        return self._get_char_relative_to_cursor(0) or ""

    @property
    def char_before_cursor(self) -> str:
        """Return character before the cursor or an empty string."""
        return self._get_char_relative_to_cursor(-1) or ""

    @property
    def text_before_cursor(self) -> str:
        return self.text[: self.cursor_position :]

    @property
    def text_after_cursor(self) -> str:
        return self.text[self.cursor_position :]

    @property
    def current_line_before_cursor(self) -> str:
        """Text from the start of the line until the cursor."""
        _, _, text = self.text_before_cursor.rpartition("\n")
        return text

    @property
    def current_line_after_cursor(self) -> str:
        """Text from the cursor until the end of the line."""
        text, _, _ = self.text_after_cursor.partition("\n")
        return text

    @property
    def lines(self) -> list[str]:
        """
        Array of all the lines.
        """
        # Cache, because this one is reused very often.
        if self._cache.lines is None:
            self._cache.lines = _ImmutableLineList(self.text.split("\n"))

        return self._cache.lines

    @property
    def _line_start_indexes(self) -> list[int]:
        """
        Array pointing to the start indexes of all the lines.
        """
        # Cache, because this is often reused. (If it is used, it's often used
        # many times. And this has to be fast for editing big documents!)
        if self._cache.line_indexes is None:
            # Create list of line lengths.
            line_lengths = map(len, self.lines)

            # Calculate cumulative sums.
            indexes = [0]
            append = indexes.append
            pos = 0

            for line_length in line_lengths:
                pos += line_length + 1
                append(pos)

            # Remove the last item. (This is not a new line.)
            if len(indexes) > 1:
                indexes.pop()

            self._cache.line_indexes = indexes

        return self._cache.line_indexes

    @property
    def lines_from_current(self) -> list[str]:
        """
        Array of the lines starting from the current line, until the last line.
        """
        return self.lines[self.cursor_position_row :]

    @property
    def line_count(self) -> int:
        r"""Return the number of lines in this document. If the document ends
        with a trailing \n, that counts as the beginning of a new line."""
        return len(self.lines)

    @property
    def current_line(self) -> str:
        """Return the text on the line where the cursor is. (when the input
        consists of just one line, it equals `text`."""
        return self.current_line_before_cursor + self.current_line_after_cursor

    @property
    def leading_whitespace_in_current_line(self) -> str:
        """The leading whitespace in the left margin of the current line."""
        current_line = self.current_line
        length = len(current_line) - len(current_line.lstrip())
        return current_line[:length]

    def _get_char_relative_to_cursor(self, offset: int = 0) -> str:
        """
        Return character relative to cursor position, or empty string
        """
        try:
            return self.text[self.cursor_position + offset]
        except IndexError:
            return ""

    @property
    def on_first_line(self) -> bool:
        """
        True when we are at the first line.
        """
        return self.cursor_position_row == 0

    @property
    def on_last_line(self) -> bool:
        """
        True when we are at the last line.
        """
        return self.cursor_position_row == self.line_count - 1

    @property
    def cursor_position_row(self) -> int:
        """
        Current row. (0-based.)
        """
        row, _ = self._find_line_start_index(self.cursor_position)
        return row

    @property
    def cursor_position_col(self) -> int:
        """
        Current column. (0-based.)
        """
        # (Don't use self.text_before_cursor to calculate this. Creating
        # substrings and doing rsplit is too expensive for getting the cursor
        # position.)
        _, line_start_index = self._find_line_start_index(self.cursor_position)
        return self.cursor_position - line_start_index

    def _find_line_start_index(self, index: int) -> tuple[int, int]:
        """
        For the index of a character at a certain line, calculate the index of
        the first character on that line.

        Return (row, index) tuple.
        """
        indexes = self._line_start_indexes

        pos = bisect.bisect_right(indexes, index) - 1
        return pos, indexes[pos]

    def translate_index_to_position(self, index: int) -> tuple[int, int]:
        """
        Given an index for the text, return the corresponding (row, col) tuple.
        (0-based. Returns (0, 0) for index=0.)
        """
        # Find start of this line.
        row, row_index = self._find_line_start_index(index)
        col = index - row_index

        return row, col

    def translate_row_col_to_index(self, row: int, col: int) -> int:
        """
        Given a (row, col) tuple, return the corresponding index.
        (Row and col params are 0-based.)

        Negative row/col values are turned into zero.
        """
        try:
            result = self._line_start_indexes[row]
            line = self.lines[row]
        except IndexError:
            if row < 0:
                result = self._line_start_indexes[0]
                line = self.lines[0]
            else:
                result = self._line_start_indexes[-1]
                line = self.lines[-1]

        result += max(0, min(col, len(line)))

        # Keep in range. (len(self.text) is included, because the cursor can be
        # right after the end of the text as well.)
        result = max(0, min(result, len(self.text)))
        return result

    @property
    def is_cursor_at_the_end(self) -> bool:
        """True when the cursor is at the end of the text."""
        return self.cursor_position == len(self.text)

    @property
    def is_cursor_at_the_end_of_line(self) -> bool:
        """True when the cursor is at the end of this line."""
        return self.current_char in ("\n", "")

    def has_match_at_current_position(self, sub: str) -> bool:
        """
        `True` when this substring is found at the cursor position.
        """
        return self.text.find(sub, self.cursor_position) == self.cursor_position

    def find(
        self,
        sub: str,
        in_current_line: bool = False,
        include_current_position: bool = False,
        ignore_case: bool = False,
        count: int = 1,
    ) -> int | None:
        """
        Find `text` after the cursor, return position relative to the cursor
        position. Return `None` if nothing was found.

        :param count: Find the n-th occurrence.
        """
        assert isinstance(ignore_case, bool)

        if in_current_line:
            text = self.current_line_after_cursor
        else:
            text = self.text_after_cursor

        if not include_current_position:
            if len(text) == 0:
                return None  # (Otherwise, we always get a match for the empty string.)
            else:
                text = text[1:]

        flags = re.IGNORECASE if ignore_case else 0
        iterator = re.finditer(re.escape(sub), text, flags)

        try:
            for i, match in enumerate(iterator):
                if i + 1 == count:
                    if include_current_position:
                        return match.start(0)
                    else:
                        return match.start(0) + 1
        except StopIteration:
            pass
        return None

    def find_all(self, sub: str, ignore_case: bool = False) -> list[int]:
        """
        Find all occurrences of the substring. Return a list of absolute
        positions in the document.
        """
        flags = re.IGNORECASE if ignore_case else 0
        return [a.start() for a in re.finditer(re.escape(sub), self.text, flags)]

    def find_backwards(
        self,
        sub: str,
        in_current_line: bool = False,
        ignore_case: bool = False,
        count: int = 1,
    ) -> int | None:
        """
        Find `text` before the cursor, return position relative to the cursor
        position. Return `None` if nothing was found.

        :param count: Find the n-th occurrence.
        """
        if in_current_line:
            before_cursor = self.current_line_before_cursor[::-1]
        else:
            before_cursor = self.text_before_cursor[::-1]

        flags = re.IGNORECASE if ignore_case else 0
        iterator = re.finditer(re.escape(sub[::-1]), before_cursor, flags)

        try:
            for i, match in enumerate(iterator):
                if i + 1 == count:
                    return -match.start(0) - len(sub)
        except StopIteration:
            pass
        return None

    def get_word_before_cursor(
        self, WORD: bool = False, pattern: Pattern[str] | None = None
    ) -> str:
        """
        Give the word before the cursor.
        If we have whitespace before the cursor this returns an empty string.

        :param pattern: (None or compiled regex). When given, use this regex
            pattern.
        """
        if self._is_word_before_cursor_complete(WORD=WORD, pattern=pattern):
            # Space before the cursor or no text before cursor.
            return ""

        text_before_cursor = self.text_before_cursor
        start = self.find_start_of_previous_word(WORD=WORD, pattern=pattern) or 0

        return text_before_cursor[len(text_before_cursor) + start :]

    def _is_word_before_cursor_complete(
        self, WORD: bool = False, pattern: Pattern[str] | None = None
    ) -> bool:
        if pattern:
            return self.find_start_of_previous_word(WORD=WORD, pattern=pattern) is None
        else:
            return (
                self.text_before_cursor == "" or self.text_before_cursor[-1:].isspace()
            )

    def find_start_of_previous_word(
        self, count: int = 1, WORD: bool = False, pattern: Pattern[str] | None = None
    ) -> int | None:
        """
        Return an index relative to the cursor position pointing to the start
        of the previous word. Return `None` if nothing was found.

        :param pattern: (None or compiled regex). When given, use this regex
            pattern.
        """
        assert not (WORD and pattern)

        # Reverse the text before the cursor, in order to do an efficient
        # backwards search.
        text_before_cursor = self.text_before_cursor[::-1]

        if pattern:
            regex = pattern
        elif WORD:
            regex = _FIND_BIG_WORD_RE
        else:
            regex = _FIND_WORD_RE

        iterator = regex.finditer(text_before_cursor)

        try:
            for i, match in enumerate(iterator):
                if i + 1 == count:
                    return -match.end(0)
        except StopIteration:
            pass
        return None

    def find_boundaries_of_current_word(
        self,
        WORD: bool = False,
        include_leading_whitespace: bool = False,
        include_trailing_whitespace: bool = False,
    ) -> tuple[int, int]:
        """
        Return the relative boundaries (startpos, endpos) of the current word under the
        cursor. (This is at the current line, because line boundaries obviously
        don't belong to any word.)
        If not on a word, this returns (0,0)
        """
        text_before_cursor = self.current_line_before_cursor[::-1]
        text_after_cursor = self.current_line_after_cursor

        def get_regex(include_whitespace: bool) -> Pattern[str]:
            return {
                (False, False): _FIND_CURRENT_WORD_RE,
                (False, True): _FIND_CURRENT_WORD_INCLUDE_TRAILING_WHITESPACE_RE,
                (True, False): _FIND_CURRENT_BIG_WORD_RE,
                (True, True): _FIND_CURRENT_BIG_WORD_INCLUDE_TRAILING_WHITESPACE_RE,
            }[(WORD, include_whitespace)]

        match_before = get_regex(include_leading_whitespace).search(text_before_cursor)
        match_after = get_regex(include_trailing_whitespace).search(text_after_cursor)

        # When there is a match before and after, and we're not looking for
        # WORDs, make sure that both the part before and after the cursor are
        # either in the [a-zA-Z_] alphabet or not. Otherwise, drop the part
        # before the cursor.
        if not WORD and match_before and match_after:
            c1 = self.text[self.cursor_position - 1]
            c2 = self.text[self.cursor_position]
            alphabet = string.ascii_letters + "0123456789_"

            if (c1 in alphabet) != (c2 in alphabet):
                match_before = None

        return (
            -match_before.end(1) if match_before else 0,
            match_after.end(1) if match_after else 0,
        )

    def get_word_under_cursor(self, WORD: bool = False) -> str:
        """
        Return the word, currently below the cursor.
        This returns an empty string when the cursor is on a whitespace region.
        """
        start, end = self.find_boundaries_of_current_word(WORD=WORD)
        return self.text[self.cursor_position + start : self.cursor_position + end]

    def find_next_word_beginning(
        self, count: int = 1, WORD: bool = False
    ) -> int | None:
        """
        Return an index relative to the cursor position pointing to the start
        of the next word. Return `None` if nothing was found.
        """
        if count < 0:
            return self.find_previous_word_beginning(count=-count, WORD=WORD)

        regex = _FIND_BIG_WORD_RE if WORD else _FIND_WORD_RE
        iterator = regex.finditer(self.text_after_cursor)

        try:
            for i, match in enumerate(iterator):
                # Take first match, unless it's the word on which we're right now.
                if i == 0 and match.start(1) == 0:
                    count += 1

                if i + 1 == count:
                    return match.start(1)
        except StopIteration:
            pass
        return None

    def find_next_word_ending(
        self, include_current_position: bool = False, count: int = 1, WORD: bool = False
    ) -> int | None:
        """
        Return an index relative to the cursor position pointing to the end
        of the next word. Return `None` if nothing was found.
        """
        if count < 0:
            return self.find_previous_word_ending(count=-count, WORD=WORD)

        if include_current_position:
            text = self.text_after_cursor
        else:
            text = self.text_after_cursor[1:]

        regex = _FIND_BIG_WORD_RE if WORD else _FIND_WORD_RE
        iterable = regex.finditer(text)

        try:
            for i, match in enumerate(iterable):
                if i + 1 == count:
                    value = match.end(1)

                    if include_current_position:
                        return value
                    else:
                        return value + 1

        except StopIteration:
            pass
        return None

    def find_previous_word_beginning(
        self, count: int = 1, WORD: bool = False
    ) -> int | None:
        """
        Return an index relative to the cursor position pointing to the start
        of the previous word. Return `None` if nothing was found.
        """
        if count < 0:
            return self.find_next_word_beginning(count=-count, WORD=WORD)

        regex = _FIND_BIG_WORD_RE if WORD else _FIND_WORD_RE
        iterator = regex.finditer(self.text_before_cursor[::-1])

        try:
            for i, match in enumerate(iterator):
                if i + 1 == count:
                    return -match.end(1)
        except StopIteration:
            pass
        return None

    def find_previous_word_ending(
        self, count: int = 1, WORD: bool = False
    ) -> int | None:
        """
        Return an index relative to the cursor position pointing to the end
        of the previous word. Return `None` if nothing was found.
        """
        if count < 0:
            return self.find_next_word_ending(count=-count, WORD=WORD)

        text_before_cursor = self.text_after_cursor[:1] + self.text_before_cursor[::-1]

        regex = _FIND_BIG_WORD_RE if WORD else _FIND_WORD_RE
        iterator = regex.finditer(text_before_cursor)

        try:
            for i, match in enumerate(iterator):
                # Take first match, unless it's the word on which we're right now.
                if i == 0 and match.start(1) == 0:
                    count += 1

                if i + 1 == count:
                    return -match.start(1) + 1
        except StopIteration:
            pass
        return None

    def find_next_matching_line(
        self, match_func: Callable[[str], bool], count: int = 1
    ) -> int | None:
        """
        Look downwards for empty lines.
        Return the line index, relative to the current line.
        """
        result = None

        for index, line in enumerate(self.lines[self.cursor_position_row + 1 :]):
            if match_func(line):
                result = 1 + index
                count -= 1

            if count == 0:
                break

        return result

    def find_previous_matching_line(
        self, match_func: Callable[[str], bool], count: int = 1
    ) -> int | None:
        """
        Look upwards for empty lines.
        Return the line index, relative to the current line.
        """
        result = None

        for index, line in enumerate(self.lines[: self.cursor_position_row][::-1]):
            if match_func(line):
                result = -1 - index
                count -= 1

            if count == 0:
                break

        return result

    def get_cursor_left_position(self, count: int = 1) -> int:
        """
        Relative position for cursor left.
        """
        if count < 0:
            return self.get_cursor_right_position(-count)

        return -min(self.cursor_position_col, count)

    def get_cursor_right_position(self, count: int = 1) -> int:
        """
        Relative position for cursor_right.
        """
        if count < 0:
            return self.get_cursor_left_position(-count)

        return min(count, len(self.current_line_after_cursor))

    def get_cursor_up_position(
        self, count: int = 1, preferred_column: int | None = None
    ) -> int:
        """
        Return the relative cursor position (character index) where we would be if the
        user pressed the arrow-up button.

        :param preferred_column: When given, go to this column instead of
                                 staying at the current column.
        """
        assert count >= 1
        column = (
            self.cursor_position_col if preferred_column is None else preferred_column
        )

        return (
            self.translate_row_col_to_index(
                max(0, self.cursor_position_row - count), column
            )
            - self.cursor_position
        )

    def get_cursor_down_position(
        self, count: int = 1, preferred_column: int | None = None
    ) -> int:
        """
        Return the relative cursor position (character index) where we would be if the
        user pressed the arrow-down button.

        :param preferred_column: When given, go to this column instead of
                                 staying at the current column.
        """
        assert count >= 1
        column = (
            self.cursor_position_col if preferred_column is None else preferred_column
        )

        return (
            self.translate_row_col_to_index(self.cursor_position_row + count, column)
            - self.cursor_position
        )

    def find_enclosing_bracket_right(
        self, left_ch: str, right_ch: str, end_pos: int | None = None
    ) -> int | None:
        """
        Find the right bracket enclosing current position. Return the relative
        position to the cursor position.

        When `end_pos` is given, don't look past the position.
        """
        if self.current_char == right_ch:
            return 0

        if end_pos is None:
            end_pos = len(self.text)
        else:
            end_pos = min(len(self.text), end_pos)

        stack = 1

        # Look forward.
        for i in range(self.cursor_position + 1, end_pos):
            c = self.text[i]

            if c == left_ch:
                stack += 1
            elif c == right_ch:
                stack -= 1

            if stack == 0:
                return i - self.cursor_position

        return None

    def find_enclosing_bracket_left(
        self, left_ch: str, right_ch: str, start_pos: int | None = None
    ) -> int | None:
        """
        Find the left bracket enclosing current position. Return the relative
        position to the cursor position.

        When `start_pos` is given, don't look past the position.
        """
        if self.current_char == left_ch:
            return 0

        if start_pos is None:
            start_pos = 0
        else:
            start_pos = max(0, start_pos)

        stack = 1

        # Look backward.
        for i in range(self.cursor_position - 1, start_pos - 1, -1):
            c = self.text[i]

            if c == right_ch:
                stack += 1
            elif c == left_ch:
                stack -= 1

            if stack == 0:
                return i - self.cursor_position

        return None

    def find_matching_bracket_position(
        self, start_pos: int | None = None, end_pos: int | None = None
    ) -> int:
        """
        Return relative cursor position of matching [, (, { or < bracket.

        When `start_pos` or `end_pos` are given. Don't look past the positions.
        """

        # Look for a match.
        for pair in "()", "[]", "{}", "<>":
            A = pair[0]
            B = pair[1]
            if self.current_char == A:
                return self.find_enclosing_bracket_right(A, B, end_pos=end_pos) or 0
            elif self.current_char == B:
                return self.find_enclosing_bracket_left(A, B, start_pos=start_pos) or 0

        return 0

    def get_start_of_document_position(self) -> int:
        """Relative position for the start of the document."""
        return -self.cursor_position

    def get_end_of_document_position(self) -> int:
        """Relative position for the end of the document."""
        return len(self.text) - self.cursor_position

    def get_start_of_line_position(self, after_whitespace: bool = False) -> int:
        """Relative position for the start of this line."""
        if after_whitespace:
            current_line = self.current_line
            return (
                len(current_line)
                - len(current_line.lstrip())
                - self.cursor_position_col
            )
        else:
            return -len(self.current_line_before_cursor)

    def get_end_of_line_position(self) -> int:
        """Relative position for the end of this line."""
        return len(self.current_line_after_cursor)

    def last_non_blank_of_current_line_position(self) -> int:
        """
        Relative position for the last non blank character of this line.
        """
        return len(self.current_line.rstrip()) - self.cursor_position_col - 1

    def get_column_cursor_position(self, column: int) -> int:
        """
        Return the relative cursor position for this column at the current
        line. (It will stay between the boundaries of the line in case of a
        larger number.)
        """
        line_length = len(self.current_line)
        current_column = self.cursor_position_col
        column = max(0, min(line_length, column))

        return column - current_column

    def selection_range(
        self,
    ) -> tuple[
        int, int
    ]:  # XXX: shouldn't this return `None` if there is no selection???
        """
        Return (from, to) tuple of the selection.
        start and end position are included.

        This doesn't take the selection type into account. Use
        `selection_ranges` instead.
        """
        if self.selection:
            from_, to = sorted(
                [self.cursor_position, self.selection.original_cursor_position]
            )
        else:
            from_, to = self.cursor_position, self.cursor_position

        return from_, to

    def selection_ranges(self) -> Iterable[tuple[int, int]]:
        """
        Return a list of `(from, to)` tuples for the selection or none if
        nothing was selected. The upper boundary is not included.

        This will yield several (from, to) tuples in case of a BLOCK selection.
        This will return zero ranges, like (8,8) for empty lines in a block
        selection.
        """
        if self.selection:
            from_, to = sorted(
                [self.cursor_position, self.selection.original_cursor_position]
            )

            if self.selection.type == SelectionType.BLOCK:
                from_line, from_column = self.translate_index_to_position(from_)
                to_line, to_column = self.translate_index_to_position(to)
                from_column, to_column = sorted([from_column, to_column])
                lines = self.lines

                if vi_mode():
                    to_column += 1

                for l in range(from_line, to_line + 1):
                    line_length = len(lines[l])

                    if from_column <= line_length:
                        yield (
                            self.translate_row_col_to_index(l, from_column),
                            self.translate_row_col_to_index(
                                l, min(line_length, to_column)
                            ),
                        )
            else:
                # In case of a LINES selection, go to the start/end of the lines.
                if self.selection.type == SelectionType.LINES:
                    from_ = max(0, self.text.rfind("\n", 0, from_) + 1)

                    if self.text.find("\n", to) >= 0:
                        to = self.text.find("\n", to)
                    else:
                        to = len(self.text) - 1

                # In Vi mode, the upper boundary is always included. For Emacs,
                # that's not the case.
                if vi_mode():
                    to += 1

                yield from_, to

    def selection_range_at_line(self, row: int) -> tuple[int, int] | None:
        """
        If the selection spans a portion of the given line, return a (from, to) tuple.

        The returned upper boundary is not included in the selection, so
        `(0, 0)` is an empty selection.  `(0, 1)`, is a one character selection.

        Returns None if the selection doesn't cover this line at all.
        """
        if self.selection:
            line = self.lines[row]

            row_start = self.translate_row_col_to_index(row, 0)
            row_end = self.translate_row_col_to_index(row, len(line))

            from_, to = sorted(
                [self.cursor_position, self.selection.original_cursor_position]
            )

            # Take the intersection of the current line and the selection.
            intersection_start = max(row_start, from_)
            intersection_end = min(row_end, to)

            if intersection_start <= intersection_end:
                if self.selection.type == SelectionType.LINES:
                    intersection_start = row_start
                    intersection_end = row_end

                elif self.selection.type == SelectionType.BLOCK:
                    _, col1 = self.translate_index_to_position(from_)
                    _, col2 = self.translate_index_to_position(to)
                    col1, col2 = sorted([col1, col2])

                    if col1 > len(line):
                        return None  # Block selection doesn't cross this line.

                    intersection_start = self.translate_row_col_to_index(row, col1)
                    intersection_end = self.translate_row_col_to_index(row, col2)

                _, from_column = self.translate_index_to_position(intersection_start)
                _, to_column = self.translate_index_to_position(intersection_end)

                # In Vi mode, the upper boundary is always included. For Emacs
                # mode, that's not the case.
                if vi_mode():
                    to_column += 1

                return from_column, to_column
        return None

    def cut_selection(self) -> tuple[Document, ClipboardData]:
        """
        Return a (:class:`.Document`, :class:`.ClipboardData`) tuple, where the
        document represents the new document when the selection is cut, and the
        clipboard data, represents whatever has to be put on the clipboard.
        """
        if self.selection:
            cut_parts = []
            remaining_parts = []
            new_cursor_position = self.cursor_position

            last_to = 0
            for from_, to in self.selection_ranges():
                if last_to == 0:
                    new_cursor_position = from_

                remaining_parts.append(self.text[last_to:from_])
                cut_parts.append(self.text[from_:to])
                last_to = to

            remaining_parts.append(self.text[last_to:])

            cut_text = "\n".join(cut_parts)
            remaining_text = "".join(remaining_parts)

            # In case of a LINES selection, don't include the trailing newline.
            if self.selection.type == SelectionType.LINES and cut_text.endswith("\n"):
                cut_text = cut_text[:-1]

            return (
                Document(text=remaining_text, cursor_position=new_cursor_position),
                ClipboardData(cut_text, self.selection.type),
            )
        else:
            return self, ClipboardData("")

    def paste_clipboard_data(
        self,
        data: ClipboardData,
        paste_mode: PasteMode = PasteMode.EMACS,
        count: int = 1,
    ) -> Document:
        """
        Return a new :class:`.Document` instance which contains the result if
        we would paste this data at the current cursor position.

        :param paste_mode: Where to paste. (Before/after/emacs.)
        :param count: When >1, Paste multiple times.
        """
        before = paste_mode == PasteMode.VI_BEFORE
        after = paste_mode == PasteMode.VI_AFTER

        if data.type == SelectionType.CHARACTERS:
            if after:
                new_text = (
                    self.text[: self.cursor_position + 1]
                    + data.text * count
                    + self.text[self.cursor_position + 1 :]
                )
            else:
                new_text = (
                    self.text_before_cursor + data.text * count + self.text_after_cursor
                )

            new_cursor_position = self.cursor_position + len(data.text) * count
            if before:
                new_cursor_position -= 1

        elif data.type == SelectionType.LINES:
            l = self.cursor_position_row
            if before:
                lines = self.lines[:l] + [data.text] * count + self.lines[l:]
                new_text = "\n".join(lines)
                new_cursor_position = len("".join(self.lines[:l])) + l
            else:
                lines = self.lines[: l + 1] + [data.text] * count + self.lines[l + 1 :]
                new_cursor_position = len("".join(self.lines[: l + 1])) + l + 1
                new_text = "\n".join(lines)

        elif data.type == SelectionType.BLOCK:
            lines = self.lines[:]
            start_line = self.cursor_position_row
            start_column = self.cursor_position_col + (0 if before else 1)

            for i, line in enumerate(data.text.split("\n")):
                index = i + start_line
                if index >= len(lines):
                    lines.append("")

                lines[index] = lines[index].ljust(start_column)
                lines[index] = (
                    lines[index][:start_column]
                    + line * count
                    + lines[index][start_column:]
                )

            new_text = "\n".join(lines)
            new_cursor_position = self.cursor_position + (0 if before else 1)

        return Document(text=new_text, cursor_position=new_cursor_position)

    def empty_line_count_at_the_end(self) -> int:
        """
        Return number of empty lines at the end of the document.
        """
        count = 0
        for line in self.lines[::-1]:
            if not line or line.isspace():
                count += 1
            else:
                break

        return count

    def start_of_paragraph(self, count: int = 1, before: bool = False) -> int:
        """
        Return the start of the current paragraph. (Relative cursor position.)
        """

        def match_func(text: str) -> bool:
            return not text or text.isspace()

        line_index = self.find_previous_matching_line(
            match_func=match_func, count=count
        )

        if line_index:
            add = 0 if before else 1
            return min(0, self.get_cursor_up_position(count=-line_index) + add)
        else:
            return -self.cursor_position

    def end_of_paragraph(self, count: int = 1, after: bool = False) -> int:
        """
        Return the end of the current paragraph. (Relative cursor position.)
        """

        def match_func(text: str) -> bool:
            return not text or text.isspace()

        line_index = self.find_next_matching_line(match_func=match_func, count=count)

        if line_index:
            add = 0 if after else 1
            return max(0, self.get_cursor_down_position(count=line_index) - add)
        else:
            return len(self.text_after_cursor)

    # Modifiers.

    def insert_after(self, text: str) -> Document:
        """
        Create a new document, with this text inserted after the buffer.
        It keeps selection ranges and cursor position in sync.
        """
        return Document(
            text=self.text + text,
            cursor_position=self.cursor_position,
            selection=self.selection,
        )

    def insert_before(self, text: str) -> Document:
        """
        Create a new document, with this text inserted before the buffer.
        It keeps selection ranges and cursor position in sync.
        """
        selection_state = self.selection

        if selection_state:
            selection_state = SelectionState(
                original_cursor_position=selection_state.original_cursor_position
                + len(text),
                type=selection_state.type,
            )

        return Document(
            text=text + self.text,
            cursor_position=self.cursor_position + len(text),
            selection=selection_state,
        )

# === NexusCore/openenv\Lib\site-packages\traitlets\config\loader.py ===
"""A simple configuration system."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import argparse
import copy
import functools
import json
import os
import re
import sys
import typing as t
from logging import Logger

from traitlets.traitlets import Any, Container, Dict, HasTraits, List, TraitType, Undefined

from ..utils import cast_unicode, filefind, warnings

# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------


class ConfigError(Exception):
    pass


class ConfigLoaderError(ConfigError):
    pass


class ConfigFileNotFound(ConfigError):
    pass


class ArgumentError(ConfigLoaderError):
    pass


# -----------------------------------------------------------------------------
# Argparse fix
# -----------------------------------------------------------------------------

# Unfortunately argparse by default prints help messages to stderr instead of
# stdout.  This makes it annoying to capture long help screens at the command
# line, since one must know how to pipe stderr, which many users don't know how
# to do.  So we override the print_help method with one that defaults to
# stdout and use our class instead.


class _Sentinel:
    def __repr__(self) -> str:
        return "<Sentinel deprecated>"

    def __str__(self) -> str:
        return "<deprecated>"


_deprecated = _Sentinel()


class ArgumentParser(argparse.ArgumentParser):
    """Simple argparse subclass that prints help to stdout by default."""

    def print_help(self, file: t.Any = None) -> None:
        if file is None:
            file = sys.stdout
        return super().print_help(file)

    print_help.__doc__ = argparse.ArgumentParser.print_help.__doc__


# -----------------------------------------------------------------------------
# Config class for holding config information
# -----------------------------------------------------------------------------


def execfile(fname: str, glob: dict[str, Any]) -> None:
    with open(fname, "rb") as f:
        exec(compile(f.read(), fname, "exec"), glob, glob)  # noqa: S102


class LazyConfigValue(HasTraits):
    """Proxy object for exposing methods on configurable containers

    These methods allow appending/extending/updating
    to add to non-empty defaults instead of clobbering them.

    Exposes:

    - append, extend, insert on lists
    - update on dicts
    - update, add on sets
    """

    _value = None

    # list methods
    _extend: List[t.Any] = List()
    _prepend: List[t.Any] = List()
    _inserts: List[t.Any] = List()

    def append(self, obj: t.Any) -> None:
        """Append an item to a List"""
        self._extend.append(obj)

    def extend(self, other: t.Any) -> None:
        """Extend a list"""
        self._extend.extend(other)

    def prepend(self, other: t.Any) -> None:
        """like list.extend, but for the front"""
        self._prepend[:0] = other

    def merge_into(self, other: t.Any) -> t.Any:
        """
        Merge with another earlier LazyConfigValue or an earlier container.
        This is useful when having global system-wide configuration files.

        Self is expected to have higher precedence.

        Parameters
        ----------
        other : LazyConfigValue or container

        Returns
        -------
        LazyConfigValue
            if ``other`` is also lazy, a reified container otherwise.
        """
        if isinstance(other, LazyConfigValue):
            other._extend.extend(self._extend)
            self._extend = other._extend

            self._prepend.extend(other._prepend)

            other._inserts.extend(self._inserts)
            self._inserts = other._inserts

            if self._update:
                other.update(self._update)
                self._update = other._update
            return self
        else:
            # other is a container, reify now.
            return self.get_value(other)

    def insert(self, index: int, other: t.Any) -> None:
        if not isinstance(index, int):
            raise TypeError("An integer is required")
        self._inserts.append((index, other))

    # dict methods
    # update is used for both dict and set
    _update = Any()

    def update(self, other: t.Any) -> None:
        """Update either a set or dict"""
        if self._update is None:
            if isinstance(other, dict):
                self._update = {}
            else:
                self._update = set()
        self._update.update(other)

    # set methods
    def add(self, obj: t.Any) -> None:
        """Add an item to a set"""
        self.update({obj})

    def get_value(self, initial: t.Any) -> t.Any:
        """construct the value from the initial one

        after applying any insert / extend / update changes
        """
        if self._value is not None:
            return self._value  # type:ignore[unreachable]
        value = copy.deepcopy(initial)
        if isinstance(value, list):
            for idx, obj in self._inserts:
                value.insert(idx, obj)
            value[:0] = self._prepend
            value.extend(self._extend)

        elif isinstance(value, dict):
            if self._update:
                value.update(self._update)
        elif isinstance(value, set):
            if self._update:
                value.update(self._update)
        self._value = value
        return value

    def to_dict(self) -> dict[str, t.Any]:
        """return JSONable dict form of my data

        Currently update as dict or set, extend, prepend as lists, and inserts as list of tuples.
        """
        d = {}
        if self._update:
            d["update"] = self._update
        if self._extend:
            d["extend"] = self._extend
        if self._prepend:
            d["prepend"] = self._prepend
        elif self._inserts:
            d["inserts"] = self._inserts
        return d

    def __repr__(self) -> str:
        if self._value is not None:
            return f"<{self.__class__.__name__} value={self._value!r}>"
        else:
            return f"<{self.__class__.__name__} {self.to_dict()!r}>"


def _is_section_key(key: str) -> bool:
    """Is a Config key a section name (does it start with a capital)?"""
    return bool(key and key[0].upper() == key[0] and not key.startswith("_"))


class Config(dict):  # type:ignore[type-arg]
    """An attribute-based dict that can do smart merges.

    Accessing a field on a config object for the first time populates the key
    with either a nested Config object for keys starting with capitals
    or :class:`.LazyConfigValue` for lowercase keys,
    allowing quick assignments such as::

        c = Config()
        c.Class.int_trait = 5
        c.Class.list_trait.append("x")

    """

    def __init__(self, *args: t.Any, **kwds: t.Any) -> None:
        dict.__init__(self, *args, **kwds)
        self._ensure_subconfig()

    def _ensure_subconfig(self) -> None:
        """ensure that sub-dicts that should be Config objects are

        casts dicts that are under section keys to Config objects,
        which is necessary for constructing Config objects from dict literals.
        """
        for key in self:
            obj = self[key]
            if _is_section_key(key) and isinstance(obj, dict) and not isinstance(obj, Config):
                setattr(self, key, Config(obj))

    def _merge(self, other: t.Any) -> None:
        """deprecated alias, use Config.merge()"""
        self.merge(other)

    def merge(self, other: t.Any) -> None:
        """merge another config object into this one"""
        to_update = {}
        for k, v in other.items():
            if k not in self:
                to_update[k] = v
            else:  # I have this key
                if isinstance(v, Config) and isinstance(self[k], Config):
                    # Recursively merge common sub Configs
                    self[k].merge(v)
                elif isinstance(v, LazyConfigValue):
                    self[k] = v.merge_into(self[k])
                else:
                    # Plain updates for non-Configs
                    to_update[k] = v

        self.update(to_update)

    def collisions(self, other: Config) -> dict[str, t.Any]:
        """Check for collisions between two config objects.

        Returns a dict of the form {"Class": {"trait": "collision message"}}`,
        indicating which values have been ignored.

        An empty dict indicates no collisions.
        """
        collisions: dict[str, t.Any] = {}
        for section in self:
            if section not in other:
                continue
            mine = self[section]
            theirs = other[section]
            for key in mine:
                if key in theirs and mine[key] != theirs[key]:
                    collisions.setdefault(section, {})
                    collisions[section][key] = f"{mine[key]!r} ignored, using {theirs[key]!r}"
        return collisions

    def __contains__(self, key: t.Any) -> bool:
        # allow nested contains of the form `"Section.key" in config`
        if "." in key:
            first, remainder = key.split(".", 1)
            if first not in self:
                return False
            return remainder in self[first]

        return super().__contains__(key)

    # .has_key is deprecated for dictionaries.
    has_key = __contains__

    def _has_section(self, key: str) -> bool:
        return _is_section_key(key) and key in self

    def copy(self) -> dict[str, t.Any]:
        return type(self)(dict.copy(self))

    def __copy__(self) -> dict[str, t.Any]:
        return self.copy()

    def __deepcopy__(self, memo: t.Any) -> Config:
        new_config = type(self)()
        for key, value in self.items():
            if isinstance(value, (Config, LazyConfigValue)):
                # deep copy config objects
                value = copy.deepcopy(value, memo)
            elif type(value) in {dict, list, set, tuple}:
                # shallow copy plain container traits
                value = copy.copy(value)
            new_config[key] = value
        return new_config

    def __getitem__(self, key: str) -> t.Any:
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            if _is_section_key(key):
                c = Config()
                dict.__setitem__(self, key, c)
                return c
            elif not key.startswith("_"):
                # undefined, create lazy value, used for container methods
                v = LazyConfigValue()
                dict.__setitem__(self, key, v)
                return v
            else:
                raise

    def __setitem__(self, key: str, value: t.Any) -> None:
        if _is_section_key(key):
            if not isinstance(value, Config):
                raise ValueError(
                    "values whose keys begin with an uppercase "
                    f"char must be Config instances: {key!r}, {value!r}"
                )
        dict.__setitem__(self, key, value)

    def __getattr__(self, key: str) -> t.Any:
        if key.startswith("__"):
            return dict.__getattr__(self, key)  # type:ignore[attr-defined]
        try:
            return self.__getitem__(key)
        except KeyError as e:
            raise AttributeError(e) from e

    def __setattr__(self, key: str, value: t.Any) -> None:
        if key.startswith("__"):
            return dict.__setattr__(self, key, value)
        try:
            self.__setitem__(key, value)
        except KeyError as e:
            raise AttributeError(e) from e

    def __delattr__(self, key: str) -> None:
        if key.startswith("__"):
            return dict.__delattr__(self, key)
        try:
            dict.__delitem__(self, key)
        except KeyError as e:
            raise AttributeError(e) from e


class DeferredConfig:
    """Class for deferred-evaluation of config from CLI"""

    def get_value(self, trait: TraitType[t.Any, t.Any]) -> t.Any:
        raise NotImplementedError("Implement in subclasses")

    def _super_repr(self) -> str:
        # explicitly call super on direct parent
        return super(self.__class__, self).__repr__()


class DeferredConfigString(str, DeferredConfig):
    """Config value for loading config from a string

    Interpretation is deferred until it is loaded into the trait.

    Subclass of str for backward compatibility.

    This class is only used for values that are not listed
    in the configurable classes.

    When config is loaded, `trait.from_string` will be used.

    If an error is raised in `.from_string`,
    the original string is returned.

    .. versionadded:: 5.0
    """

    def get_value(self, trait: TraitType[t.Any, t.Any]) -> t.Any:
        """Get the value stored in this string"""
        s = str(self)
        try:
            return trait.from_string(s)
        except Exception:
            # exception casting from string,
            # let the original string lie.
            # this will raise a more informative error when config is loaded.
            return s

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._super_repr()})"


class DeferredConfigList(t.List[t.Any], DeferredConfig):
    """Config value for loading config from a list of strings

    Interpretation is deferred until it is loaded into the trait.

    This class is only used for values that are not listed
    in the configurable classes.

    When config is loaded, `trait.from_string_list` will be used.

    If an error is raised in `.from_string_list`,
    the original string list is returned.

    .. versionadded:: 5.0
    """

    def get_value(self, trait: TraitType[t.Any, t.Any]) -> t.Any:
        """Get the value stored in this string"""
        if hasattr(trait, "from_string_list"):
            src = list(self)
            cast = trait.from_string_list
        else:
            # only allow one item
            if len(self) > 1:
                raise ValueError(
                    f"{trait.name} only accepts one value, got {len(self)}: {list(self)}"
                )
            src = self[0]
            cast = trait.from_string

        try:
            return cast(src)
        except Exception:
            # exception casting from string,
            # let the original value lie.
            # this will raise a more informative error when config is loaded.
            return src

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._super_repr()})"


# -----------------------------------------------------------------------------
# Config loading classes
# -----------------------------------------------------------------------------


class ConfigLoader:
    """A object for loading configurations from just about anywhere.

    The resulting configuration is packaged as a :class:`Config`.

    Notes
    -----
    A :class:`ConfigLoader` does one thing: load a config from a source
    (file, command line arguments) and returns the data as a :class:`Config` object.
    There are lots of things that :class:`ConfigLoader` does not do.  It does
    not implement complex logic for finding config files.  It does not handle
    default values or merge multiple configs.  These things need to be
    handled elsewhere.
    """

    def _log_default(self) -> Logger:
        from traitlets.log import get_logger

        return t.cast(Logger, get_logger())

    def __init__(self, log: Logger | None = None) -> None:
        """A base class for config loaders.

        log : instance of :class:`logging.Logger` to use.
              By default logger of :meth:`traitlets.config.application.Application.instance()`
              will be used

        Examples
        --------
        >>> cl = ConfigLoader()
        >>> config = cl.load_config()
        >>> config
        {}
        """
        self.clear()
        if log is None:
            self.log = self._log_default()
            self.log.debug("Using default logger")
        else:
            self.log = log

    def clear(self) -> None:
        self.config = Config()

    def load_config(self) -> Config:
        """Load a config from somewhere, return a :class:`Config` instance.

        Usually, this will cause self.config to be set and then returned.
        However, in most cases, :meth:`ConfigLoader.clear` should be called
        to erase any previous state.
        """
        self.clear()
        return self.config


class FileConfigLoader(ConfigLoader):
    """A base class for file based configurations.

    As we add more file based config loaders, the common logic should go
    here.
    """

    def __init__(self, filename: str, path: str | None = None, **kw: t.Any) -> None:
        """Build a config loader for a filename and path.

        Parameters
        ----------
        filename : str
            The file name of the config file.
        path : str, list, tuple
            The path to search for the config file on, or a sequence of
            paths to try in order.
        """
        super().__init__(**kw)
        self.filename = filename
        self.path = path
        self.full_filename = ""

    def _find_file(self) -> None:
        """Try to find the file by searching the paths."""
        self.full_filename = filefind(self.filename, self.path)


class JSONFileConfigLoader(FileConfigLoader):
    """A JSON file loader for config

    Can also act as a context manager that rewrite the configuration file to disk on exit.

    Example::

        with JSONFileConfigLoader('myapp.json','/home/jupyter/configurations/') as c:
            c.MyNewConfigurable.new_value = 'Updated'

    """

    def load_config(self) -> Config:
        """Load the config from a file and return it as a Config object."""
        self.clear()
        try:
            self._find_file()
        except OSError as e:
            raise ConfigFileNotFound(str(e)) from e
        dct = self._read_file_as_dict()
        self.config = self._convert_to_config(dct)
        return self.config

    def _read_file_as_dict(self) -> dict[str, t.Any]:
        with open(self.full_filename) as f:
            return t.cast("dict[str, t.Any]", json.load(f))

    def _convert_to_config(self, dictionary: dict[str, t.Any]) -> Config:
        if "version" in dictionary:
            version = dictionary.pop("version")
        else:
            version = 1

        if version == 1:
            return Config(dictionary)
        else:
            raise ValueError(f"Unknown version of JSON config file: {version}")

    def __enter__(self) -> Config:
        self.load_config()
        return self.config

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """
        Exit the context manager but do not handle any errors.

        In case of any error, we do not want to write the potentially broken
        configuration to disk.
        """
        self.config.version = 1
        json_config = json.dumps(self.config, indent=2)
        with open(self.full_filename, "w") as f:
            f.write(json_config)


class PyFileConfigLoader(FileConfigLoader):
    """A config loader for pure python files.

    This is responsible for locating a Python config file by filename and
    path, then executing it to construct a Config object.
    """

    def load_config(self) -> Config:
        """Load the config from a file and return it as a Config object."""
        self.clear()
        try:
            self._find_file()
        except OSError as e:
            raise ConfigFileNotFound(str(e)) from e
        self._read_file_as_dict()
        return self.config

    def load_subconfig(self, fname: str, path: str | None = None) -> None:
        """Injected into config file namespace as load_subconfig"""
        if path is None:
            path = self.path

        loader = self.__class__(fname, path)
        try:
            sub_config = loader.load_config()
        except ConfigFileNotFound:
            # Pass silently if the sub config is not there,
            # treat it as an empty config file.
            pass
        else:
            self.config.merge(sub_config)

    def _read_file_as_dict(self) -> None:
        """Load the config file into self.config, with recursive loading."""

        def get_config() -> Config:
            """Unnecessary now, but a deprecation warning is more trouble than it's worth."""
            return self.config

        namespace = dict(  # noqa: C408
            c=self.config,
            load_subconfig=self.load_subconfig,
            get_config=get_config,
            __file__=self.full_filename,
        )
        conf_filename = self.full_filename
        with open(conf_filename, "rb") as f:
            exec(compile(f.read(), conf_filename, "exec"), namespace, namespace)  # noqa: S102


class CommandLineConfigLoader(ConfigLoader):
    """A config loader for command line arguments.

    As we add more command line based loaders, the common logic should go
    here.
    """

    def _exec_config_str(
        self, lhs: t.Any, rhs: t.Any, trait: TraitType[t.Any, t.Any] | None = None
    ) -> None:
        """execute self.config.<lhs> = <rhs>

        * expands ~ with expanduser
        * interprets value with trait if available
        """
        value = rhs
        if isinstance(value, DeferredConfig):
            if trait:
                # trait available, reify config immediately
                value = value.get_value(trait)
            elif isinstance(rhs, DeferredConfigList) and len(rhs) == 1:
                # single item, make it a deferred str
                value = DeferredConfigString(os.path.expanduser(rhs[0]))
        else:
            if trait:
                value = trait.from_string(value)
            else:
                value = DeferredConfigString(value)

        *path, key = lhs.split(".")
        section = self.config
        for part in path:
            section = section[part]
        section[key] = value
        return

    def _load_flag(self, cfg: t.Any) -> None:
        """update self.config from a flag, which can be a dict or Config"""
        if isinstance(cfg, (dict, Config)):
            # don't clobber whole config sections, update
            # each section from config:
            for sec, c in cfg.items():
                self.config[sec].update(c)
        else:
            raise TypeError("Invalid flag: %r" % cfg)


# match --Class.trait keys for argparse
# matches:
# --Class.trait
# --x
# -x

class_trait_opt_pattern = re.compile(r"^\-?\-[A-Za-z][\w]*(\.[\w]+)*$")

_DOT_REPLACEMENT = "__DOT__"
_DASH_REPLACEMENT = "__DASH__"


class _KVAction(argparse.Action):
    """Custom argparse action for handling --Class.trait=x

    Always
    """

    def __call__(  # type:ignore[override]
        self,
        parser: argparse.ArgumentParser,
        namespace: dict[str, t.Any],
        values: t.Sequence[t.Any],
        option_string: str | None = None,
    ) -> None:
        if isinstance(values, str):
            values = [values]
        values = ["-" if v is _DASH_REPLACEMENT else v for v in values]
        items = getattr(namespace, self.dest, None)
        if items is None:
            items = DeferredConfigList()
        else:
            items = DeferredConfigList(items)
        items.extend(values)
        setattr(namespace, self.dest, items)


class _DefaultOptionDict(dict):  # type:ignore[type-arg]
    """Like the default options dict

    but acts as if all --Class.trait options are predefined
    """

    def _add_kv_action(self, key: str) -> None:
        self[key] = _KVAction(
            option_strings=[key],
            dest=key.lstrip("-").replace(".", _DOT_REPLACEMENT),
            # use metavar for display purposes
            metavar=key.lstrip("-"),
        )

    def __contains__(self, key: t.Any) -> bool:
        if "=" in key:
            return False
        if super().__contains__(key):
            return True

        if key.startswith("-") and class_trait_opt_pattern.match(key):
            self._add_kv_action(key)
            return True
        return False

    def __getitem__(self, key: str) -> t.Any:
        if key in self:
            return super().__getitem__(key)
        else:
            raise KeyError(key)

    def get(self, key: str, default: t.Any = None) -> t.Any:
        try:
            return self[key]
        except KeyError:
            return default


class _KVArgParser(argparse.ArgumentParser):
    """subclass of ArgumentParser where any --Class.trait option is implicitly defined"""

    def parse_known_args(  # type:ignore[override]
        self, args: t.Sequence[str] | None = None, namespace: argparse.Namespace | None = None
    ) -> tuple[argparse.Namespace | None, list[str]]:
        # must be done immediately prior to parsing because if we do it in init,
        # registration of explicit actions via parser.add_option will fail during setup
        for container in (self, self._optionals):
            container._option_string_actions = _DefaultOptionDict(container._option_string_actions)
        return super().parse_known_args(args, namespace)


# type aliases
SubcommandsDict = t.Dict[str, t.Any]


class ArgParseConfigLoader(CommandLineConfigLoader):
    """A loader that uses the argparse module to load from the command line."""

    parser_class = ArgumentParser

    def __init__(
        self,
        argv: list[str] | None = None,
        aliases: dict[str, str] | None = None,
        flags: dict[str, str] | None = None,
        log: t.Any = None,
        classes: list[type[t.Any]] | None = None,
        subcommands: SubcommandsDict | None = None,
        *parser_args: t.Any,
        **parser_kw: t.Any,
    ) -> None:
        """Create a config loader for use with argparse.

        Parameters
        ----------
        classes : optional, list
            The classes to scan for *container* config-traits and decide
            for their "multiplicity" when adding them as *argparse* arguments.
        argv : optional, list
            If given, used to read command-line arguments from, otherwise
            sys.argv[1:] is used.
        *parser_args : tuple
            A tuple of positional arguments that will be passed to the
            constructor of :class:`argparse.ArgumentParser`.
        **parser_kw : dict
            A tuple of keyword arguments that will be passed to the
            constructor of :class:`argparse.ArgumentParser`.
        aliases : dict of str to str
            Dict of aliases to full traitlets names for CLI parsing
        flags : dict of str to str
            Dict of flags to full traitlets names for CLI parsing
        log
            Passed to `ConfigLoader`

        Returns
        -------
        config : Config
            The resulting Config object.
        """
        classes = classes or []
        super(CommandLineConfigLoader, self).__init__(log=log)
        self.clear()
        if argv is None:
            argv = sys.argv[1:]
        self.argv = argv
        self.aliases = aliases or {}
        self.flags = flags or {}
        self.classes = classes
        self.subcommands = subcommands  # only used for argcomplete currently

        self.parser_args = parser_args
        self.version = parser_kw.pop("version", None)
        kwargs = dict(argument_default=argparse.SUPPRESS)  # noqa: C408
        kwargs.update(parser_kw)
        self.parser_kw = kwargs

    def load_config(
        self,
        argv: list[str] | None = None,
        aliases: t.Any = None,
        flags: t.Any = _deprecated,
        classes: t.Any = None,
    ) -> Config:
        """Parse command line arguments and return as a Config object.

        Parameters
        ----------
        argv : optional, list
            If given, a list with the structure of sys.argv[1:] to parse
            arguments from. If not given, the instance's self.argv attribute
            (given at construction time) is used.
        flags
            Deprecated in traitlets 5.0, instantiate the config loader with the flags.

        """

        if flags is not _deprecated:
            warnings.warn(
                "The `flag` argument to load_config is deprecated since Traitlets "
                f"5.0 and will be ignored, pass flags the `{type(self)}` constructor.",
                DeprecationWarning,
                stacklevel=2,
            )

        self.clear()
        if argv is None:
            argv = self.argv
        if aliases is not None:
            self.aliases = aliases
        if classes is not None:
            self.classes = classes
        self._create_parser()
        self._argcomplete(self.classes, self.subcommands)
        self._parse_args(argv)
        self._convert_to_config()
        return self.config

    def get_extra_args(self) -> list[str]:
        if hasattr(self, "extra_args"):
            return self.extra_args
        else:
            return []

    def _create_parser(self) -> None:
        self.parser = self.parser_class(
            *self.parser_args,
            **self.parser_kw,  # type:ignore[arg-type]
        )
        self._add_arguments(self.aliases, self.flags, self.classes)

    def _add_arguments(self, aliases: t.Any, flags: t.Any, classes: t.Any) -> None:
        raise NotImplementedError("subclasses must implement _add_arguments")

    def _argcomplete(self, classes: list[t.Any], subcommands: SubcommandsDict | None) -> None:
        """If argcomplete is enabled, allow triggering command-line autocompletion"""

    def _parse_args(self, args: t.Any) -> t.Any:
        """self.parser->self.parsed_data"""
        uargs = [cast_unicode(a) for a in args]

        unpacked_aliases: dict[str, str] = {}
        if self.aliases:
            unpacked_aliases = {}
            for alias, alias_target in self.aliases.items():
                if alias in self.flags:
                    continue
                if not isinstance(alias, tuple):  # type:ignore[unreachable]
                    alias = (alias,)  # type:ignore[assignment]
                for al in alias:
                    if len(al) == 1:
                        unpacked_aliases["-" + al] = "--" + alias_target
                    unpacked_aliases["--" + al] = "--" + alias_target

        def _replace(arg: str) -> str:
            if arg == "-":
                return _DASH_REPLACEMENT
            for k, v in unpacked_aliases.items():
                if arg == k:
                    return v
                if arg.startswith(k + "="):
                    return v + "=" + arg[len(k) + 1 :]
            return arg

        if "--" in uargs:
            idx = uargs.index("--")
            extra_args = uargs[idx + 1 :]
            to_parse = uargs[:idx]
        else:
            extra_args = []
            to_parse = uargs
        to_parse = [_replace(a) for a in to_parse]

        self.parsed_data = self.parser.parse_args(to_parse)
        self.extra_args = extra_args

    def _convert_to_config(self) -> None:
        """self.parsed_data->self.config"""
        for k, v in vars(self.parsed_data).items():
            *path, key = k.split(".")
            section = self.config
            for p in path:
                section = section[p]
            setattr(section, key, v)


class _FlagAction(argparse.Action):
    """ArgParse action to handle a flag"""

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        self.flag = kwargs.pop("flag")
        self.alias = kwargs.pop("alias", None)
        kwargs["const"] = Undefined
        if not self.alias:
            kwargs["nargs"] = 0
        super().__init__(*args, **kwargs)

    def __call__(
        self, parser: t.Any, namespace: t.Any, values: t.Any, option_string: str | None = None
    ) -> None:
        if self.nargs == 0 or values is Undefined:
            if not hasattr(namespace, "_flags"):
                namespace._flags = []
            namespace._flags.append(self.flag)
        else:
            setattr(namespace, self.alias, values)


class KVArgParseConfigLoader(ArgParseConfigLoader):
    """A config loader that loads aliases and flags with argparse,

    as well as arbitrary --Class.trait value
    """

    parser_class = _KVArgParser  # type:ignore[assignment]

    def _add_arguments(self, aliases: t.Any, flags: t.Any, classes: t.Any) -> None:
        alias_flags: dict[str, t.Any] = {}
        argparse_kwds: dict[str, t.Any]
        argparse_traits: dict[str, t.Any]
        paa = self.parser.add_argument
        self.parser.set_defaults(_flags=[])
        paa("extra_args", nargs="*")

        # An index of all container traits collected::
        #
        #     { <traitname>: (<trait>, <argparse-kwds>) }
        #
        #  Used to add the correct type into the `config` tree.
        #  Used also for aliases, not to re-collect them.
        self.argparse_traits = argparse_traits = {}
        for cls in classes:
            for traitname, trait in cls.class_traits(config=True).items():
                argname = f"{cls.__name__}.{traitname}"
                argparse_kwds = {"type": str}
                if isinstance(trait, (Container, Dict)):
                    multiplicity = trait.metadata.get("multiplicity", "append")
                    if multiplicity == "append":
                        argparse_kwds["action"] = multiplicity
                    else:
                        argparse_kwds["nargs"] = multiplicity
                argparse_traits[argname] = (trait, argparse_kwds)

        for keys, (value, fhelp) in flags.items():
            if not isinstance(keys, tuple):
                keys = (keys,)
            for key in keys:
                if key in aliases:
                    alias_flags[aliases[key]] = value
                    continue
                keys = ("-" + key, "--" + key) if len(key) == 1 else ("--" + key,)
                paa(*keys, action=_FlagAction, flag=value, help=fhelp)

        for keys, traitname in aliases.items():
            if not isinstance(keys, tuple):
                keys = (keys,)

            for key in keys:
                argparse_kwds = {
                    "type": str,
                    "dest": traitname.replace(".", _DOT_REPLACEMENT),
                    "metavar": traitname,
                }
                argcompleter = None
                if traitname in argparse_traits:
                    trait, kwds = argparse_traits[traitname]
                    argparse_kwds.update(kwds)
                    if "action" in argparse_kwds and traitname in alias_flags:
                        # flag sets 'action', so can't have flag & alias with custom action
                        # on the same name
                        raise ArgumentError(
                            f"The alias `{key}` for the 'append' sequence "
                            f"config-trait `{traitname}` cannot be also a flag!'"
                        )
                    # For argcomplete, check if any either an argcompleter metadata tag or method
                    # is available. If so, it should be a callable which takes the command-line key
                    # string as an argument and other kwargs passed by argcomplete,
                    # and returns the a list of string completions.
                    argcompleter = trait.metadata.get("argcompleter") or getattr(
                        trait, "argcompleter", None
                    )
                if traitname in alias_flags:
                    # alias and flag.
                    # when called with 0 args: flag
                    # when called with >= 1: alias
                    argparse_kwds.setdefault("nargs", "?")
                    argparse_kwds["action"] = _FlagAction
                    argparse_kwds["flag"] = alias_flags[traitname]
                    argparse_kwds["alias"] = traitname
                keys = ("-" + key, "--" + key) if len(key) == 1 else ("--" + key,)
                action = paa(*keys, **argparse_kwds)
                if argcompleter is not None:
                    # argcomplete's completers are callables returning list of completion strings
                    action.completer = functools.partial(  # type:ignore[attr-defined]
                        argcompleter, key=key
                    )

    def _convert_to_config(self) -> None:
        """self.parsed_data->self.config, parse unrecognized extra args via KVLoader."""
        extra_args = self.extra_args

        for lhs, rhs in vars(self.parsed_data).items():
            if lhs == "extra_args":
                self.extra_args = ["-" if a == _DASH_REPLACEMENT else a for a in rhs] + extra_args
                continue
            if lhs == "_flags":
                # _flags will be handled later
                continue

            lhs = lhs.replace(_DOT_REPLACEMENT, ".")
            if "." not in lhs:
                self._handle_unrecognized_alias(lhs)
                trait = None

            if isinstance(rhs, list):
                rhs = DeferredConfigList(rhs)
            elif isinstance(rhs, str):
                rhs = DeferredConfigString(rhs)

            trait = self.argparse_traits.get(lhs)
            if trait:
                trait = trait[0]

            # eval the KV assignment
            try:
                self._exec_config_str(lhs, rhs, trait)
            except Exception as e:
                # cast deferred to nicer repr for the error
                # DeferredList->list, etc
                if isinstance(rhs, DeferredConfig):
                    rhs = rhs._super_repr()
                raise ArgumentError(f"Error loading argument {lhs}={rhs}, {e}") from e

        for subc in self.parsed_data._flags:
            self._load_flag(subc)

    def _handle_unrecognized_alias(self, arg: str) -> None:
        """Handling for unrecognized alias arguments

        Probably a mistyped alias. By default just log a warning,
        but users can override this to raise an error instead, e.g.
        self.parser.error("Unrecognized alias: '%s'" % arg)
        """
        self.log.warning("Unrecognized alias: '%s', it will have no effect.", arg)

    def _argcomplete(self, classes: list[t.Any], subcommands: SubcommandsDict | None) -> None:
        """If argcomplete is enabled, allow triggering command-line autocompletion"""
        try:
            import argcomplete  # noqa: F401
        except ImportError:
            return

        from . import argcomplete_config

        finder = argcomplete_config.ExtendedCompletionFinder()  # type:ignore[no-untyped-call]
        finder.config_classes = classes
        finder.subcommands = list(subcommands or [])
        # for ease of testing, pass through self._argcomplete_kwargs if set
        finder(self.parser, **getattr(self, "_argcomplete_kwargs", {}))


class KeyValueConfigLoader(KVArgParseConfigLoader):
    """Deprecated in traitlets 5.0

    Use KVArgParseConfigLoader
    """

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        warnings.warn(
            "KeyValueConfigLoader is deprecated since Traitlets 5.0."
            " Use KVArgParseConfigLoader instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


def load_pyconfig_files(config_files: list[str], path: str) -> Config:
    """Load multiple Python config files, merging each of them in turn.

    Parameters
    ----------
    config_files : list of str
        List of config files names to load and merge into the config.
    path : unicode
        The full path to the location of the config files.
    """
    config = Config()
    for cf in config_files:
        loader = PyFileConfigLoader(cf, path=path)
        try:
            next_config = loader.load_config()
        except ConfigFileNotFound:
            pass
        except Exception:
            raise
        else:
            config.merge(next_config)
    return config