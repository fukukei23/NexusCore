
# === NexusCore/openenv\Lib\site-packages\google\auth\aio\transport\sessions.py ===
# Copyright 2024 Google LLC
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

import asyncio
from contextlib import asynccontextmanager
import functools
import time
from typing import Mapping, Optional

from google.auth import _exponential_backoff, exceptions
from google.auth.aio import transport
from google.auth.aio.credentials import Credentials
from google.auth.exceptions import TimeoutError

try:
    from google.auth.aio.transport.aiohttp import Request as AiohttpRequest

    AIOHTTP_INSTALLED = True
except ImportError:  # pragma: NO COVER
    AIOHTTP_INSTALLED = False


@asynccontextmanager
async def timeout_guard(timeout):
    """
    timeout_guard is an asynchronous context manager to apply a timeout to an asynchronous block of code.

    Args:
        timeout (float): The time in seconds before the context manager times out.

    Raises:
        google.auth.exceptions.TimeoutError: If the code within the context exceeds the provided timeout.

    Usage:
        async with timeout_guard(10) as with_timeout:
            await with_timeout(async_function())
    """
    start = time.monotonic()
    total_timeout = timeout

    def _remaining_time():
        elapsed = time.monotonic() - start
        remaining = total_timeout - elapsed
        if remaining <= 0:
            raise TimeoutError(
                f"Context manager exceeded the configured timeout of {total_timeout}s."
            )
        return remaining

    async def with_timeout(coro):
        try:
            remaining = _remaining_time()
            response = await asyncio.wait_for(coro, remaining)
            return response
        except (asyncio.TimeoutError, TimeoutError) as e:
            raise TimeoutError(
                f"The operation {coro} exceeded the configured timeout of {total_timeout}s."
            ) from e

    try:
        yield with_timeout

    finally:
        _remaining_time()


class AsyncAuthorizedSession:
    """This is an asynchronous implementation of :class:`google.auth.requests.AuthorizedSession` class.
    We utilize an instance of a class that implements :class:`google.auth.aio.transport.Request` configured
    by the caller or otherwise default to `google.auth.aio.transport.aiohttp.Request` if the external aiohttp
    package is installed.

    A Requests Session class with credentials.

    This class is used to perform asynchronous requests to API endpoints that require
    authorization::

        import aiohttp
        from google.auth.aio.transport import sessions

        async with sessions.AsyncAuthorizedSession(credentials) as authed_session:
            response = await authed_session.request(
                'GET', 'https://www.googleapis.com/storage/v1/b')

    The underlying :meth:`request` implementation handles adding the
    credentials' headers to the request and refreshing credentials as needed.

    Args:
        credentials (google.auth.aio.credentials.Credentials):
            The credentials to add to the request.
        auth_request (Optional[google.auth.aio.transport.Request]):
            An instance of a class that implements
            :class:`~google.auth.aio.transport.Request` used to make requests
            and refresh credentials. If not passed,
            an instance of :class:`~google.auth.aio.transport.aiohttp.Request`
            is created.

    Raises:
        - google.auth.exceptions.TransportError: If `auth_request` is `None`
            and the external package `aiohttp` is not installed.
        - google.auth.exceptions.InvalidType: If the provided credentials are
            not of type `google.auth.aio.credentials.Credentials`.
    """

    def __init__(
        self, credentials: Credentials, auth_request: Optional[transport.Request] = None
    ):
        if not isinstance(credentials, Credentials):
            raise exceptions.InvalidType(
                f"The configured credentials of type {type(credentials)} are invalid and must be of type `google.auth.aio.credentials.Credentials`"
            )
        self._credentials = credentials
        _auth_request = auth_request
        if not _auth_request and AIOHTTP_INSTALLED:
            _auth_request = AiohttpRequest()
        if _auth_request is None:
            raise exceptions.TransportError(
                "`auth_request` must either be configured or the external package `aiohttp` must be installed to use the default value."
            )
        self._auth_request = _auth_request

    async def request(
        self,
        method: str,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Mapping[str, str]] = None,
        max_allowed_time: float = transport._DEFAULT_TIMEOUT_SECONDS,
        timeout: float = transport._DEFAULT_TIMEOUT_SECONDS,
        **kwargs,
    ) -> transport.Response:
        """
        Args:
                method (str): The http method used to make the request.
                url (str): The URI to be requested.
                data (Optional[bytes]): The payload or body in HTTP request.
                headers (Optional[Mapping[str, str]]): Request headers.
                timeout (float):
                The amount of time in seconds to wait for the server response
                with each individual request.
                max_allowed_time (float):
                If the method runs longer than this, a ``Timeout`` exception is
                automatically raised. Unlike the ``timeout`` parameter, this
                value applies to the total method execution time, even if
                multiple requests are made under the hood.

                Mind that it is not guaranteed that the timeout error is raised
                at ``max_allowed_time``. It might take longer, for example, if
                an underlying request takes a lot of time, but the request
                itself does not timeout, e.g. if a large file is being
                transmitted. The timout error will be raised after such
                request completes.

        Returns:
                google.auth.aio.transport.Response: The HTTP response.

        Raises:
                google.auth.exceptions.TimeoutError: If the method does not complete within
                the configured `max_allowed_time` or the request exceeds the configured
                `timeout`.
        """

        retries = _exponential_backoff.AsyncExponentialBackoff(
            total_attempts=transport.DEFAULT_MAX_RETRY_ATTEMPTS
        )
        async with timeout_guard(max_allowed_time) as with_timeout:
            await with_timeout(
                # Note: before_request will attempt to refresh credentials if expired.
                self._credentials.before_request(
                    self._auth_request, method, url, headers
                )
            )
            # Workaround issue in python 3.9 related to code coverage by adding `# pragma: no branch`
            # See https://github.com/googleapis/gapic-generator-python/pull/1174#issuecomment-1025132372
            async for _ in retries:  # pragma: no branch
                response = await with_timeout(
                    self._auth_request(url, method, data, headers, timeout, **kwargs)
                )
                if response.status_code not in transport.DEFAULT_RETRYABLE_STATUS_CODES:
                    break
        return response

    @functools.wraps(request)
    async def get(
        self,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Mapping[str, str]] = None,
        max_allowed_time: float = transport._DEFAULT_TIMEOUT_SECONDS,
        timeout: float = transport._DEFAULT_TIMEOUT_SECONDS,
        **kwargs,
    ) -> transport.Response:
        return await self.request(
            "GET", url, data, headers, max_allowed_time, timeout, **kwargs
        )

    @functools.wraps(request)
    async def post(
        self,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Mapping[str, str]] = None,
        max_allowed_time: float = transport._DEFAULT_TIMEOUT_SECONDS,
        timeout: float = transport._DEFAULT_TIMEOUT_SECONDS,
        **kwargs,
    ) -> transport.Response:
        return await self.request(
            "POST", url, data, headers, max_allowed_time, timeout, **kwargs
        )

    @functools.wraps(request)
    async def put(
        self,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Mapping[str, str]] = None,
        max_allowed_time: float = transport._DEFAULT_TIMEOUT_SECONDS,
        timeout: float = transport._DEFAULT_TIMEOUT_SECONDS,
        **kwargs,
    ) -> transport.Response:
        return await self.request(
            "PUT", url, data, headers, max_allowed_time, timeout, **kwargs
        )

    @functools.wraps(request)
    async def patch(
        self,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Mapping[str, str]] = None,
        max_allowed_time: float = transport._DEFAULT_TIMEOUT_SECONDS,
        timeout: float = transport._DEFAULT_TIMEOUT_SECONDS,
        **kwargs,
    ) -> transport.Response:
        return await self.request(
            "PATCH", url, data, headers, max_allowed_time, timeout, **kwargs
        )

    @functools.wraps(request)
    async def delete(
        self,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Mapping[str, str]] = None,
        max_allowed_time: float = transport._DEFAULT_TIMEOUT_SECONDS,
        timeout: float = transport._DEFAULT_TIMEOUT_SECONDS,
        **kwargs,
    ) -> transport.Response:
        return await self.request(
            "DELETE", url, data, headers, max_allowed_time, timeout, **kwargs
        )

    async def close(self) -> None:
        """
        Close the underlying auth request session.
        """
        await self._auth_request.close()

# === NexusCore/openenv\Lib\site-packages\IPython\core\alias.py ===
# encoding: utf-8
"""
System command aliases.

Authors:

* Fernando Perez
* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.
#
#  The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import os
import re
import sys

from traitlets.config.configurable import Configurable
from .error import UsageError

from traitlets import List, Instance
from logging import error

import typing as t


#-----------------------------------------------------------------------------
# Utilities
#-----------------------------------------------------------------------------

# This is used as the pattern for calls to split_user_input.
shell_line_split = re.compile(r'^(\s*)()(\S+)(.*$)')

def default_aliases() -> t.List[t.Tuple[str, str]]:
    """Return list of shell aliases to auto-define.
    """
    # Note: the aliases defined here should be safe to use on a kernel
    # regardless of what frontend it is attached to.  Frontends that use a
    # kernel in-process can define additional aliases that will only work in
    # their case.  For example, things like 'less' or 'clear' that manipulate
    # the terminal should NOT be declared here, as they will only work if the
    # kernel is running inside a true terminal, and not over the network.

    if os.name == 'posix':
        default_aliases = [('mkdir', 'mkdir'), ('rmdir', 'rmdir'),
                           ('mv', 'mv'), ('rm', 'rm'), ('cp', 'cp'),
                           ('cat', 'cat'),
                           ]
        # Useful set of ls aliases.  The GNU and BSD options are a little
        # different, so we make aliases that provide as similar as possible
        # behavior in ipython, by passing the right flags for each platform
        if sys.platform.startswith('linux'):
            ls_aliases = [('ls', 'ls -F --color'),
                          # long ls
                          ('ll', 'ls -F -o --color'),
                          # ls normal files only
                          ('lf', 'ls -F -o --color %l | grep ^-'),
                          # ls symbolic links
                          ('lk', 'ls -F -o --color %l | grep ^l'),
                          # directories or links to directories,
                          ('ldir', 'ls -F -o --color %l | grep /$'),
                          # things which are executable
                          ('lx', 'ls -F -o --color %l | grep ^-..x'),
                          ]
        elif sys.platform.startswith('openbsd') or sys.platform.startswith('netbsd'):
            # OpenBSD, NetBSD. The ls implementation on these platforms do not support
            # the -G switch and lack the ability to use colorized output.
            ls_aliases = [('ls', 'ls -F'),
                          # long ls
                          ('ll', 'ls -F -l'),
                          # ls normal files only
                          ('lf', 'ls -F -l %l | grep ^-'),
                          # ls symbolic links
                          ('lk', 'ls -F -l %l | grep ^l'),
                          # directories or links to directories,
                          ('ldir', 'ls -F -l %l | grep /$'),
                          # things which are executable
                          ('lx', 'ls -F -l %l | grep ^-..x'),
                          ]
        else:
            # BSD, OSX, etc.
            ls_aliases = [('ls', 'ls -F -G'),
                          # long ls
                          ('ll', 'ls -F -l -G'),
                          # ls normal files only
                          ('lf', 'ls -F -l -G %l | grep ^-'),
                          # ls symbolic links
                          ('lk', 'ls -F -l -G %l | grep ^l'),
                          # directories or links to directories,
                          ('ldir', 'ls -F -G -l %l | grep /$'),
                          # things which are executable
                          ('lx', 'ls -F -l -G %l | grep ^-..x'),
                          ]
        default_aliases = default_aliases + ls_aliases
    elif os.name in ['nt', 'dos']:
        default_aliases = [('ls', 'dir /on'),
                           ('ddir', 'dir /ad /on'), ('ldir', 'dir /ad /on'),
                           ('mkdir', 'mkdir'), ('rmdir', 'rmdir'),
                           ('echo', 'echo'), ('ren', 'ren'), ('copy', 'copy'),
                           ]
    else:
        default_aliases = []

    return default_aliases


class AliasError(Exception):
    pass


class InvalidAliasError(AliasError):
    pass


class Alias:
    """Callable object storing the details of one alias.

    Instances are registered as magic functions to allow use of aliases.
    """

    # Prepare blacklist
    blacklist = {'cd','popd','pushd','dhist','alias','unalias'}

    def __init__(self, shell, name, cmd):
        self.shell = shell
        self.name = name
        self.cmd = cmd
        self.__doc__ = "Alias for `!{}`".format(cmd)
        self.nargs = self.validate()

    def validate(self):
        """Validate the alias, and return the number of arguments."""
        if self.name in self.blacklist:
            raise InvalidAliasError("The name %s can't be aliased "
                                    "because it is a keyword or builtin." % self.name)
        try:
            caller = self.shell.magics_manager.magics['line'][self.name]
        except KeyError:
            pass
        else:
            if not isinstance(caller, Alias):
                raise InvalidAliasError("The name %s can't be aliased "
                                        "because it is another magic command." % self.name)

        if not (isinstance(self.cmd, str)):
            raise InvalidAliasError("An alias command must be a string, "
                                    "got: %r" % self.cmd)

        nargs = self.cmd.count('%s') - self.cmd.count('%%s')
  
        if (nargs > 0) and (self.cmd.find('%l') >= 0):
            raise InvalidAliasError('The %s and %l specifiers are mutually '
                                    'exclusive in alias definitions.')

        return nargs

    def __repr__(self):
        return "<alias {} for {!r}>".format(self.name, self.cmd)

    def __call__(self, rest=''):
        cmd = self.cmd
        nargs = self.nargs
        # Expand the %l special to be the user's input line
        if cmd.find('%l') >= 0:
            cmd = cmd.replace('%l', rest)
            rest = ''
        
        if nargs==0:
            if cmd.find('%%s') >= 1:
                cmd = cmd.replace('%%s', '%s')
            # Simple, argument-less aliases
            cmd = '%s %s' % (cmd, rest)
        else:
            # Handle aliases with positional arguments
            args = rest.split(None, nargs)
            if len(args) < nargs:
                raise UsageError('Alias <%s> requires %s arguments, %s given.' %
                      (self.name, nargs, len(args)))
            cmd = '%s %s' % (cmd % tuple(args[:nargs]),' '.join(args[nargs:]))

        self.shell.system(cmd)

#-----------------------------------------------------------------------------
# Main AliasManager class
#-----------------------------------------------------------------------------

class AliasManager(Configurable):
    default_aliases: List = List(default_aliases()).tag(config=True)
    user_aliases: List = List(default_value=[]).tag(config=True)
    shell = Instance(
        "IPython.core.interactiveshell.InteractiveShellABC", allow_none=True
    )

    def __init__(self, shell=None, **kwargs):
        super(AliasManager, self).__init__(shell=shell, **kwargs)
        # For convenient access
        if self.shell is not None:
            self.linemagics = self.shell.magics_manager.magics["line"]
            self.init_aliases()

    def init_aliases(self):
        # Load default & user aliases
        for name, cmd in self.default_aliases + self.user_aliases:
            if (
                cmd.startswith("ls ")
                and self.shell is not None
                and self.shell.colors == "nocolor"
            ):
                cmd = cmd.replace(" --color", "")
            self.soft_define_alias(name, cmd)

    @property
    def aliases(self):
        return [(n, func.cmd) for (n, func) in self.linemagics.items()
                            if isinstance(func, Alias)]

    def soft_define_alias(self, name, cmd):
        """Define an alias, but don't raise on an AliasError."""
        try:
            self.define_alias(name, cmd)
        except AliasError as e:
            error("Invalid alias: %s" % e)

    def define_alias(self, name, cmd):
        """Define a new alias after validating it.

        This will raise an :exc:`AliasError` if there are validation
        problems.
        """
        caller = Alias(shell=self.shell, name=name, cmd=cmd)
        self.shell.magics_manager.register_function(caller, magic_kind='line',
                                                    magic_name=name)

    def get_alias(self, name):
        """Return an alias, or None if no alias by that name exists."""
        aname = self.linemagics.get(name, None)
        return aname if isinstance(aname, Alias) else None

    def is_alias(self, name):
        """Return whether or not a given name has been defined as an alias"""
        return self.get_alias(name) is not None

    def undefine_alias(self, name):
        if self.is_alias(name):
            del self.linemagics[name]
        else:
            raise ValueError('%s is not an alias' % name)

    def clear_aliases(self):
        for name, _ in self.aliases:
            self.undefine_alias(name)

    def retrieve_alias(self, name):
        """Retrieve the command to which an alias expands."""
        caller = self.get_alias(name)
        if caller:
            return caller.cmd
        else:
            raise ValueError('%s is not an alias' % name)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\cost_calculator.py ===
# What is this?
## Cost calculation for Google AI Studio / Vertex AI models
from typing import Literal, Optional, Tuple, Union

import litellm
from litellm import verbose_logger
from litellm.litellm_core_utils.llm_cost_calc.utils import (
    _is_above_128k,
    generic_cost_per_token,
)
from litellm.types.utils import ModelInfo, Usage

"""
Gemini pricing covers: 
- token
- image
- audio
- video
"""

"""
Vertex AI -> character based pricing 

Google AI Studio -> token based pricing
"""

models_without_dynamic_pricing = ["gemini-1.0-pro", "gemini-pro", "gemini-2"]


def cost_router(
    model: str,
    custom_llm_provider: str,
    call_type: Union[Literal["embedding", "aembedding"], str],
) -> Literal["cost_per_character", "cost_per_token"]:
    """
    Route the cost calc to the right place, based on model/call_type/etc.

    Returns
        - str, the specific google cost calc function it should route to.
    """
    if custom_llm_provider == "vertex_ai" and (
        "claude" in model
        or "llama" in model
        or "mistral" in model
        or "jamba" in model
        or "codestral" in model
    ):
        return "cost_per_token"
    elif custom_llm_provider == "vertex_ai" and (
        call_type == "embedding" or call_type == "aembedding"
    ):
        return "cost_per_token"
    elif custom_llm_provider == "vertex_ai" and ("gemini-2" in model):
        return "cost_per_token"
    return "cost_per_character"


def cost_per_character(
    model: str,
    custom_llm_provider: str,
    usage: Usage,
    prompt_characters: Optional[float] = None,
    completion_characters: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Calculates the cost per character for a given VertexAI model, input messages, and response object.

    Input:
        - model: str, the model name without provider prefix
        - custom_llm_provider: str, "vertex_ai-*"
        - prompt_characters: float, the number of input characters
        - completion_characters: float, the number of output characters

    Returns:
        Tuple[float, float] - prompt_cost_in_usd, completion_cost_in_usd

    Raises:
        Exception if model requires >128k pricing, but model cost not mapped
    """
    model_info = litellm.get_model_info(
        model=model, custom_llm_provider=custom_llm_provider
    )

    ## GET MODEL INFO
    model_info = litellm.get_model_info(
        model=model, custom_llm_provider=custom_llm_provider
    )

    ## CALCULATE INPUT COST
    if prompt_characters is None:
        prompt_cost, _ = cost_per_token(
            model=model,
            custom_llm_provider=custom_llm_provider,
            usage=usage,
        )
    else:
        try:
            if (
                _is_above_128k(tokens=prompt_characters * 4)  # 1 token = 4 char
                and model not in models_without_dynamic_pricing
            ):
                ## check if character pricing, else default to token pricing
                assert (
                    "input_cost_per_character_above_128k_tokens" in model_info
                    and model_info["input_cost_per_character_above_128k_tokens"]
                    is not None
                ), "model info for model={} does not have 'input_cost_per_character_above_128k_tokens'-pricing for > 128k tokens\nmodel_info={}".format(
                    model, model_info
                )
                prompt_cost = (
                    prompt_characters
                    * model_info["input_cost_per_character_above_128k_tokens"]
                )
            else:
                assert (
                    "input_cost_per_character" in model_info
                    and model_info["input_cost_per_character"] is not None
                ), "model info for model={} does not have 'input_cost_per_character'-pricing\nmodel_info={}".format(
                    model, model_info
                )
                prompt_cost = prompt_characters * model_info["input_cost_per_character"]
        except Exception as e:
            verbose_logger.debug(
                "litellm.litellm_core_utils.llm_cost_calc.google.py::cost_per_character(): Exception occured - {}\nDefaulting to None".format(
                    str(e)
                )
            )
            prompt_cost, _ = cost_per_token(
                model=model,
                custom_llm_provider=custom_llm_provider,
                usage=usage,
            )

    ## CALCULATE OUTPUT COST
    if completion_characters is None:
        _, completion_cost = cost_per_token(
            model=model,
            custom_llm_provider=custom_llm_provider,
            usage=usage,
        )
    else:
        completion_tokens = usage.completion_tokens
        try:
            if (
                _is_above_128k(tokens=completion_characters * 4)  # 1 token = 4 char
                and model not in models_without_dynamic_pricing
            ):
                assert (
                    "output_cost_per_character_above_128k_tokens" in model_info
                    and model_info["output_cost_per_character_above_128k_tokens"]
                    is not None
                ), "model info for model={} does not have 'output_cost_per_character_above_128k_tokens' pricing\nmodel_info={}".format(
                    model, model_info
                )
                completion_cost = (
                    completion_tokens
                    * model_info["output_cost_per_character_above_128k_tokens"]
                )
            else:
                assert (
                    "output_cost_per_character" in model_info
                    and model_info["output_cost_per_character"] is not None
                ), "model info for model={} does not have 'output_cost_per_character'-pricing\nmodel_info={}".format(
                    model, model_info
                )
                completion_cost = (
                    completion_characters * model_info["output_cost_per_character"]
                )
        except Exception as e:
            verbose_logger.debug(
                "litellm.litellm_core_utils.llm_cost_calc.google.py::cost_per_character(): Exception occured - {}\nDefaulting to None".format(
                    str(e)
                )
            )
            _, completion_cost = cost_per_token(
                model=model,
                custom_llm_provider=custom_llm_provider,
                usage=usage,
            )

    return prompt_cost, completion_cost


def _handle_128k_pricing(
    model_info: ModelInfo,
    usage: Usage,
) -> Tuple[float, float]:
    ## CALCULATE INPUT COST
    input_cost_per_token_above_128k_tokens = model_info.get(
        "input_cost_per_token_above_128k_tokens"
    )
    output_cost_per_token_above_128k_tokens = model_info.get(
        "output_cost_per_token_above_128k_tokens"
    )

    prompt_tokens = usage.prompt_tokens
    completion_tokens = usage.completion_tokens

    if (
        _is_above_128k(tokens=prompt_tokens)
        and input_cost_per_token_above_128k_tokens is not None
    ):
        prompt_cost = prompt_tokens * input_cost_per_token_above_128k_tokens
    else:
        prompt_cost = prompt_tokens * model_info["input_cost_per_token"]

    ## CALCULATE OUTPUT COST
    output_cost_per_token_above_128k_tokens = model_info.get(
        "output_cost_per_token_above_128k_tokens"
    )
    if (
        _is_above_128k(tokens=completion_tokens)
        and output_cost_per_token_above_128k_tokens is not None
    ):
        completion_cost = completion_tokens * output_cost_per_token_above_128k_tokens
    else:
        completion_cost = completion_tokens * model_info["output_cost_per_token"]

    return prompt_cost, completion_cost


def cost_per_token(
    model: str,
    custom_llm_provider: str,
    usage: Usage,
) -> Tuple[float, float]:
    """
    Calculates the cost per token for a given model, prompt tokens, and completion tokens.

    Input:
        - model: str, the model name without provider prefix
        - custom_llm_provider: str, either "vertex_ai-*" or "gemini"
        - prompt_tokens: float, the number of input tokens
        - completion_tokens: float, the number of output tokens

    Returns:
        Tuple[float, float] - prompt_cost_in_usd, completion_cost_in_usd

    Raises:
        Exception if model requires >128k pricing, but model cost not mapped
    """

    ## GET MODEL INFO
    model_info = litellm.get_model_info(
        model=model, custom_llm_provider=custom_llm_provider
    )

    ## HANDLE 128k+ PRICING
    input_cost_per_token_above_128k_tokens = model_info.get(
        "input_cost_per_token_above_128k_tokens"
    )
    output_cost_per_token_above_128k_tokens = model_info.get(
        "output_cost_per_token_above_128k_tokens"
    )
    if (
        input_cost_per_token_above_128k_tokens is not None
        or output_cost_per_token_above_128k_tokens is not None
    ):
        return _handle_128k_pricing(
            model_info=model_info,
            usage=usage,
        )

    return generic_cost_per_token(
        model=model,
        custom_llm_provider=custom_llm_provider,
        usage=usage,
    )

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\_inspect.py ===
import inspect
from inspect import cleandoc, getdoc, getfile, isclass, ismodule, signature
from typing import Any, Collection, Iterable, Optional, Tuple, Type, Union

from .console import Group, RenderableType
from .control import escape_control_codes
from .highlighter import ReprHighlighter
from .jupyter import JupyterMixin
from .panel import Panel
from .pretty import Pretty
from .table import Table
from .text import Text, TextType


def _first_paragraph(doc: str) -> str:
    """Get the first paragraph from a docstring."""
    paragraph, _, _ = doc.partition("\n\n")
    return paragraph


class Inspect(JupyterMixin):
    """A renderable to inspect any Python Object.

    Args:
        obj (Any): An object to inspect.
        title (str, optional): Title to display over inspect result, or None use type. Defaults to None.
        help (bool, optional): Show full help text rather than just first paragraph. Defaults to False.
        methods (bool, optional): Enable inspection of callables. Defaults to False.
        docs (bool, optional): Also render doc strings. Defaults to True.
        private (bool, optional): Show private attributes (beginning with underscore). Defaults to False.
        dunder (bool, optional): Show attributes starting with double underscore. Defaults to False.
        sort (bool, optional): Sort attributes alphabetically. Defaults to True.
        all (bool, optional): Show all attributes. Defaults to False.
        value (bool, optional): Pretty print value of object. Defaults to True.
    """

    def __init__(
        self,
        obj: Any,
        *,
        title: Optional[TextType] = None,
        help: bool = False,
        methods: bool = False,
        docs: bool = True,
        private: bool = False,
        dunder: bool = False,
        sort: bool = True,
        all: bool = True,
        value: bool = True,
    ) -> None:
        self.highlighter = ReprHighlighter()
        self.obj = obj
        self.title = title or self._make_title(obj)
        if all:
            methods = private = dunder = True
        self.help = help
        self.methods = methods
        self.docs = docs or help
        self.private = private or dunder
        self.dunder = dunder
        self.sort = sort
        self.value = value

    def _make_title(self, obj: Any) -> Text:
        """Make a default title."""
        title_str = (
            str(obj)
            if (isclass(obj) or callable(obj) or ismodule(obj))
            else str(type(obj))
        )
        title_text = self.highlighter(title_str)
        return title_text

    def __rich__(self) -> Panel:
        return Panel.fit(
            Group(*self._render()),
            title=self.title,
            border_style="scope.border",
            padding=(0, 1),
        )

    def _get_signature(self, name: str, obj: Any) -> Optional[Text]:
        """Get a signature for a callable."""
        try:
            _signature = str(signature(obj)) + ":"
        except ValueError:
            _signature = "(...)"
        except TypeError:
            return None

        source_filename: Optional[str] = None
        try:
            source_filename = getfile(obj)
        except (OSError, TypeError):
            # OSError is raised if obj has no source file, e.g. when defined in REPL.
            pass

        callable_name = Text(name, style="inspect.callable")
        if source_filename:
            callable_name.stylize(f"link file://{source_filename}")
        signature_text = self.highlighter(_signature)

        qualname = name or getattr(obj, "__qualname__", name)

        # If obj is a module, there may be classes (which are callable) to display
        if inspect.isclass(obj):
            prefix = "class"
        elif inspect.iscoroutinefunction(obj):
            prefix = "async def"
        else:
            prefix = "def"

        qual_signature = Text.assemble(
            (f"{prefix} ", f"inspect.{prefix.replace(' ', '_')}"),
            (qualname, "inspect.callable"),
            signature_text,
        )

        return qual_signature

    def _render(self) -> Iterable[RenderableType]:
        """Render object."""

        def sort_items(item: Tuple[str, Any]) -> Tuple[bool, str]:
            key, (_error, value) = item
            return (callable(value), key.strip("_").lower())

        def safe_getattr(attr_name: str) -> Tuple[Any, Any]:
            """Get attribute or any exception."""
            try:
                return (None, getattr(obj, attr_name))
            except Exception as error:
                return (error, None)

        obj = self.obj
        keys = dir(obj)
        total_items = len(keys)
        if not self.dunder:
            keys = [key for key in keys if not key.startswith("__")]
        if not self.private:
            keys = [key for key in keys if not key.startswith("_")]
        not_shown_count = total_items - len(keys)
        items = [(key, safe_getattr(key)) for key in keys]
        if self.sort:
            items.sort(key=sort_items)

        items_table = Table.grid(padding=(0, 1), expand=False)
        items_table.add_column(justify="right")
        add_row = items_table.add_row
        highlighter = self.highlighter

        if callable(obj):
            signature = self._get_signature("", obj)
            if signature is not None:
                yield signature
                yield ""

        if self.docs:
            _doc = self._get_formatted_doc(obj)
            if _doc is not None:
                doc_text = Text(_doc, style="inspect.help")
                doc_text = highlighter(doc_text)
                yield doc_text
                yield ""

        if self.value and not (isclass(obj) or callable(obj) or ismodule(obj)):
            yield Panel(
                Pretty(obj, indent_guides=True, max_length=10, max_string=60),
                border_style="inspect.value.border",
            )
            yield ""

        for key, (error, value) in items:
            key_text = Text.assemble(
                (
                    key,
                    "inspect.attr.dunder" if key.startswith("__") else "inspect.attr",
                ),
                (" =", "inspect.equals"),
            )
            if error is not None:
                warning = key_text.copy()
                warning.stylize("inspect.error")
                add_row(warning, highlighter(repr(error)))
                continue

            if callable(value):
                if not self.methods:
                    continue

                _signature_text = self._get_signature(key, value)
                if _signature_text is None:
                    add_row(key_text, Pretty(value, highlighter=highlighter))
                else:
                    if self.docs:
                        docs = self._get_formatted_doc(value)
                        if docs is not None:
                            _signature_text.append("\n" if "\n" in docs else " ")
                            doc = highlighter(docs)
                            doc.stylize("inspect.doc")
                            _signature_text.append(doc)

                    add_row(key_text, _signature_text)
            else:
                add_row(key_text, Pretty(value, highlighter=highlighter))
        if items_table.row_count:
            yield items_table
        elif not_shown_count:
            yield Text.from_markup(
                f"[b cyan]{not_shown_count}[/][i] attribute(s) not shown.[/i] "
                f"Run [b][magenta]inspect[/]([not b]inspect[/])[/b] for options."
            )

    def _get_formatted_doc(self, object_: Any) -> Optional[str]:
        """
        Extract the docstring of an object, process it and returns it.
        The processing consists in cleaning up the doctring's indentation,
        taking only its 1st paragraph if `self.help` is not True,
        and escape its control codes.

        Args:
            object_ (Any): the object to get the docstring from.

        Returns:
            Optional[str]: the processed docstring, or None if no docstring was found.
        """
        docs = getdoc(object_)
        if docs is None:
            return None
        docs = cleandoc(docs).strip()
        if not self.help:
            docs = _first_paragraph(docs)
        return escape_control_codes(docs)


def get_object_types_mro(obj: Union[object, Type[Any]]) -> Tuple[type, ...]:
    """Returns the MRO of an object's class, or of the object itself if it's a class."""
    if not hasattr(obj, "__mro__"):
        # N.B. we cannot use `if type(obj) is type` here because it doesn't work with
        # some types of classes, such as the ones that use abc.ABCMeta.
        obj = type(obj)
    return getattr(obj, "__mro__", ())


def get_object_types_mro_as_strings(obj: object) -> Collection[str]:
    """
    Returns the MRO of an object's class as full qualified names, or of the object itself if it's a class.

    Examples:
        `object_types_mro_as_strings(JSONDecoder)` will return `['json.decoder.JSONDecoder', 'builtins.object']`
    """
    return [
        f'{getattr(type_, "__module__", "")}.{getattr(type_, "__qualname__", "")}'
        for type_ in get_object_types_mro(obj)
    ]


def is_object_one_of_types(
    obj: object, fully_qualified_types_names: Collection[str]
) -> bool:
    """
    Returns `True` if the given object's class (or the object itself, if it's a class) has one of the
    fully qualified names in its MRO.
    """
    for type_name in get_object_types_mro_as_strings(obj):
        if type_name in fully_qualified_types_names:
            return True
    return False

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_browser.py ===
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

import json
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Dict, List, Optional, Pattern, Sequence, Union, cast

from playwright._impl._api_structures import (
    ClientCertificate,
    Geolocation,
    HttpCredentials,
    ProxySettings,
    StorageState,
    ViewportSize,
)
from playwright._impl._artifact import Artifact
from playwright._impl._browser_context import BrowserContext
from playwright._impl._cdp_session import CDPSession
from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._errors import is_target_closed_error
from playwright._impl._helper import (
    ColorScheme,
    Contrast,
    ForcedColors,
    HarContentPolicy,
    HarMode,
    ReducedMotion,
    ServiceWorkersPolicy,
    async_readfile,
    locals_to_params,
    make_dirs_for_file,
    prepare_record_har_options,
)
from playwright._impl._network import serialize_headers, to_client_certificates_protocol
from playwright._impl._page import Page

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_type import BrowserType


class Browser(ChannelOwner):
    Events = SimpleNamespace(
        Disconnected="disconnected",
    )

    def __init__(
        self, parent: "BrowserType", type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._browser_type = parent
        self._is_connected = True
        self._should_close_connection_on_close = False
        self._cr_tracing_path: Optional[str] = None

        self._contexts: List[BrowserContext] = []
        self._channel.on("close", lambda _: self._on_close())
        self._close_reason: Optional[str] = None

    def __repr__(self) -> str:
        return f"<Browser type={self._browser_type} version={self.version}>"

    def _on_close(self) -> None:
        self._is_connected = False
        self.emit(Browser.Events.Disconnected, self)

    @property
    def contexts(self) -> List[BrowserContext]:
        return self._contexts.copy()

    @property
    def browser_type(self) -> "BrowserType":
        return self._browser_type

    def is_connected(self) -> bool:
        return self._is_connected

    async def new_context(
        self,
        viewport: ViewportSize = None,
        screen: ViewportSize = None,
        noViewport: bool = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: Geolocation = None,
        permissions: Sequence[str] = None,
        extraHTTPHeaders: Dict[str, str] = None,
        offline: bool = None,
        httpCredentials: HttpCredentials = None,
        deviceScaleFactor: float = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: ColorScheme = None,
        reducedMotion: ReducedMotion = None,
        forcedColors: ForcedColors = None,
        contrast: Contrast = None,
        acceptDownloads: bool = None,
        defaultBrowserType: str = None,
        proxy: ProxySettings = None,
        recordHarPath: Union[Path, str] = None,
        recordHarOmitContent: bool = None,
        recordVideoDir: Union[Path, str] = None,
        recordVideoSize: ViewportSize = None,
        storageState: Union[StorageState, str, Path] = None,
        baseURL: str = None,
        strictSelectors: bool = None,
        serviceWorkers: ServiceWorkersPolicy = None,
        recordHarUrlFilter: Union[Pattern[str], str] = None,
        recordHarMode: HarMode = None,
        recordHarContent: HarContentPolicy = None,
        clientCertificates: List[ClientCertificate] = None,
    ) -> BrowserContext:
        params = locals_to_params(locals())
        await prepare_browser_context_params(params)

        channel = await self._channel.send("newContext", params)
        context = cast(BrowserContext, from_channel(channel))
        self._browser_type._did_create_context(context, params, {})
        return context

    async def new_page(
        self,
        viewport: ViewportSize = None,
        screen: ViewportSize = None,
        noViewport: bool = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: Geolocation = None,
        permissions: Sequence[str] = None,
        extraHTTPHeaders: Dict[str, str] = None,
        offline: bool = None,
        httpCredentials: HttpCredentials = None,
        deviceScaleFactor: float = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: ColorScheme = None,
        forcedColors: ForcedColors = None,
        contrast: Contrast = None,
        reducedMotion: ReducedMotion = None,
        acceptDownloads: bool = None,
        defaultBrowserType: str = None,
        proxy: ProxySettings = None,
        recordHarPath: Union[Path, str] = None,
        recordHarOmitContent: bool = None,
        recordVideoDir: Union[Path, str] = None,
        recordVideoSize: ViewportSize = None,
        storageState: Union[StorageState, str, Path] = None,
        baseURL: str = None,
        strictSelectors: bool = None,
        serviceWorkers: ServiceWorkersPolicy = None,
        recordHarUrlFilter: Union[Pattern[str], str] = None,
        recordHarMode: HarMode = None,
        recordHarContent: HarContentPolicy = None,
        clientCertificates: List[ClientCertificate] = None,
    ) -> Page:
        params = locals_to_params(locals())

        async def inner() -> Page:
            context = await self.new_context(**params)
            page = await context.new_page()
            page._owned_context = context
            context._owner_page = page
            return page

        return await self._connection.wrap_api_call(inner)

    async def close(self, reason: str = None) -> None:
        self._close_reason = reason
        try:
            if self._should_close_connection_on_close:
                await self._connection.stop_async()
            else:
                await self._channel.send("close", {"reason": reason})
        except Exception as e:
            if not is_target_closed_error(e):
                raise e

    @property
    def version(self) -> str:
        return self._initializer["version"]

    async def new_browser_cdp_session(self) -> CDPSession:
        return from_channel(await self._channel.send("newBrowserCDPSession"))

    async def start_tracing(
        self,
        page: Page = None,
        path: Union[str, Path] = None,
        screenshots: bool = None,
        categories: Sequence[str] = None,
    ) -> None:
        params = locals_to_params(locals())
        if page:
            params["page"] = page._channel
        if path:
            self._cr_tracing_path = str(path)
            params["path"] = str(path)
        await self._channel.send("startTracing", params)

    async def stop_tracing(self) -> bytes:
        artifact = cast(Artifact, from_channel(await self._channel.send("stopTracing")))
        buffer = await artifact.read_info_buffer()
        await artifact.delete()
        if self._cr_tracing_path:
            make_dirs_for_file(self._cr_tracing_path)
            with open(self._cr_tracing_path, "wb") as f:
                f.write(buffer)
            self._cr_tracing_path = None
        return buffer


async def prepare_browser_context_params(params: Dict) -> None:
    if params.get("noViewport"):
        del params["noViewport"]
        params["noDefaultViewport"] = True
    if "defaultBrowserType" in params:
        del params["defaultBrowserType"]
    if "extraHTTPHeaders" in params:
        params["extraHTTPHeaders"] = serialize_headers(params["extraHTTPHeaders"])
    if "recordHarPath" in params:
        params["recordHar"] = prepare_record_har_options(params)
        del params["recordHarPath"]
    if "recordVideoDir" in params:
        params["recordVideo"] = {"dir": Path(params["recordVideoDir"]).absolute()}
        if "recordVideoSize" in params:
            params["recordVideo"]["size"] = params["recordVideoSize"]
            del params["recordVideoSize"]
        del params["recordVideoDir"]
    if "storageState" in params:
        storageState = params["storageState"]
        if not isinstance(storageState, dict):
            params["storageState"] = json.loads(
                (await async_readfile(storageState)).decode()
            )
    if params.get("colorScheme", None) == "null":
        params["colorScheme"] = "no-override"
    if params.get("reducedMotion", None) == "null":
        params["reducedMotion"] = "no-override"
    if params.get("forcedColors", None) == "null":
        params["forcedColors"] = "no-override"
    if params.get("contrast", None) == "null":
        params["contrast"] = "no-override"
    if "acceptDownloads" in params:
        params["acceptDownloads"] = "accept" if params["acceptDownloads"] else "deny"

    if "clientCertificates" in params:
        params["clientCertificates"] = await to_client_certificates_protocol(
            params["clientCertificates"]
        )

# === NexusCore/openenv\Lib\site-packages\tornado\test\autoreload_test.py ===
import os
import shutil
import subprocess
from subprocess import Popen
import sys
from tempfile import mkdtemp
import textwrap
import time
import unittest


class AutoreloadTest(unittest.TestCase):
    def setUp(self):
        # When these tests fail the output sometimes exceeds the default maxDiff.
        self.maxDiff = 1024

        self.path = mkdtemp()

        # Most test apps run themselves twice via autoreload. The first time it manually triggers
        # a reload (could also do this by touching a file but this is faster since filesystem
        # timestamps are not necessarily high resolution). The second time it exits directly
        # so that the autoreload wrapper (if it is used) doesn't catch it.
        #
        # The last line of each such test's "main" program should be
        #     exec(open("run_twice_magic.py").read())
        self.write_files(
            {
                "run_twice_magic.py": """
                    import os
                    import sys

                    import tornado.autoreload

                    sys.stdout.flush()

                    if "TESTAPP_STARTED" not in os.environ:
                        os.environ["TESTAPP_STARTED"] = "1"
                        tornado.autoreload._reload()
                    else:
                        os._exit(0)
                """
            }
        )

    def tearDown(self):
        try:
            shutil.rmtree(self.path)
        except OSError:
            # Windows disallows deleting files that are in use by
            # another process, and even though we've waited for our
            # child process below, it appears that its lock on these
            # files is not guaranteed to be released by this point.
            # Sleep and try again (once).
            time.sleep(1)
            shutil.rmtree(self.path)

    def write_files(self, tree, base_path=None):
        """Write a directory tree to self.path.

        tree is a dictionary mapping file names to contents, or
        sub-dictionaries representing subdirectories.
        """
        if base_path is None:
            base_path = self.path
        for name, contents in tree.items():
            if isinstance(contents, dict):
                os.mkdir(os.path.join(base_path, name))
                self.write_files(contents, os.path.join(base_path, name))
            else:
                with open(os.path.join(base_path, name), "w", encoding="utf-8") as f:
                    f.write(textwrap.dedent(contents))

    def run_subprocess(self, args):
        # Make sure the tornado module under test is available to the test
        # application
        parts = [os.getcwd()]
        if "PYTHONPATH" in os.environ:
            parts += [
                os.path.join(os.getcwd(), part)
                for part in os.environ["PYTHONPATH"].split(os.pathsep)
            ]
        pythonpath = os.pathsep.join(parts)

        p = Popen(
            args,
            stdout=subprocess.PIPE,
            env=dict(os.environ, PYTHONPATH=pythonpath),
            cwd=self.path,
            universal_newlines=True,
            encoding="utf-8",
        )

        # This timeout needs to be fairly generous for pypy due to jit
        # warmup costs.
        for i in range(40):
            if p.poll() is not None:
                break
            time.sleep(0.1)
        else:
            p.kill()
            raise Exception("subprocess failed to terminate")

        out = p.communicate()[0]
        self.assertEqual(p.returncode, 0)
        return out

    def test_reload(self):
        main = """\
import sys

# In module mode, the path is set to the parent directory and we can import testapp.
try:
    import testapp
except ImportError:
    print("import testapp failed")
else:
    print("import testapp succeeded")

spec = getattr(sys.modules[__name__], '__spec__', None)
print(f"Starting {__name__=}, __spec__.name={getattr(spec, 'name', None)}")
exec(open("run_twice_magic.py", encoding="utf-8").read())
"""

        # Create temporary test application
        self.write_files(
            {
                "testapp": {
                    "__init__.py": "",
                    "__main__.py": main,
                },
            }
        )

        # The autoreload wrapper should support all the same modes as the python interpreter.
        # The wrapper itself should have no effect on this test so we try all modes with and
        # without it.
        for wrapper in [False, True]:
            with self.subTest(wrapper=wrapper):
                with self.subTest(mode="module"):
                    if wrapper:
                        base_args = [sys.executable, "-m", "tornado.autoreload"]
                    else:
                        base_args = [sys.executable]
                    # In module mode, the path is set to the parent directory and we can import
                    # testapp. Also, the __spec__.name is set to the fully qualified module name.
                    out = self.run_subprocess(base_args + ["-m", "testapp"])
                    self.assertEqual(
                        out,
                        (
                            "import testapp succeeded\n"
                            + "Starting __name__='__main__', __spec__.name=testapp.__main__\n"
                        )
                        * 2,
                    )

                with self.subTest(mode="file"):
                    out = self.run_subprocess(base_args + ["testapp/__main__.py"])
                    # In file mode, we do not expect the path to be set so we can import testapp,
                    # but when the wrapper is used the -m argument to the python interpreter
                    # does this for us.
                    expect_import = (
                        "import testapp succeeded"
                        if wrapper
                        else "import testapp failed"
                    )
                    # In file mode there is no qualified module spec.
                    self.assertEqual(
                        out,
                        f"{expect_import}\nStarting __name__='__main__', __spec__.name=None\n"
                        * 2,
                    )

                with self.subTest(mode="directory"):
                    # Running as a directory finds __main__.py like a module. It does not manipulate
                    # sys.path but it does set a spec with a name of exactly __main__.
                    out = self.run_subprocess(base_args + ["testapp"])
                    expect_import = (
                        "import testapp succeeded"
                        if wrapper
                        else "import testapp failed"
                    )
                    self.assertEqual(
                        out,
                        f"{expect_import}\nStarting __name__='__main__', __spec__.name=__main__\n"
                        * 2,
                    )

    def test_reload_wrapper_preservation(self):
        # This test verifies that when `python -m tornado.autoreload`
        # is used on an application that also has an internal
        # autoreload, the reload wrapper is preserved on restart.
        main = """\
import sys

# This import will fail if path is not set up correctly
import testapp

if 'tornado.autoreload' not in sys.modules:
    raise Exception('started without autoreload wrapper')

print('Starting')
exec(open("run_twice_magic.py", encoding="utf-8").read())
"""

        self.write_files(
            {
                "testapp": {
                    "__init__.py": "",
                    "__main__.py": main,
                },
            }
        )

        out = self.run_subprocess(
            [sys.executable, "-m", "tornado.autoreload", "-m", "testapp"]
        )
        self.assertEqual(out, "Starting\n" * 2)

    def test_reload_wrapper_args(self):
        main = """\
import os
import sys

print(os.path.basename(sys.argv[0]))
print(f'argv={sys.argv[1:]}')
exec(open("run_twice_magic.py", encoding="utf-8").read())
"""
        # Create temporary test application
        self.write_files({"main.py": main})

        # Make sure the tornado module under test is available to the test
        # application
        out = self.run_subprocess(
            [
                sys.executable,
                "-m",
                "tornado.autoreload",
                "main.py",
                "arg1",
                "--arg2",
                "-m",
                "arg3",
            ],
        )

        self.assertEqual(out, "main.py\nargv=['arg1', '--arg2', '-m', 'arg3']\n" * 2)

    def test_reload_wrapper_until_success(self):
        main = """\
import os
import sys

if "TESTAPP_STARTED" in os.environ:
    print("exiting cleanly")
    sys.exit(0)
else:
    print("reloading")
    exec(open("run_twice_magic.py", encoding="utf-8").read())
"""

        # Create temporary test application
        self.write_files({"main.py": main})

        out = self.run_subprocess(
            [sys.executable, "-m", "tornado.autoreload", "--until-success", "main.py"]
        )

        self.assertEqual(out, "reloading\nexiting cleanly\n")

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydev_sitecustomize\sitecustomize.py ===
"""
    This module will:
    - change the input() and raw_input() commands to change \r\n or \r into \n
    - execute the user site customize -- if available
    - change raw_input() and input() to also remove any trailing \r

    Up to PyDev 3.4 it also was setting the default encoding, but it was removed because of differences when
    running from a shell (i.e.: now we just set the PYTHONIOENCODING related to that -- which is properly
    treated on Py 2.7 onwards).
"""
DEBUG = 0  # 0 or 1 because of jython

import sys

encoding = None

IS_PYTHON_3_ONWARDS = 0

try:
    IS_PYTHON_3_ONWARDS = sys.version_info[0] >= 3
except:
    # That's OK, not all versions of python have sys.version_info
    if DEBUG:
        import traceback

        traceback.print_exc()  # @Reimport

# -----------------------------------------------------------------------------------------------------------------------
# Line buffering
if IS_PYTHON_3_ONWARDS:
    # Python 3 has a bug (http://bugs.python.org/issue4705) in which -u doesn't properly make output/input unbuffered
    # so, we need to enable that ourselves here.
    try:
        sys.stdout._line_buffering = True
    except:
        pass
    try:
        sys.stderr._line_buffering = True
    except:
        pass
    try:
        sys.stdin._line_buffering = True
    except:
        pass


try:
    import org.python.core.PyDictionary  # @UnresolvedImport @UnusedImport -- just to check if it could be valid

    def dict_contains(d, key):
        return d.has_key(key)
except:
    try:
        # Py3k does not have has_key anymore, and older versions don't have __contains__
        dict_contains = dict.__contains__
    except:
        try:
            dict_contains = dict.has_key
        except NameError:

            def dict_contains(d, key):
                return d.has_key(key)


def install_breakpointhook():
    def custom_sitecustomize_breakpointhook(*args, **kwargs):
        import os

        hookname = os.getenv("PYTHONBREAKPOINT")
        if (
            hookname is not None
            and len(hookname) > 0
            and hasattr(sys, "__breakpointhook__")
            and sys.__breakpointhook__ != custom_sitecustomize_breakpointhook
        ):
            sys.__breakpointhook__(*args, **kwargs)
        else:
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            import pydevd

            kwargs.setdefault("stop_at_frame", sys._getframe().f_back)
            pydevd.settrace(*args, **kwargs)

    if sys.version_info[0:2] >= (3, 7):
        # There are some choices on how to provide the breakpoint hook. Namely, we can provide a
        # PYTHONBREAKPOINT which provides the import path for a method to be executed or we
        # can override sys.breakpointhook.
        # pydevd overrides sys.breakpointhook instead of providing an environment variable because
        # it's possible that the debugger starts the user program but is not available in the
        # PYTHONPATH (and would thus fail to be imported if PYTHONBREAKPOINT was set to pydevd.settrace).
        # Note that the implementation still takes PYTHONBREAKPOINT in account (so, if it was provided
        # by someone else, it'd still work).
        sys.breakpointhook = custom_sitecustomize_breakpointhook
    else:
        if sys.version_info[0] >= 3:
            import builtins as __builtin__  # Py3
        else:
            import __builtin__

        # In older versions, breakpoint() isn't really available, so, install the hook directly
        # in the builtins.
        __builtin__.breakpoint = custom_sitecustomize_breakpointhook
        sys.__breakpointhook__ = custom_sitecustomize_breakpointhook


# Install the breakpoint hook at import time.
install_breakpointhook()

# -----------------------------------------------------------------------------------------------------------------------
# now that we've finished the needed pydev sitecustomize, let's run the default one (if available)

# Ok, some weirdness going on in Python 3k: when removing this module from the sys.module to import the 'real'
# sitecustomize, all the variables in this scope become None (as if it was garbage-collected), so, the the reference
# below is now being kept to create a cyclic reference so that it neven dies)
__pydev_sitecustomize_module__ = sys.modules.get("sitecustomize")  # A ref to this module


# remove the pydev site customize (and the pythonpath for it)
paths_removed = []
try:
    for c in sys.path[:]:
        # Pydev controls the whole classpath in Jython already, so, we don't want a a duplicate for
        # what we've already added there (this is needed to support Jython 2.5b1 onwards -- otherwise, as
        # we added the sitecustomize to the pythonpath and to the classpath, we'd have to remove it from the
        # classpath too -- and I don't think there's a way to do that... or not?)
        if (
            c.find("pydev_sitecustomize") != -1
            or c == "__classpath__"
            or c == "__pyclasspath__"
            or c == "__classpath__/"
            or c == "__pyclasspath__/"
            or c == "__classpath__\\"
            or c == "__pyclasspath__\\"
        ):
            sys.path.remove(c)
            if c.find("pydev_sitecustomize") == -1:
                # We'll re-add any paths removed but the pydev_sitecustomize we added from pydev.
                paths_removed.append(c)

    if dict_contains(sys.modules, "sitecustomize"):
        del sys.modules["sitecustomize"]  # this module
except:
    # print the error... should never happen (so, always show, and not only on debug)!
    import traceback

    traceback.print_exc()  # @Reimport
else:
    # Now, execute the default sitecustomize
    try:
        import sitecustomize  # @UnusedImport

        sitecustomize.__pydev_sitecustomize_module__ = __pydev_sitecustomize_module__
    except:
        pass

    if not dict_contains(sys.modules, "sitecustomize"):
        # If there was no sitecustomize, re-add the pydev sitecustomize (pypy gives a KeyError if it's not there)
        sys.modules["sitecustomize"] = __pydev_sitecustomize_module__

    try:
        if paths_removed:
            if sys is None:
                import sys
            if sys is not None:
                # And after executing the default sitecustomize, restore the paths (if we didn't remove it before,
                # the import sitecustomize would recurse).
                sys.path.extend(paths_removed)
    except:
        # print the error... should never happen (so, always show, and not only on debug)!
        import traceback

        traceback.print_exc()  # @Reimport


if sys.version_info[0] < 3:
    try:
        # Redefine input and raw_input only after the original sitecustomize was executed
        # (because otherwise, the original raw_input and input would still not be defined)
        import __builtin__

        original_raw_input = __builtin__.raw_input
        original_input = __builtin__.input

        def raw_input(prompt=""):
            # the original raw_input would only remove a trailing \n, so, at
            # this point if we had a \r\n the \r would remain (which is valid for eclipse)
            # so, let's remove the remaining \r which python didn't expect.
            ret = original_raw_input(prompt)

            if ret.endswith("\r"):
                return ret[:-1]

            return ret

        raw_input.__doc__ = original_raw_input.__doc__

        def input(prompt=""):
            # input must also be rebinded for using the new raw_input defined
            return eval(raw_input(prompt))

        input.__doc__ = original_input.__doc__

        __builtin__.raw_input = raw_input
        __builtin__.input = input

    except:
        # Don't report errors at this stage
        if DEBUG:
            import traceback

            traceback.print_exc()  # @Reimport

else:
    try:
        import builtins  # Python 3.0 does not have the __builtin__ module @UnresolvedImport

        original_input = builtins.input

        def input(prompt=""):
            # the original input would only remove a trailing \n, so, at
            # this point if we had a \r\n the \r would remain (which is valid for eclipse)
            # so, let's remove the remaining \r which python didn't expect.
            ret = original_input(prompt)

            if ret.endswith("\r"):
                return ret[:-1]

            return ret

        input.__doc__ = original_input.__doc__
        builtins.input = input
    except:
        # Don't report errors at this stage
        if DEBUG:
            import traceback

            traceback.print_exc()  # @Reimport


try:
    # The original getpass doesn't work from the eclipse console, so, let's put a replacement
    # here (note that it'll not go into echo mode in the console, so, what' the user writes
    # will actually be seen)
    # Note: same thing from the fix_getpass module -- but we don't want to import it in this
    # custom sitecustomize.
    def fix_get_pass():
        try:
            import getpass
        except ImportError:
            return  # If we can't import it, we can't fix it
        import warnings

        fallback = getattr(getpass, "fallback_getpass", None)  # >= 2.6
        if not fallback:
            fallback = getpass.default_getpass  # <= 2.5
        getpass.getpass = fallback
        if hasattr(getpass, "GetPassWarning"):
            warnings.simplefilter("ignore", category=getpass.GetPassWarning)

    fix_get_pass()

except:
    # Don't report errors at this stage
    if DEBUG:
        import traceback

        traceback.print_exc()  # @Reimport

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\_pydev_completer.py ===
from collections import namedtuple
from string import ascii_letters, digits

from _pydevd_bundle import pydevd_xml
import pydevconsole

import builtins as __builtin__  # Py3

try:
    import java.lang  # @UnusedImport
    from _pydev_bundle import _pydev_jy_imports_tipper

    _pydev_imports_tipper = _pydev_jy_imports_tipper
except ImportError:
    IS_JYTHON = False
    from _pydev_bundle import _pydev_imports_tipper

dir2 = _pydev_imports_tipper.generate_imports_tip_for_module


# =======================================================================================================================
# _StartsWithFilter
# =======================================================================================================================
class _StartsWithFilter:
    """
    Used because we can't create a lambda that'll use an outer scope in jython 2.1
    """

    def __init__(self, start_with):
        self.start_with = start_with.lower()

    def __call__(self, name):
        return name.lower().startswith(self.start_with)


# =======================================================================================================================
# Completer
#
# This class was gotten from IPython.completer (dir2 was replaced with the completer already in pydev)
# =======================================================================================================================
class Completer:
    def __init__(self, namespace=None, global_namespace=None):
        """Create a new completer for the command line.

        Completer([namespace,global_namespace]) -> completer instance.

        If unspecified, the default namespace where completions are performed
        is __main__ (technically, __main__.__dict__). Namespaces should be
        given as dictionaries.

        An optional second namespace can be given.  This allows the completer
        to handle cases where both the local and global scopes need to be
        distinguished.

        Completer instances should be used as the completion mechanism of
        readline via the set_completer() call:

        readline.set_completer(Completer(my_namespace).complete)
        """

        # Don't bind to namespace quite yet, but flag whether the user wants a
        # specific namespace or to use __main__.__dict__. This will allow us
        # to bind to __main__.__dict__ at completion time, not now.
        if namespace is None:
            self.use_main_ns = 1
        else:
            self.use_main_ns = 0
            self.namespace = namespace

        # The global namespace, if given, can be bound directly
        if global_namespace is None:
            self.global_namespace = {}
        else:
            self.global_namespace = global_namespace

    def complete(self, text):
        """Return the next possible completion for 'text'.

        This is called successively with state == 0, 1, 2, ... until it
        returns None.  The completion should begin with 'text'.

        """
        if self.use_main_ns:
            # In pydev this option should never be used
            raise RuntimeError("Namespace must be provided!")
            self.namespace = __main__.__dict__  # @UndefinedVariable

        if "." in text:
            return self.attr_matches(text)
        else:
            return self.global_matches(text)

    def global_matches(self, text):
        """Compute matches when text is a simple name.

        Return a list of all keywords, built-in functions and names currently
        defined in self.namespace or self.global_namespace that match.

        """

        def get_item(obj, attr):
            return obj[attr]

        a = {}

        for dict_with_comps in [__builtin__.__dict__, self.namespace, self.global_namespace]:  # @UndefinedVariable
            a.update(dict_with_comps)

        filter = _StartsWithFilter(text)

        return dir2(a, a.keys(), get_item, filter)

    def attr_matches(self, text):
        """Compute matches when text contains a dot.

        Assuming the text is of the form NAME.NAME....[NAME], and is
        evaluatable in self.namespace or self.global_namespace, it will be
        evaluated and its attributes (as revealed by dir()) are used as
        possible completions.  (For class instances, class members are are
        also considered.)

        WARNING: this can still invoke arbitrary C code, if an object
        with a __getattr__ hook is evaluated.

        """
        import re

        # Another option, seems to work great. Catches things like ''.<tab>
        m = re.match(r"(\S+(\.\w+)*)\.(\w*)$", text)  # @UndefinedVariable

        if not m:
            return []

        expr, attr = m.group(1, 3)
        try:
            obj = eval(expr, self.namespace)
        except:
            try:
                obj = eval(expr, self.global_namespace)
            except:
                return []

        filter = _StartsWithFilter(attr)

        words = dir2(obj, filter=filter)

        return words


def generate_completions(frame, act_tok):
    """
    :return list(tuple(method_name, docstring, parameters, completion_type))

    method_name: str
    docstring: str
    parameters: str -- i.e.: "(a, b)"
    completion_type is an int
        See: _pydev_bundle._pydev_imports_tipper for TYPE_ constants
    """
    if frame is None:
        return []

    # Not using frame.f_globals because of https://sourceforge.net/tracker2/?func=detail&aid=2541355&group_id=85796&atid=577329
    # (Names not resolved in generator expression in method)
    # See message: http://mail.python.org/pipermail/python-list/2009-January/526522.html
    updated_globals = {}
    updated_globals.update(frame.f_globals)
    updated_globals.update(frame.f_locals)  # locals later because it has precedence over the actual globals

    if pydevconsole.IPYTHON:
        completions = pydevconsole.get_completions(act_tok, act_tok, updated_globals, frame.f_locals)
    else:
        completer = Completer(updated_globals, None)
        # list(tuple(name, descr, parameters, type))
        completions = completer.complete(act_tok)

    return completions


def generate_completions_as_xml(frame, act_tok):
    completions = generate_completions(frame, act_tok)
    return completions_to_xml(completions)


def completions_to_xml(completions):
    valid_xml = pydevd_xml.make_valid_xml_value
    quote = pydevd_xml.quote
    msg = ["<xml>"]

    for comp in completions:
        msg.append('<comp p0="')
        msg.append(valid_xml(quote(comp[0], "/>_= \t")))
        msg.append('" p1="')
        msg.append(valid_xml(quote(comp[1], "/>_= \t")))
        msg.append('" p2="')
        msg.append(valid_xml(quote(comp[2], "/>_= \t")))
        msg.append('" p3="')
        msg.append(valid_xml(quote(comp[3], "/>_= \t")))
        msg.append('"/>')
    msg.append("</xml>")

    return "".join(msg)


identifier_start = ascii_letters + "_"
identifier_part = ascii_letters + "_" + digits

identifier_start = set(identifier_start)
identifier_part = set(identifier_part)


def isidentifier(s):
    return s.isidentifier()


TokenAndQualifier = namedtuple("TokenAndQualifier", "token, qualifier")


def extract_token_and_qualifier(text, line=0, column=0):
    """
    Extracts the token a qualifier from the text given the line/colum
    (see test_extract_token_and_qualifier for examples).

    :param unicode text:
    :param int line: 0-based
    :param int column: 0-based
    """
    # Note: not using the tokenize module because text should be unicode and
    # line/column refer to the unicode text (otherwise we'd have to know
    # those ranges after converted to bytes).
    if line < 0:
        line = 0
    if column < 0:
        column = 0

    if isinstance(text, bytes):
        text = text.decode("utf-8")

    lines = text.splitlines()
    try:
        text = lines[line]
    except IndexError:
        return TokenAndQualifier("", "")

    if column >= len(text):
        column = len(text)

    text = text[:column]
    token = ""
    qualifier = ""

    temp_token = []
    for i in range(column - 1, -1, -1):
        c = text[i]
        if c in identifier_part or isidentifier(c) or c == ".":
            temp_token.append(c)
        else:
            break
    temp_token = "".join(reversed(temp_token))
    if "." in temp_token:
        temp_token = temp_token.split(".")
        token = ".".join(temp_token[:-1])
        qualifier = temp_token[-1]
    else:
        qualifier = temp_token

    return TokenAndQualifier(token, qualifier)

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\get_supported_openai_params.py ===
from typing import Literal, Optional

import litellm
from litellm.exceptions import BadRequestError
from litellm.types.utils import LlmProviders, LlmProvidersSet


def get_supported_openai_params(  # noqa: PLR0915
    model: str,
    custom_llm_provider: Optional[str] = None,
    request_type: Literal[
        "chat_completion", "embeddings", "transcription"
    ] = "chat_completion",
) -> Optional[list]:
    """
    Returns the supported openai params for a given model + provider

    Example:
    ```
    get_supported_openai_params(model="anthropic.claude-3", custom_llm_provider="bedrock")
    ```

    Returns:
    - List if custom_llm_provider is mapped
    - None if unmapped
    """
    if not custom_llm_provider:
        try:
            custom_llm_provider = litellm.get_llm_provider(model=model)[1]
        except BadRequestError:
            return None

    if custom_llm_provider in LlmProvidersSet:
        provider_config = litellm.ProviderConfigManager.get_provider_chat_config(
            model=model, provider=LlmProviders(custom_llm_provider)
        )
    elif custom_llm_provider.split("/")[0] in LlmProvidersSet:
        provider_config = litellm.ProviderConfigManager.get_provider_chat_config(
            model=model, provider=LlmProviders(custom_llm_provider.split("/")[0])
        )
    else:
        provider_config = None

    if provider_config and request_type == "chat_completion":
        return provider_config.get_supported_openai_params(model=model)

    if custom_llm_provider == "bedrock":
        return litellm.AmazonConverseConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "meta_llama":
        provider_config = litellm.ProviderConfigManager.get_provider_chat_config(
            model=model, provider=LlmProviders.LLAMA
        )
        if provider_config:
            return provider_config.get_supported_openai_params(model=model)
    elif custom_llm_provider == "ollama":
        return litellm.OllamaConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "ollama_chat":
        return litellm.OllamaChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "anthropic":
        return litellm.AnthropicConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "anthropic_text":
        return litellm.AnthropicTextConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "fireworks_ai":
        if request_type == "embeddings":
            return litellm.FireworksAIEmbeddingConfig().get_supported_openai_params(
                model=model
            )
        elif request_type == "transcription":
            return litellm.FireworksAIAudioTranscriptionConfig().get_supported_openai_params(
                model=model
            )
        else:
            return litellm.FireworksAIConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "nvidia_nim":
        if request_type == "chat_completion":
            return litellm.nvidiaNimConfig.get_supported_openai_params(model=model)
        elif request_type == "embeddings":
            return litellm.nvidiaNimEmbeddingConfig.get_supported_openai_params()
    elif custom_llm_provider == "cerebras":
        return litellm.CerebrasConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "xai":
        return litellm.XAIChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "ai21_chat" or custom_llm_provider == "ai21":
        return litellm.AI21ChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "volcengine":
        return litellm.VolcEngineConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "groq":
        return litellm.GroqChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "hosted_vllm":
        return litellm.HostedVLLMChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "vllm":
        return litellm.VLLMConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "deepseek":
        return litellm.DeepSeekChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "cohere":
        return litellm.CohereConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "cohere_chat":
        return litellm.CohereChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "maritalk":
        return litellm.MaritalkConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "openai":
        if request_type == "transcription":
            transcription_provider_config = (
                litellm.ProviderConfigManager.get_provider_audio_transcription_config(
                    model=model, provider=LlmProviders.OPENAI
                )
            )
            if isinstance(
                transcription_provider_config, litellm.OpenAIGPTAudioTranscriptionConfig
            ):
                return transcription_provider_config.get_supported_openai_params(
                    model=model
                )
            else:
                raise ValueError(
                    f"Unsupported provider config: {transcription_provider_config} for model: {model}"
                )
        return litellm.OpenAIConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "azure":
        if litellm.AzureOpenAIO1Config().is_o_series_model(model=model):
            return litellm.AzureOpenAIO1Config().get_supported_openai_params(
                model=model
            )
        else:
            return litellm.AzureOpenAIConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "openrouter":
        return litellm.OpenrouterConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "mistral" or custom_llm_provider == "codestral":
        # mistal and codestral api have the exact same params
        if request_type == "chat_completion":
            return litellm.MistralConfig().get_supported_openai_params(model=model)
        elif request_type == "embeddings":
            return litellm.MistralEmbeddingConfig().get_supported_openai_params()
    elif custom_llm_provider == "text-completion-codestral":
        return litellm.CodestralTextCompletionConfig().get_supported_openai_params(
            model=model
        )
    elif custom_llm_provider == "sambanova":
        return litellm.SambanovaConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "nebius":
        if request_type == "chat_completion":
            return litellm.NebiusConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "replicate":
        return litellm.ReplicateConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "huggingface":
        return litellm.HuggingFaceChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "jina_ai":
        if request_type == "embeddings":
            return litellm.JinaAIEmbeddingConfig().get_supported_openai_params()
    elif custom_llm_provider == "together_ai":
        return litellm.TogetherAIConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "databricks":
        if request_type == "chat_completion":
            return litellm.DatabricksConfig().get_supported_openai_params(model=model)
        elif request_type == "embeddings":
            return litellm.DatabricksEmbeddingConfig().get_supported_openai_params()
    elif custom_llm_provider == "palm" or custom_llm_provider == "gemini":
        return litellm.GoogleAIStudioGeminiConfig().get_supported_openai_params(
            model=model
        )
    elif custom_llm_provider == "novita":
        return litellm.NovitaConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "vertex_ai" or custom_llm_provider == "vertex_ai_beta":
        if request_type == "chat_completion":
            if model.startswith("mistral"):
                return litellm.MistralConfig().get_supported_openai_params(model=model)
            elif model.startswith("codestral"):
                return (
                    litellm.CodestralTextCompletionConfig().get_supported_openai_params(
                        model=model
                    )
                )
            elif model.startswith("claude"):
                return litellm.VertexAIAnthropicConfig().get_supported_openai_params(
                    model=model
                )
            elif model.startswith("gemini"):
                return litellm.VertexGeminiConfig().get_supported_openai_params(
                    model=model
                )
            else:
                return litellm.VertexAILlama3Config().get_supported_openai_params(
                    model=model
                )
        elif request_type == "embeddings":
            return litellm.VertexAITextEmbeddingConfig().get_supported_openai_params()
    elif custom_llm_provider == "sagemaker":
        return litellm.SagemakerConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "aleph_alpha":
        return [
            "max_tokens",
            "stream",
            "top_p",
            "temperature",
            "presence_penalty",
            "frequency_penalty",
            "n",
            "stop",
        ]
    elif custom_llm_provider == "cloudflare":
        return litellm.CloudflareChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "nlp_cloud":
        return litellm.NLPCloudConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "petals":
        return litellm.PetalsConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "deepinfra":
        return litellm.DeepInfraConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "perplexity":
        return litellm.PerplexityChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "nscale":
        return litellm.NscaleConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "anyscale":
        return [
            "temperature",
            "top_p",
            "stream",
            "max_tokens",
            "stop",
            "frequency_penalty",
            "presence_penalty",
        ]
    elif custom_llm_provider == "watsonx":
        return litellm.IBMWatsonXChatConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "watsonx_text":
        return litellm.IBMWatsonXAIConfig().get_supported_openai_params(model=model)
    elif (
        custom_llm_provider == "custom_openai"
        or custom_llm_provider == "text-completion-openai"
    ):
        return litellm.OpenAITextCompletionConfig().get_supported_openai_params(
            model=model
        )
    elif custom_llm_provider == "predibase":
        return litellm.PredibaseConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "voyage":
        return litellm.VoyageEmbeddingConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "infinity":
        return litellm.InfinityEmbeddingConfig().get_supported_openai_params(
            model=model
        )
    elif custom_llm_provider == "triton":
        if request_type == "embeddings":
            return litellm.TritonEmbeddingConfig().get_supported_openai_params(
                model=model
            )
        else:
            return litellm.TritonConfig().get_supported_openai_params(model=model)
    elif custom_llm_provider == "deepgram":
        if request_type == "transcription":
            return (
                litellm.DeepgramAudioTranscriptionConfig().get_supported_openai_params(
                    model=model
                )
            )
    elif custom_llm_provider in litellm._custom_providers:
        if request_type == "chat_completion":
            provider_config = litellm.ProviderConfigManager.get_provider_chat_config(
                model=model, provider=LlmProviders.CUSTOM
            )
            if provider_config:
                return provider_config.get_supported_openai_params(model=model)
        elif request_type == "embeddings":
            return None
        elif request_type == "transcription":
            return None

    return None

# === NexusCore/openenv\Lib\site-packages\litellm\vector_stores\vector_store_registry.py ===
# litellm/proxy/vector_stores/vector_store_registry.py
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from litellm._logging import verbose_logger
from litellm.litellm_core_utils.core_helpers import remove_items_at_indices
from litellm.types.vector_stores import (
    LiteLLM_ManagedVectorStore,
    LiteLLM_ManagedVectorStoreListResponse,
    LiteLLM_VectorStoreConfig,
)

if TYPE_CHECKING:
    from litellm.proxy.utils import PrismaClient
else:
    PrismaClient = Any


class VectorStoreRegistry:
    def __init__(self, vector_stores: List[LiteLLM_ManagedVectorStore] = []):
        self.vector_stores: List[LiteLLM_ManagedVectorStore] = vector_stores
        self.vector_store_ids_to_vector_store_map: Dict[
            str, LiteLLM_ManagedVectorStore
        ] = {}

    def get_vector_store_ids_to_run(
        self, non_default_params: Dict, tools: Optional[List[Dict]] = None
    ) -> List[str]:
        """
        Returns the vector store ids to run

        vector_store_ids can be provided in two ways:
        """
        vector_store_ids: List[str] = []

        # 1. check if vector_store_ids is provided in the non_default_params
        vector_store_ids = non_default_params.get("vector_store_ids", None) or []

        # 2. check if vector_store_ids is provided as a tool in the request
        vector_store_ids = self._get_vector_store_ids_from_tool_calls(
            tools=tools, vector_store_ids=vector_store_ids
        )

        return vector_store_ids

    def pop_vector_store_ids_to_run(
        self, non_default_params: Dict, tools: Optional[List[Dict]] = None
    ) -> List[str]:
        """
        Pops the vector store ids from the non_default_params and tools
        """
        vector_store_ids: List[str] = []

        # 1. check if vector_store_ids is provided in the non_default_params
        vector_store_ids = non_default_params.pop("vector_store_ids", None) or []

        # 2. check if vector_store_ids is provided as a tool in the request
        vector_store_ids = self.get_and_pop_recognised_vector_store_tools(
            tools=tools,
            vector_store_ids=vector_store_ids,
        )

        return vector_store_ids

    def get_and_pop_recognised_vector_store_tools(
        self, tools: Optional[List[Dict]] = None, vector_store_ids: List[str] = []
    ) -> List[str]:
        """
        Returns and pops the vector store ids from the tool calls

        It only pops the recognised vector store tools from the tools list.

        Args:
            tools: The tools to pop the vector store ids from
            vector_store_ids: The list of vector store IDs the user provided

        Returns:
            The vector store ids that were popped
        """
        if tools:
            tools_to_remove: List[int] = []
            for i, tool in enumerate(tools):
                tool_vector_store_ids: List[str] = tool.get("vector_store_ids", [])
                if len(tool_vector_store_ids) == 0:
                    continue
                # remove the tool if all vector_store_ids are recognised in the registry
                recognised = all(
                    any(vs.get("vector_store_id") == vs_id for vs in self.vector_stores)
                    for vs_id in tool_vector_store_ids
                )
                if recognised:
                    tools_to_remove.append(i)
                    vector_store_ids.extend(tool_vector_store_ids)

            # remove recognised tools from the original list
            remove_items_at_indices(
                items=tools,
                indices=tools_to_remove,
            )

        return vector_store_ids

    def get_vector_store_to_run(
        self, non_default_params: Dict, tools: Optional[List[Dict]] = None
    ) -> Optional[LiteLLM_ManagedVectorStore]:
        """
        Returns the vector store to run

         vectore_stores can be run in two ways:
            1. vector_store_ids is provided in the non_default_params
            2. vector_store_ids is provided as a tool in the request


        This will return the first vector store found in the registry.
        """
        vector_store_ids = self.get_vector_store_ids_to_run(
            non_default_params=non_default_params, tools=tools
        )

        # check if the vector store ids are in the registry
        if len(vector_store_ids) <= 0:
            return None

        for vector_store_id in vector_store_ids:
            for vector_store in self.vector_stores:
                if vector_store.get("vector_store_id") == vector_store_id:
                    return vector_store
        return None

    def _get_vector_store_ids_from_tool_calls(
        self, tools: Optional[List[Dict]] = None, vector_store_ids: List[str] = []
    ) -> List[str]:
        """
        Returns the vector store ids from the tool calls
        """
        if tools:
            for tool in tools:
                if "vector_store_ids" in tool:
                    vector_store_ids.extend(tool["vector_store_ids"])
        return vector_store_ids

    def load_vector_stores_from_config(self, vector_stores_config: List[Dict]):
        """
        Loads vector stores from the litellm proxy config.yaml
        """
        for vector_store_config in vector_stores_config:
            # cast to VectorStoreConfig
            litellm_vector_store_config = LiteLLM_VectorStoreConfig(
                **vector_store_config
            )
            vector_store_name = litellm_vector_store_config.get("vector_store_name")
            vector_store_litellm_params: Dict[str, Any] = (
                litellm_vector_store_config.get("litellm_params") or {}
            )

            vector_store_id = vector_store_litellm_params.get("vector_store_id")
            if vector_store_id is None:
                raise ValueError(
                    f"vector_store_id is required for initializing vector store, got vector_store_id={vector_store_id}"
                )
            custom_llm_provider = vector_store_litellm_params.get("custom_llm_provider")
            if custom_llm_provider is None:
                raise ValueError(
                    f"custom_llm_provider is required for initializing vector store, got custom_llm_provider={custom_llm_provider}"
                )

            litellm_managed_vector_store = LiteLLM_ManagedVectorStore(
                vector_store_id=vector_store_id,
                custom_llm_provider=custom_llm_provider,
                vector_store_name=vector_store_name,
                vector_store_description=vector_store_litellm_params.get(
                    "vector_store_description"
                ),
                vector_store_metadata=vector_store_litellm_params.get(
                    "vector_store_metadata"
                ),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.vector_stores.append(litellm_managed_vector_store)

        verbose_logger.debug(
            "all loaded vector stores = %s",
            json.dumps(self.vector_stores, indent=4, default=str),
        )

    def list_all_vector_stores(self) -> LiteLLM_ManagedVectorStoreListResponse:
        """
        List all vector stores in the required format

        Returns:
            LiteLLM_ManagedVectorStoreListResponse: A standardized response with vector store data
        """
        # Prepare the response
        response = LiteLLM_ManagedVectorStoreListResponse(
            object="list",
            data=self.vector_stores,
            total_count=len(self.vector_stores),
            current_page=1,
            total_pages=1,
        )

        return response

    def add_vector_store_to_registry(self, vector_store: LiteLLM_ManagedVectorStore):
        """
        Add a vector store to the registry

        Only add the vector store if it is not already in the registry
        """
        vector_store_id = vector_store.get("vector_store_id")
        for _vector_store in self.vector_stores:
            if _vector_store.get("vector_store_id") == vector_store_id:
                return
        self.vector_stores.append(vector_store)

    def delete_vector_store_from_registry(self, vector_store_id: str):
        """
        Delete a vector store from the registry
        """
        self.vector_stores = [
            vector_store
            for vector_store in self.vector_stores
            if vector_store.get("vector_store_id") != vector_store_id
        ]

    #########################################################
    ########### DB management helpers for vector stores ###########
    #########################################################

    @staticmethod
    async def _get_vector_stores_from_db(
        prisma_client: Optional[PrismaClient],
    ) -> List[LiteLLM_ManagedVectorStore]:
        """
        Get vector stores from the database
        """
        vector_stores_from_db: List[LiteLLM_ManagedVectorStore] = []
        if prisma_client is not None:
            _vector_stores_from_db = (
                await prisma_client.db.litellm_managedvectorstorestable.find_many(
                    order={"created_at": "desc"},
                )
            )
            for vector_store in _vector_stores_from_db:
                _dict_vector_store = dict(vector_store)
                _litellm_managed_vector_store = LiteLLM_ManagedVectorStore(
                    **_dict_vector_store
                )
                vector_stores_from_db.append(_litellm_managed_vector_store)
        return vector_stores_from_db

    def get_credentials_for_vector_store(self, vector_store_id: str) -> Dict[str, Any]:
        """
        Get the credentials for a vector store

        Returns a dictionary of unpacked credentials for the vector store to use for the request
        """
        from litellm.litellm_core_utils.credential_accessor import CredentialAccessor

        for vector_store in self.vector_stores:
            if vector_store.get("vector_store_id") == vector_store_id:
                credentials = vector_store.get("litellm_credential_name")
                if credentials:
                    return CredentialAccessor.get_credential_values(credentials)
        return {}

# === NexusCore/openenv\Lib\site-packages\nltk\tbl\feature.py ===
# Natural Language Toolkit: Transformation-based learning
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Marcus Uneson <marcus.uneson@gmail.com>
#   based on previous (nltk2) version by
#   Christopher Maloof, Edward Loper, Steven Bird
# URL: <https://www.nltk.org/>
# For license information, see  LICENSE.TXT

from abc import ABCMeta, abstractmethod


class Feature(metaclass=ABCMeta):
    """
    An abstract base class for Features. A Feature is a combination of
    a specific property-computing method and a list of relative positions
    to apply that method to.

    The property-computing method, M{extract_property(tokens, index)},
    must be implemented by every subclass. It extracts or computes a specific
    property for the token at the current index. Typical extract_property()
    methods return features such as the token text or tag; but more involved
    methods may consider the entire sequence M{tokens} and
    for instance compute the length of the sentence the token belongs to.

    In addition, the subclass may have a PROPERTY_NAME, which is how
    it will be printed (in Rules and Templates, etc). If not given, defaults
    to the classname.

    """

    json_tag = "nltk.tbl.Feature"
    PROPERTY_NAME = None

    def __init__(self, positions, end=None):
        """
        Construct a Feature which may apply at C{positions}.

        >>> # For instance, importing some concrete subclasses (Feature is abstract)
        >>> from nltk.tag.brill import Word, Pos

        >>> # Feature Word, applying at one of [-2, -1]
        >>> Word([-2,-1])
        Word([-2, -1])

        >>> # Positions need not be contiguous
        >>> Word([-2,-1, 1])
        Word([-2, -1, 1])

        >>> # Contiguous ranges can alternatively be specified giving the
        >>> # two endpoints (inclusive)
        >>> Pos(-3, -1)
        Pos([-3, -2, -1])

        >>> # In two-arg form, start <= end is enforced
        >>> Pos(2, 1)
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "nltk/tbl/template.py", line 306, in __init__
            raise TypeError
        ValueError: illegal interval specification: (start=2, end=1)

        :type positions: list of int
        :param positions: the positions at which this features should apply
        :raises ValueError: illegal position specifications

        An alternative calling convention, for contiguous positions only,
        is Feature(start, end):

        :type start: int
        :param start: start of range where this feature should apply
        :type end: int
        :param end: end of range (NOTE: inclusive!) where this feature should apply
        """
        self.positions = None  # to avoid warnings
        if end is None:
            self.positions = tuple(sorted({int(i) for i in positions}))
        else:  # positions was actually not a list, but only the start index
            try:
                if positions > end:
                    raise TypeError
                self.positions = tuple(range(positions, end + 1))
            except TypeError as e:
                # let any kind of erroneous spec raise ValueError
                raise ValueError(
                    "illegal interval specification: (start={}, end={})".format(
                        positions, end
                    )
                ) from e

        # set property name given in subclass, or otherwise name of subclass
        self.PROPERTY_NAME = self.__class__.PROPERTY_NAME or self.__class__.__name__

    def encode_json_obj(self):
        return self.positions

    @classmethod
    def decode_json_obj(cls, obj):
        positions = obj
        return cls(positions)

    def __repr__(self):
        return f"{self.__class__.__name__}({list(self.positions)!r})"

    @classmethod
    def expand(cls, starts, winlens, excludezero=False):
        """
        Return a list of features, one for each start point in starts
        and for each window length in winlen. If excludezero is True,
        no Features containing 0 in its positions will be generated
        (many tbl trainers have a special representation for the
        target feature at [0])

        For instance, importing a concrete subclass (Feature is abstract)

        >>> from nltk.tag.brill import Word

        First argument gives the possible start positions, second the
        possible window lengths

        >>> Word.expand([-3,-2,-1], [1])
        [Word([-3]), Word([-2]), Word([-1])]

        >>> Word.expand([-2,-1], [1])
        [Word([-2]), Word([-1])]

        >>> Word.expand([-3,-2,-1], [1,2])
        [Word([-3]), Word([-2]), Word([-1]), Word([-3, -2]), Word([-2, -1])]

        >>> Word.expand([-2,-1], [1])
        [Word([-2]), Word([-1])]

        A third optional argument excludes all Features whose positions contain zero

        >>> Word.expand([-2,-1,0], [1,2], excludezero=False)
        [Word([-2]), Word([-1]), Word([0]), Word([-2, -1]), Word([-1, 0])]

        >>> Word.expand([-2,-1,0], [1,2], excludezero=True)
        [Word([-2]), Word([-1]), Word([-2, -1])]

        All window lengths must be positive

        >>> Word.expand([-2,-1], [0])
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "nltk/tag/tbl/template.py", line 371, in expand
            :param starts: where to start looking for Feature
        ValueError: non-positive window length in [0]

        :param starts: where to start looking for Feature
        :type starts: list of ints
        :param winlens: window lengths where to look for Feature
        :type starts: list of ints
        :param excludezero: do not output any Feature with 0 in any of its positions.
        :type excludezero: bool
        :returns: list of Features
        :raises ValueError: for non-positive window lengths
        """
        if not all(x > 0 for x in winlens):
            raise ValueError(f"non-positive window length in {winlens}")
        xs = (starts[i : i + w] for w in winlens for i in range(len(starts) - w + 1))
        return [cls(x) for x in xs if not (excludezero and 0 in x)]

    def issuperset(self, other):
        """
        Return True if this Feature always returns True when other does

        More precisely, return True if this feature refers to the same property as other;
        and this Feature looks at all positions that other does (and possibly
        other positions in addition).

        #For instance, importing a concrete subclass (Feature is abstract)
        >>> from nltk.tag.brill import Word, Pos

        >>> Word([-3,-2,-1]).issuperset(Word([-3,-2]))
        True

        >>> Word([-3,-2,-1]).issuperset(Word([-3,-2, 0]))
        False

        #Feature subclasses must agree
        >>> Word([-3,-2,-1]).issuperset(Pos([-3,-2]))
        False

        :param other: feature with which to compare
        :type other: (subclass of) Feature
        :return: True if this feature is superset, otherwise False
        :rtype: bool


        """
        return self.__class__ is other.__class__ and set(self.positions) >= set(
            other.positions
        )

    def intersects(self, other):
        """
        Return True if the positions of this Feature intersects with those of other

        More precisely, return True if this feature refers to the same property as other;
        and there is some overlap in the positions they look at.

        #For instance, importing a concrete subclass (Feature is abstract)
        >>> from nltk.tag.brill import Word, Pos

        >>> Word([-3,-2,-1]).intersects(Word([-3,-2]))
        True

        >>> Word([-3,-2,-1]).intersects(Word([-3,-2, 0]))
        True

        >>> Word([-3,-2,-1]).intersects(Word([0]))
        False

        #Feature subclasses must agree
        >>> Word([-3,-2,-1]).intersects(Pos([-3,-2]))
        False

        :param other: feature with which to compare
        :type other: (subclass of) Feature
        :return: True if feature classes agree and there is some overlap in the positions they look at
        :rtype: bool
        """

        return bool(
            self.__class__ is other.__class__
            and set(self.positions) & set(other.positions)
        )

    # Rich comparisons for Features. With @functools.total_ordering (Python 2.7+),
    # it will be enough to define __lt__ and __eq__
    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.positions == other.positions

    def __lt__(self, other):
        return (
            self.__class__.__name__ < other.__class__.__name__
            or
            #    self.positions is a sorted tuple of ints
            self.positions < other.positions
        )

    def __ne__(self, other):
        return not (self == other)

    def __gt__(self, other):
        return other < self

    def __ge__(self, other):
        return not self < other

    def __le__(self, other):
        return self < other or self == other

    @staticmethod
    @abstractmethod
    def extract_property(tokens, index):
        """
        Any subclass of Feature must define static method extract_property(tokens, index)

        :param tokens: the sequence of tokens
        :type tokens: list of tokens
        :param index: the current index
        :type index: int
        :return: feature value
        :rtype: any (but usually scalar)
        """

# === NexusCore/openenv\Lib\site-packages\PIL\ImageTk.py ===
#
# The Python Imaging Library.
# $Id$
#
# a Tk display interface
#
# History:
# 96-04-08 fl   Created
# 96-09-06 fl   Added getimage method
# 96-11-01 fl   Rewritten, removed image attribute and crop method
# 97-05-09 fl   Use PyImagingPaste method instead of image type
# 97-05-12 fl   Minor tweaks to match the IFUNC95 interface
# 97-05-17 fl   Support the "pilbitmap" booster patch
# 97-06-05 fl   Added file= and data= argument to image constructors
# 98-03-09 fl   Added width and height methods to Image classes
# 98-07-02 fl   Use default mode for "P" images without palette attribute
# 98-07-02 fl   Explicitly destroy Tkinter image objects
# 99-07-24 fl   Support multiple Tk interpreters (from Greg Couch)
# 99-07-26 fl   Automatically hook into Tkinter (if possible)
# 99-08-15 fl   Hook uses _imagingtk instead of _imaging
#
# Copyright (c) 1997-1999 by Secret Labs AB
# Copyright (c) 1996-1997 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import tkinter
from io import BytesIO
from typing import Any

from . import Image, ImageFile

TYPE_CHECKING = False
if TYPE_CHECKING:
    from ._typing import CapsuleType

# --------------------------------------------------------------------
# Check for Tkinter interface hooks


def _get_image_from_kw(kw: dict[str, Any]) -> ImageFile.ImageFile | None:
    source = None
    if "file" in kw:
        source = kw.pop("file")
    elif "data" in kw:
        source = BytesIO(kw.pop("data"))
    if not source:
        return None
    return Image.open(source)


def _pyimagingtkcall(
    command: str, photo: PhotoImage | tkinter.PhotoImage, ptr: CapsuleType
) -> None:
    tk = photo.tk
    try:
        tk.call(command, photo, repr(ptr))
    except tkinter.TclError:
        # activate Tkinter hook
        # may raise an error if it cannot attach to Tkinter
        from . import _imagingtk

        _imagingtk.tkinit(tk.interpaddr())
        tk.call(command, photo, repr(ptr))


# --------------------------------------------------------------------
# PhotoImage


class PhotoImage:
    """
    A Tkinter-compatible photo image.  This can be used
    everywhere Tkinter expects an image object.  If the image is an RGBA
    image, pixels having alpha 0 are treated as transparent.

    The constructor takes either a PIL image, or a mode and a size.
    Alternatively, you can use the ``file`` or ``data`` options to initialize
    the photo image object.

    :param image: Either a PIL image, or a mode string.  If a mode string is
                  used, a size must also be given.
    :param size: If the first argument is a mode string, this defines the size
                 of the image.
    :keyword file: A filename to load the image from (using
                   ``Image.open(file)``).
    :keyword data: An 8-bit string containing image data (as loaded from an
                   image file).
    """

    def __init__(
        self,
        image: Image.Image | str | None = None,
        size: tuple[int, int] | None = None,
        **kw: Any,
    ) -> None:
        # Tk compatibility: file or data
        if image is None:
            image = _get_image_from_kw(kw)

        if image is None:
            msg = "Image is required"
            raise ValueError(msg)
        elif isinstance(image, str):
            mode = image
            image = None

            if size is None:
                msg = "If first argument is mode, size is required"
                raise ValueError(msg)
        else:
            # got an image instead of a mode
            mode = image.mode
            if mode == "P":
                # palette mapped data
                image.apply_transparency()
                image.load()
                mode = image.palette.mode if image.palette else "RGB"
            size = image.size
            kw["width"], kw["height"] = size

        if mode not in ["1", "L", "RGB", "RGBA"]:
            mode = Image.getmodebase(mode)

        self.__mode = mode
        self.__size = size
        self.__photo = tkinter.PhotoImage(**kw)
        self.tk = self.__photo.tk
        if image:
            self.paste(image)

    def __del__(self) -> None:
        try:
            name = self.__photo.name
        except AttributeError:
            return
        self.__photo.name = None
        try:
            self.__photo.tk.call("image", "delete", name)
        except Exception:
            pass  # ignore internal errors

    def __str__(self) -> str:
        """
        Get the Tkinter photo image identifier.  This method is automatically
        called by Tkinter whenever a PhotoImage object is passed to a Tkinter
        method.

        :return: A Tkinter photo image identifier (a string).
        """
        return str(self.__photo)

    def width(self) -> int:
        """
        Get the width of the image.

        :return: The width, in pixels.
        """
        return self.__size[0]

    def height(self) -> int:
        """
        Get the height of the image.

        :return: The height, in pixels.
        """
        return self.__size[1]

    def paste(self, im: Image.Image) -> None:
        """
        Paste a PIL image into the photo image.  Note that this can
        be very slow if the photo image is displayed.

        :param im: A PIL image. The size must match the target region.  If the
                   mode does not match, the image is converted to the mode of
                   the bitmap image.
        """
        # convert to blittable
        ptr = im.getim()
        image = im.im
        if not image.isblock() or im.mode != self.__mode:
            block = Image.core.new_block(self.__mode, im.size)
            image.convert2(block, image)  # convert directly between buffers
            ptr = block.ptr

        _pyimagingtkcall("PyImagingPhoto", self.__photo, ptr)


# --------------------------------------------------------------------
# BitmapImage


class BitmapImage:
    """
    A Tkinter-compatible bitmap image.  This can be used everywhere Tkinter
    expects an image object.

    The given image must have mode "1".  Pixels having value 0 are treated as
    transparent.  Options, if any, are passed on to Tkinter.  The most commonly
    used option is ``foreground``, which is used to specify the color for the
    non-transparent parts.  See the Tkinter documentation for information on
    how to specify colours.

    :param image: A PIL image.
    """

    def __init__(self, image: Image.Image | None = None, **kw: Any) -> None:
        # Tk compatibility: file or data
        if image is None:
            image = _get_image_from_kw(kw)

        if image is None:
            msg = "Image is required"
            raise ValueError(msg)
        self.__mode = image.mode
        self.__size = image.size

        self.__photo = tkinter.BitmapImage(data=image.tobitmap(), **kw)

    def __del__(self) -> None:
        try:
            name = self.__photo.name
        except AttributeError:
            return
        self.__photo.name = None
        try:
            self.__photo.tk.call("image", "delete", name)
        except Exception:
            pass  # ignore internal errors

    def width(self) -> int:
        """
        Get the width of the image.

        :return: The width, in pixels.
        """
        return self.__size[0]

    def height(self) -> int:
        """
        Get the height of the image.

        :return: The height, in pixels.
        """
        return self.__size[1]

    def __str__(self) -> str:
        """
        Get the Tkinter bitmap image identifier.  This method is automatically
        called by Tkinter whenever a BitmapImage object is passed to a Tkinter
        method.

        :return: A Tkinter bitmap image identifier (a string).
        """
        return str(self.__photo)


def getimage(photo: PhotoImage) -> Image.Image:
    """Copies the contents of a PhotoImage to a PIL image memory."""
    im = Image.new("RGBA", (photo.width(), photo.height()))

    _pyimagingtkcall("PyImagingPhotoGet", photo, im.getim())

    return im

# === NexusCore/openenv\Lib\site-packages\starlette\applications.py ===
from __future__ import annotations

import sys
import typing
import warnings

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

from starlette.datastructures import State, URLPath
from starlette.middleware import Middleware, _MiddlewareClass
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Router
from starlette.types import ASGIApp, ExceptionHandler, Lifespan, Receive, Scope, Send
from starlette.websockets import WebSocket

AppType = typing.TypeVar("AppType", bound="Starlette")
P = ParamSpec("P")


class Starlette:
    """
    Creates an application instance.

    **Parameters:**

    * **debug** - Boolean indicating if debug tracebacks should be returned on errors.
    * **routes** - A list of routes to serve incoming HTTP and WebSocket requests.
    * **middleware** - A list of middleware to run for every request. A starlette
    application will always automatically include two middleware classes.
    `ServerErrorMiddleware` is added as the very outermost middleware, to handle
    any uncaught errors occurring anywhere in the entire stack.
    `ExceptionMiddleware` is added as the very innermost middleware, to deal
    with handled exception cases occurring in the routing or endpoints.
    * **exception_handlers** - A mapping of either integer status codes,
    or exception class types onto callables which handle the exceptions.
    Exception handler callables should be of the form
    `handler(request, exc) -> response` and may be either standard functions, or
    async functions.
    * **on_startup** - A list of callables to run on application startup.
    Startup handler callables do not take any arguments, and may be either
    standard functions, or async functions.
    * **on_shutdown** - A list of callables to run on application shutdown.
    Shutdown handler callables do not take any arguments, and may be either
    standard functions, or async functions.
    * **lifespan** - A lifespan context function, which can be used to perform
    startup and shutdown tasks. This is a newer style that replaces the
    `on_startup` and `on_shutdown` handlers. Use one or the other, not both.
    """

    def __init__(
        self: AppType,
        debug: bool = False,
        routes: typing.Sequence[BaseRoute] | None = None,
        middleware: typing.Sequence[Middleware] | None = None,
        exception_handlers: typing.Mapping[typing.Any, ExceptionHandler] | None = None,
        on_startup: typing.Sequence[typing.Callable[[], typing.Any]] | None = None,
        on_shutdown: typing.Sequence[typing.Callable[[], typing.Any]] | None = None,
        lifespan: Lifespan[AppType] | None = None,
    ) -> None:
        # The lifespan context function is a newer style that replaces
        # on_startup / on_shutdown handlers. Use one or the other, not both.
        assert lifespan is None or (
            on_startup is None and on_shutdown is None
        ), "Use either 'lifespan' or 'on_startup'/'on_shutdown', not both."

        self.debug = debug
        self.state = State()
        self.router = Router(
            routes, on_startup=on_startup, on_shutdown=on_shutdown, lifespan=lifespan
        )
        self.exception_handlers = (
            {} if exception_handlers is None else dict(exception_handlers)
        )
        self.user_middleware = [] if middleware is None else list(middleware)
        self.middleware_stack: ASGIApp | None = None

    def build_middleware_stack(self) -> ASGIApp:
        debug = self.debug
        error_handler = None
        exception_handlers: dict[
            typing.Any, typing.Callable[[Request, Exception], Response]
        ] = {}

        for key, value in self.exception_handlers.items():
            if key in (500, Exception):
                error_handler = value
            else:
                exception_handlers[key] = value

        middleware = (
            [Middleware(ServerErrorMiddleware, handler=error_handler, debug=debug)]
            + self.user_middleware
            + [
                Middleware(
                    ExceptionMiddleware, handlers=exception_handlers, debug=debug
                )
            ]
        )

        app = self.router
        for cls, args, kwargs in reversed(middleware):
            app = cls(app=app, *args, **kwargs)
        return app

    @property
    def routes(self) -> list[BaseRoute]:
        return self.router.routes

    def url_path_for(self, name: str, /, **path_params: typing.Any) -> URLPath:
        return self.router.url_path_for(name, **path_params)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        if self.middleware_stack is None:
            self.middleware_stack = self.build_middleware_stack()
        await self.middleware_stack(scope, receive, send)

    def on_event(self, event_type: str) -> typing.Callable:  # type: ignore[type-arg]
        return self.router.on_event(event_type)  # pragma: nocover

    def mount(self, path: str, app: ASGIApp, name: str | None = None) -> None:
        self.router.mount(path, app=app, name=name)  # pragma: no cover

    def host(self, host: str, app: ASGIApp, name: str | None = None) -> None:
        self.router.host(host, app=app, name=name)  # pragma: no cover

    def add_middleware(
        self,
        middleware_class: type[_MiddlewareClass[P]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        if self.middleware_stack is not None:  # pragma: no cover
            raise RuntimeError("Cannot add middleware after an application has started")
        self.user_middleware.insert(0, Middleware(middleware_class, *args, **kwargs))

    def add_exception_handler(
        self,
        exc_class_or_status_code: int | type[Exception],
        handler: ExceptionHandler,
    ) -> None:  # pragma: no cover
        self.exception_handlers[exc_class_or_status_code] = handler

    def add_event_handler(
        self,
        event_type: str,
        func: typing.Callable,  # type: ignore[type-arg]
    ) -> None:  # pragma: no cover
        self.router.add_event_handler(event_type, func)

    def add_route(
        self,
        path: str,
        route: typing.Callable[[Request], typing.Awaitable[Response] | Response],
        methods: list[str] | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> None:  # pragma: no cover
        self.router.add_route(
            path, route, methods=methods, name=name, include_in_schema=include_in_schema
        )

    def add_websocket_route(
        self,
        path: str,
        route: typing.Callable[[WebSocket], typing.Awaitable[None]],
        name: str | None = None,
    ) -> None:  # pragma: no cover
        self.router.add_websocket_route(path, route, name=name)

    def exception_handler(
        self, exc_class_or_status_code: int | type[Exception]
    ) -> typing.Callable:  # type: ignore[type-arg]
        warnings.warn(
            "The `exception_handler` decorator is deprecated, and will be removed in version 1.0.0. "  # noqa: E501
            "Refer to https://www.starlette.io/exceptions/ for the recommended approach.",  # noqa: E501
            DeprecationWarning,
        )

        def decorator(func: typing.Callable) -> typing.Callable:  # type: ignore[type-arg]  # noqa: E501
            self.add_exception_handler(exc_class_or_status_code, func)
            return func

        return decorator

    def route(
        self,
        path: str,
        methods: list[str] | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> typing.Callable:  # type: ignore[type-arg]
        """
        We no longer document this decorator style API, and its usage is discouraged.
        Instead you should use the following approach:

        >>> routes = [Route(path, endpoint=...), ...]
        >>> app = Starlette(routes=routes)
        """
        warnings.warn(
            "The `route` decorator is deprecated, and will be removed in version 1.0.0. "  # noqa: E501
            "Refer to https://www.starlette.io/routing/ for the recommended approach.",  # noqa: E501
            DeprecationWarning,
        )

        def decorator(func: typing.Callable) -> typing.Callable:  # type: ignore[type-arg]  # noqa: E501
            self.router.add_route(
                path,
                func,
                methods=methods,
                name=name,
                include_in_schema=include_in_schema,
            )
            return func

        return decorator

    def websocket_route(self, path: str, name: str | None = None) -> typing.Callable:  # type: ignore[type-arg]
        """
        We no longer document this decorator style API, and its usage is discouraged.
        Instead you should use the following approach:

        >>> routes = [WebSocketRoute(path, endpoint=...), ...]
        >>> app = Starlette(routes=routes)
        """
        warnings.warn(
            "The `websocket_route` decorator is deprecated, and will be removed in version 1.0.0. "  # noqa: E501
            "Refer to https://www.starlette.io/routing/#websocket-routing for the recommended approach.",  # noqa: E501
            DeprecationWarning,
        )

        def decorator(func: typing.Callable) -> typing.Callable:  # type: ignore[type-arg]  # noqa: E501
            self.router.add_websocket_route(path, func, name=name)
            return func

        return decorator

    def middleware(self, middleware_type: str) -> typing.Callable:  # type: ignore[type-arg]  # noqa: E501
        """
        We no longer document this decorator style API, and its usage is discouraged.
        Instead you should use the following approach:

        >>> middleware = [Middleware(...), ...]
        >>> app = Starlette(middleware=middleware)
        """
        warnings.warn(
            "The `middleware` decorator is deprecated, and will be removed in version 1.0.0. "  # noqa: E501
            "Refer to https://www.starlette.io/middleware/#using-middleware for recommended approach.",  # noqa: E501
            DeprecationWarning,
        )
        assert (
            middleware_type == "http"
        ), 'Currently only middleware("http") is supported.'

        def decorator(func: typing.Callable) -> typing.Callable:  # type: ignore[type-arg]  # noqa: E501
            self.add_middleware(BaseHTTPMiddleware, dispatch=func)
            return func

        return decorator

# === NexusCore/openenv\Lib\site-packages\trio\_path.py ===
from __future__ import annotations

import os
import pathlib
import sys
from functools import partial, update_wrapper
from inspect import cleandoc
from typing import IO, TYPE_CHECKING, Any, BinaryIO, ClassVar, TypeVar, overload

from trio._file_io import AsyncIOWrapper, wrap_file
from trio._util import final
from trio.to_thread import run_sync

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable
    from io import BufferedRandom, BufferedReader, BufferedWriter, FileIO, TextIOWrapper

    from _typeshed import (
        OpenBinaryMode,
        OpenBinaryModeReading,
        OpenBinaryModeUpdating,
        OpenBinaryModeWriting,
        OpenTextMode,
    )
    from typing_extensions import Concatenate, Literal, ParamSpec, Self

    P = ParamSpec("P")

    PathT = TypeVar("PathT", bound="Path")
    T = TypeVar("T")


def _wraps_async(  # type: ignore[explicit-any]
    wrapped: Callable[..., object],
) -> Callable[[Callable[P, T]], Callable[P, Awaitable[T]]]:
    def decorator(fn: Callable[P, T]) -> Callable[P, Awaitable[T]]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await run_sync(partial(fn, *args, **kwargs))

        update_wrapper(wrapper, wrapped)
        if wrapped.__doc__:
            wrapper.__doc__ = (
                f"Like :meth:`~{wrapped.__module__}.{wrapped.__qualname__}`, but async.\n"
                f"\n"
                f"{cleandoc(wrapped.__doc__)}\n"
            )
        return wrapper

    return decorator


def _wrap_method(
    fn: Callable[Concatenate[pathlib.Path, P], T],
) -> Callable[Concatenate[Path, P], Awaitable[T]]:
    @_wraps_async(fn)
    def wrapper(self: Path, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return fn(self._wrapped_cls(self), *args, **kwargs)

    return wrapper


def _wrap_method_path(
    fn: Callable[Concatenate[pathlib.Path, P], pathlib.Path],
) -> Callable[Concatenate[PathT, P], Awaitable[PathT]]:
    @_wraps_async(fn)
    def wrapper(self: PathT, /, *args: P.args, **kwargs: P.kwargs) -> PathT:
        return self.__class__(fn(self._wrapped_cls(self), *args, **kwargs))

    return wrapper


def _wrap_method_path_iterable(
    fn: Callable[Concatenate[pathlib.Path, P], Iterable[pathlib.Path]],
) -> Callable[Concatenate[PathT, P], Awaitable[Iterable[PathT]]]:
    @_wraps_async(fn)
    def wrapper(self: PathT, /, *args: P.args, **kwargs: P.kwargs) -> Iterable[PathT]:
        return map(self.__class__, [*fn(self._wrapped_cls(self), *args, **kwargs)])

    if wrapper.__doc__:
        wrapper.__doc__ += (
            f"\n"
            f"This is an async method that returns a synchronous iterator, so you\n"
            f"use it like:\n"
            f"\n"
            f".. code:: python\n"
            f"\n"
            f"    for subpath in await mypath.{fn.__name__}():\n"
            f"        ...\n"
            f"\n"
            f".. note::\n"
            f"\n"
            f"    The iterator is loaded into memory immediately during the initial\n"
            f"    call (see `issue #501\n"
            f"    <https://github.com/python-trio/trio/issues/501>`__ for discussion).\n"
        )
    return wrapper


class Path(pathlib.PurePath):
    """An async :class:`pathlib.Path` that executes blocking methods in :meth:`trio.to_thread.run_sync`.

    Instantiating :class:`Path` returns a concrete platform-specific subclass, one of :class:`PosixPath` or
    :class:`WindowsPath`.
    """

    __slots__ = ()

    _wrapped_cls: ClassVar[type[pathlib.Path]]

    def __new__(cls, *args: str | os.PathLike[str]) -> Self:
        if cls is Path:
            cls = WindowsPath if os.name == "nt" else PosixPath  # type: ignore[assignment]
        return super().__new__(cls, *args)

    @classmethod
    @_wraps_async(pathlib.Path.cwd)
    def cwd(cls) -> Self:
        return cls(pathlib.Path.cwd())

    @classmethod
    @_wraps_async(pathlib.Path.home)
    def home(cls) -> Self:
        return cls(pathlib.Path.home())

    @overload
    async def open(
        self,
        mode: OpenTextMode = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> AsyncIOWrapper[TextIOWrapper]: ...

    @overload
    async def open(
        self,
        mode: OpenBinaryMode,
        buffering: Literal[0],
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> AsyncIOWrapper[FileIO]: ...

    @overload
    async def open(
        self,
        mode: OpenBinaryModeUpdating,
        buffering: Literal[-1, 1] = -1,
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> AsyncIOWrapper[BufferedRandom]: ...

    @overload
    async def open(
        self,
        mode: OpenBinaryModeWriting,
        buffering: Literal[-1, 1] = -1,
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> AsyncIOWrapper[BufferedWriter]: ...

    @overload
    async def open(
        self,
        mode: OpenBinaryModeReading,
        buffering: Literal[-1, 1] = -1,
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> AsyncIOWrapper[BufferedReader]: ...

    @overload
    async def open(
        self,
        mode: OpenBinaryMode,
        buffering: int = -1,
        encoding: None = None,
        errors: None = None,
        newline: None = None,
    ) -> AsyncIOWrapper[BinaryIO]: ...

    @overload
    async def open(  # type: ignore[misc, explicit-any]  # Any usage matches builtins.open().
        self,
        mode: str,
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> AsyncIOWrapper[IO[Any]]: ...

    @_wraps_async(pathlib.Path.open)
    def open(self, *args: Any, **kwargs: Any) -> AsyncIOWrapper[IO[Any]]:  # type: ignore[misc, explicit-any]  # Overload return mismatch.
        return wrap_file(self._wrapped_cls(self).open(*args, **kwargs))

    def __repr__(self) -> str:
        return f"trio.Path({str(self)!r})"

    stat = _wrap_method(pathlib.Path.stat)
    chmod = _wrap_method(pathlib.Path.chmod)
    exists = _wrap_method(pathlib.Path.exists)
    glob = _wrap_method_path_iterable(pathlib.Path.glob)
    rglob = _wrap_method_path_iterable(pathlib.Path.rglob)
    is_dir = _wrap_method(pathlib.Path.is_dir)
    is_file = _wrap_method(pathlib.Path.is_file)
    is_symlink = _wrap_method(pathlib.Path.is_symlink)
    is_socket = _wrap_method(pathlib.Path.is_socket)
    is_fifo = _wrap_method(pathlib.Path.is_fifo)
    is_block_device = _wrap_method(pathlib.Path.is_block_device)
    is_char_device = _wrap_method(pathlib.Path.is_char_device)
    if sys.version_info >= (3, 12):
        is_junction = _wrap_method(pathlib.Path.is_junction)
    iterdir = _wrap_method_path_iterable(pathlib.Path.iterdir)
    lchmod = _wrap_method(pathlib.Path.lchmod)
    lstat = _wrap_method(pathlib.Path.lstat)
    mkdir = _wrap_method(pathlib.Path.mkdir)
    if sys.platform != "win32":
        owner = _wrap_method(pathlib.Path.owner)
        group = _wrap_method(pathlib.Path.group)
    if sys.platform != "win32" or sys.version_info >= (3, 12):
        is_mount = _wrap_method(pathlib.Path.is_mount)
    readlink = _wrap_method_path(pathlib.Path.readlink)
    rename = _wrap_method_path(pathlib.Path.rename)
    replace = _wrap_method_path(pathlib.Path.replace)
    resolve = _wrap_method_path(pathlib.Path.resolve)
    rmdir = _wrap_method(pathlib.Path.rmdir)
    symlink_to = _wrap_method(pathlib.Path.symlink_to)
    if sys.version_info >= (3, 10):
        hardlink_to = _wrap_method(pathlib.Path.hardlink_to)
    touch = _wrap_method(pathlib.Path.touch)
    unlink = _wrap_method(pathlib.Path.unlink)
    absolute = _wrap_method_path(pathlib.Path.absolute)
    expanduser = _wrap_method_path(pathlib.Path.expanduser)
    read_bytes = _wrap_method(pathlib.Path.read_bytes)
    read_text = _wrap_method(pathlib.Path.read_text)
    samefile = _wrap_method(pathlib.Path.samefile)
    write_bytes = _wrap_method(pathlib.Path.write_bytes)
    write_text = _wrap_method(pathlib.Path.write_text)
    if sys.version_info < (3, 12):
        link_to = _wrap_method(pathlib.Path.link_to)
    if sys.version_info >= (3, 13):
        full_match = _wrap_method(pathlib.Path.full_match)

    def as_uri(self) -> str:
        return pathlib.Path.as_uri(self)


@final
class PosixPath(Path, pathlib.PurePosixPath):
    """An async :class:`pathlib.PosixPath` that executes blocking methods in :meth:`trio.to_thread.run_sync`."""

    __slots__ = ()

    _wrapped_cls: ClassVar[type[pathlib.Path]] = pathlib.PosixPath


@final
class WindowsPath(Path, pathlib.PureWindowsPath):
    """An async :class:`pathlib.WindowsPath` that executes blocking methods in :meth:`trio.to_thread.run_sync`."""

    __slots__ = ()

    _wrapped_cls: ClassVar[type[pathlib.Path]] = pathlib.WindowsPath

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_runfiles\pydev_runfiles_parallel.py ===
import unittest
from _pydev_bundle._pydev_saved_modules import thread
import queue as Queue
from _pydev_runfiles import pydev_runfiles_xml_rpc
import time
import os
import threading
import sys


# =======================================================================================================================
# flatten_test_suite
# =======================================================================================================================
def flatten_test_suite(test_suite, ret):
    if isinstance(test_suite, unittest.TestSuite):
        for t in test_suite._tests:
            flatten_test_suite(t, ret)

    elif isinstance(test_suite, unittest.TestCase):
        ret.append(test_suite)


# =======================================================================================================================
# execute_tests_in_parallel
# =======================================================================================================================
def execute_tests_in_parallel(tests, jobs, split, verbosity, coverage_files, coverage_include):
    """
    @param tests: list(PydevTestSuite)
        A list with the suites to be run

    @param split: str
        Either 'module' or the number of tests that should be run in each batch

    @param coverage_files: list(file)
        A list with the files that should be used for giving coverage information (if empty, coverage information
        should not be gathered).

    @param coverage_include: str
        The pattern that should be included in the coverage.

    @return: bool
        Returns True if the tests were actually executed in parallel. If the tests were not executed because only 1
        should be used (e.g.: 2 jobs were requested for running 1 test), False will be returned and no tests will be
        run.

        It may also return False if in debug mode (in which case, multi-processes are not accepted)
    """
    try:
        from _pydevd_bundle.pydevd_comm import get_global_debugger

        if get_global_debugger() is not None:
            return False
    except:
        pass  # Ignore any error here.

    # This queue will receive the tests to be run. Each entry in a queue is a list with the tests to be run together When
    # split == 'tests', each list will have a single element, when split == 'module', each list will have all the tests
    # from a given module.
    tests_queue = []

    queue_elements = []
    if split == "module":
        module_to_tests = {}
        for test in tests:
            lst = []
            flatten_test_suite(test, lst)
            for test in lst:
                key = (test.__pydev_pyfile__, test.__pydev_module_name__)
                module_to_tests.setdefault(key, []).append(test)

        for key, tests in module_to_tests.items():
            queue_elements.append(tests)

        if len(queue_elements) < jobs:
            # Don't create jobs we will never use.
            jobs = len(queue_elements)

    elif split == "tests":
        for test in tests:
            lst = []
            flatten_test_suite(test, lst)
            for test in lst:
                queue_elements.append([test])

        if len(queue_elements) < jobs:
            # Don't create jobs we will never use.
            jobs = len(queue_elements)

    else:
        raise AssertionError("Do not know how to handle: %s" % (split,))

    for test_cases in queue_elements:
        test_queue_elements = []
        for test_case in test_cases:
            try:
                test_name = test_case.__class__.__name__ + "." + test_case._testMethodName
            except AttributeError:
                # Support for jython 2.1 (__testMethodName is pseudo-private in the test case)
                test_name = test_case.__class__.__name__ + "." + test_case._TestCase__testMethodName

            test_queue_elements.append(test_case.__pydev_pyfile__ + "|" + test_name)

        tests_queue.append(test_queue_elements)

    if jobs < 2:
        return False

    sys.stdout.write("Running tests in parallel with: %s jobs.\n" % (jobs,))

    queue = Queue.Queue()
    for item in tests_queue:
        queue.put(item, block=False)

    providers = []
    clients = []
    for i in range(jobs):
        test_cases_provider = CommunicationThread(queue)
        providers.append(test_cases_provider)

        test_cases_provider.start()
        port = test_cases_provider.port

        if coverage_files:
            clients.append(ClientThread(i, port, verbosity, coverage_files.pop(0), coverage_include))
        else:
            clients.append(ClientThread(i, port, verbosity))

    for client in clients:
        client.start()

    client_alive = True
    while client_alive:
        client_alive = False
        for client in clients:
            # Wait for all the clients to exit.
            if not client.finished:
                client_alive = True
                time.sleep(0.2)
                break

    for provider in providers:
        provider.shutdown()

    return True


# =======================================================================================================================
# CommunicationThread
# =======================================================================================================================
class CommunicationThread(threading.Thread):
    def __init__(self, tests_queue):
        threading.Thread.__init__(self)
        self.daemon = True
        self.queue = tests_queue
        self.finished = False
        from _pydev_bundle.pydev_imports import SimpleXMLRPCServer
        from _pydev_bundle import pydev_localhost

        # Create server
        server = SimpleXMLRPCServer((pydev_localhost.get_localhost(), 0), logRequests=False)
        server.register_function(self.GetTestsToRun)
        server.register_function(self.notifyStartTest)
        server.register_function(self.notifyTest)
        server.register_function(self.notifyCommands)
        self.port = server.socket.getsockname()[1]
        self.server = server

    def GetTestsToRun(self, job_id):
        """
        @param job_id:

        @return: list(str)
            Each entry is a string in the format: filename|Test.testName
        """
        try:
            ret = self.queue.get(block=False)
            return ret
        except:  # Any exception getting from the queue (empty or not) means we finished our work on providing the tests.
            self.finished = True
            return []

    def notifyCommands(self, job_id, commands):
        # Batch notification.
        for command in commands:
            getattr(self, command[0])(job_id, *command[1], **command[2])

        return True

    def notifyStartTest(self, job_id, *args, **kwargs):
        pydev_runfiles_xml_rpc.notifyStartTest(*args, **kwargs)
        return True

    def notifyTest(self, job_id, *args, **kwargs):
        pydev_runfiles_xml_rpc.notifyTest(*args, **kwargs)
        return True

    def shutdown(self):
        if hasattr(self.server, "shutdown"):
            self.server.shutdown()
        else:
            self._shutdown = True

    def run(self):
        if hasattr(self.server, "shutdown"):
            self.server.serve_forever()
        else:
            self._shutdown = False
            while not self._shutdown:
                self.server.handle_request()


# =======================================================================================================================
# Client
# =======================================================================================================================
class ClientThread(threading.Thread):
    def __init__(self, job_id, port, verbosity, coverage_output_file=None, coverage_include=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.port = port
        self.job_id = job_id
        self.verbosity = verbosity
        self.finished = False
        self.coverage_output_file = coverage_output_file
        self.coverage_include = coverage_include

    def _reader_thread(self, pipe, target):
        while True:
            target.write(pipe.read(1))

    def run(self):
        try:
            from _pydev_runfiles import pydev_runfiles_parallel_client
            # TODO: Support Jython:
            #
            # For jython, instead of using sys.executable, we should use:
            # r'D:\bin\jdk_1_5_09\bin\java.exe',
            # '-classpath',
            # 'D:/bin/jython-2.2.1/jython.jar',
            # 'org.python.util.jython',

            args = [
                sys.executable,
                pydev_runfiles_parallel_client.__file__,
                str(self.job_id),
                str(self.port),
                str(self.verbosity),
            ]

            if self.coverage_output_file and self.coverage_include:
                args.append(self.coverage_output_file)
                args.append(self.coverage_include)

            import subprocess

            if False:
                proc = subprocess.Popen(args, env=os.environ, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                thread.start_new_thread(self._reader_thread, (proc.stdout, sys.stdout))

                thread.start_new_thread(target=self._reader_thread, args=(proc.stderr, sys.stderr))
            else:
                proc = subprocess.Popen(args, env=os.environ, shell=False)
                proc.wait()

        finally:
            self.finished = True

# === NexusCore/openenv\Lib\site-packages\PIL\ImageMorph.py ===
# A binary morphology add-on for the Python Imaging Library
#
# History:
#   2014-06-04 Initial version.
#
# Copyright (c) 2014 Dov Grobgeld <dov.grobgeld@gmail.com>
from __future__ import annotations

import re

from . import Image, _imagingmorph

LUT_SIZE = 1 << 9

# fmt: off
ROTATION_MATRIX = [
    6, 3, 0,
    7, 4, 1,
    8, 5, 2,
]
MIRROR_MATRIX = [
    2, 1, 0,
    5, 4, 3,
    8, 7, 6,
]
# fmt: on


class LutBuilder:
    """A class for building a MorphLut from a descriptive language

    The input patterns is a list of a strings sequences like these::

        4:(...
           .1.
           111)->1

    (whitespaces including linebreaks are ignored). The option 4
    describes a series of symmetry operations (in this case a
    4-rotation), the pattern is described by:

    - . or X - Ignore
    - 1 - Pixel is on
    - 0 - Pixel is off

    The result of the operation is described after "->" string.

    The default is to return the current pixel value, which is
    returned if no other match is found.

    Operations:

    - 4 - 4 way rotation
    - N - Negate
    - 1 - Dummy op for no other operation (an op must always be given)
    - M - Mirroring

    Example::

        lb = LutBuilder(patterns = ["4:(... .1. 111)->1"])
        lut = lb.build_lut()

    """

    def __init__(
        self, patterns: list[str] | None = None, op_name: str | None = None
    ) -> None:
        if patterns is not None:
            self.patterns = patterns
        else:
            self.patterns = []
        self.lut: bytearray | None = None
        if op_name is not None:
            known_patterns = {
                "corner": ["1:(... ... ...)->0", "4:(00. 01. ...)->1"],
                "dilation4": ["4:(... .0. .1.)->1"],
                "dilation8": ["4:(... .0. .1.)->1", "4:(... .0. ..1)->1"],
                "erosion4": ["4:(... .1. .0.)->0"],
                "erosion8": ["4:(... .1. .0.)->0", "4:(... .1. ..0)->0"],
                "edge": [
                    "1:(... ... ...)->0",
                    "4:(.0. .1. ...)->1",
                    "4:(01. .1. ...)->1",
                ],
            }
            if op_name not in known_patterns:
                msg = f"Unknown pattern {op_name}!"
                raise Exception(msg)

            self.patterns = known_patterns[op_name]

    def add_patterns(self, patterns: list[str]) -> None:
        self.patterns += patterns

    def build_default_lut(self) -> None:
        symbols = [0, 1]
        m = 1 << 4  # pos of current pixel
        self.lut = bytearray(symbols[(i & m) > 0] for i in range(LUT_SIZE))

    def get_lut(self) -> bytearray | None:
        return self.lut

    def _string_permute(self, pattern: str, permutation: list[int]) -> str:
        """string_permute takes a pattern and a permutation and returns the
        string permuted according to the permutation list.
        """
        assert len(permutation) == 9
        return "".join(pattern[p] for p in permutation)

    def _pattern_permute(
        self, basic_pattern: str, options: str, basic_result: int
    ) -> list[tuple[str, int]]:
        """pattern_permute takes a basic pattern and its result and clones
        the pattern according to the modifications described in the $options
        parameter. It returns a list of all cloned patterns."""
        patterns = [(basic_pattern, basic_result)]

        # rotations
        if "4" in options:
            res = patterns[-1][1]
            for i in range(4):
                patterns.append(
                    (self._string_permute(patterns[-1][0], ROTATION_MATRIX), res)
                )
        # mirror
        if "M" in options:
            n = len(patterns)
            for pattern, res in patterns[:n]:
                patterns.append((self._string_permute(pattern, MIRROR_MATRIX), res))

        # negate
        if "N" in options:
            n = len(patterns)
            for pattern, res in patterns[:n]:
                # Swap 0 and 1
                pattern = pattern.replace("0", "Z").replace("1", "0").replace("Z", "1")
                res = 1 - int(res)
                patterns.append((pattern, res))

        return patterns

    def build_lut(self) -> bytearray:
        """Compile all patterns into a morphology lut.

        TBD :Build based on (file) morphlut:modify_lut
        """
        self.build_default_lut()
        assert self.lut is not None
        patterns = []

        # Parse and create symmetries of the patterns strings
        for p in self.patterns:
            m = re.search(r"(\w*):?\s*\((.+?)\)\s*->\s*(\d)", p.replace("\n", ""))
            if not m:
                msg = 'Syntax error in pattern "' + p + '"'
                raise Exception(msg)
            options = m.group(1)
            pattern = m.group(2)
            result = int(m.group(3))

            # Get rid of spaces
            pattern = pattern.replace(" ", "").replace("\n", "")

            patterns += self._pattern_permute(pattern, options, result)

        # compile the patterns into regular expressions for speed
        compiled_patterns = []
        for pattern in patterns:
            p = pattern[0].replace(".", "X").replace("X", "[01]")
            compiled_patterns.append((re.compile(p), pattern[1]))

        # Step through table and find patterns that match.
        # Note that all the patterns are searched. The last one
        # caught overrides
        for i in range(LUT_SIZE):
            # Build the bit pattern
            bitpattern = bin(i)[2:]
            bitpattern = ("0" * (9 - len(bitpattern)) + bitpattern)[::-1]

            for pattern, r in compiled_patterns:
                if pattern.match(bitpattern):
                    self.lut[i] = [0, 1][r]

        return self.lut


class MorphOp:
    """A class for binary morphological operators"""

    def __init__(
        self,
        lut: bytearray | None = None,
        op_name: str | None = None,
        patterns: list[str] | None = None,
    ) -> None:
        """Create a binary morphological operator"""
        self.lut = lut
        if op_name is not None:
            self.lut = LutBuilder(op_name=op_name).build_lut()
        elif patterns is not None:
            self.lut = LutBuilder(patterns=patterns).build_lut()

    def apply(self, image: Image.Image) -> tuple[int, Image.Image]:
        """Run a single morphological operation on an image

        Returns a tuple of the number of changed pixels and the
        morphed image"""
        if self.lut is None:
            msg = "No operator loaded"
            raise Exception(msg)

        if image.mode != "L":
            msg = "Image mode must be L"
            raise ValueError(msg)
        outimage = Image.new(image.mode, image.size, None)
        count = _imagingmorph.apply(bytes(self.lut), image.getim(), outimage.getim())
        return count, outimage

    def match(self, image: Image.Image) -> list[tuple[int, int]]:
        """Get a list of coordinates matching the morphological operation on
        an image.

        Returns a list of tuples of (x,y) coordinates
        of all matching pixels. See :ref:`coordinate-system`."""
        if self.lut is None:
            msg = "No operator loaded"
            raise Exception(msg)

        if image.mode != "L":
            msg = "Image mode must be L"
            raise ValueError(msg)
        return _imagingmorph.match(bytes(self.lut), image.getim())

    def get_on_pixels(self, image: Image.Image) -> list[tuple[int, int]]:
        """Get a list of all turned on pixels in a binary image

        Returns a list of tuples of (x,y) coordinates
        of all matching pixels. See :ref:`coordinate-system`."""

        if image.mode != "L":
            msg = "Image mode must be L"
            raise ValueError(msg)
        return _imagingmorph.get_on_pixels(image.getim())

    def load_lut(self, filename: str) -> None:
        """Load an operator from an mrl file"""
        with open(filename, "rb") as f:
            self.lut = bytearray(f.read())

        if len(self.lut) != LUT_SIZE:
            self.lut = None
            msg = "Wrong size operator file!"
            raise Exception(msg)

    def save_lut(self, filename: str) -> None:
        """Save an operator to an mrl file"""
        if self.lut is None:
            msg = "No operator loaded"
            raise Exception(msg)
        with open(filename, "wb") as f:
            f.write(self.lut)

    def set_lut(self, lut: bytearray | None) -> None:
        """Set the lut from an external source"""
        self.lut = lut

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_console.py ===
"""An helper file for the pydev debugger (REPL) console
"""
import sys
import traceback
from _pydevd_bundle.pydevconsole_code import InteractiveConsole, _EvalAwaitInNewEventLoop
from _pydev_bundle import _pydev_completer
from _pydev_bundle.pydev_console_utils import BaseInterpreterInterface, BaseStdIn
from _pydev_bundle.pydev_imports import Exec
from _pydev_bundle.pydev_override import overrides
from _pydevd_bundle import pydevd_save_locals
from _pydevd_bundle.pydevd_io import IOBuf
from pydevd_tracing import get_exception_traceback_str
from _pydevd_bundle.pydevd_xml import make_valid_xml_value
import inspect
from _pydevd_bundle.pydevd_save_locals import update_globals_and_locals

CONSOLE_OUTPUT = "output"
CONSOLE_ERROR = "error"


# =======================================================================================================================
# ConsoleMessage
# =======================================================================================================================
class ConsoleMessage:
    """Console Messages"""

    def __init__(self):
        self.more = False
        # List of tuple [('error', 'error_message'), ('message_list', 'output_message')]
        self.console_messages = []

    def add_console_message(self, message_type, message):
        """add messages in the console_messages list"""
        for m in message.split("\n"):
            if m.strip():
                self.console_messages.append((message_type, m))

    def update_more(self, more):
        """more is set to true if further input is required from the user
        else more is set to false
        """
        self.more = more

    def to_xml(self):
        """Create an XML for console message_list, error and more (true/false)
        <xml>
            <message_list>console message_list</message_list>
            <error>console error</error>
            <more>true/false</more>
        </xml>
        """
        makeValid = make_valid_xml_value

        xml = "<xml><more>%s</more>" % (self.more)

        for message_type, message in self.console_messages:
            xml += '<%s message="%s"></%s>' % (message_type, makeValid(message), message_type)

        xml += "</xml>"

        return xml


# =======================================================================================================================
# _DebugConsoleStdIn
# =======================================================================================================================
class _DebugConsoleStdIn(BaseStdIn):
    @overrides(BaseStdIn.readline)
    def readline(self, *args, **kwargs):
        sys.stderr.write("Warning: Reading from stdin is still not supported in this console.\n")
        return "\n"


# =======================================================================================================================
# DebugConsole
# =======================================================================================================================
class DebugConsole(InteractiveConsole, BaseInterpreterInterface):
    """Wrapper around code.InteractiveConsole, in order to send
    errors and outputs to the debug console
    """

    @overrides(BaseInterpreterInterface.create_std_in)
    def create_std_in(self, *args, **kwargs):
        try:
            if not self.__buffer_output:
                return sys.stdin
        except:
            pass

        return _DebugConsoleStdIn()  # If buffered, raw_input is not supported in this console.

    @overrides(InteractiveConsole.push)
    def push(self, line, frame, buffer_output=True):
        """Change built-in stdout and stderr methods by the
        new custom StdMessage.
        execute the InteractiveConsole.push.
        Change the stdout and stderr back be the original built-ins

        :param buffer_output: if False won't redirect the output.

        Return boolean (True if more input is required else False),
        output_messages and input_messages
        """
        self.__buffer_output = buffer_output
        more = False
        if buffer_output:
            original_stdout = sys.stdout
            original_stderr = sys.stderr
        try:
            try:
                self.frame = frame
                if buffer_output:
                    out = sys.stdout = IOBuf()
                    err = sys.stderr = IOBuf()
                more = self.add_exec(line)
            except Exception:
                exc = get_exception_traceback_str()
                if buffer_output:
                    err.buflist.append("Internal Error: %s" % (exc,))
                else:
                    sys.stderr.write("Internal Error: %s\n" % (exc,))
        finally:
            # Remove frame references.
            self.frame = None
            frame = None
            if buffer_output:
                sys.stdout = original_stdout
                sys.stderr = original_stderr

        if buffer_output:
            return more, out.buflist, err.buflist
        else:
            return more, [], []

    @overrides(BaseInterpreterInterface.do_add_exec)
    def do_add_exec(self, line):
        return InteractiveConsole.push(self, line)

    @overrides(InteractiveConsole.runcode)
    def runcode(self, code):
        """Execute a code object.

        When an exception occurs, self.showtraceback() is called to
        display a traceback.  All exceptions are caught except
        SystemExit, which is reraised.

        A note about KeyboardInterrupt: this exception may occur
        elsewhere in this code, and may not always be caught.  The
        caller should be prepared to deal with it.

        """
        try:
            updated_globals = self.get_namespace()
            initial_globals = updated_globals.copy()

            updated_locals = None

            is_async = False
            if hasattr(inspect, "CO_COROUTINE"):
                is_async = inspect.CO_COROUTINE & code.co_flags == inspect.CO_COROUTINE

            if is_async:
                t = _EvalAwaitInNewEventLoop(code, updated_globals, updated_locals)
                t.start()
                t.join()

                update_globals_and_locals(updated_globals, initial_globals, self.frame)
                if t.exc:
                    raise t.exc[1].with_traceback(t.exc[2])

            else:
                try:
                    exec(code, updated_globals, updated_locals)
                finally:
                    update_globals_and_locals(updated_globals, initial_globals, self.frame)
        except SystemExit:
            raise
        except:
            # In case sys.excepthook called, use original excepthook #PyDev-877: Debug console freezes with Python 3.5+
            # (showtraceback does it on python 3.5 onwards)
            sys.excepthook = sys.__excepthook__
            try:
                self.showtraceback()
            finally:
                sys.__excepthook__ = sys.excepthook

    def get_namespace(self):
        dbg_namespace = {}
        dbg_namespace.update(self.frame.f_globals)
        dbg_namespace.update(self.frame.f_locals)  # locals later because it has precedence over the actual globals
        return dbg_namespace


# =======================================================================================================================
# InteractiveConsoleCache
# =======================================================================================================================
class InteractiveConsoleCache:
    thread_id = None
    frame_id = None
    interactive_console_instance = None


# Note: On Jython 2.1 we can't use classmethod or staticmethod, so, just make the functions below free-functions.
def get_interactive_console(thread_id, frame_id, frame, console_message):
    """returns the global interactive console.
    interactive console should have been initialized by this time
    :rtype: DebugConsole
    """
    if InteractiveConsoleCache.thread_id == thread_id and InteractiveConsoleCache.frame_id == frame_id:
        return InteractiveConsoleCache.interactive_console_instance

    InteractiveConsoleCache.interactive_console_instance = DebugConsole()
    InteractiveConsoleCache.thread_id = thread_id
    InteractiveConsoleCache.frame_id = frame_id

    console_stacktrace = traceback.extract_stack(frame, limit=1)
    if console_stacktrace:
        current_context = console_stacktrace[0]  # top entry from stacktrace
        context_message = 'File "%s", line %s, in %s' % (current_context[0], current_context[1], current_context[2])
        console_message.add_console_message(CONSOLE_OUTPUT, "[Current context]: %s" % (context_message,))
    return InteractiveConsoleCache.interactive_console_instance


def clear_interactive_console():
    InteractiveConsoleCache.thread_id = None
    InteractiveConsoleCache.frame_id = None
    InteractiveConsoleCache.interactive_console_instance = None


def execute_console_command(frame, thread_id, frame_id, line, buffer_output=True):
    """fetch an interactive console instance from the cache and
    push the received command to the console.

    create and return an instance of console_message
    """
    console_message = ConsoleMessage()

    interpreter = get_interactive_console(thread_id, frame_id, frame, console_message)
    more, output_messages, error_messages = interpreter.push(line, frame, buffer_output)
    console_message.update_more(more)

    for message in output_messages:
        console_message.add_console_message(CONSOLE_OUTPUT, message)

    for message in error_messages:
        console_message.add_console_message(CONSOLE_ERROR, message)

    return console_message


def get_description(frame, thread_id, frame_id, expression):
    console_message = ConsoleMessage()
    interpreter = get_interactive_console(thread_id, frame_id, frame, console_message)
    try:
        interpreter.frame = frame
        return interpreter.getDescription(expression)
    finally:
        interpreter.frame = None


def get_completions(frame, act_tok):
    """fetch all completions, create xml for the same
    return the completions xml
    """
    return _pydev_completer.generate_completions_as_xml(frame, act_tok)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\cohere\completion\transformation.py ===
import time
from typing import TYPE_CHECKING, Any, AsyncIterator, Iterator, List, Optional, Union

import httpx

import litellm
from litellm.litellm_core_utils.prompt_templates.common_utils import (
    convert_content_list_to_str,
)
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import Choices, Message, ModelResponse, Usage

from ..common_utils import CohereError
from ..common_utils import ModelResponseIterator as CohereModelResponseIterator
from ..common_utils import validate_environment as cohere_validate_environment

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class CohereTextConfig(BaseConfig):
    """
    Reference: https://docs.cohere.com/reference/generate

    The class `CohereConfig` provides configuration for the Cohere's API interface. Below are the parameters:

    - `num_generations` (integer): Maximum number of generations returned. Default is 1, with a minimum value of 1 and a maximum value of 5.

    - `max_tokens` (integer): Maximum number of tokens the model will generate as part of the response. Default value is 20.

    - `truncate` (string): Specifies how the API handles inputs longer than maximum token length. Options include NONE, START, END. Default is END.

    - `temperature` (number): A non-negative float controlling the randomness in generation. Lower temperatures result in less random generations. Default is 0.75.

    - `preset` (string): Identifier of a custom preset, a combination of parameters such as prompt, temperature etc.

    - `end_sequences` (array of strings): The generated text gets cut at the beginning of the earliest occurrence of an end sequence, which will be excluded from the text.

    - `stop_sequences` (array of strings): The generated text gets cut at the end of the earliest occurrence of a stop sequence, which will be included in the text.

    - `k` (integer): Limits generation at each step to top `k` most likely tokens. Default is 0.

    - `p` (number): Limits generation at each step to most likely tokens with total probability mass of `p`. Default is 0.

    - `frequency_penalty` (number): Reduces repetitiveness of generated tokens. Higher values apply stronger penalties to previously occurred tokens.

    - `presence_penalty` (number): Reduces repetitiveness of generated tokens. Similar to frequency_penalty, but this penalty applies equally to all tokens that have already appeared.

    - `return_likelihoods` (string): Specifies how and if token likelihoods are returned with the response. Options include GENERATION, ALL and NONE.

    - `logit_bias` (object): Used to prevent the model from generating unwanted tokens or to incentivize it to include desired tokens. e.g. {"hello_world": 1233}
    """

    num_generations: Optional[int] = None
    max_tokens: Optional[int] = None
    truncate: Optional[str] = None
    temperature: Optional[int] = None
    preset: Optional[str] = None
    end_sequences: Optional[list] = None
    stop_sequences: Optional[list] = None
    k: Optional[int] = None
    p: Optional[int] = None
    frequency_penalty: Optional[int] = None
    presence_penalty: Optional[int] = None
    return_likelihoods: Optional[str] = None
    logit_bias: Optional[dict] = None

    def __init__(
        self,
        num_generations: Optional[int] = None,
        max_tokens: Optional[int] = None,
        truncate: Optional[str] = None,
        temperature: Optional[int] = None,
        preset: Optional[str] = None,
        end_sequences: Optional[list] = None,
        stop_sequences: Optional[list] = None,
        k: Optional[int] = None,
        p: Optional[int] = None,
        frequency_penalty: Optional[int] = None,
        presence_penalty: Optional[int] = None,
        return_likelihoods: Optional[str] = None,
        logit_bias: Optional[dict] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

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
        return cohere_validate_environment(
            headers=headers,
            model=model,
            messages=messages,
            optional_params=optional_params,
            api_key=api_key,
        )

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return CohereError(status_code=status_code, message=error_message)

    def get_supported_openai_params(self, model: str) -> List:
        return [
            "stream",
            "temperature",
            "max_tokens",
            "logit_bias",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "n",
            "extra_headers",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        for param, value in non_default_params.items():
            if param == "stream":
                optional_params["stream"] = value
            elif param == "temperature":
                optional_params["temperature"] = value
            elif param == "max_tokens":
                optional_params["max_tokens"] = value
            elif param == "n":
                optional_params["num_generations"] = value
            elif param == "logit_bias":
                optional_params["logit_bias"] = value
            elif param == "top_p":
                optional_params["p"] = value
            elif param == "frequency_penalty":
                optional_params["frequency_penalty"] = value
            elif param == "presence_penalty":
                optional_params["presence_penalty"] = value
            elif param == "stop":
                optional_params["stop_sequences"] = value
        return optional_params

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        prompt = " ".join(
            convert_content_list_to_str(message=message) for message in messages
        )

        ## Load Config
        config = litellm.CohereConfig.get_config()
        for k, v in config.items():
            if (
                k not in optional_params
            ):  # completion(top_k=3) > cohere_config(top_k=3) <- allows for dynamic variables to be passed in
                optional_params[k] = v

        ## Handle Tool Calling
        if "tools" in optional_params:
            _is_function_call = True
            tool_calling_system_prompt = self._construct_cohere_tool_for_completion_api(
                tools=optional_params["tools"]
            )
            optional_params["tools"] = tool_calling_system_prompt

        data = {
            "model": model,
            "prompt": prompt,
            **optional_params,
        }

        return data

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
        prompt = " ".join(
            convert_content_list_to_str(message=message) for message in messages
        )
        completion_response = raw_response.json()
        choices_list = []
        for idx, item in enumerate(completion_response["generations"]):
            if len(item["text"]) > 0:
                message_obj = Message(content=item["text"])
            else:
                message_obj = Message(content=None)
            choice_obj = Choices(
                finish_reason=item["finish_reason"],
                index=idx + 1,
                message=message_obj,
            )
            choices_list.append(choice_obj)
        model_response.choices = choices_list  # type: ignore

        ## CALCULATING USAGE
        prompt_tokens = len(encoding.encode(prompt))
        completion_tokens = len(
            encoding.encode(model_response["choices"][0]["message"].get("content", ""))
        )

        model_response.created = int(time.time())
        model_response.model = model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        setattr(model_response, "usage", usage)
        return model_response

    def _construct_cohere_tool_for_completion_api(
        self,
        tools: Optional[List] = None,
    ) -> dict:
        if tools is None:
            tools = []
        return {"tools": tools}

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ):
        return CohereModelResponseIterator(
            streaming_response=streaming_response,
            sync_stream=sync_stream,
            json_mode=json_mode,
        )

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\bnc.py ===
# Natural Language Toolkit: Plaintext Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Corpus reader for the XML version of the British National Corpus."""

from nltk.corpus.reader.util import concat
from nltk.corpus.reader.xmldocs import ElementTree, XMLCorpusReader, XMLCorpusView


class BNCCorpusReader(XMLCorpusReader):
    r"""Corpus reader for the XML version of the British National Corpus.

    For access to the complete XML data structure, use the ``xml()``
    method.  For access to simple word lists and tagged word lists, use
    ``words()``, ``sents()``, ``tagged_words()``, and ``tagged_sents()``.

    You can obtain the full version of the BNC corpus at
    https://www.ota.ox.ac.uk/desc/2554

    If you extracted the archive to a directory called `BNC`, then you can
    instantiate the reader as::

        BNCCorpusReader(root='BNC/Texts/', fileids=r'[A-K]/\w*/\w*\.xml')

    """

    def __init__(self, root, fileids, lazy=True):
        XMLCorpusReader.__init__(self, root, fileids)
        self._lazy = lazy

    def words(self, fileids=None, strip_space=True, stem=False):
        """
        :return: the given file(s) as a list of words
            and punctuation symbols.
        :rtype: list(str)

        :param strip_space: If true, then strip trailing spaces from
            word tokens.  Otherwise, leave the spaces on the tokens.
        :param stem: If true, then use word stems instead of word strings.
        """
        return self._views(fileids, False, None, strip_space, stem)

    def tagged_words(self, fileids=None, c5=False, strip_space=True, stem=False):
        """
        :return: the given file(s) as a list of tagged
            words and punctuation symbols, encoded as tuples
            ``(word,tag)``.
        :rtype: list(tuple(str,str))

        :param c5: If true, then the tags used will be the more detailed
            c5 tags.  Otherwise, the simplified tags will be used.
        :param strip_space: If true, then strip trailing spaces from
            word tokens.  Otherwise, leave the spaces on the tokens.
        :param stem: If true, then use word stems instead of word strings.
        """
        tag = "c5" if c5 else "pos"
        return self._views(fileids, False, tag, strip_space, stem)

    def sents(self, fileids=None, strip_space=True, stem=False):
        """
        :return: the given file(s) as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        :rtype: list(list(str))

        :param strip_space: If true, then strip trailing spaces from
            word tokens.  Otherwise, leave the spaces on the tokens.
        :param stem: If true, then use word stems instead of word strings.
        """
        return self._views(fileids, True, None, strip_space, stem)

    def tagged_sents(self, fileids=None, c5=False, strip_space=True, stem=False):
        """
        :return: the given file(s) as a list of
            sentences, each encoded as a list of ``(word,tag)`` tuples.
        :rtype: list(list(tuple(str,str)))

        :param c5: If true, then the tags used will be the more detailed
            c5 tags.  Otherwise, the simplified tags will be used.
        :param strip_space: If true, then strip trailing spaces from
            word tokens.  Otherwise, leave the spaces on the tokens.
        :param stem: If true, then use word stems instead of word strings.
        """
        tag = "c5" if c5 else "pos"
        return self._views(
            fileids, sent=True, tag=tag, strip_space=strip_space, stem=stem
        )

    def _views(self, fileids=None, sent=False, tag=False, strip_space=True, stem=False):
        """A helper function that instantiates BNCWordViews or the list of words/sentences."""
        f = BNCWordView if self._lazy else self._words
        return concat(
            [
                f(fileid, sent, tag, strip_space, stem)
                for fileid in self.abspaths(fileids)
            ]
        )

    def _words(self, fileid, bracket_sent, tag, strip_space, stem):
        """
        Helper used to implement the view methods -- returns a list of
        words or a list of sentences, optionally tagged.

        :param fileid: The name of the underlying file.
        :param bracket_sent: If true, include sentence bracketing.
        :param tag: The name of the tagset to use, or None for no tags.
        :param strip_space: If true, strip spaces from word tokens.
        :param stem: If true, then substitute stems for words.
        """
        result = []

        xmldoc = ElementTree.parse(fileid).getroot()
        for xmlsent in xmldoc.findall(".//s"):
            sent = []
            for xmlword in _all_xmlwords_in(xmlsent):
                word = xmlword.text
                if not word:
                    word = ""  # fixes issue 337?
                if strip_space or stem:
                    word = word.strip()
                if stem:
                    word = xmlword.get("hw", word)
                if tag == "c5":
                    word = (word, xmlword.get("c5"))
                elif tag == "pos":
                    word = (word, xmlword.get("pos", xmlword.get("c5")))
                sent.append(word)
            if bracket_sent:
                result.append(BNCSentence(xmlsent.attrib["n"], sent))
            else:
                result.extend(sent)

        assert None not in result
        return result


def _all_xmlwords_in(elt, result=None):
    if result is None:
        result = []
    for child in elt:
        if child.tag in ("c", "w"):
            result.append(child)
        else:
            _all_xmlwords_in(child, result)
    return result


class BNCSentence(list):
    """
    A list of words, augmented by an attribute ``num`` used to record
    the sentence identifier (the ``n`` attribute from the XML).
    """

    def __init__(self, num, items):
        self.num = num
        list.__init__(self, items)


class BNCWordView(XMLCorpusView):
    """
    A stream backed corpus view specialized for use with the BNC corpus.
    """

    tags_to_ignore = {
        "pb",
        "gap",
        "vocal",
        "event",
        "unclear",
        "shift",
        "pause",
        "align",
    }
    """These tags are ignored. For their description refer to the
    technical documentation, for example,
    http://www.natcorp.ox.ac.uk/docs/URG/ref-vocal.html

    """

    def __init__(self, fileid, sent, tag, strip_space, stem):
        """
        :param fileid: The name of the underlying file.
        :param sent: If true, include sentence bracketing.
        :param tag: The name of the tagset to use, or None for no tags.
        :param strip_space: If true, strip spaces from word tokens.
        :param stem: If true, then substitute stems for words.
        """
        if sent:
            tagspec = ".*/s"
        else:
            tagspec = ".*/s/(.*/)?(c|w)"
        self._sent = sent
        self._tag = tag
        self._strip_space = strip_space
        self._stem = stem

        self.title = None  #: Title of the document.
        self.author = None  #: Author of the document.
        self.editor = None  #: Editor
        self.resps = None  #: Statement of responsibility

        XMLCorpusView.__init__(self, fileid, tagspec)

        # Read in a tasty header.
        self._open()
        self.read_block(self._stream, ".*/teiHeader$", self.handle_header)
        self.close()

        # Reset tag context.
        self._tag_context = {0: ()}

    def handle_header(self, elt, context):
        # Set up some metadata!
        titles = elt.findall("titleStmt/title")
        if titles:
            self.title = "\n".join(title.text.strip() for title in titles)

        authors = elt.findall("titleStmt/author")
        if authors:
            self.author = "\n".join(author.text.strip() for author in authors)

        editors = elt.findall("titleStmt/editor")
        if editors:
            self.editor = "\n".join(editor.text.strip() for editor in editors)

        resps = elt.findall("titleStmt/respStmt")
        if resps:
            self.resps = "\n\n".join(
                "\n".join(resp_elt.text.strip() for resp_elt in resp) for resp in resps
            )

    def handle_elt(self, elt, context):
        if self._sent:
            return self.handle_sent(elt)
        else:
            return self.handle_word(elt)

    def handle_word(self, elt):
        word = elt.text
        if not word:
            word = ""  # fixes issue 337?
        if self._strip_space or self._stem:
            word = word.strip()
        if self._stem:
            word = elt.get("hw", word)
        if self._tag == "c5":
            word = (word, elt.get("c5"))
        elif self._tag == "pos":
            word = (word, elt.get("pos", elt.get("c5")))
        return word

    def handle_sent(self, elt):
        sent = []
        for child in elt:
            if child.tag in ("mw", "hi", "corr", "trunc"):
                sent += [self.handle_word(w) for w in child]
            elif child.tag in ("w", "c"):
                sent.append(self.handle_word(child))
            elif child.tag not in self.tags_to_ignore:
                raise ValueError("Unexpected element %s" % child.tag)
        return BNCSentence(elt.attrib["n"], sent)

# === NexusCore/openenv\Lib\site-packages\parso\grammar.py ===
import hashlib
import os
from typing import Generic, TypeVar, Union, Dict, Optional, Any
from pathlib import Path

from parso._compatibility import is_pypy
from parso.pgen2 import generate_grammar
from parso.utils import split_lines, python_bytes_to_unicode, \
    PythonVersionInfo, parse_version_string
from parso.python.diff import DiffParser
from parso.python.tokenize import tokenize_lines, tokenize
from parso.python.token import PythonTokenTypes
from parso.cache import parser_cache, load_module, try_to_save_module
from parso.parser import BaseParser
from parso.python.parser import Parser as PythonParser
from parso.python.errors import ErrorFinderConfig
from parso.python import pep8
from parso.file_io import FileIO, KnownContentFileIO
from parso.normalizer import RefactoringNormalizer, NormalizerConfig

_loaded_grammars: Dict[str, 'Grammar'] = {}

_NodeT = TypeVar("_NodeT")


class Grammar(Generic[_NodeT]):
    """
    :py:func:`parso.load_grammar` returns instances of this class.

    Creating custom none-python grammars by calling this is not supported, yet.

    :param text: A BNF representation of your grammar.
    """
    _start_nonterminal: str
    _error_normalizer_config: Optional[ErrorFinderConfig] = None
    _token_namespace: Any = None
    _default_normalizer_config: NormalizerConfig = pep8.PEP8NormalizerConfig()

    def __init__(self, text: str, *, tokenizer, parser=BaseParser, diff_parser=None):
        self._pgen_grammar = generate_grammar(
            text,
            token_namespace=self._get_token_namespace()
        )
        self._parser = parser
        self._tokenizer = tokenizer
        self._diff_parser = diff_parser
        self._hashed = hashlib.sha256(text.encode("utf-8")).hexdigest()

    def parse(self,
              code: Union[str, bytes] = None,
              *,
              error_recovery=True,
              path: Union[os.PathLike, str] = None,
              start_symbol: str = None,
              cache=False,
              diff_cache=False,
              cache_path: Union[os.PathLike, str] = None,
              file_io: FileIO = None) -> _NodeT:
        """
        If you want to parse a Python file you want to start here, most likely.

        If you need finer grained control over the parsed instance, there will be
        other ways to access it.

        :param str code: A unicode or bytes string. When it's not possible to
            decode bytes to a string, returns a
            :py:class:`UnicodeDecodeError`.
        :param bool error_recovery: If enabled, any code will be returned. If
            it is invalid, it will be returned as an error node. If disabled,
            you will get a ParseError when encountering syntax errors in your
            code.
        :param str start_symbol: The grammar rule (nonterminal) that you want
            to parse. Only allowed to be used when error_recovery is False.
        :param str path: The path to the file you want to open. Only needed for caching.
        :param bool cache: Keeps a copy of the parser tree in RAM and on disk
            if a path is given. Returns the cached trees if the corresponding
            files on disk have not changed. Note that this stores pickle files
            on your file system (e.g. for Linux in ``~/.cache/parso/``).
        :param bool diff_cache: Diffs the cached python module against the new
            code and tries to parse only the parts that have changed. Returns
            the same (changed) module that is found in cache. Using this option
            requires you to not do anything anymore with the cached modules
            under that path, because the contents of it might change. This
            option is still somewhat experimental. If you want stability,
            please don't use it.
        :param bool cache_path: If given saves the parso cache in this
            directory. If not given, defaults to the default cache places on
            each platform.

        :return: A subclass of :py:class:`parso.tree.NodeOrLeaf`. Typically a
            :py:class:`parso.python.tree.Module`.
        """
        if code is None and path is None and file_io is None:
            raise TypeError("Please provide either code or a path.")

        if isinstance(path, str):
            path = Path(path)
        if isinstance(cache_path, str):
            cache_path = Path(cache_path)

        if start_symbol is None:
            start_symbol = self._start_nonterminal

        if error_recovery and start_symbol != 'file_input':
            raise NotImplementedError("This is currently not implemented.")

        if file_io is None:
            if code is None:
                file_io = FileIO(path)  # type: ignore[arg-type]
            else:
                file_io = KnownContentFileIO(path, code)

        if cache and file_io.path is not None:
            module_node = load_module(self._hashed, file_io, cache_path=cache_path)
            if module_node is not None:
                return module_node  # type: ignore[no-any-return]

        if code is None:
            code = file_io.read()
        code = python_bytes_to_unicode(code)

        lines = split_lines(code, keepends=True)
        if diff_cache:
            if self._diff_parser is None:
                raise TypeError("You have to define a diff parser to be able "
                                "to use this option.")
            try:
                module_cache_item = parser_cache[self._hashed][file_io.path]
            except KeyError:
                pass
            else:
                module_node = module_cache_item.node
                old_lines = module_cache_item.lines
                if old_lines == lines:
                    return module_node  # type: ignore[no-any-return]

                new_node = self._diff_parser(
                    self._pgen_grammar, self._tokenizer, module_node
                ).update(
                    old_lines=old_lines,
                    new_lines=lines
                )
                try_to_save_module(self._hashed, file_io, new_node, lines,
                                   # Never pickle in pypy, it's slow as hell.
                                   pickling=cache and not is_pypy,
                                   cache_path=cache_path)
                return new_node  # type: ignore[no-any-return]

        tokens = self._tokenizer(lines)

        p = self._parser(
            self._pgen_grammar,
            error_recovery=error_recovery,
            start_nonterminal=start_symbol
        )
        root_node = p.parse(tokens=tokens)

        if cache or diff_cache:
            try_to_save_module(self._hashed, file_io, root_node, lines,
                               # Never pickle in pypy, it's slow as hell.
                               pickling=cache and not is_pypy,
                               cache_path=cache_path)
        return root_node  # type: ignore[no-any-return]

    def _get_token_namespace(self):
        ns = self._token_namespace
        if ns is None:
            raise ValueError("The token namespace should be set.")
        return ns

    def iter_errors(self, node):
        """
        Given a :py:class:`parso.tree.NodeOrLeaf` returns a generator of
        :py:class:`parso.normalizer.Issue` objects. For Python this is
        a list of syntax/indentation errors.
        """
        if self._error_normalizer_config is None:
            raise ValueError("No error normalizer specified for this grammar.")

        return self._get_normalizer_issues(node, self._error_normalizer_config)

    def refactor(self, base_node, node_to_str_map):
        return RefactoringNormalizer(node_to_str_map).walk(base_node)

    def _get_normalizer(self, normalizer_config):
        if normalizer_config is None:
            normalizer_config = self._default_normalizer_config
            if normalizer_config is None:
                raise ValueError("You need to specify a normalizer, because "
                                 "there's no default normalizer for this tree.")
        return normalizer_config.create_normalizer(self)

    def _normalize(self, node, normalizer_config=None):
        """
        TODO this is not public, yet.
        The returned code will be normalized, e.g. PEP8 for Python.
        """
        normalizer = self._get_normalizer(normalizer_config)
        return normalizer.walk(node)

    def _get_normalizer_issues(self, node, normalizer_config=None):
        normalizer = self._get_normalizer(normalizer_config)
        normalizer.walk(node)
        return normalizer.issues

    def __repr__(self):
        nonterminals = self._pgen_grammar.nonterminal_to_dfas.keys()
        txt = ' '.join(list(nonterminals)[:3]) + ' ...'
        return '<%s:%s>' % (self.__class__.__name__, txt)


class PythonGrammar(Grammar):
    _error_normalizer_config = ErrorFinderConfig()
    _token_namespace = PythonTokenTypes
    _start_nonterminal = 'file_input'

    def __init__(self, version_info: PythonVersionInfo, bnf_text: str):
        super().__init__(
            bnf_text,
            tokenizer=self._tokenize_lines,
            parser=PythonParser,
            diff_parser=DiffParser
        )
        self.version_info = version_info

    def _tokenize_lines(self, lines, **kwargs):
        return tokenize_lines(lines, version_info=self.version_info, **kwargs)

    def _tokenize(self, code):
        # Used by Jedi.
        return tokenize(code, version_info=self.version_info)


def load_grammar(*, version: str = None, path: str = None):
    """
    Loads a :py:class:`parso.Grammar`. The default version is the current Python
    version.

    :param str version: A python version string, e.g. ``version='3.8'``.
    :param str path: A path to a grammar file
    """
    version_info = parse_version_string(version)

    file = path or os.path.join(
        'python',
        'grammar%s%s.txt' % (version_info.major, version_info.minor)
    )

    global _loaded_grammars
    path = os.path.join(os.path.dirname(__file__), file)
    try:
        return _loaded_grammars[path]
    except KeyError:
        try:
            with open(path) as f:
                bnf_text = f.read()

            grammar = PythonGrammar(version_info, bnf_text)
            return _loaded_grammars.setdefault(path, grammar)
        except FileNotFoundError:
            message = "Python version %s.%s is currently not supported." % (
                version_info.major, version_info.minor
            )
            raise NotImplementedError(message)

# === NexusCore/openenv\Lib\site-packages\PIL\TgaImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# TGA file handling
#
# History:
# 95-09-01 fl   created (reads 24-bit files only)
# 97-01-04 fl   support more TGA versions, including compressed images
# 98-07-04 fl   fixed orientation and alpha layer bugs
# 98-09-11 fl   fixed orientation for runlength decoder
#
# Copyright (c) Secret Labs AB 1997-98.
# Copyright (c) Fredrik Lundh 1995-97.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import warnings
from typing import IO

from . import Image, ImageFile, ImagePalette
from ._binary import i16le as i16
from ._binary import o8
from ._binary import o16le as o16

#
# --------------------------------------------------------------------
# Read RGA file


MODES = {
    # map imagetype/depth to rawmode
    (1, 8): "P",
    (3, 1): "1",
    (3, 8): "L",
    (3, 16): "LA",
    (2, 16): "BGRA;15Z",
    (2, 24): "BGR",
    (2, 32): "BGRA",
}


##
# Image plugin for Targa files.


class TgaImageFile(ImageFile.ImageFile):
    format = "TGA"
    format_description = "Targa"

    def _open(self) -> None:
        # process header
        assert self.fp is not None

        s = self.fp.read(18)

        id_len = s[0]

        colormaptype = s[1]
        imagetype = s[2]

        depth = s[16]

        flags = s[17]

        self._size = i16(s, 12), i16(s, 14)

        # validate header fields
        if (
            colormaptype not in (0, 1)
            or self.size[0] <= 0
            or self.size[1] <= 0
            or depth not in (1, 8, 16, 24, 32)
        ):
            msg = "not a TGA file"
            raise SyntaxError(msg)

        # image mode
        if imagetype in (3, 11):
            self._mode = "L"
            if depth == 1:
                self._mode = "1"  # ???
            elif depth == 16:
                self._mode = "LA"
        elif imagetype in (1, 9):
            self._mode = "P" if colormaptype else "L"
        elif imagetype in (2, 10):
            self._mode = "RGB" if depth == 24 else "RGBA"
        else:
            msg = "unknown TGA mode"
            raise SyntaxError(msg)

        # orientation
        orientation = flags & 0x30
        self._flip_horizontally = orientation in [0x10, 0x30]
        if orientation in [0x20, 0x30]:
            orientation = 1
        elif orientation in [0, 0x10]:
            orientation = -1
        else:
            msg = "unknown TGA orientation"
            raise SyntaxError(msg)

        self.info["orientation"] = orientation

        if imagetype & 8:
            self.info["compression"] = "tga_rle"

        if id_len:
            self.info["id_section"] = self.fp.read(id_len)

        if colormaptype:
            # read palette
            start, size, mapdepth = i16(s, 3), i16(s, 5), s[7]
            if mapdepth == 16:
                self.palette = ImagePalette.raw(
                    "BGRA;15Z", bytes(2 * start) + self.fp.read(2 * size)
                )
                self.palette.mode = "RGBA"
            elif mapdepth == 24:
                self.palette = ImagePalette.raw(
                    "BGR", bytes(3 * start) + self.fp.read(3 * size)
                )
            elif mapdepth == 32:
                self.palette = ImagePalette.raw(
                    "BGRA", bytes(4 * start) + self.fp.read(4 * size)
                )
            else:
                msg = "unknown TGA map depth"
                raise SyntaxError(msg)

        # setup tile descriptor
        try:
            rawmode = MODES[(imagetype & 7, depth)]
            if imagetype & 8:
                # compressed
                self.tile = [
                    ImageFile._Tile(
                        "tga_rle",
                        (0, 0) + self.size,
                        self.fp.tell(),
                        (rawmode, orientation, depth),
                    )
                ]
            else:
                self.tile = [
                    ImageFile._Tile(
                        "raw",
                        (0, 0) + self.size,
                        self.fp.tell(),
                        (rawmode, 0, orientation),
                    )
                ]
        except KeyError:
            pass  # cannot decode

    def load_end(self) -> None:
        if self._flip_horizontally:
            self.im = self.im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)


#
# --------------------------------------------------------------------
# Write TGA file


SAVE = {
    "1": ("1", 1, 0, 3),
    "L": ("L", 8, 0, 3),
    "LA": ("LA", 16, 0, 3),
    "P": ("P", 8, 1, 1),
    "RGB": ("BGR", 24, 0, 2),
    "RGBA": ("BGRA", 32, 0, 2),
}


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    try:
        rawmode, bits, colormaptype, imagetype = SAVE[im.mode]
    except KeyError as e:
        msg = f"cannot write mode {im.mode} as TGA"
        raise OSError(msg) from e

    if "rle" in im.encoderinfo:
        rle = im.encoderinfo["rle"]
    else:
        compression = im.encoderinfo.get("compression", im.info.get("compression"))
        rle = compression == "tga_rle"
    if rle:
        imagetype += 8

    id_section = im.encoderinfo.get("id_section", im.info.get("id_section", ""))
    id_len = len(id_section)
    if id_len > 255:
        id_len = 255
        id_section = id_section[:255]
        warnings.warn("id_section has been trimmed to 255 characters")

    if colormaptype:
        palette = im.im.getpalette("RGB", "BGR")
        colormaplength, colormapentry = len(palette) // 3, 24
    else:
        colormaplength, colormapentry = 0, 0

    if im.mode in ("LA", "RGBA"):
        flags = 8
    else:
        flags = 0

    orientation = im.encoderinfo.get("orientation", im.info.get("orientation", -1))
    if orientation > 0:
        flags = flags | 0x20

    fp.write(
        o8(id_len)
        + o8(colormaptype)
        + o8(imagetype)
        + o16(0)  # colormapfirst
        + o16(colormaplength)
        + o8(colormapentry)
        + o16(0)
        + o16(0)
        + o16(im.size[0])
        + o16(im.size[1])
        + o8(bits)
        + o8(flags)
    )

    if id_section:
        fp.write(id_section)

    if colormaptype:
        fp.write(palette)

    if rle:
        ImageFile._save(
            im,
            fp,
            [ImageFile._Tile("tga_rle", (0, 0) + im.size, 0, (rawmode, orientation))],
        )
    else:
        ImageFile._save(
            im,
            fp,
            [ImageFile._Tile("raw", (0, 0) + im.size, 0, (rawmode, 0, orientation))],
        )

    # write targa version 2 footer
    fp.write(b"\000" * 8 + b"TRUEVISION-XFILE." + b"\000")


#
# --------------------------------------------------------------------
# Registry


Image.register_open(TgaImageFile.format, TgaImageFile)
Image.register_save(TgaImageFile.format, _save)

Image.register_extensions(TgaImageFile.format, [".tga", ".icb", ".vda", ".vst"])

Image.register_mime(TgaImageFile.format, "image/x-tga")

# === NexusCore/openenv\Lib\site-packages\google\api_core\retry\retry_streaming.py ===
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

"""
Generator wrapper for retryable streaming RPCs.
"""
from __future__ import annotations

from typing import (
    Callable,
    Optional,
    List,
    Tuple,
    Iterable,
    Generator,
    TypeVar,
    Any,
    TYPE_CHECKING,
)

import sys
import time
import functools

from google.api_core.retry.retry_base import _BaseRetry
from google.api_core.retry.retry_base import _retry_error_helper
from google.api_core.retry import exponential_sleep_generator
from google.api_core.retry import build_retry_error
from google.api_core.retry import RetryFailureReason

if TYPE_CHECKING:
    if sys.version_info >= (3, 10):
        from typing import ParamSpec
    else:
        from typing_extensions import ParamSpec

    _P = ParamSpec("_P")  # target function call parameters
    _Y = TypeVar("_Y")  # yielded values


def retry_target_stream(
    target: Callable[_P, Iterable[_Y]],
    predicate: Callable[[Exception], bool],
    sleep_generator: Iterable[float],
    timeout: Optional[float] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
    exception_factory: Callable[
        [List[Exception], RetryFailureReason, Optional[float]],
        Tuple[Exception, Optional[Exception]],
    ] = build_retry_error,
    init_args: tuple = (),
    init_kwargs: dict = {},
    **kwargs,
) -> Generator[_Y, Any, None]:
    """Create a generator wrapper that retries the wrapped stream if it fails.

    This is the lowest-level retry helper. Generally, you'll use the
    higher-level retry helper :class:`Retry`.

    Args:
        target: The generator function to call and retry.
        predicate: A callable used to determine if an
            exception raised by the target should be considered retryable.
            It should return True to retry or False otherwise.
        sleep_generator: An infinite iterator that determines
            how long to sleep between retries.
        timeout: How long to keep retrying the target.
            Note: timeout is only checked before initiating a retry, so the target may
            run past the timeout value as long as it is healthy.
        on_error: If given, the on_error callback will be called with each
            retryable exception raised by the target. Any error raised by this
            function will *not* be caught.
        exception_factory: A function that is called when the retryable reaches
            a terminal failure state, used to construct an exception to be raised.
            It takes a list of all exceptions encountered, a retry.RetryFailureReason
            enum indicating the failure cause, and the original timeout value
            as arguments. It should return a tuple of the exception to be raised,
            along with the cause exception if any. The default implementation will raise
            a RetryError on timeout, or the last exception encountered otherwise.
        init_args: Positional arguments to pass to the target function.
        init_kwargs: Keyword arguments to pass to the target function.

    Returns:
        Generator: A retryable generator that wraps the target generator function.

    Raises:
        ValueError: If the sleep generator stops yielding values.
        Exception: a custom exception specified by the exception_factory if provided.
            If no exception_factory is provided:
                google.api_core.RetryError: If the timeout is exceeded while retrying.
                Exception: If the target raises an error that isn't retryable.
    """

    timeout = kwargs.get("deadline", timeout)
    deadline: Optional[float] = (
        time.monotonic() + timeout if timeout is not None else None
    )
    error_list: list[Exception] = []
    sleep_iter = iter(sleep_generator)

    # continue trying until an attempt completes, or a terminal exception is raised in _retry_error_helper
    # TODO: support max_attempts argument: https://github.com/googleapis/python-api-core/issues/535
    while True:
        # Start a new retry loop
        try:
            # Note: in the future, we can add a ResumptionStrategy object
            # to generate new args between calls. For now, use the same args
            # for each attempt.
            subgenerator = target(*init_args, **init_kwargs)
            return (yield from subgenerator)
        # handle exceptions raised by the subgenerator
        # pylint: disable=broad-except
        # This function explicitly must deal with broad exceptions.
        except Exception as exc:
            # defer to shared logic for handling errors
            next_sleep = _retry_error_helper(
                exc,
                deadline,
                sleep_iter,
                error_list,
                predicate,
                on_error,
                exception_factory,
                timeout,
            )
            # if exception not raised, sleep before next attempt
            time.sleep(next_sleep)


class StreamingRetry(_BaseRetry):
    """Exponential retry decorator for streaming synchronous RPCs.

    This class returns a Generator when called, which wraps the target
    stream in retry logic. If any exception is raised by the target, the
    entire stream will be retried within the wrapper.

    Although the default behavior is to retry transient API errors, a
    different predicate can be provided to retry other exceptions.

    Important Note: when a stream encounters a retryable error, it will
    silently construct a fresh iterator instance in the background
    and continue yielding (likely duplicate) values as if no error occurred.
    This is the most general way to retry a stream, but it often is not the
    desired behavior. Example: iter([1, 2, 1/0]) -> [1, 2, 1, 2, ...]

    There are two ways to build more advanced retry logic for streams:

    1. Wrap the target
        Use a ``target`` that maintains state between retries, and creates a
        different generator on each retry call. For example, you can wrap a
        network call in a function that modifies the request based on what has
        already been returned:

        .. code-block:: python

            def attempt_with_modified_request(target, request, seen_items=[]):
                # remove seen items from request on each attempt
                new_request = modify_request(request, seen_items)
                new_generator = target(new_request)
                for item in new_generator:
                    yield item
                    seen_items.append(item)

            retry_wrapped_fn = StreamingRetry()(attempt_with_modified_request)
            retryable_generator = retry_wrapped_fn(target, request)

    2. Wrap the retry generator
        Alternatively, you can wrap the retryable generator itself before
        passing it to the end-user to add a filter on the stream. For
        example, you can keep track of the items that were successfully yielded
        in previous retry attempts, and only yield new items when the
        new attempt surpasses the previous ones:

        .. code-block:: python

            def retryable_with_filter(target):
                stream_idx = 0
                # reset stream_idx when the stream is retried
                def on_error(e):
                    nonlocal stream_idx
                    stream_idx = 0
                # build retryable
                retryable_gen = StreamingRetry(...)(target)
                # keep track of what has been yielded out of filter
                seen_items = []
                for item in retryable_gen():
                    if stream_idx >= len(seen_items):
                        seen_items.append(item)
                        yield item
                    elif item != seen_items[stream_idx]:
                        raise ValueError("Stream differs from last attempt")
                    stream_idx += 1

            filter_retry_wrapped = retryable_with_filter(target)

    Args:
        predicate (Callable[Exception]): A callable that should return ``True``
            if the given exception is retryable.
        initial (float): The minimum amount of time to delay in seconds. This
            must be greater than 0.
        maximum (float): The maximum amount of time to delay in seconds.
        multiplier (float): The multiplier applied to the delay.
        timeout (float): How long to keep retrying, in seconds.
            Note: timeout is only checked before initiating a retry, so the target may
            run past the timeout value as long as it is healthy.
        on_error (Callable[Exception]): A function to call while processing
            a retryable exception. Any error raised by this function will
            *not* be caught.
        deadline (float): DEPRECATED: use `timeout` instead. For backward
            compatibility, if specified it will override the ``timeout`` parameter.
    """

    def __call__(
        self,
        func: Callable[_P, Iterable[_Y]],
        on_error: Callable[[Exception], Any] | None = None,
    ) -> Callable[_P, Generator[_Y, Any, None]]:
        """Wrap a callable with retry behavior.

        Args:
            func (Callable): The callable to add retry behavior to.
            on_error (Optional[Callable[Exception]]): If given, the
                on_error callback will be called with each retryable exception
                raised by the wrapped function. Any error raised by this
                function will *not* be caught. If on_error was specified in the
                constructor, this value will be ignored.

        Returns:
            Callable: A callable that will invoke ``func`` with retry
                behavior.
        """
        if self._on_error is not None:
            on_error = self._on_error

        @functools.wraps(func)
        def retry_wrapped_func(
            *args: _P.args, **kwargs: _P.kwargs
        ) -> Generator[_Y, Any, None]:
            """A wrapper that calls target function with retry."""
            sleep_generator = exponential_sleep_generator(
                self._initial, self._maximum, multiplier=self._multiplier
            )
            return retry_target_stream(
                func,
                predicate=self._predicate,
                sleep_generator=sleep_generator,
                timeout=self._timeout,
                on_error=on_error,
                init_args=args,
                init_kwargs=kwargs,
            )

        return retry_wrapped_func

# === NexusCore/openenv\Lib\site-packages\jedi\api\refactoring\__init__.py ===
import difflib
from pathlib import Path
from typing import Dict, Iterable, Tuple

from parso import split_lines

from jedi.api.exceptions import RefactoringError
from jedi.inference.value.namespace import ImplicitNSName

EXPRESSION_PARTS = (
    'or_test and_test not_test comparison '
    'expr xor_expr and_expr shift_expr arith_expr term factor power atom_expr'
).split()


class ChangedFile:
    def __init__(self, inference_state, from_path, to_path,
                 module_node, node_to_str_map):
        self._inference_state = inference_state
        self._from_path = from_path
        self._to_path = to_path
        self._module_node = module_node
        self._node_to_str_map = node_to_str_map

    def get_diff(self):
        old_lines = split_lines(self._module_node.get_code(), keepends=True)
        new_lines = split_lines(self.get_new_code(), keepends=True)

        # Add a newline at the end if it's missing. Otherwise the diff will be
        # very weird. A `diff -u file1 file2` would show the string:
        #
        #     \ No newline at end of file
        #
        # This is not necessary IMO, because Jedi does not really play with
        # newlines and the ending newline does not really matter in Python
        # files. ~dave
        if old_lines[-1] != '':
            old_lines[-1] += '\n'
        if new_lines[-1] != '':
            new_lines[-1] += '\n'

        project_path = self._inference_state.project.path
        if self._from_path is None:
            from_p = ''
        else:
            try:
                from_p = self._from_path.relative_to(project_path)
            except ValueError:  # Happens it the path is not on th project_path
                from_p = self._from_path
        if self._to_path is None:
            to_p = ''
        else:
            try:
                to_p = self._to_path.relative_to(project_path)
            except ValueError:
                to_p = self._to_path
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=str(from_p),
            tofile=str(to_p),
        )
        # Apparently there's a space at the end of the diff - for whatever
        # reason.
        return ''.join(diff).rstrip(' ')

    def get_new_code(self):
        return self._inference_state.grammar.refactor(self._module_node, self._node_to_str_map)

    def apply(self):
        if self._from_path is None:
            raise RefactoringError(
                'Cannot apply a refactoring on a Script with path=None'
            )

        with open(self._from_path, 'w', newline='') as f:
            f.write(self.get_new_code())

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self._from_path)


class Refactoring:
    def __init__(self, inference_state, file_to_node_changes, renames=()):
        self._inference_state = inference_state
        self._renames = renames
        self._file_to_node_changes = file_to_node_changes

    def get_changed_files(self) -> Dict[Path, ChangedFile]:
        def calculate_to_path(p):
            if p is None:
                return p
            p = str(p)
            for from_, to in renames:
                if p.startswith(str(from_)):
                    p = str(to) + p[len(str(from_)):]
            return Path(p)

        renames = self.get_renames()
        return {
            path: ChangedFile(
                self._inference_state,
                from_path=path,
                to_path=calculate_to_path(path),
                module_node=next(iter(map_)).get_root_node(),
                node_to_str_map=map_
            )
            # We need to use `or`, because the path can be None
            for path, map_ in sorted(
                self._file_to_node_changes.items(),
                key=lambda x: x[0] or Path("")
            )
        }

    def get_renames(self) -> Iterable[Tuple[Path, Path]]:
        """
        Files can be renamed in a refactoring.
        """
        return sorted(self._renames)

    def get_diff(self):
        text = ''
        project_path = self._inference_state.project.path
        for from_, to in self.get_renames():
            text += 'rename from %s\nrename to %s\n' \
                % (_try_relative_to(from_, project_path), _try_relative_to(to, project_path))

        return text + ''.join(f.get_diff() for f in self.get_changed_files().values())

    def apply(self):
        """
        Applies the whole refactoring to the files, which includes renames.
        """
        for f in self.get_changed_files().values():
            f.apply()

        for old, new in self.get_renames():
            old.rename(new)


def _calculate_rename(path, new_name):
    dir_ = path.parent
    if path.name in ('__init__.py', '__init__.pyi'):
        return dir_, dir_.parent.joinpath(new_name)
    return path, dir_.joinpath(new_name + path.suffix)


def rename(inference_state, definitions, new_name):
    file_renames = set()
    file_tree_name_map = {}

    if not definitions:
        raise RefactoringError("There is no name under the cursor")

    for d in definitions:
        # This private access is ok in a way. It's not public to
        # protect Jedi users from seeing it.
        tree_name = d._name.tree_name
        if d.type == 'module' and tree_name is None and d.module_path is not None:
            p = Path(d.module_path)
            file_renames.add(_calculate_rename(p, new_name))
        elif isinstance(d._name, ImplicitNSName):
            for p in d._name._value.py__path__():
                file_renames.add(_calculate_rename(Path(p), new_name))
        else:
            if tree_name is not None:
                fmap = file_tree_name_map.setdefault(d.module_path, {})
                fmap[tree_name] = tree_name.prefix + new_name
    return Refactoring(inference_state, file_tree_name_map, file_renames)


def inline(inference_state, names):
    if not names:
        raise RefactoringError("There is no name under the cursor")
    if any(n.api_type in ('module', 'namespace') for n in names):
        raise RefactoringError("Cannot inline imports, modules or namespaces")
    if any(n.tree_name is None for n in names):
        raise RefactoringError("Cannot inline builtins/extensions")

    definitions = [n for n in names if n.tree_name.is_definition()]
    if len(definitions) == 0:
        raise RefactoringError("No definition found to inline")
    if len(definitions) > 1:
        raise RefactoringError("Cannot inline a name with multiple definitions")
    if len(names) == 1:
        raise RefactoringError("There are no references to this name")

    tree_name = definitions[0].tree_name

    expr_stmt = tree_name.get_definition()
    if expr_stmt.type != 'expr_stmt':
        type_ = dict(
            funcdef='function',
            classdef='class',
        ).get(expr_stmt.type, expr_stmt.type)
        raise RefactoringError("Cannot inline a %s" % type_)

    if len(expr_stmt.get_defined_names(include_setitem=True)) > 1:
        raise RefactoringError("Cannot inline a statement with multiple definitions")
    first_child = expr_stmt.children[1]
    if first_child.type == 'annassign' and len(first_child.children) == 4:
        first_child = first_child.children[2]
    if first_child != '=':
        if first_child.type == 'annassign':
            raise RefactoringError(
                'Cannot inline a statement that is defined by an annotation'
            )
        else:
            raise RefactoringError(
                'Cannot inline a statement with "%s"'
                % first_child.get_code(include_prefix=False)
            )

    rhs = expr_stmt.get_rhs()
    replace_code = rhs.get_code(include_prefix=False)

    references = [n for n in names if not n.tree_name.is_definition()]
    file_to_node_changes = {}
    for name in references:
        tree_name = name.tree_name
        path = name.get_root_context().py__file__()
        s = replace_code
        if rhs.type == 'testlist_star_expr' \
                or tree_name.parent.type in EXPRESSION_PARTS \
                or tree_name.parent.type == 'trailer' \
                and tree_name.parent.get_next_sibling() is not None:
            s = '(' + replace_code + ')'

        of_path = file_to_node_changes.setdefault(path, {})

        n = tree_name
        prefix = n.prefix
        par = n.parent
        if par.type == 'trailer' and par.children[0] == '.':
            prefix = par.parent.children[0].prefix
            n = par
            for some_node in par.parent.children[:par.parent.children.index(par)]:
                of_path[some_node] = ''
        of_path[n] = prefix + s

    path = definitions[0].get_root_context().py__file__()
    changes = file_to_node_changes.setdefault(path, {})
    changes[expr_stmt] = _remove_indent_of_prefix(expr_stmt.get_first_leaf().prefix)
    next_leaf = expr_stmt.get_next_leaf()

    # Most of the time we have to remove the newline at the end of the
    # statement, but if there's a comment we might not need to.
    if next_leaf.prefix.strip(' \t') == '' \
            and (next_leaf.type == 'newline' or next_leaf == ';'):
        changes[next_leaf] = ''
    return Refactoring(inference_state, file_to_node_changes)


def _remove_indent_of_prefix(prefix):
    r"""
    Removes the last indentation of a prefix, e.g. " \n \n " becomes " \n \n".
    """
    return ''.join(split_lines(prefix, keepends=True)[:-1])


def _try_relative_to(path: Path, base: Path) -> Path:
    try:
        return path.relative_to(base)
    except ValueError:
        return path

# === NexusCore/openenv\Lib\site-packages\litellm\router_utils\pattern_match_deployments.py ===
"""
Class to handle llm wildcard routing and regex pattern matching
"""

import copy
import re
from re import Match
from typing import Dict, List, Optional, Tuple

from litellm import get_llm_provider
from litellm._logging import verbose_router_logger


class PatternUtils:
    @staticmethod
    def calculate_pattern_specificity(pattern: str) -> Tuple[int, int]:
        """
        Calculate pattern specificity based on length and complexity.

        Args:
            pattern: Regex pattern to analyze

        Returns:
            Tuple of (length, complexity) for sorting
        """
        complexity_chars = ["*", "+", "?", "\\", "^", "$", "|", "(", ")"]
        ret_val = (
            len(pattern),  # Longer patterns more specific
            sum(
                pattern.count(char) for char in complexity_chars
            ),  # More regex complexity
        )
        return ret_val

    @staticmethod
    def sorted_patterns(
        patterns: Dict[str, List[Dict]]
    ) -> List[Tuple[str, List[Dict]]]:
        """
        Cached property for patterns sorted by specificity.

        Returns:
            Sorted list of pattern-deployment tuples
        """
        return sorted(
            patterns.items(),
            key=lambda x: PatternUtils.calculate_pattern_specificity(x[0]),
            reverse=True,
        )


class PatternMatchRouter:
    """
    Class to handle llm wildcard routing and regex pattern matching

    doc: https://docs.litellm.ai/docs/proxy/configs#provider-specific-wildcard-routing

    This class will store a mapping for regex pattern: List[Deployments]
    """

    def __init__(self):
        self.patterns: Dict[str, List] = {}

    def add_pattern(self, pattern: str, llm_deployment: Dict):
        """
        Add a regex pattern and the corresponding llm deployments to the patterns

        Args:
            pattern: str
            llm_deployment: str or List[str]
        """
        # Convert the pattern to a regex
        regex = self._pattern_to_regex(pattern)
        if regex not in self.patterns:
            self.patterns[regex] = []
        self.patterns[regex].append(llm_deployment)

    def _pattern_to_regex(self, pattern: str) -> str:
        """
        Convert a wildcard pattern to a regex pattern

        example:
        pattern: openai/*
        regex: openai/.*

        pattern: openai/fo::*::static::*
        regex: openai/fo::.*::static::.*

        Args:
            pattern: str

        Returns:
            str: regex pattern
        """
        # # Replace '*' with '.*' for regex matching
        # regex = pattern.replace("*", ".*")
        # # Escape other special characters
        # regex = re.escape(regex).replace(r"\.\*", ".*")
        # return f"^{regex}$"
        return re.escape(pattern).replace(r"\*", "(.*)")

    def _return_pattern_matched_deployments(
        self, matched_pattern: Match, deployments: List[Dict]
    ) -> List[Dict]:
        new_deployments = []
        for deployment in deployments:
            new_deployment = copy.deepcopy(deployment)
            new_deployment["litellm_params"][
                "model"
            ] = PatternMatchRouter.set_deployment_model_name(
                matched_pattern=matched_pattern,
                litellm_deployment_litellm_model=deployment["litellm_params"]["model"],
            )
            new_deployments.append(new_deployment)

        return new_deployments

    def route(
        self, request: Optional[str], filtered_model_names: Optional[List[str]] = None
    ) -> Optional[List[Dict]]:
        """
        Route a requested model to the corresponding llm deployments based on the regex pattern

        loop through all the patterns and find the matching pattern
        if a pattern is found, return the corresponding llm deployments
        if no pattern is found, return None

        Args:
            request: str - the received model name from the user (can be a wildcard route). If none, No deployments will be returned.
            filtered_model_names: Optional[List[str]] - if provided, only return deployments that match the filtered_model_names
        Returns:
            Optional[List[Deployment]]: llm deployments
        """
        try:
            if request is None:
                return None

            sorted_patterns = PatternUtils.sorted_patterns(self.patterns)
            regex_filtered_model_names = (
                [self._pattern_to_regex(m) for m in filtered_model_names]
                if filtered_model_names is not None
                else []
            )
            for pattern, llm_deployments in sorted_patterns:
                if (
                    filtered_model_names is not None
                    and pattern not in regex_filtered_model_names
                ):
                    continue
                pattern_match = re.match(pattern, request)
                if pattern_match:
                    return self._return_pattern_matched_deployments(
                        matched_pattern=pattern_match, deployments=llm_deployments
                    )
        except Exception as e:
            verbose_router_logger.debug(f"Error in PatternMatchRouter.route: {str(e)}")

        return None  # No matching pattern found

    @staticmethod
    def set_deployment_model_name(
        matched_pattern: Match,
        litellm_deployment_litellm_model: str,
    ) -> str:
        """
        Set the model name for the matched pattern llm deployment

        E.g.:

        Case 1:
        model_name: llmengine/* (can be any regex pattern or wildcard pattern)
        litellm_params:
            model: openai/*

        if model_name = "llmengine/foo" -> model = "openai/foo"

        Case 2:
        model_name: llmengine/fo::*::static::*
        litellm_params:
            model: openai/fo::*::static::*

        if model_name = "llmengine/foo::bar::static::baz" -> model = "openai/foo::bar::static::baz"

        Case 3:
        model_name: *meta.llama3*
        litellm_params:
            model: bedrock/meta.llama3*

        if model_name = "hello-world-meta.llama3-70b" -> model = "bedrock/meta.llama3-70b"
        """

        ## BASE CASE: if the deployment model name does not contain a wildcard, return the deployment model name
        if "*" not in litellm_deployment_litellm_model:
            return litellm_deployment_litellm_model

        wildcard_count = litellm_deployment_litellm_model.count("*")

        # Extract all dynamic segments from the request
        dynamic_segments = matched_pattern.groups()

        if len(dynamic_segments) > wildcard_count:
            return (
                matched_pattern.string
            )  # default to the user input, if unable to map based on wildcards.
        # Replace the corresponding wildcards in the litellm model pattern with extracted segments
        for segment in dynamic_segments:
            litellm_deployment_litellm_model = litellm_deployment_litellm_model.replace(
                "*", segment, 1
            )

        return litellm_deployment_litellm_model

    def get_pattern(
        self, model: str, custom_llm_provider: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """
        Check if a pattern exists for the given model and custom llm provider

        Args:
            model: str
            custom_llm_provider: Optional[str]

        Returns:
            bool: True if pattern exists, False otherwise
        """
        if custom_llm_provider is None:
            try:
                (
                    _,
                    custom_llm_provider,
                    _,
                    _,
                ) = get_llm_provider(model=model)
            except Exception:
                # get_llm_provider raises exception when provider is unknown
                pass
        return self.route(model) or self.route(f"{custom_llm_provider}/{model}")

    def get_deployments_by_pattern(
        self, model: str, custom_llm_provider: Optional[str] = None
    ) -> List[Dict]:
        """
        Get the deployments by pattern

        Args:
            model: str
            custom_llm_provider: Optional[str]

        Returns:
            List[Dict]: llm deployments matching the pattern
        """
        pattern_match = self.get_pattern(model, custom_llm_provider)
        if pattern_match:
            return pattern_match
        return []


# Example usage:
# router = PatternRouter()
# router.add_pattern('openai/*', [Deployment(), Deployment()])
# router.add_pattern('openai/fo::*::static::*', Deployment())
# print(router.route('openai/gpt-4'))  # Output: [Deployment(), Deployment()]
# print(router.route('openai/fo::hi::static::hi'))  # Output: [Deployment()]
# print(router.route('something/else'))  # Output: None

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\vertex_embeddings\transformation.py ===
import types
from typing import List, Literal, Optional, Union

from pydantic import BaseModel

from litellm.types.utils import EmbeddingResponse, Usage

from .types import *


class VertexAITextEmbeddingConfig(BaseModel):
    """
    Reference: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/text-embeddings-api#TextEmbeddingInput

    Args:
        auto_truncate: Optional(bool) If True, will truncate input text to fit within the model's max input length.
        task_type: Optional(str) The type of task to be performed. The default is "RETRIEVAL_QUERY".
        title: Optional(str) The title of the document to be embedded. (only valid with task_type=RETRIEVAL_DOCUMENT).
    """

    auto_truncate: Optional[bool] = None
    task_type: Optional[
        Literal[
            "RETRIEVAL_QUERY",
            "RETRIEVAL_DOCUMENT",
            "SEMANTIC_SIMILARITY",
            "CLASSIFICATION",
            "CLUSTERING",
            "QUESTION_ANSWERING",
            "FACT_VERIFICATION",
        ]
    ] = None
    title: Optional[str] = None

    def __init__(
        self,
        auto_truncate: Optional[bool] = None,
        task_type: Optional[
            Literal[
                "RETRIEVAL_QUERY",
                "RETRIEVAL_DOCUMENT",
                "SEMANTIC_SIMILARITY",
                "CLASSIFICATION",
                "CLUSTERING",
                "QUESTION_ANSWERING",
                "FACT_VERIFICATION",
            ]
        ] = None,
        title: Optional[str] = None,
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

    def get_supported_openai_params(self):
        return ["dimensions"]

    def map_openai_params(
        self, non_default_params: dict, optional_params: dict, kwargs: dict
    ):
        for param, value in non_default_params.items():
            if param == "dimensions":
                optional_params["outputDimensionality"] = value

        if "input_type" in kwargs:
            optional_params["task_type"] = kwargs.pop("input_type")
        return optional_params, kwargs

    def get_mapped_special_auth_params(self) -> dict:
        """
        Common auth params across bedrock/vertex_ai/azure/watsonx
        """
        return {"project": "vertex_project", "region_name": "vertex_location"}

    def map_special_auth_params(self, non_default_params: dict, optional_params: dict):
        mapped_params = self.get_mapped_special_auth_params()

        for param, value in non_default_params.items():
            if param in mapped_params:
                optional_params[mapped_params[param]] = value
        return optional_params

    def transform_openai_request_to_vertex_embedding_request(
        self, input: Union[list, str], optional_params: dict, model: str
    ) -> VertexEmbeddingRequest:
        """
        Transforms an openai request to a vertex embedding request.
        """
        if model.isdigit():
            return self._transform_openai_request_to_fine_tuned_embedding_request(
                input, optional_params, model
            )

        vertex_request: VertexEmbeddingRequest = VertexEmbeddingRequest()
        vertex_text_embedding_input_list: List[TextEmbeddingInput] = []
        task_type: Optional[TaskType] = optional_params.get("task_type")
        title = optional_params.get("title")

        if isinstance(input, str):
            input = [input]  # Convert single string to list for uniform processing

        for text in input:
            embedding_input = self.create_embedding_input(
                content=text, task_type=task_type, title=title
            )
            vertex_text_embedding_input_list.append(embedding_input)

        vertex_request["instances"] = vertex_text_embedding_input_list
        vertex_request["parameters"] = EmbeddingParameters(**optional_params)

        return vertex_request

    def _transform_openai_request_to_fine_tuned_embedding_request(
        self, input: Union[list, str], optional_params: dict, model: str
    ) -> VertexEmbeddingRequest:
        """
        Transforms an openai request to a vertex fine-tuned embedding request.

        Vertex Doc: https://console.cloud.google.com/vertex-ai/model-garden?hl=en&project=adroit-crow-413218&pageState=(%22galleryStateKey%22:(%22f%22:(%22g%22:%5B%5D,%22o%22:%5B%5D),%22s%22:%22%22))
        Sample Request:

        ```json
        {
            "instances" : [
                {
                "inputs": "How would the Future of AI in 10 Years look?",
                "parameters": {
                    "max_new_tokens": 128,
                    "temperature": 1.0,
                    "top_p": 0.9,
                    "top_k": 10
                }
                }
            ]
        }
        ```
        """
        vertex_request: VertexEmbeddingRequest = VertexEmbeddingRequest()
        vertex_text_embedding_input_list: List[TextEmbeddingFineTunedInput] = []
        if isinstance(input, str):
            input = [input]  # Convert single string to list for uniform processing

        for text in input:
            embedding_input = TextEmbeddingFineTunedInput(inputs=text)
            vertex_text_embedding_input_list.append(embedding_input)

        vertex_request["instances"] = vertex_text_embedding_input_list
        vertex_request["parameters"] = TextEmbeddingFineTunedParameters(
            **optional_params
        )

        return vertex_request

    def create_embedding_input(
        self,
        content: str,
        task_type: Optional[TaskType] = None,
        title: Optional[str] = None,
    ) -> TextEmbeddingInput:
        """
        Creates a TextEmbeddingInput object.

        Vertex requires a List of TextEmbeddingInput objects. This helper function creates a single TextEmbeddingInput object.

        Args:
            content (str): The content to be embedded.
            task_type (Optional[TaskType]): The type of task to be performed".
            title (Optional[str]): The title of the document to be embedded

        Returns:
            TextEmbeddingInput: A TextEmbeddingInput object.
        """
        text_embedding_input = TextEmbeddingInput(content=content)
        if task_type is not None:
            text_embedding_input["task_type"] = task_type
        if title is not None:
            text_embedding_input["title"] = title
        return text_embedding_input

    def transform_vertex_response_to_openai(
        self, response: dict, model: str, model_response: EmbeddingResponse
    ) -> EmbeddingResponse:
        """
        Transforms a vertex embedding response to an openai response.
        """
        if model.isdigit():
            return self._transform_vertex_response_to_openai_for_fine_tuned_models(
                response, model, model_response
            )

        _predictions = response["predictions"]

        embedding_response = []
        input_tokens: int = 0
        for idx, element in enumerate(_predictions):
            embedding = element["embeddings"]
            embedding_response.append(
                {
                    "object": "embedding",
                    "index": idx,
                    "embedding": embedding["values"],
                }
            )
            input_tokens += embedding["statistics"]["token_count"]

        model_response.object = "list"
        model_response.data = embedding_response
        model_response.model = model
        usage = Usage(
            prompt_tokens=input_tokens, completion_tokens=0, total_tokens=input_tokens
        )
        setattr(model_response, "usage", usage)
        return model_response

    def _transform_vertex_response_to_openai_for_fine_tuned_models(
        self, response: dict, model: str, model_response: EmbeddingResponse
    ) -> EmbeddingResponse:
        """
        Transforms a vertex fine-tuned model embedding response to an openai response format.
        """
        _predictions = response["predictions"]

        embedding_response = []
        # For fine-tuned models, we don't get token counts in the response
        input_tokens = 0

        for idx, embedding_values in enumerate(_predictions):
            embedding_response.append(
                {
                    "object": "embedding",
                    "index": idx,
                    "embedding": embedding_values[
                        0
                    ],  # The embedding values are nested one level deeper
                }
            )

        model_response.object = "list"
        model_response.data = embedding_response
        model_response.model = model
        usage = Usage(
            prompt_tokens=input_tokens, completion_tokens=0, total_tokens=input_tokens
        )
        setattr(model_response, "usage", usage)
        return model_response

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\decorator.py ===
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Mapping, Optional, Tuple, Type, TypeVar, Union, overload

from pydantic.v1 import validator
from pydantic.v1.config import Extra
from pydantic.v1.errors import ConfigError
from pydantic.v1.main import BaseModel, create_model
from pydantic.v1.typing import get_all_type_hints
from pydantic.v1.utils import to_camel

__all__ = ('validate_arguments',)

if TYPE_CHECKING:
    from pydantic.v1.typing import AnyCallable

    AnyCallableT = TypeVar('AnyCallableT', bound=AnyCallable)
    ConfigType = Union[None, Type[Any], Dict[str, Any]]


@overload
def validate_arguments(func: None = None, *, config: 'ConfigType' = None) -> Callable[['AnyCallableT'], 'AnyCallableT']:
    ...


@overload
def validate_arguments(func: 'AnyCallableT') -> 'AnyCallableT':
    ...


def validate_arguments(func: Optional['AnyCallableT'] = None, *, config: 'ConfigType' = None) -> Any:
    """
    Decorator to validate the arguments passed to a function.
    """

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
    def __init__(self, function: 'AnyCallableT', config: 'ConfigType'):  # noqa C901
        from inspect import Parameter, signature

        parameters: Mapping[str, Parameter] = signature(function).parameters

        if parameters.keys() & {ALT_V_ARGS, ALT_V_KWARGS, V_POSITIONAL_ONLY_NAME, V_DUPLICATE_KWARGS}:
            raise ConfigError(
                f'"{ALT_V_ARGS}", "{ALT_V_KWARGS}", "{V_POSITIONAL_ONLY_NAME}" and "{V_DUPLICATE_KWARGS}" '
                f'are not permitted as argument names when using the "{validate_arguments.__name__}" decorator'
            )

        self.raw_function = function
        self.arg_mapping: Dict[int, str] = {}
        self.positional_only_args = set()
        self.v_args_name = 'args'
        self.v_kwargs_name = 'kwargs'

        type_hints = get_all_type_hints(function)
        takes_args = False
        takes_kwargs = False
        fields: Dict[str, Tuple[Any, Any]] = {}
        for i, (name, p) in enumerate(parameters.items()):
            if p.annotation is p.empty:
                annotation = Any
            else:
                annotation = type_hints[name]

            default = ... if p.default is p.empty else p.default
            if p.kind == Parameter.POSITIONAL_ONLY:
                self.arg_mapping[i] = name
                fields[name] = annotation, default
                fields[V_POSITIONAL_ONLY_NAME] = List[str], None
                self.positional_only_args.add(name)
            elif p.kind == Parameter.POSITIONAL_OR_KEYWORD:
                self.arg_mapping[i] = name
                fields[name] = annotation, default
                fields[V_DUPLICATE_KWARGS] = List[str], None
            elif p.kind == Parameter.KEYWORD_ONLY:
                fields[name] = annotation, default
            elif p.kind == Parameter.VAR_POSITIONAL:
                self.v_args_name = name
                fields[name] = Tuple[annotation, ...], None
                takes_args = True
            else:
                assert p.kind == Parameter.VAR_KEYWORD, p.kind
                self.v_kwargs_name = name
                fields[name] = Dict[str, annotation], None  # type: ignore
                takes_kwargs = True

        # these checks avoid a clash between "args" and a field with that name
        if not takes_args and self.v_args_name in fields:
            self.v_args_name = ALT_V_ARGS

        # same with "kwargs"
        if not takes_kwargs and self.v_kwargs_name in fields:
            self.v_kwargs_name = ALT_V_KWARGS

        if not takes_args:
            # we add the field so validation below can raise the correct exception
            fields[self.v_args_name] = List[Any], None

        if not takes_kwargs:
            # same with kwargs
            fields[self.v_kwargs_name] = Dict[Any, Any], None

        self.create_model(fields, takes_args, takes_kwargs, config)

    def init_model_instance(self, *args: Any, **kwargs: Any) -> BaseModel:
        values = self.build_values(args, kwargs)
        return self.model(**values)

    def call(self, *args: Any, **kwargs: Any) -> Any:
        m = self.init_model_instance(*args, **kwargs)
        return self.execute(m)

    def build_values(self, args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        values: Dict[str, Any] = {}
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

        var_kwargs: Dict[str, Any] = {}
        wrong_positional_args = []
        duplicate_kwargs = []
        fields_alias = [
            field.alias
            for name, field in self.model.__fields__.items()
            if name not in (self.v_args_name, self.v_kwargs_name)
        ]
        non_var_fields = set(self.model.__fields__) - {self.v_args_name, self.v_kwargs_name}
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
        d = {k: v for k, v in m._iter() if k in m.__fields_set__ or m.__fields__[k].default_factory}
        var_kwargs = d.pop(self.v_kwargs_name, {})

        if self.v_args_name in d:
            args_: List[Any] = []
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

    def create_model(self, fields: Dict[str, Any], takes_args: bool, takes_kwargs: bool, config: 'ConfigType') -> None:
        pos_args = len(self.arg_mapping)

        class CustomConfig:
            pass

        if not TYPE_CHECKING:  # pragma: no branch
            if isinstance(config, dict):
                CustomConfig = type('Config', (), config)  # noqa: F811
            elif config is not None:
                CustomConfig = config  # noqa: F811

        if hasattr(CustomConfig, 'fields') or hasattr(CustomConfig, 'alias_generator'):
            raise ConfigError(
                'Setting the "fields" and "alias_generator" property on custom Config for '
                '@validate_arguments is not yet supported, please remove.'
            )

        class DecoratorBaseModel(BaseModel):
            @validator(self.v_args_name, check_fields=False, allow_reuse=True)
            def check_args(cls, v: Optional[List[Any]]) -> Optional[List[Any]]:
                if takes_args or v is None:
                    return v

                raise TypeError(f'{pos_args} positional arguments expected but {pos_args + len(v)} given')

            @validator(self.v_kwargs_name, check_fields=False, allow_reuse=True)
            def check_kwargs(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
                if takes_kwargs or v is None:
                    return v

                plural = '' if len(v) == 1 else 's'
                keys = ', '.join(map(repr, v.keys()))
                raise TypeError(f'unexpected keyword argument{plural}: {keys}')

            @validator(V_POSITIONAL_ONLY_NAME, check_fields=False, allow_reuse=True)
            def check_positional_only(cls, v: Optional[List[str]]) -> None:
                if v is None:
                    return

                plural = '' if len(v) == 1 else 's'
                keys = ', '.join(map(repr, v))
                raise TypeError(f'positional-only argument{plural} passed as keyword argument{plural}: {keys}')

            @validator(V_DUPLICATE_KWARGS, check_fields=False, allow_reuse=True)
            def check_duplicate_kwargs(cls, v: Optional[List[str]]) -> None:
                if v is None:
                    return

                plural = '' if len(v) == 1 else 's'
                keys = ', '.join(map(repr, v))
                raise TypeError(f'multiple values for argument{plural}: {keys}')

            class Config(CustomConfig):
                extra = getattr(CustomConfig, 'extra', Extra.forbid)

        self.model = create_model(to_camel(self.raw_function.__name__), __base__=DecoratorBaseModel, **fields)

# === NexusCore/openenv\Lib\site-packages\tornado\test\process_test.py ===
import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
import unittest

from tornado.httpclient import HTTPClient, HTTPError
from tornado.httpserver import HTTPServer
from tornado.log import gen_log
from tornado.process import fork_processes, task_id, Subprocess
from tornado.simple_httpclient import SimpleAsyncHTTPClient
from tornado.testing import bind_unused_port, ExpectLog, AsyncTestCase, gen_test
from tornado.test.util import skipIfNonUnix
from tornado.web import RequestHandler, Application


# Not using AsyncHTTPTestCase because we need control over the IOLoop.
@skipIfNonUnix
class ProcessTest(unittest.TestCase):
    def get_app(self):
        class ProcessHandler(RequestHandler):
            def get(self):
                if self.get_argument("exit", None):
                    # must use os._exit instead of sys.exit so unittest's
                    # exception handler doesn't catch it
                    os._exit(int(self.get_argument("exit")))
                if self.get_argument("signal", None):
                    os.kill(os.getpid(), int(self.get_argument("signal")))
                self.write(str(os.getpid()))

        return Application([("/", ProcessHandler)])

    def tearDown(self):
        if task_id() is not None:
            # We're in a child process, and probably got to this point
            # via an uncaught exception.  If we return now, both
            # processes will continue with the rest of the test suite.
            # Exit now so the parent process will restart the child
            # (since we don't have a clean way to signal failure to
            # the parent that won't restart)
            logging.error("aborting child process from tearDown")
            logging.shutdown()
            os._exit(1)
        # In the surviving process, clear the alarm we set earlier
        signal.alarm(0)
        super().tearDown()

    def test_multi_process(self):
        # This test doesn't work on twisted because we use the global
        # reactor and don't restore it to a sane state after the fork
        # (asyncio has the same issue, but we have a special case in
        # place for it).
        with ExpectLog(
            gen_log, "(Starting .* processes|child .* exited|uncaught exception)"
        ):
            sock, port = bind_unused_port()

            def get_url(path):
                return "http://127.0.0.1:%d%s" % (port, path)

            # ensure that none of these processes live too long
            signal.alarm(5)  # master process
            try:
                id = fork_processes(3, max_restarts=3)
                self.assertIsNotNone(id)
                signal.alarm(5)  # child processes
            except SystemExit as e:
                # if we exit cleanly from fork_processes, all the child processes
                # finished with status 0
                self.assertEqual(e.code, 0)
                self.assertIsNone(task_id())
                sock.close()
                return
            try:
                if id in (0, 1):
                    self.assertEqual(id, task_id())

                    async def f():
                        server = HTTPServer(self.get_app())
                        server.add_sockets([sock])
                        await asyncio.Event().wait()

                    asyncio.run(f())
                elif id == 2:
                    self.assertEqual(id, task_id())
                    sock.close()
                    # Always use SimpleAsyncHTTPClient here; the curl
                    # version appears to get confused sometimes if the
                    # connection gets closed before it's had a chance to
                    # switch from writing mode to reading mode.
                    client = HTTPClient(SimpleAsyncHTTPClient)

                    def fetch(url, fail_ok=False):
                        try:
                            return client.fetch(get_url(url))
                        except HTTPError as e:
                            if not (fail_ok and e.code == 599):
                                raise

                    # Make two processes exit abnormally
                    fetch("/?exit=2", fail_ok=True)
                    fetch("/?exit=3", fail_ok=True)

                    # They've been restarted, so a new fetch will work
                    int(fetch("/").body)

                    # Now the same with signals
                    # Disabled because on the mac a process dying with a signal
                    # can trigger an "Application exited abnormally; send error
                    # report to Apple?" prompt.
                    # fetch("/?signal=%d" % signal.SIGTERM, fail_ok=True)
                    # fetch("/?signal=%d" % signal.SIGABRT, fail_ok=True)
                    # int(fetch("/").body)

                    # Now kill them normally so they won't be restarted
                    fetch("/?exit=0", fail_ok=True)
                    # One process left; watch it's pid change
                    pid = int(fetch("/").body)
                    fetch("/?exit=4", fail_ok=True)
                    pid2 = int(fetch("/").body)
                    self.assertNotEqual(pid, pid2)

                    # Kill the last one so we shut down cleanly
                    fetch("/?exit=0", fail_ok=True)

                    os._exit(0)
            except Exception:
                logging.error("exception in child process %d", id, exc_info=True)
                raise


@skipIfNonUnix
class SubprocessTest(AsyncTestCase):
    def term_and_wait(self, subproc):
        subproc.proc.terminate()
        subproc.proc.wait()

    @gen_test
    def test_subprocess(self):
        subproc = Subprocess(
            [sys.executable, "-u", "-i"],
            stdin=Subprocess.STREAM,
            stdout=Subprocess.STREAM,
            stderr=subprocess.STDOUT,
        )
        self.addCleanup(lambda: self.term_and_wait(subproc))
        self.addCleanup(subproc.stdout.close)
        self.addCleanup(subproc.stdin.close)
        yield subproc.stdout.read_until(b">>> ")
        subproc.stdin.write(b"print('hello')\n")
        data = yield subproc.stdout.read_until(b"\n")
        self.assertEqual(data, b"hello\n")

        yield subproc.stdout.read_until(b">>> ")
        subproc.stdin.write(b"raise SystemExit\n")
        data = yield subproc.stdout.read_until_close()
        self.assertEqual(data, b"")

    @gen_test
    def test_close_stdin(self):
        # Close the parent's stdin handle and see that the child recognizes it.
        subproc = Subprocess(
            [sys.executable, "-u", "-i"],
            stdin=Subprocess.STREAM,
            stdout=Subprocess.STREAM,
            stderr=subprocess.STDOUT,
        )
        self.addCleanup(lambda: self.term_and_wait(subproc))
        yield subproc.stdout.read_until(b">>> ")
        subproc.stdin.close()
        data = yield subproc.stdout.read_until_close()
        self.assertEqual(data, b"\n")

    @gen_test
    def test_stderr(self):
        # This test is mysteriously flaky on twisted: it succeeds, but logs
        # an error of EBADF on closing a file descriptor.
        subproc = Subprocess(
            [sys.executable, "-u", "-c", r"import sys; sys.stderr.write('hello\n')"],
            stderr=Subprocess.STREAM,
        )
        self.addCleanup(lambda: self.term_and_wait(subproc))
        data = yield subproc.stderr.read_until(b"\n")
        self.assertEqual(data, b"hello\n")
        # More mysterious EBADF: This fails if done with self.addCleanup instead of here.
        subproc.stderr.close()

    def test_sigchild(self):
        Subprocess.initialize()
        self.addCleanup(Subprocess.uninitialize)
        subproc = Subprocess([sys.executable, "-c", "pass"])
        subproc.set_exit_callback(self.stop)
        ret = self.wait()
        self.assertEqual(ret, 0)
        self.assertEqual(subproc.returncode, ret)

    @gen_test
    def test_sigchild_future(self):
        Subprocess.initialize()
        self.addCleanup(Subprocess.uninitialize)
        subproc = Subprocess([sys.executable, "-c", "pass"])
        ret = yield subproc.wait_for_exit()
        self.assertEqual(ret, 0)
        self.assertEqual(subproc.returncode, ret)

    def test_sigchild_signal(self):
        Subprocess.initialize()
        self.addCleanup(Subprocess.uninitialize)
        subproc = Subprocess(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdout=Subprocess.STREAM,
        )
        self.addCleanup(subproc.stdout.close)
        subproc.set_exit_callback(self.stop)

        # For unclear reasons, killing a process too soon after
        # creating it can result in an exit status corresponding to
        # SIGKILL instead of the actual signal involved. This has been
        # observed on macOS 10.15 with Python 3.8 installed via brew,
        # but not with the system-installed Python 3.7.
        time.sleep(0.1)

        os.kill(subproc.pid, signal.SIGTERM)
        try:
            ret = self.wait()
        except AssertionError:
            # We failed to get the termination signal. This test is
            # occasionally flaky on pypy, so try to get a little more
            # information: did the process close its stdout
            # (indicating that the problem is in the parent process's
            # signal handling) or did the child process somehow fail
            # to terminate?
            fut = subproc.stdout.read_until_close()
            fut.add_done_callback(lambda f: self.stop())  # type: ignore
            try:
                self.wait()
            except AssertionError:
                raise AssertionError("subprocess failed to terminate")
            else:
                raise AssertionError(
                    "subprocess closed stdout but failed to " "get termination signal"
                )
        self.assertEqual(subproc.returncode, ret)
        self.assertEqual(ret, -signal.SIGTERM)

    @gen_test
    def test_wait_for_exit_raise(self):
        Subprocess.initialize()
        self.addCleanup(Subprocess.uninitialize)
        subproc = Subprocess([sys.executable, "-c", "import sys; sys.exit(1)"])
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            yield subproc.wait_for_exit()
        self.assertEqual(cm.exception.returncode, 1)

    @gen_test
    def test_wait_for_exit_raise_disabled(self):
        Subprocess.initialize()
        self.addCleanup(Subprocess.uninitialize)
        subproc = Subprocess([sys.executable, "-c", "import sys; sys.exit(1)"])
        ret = yield subproc.wait_for_exit(raise_error=False)
        self.assertEqual(ret, 1)

# === NexusCore/openenv\Lib\site-packages\win32\test\test_odbc.py ===
# odbc test suite kindly contributed by Frank Millman.
import os
import sys
import tempfile
import unittest

import odbc
import pythoncom
from pywin32_testutil import TestSkipped
from win32com.client import constants

# We use the DAO ODBC driver
from win32com.client.gencache import EnsureDispatch


class TestStuff(unittest.TestCase):
    def setUp(self):
        self.tablename = "pywin32test_users"
        self.db_filename = None
        self.conn = self.cur = None
        try:
            # Test any database if a connection string is supplied...
            conn_str = os.environ["TEST_ODBC_CONNECTION_STRING"]
        except KeyError:
            # Create a local MSAccess DB for testing.
            self.db_filename = tempfile.NamedTemporaryFile().name + ".mdb"

            # Create a brand-new database - what is the story with these?
            for suffix in (".36", ".35", ".30"):
                try:
                    dbe = EnsureDispatch("DAO.DBEngine" + suffix)
                    break
                except pythoncom.com_error:
                    pass
            else:
                raise TestSkipped("Can't find a DB engine")

            workspace = dbe.Workspaces(0)

            newdb = workspace.CreateDatabase(
                self.db_filename, constants.dbLangGeneral, constants.dbEncrypt
            )

            newdb.Close()

            conn_str = (
                "Driver={{Microsoft Access Driver (*.mdb)}};dbq={};Uid=;Pwd=;".format(
                    self.db_filename,
                )
            )
        # print("Connection string:", conn_str)
        self.conn = odbc.odbc(conn_str)
        # And we expect a 'users' table for these tests.
        self.cur = self.conn.cursor()
        ## self.cur.setoutputsize(1000)
        try:
            self.cur.execute("""drop table %s""" % self.tablename)
        except (odbc.error, odbc.progError):
            pass

        ## This needs to be adjusted for sql server syntax for unicode fields
        ##  - memo -> TEXT
        ##  - varchar -> nvarchar
        self.assertEqual(
            self.cur.execute(
                """create table %s (
                    userid varchar(25),
                    username varchar(25),
                    bitfield bit,
                    intfield integer,
                    floatfield float,
                    datefield datetime,
                    rawfield varbinary(100),
                    longtextfield memo,
                    longbinaryfield image
            )"""
                % self.tablename
            ),
            -1,
        )

    def tearDown(self):
        if self.cur is not None:
            try:
                self.cur.execute("""drop table %s""" % self.tablename)
            except (odbc.error, odbc.progError) as why:
                print("Failed to delete test table %s" % self.tablename, why)

            self.cur.close()
            self.cur = None
        if self.conn is not None:
            self.conn.close()
            self.conn = None
        if self.db_filename is not None:
            try:
                os.unlink(self.db_filename)
            except OSError:
                pass

    def test_insert_select(self, userid="Frank", username="Frank Millman"):
        self.assertEqual(
            self.cur.execute(
                "insert into %s (userid, username) \
            values (?,?)"
                % self.tablename,
                [userid, username],
            ),
            1,
        )
        self.assertEqual(
            self.cur.execute(
                "select * from %s \
            where userid = ?"
                % self.tablename,
                [userid.lower()],
            ),
            0,
        )
        self.assertEqual(
            self.cur.execute(
                "select * from %s \
            where username = ?"
                % self.tablename,
                [username.lower()],
            ),
            0,
        )

    def test_insert_select_unicode(self, userid="Frank", username="Frank Millman"):
        self.assertEqual(
            self.cur.execute(
                "insert into %s (userid, username)\
            values (?,?)"
                % self.tablename,
                [userid, username],
            ),
            1,
        )
        self.assertEqual(
            self.cur.execute(
                "select * from %s \
            where userid = ?"
                % self.tablename,
                [userid.lower()],
            ),
            0,
        )
        self.assertEqual(
            self.cur.execute(
                "select * from %s \
            where username = ?"
                % self.tablename,
                [username.lower()],
            ),
            0,
        )

    def test_insert_select_unicode_ext(self):
        userid = "t-\xe0\xf2"
        username = "test-\xe0\xf2 name"
        self.test_insert_select_unicode(userid, username)

    def _test_val(self, fieldName, value):
        for x in range(100):
            self.cur.execute("delete from %s where userid='Frank'" % self.tablename)
            self.assertEqual(
                self.cur.execute(
                    f"insert into {self.tablename} (userid, {fieldName}) values (?,?)",
                    ["Frank", value],
                ),
                1,
            )
            self.cur.execute(
                f"select {fieldName} from {self.tablename} where userid = ?",
                ["Frank"],
            )
            rows = self.cur.fetchmany()
            self.assertEqual(1, len(rows))
            row = rows[0]
            self.assertEqual(row[0], value)

    def testBit(self):
        self._test_val("bitfield", 1)
        self._test_val("bitfield", 0)

    def testInt(self):
        self._test_val("intfield", 1)
        self._test_val("intfield", 0)
        self._test_val("intfield", sys.maxsize)

    def testFloat(self):
        self._test_val("floatfield", 1.01)
        self._test_val("floatfield", 0)

    def testVarchar(
        self,
    ):
        self._test_val("username", "foo")

    def testLongVarchar(self):
        """Test a long text field in excess of internal cursor data size (65536)"""
        self._test_val("longtextfield", "abc" * 70000)

    def testLongBinary(self):
        """Test a long raw field in excess of internal cursor data size (65536)"""
        self._test_val("longbinaryfield", memoryview(b"\0\1\2" * 70000))

    def testRaw(self):
        ## Test binary data
        self._test_val("rawfield", memoryview(b"\1\2\3\4\0\5\6\7"))

    def test_widechar(self):
        """Test a unicode character that would be mangled if bound as plain character.
        For example, previously the below was returned as ascii 'a'
        """
        self._test_val("username", "\u0101")

    def testDates(self):
        import datetime

        for v in ((1900, 12, 25, 23, 39, 59),):
            d = datetime.datetime(*v)
            self._test_val("datefield", d)

    def test_set_nonzero_length(self):
        self.assertEqual(
            self.cur.execute(
                "insert into %s (userid,username) values (?,?)" % self.tablename,
                ["Frank", "Frank Millman"],
            ),
            1,
        )
        self.assertEqual(
            self.cur.execute("update %s set username = ?" % self.tablename, ["Frank"]),
            1,
        )
        self.assertEqual(self.cur.execute("select * from %s" % self.tablename), 0)
        self.assertEqual(len(self.cur.fetchone()[1]), 5)

    def test_set_zero_length(self):
        self.assertEqual(
            self.cur.execute(
                "insert into %s (userid,username) values (?,?)" % self.tablename,
                [b"Frank", ""],
            ),
            1,
        )
        self.assertEqual(self.cur.execute("select * from %s" % self.tablename), 0)
        self.assertEqual(len(self.cur.fetchone()[1]), 0)

    def test_set_zero_length_unicode(self):
        self.assertEqual(
            self.cur.execute(
                "insert into %s (userid,username) values (?,?)" % self.tablename,
                ["Frank", ""],
            ),
            1,
        )
        self.assertEqual(self.cur.execute("select * from %s" % self.tablename), 0)
        self.assertEqual(len(self.cur.fetchone()[1]), 0)


if __name__ == "__main__":
    unittest.main()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\packaging\_manylinux.py ===
from __future__ import annotations

import collections
import contextlib
import functools
import os
import re
import sys
import warnings
from typing import Generator, Iterator, NamedTuple, Sequence

from ._elffile import EIClass, EIData, ELFFile, EMachine

EF_ARM_ABIMASK = 0xFF000000
EF_ARM_ABI_VER5 = 0x05000000
EF_ARM_ABI_FLOAT_HARD = 0x00000400


# `os.PathLike` not a generic type until Python 3.9, so sticking with `str`
# as the type for `path` until then.
@contextlib.contextmanager
def _parse_elf(path: str) -> Generator[ELFFile | None, None, None]:
    try:
        with open(path, "rb") as f:
            yield ELFFile(f)
    except (OSError, TypeError, ValueError):
        yield None


def _is_linux_armhf(executable: str) -> bool:
    # hard-float ABI can be detected from the ELF header of the running
    # process
    # https://static.docs.arm.com/ihi0044/g/aaelf32.pdf
    with _parse_elf(executable) as f:
        return (
            f is not None
            and f.capacity == EIClass.C32
            and f.encoding == EIData.Lsb
            and f.machine == EMachine.Arm
            and f.flags & EF_ARM_ABIMASK == EF_ARM_ABI_VER5
            and f.flags & EF_ARM_ABI_FLOAT_HARD == EF_ARM_ABI_FLOAT_HARD
        )


def _is_linux_i686(executable: str) -> bool:
    with _parse_elf(executable) as f:
        return (
            f is not None
            and f.capacity == EIClass.C32
            and f.encoding == EIData.Lsb
            and f.machine == EMachine.I386
        )


def _have_compatible_abi(executable: str, archs: Sequence[str]) -> bool:
    if "armv7l" in archs:
        return _is_linux_armhf(executable)
    if "i686" in archs:
        return _is_linux_i686(executable)
    allowed_archs = {
        "x86_64",
        "aarch64",
        "ppc64",
        "ppc64le",
        "s390x",
        "loongarch64",
        "riscv64",
    }
    return any(arch in allowed_archs for arch in archs)


# If glibc ever changes its major version, we need to know what the last
# minor version was, so we can build the complete list of all versions.
# For now, guess what the highest minor version might be, assume it will
# be 50 for testing. Once this actually happens, update the dictionary
# with the actual value.
_LAST_GLIBC_MINOR: dict[int, int] = collections.defaultdict(lambda: 50)


class _GLibCVersion(NamedTuple):
    major: int
    minor: int


def _glibc_version_string_confstr() -> str | None:
    """
    Primary implementation of glibc_version_string using os.confstr.
    """
    # os.confstr is quite a bit faster than ctypes.DLL. It's also less likely
    # to be broken or missing. This strategy is used in the standard library
    # platform module.
    # https://github.com/python/cpython/blob/fcf1d003bf4f0100c/Lib/platform.py#L175-L183
    try:
        # Should be a string like "glibc 2.17".
        version_string: str | None = os.confstr("CS_GNU_LIBC_VERSION")
        assert version_string is not None
        _, version = version_string.rsplit()
    except (AssertionError, AttributeError, OSError, ValueError):
        # os.confstr() or CS_GNU_LIBC_VERSION not available (or a bad value)...
        return None
    return version


def _glibc_version_string_ctypes() -> str | None:
    """
    Fallback implementation of glibc_version_string using ctypes.
    """
    try:
        import ctypes
    except ImportError:
        return None

    # ctypes.CDLL(None) internally calls dlopen(NULL), and as the dlopen
    # manpage says, "If filename is NULL, then the returned handle is for the
    # main program". This way we can let the linker do the work to figure out
    # which libc our process is actually using.
    #
    # We must also handle the special case where the executable is not a
    # dynamically linked executable. This can occur when using musl libc,
    # for example. In this situation, dlopen() will error, leading to an
    # OSError. Interestingly, at least in the case of musl, there is no
    # errno set on the OSError. The single string argument used to construct
    # OSError comes from libc itself and is therefore not portable to
    # hard code here. In any case, failure to call dlopen() means we
    # can proceed, so we bail on our attempt.
    try:
        process_namespace = ctypes.CDLL(None)
    except OSError:
        return None

    try:
        gnu_get_libc_version = process_namespace.gnu_get_libc_version
    except AttributeError:
        # Symbol doesn't exist -> therefore, we are not linked to
        # glibc.
        return None

    # Call gnu_get_libc_version, which returns a string like "2.5"
    gnu_get_libc_version.restype = ctypes.c_char_p
    version_str: str = gnu_get_libc_version()
    # py2 / py3 compatibility:
    if not isinstance(version_str, str):
        version_str = version_str.decode("ascii")

    return version_str


def _glibc_version_string() -> str | None:
    """Returns glibc version string, or None if not using glibc."""
    return _glibc_version_string_confstr() or _glibc_version_string_ctypes()


def _parse_glibc_version(version_str: str) -> tuple[int, int]:
    """Parse glibc version.

    We use a regexp instead of str.split because we want to discard any
    random junk that might come after the minor version -- this might happen
    in patched/forked versions of glibc (e.g. Linaro's version of glibc
    uses version strings like "2.20-2014.11"). See gh-3588.
    """
    m = re.match(r"(?P<major>[0-9]+)\.(?P<minor>[0-9]+)", version_str)
    if not m:
        warnings.warn(
            f"Expected glibc version with 2 components major.minor,"
            f" got: {version_str}",
            RuntimeWarning,
            stacklevel=2,
        )
        return -1, -1
    return int(m.group("major")), int(m.group("minor"))


@functools.lru_cache
def _get_glibc_version() -> tuple[int, int]:
    version_str = _glibc_version_string()
    if version_str is None:
        return (-1, -1)
    return _parse_glibc_version(version_str)


# From PEP 513, PEP 600
def _is_compatible(arch: str, version: _GLibCVersion) -> bool:
    sys_glibc = _get_glibc_version()
    if sys_glibc < version:
        return False
    # Check for presence of _manylinux module.
    try:
        import _manylinux
    except ImportError:
        return True
    if hasattr(_manylinux, "manylinux_compatible"):
        result = _manylinux.manylinux_compatible(version[0], version[1], arch)
        if result is not None:
            return bool(result)
        return True
    if version == _GLibCVersion(2, 5):
        if hasattr(_manylinux, "manylinux1_compatible"):
            return bool(_manylinux.manylinux1_compatible)
    if version == _GLibCVersion(2, 12):
        if hasattr(_manylinux, "manylinux2010_compatible"):
            return bool(_manylinux.manylinux2010_compatible)
    if version == _GLibCVersion(2, 17):
        if hasattr(_manylinux, "manylinux2014_compatible"):
            return bool(_manylinux.manylinux2014_compatible)
    return True


_LEGACY_MANYLINUX_MAP = {
    # CentOS 7 w/ glibc 2.17 (PEP 599)
    (2, 17): "manylinux2014",
    # CentOS 6 w/ glibc 2.12 (PEP 571)
    (2, 12): "manylinux2010",
    # CentOS 5 w/ glibc 2.5 (PEP 513)
    (2, 5): "manylinux1",
}


def platform_tags(archs: Sequence[str]) -> Iterator[str]:
    """Generate manylinux tags compatible to the current platform.

    :param archs: Sequence of compatible architectures.
        The first one shall be the closest to the actual architecture and be the part of
        platform tag after the ``linux_`` prefix, e.g. ``x86_64``.
        The ``linux_`` prefix is assumed as a prerequisite for the current platform to
        be manylinux-compatible.

    :returns: An iterator of compatible manylinux tags.
    """
    if not _have_compatible_abi(sys.executable, archs):
        return
    # Oldest glibc to be supported regardless of architecture is (2, 17).
    too_old_glibc2 = _GLibCVersion(2, 16)
    if set(archs) & {"x86_64", "i686"}:
        # On x86/i686 also oldest glibc to be supported is (2, 5).
        too_old_glibc2 = _GLibCVersion(2, 4)
    current_glibc = _GLibCVersion(*_get_glibc_version())
    glibc_max_list = [current_glibc]
    # We can assume compatibility across glibc major versions.
    # https://sourceware.org/bugzilla/show_bug.cgi?id=24636
    #
    # Build a list of maximum glibc versions so that we can
    # output the canonical list of all glibc from current_glibc
    # down to too_old_glibc2, including all intermediary versions.
    for glibc_major in range(current_glibc.major - 1, 1, -1):
        glibc_minor = _LAST_GLIBC_MINOR[glibc_major]
        glibc_max_list.append(_GLibCVersion(glibc_major, glibc_minor))
    for arch in archs:
        for glibc_max in glibc_max_list:
            if glibc_max.major == too_old_glibc2.major:
                min_minor = too_old_glibc2.minor
            else:
                # For other glibc major versions oldest supported is (x, 0).
                min_minor = -1
            for glibc_minor in range(glibc_max.minor, min_minor, -1):
                glibc_version = _GLibCVersion(glibc_max.major, glibc_minor)
                tag = "manylinux_{}_{}".format(*glibc_version)
                if _is_compatible(arch, glibc_version):
                    yield f"{tag}_{arch}"
                # Handle the legacy manylinux1, manylinux2010, manylinux2014 tags.
                if glibc_version in _LEGACY_MANYLINUX_MAP:
                    legacy_tag = _LEGACY_MANYLINUX_MAP[glibc_version]
                    if _is_compatible(arch, glibc_version):
                        yield f"{legacy_tag}_{arch}"

# === NexusCore/openenv\Lib\site-packages\matplotlib\tri\_tritools.py ===
"""
Tools for triangular grids.
"""

import numpy as np

from matplotlib import _api
from matplotlib.tri import Triangulation


class TriAnalyzer:
    """
    Define basic tools for triangular mesh analysis and improvement.

    A TriAnalyzer encapsulates a `.Triangulation` object and provides basic
    tools for mesh analysis and mesh improvement.

    Attributes
    ----------
    scale_factors

    Parameters
    ----------
    triangulation : `~matplotlib.tri.Triangulation`
        The encapsulated triangulation to analyze.
    """

    def __init__(self, triangulation):
        _api.check_isinstance(Triangulation, triangulation=triangulation)
        self._triangulation = triangulation

    @property
    def scale_factors(self):
        """
        Factors to rescale the triangulation into a unit square.

        Returns
        -------
        (float, float)
            Scaling factors (kx, ky) so that the triangulation
            ``[triangulation.x * kx, triangulation.y * ky]``
            fits exactly inside a unit square.
        """
        compressed_triangles = self._triangulation.get_masked_triangles()
        node_used = (np.bincount(np.ravel(compressed_triangles),
                                 minlength=self._triangulation.x.size) != 0)
        return (1 / np.ptp(self._triangulation.x[node_used]),
                1 / np.ptp(self._triangulation.y[node_used]))

    def circle_ratios(self, rescale=True):
        """
        Return a measure of the triangulation triangles flatness.

        The ratio of the incircle radius over the circumcircle radius is a
        widely used indicator of a triangle flatness.
        It is always ``<= 0.5`` and ``== 0.5`` only for equilateral
        triangles. Circle ratios below 0.01 denote very flat triangles.

        To avoid unduly low values due to a difference of scale between the 2
        axis, the triangular mesh can first be rescaled to fit inside a unit
        square with `scale_factors` (Only if *rescale* is True, which is
        its default value).

        Parameters
        ----------
        rescale : bool, default: True
            If True, internally rescale (based on `scale_factors`), so that the
            (unmasked) triangles fit exactly inside a unit square mesh.

        Returns
        -------
        masked array
            Ratio of the incircle radius over the circumcircle radius, for
            each 'rescaled' triangle of the encapsulated triangulation.
            Values corresponding to masked triangles are masked out.

        """
        # Coords rescaling
        if rescale:
            (kx, ky) = self.scale_factors
        else:
            (kx, ky) = (1.0, 1.0)
        pts = np.vstack([self._triangulation.x*kx,
                         self._triangulation.y*ky]).T
        tri_pts = pts[self._triangulation.triangles]
        # Computes the 3 side lengths
        a = tri_pts[:, 1, :] - tri_pts[:, 0, :]
        b = tri_pts[:, 2, :] - tri_pts[:, 1, :]
        c = tri_pts[:, 0, :] - tri_pts[:, 2, :]
        a = np.hypot(a[:, 0], a[:, 1])
        b = np.hypot(b[:, 0], b[:, 1])
        c = np.hypot(c[:, 0], c[:, 1])
        # circumcircle and incircle radii
        s = (a+b+c)*0.5
        prod = s*(a+b-s)*(a+c-s)*(b+c-s)
        # We have to deal with flat triangles with infinite circum_radius
        bool_flat = (prod == 0.)
        if np.any(bool_flat):
            # Pathologic flow
            ntri = tri_pts.shape[0]
            circum_radius = np.empty(ntri, dtype=np.float64)
            circum_radius[bool_flat] = np.inf
            abc = a*b*c
            circum_radius[~bool_flat] = abc[~bool_flat] / (
                4.0*np.sqrt(prod[~bool_flat]))
        else:
            # Normal optimized flow
            circum_radius = (a*b*c) / (4.0*np.sqrt(prod))
        in_radius = (a*b*c) / (4.0*circum_radius*s)
        circle_ratio = in_radius/circum_radius
        mask = self._triangulation.mask
        if mask is None:
            return circle_ratio
        else:
            return np.ma.array(circle_ratio, mask=mask)

    def get_flat_tri_mask(self, min_circle_ratio=0.01, rescale=True):
        """
        Eliminate excessively flat border triangles from the triangulation.

        Returns a mask *new_mask* which allows to clean the encapsulated
        triangulation from its border-located flat triangles
        (according to their :meth:`circle_ratios`).
        This mask is meant to be subsequently applied to the triangulation
        using `.Triangulation.set_mask`.
        *new_mask* is an extension of the initial triangulation mask
        in the sense that an initially masked triangle will remain masked.

        The *new_mask* array is computed recursively; at each step flat
        triangles are removed only if they share a side with the current mesh
        border. Thus, no new holes in the triangulated domain will be created.

        Parameters
        ----------
        min_circle_ratio : float, default: 0.01
            Border triangles with incircle/circumcircle radii ratio r/R will
            be removed if r/R < *min_circle_ratio*.
        rescale : bool, default: True
            If True, first, internally rescale (based on `scale_factors`) so
            that the (unmasked) triangles fit exactly inside a unit square
            mesh.  This rescaling accounts for the difference of scale which
            might exist between the 2 axis.

        Returns
        -------
        array of bool
            Mask to apply to encapsulated triangulation.
            All the initially masked triangles remain masked in the
            *new_mask*.

        Notes
        -----
        The rationale behind this function is that a Delaunay
        triangulation - of an unstructured set of points - sometimes contains
        almost flat triangles at its border, leading to artifacts in plots
        (especially for high-resolution contouring).
        Masked with computed *new_mask*, the encapsulated
        triangulation would contain no more unmasked border triangles
        with a circle ratio below *min_circle_ratio*, thus improving the
        mesh quality for subsequent plots or interpolation.
        """
        # Recursively computes the mask_current_borders, true if a triangle is
        # at the border of the mesh OR touching the border through a chain of
        # invalid aspect ratio masked_triangles.
        ntri = self._triangulation.triangles.shape[0]
        mask_bad_ratio = self.circle_ratios(rescale) < min_circle_ratio

        current_mask = self._triangulation.mask
        if current_mask is None:
            current_mask = np.zeros(ntri, dtype=bool)
        valid_neighbors = np.copy(self._triangulation.neighbors)
        renum_neighbors = np.arange(ntri, dtype=np.int32)
        nadd = -1
        while nadd != 0:
            # The active wavefront is the triangles from the border (unmasked
            # but with a least 1 neighbor equal to -1
            wavefront = (np.min(valid_neighbors, axis=1) == -1) & ~current_mask
            # The element from the active wavefront will be masked if their
            # circle ratio is bad.
            added_mask = wavefront & mask_bad_ratio
            current_mask = added_mask | current_mask
            nadd = np.sum(added_mask)

            # now we have to update the tables valid_neighbors
            valid_neighbors[added_mask, :] = -1
            renum_neighbors[added_mask] = -1
            valid_neighbors = np.where(valid_neighbors == -1, -1,
                                       renum_neighbors[valid_neighbors])

        return np.ma.filled(current_mask, True)

    def _get_compressed_triangulation(self):
        """
        Compress (if masked) the encapsulated triangulation.

        Returns minimal-length triangles array (*compressed_triangles*) and
        coordinates arrays (*compressed_x*, *compressed_y*) that can still
        describe the unmasked triangles of the encapsulated triangulation.

        Returns
        -------
        compressed_triangles : array-like
            the returned compressed triangulation triangles
        compressed_x : array-like
            the returned compressed triangulation 1st coordinate
        compressed_y : array-like
            the returned compressed triangulation 2nd coordinate
        tri_renum : int array
            renumbering table to translate the triangle numbers from the
            encapsulated triangulation into the new (compressed) renumbering.
            -1 for masked triangles (deleted from *compressed_triangles*).
        node_renum : int array
            renumbering table to translate the point numbers from the
            encapsulated triangulation into the new (compressed) renumbering.
            -1 for unused points (i.e. those deleted from *compressed_x* and
            *compressed_y*).

        """
        # Valid triangles and renumbering
        tri_mask = self._triangulation.mask
        compressed_triangles = self._triangulation.get_masked_triangles()
        ntri = self._triangulation.triangles.shape[0]
        if tri_mask is not None:
            tri_renum = self._total_to_compress_renum(~tri_mask)
        else:
            tri_renum = np.arange(ntri, dtype=np.int32)

        # Valid nodes and renumbering
        valid_node = (np.bincount(np.ravel(compressed_triangles),
                                  minlength=self._triangulation.x.size) != 0)
        compressed_x = self._triangulation.x[valid_node]
        compressed_y = self._triangulation.y[valid_node]
        node_renum = self._total_to_compress_renum(valid_node)

        # Now renumbering the valid triangles nodes
        compressed_triangles = node_renum[compressed_triangles]

        return (compressed_triangles, compressed_x, compressed_y, tri_renum,
                node_renum)

    @staticmethod
    def _total_to_compress_renum(valid):
        """
        Parameters
        ----------
        valid : 1D bool array
            Validity mask.

        Returns
        -------
        int array
            Array so that (`valid_array` being a compressed array
            based on a `masked_array` with mask ~*valid*):

            - For all i with valid[i] = True:
              valid_array[renum[i]] = masked_array[i]
            - For all i with valid[i] = False:
              renum[i] = -1 (invalid value)
        """
        renum = np.full(np.size(valid), -1, dtype=np.int32)
        n_valid = np.sum(valid)
        renum[valid] = np.arange(n_valid, dtype=np.int32)
        return renum

# === NexusCore/openenv\Lib\site-packages\nltk\translate\gale_church.py ===
# Natural Language Toolkit: Gale-Church Aligner
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Torsten Marek <marek@ifi.uzh.ch>
# Contributor: Cassidy Laidlaw, Liling Tan
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""

A port of the Gale-Church Aligner.

Gale & Church (1993), A Program for Aligning Sentences in Bilingual Corpora.
https://aclweb.org/anthology/J93-1004.pdf

"""

import math

try:
    from norm import logsf as norm_logsf
    from scipy.stats import norm
except ImportError:

    def erfcc(x):
        """Complementary error function."""
        z = abs(x)
        t = 1 / (1 + 0.5 * z)
        r = t * math.exp(
            -z * z
            - 1.26551223
            + t
            * (
                1.00002368
                + t
                * (
                    0.37409196
                    + t
                    * (
                        0.09678418
                        + t
                        * (
                            -0.18628806
                            + t
                            * (
                                0.27886807
                                + t
                                * (
                                    -1.13520398
                                    + t
                                    * (1.48851587 + t * (-0.82215223 + t * 0.17087277))
                                )
                            )
                        )
                    )
                )
            )
        )
        if x >= 0.0:
            return r
        else:
            return 2.0 - r

    def norm_cdf(x):
        """Return the area under the normal distribution from M{-∞..x}."""
        return 1 - 0.5 * erfcc(x / math.sqrt(2))

    def norm_logsf(x):
        try:
            return math.log(1 - norm_cdf(x))
        except ValueError:
            return float("-inf")


LOG2 = math.log(2)


class LanguageIndependent:
    # These are the language-independent probabilities and parameters
    # given in Gale & Church

    # for the computation, l_1 is always the language with less characters
    PRIORS = {
        (1, 0): 0.0099,
        (0, 1): 0.0099,
        (1, 1): 0.89,
        (2, 1): 0.089,
        (1, 2): 0.089,
        (2, 2): 0.011,
    }

    AVERAGE_CHARACTERS = 1
    VARIANCE_CHARACTERS = 6.8


def trace(backlinks, source_sents_lens, target_sents_lens):
    """
    Traverse the alignment cost from the tracebacks and retrieves
    appropriate sentence pairs.

    :param backlinks: A dictionary where the key is the alignment points and value is the cost (referencing the LanguageIndependent.PRIORS)
    :type backlinks: dict
    :param source_sents_lens: A list of target sentences' lengths
    :type source_sents_lens: list(int)
    :param target_sents_lens: A list of target sentences' lengths
    :type target_sents_lens: list(int)
    """
    links = []
    position = (len(source_sents_lens), len(target_sents_lens))
    while position != (0, 0) and all(p >= 0 for p in position):
        try:
            s, t = backlinks[position]
        except TypeError:
            position = (position[0] - 1, position[1] - 1)
            continue
        for i in range(s):
            for j in range(t):
                links.append((position[0] - i - 1, position[1] - j - 1))
        position = (position[0] - s, position[1] - t)

    return links[::-1]


def align_log_prob(i, j, source_sents, target_sents, alignment, params):
    """Returns the log probability of the two sentences C{source_sents[i]}, C{target_sents[j]}
    being aligned with a specific C{alignment}.

    @param i: The offset of the source sentence.
    @param j: The offset of the target sentence.
    @param source_sents: The list of source sentence lengths.
    @param target_sents: The list of target sentence lengths.
    @param alignment: The alignment type, a tuple of two integers.
    @param params: The sentence alignment parameters.

    @returns: The log probability of a specific alignment between the two sentences, given the parameters.
    """
    l_s = sum(source_sents[i - offset - 1] for offset in range(alignment[0]))
    l_t = sum(target_sents[j - offset - 1] for offset in range(alignment[1]))
    try:
        # actually, the paper says l_s * params.VARIANCE_CHARACTERS, this is based on the C
        # reference implementation. With l_s in the denominator, insertions are impossible.
        m = (l_s + l_t / params.AVERAGE_CHARACTERS) / 2
        delta = (l_s * params.AVERAGE_CHARACTERS - l_t) / math.sqrt(
            m * params.VARIANCE_CHARACTERS
        )
    except ZeroDivisionError:
        return float("-inf")

    return -(LOG2 + norm_logsf(abs(delta)) + math.log(params.PRIORS[alignment]))


def align_blocks(source_sents_lens, target_sents_lens, params=LanguageIndependent):
    """Return the sentence alignment of two text blocks (usually paragraphs).

        >>> align_blocks([5,5,5], [7,7,7])
        [(0, 0), (1, 1), (2, 2)]
        >>> align_blocks([10,5,5], [12,20])
        [(0, 0), (1, 1), (2, 1)]
        >>> align_blocks([12,20], [10,5,5])
        [(0, 0), (1, 1), (1, 2)]
        >>> align_blocks([10,2,10,10,2,10], [12,3,20,3,12])
        [(0, 0), (1, 1), (2, 2), (3, 2), (4, 3), (5, 4)]

    @param source_sents_lens: The list of source sentence lengths.
    @param target_sents_lens: The list of target sentence lengths.
    @param params: the sentence alignment parameters.
    @return: The sentence alignments, a list of index pairs.
    """

    alignment_types = list(params.PRIORS.keys())

    # there are always three rows in the history (with the last of them being filled)
    D = [[]]

    backlinks = {}

    for i in range(len(source_sents_lens) + 1):
        for j in range(len(target_sents_lens) + 1):
            min_dist = float("inf")
            min_align = None
            for a in alignment_types:
                prev_i = -1 - a[0]
                prev_j = j - a[1]
                if prev_i < -len(D) or prev_j < 0:
                    continue
                p = D[prev_i][prev_j] + align_log_prob(
                    i, j, source_sents_lens, target_sents_lens, a, params
                )
                if p < min_dist:
                    min_dist = p
                    min_align = a

            if min_dist == float("inf"):
                min_dist = 0

            backlinks[(i, j)] = min_align
            D[-1].append(min_dist)

        if len(D) > 2:
            D.pop(0)
        D.append([])

    return trace(backlinks, source_sents_lens, target_sents_lens)


def align_texts(source_blocks, target_blocks, params=LanguageIndependent):
    """Creates the sentence alignment of two texts.

    Texts can consist of several blocks. Block boundaries cannot be crossed by sentence
    alignment links.

    Each block consists of a list that contains the lengths (in characters) of the sentences
    in this block.

    @param source_blocks: The list of blocks in the source text.
    @param target_blocks: The list of blocks in the target text.
    @param params: the sentence alignment parameters.

    @returns: A list of sentence alignment lists
    """
    if len(source_blocks) != len(target_blocks):
        raise ValueError(
            "Source and target texts do not have the same number of blocks."
        )

    return [
        align_blocks(source_block, target_block, params)
        for source_block, target_block in zip(source_blocks, target_blocks)
    ]


# File I/O functions; may belong in a corpus reader


def split_at(it, split_value):
    """Splits an iterator C{it} at values of C{split_value}.

    Each instance of C{split_value} is swallowed. The iterator produces
    subiterators which need to be consumed fully before the next subiterator
    can be used.
    """

    def _chunk_iterator(first):
        v = first
        while v != split_value:
            yield v
            v = it.next()

    while True:
        yield _chunk_iterator(it.next())


def parse_token_stream(stream, soft_delimiter, hard_delimiter):
    """Parses a stream of tokens and splits it into sentences (using C{soft_delimiter} tokens)
    and blocks (using C{hard_delimiter} tokens) for use with the L{align_texts} function.
    """
    return [
        [
            sum(len(token) for token in sentence_it)
            for sentence_it in split_at(block_it, soft_delimiter)
        ]
        for block_it in split_at(stream, hard_delimiter)
    ]

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\packaging\_manylinux.py ===
from __future__ import annotations

import collections
import contextlib
import functools
import os
import re
import sys
import warnings
from typing import Generator, Iterator, NamedTuple, Sequence

from ._elffile import EIClass, EIData, ELFFile, EMachine

EF_ARM_ABIMASK = 0xFF000000
EF_ARM_ABI_VER5 = 0x05000000
EF_ARM_ABI_FLOAT_HARD = 0x00000400


# `os.PathLike` not a generic type until Python 3.9, so sticking with `str`
# as the type for `path` until then.
@contextlib.contextmanager
def _parse_elf(path: str) -> Generator[ELFFile | None, None, None]:
    try:
        with open(path, "rb") as f:
            yield ELFFile(f)
    except (OSError, TypeError, ValueError):
        yield None


def _is_linux_armhf(executable: str) -> bool:
    # hard-float ABI can be detected from the ELF header of the running
    # process
    # https://static.docs.arm.com/ihi0044/g/aaelf32.pdf
    with _parse_elf(executable) as f:
        return (
            f is not None
            and f.capacity == EIClass.C32
            and f.encoding == EIData.Lsb
            and f.machine == EMachine.Arm
            and f.flags & EF_ARM_ABIMASK == EF_ARM_ABI_VER5
            and f.flags & EF_ARM_ABI_FLOAT_HARD == EF_ARM_ABI_FLOAT_HARD
        )


def _is_linux_i686(executable: str) -> bool:
    with _parse_elf(executable) as f:
        return (
            f is not None
            and f.capacity == EIClass.C32
            and f.encoding == EIData.Lsb
            and f.machine == EMachine.I386
        )


def _have_compatible_abi(executable: str, archs: Sequence[str]) -> bool:
    if "armv7l" in archs:
        return _is_linux_armhf(executable)
    if "i686" in archs:
        return _is_linux_i686(executable)
    allowed_archs = {
        "x86_64",
        "aarch64",
        "ppc64",
        "ppc64le",
        "s390x",
        "loongarch64",
        "riscv64",
    }
    return any(arch in allowed_archs for arch in archs)


# If glibc ever changes its major version, we need to know what the last
# minor version was, so we can build the complete list of all versions.
# For now, guess what the highest minor version might be, assume it will
# be 50 for testing. Once this actually happens, update the dictionary
# with the actual value.
_LAST_GLIBC_MINOR: dict[int, int] = collections.defaultdict(lambda: 50)


class _GLibCVersion(NamedTuple):
    major: int
    minor: int


def _glibc_version_string_confstr() -> str | None:
    """
    Primary implementation of glibc_version_string using os.confstr.
    """
    # os.confstr is quite a bit faster than ctypes.DLL. It's also less likely
    # to be broken or missing. This strategy is used in the standard library
    # platform module.
    # https://github.com/python/cpython/blob/fcf1d003bf4f0100c/Lib/platform.py#L175-L183
    try:
        # Should be a string like "glibc 2.17".
        version_string: str | None = os.confstr("CS_GNU_LIBC_VERSION")
        assert version_string is not None
        _, version = version_string.rsplit()
    except (AssertionError, AttributeError, OSError, ValueError):
        # os.confstr() or CS_GNU_LIBC_VERSION not available (or a bad value)...
        return None
    return version


def _glibc_version_string_ctypes() -> str | None:
    """
    Fallback implementation of glibc_version_string using ctypes.
    """
    try:
        import ctypes
    except ImportError:
        return None

    # ctypes.CDLL(None) internally calls dlopen(NULL), and as the dlopen
    # manpage says, "If filename is NULL, then the returned handle is for the
    # main program". This way we can let the linker do the work to figure out
    # which libc our process is actually using.
    #
    # We must also handle the special case where the executable is not a
    # dynamically linked executable. This can occur when using musl libc,
    # for example. In this situation, dlopen() will error, leading to an
    # OSError. Interestingly, at least in the case of musl, there is no
    # errno set on the OSError. The single string argument used to construct
    # OSError comes from libc itself and is therefore not portable to
    # hard code here. In any case, failure to call dlopen() means we
    # can proceed, so we bail on our attempt.
    try:
        process_namespace = ctypes.CDLL(None)
    except OSError:
        return None

    try:
        gnu_get_libc_version = process_namespace.gnu_get_libc_version
    except AttributeError:
        # Symbol doesn't exist -> therefore, we are not linked to
        # glibc.
        return None

    # Call gnu_get_libc_version, which returns a string like "2.5"
    gnu_get_libc_version.restype = ctypes.c_char_p
    version_str: str = gnu_get_libc_version()
    # py2 / py3 compatibility:
    if not isinstance(version_str, str):
        version_str = version_str.decode("ascii")

    return version_str


def _glibc_version_string() -> str | None:
    """Returns glibc version string, or None if not using glibc."""
    return _glibc_version_string_confstr() or _glibc_version_string_ctypes()


def _parse_glibc_version(version_str: str) -> tuple[int, int]:
    """Parse glibc version.

    We use a regexp instead of str.split because we want to discard any
    random junk that might come after the minor version -- this might happen
    in patched/forked versions of glibc (e.g. Linaro's version of glibc
    uses version strings like "2.20-2014.11"). See gh-3588.
    """
    m = re.match(r"(?P<major>[0-9]+)\.(?P<minor>[0-9]+)", version_str)
    if not m:
        warnings.warn(
            f"Expected glibc version with 2 components major.minor,"
            f" got: {version_str}",
            RuntimeWarning,
            stacklevel=2,
        )
        return -1, -1
    return int(m.group("major")), int(m.group("minor"))


@functools.lru_cache
def _get_glibc_version() -> tuple[int, int]:
    version_str = _glibc_version_string()
    if version_str is None:
        return (-1, -1)
    return _parse_glibc_version(version_str)


# From PEP 513, PEP 600
def _is_compatible(arch: str, version: _GLibCVersion) -> bool:
    sys_glibc = _get_glibc_version()
    if sys_glibc < version:
        return False
    # Check for presence of _manylinux module.
    try:
        import _manylinux
    except ImportError:
        return True
    if hasattr(_manylinux, "manylinux_compatible"):
        result = _manylinux.manylinux_compatible(version[0], version[1], arch)
        if result is not None:
            return bool(result)
        return True
    if version == _GLibCVersion(2, 5):
        if hasattr(_manylinux, "manylinux1_compatible"):
            return bool(_manylinux.manylinux1_compatible)
    if version == _GLibCVersion(2, 12):
        if hasattr(_manylinux, "manylinux2010_compatible"):
            return bool(_manylinux.manylinux2010_compatible)
    if version == _GLibCVersion(2, 17):
        if hasattr(_manylinux, "manylinux2014_compatible"):
            return bool(_manylinux.manylinux2014_compatible)
    return True


_LEGACY_MANYLINUX_MAP = {
    # CentOS 7 w/ glibc 2.17 (PEP 599)
    (2, 17): "manylinux2014",
    # CentOS 6 w/ glibc 2.12 (PEP 571)
    (2, 12): "manylinux2010",
    # CentOS 5 w/ glibc 2.5 (PEP 513)
    (2, 5): "manylinux1",
}


def platform_tags(archs: Sequence[str]) -> Iterator[str]:
    """Generate manylinux tags compatible to the current platform.

    :param archs: Sequence of compatible architectures.
        The first one shall be the closest to the actual architecture and be the part of
        platform tag after the ``linux_`` prefix, e.g. ``x86_64``.
        The ``linux_`` prefix is assumed as a prerequisite for the current platform to
        be manylinux-compatible.

    :returns: An iterator of compatible manylinux tags.
    """
    if not _have_compatible_abi(sys.executable, archs):
        return
    # Oldest glibc to be supported regardless of architecture is (2, 17).
    too_old_glibc2 = _GLibCVersion(2, 16)
    if set(archs) & {"x86_64", "i686"}:
        # On x86/i686 also oldest glibc to be supported is (2, 5).
        too_old_glibc2 = _GLibCVersion(2, 4)
    current_glibc = _GLibCVersion(*_get_glibc_version())
    glibc_max_list = [current_glibc]
    # We can assume compatibility across glibc major versions.
    # https://sourceware.org/bugzilla/show_bug.cgi?id=24636
    #
    # Build a list of maximum glibc versions so that we can
    # output the canonical list of all glibc from current_glibc
    # down to too_old_glibc2, including all intermediary versions.
    for glibc_major in range(current_glibc.major - 1, 1, -1):
        glibc_minor = _LAST_GLIBC_MINOR[glibc_major]
        glibc_max_list.append(_GLibCVersion(glibc_major, glibc_minor))
    for arch in archs:
        for glibc_max in glibc_max_list:
            if glibc_max.major == too_old_glibc2.major:
                min_minor = too_old_glibc2.minor
            else:
                # For other glibc major versions oldest supported is (x, 0).
                min_minor = -1
            for glibc_minor in range(glibc_max.minor, min_minor, -1):
                glibc_version = _GLibCVersion(glibc_max.major, glibc_minor)
                tag = "manylinux_{}_{}".format(*glibc_version)
                if _is_compatible(arch, glibc_version):
                    yield f"{tag}_{arch}"
                # Handle the legacy manylinux1, manylinux2010, manylinux2014 tags.
                if glibc_version in _LEGACY_MANYLINUX_MAP:
                    legacy_tag = _LEGACY_MANYLINUX_MAP[glibc_version]
                    if _is_compatible(arch, glibc_version):
                        yield f"{legacy_tag}_{arch}"

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\packaging\_manylinux.py ===
from __future__ import annotations

import collections
import contextlib
import functools
import os
import re
import sys
import warnings
from typing import Generator, Iterator, NamedTuple, Sequence

from ._elffile import EIClass, EIData, ELFFile, EMachine

EF_ARM_ABIMASK = 0xFF000000
EF_ARM_ABI_VER5 = 0x05000000
EF_ARM_ABI_FLOAT_HARD = 0x00000400


# `os.PathLike` not a generic type until Python 3.9, so sticking with `str`
# as the type for `path` until then.
@contextlib.contextmanager
def _parse_elf(path: str) -> Generator[ELFFile | None, None, None]:
    try:
        with open(path, "rb") as f:
            yield ELFFile(f)
    except (OSError, TypeError, ValueError):
        yield None


def _is_linux_armhf(executable: str) -> bool:
    # hard-float ABI can be detected from the ELF header of the running
    # process
    # https://static.docs.arm.com/ihi0044/g/aaelf32.pdf
    with _parse_elf(executable) as f:
        return (
            f is not None
            and f.capacity == EIClass.C32
            and f.encoding == EIData.Lsb
            and f.machine == EMachine.Arm
            and f.flags & EF_ARM_ABIMASK == EF_ARM_ABI_VER5
            and f.flags & EF_ARM_ABI_FLOAT_HARD == EF_ARM_ABI_FLOAT_HARD
        )


def _is_linux_i686(executable: str) -> bool:
    with _parse_elf(executable) as f:
        return (
            f is not None
            and f.capacity == EIClass.C32
            and f.encoding == EIData.Lsb
            and f.machine == EMachine.I386
        )


def _have_compatible_abi(executable: str, archs: Sequence[str]) -> bool:
    if "armv7l" in archs:
        return _is_linux_armhf(executable)
    if "i686" in archs:
        return _is_linux_i686(executable)
    allowed_archs = {
        "x86_64",
        "aarch64",
        "ppc64",
        "ppc64le",
        "s390x",
        "loongarch64",
        "riscv64",
    }
    return any(arch in allowed_archs for arch in archs)


# If glibc ever changes its major version, we need to know what the last
# minor version was, so we can build the complete list of all versions.
# For now, guess what the highest minor version might be, assume it will
# be 50 for testing. Once this actually happens, update the dictionary
# with the actual value.
_LAST_GLIBC_MINOR: dict[int, int] = collections.defaultdict(lambda: 50)


class _GLibCVersion(NamedTuple):
    major: int
    minor: int


def _glibc_version_string_confstr() -> str | None:
    """
    Primary implementation of glibc_version_string using os.confstr.
    """
    # os.confstr is quite a bit faster than ctypes.DLL. It's also less likely
    # to be broken or missing. This strategy is used in the standard library
    # platform module.
    # https://github.com/python/cpython/blob/fcf1d003bf4f0100c/Lib/platform.py#L175-L183
    try:
        # Should be a string like "glibc 2.17".
        version_string: str | None = os.confstr("CS_GNU_LIBC_VERSION")
        assert version_string is not None
        _, version = version_string.rsplit()
    except (AssertionError, AttributeError, OSError, ValueError):
        # os.confstr() or CS_GNU_LIBC_VERSION not available (or a bad value)...
        return None
    return version


def _glibc_version_string_ctypes() -> str | None:
    """
    Fallback implementation of glibc_version_string using ctypes.
    """
    try:
        import ctypes
    except ImportError:
        return None

    # ctypes.CDLL(None) internally calls dlopen(NULL), and as the dlopen
    # manpage says, "If filename is NULL, then the returned handle is for the
    # main program". This way we can let the linker do the work to figure out
    # which libc our process is actually using.
    #
    # We must also handle the special case where the executable is not a
    # dynamically linked executable. This can occur when using musl libc,
    # for example. In this situation, dlopen() will error, leading to an
    # OSError. Interestingly, at least in the case of musl, there is no
    # errno set on the OSError. The single string argument used to construct
    # OSError comes from libc itself and is therefore not portable to
    # hard code here. In any case, failure to call dlopen() means we
    # can proceed, so we bail on our attempt.
    try:
        process_namespace = ctypes.CDLL(None)
    except OSError:
        return None

    try:
        gnu_get_libc_version = process_namespace.gnu_get_libc_version
    except AttributeError:
        # Symbol doesn't exist -> therefore, we are not linked to
        # glibc.
        return None

    # Call gnu_get_libc_version, which returns a string like "2.5"
    gnu_get_libc_version.restype = ctypes.c_char_p
    version_str: str = gnu_get_libc_version()
    # py2 / py3 compatibility:
    if not isinstance(version_str, str):
        version_str = version_str.decode("ascii")

    return version_str


def _glibc_version_string() -> str | None:
    """Returns glibc version string, or None if not using glibc."""
    return _glibc_version_string_confstr() or _glibc_version_string_ctypes()


def _parse_glibc_version(version_str: str) -> tuple[int, int]:
    """Parse glibc version.

    We use a regexp instead of str.split because we want to discard any
    random junk that might come after the minor version -- this might happen
    in patched/forked versions of glibc (e.g. Linaro's version of glibc
    uses version strings like "2.20-2014.11"). See gh-3588.
    """
    m = re.match(r"(?P<major>[0-9]+)\.(?P<minor>[0-9]+)", version_str)
    if not m:
        warnings.warn(
            f"Expected glibc version with 2 components major.minor,"
            f" got: {version_str}",
            RuntimeWarning,
            stacklevel=2,
        )
        return -1, -1
    return int(m.group("major")), int(m.group("minor"))


@functools.lru_cache
def _get_glibc_version() -> tuple[int, int]:
    version_str = _glibc_version_string()
    if version_str is None:
        return (-1, -1)
    return _parse_glibc_version(version_str)


# From PEP 513, PEP 600
def _is_compatible(arch: str, version: _GLibCVersion) -> bool:
    sys_glibc = _get_glibc_version()
    if sys_glibc < version:
        return False
    # Check for presence of _manylinux module.
    try:
        import _manylinux
    except ImportError:
        return True
    if hasattr(_manylinux, "manylinux_compatible"):
        result = _manylinux.manylinux_compatible(version[0], version[1], arch)
        if result is not None:
            return bool(result)
        return True
    if version == _GLibCVersion(2, 5):
        if hasattr(_manylinux, "manylinux1_compatible"):
            return bool(_manylinux.manylinux1_compatible)
    if version == _GLibCVersion(2, 12):
        if hasattr(_manylinux, "manylinux2010_compatible"):
            return bool(_manylinux.manylinux2010_compatible)
    if version == _GLibCVersion(2, 17):
        if hasattr(_manylinux, "manylinux2014_compatible"):
            return bool(_manylinux.manylinux2014_compatible)
    return True


_LEGACY_MANYLINUX_MAP = {
    # CentOS 7 w/ glibc 2.17 (PEP 599)
    (2, 17): "manylinux2014",
    # CentOS 6 w/ glibc 2.12 (PEP 571)
    (2, 12): "manylinux2010",
    # CentOS 5 w/ glibc 2.5 (PEP 513)
    (2, 5): "manylinux1",
}


def platform_tags(archs: Sequence[str]) -> Iterator[str]:
    """Generate manylinux tags compatible to the current platform.

    :param archs: Sequence of compatible architectures.
        The first one shall be the closest to the actual architecture and be the part of
        platform tag after the ``linux_`` prefix, e.g. ``x86_64``.
        The ``linux_`` prefix is assumed as a prerequisite for the current platform to
        be manylinux-compatible.

    :returns: An iterator of compatible manylinux tags.
    """
    if not _have_compatible_abi(sys.executable, archs):
        return
    # Oldest glibc to be supported regardless of architecture is (2, 17).
    too_old_glibc2 = _GLibCVersion(2, 16)
    if set(archs) & {"x86_64", "i686"}:
        # On x86/i686 also oldest glibc to be supported is (2, 5).
        too_old_glibc2 = _GLibCVersion(2, 4)
    current_glibc = _GLibCVersion(*_get_glibc_version())
    glibc_max_list = [current_glibc]
    # We can assume compatibility across glibc major versions.
    # https://sourceware.org/bugzilla/show_bug.cgi?id=24636
    #
    # Build a list of maximum glibc versions so that we can
    # output the canonical list of all glibc from current_glibc
    # down to too_old_glibc2, including all intermediary versions.
    for glibc_major in range(current_glibc.major - 1, 1, -1):
        glibc_minor = _LAST_GLIBC_MINOR[glibc_major]
        glibc_max_list.append(_GLibCVersion(glibc_major, glibc_minor))
    for arch in archs:
        for glibc_max in glibc_max_list:
            if glibc_max.major == too_old_glibc2.major:
                min_minor = too_old_glibc2.minor
            else:
                # For other glibc major versions oldest supported is (x, 0).
                min_minor = -1
            for glibc_minor in range(glibc_max.minor, min_minor, -1):
                glibc_version = _GLibCVersion(glibc_max.major, glibc_minor)
                tag = "manylinux_{}_{}".format(*glibc_version)
                if _is_compatible(arch, glibc_version):
                    yield f"{tag}_{arch}"
                # Handle the legacy manylinux1, manylinux2010, manylinux2014 tags.
                if glibc_version in _LEGACY_MANYLINUX_MAP:
                    legacy_tag = _LEGACY_MANYLINUX_MAP[glibc_version]
                    if _is_compatible(arch, glibc_version):
                        yield f"{legacy_tag}_{arch}"

# === NexusCore/openenv\Lib\site-packages\matplotlib\_animation_data.py ===
# JavaScript template for HTMLWriter
JS_INCLUDE = """
<link rel="stylesheet"
href="https://maxcdn.bootstrapcdn.com/font-awesome/4.4.0/css/font-awesome.min.css">
<script language="javascript">
  function isInternetExplorer() {
    ua = navigator.userAgent;
    /* MSIE used to detect old browsers and Trident used to newer ones*/
    return ua.indexOf("MSIE ") > -1 || ua.indexOf("Trident/") > -1;
  }

  /* Define the Animation class */
  function Animation(frames, img_id, slider_id, interval, loop_select_id){
    this.img_id = img_id;
    this.slider_id = slider_id;
    this.loop_select_id = loop_select_id;
    this.interval = interval;
    this.current_frame = 0;
    this.direction = 0;
    this.timer = null;
    this.frames = new Array(frames.length);

    for (var i=0; i<frames.length; i++)
    {
     this.frames[i] = new Image();
     this.frames[i].src = frames[i];
    }
    var slider = document.getElementById(this.slider_id);
    slider.max = this.frames.length - 1;
    if (isInternetExplorer()) {
        // switch from oninput to onchange because IE <= 11 does not conform
        // with W3C specification. It ignores oninput and onchange behaves
        // like oninput. In contrast, Microsoft Edge behaves correctly.
        slider.setAttribute('onchange', slider.getAttribute('oninput'));
        slider.setAttribute('oninput', null);
    }
    this.set_frame(this.current_frame);
  }

  Animation.prototype.get_loop_state = function(){
    var button_group = document[this.loop_select_id].state;
    for (var i = 0; i < button_group.length; i++) {
        var button = button_group[i];
        if (button.checked) {
            return button.value;
        }
    }
    return undefined;
  }

  Animation.prototype.set_frame = function(frame){
    this.current_frame = frame;
    document.getElementById(this.img_id).src =
            this.frames[this.current_frame].src;
    document.getElementById(this.slider_id).value = this.current_frame;
  }

  Animation.prototype.next_frame = function()
  {
    this.set_frame(Math.min(this.frames.length - 1, this.current_frame + 1));
  }

  Animation.prototype.previous_frame = function()
  {
    this.set_frame(Math.max(0, this.current_frame - 1));
  }

  Animation.prototype.first_frame = function()
  {
    this.set_frame(0);
  }

  Animation.prototype.last_frame = function()
  {
    this.set_frame(this.frames.length - 1);
  }

  Animation.prototype.slower = function()
  {
    this.interval /= 0.7;
    if(this.direction > 0){this.play_animation();}
    else if(this.direction < 0){this.reverse_animation();}
  }

  Animation.prototype.faster = function()
  {
    this.interval *= 0.7;
    if(this.direction > 0){this.play_animation();}
    else if(this.direction < 0){this.reverse_animation();}
  }

  Animation.prototype.anim_step_forward = function()
  {
    this.current_frame += 1;
    if(this.current_frame < this.frames.length){
      this.set_frame(this.current_frame);
    }else{
      var loop_state = this.get_loop_state();
      if(loop_state == "loop"){
        this.first_frame();
      }else if(loop_state == "reflect"){
        this.last_frame();
        this.reverse_animation();
      }else{
        this.pause_animation();
        this.last_frame();
      }
    }
  }

  Animation.prototype.anim_step_reverse = function()
  {
    this.current_frame -= 1;
    if(this.current_frame >= 0){
      this.set_frame(this.current_frame);
    }else{
      var loop_state = this.get_loop_state();
      if(loop_state == "loop"){
        this.last_frame();
      }else if(loop_state == "reflect"){
        this.first_frame();
        this.play_animation();
      }else{
        this.pause_animation();
        this.first_frame();
      }
    }
  }

  Animation.prototype.pause_animation = function()
  {
    this.direction = 0;
    if (this.timer){
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  Animation.prototype.play_animation = function()
  {
    this.pause_animation();
    this.direction = 1;
    var t = this;
    if (!this.timer) this.timer = setInterval(function() {
        t.anim_step_forward();
    }, this.interval);
  }

  Animation.prototype.reverse_animation = function()
  {
    this.pause_animation();
    this.direction = -1;
    var t = this;
    if (!this.timer) this.timer = setInterval(function() {
        t.anim_step_reverse();
    }, this.interval);
  }
</script>
"""


# Style definitions for the HTML template
STYLE_INCLUDE = """
<style>
.animation {
    display: inline-block;
    text-align: center;
}
input[type=range].anim-slider {
    width: 374px;
    margin-left: auto;
    margin-right: auto;
}
.anim-buttons {
    margin: 8px 0px;
}
.anim-buttons button {
    padding: 0;
    width: 36px;
}
.anim-state label {
    margin-right: 8px;
}
.anim-state input {
    margin: 0;
    vertical-align: middle;
}
</style>
"""


# HTML template for HTMLWriter
DISPLAY_TEMPLATE = """
<div class="animation">
  <img id="_anim_img{id}">
  <div class="anim-controls">
    <input id="_anim_slider{id}" type="range" class="anim-slider"
           name="points" min="0" max="1" step="1" value="0"
           oninput="anim{id}.set_frame(parseInt(this.value));">
    <div class="anim-buttons">
      <button title="Decrease speed" aria-label="Decrease speed" onclick="anim{id}.slower()">
          <i class="fa fa-minus"></i></button>
      <button title="First frame" aria-label="First frame" onclick="anim{id}.first_frame()">
        <i class="fa fa-fast-backward"></i></button>
      <button title="Previous frame" aria-label="Previous frame" onclick="anim{id}.previous_frame()">
          <i class="fa fa-step-backward"></i></button>
      <button title="Play backwards" aria-label="Play backwards" onclick="anim{id}.reverse_animation()">
          <i class="fa fa-play fa-flip-horizontal"></i></button>
      <button title="Pause" aria-label="Pause" onclick="anim{id}.pause_animation()">
          <i class="fa fa-pause"></i></button>
      <button title="Play" aria-label="Play" onclick="anim{id}.play_animation()">
          <i class="fa fa-play"></i></button>
      <button title="Next frame" aria-label="Next frame" onclick="anim{id}.next_frame()">
          <i class="fa fa-step-forward"></i></button>
      <button title="Last frame" aria-label="Last frame" onclick="anim{id}.last_frame()">
          <i class="fa fa-fast-forward"></i></button>
      <button title="Increase speed" aria-label="Increase speed" onclick="anim{id}.faster()">
          <i class="fa fa-plus"></i></button>
    </div>
    <form title="Repetition mode" aria-label="Repetition mode" action="#n" name="_anim_loop_select{id}"
          class="anim-state">
      <input type="radio" name="state" value="once" id="_anim_radio1_{id}"
             {once_checked}>
      <label for="_anim_radio1_{id}">Once</label>
      <input type="radio" name="state" value="loop" id="_anim_radio2_{id}"
             {loop_checked}>
      <label for="_anim_radio2_{id}">Loop</label>
      <input type="radio" name="state" value="reflect" id="_anim_radio3_{id}"
             {reflect_checked}>
      <label for="_anim_radio3_{id}">Reflect</label>
    </form>
  </div>
</div>


<script language="javascript">
  /* Instantiate the Animation class. */
  /* The IDs given should match those used in the template above. */
  (function() {{
    var img_id = "_anim_img{id}";
    var slider_id = "_anim_slider{id}";
    var loop_select_id = "_anim_loop_select{id}";
    var frames = new Array({Nframes});
    {fill_frames}

    /* set a timeout to make sure all the above elements are created before
       the object is initialized. */
    setTimeout(function() {{
        anim{id} = new Animation(frames, img_id, slider_id, {interval},
                                 loop_select_id);
    }}, 0);
  }})()
</script>
"""  # noqa: E501


INCLUDED_FRAMES = """
  for (var i=0; i<{Nframes}; i++){{
    frames[i] = "{frame_dir}/frame" + ("0000000" + i).slice(-7) +
                ".{frame_format}";
  }}
"""

# === NexusCore/openenv\Lib\site-packages\packaging\_manylinux.py ===
from __future__ import annotations

import collections
import contextlib
import functools
import os
import re
import sys
import warnings
from typing import Generator, Iterator, NamedTuple, Sequence

from ._elffile import EIClass, EIData, ELFFile, EMachine

EF_ARM_ABIMASK = 0xFF000000
EF_ARM_ABI_VER5 = 0x05000000
EF_ARM_ABI_FLOAT_HARD = 0x00000400


# `os.PathLike` not a generic type until Python 3.9, so sticking with `str`
# as the type for `path` until then.
@contextlib.contextmanager
def _parse_elf(path: str) -> Generator[ELFFile | None, None, None]:
    try:
        with open(path, "rb") as f:
            yield ELFFile(f)
    except (OSError, TypeError, ValueError):
        yield None


def _is_linux_armhf(executable: str) -> bool:
    # hard-float ABI can be detected from the ELF header of the running
    # process
    # https://static.docs.arm.com/ihi0044/g/aaelf32.pdf
    with _parse_elf(executable) as f:
        return (
            f is not None
            and f.capacity == EIClass.C32
            and f.encoding == EIData.Lsb
            and f.machine == EMachine.Arm
            and f.flags & EF_ARM_ABIMASK == EF_ARM_ABI_VER5
            and f.flags & EF_ARM_ABI_FLOAT_HARD == EF_ARM_ABI_FLOAT_HARD
        )


def _is_linux_i686(executable: str) -> bool:
    with _parse_elf(executable) as f:
        return (
            f is not None
            and f.capacity == EIClass.C32
            and f.encoding == EIData.Lsb
            and f.machine == EMachine.I386
        )


def _have_compatible_abi(executable: str, archs: Sequence[str]) -> bool:
    if "armv7l" in archs:
        return _is_linux_armhf(executable)
    if "i686" in archs:
        return _is_linux_i686(executable)
    allowed_archs = {
        "x86_64",
        "aarch64",
        "ppc64",
        "ppc64le",
        "s390x",
        "loongarch64",
        "riscv64",
    }
    return any(arch in allowed_archs for arch in archs)


# If glibc ever changes its major version, we need to know what the last
# minor version was, so we can build the complete list of all versions.
# For now, guess what the highest minor version might be, assume it will
# be 50 for testing. Once this actually happens, update the dictionary
# with the actual value.
_LAST_GLIBC_MINOR: dict[int, int] = collections.defaultdict(lambda: 50)


class _GLibCVersion(NamedTuple):
    major: int
    minor: int


def _glibc_version_string_confstr() -> str | None:
    """
    Primary implementation of glibc_version_string using os.confstr.
    """
    # os.confstr is quite a bit faster than ctypes.DLL. It's also less likely
    # to be broken or missing. This strategy is used in the standard library
    # platform module.
    # https://github.com/python/cpython/blob/fcf1d003bf4f0100c/Lib/platform.py#L175-L183
    try:
        # Should be a string like "glibc 2.17".
        version_string: str | None = os.confstr("CS_GNU_LIBC_VERSION")
        assert version_string is not None
        _, version = version_string.rsplit()
    except (AssertionError, AttributeError, OSError, ValueError):
        # os.confstr() or CS_GNU_LIBC_VERSION not available (or a bad value)...
        return None
    return version


def _glibc_version_string_ctypes() -> str | None:
    """
    Fallback implementation of glibc_version_string using ctypes.
    """
    try:
        import ctypes
    except ImportError:
        return None

    # ctypes.CDLL(None) internally calls dlopen(NULL), and as the dlopen
    # manpage says, "If filename is NULL, then the returned handle is for the
    # main program". This way we can let the linker do the work to figure out
    # which libc our process is actually using.
    #
    # We must also handle the special case where the executable is not a
    # dynamically linked executable. This can occur when using musl libc,
    # for example. In this situation, dlopen() will error, leading to an
    # OSError. Interestingly, at least in the case of musl, there is no
    # errno set on the OSError. The single string argument used to construct
    # OSError comes from libc itself and is therefore not portable to
    # hard code here. In any case, failure to call dlopen() means we
    # can proceed, so we bail on our attempt.
    try:
        process_namespace = ctypes.CDLL(None)
    except OSError:
        return None

    try:
        gnu_get_libc_version = process_namespace.gnu_get_libc_version
    except AttributeError:
        # Symbol doesn't exist -> therefore, we are not linked to
        # glibc.
        return None

    # Call gnu_get_libc_version, which returns a string like "2.5"
    gnu_get_libc_version.restype = ctypes.c_char_p
    version_str: str = gnu_get_libc_version()
    # py2 / py3 compatibility:
    if not isinstance(version_str, str):
        version_str = version_str.decode("ascii")

    return version_str


def _glibc_version_string() -> str | None:
    """Returns glibc version string, or None if not using glibc."""
    return _glibc_version_string_confstr() or _glibc_version_string_ctypes()


def _parse_glibc_version(version_str: str) -> tuple[int, int]:
    """Parse glibc version.

    We use a regexp instead of str.split because we want to discard any
    random junk that might come after the minor version -- this might happen
    in patched/forked versions of glibc (e.g. Linaro's version of glibc
    uses version strings like "2.20-2014.11"). See gh-3588.
    """
    m = re.match(r"(?P<major>[0-9]+)\.(?P<minor>[0-9]+)", version_str)
    if not m:
        warnings.warn(
            f"Expected glibc version with 2 components major.minor, got: {version_str}",
            RuntimeWarning,
            stacklevel=2,
        )
        return -1, -1
    return int(m.group("major")), int(m.group("minor"))


@functools.lru_cache
def _get_glibc_version() -> tuple[int, int]:
    version_str = _glibc_version_string()
    if version_str is None:
        return (-1, -1)
    return _parse_glibc_version(version_str)


# From PEP 513, PEP 600
def _is_compatible(arch: str, version: _GLibCVersion) -> bool:
    sys_glibc = _get_glibc_version()
    if sys_glibc < version:
        return False
    # Check for presence of _manylinux module.
    try:
        import _manylinux
    except ImportError:
        return True
    if hasattr(_manylinux, "manylinux_compatible"):
        result = _manylinux.manylinux_compatible(version[0], version[1], arch)
        if result is not None:
            return bool(result)
        return True
    if version == _GLibCVersion(2, 5):
        if hasattr(_manylinux, "manylinux1_compatible"):
            return bool(_manylinux.manylinux1_compatible)
    if version == _GLibCVersion(2, 12):
        if hasattr(_manylinux, "manylinux2010_compatible"):
            return bool(_manylinux.manylinux2010_compatible)
    if version == _GLibCVersion(2, 17):
        if hasattr(_manylinux, "manylinux2014_compatible"):
            return bool(_manylinux.manylinux2014_compatible)
    return True


_LEGACY_MANYLINUX_MAP = {
    # CentOS 7 w/ glibc 2.17 (PEP 599)
    (2, 17): "manylinux2014",
    # CentOS 6 w/ glibc 2.12 (PEP 571)
    (2, 12): "manylinux2010",
    # CentOS 5 w/ glibc 2.5 (PEP 513)
    (2, 5): "manylinux1",
}


def platform_tags(archs: Sequence[str]) -> Iterator[str]:
    """Generate manylinux tags compatible to the current platform.

    :param archs: Sequence of compatible architectures.
        The first one shall be the closest to the actual architecture and be the part of
        platform tag after the ``linux_`` prefix, e.g. ``x86_64``.
        The ``linux_`` prefix is assumed as a prerequisite for the current platform to
        be manylinux-compatible.

    :returns: An iterator of compatible manylinux tags.
    """
    if not _have_compatible_abi(sys.executable, archs):
        return
    # Oldest glibc to be supported regardless of architecture is (2, 17).
    too_old_glibc2 = _GLibCVersion(2, 16)
    if set(archs) & {"x86_64", "i686"}:
        # On x86/i686 also oldest glibc to be supported is (2, 5).
        too_old_glibc2 = _GLibCVersion(2, 4)
    current_glibc = _GLibCVersion(*_get_glibc_version())
    glibc_max_list = [current_glibc]
    # We can assume compatibility across glibc major versions.
    # https://sourceware.org/bugzilla/show_bug.cgi?id=24636
    #
    # Build a list of maximum glibc versions so that we can
    # output the canonical list of all glibc from current_glibc
    # down to too_old_glibc2, including all intermediary versions.
    for glibc_major in range(current_glibc.major - 1, 1, -1):
        glibc_minor = _LAST_GLIBC_MINOR[glibc_major]
        glibc_max_list.append(_GLibCVersion(glibc_major, glibc_minor))
    for arch in archs:
        for glibc_max in glibc_max_list:
            if glibc_max.major == too_old_glibc2.major:
                min_minor = too_old_glibc2.minor
            else:
                # For other glibc major versions oldest supported is (x, 0).
                min_minor = -1
            for glibc_minor in range(glibc_max.minor, min_minor, -1):
                glibc_version = _GLibCVersion(glibc_max.major, glibc_minor)
                tag = "manylinux_{}_{}".format(*glibc_version)
                if _is_compatible(arch, glibc_version):
                    yield f"{tag}_{arch}"
                # Handle the legacy manylinux1, manylinux2010, manylinux2014 tags.
                if glibc_version in _LEGACY_MANYLINUX_MAP:
                    legacy_tag = _LEGACY_MANYLINUX_MAP[glibc_version]
                    if _is_compatible(arch, glibc_version):
                        yield f"{legacy_tag}_{arch}"

# === NexusCore/openenv\Lib\site-packages\litellm\llms\clarifai\chat\transformation.py ===
import json
from typing import TYPE_CHECKING, Any, AsyncIterator, Iterator, List, Optional, Union

import httpx

from litellm.litellm_core_utils.prompt_templates.common_utils import (
    convert_content_list_to_str,
)
from litellm.llms.base_llm.base_model_iterator import FakeStreamResponseIterator
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import (
    ChatCompletionToolCallChunk,
    ChatCompletionUsageBlock,
    Choices,
    GenericStreamingChunk,
    Message,
    ModelResponse,
    Usage,
)
from litellm.utils import token_counter

from ..common_utils import ClarifaiError

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj

    LoggingClass = LiteLLMLoggingObj
else:
    LoggingClass = Any


class ClarifaiConfig(BaseConfig):
    """
    Reference: https://clarifai.com/meta/Llama-2/models/llama2-70b-chat
    """

    max_tokens: Optional[int] = None
    temperature: Optional[int] = None
    top_k: Optional[int] = None

    def __init__(
        self,
        max_tokens: Optional[int] = None,
        temperature: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_supported_openai_params(self, model: str) -> list:
        return [
            "temperature",
            "max_tokens",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        for param, value in non_default_params.items():
            if param == "temperature":
                optional_params["temperature"] = value
            elif param == "max_tokens":
                optional_params["max_tokens"] = value

        return optional_params

    def _completions_to_model(self, prompt: str, optional_params: dict) -> dict:
        params = {}
        if temperature := optional_params.get("temperature"):
            params["temperature"] = temperature
        if max_tokens := optional_params.get("max_tokens"):
            params["max_tokens"] = max_tokens
        return {
            "inputs": [{"data": {"text": {"raw": prompt}}}],
            "model": {"output_info": {"params": params}},
        }

    def _convert_model_to_url(self, model: str, api_base: str):
        user_id, app_id, model_id = model.split(".")
        return f"{api_base}/users/{user_id}/apps/{app_id}/models/{model_id}/outputs"

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        prompt = " ".join(convert_content_list_to_str(message) for message in messages)

        ## Load Config
        config = self.get_config()
        for k, v in config.items():
            if k not in optional_params:
                optional_params[k] = v

        data = self._completions_to_model(
            prompt=prompt, optional_params=optional_params
        )

        return data

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
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }

        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return ClarifaiError(message=error_message, status_code=status_code)

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LoggingClass,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: str,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        logging_obj.post_call(
            input=messages,
            api_key=api_key,
            original_response=raw_response.text,
            additional_args={"complete_input_dict": request_data},
        )
        ## RESPONSE OBJECT
        try:
            completion_response = raw_response.json()
        except httpx.HTTPStatusError as e:
            raise ClarifaiError(
                message=str(e),
                status_code=raw_response.status_code,
            )
        except Exception as e:
            raise ClarifaiError(
                message=str(e),
                status_code=422,
            )
        # print(completion_response)
        try:
            choices_list = []
            for idx, item in enumerate(completion_response["outputs"]):
                if len(item["data"]["text"]["raw"]) > 0:
                    message_obj = Message(content=item["data"]["text"]["raw"])
                else:
                    message_obj = Message(content=None)
                choice_obj = Choices(
                    finish_reason="stop",
                    index=idx + 1,  # check
                    message=message_obj,
                )
                choices_list.append(choice_obj)
            model_response.choices = choices_list  # type: ignore

        except Exception as e:
            raise ClarifaiError(
                message=str(e),
                status_code=422,
            )

        # Calculate Usage
        prompt_tokens = token_counter(model=model, messages=messages)
        completion_tokens = len(
            encoding.encode(model_response["choices"][0]["message"].get("content"))
        )
        model_response.model = model
        setattr(
            model_response,
            "usage",
            Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )
        return model_response

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ) -> Any:
        return ClarifaiModelResponseIterator(
            model_response=streaming_response,
            json_mode=json_mode,
        )


class ClarifaiModelResponseIterator(FakeStreamResponseIterator):
    def __init__(
        self,
        model_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        json_mode: Optional[bool] = False,
    ):
        super().__init__(
            model_response=model_response,
            json_mode=json_mode,
        )

    def chunk_parser(self, chunk: dict) -> GenericStreamingChunk:
        try:
            text = ""
            tool_use: Optional[ChatCompletionToolCallChunk] = None
            is_finished = False
            finish_reason = ""
            usage: Optional[ChatCompletionUsageBlock] = None
            provider_specific_fields = None

            text = (
                chunk.get("outputs", "")[0]
                .get("data", "")
                .get("text", "")
                .get("raw", "")
            )

            index: int = 0

            return GenericStreamingChunk(
                text=text,
                tool_use=tool_use,
                is_finished=is_finished,
                finish_reason=finish_reason,
                usage=usage,
                index=index,
                provider_specific_fields=provider_specific_fields,
            )
        except json.JSONDecodeError:
            raise ValueError(f"Failed to decode JSON from chunk: {chunk}")

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\grammar_notation.py ===
"""
    pygments.lexers.grammar_notation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for grammar notations like BNF.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, bygroups, include, this, using, words
from pygments.token import Comment, Keyword, Literal, Name, Number, \
    Operator, Punctuation, String, Text, Whitespace

__all__ = ['BnfLexer', 'AbnfLexer', 'JsgfLexer', 'PegLexer']


class BnfLexer(RegexLexer):
    """
    This lexer is for grammar notations which are similar to
    original BNF.

    In order to maximize a number of targets of this lexer,
    let's decide some designs:

    * We don't distinguish `Terminal Symbol`.

    * We do assume that `NonTerminal Symbol` are always enclosed
      with arrow brackets.

    * We do assume that `NonTerminal Symbol` may include
      any printable characters except arrow brackets and ASCII 0x20.
      This assumption is for `RBNF <http://www.rfc-base.org/txt/rfc-5511.txt>`_.

    * We do assume that target notation doesn't support comment.

    * We don't distinguish any operators and punctuation except
      `::=`.

    Though these decision making might cause too minimal highlighting
    and you might be disappointed, but it is reasonable for us.
    """

    name = 'BNF'
    aliases = ['bnf']
    filenames = ['*.bnf']
    mimetypes = ['text/x-bnf']
    url = 'https://en.wikipedia.org/wiki/Backus%E2%80%93Naur_form'
    version_added = '2.1'

    tokens = {
        'root': [
            (r'(<)([ -;=?-~]+)(>)',
             bygroups(Punctuation, Name.Class, Punctuation)),

            # an only operator
            (r'::=', Operator),

            # fallback
            (r'[^<>:]+', Text),  # for performance
            (r'.', Text),
        ],
    }


class AbnfLexer(RegexLexer):
    """
    Lexer for IETF 7405 ABNF.

    (Updates `5234 <http://www.ietf.org/rfc/rfc5234.txt>`_) grammars.
    """

    name = 'ABNF'
    url = 'http://www.ietf.org/rfc/rfc7405.txt'
    aliases = ['abnf']
    filenames = ['*.abnf']
    mimetypes = ['text/x-abnf']
    version_added = '2.1'

    _core_rules = (
        'ALPHA', 'BIT', 'CHAR', 'CR', 'CRLF', 'CTL', 'DIGIT',
        'DQUOTE', 'HEXDIG', 'HTAB', 'LF', 'LWSP', 'OCTET',
        'SP', 'VCHAR', 'WSP')

    tokens = {
        'root': [
            # comment
            (r';.*$', Comment.Single),

            # quoted
            #   double quote itself in this state, it is as '%x22'.
            (r'(%[si])?"[^"]*"', Literal),

            # binary (but i have never seen...)
            (r'%b[01]+\-[01]+\b', Literal),  # range
            (r'%b[01]+(\.[01]+)*\b', Literal),  # concat

            # decimal
            (r'%d[0-9]+\-[0-9]+\b', Literal),  # range
            (r'%d[0-9]+(\.[0-9]+)*\b', Literal),  # concat

            # hexadecimal
            (r'%x[0-9a-fA-F]+\-[0-9a-fA-F]+\b', Literal),  # range
            (r'%x[0-9a-fA-F]+(\.[0-9a-fA-F]+)*\b', Literal),  # concat

            # repetition (<a>*<b>element) including nRule
            (r'\b[0-9]+\*[0-9]+', Operator),
            (r'\b[0-9]+\*', Operator),
            (r'\b[0-9]+', Operator),
            (r'\*', Operator),

            # Strictly speaking, these are not keyword but
            # are called `Core Rule'.
            (words(_core_rules, suffix=r'\b'), Keyword),

            # nonterminals (ALPHA *(ALPHA / DIGIT / "-"))
            (r'[a-zA-Z][a-zA-Z0-9-]*\b', Name.Class),

            # operators
            (r'(=/|=|/)', Operator),

            # punctuation
            (r'[\[\]()]', Punctuation),

            # fallback
            (r'\s+', Whitespace),
            (r'.', Text),
        ],
    }


class JsgfLexer(RegexLexer):
    """
    For JSpeech Grammar Format grammars.
    """
    name = 'JSGF'
    url = 'https://www.w3.org/TR/jsgf/'
    aliases = ['jsgf']
    filenames = ['*.jsgf']
    mimetypes = ['application/jsgf', 'application/x-jsgf', 'text/jsgf']
    version_added = '2.2'

    tokens = {
        'root': [
            include('comments'),
            include('non-comments'),
        ],
        'comments': [
            (r'/\*\*(?!/)', Comment.Multiline, 'documentation comment'),
            (r'/\*[\w\W]*?\*/', Comment.Multiline),
            (r'//.*$', Comment.Single),
        ],
        'non-comments': [
            (r'\A#JSGF[^;]*', Comment.Preproc),
            (r'\s+', Whitespace),
            (r';', Punctuation),
            (r'[=|()\[\]*+]', Operator),
            (r'/[^/]+/', Number.Float),
            (r'"', String.Double, 'string'),
            (r'\{', String.Other, 'tag'),
            (words(('import', 'public'), suffix=r'\b'), Keyword.Reserved),
            (r'grammar\b', Keyword.Reserved, 'grammar name'),
            (r'(<)(NULL|VOID)(>)',
             bygroups(Punctuation, Name.Builtin, Punctuation)),
            (r'<', Punctuation, 'rulename'),
            (r'\w+|[^\s;=|()\[\]*+/"{<\w]+', Text),
        ],
        'string': [
            (r'"', String.Double, '#pop'),
            (r'\\.', String.Escape),
            (r'[^\\"]+', String.Double),
        ],
        'tag': [
            (r'\}', String.Other, '#pop'),
            (r'\\.', String.Escape),
            (r'[^\\}]+', String.Other),
        ],
        'grammar name': [
            (r';', Punctuation, '#pop'),
            (r'\s+', Whitespace),
            (r'\.', Punctuation),
            (r'[^;\s.]+', Name.Namespace),
        ],
        'rulename': [
            (r'>', Punctuation, '#pop'),
            (r'\*', Punctuation),
            (r'\s+', Whitespace),
            (r'([^.>]+)(\s*)(\.)', bygroups(Name.Namespace, Text, Punctuation)),
            (r'[^.>]+', Name.Constant),
        ],
        'documentation comment': [
            (r'\*/', Comment.Multiline, '#pop'),
            (r'^(\s*)(\*?)(\s*)(@(?:example|see))(\s+)'
             r'([\w\W]*?(?=(?:^\s*\*?\s*@|\*/)))',
             bygroups(Whitespace, Comment.Multiline, Whitespace, Comment.Special,
                      Whitespace, using(this, state='example'))),
            (r'(^\s*\*?\s*)(@\S*)',
             bygroups(Comment.Multiline, Comment.Special)),
            (r'[^*\n@]+|\w|\W', Comment.Multiline),
        ],
        'example': [
            (r'(\n\s*)(\*)', bygroups(Whitespace, Comment.Multiline)),
            include('non-comments'),
            (r'.', Comment.Multiline),
        ],
    }


class PegLexer(RegexLexer):
    """
    This lexer is for Parsing Expression Grammars (PEG).

    Various implementations of PEG have made different decisions
    regarding the syntax, so let's try to be accommodating:

    * `<-`, `←`, `:`, and `=` are all accepted as rule operators.

    * Both `|` and `/` are choice operators.

    * `^`, `↑`, and `~` are cut operators.

    * A single `a-z` character immediately before a string, or
      multiple `a-z` characters following a string, are part of the
      string (e.g., `r"..."` or `"..."ilmsuxa`).
    """

    name = 'PEG'
    url = 'https://bford.info/pub/lang/peg.pdf'
    aliases = ['peg']
    filenames = ['*.peg']
    mimetypes = ['text/x-peg']
    version_added = '2.6'

    tokens = {
        'root': [
            # Comments
            (r'#.*$', Comment.Single),

            # All operators
            (r'<-|[←:=/|&!?*+^↑~]', Operator),

            # Other punctuation
            (r'[()]', Punctuation),

            # Keywords
            (r'\.', Keyword),

            # Character classes
            (r'(\[)([^\]]*(?:\\.[^\]\\]*)*)(\])',
             bygroups(Punctuation, String, Punctuation)),

            # Single and double quoted strings (with optional modifiers)
            (r'[a-z]?"[^"\\]*(?:\\.[^"\\]*)*"[a-z]*', String.Double),
            (r"[a-z]?'[^'\\]*(?:\\.[^'\\]*)*'[a-z]*", String.Single),

            # Nonterminals are not whitespace, operators, or punctuation
            (r'[^\s<←:=/|&!?*+\^↑~()\[\]"\'#]+', Name.Class),

            # Fallback
            (r'.', Text),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\win32com\test\util.py ===
import logging
import os
import sys
import tempfile
import unittest
import winreg

import pythoncom
import pywin32_testutil
import pywintypes
import win32api
import win32com
import winerror
from pythoncom import _GetGatewayCount, _GetInterfaceCount


def CheckClean():
    # Ensure no lingering exceptions - Python should have zero outstanding
    # COM objects
    c = _GetInterfaceCount()
    if c:
        print("Warning - %d com interface objects still alive" % c)
    c = _GetGatewayCount()
    if c:
        print("Warning - %d com gateway objects still alive" % c)


def RegisterPythonServer(filename, progids=None, verbose=0):
    if progids:
        if isinstance(progids, str):
            progids = [progids]
        # we know the CLSIDs we need, but we might not be an admin user
        # and otherwise unable to register them.  So as long as the progids
        # exist and the DLL points at our version, assume it already is.
        why_not = None
        for progid in progids:
            try:
                clsid = pywintypes.IID(progid)
            except pythoncom.com_error:
                # not registered.
                break
            try:
                HKCR = winreg.HKEY_CLASSES_ROOT
                hk = winreg.OpenKey(HKCR, "CLSID\\%s" % clsid)
                dll = winreg.QueryValue(hk, "InprocServer32")
            except OSError:
                # no CLSID or InProcServer32 - not registered
                break
            ok_files = [
                os.path.basename(pythoncom.__file__),
                "pythoncomloader%d%d.dll"
                % (sys.version_info.major, sys.version_info.minor),
            ]
            if os.path.basename(dll) not in ok_files:
                why_not = (
                    "{!r} is registered against a different Python version ({})".format(
                        progid,
                        dll,
                    )
                )
                break
        else:
            # print(f"Skipping registration of '{filename}' - already registered")
            return
    # needs registration - see if it's likely!
    try:
        from win32com.shell.shell import IsUserAnAdmin
    except ImportError:
        print("Can't import win32com.shell - no idea if you are an admin or not?")
        is_admin = False
    else:
        try:
            is_admin = IsUserAnAdmin()
        except pythoncom.com_error:
            # old, less-secure OS - assume *is* admin.
            is_admin = True
    if not is_admin:
        msg = (
            "%r isn't registered, but I'm not an administrator who can register it."
            % progids[0]
        )
        if why_not:
            msg += "\n(registration check failed as %s)" % why_not
        # throw a normal "class not registered" exception - we don't report
        # them the same way as "real" errors.
        raise pythoncom.com_error(winerror.CO_E_CLASSSTRING, msg, None, -1)
    # so theoretically we are able to register it.
    cmd = f'{win32api.GetModuleFileName(0)} "{filename}" --unattended > nul 2>&1'
    if verbose:
        print("Registering engine", filename)
        # print(cmd)
    rc = os.system(cmd)
    if rc:
        print("Registration command was:")
        print(cmd)
        raise RuntimeError("Registration of engine '%s' failed" % filename)


def ExecuteShellCommand(
    cmd,
    testcase,
    expected_output=None,  # Set to '' to check for nothing
    tracebacks_ok=0,  # OK if the output contains a t/b?
):
    output_name = tempfile.mktemp("win32com_test")
    cmd += ' > "%s" 2>&1' % output_name
    rc = os.system(cmd)
    output = open(output_name, "r").read().strip()
    os.remove(output_name)

    class Failed(Exception):
        pass

    try:
        if rc:
            raise Failed("exit code was " + str(rc))
        if expected_output is not None and output != expected_output:
            raise Failed(f"Expected output {expected_output!r} (got {output!r})")
        if not tracebacks_ok and output.find("Traceback (most recent call last)") >= 0:
            raise Failed("traceback in program output")
        return output
    except Failed as why:
        print("Failed to exec command '%r'" % cmd)
        print("Failed as", why)
        print("** start of program output **")
        print(output)
        print("** end of program output **")
        testcase.fail(f"Executing '{cmd}' failed as {why}")


def assertRaisesCOM_HRESULT(testcase, hresult, func, *args, **kw):
    try:
        func(*args, **kw)
    except pythoncom.com_error as details:
        if details.hresult == hresult:
            return
    testcase.fail("Excepected COM exception with HRESULT 0x%x" % hresult)


class CaptureWriter:
    def __init__(self):
        self.old_err = self.old_out = None
        self.clear()

    def capture(self):
        self.clear()
        self.old_out = sys.stdout
        self.old_err = sys.stderr
        sys.stdout = sys.stderr = self

    def release(self):
        if self.old_out:
            sys.stdout = self.old_out
            self.old_out = None
        if self.old_err:
            sys.stderr = self.old_err
            self.old_err = None

    def clear(self):
        self.captured = []

    def write(self, msg):
        self.captured.append(msg)

    def get_captured(self):
        return "".join(self.captured)

    def get_num_lines_captured(self):
        return len("".join(self.captured).split("\n"))


# Utilities to set the win32com logger to something what just captures
# records written and doesn't print them.
class LogHandler(logging.Handler):
    def __init__(self):
        self.emitted = []
        logging.Handler.__init__(self)

    def emit(self, record):
        self.emitted.append(record)


_win32com_logger = None


def setup_test_logger():
    old_log = getattr(win32com, "logger", None)
    global _win32com_logger
    if _win32com_logger is None:
        _win32com_logger = logging.Logger("test")
        handler = LogHandler()
        _win32com_logger.addHandler(handler)

    win32com.logger = _win32com_logger
    handler = _win32com_logger.handlers[0]
    handler.emitted = []
    return handler.emitted, old_log


def restore_test_logger(prev_logger):
    assert prev_logger is None, "who needs this?"
    if prev_logger is None:
        del win32com.logger
    else:
        win32com.logger = prev_logger


# We used to override some of this (and may later!)
TestCase = unittest.TestCase


def CapturingFunctionTestCase(*args, **kw):
    real_test = _CapturingFunctionTestCase(*args, **kw)
    return pywin32_testutil.LeakTestCase(real_test)


class _CapturingFunctionTestCase(unittest.FunctionTestCase):  # , TestCaseMixin):
    def __call__(self, result=None):
        if result is None:
            result = self.defaultTestResult()
        writer = CaptureWriter()
        # self._preTest()
        writer.capture()
        try:
            unittest.FunctionTestCase.__call__(self, result)
            if getattr(self, "do_leak_tests", 0) and hasattr(sys, "gettotalrefcount"):
                self.run_leak_tests(result)
        finally:
            writer.release()
            # self._postTest(result)
        output = writer.get_captured()
        self.checkOutput(output, result)
        if result.showAll:
            print(output)

    def checkOutput(self, output, result):
        if output.find("Traceback") >= 0:
            msg = "Test output contained a traceback\n---\n%s\n---" % output
            result.errors.append((self, msg))


class ShellTestCase(unittest.TestCase):
    def __init__(self, cmd, expected_output):
        self.__cmd = cmd
        self.__eo = expected_output
        unittest.TestCase.__init__(self)

    def runTest(self):
        ExecuteShellCommand(self.__cmd, self, self.__eo)

    def __str__(self):
        max = 30
        if len(self.__cmd) > max:
            cmd_repr = self.__cmd[:max] + "..."
        else:
            cmd_repr = self.__cmd
        return "exec: " + cmd_repr


def testmain(*args, **kw):
    pywin32_testutil.testmain(*args, **kw)
    CheckClean()