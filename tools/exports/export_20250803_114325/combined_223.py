
# === NexusCore/openenv\Lib\site-packages\cffi\setuptools_ext.py ===
import os
import sys

try:
    basestring
except NameError:
    # Python 3.x
    basestring = str

def error(msg):
    from cffi._shimmed_dist_utils import DistutilsSetupError
    raise DistutilsSetupError(msg)


def execfile(filename, glob):
    # We use execfile() (here rewritten for Python 3) instead of
    # __import__() to load the build script.  The problem with
    # a normal import is that in some packages, the intermediate
    # __init__.py files may already try to import the file that
    # we are generating.
    with open(filename) as f:
        src = f.read()
    src += '\n'      # Python 2.6 compatibility
    code = compile(src, filename, 'exec')
    exec(code, glob, glob)


def add_cffi_module(dist, mod_spec):
    from cffi.api import FFI

    if not isinstance(mod_spec, basestring):
        error("argument to 'cffi_modules=...' must be a str or a list of str,"
              " not %r" % (type(mod_spec).__name__,))
    mod_spec = str(mod_spec)
    try:
        build_file_name, ffi_var_name = mod_spec.split(':')
    except ValueError:
        error("%r must be of the form 'path/build.py:ffi_variable'" %
              (mod_spec,))
    if not os.path.exists(build_file_name):
        ext = ''
        rewritten = build_file_name.replace('.', '/') + '.py'
        if os.path.exists(rewritten):
            ext = ' (rewrite cffi_modules to [%r])' % (
                rewritten + ':' + ffi_var_name,)
        error("%r does not name an existing file%s" % (build_file_name, ext))

    mod_vars = {'__name__': '__cffi__', '__file__': build_file_name}
    execfile(build_file_name, mod_vars)

    try:
        ffi = mod_vars[ffi_var_name]
    except KeyError:
        error("%r: object %r not found in module" % (mod_spec,
                                                     ffi_var_name))
    if not isinstance(ffi, FFI):
        ffi = ffi()      # maybe it's a function instead of directly an ffi
    if not isinstance(ffi, FFI):
        error("%r is not an FFI instance (got %r)" % (mod_spec,
                                                      type(ffi).__name__))
    if not hasattr(ffi, '_assigned_source'):
        error("%r: the set_source() method was not called" % (mod_spec,))
    module_name, source, source_extension, kwds = ffi._assigned_source
    if ffi._windows_unicode:
        kwds = kwds.copy()
        ffi._apply_windows_unicode(kwds)

    if source is None:
        _add_py_module(dist, ffi, module_name)
    else:
        _add_c_module(dist, ffi, module_name, source, source_extension, kwds)

def _set_py_limited_api(Extension, kwds):
    """
    Add py_limited_api to kwds if setuptools >= 26 is in use.
    Do not alter the setting if it already exists.
    Setuptools takes care of ignoring the flag on Python 2 and PyPy.

    CPython itself should ignore the flag in a debugging version
    (by not listing .abi3.so in the extensions it supports), but
    it doesn't so far, creating troubles.  That's why we check
    for "not hasattr(sys, 'gettotalrefcount')" (the 2.7 compatible equivalent
    of 'd' not in sys.abiflags). (http://bugs.python.org/issue28401)

    On Windows, with CPython <= 3.4, it's better not to use py_limited_api
    because virtualenv *still* doesn't copy PYTHON3.DLL on these versions.
    Recently (2020) we started shipping only >= 3.5 wheels, though.  So
    we'll give it another try and set py_limited_api on Windows >= 3.5.
    """
    from cffi import recompiler

    if ('py_limited_api' not in kwds and not hasattr(sys, 'gettotalrefcount')
            and recompiler.USE_LIMITED_API):
        import setuptools
        try:
            setuptools_major_version = int(setuptools.__version__.partition('.')[0])
            if setuptools_major_version >= 26:
                kwds['py_limited_api'] = True
        except ValueError:  # certain development versions of setuptools
            # If we don't know the version number of setuptools, we
            # try to set 'py_limited_api' anyway.  At worst, we get a
            # warning.
            kwds['py_limited_api'] = True
    return kwds

def _add_c_module(dist, ffi, module_name, source, source_extension, kwds):
    # We are a setuptools extension. Need this build_ext for py_limited_api.
    from setuptools.command.build_ext import build_ext
    from cffi._shimmed_dist_utils import Extension, log, mkpath
    from cffi import recompiler

    allsources = ['$PLACEHOLDER']
    allsources.extend(kwds.pop('sources', []))
    kwds = _set_py_limited_api(Extension, kwds)
    ext = Extension(name=module_name, sources=allsources, **kwds)

    def make_mod(tmpdir, pre_run=None):
        c_file = os.path.join(tmpdir, module_name + source_extension)
        log.info("generating cffi module %r" % c_file)
        mkpath(tmpdir)
        # a setuptools-only, API-only hook: called with the "ext" and "ffi"
        # arguments just before we turn the ffi into C code.  To use it,
        # subclass the 'distutils.command.build_ext.build_ext' class and
        # add a method 'def pre_run(self, ext, ffi)'.
        if pre_run is not None:
            pre_run(ext, ffi)
        updated = recompiler.make_c_source(ffi, module_name, source, c_file)
        if not updated:
            log.info("already up-to-date")
        return c_file

    if dist.ext_modules is None:
        dist.ext_modules = []
    dist.ext_modules.append(ext)

    base_class = dist.cmdclass.get('build_ext', build_ext)
    class build_ext_make_mod(base_class):
        def run(self):
            if ext.sources[0] == '$PLACEHOLDER':
                pre_run = getattr(self, 'pre_run', None)
                ext.sources[0] = make_mod(self.build_temp, pre_run)
            base_class.run(self)
    dist.cmdclass['build_ext'] = build_ext_make_mod
    # NB. multiple runs here will create multiple 'build_ext_make_mod'
    # classes.  Even in this case the 'build_ext' command should be
    # run once; but just in case, the logic above does nothing if
    # called again.


def _add_py_module(dist, ffi, module_name):
    from setuptools.command.build_py import build_py
    from setuptools.command.build_ext import build_ext
    from cffi._shimmed_dist_utils import log, mkpath
    from cffi import recompiler

    def generate_mod(py_file):
        log.info("generating cffi module %r" % py_file)
        mkpath(os.path.dirname(py_file))
        updated = recompiler.make_py_source(ffi, module_name, py_file)
        if not updated:
            log.info("already up-to-date")

    base_class = dist.cmdclass.get('build_py', build_py)
    class build_py_make_mod(base_class):
        def run(self):
            base_class.run(self)
            module_path = module_name.split('.')
            module_path[-1] += '.py'
            generate_mod(os.path.join(self.build_lib, *module_path))
        def get_source_files(self):
            # This is called from 'setup.py sdist' only.  Exclude
            # the generate .py module in this case.
            saved_py_modules = self.py_modules
            try:
                if saved_py_modules:
                    self.py_modules = [m for m in saved_py_modules
                                         if m != module_name]
                return base_class.get_source_files(self)
            finally:
                self.py_modules = saved_py_modules
    dist.cmdclass['build_py'] = build_py_make_mod

    # distutils and setuptools have no notion I could find of a
    # generated python module.  If we don't add module_name to
    # dist.py_modules, then things mostly work but there are some
    # combination of options (--root and --record) that will miss
    # the module.  So we add it here, which gives a few apparently
    # harmless warnings about not finding the file outside the
    # build directory.
    # Then we need to hack more in get_source_files(); see above.
    if dist.py_modules is None:
        dist.py_modules = []
    dist.py_modules.append(module_name)

    # the following is only for "build_ext -i"
    base_class_2 = dist.cmdclass.get('build_ext', build_ext)
    class build_ext_make_mod(base_class_2):
        def run(self):
            base_class_2.run(self)
            if self.inplace:
                # from get_ext_fullpath() in distutils/command/build_ext.py
                module_path = module_name.split('.')
                package = '.'.join(module_path[:-1])
                build_py = self.get_finalized_command('build_py')
                package_dir = build_py.get_package_dir(package)
                file_name = module_path[-1] + '.py'
                generate_mod(os.path.join(package_dir, file_name))
    dist.cmdclass['build_ext'] = build_ext_make_mod

def cffi_modules(dist, attr, value):
    assert attr == 'cffi_modules'
    if isinstance(value, basestring):
        value = [value]

    for cffi_module in value:
        add_cffi_module(dist, cffi_module)

# === NexusCore/openenv\Lib\site-packages\IPython\utils\_process_win32.py ===
"""Windows-specific implementation of process utilities.

This file is only meant to be imported by process.py, not by end-users.
"""

import ctypes
import os
import subprocess
import sys
import time
from ctypes import POINTER, c_int
from ctypes.wintypes import HLOCAL, LPCWSTR
from subprocess import STDOUT
from threading import Thread
from types import TracebackType
from typing import List, Optional

from . import py3compat
from ._process_common import arg_split as py_arg_split

from ._process_common import process_handler, read_no_interrupt
from .encoding import DEFAULT_ENCODING


class AvoidUNCPath:
    """A context manager to protect command execution from UNC paths.

    In the Win32 API, commands can't be invoked with the cwd being a UNC path.
    This context manager temporarily changes directory to the 'C:' drive on
    entering, and restores the original working directory on exit.

    The context manager returns the starting working directory *if* it made a
    change and None otherwise, so that users can apply the necessary adjustment
    to their system calls in the event of a change.

    Examples
    --------
    ::
        cmd = 'dir'
        with AvoidUNCPath() as path:
            if path is not None:
                cmd = '"pushd %s &&"%s' % (path, cmd)
            os.system(cmd)
    """

    def __enter__(self) -> Optional[str]:
        self.path = os.getcwd()
        self.is_unc_path = self.path.startswith(r"\\")
        if self.is_unc_path:
            # change to c drive (as cmd.exe cannot handle UNC addresses)
            os.chdir("C:")
            return self.path
        else:
            # We return None to signal that there was no change in the working
            # directory
            return None

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: TracebackType,
    ) -> None:
        if self.is_unc_path:
            os.chdir(self.path)


def _system_body(p: subprocess.Popen) -> int:
    """Callback for _system."""
    enc = DEFAULT_ENCODING

    # Dec 2024: in both of these functions, I'm not sure why we .splitlines()
    # the bytes and then decode each line individually instead of just decoding
    # the whole thing at once.
    def stdout_read() -> None:
        try:
            assert p.stdout is not None
            for byte_line in read_no_interrupt(p.stdout).splitlines():
                line = byte_line.decode(enc, "replace")
                print(line, file=sys.stdout)
        except Exception as e:
            print(f"Error reading stdout: {e}", file=sys.stderr)

    def stderr_read() -> None:
        try:
            assert p.stderr is not None
            for byte_line in read_no_interrupt(p.stderr).splitlines():
                line = byte_line.decode(enc, "replace")
                print(line, file=sys.stderr)
        except Exception as e:
            print(f"Error reading stderr: {e}", file=sys.stderr)

    stdout_thread = Thread(target=stdout_read)
    stderr_thread = Thread(target=stderr_read)

    stdout_thread.start()
    stderr_thread.start()

    # Wait to finish for returncode. Unfortunately, Python has a bug where
    # wait() isn't interruptible (https://bugs.python.org/issue28168) so poll in
    # a loop instead of just doing `return p.wait()`
    while True:
        result = p.poll()
        if result is None:
            time.sleep(0.01)
        else:
            break

    # Join the threads to ensure they complete before returning
    stdout_thread.join()
    stderr_thread.join()

    return result


def system(cmd: str) -> Optional[int]:
    """Win32 version of os.system() that works with network shares.

    Note that this implementation returns None, as meant for use in IPython.

    Parameters
    ----------
    cmd : str or list
        A command to be executed in the system shell.

    Returns
    -------
    int : child process' exit code.
    """
    # The controller provides interactivity with both
    # stdin and stdout
    # import _process_win32_controller
    # _process_win32_controller.system(cmd)

    with AvoidUNCPath() as path:
        if path is not None:
            cmd = '"pushd %s &&"%s' % (path, cmd)
        res = process_handler(cmd, _system_body)
        assert isinstance(res, int | type(None))
        return res
    return None


def getoutput(cmd: str) -> str:
    """Return standard output of executing cmd in a shell.

    Accepts the same arguments as os.system().

    Parameters
    ----------
    cmd : str or list
        A command to be executed in the system shell.

    Returns
    -------
    stdout : str
    """

    with AvoidUNCPath() as path:
        if path is not None:
            cmd = '"pushd %s &&"%s' % (path, cmd)
        out = process_handler(cmd, lambda p: p.communicate()[0], STDOUT)

    if out is None:
        out = b""
    return py3compat.decode(out)


try:
    windll = ctypes.windll  # type: ignore [attr-defined]
    CommandLineToArgvW = windll.shell32.CommandLineToArgvW
    CommandLineToArgvW.arg_types = [LPCWSTR, POINTER(c_int)]
    CommandLineToArgvW.restype = POINTER(LPCWSTR)
    LocalFree = windll.kernel32.LocalFree
    LocalFree.res_type = HLOCAL
    LocalFree.arg_types = [HLOCAL]

    def arg_split(
        commandline: str, posix: bool = False, strict: bool = True
    ) -> List[str]:
        """Split a command line's arguments in a shell-like manner.

        This is a special version for windows that use a ctypes call to CommandLineToArgvW
        to do the argv splitting. The posix parameter is ignored.

        If strict=False, process_common.arg_split(...strict=False) is used instead.
        """
        # CommandLineToArgvW returns path to executable if called with empty string.
        if commandline.strip() == "":
            return []
        if not strict:
            # not really a cl-arg, fallback on _process_common
            return py_arg_split(commandline, posix=posix, strict=strict)
        argvn = c_int()
        result_pointer = CommandLineToArgvW(commandline.lstrip(), ctypes.byref(argvn))
        try:
            result_array_type = LPCWSTR * argvn.value
            result = [
                arg
                for arg in result_array_type.from_address(
                    ctypes.addressof(result_pointer.contents)
                )
                if arg is not None
            ]
        finally:
            # for side effects
            _ = LocalFree(result_pointer)
        return result
except AttributeError:
    arg_split = py_arg_split


def check_pid(pid: int) -> bool:
    # OpenProcess returns 0 if no such process (of ours) exists
    # positive int otherwise
    return bool(windll.kernel32.OpenProcess(1, 0, pid))

# === NexusCore/openenv\Lib\site-packages\litellm\llms\azure\responses\transformation.py ===
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, cast

import httpx

import litellm
from litellm._logging import verbose_logger
from litellm.llms.openai.responses.transformation import OpenAIResponsesAPIConfig
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import *
from litellm.types.responses.main import *
from litellm.types.router import GenericLiteLLMParams
from litellm.utils import _add_path_to_api_base

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class AzureOpenAIResponsesAPIConfig(OpenAIResponsesAPIConfig):
    def validate_environment(
        self,
        headers: dict,
        model: str,
        api_key: Optional[str] = None,
    ) -> dict:
        api_key = (
            api_key
            or litellm.api_key
            or litellm.azure_key
            or get_secret_str("AZURE_OPENAI_API_KEY")
            or get_secret_str("AZURE_API_KEY")
        )

        headers.update(
            {
                "Authorization": f"Bearer {api_key}",
            }
        )
        return headers

    def get_complete_url(
        self,
        api_base: Optional[str],
        litellm_params: dict,
    ) -> str:
        """
        Constructs a complete URL for the API request.

        Args:
        - api_base: Base URL, e.g.,
            "https://litellm8397336933.openai.azure.com"
            OR
            "https://litellm8397336933.openai.azure.com/openai/responses?api-version=2024-05-01-preview"
        - model: Model name.
        - optional_params: Additional query parameters, including "api_version".
        - stream: If streaming is required (optional).

        Returns:
        - A complete URL string, e.g.,
        "https://litellm8397336933.openai.azure.com/openai/responses?api-version=2024-05-01-preview"
        """
        api_base = api_base or litellm.api_base or get_secret_str("AZURE_API_BASE")
        if api_base is None:
            raise ValueError(
                f"api_base is required for Azure AI Studio. Please set the api_base parameter. Passed `api_base={api_base}`"
            )
        original_url = httpx.URL(api_base)

        # Extract api_version or use default
        api_version = cast(Optional[str], litellm_params.get("api_version"))

        # Create a new dictionary with existing params
        query_params = dict(original_url.params)

        # Add api_version if needed
        if "api-version" not in query_params and api_version:
            query_params["api-version"] = api_version
        
        # Add the path to the base URL
        if "/openai/responses" not in api_base:
            new_url = _add_path_to_api_base(
                api_base=api_base, ending_path="/openai/responses"
            )
        else:
            new_url = api_base
        
        if self._is_azure_v1_api_version(api_version):
            # ensure the request go to /openai/v1 and not just /openai
            if "/openai/v1" not in new_url:
                parsed_url = httpx.URL(new_url)
                new_url = str(parsed_url.copy_with(path=parsed_url.path.replace("/openai", "/openai/v1")))


        # Use the new query_params dictionary
        final_url = httpx.URL(new_url).copy_with(params=query_params)

        return str(final_url)
    
    def _is_azure_v1_api_version(self, api_version: Optional[str]) -> bool:
        if api_version is None:
            return False
        return api_version == "preview" or api_version == "latest"

    #########################################################
    ########## DELETE RESPONSE API TRANSFORMATION ##############
    #########################################################
    def _construct_url_for_response_id_in_path(
        self, api_base: str, response_id: str
    ) -> str:
        """
        Constructs a URL for the API request with the response_id in the path.
        """
        from urllib.parse import urlparse, urlunparse

        # Parse the URL to separate its components
        parsed_url = urlparse(api_base)

        # Insert the response_id at the end of the path component
        # Remove trailing slash if present to avoid double slashes
        path = parsed_url.path.rstrip("/")
        new_path = f"{path}/{response_id}"

        # Reconstruct the URL with all original components but with the modified path
        constructed_url = urlunparse(
            (
                parsed_url.scheme,  # http, https
                parsed_url.netloc,  # domain name, port
                new_path,  # path with response_id added
                parsed_url.params,  # parameters
                parsed_url.query,  # query string
                parsed_url.fragment,  # fragment
            )
        )
        return constructed_url

    def transform_delete_response_api_request(
        self,
        response_id: str,
        api_base: str,
        litellm_params: GenericLiteLLMParams,
        headers: dict,
    ) -> Tuple[str, Dict]:
        """
        Transform the delete response API request into a URL and data

        Azure OpenAI API expects the following request:
        - DELETE /openai/responses/{response_id}?api-version=xxx

        This function handles URLs with query parameters by inserting the response_id
        at the correct location (before any query parameters).
        """
        delete_url = self._construct_url_for_response_id_in_path(
            api_base=api_base, response_id=response_id
        )

        data: Dict = {}
        verbose_logger.debug(f"delete response url={delete_url}")
        return delete_url, data

    #########################################################
    ########## GET RESPONSE API TRANSFORMATION ###############
    #########################################################
    def transform_get_response_api_request(
        self,
        response_id: str,
        api_base: str,
        litellm_params: GenericLiteLLMParams,
        headers: dict,
    ) -> Tuple[str, Dict]:
        """
        Transform the get response API request into a URL and data

        OpenAI API expects the following request
        - GET /v1/responses/{response_id}
        """
        get_url = self._construct_url_for_response_id_in_path(
            api_base=api_base, response_id=response_id
        )
        data: Dict = {}
        verbose_logger.debug(f"get response url={get_url}")
        return get_url, data

    def transform_list_input_items_request(
        self,
        response_id: str,
        api_base: str,
        litellm_params: GenericLiteLLMParams,
        headers: dict,
        after: Optional[str] = None,
        before: Optional[str] = None,
        include: Optional[List[str]] = None,
        limit: int = 20,
        order: Literal["asc", "desc"] = "desc",
    ) -> Tuple[str, Dict]:
        url = (
            self._construct_url_for_response_id_in_path(
                api_base=api_base, response_id=response_id
            )
            + "/input_items"
        )
        params: Dict[str, Any] = {}
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before
        if include:
            params["include"] = ",".join(include)
        if limit is not None:
            params["limit"] = limit
        if order is not None:
            params["order"] = order
        verbose_logger.debug(f"list input items url={url}")
        return url, params

# === NexusCore/openenv\Lib\site-packages\litellm\llms\base_llm\responses\transformation.py ===
import types
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union

import httpx

from litellm.types.llms.openai import (
    ResponseInputParam,
    ResponsesAPIOptionalRequestParams,
    ResponsesAPIResponse,
    ResponsesAPIStreamingResponse,
)
from litellm.types.responses.main import *
from litellm.types.router import GenericLiteLLMParams

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    from ..chat.transformation import BaseLLMException as _BaseLLMException

    LiteLLMLoggingObj = _LiteLLMLoggingObj
    BaseLLMException = _BaseLLMException
else:
    LiteLLMLoggingObj = Any
    BaseLLMException = Any


class BaseResponsesAPIConfig(ABC):
    def __init__(self):
        pass

    @classmethod
    def get_config(cls):
        return {
            k: v
            for k, v in cls.__dict__.items()
            if not k.startswith("__")
            and not k.startswith("_abc")
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

    @abstractmethod
    def get_supported_openai_params(self, model: str) -> list:
        pass

    @abstractmethod
    def map_openai_params(
        self,
        response_api_optional_params: ResponsesAPIOptionalRequestParams,
        model: str,
        drop_params: bool,
    ) -> Dict:
        pass

    @abstractmethod
    def validate_environment(
        self,
        headers: dict,
        model: str,
        api_key: Optional[str] = None,
    ) -> dict:
        return {}

    @abstractmethod
    def get_complete_url(
        self,
        api_base: Optional[str],
        litellm_params: dict,
    ) -> str:
        """
        OPTIONAL

        Get the complete url for the request

        Some providers need `model` in `api_base`
        """
        if api_base is None:
            raise ValueError("api_base is required")
        return api_base

    @abstractmethod
    def transform_responses_api_request(
        self,
        model: str,
        input: Union[str, ResponseInputParam],
        response_api_optional_request_params: Dict,
        litellm_params: GenericLiteLLMParams,
        headers: dict,
    ) -> Dict:
        pass

    @abstractmethod
    def transform_response_api_response(
        self,
        model: str,
        raw_response: httpx.Response,
        logging_obj: LiteLLMLoggingObj,
    ) -> ResponsesAPIResponse:
        pass

    @abstractmethod
    def transform_streaming_response(
        self,
        model: str,
        parsed_chunk: dict,
        logging_obj: LiteLLMLoggingObj,
    ) -> ResponsesAPIStreamingResponse:
        """
        Transform a parsed streaming response chunk into a ResponsesAPIStreamingResponse
        """
        pass

    #########################################################
    ########## DELETE RESPONSE API TRANSFORMATION ##############
    #########################################################
    @abstractmethod
    def transform_delete_response_api_request(
        self,
        response_id: str,
        api_base: str,
        litellm_params: GenericLiteLLMParams,
        headers: dict,
    ) -> Tuple[str, Dict]:
        pass

    @abstractmethod
    def transform_delete_response_api_response(
        self,
        raw_response: httpx.Response,
        logging_obj: LiteLLMLoggingObj,
    ) -> DeleteResponseResult:
        pass

    #########################################################
    ########## END DELETE RESPONSE API TRANSFORMATION #######
    #########################################################

    #########################################################
    ########## GET RESPONSE API TRANSFORMATION ###############
    #########################################################
    @abstractmethod
    def transform_get_response_api_request(
        self,
        response_id: str,
        api_base: str,
        litellm_params: GenericLiteLLMParams,
        headers: dict,
    ) -> Tuple[str, Dict]:
        pass

    @abstractmethod
    def transform_get_response_api_response(
        self,
        raw_response: httpx.Response,
        logging_obj: LiteLLMLoggingObj,
    ) -> ResponsesAPIResponse:
        pass

    #########################################################
    ########## LIST INPUT ITEMS API TRANSFORMATION ##########
    #########################################################
    @abstractmethod
    def transform_list_input_items_request(
        self,
        response_id: str,
        api_base: str,
        litellm_params: GenericLiteLLMParams,
        headers: dict,
        after: Optional[str] = None,
        before: Optional[str] = None,
        include: Optional[List[str]] = None,
        limit: int = 20,
        order: Literal["asc", "desc"] = "desc",
    ) -> Tuple[str, Dict]:
        pass

    @abstractmethod
    def transform_list_input_items_response(
        self,
        raw_response: httpx.Response,
        logging_obj: LiteLLMLoggingObj,
    ) -> Dict:
        pass

    #########################################################
    ########## END GET RESPONSE API TRANSFORMATION ##########
    #########################################################

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        from ..chat.transformation import BaseLLMException

        raise BaseLLMException(
            status_code=status_code,
            message=error_message,
            headers=headers,
        )

    def should_fake_stream(
        self,
        model: Optional[str],
        stream: Optional[bool],
        custom_llm_provider: Optional[str] = None,
    ) -> bool:
        """Returns True if litellm should fake a stream for the given model and stream value"""
        return False

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\socks.py ===
# -*- coding: utf-8 -*-
"""
This module contains provisional support for SOCKS proxies from within
urllib3. This module supports SOCKS4, SOCKS4A (an extension of SOCKS4), and
SOCKS5. To enable its functionality, either install PySocks or install this
module with the ``socks`` extra.

The SOCKS implementation supports the full range of urllib3 features. It also
supports the following SOCKS features:

- SOCKS4A (``proxy_url='socks4a://...``)
- SOCKS4 (``proxy_url='socks4://...``)
- SOCKS5 with remote DNS (``proxy_url='socks5h://...``)
- SOCKS5 with local DNS (``proxy_url='socks5://...``)
- Usernames and passwords for the SOCKS proxy

.. note::
   It is recommended to use ``socks5h://`` or ``socks4a://`` schemes in
   your ``proxy_url`` to ensure that DNS resolution is done from the remote
   server instead of client-side when connecting to a domain name.

SOCKS4 supports IPv4 and domain names with the SOCKS4A extension. SOCKS5
supports IPv4, IPv6, and domain names.

When connecting to a SOCKS4 proxy the ``username`` portion of the ``proxy_url``
will be sent as the ``userid`` section of the SOCKS request:

.. code-block:: python

    proxy_url="socks4a://<userid>@proxy-host"

When connecting to a SOCKS5 proxy the ``username`` and ``password`` portion
of the ``proxy_url`` will be sent as the username/password to authenticate
with the proxy:

.. code-block:: python

    proxy_url="socks5h://<username>:<password>@proxy-host"

"""
from __future__ import absolute_import

try:
    import socks
except ImportError:
    import warnings

    from ..exceptions import DependencyWarning

    warnings.warn(
        (
            "SOCKS support in urllib3 requires the installation of optional "
            "dependencies: specifically, PySocks.  For more information, see "
            "https://urllib3.readthedocs.io/en/1.26.x/contrib.html#socks-proxies"
        ),
        DependencyWarning,
    )
    raise

from socket import error as SocketError
from socket import timeout as SocketTimeout

from ..connection import HTTPConnection, HTTPSConnection
from ..connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from ..exceptions import ConnectTimeoutError, NewConnectionError
from ..poolmanager import PoolManager
from ..util.url import parse_url

try:
    import ssl
except ImportError:
    ssl = None


class SOCKSConnection(HTTPConnection):
    """
    A plain-text HTTP connection that connects via a SOCKS proxy.
    """

    def __init__(self, *args, **kwargs):
        self._socks_options = kwargs.pop("_socks_options")
        super(SOCKSConnection, self).__init__(*args, **kwargs)

    def _new_conn(self):
        """
        Establish a new connection via the SOCKS proxy.
        """
        extra_kw = {}
        if self.source_address:
            extra_kw["source_address"] = self.source_address

        if self.socket_options:
            extra_kw["socket_options"] = self.socket_options

        try:
            conn = socks.create_connection(
                (self.host, self.port),
                proxy_type=self._socks_options["socks_version"],
                proxy_addr=self._socks_options["proxy_host"],
                proxy_port=self._socks_options["proxy_port"],
                proxy_username=self._socks_options["username"],
                proxy_password=self._socks_options["password"],
                proxy_rdns=self._socks_options["rdns"],
                timeout=self.timeout,
                **extra_kw
            )

        except SocketTimeout:
            raise ConnectTimeoutError(
                self,
                "Connection to %s timed out. (connect timeout=%s)"
                % (self.host, self.timeout),
            )

        except socks.ProxyError as e:
            # This is fragile as hell, but it seems to be the only way to raise
            # useful errors here.
            if e.socket_err:
                error = e.socket_err
                if isinstance(error, SocketTimeout):
                    raise ConnectTimeoutError(
                        self,
                        "Connection to %s timed out. (connect timeout=%s)"
                        % (self.host, self.timeout),
                    )
                else:
                    raise NewConnectionError(
                        self, "Failed to establish a new connection: %s" % error
                    )
            else:
                raise NewConnectionError(
                    self, "Failed to establish a new connection: %s" % e
                )

        except SocketError as e:  # Defensive: PySocks should catch all these.
            raise NewConnectionError(
                self, "Failed to establish a new connection: %s" % e
            )

        return conn


# We don't need to duplicate the Verified/Unverified distinction from
# urllib3/connection.py here because the HTTPSConnection will already have been
# correctly set to either the Verified or Unverified form by that module. This
# means the SOCKSHTTPSConnection will automatically be the correct type.
class SOCKSHTTPSConnection(SOCKSConnection, HTTPSConnection):
    pass


class SOCKSHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = SOCKSConnection


class SOCKSHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = SOCKSHTTPSConnection


class SOCKSProxyManager(PoolManager):
    """
    A version of the urllib3 ProxyManager that routes connections via the
    defined SOCKS proxy.
    """

    pool_classes_by_scheme = {
        "http": SOCKSHTTPConnectionPool,
        "https": SOCKSHTTPSConnectionPool,
    }

    def __init__(
        self,
        proxy_url,
        username=None,
        password=None,
        num_pools=10,
        headers=None,
        **connection_pool_kw
    ):
        parsed = parse_url(proxy_url)

        if username is None and password is None and parsed.auth is not None:
            split = parsed.auth.split(":")
            if len(split) == 2:
                username, password = split
        if parsed.scheme == "socks5":
            socks_version = socks.PROXY_TYPE_SOCKS5
            rdns = False
        elif parsed.scheme == "socks5h":
            socks_version = socks.PROXY_TYPE_SOCKS5
            rdns = True
        elif parsed.scheme == "socks4":
            socks_version = socks.PROXY_TYPE_SOCKS4
            rdns = False
        elif parsed.scheme == "socks4a":
            socks_version = socks.PROXY_TYPE_SOCKS4
            rdns = True
        else:
            raise ValueError("Unable to determine SOCKS version from %s" % proxy_url)

        self.proxy_url = proxy_url

        socks_options = {
            "socks_version": socks_version,
            "proxy_host": parsed.host,
            "proxy_port": parsed.port,
            "username": username,
            "password": password,
            "rdns": rdns,
        }
        connection_pool_kw["_socks_options"] = socks_options

        super(SOCKSProxyManager, self).__init__(
            num_pools, headers, **connection_pool_kw
        )

        self.pool_classes_by_scheme = SOCKSProxyManager.pool_classes_by_scheme

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\typoscript.py ===
"""
    pygments.lexers.typoscript
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for TypoScript

    `TypoScriptLexer`
        A TypoScript lexer.

    `TypoScriptCssDataLexer`
        Lexer that highlights markers, constants and registers within css.

    `TypoScriptHtmlDataLexer`
        Lexer that highlights markers, constants and registers within html tags.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, using
from pygments.token import Text, Comment, Name, String, Number, \
    Operator, Punctuation

__all__ = ['TypoScriptLexer', 'TypoScriptCssDataLexer', 'TypoScriptHtmlDataLexer']


class TypoScriptCssDataLexer(RegexLexer):
    """
    Lexer that highlights markers, constants and registers within css blocks.
    """

    name = 'TypoScriptCssData'
    aliases = ['typoscriptcssdata']
    url = 'http://docs.typo3.org/typo3cms/TyposcriptReference/'
    version_added = '2.2'

    tokens = {
        'root': [
            # marker: ###MARK###
            (r'(.*)(###\w+###)(.*)', bygroups(String, Name.Constant, String)),
            # constant: {$some.constant}
            (r'(\{)(\$)((?:[\w\-]+\.)*)([\w\-]+)(\})',
             bygroups(String.Symbol, Operator, Name.Constant,
                      Name.Constant, String.Symbol)),  # constant
            # constant: {register:somevalue}
            (r'(.*)(\{)([\w\-]+)(\s*:\s*)([\w\-]+)(\})(.*)',
             bygroups(String, String.Symbol, Name.Constant, Operator,
                      Name.Constant, String.Symbol, String)),  # constant
            # whitespace
            (r'\s+', Text),
            # comments
            (r'/\*(?:(?!\*/).)*\*/', Comment),
            (r'(?<!(#|\'|"))(?:#(?!(?:[a-fA-F0-9]{6}|[a-fA-F0-9]{3}))[^\n#]+|//[^\n]*)',
             Comment),
            # other
            (r'[<>,:=.*%+|]', String),
            (r'[\w"\-!/&;(){}]+', String),
        ]
    }


class TypoScriptHtmlDataLexer(RegexLexer):
    """
    Lexer that highlights markers, constants and registers within html tags.
    """

    name = 'TypoScriptHtmlData'
    aliases = ['typoscripthtmldata']
    url = 'http://docs.typo3.org/typo3cms/TyposcriptReference/'
    version_added = '2.2'

    tokens = {
        'root': [
            # INCLUDE_TYPOSCRIPT
            (r'(INCLUDE_TYPOSCRIPT)', Name.Class),
            # Language label or extension resource FILE:... or LLL:... or EXT:...
            (r'(EXT|FILE|LLL):[^}\n"]*', String),
            # marker: ###MARK###
            (r'(.*)(###\w+###)(.*)', bygroups(String, Name.Constant, String)),
            # constant: {$some.constant}
            (r'(\{)(\$)((?:[\w\-]+\.)*)([\w\-]+)(\})',
             bygroups(String.Symbol, Operator, Name.Constant,
                      Name.Constant, String.Symbol)),  # constant
            # constant: {register:somevalue}
            (r'(.*)(\{)([\w\-]+)(\s*:\s*)([\w\-]+)(\})(.*)',
             bygroups(String, String.Symbol, Name.Constant, Operator,
                      Name.Constant, String.Symbol, String)),  # constant
            # whitespace
            (r'\s+', Text),
            # other
            (r'[<>,:=.*%+|]', String),
            (r'[\w"\-!/&;(){}#]+', String),
        ]
    }


class TypoScriptLexer(RegexLexer):
    """
    Lexer for TypoScript code.
    """

    name = 'TypoScript'
    url = 'http://docs.typo3.org/typo3cms/TyposcriptReference/'
    aliases = ['typoscript']
    filenames = ['*.typoscript']
    mimetypes = ['text/x-typoscript']
    version_added = '2.2'

    flags = re.DOTALL | re.MULTILINE

    tokens = {
        'root': [
            include('comment'),
            include('constant'),
            include('html'),
            include('label'),
            include('whitespace'),
            include('keywords'),
            include('punctuation'),
            include('operator'),
            include('structure'),
            include('literal'),
            include('other'),
        ],
        'keywords': [
            # Conditions
            (r'(?i)(\[)(browser|compatVersion|dayofmonth|dayofweek|dayofyear|'
             r'device|ELSE|END|GLOBAL|globalString|globalVar|hostname|hour|IP|'
             r'language|loginUser|loginuser|minute|month|page|PIDinRootline|'
             r'PIDupinRootline|system|treeLevel|useragent|userFunc|usergroup|'
             r'version)([^\]]*)(\])',
             bygroups(String.Symbol, Name.Constant, Text, String.Symbol)),
            # Functions
            (r'(?=[\w\-])(HTMLparser|HTMLparser_tags|addParams|cache|encapsLines|'
             r'filelink|if|imageLinkWrap|imgResource|makelinks|numRows|numberFormat|'
             r'parseFunc|replacement|round|select|split|stdWrap|strPad|tableStyle|'
             r'tags|textStyle|typolink)(?![\w\-])', Name.Function),
            # Toplevel objects and _*
            (r'(?:(=?\s*<?\s+|^\s*))(cObj|field|config|content|constants|FEData|'
             r'file|frameset|includeLibs|lib|page|plugin|register|resources|sitemap|'
             r'sitetitle|styles|temp|tt_[^:.\s]*|types|xmlnews|INCLUDE_TYPOSCRIPT|'
             r'_CSS_DEFAULT_STYLE|_DEFAULT_PI_VARS|_LOCAL_LANG)(?![\w\-])',
             bygroups(Operator, Name.Builtin)),
            # Content objects
            (r'(?=[\w\-])(CASE|CLEARGIF|COA|COA_INT|COBJ_ARRAY|COLUMNS|CONTENT|'
             r'CTABLE|EDITPANEL|FILE|FILES|FLUIDTEMPLATE|FORM|HMENU|HRULER|HTML|'
             r'IMAGE|IMGTEXT|IMG_RESOURCE|LOAD_REGISTER|MEDIA|MULTIMEDIA|OTABLE|'
             r'PAGE|QTOBJECT|RECORDS|RESTORE_REGISTER|SEARCHRESULT|SVG|SWFOBJECT|'
             r'TEMPLATE|TEXT|USER|USER_INT)(?![\w\-])', Name.Class),
            # Menu states
            (r'(?=[\w\-])(ACTIFSUBRO|ACTIFSUB|ACTRO|ACT|CURIFSUBRO|CURIFSUB|CURRO|'
             r'CUR|IFSUBRO|IFSUB|NO|SPC|USERDEF1RO|USERDEF1|USERDEF2RO|USERDEF2|'
             r'USRRO|USR)', Name.Class),
            # Menu objects
            (r'(?=[\w\-])(GMENU_FOLDOUT|GMENU_LAYERS|GMENU|IMGMENUITEM|IMGMENU|'
             r'JSMENUITEM|JSMENU|TMENUITEM|TMENU_LAYERS|TMENU)', Name.Class),
            # PHP objects
            (r'(?=[\w\-])(PHP_SCRIPT(_EXT|_INT)?)', Name.Class),
            (r'(?=[\w\-])(userFunc)(?![\w\-])', Name.Function),
        ],
        'whitespace': [
            (r'\s+', Text),
        ],
        'html': [
            (r'<\S[^\n>]*>', using(TypoScriptHtmlDataLexer)),
            (r'&[^;\n]*;', String),
            (r'(?s)(_CSS_DEFAULT_STYLE)(\s*)(\()(.*(?=\n\)))',
             bygroups(Name.Class, Text, String.Symbol, using(TypoScriptCssDataLexer))),
        ],
        'literal': [
            (r'0x[0-9A-Fa-f]+t?', Number.Hex),
            # (r'[0-9]*\.[0-9]+([eE][0-9]+)?[fd]?\s*(?:[^=])', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r'(###\w+###)', Name.Constant),
        ],
        'label': [
            # Language label or extension resource FILE:... or LLL:... or EXT:...
            (r'(EXT|FILE|LLL):[^}\n"]*', String),
            # Path to a resource
            (r'(?![^\w\-])([\w\-]+(?:/[\w\-]+)+/?)(\S*\n)',
             bygroups(String, String)),
        ],
        'punctuation': [
            (r'[,.]', Punctuation),
        ],
        'operator': [
            (r'[<>,:=.*%+|]', Operator),
        ],
        'structure': [
            # Brackets and braces
            (r'[{}()\[\]\\]', String.Symbol),
        ],
        'constant': [
            # Constant: {$some.constant}
            (r'(\{)(\$)((?:[\w\-]+\.)*)([\w\-]+)(\})',
                bygroups(String.Symbol, Operator, Name.Constant,
                         Name.Constant, String.Symbol)),  # constant
            # Constant: {register:somevalue}
            (r'(\{)([\w\-]+)(\s*:\s*)([\w\-]+)(\})',
                bygroups(String.Symbol, Name.Constant, Operator,
                         Name.Constant, String.Symbol)),  # constant
            # Hex color: #ff0077
            (r'(#[a-fA-F0-9]{6}\b|#[a-fA-F0-9]{3}\b)', String.Char)
        ],
        'comment': [
            (r'(?<!(#|\'|"))(?:#(?!(?:[a-fA-F0-9]{6}|[a-fA-F0-9]{3}))[^\n#]+|//[^\n]*)',
             Comment),
            (r'/\*(?:(?!\*/).)*\*/', Comment),
            (r'(\s*#\s*\n)', Comment),
        ],
        'other': [
            (r'[\w"\-!/&;]+', Text),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\idle\CallTips.py ===
# CallTips.py - An IDLE extension that provides "Call Tips" - ie, a floating window that
# displays parameter information as you open parens.

import inspect
import string
import sys
import traceback


class CallTips:
    menudefs = []

    keydefs = {
        "<<paren-open>>": ["<Key-parenleft>"],
        "<<paren-close>>": ["<Key-parenright>"],
        "<<check-calltip-cancel>>": ["<KeyRelease>"],
        "<<calltip-cancel>>": ["<ButtonPress>", "<Key-Escape>"],
    }

    windows_keydefs = {}

    unix_keydefs = {}

    def __init__(self, editwin):
        self.editwin = editwin
        self.text = editwin.text
        self.calltip = None
        if hasattr(self.text, "make_calltip_window"):
            self._make_calltip_window = self.text.make_calltip_window
        else:
            self._make_calltip_window = self._make_tk_calltip_window

    def close(self):
        self._make_calltip_window = None

    # Makes a Tk based calltip window.  Used by IDLE, but not Pythonwin.
    # See __init__ above for how this is used.
    def _make_tk_calltip_window(self):
        import CallTipWindow

        return CallTipWindow.CallTip(self.text)

    def _remove_calltip_window(self):
        if self.calltip:
            self.calltip.hidetip()
            self.calltip = None

    def paren_open_event(self, event):
        self._remove_calltip_window()
        arg_text = get_arg_text(self.get_object_at_cursor())
        if arg_text:
            self.calltip_start = self.text.index("insert")
            self.calltip = self._make_calltip_window()
            self.calltip.showtip(arg_text)
        return ""  # so the event is handled normally.

    def paren_close_event(self, event):
        # Now just hides, but later we should check if other
        # paren'd expressions remain open.
        self._remove_calltip_window()
        return ""  # so the event is handled normally.

    def check_calltip_cancel_event(self, event):
        if self.calltip:
            # If we have moved before the start of the calltip,
            # or off the calltip line, then cancel the tip.
            # (Later need to be smarter about multi-line, etc)
            if self.text.compare(
                "insert", "<=", self.calltip_start
            ) or self.text.compare("insert", ">", self.calltip_start + " lineend"):
                self._remove_calltip_window()
        return ""  # so the event is handled normally.

    def calltip_cancel_event(self, event):
        self._remove_calltip_window()
        return ""  # so the event is handled normally.

    def get_object_at_cursor(
        self,
        wordchars="._"
        + string.ascii_uppercase
        + string.ascii_lowercase
        + string.digits,
    ):
        # XXX - This needs to be moved to a better place
        # so the "." attribute lookup code can also use it.
        text = self.text
        chars = text.get("insert linestart", "insert")
        i = len(chars)
        while i and chars[i - 1] in wordchars:
            i -= 1
        word = chars[i:]
        if word:
            # How is this for a hack!
            import __main__

            namespace = sys.modules.copy()
            namespace.update(__main__.__dict__)
            try:
                return eval(word, namespace)
            except:
                pass
        return None  # Can't find an object.


def _find_constructor(class_ob):
    # Given a class object, return a function object used for the
    # constructor (ie, __init__() ) or None if we can't find one.
    try:
        return class_ob.__init__
    except AttributeError:
        for base in class_ob.__bases__:
            rc = _find_constructor(base)
            if rc is not None:
                return rc
    return None


def get_arg_text(ob):
    # Get a string describing the arguments for the given object.
    argText = ""
    if ob is not None:
        if inspect.isclass(ob):
            # Look for the highest __init__ in the class chain.
            fob = _find_constructor(ob)
            if fob is None:
                fob = lambda: None
        else:
            fob = ob
        if inspect.isfunction(fob) or inspect.ismethod(fob):
            try:
                argText = str(inspect.signature(fob))
            except:
                print("Failed to format the args")
                traceback.print_exc()
        # See if we can use the docstring
        if hasattr(ob, "__doc__"):
            doc = ob.__doc__
            try:
                doc = doc.strip()
                pos = doc.find("\n")
            except AttributeError:
                ## New style classes may have __doc__ slot without actually
                ## having a string assigned to it
                pass
            else:
                if pos < 0 or pos > 70:
                    pos = 70
                if argText:
                    argText += "\n"
                argText += doc[:pos]

    return argText


#################################################
#
# Test code
#
if __name__ == "__main__":

    def t1():
        "()"

    def t2(a, b=None):
        "(a, b=None)"

    def t3(a, *args):
        "(a, *args)"

    def t4(*args):
        "(*args)"

    def t5(a, *args):
        "(a, *args)"

    def t6(a, b=None, *args, **kw):
        "(a, b=None, *args, **kw)"

    class TC:
        "(self, a=None, *b)"

        def __init__(self, a=None, *b):
            "(self, a=None, *b)"

        def t1(self):
            "(self)"

        def t2(self, a, b=None):
            "(self, a, b=None)"

        def t3(self, a, *args):
            "(self, a, *args)"

        def t4(self, *args):
            "(self, *args)"

        def t5(self, a, *args):
            "(self, a, *args)"

        def t6(self, a, b=None, *args, **kw):
            "(self, a, b=None, *args, **kw)"

    def test(tests):
        failed = []
        for t in tests:
            expected = t.__doc__ + "\n" + t.__doc__
            if get_arg_text(t) != expected:
                failed.append(t)
                print(f"{t} - expected {expected!r}, but got {get_arg_text(t)!r}")
        print("%d of %d tests failed" % (len(failed), len(tests)))

    tc = TC()
    tests = t1, t2, t3, t4, t5, t6, TC, tc.t1, tc.t2, tc.t3, tc.t4, tc.t5, tc.t6

    test(tests)

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\builder.py ===
from fontTools import ttLib
from fontTools.ttLib.tables import otTables as ot

# VariationStore


def buildVarRegionAxis(axisSupport):
    self = ot.VarRegionAxis()
    self.StartCoord, self.PeakCoord, self.EndCoord = [float(v) for v in axisSupport]
    return self


def buildSparseVarRegionAxis(axisIndex, axisSupport):
    self = ot.SparseVarRegionAxis()
    self.AxisIndex = axisIndex
    self.StartCoord, self.PeakCoord, self.EndCoord = [float(v) for v in axisSupport]
    return self


def buildVarRegion(support, axisTags):
    assert all(tag in axisTags for tag in support.keys()), (
        "Unknown axis tag found.",
        support,
        axisTags,
    )
    self = ot.VarRegion()
    self.VarRegionAxis = []
    for tag in axisTags:
        self.VarRegionAxis.append(buildVarRegionAxis(support.get(tag, (0, 0, 0))))
    return self


def buildSparseVarRegion(support, axisTags):
    assert all(tag in axisTags for tag in support.keys()), (
        "Unknown axis tag found.",
        support,
        axisTags,
    )
    self = ot.SparseVarRegion()
    self.SparseVarRegionAxis = []
    for i, tag in enumerate(axisTags):
        if tag not in support:
            continue
        self.SparseVarRegionAxis.append(
            buildSparseVarRegionAxis(i, support.get(tag, (0, 0, 0)))
        )
    self.SparseRegionCount = len(self.SparseVarRegionAxis)
    return self


def buildVarRegionList(supports, axisTags):
    self = ot.VarRegionList()
    self.RegionAxisCount = len(axisTags)
    self.Region = []
    for support in supports:
        self.Region.append(buildVarRegion(support, axisTags))
    self.RegionCount = len(self.Region)
    return self


def buildSparseVarRegionList(supports, axisTags):
    self = ot.SparseVarRegionList()
    self.RegionAxisCount = len(axisTags)
    self.Region = []
    for support in supports:
        self.Region.append(buildSparseVarRegion(support, axisTags))
    self.RegionCount = len(self.Region)
    return self


def _reorderItem(lst, mapping):
    return [lst[i] for i in mapping]


def VarData_calculateNumShorts(self, optimize=False):
    count = self.VarRegionCount
    items = self.Item
    bit_lengths = [0] * count
    for item in items:
        # The "+ (i < -1)" magic is to handle two's-compliment.
        # That is, we want to get back 7 for -128, whereas
        # bit_length() returns 8. Similarly for -65536.
        # The reason "i < -1" is used instead of "i < 0" is that
        # the latter would make it return 0 for "-1" instead of 1.
        bl = [(i + (i < -1)).bit_length() for i in item]
        bit_lengths = [max(*pair) for pair in zip(bl, bit_lengths)]
    # The addition of 8, instead of seven, is to account for the sign bit.
    # This "((b + 8) >> 3) if b else 0" when combined with the above
    # "(i + (i < -1)).bit_length()" is a faster way to compute byte-lengths
    # conforming to:
    #
    # byte_length = (0 if i == 0 else
    # 		 1 if -128 <= i < 128 else
    # 		 2 if -65536 <= i < 65536 else
    # 		 ...)
    byte_lengths = [((b + 8) >> 3) if b else 0 for b in bit_lengths]

    # https://github.com/fonttools/fonttools/issues/2279
    longWords = any(b > 2 for b in byte_lengths)

    if optimize:
        # Reorder columns such that wider columns come before narrower columns
        mapping = []
        mapping.extend(i for i, b in enumerate(byte_lengths) if b > 2)
        mapping.extend(i for i, b in enumerate(byte_lengths) if b == 2)
        mapping.extend(i for i, b in enumerate(byte_lengths) if b == 1)

        byte_lengths = _reorderItem(byte_lengths, mapping)
        self.VarRegionIndex = _reorderItem(self.VarRegionIndex, mapping)
        self.VarRegionCount = len(self.VarRegionIndex)
        for i in range(len(items)):
            items[i] = _reorderItem(items[i], mapping)

    if longWords:
        self.NumShorts = (
            max((i for i, b in enumerate(byte_lengths) if b > 2), default=-1) + 1
        )
        self.NumShorts |= 0x8000
    else:
        self.NumShorts = (
            max((i for i, b in enumerate(byte_lengths) if b > 1), default=-1) + 1
        )

    self.VarRegionCount = len(self.VarRegionIndex)
    return self


ot.VarData.calculateNumShorts = VarData_calculateNumShorts


def VarData_CalculateNumShorts(self, optimize=True):
    """Deprecated name for VarData_calculateNumShorts() which
    defaults to optimize=True.  Use varData.calculateNumShorts()
    or varData.optimize()."""
    return VarData_calculateNumShorts(self, optimize=optimize)


def VarData_optimize(self):
    return VarData_calculateNumShorts(self, optimize=True)


ot.VarData.optimize = VarData_optimize


def buildVarData(varRegionIndices, items, optimize=True):
    self = ot.VarData()
    self.VarRegionIndex = list(varRegionIndices)
    regionCount = self.VarRegionCount = len(self.VarRegionIndex)
    records = self.Item = []
    if items:
        for item in items:
            assert len(item) == regionCount
            records.append(list(item))
    self.ItemCount = len(self.Item)
    self.calculateNumShorts(optimize=optimize)
    return self


def buildVarStore(varRegionList, varDataList):
    self = ot.VarStore()
    self.Format = 1
    self.VarRegionList = varRegionList
    self.VarData = list(varDataList)
    self.VarDataCount = len(self.VarData)
    return self


def buildMultiVarData(varRegionIndices, items):
    self = ot.MultiVarData()
    self.Format = 1
    self.VarRegionIndex = list(varRegionIndices)
    regionCount = self.VarRegionCount = len(self.VarRegionIndex)
    records = self.Item = []
    if items:
        for item in items:
            assert len(item) == regionCount
            records.append(list(item))
    self.ItemCount = len(self.Item)
    return self


def buildMultiVarStore(varRegionList, multiVarDataList):
    self = ot.MultiVarStore()
    self.Format = 1
    self.SparseVarRegionList = varRegionList
    self.MultiVarData = list(multiVarDataList)
    self.MultiVarDataCount = len(self.MultiVarData)
    return self


# Variation helpers


def buildVarIdxMap(varIdxes, glyphOrder):
    self = ot.VarIdxMap()
    self.mapping = {g: v for g, v in zip(glyphOrder, varIdxes)}
    return self


def buildDeltaSetIndexMap(varIdxes):
    mapping = list(varIdxes)
    if all(i == v for i, v in enumerate(mapping)):
        return None
    self = ot.DeltaSetIndexMap()
    self.mapping = mapping
    self.Format = 1 if len(mapping) > 0xFFFF else 0
    return self


def buildVarDevTable(varIdx):
    self = ot.Device()
    self.DeltaFormat = 0x8000
    self.StartSize = varIdx >> 16
    self.EndSize = varIdx & 0xFFFF
    return self

# === NexusCore/openenv\Lib\site-packages\litellm\llms\custom_llm.py ===
# What is this?
## Handler file for a Custom Chat LLM

"""
- completion
- acompletion
- streaming
- async_streaming
"""

from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Callable,
    Coroutine,
    Iterator,
    Optional,
    Union,
)

import httpx

from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler
from litellm.types.utils import GenericStreamingChunk
from litellm.utils import EmbeddingResponse, ImageResponse, ModelResponse

from .base import BaseLLM

if TYPE_CHECKING:
    from litellm import CustomStreamWrapper


class CustomLLMError(Exception):  # use this for all your exceptions
    def __init__(
        self,
        status_code,
        message,
    ):
        self.status_code = status_code
        self.message = message
        super().__init__(
            self.message
        )  # Call the base class constructor with the parameters it needs


class CustomLLM(BaseLLM):
    def __init__(self) -> None:
        super().__init__()

    def completion(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        api_key,
        logging_obj,
        optional_params: dict,
        acompletion=None,
        litellm_params=None,
        logger_fn=None,
        headers={},
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[HTTPHandler] = None,
    ) -> Union[ModelResponse, "CustomStreamWrapper"]:
        raise CustomLLMError(status_code=500, message="Not implemented yet!")

    def streaming(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        api_key,
        logging_obj,
        optional_params: dict,
        acompletion=None,
        litellm_params=None,
        logger_fn=None,
        headers={},
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[HTTPHandler] = None,
    ) -> Iterator[GenericStreamingChunk]:
        raise CustomLLMError(status_code=500, message="Not implemented yet!")

    async def acompletion(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        api_key,
        logging_obj,
        optional_params: dict,
        acompletion=None,
        litellm_params=None,
        logger_fn=None,
        headers={},
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[AsyncHTTPHandler] = None,
    ) -> Union[
        Coroutine[Any, Any, Union[ModelResponse, "CustomStreamWrapper"]],
        Union[ModelResponse, "CustomStreamWrapper"],
    ]:
        raise CustomLLMError(status_code=500, message="Not implemented yet!")

    async def astreaming(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        api_key,
        logging_obj,
        optional_params: dict,
        acompletion=None,
        litellm_params=None,
        logger_fn=None,
        headers={},
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[AsyncHTTPHandler] = None,
    ) -> AsyncIterator[GenericStreamingChunk]:
        raise CustomLLMError(status_code=500, message="Not implemented yet!")

    def image_generation(
        self,
        model: str,
        prompt: str,
        api_key: Optional[str],
        api_base: Optional[str],
        model_response: ImageResponse,
        optional_params: dict,
        logging_obj: Any,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[HTTPHandler] = None,
    ) -> ImageResponse:
        raise CustomLLMError(status_code=500, message="Not implemented yet!")

    async def aimage_generation(
        self,
        model: str,
        prompt: str,
        model_response: ImageResponse,
        api_key: Optional[
            str
        ],  # dynamically set api_key - https://docs.litellm.ai/docs/set_keys#api_key
        api_base: Optional[
            str
        ],  # dynamically set api_base - https://docs.litellm.ai/docs/set_keys#api_base
        optional_params: dict,
        logging_obj: Any,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[AsyncHTTPHandler] = None,
    ) -> ImageResponse:
        raise CustomLLMError(status_code=500, message="Not implemented yet!")

    def embedding(
        self,
        model: str,
        input: list,
        model_response: EmbeddingResponse,
        print_verbose: Callable,
        logging_obj: Any,
        optional_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        litellm_params=None,
    ) -> EmbeddingResponse:
        raise CustomLLMError(status_code=500, message="Not implemented yet!")

    async def aembedding(
        self,
        model: str,
        input: list,
        model_response: EmbeddingResponse,
        print_verbose: Callable,
        logging_obj: Any,
        optional_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        litellm_params=None,
    ) -> EmbeddingResponse:
        raise CustomLLMError(status_code=500, message="Not implemented yet!")


def custom_chat_llm_router(
    async_fn: bool, stream: Optional[bool], custom_llm: CustomLLM
):
    """
    Routes call to CustomLLM completion/acompletion/streaming/astreaming functions, based on call type

    Validates if response is in expected format
    """
    if async_fn:
        if stream:
            return custom_llm.astreaming
        return custom_llm.acompletion
    if stream:
        return custom_llm.streaming
    return custom_llm.completion

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\datadog\datadog_llm_obs.py ===
"""
Implements logging integration with Datadog's LLM Observability Service


API Reference: https://docs.datadoghq.com/llm_observability/setup/api/?tab=example#api-standards

"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx

import litellm
from litellm._logging import verbose_logger
from litellm.integrations.custom_batch_logger import CustomBatchLogger
from litellm.integrations.datadog.datadog import DataDogLogger
from litellm.litellm_core_utils.prompt_templates.common_utils import (
    handle_any_messages_to_chat_completion_str_messages_conversion,
)
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.types.integrations.datadog_llm_obs import *
from litellm.types.utils import StandardLoggingPayload


class DataDogLLMObsLogger(DataDogLogger, CustomBatchLogger):
    def __init__(self, **kwargs):
        try:
            verbose_logger.debug("DataDogLLMObs: Initializing logger")
            if os.getenv("DD_API_KEY", None) is None:
                raise Exception("DD_API_KEY is not set, set 'DD_API_KEY=<>'")
            if os.getenv("DD_SITE", None) is None:
                raise Exception(
                    "DD_SITE is not set, set 'DD_SITE=<>', example sit = `us5.datadoghq.com`"
                )

            self.async_client = get_async_httpx_client(
                llm_provider=httpxSpecialProvider.LoggingCallback
            )
            self.DD_API_KEY = os.getenv("DD_API_KEY")
            self.DD_SITE = os.getenv("DD_SITE")
            self.intake_url = (
                f"https://api.{self.DD_SITE}/api/intake/llm-obs/v1/trace/spans"
            )

            # testing base url
            dd_base_url = os.getenv("DD_BASE_URL")
            if dd_base_url:
                self.intake_url = f"{dd_base_url}/api/intake/llm-obs/v1/trace/spans"

            asyncio.create_task(self.periodic_flush())
            self.flush_lock = asyncio.Lock()
            self.log_queue: List[LLMObsPayload] = []
            CustomBatchLogger.__init__(self, **kwargs, flush_lock=self.flush_lock)
        except Exception as e:
            verbose_logger.exception(f"DataDogLLMObs: Error initializing - {str(e)}")
            raise e

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            verbose_logger.debug(
                f"DataDogLLMObs: Logging success event for model {kwargs.get('model', 'unknown')}"
            )
            payload = self.create_llm_obs_payload(
                kwargs, response_obj, start_time, end_time
            )
            verbose_logger.debug(f"DataDogLLMObs: Payload: {payload}")
            self.log_queue.append(payload)

            if len(self.log_queue) >= self.batch_size:
                await self.async_send_batch()
        except Exception as e:
            verbose_logger.exception(
                f"DataDogLLMObs: Error logging success event - {str(e)}"
            )

    async def async_send_batch(self):
        try:
            if not self.log_queue:
                return

            verbose_logger.debug(
                f"DataDogLLMObs: Flushing {len(self.log_queue)} events"
            )

            # Prepare the payload
            payload = {
                "data": DDIntakePayload(
                    type="span",
                    attributes=DDSpanAttributes(
                        ml_app=self._get_datadog_service(),
                        tags=[self._get_datadog_tags()],
                        spans=self.log_queue,
                    ),
                ),
            }
            verbose_logger.debug("payload %s", json.dumps(payload, indent=4))
            response = await self.async_client.post(
                url=self.intake_url,
                json=payload,
                headers={
                    "DD-API-KEY": self.DD_API_KEY,
                    "Content-Type": "application/json",
                },
            )

            if response.status_code != 202:
                raise Exception(
                    f"DataDogLLMObs: Unexpected response - status_code: {response.status_code}, text: {response.text}"
                )

            verbose_logger.debug(
                f"DataDogLLMObs: Successfully sent batch - status_code: {response.status_code}"
            )
            self.log_queue.clear()
        except httpx.HTTPStatusError as e:
            verbose_logger.exception(
                f"DataDogLLMObs: Error sending batch - {e.response.text}"
            )
        except Exception as e:
            verbose_logger.exception(f"DataDogLLMObs: Error sending batch - {str(e)}")

    def create_llm_obs_payload(
        self, kwargs: Dict, response_obj: Any, start_time: datetime, end_time: datetime
    ) -> LLMObsPayload:
        standard_logging_payload: Optional[StandardLoggingPayload] = kwargs.get(
            "standard_logging_object"
        )
        if standard_logging_payload is None:
            raise Exception("DataDogLLMObs: standard_logging_object is not set")

        messages = standard_logging_payload["messages"]
        messages = self._ensure_string_content(messages=messages)

        metadata = kwargs.get("litellm_params", {}).get("metadata", {})

        input_meta = InputMeta(
            messages=handle_any_messages_to_chat_completion_str_messages_conversion(
                messages
            )
        )
        output_meta = OutputMeta(messages=self._get_response_messages(response_obj))

        meta = Meta(
            kind="llm",
            input=input_meta,
            output=output_meta,
            metadata=self._get_dd_llm_obs_payload_metadata(standard_logging_payload),
        )

        # Calculate metrics (you may need to adjust these based on available data)
        metrics = LLMMetrics(
            input_tokens=float(standard_logging_payload.get("prompt_tokens", 0)),
            output_tokens=float(standard_logging_payload.get("completion_tokens", 0)),
            total_tokens=float(standard_logging_payload.get("total_tokens", 0)),
        )

        return LLMObsPayload(
            parent_id=metadata.get("parent_id", "undefined"),
            trace_id=metadata.get("trace_id", str(uuid.uuid4())),
            span_id=metadata.get("span_id", str(uuid.uuid4())),
            name=metadata.get("name", "litellm_llm_call"),
            meta=meta,
            start_ns=int(start_time.timestamp() * 1e9),
            duration=int((end_time - start_time).total_seconds() * 1e9),
            metrics=metrics,
            tags=[
                self._get_datadog_tags(standard_logging_object=standard_logging_payload)
            ],
        )

    def _get_response_messages(self, response_obj: Any) -> List[Any]:
        """
        Get the messages from the response object

        for now this handles logging /chat/completions responses
        """
        if isinstance(response_obj, litellm.ModelResponse):
            return [response_obj["choices"][0]["message"].json()]
        return []

    def _ensure_string_content(
        self, messages: Optional[Union[str, List[Any], Dict[Any, Any]]]
    ) -> List[Any]:
        if messages is None:
            return []
        if isinstance(messages, str):
            return [messages]
        elif isinstance(messages, list):
            return [message for message in messages]
        elif isinstance(messages, dict):
            return [str(messages.get("content", ""))]
        return []

    def _get_dd_llm_obs_payload_metadata(
        self, standard_logging_payload: StandardLoggingPayload
    ) -> Dict:
        _metadata = {
            "model_name": standard_logging_payload.get("model", "unknown"),
            "model_provider": standard_logging_payload.get(
                "custom_llm_provider", "unknown"
            ),
        }
        _standard_logging_metadata: dict = (
            dict(standard_logging_payload.get("metadata", {})) or {}
        )
        _metadata.update(_standard_logging_metadata)
        return _metadata

# === NexusCore/openenv\Lib\site-packages\litellm\llms\sagemaker\chat\transformation.py ===
"""
Translate from OpenAI's `/v1/chat/completions` to Sagemaker's `/invocations` API

Called if Sagemaker endpoint supports HF Messages API.

LiteLLM Docs: https://docs.litellm.ai/docs/providers/aws_sagemaker#sagemaker-messages-api
Huggingface Docs: https://huggingface.co/docs/text-generation-inference/en/messages_api
"""

from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union, cast

import httpx
from httpx._models import Headers

from litellm.litellm_core_utils.logging_utils import track_llm_api_timing
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.llms.bedrock.base_aws_llm import BaseAWSLLM
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    _get_httpx_client,
    get_async_httpx_client,
)
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import LlmProviders

from ...openai.chat.gpt_transformation import OpenAIGPTConfig
from ..common_utils import AWSEventStreamDecoder, SagemakerError

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class SagemakerChatConfig(OpenAIGPTConfig, BaseAWSLLM):
    def __init__(self, **kwargs):
        OpenAIGPTConfig.__init__(self, **kwargs)
        BaseAWSLLM.__init__(self, **kwargs)

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, Headers]
    ) -> BaseLLMException:
        return SagemakerError(
            status_code=status_code, message=error_message, headers=headers
        )

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
        aws_region_name = self._get_aws_region_name(
            optional_params=optional_params,
            model=model,
            model_id=None,
        )
        if stream is True:
            api_base = f"https://runtime.sagemaker.{aws_region_name}.amazonaws.com/endpoints/{model}/invocations-response-stream"
        else:
            api_base = f"https://runtime.sagemaker.{aws_region_name}.amazonaws.com/endpoints/{model}/invocations"

        sagemaker_base_url = cast(
            Optional[str], optional_params.get("sagemaker_base_url")
        )
        if sagemaker_base_url is not None:
            api_base = sagemaker_base_url

        return api_base

    def sign_request(
        self,
        headers: dict,
        optional_params: dict,
        request_data: dict,
        api_base: str,
        model: Optional[str] = None,
        stream: Optional[bool] = None,
        fake_stream: Optional[bool] = None,
    ) -> Tuple[dict, Optional[bytes]]:
        return self._sign_request(
            service_name="sagemaker",
            headers=headers,
            optional_params=optional_params,
            request_data=request_data,
            api_base=api_base,
            model=model,
            stream=stream,
            fake_stream=fake_stream,
        )

    @property
    def has_custom_stream_wrapper(self) -> bool:
        return True

    @property
    def supports_stream_param_in_request_body(self) -> bool:
        return False

    @track_llm_api_timing()
    def get_sync_custom_stream_wrapper(
        self,
        model: str,
        custom_llm_provider: str,
        logging_obj: LiteLLMLoggingObj,
        api_base: str,
        headers: dict,
        data: dict,
        messages: list,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        json_mode: Optional[bool] = None,
        signed_json_body: Optional[bytes] = None,
    ) -> CustomStreamWrapper:
        if client is None or isinstance(client, AsyncHTTPHandler):
            client = _get_httpx_client(params={})

        try:
            response = client.post(
                api_base,
                headers=headers,
                data=signed_json_body if signed_json_body is not None else data,
                stream=True,
                logging_obj=logging_obj,
            )
        except httpx.HTTPStatusError as e:
            raise SagemakerError(
                status_code=e.response.status_code, message=e.response.text
            )

        if response.status_code != 200:
            raise SagemakerError(
                status_code=response.status_code, message=response.text
            )

        custom_stream_decoder = AWSEventStreamDecoder(model="", is_messages_api=True)
        completion_stream = custom_stream_decoder.iter_bytes(
            response.iter_bytes(chunk_size=1024)
        )

        streaming_response = CustomStreamWrapper(
            completion_stream=completion_stream,
            model=model,
            custom_llm_provider="sagemaker_chat",
            logging_obj=logging_obj,
        )
        return streaming_response

    @track_llm_api_timing()
    async def get_async_custom_stream_wrapper(
        self,
        model: str,
        custom_llm_provider: str,
        logging_obj: LiteLLMLoggingObj,
        api_base: str,
        headers: dict,
        data: dict,
        messages: list,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        json_mode: Optional[bool] = None,
        signed_json_body: Optional[bytes] = None,
    ) -> CustomStreamWrapper:
        if client is None or isinstance(client, HTTPHandler):
            client = get_async_httpx_client(
                llm_provider=LlmProviders.SAGEMAKER_CHAT, params={}
            )

        try:
            response = await client.post(
                api_base,
                headers=headers,
                data=signed_json_body if signed_json_body is not None else data,
                stream=True,
                logging_obj=logging_obj,
            )
        except httpx.HTTPStatusError as e:
            raise SagemakerError(
                status_code=e.response.status_code, message=e.response.text
            )

        if response.status_code != 200:
            raise SagemakerError(
                status_code=response.status_code, message=response.text
            )

        custom_stream_decoder = AWSEventStreamDecoder(model="", is_messages_api=True)
        completion_stream = custom_stream_decoder.aiter_bytes(
            response.aiter_bytes(chunk_size=1024)
        )

        streaming_response = CustomStreamWrapper(
            completion_stream=completion_stream,
            model=model,
            custom_llm_provider="sagemaker_chat",
            logging_obj=logging_obj,
        )
        return streaming_response

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\batches\handler.py ===
import json
from typing import Any, Coroutine, Dict, Optional, Union

import httpx

import litellm
from litellm.llms.custom_httpx.http_handler import (
    _get_httpx_client,
    get_async_httpx_client,
)
from litellm.llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import VertexLLM
from litellm.types.llms.openai import CreateBatchRequest
from litellm.types.llms.vertex_ai import (
    VERTEX_CREDENTIALS_TYPES,
    VertexAIBatchPredictionJob,
)
from litellm.types.utils import LiteLLMBatch

from .transformation import VertexAIBatchTransformation


class VertexAIBatchPrediction(VertexLLM):
    def __init__(self, gcs_bucket_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gcs_bucket_name = gcs_bucket_name

    def create_batch(
        self,
        _is_async: bool,
        create_batch_data: CreateBatchRequest,
        api_base: Optional[str],
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES],
        vertex_project: Optional[str],
        vertex_location: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
    ) -> Union[LiteLLMBatch, Coroutine[Any, Any, LiteLLMBatch]]:
        sync_handler = _get_httpx_client()

        access_token, project_id = self._ensure_access_token(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider="vertex_ai",
        )

        default_api_base = self.create_vertex_batch_url(
            vertex_location=vertex_location or "us-central1",
            vertex_project=vertex_project or project_id,
        )

        if len(default_api_base.split(":")) > 1:
            endpoint = default_api_base.split(":")[-1]
        else:
            endpoint = ""

        _, api_base = self._check_custom_proxy(
            api_base=api_base,
            custom_llm_provider="vertex_ai",
            gemini_api_key=None,
            endpoint=endpoint,
            stream=None,
            auth_header=None,
            url=default_api_base,
        )

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {access_token}",
        }

        vertex_batch_request: VertexAIBatchPredictionJob = VertexAIBatchTransformation.transform_openai_batch_request_to_vertex_ai_batch_request(
            request=create_batch_data
        )

        if _is_async is True:
            return self._async_create_batch(
                vertex_batch_request=vertex_batch_request,
                api_base=api_base,
                headers=headers,
            )

        response = sync_handler.post(
            url=api_base,
            headers=headers,
            data=json.dumps(vertex_batch_request),
        )

        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} {response.text}")

        _json_response = response.json()
        vertex_batch_response = VertexAIBatchTransformation.transform_vertex_ai_batch_response_to_openai_batch_response(
            response=_json_response
        )
        return vertex_batch_response

    async def _async_create_batch(
        self,
        vertex_batch_request: VertexAIBatchPredictionJob,
        api_base: str,
        headers: Dict[str, str],
    ) -> LiteLLMBatch:
        client = get_async_httpx_client(
            llm_provider=litellm.LlmProviders.VERTEX_AI,
        )
        response = await client.post(
            url=api_base,
            headers=headers,
            data=json.dumps(vertex_batch_request),
        )
        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} {response.text}")

        _json_response = response.json()
        vertex_batch_response = VertexAIBatchTransformation.transform_vertex_ai_batch_response_to_openai_batch_response(
            response=_json_response
        )
        return vertex_batch_response

    def create_vertex_batch_url(
        self,
        vertex_location: str,
        vertex_project: str,
    ) -> str:
        """Return the base url for the vertex garden models"""
        #  POST https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/batchPredictionJobs
        return f"https://{vertex_location}-aiplatform.googleapis.com/v1/projects/{vertex_project}/locations/{vertex_location}/batchPredictionJobs"

    def retrieve_batch(
        self,
        _is_async: bool,
        batch_id: str,
        api_base: Optional[str],
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES],
        vertex_project: Optional[str],
        vertex_location: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
    ) -> Union[LiteLLMBatch, Coroutine[Any, Any, LiteLLMBatch]]:
        sync_handler = _get_httpx_client()

        access_token, project_id = self._ensure_access_token(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider="vertex_ai",
        )

        default_api_base = self.create_vertex_batch_url(
            vertex_location=vertex_location or "us-central1",
            vertex_project=vertex_project or project_id,
        )

        # Append batch_id to the URL
        default_api_base = f"{default_api_base}/{batch_id}"

        if len(default_api_base.split(":")) > 1:
            endpoint = default_api_base.split(":")[-1]
        else:
            endpoint = ""

        _, api_base = self._check_custom_proxy(
            api_base=api_base,
            custom_llm_provider="vertex_ai",
            gemini_api_key=None,
            endpoint=endpoint,
            stream=None,
            auth_header=None,
            url=default_api_base,
        )

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {access_token}",
        }

        if _is_async is True:
            return self._async_retrieve_batch(
                api_base=api_base,
                headers=headers,
            )

        response = sync_handler.get(
            url=api_base,
            headers=headers,
        )

        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} {response.text}")

        _json_response = response.json()
        vertex_batch_response = VertexAIBatchTransformation.transform_vertex_ai_batch_response_to_openai_batch_response(
            response=_json_response
        )
        return vertex_batch_response

    async def _async_retrieve_batch(
        self,
        api_base: str,
        headers: Dict[str, str],
    ) -> LiteLLMBatch:
        client = get_async_httpx_client(
            llm_provider=litellm.LlmProviders.VERTEX_AI,
        )
        response = await client.get(
            url=api_base,
            headers=headers,
        )
        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} {response.text}")

        _json_response = response.json()
        vertex_batch_response = VertexAIBatchTransformation.transform_vertex_ai_batch_response_to_openai_batch_response(
            response=_json_response
        )
        return vertex_batch_response

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\vertex_ai_partner_models\main.py ===
# What is this?
## API Handler for calling Vertex AI Partner Models
from typing import Callable, Optional, Union

import httpx  # type: ignore

import litellm
from litellm import LlmProviders
from litellm.types.llms.vertex_ai import VertexPartnerProvider
from litellm.utils import ModelResponse

from ...custom_httpx.llm_http_handler import BaseLLMHTTPHandler
from ..vertex_llm_base import VertexBase

base_llm_http_handler = BaseLLMHTTPHandler()


class VertexAIError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        self.request = httpx.Request(
            method="POST", url=" https://cloud.google.com/vertex-ai/"
        )
        self.response = httpx.Response(status_code=status_code, request=self.request)
        super().__init__(
            self.message
        )  # Call the base class constructor with the parameters it needs


class VertexAIPartnerModels(VertexBase):
    def __init__(self) -> None:
        pass

    def completion(
        self,
        model: str,
        messages: list,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        logging_obj,
        api_base: Optional[str],
        optional_params: dict,
        custom_prompt_dict: dict,
        headers: Optional[dict],
        timeout: Union[float, httpx.Timeout],
        litellm_params: dict,
        vertex_project=None,
        vertex_location=None,
        vertex_credentials=None,
        logger_fn=None,
        acompletion: bool = False,
        client=None,
    ):
        try:
            import vertexai

            from litellm.llms.anthropic.chat import AnthropicChatCompletion
            from litellm.llms.codestral.completion.handler import (
                CodestralTextCompletion,
            )
            from litellm.llms.openai_like.chat.handler import OpenAILikeChatHandler
            from litellm.llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import (
                VertexLLM,
            )
        except Exception as e:
            raise VertexAIError(
                status_code=400,
                message=f"""vertexai import failed please run `pip install -U "google-cloud-aiplatform>=1.38"`. Got error: {e}""",
            )

        if not (
            hasattr(vertexai, "preview") or hasattr(vertexai.preview, "language_models")
        ):
            raise VertexAIError(
                status_code=400,
                message="""Upgrade vertex ai. Run `pip install "google-cloud-aiplatform>=1.38"`""",
            )
        try:
            vertex_httpx_logic = VertexLLM()

            access_token, project_id = vertex_httpx_logic._ensure_access_token(
                credentials=vertex_credentials,
                project_id=vertex_project,
                custom_llm_provider="vertex_ai",
            )

            openai_like_chat_completions = OpenAILikeChatHandler()
            codestral_fim_completions = CodestralTextCompletion()
            anthropic_chat_completions = AnthropicChatCompletion()

            ## CONSTRUCT API BASE
            stream: bool = optional_params.get("stream", False) or False

            optional_params["stream"] = stream

            if "llama" in model:
                partner = VertexPartnerProvider.llama
            elif "mistral" in model or "codestral" in model:
                partner = VertexPartnerProvider.mistralai
            elif "jamba" in model:
                partner = VertexPartnerProvider.ai21
            elif "claude" in model:
                partner = VertexPartnerProvider.claude
            else:
                raise ValueError(f"Unknown partner model: {model}")

            api_base = self.get_complete_vertex_url(
                custom_api_base=api_base,
                vertex_location=vertex_location,
                vertex_project=vertex_project,
                project_id=project_id,
                partner=partner,
                stream=stream,
                model=model,
            )

            if "codestral" in model or "mistral" in model:
                model = model.split("@")[0]

            if "codestral" in model and litellm_params.get("text_completion") is True:
                optional_params["model"] = model
                text_completion_model_response = litellm.TextCompletionResponse(
                    stream=stream
                )
                return codestral_fim_completions.completion(
                    model=model,
                    messages=messages,
                    api_base=api_base,
                    api_key=access_token,
                    custom_prompt_dict=custom_prompt_dict,
                    model_response=text_completion_model_response,
                    print_verbose=print_verbose,
                    logging_obj=logging_obj,
                    optional_params=optional_params,
                    acompletion=acompletion,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    timeout=timeout,
                    encoding=encoding,
                )
            elif "claude" in model:
                if headers is None:
                    headers = {}
                headers.update({"Authorization": "Bearer {}".format(access_token)})

                optional_params.update(
                    {
                        "anthropic_version": "vertex-2023-10-16",
                        "is_vertex_request": True,
                    }
                )

                return anthropic_chat_completions.completion(
                    model=model,
                    messages=messages,
                    api_base=api_base,
                    acompletion=acompletion,
                    custom_prompt_dict=litellm.custom_prompt_dict,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    encoding=encoding,  # for calculating input/output tokens
                    api_key=access_token,
                    logging_obj=logging_obj,
                    headers=headers,
                    timeout=timeout,
                    client=client,
                    custom_llm_provider=LlmProviders.VERTEX_AI.value,
                )
            elif "llama" in model:
                return base_llm_http_handler.completion(
                    model=model,
                    stream=stream,
                    messages=messages,
                    acompletion=acompletion,
                    api_base=api_base,
                    model_response=model_response,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    custom_llm_provider="vertex_ai",
                    timeout=timeout,
                    headers=headers,
                    encoding=encoding,
                    api_key=access_token,
                    logging_obj=logging_obj,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
                    client=client,
                )
            return openai_like_chat_completions.completion(
                model=model,
                messages=messages,
                api_base=api_base,
                api_key=access_token,
                custom_prompt_dict=custom_prompt_dict,
                model_response=model_response,
                print_verbose=print_verbose,
                logging_obj=logging_obj,
                optional_params=optional_params,
                acompletion=acompletion,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                client=client,
                timeout=timeout,
                encoding=encoding,
                custom_llm_provider="vertex_ai",
                custom_endpoint=True,
            )

        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            raise VertexAIError(status_code=500, message=str(e))

# === NexusCore/openenv\Lib\site-packages\markdown_it\rules_block\reference.py ===
import logging

from ..common.utils import charCodeAt, isSpace, normalizeReference
from .state_block import StateBlock

LOGGER = logging.getLogger(__name__)


def reference(state: StateBlock, startLine: int, _endLine: int, silent: bool) -> bool:
    LOGGER.debug(
        "entering reference: %s, %s, %s, %s", state, startLine, _endLine, silent
    )

    lines = 0
    pos = state.bMarks[startLine] + state.tShift[startLine]
    maximum = state.eMarks[startLine]
    nextLine = startLine + 1

    if state.is_code_block(startLine):
        return False

    if state.src[pos] != "[":
        return False

    # Simple check to quickly interrupt scan on [link](url) at the start of line.
    # Can be useful on practice: https:#github.com/markdown-it/markdown-it/issues/54
    while pos < maximum:
        # /* ] */  /* \ */  /* : */
        if state.src[pos] == "]" and state.src[pos - 1] != "\\":
            if pos + 1 == maximum:
                return False
            if state.src[pos + 1] != ":":
                return False
            break
        pos += 1

    endLine = state.lineMax

    # jump line-by-line until empty one or EOF
    terminatorRules = state.md.block.ruler.getRules("reference")

    oldParentType = state.parentType
    state.parentType = "reference"

    while nextLine < endLine and not state.isEmpty(nextLine):
        # this would be a code block normally, but after paragraph
        # it's considered a lazy continuation regardless of what's there
        if state.sCount[nextLine] - state.blkIndent > 3:
            nextLine += 1
            continue

        # quirk for blockquotes, this line should already be checked by that rule
        if state.sCount[nextLine] < 0:
            nextLine += 1
            continue

        # Some tags can terminate paragraph without empty line.
        terminate = False
        for terminatorRule in terminatorRules:
            if terminatorRule(state, nextLine, endLine, True):
                terminate = True
                break

        if terminate:
            break

        nextLine += 1

    string = state.getLines(startLine, nextLine, state.blkIndent, False).strip()
    maximum = len(string)

    labelEnd = None
    pos = 1
    while pos < maximum:
        ch = charCodeAt(string, pos)
        if ch == 0x5B:  # /* [ */
            return False
        elif ch == 0x5D:  # /* ] */
            labelEnd = pos
            break
        elif ch == 0x0A:  # /* \n */
            lines += 1
        elif ch == 0x5C:  # /* \ */
            pos += 1
            if pos < maximum and charCodeAt(string, pos) == 0x0A:
                lines += 1
        pos += 1

    if (
        labelEnd is None or labelEnd < 0 or charCodeAt(string, labelEnd + 1) != 0x3A
    ):  # /* : */
        return False

    # [label]:   destination   'title'
    #         ^^^ skip optional whitespace here
    pos = labelEnd + 2
    while pos < maximum:
        ch = charCodeAt(string, pos)
        if ch == 0x0A:
            lines += 1
        elif isSpace(ch):
            pass
        else:
            break
        pos += 1

    # [label]:   destination   'title'
    #            ^^^^^^^^^^^ parse this
    res = state.md.helpers.parseLinkDestination(string, pos, maximum)
    if not res.ok:
        return False

    href = state.md.normalizeLink(res.str)
    if not state.md.validateLink(href):
        return False

    pos = res.pos
    lines += res.lines

    # save cursor state, we could require to rollback later
    destEndPos = pos
    destEndLineNo = lines

    # [label]:   destination   'title'
    #                       ^^^ skipping those spaces
    start = pos
    while pos < maximum:
        ch = charCodeAt(string, pos)
        if ch == 0x0A:
            lines += 1
        elif isSpace(ch):
            pass
        else:
            break
        pos += 1

    # [label]:   destination   'title'
    #                          ^^^^^^^ parse this
    res = state.md.helpers.parseLinkTitle(string, pos, maximum)
    if pos < maximum and start != pos and res.ok:
        title = res.str
        pos = res.pos
        lines += res.lines
    else:
        title = ""
        pos = destEndPos
        lines = destEndLineNo

    # skip trailing spaces until the rest of the line
    while pos < maximum:
        ch = charCodeAt(string, pos)
        if not isSpace(ch):
            break
        pos += 1

    if pos < maximum and charCodeAt(string, pos) != 0x0A and title:
        # garbage at the end of the line after title,
        # but it could still be a valid reference if we roll back
        title = ""
        pos = destEndPos
        lines = destEndLineNo
        while pos < maximum:
            ch = charCodeAt(string, pos)
            if not isSpace(ch):
                break
            pos += 1

    if pos < maximum and charCodeAt(string, pos) != 0x0A:
        # garbage at the end of the line
        return False

    label = normalizeReference(string[1:labelEnd])
    if not label:
        # CommonMark 0.20 disallows empty labels
        return False

    # Reference can not terminate anything. This check is for safety only.
    if silent:
        return True

    if "references" not in state.env:
        state.env["references"] = {}

    state.line = startLine + lines + 1

    # note, this is not part of markdown-it JS, but is useful for renderers
    if state.md.options.get("inline_definitions", False):
        token = state.push("definition", "", 0)
        token.meta = {
            "id": label,
            "title": title,
            "url": href,
            "label": string[1:labelEnd],
        }
        token.map = [startLine, state.line]

    if label not in state.env["references"]:
        state.env["references"][label] = {
            "title": title,
            "href": href,
            "map": [startLine, state.line],
        }
    else:
        state.env.setdefault("duplicate_refs", []).append(
            {
                "title": title,
                "href": href,
                "label": label,
                "map": [startLine, state.line],
            }
        )

    state.parentType = oldParentType

    return True

# === NexusCore/openenv\Lib\site-packages\numpy\fft\__init__.py ===
"""
Discrete Fourier Transform
==========================

.. currentmodule:: numpy.fft

The SciPy module `scipy.fft` is a more comprehensive superset
of `numpy.fft`, which includes only a basic set of routines.

Standard FFTs
-------------

.. autosummary::
   :toctree: generated/

   fft       Discrete Fourier transform.
   ifft      Inverse discrete Fourier transform.
   fft2      Discrete Fourier transform in two dimensions.
   ifft2     Inverse discrete Fourier transform in two dimensions.
   fftn      Discrete Fourier transform in N-dimensions.
   ifftn     Inverse discrete Fourier transform in N dimensions.

Real FFTs
---------

.. autosummary::
   :toctree: generated/

   rfft      Real discrete Fourier transform.
   irfft     Inverse real discrete Fourier transform.
   rfft2     Real discrete Fourier transform in two dimensions.
   irfft2    Inverse real discrete Fourier transform in two dimensions.
   rfftn     Real discrete Fourier transform in N dimensions.
   irfftn    Inverse real discrete Fourier transform in N dimensions.

Hermitian FFTs
--------------

.. autosummary::
   :toctree: generated/

   hfft      Hermitian discrete Fourier transform.
   ihfft     Inverse Hermitian discrete Fourier transform.

Helper routines
---------------

.. autosummary::
   :toctree: generated/

   fftfreq   Discrete Fourier Transform sample frequencies.
   rfftfreq  DFT sample frequencies (for usage with rfft, irfft).
   fftshift  Shift zero-frequency component to center of spectrum.
   ifftshift Inverse of fftshift.


Background information
----------------------

Fourier analysis is fundamentally a method for expressing a function as a
sum of periodic components, and for recovering the function from those
components.  When both the function and its Fourier transform are
replaced with discretized counterparts, it is called the discrete Fourier
transform (DFT).  The DFT has become a mainstay of numerical computing in
part because of a very fast algorithm for computing it, called the Fast
Fourier Transform (FFT), which was known to Gauss (1805) and was brought
to light in its current form by Cooley and Tukey [CT]_.  Press et al. [NR]_
provide an accessible introduction to Fourier analysis and its
applications.

Because the discrete Fourier transform separates its input into
components that contribute at discrete frequencies, it has a great number
of applications in digital signal processing, e.g., for filtering, and in
this context the discretized input to the transform is customarily
referred to as a *signal*, which exists in the *time domain*.  The output
is called a *spectrum* or *transform* and exists in the *frequency
domain*.

Implementation details
----------------------

There are many ways to define the DFT, varying in the sign of the
exponent, normalization, etc.  In this implementation, the DFT is defined
as

.. math::
   A_k =  \\sum_{m=0}^{n-1} a_m \\exp\\left\\{-2\\pi i{mk \\over n}\\right\\}
   \\qquad k = 0,\\ldots,n-1.

The DFT is in general defined for complex inputs and outputs, and a
single-frequency component at linear frequency :math:`f` is
represented by a complex exponential
:math:`a_m = \\exp\\{2\\pi i\\,f m\\Delta t\\}`, where :math:`\\Delta t`
is the sampling interval.

The values in the result follow so-called "standard" order: If ``A =
fft(a, n)``, then ``A[0]`` contains the zero-frequency term (the sum of
the signal), which is always purely real for real inputs. Then ``A[1:n/2]``
contains the positive-frequency terms, and ``A[n/2+1:]`` contains the
negative-frequency terms, in order of decreasingly negative frequency.
For an even number of input points, ``A[n/2]`` represents both positive and
negative Nyquist frequency, and is also purely real for real input.  For
an odd number of input points, ``A[(n-1)/2]`` contains the largest positive
frequency, while ``A[(n+1)/2]`` contains the largest negative frequency.
The routine ``np.fft.fftfreq(n)`` returns an array giving the frequencies
of corresponding elements in the output.  The routine
``np.fft.fftshift(A)`` shifts transforms and their frequencies to put the
zero-frequency components in the middle, and ``np.fft.ifftshift(A)`` undoes
that shift.

When the input `a` is a time-domain signal and ``A = fft(a)``, ``np.abs(A)``
is its amplitude spectrum and ``np.abs(A)**2`` is its power spectrum.
The phase spectrum is obtained by ``np.angle(A)``.

The inverse DFT is defined as

.. math::
   a_m = \\frac{1}{n}\\sum_{k=0}^{n-1}A_k\\exp\\left\\{2\\pi i{mk\\over n}\\right\\}
   \\qquad m = 0,\\ldots,n-1.

It differs from the forward transform by the sign of the exponential
argument and the default normalization by :math:`1/n`.

Type Promotion
--------------

`numpy.fft` promotes ``float32`` and ``complex64`` arrays to ``float64`` and
``complex128`` arrays respectively. For an FFT implementation that does not
promote input arrays, see `scipy.fftpack`.

Normalization
-------------

The argument ``norm`` indicates which direction of the pair of direct/inverse
transforms is scaled and with what normalization factor.
The default normalization (``"backward"``) has the direct (forward) transforms
unscaled and the inverse (backward) transforms scaled by :math:`1/n`. It is
possible to obtain unitary transforms by setting the keyword argument ``norm``
to ``"ortho"`` so that both direct and inverse transforms are scaled by
:math:`1/\\sqrt{n}`. Finally, setting the keyword argument ``norm`` to
``"forward"`` has the direct transforms scaled by :math:`1/n` and the inverse
transforms unscaled (i.e. exactly opposite to the default ``"backward"``).
`None` is an alias of the default option ``"backward"`` for backward
compatibility.

Real and Hermitian transforms
-----------------------------

When the input is purely real, its transform is Hermitian, i.e., the
component at frequency :math:`f_k` is the complex conjugate of the
component at frequency :math:`-f_k`, which means that for real
inputs there is no information in the negative frequency components that
is not already available from the positive frequency components.
The family of `rfft` functions is
designed to operate on real inputs, and exploits this symmetry by
computing only the positive frequency components, up to and including the
Nyquist frequency.  Thus, ``n`` input points produce ``n/2+1`` complex
output points.  The inverses of this family assumes the same symmetry of
its input, and for an output of ``n`` points uses ``n/2+1`` input points.

Correspondingly, when the spectrum is purely real, the signal is
Hermitian.  The `hfft` family of functions exploits this symmetry by
using ``n/2+1`` complex points in the input (time) domain for ``n`` real
points in the frequency domain.

In higher dimensions, FFTs are used, e.g., for image analysis and
filtering.  The computational efficiency of the FFT means that it can
also be a faster way to compute large convolutions, using the property
that a convolution in the time domain is equivalent to a point-by-point
multiplication in the frequency domain.

Higher dimensions
-----------------

In two dimensions, the DFT is defined as

.. math::
   A_{kl} =  \\sum_{m=0}^{M-1} \\sum_{n=0}^{N-1}
   a_{mn}\\exp\\left\\{-2\\pi i \\left({mk\\over M}+{nl\\over N}\\right)\\right\\}
   \\qquad k = 0, \\ldots, M-1;\\quad l = 0, \\ldots, N-1,

which extends in the obvious way to higher dimensions, and the inverses
in higher dimensions also extend in the same way.

References
----------

.. [CT] Cooley, James W., and John W. Tukey, 1965, "An algorithm for the
        machine calculation of complex Fourier series," *Math. Comput.*
        19: 297-301.

.. [NR] Press, W., Teukolsky, S., Vetterline, W.T., and Flannery, B.P.,
        2007, *Numerical Recipes: The Art of Scientific Computing*, ch.
        12-13.  Cambridge Univ. Press, Cambridge, UK.

Examples
--------

For examples, see the various functions.

"""

# TODO: `numpy.fft.helper`` was deprecated in NumPy 2.0. It should
# be deleted once downstream libraries move to `numpy.fft`.
from . import _helper, _pocketfft, helper
from ._helper import *
from ._pocketfft import *

__all__ = _pocketfft.__all__.copy()  # noqa: PLE0605
__all__ += _helper.__all__

from numpy._pytesttester import PytestTester

test = PytestTester(__name__)
del PytestTester

# === NexusCore/openenv\Lib\site-packages\openai\resources\__init__.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from .beta import (
    Beta,
    AsyncBeta,
    BetaWithRawResponse,
    AsyncBetaWithRawResponse,
    BetaWithStreamingResponse,
    AsyncBetaWithStreamingResponse,
)
from .chat import (
    Chat,
    AsyncChat,
    ChatWithRawResponse,
    AsyncChatWithRawResponse,
    ChatWithStreamingResponse,
    AsyncChatWithStreamingResponse,
)
from .audio import (
    Audio,
    AsyncAudio,
    AudioWithRawResponse,
    AsyncAudioWithRawResponse,
    AudioWithStreamingResponse,
    AsyncAudioWithStreamingResponse,
)
from .evals import (
    Evals,
    AsyncEvals,
    EvalsWithRawResponse,
    AsyncEvalsWithRawResponse,
    EvalsWithStreamingResponse,
    AsyncEvalsWithStreamingResponse,
)
from .files import (
    Files,
    AsyncFiles,
    FilesWithRawResponse,
    AsyncFilesWithRawResponse,
    FilesWithStreamingResponse,
    AsyncFilesWithStreamingResponse,
)
from .images import (
    Images,
    AsyncImages,
    ImagesWithRawResponse,
    AsyncImagesWithRawResponse,
    ImagesWithStreamingResponse,
    AsyncImagesWithStreamingResponse,
)
from .models import (
    Models,
    AsyncModels,
    ModelsWithRawResponse,
    AsyncModelsWithRawResponse,
    ModelsWithStreamingResponse,
    AsyncModelsWithStreamingResponse,
)
from .batches import (
    Batches,
    AsyncBatches,
    BatchesWithRawResponse,
    AsyncBatchesWithRawResponse,
    BatchesWithStreamingResponse,
    AsyncBatchesWithStreamingResponse,
)
from .uploads import (
    Uploads,
    AsyncUploads,
    UploadsWithRawResponse,
    AsyncUploadsWithRawResponse,
    UploadsWithStreamingResponse,
    AsyncUploadsWithStreamingResponse,
)
from .containers import (
    Containers,
    AsyncContainers,
    ContainersWithRawResponse,
    AsyncContainersWithRawResponse,
    ContainersWithStreamingResponse,
    AsyncContainersWithStreamingResponse,
)
from .embeddings import (
    Embeddings,
    AsyncEmbeddings,
    EmbeddingsWithRawResponse,
    AsyncEmbeddingsWithRawResponse,
    EmbeddingsWithStreamingResponse,
    AsyncEmbeddingsWithStreamingResponse,
)
from .completions import (
    Completions,
    AsyncCompletions,
    CompletionsWithRawResponse,
    AsyncCompletionsWithRawResponse,
    CompletionsWithStreamingResponse,
    AsyncCompletionsWithStreamingResponse,
)
from .fine_tuning import (
    FineTuning,
    AsyncFineTuning,
    FineTuningWithRawResponse,
    AsyncFineTuningWithRawResponse,
    FineTuningWithStreamingResponse,
    AsyncFineTuningWithStreamingResponse,
)
from .moderations import (
    Moderations,
    AsyncModerations,
    ModerationsWithRawResponse,
    AsyncModerationsWithRawResponse,
    ModerationsWithStreamingResponse,
    AsyncModerationsWithStreamingResponse,
)
from .vector_stores import (
    VectorStores,
    AsyncVectorStores,
    VectorStoresWithRawResponse,
    AsyncVectorStoresWithRawResponse,
    VectorStoresWithStreamingResponse,
    AsyncVectorStoresWithStreamingResponse,
)

__all__ = [
    "Completions",
    "AsyncCompletions",
    "CompletionsWithRawResponse",
    "AsyncCompletionsWithRawResponse",
    "CompletionsWithStreamingResponse",
    "AsyncCompletionsWithStreamingResponse",
    "Chat",
    "AsyncChat",
    "ChatWithRawResponse",
    "AsyncChatWithRawResponse",
    "ChatWithStreamingResponse",
    "AsyncChatWithStreamingResponse",
    "Embeddings",
    "AsyncEmbeddings",
    "EmbeddingsWithRawResponse",
    "AsyncEmbeddingsWithRawResponse",
    "EmbeddingsWithStreamingResponse",
    "AsyncEmbeddingsWithStreamingResponse",
    "Files",
    "AsyncFiles",
    "FilesWithRawResponse",
    "AsyncFilesWithRawResponse",
    "FilesWithStreamingResponse",
    "AsyncFilesWithStreamingResponse",
    "Images",
    "AsyncImages",
    "ImagesWithRawResponse",
    "AsyncImagesWithRawResponse",
    "ImagesWithStreamingResponse",
    "AsyncImagesWithStreamingResponse",
    "Audio",
    "AsyncAudio",
    "AudioWithRawResponse",
    "AsyncAudioWithRawResponse",
    "AudioWithStreamingResponse",
    "AsyncAudioWithStreamingResponse",
    "Moderations",
    "AsyncModerations",
    "ModerationsWithRawResponse",
    "AsyncModerationsWithRawResponse",
    "ModerationsWithStreamingResponse",
    "AsyncModerationsWithStreamingResponse",
    "Models",
    "AsyncModels",
    "ModelsWithRawResponse",
    "AsyncModelsWithRawResponse",
    "ModelsWithStreamingResponse",
    "AsyncModelsWithStreamingResponse",
    "FineTuning",
    "AsyncFineTuning",
    "FineTuningWithRawResponse",
    "AsyncFineTuningWithRawResponse",
    "FineTuningWithStreamingResponse",
    "AsyncFineTuningWithStreamingResponse",
    "VectorStores",
    "AsyncVectorStores",
    "VectorStoresWithRawResponse",
    "AsyncVectorStoresWithRawResponse",
    "VectorStoresWithStreamingResponse",
    "AsyncVectorStoresWithStreamingResponse",
    "Beta",
    "AsyncBeta",
    "BetaWithRawResponse",
    "AsyncBetaWithRawResponse",
    "BetaWithStreamingResponse",
    "AsyncBetaWithStreamingResponse",
    "Batches",
    "AsyncBatches",
    "BatchesWithRawResponse",
    "AsyncBatchesWithRawResponse",
    "BatchesWithStreamingResponse",
    "AsyncBatchesWithStreamingResponse",
    "Uploads",
    "AsyncUploads",
    "UploadsWithRawResponse",
    "AsyncUploadsWithRawResponse",
    "UploadsWithStreamingResponse",
    "AsyncUploadsWithStreamingResponse",
    "Evals",
    "AsyncEvals",
    "EvalsWithRawResponse",
    "AsyncEvalsWithRawResponse",
    "EvalsWithStreamingResponse",
    "AsyncEvalsWithStreamingResponse",
    "Containers",
    "AsyncContainers",
    "ContainersWithRawResponse",
    "AsyncContainersWithRawResponse",
    "ContainersWithStreamingResponse",
    "AsyncContainersWithStreamingResponse",
]

# === NexusCore/myenv\Lib\site-packages\pip\_internal\locations\_sysconfig.py ===
import logging
import os
import sys
import sysconfig
import typing

from pip._internal.exceptions import InvalidSchemeCombination, UserInstallationInvalid
from pip._internal.models.scheme import SCHEME_KEYS, Scheme
from pip._internal.utils.virtualenv import running_under_virtualenv

from .base import change_root, get_major_minor_version, is_osx_framework

logger = logging.getLogger(__name__)


# Notes on _infer_* functions.
# Unfortunately ``get_default_scheme()`` didn't exist before 3.10, so there's no
# way to ask things like "what is the '_prefix' scheme on this platform". These
# functions try to answer that with some heuristics while accounting for ad-hoc
# platforms not covered by CPython's default sysconfig implementation. If the
# ad-hoc implementation does not fully implement sysconfig, we'll fall back to
# a POSIX scheme.

_AVAILABLE_SCHEMES = set(sysconfig.get_scheme_names())

_PREFERRED_SCHEME_API = getattr(sysconfig, "get_preferred_scheme", None)


def _should_use_osx_framework_prefix() -> bool:
    """Check for Apple's ``osx_framework_library`` scheme.

    Python distributed by Apple's Command Line Tools has this special scheme
    that's used when:

    * This is a framework build.
    * We are installing into the system prefix.

    This does not account for ``pip install --prefix`` (also means we're not
    installing to the system prefix), which should use ``posix_prefix``, but
    logic here means ``_infer_prefix()`` outputs ``osx_framework_library``. But
    since ``prefix`` is not available for ``sysconfig.get_default_scheme()``,
    which is the stdlib replacement for ``_infer_prefix()``, presumably Apple
    wouldn't be able to magically switch between ``osx_framework_library`` and
    ``posix_prefix``. ``_infer_prefix()`` returning ``osx_framework_library``
    means its behavior is consistent whether we use the stdlib implementation
    or our own, and we deal with this special case in ``get_scheme()`` instead.
    """
    return (
        "osx_framework_library" in _AVAILABLE_SCHEMES
        and not running_under_virtualenv()
        and is_osx_framework()
    )


def _infer_prefix() -> str:
    """Try to find a prefix scheme for the current platform.

    This tries:

    * A special ``osx_framework_library`` for Python distributed by Apple's
      Command Line Tools, when not running in a virtual environment.
    * Implementation + OS, used by PyPy on Windows (``pypy_nt``).
    * Implementation without OS, used by PyPy on POSIX (``pypy``).
    * OS + "prefix", used by CPython on POSIX (``posix_prefix``).
    * Just the OS name, used by CPython on Windows (``nt``).

    If none of the above works, fall back to ``posix_prefix``.
    """
    if _PREFERRED_SCHEME_API:
        return _PREFERRED_SCHEME_API("prefix")
    if _should_use_osx_framework_prefix():
        return "osx_framework_library"
    implementation_suffixed = f"{sys.implementation.name}_{os.name}"
    if implementation_suffixed in _AVAILABLE_SCHEMES:
        return implementation_suffixed
    if sys.implementation.name in _AVAILABLE_SCHEMES:
        return sys.implementation.name
    suffixed = f"{os.name}_prefix"
    if suffixed in _AVAILABLE_SCHEMES:
        return suffixed
    if os.name in _AVAILABLE_SCHEMES:  # On Windows, prefx is just called "nt".
        return os.name
    return "posix_prefix"


def _infer_user() -> str:
    """Try to find a user scheme for the current platform."""
    if _PREFERRED_SCHEME_API:
        return _PREFERRED_SCHEME_API("user")
    if is_osx_framework() and not running_under_virtualenv():
        suffixed = "osx_framework_user"
    else:
        suffixed = f"{os.name}_user"
    if suffixed in _AVAILABLE_SCHEMES:
        return suffixed
    if "posix_user" not in _AVAILABLE_SCHEMES:  # User scheme unavailable.
        raise UserInstallationInvalid()
    return "posix_user"


def _infer_home() -> str:
    """Try to find a home for the current platform."""
    if _PREFERRED_SCHEME_API:
        return _PREFERRED_SCHEME_API("home")
    suffixed = f"{os.name}_home"
    if suffixed in _AVAILABLE_SCHEMES:
        return suffixed
    return "posix_home"


# Update these keys if the user sets a custom home.
_HOME_KEYS = [
    "installed_base",
    "base",
    "installed_platbase",
    "platbase",
    "prefix",
    "exec_prefix",
]
if sysconfig.get_config_var("userbase") is not None:
    _HOME_KEYS.append("userbase")


def get_scheme(
    dist_name: str,
    user: bool = False,
    home: typing.Optional[str] = None,
    root: typing.Optional[str] = None,
    isolated: bool = False,
    prefix: typing.Optional[str] = None,
) -> Scheme:
    """
    Get the "scheme" corresponding to the input parameters.

    :param dist_name: the name of the package to retrieve the scheme for, used
        in the headers scheme path
    :param user: indicates to use the "user" scheme
    :param home: indicates to use the "home" scheme
    :param root: root under which other directories are re-based
    :param isolated: ignored, but kept for distutils compatibility (where
        this controls whether the user-site pydistutils.cfg is honored)
    :param prefix: indicates to use the "prefix" scheme and provides the
        base directory for the same
    """
    if user and prefix:
        raise InvalidSchemeCombination("--user", "--prefix")
    if home and prefix:
        raise InvalidSchemeCombination("--home", "--prefix")

    if home is not None:
        scheme_name = _infer_home()
    elif user:
        scheme_name = _infer_user()
    else:
        scheme_name = _infer_prefix()

    # Special case: When installing into a custom prefix, use posix_prefix
    # instead of osx_framework_library. See _should_use_osx_framework_prefix()
    # docstring for details.
    if prefix is not None and scheme_name == "osx_framework_library":
        scheme_name = "posix_prefix"

    if home is not None:
        variables = {k: home for k in _HOME_KEYS}
    elif prefix is not None:
        variables = {k: prefix for k in _HOME_KEYS}
    else:
        variables = {}

    paths = sysconfig.get_paths(scheme=scheme_name, vars=variables)

    # Logic here is very arbitrary, we're doing it for compatibility, don't ask.
    # 1. Pip historically uses a special header path in virtual environments.
    # 2. If the distribution name is not known, distutils uses 'UNKNOWN'. We
    #    only do the same when not running in a virtual environment because
    #    pip's historical header path logic (see point 1) did not do this.
    if running_under_virtualenv():
        if user:
            base = variables.get("userbase", sys.prefix)
        else:
            base = variables.get("base", sys.prefix)
        python_xy = f"python{get_major_minor_version()}"
        paths["include"] = os.path.join(base, "include", "site", python_xy)
    elif not dist_name:
        dist_name = "UNKNOWN"

    scheme = Scheme(
        platlib=paths["platlib"],
        purelib=paths["purelib"],
        headers=os.path.join(paths["include"], dist_name),
        scripts=paths["scripts"],
        data=paths["data"],
    )
    if root is not None:
        converted_keys = {}
        for key in SCHEME_KEYS:
            converted_keys[key] = change_root(root, getattr(scheme, key))
        scheme = Scheme(**converted_keys)
    return scheme


def get_bin_prefix() -> str:
    # Forcing to use /usr/local/bin for standard macOS framework installs.
    if sys.platform[:6] == "darwin" and sys.prefix[:16] == "/System/Library/":
        return "/usr/local/bin"
    return sysconfig.get_paths()["scripts"]


def get_purelib() -> str:
    return sysconfig.get_paths()["purelib"]


def get_platlib() -> str:
    return sysconfig.get_paths()["platlib"]

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\token.py ===
"""
    pygments.token
    ~~~~~~~~~~~~~~

    Basic token types and the standard tokens.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""


class _TokenType(tuple):
    parent = None

    def split(self):
        buf = []
        node = self
        while node is not None:
            buf.append(node)
            node = node.parent
        buf.reverse()
        return buf

    def __init__(self, *args):
        # no need to call super.__init__
        self.subtypes = set()

    def __contains__(self, val):
        return self is val or (
            type(val) is self.__class__ and
            val[:len(self)] == self
        )

    def __getattr__(self, val):
        if not val or not val[0].isupper():
            return tuple.__getattribute__(self, val)
        new = _TokenType(self + (val,))
        setattr(self, val, new)
        self.subtypes.add(new)
        new.parent = self
        return new

    def __repr__(self):
        return 'Token' + (self and '.' or '') + '.'.join(self)

    def __copy__(self):
        # These instances are supposed to be singletons
        return self

    def __deepcopy__(self, memo):
        # These instances are supposed to be singletons
        return self


Token = _TokenType()

# Special token types
Text = Token.Text
Whitespace = Text.Whitespace
Escape = Token.Escape
Error = Token.Error
# Text that doesn't belong to this lexer (e.g. HTML in PHP)
Other = Token.Other

# Common token types for source code
Keyword = Token.Keyword
Name = Token.Name
Literal = Token.Literal
String = Literal.String
Number = Literal.Number
Punctuation = Token.Punctuation
Operator = Token.Operator
Comment = Token.Comment

# Generic types for non-source code
Generic = Token.Generic

# String and some others are not direct children of Token.
# alias them:
Token.Token = Token
Token.String = String
Token.Number = Number


def is_token_subtype(ttype, other):
    """
    Return True if ``ttype`` is a subtype of ``other``.

    exists for backwards compatibility. use ``ttype in other`` now.
    """
    return ttype in other


def string_to_tokentype(s):
    """
    Convert a string into a token type::

        >>> string_to_token('String.Double')
        Token.Literal.String.Double
        >>> string_to_token('Token.Literal.Number')
        Token.Literal.Number
        >>> string_to_token('')
        Token

    Tokens that are already tokens are returned unchanged:

        >>> string_to_token(String)
        Token.Literal.String
    """
    if isinstance(s, _TokenType):
        return s
    if not s:
        return Token
    node = Token
    for item in s.split('.'):
        node = getattr(node, item)
    return node


# Map standard token types to short names, used in CSS class naming.
# If you add a new item, please be sure to run this file to perform
# a consistency check for duplicate values.
STANDARD_TYPES = {
    Token:                         '',

    Text:                          '',
    Whitespace:                    'w',
    Escape:                        'esc',
    Error:                         'err',
    Other:                         'x',

    Keyword:                       'k',
    Keyword.Constant:              'kc',
    Keyword.Declaration:           'kd',
    Keyword.Namespace:             'kn',
    Keyword.Pseudo:                'kp',
    Keyword.Reserved:              'kr',
    Keyword.Type:                  'kt',

    Name:                          'n',
    Name.Attribute:                'na',
    Name.Builtin:                  'nb',
    Name.Builtin.Pseudo:           'bp',
    Name.Class:                    'nc',
    Name.Constant:                 'no',
    Name.Decorator:                'nd',
    Name.Entity:                   'ni',
    Name.Exception:                'ne',
    Name.Function:                 'nf',
    Name.Function.Magic:           'fm',
    Name.Property:                 'py',
    Name.Label:                    'nl',
    Name.Namespace:                'nn',
    Name.Other:                    'nx',
    Name.Tag:                      'nt',
    Name.Variable:                 'nv',
    Name.Variable.Class:           'vc',
    Name.Variable.Global:          'vg',
    Name.Variable.Instance:        'vi',
    Name.Variable.Magic:           'vm',

    Literal:                       'l',
    Literal.Date:                  'ld',

    String:                        's',
    String.Affix:                  'sa',
    String.Backtick:               'sb',
    String.Char:                   'sc',
    String.Delimiter:              'dl',
    String.Doc:                    'sd',
    String.Double:                 's2',
    String.Escape:                 'se',
    String.Heredoc:                'sh',
    String.Interpol:               'si',
    String.Other:                  'sx',
    String.Regex:                  'sr',
    String.Single:                 's1',
    String.Symbol:                 'ss',

    Number:                        'm',
    Number.Bin:                    'mb',
    Number.Float:                  'mf',
    Number.Hex:                    'mh',
    Number.Integer:                'mi',
    Number.Integer.Long:           'il',
    Number.Oct:                    'mo',

    Operator:                      'o',
    Operator.Word:                 'ow',

    Punctuation:                   'p',
    Punctuation.Marker:            'pm',

    Comment:                       'c',
    Comment.Hashbang:              'ch',
    Comment.Multiline:             'cm',
    Comment.Preproc:               'cp',
    Comment.PreprocFile:           'cpf',
    Comment.Single:                'c1',
    Comment.Special:               'cs',

    Generic:                       'g',
    Generic.Deleted:               'gd',
    Generic.Emph:                  'ge',
    Generic.Error:                 'gr',
    Generic.Heading:               'gh',
    Generic.Inserted:              'gi',
    Generic.Output:                'go',
    Generic.Prompt:                'gp',
    Generic.Strong:                'gs',
    Generic.Subheading:            'gu',
    Generic.EmphStrong:            'ges',
    Generic.Traceback:             'gt',
}

# === NexusCore/openenv\Lib\site-packages\aiohttp\web_routedef.py ===
import abc
import os  # noqa
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Type,
    Union,
    overload,
)

import attr

from . import hdrs
from .abc import AbstractView
from .typedefs import Handler, PathLike

if TYPE_CHECKING:
    from .web_request import Request
    from .web_response import StreamResponse
    from .web_urldispatcher import AbstractRoute, UrlDispatcher
else:
    Request = StreamResponse = UrlDispatcher = AbstractRoute = None


__all__ = (
    "AbstractRouteDef",
    "RouteDef",
    "StaticDef",
    "RouteTableDef",
    "head",
    "options",
    "get",
    "post",
    "patch",
    "put",
    "delete",
    "route",
    "view",
    "static",
)


class AbstractRouteDef(abc.ABC):
    @abc.abstractmethod
    def register(self, router: UrlDispatcher) -> List[AbstractRoute]:
        pass  # pragma: no cover


_HandlerType = Union[Type[AbstractView], Handler]


@attr.s(auto_attribs=True, frozen=True, repr=False, slots=True)
class RouteDef(AbstractRouteDef):
    method: str
    path: str
    handler: _HandlerType
    kwargs: Dict[str, Any]

    def __repr__(self) -> str:
        info = []
        for name, value in sorted(self.kwargs.items()):
            info.append(f", {name}={value!r}")
        return "<RouteDef {method} {path} -> {handler.__name__!r}{info}>".format(
            method=self.method, path=self.path, handler=self.handler, info="".join(info)
        )

    def register(self, router: UrlDispatcher) -> List[AbstractRoute]:
        if self.method in hdrs.METH_ALL:
            reg = getattr(router, "add_" + self.method.lower())
            return [reg(self.path, self.handler, **self.kwargs)]
        else:
            return [
                router.add_route(self.method, self.path, self.handler, **self.kwargs)
            ]


@attr.s(auto_attribs=True, frozen=True, repr=False, slots=True)
class StaticDef(AbstractRouteDef):
    prefix: str
    path: PathLike
    kwargs: Dict[str, Any]

    def __repr__(self) -> str:
        info = []
        for name, value in sorted(self.kwargs.items()):
            info.append(f", {name}={value!r}")
        return "<StaticDef {prefix} -> {path}{info}>".format(
            prefix=self.prefix, path=self.path, info="".join(info)
        )

    def register(self, router: UrlDispatcher) -> List[AbstractRoute]:
        resource = router.add_static(self.prefix, self.path, **self.kwargs)
        routes = resource.get_info().get("routes", {})
        return list(routes.values())


def route(method: str, path: str, handler: _HandlerType, **kwargs: Any) -> RouteDef:
    return RouteDef(method, path, handler, kwargs)


def head(path: str, handler: _HandlerType, **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_HEAD, path, handler, **kwargs)


def options(path: str, handler: _HandlerType, **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_OPTIONS, path, handler, **kwargs)


def get(
    path: str,
    handler: _HandlerType,
    *,
    name: Optional[str] = None,
    allow_head: bool = True,
    **kwargs: Any,
) -> RouteDef:
    return route(
        hdrs.METH_GET, path, handler, name=name, allow_head=allow_head, **kwargs
    )


def post(path: str, handler: _HandlerType, **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_POST, path, handler, **kwargs)


def put(path: str, handler: _HandlerType, **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_PUT, path, handler, **kwargs)


def patch(path: str, handler: _HandlerType, **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_PATCH, path, handler, **kwargs)


def delete(path: str, handler: _HandlerType, **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_DELETE, path, handler, **kwargs)


def view(path: str, handler: Type[AbstractView], **kwargs: Any) -> RouteDef:
    return route(hdrs.METH_ANY, path, handler, **kwargs)


def static(prefix: str, path: PathLike, **kwargs: Any) -> StaticDef:
    return StaticDef(prefix, path, kwargs)


_Deco = Callable[[_HandlerType], _HandlerType]


class RouteTableDef(Sequence[AbstractRouteDef]):
    """Route definition table"""

    def __init__(self) -> None:
        self._items: List[AbstractRouteDef] = []

    def __repr__(self) -> str:
        return f"<RouteTableDef count={len(self._items)}>"

    @overload
    def __getitem__(self, index: int) -> AbstractRouteDef: ...

    @overload
    def __getitem__(self, index: slice) -> List[AbstractRouteDef]: ...

    def __getitem__(self, index):  # type: ignore[no-untyped-def]
        return self._items[index]

    def __iter__(self) -> Iterator[AbstractRouteDef]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, item: object) -> bool:
        return item in self._items

    def route(self, method: str, path: str, **kwargs: Any) -> _Deco:
        def inner(handler: _HandlerType) -> _HandlerType:
            self._items.append(RouteDef(method, path, handler, kwargs))
            return handler

        return inner

    def head(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(hdrs.METH_HEAD, path, **kwargs)

    def get(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(hdrs.METH_GET, path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(hdrs.METH_POST, path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(hdrs.METH_PUT, path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(hdrs.METH_PATCH, path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(hdrs.METH_DELETE, path, **kwargs)

    def options(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(hdrs.METH_OPTIONS, path, **kwargs)

    def view(self, path: str, **kwargs: Any) -> _Deco:
        return self.route(hdrs.METH_ANY, path, **kwargs)

    def static(self, prefix: str, path: PathLike, **kwargs: Any) -> None:
        self._items.append(StaticDef(prefix, path, kwargs))

# === NexusCore/openenv\Lib\site-packages\pygments\token.py ===
"""
    pygments.token
    ~~~~~~~~~~~~~~

    Basic token types and the standard tokens.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""


class _TokenType(tuple):
    parent = None

    def split(self):
        buf = []
        node = self
        while node is not None:
            buf.append(node)
            node = node.parent
        buf.reverse()
        return buf

    def __init__(self, *args):
        # no need to call super.__init__
        self.subtypes = set()

    def __contains__(self, val):
        return self is val or (
            type(val) is self.__class__ and
            val[:len(self)] == self
        )

    def __getattr__(self, val):
        if not val or not val[0].isupper():
            return tuple.__getattribute__(self, val)
        new = _TokenType(self + (val,))
        setattr(self, val, new)
        self.subtypes.add(new)
        new.parent = self
        return new

    def __repr__(self):
        return 'Token' + (self and '.' or '') + '.'.join(self)

    def __copy__(self):
        # These instances are supposed to be singletons
        return self

    def __deepcopy__(self, memo):
        # These instances are supposed to be singletons
        return self


Token = _TokenType()

# Special token types
Text = Token.Text
Whitespace = Text.Whitespace
Escape = Token.Escape
Error = Token.Error
# Text that doesn't belong to this lexer (e.g. HTML in PHP)
Other = Token.Other

# Common token types for source code
Keyword = Token.Keyword
Name = Token.Name
Literal = Token.Literal
String = Literal.String
Number = Literal.Number
Punctuation = Token.Punctuation
Operator = Token.Operator
Comment = Token.Comment

# Generic types for non-source code
Generic = Token.Generic

# String and some others are not direct children of Token.
# alias them:
Token.Token = Token
Token.String = String
Token.Number = Number


def is_token_subtype(ttype, other):
    """
    Return True if ``ttype`` is a subtype of ``other``.

    exists for backwards compatibility. use ``ttype in other`` now.
    """
    return ttype in other


def string_to_tokentype(s):
    """
    Convert a string into a token type::

        >>> string_to_token('String.Double')
        Token.Literal.String.Double
        >>> string_to_token('Token.Literal.Number')
        Token.Literal.Number
        >>> string_to_token('')
        Token

    Tokens that are already tokens are returned unchanged:

        >>> string_to_token(String)
        Token.Literal.String
    """
    if isinstance(s, _TokenType):
        return s
    if not s:
        return Token
    node = Token
    for item in s.split('.'):
        node = getattr(node, item)
    return node


# Map standard token types to short names, used in CSS class naming.
# If you add a new item, please be sure to run this file to perform
# a consistency check for duplicate values.
STANDARD_TYPES = {
    Token:                         '',

    Text:                          '',
    Whitespace:                    'w',
    Escape:                        'esc',
    Error:                         'err',
    Other:                         'x',

    Keyword:                       'k',
    Keyword.Constant:              'kc',
    Keyword.Declaration:           'kd',
    Keyword.Namespace:             'kn',
    Keyword.Pseudo:                'kp',
    Keyword.Reserved:              'kr',
    Keyword.Type:                  'kt',

    Name:                          'n',
    Name.Attribute:                'na',
    Name.Builtin:                  'nb',
    Name.Builtin.Pseudo:           'bp',
    Name.Class:                    'nc',
    Name.Constant:                 'no',
    Name.Decorator:                'nd',
    Name.Entity:                   'ni',
    Name.Exception:                'ne',
    Name.Function:                 'nf',
    Name.Function.Magic:           'fm',
    Name.Property:                 'py',
    Name.Label:                    'nl',
    Name.Namespace:                'nn',
    Name.Other:                    'nx',
    Name.Tag:                      'nt',
    Name.Variable:                 'nv',
    Name.Variable.Class:           'vc',
    Name.Variable.Global:          'vg',
    Name.Variable.Instance:        'vi',
    Name.Variable.Magic:           'vm',

    Literal:                       'l',
    Literal.Date:                  'ld',

    String:                        's',
    String.Affix:                  'sa',
    String.Backtick:               'sb',
    String.Char:                   'sc',
    String.Delimiter:              'dl',
    String.Doc:                    'sd',
    String.Double:                 's2',
    String.Escape:                 'se',
    String.Heredoc:                'sh',
    String.Interpol:               'si',
    String.Other:                  'sx',
    String.Regex:                  'sr',
    String.Single:                 's1',
    String.Symbol:                 'ss',

    Number:                        'm',
    Number.Bin:                    'mb',
    Number.Float:                  'mf',
    Number.Hex:                    'mh',
    Number.Integer:                'mi',
    Number.Integer.Long:           'il',
    Number.Oct:                    'mo',

    Operator:                      'o',
    Operator.Word:                 'ow',

    Punctuation:                   'p',
    Punctuation.Marker:            'pm',

    Comment:                       'c',
    Comment.Hashbang:              'ch',
    Comment.Multiline:             'cm',
    Comment.Preproc:               'cp',
    Comment.PreprocFile:           'cpf',
    Comment.Single:                'c1',
    Comment.Special:               'cs',

    Generic:                       'g',
    Generic.Deleted:               'gd',
    Generic.Emph:                  'ge',
    Generic.Error:                 'gr',
    Generic.Heading:               'gh',
    Generic.Inserted:              'gi',
    Generic.Output:                'go',
    Generic.Prompt:                'gp',
    Generic.Strong:                'gs',
    Generic.Subheading:            'gu',
    Generic.EmphStrong:            'ges',
    Generic.Traceback:             'gt',
}

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\utils\_auth.py ===
# Copyright 2023 The HuggingFace Team. All rights reserved.
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
"""Contains an helper to get the token from machine (env variable, secret or config file)."""

import configparser
import logging
import os
import warnings
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

from .. import constants
from ._runtime import is_colab_enterprise, is_google_colab


_IS_GOOGLE_COLAB_CHECKED = False
_GOOGLE_COLAB_SECRET_LOCK = Lock()
_GOOGLE_COLAB_SECRET: Optional[str] = None

logger = logging.getLogger(__name__)


def get_token() -> Optional[str]:
    """
    Get token if user is logged in.

    Note: in most cases, you should use [`huggingface_hub.utils.build_hf_headers`] instead. This method is only useful
          if you want to retrieve the token for other purposes than sending an HTTP request.

    Token is retrieved in priority from the `HF_TOKEN` environment variable. Otherwise, we read the token file located
    in the Hugging Face home folder. Returns None if user is not logged in. To log in, use [`login`] or
    `huggingface-cli login`.

    Returns:
        `str` or `None`: The token, `None` if it doesn't exist.
    """
    return _get_token_from_google_colab() or _get_token_from_environment() or _get_token_from_file()


def _get_token_from_google_colab() -> Optional[str]:
    """Get token from Google Colab secrets vault using `google.colab.userdata.get(...)`.

    Token is read from the vault only once per session and then stored in a global variable to avoid re-requesting
    access to the vault.
    """
    # If it's not a Google Colab or it's Colab Enterprise, fallback to environment variable or token file authentication
    if not is_google_colab() or is_colab_enterprise():
        return None

    # `google.colab.userdata` is not thread-safe
    # This can lead to a deadlock if multiple threads try to access it at the same time
    # (typically when using `snapshot_download`)
    # => use a lock
    # See https://github.com/huggingface/huggingface_hub/issues/1952 for more details.
    with _GOOGLE_COLAB_SECRET_LOCK:
        global _GOOGLE_COLAB_SECRET
        global _IS_GOOGLE_COLAB_CHECKED

        if _IS_GOOGLE_COLAB_CHECKED:  # request access only once
            return _GOOGLE_COLAB_SECRET

        try:
            from google.colab import userdata  # type: ignore
            from google.colab.errors import Error as ColabError  # type: ignore
        except ImportError:
            return None

        try:
            token = userdata.get("HF_TOKEN")
            _GOOGLE_COLAB_SECRET = _clean_token(token)
        except userdata.NotebookAccessError:
            # Means the user has a secret call `HF_TOKEN` and got a popup "please grand access to HF_TOKEN" and refused it
            # => warn user but ignore error => do not re-request access to user
            warnings.warn(
                "\nAccess to the secret `HF_TOKEN` has not been granted on this notebook."
                "\nYou will not be requested again."
                "\nPlease restart the session if you want to be prompted again."
            )
            _GOOGLE_COLAB_SECRET = None
        except userdata.SecretNotFoundError:
            # Means the user did not define a `HF_TOKEN` secret => warn
            warnings.warn(
                "\nThe secret `HF_TOKEN` does not exist in your Colab secrets."
                "\nTo authenticate with the Hugging Face Hub, create a token in your settings tab "
                "(https://huggingface.co/settings/tokens), set it as secret in your Google Colab and restart your session."
                "\nYou will be able to reuse this secret in all of your notebooks."
                "\nPlease note that authentication is recommended but still optional to access public models or datasets."
            )
            _GOOGLE_COLAB_SECRET = None
        except ColabError as e:
            # Something happen but we don't know what => recommend to open a GitHub issue
            warnings.warn(
                f"\nError while fetching `HF_TOKEN` secret value from your vault: '{str(e)}'."
                "\nYou are not authenticated with the Hugging Face Hub in this notebook."
                "\nIf the error persists, please let us know by opening an issue on GitHub "
                "(https://github.com/huggingface/huggingface_hub/issues/new)."
            )
            _GOOGLE_COLAB_SECRET = None

        _IS_GOOGLE_COLAB_CHECKED = True
        return _GOOGLE_COLAB_SECRET


def _get_token_from_environment() -> Optional[str]:
    # `HF_TOKEN` has priority (keep `HUGGING_FACE_HUB_TOKEN` for backward compatibility)
    return _clean_token(os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN"))


def _get_token_from_file() -> Optional[str]:
    try:
        return _clean_token(Path(constants.HF_TOKEN_PATH).read_text())
    except FileNotFoundError:
        return None


def get_stored_tokens() -> Dict[str, str]:
    """
    Returns the parsed INI file containing the access tokens.
    The file is located at `HF_STORED_TOKENS_PATH`, defaulting to `~/.cache/huggingface/stored_tokens`.
    If the file does not exist, an empty dictionary is returned.

    Returns: `Dict[str, str]`
        Key is the token name and value is the token.
    """
    tokens_path = Path(constants.HF_STORED_TOKENS_PATH)
    if not tokens_path.exists():
        stored_tokens = {}
    config = configparser.ConfigParser()
    try:
        config.read(tokens_path)
        stored_tokens = {token_name: config.get(token_name, "hf_token") for token_name in config.sections()}
    except configparser.Error as e:
        logger.error(f"Error parsing stored tokens file: {e}")
        stored_tokens = {}
    return stored_tokens


def _save_stored_tokens(stored_tokens: Dict[str, str]) -> None:
    """
    Saves the given configuration to the stored tokens file.

    Args:
        stored_tokens (`Dict[str, str]`):
            The stored tokens to save. Key is the token name and value is the token.
    """
    stored_tokens_path = Path(constants.HF_STORED_TOKENS_PATH)

    # Write the stored tokens into an INI file
    config = configparser.ConfigParser()
    for token_name in sorted(stored_tokens.keys()):
        config.add_section(token_name)
        config.set(token_name, "hf_token", stored_tokens[token_name])

    stored_tokens_path.parent.mkdir(parents=True, exist_ok=True)
    with stored_tokens_path.open("w") as config_file:
        config.write(config_file)


def _get_token_by_name(token_name: str) -> Optional[str]:
    """
    Get the token by name.

    Args:
        token_name (`str`):
            The name of the token to get.

    Returns:
        `str` or `None`: The token, `None` if it doesn't exist.

    """
    stored_tokens = get_stored_tokens()
    if token_name not in stored_tokens:
        return None
    return _clean_token(stored_tokens[token_name])


def _save_token(token: str, token_name: str) -> None:
    """
    Save the given token.

    If the stored tokens file does not exist, it will be created.
    Args:
        token (`str`):
            The token to save.
        token_name (`str`):
            The name of the token.
    """
    tokens_path = Path(constants.HF_STORED_TOKENS_PATH)
    stored_tokens = get_stored_tokens()
    stored_tokens[token_name] = token
    _save_stored_tokens(stored_tokens)
    logger.info(f"The token `{token_name}` has been saved to {tokens_path}")


def _clean_token(token: Optional[str]) -> Optional[str]:
    """Clean token by removing trailing and leading spaces and newlines.

    If token is an empty string, return None.
    """
    if token is None:
        return None
    return token.replace("\r", "").replace("\n", "").strip() or None

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\magics.py ===
"""Extra magics for terminal use."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.


from logging import error
import os
import sys

from IPython.core.error import TryNext, UsageError
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.lib.clipboard import ClipboardEmpty
from IPython.testing.skipdoctest import skip_doctest
from IPython.utils.text import SList, strip_email_quotes
from IPython.utils import py3compat

def get_pasted_lines(sentinel, l_input=py3compat.input, quiet=False):
    """ Yield pasted lines until the user enters the given sentinel value.
    """
    if not quiet:
        print("Pasting code; enter '%s' alone on the line to stop or use Ctrl-D." \
              % sentinel)
        prompt = ":"
    else:
        prompt = ""
    while True:
        try:
            l = l_input(prompt)
            if l == sentinel:
                return
            else:
                yield l
        except EOFError:
            print('<EOF>')
            return


@magics_class
class TerminalMagics(Magics):
    def __init__(self, shell):
        super(TerminalMagics, self).__init__(shell)

    def store_or_execute(self, block, name, store_history=False):
        """ Execute a block, or store it in a variable, per the user's request.
        """
        if name:
            # If storing it for further editing
            self.shell.user_ns[name] = SList(block.splitlines())
            print("Block assigned to '%s'" % name)
        else:
            b = self.preclean_input(block)
            self.shell.user_ns['pasted_block'] = b
            self.shell.using_paste_magics = True
            try:
                self.shell.run_cell(b, store_history)
            finally:
                self.shell.using_paste_magics = False

    def preclean_input(self, block):
        lines = block.splitlines()
        while lines and not lines[0].strip():
            lines = lines[1:]
        return strip_email_quotes('\n'.join(lines))

    def rerun_pasted(self, name='pasted_block'):
        """ Rerun a previously pasted command.
        """
        b = self.shell.user_ns.get(name)

        # Sanity checks
        if b is None:
            raise UsageError('No previous pasted block available')
        if not isinstance(b, str):
            raise UsageError(
                "Variable 'pasted_block' is not a string, can't execute")

        print("Re-executing '%s...' (%d chars)"% (b.split('\n',1)[0], len(b)))
        self.shell.run_cell(b)

    @line_magic
    def autoindent(self, parameter_s = ''):
        """Toggle autoindent on/off (deprecated)"""
        self.shell.set_autoindent()
        print("Automatic indentation is:",['OFF','ON'][self.shell.autoindent])

    @skip_doctest
    @line_magic
    def cpaste(self, parameter_s=''):
        """Paste & execute a pre-formatted code block from clipboard.

        You must terminate the block with '--' (two minus-signs) or Ctrl-D
        alone on the line. You can also provide your own sentinel with '%paste
        -s %%' ('%%' is the new sentinel for this operation).

        The block is dedented prior to execution to enable execution of method
        definitions. '>' and '+' characters at the beginning of a line are
        ignored, to allow pasting directly from e-mails, diff files and
        doctests (the '...' continuation prompt is also stripped).  The
        executed block is also assigned to variable named 'pasted_block' for
        later editing with '%edit pasted_block'.

        You can also pass a variable name as an argument, e.g. '%cpaste foo'.
        This assigns the pasted block to variable 'foo' as string, without
        dedenting or executing it (preceding >>> and + is still stripped)

        '%cpaste -r' re-executes the block previously entered by cpaste.
        '%cpaste -q' suppresses any additional output messages.

        Do not be alarmed by garbled output on Windows (it's a readline bug).
        Just press enter and type -- (and press enter again) and the block
        will be what was just pasted.

        Shell escapes are not supported (yet).

        See Also
        --------
        paste : automatically pull code from clipboard.

        Examples
        --------
        ::

          In [8]: %cpaste
          Pasting code; enter '--' alone on the line to stop.
          :>>> a = ["world!", "Hello"]
          :>>> print(" ".join(sorted(a)))
          :--
          Hello world!

        ::
          In [8]: %cpaste
          Pasting code; enter '--' alone on the line to stop.
          :>>> %alias_magic t timeit
          :>>> %t -n1 pass
          :--
          Created `%t` as an alias for `%timeit`.
          Created `%%t` as an alias for `%%timeit`.
          354 ns ± 224 ns per loop (mean ± std. dev. of 7 runs, 1 loop each)
        """
        opts, name = self.parse_options(parameter_s, 'rqs:', mode='string')
        if 'r' in opts:
            self.rerun_pasted()
            return

        quiet = ('q' in opts)

        sentinel = opts.get('s', u'--')
        block = '\n'.join(get_pasted_lines(sentinel, quiet=quiet))
        self.store_or_execute(block, name, store_history=True)

    @line_magic
    def paste(self, parameter_s=''):
        """Paste & execute a pre-formatted code block from clipboard.

        The text is pulled directly from the clipboard without user
        intervention and printed back on the screen before execution (unless
        the -q flag is given to force quiet mode).

        The block is dedented prior to execution to enable execution of method
        definitions. '>' and '+' characters at the beginning of a line are
        ignored, to allow pasting directly from e-mails, diff files and
        doctests (the '...' continuation prompt is also stripped).  The
        executed block is also assigned to variable named 'pasted_block' for
        later editing with '%edit pasted_block'.

        You can also pass a variable name as an argument, e.g. '%paste foo'.
        This assigns the pasted block to variable 'foo' as string, without
        executing it (preceding >>> and + is still stripped).

        Options:

          -r: re-executes the block previously entered by cpaste.

          -q: quiet mode: do not echo the pasted text back to the terminal.

        IPython statements (magics, shell escapes) are not supported (yet).

        See Also
        --------
        cpaste : manually paste code into terminal until you mark its end.
        """
        opts, name = self.parse_options(parameter_s, 'rq', mode='string')
        if 'r' in opts:
            self.rerun_pasted()
            return
        try:
            block = self.shell.hooks.clipboard_get()
        except TryNext as clipboard_exc:
            message = getattr(clipboard_exc, 'args')
            if message:
                error(message[0])
            else:
                error('Could not get text from the clipboard.')
            return
        except ClipboardEmpty as e:
            raise UsageError("The clipboard appears to be empty") from e

        # By default, echo back to terminal unless quiet mode is requested
        if 'q' not in opts:
            sys.stdout.write(self.shell.pycolorize(block))
            if not block.endswith("\n"):
                sys.stdout.write("\n")
            sys.stdout.write("## -- End pasted text --\n")

        self.store_or_execute(block, name, store_history=True)

    # Class-level: add a '%cls' magic only on Windows
    if sys.platform == 'win32':
        @line_magic
        def cls(self, s):
            """Clear screen.
            """
            os.system("cls")

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\gcs_pubsub\pub_sub.py ===
"""
BETA

This is the PubSub logger for GCS PubSub, this sends LiteLLM SpendLogs Payloads to GCS PubSub.

Users can use this instead of sending their SpendLogs to their Postgres database.
"""

import asyncio
import json
import os
import traceback
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from litellm.types.utils import StandardLoggingPayload

if TYPE_CHECKING:
    from litellm.proxy._types import SpendLogsPayload
else:
    SpendLogsPayload = Any

import litellm
from litellm._logging import verbose_logger
from litellm.integrations.custom_batch_logger import CustomBatchLogger
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)


class GcsPubSubLogger(CustomBatchLogger):
    def __init__(
        self,
        project_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize Google Cloud Pub/Sub publisher

        Args:
            project_id (str): Google Cloud project ID
            topic_id (str): Pub/Sub topic ID
            credentials_path (str, optional): Path to Google Cloud credentials JSON file
        """
        from litellm.proxy.utils import _premium_user_check

        _premium_user_check()

        self.async_httpx_client = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.LoggingCallback
        )

        self.project_id = project_id or os.getenv("GCS_PUBSUB_PROJECT_ID")
        self.topic_id = topic_id or os.getenv("GCS_PUBSUB_TOPIC_ID")
        self.path_service_account_json = credentials_path or os.getenv(
            "GCS_PATH_SERVICE_ACCOUNT"
        )

        if not self.project_id or not self.topic_id:
            raise ValueError("Both project_id and topic_id must be provided")

        self.flush_lock = asyncio.Lock()
        super().__init__(**kwargs, flush_lock=self.flush_lock)
        asyncio.create_task(self.periodic_flush())
        self.log_queue: List[Union[SpendLogsPayload, StandardLoggingPayload]] = []

    async def construct_request_headers(self) -> Dict[str, str]:
        """Construct authorization headers using Vertex AI auth"""
        from litellm import vertex_chat_completion

        (
            _auth_header,
            vertex_project,
        ) = await vertex_chat_completion._ensure_access_token_async(
            credentials=self.path_service_account_json,
            project_id=self.project_id,
            custom_llm_provider="vertex_ai",
        )

        auth_header, _ = vertex_chat_completion._get_token_and_url(
            model="pub-sub",
            auth_header=_auth_header,
            vertex_credentials=self.path_service_account_json,
            vertex_project=vertex_project,
            vertex_location=None,
            gemini_api_key=None,
            stream=None,
            custom_llm_provider="vertex_ai",
            api_base=None,
        )

        headers = {
            "Authorization": f"Bearer {auth_header}",
            "Content-Type": "application/json",
        }
        return headers

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """
        Async Log success events to GCS PubSub Topic

        - Creates a SpendLogsPayload
        - Adds to batch queue
        - Flushes based on CustomBatchLogger settings

        Raises:
            Raises a NON Blocking verbose_logger.exception if an error occurs
        """
        from litellm.proxy.spend_tracking.spend_tracking_utils import (
            get_logging_payload,
        )
        from litellm.proxy.utils import _premium_user_check

        _premium_user_check()

        try:
            verbose_logger.debug(
                "PubSub: Logging - Enters logging function for model %s", kwargs
            )
            standard_logging_payload = kwargs.get("standard_logging_object", None)

            # Backwards compatibility with old logging payload
            if litellm.gcs_pub_sub_use_v1 is True:
                spend_logs_payload = get_logging_payload(
                    kwargs=kwargs,
                    response_obj=response_obj,
                    start_time=start_time,
                    end_time=end_time,
                )
                self.log_queue.append(spend_logs_payload)
            else:
                # New logging payload, StandardLoggingPayload
                self.log_queue.append(standard_logging_payload)

            if len(self.log_queue) >= self.batch_size:
                await self.async_send_batch()

        except Exception as e:
            verbose_logger.exception(
                f"PubSub Layer Error - {str(e)}\n{traceback.format_exc()}"
            )
            pass

    async def async_send_batch(self):
        """
        Sends the batch of messages to Pub/Sub
        """
        try:
            if not self.log_queue:
                return

            verbose_logger.debug(
                f"PubSub - about to flush {len(self.log_queue)} events"
            )

            for message in self.log_queue:
                await self.publish_message(message)

        except Exception as e:
            verbose_logger.exception(
                f"PubSub Error sending batch - {str(e)}\n{traceback.format_exc()}"
            )
        finally:
            self.log_queue.clear()

    async def publish_message(
        self, message: Union[SpendLogsPayload, StandardLoggingPayload]
    ) -> Optional[Dict[str, Any]]:
        """
        Publish message to Google Cloud Pub/Sub using REST API

        Args:
            message: Message to publish (dict or string)

        Returns:
            dict: Published message response
        """
        try:
            headers = await self.construct_request_headers()

            # Prepare message data
            if isinstance(message, str):
                message_data = message
            else:
                message_data = json.dumps(message, default=str)

            # Base64 encode the message
            import base64

            encoded_message = base64.b64encode(message_data.encode("utf-8")).decode(
                "utf-8"
            )

            # Construct request body
            request_body = {"messages": [{"data": encoded_message}]}

            url = f"https://pubsub.googleapis.com/v1/projects/{self.project_id}/topics/{self.topic_id}:publish"

            response = await self.async_httpx_client.post(
                url=url, headers=headers, json=request_body
            )

            if response.status_code not in [200, 202]:
                verbose_logger.error("Pub/Sub publish error: %s", str(response.text))
                raise Exception(f"Failed to publish message: {response.text}")

            verbose_logger.debug("Pub/Sub response: %s", response.text)
            return response.json()

        except Exception as e:
            verbose_logger.error("Pub/Sub publish error: %s", str(e))
            return None

# === NexusCore/openenv\Lib\site-packages\pip\_internal\locations\_sysconfig.py ===
import logging
import os
import sys
import sysconfig
import typing

from pip._internal.exceptions import InvalidSchemeCombination, UserInstallationInvalid
from pip._internal.models.scheme import SCHEME_KEYS, Scheme
from pip._internal.utils.virtualenv import running_under_virtualenv

from .base import change_root, get_major_minor_version, is_osx_framework

logger = logging.getLogger(__name__)


# Notes on _infer_* functions.
# Unfortunately ``get_default_scheme()`` didn't exist before 3.10, so there's no
# way to ask things like "what is the '_prefix' scheme on this platform". These
# functions try to answer that with some heuristics while accounting for ad-hoc
# platforms not covered by CPython's default sysconfig implementation. If the
# ad-hoc implementation does not fully implement sysconfig, we'll fall back to
# a POSIX scheme.

_AVAILABLE_SCHEMES = set(sysconfig.get_scheme_names())

_PREFERRED_SCHEME_API = getattr(sysconfig, "get_preferred_scheme", None)


def _should_use_osx_framework_prefix() -> bool:
    """Check for Apple's ``osx_framework_library`` scheme.

    Python distributed by Apple's Command Line Tools has this special scheme
    that's used when:

    * This is a framework build.
    * We are installing into the system prefix.

    This does not account for ``pip install --prefix`` (also means we're not
    installing to the system prefix), which should use ``posix_prefix``, but
    logic here means ``_infer_prefix()`` outputs ``osx_framework_library``. But
    since ``prefix`` is not available for ``sysconfig.get_default_scheme()``,
    which is the stdlib replacement for ``_infer_prefix()``, presumably Apple
    wouldn't be able to magically switch between ``osx_framework_library`` and
    ``posix_prefix``. ``_infer_prefix()`` returning ``osx_framework_library``
    means its behavior is consistent whether we use the stdlib implementation
    or our own, and we deal with this special case in ``get_scheme()`` instead.
    """
    return (
        "osx_framework_library" in _AVAILABLE_SCHEMES
        and not running_under_virtualenv()
        and is_osx_framework()
    )


def _infer_prefix() -> str:
    """Try to find a prefix scheme for the current platform.

    This tries:

    * A special ``osx_framework_library`` for Python distributed by Apple's
      Command Line Tools, when not running in a virtual environment.
    * Implementation + OS, used by PyPy on Windows (``pypy_nt``).
    * Implementation without OS, used by PyPy on POSIX (``pypy``).
    * OS + "prefix", used by CPython on POSIX (``posix_prefix``).
    * Just the OS name, used by CPython on Windows (``nt``).

    If none of the above works, fall back to ``posix_prefix``.
    """
    if _PREFERRED_SCHEME_API:
        return _PREFERRED_SCHEME_API("prefix")
    if _should_use_osx_framework_prefix():
        return "osx_framework_library"
    implementation_suffixed = f"{sys.implementation.name}_{os.name}"
    if implementation_suffixed in _AVAILABLE_SCHEMES:
        return implementation_suffixed
    if sys.implementation.name in _AVAILABLE_SCHEMES:
        return sys.implementation.name
    suffixed = f"{os.name}_prefix"
    if suffixed in _AVAILABLE_SCHEMES:
        return suffixed
    if os.name in _AVAILABLE_SCHEMES:  # On Windows, prefx is just called "nt".
        return os.name
    return "posix_prefix"


def _infer_user() -> str:
    """Try to find a user scheme for the current platform."""
    if _PREFERRED_SCHEME_API:
        return _PREFERRED_SCHEME_API("user")
    if is_osx_framework() and not running_under_virtualenv():
        suffixed = "osx_framework_user"
    else:
        suffixed = f"{os.name}_user"
    if suffixed in _AVAILABLE_SCHEMES:
        return suffixed
    if "posix_user" not in _AVAILABLE_SCHEMES:  # User scheme unavailable.
        raise UserInstallationInvalid()
    return "posix_user"


def _infer_home() -> str:
    """Try to find a home for the current platform."""
    if _PREFERRED_SCHEME_API:
        return _PREFERRED_SCHEME_API("home")
    suffixed = f"{os.name}_home"
    if suffixed in _AVAILABLE_SCHEMES:
        return suffixed
    return "posix_home"


# Update these keys if the user sets a custom home.
_HOME_KEYS = [
    "installed_base",
    "base",
    "installed_platbase",
    "platbase",
    "prefix",
    "exec_prefix",
]
if sysconfig.get_config_var("userbase") is not None:
    _HOME_KEYS.append("userbase")


def get_scheme(
    dist_name: str,
    user: bool = False,
    home: typing.Optional[str] = None,
    root: typing.Optional[str] = None,
    isolated: bool = False,
    prefix: typing.Optional[str] = None,
) -> Scheme:
    """
    Get the "scheme" corresponding to the input parameters.

    :param dist_name: the name of the package to retrieve the scheme for, used
        in the headers scheme path
    :param user: indicates to use the "user" scheme
    :param home: indicates to use the "home" scheme
    :param root: root under which other directories are re-based
    :param isolated: ignored, but kept for distutils compatibility (where
        this controls whether the user-site pydistutils.cfg is honored)
    :param prefix: indicates to use the "prefix" scheme and provides the
        base directory for the same
    """
    if user and prefix:
        raise InvalidSchemeCombination("--user", "--prefix")
    if home and prefix:
        raise InvalidSchemeCombination("--home", "--prefix")

    if home is not None:
        scheme_name = _infer_home()
    elif user:
        scheme_name = _infer_user()
    else:
        scheme_name = _infer_prefix()

    # Special case: When installing into a custom prefix, use posix_prefix
    # instead of osx_framework_library. See _should_use_osx_framework_prefix()
    # docstring for details.
    if prefix is not None and scheme_name == "osx_framework_library":
        scheme_name = "posix_prefix"

    if home is not None:
        variables = {k: home for k in _HOME_KEYS}
    elif prefix is not None:
        variables = {k: prefix for k in _HOME_KEYS}
    else:
        variables = {}

    paths = sysconfig.get_paths(scheme=scheme_name, vars=variables)

    # Logic here is very arbitrary, we're doing it for compatibility, don't ask.
    # 1. Pip historically uses a special header path in virtual environments.
    # 2. If the distribution name is not known, distutils uses 'UNKNOWN'. We
    #    only do the same when not running in a virtual environment because
    #    pip's historical header path logic (see point 1) did not do this.
    if running_under_virtualenv():
        if user:
            base = variables.get("userbase", sys.prefix)
        else:
            base = variables.get("base", sys.prefix)
        python_xy = f"python{get_major_minor_version()}"
        paths["include"] = os.path.join(base, "include", "site", python_xy)
    elif not dist_name:
        dist_name = "UNKNOWN"

    scheme = Scheme(
        platlib=paths["platlib"],
        purelib=paths["purelib"],
        headers=os.path.join(paths["include"], dist_name),
        scripts=paths["scripts"],
        data=paths["data"],
    )
    if root is not None:
        converted_keys = {}
        for key in SCHEME_KEYS:
            converted_keys[key] = change_root(root, getattr(scheme, key))
        scheme = Scheme(**converted_keys)
    return scheme


def get_bin_prefix() -> str:
    # Forcing to use /usr/local/bin for standard macOS framework installs.
    if sys.platform[:6] == "darwin" and sys.prefix[:16] == "/System/Library/":
        return "/usr/local/bin"
    return sysconfig.get_paths()["scripts"]


def get_purelib() -> str:
    return sysconfig.get_paths()["purelib"]


def get_platlib() -> str:
    return sysconfig.get_paths()["platlib"]

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\token.py ===
"""
    pygments.token
    ~~~~~~~~~~~~~~

    Basic token types and the standard tokens.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""


class _TokenType(tuple):
    parent = None

    def split(self):
        buf = []
        node = self
        while node is not None:
            buf.append(node)
            node = node.parent
        buf.reverse()
        return buf

    def __init__(self, *args):
        # no need to call super.__init__
        self.subtypes = set()

    def __contains__(self, val):
        return self is val or (
            type(val) is self.__class__ and
            val[:len(self)] == self
        )

    def __getattr__(self, val):
        if not val or not val[0].isupper():
            return tuple.__getattribute__(self, val)
        new = _TokenType(self + (val,))
        setattr(self, val, new)
        self.subtypes.add(new)
        new.parent = self
        return new

    def __repr__(self):
        return 'Token' + (self and '.' or '') + '.'.join(self)

    def __copy__(self):
        # These instances are supposed to be singletons
        return self

    def __deepcopy__(self, memo):
        # These instances are supposed to be singletons
        return self


Token = _TokenType()

# Special token types
Text = Token.Text
Whitespace = Text.Whitespace
Escape = Token.Escape
Error = Token.Error
# Text that doesn't belong to this lexer (e.g. HTML in PHP)
Other = Token.Other

# Common token types for source code
Keyword = Token.Keyword
Name = Token.Name
Literal = Token.Literal
String = Literal.String
Number = Literal.Number
Punctuation = Token.Punctuation
Operator = Token.Operator
Comment = Token.Comment

# Generic types for non-source code
Generic = Token.Generic

# String and some others are not direct children of Token.
# alias them:
Token.Token = Token
Token.String = String
Token.Number = Number


def is_token_subtype(ttype, other):
    """
    Return True if ``ttype`` is a subtype of ``other``.

    exists for backwards compatibility. use ``ttype in other`` now.
    """
    return ttype in other


def string_to_tokentype(s):
    """
    Convert a string into a token type::

        >>> string_to_token('String.Double')
        Token.Literal.String.Double
        >>> string_to_token('Token.Literal.Number')
        Token.Literal.Number
        >>> string_to_token('')
        Token

    Tokens that are already tokens are returned unchanged:

        >>> string_to_token(String)
        Token.Literal.String
    """
    if isinstance(s, _TokenType):
        return s
    if not s:
        return Token
    node = Token
    for item in s.split('.'):
        node = getattr(node, item)
    return node


# Map standard token types to short names, used in CSS class naming.
# If you add a new item, please be sure to run this file to perform
# a consistency check for duplicate values.
STANDARD_TYPES = {
    Token:                         '',

    Text:                          '',
    Whitespace:                    'w',
    Escape:                        'esc',
    Error:                         'err',
    Other:                         'x',

    Keyword:                       'k',
    Keyword.Constant:              'kc',
    Keyword.Declaration:           'kd',
    Keyword.Namespace:             'kn',
    Keyword.Pseudo:                'kp',
    Keyword.Reserved:              'kr',
    Keyword.Type:                  'kt',

    Name:                          'n',
    Name.Attribute:                'na',
    Name.Builtin:                  'nb',
    Name.Builtin.Pseudo:           'bp',
    Name.Class:                    'nc',
    Name.Constant:                 'no',
    Name.Decorator:                'nd',
    Name.Entity:                   'ni',
    Name.Exception:                'ne',
    Name.Function:                 'nf',
    Name.Function.Magic:           'fm',
    Name.Property:                 'py',
    Name.Label:                    'nl',
    Name.Namespace:                'nn',
    Name.Other:                    'nx',
    Name.Tag:                      'nt',
    Name.Variable:                 'nv',
    Name.Variable.Class:           'vc',
    Name.Variable.Global:          'vg',
    Name.Variable.Instance:        'vi',
    Name.Variable.Magic:           'vm',

    Literal:                       'l',
    Literal.Date:                  'ld',

    String:                        's',
    String.Affix:                  'sa',
    String.Backtick:               'sb',
    String.Char:                   'sc',
    String.Delimiter:              'dl',
    String.Doc:                    'sd',
    String.Double:                 's2',
    String.Escape:                 'se',
    String.Heredoc:                'sh',
    String.Interpol:               'si',
    String.Other:                  'sx',
    String.Regex:                  'sr',
    String.Single:                 's1',
    String.Symbol:                 'ss',

    Number:                        'm',
    Number.Bin:                    'mb',
    Number.Float:                  'mf',
    Number.Hex:                    'mh',
    Number.Integer:                'mi',
    Number.Integer.Long:           'il',
    Number.Oct:                    'mo',

    Operator:                      'o',
    Operator.Word:                 'ow',

    Punctuation:                   'p',
    Punctuation.Marker:            'pm',

    Comment:                       'c',
    Comment.Hashbang:              'ch',
    Comment.Multiline:             'cm',
    Comment.Preproc:               'cp',
    Comment.PreprocFile:           'cpf',
    Comment.Single:                'c1',
    Comment.Special:               'cs',

    Generic:                       'g',
    Generic.Deleted:               'gd',
    Generic.Emph:                  'ge',
    Generic.Error:                 'gr',
    Generic.Heading:               'gh',
    Generic.Inserted:              'gi',
    Generic.Output:                'go',
    Generic.Prompt:                'gp',
    Generic.Strong:                'gs',
    Generic.Subheading:            'gu',
    Generic.EmphStrong:            'ges',
    Generic.Traceback:             'gt',
}

# === NexusCore/openenv\Lib\site-packages\win32com\demos\iebutton.py ===
# -*- coding: latin-1 -*-

# PyWin32 Internet Explorer Button
#
# written by Leonard Ritter (paniq@gmx.net)
# and Robert Förtsch (info@robert-foertsch.com)


"""
This sample implements a simple IE Button COM server
with access to the IWebBrowser2 interface.

To demonstrate:
* Execute this script to register the server.
* Open Pythonwin's Tools -> Trace Collector Debugging Tool, so you can
  see the output of 'print' statements in this demo.
* Open a new IE instance.  The toolbar should have a new "scissors" icon,
  with tooltip text "IE Button" - this is our new button - click it.
* Switch back to the Pythonwin window - you should see:
   IOleCommandTarget::Exec called.
  This is the button being clicked.  Extending this to do something more
  useful is left as an exercise.

Contribtions to this sample to make it a little "friendlier" welcome!
"""

# imports section

import pythoncom
import win32api
import win32com
import win32com.server.register

# This demo uses 'print' - use win32traceutil to see it if we have no
# console.
try:
    win32api.GetConsoleTitle()
except win32api.error:
    import win32traceutil


from win32com.axcontrol import axcontrol

# ensure we know the ms internet controls typelib so we have access to IWebBrowser2 later on
win32com.client.gencache.EnsureModule("{EAB22AC0-30C1-11CF-A7EB-0000C05BAE0B}", 0, 1, 1)


#
IObjectWithSite_methods = ["SetSite", "GetSite"]
IOleCommandTarget_methods = ["Exec", "QueryStatus"]

_iebutton_methods_ = IOleCommandTarget_methods + IObjectWithSite_methods
_iebutton_com_interfaces_ = [
    axcontrol.IID_IOleCommandTarget,
    axcontrol.IID_IObjectWithSite,  # IObjectWithSite
]


class Stub:
    """
    this class serves as a method stub,
    outputting debug info whenever the object
    is being called.
    """

    def __init__(self, name):
        self.name = name

    def __call__(self, *args):
        print("STUB: ", self.name, args)


class IEButton:
    """
    The actual COM server class
    """

    _com_interfaces_ = _iebutton_com_interfaces_
    _public_methods_ = _iebutton_methods_
    _reg_clsctx_ = pythoncom.CLSCTX_INPROC_SERVER
    _button_text_ = "IE Button"
    _tool_tip_ = "An example implementation for an IE Button."
    _icon_ = ""
    _hot_icon_ = ""

    def __init__(self):
        # put stubs for non-implemented methods
        for method in self._public_methods_:
            if not hasattr(self, method):
                print("providing default stub for %s" % method)
                setattr(self, method, Stub(method))

    def QueryStatus(self, pguidCmdGroup, prgCmds, cmdtextf):
        # 'cmdtextf' is the 'cmdtextf' element from the OLECMDTEXT structure,
        # or None if a NULL pointer was passed.
        result = []
        for id, flags in prgCmds:
            flags |= axcontrol.OLECMDF_SUPPORTED | axcontrol.OLECMDF_ENABLED
            result.append((id, flags))
        if cmdtextf is None:
            cmdtext = None  # must return None if nothing requested.
        # IE never seems to want any text - this code is here for
        # demo purposes only
        elif cmdtextf == axcontrol.OLECMDTEXTF_NAME:
            cmdtext = "IEButton Name"
        else:
            cmdtext = "IEButton State"
        return result, cmdtext

    def Exec(self, pguidCmdGroup, nCmdID, nCmdExecOpt, pvaIn):
        print(pguidCmdGroup, nCmdID, nCmdExecOpt, pvaIn)
        print("IOleCommandTarget::Exec called.")
        # self.webbrowser.ShowBrowserBar(GUID_IETOOLBAR, not is_ietoolbar_visible())

    def SetSite(self, unknown):
        if unknown:
            # first get a command target
            cmdtarget = unknown.QueryInterface(axcontrol.IID_IOleCommandTarget)
            # then travel over to a service provider
            serviceprovider = cmdtarget.QueryInterface(pythoncom.IID_IServiceProvider)
            # finally ask for the internet explorer application, returned as a dispatch object
            self.webbrowser = win32com.client.Dispatch(
                serviceprovider.QueryService(
                    "{0002DF05-0000-0000-C000-000000000046}", pythoncom.IID_IDispatch
                )
            )
        else:
            # lose all references
            self.webbrowser = None

    def GetClassID(self):
        return self._reg_clsid_


def register(classobj):
    import winreg

    subKeyCLSID = (
        "SOFTWARE\\Microsoft\\Internet Explorer\\Extensions\\%38s"
        % classobj._reg_clsid_
    )
    try:
        hKey = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, subKeyCLSID)
        subKey = winreg.SetValueEx(
            hKey, "ButtonText", 0, winreg.REG_SZ, classobj._button_text_
        )
        winreg.SetValueEx(
            hKey, "ClsidExtension", 0, winreg.REG_SZ, classobj._reg_clsid_
        )  # reg value for calling COM object
        winreg.SetValueEx(
            hKey, "CLSID", 0, winreg.REG_SZ, "{1FBA04EE-3024-11D2-8F1F-0000F87ABD16}"
        )  # CLSID for button that sends command to COM object
        winreg.SetValueEx(hKey, "Default Visible", 0, winreg.REG_SZ, "Yes")
        winreg.SetValueEx(hKey, "ToolTip", 0, winreg.REG_SZ, classobj._tool_tip_)
        winreg.SetValueEx(hKey, "Icon", 0, winreg.REG_SZ, classobj._icon_)
        winreg.SetValueEx(hKey, "HotIcon", 0, winreg.REG_SZ, classobj._hot_icon_)
    except OSError:
        print("Couldn't set standard toolbar reg keys.")
    else:
        print("Set standard toolbar reg keys.")


def unregister(classobj):
    import winreg

    subKeyCLSID = (
        "SOFTWARE\\Microsoft\\Internet Explorer\\Extensions\\%38s"
        % classobj._reg_clsid_
    )
    try:
        hKey = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, subKeyCLSID)
        subKey = winreg.DeleteValue(hKey, "ButtonText")
        winreg.DeleteValue(hKey, "ClsidExtension")  # for calling COM object
        winreg.DeleteValue(hKey, "CLSID")
        winreg.DeleteValue(hKey, "Default Visible")
        winreg.DeleteValue(hKey, "ToolTip")
        winreg.DeleteValue(hKey, "Icon")
        winreg.DeleteValue(hKey, "HotIcon")
        winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, subKeyCLSID)
    except OSError:
        print("Couldn't delete Standard toolbar regkey.")
    else:
        print("Deleted Standard toolbar regkey.")


#
# test implementation
#


class PyWin32InternetExplorerButton(IEButton):
    _reg_clsid_ = "{104B66A9-9E68-49D1-A3F5-94754BE9E0E6}"
    _reg_progid_ = "PyWin32.IEButton"
    _reg_desc_ = "Test Button"
    _button_text_ = "IE Button"
    _tool_tip_ = "An example implementation for an IE Button."
    _icon_ = ""
    _hot_icon_ = _icon_


def DllRegisterServer():
    register(PyWin32InternetExplorerButton)


def DllUnregisterServer():
    unregister(PyWin32InternetExplorerButton)


if __name__ == "__main__":
    win32com.server.register.UseCommandLine(
        PyWin32InternetExplorerButton,
        finalize_register=DllRegisterServer,
        finalize_unregister=DllUnregisterServer,
    )

# === NexusCore/openenv\Lib\site-packages\nltk\book.py ===
# Natural Language Toolkit: Some texts for exploration in chapter 1 of the book
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus import (
    genesis,
    gutenberg,
    inaugural,
    nps_chat,
    treebank,
    webtext,
    wordnet,
)
from nltk.probability import FreqDist
from nltk.text import Text
from nltk.util import bigrams

print("*** Introductory Examples for the NLTK Book ***")
print("Loading text1, ..., text9 and sent1, ..., sent9")
print("Type the name of the text or sentence to view it.")
print("Type: 'texts()' or 'sents()' to list the materials.")

text1 = Text(gutenberg.words("melville-moby_dick.txt"))
print("text1:", text1.name)

text2 = Text(gutenberg.words("austen-sense.txt"))
print("text2:", text2.name)

text3 = Text(genesis.words("english-kjv.txt"), name="The Book of Genesis")
print("text3:", text3.name)

text4 = Text(inaugural.words(), name="Inaugural Address Corpus")
print("text4:", text4.name)

text5 = Text(nps_chat.words(), name="Chat Corpus")
print("text5:", text5.name)

text6 = Text(webtext.words("grail.txt"), name="Monty Python and the Holy Grail")
print("text6:", text6.name)

text7 = Text(treebank.words(), name="Wall Street Journal")
print("text7:", text7.name)

text8 = Text(webtext.words("singles.txt"), name="Personals Corpus")
print("text8:", text8.name)

text9 = Text(gutenberg.words("chesterton-thursday.txt"))
print("text9:", text9.name)


def texts():
    print("text1:", text1.name)
    print("text2:", text2.name)
    print("text3:", text3.name)
    print("text4:", text4.name)
    print("text5:", text5.name)
    print("text6:", text6.name)
    print("text7:", text7.name)
    print("text8:", text8.name)
    print("text9:", text9.name)


sent1 = ["Call", "me", "Ishmael", "."]
sent2 = [
    "The",
    "family",
    "of",
    "Dashwood",
    "had",
    "long",
    "been",
    "settled",
    "in",
    "Sussex",
    ".",
]
sent3 = [
    "In",
    "the",
    "beginning",
    "God",
    "created",
    "the",
    "heaven",
    "and",
    "the",
    "earth",
    ".",
]
sent4 = [
    "Fellow",
    "-",
    "Citizens",
    "of",
    "the",
    "Senate",
    "and",
    "of",
    "the",
    "House",
    "of",
    "Representatives",
    ":",
]
sent5 = [
    "I",
    "have",
    "a",
    "problem",
    "with",
    "people",
    "PMing",
    "me",
    "to",
    "lol",
    "JOIN",
]
sent6 = [
    "SCENE",
    "1",
    ":",
    "[",
    "wind",
    "]",
    "[",
    "clop",
    "clop",
    "clop",
    "]",
    "KING",
    "ARTHUR",
    ":",
    "Whoa",
    "there",
    "!",
]
sent7 = [
    "Pierre",
    "Vinken",
    ",",
    "61",
    "years",
    "old",
    ",",
    "will",
    "join",
    "the",
    "board",
    "as",
    "a",
    "nonexecutive",
    "director",
    "Nov.",
    "29",
    ".",
]
sent8 = [
    "25",
    "SEXY",
    "MALE",
    ",",
    "seeks",
    "attrac",
    "older",
    "single",
    "lady",
    ",",
    "for",
    "discreet",
    "encounters",
    ".",
]
sent9 = [
    "THE",
    "suburb",
    "of",
    "Saffron",
    "Park",
    "lay",
    "on",
    "the",
    "sunset",
    "side",
    "of",
    "London",
    ",",
    "as",
    "red",
    "and",
    "ragged",
    "as",
    "a",
    "cloud",
    "of",
    "sunset",
    ".",
]


def sents():
    print("sent1:", " ".join(sent1))
    print("sent2:", " ".join(sent2))
    print("sent3:", " ".join(sent3))
    print("sent4:", " ".join(sent4))
    print("sent5:", " ".join(sent5))
    print("sent6:", " ".join(sent6))
    print("sent7:", " ".join(sent7))
    print("sent8:", " ".join(sent8))
    print("sent9:", " ".join(sent9))

# === NexusCore/openenv\Lib\site-packages\yarl\_quoting_py.py ===
import codecs
import re
from string import ascii_letters, ascii_lowercase, digits
from typing import Union, cast, overload

BASCII_LOWERCASE = ascii_lowercase.encode("ascii")
BPCT_ALLOWED = {f"%{i:02X}".encode("ascii") for i in range(256)}
GEN_DELIMS = ":/?#[]@"
SUB_DELIMS_WITHOUT_QS = "!$'()*,"
SUB_DELIMS = SUB_DELIMS_WITHOUT_QS + "+&=;"
RESERVED = GEN_DELIMS + SUB_DELIMS
UNRESERVED = ascii_letters + digits + "-._~"
ALLOWED = UNRESERVED + SUB_DELIMS_WITHOUT_QS


_IS_HEX = re.compile(b"[A-Z0-9][A-Z0-9]")
_IS_HEX_STR = re.compile("[A-Fa-f0-9][A-Fa-f0-9]")

utf8_decoder = codecs.getincrementaldecoder("utf-8")


class _Quoter:
    def __init__(
        self,
        *,
        safe: str = "",
        protected: str = "",
        qs: bool = False,
        requote: bool = True,
    ) -> None:
        self._safe = safe
        self._protected = protected
        self._qs = qs
        self._requote = requote

    @overload
    def __call__(self, val: str) -> str: ...
    @overload
    def __call__(self, val: None) -> None: ...
    def __call__(self, val: Union[str, None]) -> Union[str, None]:
        if val is None:
            return None
        if not isinstance(val, str):
            raise TypeError("Argument should be str")
        if not val:
            return ""
        bval = val.encode("utf8", errors="ignore")
        ret = bytearray()
        pct = bytearray()
        safe = self._safe
        safe += ALLOWED
        if not self._qs:
            safe += "+&=;"
        safe += self._protected
        bsafe = safe.encode("ascii")
        idx = 0
        while idx < len(bval):
            ch = bval[idx]
            idx += 1

            if pct:
                if ch in BASCII_LOWERCASE:
                    ch = ch - 32  # convert to uppercase
                pct.append(ch)
                if len(pct) == 3:  # pragma: no branch   # peephole optimizer
                    buf = pct[1:]
                    if not _IS_HEX.match(buf):
                        ret.extend(b"%25")
                        pct.clear()
                        idx -= 2
                        continue
                    try:
                        unquoted = chr(int(pct[1:].decode("ascii"), base=16))
                    except ValueError:
                        ret.extend(b"%25")
                        pct.clear()
                        idx -= 2
                        continue

                    if unquoted in self._protected:
                        ret.extend(pct)
                    elif unquoted in safe:
                        ret.append(ord(unquoted))
                    else:
                        ret.extend(pct)
                    pct.clear()

                # special case, if we have only one char after "%"
                elif len(pct) == 2 and idx == len(bval):
                    ret.extend(b"%25")
                    pct.clear()
                    idx -= 1

                continue

            elif ch == ord("%") and self._requote:
                pct.clear()
                pct.append(ch)

                # special case if "%" is last char
                if idx == len(bval):
                    ret.extend(b"%25")

                continue

            if self._qs and ch == ord(" "):
                ret.append(ord("+"))
                continue
            if ch in bsafe:
                ret.append(ch)
                continue

            ret.extend((f"%{ch:02X}").encode("ascii"))

        ret2 = ret.decode("ascii")
        if ret2 == val:
            return val
        return ret2


class _Unquoter:
    def __init__(
        self,
        *,
        ignore: str = "",
        unsafe: str = "",
        qs: bool = False,
        plus: bool = False,
    ) -> None:
        self._ignore = ignore
        self._unsafe = unsafe
        self._qs = qs
        self._plus = plus  # to match urllib.parse.unquote_plus
        self._quoter = _Quoter()
        self._qs_quoter = _Quoter(qs=True)

    @overload
    def __call__(self, val: str) -> str: ...
    @overload
    def __call__(self, val: None) -> None: ...
    def __call__(self, val: Union[str, None]) -> Union[str, None]:
        if val is None:
            return None
        if not isinstance(val, str):
            raise TypeError("Argument should be str")
        if not val:
            return ""
        decoder = cast(codecs.BufferedIncrementalDecoder, utf8_decoder())
        ret = []
        idx = 0
        while idx < len(val):
            ch = val[idx]
            idx += 1
            if ch == "%" and idx <= len(val) - 2:
                pct = val[idx : idx + 2]
                if _IS_HEX_STR.fullmatch(pct):
                    b = bytes([int(pct, base=16)])
                    idx += 2
                    try:
                        unquoted = decoder.decode(b)
                    except UnicodeDecodeError:
                        start_pct = idx - 3 - len(decoder.buffer) * 3
                        ret.append(val[start_pct : idx - 3])
                        decoder.reset()
                        try:
                            unquoted = decoder.decode(b)
                        except UnicodeDecodeError:
                            ret.append(val[idx - 3 : idx])
                            continue
                    if not unquoted:
                        continue
                    if self._qs and unquoted in "+=&;":
                        to_add = self._qs_quoter(unquoted)
                        if to_add is None:  # pragma: no cover
                            raise RuntimeError("Cannot quote None")
                        ret.append(to_add)
                    elif unquoted in self._unsafe or unquoted in self._ignore:
                        to_add = self._quoter(unquoted)
                        if to_add is None:  # pragma: no cover
                            raise RuntimeError("Cannot quote None")
                        ret.append(to_add)
                    else:
                        ret.append(unquoted)
                    continue

            if decoder.buffer:
                start_pct = idx - 1 - len(decoder.buffer) * 3
                ret.append(val[start_pct : idx - 1])
                decoder.reset()

            if ch == "+":
                if (not self._qs and not self._plus) or ch in self._unsafe:
                    ret.append("+")
                else:
                    ret.append(" ")
                continue

            if ch in self._unsafe:
                ret.append("%")
                h = hex(ord(ch)).upper()[2:]
                for ch in h:
                    ret.append(ch)
                continue

            ret.append(ch)

        if decoder.buffer:
            ret.append(val[-len(decoder.buffer) * 3 :])

        ret2 = "".join(ret)
        if ret2 == val:
            return val
        return ret2

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\libarchive.py ===
from contextlib import contextmanager
from ctypes import (
    CFUNCTYPE,
    POINTER,
    c_int,
    c_longlong,
    c_void_p,
    cast,
    create_string_buffer,
)

import libarchive
import libarchive.ffi as ffi

from fsspec import open_files
from fsspec.archive import AbstractArchiveFileSystem
from fsspec.implementations.memory import MemoryFile
from fsspec.utils import DEFAULT_BLOCK_SIZE

# Libarchive requires seekable files or memory only for certain archive
# types. However, since we read the directory first to cache the contents
# and also allow random access to any file, the file-like object needs
# to be seekable no matter what.

# Seek call-backs (not provided in the libarchive python wrapper)
SEEK_CALLBACK = CFUNCTYPE(c_longlong, c_int, c_void_p, c_longlong, c_int)
read_set_seek_callback = ffi.ffi(
    "read_set_seek_callback", [ffi.c_archive_p, SEEK_CALLBACK], c_int, ffi.check_int
)
new_api = hasattr(ffi, "NO_OPEN_CB")


@contextmanager
def custom_reader(file, format_name="all", filter_name="all", block_size=ffi.page_size):
    """Read an archive from a seekable file-like object.

    The `file` object must support the standard `readinto` and 'seek' methods.
    """
    buf = create_string_buffer(block_size)
    buf_p = cast(buf, c_void_p)

    def read_func(archive_p, context, ptrptr):
        # readinto the buffer, returns number of bytes read
        length = file.readinto(buf)
        # write the address of the buffer into the pointer
        ptrptr = cast(ptrptr, POINTER(c_void_p))
        ptrptr[0] = buf_p
        # tell libarchive how much data was written into the buffer
        return length

    def seek_func(archive_p, context, offset, whence):
        file.seek(offset, whence)
        # tell libarchvie the current position
        return file.tell()

    read_cb = ffi.READ_CALLBACK(read_func)
    seek_cb = SEEK_CALLBACK(seek_func)

    if new_api:
        open_cb = ffi.NO_OPEN_CB
        close_cb = ffi.NO_CLOSE_CB
    else:
        open_cb = libarchive.read.OPEN_CALLBACK(ffi.VOID_CB)
        close_cb = libarchive.read.CLOSE_CALLBACK(ffi.VOID_CB)

    with libarchive.read.new_archive_read(format_name, filter_name) as archive_p:
        read_set_seek_callback(archive_p, seek_cb)
        ffi.read_open(archive_p, None, open_cb, read_cb, close_cb)
        yield libarchive.read.ArchiveRead(archive_p)


class LibArchiveFileSystem(AbstractArchiveFileSystem):
    """Compressed archives as a file-system (read-only)

    Supports the following formats:
    tar, pax , cpio, ISO9660, zip, mtree, shar, ar, raw, xar, lha/lzh, rar
    Microsoft CAB, 7-Zip, WARC

    See the libarchive documentation for further restrictions.
    https://www.libarchive.org/

    Keeps file object open while instance lives. It only works in seekable
    file-like objects. In case the filesystem does not support this kind of
    file object, it is recommended to cache locally.

    This class is pickleable, but not necessarily thread-safe (depends on the
    platform). See libarchive documentation for details.
    """

    root_marker = ""
    protocol = "libarchive"
    cachable = False

    def __init__(
        self,
        fo="",
        mode="r",
        target_protocol=None,
        target_options=None,
        block_size=DEFAULT_BLOCK_SIZE,
        **kwargs,
    ):
        """
        Parameters
        ----------
        fo: str or file-like
            Contains ZIP, and must exist. If a str, will fetch file using
            :meth:`~fsspec.open_files`, which must return one file exactly.
        mode: str
            Currently, only 'r' accepted
        target_protocol: str (optional)
            If ``fo`` is a string, this value can be used to override the
            FS protocol inferred from a URL
        target_options: dict (optional)
            Kwargs passed when instantiating the target FS, if ``fo`` is
            a string.
        """
        super().__init__(self, **kwargs)
        if mode != "r":
            raise ValueError("Only read from archive files accepted")
        if isinstance(fo, str):
            files = open_files(fo, protocol=target_protocol, **(target_options or {}))
            if len(files) != 1:
                raise ValueError(
                    f'Path "{fo}" did not resolve to exactly one file: "{files}"'
                )
            fo = files[0]
        self.of = fo
        self.fo = fo.__enter__()  # the whole instance is a context
        self.block_size = block_size
        self.dir_cache = None

    @contextmanager
    def _open_archive(self):
        self.fo.seek(0)
        with custom_reader(self.fo, block_size=self.block_size) as arc:
            yield arc

    @classmethod
    def _strip_protocol(cls, path):
        # file paths are always relative to the archive root
        return super()._strip_protocol(path).lstrip("/")

    def _get_dirs(self):
        fields = {
            "name": "pathname",
            "size": "size",
            "created": "ctime",
            "mode": "mode",
            "uid": "uid",
            "gid": "gid",
            "mtime": "mtime",
        }

        if self.dir_cache is not None:
            return

        self.dir_cache = {}
        list_names = []
        with self._open_archive() as arc:
            for entry in arc:
                if not entry.isdir and not entry.isfile:
                    # Skip symbolic links, fifo entries, etc.
                    continue
                self.dir_cache.update(
                    {
                        dirname: {"name": dirname, "size": 0, "type": "directory"}
                        for dirname in self._all_dirnames(set(entry.name))
                    }
                )
                f = {key: getattr(entry, fields[key]) for key in fields}
                f["type"] = "directory" if entry.isdir else "file"
                list_names.append(entry.name)

                self.dir_cache[f["name"]] = f
        # libarchive does not seem to return an entry for the directories (at least
        # not in all formats), so get the directories names from the files names
        self.dir_cache.update(
            {
                dirname: {"name": dirname, "size": 0, "type": "directory"}
                for dirname in self._all_dirnames(list_names)
            }
        )

    def _open(
        self,
        path,
        mode="rb",
        block_size=None,
        autocommit=True,
        cache_options=None,
        **kwargs,
    ):
        path = self._strip_protocol(path)
        if mode != "rb":
            raise NotImplementedError

        data = bytes()
        with self._open_archive() as arc:
            for entry in arc:
                if entry.pathname != path:
                    continue

                if entry.size == 0:
                    # empty file, so there are no blocks
                    break

                for block in entry.get_blocks(entry.size):
                    data = block
                    break
                else:
                    raise ValueError
        return MemoryFile(fs=self, path=path, data=data)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\text_service\transports\base.py ===
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

from google.ai.generativelanguage_v1beta3 import gapic_version as package_version
from google.ai.generativelanguage_v1beta3.types import text_service

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class TextServiceTransport(abc.ABC):
    """Abstract transport class for TextService."""

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
            self.generate_text: gapic_v1.method.wrap_method(
                self.generate_text,
                default_timeout=None,
                client_info=client_info,
            ),
            self.embed_text: gapic_v1.method.wrap_method(
                self.embed_text,
                default_timeout=None,
                client_info=client_info,
            ),
            self.batch_embed_text: gapic_v1.method.wrap_method(
                self.batch_embed_text,
                default_timeout=None,
                client_info=client_info,
            ),
            self.count_text_tokens: gapic_v1.method.wrap_method(
                self.count_text_tokens,
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
    def generate_text(
        self,
    ) -> Callable[
        [text_service.GenerateTextRequest],
        Union[
            text_service.GenerateTextResponse,
            Awaitable[text_service.GenerateTextResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def embed_text(
        self,
    ) -> Callable[
        [text_service.EmbedTextRequest],
        Union[
            text_service.EmbedTextResponse, Awaitable[text_service.EmbedTextResponse]
        ],
    ]:
        raise NotImplementedError()

    @property
    def batch_embed_text(
        self,
    ) -> Callable[
        [text_service.BatchEmbedTextRequest],
        Union[
            text_service.BatchEmbedTextResponse,
            Awaitable[text_service.BatchEmbedTextResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def count_text_tokens(
        self,
    ) -> Callable[
        [text_service.CountTextTokensRequest],
        Union[
            text_service.CountTextTokensResponse,
            Awaitable[text_service.CountTextTokensResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("TextServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\utils\computer_vision.py ===
import io

from ...utils.lazy_import import lazy_import

# Lazy import of optional packages
np = lazy_import("numpy")
try:
    cv2 = lazy_import("cv2")
except:
    cv2 = None  # Fixes colab error
PIL = lazy_import("PIL")
pytesseract = lazy_import("pytesseract")


def pytesseract_get_text(img):
    # List the attributes of pytesseract, which will trigger lazy loading of it
    attributes = dir(pytesseract)
    if pytesseract == None:
        raise ImportError("The pytesseract module could not be imported.")

    result = pytesseract.image_to_string(img)
    return result


def pytesseract_get_text_bounding_boxes(img):
    # Convert PIL Image to NumPy array
    img_array = np.array(img)

    # Convert the image to grayscale
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

    # Use pytesseract to get the data from the image
    d = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

    # Create an empty list to hold dictionaries for each bounding box
    boxes = []

    # Iterate through the number of detected boxes based on the length of one of the property lists
    for i in range(len(d["text"])):
        # For each box, create a dictionary with the properties you're interested in
        box = {
            "text": d["text"][i],
            "top": d["top"][i],
            "left": d["left"][i],
            "width": d["width"][i],
            "height": d["height"][i],
        }
        # Append this box dictionary to the list
        boxes.append(box)

    return boxes


def find_text_in_image(img, text, debug=False):
    # Convert PIL Image to NumPy array
    img_array = np.array(img)

    # Convert the image to grayscale
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

    # Use pytesseract to get the data from the image
    d = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

    # Initialize an empty list to store the centers of the bounding boxes
    centers = []

    # Get the number of detected boxes
    n_boxes = len(d["level"])

    # Create a copy of the grayscale image to draw on
    img_draw = np.array(gray.copy())

    # Convert the img_draw grayscale image to RGB
    img_draw = cv2.cvtColor(img_draw, cv2.COLOR_GRAY2RGB)

    id = 0

    # Loop through each box
    for i in range(n_boxes):
        if debug:
            # (DEBUGGING) Draw each box on the grayscale image
            cv2.rectangle(
                img_draw,
                (d["left"][i], d["top"][i]),
                (d["left"][i] + d["width"][i], d["top"][i] + d["height"][i]),
                (0, 255, 0),
                2,
            )
            # Draw the detected text in the rectangle in small font
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            font_color = (0, 0, 255)
            line_type = 2

            cv2.putText(
                img_draw,
                d["text"][i],
                (d["left"][i], d["top"][i] - 10),
                font,
                font_scale,
                font_color,
                line_type,
            )

        # Print the text of the box
        # If the text in the box matches the given text
        if text.lower() in d["text"][i].lower():
            # Find the start index of the matching text in the box
            start_index = d["text"][i].lower().find(text.lower())
            # Calculate the percentage of the box width that the start of the matching text represents
            start_percentage = start_index / len(d["text"][i])
            # Move the left edge of the box to the right by this percentage of the box width
            d["left"][i] = d["left"][i] + int(d["width"][i] * start_percentage)

            # Calculate the width of the matching text relative to the entire text in the box
            text_width_percentage = len(text) / len(d["text"][i])
            # Adjust the width of the box to match the width of the matching text
            d["width"][i] = int(d["width"][i] * text_width_percentage)

            # Calculate the center of the bounding box
            center = (
                d["left"][i] + d["width"][i] / 2,
                d["top"][i] + d["height"][i] / 2,
            )

            # Add the center to the list
            centers.append(center)

            # Draw the bounding box on the image in red and make it slightly larger
            larger = 10
            cv2.rectangle(
                img_draw,
                (d["left"][i] - larger, d["top"][i] - larger),
                (
                    d["left"][i] + d["width"][i] + larger,
                    d["top"][i] + d["height"][i] + larger,
                ),
                (255, 0, 0),
                7,
            )

            # Create a small black square background for the ID
            cv2.rectangle(
                img_draw,
                (
                    d["left"][i] + d["width"][i] // 2 - larger * 2,
                    d["top"][i] + d["height"][i] // 2 - larger * 2,
                ),
                (
                    d["left"][i] + d["width"][i] // 2 + larger * 2,
                    d["top"][i] + d["height"][i] // 2 + larger * 2,
                ),
                (0, 0, 0),
                -1,
            )

            # Put the ID in the center of the bounding box in red
            cv2.putText(
                img_draw,
                str(id),
                (
                    d["left"][i] + d["width"][i] // 2 - larger,
                    d["top"][i] + d["height"][i] // 2 + larger,
                ),
                cv2.FONT_HERSHEY_DUPLEX,
                1,
                (255, 155, 155),
                4,
            )

            # Increment id
            id += 1

    if not centers:
        word_centers = []
        for word in text.split():
            for i in range(n_boxes):
                if word.lower() in d["text"][i].lower():
                    center = (
                        d["left"][i] + d["width"][i] / 2,
                        d["top"][i] + d["height"][i] / 2,
                    )
                    center = (center[0] / 2, center[1] / 2)
                    word_centers.append(center)

        for center1 in word_centers:
            for center2 in word_centers:
                if (
                    center1 != center2
                    and (
                        (center1[0] - center2[0]) ** 2 + (center1[1] - center2[1]) ** 2
                    )
                    ** 0.5
                    <= 400
                ):
                    centers.append(
                        ((center1[0] + center2[0]) / 2, (center1[1] + center2[1]) / 2)
                    )
                    break
            if centers:
                break

    bounding_box_image = PIL.Image.fromarray(img_draw)
    bounding_box_image.format = img.format

    # Convert centers to relative
    img_width, img_height = img.size
    centers = [(x / img_width, y / img_height) for x, y in centers]

    # Debug by showing bounding boxes:
    # bounding_box_image.show()

    return centers

# === NexusCore/openenv\Lib\site-packages\jedi\inference\analysis.py ===
"""
Module for statical analysis.
"""
from parso.python import tree

from jedi import debug
from jedi.inference.helpers import is_string


CODES = {
    'attribute-error': (1, AttributeError, 'Potential AttributeError.'),
    'name-error': (2, NameError, 'Potential NameError.'),
    'import-error': (3, ImportError, 'Potential ImportError.'),
    'type-error-too-many-arguments': (4, TypeError, None),
    'type-error-too-few-arguments': (5, TypeError, None),
    'type-error-keyword-argument': (6, TypeError, None),
    'type-error-multiple-values': (7, TypeError, None),
    'type-error-star-star': (8, TypeError, None),
    'type-error-star': (9, TypeError, None),
    'type-error-operation': (10, TypeError, None),
    'type-error-not-iterable': (11, TypeError, None),
    'type-error-isinstance': (12, TypeError, None),
    'type-error-not-subscriptable': (13, TypeError, None),
    'value-error-too-many-values': (14, ValueError, None),
    'value-error-too-few-values': (15, ValueError, None),
}


class Error:
    def __init__(self, name, module_path, start_pos, message=None):
        self.path = module_path
        self._start_pos = start_pos
        self.name = name
        if message is None:
            message = CODES[self.name][2]
        self.message = message

    @property
    def line(self):
        return self._start_pos[0]

    @property
    def column(self):
        return self._start_pos[1]

    @property
    def code(self):
        # The class name start
        first = self.__class__.__name__[0]
        return first + str(CODES[self.name][0])

    def __str__(self):
        return '%s:%s:%s: %s %s' % (self.path, self.line, self.column,
                                    self.code, self.message)

    def __eq__(self, other):
        return (self.path == other.path and self.name == other.name
                and self._start_pos == other._start_pos)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.path, self._start_pos, self.name))

    def __repr__(self):
        return '<%s %s: %s@%s,%s>' % (self.__class__.__name__,
                                      self.name, self.path,
                                      self._start_pos[0], self._start_pos[1])


class Warning(Error):
    pass


def add(node_context, error_name, node, message=None, typ=Error, payload=None):
    exception = CODES[error_name][1]
    if _check_for_exception_catch(node_context, node, exception, payload):
        return

    # TODO this path is probably not right
    module_context = node_context.get_root_context()
    module_path = module_context.py__file__()
    issue_instance = typ(error_name, module_path, node.start_pos, message)
    debug.warning(str(issue_instance), format=False)
    node_context.inference_state.analysis.append(issue_instance)
    return issue_instance


def _check_for_setattr(instance):
    """
    Check if there's any setattr method inside an instance. If so, return True.
    """
    module = instance.get_root_context()
    node = module.tree_node
    if node is None:
        # If it's a compiled module or doesn't have a tree_node
        return False

    try:
        stmt_names = node.get_used_names()['setattr']
    except KeyError:
        return False

    return any(node.start_pos < n.start_pos < node.end_pos
               # Check if it's a function called setattr.
               and not (n.parent.type == 'funcdef' and n.parent.name == n)
               for n in stmt_names)


def add_attribute_error(name_context, lookup_value, name):
    message = ('AttributeError: %s has no attribute %s.' % (lookup_value, name))
    # Check for __getattr__/__getattribute__ existance and issue a warning
    # instead of an error, if that happens.
    typ = Error
    if lookup_value.is_instance() and not lookup_value.is_compiled():
        # TODO maybe make a warning for __getattr__/__getattribute__

        if _check_for_setattr(lookup_value):
            typ = Warning

    payload = lookup_value, name
    add(name_context, 'attribute-error', name, message, typ, payload)


def _check_for_exception_catch(node_context, jedi_name, exception, payload=None):
    """
    Checks if a jedi object (e.g. `Statement`) sits inside a try/catch and
    doesn't count as an error (if equal to `exception`).
    Also checks `hasattr` for AttributeErrors and uses the `payload` to compare
    it.
    Returns True if the exception was catched.
    """
    def check_match(cls, exception):
        if not cls.is_class():
            return False

        for python_cls in exception.mro():
            if cls.py__name__() == python_cls.__name__ \
                    and cls.parent_context.is_builtins_module():
                return True
        return False

    def check_try_for_except(obj, exception):
        # Only nodes in try
        iterator = iter(obj.children)
        for branch_type in iterator:
            next(iterator)  # The colon
            suite = next(iterator)
            if branch_type == 'try' \
                    and not (branch_type.start_pos < jedi_name.start_pos <= suite.end_pos):
                return False

        for node in obj.get_except_clause_tests():
            if node is None:
                return True  # An exception block that catches everything.
            else:
                except_classes = node_context.infer_node(node)
                for cls in except_classes:
                    from jedi.inference.value import iterable
                    if isinstance(cls, iterable.Sequence) and \
                            cls.array_type == 'tuple':
                        # multiple exceptions
                        for lazy_value in cls.py__iter__():
                            for typ in lazy_value.infer():
                                if check_match(typ, exception):
                                    return True
                    else:
                        if check_match(cls, exception):
                            return True

    def check_hasattr(node, suite):
        try:
            assert suite.start_pos <= jedi_name.start_pos < suite.end_pos
            assert node.type in ('power', 'atom_expr')
            base = node.children[0]
            assert base.type == 'name' and base.value == 'hasattr'
            trailer = node.children[1]
            assert trailer.type == 'trailer'
            arglist = trailer.children[1]
            assert arglist.type == 'arglist'
            from jedi.inference.arguments import TreeArguments
            args = TreeArguments(node_context.inference_state, node_context, arglist)
            unpacked_args = list(args.unpack())
            # Arguments should be very simple
            assert len(unpacked_args) == 2

            # Check name
            key, lazy_value = unpacked_args[1]
            names = list(lazy_value.infer())
            assert len(names) == 1 and is_string(names[0])
            assert names[0].get_safe_value() == payload[1].value

            # Check objects
            key, lazy_value = unpacked_args[0]
            objects = lazy_value.infer()
            return payload[0] in objects
        except AssertionError:
            return False

    obj = jedi_name
    while obj is not None and not isinstance(obj, (tree.Function, tree.Class)):
        if isinstance(obj, tree.Flow):
            # try/except catch check
            if obj.type == 'try_stmt' and check_try_for_except(obj, exception):
                return True
            # hasattr check
            if exception == AttributeError and obj.type in ('if_stmt', 'while_stmt'):
                if check_hasattr(obj.children[1], obj.children[3]):
                    return True
        obj = obj.parent

    return False

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\backend_template.py ===
"""
A fully functional, do-nothing backend intended as a template for backend
writers.  It is fully functional in that you can select it as a backend e.g.
with ::

    import matplotlib
    matplotlib.use("template")

and your program will (should!) run without error, though no output is
produced.  This provides a starting point for backend writers; you can
selectively implement drawing methods (`~.RendererTemplate.draw_path`,
`~.RendererTemplate.draw_image`, etc.) and slowly see your figure come to life
instead having to have a full-blown implementation before getting any results.

Copy this file to a directory outside the Matplotlib source tree, somewhere
where Python can import it (by adding the directory to your ``sys.path`` or by
packaging it as a normal Python package); if the backend is importable as
``import my.backend`` you can then select it using ::

    import matplotlib
    matplotlib.use("module://my.backend")

If your backend implements support for saving figures (i.e. has a ``print_xyz`` method),
you can register it as the default handler for a given file type::

    from matplotlib.backend_bases import register_backend
    register_backend('xyz', 'my_backend', 'XYZ File Format')
    ...
    plt.savefig("figure.xyz")
"""

from matplotlib import _api
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import (
     FigureCanvasBase, FigureManagerBase, GraphicsContextBase, RendererBase)
from matplotlib.figure import Figure


class RendererTemplate(RendererBase):
    """
    The renderer handles drawing/rendering operations.

    This is a minimal do-nothing class that can be used to get started when
    writing a new backend.  Refer to `.backend_bases.RendererBase` for
    documentation of the methods.
    """

    def __init__(self, dpi):
        super().__init__()
        self.dpi = dpi

    def draw_path(self, gc, path, transform, rgbFace=None):
        pass

    # draw_markers is optional, and we get more correct relative
    # timings by leaving it out.  backend implementers concerned with
    # performance will probably want to implement it
#     def draw_markers(self, gc, marker_path, marker_trans, path, trans,
#                      rgbFace=None):
#         pass

    # draw_path_collection is optional, and we get more correct
    # relative timings by leaving it out. backend implementers concerned with
    # performance will probably want to implement it
#     def draw_path_collection(self, gc, master_transform, paths,
#                              all_transforms, offsets, offset_trans,
#                              facecolors, edgecolors, linewidths, linestyles,
#                              antialiaseds):
#         pass

    # draw_quad_mesh is optional, and we get more correct
    # relative timings by leaving it out.  backend implementers concerned with
    # performance will probably want to implement it
#     def draw_quad_mesh(self, gc, master_transform, meshWidth, meshHeight,
#                        coordinates, offsets, offsetTrans, facecolors,
#                        antialiased, edgecolors):
#         pass

    def draw_image(self, gc, x, y, im):
        pass

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False, mtext=None):
        pass

    def flipy(self):
        # docstring inherited
        return True

    def get_canvas_width_height(self):
        # docstring inherited
        return 100, 100

    def get_text_width_height_descent(self, s, prop, ismath):
        return 1, 1, 1

    def new_gc(self):
        # docstring inherited
        return GraphicsContextTemplate()

    def points_to_pixels(self, points):
        # if backend doesn't have dpi, e.g., postscript or svg
        return points
        # elif backend assumes a value for pixels_per_inch
        # return points/72.0 * self.dpi.get() * pixels_per_inch/72.0
        # else
        # return points/72.0 * self.dpi.get()


class GraphicsContextTemplate(GraphicsContextBase):
    """
    The graphics context provides the color, line styles, etc.  See the cairo
    and postscript backends for examples of mapping the graphics context
    attributes (cap styles, join styles, line widths, colors) to a particular
    backend.  In cairo this is done by wrapping a cairo.Context object and
    forwarding the appropriate calls to it using a dictionary mapping styles
    to gdk constants.  In Postscript, all the work is done by the renderer,
    mapping line styles to postscript calls.

    If it's more appropriate to do the mapping at the renderer level (as in
    the postscript backend), you don't need to override any of the GC methods.
    If it's more appropriate to wrap an instance (as in the cairo backend) and
    do the mapping here, you'll need to override several of the setter
    methods.

    The base GraphicsContext stores colors as an RGB tuple on the unit
    interval, e.g., (0.5, 0.0, 1.0). You may need to map this to colors
    appropriate for your backend.
    """


########################################################################
#
# The following functions and classes are for pyplot and implement
# window/figure managers, etc.
#
########################################################################


class FigureManagerTemplate(FigureManagerBase):
    """
    Helper class for pyplot mode, wraps everything up into a neat bundle.

    For non-interactive backends, the base class is sufficient.  For
    interactive backends, see the documentation of the `.FigureManagerBase`
    class for the list of methods that can/should be overridden.
    """


class FigureCanvasTemplate(FigureCanvasBase):
    """
    The canvas the figure renders into.  Calls the draw and print fig
    methods, creates the renderers, etc.

    Note: GUI templates will want to connect events for button presses,
    mouse movements and key presses to functions that call the base
    class methods button_press_event, button_release_event,
    motion_notify_event, key_press_event, and key_release_event.  See the
    implementations of the interactive backends for examples.

    Attributes
    ----------
    figure : `~matplotlib.figure.Figure`
        A high-level Figure instance
    """

    # The instantiated manager class.  For further customization,
    # ``FigureManager.create_with_canvas`` can also be overridden; see the
    # wx-based backends for an example.
    manager_class = FigureManagerTemplate

    def draw(self):
        """
        Draw the figure using the renderer.

        It is important that this method actually walk the artist tree
        even if not output is produced because this will trigger
        deferred work (like computing limits auto-limits and tick
        values) that users may want access to before saving to disk.
        """
        renderer = RendererTemplate(self.figure.dpi)
        self.figure.draw(renderer)

    # You should provide a print_xxx function for every file format
    # you can write.

    # If the file type is not in the base set of filetypes,
    # you should add it to the class-scope filetypes dictionary as follows:
    filetypes = {**FigureCanvasBase.filetypes, 'foo': 'My magic Foo format'}

    def print_foo(self, filename, **kwargs):
        """
        Write out format foo.

        This method is normally called via `.Figure.savefig` and
        `.FigureCanvasBase.print_figure`, which take care of setting the figure
        facecolor, edgecolor, and dpi to the desired output values, and will
        restore them to the original values.  Therefore, `print_foo` does not
        need to handle these settings.
        """
        self.draw()

    def get_default_filetype(self):
        return 'foo'


########################################################################
#
# Now just provide the standard names that backend.__init__ is expecting
#
########################################################################

FigureCanvas = FigureCanvasTemplate
FigureManager = FigureManagerTemplate

# === NexusCore/openenv\Lib\site-packages\numpy\random\__init__.py ===
"""
========================
Random Number Generation
========================

Use ``default_rng()`` to create a `Generator` and call its methods.

=============== =========================================================
Generator
--------------- ---------------------------------------------------------
Generator       Class implementing all of the random number distributions
default_rng     Default constructor for ``Generator``
=============== =========================================================

============================================= ===
BitGenerator Streams that work with Generator
--------------------------------------------- ---
MT19937
PCG64
PCG64DXSM
Philox
SFC64
============================================= ===

============================================= ===
Getting entropy to initialize a BitGenerator
--------------------------------------------- ---
SeedSequence
============================================= ===


Legacy
------

For backwards compatibility with previous versions of numpy before 1.17, the
various aliases to the global `RandomState` methods are left alone and do not
use the new `Generator` API.

==================== =========================================================
Utility functions
-------------------- ---------------------------------------------------------
random               Uniformly distributed floats over ``[0, 1)``
bytes                Uniformly distributed random bytes.
permutation          Randomly permute a sequence / generate a random sequence.
shuffle              Randomly permute a sequence in place.
choice               Random sample from 1-D array.
==================== =========================================================

==================== =========================================================
Compatibility
functions - removed
in the new API
-------------------- ---------------------------------------------------------
rand                 Uniformly distributed values.
randn                Normally distributed values.
ranf                 Uniformly distributed floating point numbers.
random_integers      Uniformly distributed integers in a given range.
                     (deprecated, use ``integers(..., closed=True)`` instead)
random_sample        Alias for `random_sample`
randint              Uniformly distributed integers in a given range
seed                 Seed the legacy random number generator.
==================== =========================================================

==================== =========================================================
Univariate
distributions
-------------------- ---------------------------------------------------------
beta                 Beta distribution over ``[0, 1]``.
binomial             Binomial distribution.
chisquare            :math:`\\chi^2` distribution.
exponential          Exponential distribution.
f                    F (Fisher-Snedecor) distribution.
gamma                Gamma distribution.
geometric            Geometric distribution.
gumbel               Gumbel distribution.
hypergeometric       Hypergeometric distribution.
laplace              Laplace distribution.
logistic             Logistic distribution.
lognormal            Log-normal distribution.
logseries            Logarithmic series distribution.
negative_binomial    Negative binomial distribution.
noncentral_chisquare Non-central chi-square distribution.
noncentral_f         Non-central F distribution.
normal               Normal / Gaussian distribution.
pareto               Pareto distribution.
poisson              Poisson distribution.
power                Power distribution.
rayleigh             Rayleigh distribution.
triangular           Triangular distribution.
uniform              Uniform distribution.
vonmises             Von Mises circular distribution.
wald                 Wald (inverse Gaussian) distribution.
weibull              Weibull distribution.
zipf                 Zipf's distribution over ranked data.
==================== =========================================================

==================== ==========================================================
Multivariate
distributions
-------------------- ----------------------------------------------------------
dirichlet            Multivariate generalization of Beta distribution.
multinomial          Multivariate generalization of the binomial distribution.
multivariate_normal  Multivariate generalization of the normal distribution.
==================== ==========================================================

==================== =========================================================
Standard
distributions
-------------------- ---------------------------------------------------------
standard_cauchy      Standard Cauchy-Lorentz distribution.
standard_exponential Standard exponential distribution.
standard_gamma       Standard Gamma distribution.
standard_normal      Standard normal distribution.
standard_t           Standard Student's t-distribution.
==================== =========================================================

==================== =========================================================
Internal functions
-------------------- ---------------------------------------------------------
get_state            Get tuple representing internal state of generator.
set_state            Set state of generator.
==================== =========================================================


"""
__all__ = [
    'beta',
    'binomial',
    'bytes',
    'chisquare',
    'choice',
    'dirichlet',
    'exponential',
    'f',
    'gamma',
    'geometric',
    'get_state',
    'gumbel',
    'hypergeometric',
    'laplace',
    'logistic',
    'lognormal',
    'logseries',
    'multinomial',
    'multivariate_normal',
    'negative_binomial',
    'noncentral_chisquare',
    'noncentral_f',
    'normal',
    'pareto',
    'permutation',
    'poisson',
    'power',
    'rand',
    'randint',
    'randn',
    'random',
    'random_integers',
    'random_sample',
    'ranf',
    'rayleigh',
    'sample',
    'seed',
    'set_state',
    'shuffle',
    'standard_cauchy',
    'standard_exponential',
    'standard_gamma',
    'standard_normal',
    'standard_t',
    'triangular',
    'uniform',
    'vonmises',
    'wald',
    'weibull',
    'zipf',
]

# add these for module-freeze analysis (like PyInstaller)
from . import _bounded_integers, _common, _pickle
from ._generator import Generator, default_rng
from ._mt19937 import MT19937
from ._pcg64 import PCG64, PCG64DXSM
from ._philox import Philox
from ._sfc64 import SFC64
from .bit_generator import BitGenerator, SeedSequence
from .mtrand import *

__all__ += ['Generator', 'RandomState', 'SeedSequence', 'MT19937',
            'Philox', 'PCG64', 'PCG64DXSM', 'SFC64', 'default_rng',
            'BitGenerator']


def __RandomState_ctor():
    """Return a RandomState instance.

    This function exists solely to assist (un)pickling.

    Note that the state of the RandomState returned here is irrelevant, as this
    function's entire purpose is to return a newly allocated RandomState whose
    state pickle can set.  Consequently the RandomState returned by this function
    is a freshly allocated copy with a seed=0.

    See https://github.com/numpy/numpy/issues/4763 for a detailed discussion

    """
    return RandomState(seed=0)


from numpy._pytesttester import PytestTester

test = PytestTester(__name__)
del PytestTester

# === NexusCore/openenv\Lib\site-packages\numpy\_typing\_char_codes.py ===
from typing import Literal

_BoolCodes = Literal[
    "bool", "bool_",
    "?", "|?", "=?", "<?", ">?",
    "b1", "|b1", "=b1", "<b1", ">b1",
]  # fmt: skip

_UInt8Codes = Literal["uint8", "u1", "|u1", "=u1", "<u1", ">u1"]
_UInt16Codes = Literal["uint16", "u2", "|u2", "=u2", "<u2", ">u2"]
_UInt32Codes = Literal["uint32", "u4", "|u4", "=u4", "<u4", ">u4"]
_UInt64Codes = Literal["uint64", "u8", "|u8", "=u8", "<u8", ">u8"]

_Int8Codes = Literal["int8", "i1", "|i1", "=i1", "<i1", ">i1"]
_Int16Codes = Literal["int16", "i2", "|i2", "=i2", "<i2", ">i2"]
_Int32Codes = Literal["int32", "i4", "|i4", "=i4", "<i4", ">i4"]
_Int64Codes = Literal["int64", "i8", "|i8", "=i8", "<i8", ">i8"]

_Float16Codes = Literal["float16", "f2", "|f2", "=f2", "<f2", ">f2"]
_Float32Codes = Literal["float32", "f4", "|f4", "=f4", "<f4", ">f4"]
_Float64Codes = Literal["float64", "f8", "|f8", "=f8", "<f8", ">f8"]

_Complex64Codes = Literal["complex64", "c8", "|c8", "=c8", "<c8", ">c8"]
_Complex128Codes = Literal["complex128", "c16", "|c16", "=c16", "<c16", ">c16"]

_ByteCodes = Literal["byte", "b", "|b", "=b", "<b", ">b"]
_ShortCodes = Literal["short", "h", "|h", "=h", "<h", ">h"]
_IntCCodes = Literal["intc", "i", "|i", "=i", "<i", ">i"]
_IntPCodes = Literal["intp", "int", "int_", "n", "|n", "=n", "<n", ">n"]
_LongCodes = Literal["long", "l", "|l", "=l", "<l", ">l"]
_IntCodes = _IntPCodes
_LongLongCodes = Literal["longlong", "q", "|q", "=q", "<q", ">q"]

_UByteCodes = Literal["ubyte", "B", "|B", "=B", "<B", ">B"]
_UShortCodes = Literal["ushort", "H", "|H", "=H", "<H", ">H"]
_UIntCCodes = Literal["uintc", "I", "|I", "=I", "<I", ">I"]
_UIntPCodes = Literal["uintp", "uint", "N", "|N", "=N", "<N", ">N"]
_ULongCodes = Literal["ulong", "L", "|L", "=L", "<L", ">L"]
_UIntCodes = _UIntPCodes
_ULongLongCodes = Literal["ulonglong", "Q", "|Q", "=Q", "<Q", ">Q"]

_HalfCodes = Literal["half", "e", "|e", "=e", "<e", ">e"]
_SingleCodes = Literal["single", "f", "|f", "=f", "<f", ">f"]
_DoubleCodes = Literal["double", "float", "d", "|d", "=d", "<d", ">d"]
_LongDoubleCodes = Literal["longdouble", "g", "|g", "=g", "<g", ">g"]

_CSingleCodes = Literal["csingle", "F", "|F", "=F", "<F", ">F"]
_CDoubleCodes = Literal["cdouble", "complex", "D", "|D", "=D", "<D", ">D"]
_CLongDoubleCodes = Literal["clongdouble", "G", "|G", "=G", "<G", ">G"]

_StrCodes = Literal["str", "str_", "unicode", "U", "|U", "=U", "<U", ">U"]
_BytesCodes = Literal["bytes", "bytes_", "S", "|S", "=S", "<S", ">S"]
_VoidCodes = Literal["void", "V", "|V", "=V", "<V", ">V"]
_ObjectCodes = Literal["object", "object_", "O", "|O", "=O", "<O", ">O"]

_DT64Codes = Literal[
    "datetime64", "|datetime64", "=datetime64",
    "<datetime64", ">datetime64",
    "datetime64[Y]", "|datetime64[Y]", "=datetime64[Y]",
    "<datetime64[Y]", ">datetime64[Y]",
    "datetime64[M]", "|datetime64[M]", "=datetime64[M]",
    "<datetime64[M]", ">datetime64[M]",
    "datetime64[W]", "|datetime64[W]", "=datetime64[W]",
    "<datetime64[W]", ">datetime64[W]",
    "datetime64[D]", "|datetime64[D]", "=datetime64[D]",
    "<datetime64[D]", ">datetime64[D]",
    "datetime64[h]", "|datetime64[h]", "=datetime64[h]",
    "<datetime64[h]", ">datetime64[h]",
    "datetime64[m]", "|datetime64[m]", "=datetime64[m]",
    "<datetime64[m]", ">datetime64[m]",
    "datetime64[s]", "|datetime64[s]", "=datetime64[s]",
    "<datetime64[s]", ">datetime64[s]",
    "datetime64[ms]", "|datetime64[ms]", "=datetime64[ms]",
    "<datetime64[ms]", ">datetime64[ms]",
    "datetime64[us]", "|datetime64[us]", "=datetime64[us]",
    "<datetime64[us]", ">datetime64[us]",
    "datetime64[ns]", "|datetime64[ns]", "=datetime64[ns]",
    "<datetime64[ns]", ">datetime64[ns]",
    "datetime64[ps]", "|datetime64[ps]", "=datetime64[ps]",
    "<datetime64[ps]", ">datetime64[ps]",
    "datetime64[fs]", "|datetime64[fs]", "=datetime64[fs]",
    "<datetime64[fs]", ">datetime64[fs]",
    "datetime64[as]", "|datetime64[as]", "=datetime64[as]",
    "<datetime64[as]", ">datetime64[as]",
    "M", "|M", "=M", "<M", ">M",
    "M8", "|M8", "=M8", "<M8", ">M8",
    "M8[Y]", "|M8[Y]", "=M8[Y]", "<M8[Y]", ">M8[Y]",
    "M8[M]", "|M8[M]", "=M8[M]", "<M8[M]", ">M8[M]",
    "M8[W]", "|M8[W]", "=M8[W]", "<M8[W]", ">M8[W]",
    "M8[D]", "|M8[D]", "=M8[D]", "<M8[D]", ">M8[D]",
    "M8[h]", "|M8[h]", "=M8[h]", "<M8[h]", ">M8[h]",
    "M8[m]", "|M8[m]", "=M8[m]", "<M8[m]", ">M8[m]",
    "M8[s]", "|M8[s]", "=M8[s]", "<M8[s]", ">M8[s]",
    "M8[ms]", "|M8[ms]", "=M8[ms]", "<M8[ms]", ">M8[ms]",
    "M8[us]", "|M8[us]", "=M8[us]", "<M8[us]", ">M8[us]",
    "M8[ns]", "|M8[ns]", "=M8[ns]", "<M8[ns]", ">M8[ns]",
    "M8[ps]", "|M8[ps]", "=M8[ps]", "<M8[ps]", ">M8[ps]",
    "M8[fs]", "|M8[fs]", "=M8[fs]", "<M8[fs]", ">M8[fs]",
    "M8[as]", "|M8[as]", "=M8[as]", "<M8[as]", ">M8[as]",
]
_TD64Codes = Literal[
    "timedelta64", "|timedelta64", "=timedelta64",
    "<timedelta64", ">timedelta64",
    "timedelta64[Y]", "|timedelta64[Y]", "=timedelta64[Y]",
    "<timedelta64[Y]", ">timedelta64[Y]",
    "timedelta64[M]", "|timedelta64[M]", "=timedelta64[M]",
    "<timedelta64[M]", ">timedelta64[M]",
    "timedelta64[W]", "|timedelta64[W]", "=timedelta64[W]",
    "<timedelta64[W]", ">timedelta64[W]",
    "timedelta64[D]", "|timedelta64[D]", "=timedelta64[D]",
    "<timedelta64[D]", ">timedelta64[D]",
    "timedelta64[h]", "|timedelta64[h]", "=timedelta64[h]",
    "<timedelta64[h]", ">timedelta64[h]",
    "timedelta64[m]", "|timedelta64[m]", "=timedelta64[m]",
    "<timedelta64[m]", ">timedelta64[m]",
    "timedelta64[s]", "|timedelta64[s]", "=timedelta64[s]",
    "<timedelta64[s]", ">timedelta64[s]",
    "timedelta64[ms]", "|timedelta64[ms]", "=timedelta64[ms]",
    "<timedelta64[ms]", ">timedelta64[ms]",
    "timedelta64[us]", "|timedelta64[us]", "=timedelta64[us]",
    "<timedelta64[us]", ">timedelta64[us]",
    "timedelta64[ns]", "|timedelta64[ns]", "=timedelta64[ns]",
    "<timedelta64[ns]", ">timedelta64[ns]",
    "timedelta64[ps]", "|timedelta64[ps]", "=timedelta64[ps]",
    "<timedelta64[ps]", ">timedelta64[ps]",
    "timedelta64[fs]", "|timedelta64[fs]", "=timedelta64[fs]",
    "<timedelta64[fs]", ">timedelta64[fs]",
    "timedelta64[as]", "|timedelta64[as]", "=timedelta64[as]",
    "<timedelta64[as]", ">timedelta64[as]",
    "m", "|m", "=m", "<m", ">m",
    "m8", "|m8", "=m8", "<m8", ">m8",
    "m8[Y]", "|m8[Y]", "=m8[Y]", "<m8[Y]", ">m8[Y]",
    "m8[M]", "|m8[M]", "=m8[M]", "<m8[M]", ">m8[M]",
    "m8[W]", "|m8[W]", "=m8[W]", "<m8[W]", ">m8[W]",
    "m8[D]", "|m8[D]", "=m8[D]", "<m8[D]", ">m8[D]",
    "m8[h]", "|m8[h]", "=m8[h]", "<m8[h]", ">m8[h]",
    "m8[m]", "|m8[m]", "=m8[m]", "<m8[m]", ">m8[m]",
    "m8[s]", "|m8[s]", "=m8[s]", "<m8[s]", ">m8[s]",
    "m8[ms]", "|m8[ms]", "=m8[ms]", "<m8[ms]", ">m8[ms]",
    "m8[us]", "|m8[us]", "=m8[us]", "<m8[us]", ">m8[us]",
    "m8[ns]", "|m8[ns]", "=m8[ns]", "<m8[ns]", ">m8[ns]",
    "m8[ps]", "|m8[ps]", "=m8[ps]", "<m8[ps]", ">m8[ps]",
    "m8[fs]", "|m8[fs]", "=m8[fs]", "<m8[fs]", ">m8[fs]",
    "m8[as]", "|m8[as]", "=m8[as]", "<m8[as]", ">m8[as]",
]

# NOTE: `StringDType' has no scalar type, and therefore has no name that can
# be passed to the `dtype` constructor
_StringCodes = Literal["T", "|T", "=T", "<T", ">T"]

# NOTE: Nested literals get flattened and de-duplicated at runtime, which isn't
# the case for a `Union` of `Literal`s.
# So even though they're equivalent when type-checking, they differ at runtime.
# Another advantage of nesting, is that they always have a "flat"
# `Literal.__args__`, which is a tuple of *literally* all its literal values.

_UnsignedIntegerCodes = Literal[
    _UInt8Codes,
    _UInt16Codes,
    _UInt32Codes,
    _UInt64Codes,
    _UIntCodes,
    _UByteCodes,
    _UShortCodes,
    _UIntCCodes,
    _ULongCodes,
    _ULongLongCodes,
]
_SignedIntegerCodes = Literal[
    _Int8Codes,
    _Int16Codes,
    _Int32Codes,
    _Int64Codes,
    _IntCodes,
    _ByteCodes,
    _ShortCodes,
    _IntCCodes,
    _LongCodes,
    _LongLongCodes,
]
_FloatingCodes = Literal[
    _Float16Codes,
    _Float32Codes,
    _Float64Codes,
    _HalfCodes,
    _SingleCodes,
    _DoubleCodes,
    _LongDoubleCodes
]
_ComplexFloatingCodes = Literal[
    _Complex64Codes,
    _Complex128Codes,
    _CSingleCodes,
    _CDoubleCodes,
    _CLongDoubleCodes,
]
_IntegerCodes = Literal[_UnsignedIntegerCodes, _SignedIntegerCodes]
_InexactCodes = Literal[_FloatingCodes, _ComplexFloatingCodes]
_NumberCodes = Literal[_IntegerCodes, _InexactCodes]

_CharacterCodes = Literal[_StrCodes, _BytesCodes]
_FlexibleCodes = Literal[_VoidCodes, _CharacterCodes]

_GenericCodes = Literal[
    _BoolCodes,
    _NumberCodes,
    _FlexibleCodes,
    _DT64Codes,
    _TD64Codes,
    _ObjectCodes,
    # TODO: add `_StringCodes` once it has a scalar type
    # _StringCodes,
]

# === NexusCore/openenv\Lib\site-packages\openai\types\responses\__init__.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from .tool import Tool as Tool
from .response import Response as Response
from .tool_param import ToolParam as ToolParam
from .computer_tool import ComputerTool as ComputerTool
from .function_tool import FunctionTool as FunctionTool
from .response_item import ResponseItem as ResponseItem
from .response_error import ResponseError as ResponseError
from .response_usage import ResponseUsage as ResponseUsage
from .parsed_response import (
    ParsedContent as ParsedContent,
    ParsedResponse as ParsedResponse,
    ParsedResponseOutputItem as ParsedResponseOutputItem,
    ParsedResponseOutputText as ParsedResponseOutputText,
    ParsedResponseOutputMessage as ParsedResponseOutputMessage,
    ParsedResponseFunctionToolCall as ParsedResponseFunctionToolCall,
)
from .response_prompt import ResponsePrompt as ResponsePrompt
from .response_status import ResponseStatus as ResponseStatus
from .web_search_tool import WebSearchTool as WebSearchTool
from .file_search_tool import FileSearchTool as FileSearchTool
from .tool_choice_types import ToolChoiceTypes as ToolChoiceTypes
from .easy_input_message import EasyInputMessage as EasyInputMessage
from .response_item_list import ResponseItemList as ResponseItemList
from .computer_tool_param import ComputerToolParam as ComputerToolParam
from .function_tool_param import FunctionToolParam as FunctionToolParam
from .response_includable import ResponseIncludable as ResponseIncludable
from .response_input_file import ResponseInputFile as ResponseInputFile
from .response_input_item import ResponseInputItem as ResponseInputItem
from .response_input_text import ResponseInputText as ResponseInputText
from .tool_choice_options import ToolChoiceOptions as ToolChoiceOptions
from .response_error_event import ResponseErrorEvent as ResponseErrorEvent
from .response_input_image import ResponseInputImage as ResponseInputImage
from .response_input_param import ResponseInputParam as ResponseInputParam
from .response_output_item import ResponseOutputItem as ResponseOutputItem
from .response_output_text import ResponseOutputText as ResponseOutputText
from .response_text_config import ResponseTextConfig as ResponseTextConfig
from .tool_choice_function import ToolChoiceFunction as ToolChoiceFunction
from .response_failed_event import ResponseFailedEvent as ResponseFailedEvent
from .response_prompt_param import ResponsePromptParam as ResponsePromptParam
from .response_queued_event import ResponseQueuedEvent as ResponseQueuedEvent
from .response_stream_event import ResponseStreamEvent as ResponseStreamEvent
from .web_search_tool_param import WebSearchToolParam as WebSearchToolParam
from .file_search_tool_param import FileSearchToolParam as FileSearchToolParam
from .input_item_list_params import InputItemListParams as InputItemListParams
from .response_create_params import ResponseCreateParams as ResponseCreateParams
from .response_created_event import ResponseCreatedEvent as ResponseCreatedEvent
from .response_input_content import ResponseInputContent as ResponseInputContent
from .response_output_message import ResponseOutputMessage as ResponseOutputMessage
from .response_output_refusal import ResponseOutputRefusal as ResponseOutputRefusal
from .response_reasoning_item import ResponseReasoningItem as ResponseReasoningItem
from .tool_choice_types_param import ToolChoiceTypesParam as ToolChoiceTypesParam
from .easy_input_message_param import EasyInputMessageParam as EasyInputMessageParam
from .response_completed_event import ResponseCompletedEvent as ResponseCompletedEvent
from .response_retrieve_params import ResponseRetrieveParams as ResponseRetrieveParams
from .response_text_done_event import ResponseTextDoneEvent as ResponseTextDoneEvent
from .response_audio_done_event import ResponseAudioDoneEvent as ResponseAudioDoneEvent
from .response_incomplete_event import ResponseIncompleteEvent as ResponseIncompleteEvent
from .response_input_file_param import ResponseInputFileParam as ResponseInputFileParam
from .response_input_item_param import ResponseInputItemParam as ResponseInputItemParam
from .response_input_text_param import ResponseInputTextParam as ResponseInputTextParam
from .response_text_delta_event import ResponseTextDeltaEvent as ResponseTextDeltaEvent
from .response_audio_delta_event import ResponseAudioDeltaEvent as ResponseAudioDeltaEvent
from .response_in_progress_event import ResponseInProgressEvent as ResponseInProgressEvent
from .response_input_image_param import ResponseInputImageParam as ResponseInputImageParam
from .response_output_text_param import ResponseOutputTextParam as ResponseOutputTextParam
from .response_text_config_param import ResponseTextConfigParam as ResponseTextConfigParam
from .tool_choice_function_param import ToolChoiceFunctionParam as ToolChoiceFunctionParam
from .response_computer_tool_call import ResponseComputerToolCall as ResponseComputerToolCall
from .response_format_text_config import ResponseFormatTextConfig as ResponseFormatTextConfig
from .response_function_tool_call import ResponseFunctionToolCall as ResponseFunctionToolCall
from .response_input_message_item import ResponseInputMessageItem as ResponseInputMessageItem
from .response_refusal_done_event import ResponseRefusalDoneEvent as ResponseRefusalDoneEvent
from .response_function_web_search import ResponseFunctionWebSearch as ResponseFunctionWebSearch
from .response_input_content_param import ResponseInputContentParam as ResponseInputContentParam
from .response_refusal_delta_event import ResponseRefusalDeltaEvent as ResponseRefusalDeltaEvent
from .response_output_message_param import ResponseOutputMessageParam as ResponseOutputMessageParam
from .response_output_refusal_param import ResponseOutputRefusalParam as ResponseOutputRefusalParam
from .response_reasoning_done_event import ResponseReasoningDoneEvent as ResponseReasoningDoneEvent
from .response_reasoning_item_param import ResponseReasoningItemParam as ResponseReasoningItemParam
from .response_file_search_tool_call import ResponseFileSearchToolCall as ResponseFileSearchToolCall
from .response_mcp_call_failed_event import ResponseMcpCallFailedEvent as ResponseMcpCallFailedEvent
from .response_reasoning_delta_event import ResponseReasoningDeltaEvent as ResponseReasoningDeltaEvent
from .response_output_item_done_event import ResponseOutputItemDoneEvent as ResponseOutputItemDoneEvent
from .response_content_part_done_event import ResponseContentPartDoneEvent as ResponseContentPartDoneEvent
from .response_function_tool_call_item import ResponseFunctionToolCallItem as ResponseFunctionToolCallItem
from .response_output_item_added_event import ResponseOutputItemAddedEvent as ResponseOutputItemAddedEvent
from .response_computer_tool_call_param import ResponseComputerToolCallParam as ResponseComputerToolCallParam
from .response_content_part_added_event import ResponseContentPartAddedEvent as ResponseContentPartAddedEvent
from .response_format_text_config_param import ResponseFormatTextConfigParam as ResponseFormatTextConfigParam
from .response_function_tool_call_param import ResponseFunctionToolCallParam as ResponseFunctionToolCallParam
from .response_mcp_call_completed_event import ResponseMcpCallCompletedEvent as ResponseMcpCallCompletedEvent
from .response_function_web_search_param import ResponseFunctionWebSearchParam as ResponseFunctionWebSearchParam
from .response_code_interpreter_tool_call import ResponseCodeInterpreterToolCall as ResponseCodeInterpreterToolCall
from .response_input_message_content_list import ResponseInputMessageContentList as ResponseInputMessageContentList
from .response_mcp_call_in_progress_event import ResponseMcpCallInProgressEvent as ResponseMcpCallInProgressEvent
from .response_audio_transcript_done_event import ResponseAudioTranscriptDoneEvent as ResponseAudioTranscriptDoneEvent
from .response_file_search_tool_call_param import ResponseFileSearchToolCallParam as ResponseFileSearchToolCallParam
from .response_mcp_list_tools_failed_event import ResponseMcpListToolsFailedEvent as ResponseMcpListToolsFailedEvent
from .response_audio_transcript_delta_event import (
    ResponseAudioTranscriptDeltaEvent as ResponseAudioTranscriptDeltaEvent,
)
from .response_reasoning_summary_done_event import (
    ResponseReasoningSummaryDoneEvent as ResponseReasoningSummaryDoneEvent,
)
from .response_mcp_call_arguments_done_event import (
    ResponseMcpCallArgumentsDoneEvent as ResponseMcpCallArgumentsDoneEvent,
)
from .response_reasoning_summary_delta_event import (
    ResponseReasoningSummaryDeltaEvent as ResponseReasoningSummaryDeltaEvent,
)
from .response_computer_tool_call_output_item import (
    ResponseComputerToolCallOutputItem as ResponseComputerToolCallOutputItem,
)
from .response_format_text_json_schema_config import (
    ResponseFormatTextJSONSchemaConfig as ResponseFormatTextJSONSchemaConfig,
)
from .response_function_tool_call_output_item import (
    ResponseFunctionToolCallOutputItem as ResponseFunctionToolCallOutputItem,
)
from .response_image_gen_call_completed_event import (
    ResponseImageGenCallCompletedEvent as ResponseImageGenCallCompletedEvent,
)
from .response_mcp_call_arguments_delta_event import (
    ResponseMcpCallArgumentsDeltaEvent as ResponseMcpCallArgumentsDeltaEvent,
)
from .response_mcp_list_tools_completed_event import (
    ResponseMcpListToolsCompletedEvent as ResponseMcpListToolsCompletedEvent,
)
from .response_image_gen_call_generating_event import (
    ResponseImageGenCallGeneratingEvent as ResponseImageGenCallGeneratingEvent,
)
from .response_web_search_call_completed_event import (
    ResponseWebSearchCallCompletedEvent as ResponseWebSearchCallCompletedEvent,
)
from .response_web_search_call_searching_event import (
    ResponseWebSearchCallSearchingEvent as ResponseWebSearchCallSearchingEvent,
)
from .response_code_interpreter_tool_call_param import (
    ResponseCodeInterpreterToolCallParam as ResponseCodeInterpreterToolCallParam,
)
from .response_file_search_call_completed_event import (
    ResponseFileSearchCallCompletedEvent as ResponseFileSearchCallCompletedEvent,
)
from .response_file_search_call_searching_event import (
    ResponseFileSearchCallSearchingEvent as ResponseFileSearchCallSearchingEvent,
)
from .response_image_gen_call_in_progress_event import (
    ResponseImageGenCallInProgressEvent as ResponseImageGenCallInProgressEvent,
)
from .response_input_message_content_list_param import (
    ResponseInputMessageContentListParam as ResponseInputMessageContentListParam,
)
from .response_mcp_list_tools_in_progress_event import (
    ResponseMcpListToolsInProgressEvent as ResponseMcpListToolsInProgressEvent,
)
from .response_reasoning_summary_part_done_event import (
    ResponseReasoningSummaryPartDoneEvent as ResponseReasoningSummaryPartDoneEvent,
)
from .response_reasoning_summary_text_done_event import (
    ResponseReasoningSummaryTextDoneEvent as ResponseReasoningSummaryTextDoneEvent,
)
from .response_web_search_call_in_progress_event import (
    ResponseWebSearchCallInProgressEvent as ResponseWebSearchCallInProgressEvent,
)
from .response_file_search_call_in_progress_event import (
    ResponseFileSearchCallInProgressEvent as ResponseFileSearchCallInProgressEvent,
)
from .response_function_call_arguments_done_event import (
    ResponseFunctionCallArgumentsDoneEvent as ResponseFunctionCallArgumentsDoneEvent,
)
from .response_image_gen_call_partial_image_event import (
    ResponseImageGenCallPartialImageEvent as ResponseImageGenCallPartialImageEvent,
)
from .response_output_text_annotation_added_event import (
    ResponseOutputTextAnnotationAddedEvent as ResponseOutputTextAnnotationAddedEvent,
)
from .response_reasoning_summary_part_added_event import (
    ResponseReasoningSummaryPartAddedEvent as ResponseReasoningSummaryPartAddedEvent,
)
from .response_reasoning_summary_text_delta_event import (
    ResponseReasoningSummaryTextDeltaEvent as ResponseReasoningSummaryTextDeltaEvent,
)
from .response_function_call_arguments_delta_event import (
    ResponseFunctionCallArgumentsDeltaEvent as ResponseFunctionCallArgumentsDeltaEvent,
)
from .response_computer_tool_call_output_screenshot import (
    ResponseComputerToolCallOutputScreenshot as ResponseComputerToolCallOutputScreenshot,
)
from .response_format_text_json_schema_config_param import (
    ResponseFormatTextJSONSchemaConfigParam as ResponseFormatTextJSONSchemaConfigParam,
)
from .response_code_interpreter_call_code_done_event import (
    ResponseCodeInterpreterCallCodeDoneEvent as ResponseCodeInterpreterCallCodeDoneEvent,
)
from .response_code_interpreter_call_completed_event import (
    ResponseCodeInterpreterCallCompletedEvent as ResponseCodeInterpreterCallCompletedEvent,
)
from .response_code_interpreter_call_code_delta_event import (
    ResponseCodeInterpreterCallCodeDeltaEvent as ResponseCodeInterpreterCallCodeDeltaEvent,
)
from .response_code_interpreter_call_in_progress_event import (
    ResponseCodeInterpreterCallInProgressEvent as ResponseCodeInterpreterCallInProgressEvent,
)
from .response_code_interpreter_call_interpreting_event import (
    ResponseCodeInterpreterCallInterpretingEvent as ResponseCodeInterpreterCallInterpretingEvent,
)
from .response_computer_tool_call_output_screenshot_param import (
    ResponseComputerToolCallOutputScreenshotParam as ResponseComputerToolCallOutputScreenshotParam,
)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\completion\fuzzy_completer.py ===
from __future__ import annotations

import re
from typing import Callable, Iterable, NamedTuple, Sequence

from prompt_toolkit.document import Document
from prompt_toolkit.filters import FilterOrBool, to_filter
from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples

from .base import CompleteEvent, Completer, Completion
from .word_completer import WordCompleter

__all__ = [
    "FuzzyCompleter",
    "FuzzyWordCompleter",
]


class FuzzyCompleter(Completer):
    """
    Fuzzy completion.
    This wraps any other completer and turns it into a fuzzy completer.

    If the list of words is: ["leopard" , "gorilla", "dinosaur", "cat", "bee"]
    Then trying to complete "oar" would yield "leopard" and "dinosaur", but not
    the others, because they match the regular expression 'o.*a.*r'.
    Similar, in another application "djm" could expand to "django_migrations".

    The results are sorted by relevance, which is defined as the start position
    and the length of the match.

    Notice that this is not really a tool to work around spelling mistakes,
    like what would be possible with difflib. The purpose is rather to have a
    quicker or more intuitive way to filter the given completions, especially
    when many completions have a common prefix.

    Fuzzy algorithm is based on this post:
    https://blog.amjith.com/fuzzyfinder-in-10-lines-of-python

    :param completer: A :class:`~.Completer` instance.
    :param WORD: When True, use WORD characters.
    :param pattern: Regex pattern which selects the characters before the
        cursor that are considered for the fuzzy matching.
    :param enable_fuzzy: (bool or `Filter`) Enabled the fuzzy behavior. For
        easily turning fuzzyness on or off according to a certain condition.
    """

    def __init__(
        self,
        completer: Completer,
        WORD: bool = False,
        pattern: str | None = None,
        enable_fuzzy: FilterOrBool = True,
    ) -> None:
        assert pattern is None or pattern.startswith("^")

        self.completer = completer
        self.pattern = pattern
        self.WORD = WORD
        self.pattern = pattern
        self.enable_fuzzy = to_filter(enable_fuzzy)

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        if self.enable_fuzzy():
            return self._get_fuzzy_completions(document, complete_event)
        else:
            return self.completer.get_completions(document, complete_event)

    def _get_pattern(self) -> str:
        if self.pattern:
            return self.pattern
        if self.WORD:
            return r"[^\s]+"
        return "^[a-zA-Z0-9_]*"

    def _get_fuzzy_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        word_before_cursor = document.get_word_before_cursor(
            pattern=re.compile(self._get_pattern())
        )

        # Get completions
        document2 = Document(
            text=document.text[: document.cursor_position - len(word_before_cursor)],
            cursor_position=document.cursor_position - len(word_before_cursor),
        )

        inner_completions = list(
            self.completer.get_completions(document2, complete_event)
        )

        fuzzy_matches: list[_FuzzyMatch] = []

        if word_before_cursor == "":
            # If word before the cursor is an empty string, consider all
            # completions, without filtering everything with an empty regex
            # pattern.
            fuzzy_matches = [_FuzzyMatch(0, 0, compl) for compl in inner_completions]
        else:
            pat = ".*?".join(map(re.escape, word_before_cursor))
            pat = f"(?=({pat}))"  # lookahead regex to manage overlapping matches
            regex = re.compile(pat, re.IGNORECASE)
            for compl in inner_completions:
                matches = list(regex.finditer(compl.text))
                if matches:
                    # Prefer the match, closest to the left, then shortest.
                    best = min(matches, key=lambda m: (m.start(), len(m.group(1))))
                    fuzzy_matches.append(
                        _FuzzyMatch(len(best.group(1)), best.start(), compl)
                    )

            def sort_key(fuzzy_match: _FuzzyMatch) -> tuple[int, int]:
                "Sort by start position, then by the length of the match."
                return fuzzy_match.start_pos, fuzzy_match.match_length

            fuzzy_matches = sorted(fuzzy_matches, key=sort_key)

        for match in fuzzy_matches:
            # Include these completions, but set the correct `display`
            # attribute and `start_position`.
            yield Completion(
                text=match.completion.text,
                start_position=match.completion.start_position
                - len(word_before_cursor),
                # We access to private `_display_meta` attribute, because that one is lazy.
                display_meta=match.completion._display_meta,
                display=self._get_display(match, word_before_cursor),
                style=match.completion.style,
            )

    def _get_display(
        self, fuzzy_match: _FuzzyMatch, word_before_cursor: str
    ) -> AnyFormattedText:
        """
        Generate formatted text for the display label.
        """

        def get_display() -> AnyFormattedText:
            m = fuzzy_match
            word = m.completion.text

            if m.match_length == 0:
                # No highlighting when we have zero length matches (no input text).
                # In this case, use the original display text (which can include
                # additional styling or characters).
                return m.completion.display

            result: StyleAndTextTuples = []

            # Text before match.
            result.append(("class:fuzzymatch.outside", word[: m.start_pos]))

            # The match itself.
            characters = list(word_before_cursor)

            for c in word[m.start_pos : m.start_pos + m.match_length]:
                classname = "class:fuzzymatch.inside"
                if characters and c.lower() == characters[0].lower():
                    classname += ".character"
                    del characters[0]

                result.append((classname, c))

            # Text after match.
            result.append(
                ("class:fuzzymatch.outside", word[m.start_pos + m.match_length :])
            )

            return result

        return get_display()


class FuzzyWordCompleter(Completer):
    """
    Fuzzy completion on a list of words.

    (This is basically a `WordCompleter` wrapped in a `FuzzyCompleter`.)

    :param words: List of words or callable that returns a list of words.
    :param meta_dict: Optional dict mapping words to their meta-information.
    :param WORD: When True, use WORD characters.
    """

    def __init__(
        self,
        words: Sequence[str] | Callable[[], Sequence[str]],
        meta_dict: dict[str, str] | None = None,
        WORD: bool = False,
    ) -> None:
        self.words = words
        self.meta_dict = meta_dict or {}
        self.WORD = WORD

        self.word_completer = WordCompleter(
            words=self.words, WORD=self.WORD, meta_dict=self.meta_dict
        )

        self.fuzzy_completer = FuzzyCompleter(self.word_completer, WORD=self.WORD)

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        return self.fuzzy_completer.get_completions(document, complete_event)


class _FuzzyMatch(NamedTuple):
    match_length: int
    start_pos: int
    completion: Completion

# === NexusCore/openenv\Lib\site-packages\pyreadline3\keysyms\ironpython_keysyms.py ===
# -*- coding: utf-8 -*-
# *****************************************************************************
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006-2020 Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#       Copyright (C) 2020 Bassem Girgis. <brgirgis@gmail.com>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# *****************************************************************************


import System

from .common import KeyPress, make_KeyPress_from_keydescr, validkey

c32 = System.ConsoleKey
Shift = System.ConsoleModifiers.Shift
Control = System.ConsoleModifiers.Control
Alt = System.ConsoleModifiers.Alt
# table for translating virtual keys to X windows key symbols
code2sym_map = {
    # c32.CANCEL:    'Cancel',
    c32.Backspace: "BackSpace",
    c32.Tab: "Tab",
    c32.Clear: "Clear",
    c32.Enter: "Return",
    # c32.Shift:     'Shift_L',
    # c32.Control:   'Control_L',
    # c32.Menu:      'Alt_L',
    c32.Pause: "Pause",
    # c32.Capital:   'Caps_Lock',
    c32.Escape: "Escape",
    # c32.Space:     'space',
    c32.PageUp: "Prior",
    c32.PageDown: "Next",
    c32.End: "End",
    c32.Home: "Home",
    c32.LeftArrow: "Left",
    c32.UpArrow: "Up",
    c32.RightArrow: "Right",
    c32.DownArrow: "Down",
    c32.Select: "Select",
    c32.Print: "Print",
    c32.Execute: "Execute",
    # c32.Snapshot:  'Snapshot',
    c32.Insert: "Insert",
    c32.Delete: "Delete",
    c32.Help: "Help",
    c32.F1: "F1",
    c32.F2: "F2",
    c32.F3: "F3",
    c32.F4: "F4",
    c32.F5: "F5",
    c32.F6: "F6",
    c32.F7: "F7",
    c32.F8: "F8",
    c32.F9: "F9",
    c32.F10: "F10",
    c32.F11: "F11",
    c32.F12: "F12",
    c32.F13: "F13",
    c32.F14: "F14",
    c32.F15: "F15",
    c32.F16: "F16",
    c32.F17: "F17",
    c32.F18: "F18",
    c32.F19: "F19",
    c32.F20: "F20",
    c32.F21: "F21",
    c32.F22: "F22",
    c32.F23: "F23",
    c32.F24: "F24",
    # c32.Numlock:    'Num_Lock,',
    # c32.Scroll:     'Scroll_Lock',
    # c32.Apps:       'VK_APPS',
    # c32.ProcesskeY: 'VK_PROCESSKEY',
    # c32.Attn:       'VK_ATTN',
    # c32.Crsel:      'VK_CRSEL',
    # c32.Exsel:      'VK_EXSEL',
    # c32.Ereof:      'VK_EREOF',
    # c32.Play:       'VK_PLAY',
    # c32.Zoom:       'VK_ZOOM',
    # c32.Noname:     'VK_NONAME',
    # c32.Pa1:        'VK_PA1',
    c32.OemClear: "VK_OEM_CLEAR",
    c32.NumPad0: "NUMPAD0",
    c32.NumPad1: "NUMPAD1",
    c32.NumPad2: "NUMPAD2",
    c32.NumPad3: "NUMPAD3",
    c32.NumPad4: "NUMPAD4",
    c32.NumPad5: "NUMPAD5",
    c32.NumPad6: "NUMPAD6",
    c32.NumPad7: "NUMPAD7",
    c32.NumPad8: "NUMPAD8",
    c32.NumPad9: "NUMPAD9",
    c32.Divide: "Divide",
    c32.Multiply: "Multiply",
    c32.Add: "Add",
    c32.Subtract: "Subtract",
    c32.Decimal: "VK_DECIMAL",
}

# function to handle the mapping


def make_keysym(keycode):
    try:
        sym = code2sym_map[keycode]
    except KeyError:
        sym = ""
    return sym


sym2code_map = {}
for code, sym in code2sym_map.items():
    sym2code_map[sym.lower()] = code


def key_text_to_keyinfo(keytext):
    """Convert a GNU readline style textual description of a key to keycode with modifiers"""
    if keytext.startswith('"'):  # "
        return keyseq_to_keyinfo(keytext[1:-1])
    else:
        return keyname_to_keyinfo(keytext)


def char_to_keyinfo(char, control=False, meta=False, shift=False):
    vk = ord(char)
    if vk & 0xFFFF == 0xFFFF:
        print('VkKeyScan("%s") = %x' % (char, vk))
        raise ValueError("bad key")
    if vk & 0x100:
        shift = True
    if vk & 0x200:
        control = True
    if vk & 0x400:
        meta = True
    return (control, meta, shift, vk & 0xFF)


def keyname_to_keyinfo(keyname):
    control = False
    meta = False
    shift = False

    while True:
        lkeyname = keyname.lower()
        if lkeyname.startswith("control-"):
            control = True
            keyname = keyname[8:]
        elif lkeyname.startswith("ctrl-"):
            control = True
            keyname = keyname[5:]
        elif lkeyname.startswith("meta-"):
            meta = True
            keyname = keyname[5:]
        elif lkeyname.startswith("alt-"):
            meta = True
            keyname = keyname[4:]
        elif lkeyname.startswith("shift-"):
            shift = True
            keyname = keyname[6:]
        else:
            if len(keyname) > 1:
                return (control, meta, shift, sym2code_map.get(keyname.lower(), " "))
            else:
                return char_to_keyinfo(keyname, control, meta, shift)


def keyseq_to_keyinfo(keyseq):
    res = []
    control = False
    meta = False
    shift = False

    while True:
        if keyseq.startswith("\\C-"):
            control = True
            keyseq = keyseq[3:]
        elif keyseq.startswith("\\M-"):
            meta = True
            keyseq = keyseq[3:]
        elif keyseq.startswith("\\e"):
            res.append(char_to_keyinfo("\033", control, meta, shift))
            control = meta = shift = False
            keyseq = keyseq[2:]
        elif len(keyseq) >= 1:
            res.append(char_to_keyinfo(keyseq[0], control, meta, shift))
            control = meta = shift = False
            keyseq = keyseq[1:]
        else:
            return res[0]


def make_keyinfo(keycode, state):
    control = False
    meta = False
    shift = False
    return (control, meta, shift, keycode)


def make_KeyPress(char, state, keycode):

    shift = bool(int(state) & int(Shift))
    control = bool(int(state) & int(Control))
    meta = bool(int(state) & int(Alt))
    keyname = code2sym_map.get(keycode, "").lower()
    if control and meta:  # equivalent to altgr so clear flags
        control = False
        meta = False
    elif control:
        char = str(keycode)
    return KeyPress(char, shift, control, meta, keyname)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\background_service.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: BackgroundService (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import network
from . import service_worker


class ServiceName(enum.Enum):
    '''
    The Background Service that will be associated with the commands/events.
    Every Background Service operates independently, but they share the same
    API.
    '''
    BACKGROUND_FETCH = "backgroundFetch"
    BACKGROUND_SYNC = "backgroundSync"
    PUSH_MESSAGING = "pushMessaging"
    NOTIFICATIONS = "notifications"
    PAYMENT_HANDLER = "paymentHandler"
    PERIODIC_BACKGROUND_SYNC = "periodicBackgroundSync"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class EventMetadata:
    '''
    A key-value pair for additional event information to pass along.
    '''
    key: str

    value: str

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            value=str(json['value']),
        )


@dataclass
class BackgroundServiceEvent:
    #: Timestamp of the event (in seconds).
    timestamp: network.TimeSinceEpoch

    #: The origin this event belongs to.
    origin: str

    #: The Service Worker ID that initiated the event.
    service_worker_registration_id: service_worker.RegistrationID

    #: The Background Service this event belongs to.
    service: ServiceName

    #: A description of the event.
    event_name: str

    #: An identifier that groups related events together.
    instance_id: str

    #: A list of event-specific information.
    event_metadata: typing.List[EventMetadata]

    #: Storage key this event belongs to.
    storage_key: str

    def to_json(self):
        json = dict()
        json['timestamp'] = self.timestamp.to_json()
        json['origin'] = self.origin
        json['serviceWorkerRegistrationId'] = self.service_worker_registration_id.to_json()
        json['service'] = self.service.to_json()
        json['eventName'] = self.event_name
        json['instanceId'] = self.instance_id
        json['eventMetadata'] = [i.to_json() for i in self.event_metadata]
        json['storageKey'] = self.storage_key
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            timestamp=network.TimeSinceEpoch.from_json(json['timestamp']),
            origin=str(json['origin']),
            service_worker_registration_id=service_worker.RegistrationID.from_json(json['serviceWorkerRegistrationId']),
            service=ServiceName.from_json(json['service']),
            event_name=str(json['eventName']),
            instance_id=str(json['instanceId']),
            event_metadata=[EventMetadata.from_json(i) for i in json['eventMetadata']],
            storage_key=str(json['storageKey']),
        )


def start_observing(
        service: ServiceName
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables event updates for the service.

    :param service:
    '''
    params: T_JSON_DICT = dict()
    params['service'] = service.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BackgroundService.startObserving',
        'params': params,
    }
    json = yield cmd_dict


def stop_observing(
        service: ServiceName
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables event updates for the service.

    :param service:
    '''
    params: T_JSON_DICT = dict()
    params['service'] = service.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BackgroundService.stopObserving',
        'params': params,
    }
    json = yield cmd_dict


def set_recording(
        should_record: bool,
        service: ServiceName
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set the recording state for the service.

    :param should_record:
    :param service:
    '''
    params: T_JSON_DICT = dict()
    params['shouldRecord'] = should_record
    params['service'] = service.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BackgroundService.setRecording',
        'params': params,
    }
    json = yield cmd_dict


def clear_events(
        service: ServiceName
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears all stored data for the service.

    :param service:
    '''
    params: T_JSON_DICT = dict()
    params['service'] = service.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BackgroundService.clearEvents',
        'params': params,
    }
    json = yield cmd_dict


@event_class('BackgroundService.recordingStateChanged')
@dataclass
class RecordingStateChanged:
    '''
    Called when the recording state for the service has been updated.
    '''
    is_recording: bool
    service: ServiceName

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RecordingStateChanged:
        return cls(
            is_recording=bool(json['isRecording']),
            service=ServiceName.from_json(json['service'])
        )


@event_class('BackgroundService.backgroundServiceEventReceived')
@dataclass
class BackgroundServiceEventReceived:
    '''
    Called with all existing backgroundServiceEvents when enabled, and all new
    events afterwards if enabled and recording.
    '''
    background_service_event: BackgroundServiceEvent

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BackgroundServiceEventReceived:
        return cls(
            background_service_event=BackgroundServiceEvent.from_json(json['backgroundServiceEvent'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\background_service.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: BackgroundService (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import network
from . import service_worker


class ServiceName(enum.Enum):
    '''
    The Background Service that will be associated with the commands/events.
    Every Background Service operates independently, but they share the same
    API.
    '''
    BACKGROUND_FETCH = "backgroundFetch"
    BACKGROUND_SYNC = "backgroundSync"
    PUSH_MESSAGING = "pushMessaging"
    NOTIFICATIONS = "notifications"
    PAYMENT_HANDLER = "paymentHandler"
    PERIODIC_BACKGROUND_SYNC = "periodicBackgroundSync"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class EventMetadata:
    '''
    A key-value pair for additional event information to pass along.
    '''
    key: str

    value: str

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            value=str(json['value']),
        )


@dataclass
class BackgroundServiceEvent:
    #: Timestamp of the event (in seconds).
    timestamp: network.TimeSinceEpoch

    #: The origin this event belongs to.
    origin: str

    #: The Service Worker ID that initiated the event.
    service_worker_registration_id: service_worker.RegistrationID

    #: The Background Service this event belongs to.
    service: ServiceName

    #: A description of the event.
    event_name: str

    #: An identifier that groups related events together.
    instance_id: str

    #: A list of event-specific information.
    event_metadata: typing.List[EventMetadata]

    #: Storage key this event belongs to.
    storage_key: str

    def to_json(self):
        json = dict()
        json['timestamp'] = self.timestamp.to_json()
        json['origin'] = self.origin
        json['serviceWorkerRegistrationId'] = self.service_worker_registration_id.to_json()
        json['service'] = self.service.to_json()
        json['eventName'] = self.event_name
        json['instanceId'] = self.instance_id
        json['eventMetadata'] = [i.to_json() for i in self.event_metadata]
        json['storageKey'] = self.storage_key
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            timestamp=network.TimeSinceEpoch.from_json(json['timestamp']),
            origin=str(json['origin']),
            service_worker_registration_id=service_worker.RegistrationID.from_json(json['serviceWorkerRegistrationId']),
            service=ServiceName.from_json(json['service']),
            event_name=str(json['eventName']),
            instance_id=str(json['instanceId']),
            event_metadata=[EventMetadata.from_json(i) for i in json['eventMetadata']],
            storage_key=str(json['storageKey']),
        )


def start_observing(
        service: ServiceName
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables event updates for the service.

    :param service:
    '''
    params: T_JSON_DICT = dict()
    params['service'] = service.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BackgroundService.startObserving',
        'params': params,
    }
    json = yield cmd_dict


def stop_observing(
        service: ServiceName
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables event updates for the service.

    :param service:
    '''
    params: T_JSON_DICT = dict()
    params['service'] = service.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BackgroundService.stopObserving',
        'params': params,
    }
    json = yield cmd_dict


def set_recording(
        should_record: bool,
        service: ServiceName
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set the recording state for the service.

    :param should_record:
    :param service:
    '''
    params: T_JSON_DICT = dict()
    params['shouldRecord'] = should_record
    params['service'] = service.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BackgroundService.setRecording',
        'params': params,
    }
    json = yield cmd_dict


def clear_events(
        service: ServiceName
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears all stored data for the service.

    :param service:
    '''
    params: T_JSON_DICT = dict()
    params['service'] = service.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BackgroundService.clearEvents',
        'params': params,
    }
    json = yield cmd_dict


@event_class('BackgroundService.recordingStateChanged')
@dataclass
class RecordingStateChanged:
    '''
    Called when the recording state for the service has been updated.
    '''
    is_recording: bool
    service: ServiceName

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RecordingStateChanged:
        return cls(
            is_recording=bool(json['isRecording']),
            service=ServiceName.from_json(json['service'])
        )


@event_class('BackgroundService.backgroundServiceEventReceived')
@dataclass
class BackgroundServiceEventReceived:
    '''
    Called with all existing backgroundServiceEvents when enabled, and all new
    events afterwards if enabled and recording.
    '''
    background_service_event: BackgroundServiceEvent

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BackgroundServiceEventReceived:
        return cls(
            background_service_event=BackgroundServiceEvent.from_json(json['backgroundServiceEvent'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\background_service.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: BackgroundService (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import network
from . import service_worker


class ServiceName(enum.Enum):
    '''
    The Background Service that will be associated with the commands/events.
    Every Background Service operates independently, but they share the same
    API.
    '''
    BACKGROUND_FETCH = "backgroundFetch"
    BACKGROUND_SYNC = "backgroundSync"
    PUSH_MESSAGING = "pushMessaging"
    NOTIFICATIONS = "notifications"
    PAYMENT_HANDLER = "paymentHandler"
    PERIODIC_BACKGROUND_SYNC = "periodicBackgroundSync"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class EventMetadata:
    '''
    A key-value pair for additional event information to pass along.
    '''
    key: str

    value: str

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            value=str(json['value']),
        )


@dataclass
class BackgroundServiceEvent:
    #: Timestamp of the event (in seconds).
    timestamp: network.TimeSinceEpoch

    #: The origin this event belongs to.
    origin: str

    #: The Service Worker ID that initiated the event.
    service_worker_registration_id: service_worker.RegistrationID

    #: The Background Service this event belongs to.
    service: ServiceName

    #: A description of the event.
    event_name: str

    #: An identifier that groups related events together.
    instance_id: str

    #: A list of event-specific information.
    event_metadata: typing.List[EventMetadata]

    #: Storage key this event belongs to.
    storage_key: str

    def to_json(self):
        json = dict()
        json['timestamp'] = self.timestamp.to_json()
        json['origin'] = self.origin
        json['serviceWorkerRegistrationId'] = self.service_worker_registration_id.to_json()
        json['service'] = self.service.to_json()
        json['eventName'] = self.event_name
        json['instanceId'] = self.instance_id
        json['eventMetadata'] = [i.to_json() for i in self.event_metadata]
        json['storageKey'] = self.storage_key
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            timestamp=network.TimeSinceEpoch.from_json(json['timestamp']),
            origin=str(json['origin']),
            service_worker_registration_id=service_worker.RegistrationID.from_json(json['serviceWorkerRegistrationId']),
            service=ServiceName.from_json(json['service']),
            event_name=str(json['eventName']),
            instance_id=str(json['instanceId']),
            event_metadata=[EventMetadata.from_json(i) for i in json['eventMetadata']],
            storage_key=str(json['storageKey']),
        )


def start_observing(
        service: ServiceName
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables event updates for the service.

    :param service:
    '''
    params: T_JSON_DICT = dict()
    params['service'] = service.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BackgroundService.startObserving',
        'params': params,
    }
    json = yield cmd_dict


def stop_observing(
        service: ServiceName
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables event updates for the service.

    :param service:
    '''
    params: T_JSON_DICT = dict()
    params['service'] = service.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BackgroundService.stopObserving',
        'params': params,
    }
    json = yield cmd_dict


def set_recording(
        should_record: bool,
        service: ServiceName
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set the recording state for the service.

    :param should_record:
    :param service:
    '''
    params: T_JSON_DICT = dict()
    params['shouldRecord'] = should_record
    params['service'] = service.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BackgroundService.setRecording',
        'params': params,
    }
    json = yield cmd_dict


def clear_events(
        service: ServiceName
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears all stored data for the service.

    :param service:
    '''
    params: T_JSON_DICT = dict()
    params['service'] = service.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BackgroundService.clearEvents',
        'params': params,
    }
    json = yield cmd_dict


@event_class('BackgroundService.recordingStateChanged')
@dataclass
class RecordingStateChanged:
    '''
    Called when the recording state for the service has been updated.
    '''
    is_recording: bool
    service: ServiceName

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RecordingStateChanged:
        return cls(
            is_recording=bool(json['isRecording']),
            service=ServiceName.from_json(json['service'])
        )


@event_class('BackgroundService.backgroundServiceEventReceived')
@dataclass
class BackgroundServiceEventReceived:
    '''
    Called with all existing backgroundServiceEvents when enabled, and all new
    events afterwards if enabled and recording.
    '''
    background_service_event: BackgroundServiceEvent

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BackgroundServiceEventReceived:
        return cls(
            background_service_event=BackgroundServiceEvent.from_json(json['backgroundServiceEvent'])
        )

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\typeguard\_importhook.py ===
from __future__ import annotations

import ast
import sys
import types
from collections.abc import Callable, Iterable
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec, SourceFileLoader
from importlib.util import cache_from_source, decode_source
from inspect import isclass
from os import PathLike
from types import CodeType, ModuleType, TracebackType
from typing import Sequence, TypeVar
from unittest.mock import patch

from ._config import global_config
from ._transformer import TypeguardTransformer

if sys.version_info >= (3, 12):
    from collections.abc import Buffer
else:
    from typing_extensions import Buffer

if sys.version_info >= (3, 11):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 10):
    from importlib.metadata import PackageNotFoundError, version
else:
    from importlib_metadata import PackageNotFoundError, version

try:
    OPTIMIZATION = "typeguard" + "".join(version("typeguard").split(".")[:3])
except PackageNotFoundError:
    OPTIMIZATION = "typeguard"

P = ParamSpec("P")
T = TypeVar("T")


# The name of this function is magical
def _call_with_frames_removed(
    f: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    return f(*args, **kwargs)


def optimized_cache_from_source(path: str, debug_override: bool | None = None) -> str:
    return cache_from_source(path, debug_override, optimization=OPTIMIZATION)


class TypeguardLoader(SourceFileLoader):
    @staticmethod
    def source_to_code(
        data: Buffer | str | ast.Module | ast.Expression | ast.Interactive,
        path: Buffer | str | PathLike[str] = "<string>",
    ) -> CodeType:
        if isinstance(data, (ast.Module, ast.Expression, ast.Interactive)):
            tree = data
        else:
            if isinstance(data, str):
                source = data
            else:
                source = decode_source(data)

            tree = _call_with_frames_removed(
                ast.parse,
                source,
                path,
                "exec",
            )

        tree = TypeguardTransformer().visit(tree)
        ast.fix_missing_locations(tree)

        if global_config.debug_instrumentation and sys.version_info >= (3, 9):
            print(
                f"Source code of {path!r} after instrumentation:\n"
                "----------------------------------------------",
                file=sys.stderr,
            )
            print(ast.unparse(tree), file=sys.stderr)
            print("----------------------------------------------", file=sys.stderr)

        return _call_with_frames_removed(
            compile, tree, path, "exec", 0, dont_inherit=True
        )

    def exec_module(self, module: ModuleType) -> None:
        # Use a custom optimization marker – the import lock should make this monkey
        # patch safe
        with patch(
            "importlib._bootstrap_external.cache_from_source",
            optimized_cache_from_source,
        ):
            super().exec_module(module)


class TypeguardFinder(MetaPathFinder):
    """
    Wraps another path finder and instruments the module with
    :func:`@typechecked <typeguard.typechecked>` if :meth:`should_instrument` returns
    ``True``.

    Should not be used directly, but rather via :func:`~.install_import_hook`.

    .. versionadded:: 2.6
    """

    def __init__(self, packages: list[str] | None, original_pathfinder: MetaPathFinder):
        self.packages = packages
        self._original_pathfinder = original_pathfinder

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: types.ModuleType | None = None,
    ) -> ModuleSpec | None:
        if self.should_instrument(fullname):
            spec = self._original_pathfinder.find_spec(fullname, path, target)
            if spec is not None and isinstance(spec.loader, SourceFileLoader):
                spec.loader = TypeguardLoader(spec.loader.name, spec.loader.path)
                return spec

        return None

    def should_instrument(self, module_name: str) -> bool:
        """
        Determine whether the module with the given name should be instrumented.

        :param module_name: full name of the module that is about to be imported (e.g.
            ``xyz.abc``)

        """
        if self.packages is None:
            return True

        for package in self.packages:
            if module_name == package or module_name.startswith(package + "."):
                return True

        return False


class ImportHookManager:
    """
    A handle that can be used to uninstall the Typeguard import hook.
    """

    def __init__(self, hook: MetaPathFinder):
        self.hook = hook

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self.uninstall()

    def uninstall(self) -> None:
        """Uninstall the import hook."""
        try:
            sys.meta_path.remove(self.hook)
        except ValueError:
            pass  # already removed


def install_import_hook(
    packages: Iterable[str] | None = None,
    *,
    cls: type[TypeguardFinder] = TypeguardFinder,
) -> ImportHookManager:
    """
    Install an import hook that instruments functions for automatic type checking.

    This only affects modules loaded **after** this hook has been installed.

    :param packages: an iterable of package names to instrument, or ``None`` to
        instrument all packages
    :param cls: a custom meta path finder class
    :return: a context manager that uninstalls the hook on exit (or when you call
        ``.uninstall()``)

    .. versionadded:: 2.6

    """
    if packages is None:
        target_packages: list[str] | None = None
    elif isinstance(packages, str):
        target_packages = [packages]
    else:
        target_packages = list(packages)

    for finder in sys.meta_path:
        if (
            isclass(finder)
            and finder.__name__ == "PathFinder"
            and hasattr(finder, "find_spec")
        ):
            break
    else:
        raise RuntimeError("Cannot find a PathFinder in sys.meta_path")

    hook = cls(target_packages, finder)
    sys.meta_path.insert(0, hook)
    return ImportHookManager(hook)

# === NexusCore/openenv\Lib\site-packages\win32\test\test_exceptions.py ===
"""Test pywin32's error semantics"""

import unittest

import pythoncom
import pywintypes
import win32api
import winerror


class TestBase(unittest.TestCase):
    def _testExceptionIndex(self, exc, index, expected):
        # Check that exception.args is the same.
        self.assertEqual(exc.args[index], expected)


class TestAPISimple(TestBase):
    def _getInvalidHandleException(self):
        try:
            win32api.CloseHandle(1)
        except win32api.error as exc:
            return exc
        self.fail("Didn't get invalid-handle exception.")

    def testSimple(self):
        self.assertRaises(pywintypes.error, win32api.CloseHandle, 1)

    def testErrnoIndex(self):
        exc = self._getInvalidHandleException()
        self._testExceptionIndex(exc, 0, winerror.ERROR_INVALID_HANDLE)

    def testFuncIndex(self):
        exc = self._getInvalidHandleException()
        self._testExceptionIndex(exc, 1, "CloseHandle")

    def testMessageIndex(self):
        exc = self._getInvalidHandleException()
        expected = win32api.FormatMessage(winerror.ERROR_INVALID_HANDLE).rstrip()
        self._testExceptionIndex(exc, 2, expected)

    def testUnpack(self):
        try:
            win32api.CloseHandle(1)
            self.fail("expected exception!")
        except win32api.error as exc:
            self.assertEqual(exc.winerror, winerror.ERROR_INVALID_HANDLE)
            self.assertEqual(exc.funcname, "CloseHandle")
            expected_msg = win32api.FormatMessage(
                winerror.ERROR_INVALID_HANDLE
            ).rstrip()
            self.assertEqual(exc.strerror, expected_msg)

    def testAsStr(self):
        exc = self._getInvalidHandleException()
        err_msg = win32api.FormatMessage(winerror.ERROR_INVALID_HANDLE).rstrip()
        # early on the result actually *was* a tuple - it must always look like one
        err_tuple = (winerror.ERROR_INVALID_HANDLE, "CloseHandle", err_msg)
        self.assertEqual(str(exc), str(err_tuple))

    def testAsTuple(self):
        exc = self._getInvalidHandleException()
        err_msg = win32api.FormatMessage(winerror.ERROR_INVALID_HANDLE).rstrip()
        # early on the result actually *was* a tuple - it must be able to be one
        err_tuple = (winerror.ERROR_INVALID_HANDLE, "CloseHandle", err_msg)
        self.assertEqual(exc.args, err_tuple)

    def testClassName(self):
        exc = self._getInvalidHandleException()
        # The error class has always been named 'error'.  That's not ideal :(
        self.assertEqual(exc.__class__.__name__, "error")

    def testIdentity(self):
        exc = self._getInvalidHandleException()
        self.assertTrue(exc.__class__ is pywintypes.error)

    def testBaseClass(self):
        self.assertEqual(pywintypes.error.__bases__, (Exception,))

    def testAttributes(self):
        exc = self._getInvalidHandleException()
        err_msg = win32api.FormatMessage(winerror.ERROR_INVALID_HANDLE).rstrip()
        self.assertEqual(exc.winerror, winerror.ERROR_INVALID_HANDLE)
        self.assertEqual(exc.strerror, err_msg)
        self.assertEqual(exc.funcname, "CloseHandle")

    # some tests for 'insane' args.
    def testStrangeArgsNone(self):
        try:
            raise pywintypes.error
            self.fail("Expected exception")
        except pywintypes.error as exc:
            self.assertEqual(exc.args, ())
            self.assertEqual(exc.winerror, None)
            self.assertEqual(exc.funcname, None)
            self.assertEqual(exc.strerror, None)

    def testStrangeArgsNotEnough(self):
        try:
            raise pywintypes.error("foo")
            self.fail("Expected exception")
        except pywintypes.error as exc:
            self.assertEqual(exc.args[0], "foo")
            # 'winerror' always args[0]
            self.assertEqual(exc.winerror, "foo")
            self.assertEqual(exc.funcname, None)
            self.assertEqual(exc.strerror, None)

    def testStrangeArgsTooMany(self):
        try:
            raise pywintypes.error("foo", "bar", "you", "never", "kn", 0)
            self.fail("Expected exception")
        except pywintypes.error as exc:
            self.assertEqual(exc.args[0], "foo")
            self.assertEqual(exc.args[-1], 0)
            self.assertEqual(exc.winerror, "foo")
            self.assertEqual(exc.funcname, "bar")
            self.assertEqual(exc.strerror, "you")


class TestCOMSimple(TestBase):
    def _getException(self):
        try:
            pythoncom.StgOpenStorage("foo", None, 0)
        except pythoncom.com_error as exc:
            return exc
        self.fail("Didn't get storage exception.")

    def testIs(self):
        self.assertTrue(pythoncom.com_error is pywintypes.com_error)

    def testSimple(self):
        self.assertRaises(pythoncom.com_error, pythoncom.StgOpenStorage, "foo", None, 0)

    def testErrnoIndex(self):
        exc = self._getException()
        self._testExceptionIndex(exc, 0, winerror.STG_E_INVALIDFLAG)

    def testMessageIndex(self):
        exc = self._getException()
        expected = win32api.FormatMessage(winerror.STG_E_INVALIDFLAG).rstrip()
        self._testExceptionIndex(exc, 1, expected)

    def testAsStr(self):
        exc = self._getException()
        err_msg = win32api.FormatMessage(winerror.STG_E_INVALIDFLAG).rstrip()
        # early on the result actually *was* a tuple - it must always look like one
        err_tuple = (winerror.STG_E_INVALIDFLAG, err_msg, None, None)
        self.assertEqual(str(exc), str(err_tuple))

    def testAsTuple(self):
        exc = self._getException()
        err_msg = win32api.FormatMessage(winerror.STG_E_INVALIDFLAG).rstrip()
        # early on the result actually *was* a tuple - it must be able to be one
        err_tuple = (winerror.STG_E_INVALIDFLAG, err_msg, None, None)
        self.assertEqual(exc.args, err_tuple)

    def testClassName(self):
        exc = self._getException()
        self.assertEqual(exc.__class__.__name__, "com_error")

    def testIdentity(self):
        exc = self._getException()
        self.assertTrue(exc.__class__ is pywintypes.com_error)

    def testBaseClass(self):
        exc = self._getException()
        self.assertEqual(pywintypes.com_error.__bases__, (Exception,))

    def testAttributes(self):
        exc = self._getException()
        err_msg = win32api.FormatMessage(winerror.STG_E_INVALIDFLAG).rstrip()
        self.assertEqual(exc.hresult, winerror.STG_E_INVALIDFLAG)
        self.assertEqual(exc.strerror, err_msg)
        self.assertEqual(exc.argerror, None)
        self.assertEqual(exc.excepinfo, None)

    def testStrangeArgsNone(self):
        try:
            raise pywintypes.com_error
            self.fail("Expected exception")
        except pywintypes.com_error as exc:
            self.assertEqual(exc.args, ())
            self.assertEqual(exc.hresult, None)
            self.assertEqual(exc.strerror, None)
            self.assertEqual(exc.argerror, None)
            self.assertEqual(exc.excepinfo, None)

    def testStrangeArgsNotEnough(self):
        try:
            raise pywintypes.com_error("foo")
            self.fail("Expected exception")
        except pywintypes.com_error as exc:
            self.assertEqual(exc.args[0], "foo")
            self.assertEqual(exc.hresult, "foo")
            self.assertEqual(exc.strerror, None)
            self.assertEqual(exc.excepinfo, None)
            self.assertEqual(exc.argerror, None)

    def testStrangeArgsTooMany(self):
        try:
            raise pywintypes.com_error("foo", "bar", "you", "never", "kn", 0)
            self.fail("Expected exception")
        except pywintypes.com_error as exc:
            self.assertEqual(exc.args[0], "foo")
            self.assertEqual(exc.args[-1], 0)
            self.assertEqual(exc.hresult, "foo")
            self.assertEqual(exc.strerror, "bar")
            self.assertEqual(exc.excepinfo, "you")
            self.assertEqual(exc.argerror, "never")


if __name__ == "__main__":
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\zmq\utils\garbage.py ===
"""Garbage collection thread for representing zmq refcount of Python objects
used in zero-copy sends.
"""

# Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.

import atexit
import struct
import warnings
from collections import namedtuple
from os import getpid
from threading import Event, Lock, Thread

import zmq

gcref = namedtuple('gcref', ['obj', 'event'])


class GarbageCollectorThread(Thread):
    """Thread in which garbage collection actually happens."""

    def __init__(self, gc):
        super().__init__()
        self.gc = gc
        self.daemon = True
        self.pid = getpid()
        self.ready = Event()

    def run(self):
        # detect fork at beginning of the thread
        if getpid is None or getpid() != self.pid:
            self.ready.set()
            return
        try:
            s = self.gc.context.socket(zmq.PULL)
            s.linger = 0
            s.bind(self.gc.url)
        finally:
            self.ready.set()

        while True:
            # detect fork
            if getpid is None or getpid() != self.pid:
                return
            msg = s.recv()
            if msg == b'DIE':
                break
            fmt = 'L' if len(msg) == 4 else 'Q'
            key = struct.unpack(fmt, msg)[0]
            tup = self.gc.refs.pop(key, None)
            if tup and tup.event:
                tup.event.set()
            del tup
        s.close()


class GarbageCollector:
    """PyZMQ Garbage Collector

    Used for representing the reference held by libzmq during zero-copy sends.
    This object holds a dictionary, keyed by Python id,
    of the Python objects whose memory are currently in use by zeromq.

    When zeromq is done with the memory, it sends a message on an inproc PUSH socket
    containing the packed size_t (32 or 64-bit unsigned int),
    which is the key in the dict.
    When the PULL socket in the gc thread receives that message,
    the reference is popped from the dict,
    and any tracker events that should be signaled fire.
    """

    refs = None
    _context = None
    _lock = None
    url = "inproc://pyzmq.gc.01"

    def __init__(self, context=None):
        super().__init__()
        self.refs = {}
        self.pid = None
        self.thread = None
        self._context = context
        self._lock = Lock()
        self._stay_down = False
        self._push = None
        self._push_mutex = None
        atexit.register(self._atexit)

    @property
    def context(self):
        if self._context is None:
            if Thread.__module__.startswith('gevent'):
                # gevent has monkey-patched Thread, use green Context
                from zmq import green

                self._context = green.Context()
            else:
                self._context = zmq.Context()
        return self._context

    @context.setter
    def context(self, ctx):
        if self.is_alive():
            if self.refs:
                warnings.warn(
                    "Replacing gc context while gc is running", RuntimeWarning
                )
            self.stop()
        self._context = ctx

    def _atexit(self):
        """atexit callback

        sets _stay_down flag so that gc doesn't try to start up again in other atexit handlers
        """
        self._stay_down = True
        self.stop()

    def stop(self):
        """stop the garbage-collection thread"""
        if not self.is_alive():
            return
        self._stop()

    def _clear(self):
        """Clear state

        called after stop or when setting up a new subprocess
        """
        self._push = None
        self._push_mutex = None
        self.thread = None
        self.refs.clear()
        self.context = None

    def _stop(self):
        push = self.context.socket(zmq.PUSH)
        push.connect(self.url)
        push.send(b'DIE')
        push.close()
        if self._push:
            self._push.close()
        self.thread.join()
        self.context.term()
        self._clear()

    @property
    def _push_socket(self):
        """The PUSH socket for use in the zmq message destructor callback."""
        if getattr(self, "_stay_down", False):
            raise RuntimeError("zmq gc socket requested during shutdown")
        if not self.is_alive() or self._push is None:
            self._push = self.context.socket(zmq.PUSH)
            self._push.connect(self.url)
        return self._push

    def start(self):
        """Start a new garbage collection thread.

        Creates a new zmq Context used for garbage collection.
        Under most circumstances, this will only be called once per process.
        """
        if self.thread is not None and self.pid != getpid():
            # It's re-starting, must free earlier thread's context
            # since a fork probably broke it
            self._clear()
        self.pid = getpid()
        self.refs = {}
        self.thread = GarbageCollectorThread(self)
        self.thread.start()
        self.thread.ready.wait()

    def is_alive(self):
        """Is the garbage collection thread currently running?

        Includes checks for process shutdown or fork.
        """
        if (
            getpid is None
            or getpid() != self.pid
            or self.thread is None
            or not self.thread.is_alive()
        ):
            return False
        return True

    def store(self, obj, event=None):
        """store an object and (optionally) event for zero-copy"""
        if not self.is_alive():
            if self._stay_down:
                return 0
            # safely start the gc thread
            # use lock and double check,
            # so we don't start multiple threads
            with self._lock:
                if not self.is_alive():
                    self.start()
        tup = gcref(obj, event)
        theid = id(tup)
        self.refs[theid] = tup
        return theid

    def __del__(self):
        if not self.is_alive():
            return
        try:
            self.stop()
        except Exception as e:
            raise (e)


gc = GarbageCollector()

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\email_templates\key_created_email.py ===
"""
Modern Email Templates for LiteLLM Email Service with professional styling
"""

KEY_CREATED_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your API Key is Ready</title>
    <style>
        body, html {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #333333;
            background-color: #f8fafc;
            line-height: 1.5;
        }}
        .container {{
            max-width: 560px;
            margin: 20px auto;
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .header {{
            padding: 24px 0;
            text-align: center;
            border-bottom: 1px solid #f1f5f9;
        }}
        .content {{
            padding: 32px 40px;
        }}
        .greeting {{
            font-size: 16px;
            margin-bottom: 20px;
            color: #333333;
        }}
        .message {{
            font-size: 16px;
            color: #333333;
            margin-bottom: 20px;
        }}
        .key-container {{
            margin: 28px 0;
        }}
        .key-label {{
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 8px;
            color: #4b5563;
        }}
        .key {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            word-break: break-all;
            background-color: #f9fafb;
            border-radius: 6px;
            padding: 16px;
            font-size: 14px;
            border: 1px solid #e5e7eb;
            color: #4338ca;
        }}
        h2 {{
            font-size: 18px;
            font-weight: 600;
            margin-top: 36px;
            margin-bottom: 16px;
            color: #333333;
        }}
        .budget-info {{
            background-color: #f0fdf4;
            border-radius: 6px;
            padding: 14px 16px;
            margin: 24px 0;
            font-size: 14px;
            border: 1px solid #dcfce7;
        }}
        .code-block {{
            background-color: #f8fafc;
            color: #334155;
            border-radius: 8px;
            padding: 20px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 13px;
            overflow-x: auto;
            margin: 20px 0;
            line-height: 1.6;
            border: 1px solid #e2e8f0;
        }}
        .code-comment {{
            color: #64748b;
        }}
        .code-string {{
            color: #0369a1;
        }}
        .code-keyword {{
            color: #7e22ce;
        }}
        .btn {{
            display: inline-block;
            padding: 8px 20px;
            background-color: #6366f1;
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            margin-top: 24px;
            text-align: center;
            font-size: 14px;
            transition: background-color 0.2s;
        }}
        .btn:hover {{
            background-color: #4f46e5;
            color: #ffffff !important;
        }}
        .separator {{
            height: 1px;
            background-color: #f1f5f9;
            margin: 40px 0 30px;
        }}
        .footer {{
            padding: 24px 40px 32px;
            text-align: center;
            color: #64748b;
            font-size: 13px;
            background-color: #f8fafc;
            border-top: 1px solid #f1f5f9;
        }}
        .social-links {{
            margin-top: 12px;
        }}
        .social-links a {{
            display: inline-block;
            margin: 0 8px;
            color: #64748b;
            text-decoration: none;
        }}
        @media only screen and (max-width: 620px) {{
            .container {{
                width: 100%;
                margin: 0;
                border-radius: 0;
            }}
            .content {{
                padding: 24px 20px;
            }}
            .footer {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="{email_logo_url}" alt="LiteLLM Logo" style="height: 32px; width: auto;">
        </div>
        <div class="content">
            <div class="greeting">
                <p>Hi {recipient_email},</p>
            </div>
            
            <div class="message">
                <p>Great news! Your LiteLLM API key is ready to use.</p>
            </div>
            
            <div class="budget-info">
                <p style="margin: 0;"><strong>Monthly Budget:</strong> {key_budget}</p>
            </div>
            
            <div class="key-container">
                <div class="key-label">Your API Key</div>
                <div class="key">{key_token}</div>
            </div>
            
            <h2>Quick Start Guide</h2>
            <p>Here's how to use your key with the OpenAI SDK:</p>
            
            <div class="code-block">
<span class="code-keyword">import</span> openai<br>
<br>
client = openai.OpenAI(<br>
&nbsp;&nbsp;api_key=<span class="code-string">"{key_token}"</span>,<br>
&nbsp;&nbsp;base_url=<span class="code-string">"{base_url}"</span><br>
)<br>
<br>
response = client.chat.completions.create(<br>
&nbsp;&nbsp;model=<span class="code-string">"gpt-3.5-turbo"</span>, <span class="code-comment"># model to send to the proxy</span><br>
&nbsp;&nbsp;messages = [<br>
&nbsp;&nbsp;&nbsp;&nbsp;{{<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="code-string">"role"</span>: <span class="code-string">"user"</span>,<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="code-string">"content"</span>: <span class="code-string">"this is a test request, write a short poem"</span><br>
&nbsp;&nbsp;&nbsp;&nbsp;}}<br>
&nbsp;&nbsp;]<br>
)
            </div>
            
            <a href="https://docs.litellm.ai/docs/proxy/user_keys" class="btn" style="color: #ffffff;">View Documentation</a>
            
            <div class="separator"></div>
            
            <h2>Need Help?</h2>
            <p>If you have any questions or need assistance, please contact us at {email_support_contact}.</p>
        </div>
        {email_footer}
    </div>
</body>
</html>
"""

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai\common_utils.py ===
"""
Common helpers / utils across al OpenAI endpoints
"""

import hashlib
import json
from typing import Any, Dict, List, Literal, Optional, Union

import httpx
import openai
from openai import AsyncAzureOpenAI, AsyncOpenAI, AzureOpenAI, OpenAI

import litellm
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.llms.custom_httpx.http_handler import (
    _DEFAULT_TTL_FOR_HTTPX_CLIENTS,
    AsyncHTTPHandler,
)


class OpenAIError(BaseLLMException):
    def __init__(
        self,
        status_code: int,
        message: str,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
        headers: Optional[Union[dict, httpx.Headers]] = None,
        body: Optional[dict] = None,
    ):
        self.status_code = status_code
        self.message = message
        self.headers = headers
        if request:
            self.request = request
        else:
            self.request = httpx.Request(method="POST", url="https://api.openai.com/v1")
        if response:
            self.response = response
        else:
            self.response = httpx.Response(
                status_code=status_code, request=self.request
            )
        super().__init__(
            status_code=status_code,
            message=self.message,
            headers=self.headers,
            request=self.request,
            response=self.response,
            body=body,
        )


####### Error Handling Utils for OpenAI API #######################
###################################################################
def drop_params_from_unprocessable_entity_error(
    e: Union[openai.UnprocessableEntityError, httpx.HTTPStatusError],
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Helper function to read OpenAI UnprocessableEntityError and drop the params that raised an error from the error message.

    Args:
    e (UnprocessableEntityError): The UnprocessableEntityError exception
    data (Dict[str, Any]): The original data dictionary containing all parameters

    Returns:
    Dict[str, Any]: A new dictionary with invalid parameters removed
    """
    invalid_params: List[str] = []
    if isinstance(e, httpx.HTTPStatusError):
        error_json = e.response.json()
        error_message = error_json.get("error", {})
        error_body = error_message
    else:
        error_body = e.body
    if (
        error_body is not None
        and isinstance(error_body, dict)
        and error_body.get("message")
    ):
        message = error_body.get("message", {})
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                message = {"detail": message}
        detail = message.get("detail")

        if isinstance(detail, List) and len(detail) > 0 and isinstance(detail[0], dict):
            for error_dict in detail:
                if (
                    error_dict.get("loc")
                    and isinstance(error_dict.get("loc"), list)
                    and len(error_dict.get("loc")) == 2
                ):
                    invalid_params.append(error_dict["loc"][1])

    new_data = {k: v for k, v in data.items() if k not in invalid_params}

    return new_data


class BaseOpenAILLM:
    """
    Base class for OpenAI LLMs for getting their httpx clients and SSL verification settings
    """

    @staticmethod
    def get_cached_openai_client(
        client_initialization_params: dict, client_type: Literal["openai", "azure"]
    ) -> Optional[Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]]:
        """Retrieves the OpenAI client from the in-memory cache based on the client initialization parameters"""
        _cache_key = BaseOpenAILLM.get_openai_client_cache_key(
            client_initialization_params=client_initialization_params,
            client_type=client_type,
        )
        _cached_client = litellm.in_memory_llm_clients_cache.get_cache(_cache_key)
        return _cached_client

    @staticmethod
    def set_cached_openai_client(
        openai_client: Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI],
        client_type: Literal["openai", "azure"],
        client_initialization_params: dict,
    ):
        """Stores the OpenAI client in the in-memory cache for _DEFAULT_TTL_FOR_HTTPX_CLIENTS SECONDS"""
        _cache_key = BaseOpenAILLM.get_openai_client_cache_key(
            client_initialization_params=client_initialization_params,
            client_type=client_type,
        )
        litellm.in_memory_llm_clients_cache.set_cache(
            key=_cache_key,
            value=openai_client,
            ttl=_DEFAULT_TTL_FOR_HTTPX_CLIENTS,
        )

    @staticmethod
    def get_openai_client_cache_key(
        client_initialization_params: dict, client_type: Literal["openai", "azure"]
    ) -> str:
        """Creates a cache key for the OpenAI client based on the client initialization parameters"""
        hashed_api_key = None
        if client_initialization_params.get("api_key") is not None:
            hash_object = hashlib.sha256(
                client_initialization_params.get("api_key", "").encode()
            )
            # Hexadecimal representation of the hash
            hashed_api_key = hash_object.hexdigest()

        # Create a more readable cache key using a list of key-value pairs
        key_parts = [
            f"hashed_api_key={hashed_api_key}",
            f"is_async={client_initialization_params.get('is_async')}",
        ]

        LITELLM_CLIENT_SPECIFIC_PARAMS = [
            "timeout",
            "max_retries",
            "organization",
            "api_base",
        ]
        openai_client_fields = (
            BaseOpenAILLM.get_openai_client_initialization_param_fields(
                client_type=client_type
            )
            + LITELLM_CLIENT_SPECIFIC_PARAMS
        )

        for param in openai_client_fields:
            key_parts.append(f"{param}={client_initialization_params.get(param)}")

        _cache_key = ",".join(key_parts)
        return _cache_key

    @staticmethod
    def get_openai_client_initialization_param_fields(
        client_type: Literal["openai", "azure"]
    ) -> List[str]:
        """Returns a list of fields that are used to initialize the OpenAI client"""
        import inspect

        from openai import AzureOpenAI, OpenAI

        if client_type == "openai":
            signature = inspect.signature(OpenAI.__init__)
        else:
            signature = inspect.signature(AzureOpenAI.__init__)

        # Extract parameter names, excluding 'self'
        param_names = [param for param in signature.parameters if param != "self"]
        return param_names

    @staticmethod
    def _get_async_http_client() -> Optional[httpx.AsyncClient]:
        if litellm.aclient_session is not None:
            return litellm.aclient_session

        return httpx.AsyncClient(
            limits=httpx.Limits(max_connections=1000, max_keepalive_connections=100),
            verify=litellm.ssl_verify,
            transport=AsyncHTTPHandler._create_async_transport(),
        )

    @staticmethod
    def _get_sync_http_client() -> Optional[httpx.Client]:
        if litellm.client_session is not None:
            return litellm.client_session
        return httpx.Client(
            limits=httpx.Limits(max_connections=1000, max_keepalive_connections=100),
            verify=litellm.ssl_verify,
        )

# === NexusCore/openenv\Lib\site-packages\openai\resources\chat\completions\messages.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing_extensions import Literal

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import maybe_transform
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ....pagination import SyncCursorPage, AsyncCursorPage
from ...._base_client import AsyncPaginator, make_request_options
from ....types.chat.completions import message_list_params
from ....types.chat.chat_completion_store_message import ChatCompletionStoreMessage

__all__ = ["Messages", "AsyncMessages"]


class Messages(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> MessagesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return MessagesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> MessagesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return MessagesWithStreamingResponse(self)

    def list(
        self,
        completion_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[ChatCompletionStoreMessage]:
        """Get the messages in a stored chat completion.

        Only Chat Completions that have
        been created with the `store` parameter set to `true` will be returned.

        Args:
          after: Identifier for the last message from the previous pagination request.

          limit: Number of messages to retrieve.

          order: Sort order for messages by timestamp. Use `asc` for ascending order or `desc`
              for descending order. Defaults to `asc`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not completion_id:
            raise ValueError(f"Expected a non-empty value for `completion_id` but received {completion_id!r}")
        return self._get_api_list(
            f"/chat/completions/{completion_id}/messages",
            page=SyncCursorPage[ChatCompletionStoreMessage],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                        "order": order,
                    },
                    message_list_params.MessageListParams,
                ),
            ),
            model=ChatCompletionStoreMessage,
        )


class AsyncMessages(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncMessagesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncMessagesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncMessagesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncMessagesWithStreamingResponse(self)

    def list(
        self,
        completion_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[ChatCompletionStoreMessage, AsyncCursorPage[ChatCompletionStoreMessage]]:
        """Get the messages in a stored chat completion.

        Only Chat Completions that have
        been created with the `store` parameter set to `true` will be returned.

        Args:
          after: Identifier for the last message from the previous pagination request.

          limit: Number of messages to retrieve.

          order: Sort order for messages by timestamp. Use `asc` for ascending order or `desc`
              for descending order. Defaults to `asc`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not completion_id:
            raise ValueError(f"Expected a non-empty value for `completion_id` but received {completion_id!r}")
        return self._get_api_list(
            f"/chat/completions/{completion_id}/messages",
            page=AsyncCursorPage[ChatCompletionStoreMessage],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                        "order": order,
                    },
                    message_list_params.MessageListParams,
                ),
            ),
            model=ChatCompletionStoreMessage,
        )


class MessagesWithRawResponse:
    def __init__(self, messages: Messages) -> None:
        self._messages = messages

        self.list = _legacy_response.to_raw_response_wrapper(
            messages.list,
        )


class AsyncMessagesWithRawResponse:
    def __init__(self, messages: AsyncMessages) -> None:
        self._messages = messages

        self.list = _legacy_response.async_to_raw_response_wrapper(
            messages.list,
        )


class MessagesWithStreamingResponse:
    def __init__(self, messages: Messages) -> None:
        self._messages = messages

        self.list = to_streamed_response_wrapper(
            messages.list,
        )


class AsyncMessagesWithStreamingResponse:
    def __init__(self, messages: AsyncMessages) -> None:
        self._messages = messages

        self.list = async_to_streamed_response_wrapper(
            messages.list,
        )