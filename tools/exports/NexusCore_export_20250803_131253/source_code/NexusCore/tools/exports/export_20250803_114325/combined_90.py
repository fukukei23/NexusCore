
# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_process_net_command_json.py ===
import itertools
import json
import linecache
import os
import platform
import sys
from functools import partial

import pydevd_file_utils
from _pydev_bundle import pydev_log
from _pydevd_bundle._debug_adapter import pydevd_base_schema, pydevd_schema
from _pydevd_bundle._debug_adapter.pydevd_schema import (
    CompletionsResponseBody,
    EvaluateResponseBody,
    ExceptionOptions,
    GotoTargetsResponseBody,
    ModulesResponseBody,
    ProcessEventBody,
    ProcessEvent,
    Scope,
    ScopesResponseBody,
    SetExpressionResponseBody,
    SetVariableResponseBody,
    SourceBreakpoint,
    SourceResponseBody,
    VariablesResponseBody,
    SetBreakpointsResponseBody,
    Response,
    Capabilities,
    PydevdAuthorizeRequest,
    Request,
    StepInTargetsResponseBody,
    SetFunctionBreakpointsResponseBody,
    BreakpointEvent,
    BreakpointEventBody,
    InitializedEvent,
)
from _pydevd_bundle.pydevd_api import PyDevdAPI
from _pydevd_bundle.pydevd_breakpoints import get_exception_class, FunctionBreakpoint
from _pydevd_bundle.pydevd_comm_constants import (
    CMD_PROCESS_EVENT,
    CMD_RETURN,
    CMD_SET_NEXT_STATEMENT,
    CMD_STEP_INTO,
    CMD_STEP_INTO_MY_CODE,
    CMD_STEP_OVER,
    CMD_STEP_OVER_MY_CODE,
    file_system_encoding,
    CMD_STEP_RETURN_MY_CODE,
    CMD_STEP_RETURN,
)
from _pydevd_bundle.pydevd_filtering import ExcludeFilter
from _pydevd_bundle.pydevd_json_debug_options import _extract_debug_options, DebugOptions
from _pydevd_bundle.pydevd_net_command import NetCommand
from _pydevd_bundle.pydevd_utils import convert_dap_log_message_to_expression, ScopeRequest
from _pydevd_bundle.pydevd_constants import PY_IMPL_NAME, DebugInfoHolder, PY_VERSION_STR, PY_IMPL_VERSION_STR, IS_64BIT_PROCESS
from _pydevd_bundle.pydevd_trace_dispatch import USING_CYTHON
from _pydevd_frame_eval.pydevd_frame_eval_main import USING_FRAME_EVAL
from _pydevd_bundle.pydevd_comm import internal_get_step_in_targets_json
from _pydevd_bundle.pydevd_additional_thread_info import set_additional_thread_info
from _pydevd_bundle.pydevd_thread_lifecycle import pydevd_find_thread_by_id


def _convert_rules_to_exclude_filters(rules, on_error):
    exclude_filters = []
    if not isinstance(rules, list):
        on_error('Invalid "rules" (expected list of dicts). Found: %s' % (rules,))

    else:
        directory_exclude_filters = []
        module_exclude_filters = []
        glob_exclude_filters = []

        for rule in rules:
            if not isinstance(rule, dict):
                on_error('Invalid "rules" (expected list of dicts). Found: %s' % (rules,))
                continue

            include = rule.get("include")
            if include is None:
                on_error('Invalid "rule" (expected dict with "include"). Found: %s' % (rule,))
                continue

            path = rule.get("path")
            module = rule.get("module")
            if path is None and module is None:
                on_error('Invalid "rule" (expected dict with "path" or "module"). Found: %s' % (rule,))
                continue

            if path is not None:
                glob_pattern = path
                if "*" not in path and "?" not in path:
                    if os.path.isdir(glob_pattern):
                        # If a directory was specified, add a '/**'
                        # to be consistent with the glob pattern required
                        # by pydevd.
                        if not glob_pattern.endswith("/") and not glob_pattern.endswith("\\"):
                            glob_pattern += "/"
                        glob_pattern += "**"
                    directory_exclude_filters.append(ExcludeFilter(glob_pattern, not include, True))
                else:
                    glob_exclude_filters.append(ExcludeFilter(glob_pattern, not include, True))

            elif module is not None:
                module_exclude_filters.append(ExcludeFilter(module, not include, False))

            else:
                on_error("Internal error: expected path or module to be specified.")

        # Note that we have to sort the directory/module exclude filters so that the biggest
        # paths match first.
        # i.e.: if we have:
        # /sub1/sub2/sub3
        # a rule with /sub1/sub2 would match before a rule only with /sub1.
        directory_exclude_filters = sorted(directory_exclude_filters, key=lambda exclude_filter: -len(exclude_filter.name))
        module_exclude_filters = sorted(module_exclude_filters, key=lambda exclude_filter: -len(exclude_filter.name))
        exclude_filters = directory_exclude_filters + glob_exclude_filters + module_exclude_filters

    return exclude_filters


class IDMap(object):
    def __init__(self):
        self._value_to_key = {}
        self._key_to_value = {}
        self._next_id = partial(next, itertools.count(0))

    def obtain_value(self, key):
        return self._key_to_value[key]

    def obtain_key(self, value):
        try:
            key = self._value_to_key[value]
        except KeyError:
            key = self._next_id()
            self._key_to_value[key] = value
            self._value_to_key[value] = key
        return key


class PyDevJsonCommandProcessor(object):
    def __init__(self, from_json):
        self.from_json = from_json
        self.api = PyDevdAPI()
        self._options = DebugOptions()
        self._next_breakpoint_id = partial(next, itertools.count(0))
        self._goto_targets_map = IDMap()
        self._launch_or_attach_request_done = False

    def process_net_command_json(self, py_db, json_contents, send_response=True):
        """
        Processes a debug adapter protocol json command.
        """

        DEBUG = False

        try:
            if isinstance(json_contents, bytes):
                json_contents = json_contents.decode("utf-8")

            request = self.from_json(json_contents, update_ids_from_dap=True)
        except Exception as e:
            try:
                loaded_json = json.loads(json_contents)
                request = Request(loaded_json.get("command", "<unknown>"), loaded_json["seq"])
            except:
                # There's not much we can do in this case...
                pydev_log.exception("Error loading json: %s", json_contents)
                return

            error_msg = str(e)
            if error_msg.startswith("'") and error_msg.endswith("'"):
                error_msg = error_msg[1:-1]

            # This means a failure processing the request (but we were able to load the seq,
            # so, answer with a failure response).
            def on_request(py_db, request):
                error_response = {
                    "type": "response",
                    "request_seq": request.seq,
                    "success": False,
                    "command": request.command,
                    "message": error_msg,
                }
                return NetCommand(CMD_RETURN, 0, error_response, is_json=True)

        else:
            if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 1:
                pydev_log.info(
                    "Process %s: %s\n"
                    % (
                        request.__class__.__name__,
                        json.dumps(request.to_dict(update_ids_to_dap=True), indent=4, sort_keys=True),
                    )
                )

            assert request.type == "request"
            method_name = "on_%s_request" % (request.command.lower(),)
            on_request = getattr(self, method_name, None)
            if on_request is None:
                print("Unhandled: %s not available in PyDevJsonCommandProcessor.\n" % (method_name,))
                return

            if DEBUG:
                print("Handled in pydevd: %s (in PyDevJsonCommandProcessor).\n" % (method_name,))

        with py_db._main_lock:
            if request.__class__ == PydevdAuthorizeRequest:
                authorize_request = request  # : :type authorize_request: PydevdAuthorizeRequest
                access_token = authorize_request.arguments.debugServerAccessToken
                py_db.authentication.login(access_token)

            if not py_db.authentication.is_authenticated():
                response = Response(request.seq, success=False, command=request.command, message="Client not authenticated.", body={})
                cmd = NetCommand(CMD_RETURN, 0, response, is_json=True)
                py_db.writer.add_command(cmd)
                return

            cmd = on_request(py_db, request)
            if cmd is not None and send_response:
                py_db.writer.add_command(cmd)

    def on_pydevdauthorize_request(self, py_db, request):
        client_access_token = py_db.authentication.client_access_token
        body = {"clientAccessToken": None}
        if client_access_token:
            body["clientAccessToken"] = client_access_token

        response = pydevd_base_schema.build_response(request, kwargs={"body": body})
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_initialize_request(self, py_db, request):
        body = Capabilities(
            # Supported.
            supportsConfigurationDoneRequest=True,
            supportsConditionalBreakpoints=True,
            supportsHitConditionalBreakpoints=True,
            supportsEvaluateForHovers=True,
            supportsSetVariable=True,
            supportsGotoTargetsRequest=True,
            supportsCompletionsRequest=True,
            supportsModulesRequest=True,
            supportsExceptionOptions=True,
            supportsValueFormattingOptions=True,
            supportsExceptionInfoRequest=True,
            supportTerminateDebuggee=True,
            supportsDelayedStackTraceLoading=True,
            supportsLogPoints=True,
            supportsSetExpression=True,
            supportsTerminateRequest=True,
            supportsClipboardContext=True,
            supportsFunctionBreakpoints=True,
            exceptionBreakpointFilters=[
                {"filter": "raised", "label": "Raised Exceptions", "default": False},
                {"filter": "uncaught", "label": "Uncaught Exceptions", "default": True},
                {"filter": "userUnhandled", "label": "User Uncaught Exceptions", "default": False},
            ],
            # Not supported.
            supportsStepBack=False,
            supportsRestartFrame=False,
            supportsStepInTargetsRequest=True,
            supportsRestartRequest=False,
            supportsLoadedSourcesRequest=False,
            supportsTerminateThreadsRequest=False,
            supportsDataBreakpoints=False,
            supportsReadMemoryRequest=False,
            supportsDisassembleRequest=False,
            additionalModuleColumns=[],
            completionTriggerCharacters=[],
            supportedChecksumAlgorithms=[],
        ).to_dict()

        # Non-standard capabilities/info below.
        body["supportsDebuggerProperties"] = True

        body["pydevd"] = pydevd_info = {}
        pydevd_info["processId"] = os.getpid()
        self.api.notify_initialize(py_db)
        response = pydevd_base_schema.build_response(request, kwargs={"body": body})
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_configurationdone_request(self, py_db, request):
        """
        :param ConfigurationDoneRequest request:
        """
        if not self._launch_or_attach_request_done:
            pydev_log.critical("Missing launch request or attach request before configuration done request.")

        self.api.run(py_db)
        self.api.notify_configuration_done(py_db)

        configuration_done_response = pydevd_base_schema.build_response(request)
        return NetCommand(CMD_RETURN, 0, configuration_done_response, is_json=True)

    def on_threads_request(self, py_db, request):
        """
        :param ThreadsRequest request:
        """
        return self.api.list_threads(py_db, request.seq)

    def on_terminate_request(self, py_db, request):
        """
        :param TerminateRequest request:
        """
        self._request_terminate_process(py_db)
        response = pydevd_base_schema.build_response(request)
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def _request_terminate_process(self, py_db):
        self.api.request_terminate_process(py_db)

    def on_completions_request(self, py_db, request):
        """
        :param CompletionsRequest request:
        """
        arguments = request.arguments  # : :type arguments: CompletionsArguments
        seq = request.seq
        text = arguments.text
        frame_id = arguments.frameId
        thread_id = py_db.suspended_frames_manager.get_thread_id_for_variable_reference(frame_id)

        if thread_id is None:
            body = CompletionsResponseBody([])
            variables_response = pydevd_base_schema.build_response(
                request, kwargs={"body": body, "success": False, "message": "Thread to get completions seems to have resumed already."}
            )
            return NetCommand(CMD_RETURN, 0, variables_response, is_json=True)

        # Note: line and column are 1-based (convert to 0-based for pydevd).
        column = arguments.column - 1

        if arguments.line is None:
            # line is optional
            line = -1
        else:
            line = arguments.line - 1

        self.api.request_completions(py_db, seq, thread_id, frame_id, text, line=line, column=column)

    def _resolve_remote_root(self, local_root, remote_root):
        if remote_root == ".":
            cwd = os.getcwd()
            append_pathsep = local_root.endswith("\\") or local_root.endswith("/")
            return cwd + (os.path.sep if append_pathsep else "")
        return remote_root

    def _set_debug_options(self, py_db, args, start_reason):
        rules = args.get("rules")
        stepping_resumes_all_threads = args.get("steppingResumesAllThreads", True)
        self.api.set_stepping_resumes_all_threads(py_db, stepping_resumes_all_threads)

        terminate_child_processes = args.get("terminateChildProcesses", True)
        self.api.set_terminate_child_processes(py_db, terminate_child_processes)

        terminate_keyboard_interrupt = args.get("onTerminate", "kill") == "KeyboardInterrupt"
        self.api.set_terminate_keyboard_interrupt(py_db, terminate_keyboard_interrupt)

        variable_presentation = args.get("variablePresentation", None)
        if isinstance(variable_presentation, dict):

            def get_variable_presentation(setting, default):
                value = variable_presentation.get(setting, default)
                if value not in ("group", "inline", "hide"):
                    pydev_log.info(
                        'The value set for "%s" (%s) in the variablePresentation is not valid. Valid values are: "group", "inline", "hide"'
                        % (
                            setting,
                            value,
                        )
                    )
                    value = default

                return value

            default = get_variable_presentation("all", "group")

            special_presentation = get_variable_presentation("special", default)
            function_presentation = get_variable_presentation("function", default)
            class_presentation = get_variable_presentation("class", default)
            protected_presentation = get_variable_presentation("protected", default)

            self.api.set_variable_presentation(
                py_db,
                self.api.VariablePresentation(special_presentation, function_presentation, class_presentation, protected_presentation),
            )

        exclude_filters = []

        if rules is not None:
            exclude_filters = _convert_rules_to_exclude_filters(rules, lambda msg: self.api.send_error_message(py_db, msg))

        self.api.set_exclude_filters(py_db, exclude_filters)

        debug_options = _extract_debug_options(
            args.get("options"),
            args.get("debugOptions"),
        )
        self._options.update_fom_debug_options(debug_options)
        self._options.update_from_args(args)

        self.api.set_use_libraries_filter(py_db, self._options.just_my_code)

        if self._options.client_os:
            self.api.set_ide_os(self._options.client_os)

        path_mappings = []
        for pathMapping in args.get("pathMappings", []):
            localRoot = pathMapping.get("localRoot", "")
            remoteRoot = pathMapping.get("remoteRoot", "")
            remoteRoot = self._resolve_remote_root(localRoot, remoteRoot)
            if (localRoot != "") and (remoteRoot != ""):
                path_mappings.append((localRoot, remoteRoot))

        if bool(path_mappings):
            pydevd_file_utils.setup_client_server_paths(path_mappings)

        resolve_symlinks = args.get("resolveSymlinks", None)
        if resolve_symlinks is not None:
            pydevd_file_utils.set_resolve_symlinks(resolve_symlinks)

        redirecting = args.get("isOutputRedirected")
        if self._options.redirect_output:
            py_db.enable_output_redirection(True, True)
            redirecting = True
        else:
            py_db.enable_output_redirection(False, False)

        py_db.is_output_redirected = redirecting

        self.api.set_show_return_values(py_db, self._options.show_return_value)

        if not self._options.break_system_exit_zero:
            ignore_system_exit_codes = [0, None]
            if self._options.django_debug or self._options.flask_debug:
                ignore_system_exit_codes += [3]

            self.api.set_ignore_system_exit_codes(py_db, ignore_system_exit_codes)

        auto_reload = args.get("autoReload", {})
        if not isinstance(auto_reload, dict):
            pydev_log.info("Expected autoReload to be a dict. Received: %s" % (auto_reload,))
            auto_reload = {}

        enable_auto_reload = auto_reload.get("enable", False)
        watch_dirs = auto_reload.get("watchDirectories")
        if not watch_dirs:
            watch_dirs = []
            # Note: by default this is no longer done because on some cases there are entries in the PYTHONPATH
            # such as the home directory or /python/x64, where the site packages are in /python/x64/libs, so,
            # we only watch the current working directory as well as executed script.
            # check = getattr(sys, 'path', [])[:]
            # # By default only watch directories that are in the project roots /
            # # program dir (if available), sys.argv[0], as well as the current dir (we don't want to
            # # listen to the whole site-packages by default as it can be huge).
            # watch_dirs = [pydevd_file_utils.absolute_path(w) for w in check]
            # watch_dirs = [w for w in watch_dirs if py_db.in_project_roots_filename_uncached(w) and os.path.isdir(w)]

            program = args.get("program")
            if program:
                if os.path.isdir(program):
                    watch_dirs.append(program)
                else:
                    watch_dirs.append(os.path.dirname(program))
            watch_dirs.append(os.path.abspath("."))

            argv = getattr(sys, "argv", [])
            if argv:
                f = argv[0]
                if f:  # argv[0] could be None (https://github.com/microsoft/debugpy/issues/987)
                    if os.path.isdir(f):
                        watch_dirs.append(f)
                    else:
                        watch_dirs.append(os.path.dirname(f))

        if not isinstance(watch_dirs, (list, set, tuple)):
            watch_dirs = (watch_dirs,)
        new_watch_dirs = set()
        for w in watch_dirs:
            try:
                new_watch_dirs.add(pydevd_file_utils.get_path_with_real_case(pydevd_file_utils.absolute_path(w)))
            except Exception:
                pydev_log.exception("Error adding watch dir: %s", w)
        watch_dirs = new_watch_dirs

        poll_target_time = auto_reload.get("pollingInterval", 1)
        exclude_patterns = auto_reload.get(
            "exclude", ("**/.git/**", "**/__pycache__/**", "**/node_modules/**", "**/.metadata/**", "**/site-packages/**")
        )
        include_patterns = auto_reload.get("include", ("**/*.py", "**/*.pyw"))
        self.api.setup_auto_reload_watcher(py_db, enable_auto_reload, watch_dirs, poll_target_time, exclude_patterns, include_patterns)

        if self._options.stop_on_entry and start_reason == "launch":
            self.api.stop_on_entry()

        self.api.set_gui_event_loop(py_db, self._options.gui_event_loop)

    def _send_process_event(self, py_db, start_method):
        argv = getattr(sys, "argv", [])
        if len(argv) > 0:
            name = argv[0]
        else:
            name = ""

        if isinstance(name, bytes):
            name = name.decode(file_system_encoding, "replace")
            name = name.encode("utf-8")

        body = ProcessEventBody(
            name=name,
            systemProcessId=os.getpid(),
            isLocalProcess=True,
            startMethod=start_method,
        )
        event = ProcessEvent(body)
        py_db.writer.add_command(NetCommand(CMD_PROCESS_EVENT, 0, event, is_json=True))

    def _handle_launch_or_attach_request(self, py_db, request, start_reason):
        self._send_process_event(py_db, start_reason)
        self._launch_or_attach_request_done = True
        self.api.set_enable_thread_notifications(py_db, True)
        self._set_debug_options(py_db, request.arguments.kwargs, start_reason=start_reason)
        response = pydevd_base_schema.build_response(request)

        initialized_event = InitializedEvent()
        py_db.writer.add_command(NetCommand(CMD_RETURN, 0, initialized_event, is_json=True))
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_launch_request(self, py_db, request):
        """
        :param LaunchRequest request:
        """
        return self._handle_launch_or_attach_request(py_db, request, start_reason="launch")

    def on_attach_request(self, py_db, request):
        """
        :param AttachRequest request:
        """
        return self._handle_launch_or_attach_request(py_db, request, start_reason="attach")

    def on_pause_request(self, py_db, request):
        """
        :param PauseRequest request:
        """
        arguments = request.arguments  # : :type arguments: PauseArguments
        thread_id = arguments.threadId

        self.api.request_suspend_thread(py_db, thread_id=thread_id)

        response = pydevd_base_schema.build_response(request)
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_continue_request(self, py_db, request):
        """
        :param ContinueRequest request:
        """
        arguments = request.arguments  # : :type arguments: ContinueArguments
        thread_id = arguments.threadId

        def on_resumed():
            body = {"allThreadsContinued": thread_id == "*"}
            response = pydevd_base_schema.build_response(request, kwargs={"body": body})
            cmd = NetCommand(CMD_RETURN, 0, response, is_json=True)
            py_db.writer.add_command(cmd)

        if py_db.multi_threads_single_notification:
            # Only send resumed notification when it has actually resumed!
            # (otherwise the user could send a continue, receive the notification and then
            # request a new pause which would be paused without sending any notification as
            # it didn't really run in the first place).
            py_db.threads_suspended_single_notification.add_on_resumed_callback(on_resumed)
            self.api.request_resume_thread(thread_id)
        else:
            # Only send resumed notification when it has actually resumed!
            # (otherwise the user could send a continue, receive the notification and then
            # request a new pause which would be paused without sending any notification as
            # it didn't really run in the first place).
            self.api.request_resume_thread(thread_id)
            on_resumed()

    def on_next_request(self, py_db, request):
        """
        :param NextRequest request:
        """
        arguments = request.arguments  # : :type arguments: NextArguments
        thread_id = arguments.threadId

        if py_db.get_use_libraries_filter():
            step_cmd_id = CMD_STEP_OVER_MY_CODE
        else:
            step_cmd_id = CMD_STEP_OVER

        self.api.request_step(py_db, thread_id, step_cmd_id)

        response = pydevd_base_schema.build_response(request)
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_stepin_request(self, py_db, request):
        """
        :param StepInRequest request:
        """
        arguments = request.arguments  # : :type arguments: StepInArguments
        thread_id = arguments.threadId

        target_id = arguments.targetId
        if target_id is not None:
            thread = pydevd_find_thread_by_id(thread_id)
            if thread is None:
                response = Response(
                    request_seq=request.seq,
                    success=False,
                    command=request.command,
                    message="Unable to find thread from thread_id: %s" % (thread_id,),
                    body={},
                )
                return NetCommand(CMD_RETURN, 0, response, is_json=True)

            info = set_additional_thread_info(thread)
            target_id_to_smart_step_into_variant = info.target_id_to_smart_step_into_variant
            if not target_id_to_smart_step_into_variant:
                variables_response = pydevd_base_schema.build_response(
                    request, kwargs={"success": False, "message": "Unable to step into target (no targets are saved in the thread info)."}
                )
                return NetCommand(CMD_RETURN, 0, variables_response, is_json=True)

            variant = target_id_to_smart_step_into_variant.get(target_id)
            if variant is not None:
                parent = variant.parent
                if parent is not None:
                    self.api.request_smart_step_into(py_db, request.seq, thread_id, parent.offset, variant.offset)
                else:
                    self.api.request_smart_step_into(py_db, request.seq, thread_id, variant.offset, -1)
            else:
                variables_response = pydevd_base_schema.build_response(
                    request,
                    kwargs={
                        "success": False,
                        "message": "Unable to find step into target %s. Available targets: %s"
                        % (target_id, target_id_to_smart_step_into_variant),
                    },
                )
                return NetCommand(CMD_RETURN, 0, variables_response, is_json=True)

        else:
            if py_db.get_use_libraries_filter():
                step_cmd_id = CMD_STEP_INTO_MY_CODE
            else:
                step_cmd_id = CMD_STEP_INTO

            self.api.request_step(py_db, thread_id, step_cmd_id)

        response = pydevd_base_schema.build_response(request)
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_stepintargets_request(self, py_db, request):
        """
        :param StepInTargetsRequest request:
        """
        frame_id = request.arguments.frameId
        thread_id = py_db.suspended_frames_manager.get_thread_id_for_variable_reference(frame_id)

        if thread_id is None:
            body = StepInTargetsResponseBody([])
            variables_response = pydevd_base_schema.build_response(
                request,
                kwargs={
                    "body": body,
                    "success": False,
                    "message": "Unable to get thread_id from frame_id (thread to get step in targets seems to have resumed already).",
                },
            )
            return NetCommand(CMD_RETURN, 0, variables_response, is_json=True)

        py_db.post_method_as_internal_command(
            thread_id, internal_get_step_in_targets_json, request.seq, thread_id, frame_id, request, set_additional_thread_info
        )

    def on_stepout_request(self, py_db, request):
        """
        :param StepOutRequest request:
        """
        arguments = request.arguments  # : :type arguments: StepOutArguments
        thread_id = arguments.threadId

        if py_db.get_use_libraries_filter():
            step_cmd_id = CMD_STEP_RETURN_MY_CODE
        else:
            step_cmd_id = CMD_STEP_RETURN

        self.api.request_step(py_db, thread_id, step_cmd_id)

        response = pydevd_base_schema.build_response(request)
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def _get_hit_condition_expression(self, hit_condition):
        """Following hit condition values are supported

        * x or == x when breakpoint is hit x times
        * >= x when breakpoint is hit more than or equal to x times
        * % x when breakpoint is hit multiple of x times

        Returns '@HIT@ == x' where @HIT@ will be replaced by number of hits
        """
        if not hit_condition:
            return None

        expr = hit_condition.strip()
        try:
            int(expr)
            return "@HIT@ == {}".format(expr)
        except ValueError:
            pass

        if expr.startswith("%"):
            return "@HIT@ {} == 0".format(expr)

        if expr.startswith("==") or expr.startswith(">") or expr.startswith("<"):
            return "@HIT@ {}".format(expr)

        return hit_condition

    def on_disconnect_request(self, py_db, request):
        """
        :param DisconnectRequest request:
        """
        if request.arguments.terminateDebuggee:
            self._request_terminate_process(py_db)
            response = pydevd_base_schema.build_response(request)
            return NetCommand(CMD_RETURN, 0, response, is_json=True)

        self._launch_or_attach_request_done = False
        py_db.enable_output_redirection(False, False)
        self.api.request_disconnect(py_db, resume_threads=True)

        response = pydevd_base_schema.build_response(request)
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def _verify_launch_or_attach_done(self, request):
        if not self._launch_or_attach_request_done:
            # Note that to validate the breakpoints we need the launch request to be done already
            # (otherwise the filters wouldn't be set for the breakpoint validation).
            if request.command == "setFunctionBreakpoints":
                body = SetFunctionBreakpointsResponseBody([])
            else:
                body = SetBreakpointsResponseBody([])
            response = pydevd_base_schema.build_response(
                request,
                kwargs={"body": body, "success": False, "message": "Breakpoints may only be set after the launch request is received."},
            )
            return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_setfunctionbreakpoints_request(self, py_db, request):
        """
        :param SetFunctionBreakpointsRequest request:
        """
        response = self._verify_launch_or_attach_done(request)
        if response is not None:
            return response

        arguments = request.arguments  # : :type arguments: SetFunctionBreakpointsArguments
        function_breakpoints = []
        suspend_policy = "ALL" if py_db.multi_threads_single_notification else "NONE"

        # Not currently covered by the DAP.
        is_logpoint = False
        expression = None

        breakpoints_set = []
        arguments.breakpoints = arguments.breakpoints or []
        for bp in arguments.breakpoints:
            hit_condition = self._get_hit_condition_expression(bp.get("hitCondition"))
            condition = bp.get("condition")

            function_breakpoints.append(FunctionBreakpoint(bp["name"], condition, expression, suspend_policy, hit_condition, is_logpoint))

            # Note: always succeeds.
            breakpoints_set.append(pydevd_schema.Breakpoint(verified=True, id=self._next_breakpoint_id()).to_dict())

        self.api.set_function_breakpoints(py_db, function_breakpoints)

        body = {"breakpoints": breakpoints_set}
        set_breakpoints_response = pydevd_base_schema.build_response(request, kwargs={"body": body})
        return NetCommand(CMD_RETURN, 0, set_breakpoints_response, is_json=True)

    def on_setbreakpoints_request(self, py_db, request):
        """
        :param SetBreakpointsRequest request:
        """
        response = self._verify_launch_or_attach_done(request)
        if response is not None:
            return response

        arguments = request.arguments  # : :type arguments: SetBreakpointsArguments
        # TODO: Path is optional here it could be source reference.
        filename = self.api.filename_to_str(arguments.source.path)
        func_name = "None"

        self.api.remove_all_breakpoints(py_db, filename)

        btype = "python-line"
        suspend_policy = "ALL" if py_db.multi_threads_single_notification else "NONE"

        if not filename.lower().endswith(".py"):  # Note: check based on original file, not mapping.
            if self._options.django_debug:
                btype = "django-line"
            elif self._options.flask_debug:
                btype = "jinja2-line"

        breakpoints_set = []
        arguments.breakpoints = arguments.breakpoints or []
        for source_breakpoint in arguments.breakpoints:
            source_breakpoint = SourceBreakpoint(**source_breakpoint)
            line = source_breakpoint.line
            condition = source_breakpoint.condition
            breakpoint_id = self._next_breakpoint_id()

            hit_condition = self._get_hit_condition_expression(source_breakpoint.hitCondition)
            log_message = source_breakpoint.logMessage
            if not log_message:
                is_logpoint = None
                expression = None
            else:
                is_logpoint = True
                expression = convert_dap_log_message_to_expression(log_message)

            on_changed_breakpoint_state = partial(self._on_changed_breakpoint_state, py_db, arguments.source)
            result = self.api.add_breakpoint(
                py_db,
                filename,
                btype,
                breakpoint_id,
                line,
                condition,
                func_name,
                expression,
                suspend_policy,
                hit_condition,
                is_logpoint,
                adjust_line=True,
                on_changed_breakpoint_state=on_changed_breakpoint_state,
            )

            bp = self._create_breakpoint_from_add_breakpoint_result(py_db, arguments.source, breakpoint_id, result)
            breakpoints_set.append(bp)

        body = {"breakpoints": breakpoints_set}
        set_breakpoints_response = pydevd_base_schema.build_response(request, kwargs={"body": body})
        return NetCommand(CMD_RETURN, 0, set_breakpoints_response, is_json=True)

    def _on_changed_breakpoint_state(self, py_db, source, breakpoint_id, result):
        bp = self._create_breakpoint_from_add_breakpoint_result(py_db, source, breakpoint_id, result)
        body = BreakpointEventBody(
            reason="changed",
            breakpoint=bp,
        )
        event = BreakpointEvent(body)
        event_id = 0  # Actually ignored in this case
        py_db.writer.add_command(NetCommand(event_id, 0, event, is_json=True))

    def _create_breakpoint_from_add_breakpoint_result(self, py_db, source, breakpoint_id, result):
        error_code = result.error_code

        if error_code:
            if error_code == self.api.ADD_BREAKPOINT_FILE_NOT_FOUND:
                error_msg = "Breakpoint in file that does not exist."

            elif error_code == self.api.ADD_BREAKPOINT_FILE_EXCLUDED_BY_FILTERS:
                error_msg = "Breakpoint in file excluded by filters."
                if py_db.get_use_libraries_filter():
                    error_msg += (
                        '\nNote: may be excluded because of "justMyCode" option (default == true).'
                        'Try setting "justMyCode": false in the debug configuration (e.g., launch.json).\n'
                    )

            elif error_code == self.api.ADD_BREAKPOINT_LAZY_VALIDATION:
                error_msg = "Waiting for code to be loaded to verify breakpoint."

            elif error_code == self.api.ADD_BREAKPOINT_INVALID_LINE:
                error_msg = "Breakpoint added to invalid line."

            else:
                # Shouldn't get here.
                error_msg = "Breakpoint not validated (reason unknown -- please report as bug)."

            return pydevd_schema.Breakpoint(
                verified=False, id=breakpoint_id, line=result.translated_line, message=error_msg, source=source
            ).to_dict()
        else:
            return pydevd_schema.Breakpoint(verified=True, id=breakpoint_id, line=result.translated_line, source=source).to_dict()

    def on_setexceptionbreakpoints_request(self, py_db, request):
        """
        :param SetExceptionBreakpointsRequest request:
        """
        # : :type arguments: SetExceptionBreakpointsArguments
        arguments = request.arguments
        filters = arguments.filters
        exception_options = arguments.exceptionOptions
        self.api.remove_all_exception_breakpoints(py_db)

        # Can't set these in the DAP.
        condition = None
        expression = None
        notify_on_first_raise_only = False

        ignore_libraries = 1 if py_db.get_use_libraries_filter() else 0

        if exception_options:
            break_raised = False
            break_uncaught = False

            for option in exception_options:
                option = ExceptionOptions(**option)
                if not option.path:
                    continue

                # never: never breaks
                #
                # always: always breaks
                #
                # unhandled: breaks when exception unhandled
                #
                # userUnhandled: breaks if the exception is not handled by user code

                notify_on_handled_exceptions = 1 if option.breakMode == "always" else 0
                notify_on_unhandled_exceptions = 1 if option.breakMode == "unhandled" else 0
                notify_on_user_unhandled_exceptions = 1 if option.breakMode == "userUnhandled" else 0
                exception_paths = option.path
                break_raised |= notify_on_handled_exceptions
                break_uncaught |= notify_on_unhandled_exceptions

                exception_names = []
                if len(exception_paths) == 0:
                    continue

                elif len(exception_paths) == 1:
                    if "Python Exceptions" in exception_paths[0]["names"]:
                        exception_names = ["BaseException"]

                else:
                    path_iterator = iter(exception_paths)
                    if "Python Exceptions" in next(path_iterator)["names"]:
                        for path in path_iterator:
                            for ex_name in path["names"]:
                                exception_names.append(ex_name)

                for exception_name in exception_names:
                    self.api.add_python_exception_breakpoint(
                        py_db,
                        exception_name,
                        condition,
                        expression,
                        notify_on_handled_exceptions,
                        notify_on_unhandled_exceptions,
                        notify_on_user_unhandled_exceptions,
                        notify_on_first_raise_only,
                        ignore_libraries,
                    )

        else:
            break_raised = "raised" in filters
            break_uncaught = "uncaught" in filters
            break_user = "userUnhandled" in filters
            if break_raised or break_uncaught or break_user:
                notify_on_handled_exceptions = 1 if break_raised else 0
                notify_on_unhandled_exceptions = 1 if break_uncaught else 0
                notify_on_user_unhandled_exceptions = 1 if break_user else 0
                exception = "BaseException"

                self.api.add_python_exception_breakpoint(
                    py_db,
                    exception,
                    condition,
                    expression,
                    notify_on_handled_exceptions,
                    notify_on_unhandled_exceptions,
                    notify_on_user_unhandled_exceptions,
                    notify_on_first_raise_only,
                    ignore_libraries,
                )

        if break_raised:
            btype = None
            if self._options.django_debug:
                btype = "django"
            elif self._options.flask_debug:
                btype = "jinja2"

            if btype:
                self.api.add_plugins_exception_breakpoint(py_db, btype, "BaseException")  # Note: Exception name could be anything here.

        # Note: no body required on success.
        set_breakpoints_response = pydevd_base_schema.build_response(request)
        return NetCommand(CMD_RETURN, 0, set_breakpoints_response, is_json=True)

    def on_stacktrace_request(self, py_db, request):
        """
        :param StackTraceRequest request:
        """
        # : :type stack_trace_arguments: StackTraceArguments
        stack_trace_arguments = request.arguments
        thread_id = stack_trace_arguments.threadId

        if stack_trace_arguments.startFrame:
            start_frame = int(stack_trace_arguments.startFrame)
        else:
            start_frame = 0

        if stack_trace_arguments.levels:
            levels = int(stack_trace_arguments.levels)
        else:
            levels = 0

        fmt = stack_trace_arguments.format
        if hasattr(fmt, "to_dict"):
            fmt = fmt.to_dict()
        self.api.request_stack(py_db, request.seq, thread_id, fmt=fmt, start_frame=start_frame, levels=levels)

    def on_exceptioninfo_request(self, py_db, request):
        """
        :param ExceptionInfoRequest request:
        """
        # : :type exception_into_arguments: ExceptionInfoArguments
        exception_into_arguments = request.arguments
        thread_id = exception_into_arguments.threadId
        max_frames = self._options.max_exception_stack_frames
        thread = pydevd_find_thread_by_id(thread_id)
        if thread is not None:
            self.api.request_exception_info_json(py_db, request, thread_id, thread, max_frames)
        else:
            response = Response(
                request_seq=request.seq,
                success=False,
                command=request.command,
                message="Unable to find thread from thread_id: %s" % (thread_id,),
                body={},
            )
            return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_scopes_request(self, py_db, request):
        """
        Scopes are the top-level items which appear for a frame (so, we receive the frame id
        and provide the scopes it has).

        :param ScopesRequest request:
        """
        frame_id = request.arguments.frameId

        variables_reference = frame_id
        scopes = [
            Scope("Locals", ScopeRequest(int(variables_reference), "locals"), False, presentationHint="locals"),
            Scope("Globals", ScopeRequest(int(variables_reference), "globals"), False),
        ]
        body = ScopesResponseBody(scopes)
        scopes_response = pydevd_base_schema.build_response(request, kwargs={"body": body})
        return NetCommand(CMD_RETURN, 0, scopes_response, is_json=True)

    def on_evaluate_request(self, py_db, request):
        """
        :param EvaluateRequest request:
        """
        # : :type arguments: EvaluateArguments
        arguments = request.arguments

        if arguments.frameId is None:
            self.api.request_exec_or_evaluate_json(py_db, request, thread_id="*")
        else:
            thread_id = py_db.suspended_frames_manager.get_thread_id_for_variable_reference(arguments.frameId)

            if thread_id is not None:
                self.api.request_exec_or_evaluate_json(py_db, request, thread_id)
            else:
                body = EvaluateResponseBody("", 0)
                response = pydevd_base_schema.build_response(
                    request, kwargs={"body": body, "success": False, "message": "Unable to find thread for evaluation."}
                )
                return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_setexpression_request(self, py_db, request):
        # : :type arguments: SetExpressionArguments
        arguments = request.arguments

        thread_id = py_db.suspended_frames_manager.get_thread_id_for_variable_reference(arguments.frameId)

        if thread_id is not None:
            self.api.request_set_expression_json(py_db, request, thread_id)
        else:
            body = SetExpressionResponseBody("")
            response = pydevd_base_schema.build_response(
                request, kwargs={"body": body, "success": False, "message": "Unable to find thread to set expression."}
            )
            return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_variables_request(self, py_db, request):
        """
        Variables can be asked whenever some place returned a variables reference (so, it
        can be a scope gotten from on_scopes_request, the result of some evaluation, etc.).

        Note that in the DAP the variables reference requires a unique int... the way this works for
        pydevd is that an instance is generated for that specific variable reference and we use its
        id(instance) to identify it to make sure all items are unique (and the actual {id->instance}
        is added to a dict which is only valid while the thread is suspended and later cleared when
        the related thread resumes execution).

        see: SuspendedFramesManager

        :param VariablesRequest request:
        """
        arguments = request.arguments  # : :type arguments: VariablesArguments
        variables_reference = arguments.variablesReference

        if isinstance(variables_reference, ScopeRequest):
            variables_reference = variables_reference.variable_reference

        thread_id = py_db.suspended_frames_manager.get_thread_id_for_variable_reference(variables_reference)
        if thread_id is not None:
            self.api.request_get_variable_json(py_db, request, thread_id)
        else:
            variables = []
            body = VariablesResponseBody(variables)
            variables_response = pydevd_base_schema.build_response(
                request, kwargs={"body": body, "success": False, "message": "Unable to find thread to evaluate variable reference."}
            )
            return NetCommand(CMD_RETURN, 0, variables_response, is_json=True)

    def on_setvariable_request(self, py_db, request):
        arguments = request.arguments  # : :type arguments: SetVariableArguments
        variables_reference = arguments.variablesReference

        if isinstance(variables_reference, ScopeRequest):
            variables_reference = variables_reference.variable_reference

        if arguments.name.startswith("(return) "):
            response = pydevd_base_schema.build_response(
                request, kwargs={"body": SetVariableResponseBody(""), "success": False, "message": "Cannot change return value"}
            )
            return NetCommand(CMD_RETURN, 0, response, is_json=True)

        thread_id = py_db.suspended_frames_manager.get_thread_id_for_variable_reference(variables_reference)

        if thread_id is not None:
            self.api.request_change_variable_json(py_db, request, thread_id)
        else:
            response = pydevd_base_schema.build_response(
                request,
                kwargs={
                    "body": SetVariableResponseBody(""),
                    "success": False,
                    "message": "Unable to find thread to evaluate variable reference.",
                },
            )
            return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_modules_request(self, py_db, request):
        modules_manager = py_db.cmd_factory.modules_manager  # : :type modules_manager: ModulesManager
        modules_info = modules_manager.get_modules_info()
        body = ModulesResponseBody(modules_info)
        variables_response = pydevd_base_schema.build_response(request, kwargs={"body": body})
        return NetCommand(CMD_RETURN, 0, variables_response, is_json=True)

    def on_source_request(self, py_db, request):
        """
        :param SourceRequest request:
        """
        source_reference = request.arguments.sourceReference
        server_filename = None
        content = None

        if source_reference != 0:
            server_filename = pydevd_file_utils.get_server_filename_from_source_reference(source_reference)
            if not server_filename:
                server_filename = pydevd_file_utils.get_source_reference_filename_from_linecache(source_reference)

            if server_filename:
                # Try direct file access first - it's much faster when available.
                try:
                    with open(server_filename, "r") as stream:
                        content = stream.read()
                except:
                    pass

                if content is None:
                    # File might not exist at all, or we might not have a permission to read it,
                    # but it might also be inside a zipfile, or an IPython cell. In this case,
                    # linecache might still be able to retrieve the source.
                    lines = (linecache.getline(server_filename, i) for i in itertools.count(1))
                    lines = itertools.takewhile(bool, lines)  # empty lines are '\n', EOF is ''

                    # If we didn't get at least one line back, reset it to None so that it's
                    # reported as error below, and not as an empty file.
                    content = "".join(lines) or None

            if content is None:
                frame_id = pydevd_file_utils.get_frame_id_from_source_reference(source_reference)
                pydev_log.debug("Found frame id: %s for source reference: %s", frame_id, source_reference)
                if frame_id is not None:
                    try:
                        content = self.api.get_decompiled_source_from_frame_id(py_db, frame_id)
                    except Exception:
                        pydev_log.exception("Error getting source for frame id: %s", frame_id)
                        content = None

        body = SourceResponseBody(content or "")
        response_args = {"body": body}

        if content is None:
            if source_reference == 0:
                message = "Source unavailable"
            elif server_filename:
                message = "Unable to retrieve source for %s" % (server_filename,)
            else:
                message = "Invalid sourceReference %d" % (source_reference,)
            response_args.update({"success": False, "message": message})

        response = pydevd_base_schema.build_response(request, kwargs=response_args)
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_gototargets_request(self, py_db, request):
        path = request.arguments.source.path
        line = request.arguments.line
        target_id = self._goto_targets_map.obtain_key((path, line))
        target = {"id": target_id, "label": "%s:%s" % (path, line), "line": line}
        body = GotoTargetsResponseBody(targets=[target])
        response_args = {"body": body}
        response = pydevd_base_schema.build_response(request, kwargs=response_args)
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_goto_request(self, py_db, request):
        target_id = int(request.arguments.targetId)
        thread_id = request.arguments.threadId
        try:
            path, line = self._goto_targets_map.obtain_value(target_id)
        except KeyError:
            response = pydevd_base_schema.build_response(
                request,
                kwargs={
                    "body": {},
                    "success": False,
                    "message": "Unknown goto target id: %d" % (target_id,),
                },
            )
            return NetCommand(CMD_RETURN, 0, response, is_json=True)

        self.api.request_set_next(py_db, request.seq, thread_id, CMD_SET_NEXT_STATEMENT, path, line, "*")
        # See 'NetCommandFactoryJson.make_set_next_stmnt_status_message' for response
        return None

    def on_setdebuggerproperty_request(self, py_db, request):
        args = request.arguments  # : :type args: SetDebuggerPropertyArguments
        if args.ideOS is not None:
            self.api.set_ide_os(args.ideOS)

        if args.dontTraceStartPatterns is not None and args.dontTraceEndPatterns is not None:
            start_patterns = tuple(args.dontTraceStartPatterns)
            end_patterns = tuple(args.dontTraceEndPatterns)
            self.api.set_dont_trace_start_end_patterns(py_db, start_patterns, end_patterns)

        if args.skipSuspendOnBreakpointException is not None:
            py_db.skip_suspend_on_breakpoint_exception = tuple(get_exception_class(x) for x in args.skipSuspendOnBreakpointException)

        if args.skipPrintBreakpointException is not None:
            py_db.skip_print_breakpoint_exception = tuple(get_exception_class(x) for x in args.skipPrintBreakpointException)

        if args.multiThreadsSingleNotification is not None:
            py_db.multi_threads_single_notification = args.multiThreadsSingleNotification

        # TODO: Support other common settings. Note that not all of these might be relevant to python.
        # JustMyCodeStepping: 0 or 1
        # AllowOutOfProcessSymbols: 0 or 1
        # DisableJITOptimization: 0 or 1
        # InterpreterOptions: 0 or 1
        # StopOnExceptionCrossingManagedBoundary: 0 or 1
        # WarnIfNoUserCodeOnLaunch: 0 or 1
        # EnableStepFiltering: true of false

        response = pydevd_base_schema.build_response(request, kwargs={"body": {}})
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_pydevdsysteminfo_request(self, py_db, request):
        try:
            pid = os.getpid()
        except AttributeError:
            pid = None

        # It's possible to have the ppid reported from args. In this case, use that instead of the
        # real ppid (athough we're using `ppid`, what we want in meaning is the `launcher_pid` --
        # so, if a python process is launched from another python process, consider that process the
        # parent and not any intermediary stubs).

        ppid = py_db.get_arg_ppid() or self.api.get_ppid()

        try:
            impl_desc = platform.python_implementation()
        except AttributeError:
            impl_desc = PY_IMPL_NAME

        py_info = pydevd_schema.PydevdPythonInfo(
            version=PY_VERSION_STR,
            implementation=pydevd_schema.PydevdPythonImplementationInfo(
                name=PY_IMPL_NAME,
                version=PY_IMPL_VERSION_STR,
                description=impl_desc,
            ),
        )
        platform_info = pydevd_schema.PydevdPlatformInfo(name=sys.platform)
        process_info = pydevd_schema.PydevdProcessInfo(
            pid=pid,
            ppid=ppid,
            executable=sys.executable,
            bitness=64 if IS_64BIT_PROCESS else 32,
        )
        pydevd_info = pydevd_schema.PydevdInfo(
            usingCython=USING_CYTHON,
            usingFrameEval=USING_FRAME_EVAL,
        )
        body = {
            "python": py_info,
            "platform": platform_info,
            "process": process_info,
            "pydevd": pydevd_info,
        }
        response = pydevd_base_schema.build_response(request, kwargs={"body": body})
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

    def on_setpydevdsourcemap_request(self, py_db, request):
        args = request.arguments  # : :type args: SetPydevdSourceMapArguments
        SourceMappingEntry = self.api.SourceMappingEntry

        path = args.source.path
        source_maps = args.pydevdSourceMaps
        # : :type source_map: PydevdSourceMap
        new_mappings = [
            SourceMappingEntry(
                source_map["line"],
                source_map["endLine"],
                source_map["runtimeLine"],
                self.api.filename_to_str(source_map["runtimeSource"]["path"]),
            )
            for source_map in source_maps
        ]

        error_msg = self.api.set_source_mapping(py_db, path, new_mappings)
        if error_msg:
            response = pydevd_base_schema.build_response(
                request,
                kwargs={
                    "body": {},
                    "success": False,
                    "message": error_msg,
                },
            )
            return NetCommand(CMD_RETURN, 0, response, is_json=True)

        response = pydevd_base_schema.build_response(request)
        return NetCommand(CMD_RETURN, 0, response, is_json=True)

# === NexusCore/openenv\Lib\site-packages\win32com\client\genpy.py ===
"""genpy.py - The worker for makepy.  See makepy.py for more details

This code was moved simply to speed Python in normal circumstances.  As the makepy.py
is normally run from the command line, it reparses the code each time.  Now makepy
is nothing more than the command line handler and public interface.

The makepy command line etc handling is also getting large enough in its own right!
"""

# NOTE - now supports a "demand" mechanism - the top-level is a package, and
# each class etc can be made individually.
# This should eventually become the default.
# Then the old non-package technique should be removed.
# There should be no b/w compat issues, and will just help clean the code.
# This will be done once the new "demand" mechanism gets a good workout.
import os
import sys
import time
from itertools import chain

import pythoncom

from . import build, gencache

makepy_version = "0.5.01"  # Written to generated file.

GEN_FULL = "full"
GEN_DEMAND_BASE = "demand(base)"
GEN_DEMAND_CHILD = "demand(child)"

# This map is used purely for the users benefit -it shows the
# raw, underlying type of Alias/Enums, etc.  The COM implementation
# does not use this map at runtime - all Alias/Enum have already
# been translated.
mapVTToTypeString = {
    pythoncom.VT_I2: "int",
    pythoncom.VT_I4: "int",
    pythoncom.VT_R4: "float",
    pythoncom.VT_R8: "float",
    pythoncom.VT_BSTR: "str",
    pythoncom.VT_BOOL: "int",
    pythoncom.VT_VARIANT: "type",
    pythoncom.VT_I1: "int",
    pythoncom.VT_UI1: "int",
    pythoncom.VT_UI2: "int",
    pythoncom.VT_UI4: "int",
    pythoncom.VT_I8: "int",
    pythoncom.VT_UI8: "int",
    pythoncom.VT_INT: "int",
    pythoncom.VT_DATE: "datetime.date",
    pythoncom.VT_UINT: "int",
}


# Given a propget function's arg desc, return the default parameters for all
# params bar the first.  Eg, then Python does a:
# object.Property = "foo"
# Python can only pass the "foo" value.  If the property has
# multiple args, and the rest have default values, this allows
# Python to correctly pass those defaults.
def MakeDefaultArgsForPropertyPut(argsDesc):
    ret = []
    for desc in argsDesc[1:]:
        default = build.MakeDefaultArgRepr(desc)
        if default is None:
            break
        ret.append(default)
    return tuple(ret)


def MakeMapLineEntry(dispid, wFlags, retType, argTypes, user, resultCLSID):
    # Strip the default value
    argTypes = tuple([what[:2] for what in argTypes])
    return '(%s, %d, %s, %s, "%s", %s)' % (
        dispid,
        wFlags,
        retType[:2],
        argTypes,
        user,
        resultCLSID,
    )


def MakeEventMethodName(eventName):
    if eventName[:2] == "On":
        return eventName
    else:
        return "On" + eventName


def WriteSinkEventMap(obj, stream):
    print("\t_dispid_to_func_ = {", file=stream)
    for entry in chain(
        obj.propMapGet.values(),
        obj.propMapPut.values(),
        obj.mapFuncs.values(),
    ):
        memid = entry.desc.memid
        print(
            '\t\t%9d : "%s",' % (memid, MakeEventMethodName(entry.names[0])),
            file=stream,
        )
    print("\t\t}", file=stream)


# MI is used to join my writable helpers, and the OLE
# classes.
class WritableItem:
    def __lt__(self, other):
        if self.order == other.order:
            return self.doc < other.doc
        return self.order < other.order

    def __repr__(self):
        return f"OleItem: doc={self.doc!r}, order={self.order}"


class RecordItem(build.OleItem, WritableItem):
    order = 9
    typename = "RECORD"

    def __init__(self, typeInfo, typeAttr, doc=None, bForUser=1):
        ##    sys.stderr.write("Record %s: size %s\n" % (doc,typeAttr.cbSizeInstance))
        ##    sys.stderr.write(" cVars = %s\n" % (typeAttr.cVars,))
        ##    for i in range(typeAttr.cVars):
        ##        vdesc = typeInfo.GetVarDesc(i)
        ##        sys.stderr.write(" Var %d has value %s, type %d, desc=%s\n" % (i, vdesc.value, vdesc.varkind, vdesc.elemdescVar))
        ##        sys.stderr.write(" Doc is %s\n" % (typeInfo.GetDocumentation(vdesc.memid),))

        build.OleItem.__init__(self, doc)
        self.clsid = typeAttr[0]

    def WriteClass(self, generator):
        pass


# Given an enum, write all aliases for it.
# (no longer necessary for new style code, but still used for old code.
def WriteAliasesForItem(item, aliasItems, stream):
    for alias in aliasItems.values():
        if item.doc and alias.aliasDoc and (alias.aliasDoc[0] == item.doc[0]):
            alias.WriteAliasItem(aliasItems, stream)


class AliasItem(build.OleItem, WritableItem):
    order = 2
    typename = "ALIAS"

    def __init__(self, typeinfo, attr, doc=None, bForUser=1):
        build.OleItem.__init__(self, doc)

        ai = attr[14]
        self.attr = attr
        # XXX - This is a hack - why tuples?  Need to resolve?
        if isinstance(ai, tuple) and isinstance(ai[1], int):
            href = ai[1]
            alinfo = typeinfo.GetRefTypeInfo(href)
            self.aliasDoc = alinfo.GetDocumentation(-1)
            self.aliasAttr = alinfo.GetTypeAttr()
        else:
            self.aliasDoc = None
            self.aliasAttr = None

    def WriteAliasItem(self, aliasDict, stream):
        # we could have been written as part of an alias dependency
        if self.bWritten:
            return

        if self.aliasDoc:
            depName = self.aliasDoc[0]
            if depName in aliasDict:
                aliasDict[depName].WriteAliasItem(aliasDict, stream)
            print(self.doc[0] + " = " + depName, file=stream)
        else:
            ai = self.attr[14]
            if isinstance(ai, int):
                try:
                    typeStr = mapVTToTypeString[ai]
                    print(f"# {self.doc[0]}={typeStr}", file=stream)
                except KeyError:
                    print(
                        self.doc[0] + " = None # Can't convert alias info " + str(ai),
                        file=stream,
                    )
        print(file=stream)
        self.bWritten = 1


class EnumerationItem(build.OleItem, WritableItem):
    order = 1
    typename = "ENUMERATION"

    def __init__(self, typeinfo, attr, doc=None, bForUser=1):
        build.OleItem.__init__(self, doc)

        self.clsid = attr[0]
        self.mapVars = {}
        typeFlags = attr[11]
        self.hidden = (
            typeFlags & pythoncom.TYPEFLAG_FHIDDEN
            or typeFlags & pythoncom.TYPEFLAG_FRESTRICTED
        )

        for j in range(attr[7]):
            vdesc = typeinfo.GetVarDesc(j)
            name = typeinfo.GetNames(vdesc[0])[0]
            self.mapVars[name] = build.MapEntry(vdesc)

    # def WriteEnumerationHeaders(self, aliasItems, stream):
    #     enumName = self.doc[0]
    #     print(f"{enumName}=constants # Compatibility with previous versions.", file=stream)
    #     WriteAliasesForItem(self, aliasItems)

    def WriteEnumerationItems(self, stream):
        num = 0
        enumName = self.doc[0]
        # Write in name alpha order
        for name in sorted(self.mapVars):
            entry = self.mapVars[name]
            vdesc = entry.desc
            if vdesc[4] == pythoncom.VAR_CONST:
                val = vdesc[1]

                use = repr(val)
                # Make sure the repr of the value is valid python syntax
                # still could cause an error on import if it contains a module or type name
                # not available in the global namespace
                try:
                    compile(use, "<makepy>", "eval")
                except SyntaxError:
                    # At least add the repr as a string, so it can be investigated further
                    # Sanitize it, in case the repr contains its own quotes.  (??? line breaks too ???)
                    use = use.replace('"', "'")
                    use = (
                        f'"{use}" # This VARIANT type cannot be converted automatically'
                    )
                print(
                    "\t%-30s=%-10s # from enum %s"
                    % (build.MakePublicAttributeName(name, True), use, enumName),
                    file=stream,
                )
                num += 1
        return num


class VTableItem(build.VTableItem, WritableItem):
    order = 4

    def WriteClass(self, generator):
        self.WriteVTableMap(generator)
        self.bWritten = 1

    def WriteVTableMap(self, generator):
        stream = generator.file
        print(
            "%s_vtables_dispatch_ = %d" % (self.python_name, self.bIsDispatch),
            file=stream,
        )
        print(f"{self.python_name}_vtables_ = [", file=stream)
        for v in self.vtableFuncs:
            names, dispid, desc = v
            assert desc.desckind == pythoncom.DESCKIND_FUNCDESC
            arg_reprs = []
            # more hoops so we don't generate huge lines.
            item_num = 0
            print("\t((", end=" ", file=stream)
            for name in names:
                print(repr(name), ",", end=" ", file=stream)
                item_num += 1
                if item_num % 5 == 0:
                    print("\n\t\t\t", end=" ", file=stream)
            print(
                "), %d, (%r, %r, [" % (dispid, desc.memid, desc.scodeArray),
                end=" ",
                file=stream,
            )
            for arg in desc.args:
                item_num += 1
                if item_num % 5 == 0:
                    print("\n\t\t\t", end=" ", file=stream)
                defval = build.MakeDefaultArgRepr(arg)
                if arg[3] is None:
                    arg3_repr = None
                else:
                    arg3_repr = repr(arg[3])
                print(
                    repr((arg[0], arg[1], defval, arg3_repr)), ",", end=" ", file=stream
                )
            print("],", end=" ", file=stream)
            print(repr(desc.funckind), ",", end=" ", file=stream)
            print(repr(desc.invkind), ",", end=" ", file=stream)
            print(repr(desc.callconv), ",", end=" ", file=stream)
            print(repr(desc.cParamsOpt), ",", end=" ", file=stream)
            print(repr(desc.oVft), ",", end=" ", file=stream)
            print(repr(desc.rettype), ",", end=" ", file=stream)
            print(repr(desc.wFuncFlags), ",", end=" ", file=stream)
            print(")),", file=stream)
        print("]", file=stream)
        print(file=stream)


class DispatchItem(build.DispatchItem, WritableItem):
    order = 3

    def __init__(self, typeinfo, attr, doc=None):
        build.DispatchItem.__init__(self, typeinfo, attr, doc)
        self.type_attr = attr
        self.coclass_clsid = None

    def WriteClass(self, generator):
        if (
            not self.bIsDispatch
            and not self.type_attr.typekind == pythoncom.TKIND_DISPATCH
        ):
            return
        # This is pretty screwey - now we have vtable support we
        # should probably rethink this (ie, maybe write both sides for sinks, etc)
        if self.bIsSink:
            self.WriteEventSinkClassHeader(generator)
            self.WriteCallbackClassBody(generator)
        else:
            self.WriteClassHeader(generator)
            self.WriteClassBody(generator)
        print(file=generator.file)
        self.bWritten = 1

    def WriteClassHeader(self, generator):
        generator.checkWriteDispatchBaseClass()
        doc = self.doc
        stream = generator.file
        print("class " + self.python_name + "(DispatchBaseClass):", file=stream)
        if doc[1]:
            print("\t" + build._makeDocString(doc[1]), file=stream)
        try:
            progId = pythoncom.ProgIDFromCLSID(self.clsid)
            print(
                "\t# This class is creatable by the name '%s'" % (progId), file=stream
            )
        except pythoncom.com_error:
            pass
        print(f"\tCLSID = {self.clsid!r}", file=stream)
        if self.coclass_clsid is None:
            print("\tcoclass_clsid = None", file=stream)
        else:
            print(f"\tcoclass_clsid = {self.coclass_clsid!r}", file=stream)
        print(file=stream)
        self.bWritten = 1

    def WriteEventSinkClassHeader(self, generator):
        generator.checkWriteEventBaseClass()
        doc = self.doc
        stream = generator.file
        print("class " + self.python_name + ":", file=stream)
        if doc[1]:
            print("\t" + build._makeDocString(doc[1]), file=stream)
        try:
            progId = pythoncom.ProgIDFromCLSID(self.clsid)
            print(
                "\t# This class is creatable by the name '%s'" % (progId), file=stream
            )
        except pythoncom.com_error:
            pass
        print(f"\tCLSID = CLSID_Sink = {self.clsid!r}", file=stream)
        if self.coclass_clsid is None:
            print("\tcoclass_clsid = None", file=stream)
        else:
            print(f"\tcoclass_clsid = {self.coclass_clsid!r}", file=stream)
        print("\t_public_methods_ = [] # For COM Server support", file=stream)
        WriteSinkEventMap(self, stream)
        print(file=stream)
        print("\tdef __init__(self, oobj = None):", file=stream)
        print("\t\tif oobj is None:", file=stream)
        print("\t\t\tself._olecp = None", file=stream)
        print("\t\telse:", file=stream)
        print("\t\t\timport win32com.server.util", file=stream)
        print(
            "\t\t\tfrom win32com.server.policy import EventHandlerPolicy", file=stream
        )
        print(
            "\t\t\tcpc=oobj._oleobj_.QueryInterface(pythoncom.IID_IConnectionPointContainer)",
            file=stream,
        )
        print("\t\t\tcp=cpc.FindConnectionPoint(self.CLSID_Sink)", file=stream)
        print(
            "\t\t\tcookie=cp.Advise(win32com.server.util.wrap(self, usePolicy=EventHandlerPolicy))",
            file=stream,
        )
        print("\t\t\tself._olecp,self._olecp_cookie = cp,cookie", file=stream)
        print("\tdef __del__(self):", file=stream)
        print("\t\ttry:", file=stream)
        print("\t\t\tself.close()", file=stream)
        print("\t\texcept pythoncom.com_error:", file=stream)
        print("\t\t\tpass", file=stream)
        print("\tdef close(self):", file=stream)
        print("\t\tif self._olecp is not None:", file=stream)
        print(
            "\t\t\tcp,cookie,self._olecp,self._olecp_cookie = self._olecp,self._olecp_cookie,None,None",
            file=stream,
        )
        print("\t\t\tcp.Unadvise(cookie)", file=stream)
        print("\tdef _query_interface_(self, iid):", file=stream)
        print("\t\timport win32com.server.util", file=stream)
        print(
            "\t\tif iid==self.CLSID_Sink: return win32com.server.util.wrap(self)",
            file=stream,
        )
        print(file=stream)
        self.bWritten = 1

    def WriteCallbackClassBody(self, generator):
        stream = generator.file
        print("\t# Event Handlers", file=stream)
        print(
            "\t# If you create handlers, they should have the following prototypes:",
            file=stream,
        )
        for entry in chain(
            self.propMapGet.values(), self.propMapPut.values(), self.mapFuncs.values()
        ):
            fdesc = entry.desc
            methName = MakeEventMethodName(entry.names[0])
            print(
                "#\tdef "
                + methName
                + "(self"
                + build.BuildCallList(
                    fdesc,
                    entry.names,
                    "defaultNamedOptArg",
                    "defaultNamedNotOptArg",
                    "defaultUnnamedArg",
                    "pythoncom.Missing",
                    is_comment=True,
                )
                + "):",
                file=stream,
            )
            if entry.doc and entry.doc[1]:
                print("#\t\t" + build._makeDocString(entry.doc[1]), file=stream)
        print(file=stream)
        self.bWritten = 1

    def WriteClassBody(self, generator):
        stream = generator.file
        specialItems = {
            "count": None,
            "item": None,
            "value": None,
            "_newenum": None,
        }  # If found, will end up with (entry, invoke_tupe)
        # Write in alpha order.
        for name in sorted(self.mapFuncs):
            entry = self.mapFuncs[name]
            assert entry.desc.desckind == pythoncom.DESCKIND_FUNCDESC
            # skip [restricted] methods, unless it is the
            # enumerator (which, being part of the "system",
            # we know about and can use)
            dispid = entry.desc.memid
            if (
                entry.desc.wFuncFlags & pythoncom.FUNCFLAG_FRESTRICTED
                and dispid != pythoncom.DISPID_NEWENUM
            ):
                continue
            # If not accessible via IDispatch, then we can't use it here.
            if entry.desc.funckind != pythoncom.FUNC_DISPATCH:
                continue
            if dispid == pythoncom.DISPID_VALUE:
                lkey = "value"
            elif dispid == pythoncom.DISPID_NEWENUM:
                specialItems["_newenum"] = (entry, entry.desc.invkind, None)
                continue  # Don't build this one now!
            else:
                lkey = name.lower()
            if (
                lkey in specialItems and specialItems[lkey] is None
            ):  # remember if a special one.
                specialItems[lkey] = (entry, entry.desc.invkind, None)
            if generator.bBuildHidden or not entry.hidden:
                if entry.GetResultName():
                    print("\t# Result is of type " + entry.GetResultName(), file=stream)
                if entry.wasProperty:
                    print(
                        "\t# The method %s is actually a property, but must be used as a method to correctly pass the arguments"
                        % name,
                        file=stream,
                    )
                ret = self.MakeFuncMethod(entry, build.MakePublicAttributeName(name))
                for line in ret:
                    print(line, file=stream)
        print("\t_prop_map_get_ = {", file=stream)
        for key in sorted(self.propMap):
            entry = self.propMap[key]
            if generator.bBuildHidden or not entry.hidden:
                resultName = entry.GetResultName()
                if resultName:
                    print(
                        f"\t\t# Property '{key}' is an object of type '{resultName}'",
                        file=stream,
                    )
                lkey = key.lower()
                details = entry.desc
                resultDesc = details[2]
                argDesc = ()
                mapEntry = MakeMapLineEntry(
                    details.memid,
                    pythoncom.DISPATCH_PROPERTYGET,
                    resultDesc,
                    argDesc,
                    key,
                    entry.GetResultCLSIDStr(),
                )

                if details.memid == pythoncom.DISPID_VALUE:
                    lkey = "value"
                elif details.memid == pythoncom.DISPID_NEWENUM:
                    lkey = "_newenum"
                else:
                    lkey = key.lower()
                if (
                    lkey in specialItems and specialItems[lkey] is None
                ):  # remember if a special one.
                    specialItems[lkey] = (
                        entry,
                        pythoncom.DISPATCH_PROPERTYGET,
                        mapEntry,
                    )
                    # All special methods, except _newenum, are written
                    # "normally".  This is a mess!
                    if details.memid == pythoncom.DISPID_NEWENUM:
                        continue

                print(
                    f'\t\t"{build.MakePublicAttributeName(key)}": {mapEntry},',
                    file=stream,
                )
        for key in sorted(self.propMapGet):
            entry = self.propMapGet[key]
            if generator.bBuildHidden or not entry.hidden:
                if entry.GetResultName():
                    print(
                        "\t\t# Method '{}' returns object of type '{}'".format(
                            key, entry.GetResultName()
                        ),
                        file=stream,
                    )
                details = entry.desc
                assert details.desckind == pythoncom.DESCKIND_FUNCDESC
                lkey = key.lower()
                argDesc = details[2]
                resultDesc = details[8]
                mapEntry = MakeMapLineEntry(
                    details[0],
                    pythoncom.DISPATCH_PROPERTYGET,
                    resultDesc,
                    argDesc,
                    key,
                    entry.GetResultCLSIDStr(),
                )
                if details.memid == pythoncom.DISPID_VALUE:
                    lkey = "value"
                elif details.memid == pythoncom.DISPID_NEWENUM:
                    lkey = "_newenum"
                else:
                    lkey = key.lower()
                if (
                    lkey in specialItems and specialItems[lkey] is None
                ):  # remember if a special one.
                    specialItems[lkey] = (
                        entry,
                        pythoncom.DISPATCH_PROPERTYGET,
                        mapEntry,
                    )
                    # All special methods, except _newenum, are written
                    # "normally".  This is a mess!
                    if details.memid == pythoncom.DISPID_NEWENUM:
                        continue
                print(
                    f'\t\t"{build.MakePublicAttributeName(key)}": {mapEntry},',
                    file=stream,
                )

        print("\t}", file=stream)

        print("\t_prop_map_put_ = {", file=stream)
        # These are "Invoke" args
        for key in sorted(self.propMap):
            entry = self.propMap[key]
            if generator.bBuildHidden or not entry.hidden:
                lkey = key.lower()
                details = entry.desc
                # If default arg is None, write an empty tuple
                defArgDesc = build.MakeDefaultArgRepr(details[2])
                if defArgDesc is None:
                    defArgDesc = ""
                else:
                    defArgDesc += ","
                print(
                    '\t\t"%s" : ((%s, LCID, %d, 0),(%s)),'
                    % (
                        build.MakePublicAttributeName(key),
                        details[0],
                        pythoncom.DISPATCH_PROPERTYPUT,
                        defArgDesc,
                    ),
                    file=stream,
                )

        for key in sorted(self.propMapPut):
            entry = self.propMapPut[key]
            if generator.bBuildHidden or not entry.hidden:
                details = entry.desc
                defArgDesc = MakeDefaultArgsForPropertyPut(details[2])
                print(
                    '\t\t"%s": ((%s, LCID, %d, 0),%s),'
                    % (
                        build.MakePublicAttributeName(key),
                        details[0],
                        details[4],
                        defArgDesc,
                    ),
                    file=stream,
                )
        print("\t}", file=stream)

        if specialItems["value"]:
            entry, invoketype, propArgs = specialItems["value"]
            if propArgs is None:
                typename = "method"
                ret = self.MakeFuncMethod(entry, "__call__")
            else:
                typename = "property"
                ret = [
                    "\tdef __call__(self):\n\t\treturn self._ApplyTypes_(*%s)"
                    % propArgs
                ]
            print(
                f"\t# Default {typename} for this class is '{entry.names[0]}'",
                file=stream,
            )
            for line in ret:
                print(line, file=stream)
            print("\tdef __str__(self, *args):", file=stream)
            print("\t\treturn str(self.__call__(*args))", file=stream)
            print("\tdef __int__(self, *args):", file=stream)
            print("\t\treturn int(self.__call__(*args))", file=stream)

        # _NewEnum (DISPID_NEWENUM) does not appear in typelib for many office objects,
        # but it can still be retrieved at runtime, so  always create __iter__.
        # Also, some of those same objects use 1-based indexing, causing the old-style
        # __getitem__ iteration to fail for index 0 where the dynamic iteration succeeds.
        if specialItems["_newenum"]:
            enumEntry, invoketype, propArgs = specialItems["_newenum"]
            assert enumEntry.desc.desckind == pythoncom.DESCKIND_FUNCDESC
            invkind = enumEntry.desc.invkind
            # ??? Wouldn't this be the resultCLSID for the iterator itself, rather than the resultCLSID
            #  for the result of each Next() call, which is what it's used for ???
            resultCLSID = enumEntry.GetResultCLSIDStr()
        else:
            invkind = pythoncom.DISPATCH_METHOD | pythoncom.DISPATCH_PROPERTYGET
            resultCLSID = "None"
        # If we don't have a good CLSID for the enum result, assume it is the same as the Item() method.
        if resultCLSID == "None" and "Item" in self.mapFuncs:
            resultCLSID = self.mapFuncs["Item"].GetResultCLSIDStr()
        print("\tdef __iter__(self):", file=stream)
        print('\t\t"Return a Python iterator for this object"', file=stream)
        print("\t\ttry:", file=stream)
        print(
            "\t\t\tob = self._oleobj_.InvokeTypes(%d,LCID,%d,(13, 10),())"
            % (pythoncom.DISPID_NEWENUM, invkind),
            file=stream,
        )
        print("\t\texcept pythoncom.error:", file=stream)
        print(
            '\t\t\traise TypeError("This object does not support enumeration")',
            file=stream,
        )
        # Iterator is wrapped as PyIEnumVariant, and each result of __next__ is Dispatch'ed if necessary
        print(
            "\t\treturn win32com.client.util.Iterator(ob, %s)" % resultCLSID,
            file=stream,
        )

        if specialItems["item"]:
            entry, invoketype, propArgs = specialItems["item"]
            resultCLSID = entry.GetResultCLSIDStr()
            print(
                "\t#This class has Item property/method which allows indexed access with the object[key] syntax.",
                file=stream,
            )
            print(
                "\t#Some objects will accept a string or other type of key in addition to integers.",
                file=stream,
            )
            print(
                "\t#Note that many Office objects do not use zero-based indexing.",
                file=stream,
            )
            print("\tdef __getitem__(self, key):", file=stream)
            print(
                '\t\treturn self._get_good_object_(self._oleobj_.Invoke(*(%d, LCID, %d, 1, key)), "Item", %s)'
                % (entry.desc.memid, invoketype, resultCLSID),
                file=stream,
            )

        if specialItems["count"]:
            entry, invoketype, propArgs = specialItems["count"]
            if propArgs is None:
                typename = "method"
                ret = self.MakeFuncMethod(entry, "__len__")
            else:
                typename = "property"
                ret = [
                    "\tdef __len__(self):\n\t\treturn self._ApplyTypes_(*%s)" % propArgs
                ]
            print(
                "\t#This class has Count() %s - allow len(ob) to provide this"
                % (typename),
                file=stream,
            )
            for line in ret:
                print(line, file=stream)
            # Also include a __bool__
            print(
                "\t#This class has a __len__ - this is needed so 'if object:' always returns TRUE.",
                file=stream,
            )
            print("\tdef __bool__(self):", file=stream)
            print("\t\treturn True", file=stream)


class CoClassItem(build.OleItem, WritableItem):
    order = 5
    typename = "COCLASS"

    def __init__(self, typeinfo, attr, doc=None, sources=[], interfaces=[], bForUser=1):
        build.OleItem.__init__(self, doc)
        self.clsid = attr[0]
        self.sources = sources
        self.interfaces = interfaces
        self.bIsDispatch = 1  # Pretend it is so it is written to the class map.

    def WriteClass(self, generator):
        generator.checkWriteCoClassBaseClass()
        doc = self.doc
        stream = generator.file
        if generator.generate_type == GEN_DEMAND_CHILD:
            # Some special imports we must setup.
            referenced_items = []
            for ref, flag in self.sources:
                referenced_items.append(ref)
            for ref, flag in self.interfaces:
                referenced_items.append(ref)
            print("import sys", file=stream)
            for ref in referenced_items:
                print(
                    f"__import__('{generator.base_mod_name}.{ref.python_name}')",
                    file=stream,
                )
                print(
                    "{} = sys.modules['{}.{}'].{}".format(
                        ref.python_name,
                        generator.base_mod_name,
                        ref.python_name,
                        ref.python_name,
                    ),
                    file=stream,
                )
                # And pretend we have written it - the name is now available as if we had!
                ref.bWritten = 1
        try:
            progId = pythoncom.ProgIDFromCLSID(self.clsid)
            print("# This CoClass is known by the name '%s'" % (progId), file=stream)
        except pythoncom.com_error:
            pass
        print(
            "class %s(CoClassBaseClass): # A CoClass" % (self.python_name), file=stream
        )
        if doc and doc[1]:
            print("\t# " + doc[1], file=stream)
        print(f"\tCLSID = {self.clsid!r}", file=stream)
        print("\tcoclass_sources = [", file=stream)
        defItem = None
        for item, flag in self.sources:
            if flag & pythoncom.IMPLTYPEFLAG_FDEFAULT:
                defItem = item
            # If we have written a Python class, reference the name -
            # otherwise just the IID.
            if item.bWritten:
                key = item.python_name
            else:
                key = f"'{item.clsid}'"  # really the iid.
            print(f"\t\t{key},", file=stream)
        print("\t]", file=stream)
        if defItem:
            if defItem.bWritten:
                defName = defItem.python_name
            else:
                defName = f"'{defItem.clsid}'"  # really the iid.
            print(f"\tdefault_source = {defName}", file=stream)
        print("\tcoclass_interfaces = [", file=stream)
        defItem = None
        for item, flag in self.interfaces:
            if flag & pythoncom.IMPLTYPEFLAG_FDEFAULT:  # and dual:
                defItem = item
            # If we have written a class, reference its name, otherwise the IID
            if item.bWritten:
                key = item.python_name
            else:
                key = f"'{item.clsid}'"  # really the iid.
            print(f"\t\t{key},", file=stream)
        print("\t]", file=stream)
        if defItem:
            if defItem.bWritten:
                defName = defItem.python_name
            else:
                defName = f"'{defItem.clsid}'"  # really the iid.
            print(f"\tdefault_interface = {defName}", file=stream)
        self.bWritten = 1
        print(file=stream)


class GeneratorProgress:
    def __init__(self):
        pass

    def Starting(self, tlb_desc):
        """Called when the process starts."""
        self.tlb_desc = tlb_desc

    def Finished(self):
        """Called when the process is complete."""

    def SetDescription(self, desc, maxticks=None):
        """We are entering a major step.  If maxticks, then this
        is how many ticks we expect to make until finished
        """

    def Tick(self, desc=None):
        """Minor progress step.  Can provide new description if necessary"""

    def VerboseProgress(self, desc):
        """Verbose/Debugging output."""

    def LogWarning(self, desc):
        """If a warning is generated"""

    def LogBeginGenerate(self, filename):
        pass

    def Close(self):
        pass


class Generator:
    def __init__(
        self,
        typelib,
        sourceFilename,
        progressObject,
        bBuildHidden=1,
    ):
        self.bHaveWrittenDispatchBaseClass = 0
        self.bHaveWrittenCoClassBaseClass = 0
        self.bHaveWrittenEventBaseClass = 0
        self.typelib = typelib
        self.sourceFilename = sourceFilename
        self.bBuildHidden = bBuildHidden
        self.progress = progressObject
        # These 2 are later additions and most of the code still 'print's...
        self.file = None

    def CollectOleItemInfosFromType(self):
        ret = []
        for i in range(self.typelib.GetTypeInfoCount()):
            info = self.typelib.GetTypeInfo(i)
            infotype = self.typelib.GetTypeInfoType(i)
            doc = self.typelib.GetDocumentation(i)
            attr = info.GetTypeAttr()
            ret.append((info, infotype, doc, attr))
        return ret

    def _Build_CoClass(self, type_info_tuple):
        info, infotype, doc, attr = type_info_tuple
        # find the source and dispinterfaces for the coclass
        child_infos = []
        for j in range(attr[8]):
            flags = info.GetImplTypeFlags(j)
            try:
                refType = info.GetRefTypeInfo(info.GetRefTypeOfImplType(j))
            except pythoncom.com_error:
                # Can't load a dependent typelib?
                continue
            refAttr = refType.GetTypeAttr()
            child_infos.append(
                (
                    info,
                    refAttr.typekind,
                    refType,
                    refType.GetDocumentation(-1),
                    refAttr,
                    flags,
                )
            )

        # Done generating children - now the CoClass itself.
        newItem = CoClassItem(info, attr, doc)
        return newItem, child_infos

    def _Build_CoClassChildren(self, coclass, coclass_info, oleItems, vtableItems):
        sources = {}
        interfaces = {}
        for info, info_type, refType, doc, refAttr, flags in coclass_info:
            #          sys.stderr.write("Attr typeflags for coclass referenced object %s=%d (%d), typekind=%d\n" % (name, refAttr.wTypeFlags, refAttr.wTypeFlags & pythoncom.TYPEFLAG_FDUAL,refAttr.typekind))
            if refAttr.typekind == pythoncom.TKIND_DISPATCH or (
                refAttr.typekind == pythoncom.TKIND_INTERFACE
                and refAttr[11] & pythoncom.TYPEFLAG_FDISPATCHABLE
            ):
                clsid = refAttr[0]
                if clsid in oleItems:
                    dispItem = oleItems[clsid]
                else:
                    dispItem = DispatchItem(refType, refAttr, doc)
                    oleItems[dispItem.clsid] = dispItem
                dispItem.coclass_clsid = coclass.clsid
                if flags & pythoncom.IMPLTYPEFLAG_FSOURCE:
                    dispItem.bIsSink = 1
                    sources[dispItem.clsid] = (dispItem, flags)
                else:
                    interfaces[dispItem.clsid] = (dispItem, flags)
                # If dual interface, make do that too.
                if clsid not in vtableItems and refAttr[11] & pythoncom.TYPEFLAG_FDUAL:
                    refType = refType.GetRefTypeInfo(refType.GetRefTypeOfImplType(-1))
                    refAttr = refType.GetTypeAttr()
                    assert (
                        refAttr.typekind == pythoncom.TKIND_INTERFACE
                    ), "must be interface bynow!"
                    vtableItem = VTableItem(refType, refAttr, doc)
                    vtableItems[clsid] = vtableItem
        coclass.sources = list(sources.values())
        coclass.interfaces = list(interfaces.values())

    def _Build_Interface(self, type_info_tuple):
        info, infotype, doc, attr = type_info_tuple
        oleItem = vtableItem = None
        if infotype == pythoncom.TKIND_DISPATCH or (
            infotype == pythoncom.TKIND_INTERFACE
            and attr[11] & pythoncom.TYPEFLAG_FDISPATCHABLE
        ):
            oleItem = DispatchItem(info, attr, doc)
            # If this DISPATCH interface dual, then build that too.
            if attr.wTypeFlags & pythoncom.TYPEFLAG_FDUAL:
                # Get the vtable interface
                refhtype = info.GetRefTypeOfImplType(-1)
                info = info.GetRefTypeInfo(refhtype)
                attr = info.GetTypeAttr()
                infotype = pythoncom.TKIND_INTERFACE
            else:
                infotype = None
        assert infotype in [
            None,
            pythoncom.TKIND_INTERFACE,
        ], "Must be a real interface at this point"
        if infotype == pythoncom.TKIND_INTERFACE:
            vtableItem = VTableItem(info, attr, doc)
        return oleItem, vtableItem

    def BuildOleItemsFromType(self):
        assert self.bBuildHidden, "This code doesn't look at the hidden flag - I thought everyone set it true!?!?!"
        oleItems = {}
        enumItems = {}
        recordItems = {}
        vtableItems = {}

        for type_info_tuple in self.CollectOleItemInfosFromType():
            info, infotype, doc, attr = type_info_tuple
            clsid = attr[0]
            if infotype == pythoncom.TKIND_ENUM or infotype == pythoncom.TKIND_MODULE:
                newItem = EnumerationItem(info, attr, doc)
                enumItems[newItem.doc[0]] = newItem
            # We never hide interfaces (MSAccess, for example, nominates interfaces as
            # hidden, assuming that you only ever use them via the CoClass)
            elif infotype in [pythoncom.TKIND_DISPATCH, pythoncom.TKIND_INTERFACE]:
                if clsid not in oleItems:
                    oleItem, vtableItem = self._Build_Interface(type_info_tuple)
                    oleItems[clsid] = oleItem  # Even "None" goes in here.
                    if vtableItem is not None:
                        vtableItems[clsid] = vtableItem
            elif (
                infotype == pythoncom.TKIND_RECORD or infotype == pythoncom.TKIND_UNION
            ):
                newItem = RecordItem(info, attr, doc)
                recordItems[newItem.clsid] = newItem
            elif infotype == pythoncom.TKIND_ALIAS:
                # We don't care about alias' - handled intrinsicly.
                continue
            elif infotype == pythoncom.TKIND_COCLASS:
                newItem, child_infos = self._Build_CoClass(type_info_tuple)
                self._Build_CoClassChildren(newItem, child_infos, oleItems, vtableItems)
                oleItems[newItem.clsid] = newItem
            else:
                self.progress.LogWarning("Unknown TKIND found: %d" % infotype)

        return oleItems, enumItems, recordItems, vtableItems

    def open_writer(self, filename, encoding="utf-8"):
        # A place to put code to open a file with the appropriate encoding.
        # Does *not* set self.file - just opens and returns a file.
        # Actually returns a handle to a temp file - finish_writer then deletes
        # the filename asked for and puts everything back in place.  This
        # is so errors don't leave a 1/2 generated file around causing bizarre
        # errors later, and so that multiple processes writing the same file
        # don't step on each others' toes.
        # Could be a classmethod one day...
        temp_filename = self.get_temp_filename(filename)
        return open(temp_filename, "wt", encoding=encoding)

    def finish_writer(self, filename, f, worked):
        f.close()
        temp_filename = self.get_temp_filename(filename)
        if worked:
            os.replace(temp_filename, filename)
        else:
            try:
                os.unlink(filename)
                os.unlink(temp_filename)
            except OSError:
                pass

    def get_temp_filename(self, filename):
        return "%s.%d.temp" % (filename, os.getpid())

    def generate(self, file, is_for_demand=0):
        if is_for_demand:
            self.generate_type = GEN_DEMAND_BASE
        else:
            self.generate_type = GEN_FULL
        self.file = file
        self.do_generate()
        self.file = None
        self.progress.Finished()

    def do_gen_file_header(self):
        la = self.typelib.GetLibAttr()
        moduleDoc = self.typelib.GetDocumentation(-1)
        docDesc = ""
        if moduleDoc[1]:
            docDesc = moduleDoc[1]

        # Reset all the 'per file' state
        self.bHaveWrittenDispatchBaseClass = 0
        self.bHaveWrittenCoClassBaseClass = 0
        self.bHaveWrittenEventBaseClass = 0
        # You must provide a file correctly configured for writing unicode.
        # We assert this is it may indicate somewhere in pywin32 that needs
        # upgrading.
        assert self.file.encoding, self.file
        encoding = self.file.encoding

        print(f"# -*- coding: {encoding} -*-", file=self.file)
        print(f"# Created by makepy.py version {makepy_version}", file=self.file)
        print(
            "# By python version {}".format(sys.version.replace("\n", "-")),
            file=self.file,
        )
        if self.sourceFilename:
            print(
                f"# From type library '{os.path.split(self.sourceFilename)[1]}'",
                file=self.file,
            )
        print("# On %s" % time.ctime(time.time()), file=self.file)

        print(build._makeDocString(docDesc), file=self.file)

        print(f"makepy_version = {makepy_version!r}", file=self.file)
        print(f"python_version = 0x{sys.hexversion:x}", file=self.file)
        print(file=self.file)
        print(
            "import win32com.client.CLSIDToClass, pythoncom, pywintypes", file=self.file
        )
        print("import win32com.client.util", file=self.file)
        print("from pywintypes import IID", file=self.file)
        print("from win32com.client import Dispatch", file=self.file)
        print(file=self.file)
        print(
            "# The following 3 lines may need tweaking for the particular server",
            file=self.file,
        )
        print(
            "# Candidates are pythoncom.Missing, .Empty and .ArgNotFound",
            file=self.file,
        )
        print("defaultNamedOptArg=pythoncom.Empty", file=self.file)
        print("defaultNamedNotOptArg=pythoncom.Empty", file=self.file)
        print("defaultUnnamedArg=pythoncom.Empty", file=self.file)
        print(file=self.file)
        print(f"CLSID = {la[0]!r}", file=self.file)
        print(f"MajorVersion = {la[3]}", file=self.file)
        print(f"MinorVersion = {la[4]}", file=self.file)
        print(f"LibraryFlags = {la[5]}", file=self.file)
        print("LCID = " + hex(la[1]), file=self.file)
        print(file=self.file)

    def do_generate(self):
        moduleDoc = self.typelib.GetDocumentation(-1)
        stream = self.file
        docDesc = ""
        if moduleDoc[1]:
            docDesc = moduleDoc[1]
        self.progress.Starting(docDesc)
        self.progress.SetDescription("Building definitions from type library...")

        self.do_gen_file_header()

        oleItems, enumItems, recordItems, vtableItems = self.BuildOleItemsFromType()

        self.progress.SetDescription(
            "Generating...", len(oleItems) + len(enumItems) + len(vtableItems)
        )

        # Generate the constants and their support.
        if enumItems:
            print("class constants:", file=stream)
            num_written = 0
            for oleitem in sorted(enumItems.values()):
                num_written += oleitem.WriteEnumerationItems(stream)
                self.progress.Tick()
            if not num_written:
                print("\tpass", file=stream)
            print(file=stream)

        if self.generate_type == GEN_FULL:
            for oleitem in sorted(filter(None, oleItems.values())):
                self.progress.Tick()
                oleitem.WriteClass(self)

            for oleitem in sorted(vtableItems.values()):
                self.progress.Tick()
                oleitem.WriteClass(self)
        else:
            self.progress.Tick(len(oleItems) + len(vtableItems))

        print("RecordMap = {", file=stream)
        for record in recordItems.values():
            record_str = f"{record.doc[0]!r}: '{record.clsid}',"
            if record.clsid == pythoncom.IID_NULL:
                print(
                    f"\t###{record_str}",
                    "# Record disabled because it doesn't have a non-null GUID",
                    file=stream,
                )
            else:
                print(f"\t{record_str}", file=stream)
        print("}", file=stream)
        print(file=stream)

        # Write out _all_ my generated CLSID's in the map
        if self.generate_type == GEN_FULL:
            print("CLSIDToClassMap = {", file=stream)
            for item in oleItems.values():
                if item is not None and item.bWritten:
                    print(
                        f"\t'{item.clsid}' : {item.python_name},",
                        file=stream,
                    )
            print("}", file=stream)
            print("CLSIDToPackageMap = {}", file=stream)
            print(
                "win32com.client.CLSIDToClass.RegisterCLSIDsFromDict( CLSIDToClassMap )",
                file=stream,
            )
            print("VTablesToPackageMap = {}", file=stream)
            print("VTablesToClassMap = {", file=stream)
            for item in vtableItems.values():
                print(f"\t'{item.clsid}' : '{item.python_name}',", file=stream)
            print("}", file=stream)
            print(file=stream)

        else:
            print("CLSIDToClassMap = {}", file=stream)
            print("CLSIDToPackageMap = {", file=stream)
            for item in oleItems.values():
                if item is not None:
                    print(
                        f"\t'{item.clsid}' : {item.python_name!r},",
                        file=stream,
                    )
            print("}", file=stream)
            print("VTablesToClassMap = {}", file=stream)
            print("VTablesToPackageMap = {", file=stream)
            for item in vtableItems.values():
                print(f"\t'{item.clsid}' : '{item.python_name}',", file=stream)
            print("}", file=stream)
            print(file=stream)

        print(file=stream)
        # Bit of a hack - build a temp map of iteItems + vtableItems - coClasses
        map = {}
        for item in oleItems.values():
            if item is not None and not isinstance(item, CoClassItem):
                map[item.python_name] = item.clsid
        for item in vtableItems.values():  # No nones or CoClasses in this map
            map[item.python_name] = item.clsid

        print("NamesToIIDMap = {", file=stream)
        for name, iid in map.items():
            print(f"\t'{name}' : '{iid}',", file=stream)
        print("}", file=stream)
        print(file=stream)

        if enumItems:
            print(
                "win32com.client.constants.__dicts__.append(constants.__dict__)",
                file=stream,
            )
        print(file=stream)

    def generate_child(self, child, dir):
        "Generate a single child.  May force a few children to be built as we generate deps"
        self.generate_type = GEN_DEMAND_CHILD

        la = self.typelib.GetLibAttr()
        lcid = la[1]
        clsid = la[0]
        major = la[3]
        minor = la[4]
        self.base_mod_name = (
            "win32com.gen_py." + str(clsid)[1:-1] + f"x{lcid}x{major}x{minor}"
        )
        try:
            # Process the type library's CoClass objects, looking for the
            # specified name, or where a child has the specified name.
            # This ensures that all interesting things (including event interfaces)
            # are generated correctly.
            oleItems = {}
            vtableItems = {}
            infos = self.CollectOleItemInfosFromType()
            found = 0
            for type_info_tuple in infos:
                info, infotype, doc, attr = type_info_tuple
                if infotype == pythoncom.TKIND_COCLASS:
                    coClassItem, child_infos = self._Build_CoClass(type_info_tuple)
                    found = build.MakePublicAttributeName(doc[0]) == child
                    if not found:
                        # OK, check the child interfaces
                        for (
                            info,
                            info_type,
                            refType,
                            doc,
                            refAttr,
                            flags,
                        ) in child_infos:
                            if build.MakePublicAttributeName(doc[0]) == child:
                                found = 1
                                break
                    if found:
                        oleItems[coClassItem.clsid] = coClassItem
                        self._Build_CoClassChildren(
                            coClassItem, child_infos, oleItems, vtableItems
                        )
                        break
            if not found:
                # Doesn't appear in a class defn - look in the interface objects for it
                for type_info_tuple in infos:
                    info, infotype, doc, attr = type_info_tuple
                    if infotype in [
                        pythoncom.TKIND_INTERFACE,
                        pythoncom.TKIND_DISPATCH,
                    ]:
                        if build.MakePublicAttributeName(doc[0]) == child:
                            found = 1
                            oleItem, vtableItem = self._Build_Interface(type_info_tuple)
                            oleItems[clsid] = oleItem  # Even "None" goes in here.
                            if vtableItem is not None:
                                vtableItems[clsid] = vtableItem

            assert (
                found
            ), f"Can't find the '{child}' interface in the CoClasses, or the interfaces"
            # Make a map of iid: dispitem, vtableitem)
            items = {}
            for key, value in oleItems.items():
                items[key] = (value, None)
            for key, value in vtableItems.items():
                existing = items.get(key, None)
                if existing is not None:
                    new_val = existing[0], value
                else:
                    new_val = None, value
                items[key] = new_val

            self.progress.SetDescription("Generating...", len(items))
            for oleitem, vtableitem in items.values():
                an_item = oleitem or vtableitem
                assert not self.file, "already have a file?"
                # like makepy.py, we gen to a .temp file so failure doesn't
                # leave a 1/2 generated mess.
                out_name = os.path.join(dir, an_item.python_name) + ".py"
                worked = False
                self.file = self.open_writer(out_name)
                try:
                    if oleitem is not None:
                        self.do_gen_child_item(oleitem)
                    if vtableitem is not None:
                        self.do_gen_child_item(vtableitem)
                    self.progress.Tick()
                    worked = True
                finally:
                    with gencache.ModuleMutex(self.base_mod_name.split(".")[-1]):
                        self.finish_writer(out_name, self.file, worked)
                    self.file = None
        finally:
            self.progress.Finished()

    def do_gen_child_item(self, oleitem):
        moduleDoc = self.typelib.GetDocumentation(-1)
        docDesc = ""
        if moduleDoc[1]:
            docDesc = moduleDoc[1]
        self.progress.Starting(docDesc)
        self.progress.SetDescription("Building definitions from type library...")
        self.do_gen_file_header()
        oleitem.WriteClass(self)
        if oleitem.bWritten:
            print(
                'win32com.client.CLSIDToClass.RegisterCLSID( "{}", {} )'.format(
                    oleitem.clsid, oleitem.python_name
                ),
                file=self.file,
            )

    def checkWriteDispatchBaseClass(self):
        if not self.bHaveWrittenDispatchBaseClass:
            print("from win32com.client import DispatchBaseClass", file=self.file)
            self.bHaveWrittenDispatchBaseClass = 1

    def checkWriteCoClassBaseClass(self):
        if not self.bHaveWrittenCoClassBaseClass:
            print("from win32com.client import CoClassBaseClass", file=self.file)
            self.bHaveWrittenCoClassBaseClass = 1

    def checkWriteEventBaseClass(self):
        # Not a base class as such...
        if not self.bHaveWrittenEventBaseClass:
            # Nothing to do any more!
            self.bHaveWrittenEventBaseClass = 1


if __name__ == "__main__":
    print("This is a worker module.  Please use makepy to generate Python files.")

# === NexusCore/openenv\Lib\site-packages\git\util.py ===
# Copyright (C) 2008, 2009 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

import sys

__all__ = [
    "stream_copy",
    "join_path",
    "to_native_path_linux",
    "join_path_native",
    "Stats",
    "IndexFileSHA1Writer",
    "IterableObj",
    "IterableList",
    "BlockingLockFile",
    "LockFile",
    "Actor",
    "get_user_id",
    "assure_directory_exists",
    "RemoteProgress",
    "CallableRemoteProgress",
    "rmtree",
    "unbare_repo",
    "HIDE_WINDOWS_KNOWN_ERRORS",
]

if sys.platform == "win32":
    __all__.append("to_native_path_windows")

from abc import abstractmethod
import contextlib
from functools import wraps
import getpass
import logging
import os
import os.path as osp
import pathlib
import platform
import re
import shutil
import stat
import subprocess
import time
from urllib.parse import urlsplit, urlunsplit
import warnings

# NOTE: Unused imports can be improved now that CI testing has fully resumed. Some of
# these be used indirectly through other GitPython modules, which avoids having to write
# gitdb all the time in their imports. They are not in __all__, at least currently,
# because they could be removed or changed at any time, and so should not be considered
# conceptually public to code outside GitPython. Linters of course do not like it.
from gitdb.util import (
    LazyMixin,  # noqa: F401
    LockedFD,  # noqa: F401
    bin_to_hex,  # noqa: F401
    file_contents_ro,  # noqa: F401
    file_contents_ro_filepath,  # noqa: F401
    hex_to_bin,  # noqa: F401
    make_sha,
    to_bin_sha,  # noqa: F401
    to_hex_sha,  # noqa: F401
)

# typing ---------------------------------------------------------

from typing import (
    Any,
    AnyStr,
    BinaryIO,
    Callable,
    Dict,
    Generator,
    IO,
    Iterator,
    List,
    Optional,
    Pattern,
    Sequence,
    Tuple,
    TYPE_CHECKING,
    TypeVar,
    Union,
    cast,
    overload,
)

if TYPE_CHECKING:
    from git.cmd import Git
    from git.config import GitConfigParser, SectionConstraint
    from git.remote import Remote
    from git.repo.base import Repo

from git.types import (
    Files_TD,
    Has_id_attribute,
    HSH_TD,
    Literal,
    PathLike,
    Protocol,
    SupportsIndex,
    Total_TD,
    runtime_checkable,
)

# ---------------------------------------------------------------------

T_IterableObj = TypeVar("T_IterableObj", bound=Union["IterableObj", "Has_id_attribute"], covariant=True)
# So IterableList[Head] is subtype of IterableList[IterableObj].

_logger = logging.getLogger(__name__)


def _read_env_flag(name: str, default: bool) -> bool:
    """Read a boolean flag from an environment variable.

    :return:
        The flag, or the `default` value if absent or ambiguous.
    """
    try:
        value = os.environ[name]
    except KeyError:
        return default

    _logger.warning(
        "The %s environment variable is deprecated. Its effect has never been documented and changes without warning.",
        name,
    )

    adjusted_value = value.strip().lower()

    if adjusted_value in {"", "0", "false", "no"}:
        return False
    if adjusted_value in {"1", "true", "yes"}:
        return True
    _logger.warning("%s has unrecognized value %r, treating as %r.", name, value, default)
    return default


def _read_win_env_flag(name: str, default: bool) -> bool:
    """Read a boolean flag from an environment variable on Windows.

    :return:
        On Windows, the flag, or the `default` value if absent or ambiguous.
        On all other operating systems, ``False``.

    :note:
        This only accesses the environment on Windows.
    """
    return sys.platform == "win32" and _read_env_flag(name, default)


#: We need an easy way to see if Appveyor TCs start failing,
#: so the errors marked with this var are considered "acknowledged" ones, awaiting remedy,
#: till then, we wish to hide them.
HIDE_WINDOWS_KNOWN_ERRORS = _read_win_env_flag("HIDE_WINDOWS_KNOWN_ERRORS", True)
HIDE_WINDOWS_FREEZE_ERRORS = _read_win_env_flag("HIDE_WINDOWS_FREEZE_ERRORS", True)

# { Utility Methods

T = TypeVar("T")


def unbare_repo(func: Callable[..., T]) -> Callable[..., T]:
    """Methods with this decorator raise :exc:`~git.exc.InvalidGitRepositoryError` if
    they encounter a bare repository."""

    from .exc import InvalidGitRepositoryError

    @wraps(func)
    def wrapper(self: "Remote", *args: Any, **kwargs: Any) -> T:
        if self.repo.bare:
            raise InvalidGitRepositoryError("Method '%s' cannot operate on bare repositories" % func.__name__)
        # END bare method
        return func(self, *args, **kwargs)

    # END wrapper

    return wrapper


@contextlib.contextmanager
def cwd(new_dir: PathLike) -> Generator[PathLike, None, None]:
    """Context manager to temporarily change directory.

    This is similar to :func:`contextlib.chdir` introduced in Python 3.11, but the
    context manager object returned by a single call to this function is not reentrant.
    """
    old_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield new_dir
    finally:
        os.chdir(old_dir)


@contextlib.contextmanager
def patch_env(name: str, value: str) -> Generator[None, None, None]:
    """Context manager to temporarily patch an environment variable."""
    old_value = os.getenv(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if old_value is None:
            del os.environ[name]
        else:
            os.environ[name] = old_value


def rmtree(path: PathLike) -> None:
    """Remove the given directory tree recursively.

    :note:
        We use :func:`shutil.rmtree` but adjust its behaviour to see whether files that
        couldn't be deleted are read-only. Windows will not remove them in that case.
    """

    def handler(function: Callable, path: PathLike, _excinfo: Any) -> None:
        """Callback for :func:`shutil.rmtree`.

        This works as either a ``onexc`` or ``onerror`` style callback.
        """
        # Is the error an access error?
        os.chmod(path, stat.S_IWUSR)

        try:
            function(path)
        except PermissionError as ex:
            if HIDE_WINDOWS_KNOWN_ERRORS:
                from unittest import SkipTest

                raise SkipTest(f"FIXME: fails with: PermissionError\n  {ex}") from ex
            raise

    if sys.platform != "win32":
        shutil.rmtree(path)
    elif sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=handler)
    else:
        shutil.rmtree(path, onerror=handler)


def rmfile(path: PathLike) -> None:
    """Ensure file deleted also on *Windows* where read-only files need special
    treatment."""
    if osp.isfile(path):
        if sys.platform == "win32":
            os.chmod(path, 0o777)
        os.remove(path)


def stream_copy(source: BinaryIO, destination: BinaryIO, chunk_size: int = 512 * 1024) -> int:
    """Copy all data from the `source` stream into the `destination` stream in chunks
    of size `chunk_size`.

    :return:
        Number of bytes written
    """
    br = 0
    while True:
        chunk = source.read(chunk_size)
        destination.write(chunk)
        br += len(chunk)
        if len(chunk) < chunk_size:
            break
    # END reading output stream
    return br


def join_path(a: PathLike, *p: PathLike) -> PathLike:
    R"""Join path tokens together similar to osp.join, but always use ``/`` instead of
    possibly ``\`` on Windows."""
    path = str(a)
    for b in p:
        b = str(b)
        if not b:
            continue
        if b.startswith("/"):
            path += b[1:]
        elif path == "" or path.endswith("/"):
            path += b
        else:
            path += "/" + b
    # END for each path token to add
    return path


if sys.platform == "win32":

    def to_native_path_windows(path: PathLike) -> PathLike:
        path = str(path)
        return path.replace("/", "\\")

    def to_native_path_linux(path: PathLike) -> str:
        path = str(path)
        return path.replace("\\", "/")

    to_native_path = to_native_path_windows
else:
    # No need for any work on Linux.
    def to_native_path_linux(path: PathLike) -> str:
        return str(path)

    to_native_path = to_native_path_linux


def join_path_native(a: PathLike, *p: PathLike) -> PathLike:
    R"""Like :func:`join_path`, but makes sure an OS native path is returned.

    This is only needed to play it safe on Windows and to ensure nice paths that only
    use ``\``.
    """
    return to_native_path(join_path(a, *p))


def assure_directory_exists(path: PathLike, is_file: bool = False) -> bool:
    """Make sure that the directory pointed to by path exists.

    :param is_file:
        If ``True``, `path` is assumed to be a file and handled correctly.
        Otherwise it must be a directory.

    :return:
        ``True`` if the directory was created, ``False`` if it already existed.
    """
    if is_file:
        path = osp.dirname(path)
    # END handle file
    if not osp.isdir(path):
        os.makedirs(path, exist_ok=True)
        return True
    return False


def _get_exe_extensions() -> Sequence[str]:
    PATHEXT = os.environ.get("PATHEXT", None)
    if PATHEXT:
        return tuple(p.upper() for p in PATHEXT.split(os.pathsep))
    elif sys.platform == "win32":
        return (".BAT", ".COM", ".EXE")
    else:
        return ()


def py_where(program: str, path: Optional[PathLike] = None) -> List[str]:
    """Perform a path search to assist :func:`is_cygwin_git`.

    This is not robust for general use. It is an implementation detail of
    :func:`is_cygwin_git`. When a search following all shell rules is needed,
    :func:`shutil.which` can be used instead.

    :note:
        Neither this function nor :func:`shutil.which` will predict the effect of an
        executable search on a native Windows system due to a :class:`subprocess.Popen`
        call without ``shell=True``, because shell and non-shell executable search on
        Windows differ considerably.
    """
    # From: http://stackoverflow.com/a/377028/548792
    winprog_exts = _get_exe_extensions()

    def is_exec(fpath: str) -> bool:
        return (
            osp.isfile(fpath)
            and os.access(fpath, os.X_OK)
            and (
                sys.platform != "win32" or not winprog_exts or any(fpath.upper().endswith(ext) for ext in winprog_exts)
            )
        )

    progs = []
    if not path:
        path = os.environ["PATH"]
    for folder in str(path).split(os.pathsep):
        folder = folder.strip('"')
        if folder:
            exe_path = osp.join(folder, program)
            for f in [exe_path] + ["%s%s" % (exe_path, e) for e in winprog_exts]:
                if is_exec(f):
                    progs.append(f)
    return progs


def _cygexpath(drive: Optional[str], path: str) -> str:
    if osp.isabs(path) and not drive:
        # Invoked from `cygpath()` directly with `D:Apps\123`?
        #  It's an error, leave it alone just slashes)
        p = path  # convert to str if AnyPath given
    else:
        p = path and osp.normpath(osp.expandvars(osp.expanduser(path)))
        if osp.isabs(p):
            if drive:
                # Confusing, maybe a remote system should expand vars.
                p = path
            else:
                p = cygpath(p)
        elif drive:
            p = "/proc/cygdrive/%s/%s" % (drive.lower(), p)
    p_str = str(p)  # ensure it is a str and not AnyPath
    return p_str.replace("\\", "/")


_cygpath_parsers: Tuple[Tuple[Pattern[str], Callable, bool], ...] = (
    # See: https://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx
    # and: https://www.cygwin.com/cygwin-ug-net/using.html#unc-paths
    (
        re.compile(r"\\\\\?\\UNC\\([^\\]+)\\([^\\]+)(?:\\(.*))?"),
        (lambda server, share, rest_path: "//%s/%s/%s" % (server, share, rest_path.replace("\\", "/"))),
        False,
    ),
    (re.compile(r"\\\\\?\\(\w):[/\\](.*)"), (_cygexpath), False),
    (re.compile(r"(\w):[/\\](.*)"), (_cygexpath), False),
    (re.compile(r"file:(.*)", re.I), (lambda rest_path: rest_path), True),
    (re.compile(r"(\w{2,}:.*)"), (lambda url: url), False),  # remote URL, do nothing
)


def cygpath(path: str) -> str:
    """Use :meth:`git.cmd.Git.polish_url` instead, that works on any environment."""
    path = str(path)  # Ensure is str and not AnyPath.
    # Fix to use Paths when 3.5 dropped. Or to be just str if only for URLs?
    if not path.startswith(("/cygdrive", "//", "/proc/cygdrive")):
        for regex, parser, recurse in _cygpath_parsers:
            match = regex.match(path)
            if match:
                path = parser(*match.groups())
                if recurse:
                    path = cygpath(path)
                break
        else:
            path = _cygexpath(None, path)

    return path


_decygpath_regex = re.compile(r"(?:/proc)?/cygdrive/(\w)(/.*)?")


def decygpath(path: PathLike) -> str:
    path = str(path)
    m = _decygpath_regex.match(path)
    if m:
        drive, rest_path = m.groups()
        path = "%s:%s" % (drive.upper(), rest_path or "")

    return path.replace("/", "\\")


#: Store boolean flags denoting if a specific Git executable
#: is from a Cygwin installation (since `cache_lru()` unsupported on PY2).
_is_cygwin_cache: Dict[str, Optional[bool]] = {}


def _is_cygwin_git(git_executable: str) -> bool:
    is_cygwin = _is_cygwin_cache.get(git_executable)  # type: Optional[bool]
    if is_cygwin is None:
        is_cygwin = False
        try:
            git_dir = osp.dirname(git_executable)
            if not git_dir:
                res = py_where(git_executable)
                git_dir = osp.dirname(res[0]) if res else ""

            # Just a name given, not a real path.
            uname_cmd = osp.join(git_dir, "uname")
            process = subprocess.Popen([uname_cmd], stdout=subprocess.PIPE, universal_newlines=True)
            uname_out, _ = process.communicate()
            # retcode = process.poll()
            is_cygwin = "CYGWIN" in uname_out
        except Exception as ex:
            _logger.debug("Failed checking if running in CYGWIN due to: %r", ex)
        _is_cygwin_cache[git_executable] = is_cygwin

    return is_cygwin


@overload
def is_cygwin_git(git_executable: None) -> Literal[False]: ...


@overload
def is_cygwin_git(git_executable: PathLike) -> bool: ...


def is_cygwin_git(git_executable: Union[None, PathLike]) -> bool:
    if sys.platform == "win32":  # TODO: See if we can use `sys.platform != "cygwin"`.
        return False
    elif git_executable is None:
        return False
    else:
        return _is_cygwin_git(str(git_executable))


def get_user_id() -> str:
    """:return: String identifying the currently active system user as ``name@node``"""
    return "%s@%s" % (getpass.getuser(), platform.node())


def finalize_process(proc: Union[subprocess.Popen, "Git.AutoInterrupt"], **kwargs: Any) -> None:
    """Wait for the process (clone, fetch, pull or push) and handle its errors
    accordingly."""
    # TODO: No close proc-streams??
    proc.wait(**kwargs)


@overload
def expand_path(p: None, expand_vars: bool = ...) -> None: ...


@overload
def expand_path(p: PathLike, expand_vars: bool = ...) -> str:
    # TODO: Support for Python 3.5 has been dropped, so these overloads can be improved.
    ...


def expand_path(p: Union[None, PathLike], expand_vars: bool = True) -> Optional[PathLike]:
    if isinstance(p, pathlib.Path):
        return p.resolve()
    try:
        p = osp.expanduser(p)  # type: ignore[arg-type]
        if expand_vars:
            p = osp.expandvars(p)
        return osp.normpath(osp.abspath(p))
    except Exception:
        return None


def remove_password_if_present(cmdline: Sequence[str]) -> List[str]:
    """Parse any command line argument and if one of the elements is an URL with a
    username and/or password, replace them by stars (in-place).

    If nothing is found, this just returns the command line as-is.

    This should be used for every log line that print a command line, as well as
    exception messages.
    """
    new_cmdline = []
    for index, to_parse in enumerate(cmdline):
        new_cmdline.append(to_parse)
        try:
            url = urlsplit(to_parse)
            # Remove password from the URL if present.
            if url.password is None and url.username is None:
                continue

            if url.password is not None:
                url = url._replace(netloc=url.netloc.replace(url.password, "*****"))
            if url.username is not None:
                url = url._replace(netloc=url.netloc.replace(url.username, "*****"))
            new_cmdline[index] = urlunsplit(url)
        except ValueError:
            # This is not a valid URL.
            continue
    return new_cmdline


# } END utilities

# { Classes


class RemoteProgress:
    """Handler providing an interface to parse progress information emitted by
    :manpage:`git-push(1)` and :manpage:`git-fetch(1)` and to dispatch callbacks
    allowing subclasses to react to the progress."""

    _num_op_codes: int = 9
    (
        BEGIN,
        END,
        COUNTING,
        COMPRESSING,
        WRITING,
        RECEIVING,
        RESOLVING,
        FINDING_SOURCES,
        CHECKING_OUT,
    ) = [1 << x for x in range(_num_op_codes)]
    STAGE_MASK = BEGIN | END
    OP_MASK = ~STAGE_MASK

    DONE_TOKEN = "done."
    TOKEN_SEPARATOR = ", "

    __slots__ = (
        "_cur_line",
        "_seen_ops",
        "error_lines",  # Lines that started with 'error:' or 'fatal:'.
        "other_lines",  # Lines not denoting progress (i.e.g. push-infos).
    )
    re_op_absolute = re.compile(r"(remote: )?([\w\s]+):\s+()(\d+)()(.*)")
    re_op_relative = re.compile(r"(remote: )?([\w\s]+):\s+(\d+)% \((\d+)/(\d+)\)(.*)")

    def __init__(self) -> None:
        self._seen_ops: List[int] = []
        self._cur_line: Optional[str] = None
        self.error_lines: List[str] = []
        self.other_lines: List[str] = []

    def _parse_progress_line(self, line: AnyStr) -> None:
        """Parse progress information from the given line as retrieved by
        :manpage:`git-push(1)` or :manpage:`git-fetch(1)`.

        - Lines that do not contain progress info are stored in :attr:`other_lines`.
        - Lines that seem to contain an error (i.e. start with ``error:`` or ``fatal:``)
          are stored in :attr:`error_lines`.
        """
        # handle
        # Counting objects: 4, done.
        # Compressing objects:  50% (1/2)
        # Compressing objects: 100% (2/2)
        # Compressing objects: 100% (2/2), done.
        if isinstance(line, bytes):  # mypy argues about ternary assignment.
            line_str = line.decode("utf-8")
        else:
            line_str = line
        self._cur_line = line_str

        if self._cur_line.startswith(("error:", "fatal:")):
            self.error_lines.append(self._cur_line)
            return

        cur_count, max_count = None, None
        match = self.re_op_relative.match(line_str)
        if match is None:
            match = self.re_op_absolute.match(line_str)

        if not match:
            self.line_dropped(line_str)
            self.other_lines.append(line_str)
            return
        # END could not get match

        op_code = 0
        _remote, op_name, _percent, cur_count, max_count, message = match.groups()

        # Get operation ID.
        if op_name == "Counting objects":
            op_code |= self.COUNTING
        elif op_name == "Compressing objects":
            op_code |= self.COMPRESSING
        elif op_name == "Writing objects":
            op_code |= self.WRITING
        elif op_name == "Receiving objects":
            op_code |= self.RECEIVING
        elif op_name == "Resolving deltas":
            op_code |= self.RESOLVING
        elif op_name == "Finding sources":
            op_code |= self.FINDING_SOURCES
        elif op_name == "Checking out files":
            op_code |= self.CHECKING_OUT
        else:
            # Note: On Windows it can happen that partial lines are sent.
            # Hence we get something like "CompreReceiving objects", which is
            # a blend of "Compressing objects" and "Receiving objects".
            # This can't really be prevented, so we drop the line verbosely
            # to make sure we get informed in case the process spits out new
            # commands at some point.
            self.line_dropped(line_str)
            # Note: Don't add this line to the other lines, as we have to silently
            # drop it.
            return
        # END handle op code

        # Figure out stage.
        if op_code not in self._seen_ops:
            self._seen_ops.append(op_code)
            op_code |= self.BEGIN
        # END begin opcode

        if message is None:
            message = ""
        # END message handling

        message = message.strip()
        if message.endswith(self.DONE_TOKEN):
            op_code |= self.END
            message = message[: -len(self.DONE_TOKEN)]
        # END end message handling
        message = message.strip(self.TOKEN_SEPARATOR)

        self.update(
            op_code,
            cur_count and float(cur_count),
            max_count and float(max_count),
            message,
        )

    def new_message_handler(self) -> Callable[[str], None]:
        """
        :return:
            A progress handler suitable for :func:`~git.cmd.handle_process_output`,
            passing lines on to this progress handler in a suitable format.
        """

        def handler(line: AnyStr) -> None:
            return self._parse_progress_line(line.rstrip())

        # END handler

        return handler

    def line_dropped(self, line: str) -> None:
        """Called whenever a line could not be understood and was therefore dropped."""
        pass

    def update(
        self,
        op_code: int,
        cur_count: Union[str, float],
        max_count: Union[str, float, None] = None,
        message: str = "",
    ) -> None:
        """Called whenever the progress changes.

        :param op_code:
            Integer allowing to be compared against Operation IDs and stage IDs.

            Stage IDs are :const:`BEGIN` and :const:`END`. :const:`BEGIN` will only be
            set once for each Operation ID as well as :const:`END`. It may be that
            :const:`BEGIN` and :const:`END` are set at once in case only one progress
            message was emitted due to the speed of the operation. Between
            :const:`BEGIN` and :const:`END`, none of these flags will be set.

            Operation IDs are all held within the :const:`OP_MASK`. Only one Operation
            ID will be active per call.

        :param cur_count:
            Current absolute count of items.

        :param max_count:
            The maximum count of items we expect. It may be ``None`` in case there is no
            maximum number of items or if it is (yet) unknown.

        :param message:
            In case of the :const:`WRITING` operation, it contains the amount of bytes
            transferred. It may possibly be used for other purposes as well.

        :note:
            You may read the contents of the current line in
            :attr:`self._cur_line <_cur_line>`.
        """
        pass


class CallableRemoteProgress(RemoteProgress):
    """A :class:`RemoteProgress` implementation forwarding updates to any callable.

    :note:
        Like direct instances of :class:`RemoteProgress`, instances of this
        :class:`CallableRemoteProgress` class are not themselves directly callable.
        Rather, instances of this class wrap a callable and forward to it. This should
        therefore not be confused with :class:`git.types.CallableProgress`.
    """

    __slots__ = ("_callable",)

    def __init__(self, fn: Callable) -> None:
        self._callable = fn
        super().__init__()

    def update(self, *args: Any, **kwargs: Any) -> None:
        self._callable(*args, **kwargs)


class Actor:
    """Actors hold information about a person acting on the repository. They can be
    committers and authors or anything with a name and an email as mentioned in the git
    log entries."""

    # PRECOMPILED REGEX
    name_only_regex = re.compile(r"<(.*)>")
    name_email_regex = re.compile(r"(.*) <(.*?)>")

    # ENVIRONMENT VARIABLES
    # These are read when creating new commits.
    env_author_name = "GIT_AUTHOR_NAME"
    env_author_email = "GIT_AUTHOR_EMAIL"
    env_committer_name = "GIT_COMMITTER_NAME"
    env_committer_email = "GIT_COMMITTER_EMAIL"

    # CONFIGURATION KEYS
    conf_name = "name"
    conf_email = "email"

    __slots__ = ("name", "email")

    def __init__(self, name: Optional[str], email: Optional[str]) -> None:
        self.name = name
        self.email = email

    def __eq__(self, other: Any) -> bool:
        return self.name == other.name and self.email == other.email

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return hash((self.name, self.email))

    def __str__(self) -> str:
        return self.name if self.name else ""

    def __repr__(self) -> str:
        return '<git.Actor "%s <%s>">' % (self.name, self.email)

    @classmethod
    def _from_string(cls, string: str) -> "Actor":
        """Create an :class:`Actor` from a string.

        :param string:
            The string, which is expected to be in regular git format::

                John Doe <jdoe@example.com>

        :return:
            :class:`Actor`
        """
        m = cls.name_email_regex.search(string)
        if m:
            name, email = m.groups()
            return Actor(name, email)
        else:
            m = cls.name_only_regex.search(string)
            if m:
                return Actor(m.group(1), None)
            # Assume the best and use the whole string as name.
            return Actor(string, None)
            # END special case name
        # END handle name/email matching

    @classmethod
    def _main_actor(
        cls,
        env_name: str,
        env_email: str,
        config_reader: Union[None, "GitConfigParser", "SectionConstraint"] = None,
    ) -> "Actor":
        actor = Actor("", "")
        user_id = None  # We use this to avoid multiple calls to getpass.getuser().

        def default_email() -> str:
            nonlocal user_id
            if not user_id:
                user_id = get_user_id()
            return user_id

        def default_name() -> str:
            return default_email().split("@")[0]

        for attr, evar, cvar, default in (
            ("name", env_name, cls.conf_name, default_name),
            ("email", env_email, cls.conf_email, default_email),
        ):
            try:
                val = os.environ[evar]
                setattr(actor, attr, val)
            except KeyError:
                if config_reader is not None:
                    try:
                        val = config_reader.get("user", cvar)
                    except Exception:
                        val = default()
                    setattr(actor, attr, val)
                # END config-reader handling
                if not getattr(actor, attr):
                    setattr(actor, attr, default())
            # END handle name
        # END for each item to retrieve
        return actor

    @classmethod
    def committer(cls, config_reader: Union[None, "GitConfigParser", "SectionConstraint"] = None) -> "Actor":
        """
        :return:
            :class:`Actor` instance corresponding to the configured committer. It
            behaves similar to the git implementation, such that the environment will
            override configuration values of `config_reader`. If no value is set at all,
            it will be generated.

        :param config_reader:
            ConfigReader to use to retrieve the values from in case they are not set in
            the environment.
        """
        return cls._main_actor(cls.env_committer_name, cls.env_committer_email, config_reader)

    @classmethod
    def author(cls, config_reader: Union[None, "GitConfigParser", "SectionConstraint"] = None) -> "Actor":
        """Same as :meth:`committer`, but defines the main author. It may be specified
        in the environment, but defaults to the committer."""
        return cls._main_actor(cls.env_author_name, cls.env_author_email, config_reader)


class Stats:
    """Represents stat information as presented by git at the end of a merge. It is
    created from the output of a diff operation.

    Example::

     c = Commit( sha1 )
     s = c.stats
     s.total         # full-stat-dict
     s.files         # dict( filepath : stat-dict )

    ``stat-dict``

    A dictionary with the following keys and values::

      deletions = number of deleted lines as int
      insertions = number of inserted lines as int
      lines = total number of lines changed as int, or deletions + insertions
      change_type = type of change as str, A|C|D|M|R|T|U|X|B

    ``full-stat-dict``

    In addition to the items in the stat-dict, it features additional information::

     files = number of changed files as int
    """

    __slots__ = ("total", "files")

    def __init__(self, total: Total_TD, files: Dict[PathLike, Files_TD]) -> None:
        self.total = total
        self.files = files

    @classmethod
    def _list_from_string(cls, repo: "Repo", text: str) -> "Stats":
        """Create a :class:`Stats` object from output retrieved by
        :manpage:`git-diff(1)`.

        :return:
            :class:`git.Stats`
        """

        hsh: HSH_TD = {
            "total": {"insertions": 0, "deletions": 0, "lines": 0, "files": 0},
            "files": {},
        }
        for line in text.splitlines():
            (change_type, raw_insertions, raw_deletions, filename) = line.split("\t")
            insertions = raw_insertions != "-" and int(raw_insertions) or 0
            deletions = raw_deletions != "-" and int(raw_deletions) or 0
            hsh["total"]["insertions"] += insertions
            hsh["total"]["deletions"] += deletions
            hsh["total"]["lines"] += insertions + deletions
            hsh["total"]["files"] += 1
            files_dict: Files_TD = {
                "insertions": insertions,
                "deletions": deletions,
                "lines": insertions + deletions,
                "change_type": change_type,
            }
            hsh["files"][filename.strip()] = files_dict
        return Stats(hsh["total"], hsh["files"])


class IndexFileSHA1Writer:
    """Wrapper around a file-like object that remembers the SHA1 of the data written to
    it. It will write a sha when the stream is closed or if asked for explicitly using
    :meth:`write_sha`.

    Only useful to the index file.

    :note:
        Based on the dulwich project.
    """

    __slots__ = ("f", "sha1")

    def __init__(self, f: IO) -> None:
        self.f = f
        self.sha1 = make_sha(b"")

    def write(self, data: AnyStr) -> int:
        self.sha1.update(data)
        return self.f.write(data)

    def write_sha(self) -> bytes:
        sha = self.sha1.digest()
        self.f.write(sha)
        return sha

    def close(self) -> bytes:
        sha = self.write_sha()
        self.f.close()
        return sha

    def tell(self) -> int:
        return self.f.tell()


class LockFile:
    """Provides methods to obtain, check for, and release a file based lock which
    should be used to handle concurrent access to the same file.

    As we are a utility class to be derived from, we only use protected methods.

    Locks will automatically be released on destruction.
    """

    __slots__ = ("_file_path", "_owns_lock")

    def __init__(self, file_path: PathLike) -> None:
        self._file_path = file_path
        self._owns_lock = False

    def __del__(self) -> None:
        self._release_lock()

    def _lock_file_path(self) -> str:
        """:return: Path to lockfile"""
        return "%s.lock" % (self._file_path)

    def _has_lock(self) -> bool:
        """
        :return:
            True if we have a lock and if the lockfile still exists

        :raise AssertionError:
            If our lock-file does not exist.
        """
        return self._owns_lock

    def _obtain_lock_or_raise(self) -> None:
        """Create a lock file as flag for other instances, mark our instance as
        lock-holder.

        :raise IOError:
            If a lock was already present or a lock file could not be written.
        """
        if self._has_lock():
            return
        lock_file = self._lock_file_path()
        if osp.isfile(lock_file):
            raise IOError(
                "Lock for file %r did already exist, delete %r in case the lock is illegal"
                % (self._file_path, lock_file)
            )

        try:
            with open(lock_file, mode="w"):
                pass
        except OSError as e:
            raise IOError(str(e)) from e

        self._owns_lock = True

    def _obtain_lock(self) -> None:
        """The default implementation will raise if a lock cannot be obtained.

        Subclasses may override this method to provide a different implementation.
        """
        return self._obtain_lock_or_raise()

    def _release_lock(self) -> None:
        """Release our lock if we have one."""
        if not self._has_lock():
            return

        # If someone removed our file beforehand, lets just flag this issue instead of
        # failing, to make it more usable.
        lfp = self._lock_file_path()
        try:
            rmfile(lfp)
        except OSError:
            pass
        self._owns_lock = False


class BlockingLockFile(LockFile):
    """The lock file will block until a lock could be obtained, or fail after a
    specified timeout.

    :note:
        If the directory containing the lock was removed, an exception will be raised
        during the blocking period, preventing hangs as the lock can never be obtained.
    """

    __slots__ = ("_check_interval", "_max_block_time")

    def __init__(
        self,
        file_path: PathLike,
        check_interval_s: float = 0.3,
        max_block_time_s: int = sys.maxsize,
    ) -> None:
        """Configure the instance.

        :param check_interval_s:
            Period of time to sleep until the lock is checked the next time.
            By default, it waits a nearly unlimited time.

        :param max_block_time_s:
            Maximum amount of seconds we may lock.
        """
        super().__init__(file_path)
        self._check_interval = check_interval_s
        self._max_block_time = max_block_time_s

    def _obtain_lock(self) -> None:
        """This method blocks until it obtained the lock, or raises :exc:`IOError` if it
        ran out of time or if the parent directory was not available anymore.

        If this method returns, you are guaranteed to own the lock.
        """
        starttime = time.time()
        maxtime = starttime + float(self._max_block_time)
        while True:
            try:
                super()._obtain_lock()
            except IOError as e:
                # synity check: if the directory leading to the lockfile is not
                # readable anymore, raise an exception
                curtime = time.time()
                if not osp.isdir(osp.dirname(self._lock_file_path())):
                    msg = "Directory containing the lockfile %r was not readable anymore after waiting %g seconds" % (
                        self._lock_file_path(),
                        curtime - starttime,
                    )
                    raise IOError(msg) from e
                # END handle missing directory

                if curtime >= maxtime:
                    msg = "Waited %g seconds for lock at %r" % (
                        maxtime - starttime,
                        self._lock_file_path(),
                    )
                    raise IOError(msg) from e
                # END abort if we wait too long
                time.sleep(self._check_interval)
            else:
                break
        # END endless loop


class IterableList(List[T_IterableObj]):
    """List of iterable objects allowing to query an object by id or by named index::

     heads = repo.heads
     heads.master
     heads['master']
     heads[0]

    Iterable parent objects:

    * :class:`Commit <git.objects.Commit>`
    * :class:`Submodule <git.objects.submodule.base.Submodule>`
    * :class:`Reference <git.refs.reference.Reference>`
    * :class:`FetchInfo <git.remote.FetchInfo>`
    * :class:`PushInfo <git.remote.PushInfo>`

    Iterable via inheritance:

    * :class:`Head <git.refs.head.Head>`
    * :class:`TagReference <git.refs.tag.TagReference>`
    * :class:`RemoteReference <git.refs.remote.RemoteReference>`

    This requires an ``id_attribute`` name to be set which will be queried from its
    contained items to have a means for comparison.

    A prefix can be specified which is to be used in case the id returned by the items
    always contains a prefix that does not matter to the user, so it can be left out.
    """

    __slots__ = ("_id_attr", "_prefix")

    def __new__(cls, id_attr: str, prefix: str = "") -> "IterableList[T_IterableObj]":
        return super().__new__(cls)

    def __init__(self, id_attr: str, prefix: str = "") -> None:
        self._id_attr = id_attr
        self._prefix = prefix

    def __contains__(self, attr: object) -> bool:
        # First try identity match for performance.
        try:
            rval = list.__contains__(self, attr)
            if rval:
                return rval
        except (AttributeError, TypeError):
            pass
        # END handle match

        # Otherwise make a full name search.
        try:
            getattr(self, cast(str, attr))  # Use cast to silence mypy.
            return True
        except (AttributeError, TypeError):
            return False
        # END handle membership

    def __getattr__(self, attr: str) -> T_IterableObj:
        attr = self._prefix + attr
        for item in self:
            if getattr(item, self._id_attr) == attr:
                return item
        # END for each item
        return list.__getattribute__(self, attr)

    def __getitem__(self, index: Union[SupportsIndex, int, slice, str]) -> T_IterableObj:  # type: ignore[override]
        assert isinstance(index, (int, str, slice)), "Index of IterableList should be an int or str"

        if isinstance(index, int):
            return list.__getitem__(self, index)
        elif isinstance(index, slice):
            raise ValueError("Index should be an int or str")
        else:
            try:
                return getattr(self, index)
            except AttributeError as e:
                raise IndexError("No item found with id %r" % (self._prefix + index)) from e
        # END handle getattr

    def __delitem__(self, index: Union[SupportsIndex, int, slice, str]) -> None:
        assert isinstance(index, (int, str)), "Index of IterableList should be an int or str"

        delindex = cast(int, index)
        if not isinstance(index, int):
            delindex = -1
            name = self._prefix + index
            for i, item in enumerate(self):
                if getattr(item, self._id_attr) == name:
                    delindex = i
                    break
                # END search index
            # END for each item
            if delindex == -1:
                raise IndexError("Item with name %s not found" % name)
            # END handle error
        # END get index to delete
        list.__delitem__(self, delindex)


@runtime_checkable
class IterableObj(Protocol):
    """Defines an interface for iterable items, so there is a uniform way to retrieve
    and iterate items within the git repository.

    Subclasses:

    * :class:`Submodule <git.objects.submodule.base.Submodule>`
    * :class:`Commit <git.objects.Commit>`
    * :class:`Reference <git.refs.reference.Reference>`
    * :class:`PushInfo <git.remote.PushInfo>`
    * :class:`FetchInfo <git.remote.FetchInfo>`
    * :class:`Remote <git.remote.Remote>`
    """

    __slots__ = ()

    _id_attribute_: str

    @classmethod
    @abstractmethod
    def iter_items(cls, repo: "Repo", *args: Any, **kwargs: Any) -> Iterator[T_IterableObj]:
        # Return-typed to be compatible with subtypes e.g. Remote.
        """Find (all) items of this type.

        Subclasses can specify `args` and `kwargs` differently, and may use them for
        filtering. However, when the method is called with no additional positional or
        keyword arguments, subclasses are obliged to to yield all items.

        :return:
            Iterator yielding Items
        """
        raise NotImplementedError("To be implemented by Subclass")

    @classmethod
    def list_items(cls, repo: "Repo", *args: Any, **kwargs: Any) -> IterableList[T_IterableObj]:
        """Find (all) items of this type and collect them into a list.

        For more information about the arguments, see :meth:`iter_items`.

        :note:
            Favor the :meth:`iter_items` method as it will avoid eagerly collecting all
            items. When there are many items, that can slow performance and increase
            memory usage.

        :return:
            list(Item,...) list of item instances
        """
        out_list: IterableList = IterableList(cls._id_attribute_)
        out_list.extend(cls.iter_items(repo, *args, **kwargs))
        return out_list


class IterableClassWatcher(type):
    """Metaclass that issues :exc:`DeprecationWarning` when :class:`git.util.Iterable`
    is subclassed."""

    def __init__(cls, name: str, bases: Tuple, clsdict: Dict) -> None:
        for base in bases:
            if type(base) is IterableClassWatcher:
                warnings.warn(
                    f"GitPython Iterable subclassed by {name}."
                    " Iterable is deprecated due to naming clash since v3.1.18"
                    " and will be removed in 4.0.0."
                    " Use IterableObj instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )


class Iterable(metaclass=IterableClassWatcher):
    """Deprecated, use :class:`IterableObj` instead.

    Defines an interface for iterable items, so there is a uniform way to retrieve
    and iterate items within the git repository.
    """

    __slots__ = ()

    _id_attribute_ = "attribute that most suitably identifies your instance"

    @classmethod
    def iter_items(cls, repo: "Repo", *args: Any, **kwargs: Any) -> Any:
        """Deprecated, use :class:`IterableObj` instead.

        Find (all) items of this type.

        See :meth:`IterableObj.iter_items` for details on usage.

        :return:
            Iterator yielding Items
        """
        raise NotImplementedError("To be implemented by Subclass")

    @classmethod
    def list_items(cls, repo: "Repo", *args: Any, **kwargs: Any) -> Any:
        """Deprecated, use :class:`IterableObj` instead.

        Find (all) items of this type and collect them into a list.

        See :meth:`IterableObj.list_items` for details on usage.

        :return:
            list(Item,...) list of item instances
        """
        out_list: Any = IterableList(cls._id_attribute_)
        out_list.extend(cls.iter_items(repo, *args, **kwargs))
        return out_list


# } END classes

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\emulation.py ===
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
class SafeAreaInsets:
    #: Overrides safe-area-inset-top.
    top: typing.Optional[int] = None

    #: Overrides safe-area-max-inset-top.
    top_max: typing.Optional[int] = None

    #: Overrides safe-area-inset-left.
    left: typing.Optional[int] = None

    #: Overrides safe-area-max-inset-left.
    left_max: typing.Optional[int] = None

    #: Overrides safe-area-inset-bottom.
    bottom: typing.Optional[int] = None

    #: Overrides safe-area-max-inset-bottom.
    bottom_max: typing.Optional[int] = None

    #: Overrides safe-area-inset-right.
    right: typing.Optional[int] = None

    #: Overrides safe-area-max-inset-right.
    right_max: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        if self.top is not None:
            json['top'] = self.top
        if self.top_max is not None:
            json['topMax'] = self.top_max
        if self.left is not None:
            json['left'] = self.left
        if self.left_max is not None:
            json['leftMax'] = self.left_max
        if self.bottom is not None:
            json['bottom'] = self.bottom
        if self.bottom_max is not None:
            json['bottomMax'] = self.bottom_max
        if self.right is not None:
            json['right'] = self.right
        if self.right_max is not None:
            json['rightMax'] = self.right_max
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            top=int(json['top']) if 'top' in json else None,
            top_max=int(json['topMax']) if 'topMax' in json else None,
            left=int(json['left']) if 'left' in json else None,
            left_max=int(json['leftMax']) if 'leftMax' in json else None,
            bottom=int(json['bottom']) if 'bottom' in json else None,
            bottom_max=int(json['bottomMax']) if 'bottomMax' in json else None,
            right=int(json['right']) if 'right' in json else None,
            right_max=int(json['rightMax']) if 'rightMax' in json else None,
        )


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


def set_safe_area_insets_override(
        insets: SafeAreaInsets
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides the values for env(safe-area-inset-*) and env(safe-area-max-inset-*). Unset values will cause the
    respective variables to be undefined, even if previously overridden.

    **EXPERIMENTAL**

    :param insets:
    '''
    params: T_JSON_DICT = dict()
    params['insets'] = insets.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setSafeAreaInsetsOverride',
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
    :param display_feature: **(EXPERIMENTAL)** *(Optional)* If set, the display feature of a multi-segment screen. If not set, multi-segment support is turned-off. Deprecated, use Emulation.setDisplayFeaturesOverride.
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


def set_display_features_override(
        features: typing.List[DisplayFeature]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Start using the given display features to pupulate the Viewport Segments API.
    This override can also be set in setDeviceMetricsOverride().

    **EXPERIMENTAL**

    :param features:
    '''
    params: T_JSON_DICT = dict()
    params['features'] = [i.to_json() for i in features]
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setDisplayFeaturesOverride',
        'params': params,
    }
    json = yield cmd_dict


def clear_display_features_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears the display features override set with either setDeviceMetricsOverride()
    or setDisplayFeaturesOverride() and starts using display features from the
    platform again.
    Does nothing if no override is set.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.clearDisplayFeaturesOverride',
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
        accuracy: typing.Optional[float] = None,
        altitude: typing.Optional[float] = None,
        altitude_accuracy: typing.Optional[float] = None,
        heading: typing.Optional[float] = None,
        speed: typing.Optional[float] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides the Geolocation Position or Error. Omitting latitude, longitude or
    accuracy emulates position unavailable.

    :param latitude: *(Optional)* Mock latitude
    :param longitude: *(Optional)* Mock longitude
    :param accuracy: *(Optional)* Mock accuracy
    :param altitude: *(Optional)* Mock altitude
    :param altitude_accuracy: *(Optional)* Mock altitudeAccuracy
    :param heading: *(Optional)* Mock heading
    :param speed: *(Optional)* Mock speed
    '''
    params: T_JSON_DICT = dict()
    if latitude is not None:
        params['latitude'] = latitude
    if longitude is not None:
        params['longitude'] = longitude
    if accuracy is not None:
        params['accuracy'] = accuracy
    if altitude is not None:
        params['altitude'] = altitude
    if altitude_accuracy is not None:
        params['altitudeAccuracy'] = altitude_accuracy
    if heading is not None:
        params['heading'] = heading
    if speed is not None:
        params['speed'] = speed
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


def set_small_viewport_height_difference_override(
        difference: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Allows overriding the difference between the small and large viewport sizes, which determine the
    value of the ``svh`` and ``lvh`` unit, respectively. Only supported for top-level frames.

    **EXPERIMENTAL**

    :param difference: This will cause an element of size 100svh to be ```difference``` pixels smaller than an element of size 100lvh.
    '''
    params: T_JSON_DICT = dict()
    params['difference'] = difference
    cmd_dict: T_JSON_DICT = {
        'method': 'Emulation.setSmallViewportHeightDifferenceOverride',
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

# === NexusCore/openenv\Lib\site-packages\joblib\externals\loky\process_executor.py ===
###############################################################################
# Re-implementation of the ProcessPoolExecutor more robust to faults
#
# author: Thomas Moreau and Olivier Grisel
#
# adapted from concurrent/futures/process_pool_executor.py (17/02/2017)
#  * Add an extra management thread to detect executor_manager_thread failures,
#  * Improve the shutdown process to avoid deadlocks,
#  * Add timeout for workers,
#  * More robust pickling process.
#
# Copyright 2009 Brian Quinlan. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

"""Implements ProcessPoolExecutor.

The follow diagram and text describe the data-flow through the system:

|======================= In-process =====================|== Out-of-process ==|

+----------+     +----------+       +--------+     +-----------+    +---------+
|          |  => | Work Ids |       |        |     | Call Q    |    | Process |
|          |     +----------+       |        |     +-----------+    |  Pool   |
|          |     | ...      |       |        |     | ...       |    +---------+
|          |     | 6        |    => |        |  => | 5, call() | => |         |
|          |     | 7        |       |        |     | ...       |    |         |
| Process  |     | ...      |       | Local  |     +-----------+    | Process |
|  Pool    |     +----------+       | Worker |                      |  #1..n  |
| Executor |                        | Thread |                      |         |
|          |     +----------- +     |        |     +-----------+    |         |
|          | <=> | Work Items | <=> |        | <=  | Result Q  | <= |         |
|          |     +------------+     |        |     +-----------+    |         |
|          |     | 6: call()  |     |        |     | ...       |    |         |
|          |     |    future  |     +--------+     | 4, result |    |         |
|          |     | ...        |                    | 3, except |    |         |
+----------+     +------------+                    +-----------+    +---------+

Executor.submit() called:
- creates a uniquely numbered _WorkItem and adds it to the "Work Items" dict
- adds the id of the _WorkItem to the "Work Ids" queue

Local worker thread:
- reads work ids from the "Work Ids" queue and looks up the corresponding
  WorkItem from the "Work Items" dict: if the work item has been cancelled then
  it is simply removed from the dict, otherwise it is repackaged as a
  _CallItem and put in the "Call Q". New _CallItems are put in the "Call Q"
  until "Call Q" is full. NOTE: the size of the "Call Q" is kept small because
  calls placed in the "Call Q" can no longer be cancelled with Future.cancel().
- reads _ResultItems from "Result Q", updates the future stored in the
  "Work Items" dict and deletes the dict entry

Process #1..n:
- reads _CallItems from "Call Q", executes the calls, and puts the resulting
  _ResultItems in "Result Q"
"""


__author__ = "Thomas Moreau (thomas.moreau.2010@gmail.com)"


import faulthandler
import os
import gc
import sys
import queue
import struct
import weakref
import warnings
import itertools
import traceback
import threading
from time import time, sleep
import multiprocessing as mp
from functools import partial
from pickle import PicklingError
from concurrent.futures import Executor
from concurrent.futures._base import LOGGER
from concurrent.futures.process import BrokenProcessPool as _BPPException
from multiprocessing.connection import wait

from ._base import Future
from .backend import get_context
from .backend.context import cpu_count, _MAX_WINDOWS_WORKERS
from .backend.queues import Queue, SimpleQueue
from .backend.reduction import set_loky_pickler, get_loky_pickler_name
from .backend.utils import kill_process_tree, get_exitcodes_terminated_worker
from .initializers import _prepare_initializer


# Mechanism to prevent infinite process spawning. When a worker of a
# ProcessPoolExecutor nested in MAX_DEPTH Executor tries to create a new
# Executor, a LokyRecursionError is raised
MAX_DEPTH = int(os.environ.get("LOKY_MAX_DEPTH", 10))
_CURRENT_DEPTH = 0

# Minimum time interval between two consecutive memory leak protection checks.
_MEMORY_LEAK_CHECK_DELAY = 1.0

# Number of bytes of memory usage allowed over the reference process size.
_MAX_MEMORY_LEAK_SIZE = int(3e8)


try:
    from psutil import Process

    _USE_PSUTIL = True

    def _get_memory_usage(pid, force_gc=False):
        if force_gc:
            gc.collect()

        mem_size = Process(pid).memory_info().rss
        mp.util.debug(f"psutil return memory size: {mem_size}")
        return mem_size

except ImportError:
    _USE_PSUTIL = False


class _ThreadWakeup:
    def __init__(self):
        self._closed = False
        self._reader, self._writer = mp.Pipe(duplex=False)

    def close(self):
        if not self._closed:
            self._closed = True
            self._writer.close()
            self._reader.close()

    def wakeup(self):
        if not self._closed:
            self._writer.send_bytes(b"")

    def clear(self):
        if not self._closed:
            while self._reader.poll():
                self._reader.recv_bytes()


class _ExecutorFlags:
    """necessary references to maintain executor states without preventing gc

    It permits to keep the information needed by executor_manager_thread
    and crash_detection_thread to maintain the pool without preventing the
    garbage collection of unreferenced executors.
    """

    def __init__(self, shutdown_lock):

        self.shutdown = False
        self.broken = None
        self.kill_workers = False
        self.shutdown_lock = shutdown_lock

    def flag_as_shutting_down(self, kill_workers=None):
        with self.shutdown_lock:
            self.shutdown = True
            if kill_workers is not None:
                self.kill_workers = kill_workers

    def flag_as_broken(self, broken):
        with self.shutdown_lock:
            self.shutdown = True
            self.broken = broken


# Prior to 3.9, executor_manager_thread is created as daemon thread. This means
# that it is not joined automatically when the interpreter is shutting down.
# To work around this problem, an exit handler is installed to tell the
# thread to exit when the interpreter is shutting down and then waits until
# it finishes. The thread needs to be daemonized because the atexit hooks are
# called after all non daemonized threads are joined.
#
# Starting 3.9, there exists a specific atexit hook to be called before joining
# the threads so the executor_manager_thread does not need to be daemonized
# anymore.
#
# The atexit hooks are registered when starting the first ProcessPoolExecutor
# to avoid import having an effect on the interpreter.

_global_shutdown = False
_global_shutdown_lock = threading.Lock()
_threads_wakeups = weakref.WeakKeyDictionary()


def _python_exit():
    global _global_shutdown
    _global_shutdown = True

    # Materialize the list of items to avoid error due to iterating over
    # changing size dictionary.
    items = list(_threads_wakeups.items())
    if len(items) > 0:
        mp.util.debug(
            f"Interpreter shutting down. Waking up {len(items)}"
            f"executor_manager_thread:\n{items}"
        )

    # Wake up the executor_manager_thread's so they can detect the interpreter
    # is shutting down and exit.
    for _, (shutdown_lock, thread_wakeup) in items:
        with shutdown_lock:
            thread_wakeup.wakeup()

    # Collect the executor_manager_thread's to make sure we exit cleanly.
    for thread, _ in items:
        # This locks is to prevent situations where an executor is gc'ed in one
        # thread while the atexit finalizer is running in another thread.
        with _global_shutdown_lock:
            thread.join()


# With the fork context, _thread_wakeups is propagated to children.
# Clear it after fork to avoid some situation that can cause some
# freeze when joining the workers.
mp.util.register_after_fork(_threads_wakeups, lambda obj: obj.clear())


# Module variable to register the at_exit call
process_pool_executor_at_exit = None

# Controls how many more calls than processes will be queued in the call queue.
# A smaller number will mean that processes spend more time idle waiting for
# work while a larger number will make Future.cancel() succeed less frequently
# (Futures in the call queue cannot be cancelled).
EXTRA_QUEUED_CALLS = 1


class _RemoteTraceback(Exception):
    """Embed stringification of remote traceback in local traceback"""

    def __init__(self, tb=None):
        self.tb = f'\n"""\n{tb}"""'

    def __str__(self):
        return self.tb


# Do not inherit from BaseException to mirror
# concurrent.futures.process._ExceptionWithTraceback
class _ExceptionWithTraceback:
    def __init__(self, exc):
        tb = getattr(exc, "__traceback__", None)
        if tb is None:
            _, _, tb = sys.exc_info()
        tb = traceback.format_exception(type(exc), exc, tb)
        tb = "".join(tb)
        self.exc = exc
        self.tb = tb

    def __reduce__(self):
        return _rebuild_exc, (self.exc, self.tb)


def _rebuild_exc(exc, tb):
    exc.__cause__ = _RemoteTraceback(tb)
    return exc


class _WorkItem:

    __slots__ = ["future", "fn", "args", "kwargs"]

    def __init__(self, future, fn, args, kwargs):
        self.future = future
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


class _ResultItem:
    def __init__(self, work_id, exception=None, result=None):
        self.work_id = work_id
        self.exception = exception
        self.result = result


class _CallItem:
    def __init__(self, work_id, fn, args, kwargs):
        self.work_id = work_id
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

        # Store the current loky_pickler so it is correctly set in the worker
        self.loky_pickler = get_loky_pickler_name()

    def __call__(self):
        set_loky_pickler(self.loky_pickler)
        return self.fn(*self.args, **self.kwargs)

    def __repr__(self):
        return (
            f"CallItem({self.work_id}, {self.fn}, {self.args}, {self.kwargs})"
        )


class _SafeQueue(Queue):
    """Safe Queue set exception to the future object linked to a job"""

    def __init__(
        self,
        max_size=0,
        ctx=None,
        pending_work_items=None,
        running_work_items=None,
        thread_wakeup=None,
        shutdown_lock=None,
        reducers=None,
    ):
        self.thread_wakeup = thread_wakeup
        self.shutdown_lock = shutdown_lock
        self.pending_work_items = pending_work_items
        self.running_work_items = running_work_items
        super().__init__(max_size, reducers=reducers, ctx=ctx)

    def _on_queue_feeder_error(self, e, obj):
        if isinstance(obj, _CallItem):
            # format traceback only works on python3
            if isinstance(e, struct.error):
                raised_error = RuntimeError(
                    "The task could not be sent to the workers as it is too "
                    "large for `send_bytes`."
                )
            else:
                raised_error = PicklingError(
                    "Could not pickle the task to send it to the workers."
                )
            tb = traceback.format_exception(
                type(e), e, getattr(e, "__traceback__", None)
            )
            raised_error.__cause__ = _RemoteTraceback("".join(tb))
            work_item = self.pending_work_items.pop(obj.work_id, None)
            self.running_work_items.remove(obj.work_id)
            # work_item can be None if another process terminated. In this
            # case, the executor_manager_thread fails all work_items with
            # BrokenProcessPool
            if work_item is not None:
                work_item.future.set_exception(raised_error)
                del work_item
            with self.shutdown_lock:
                self.thread_wakeup.wakeup()
        else:
            super()._on_queue_feeder_error(e, obj)


def _get_chunks(chunksize, *iterables):
    """Iterates over zip()ed iterables in chunks."""
    it = zip(*iterables)
    while True:
        chunk = tuple(itertools.islice(it, chunksize))
        if not chunk:
            return
        yield chunk


def _process_chunk(fn, chunk):
    """Processes a chunk of an iterable passed to map.

    Runs the function passed to map() on a chunk of the
    iterable passed to map.

    This function is run in a separate process.

    """
    return [fn(*args) for args in chunk]


def _sendback_result(result_queue, work_id, result=None, exception=None):
    """Safely send back the given result or exception"""
    try:
        result_queue.put(
            _ResultItem(work_id, result=result, exception=exception)
        )
    except BaseException as e:
        exc = _ExceptionWithTraceback(e)
        result_queue.put(_ResultItem(work_id, exception=exc))


def _enable_faulthandler_if_needed():
    if "PYTHONFAULTHANDLER" in os.environ:
        # Respect the environment variable to configure faulthandler. This
        # makes it possible to never enable faulthandler in the loky workers by
        # setting PYTHONFAULTHANDLER=0 explicitly in the environment.
        mp.util.debug(
            f"faulthandler explicitly configured by environment variable: "
            f"PYTHONFAULTHANDLER={os.environ['PYTHONFAULTHANDLER']}."
        )
    else:
        if faulthandler.is_enabled():
            # Fault handler is already enabled, possibly via a custom
            # initializer to customize the behavior.
            mp.util.debug("faulthandler already enabled.")
        else:
            # Enable faulthandler by default with default paramaters otherwise.
            mp.util.debug(
                "Enabling faulthandler to report tracebacks on worker crashes."
            )
            faulthandler.enable()


def _process_worker(
    call_queue,
    result_queue,
    initializer,
    initargs,
    processes_management_lock,
    timeout,
    worker_exit_lock,
    current_depth,
):
    """Evaluates calls from call_queue and places the results in result_queue.

    This worker is run in a separate process.

    Args:
        call_queue: A ctx.Queue of _CallItems that will be read and
            evaluated by the worker.
        result_queue: A ctx.Queue of _ResultItems that will written
            to by the worker.
        initializer: A callable initializer, or None
        initargs: A tuple of args for the initializer
        processes_management_lock: A ctx.Lock avoiding worker timeout while
            some workers are being spawned.
        timeout: maximum time to wait for a new item in the call_queue. If that
            time is expired, the worker will shutdown.
        worker_exit_lock: Lock to avoid flagging the executor as broken on
            workers timeout.
        current_depth: Nested parallelism level, to avoid infinite spawning.
    """
    if initializer is not None:
        try:
            initializer(*initargs)
        except BaseException:
            LOGGER.critical("Exception in initializer:", exc_info=True)
            # The parent will notice that the process stopped and
            # mark the pool broken
            return

    # set the global _CURRENT_DEPTH mechanism to limit recursive call
    global _CURRENT_DEPTH
    _CURRENT_DEPTH = current_depth
    _process_reference_size = None
    _last_memory_leak_check = None
    pid = os.getpid()

    mp.util.debug(f"Worker started with timeout={timeout}")
    _enable_faulthandler_if_needed()

    while True:
        try:
            call_item = call_queue.get(block=True, timeout=timeout)
            if call_item is None:
                mp.util.info("Shutting down worker on sentinel")
        except queue.Empty:
            mp.util.info(f"Shutting down worker after timeout {timeout:0.3f}s")
            if processes_management_lock.acquire(block=False):
                processes_management_lock.release()
                call_item = None
            else:
                mp.util.info("Could not acquire processes_management_lock")
                continue
        except BaseException:
            previous_tb = traceback.format_exc()
            try:
                result_queue.put(_RemoteTraceback(previous_tb))
            except BaseException:
                # If we cannot format correctly the exception, at least print
                # the traceback.
                print(previous_tb)
            mp.util.debug("Exiting with code 1")
            sys.exit(1)
        if call_item is None:
            # Notify queue management thread about worker shutdown
            result_queue.put(pid)
            is_clean = worker_exit_lock.acquire(True, timeout=30)

            # Early notify any loky executor running in this worker process
            # (nested parallelism) that this process is about to shutdown to
            # avoid a deadlock waiting undifinitely for the worker to finish.
            _python_exit()

            if is_clean:
                mp.util.debug("Exited cleanly")
            else:
                mp.util.info("Main process did not release worker_exit")
            return
        try:
            r = call_item()
        except BaseException as e:
            exc = _ExceptionWithTraceback(e)
            result_queue.put(_ResultItem(call_item.work_id, exception=exc))
        else:
            _sendback_result(result_queue, call_item.work_id, result=r)
            del r

        # Free the resource as soon as possible, to avoid holding onto
        # open files or shared memory that is not needed anymore
        del call_item

        if _USE_PSUTIL:
            if _process_reference_size is None:
                # Make reference measurement after the first call
                _process_reference_size = _get_memory_usage(pid, force_gc=True)
                _last_memory_leak_check = time()
                continue
            if time() - _last_memory_leak_check > _MEMORY_LEAK_CHECK_DELAY:
                mem_usage = _get_memory_usage(pid)
                _last_memory_leak_check = time()
                if mem_usage - _process_reference_size < _MAX_MEMORY_LEAK_SIZE:
                    # Memory usage stays within bounds: everything is fine.
                    continue

                # Check again memory usage; this time take the measurement
                # after a forced garbage collection to break any reference
                # cycles.
                mem_usage = _get_memory_usage(pid, force_gc=True)
                _last_memory_leak_check = time()
                if mem_usage - _process_reference_size < _MAX_MEMORY_LEAK_SIZE:
                    # The GC managed to free the memory: everything is fine.
                    continue

                # The process is leaking memory: let the master process
                # know that we need to start a new worker.
                mp.util.info("Memory leak detected: shutting down worker")
                result_queue.put(pid)
                with worker_exit_lock:
                    mp.util.debug("Exit due to memory leak")
                    return
        else:
            # if psutil is not installed, trigger gc.collect events
            # regularly to limit potential memory leaks due to reference cycles
            if _last_memory_leak_check is None or (
                time() - _last_memory_leak_check > _MEMORY_LEAK_CHECK_DELAY
            ):
                gc.collect()
                _last_memory_leak_check = time()


class _ExecutorManagerThread(threading.Thread):
    """Manages the communication between this process and the worker processes.

    The manager is run in a local thread.

    Args:
        executor: A reference to the ProcessPoolExecutor that owns
            this thread. A weakref will be own by the manager as well as
            references to internal objects used to introspect the state of
            the executor.
    """

    def __init__(self, executor):
        # Store references to necessary internals of the executor.

        # A _ThreadWakeup to allow waking up the executor_manager_thread from
        # the main Thread and avoid deadlocks caused by permanently
        # locked queues.
        self.thread_wakeup = executor._executor_manager_thread_wakeup
        self.shutdown_lock = executor._shutdown_lock

        # A weakref.ref to the ProcessPoolExecutor that owns this thread. Used
        # to determine if the ProcessPoolExecutor has been garbage collected
        # and that the manager can exit.
        # When the executor gets garbage collected, the weakref callback
        # will wake up the queue management thread so that it can terminate
        # if there is no pending work item.
        def weakref_cb(
            _,
            thread_wakeup=self.thread_wakeup,
            shutdown_lock=self.shutdown_lock,
        ):
            if mp is not None:
                # At this point, the multiprocessing module can already be
                # garbage collected. We only log debug info when still
                # possible.
                mp.util.debug(
                    "Executor collected: triggering callback for"
                    " QueueManager wakeup"
                )
            with shutdown_lock:
                thread_wakeup.wakeup()

        self.executor_reference = weakref.ref(executor, weakref_cb)

        # The flags of the executor
        self.executor_flags = executor._flags

        # A list of the ctx.Process instances used as workers.
        self.processes = executor._processes

        # A ctx.Queue that will be filled with _CallItems derived from
        # _WorkItems for processing by the process workers.
        self.call_queue = executor._call_queue

        # A ctx.SimpleQueue of _ResultItems generated by the process workers.
        self.result_queue = executor._result_queue

        # A queue.Queue of work ids e.g. Queue([5, 6, ...]).
        self.work_ids_queue = executor._work_ids

        # A dict mapping work ids to _WorkItems e.g.
        #     {5: <_WorkItem...>, 6: <_WorkItem...>, ...}
        self.pending_work_items = executor._pending_work_items

        # A list of the work_ids that are currently running
        self.running_work_items = executor._running_work_items

        # A lock to avoid concurrent shutdown of workers on timeout and spawn
        # of new processes or shut down
        self.processes_management_lock = executor._processes_management_lock

        super().__init__(name="ExecutorManagerThread")
        if sys.version_info < (3, 9):
            self.daemon = True

    def run(self):
        # Main loop for the executor manager thread.

        while True:
            self.add_call_item_to_queue()

            result_item, is_broken, bpe = self.wait_result_broken_or_wakeup()

            if is_broken:
                self.terminate_broken(bpe)
                return
            if result_item is not None:
                self.process_result_item(result_item)
                # Delete reference to result_item to avoid keeping references
                # while waiting on new results.
                del result_item

            if self.is_shutting_down():
                self.flag_executor_shutting_down()

                # Since no new work items can be added, it is safe to shutdown
                # this thread if there are no pending work items.
                if not self.pending_work_items:
                    self.join_executor_internals()
                    return

    def add_call_item_to_queue(self):
        # Fills call_queue with _WorkItems from pending_work_items.
        # This function never blocks.
        while True:
            if self.call_queue.full():
                return
            try:
                work_id = self.work_ids_queue.get(block=False)
            except queue.Empty:
                return
            else:
                work_item = self.pending_work_items[work_id]

                if work_item.future.set_running_or_notify_cancel():
                    self.running_work_items += [work_id]
                    self.call_queue.put(
                        _CallItem(
                            work_id,
                            work_item.fn,
                            work_item.args,
                            work_item.kwargs,
                        ),
                        block=True,
                    )
                else:
                    del self.pending_work_items[work_id]
                    continue

    def wait_result_broken_or_wakeup(self):
        # Wait for a result to be ready in the result_queue while checking
        # that all worker processes are still running, or for a wake up
        # signal send. The wake up signals come either from new tasks being
        # submitted, from the executor being shutdown/gc-ed, or from the
        # shutdown of the python interpreter.
        result_reader = self.result_queue._reader
        wakeup_reader = self.thread_wakeup._reader
        readers = [result_reader, wakeup_reader]
        worker_sentinels = [p.sentinel for p in list(self.processes.values())]
        ready = wait(readers + worker_sentinels)

        bpe = None
        is_broken = True
        result_item = None
        if result_reader in ready:
            try:
                result_item = result_reader.recv()
                if isinstance(result_item, _RemoteTraceback):
                    bpe = BrokenProcessPool(
                        "A task has failed to un-serialize. Please ensure that"
                        " the arguments of the function are all picklable."
                    )
                    bpe.__cause__ = result_item
                else:
                    is_broken = False
            except BaseException as e:
                bpe = BrokenProcessPool(
                    "A result has failed to un-serialize. Please ensure that "
                    "the objects returned by the function are always "
                    "picklable."
                )
                tb = traceback.format_exception(
                    type(e), e, getattr(e, "__traceback__", None)
                )
                bpe.__cause__ = _RemoteTraceback("".join(tb))

        elif wakeup_reader in ready:
            # This is simply a wake-up event that might either trigger putting
            # more tasks in the queue or trigger the clean up of resources.
            is_broken = False
        else:
            # A worker has terminated and we don't know why, set the state of
            # the executor as broken
            exit_codes = ""
            if sys.platform != "win32":
                # In Windows, introspecting terminated workers exitcodes seems
                # unstable, therefore they are not appended in the exception
                # message.
                exit_codes = (
                    "\nThe exit codes of the workers are "
                    f"{get_exitcodes_terminated_worker(self.processes)}"
                )
            mp.util.debug(
                "A worker unexpectedly terminated. Workers that "
                "might have caused the breakage: "
                + str(
                    {
                        p.name: p.exitcode
                        for p in list(self.processes.values())
                        if p is not None and p.sentinel in ready
                    }
                )
            )
            bpe = TerminatedWorkerError(
                "A worker process managed by the executor was unexpectedly "
                "terminated. This could be caused by a segmentation fault "
                "while calling the function or by an excessive memory usage "
                "causing the Operating System to kill the worker.\n"
                f"{exit_codes}\n"
                "Detailed tracebacks of the workers should have been printed "
                "to stderr in the executor process if faulthandler was not "
                "disabled."
            )

        self.thread_wakeup.clear()

        return result_item, is_broken, bpe

    def process_result_item(self, result_item):
        # Process the received a result_item. This can be either the PID of a
        # worker that exited gracefully or a _ResultItem

        if isinstance(result_item, int):
            # Clean shutdown of a worker using its PID, either on request
            # by the executor.shutdown method or by the timeout of the worker
            # itself: we should not mark the executor as broken.
            with self.processes_management_lock:
                p = self.processes.pop(result_item, None)

            # p can be None if the executor is concurrently shutting down.
            if p is not None:
                p._worker_exit_lock.release()
                mp.util.debug(
                    f"joining {p.name} when processing {p.pid} as result_item"
                )
                p.join()
                del p

            # Make sure the executor have the right number of worker, even if a
            # worker timeout while some jobs were submitted. If some work is
            # pending or there is less processes than running items, we need to
            # start a new Process and raise a warning.
            n_pending = len(self.pending_work_items)
            n_running = len(self.running_work_items)
            if n_pending - n_running > 0 or n_running > len(self.processes):
                executor = self.executor_reference()
                if (
                    executor is not None
                    and len(self.processes) < executor._max_workers
                ):
                    warnings.warn(
                        "A worker stopped while some jobs were given to the "
                        "executor. This can be caused by a too short worker "
                        "timeout or by a memory leak.",
                        UserWarning,
                    )
                    with executor._processes_management_lock:
                        executor._adjust_process_count()
                    executor = None
        else:
            # Received a _ResultItem so mark the future as completed.
            work_item = self.pending_work_items.pop(result_item.work_id, None)
            # work_item can be None if another process terminated (see above)
            if work_item is not None:
                if result_item.exception:
                    work_item.future.set_exception(result_item.exception)
                else:
                    work_item.future.set_result(result_item.result)
                self.running_work_items.remove(result_item.work_id)

    def is_shutting_down(self):
        # Check whether we should start shutting down the executor.
        executor = self.executor_reference()
        # No more work items can be added if:
        #   - The interpreter is shutting down OR
        #   - The executor that owns this thread is not broken AND
        #        * The executor that owns this worker has been collected OR
        #        * The executor that owns this worker has been shutdown.
        # If the executor is broken, it should be detected in the next loop.
        return _global_shutdown or (
            (executor is None or self.executor_flags.shutdown)
            and not self.executor_flags.broken
        )

    def terminate_broken(self, bpe):
        # Terminate the executor because it is in a broken state. The bpe
        # argument can be used to display more information on the error that
        # lead the executor into becoming broken.

        # Mark the process pool broken so that submits fail right now.
        self.executor_flags.flag_as_broken(bpe)

        # Mark pending tasks as failed.
        for work_item in self.pending_work_items.values():
            work_item.future.set_exception(bpe)
            # Delete references to object. See issue16284
            del work_item
        self.pending_work_items.clear()

        # Terminate remaining workers forcibly: the queues or their
        # locks may be in a dirty state and block forever.
        self.kill_workers(reason="broken executor")

        # clean up resources
        self.join_executor_internals()

    def flag_executor_shutting_down(self):
        # Flag the executor as shutting down and cancel remaining tasks if
        # requested as early as possible if it is not gc-ed yet.
        self.executor_flags.flag_as_shutting_down()

        # Cancel pending work items if requested.
        if self.executor_flags.kill_workers:
            while self.pending_work_items:
                _, work_item = self.pending_work_items.popitem()
                work_item.future.set_exception(
                    ShutdownExecutorError(
                        "The Executor was shutdown with `kill_workers=True` "
                        "before this job could complete."
                    )
                )
                del work_item

            # Kill the remaining worker forcibly to no waste time joining them
            self.kill_workers(reason="executor shutting down")

    def kill_workers(self, reason=""):
        # Terminate the remaining workers using SIGKILL. This function also
        # terminates descendant workers of the children in case there is some
        # nested parallelism.
        while self.processes:
            _, p = self.processes.popitem()
            mp.util.debug(f"terminate process {p.name}, reason: {reason}")
            try:
                kill_process_tree(p)
            except ProcessLookupError:  # pragma: no cover
                pass

    def shutdown_workers(self):
        # shutdown all workers in self.processes

        # Create a list to avoid RuntimeError due to concurrent modification of
        # processes. nb_children_alive is thus an upper bound. Also release the
        # processes' _worker_exit_lock to accelerate the shutdown procedure, as
        # there is no need for hand-shake here.
        with self.processes_management_lock:
            n_children_to_stop = 0
            for p in list(self.processes.values()):
                mp.util.debug(f"releasing worker exit lock on {p.name}")
                p._worker_exit_lock.release()
                n_children_to_stop += 1

        mp.util.debug(f"found {n_children_to_stop} processes to stop")

        # Send the right number of sentinels, to make sure all children are
        # properly terminated. Do it with a mechanism that avoid hanging on
        # Full queue when all workers have already been shutdown.
        n_sentinels_sent = 0
        cooldown_time = 0.001
        while (
            n_sentinels_sent < n_children_to_stop
            and self.get_n_children_alive() > 0
        ):
            for _ in range(n_children_to_stop - n_sentinels_sent):
                try:
                    self.call_queue.put_nowait(None)
                    n_sentinels_sent += 1
                except queue.Full as e:
                    if cooldown_time > 5.0:
                        mp.util.info(
                            "failed to send all sentinels and exit with error."
                            f"\ncall_queue size={self.call_queue._maxsize}; "
                            f" full is {self.call_queue.full()}; "
                        )
                        raise e
                    mp.util.info(
                        "full call_queue prevented to send all sentinels at "
                        "once, waiting..."
                    )
                    sleep(cooldown_time)
                    cooldown_time *= 1.2
                    break

        mp.util.debug(f"sent {n_sentinels_sent} sentinels to the call queue")

    def join_executor_internals(self):
        self.shutdown_workers()

        # Release the queue's resources as soon as possible. Flag the feeder
        # thread for clean exit to avoid having the crash detection thread flag
        # the Executor as broken during the shutdown. This is safe as either:
        #  * We don't need to communicate with the workers anymore
        #  * There is nothing left in the Queue buffer except None sentinels
        mp.util.debug("closing call_queue")
        self.call_queue.close()
        self.call_queue.join_thread()

        # Closing result_queue
        mp.util.debug("closing result_queue")
        self.result_queue.close()

        mp.util.debug("closing thread_wakeup")
        with self.shutdown_lock:
            self.thread_wakeup.close()

        # If .join() is not called on the created processes then
        # some ctx.Queue methods may deadlock on macOS.
        with self.processes_management_lock:
            mp.util.debug(f"joining {len(self.processes)} processes")
            n_joined_processes = 0
            while True:
                try:
                    pid, p = self.processes.popitem()
                    mp.util.debug(f"joining process {p.name} with pid {pid}")
                    p.join()
                    n_joined_processes += 1
                except KeyError:
                    break

            mp.util.debug(
                "executor management thread clean shutdown of "
                f"{n_joined_processes} workers"
            )

    def get_n_children_alive(self):
        # This is an upper bound on the number of children alive.
        with self.processes_management_lock:
            return sum(p.is_alive() for p in list(self.processes.values()))


_system_limits_checked = False
_system_limited = None


def _check_system_limits():
    global _system_limits_checked, _system_limited
    if _system_limits_checked and _system_limited:
        raise NotImplementedError(_system_limited)
    _system_limits_checked = True
    try:
        nsems_max = os.sysconf("SC_SEM_NSEMS_MAX")
    except (AttributeError, ValueError):
        # sysconf not available or setting not available
        return
    if nsems_max == -1:
        # undetermined limit, assume that limit is determined
        # by available memory only
        return
    if nsems_max >= 256:
        # minimum number of semaphores available
        # according to POSIX
        return
    _system_limited = (
        f"system provides too few semaphores ({nsems_max} available, "
        "256 necessary)"
    )
    raise NotImplementedError(_system_limited)


def _chain_from_iterable_of_lists(iterable):
    """
    Specialized implementation of itertools.chain.from_iterable.
    Each item in *iterable* should be a list.  This function is
    careful not to keep references to yielded objects.
    """
    for element in iterable:
        element.reverse()
        while element:
            yield element.pop()


def _check_max_depth(context):
    # Limit the maxmal recursion level
    global _CURRENT_DEPTH
    if context.get_start_method() == "fork" and _CURRENT_DEPTH > 0:
        raise LokyRecursionError(
            "Could not spawn extra nested processes at depth superior to "
            "MAX_DEPTH=1. It is not possible to increase this limit when "
            "using the 'fork' start method."
        )

    if 0 < MAX_DEPTH and _CURRENT_DEPTH + 1 > MAX_DEPTH:
        raise LokyRecursionError(
            "Could not spawn extra nested processes at depth superior to "
            f"MAX_DEPTH={MAX_DEPTH}. If this is intendend, you can change "
            "this limit with the LOKY_MAX_DEPTH environment variable."
        )


class LokyRecursionError(RuntimeError):
    """A process tries to spawn too many levels of nested processes."""


class BrokenProcessPool(_BPPException):
    """
    Raised when the executor is broken while a future was in the running state.
    The cause can an error raised when unpickling the task in the worker
    process or when unpickling the result value in the parent process. It can
    also be caused by a worker process being terminated unexpectedly.
    """


class TerminatedWorkerError(BrokenProcessPool):
    """
    Raised when a process in a ProcessPoolExecutor terminated abruptly
    while a future was in the running state.
    """


# Alias for backward compat (for code written for loky 1.1.4 and earlier). Do
# not use in new code.
BrokenExecutor = BrokenProcessPool


class ShutdownExecutorError(RuntimeError):
    """
    Raised when a ProcessPoolExecutor is shutdown while a future was in the
    running or pending state.
    """


class ProcessPoolExecutor(Executor):

    _at_exit = None

    def __init__(
        self,
        max_workers=None,
        job_reducers=None,
        result_reducers=None,
        timeout=None,
        context=None,
        initializer=None,
        initargs=(),
        env=None,
    ):
        """Initializes a new ProcessPoolExecutor instance.

        Args:
            max_workers: int, optional (default: cpu_count())
                The maximum number of processes that can be used to execute the
                given calls. If None or not given then as many worker processes
                will be created as the number of CPUs the current process
                can use.
            job_reducers, result_reducers: dict(type: reducer_func)
                Custom reducer for pickling the jobs and the results from the
                Executor. If only `job_reducers` is provided, `result_reducer`
                will use the same reducers
            timeout: int, optional (default: None)
                Idle workers exit after timeout seconds. If a new job is
                submitted after the timeout, the executor will start enough
                new Python processes to make sure the pool of workers is full.
            context: A multiprocessing context to launch the workers. This
                object should provide SimpleQueue, Queue and Process.
            initializer: An callable used to initialize worker processes.
            initargs: A tuple of arguments to pass to the initializer.
            env: A dict of environment variable to overwrite in the child
                process. The environment variables are set before any module is
                loaded. Note that this only works with the loky context.
        """
        _check_system_limits()

        if max_workers is None:
            self._max_workers = cpu_count()
        else:
            if max_workers <= 0:
                raise ValueError("max_workers must be greater than 0")
            self._max_workers = max_workers

        if (
            sys.platform == "win32"
            and self._max_workers > _MAX_WINDOWS_WORKERS
        ):
            warnings.warn(
                f"On Windows, max_workers cannot exceed {_MAX_WINDOWS_WORKERS} "
                "due to limitations of the operating system."
            )
            self._max_workers = _MAX_WINDOWS_WORKERS

        if context is None:
            context = get_context()
        self._context = context
        self._env = env

        self._initializer, self._initargs = _prepare_initializer(
            initializer, initargs
        )
        _check_max_depth(self._context)

        if result_reducers is None:
            result_reducers = job_reducers

        # Timeout
        self._timeout = timeout

        # Management thread
        self._executor_manager_thread = None

        # Map of pids to processes
        self._processes = {}

        # Internal variables of the ProcessPoolExecutor
        self._processes = {}
        self._queue_count = 0
        self._pending_work_items = {}
        self._running_work_items = []
        self._work_ids = queue.Queue()
        self._processes_management_lock = self._context.Lock()
        self._executor_manager_thread = None
        self._shutdown_lock = threading.Lock()

        # _ThreadWakeup is a communication channel used to interrupt the wait
        # of the main loop of executor_manager_thread from another thread (e.g.
        # when calling executor.submit or executor.shutdown). We do not use the
        # _result_queue to send wakeup signals to the executor_manager_thread
        # as it could result in a deadlock if a worker process dies with the
        # _result_queue write lock still acquired.
        #
        # _shutdown_lock must be locked to access _ThreadWakeup.wakeup.
        self._executor_manager_thread_wakeup = _ThreadWakeup()

        # Flag to hold the state of the Executor. This permits to introspect
        # the Executor state even once it has been garbage collected.
        self._flags = _ExecutorFlags(self._shutdown_lock)

        # Finally setup the queues for interprocess communication
        self._setup_queues(job_reducers, result_reducers)

        mp.util.debug("ProcessPoolExecutor is setup")

    def _setup_queues(self, job_reducers, result_reducers, queue_size=None):
        # Make the call queue slightly larger than the number of processes to
        # prevent the worker processes from idling. But don't make it too big
        # because futures in the call queue cannot be cancelled.
        if queue_size is None:
            queue_size = 2 * self._max_workers + EXTRA_QUEUED_CALLS
        self._call_queue = _SafeQueue(
            max_size=queue_size,
            pending_work_items=self._pending_work_items,
            running_work_items=self._running_work_items,
            thread_wakeup=self._executor_manager_thread_wakeup,
            shutdown_lock=self._shutdown_lock,
            reducers=job_reducers,
            ctx=self._context,
        )
        # Killed worker processes can produce spurious "broken pipe"
        # tracebacks in the queue's own worker thread. But we detect killed
        # processes anyway, so silence the tracebacks.
        self._call_queue._ignore_epipe = True

        self._result_queue = SimpleQueue(
            reducers=result_reducers, ctx=self._context
        )

    def _start_executor_manager_thread(self):
        if self._executor_manager_thread is None:
            mp.util.debug("_start_executor_manager_thread called")

            # Start the processes so that their sentinels are known.
            self._executor_manager_thread = _ExecutorManagerThread(self)
            self._executor_manager_thread.start()

            # register this executor in a mechanism that ensures it will wakeup
            # when the interpreter is exiting.
            _threads_wakeups[self._executor_manager_thread] = (
                self._shutdown_lock,
                self._executor_manager_thread_wakeup,
            )

            global process_pool_executor_at_exit
            if process_pool_executor_at_exit is None:
                # Ensure that the _python_exit function will be called before
                # the multiprocessing.Queue._close finalizers which have an
                # exitpriority of 10.

                if sys.version_info < (3, 9):
                    process_pool_executor_at_exit = mp.util.Finalize(
                        None, _python_exit, exitpriority=20
                    )
                else:
                    process_pool_executor_at_exit = threading._register_atexit(
                        _python_exit
                    )

    def _adjust_process_count(self):
        while len(self._processes) < self._max_workers:
            worker_exit_lock = self._context.BoundedSemaphore(1)
            args = (
                self._call_queue,
                self._result_queue,
                self._initializer,
                self._initargs,
                self._processes_management_lock,
                self._timeout,
                worker_exit_lock,
                _CURRENT_DEPTH + 1,
            )
            worker_exit_lock.acquire()
            try:
                # Try to spawn the process with some environment variable to
                # overwrite but it only works with the loky context for now.
                p = self._context.Process(
                    target=_process_worker, args=args, env=self._env
                )
            except TypeError:
                p = self._context.Process(target=_process_worker, args=args)
            p._worker_exit_lock = worker_exit_lock
            p.start()
            self._processes[p.pid] = p
        mp.util.debug(
            f"Adjusted process count to {self._max_workers}: "
            f"{[(p.name, pid) for pid, p in self._processes.items()]}"
        )

    def _ensure_executor_running(self):
        """ensures all workers and management thread are running"""
        with self._processes_management_lock:
            if len(self._processes) != self._max_workers:
                self._adjust_process_count()
            self._start_executor_manager_thread()

    def submit(self, fn, *args, **kwargs):
        with self._flags.shutdown_lock:
            if self._flags.broken is not None:
                raise self._flags.broken
            if self._flags.shutdown:
                raise ShutdownExecutorError(
                    "cannot schedule new futures after shutdown"
                )

            # Cannot submit a new calls once the interpreter is shutting down.
            # This check avoids spawning new processes at exit.
            if _global_shutdown:
                raise RuntimeError(
                    "cannot schedule new futures after interpreter shutdown"
                )

            f = Future()
            w = _WorkItem(f, fn, args, kwargs)

            self._pending_work_items[self._queue_count] = w
            self._work_ids.put(self._queue_count)
            self._queue_count += 1
            # Wake up queue management thread
            self._executor_manager_thread_wakeup.wakeup()

            self._ensure_executor_running()
            return f

    submit.__doc__ = Executor.submit.__doc__

    def map(self, fn, *iterables, **kwargs):
        """Returns an iterator equivalent to map(fn, iter).

        Args:
            fn: A callable that will take as many arguments as there are
                passed iterables.
            timeout: The maximum number of seconds to wait. If None, then there
                is no limit on the wait time.
            chunksize: If greater than one, the iterables will be chopped into
                chunks of size chunksize and submitted to the process pool.
                If set to one, the items in the list will be sent one at a
                time.

        Returns:
            An iterator equivalent to: map(func, *iterables) but the calls may
            be evaluated out-of-order.

        Raises:
            TimeoutError: If the entire result iterator could not be generated
                before the given timeout.
            Exception: If fn(*args) raises for any values.
        """
        timeout = kwargs.get("timeout", None)
        chunksize = kwargs.get("chunksize", 1)
        if chunksize < 1:
            raise ValueError("chunksize must be >= 1.")

        results = super().map(
            partial(_process_chunk, fn),
            _get_chunks(chunksize, *iterables),
            timeout=timeout,
        )
        return _chain_from_iterable_of_lists(results)

    def shutdown(self, wait=True, kill_workers=False):
        mp.util.debug(f"shutting down executor {self}")

        self._flags.flag_as_shutting_down(kill_workers)
        executor_manager_thread = self._executor_manager_thread
        executor_manager_thread_wakeup = self._executor_manager_thread_wakeup

        if executor_manager_thread_wakeup is not None:
            # Wake up queue management thread
            with self._shutdown_lock:
                self._executor_manager_thread_wakeup.wakeup()

        if executor_manager_thread is not None and wait:
            # This locks avoids concurrent join if the interpreter
            # is shutting down.
            with _global_shutdown_lock:
                executor_manager_thread.join()
                _threads_wakeups.pop(executor_manager_thread, None)

        # To reduce the risk of opening too many files, remove references to
        # objects that use file descriptors.
        self._executor_manager_thread = None
        self._executor_manager_thread_wakeup = None
        self._call_queue = None
        self._result_queue = None
        self._processes_management_lock = None

    shutdown.__doc__ = Executor.shutdown.__doc__

# === NexusCore/openenv\Lib\site-packages\PIL\ImageFont.py ===
#
# The Python Imaging Library.
# $Id$
#
# PIL raster font management
#
# History:
# 1996-08-07 fl   created (experimental)
# 1997-08-25 fl   minor adjustments to handle fonts from pilfont 0.3
# 1999-02-06 fl   rewrote most font management stuff in C
# 1999-03-17 fl   take pth files into account in load_path (from Richard Jones)
# 2001-02-17 fl   added freetype support
# 2001-05-09 fl   added TransposedFont wrapper class
# 2002-03-04 fl   make sure we have a "L" or "1" font
# 2002-12-04 fl   skip non-directory entries in the system path
# 2003-04-29 fl   add embedded default font
# 2003-09-27 fl   added support for truetype charmap encodings
#
# Todo:
# Adapt to PILFONT2 format (16-bit fonts, compressed, single file)
#
# Copyright (c) 1997-2003 by Secret Labs AB
# Copyright (c) 1996-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from __future__ import annotations

import base64
import os
import sys
import warnings
from enum import IntEnum
from io import BytesIO
from types import ModuleType
from typing import IO, Any, BinaryIO, TypedDict, cast

from . import Image, features
from ._typing import StrOrBytesPath
from ._util import DeferredError, is_path

TYPE_CHECKING = False
if TYPE_CHECKING:
    from . import ImageFile
    from ._imaging import ImagingFont
    from ._imagingft import Font


class Axis(TypedDict):
    minimum: int | None
    default: int | None
    maximum: int | None
    name: bytes | None


class Layout(IntEnum):
    BASIC = 0
    RAQM = 1


MAX_STRING_LENGTH = 1_000_000


core: ModuleType | DeferredError
try:
    from . import _imagingft as core
except ImportError as ex:
    core = DeferredError.new(ex)


def _string_length_check(text: str | bytes | bytearray) -> None:
    if MAX_STRING_LENGTH is not None and len(text) > MAX_STRING_LENGTH:
        msg = "too many characters in string"
        raise ValueError(msg)


# FIXME: add support for pilfont2 format (see FontFile.py)

# --------------------------------------------------------------------
# Font metrics format:
#       "PILfont" LF
#       fontdescriptor LF
#       (optional) key=value... LF
#       "DATA" LF
#       binary data: 256*10*2 bytes (dx, dy, dstbox, srcbox)
#
# To place a character, cut out srcbox and paste at dstbox,
# relative to the character position.  Then move the character
# position according to dx, dy.
# --------------------------------------------------------------------


class ImageFont:
    """PIL font wrapper"""

    font: ImagingFont

    def _load_pilfont(self, filename: str) -> None:
        with open(filename, "rb") as fp:
            image: ImageFile.ImageFile | None = None
            root = os.path.splitext(filename)[0]

            for ext in (".png", ".gif", ".pbm"):
                if image:
                    image.close()
                try:
                    fullname = root + ext
                    image = Image.open(fullname)
                except Exception:
                    pass
                else:
                    if image and image.mode in ("1", "L"):
                        break
            else:
                if image:
                    image.close()

                msg = f"cannot find glyph data file {root}.{{gif|pbm|png}}"
                raise OSError(msg)

            self.file = fullname

            self._load_pilfont_data(fp, image)
            image.close()

    def _load_pilfont_data(self, file: IO[bytes], image: Image.Image) -> None:
        # read PILfont header
        if file.readline() != b"PILfont\n":
            msg = "Not a PILfont file"
            raise SyntaxError(msg)
        file.readline().split(b";")
        self.info = []  # FIXME: should be a dictionary
        while True:
            s = file.readline()
            if not s or s == b"DATA\n":
                break
            self.info.append(s)

        # read PILfont metrics
        data = file.read(256 * 20)

        # check image
        if image.mode not in ("1", "L"):
            msg = "invalid font image mode"
            raise TypeError(msg)

        image.load()

        self.font = Image.core.font(image.im, data)

    def getmask(
        self, text: str | bytes, mode: str = "", *args: Any, **kwargs: Any
    ) -> Image.core.ImagingCore:
        """
        Create a bitmap for the text.

        If the font uses antialiasing, the bitmap should have mode ``L`` and use a
        maximum value of 255. Otherwise, it should have mode ``1``.

        :param text: Text to render.
        :param mode: Used by some graphics drivers to indicate what mode the
                     driver prefers; if empty, the renderer may return either
                     mode. Note that the mode is always a string, to simplify
                     C-level implementations.

                     .. versionadded:: 1.1.5

        :return: An internal PIL storage memory instance as defined by the
                 :py:mod:`PIL.Image.core` interface module.
        """
        _string_length_check(text)
        Image._decompression_bomb_check(self.font.getsize(text))
        return self.font.getmask(text, mode)

    def getbbox(
        self, text: str | bytes | bytearray, *args: Any, **kwargs: Any
    ) -> tuple[int, int, int, int]:
        """
        Returns bounding box (in pixels) of given text.

        .. versionadded:: 9.2.0

        :param text: Text to render.

        :return: ``(left, top, right, bottom)`` bounding box
        """
        _string_length_check(text)
        width, height = self.font.getsize(text)
        return 0, 0, width, height

    def getlength(
        self, text: str | bytes | bytearray, *args: Any, **kwargs: Any
    ) -> int:
        """
        Returns length (in pixels) of given text.
        This is the amount by which following text should be offset.

        .. versionadded:: 9.2.0
        """
        _string_length_check(text)
        width, height = self.font.getsize(text)
        return width


##
# Wrapper for FreeType fonts.  Application code should use the
# <b>truetype</b> factory function to create font objects.


class FreeTypeFont:
    """FreeType font wrapper (requires _imagingft service)"""

    font: Font
    font_bytes: bytes

    def __init__(
        self,
        font: StrOrBytesPath | BinaryIO,
        size: float = 10,
        index: int = 0,
        encoding: str = "",
        layout_engine: Layout | None = None,
    ) -> None:
        # FIXME: use service provider instead

        if isinstance(core, DeferredError):
            raise core.ex

        if size <= 0:
            msg = f"font size must be greater than 0, not {size}"
            raise ValueError(msg)

        self.path = font
        self.size = size
        self.index = index
        self.encoding = encoding

        try:
            from packaging.version import parse as parse_version
        except ImportError:
            pass
        else:
            if freetype_version := features.version_module("freetype2"):
                if parse_version(freetype_version) < parse_version("2.9.1"):
                    warnings.warn(
                        "Support for FreeType 2.9.0 is deprecated and will be removed "
                        "in Pillow 12 (2025-10-15). Please upgrade to FreeType 2.9.1 "
                        "or newer, preferably FreeType 2.10.4 which fixes "
                        "CVE-2020-15999.",
                        DeprecationWarning,
                    )

        if layout_engine not in (Layout.BASIC, Layout.RAQM):
            layout_engine = Layout.BASIC
            if core.HAVE_RAQM:
                layout_engine = Layout.RAQM
        elif layout_engine == Layout.RAQM and not core.HAVE_RAQM:
            warnings.warn(
                "Raqm layout was requested, but Raqm is not available. "
                "Falling back to basic layout."
            )
            layout_engine = Layout.BASIC

        self.layout_engine = layout_engine

        def load_from_bytes(f: IO[bytes]) -> None:
            self.font_bytes = f.read()
            self.font = core.getfont(
                "", size, index, encoding, self.font_bytes, layout_engine
            )

        if is_path(font):
            font = os.fspath(font)
            if sys.platform == "win32":
                font_bytes_path = font if isinstance(font, bytes) else font.encode()
                try:
                    font_bytes_path.decode("ascii")
                except UnicodeDecodeError:
                    # FreeType cannot load fonts with non-ASCII characters on Windows
                    # So load it into memory first
                    with open(font, "rb") as f:
                        load_from_bytes(f)
                    return
            self.font = core.getfont(
                font, size, index, encoding, layout_engine=layout_engine
            )
        else:
            load_from_bytes(cast(IO[bytes], font))

    def __getstate__(self) -> list[Any]:
        return [self.path, self.size, self.index, self.encoding, self.layout_engine]

    def __setstate__(self, state: list[Any]) -> None:
        path, size, index, encoding, layout_engine = state
        FreeTypeFont.__init__(self, path, size, index, encoding, layout_engine)

    def getname(self) -> tuple[str | None, str | None]:
        """
        :return: A tuple of the font family (e.g. Helvetica) and the font style
            (e.g. Bold)
        """
        return self.font.family, self.font.style

    def getmetrics(self) -> tuple[int, int]:
        """
        :return: A tuple of the font ascent (the distance from the baseline to
            the highest outline point) and descent (the distance from the
            baseline to the lowest outline point, a negative value)
        """
        return self.font.ascent, self.font.descent

    def getlength(
        self,
        text: str | bytes,
        mode: str = "",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
    ) -> float:
        """
        Returns length (in pixels with 1/64 precision) of given text when rendered
        in font with provided direction, features, and language.

        This is the amount by which following text should be offset.
        Text bounding box may extend past the length in some fonts,
        e.g. when using italics or accents.

        The result is returned as a float; it is a whole number if using basic layout.

        Note that the sum of two lengths may not equal the length of a concatenated
        string due to kerning. If you need to adjust for kerning, include the following
        character and subtract its length.

        For example, instead of ::

          hello = font.getlength("Hello")
          world = font.getlength("World")
          hello_world = hello + world  # not adjusted for kerning
          assert hello_world == font.getlength("HelloWorld")  # may fail

        use ::

          hello = font.getlength("HelloW") - font.getlength("W")  # adjusted for kerning
          world = font.getlength("World")
          hello_world = hello + world  # adjusted for kerning
          assert hello_world == font.getlength("HelloWorld")  # True

        or disable kerning with (requires libraqm) ::

          hello = draw.textlength("Hello", font, features=["-kern"])
          world = draw.textlength("World", font, features=["-kern"])
          hello_world = hello + world  # kerning is disabled, no need to adjust
          assert hello_world == draw.textlength("HelloWorld", font, features=["-kern"])

        .. versionadded:: 8.0.0

        :param text: Text to measure.
        :param mode: Used by some graphics drivers to indicate what mode the
                     driver prefers; if empty, the renderer may return either
                     mode. Note that the mode is always a string, to simplify
                     C-level implementations.

        :param direction: Direction of the text. It can be 'rtl' (right to
                          left), 'ltr' (left to right) or 'ttb' (top to bottom).
                          Requires libraqm.

        :param features: A list of OpenType font features to be used during text
                         layout. This is usually used to turn on optional
                         font features that are not enabled by default,
                         for example 'dlig' or 'ss01', but can be also
                         used to turn off default font features for
                         example '-liga' to disable ligatures or '-kern'
                         to disable kerning.  To get all supported
                         features, see
                         https://learn.microsoft.com/en-us/typography/opentype/spec/featurelist
                         Requires libraqm.

        :param language: Language of the text. Different languages may use
                         different glyph shapes or ligatures. This parameter tells
                         the font which language the text is in, and to apply the
                         correct substitutions as appropriate, if available.
                         It should be a `BCP 47 language code
                         <https://www.w3.org/International/articles/language-tags/>`_
                         Requires libraqm.

        :return: Either width for horizontal text, or height for vertical text.
        """
        _string_length_check(text)
        return self.font.getlength(text, mode, direction, features, language) / 64

    def getbbox(
        self,
        text: str | bytes,
        mode: str = "",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        anchor: str | None = None,
    ) -> tuple[float, float, float, float]:
        """
        Returns bounding box (in pixels) of given text relative to given anchor
        when rendered in font with provided direction, features, and language.

        Use :py:meth:`getlength()` to get the offset of following text with
        1/64 pixel precision. The bounding box includes extra margins for
        some fonts, e.g. italics or accents.

        .. versionadded:: 8.0.0

        :param text: Text to render.
        :param mode: Used by some graphics drivers to indicate what mode the
                     driver prefers; if empty, the renderer may return either
                     mode. Note that the mode is always a string, to simplify
                     C-level implementations.

        :param direction: Direction of the text. It can be 'rtl' (right to
                          left), 'ltr' (left to right) or 'ttb' (top to bottom).
                          Requires libraqm.

        :param features: A list of OpenType font features to be used during text
                         layout. This is usually used to turn on optional
                         font features that are not enabled by default,
                         for example 'dlig' or 'ss01', but can be also
                         used to turn off default font features for
                         example '-liga' to disable ligatures or '-kern'
                         to disable kerning.  To get all supported
                         features, see
                         https://learn.microsoft.com/en-us/typography/opentype/spec/featurelist
                         Requires libraqm.

        :param language: Language of the text. Different languages may use
                         different glyph shapes or ligatures. This parameter tells
                         the font which language the text is in, and to apply the
                         correct substitutions as appropriate, if available.
                         It should be a `BCP 47 language code
                         <https://www.w3.org/International/articles/language-tags/>`_
                         Requires libraqm.

        :param stroke_width: The width of the text stroke.

        :param anchor:  The text anchor alignment. Determines the relative location of
                        the anchor to the text. The default alignment is top left,
                        specifically ``la`` for horizontal text and ``lt`` for
                        vertical text. See :ref:`text-anchors` for details.

        :return: ``(left, top, right, bottom)`` bounding box
        """
        _string_length_check(text)
        size, offset = self.font.getsize(
            text, mode, direction, features, language, anchor
        )
        left, top = offset[0] - stroke_width, offset[1] - stroke_width
        width, height = size[0] + 2 * stroke_width, size[1] + 2 * stroke_width
        return left, top, left + width, top + height

    def getmask(
        self,
        text: str | bytes,
        mode: str = "",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        anchor: str | None = None,
        ink: int = 0,
        start: tuple[float, float] | None = None,
    ) -> Image.core.ImagingCore:
        """
        Create a bitmap for the text.

        If the font uses antialiasing, the bitmap should have mode ``L`` and use a
        maximum value of 255. If the font has embedded color data, the bitmap
        should have mode ``RGBA``. Otherwise, it should have mode ``1``.

        :param text: Text to render.
        :param mode: Used by some graphics drivers to indicate what mode the
                     driver prefers; if empty, the renderer may return either
                     mode. Note that the mode is always a string, to simplify
                     C-level implementations.

                     .. versionadded:: 1.1.5

        :param direction: Direction of the text. It can be 'rtl' (right to
                          left), 'ltr' (left to right) or 'ttb' (top to bottom).
                          Requires libraqm.

                          .. versionadded:: 4.2.0

        :param features: A list of OpenType font features to be used during text
                         layout. This is usually used to turn on optional
                         font features that are not enabled by default,
                         for example 'dlig' or 'ss01', but can be also
                         used to turn off default font features for
                         example '-liga' to disable ligatures or '-kern'
                         to disable kerning.  To get all supported
                         features, see
                         https://learn.microsoft.com/en-us/typography/opentype/spec/featurelist
                         Requires libraqm.

                         .. versionadded:: 4.2.0

        :param language: Language of the text. Different languages may use
                         different glyph shapes or ligatures. This parameter tells
                         the font which language the text is in, and to apply the
                         correct substitutions as appropriate, if available.
                         It should be a `BCP 47 language code
                         <https://www.w3.org/International/articles/language-tags/>`_
                         Requires libraqm.

                         .. versionadded:: 6.0.0

        :param stroke_width: The width of the text stroke.

                         .. versionadded:: 6.2.0

        :param anchor:  The text anchor alignment. Determines the relative location of
                        the anchor to the text. The default alignment is top left,
                        specifically ``la`` for horizontal text and ``lt`` for
                        vertical text. See :ref:`text-anchors` for details.

                         .. versionadded:: 8.0.0

        :param ink: Foreground ink for rendering in RGBA mode.

                         .. versionadded:: 8.0.0

        :param start: Tuple of horizontal and vertical offset, as text may render
                      differently when starting at fractional coordinates.

                         .. versionadded:: 9.4.0

        :return: An internal PIL storage memory instance as defined by the
                 :py:mod:`PIL.Image.core` interface module.
        """
        return self.getmask2(
            text,
            mode,
            direction=direction,
            features=features,
            language=language,
            stroke_width=stroke_width,
            anchor=anchor,
            ink=ink,
            start=start,
        )[0]

    def getmask2(
        self,
        text: str | bytes,
        mode: str = "",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        anchor: str | None = None,
        ink: int = 0,
        start: tuple[float, float] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[Image.core.ImagingCore, tuple[int, int]]:
        """
        Create a bitmap for the text.

        If the font uses antialiasing, the bitmap should have mode ``L`` and use a
        maximum value of 255. If the font has embedded color data, the bitmap
        should have mode ``RGBA``. Otherwise, it should have mode ``1``.

        :param text: Text to render.
        :param mode: Used by some graphics drivers to indicate what mode the
                     driver prefers; if empty, the renderer may return either
                     mode. Note that the mode is always a string, to simplify
                     C-level implementations.

                     .. versionadded:: 1.1.5

        :param direction: Direction of the text. It can be 'rtl' (right to
                          left), 'ltr' (left to right) or 'ttb' (top to bottom).
                          Requires libraqm.

                          .. versionadded:: 4.2.0

        :param features: A list of OpenType font features to be used during text
                         layout. This is usually used to turn on optional
                         font features that are not enabled by default,
                         for example 'dlig' or 'ss01', but can be also
                         used to turn off default font features for
                         example '-liga' to disable ligatures or '-kern'
                         to disable kerning.  To get all supported
                         features, see
                         https://learn.microsoft.com/en-us/typography/opentype/spec/featurelist
                         Requires libraqm.

                         .. versionadded:: 4.2.0

        :param language: Language of the text. Different languages may use
                         different glyph shapes or ligatures. This parameter tells
                         the font which language the text is in, and to apply the
                         correct substitutions as appropriate, if available.
                         It should be a `BCP 47 language code
                         <https://www.w3.org/International/articles/language-tags/>`_
                         Requires libraqm.

                         .. versionadded:: 6.0.0

        :param stroke_width: The width of the text stroke.

                         .. versionadded:: 6.2.0

        :param anchor:  The text anchor alignment. Determines the relative location of
                        the anchor to the text. The default alignment is top left,
                        specifically ``la`` for horizontal text and ``lt`` for
                        vertical text. See :ref:`text-anchors` for details.

                         .. versionadded:: 8.0.0

        :param ink: Foreground ink for rendering in RGBA mode.

                         .. versionadded:: 8.0.0

        :param start: Tuple of horizontal and vertical offset, as text may render
                      differently when starting at fractional coordinates.

                         .. versionadded:: 9.4.0

        :return: A tuple of an internal PIL storage memory instance as defined by the
                 :py:mod:`PIL.Image.core` interface module, and the text offset, the
                 gap between the starting coordinate and the first marking
        """
        _string_length_check(text)
        if start is None:
            start = (0, 0)

        def fill(width: int, height: int) -> Image.core.ImagingCore:
            size = (width, height)
            Image._decompression_bomb_check(size)
            return Image.core.fill("RGBA" if mode == "RGBA" else "L", size)

        return self.font.render(
            text,
            fill,
            mode,
            direction,
            features,
            language,
            stroke_width,
            kwargs.get("stroke_filled", False),
            anchor,
            ink,
            start,
        )

    def font_variant(
        self,
        font: StrOrBytesPath | BinaryIO | None = None,
        size: float | None = None,
        index: int | None = None,
        encoding: str | None = None,
        layout_engine: Layout | None = None,
    ) -> FreeTypeFont:
        """
        Create a copy of this FreeTypeFont object,
        using any specified arguments to override the settings.

        Parameters are identical to the parameters used to initialize this
        object.

        :return: A FreeTypeFont object.
        """
        if font is None:
            try:
                font = BytesIO(self.font_bytes)
            except AttributeError:
                font = self.path
        return FreeTypeFont(
            font=font,
            size=self.size if size is None else size,
            index=self.index if index is None else index,
            encoding=self.encoding if encoding is None else encoding,
            layout_engine=layout_engine or self.layout_engine,
        )

    def get_variation_names(self) -> list[bytes]:
        """
        :returns: A list of the named styles in a variation font.
        :exception OSError: If the font is not a variation font.
        """
        try:
            names = self.font.getvarnames()
        except AttributeError as e:
            msg = "FreeType 2.9.1 or greater is required"
            raise NotImplementedError(msg) from e
        return [name.replace(b"\x00", b"") for name in names]

    def set_variation_by_name(self, name: str | bytes) -> None:
        """
        :param name: The name of the style.
        :exception OSError: If the font is not a variation font.
        """
        names = self.get_variation_names()
        if not isinstance(name, bytes):
            name = name.encode()
        index = names.index(name) + 1

        if index == getattr(self, "_last_variation_index", None):
            # When the same name is set twice in a row,
            # there is an 'unknown freetype error'
            # https://savannah.nongnu.org/bugs/?56186
            return
        self._last_variation_index = index

        self.font.setvarname(index)

    def get_variation_axes(self) -> list[Axis]:
        """
        :returns: A list of the axes in a variation font.
        :exception OSError: If the font is not a variation font.
        """
        try:
            axes = self.font.getvaraxes()
        except AttributeError as e:
            msg = "FreeType 2.9.1 or greater is required"
            raise NotImplementedError(msg) from e
        for axis in axes:
            if axis["name"]:
                axis["name"] = axis["name"].replace(b"\x00", b"")
        return axes

    def set_variation_by_axes(self, axes: list[float]) -> None:
        """
        :param axes: A list of values for each axis.
        :exception OSError: If the font is not a variation font.
        """
        try:
            self.font.setvaraxes(axes)
        except AttributeError as e:
            msg = "FreeType 2.9.1 or greater is required"
            raise NotImplementedError(msg) from e


class TransposedFont:
    """Wrapper for writing rotated or mirrored text"""

    def __init__(
        self, font: ImageFont | FreeTypeFont, orientation: Image.Transpose | None = None
    ):
        """
        Wrapper that creates a transposed font from any existing font
        object.

        :param font: A font object.
        :param orientation: An optional orientation.  If given, this should
            be one of Image.Transpose.FLIP_LEFT_RIGHT, Image.Transpose.FLIP_TOP_BOTTOM,
            Image.Transpose.ROTATE_90, Image.Transpose.ROTATE_180, or
            Image.Transpose.ROTATE_270.
        """
        self.font = font
        self.orientation = orientation  # any 'transpose' argument, or None

    def getmask(
        self, text: str | bytes, mode: str = "", *args: Any, **kwargs: Any
    ) -> Image.core.ImagingCore:
        im = self.font.getmask(text, mode, *args, **kwargs)
        if self.orientation is not None:
            return im.transpose(self.orientation)
        return im

    def getbbox(
        self, text: str | bytes, *args: Any, **kwargs: Any
    ) -> tuple[int, int, float, float]:
        # TransposedFont doesn't support getmask2, move top-left point to (0, 0)
        # this has no effect on ImageFont and simulates anchor="lt" for FreeTypeFont
        left, top, right, bottom = self.font.getbbox(text, *args, **kwargs)
        width = right - left
        height = bottom - top
        if self.orientation in (Image.Transpose.ROTATE_90, Image.Transpose.ROTATE_270):
            return 0, 0, height, width
        return 0, 0, width, height

    def getlength(self, text: str | bytes, *args: Any, **kwargs: Any) -> float:
        if self.orientation in (Image.Transpose.ROTATE_90, Image.Transpose.ROTATE_270):
            msg = "text length is undefined for text rotated by 90 or 270 degrees"
            raise ValueError(msg)
        return self.font.getlength(text, *args, **kwargs)


def load(filename: str) -> ImageFont:
    """
    Load a font file. This function loads a font object from the given
    bitmap font file, and returns the corresponding font object. For loading TrueType
    or OpenType fonts instead, see :py:func:`~PIL.ImageFont.truetype`.

    :param filename: Name of font file.
    :return: A font object.
    :exception OSError: If the file could not be read.
    """
    f = ImageFont()
    f._load_pilfont(filename)
    return f


def truetype(
    font: StrOrBytesPath | BinaryIO,
    size: float = 10,
    index: int = 0,
    encoding: str = "",
    layout_engine: Layout | None = None,
) -> FreeTypeFont:
    """
    Load a TrueType or OpenType font from a file or file-like object,
    and create a font object. This function loads a font object from the given
    file or file-like object, and creates a font object for a font of the given
    size. For loading bitmap fonts instead, see :py:func:`~PIL.ImageFont.load`
    and :py:func:`~PIL.ImageFont.load_path`.

    Pillow uses FreeType to open font files. On Windows, be aware that FreeType
    will keep the file open as long as the FreeTypeFont object exists. Windows
    limits the number of files that can be open in C at once to 512, so if many
    fonts are opened simultaneously and that limit is approached, an
    ``OSError`` may be thrown, reporting that FreeType "cannot open resource".
    A workaround would be to copy the file(s) into memory, and open that instead.

    This function requires the _imagingft service.

    :param font: A filename or file-like object containing a TrueType font.
                 If the file is not found in this filename, the loader may also
                 search in other directories, such as:

                 * The :file:`fonts/` directory on Windows,
                 * :file:`/Library/Fonts/`, :file:`/System/Library/Fonts/`
                   and :file:`~/Library/Fonts/` on macOS.
                 * :file:`~/.local/share/fonts`, :file:`/usr/local/share/fonts`,
                   and :file:`/usr/share/fonts` on Linux; or those specified by
                   the ``XDG_DATA_HOME`` and ``XDG_DATA_DIRS`` environment variables
                   for user-installed and system-wide fonts, respectively.

    :param size: The requested size, in pixels.
    :param index: Which font face to load (default is first available face).
    :param encoding: Which font encoding to use (default is Unicode). Possible
                     encodings include (see the FreeType documentation for more
                     information):

                     * "unic" (Unicode)
                     * "symb" (Microsoft Symbol)
                     * "ADOB" (Adobe Standard)
                     * "ADBE" (Adobe Expert)
                     * "ADBC" (Adobe Custom)
                     * "armn" (Apple Roman)
                     * "sjis" (Shift JIS)
                     * "gb  " (PRC)
                     * "big5"
                     * "wans" (Extended Wansung)
                     * "joha" (Johab)
                     * "lat1" (Latin-1)

                     This specifies the character set to use. It does not alter the
                     encoding of any text provided in subsequent operations.
    :param layout_engine: Which layout engine to use, if available:
                     :attr:`.ImageFont.Layout.BASIC` or :attr:`.ImageFont.Layout.RAQM`.
                     If it is available, Raqm layout will be used by default.
                     Otherwise, basic layout will be used.

                     Raqm layout is recommended for all non-English text. If Raqm layout
                     is not required, basic layout will have better performance.

                     You can check support for Raqm layout using
                     :py:func:`PIL.features.check_feature` with ``feature="raqm"``.

                     .. versionadded:: 4.2.0
    :return: A font object.
    :exception OSError: If the file could not be read.
    :exception ValueError: If the font size is not greater than zero.
    """

    def freetype(font: StrOrBytesPath | BinaryIO) -> FreeTypeFont:
        return FreeTypeFont(font, size, index, encoding, layout_engine)

    try:
        return freetype(font)
    except OSError:
        if not is_path(font):
            raise
        ttf_filename = os.path.basename(font)

        dirs = []
        if sys.platform == "win32":
            # check the windows font repository
            # NOTE: must use uppercase WINDIR, to work around bugs in
            # 1.5.2's os.environ.get()
            windir = os.environ.get("WINDIR")
            if windir:
                dirs.append(os.path.join(windir, "fonts"))
        elif sys.platform in ("linux", "linux2"):
            data_home = os.environ.get("XDG_DATA_HOME")
            if not data_home:
                # The freedesktop spec defines the following default directory for
                # when XDG_DATA_HOME is unset or empty. This user-level directory
                # takes precedence over system-level directories.
                data_home = os.path.expanduser("~/.local/share")
            xdg_dirs = [data_home]

            data_dirs = os.environ.get("XDG_DATA_DIRS")
            if not data_dirs:
                # Similarly, defaults are defined for the system-level directories
                data_dirs = "/usr/local/share:/usr/share"
            xdg_dirs += data_dirs.split(":")

            dirs += [os.path.join(xdg_dir, "fonts") for xdg_dir in xdg_dirs]
        elif sys.platform == "darwin":
            dirs += [
                "/Library/Fonts",
                "/System/Library/Fonts",
                os.path.expanduser("~/Library/Fonts"),
            ]

        ext = os.path.splitext(ttf_filename)[1]
        first_font_with_a_different_extension = None
        for directory in dirs:
            for walkroot, walkdir, walkfilenames in os.walk(directory):
                for walkfilename in walkfilenames:
                    if ext and walkfilename == ttf_filename:
                        return freetype(os.path.join(walkroot, walkfilename))
                    elif not ext and os.path.splitext(walkfilename)[0] == ttf_filename:
                        fontpath = os.path.join(walkroot, walkfilename)
                        if os.path.splitext(fontpath)[1] == ".ttf":
                            return freetype(fontpath)
                        if not ext and first_font_with_a_different_extension is None:
                            first_font_with_a_different_extension = fontpath
        if first_font_with_a_different_extension:
            return freetype(first_font_with_a_different_extension)
        raise


def load_path(filename: str | bytes) -> ImageFont:
    """
    Load font file. Same as :py:func:`~PIL.ImageFont.load`, but searches for a
    bitmap font along the Python path.

    :param filename: Name of font file.
    :return: A font object.
    :exception OSError: If the file could not be read.
    """
    if not isinstance(filename, str):
        filename = filename.decode("utf-8")
    for directory in sys.path:
        try:
            return load(os.path.join(directory, filename))
        except OSError:
            pass
    msg = f'cannot find font file "{filename}" in sys.path'
    if os.path.exists(filename):
        msg += f', did you mean ImageFont.load("{filename}") instead?'

    raise OSError(msg)


def load_default_imagefont() -> ImageFont:
    f = ImageFont()
    f._load_pilfont_data(
        # courB08
        BytesIO(
            base64.b64decode(
                b"""
UElMZm9udAo7Ozs7OzsxMDsKREFUQQoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAYAAAAA//8AAQAAAAAAAAABAAEA
BgAAAAH/+gADAAAAAQAAAAMABgAGAAAAAf/6AAT//QADAAAABgADAAYAAAAA//kABQABAAYAAAAL
AAgABgAAAAD/+AAFAAEACwAAABAACQAGAAAAAP/5AAUAAAAQAAAAFQAHAAYAAP////oABQAAABUA
AAAbAAYABgAAAAH/+QAE//wAGwAAAB4AAwAGAAAAAf/5AAQAAQAeAAAAIQAIAAYAAAAB//kABAAB
ACEAAAAkAAgABgAAAAD/+QAE//0AJAAAACgABAAGAAAAAP/6AAX//wAoAAAALQAFAAYAAAAB//8A
BAACAC0AAAAwAAMABgAAAAD//AAF//0AMAAAADUAAQAGAAAAAf//AAMAAAA1AAAANwABAAYAAAAB
//kABQABADcAAAA7AAgABgAAAAD/+QAFAAAAOwAAAEAABwAGAAAAAP/5AAYAAABAAAAARgAHAAYA
AAAA//kABQAAAEYAAABLAAcABgAAAAD/+QAFAAAASwAAAFAABwAGAAAAAP/5AAYAAABQAAAAVgAH
AAYAAAAA//kABQAAAFYAAABbAAcABgAAAAD/+QAFAAAAWwAAAGAABwAGAAAAAP/5AAUAAABgAAAA
ZQAHAAYAAAAA//kABQAAAGUAAABqAAcABgAAAAD/+QAFAAAAagAAAG8ABwAGAAAAAf/8AAMAAABv
AAAAcQAEAAYAAAAA//wAAwACAHEAAAB0AAYABgAAAAD/+gAE//8AdAAAAHgABQAGAAAAAP/7AAT/
/gB4AAAAfAADAAYAAAAB//oABf//AHwAAACAAAUABgAAAAD/+gAFAAAAgAAAAIUABgAGAAAAAP/5
AAYAAQCFAAAAiwAIAAYAAP////oABgAAAIsAAACSAAYABgAA////+gAFAAAAkgAAAJgABgAGAAAA
AP/6AAUAAACYAAAAnQAGAAYAAP////oABQAAAJ0AAACjAAYABgAA////+gAFAAAAowAAAKkABgAG
AAD////6AAUAAACpAAAArwAGAAYAAAAA//oABQAAAK8AAAC0AAYABgAA////+gAGAAAAtAAAALsA
BgAGAAAAAP/6AAQAAAC7AAAAvwAGAAYAAP////oABQAAAL8AAADFAAYABgAA////+gAGAAAAxQAA
AMwABgAGAAD////6AAUAAADMAAAA0gAGAAYAAP////oABQAAANIAAADYAAYABgAA////+gAGAAAA
2AAAAN8ABgAGAAAAAP/6AAUAAADfAAAA5AAGAAYAAP////oABQAAAOQAAADqAAYABgAAAAD/+gAF
AAEA6gAAAO8ABwAGAAD////6AAYAAADvAAAA9gAGAAYAAAAA//oABQAAAPYAAAD7AAYABgAA////
+gAFAAAA+wAAAQEABgAGAAD////6AAYAAAEBAAABCAAGAAYAAP////oABgAAAQgAAAEPAAYABgAA
////+gAGAAABDwAAARYABgAGAAAAAP/6AAYAAAEWAAABHAAGAAYAAP////oABgAAARwAAAEjAAYA
BgAAAAD/+gAFAAABIwAAASgABgAGAAAAAf/5AAQAAQEoAAABKwAIAAYAAAAA//kABAABASsAAAEv
AAgABgAAAAH/+QAEAAEBLwAAATIACAAGAAAAAP/5AAX//AEyAAABNwADAAYAAAAAAAEABgACATcA
AAE9AAEABgAAAAH/+QAE//wBPQAAAUAAAwAGAAAAAP/7AAYAAAFAAAABRgAFAAYAAP////kABQAA
AUYAAAFMAAcABgAAAAD/+wAFAAABTAAAAVEABQAGAAAAAP/5AAYAAAFRAAABVwAHAAYAAAAA//sA
BQAAAVcAAAFcAAUABgAAAAD/+QAFAAABXAAAAWEABwAGAAAAAP/7AAYAAgFhAAABZwAHAAYAAP//
//kABQAAAWcAAAFtAAcABgAAAAD/+QAGAAABbQAAAXMABwAGAAAAAP/5AAQAAgFzAAABdwAJAAYA
AP////kABgAAAXcAAAF+AAcABgAAAAD/+QAGAAABfgAAAYQABwAGAAD////7AAUAAAGEAAABigAF
AAYAAP////sABQAAAYoAAAGQAAUABgAAAAD/+wAFAAABkAAAAZUABQAGAAD////7AAUAAgGVAAAB
mwAHAAYAAAAA//sABgACAZsAAAGhAAcABgAAAAD/+wAGAAABoQAAAacABQAGAAAAAP/7AAYAAAGn
AAABrQAFAAYAAAAA//kABgAAAa0AAAGzAAcABgAA////+wAGAAABswAAAboABQAGAAD////7AAUA
AAG6AAABwAAFAAYAAP////sABgAAAcAAAAHHAAUABgAAAAD/+wAGAAABxwAAAc0ABQAGAAD////7
AAYAAgHNAAAB1AAHAAYAAAAA//sABQAAAdQAAAHZAAUABgAAAAH/+QAFAAEB2QAAAd0ACAAGAAAA
Av/6AAMAAQHdAAAB3gAHAAYAAAAA//kABAABAd4AAAHiAAgABgAAAAD/+wAF//0B4gAAAecAAgAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAYAAAAB
//sAAwACAecAAAHpAAcABgAAAAD/+QAFAAEB6QAAAe4ACAAGAAAAAP/5AAYAAAHuAAAB9AAHAAYA
AAAA//oABf//AfQAAAH5AAUABgAAAAD/+QAGAAAB+QAAAf8ABwAGAAAAAv/5AAMAAgH/AAACAAAJ
AAYAAAAA//kABQABAgAAAAIFAAgABgAAAAH/+gAE//sCBQAAAggAAQAGAAAAAP/5AAYAAAIIAAAC
DgAHAAYAAAAB//kABf/+Ag4AAAISAAUABgAA////+wAGAAACEgAAAhkABQAGAAAAAP/7AAX//gIZ
AAACHgADAAYAAAAA//wABf/9Ah4AAAIjAAEABgAAAAD/+QAHAAACIwAAAioABwAGAAAAAP/6AAT/
+wIqAAACLgABAAYAAAAA//kABP/8Ai4AAAIyAAMABgAAAAD/+gAFAAACMgAAAjcABgAGAAAAAf/5
AAT//QI3AAACOgAEAAYAAAAB//kABP/9AjoAAAI9AAQABgAAAAL/+QAE//sCPQAAAj8AAgAGAAD/
///7AAYAAgI/AAACRgAHAAYAAAAA//kABgABAkYAAAJMAAgABgAAAAH//AAD//0CTAAAAk4AAQAG
AAAAAf//AAQAAgJOAAACUQADAAYAAAAB//kABP/9AlEAAAJUAAQABgAAAAH/+QAF//4CVAAAAlgA
BQAGAAD////7AAYAAAJYAAACXwAFAAYAAP////kABgAAAl8AAAJmAAcABgAA////+QAGAAACZgAA
Am0ABwAGAAD////5AAYAAAJtAAACdAAHAAYAAAAA//sABQACAnQAAAJ5AAcABgAA////9wAGAAAC
eQAAAoAACQAGAAD////3AAYAAAKAAAAChwAJAAYAAP////cABgAAAocAAAKOAAkABgAA////9wAG
AAACjgAAApUACQAGAAD////4AAYAAAKVAAACnAAIAAYAAP////cABgAAApwAAAKjAAkABgAA////
+gAGAAACowAAAqoABgAGAAAAAP/6AAUAAgKqAAACrwAIAAYAAP////cABQAAAq8AAAK1AAkABgAA
////9wAFAAACtQAAArsACQAGAAD////3AAUAAAK7AAACwQAJAAYAAP////gABQAAAsEAAALHAAgA
BgAAAAD/9wAEAAACxwAAAssACQAGAAAAAP/3AAQAAALLAAACzwAJAAYAAAAA//cABAAAAs8AAALT
AAkABgAAAAD/+AAEAAAC0wAAAtcACAAGAAD////6AAUAAALXAAAC3QAGAAYAAP////cABgAAAt0A
AALkAAkABgAAAAD/9wAFAAAC5AAAAukACQAGAAAAAP/3AAUAAALpAAAC7gAJAAYAAAAA//cABQAA
Au4AAALzAAkABgAAAAD/9wAFAAAC8wAAAvgACQAGAAAAAP/4AAUAAAL4AAAC/QAIAAYAAAAA//oA
Bf//Av0AAAMCAAUABgAA////+gAGAAADAgAAAwkABgAGAAD////3AAYAAAMJAAADEAAJAAYAAP//
//cABgAAAxAAAAMXAAkABgAA////9wAGAAADFwAAAx4ACQAGAAD////4AAYAAAAAAAoABwASAAYA
AP////cABgAAAAcACgAOABMABgAA////+gAFAAAADgAKABQAEAAGAAD////6AAYAAAAUAAoAGwAQ
AAYAAAAA//gABgAAABsACgAhABIABgAAAAD/+AAGAAAAIQAKACcAEgAGAAAAAP/4AAYAAAAnAAoA
LQASAAYAAAAA//gABgAAAC0ACgAzABIABgAAAAD/+QAGAAAAMwAKADkAEQAGAAAAAP/3AAYAAAA5
AAoAPwATAAYAAP////sABQAAAD8ACgBFAA8ABgAAAAD/+wAFAAIARQAKAEoAEQAGAAAAAP/4AAUA
AABKAAoATwASAAYAAAAA//gABQAAAE8ACgBUABIABgAAAAD/+AAFAAAAVAAKAFkAEgAGAAAAAP/5
AAUAAABZAAoAXgARAAYAAAAA//gABgAAAF4ACgBkABIABgAAAAD/+AAGAAAAZAAKAGoAEgAGAAAA
AP/4AAYAAABqAAoAcAASAAYAAAAA//kABgAAAHAACgB2ABEABgAAAAD/+AAFAAAAdgAKAHsAEgAG
AAD////4AAYAAAB7AAoAggASAAYAAAAA//gABQAAAIIACgCHABIABgAAAAD/+AAFAAAAhwAKAIwA
EgAGAAAAAP/4AAUAAACMAAoAkQASAAYAAAAA//gABQAAAJEACgCWABIABgAAAAD/+QAFAAAAlgAK
AJsAEQAGAAAAAP/6AAX//wCbAAoAoAAPAAYAAAAA//oABQABAKAACgClABEABgAA////+AAGAAAA
pQAKAKwAEgAGAAD////4AAYAAACsAAoAswASAAYAAP////gABgAAALMACgC6ABIABgAA////+QAG
AAAAugAKAMEAEQAGAAD////4AAYAAgDBAAoAyAAUAAYAAP////kABQACAMgACgDOABMABgAA////
+QAGAAIAzgAKANUAEw==
"""
            )
        ),
        Image.open(
            BytesIO(
                base64.b64decode(
                    b"""
iVBORw0KGgoAAAANSUhEUgAAAx4AAAAUAQAAAAArMtZoAAAEwElEQVR4nABlAJr/AHVE4czCI/4u
Mc4b7vuds/xzjz5/3/7u/n9vMe7vnfH/9++vPn/xyf5zhxzjt8GHw8+2d83u8x27199/nxuQ6Od9
M43/5z2I+9n9ZtmDBwMQECDRQw/eQIQohJXxpBCNVE6QCCAAAAD//wBlAJr/AgALyj1t/wINwq0g
LeNZUworuN1cjTPIzrTX6ofHWeo3v336qPzfEwRmBnHTtf95/fglZK5N0PDgfRTslpGBvz7LFc4F
IUXBWQGjQ5MGCx34EDFPwXiY4YbYxavpnhHFrk14CDAAAAD//wBlAJr/AgKqRooH2gAgPeggvUAA
Bu2WfgPoAwzRAABAAAAAAACQgLz/3Uv4Gv+gX7BJgDeeGP6AAAD1NMDzKHD7ANWr3loYbxsAD791
NAADfcoIDyP44K/jv4Y63/Z+t98Ovt+ub4T48LAAAAD//wBlAJr/AuplMlADJAAAAGuAphWpqhMx
in0A/fRvAYBABPgBwBUgABBQ/sYAyv9g0bCHgOLoGAAAAAAAREAAwI7nr0ArYpow7aX8//9LaP/9
SjdavWA8ePHeBIKB//81/83ndznOaXx379wAAAD//wBlAJr/AqDxW+D3AABAAbUh/QMnbQag/gAY
AYDAAACgtgD/gOqAAAB5IA/8AAAk+n9w0AAA8AAAmFRJuPo27ciC0cD5oeW4E7KA/wD3ECMAn2tt
y8PgwH8AfAxFzC0JzeAMtratAsC/ffwAAAD//wBlAJr/BGKAyCAA4AAAAvgeYTAwHd1kmQF5chkG
ABoMIHcL5xVpTfQbUqzlAAAErwAQBgAAEOClA5D9il08AEh/tUzdCBsXkbgACED+woQg8Si9VeqY
lODCn7lmF6NhnAEYgAAA/NMIAAAAAAD//2JgjLZgVGBg5Pv/Tvpc8hwGBjYGJADjHDrAwPzAjv/H
/Wf3PzCwtzcwHmBgYGcwbZz8wHaCAQMDOwMDQ8MCBgYOC3W7mp+f0w+wHOYxO3OG+e376hsMZjk3
AAAAAP//YmCMY2A4wMAIN5e5gQETPD6AZisDAwMDgzSDAAPjByiHcQMDAwMDg1nOze1lByRu5/47
c4859311AYNZzg0AAAAA//9iYGDBYihOIIMuwIjGL39/fwffA8b//xv/P2BPtzzHwCBjUQAAAAD/
/yLFBrIBAAAA//9i1HhcwdhizX7u8NZNzyLbvT97bfrMf/QHI8evOwcSqGUJAAAA//9iYBB81iSw
pEE170Qrg5MIYydHqwdDQRMrAwcVrQAAAAD//2J4x7j9AAMDn8Q/BgYLBoaiAwwMjPdvMDBYM1Tv
oJodAAAAAP//Yqo/83+dxePWlxl3npsel9lvLfPcqlE9725C+acfVLMEAAAA//9i+s9gwCoaaGMR
evta/58PTEWzr21hufPjA8N+qlnBwAAAAAD//2JiWLci5v1+HmFXDqcnULE/MxgYGBj+f6CaJQAA
AAD//2Ji2FrkY3iYpYC5qDeGgeEMAwPDvwQBBoYvcTwOVLMEAAAA//9isDBgkP///0EOg9z35v//
Gc/eeW7BwPj5+QGZhANUswMAAAD//2JgqGBgYGBgqEMXlvhMPUsAAAAA//8iYDd1AAAAAP//AwDR
w7IkEbzhVQAAAABJRU5ErkJggg==
"""
                )
            )
        ),
    )
    return f


def load_default(size: float | None = None) -> FreeTypeFont | ImageFont:
    """If FreeType support is available, load a version of Aileron Regular,
    https://dotcolon.net/font/aileron, with a more limited character set.

    Otherwise, load a "better than nothing" font.

    .. versionadded:: 1.1.4

    :param size: The font size of Aileron Regular.

        .. versionadded:: 10.1.0

    :return: A font object.
    """
    if isinstance(core, ModuleType) or size is not None:
        return truetype(
            BytesIO(
                base64.b64decode(
                    b"""
AAEAAAAPAIAAAwBwRkZUTYwDlUAAADFoAAAAHEdERUYAqADnAAAo8AAAACRHUE9ThhmITwAAKfgAA
AduR1NVQnHxefoAACkUAAAA4k9TLzJovoHLAAABeAAAAGBjbWFw5lFQMQAAA6gAAAGqZ2FzcP//AA
MAACjoAAAACGdseWYmRXoPAAAGQAAAHfhoZWFkE18ayQAAAPwAAAA2aGhlYQboArEAAAE0AAAAJGh
tdHjjERZ8AAAB2AAAAdBsb2NhuOexrgAABVQAAADqbWF4cAC7AEYAAAFYAAAAIG5hbWUr+h5lAAAk
OAAAA6Jwb3N0D3oPTQAAJ9wAAAEKAAEAAAABGhxJDqIhXw889QALA+gAAAAA0Bqf2QAAAADhCh2h/
2r/LgOxAyAAAAAIAAIAAAAAAAAAAQAAA8r/GgAAA7j/av9qA7EAAQAAAAAAAAAAAAAAAAAAAHQAAQ
AAAHQAQwAFAAAAAAACAAAAAQABAAAAQAAAAAAAAAADAfoBkAAFAAgCigJYAAAASwKKAlgAAAFeADI
BPgAAAAAFAAAAAAAAAAAAAAcAAAAAAAAAAAAAAABVS1dOAEAAIPsCAwL/GgDIA8oA5iAAAJMAAAAA
AhICsgAAACAAAwH0AAAAAAAAAU0AAADYAAAA8gA5AVMAVgJEAEYCRAA1AuQAKQKOAEAAsAArATsAZ
AE7AB4CMABVAkQAUADc/+EBEgAgANwAJQEv//sCRAApAkQAggJEADwCRAAtAkQAIQJEADkCRAArAk
QAMgJEACwCRAAxANwAJQDc/+ECRABnAkQAUAJEAEQB8wAjA1QANgJ/AB0CcwBkArsALwLFAGQCSwB
kAjcAZALGAC8C2gBkAQgAZAIgADcCYQBkAj8AZANiAGQCzgBkAuEALwJWAGQC3QAvAmsAZAJJADQC
ZAAiAqoAXgJuACADuAAaAnEAGQJFABMCTwAuATMAYgEv//sBJwAiAkQAUAH0ADIBLAApAhMAJAJjA
EoCEQAeAmcAHgIlAB4BIgAVAmcAHgJRAEoA7gA+AOn/8wIKAEoA9wBGA1cASgJRAEoCSgAeAmMASg
JnAB4BSgBKAcsAGAE5ABQCUABCAgIAAQMRAAEB4v/6AgEAAQHOABQBLwBAAPoAYAEvACECRABNA0Y
AJAItAHgBKgAcAkQAUAEsAHQAygAgAi0AOQD3ADYA9wAWAaEANgGhABYCbAAlAYMAeAGDADkA6/9q
AhsAFAIKABUB/QAVAAAAAwAAAAMAAAAcAAEAAAAAAKQAAwABAAAAHAAEAIgAAAAeABAAAwAOAH4Aq
QCrALEAtAC3ALsgGSAdICYgOiBEISL7Av//AAAAIACpAKsAsAC0ALcAuyAYIBwgJiA5IEQhIvsB//
//4/+5/7j/tP+y/7D/reBR4E/gR+A14CzfTwVxAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAEGAAABAAAAAAAAAAECAAAAAgAAAAAAAAAAAAAAAAAAAAEAAAMEBQYHCAkKCwwNDg8QERIT
FBUWFxgZGhscHR4fICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj9AQUJDREVGR0hJSktMT
U5PUFFSU1RVVldYWVpbXF1eX2BhAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGQAAA
AAAAAAYnFmAAAAAABlAAAAAAAAAAAAAAAAAAAAAAAAAAAAY2htAAAAAAAAAABrbGlqAAAAAHAAbm9
ycwBnAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAmACYAJgAmAD4AUgCCAMoBCgFO
AVwBcgGIAaYBvAHKAdYB6AH2AgwCIAJKAogCpgLWAw4DIgNkA5wDugPUA+gD/AQQBEYEogS8BPoFJ
gVSBWoFgAWwBcoF1gX6BhQGJAZMBmgGiga0BuIHGgdUB2YHkAeiB8AH3AfyCAoIHAgqCDoITghcCG
oIogjSCPoJKglYCXwJwgnqCgIKKApACl4Klgq8CtwLDAs8C1YLjAuyC9oL7gwMDCYMSAxgDKAMrAz
qDQoNTA1mDYQNoA2uDcAN2g3oDfYODA4iDkoOXA5sDnoOnA7EDvwAAAAFAAAAAAH0ArwAAwAGAAkA
DAAPAAAxESERAxMhExcRASELARETAfT6qv6syKr+jgFUqsiqArz9RAGLAP/+1P8B/v3VAP8BLP4CA
P8AAgA5//IAuQKyAAMACwAANyMDMwIyFhQGIiY0oE4MZk84JCQ4JLQB/v3AJDgkJDgAAgBWAeUBPA
LfAAMABwAAEyMnMxcjJzOmRgpagkYKWgHl+vr6AAAAAAIARgAAAf4CsgAbAB8AAAEHMxUjByM3Iwc
jNyM1MzcjNTM3MwczNzMHMxUrAQczAZgdZXEvOi9bLzovWmYdZXEvOi9bLzovWp9bHlsBn4w429vb
2ziMONvb29s4jAAAAAMANf+mAg4DDAAfACYALAAAJRQGBxUjNS4BJzMeARcRLgE0Njc1MxUeARcjJ
icVHgEBFBYXNQ4BExU+ATU0Ag5xWDpgcgRcBz41Xl9oVTpVYwpcC1ttXP6cLTQuM5szOrVRZwlOTQ
ZqVzZECAEAGlukZAlOTQdrUG8O7iNlAQgxNhDlCDj+8/YGOjReAAAAAAUAKf/yArsCvAAHAAsAFQA
dACcAABIyFhQGIiY0EyMBMwQiBhUUFjI2NTQSMhYUBiImNDYiBhUUFjI2NTR5iFBQiFCVVwHAV/5c
OiMjOiPmiFBQiFCxOiMjOiMCvFaSVlaS/ZoCsjIzMC80NC8w/uNWklZWkhozMC80NC8wAAAAAgBA/
/ICbgLAACIALgAAARUjEQYjIiY1NDY3LgE1NDYzMhcVJiMiBhUUFhcWOwE1MxUFFBYzMjc1IyIHDg
ECbmBcYYOOVkg7R4hsQjY4Q0RNRD4SLDxW/pJUXzksPCkUUk0BgUb+zBVUZ0BkDw5RO1huCkULQzp
COAMBcHDHRz0J/AIHRQAAAAEAKwHlAIUC3wADAAATIycze0YKWgHl+gAAAAABAGT/sAEXAwwACQAA
EzMGEBcjLgE0Nt06dXU6OUBAAwzG/jDGVePs4wAAAAEAHv+wANEDDAAJAAATMx4BFAYHIzYQHjo5Q
EA5OnUDDFXj7ONVxgHQAAAAAQBVAFIB2wHbAA4AAAE3FwcXBycHJzcnNxcnMwEtmxOfcTJjYzJxnx
ObCj4BKD07KYolmZkliik7PbMAAQBQAFUB9AIlAAsAAAEjFSM1IzUzNTMVMwH0tTq1tTq1AR/Kyjj
OzgAAAAAB/+H/iACMAGQABAAANwcjNzOMWlFOXVrS3AAAAQAgAP8A8gE3AAMAABMjNTPy0tIA/zgA
AQAl//IApQByAAcAADYyFhQGIiY0STgkJDgkciQ4JCQ4AAAAAf/7/+IBNALQAAMAABcjEzM5Pvs+H
gLuAAAAAAIAKf/yAhsCwAADAAcAABIgECA2IBAgKQHy/g5gATL+zgLA/TJEAkYAAAAAAQCCAAABlg
KyAAgAAAERIxEHNTc2MwGWVr6SIygCsv1OAldxW1sWAAEAPAAAAg4CwAAZAAA3IRUhNRM+ATU0JiM
iDwEjNz4BMzIWFRQGB7kBUv4x+kI2QTt+EAFWAQp8aGVtSl5GRjEA/0RVLzlLmAoKa3FsUkNxXQAA
AAEALf/yAhYCwAAqAAABHgEVFAYjIi8BMxceATMyNjU0KwE1MzI2NTQmIyIGDwEjNz4BMzIWFRQGA
YxBSZJo2RUBVgEHV0JBUaQREUBUQzc5TQcBVgEKfGhfcEMBbxJbQl1x0AoKRkZHPn9GSD80QUVCCg
pfbGBPOlgAAAACACEAAAIkArIACgAPAAAlIxUjNSE1ATMRMyMRBg8BAiRXVv6qAVZWV60dHLCurq4
rAdn+QgFLMibzAAABADn/8gIZArIAHQAAATIWFRQGIyIvATMXFjMyNjU0JiMiByMTIRUhBzc2ATNv
d5Fl1RQBVgIad0VSTkVhL1IwAYj+vh8rMAHHgGdtgcUKCoFXTU5bYgGRRvAuHQAAAAACACv/8gITA
sAAFwAjAAABMhYVFAYjIhE0NjMyFh8BIycmIyIDNzYTMjY1NCYjIgYVFBYBLmp7imr0l3RZdAgBXA
IYZ5wKJzU6QVNJSz5SUAHSgWltiQFGxcNlVQoKdv7sPiz+ZF1LTmJbU0lhAAAAAQAyAAACGgKyAAY
AAAEVASMBITUCGv6oXAFL/oECsij9dgJsRgAAAAMALP/xAhgCwAAWACAALAAAAR4BFRQGIyImNTQ2
Ny4BNTQ2MhYVFAYmIgYVFBYyNjU0AzI2NTQmIyIGFRQWAZQ5S5BmbIpPOjA7ecp5P2F8Q0J8RIVJS
0pLTEtOAW0TXTxpZ2ZqPF0SE1A3VWVlVTdQ/UU0N0RENzT9/ko+Ok1NOj1LAAIAMf/yAhkCwAAXAC
MAAAEyERQGIyImLwEzFxYzMhMHBiMiJjU0NhMyNjU0JiMiBhUUFgEl9Jd0WXQIAVwCGGecCic1SWp
7imo+UlBAQVNJAsD+usXDZVUKCnYBFD4sgWltif5kW1NJYV1LTmIAAAACACX/8gClAiAABwAPAAAS
MhYUBiImNBIyFhQGIiY0STgkJDgkJDgkJDgkAiAkOCQkOP52JDgkJDgAAAAC/+H/iAClAiAABwAMA
AASMhYUBiImNBMHIzczSTgkJDgkaFpSTl4CICQ4JCQ4/mba5gAAAQBnAB4B+AH0AAYAAAENARUlNS
UB+P6qAVb+bwGRAbCmpkbJRMkAAAIAUAC7AfQBuwADAAcAAAEhNSERITUhAfT+XAGk/lwBpAGDOP8
AOAABAEQAHgHVAfQABgAAARUFNS0BNQHV/m8BVv6qAStEyUSmpkYAAAAAAgAj//IB1ALAABgAIAAA
ATIWFRQHDgEHIz4BNz4BNTQmIyIGByM+ARIyFhQGIiY0AQRibmktIAJWBSEqNig+NTlHBFoDezQ4J
CQ4JALAZ1BjaS03JS1DMD5LLDQ/SUVgcv2yJDgkJDgAAAAAAgA2/5gDFgKYADYAQgAAAQMGFRQzMj
Y1NCYjIg4CFRQWMzI2NxcGIyImNTQ+AjMyFhUUBiMiJwcGIyImNTQ2MzIfATcHNzYmIyIGFRQzMjY
Cej8EJjJJlnBAfGQ+oHtAhjUYg5OPx0h2k06Os3xRWQsVLjY5VHtdPBwJETcJDyUoOkZEJz8B0f74
EQ8kZl6EkTFZjVOLlyknMVm1pmCiaTq4lX6CSCknTVRmmR8wPdYnQzxuSWVGAAIAHQAAAncCsgAHA
AoAACUjByMTMxMjATMDAcj+UVz4dO5d/sjPZPT0ArL9TgE6ATQAAAADAGQAAAJMArIAEAAbACcAAA
EeARUUBgcGKwERMzIXFhUUJRUzMjc2NTQnJiMTPgE1NCcmKwEVMzIBvkdHZkwiNt7LOSGq/oeFHBt
hahIlSTM+cB8Yj5UWAW8QT0VYYgwFArIEF5Fv1eMED2NfDAL93AU+N24PBP0AAAAAAQAv//ICjwLA
ABsAAAEyFh8BIycmIyIGFRQWMzI/ATMHDgEjIiY1NDYBdX+PCwFWAiKiaHx5ZaIiAlYBCpWBk6a0A
sCAagoKpqN/gaOmCgplhcicn8sAAAIAZAAAAp8CsgAMABkAAAEeARUUBgcGKwERMzITPgE1NCYnJi
sBETMyAY59lJp8IzXN0jUVWmdjWRs5d3I4Aq4QqJWUug8EArL9mQ+PeHGHDgX92gAAAAABAGQAAAI
vArIACwAAJRUhESEVIRUhFSEVAi/+NQHB/pUBTf6zRkYCskbwRvAAAAABAGQAAAIlArIACQAAExUh
FSERIxEhFboBQ/69VgHBAmzwRv7KArJGAAAAAAEAL//yAo8CwAAfAAABMxEjNQcGIyImNTQ2MzIWH
wEjJyYjIgYVFBYzMjY1IwGP90wfPnWTprSSf48LAVYCIqJofHllVG+hAU3+s3hARsicn8uAagoKpq
N/gaN1XAAAAAEAZAAAAowCsgALAAABESMRIREjETMRIRECjFb+hFZWAXwCsv1OAS7+0gKy/sQBPAA
AAAABAGQAAAC6ArIAAwAAMyMRM7pWVgKyAAABADf/8gHoArIAEwAAAREUBw4BIyImLwEzFxYzMjc2
NREB6AIFcGpgbQIBVgIHfXQKAQKy/lYxIltob2EpKYyEFD0BpwAAAAABAGQAAAJ0ArIACwAACQEjA
wcVIxEzEQEzATsBJ3ntQlZWAVVlAWH+nwEnR+ACsv6RAW8AAQBkAAACLwKyAAUAACUVIREzEQIv/j
VWRkYCsv2UAAABAGQAAAMUArIAFAAAAREjETQ3BgcDIwMmJxYVESMRMxsBAxRWAiMxemx8NxsCVo7
MywKy/U4BY7ZLco7+nAFmoFxLtP6dArL9lwJpAAAAAAEAZAAAAoACsgANAAAhIwEWFREjETMBJjUR
MwKAhP67A1aEAUUDVAJeeov+pwKy/aJ5jAFZAAAAAgAv//ICuwLAAAkAEwAAEiAWFRQGICY1NBIyN
jU0JiIGFRTbATSsrP7MrNrYenrYegLAxaKhxsahov47nIeIm5uIhwACAGQAAAJHArIADgAYAAABHg
EVFAYHBisBESMRMzITNjQnJisBETMyAZRUX2VOHzuAVtY7GlxcGDWIiDUCrgtnVlVpCgT+5gKy/rU
V1BUF/vgAAAACAC//zAK9AsAAEgAcAAAlFhcHJiMiBwYjIiY1NDYgFhUUJRQWMjY1NCYiBgI9PUMx
UDcfKh8omqysATSs/dR62Hp62HpICTg7NgkHxqGixcWitbWHnJyHiJubAAIAZAAAAlgCsgAXACMAA
CUWFyMmJyYnJisBESMRMzIXHgEVFAYHFiUzMjc+ATU0JyYrAQIqDCJfGQwNWhAhglbiOx9QXEY1Tv
6bhDATMj1lGSyMtYgtOXR0BwH+1wKyBApbU0BSESRAAgVAOGoQBAABADT/8gIoAsAAJQAAATIWFyM
uASMiBhUUFhceARUUBiMiJiczHgEzMjY1NCYnLgE1NDYBOmd2ClwGS0E6SUNRdW+HZnKKC1wPWkQ9
Uk1cZGuEAsBwXUJHNjQ3OhIbZVZZbm5kREo+NT5DFRdYUFdrAAAAAAEAIgAAAmQCsgAHAAABIxEjE
SM1IQJk9lb2AkICbP2UAmxGAAEAXv/yAmQCsgAXAAABERQHDgEiJicmNREzERQXHgEyNjc2NRECZA
IIgfCBCAJWAgZYmlgGAgKy/k0qFFxzc1wUKgGz/lUrEkRQUEQSKwGrAAAAAAEAIAAAAnoCsgAGAAA
hIwMzGwEzAYJ07l3N1FwCsv2PAnEAAAEAGgAAA7ECsgAMAAABAyMLASMDMxsBMxsBA7HAcZyicrZi
kaB0nJkCsv1OAlP9rQKy/ZsCW/2kAmYAAAEAGQAAAm8CsgALAAAhCwEjEwMzGwEzAxMCCsrEY/bkY
re+Y/D6AST+3AFcAVb+5gEa/q3+oQAAAQATAAACUQKyAAgAAAERIxEDMxsBMwFdVvRjwLphARD+8A
EQAaL+sQFPAAABAC4AAAI5ArIACQAAJRUhNQEhNSEVAQI5/fUBof57Aen+YUZGQgIqRkX92QAAAAA
BAGL/sAEFAwwABwAAARUjETMVIxEBBWlpowMMOP0UOANcAAAB//v/4gE0AtAAAwAABSMDMwE0Pvs+
HgLuAAAAAQAi/7AAxQMMAAcAABcjNTMRIzUzxaNpaaNQOALsOAABAFAA1wH0AmgABgAAJQsBIxMzE
wGwjY1GsESw1wFZ/qcBkf5vAAAAAQAy/6oBwv/iAAMAAAUhNSEBwv5wAZBWOAAAAAEAKQJEALYCsg
ADAAATIycztjhVUAJEbgAAAAACACT/8gHQAiAAHQAlAAAhJwcGIyImNTQ2OwE1NCcmIyIHIz4BMzI
XFh0BFBcnMjY9ASYVFAF6CR0wVUtgkJoiAgdgaQlaBm1Zrg4DCuQ9R+5MOSFQR1tbDiwUUXBUXowf
J8c9SjRORzYSgVwAAAAAAgBK//ICRQLfABEAHgAAATIWFRQGIyImLwEVIxEzETc2EzI2NTQmIyIGH
QEUFgFUcYCVbiNJEyNWVigySElcU01JXmECIJd4i5QTEDRJAt/+3jkq/hRuZV55ZWsdX14AAQAe//
IB9wIgABgAAAEyFhcjJiMiBhUUFjMyNjczDgEjIiY1NDYBF152DFocbEJXU0A1Rw1aE3pbaoKQAiB
oWH5qZm1tPDlaXYuLgZcAAAACAB7/8gIZAt8AEQAeAAABESM1BwYjIiY1NDYzMhYfAREDMjY9ATQm
IyIGFRQWAhlWKDJacYCVbiNJEyOnSV5hQUlcUwLf/SFVOSqXeIuUExA0ARb9VWVrHV9ebmVeeQACA
B7/8gH9AiAAFQAbAAABFAchHgEzMjY3Mw4BIyImNTQ2MzIWJyIGByEmAf0C/oAGUkA1SwlaD4FXbI
WObmt45UBVBwEqDQEYFhNjWD84W16Oh3+akU9aU60AAAEAFQAAARoC8gAWAAATBh0BMxUjESMRIzU
zNTQ3PgEzMhcVJqcDbW1WOTkDB0k8Hx5oAngVITRC/jQBzEIsJRs5PwVHEwAAAAIAHv8uAhkCIAAi
AC8AAAERFAcOASMiLwEzFx4BMzI2NzY9AQcGIyImNTQ2MzIWHwE1AzI2PQE0JiMiBhUUFgIZAQSEd
NwRAVcBBU5DTlUDASgyWnGAlW4jSRMjp0leYUFJXFMCEv5wSh1zeq8KCTI8VU0ZIQk5Kpd4i5QTED
RJ/iJlax1fXm5lXnkAAQBKAAACCgLkABcAAAEWFREjETQnLgEHDgEdASMRMxE3NjMyFgIIAlYCBDs
6RVRWViE5UVViAYUbQP7WASQxGzI7AQJyf+kC5P7TPSxUAAACAD4AAACsAsAABwALAAASMhYUBiIm
NBMjETNeLiAgLiBiVlYCwCAuICAu/WACEgAC//P/LgCnAsAABwAVAAASMhYUBiImNBcRFAcGIyInN
RY3NjURWS4gIC4gYgMLcRwNSgYCAsAgLiAgLo79wCUbZAJGBzMOHgJEAAAAAQBKAAACCALfAAsAAC
EnBxUjETMREzMHEwGTwTJWVvdu9/rgN6kC3/4oAQv6/ugAAQBG//wA3gLfAA8AABMRFBceATcVBiM
iJicmNRGcAQIcIxkkKi4CAQLf/bkhERoSBD4EJC8SNAJKAAAAAQBKAAADEAIgACQAAAEWFREjETQn
JiMiFREjETQnJiMiFREjETMVNzYzMhYXNzYzMhYDCwVWBAxedFYEDF50VlYiJko7ThAvJkpEVAGfI
jn+vAEcQyRZ1v76ARxDJFnW/voCEk08HzYtRB9HAAAAAAEASgAAAgoCIAAWAAABFhURIxE0JyYjIg
YdASMRMxU3NjMyFgIIAlYCCXBEVVZWITlRVWIBhRtA/tYBJDEbbHR/6QISWz0sVAAAAAACAB7/8gI
sAiAABwARAAASIBYUBiAmNBIyNjU0JiIGFRSlAQCHh/8Ah7ieWlqeWgIgn/Cfn/D+s3ZfYHV1YF8A
AgBK/zwCRQIgABEAHgAAATIWFRQGIyImLwERIxEzFTc2EzI2NTQmIyIGHQEUFgFUcYCVbiNJEyNWV
igySElcU01JXmECIJd4i5QTEDT+8wLWVTkq/hRuZV55ZWsdX14AAgAe/zwCGQIgABEAHgAAAREjEQ
cGIyImNTQ2MzIWHwE1AzI2PQE0JiMiBhUUFgIZVigyWnGAlW4jSRMjp0leYUFJXFMCEv0qARk5Kpd
4i5QTEDRJ/iJlax1fXm5lXnkAAQBKAAABPgIeAA0AAAEyFxUmBhURIxEzFTc2ARoWDkdXVlYwIwIe
B0EFVlf+0gISU0cYAAEAGP/yAa0CIAAjAAATMhYXIyYjIgYVFBYXHgEVFAYjIiYnMxYzMjY1NCYnL
gE1NDbkV2MJWhNdKy04PF1XbVhWbgxaE2ktOjlEUllkAiBaS2MrJCUoEBlPQkhOVFZoKCUmLhIWSE
BIUwAAAAEAFP/4ARQCiQAXAAATERQXHgE3FQYjIiYnJjURIzUzNTMVMxWxAQMmMx8qMjMEAUdHVmM
BzP7PGw4mFgY/BSwxDjQBNUJ7e0IAAAABAEL/8gICAhIAFwAAAREjNQcGIyImJyY1ETMRFBceATMy
Nj0BAgJWITlRT2EKBVYEBkA1RFECEv3uWj4qTToiOQE+/tIlJC43c4DpAAAAAAEAAQAAAfwCEgAGA
AABAyMDMxsBAfzJaclfop8CEv3uAhL+LQHTAAABAAEAAAMLAhIADAAAAQMjCwEjAzMbATMbAQMLqW
Z2dmapY3t0a3Z7AhL97gG+/kICEv5AAcD+QwG9AAAB//oAAAHWAhIACwAAARMjJwcjEwMzFzczARq
8ZIuKY763ZoWFYwEO/vLV1QEMAQbNzQAAAQAB/y4B+wISABEAAAEDDgEjIic1FjMyNj8BAzMbAQH7
2iFZQB8NDRIpNhQH02GenQIS/cFVUAJGASozEwIt/i4B0gABABQAAAGxAg4ACQAAJRUhNQEhNSEVA
QGx/mMBNP7iAYL+zkREQgGIREX+ewAAAAABAED/sAEOAwwALAAAASMiBhUUFxYVFAYHHgEVFAcGFR
QWOwEVIyImNTQ3NjU0JzU2NTQnJjU0NjsBAQ4MKiMLDS4pKS4NCyMqDAtERAwLUlILDERECwLUGBk
WTlsgKzUFBTcrIFtOFhkYOC87GFVMIkUIOAhFIkxVGDsvAAAAAAEAYP84AJoDIAADAAAXIxEzmjo6
yAPoAAEAIf+wAO8DDAAsAAATFQYVFBcWFRQGKwE1MzI2NTQnJjU0NjcuATU0NzY1NCYrATUzMhYVF
AcGFRTvUgsMREQLDCojCw0uKSkuDQsjKgwLREQMCwF6OAhFIkxVGDsvOBgZFk5bICs1BQU3KyBbTh
YZGDgvOxhVTCJFAAABAE0A3wH2AWQAEwAAATMUIyImJyYjIhUjNDMyFhcWMzIBvjhuGywtQR0xOG4
bLC1BHTEBZIURGCNMhREYIwAAAwAk/94DIgLoAAcAEQApAAAAIBYQBiAmECQgBhUUFiA2NTQlMhYX
IyYjIgYUFjMyNjczDgEjIiY1NDYBAQFE3d3+vN0CB/7wubkBELn+xVBnD1wSWDo+QTcqOQZcEmZWX
HN2Aujg/rbg4AFKpr+Mjb6+jYxbWEldV5ZZNShLVn5na34AAgB4AFIB9AGeAAUACwAAAQcXIyc3Mw
cXIyc3AUqJiUmJifOJiUmJiQGepqampqampqYAAAIAHAHSAQ4CwAAHAA8AABIyFhQGIiY0NiIGFBY
yNjRgakREakSTNCEhNCECwEJqQkJqCiM4IyM4AAAAAAIAUAAAAfQCCwALAA8AAAEzFSMVIzUjNTM1
MxMhNSEBP7W1OrW1OrX+XAGkAVs4tLQ4sP31OAAAAQB0AkQBAQKyAAMAABMjNzOsOD1QAkRuAAAAA
AEAIADsAKoBdgAHAAASMhYUBiImNEg6KCg6KAF2KDooKDoAAAIAOQBSAbUBngAFAAsAACUHIzcnMw
UHIzcnMwELiUmJiUkBM4lJiYlJ+KampqampqYAAAABADYB5QDhAt8ABAAAEzczByM2Xk1OXQHv8Po
AAQAWAeUAwQLfAAQAABMHIzczwV5NTl0C1fD6AAIANgHlAYsC3wAEAAkAABM3MwcjPwEzByM2Xk1O
XapeTU5dAe/w+grw+gAAAgAWAeUBawLfAAQACQAAEwcjNzMXByM3M8FeTU5dql5NTl0C1fD6CvD6A
AADACX/8gI1AHIABwAPABcAADYyFhQGIiY0NjIWFAYiJjQ2MhYUBiImNEk4JCQ4JOw4JCQ4JOw4JC
Q4JHIkOCQkOCQkOCQkOCQkOCQkOAAAAAEAeABSAUoBngAFAAABBxcjJzcBSomJSYmJAZ6mpqamAAA
AAAEAOQBSAQsBngAFAAAlByM3JzMBC4lJiYlJ+KampgAAAf9qAAABgQKyAAMAACsBATM/VwHAVwKy
AAAAAAIAFAHIAdwClAAHABQAABMVIxUjNSM1BRUjNwcjJxcjNTMXN9pKMkoByDICKzQqATJLKysCl
CmjoykBy46KiY3Lm5sAAQAVAAABvALyABgAAAERIxEjESMRIzUzNTQ3NjMyFxUmBgcGHQEBvFbCVj
k5AxHHHx5iVgcDAg798gHM/jQBzEIOJRuWBUcIJDAVIRYAAAABABX//AHkAvIAJQAAJR4BNxUGIyI
mJyY1ESYjIgcGHQEzFSMRIxEjNTM1NDc2MzIXERQBowIcIxkkKi4CAR4nXgwDbW1WLy8DEbNdOmYa
EQQ/BCQvEjQCFQZWFSEWQv40AcxCDiUblhP9uSEAAAAAAAAWAQ4AAQAAAAAAAAATACgAAQAAAAAAA
QAHAEwAAQAAAAAAAgAHAGQAAQAAAAAAAwAaAKIAAQAAAAAABAAHAM0AAQAAAAAABQA8AU8AAQAAAA
AABgAPAawAAQAAAAAACAALAdQAAQAAAAAACQALAfgAAQAAAAAACwAXAjQAAQAAAAAADAAXAnwAAwA
BBAkAAAAmAAAAAwABBAkAAQAOADwAAwABBAkAAgAOAFQAAwABBAkAAwA0AGwAAwABBAkABAAOAL0A
AwABBAkABQB4ANUAAwABBAkABgAeAYwAAwABBAkACAAWAbwAAwABBAkACQAWAeAAAwABBAkACwAuA
gQAAwABBAkADAAuAkwATgBvACAAUgBpAGcAaAB0AHMAIABSAGUAcwBlAHIAdgBlAGQALgAATm8gUm
lnaHRzIFJlc2VydmVkLgAAQQBpAGwAZQByAG8AbgAAQWlsZXJvbgAAUgBlAGcAdQBsAGEAcgAAUmV
ndWxhcgAAMQAuADEAMAAyADsAVQBLAFcATgA7AEEAaQBsAGUAcgBvAG4ALQBSAGUAZwB1AGwAYQBy
AAAxLjEwMjtVS1dOO0FpbGVyb24tUmVndWxhcgAAQQBpAGwAZQByAG8AbgAAQWlsZXJvbgAAVgBlA
HIAcwBpAG8AbgAgADEALgAxADAAMgA7AFAAUwAgADAAMAAxAC4AMQAwADIAOwBoAG8AdABjAG8Abg
B2ACAAMQAuADAALgA3ADAAOwBtAGEAawBlAG8AdABmAC4AbABpAGIAMgAuADUALgA1ADgAMwAyADk
AAFZlcnNpb24gMS4xMDI7UFMgMDAxLjEwMjtob3Rjb252IDEuMC43MDttYWtlb3RmLmxpYjIuNS41
ODMyOQAAQQBpAGwAZQByAG8AbgAtAFIAZQBnAHUAbABhAHIAAEFpbGVyb24tUmVndWxhcgAAUwBvA
HIAYQAgAFMAYQBnAGEAbgBvAABTb3JhIFNhZ2FubwAAUwBvAHIAYQAgAFMAYQBnAGEAbgBvAABTb3
JhIFNhZ2FubwAAaAB0AHQAcAA6AC8ALwB3AHcAdwAuAGQAbwB0AGMAbwBsAG8AbgAuAG4AZQB0AAB
odHRwOi8vd3d3LmRvdGNvbG9uLm5ldAAAaAB0AHQAcAA6AC8ALwB3AHcAdwAuAGQAbwB0AGMAbwBs
AG8AbgAuAG4AZQB0AABodHRwOi8vd3d3LmRvdGNvbG9uLm5ldAAAAAACAAAAAAAA/4MAMgAAAAAAA
AAAAAAAAAAAAAAAAAAAAHQAAAABAAIAAwAEAAUABgAHAAgACQAKAAsADAANAA4ADwAQABEAEgATAB
QAFQAWABcAGAAZABoAGwAcAB0AHgAfACAAIQAiACMAJAAlACYAJwAoACkAKgArACwALQAuAC8AMAA
xADIAMwA0ADUANgA3ADgAOQA6ADsAPAA9AD4APwBAAEEAQgBDAEQARQBGAEcASABJAEoASwBMAE0A
TgBPAFAAUQBSAFMAVABVAFYAVwBYAFkAWgBbAFwAXQBeAF8AYABhAIsAqQCDAJMAjQDDAKoAtgC3A
LQAtQCrAL4AvwC8AIwAwADBAAAAAAAB//8AAgABAAAADAAAABwAAAACAAIAAwBxAAEAcgBzAAIABA
AAAAIAAAABAAAACgBMAGYAAkRGTFQADmxhdG4AGgAEAAAAAP//AAEAAAAWAANDQVQgAB5NT0wgABZ
ST00gABYAAP//AAEAAAAA//8AAgAAAAEAAmxpZ2EADmxvY2wAFAAAAAEAAQAAAAEAAAACAAYAEAAG
AAAAAgASADQABAAAAAEATAADAAAAAgAQABYAAQAcAAAAAQABAE8AAQABAGcAAQABAE8AAwAAAAIAE
AAWAAEAHAAAAAEAAQAvAAEAAQBnAAEAAQAvAAEAGgABAAgAAgAGAAwAcwACAE8AcgACAEwAAQABAE
kAAAABAAAACgBGAGAAAkRGTFQADmxhdG4AHAAEAAAAAP//AAIAAAABABYAA0NBVCAAFk1PTCAAFlJ
PTSAAFgAA//8AAgAAAAEAAmNwc3AADmtlcm4AFAAAAAEAAAAAAAEAAQACAAYADgABAAAAAQASAAIA
AAACAB4ANgABAAoABQAFAAoAAgABACQAPQAAAAEAEgAEAAAAAQAMAAEAOP/nAAEAAQAkAAIGigAEA
AAFJAXKABoAGQAA//gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAD/sv+4/+z/7v/MAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAD/xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/9T/6AAAAAD/8QAA
ABD/vQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/7gAAAAAAAAAAAAAAAAAA//MAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABIAAAAAAAAAAP/5AAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP/gAAD/4AAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//L/9AAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAA/+gAAAAAAAkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP/zAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP/mAAAAAAAAAAAAAAAAAAD
/4gAA//AAAAAA//YAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/+AAAAAAAAP/OAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/zv/qAAAAAP/0AAAACAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP/ZAAD/egAA/1kAAAAA/5D/rgAAAAAAAAAAAA
AAAAAAAAAAAAAAAAD/9AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAD/8AAA/7b/8P+wAAD/8P/E/98AAAAA/8P/+P/0//oAAAAAAAAAAAAA//gA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/+AAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/w//C/9MAAP/SAAD/9wAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAD/yAAA/+kAAAAA//QAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/9wAAAAD//QAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAP/2AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAP/cAAAAAAAAAAAAAAAA/7YAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAP/8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/6AAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAkAFAAEAAAAAQACwAAABcA
BgAAAAAAAAAIAA4AAAAAAAsAEgAAAAAAAAATABkAAwANAAAAAQAJAAAAAAAAAAAAAAAAAAAAGAAAA
AAABwAAAAAAAAAAAAAAFQAFAAAAAAAYABgAAAAUAAAACgAAAAwAAgAPABEAFgAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFAAEAEQBdAAYAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAcAAAAAAAAABwAAAAAACAAAAAAAAAAAAAcAAAAHAAAAEwAJ
ABUADgAPAAAACwAQAAAAAAAAAAAAAAAAAAUAGAACAAIAAgAAAAIAGAAXAAAAGAAAABYAFgACABYAA
gAWAAAAEQADAAoAFAAMAA0ABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASAAAAEgAGAAEAHgAkAC
YAJwApACoALQAuAC8AMgAzADcAOAA5ADoAPAA9AEUASABOAE8AUgBTAFUAVwBZAFoAWwBcAF0AcwA
AAAAAAQAAAADa3tfFAAAAANAan9kAAAAA4QodoQ==
"""
                )
            ),
            10 if size is None else size,
            layout_engine=Layout.BASIC,
        )
    return load_default_imagefont()

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc2459.py ===
#
# This file is part of pyasn1-modules software.
#
# Updated by Russ Housley to resolve the TODO regarding the Certificate
#   Policies Certificate Extension.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# X.509 message syntax
#
# ASN.1 source from:
# http://www.trl.ibm.com/projects/xml/xss4j/data/asn1/grammars/x509.asn
# http://www.ietf.org/rfc/rfc2459.txt
#
# Sample captures from:
# http://wiki.wireshark.org/SampleCaptures/
#
from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import opentype
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

MAX = float('inf')

#
# PKIX1Explicit88
#

# Upper Bounds
ub_name = univ.Integer(32768)
ub_common_name = univ.Integer(64)
ub_locality_name = univ.Integer(128)
ub_state_name = univ.Integer(128)
ub_organization_name = univ.Integer(64)
ub_organizational_unit_name = univ.Integer(64)
ub_title = univ.Integer(64)
ub_match = univ.Integer(128)
ub_emailaddress_length = univ.Integer(128)
ub_common_name_length = univ.Integer(64)
ub_country_name_alpha_length = univ.Integer(2)
ub_country_name_numeric_length = univ.Integer(3)
ub_domain_defined_attributes = univ.Integer(4)
ub_domain_defined_attribute_type_length = univ.Integer(8)
ub_domain_defined_attribute_value_length = univ.Integer(128)
ub_domain_name_length = univ.Integer(16)
ub_extension_attributes = univ.Integer(256)
ub_e163_4_number_length = univ.Integer(15)
ub_e163_4_sub_address_length = univ.Integer(40)
ub_generation_qualifier_length = univ.Integer(3)
ub_given_name_length = univ.Integer(16)
ub_initials_length = univ.Integer(5)
ub_integer_options = univ.Integer(256)
ub_numeric_user_id_length = univ.Integer(32)
ub_organization_name_length = univ.Integer(64)
ub_organizational_unit_name_length = univ.Integer(32)
ub_organizational_units = univ.Integer(4)
ub_pds_name_length = univ.Integer(16)
ub_pds_parameter_length = univ.Integer(30)
ub_pds_physical_address_lines = univ.Integer(6)
ub_postal_code_length = univ.Integer(16)
ub_surname_length = univ.Integer(40)
ub_terminal_id_length = univ.Integer(24)
ub_unformatted_address_length = univ.Integer(180)
ub_x121_address_length = univ.Integer(16)


class UniversalString(char.UniversalString):
    pass


class BMPString(char.BMPString):
    pass


class UTF8String(char.UTF8String):
    pass


id_pkix = univ.ObjectIdentifier('1.3.6.1.5.5.7')
id_pe = univ.ObjectIdentifier('1.3.6.1.5.5.7.1')
id_qt = univ.ObjectIdentifier('1.3.6.1.5.5.7.2')
id_kp = univ.ObjectIdentifier('1.3.6.1.5.5.7.3')
id_ad = univ.ObjectIdentifier('1.3.6.1.5.5.7.48')

id_qt_cps = univ.ObjectIdentifier('1.3.6.1.5.5.7.2.1')
id_qt_unotice = univ.ObjectIdentifier('1.3.6.1.5.5.7.2.2')

id_ad_ocsp = univ.ObjectIdentifier('1.3.6.1.5.5.7.48.1')
id_ad_caIssuers = univ.ObjectIdentifier('1.3.6.1.5.5.7.48.2')




id_at = univ.ObjectIdentifier('2.5.4')
id_at_name = univ.ObjectIdentifier('2.5.4.41')
# preserve misspelled variable for compatibility
id_at_sutname = id_at_surname = univ.ObjectIdentifier('2.5.4.4')
id_at_givenName = univ.ObjectIdentifier('2.5.4.42')
id_at_initials = univ.ObjectIdentifier('2.5.4.43')
id_at_generationQualifier = univ.ObjectIdentifier('2.5.4.44')


class X520name(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('teletexString',
                            char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name))),
        namedtype.NamedType('printableString',
                            char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name))),
        namedtype.NamedType('universalString',
                            char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name))),
        namedtype.NamedType('utf8String',
                            char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name))),
        namedtype.NamedType('bmpString',
                            char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name)))
    )


id_at_commonName = univ.ObjectIdentifier('2.5.4.3')


class X520CommonName(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('teletexString', char.TeletexString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name))),
        namedtype.NamedType('printableString', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name))),
        namedtype.NamedType('universalString', char.UniversalString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name))),
        namedtype.NamedType('utf8String',
                            char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name))),
        namedtype.NamedType('bmpString',
                            char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name)))
    )


id_at_localityName = univ.ObjectIdentifier('2.5.4.7')


class X520LocalityName(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('teletexString', char.TeletexString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name))),
        namedtype.NamedType('printableString', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name))),
        namedtype.NamedType('universalString', char.UniversalString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name))),
        namedtype.NamedType('utf8String',
                            char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name))),
        namedtype.NamedType('bmpString',
                            char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name)))
    )


id_at_stateOrProvinceName = univ.ObjectIdentifier('2.5.4.8')


class X520StateOrProvinceName(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('teletexString',
                            char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name))),
        namedtype.NamedType('printableString', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name))),
        namedtype.NamedType('universalString', char.UniversalString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name))),
        namedtype.NamedType('utf8String',
                            char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name))),
        namedtype.NamedType('bmpString',
                            char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name)))
    )


id_at_organizationName = univ.ObjectIdentifier('2.5.4.10')


class X520OrganizationName(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('teletexString', char.TeletexString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name))),
        namedtype.NamedType('printableString', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name))),
        namedtype.NamedType('universalString', char.UniversalString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name))),
        namedtype.NamedType('utf8String', char.UTF8String().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name))),
        namedtype.NamedType('bmpString', char.BMPString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name)))
    )


id_at_organizationalUnitName = univ.ObjectIdentifier('2.5.4.11')


class X520OrganizationalUnitName(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('teletexString', char.TeletexString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name))),
        namedtype.NamedType('printableString', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name))),
        namedtype.NamedType('universalString', char.UniversalString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name))),
        namedtype.NamedType('utf8String', char.UTF8String().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name))),
        namedtype.NamedType('bmpString', char.BMPString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name)))
    )


id_at_title = univ.ObjectIdentifier('2.5.4.12')


class X520Title(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('teletexString',
                            char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title))),
        namedtype.NamedType('printableString',
                            char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title))),
        namedtype.NamedType('universalString',
                            char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title))),
        namedtype.NamedType('utf8String',
                            char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title))),
        namedtype.NamedType('bmpString',
                            char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title)))
    )


id_at_dnQualifier = univ.ObjectIdentifier('2.5.4.46')


class X520dnQualifier(char.PrintableString):
    pass


id_at_countryName = univ.ObjectIdentifier('2.5.4.6')


class X520countryName(char.PrintableString):
    subtypeSpec = char.PrintableString.subtypeSpec + constraint.ValueSizeConstraint(2, 2)


pkcs_9 = univ.ObjectIdentifier('1.2.840.113549.1.9')

emailAddress = univ.ObjectIdentifier('1.2.840.113549.1.9.1')


class Pkcs9email(char.IA5String):
    subtypeSpec = char.IA5String.subtypeSpec + constraint.ValueSizeConstraint(1, ub_emailaddress_length)


# ----

class DSAPrivateKey(univ.Sequence):
    """PKIX compliant DSA private key structure"""
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('version', univ.Integer(namedValues=namedval.NamedValues(('v1', 0)))),
        namedtype.NamedType('p', univ.Integer()),
        namedtype.NamedType('q', univ.Integer()),
        namedtype.NamedType('g', univ.Integer()),
        namedtype.NamedType('public', univ.Integer()),
        namedtype.NamedType('private', univ.Integer())
    )


# ----


class DirectoryString(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('teletexString',
                            char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
        namedtype.NamedType('printableString',
                            char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
        namedtype.NamedType('universalString',
                            char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
        namedtype.NamedType('utf8String',
                            char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
        namedtype.NamedType('bmpString', char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
        namedtype.NamedType('ia5String', char.IA5String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX)))
        # hm, this should not be here!? XXX
    )


# certificate and CRL specific structures begin here

class AlgorithmIdentifier(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('algorithm', univ.ObjectIdentifier()),
        namedtype.OptionalNamedType('parameters', univ.Any())
    )



# Algorithm OIDs and parameter structures

pkcs_1 = univ.ObjectIdentifier('1.2.840.113549.1.1')
rsaEncryption = univ.ObjectIdentifier('1.2.840.113549.1.1.1')
md2WithRSAEncryption = univ.ObjectIdentifier('1.2.840.113549.1.1.2')
md5WithRSAEncryption = univ.ObjectIdentifier('1.2.840.113549.1.1.4')
sha1WithRSAEncryption = univ.ObjectIdentifier('1.2.840.113549.1.1.5')
id_dsa_with_sha1 = univ.ObjectIdentifier('1.2.840.10040.4.3')


class Dss_Sig_Value(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('r', univ.Integer()),
        namedtype.NamedType('s', univ.Integer())
    )


dhpublicnumber = univ.ObjectIdentifier('1.2.840.10046.2.1')


class ValidationParms(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('seed', univ.BitString()),
        namedtype.NamedType('pgenCounter', univ.Integer())
    )


class DomainParameters(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('p', univ.Integer()),
        namedtype.NamedType('g', univ.Integer()),
        namedtype.NamedType('q', univ.Integer()),
        namedtype.NamedType('j', univ.Integer()),
        namedtype.OptionalNamedType('validationParms', ValidationParms())
    )


id_dsa = univ.ObjectIdentifier('1.2.840.10040.4.1')


class Dss_Parms(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('p', univ.Integer()),
        namedtype.NamedType('q', univ.Integer()),
        namedtype.NamedType('g', univ.Integer())
    )


# x400 address syntax starts here

teletex_domain_defined_attributes = univ.Integer(6)


class TeletexDomainDefinedAttribute(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type', char.TeletexString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_defined_attribute_type_length))),
        namedtype.NamedType('value', char.TeletexString())
    )


class TeletexDomainDefinedAttributes(univ.SequenceOf):
    componentType = TeletexDomainDefinedAttribute()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, ub_domain_defined_attributes)


terminal_type = univ.Integer(23)


class TerminalType(univ.Integer):
    subtypeSpec = univ.Integer.subtypeSpec + constraint.ValueSizeConstraint(0, ub_integer_options)
    namedValues = namedval.NamedValues(
        ('telex', 3),
        ('teletelex', 4),
        ('g3-facsimile', 5),
        ('g4-facsimile', 6),
        ('ia5-terminal', 7),
        ('videotex', 8)
    )


class PresentationAddress(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('pSelector', univ.OctetString().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('sSelector', univ.OctetString().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('tSelector', univ.OctetString().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.OptionalNamedType('nAddresses', univ.SetOf(componentType=univ.OctetString()).subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3),
            subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
    )


extended_network_address = univ.Integer(22)


class E163_4_address(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('number', char.NumericString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_e163_4_number_length),
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('sub-address', char.NumericString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_e163_4_sub_address_length),
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class ExtendedNetworkAddress(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('e163-4-address', E163_4_address()),
        namedtype.NamedType('psap-address', PresentationAddress().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
    )


class PDSParameter(univ.Set):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('printable-string', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_pds_parameter_length))),
        namedtype.OptionalNamedType('teletex-string', char.TeletexString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_pds_parameter_length)))
    )


local_postal_attributes = univ.Integer(21)


class LocalPostalAttributes(PDSParameter):
    pass


class UniquePostalName(PDSParameter):
    pass


unique_postal_name = univ.Integer(20)

poste_restante_address = univ.Integer(19)


class PosteRestanteAddress(PDSParameter):
    pass


post_office_box_address = univ.Integer(18)


class PostOfficeBoxAddress(PDSParameter):
    pass


street_address = univ.Integer(17)


class StreetAddress(PDSParameter):
    pass


class UnformattedPostalAddress(univ.Set):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('printable-address', univ.SequenceOf(componentType=char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_pds_parameter_length)).subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_pds_physical_address_lines)))),
        namedtype.OptionalNamedType('teletex-string', char.TeletexString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_unformatted_address_length)))
    )


physical_delivery_office_name = univ.Integer(10)


class PhysicalDeliveryOfficeName(PDSParameter):
    pass


physical_delivery_office_number = univ.Integer(11)


class PhysicalDeliveryOfficeNumber(PDSParameter):
    pass


extension_OR_address_components = univ.Integer(12)


class ExtensionORAddressComponents(PDSParameter):
    pass


physical_delivery_personal_name = univ.Integer(13)


class PhysicalDeliveryPersonalName(PDSParameter):
    pass


physical_delivery_organization_name = univ.Integer(14)


class PhysicalDeliveryOrganizationName(PDSParameter):
    pass


extension_physical_delivery_address_components = univ.Integer(15)


class ExtensionPhysicalDeliveryAddressComponents(PDSParameter):
    pass


unformatted_postal_address = univ.Integer(16)

postal_code = univ.Integer(9)


class PostalCode(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('numeric-code', char.NumericString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_postal_code_length))),
        namedtype.NamedType('printable-code', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_postal_code_length)))
    )


class PhysicalDeliveryCountryName(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('x121-dcc-code', char.NumericString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(ub_country_name_numeric_length,
                                                       ub_country_name_numeric_length))),
        namedtype.NamedType('iso-3166-alpha2-code', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(ub_country_name_alpha_length, ub_country_name_alpha_length)))
    )


class PDSName(char.PrintableString):
    subtypeSpec = char.PrintableString.subtypeSpec + constraint.ValueSizeConstraint(1, ub_pds_name_length)


physical_delivery_country_name = univ.Integer(8)


class TeletexOrganizationalUnitName(char.TeletexString):
    subtypeSpec = char.TeletexString.subtypeSpec + constraint.ValueSizeConstraint(1, ub_organizational_unit_name_length)


pds_name = univ.Integer(7)

teletex_organizational_unit_names = univ.Integer(5)


class TeletexOrganizationalUnitNames(univ.SequenceOf):
    componentType = TeletexOrganizationalUnitName()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, ub_organizational_units)


teletex_personal_name = univ.Integer(4)


class TeletexPersonalName(univ.Set):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('surname', char.TeletexString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_surname_length),
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('given-name', char.TeletexString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_given_name_length),
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('initials', char.TeletexString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_initials_length),
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.OptionalNamedType('generation-qualifier', char.TeletexString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_generation_qualifier_length),
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
    )


teletex_organization_name = univ.Integer(3)


class TeletexOrganizationName(char.TeletexString):
    subtypeSpec = char.TeletexString.subtypeSpec + constraint.ValueSizeConstraint(1, ub_organization_name_length)


teletex_common_name = univ.Integer(2)


class TeletexCommonName(char.TeletexString):
    subtypeSpec = char.TeletexString.subtypeSpec + constraint.ValueSizeConstraint(1, ub_common_name_length)


class CommonName(char.PrintableString):
    subtypeSpec = char.PrintableString.subtypeSpec + constraint.ValueSizeConstraint(1, ub_common_name_length)


common_name = univ.Integer(1)


class ExtensionAttribute(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('extension-attribute-type', univ.Integer().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(0, ub_extension_attributes),
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('extension-attribute-value',
                            univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class ExtensionAttributes(univ.SetOf):
    componentType = ExtensionAttribute()
    sizeSpec = univ.SetOf.sizeSpec + constraint.ValueSizeConstraint(1, ub_extension_attributes)


class BuiltInDomainDefinedAttribute(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_defined_attribute_type_length))),
        namedtype.NamedType('value', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_defined_attribute_value_length)))
    )


class BuiltInDomainDefinedAttributes(univ.SequenceOf):
    componentType = BuiltInDomainDefinedAttribute()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, ub_domain_defined_attributes)


class OrganizationalUnitName(char.PrintableString):
    subtypeSpec = char.PrintableString.subtypeSpec + constraint.ValueSizeConstraint(1, ub_organizational_unit_name_length)


class OrganizationalUnitNames(univ.SequenceOf):
    componentType = OrganizationalUnitName()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, ub_organizational_units)


class PersonalName(univ.Set):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('surname', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_surname_length),
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('given-name', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_given_name_length),
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('initials', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_initials_length),
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.OptionalNamedType('generation-qualifier', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_generation_qualifier_length),
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
    )


class NumericUserIdentifier(char.NumericString):
    subtypeSpec = char.NumericString.subtypeSpec + constraint.ValueSizeConstraint(1, ub_numeric_user_id_length)


class OrganizationName(char.PrintableString):
    subtypeSpec = char.PrintableString.subtypeSpec + constraint.ValueSizeConstraint(1, ub_organization_name_length)


class PrivateDomainName(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('numeric', char.NumericString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_name_length))),
        namedtype.NamedType('printable', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_name_length)))
    )


class TerminalIdentifier(char.PrintableString):
    subtypeSpec = char.PrintableString.subtypeSpec + constraint.ValueSizeConstraint(1, ub_terminal_id_length)


class X121Address(char.NumericString):
    subtypeSpec = char.NumericString.subtypeSpec + constraint.ValueSizeConstraint(1, ub_x121_address_length)


class NetworkAddress(X121Address):
    pass


class AdministrationDomainName(univ.Choice):
    tagSet = univ.Choice.tagSet.tagExplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 2)
    )
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('numeric', char.NumericString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(0, ub_domain_name_length))),
        namedtype.NamedType('printable', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(0, ub_domain_name_length)))
    )


class CountryName(univ.Choice):
    tagSet = univ.Choice.tagSet.tagExplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 1)
    )
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('x121-dcc-code', char.NumericString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(ub_country_name_numeric_length,
                                                       ub_country_name_numeric_length))),
        namedtype.NamedType('iso-3166-alpha2-code', char.PrintableString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(ub_country_name_alpha_length, ub_country_name_alpha_length)))
    )


class BuiltInStandardAttributes(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('country-name', CountryName()),
        namedtype.OptionalNamedType('administration-domain-name', AdministrationDomainName()),
        namedtype.OptionalNamedType('network-address', NetworkAddress().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('terminal-identifier', TerminalIdentifier().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('private-domain-name', PrivateDomainName().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.OptionalNamedType('organization-name', OrganizationName().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
        namedtype.OptionalNamedType('numeric-user-identifier', NumericUserIdentifier().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))),
        namedtype.OptionalNamedType('personal-name', PersonalName().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 5))),
        namedtype.OptionalNamedType('organizational-unit-names', OrganizationalUnitNames().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 6)))
    )


class ORAddress(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('built-in-standard-attributes', BuiltInStandardAttributes()),
        namedtype.OptionalNamedType('built-in-domain-defined-attributes', BuiltInDomainDefinedAttributes()),
        namedtype.OptionalNamedType('extension-attributes', ExtensionAttributes())
    )


#
# PKIX1Implicit88
#

id_ce_invalidityDate = univ.ObjectIdentifier('2.5.29.24')


class InvalidityDate(useful.GeneralizedTime):
    pass


id_holdinstruction_none = univ.ObjectIdentifier('2.2.840.10040.2.1')
id_holdinstruction_callissuer = univ.ObjectIdentifier('2.2.840.10040.2.2')
id_holdinstruction_reject = univ.ObjectIdentifier('2.2.840.10040.2.3')

holdInstruction = univ.ObjectIdentifier('2.2.840.10040.2')

id_ce_holdInstructionCode = univ.ObjectIdentifier('2.5.29.23')


class HoldInstructionCode(univ.ObjectIdentifier):
    pass


id_ce_cRLReasons = univ.ObjectIdentifier('2.5.29.21')


class CRLReason(univ.Enumerated):
    namedValues = namedval.NamedValues(
        ('unspecified', 0),
        ('keyCompromise', 1),
        ('cACompromise', 2),
        ('affiliationChanged', 3),
        ('superseded', 4),
        ('cessationOfOperation', 5),
        ('certificateHold', 6),
        ('removeFromCRL', 8)
    )


id_ce_cRLNumber = univ.ObjectIdentifier('2.5.29.20')


class CRLNumber(univ.Integer):
    subtypeSpec = univ.Integer.subtypeSpec + constraint.ValueSizeConstraint(0, MAX)


class BaseCRLNumber(CRLNumber):
    pass


id_kp_serverAuth = univ.ObjectIdentifier('1.3.6.1.5.5.7.3.1')
id_kp_clientAuth = univ.ObjectIdentifier('1.3.6.1.5.5.7.3.2')
id_kp_codeSigning = univ.ObjectIdentifier('1.3.6.1.5.5.7.3.3')
id_kp_emailProtection = univ.ObjectIdentifier('1.3.6.1.5.5.7.3.4')
id_kp_ipsecEndSystem = univ.ObjectIdentifier('1.3.6.1.5.5.7.3.5')
id_kp_ipsecTunnel = univ.ObjectIdentifier('1.3.6.1.5.5.7.3.6')
id_kp_ipsecUser = univ.ObjectIdentifier('1.3.6.1.5.5.7.3.7')
id_kp_timeStamping = univ.ObjectIdentifier('1.3.6.1.5.5.7.3.8')
id_pe_authorityInfoAccess = univ.ObjectIdentifier('1.3.6.1.5.5.7.1.1')
id_ce_extKeyUsage = univ.ObjectIdentifier('2.5.29.37')


class KeyPurposeId(univ.ObjectIdentifier):
    pass


class ExtKeyUsageSyntax(univ.SequenceOf):
    componentType = KeyPurposeId()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


class ReasonFlags(univ.BitString):
    namedValues = namedval.NamedValues(
        ('unused', 0),
        ('keyCompromise', 1),
        ('cACompromise', 2),
        ('affiliationChanged', 3),
        ('superseded', 4),
        ('cessationOfOperation', 5),
        ('certificateHold', 6)
    )


class SkipCerts(univ.Integer):
    subtypeSpec = univ.Integer.subtypeSpec + constraint.ValueSizeConstraint(0, MAX)


id_ce_policyConstraints = univ.ObjectIdentifier('2.5.29.36')


class PolicyConstraints(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('requireExplicitPolicy', SkipCerts().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.OptionalNamedType('inhibitPolicyMapping', SkipCerts().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
    )


id_ce_basicConstraints = univ.ObjectIdentifier('2.5.29.19')


class BasicConstraints(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.DefaultedNamedType('cA', univ.Boolean(False)),
        namedtype.OptionalNamedType('pathLenConstraint',
                                    univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, MAX)))
    )


id_ce_subjectDirectoryAttributes = univ.ObjectIdentifier('2.5.29.9')


class EDIPartyName(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('nameAssigner', DirectoryString().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('partyName',
                            DirectoryString().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    )



id_ce_deltaCRLIndicator = univ.ObjectIdentifier('2.5.29.27')



class BaseDistance(univ.Integer):
    subtypeSpec = univ.Integer.subtypeSpec + constraint.ValueRangeConstraint(0, MAX)


id_ce_cRLDistributionPoints = univ.ObjectIdentifier('2.5.29.31')


id_ce_issuingDistributionPoint = univ.ObjectIdentifier('2.5.29.28')




id_ce_nameConstraints = univ.ObjectIdentifier('2.5.29.30')


class DisplayText(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('visibleString',
                            char.VisibleString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 200))),
        namedtype.NamedType('bmpString', char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 200))),
        namedtype.NamedType('utf8String', char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 200)))
    )


class NoticeReference(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('organization', DisplayText()),
        namedtype.NamedType('noticeNumbers', univ.SequenceOf(componentType=univ.Integer()))
    )


class UserNotice(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('noticeRef', NoticeReference()),
        namedtype.OptionalNamedType('explicitText', DisplayText())
    )


class CPSuri(char.IA5String):
    pass


class PolicyQualifierId(univ.ObjectIdentifier):
    subtypeSpec = univ.ObjectIdentifier.subtypeSpec + constraint.SingleValueConstraint(id_qt_cps, id_qt_unotice)


class CertPolicyId(univ.ObjectIdentifier):
    pass


class PolicyQualifierInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('policyQualifierId', PolicyQualifierId()),
        namedtype.NamedType('qualifier', univ.Any())
    )


id_ce_certificatePolicies = univ.ObjectIdentifier('2.5.29.32')


class PolicyInformation(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('policyIdentifier', CertPolicyId()),
        namedtype.OptionalNamedType('policyQualifiers', univ.SequenceOf(componentType=PolicyQualifierInfo()).subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, MAX)))
    )


class CertificatePolicies(univ.SequenceOf):
    componentType = PolicyInformation()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


id_ce_policyMappings = univ.ObjectIdentifier('2.5.29.33')


class PolicyMapping(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('issuerDomainPolicy', CertPolicyId()),
        namedtype.NamedType('subjectDomainPolicy', CertPolicyId())
    )


class PolicyMappings(univ.SequenceOf):
    componentType = PolicyMapping()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


id_ce_privateKeyUsagePeriod = univ.ObjectIdentifier('2.5.29.16')


class PrivateKeyUsagePeriod(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('notBefore', useful.GeneralizedTime().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('notAfter', useful.GeneralizedTime().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


id_ce_keyUsage = univ.ObjectIdentifier('2.5.29.15')


class KeyUsage(univ.BitString):
    namedValues = namedval.NamedValues(
        ('digitalSignature', 0),
        ('nonRepudiation', 1),
        ('keyEncipherment', 2),
        ('dataEncipherment', 3),
        ('keyAgreement', 4),
        ('keyCertSign', 5),
        ('cRLSign', 6),
        ('encipherOnly', 7),
        ('decipherOnly', 8)
    )


id_ce = univ.ObjectIdentifier('2.5.29')

id_ce_authorityKeyIdentifier = univ.ObjectIdentifier('2.5.29.35')


class KeyIdentifier(univ.OctetString):
    pass


id_ce_subjectKeyIdentifier = univ.ObjectIdentifier('2.5.29.14')


class SubjectKeyIdentifier(KeyIdentifier):
    pass


id_ce_certificateIssuer = univ.ObjectIdentifier('2.5.29.29')


id_ce_subjectAltName = univ.ObjectIdentifier('2.5.29.17')


id_ce_issuerAltName = univ.ObjectIdentifier('2.5.29.18')


class AttributeValue(univ.Any):
    pass


class AttributeType(univ.ObjectIdentifier):
    pass

certificateAttributesMap = {}


class AttributeTypeAndValue(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type', AttributeType()),
        namedtype.NamedType('value', AttributeValue(),
                            openType=opentype.OpenType('type', certificateAttributesMap))
    )


class Attribute(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type', AttributeType()),
        namedtype.NamedType('vals', univ.SetOf(componentType=AttributeValue()))
    )


class SubjectDirectoryAttributes(univ.SequenceOf):
    componentType = Attribute()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


class RelativeDistinguishedName(univ.SetOf):
    componentType = AttributeTypeAndValue()


class RDNSequence(univ.SequenceOf):
    componentType = RelativeDistinguishedName()


class Name(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('', RDNSequence())
    )

class CertificateSerialNumber(univ.Integer):
    pass


class AnotherName(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type-id', univ.ObjectIdentifier()),
        namedtype.NamedType('value',
                            univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
    )


class GeneralName(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('otherName',
                            AnotherName().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('rfc822Name',
                            char.IA5String().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.NamedType('dNSName',
                            char.IA5String().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.NamedType('x400Address',
                            ORAddress().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
        namedtype.NamedType('directoryName',
                            Name().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))),
        namedtype.NamedType('ediPartyName',
                            EDIPartyName().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 5))),
        namedtype.NamedType('uniformResourceIdentifier',
                            char.IA5String().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 6))),
        namedtype.NamedType('iPAddress', univ.OctetString().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 7))),
        namedtype.NamedType('registeredID', univ.ObjectIdentifier().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 8)))
    )


class GeneralNames(univ.SequenceOf):
    componentType = GeneralName()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


class AccessDescription(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('accessMethod', univ.ObjectIdentifier()),
        namedtype.NamedType('accessLocation', GeneralName())
    )


class AuthorityInfoAccessSyntax(univ.SequenceOf):
    componentType = AccessDescription()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


class AuthorityKeyIdentifier(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('keyIdentifier', KeyIdentifier().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('authorityCertIssuer', GeneralNames().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('authorityCertSerialNumber', CertificateSerialNumber().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


class DistributionPointName(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('fullName', GeneralNames().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.NamedType('nameRelativeToCRLIssuer', RelativeDistinguishedName().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
    )


class DistributionPoint(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('distributionPoint', DistributionPointName().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.OptionalNamedType('reasons', ReasonFlags().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('cRLIssuer', GeneralNames().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2)))
    )


class CRLDistPointsSyntax(univ.SequenceOf):
    componentType = DistributionPoint()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


class IssuingDistributionPoint(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('distributionPoint', DistributionPointName().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.NamedType('onlyContainsUserCerts', univ.Boolean(False).subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.NamedType('onlyContainsCACerts', univ.Boolean(False).subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.OptionalNamedType('onlySomeReasons', ReasonFlags().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
        namedtype.NamedType('indirectCRL', univ.Boolean(False).subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4)))
    )


class GeneralSubtree(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('base', GeneralName()),
        namedtype.DefaultedNamedType('minimum', BaseDistance(0).subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.OptionalNamedType('maximum', BaseDistance().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
    )


class GeneralSubtrees(univ.SequenceOf):
    componentType = GeneralSubtree()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


class NameConstraints(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('permittedSubtrees', GeneralSubtrees().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.OptionalNamedType('excludedSubtrees', GeneralSubtrees().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
    )


class CertificateIssuer(GeneralNames):
    pass


class SubjectAltName(GeneralNames):
    pass


class IssuerAltName(GeneralNames):
    pass


certificateExtensionsMap = {}


class Extension(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('extnID', univ.ObjectIdentifier()),
        namedtype.DefaultedNamedType('critical', univ.Boolean('False')),
        namedtype.NamedType('extnValue', univ.OctetString(),
                            openType=opentype.OpenType('extnID', certificateExtensionsMap))
    )


class Extensions(univ.SequenceOf):
    componentType = Extension()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


class SubjectPublicKeyInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('algorithm', AlgorithmIdentifier()),
        namedtype.NamedType('subjectPublicKey', univ.BitString())
    )


class UniqueIdentifier(univ.BitString):
    pass


class Time(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('utcTime', useful.UTCTime()),
        namedtype.NamedType('generalTime', useful.GeneralizedTime())
    )


class Validity(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('notBefore', Time()),
        namedtype.NamedType('notAfter', Time())
    )


class Version(univ.Integer):
    namedValues = namedval.NamedValues(
        ('v1', 0), ('v2', 1), ('v3', 2)
    )


class TBSCertificate(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.DefaultedNamedType('version', Version('v1').subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('serialNumber', CertificateSerialNumber()),
        namedtype.NamedType('signature', AlgorithmIdentifier()),
        namedtype.NamedType('issuer', Name()),
        namedtype.NamedType('validity', Validity()),
        namedtype.NamedType('subject', Name()),
        namedtype.NamedType('subjectPublicKeyInfo', SubjectPublicKeyInfo()),
        namedtype.OptionalNamedType('issuerUniqueID', UniqueIdentifier().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('subjectUniqueID', UniqueIdentifier().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.OptionalNamedType('extensions', Extensions().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
    )


class Certificate(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('tbsCertificate', TBSCertificate()),
        namedtype.NamedType('signatureAlgorithm', AlgorithmIdentifier()),
        namedtype.NamedType('signatureValue', univ.BitString())
    )

# CRL structures

class RevokedCertificate(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('userCertificate', CertificateSerialNumber()),
        namedtype.NamedType('revocationDate', Time()),
        namedtype.OptionalNamedType('crlEntryExtensions', Extensions())
    )


class TBSCertList(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('version', Version()),
        namedtype.NamedType('signature', AlgorithmIdentifier()),
        namedtype.NamedType('issuer', Name()),
        namedtype.NamedType('thisUpdate', Time()),
        namedtype.OptionalNamedType('nextUpdate', Time()),
        namedtype.OptionalNamedType('revokedCertificates', univ.SequenceOf(componentType=RevokedCertificate())),
        namedtype.OptionalNamedType('crlExtensions', Extensions().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)))
    )


class CertificateList(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('tbsCertList', TBSCertList()),
        namedtype.NamedType('signatureAlgorithm', AlgorithmIdentifier()),
        namedtype.NamedType('signature', univ.BitString())
    )

# map of AttributeType -> AttributeValue

_certificateAttributesMapUpdate = {
    id_at_name: X520name(),
    id_at_surname: X520name(),
    id_at_givenName: X520name(),
    id_at_initials: X520name(),
    id_at_generationQualifier: X520name(),
    id_at_commonName: X520CommonName(),
    id_at_localityName: X520LocalityName(),
    id_at_stateOrProvinceName: X520StateOrProvinceName(),
    id_at_organizationName: X520OrganizationName(),
    id_at_organizationalUnitName: X520OrganizationalUnitName(),
    id_at_title: X520Title(),
    id_at_dnQualifier: X520dnQualifier(),
    id_at_countryName: X520countryName(),
    emailAddress: Pkcs9email(),
}

certificateAttributesMap.update(_certificateAttributesMapUpdate)


# map of Certificate Extension OIDs to Extensions

_certificateExtensionsMapUpdate = {
    id_ce_authorityKeyIdentifier: AuthorityKeyIdentifier(),
    id_ce_subjectKeyIdentifier: SubjectKeyIdentifier(),
    id_ce_keyUsage: KeyUsage(),
    id_ce_privateKeyUsagePeriod: PrivateKeyUsagePeriod(),
    id_ce_certificatePolicies: CertificatePolicies(),
    id_ce_policyMappings: PolicyMappings(),
    id_ce_subjectAltName: SubjectAltName(),
    id_ce_issuerAltName: IssuerAltName(),
    id_ce_subjectDirectoryAttributes: SubjectDirectoryAttributes(),
    id_ce_basicConstraints: BasicConstraints(),
    id_ce_nameConstraints: NameConstraints(),
    id_ce_policyConstraints: PolicyConstraints(),
    id_ce_extKeyUsage: ExtKeyUsageSyntax(),
    id_ce_cRLDistributionPoints: CRLDistPointsSyntax(),
    id_pe_authorityInfoAccess: AuthorityInfoAccessSyntax(),
    id_ce_cRLNumber: univ.Integer(),
    id_ce_deltaCRLIndicator: BaseCRLNumber(),
    id_ce_issuingDistributionPoint: IssuingDistributionPoint(),
    id_ce_cRLReasons: CRLReason(),
    id_ce_holdInstructionCode: univ.ObjectIdentifier(),
    id_ce_invalidityDate: useful.GeneralizedTime(),
    id_ce_certificateIssuer: GeneralNames(),
}

certificateExtensionsMap.update(_certificateExtensionsMapUpdate)


# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_mysql_builtins.py ===
"""
    pygments.lexers._mysql_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Self-updating data files for the MySQL lexer.

    Run with `python -I` to update.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""


MYSQL_CONSTANTS = (
    'false',
    'null',
    'true',
    'unknown',
)


# At this time, no easily-parsed, definitive list of data types
# has been found in the MySQL source code or documentation. (The
# `sql/sql_yacc.yy` file is definitive but is difficult to parse.)
# Therefore these types are currently maintained manually.
#
# Some words in this list -- like "long", "national", "precision",
# and "varying" -- appear to only occur in combination with other
# data type keywords. Therefore they are included as separate words
# even though they do not naturally occur in syntax separately.
#
# This list is also used to strip data types out of the list of
# MySQL keywords, which is automatically updated later in the file.
#
MYSQL_DATATYPES = (
    # Numeric data types
    'bigint',
    'bit',
    'bool',
    'boolean',
    'dec',
    'decimal',
    'double',
    'fixed',
    'float',
    'float4',
    'float8',
    'int',
    'int1',
    'int2',
    'int3',
    'int4',
    'int8',
    'integer',
    'mediumint',
    'middleint',
    'numeric',
    'precision',
    'real',
    'serial',
    'smallint',
    'tinyint',

    # Date and time data types
    'date',
    'datetime',
    'time',
    'timestamp',
    'year',

    # String data types
    'binary',
    'blob',
    'char',
    'enum',
    'long',
    'longblob',
    'longtext',
    'mediumblob',
    'mediumtext',
    'national',
    'nchar',
    'nvarchar',
    'set',
    'text',
    'tinyblob',
    'tinytext',
    'varbinary',
    'varchar',
    'varcharacter',
    'varying',

    # Spatial data types
    'geometry',
    'geometrycollection',
    'linestring',
    'multilinestring',
    'multipoint',
    'multipolygon',
    'point',
    'polygon',

    # JSON data types
    'json',
)

# Everything below this line is auto-generated from the MySQL source code.
# Run this file in Python and it will update itself.
# -----------------------------------------------------------------------------

MYSQL_FUNCTIONS = (
    'abs',
    'acos',
    'adddate',
    'addtime',
    'aes_decrypt',
    'aes_encrypt',
    'any_value',
    'asin',
    'atan',
    'atan2',
    'benchmark',
    'bin',
    'bin_to_uuid',
    'bit_and',
    'bit_count',
    'bit_length',
    'bit_or',
    'bit_xor',
    'can_access_column',
    'can_access_database',
    'can_access_event',
    'can_access_resource_group',
    'can_access_routine',
    'can_access_table',
    'can_access_trigger',
    'can_access_user',
    'can_access_view',
    'cast',
    'ceil',
    'ceiling',
    'char_length',
    'character_length',
    'coercibility',
    'compress',
    'concat',
    'concat_ws',
    'connection_id',
    'conv',
    'convert_cpu_id_mask',
    'convert_interval_to_user_interval',
    'convert_tz',
    'cos',
    'cot',
    'count',
    'crc32',
    'curdate',
    'current_role',
    'curtime',
    'date_add',
    'date_format',
    'date_sub',
    'datediff',
    'dayname',
    'dayofmonth',
    'dayofweek',
    'dayofyear',
    'degrees',
    'elt',
    'exp',
    'export_set',
    'extract',
    'extractvalue',
    'field',
    'find_in_set',
    'floor',
    'format_bytes',
    'format_pico_time',
    'found_rows',
    'from_base64',
    'from_days',
    'from_unixtime',
    'get_dd_column_privileges',
    'get_dd_create_options',
    'get_dd_index_private_data',
    'get_dd_index_sub_part_length',
    'get_dd_property_key_value',
    'get_dd_schema_options',
    'get_dd_tablespace_private_data',
    'get_lock',
    'greatest',
    'group_concat',
    'gtid_subset',
    'gtid_subtract',
    'hex',
    'icu_version',
    'ifnull',
    'inet6_aton',
    'inet6_ntoa',
    'inet_aton',
    'inet_ntoa',
    'instr',
    'internal_auto_increment',
    'internal_avg_row_length',
    'internal_check_time',
    'internal_checksum',
    'internal_data_free',
    'internal_data_length',
    'internal_dd_char_length',
    'internal_get_comment_or_error',
    'internal_get_dd_column_extra',
    'internal_get_enabled_role_json',
    'internal_get_hostname',
    'internal_get_mandatory_roles_json',
    'internal_get_partition_nodegroup',
    'internal_get_username',
    'internal_get_view_warning_or_error',
    'internal_index_column_cardinality',
    'internal_index_length',
    'internal_is_enabled_role',
    'internal_is_mandatory_role',
    'internal_keys_disabled',
    'internal_max_data_length',
    'internal_table_rows',
    'internal_tablespace_autoextend_size',
    'internal_tablespace_data_free',
    'internal_tablespace_extent_size',
    'internal_tablespace_extra',
    'internal_tablespace_free_extents',
    'internal_tablespace_id',
    'internal_tablespace_initial_size',
    'internal_tablespace_logfile_group_name',
    'internal_tablespace_logfile_group_number',
    'internal_tablespace_maximum_size',
    'internal_tablespace_row_format',
    'internal_tablespace_status',
    'internal_tablespace_total_extents',
    'internal_tablespace_type',
    'internal_tablespace_version',
    'internal_update_time',
    'is_free_lock',
    'is_ipv4',
    'is_ipv4_compat',
    'is_ipv4_mapped',
    'is_ipv6',
    'is_used_lock',
    'is_uuid',
    'is_visible_dd_object',
    'isnull',
    'json_array',
    'json_array_append',
    'json_array_insert',
    'json_arrayagg',
    'json_contains',
    'json_contains_path',
    'json_depth',
    'json_extract',
    'json_insert',
    'json_keys',
    'json_length',
    'json_merge',
    'json_merge_patch',
    'json_merge_preserve',
    'json_object',
    'json_objectagg',
    'json_overlaps',
    'json_pretty',
    'json_quote',
    'json_remove',
    'json_replace',
    'json_schema_valid',
    'json_schema_validation_report',
    'json_search',
    'json_set',
    'json_storage_free',
    'json_storage_size',
    'json_type',
    'json_unquote',
    'json_valid',
    'last_day',
    'last_insert_id',
    'lcase',
    'least',
    'length',
    'like_range_max',
    'like_range_min',
    'ln',
    'load_file',
    'locate',
    'log',
    'log10',
    'log2',
    'lower',
    'lpad',
    'ltrim',
    'make_set',
    'makedate',
    'maketime',
    'master_pos_wait',
    'max',
    'mbrcontains',
    'mbrcoveredby',
    'mbrcovers',
    'mbrdisjoint',
    'mbrequals',
    'mbrintersects',
    'mbroverlaps',
    'mbrtouches',
    'mbrwithin',
    'md5',
    'mid',
    'min',
    'monthname',
    'name_const',
    'now',
    'nullif',
    'oct',
    'octet_length',
    'ord',
    'period_add',
    'period_diff',
    'pi',
    'position',
    'pow',
    'power',
    'ps_current_thread_id',
    'ps_thread_id',
    'quote',
    'radians',
    'rand',
    'random_bytes',
    'regexp_instr',
    'regexp_like',
    'regexp_replace',
    'regexp_substr',
    'release_all_locks',
    'release_lock',
    'remove_dd_property_key',
    'reverse',
    'roles_graphml',
    'round',
    'rpad',
    'rtrim',
    'sec_to_time',
    'session_user',
    'sha',
    'sha1',
    'sha2',
    'sign',
    'sin',
    'sleep',
    'soundex',
    'source_pos_wait',
    'space',
    'sqrt',
    'st_area',
    'st_asbinary',
    'st_asgeojson',
    'st_astext',
    'st_aswkb',
    'st_aswkt',
    'st_buffer',
    'st_buffer_strategy',
    'st_centroid',
    'st_collect',
    'st_contains',
    'st_convexhull',
    'st_crosses',
    'st_difference',
    'st_dimension',
    'st_disjoint',
    'st_distance',
    'st_distance_sphere',
    'st_endpoint',
    'st_envelope',
    'st_equals',
    'st_exteriorring',
    'st_frechetdistance',
    'st_geohash',
    'st_geomcollfromtext',
    'st_geomcollfromtxt',
    'st_geomcollfromwkb',
    'st_geometrycollectionfromtext',
    'st_geometrycollectionfromwkb',
    'st_geometryfromtext',
    'st_geometryfromwkb',
    'st_geometryn',
    'st_geometrytype',
    'st_geomfromgeojson',
    'st_geomfromtext',
    'st_geomfromwkb',
    'st_hausdorffdistance',
    'st_interiorringn',
    'st_intersection',
    'st_intersects',
    'st_isclosed',
    'st_isempty',
    'st_issimple',
    'st_isvalid',
    'st_latfromgeohash',
    'st_latitude',
    'st_length',
    'st_linefromtext',
    'st_linefromwkb',
    'st_lineinterpolatepoint',
    'st_lineinterpolatepoints',
    'st_linestringfromtext',
    'st_linestringfromwkb',
    'st_longfromgeohash',
    'st_longitude',
    'st_makeenvelope',
    'st_mlinefromtext',
    'st_mlinefromwkb',
    'st_mpointfromtext',
    'st_mpointfromwkb',
    'st_mpolyfromtext',
    'st_mpolyfromwkb',
    'st_multilinestringfromtext',
    'st_multilinestringfromwkb',
    'st_multipointfromtext',
    'st_multipointfromwkb',
    'st_multipolygonfromtext',
    'st_multipolygonfromwkb',
    'st_numgeometries',
    'st_numinteriorring',
    'st_numinteriorrings',
    'st_numpoints',
    'st_overlaps',
    'st_pointatdistance',
    'st_pointfromgeohash',
    'st_pointfromtext',
    'st_pointfromwkb',
    'st_pointn',
    'st_polyfromtext',
    'st_polyfromwkb',
    'st_polygonfromtext',
    'st_polygonfromwkb',
    'st_simplify',
    'st_srid',
    'st_startpoint',
    'st_swapxy',
    'st_symdifference',
    'st_touches',
    'st_transform',
    'st_union',
    'st_validate',
    'st_within',
    'st_x',
    'st_y',
    'statement_digest',
    'statement_digest_text',
    'std',
    'stddev',
    'stddev_pop',
    'stddev_samp',
    'str_to_date',
    'strcmp',
    'subdate',
    'substr',
    'substring',
    'substring_index',
    'subtime',
    'sum',
    'sysdate',
    'system_user',
    'tan',
    'time_format',
    'time_to_sec',
    'timediff',
    'to_base64',
    'to_days',
    'to_seconds',
    'trim',
    'ucase',
    'uncompress',
    'uncompressed_length',
    'unhex',
    'unix_timestamp',
    'updatexml',
    'upper',
    'uuid',
    'uuid_short',
    'uuid_to_bin',
    'validate_password_strength',
    'var_pop',
    'var_samp',
    'variance',
    'version',
    'wait_for_executed_gtid_set',
    'wait_until_sql_thread_after_gtids',
    'weekday',
    'weekofyear',
    'yearweek',
)


MYSQL_OPTIMIZER_HINTS = (
    'bka',
    'bnl',
    'derived_condition_pushdown',
    'dupsweedout',
    'firstmatch',
    'group_index',
    'hash_join',
    'index',
    'index_merge',
    'intoexists',
    'join_fixed_order',
    'join_index',
    'join_order',
    'join_prefix',
    'join_suffix',
    'loosescan',
    'materialization',
    'max_execution_time',
    'merge',
    'mrr',
    'no_bka',
    'no_bnl',
    'no_derived_condition_pushdown',
    'no_group_index',
    'no_hash_join',
    'no_icp',
    'no_index',
    'no_index_merge',
    'no_join_index',
    'no_merge',
    'no_mrr',
    'no_order_index',
    'no_range_optimization',
    'no_semijoin',
    'no_skip_scan',
    'order_index',
    'qb_name',
    'resource_group',
    'semijoin',
    'set_var',
    'skip_scan',
    'subquery',
)


MYSQL_KEYWORDS = (
    'accessible',
    'account',
    'action',
    'active',
    'add',
    'admin',
    'after',
    'against',
    'aggregate',
    'algorithm',
    'all',
    'alter',
    'always',
    'analyze',
    'and',
    'any',
    'array',
    'as',
    'asc',
    'ascii',
    'asensitive',
    'assign_gtids_to_anonymous_transactions',
    'at',
    'attribute',
    'authentication',
    'auto_increment',
    'autoextend_size',
    'avg',
    'avg_row_length',
    'backup',
    'before',
    'begin',
    'between',
    'binlog',
    'block',
    'both',
    'btree',
    'buckets',
    'by',
    'byte',
    'cache',
    'call',
    'cascade',
    'cascaded',
    'case',
    'catalog_name',
    'chain',
    'challenge_response',
    'change',
    'changed',
    'channel',
    'character',
    'charset',
    'check',
    'checksum',
    'cipher',
    'class_origin',
    'client',
    'clone',
    'close',
    'coalesce',
    'code',
    'collate',
    'collation',
    'column',
    'column_format',
    'column_name',
    'columns',
    'comment',
    'commit',
    'committed',
    'compact',
    'completion',
    'component',
    'compressed',
    'compression',
    'concurrent',
    'condition',
    'connection',
    'consistent',
    'constraint',
    'constraint_catalog',
    'constraint_name',
    'constraint_schema',
    'contains',
    'context',
    'continue',
    'convert',
    'cpu',
    'create',
    'cross',
    'cube',
    'cume_dist',
    'current',
    'current_date',
    'current_time',
    'current_timestamp',
    'current_user',
    'cursor',
    'cursor_name',
    'data',
    'database',
    'databases',
    'datafile',
    'day',
    'day_hour',
    'day_microsecond',
    'day_minute',
    'day_second',
    'deallocate',
    'declare',
    'default',
    'default_auth',
    'definer',
    'definition',
    'delay_key_write',
    'delayed',
    'delete',
    'dense_rank',
    'desc',
    'describe',
    'description',
    'deterministic',
    'diagnostics',
    'directory',
    'disable',
    'discard',
    'disk',
    'distinct',
    'distinctrow',
    'div',
    'do',
    'drop',
    'dual',
    'dumpfile',
    'duplicate',
    'dynamic',
    'each',
    'else',
    'elseif',
    'empty',
    'enable',
    'enclosed',
    'encryption',
    'end',
    'ends',
    'enforced',
    'engine',
    'engine_attribute',
    'engines',
    'error',
    'errors',
    'escape',
    'escaped',
    'event',
    'events',
    'every',
    'except',
    'exchange',
    'exclude',
    'execute',
    'exists',
    'exit',
    'expansion',
    'expire',
    'explain',
    'export',
    'extended',
    'extent_size',
    'factor',
    'failed_login_attempts',
    'false',
    'fast',
    'faults',
    'fetch',
    'fields',
    'file',
    'file_block_size',
    'filter',
    'finish',
    'first',
    'first_value',
    'flush',
    'following',
    'follows',
    'for',
    'force',
    'foreign',
    'format',
    'found',
    'from',
    'full',
    'fulltext',
    'function',
    'general',
    'generated',
    'geomcollection',
    'get',
    'get_format',
    'get_master_public_key',
    'get_source_public_key',
    'global',
    'grant',
    'grants',
    'group',
    'group_replication',
    'grouping',
    'groups',
    'gtid_only',
    'handler',
    'hash',
    'having',
    'help',
    'high_priority',
    'histogram',
    'history',
    'host',
    'hosts',
    'hour',
    'hour_microsecond',
    'hour_minute',
    'hour_second',
    'identified',
    'if',
    'ignore',
    'ignore_server_ids',
    'import',
    'in',
    'inactive',
    'index',
    'indexes',
    'infile',
    'initial',
    'initial_size',
    'initiate',
    'inner',
    'inout',
    'insensitive',
    'insert',
    'insert_method',
    'install',
    'instance',
    'interval',
    'into',
    'invisible',
    'invoker',
    'io',
    'io_after_gtids',
    'io_before_gtids',
    'io_thread',
    'ipc',
    'is',
    'isolation',
    'issuer',
    'iterate',
    'join',
    'json_table',
    'json_value',
    'key',
    'key_block_size',
    'keyring',
    'keys',
    'kill',
    'lag',
    'language',
    'last',
    'last_value',
    'lateral',
    'lead',
    'leading',
    'leave',
    'leaves',
    'left',
    'less',
    'level',
    'like',
    'limit',
    'linear',
    'lines',
    'list',
    'load',
    'local',
    'localtime',
    'localtimestamp',
    'lock',
    'locked',
    'locks',
    'logfile',
    'logs',
    'loop',
    'low_priority',
    'master',
    'master_auto_position',
    'master_bind',
    'master_compression_algorithms',
    'master_connect_retry',
    'master_delay',
    'master_heartbeat_period',
    'master_host',
    'master_log_file',
    'master_log_pos',
    'master_password',
    'master_port',
    'master_public_key_path',
    'master_retry_count',
    'master_ssl',
    'master_ssl_ca',
    'master_ssl_capath',
    'master_ssl_cert',
    'master_ssl_cipher',
    'master_ssl_crl',
    'master_ssl_crlpath',
    'master_ssl_key',
    'master_ssl_verify_server_cert',
    'master_tls_ciphersuites',
    'master_tls_version',
    'master_user',
    'master_zstd_compression_level',
    'match',
    'max_connections_per_hour',
    'max_queries_per_hour',
    'max_rows',
    'max_size',
    'max_updates_per_hour',
    'max_user_connections',
    'maxvalue',
    'medium',
    'member',
    'memory',
    'merge',
    'message_text',
    'microsecond',
    'migrate',
    'min_rows',
    'minute',
    'minute_microsecond',
    'minute_second',
    'mod',
    'mode',
    'modifies',
    'modify',
    'month',
    'mutex',
    'mysql_errno',
    'name',
    'names',
    'natural',
    'ndb',
    'ndbcluster',
    'nested',
    'network_namespace',
    'never',
    'new',
    'next',
    'no',
    'no_wait',
    'no_write_to_binlog',
    'nodegroup',
    'none',
    'not',
    'nowait',
    'nth_value',
    'ntile',
    'null',
    'nulls',
    'number',
    'of',
    'off',
    'offset',
    'oj',
    'old',
    'on',
    'one',
    'only',
    'open',
    'optimize',
    'optimizer_costs',
    'option',
    'optional',
    'optionally',
    'options',
    'or',
    'order',
    'ordinality',
    'organization',
    'others',
    'out',
    'outer',
    'outfile',
    'over',
    'owner',
    'pack_keys',
    'page',
    'parser',
    'partial',
    'partition',
    'partitioning',
    'partitions',
    'password',
    'password_lock_time',
    'path',
    'percent_rank',
    'persist',
    'persist_only',
    'phase',
    'plugin',
    'plugin_dir',
    'plugins',
    'port',
    'precedes',
    'preceding',
    'prepare',
    'preserve',
    'prev',
    'primary',
    'privilege_checks_user',
    'privileges',
    'procedure',
    'process',
    'processlist',
    'profile',
    'profiles',
    'proxy',
    'purge',
    'quarter',
    'query',
    'quick',
    'random',
    'range',
    'rank',
    'read',
    'read_only',
    'read_write',
    'reads',
    'rebuild',
    'recover',
    'recursive',
    'redo_buffer_size',
    'redundant',
    'reference',
    'references',
    'regexp',
    'registration',
    'relay',
    'relay_log_file',
    'relay_log_pos',
    'relay_thread',
    'relaylog',
    'release',
    'reload',
    'remove',
    'rename',
    'reorganize',
    'repair',
    'repeat',
    'repeatable',
    'replace',
    'replica',
    'replicas',
    'replicate_do_db',
    'replicate_do_table',
    'replicate_ignore_db',
    'replicate_ignore_table',
    'replicate_rewrite_db',
    'replicate_wild_do_table',
    'replicate_wild_ignore_table',
    'replication',
    'require',
    'require_row_format',
    'require_table_primary_key_check',
    'reset',
    'resignal',
    'resource',
    'respect',
    'restart',
    'restore',
    'restrict',
    'resume',
    'retain',
    'return',
    'returned_sqlstate',
    'returning',
    'returns',
    'reuse',
    'reverse',
    'revoke',
    'right',
    'rlike',
    'role',
    'rollback',
    'rollup',
    'rotate',
    'routine',
    'row',
    'row_count',
    'row_format',
    'row_number',
    'rows',
    'rtree',
    'savepoint',
    'schedule',
    'schema',
    'schema_name',
    'schemas',
    'second',
    'second_microsecond',
    'secondary',
    'secondary_engine',
    'secondary_engine_attribute',
    'secondary_load',
    'secondary_unload',
    'security',
    'select',
    'sensitive',
    'separator',
    'serializable',
    'server',
    'session',
    'share',
    'show',
    'shutdown',
    'signal',
    'signed',
    'simple',
    'skip',
    'slave',
    'slow',
    'snapshot',
    'socket',
    'some',
    'soname',
    'sounds',
    'source',
    'source_auto_position',
    'source_bind',
    'source_compression_algorithms',
    'source_connect_retry',
    'source_connection_auto_failover',
    'source_delay',
    'source_heartbeat_period',
    'source_host',
    'source_log_file',
    'source_log_pos',
    'source_password',
    'source_port',
    'source_public_key_path',
    'source_retry_count',
    'source_ssl',
    'source_ssl_ca',
    'source_ssl_capath',
    'source_ssl_cert',
    'source_ssl_cipher',
    'source_ssl_crl',
    'source_ssl_crlpath',
    'source_ssl_key',
    'source_ssl_verify_server_cert',
    'source_tls_ciphersuites',
    'source_tls_version',
    'source_user',
    'source_zstd_compression_level',
    'spatial',
    'specific',
    'sql',
    'sql_after_gtids',
    'sql_after_mts_gaps',
    'sql_before_gtids',
    'sql_big_result',
    'sql_buffer_result',
    'sql_calc_found_rows',
    'sql_no_cache',
    'sql_small_result',
    'sql_thread',
    'sql_tsi_day',
    'sql_tsi_hour',
    'sql_tsi_minute',
    'sql_tsi_month',
    'sql_tsi_quarter',
    'sql_tsi_second',
    'sql_tsi_week',
    'sql_tsi_year',
    'sqlexception',
    'sqlstate',
    'sqlwarning',
    'srid',
    'ssl',
    'stacked',
    'start',
    'starting',
    'starts',
    'stats_auto_recalc',
    'stats_persistent',
    'stats_sample_pages',
    'status',
    'stop',
    'storage',
    'stored',
    'straight_join',
    'stream',
    'string',
    'subclass_origin',
    'subject',
    'subpartition',
    'subpartitions',
    'super',
    'suspend',
    'swaps',
    'switches',
    'system',
    'table',
    'table_checksum',
    'table_name',
    'tables',
    'tablespace',
    'temporary',
    'temptable',
    'terminated',
    'than',
    'then',
    'thread_priority',
    'ties',
    'timestampadd',
    'timestampdiff',
    'tls',
    'to',
    'trailing',
    'transaction',
    'trigger',
    'triggers',
    'true',
    'truncate',
    'type',
    'types',
    'unbounded',
    'uncommitted',
    'undefined',
    'undo',
    'undo_buffer_size',
    'undofile',
    'unicode',
    'uninstall',
    'union',
    'unique',
    'unknown',
    'unlock',
    'unregister',
    'unsigned',
    'until',
    'update',
    'upgrade',
    'usage',
    'use',
    'use_frm',
    'user',
    'user_resources',
    'using',
    'utc_date',
    'utc_time',
    'utc_timestamp',
    'validation',
    'value',
    'values',
    'variables',
    'vcpu',
    'view',
    'virtual',
    'visible',
    'wait',
    'warnings',
    'week',
    'weight_string',
    'when',
    'where',
    'while',
    'window',
    'with',
    'without',
    'work',
    'wrapper',
    'write',
    'x509',
    'xa',
    'xid',
    'xml',
    'xor',
    'year_month',
    'zerofill',
    'zone',
)


if __name__ == '__main__':  # pragma: no cover
    import re
    from urllib.request import urlopen

    from pygments.util import format_lines

    # MySQL source code
    SOURCE_URL = 'https://github.com/mysql/mysql-server/raw/8.0'
    LEX_URL = SOURCE_URL + '/sql/lex.h'
    ITEM_CREATE_URL = SOURCE_URL + '/sql/item_create.cc'


    def update_myself():
        # Pull content from lex.h.
        lex_file = urlopen(LEX_URL).read().decode('utf8', errors='ignore')
        keywords = parse_lex_keywords(lex_file)
        functions = parse_lex_functions(lex_file)
        optimizer_hints = parse_lex_optimizer_hints(lex_file)

        # Parse content in item_create.cc.
        item_create_file = urlopen(ITEM_CREATE_URL).read().decode('utf8', errors='ignore')
        functions.update(parse_item_create_functions(item_create_file))

        # Remove data types from the set of keywords.
        keywords -= set(MYSQL_DATATYPES)

        update_content('MYSQL_FUNCTIONS', tuple(sorted(functions)))
        update_content('MYSQL_KEYWORDS', tuple(sorted(keywords)))
        update_content('MYSQL_OPTIMIZER_HINTS', tuple(sorted(optimizer_hints)))


    def parse_lex_keywords(f):
        """Parse keywords in lex.h."""

        results = set()
        for m in re.finditer(r'{SYM(?:_HK)?\("(?P<keyword>[a-z0-9_]+)",', f, flags=re.I):
            results.add(m.group('keyword').lower())

        if not results:
            raise ValueError('No keywords found')

        return results


    def parse_lex_optimizer_hints(f):
        """Parse optimizer hints in lex.h."""

        results = set()
        for m in re.finditer(r'{SYM_H\("(?P<keyword>[a-z0-9_]+)",', f, flags=re.I):
            results.add(m.group('keyword').lower())

        if not results:
            raise ValueError('No optimizer hints found')

        return results


    def parse_lex_functions(f):
        """Parse MySQL function names from lex.h."""

        results = set()
        for m in re.finditer(r'{SYM_FN?\("(?P<function>[a-z0-9_]+)",', f, flags=re.I):
            results.add(m.group('function').lower())

        if not results:
            raise ValueError('No lex functions found')

        return results


    def parse_item_create_functions(f):
        """Parse MySQL function names from item_create.cc."""

        results = set()
        for m in re.finditer(r'{"(?P<function>[^"]+?)",\s*SQL_F[^(]+?\(', f, flags=re.I):
            results.add(m.group('function').lower())

        if not results:
            raise ValueError('No item_create functions found')

        return results


    def update_content(field_name, content):
        """Overwrite this file with content parsed from MySQL's source code."""

        with open(__file__, encoding="utf-8") as f:
            data = f.read()

        # Line to start/end inserting
        re_match = re.compile(rf'^{field_name}\s*=\s*\($.*?^\s*\)$', re.M | re.S)
        m = re_match.search(data)
        if not m:
            raise ValueError(f'Could not find an existing definition for {field_name}')

        new_block = format_lines(field_name, content)
        data = data[:m.start()] + new_block + data[m.end():]

        with open(__file__, 'w', encoding='utf-8', newline='\n') as f:
            f.write(data)

    update_myself()