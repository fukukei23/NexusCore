
# === NexusCore/tools\exports\export_20250803_114325\combined_237.py ===

# === NexusCore/openenv\Lib\site-packages\pygments\formatters\__init__.py ===
"""
    pygments.formatters
    ~~~~~~~~~~~~~~~~~~~

    Pygments formatters.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import sys
import types
import fnmatch
from os.path import basename

from pygments.formatters._mapping import FORMATTERS
from pygments.plugin import find_plugin_formatters
from pygments.util import ClassNotFound

__all__ = ['get_formatter_by_name', 'get_formatter_for_filename',
           'get_all_formatters', 'load_formatter_from_file'] + list(FORMATTERS)

_formatter_cache = {}  # classes by name
_pattern_cache = {}


def _fn_matches(fn, glob):
    """Return whether the supplied file name fn matches pattern filename."""
    if glob not in _pattern_cache:
        pattern = _pattern_cache[glob] = re.compile(fnmatch.translate(glob))
        return pattern.match(fn)
    return _pattern_cache[glob].match(fn)


def _load_formatters(module_name):
    """Load a formatter (and all others in the module too)."""
    mod = __import__(module_name, None, None, ['__all__'])
    for formatter_name in mod.__all__:
        cls = getattr(mod, formatter_name)
        _formatter_cache[cls.name] = cls


def get_all_formatters():
    """Return a generator for all formatter classes."""
    # NB: this returns formatter classes, not info like get_all_lexers().
    for info in FORMATTERS.values():
        if info[1] not in _formatter_cache:
            _load_formatters(info[0])
        yield _formatter_cache[info[1]]
    for _, formatter in find_plugin_formatters():
        yield formatter


def find_formatter_class(alias):
    """Lookup a formatter by alias.

    Returns None if not found.
    """
    for module_name, name, aliases, _, _ in FORMATTERS.values():
        if alias in aliases:
            if name not in _formatter_cache:
                _load_formatters(module_name)
            return _formatter_cache[name]
    for _, cls in find_plugin_formatters():
        if alias in cls.aliases:
            return cls


def get_formatter_by_name(_alias, **options):
    """
    Return an instance of a :class:`.Formatter` subclass that has `alias` in its
    aliases list. The formatter is given the `options` at its instantiation.

    Will raise :exc:`pygments.util.ClassNotFound` if no formatter with that
    alias is found.
    """
    cls = find_formatter_class(_alias)
    if cls is None:
        raise ClassNotFound(f"no formatter found for name {_alias!r}")
    return cls(**options)


def load_formatter_from_file(filename, formattername="CustomFormatter", **options):
    """
    Return a `Formatter` subclass instance loaded from the provided file, relative
    to the current directory.

    The file is expected to contain a Formatter class named ``formattername``
    (by default, CustomFormatter). Users should be very careful with the input, because
    this method is equivalent to running ``eval()`` on the input file. The formatter is
    given the `options` at its instantiation.

    :exc:`pygments.util.ClassNotFound` is raised if there are any errors loading
    the formatter.

    .. versionadded:: 2.2
    """
    try:
        # This empty dict will contain the namespace for the exec'd file
        custom_namespace = {}
        with open(filename, 'rb') as f:
            exec(f.read(), custom_namespace)
        # Retrieve the class `formattername` from that namespace
        if formattername not in custom_namespace:
            raise ClassNotFound(f'no valid {formattername} class found in {filename}')
        formatter_class = custom_namespace[formattername]
        # And finally instantiate it with the options
        return formatter_class(**options)
    except OSError as err:
        raise ClassNotFound(f'cannot read {filename}: {err}')
    except ClassNotFound:
        raise
    except Exception as err:
        raise ClassNotFound(f'error when loading custom formatter: {err}')


def get_formatter_for_filename(fn, **options):
    """
    Return a :class:`.Formatter` subclass instance that has a filename pattern
    matching `fn`. The formatter is given the `options` at its instantiation.

    Will raise :exc:`pygments.util.ClassNotFound` if no formatter for that filename
    is found.
    """
    fn = basename(fn)
    for modname, name, _, filenames, _ in FORMATTERS.values():
        for filename in filenames:
            if _fn_matches(fn, filename):
                if name not in _formatter_cache:
                    _load_formatters(modname)
                return _formatter_cache[name](**options)
    for _name, cls in find_plugin_formatters():
        for filename in cls.filenames:
            if _fn_matches(fn, filename):
                return cls(**options)
    raise ClassNotFound(f"no formatter found for file name {fn!r}")


class _automodule(types.ModuleType):
    """Automatically import formatters."""

    def __getattr__(self, name):
        info = FORMATTERS.get(name)
        if info:
            _load_formatters(info[0])
            cls = _formatter_cache[info[1]]
            setattr(self, name, cls)
            return cls
        raise AttributeError(name)


oldmod = sys.modules[__name__]
newmod = _automodule(__name__)
newmod.__dict__.update(oldmod.__dict__)
sys.modules[__name__] = newmod
del newmod.newmod, newmod.oldmod, newmod.sys, newmod.types

# === NexusCore/openenv\Lib\site-packages\pyreadline3\clipboard\win32_clipboard.py ===
# -*- coding: utf-8 -*-
# *****************************************************************************
#     Copyright (C) 2003-2006 Jack Trainor.
#     Copyright (C) 2006-2020 Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#     Copyright (C) 2020 Bassem Girgis. <brgirgis@gmail.com>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# *****************************************************************************
###################################
#
# Based on recipe posted to ctypes-users
# see archive
# http://aspn.activestate.com/ASPN/Mail/Message/ctypes-users/1771866
#
#

##########################################################################
#
# The Python win32clipboard lib functions work well enough ... except that they
# can only cut and paste items from within one application, not across
# applications or processes.
#
# I've written a number of Python text filters I like to run on the contents of
# the clipboard so I need to call the Windows clipboard API with global memory
# for my filters to work properly.
#
# Here's some sample code solving this problem using ctypes.
#
# This is my first work with ctypes.  It's powerful stuff, but passing
# arguments in and out of functions is tricky.  More sample code would have
# been helpful, hence this contribution.
#
##########################################################################

import ctypes
import ctypes.wintypes as wintypes
from ctypes import (
    addressof,
    c_buffer,
    c_char_p,
    c_int,
    c_size_t,
    c_void_p,
    c_wchar_p,
    cast,
    create_unicode_buffer,
    sizeof,
    windll,
    wstring_at,
)
from typing import Union

from pyreadline3.keysyms.winconstants import CF_UNICODETEXT, GHND
from pyreadline3.unicode_helper import ensure_unicode

OpenClipboard = windll.user32.OpenClipboard
OpenClipboard.argtypes = [wintypes.HWND]
OpenClipboard.restype = wintypes.BOOL

EmptyClipboard = windll.user32.EmptyClipboard

GetClipboardData = windll.user32.GetClipboardData
GetClipboardData.argtypes = [wintypes.UINT]
GetClipboardData.restype = wintypes.HANDLE

GetClipboardFormatName = windll.user32.GetClipboardFormatNameA
GetClipboardFormatName.argtypes = [wintypes.UINT, c_char_p, c_int]

SetClipboardData = windll.user32.SetClipboardData
SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
SetClipboardData.restype = wintypes.HANDLE

EnumClipboardFormats = windll.user32.EnumClipboardFormats
EnumClipboardFormats.argtypes = [c_int]

CloseClipboard = windll.user32.CloseClipboard
CloseClipboard.argtypes = []


GlobalAlloc = windll.kernel32.GlobalAlloc
GlobalAlloc.argtypes = [wintypes.UINT, c_size_t]
GlobalAlloc.restype = wintypes.HGLOBAL
GlobalLock = windll.kernel32.GlobalLock
GlobalLock.argtypes = [wintypes.HGLOBAL]
GlobalLock.restype = c_void_p
GlobalUnlock = windll.kernel32.GlobalUnlock
GlobalUnlock.argtypes = [c_int]

_strncpy = ctypes.windll.kernel32.lstrcpynW
_strncpy.restype = c_wchar_p
_strncpy.argtypes = [c_wchar_p, c_wchar_p, c_size_t]


def _enum() -> None:
    OpenClipboard(0)

    q = EnumClipboardFormats(0)
    while q:
        q = EnumClipboardFormats(q)

    CloseClipboard()


def _get_format_name(format_str: str) -> bytes:
    buffer = c_buffer(100)
    bufferSize = sizeof(buffer)

    OpenClipboard(0)

    GetClipboardFormatName(format_str, buffer, bufferSize)

    CloseClipboard()

    return buffer.value


def get_clipboard_text() -> str:
    text = ""

    if OpenClipboard(0):
        h_clip_mem = GetClipboardData(CF_UNICODETEXT)

        if h_clip_mem:
            text = wstring_at(GlobalLock(h_clip_mem))
            GlobalUnlock(h_clip_mem)

        CloseClipboard()

    return text


def set_clipboard_text(text: Union[str, bytes]) -> None:
    buffer = create_unicode_buffer(ensure_unicode(text))
    buffer_size = sizeof(buffer)

    h_global_mem = GlobalAlloc(GHND, c_size_t(buffer_size))
    GlobalLock.restype = c_void_p
    lp_global_mem = GlobalLock(h_global_mem)

    _strncpy(
        cast(lp_global_mem, c_wchar_p),
        cast(addressof(buffer), c_wchar_p),
        c_size_t(buffer_size),
    )

    GlobalUnlock(c_int(h_global_mem))

    if OpenClipboard(0):
        EmptyClipboard()
        SetClipboardData(CF_UNICODETEXT, h_global_mem)
        CloseClipboard()


if __name__ == "__main__":
    txt = get_clipboard_text()  # display last text clipped
    print(txt)

# === NexusCore/openenv\Lib\site-packages\openai\_exceptions.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, cast
from typing_extensions import Literal

import httpx

from ._utils import is_dict
from ._models import construct_type

if TYPE_CHECKING:
    from .types.chat import ChatCompletion

__all__ = [
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "UnprocessableEntityError",
    "RateLimitError",
    "InternalServerError",
    "LengthFinishReasonError",
    "ContentFilterFinishReasonError",
]


class OpenAIError(Exception):
    pass


class APIError(OpenAIError):
    message: str
    request: httpx.Request

    body: object | None
    """The API response body.

    If the API responded with a valid JSON structure then this property will be the
    decoded result.

    If it isn't a valid JSON structure then this will be the raw response.

    If there was no response associated with this error then it will be `None`.
    """

    code: Optional[str] = None
    param: Optional[str] = None
    type: Optional[str]

    def __init__(self, message: str, request: httpx.Request, *, body: object | None) -> None:
        super().__init__(message)
        self.request = request
        self.message = message
        self.body = body

        if is_dict(body):
            self.code = cast(Any, construct_type(type_=Optional[str], value=body.get("code")))
            self.param = cast(Any, construct_type(type_=Optional[str], value=body.get("param")))
            self.type = cast(Any, construct_type(type_=str, value=body.get("type")))
        else:
            self.code = None
            self.param = None
            self.type = None


class APIResponseValidationError(APIError):
    response: httpx.Response
    status_code: int

    def __init__(self, response: httpx.Response, body: object | None, *, message: str | None = None) -> None:
        super().__init__(message or "Data returned by API invalid for expected schema.", response.request, body=body)
        self.response = response
        self.status_code = response.status_code


class APIStatusError(APIError):
    """Raised when an API response has a status code of 4xx or 5xx."""

    response: httpx.Response
    status_code: int
    request_id: str | None

    def __init__(self, message: str, *, response: httpx.Response, body: object | None) -> None:
        super().__init__(message, response.request, body=body)
        self.response = response
        self.status_code = response.status_code
        self.request_id = response.headers.get("x-request-id")


class APIConnectionError(APIError):
    def __init__(self, *, message: str = "Connection error.", request: httpx.Request) -> None:
        super().__init__(message, request, body=None)


class APITimeoutError(APIConnectionError):
    def __init__(self, request: httpx.Request) -> None:
        super().__init__(message="Request timed out.", request=request)


class BadRequestError(APIStatusError):
    status_code: Literal[400] = 400  # pyright: ignore[reportIncompatibleVariableOverride]


class AuthenticationError(APIStatusError):
    status_code: Literal[401] = 401  # pyright: ignore[reportIncompatibleVariableOverride]


class PermissionDeniedError(APIStatusError):
    status_code: Literal[403] = 403  # pyright: ignore[reportIncompatibleVariableOverride]


class NotFoundError(APIStatusError):
    status_code: Literal[404] = 404  # pyright: ignore[reportIncompatibleVariableOverride]


class ConflictError(APIStatusError):
    status_code: Literal[409] = 409  # pyright: ignore[reportIncompatibleVariableOverride]


class UnprocessableEntityError(APIStatusError):
    status_code: Literal[422] = 422  # pyright: ignore[reportIncompatibleVariableOverride]


class RateLimitError(APIStatusError):
    status_code: Literal[429] = 429  # pyright: ignore[reportIncompatibleVariableOverride]


class InternalServerError(APIStatusError):
    pass


class LengthFinishReasonError(OpenAIError):
    completion: ChatCompletion
    """The completion that caused this error.

    Note: this will *not* be a complete `ChatCompletion` object when streaming as `usage`
          will not be included.
    """

    def __init__(self, *, completion: ChatCompletion) -> None:
        msg = "Could not parse response content as the length limit was reached"
        if completion.usage:
            msg += f" - {completion.usage}"

        super().__init__(msg)
        self.completion = completion


class ContentFilterFinishReasonError(OpenAIError):
    def __init__(self) -> None:
        super().__init__(
            f"Could not parse response content as the request was rejected by the content filter",
        )

# === NexusCore/openenv\Lib\site-packages\google\oauth2\webauthn_types.py ===
from dataclasses import dataclass
import json
from typing import Any, Dict, List, Optional

from google.auth import exceptions


@dataclass(frozen=True)
class PublicKeyCredentialDescriptor:
    """Descriptor for a security key based credential.

    https://www.w3.org/TR/webauthn-3/#dictionary-credential-descriptor

    Args:
        id: <url-safe base64-encoded> credential id (key handle).
        transports: <'usb'|'nfc'|'ble'|'internal'> List of supported transports.
    """

    id: str
    transports: Optional[List[str]] = None

    def to_dict(self):
        cred = {"type": "public-key", "id": self.id}
        if self.transports:
            cred["transports"] = self.transports
        return cred


@dataclass
class AuthenticationExtensionsClientInputs:
    """Client extensions inputs for WebAuthn extensions.

    Args:
        appid: app id that can be asserted with in addition to rpid.
            https://www.w3.org/TR/webauthn-3/#sctn-appid-extension
    """

    appid: Optional[str] = None

    def to_dict(self):
        extensions = {}
        if self.appid:
            extensions["appid"] = self.appid
        return extensions


@dataclass
class GetRequest:
    """WebAuthn get request

    Args:
        origin: Origin where the WebAuthn get assertion takes place.
        rpid: Relying Party ID.
        challenge: <url-safe base64-encoded> raw challenge.
        timeout_ms: Timeout number in millisecond.
        allow_credentials: List of allowed credentials.
        user_verification: <'required'|'preferred'|'discouraged'> User verification requirement.
        extensions: WebAuthn authentication extensions inputs.
    """

    origin: str
    rpid: str
    challenge: str
    timeout_ms: Optional[int] = None
    allow_credentials: Optional[List[PublicKeyCredentialDescriptor]] = None
    user_verification: Optional[str] = None
    extensions: Optional[AuthenticationExtensionsClientInputs] = None

    def to_json(self) -> str:
        req_options: Dict[str, Any] = {"rpId": self.rpid, "challenge": self.challenge}
        if self.timeout_ms:
            req_options["timeout"] = self.timeout_ms
        if self.allow_credentials:
            req_options["allowCredentials"] = [
                c.to_dict() for c in self.allow_credentials
            ]
        if self.user_verification:
            req_options["userVerification"] = self.user_verification
        if self.extensions:
            req_options["extensions"] = self.extensions.to_dict()
        return json.dumps(
            {"type": "get", "origin": self.origin, "requestData": req_options}
        )


@dataclass(frozen=True)
class AuthenticatorAssertionResponse:
    """Authenticator response to a WebAuthn get (assertion) request.

    https://www.w3.org/TR/webauthn-3/#authenticatorassertionresponse

    Args:
        client_data_json: <url-safe base64-encoded> client data JSON.
        authenticator_data: <url-safe base64-encoded> authenticator data.
        signature: <url-safe base64-encoded> signature.
        user_handle: <url-safe base64-encoded> user handle.
    """

    client_data_json: str
    authenticator_data: str
    signature: str
    user_handle: Optional[str]


@dataclass(frozen=True)
class GetResponse:
    """WebAuthn get (assertion) response.

    Args:
        id: <url-safe base64-encoded> credential id (key handle).
        response: The authenticator assertion response.
        authenticator_attachment: <'cross-platform'|'platform'> The attachment status of the authenticator.
        client_extension_results: WebAuthn authentication extensions output results in a dictionary.
    """

    id: str
    response: AuthenticatorAssertionResponse
    authenticator_attachment: Optional[str]
    client_extension_results: Optional[Dict]

    @staticmethod
    def from_json(json_str: str):
        """Verify and construct GetResponse from a JSON string."""
        try:
            resp_json = json.loads(json_str)
        except ValueError:
            raise exceptions.MalformedError("Invalid Get JSON response")
        if resp_json.get("type") != "getResponse":
            raise exceptions.MalformedError(
                "Invalid Get response type: {}".format(resp_json.get("type"))
            )
        pk_cred = resp_json.get("responseData")
        if pk_cred is None:
            if resp_json.get("error"):
                raise exceptions.ReauthFailError(
                    "WebAuthn.get failure: {}".format(resp_json["error"])
                )
            else:
                raise exceptions.MalformedError("Get response is empty")
        if pk_cred.get("type") != "public-key":
            raise exceptions.MalformedError(
                "Invalid credential type: {}".format(pk_cred.get("type"))
            )
        assertion_json = pk_cred["response"]
        assertion_resp = AuthenticatorAssertionResponse(
            client_data_json=assertion_json["clientDataJSON"],
            authenticator_data=assertion_json["authenticatorData"],
            signature=assertion_json["signature"],
            user_handle=assertion_json.get("userHandle"),
        )
        return GetResponse(
            id=pk_cred["id"],
            response=assertion_resp,
            authenticator_attachment=pk_cred.get("authenticatorAttachment"),
            client_extension_results=pk_cred.get("clientExtensionResults"),
        )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\route_llm_request.py ===
from typing import TYPE_CHECKING, Any, Literal, Optional

from fastapi import HTTPException, status

import litellm

if TYPE_CHECKING:
    from litellm.router import Router as _Router

    LitellmRouter = _Router
else:
    LitellmRouter = Any


ROUTE_ENDPOINT_MAPPING = {
    "acompletion": "/chat/completions",
    "atext_completion": "/completions",
    "aembedding": "/embeddings",
    "aimage_generation": "/image/generations",
    "aspeech": "/audio/speech",
    "atranscription": "/audio/transcriptions",
    "amoderation": "/moderations",
    "arerank": "/rerank",
    "aresponses": "/responses",
    "alist_input_items": "/responses/{response_id}/input_items",
    "aimage_edit": "/images/edits",
}


class ProxyModelNotFoundError(HTTPException):
    def __init__(self, route: str, model_name: str):
        detail = {
            "error": f"{route}: Invalid model name passed in model={model_name}. Call `/v1/models` to view available models for your key."
        }
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def get_team_id_from_data(data: dict) -> Optional[str]:
    """
    Get the team id from the data's metadata or litellm_metadata params.
    """
    if (
        "metadata" in data
        and data["metadata"] is not None
        and "user_api_key_team_id" in data["metadata"]
    ):
        return data["metadata"].get("user_api_key_team_id")
    elif (
        "litellm_metadata" in data
        and data["litellm_metadata"] is not None
        and "user_api_key_team_id" in data["litellm_metadata"]
    ):
        return data["litellm_metadata"].get("user_api_key_team_id")
    return None


async def route_request(
    data: dict,
    llm_router: Optional[LitellmRouter],
    user_model: Optional[str],
    route_type: Literal[
        "acompletion",
        "atext_completion",
        "aembedding",
        "aimage_generation",
        "aspeech",
        "atranscription",
        "amoderation",
        "arerank",
        "aresponses",
        "aget_responses",
        "adelete_responses",
        "alist_input_items",
        "_arealtime",  # private function for realtime API
        "aimage_edit",
    ],
):
    """
    Common helper to route the request
    """
    team_id = get_team_id_from_data(data)
    router_model_names = llm_router.model_names if llm_router is not None else []
    if "api_key" in data or "api_base" in data:
        return getattr(llm_router, f"{route_type}")(**data)

    elif "user_config" in data:
        router_config = data.pop("user_config")
        user_router = litellm.Router(**router_config)
        ret_val = getattr(user_router, f"{route_type}")(**data)
        user_router.discard()
        return ret_val

    elif (
        route_type == "acompletion"
        and data.get("model", "") is not None
        and "," in data.get("model", "")
        and llm_router is not None
    ):
        if data.get("fastest_response", False):
            return llm_router.abatch_completion_fastest_response(**data)
        else:
            models = [model.strip() for model in data.pop("model").split(",")]
            return llm_router.abatch_completion(models=models, **data)
    elif llm_router is not None:
        team_model_name = (
            llm_router.map_team_model(data["model"], team_id)
            if team_id is not None
            else None
        )
        if team_model_name is not None:
            data["model"] = team_model_name
            return getattr(llm_router, f"{route_type}")(**data)

        elif (
            data["model"] in router_model_names
            or data["model"] in llm_router.get_model_ids()
        ):
            return getattr(llm_router, f"{route_type}")(**data)

        elif (
            llm_router.model_group_alias is not None
            and data["model"] in llm_router.model_group_alias
        ):
            return getattr(llm_router, f"{route_type}")(**data)

        elif data["model"] in llm_router.deployment_names:
            return getattr(llm_router, f"{route_type}")(
                **data, specific_deployment=True
            )

        elif data["model"] not in router_model_names:
            if llm_router.router_general_settings.pass_through_all_models:
                return getattr(litellm, f"{route_type}")(**data)
            elif (
                llm_router.default_deployment is not None
                or len(llm_router.pattern_router.patterns) > 0
            ):
                return getattr(llm_router, f"{route_type}")(**data)
            elif route_type in [
                "amoderation",
                "aget_responses",
                "adelete_responses",
                "alist_input_items",
            ]:
                # moderation endpoint does not require `model` parameter
                return getattr(llm_router, f"{route_type}")(**data)

    elif user_model is not None:
        return getattr(litellm, f"{route_type}")(**data)

    # if no route found then it's a bad request
    route_name = ROUTE_ENDPOINT_MAPPING.get(route_type, route_type)
    raise ProxyModelNotFoundError(
        route=route_name,
        model_name=data.get("model", ""),
    )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai\image_edit\transformation.py ===
from io import BufferedReader
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast

import httpx
from httpx._types import RequestFiles

import litellm
from litellm.images.utils import ImageEditRequestUtils
from litellm.llms.base_llm.image_edit.transformation import BaseImageEditConfig
from litellm.secret_managers.main import get_secret_str
from litellm.types.images.main import (
    ImageEditOptionalRequestParams,
    ImageEditRequestParams,
)
from litellm.types.llms.openai import FileTypes
from litellm.types.router import GenericLiteLLMParams
from litellm.utils import ImageResponse

from ..common_utils import OpenAIError

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class OpenAIImageEditConfig(BaseImageEditConfig):
    def get_supported_openai_params(self, model: str) -> list:
        """
        All OpenAI Image Edits params are supported
        """
        return [
            "image",
            "prompt",
            "background",
            "mask",
            "model",
            "n",
            "quality",
            "response_format",
            "size",
            "user",
            "extra_headers",
            "extra_query",
            "extra_body",
            "timeout",
        ]

    def map_openai_params(
        self,
        image_edit_optional_params: ImageEditOptionalRequestParams,
        model: str,
        drop_params: bool,
    ) -> Dict:
        """No mapping applied since inputs are in OpenAI spec already"""
        return dict(image_edit_optional_params)

    def transform_image_edit_request(
        self,
        model: str,
        prompt: str,
        image: FileTypes,
        image_edit_optional_request_params: Dict,
        litellm_params: GenericLiteLLMParams,
        headers: dict,
    ) -> Tuple[Dict, RequestFiles]:
        """
        No transform applied since inputs are in OpenAI spec already

        This handles buffered readers as images to be sent as multipart/form-data for OpenAI
        """
        request = ImageEditRequestParams(
            model=model,
            image=image,
            prompt=prompt,
            **image_edit_optional_request_params,
        )
        request_dict = cast(Dict, request)

        #########################################################
        # Separate images as `files` and send other parameters as `data`
        #########################################################
        _images = request_dict.get("image") or []
        data_without_images = {k: v for k, v in request_dict.items() if k != "image"}
        files_list: List[Tuple[str, Any]] = []
        for _image in _images:
            image_content_type: str = ImageEditRequestUtils.get_image_content_type(
                _image
            )
            if isinstance(_image, BufferedReader):
                files_list.append(
                    ("image[]", (_image.name, _image, image_content_type))
                )
            else:
                files_list.append(
                    ("image[]", ("image.png", _image, image_content_type))
                )
        return data_without_images, files_list

    def transform_image_edit_response(
        self,
        model: str,
        raw_response: httpx.Response,
        logging_obj: LiteLLMLoggingObj,
    ) -> ImageResponse:
        """No transform applied since outputs are in OpenAI spec already"""
        try:
            raw_response_json = raw_response.json()
        except Exception:
            raise OpenAIError(
                message=raw_response.text, status_code=raw_response.status_code
            )
        return ImageResponse(**raw_response_json)

    def validate_environment(
        self,
        headers: dict,
        model: str,
        api_key: Optional[str] = None,
    ) -> dict:
        api_key = (
            api_key
            or litellm.api_key
            or litellm.openai_key
            or get_secret_str("OPENAI_API_KEY")
        )
        headers.update(
            {
                "Authorization": f"Bearer {api_key}",
            }
        )
        return headers

    def get_complete_url(
        self,
        model: str,
        api_base: Optional[str],
        litellm_params: dict,
    ) -> str:
        """
        Get the endpoint for OpenAI responses API
        """
        api_base = (
            api_base
            or litellm.api_base
            or get_secret_str("OPENAI_BASE_URL")
            or get_secret_str("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )

        # Remove trailing slashes
        api_base = api_base.rstrip("/")

        return f"{api_base}/images/edits"

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\hooks\azure_content_safety.py ===
import traceback
from typing import Optional

from fastapi import HTTPException

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching.caching import DualCache
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy._types import UserAPIKeyAuth


class _PROXY_AzureContentSafety(
    CustomLogger
):  # https://docs.litellm.ai/docs/observability/custom_callback#callback-class
    # Class variables or attributes

    def __init__(self, endpoint, api_key, thresholds=None):
        try:
            from azure.ai.contentsafety.aio import ContentSafetyClient
            from azure.ai.contentsafety.models import (
                AnalyzeTextOptions,
                AnalyzeTextOutputType,
                TextCategory,
            )
            from azure.core.credentials import AzureKeyCredential
            from azure.core.exceptions import HttpResponseError
        except Exception as e:
            raise Exception(
                f"\033[91mAzure Content-Safety not installed, try running 'pip install azure-ai-contentsafety' to fix this error: {e}\n{traceback.format_exc()}\033[0m"
            )
        self.endpoint = endpoint
        self.api_key = api_key
        self.text_category = TextCategory
        self.analyze_text_options = AnalyzeTextOptions
        self.analyze_text_output_type = AnalyzeTextOutputType
        self.azure_http_error = HttpResponseError

        self.thresholds = self._configure_thresholds(thresholds)

        self.client = ContentSafetyClient(
            self.endpoint, AzureKeyCredential(self.api_key)
        )

    def _configure_thresholds(self, thresholds=None):
        default_thresholds = {
            self.text_category.HATE: 4,
            self.text_category.SELF_HARM: 4,
            self.text_category.SEXUAL: 4,
            self.text_category.VIOLENCE: 4,
        }

        if thresholds is None:
            return default_thresholds

        for key, default in default_thresholds.items():
            if key not in thresholds:
                thresholds[key] = default

        return thresholds

    def _compute_result(self, response):
        result = {}

        category_severity = {
            item.category: item.severity for item in response.categories_analysis
        }
        for category in self.text_category:
            severity = category_severity.get(category)
            if severity is not None:
                result[category] = {
                    "filtered": severity >= self.thresholds[category],
                    "severity": severity,
                }

        return result

    async def test_violation(self, content: str, source: Optional[str] = None):
        verbose_proxy_logger.debug("Testing Azure Content-Safety for: %s", content)

        # Construct a request
        request = self.analyze_text_options(
            text=content,
            output_type=self.analyze_text_output_type.EIGHT_SEVERITY_LEVELS,
        )

        # Analyze text
        try:
            response = await self.client.analyze_text(request)
        except self.azure_http_error:
            verbose_proxy_logger.debug(
                "Error in Azure Content-Safety: %s", traceback.format_exc()
            )
            verbose_proxy_logger.debug(traceback.format_exc())
            raise

        result = self._compute_result(response)
        verbose_proxy_logger.debug("Azure Content-Safety Result: %s", result)

        for key, value in result.items():
            if value["filtered"]:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Violated content safety policy",
                        "source": source,
                        "category": key,
                        "severity": value["severity"],
                    },
                )

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: str,  # "completion", "embeddings", "image_generation", "moderation"
    ):
        verbose_proxy_logger.debug("Inside Azure Content-Safety Pre-Call Hook")
        try:
            if call_type == "completion" and "messages" in data:
                for m in data["messages"]:
                    if "content" in m and isinstance(m["content"], str):
                        await self.test_violation(content=m["content"], source="input")

        except HTTPException as e:
            raise e
        except Exception as e:
            verbose_proxy_logger.error(
                "litellm.proxy.hooks.azure_content_safety.py::async_pre_call_hook(): Exception occured - {}".format(
                    str(e)
                )
            )
            verbose_proxy_logger.debug(traceback.format_exc())

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        response,
    ):
        verbose_proxy_logger.debug("Inside Azure Content-Safety Post-Call Hook")
        if isinstance(response, litellm.ModelResponse) and isinstance(
            response.choices[0], litellm.utils.Choices
        ):
            await self.test_violation(
                content=response.choices[0].message.content or "", source="output"
            )

    # async def async_post_call_streaming_hook(
    #    self,
    #    user_api_key_dict: UserAPIKeyAuth,
    #    response: str,
    # ):
    #    verbose_proxy_logger.debug("Inside Azure Content-Safety Call-Stream Hook")
    #    await self.test_violation(content=response, source="output")

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\scim\scim_transformations.py ===
from typing import List, Union

from litellm.proxy._types import (
    LiteLLM_TeamTable,
    LiteLLM_UserTable,
    Member,
    NewUserResponse,
)
from litellm.types.proxy.management_endpoints.scim_v2 import *


class ScimTransformations:
    DEFAULT_SCIM_NAME = "Unknown User"
    DEFAULT_SCIM_FAMILY_NAME = "Unknown Family Name"
    DEFAULT_SCIM_DISPLAY_NAME = "Unknown Display Name"
    DEFAULT_SCIM_MEMBER_VALUE = "Unknown Member Value"

    @staticmethod
    async def transform_litellm_user_to_scim_user(
        user: Union[LiteLLM_UserTable, NewUserResponse],
    ) -> SCIMUser:
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            raise HTTPException(
                status_code=500, detail={"error": "No database connected"}
            )

        # Get user's teams/groups
        groups = []
        for team_id in user.teams or []:
            team = await prisma_client.db.litellm_teamtable.find_unique(
                where={"team_id": team_id}
            )
            if team:
                team_alias = getattr(team, "team_alias", team.team_id)
                groups.append(SCIMUserGroup(value=team.team_id, display=team_alias))

        user_created_at = user.created_at.isoformat() if user.created_at else None
        user_updated_at = user.updated_at.isoformat() if user.updated_at else None

        emails = []
        if user.user_email:
            emails.append(SCIMUserEmail(value=user.user_email, primary=True))

        return SCIMUser(
            schemas=["urn:ietf:params:scim:schemas:core:2.0:User"],
            id=user.user_id,
            userName=ScimTransformations._get_scim_user_name(user),
            displayName=ScimTransformations._get_scim_user_name(user),
            name=SCIMUserName(
                familyName=ScimTransformations._get_scim_family_name(user),
                givenName=ScimTransformations._get_scim_given_name(user),
            ),
            emails=emails,
            groups=groups,
            active=True,
            meta={
                "resourceType": "User",
                "created": user_created_at,
                "lastModified": user_updated_at,
            },
        )

    @staticmethod
    def _get_scim_user_name(user: Union[LiteLLM_UserTable, NewUserResponse]) -> str:
        """
        SCIM requires a display name with length > 0

        We use the same userName and displayName for SCIM users
        """
        if user.user_email and len(user.user_email) > 0:
            return user.user_email
        return ScimTransformations.DEFAULT_SCIM_DISPLAY_NAME

    @staticmethod
    def _get_scim_family_name(user: Union[LiteLLM_UserTable, NewUserResponse]) -> str:
        """
        SCIM requires a family name with length > 0
        """
        metadata = user.metadata or {}
        if "scim_metadata" in metadata:
            scim_metadata: LiteLLM_UserScimMetadata = LiteLLM_UserScimMetadata(
                **metadata["scim_metadata"]
            )
            if scim_metadata.familyName and len(scim_metadata.familyName) > 0:
                return scim_metadata.familyName

        if user.user_alias and len(user.user_alias) > 0:
            return user.user_alias
        return ScimTransformations.DEFAULT_SCIM_FAMILY_NAME

    @staticmethod
    def _get_scim_given_name(user: Union[LiteLLM_UserTable, NewUserResponse]) -> str:
        """
        SCIM requires a given name with length > 0
        """
        metadata = user.metadata or {}
        if "scim_metadata" in metadata:
            scim_metadata: LiteLLM_UserScimMetadata = LiteLLM_UserScimMetadata(
                **metadata["scim_metadata"]
            )
            if scim_metadata.givenName and len(scim_metadata.givenName) > 0:
                return scim_metadata.givenName

        if user.user_alias and len(user.user_alias) > 0:
            return user.user_alias or ScimTransformations.DEFAULT_SCIM_NAME
        return ScimTransformations.DEFAULT_SCIM_NAME

    @staticmethod
    async def transform_litellm_team_to_scim_group(
        team: Union[LiteLLM_TeamTable, dict],
    ) -> SCIMGroup:
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            raise HTTPException(
                status_code=500, detail={"error": "No database connected"}
            )

        if isinstance(team, dict):
            team = LiteLLM_TeamTable(**team)

        # Get team members
        scim_members: List[SCIMMember] = []
        for member in team.members_with_roles or []:
            if isinstance(member, dict):
                member = Member(**member)
            scim_members.append(
                SCIMMember(
                    value=ScimTransformations._get_scim_member_value(member),
                    display=member.user_email,
                )
            )

        team_alias = getattr(team, "team_alias", team.team_id)
        team_created_at = team.created_at.isoformat() if team.created_at else None
        team_updated_at = team.updated_at.isoformat() if team.updated_at else None

        return SCIMGroup(
            schemas=["urn:ietf:params:scim:schemas:core:2.0:Group"],
            id=team.team_id,
            displayName=team_alias,
            members=scim_members,
            meta={
                "resourceType": "Group",
                "created": team_created_at,
                "lastModified": team_updated_at,
            },
        )

    @staticmethod
    def _get_scim_member_value(member: Member) -> str:
        if member.user_email:
            return member.user_email
        return ScimTransformations.DEFAULT_SCIM_MEMBER_VALUE

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\lm\test_vocabulary.py ===
# Natural Language Toolkit: Language Model Unit Tests
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import unittest
from collections import Counter
from timeit import timeit

from nltk.lm import Vocabulary


class NgramModelVocabularyTests(unittest.TestCase):
    """tests Vocabulary Class"""

    @classmethod
    def setUpClass(cls):
        cls.vocab = Vocabulary(
            ["z", "a", "b", "c", "f", "d", "e", "g", "a", "d", "b", "e", "w"],
            unk_cutoff=2,
        )

    def test_truthiness(self):
        self.assertTrue(self.vocab)

    def test_cutoff_value_set_correctly(self):
        self.assertEqual(self.vocab.cutoff, 2)

    def test_unable_to_change_cutoff(self):
        with self.assertRaises(AttributeError):
            self.vocab.cutoff = 3

    def test_cutoff_setter_checks_value(self):
        with self.assertRaises(ValueError) as exc_info:
            Vocabulary("abc", unk_cutoff=0)
        expected_error_msg = "Cutoff value cannot be less than 1. Got: 0"
        self.assertEqual(expected_error_msg, str(exc_info.exception))

    def test_counts_set_correctly(self):
        self.assertEqual(self.vocab.counts["a"], 2)
        self.assertEqual(self.vocab.counts["b"], 2)
        self.assertEqual(self.vocab.counts["c"], 1)

    def test_membership_check_respects_cutoff(self):
        # a was seen 2 times, so it should be considered part of the vocabulary
        self.assertTrue("a" in self.vocab)
        # "c" was seen once, it shouldn't be considered part of the vocab
        self.assertFalse("c" in self.vocab)
        # "z" was never seen at all, also shouldn't be considered in the vocab
        self.assertFalse("z" in self.vocab)

    def test_vocab_len_respects_cutoff(self):
        # Vocab size is the number of unique tokens that occur at least as often
        # as the cutoff value, plus 1 to account for unknown words.
        self.assertEqual(5, len(self.vocab))

    def test_vocab_iter_respects_cutoff(self):
        vocab_counts = ["a", "b", "c", "d", "e", "f", "g", "w", "z"]
        vocab_items = ["a", "b", "d", "e", "<UNK>"]

        self.assertCountEqual(vocab_counts, list(self.vocab.counts.keys()))
        self.assertCountEqual(vocab_items, list(self.vocab))

    def test_update_empty_vocab(self):
        empty = Vocabulary(unk_cutoff=2)
        self.assertEqual(len(empty), 0)
        self.assertFalse(empty)
        self.assertIn(empty.unk_label, empty)

        empty.update(list("abcde"))
        self.assertIn(empty.unk_label, empty)

    def test_lookup(self):
        self.assertEqual(self.vocab.lookup("a"), "a")
        self.assertEqual(self.vocab.lookup("c"), "<UNK>")

    def test_lookup_iterables(self):
        self.assertEqual(self.vocab.lookup(["a", "b"]), ("a", "b"))
        self.assertEqual(self.vocab.lookup(("a", "b")), ("a", "b"))
        self.assertEqual(self.vocab.lookup(("a", "c")), ("a", "<UNK>"))
        self.assertEqual(
            self.vocab.lookup(map(str, range(3))), ("<UNK>", "<UNK>", "<UNK>")
        )

    def test_lookup_empty_iterables(self):
        self.assertEqual(self.vocab.lookup(()), ())
        self.assertEqual(self.vocab.lookup([]), ())
        self.assertEqual(self.vocab.lookup(iter([])), ())
        self.assertEqual(self.vocab.lookup(n for n in range(0, 0)), ())

    def test_lookup_recursive(self):
        self.assertEqual(
            self.vocab.lookup([["a", "b"], ["a", "c"]]), (("a", "b"), ("a", "<UNK>"))
        )
        self.assertEqual(self.vocab.lookup([["a", "b"], "c"]), (("a", "b"), "<UNK>"))
        self.assertEqual(self.vocab.lookup([[[[["a", "b"]]]]]), ((((("a", "b"),),),),))

    def test_lookup_None(self):
        with self.assertRaises(TypeError):
            self.vocab.lookup(None)
        with self.assertRaises(TypeError):
            list(self.vocab.lookup([None, None]))

    def test_lookup_int(self):
        with self.assertRaises(TypeError):
            self.vocab.lookup(1)
        with self.assertRaises(TypeError):
            list(self.vocab.lookup([1, 2]))

    def test_lookup_empty_str(self):
        self.assertEqual(self.vocab.lookup(""), "<UNK>")

    def test_eqality(self):
        v1 = Vocabulary(["a", "b", "c"], unk_cutoff=1)
        v2 = Vocabulary(["a", "b", "c"], unk_cutoff=1)
        v3 = Vocabulary(["a", "b", "c"], unk_cutoff=1, unk_label="blah")
        v4 = Vocabulary(["a", "b"], unk_cutoff=1)

        self.assertEqual(v1, v2)
        self.assertNotEqual(v1, v3)
        self.assertNotEqual(v1, v4)

    def test_str(self):
        self.assertEqual(
            str(self.vocab), "<Vocabulary with cutoff=2 unk_label='<UNK>' and 5 items>"
        )

    def test_creation_with_counter(self):
        self.assertEqual(
            self.vocab,
            Vocabulary(
                Counter(
                    ["z", "a", "b", "c", "f", "d", "e", "g", "a", "d", "b", "e", "w"]
                ),
                unk_cutoff=2,
            ),
        )

    @unittest.skip(
        reason="Test is known to be flaky as it compares (runtime) performance."
    )
    def test_len_is_constant(self):
        # Given an obviously small and an obviously large vocabulary.
        small_vocab = Vocabulary("abcde")
        from nltk.corpus.europarl_raw import english

        large_vocab = Vocabulary(english.words())

        # If we time calling `len` on them.
        small_vocab_len_time = timeit("len(small_vocab)", globals=locals())
        large_vocab_len_time = timeit("len(large_vocab)", globals=locals())

        # The timing should be the same order of magnitude.
        self.assertAlmostEqual(small_vocab_len_time, large_vocab_len_time, places=1)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\input\win32_pipe.py ===
from __future__ import annotations

import sys

assert sys.platform == "win32"

from contextlib import contextmanager
from ctypes import windll
from ctypes.wintypes import HANDLE
from typing import Callable, ContextManager, Iterator

from prompt_toolkit.eventloop.win32 import create_win32_event

from ..key_binding import KeyPress
from ..utils import DummyContext
from .base import PipeInput
from .vt100_parser import Vt100Parser
from .win32 import _Win32InputBase, attach_win32_input, detach_win32_input

__all__ = ["Win32PipeInput"]


class Win32PipeInput(_Win32InputBase, PipeInput):
    """
    This is an input pipe that works on Windows.
    Text or bytes can be feed into the pipe, and key strokes can be read from
    the pipe. This is useful if we want to send the input programmatically into
    the application. Mostly useful for unit testing.

    Notice that even though it's Windows, we use vt100 escape sequences over
    the pipe.

    Usage::

        input = Win32PipeInput()
        input.send_text('inputdata')
    """

    _id = 0

    def __init__(self, _event: HANDLE) -> None:
        super().__init__()
        # Event (handle) for registering this input in the event loop.
        # This event is set when there is data available to read from the pipe.
        # Note: We use this approach instead of using a regular pipe, like
        #       returned from `os.pipe()`, because making such a regular pipe
        #       non-blocking is tricky and this works really well.
        self._event = create_win32_event()

        self._closed = False

        # Parser for incoming keys.
        self._buffer: list[KeyPress] = []  # Buffer to collect the Key objects.
        self.vt100_parser = Vt100Parser(lambda key: self._buffer.append(key))

        # Identifier for every PipeInput for the hash.
        self.__class__._id += 1
        self._id = self.__class__._id

    @classmethod
    @contextmanager
    def create(cls) -> Iterator[Win32PipeInput]:
        event = create_win32_event()
        try:
            yield Win32PipeInput(_event=event)
        finally:
            windll.kernel32.CloseHandle(event)

    @property
    def closed(self) -> bool:
        return self._closed

    def fileno(self) -> int:
        """
        The windows pipe doesn't depend on the file handle.
        """
        raise NotImplementedError

    @property
    def handle(self) -> HANDLE:
        "The handle used for registering this pipe in the event loop."
        return self._event

    def attach(self, input_ready_callback: Callable[[], None]) -> ContextManager[None]:
        """
        Return a context manager that makes this input active in the current
        event loop.
        """
        return attach_win32_input(self, input_ready_callback)

    def detach(self) -> ContextManager[None]:
        """
        Return a context manager that makes sure that this input is not active
        in the current event loop.
        """
        return detach_win32_input(self)

    def read_keys(self) -> list[KeyPress]:
        "Read list of KeyPress."

        # Return result.
        result = self._buffer
        self._buffer = []

        # Reset event.
        if not self._closed:
            # (If closed, the event should not reset.)
            windll.kernel32.ResetEvent(self._event)

        return result

    def flush_keys(self) -> list[KeyPress]:
        """
        Flush pending keys and return them.
        (Used for flushing the 'escape' key.)
        """
        # Flush all pending keys. (This is most important to flush the vt100
        # 'Escape' key early when nothing else follows.)
        self.vt100_parser.flush()

        # Return result.
        result = self._buffer
        self._buffer = []
        return result

    def send_bytes(self, data: bytes) -> None:
        "Send bytes to the input."
        self.send_text(data.decode("utf-8", "ignore"))

    def send_text(self, text: str) -> None:
        "Send text to the input."
        if self._closed:
            raise ValueError("Attempt to write into a closed pipe.")

        # Pass it through our vt100 parser.
        self.vt100_parser.feed(text)

        # Set event.
        windll.kernel32.SetEvent(self._event)

    def raw_mode(self) -> ContextManager[None]:
        return DummyContext()

    def cooked_mode(self) -> ContextManager[None]:
        return DummyContext()

    def close(self) -> None:
        "Close write-end of the pipe."
        self._closed = True
        windll.kernel32.SetEvent(self._event)

    def typeahead_hash(self) -> str:
        """
        This needs to be unique for every `PipeInput`.
        """
        return f"pipe-input-{self._id}"

# === NexusCore/openenv\Lib\site-packages\pygments\styles\nord.py ===
"""
    pygments.styles.nord
    ~~~~~~~~~~~~~~~~~~~~

    pygments version of the "nord" theme by Arctic Ice Studio
    https://www.nordtheme.com/

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, Number, \
    Operator, Generic, Whitespace, Punctuation, Text, Token


__all__ = ['NordStyle', 'NordDarkerStyle']


class NordStyle(Style):
    """
    Pygments version of the "nord" theme by Arctic Ice Studio.
    """
    name = 'nord'
    
    line_number_color = "#D8DEE9"
    line_number_background_color = "#242933"
    line_number_special_color = "#242933"
    line_number_special_background_color = "#D8DEE9"

    background_color = "#2E3440"
    highlight_color = "#3B4252"

    styles = {
        Token:                      "#d8dee9",

        Whitespace:                 '#d8dee9',
        Punctuation:                '#eceff4',

        Comment:                    'italic #616e87',
        Comment.Preproc:            '#5e81ac',

        Keyword:                    'bold #81a1c1',
        Keyword.Pseudo:             'nobold #81a1c1',
        Keyword.Type:               'nobold #81a1c1',

        Operator:                   'bold #81a1c1',
        Operator.Word:              'bold #81a1c1',

        Name:                       '#d8dee9',
        Name.Builtin:               '#81a1c1',
        Name.Function:              '#88c0d0',
        Name.Class:                 '#8fbcbb',
        Name.Namespace:             '#8fbcbb',
        Name.Exception:             '#bf616a',
        Name.Variable:              '#d8dee9',
        Name.Constant:              '#8fbcbb',
        Name.Entity:                '#d08770',
        Name.Attribute:             '#8fbcbb',
        Name.Tag:                   '#81a1c1',
        Name.Decorator:             '#d08770',

        String:                     '#a3be8c',
        String.Doc:                 '#616e87',
        String.Interpol:            '#a3be8c',
        String.Escape:              '#ebcb8b',
        String.Regex:               '#ebcb8b',
        String.Symbol:              '#a3be8c',
        String.Other:               '#a3be8c',

        Number:                     '#b48ead',

        Generic.Heading:            'bold #88c0d0',
        Generic.Subheading:         'bold #88c0d0',
        Generic.Deleted:            '#bf616a',
        Generic.Inserted:           '#a3be8c',
        Generic.Error:              '#bf616a',
        Generic.Emph:               'italic',
        Generic.Strong:             'bold',
        Generic.EmphStrong:         'bold italic',
        Generic.Prompt:             'bold #616e88',
        Generic.Output:             '#d8dee9',
        Generic.Traceback:          '#bf616a',

        Error:                      '#bf616a',
        Text:                       '#d8dee9',
    }


class NordDarkerStyle(Style):
    """
    Pygments version of a darker "nord" theme by Arctic Ice Studio
    """
    name = 'nord-darker'
    
    line_number_color = "#D8DEE9"
    line_number_background_color = "#242933"
    line_number_special_color = "#242933"
    line_number_special_background_color = "#D8DEE9"

    background_color = "#242933"
    highlight_color = "#3B4252"

    styles = {
        Token:                      "#d8dee9",

        Whitespace:                 '#d8dee9',
        Punctuation:                '#eceff4',

        Comment:                    'italic #616e87',
        Comment.Preproc:            '#5e81ac',

        Keyword:                    'bold #81a1c1',
        Keyword.Pseudo:             'nobold #81a1c1',
        Keyword.Type:               'nobold #81a1c1',

        Operator:                   'bold #81a1c1',
        Operator.Word:              'bold #81a1c1',

        Name:                       '#d8dee9',
        Name.Builtin:               '#81a1c1',
        Name.Function:              '#88c0d0',
        Name.Class:                 '#8fbcbb',
        Name.Namespace:             '#8fbcbb',
        Name.Exception:             '#bf616a',
        Name.Variable:              '#d8dee9',
        Name.Constant:              '#8fbcbb',
        Name.Entity:                '#d08770',
        Name.Attribute:             '#8fbcbb',
        Name.Tag:                   '#81a1c1',
        Name.Decorator:             '#d08770',

        String:                     '#a3be8c',
        String.Doc:                 '#616e87',
        String.Interpol:            '#a3be8c',
        String.Escape:              '#ebcb8b',
        String.Regex:               '#ebcb8b',
        String.Symbol:              '#a3be8c',
        String.Other:               '#a3be8c',

        Number:                     '#b48ead',

        Generic.Heading:            'bold #88c0d0',
        Generic.Subheading:         'bold #88c0d0',
        Generic.Deleted:            '#bf616a',
        Generic.Inserted:           '#a3be8c',
        Generic.Error:              '#bf616a',
        Generic.Emph:               'italic',
        Generic.Strong:             'bold',
        Generic.Prompt:             'bold #616e88',
        Generic.Output:             '#d8dee9',
        Generic.Traceback:          '#bf616a',

        Error:                      '#bf616a',
        Text:                       '#d8dee9',
    }

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\command\build.py ===
"""distutils.command.build

Implements the Distutils 'build' command."""

from __future__ import annotations

import os
import sys
import sysconfig
from collections.abc import Callable
from typing import ClassVar

from ..ccompiler import show_compilers
from ..core import Command
from ..errors import DistutilsOptionError
from ..util import get_platform


class build(Command):
    description = "build everything needed to install"

    user_options = [
        ('build-base=', 'b', "base directory for build library"),
        ('build-purelib=', None, "build directory for platform-neutral distributions"),
        ('build-platlib=', None, "build directory for platform-specific distributions"),
        (
            'build-lib=',
            None,
            "build directory for all distribution (defaults to either build-purelib or build-platlib",
        ),
        ('build-scripts=', None, "build directory for scripts"),
        ('build-temp=', 't', "temporary build directory"),
        (
            'plat-name=',
            'p',
            f"platform name to build for, if supported [default: {get_platform()}]",
        ),
        ('compiler=', 'c', "specify the compiler type"),
        ('parallel=', 'j', "number of parallel build jobs"),
        ('debug', 'g', "compile extensions and libraries with debugging information"),
        ('force', 'f', "forcibly build everything (ignore file timestamps)"),
        ('executable=', 'e', "specify final destination interpreter path (build.py)"),
    ]

    boolean_options: ClassVar[list[str]] = ['debug', 'force']

    help_options: ClassVar[list[tuple[str, str | None, str, Callable[[], object]]]] = [
        ('help-compiler', None, "list available compilers", show_compilers),
    ]

    def initialize_options(self):
        self.build_base = 'build'
        # these are decided only after 'build_base' has its final value
        # (unless overridden by the user or client)
        self.build_purelib = None
        self.build_platlib = None
        self.build_lib = None
        self.build_temp = None
        self.build_scripts = None
        self.compiler = None
        self.plat_name = None
        self.debug = None
        self.force = False
        self.executable = None
        self.parallel = None

    def finalize_options(self) -> None:  # noqa: C901
        if self.plat_name is None:
            self.plat_name = get_platform()
        else:
            # plat-name only supported for windows (other platforms are
            # supported via ./configure flags, if at all).  Avoid misleading
            # other platforms.
            if os.name != 'nt':
                raise DistutilsOptionError(
                    "--plat-name only supported on Windows (try "
                    "using './configure --help' on your platform)"
                )

        plat_specifier = f".{self.plat_name}-{sys.implementation.cache_tag}"

        # Python 3.13+ with --disable-gil shouldn't share build directories
        if sysconfig.get_config_var('Py_GIL_DISABLED'):
            plat_specifier += 't'

        # Make it so Python 2.x and Python 2.x with --with-pydebug don't
        # share the same build directories. Doing so confuses the build
        # process for C modules
        if hasattr(sys, 'gettotalrefcount'):
            plat_specifier += '-pydebug'

        # 'build_purelib' and 'build_platlib' just default to 'lib' and
        # 'lib.<plat>' under the base build directory.  We only use one of
        # them for a given distribution, though --
        if self.build_purelib is None:
            self.build_purelib = os.path.join(self.build_base, 'lib')
        if self.build_platlib is None:
            self.build_platlib = os.path.join(self.build_base, 'lib' + plat_specifier)

        # 'build_lib' is the actual directory that we will use for this
        # particular module distribution -- if user didn't supply it, pick
        # one of 'build_purelib' or 'build_platlib'.
        if self.build_lib is None:
            if self.distribution.has_ext_modules():
                self.build_lib = self.build_platlib
            else:
                self.build_lib = self.build_purelib

        # 'build_temp' -- temporary directory for compiler turds,
        # "build/temp.<plat>"
        if self.build_temp is None:
            self.build_temp = os.path.join(self.build_base, 'temp' + plat_specifier)
        if self.build_scripts is None:
            self.build_scripts = os.path.join(
                self.build_base,
                f'scripts-{sys.version_info.major}.{sys.version_info.minor}',
            )

        if self.executable is None and sys.executable:
            self.executable = os.path.normpath(sys.executable)

        if isinstance(self.parallel, str):
            try:
                self.parallel = int(self.parallel)
            except ValueError:
                raise DistutilsOptionError("parallel should be an integer")

    def run(self) -> None:
        # Run all relevant sub-commands.  This will be some subset of:
        #  - build_py      - pure Python modules
        #  - build_clib    - standalone C libraries
        #  - build_ext     - Python extensions
        #  - build_scripts - (Python) scripts
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)

    # -- Predicates for the sub-command list ---------------------------

    def has_pure_modules(self):
        return self.distribution.has_pure_modules()

    def has_c_libraries(self):
        return self.distribution.has_c_libraries()

    def has_ext_modules(self):
        return self.distribution.has_ext_modules()

    def has_scripts(self):
        return self.distribution.has_scripts()

    sub_commands = [
        ('build_py', has_pure_modules),
        ('build_clib', has_c_libraries),
        ('build_ext', has_ext_modules),
        ('build_scripts', has_scripts),
    ]

# === NexusCore/openenv\Lib\site-packages\starlette\middleware\wsgi.py ===
from __future__ import annotations

import io
import math
import sys
import typing
import warnings

import anyio
from anyio.abc import ObjectReceiveStream, ObjectSendStream

from starlette.types import Receive, Scope, Send

warnings.warn(
    "starlette.middleware.wsgi is deprecated and will be removed in a future release. "
    "Please refer to https://github.com/abersheeran/a2wsgi as a replacement.",
    DeprecationWarning,
)


def build_environ(scope: Scope, body: bytes) -> dict[str, typing.Any]:
    """
    Builds a scope and request body into a WSGI environ object.
    """

    script_name = scope.get("root_path", "").encode("utf8").decode("latin1")
    path_info = scope["path"].encode("utf8").decode("latin1")
    if path_info.startswith(script_name):
        path_info = path_info[len(script_name) :]

    environ = {
        "REQUEST_METHOD": scope["method"],
        "SCRIPT_NAME": script_name,
        "PATH_INFO": path_info,
        "QUERY_STRING": scope["query_string"].decode("ascii"),
        "SERVER_PROTOCOL": f"HTTP/{scope['http_version']}",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": scope.get("scheme", "http"),
        "wsgi.input": io.BytesIO(body),
        "wsgi.errors": sys.stdout,
        "wsgi.multithread": True,
        "wsgi.multiprocess": True,
        "wsgi.run_once": False,
    }

    # Get server name and port - required in WSGI, not in ASGI
    server = scope.get("server") or ("localhost", 80)
    environ["SERVER_NAME"] = server[0]
    environ["SERVER_PORT"] = server[1]

    # Get client IP address
    if scope.get("client"):
        environ["REMOTE_ADDR"] = scope["client"][0]

    # Go through headers and make them into environ entries
    for name, value in scope.get("headers", []):
        name = name.decode("latin1")
        if name == "content-length":
            corrected_name = "CONTENT_LENGTH"
        elif name == "content-type":
            corrected_name = "CONTENT_TYPE"
        else:
            corrected_name = f"HTTP_{name}".upper().replace("-", "_")
        # HTTPbis say only ASCII chars are allowed in headers, but we latin1 just in
        # case
        value = value.decode("latin1")
        if corrected_name in environ:
            value = environ[corrected_name] + "," + value
        environ[corrected_name] = value
    return environ


class WSGIMiddleware:
    def __init__(self, app: typing.Callable[..., typing.Any]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] == "http"
        responder = WSGIResponder(self.app, scope)
        await responder(receive, send)


class WSGIResponder:
    stream_send: ObjectSendStream[typing.MutableMapping[str, typing.Any]]
    stream_receive: ObjectReceiveStream[typing.MutableMapping[str, typing.Any]]

    def __init__(self, app: typing.Callable[..., typing.Any], scope: Scope) -> None:
        self.app = app
        self.scope = scope
        self.status = None
        self.response_headers = None
        self.stream_send, self.stream_receive = anyio.create_memory_object_stream(
            math.inf
        )
        self.response_started = False
        self.exc_info: typing.Any = None

    async def __call__(self, receive: Receive, send: Send) -> None:
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)
        environ = build_environ(self.scope, body)

        async with anyio.create_task_group() as task_group:
            task_group.start_soon(self.sender, send)
            async with self.stream_send:
                await anyio.to_thread.run_sync(self.wsgi, environ, self.start_response)
        if self.exc_info is not None:
            raise self.exc_info[0].with_traceback(self.exc_info[1], self.exc_info[2])

    async def sender(self, send: Send) -> None:
        async with self.stream_receive:
            async for message in self.stream_receive:
                await send(message)

    def start_response(
        self,
        status: str,
        response_headers: list[tuple[str, str]],
        exc_info: typing.Any = None,
    ) -> None:
        self.exc_info = exc_info
        if not self.response_started:
            self.response_started = True
            status_code_string, _ = status.split(" ", 1)
            status_code = int(status_code_string)
            headers = [
                (name.strip().encode("ascii").lower(), value.strip().encode("ascii"))
                for name, value in response_headers
            ]
            anyio.from_thread.run(
                self.stream_send.send,
                {
                    "type": "http.response.start",
                    "status": status_code,
                    "headers": headers,
                },
            )

    def wsgi(
        self,
        environ: dict[str, typing.Any],
        start_response: typing.Callable[..., typing.Any],
    ) -> None:
        for chunk in self.app(environ, start_response):
            anyio.from_thread.run(
                self.stream_send.send,
                {"type": "http.response.body", "body": chunk, "more_body": True},
            )

        anyio.from_thread.run(
            self.stream_send.send, {"type": "http.response.body", "body": b""}
        )

# === NexusCore/openenv\Lib\site-packages\tqdm\contrib\discord.py ===
"""
Sends updates to a Discord bot.

Usage:
>>> from tqdm.contrib.discord import tqdm, trange
>>> for i in trange(10, token='{token}', channel_id='{channel_id}'):
...     ...

![screenshot](https://tqdm.github.io/img/screenshot-discord.png)
"""
from os import getenv
from warnings import warn

from requests import Session
from requests.utils import default_user_agent

from ..auto import tqdm as tqdm_auto
from ..std import TqdmWarning
from ..version import __version__
from .utils_worker import MonoWorker

__author__ = {"github.com/": ["casperdcl", "guigoruiz1"]}
__all__ = ['DiscordIO', 'tqdm_discord', 'tdrange', 'tqdm', 'trange']


class DiscordIO(MonoWorker):
    """Non-blocking file-like IO using a Discord Bot."""
    API = "https://discord.com/api/v10"
    UA = f"tqdm (https://tqdm.github.io, {__version__}) {default_user_agent()}"

    def __init__(self, token, channel_id):
        """Creates a new message in the given `channel_id`."""
        super().__init__()
        self.token = token
        self.channel_id = channel_id
        self.session = Session()
        self.text = self.__class__.__name__
        self.message_id

    @property
    def message_id(self):
        if hasattr(self, '_message_id'):
            return self._message_id
        try:
            res = self.session.post(
                f'{self.API}/channels/{self.channel_id}/messages',
                headers={'Authorization': f'Bot {self.token}', 'User-Agent': self.UA},
                json={'content': f"`{self.text}`"}).json()
        except Exception as e:
            tqdm_auto.write(str(e))
        else:
            if res.get('error_code') == 429:
                warn("Creation rate limit: try increasing `mininterval`.",
                     TqdmWarning, stacklevel=2)
            else:
                self._message_id = res['id']
                return self._message_id

    def write(self, s):
        """Replaces internal `message_id`'s text with `s`."""
        if not s:
            s = "..."
        s = s.replace('\r', '').strip()
        if s == self.text:
            return  # avoid duplicate message Bot error
        message_id = self.message_id
        if message_id is None:
            return
        self.text = s
        try:
            future = self.submit(
                self.session.patch,
                f'{self.API}/channels/{self.channel_id}/messages/{message_id}',
                headers={'Authorization': f'Bot {self.token}', 'User-Agent': self.UA},
                json={'content': f"`{self.text}`"})
        except Exception as e:
            tqdm_auto.write(str(e))
        else:
            return future

    def delete(self):
        """Deletes internal `message_id`."""
        try:
            future = self.submit(
                self.session.delete,
                f'{self.API}/channels/{self.channel_id}/messages/{self.message_id}',
                headers={'Authorization': f'Bot {self.token}', 'User-Agent': self.UA})
        except Exception as e:
            tqdm_auto.write(str(e))
        else:
            return future


class tqdm_discord(tqdm_auto):
    """
    Standard `tqdm.auto.tqdm` but also sends updates to a Discord Bot.
    May take a few seconds to create (`__init__`).

    - create a discord bot (not public, no requirement of OAuth2 code
      grant, only send message permissions) & invite it to a channel:
      <https://discordpy.readthedocs.io/en/latest/discord.html>
    - copy the bot `{token}` & `{channel_id}` and paste below

    >>> from tqdm.contrib.discord import tqdm, trange
    >>> for i in tqdm(iterable, token='{token}', channel_id='{channel_id}'):
    ...     ...
    """
    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        token  : str, required. Discord bot token
            [default: ${TQDM_DISCORD_TOKEN}].
        channel_id  : int, required. Discord channel ID
            [default: ${TQDM_DISCORD_CHANNEL_ID}].

        See `tqdm.auto.tqdm.__init__` for other parameters.
        """
        if not kwargs.get('disable'):
            kwargs = kwargs.copy()
            self.dio = DiscordIO(
                kwargs.pop('token', getenv('TQDM_DISCORD_TOKEN')),
                kwargs.pop('channel_id', getenv('TQDM_DISCORD_CHANNEL_ID')))
        super().__init__(*args, **kwargs)

    def display(self, **kwargs):
        super().display(**kwargs)
        fmt = self.format_dict
        if fmt.get('bar_format', None):
            fmt['bar_format'] = fmt['bar_format'].replace(
                '<bar/>', '{bar:10u}').replace('{bar}', '{bar:10u}')
        else:
            fmt['bar_format'] = '{l_bar}{bar:10u}{r_bar}'
        self.dio.write(self.format_meter(**fmt))

    def clear(self, *args, **kwargs):
        super().clear(*args, **kwargs)
        if not self.disable:
            self.dio.write("")

    def close(self):
        if self.disable:
            return
        super().close()
        if not (self.leave or (self.leave is None and self.pos == 0)):
            self.dio.delete()


def tdrange(*args, **kwargs):
    """Shortcut for `tqdm.contrib.discord.tqdm(range(*args), **kwargs)`."""
    return tqdm_discord(range(*args), **kwargs)


# Aliases
tqdm = tqdm_discord
trange = tdrange

# === NexusCore/openenv\Lib\site-packages\win32\scripts\VersionStamp\bulkstamp.py ===
#
# bulkstamp.py:
#    Stamp versions on all files that can be found in a given tree.
#
# USAGE: python bulkstamp.py <version> <root directory> <descriptions>
#
# Example: python bulkstamp.py 103 ..\win32\Build\ desc.txt
#
# <version> corresponds to the build number. It will be concatenated with
# the major and minor version numbers found in the description file.
#
# Description information is pulled from an input text file with lines of
# the form:
#
#    <basename> <white space> <description>
#
# For example:
#
#    PyWinTypes.dll Common types for Python on Win32
#    etc
#
# The product's name, major, and minor versions are specified as:
#
#    name <white space> <value>
#    major <white space> <value>
#    minor <white space> <value>
#
# The tags are case-sensitive.
#
# Any line beginning with "#" will be ignored. Empty lines are okay.
#

import fnmatch
import os
import sys
from collections.abc import Mapping
from optparse import Values

try:
    import win32verstamp
except ModuleNotFoundError:
    # If run with pywin32 not already installed
    sys.path.append(os.path.abspath(__file__ + "/../../../Lib"))
    import win32verstamp

g_patterns = [
    "*.dll",
    "*.pyd",
    "*.exe",
    "*.ocx",
]


def walk(vars: Mapping[str, str], debug, descriptions, dirname, names) -> int:
    """Returns the number of stamped files."""
    numStamped = 0
    for name in names:
        for pat in g_patterns:
            if fnmatch.fnmatch(name, pat):
                # Handle the "_d" thing.
                pathname = os.path.join(dirname, name)
                base, ext = os.path.splitext(name)
                if base.endswith("_d"):
                    name = base[:-2] + ext
                is_dll = ext.lower() != ".exe"
                if os.path.normcase(name) in descriptions:
                    description = descriptions[os.path.normcase(name)]
                    try:
                        options = Values(
                            {**vars, "description": description, "dll": is_dll}
                        )
                        win32verstamp.stamp(pathname, options)
                        numStamped += 1
                    except OSError as exc:
                        print(
                            "Could not stamp",
                            pathname,
                            "Error",
                            exc.winerror,
                            "-",
                            exc.strerror,
                        )
                else:
                    print("WARNING: description not provided for:", name)
                    # skip branding this - assume already branded or handled elsewhere
    return numStamped


# print("Stamped", pathname)


def load_descriptions(fname, vars):
    retvars: dict[str, str] = {}
    descriptions = {}

    lines = open(fname, "r").readlines()

    for i in range(len(lines)):
        line = lines[i].strip()
        if line != "" and line[0] != "#":
            idx1 = line.find(" ")
            idx2 = line.find("\t")
            if idx1 == -1 or idx2 < idx1:
                idx1 = idx2
            if idx1 == -1:
                print("ERROR: bad syntax in description file at line %d." % (i + 1))
                sys.exit(1)

            key = line[:idx1]
            val = line[idx1:].strip()
            if key in vars:
                retvars[key] = val
            else:
                descriptions[key] = val

    if "product" not in retvars:
        print("ERROR: description file is missing the product name.")
        sys.exit(1)
    if "major" not in retvars:
        print("ERROR: description file is missing the major version number.")
        sys.exit(1)
    if "minor" not in retvars:
        print("ERROR: description file is missing the minor version number.")
        sys.exit(1)

    return retvars, descriptions


def scan(build, root: str, desc, **custom_vars):
    try:
        build = int(build)
    except ValueError:
        print("ERROR: build number is not a number: %s" % build)
        sys.exit(1)

    debug = 0  ### maybe fix this one day

    varList = ["major", "minor", "sub", "company", "copyright", "trademarks", "product"]

    vars, descriptions = load_descriptions(desc, varList)
    vars["build"] = build
    vars.update(custom_vars)

    numStamped = 0
    for directory, dirnames, filenames in os.walk(root):
        numStamped += walk(vars, debug, descriptions, directory, filenames)

    print(f"Stamped {numStamped} files.")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("ERROR: incorrect invocation. See script's header comments.")
        sys.exit(1)

    scan(*sys.argv[1:])

# === NexusCore/main_cli.py ===
# ==============================================================================
# フォルダ: (プロジェクトルート)
# ファイル名: main_cli.py
# メモ: 【品質ゲート対応版】Orchestratorに渡す「憲法(constitution)」に、
#      テストカバレッジやPylintスコアの最低基準値を設定するロジックを追加。
# ==============================================================================
import sys
import os
import argparse
import logging

# ------------------------------------------------------------------------------
# パス設定
# ------------------------------------------------------------------------------
# このスクリプトがプロジェクトのどこから実行されても、
# `src`フォルダ内のモジュールを正しく見つけられるようにするための設定。
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ------------------------------------------------------------------------------
# 必要なモジュールとエージェントのインポート
# ------------------------------------------------------------------------------
from src.core.orchestrator import Orchestrator
from src.agents.architect_agent import ArchitectAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.coder_agent import CoderAgent
from src.agents.tester_agent import TesterAgent
from src.agents.debugger_agent import DebuggerAgent
from src.agents.guardian_agent import GuardianAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.postmortem_agent import PostmortemAgent
from src.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from src.utils.config import config

def setup_logging(verbose: bool):
    """ロギングの基本設定"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("nexus_core_run.log", mode='w', encoding='utf-8')
        ]
    )
    logging.info(f"Log level set to {logging.getLevelName(log_level)}")

def main():
    """
    コマンドラインからタスクを受け取り、Orchestratorを実行するメイン関数。
    """
    # --- 1. コマンドライン引数の定義 ---
    parser = argparse.ArgumentParser(
        description="NexusCore - AI Multi-Agent Development System",
        formatter_class=argparse.RawTextHelpFormatter # ヘルプの改行を維持
    )
    
    parser.add_argument(
        "requirement",
        type=str,
        help="作成したいアプリケーションや機能の自然言語による説明。\n例: \"簡単なCRMアプリを作成して。ユーザーを追加、表示できること\""
    )
    parser.add_argument(
        "--project-path",
        type=str,
        required=True,
        help="開発プロジェクトが作成される、あるいは対象となるディレクトリのパス。"
    )
    parser.add_argument(
        "--constitution-text",
        type=str,
        default="このプロジェクトのコードは、常にクリーンで読みやすく、保守性が高いこと。また、すべてのコードには型ヒントとdocstringが付与されている必要がある。",
        help="AIチーム全体が従うべきプロジェクトの原則（自然言語）。"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="詳細なデバッグログをコンソールに出力します。"
    )

    args = parser.parse_args()

    # --- 2. ロギングと設定の初期化 ---
    setup_logging(args.verbose)
    
    project_path = os.path.abspath(args.project_path)
    os.makedirs(project_path, exist_ok=True)

    logging.info(f"Project Path: {project_path}")
    logging.info(f"User Requirement: {args.requirement}")
    logging.info(f"Constitution Text: {args.constitution_text}")

    # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
    # プロジェクト憲法を構造化データとして定義します。
    # これにより、品質ゲートのような具体的なルールをシステムに組み込めます。
    constitution = {
        "description": args.constitution_text,
        "quality_gate": {
            "MIN_COVERAGE": 90,       # テストカバレッジの最低基準値 (%)
            "MIN_PYLINT_SCORE": 8.0   # Pylintスコアの最低基準値 (/10)
        }
    }
    logging.info(f"Full Constitution with Quality Gate: {constitution}")
    # --- ★★★★★ ここまで ★★★★★ ---

    try:
        # --- 3. AI開発チーム（エージェント群）の招集 ---
        logging.info("Initializing AI agent team...")
        
        # .envファイルからモデル名とAPIキーを取得
        model_name = "gemini-1.5-pro-latest" 
        api_key = config.GEMINI_API_KEY_AGENT_A 
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY_AGENT_A is not set in the .env file.")

        architect = ArchitectAgent(api_key=api_key, model=model_name)
        planner = PlannerAgent(api_key=api_key, model=model_name)
        coder = CoderAgent(api_key=api_key, model=model_name)
        tester = TesterAgent(api_key=api_key, model=model_name)
        debugger = DebuggerAgent(api_key=api_key, model=model_name, knowledge_base_path="fkb_local.json", project_path=project_path)
        guardian = GuardianAgent(api_key=api_key, model=model_name)
        policy_agent = PolicyAgent(api_key=api_key, model=model_name, policy_rules_path="config/policy_rules.json")
        postmortem_agent = PostmortemAgent(api_key=api_key, model=model_name)
        knowledge_curator_agent = KnowledgeCuratorAgent(api_key=api_key, model=model_name)

        # --- 4. 司令塔 (Orchestrator) の任命 ---
        logging.info("Initializing Orchestrator...")
        orchestrator = Orchestrator(
            project_path=project_path,
            constitution=constitution,  # ★ 構造化された憲法を渡す
            architect=architect,
            planner=planner,
            coder=coder,
            tester=tester,
            debugger=debugger,
            guardian=guardian,
            policy_agent=policy_agent,
            postmortem_agent=postmortem_agent,
            knowledge_curator_agent=knowledge_curator_agent
        )

        # --- 5. 開発プロセスの開始 ---
        logging.info("Starting development process...")
        orchestrator.design_phase(args.requirement)
        orchestrator.development_cycle(args.requirement)
        logging.info("Development process finished successfully.")

    except Exception as e:
        logging.critical(f"An unexpected error occurred in the main CLI: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\packages\backports\weakref_finalize.py ===
# -*- coding: utf-8 -*-
"""
backports.weakref_finalize
~~~~~~~~~~~~~~~~~~

Backports the Python 3 ``weakref.finalize`` method.
"""
from __future__ import absolute_import

import itertools
import sys
from weakref import ref

__all__ = ["weakref_finalize"]


class weakref_finalize(object):
    """Class for finalization of weakrefable objects
    finalize(obj, func, *args, **kwargs) returns a callable finalizer
    object which will be called when obj is garbage collected. The
    first time the finalizer is called it evaluates func(*arg, **kwargs)
    and returns the result. After this the finalizer is dead, and
    calling it just returns None.
    When the program exits any remaining finalizers for which the
    atexit attribute is true will be run in reverse order of creation.
    By default atexit is true.
    """

    # Finalizer objects don't have any state of their own.  They are
    # just used as keys to lookup _Info objects in the registry.  This
    # ensures that they cannot be part of a ref-cycle.

    __slots__ = ()
    _registry = {}
    _shutdown = False
    _index_iter = itertools.count()
    _dirty = False
    _registered_with_atexit = False

    class _Info(object):
        __slots__ = ("weakref", "func", "args", "kwargs", "atexit", "index")

    def __init__(self, obj, func, *args, **kwargs):
        if not self._registered_with_atexit:
            # We may register the exit function more than once because
            # of a thread race, but that is harmless
            import atexit

            atexit.register(self._exitfunc)
            weakref_finalize._registered_with_atexit = True
        info = self._Info()
        info.weakref = ref(obj, self)
        info.func = func
        info.args = args
        info.kwargs = kwargs or None
        info.atexit = True
        info.index = next(self._index_iter)
        self._registry[self] = info
        weakref_finalize._dirty = True

    def __call__(self, _=None):
        """If alive then mark as dead and return func(*args, **kwargs);
        otherwise return None"""
        info = self._registry.pop(self, None)
        if info and not self._shutdown:
            return info.func(*info.args, **(info.kwargs or {}))

    def detach(self):
        """If alive then mark as dead and return (obj, func, args, kwargs);
        otherwise return None"""
        info = self._registry.get(self)
        obj = info and info.weakref()
        if obj is not None and self._registry.pop(self, None):
            return (obj, info.func, info.args, info.kwargs or {})

    def peek(self):
        """If alive then return (obj, func, args, kwargs);
        otherwise return None"""
        info = self._registry.get(self)
        obj = info and info.weakref()
        if obj is not None:
            return (obj, info.func, info.args, info.kwargs or {})

    @property
    def alive(self):
        """Whether finalizer is alive"""
        return self in self._registry

    @property
    def atexit(self):
        """Whether finalizer should be called at exit"""
        info = self._registry.get(self)
        return bool(info) and info.atexit

    @atexit.setter
    def atexit(self, value):
        info = self._registry.get(self)
        if info:
            info.atexit = bool(value)

    def __repr__(self):
        info = self._registry.get(self)
        obj = info and info.weakref()
        if obj is None:
            return "<%s object at %#x; dead>" % (type(self).__name__, id(self))
        else:
            return "<%s object at %#x; for %r at %#x>" % (
                type(self).__name__,
                id(self),
                type(obj).__name__,
                id(obj),
            )

    @classmethod
    def _select_for_exit(cls):
        # Return live finalizers marked for exit, oldest first
        L = [(f, i) for (f, i) in cls._registry.items() if i.atexit]
        L.sort(key=lambda item: item[1].index)
        return [f for (f, i) in L]

    @classmethod
    def _exitfunc(cls):
        # At shutdown invoke finalizers for which atexit is true.
        # This is called once all other non-daemonic threads have been
        # joined.
        reenable_gc = False
        try:
            if cls._registry:
                import gc

                if gc.isenabled():
                    reenable_gc = True
                    gc.disable()
                pending = None
                while True:
                    if pending is None or weakref_finalize._dirty:
                        pending = cls._select_for_exit()
                        weakref_finalize._dirty = False
                    if not pending:
                        break
                    f = pending.pop()
                    try:
                        # gc is disabled, so (assuming no daemonic
                        # threads) the following is the only line in
                        # this function which might trigger creation
                        # of a new finalizer
                        f()
                    except Exception:
                        sys.excepthook(*sys.exc_info())
                    assert f not in cls._registry
        finally:
            # prevent any more finalizers from executing during shutdown
            weakref_finalize._shutdown = True
            if reenable_gc:
                gc.enable()

# === NexusCore/openenv\Lib\site-packages\setuptools\installer.py ===
from __future__ import annotations

import glob
import itertools
import os
import subprocess
import sys
import tempfile

import packaging.requirements
import packaging.utils

from . import _reqs
from ._importlib import metadata
from .warnings import SetuptoolsDeprecationWarning
from .wheel import Wheel

from distutils import log
from distutils.errors import DistutilsError


def _fixup_find_links(find_links):
    """Ensure find-links option end-up being a list of strings."""
    if isinstance(find_links, str):
        return find_links.split()
    assert isinstance(find_links, (tuple, list))
    return find_links


def fetch_build_egg(dist, req):
    """Fetch an egg needed for building.

    Use pip/wheel to fetch/build a wheel."""
    _DeprecatedInstaller.emit()
    _warn_wheel_not_available(dist)
    return _fetch_build_egg_no_warn(dist, req)


def _present(req):
    return any(_dist_matches_req(dist, req) for dist in metadata.distributions())


def _fetch_build_eggs(dist, requires: _reqs._StrOrIter) -> list[metadata.Distribution]:
    _DeprecatedInstaller.emit(stacklevel=3)
    _warn_wheel_not_available(dist)

    parsed_reqs = _reqs.parse(requires)

    missing_reqs = itertools.filterfalse(_present, parsed_reqs)

    needed_reqs = (
        req for req in missing_reqs if not req.marker or req.marker.evaluate()
    )
    resolved_dists = [_fetch_build_egg_no_warn(dist, req) for req in needed_reqs]
    for dist in resolved_dists:
        # dist.locate_file('') is the directory containing EGG-INFO, where the importabl
        # contents can be found.
        sys.path.insert(0, str(dist.locate_file('')))
    return resolved_dists


def _dist_matches_req(egg_dist, req):
    return (
        packaging.utils.canonicalize_name(egg_dist.name)
        == packaging.utils.canonicalize_name(req.name)
        and egg_dist.version in req.specifier
    )


def _fetch_build_egg_no_warn(dist, req):  # noqa: C901  # is too complex (16)  # FIXME
    # Ignore environment markers; if supplied, it is required.
    req = strip_marker(req)
    # Take easy_install options into account, but do not override relevant
    # pip environment variables (like PIP_INDEX_URL or PIP_QUIET); they'll
    # take precedence.
    opts = dist.get_option_dict('easy_install')
    if 'allow_hosts' in opts:
        raise DistutilsError(
            'the `allow-hosts` option is not supported '
            'when using pip to install requirements.'
        )
    quiet = 'PIP_QUIET' not in os.environ and 'PIP_VERBOSE' not in os.environ
    if 'PIP_INDEX_URL' in os.environ:
        index_url = None
    elif 'index_url' in opts:
        index_url = opts['index_url'][1]
    else:
        index_url = None
    find_links = (
        _fixup_find_links(opts['find_links'][1])[:] if 'find_links' in opts else []
    )
    if dist.dependency_links:
        find_links.extend(dist.dependency_links)
    eggs_dir = os.path.realpath(dist.get_egg_cache_dir())
    cached_dists = metadata.Distribution.discover(path=glob.glob(f'{eggs_dir}/*.egg'))
    for egg_dist in cached_dists:
        if _dist_matches_req(egg_dist, req):
            return egg_dist
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            sys.executable,
            '-m',
            'pip',
            '--disable-pip-version-check',
            'wheel',
            '--no-deps',
            '-w',
            tmpdir,
        ]
        if quiet:
            cmd.append('--quiet')
        if index_url is not None:
            cmd.extend(('--index-url', index_url))
        for link in find_links or []:
            cmd.extend(('--find-links', link))
        # If requirement is a PEP 508 direct URL, directly pass
        # the URL to pip, as `req @ url` does not work on the
        # command line.
        cmd.append(req.url or str(req))
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as e:
            raise DistutilsError(str(e)) from e
        wheel = Wheel(glob.glob(os.path.join(tmpdir, '*.whl'))[0])
        dist_location = os.path.join(eggs_dir, wheel.egg_name())
        wheel.install_as_egg(dist_location)
        return metadata.Distribution.at(dist_location + '/EGG-INFO')


def strip_marker(req):
    """
    Return a new requirement without the environment marker to avoid
    calling pip with something like `babel; extra == "i18n"`, which
    would always be ignored.
    """
    # create a copy to avoid mutating the input
    req = packaging.requirements.Requirement(str(req))
    req.marker = None
    return req


def _warn_wheel_not_available(dist):
    try:
        metadata.distribution('wheel')
    except metadata.PackageNotFoundError:
        dist.announce('WARNING: The wheel package is not available.', log.WARN)


class _DeprecatedInstaller(SetuptoolsDeprecationWarning):
    _SUMMARY = "setuptools.installer and fetch_build_eggs are deprecated."
    _DETAILS = """
    Requirements should be satisfied by a PEP 517 installer.
    If you are using pip, you can try `pip install --use-pep517`.
    """
    _DUE_DATE = 2025, 10, 31

# === NexusCore/openenv\Lib\site-packages\starlette\authentication.py ===
from __future__ import annotations

import functools
import inspect
import sys
import typing
from urllib.parse import urlencode

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

from starlette._utils import is_async_callable
from starlette.exceptions import HTTPException
from starlette.requests import HTTPConnection, Request
from starlette.responses import RedirectResponse
from starlette.websockets import WebSocket

_P = ParamSpec("_P")


def has_required_scope(conn: HTTPConnection, scopes: typing.Sequence[str]) -> bool:
    for scope in scopes:
        if scope not in conn.auth.scopes:
            return False
    return True


def requires(
    scopes: str | typing.Sequence[str],
    status_code: int = 403,
    redirect: str | None = None,
) -> typing.Callable[
    [typing.Callable[_P, typing.Any]], typing.Callable[_P, typing.Any]
]:
    scopes_list = [scopes] if isinstance(scopes, str) else list(scopes)

    def decorator(
        func: typing.Callable[_P, typing.Any],
    ) -> typing.Callable[_P, typing.Any]:
        sig = inspect.signature(func)
        for idx, parameter in enumerate(sig.parameters.values()):
            if parameter.name == "request" or parameter.name == "websocket":
                type_ = parameter.name
                break
        else:
            raise Exception(
                f'No "request" or "websocket" argument on function "{func}"'
            )

        if type_ == "websocket":
            # Handle websocket functions. (Always async)
            @functools.wraps(func)
            async def websocket_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> None:
                websocket = kwargs.get(
                    "websocket", args[idx] if idx < len(args) else None
                )
                assert isinstance(websocket, WebSocket)

                if not has_required_scope(websocket, scopes_list):
                    await websocket.close()
                else:
                    await func(*args, **kwargs)

            return websocket_wrapper

        elif is_async_callable(func):
            # Handle async request/response functions.
            @functools.wraps(func)
            async def async_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> typing.Any:
                request = kwargs.get("request", args[idx] if idx < len(args) else None)
                assert isinstance(request, Request)

                if not has_required_scope(request, scopes_list):
                    if redirect is not None:
                        orig_request_qparam = urlencode({"next": str(request.url)})
                        next_url = f"{request.url_for(redirect)}?{orig_request_qparam}"
                        return RedirectResponse(url=next_url, status_code=303)
                    raise HTTPException(status_code=status_code)
                return await func(*args, **kwargs)

            return async_wrapper

        else:
            # Handle sync request/response functions.
            @functools.wraps(func)
            def sync_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> typing.Any:
                request = kwargs.get("request", args[idx] if idx < len(args) else None)
                assert isinstance(request, Request)

                if not has_required_scope(request, scopes_list):
                    if redirect is not None:
                        orig_request_qparam = urlencode({"next": str(request.url)})
                        next_url = f"{request.url_for(redirect)}?{orig_request_qparam}"
                        return RedirectResponse(url=next_url, status_code=303)
                    raise HTTPException(status_code=status_code)
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


class AuthenticationError(Exception):
    pass


class AuthenticationBackend:
    async def authenticate(
        self, conn: HTTPConnection
    ) -> tuple[AuthCredentials, BaseUser] | None:
        raise NotImplementedError()  # pragma: no cover


class AuthCredentials:
    def __init__(self, scopes: typing.Sequence[str] | None = None):
        self.scopes = [] if scopes is None else list(scopes)


class BaseUser:
    @property
    def is_authenticated(self) -> bool:
        raise NotImplementedError()  # pragma: no cover

    @property
    def display_name(self) -> str:
        raise NotImplementedError()  # pragma: no cover

    @property
    def identity(self) -> str:
        raise NotImplementedError()  # pragma: no cover


class SimpleUser(BaseUser):
    def __init__(self, username: str) -> None:
        self.username = username

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.username


class UnauthenticatedUser(BaseUser):
    @property
    def is_authenticated(self) -> bool:
        return False

    @property
    def display_name(self) -> str:
        return ""

# === NexusCore/openenv\Lib\site-packages\git\refs\tag.py ===
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

"""Provides a :class:`~git.refs.reference.Reference`-based type for lightweight tags.

This defines the :class:`TagReference` class (and its alias :class:`Tag`), which
represents lightweight tags. For annotated tags (which are git objects), see the
:mod:`git.objects.tag` module.
"""

__all__ = ["TagReference", "Tag"]

from .reference import Reference

# typing ------------------------------------------------------------------

from typing import Any, TYPE_CHECKING, Type, Union

from git.types import AnyGitObject, PathLike

if TYPE_CHECKING:
    from git.objects import Commit, TagObject
    from git.refs import SymbolicReference
    from git.repo import Repo

# ------------------------------------------------------------------------------


class TagReference(Reference):
    """A lightweight tag reference which either points to a commit, a tag object or any
    other object. In the latter case additional information, like the signature or the
    tag-creator, is available.

    This tag object will always point to a commit object, but may carry additional
    information in a tag object::

     tagref = TagReference.list_items(repo)[0]
     print(tagref.commit.message)
     if tagref.tag is not None:
        print(tagref.tag.message)
    """

    __slots__ = ()

    _common_default = "tags"
    _common_path_default = Reference._common_path_default + "/" + _common_default

    @property
    def commit(self) -> "Commit":  # type: ignore[override]  # LazyMixin has unrelated commit method
        """:return: Commit object the tag ref points to

        :raise ValueError:
            If the tag points to a tree or blob.
        """
        obj = self.object
        while obj.type != "commit":
            if obj.type == "tag":
                # It is a tag object which carries the commit as an object - we can point to anything.
                obj = obj.object
            else:
                raise ValueError(
                    (
                        "Cannot resolve commit as tag %s points to a %s object - "
                        + "use the `.object` property instead to access it"
                    )
                    % (self, obj.type)
                )
        return obj

    @property
    def tag(self) -> Union["TagObject", None]:
        """
        :return:
            Tag object this tag ref points to, or ``None`` in case we are a lightweight
            tag
        """
        obj = self.object
        if obj.type == "tag":
            return obj
        return None

    # Make object read-only. It should be reasonably hard to adjust an existing tag.
    @property
    def object(self) -> AnyGitObject:  # type: ignore[override]
        return Reference._get_object(self)

    @classmethod
    def create(
        cls: Type["TagReference"],
        repo: "Repo",
        path: PathLike,
        reference: Union[str, "SymbolicReference"] = "HEAD",
        logmsg: Union[str, None] = None,
        force: bool = False,
        **kwargs: Any,
    ) -> "TagReference":
        """Create a new tag reference.

        :param repo:
            The :class:`~git.repo.base.Repo` to create the tag in.

        :param path:
            The name of the tag, e.g. ``1.0`` or ``releases/1.0``.
            The prefix ``refs/tags`` is implied.

        :param reference:
            A reference to the :class:`~git.objects.base.Object` you want to tag.
            The referenced object can be a commit, tree, or blob.

        :param logmsg:
            If not ``None``, the message will be used in your tag object. This will also
            create an additional tag object that allows to obtain that information,
            e.g.::

                tagref.tag.message

        :param message:
            Synonym for the `logmsg` parameter. Included for backwards compatibility.
            `logmsg` takes precedence if both are passed.

        :param force:
            If ``True``, force creation of a tag even though that tag already exists.

        :param kwargs:
            Additional keyword arguments to be passed to :manpage:`git-tag(1)`.

        :return:
            A new :class:`TagReference`.
        """
        if "ref" in kwargs and kwargs["ref"]:
            reference = kwargs["ref"]

        if "message" in kwargs and kwargs["message"]:
            kwargs["m"] = kwargs["message"]
            del kwargs["message"]

        if logmsg:
            kwargs["m"] = logmsg

        if force:
            kwargs["f"] = True

        args = (path, reference)

        repo.git.tag(*args, **kwargs)
        return TagReference(repo, "%s/%s" % (cls._common_path_default, path))

    @classmethod
    def delete(cls, repo: "Repo", *tags: "TagReference") -> None:  # type: ignore[override]
        """Delete the given existing tag or tags."""
        repo.git.tag("-d", *tags)


# Provide an alias.
Tag = TagReference

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\__init__.py ===
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
from google.ai.generativelanguage_v1beta3 import gapic_version as package_version

__version__ = package_version.__version__


from .services.discuss_service import DiscussServiceAsyncClient, DiscussServiceClient
from .services.model_service import ModelServiceAsyncClient, ModelServiceClient
from .services.permission_service import (
    PermissionServiceAsyncClient,
    PermissionServiceClient,
)
from .services.text_service import TextServiceAsyncClient, TextServiceClient
from .types.citation import CitationMetadata, CitationSource
from .types.discuss_service import (
    CountMessageTokensRequest,
    CountMessageTokensResponse,
    Example,
    GenerateMessageRequest,
    GenerateMessageResponse,
    Message,
    MessagePrompt,
)
from .types.model import Model
from .types.model_service import (
    CreateTunedModelMetadata,
    CreateTunedModelRequest,
    DeleteTunedModelRequest,
    GetModelRequest,
    GetTunedModelRequest,
    ListModelsRequest,
    ListModelsResponse,
    ListTunedModelsRequest,
    ListTunedModelsResponse,
    UpdateTunedModelRequest,
)
from .types.permission import Permission
from .types.permission_service import (
    CreatePermissionRequest,
    DeletePermissionRequest,
    GetPermissionRequest,
    ListPermissionsRequest,
    ListPermissionsResponse,
    TransferOwnershipRequest,
    TransferOwnershipResponse,
    UpdatePermissionRequest,
)
from .types.safety import (
    ContentFilter,
    HarmCategory,
    SafetyFeedback,
    SafetyRating,
    SafetySetting,
)
from .types.text_service import (
    BatchEmbedTextRequest,
    BatchEmbedTextResponse,
    CountTextTokensRequest,
    CountTextTokensResponse,
    Embedding,
    EmbedTextRequest,
    EmbedTextResponse,
    GenerateTextRequest,
    GenerateTextResponse,
    TextCompletion,
    TextPrompt,
)
from .types.tuned_model import (
    Dataset,
    Hyperparameters,
    TunedModel,
    TunedModelSource,
    TuningExample,
    TuningExamples,
    TuningSnapshot,
    TuningTask,
)

__all__ = (
    "DiscussServiceAsyncClient",
    "ModelServiceAsyncClient",
    "PermissionServiceAsyncClient",
    "TextServiceAsyncClient",
    "BatchEmbedTextRequest",
    "BatchEmbedTextResponse",
    "CitationMetadata",
    "CitationSource",
    "ContentFilter",
    "CountMessageTokensRequest",
    "CountMessageTokensResponse",
    "CountTextTokensRequest",
    "CountTextTokensResponse",
    "CreatePermissionRequest",
    "CreateTunedModelMetadata",
    "CreateTunedModelRequest",
    "Dataset",
    "DeletePermissionRequest",
    "DeleteTunedModelRequest",
    "DiscussServiceClient",
    "EmbedTextRequest",
    "EmbedTextResponse",
    "Embedding",
    "Example",
    "GenerateMessageRequest",
    "GenerateMessageResponse",
    "GenerateTextRequest",
    "GenerateTextResponse",
    "GetModelRequest",
    "GetPermissionRequest",
    "GetTunedModelRequest",
    "HarmCategory",
    "Hyperparameters",
    "ListModelsRequest",
    "ListModelsResponse",
    "ListPermissionsRequest",
    "ListPermissionsResponse",
    "ListTunedModelsRequest",
    "ListTunedModelsResponse",
    "Message",
    "MessagePrompt",
    "Model",
    "ModelServiceClient",
    "Permission",
    "PermissionServiceClient",
    "SafetyFeedback",
    "SafetyRating",
    "SafetySetting",
    "TextCompletion",
    "TextPrompt",
    "TextServiceClient",
    "TransferOwnershipRequest",
    "TransferOwnershipResponse",
    "TunedModel",
    "TunedModelSource",
    "TuningExample",
    "TuningExamples",
    "TuningSnapshot",
    "TuningTask",
    "UpdatePermissionRequest",
    "UpdateTunedModelRequest",
)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\services\model_service\pagers.py ===
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
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
)

from google.ai.generativelanguage_v1.types import model, model_service


class ListModelsPager:
    """A pager for iterating through ``list_models`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1.types.ListModelsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``models`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListModels`` requests and continue to iterate
    through the ``models`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1.types.ListModelsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., model_service.ListModelsResponse],
        request: model_service.ListModelsRequest,
        response: model_service.ListModelsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1.types.ListModelsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1.types.ListModelsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = model_service.ListModelsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[model_service.ListModelsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[model.Model]:
        for page in self.pages:
            yield from page.models

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListModelsAsyncPager:
    """A pager for iterating through ``list_models`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1.types.ListModelsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``models`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListModels`` requests and continue to iterate
    through the ``models`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1.types.ListModelsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[model_service.ListModelsResponse]],
        request: model_service.ListModelsRequest,
        response: model_service.ListModelsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1.types.ListModelsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1.types.ListModelsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = model_service.ListModelsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[model_service.ListModelsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[model.Model]:
        async def async_generator():
            async for page in self.pages:
                for response in page.models:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\cache_service\pagers.py ===
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
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
)

from google.ai.generativelanguage_v1beta.types import cache_service, cached_content


class ListCachedContentsPager:
    """A pager for iterating through ``list_cached_contents`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListCachedContentsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``cached_contents`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListCachedContents`` requests and continue to iterate
    through the ``cached_contents`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListCachedContentsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., cache_service.ListCachedContentsResponse],
        request: cache_service.ListCachedContentsRequest,
        response: cache_service.ListCachedContentsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListCachedContentsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListCachedContentsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = cache_service.ListCachedContentsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[cache_service.ListCachedContentsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[cached_content.CachedContent]:
        for page in self.pages:
            yield from page.cached_contents

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListCachedContentsAsyncPager:
    """A pager for iterating through ``list_cached_contents`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListCachedContentsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``cached_contents`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListCachedContents`` requests and continue to iterate
    through the ``cached_contents`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListCachedContentsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[cache_service.ListCachedContentsResponse]],
        request: cache_service.ListCachedContentsRequest,
        response: cache_service.ListCachedContentsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListCachedContentsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListCachedContentsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = cache_service.ListCachedContentsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[cache_service.ListCachedContentsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[cached_content.CachedContent]:
        async def async_generator():
            async for page in self.pages:
                for response in page.cached_contents:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\file_service\pagers.py ===
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
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
)

from google.ai.generativelanguage_v1beta.types import file, file_service


class ListFilesPager:
    """A pager for iterating through ``list_files`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListFilesResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``files`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListFiles`` requests and continue to iterate
    through the ``files`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListFilesResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., file_service.ListFilesResponse],
        request: file_service.ListFilesRequest,
        response: file_service.ListFilesResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListFilesRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListFilesResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = file_service.ListFilesRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[file_service.ListFilesResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[file.File]:
        for page in self.pages:
            yield from page.files

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListFilesAsyncPager:
    """A pager for iterating through ``list_files`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListFilesResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``files`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListFiles`` requests and continue to iterate
    through the ``files`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListFilesResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[file_service.ListFilesResponse]],
        request: file_service.ListFilesRequest,
        response: file_service.ListFilesResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListFilesRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListFilesResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = file_service.ListFilesRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[file_service.ListFilesResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[file.File]:
        async def async_generator():
            async for page in self.pages:
                for response in page.files:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\permission_service\pagers.py ===
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
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
)

from google.ai.generativelanguage_v1beta.types import permission, permission_service


class ListPermissionsPager:
    """A pager for iterating through ``list_permissions`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListPermissionsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``permissions`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListPermissions`` requests and continue to iterate
    through the ``permissions`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListPermissionsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., permission_service.ListPermissionsResponse],
        request: permission_service.ListPermissionsRequest,
        response: permission_service.ListPermissionsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListPermissionsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListPermissionsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = permission_service.ListPermissionsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[permission_service.ListPermissionsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[permission.Permission]:
        for page in self.pages:
            yield from page.permissions

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListPermissionsAsyncPager:
    """A pager for iterating through ``list_permissions`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListPermissionsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``permissions`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListPermissions`` requests and continue to iterate
    through the ``permissions`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListPermissionsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[permission_service.ListPermissionsResponse]],
        request: permission_service.ListPermissionsRequest,
        response: permission_service.ListPermissionsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListPermissionsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListPermissionsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = permission_service.ListPermissionsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[permission_service.ListPermissionsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[permission.Permission]:
        async def async_generator():
            async for page in self.pages:
                for response in page.permissions:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\types\model.py ===
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
from __future__ import annotations

from typing import MutableMapping, MutableSequence

import proto  # type: ignore

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta2",
    manifest={
        "Model",
    },
)


class Model(proto.Message):
    r"""Information about a Generative Language Model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        name (str):
            Required. The resource name of the ``Model``.

            Format: ``models/{model}`` with a ``{model}`` naming
            convention of:

            -  "{base_model_id}-{version}"

            Examples:

            -  ``models/chat-bison-001``
        base_model_id (str):
            Required. The name of the base model, pass this to the
            generation request.

            Examples:

            -  ``chat-bison``
        version (str):
            Required. The version number of the model.

            This represents the major version
        display_name (str):
            The human-readable name of the model. E.g.
            "Chat Bison".
            The name can be up to 128 characters long and
            can consist of any UTF-8 characters.
        description (str):
            A short description of the model.
        input_token_limit (int):
            Maximum number of input tokens allowed for
            this model.
        output_token_limit (int):
            Maximum number of output tokens available for
            this model.
        supported_generation_methods (MutableSequence[str]):
            The model's supported generation methods.

            The method names are defined as Pascal case strings, such as
            ``generateMessage`` which correspond to API methods.
        temperature (float):
            Controls the randomness of the output.

            Values can range over ``[0.0,1.0]``, inclusive. A value
            closer to ``1.0`` will produce responses that are more
            varied, while a value closer to ``0.0`` will typically
            result in less surprising responses from the model. This
            value specifies default to be used by the backend while
            making the call to the model.

            This field is a member of `oneof`_ ``_temperature``.
        top_p (float):
            For Nucleus sampling.

            Nucleus sampling considers the smallest set of tokens whose
            probability sum is at least ``top_p``. This value specifies
            default to be used by the backend while making the call to
            the model.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            For Top-k sampling.

            Top-k sampling considers the set of ``top_k`` most probable
            tokens. This value specifies default to be used by the
            backend while making the call to the model.

            This field is a member of `oneof`_ ``_top_k``.
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    base_model_id: str = proto.Field(
        proto.STRING,
        number=2,
    )
    version: str = proto.Field(
        proto.STRING,
        number=3,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=4,
    )
    description: str = proto.Field(
        proto.STRING,
        number=5,
    )
    input_token_limit: int = proto.Field(
        proto.INT32,
        number=6,
    )
    output_token_limit: int = proto.Field(
        proto.INT32,
        number=7,
    )
    supported_generation_methods: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=8,
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=9,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=10,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=11,
        optional=True,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\model_service\pagers.py ===
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
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
)

from google.ai.generativelanguage_v1beta2.types import model, model_service


class ListModelsPager:
    """A pager for iterating through ``list_models`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta2.types.ListModelsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``models`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListModels`` requests and continue to iterate
    through the ``models`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta2.types.ListModelsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., model_service.ListModelsResponse],
        request: model_service.ListModelsRequest,
        response: model_service.ListModelsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta2.types.ListModelsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta2.types.ListModelsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = model_service.ListModelsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[model_service.ListModelsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[model.Model]:
        for page in self.pages:
            yield from page.models

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListModelsAsyncPager:
    """A pager for iterating through ``list_models`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta2.types.ListModelsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``models`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListModels`` requests and continue to iterate
    through the ``models`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta2.types.ListModelsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[model_service.ListModelsResponse]],
        request: model_service.ListModelsRequest,
        response: model_service.ListModelsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta2.types.ListModelsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta2.types.ListModelsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = model_service.ListModelsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[model_service.ListModelsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[model.Model]:
        async def async_generator():
            async for page in self.pages:
                for response in page.models:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\types\model.py ===
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
from __future__ import annotations

from typing import MutableMapping, MutableSequence

import proto  # type: ignore

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta3",
    manifest={
        "Model",
    },
)


class Model(proto.Message):
    r"""Information about a Generative Language Model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        name (str):
            Required. The resource name of the ``Model``.

            Format: ``models/{model}`` with a ``{model}`` naming
            convention of:

            -  "{base_model_id}-{version}"

            Examples:

            -  ``models/chat-bison-001``
        base_model_id (str):
            Required. The name of the base model, pass this to the
            generation request.

            Examples:

            -  ``chat-bison``
        version (str):
            Required. The version number of the model.

            This represents the major version
        display_name (str):
            The human-readable name of the model. E.g.
            "Chat Bison".
            The name can be up to 128 characters long and
            can consist of any UTF-8 characters.
        description (str):
            A short description of the model.
        input_token_limit (int):
            Maximum number of input tokens allowed for
            this model.
        output_token_limit (int):
            Maximum number of output tokens available for
            this model.
        supported_generation_methods (MutableSequence[str]):
            The model's supported generation methods.

            The method names are defined as Pascal case strings, such as
            ``generateMessage`` which correspond to API methods.
        temperature (float):
            Controls the randomness of the output.

            Values can range over ``[0.0,1.0]``, inclusive. A value
            closer to ``1.0`` will produce responses that are more
            varied, while a value closer to ``0.0`` will typically
            result in less surprising responses from the model. This
            value specifies default to be used by the backend while
            making the call to the model.

            This field is a member of `oneof`_ ``_temperature``.
        top_p (float):
            For Nucleus sampling.

            Nucleus sampling considers the smallest set of tokens whose
            probability sum is at least ``top_p``. This value specifies
            default to be used by the backend while making the call to
            the model.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            For Top-k sampling.

            Top-k sampling considers the set of ``top_k`` most probable
            tokens. This value specifies default to be used by the
            backend while making the call to the model.

            This field is a member of `oneof`_ ``_top_k``.
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    base_model_id: str = proto.Field(
        proto.STRING,
        number=2,
    )
    version: str = proto.Field(
        proto.STRING,
        number=3,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=4,
    )
    description: str = proto.Field(
        proto.STRING,
        number=5,
    )
    input_token_limit: int = proto.Field(
        proto.INT32,
        number=6,
    )
    output_token_limit: int = proto.Field(
        proto.INT32,
        number=7,
    )
    supported_generation_methods: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=8,
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=9,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=10,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=11,
        optional=True,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\permission_service\pagers.py ===
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
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
)

from google.ai.generativelanguage_v1beta3.types import permission, permission_service


class ListPermissionsPager:
    """A pager for iterating through ``list_permissions`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta3.types.ListPermissionsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``permissions`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListPermissions`` requests and continue to iterate
    through the ``permissions`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta3.types.ListPermissionsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., permission_service.ListPermissionsResponse],
        request: permission_service.ListPermissionsRequest,
        response: permission_service.ListPermissionsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta3.types.ListPermissionsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta3.types.ListPermissionsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = permission_service.ListPermissionsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[permission_service.ListPermissionsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[permission.Permission]:
        for page in self.pages:
            yield from page.permissions

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListPermissionsAsyncPager:
    """A pager for iterating through ``list_permissions`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta3.types.ListPermissionsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``permissions`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListPermissions`` requests and continue to iterate
    through the ``permissions`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta3.types.ListPermissionsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[permission_service.ListPermissionsResponse]],
        request: permission_service.ListPermissionsRequest,
        response: permission_service.ListPermissionsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta3.types.ListPermissionsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta3.types.ListPermissionsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = permission_service.ListPermissionsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[permission_service.ListPermissionsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[permission.Permission]:
        async def async_generator():
            async for page in self.pages:
                for response in page.permissions:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)

# === NexusCore/openenv\Lib\site-packages\IPython\core\async_helpers.py ===
"""
Async helper function that are invalid syntax on Python 3.5 and below.

This code is best effort, and may have edge cases not behaving as expected. In
particular it contain a number of heuristics to detect whether code is
effectively async and need to run in an event loop or not.

Some constructs (like top-level `return`, or `yield`) are taken care of
explicitly to actually raise a SyntaxError and stay as close as possible to
Python semantics.
"""

import ast
import asyncio
import inspect
from functools import wraps

_asyncio_event_loop = None


def get_asyncio_loop():
    """asyncio has deprecated get_event_loop

    Replicate it here, with our desired semantics:

    - always returns a valid, not-closed loop
    - not thread-local like asyncio's,
      because we only want one loop for IPython
    - if called from inside a coroutine (e.g. in ipykernel),
      return the running loop

    .. versionadded:: 8.0
    """
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        # not inside a coroutine,
        # track our own global
        pass

    # not thread-local like asyncio's,
    # because we only track one event loop to run for IPython itself,
    # always in the main thread.
    global _asyncio_event_loop
    if _asyncio_event_loop is None or _asyncio_event_loop.is_closed():
        _asyncio_event_loop = asyncio.new_event_loop()
    return _asyncio_event_loop


class _AsyncIORunner:
    def __call__(self, coro):
        """
        Handler for asyncio autoawait
        """
        return get_asyncio_loop().run_until_complete(coro)

    def __str__(self):
        return "asyncio"


_asyncio_runner = _AsyncIORunner()


class _AsyncIOProxy:
    """Proxy-object for an asyncio

    Any coroutine methods will be wrapped in event_loop.run_
    """

    def __init__(self, obj, event_loop):
        self._obj = obj
        self._event_loop = event_loop

    def __repr__(self):
        return f"<_AsyncIOProxy({self._obj!r})>"

    def __getattr__(self, key):
        attr = getattr(self._obj, key)
        if inspect.iscoroutinefunction(attr):
            # if it's a coroutine method,
            # return a threadsafe wrapper onto the _current_ asyncio loop
            @wraps(attr)
            def _wrapped(*args, **kwargs):
                concurrent_future = asyncio.run_coroutine_threadsafe(
                    attr(*args, **kwargs), self._event_loop
                )
                return asyncio.wrap_future(concurrent_future)

            return _wrapped
        else:
            return attr

    def __dir__(self):
        return dir(self._obj)


def _curio_runner(coroutine):
    """
    handler for curio autoawait
    """
    import curio

    return curio.run(coroutine)


def _trio_runner(async_fn):
    import trio

    async def loc(coro):
        """
        We need the dummy no-op async def to protect from
        trio's internal. See https://github.com/python-trio/trio/issues/89
        """
        return await coro

    return trio.run(loc, async_fn)


def _pseudo_sync_runner(coro):
    """
    A runner that does not really allow async execution, and just advance the coroutine.

    See discussion in https://github.com/python-trio/trio/issues/608,

    Credit to Nathaniel Smith
    """
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    else:
        # TODO: do not raise but return an execution result with the right info.
        raise RuntimeError(
            "{coro_name!r} needs a real async loop".format(coro_name=coro.__name__)
        )


def _should_be_async(cell: str) -> bool:
    """Detect if a block of code need to be wrapped in an `async def`

    Attempt to parse the block of code, it it compile we're fine.
    Otherwise we  wrap if and try to compile.

    If it works, assume it should be async. Otherwise Return False.

    Not handled yet: If the block of code has a return statement as the top
    level, it will be seen as async. This is a know limitation.
    """
    try:
        code = compile(
            cell, "<>", "exec", flags=getattr(ast, "PyCF_ALLOW_TOP_LEVEL_AWAIT", 0x0)
        )
        return inspect.CO_COROUTINE & code.co_flags == inspect.CO_COROUTINE
    except (SyntaxError, MemoryError):
        return False

# === NexusCore/openenv\Lib\site-packages\IPython\sphinxext\custom_doctests.py ===
"""
Handlers for IPythonDirective's @doctest pseudo-decorator.

The Sphinx extension that provides support for embedded IPython code provides
a pseudo-decorator @doctest, which treats the input/output block as a
doctest, raising a RuntimeError during doc generation if the actual output
(after running the input) does not match the expected output.

An example usage is:

.. code-block:: rst

   .. ipython::

        In [1]: x = 1

        @doctest
        In [2]: x + 2
        Out[3]: 3

One can also provide arguments to the decorator. The first argument should be
the name of a custom handler. The specification of any other arguments is
determined by the handler. For example,

.. code-block:: rst

      .. ipython::

         @doctest float
         In [154]: 0.1 + 0.2
         Out[154]: 0.3

allows the actual output ``0.30000000000000004`` to match the expected output
due to a comparison with `np.allclose`.

This module contains handlers for the @doctest pseudo-decorator. Handlers
should have the following function signature::

    handler(sphinx_shell, args, input_lines, found, submitted)

where `sphinx_shell` is the embedded Sphinx shell, `args` contains the list
of arguments that follow: '@doctest handler_name', `input_lines` contains
a list of the lines relevant to the current doctest, `found` is a string
containing the output from the IPython shell, and `submitted` is a string
containing the expected output from the IPython shell.

Handlers must be registered in the `doctests` dict at the end of this module.

"""

def str_to_array(s):
    """
    Simplistic converter of strings from repr to float NumPy arrays.

    If the repr representation has ellipsis in it, then this will fail.

    Parameters
    ----------
    s : str
        The repr version of a NumPy array.

    Examples
    --------
    >>> s = "array([ 0.3,  inf,  nan])"
    >>> a = str_to_array(s)

    """
    import numpy as np

    # Need to make sure eval() knows about inf and nan.
    # This also assumes default printoptions for NumPy.
    from numpy import inf, nan

    if s.startswith(u'array'):
        # Remove array( and )
        s = s[6:-1]

    if s.startswith(u'['):
        a = np.array(eval(s), dtype=float)
    else:
        # Assume its a regular float. Force 1D so we can index into it.
        a = np.atleast_1d(float(s))
    return a

def float_doctest(sphinx_shell, args, input_lines, found, submitted):
    """
    Doctest which allow the submitted output to vary slightly from the input.

    Here is how it might appear in an rst file:

    .. code-block:: rst

       .. ipython::

          @doctest float
          In [1]: 0.1 + 0.2
          Out[1]: 0.3

    """
    import numpy as np

    if len(args) == 2:
        rtol = 1e-05
        atol = 1e-08
    else:
        # Both must be specified if any are specified.
        try:
            rtol = float(args[2])
            atol = float(args[3])
        except IndexError:
            e = ("Both `rtol` and `atol` must be specified "
                 "if either are specified: {0}".format(args))
            raise IndexError(e) from e

    try:
        submitted = str_to_array(submitted)
        found = str_to_array(found)
    except:
        # For example, if the array is huge and there are ellipsis in it.
        error = True
    else:
        found_isnan = np.isnan(found)
        submitted_isnan = np.isnan(submitted)
        error = not np.allclose(found_isnan, submitted_isnan)
        error |= not np.allclose(found[~found_isnan],
                                 submitted[~submitted_isnan],
                                 rtol=rtol, atol=atol)

    TAB = ' ' * 4
    directive = sphinx_shell.directive
    if directive is None:
        source = 'Unavailable'
        content = 'Unavailable'
    else:
        source = directive.state.document.current_source
        # Add tabs and make into a single string.
        content = '\n'.join([TAB + line for line in directive.content])

    if error:

        e = ('doctest float comparison failure\n\n'
             'Document source: {0}\n\n'
             'Raw content: \n{1}\n\n'
             'On input line(s):\n{TAB}{2}\n\n'
             'we found output:\n{TAB}{3}\n\n'
             'instead of the expected:\n{TAB}{4}\n\n')
        e = e.format(source, content, '\n'.join(input_lines), repr(found),
                     repr(submitted), TAB=TAB)
        raise RuntimeError(e)

# dict of allowable doctest handlers. The key represents the first argument
# that must be given to @doctest in order to activate the handler.
doctests = {
    'float': float_doctest,
}

# === NexusCore/openenv\Lib\site-packages\jedi\api\file_name.py ===
import os

from jedi.api import classes
from jedi.api.strings import StringName, get_quote_ending
from jedi.api.helpers import match
from jedi.inference.helpers import get_str_or_none


class PathName(StringName):
    api_type = 'path'


def complete_file_name(inference_state, module_context, start_leaf, quote, string,
                       like_name, signatures_callback, code_lines, position, fuzzy):
    # First we want to find out what can actually be changed as a name.
    like_name_length = len(os.path.basename(string))

    addition = _get_string_additions(module_context, start_leaf)
    if string.startswith('~'):
        string = os.path.expanduser(string)
    if addition is None:
        return
    string = addition + string

    # Here we use basename again, because if strings are added like
    # `'foo' + 'bar`, it should complete to `foobar/`.
    must_start_with = os.path.basename(string)
    string = os.path.dirname(string)

    sigs = signatures_callback(*position)
    is_in_os_path_join = sigs and all(s.full_name == 'os.path.join' for s in sigs)
    if is_in_os_path_join:
        to_be_added = _add_os_path_join(module_context, start_leaf, sigs[0].bracket_start)
        if to_be_added is None:
            is_in_os_path_join = False
        else:
            string = to_be_added + string
    base_path = os.path.join(inference_state.project.path, string)
    try:
        listed = sorted(os.scandir(base_path), key=lambda e: e.name)
        # OSError: [Errno 36] File name too long: '...'
    except (FileNotFoundError, OSError):
        return
    quote_ending = get_quote_ending(quote, code_lines, position)
    for entry in listed:
        name = entry.name
        if match(name, must_start_with, fuzzy=fuzzy):
            if is_in_os_path_join or not entry.is_dir():
                name += quote_ending
            else:
                name += os.path.sep

            yield classes.Completion(
                inference_state,
                PathName(inference_state, name[len(must_start_with) - like_name_length:]),
                stack=None,
                like_name_length=like_name_length,
                is_fuzzy=fuzzy,
            )


def _get_string_additions(module_context, start_leaf):
    def iterate_nodes():
        node = addition.parent
        was_addition = True
        for child_node in reversed(node.children[:node.children.index(addition)]):
            if was_addition:
                was_addition = False
                yield child_node
                continue

            if child_node != '+':
                break
            was_addition = True

    addition = start_leaf.get_previous_leaf()
    if addition != '+':
        return ''
    context = module_context.create_context(start_leaf)
    return _add_strings(context, reversed(list(iterate_nodes())))


def _add_strings(context, nodes, add_slash=False):
    string = ''
    first = True
    for child_node in nodes:
        values = context.infer_node(child_node)
        if len(values) != 1:
            return None
        c, = values
        s = get_str_or_none(c)
        if s is None:
            return None
        if not first and add_slash:
            string += os.path.sep
        string += s
        first = False
    return string


def _add_os_path_join(module_context, start_leaf, bracket_start):
    def check(maybe_bracket, nodes):
        if maybe_bracket.start_pos != bracket_start:
            return None

        if not nodes:
            return ''
        context = module_context.create_context(nodes[0])
        return _add_strings(context, nodes, add_slash=True) or ''

    if start_leaf.type == 'error_leaf':
        # Unfinished string literal, like `join('`
        value_node = start_leaf.parent
        index = value_node.children.index(start_leaf)
        if index > 0:
            error_node = value_node.children[index - 1]
            if error_node.type == 'error_node' and len(error_node.children) >= 2:
                index = -2
                if error_node.children[-1].type == 'arglist':
                    arglist_nodes = error_node.children[-1].children
                    index -= 1
                else:
                    arglist_nodes = []

                return check(error_node.children[index + 1], arglist_nodes[::2])
        return None

    # Maybe an arglist or some weird error case. Therefore checked below.
    searched_node_child = start_leaf
    while searched_node_child.parent is not None \
            and searched_node_child.parent.type not in ('arglist', 'trailer', 'error_node'):
        searched_node_child = searched_node_child.parent

    if searched_node_child.get_first_leaf() is not start_leaf:
        return None
    searched_node = searched_node_child.parent
    if searched_node is None:
        return None

    index = searched_node.children.index(searched_node_child)
    arglist_nodes = searched_node.children[:index]
    if searched_node.type == 'arglist':
        trailer = searched_node.parent
        if trailer.type == 'error_node':
            trailer_index = trailer.children.index(searched_node)
            assert trailer_index >= 2
            assert trailer.children[trailer_index - 1] == '('
            return check(trailer.children[trailer_index - 1], arglist_nodes[::2])
        elif trailer.type == 'trailer':
            return check(trailer.children[0], arglist_nodes[::2])
    elif searched_node.type == 'trailer':
        return check(searched_node.children[0], [])
    elif searched_node.type == 'error_node':
        # Stuff like `join(""`
        return check(arglist_nodes[-1], [])

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\packages\backports\weakref_finalize.py ===
# -*- coding: utf-8 -*-
"""
backports.weakref_finalize
~~~~~~~~~~~~~~~~~~

Backports the Python 3 ``weakref.finalize`` method.
"""
from __future__ import absolute_import

import itertools
import sys
from weakref import ref

__all__ = ["weakref_finalize"]


class weakref_finalize(object):
    """Class for finalization of weakrefable objects
    finalize(obj, func, *args, **kwargs) returns a callable finalizer
    object which will be called when obj is garbage collected. The
    first time the finalizer is called it evaluates func(*arg, **kwargs)
    and returns the result. After this the finalizer is dead, and
    calling it just returns None.
    When the program exits any remaining finalizers for which the
    atexit attribute is true will be run in reverse order of creation.
    By default atexit is true.
    """

    # Finalizer objects don't have any state of their own.  They are
    # just used as keys to lookup _Info objects in the registry.  This
    # ensures that they cannot be part of a ref-cycle.

    __slots__ = ()
    _registry = {}
    _shutdown = False
    _index_iter = itertools.count()
    _dirty = False
    _registered_with_atexit = False

    class _Info(object):
        __slots__ = ("weakref", "func", "args", "kwargs", "atexit", "index")

    def __init__(self, obj, func, *args, **kwargs):
        if not self._registered_with_atexit:
            # We may register the exit function more than once because
            # of a thread race, but that is harmless
            import atexit

            atexit.register(self._exitfunc)
            weakref_finalize._registered_with_atexit = True
        info = self._Info()
        info.weakref = ref(obj, self)
        info.func = func
        info.args = args
        info.kwargs = kwargs or None
        info.atexit = True
        info.index = next(self._index_iter)
        self._registry[self] = info
        weakref_finalize._dirty = True

    def __call__(self, _=None):
        """If alive then mark as dead and return func(*args, **kwargs);
        otherwise return None"""
        info = self._registry.pop(self, None)
        if info and not self._shutdown:
            return info.func(*info.args, **(info.kwargs or {}))

    def detach(self):
        """If alive then mark as dead and return (obj, func, args, kwargs);
        otherwise return None"""
        info = self._registry.get(self)
        obj = info and info.weakref()
        if obj is not None and self._registry.pop(self, None):
            return (obj, info.func, info.args, info.kwargs or {})

    def peek(self):
        """If alive then return (obj, func, args, kwargs);
        otherwise return None"""
        info = self._registry.get(self)
        obj = info and info.weakref()
        if obj is not None:
            return (obj, info.func, info.args, info.kwargs or {})

    @property
    def alive(self):
        """Whether finalizer is alive"""
        return self in self._registry

    @property
    def atexit(self):
        """Whether finalizer should be called at exit"""
        info = self._registry.get(self)
        return bool(info) and info.atexit

    @atexit.setter
    def atexit(self, value):
        info = self._registry.get(self)
        if info:
            info.atexit = bool(value)

    def __repr__(self):
        info = self._registry.get(self)
        obj = info and info.weakref()
        if obj is None:
            return "<%s object at %#x; dead>" % (type(self).__name__, id(self))
        else:
            return "<%s object at %#x; for %r at %#x>" % (
                type(self).__name__,
                id(self),
                type(obj).__name__,
                id(obj),
            )

    @classmethod
    def _select_for_exit(cls):
        # Return live finalizers marked for exit, oldest first
        L = [(f, i) for (f, i) in cls._registry.items() if i.atexit]
        L.sort(key=lambda item: item[1].index)
        return [f for (f, i) in L]

    @classmethod
    def _exitfunc(cls):
        # At shutdown invoke finalizers for which atexit is true.
        # This is called once all other non-daemonic threads have been
        # joined.
        reenable_gc = False
        try:
            if cls._registry:
                import gc

                if gc.isenabled():
                    reenable_gc = True
                    gc.disable()
                pending = None
                while True:
                    if pending is None or weakref_finalize._dirty:
                        pending = cls._select_for_exit()
                        weakref_finalize._dirty = False
                    if not pending:
                        break
                    f = pending.pop()
                    try:
                        # gc is disabled, so (assuming no daemonic
                        # threads) the following is the only line in
                        # this function which might trigger creation
                        # of a new finalizer
                        f()
                    except Exception:
                        sys.excepthook(*sys.exc_info())
                    assert f not in cls._registry
        finally:
            # prevent any more finalizers from executing during shutdown
            weakref_finalize._shutdown = True
            if reenable_gc:
                gc.enable()

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_set_input_files_helpers.py ===
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
import base64
import collections.abc
import os
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
    cast,
)

from playwright._impl._connection import Channel, from_channel
from playwright._impl._helper import Error
from playwright._impl._writable_stream import WritableStream

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext

from playwright._impl._api_structures import FilePayload

SIZE_LIMIT_IN_BYTES = 50 * 1024 * 1024


class InputFilesList(TypedDict, total=False):
    streams: Optional[List[Channel]]
    directoryStream: Optional[Channel]
    localDirectory: Optional[str]
    localPaths: Optional[List[str]]
    payloads: Optional[List[Dict[str, Union[str, bytes]]]]


def _list_files(directory: str) -> List[str]:
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            files.append(os.path.join(root, filename))
    return files


async def convert_input_files(
    files: Union[
        str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
    ],
    context: "BrowserContext",
) -> InputFilesList:
    items = (
        files
        if isinstance(files, collections.abc.Sequence) and not isinstance(files, str)
        else [files]
    )

    if any([isinstance(item, (str, Path)) for item in items]):
        if not all([isinstance(item, (str, Path)) for item in items]):
            raise Error("File paths cannot be mixed with buffers")

        (local_paths, local_directory) = resolve_paths_and_directory_for_input_files(
            cast(Sequence[Union[str, Path]], items)
        )

        if context._channel._connection.is_remote:
            files_to_stream = cast(
                List[str],
                (_list_files(local_directory) if local_directory else local_paths),
            )
            streams = []
            result = await context._connection.wrap_api_call(
                lambda: context._channel.send_return_as_dict(
                    "createTempFiles",
                    {
                        "rootDirName": (
                            os.path.basename(local_directory)
                            if local_directory
                            else None
                        ),
                        "items": list(
                            map(
                                lambda file: dict(
                                    name=(
                                        os.path.relpath(file, local_directory)
                                        if local_directory
                                        else os.path.basename(file)
                                    ),
                                    lastModifiedMs=int(os.path.getmtime(file) * 1000),
                                ),
                                files_to_stream,
                            )
                        ),
                    },
                )
            )
            for i, file in enumerate(result["writableStreams"]):
                stream: WritableStream = from_channel(file)
                await stream.copy(files_to_stream[i])
                streams.append(stream._channel)
            return InputFilesList(
                streams=None if local_directory else streams,
                directoryStream=result.get("rootDir"),
            )
        return InputFilesList(localPaths=local_paths, localDirectory=local_directory)

    file_payload_exceeds_size_limit = (
        sum([len(f.get("buffer", "")) for f in items if not isinstance(f, (str, Path))])
        > SIZE_LIMIT_IN_BYTES
    )
    if file_payload_exceeds_size_limit:
        raise Error(
            "Cannot set buffer larger than 50Mb, please write it to a file and pass its path instead."
        )

    return InputFilesList(
        payloads=[
            {
                "name": item["name"],
                "mimeType": item["mimeType"],
                "buffer": base64.b64encode(item["buffer"]).decode(),
            }
            for item in cast(List[FilePayload], items)
        ]
    )


def resolve_paths_and_directory_for_input_files(
    items: Sequence[Union[str, Path]]
) -> Tuple[Optional[List[str]], Optional[str]]:
    local_paths: Optional[List[str]] = None
    local_directory: Optional[str] = None
    for item in items:
        if os.path.isdir(item):
            if local_directory:
                raise Error("Multiple directories are not supported")
            local_directory = str(Path(item).resolve())
        else:
            local_paths = local_paths or []
            local_paths.append(str(Path(item).resolve()))
    if local_paths and local_directory:
        raise Error("File paths must be all files or a single directory")
    return (local_paths, local_directory)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\ldap.py ===
"""
    pygments.lexers.ldap
    ~~~~~~~~~~~~~~~~~~~~

    Pygments lexers for LDAP.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re


from pygments.lexer import RegexLexer, bygroups, default
from pygments.token import Operator, Comment, Keyword, Literal, Name, String, \
    Number, Punctuation, Whitespace, Escape

__all__ = ['LdifLexer', 'LdaprcLexer']


class LdifLexer(RegexLexer):

    """
    Lexer for LDIF
    """

    name = 'LDIF'
    aliases = ['ldif']
    filenames = ['*.ldif']
    mimetypes = ["text/x-ldif"]
    url = "https://datatracker.ietf.org/doc/html/rfc2849"
    version_added = '2.17'

    tokens = {
        'root': [
            (r'\s*\n', Whitespace),
            (r'(-)(\n)', bygroups(Punctuation, Whitespace)),
            (r'(#.*)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'(version)(:)([ \t]*)(.*)([ \t]*\n)', bygroups(Keyword,
             Punctuation, Whitespace, Number.Integer, Whitespace)),
            (r'(control)(:)([ \t]*)([\.0-9]+)([ \t]+)((?:true|false)?)([ \t]*)',
                bygroups(Keyword, Punctuation, Whitespace, Name.Other, Whitespace, Keyword, Whitespace), "after-control"),
            (r'(deleteoldrdn)(:)([ \n]*)([0-1]+)([ \t]*\n)',
             bygroups(Keyword, Punctuation, Whitespace, Number, Whitespace)),
            (r'(add|delete|replace)(::?)(\s*)(.*)([ \t]*\n)', bygroups(
                Keyword, Punctuation, Whitespace, Name.Attribute, Whitespace)),
            (r'(changetype)(:)([ \t]*)([a-z]*)([ \t]*\n)',
             bygroups(Keyword, Punctuation, Whitespace, Keyword, Whitespace)),
            (r'(dn|newrdn)(::)', bygroups(Keyword, Punctuation), "base64-dn"),
            (r'(dn|newrdn)(:)', bygroups(Keyword, Punctuation), "dn"),
            (r'(objectclass)(:)([ \t]*)([^ \t\n]*)([ \t]*\n)', bygroups(
                Keyword, Punctuation, Whitespace, Name.Class, Whitespace)),
            (r'([a-zA-Z]*|[0-9][0-9\.]*[0-9])(;)',
             bygroups(Name.Attribute, Punctuation), "property"),
            (r'([a-zA-Z]*|[0-9][0-9\.]*[0-9])(:<)',
             bygroups(Name.Attribute, Punctuation), "url"),
            (r'([a-zA-Z]*|[0-9][0-9\.]*[0-9])(::?)',
             bygroups(Name.Attribute, Punctuation), "value"),
        ],
        "after-control": [
            (r":<", Punctuation, ("#pop", "url")),
            (r"::?", Punctuation, ("#pop", "value")),
            default("#pop"),
        ],
        'property': [
            (r'([-a-zA-Z0-9]*)(;)', bygroups(Name.Property, Punctuation)),
            (r'([-a-zA-Z0-9]*)(:<)',
             bygroups(Name.Property, Punctuation), ("#pop", "url")),
            (r'([-a-zA-Z0-9]*)(::?)',
             bygroups(Name.Property, Punctuation), ("#pop", "value")),
        ],
        'value': [
            (r'(\s*)([^\n]+\S)(\n )',
             bygroups(Whitespace, String, Whitespace)),
            (r'(\s*)([^\n]+\S)(\n)',
             bygroups(Whitespace, String, Whitespace), "#pop"),
        ],
        'url': [
            (r'([ \t]*)(\S*)([ \t]*\n )',
             bygroups(Whitespace, Comment.PreprocFile, Whitespace)),
            (r'([ \t]*)(\S*)([ \t]*\n)', bygroups(Whitespace,
             Comment.PreprocFile, Whitespace), "#pop"),
        ],
        "dn": [
            (r'([ \t]*)([-a-zA-Z0-9\.]+)(=)', bygroups(Whitespace,
             Name.Attribute, Operator), ("#pop", "dn-value")),
        ],
        "dn-value": [
            (r'\\[^\n]', Escape),
            (r',', Punctuation, ("#pop", "dn")),
            (r'\+', Operator, ("#pop", "dn")),
            (r'[^,\+\n]+', String),
            (r'\n ', Whitespace),
            (r'\n', Whitespace, "#pop"),
        ],
        "base64-dn": [
            (r'([ \t]*)([^ \t\n][^ \t\n]*[^\n])([ \t]*\n )',
             bygroups(Whitespace, Name, Whitespace)),
            (r'([ \t]*)([^ \t\n][^ \t\n]*[^\n])([ \t]*\n)',
             bygroups(Whitespace, Name, Whitespace), "#pop"),
        ]
    }


class LdaprcLexer(RegexLexer):
    """
    Lexer for OpenLDAP configuration files.
    """

    name = 'LDAP configuration file'
    aliases = ['ldapconf', 'ldaprc']
    filenames = ['.ldaprc', 'ldaprc', 'ldap.conf']
    mimetypes = ["text/x-ldapconf"]
    url = 'https://www.openldap.org/software//man.cgi?query=ldap.conf&sektion=5&apropos=0&manpath=OpenLDAP+2.4-Release'
    version_added = '2.17'

    _sasl_keywords = r'SASL_(?:MECH|REALM|AUTHCID|AUTHZID|CBINDING)'
    _tls_keywords = r'TLS_(?:CACERT|CACERTDIR|CERT|ECNAME|KEY|CIPHER_SUITE|PROTOCOL_MIN|RANDFILE|CRLFILE)'
    _literal_keywords = rf'(?:URI|SOCKET_BIND_ADDRESSES|{_sasl_keywords}|{_tls_keywords})'
    _boolean_keywords = r'GSSAPI_(?:ALLOW_REMOTE_PRINCIPAL|ENCRYPT|SIGN)|REFERRALS|SASL_NOCANON'
    _integer_keywords = r'KEEPALIVE_(?:IDLE|PROBES|INTERVAL)|NETWORK_TIMEOUT|PORT|SIZELIMIT|TIMELIMIT|TIMEOUT'
    _secprops = r'none|noanonymous|noplain|noactive|nodict|forwardsec|passcred|(?:minssf|maxssf|maxbufsize)=\d+'

    flags = re.IGNORECASE | re.MULTILINE

    tokens = {
        'root': [
            (r'#.*', Comment.Single),
            (r'\s+', Whitespace),
            (rf'({_boolean_keywords})(\s+)(on|true|yes|off|false|no)$',
             bygroups(Keyword, Whitespace, Keyword.Constant)),
            (rf'({_integer_keywords})(\s+)(\d+)',
             bygroups(Keyword, Whitespace, Number.Integer)),
            (r'(VERSION)(\s+)(2|3)', bygroups(Keyword, Whitespace, Number.Integer)),
            # Constants
            (r'(DEREF)(\s+)(never|searching|finding|always)',
             bygroups(Keyword, Whitespace, Keyword.Constant)),
            (rf'(SASL_SECPROPS)(\s+)((?:{_secprops})(?:,{_secprops})*)',
             bygroups(Keyword, Whitespace, Keyword.Constant)),
            (r'(SASL_CBINDING)(\s+)(none|tls-unique|tls-endpoint)',
             bygroups(Keyword, Whitespace, Keyword.Constant)),
            (r'(TLS_REQ(?:CERT|SAN))(\s+)(allow|demand|hard|never|try)',
             bygroups(Keyword, Whitespace, Keyword.Constant)),
            (r'(TLS_CRLCHECK)(\s+)(none|peer|all)',
             bygroups(Keyword, Whitespace, Keyword.Constant)),
            # Literals
            (r'(BASE|BINDDN)(\s+)(\S+)$',
             bygroups(Keyword, Whitespace, Literal)),
            # Accepts hostname with or without port.
            (r'(HOST)(\s+)([a-z0-9]+)((?::(\d+))?)',
             bygroups(Keyword, Whitespace, Literal, Number.Integer)),
            (rf'({_literal_keywords})(\s+)(\S+)$',
             bygroups(Keyword, Whitespace, Literal)),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\dialogs\login.py ===
"""login -- PythonWin user ID and password dialog box

(Adapted from originally distributed with Mark Hammond's PythonWin -
this now replaces it!)

login.GetLogin() displays a modal "OK/Cancel" dialog box with input
fields for a user ID and password. The password field input is masked
with *'s. GetLogin takes two optional parameters, a window title, and a
default user ID. If these parameters are omitted, the title defaults to
"Login", and the user ID is left blank. GetLogin returns a (userid, password)
tuple. GetLogin can be called from scripts running on the console - i.e. you
don't need to write a full-blown GUI app to use it.

login.GetPassword() is similar, except there is no username field.

Example:
import pywin.dialogs.login
title = "FTP Login"
def_user = "fred"
userid, password = pywin.dialogs.login.GetLogin(title, def_user)

Jim Eggleston, 28 August 1996
Merged with dlgpass and moved to pywin.dialogs by Mark Hammond Jan 1998.
"""

import win32con
import win32ui
from pywin.mfc import dialog


def MakeLoginDlgTemplate(title):
    style = (
        win32con.DS_MODALFRAME
        | win32con.WS_POPUP
        | win32con.WS_VISIBLE
        | win32con.WS_CAPTION
        | win32con.WS_SYSMENU
        | win32con.DS_SETFONT
    )
    cs = win32con.WS_CHILD | win32con.WS_VISIBLE

    # Window frame and title
    dlg = [
        [title, (0, 0, 184, 40), style, None, (8, "MS Sans Serif")],
    ]

    # ID label and text box
    dlg.append([130, "User ID:", -1, (7, 9, 69, 9), cs | win32con.SS_LEFT])
    s = cs | win32con.WS_TABSTOP | win32con.WS_BORDER
    dlg.append(["EDIT", None, win32ui.IDC_EDIT1, (50, 7, 60, 12), s])

    # Password label and text box
    dlg.append([130, "Password:", -1, (7, 22, 69, 9), cs | win32con.SS_LEFT])
    s = cs | win32con.WS_TABSTOP | win32con.WS_BORDER
    dlg.append(
        ["EDIT", None, win32ui.IDC_EDIT2, (50, 20, 60, 12), s | win32con.ES_PASSWORD]
    )

    # OK/Cancel Buttons
    s = cs | win32con.WS_TABSTOP
    dlg.append(
        [128, "OK", win32con.IDOK, (124, 5, 50, 14), s | win32con.BS_DEFPUSHBUTTON]
    )
    s = win32con.BS_PUSHBUTTON | s
    dlg.append([128, "Cancel", win32con.IDCANCEL, (124, 20, 50, 14), s])
    return dlg


def MakePasswordDlgTemplate(title):
    style = (
        win32con.DS_MODALFRAME
        | win32con.WS_POPUP
        | win32con.WS_VISIBLE
        | win32con.WS_CAPTION
        | win32con.WS_SYSMENU
        | win32con.DS_SETFONT
    )
    cs = win32con.WS_CHILD | win32con.WS_VISIBLE
    # Window frame and title
    dlg = [
        [title, (0, 0, 177, 45), style, None, (8, "MS Sans Serif")],
    ]

    # Password label and text box
    dlg.append([130, "Password:", -1, (7, 7, 69, 9), cs | win32con.SS_LEFT])
    s = cs | win32con.WS_TABSTOP | win32con.WS_BORDER
    dlg.append(
        ["EDIT", None, win32ui.IDC_EDIT1, (50, 7, 60, 12), s | win32con.ES_PASSWORD]
    )

    # OK/Cancel Buttons
    s = cs | win32con.WS_TABSTOP | win32con.BS_PUSHBUTTON
    dlg.append(
        [128, "OK", win32con.IDOK, (124, 5, 50, 14), s | win32con.BS_DEFPUSHBUTTON]
    )
    dlg.append([128, "Cancel", win32con.IDCANCEL, (124, 22, 50, 14), s])
    return dlg


class LoginDlg(dialog.Dialog):
    Cancel = 0

    def __init__(self, title):
        dialog.Dialog.__init__(self, MakeLoginDlgTemplate(title))
        self.AddDDX(win32ui.IDC_EDIT1, "userid")
        self.AddDDX(win32ui.IDC_EDIT2, "password")


def GetLogin(title="Login", userid="", password=""):
    d = LoginDlg(title)
    d["userid"] = userid
    d["password"] = password
    if d.DoModal() != win32con.IDOK:
        return (None, None)
    else:
        return (d["userid"], d["password"])


class PasswordDlg(dialog.Dialog):
    def __init__(self, title):
        dialog.Dialog.__init__(self, MakePasswordDlgTemplate(title))
        self.AddDDX(win32ui.IDC_EDIT1, "password")


def GetPassword(title="Password", password=""):
    d = PasswordDlg(title)
    d["password"] = password
    if d.DoModal() != win32con.IDOK:
        return None
    return d["password"]


if __name__ == "__main__":
    import sys

    title = "Login"
    def_user = ""
    if len(sys.argv) > 1:
        title = sys.argv[1]
    if len(sys.argv) > 2:
        def_userid = sys.argv[2]
    userid, password = GetLogin(title, def_user)
    if userid == password is None:
        print("User pressed Cancel")
    else:
        print("User ID: ", userid)
        print("Password:", password)
        newpassword = GetPassword("Reenter just for fun", password)
        if newpassword is None:
            print("User cancelled")
        else:
            what = ""
            if newpassword != password:
                what = "not "
            print("The passwords did %smatch" % (what))

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\cli\__init__.py ===
"""
Wheel command-line utility.
"""

from __future__ import annotations

import argparse
import os
import sys
from argparse import ArgumentTypeError


class WheelError(Exception):
    pass


def unpack_f(args: argparse.Namespace) -> None:
    from .unpack import unpack

    unpack(args.wheelfile, args.dest)


def pack_f(args: argparse.Namespace) -> None:
    from .pack import pack

    pack(args.directory, args.dest_dir, args.build_number)


def convert_f(args: argparse.Namespace) -> None:
    from .convert import convert

    convert(args.files, args.dest_dir, args.verbose)


def tags_f(args: argparse.Namespace) -> None:
    from .tags import tags

    names = (
        tags(
            wheel,
            args.python_tag,
            args.abi_tag,
            args.platform_tag,
            args.build,
            args.remove,
        )
        for wheel in args.wheel
    )

    for name in names:
        print(name)


def version_f(args: argparse.Namespace) -> None:
    from .. import __version__

    print(f"wheel {__version__}")


def parse_build_tag(build_tag: str) -> str:
    if build_tag and not build_tag[0].isdigit():
        raise ArgumentTypeError("build tag must begin with a digit")
    elif "-" in build_tag:
        raise ArgumentTypeError("invalid character ('-') in build tag")

    return build_tag


TAGS_HELP = """\
Make a new wheel with given tags. Any tags unspecified will remain the same.
Starting the tags with a "+" will append to the existing tags. Starting with a
"-" will remove a tag (use --option=-TAG syntax). Multiple tags can be
separated by ".". The original file will remain unless --remove is given.  The
output filename(s) will be displayed on stdout for further processing.
"""


def parser():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(help="commands")

    unpack_parser = s.add_parser("unpack", help="Unpack wheel")
    unpack_parser.add_argument(
        "--dest", "-d", help="Destination directory", default="."
    )
    unpack_parser.add_argument("wheelfile", help="Wheel file")
    unpack_parser.set_defaults(func=unpack_f)

    repack_parser = s.add_parser("pack", help="Repack wheel")
    repack_parser.add_argument("directory", help="Root directory of the unpacked wheel")
    repack_parser.add_argument(
        "--dest-dir",
        "-d",
        default=os.path.curdir,
        help="Directory to store the wheel (default %(default)s)",
    )
    repack_parser.add_argument(
        "--build-number", help="Build tag to use in the wheel name"
    )
    repack_parser.set_defaults(func=pack_f)

    convert_parser = s.add_parser("convert", help="Convert egg or wininst to wheel")
    convert_parser.add_argument("files", nargs="*", help="Files to convert")
    convert_parser.add_argument(
        "--dest-dir",
        "-d",
        default=os.path.curdir,
        help="Directory to store wheels (default %(default)s)",
    )
    convert_parser.add_argument("--verbose", "-v", action="store_true")
    convert_parser.set_defaults(func=convert_f)

    tags_parser = s.add_parser(
        "tags", help="Add or replace the tags on a wheel", description=TAGS_HELP
    )
    tags_parser.add_argument("wheel", nargs="*", help="Existing wheel(s) to retag")
    tags_parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove the original files, keeping only the renamed ones",
    )
    tags_parser.add_argument(
        "--python-tag", metavar="TAG", help="Specify an interpreter tag(s)"
    )
    tags_parser.add_argument("--abi-tag", metavar="TAG", help="Specify an ABI tag(s)")
    tags_parser.add_argument(
        "--platform-tag", metavar="TAG", help="Specify a platform tag(s)"
    )
    tags_parser.add_argument(
        "--build", type=parse_build_tag, metavar="BUILD", help="Specify a build tag"
    )
    tags_parser.set_defaults(func=tags_f)

    version_parser = s.add_parser("version", help="Print version and exit")
    version_parser.set_defaults(func=version_f)

    help_parser = s.add_parser("help", help="Show this help")
    help_parser.set_defaults(func=lambda args: p.print_help())

    return p


def main():
    p = parser()
    args = p.parse_args()
    if not hasattr(args, "func"):
        p.print_help()
    else:
        try:
            args.func(args)
            return 0
        except WheelError as e:
            print(e, file=sys.stderr)

    return 1

# === NexusCore/openenv\Lib\site-packages\win32\Demos\win32clipboardDemo.py ===
# win32clipboardDemo.py
#
# Demo/test of the win32clipboard module.
import win32con
from win32clipboard import (
    CloseClipboard,
    EmptyClipboard,
    EnumClipboardFormats,
    GetClipboardData,
    GetClipboardFormatName,
    IsClipboardFormatAvailable,
    OpenClipboard,
    RegisterClipboardFormat,
    SetClipboardData,
    SetClipboardText,
)

if not __debug__:
    print("WARNING: The test code in this module uses assert")
    print("This instance of Python has asserts disabled, so many tests will be skipped")

# Build map of CF_* constants to names.
cf_names = {
    val: name
    for name, val in win32con.__dict__.items()
    if name[:3] == "CF_" and name != "CF_SCREENFONTS"  # CF_SCREEN_FONTS==CF_TEXT!?!?
}


def TestEmptyClipboard():
    OpenClipboard()
    try:
        EmptyClipboard()
        assert (
            EnumClipboardFormats(0) == 0
        ), "Clipboard formats were available after emptying it!"
    finally:
        CloseClipboard()


def TestText():
    OpenClipboard()
    try:
        text = "Hello from Python"
        text_bytes = text.encode("latin1")
        SetClipboardText(text)
        got = GetClipboardData(win32con.CF_TEXT)
        # CF_TEXT always gives us 'bytes' back .
        assert got == text_bytes, f"Didn't get the correct result back - '{got!r}'."
    finally:
        CloseClipboard()

    OpenClipboard()
    try:
        # CF_UNICODE text always gives unicode objects back.
        got = GetClipboardData(win32con.CF_UNICODETEXT)
        assert got == text, f"Didn't get the correct result back - '{got!r}'."
        assert isinstance(got, str), f"Didn't get the correct result back - '{got!r}'."

        # CF_OEMTEXT is a bytes-based format.
        got = GetClipboardData(win32con.CF_OEMTEXT)
        assert got == text_bytes, f"Didn't get the correct result back - '{got!r}'."

        # Unicode tests
        EmptyClipboard()
        text = "Hello from Python unicode"
        text_bytes = text.encode("latin1")
        # Now set the Unicode value
        SetClipboardData(win32con.CF_UNICODETEXT, text)
        # Get it in Unicode.
        got = GetClipboardData(win32con.CF_UNICODETEXT)
        assert got == text, f"Didn't get the correct result back - '{got!r}'."
        assert isinstance(got, str), f"Didn't get the correct result back - '{got!r}'."

        # Close and open the clipboard to ensure auto-conversions take place.
    finally:
        CloseClipboard()

    OpenClipboard()
    try:
        # Make sure I can still get the text as bytes
        got = GetClipboardData(win32con.CF_TEXT)
        assert got == text_bytes, f"Didn't get the correct result back - '{got!r}'."
        # Make sure we get back the correct types.
        got = GetClipboardData(win32con.CF_UNICODETEXT)
        assert isinstance(got, str), f"Didn't get the correct result back - '{got!r}'."
        got = GetClipboardData(win32con.CF_OEMTEXT)
        assert got == text_bytes, f"Didn't get the correct result back - '{got!r}'."
        print("Clipboard text tests worked correctly")
    finally:
        CloseClipboard()


def TestClipboardEnum():
    OpenClipboard()
    try:
        # Enumerate over the clipboard types
        enum = 0
        while 1:
            enum = EnumClipboardFormats(enum)
            if enum == 0:
                break
            assert IsClipboardFormatAvailable(
                enum
            ), "Have format, but clipboard says it is not available!"
            n = cf_names.get(enum, "")
            if not n:
                try:
                    n = GetClipboardFormatName(enum)
                except error:
                    n = f"unknown ({enum})"

            print("Have format", n)
        print("Clipboard enumerator tests worked correctly")
    finally:
        CloseClipboard()


class Foo:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __lt__(self, other):
        return self.__dict__ < other.__dict__

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


def TestCustomFormat():
    OpenClipboard()
    try:
        # Just for the fun of it pickle Python objects through the clipboard
        fmt = RegisterClipboardFormat("Python Pickle Format")
        import pickle

        pickled_object = Foo(a=1, b=2, Hi=3)
        SetClipboardData(fmt, pickle.dumps(pickled_object))
        # Now read it back.
        data = GetClipboardData(fmt)
        loaded_object = pickle.loads(data)
        assert pickle.loads(data) == pickled_object, "Didn't get the correct data!"

        print("Clipboard custom format tests worked correctly")
    finally:
        CloseClipboard()


if __name__ == "__main__":
    TestEmptyClipboard()
    TestText()
    TestCustomFormat()
    TestClipboardEnum()
    # And leave it empty at the end!
    TestEmptyClipboard()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\formatters\irc.py ===
"""
    pygments.formatters.irc
    ~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for IRC output

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.token import Keyword, Name, Comment, String, Error, \
    Number, Operator, Generic, Token, Whitespace
from pip._vendor.pygments.util import get_choice_opt


__all__ = ['IRCFormatter']


#: Map token types to a tuple of color values for light and dark
#: backgrounds.
IRC_COLORS = {
    Token:              ('',            ''),

    Whitespace:         ('gray',   'brightblack'),
    Comment:            ('gray',   'brightblack'),
    Comment.Preproc:    ('cyan',        'brightcyan'),
    Keyword:            ('blue',    'brightblue'),
    Keyword.Type:       ('cyan',        'brightcyan'),
    Operator.Word:      ('magenta',      'brightcyan'),
    Name.Builtin:       ('cyan',        'brightcyan'),
    Name.Function:      ('green',   'brightgreen'),
    Name.Namespace:     ('_cyan_',      '_brightcyan_'),
    Name.Class:         ('_green_', '_brightgreen_'),
    Name.Exception:     ('cyan',        'brightcyan'),
    Name.Decorator:     ('brightblack',    'gray'),
    Name.Variable:      ('red',     'brightred'),
    Name.Constant:      ('red',     'brightred'),
    Name.Attribute:     ('cyan',        'brightcyan'),
    Name.Tag:           ('brightblue',        'brightblue'),
    String:             ('yellow',       'yellow'),
    Number:             ('blue',    'brightblue'),

    Generic.Deleted:    ('brightred',        'brightred'),
    Generic.Inserted:   ('green',  'brightgreen'),
    Generic.Heading:    ('**',         '**'),
    Generic.Subheading: ('*magenta*',   '*brightmagenta*'),
    Generic.Error:      ('brightred',        'brightred'),

    Error:              ('_brightred_',      '_brightred_'),
}


IRC_COLOR_MAP = {
    'white': 0,
    'black': 1,
    'blue': 2,
    'brightgreen': 3,
    'brightred': 4,
    'yellow': 5,
    'magenta': 6,
    'orange': 7,
    'green': 7, #compat w/ ansi
    'brightyellow': 8,
    'lightgreen': 9,
    'brightcyan': 9, # compat w/ ansi
    'cyan': 10,
    'lightblue': 11,
    'red': 11, # compat w/ ansi
    'brightblue': 12,
    'brightmagenta': 13,
    'brightblack': 14,
    'gray': 15,
}

def ircformat(color, text):
    if len(color) < 1:
        return text
    add = sub = ''
    if '_' in color: # italic
        add += '\x1D'
        sub = '\x1D' + sub
        color = color.strip('_')
    if '*' in color: # bold
        add += '\x02'
        sub = '\x02' + sub
        color = color.strip('*')
    # underline (\x1F) not supported
    # backgrounds (\x03FF,BB) not supported
    if len(color) > 0: # actual color - may have issues with ircformat("red", "blah")+"10" type stuff
        add += '\x03' + str(IRC_COLOR_MAP[color]).zfill(2)
        sub = '\x03' + sub
    return add + text + sub
    return '<'+add+'>'+text+'</'+sub+'>'


class IRCFormatter(Formatter):
    r"""
    Format tokens with IRC color sequences

    The `get_style_defs()` method doesn't do anything special since there is
    no support for common styles.

    Options accepted:

    `bg`
        Set to ``"light"`` or ``"dark"`` depending on the terminal's background
        (default: ``"light"``).

    `colorscheme`
        A dictionary mapping token types to (lightbg, darkbg) color names or
        ``None`` (default: ``None`` = use builtin colorscheme).

    `linenos`
        Set to ``True`` to have line numbers in the output as well
        (default: ``False`` = no line numbers).
    """
    name = 'IRC'
    aliases = ['irc', 'IRC']
    filenames = []

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.darkbg = get_choice_opt(options, 'bg',
                                     ['light', 'dark'], 'light') == 'dark'
        self.colorscheme = options.get('colorscheme', None) or IRC_COLORS
        self.linenos = options.get('linenos', False)
        self._lineno = 0

    def _write_lineno(self, outfile):
        if self.linenos:
            self._lineno += 1
            outfile.write("%04d: " % self._lineno)

    def format_unencoded(self, tokensource, outfile):
        self._write_lineno(outfile)

        for ttype, value in tokensource:
            color = self.colorscheme.get(ttype)
            while color is None:
                ttype = ttype[:-1]
                color = self.colorscheme.get(ttype)
            if color:
                color = color[self.darkbg]
                spl = value.split('\n')
                for line in spl[:-1]:
                    if line:
                        outfile.write(ircformat(color, line))
                    outfile.write('\n')
                    self._write_lineno(outfile)
                if spl[-1]:
                    outfile.write(ircformat(color, spl[-1]))
            else:
                outfile.write(value)

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\textTools.py ===
"""fontTools.misc.textTools.py -- miscellaneous routines."""

import ast
import string


# alias kept for backward compatibility
safeEval = ast.literal_eval


class Tag(str):
    @staticmethod
    def transcode(blob):
        if isinstance(blob, bytes):
            blob = blob.decode("latin-1")
        return blob

    def __new__(self, content):
        return str.__new__(self, self.transcode(content))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        return str.__eq__(self, self.transcode(other))

    def __hash__(self):
        return str.__hash__(self)

    def tobytes(self):
        return self.encode("latin-1")


def readHex(content):
    """Convert a list of hex strings to binary data."""
    return deHexStr(strjoin(chunk for chunk in content if isinstance(chunk, str)))


def deHexStr(hexdata):
    """Convert a hex string to binary data."""
    hexdata = strjoin(hexdata.split())
    if len(hexdata) % 2:
        hexdata = hexdata + "0"
    data = []
    for i in range(0, len(hexdata), 2):
        data.append(bytechr(int(hexdata[i : i + 2], 16)))
    return bytesjoin(data)


def hexStr(data):
    """Convert binary data to a hex string."""
    h = string.hexdigits
    r = ""
    for c in data:
        i = byteord(c)
        r = r + h[(i >> 4) & 0xF] + h[i & 0xF]
    return r


def num2binary(l, bits=32):
    items = []
    binary = ""
    for i in range(bits):
        if l & 0x1:
            binary = "1" + binary
        else:
            binary = "0" + binary
        l = l >> 1
        if not ((i + 1) % 8):
            items.append(binary)
            binary = ""
    if binary:
        items.append(binary)
    items.reverse()
    assert l in (0, -1), "number doesn't fit in number of bits"
    return " ".join(items)


def binary2num(bin):
    bin = strjoin(bin.split())
    l = 0
    for digit in bin:
        l = l << 1
        if digit != "0":
            l = l | 0x1
    return l


def caselessSort(alist):
    """Return a sorted copy of a list. If there are only strings
    in the list, it will not consider case.
    """

    try:
        return sorted(alist, key=lambda a: (a.lower(), a))
    except TypeError:
        return sorted(alist)


def pad(data, size):
    r"""Pad byte string 'data' with null bytes until its length is a
    multiple of 'size'.

    >>> len(pad(b'abcd', 4))
    4
    >>> len(pad(b'abcde', 2))
    6
    >>> len(pad(b'abcde', 4))
    8
    >>> pad(b'abcdef', 4) == b'abcdef\x00\x00'
    True
    """
    data = tobytes(data)
    if size > 1:
        remainder = len(data) % size
        if remainder:
            data += b"\0" * (size - remainder)
    return data


def tostr(s, encoding="ascii", errors="strict"):
    if not isinstance(s, str):
        return s.decode(encoding, errors)
    else:
        return s


def tobytes(s, encoding="ascii", errors="strict"):
    if isinstance(s, str):
        return s.encode(encoding, errors)
    else:
        return bytes(s)


def bytechr(n):
    return bytes([n])


def byteord(c):
    return c if isinstance(c, int) else ord(c)


def strjoin(iterable, joiner=""):
    return tostr(joiner).join(iterable)


def bytesjoin(iterable, joiner=b""):
    return tobytes(joiner).join(tobytes(item) for item in iterable)


if __name__ == "__main__":
    import doctest, sys

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\fontTools\svgLib\path\arc.py ===
"""Convert SVG Path's elliptical arcs to Bezier curves.

The code is mostly adapted from Blink's SVGPathNormalizer::DecomposeArcToCubic
https://github.com/chromium/chromium/blob/93831f2/third_party/
blink/renderer/core/svg/svg_path_parser.cc#L169-L278
"""

from fontTools.misc.transform import Identity, Scale
from math import atan2, ceil, cos, fabs, isfinite, pi, radians, sin, sqrt, tan


TWO_PI = 2 * pi
PI_OVER_TWO = 0.5 * pi


def _map_point(matrix, pt):
    # apply Transform matrix to a point represented as a complex number
    r = matrix.transformPoint((pt.real, pt.imag))
    return r[0] + r[1] * 1j


class EllipticalArc(object):
    def __init__(self, current_point, rx, ry, rotation, large, sweep, target_point):
        self.current_point = current_point
        self.rx = rx
        self.ry = ry
        self.rotation = rotation
        self.large = large
        self.sweep = sweep
        self.target_point = target_point

        # SVG arc's rotation angle is expressed in degrees, whereas Transform.rotate
        # uses radians
        self.angle = radians(rotation)

        # these derived attributes are computed by the _parametrize method
        self.center_point = self.theta1 = self.theta2 = self.theta_arc = None

    def _parametrize(self):
        # convert from endopoint to center parametrization:
        # https://www.w3.org/TR/SVG/implnote.html#ArcConversionEndpointToCenter

        # If rx = 0 or ry = 0 then this arc is treated as a straight line segment (a
        # "lineto") joining the endpoints.
        # http://www.w3.org/TR/SVG/implnote.html#ArcOutOfRangeParameters
        rx = fabs(self.rx)
        ry = fabs(self.ry)
        if not (rx and ry):
            return False

        # If the current point and target point for the arc are identical, it should
        # be treated as a zero length path. This ensures continuity in animations.
        if self.target_point == self.current_point:
            return False

        mid_point_distance = (self.current_point - self.target_point) * 0.5

        point_transform = Identity.rotate(-self.angle)

        transformed_mid_point = _map_point(point_transform, mid_point_distance)
        square_rx = rx * rx
        square_ry = ry * ry
        square_x = transformed_mid_point.real * transformed_mid_point.real
        square_y = transformed_mid_point.imag * transformed_mid_point.imag

        # Check if the radii are big enough to draw the arc, scale radii if not.
        # http://www.w3.org/TR/SVG/implnote.html#ArcCorrectionOutOfRangeRadii
        radii_scale = square_x / square_rx + square_y / square_ry
        if radii_scale > 1:
            rx *= sqrt(radii_scale)
            ry *= sqrt(radii_scale)
            self.rx, self.ry = rx, ry

        point_transform = Scale(1 / rx, 1 / ry).rotate(-self.angle)

        point1 = _map_point(point_transform, self.current_point)
        point2 = _map_point(point_transform, self.target_point)
        delta = point2 - point1

        d = delta.real * delta.real + delta.imag * delta.imag
        scale_factor_squared = max(1 / d - 0.25, 0.0)

        scale_factor = sqrt(scale_factor_squared)
        if self.sweep == self.large:
            scale_factor = -scale_factor

        delta *= scale_factor
        center_point = (point1 + point2) * 0.5
        center_point += complex(-delta.imag, delta.real)
        point1 -= center_point
        point2 -= center_point

        theta1 = atan2(point1.imag, point1.real)
        theta2 = atan2(point2.imag, point2.real)

        theta_arc = theta2 - theta1
        if theta_arc < 0 and self.sweep:
            theta_arc += TWO_PI
        elif theta_arc > 0 and not self.sweep:
            theta_arc -= TWO_PI

        self.theta1 = theta1
        self.theta2 = theta1 + theta_arc
        self.theta_arc = theta_arc
        self.center_point = center_point

        return True

    def _decompose_to_cubic_curves(self):
        if self.center_point is None and not self._parametrize():
            return

        point_transform = Identity.rotate(self.angle).scale(self.rx, self.ry)

        # Some results of atan2 on some platform implementations are not exact
        # enough. So that we get more cubic curves than expected here. Adding 0.001f
        # reduces the count of sgements to the correct count.
        num_segments = int(ceil(fabs(self.theta_arc / (PI_OVER_TWO + 0.001))))
        for i in range(num_segments):
            start_theta = self.theta1 + i * self.theta_arc / num_segments
            end_theta = self.theta1 + (i + 1) * self.theta_arc / num_segments

            t = (4 / 3) * tan(0.25 * (end_theta - start_theta))
            if not isfinite(t):
                return

            sin_start_theta = sin(start_theta)
            cos_start_theta = cos(start_theta)
            sin_end_theta = sin(end_theta)
            cos_end_theta = cos(end_theta)

            point1 = complex(
                cos_start_theta - t * sin_start_theta,
                sin_start_theta + t * cos_start_theta,
            )
            point1 += self.center_point
            target_point = complex(cos_end_theta, sin_end_theta)
            target_point += self.center_point
            point2 = target_point
            point2 += complex(t * sin_end_theta, -t * cos_end_theta)

            point1 = _map_point(point_transform, point1)
            point2 = _map_point(point_transform, point2)
            target_point = _map_point(point_transform, target_point)

            yield point1, point2, target_point

    def draw(self, pen):
        for point1, point2, target_point in self._decompose_to_cubic_curves():
            pen.curveTo(
                (point1.real, point1.imag),
                (point2.real, point2.imag),
                (target_point.real, target_point.imag),
            )

# === NexusCore/openenv\Lib\site-packages\google\auth\metrics.py ===
# Copyright 2023 Google LLC
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

""" We use x-goog-api-client header to report metrics. This module provides
the constants and helper methods to construct x-goog-api-client header.
"""

import platform

from google.auth import version


API_CLIENT_HEADER = "x-goog-api-client"

# BYOID Specific consts
BYOID_HEADER_SECTION = "google-byoid-sdk"

# Auth request type
REQUEST_TYPE_ACCESS_TOKEN = "auth-request-type/at"
REQUEST_TYPE_ID_TOKEN = "auth-request-type/it"
REQUEST_TYPE_MDS_PING = "auth-request-type/mds"
REQUEST_TYPE_REAUTH_START = "auth-request-type/re-start"
REQUEST_TYPE_REAUTH_CONTINUE = "auth-request-type/re-cont"

# Credential type
CRED_TYPE_USER = "cred-type/u"
CRED_TYPE_SA_ASSERTION = "cred-type/sa"
CRED_TYPE_SA_JWT = "cred-type/jwt"
CRED_TYPE_SA_MDS = "cred-type/mds"
CRED_TYPE_SA_IMPERSONATE = "cred-type/imp"


# Versions
def python_and_auth_lib_version():
    return "gl-python/{} auth/{}".format(platform.python_version(), version.__version__)


# Token request metric header values

# x-goog-api-client header value for access token request via metadata server.
# Example: "gl-python/3.7 auth/1.1 auth-request-type/at cred-type/mds"
def token_request_access_token_mds():
    return "{} {} {}".format(
        python_and_auth_lib_version(), REQUEST_TYPE_ACCESS_TOKEN, CRED_TYPE_SA_MDS
    )


# x-goog-api-client header value for ID token request via metadata server.
# Example: "gl-python/3.7 auth/1.1 auth-request-type/it cred-type/mds"
def token_request_id_token_mds():
    return "{} {} {}".format(
        python_and_auth_lib_version(), REQUEST_TYPE_ID_TOKEN, CRED_TYPE_SA_MDS
    )


# x-goog-api-client header value for impersonated credentials access token request.
# Example: "gl-python/3.7 auth/1.1 auth-request-type/at cred-type/imp"
def token_request_access_token_impersonate():
    return "{} {} {}".format(
        python_and_auth_lib_version(),
        REQUEST_TYPE_ACCESS_TOKEN,
        CRED_TYPE_SA_IMPERSONATE,
    )


# x-goog-api-client header value for impersonated credentials ID token request.
# Example: "gl-python/3.7 auth/1.1 auth-request-type/it cred-type/imp"
def token_request_id_token_impersonate():
    return "{} {} {}".format(
        python_and_auth_lib_version(), REQUEST_TYPE_ID_TOKEN, CRED_TYPE_SA_IMPERSONATE
    )


# x-goog-api-client header value for service account credentials access token
# request (assertion flow).
# Example: "gl-python/3.7 auth/1.1 auth-request-type/at cred-type/sa"
def token_request_access_token_sa_assertion():
    return "{} {} {}".format(
        python_and_auth_lib_version(), REQUEST_TYPE_ACCESS_TOKEN, CRED_TYPE_SA_ASSERTION
    )


# x-goog-api-client header value for service account credentials ID token
# request (assertion flow).
# Example: "gl-python/3.7 auth/1.1 auth-request-type/it cred-type/sa"
def token_request_id_token_sa_assertion():
    return "{} {} {}".format(
        python_and_auth_lib_version(), REQUEST_TYPE_ID_TOKEN, CRED_TYPE_SA_ASSERTION
    )


# x-goog-api-client header value for user credentials token request.
# Example: "gl-python/3.7 auth/1.1 cred-type/u"
def token_request_user():
    return "{} {}".format(python_and_auth_lib_version(), CRED_TYPE_USER)


# Miscellenous metrics

# x-goog-api-client header value for metadata server ping.
# Example: "gl-python/3.7 auth/1.1 auth-request-type/mds"
def mds_ping():
    return "{} {}".format(python_and_auth_lib_version(), REQUEST_TYPE_MDS_PING)


# x-goog-api-client header value for reauth start endpoint calls.
# Example: "gl-python/3.7 auth/1.1 auth-request-type/re-start"
def reauth_start():
    return "{} {}".format(python_and_auth_lib_version(), REQUEST_TYPE_REAUTH_START)


# x-goog-api-client header value for reauth continue endpoint calls.
# Example: "gl-python/3.7 auth/1.1 cred-type/re-cont"
def reauth_continue():
    return "{} {}".format(python_and_auth_lib_version(), REQUEST_TYPE_REAUTH_CONTINUE)


# x-goog-api-client header value for BYOID calls to the Security Token Service exchange token endpoint.
# Example: "gl-python/3.7 auth/1.1 google-byoid-sdk source/aws sa-impersonation/true sa-impersonation/true"
def byoid_metrics_header(metrics_options):
    header = "{} {}".format(python_and_auth_lib_version(), BYOID_HEADER_SECTION)
    for key, value in metrics_options.items():
        header = "{} {}/{}".format(header, key, value)
    return header


def add_metric_header(headers, metric_header_value):
    """Add x-goog-api-client header with the given value.

    Args:
        headers (Mapping[str, str]): The headers to which we will add the
            metric header.
        metric_header_value (Optional[str]): If value is None, do nothing;
            if headers already has a x-goog-api-client header, append the value
            to the existing header; otherwise add a new x-goog-api-client
            header with the given value.
    """
    if not metric_header_value:
        return
    if API_CLIENT_HEADER not in headers:
        headers[API_CLIENT_HEADER] = metric_header_value
    else:
        headers[API_CLIENT_HEADER] += " " + metric_header_value

# === NexusCore/openenv\Lib\site-packages\google\protobuf\descriptor_database.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Provides a container for DescriptorProtos."""

__author__ = 'matthewtoia@google.com (Matt Toia)'

import warnings


class Error(Exception):
  pass


class DescriptorDatabaseConflictingDefinitionError(Error):
  """Raised when a proto is added with the same name & different descriptor."""


class DescriptorDatabase(object):
  """A container accepting FileDescriptorProtos and maps DescriptorProtos."""

  def __init__(self):
    self._file_desc_protos_by_file = {}
    self._file_desc_protos_by_symbol = {}

  def Add(self, file_desc_proto):
    """Adds the FileDescriptorProto and its types to this database.

    Args:
      file_desc_proto: The FileDescriptorProto to add.
    Raises:
      DescriptorDatabaseConflictingDefinitionError: if an attempt is made to
        add a proto with the same name but different definition than an
        existing proto in the database.
    """
    proto_name = file_desc_proto.name
    if proto_name not in self._file_desc_protos_by_file:
      self._file_desc_protos_by_file[proto_name] = file_desc_proto
    elif self._file_desc_protos_by_file[proto_name] != file_desc_proto:
      raise DescriptorDatabaseConflictingDefinitionError(
          '%s already added, but with different descriptor.' % proto_name)
    else:
      return

    # Add all the top-level descriptors to the index.
    package = file_desc_proto.package
    for message in file_desc_proto.message_type:
      for name in _ExtractSymbols(message, package):
        self._AddSymbol(name, file_desc_proto)
    for enum in file_desc_proto.enum_type:
      self._AddSymbol(('.'.join((package, enum.name))), file_desc_proto)
      for enum_value in enum.value:
        self._file_desc_protos_by_symbol[
            '.'.join((package, enum_value.name))] = file_desc_proto
    for extension in file_desc_proto.extension:
      self._AddSymbol(('.'.join((package, extension.name))), file_desc_proto)
    for service in file_desc_proto.service:
      self._AddSymbol(('.'.join((package, service.name))), file_desc_proto)

  def FindFileByName(self, name):
    """Finds the file descriptor proto by file name.

    Typically the file name is a relative path ending to a .proto file. The
    proto with the given name will have to have been added to this database
    using the Add method or else an error will be raised.

    Args:
      name: The file name to find.

    Returns:
      The file descriptor proto matching the name.

    Raises:
      KeyError if no file by the given name was added.
    """

    return self._file_desc_protos_by_file[name]

  def FindFileContainingSymbol(self, symbol):
    """Finds the file descriptor proto containing the specified symbol.

    The symbol should be a fully qualified name including the file descriptor's
    package and any containing messages. Some examples:

    'some.package.name.Message'
    'some.package.name.Message.NestedEnum'
    'some.package.name.Message.some_field'

    The file descriptor proto containing the specified symbol must be added to
    this database using the Add method or else an error will be raised.

    Args:
      symbol: The fully qualified symbol name.

    Returns:
      The file descriptor proto containing the symbol.

    Raises:
      KeyError if no file contains the specified symbol.
    """
    try:
      return self._file_desc_protos_by_symbol[symbol]
    except KeyError:
      # Fields, enum values, and nested extensions are not in
      # _file_desc_protos_by_symbol. Try to find the top level
      # descriptor. Non-existent nested symbol under a valid top level
      # descriptor can also be found. The behavior is the same with
      # protobuf C++.
      top_level, _, _ = symbol.rpartition('.')
      try:
        return self._file_desc_protos_by_symbol[top_level]
      except KeyError:
        # Raise the original symbol as a KeyError for better diagnostics.
        raise KeyError(symbol)

  def FindFileContainingExtension(self, extendee_name, extension_number):
    # TODO: implement this API.
    return None

  def FindAllExtensionNumbers(self, extendee_name):
    # TODO: implement this API.
    return []

  def _AddSymbol(self, name, file_desc_proto):
    if name in self._file_desc_protos_by_symbol:
      warn_msg = ('Conflict register for file "' + file_desc_proto.name +
                  '": ' + name +
                  ' is already defined in file "' +
                  self._file_desc_protos_by_symbol[name].name + '"')
      warnings.warn(warn_msg, RuntimeWarning)
    self._file_desc_protos_by_symbol[name] = file_desc_proto


def _ExtractSymbols(desc_proto, package):
  """Pulls out all the symbols from a descriptor proto.

  Args:
    desc_proto: The proto to extract symbols from.
    package: The package containing the descriptor type.

  Yields:
    The fully qualified name found in the descriptor.
  """
  message_name = package + '.' + desc_proto.name if package else desc_proto.name
  yield message_name
  for nested_type in desc_proto.nested_type:
    for symbol in _ExtractSymbols(nested_type, message_name):
      yield symbol
  for enum_type in desc_proto.enum_type:
    yield '.'.join((message_name, enum_type.name))

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\aligned.py ===
# Natural Language Toolkit: Aligned Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# Author: Steven Bird <stevenbird1@gmail.com>
# For license information, see LICENSE.TXT

from nltk.corpus.reader.api import CorpusReader
from nltk.corpus.reader.util import (
    StreamBackedCorpusView,
    concat,
    read_alignedsent_block,
)
from nltk.tokenize import RegexpTokenizer, WhitespaceTokenizer
from nltk.translate import AlignedSent, Alignment


class AlignedCorpusReader(CorpusReader):
    """
    Reader for corpora of word-aligned sentences.  Tokens are assumed
    to be separated by whitespace.  Sentences begin on separate lines.
    """

    def __init__(
        self,
        root,
        fileids,
        sep="/",
        word_tokenizer=WhitespaceTokenizer(),
        sent_tokenizer=RegexpTokenizer("\n", gaps=True),
        alignedsent_block_reader=read_alignedsent_block,
        encoding="latin1",
    ):
        """
        Construct a new Aligned Corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/...path to corpus.../'
            >>> reader = AlignedCorpusReader(root, '.*', '.txt') # doctest: +SKIP

        :param root: The root directory for this corpus.
        :param fileids: A list or regexp specifying the fileids in this corpus.
        """
        CorpusReader.__init__(self, root, fileids, encoding)
        self._sep = sep
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._alignedsent_block_reader = alignedsent_block_reader

    def words(self, fileids=None):
        """
        :return: the given file(s) as a list of words
            and punctuation symbols.
        :rtype: list(str)
        """
        return concat(
            [
                AlignedSentCorpusView(
                    fileid,
                    enc,
                    False,
                    False,
                    self._word_tokenizer,
                    self._sent_tokenizer,
                    self._alignedsent_block_reader,
                )
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def sents(self, fileids=None):
        """
        :return: the given file(s) as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        :rtype: list(list(str))
        """
        return concat(
            [
                AlignedSentCorpusView(
                    fileid,
                    enc,
                    False,
                    True,
                    self._word_tokenizer,
                    self._sent_tokenizer,
                    self._alignedsent_block_reader,
                )
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def aligned_sents(self, fileids=None):
        """
        :return: the given file(s) as a list of AlignedSent objects.
        :rtype: list(AlignedSent)
        """
        return concat(
            [
                AlignedSentCorpusView(
                    fileid,
                    enc,
                    True,
                    True,
                    self._word_tokenizer,
                    self._sent_tokenizer,
                    self._alignedsent_block_reader,
                )
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )


class AlignedSentCorpusView(StreamBackedCorpusView):
    """
    A specialized corpus view for aligned sentences.
    ``AlignedSentCorpusView`` objects are typically created by
    ``AlignedCorpusReader`` (not directly by nltk users).
    """

    def __init__(
        self,
        corpus_file,
        encoding,
        aligned,
        group_by_sent,
        word_tokenizer,
        sent_tokenizer,
        alignedsent_block_reader,
    ):
        self._aligned = aligned
        self._group_by_sent = group_by_sent
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._alignedsent_block_reader = alignedsent_block_reader
        StreamBackedCorpusView.__init__(self, corpus_file, encoding=encoding)

    def read_block(self, stream):
        block = [
            self._word_tokenizer.tokenize(sent_str)
            for alignedsent_str in self._alignedsent_block_reader(stream)
            for sent_str in self._sent_tokenizer.tokenize(alignedsent_str)
        ]
        if self._aligned:
            block[2] = Alignment.fromstring(
                " ".join(block[2])
            )  # kludge; we shouldn't have tokenized the alignment string
            block = [AlignedSent(*block)]
        elif self._group_by_sent:
            block = [block[0]]
        else:
            block = block[0]

        return block

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\chasen.py ===
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Masato Hagiwara <hagisan@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import sys

from nltk.corpus.reader import util
from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *


class ChasenCorpusReader(CorpusReader):
    def __init__(self, root, fileids, encoding="utf8", sent_splitter=None):
        self._sent_splitter = sent_splitter
        CorpusReader.__init__(self, root, fileids, encoding)

    def words(self, fileids=None):
        return concat(
            [
                ChasenCorpusView(fileid, enc, False, False, False, self._sent_splitter)
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def tagged_words(self, fileids=None):
        return concat(
            [
                ChasenCorpusView(fileid, enc, True, False, False, self._sent_splitter)
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def sents(self, fileids=None):
        return concat(
            [
                ChasenCorpusView(fileid, enc, False, True, False, self._sent_splitter)
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def tagged_sents(self, fileids=None):
        return concat(
            [
                ChasenCorpusView(fileid, enc, True, True, False, self._sent_splitter)
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def paras(self, fileids=None):
        return concat(
            [
                ChasenCorpusView(fileid, enc, False, True, True, self._sent_splitter)
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def tagged_paras(self, fileids=None):
        return concat(
            [
                ChasenCorpusView(fileid, enc, True, True, True, self._sent_splitter)
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )


class ChasenCorpusView(StreamBackedCorpusView):
    """
    A specialized corpus view for ChasenReader. Similar to ``TaggedCorpusView``,
    but this'll use fixed sets of word and sentence tokenizer.
    """

    def __init__(
        self,
        corpus_file,
        encoding,
        tagged,
        group_by_sent,
        group_by_para,
        sent_splitter=None,
    ):
        self._tagged = tagged
        self._group_by_sent = group_by_sent
        self._group_by_para = group_by_para
        self._sent_splitter = sent_splitter
        StreamBackedCorpusView.__init__(self, corpus_file, encoding=encoding)

    def read_block(self, stream):
        """Reads one paragraph at a time."""
        block = []
        for para_str in read_regexp_block(stream, r".", r"^EOS\n"):
            para = []

            sent = []
            for line in para_str.splitlines():
                _eos = line.strip() == "EOS"
                _cells = line.split("\t")
                w = (_cells[0], "\t".join(_cells[1:]))
                if not _eos:
                    sent.append(w)

                if _eos or (self._sent_splitter and self._sent_splitter(w)):
                    if not self._tagged:
                        sent = [w for (w, t) in sent]
                    if self._group_by_sent:
                        para.append(sent)
                    else:
                        para.extend(sent)
                    sent = []

            if len(sent) > 0:
                if not self._tagged:
                    sent = [w for (w, t) in sent]

                if self._group_by_sent:
                    para.append(sent)
                else:
                    para.extend(sent)

            if self._group_by_para:
                block.append(para)
            else:
                block.extend(para)

        return block


def demo():
    import nltk
    from nltk.corpus.util import LazyCorpusLoader

    jeita = LazyCorpusLoader("jeita", ChasenCorpusReader, r".*chasen", encoding="utf-8")
    print("/".join(jeita.words()[22100:22140]))

    print(
        "\nEOS\n".join(
            "\n".join("{}/{}".format(w[0], w[1].split("\t")[2]) for w in sent)
            for sent in jeita.tagged_sents()[2170:2173]
        )
    )


def test():
    from nltk.corpus.util import LazyCorpusLoader

    jeita = LazyCorpusLoader("jeita", ChasenCorpusReader, r".*chasen", encoding="utf-8")

    assert isinstance(jeita.tagged_words()[0][1], str)


if __name__ == "__main__":
    demo()
    test()

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\translate\test_gdfa.py ===
"""
Tests GDFA alignments
"""

import unittest

from nltk.translate.gdfa import grow_diag_final_and


class TestGDFA(unittest.TestCase):
    def test_from_eflomal_outputs(self):
        """
        Testing GDFA with first 10 eflomal outputs from issue #1829
        https://github.com/nltk/nltk/issues/1829
        """
        # Input.
        forwards = [
            "0-0 1-2",
            "0-0 1-1",
            "0-0 2-1 3-2 4-3 5-4 6-5 7-6 8-7 7-8 9-9 10-10 9-11 11-12 12-13 13-14",
            "0-0 1-1 1-2 2-3 3-4 4-5 4-6 5-7 6-8 8-9 9-10",
            "0-0 14-1 15-2 16-3 20-5 21-6 22-7 5-8 6-9 7-10 8-11 9-12 10-13 11-14 12-15 13-16 14-17 17-18 18-19 19-20 20-21 23-22 24-23 25-24 26-25 27-27 28-28 29-29 30-30 31-31",
            "0-0 1-1 0-2 2-3",
            "0-0 2-2 4-4",
            "0-0 1-1 2-3 3-4 5-5 7-6 8-7 9-8 10-9 11-10 12-11 13-12 14-13 15-14 16-16 17-17 18-18 19-19 20-20",
            "3-0 4-1 6-2 5-3 6-4 7-5 8-6 9-7 10-8 11-9 16-10 9-12 10-13 12-14",
            "1-0",
        ]
        backwards = [
            "0-0 1-2",
            "0-0 1-1",
            "0-0 2-1 3-2 4-3 5-4 6-5 7-6 8-7 9-8 10-10 11-12 12-11 13-13",
            "0-0 1-2 2-3 3-4 4-6 6-8 7-5 8-7 9-8",
            "0-0 1-8 2-9 3-10 4-11 5-12 6-11 8-13 9-14 10-15 11-16 12-17 13-18 14-19 15-20 16-21 17-22 18-23 19-24 20-29 21-30 22-31 23-2 24-3 25-4 26-5 27-5 28-6 29-7 30-28 31-31",
            "0-0 1-1 2-3",
            "0-0 1-1 2-3 4-4",
            "0-0 1-1 2-3 3-4 5-5 7-6 8-7 9-8 10-9 11-10 12-11 13-12 14-13 15-14 16-16 17-17 18-18 19-19 20-16 21-18",
            "0-0 1-1 3-2 4-1 5-3 6-4 7-5 8-6 9-7 10-8 11-9 12-8 13-9 14-8 15-9 16-10",
            "1-0",
        ]
        source_lens = [2, 3, 3, 15, 11, 33, 4, 6, 23, 18]
        target_lens = [2, 4, 3, 16, 12, 33, 5, 6, 22, 16]
        # Expected Output.
        expected = [
            [(0, 0), (1, 2)],
            [(0, 0), (1, 1)],
            [
                (0, 0),
                (2, 1),
                (3, 2),
                (4, 3),
                (5, 4),
                (6, 5),
                (7, 6),
                (8, 7),
                (10, 10),
                (11, 12),
            ],
            [
                (0, 0),
                (1, 1),
                (1, 2),
                (2, 3),
                (3, 4),
                (4, 5),
                (4, 6),
                (5, 7),
                (6, 8),
                (7, 5),
                (8, 7),
                (8, 9),
                (9, 8),
                (9, 10),
            ],
            [
                (0, 0),
                (1, 8),
                (2, 9),
                (3, 10),
                (4, 11),
                (5, 8),
                (6, 9),
                (6, 11),
                (7, 10),
                (8, 11),
                (31, 31),
            ],
            [(0, 0), (0, 2), (1, 1), (2, 3)],
            [(0, 0), (1, 1), (2, 2), (2, 3), (4, 4)],
            [
                (0, 0),
                (1, 1),
                (2, 3),
                (3, 4),
                (5, 5),
                (7, 6),
                (8, 7),
                (9, 8),
                (10, 9),
                (11, 10),
                (12, 11),
                (13, 12),
                (14, 13),
                (15, 14),
                (16, 16),
                (17, 17),
                (18, 18),
                (19, 19),
            ],
            [
                (0, 0),
                (1, 1),
                (3, 0),
                (3, 2),
                (4, 1),
                (5, 3),
                (6, 2),
                (6, 4),
                (7, 5),
                (8, 6),
                (9, 7),
                (9, 12),
                (10, 8),
                (10, 13),
                (11, 9),
                (12, 8),
                (12, 14),
                (13, 9),
                (14, 8),
                (15, 9),
                (16, 10),
            ],
            [(1, 0)],
            [
                (0, 0),
                (1, 1),
                (3, 2),
                (4, 3),
                (5, 4),
                (6, 5),
                (7, 6),
                (9, 10),
                (10, 12),
                (11, 13),
                (12, 14),
                (13, 15),
            ],
        ]

        # Iterate through all 10 examples and check for expected outputs.
        for fw, bw, src_len, trg_len, expect in zip(
            forwards, backwards, source_lens, target_lens, expected
        ):
            self.assertListEqual(expect, grow_diag_final_and(src_len, trg_len, fw, bw))

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\formatters\irc.py ===
"""
    pygments.formatters.irc
    ~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for IRC output

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.token import Keyword, Name, Comment, String, Error, \
    Number, Operator, Generic, Token, Whitespace
from pip._vendor.pygments.util import get_choice_opt


__all__ = ['IRCFormatter']


#: Map token types to a tuple of color values for light and dark
#: backgrounds.
IRC_COLORS = {
    Token:              ('',            ''),

    Whitespace:         ('gray',   'brightblack'),
    Comment:            ('gray',   'brightblack'),
    Comment.Preproc:    ('cyan',        'brightcyan'),
    Keyword:            ('blue',    'brightblue'),
    Keyword.Type:       ('cyan',        'brightcyan'),
    Operator.Word:      ('magenta',      'brightcyan'),
    Name.Builtin:       ('cyan',        'brightcyan'),
    Name.Function:      ('green',   'brightgreen'),
    Name.Namespace:     ('_cyan_',      '_brightcyan_'),
    Name.Class:         ('_green_', '_brightgreen_'),
    Name.Exception:     ('cyan',        'brightcyan'),
    Name.Decorator:     ('brightblack',    'gray'),
    Name.Variable:      ('red',     'brightred'),
    Name.Constant:      ('red',     'brightred'),
    Name.Attribute:     ('cyan',        'brightcyan'),
    Name.Tag:           ('brightblue',        'brightblue'),
    String:             ('yellow',       'yellow'),
    Number:             ('blue',    'brightblue'),

    Generic.Deleted:    ('brightred',        'brightred'),
    Generic.Inserted:   ('green',  'brightgreen'),
    Generic.Heading:    ('**',         '**'),
    Generic.Subheading: ('*magenta*',   '*brightmagenta*'),
    Generic.Error:      ('brightred',        'brightred'),

    Error:              ('_brightred_',      '_brightred_'),
}


IRC_COLOR_MAP = {
    'white': 0,
    'black': 1,
    'blue': 2,
    'brightgreen': 3,
    'brightred': 4,
    'yellow': 5,
    'magenta': 6,
    'orange': 7,
    'green': 7, #compat w/ ansi
    'brightyellow': 8,
    'lightgreen': 9,
    'brightcyan': 9, # compat w/ ansi
    'cyan': 10,
    'lightblue': 11,
    'red': 11, # compat w/ ansi
    'brightblue': 12,
    'brightmagenta': 13,
    'brightblack': 14,
    'gray': 15,
}

def ircformat(color, text):
    if len(color) < 1:
        return text
    add = sub = ''
    if '_' in color: # italic
        add += '\x1D'
        sub = '\x1D' + sub
        color = color.strip('_')
    if '*' in color: # bold
        add += '\x02'
        sub = '\x02' + sub
        color = color.strip('*')
    # underline (\x1F) not supported
    # backgrounds (\x03FF,BB) not supported
    if len(color) > 0: # actual color - may have issues with ircformat("red", "blah")+"10" type stuff
        add += '\x03' + str(IRC_COLOR_MAP[color]).zfill(2)
        sub = '\x03' + sub
    return add + text + sub
    return '<'+add+'>'+text+'</'+sub+'>'


class IRCFormatter(Formatter):
    r"""
    Format tokens with IRC color sequences

    The `get_style_defs()` method doesn't do anything special since there is
    no support for common styles.

    Options accepted:

    `bg`
        Set to ``"light"`` or ``"dark"`` depending on the terminal's background
        (default: ``"light"``).

    `colorscheme`
        A dictionary mapping token types to (lightbg, darkbg) color names or
        ``None`` (default: ``None`` = use builtin colorscheme).

    `linenos`
        Set to ``True`` to have line numbers in the output as well
        (default: ``False`` = no line numbers).
    """
    name = 'IRC'
    aliases = ['irc', 'IRC']
    filenames = []

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.darkbg = get_choice_opt(options, 'bg',
                                     ['light', 'dark'], 'light') == 'dark'
        self.colorscheme = options.get('colorscheme', None) or IRC_COLORS
        self.linenos = options.get('linenos', False)
        self._lineno = 0

    def _write_lineno(self, outfile):
        if self.linenos:
            self._lineno += 1
            outfile.write("%04d: " % self._lineno)

    def format_unencoded(self, tokensource, outfile):
        self._write_lineno(outfile)

        for ttype, value in tokensource:
            color = self.colorscheme.get(ttype)
            while color is None:
                ttype = ttype[:-1]
                color = self.colorscheme.get(ttype)
            if color:
                color = color[self.darkbg]
                spl = value.split('\n')
                for line in spl[:-1]:
                    if line:
                        outfile.write(ircformat(color, line))
                    outfile.write('\n')
                    self._write_lineno(outfile)
                if spl[-1]:
                    outfile.write(ircformat(color, spl[-1]))
            else:
                outfile.write(value)

# === NexusCore/openenv\Lib\site-packages\pygments\formatters\irc.py ===
"""
    pygments.formatters.irc
    ~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for IRC output

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.formatter import Formatter
from pygments.token import Keyword, Name, Comment, String, Error, \
    Number, Operator, Generic, Token, Whitespace
from pygments.util import get_choice_opt


__all__ = ['IRCFormatter']


#: Map token types to a tuple of color values for light and dark
#: backgrounds.
IRC_COLORS = {
    Token:              ('',            ''),

    Whitespace:         ('gray',   'brightblack'),
    Comment:            ('gray',   'brightblack'),
    Comment.Preproc:    ('cyan',        'brightcyan'),
    Keyword:            ('blue',    'brightblue'),
    Keyword.Type:       ('cyan',        'brightcyan'),
    Operator.Word:      ('magenta',      'brightcyan'),
    Name.Builtin:       ('cyan',        'brightcyan'),
    Name.Function:      ('green',   'brightgreen'),
    Name.Namespace:     ('_cyan_',      '_brightcyan_'),
    Name.Class:         ('_green_', '_brightgreen_'),
    Name.Exception:     ('cyan',        'brightcyan'),
    Name.Decorator:     ('brightblack',    'gray'),
    Name.Variable:      ('red',     'brightred'),
    Name.Constant:      ('red',     'brightred'),
    Name.Attribute:     ('cyan',        'brightcyan'),
    Name.Tag:           ('brightblue',        'brightblue'),
    String:             ('yellow',       'yellow'),
    Number:             ('blue',    'brightblue'),

    Generic.Deleted:    ('brightred',        'brightred'),
    Generic.Inserted:   ('green',  'brightgreen'),
    Generic.Heading:    ('**',         '**'),
    Generic.Subheading: ('*magenta*',   '*brightmagenta*'),
    Generic.Error:      ('brightred',        'brightred'),

    Error:              ('_brightred_',      '_brightred_'),
}


IRC_COLOR_MAP = {
    'white': 0,
    'black': 1,
    'blue': 2,
    'brightgreen': 3,
    'brightred': 4,
    'yellow': 5,
    'magenta': 6,
    'orange': 7,
    'green': 7, #compat w/ ansi
    'brightyellow': 8,
    'lightgreen': 9,
    'brightcyan': 9, # compat w/ ansi
    'cyan': 10,
    'lightblue': 11,
    'red': 11, # compat w/ ansi
    'brightblue': 12,
    'brightmagenta': 13,
    'brightblack': 14,
    'gray': 15,
}

def ircformat(color, text):
    if len(color) < 1:
        return text
    add = sub = ''
    if '_' in color: # italic
        add += '\x1D'
        sub = '\x1D' + sub
        color = color.strip('_')
    if '*' in color: # bold
        add += '\x02'
        sub = '\x02' + sub
        color = color.strip('*')
    # underline (\x1F) not supported
    # backgrounds (\x03FF,BB) not supported
    if len(color) > 0: # actual color - may have issues with ircformat("red", "blah")+"10" type stuff
        add += '\x03' + str(IRC_COLOR_MAP[color]).zfill(2)
        sub = '\x03' + sub
    return add + text + sub
    return '<'+add+'>'+text+'</'+sub+'>'


class IRCFormatter(Formatter):
    r"""
    Format tokens with IRC color sequences

    The `get_style_defs()` method doesn't do anything special since there is
    no support for common styles.

    Options accepted:

    `bg`
        Set to ``"light"`` or ``"dark"`` depending on the terminal's background
        (default: ``"light"``).

    `colorscheme`
        A dictionary mapping token types to (lightbg, darkbg) color names or
        ``None`` (default: ``None`` = use builtin colorscheme).

    `linenos`
        Set to ``True`` to have line numbers in the output as well
        (default: ``False`` = no line numbers).
    """
    name = 'IRC'
    aliases = ['irc', 'IRC']
    filenames = []

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.darkbg = get_choice_opt(options, 'bg',
                                     ['light', 'dark'], 'light') == 'dark'
        self.colorscheme = options.get('colorscheme', None) or IRC_COLORS
        self.linenos = options.get('linenos', False)
        self._lineno = 0

    def _write_lineno(self, outfile):
        if self.linenos:
            self._lineno += 1
            outfile.write("%04d: " % self._lineno)

    def format_unencoded(self, tokensource, outfile):
        self._write_lineno(outfile)

        for ttype, value in tokensource:
            color = self.colorscheme.get(ttype)
            while color is None:
                ttype = ttype[:-1]
                color = self.colorscheme.get(ttype)
            if color:
                color = color[self.darkbg]
                spl = value.split('\n')
                for line in spl[:-1]:
                    if line:
                        outfile.write(ircformat(color, line))
                    outfile.write('\n')
                    self._write_lineno(outfile)
                if spl[-1]:
                    outfile.write(ircformat(color, spl[-1]))
            else:
                outfile.write(value)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\remote\websocket_connection.py ===
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
import json
import logging
from ssl import CERT_NONE
from threading import Thread
from time import sleep

from websocket import WebSocketApp  # type: ignore

from selenium.common import WebDriverException

logger = logging.getLogger(__name__)


class WebSocketConnection:
    _response_wait_timeout = 30
    _response_wait_interval = 0.1

    _max_log_message_size = 9999

    def __init__(self, url):
        self.callbacks = {}
        self.session_id = None
        self.url = url

        self._id = 0
        self._messages = {}
        self._started = False

        self._start_ws()
        self._wait_until(lambda: self._started)

    def close(self):
        self._ws_thread.join(timeout=self._response_wait_timeout)
        self._ws.close()
        self._started = False
        self._ws = None

    def execute(self, command):
        self._id += 1
        payload = self._serialize_command(command)
        payload["id"] = self._id
        if self.session_id:
            payload["sessionId"] = self.session_id

        data = json.dumps(payload)
        logger.debug(f"-> {data}"[: self._max_log_message_size])
        self._ws.send(data)

        current_id = self._id
        self._wait_until(lambda: current_id in self._messages)
        response = self._messages.pop(current_id)

        if "error" in response:
            error = response["error"]
            if "message" in response:
                error_msg = f"{error}: {response['message']}"
                raise WebDriverException(error_msg)
            else:
                raise WebDriverException(error)
        else:
            result = response["result"]
            return self._deserialize_result(result, command)

    def add_callback(self, event, callback):
        event_name = event.event_class
        if event_name not in self.callbacks:
            self.callbacks[event_name] = []

        def _callback(params):
            callback(event.from_json(params))

        self.callbacks[event_name].append(_callback)
        return id(_callback)

    on = add_callback

    def remove_callback(self, event, callback_id):
        event_name = event.event_class
        if event_name in self.callbacks:
            for callback in self.callbacks[event_name]:
                if id(callback) == callback_id:
                    self.callbacks[event_name].remove(callback)
                    return

    def _serialize_command(self, command):
        return next(command)

    def _deserialize_result(self, result, command):
        try:
            _ = command.send(result)
            raise WebDriverException("The command's generator function did not exit when expected!")
        except StopIteration as exit:
            return exit.value

    def _start_ws(self):
        def on_open(ws):
            self._started = True

        def on_message(ws, message):
            self._process_message(message)

        def on_error(ws, error):
            logger.debug(f"error: {error}")
            ws.close()

        def run_socket():
            if self.url.startswith("wss://"):
                self._ws.run_forever(sslopt={"cert_reqs": CERT_NONE}, suppress_origin=True)
            else:
                self._ws.run_forever(suppress_origin=True)

        self._ws = WebSocketApp(self.url, on_open=on_open, on_message=on_message, on_error=on_error)
        self._ws_thread = Thread(target=run_socket)
        self._ws_thread.start()

    def _process_message(self, message):
        message = json.loads(message)
        logger.debug(f"<- {message}"[: self._max_log_message_size])

        if "id" in message:
            self._messages[message["id"]] = message

        if "method" in message:
            params = message["params"]
            for callback in self.callbacks.get(message["method"], []):
                Thread(target=callback, args=(params,)).start()

    def _wait_until(self, condition):
        timeout = self._response_wait_timeout
        interval = self._response_wait_interval

        while timeout > 0:
            result = condition()
            if result:
                return result
            else:
                timeout -= interval
                sleep(interval)

# === NexusCore/openenv\Lib\site-packages\trio\_core\_tests\test_unbounded_queue.py ===
from __future__ import annotations

import itertools

import pytest

from ... import _core
from ...testing import assert_checkpoints, wait_all_tasks_blocked

pytestmark = pytest.mark.filterwarnings(
    "ignore:.*UnboundedQueue:trio.TrioDeprecationWarning",
)


async def test_UnboundedQueue_basic() -> None:
    q: _core.UnboundedQueue[str | int | None] = _core.UnboundedQueue()
    q.put_nowait("hi")
    assert await q.get_batch() == ["hi"]
    with pytest.raises(_core.WouldBlock):
        q.get_batch_nowait()
    q.put_nowait(1)
    q.put_nowait(2)
    q.put_nowait(3)
    assert q.get_batch_nowait() == [1, 2, 3]

    assert q.empty()
    assert q.qsize() == 0
    q.put_nowait(None)
    assert not q.empty()
    assert q.qsize() == 1

    stats = q.statistics()
    assert stats.qsize == 1
    assert stats.tasks_waiting == 0

    # smoke test
    repr(q)


async def test_UnboundedQueue_blocking() -> None:
    record = []
    q = _core.UnboundedQueue[int]()

    async def get_batch_consumer() -> None:
        while True:
            batch = await q.get_batch()
            assert batch
            record.append(batch)

    async def aiter_consumer() -> None:
        async for batch in q:
            assert batch
            record.append(batch)

    for consumer in (get_batch_consumer, aiter_consumer):
        record.clear()
        async with _core.open_nursery() as nursery:
            nursery.start_soon(consumer)
            await _core.wait_all_tasks_blocked()
            stats = q.statistics()
            assert stats.qsize == 0
            assert stats.tasks_waiting == 1
            q.put_nowait(10)
            q.put_nowait(11)
            await _core.wait_all_tasks_blocked()
            q.put_nowait(12)
            await _core.wait_all_tasks_blocked()
            assert record == [[10, 11], [12]]
            nursery.cancel_scope.cancel()


async def test_UnboundedQueue_fairness() -> None:
    q = _core.UnboundedQueue[int]()

    # If there's no-one else around, we can put stuff in and take it out
    # again, no problem
    q.put_nowait(1)
    q.put_nowait(2)
    assert q.get_batch_nowait() == [1, 2]

    result = None

    async def get_batch(q: _core.UnboundedQueue[int]) -> None:
        nonlocal result
        result = await q.get_batch()

    # But if someone else is waiting to read, then they get dibs
    async with _core.open_nursery() as nursery:
        nursery.start_soon(get_batch, q)
        await _core.wait_all_tasks_blocked()
        q.put_nowait(3)
        q.put_nowait(4)
        with pytest.raises(_core.WouldBlock):
            q.get_batch_nowait()
    assert result == [3, 4]

    # If two tasks are trying to read, they alternate
    record = []

    async def reader(name: str) -> None:
        while True:
            record.append((name, await q.get_batch()))

    async with _core.open_nursery() as nursery:
        nursery.start_soon(reader, "a")
        await _core.wait_all_tasks_blocked()
        nursery.start_soon(reader, "b")
        await _core.wait_all_tasks_blocked()

        for i in range(20):
            q.put_nowait(i)
            await _core.wait_all_tasks_blocked()

        nursery.cancel_scope.cancel()

    assert record == list(zip(itertools.cycle("ab"), [[i] for i in range(20)]))


async def test_UnboundedQueue_trivial_yields() -> None:
    q = _core.UnboundedQueue[None]()

    q.put_nowait(None)
    with assert_checkpoints():
        await q.get_batch()

    q.put_nowait(None)
    with assert_checkpoints():
        async for _ in q:  # pragma: no branch
            break


async def test_UnboundedQueue_no_spurious_wakeups() -> None:
    # If we have two tasks waiting, and put two items into the queue... then
    # only one task wakes up
    record = []

    async def getter(q: _core.UnboundedQueue[int], i: int) -> None:
        got = await q.get_batch()
        record.append((i, got))

    async with _core.open_nursery() as nursery:
        q = _core.UnboundedQueue[int]()
        nursery.start_soon(getter, q, 1)
        await wait_all_tasks_blocked()
        nursery.start_soon(getter, q, 2)
        await wait_all_tasks_blocked()

        for i in range(10):
            q.put_nowait(i)
        await wait_all_tasks_blocked()

        assert record == [(1, list(range(10)))]

        nursery.cancel_scope.cancel()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\unistring.py ===
"""
    pygments.unistring
    ~~~~~~~~~~~~~~~~~~

    Strings of all Unicode characters of a certain category.
    Used for matching in Unicode-aware languages. Run to regenerate.

    Inspired by chartypes_create.py from the MoinMoin project.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

Cc = '\x00-\x1f\x7f-\x9f'

Cf = '\xad\u0600-\u0605\u061c\u06dd\u070f\u08e2\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u206f\ufeff\ufff9-\ufffb\U000110bd\U000110cd\U0001bca0-\U0001bca3\U0001d173-\U0001d17a\U000e0001\U000e0020-\U000e007f'

Cn = '\u0378-\u0379\u0380-\u0383\u038b\u038d\u03a2\u0530\u0557-\u0558\u058b-\u058c\u0590\u05c8-\u05cf\u05eb-\u05ee\u05f5-\u05ff\u061d\u070e\u074b-\u074c\u07b2-\u07bf\u07fb-\u07fc\u082e-\u082f\u083f\u085c-\u085d\u085f\u086b-\u089f\u08b5\u08be-\u08d2\u0984\u098d-\u098e\u0991-\u0992\u09a9\u09b1\u09b3-\u09b5\u09ba-\u09bb\u09c5-\u09c6\u09c9-\u09ca\u09cf-\u09d6\u09d8-\u09db\u09de\u09e4-\u09e5\u09ff-\u0a00\u0a04\u0a0b-\u0a0e\u0a11-\u0a12\u0a29\u0a31\u0a34\u0a37\u0a3a-\u0a3b\u0a3d\u0a43-\u0a46\u0a49-\u0a4a\u0a4e-\u0a50\u0a52-\u0a58\u0a5d\u0a5f-\u0a65\u0a77-\u0a80\u0a84\u0a8e\u0a92\u0aa9\u0ab1\u0ab4\u0aba-\u0abb\u0ac6\u0aca\u0ace-\u0acf\u0ad1-\u0adf\u0ae4-\u0ae5\u0af2-\u0af8\u0b00\u0b04\u0b0d-\u0b0e\u0b11-\u0b12\u0b29\u0b31\u0b34\u0b3a-\u0b3b\u0b45-\u0b46\u0b49-\u0b4a\u0b4e-\u0b55\u0b58-\u0b5b\u0b5e\u0b64-\u0b65\u0b78-\u0b81\u0b84\u0b8b-\u0b8d\u0b91\u0b96-\u0b98\u0b9b\u0b9d\u0ba0-\u0ba2\u0ba5-\u0ba7\u0bab-\u0bad\u0bba-\u0bbd\u0bc3-\u0bc5\u0bc9\u0bce-\u0bcf\u0bd1-\u0bd6\u0bd8-\u0be5\u0bfb-\u0bff\u0c0d\u0c11\u0c29\u0c3a-\u0c3c\u0c45\u0c49\u0c4e-\u0c54\u0c57\u0c5b-\u0c5f\u0c64-\u0c65\u0c70-\u0c77\u0c8d\u0c91\u0ca9\u0cb4\u0cba-\u0cbb\u0cc5\u0cc9\u0cce-\u0cd4\u0cd7-\u0cdd\u0cdf\u0ce4-\u0ce5\u0cf0\u0cf3-\u0cff\u0d04\u0d0d\u0d11\u0d45\u0d49\u0d50-\u0d53\u0d64-\u0d65\u0d80-\u0d81\u0d84\u0d97-\u0d99\u0db2\u0dbc\u0dbe-\u0dbf\u0dc7-\u0dc9\u0dcb-\u0dce\u0dd5\u0dd7\u0de0-\u0de5\u0df0-\u0df1\u0df5-\u0e00\u0e3b-\u0e3e\u0e5c-\u0e80\u0e83\u0e85-\u0e86\u0e89\u0e8b-\u0e8c\u0e8e-\u0e93\u0e98\u0ea0\u0ea4\u0ea6\u0ea8-\u0ea9\u0eac\u0eba\u0ebe-\u0ebf\u0ec5\u0ec7\u0ece-\u0ecf\u0eda-\u0edb\u0ee0-\u0eff\u0f48\u0f6d-\u0f70\u0f98\u0fbd\u0fcd\u0fdb-\u0fff\u10c6\u10c8-\u10cc\u10ce-\u10cf\u1249\u124e-\u124f\u1257\u1259\u125e-\u125f\u1289\u128e-\u128f\u12b1\u12b6-\u12b7\u12bf\u12c1\u12c6-\u12c7\u12d7\u1311\u1316-\u1317\u135b-\u135c\u137d-\u137f\u139a-\u139f\u13f6-\u13f7\u13fe-\u13ff\u169d-\u169f\u16f9-\u16ff\u170d\u1715-\u171f\u1737-\u173f\u1754-\u175f\u176d\u1771\u1774-\u177f\u17de-\u17df\u17ea-\u17ef\u17fa-\u17ff\u180f\u181a-\u181f\u1879-\u187f\u18ab-\u18af\u18f6-\u18ff\u191f\u192c-\u192f\u193c-\u193f\u1941-\u1943\u196e-\u196f\u1975-\u197f\u19ac-\u19af\u19ca-\u19cf\u19db-\u19dd\u1a1c-\u1a1d\u1a5f\u1a7d-\u1a7e\u1a8a-\u1a8f\u1a9a-\u1a9f\u1aae-\u1aaf\u1abf-\u1aff\u1b4c-\u1b4f\u1b7d-\u1b7f\u1bf4-\u1bfb\u1c38-\u1c3a\u1c4a-\u1c4c\u1c89-\u1c8f\u1cbb-\u1cbc\u1cc8-\u1ccf\u1cfa-\u1cff\u1dfa\u1f16-\u1f17\u1f1e-\u1f1f\u1f46-\u1f47\u1f4e-\u1f4f\u1f58\u1f5a\u1f5c\u1f5e\u1f7e-\u1f7f\u1fb5\u1fc5\u1fd4-\u1fd5\u1fdc\u1ff0-\u1ff1\u1ff5\u1fff\u2065\u2072-\u2073\u208f\u209d-\u209f\u20c0-\u20cf\u20f1-\u20ff\u218c-\u218f\u2427-\u243f\u244b-\u245f\u2b74-\u2b75\u2b96-\u2b97\u2bc9\u2bff\u2c2f\u2c5f\u2cf4-\u2cf8\u2d26\u2d28-\u2d2c\u2d2e-\u2d2f\u2d68-\u2d6e\u2d71-\u2d7e\u2d97-\u2d9f\u2da7\u2daf\u2db7\u2dbf\u2dc7\u2dcf\u2dd7\u2ddf\u2e4f-\u2e7f\u2e9a\u2ef4-\u2eff\u2fd6-\u2fef\u2ffc-\u2fff\u3040\u3097-\u3098\u3100-\u3104\u3130\u318f\u31bb-\u31bf\u31e4-\u31ef\u321f\u32ff\u4db6-\u4dbf\u9ff0-\u9fff\ua48d-\ua48f\ua4c7-\ua4cf\ua62c-\ua63f\ua6f8-\ua6ff\ua7ba-\ua7f6\ua82c-\ua82f\ua83a-\ua83f\ua878-\ua87f\ua8c6-\ua8cd\ua8da-\ua8df\ua954-\ua95e\ua97d-\ua97f\ua9ce\ua9da-\ua9dd\ua9ff\uaa37-\uaa3f\uaa4e-\uaa4f\uaa5a-\uaa5b\uaac3-\uaada\uaaf7-\uab00\uab07-\uab08\uab0f-\uab10\uab17-\uab1f\uab27\uab2f\uab66-\uab6f\uabee-\uabef\uabfa-\uabff\ud7a4-\ud7af\ud7c7-\ud7ca\ud7fc-\ud7ff\ufa6e-\ufa6f\ufada-\ufaff\ufb07-\ufb12\ufb18-\ufb1c\ufb37\ufb3d\ufb3f\ufb42\ufb45\ufbc2-\ufbd2\ufd40-\ufd4f\ufd90-\ufd91\ufdc8-\ufdef\ufdfe-\ufdff\ufe1a-\ufe1f\ufe53\ufe67\ufe6c-\ufe6f\ufe75\ufefd-\ufefe\uff00\uffbf-\uffc1\uffc8-\uffc9\uffd0-\uffd1\uffd8-\uffd9\uffdd-\uffdf\uffe7\uffef-\ufff8\ufffe-\uffff\U0001000c\U00010027\U0001003b\U0001003e\U0001004e-\U0001004f\U0001005e-\U0001007f\U000100fb-\U000100ff\U00010103-\U00010106\U00010134-\U00010136\U0001018f\U0001019c-\U0001019f\U000101a1-\U000101cf\U000101fe-\U0001027f\U0001029d-\U0001029f\U000102d1-\U000102df\U000102fc-\U000102ff\U00010324-\U0001032c\U0001034b-\U0001034f\U0001037b-\U0001037f\U0001039e\U000103c4-\U000103c7\U000103d6-\U000103ff\U0001049e-\U0001049f\U000104aa-\U000104af\U000104d4-\U000104d7\U000104fc-\U000104ff\U00010528-\U0001052f\U00010564-\U0001056e\U00010570-\U000105ff\U00010737-\U0001073f\U00010756-\U0001075f\U00010768-\U000107ff\U00010806-\U00010807\U00010809\U00010836\U00010839-\U0001083b\U0001083d-\U0001083e\U00010856\U0001089f-\U000108a6\U000108b0-\U000108df\U000108f3\U000108f6-\U000108fa\U0001091c-\U0001091e\U0001093a-\U0001093e\U00010940-\U0001097f\U000109b8-\U000109bb\U000109d0-\U000109d1\U00010a04\U00010a07-\U00010a0b\U00010a14\U00010a18\U00010a36-\U00010a37\U00010a3b-\U00010a3e\U00010a49-\U00010a4f\U00010a59-\U00010a5f\U00010aa0-\U00010abf\U00010ae7-\U00010aea\U00010af7-\U00010aff\U00010b36-\U00010b38\U00010b56-\U00010b57\U00010b73-\U00010b77\U00010b92-\U00010b98\U00010b9d-\U00010ba8\U00010bb0-\U00010bff\U00010c49-\U00010c7f\U00010cb3-\U00010cbf\U00010cf3-\U00010cf9\U00010d28-\U00010d2f\U00010d3a-\U00010e5f\U00010e7f-\U00010eff\U00010f28-\U00010f2f\U00010f5a-\U00010fff\U0001104e-\U00011051\U00011070-\U0001107e\U000110c2-\U000110cc\U000110ce-\U000110cf\U000110e9-\U000110ef\U000110fa-\U000110ff\U00011135\U00011147-\U0001114f\U00011177-\U0001117f\U000111ce-\U000111cf\U000111e0\U000111f5-\U000111ff\U00011212\U0001123f-\U0001127f\U00011287\U00011289\U0001128e\U0001129e\U000112aa-\U000112af\U000112eb-\U000112ef\U000112fa-\U000112ff\U00011304\U0001130d-\U0001130e\U00011311-\U00011312\U00011329\U00011331\U00011334\U0001133a\U00011345-\U00011346\U00011349-\U0001134a\U0001134e-\U0001134f\U00011351-\U00011356\U00011358-\U0001135c\U00011364-\U00011365\U0001136d-\U0001136f\U00011375-\U000113ff\U0001145a\U0001145c\U0001145f-\U0001147f\U000114c8-\U000114cf\U000114da-\U0001157f\U000115b6-\U000115b7\U000115de-\U000115ff\U00011645-\U0001164f\U0001165a-\U0001165f\U0001166d-\U0001167f\U000116b8-\U000116bf\U000116ca-\U000116ff\U0001171b-\U0001171c\U0001172c-\U0001172f\U00011740-\U000117ff\U0001183c-\U0001189f\U000118f3-\U000118fe\U00011900-\U000119ff\U00011a48-\U00011a4f\U00011a84-\U00011a85\U00011aa3-\U00011abf\U00011af9-\U00011bff\U00011c09\U00011c37\U00011c46-\U00011c4f\U00011c6d-\U00011c6f\U00011c90-\U00011c91\U00011ca8\U00011cb7-\U00011cff\U00011d07\U00011d0a\U00011d37-\U00011d39\U00011d3b\U00011d3e\U00011d48-\U00011d4f\U00011d5a-\U00011d5f\U00011d66\U00011d69\U00011d8f\U00011d92\U00011d99-\U00011d9f\U00011daa-\U00011edf\U00011ef9-\U00011fff\U0001239a-\U000123ff\U0001246f\U00012475-\U0001247f\U00012544-\U00012fff\U0001342f-\U000143ff\U00014647-\U000167ff\U00016a39-\U00016a3f\U00016a5f\U00016a6a-\U00016a6d\U00016a70-\U00016acf\U00016aee-\U00016aef\U00016af6-\U00016aff\U00016b46-\U00016b4f\U00016b5a\U00016b62\U00016b78-\U00016b7c\U00016b90-\U00016e3f\U00016e9b-\U00016eff\U00016f45-\U00016f4f\U00016f7f-\U00016f8e\U00016fa0-\U00016fdf\U00016fe2-\U00016fff\U000187f2-\U000187ff\U00018af3-\U0001afff\U0001b11f-\U0001b16f\U0001b2fc-\U0001bbff\U0001bc6b-\U0001bc6f\U0001bc7d-\U0001bc7f\U0001bc89-\U0001bc8f\U0001bc9a-\U0001bc9b\U0001bca4-\U0001cfff\U0001d0f6-\U0001d0ff\U0001d127-\U0001d128\U0001d1e9-\U0001d1ff\U0001d246-\U0001d2df\U0001d2f4-\U0001d2ff\U0001d357-\U0001d35f\U0001d379-\U0001d3ff\U0001d455\U0001d49d\U0001d4a0-\U0001d4a1\U0001d4a3-\U0001d4a4\U0001d4a7-\U0001d4a8\U0001d4ad\U0001d4ba\U0001d4bc\U0001d4c4\U0001d506\U0001d50b-\U0001d50c\U0001d515\U0001d51d\U0001d53a\U0001d53f\U0001d545\U0001d547-\U0001d549\U0001d551\U0001d6a6-\U0001d6a7\U0001d7cc-\U0001d7cd\U0001da8c-\U0001da9a\U0001daa0\U0001dab0-\U0001dfff\U0001e007\U0001e019-\U0001e01a\U0001e022\U0001e025\U0001e02b-\U0001e7ff\U0001e8c5-\U0001e8c6\U0001e8d7-\U0001e8ff\U0001e94b-\U0001e94f\U0001e95a-\U0001e95d\U0001e960-\U0001ec70\U0001ecb5-\U0001edff\U0001ee04\U0001ee20\U0001ee23\U0001ee25-\U0001ee26\U0001ee28\U0001ee33\U0001ee38\U0001ee3a\U0001ee3c-\U0001ee41\U0001ee43-\U0001ee46\U0001ee48\U0001ee4a\U0001ee4c\U0001ee50\U0001ee53\U0001ee55-\U0001ee56\U0001ee58\U0001ee5a\U0001ee5c\U0001ee5e\U0001ee60\U0001ee63\U0001ee65-\U0001ee66\U0001ee6b\U0001ee73\U0001ee78\U0001ee7d\U0001ee7f\U0001ee8a\U0001ee9c-\U0001eea0\U0001eea4\U0001eeaa\U0001eebc-\U0001eeef\U0001eef2-\U0001efff\U0001f02c-\U0001f02f\U0001f094-\U0001f09f\U0001f0af-\U0001f0b0\U0001f0c0\U0001f0d0\U0001f0f6-\U0001f0ff\U0001f10d-\U0001f10f\U0001f16c-\U0001f16f\U0001f1ad-\U0001f1e5\U0001f203-\U0001f20f\U0001f23c-\U0001f23f\U0001f249-\U0001f24f\U0001f252-\U0001f25f\U0001f266-\U0001f2ff\U0001f6d5-\U0001f6df\U0001f6ed-\U0001f6ef\U0001f6fa-\U0001f6ff\U0001f774-\U0001f77f\U0001f7d9-\U0001f7ff\U0001f80c-\U0001f80f\U0001f848-\U0001f84f\U0001f85a-\U0001f85f\U0001f888-\U0001f88f\U0001f8ae-\U0001f8ff\U0001f90c-\U0001f90f\U0001f93f\U0001f971-\U0001f972\U0001f977-\U0001f979\U0001f97b\U0001f9a3-\U0001f9af\U0001f9ba-\U0001f9bf\U0001f9c3-\U0001f9cf\U0001fa00-\U0001fa5f\U0001fa6e-\U0001ffff\U0002a6d7-\U0002a6ff\U0002b735-\U0002b73f\U0002b81e-\U0002b81f\U0002cea2-\U0002ceaf\U0002ebe1-\U0002f7ff\U0002fa1e-\U000e0000\U000e0002-\U000e001f\U000e0080-\U000e00ff\U000e01f0-\U000effff\U000ffffe-\U000fffff\U0010fffe-\U0010ffff'

Co = '\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd'

Cs = '\ud800-\udbff\\\udc00\udc01-\udfff'

Ll = 'a-z\xb5\xdf-\xf6\xf8-\xff\u0101\u0103\u0105\u0107\u0109\u010b\u010d\u010f\u0111\u0113\u0115\u0117\u0119\u011b\u011d\u011f\u0121\u0123\u0125\u0127\u0129\u012b\u012d\u012f\u0131\u0133\u0135\u0137-\u0138\u013a\u013c\u013e\u0140\u0142\u0144\u0146\u0148-\u0149\u014b\u014d\u014f\u0151\u0153\u0155\u0157\u0159\u015b\u015d\u015f\u0161\u0163\u0165\u0167\u0169\u016b\u016d\u016f\u0171\u0173\u0175\u0177\u017a\u017c\u017e-\u0180\u0183\u0185\u0188\u018c-\u018d\u0192\u0195\u0199-\u019b\u019e\u01a1\u01a3\u01a5\u01a8\u01aa-\u01ab\u01ad\u01b0\u01b4\u01b6\u01b9-\u01ba\u01bd-\u01bf\u01c6\u01c9\u01cc\u01ce\u01d0\u01d2\u01d4\u01d6\u01d8\u01da\u01dc-\u01dd\u01df\u01e1\u01e3\u01e5\u01e7\u01e9\u01eb\u01ed\u01ef-\u01f0\u01f3\u01f5\u01f9\u01fb\u01fd\u01ff\u0201\u0203\u0205\u0207\u0209\u020b\u020d\u020f\u0211\u0213\u0215\u0217\u0219\u021b\u021d\u021f\u0221\u0223\u0225\u0227\u0229\u022b\u022d\u022f\u0231\u0233-\u0239\u023c\u023f-\u0240\u0242\u0247\u0249\u024b\u024d\u024f-\u0293\u0295-\u02af\u0371\u0373\u0377\u037b-\u037d\u0390\u03ac-\u03ce\u03d0-\u03d1\u03d5-\u03d7\u03d9\u03db\u03dd\u03df\u03e1\u03e3\u03e5\u03e7\u03e9\u03eb\u03ed\u03ef-\u03f3\u03f5\u03f8\u03fb-\u03fc\u0430-\u045f\u0461\u0463\u0465\u0467\u0469\u046b\u046d\u046f\u0471\u0473\u0475\u0477\u0479\u047b\u047d\u047f\u0481\u048b\u048d\u048f\u0491\u0493\u0495\u0497\u0499\u049b\u049d\u049f\u04a1\u04a3\u04a5\u04a7\u04a9\u04ab\u04ad\u04af\u04b1\u04b3\u04b5\u04b7\u04b9\u04bb\u04bd\u04bf\u04c2\u04c4\u04c6\u04c8\u04ca\u04cc\u04ce-\u04cf\u04d1\u04d3\u04d5\u04d7\u04d9\u04db\u04dd\u04df\u04e1\u04e3\u04e5\u04e7\u04e9\u04eb\u04ed\u04ef\u04f1\u04f3\u04f5\u04f7\u04f9\u04fb\u04fd\u04ff\u0501\u0503\u0505\u0507\u0509\u050b\u050d\u050f\u0511\u0513\u0515\u0517\u0519\u051b\u051d\u051f\u0521\u0523\u0525\u0527\u0529\u052b\u052d\u052f\u0560-\u0588\u10d0-\u10fa\u10fd-\u10ff\u13f8-\u13fd\u1c80-\u1c88\u1d00-\u1d2b\u1d6b-\u1d77\u1d79-\u1d9a\u1e01\u1e03\u1e05\u1e07\u1e09\u1e0b\u1e0d\u1e0f\u1e11\u1e13\u1e15\u1e17\u1e19\u1e1b\u1e1d\u1e1f\u1e21\u1e23\u1e25\u1e27\u1e29\u1e2b\u1e2d\u1e2f\u1e31\u1e33\u1e35\u1e37\u1e39\u1e3b\u1e3d\u1e3f\u1e41\u1e43\u1e45\u1e47\u1e49\u1e4b\u1e4d\u1e4f\u1e51\u1e53\u1e55\u1e57\u1e59\u1e5b\u1e5d\u1e5f\u1e61\u1e63\u1e65\u1e67\u1e69\u1e6b\u1e6d\u1e6f\u1e71\u1e73\u1e75\u1e77\u1e79\u1e7b\u1e7d\u1e7f\u1e81\u1e83\u1e85\u1e87\u1e89\u1e8b\u1e8d\u1e8f\u1e91\u1e93\u1e95-\u1e9d\u1e9f\u1ea1\u1ea3\u1ea5\u1ea7\u1ea9\u1eab\u1ead\u1eaf\u1eb1\u1eb3\u1eb5\u1eb7\u1eb9\u1ebb\u1ebd\u1ebf\u1ec1\u1ec3\u1ec5\u1ec7\u1ec9\u1ecb\u1ecd\u1ecf\u1ed1\u1ed3\u1ed5\u1ed7\u1ed9\u1edb\u1edd\u1edf\u1ee1\u1ee3\u1ee5\u1ee7\u1ee9\u1eeb\u1eed\u1eef\u1ef1\u1ef3\u1ef5\u1ef7\u1ef9\u1efb\u1efd\u1eff-\u1f07\u1f10-\u1f15\u1f20-\u1f27\u1f30-\u1f37\u1f40-\u1f45\u1f50-\u1f57\u1f60-\u1f67\u1f70-\u1f7d\u1f80-\u1f87\u1f90-\u1f97\u1fa0-\u1fa7\u1fb0-\u1fb4\u1fb6-\u1fb7\u1fbe\u1fc2-\u1fc4\u1fc6-\u1fc7\u1fd0-\u1fd3\u1fd6-\u1fd7\u1fe0-\u1fe7\u1ff2-\u1ff4\u1ff6-\u1ff7\u210a\u210e-\u210f\u2113\u212f\u2134\u2139\u213c-\u213d\u2146-\u2149\u214e\u2184\u2c30-\u2c5e\u2c61\u2c65-\u2c66\u2c68\u2c6a\u2c6c\u2c71\u2c73-\u2c74\u2c76-\u2c7b\u2c81\u2c83\u2c85\u2c87\u2c89\u2c8b\u2c8d\u2c8f\u2c91\u2c93\u2c95\u2c97\u2c99\u2c9b\u2c9d\u2c9f\u2ca1\u2ca3\u2ca5\u2ca7\u2ca9\u2cab\u2cad\u2caf\u2cb1\u2cb3\u2cb5\u2cb7\u2cb9\u2cbb\u2cbd\u2cbf\u2cc1\u2cc3\u2cc5\u2cc7\u2cc9\u2ccb\u2ccd\u2ccf\u2cd1\u2cd3\u2cd5\u2cd7\u2cd9\u2cdb\u2cdd\u2cdf\u2ce1\u2ce3-\u2ce4\u2cec\u2cee\u2cf3\u2d00-\u2d25\u2d27\u2d2d\ua641\ua643\ua645\ua647\ua649\ua64b\ua64d\ua64f\ua651\ua653\ua655\ua657\ua659\ua65b\ua65d\ua65f\ua661\ua663\ua665\ua667\ua669\ua66b\ua66d\ua681\ua683\ua685\ua687\ua689\ua68b\ua68d\ua68f\ua691\ua693\ua695\ua697\ua699\ua69b\ua723\ua725\ua727\ua729\ua72b\ua72d\ua72f-\ua731\ua733\ua735\ua737\ua739\ua73b\ua73d\ua73f\ua741\ua743\ua745\ua747\ua749\ua74b\ua74d\ua74f\ua751\ua753\ua755\ua757\ua759\ua75b\ua75d\ua75f\ua761\ua763\ua765\ua767\ua769\ua76b\ua76d\ua76f\ua771-\ua778\ua77a\ua77c\ua77f\ua781\ua783\ua785\ua787\ua78c\ua78e\ua791\ua793-\ua795\ua797\ua799\ua79b\ua79d\ua79f\ua7a1\ua7a3\ua7a5\ua7a7\ua7a9\ua7af\ua7b5\ua7b7\ua7b9\ua7fa\uab30-\uab5a\uab60-\uab65\uab70-\uabbf\ufb00-\ufb06\ufb13-\ufb17\uff41-\uff5a\U00010428-\U0001044f\U000104d8-\U000104fb\U00010cc0-\U00010cf2\U000118c0-\U000118df\U00016e60-\U00016e7f\U0001d41a-\U0001d433\U0001d44e-\U0001d454\U0001d456-\U0001d467\U0001d482-\U0001d49b\U0001d4b6-\U0001d4b9\U0001d4bb\U0001d4bd-\U0001d4c3\U0001d4c5-\U0001d4cf\U0001d4ea-\U0001d503\U0001d51e-\U0001d537\U0001d552-\U0001d56b\U0001d586-\U0001d59f\U0001d5ba-\U0001d5d3\U0001d5ee-\U0001d607\U0001d622-\U0001d63b\U0001d656-\U0001d66f\U0001d68a-\U0001d6a5\U0001d6c2-\U0001d6da\U0001d6dc-\U0001d6e1\U0001d6fc-\U0001d714\U0001d716-\U0001d71b\U0001d736-\U0001d74e\U0001d750-\U0001d755\U0001d770-\U0001d788\U0001d78a-\U0001d78f\U0001d7aa-\U0001d7c2\U0001d7c4-\U0001d7c9\U0001d7cb\U0001e922-\U0001e943'

Lm = '\u02b0-\u02c1\u02c6-\u02d1\u02e0-\u02e4\u02ec\u02ee\u0374\u037a\u0559\u0640\u06e5-\u06e6\u07f4-\u07f5\u07fa\u081a\u0824\u0828\u0971\u0e46\u0ec6\u10fc\u17d7\u1843\u1aa7\u1c78-\u1c7d\u1d2c-\u1d6a\u1d78\u1d9b-\u1dbf\u2071\u207f\u2090-\u209c\u2c7c-\u2c7d\u2d6f\u2e2f\u3005\u3031-\u3035\u303b\u309d-\u309e\u30fc-\u30fe\ua015\ua4f8-\ua4fd\ua60c\ua67f\ua69c-\ua69d\ua717-\ua71f\ua770\ua788\ua7f8-\ua7f9\ua9cf\ua9e6\uaa70\uaadd\uaaf3-\uaaf4\uab5c-\uab5f\uff70\uff9e-\uff9f\U00016b40-\U00016b43\U00016f93-\U00016f9f\U00016fe0-\U00016fe1'

Lo = '\xaa\xba\u01bb\u01c0-\u01c3\u0294\u05d0-\u05ea\u05ef-\u05f2\u0620-\u063f\u0641-\u064a\u066e-\u066f\u0671-\u06d3\u06d5\u06ee-\u06ef\u06fa-\u06fc\u06ff\u0710\u0712-\u072f\u074d-\u07a5\u07b1\u07ca-\u07ea\u0800-\u0815\u0840-\u0858\u0860-\u086a\u08a0-\u08b4\u08b6-\u08bd\u0904-\u0939\u093d\u0950\u0958-\u0961\u0972-\u0980\u0985-\u098c\u098f-\u0990\u0993-\u09a8\u09aa-\u09b0\u09b2\u09b6-\u09b9\u09bd\u09ce\u09dc-\u09dd\u09df-\u09e1\u09f0-\u09f1\u09fc\u0a05-\u0a0a\u0a0f-\u0a10\u0a13-\u0a28\u0a2a-\u0a30\u0a32-\u0a33\u0a35-\u0a36\u0a38-\u0a39\u0a59-\u0a5c\u0a5e\u0a72-\u0a74\u0a85-\u0a8d\u0a8f-\u0a91\u0a93-\u0aa8\u0aaa-\u0ab0\u0ab2-\u0ab3\u0ab5-\u0ab9\u0abd\u0ad0\u0ae0-\u0ae1\u0af9\u0b05-\u0b0c\u0b0f-\u0b10\u0b13-\u0b28\u0b2a-\u0b30\u0b32-\u0b33\u0b35-\u0b39\u0b3d\u0b5c-\u0b5d\u0b5f-\u0b61\u0b71\u0b83\u0b85-\u0b8a\u0b8e-\u0b90\u0b92-\u0b95\u0b99-\u0b9a\u0b9c\u0b9e-\u0b9f\u0ba3-\u0ba4\u0ba8-\u0baa\u0bae-\u0bb9\u0bd0\u0c05-\u0c0c\u0c0e-\u0c10\u0c12-\u0c28\u0c2a-\u0c39\u0c3d\u0c58-\u0c5a\u0c60-\u0c61\u0c80\u0c85-\u0c8c\u0c8e-\u0c90\u0c92-\u0ca8\u0caa-\u0cb3\u0cb5-\u0cb9\u0cbd\u0cde\u0ce0-\u0ce1\u0cf1-\u0cf2\u0d05-\u0d0c\u0d0e-\u0d10\u0d12-\u0d3a\u0d3d\u0d4e\u0d54-\u0d56\u0d5f-\u0d61\u0d7a-\u0d7f\u0d85-\u0d96\u0d9a-\u0db1\u0db3-\u0dbb\u0dbd\u0dc0-\u0dc6\u0e01-\u0e30\u0e32-\u0e33\u0e40-\u0e45\u0e81-\u0e82\u0e84\u0e87-\u0e88\u0e8a\u0e8d\u0e94-\u0e97\u0e99-\u0e9f\u0ea1-\u0ea3\u0ea5\u0ea7\u0eaa-\u0eab\u0ead-\u0eb0\u0eb2-\u0eb3\u0ebd\u0ec0-\u0ec4\u0edc-\u0edf\u0f00\u0f40-\u0f47\u0f49-\u0f6c\u0f88-\u0f8c\u1000-\u102a\u103f\u1050-\u1055\u105a-\u105d\u1061\u1065-\u1066\u106e-\u1070\u1075-\u1081\u108e\u1100-\u1248\u124a-\u124d\u1250-\u1256\u1258\u125a-\u125d\u1260-\u1288\u128a-\u128d\u1290-\u12b0\u12b2-\u12b5\u12b8-\u12be\u12c0\u12c2-\u12c5\u12c8-\u12d6\u12d8-\u1310\u1312-\u1315\u1318-\u135a\u1380-\u138f\u1401-\u166c\u166f-\u167f\u1681-\u169a\u16a0-\u16ea\u16f1-\u16f8\u1700-\u170c\u170e-\u1711\u1720-\u1731\u1740-\u1751\u1760-\u176c\u176e-\u1770\u1780-\u17b3\u17dc\u1820-\u1842\u1844-\u1878\u1880-\u1884\u1887-\u18a8\u18aa\u18b0-\u18f5\u1900-\u191e\u1950-\u196d\u1970-\u1974\u1980-\u19ab\u19b0-\u19c9\u1a00-\u1a16\u1a20-\u1a54\u1b05-\u1b33\u1b45-\u1b4b\u1b83-\u1ba0\u1bae-\u1baf\u1bba-\u1be5\u1c00-\u1c23\u1c4d-\u1c4f\u1c5a-\u1c77\u1ce9-\u1cec\u1cee-\u1cf1\u1cf5-\u1cf6\u2135-\u2138\u2d30-\u2d67\u2d80-\u2d96\u2da0-\u2da6\u2da8-\u2dae\u2db0-\u2db6\u2db8-\u2dbe\u2dc0-\u2dc6\u2dc8-\u2dce\u2dd0-\u2dd6\u2dd8-\u2dde\u3006\u303c\u3041-\u3096\u309f\u30a1-\u30fa\u30ff\u3105-\u312f\u3131-\u318e\u31a0-\u31ba\u31f0-\u31ff\u3400-\u4db5\u4e00-\u9fef\ua000-\ua014\ua016-\ua48c\ua4d0-\ua4f7\ua500-\ua60b\ua610-\ua61f\ua62a-\ua62b\ua66e\ua6a0-\ua6e5\ua78f\ua7f7\ua7fb-\ua801\ua803-\ua805\ua807-\ua80a\ua80c-\ua822\ua840-\ua873\ua882-\ua8b3\ua8f2-\ua8f7\ua8fb\ua8fd-\ua8fe\ua90a-\ua925\ua930-\ua946\ua960-\ua97c\ua984-\ua9b2\ua9e0-\ua9e4\ua9e7-\ua9ef\ua9fa-\ua9fe\uaa00-\uaa28\uaa40-\uaa42\uaa44-\uaa4b\uaa60-\uaa6f\uaa71-\uaa76\uaa7a\uaa7e-\uaaaf\uaab1\uaab5-\uaab6\uaab9-\uaabd\uaac0\uaac2\uaadb-\uaadc\uaae0-\uaaea\uaaf2\uab01-\uab06\uab09-\uab0e\uab11-\uab16\uab20-\uab26\uab28-\uab2e\uabc0-\uabe2\uac00-\ud7a3\ud7b0-\ud7c6\ud7cb-\ud7fb\uf900-\ufa6d\ufa70-\ufad9\ufb1d\ufb1f-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufbb1\ufbd3-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdfb\ufe70-\ufe74\ufe76-\ufefc\uff66-\uff6f\uff71-\uff9d\uffa0-\uffbe\uffc2-\uffc7\uffca-\uffcf\uffd2-\uffd7\uffda-\uffdc\U00010000-\U0001000b\U0001000d-\U00010026\U00010028-\U0001003a\U0001003c-\U0001003d\U0001003f-\U0001004d\U00010050-\U0001005d\U00010080-\U000100fa\U00010280-\U0001029c\U000102a0-\U000102d0\U00010300-\U0001031f\U0001032d-\U00010340\U00010342-\U00010349\U00010350-\U00010375\U00010380-\U0001039d\U000103a0-\U000103c3\U000103c8-\U000103cf\U00010450-\U0001049d\U00010500-\U00010527\U00010530-\U00010563\U00010600-\U00010736\U00010740-\U00010755\U00010760-\U00010767\U00010800-\U00010805\U00010808\U0001080a-\U00010835\U00010837-\U00010838\U0001083c\U0001083f-\U00010855\U00010860-\U00010876\U00010880-\U0001089e\U000108e0-\U000108f2\U000108f4-\U000108f5\U00010900-\U00010915\U00010920-\U00010939\U00010980-\U000109b7\U000109be-\U000109bf\U00010a00\U00010a10-\U00010a13\U00010a15-\U00010a17\U00010a19-\U00010a35\U00010a60-\U00010a7c\U00010a80-\U00010a9c\U00010ac0-\U00010ac7\U00010ac9-\U00010ae4\U00010b00-\U00010b35\U00010b40-\U00010b55\U00010b60-\U00010b72\U00010b80-\U00010b91\U00010c00-\U00010c48\U00010d00-\U00010d23\U00010f00-\U00010f1c\U00010f27\U00010f30-\U00010f45\U00011003-\U00011037\U00011083-\U000110af\U000110d0-\U000110e8\U00011103-\U00011126\U00011144\U00011150-\U00011172\U00011176\U00011183-\U000111b2\U000111c1-\U000111c4\U000111da\U000111dc\U00011200-\U00011211\U00011213-\U0001122b\U00011280-\U00011286\U00011288\U0001128a-\U0001128d\U0001128f-\U0001129d\U0001129f-\U000112a8\U000112b0-\U000112de\U00011305-\U0001130c\U0001130f-\U00011310\U00011313-\U00011328\U0001132a-\U00011330\U00011332-\U00011333\U00011335-\U00011339\U0001133d\U00011350\U0001135d-\U00011361\U00011400-\U00011434\U00011447-\U0001144a\U00011480-\U000114af\U000114c4-\U000114c5\U000114c7\U00011580-\U000115ae\U000115d8-\U000115db\U00011600-\U0001162f\U00011644\U00011680-\U000116aa\U00011700-\U0001171a\U00011800-\U0001182b\U000118ff\U00011a00\U00011a0b-\U00011a32\U00011a3a\U00011a50\U00011a5c-\U00011a83\U00011a86-\U00011a89\U00011a9d\U00011ac0-\U00011af8\U00011c00-\U00011c08\U00011c0a-\U00011c2e\U00011c40\U00011c72-\U00011c8f\U00011d00-\U00011d06\U00011d08-\U00011d09\U00011d0b-\U00011d30\U00011d46\U00011d60-\U00011d65\U00011d67-\U00011d68\U00011d6a-\U00011d89\U00011d98\U00011ee0-\U00011ef2\U00012000-\U00012399\U00012480-\U00012543\U00013000-\U0001342e\U00014400-\U00014646\U00016800-\U00016a38\U00016a40-\U00016a5e\U00016ad0-\U00016aed\U00016b00-\U00016b2f\U00016b63-\U00016b77\U00016b7d-\U00016b8f\U00016f00-\U00016f44\U00016f50\U00017000-\U000187f1\U00018800-\U00018af2\U0001b000-\U0001b11e\U0001b170-\U0001b2fb\U0001bc00-\U0001bc6a\U0001bc70-\U0001bc7c\U0001bc80-\U0001bc88\U0001bc90-\U0001bc99\U0001e800-\U0001e8c4\U0001ee00-\U0001ee03\U0001ee05-\U0001ee1f\U0001ee21-\U0001ee22\U0001ee24\U0001ee27\U0001ee29-\U0001ee32\U0001ee34-\U0001ee37\U0001ee39\U0001ee3b\U0001ee42\U0001ee47\U0001ee49\U0001ee4b\U0001ee4d-\U0001ee4f\U0001ee51-\U0001ee52\U0001ee54\U0001ee57\U0001ee59\U0001ee5b\U0001ee5d\U0001ee5f\U0001ee61-\U0001ee62\U0001ee64\U0001ee67-\U0001ee6a\U0001ee6c-\U0001ee72\U0001ee74-\U0001ee77\U0001ee79-\U0001ee7c\U0001ee7e\U0001ee80-\U0001ee89\U0001ee8b-\U0001ee9b\U0001eea1-\U0001eea3\U0001eea5-\U0001eea9\U0001eeab-\U0001eebb\U00020000-\U0002a6d6\U0002a700-\U0002b734\U0002b740-\U0002b81d\U0002b820-\U0002cea1\U0002ceb0-\U0002ebe0\U0002f800-\U0002fa1d'

Lt = '\u01c5\u01c8\u01cb\u01f2\u1f88-\u1f8f\u1f98-\u1f9f\u1fa8-\u1faf\u1fbc\u1fcc\u1ffc'

Lu = 'A-Z\xc0-\xd6\xd8-\xde\u0100\u0102\u0104\u0106\u0108\u010a\u010c\u010e\u0110\u0112\u0114\u0116\u0118\u011a\u011c\u011e\u0120\u0122\u0124\u0126\u0128\u012a\u012c\u012e\u0130\u0132\u0134\u0136\u0139\u013b\u013d\u013f\u0141\u0143\u0145\u0147\u014a\u014c\u014e\u0150\u0152\u0154\u0156\u0158\u015a\u015c\u015e\u0160\u0162\u0164\u0166\u0168\u016a\u016c\u016e\u0170\u0172\u0174\u0176\u0178-\u0179\u017b\u017d\u0181-\u0182\u0184\u0186-\u0187\u0189-\u018b\u018e-\u0191\u0193-\u0194\u0196-\u0198\u019c-\u019d\u019f-\u01a0\u01a2\u01a4\u01a6-\u01a7\u01a9\u01ac\u01ae-\u01af\u01b1-\u01b3\u01b5\u01b7-\u01b8\u01bc\u01c4\u01c7\u01ca\u01cd\u01cf\u01d1\u01d3\u01d5\u01d7\u01d9\u01db\u01de\u01e0\u01e2\u01e4\u01e6\u01e8\u01ea\u01ec\u01ee\u01f1\u01f4\u01f6-\u01f8\u01fa\u01fc\u01fe\u0200\u0202\u0204\u0206\u0208\u020a\u020c\u020e\u0210\u0212\u0214\u0216\u0218\u021a\u021c\u021e\u0220\u0222\u0224\u0226\u0228\u022a\u022c\u022e\u0230\u0232\u023a-\u023b\u023d-\u023e\u0241\u0243-\u0246\u0248\u024a\u024c\u024e\u0370\u0372\u0376\u037f\u0386\u0388-\u038a\u038c\u038e-\u038f\u0391-\u03a1\u03a3-\u03ab\u03cf\u03d2-\u03d4\u03d8\u03da\u03dc\u03de\u03e0\u03e2\u03e4\u03e6\u03e8\u03ea\u03ec\u03ee\u03f4\u03f7\u03f9-\u03fa\u03fd-\u042f\u0460\u0462\u0464\u0466\u0468\u046a\u046c\u046e\u0470\u0472\u0474\u0476\u0478\u047a\u047c\u047e\u0480\u048a\u048c\u048e\u0490\u0492\u0494\u0496\u0498\u049a\u049c\u049e\u04a0\u04a2\u04a4\u04a6\u04a8\u04aa\u04ac\u04ae\u04b0\u04b2\u04b4\u04b6\u04b8\u04ba\u04bc\u04be\u04c0-\u04c1\u04c3\u04c5\u04c7\u04c9\u04cb\u04cd\u04d0\u04d2\u04d4\u04d6\u04d8\u04da\u04dc\u04de\u04e0\u04e2\u04e4\u04e6\u04e8\u04ea\u04ec\u04ee\u04f0\u04f2\u04f4\u04f6\u04f8\u04fa\u04fc\u04fe\u0500\u0502\u0504\u0506\u0508\u050a\u050c\u050e\u0510\u0512\u0514\u0516\u0518\u051a\u051c\u051e\u0520\u0522\u0524\u0526\u0528\u052a\u052c\u052e\u0531-\u0556\u10a0-\u10c5\u10c7\u10cd\u13a0-\u13f5\u1c90-\u1cba\u1cbd-\u1cbf\u1e00\u1e02\u1e04\u1e06\u1e08\u1e0a\u1e0c\u1e0e\u1e10\u1e12\u1e14\u1e16\u1e18\u1e1a\u1e1c\u1e1e\u1e20\u1e22\u1e24\u1e26\u1e28\u1e2a\u1e2c\u1e2e\u1e30\u1e32\u1e34\u1e36\u1e38\u1e3a\u1e3c\u1e3e\u1e40\u1e42\u1e44\u1e46\u1e48\u1e4a\u1e4c\u1e4e\u1e50\u1e52\u1e54\u1e56\u1e58\u1e5a\u1e5c\u1e5e\u1e60\u1e62\u1e64\u1e66\u1e68\u1e6a\u1e6c\u1e6e\u1e70\u1e72\u1e74\u1e76\u1e78\u1e7a\u1e7c\u1e7e\u1e80\u1e82\u1e84\u1e86\u1e88\u1e8a\u1e8c\u1e8e\u1e90\u1e92\u1e94\u1e9e\u1ea0\u1ea2\u1ea4\u1ea6\u1ea8\u1eaa\u1eac\u1eae\u1eb0\u1eb2\u1eb4\u1eb6\u1eb8\u1eba\u1ebc\u1ebe\u1ec0\u1ec2\u1ec4\u1ec6\u1ec8\u1eca\u1ecc\u1ece\u1ed0\u1ed2\u1ed4\u1ed6\u1ed8\u1eda\u1edc\u1ede\u1ee0\u1ee2\u1ee4\u1ee6\u1ee8\u1eea\u1eec\u1eee\u1ef0\u1ef2\u1ef4\u1ef6\u1ef8\u1efa\u1efc\u1efe\u1f08-\u1f0f\u1f18-\u1f1d\u1f28-\u1f2f\u1f38-\u1f3f\u1f48-\u1f4d\u1f59\u1f5b\u1f5d\u1f5f\u1f68-\u1f6f\u1fb8-\u1fbb\u1fc8-\u1fcb\u1fd8-\u1fdb\u1fe8-\u1fec\u1ff8-\u1ffb\u2102\u2107\u210b-\u210d\u2110-\u2112\u2115\u2119-\u211d\u2124\u2126\u2128\u212a-\u212d\u2130-\u2133\u213e-\u213f\u2145\u2183\u2c00-\u2c2e\u2c60\u2c62-\u2c64\u2c67\u2c69\u2c6b\u2c6d-\u2c70\u2c72\u2c75\u2c7e-\u2c80\u2c82\u2c84\u2c86\u2c88\u2c8a\u2c8c\u2c8e\u2c90\u2c92\u2c94\u2c96\u2c98\u2c9a\u2c9c\u2c9e\u2ca0\u2ca2\u2ca4\u2ca6\u2ca8\u2caa\u2cac\u2cae\u2cb0\u2cb2\u2cb4\u2cb6\u2cb8\u2cba\u2cbc\u2cbe\u2cc0\u2cc2\u2cc4\u2cc6\u2cc8\u2cca\u2ccc\u2cce\u2cd0\u2cd2\u2cd4\u2cd6\u2cd8\u2cda\u2cdc\u2cde\u2ce0\u2ce2\u2ceb\u2ced\u2cf2\ua640\ua642\ua644\ua646\ua648\ua64a\ua64c\ua64e\ua650\ua652\ua654\ua656\ua658\ua65a\ua65c\ua65e\ua660\ua662\ua664\ua666\ua668\ua66a\ua66c\ua680\ua682\ua684\ua686\ua688\ua68a\ua68c\ua68e\ua690\ua692\ua694\ua696\ua698\ua69a\ua722\ua724\ua726\ua728\ua72a\ua72c\ua72e\ua732\ua734\ua736\ua738\ua73a\ua73c\ua73e\ua740\ua742\ua744\ua746\ua748\ua74a\ua74c\ua74e\ua750\ua752\ua754\ua756\ua758\ua75a\ua75c\ua75e\ua760\ua762\ua764\ua766\ua768\ua76a\ua76c\ua76e\ua779\ua77b\ua77d-\ua77e\ua780\ua782\ua784\ua786\ua78b\ua78d\ua790\ua792\ua796\ua798\ua79a\ua79c\ua79e\ua7a0\ua7a2\ua7a4\ua7a6\ua7a8\ua7aa-\ua7ae\ua7b0-\ua7b4\ua7b6\ua7b8\uff21-\uff3a\U00010400-\U00010427\U000104b0-\U000104d3\U00010c80-\U00010cb2\U000118a0-\U000118bf\U00016e40-\U00016e5f\U0001d400-\U0001d419\U0001d434-\U0001d44d\U0001d468-\U0001d481\U0001d49c\U0001d49e-\U0001d49f\U0001d4a2\U0001d4a5-\U0001d4a6\U0001d4a9-\U0001d4ac\U0001d4ae-\U0001d4b5\U0001d4d0-\U0001d4e9\U0001d504-\U0001d505\U0001d507-\U0001d50a\U0001d50d-\U0001d514\U0001d516-\U0001d51c\U0001d538-\U0001d539\U0001d53b-\U0001d53e\U0001d540-\U0001d544\U0001d546\U0001d54a-\U0001d550\U0001d56c-\U0001d585\U0001d5a0-\U0001d5b9\U0001d5d4-\U0001d5ed\U0001d608-\U0001d621\U0001d63c-\U0001d655\U0001d670-\U0001d689\U0001d6a8-\U0001d6c0\U0001d6e2-\U0001d6fa\U0001d71c-\U0001d734\U0001d756-\U0001d76e\U0001d790-\U0001d7a8\U0001d7ca\U0001e900-\U0001e921'

Mc = '\u0903\u093b\u093e-\u0940\u0949-\u094c\u094e-\u094f\u0982-\u0983\u09be-\u09c0\u09c7-\u09c8\u09cb-\u09cc\u09d7\u0a03\u0a3e-\u0a40\u0a83\u0abe-\u0ac0\u0ac9\u0acb-\u0acc\u0b02-\u0b03\u0b3e\u0b40\u0b47-\u0b48\u0b4b-\u0b4c\u0b57\u0bbe-\u0bbf\u0bc1-\u0bc2\u0bc6-\u0bc8\u0bca-\u0bcc\u0bd7\u0c01-\u0c03\u0c41-\u0c44\u0c82-\u0c83\u0cbe\u0cc0-\u0cc4\u0cc7-\u0cc8\u0cca-\u0ccb\u0cd5-\u0cd6\u0d02-\u0d03\u0d3e-\u0d40\u0d46-\u0d48\u0d4a-\u0d4c\u0d57\u0d82-\u0d83\u0dcf-\u0dd1\u0dd8-\u0ddf\u0df2-\u0df3\u0f3e-\u0f3f\u0f7f\u102b-\u102c\u1031\u1038\u103b-\u103c\u1056-\u1057\u1062-\u1064\u1067-\u106d\u1083-\u1084\u1087-\u108c\u108f\u109a-\u109c\u17b6\u17be-\u17c5\u17c7-\u17c8\u1923-\u1926\u1929-\u192b\u1930-\u1931\u1933-\u1938\u1a19-\u1a1a\u1a55\u1a57\u1a61\u1a63-\u1a64\u1a6d-\u1a72\u1b04\u1b35\u1b3b\u1b3d-\u1b41\u1b43-\u1b44\u1b82\u1ba1\u1ba6-\u1ba7\u1baa\u1be7\u1bea-\u1bec\u1bee\u1bf2-\u1bf3\u1c24-\u1c2b\u1c34-\u1c35\u1ce1\u1cf2-\u1cf3\u1cf7\u302e-\u302f\ua823-\ua824\ua827\ua880-\ua881\ua8b4-\ua8c3\ua952-\ua953\ua983\ua9b4-\ua9b5\ua9ba-\ua9bb\ua9bd-\ua9c0\uaa2f-\uaa30\uaa33-\uaa34\uaa4d\uaa7b\uaa7d\uaaeb\uaaee-\uaaef\uaaf5\uabe3-\uabe4\uabe6-\uabe7\uabe9-\uabea\uabec\U00011000\U00011002\U00011082\U000110b0-\U000110b2\U000110b7-\U000110b8\U0001112c\U00011145-\U00011146\U00011182\U000111b3-\U000111b5\U000111bf-\U000111c0\U0001122c-\U0001122e\U00011232-\U00011233\U00011235\U000112e0-\U000112e2\U00011302-\U00011303\U0001133e-\U0001133f\U00011341-\U00011344\U00011347-\U00011348\U0001134b-\U0001134d\U00011357\U00011362-\U00011363\U00011435-\U00011437\U00011440-\U00011441\U00011445\U000114b0-\U000114b2\U000114b9\U000114bb-\U000114be\U000114c1\U000115af-\U000115b1\U000115b8-\U000115bb\U000115be\U00011630-\U00011632\U0001163b-\U0001163c\U0001163e\U000116ac\U000116ae-\U000116af\U000116b6\U00011720-\U00011721\U00011726\U0001182c-\U0001182e\U00011838\U00011a39\U00011a57-\U00011a58\U00011a97\U00011c2f\U00011c3e\U00011ca9\U00011cb1\U00011cb4\U00011d8a-\U00011d8e\U00011d93-\U00011d94\U00011d96\U00011ef5-\U00011ef6\U00016f51-\U00016f7e\U0001d165-\U0001d166\U0001d16d-\U0001d172'

Me = '\u0488-\u0489\u1abe\u20dd-\u20e0\u20e2-\u20e4\ua670-\ua672'

Mn = '\u0300-\u036f\u0483-\u0487\u0591-\u05bd\u05bf\u05c1-\u05c2\u05c4-\u05c5\u05c7\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06dc\u06df-\u06e4\u06e7-\u06e8\u06ea-\u06ed\u0711\u0730-\u074a\u07a6-\u07b0\u07eb-\u07f3\u07fd\u0816-\u0819\u081b-\u0823\u0825-\u0827\u0829-\u082d\u0859-\u085b\u08d3-\u08e1\u08e3-\u0902\u093a\u093c\u0941-\u0948\u094d\u0951-\u0957\u0962-\u0963\u0981\u09bc\u09c1-\u09c4\u09cd\u09e2-\u09e3\u09fe\u0a01-\u0a02\u0a3c\u0a41-\u0a42\u0a47-\u0a48\u0a4b-\u0a4d\u0a51\u0a70-\u0a71\u0a75\u0a81-\u0a82\u0abc\u0ac1-\u0ac5\u0ac7-\u0ac8\u0acd\u0ae2-\u0ae3\u0afa-\u0aff\u0b01\u0b3c\u0b3f\u0b41-\u0b44\u0b4d\u0b56\u0b62-\u0b63\u0b82\u0bc0\u0bcd\u0c00\u0c04\u0c3e-\u0c40\u0c46-\u0c48\u0c4a-\u0c4d\u0c55-\u0c56\u0c62-\u0c63\u0c81\u0cbc\u0cbf\u0cc6\u0ccc-\u0ccd\u0ce2-\u0ce3\u0d00-\u0d01\u0d3b-\u0d3c\u0d41-\u0d44\u0d4d\u0d62-\u0d63\u0dca\u0dd2-\u0dd4\u0dd6\u0e31\u0e34-\u0e3a\u0e47-\u0e4e\u0eb1\u0eb4-\u0eb9\u0ebb-\u0ebc\u0ec8-\u0ecd\u0f18-\u0f19\u0f35\u0f37\u0f39\u0f71-\u0f7e\u0f80-\u0f84\u0f86-\u0f87\u0f8d-\u0f97\u0f99-\u0fbc\u0fc6\u102d-\u1030\u1032-\u1037\u1039-\u103a\u103d-\u103e\u1058-\u1059\u105e-\u1060\u1071-\u1074\u1082\u1085-\u1086\u108d\u109d\u135d-\u135f\u1712-\u1714\u1732-\u1734\u1752-\u1753\u1772-\u1773\u17b4-\u17b5\u17b7-\u17bd\u17c6\u17c9-\u17d3\u17dd\u180b-\u180d\u1885-\u1886\u18a9\u1920-\u1922\u1927-\u1928\u1932\u1939-\u193b\u1a17-\u1a18\u1a1b\u1a56\u1a58-\u1a5e\u1a60\u1a62\u1a65-\u1a6c\u1a73-\u1a7c\u1a7f\u1ab0-\u1abd\u1b00-\u1b03\u1b34\u1b36-\u1b3a\u1b3c\u1b42\u1b6b-\u1b73\u1b80-\u1b81\u1ba2-\u1ba5\u1ba8-\u1ba9\u1bab-\u1bad\u1be6\u1be8-\u1be9\u1bed\u1bef-\u1bf1\u1c2c-\u1c33\u1c36-\u1c37\u1cd0-\u1cd2\u1cd4-\u1ce0\u1ce2-\u1ce8\u1ced\u1cf4\u1cf8-\u1cf9\u1dc0-\u1df9\u1dfb-\u1dff\u20d0-\u20dc\u20e1\u20e5-\u20f0\u2cef-\u2cf1\u2d7f\u2de0-\u2dff\u302a-\u302d\u3099-\u309a\ua66f\ua674-\ua67d\ua69e-\ua69f\ua6f0-\ua6f1\ua802\ua806\ua80b\ua825-\ua826\ua8c4-\ua8c5\ua8e0-\ua8f1\ua8ff\ua926-\ua92d\ua947-\ua951\ua980-\ua982\ua9b3\ua9b6-\ua9b9\ua9bc\ua9e5\uaa29-\uaa2e\uaa31-\uaa32\uaa35-\uaa36\uaa43\uaa4c\uaa7c\uaab0\uaab2-\uaab4\uaab7-\uaab8\uaabe-\uaabf\uaac1\uaaec-\uaaed\uaaf6\uabe5\uabe8\uabed\ufb1e\ufe00-\ufe0f\ufe20-\ufe2f\U000101fd\U000102e0\U00010376-\U0001037a\U00010a01-\U00010a03\U00010a05-\U00010a06\U00010a0c-\U00010a0f\U00010a38-\U00010a3a\U00010a3f\U00010ae5-\U00010ae6\U00010d24-\U00010d27\U00010f46-\U00010f50\U00011001\U00011038-\U00011046\U0001107f-\U00011081\U000110b3-\U000110b6\U000110b9-\U000110ba\U00011100-\U00011102\U00011127-\U0001112b\U0001112d-\U00011134\U00011173\U00011180-\U00011181\U000111b6-\U000111be\U000111c9-\U000111cc\U0001122f-\U00011231\U00011234\U00011236-\U00011237\U0001123e\U000112df\U000112e3-\U000112ea\U00011300-\U00011301\U0001133b-\U0001133c\U00011340\U00011366-\U0001136c\U00011370-\U00011374\U00011438-\U0001143f\U00011442-\U00011444\U00011446\U0001145e\U000114b3-\U000114b8\U000114ba\U000114bf-\U000114c0\U000114c2-\U000114c3\U000115b2-\U000115b5\U000115bc-\U000115bd\U000115bf-\U000115c0\U000115dc-\U000115dd\U00011633-\U0001163a\U0001163d\U0001163f-\U00011640\U000116ab\U000116ad\U000116b0-\U000116b5\U000116b7\U0001171d-\U0001171f\U00011722-\U00011725\U00011727-\U0001172b\U0001182f-\U00011837\U00011839-\U0001183a\U00011a01-\U00011a0a\U00011a33-\U00011a38\U00011a3b-\U00011a3e\U00011a47\U00011a51-\U00011a56\U00011a59-\U00011a5b\U00011a8a-\U00011a96\U00011a98-\U00011a99\U00011c30-\U00011c36\U00011c38-\U00011c3d\U00011c3f\U00011c92-\U00011ca7\U00011caa-\U00011cb0\U00011cb2-\U00011cb3\U00011cb5-\U00011cb6\U00011d31-\U00011d36\U00011d3a\U00011d3c-\U00011d3d\U00011d3f-\U00011d45\U00011d47\U00011d90-\U00011d91\U00011d95\U00011d97\U00011ef3-\U00011ef4\U00016af0-\U00016af4\U00016b30-\U00016b36\U00016f8f-\U00016f92\U0001bc9d-\U0001bc9e\U0001d167-\U0001d169\U0001d17b-\U0001d182\U0001d185-\U0001d18b\U0001d1aa-\U0001d1ad\U0001d242-\U0001d244\U0001da00-\U0001da36\U0001da3b-\U0001da6c\U0001da75\U0001da84\U0001da9b-\U0001da9f\U0001daa1-\U0001daaf\U0001e000-\U0001e006\U0001e008-\U0001e018\U0001e01b-\U0001e021\U0001e023-\U0001e024\U0001e026-\U0001e02a\U0001e8d0-\U0001e8d6\U0001e944-\U0001e94a\U000e0100-\U000e01ef'

Nd = '0-9\u0660-\u0669\u06f0-\u06f9\u07c0-\u07c9\u0966-\u096f\u09e6-\u09ef\u0a66-\u0a6f\u0ae6-\u0aef\u0b66-\u0b6f\u0be6-\u0bef\u0c66-\u0c6f\u0ce6-\u0cef\u0d66-\u0d6f\u0de6-\u0def\u0e50-\u0e59\u0ed0-\u0ed9\u0f20-\u0f29\u1040-\u1049\u1090-\u1099\u17e0-\u17e9\u1810-\u1819\u1946-\u194f\u19d0-\u19d9\u1a80-\u1a89\u1a90-\u1a99\u1b50-\u1b59\u1bb0-\u1bb9\u1c40-\u1c49\u1c50-\u1c59\ua620-\ua629\ua8d0-\ua8d9\ua900-\ua909\ua9d0-\ua9d9\ua9f0-\ua9f9\uaa50-\uaa59\uabf0-\uabf9\uff10-\uff19\U000104a0-\U000104a9\U00010d30-\U00010d39\U00011066-\U0001106f\U000110f0-\U000110f9\U00011136-\U0001113f\U000111d0-\U000111d9\U000112f0-\U000112f9\U00011450-\U00011459\U000114d0-\U000114d9\U00011650-\U00011659\U000116c0-\U000116c9\U00011730-\U00011739\U000118e0-\U000118e9\U00011c50-\U00011c59\U00011d50-\U00011d59\U00011da0-\U00011da9\U00016a60-\U00016a69\U00016b50-\U00016b59\U0001d7ce-\U0001d7ff\U0001e950-\U0001e959'

Nl = '\u16ee-\u16f0\u2160-\u2182\u2185-\u2188\u3007\u3021-\u3029\u3038-\u303a\ua6e6-\ua6ef\U00010140-\U00010174\U00010341\U0001034a\U000103d1-\U000103d5\U00012400-\U0001246e'

No = '\xb2-\xb3\xb9\xbc-\xbe\u09f4-\u09f9\u0b72-\u0b77\u0bf0-\u0bf2\u0c78-\u0c7e\u0d58-\u0d5e\u0d70-\u0d78\u0f2a-\u0f33\u1369-\u137c\u17f0-\u17f9\u19da\u2070\u2074-\u2079\u2080-\u2089\u2150-\u215f\u2189\u2460-\u249b\u24ea-\u24ff\u2776-\u2793\u2cfd\u3192-\u3195\u3220-\u3229\u3248-\u324f\u3251-\u325f\u3280-\u3289\u32b1-\u32bf\ua830-\ua835\U00010107-\U00010133\U00010175-\U00010178\U0001018a-\U0001018b\U000102e1-\U000102fb\U00010320-\U00010323\U00010858-\U0001085f\U00010879-\U0001087f\U000108a7-\U000108af\U000108fb-\U000108ff\U00010916-\U0001091b\U000109bc-\U000109bd\U000109c0-\U000109cf\U000109d2-\U000109ff\U00010a40-\U00010a48\U00010a7d-\U00010a7e\U00010a9d-\U00010a9f\U00010aeb-\U00010aef\U00010b58-\U00010b5f\U00010b78-\U00010b7f\U00010ba9-\U00010baf\U00010cfa-\U00010cff\U00010e60-\U00010e7e\U00010f1d-\U00010f26\U00010f51-\U00010f54\U00011052-\U00011065\U000111e1-\U000111f4\U0001173a-\U0001173b\U000118ea-\U000118f2\U00011c5a-\U00011c6c\U00016b5b-\U00016b61\U00016e80-\U00016e96\U0001d2e0-\U0001d2f3\U0001d360-\U0001d378\U0001e8c7-\U0001e8cf\U0001ec71-\U0001ecab\U0001ecad-\U0001ecaf\U0001ecb1-\U0001ecb4\U0001f100-\U0001f10c'

Pc = '_\u203f-\u2040\u2054\ufe33-\ufe34\ufe4d-\ufe4f\uff3f'

Pd = '\\-\u058a\u05be\u1400\u1806\u2010-\u2015\u2e17\u2e1a\u2e3a-\u2e3b\u2e40\u301c\u3030\u30a0\ufe31-\ufe32\ufe58\ufe63\uff0d'

Pe = ')\\]}\u0f3b\u0f3d\u169c\u2046\u207e\u208e\u2309\u230b\u232a\u2769\u276b\u276d\u276f\u2771\u2773\u2775\u27c6\u27e7\u27e9\u27eb\u27ed\u27ef\u2984\u2986\u2988\u298a\u298c\u298e\u2990\u2992\u2994\u2996\u2998\u29d9\u29db\u29fd\u2e23\u2e25\u2e27\u2e29\u3009\u300b\u300d\u300f\u3011\u3015\u3017\u3019\u301b\u301e-\u301f\ufd3e\ufe18\ufe36\ufe38\ufe3a\ufe3c\ufe3e\ufe40\ufe42\ufe44\ufe48\ufe5a\ufe5c\ufe5e\uff09\uff3d\uff5d\uff60\uff63'

Pf = '\xbb\u2019\u201d\u203a\u2e03\u2e05\u2e0a\u2e0d\u2e1d\u2e21'

Pi = '\xab\u2018\u201b-\u201c\u201f\u2039\u2e02\u2e04\u2e09\u2e0c\u2e1c\u2e20'

Po = "!-#%-'*,.-/:-;?-@\\\\\xa1\xa7\xb6-\xb7\xbf\u037e\u0387\u055a-\u055f\u0589\u05c0\u05c3\u05c6\u05f3-\u05f4\u0609-\u060a\u060c-\u060d\u061b\u061e-\u061f\u066a-\u066d\u06d4\u0700-\u070d\u07f7-\u07f9\u0830-\u083e\u085e\u0964-\u0965\u0970\u09fd\u0a76\u0af0\u0c84\u0df4\u0e4f\u0e5a-\u0e5b\u0f04-\u0f12\u0f14\u0f85\u0fd0-\u0fd4\u0fd9-\u0fda\u104a-\u104f\u10fb\u1360-\u1368\u166d-\u166e\u16eb-\u16ed\u1735-\u1736\u17d4-\u17d6\u17d8-\u17da\u1800-\u1805\u1807-\u180a\u1944-\u1945\u1a1e-\u1a1f\u1aa0-\u1aa6\u1aa8-\u1aad\u1b5a-\u1b60\u1bfc-\u1bff\u1c3b-\u1c3f\u1c7e-\u1c7f\u1cc0-\u1cc7\u1cd3\u2016-\u2017\u2020-\u2027\u2030-\u2038\u203b-\u203e\u2041-\u2043\u2047-\u2051\u2053\u2055-\u205e\u2cf9-\u2cfc\u2cfe-\u2cff\u2d70\u2e00-\u2e01\u2e06-\u2e08\u2e0b\u2e0e-\u2e16\u2e18-\u2e19\u2e1b\u2e1e-\u2e1f\u2e2a-\u2e2e\u2e30-\u2e39\u2e3c-\u2e3f\u2e41\u2e43-\u2e4e\u3001-\u3003\u303d\u30fb\ua4fe-\ua4ff\ua60d-\ua60f\ua673\ua67e\ua6f2-\ua6f7\ua874-\ua877\ua8ce-\ua8cf\ua8f8-\ua8fa\ua8fc\ua92e-\ua92f\ua95f\ua9c1-\ua9cd\ua9de-\ua9df\uaa5c-\uaa5f\uaade-\uaadf\uaaf0-\uaaf1\uabeb\ufe10-\ufe16\ufe19\ufe30\ufe45-\ufe46\ufe49-\ufe4c\ufe50-\ufe52\ufe54-\ufe57\ufe5f-\ufe61\ufe68\ufe6a-\ufe6b\uff01-\uff03\uff05-\uff07\uff0a\uff0c\uff0e-\uff0f\uff1a-\uff1b\uff1f-\uff20\uff3c\uff61\uff64-\uff65\U00010100-\U00010102\U0001039f\U000103d0\U0001056f\U00010857\U0001091f\U0001093f\U00010a50-\U00010a58\U00010a7f\U00010af0-\U00010af6\U00010b39-\U00010b3f\U00010b99-\U00010b9c\U00010f55-\U00010f59\U00011047-\U0001104d\U000110bb-\U000110bc\U000110be-\U000110c1\U00011140-\U00011143\U00011174-\U00011175\U000111c5-\U000111c8\U000111cd\U000111db\U000111dd-\U000111df\U00011238-\U0001123d\U000112a9\U0001144b-\U0001144f\U0001145b\U0001145d\U000114c6\U000115c1-\U000115d7\U00011641-\U00011643\U00011660-\U0001166c\U0001173c-\U0001173e\U0001183b\U00011a3f-\U00011a46\U00011a9a-\U00011a9c\U00011a9e-\U00011aa2\U00011c41-\U00011c45\U00011c70-\U00011c71\U00011ef7-\U00011ef8\U00012470-\U00012474\U00016a6e-\U00016a6f\U00016af5\U00016b37-\U00016b3b\U00016b44\U00016e97-\U00016e9a\U0001bc9f\U0001da87-\U0001da8b\U0001e95e-\U0001e95f"

Ps = '(\\[{\u0f3a\u0f3c\u169b\u201a\u201e\u2045\u207d\u208d\u2308\u230a\u2329\u2768\u276a\u276c\u276e\u2770\u2772\u2774\u27c5\u27e6\u27e8\u27ea\u27ec\u27ee\u2983\u2985\u2987\u2989\u298b\u298d\u298f\u2991\u2993\u2995\u2997\u29d8\u29da\u29fc\u2e22\u2e24\u2e26\u2e28\u2e42\u3008\u300a\u300c\u300e\u3010\u3014\u3016\u3018\u301a\u301d\ufd3f\ufe17\ufe35\ufe37\ufe39\ufe3b\ufe3d\ufe3f\ufe41\ufe43\ufe47\ufe59\ufe5b\ufe5d\uff08\uff3b\uff5b\uff5f\uff62'

Sc = '$\xa2-\xa5\u058f\u060b\u07fe-\u07ff\u09f2-\u09f3\u09fb\u0af1\u0bf9\u0e3f\u17db\u20a0-\u20bf\ua838\ufdfc\ufe69\uff04\uffe0-\uffe1\uffe5-\uffe6\U0001ecb0'

Sk = '\\^`\xa8\xaf\xb4\xb8\u02c2-\u02c5\u02d2-\u02df\u02e5-\u02eb\u02ed\u02ef-\u02ff\u0375\u0384-\u0385\u1fbd\u1fbf-\u1fc1\u1fcd-\u1fcf\u1fdd-\u1fdf\u1fed-\u1fef\u1ffd-\u1ffe\u309b-\u309c\ua700-\ua716\ua720-\ua721\ua789-\ua78a\uab5b\ufbb2-\ufbc1\uff3e\uff40\uffe3\U0001f3fb-\U0001f3ff'

Sm = '+<->|~\xac\xb1\xd7\xf7\u03f6\u0606-\u0608\u2044\u2052\u207a-\u207c\u208a-\u208c\u2118\u2140-\u2144\u214b\u2190-\u2194\u219a-\u219b\u21a0\u21a3\u21a6\u21ae\u21ce-\u21cf\u21d2\u21d4\u21f4-\u22ff\u2320-\u2321\u237c\u239b-\u23b3\u23dc-\u23e1\u25b7\u25c1\u25f8-\u25ff\u266f\u27c0-\u27c4\u27c7-\u27e5\u27f0-\u27ff\u2900-\u2982\u2999-\u29d7\u29dc-\u29fb\u29fe-\u2aff\u2b30-\u2b44\u2b47-\u2b4c\ufb29\ufe62\ufe64-\ufe66\uff0b\uff1c-\uff1e\uff5c\uff5e\uffe2\uffe9-\uffec\U0001d6c1\U0001d6db\U0001d6fb\U0001d715\U0001d735\U0001d74f\U0001d76f\U0001d789\U0001d7a9\U0001d7c3\U0001eef0-\U0001eef1'

So = '\xa6\xa9\xae\xb0\u0482\u058d-\u058e\u060e-\u060f\u06de\u06e9\u06fd-\u06fe\u07f6\u09fa\u0b70\u0bf3-\u0bf8\u0bfa\u0c7f\u0d4f\u0d79\u0f01-\u0f03\u0f13\u0f15-\u0f17\u0f1a-\u0f1f\u0f34\u0f36\u0f38\u0fbe-\u0fc5\u0fc7-\u0fcc\u0fce-\u0fcf\u0fd5-\u0fd8\u109e-\u109f\u1390-\u1399\u1940\u19de-\u19ff\u1b61-\u1b6a\u1b74-\u1b7c\u2100-\u2101\u2103-\u2106\u2108-\u2109\u2114\u2116-\u2117\u211e-\u2123\u2125\u2127\u2129\u212e\u213a-\u213b\u214a\u214c-\u214d\u214f\u218a-\u218b\u2195-\u2199\u219c-\u219f\u21a1-\u21a2\u21a4-\u21a5\u21a7-\u21ad\u21af-\u21cd\u21d0-\u21d1\u21d3\u21d5-\u21f3\u2300-\u2307\u230c-\u231f\u2322-\u2328\u232b-\u237b\u237d-\u239a\u23b4-\u23db\u23e2-\u2426\u2440-\u244a\u249c-\u24e9\u2500-\u25b6\u25b8-\u25c0\u25c2-\u25f7\u2600-\u266e\u2670-\u2767\u2794-\u27bf\u2800-\u28ff\u2b00-\u2b2f\u2b45-\u2b46\u2b4d-\u2b73\u2b76-\u2b95\u2b98-\u2bc8\u2bca-\u2bfe\u2ce5-\u2cea\u2e80-\u2e99\u2e9b-\u2ef3\u2f00-\u2fd5\u2ff0-\u2ffb\u3004\u3012-\u3013\u3020\u3036-\u3037\u303e-\u303f\u3190-\u3191\u3196-\u319f\u31c0-\u31e3\u3200-\u321e\u322a-\u3247\u3250\u3260-\u327f\u328a-\u32b0\u32c0-\u32fe\u3300-\u33ff\u4dc0-\u4dff\ua490-\ua4c6\ua828-\ua82b\ua836-\ua837\ua839\uaa77-\uaa79\ufdfd\uffe4\uffe8\uffed-\uffee\ufffc-\ufffd\U00010137-\U0001013f\U00010179-\U00010189\U0001018c-\U0001018e\U00010190-\U0001019b\U000101a0\U000101d0-\U000101fc\U00010877-\U00010878\U00010ac8\U0001173f\U00016b3c-\U00016b3f\U00016b45\U0001bc9c\U0001d000-\U0001d0f5\U0001d100-\U0001d126\U0001d129-\U0001d164\U0001d16a-\U0001d16c\U0001d183-\U0001d184\U0001d18c-\U0001d1a9\U0001d1ae-\U0001d1e8\U0001d200-\U0001d241\U0001d245\U0001d300-\U0001d356\U0001d800-\U0001d9ff\U0001da37-\U0001da3a\U0001da6d-\U0001da74\U0001da76-\U0001da83\U0001da85-\U0001da86\U0001ecac\U0001f000-\U0001f02b\U0001f030-\U0001f093\U0001f0a0-\U0001f0ae\U0001f0b1-\U0001f0bf\U0001f0c1-\U0001f0cf\U0001f0d1-\U0001f0f5\U0001f110-\U0001f16b\U0001f170-\U0001f1ac\U0001f1e6-\U0001f202\U0001f210-\U0001f23b\U0001f240-\U0001f248\U0001f250-\U0001f251\U0001f260-\U0001f265\U0001f300-\U0001f3fa\U0001f400-\U0001f6d4\U0001f6e0-\U0001f6ec\U0001f6f0-\U0001f6f9\U0001f700-\U0001f773\U0001f780-\U0001f7d8\U0001f800-\U0001f80b\U0001f810-\U0001f847\U0001f850-\U0001f859\U0001f860-\U0001f887\U0001f890-\U0001f8ad\U0001f900-\U0001f90b\U0001f910-\U0001f93e\U0001f940-\U0001f970\U0001f973-\U0001f976\U0001f97a\U0001f97c-\U0001f9a2\U0001f9b0-\U0001f9b9\U0001f9c0-\U0001f9c2\U0001f9d0-\U0001f9ff\U0001fa60-\U0001fa6d'

Zl = '\u2028'

Zp = '\u2029'

Zs = ' \xa0\u1680\u2000-\u200a\u202f\u205f\u3000'

xid_continue = '0-9A-Z_a-z\xaa\xb5\xb7\xba\xc0-\xd6\xd8-\xf6\xf8-\u02c1\u02c6-\u02d1\u02e0-\u02e4\u02ec\u02ee\u0300-\u0374\u0376-\u0377\u037b-\u037d\u037f\u0386-\u038a\u038c\u038e-\u03a1\u03a3-\u03f5\u03f7-\u0481\u0483-\u0487\u048a-\u052f\u0531-\u0556\u0559\u0560-\u0588\u0591-\u05bd\u05bf\u05c1-\u05c2\u05c4-\u05c5\u05c7\u05d0-\u05ea\u05ef-\u05f2\u0610-\u061a\u0620-\u0669\u066e-\u06d3\u06d5-\u06dc\u06df-\u06e8\u06ea-\u06fc\u06ff\u0710-\u074a\u074d-\u07b1\u07c0-\u07f5\u07fa\u07fd\u0800-\u082d\u0840-\u085b\u0860-\u086a\u08a0-\u08b4\u08b6-\u08bd\u08d3-\u08e1\u08e3-\u0963\u0966-\u096f\u0971-\u0983\u0985-\u098c\u098f-\u0990\u0993-\u09a8\u09aa-\u09b0\u09b2\u09b6-\u09b9\u09bc-\u09c4\u09c7-\u09c8\u09cb-\u09ce\u09d7\u09dc-\u09dd\u09df-\u09e3\u09e6-\u09f1\u09fc\u09fe\u0a01-\u0a03\u0a05-\u0a0a\u0a0f-\u0a10\u0a13-\u0a28\u0a2a-\u0a30\u0a32-\u0a33\u0a35-\u0a36\u0a38-\u0a39\u0a3c\u0a3e-\u0a42\u0a47-\u0a48\u0a4b-\u0a4d\u0a51\u0a59-\u0a5c\u0a5e\u0a66-\u0a75\u0a81-\u0a83\u0a85-\u0a8d\u0a8f-\u0a91\u0a93-\u0aa8\u0aaa-\u0ab0\u0ab2-\u0ab3\u0ab5-\u0ab9\u0abc-\u0ac5\u0ac7-\u0ac9\u0acb-\u0acd\u0ad0\u0ae0-\u0ae3\u0ae6-\u0aef\u0af9-\u0aff\u0b01-\u0b03\u0b05-\u0b0c\u0b0f-\u0b10\u0b13-\u0b28\u0b2a-\u0b30\u0b32-\u0b33\u0b35-\u0b39\u0b3c-\u0b44\u0b47-\u0b48\u0b4b-\u0b4d\u0b56-\u0b57\u0b5c-\u0b5d\u0b5f-\u0b63\u0b66-\u0b6f\u0b71\u0b82-\u0b83\u0b85-\u0b8a\u0b8e-\u0b90\u0b92-\u0b95\u0b99-\u0b9a\u0b9c\u0b9e-\u0b9f\u0ba3-\u0ba4\u0ba8-\u0baa\u0bae-\u0bb9\u0bbe-\u0bc2\u0bc6-\u0bc8\u0bca-\u0bcd\u0bd0\u0bd7\u0be6-\u0bef\u0c00-\u0c0c\u0c0e-\u0c10\u0c12-\u0c28\u0c2a-\u0c39\u0c3d-\u0c44\u0c46-\u0c48\u0c4a-\u0c4d\u0c55-\u0c56\u0c58-\u0c5a\u0c60-\u0c63\u0c66-\u0c6f\u0c80-\u0c83\u0c85-\u0c8c\u0c8e-\u0c90\u0c92-\u0ca8\u0caa-\u0cb3\u0cb5-\u0cb9\u0cbc-\u0cc4\u0cc6-\u0cc8\u0cca-\u0ccd\u0cd5-\u0cd6\u0cde\u0ce0-\u0ce3\u0ce6-\u0cef\u0cf1-\u0cf2\u0d00-\u0d03\u0d05-\u0d0c\u0d0e-\u0d10\u0d12-\u0d44\u0d46-\u0d48\u0d4a-\u0d4e\u0d54-\u0d57\u0d5f-\u0d63\u0d66-\u0d6f\u0d7a-\u0d7f\u0d82-\u0d83\u0d85-\u0d96\u0d9a-\u0db1\u0db3-\u0dbb\u0dbd\u0dc0-\u0dc6\u0dca\u0dcf-\u0dd4\u0dd6\u0dd8-\u0ddf\u0de6-\u0def\u0df2-\u0df3\u0e01-\u0e3a\u0e40-\u0e4e\u0e50-\u0e59\u0e81-\u0e82\u0e84\u0e87-\u0e88\u0e8a\u0e8d\u0e94-\u0e97\u0e99-\u0e9f\u0ea1-\u0ea3\u0ea5\u0ea7\u0eaa-\u0eab\u0ead-\u0eb9\u0ebb-\u0ebd\u0ec0-\u0ec4\u0ec6\u0ec8-\u0ecd\u0ed0-\u0ed9\u0edc-\u0edf\u0f00\u0f18-\u0f19\u0f20-\u0f29\u0f35\u0f37\u0f39\u0f3e-\u0f47\u0f49-\u0f6c\u0f71-\u0f84\u0f86-\u0f97\u0f99-\u0fbc\u0fc6\u1000-\u1049\u1050-\u109d\u10a0-\u10c5\u10c7\u10cd\u10d0-\u10fa\u10fc-\u1248\u124a-\u124d\u1250-\u1256\u1258\u125a-\u125d\u1260-\u1288\u128a-\u128d\u1290-\u12b0\u12b2-\u12b5\u12b8-\u12be\u12c0\u12c2-\u12c5\u12c8-\u12d6\u12d8-\u1310\u1312-\u1315\u1318-\u135a\u135d-\u135f\u1369-\u1371\u1380-\u138f\u13a0-\u13f5\u13f8-\u13fd\u1401-\u166c\u166f-\u167f\u1681-\u169a\u16a0-\u16ea\u16ee-\u16f8\u1700-\u170c\u170e-\u1714\u1720-\u1734\u1740-\u1753\u1760-\u176c\u176e-\u1770\u1772-\u1773\u1780-\u17d3\u17d7\u17dc-\u17dd\u17e0-\u17e9\u180b-\u180d\u1810-\u1819\u1820-\u1878\u1880-\u18aa\u18b0-\u18f5\u1900-\u191e\u1920-\u192b\u1930-\u193b\u1946-\u196d\u1970-\u1974\u1980-\u19ab\u19b0-\u19c9\u19d0-\u19da\u1a00-\u1a1b\u1a20-\u1a5e\u1a60-\u1a7c\u1a7f-\u1a89\u1a90-\u1a99\u1aa7\u1ab0-\u1abd\u1b00-\u1b4b\u1b50-\u1b59\u1b6b-\u1b73\u1b80-\u1bf3\u1c00-\u1c37\u1c40-\u1c49\u1c4d-\u1c7d\u1c80-\u1c88\u1c90-\u1cba\u1cbd-\u1cbf\u1cd0-\u1cd2\u1cd4-\u1cf9\u1d00-\u1df9\u1dfb-\u1f15\u1f18-\u1f1d\u1f20-\u1f45\u1f48-\u1f4d\u1f50-\u1f57\u1f59\u1f5b\u1f5d\u1f5f-\u1f7d\u1f80-\u1fb4\u1fb6-\u1fbc\u1fbe\u1fc2-\u1fc4\u1fc6-\u1fcc\u1fd0-\u1fd3\u1fd6-\u1fdb\u1fe0-\u1fec\u1ff2-\u1ff4\u1ff6-\u1ffc\u203f-\u2040\u2054\u2071\u207f\u2090-\u209c\u20d0-\u20dc\u20e1\u20e5-\u20f0\u2102\u2107\u210a-\u2113\u2115\u2118-\u211d\u2124\u2126\u2128\u212a-\u2139\u213c-\u213f\u2145-\u2149\u214e\u2160-\u2188\u2c00-\u2c2e\u2c30-\u2c5e\u2c60-\u2ce4\u2ceb-\u2cf3\u2d00-\u2d25\u2d27\u2d2d\u2d30-\u2d67\u2d6f\u2d7f-\u2d96\u2da0-\u2da6\u2da8-\u2dae\u2db0-\u2db6\u2db8-\u2dbe\u2dc0-\u2dc6\u2dc8-\u2dce\u2dd0-\u2dd6\u2dd8-\u2dde\u2de0-\u2dff\u3005-\u3007\u3021-\u302f\u3031-\u3035\u3038-\u303c\u3041-\u3096\u3099-\u309a\u309d-\u309f\u30a1-\u30fa\u30fc-\u30ff\u3105-\u312f\u3131-\u318e\u31a0-\u31ba\u31f0-\u31ff\u3400-\u4db5\u4e00-\u9fef\ua000-\ua48c\ua4d0-\ua4fd\ua500-\ua60c\ua610-\ua62b\ua640-\ua66f\ua674-\ua67d\ua67f-\ua6f1\ua717-\ua71f\ua722-\ua788\ua78b-\ua7b9\ua7f7-\ua827\ua840-\ua873\ua880-\ua8c5\ua8d0-\ua8d9\ua8e0-\ua8f7\ua8fb\ua8fd-\ua92d\ua930-\ua953\ua960-\ua97c\ua980-\ua9c0\ua9cf-\ua9d9\ua9e0-\ua9fe\uaa00-\uaa36\uaa40-\uaa4d\uaa50-\uaa59\uaa60-\uaa76\uaa7a-\uaac2\uaadb-\uaadd\uaae0-\uaaef\uaaf2-\uaaf6\uab01-\uab06\uab09-\uab0e\uab11-\uab16\uab20-\uab26\uab28-\uab2e\uab30-\uab5a\uab5c-\uab65\uab70-\uabea\uabec-\uabed\uabf0-\uabf9\uac00-\ud7a3\ud7b0-\ud7c6\ud7cb-\ud7fb\uf900-\ufa6d\ufa70-\ufad9\ufb00-\ufb06\ufb13-\ufb17\ufb1d-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufbb1\ufbd3-\ufc5d\ufc64-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdf9\ufe00-\ufe0f\ufe20-\ufe2f\ufe33-\ufe34\ufe4d-\ufe4f\ufe71\ufe73\ufe77\ufe79\ufe7b\ufe7d\ufe7f-\ufefc\uff10-\uff19\uff21-\uff3a\uff3f\uff41-\uff5a\uff66-\uffbe\uffc2-\uffc7\uffca-\uffcf\uffd2-\uffd7\uffda-\uffdc\U00010000-\U0001000b\U0001000d-\U00010026\U00010028-\U0001003a\U0001003c-\U0001003d\U0001003f-\U0001004d\U00010050-\U0001005d\U00010080-\U000100fa\U00010140-\U00010174\U000101fd\U00010280-\U0001029c\U000102a0-\U000102d0\U000102e0\U00010300-\U0001031f\U0001032d-\U0001034a\U00010350-\U0001037a\U00010380-\U0001039d\U000103a0-\U000103c3\U000103c8-\U000103cf\U000103d1-\U000103d5\U00010400-\U0001049d\U000104a0-\U000104a9\U000104b0-\U000104d3\U000104d8-\U000104fb\U00010500-\U00010527\U00010530-\U00010563\U00010600-\U00010736\U00010740-\U00010755\U00010760-\U00010767\U00010800-\U00010805\U00010808\U0001080a-\U00010835\U00010837-\U00010838\U0001083c\U0001083f-\U00010855\U00010860-\U00010876\U00010880-\U0001089e\U000108e0-\U000108f2\U000108f4-\U000108f5\U00010900-\U00010915\U00010920-\U00010939\U00010980-\U000109b7\U000109be-\U000109bf\U00010a00-\U00010a03\U00010a05-\U00010a06\U00010a0c-\U00010a13\U00010a15-\U00010a17\U00010a19-\U00010a35\U00010a38-\U00010a3a\U00010a3f\U00010a60-\U00010a7c\U00010a80-\U00010a9c\U00010ac0-\U00010ac7\U00010ac9-\U00010ae6\U00010b00-\U00010b35\U00010b40-\U00010b55\U00010b60-\U00010b72\U00010b80-\U00010b91\U00010c00-\U00010c48\U00010c80-\U00010cb2\U00010cc0-\U00010cf2\U00010d00-\U00010d27\U00010d30-\U00010d39\U00010f00-\U00010f1c\U00010f27\U00010f30-\U00010f50\U00011000-\U00011046\U00011066-\U0001106f\U0001107f-\U000110ba\U000110d0-\U000110e8\U000110f0-\U000110f9\U00011100-\U00011134\U00011136-\U0001113f\U00011144-\U00011146\U00011150-\U00011173\U00011176\U00011180-\U000111c4\U000111c9-\U000111cc\U000111d0-\U000111da\U000111dc\U00011200-\U00011211\U00011213-\U00011237\U0001123e\U00011280-\U00011286\U00011288\U0001128a-\U0001128d\U0001128f-\U0001129d\U0001129f-\U000112a8\U000112b0-\U000112ea\U000112f0-\U000112f9\U00011300-\U00011303\U00011305-\U0001130c\U0001130f-\U00011310\U00011313-\U00011328\U0001132a-\U00011330\U00011332-\U00011333\U00011335-\U00011339\U0001133b-\U00011344\U00011347-\U00011348\U0001134b-\U0001134d\U00011350\U00011357\U0001135d-\U00011363\U00011366-\U0001136c\U00011370-\U00011374\U00011400-\U0001144a\U00011450-\U00011459\U0001145e\U00011480-\U000114c5\U000114c7\U000114d0-\U000114d9\U00011580-\U000115b5\U000115b8-\U000115c0\U000115d8-\U000115dd\U00011600-\U00011640\U00011644\U00011650-\U00011659\U00011680-\U000116b7\U000116c0-\U000116c9\U00011700-\U0001171a\U0001171d-\U0001172b\U00011730-\U00011739\U00011800-\U0001183a\U000118a0-\U000118e9\U000118ff\U00011a00-\U00011a3e\U00011a47\U00011a50-\U00011a83\U00011a86-\U00011a99\U00011a9d\U00011ac0-\U00011af8\U00011c00-\U00011c08\U00011c0a-\U00011c36\U00011c38-\U00011c40\U00011c50-\U00011c59\U00011c72-\U00011c8f\U00011c92-\U00011ca7\U00011ca9-\U00011cb6\U00011d00-\U00011d06\U00011d08-\U00011d09\U00011d0b-\U00011d36\U00011d3a\U00011d3c-\U00011d3d\U00011d3f-\U00011d47\U00011d50-\U00011d59\U00011d60-\U00011d65\U00011d67-\U00011d68\U00011d6a-\U00011d8e\U00011d90-\U00011d91\U00011d93-\U00011d98\U00011da0-\U00011da9\U00011ee0-\U00011ef6\U00012000-\U00012399\U00012400-\U0001246e\U00012480-\U00012543\U00013000-\U0001342e\U00014400-\U00014646\U00016800-\U00016a38\U00016a40-\U00016a5e\U00016a60-\U00016a69\U00016ad0-\U00016aed\U00016af0-\U00016af4\U00016b00-\U00016b36\U00016b40-\U00016b43\U00016b50-\U00016b59\U00016b63-\U00016b77\U00016b7d-\U00016b8f\U00016e40-\U00016e7f\U00016f00-\U00016f44\U00016f50-\U00016f7e\U00016f8f-\U00016f9f\U00016fe0-\U00016fe1\U00017000-\U000187f1\U00018800-\U00018af2\U0001b000-\U0001b11e\U0001b170-\U0001b2fb\U0001bc00-\U0001bc6a\U0001bc70-\U0001bc7c\U0001bc80-\U0001bc88\U0001bc90-\U0001bc99\U0001bc9d-\U0001bc9e\U0001d165-\U0001d169\U0001d16d-\U0001d172\U0001d17b-\U0001d182\U0001d185-\U0001d18b\U0001d1aa-\U0001d1ad\U0001d242-\U0001d244\U0001d400-\U0001d454\U0001d456-\U0001d49c\U0001d49e-\U0001d49f\U0001d4a2\U0001d4a5-\U0001d4a6\U0001d4a9-\U0001d4ac\U0001d4ae-\U0001d4b9\U0001d4bb\U0001d4bd-\U0001d4c3\U0001d4c5-\U0001d505\U0001d507-\U0001d50a\U0001d50d-\U0001d514\U0001d516-\U0001d51c\U0001d51e-\U0001d539\U0001d53b-\U0001d53e\U0001d540-\U0001d544\U0001d546\U0001d54a-\U0001d550\U0001d552-\U0001d6a5\U0001d6a8-\U0001d6c0\U0001d6c2-\U0001d6da\U0001d6dc-\U0001d6fa\U0001d6fc-\U0001d714\U0001d716-\U0001d734\U0001d736-\U0001d74e\U0001d750-\U0001d76e\U0001d770-\U0001d788\U0001d78a-\U0001d7a8\U0001d7aa-\U0001d7c2\U0001d7c4-\U0001d7cb\U0001d7ce-\U0001d7ff\U0001da00-\U0001da36\U0001da3b-\U0001da6c\U0001da75\U0001da84\U0001da9b-\U0001da9f\U0001daa1-\U0001daaf\U0001e000-\U0001e006\U0001e008-\U0001e018\U0001e01b-\U0001e021\U0001e023-\U0001e024\U0001e026-\U0001e02a\U0001e800-\U0001e8c4\U0001e8d0-\U0001e8d6\U0001e900-\U0001e94a\U0001e950-\U0001e959\U0001ee00-\U0001ee03\U0001ee05-\U0001ee1f\U0001ee21-\U0001ee22\U0001ee24\U0001ee27\U0001ee29-\U0001ee32\U0001ee34-\U0001ee37\U0001ee39\U0001ee3b\U0001ee42\U0001ee47\U0001ee49\U0001ee4b\U0001ee4d-\U0001ee4f\U0001ee51-\U0001ee52\U0001ee54\U0001ee57\U0001ee59\U0001ee5b\U0001ee5d\U0001ee5f\U0001ee61-\U0001ee62\U0001ee64\U0001ee67-\U0001ee6a\U0001ee6c-\U0001ee72\U0001ee74-\U0001ee77\U0001ee79-\U0001ee7c\U0001ee7e\U0001ee80-\U0001ee89\U0001ee8b-\U0001ee9b\U0001eea1-\U0001eea3\U0001eea5-\U0001eea9\U0001eeab-\U0001eebb\U00020000-\U0002a6d6\U0002a700-\U0002b734\U0002b740-\U0002b81d\U0002b820-\U0002cea1\U0002ceb0-\U0002ebe0\U0002f800-\U0002fa1d\U000e0100-\U000e01ef'

xid_start = 'A-Z_a-z\xaa\xb5\xba\xc0-\xd6\xd8-\xf6\xf8-\u02c1\u02c6-\u02d1\u02e0-\u02e4\u02ec\u02ee\u0370-\u0374\u0376-\u0377\u037b-\u037d\u037f\u0386\u0388-\u038a\u038c\u038e-\u03a1\u03a3-\u03f5\u03f7-\u0481\u048a-\u052f\u0531-\u0556\u0559\u0560-\u0588\u05d0-\u05ea\u05ef-\u05f2\u0620-\u064a\u066e-\u066f\u0671-\u06d3\u06d5\u06e5-\u06e6\u06ee-\u06ef\u06fa-\u06fc\u06ff\u0710\u0712-\u072f\u074d-\u07a5\u07b1\u07ca-\u07ea\u07f4-\u07f5\u07fa\u0800-\u0815\u081a\u0824\u0828\u0840-\u0858\u0860-\u086a\u08a0-\u08b4\u08b6-\u08bd\u0904-\u0939\u093d\u0950\u0958-\u0961\u0971-\u0980\u0985-\u098c\u098f-\u0990\u0993-\u09a8\u09aa-\u09b0\u09b2\u09b6-\u09b9\u09bd\u09ce\u09dc-\u09dd\u09df-\u09e1\u09f0-\u09f1\u09fc\u0a05-\u0a0a\u0a0f-\u0a10\u0a13-\u0a28\u0a2a-\u0a30\u0a32-\u0a33\u0a35-\u0a36\u0a38-\u0a39\u0a59-\u0a5c\u0a5e\u0a72-\u0a74\u0a85-\u0a8d\u0a8f-\u0a91\u0a93-\u0aa8\u0aaa-\u0ab0\u0ab2-\u0ab3\u0ab5-\u0ab9\u0abd\u0ad0\u0ae0-\u0ae1\u0af9\u0b05-\u0b0c\u0b0f-\u0b10\u0b13-\u0b28\u0b2a-\u0b30\u0b32-\u0b33\u0b35-\u0b39\u0b3d\u0b5c-\u0b5d\u0b5f-\u0b61\u0b71\u0b83\u0b85-\u0b8a\u0b8e-\u0b90\u0b92-\u0b95\u0b99-\u0b9a\u0b9c\u0b9e-\u0b9f\u0ba3-\u0ba4\u0ba8-\u0baa\u0bae-\u0bb9\u0bd0\u0c05-\u0c0c\u0c0e-\u0c10\u0c12-\u0c28\u0c2a-\u0c39\u0c3d\u0c58-\u0c5a\u0c60-\u0c61\u0c80\u0c85-\u0c8c\u0c8e-\u0c90\u0c92-\u0ca8\u0caa-\u0cb3\u0cb5-\u0cb9\u0cbd\u0cde\u0ce0-\u0ce1\u0cf1-\u0cf2\u0d05-\u0d0c\u0d0e-\u0d10\u0d12-\u0d3a\u0d3d\u0d4e\u0d54-\u0d56\u0d5f-\u0d61\u0d7a-\u0d7f\u0d85-\u0d96\u0d9a-\u0db1\u0db3-\u0dbb\u0dbd\u0dc0-\u0dc6\u0e01-\u0e30\u0e32\u0e40-\u0e46\u0e81-\u0e82\u0e84\u0e87-\u0e88\u0e8a\u0e8d\u0e94-\u0e97\u0e99-\u0e9f\u0ea1-\u0ea3\u0ea5\u0ea7\u0eaa-\u0eab\u0ead-\u0eb0\u0eb2\u0ebd\u0ec0-\u0ec4\u0ec6\u0edc-\u0edf\u0f00\u0f40-\u0f47\u0f49-\u0f6c\u0f88-\u0f8c\u1000-\u102a\u103f\u1050-\u1055\u105a-\u105d\u1061\u1065-\u1066\u106e-\u1070\u1075-\u1081\u108e\u10a0-\u10c5\u10c7\u10cd\u10d0-\u10fa\u10fc-\u1248\u124a-\u124d\u1250-\u1256\u1258\u125a-\u125d\u1260-\u1288\u128a-\u128d\u1290-\u12b0\u12b2-\u12b5\u12b8-\u12be\u12c0\u12c2-\u12c5\u12c8-\u12d6\u12d8-\u1310\u1312-\u1315\u1318-\u135a\u1380-\u138f\u13a0-\u13f5\u13f8-\u13fd\u1401-\u166c\u166f-\u167f\u1681-\u169a\u16a0-\u16ea\u16ee-\u16f8\u1700-\u170c\u170e-\u1711\u1720-\u1731\u1740-\u1751\u1760-\u176c\u176e-\u1770\u1780-\u17b3\u17d7\u17dc\u1820-\u1878\u1880-\u18a8\u18aa\u18b0-\u18f5\u1900-\u191e\u1950-\u196d\u1970-\u1974\u1980-\u19ab\u19b0-\u19c9\u1a00-\u1a16\u1a20-\u1a54\u1aa7\u1b05-\u1b33\u1b45-\u1b4b\u1b83-\u1ba0\u1bae-\u1baf\u1bba-\u1be5\u1c00-\u1c23\u1c4d-\u1c4f\u1c5a-\u1c7d\u1c80-\u1c88\u1c90-\u1cba\u1cbd-\u1cbf\u1ce9-\u1cec\u1cee-\u1cf1\u1cf5-\u1cf6\u1d00-\u1dbf\u1e00-\u1f15\u1f18-\u1f1d\u1f20-\u1f45\u1f48-\u1f4d\u1f50-\u1f57\u1f59\u1f5b\u1f5d\u1f5f-\u1f7d\u1f80-\u1fb4\u1fb6-\u1fbc\u1fbe\u1fc2-\u1fc4\u1fc6-\u1fcc\u1fd0-\u1fd3\u1fd6-\u1fdb\u1fe0-\u1fec\u1ff2-\u1ff4\u1ff6-\u1ffc\u2071\u207f\u2090-\u209c\u2102\u2107\u210a-\u2113\u2115\u2118-\u211d\u2124\u2126\u2128\u212a-\u2139\u213c-\u213f\u2145-\u2149\u214e\u2160-\u2188\u2c00-\u2c2e\u2c30-\u2c5e\u2c60-\u2ce4\u2ceb-\u2cee\u2cf2-\u2cf3\u2d00-\u2d25\u2d27\u2d2d\u2d30-\u2d67\u2d6f\u2d80-\u2d96\u2da0-\u2da6\u2da8-\u2dae\u2db0-\u2db6\u2db8-\u2dbe\u2dc0-\u2dc6\u2dc8-\u2dce\u2dd0-\u2dd6\u2dd8-\u2dde\u3005-\u3007\u3021-\u3029\u3031-\u3035\u3038-\u303c\u3041-\u3096\u309d-\u309f\u30a1-\u30fa\u30fc-\u30ff\u3105-\u312f\u3131-\u318e\u31a0-\u31ba\u31f0-\u31ff\u3400-\u4db5\u4e00-\u9fef\ua000-\ua48c\ua4d0-\ua4fd\ua500-\ua60c\ua610-\ua61f\ua62a-\ua62b\ua640-\ua66e\ua67f-\ua69d\ua6a0-\ua6ef\ua717-\ua71f\ua722-\ua788\ua78b-\ua7b9\ua7f7-\ua801\ua803-\ua805\ua807-\ua80a\ua80c-\ua822\ua840-\ua873\ua882-\ua8b3\ua8f2-\ua8f7\ua8fb\ua8fd-\ua8fe\ua90a-\ua925\ua930-\ua946\ua960-\ua97c\ua984-\ua9b2\ua9cf\ua9e0-\ua9e4\ua9e6-\ua9ef\ua9fa-\ua9fe\uaa00-\uaa28\uaa40-\uaa42\uaa44-\uaa4b\uaa60-\uaa76\uaa7a\uaa7e-\uaaaf\uaab1\uaab5-\uaab6\uaab9-\uaabd\uaac0\uaac2\uaadb-\uaadd\uaae0-\uaaea\uaaf2-\uaaf4\uab01-\uab06\uab09-\uab0e\uab11-\uab16\uab20-\uab26\uab28-\uab2e\uab30-\uab5a\uab5c-\uab65\uab70-\uabe2\uac00-\ud7a3\ud7b0-\ud7c6\ud7cb-\ud7fb\uf900-\ufa6d\ufa70-\ufad9\ufb00-\ufb06\ufb13-\ufb17\ufb1d\ufb1f-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufbb1\ufbd3-\ufc5d\ufc64-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdf9\ufe71\ufe73\ufe77\ufe79\ufe7b\ufe7d\ufe7f-\ufefc\uff21-\uff3a\uff41-\uff5a\uff66-\uff9d\uffa0-\uffbe\uffc2-\uffc7\uffca-\uffcf\uffd2-\uffd7\uffda-\uffdc\U00010000-\U0001000b\U0001000d-\U00010026\U00010028-\U0001003a\U0001003c-\U0001003d\U0001003f-\U0001004d\U00010050-\U0001005d\U00010080-\U000100fa\U00010140-\U00010174\U00010280-\U0001029c\U000102a0-\U000102d0\U00010300-\U0001031f\U0001032d-\U0001034a\U00010350-\U00010375\U00010380-\U0001039d\U000103a0-\U000103c3\U000103c8-\U000103cf\U000103d1-\U000103d5\U00010400-\U0001049d\U000104b0-\U000104d3\U000104d8-\U000104fb\U00010500-\U00010527\U00010530-\U00010563\U00010600-\U00010736\U00010740-\U00010755\U00010760-\U00010767\U00010800-\U00010805\U00010808\U0001080a-\U00010835\U00010837-\U00010838\U0001083c\U0001083f-\U00010855\U00010860-\U00010876\U00010880-\U0001089e\U000108e0-\U000108f2\U000108f4-\U000108f5\U00010900-\U00010915\U00010920-\U00010939\U00010980-\U000109b7\U000109be-\U000109bf\U00010a00\U00010a10-\U00010a13\U00010a15-\U00010a17\U00010a19-\U00010a35\U00010a60-\U00010a7c\U00010a80-\U00010a9c\U00010ac0-\U00010ac7\U00010ac9-\U00010ae4\U00010b00-\U00010b35\U00010b40-\U00010b55\U00010b60-\U00010b72\U00010b80-\U00010b91\U00010c00-\U00010c48\U00010c80-\U00010cb2\U00010cc0-\U00010cf2\U00010d00-\U00010d23\U00010f00-\U00010f1c\U00010f27\U00010f30-\U00010f45\U00011003-\U00011037\U00011083-\U000110af\U000110d0-\U000110e8\U00011103-\U00011126\U00011144\U00011150-\U00011172\U00011176\U00011183-\U000111b2\U000111c1-\U000111c4\U000111da\U000111dc\U00011200-\U00011211\U00011213-\U0001122b\U00011280-\U00011286\U00011288\U0001128a-\U0001128d\U0001128f-\U0001129d\U0001129f-\U000112a8\U000112b0-\U000112de\U00011305-\U0001130c\U0001130f-\U00011310\U00011313-\U00011328\U0001132a-\U00011330\U00011332-\U00011333\U00011335-\U00011339\U0001133d\U00011350\U0001135d-\U00011361\U00011400-\U00011434\U00011447-\U0001144a\U00011480-\U000114af\U000114c4-\U000114c5\U000114c7\U00011580-\U000115ae\U000115d8-\U000115db\U00011600-\U0001162f\U00011644\U00011680-\U000116aa\U00011700-\U0001171a\U00011800-\U0001182b\U000118a0-\U000118df\U000118ff\U00011a00\U00011a0b-\U00011a32\U00011a3a\U00011a50\U00011a5c-\U00011a83\U00011a86-\U00011a89\U00011a9d\U00011ac0-\U00011af8\U00011c00-\U00011c08\U00011c0a-\U00011c2e\U00011c40\U00011c72-\U00011c8f\U00011d00-\U00011d06\U00011d08-\U00011d09\U00011d0b-\U00011d30\U00011d46\U00011d60-\U00011d65\U00011d67-\U00011d68\U00011d6a-\U00011d89\U00011d98\U00011ee0-\U00011ef2\U00012000-\U00012399\U00012400-\U0001246e\U00012480-\U00012543\U00013000-\U0001342e\U00014400-\U00014646\U00016800-\U00016a38\U00016a40-\U00016a5e\U00016ad0-\U00016aed\U00016b00-\U00016b2f\U00016b40-\U00016b43\U00016b63-\U00016b77\U00016b7d-\U00016b8f\U00016e40-\U00016e7f\U00016f00-\U00016f44\U00016f50\U00016f93-\U00016f9f\U00016fe0-\U00016fe1\U00017000-\U000187f1\U00018800-\U00018af2\U0001b000-\U0001b11e\U0001b170-\U0001b2fb\U0001bc00-\U0001bc6a\U0001bc70-\U0001bc7c\U0001bc80-\U0001bc88\U0001bc90-\U0001bc99\U0001d400-\U0001d454\U0001d456-\U0001d49c\U0001d49e-\U0001d49f\U0001d4a2\U0001d4a5-\U0001d4a6\U0001d4a9-\U0001d4ac\U0001d4ae-\U0001d4b9\U0001d4bb\U0001d4bd-\U0001d4c3\U0001d4c5-\U0001d505\U0001d507-\U0001d50a\U0001d50d-\U0001d514\U0001d516-\U0001d51c\U0001d51e-\U0001d539\U0001d53b-\U0001d53e\U0001d540-\U0001d544\U0001d546\U0001d54a-\U0001d550\U0001d552-\U0001d6a5\U0001d6a8-\U0001d6c0\U0001d6c2-\U0001d6da\U0001d6dc-\U0001d6fa\U0001d6fc-\U0001d714\U0001d716-\U0001d734\U0001d736-\U0001d74e\U0001d750-\U0001d76e\U0001d770-\U0001d788\U0001d78a-\U0001d7a8\U0001d7aa-\U0001d7c2\U0001d7c4-\U0001d7cb\U0001e800-\U0001e8c4\U0001e900-\U0001e943\U0001ee00-\U0001ee03\U0001ee05-\U0001ee1f\U0001ee21-\U0001ee22\U0001ee24\U0001ee27\U0001ee29-\U0001ee32\U0001ee34-\U0001ee37\U0001ee39\U0001ee3b\U0001ee42\U0001ee47\U0001ee49\U0001ee4b\U0001ee4d-\U0001ee4f\U0001ee51-\U0001ee52\U0001ee54\U0001ee57\U0001ee59\U0001ee5b\U0001ee5d\U0001ee5f\U0001ee61-\U0001ee62\U0001ee64\U0001ee67-\U0001ee6a\U0001ee6c-\U0001ee72\U0001ee74-\U0001ee77\U0001ee79-\U0001ee7c\U0001ee7e\U0001ee80-\U0001ee89\U0001ee8b-\U0001ee9b\U0001eea1-\U0001eea3\U0001eea5-\U0001eea9\U0001eeab-\U0001eebb\U00020000-\U0002a6d6\U0002a700-\U0002b734\U0002b740-\U0002b81d\U0002b820-\U0002cea1\U0002ceb0-\U0002ebe0\U0002f800-\U0002fa1d'

cats = ['Cc', 'Cf', 'Cn', 'Co', 'Cs', 'Ll', 'Lm', 'Lo', 'Lt', 'Lu', 'Mc', 'Me', 'Mn', 'Nd', 'Nl', 'No', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zl', 'Zp', 'Zs']

# Generated from unidata 11.0.0

def combine(*args):
    return ''.join(globals()[cat] for cat in args)


def allexcept(*args):
    newcats = cats[:]
    for arg in args:
        newcats.remove(arg)
    return ''.join(globals()[cat] for cat in newcats)


def _handle_runs(char_list):  # pragma: no cover
    buf = []
    for c in char_list:
        if len(c) == 1:
            if buf and buf[-1][1] == chr(ord(c)-1):
                buf[-1] = (buf[-1][0], c)
            else:
                buf.append((c, c))
        else:
            buf.append((c, c))
    for a, b in buf:
        if a == b:
            yield a
        else:
            yield f'{a}-{b}'


if __name__ == '__main__':  # pragma: no cover
    import unicodedata

    categories = {'xid_start': [], 'xid_continue': []}

    with open(__file__, encoding='utf-8') as fp:
        content = fp.read()

    header = content[:content.find('Cc =')]
    footer = content[content.find("def combine("):]

    for code in range(0x110000):
        c = chr(code)
        cat = unicodedata.category(c)
        if ord(c) == 0xdc00:
            # Hack to avoid combining this combining with the preceding high
            # surrogate, 0xdbff, when doing a repr.
            c = '\\' + c
        elif ord(c) in (0x2d, 0x5b, 0x5c, 0x5d, 0x5e):
            # Escape regex metachars.
            c = '\\' + c
        categories.setdefault(cat, []).append(c)
        # XID_START and XID_CONTINUE are special categories used for matching
        # identifiers in Python 3.
        if c.isidentifier():
            categories['xid_start'].append(c)
        if ('a' + c).isidentifier():
            categories['xid_continue'].append(c)

    with open(__file__, 'w', encoding='utf-8') as fp:
        fp.write(header)

        for cat in sorted(categories):
            val = ''.join(_handle_runs(categories[cat]))
            fp.write(f'{cat} = {val!a}\n\n')

        cats = sorted(categories)
        cats.remove('xid_start')
        cats.remove('xid_continue')
        fp.write(f'cats = {cats!r}\n\n')

        fp.write(f'# Generated from unidata {unicodedata.unidata_version}\n\n')

        fp.write(footer)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\terminal_theme.py ===
from typing import List, Optional, Tuple

from .color_triplet import ColorTriplet
from .palette import Palette

_ColorTuple = Tuple[int, int, int]


class TerminalTheme:
    """A color theme used when exporting console content.

    Args:
        background (Tuple[int, int, int]): The background color.
        foreground (Tuple[int, int, int]): The foreground (text) color.
        normal (List[Tuple[int, int, int]]): A list of 8 normal intensity colors.
        bright (List[Tuple[int, int, int]], optional): A list of 8 bright colors, or None
            to repeat normal intensity. Defaults to None.
    """

    def __init__(
        self,
        background: _ColorTuple,
        foreground: _ColorTuple,
        normal: List[_ColorTuple],
        bright: Optional[List[_ColorTuple]] = None,
    ) -> None:
        self.background_color = ColorTriplet(*background)
        self.foreground_color = ColorTriplet(*foreground)
        self.ansi_colors = Palette(normal + (bright or normal))


DEFAULT_TERMINAL_THEME = TerminalTheme(
    (255, 255, 255),
    (0, 0, 0),
    [
        (0, 0, 0),
        (128, 0, 0),
        (0, 128, 0),
        (128, 128, 0),
        (0, 0, 128),
        (128, 0, 128),
        (0, 128, 128),
        (192, 192, 192),
    ],
    [
        (128, 128, 128),
        (255, 0, 0),
        (0, 255, 0),
        (255, 255, 0),
        (0, 0, 255),
        (255, 0, 255),
        (0, 255, 255),
        (255, 255, 255),
    ],
)

MONOKAI = TerminalTheme(
    (12, 12, 12),
    (217, 217, 217),
    [
        (26, 26, 26),
        (244, 0, 95),
        (152, 224, 36),
        (253, 151, 31),
        (157, 101, 255),
        (244, 0, 95),
        (88, 209, 235),
        (196, 197, 181),
        (98, 94, 76),
    ],
    [
        (244, 0, 95),
        (152, 224, 36),
        (224, 213, 97),
        (157, 101, 255),
        (244, 0, 95),
        (88, 209, 235),
        (246, 246, 239),
    ],
)
DIMMED_MONOKAI = TerminalTheme(
    (25, 25, 25),
    (185, 188, 186),
    [
        (58, 61, 67),
        (190, 63, 72),
        (135, 154, 59),
        (197, 166, 53),
        (79, 118, 161),
        (133, 92, 141),
        (87, 143, 164),
        (185, 188, 186),
        (136, 137, 135),
    ],
    [
        (251, 0, 31),
        (15, 114, 47),
        (196, 112, 51),
        (24, 109, 227),
        (251, 0, 103),
        (46, 112, 109),
        (253, 255, 185),
    ],
)
NIGHT_OWLISH = TerminalTheme(
    (255, 255, 255),
    (64, 63, 83),
    [
        (1, 22, 39),
        (211, 66, 62),
        (42, 162, 152),
        (218, 170, 1),
        (72, 118, 214),
        (64, 63, 83),
        (8, 145, 106),
        (122, 129, 129),
        (122, 129, 129),
    ],
    [
        (247, 110, 110),
        (73, 208, 197),
        (218, 194, 107),
        (92, 167, 228),
        (105, 112, 152),
        (0, 201, 144),
        (152, 159, 177),
    ],
)

SVG_EXPORT_THEME = TerminalTheme(
    (41, 41, 41),
    (197, 200, 198),
    [
        (75, 78, 85),
        (204, 85, 90),
        (152, 168, 75),
        (208, 179, 68),
        (96, 138, 177),
        (152, 114, 159),
        (104, 160, 179),
        (197, 200, 198),
        (154, 155, 153),
    ],
    [
        (255, 38, 39),
        (0, 130, 61),
        (208, 132, 66),
        (25, 132, 233),
        (255, 44, 122),
        (57, 130, 128),
        (253, 253, 197),
    ],
)

# === NexusCore/openenv\Lib\site-packages\h11\_receivebuffer.py ===
import re
import sys
from typing import List, Optional, Union

__all__ = ["ReceiveBuffer"]


# Operations we want to support:
# - find next \r\n or \r\n\r\n (\n or \n\n are also acceptable),
#   or wait until there is one
# - read at-most-N bytes
# Goals:
# - on average, do this fast
# - worst case, do this in O(n) where n is the number of bytes processed
# Plan:
# - store bytearray, offset, how far we've searched for a separator token
# - use the how-far-we've-searched data to avoid rescanning
# - while doing a stream of uninterrupted processing, advance offset instead
#   of constantly copying
# WARNING:
# - I haven't benchmarked or profiled any of this yet.
#
# Note that starting in Python 3.4, deleting the initial n bytes from a
# bytearray is amortized O(n), thanks to some excellent work by Antoine
# Martin:
#
#     https://bugs.python.org/issue19087
#
# This means that if we only supported 3.4+, we could get rid of the code here
# involving self._start and self.compress, because it's doing exactly the same
# thing that bytearray now does internally.
#
# BUT unfortunately, we still support 2.7, and reading short segments out of a
# long buffer MUST be O(bytes read) to avoid DoS issues, so we can't actually
# delete this code. Yet:
#
#     https://pythonclock.org/
#
# (Two things to double-check first though: make sure PyPy also has the
# optimization, and benchmark to make sure it's a win, since we do have a
# slightly clever thing where we delay calling compress() until we've
# processed a whole event, which could in theory be slightly more efficient
# than the internal bytearray support.)
blank_line_regex = re.compile(b"\n\r?\n", re.MULTILINE)


class ReceiveBuffer:
    def __init__(self) -> None:
        self._data = bytearray()
        self._next_line_search = 0
        self._multiple_lines_search = 0

    def __iadd__(self, byteslike: Union[bytes, bytearray]) -> "ReceiveBuffer":
        self._data += byteslike
        return self

    def __bool__(self) -> bool:
        return bool(len(self))

    def __len__(self) -> int:
        return len(self._data)

    # for @property unprocessed_data
    def __bytes__(self) -> bytes:
        return bytes(self._data)

    def _extract(self, count: int) -> bytearray:
        # extracting an initial slice of the data buffer and return it
        out = self._data[:count]
        del self._data[:count]

        self._next_line_search = 0
        self._multiple_lines_search = 0

        return out

    def maybe_extract_at_most(self, count: int) -> Optional[bytearray]:
        """
        Extract a fixed number of bytes from the buffer.
        """
        out = self._data[:count]
        if not out:
            return None

        return self._extract(count)

    def maybe_extract_next_line(self) -> Optional[bytearray]:
        """
        Extract the first line, if it is completed in the buffer.
        """
        # Only search in buffer space that we've not already looked at.
        search_start_index = max(0, self._next_line_search - 1)
        partial_idx = self._data.find(b"\r\n", search_start_index)

        if partial_idx == -1:
            self._next_line_search = len(self._data)
            return None

        # + 2 is to compensate len(b"\r\n")
        idx = partial_idx + 2

        return self._extract(idx)

    def maybe_extract_lines(self) -> Optional[List[bytearray]]:
        """
        Extract everything up to the first blank line, and return a list of lines.
        """
        # Handle the case where we have an immediate empty line.
        if self._data[:1] == b"\n":
            self._extract(1)
            return []

        if self._data[:2] == b"\r\n":
            self._extract(2)
            return []

        # Only search in buffer space that we've not already looked at.
        match = blank_line_regex.search(self._data, self._multiple_lines_search)
        if match is None:
            self._multiple_lines_search = max(0, len(self._data) - 2)
            return None

        # Truncate the buffer and return it.
        idx = match.span(0)[-1]
        out = self._extract(idx)
        lines = out.split(b"\n")

        for line in lines:
            if line.endswith(b"\r"):
                del line[-1]

        assert lines[-2] == lines[-1] == b""

        del lines[-2:]

        return lines

    # In theory we should wait until `\r\n` before starting to validate
    # incoming data. However it's interesting to detect (very) invalid data
    # early given they might not even contain `\r\n` at all (hence only
    # timeout will get rid of them).
    # This is not a 100% effective detection but more of a cheap sanity check
    # allowing for early abort in some useful cases.
    # This is especially interesting when peer is messing up with HTTPS and
    # sent us a TLS stream where we were expecting plain HTTP given all
    # versions of TLS so far start handshake with a 0x16 message type code.
    def is_next_line_obviously_invalid_request_line(self) -> bool:
        try:
            # HTTP header line must not contain non-printable characters
            # and should not start with a space
            return self._data[0] < 0x21
        except IndexError:
            return False

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc8017.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# PKCS #1: RSA Cryptography Specifications Version 2.2
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc8017.txt
#

from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import univ

from pyasn1_modules import rfc2437
from pyasn1_modules import rfc3447
from pyasn1_modules import rfc4055
from pyasn1_modules import rfc5280

MAX = float('inf')


# Import Algorithm Identifier from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier

class DigestAlgorithm(AlgorithmIdentifier):
    pass

class HashAlgorithm(AlgorithmIdentifier):
    pass

class MaskGenAlgorithm(AlgorithmIdentifier):
    pass

class PSourceAlgorithm(AlgorithmIdentifier):
    pass


# Object identifiers from NIST SHA2

hashAlgs = univ.ObjectIdentifier('2.16.840.1.101.3.4.2')
id_sha256 = rfc4055.id_sha256
id_sha384 = rfc4055.id_sha384
id_sha512 = rfc4055.id_sha512
id_sha224 = rfc4055.id_sha224
id_sha512_224 = hashAlgs + (5, )
id_sha512_256 = hashAlgs + (6, )


# Basic object identifiers

pkcs_1 = univ.ObjectIdentifier('1.2.840.113549.1.1')
rsaEncryption = rfc2437.rsaEncryption
id_RSAES_OAEP = rfc2437.id_RSAES_OAEP
id_pSpecified = rfc2437.id_pSpecified
id_RSASSA_PSS = rfc4055.id_RSASSA_PSS
md2WithRSAEncryption = rfc2437.md2WithRSAEncryption
md5WithRSAEncryption = rfc2437.md5WithRSAEncryption
sha1WithRSAEncryption = rfc2437.sha1WithRSAEncryption
sha224WithRSAEncryption = rfc4055.sha224WithRSAEncryption
sha256WithRSAEncryption = rfc4055.sha256WithRSAEncryption
sha384WithRSAEncryption = rfc4055.sha384WithRSAEncryption
sha512WithRSAEncryption = rfc4055.sha512WithRSAEncryption
sha512_224WithRSAEncryption = pkcs_1 + (15, )
sha512_256WithRSAEncryption = pkcs_1 + (16, )
id_sha1 = rfc2437.id_sha1
id_md2 = univ.ObjectIdentifier('1.2.840.113549.2.2')
id_md5 = univ.ObjectIdentifier('1.2.840.113549.2.5')
id_mgf1 = rfc2437.id_mgf1


# Default parameter values

sha1 = rfc4055.sha1Identifier
SHA1Parameters = univ.Null("")

mgf1SHA1 = rfc4055.mgf1SHA1Identifier

class EncodingParameters(univ.OctetString):
    subtypeSpec = constraint.ValueSizeConstraint(0, MAX)

pSpecifiedEmpty = rfc4055.pSpecifiedEmptyIdentifier

emptyString = EncodingParameters(value='')


# Main structures

class Version(univ.Integer):
    namedValues = namedval.NamedValues(
        ('two-prime', 0),
        ('multi', 1)
    )

class TrailerField(univ.Integer):
    namedValues = namedval.NamedValues(
       ('trailerFieldBC', 1)
    )

RSAPublicKey = rfc2437.RSAPublicKey

OtherPrimeInfo = rfc3447.OtherPrimeInfo
OtherPrimeInfos = rfc3447.OtherPrimeInfos
RSAPrivateKey = rfc3447.RSAPrivateKey

RSAES_OAEP_params = rfc4055.RSAES_OAEP_params
rSAES_OAEP_Default_Identifier = rfc4055.rSAES_OAEP_Default_Identifier

RSASSA_PSS_params = rfc4055.RSASSA_PSS_params
rSASSA_PSS_Default_Identifier = rfc4055.rSASSA_PSS_Default_Identifier


# Syntax for the EMSA-PKCS1-v1_5 hash identifier

class DigestInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('digestAlgorithm', DigestAlgorithm()),
        namedtype.NamedType('digest', univ.OctetString())
    )


# Update the Algorithm Identifier map

_algorithmIdentifierMapUpdate = {
    id_sha1: univ.Null(),
    id_sha224: univ.Null(),
    id_sha256: univ.Null(),
    id_sha384: univ.Null(),
    id_sha512: univ.Null(),
    id_sha512_224: univ.Null(),
    id_sha512_256: univ.Null(),
    id_mgf1: AlgorithmIdentifier(),
    id_pSpecified: univ.OctetString(),
    id_RSAES_OAEP: RSAES_OAEP_params(),
    id_RSASSA_PSS: RSASSA_PSS_params(),
    md2WithRSAEncryption: univ.Null(),
    md5WithRSAEncryption: univ.Null(),
    sha1WithRSAEncryption: univ.Null(),
    sha224WithRSAEncryption: univ.Null(),
    sha256WithRSAEncryption: univ.Null(),
    sha384WithRSAEncryption: univ.Null(),
    sha512WithRSAEncryption: univ.Null(),
    sha512_224WithRSAEncryption: univ.Null(),
    sha512_256WithRSAEncryption: univ.Null(),
}

rfc5280.algorithmIdentifierMap.update(_algorithmIdentifierMapUpdate)

# === NexusCore/openenv\Lib\site-packages\pygments\unistring.py ===
"""
    pygments.unistring
    ~~~~~~~~~~~~~~~~~~

    Strings of all Unicode characters of a certain category.
    Used for matching in Unicode-aware languages. Run to regenerate.

    Inspired by chartypes_create.py from the MoinMoin project.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

Cc = '\x00-\x1f\x7f-\x9f'

Cf = '\xad\u0600-\u0605\u061c\u06dd\u070f\u08e2\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u206f\ufeff\ufff9-\ufffb\U000110bd\U000110cd\U0001bca0-\U0001bca3\U0001d173-\U0001d17a\U000e0001\U000e0020-\U000e007f'

Cn = '\u0378-\u0379\u0380-\u0383\u038b\u038d\u03a2\u0530\u0557-\u0558\u058b-\u058c\u0590\u05c8-\u05cf\u05eb-\u05ee\u05f5-\u05ff\u061d\u070e\u074b-\u074c\u07b2-\u07bf\u07fb-\u07fc\u082e-\u082f\u083f\u085c-\u085d\u085f\u086b-\u089f\u08b5\u08be-\u08d2\u0984\u098d-\u098e\u0991-\u0992\u09a9\u09b1\u09b3-\u09b5\u09ba-\u09bb\u09c5-\u09c6\u09c9-\u09ca\u09cf-\u09d6\u09d8-\u09db\u09de\u09e4-\u09e5\u09ff-\u0a00\u0a04\u0a0b-\u0a0e\u0a11-\u0a12\u0a29\u0a31\u0a34\u0a37\u0a3a-\u0a3b\u0a3d\u0a43-\u0a46\u0a49-\u0a4a\u0a4e-\u0a50\u0a52-\u0a58\u0a5d\u0a5f-\u0a65\u0a77-\u0a80\u0a84\u0a8e\u0a92\u0aa9\u0ab1\u0ab4\u0aba-\u0abb\u0ac6\u0aca\u0ace-\u0acf\u0ad1-\u0adf\u0ae4-\u0ae5\u0af2-\u0af8\u0b00\u0b04\u0b0d-\u0b0e\u0b11-\u0b12\u0b29\u0b31\u0b34\u0b3a-\u0b3b\u0b45-\u0b46\u0b49-\u0b4a\u0b4e-\u0b55\u0b58-\u0b5b\u0b5e\u0b64-\u0b65\u0b78-\u0b81\u0b84\u0b8b-\u0b8d\u0b91\u0b96-\u0b98\u0b9b\u0b9d\u0ba0-\u0ba2\u0ba5-\u0ba7\u0bab-\u0bad\u0bba-\u0bbd\u0bc3-\u0bc5\u0bc9\u0bce-\u0bcf\u0bd1-\u0bd6\u0bd8-\u0be5\u0bfb-\u0bff\u0c0d\u0c11\u0c29\u0c3a-\u0c3c\u0c45\u0c49\u0c4e-\u0c54\u0c57\u0c5b-\u0c5f\u0c64-\u0c65\u0c70-\u0c77\u0c8d\u0c91\u0ca9\u0cb4\u0cba-\u0cbb\u0cc5\u0cc9\u0cce-\u0cd4\u0cd7-\u0cdd\u0cdf\u0ce4-\u0ce5\u0cf0\u0cf3-\u0cff\u0d04\u0d0d\u0d11\u0d45\u0d49\u0d50-\u0d53\u0d64-\u0d65\u0d80-\u0d81\u0d84\u0d97-\u0d99\u0db2\u0dbc\u0dbe-\u0dbf\u0dc7-\u0dc9\u0dcb-\u0dce\u0dd5\u0dd7\u0de0-\u0de5\u0df0-\u0df1\u0df5-\u0e00\u0e3b-\u0e3e\u0e5c-\u0e80\u0e83\u0e85-\u0e86\u0e89\u0e8b-\u0e8c\u0e8e-\u0e93\u0e98\u0ea0\u0ea4\u0ea6\u0ea8-\u0ea9\u0eac\u0eba\u0ebe-\u0ebf\u0ec5\u0ec7\u0ece-\u0ecf\u0eda-\u0edb\u0ee0-\u0eff\u0f48\u0f6d-\u0f70\u0f98\u0fbd\u0fcd\u0fdb-\u0fff\u10c6\u10c8-\u10cc\u10ce-\u10cf\u1249\u124e-\u124f\u1257\u1259\u125e-\u125f\u1289\u128e-\u128f\u12b1\u12b6-\u12b7\u12bf\u12c1\u12c6-\u12c7\u12d7\u1311\u1316-\u1317\u135b-\u135c\u137d-\u137f\u139a-\u139f\u13f6-\u13f7\u13fe-\u13ff\u169d-\u169f\u16f9-\u16ff\u170d\u1715-\u171f\u1737-\u173f\u1754-\u175f\u176d\u1771\u1774-\u177f\u17de-\u17df\u17ea-\u17ef\u17fa-\u17ff\u180f\u181a-\u181f\u1879-\u187f\u18ab-\u18af\u18f6-\u18ff\u191f\u192c-\u192f\u193c-\u193f\u1941-\u1943\u196e-\u196f\u1975-\u197f\u19ac-\u19af\u19ca-\u19cf\u19db-\u19dd\u1a1c-\u1a1d\u1a5f\u1a7d-\u1a7e\u1a8a-\u1a8f\u1a9a-\u1a9f\u1aae-\u1aaf\u1abf-\u1aff\u1b4c-\u1b4f\u1b7d-\u1b7f\u1bf4-\u1bfb\u1c38-\u1c3a\u1c4a-\u1c4c\u1c89-\u1c8f\u1cbb-\u1cbc\u1cc8-\u1ccf\u1cfa-\u1cff\u1dfa\u1f16-\u1f17\u1f1e-\u1f1f\u1f46-\u1f47\u1f4e-\u1f4f\u1f58\u1f5a\u1f5c\u1f5e\u1f7e-\u1f7f\u1fb5\u1fc5\u1fd4-\u1fd5\u1fdc\u1ff0-\u1ff1\u1ff5\u1fff\u2065\u2072-\u2073\u208f\u209d-\u209f\u20c0-\u20cf\u20f1-\u20ff\u218c-\u218f\u2427-\u243f\u244b-\u245f\u2b74-\u2b75\u2b96-\u2b97\u2bc9\u2bff\u2c2f\u2c5f\u2cf4-\u2cf8\u2d26\u2d28-\u2d2c\u2d2e-\u2d2f\u2d68-\u2d6e\u2d71-\u2d7e\u2d97-\u2d9f\u2da7\u2daf\u2db7\u2dbf\u2dc7\u2dcf\u2dd7\u2ddf\u2e4f-\u2e7f\u2e9a\u2ef4-\u2eff\u2fd6-\u2fef\u2ffc-\u2fff\u3040\u3097-\u3098\u3100-\u3104\u3130\u318f\u31bb-\u31bf\u31e4-\u31ef\u321f\u32ff\u4db6-\u4dbf\u9ff0-\u9fff\ua48d-\ua48f\ua4c7-\ua4cf\ua62c-\ua63f\ua6f8-\ua6ff\ua7ba-\ua7f6\ua82c-\ua82f\ua83a-\ua83f\ua878-\ua87f\ua8c6-\ua8cd\ua8da-\ua8df\ua954-\ua95e\ua97d-\ua97f\ua9ce\ua9da-\ua9dd\ua9ff\uaa37-\uaa3f\uaa4e-\uaa4f\uaa5a-\uaa5b\uaac3-\uaada\uaaf7-\uab00\uab07-\uab08\uab0f-\uab10\uab17-\uab1f\uab27\uab2f\uab66-\uab6f\uabee-\uabef\uabfa-\uabff\ud7a4-\ud7af\ud7c7-\ud7ca\ud7fc-\ud7ff\ufa6e-\ufa6f\ufada-\ufaff\ufb07-\ufb12\ufb18-\ufb1c\ufb37\ufb3d\ufb3f\ufb42\ufb45\ufbc2-\ufbd2\ufd40-\ufd4f\ufd90-\ufd91\ufdc8-\ufdef\ufdfe-\ufdff\ufe1a-\ufe1f\ufe53\ufe67\ufe6c-\ufe6f\ufe75\ufefd-\ufefe\uff00\uffbf-\uffc1\uffc8-\uffc9\uffd0-\uffd1\uffd8-\uffd9\uffdd-\uffdf\uffe7\uffef-\ufff8\ufffe-\uffff\U0001000c\U00010027\U0001003b\U0001003e\U0001004e-\U0001004f\U0001005e-\U0001007f\U000100fb-\U000100ff\U00010103-\U00010106\U00010134-\U00010136\U0001018f\U0001019c-\U0001019f\U000101a1-\U000101cf\U000101fe-\U0001027f\U0001029d-\U0001029f\U000102d1-\U000102df\U000102fc-\U000102ff\U00010324-\U0001032c\U0001034b-\U0001034f\U0001037b-\U0001037f\U0001039e\U000103c4-\U000103c7\U000103d6-\U000103ff\U0001049e-\U0001049f\U000104aa-\U000104af\U000104d4-\U000104d7\U000104fc-\U000104ff\U00010528-\U0001052f\U00010564-\U0001056e\U00010570-\U000105ff\U00010737-\U0001073f\U00010756-\U0001075f\U00010768-\U000107ff\U00010806-\U00010807\U00010809\U00010836\U00010839-\U0001083b\U0001083d-\U0001083e\U00010856\U0001089f-\U000108a6\U000108b0-\U000108df\U000108f3\U000108f6-\U000108fa\U0001091c-\U0001091e\U0001093a-\U0001093e\U00010940-\U0001097f\U000109b8-\U000109bb\U000109d0-\U000109d1\U00010a04\U00010a07-\U00010a0b\U00010a14\U00010a18\U00010a36-\U00010a37\U00010a3b-\U00010a3e\U00010a49-\U00010a4f\U00010a59-\U00010a5f\U00010aa0-\U00010abf\U00010ae7-\U00010aea\U00010af7-\U00010aff\U00010b36-\U00010b38\U00010b56-\U00010b57\U00010b73-\U00010b77\U00010b92-\U00010b98\U00010b9d-\U00010ba8\U00010bb0-\U00010bff\U00010c49-\U00010c7f\U00010cb3-\U00010cbf\U00010cf3-\U00010cf9\U00010d28-\U00010d2f\U00010d3a-\U00010e5f\U00010e7f-\U00010eff\U00010f28-\U00010f2f\U00010f5a-\U00010fff\U0001104e-\U00011051\U00011070-\U0001107e\U000110c2-\U000110cc\U000110ce-\U000110cf\U000110e9-\U000110ef\U000110fa-\U000110ff\U00011135\U00011147-\U0001114f\U00011177-\U0001117f\U000111ce-\U000111cf\U000111e0\U000111f5-\U000111ff\U00011212\U0001123f-\U0001127f\U00011287\U00011289\U0001128e\U0001129e\U000112aa-\U000112af\U000112eb-\U000112ef\U000112fa-\U000112ff\U00011304\U0001130d-\U0001130e\U00011311-\U00011312\U00011329\U00011331\U00011334\U0001133a\U00011345-\U00011346\U00011349-\U0001134a\U0001134e-\U0001134f\U00011351-\U00011356\U00011358-\U0001135c\U00011364-\U00011365\U0001136d-\U0001136f\U00011375-\U000113ff\U0001145a\U0001145c\U0001145f-\U0001147f\U000114c8-\U000114cf\U000114da-\U0001157f\U000115b6-\U000115b7\U000115de-\U000115ff\U00011645-\U0001164f\U0001165a-\U0001165f\U0001166d-\U0001167f\U000116b8-\U000116bf\U000116ca-\U000116ff\U0001171b-\U0001171c\U0001172c-\U0001172f\U00011740-\U000117ff\U0001183c-\U0001189f\U000118f3-\U000118fe\U00011900-\U000119ff\U00011a48-\U00011a4f\U00011a84-\U00011a85\U00011aa3-\U00011abf\U00011af9-\U00011bff\U00011c09\U00011c37\U00011c46-\U00011c4f\U00011c6d-\U00011c6f\U00011c90-\U00011c91\U00011ca8\U00011cb7-\U00011cff\U00011d07\U00011d0a\U00011d37-\U00011d39\U00011d3b\U00011d3e\U00011d48-\U00011d4f\U00011d5a-\U00011d5f\U00011d66\U00011d69\U00011d8f\U00011d92\U00011d99-\U00011d9f\U00011daa-\U00011edf\U00011ef9-\U00011fff\U0001239a-\U000123ff\U0001246f\U00012475-\U0001247f\U00012544-\U00012fff\U0001342f-\U000143ff\U00014647-\U000167ff\U00016a39-\U00016a3f\U00016a5f\U00016a6a-\U00016a6d\U00016a70-\U00016acf\U00016aee-\U00016aef\U00016af6-\U00016aff\U00016b46-\U00016b4f\U00016b5a\U00016b62\U00016b78-\U00016b7c\U00016b90-\U00016e3f\U00016e9b-\U00016eff\U00016f45-\U00016f4f\U00016f7f-\U00016f8e\U00016fa0-\U00016fdf\U00016fe2-\U00016fff\U000187f2-\U000187ff\U00018af3-\U0001afff\U0001b11f-\U0001b16f\U0001b2fc-\U0001bbff\U0001bc6b-\U0001bc6f\U0001bc7d-\U0001bc7f\U0001bc89-\U0001bc8f\U0001bc9a-\U0001bc9b\U0001bca4-\U0001cfff\U0001d0f6-\U0001d0ff\U0001d127-\U0001d128\U0001d1e9-\U0001d1ff\U0001d246-\U0001d2df\U0001d2f4-\U0001d2ff\U0001d357-\U0001d35f\U0001d379-\U0001d3ff\U0001d455\U0001d49d\U0001d4a0-\U0001d4a1\U0001d4a3-\U0001d4a4\U0001d4a7-\U0001d4a8\U0001d4ad\U0001d4ba\U0001d4bc\U0001d4c4\U0001d506\U0001d50b-\U0001d50c\U0001d515\U0001d51d\U0001d53a\U0001d53f\U0001d545\U0001d547-\U0001d549\U0001d551\U0001d6a6-\U0001d6a7\U0001d7cc-\U0001d7cd\U0001da8c-\U0001da9a\U0001daa0\U0001dab0-\U0001dfff\U0001e007\U0001e019-\U0001e01a\U0001e022\U0001e025\U0001e02b-\U0001e7ff\U0001e8c5-\U0001e8c6\U0001e8d7-\U0001e8ff\U0001e94b-\U0001e94f\U0001e95a-\U0001e95d\U0001e960-\U0001ec70\U0001ecb5-\U0001edff\U0001ee04\U0001ee20\U0001ee23\U0001ee25-\U0001ee26\U0001ee28\U0001ee33\U0001ee38\U0001ee3a\U0001ee3c-\U0001ee41\U0001ee43-\U0001ee46\U0001ee48\U0001ee4a\U0001ee4c\U0001ee50\U0001ee53\U0001ee55-\U0001ee56\U0001ee58\U0001ee5a\U0001ee5c\U0001ee5e\U0001ee60\U0001ee63\U0001ee65-\U0001ee66\U0001ee6b\U0001ee73\U0001ee78\U0001ee7d\U0001ee7f\U0001ee8a\U0001ee9c-\U0001eea0\U0001eea4\U0001eeaa\U0001eebc-\U0001eeef\U0001eef2-\U0001efff\U0001f02c-\U0001f02f\U0001f094-\U0001f09f\U0001f0af-\U0001f0b0\U0001f0c0\U0001f0d0\U0001f0f6-\U0001f0ff\U0001f10d-\U0001f10f\U0001f16c-\U0001f16f\U0001f1ad-\U0001f1e5\U0001f203-\U0001f20f\U0001f23c-\U0001f23f\U0001f249-\U0001f24f\U0001f252-\U0001f25f\U0001f266-\U0001f2ff\U0001f6d5-\U0001f6df\U0001f6ed-\U0001f6ef\U0001f6fa-\U0001f6ff\U0001f774-\U0001f77f\U0001f7d9-\U0001f7ff\U0001f80c-\U0001f80f\U0001f848-\U0001f84f\U0001f85a-\U0001f85f\U0001f888-\U0001f88f\U0001f8ae-\U0001f8ff\U0001f90c-\U0001f90f\U0001f93f\U0001f971-\U0001f972\U0001f977-\U0001f979\U0001f97b\U0001f9a3-\U0001f9af\U0001f9ba-\U0001f9bf\U0001f9c3-\U0001f9cf\U0001fa00-\U0001fa5f\U0001fa6e-\U0001ffff\U0002a6d7-\U0002a6ff\U0002b735-\U0002b73f\U0002b81e-\U0002b81f\U0002cea2-\U0002ceaf\U0002ebe1-\U0002f7ff\U0002fa1e-\U000e0000\U000e0002-\U000e001f\U000e0080-\U000e00ff\U000e01f0-\U000effff\U000ffffe-\U000fffff\U0010fffe-\U0010ffff'

Co = '\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd'

Cs = '\ud800-\udbff\\\udc00\udc01-\udfff'

Ll = 'a-z\xb5\xdf-\xf6\xf8-\xff\u0101\u0103\u0105\u0107\u0109\u010b\u010d\u010f\u0111\u0113\u0115\u0117\u0119\u011b\u011d\u011f\u0121\u0123\u0125\u0127\u0129\u012b\u012d\u012f\u0131\u0133\u0135\u0137-\u0138\u013a\u013c\u013e\u0140\u0142\u0144\u0146\u0148-\u0149\u014b\u014d\u014f\u0151\u0153\u0155\u0157\u0159\u015b\u015d\u015f\u0161\u0163\u0165\u0167\u0169\u016b\u016d\u016f\u0171\u0173\u0175\u0177\u017a\u017c\u017e-\u0180\u0183\u0185\u0188\u018c-\u018d\u0192\u0195\u0199-\u019b\u019e\u01a1\u01a3\u01a5\u01a8\u01aa-\u01ab\u01ad\u01b0\u01b4\u01b6\u01b9-\u01ba\u01bd-\u01bf\u01c6\u01c9\u01cc\u01ce\u01d0\u01d2\u01d4\u01d6\u01d8\u01da\u01dc-\u01dd\u01df\u01e1\u01e3\u01e5\u01e7\u01e9\u01eb\u01ed\u01ef-\u01f0\u01f3\u01f5\u01f9\u01fb\u01fd\u01ff\u0201\u0203\u0205\u0207\u0209\u020b\u020d\u020f\u0211\u0213\u0215\u0217\u0219\u021b\u021d\u021f\u0221\u0223\u0225\u0227\u0229\u022b\u022d\u022f\u0231\u0233-\u0239\u023c\u023f-\u0240\u0242\u0247\u0249\u024b\u024d\u024f-\u0293\u0295-\u02af\u0371\u0373\u0377\u037b-\u037d\u0390\u03ac-\u03ce\u03d0-\u03d1\u03d5-\u03d7\u03d9\u03db\u03dd\u03df\u03e1\u03e3\u03e5\u03e7\u03e9\u03eb\u03ed\u03ef-\u03f3\u03f5\u03f8\u03fb-\u03fc\u0430-\u045f\u0461\u0463\u0465\u0467\u0469\u046b\u046d\u046f\u0471\u0473\u0475\u0477\u0479\u047b\u047d\u047f\u0481\u048b\u048d\u048f\u0491\u0493\u0495\u0497\u0499\u049b\u049d\u049f\u04a1\u04a3\u04a5\u04a7\u04a9\u04ab\u04ad\u04af\u04b1\u04b3\u04b5\u04b7\u04b9\u04bb\u04bd\u04bf\u04c2\u04c4\u04c6\u04c8\u04ca\u04cc\u04ce-\u04cf\u04d1\u04d3\u04d5\u04d7\u04d9\u04db\u04dd\u04df\u04e1\u04e3\u04e5\u04e7\u04e9\u04eb\u04ed\u04ef\u04f1\u04f3\u04f5\u04f7\u04f9\u04fb\u04fd\u04ff\u0501\u0503\u0505\u0507\u0509\u050b\u050d\u050f\u0511\u0513\u0515\u0517\u0519\u051b\u051d\u051f\u0521\u0523\u0525\u0527\u0529\u052b\u052d\u052f\u0560-\u0588\u10d0-\u10fa\u10fd-\u10ff\u13f8-\u13fd\u1c80-\u1c88\u1d00-\u1d2b\u1d6b-\u1d77\u1d79-\u1d9a\u1e01\u1e03\u1e05\u1e07\u1e09\u1e0b\u1e0d\u1e0f\u1e11\u1e13\u1e15\u1e17\u1e19\u1e1b\u1e1d\u1e1f\u1e21\u1e23\u1e25\u1e27\u1e29\u1e2b\u1e2d\u1e2f\u1e31\u1e33\u1e35\u1e37\u1e39\u1e3b\u1e3d\u1e3f\u1e41\u1e43\u1e45\u1e47\u1e49\u1e4b\u1e4d\u1e4f\u1e51\u1e53\u1e55\u1e57\u1e59\u1e5b\u1e5d\u1e5f\u1e61\u1e63\u1e65\u1e67\u1e69\u1e6b\u1e6d\u1e6f\u1e71\u1e73\u1e75\u1e77\u1e79\u1e7b\u1e7d\u1e7f\u1e81\u1e83\u1e85\u1e87\u1e89\u1e8b\u1e8d\u1e8f\u1e91\u1e93\u1e95-\u1e9d\u1e9f\u1ea1\u1ea3\u1ea5\u1ea7\u1ea9\u1eab\u1ead\u1eaf\u1eb1\u1eb3\u1eb5\u1eb7\u1eb9\u1ebb\u1ebd\u1ebf\u1ec1\u1ec3\u1ec5\u1ec7\u1ec9\u1ecb\u1ecd\u1ecf\u1ed1\u1ed3\u1ed5\u1ed7\u1ed9\u1edb\u1edd\u1edf\u1ee1\u1ee3\u1ee5\u1ee7\u1ee9\u1eeb\u1eed\u1eef\u1ef1\u1ef3\u1ef5\u1ef7\u1ef9\u1efb\u1efd\u1eff-\u1f07\u1f10-\u1f15\u1f20-\u1f27\u1f30-\u1f37\u1f40-\u1f45\u1f50-\u1f57\u1f60-\u1f67\u1f70-\u1f7d\u1f80-\u1f87\u1f90-\u1f97\u1fa0-\u1fa7\u1fb0-\u1fb4\u1fb6-\u1fb7\u1fbe\u1fc2-\u1fc4\u1fc6-\u1fc7\u1fd0-\u1fd3\u1fd6-\u1fd7\u1fe0-\u1fe7\u1ff2-\u1ff4\u1ff6-\u1ff7\u210a\u210e-\u210f\u2113\u212f\u2134\u2139\u213c-\u213d\u2146-\u2149\u214e\u2184\u2c30-\u2c5e\u2c61\u2c65-\u2c66\u2c68\u2c6a\u2c6c\u2c71\u2c73-\u2c74\u2c76-\u2c7b\u2c81\u2c83\u2c85\u2c87\u2c89\u2c8b\u2c8d\u2c8f\u2c91\u2c93\u2c95\u2c97\u2c99\u2c9b\u2c9d\u2c9f\u2ca1\u2ca3\u2ca5\u2ca7\u2ca9\u2cab\u2cad\u2caf\u2cb1\u2cb3\u2cb5\u2cb7\u2cb9\u2cbb\u2cbd\u2cbf\u2cc1\u2cc3\u2cc5\u2cc7\u2cc9\u2ccb\u2ccd\u2ccf\u2cd1\u2cd3\u2cd5\u2cd7\u2cd9\u2cdb\u2cdd\u2cdf\u2ce1\u2ce3-\u2ce4\u2cec\u2cee\u2cf3\u2d00-\u2d25\u2d27\u2d2d\ua641\ua643\ua645\ua647\ua649\ua64b\ua64d\ua64f\ua651\ua653\ua655\ua657\ua659\ua65b\ua65d\ua65f\ua661\ua663\ua665\ua667\ua669\ua66b\ua66d\ua681\ua683\ua685\ua687\ua689\ua68b\ua68d\ua68f\ua691\ua693\ua695\ua697\ua699\ua69b\ua723\ua725\ua727\ua729\ua72b\ua72d\ua72f-\ua731\ua733\ua735\ua737\ua739\ua73b\ua73d\ua73f\ua741\ua743\ua745\ua747\ua749\ua74b\ua74d\ua74f\ua751\ua753\ua755\ua757\ua759\ua75b\ua75d\ua75f\ua761\ua763\ua765\ua767\ua769\ua76b\ua76d\ua76f\ua771-\ua778\ua77a\ua77c\ua77f\ua781\ua783\ua785\ua787\ua78c\ua78e\ua791\ua793-\ua795\ua797\ua799\ua79b\ua79d\ua79f\ua7a1\ua7a3\ua7a5\ua7a7\ua7a9\ua7af\ua7b5\ua7b7\ua7b9\ua7fa\uab30-\uab5a\uab60-\uab65\uab70-\uabbf\ufb00-\ufb06\ufb13-\ufb17\uff41-\uff5a\U00010428-\U0001044f\U000104d8-\U000104fb\U00010cc0-\U00010cf2\U000118c0-\U000118df\U00016e60-\U00016e7f\U0001d41a-\U0001d433\U0001d44e-\U0001d454\U0001d456-\U0001d467\U0001d482-\U0001d49b\U0001d4b6-\U0001d4b9\U0001d4bb\U0001d4bd-\U0001d4c3\U0001d4c5-\U0001d4cf\U0001d4ea-\U0001d503\U0001d51e-\U0001d537\U0001d552-\U0001d56b\U0001d586-\U0001d59f\U0001d5ba-\U0001d5d3\U0001d5ee-\U0001d607\U0001d622-\U0001d63b\U0001d656-\U0001d66f\U0001d68a-\U0001d6a5\U0001d6c2-\U0001d6da\U0001d6dc-\U0001d6e1\U0001d6fc-\U0001d714\U0001d716-\U0001d71b\U0001d736-\U0001d74e\U0001d750-\U0001d755\U0001d770-\U0001d788\U0001d78a-\U0001d78f\U0001d7aa-\U0001d7c2\U0001d7c4-\U0001d7c9\U0001d7cb\U0001e922-\U0001e943'

Lm = '\u02b0-\u02c1\u02c6-\u02d1\u02e0-\u02e4\u02ec\u02ee\u0374\u037a\u0559\u0640\u06e5-\u06e6\u07f4-\u07f5\u07fa\u081a\u0824\u0828\u0971\u0e46\u0ec6\u10fc\u17d7\u1843\u1aa7\u1c78-\u1c7d\u1d2c-\u1d6a\u1d78\u1d9b-\u1dbf\u2071\u207f\u2090-\u209c\u2c7c-\u2c7d\u2d6f\u2e2f\u3005\u3031-\u3035\u303b\u309d-\u309e\u30fc-\u30fe\ua015\ua4f8-\ua4fd\ua60c\ua67f\ua69c-\ua69d\ua717-\ua71f\ua770\ua788\ua7f8-\ua7f9\ua9cf\ua9e6\uaa70\uaadd\uaaf3-\uaaf4\uab5c-\uab5f\uff70\uff9e-\uff9f\U00016b40-\U00016b43\U00016f93-\U00016f9f\U00016fe0-\U00016fe1'

Lo = '\xaa\xba\u01bb\u01c0-\u01c3\u0294\u05d0-\u05ea\u05ef-\u05f2\u0620-\u063f\u0641-\u064a\u066e-\u066f\u0671-\u06d3\u06d5\u06ee-\u06ef\u06fa-\u06fc\u06ff\u0710\u0712-\u072f\u074d-\u07a5\u07b1\u07ca-\u07ea\u0800-\u0815\u0840-\u0858\u0860-\u086a\u08a0-\u08b4\u08b6-\u08bd\u0904-\u0939\u093d\u0950\u0958-\u0961\u0972-\u0980\u0985-\u098c\u098f-\u0990\u0993-\u09a8\u09aa-\u09b0\u09b2\u09b6-\u09b9\u09bd\u09ce\u09dc-\u09dd\u09df-\u09e1\u09f0-\u09f1\u09fc\u0a05-\u0a0a\u0a0f-\u0a10\u0a13-\u0a28\u0a2a-\u0a30\u0a32-\u0a33\u0a35-\u0a36\u0a38-\u0a39\u0a59-\u0a5c\u0a5e\u0a72-\u0a74\u0a85-\u0a8d\u0a8f-\u0a91\u0a93-\u0aa8\u0aaa-\u0ab0\u0ab2-\u0ab3\u0ab5-\u0ab9\u0abd\u0ad0\u0ae0-\u0ae1\u0af9\u0b05-\u0b0c\u0b0f-\u0b10\u0b13-\u0b28\u0b2a-\u0b30\u0b32-\u0b33\u0b35-\u0b39\u0b3d\u0b5c-\u0b5d\u0b5f-\u0b61\u0b71\u0b83\u0b85-\u0b8a\u0b8e-\u0b90\u0b92-\u0b95\u0b99-\u0b9a\u0b9c\u0b9e-\u0b9f\u0ba3-\u0ba4\u0ba8-\u0baa\u0bae-\u0bb9\u0bd0\u0c05-\u0c0c\u0c0e-\u0c10\u0c12-\u0c28\u0c2a-\u0c39\u0c3d\u0c58-\u0c5a\u0c60-\u0c61\u0c80\u0c85-\u0c8c\u0c8e-\u0c90\u0c92-\u0ca8\u0caa-\u0cb3\u0cb5-\u0cb9\u0cbd\u0cde\u0ce0-\u0ce1\u0cf1-\u0cf2\u0d05-\u0d0c\u0d0e-\u0d10\u0d12-\u0d3a\u0d3d\u0d4e\u0d54-\u0d56\u0d5f-\u0d61\u0d7a-\u0d7f\u0d85-\u0d96\u0d9a-\u0db1\u0db3-\u0dbb\u0dbd\u0dc0-\u0dc6\u0e01-\u0e30\u0e32-\u0e33\u0e40-\u0e45\u0e81-\u0e82\u0e84\u0e87-\u0e88\u0e8a\u0e8d\u0e94-\u0e97\u0e99-\u0e9f\u0ea1-\u0ea3\u0ea5\u0ea7\u0eaa-\u0eab\u0ead-\u0eb0\u0eb2-\u0eb3\u0ebd\u0ec0-\u0ec4\u0edc-\u0edf\u0f00\u0f40-\u0f47\u0f49-\u0f6c\u0f88-\u0f8c\u1000-\u102a\u103f\u1050-\u1055\u105a-\u105d\u1061\u1065-\u1066\u106e-\u1070\u1075-\u1081\u108e\u1100-\u1248\u124a-\u124d\u1250-\u1256\u1258\u125a-\u125d\u1260-\u1288\u128a-\u128d\u1290-\u12b0\u12b2-\u12b5\u12b8-\u12be\u12c0\u12c2-\u12c5\u12c8-\u12d6\u12d8-\u1310\u1312-\u1315\u1318-\u135a\u1380-\u138f\u1401-\u166c\u166f-\u167f\u1681-\u169a\u16a0-\u16ea\u16f1-\u16f8\u1700-\u170c\u170e-\u1711\u1720-\u1731\u1740-\u1751\u1760-\u176c\u176e-\u1770\u1780-\u17b3\u17dc\u1820-\u1842\u1844-\u1878\u1880-\u1884\u1887-\u18a8\u18aa\u18b0-\u18f5\u1900-\u191e\u1950-\u196d\u1970-\u1974\u1980-\u19ab\u19b0-\u19c9\u1a00-\u1a16\u1a20-\u1a54\u1b05-\u1b33\u1b45-\u1b4b\u1b83-\u1ba0\u1bae-\u1baf\u1bba-\u1be5\u1c00-\u1c23\u1c4d-\u1c4f\u1c5a-\u1c77\u1ce9-\u1cec\u1cee-\u1cf1\u1cf5-\u1cf6\u2135-\u2138\u2d30-\u2d67\u2d80-\u2d96\u2da0-\u2da6\u2da8-\u2dae\u2db0-\u2db6\u2db8-\u2dbe\u2dc0-\u2dc6\u2dc8-\u2dce\u2dd0-\u2dd6\u2dd8-\u2dde\u3006\u303c\u3041-\u3096\u309f\u30a1-\u30fa\u30ff\u3105-\u312f\u3131-\u318e\u31a0-\u31ba\u31f0-\u31ff\u3400-\u4db5\u4e00-\u9fef\ua000-\ua014\ua016-\ua48c\ua4d0-\ua4f7\ua500-\ua60b\ua610-\ua61f\ua62a-\ua62b\ua66e\ua6a0-\ua6e5\ua78f\ua7f7\ua7fb-\ua801\ua803-\ua805\ua807-\ua80a\ua80c-\ua822\ua840-\ua873\ua882-\ua8b3\ua8f2-\ua8f7\ua8fb\ua8fd-\ua8fe\ua90a-\ua925\ua930-\ua946\ua960-\ua97c\ua984-\ua9b2\ua9e0-\ua9e4\ua9e7-\ua9ef\ua9fa-\ua9fe\uaa00-\uaa28\uaa40-\uaa42\uaa44-\uaa4b\uaa60-\uaa6f\uaa71-\uaa76\uaa7a\uaa7e-\uaaaf\uaab1\uaab5-\uaab6\uaab9-\uaabd\uaac0\uaac2\uaadb-\uaadc\uaae0-\uaaea\uaaf2\uab01-\uab06\uab09-\uab0e\uab11-\uab16\uab20-\uab26\uab28-\uab2e\uabc0-\uabe2\uac00-\ud7a3\ud7b0-\ud7c6\ud7cb-\ud7fb\uf900-\ufa6d\ufa70-\ufad9\ufb1d\ufb1f-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufbb1\ufbd3-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdfb\ufe70-\ufe74\ufe76-\ufefc\uff66-\uff6f\uff71-\uff9d\uffa0-\uffbe\uffc2-\uffc7\uffca-\uffcf\uffd2-\uffd7\uffda-\uffdc\U00010000-\U0001000b\U0001000d-\U00010026\U00010028-\U0001003a\U0001003c-\U0001003d\U0001003f-\U0001004d\U00010050-\U0001005d\U00010080-\U000100fa\U00010280-\U0001029c\U000102a0-\U000102d0\U00010300-\U0001031f\U0001032d-\U00010340\U00010342-\U00010349\U00010350-\U00010375\U00010380-\U0001039d\U000103a0-\U000103c3\U000103c8-\U000103cf\U00010450-\U0001049d\U00010500-\U00010527\U00010530-\U00010563\U00010600-\U00010736\U00010740-\U00010755\U00010760-\U00010767\U00010800-\U00010805\U00010808\U0001080a-\U00010835\U00010837-\U00010838\U0001083c\U0001083f-\U00010855\U00010860-\U00010876\U00010880-\U0001089e\U000108e0-\U000108f2\U000108f4-\U000108f5\U00010900-\U00010915\U00010920-\U00010939\U00010980-\U000109b7\U000109be-\U000109bf\U00010a00\U00010a10-\U00010a13\U00010a15-\U00010a17\U00010a19-\U00010a35\U00010a60-\U00010a7c\U00010a80-\U00010a9c\U00010ac0-\U00010ac7\U00010ac9-\U00010ae4\U00010b00-\U00010b35\U00010b40-\U00010b55\U00010b60-\U00010b72\U00010b80-\U00010b91\U00010c00-\U00010c48\U00010d00-\U00010d23\U00010f00-\U00010f1c\U00010f27\U00010f30-\U00010f45\U00011003-\U00011037\U00011083-\U000110af\U000110d0-\U000110e8\U00011103-\U00011126\U00011144\U00011150-\U00011172\U00011176\U00011183-\U000111b2\U000111c1-\U000111c4\U000111da\U000111dc\U00011200-\U00011211\U00011213-\U0001122b\U00011280-\U00011286\U00011288\U0001128a-\U0001128d\U0001128f-\U0001129d\U0001129f-\U000112a8\U000112b0-\U000112de\U00011305-\U0001130c\U0001130f-\U00011310\U00011313-\U00011328\U0001132a-\U00011330\U00011332-\U00011333\U00011335-\U00011339\U0001133d\U00011350\U0001135d-\U00011361\U00011400-\U00011434\U00011447-\U0001144a\U00011480-\U000114af\U000114c4-\U000114c5\U000114c7\U00011580-\U000115ae\U000115d8-\U000115db\U00011600-\U0001162f\U00011644\U00011680-\U000116aa\U00011700-\U0001171a\U00011800-\U0001182b\U000118ff\U00011a00\U00011a0b-\U00011a32\U00011a3a\U00011a50\U00011a5c-\U00011a83\U00011a86-\U00011a89\U00011a9d\U00011ac0-\U00011af8\U00011c00-\U00011c08\U00011c0a-\U00011c2e\U00011c40\U00011c72-\U00011c8f\U00011d00-\U00011d06\U00011d08-\U00011d09\U00011d0b-\U00011d30\U00011d46\U00011d60-\U00011d65\U00011d67-\U00011d68\U00011d6a-\U00011d89\U00011d98\U00011ee0-\U00011ef2\U00012000-\U00012399\U00012480-\U00012543\U00013000-\U0001342e\U00014400-\U00014646\U00016800-\U00016a38\U00016a40-\U00016a5e\U00016ad0-\U00016aed\U00016b00-\U00016b2f\U00016b63-\U00016b77\U00016b7d-\U00016b8f\U00016f00-\U00016f44\U00016f50\U00017000-\U000187f1\U00018800-\U00018af2\U0001b000-\U0001b11e\U0001b170-\U0001b2fb\U0001bc00-\U0001bc6a\U0001bc70-\U0001bc7c\U0001bc80-\U0001bc88\U0001bc90-\U0001bc99\U0001e800-\U0001e8c4\U0001ee00-\U0001ee03\U0001ee05-\U0001ee1f\U0001ee21-\U0001ee22\U0001ee24\U0001ee27\U0001ee29-\U0001ee32\U0001ee34-\U0001ee37\U0001ee39\U0001ee3b\U0001ee42\U0001ee47\U0001ee49\U0001ee4b\U0001ee4d-\U0001ee4f\U0001ee51-\U0001ee52\U0001ee54\U0001ee57\U0001ee59\U0001ee5b\U0001ee5d\U0001ee5f\U0001ee61-\U0001ee62\U0001ee64\U0001ee67-\U0001ee6a\U0001ee6c-\U0001ee72\U0001ee74-\U0001ee77\U0001ee79-\U0001ee7c\U0001ee7e\U0001ee80-\U0001ee89\U0001ee8b-\U0001ee9b\U0001eea1-\U0001eea3\U0001eea5-\U0001eea9\U0001eeab-\U0001eebb\U00020000-\U0002a6d6\U0002a700-\U0002b734\U0002b740-\U0002b81d\U0002b820-\U0002cea1\U0002ceb0-\U0002ebe0\U0002f800-\U0002fa1d'

Lt = '\u01c5\u01c8\u01cb\u01f2\u1f88-\u1f8f\u1f98-\u1f9f\u1fa8-\u1faf\u1fbc\u1fcc\u1ffc'

Lu = 'A-Z\xc0-\xd6\xd8-\xde\u0100\u0102\u0104\u0106\u0108\u010a\u010c\u010e\u0110\u0112\u0114\u0116\u0118\u011a\u011c\u011e\u0120\u0122\u0124\u0126\u0128\u012a\u012c\u012e\u0130\u0132\u0134\u0136\u0139\u013b\u013d\u013f\u0141\u0143\u0145\u0147\u014a\u014c\u014e\u0150\u0152\u0154\u0156\u0158\u015a\u015c\u015e\u0160\u0162\u0164\u0166\u0168\u016a\u016c\u016e\u0170\u0172\u0174\u0176\u0178-\u0179\u017b\u017d\u0181-\u0182\u0184\u0186-\u0187\u0189-\u018b\u018e-\u0191\u0193-\u0194\u0196-\u0198\u019c-\u019d\u019f-\u01a0\u01a2\u01a4\u01a6-\u01a7\u01a9\u01ac\u01ae-\u01af\u01b1-\u01b3\u01b5\u01b7-\u01b8\u01bc\u01c4\u01c7\u01ca\u01cd\u01cf\u01d1\u01d3\u01d5\u01d7\u01d9\u01db\u01de\u01e0\u01e2\u01e4\u01e6\u01e8\u01ea\u01ec\u01ee\u01f1\u01f4\u01f6-\u01f8\u01fa\u01fc\u01fe\u0200\u0202\u0204\u0206\u0208\u020a\u020c\u020e\u0210\u0212\u0214\u0216\u0218\u021a\u021c\u021e\u0220\u0222\u0224\u0226\u0228\u022a\u022c\u022e\u0230\u0232\u023a-\u023b\u023d-\u023e\u0241\u0243-\u0246\u0248\u024a\u024c\u024e\u0370\u0372\u0376\u037f\u0386\u0388-\u038a\u038c\u038e-\u038f\u0391-\u03a1\u03a3-\u03ab\u03cf\u03d2-\u03d4\u03d8\u03da\u03dc\u03de\u03e0\u03e2\u03e4\u03e6\u03e8\u03ea\u03ec\u03ee\u03f4\u03f7\u03f9-\u03fa\u03fd-\u042f\u0460\u0462\u0464\u0466\u0468\u046a\u046c\u046e\u0470\u0472\u0474\u0476\u0478\u047a\u047c\u047e\u0480\u048a\u048c\u048e\u0490\u0492\u0494\u0496\u0498\u049a\u049c\u049e\u04a0\u04a2\u04a4\u04a6\u04a8\u04aa\u04ac\u04ae\u04b0\u04b2\u04b4\u04b6\u04b8\u04ba\u04bc\u04be\u04c0-\u04c1\u04c3\u04c5\u04c7\u04c9\u04cb\u04cd\u04d0\u04d2\u04d4\u04d6\u04d8\u04da\u04dc\u04de\u04e0\u04e2\u04e4\u04e6\u04e8\u04ea\u04ec\u04ee\u04f0\u04f2\u04f4\u04f6\u04f8\u04fa\u04fc\u04fe\u0500\u0502\u0504\u0506\u0508\u050a\u050c\u050e\u0510\u0512\u0514\u0516\u0518\u051a\u051c\u051e\u0520\u0522\u0524\u0526\u0528\u052a\u052c\u052e\u0531-\u0556\u10a0-\u10c5\u10c7\u10cd\u13a0-\u13f5\u1c90-\u1cba\u1cbd-\u1cbf\u1e00\u1e02\u1e04\u1e06\u1e08\u1e0a\u1e0c\u1e0e\u1e10\u1e12\u1e14\u1e16\u1e18\u1e1a\u1e1c\u1e1e\u1e20\u1e22\u1e24\u1e26\u1e28\u1e2a\u1e2c\u1e2e\u1e30\u1e32\u1e34\u1e36\u1e38\u1e3a\u1e3c\u1e3e\u1e40\u1e42\u1e44\u1e46\u1e48\u1e4a\u1e4c\u1e4e\u1e50\u1e52\u1e54\u1e56\u1e58\u1e5a\u1e5c\u1e5e\u1e60\u1e62\u1e64\u1e66\u1e68\u1e6a\u1e6c\u1e6e\u1e70\u1e72\u1e74\u1e76\u1e78\u1e7a\u1e7c\u1e7e\u1e80\u1e82\u1e84\u1e86\u1e88\u1e8a\u1e8c\u1e8e\u1e90\u1e92\u1e94\u1e9e\u1ea0\u1ea2\u1ea4\u1ea6\u1ea8\u1eaa\u1eac\u1eae\u1eb0\u1eb2\u1eb4\u1eb6\u1eb8\u1eba\u1ebc\u1ebe\u1ec0\u1ec2\u1ec4\u1ec6\u1ec8\u1eca\u1ecc\u1ece\u1ed0\u1ed2\u1ed4\u1ed6\u1ed8\u1eda\u1edc\u1ede\u1ee0\u1ee2\u1ee4\u1ee6\u1ee8\u1eea\u1eec\u1eee\u1ef0\u1ef2\u1ef4\u1ef6\u1ef8\u1efa\u1efc\u1efe\u1f08-\u1f0f\u1f18-\u1f1d\u1f28-\u1f2f\u1f38-\u1f3f\u1f48-\u1f4d\u1f59\u1f5b\u1f5d\u1f5f\u1f68-\u1f6f\u1fb8-\u1fbb\u1fc8-\u1fcb\u1fd8-\u1fdb\u1fe8-\u1fec\u1ff8-\u1ffb\u2102\u2107\u210b-\u210d\u2110-\u2112\u2115\u2119-\u211d\u2124\u2126\u2128\u212a-\u212d\u2130-\u2133\u213e-\u213f\u2145\u2183\u2c00-\u2c2e\u2c60\u2c62-\u2c64\u2c67\u2c69\u2c6b\u2c6d-\u2c70\u2c72\u2c75\u2c7e-\u2c80\u2c82\u2c84\u2c86\u2c88\u2c8a\u2c8c\u2c8e\u2c90\u2c92\u2c94\u2c96\u2c98\u2c9a\u2c9c\u2c9e\u2ca0\u2ca2\u2ca4\u2ca6\u2ca8\u2caa\u2cac\u2cae\u2cb0\u2cb2\u2cb4\u2cb6\u2cb8\u2cba\u2cbc\u2cbe\u2cc0\u2cc2\u2cc4\u2cc6\u2cc8\u2cca\u2ccc\u2cce\u2cd0\u2cd2\u2cd4\u2cd6\u2cd8\u2cda\u2cdc\u2cde\u2ce0\u2ce2\u2ceb\u2ced\u2cf2\ua640\ua642\ua644\ua646\ua648\ua64a\ua64c\ua64e\ua650\ua652\ua654\ua656\ua658\ua65a\ua65c\ua65e\ua660\ua662\ua664\ua666\ua668\ua66a\ua66c\ua680\ua682\ua684\ua686\ua688\ua68a\ua68c\ua68e\ua690\ua692\ua694\ua696\ua698\ua69a\ua722\ua724\ua726\ua728\ua72a\ua72c\ua72e\ua732\ua734\ua736\ua738\ua73a\ua73c\ua73e\ua740\ua742\ua744\ua746\ua748\ua74a\ua74c\ua74e\ua750\ua752\ua754\ua756\ua758\ua75a\ua75c\ua75e\ua760\ua762\ua764\ua766\ua768\ua76a\ua76c\ua76e\ua779\ua77b\ua77d-\ua77e\ua780\ua782\ua784\ua786\ua78b\ua78d\ua790\ua792\ua796\ua798\ua79a\ua79c\ua79e\ua7a0\ua7a2\ua7a4\ua7a6\ua7a8\ua7aa-\ua7ae\ua7b0-\ua7b4\ua7b6\ua7b8\uff21-\uff3a\U00010400-\U00010427\U000104b0-\U000104d3\U00010c80-\U00010cb2\U000118a0-\U000118bf\U00016e40-\U00016e5f\U0001d400-\U0001d419\U0001d434-\U0001d44d\U0001d468-\U0001d481\U0001d49c\U0001d49e-\U0001d49f\U0001d4a2\U0001d4a5-\U0001d4a6\U0001d4a9-\U0001d4ac\U0001d4ae-\U0001d4b5\U0001d4d0-\U0001d4e9\U0001d504-\U0001d505\U0001d507-\U0001d50a\U0001d50d-\U0001d514\U0001d516-\U0001d51c\U0001d538-\U0001d539\U0001d53b-\U0001d53e\U0001d540-\U0001d544\U0001d546\U0001d54a-\U0001d550\U0001d56c-\U0001d585\U0001d5a0-\U0001d5b9\U0001d5d4-\U0001d5ed\U0001d608-\U0001d621\U0001d63c-\U0001d655\U0001d670-\U0001d689\U0001d6a8-\U0001d6c0\U0001d6e2-\U0001d6fa\U0001d71c-\U0001d734\U0001d756-\U0001d76e\U0001d790-\U0001d7a8\U0001d7ca\U0001e900-\U0001e921'

Mc = '\u0903\u093b\u093e-\u0940\u0949-\u094c\u094e-\u094f\u0982-\u0983\u09be-\u09c0\u09c7-\u09c8\u09cb-\u09cc\u09d7\u0a03\u0a3e-\u0a40\u0a83\u0abe-\u0ac0\u0ac9\u0acb-\u0acc\u0b02-\u0b03\u0b3e\u0b40\u0b47-\u0b48\u0b4b-\u0b4c\u0b57\u0bbe-\u0bbf\u0bc1-\u0bc2\u0bc6-\u0bc8\u0bca-\u0bcc\u0bd7\u0c01-\u0c03\u0c41-\u0c44\u0c82-\u0c83\u0cbe\u0cc0-\u0cc4\u0cc7-\u0cc8\u0cca-\u0ccb\u0cd5-\u0cd6\u0d02-\u0d03\u0d3e-\u0d40\u0d46-\u0d48\u0d4a-\u0d4c\u0d57\u0d82-\u0d83\u0dcf-\u0dd1\u0dd8-\u0ddf\u0df2-\u0df3\u0f3e-\u0f3f\u0f7f\u102b-\u102c\u1031\u1038\u103b-\u103c\u1056-\u1057\u1062-\u1064\u1067-\u106d\u1083-\u1084\u1087-\u108c\u108f\u109a-\u109c\u17b6\u17be-\u17c5\u17c7-\u17c8\u1923-\u1926\u1929-\u192b\u1930-\u1931\u1933-\u1938\u1a19-\u1a1a\u1a55\u1a57\u1a61\u1a63-\u1a64\u1a6d-\u1a72\u1b04\u1b35\u1b3b\u1b3d-\u1b41\u1b43-\u1b44\u1b82\u1ba1\u1ba6-\u1ba7\u1baa\u1be7\u1bea-\u1bec\u1bee\u1bf2-\u1bf3\u1c24-\u1c2b\u1c34-\u1c35\u1ce1\u1cf2-\u1cf3\u1cf7\u302e-\u302f\ua823-\ua824\ua827\ua880-\ua881\ua8b4-\ua8c3\ua952-\ua953\ua983\ua9b4-\ua9b5\ua9ba-\ua9bb\ua9bd-\ua9c0\uaa2f-\uaa30\uaa33-\uaa34\uaa4d\uaa7b\uaa7d\uaaeb\uaaee-\uaaef\uaaf5\uabe3-\uabe4\uabe6-\uabe7\uabe9-\uabea\uabec\U00011000\U00011002\U00011082\U000110b0-\U000110b2\U000110b7-\U000110b8\U0001112c\U00011145-\U00011146\U00011182\U000111b3-\U000111b5\U000111bf-\U000111c0\U0001122c-\U0001122e\U00011232-\U00011233\U00011235\U000112e0-\U000112e2\U00011302-\U00011303\U0001133e-\U0001133f\U00011341-\U00011344\U00011347-\U00011348\U0001134b-\U0001134d\U00011357\U00011362-\U00011363\U00011435-\U00011437\U00011440-\U00011441\U00011445\U000114b0-\U000114b2\U000114b9\U000114bb-\U000114be\U000114c1\U000115af-\U000115b1\U000115b8-\U000115bb\U000115be\U00011630-\U00011632\U0001163b-\U0001163c\U0001163e\U000116ac\U000116ae-\U000116af\U000116b6\U00011720-\U00011721\U00011726\U0001182c-\U0001182e\U00011838\U00011a39\U00011a57-\U00011a58\U00011a97\U00011c2f\U00011c3e\U00011ca9\U00011cb1\U00011cb4\U00011d8a-\U00011d8e\U00011d93-\U00011d94\U00011d96\U00011ef5-\U00011ef6\U00016f51-\U00016f7e\U0001d165-\U0001d166\U0001d16d-\U0001d172'

Me = '\u0488-\u0489\u1abe\u20dd-\u20e0\u20e2-\u20e4\ua670-\ua672'

Mn = '\u0300-\u036f\u0483-\u0487\u0591-\u05bd\u05bf\u05c1-\u05c2\u05c4-\u05c5\u05c7\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06dc\u06df-\u06e4\u06e7-\u06e8\u06ea-\u06ed\u0711\u0730-\u074a\u07a6-\u07b0\u07eb-\u07f3\u07fd\u0816-\u0819\u081b-\u0823\u0825-\u0827\u0829-\u082d\u0859-\u085b\u08d3-\u08e1\u08e3-\u0902\u093a\u093c\u0941-\u0948\u094d\u0951-\u0957\u0962-\u0963\u0981\u09bc\u09c1-\u09c4\u09cd\u09e2-\u09e3\u09fe\u0a01-\u0a02\u0a3c\u0a41-\u0a42\u0a47-\u0a48\u0a4b-\u0a4d\u0a51\u0a70-\u0a71\u0a75\u0a81-\u0a82\u0abc\u0ac1-\u0ac5\u0ac7-\u0ac8\u0acd\u0ae2-\u0ae3\u0afa-\u0aff\u0b01\u0b3c\u0b3f\u0b41-\u0b44\u0b4d\u0b56\u0b62-\u0b63\u0b82\u0bc0\u0bcd\u0c00\u0c04\u0c3e-\u0c40\u0c46-\u0c48\u0c4a-\u0c4d\u0c55-\u0c56\u0c62-\u0c63\u0c81\u0cbc\u0cbf\u0cc6\u0ccc-\u0ccd\u0ce2-\u0ce3\u0d00-\u0d01\u0d3b-\u0d3c\u0d41-\u0d44\u0d4d\u0d62-\u0d63\u0dca\u0dd2-\u0dd4\u0dd6\u0e31\u0e34-\u0e3a\u0e47-\u0e4e\u0eb1\u0eb4-\u0eb9\u0ebb-\u0ebc\u0ec8-\u0ecd\u0f18-\u0f19\u0f35\u0f37\u0f39\u0f71-\u0f7e\u0f80-\u0f84\u0f86-\u0f87\u0f8d-\u0f97\u0f99-\u0fbc\u0fc6\u102d-\u1030\u1032-\u1037\u1039-\u103a\u103d-\u103e\u1058-\u1059\u105e-\u1060\u1071-\u1074\u1082\u1085-\u1086\u108d\u109d\u135d-\u135f\u1712-\u1714\u1732-\u1734\u1752-\u1753\u1772-\u1773\u17b4-\u17b5\u17b7-\u17bd\u17c6\u17c9-\u17d3\u17dd\u180b-\u180d\u1885-\u1886\u18a9\u1920-\u1922\u1927-\u1928\u1932\u1939-\u193b\u1a17-\u1a18\u1a1b\u1a56\u1a58-\u1a5e\u1a60\u1a62\u1a65-\u1a6c\u1a73-\u1a7c\u1a7f\u1ab0-\u1abd\u1b00-\u1b03\u1b34\u1b36-\u1b3a\u1b3c\u1b42\u1b6b-\u1b73\u1b80-\u1b81\u1ba2-\u1ba5\u1ba8-\u1ba9\u1bab-\u1bad\u1be6\u1be8-\u1be9\u1bed\u1bef-\u1bf1\u1c2c-\u1c33\u1c36-\u1c37\u1cd0-\u1cd2\u1cd4-\u1ce0\u1ce2-\u1ce8\u1ced\u1cf4\u1cf8-\u1cf9\u1dc0-\u1df9\u1dfb-\u1dff\u20d0-\u20dc\u20e1\u20e5-\u20f0\u2cef-\u2cf1\u2d7f\u2de0-\u2dff\u302a-\u302d\u3099-\u309a\ua66f\ua674-\ua67d\ua69e-\ua69f\ua6f0-\ua6f1\ua802\ua806\ua80b\ua825-\ua826\ua8c4-\ua8c5\ua8e0-\ua8f1\ua8ff\ua926-\ua92d\ua947-\ua951\ua980-\ua982\ua9b3\ua9b6-\ua9b9\ua9bc\ua9e5\uaa29-\uaa2e\uaa31-\uaa32\uaa35-\uaa36\uaa43\uaa4c\uaa7c\uaab0\uaab2-\uaab4\uaab7-\uaab8\uaabe-\uaabf\uaac1\uaaec-\uaaed\uaaf6\uabe5\uabe8\uabed\ufb1e\ufe00-\ufe0f\ufe20-\ufe2f\U000101fd\U000102e0\U00010376-\U0001037a\U00010a01-\U00010a03\U00010a05-\U00010a06\U00010a0c-\U00010a0f\U00010a38-\U00010a3a\U00010a3f\U00010ae5-\U00010ae6\U00010d24-\U00010d27\U00010f46-\U00010f50\U00011001\U00011038-\U00011046\U0001107f-\U00011081\U000110b3-\U000110b6\U000110b9-\U000110ba\U00011100-\U00011102\U00011127-\U0001112b\U0001112d-\U00011134\U00011173\U00011180-\U00011181\U000111b6-\U000111be\U000111c9-\U000111cc\U0001122f-\U00011231\U00011234\U00011236-\U00011237\U0001123e\U000112df\U000112e3-\U000112ea\U00011300-\U00011301\U0001133b-\U0001133c\U00011340\U00011366-\U0001136c\U00011370-\U00011374\U00011438-\U0001143f\U00011442-\U00011444\U00011446\U0001145e\U000114b3-\U000114b8\U000114ba\U000114bf-\U000114c0\U000114c2-\U000114c3\U000115b2-\U000115b5\U000115bc-\U000115bd\U000115bf-\U000115c0\U000115dc-\U000115dd\U00011633-\U0001163a\U0001163d\U0001163f-\U00011640\U000116ab\U000116ad\U000116b0-\U000116b5\U000116b7\U0001171d-\U0001171f\U00011722-\U00011725\U00011727-\U0001172b\U0001182f-\U00011837\U00011839-\U0001183a\U00011a01-\U00011a0a\U00011a33-\U00011a38\U00011a3b-\U00011a3e\U00011a47\U00011a51-\U00011a56\U00011a59-\U00011a5b\U00011a8a-\U00011a96\U00011a98-\U00011a99\U00011c30-\U00011c36\U00011c38-\U00011c3d\U00011c3f\U00011c92-\U00011ca7\U00011caa-\U00011cb0\U00011cb2-\U00011cb3\U00011cb5-\U00011cb6\U00011d31-\U00011d36\U00011d3a\U00011d3c-\U00011d3d\U00011d3f-\U00011d45\U00011d47\U00011d90-\U00011d91\U00011d95\U00011d97\U00011ef3-\U00011ef4\U00016af0-\U00016af4\U00016b30-\U00016b36\U00016f8f-\U00016f92\U0001bc9d-\U0001bc9e\U0001d167-\U0001d169\U0001d17b-\U0001d182\U0001d185-\U0001d18b\U0001d1aa-\U0001d1ad\U0001d242-\U0001d244\U0001da00-\U0001da36\U0001da3b-\U0001da6c\U0001da75\U0001da84\U0001da9b-\U0001da9f\U0001daa1-\U0001daaf\U0001e000-\U0001e006\U0001e008-\U0001e018\U0001e01b-\U0001e021\U0001e023-\U0001e024\U0001e026-\U0001e02a\U0001e8d0-\U0001e8d6\U0001e944-\U0001e94a\U000e0100-\U000e01ef'

Nd = '0-9\u0660-\u0669\u06f0-\u06f9\u07c0-\u07c9\u0966-\u096f\u09e6-\u09ef\u0a66-\u0a6f\u0ae6-\u0aef\u0b66-\u0b6f\u0be6-\u0bef\u0c66-\u0c6f\u0ce6-\u0cef\u0d66-\u0d6f\u0de6-\u0def\u0e50-\u0e59\u0ed0-\u0ed9\u0f20-\u0f29\u1040-\u1049\u1090-\u1099\u17e0-\u17e9\u1810-\u1819\u1946-\u194f\u19d0-\u19d9\u1a80-\u1a89\u1a90-\u1a99\u1b50-\u1b59\u1bb0-\u1bb9\u1c40-\u1c49\u1c50-\u1c59\ua620-\ua629\ua8d0-\ua8d9\ua900-\ua909\ua9d0-\ua9d9\ua9f0-\ua9f9\uaa50-\uaa59\uabf0-\uabf9\uff10-\uff19\U000104a0-\U000104a9\U00010d30-\U00010d39\U00011066-\U0001106f\U000110f0-\U000110f9\U00011136-\U0001113f\U000111d0-\U000111d9\U000112f0-\U000112f9\U00011450-\U00011459\U000114d0-\U000114d9\U00011650-\U00011659\U000116c0-\U000116c9\U00011730-\U00011739\U000118e0-\U000118e9\U00011c50-\U00011c59\U00011d50-\U00011d59\U00011da0-\U00011da9\U00016a60-\U00016a69\U00016b50-\U00016b59\U0001d7ce-\U0001d7ff\U0001e950-\U0001e959'

Nl = '\u16ee-\u16f0\u2160-\u2182\u2185-\u2188\u3007\u3021-\u3029\u3038-\u303a\ua6e6-\ua6ef\U00010140-\U00010174\U00010341\U0001034a\U000103d1-\U000103d5\U00012400-\U0001246e'

No = '\xb2-\xb3\xb9\xbc-\xbe\u09f4-\u09f9\u0b72-\u0b77\u0bf0-\u0bf2\u0c78-\u0c7e\u0d58-\u0d5e\u0d70-\u0d78\u0f2a-\u0f33\u1369-\u137c\u17f0-\u17f9\u19da\u2070\u2074-\u2079\u2080-\u2089\u2150-\u215f\u2189\u2460-\u249b\u24ea-\u24ff\u2776-\u2793\u2cfd\u3192-\u3195\u3220-\u3229\u3248-\u324f\u3251-\u325f\u3280-\u3289\u32b1-\u32bf\ua830-\ua835\U00010107-\U00010133\U00010175-\U00010178\U0001018a-\U0001018b\U000102e1-\U000102fb\U00010320-\U00010323\U00010858-\U0001085f\U00010879-\U0001087f\U000108a7-\U000108af\U000108fb-\U000108ff\U00010916-\U0001091b\U000109bc-\U000109bd\U000109c0-\U000109cf\U000109d2-\U000109ff\U00010a40-\U00010a48\U00010a7d-\U00010a7e\U00010a9d-\U00010a9f\U00010aeb-\U00010aef\U00010b58-\U00010b5f\U00010b78-\U00010b7f\U00010ba9-\U00010baf\U00010cfa-\U00010cff\U00010e60-\U00010e7e\U00010f1d-\U00010f26\U00010f51-\U00010f54\U00011052-\U00011065\U000111e1-\U000111f4\U0001173a-\U0001173b\U000118ea-\U000118f2\U00011c5a-\U00011c6c\U00016b5b-\U00016b61\U00016e80-\U00016e96\U0001d2e0-\U0001d2f3\U0001d360-\U0001d378\U0001e8c7-\U0001e8cf\U0001ec71-\U0001ecab\U0001ecad-\U0001ecaf\U0001ecb1-\U0001ecb4\U0001f100-\U0001f10c'

Pc = '_\u203f-\u2040\u2054\ufe33-\ufe34\ufe4d-\ufe4f\uff3f'

Pd = '\\-\u058a\u05be\u1400\u1806\u2010-\u2015\u2e17\u2e1a\u2e3a-\u2e3b\u2e40\u301c\u3030\u30a0\ufe31-\ufe32\ufe58\ufe63\uff0d'

Pe = ')\\]}\u0f3b\u0f3d\u169c\u2046\u207e\u208e\u2309\u230b\u232a\u2769\u276b\u276d\u276f\u2771\u2773\u2775\u27c6\u27e7\u27e9\u27eb\u27ed\u27ef\u2984\u2986\u2988\u298a\u298c\u298e\u2990\u2992\u2994\u2996\u2998\u29d9\u29db\u29fd\u2e23\u2e25\u2e27\u2e29\u3009\u300b\u300d\u300f\u3011\u3015\u3017\u3019\u301b\u301e-\u301f\ufd3e\ufe18\ufe36\ufe38\ufe3a\ufe3c\ufe3e\ufe40\ufe42\ufe44\ufe48\ufe5a\ufe5c\ufe5e\uff09\uff3d\uff5d\uff60\uff63'

Pf = '\xbb\u2019\u201d\u203a\u2e03\u2e05\u2e0a\u2e0d\u2e1d\u2e21'

Pi = '\xab\u2018\u201b-\u201c\u201f\u2039\u2e02\u2e04\u2e09\u2e0c\u2e1c\u2e20'

Po = "!-#%-'*,.-/:-;?-@\\\\\xa1\xa7\xb6-\xb7\xbf\u037e\u0387\u055a-\u055f\u0589\u05c0\u05c3\u05c6\u05f3-\u05f4\u0609-\u060a\u060c-\u060d\u061b\u061e-\u061f\u066a-\u066d\u06d4\u0700-\u070d\u07f7-\u07f9\u0830-\u083e\u085e\u0964-\u0965\u0970\u09fd\u0a76\u0af0\u0c84\u0df4\u0e4f\u0e5a-\u0e5b\u0f04-\u0f12\u0f14\u0f85\u0fd0-\u0fd4\u0fd9-\u0fda\u104a-\u104f\u10fb\u1360-\u1368\u166d-\u166e\u16eb-\u16ed\u1735-\u1736\u17d4-\u17d6\u17d8-\u17da\u1800-\u1805\u1807-\u180a\u1944-\u1945\u1a1e-\u1a1f\u1aa0-\u1aa6\u1aa8-\u1aad\u1b5a-\u1b60\u1bfc-\u1bff\u1c3b-\u1c3f\u1c7e-\u1c7f\u1cc0-\u1cc7\u1cd3\u2016-\u2017\u2020-\u2027\u2030-\u2038\u203b-\u203e\u2041-\u2043\u2047-\u2051\u2053\u2055-\u205e\u2cf9-\u2cfc\u2cfe-\u2cff\u2d70\u2e00-\u2e01\u2e06-\u2e08\u2e0b\u2e0e-\u2e16\u2e18-\u2e19\u2e1b\u2e1e-\u2e1f\u2e2a-\u2e2e\u2e30-\u2e39\u2e3c-\u2e3f\u2e41\u2e43-\u2e4e\u3001-\u3003\u303d\u30fb\ua4fe-\ua4ff\ua60d-\ua60f\ua673\ua67e\ua6f2-\ua6f7\ua874-\ua877\ua8ce-\ua8cf\ua8f8-\ua8fa\ua8fc\ua92e-\ua92f\ua95f\ua9c1-\ua9cd\ua9de-\ua9df\uaa5c-\uaa5f\uaade-\uaadf\uaaf0-\uaaf1\uabeb\ufe10-\ufe16\ufe19\ufe30\ufe45-\ufe46\ufe49-\ufe4c\ufe50-\ufe52\ufe54-\ufe57\ufe5f-\ufe61\ufe68\ufe6a-\ufe6b\uff01-\uff03\uff05-\uff07\uff0a\uff0c\uff0e-\uff0f\uff1a-\uff1b\uff1f-\uff20\uff3c\uff61\uff64-\uff65\U00010100-\U00010102\U0001039f\U000103d0\U0001056f\U00010857\U0001091f\U0001093f\U00010a50-\U00010a58\U00010a7f\U00010af0-\U00010af6\U00010b39-\U00010b3f\U00010b99-\U00010b9c\U00010f55-\U00010f59\U00011047-\U0001104d\U000110bb-\U000110bc\U000110be-\U000110c1\U00011140-\U00011143\U00011174-\U00011175\U000111c5-\U000111c8\U000111cd\U000111db\U000111dd-\U000111df\U00011238-\U0001123d\U000112a9\U0001144b-\U0001144f\U0001145b\U0001145d\U000114c6\U000115c1-\U000115d7\U00011641-\U00011643\U00011660-\U0001166c\U0001173c-\U0001173e\U0001183b\U00011a3f-\U00011a46\U00011a9a-\U00011a9c\U00011a9e-\U00011aa2\U00011c41-\U00011c45\U00011c70-\U00011c71\U00011ef7-\U00011ef8\U00012470-\U00012474\U00016a6e-\U00016a6f\U00016af5\U00016b37-\U00016b3b\U00016b44\U00016e97-\U00016e9a\U0001bc9f\U0001da87-\U0001da8b\U0001e95e-\U0001e95f"

Ps = '(\\[{\u0f3a\u0f3c\u169b\u201a\u201e\u2045\u207d\u208d\u2308\u230a\u2329\u2768\u276a\u276c\u276e\u2770\u2772\u2774\u27c5\u27e6\u27e8\u27ea\u27ec\u27ee\u2983\u2985\u2987\u2989\u298b\u298d\u298f\u2991\u2993\u2995\u2997\u29d8\u29da\u29fc\u2e22\u2e24\u2e26\u2e28\u2e42\u3008\u300a\u300c\u300e\u3010\u3014\u3016\u3018\u301a\u301d\ufd3f\ufe17\ufe35\ufe37\ufe39\ufe3b\ufe3d\ufe3f\ufe41\ufe43\ufe47\ufe59\ufe5b\ufe5d\uff08\uff3b\uff5b\uff5f\uff62'

Sc = '$\xa2-\xa5\u058f\u060b\u07fe-\u07ff\u09f2-\u09f3\u09fb\u0af1\u0bf9\u0e3f\u17db\u20a0-\u20bf\ua838\ufdfc\ufe69\uff04\uffe0-\uffe1\uffe5-\uffe6\U0001ecb0'

Sk = '\\^`\xa8\xaf\xb4\xb8\u02c2-\u02c5\u02d2-\u02df\u02e5-\u02eb\u02ed\u02ef-\u02ff\u0375\u0384-\u0385\u1fbd\u1fbf-\u1fc1\u1fcd-\u1fcf\u1fdd-\u1fdf\u1fed-\u1fef\u1ffd-\u1ffe\u309b-\u309c\ua700-\ua716\ua720-\ua721\ua789-\ua78a\uab5b\ufbb2-\ufbc1\uff3e\uff40\uffe3\U0001f3fb-\U0001f3ff'

Sm = '+<->|~\xac\xb1\xd7\xf7\u03f6\u0606-\u0608\u2044\u2052\u207a-\u207c\u208a-\u208c\u2118\u2140-\u2144\u214b\u2190-\u2194\u219a-\u219b\u21a0\u21a3\u21a6\u21ae\u21ce-\u21cf\u21d2\u21d4\u21f4-\u22ff\u2320-\u2321\u237c\u239b-\u23b3\u23dc-\u23e1\u25b7\u25c1\u25f8-\u25ff\u266f\u27c0-\u27c4\u27c7-\u27e5\u27f0-\u27ff\u2900-\u2982\u2999-\u29d7\u29dc-\u29fb\u29fe-\u2aff\u2b30-\u2b44\u2b47-\u2b4c\ufb29\ufe62\ufe64-\ufe66\uff0b\uff1c-\uff1e\uff5c\uff5e\uffe2\uffe9-\uffec\U0001d6c1\U0001d6db\U0001d6fb\U0001d715\U0001d735\U0001d74f\U0001d76f\U0001d789\U0001d7a9\U0001d7c3\U0001eef0-\U0001eef1'

So = '\xa6\xa9\xae\xb0\u0482\u058d-\u058e\u060e-\u060f\u06de\u06e9\u06fd-\u06fe\u07f6\u09fa\u0b70\u0bf3-\u0bf8\u0bfa\u0c7f\u0d4f\u0d79\u0f01-\u0f03\u0f13\u0f15-\u0f17\u0f1a-\u0f1f\u0f34\u0f36\u0f38\u0fbe-\u0fc5\u0fc7-\u0fcc\u0fce-\u0fcf\u0fd5-\u0fd8\u109e-\u109f\u1390-\u1399\u1940\u19de-\u19ff\u1b61-\u1b6a\u1b74-\u1b7c\u2100-\u2101\u2103-\u2106\u2108-\u2109\u2114\u2116-\u2117\u211e-\u2123\u2125\u2127\u2129\u212e\u213a-\u213b\u214a\u214c-\u214d\u214f\u218a-\u218b\u2195-\u2199\u219c-\u219f\u21a1-\u21a2\u21a4-\u21a5\u21a7-\u21ad\u21af-\u21cd\u21d0-\u21d1\u21d3\u21d5-\u21f3\u2300-\u2307\u230c-\u231f\u2322-\u2328\u232b-\u237b\u237d-\u239a\u23b4-\u23db\u23e2-\u2426\u2440-\u244a\u249c-\u24e9\u2500-\u25b6\u25b8-\u25c0\u25c2-\u25f7\u2600-\u266e\u2670-\u2767\u2794-\u27bf\u2800-\u28ff\u2b00-\u2b2f\u2b45-\u2b46\u2b4d-\u2b73\u2b76-\u2b95\u2b98-\u2bc8\u2bca-\u2bfe\u2ce5-\u2cea\u2e80-\u2e99\u2e9b-\u2ef3\u2f00-\u2fd5\u2ff0-\u2ffb\u3004\u3012-\u3013\u3020\u3036-\u3037\u303e-\u303f\u3190-\u3191\u3196-\u319f\u31c0-\u31e3\u3200-\u321e\u322a-\u3247\u3250\u3260-\u327f\u328a-\u32b0\u32c0-\u32fe\u3300-\u33ff\u4dc0-\u4dff\ua490-\ua4c6\ua828-\ua82b\ua836-\ua837\ua839\uaa77-\uaa79\ufdfd\uffe4\uffe8\uffed-\uffee\ufffc-\ufffd\U00010137-\U0001013f\U00010179-\U00010189\U0001018c-\U0001018e\U00010190-\U0001019b\U000101a0\U000101d0-\U000101fc\U00010877-\U00010878\U00010ac8\U0001173f\U00016b3c-\U00016b3f\U00016b45\U0001bc9c\U0001d000-\U0001d0f5\U0001d100-\U0001d126\U0001d129-\U0001d164\U0001d16a-\U0001d16c\U0001d183-\U0001d184\U0001d18c-\U0001d1a9\U0001d1ae-\U0001d1e8\U0001d200-\U0001d241\U0001d245\U0001d300-\U0001d356\U0001d800-\U0001d9ff\U0001da37-\U0001da3a\U0001da6d-\U0001da74\U0001da76-\U0001da83\U0001da85-\U0001da86\U0001ecac\U0001f000-\U0001f02b\U0001f030-\U0001f093\U0001f0a0-\U0001f0ae\U0001f0b1-\U0001f0bf\U0001f0c1-\U0001f0cf\U0001f0d1-\U0001f0f5\U0001f110-\U0001f16b\U0001f170-\U0001f1ac\U0001f1e6-\U0001f202\U0001f210-\U0001f23b\U0001f240-\U0001f248\U0001f250-\U0001f251\U0001f260-\U0001f265\U0001f300-\U0001f3fa\U0001f400-\U0001f6d4\U0001f6e0-\U0001f6ec\U0001f6f0-\U0001f6f9\U0001f700-\U0001f773\U0001f780-\U0001f7d8\U0001f800-\U0001f80b\U0001f810-\U0001f847\U0001f850-\U0001f859\U0001f860-\U0001f887\U0001f890-\U0001f8ad\U0001f900-\U0001f90b\U0001f910-\U0001f93e\U0001f940-\U0001f970\U0001f973-\U0001f976\U0001f97a\U0001f97c-\U0001f9a2\U0001f9b0-\U0001f9b9\U0001f9c0-\U0001f9c2\U0001f9d0-\U0001f9ff\U0001fa60-\U0001fa6d'

Zl = '\u2028'

Zp = '\u2029'

Zs = ' \xa0\u1680\u2000-\u200a\u202f\u205f\u3000'

xid_continue = '0-9A-Z_a-z\xaa\xb5\xb7\xba\xc0-\xd6\xd8-\xf6\xf8-\u02c1\u02c6-\u02d1\u02e0-\u02e4\u02ec\u02ee\u0300-\u0374\u0376-\u0377\u037b-\u037d\u037f\u0386-\u038a\u038c\u038e-\u03a1\u03a3-\u03f5\u03f7-\u0481\u0483-\u0487\u048a-\u052f\u0531-\u0556\u0559\u0560-\u0588\u0591-\u05bd\u05bf\u05c1-\u05c2\u05c4-\u05c5\u05c7\u05d0-\u05ea\u05ef-\u05f2\u0610-\u061a\u0620-\u0669\u066e-\u06d3\u06d5-\u06dc\u06df-\u06e8\u06ea-\u06fc\u06ff\u0710-\u074a\u074d-\u07b1\u07c0-\u07f5\u07fa\u07fd\u0800-\u082d\u0840-\u085b\u0860-\u086a\u08a0-\u08b4\u08b6-\u08bd\u08d3-\u08e1\u08e3-\u0963\u0966-\u096f\u0971-\u0983\u0985-\u098c\u098f-\u0990\u0993-\u09a8\u09aa-\u09b0\u09b2\u09b6-\u09b9\u09bc-\u09c4\u09c7-\u09c8\u09cb-\u09ce\u09d7\u09dc-\u09dd\u09df-\u09e3\u09e6-\u09f1\u09fc\u09fe\u0a01-\u0a03\u0a05-\u0a0a\u0a0f-\u0a10\u0a13-\u0a28\u0a2a-\u0a30\u0a32-\u0a33\u0a35-\u0a36\u0a38-\u0a39\u0a3c\u0a3e-\u0a42\u0a47-\u0a48\u0a4b-\u0a4d\u0a51\u0a59-\u0a5c\u0a5e\u0a66-\u0a75\u0a81-\u0a83\u0a85-\u0a8d\u0a8f-\u0a91\u0a93-\u0aa8\u0aaa-\u0ab0\u0ab2-\u0ab3\u0ab5-\u0ab9\u0abc-\u0ac5\u0ac7-\u0ac9\u0acb-\u0acd\u0ad0\u0ae0-\u0ae3\u0ae6-\u0aef\u0af9-\u0aff\u0b01-\u0b03\u0b05-\u0b0c\u0b0f-\u0b10\u0b13-\u0b28\u0b2a-\u0b30\u0b32-\u0b33\u0b35-\u0b39\u0b3c-\u0b44\u0b47-\u0b48\u0b4b-\u0b4d\u0b56-\u0b57\u0b5c-\u0b5d\u0b5f-\u0b63\u0b66-\u0b6f\u0b71\u0b82-\u0b83\u0b85-\u0b8a\u0b8e-\u0b90\u0b92-\u0b95\u0b99-\u0b9a\u0b9c\u0b9e-\u0b9f\u0ba3-\u0ba4\u0ba8-\u0baa\u0bae-\u0bb9\u0bbe-\u0bc2\u0bc6-\u0bc8\u0bca-\u0bcd\u0bd0\u0bd7\u0be6-\u0bef\u0c00-\u0c0c\u0c0e-\u0c10\u0c12-\u0c28\u0c2a-\u0c39\u0c3d-\u0c44\u0c46-\u0c48\u0c4a-\u0c4d\u0c55-\u0c56\u0c58-\u0c5a\u0c60-\u0c63\u0c66-\u0c6f\u0c80-\u0c83\u0c85-\u0c8c\u0c8e-\u0c90\u0c92-\u0ca8\u0caa-\u0cb3\u0cb5-\u0cb9\u0cbc-\u0cc4\u0cc6-\u0cc8\u0cca-\u0ccd\u0cd5-\u0cd6\u0cde\u0ce0-\u0ce3\u0ce6-\u0cef\u0cf1-\u0cf2\u0d00-\u0d03\u0d05-\u0d0c\u0d0e-\u0d10\u0d12-\u0d44\u0d46-\u0d48\u0d4a-\u0d4e\u0d54-\u0d57\u0d5f-\u0d63\u0d66-\u0d6f\u0d7a-\u0d7f\u0d82-\u0d83\u0d85-\u0d96\u0d9a-\u0db1\u0db3-\u0dbb\u0dbd\u0dc0-\u0dc6\u0dca\u0dcf-\u0dd4\u0dd6\u0dd8-\u0ddf\u0de6-\u0def\u0df2-\u0df3\u0e01-\u0e3a\u0e40-\u0e4e\u0e50-\u0e59\u0e81-\u0e82\u0e84\u0e87-\u0e88\u0e8a\u0e8d\u0e94-\u0e97\u0e99-\u0e9f\u0ea1-\u0ea3\u0ea5\u0ea7\u0eaa-\u0eab\u0ead-\u0eb9\u0ebb-\u0ebd\u0ec0-\u0ec4\u0ec6\u0ec8-\u0ecd\u0ed0-\u0ed9\u0edc-\u0edf\u0f00\u0f18-\u0f19\u0f20-\u0f29\u0f35\u0f37\u0f39\u0f3e-\u0f47\u0f49-\u0f6c\u0f71-\u0f84\u0f86-\u0f97\u0f99-\u0fbc\u0fc6\u1000-\u1049\u1050-\u109d\u10a0-\u10c5\u10c7\u10cd\u10d0-\u10fa\u10fc-\u1248\u124a-\u124d\u1250-\u1256\u1258\u125a-\u125d\u1260-\u1288\u128a-\u128d\u1290-\u12b0\u12b2-\u12b5\u12b8-\u12be\u12c0\u12c2-\u12c5\u12c8-\u12d6\u12d8-\u1310\u1312-\u1315\u1318-\u135a\u135d-\u135f\u1369-\u1371\u1380-\u138f\u13a0-\u13f5\u13f8-\u13fd\u1401-\u166c\u166f-\u167f\u1681-\u169a\u16a0-\u16ea\u16ee-\u16f8\u1700-\u170c\u170e-\u1714\u1720-\u1734\u1740-\u1753\u1760-\u176c\u176e-\u1770\u1772-\u1773\u1780-\u17d3\u17d7\u17dc-\u17dd\u17e0-\u17e9\u180b-\u180d\u1810-\u1819\u1820-\u1878\u1880-\u18aa\u18b0-\u18f5\u1900-\u191e\u1920-\u192b\u1930-\u193b\u1946-\u196d\u1970-\u1974\u1980-\u19ab\u19b0-\u19c9\u19d0-\u19da\u1a00-\u1a1b\u1a20-\u1a5e\u1a60-\u1a7c\u1a7f-\u1a89\u1a90-\u1a99\u1aa7\u1ab0-\u1abd\u1b00-\u1b4b\u1b50-\u1b59\u1b6b-\u1b73\u1b80-\u1bf3\u1c00-\u1c37\u1c40-\u1c49\u1c4d-\u1c7d\u1c80-\u1c88\u1c90-\u1cba\u1cbd-\u1cbf\u1cd0-\u1cd2\u1cd4-\u1cf9\u1d00-\u1df9\u1dfb-\u1f15\u1f18-\u1f1d\u1f20-\u1f45\u1f48-\u1f4d\u1f50-\u1f57\u1f59\u1f5b\u1f5d\u1f5f-\u1f7d\u1f80-\u1fb4\u1fb6-\u1fbc\u1fbe\u1fc2-\u1fc4\u1fc6-\u1fcc\u1fd0-\u1fd3\u1fd6-\u1fdb\u1fe0-\u1fec\u1ff2-\u1ff4\u1ff6-\u1ffc\u203f-\u2040\u2054\u2071\u207f\u2090-\u209c\u20d0-\u20dc\u20e1\u20e5-\u20f0\u2102\u2107\u210a-\u2113\u2115\u2118-\u211d\u2124\u2126\u2128\u212a-\u2139\u213c-\u213f\u2145-\u2149\u214e\u2160-\u2188\u2c00-\u2c2e\u2c30-\u2c5e\u2c60-\u2ce4\u2ceb-\u2cf3\u2d00-\u2d25\u2d27\u2d2d\u2d30-\u2d67\u2d6f\u2d7f-\u2d96\u2da0-\u2da6\u2da8-\u2dae\u2db0-\u2db6\u2db8-\u2dbe\u2dc0-\u2dc6\u2dc8-\u2dce\u2dd0-\u2dd6\u2dd8-\u2dde\u2de0-\u2dff\u3005-\u3007\u3021-\u302f\u3031-\u3035\u3038-\u303c\u3041-\u3096\u3099-\u309a\u309d-\u309f\u30a1-\u30fa\u30fc-\u30ff\u3105-\u312f\u3131-\u318e\u31a0-\u31ba\u31f0-\u31ff\u3400-\u4db5\u4e00-\u9fef\ua000-\ua48c\ua4d0-\ua4fd\ua500-\ua60c\ua610-\ua62b\ua640-\ua66f\ua674-\ua67d\ua67f-\ua6f1\ua717-\ua71f\ua722-\ua788\ua78b-\ua7b9\ua7f7-\ua827\ua840-\ua873\ua880-\ua8c5\ua8d0-\ua8d9\ua8e0-\ua8f7\ua8fb\ua8fd-\ua92d\ua930-\ua953\ua960-\ua97c\ua980-\ua9c0\ua9cf-\ua9d9\ua9e0-\ua9fe\uaa00-\uaa36\uaa40-\uaa4d\uaa50-\uaa59\uaa60-\uaa76\uaa7a-\uaac2\uaadb-\uaadd\uaae0-\uaaef\uaaf2-\uaaf6\uab01-\uab06\uab09-\uab0e\uab11-\uab16\uab20-\uab26\uab28-\uab2e\uab30-\uab5a\uab5c-\uab65\uab70-\uabea\uabec-\uabed\uabf0-\uabf9\uac00-\ud7a3\ud7b0-\ud7c6\ud7cb-\ud7fb\uf900-\ufa6d\ufa70-\ufad9\ufb00-\ufb06\ufb13-\ufb17\ufb1d-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufbb1\ufbd3-\ufc5d\ufc64-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdf9\ufe00-\ufe0f\ufe20-\ufe2f\ufe33-\ufe34\ufe4d-\ufe4f\ufe71\ufe73\ufe77\ufe79\ufe7b\ufe7d\ufe7f-\ufefc\uff10-\uff19\uff21-\uff3a\uff3f\uff41-\uff5a\uff66-\uffbe\uffc2-\uffc7\uffca-\uffcf\uffd2-\uffd7\uffda-\uffdc\U00010000-\U0001000b\U0001000d-\U00010026\U00010028-\U0001003a\U0001003c-\U0001003d\U0001003f-\U0001004d\U00010050-\U0001005d\U00010080-\U000100fa\U00010140-\U00010174\U000101fd\U00010280-\U0001029c\U000102a0-\U000102d0\U000102e0\U00010300-\U0001031f\U0001032d-\U0001034a\U00010350-\U0001037a\U00010380-\U0001039d\U000103a0-\U000103c3\U000103c8-\U000103cf\U000103d1-\U000103d5\U00010400-\U0001049d\U000104a0-\U000104a9\U000104b0-\U000104d3\U000104d8-\U000104fb\U00010500-\U00010527\U00010530-\U00010563\U00010600-\U00010736\U00010740-\U00010755\U00010760-\U00010767\U00010800-\U00010805\U00010808\U0001080a-\U00010835\U00010837-\U00010838\U0001083c\U0001083f-\U00010855\U00010860-\U00010876\U00010880-\U0001089e\U000108e0-\U000108f2\U000108f4-\U000108f5\U00010900-\U00010915\U00010920-\U00010939\U00010980-\U000109b7\U000109be-\U000109bf\U00010a00-\U00010a03\U00010a05-\U00010a06\U00010a0c-\U00010a13\U00010a15-\U00010a17\U00010a19-\U00010a35\U00010a38-\U00010a3a\U00010a3f\U00010a60-\U00010a7c\U00010a80-\U00010a9c\U00010ac0-\U00010ac7\U00010ac9-\U00010ae6\U00010b00-\U00010b35\U00010b40-\U00010b55\U00010b60-\U00010b72\U00010b80-\U00010b91\U00010c00-\U00010c48\U00010c80-\U00010cb2\U00010cc0-\U00010cf2\U00010d00-\U00010d27\U00010d30-\U00010d39\U00010f00-\U00010f1c\U00010f27\U00010f30-\U00010f50\U00011000-\U00011046\U00011066-\U0001106f\U0001107f-\U000110ba\U000110d0-\U000110e8\U000110f0-\U000110f9\U00011100-\U00011134\U00011136-\U0001113f\U00011144-\U00011146\U00011150-\U00011173\U00011176\U00011180-\U000111c4\U000111c9-\U000111cc\U000111d0-\U000111da\U000111dc\U00011200-\U00011211\U00011213-\U00011237\U0001123e\U00011280-\U00011286\U00011288\U0001128a-\U0001128d\U0001128f-\U0001129d\U0001129f-\U000112a8\U000112b0-\U000112ea\U000112f0-\U000112f9\U00011300-\U00011303\U00011305-\U0001130c\U0001130f-\U00011310\U00011313-\U00011328\U0001132a-\U00011330\U00011332-\U00011333\U00011335-\U00011339\U0001133b-\U00011344\U00011347-\U00011348\U0001134b-\U0001134d\U00011350\U00011357\U0001135d-\U00011363\U00011366-\U0001136c\U00011370-\U00011374\U00011400-\U0001144a\U00011450-\U00011459\U0001145e\U00011480-\U000114c5\U000114c7\U000114d0-\U000114d9\U00011580-\U000115b5\U000115b8-\U000115c0\U000115d8-\U000115dd\U00011600-\U00011640\U00011644\U00011650-\U00011659\U00011680-\U000116b7\U000116c0-\U000116c9\U00011700-\U0001171a\U0001171d-\U0001172b\U00011730-\U00011739\U00011800-\U0001183a\U000118a0-\U000118e9\U000118ff\U00011a00-\U00011a3e\U00011a47\U00011a50-\U00011a83\U00011a86-\U00011a99\U00011a9d\U00011ac0-\U00011af8\U00011c00-\U00011c08\U00011c0a-\U00011c36\U00011c38-\U00011c40\U00011c50-\U00011c59\U00011c72-\U00011c8f\U00011c92-\U00011ca7\U00011ca9-\U00011cb6\U00011d00-\U00011d06\U00011d08-\U00011d09\U00011d0b-\U00011d36\U00011d3a\U00011d3c-\U00011d3d\U00011d3f-\U00011d47\U00011d50-\U00011d59\U00011d60-\U00011d65\U00011d67-\U00011d68\U00011d6a-\U00011d8e\U00011d90-\U00011d91\U00011d93-\U00011d98\U00011da0-\U00011da9\U00011ee0-\U00011ef6\U00012000-\U00012399\U00012400-\U0001246e\U00012480-\U00012543\U00013000-\U0001342e\U00014400-\U00014646\U00016800-\U00016a38\U00016a40-\U00016a5e\U00016a60-\U00016a69\U00016ad0-\U00016aed\U00016af0-\U00016af4\U00016b00-\U00016b36\U00016b40-\U00016b43\U00016b50-\U00016b59\U00016b63-\U00016b77\U00016b7d-\U00016b8f\U00016e40-\U00016e7f\U00016f00-\U00016f44\U00016f50-\U00016f7e\U00016f8f-\U00016f9f\U00016fe0-\U00016fe1\U00017000-\U000187f1\U00018800-\U00018af2\U0001b000-\U0001b11e\U0001b170-\U0001b2fb\U0001bc00-\U0001bc6a\U0001bc70-\U0001bc7c\U0001bc80-\U0001bc88\U0001bc90-\U0001bc99\U0001bc9d-\U0001bc9e\U0001d165-\U0001d169\U0001d16d-\U0001d172\U0001d17b-\U0001d182\U0001d185-\U0001d18b\U0001d1aa-\U0001d1ad\U0001d242-\U0001d244\U0001d400-\U0001d454\U0001d456-\U0001d49c\U0001d49e-\U0001d49f\U0001d4a2\U0001d4a5-\U0001d4a6\U0001d4a9-\U0001d4ac\U0001d4ae-\U0001d4b9\U0001d4bb\U0001d4bd-\U0001d4c3\U0001d4c5-\U0001d505\U0001d507-\U0001d50a\U0001d50d-\U0001d514\U0001d516-\U0001d51c\U0001d51e-\U0001d539\U0001d53b-\U0001d53e\U0001d540-\U0001d544\U0001d546\U0001d54a-\U0001d550\U0001d552-\U0001d6a5\U0001d6a8-\U0001d6c0\U0001d6c2-\U0001d6da\U0001d6dc-\U0001d6fa\U0001d6fc-\U0001d714\U0001d716-\U0001d734\U0001d736-\U0001d74e\U0001d750-\U0001d76e\U0001d770-\U0001d788\U0001d78a-\U0001d7a8\U0001d7aa-\U0001d7c2\U0001d7c4-\U0001d7cb\U0001d7ce-\U0001d7ff\U0001da00-\U0001da36\U0001da3b-\U0001da6c\U0001da75\U0001da84\U0001da9b-\U0001da9f\U0001daa1-\U0001daaf\U0001e000-\U0001e006\U0001e008-\U0001e018\U0001e01b-\U0001e021\U0001e023-\U0001e024\U0001e026-\U0001e02a\U0001e800-\U0001e8c4\U0001e8d0-\U0001e8d6\U0001e900-\U0001e94a\U0001e950-\U0001e959\U0001ee00-\U0001ee03\U0001ee05-\U0001ee1f\U0001ee21-\U0001ee22\U0001ee24\U0001ee27\U0001ee29-\U0001ee32\U0001ee34-\U0001ee37\U0001ee39\U0001ee3b\U0001ee42\U0001ee47\U0001ee49\U0001ee4b\U0001ee4d-\U0001ee4f\U0001ee51-\U0001ee52\U0001ee54\U0001ee57\U0001ee59\U0001ee5b\U0001ee5d\U0001ee5f\U0001ee61-\U0001ee62\U0001ee64\U0001ee67-\U0001ee6a\U0001ee6c-\U0001ee72\U0001ee74-\U0001ee77\U0001ee79-\U0001ee7c\U0001ee7e\U0001ee80-\U0001ee89\U0001ee8b-\U0001ee9b\U0001eea1-\U0001eea3\U0001eea5-\U0001eea9\U0001eeab-\U0001eebb\U00020000-\U0002a6d6\U0002a700-\U0002b734\U0002b740-\U0002b81d\U0002b820-\U0002cea1\U0002ceb0-\U0002ebe0\U0002f800-\U0002fa1d\U000e0100-\U000e01ef'

xid_start = 'A-Z_a-z\xaa\xb5\xba\xc0-\xd6\xd8-\xf6\xf8-\u02c1\u02c6-\u02d1\u02e0-\u02e4\u02ec\u02ee\u0370-\u0374\u0376-\u0377\u037b-\u037d\u037f\u0386\u0388-\u038a\u038c\u038e-\u03a1\u03a3-\u03f5\u03f7-\u0481\u048a-\u052f\u0531-\u0556\u0559\u0560-\u0588\u05d0-\u05ea\u05ef-\u05f2\u0620-\u064a\u066e-\u066f\u0671-\u06d3\u06d5\u06e5-\u06e6\u06ee-\u06ef\u06fa-\u06fc\u06ff\u0710\u0712-\u072f\u074d-\u07a5\u07b1\u07ca-\u07ea\u07f4-\u07f5\u07fa\u0800-\u0815\u081a\u0824\u0828\u0840-\u0858\u0860-\u086a\u08a0-\u08b4\u08b6-\u08bd\u0904-\u0939\u093d\u0950\u0958-\u0961\u0971-\u0980\u0985-\u098c\u098f-\u0990\u0993-\u09a8\u09aa-\u09b0\u09b2\u09b6-\u09b9\u09bd\u09ce\u09dc-\u09dd\u09df-\u09e1\u09f0-\u09f1\u09fc\u0a05-\u0a0a\u0a0f-\u0a10\u0a13-\u0a28\u0a2a-\u0a30\u0a32-\u0a33\u0a35-\u0a36\u0a38-\u0a39\u0a59-\u0a5c\u0a5e\u0a72-\u0a74\u0a85-\u0a8d\u0a8f-\u0a91\u0a93-\u0aa8\u0aaa-\u0ab0\u0ab2-\u0ab3\u0ab5-\u0ab9\u0abd\u0ad0\u0ae0-\u0ae1\u0af9\u0b05-\u0b0c\u0b0f-\u0b10\u0b13-\u0b28\u0b2a-\u0b30\u0b32-\u0b33\u0b35-\u0b39\u0b3d\u0b5c-\u0b5d\u0b5f-\u0b61\u0b71\u0b83\u0b85-\u0b8a\u0b8e-\u0b90\u0b92-\u0b95\u0b99-\u0b9a\u0b9c\u0b9e-\u0b9f\u0ba3-\u0ba4\u0ba8-\u0baa\u0bae-\u0bb9\u0bd0\u0c05-\u0c0c\u0c0e-\u0c10\u0c12-\u0c28\u0c2a-\u0c39\u0c3d\u0c58-\u0c5a\u0c60-\u0c61\u0c80\u0c85-\u0c8c\u0c8e-\u0c90\u0c92-\u0ca8\u0caa-\u0cb3\u0cb5-\u0cb9\u0cbd\u0cde\u0ce0-\u0ce1\u0cf1-\u0cf2\u0d05-\u0d0c\u0d0e-\u0d10\u0d12-\u0d3a\u0d3d\u0d4e\u0d54-\u0d56\u0d5f-\u0d61\u0d7a-\u0d7f\u0d85-\u0d96\u0d9a-\u0db1\u0db3-\u0dbb\u0dbd\u0dc0-\u0dc6\u0e01-\u0e30\u0e32\u0e40-\u0e46\u0e81-\u0e82\u0e84\u0e87-\u0e88\u0e8a\u0e8d\u0e94-\u0e97\u0e99-\u0e9f\u0ea1-\u0ea3\u0ea5\u0ea7\u0eaa-\u0eab\u0ead-\u0eb0\u0eb2\u0ebd\u0ec0-\u0ec4\u0ec6\u0edc-\u0edf\u0f00\u0f40-\u0f47\u0f49-\u0f6c\u0f88-\u0f8c\u1000-\u102a\u103f\u1050-\u1055\u105a-\u105d\u1061\u1065-\u1066\u106e-\u1070\u1075-\u1081\u108e\u10a0-\u10c5\u10c7\u10cd\u10d0-\u10fa\u10fc-\u1248\u124a-\u124d\u1250-\u1256\u1258\u125a-\u125d\u1260-\u1288\u128a-\u128d\u1290-\u12b0\u12b2-\u12b5\u12b8-\u12be\u12c0\u12c2-\u12c5\u12c8-\u12d6\u12d8-\u1310\u1312-\u1315\u1318-\u135a\u1380-\u138f\u13a0-\u13f5\u13f8-\u13fd\u1401-\u166c\u166f-\u167f\u1681-\u169a\u16a0-\u16ea\u16ee-\u16f8\u1700-\u170c\u170e-\u1711\u1720-\u1731\u1740-\u1751\u1760-\u176c\u176e-\u1770\u1780-\u17b3\u17d7\u17dc\u1820-\u1878\u1880-\u18a8\u18aa\u18b0-\u18f5\u1900-\u191e\u1950-\u196d\u1970-\u1974\u1980-\u19ab\u19b0-\u19c9\u1a00-\u1a16\u1a20-\u1a54\u1aa7\u1b05-\u1b33\u1b45-\u1b4b\u1b83-\u1ba0\u1bae-\u1baf\u1bba-\u1be5\u1c00-\u1c23\u1c4d-\u1c4f\u1c5a-\u1c7d\u1c80-\u1c88\u1c90-\u1cba\u1cbd-\u1cbf\u1ce9-\u1cec\u1cee-\u1cf1\u1cf5-\u1cf6\u1d00-\u1dbf\u1e00-\u1f15\u1f18-\u1f1d\u1f20-\u1f45\u1f48-\u1f4d\u1f50-\u1f57\u1f59\u1f5b\u1f5d\u1f5f-\u1f7d\u1f80-\u1fb4\u1fb6-\u1fbc\u1fbe\u1fc2-\u1fc4\u1fc6-\u1fcc\u1fd0-\u1fd3\u1fd6-\u1fdb\u1fe0-\u1fec\u1ff2-\u1ff4\u1ff6-\u1ffc\u2071\u207f\u2090-\u209c\u2102\u2107\u210a-\u2113\u2115\u2118-\u211d\u2124\u2126\u2128\u212a-\u2139\u213c-\u213f\u2145-\u2149\u214e\u2160-\u2188\u2c00-\u2c2e\u2c30-\u2c5e\u2c60-\u2ce4\u2ceb-\u2cee\u2cf2-\u2cf3\u2d00-\u2d25\u2d27\u2d2d\u2d30-\u2d67\u2d6f\u2d80-\u2d96\u2da0-\u2da6\u2da8-\u2dae\u2db0-\u2db6\u2db8-\u2dbe\u2dc0-\u2dc6\u2dc8-\u2dce\u2dd0-\u2dd6\u2dd8-\u2dde\u3005-\u3007\u3021-\u3029\u3031-\u3035\u3038-\u303c\u3041-\u3096\u309d-\u309f\u30a1-\u30fa\u30fc-\u30ff\u3105-\u312f\u3131-\u318e\u31a0-\u31ba\u31f0-\u31ff\u3400-\u4db5\u4e00-\u9fef\ua000-\ua48c\ua4d0-\ua4fd\ua500-\ua60c\ua610-\ua61f\ua62a-\ua62b\ua640-\ua66e\ua67f-\ua69d\ua6a0-\ua6ef\ua717-\ua71f\ua722-\ua788\ua78b-\ua7b9\ua7f7-\ua801\ua803-\ua805\ua807-\ua80a\ua80c-\ua822\ua840-\ua873\ua882-\ua8b3\ua8f2-\ua8f7\ua8fb\ua8fd-\ua8fe\ua90a-\ua925\ua930-\ua946\ua960-\ua97c\ua984-\ua9b2\ua9cf\ua9e0-\ua9e4\ua9e6-\ua9ef\ua9fa-\ua9fe\uaa00-\uaa28\uaa40-\uaa42\uaa44-\uaa4b\uaa60-\uaa76\uaa7a\uaa7e-\uaaaf\uaab1\uaab5-\uaab6\uaab9-\uaabd\uaac0\uaac2\uaadb-\uaadd\uaae0-\uaaea\uaaf2-\uaaf4\uab01-\uab06\uab09-\uab0e\uab11-\uab16\uab20-\uab26\uab28-\uab2e\uab30-\uab5a\uab5c-\uab65\uab70-\uabe2\uac00-\ud7a3\ud7b0-\ud7c6\ud7cb-\ud7fb\uf900-\ufa6d\ufa70-\ufad9\ufb00-\ufb06\ufb13-\ufb17\ufb1d\ufb1f-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufbb1\ufbd3-\ufc5d\ufc64-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdf9\ufe71\ufe73\ufe77\ufe79\ufe7b\ufe7d\ufe7f-\ufefc\uff21-\uff3a\uff41-\uff5a\uff66-\uff9d\uffa0-\uffbe\uffc2-\uffc7\uffca-\uffcf\uffd2-\uffd7\uffda-\uffdc\U00010000-\U0001000b\U0001000d-\U00010026\U00010028-\U0001003a\U0001003c-\U0001003d\U0001003f-\U0001004d\U00010050-\U0001005d\U00010080-\U000100fa\U00010140-\U00010174\U00010280-\U0001029c\U000102a0-\U000102d0\U00010300-\U0001031f\U0001032d-\U0001034a\U00010350-\U00010375\U00010380-\U0001039d\U000103a0-\U000103c3\U000103c8-\U000103cf\U000103d1-\U000103d5\U00010400-\U0001049d\U000104b0-\U000104d3\U000104d8-\U000104fb\U00010500-\U00010527\U00010530-\U00010563\U00010600-\U00010736\U00010740-\U00010755\U00010760-\U00010767\U00010800-\U00010805\U00010808\U0001080a-\U00010835\U00010837-\U00010838\U0001083c\U0001083f-\U00010855\U00010860-\U00010876\U00010880-\U0001089e\U000108e0-\U000108f2\U000108f4-\U000108f5\U00010900-\U00010915\U00010920-\U00010939\U00010980-\U000109b7\U000109be-\U000109bf\U00010a00\U00010a10-\U00010a13\U00010a15-\U00010a17\U00010a19-\U00010a35\U00010a60-\U00010a7c\U00010a80-\U00010a9c\U00010ac0-\U00010ac7\U00010ac9-\U00010ae4\U00010b00-\U00010b35\U00010b40-\U00010b55\U00010b60-\U00010b72\U00010b80-\U00010b91\U00010c00-\U00010c48\U00010c80-\U00010cb2\U00010cc0-\U00010cf2\U00010d00-\U00010d23\U00010f00-\U00010f1c\U00010f27\U00010f30-\U00010f45\U00011003-\U00011037\U00011083-\U000110af\U000110d0-\U000110e8\U00011103-\U00011126\U00011144\U00011150-\U00011172\U00011176\U00011183-\U000111b2\U000111c1-\U000111c4\U000111da\U000111dc\U00011200-\U00011211\U00011213-\U0001122b\U00011280-\U00011286\U00011288\U0001128a-\U0001128d\U0001128f-\U0001129d\U0001129f-\U000112a8\U000112b0-\U000112de\U00011305-\U0001130c\U0001130f-\U00011310\U00011313-\U00011328\U0001132a-\U00011330\U00011332-\U00011333\U00011335-\U00011339\U0001133d\U00011350\U0001135d-\U00011361\U00011400-\U00011434\U00011447-\U0001144a\U00011480-\U000114af\U000114c4-\U000114c5\U000114c7\U00011580-\U000115ae\U000115d8-\U000115db\U00011600-\U0001162f\U00011644\U00011680-\U000116aa\U00011700-\U0001171a\U00011800-\U0001182b\U000118a0-\U000118df\U000118ff\U00011a00\U00011a0b-\U00011a32\U00011a3a\U00011a50\U00011a5c-\U00011a83\U00011a86-\U00011a89\U00011a9d\U00011ac0-\U00011af8\U00011c00-\U00011c08\U00011c0a-\U00011c2e\U00011c40\U00011c72-\U00011c8f\U00011d00-\U00011d06\U00011d08-\U00011d09\U00011d0b-\U00011d30\U00011d46\U00011d60-\U00011d65\U00011d67-\U00011d68\U00011d6a-\U00011d89\U00011d98\U00011ee0-\U00011ef2\U00012000-\U00012399\U00012400-\U0001246e\U00012480-\U00012543\U00013000-\U0001342e\U00014400-\U00014646\U00016800-\U00016a38\U00016a40-\U00016a5e\U00016ad0-\U00016aed\U00016b00-\U00016b2f\U00016b40-\U00016b43\U00016b63-\U00016b77\U00016b7d-\U00016b8f\U00016e40-\U00016e7f\U00016f00-\U00016f44\U00016f50\U00016f93-\U00016f9f\U00016fe0-\U00016fe1\U00017000-\U000187f1\U00018800-\U00018af2\U0001b000-\U0001b11e\U0001b170-\U0001b2fb\U0001bc00-\U0001bc6a\U0001bc70-\U0001bc7c\U0001bc80-\U0001bc88\U0001bc90-\U0001bc99\U0001d400-\U0001d454\U0001d456-\U0001d49c\U0001d49e-\U0001d49f\U0001d4a2\U0001d4a5-\U0001d4a6\U0001d4a9-\U0001d4ac\U0001d4ae-\U0001d4b9\U0001d4bb\U0001d4bd-\U0001d4c3\U0001d4c5-\U0001d505\U0001d507-\U0001d50a\U0001d50d-\U0001d514\U0001d516-\U0001d51c\U0001d51e-\U0001d539\U0001d53b-\U0001d53e\U0001d540-\U0001d544\U0001d546\U0001d54a-\U0001d550\U0001d552-\U0001d6a5\U0001d6a8-\U0001d6c0\U0001d6c2-\U0001d6da\U0001d6dc-\U0001d6fa\U0001d6fc-\U0001d714\U0001d716-\U0001d734\U0001d736-\U0001d74e\U0001d750-\U0001d76e\U0001d770-\U0001d788\U0001d78a-\U0001d7a8\U0001d7aa-\U0001d7c2\U0001d7c4-\U0001d7cb\U0001e800-\U0001e8c4\U0001e900-\U0001e943\U0001ee00-\U0001ee03\U0001ee05-\U0001ee1f\U0001ee21-\U0001ee22\U0001ee24\U0001ee27\U0001ee29-\U0001ee32\U0001ee34-\U0001ee37\U0001ee39\U0001ee3b\U0001ee42\U0001ee47\U0001ee49\U0001ee4b\U0001ee4d-\U0001ee4f\U0001ee51-\U0001ee52\U0001ee54\U0001ee57\U0001ee59\U0001ee5b\U0001ee5d\U0001ee5f\U0001ee61-\U0001ee62\U0001ee64\U0001ee67-\U0001ee6a\U0001ee6c-\U0001ee72\U0001ee74-\U0001ee77\U0001ee79-\U0001ee7c\U0001ee7e\U0001ee80-\U0001ee89\U0001ee8b-\U0001ee9b\U0001eea1-\U0001eea3\U0001eea5-\U0001eea9\U0001eeab-\U0001eebb\U00020000-\U0002a6d6\U0002a700-\U0002b734\U0002b740-\U0002b81d\U0002b820-\U0002cea1\U0002ceb0-\U0002ebe0\U0002f800-\U0002fa1d'

cats = ['Cc', 'Cf', 'Cn', 'Co', 'Cs', 'Ll', 'Lm', 'Lo', 'Lt', 'Lu', 'Mc', 'Me', 'Mn', 'Nd', 'Nl', 'No', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zl', 'Zp', 'Zs']

# Generated from unidata 11.0.0

def combine(*args):
    return ''.join(globals()[cat] for cat in args)


def allexcept(*args):
    newcats = cats[:]
    for arg in args:
        newcats.remove(arg)
    return ''.join(globals()[cat] for cat in newcats)


def _handle_runs(char_list):  # pragma: no cover
    buf = []
    for c in char_list:
        if len(c) == 1:
            if buf and buf[-1][1] == chr(ord(c)-1):
                buf[-1] = (buf[-1][0], c)
            else:
                buf.append((c, c))
        else:
            buf.append((c, c))
    for a, b in buf:
        if a == b:
            yield a
        else:
            yield f'{a}-{b}'


if __name__ == '__main__':  # pragma: no cover
    import unicodedata

    categories = {'xid_start': [], 'xid_continue': []}

    with open(__file__, encoding='utf-8') as fp:
        content = fp.read()

    header = content[:content.find('Cc =')]
    footer = content[content.find("def combine("):]

    for code in range(0x110000):
        c = chr(code)
        cat = unicodedata.category(c)
        if ord(c) == 0xdc00:
            # Hack to avoid combining this combining with the preceding high
            # surrogate, 0xdbff, when doing a repr.
            c = '\\' + c
        elif ord(c) in (0x2d, 0x5b, 0x5c, 0x5d, 0x5e):
            # Escape regex metachars.
            c = '\\' + c
        categories.setdefault(cat, []).append(c)
        # XID_START and XID_CONTINUE are special categories used for matching
        # identifiers in Python 3.
        if c.isidentifier():
            categories['xid_start'].append(c)
        if ('a' + c).isidentifier():
            categories['xid_continue'].append(c)

    with open(__file__, 'w', encoding='utf-8') as fp:
        fp.write(header)

        for cat in sorted(categories):
            val = ''.join(_handle_runs(categories[cat]))
            fp.write(f'{cat} = {val!a}\n\n')

        cats = sorted(categories)
        cats.remove('xid_start')
        cats.remove('xid_continue')
        fp.write(f'cats = {cats!r}\n\n')

        fp.write(f'# Generated from unidata {unicodedata.unidata_version}\n\n')

        fp.write(footer)

# === NexusCore/openenv\Lib\site-packages\rich\terminal_theme.py ===
from typing import List, Optional, Tuple

from .color_triplet import ColorTriplet
from .palette import Palette

_ColorTuple = Tuple[int, int, int]


class TerminalTheme:
    """A color theme used when exporting console content.

    Args:
        background (Tuple[int, int, int]): The background color.
        foreground (Tuple[int, int, int]): The foreground (text) color.
        normal (List[Tuple[int, int, int]]): A list of 8 normal intensity colors.
        bright (List[Tuple[int, int, int]], optional): A list of 8 bright colors, or None
            to repeat normal intensity. Defaults to None.
    """

    def __init__(
        self,
        background: _ColorTuple,
        foreground: _ColorTuple,
        normal: List[_ColorTuple],
        bright: Optional[List[_ColorTuple]] = None,
    ) -> None:
        self.background_color = ColorTriplet(*background)
        self.foreground_color = ColorTriplet(*foreground)
        self.ansi_colors = Palette(normal + (bright or normal))


DEFAULT_TERMINAL_THEME = TerminalTheme(
    (255, 255, 255),
    (0, 0, 0),
    [
        (0, 0, 0),
        (128, 0, 0),
        (0, 128, 0),
        (128, 128, 0),
        (0, 0, 128),
        (128, 0, 128),
        (0, 128, 128),
        (192, 192, 192),
    ],
    [
        (128, 128, 128),
        (255, 0, 0),
        (0, 255, 0),
        (255, 255, 0),
        (0, 0, 255),
        (255, 0, 255),
        (0, 255, 255),
        (255, 255, 255),
    ],
)

MONOKAI = TerminalTheme(
    (12, 12, 12),
    (217, 217, 217),
    [
        (26, 26, 26),
        (244, 0, 95),
        (152, 224, 36),
        (253, 151, 31),
        (157, 101, 255),
        (244, 0, 95),
        (88, 209, 235),
        (196, 197, 181),
        (98, 94, 76),
    ],
    [
        (244, 0, 95),
        (152, 224, 36),
        (224, 213, 97),
        (157, 101, 255),
        (244, 0, 95),
        (88, 209, 235),
        (246, 246, 239),
    ],
)
DIMMED_MONOKAI = TerminalTheme(
    (25, 25, 25),
    (185, 188, 186),
    [
        (58, 61, 67),
        (190, 63, 72),
        (135, 154, 59),
        (197, 166, 53),
        (79, 118, 161),
        (133, 92, 141),
        (87, 143, 164),
        (185, 188, 186),
        (136, 137, 135),
    ],
    [
        (251, 0, 31),
        (15, 114, 47),
        (196, 112, 51),
        (24, 109, 227),
        (251, 0, 103),
        (46, 112, 109),
        (253, 255, 185),
    ],
)
NIGHT_OWLISH = TerminalTheme(
    (255, 255, 255),
    (64, 63, 83),
    [
        (1, 22, 39),
        (211, 66, 62),
        (42, 162, 152),
        (218, 170, 1),
        (72, 118, 214),
        (64, 63, 83),
        (8, 145, 106),
        (122, 129, 129),
        (122, 129, 129),
    ],
    [
        (247, 110, 110),
        (73, 208, 197),
        (218, 194, 107),
        (92, 167, 228),
        (105, 112, 152),
        (0, 201, 144),
        (152, 159, 177),
    ],
)

SVG_EXPORT_THEME = TerminalTheme(
    (41, 41, 41),
    (197, 200, 198),
    [
        (75, 78, 85),
        (204, 85, 90),
        (152, 168, 75),
        (208, 179, 68),
        (96, 138, 177),
        (152, 114, 159),
        (104, 160, 179),
        (197, 200, 198),
        (154, 155, 153),
    ],
    [
        (255, 38, 39),
        (0, 130, 61),
        (208, 132, 66),
        (25, 132, 233),
        (255, 44, 122),
        (57, 130, 128),
        (253, 253, 197),
    ],
)

# === NexusCore/openenv\Lib\site-packages\starlette\config.py ===
from __future__ import annotations

import os
import typing
import warnings
from pathlib import Path


class undefined:
    pass


class EnvironError(Exception):
    pass


class Environ(typing.MutableMapping[str, str]):
    def __init__(self, environ: typing.MutableMapping[str, str] = os.environ):
        self._environ = environ
        self._has_been_read: set[str] = set()

    def __getitem__(self, key: str) -> str:
        self._has_been_read.add(key)
        return self._environ.__getitem__(key)

    def __setitem__(self, key: str, value: str) -> None:
        if key in self._has_been_read:
            raise EnvironError(
                f"Attempting to set environ['{key}'], but the value has already been "
                "read."
            )
        self._environ.__setitem__(key, value)

    def __delitem__(self, key: str) -> None:
        if key in self._has_been_read:
            raise EnvironError(
                f"Attempting to delete environ['{key}'], but the value has already "
                "been read."
            )
        self._environ.__delitem__(key)

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._environ)

    def __len__(self) -> int:
        return len(self._environ)


environ = Environ()

T = typing.TypeVar("T")


class Config:
    def __init__(
        self,
        env_file: str | Path | None = None,
        environ: typing.Mapping[str, str] = environ,
        env_prefix: str = "",
    ) -> None:
        self.environ = environ
        self.env_prefix = env_prefix
        self.file_values: dict[str, str] = {}
        if env_file is not None:
            if not os.path.isfile(env_file):
                warnings.warn(f"Config file '{env_file}' not found.")
            else:
                self.file_values = self._read_file(env_file)

    @typing.overload
    def __call__(self, key: str, *, default: None) -> str | None:
        ...

    @typing.overload
    def __call__(self, key: str, cast: type[T], default: T = ...) -> T:
        ...

    @typing.overload
    def __call__(self, key: str, cast: type[str] = ..., default: str = ...) -> str:
        ...

    @typing.overload
    def __call__(
        self,
        key: str,
        cast: typing.Callable[[typing.Any], T] = ...,
        default: typing.Any = ...,
    ) -> T:
        ...

    @typing.overload
    def __call__(self, key: str, cast: type[str] = ..., default: T = ...) -> T | str:
        ...

    def __call__(
        self,
        key: str,
        cast: typing.Callable[[typing.Any], typing.Any] | None = None,
        default: typing.Any = undefined,
    ) -> typing.Any:
        return self.get(key, cast, default)

    def get(
        self,
        key: str,
        cast: typing.Callable[[typing.Any], typing.Any] | None = None,
        default: typing.Any = undefined,
    ) -> typing.Any:
        key = self.env_prefix + key
        if key in self.environ:
            value = self.environ[key]
            return self._perform_cast(key, value, cast)
        if key in self.file_values:
            value = self.file_values[key]
            return self._perform_cast(key, value, cast)
        if default is not undefined:
            return self._perform_cast(key, default, cast)
        raise KeyError(f"Config '{key}' is missing, and has no default.")

    def _read_file(self, file_name: str | Path) -> dict[str, str]:
        file_values: dict[str, str] = {}
        with open(file_name) as input_file:
            for line in input_file.readlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    file_values[key] = value
        return file_values

    def _perform_cast(
        self,
        key: str,
        value: typing.Any,
        cast: typing.Callable[[typing.Any], typing.Any] | None = None,
    ) -> typing.Any:
        if cast is None or value is None:
            return value
        elif cast is bool and isinstance(value, str):
            mapping = {"true": True, "1": True, "false": False, "0": False}
            value = value.lower()
            if value not in mapping:
                raise ValueError(
                    f"Config '{key}' has value '{value}'. Not a valid bool."
                )
            return mapping[value]
        try:
            return cast(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"Config '{key}' has value '{value}'. Not a valid {cast.__name__}."
            )

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\_pydev_calltip_util.py ===
"""
License: Apache 2.0
Author: Yuli Fitterman
"""
import types

from _pydevd_bundle.pydevd_constants import IS_JYTHON

try:
    import inspect
except:
    import traceback

    traceback.print_exc()  # Ok, no inspect available (search will not work)

from _pydev_bundle._pydev_imports_tipper import signature_from_docstring


def is_bound_method(obj):
    if isinstance(obj, types.MethodType):
        return getattr(obj, "__self__", getattr(obj, "im_self", None)) is not None
    else:
        return False


def get_class_name(instance):
    return getattr(getattr(instance, "__class__", None), "__name__", None)


def get_bound_class_name(obj):
    my_self = getattr(obj, "__self__", getattr(obj, "im_self", None))
    if my_self is None:
        return None
    return get_class_name(my_self)


def get_description(obj):
    try:
        ob_call = obj.__call__
    except:
        ob_call = None

    if isinstance(obj, type) or type(obj).__name__ == "classobj":
        fob = getattr(obj, "__init__", lambda: None)
        if not isinstance(fob, (types.FunctionType, types.MethodType)):
            fob = obj
    elif is_bound_method(ob_call):
        fob = ob_call
    else:
        fob = obj

    argspec = ""
    fn_name = None
    fn_class = None
    if isinstance(fob, (types.FunctionType, types.MethodType)):
        spec_info = inspect.getfullargspec(fob)
        argspec = inspect.formatargspec(*spec_info)
        fn_name = getattr(fob, "__name__", None)
        if isinstance(obj, type) or type(obj).__name__ == "classobj":
            fn_name = "__init__"
            fn_class = getattr(obj, "__name__", "UnknownClass")
        elif is_bound_method(obj) or is_bound_method(ob_call):
            fn_class = get_bound_class_name(obj) or "UnknownClass"

    else:
        fn_name = getattr(fob, "__name__", None)
        fn_self = getattr(fob, "__self__", None)
        if fn_self is not None and not isinstance(fn_self, types.ModuleType):
            fn_class = get_class_name(fn_self)

    doc_string = get_docstring(ob_call) if is_bound_method(ob_call) else get_docstring(obj)
    return create_method_stub(fn_name, fn_class, argspec, doc_string)


def create_method_stub(fn_name, fn_class, argspec, doc_string):
    if fn_name and argspec:
        doc_string = "" if doc_string is None else doc_string
        fn_stub = create_function_stub(fn_name, argspec, doc_string, indent=1 if fn_class else 0)
        if fn_class:
            expr = fn_class if fn_name == "__init__" else fn_class + "()." + fn_name
            return create_class_stub(fn_class, fn_stub) + "\n" + expr
        else:
            expr = fn_name
            return fn_stub + "\n" + expr
    elif doc_string:
        if fn_name:
            restored_signature, _ = signature_from_docstring(doc_string, fn_name)
            if restored_signature:
                return create_method_stub(fn_name, fn_class, restored_signature, doc_string)
        return create_function_stub("unknown", "(*args, **kwargs)", doc_string) + "\nunknown"

    else:
        return ""


def get_docstring(obj):
    if obj is not None:
        try:
            if IS_JYTHON:
                # Jython
                doc = obj.__doc__
                if doc is not None:
                    return doc

                from _pydev_bundle import _pydev_jy_imports_tipper

                is_method, infos = _pydev_jy_imports_tipper.ismethod(obj)
                ret = ""
                if is_method:
                    for info in infos:
                        ret += info.get_as_doc()
                    return ret

            else:
                doc = inspect.getdoc(obj)
                if doc is not None:
                    return doc
        except:
            pass
    else:
        return ""
    try:
        # if no attempt succeeded, try to return repr()...
        return repr(obj)
    except:
        try:
            # otherwise the class
            return str(obj.__class__)
        except:
            # if all fails, go to an empty string
            return ""


def create_class_stub(class_name, contents):
    return "class %s(object):\n%s" % (class_name, contents)


def create_function_stub(fn_name, fn_argspec, fn_docstring, indent=0):
    def shift_right(string, prefix):
        return "".join(prefix + line for line in string.splitlines(True))

    fn_docstring = shift_right(inspect.cleandoc(fn_docstring), "  " * (indent + 1))
    ret = '''
def %s%s:
    """%s"""
    pass
''' % (fn_name, fn_argspec, fn_docstring)
    ret = ret[1:]  # remove first /n
    ret = ret.replace("\t", "  ")
    if indent:
        prefix = "  " * indent
        ret = shift_right(ret, prefix)
    return ret

# === NexusCore/openenv\Lib\site-packages\google\api_core\client_options.py ===
# Copyright 2019 Google LLC
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

"""Client options class.

Client options provide a consistent interface for user options to be defined
across clients.

You can pass a client options object to a client.

.. code-block:: python

    from google.api_core.client_options import ClientOptions
    from google.cloud.vision_v1 import ImageAnnotatorClient

    def get_client_cert():
        # code to load client certificate and private key.
        return client_cert_bytes, client_private_key_bytes

    options = ClientOptions(api_endpoint="foo.googleapis.com",
        client_cert_source=get_client_cert)

    client = ImageAnnotatorClient(client_options=options)

You can also pass a mapping object.

.. code-block:: python

    from google.cloud.vision_v1 import ImageAnnotatorClient

    client = ImageAnnotatorClient(
        client_options={
            "api_endpoint": "foo.googleapis.com",
            "client_cert_source" : get_client_cert
        })


"""

from typing import Callable, Mapping, Optional, Sequence, Tuple


class ClientOptions(object):
    """Client Options used to set options on clients.

    Args:
        api_endpoint (Optional[str]): The desired API endpoint, e.g.,
            compute.googleapis.com
        client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]): A callback
            which returns client certificate bytes and private key bytes both in
            PEM format. ``client_cert_source`` and ``client_encrypted_cert_source``
            are mutually exclusive.
        client_encrypted_cert_source (Optional[Callable[[], Tuple[str, str, bytes]]]):
            A callback which returns client certificate file path, encrypted
            private key file path, and the passphrase bytes.``client_cert_source``
            and ``client_encrypted_cert_source`` are mutually exclusive.
        quota_project_id (Optional[str]): A project name that a client's
            quota belongs to.
        credentials_file (Optional[str]): A path to a file storing credentials.
            ``credentials_file` and ``api_key`` are mutually exclusive.

            .. warning::
                Important: If you accept a credential configuration (credential JSON/File/Stream)
                from an external source for authentication to Google Cloud Platform, you must
                validate it before providing it to any Google API or client library. Providing an
                unvalidated credential configuration to Google APIs or libraries can compromise
                the security of your systems and data. For more information, refer to
                `Validate credential configurations from external sources`_.

            .. _Validate credential configurations from external sources:

            https://cloud.google.com/docs/authentication/external/externally-sourced-credentials
        scopes (Optional[Sequence[str]]): OAuth access token override scopes.
        api_key (Optional[str]): Google API key. ``credentials_file`` and
            ``api_key`` are mutually exclusive.
        api_audience (Optional[str]): The intended audience for the API calls
            to the service that will be set when using certain 3rd party
            authentication flows. Audience is typically a resource identifier.
            If not set, the service endpoint value will be used as a default.
            An example of a valid ``api_audience`` is: "https://language.googleapis.com".
        universe_domain (Optional[str]): The desired universe domain. This must match
            the one in credentials. If not set, the default universe domain is
            `googleapis.com`. If both `api_endpoint` and `universe_domain` are set,
            then `api_endpoint` is used as the service endpoint. If `api_endpoint` is
            not specified, the format will be `{service}.{universe_domain}`.

    Raises:
        ValueError: If both ``client_cert_source`` and ``client_encrypted_cert_source``
            are provided, or both ``credentials_file`` and ``api_key`` are provided.
    """

    def __init__(
        self,
        api_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        client_encrypted_cert_source: Optional[
            Callable[[], Tuple[str, str, bytes]]
        ] = None,
        quota_project_id: Optional[str] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        api_key: Optional[str] = None,
        api_audience: Optional[str] = None,
        universe_domain: Optional[str] = None,
    ):
        if client_cert_source and client_encrypted_cert_source:
            raise ValueError(
                "client_cert_source and client_encrypted_cert_source are mutually exclusive"
            )
        if api_key and credentials_file:
            raise ValueError("api_key and credentials_file are mutually exclusive")
        self.api_endpoint = api_endpoint
        self.client_cert_source = client_cert_source
        self.client_encrypted_cert_source = client_encrypted_cert_source
        self.quota_project_id = quota_project_id
        self.credentials_file = credentials_file
        self.scopes = scopes
        self.api_key = api_key
        self.api_audience = api_audience
        self.universe_domain = universe_domain

    def __repr__(self) -> str:
        return "ClientOptions: " + repr(self.__dict__)


def from_dict(options: Mapping[str, object]) -> ClientOptions:
    """Construct a client options object from a mapping object.

    Args:
        options (collections.abc.Mapping): A mapping object with client options.
            See the docstring for ClientOptions for details on valid arguments.
    """

    client_options = ClientOptions()

    for key, value in options.items():
        if hasattr(client_options, key):
            setattr(client_options, key, value)
        else:
            raise ValueError("ClientOptions does not accept an option '" + key + "'")

    return client_options

# === NexusCore/openenv\Lib\site-packages\google\auth\_cloud_sdk.py ===
# Copyright 2015 Google Inc.
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

"""Helpers for reading the Google Cloud SDK's configuration."""

import os
import subprocess

from google.auth import _helpers
from google.auth import environment_vars
from google.auth import exceptions


# The ~/.config subdirectory containing gcloud credentials.
_CONFIG_DIRECTORY = "gcloud"
# Windows systems store config at %APPDATA%\gcloud
_WINDOWS_CONFIG_ROOT_ENV_VAR = "APPDATA"
# The name of the file in the Cloud SDK config that contains default
# credentials.
_CREDENTIALS_FILENAME = "application_default_credentials.json"
# The name of the Cloud SDK shell script
_CLOUD_SDK_POSIX_COMMAND = "gcloud"
_CLOUD_SDK_WINDOWS_COMMAND = "gcloud.cmd"
# The command to get the Cloud SDK configuration
_CLOUD_SDK_CONFIG_GET_PROJECT_COMMAND = ("config", "get", "project")
# The command to get google user access token
_CLOUD_SDK_USER_ACCESS_TOKEN_COMMAND = ("auth", "print-access-token")
# Cloud SDK's application-default client ID
CLOUD_SDK_CLIENT_ID = (
    "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
)


def get_config_path():
    """Returns the absolute path the the Cloud SDK's configuration directory.

    Returns:
        str: The Cloud SDK config path.
    """
    # If the path is explicitly set, return that.
    try:
        return os.environ[environment_vars.CLOUD_SDK_CONFIG_DIR]
    except KeyError:
        pass

    # Non-windows systems store this at ~/.config/gcloud
    if os.name != "nt":
        return os.path.join(os.path.expanduser("~"), ".config", _CONFIG_DIRECTORY)
    # Windows systems store config at %APPDATA%\gcloud
    else:
        try:
            return os.path.join(
                os.environ[_WINDOWS_CONFIG_ROOT_ENV_VAR], _CONFIG_DIRECTORY
            )
        except KeyError:
            # This should never happen unless someone is really
            # messing with things, but we'll cover the case anyway.
            drive = os.environ.get("SystemDrive", "C:")
            return os.path.join(drive, "\\", _CONFIG_DIRECTORY)


def get_application_default_credentials_path():
    """Gets the path to the application default credentials file.

    The path may or may not exist.

    Returns:
        str: The full path to application default credentials.
    """
    config_path = get_config_path()
    return os.path.join(config_path, _CREDENTIALS_FILENAME)


def _run_subprocess_ignore_stderr(command):
    """ Return subprocess.check_output with the given command and ignores stderr."""
    with open(os.devnull, "w") as devnull:
        output = subprocess.check_output(command, stderr=devnull)
    return output


def get_project_id():
    """Gets the project ID from the Cloud SDK.

    Returns:
        Optional[str]: The project ID.
    """
    if os.name == "nt":
        command = _CLOUD_SDK_WINDOWS_COMMAND
    else:
        command = _CLOUD_SDK_POSIX_COMMAND

    try:
        # Ignore the stderr coming from gcloud, so it won't be mixed into the output.
        # https://github.com/googleapis/google-auth-library-python/issues/673
        project = _run_subprocess_ignore_stderr(
            (command,) + _CLOUD_SDK_CONFIG_GET_PROJECT_COMMAND
        )

        # Turn bytes into a string and remove "\n"
        project = _helpers.from_bytes(project).strip()
        return project if project else None
    except (subprocess.CalledProcessError, OSError, IOError):
        return None


def get_auth_access_token(account=None):
    """Load user access token with the ``gcloud auth print-access-token`` command.

    Args:
        account (Optional[str]): Account to get the access token for. If not
            specified, the current active account will be used.

    Returns:
        str: The user access token.

    Raises:
        google.auth.exceptions.UserAccessTokenError: if failed to get access
            token from gcloud.
    """
    if os.name == "nt":
        command = _CLOUD_SDK_WINDOWS_COMMAND
    else:
        command = _CLOUD_SDK_POSIX_COMMAND

    try:
        if account:
            command = (
                (command,)
                + _CLOUD_SDK_USER_ACCESS_TOKEN_COMMAND
                + ("--account=" + account,)
            )
        else:
            command = (command,) + _CLOUD_SDK_USER_ACCESS_TOKEN_COMMAND

        access_token = subprocess.check_output(command, stderr=subprocess.STDOUT)
        # remove the trailing "\n"
        return access_token.decode("utf-8").strip()
    except (subprocess.CalledProcessError, OSError, IOError) as caught_exc:
        new_exc = exceptions.UserAccessTokenError(
            "Failed to obtain access token", caught_exc
        )
        raise new_exc from caught_exc

# === NexusCore/openenv\Lib\site-packages\grpc\beta\utilities.py ===
# Copyright 2015 gRPC authors.
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
"""Utilities for the gRPC Python Beta API."""

import threading
import time

# implementations is referenced from specification in this module.
from grpc.beta import implementations  # pylint: disable=unused-import
from grpc.beta import interfaces
from grpc.framework.foundation import callable_util
from grpc.framework.foundation import future

_DONE_CALLBACK_EXCEPTION_LOG_MESSAGE = (
    'Exception calling connectivity future "done" callback!'
)


class _ChannelReadyFuture(future.Future):
    def __init__(self, channel):
        self._condition = threading.Condition()
        self._channel = channel

        self._matured = False
        self._cancelled = False
        self._done_callbacks = []

    def _block(self, timeout):
        until = None if timeout is None else time.time() + timeout
        with self._condition:
            while True:
                if self._cancelled:
                    raise future.CancelledError()
                elif self._matured:
                    return
                else:
                    if until is None:
                        self._condition.wait()
                    else:
                        remaining = until - time.time()
                        if remaining < 0:
                            raise future.TimeoutError()
                        else:
                            self._condition.wait(timeout=remaining)

    def _update(self, connectivity):
        with self._condition:
            if (
                not self._cancelled
                and connectivity is interfaces.ChannelConnectivity.READY
            ):
                self._matured = True
                self._channel.unsubscribe(self._update)
                self._condition.notify_all()
                done_callbacks = tuple(self._done_callbacks)
                self._done_callbacks = None
            else:
                return

        for done_callback in done_callbacks:
            callable_util.call_logging_exceptions(
                done_callback, _DONE_CALLBACK_EXCEPTION_LOG_MESSAGE, self
            )

    def cancel(self):
        with self._condition:
            if not self._matured:
                self._cancelled = True
                self._channel.unsubscribe(self._update)
                self._condition.notify_all()
                done_callbacks = tuple(self._done_callbacks)
                self._done_callbacks = None
            else:
                return False

        for done_callback in done_callbacks:
            callable_util.call_logging_exceptions(
                done_callback, _DONE_CALLBACK_EXCEPTION_LOG_MESSAGE, self
            )

        return True

    def cancelled(self):
        with self._condition:
            return self._cancelled

    def running(self):
        with self._condition:
            return not self._cancelled and not self._matured

    def done(self):
        with self._condition:
            return self._cancelled or self._matured

    def result(self, timeout=None):
        self._block(timeout)
        return None

    def exception(self, timeout=None):
        self._block(timeout)
        return None

    def traceback(self, timeout=None):
        self._block(timeout)
        return None

    def add_done_callback(self, fn):
        with self._condition:
            if not self._cancelled and not self._matured:
                self._done_callbacks.append(fn)
                return

        fn(self)

    def start(self):
        with self._condition:
            self._channel.subscribe(self._update, try_to_connect=True)

    def __del__(self):
        with self._condition:
            if not self._cancelled and not self._matured:
                self._channel.unsubscribe(self._update)


def channel_ready_future(channel):
    """Creates a future.Future tracking when an implementations.Channel is ready.

    Cancelling the returned future.Future does not tell the given
    implementations.Channel to abandon attempts it may have been making to
    connect; cancelling merely deactivates the return future.Future's
    subscription to the given implementations.Channel's connectivity.

    Args:
      channel: An implementations.Channel.

    Returns:
      A future.Future that matures when the given Channel has connectivity
        interfaces.ChannelConnectivity.READY.
    """
    ready_future = _ChannelReadyFuture(channel)
    ready_future.start()
    return ready_future

# === NexusCore/openenv\Lib\site-packages\jedi\inference\recursion.py ===
"""
Recursions are the recipe of |jedi| to conquer Python code. However, someone
must stop recursions going mad. Some settings are here to make |jedi| stop at
the right time. You can read more about them :ref:`here <settings-recursion>`.

Next to the internal ``jedi.inference.cache`` this module also makes |jedi| not
thread-safe, because ``execution_recursion_decorator`` uses class variables to
count the function calls.

.. _settings-recursion:

Settings
~~~~~~~~~~

Recursion settings are important if you don't want extremely
recursive python code to go absolutely crazy.

The default values are based on experiments while completing the |jedi| library
itself (inception!). But I don't think there's any other Python library that
uses recursion in a similarly extreme way. Completion should also be fast and
therefore the quality might not always be maximal.

.. autodata:: recursion_limit
.. autodata:: total_function_execution_limit
.. autodata:: per_function_execution_limit
.. autodata:: per_function_recursion_limit
"""

from contextlib import contextmanager

from jedi import debug
from jedi.inference.base_value import NO_VALUES


recursion_limit = 15
"""
Like :func:`sys.getrecursionlimit()`, just for |jedi|.
"""
total_function_execution_limit = 200
"""
This is a hard limit of how many non-builtin functions can be executed.
"""
per_function_execution_limit = 6
"""
The maximal amount of times a specific function may be executed.
"""
per_function_recursion_limit = 2
"""
A function may not be executed more than this number of times recursively.
"""


class RecursionDetector:
    def __init__(self):
        self.pushed_nodes = []


@contextmanager
def execution_allowed(inference_state, node):
    """
    A decorator to detect recursions in statements. In a recursion a statement
    at the same place, in the same module may not be executed two times.
    """
    pushed_nodes = inference_state.recursion_detector.pushed_nodes

    if node in pushed_nodes:
        debug.warning('catched stmt recursion: %s @%s', node,
                      getattr(node, 'start_pos', None))
        yield False
    else:
        try:
            pushed_nodes.append(node)
            yield True
        finally:
            pushed_nodes.pop()


def execution_recursion_decorator(default=NO_VALUES):
    def decorator(func):
        def wrapper(self, **kwargs):
            detector = self.inference_state.execution_recursion_detector
            limit_reached = detector.push_execution(self)
            try:
                if limit_reached:
                    result = default
                else:
                    result = func(self, **kwargs)
            finally:
                detector.pop_execution()
            return result
        return wrapper
    return decorator


class ExecutionRecursionDetector:
    """
    Catches recursions of executions.
    """
    def __init__(self, inference_state):
        self._inference_state = inference_state

        self._recursion_level = 0
        self._parent_execution_funcs = []
        self._funcdef_execution_counts = {}
        self._execution_count = 0

    def pop_execution(self):
        self._parent_execution_funcs.pop()
        self._recursion_level -= 1

    def push_execution(self, execution):
        funcdef = execution.tree_node

        # These two will be undone in pop_execution.
        self._recursion_level += 1
        self._parent_execution_funcs.append(funcdef)

        module_context = execution.get_root_context()

        if module_context.is_builtins_module():
            # We have control over builtins so we know they are not recursing
            # like crazy. Therefore we just let them execute always, because
            # they usually just help a lot with getting good results.
            return False

        if self._recursion_level > recursion_limit:
            debug.warning('Recursion limit (%s) reached', recursion_limit)
            return True

        if self._execution_count >= total_function_execution_limit:
            debug.warning('Function execution limit (%s) reached', total_function_execution_limit)
            return True
        self._execution_count += 1

        if self._funcdef_execution_counts.setdefault(funcdef, 0) >= per_function_execution_limit:
            if module_context.py__name__() == 'typing':
                return False
            debug.warning(
                'Per function execution limit (%s) reached: %s',
                per_function_execution_limit,
                funcdef
            )
            return True
        self._funcdef_execution_counts[funcdef] += 1

        if self._parent_execution_funcs.count(funcdef) > per_function_recursion_limit:
            debug.warning(
                'Per function recursion limit (%s) reached: %s',
                per_function_recursion_limit,
                funcdef
            )
            return True
        return False

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai_like\embedding\handler.py ===
# What is this?
## Handler file for OpenAI-like endpoints.
## Allows jina ai embedding calls - which don't allow 'encoding_format' in payload.

import json
from typing import Optional

import httpx

import litellm
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    get_async_httpx_client,
)
from litellm.types.utils import EmbeddingResponse

from ..common_utils import OpenAILikeBase, OpenAILikeError


class OpenAILikeEmbeddingHandler(OpenAILikeBase):
    def __init__(self, **kwargs):
        pass

    async def aembedding(
        self,
        input: list,
        data: dict,
        model_response: EmbeddingResponse,
        timeout: float,
        api_key: str,
        api_base: str,
        logging_obj,
        headers: dict,
        client=None,
    ) -> EmbeddingResponse:
        response = None
        try:
            if client is None or not isinstance(client, AsyncHTTPHandler):
                async_client = get_async_httpx_client(
                    llm_provider=litellm.LlmProviders.OPENAI,
                    params={"timeout": timeout},
                )
            else:
                async_client = client
            try:
                response = await async_client.post(
                    api_base,
                    headers=headers,
                    data=json.dumps(data),
                )  # type: ignore

                response.raise_for_status()

                response_json = response.json()
            except httpx.HTTPStatusError as e:
                raise OpenAILikeError(
                    status_code=e.response.status_code,
                    message=e.response.text if e.response else str(e),
                )
            except httpx.TimeoutException:
                raise OpenAILikeError(
                    status_code=408, message="Timeout error occurred."
                )
            except Exception as e:
                raise OpenAILikeError(status_code=500, message=str(e))

            ## LOGGING
            logging_obj.post_call(
                input=input,
                api_key=api_key,
                additional_args={"complete_input_dict": data},
                original_response=response_json,
            )
            return EmbeddingResponse(**response_json)
        except Exception as e:
            ## LOGGING
            logging_obj.post_call(
                input=input,
                api_key=api_key,
                original_response=str(e),
            )
            raise e

    def embedding(
        self,
        model: str,
        input: list,
        timeout: float,
        logging_obj,
        api_key: Optional[str],
        api_base: Optional[str],
        optional_params: dict,
        model_response: Optional[EmbeddingResponse] = None,
        client=None,
        aembedding=None,
        custom_endpoint: Optional[bool] = None,
        headers: Optional[dict] = None,
    ) -> EmbeddingResponse:
        api_base, headers = self._validate_environment(
            api_base=api_base,
            api_key=api_key,
            endpoint_type="embeddings",
            headers=headers,
            custom_endpoint=custom_endpoint,
        )
        model = model
        data = {"model": model, "input": input, **optional_params}

        ## LOGGING
        logging_obj.pre_call(
            input=input,
            api_key=api_key,
            additional_args={"complete_input_dict": data, "api_base": api_base},
        )

        if aembedding is True:
            return self.aembedding(data=data, input=input, logging_obj=logging_obj, model_response=model_response, api_base=api_base, api_key=api_key, timeout=timeout, client=client, headers=headers)  # type: ignore
        if client is None or isinstance(client, AsyncHTTPHandler):
            self.client = HTTPHandler(timeout=timeout)  # type: ignore
        else:
            self.client = client

        ## EMBEDDING CALL
        try:
            response = self.client.post(
                api_base,
                headers=headers,
                data=json.dumps(data),
            )  # type: ignore

            response.raise_for_status()  # type: ignore

            response_json = response.json()  # type: ignore
        except httpx.HTTPStatusError as e:
            raise OpenAILikeError(
                status_code=e.response.status_code,
                message=e.response.text,
            )
        except httpx.TimeoutException:
            raise OpenAILikeError(status_code=408, message="Timeout error occurred.")
        except Exception as e:
            raise OpenAILikeError(status_code=500, message=str(e))

        ## LOGGING
        logging_obj.post_call(
            input=input,
            api_key=api_key,
            additional_args={"complete_input_dict": data},
            original_response=response_json,
        )

        return litellm.EmbeddingResponse(**response_json)

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\util.py ===
# Natural Language Toolkit: Corpus Reader Utility Functions
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

######################################################################
# { Lazy Corpus Loader
######################################################################

import gc
import re

import nltk

TRY_ZIPFILE_FIRST = False


class LazyCorpusLoader:
    """
    To see the API documentation for this lazily loaded corpus, first
    run corpus.ensure_loaded(), and then run help(this_corpus).

    LazyCorpusLoader is a proxy object which is used to stand in for a
    corpus object before the corpus is loaded.  This allows NLTK to
    create an object for each corpus, but defer the costs associated
    with loading those corpora until the first time that they're
    actually accessed.

    The first time this object is accessed in any way, it will load
    the corresponding corpus, and transform itself into that corpus
    (by modifying its own ``__class__`` and ``__dict__`` attributes).

    If the corpus can not be found, then accessing this object will
    raise an exception, displaying installation instructions for the
    NLTK data package.  Once they've properly installed the data
    package (or modified ``nltk.data.path`` to point to its location),
    they can then use the corpus object without restarting python.

    :param name: The name of the corpus
    :type name: str
    :param reader_cls: The specific CorpusReader class, e.g. PlaintextCorpusReader, WordListCorpusReader
    :type reader: nltk.corpus.reader.api.CorpusReader
    :param nltk_data_subdir: The subdirectory where the corpus is stored.
    :type nltk_data_subdir: str
    :param `*args`: Any other non-keywords arguments that `reader_cls` might need.
    :param `**kwargs`: Any other keywords arguments that `reader_cls` might need.
    """

    def __init__(self, name, reader_cls, *args, **kwargs):
        from nltk.corpus.reader.api import CorpusReader

        assert issubclass(reader_cls, CorpusReader)
        self.__name = self.__name__ = name
        self.__reader_cls = reader_cls
        # If nltk_data_subdir is set explicitly
        if "nltk_data_subdir" in kwargs:
            # Use the specified subdirectory path
            self.subdir = kwargs["nltk_data_subdir"]
            # Pops the `nltk_data_subdir` argument, we don't need it anymore.
            kwargs.pop("nltk_data_subdir", None)
        else:  # Otherwise use 'nltk_data/corpora'
            self.subdir = "corpora"
        self.__args = args
        self.__kwargs = kwargs

    def __load(self):
        # Find the corpus root directory.
        zip_name = re.sub(r"(([^/]+)(/.*)?)", r"\2.zip/\1/", self.__name)
        if TRY_ZIPFILE_FIRST:
            try:
                root = nltk.data.find(f"{self.subdir}/{zip_name}")
            except LookupError as e:
                try:
                    root = nltk.data.find(f"{self.subdir}/{self.__name}")
                except LookupError:
                    raise e
        else:
            try:
                root = nltk.data.find(f"{self.subdir}/{self.__name}")
            except LookupError as e:
                try:
                    root = nltk.data.find(f"{self.subdir}/{zip_name}")
                except LookupError:
                    raise e

        # Load the corpus.
        corpus = self.__reader_cls(root, *self.__args, **self.__kwargs)

        # This is where the magic happens!  Transform ourselves into
        # the corpus by modifying our own __dict__ and __class__ to
        # match that of the corpus.

        args, kwargs = self.__args, self.__kwargs
        name, reader_cls = self.__name, self.__reader_cls

        self.__dict__ = corpus.__dict__
        self.__class__ = corpus.__class__

        # _unload support: assign __dict__ and __class__ back, then do GC.
        # after reassigning __dict__ there shouldn't be any references to
        # corpus data so the memory should be deallocated after gc.collect()
        def _unload(self):
            lazy_reader = LazyCorpusLoader(name, reader_cls, *args, **kwargs)
            self.__dict__ = lazy_reader.__dict__
            self.__class__ = lazy_reader.__class__
            gc.collect()

        self._unload = _make_bound_method(_unload, self)

    def __getattr__(self, attr):
        # Fix for inspect.isclass under Python 2.6
        # (see https://bugs.python.org/issue1225107).
        # Without this fix tests may take extra 1.5GB RAM
        # because all corpora gets loaded during test collection.
        if attr == "__bases__":
            raise AttributeError("LazyCorpusLoader object has no attribute '__bases__'")

        self.__load()
        # This looks circular, but its not, since __load() changes our
        # __class__ to something new:
        return getattr(self, attr)

    def __repr__(self):
        return "<{} in {!r} (not loaded yet)>".format(
            self.__reader_cls.__name__,
            ".../corpora/" + self.__name,
        )

    def _unload(self):
        # If an exception occurs during corpus loading then
        # '_unload' method may be unattached, so __getattr__ can be called;
        # we shouldn't trigger corpus loading again in this case.
        pass


def _make_bound_method(func, self):
    """
    Magic for creating bound methods (used for _unload).
    """

    class Foo:
        def meth(self):
            pass

    f = Foo()
    bound_method = type(f.meth)

    try:
        return bound_method(func, self, self.__class__)
    except TypeError:  # python3
        return bound_method(func, self)

# === NexusCore/openenv\Lib\site-packages\numpy\_typing\_add_docstring.py ===
"""A module for creating docstrings for sphinx ``data`` domains."""

import re
import textwrap

from ._array_like import NDArray

_docstrings_list = []


def add_newdoc(name: str, value: str, doc: str) -> None:
    """Append ``_docstrings_list`` with a docstring for `name`.

    Parameters
    ----------
    name : str
        The name of the object.
    value : str
        A string-representation of the object.
    doc : str
        The docstring of the object.

    """
    _docstrings_list.append((name, value, doc))


def _parse_docstrings() -> str:
    """Convert all docstrings in ``_docstrings_list`` into a single
    sphinx-legible text block.

    """
    type_list_ret = []
    for name, value, doc in _docstrings_list:
        s = textwrap.dedent(doc).replace("\n", "\n    ")

        # Replace sections by rubrics
        lines = s.split("\n")
        new_lines = []
        indent = ""
        for line in lines:
            m = re.match(r'^(\s+)[-=]+\s*$', line)
            if m and new_lines:
                prev = textwrap.dedent(new_lines.pop())
                if prev == "Examples":
                    indent = ""
                    new_lines.append(f'{m.group(1)}.. rubric:: {prev}')
                else:
                    indent = 4 * " "
                    new_lines.append(f'{m.group(1)}.. admonition:: {prev}')
                new_lines.append("")
            else:
                new_lines.append(f"{indent}{line}")

        s = "\n".join(new_lines)
        s_block = f""".. data:: {name}\n    :value: {value}\n    {s}"""
        type_list_ret.append(s_block)
    return "\n".join(type_list_ret)


add_newdoc('ArrayLike', 'typing.Union[...]',
    """
    A `~typing.Union` representing objects that can be coerced
    into an `~numpy.ndarray`.

    Among others this includes the likes of:

    * Scalars.
    * (Nested) sequences.
    * Objects implementing the `~class.__array__` protocol.

    .. versionadded:: 1.20

    See Also
    --------
    :term:`array_like`:
        Any scalar or sequence that can be interpreted as an ndarray.

    Examples
    --------
    .. code-block:: python

        >>> import numpy as np
        >>> import numpy.typing as npt

        >>> def as_array(a: npt.ArrayLike) -> np.ndarray:
        ...     return np.array(a)

    """)

add_newdoc('DTypeLike', 'typing.Union[...]',
    """
    A `~typing.Union` representing objects that can be coerced
    into a `~numpy.dtype`.

    Among others this includes the likes of:

    * :class:`type` objects.
    * Character codes or the names of :class:`type` objects.
    * Objects with the ``.dtype`` attribute.

    .. versionadded:: 1.20

    See Also
    --------
    :ref:`Specifying and constructing data types <arrays.dtypes.constructing>`
        A comprehensive overview of all objects that can be coerced
        into data types.

    Examples
    --------
    .. code-block:: python

        >>> import numpy as np
        >>> import numpy.typing as npt

        >>> def as_dtype(d: npt.DTypeLike) -> np.dtype:
        ...     return np.dtype(d)

    """)

add_newdoc('NDArray', repr(NDArray),
    """
    A `np.ndarray[tuple[Any, ...], np.dtype[ScalarT]] <numpy.ndarray>`
    type alias :term:`generic <generic type>` w.r.t. its
    `dtype.type <numpy.dtype.type>`.

    Can be used during runtime for typing arrays with a given dtype
    and unspecified shape.

    .. versionadded:: 1.21

    Examples
    --------
    .. code-block:: python

        >>> import numpy as np
        >>> import numpy.typing as npt

        >>> print(npt.NDArray)
        numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[~_ScalarT]]

        >>> print(npt.NDArray[np.float64])
        numpy.ndarray[tuple[typing.Any, ...], numpy.dtype[numpy.float64]]

        >>> NDArrayInt = npt.NDArray[np.int_]
        >>> a: NDArrayInt = np.arange(10)

        >>> def func(a: npt.ArrayLike) -> npt.NDArray[Any]:
        ...     return np.array(a)

    """)

_docstrings = _parse_docstrings()