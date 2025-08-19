
# === NexusCore/openenv\Lib\site-packages\litellm\router_strategy\lowest_cost.py ===
#### What this does ####
#   picks based on response time (for streaming, this is time to first token)
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import litellm
from litellm import ModelResponse, token_counter, verbose_logger
from litellm._logging import verbose_router_logger
from litellm.caching.caching import DualCache
from litellm.integrations.custom_logger import CustomLogger


class LowestCostLoggingHandler(CustomLogger):
    test_flag: bool = False
    logged_success: int = 0
    logged_failure: int = 0

    def __init__(
        self, router_cache: DualCache, model_list: list, routing_args: dict = {}
    ):
        self.router_cache = router_cache
        self.model_list = model_list

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            """
            Update usage on success
            """
            if kwargs["litellm_params"].get("metadata") is None:
                pass
            else:
                model_group = kwargs["litellm_params"]["metadata"].get(
                    "model_group", None
                )

                id = kwargs["litellm_params"].get("model_info", {}).get("id", None)
                if model_group is None or id is None:
                    return
                elif isinstance(id, int):
                    id = str(id)

                # ------------
                # Setup values
                # ------------
                """
                {
                    {model_group}_map: {
                        id: {
                            f"{date:hour:minute}" : {"tpm": 34, "rpm": 3}
                        }
                    }
                }
                """
                current_date = datetime.now().strftime("%Y-%m-%d")
                current_hour = datetime.now().strftime("%H")
                current_minute = datetime.now().strftime("%M")
                precise_minute = f"{current_date}-{current_hour}-{current_minute}"
                cost_key = f"{model_group}_map"

                response_ms: timedelta = end_time - start_time

                total_tokens = 0

                if isinstance(response_obj, ModelResponse):
                    _usage = getattr(response_obj, "usage", None)
                    if _usage is not None and isinstance(_usage, litellm.Usage):
                        completion_tokens = _usage.completion_tokens
                        total_tokens = _usage.total_tokens
                        float(response_ms.total_seconds() / completion_tokens)

                # ------------
                # Update usage
                # ------------

                request_count_dict = self.router_cache.get_cache(key=cost_key) or {}

                # check local result first

                if id not in request_count_dict:
                    request_count_dict[id] = {}

                if precise_minute not in request_count_dict[id]:
                    request_count_dict[id][precise_minute] = {}

                ## TPM
                request_count_dict[id][precise_minute]["tpm"] = (
                    request_count_dict[id][precise_minute].get("tpm", 0) + total_tokens
                )

                ## RPM
                request_count_dict[id][precise_minute]["rpm"] = (
                    request_count_dict[id][precise_minute].get("rpm", 0) + 1
                )

                self.router_cache.set_cache(key=cost_key, value=request_count_dict)

                ### TESTING ###
                if self.test_flag:
                    self.logged_success += 1
        except Exception as e:
            verbose_logger.exception(
                "litellm.router_strategy.lowest_cost.py::log_success_event(): Exception occured - {}".format(
                    str(e)
                )
            )
            pass

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            """
            Update cost usage on success
            """
            if kwargs["litellm_params"].get("metadata") is None:
                pass
            else:
                model_group = kwargs["litellm_params"]["metadata"].get(
                    "model_group", None
                )

                id = kwargs["litellm_params"].get("model_info", {}).get("id", None)
                if model_group is None or id is None:
                    return
                elif isinstance(id, int):
                    id = str(id)

                # ------------
                # Setup values
                # ------------
                """
                {
                    {model_group}_map: {
                        id: {
                            "cost": [..]
                            f"{date:hour:minute}" : {"tpm": 34, "rpm": 3}
                        }
                    }
                }
                """
                cost_key = f"{model_group}_map"

                current_date = datetime.now().strftime("%Y-%m-%d")
                current_hour = datetime.now().strftime("%H")
                current_minute = datetime.now().strftime("%M")
                precise_minute = f"{current_date}-{current_hour}-{current_minute}"

                response_ms: timedelta = end_time - start_time

                total_tokens = 0

                if isinstance(response_obj, ModelResponse):
                    _usage = getattr(response_obj, "usage", None)
                    if _usage is not None and isinstance(_usage, litellm.Usage):
                        completion_tokens = _usage.completion_tokens
                        total_tokens = _usage.total_tokens

                        float(response_ms.total_seconds() / completion_tokens)

                # ------------
                # Update usage
                # ------------

                request_count_dict = (
                    await self.router_cache.async_get_cache(key=cost_key) or {}
                )

                if id not in request_count_dict:
                    request_count_dict[id] = {}
                if precise_minute not in request_count_dict[id]:
                    request_count_dict[id][precise_minute] = {}

                ## TPM
                request_count_dict[id][precise_minute]["tpm"] = (
                    request_count_dict[id][precise_minute].get("tpm", 0) + total_tokens
                )

                ## RPM
                request_count_dict[id][precise_minute]["rpm"] = (
                    request_count_dict[id][precise_minute].get("rpm", 0) + 1
                )

                await self.router_cache.async_set_cache(
                    key=cost_key, value=request_count_dict
                )  # reset map within window

                ### TESTING ###
                if self.test_flag:
                    self.logged_success += 1
        except Exception as e:
            verbose_logger.exception(
                "litellm.proxy.hooks.prompt_injection_detection.py::async_pre_call_hook(): Exception occured - {}".format(
                    str(e)
                )
            )
            pass

    async def async_get_available_deployments(  # noqa: PLR0915
        self,
        model_group: str,
        healthy_deployments: list,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
        request_kwargs: Optional[Dict] = None,
    ):
        """
        Returns a deployment with the lowest cost
        """
        cost_key = f"{model_group}_map"

        request_count_dict = await self.router_cache.async_get_cache(key=cost_key) or {}

        # -----------------------
        # Find lowest used model
        # ----------------------
        float("inf")

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_hour = datetime.now().strftime("%H")
        current_minute = datetime.now().strftime("%M")
        precise_minute = f"{current_date}-{current_hour}-{current_minute}"

        if request_count_dict is None:  # base case
            return

        all_deployments = request_count_dict
        for d in healthy_deployments:
            ## if healthy deployment not yet used
            if d["model_info"]["id"] not in all_deployments:
                all_deployments[d["model_info"]["id"]] = {
                    precise_minute: {"tpm": 0, "rpm": 0},
                }

        try:
            input_tokens = token_counter(messages=messages, text=input)
        except Exception:
            input_tokens = 0

        # randomly sample from all_deployments, incase all deployments have latency=0.0
        _items = all_deployments.items()

        ### GET AVAILABLE DEPLOYMENTS ### filter out any deployments > tpm/rpm limits
        potential_deployments = []
        _cost_per_deployment = {}
        for item, item_map in all_deployments.items():
            ## get the item from model list
            _deployment = None
            for m in healthy_deployments:
                if item == m["model_info"]["id"]:
                    _deployment = m

            if _deployment is None:
                continue  # skip to next one

            _deployment_tpm = (
                _deployment.get("tpm", None)
                or _deployment.get("litellm_params", {}).get("tpm", None)
                or _deployment.get("model_info", {}).get("tpm", None)
                or float("inf")
            )

            _deployment_rpm = (
                _deployment.get("rpm", None)
                or _deployment.get("litellm_params", {}).get("rpm", None)
                or _deployment.get("model_info", {}).get("rpm", None)
                or float("inf")
            )
            item_litellm_model_name = _deployment.get("litellm_params", {}).get("model")
            item_litellm_model_cost_map = litellm.model_cost.get(
                item_litellm_model_name, {}
            )

            # check if user provided input_cost_per_token and output_cost_per_token in litellm_params
            item_input_cost = None
            item_output_cost = None
            if _deployment.get("litellm_params", {}).get("input_cost_per_token", None):
                item_input_cost = _deployment.get("litellm_params", {}).get(
                    "input_cost_per_token"
                )

            if _deployment.get("litellm_params", {}).get("output_cost_per_token", None):
                item_output_cost = _deployment.get("litellm_params", {}).get(
                    "output_cost_per_token"
                )

            if item_input_cost is None:
                item_input_cost = item_litellm_model_cost_map.get(
                    "input_cost_per_token", 5.0
                )

            if item_output_cost is None:
                item_output_cost = item_litellm_model_cost_map.get(
                    "output_cost_per_token", 5.0
                )

            # if litellm["model"] is not in model_cost map -> use item_cost = $10

            item_cost = item_input_cost + item_output_cost

            item_rpm = item_map.get(precise_minute, {}).get("rpm", 0)
            item_tpm = item_map.get(precise_minute, {}).get("tpm", 0)

            verbose_router_logger.debug(
                f"item_cost: {item_cost}, item_tpm: {item_tpm}, item_rpm: {item_rpm}, model_id: {_deployment.get('model_info', {}).get('id')}"
            )

            # -------------- #
            # Debugging Logic
            # -------------- #
            # We use _cost_per_deployment to log to langfuse, slack - this is not used to make a decision on routing
            # this helps a user to debug why the router picked a specfic deployment      #
            _deployment_api_base = _deployment.get("litellm_params", {}).get(
                "api_base", ""
            )
            if _deployment_api_base is not None:
                _cost_per_deployment[_deployment_api_base] = item_cost
            # -------------- #
            # End of Debugging Logic
            # -------------- #

            if (
                item_tpm + input_tokens > _deployment_tpm
                or item_rpm + 1 > _deployment_rpm
            ):  # if user passed in tpm / rpm in the model_list
                continue
            else:
                potential_deployments.append((_deployment, item_cost))

        if len(potential_deployments) == 0:
            return None

        potential_deployments = sorted(potential_deployments, key=lambda x: x[1])

        selected_deployment = potential_deployments[0][0]
        return selected_deployment

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\autocommand\autoparse.py ===
# Copyright 2014-2015 Nathan West
#
# This file is part of autocommand.
#
# autocommand is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# autocommand is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with autocommand.  If not, see <http://www.gnu.org/licenses/>.

import sys
from re import compile as compile_regex
from inspect import signature, getdoc, Parameter
from argparse import ArgumentParser
from contextlib import contextmanager
from functools import wraps
from io import IOBase
from autocommand.errors import AutocommandError


_empty = Parameter.empty


class AnnotationError(AutocommandError):
    '''Annotation error: annotation must be a string, type, or tuple of both'''


class PositionalArgError(AutocommandError):
    '''
    Postional Arg Error: autocommand can't handle postional-only parameters
    '''


class KWArgError(AutocommandError):
    '''kwarg Error: autocommand can't handle a **kwargs parameter'''


class DocstringError(AutocommandError):
    '''Docstring error'''


class TooManySplitsError(DocstringError):
    '''
    The docstring had too many ---- section splits. Currently we only support
    using up to a single split, to split the docstring into description and
    epilog parts.
    '''


def _get_type_description(annotation):
    '''
    Given an annotation, return the (type, description) for the parameter.
    If you provide an annotation that is somehow both a string and a callable,
    the behavior is undefined.
    '''
    if annotation is _empty:
        return None, None
    elif callable(annotation):
        return annotation, None
    elif isinstance(annotation, str):
        return None, annotation
    elif isinstance(annotation, tuple):
        try:
            arg1, arg2 = annotation
        except ValueError as e:
            raise AnnotationError(annotation) from e
        else:
            if callable(arg1) and isinstance(arg2, str):
                return arg1, arg2
            elif isinstance(arg1, str) and callable(arg2):
                return arg2, arg1

    raise AnnotationError(annotation)


def _add_arguments(param, parser, used_char_args, add_nos):
    '''
    Add the argument(s) to an ArgumentParser (using add_argument) for a given
    parameter. used_char_args is the set of -short options currently already in
    use, and is updated (if necessary) by this function. If add_nos is True,
    this will also add an inverse switch for all boolean options. For
    instance, for the boolean parameter "verbose", this will create --verbose
    and --no-verbose.
    '''

    # Impl note: This function is kept separate from make_parser because it's
    # already very long and I wanted to separate out as much as possible into
    # its own call scope, to prevent even the possibility of suble mutation
    # bugs.
    if param.kind is param.POSITIONAL_ONLY:
        raise PositionalArgError(param)
    elif param.kind is param.VAR_KEYWORD:
        raise KWArgError(param)

    # These are the kwargs for the add_argument function.
    arg_spec = {}
    is_option = False

    # Get the type and default from the annotation.
    arg_type, description = _get_type_description(param.annotation)

    # Get the default value
    default = param.default

    # If there is no explicit type, and the default is present and not None,
    # infer the type from the default.
    if arg_type is None and default not in {_empty, None}:
        arg_type = type(default)

    # Add default. The presence of a default means this is an option, not an
    # argument.
    if default is not _empty:
        arg_spec['default'] = default
        is_option = True

    # Add the type
    if arg_type is not None:
        # Special case for bool: make it just a --switch
        if arg_type is bool:
            if not default or default is _empty:
                arg_spec['action'] = 'store_true'
            else:
                arg_spec['action'] = 'store_false'

            # Switches are always options
            is_option = True

        # Special case for file types: make it a string type, for filename
        elif isinstance(default, IOBase):
            arg_spec['type'] = str

        # TODO: special case for list type.
        #   - How to specificy type of list members?
        #       - param: [int]
        #       - param: int =[]
        #   - action='append' vs nargs='*'

        else:
            arg_spec['type'] = arg_type

    # nargs: if the signature includes *args, collect them as trailing CLI
    # arguments in a list. *args can't have a default value, so it can never be
    # an option.
    if param.kind is param.VAR_POSITIONAL:
        # TODO: consider depluralizing metavar/name here.
        arg_spec['nargs'] = '*'

    # Add description.
    if description is not None:
        arg_spec['help'] = description

    # Get the --flags
    flags = []
    name = param.name

    if is_option:
        # Add the first letter as a -short option.
        for letter in name[0], name[0].swapcase():
            if letter not in used_char_args:
                used_char_args.add(letter)
                flags.append('-{}'.format(letter))
                break

        # If the parameter is a --long option, or is a -short option that
        # somehow failed to get a flag, add it.
        if len(name) > 1 or not flags:
            flags.append('--{}'.format(name))

        arg_spec['dest'] = name
    else:
        flags.append(name)

    parser.add_argument(*flags, **arg_spec)

    # Create the --no- version for boolean switches
    if add_nos and arg_type is bool:
        parser.add_argument(
            '--no-{}'.format(name),
            action='store_const',
            dest=name,
            const=default if default is not _empty else False)


def make_parser(func_sig, description, epilog, add_nos):
    '''
    Given the signature of a function, create an ArgumentParser
    '''
    parser = ArgumentParser(description=description, epilog=epilog)

    used_char_args = {'h'}

    # Arange the params so that single-character arguments are first. This
    # esnures they don't have to get --long versions. sorted is stable, so the
    # parameters will otherwise still be in relative order.
    params = sorted(
        func_sig.parameters.values(),
        key=lambda param: len(param.name) > 1)

    for param in params:
        _add_arguments(param, parser, used_char_args, add_nos)

    return parser


_DOCSTRING_SPLIT = compile_regex(r'\n\s*-{4,}\s*\n')


def parse_docstring(docstring):
    '''
    Given a docstring, parse it into a description and epilog part
    '''
    if docstring is None:
        return '', ''

    parts = _DOCSTRING_SPLIT.split(docstring)

    if len(parts) == 1:
        return docstring, ''
    elif len(parts) == 2:
        return parts[0], parts[1]
    else:
        raise TooManySplitsError()


def autoparse(
        func=None, *,
        description=None,
        epilog=None,
        add_nos=False,
        parser=None):
    '''
    This decorator converts a function that takes normal arguments into a
    function which takes a single optional argument, argv, parses it using an
    argparse.ArgumentParser, and calls the underlying function with the parsed
    arguments. If it is not given, sys.argv[1:] is used. This is so that the
    function can be used as a setuptools entry point, as well as a normal main
    function. sys.argv[1:] is not evaluated until the function is called, to
    allow injecting different arguments for testing.

    It uses the argument signature of the function to create an
    ArgumentParser. Parameters without defaults become positional parameters,
    while parameters *with* defaults become --options. Use annotations to set
    the type of the parameter.

    The `desctiption` and `epilog` parameters corrospond to the same respective
    argparse parameters. If no description is given, it defaults to the
    decorated functions's docstring, if present.

    If add_nos is True, every boolean option (that is, every parameter with a
    default of True/False or a type of bool) will have a --no- version created
    as well, which inverts the option. For instance, the --verbose option will
    have a --no-verbose counterpart. These are not mutually exclusive-
    whichever one appears last in the argument list will have precedence.

    If a parser is given, it is used instead of one generated from the function
    signature. In this case, no parser is created; instead, the given parser is
    used to parse the argv argument. The parser's results' argument names must
    match up with the parameter names of the decorated function.

    The decorated function is attached to the result as the `func` attribute,
    and the parser is attached as the `parser` attribute.
    '''

    # If @autoparse(...) is used instead of @autoparse
    if func is None:
        return lambda f: autoparse(
            f, description=description,
            epilog=epilog,
            add_nos=add_nos,
            parser=parser)

    func_sig = signature(func)

    docstr_description, docstr_epilog = parse_docstring(getdoc(func))

    if parser is None:
        parser = make_parser(
            func_sig,
            description or docstr_description,
            epilog or docstr_epilog,
            add_nos)

    @wraps(func)
    def autoparse_wrapper(argv=None):
        if argv is None:
            argv = sys.argv[1:]

        # Get empty argument binding, to fill with parsed arguments. This
        # object does all the heavy lifting of turning named arguments into
        # into correctly bound *args and **kwargs.
        parsed_args = func_sig.bind_partial()
        parsed_args.arguments.update(vars(parser.parse_args(argv)))

        return func(*parsed_args.args, **parsed_args.kwargs)

    # TODO: attach an updated __signature__ to autoparse_wrapper, just in case.

    # Attach the wrapped function and parser, and return the wrapper.
    autoparse_wrapper.func = func
    autoparse_wrapper.parser = parser
    return autoparse_wrapper


@contextmanager
def smart_open(filename_or_file, *args, **kwargs):
    '''
    This context manager allows you to open a filename, if you want to default
    some already-existing file object, like sys.stdout, which shouldn't be
    closed at the end of the context. If the filename argument is a str, bytes,
    or int, the file object is created via a call to open with the given *args
    and **kwargs, sent to the context, and closed at the end of the context,
    just like "with open(filename) as f:". If it isn't one of the openable
    types, the object simply sent to the context unchanged, and left unclosed
    at the end of the context. Example:

        def work_with_file(name=sys.stdout):
            with smart_open(name) as f:
                # Works correctly if name is a str filename or sys.stdout
                print("Some stuff", file=f)
                # If it was a filename, f is closed at the end here.
    '''
    if isinstance(filename_or_file, (str, bytes, int)):
        with open(filename_or_file, *args, **kwargs) as file:
            yield file
    else:
        yield filename_or_file

# === NexusCore/openenv\Lib\site-packages\win32\test\test_win32guistruct.py ===
import array
import unittest

import pythoncom
import win32con
import win32gui_struct


class TestBase(unittest.TestCase):
    def assertDictEquals(self, d, **kw):
        checked = {}
        for n, v in kw.items():
            self.assertEqual(v, d[n], f"'{n}' doesn't match: {v!r} != {d[n]!r}")
            checked[n] = True
        checked_keys = sorted(checked)
        passed_keys = sorted(kw)
        self.assertEqual(checked_keys, passed_keys)


class TestMenuItemInfo(TestBase):
    def _testPackUnpack(self, text):
        vals = {
            "fType": win32con.MFT_MENUBARBREAK,
            "fState": win32con.MFS_CHECKED,
            "wID": 123,
            "hSubMenu": 1234,
            "hbmpChecked": 12345,
            "hbmpUnchecked": 123456,
            "dwItemData": 1234567,
            "text": text,
            "hbmpItem": 321,
        }
        mii, extras = win32gui_struct.PackMENUITEMINFO(**vals)
        (
            fType,
            fState,
            wID,
            hSubMenu,
            hbmpChecked,
            hbmpUnchecked,
            dwItemData,
            text,
            hbmpItem,
        ) = win32gui_struct.UnpackMENUITEMINFO(mii)
        self.assertDictEquals(
            vals,
            fType=fType,
            fState=fState,
            wID=wID,
            hSubMenu=hSubMenu,
            hbmpChecked=hbmpChecked,
            hbmpUnchecked=hbmpUnchecked,
            dwItemData=dwItemData,
            text=text,
            hbmpItem=hbmpItem,
        )

    def testPackUnpack(self):
        self._testPackUnpack("Hello")

    def testPackUnpackNone(self):
        self._testPackUnpack(None)

    def testEmptyMenuItemInfo(self):
        mii, extra = win32gui_struct.EmptyMENUITEMINFO()
        (
            fType,
            fState,
            wID,
            hSubMenu,
            hbmpChecked,
            hbmpUnchecked,
            dwItemData,
            text,
            hbmpItem,
        ) = win32gui_struct.UnpackMENUITEMINFO(mii)
        self.assertEqual(fType, 0)
        self.assertEqual(fState, 0)
        self.assertEqual(wID, 0)
        self.assertEqual(hSubMenu, 0)
        self.assertEqual(hbmpChecked, 0)
        self.assertEqual(hbmpUnchecked, 0)
        self.assertEqual(dwItemData, 0)
        self.assertEqual(hbmpItem, 0)
        # it's not clear if UnpackMENUITEMINFO() should ignore cch, instead
        # assuming it is a buffer size rather than 'current length' - but it
        # never has (and this gives us every \0 in the string), and actually
        # helps us test the unicode/str semantics.
        self.assertEqual(text, "\0" * len(text))


class TestMenuInfo(TestBase):
    def testPackUnpack(self):
        vals = {
            "dwStyle": 1,
            "cyMax": 2,
            "hbrBack": 3,
            "dwContextHelpID": 4,
            "dwMenuData": 5,
        }

        mi = win32gui_struct.PackMENUINFO(**vals)
        (
            dwStyle,
            cyMax,
            hbrBack,
            dwContextHelpID,
            dwMenuData,
        ) = win32gui_struct.UnpackMENUINFO(mi)

        self.assertDictEquals(
            vals,
            dwStyle=dwStyle,
            cyMax=cyMax,
            hbrBack=hbrBack,
            dwContextHelpID=dwContextHelpID,
            dwMenuData=dwMenuData,
        )

    def testEmptyMenuItemInfo(self):
        mi = win32gui_struct.EmptyMENUINFO()
        (
            dwStyle,
            cyMax,
            hbrBack,
            dwContextHelpID,
            dwMenuData,
        ) = win32gui_struct.UnpackMENUINFO(mi)
        self.assertEqual(dwStyle, 0)
        self.assertEqual(cyMax, 0)
        self.assertEqual(hbrBack, 0)
        self.assertEqual(dwContextHelpID, 0)
        self.assertEqual(dwMenuData, 0)


class TestTreeViewItem(TestBase):
    def _testPackUnpack(self, text):
        vals = {
            "hitem": 1,
            "state": 2,
            "stateMask": 3,
            "text": text,
            "image": 4,
            "selimage": 5,
            "citems": 6,
            "param": 7,
        }

        ti, extra = win32gui_struct.PackTVITEM(**vals)
        (
            hitem,
            state,
            stateMask,
            text,
            image,
            selimage,
            citems,
            param,
        ) = win32gui_struct.UnpackTVITEM(ti)

        self.assertDictEquals(
            vals,
            hitem=hitem,
            state=state,
            stateMask=stateMask,
            text=text,
            image=image,
            selimage=selimage,
            citems=citems,
            param=param,
        )

    def testPackUnpack(self):
        self._testPackUnpack("Hello")

    def testPackUnpackNone(self):
        self._testPackUnpack(None)

    def testEmpty(self):
        ti, extras = win32gui_struct.EmptyTVITEM(0)
        (
            hitem,
            state,
            stateMask,
            text,
            image,
            selimage,
            citems,
            param,
        ) = win32gui_struct.UnpackTVITEM(ti)
        self.assertEqual(hitem, 0)
        self.assertEqual(state, 0)
        self.assertEqual(stateMask, 0)
        self.assertEqual(text, "")
        self.assertEqual(image, 0)
        self.assertEqual(selimage, 0)
        self.assertEqual(citems, 0)
        self.assertEqual(param, 0)


class TestListViewItem(TestBase):
    def _testPackUnpack(self, text):
        vals = {
            "item": None,
            "subItem": None,
            "state": 1,
            "stateMask": 2,
            "text": text,
            "image": 3,
            "param": 4,
            "indent": 5,
        }

        ti, extra = win32gui_struct.PackLVITEM(**vals)
        (
            item,
            subItem,
            state,
            stateMask,
            text,
            image,
            param,
            indent,
        ) = win32gui_struct.UnpackLVITEM(ti)

        # patch expected values.
        vals["item"] = 0
        vals["subItem"] = 0
        self.assertDictEquals(
            vals,
            item=item,
            subItem=subItem,
            state=state,
            stateMask=stateMask,
            text=text,
            image=image,
            param=param,
            indent=indent,
        )

    def testPackUnpack(self):
        self._testPackUnpack("Hello")

    def testPackUnpackNone(self):
        self._testPackUnpack(None)

    def testEmpty(self):
        ti, extras = win32gui_struct.EmptyLVITEM(1, 2)
        (
            item,
            subItem,
            state,
            stateMask,
            text,
            image,
            param,
            indent,
        ) = win32gui_struct.UnpackLVITEM(ti)
        self.assertEqual(item, 1)
        self.assertEqual(subItem, 2)
        self.assertEqual(state, 0)
        self.assertEqual(stateMask, 0)
        self.assertEqual(text, "")
        self.assertEqual(image, 0)
        self.assertEqual(param, 0)
        self.assertEqual(indent, 0)


class TestLVColumn(TestBase):
    def _testPackUnpack(self, text):
        vals = {"fmt": 1, "cx": 2, "text": text, "subItem": 3, "image": 4, "order": 5}

        ti, extra = win32gui_struct.PackLVCOLUMN(**vals)
        fmt, cx, text, subItem, image, order = win32gui_struct.UnpackLVCOLUMN(ti)

        self.assertDictEquals(
            vals, fmt=fmt, cx=cx, text=text, subItem=subItem, image=image, order=order
        )

    def testPackUnpack(self):
        self._testPackUnpack("Hello")

    def testPackUnpackNone(self):
        self._testPackUnpack(None)

    def testEmpty(self):
        ti, extras = win32gui_struct.EmptyLVCOLUMN()
        fmt, cx, text, subItem, image, order = win32gui_struct.UnpackLVCOLUMN(ti)
        self.assertEqual(fmt, 0)
        self.assertEqual(cx, 0)
        self.assertEqual(text, "")
        self.assertEqual(subItem, 0)
        self.assertEqual(image, 0)
        self.assertEqual(order, 0)


class TestDEV_BROADCAST_HANDLE(TestBase):
    def testPackUnpack(self):
        s = win32gui_struct.PackDEV_BROADCAST_HANDLE(123)
        c = array.array("b", s)
        got = win32gui_struct.UnpackDEV_BROADCAST(c.buffer_info()[0])
        self.assertEqual(got.handle, 123)

    def testGUID(self):
        s = win32gui_struct.PackDEV_BROADCAST_HANDLE(123, guid=pythoncom.IID_IUnknown)
        c = array.array("b", s)
        got = win32gui_struct.UnpackDEV_BROADCAST(c.buffer_info()[0])
        self.assertEqual(got.handle, 123)
        self.assertEqual(got.eventguid, pythoncom.IID_IUnknown)


class TestDEV_BROADCAST_DEVICEINTERFACE(TestBase):
    def testPackUnpack(self):
        s = win32gui_struct.PackDEV_BROADCAST_DEVICEINTERFACE(
            pythoncom.IID_IUnknown, "hello"
        )
        c = array.array("b", s)
        got = win32gui_struct.UnpackDEV_BROADCAST(c.buffer_info()[0])
        self.assertEqual(got.classguid, pythoncom.IID_IUnknown)
        self.assertEqual(got.name, "hello")


class TestDEV_BROADCAST_VOLUME(TestBase):
    def testPackUnpack(self):
        s = win32gui_struct.PackDEV_BROADCAST_VOLUME(123, 456)
        c = array.array("b", s)
        got = win32gui_struct.UnpackDEV_BROADCAST(c.buffer_info()[0])
        self.assertEqual(got.unitmask, 123)
        self.assertEqual(got.flags, 456)


if __name__ == "__main__":
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\tornado\tcpclient.py ===
#
# Copyright 2014 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A non-blocking TCP connection factory.
"""

import functools
import socket
import numbers
import datetime
import ssl
import typing

from tornado.concurrent import Future, future_add_done_callback
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado import gen
from tornado.netutil import Resolver
from tornado.gen import TimeoutError

from typing import Any, Union, Dict, Tuple, List, Callable, Iterator, Optional

if typing.TYPE_CHECKING:
    from typing import Set  # noqa(F401)

_INITIAL_CONNECT_TIMEOUT = 0.3


class _Connector:
    """A stateless implementation of the "Happy Eyeballs" algorithm.

    "Happy Eyeballs" is documented in RFC6555 as the recommended practice
    for when both IPv4 and IPv6 addresses are available.

    In this implementation, we partition the addresses by family, and
    make the first connection attempt to whichever address was
    returned first by ``getaddrinfo``.  If that connection fails or
    times out, we begin a connection in parallel to the first address
    of the other family.  If there are additional failures we retry
    with other addresses, keeping one connection attempt per family
    in flight at a time.

    http://tools.ietf.org/html/rfc6555

    """

    def __init__(
        self,
        addrinfo: List[Tuple],
        connect: Callable[
            [socket.AddressFamily, Tuple], Tuple[IOStream, "Future[IOStream]"]
        ],
    ) -> None:
        self.io_loop = IOLoop.current()
        self.connect = connect

        self.future = (
            Future()
        )  # type: Future[Tuple[socket.AddressFamily, Any, IOStream]]
        self.timeout = None  # type: Optional[object]
        self.connect_timeout = None  # type: Optional[object]
        self.last_error = None  # type: Optional[Exception]
        self.remaining = len(addrinfo)
        self.primary_addrs, self.secondary_addrs = self.split(addrinfo)
        self.streams = set()  # type: Set[IOStream]

    @staticmethod
    def split(
        addrinfo: List[Tuple],
    ) -> Tuple[
        List[Tuple[socket.AddressFamily, Tuple]],
        List[Tuple[socket.AddressFamily, Tuple]],
    ]:
        """Partition the ``addrinfo`` list by address family.

        Returns two lists.  The first list contains the first entry from
        ``addrinfo`` and all others with the same family, and the
        second list contains all other addresses (normally one list will
        be AF_INET and the other AF_INET6, although non-standard resolvers
        may return additional families).
        """
        primary = []
        secondary = []
        primary_af = addrinfo[0][0]
        for af, addr in addrinfo:
            if af == primary_af:
                primary.append((af, addr))
            else:
                secondary.append((af, addr))
        return primary, secondary

    def start(
        self,
        timeout: float = _INITIAL_CONNECT_TIMEOUT,
        connect_timeout: Optional[Union[float, datetime.timedelta]] = None,
    ) -> "Future[Tuple[socket.AddressFamily, Any, IOStream]]":
        self.try_connect(iter(self.primary_addrs))
        self.set_timeout(timeout)
        if connect_timeout is not None:
            self.set_connect_timeout(connect_timeout)
        return self.future

    def try_connect(self, addrs: Iterator[Tuple[socket.AddressFamily, Tuple]]) -> None:
        try:
            af, addr = next(addrs)
        except StopIteration:
            # We've reached the end of our queue, but the other queue
            # might still be working.  Send a final error on the future
            # only when both queues are finished.
            if self.remaining == 0 and not self.future.done():
                self.future.set_exception(
                    self.last_error or IOError("connection failed")
                )
            return
        stream, future = self.connect(af, addr)
        self.streams.add(stream)
        future_add_done_callback(
            future, functools.partial(self.on_connect_done, addrs, af, addr)
        )

    def on_connect_done(
        self,
        addrs: Iterator[Tuple[socket.AddressFamily, Tuple]],
        af: socket.AddressFamily,
        addr: Tuple,
        future: "Future[IOStream]",
    ) -> None:
        self.remaining -= 1
        try:
            stream = future.result()
        except Exception as e:
            if self.future.done():
                return
            # Error: try again (but remember what happened so we have an
            # error to raise in the end)
            self.last_error = e
            self.try_connect(addrs)
            if self.timeout is not None:
                # If the first attempt failed, don't wait for the
                # timeout to try an address from the secondary queue.
                self.io_loop.remove_timeout(self.timeout)
                self.on_timeout()
            return
        self.clear_timeouts()
        if self.future.done():
            # This is a late arrival; just drop it.
            stream.close()
        else:
            self.streams.discard(stream)
            self.future.set_result((af, addr, stream))
            self.close_streams()

    def set_timeout(self, timeout: float) -> None:
        self.timeout = self.io_loop.add_timeout(
            self.io_loop.time() + timeout, self.on_timeout
        )

    def on_timeout(self) -> None:
        self.timeout = None
        if not self.future.done():
            self.try_connect(iter(self.secondary_addrs))

    def clear_timeout(self) -> None:
        if self.timeout is not None:
            self.io_loop.remove_timeout(self.timeout)

    def set_connect_timeout(
        self, connect_timeout: Union[float, datetime.timedelta]
    ) -> None:
        self.connect_timeout = self.io_loop.add_timeout(
            connect_timeout, self.on_connect_timeout
        )

    def on_connect_timeout(self) -> None:
        if not self.future.done():
            self.future.set_exception(TimeoutError())
        self.close_streams()

    def clear_timeouts(self) -> None:
        if self.timeout is not None:
            self.io_loop.remove_timeout(self.timeout)
        if self.connect_timeout is not None:
            self.io_loop.remove_timeout(self.connect_timeout)

    def close_streams(self) -> None:
        for stream in self.streams:
            stream.close()


class TCPClient:
    """A non-blocking TCP connection factory.

    .. versionchanged:: 5.0
       The ``io_loop`` argument (deprecated since version 4.1) has been removed.
    """

    def __init__(self, resolver: Optional[Resolver] = None) -> None:
        if resolver is not None:
            self.resolver = resolver
            self._own_resolver = False
        else:
            self.resolver = Resolver()
            self._own_resolver = True

    def close(self) -> None:
        if self._own_resolver:
            self.resolver.close()

    async def connect(
        self,
        host: str,
        port: int,
        af: socket.AddressFamily = socket.AF_UNSPEC,
        ssl_options: Optional[Union[Dict[str, Any], ssl.SSLContext]] = None,
        max_buffer_size: Optional[int] = None,
        source_ip: Optional[str] = None,
        source_port: Optional[int] = None,
        timeout: Optional[Union[float, datetime.timedelta]] = None,
    ) -> IOStream:
        """Connect to the given host and port.

        Asynchronously returns an `.IOStream` (or `.SSLIOStream` if
        ``ssl_options`` is not None).

        Using the ``source_ip`` kwarg, one can specify the source
        IP address to use when establishing the connection.
        In case the user needs to resolve and
        use a specific interface, it has to be handled outside
        of Tornado as this depends very much on the platform.

        Raises `TimeoutError` if the input future does not complete before
        ``timeout``, which may be specified in any form allowed by
        `.IOLoop.add_timeout` (i.e. a `datetime.timedelta` or an absolute time
        relative to `.IOLoop.time`)

        Similarly, when the user requires a certain source port, it can
        be specified using the ``source_port`` arg.

        .. versionchanged:: 4.5
           Added the ``source_ip`` and ``source_port`` arguments.

        .. versionchanged:: 5.0
           Added the ``timeout`` argument.
        """
        if timeout is not None:
            if isinstance(timeout, numbers.Real):
                timeout = IOLoop.current().time() + timeout
            elif isinstance(timeout, datetime.timedelta):
                timeout = IOLoop.current().time() + timeout.total_seconds()
            else:
                raise TypeError("Unsupported timeout %r" % timeout)
        if timeout is not None:
            addrinfo = await gen.with_timeout(
                timeout, self.resolver.resolve(host, port, af)
            )
        else:
            addrinfo = await self.resolver.resolve(host, port, af)
        connector = _Connector(
            addrinfo,
            functools.partial(
                self._create_stream,
                max_buffer_size,
                source_ip=source_ip,
                source_port=source_port,
            ),
        )
        af, addr, stream = await connector.start(connect_timeout=timeout)
        # TODO: For better performance we could cache the (af, addr)
        # information here and re-use it on subsequent connections to
        # the same host. (http://tools.ietf.org/html/rfc6555#section-4.2)
        if ssl_options is not None:
            if timeout is not None:
                stream = await gen.with_timeout(
                    timeout,
                    stream.start_tls(
                        False, ssl_options=ssl_options, server_hostname=host
                    ),
                )
            else:
                stream = await stream.start_tls(
                    False, ssl_options=ssl_options, server_hostname=host
                )
        return stream

    def _create_stream(
        self,
        max_buffer_size: int,
        af: socket.AddressFamily,
        addr: Tuple,
        source_ip: Optional[str] = None,
        source_port: Optional[int] = None,
    ) -> Tuple[IOStream, "Future[IOStream]"]:
        # Always connect in plaintext; we'll convert to ssl if necessary
        # after one connection has completed.
        source_port_bind = source_port if isinstance(source_port, int) else 0
        source_ip_bind = source_ip
        if source_port_bind and not source_ip:
            # User required a specific port, but did not specify
            # a certain source IP, will bind to the default loopback.
            source_ip_bind = "::1" if af == socket.AF_INET6 else "127.0.0.1"
            # Trying to use the same address family as the requested af socket:
            # - 127.0.0.1 for IPv4
            # - ::1 for IPv6
        socket_obj = socket.socket(af)
        if source_port_bind or source_ip_bind:
            # If the user requires binding also to a specific IP/port.
            try:
                socket_obj.bind((source_ip_bind, source_port_bind))
            except OSError:
                socket_obj.close()
                # Fail loudly if unable to use the IP/port.
                raise
        try:
            stream = IOStream(socket_obj, max_buffer_size=max_buffer_size)
        except OSError as e:
            fu = Future()  # type: Future[IOStream]
            fu.set_exception(e)
            return stream, fu
        else:
            return stream, stream.connect(addr)

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_t_r_a_k.py ===
from fontTools.misc import sstruct
from fontTools.misc.fixedTools import (
    fixedToFloat as fi2fl,
    floatToFixed as fl2fi,
    floatToFixedToStr as fl2str,
    strToFixedToFloat as str2fl,
)
from fontTools.misc.textTools import bytesjoin, safeEval
from fontTools.ttLib import TTLibError
from . import DefaultTable
import struct
from collections.abc import MutableMapping


# Apple's documentation of 'trak':
# https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6trak.html

TRAK_HEADER_FORMAT = """
	> # big endian
	version:     16.16F
	format:      H
	horizOffset: H
	vertOffset:  H
	reserved:    H
"""

TRAK_HEADER_FORMAT_SIZE = sstruct.calcsize(TRAK_HEADER_FORMAT)


TRACK_DATA_FORMAT = """
	> # big endian
	nTracks:         H
	nSizes:          H
	sizeTableOffset: L
"""

TRACK_DATA_FORMAT_SIZE = sstruct.calcsize(TRACK_DATA_FORMAT)


TRACK_TABLE_ENTRY_FORMAT = """
	> # big endian
	track:      16.16F
	nameIndex:       H
	offset:          H
"""

TRACK_TABLE_ENTRY_FORMAT_SIZE = sstruct.calcsize(TRACK_TABLE_ENTRY_FORMAT)


# size values are actually '16.16F' fixed-point values, but here I do the
# fixedToFloat conversion manually instead of relying on sstruct
SIZE_VALUE_FORMAT = ">l"
SIZE_VALUE_FORMAT_SIZE = struct.calcsize(SIZE_VALUE_FORMAT)

# per-Size values are in 'FUnits', i.e. 16-bit signed integers
PER_SIZE_VALUE_FORMAT = ">h"
PER_SIZE_VALUE_FORMAT_SIZE = struct.calcsize(PER_SIZE_VALUE_FORMAT)


class table__t_r_a_k(DefaultTable.DefaultTable):
    """The AAT ``trak`` table can store per-size adjustments to each glyph's
    sidebearings to make when tracking is enabled, which applications can
    use to provide more visually balanced line spacing.

    See also https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6trak.html
    """

    dependencies = ["name"]

    def compile(self, ttFont):
        dataList = []
        offset = TRAK_HEADER_FORMAT_SIZE
        for direction in ("horiz", "vert"):
            trackData = getattr(self, direction + "Data", TrackData())
            offsetName = direction + "Offset"
            # set offset to 0 if None or empty
            if not trackData:
                setattr(self, offsetName, 0)
                continue
            # TrackData table format must be longword aligned
            alignedOffset = (offset + 3) & ~3
            padding, offset = b"\x00" * (alignedOffset - offset), alignedOffset
            setattr(self, offsetName, offset)

            data = trackData.compile(offset)
            offset += len(data)
            dataList.append(padding + data)

        self.reserved = 0
        tableData = bytesjoin([sstruct.pack(TRAK_HEADER_FORMAT, self)] + dataList)
        return tableData

    def decompile(self, data, ttFont):
        sstruct.unpack(TRAK_HEADER_FORMAT, data[:TRAK_HEADER_FORMAT_SIZE], self)
        for direction in ("horiz", "vert"):
            trackData = TrackData()
            offset = getattr(self, direction + "Offset")
            if offset != 0:
                trackData.decompile(data, offset)
            setattr(self, direction + "Data", trackData)

    def toXML(self, writer, ttFont):
        writer.simpletag("version", value=self.version)
        writer.newline()
        writer.simpletag("format", value=self.format)
        writer.newline()
        for direction in ("horiz", "vert"):
            dataName = direction + "Data"
            writer.begintag(dataName)
            writer.newline()
            trackData = getattr(self, dataName, TrackData())
            trackData.toXML(writer, ttFont)
            writer.endtag(dataName)
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "version":
            self.version = safeEval(attrs["value"])
        elif name == "format":
            self.format = safeEval(attrs["value"])
        elif name in ("horizData", "vertData"):
            trackData = TrackData()
            setattr(self, name, trackData)
            for element in content:
                if not isinstance(element, tuple):
                    continue
                name, attrs, content_ = element
                trackData.fromXML(name, attrs, content_, ttFont)


class TrackData(MutableMapping):
    def __init__(self, initialdata={}):
        self._map = dict(initialdata)

    def compile(self, offset):
        nTracks = len(self)
        sizes = self.sizes()
        nSizes = len(sizes)

        # offset to the start of the size subtable
        offset += TRACK_DATA_FORMAT_SIZE + TRACK_TABLE_ENTRY_FORMAT_SIZE * nTracks
        trackDataHeader = sstruct.pack(
            TRACK_DATA_FORMAT,
            {"nTracks": nTracks, "nSizes": nSizes, "sizeTableOffset": offset},
        )

        entryDataList = []
        perSizeDataList = []
        # offset to per-size tracking values
        offset += SIZE_VALUE_FORMAT_SIZE * nSizes
        # sort track table entries by track value
        for track, entry in sorted(self.items()):
            assert entry.nameIndex is not None
            entry.track = track
            entry.offset = offset
            entryDataList += [sstruct.pack(TRACK_TABLE_ENTRY_FORMAT, entry)]
            # sort per-size values by size
            for size, value in sorted(entry.items()):
                perSizeDataList += [struct.pack(PER_SIZE_VALUE_FORMAT, value)]
            offset += PER_SIZE_VALUE_FORMAT_SIZE * nSizes
        # sort size values
        sizeDataList = [
            struct.pack(SIZE_VALUE_FORMAT, fl2fi(sv, 16)) for sv in sorted(sizes)
        ]

        data = bytesjoin(
            [trackDataHeader] + entryDataList + sizeDataList + perSizeDataList
        )
        return data

    def decompile(self, data, offset):
        # initial offset is from the start of trak table to the current TrackData
        trackDataHeader = data[offset : offset + TRACK_DATA_FORMAT_SIZE]
        if len(trackDataHeader) != TRACK_DATA_FORMAT_SIZE:
            raise TTLibError("not enough data to decompile TrackData header")
        sstruct.unpack(TRACK_DATA_FORMAT, trackDataHeader, self)
        offset += TRACK_DATA_FORMAT_SIZE

        nSizes = self.nSizes
        sizeTableOffset = self.sizeTableOffset
        sizeTable = []
        for i in range(nSizes):
            sizeValueData = data[
                sizeTableOffset : sizeTableOffset + SIZE_VALUE_FORMAT_SIZE
            ]
            if len(sizeValueData) < SIZE_VALUE_FORMAT_SIZE:
                raise TTLibError("not enough data to decompile TrackData size subtable")
            (sizeValue,) = struct.unpack(SIZE_VALUE_FORMAT, sizeValueData)
            sizeTable.append(fi2fl(sizeValue, 16))
            sizeTableOffset += SIZE_VALUE_FORMAT_SIZE

        for i in range(self.nTracks):
            entry = TrackTableEntry()
            entryData = data[offset : offset + TRACK_TABLE_ENTRY_FORMAT_SIZE]
            if len(entryData) < TRACK_TABLE_ENTRY_FORMAT_SIZE:
                raise TTLibError("not enough data to decompile TrackTableEntry record")
            sstruct.unpack(TRACK_TABLE_ENTRY_FORMAT, entryData, entry)
            perSizeOffset = entry.offset
            for j in range(nSizes):
                size = sizeTable[j]
                perSizeValueData = data[
                    perSizeOffset : perSizeOffset + PER_SIZE_VALUE_FORMAT_SIZE
                ]
                if len(perSizeValueData) < PER_SIZE_VALUE_FORMAT_SIZE:
                    raise TTLibError(
                        "not enough data to decompile per-size track values"
                    )
                (perSizeValue,) = struct.unpack(PER_SIZE_VALUE_FORMAT, perSizeValueData)
                entry[size] = perSizeValue
                perSizeOffset += PER_SIZE_VALUE_FORMAT_SIZE
            self[entry.track] = entry
            offset += TRACK_TABLE_ENTRY_FORMAT_SIZE

    def toXML(self, writer, ttFont):
        nTracks = len(self)
        nSizes = len(self.sizes())
        writer.comment("nTracks=%d, nSizes=%d" % (nTracks, nSizes))
        writer.newline()
        for track, entry in sorted(self.items()):
            assert entry.nameIndex is not None
            entry.track = track
            entry.toXML(writer, ttFont)

    def fromXML(self, name, attrs, content, ttFont):
        if name != "trackEntry":
            return
        entry = TrackTableEntry()
        entry.fromXML(name, attrs, content, ttFont)
        self[entry.track] = entry

    def sizes(self):
        if not self:
            return frozenset()
        tracks = list(self.tracks())
        sizes = self[tracks.pop(0)].sizes()
        for track in tracks:
            entrySizes = self[track].sizes()
            if sizes != entrySizes:
                raise TTLibError(
                    "'trak' table entries must specify the same sizes: "
                    "%s != %s" % (sorted(sizes), sorted(entrySizes))
                )
        return frozenset(sizes)

    def __getitem__(self, track):
        return self._map[track]

    def __delitem__(self, track):
        del self._map[track]

    def __setitem__(self, track, entry):
        self._map[track] = entry

    def __len__(self):
        return len(self._map)

    def __iter__(self):
        return iter(self._map)

    def keys(self):
        return self._map.keys()

    tracks = keys

    def __repr__(self):
        return "TrackData({})".format(self._map if self else "")


class TrackTableEntry(MutableMapping):
    def __init__(self, values={}, nameIndex=None):
        self.nameIndex = nameIndex
        self._map = dict(values)

    def toXML(self, writer, ttFont):
        name = ttFont["name"].getDebugName(self.nameIndex)
        writer.begintag(
            "trackEntry",
            (("value", fl2str(self.track, 16)), ("nameIndex", self.nameIndex)),
        )
        writer.newline()
        if name:
            writer.comment(name)
            writer.newline()
        for size, perSizeValue in sorted(self.items()):
            writer.simpletag("track", size=fl2str(size, 16), value=perSizeValue)
            writer.newline()
        writer.endtag("trackEntry")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        self.track = str2fl(attrs["value"], 16)
        self.nameIndex = safeEval(attrs["nameIndex"])
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, _ = element
            if name != "track":
                continue
            size = str2fl(attrs["size"], 16)
            self[size] = safeEval(attrs["value"])

    def __getitem__(self, size):
        return self._map[size]

    def __delitem__(self, size):
        del self._map[size]

    def __setitem__(self, size, value):
        self._map[size] = value

    def __len__(self):
        return len(self._map)

    def __iter__(self):
        return iter(self._map)

    def keys(self):
        return self._map.keys()

    sizes = keys

    def __repr__(self):
        return "TrackTableEntry({}, nameIndex={})".format(self._map, self.nameIndex)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.nameIndex == other.nameIndex and dict(self) == dict(other)

    def __ne__(self, other):
        result = self.__eq__(other)
        return result if result is NotImplemented else not result

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\model_service\transports\grpc_asyncio.py ===
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
from typing import Awaitable, Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, grpc_helpers_async
from google.api_core import retry_async as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta2.types import model, model_service

from .base import DEFAULT_CLIENT_INFO, ModelServiceTransport
from .grpc import ModelServiceGrpcTransport


class ModelServiceGrpcAsyncIOTransport(ModelServiceTransport):
    """gRPC AsyncIO backend transport for ModelService.

    Provides methods for getting metadata information about
    Generative Models.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _grpc_channel: aio.Channel
    _stubs: Dict[str, Callable] = {}

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> aio.Channel:
        """Create and return a gRPC AsyncIO channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            aio.Channel: A gRPC AsyncIO channel object.
        """

        return grpc_helpers_async.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[aio.Channel, Callable[..., aio.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
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
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            channel (Optional[Union[aio.Channel, Callable[..., aio.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, aio.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None
        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @property
    def grpc_channel(self) -> aio.Channel:
        """Create the channel designed to connect to this service.

        This property caches on the instance; repeated calls return
        the same channel.
        """
        # Return the channel from cache.
        return self._grpc_channel

    @property
    def get_model(
        self,
    ) -> Callable[[model_service.GetModelRequest], Awaitable[model.Model]]:
        r"""Return a callable for the get model method over gRPC.

        Gets information about a specific Model.

        Returns:
            Callable[[~.GetModelRequest],
                    Awaitable[~.Model]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_model" not in self._stubs:
            self._stubs["get_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta2.ModelService/GetModel",
                request_serializer=model_service.GetModelRequest.serialize,
                response_deserializer=model.Model.deserialize,
            )
        return self._stubs["get_model"]

    @property
    def list_models(
        self,
    ) -> Callable[
        [model_service.ListModelsRequest], Awaitable[model_service.ListModelsResponse]
    ]:
        r"""Return a callable for the list models method over gRPC.

        Lists models available through the API.

        Returns:
            Callable[[~.ListModelsRequest],
                    Awaitable[~.ListModelsResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_models" not in self._stubs:
            self._stubs["list_models"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta2.ModelService/ListModels",
                request_serializer=model_service.ListModelsRequest.serialize,
                response_deserializer=model_service.ListModelsResponse.deserialize,
            )
        return self._stubs["list_models"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.get_model: gapic_v1.method_async.wrap_method(
                self.get_model,
                default_retry=retries.AsyncRetry(
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
            self.list_models: gapic_v1.method_async.wrap_method(
                self.list_models,
                default_retry=retries.AsyncRetry(
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
        return self.grpc_channel.close()


__all__ = ("ModelServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai\responses\transformation.py ===
from typing import TYPE_CHECKING, Any, Dict, Optional, Union, cast

import httpx

import litellm
from litellm._logging import verbose_logger
from litellm.llms.base_llm.responses.transformation import BaseResponsesAPIConfig
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import *
from litellm.types.responses.main import *
from litellm.types.router import GenericLiteLLMParams

from ..common_utils import OpenAIError

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class OpenAIResponsesAPIConfig(BaseResponsesAPIConfig):
    def get_supported_openai_params(self, model: str) -> list:
        """
        All OpenAI Responses API params are supported
        """
        return [
            "input",
            "model",
            "include",
            "instructions",
            "max_output_tokens",
            "metadata",
            "parallel_tool_calls",
            "previous_response_id",
            "reasoning",
            "store",
            "background",
            "stream",
            "prompt",
            "temperature",
            "text",
            "tool_choice",
            "tools",
            "top_p",
            "truncation",
            "user",
            "extra_headers",
            "extra_query",
            "extra_body",
            "timeout",
        ]

    def map_openai_params(
        self,
        response_api_optional_params: ResponsesAPIOptionalRequestParams,
        model: str,
        drop_params: bool,
    ) -> Dict:
        """No mapping applied since inputs are in OpenAI spec already"""
        return dict(response_api_optional_params)

    def transform_responses_api_request(
        self,
        model: str,
        input: Union[str, ResponseInputParam],
        response_api_optional_request_params: Dict,
        litellm_params: GenericLiteLLMParams,
        headers: dict,
    ) -> Dict:
        """No transform applied since inputs are in OpenAI spec already"""
        return dict(
            ResponsesAPIRequestParams(
                model=model, input=input, **response_api_optional_request_params
            )
        )

    def transform_response_api_response(
        self,
        model: str,
        raw_response: httpx.Response,
        logging_obj: LiteLLMLoggingObj,
    ) -> ResponsesAPIResponse:
        """No transform applied since outputs are in OpenAI spec already"""
        try:
            raw_response_json = raw_response.json()
        except Exception:
            raise OpenAIError(
                message=raw_response.text, status_code=raw_response.status_code
            )
        return ResponsesAPIResponse(**raw_response_json)

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

        return f"{api_base}/responses"

    def transform_streaming_response(
        self,
        model: str,
        parsed_chunk: dict,
        logging_obj: LiteLLMLoggingObj,
    ) -> ResponsesAPIStreamingResponse:
        """
        Transform a parsed streaming response chunk into a ResponsesAPIStreamingResponse
        """
        # Convert the dictionary to a properly typed ResponsesAPIStreamingResponse
        verbose_logger.debug("Raw OpenAI Chunk=%s", parsed_chunk)
        event_type = str(parsed_chunk.get("type"))
        event_pydantic_model = OpenAIResponsesAPIConfig.get_event_model_class(
            event_type=event_type
        )
        return event_pydantic_model(**parsed_chunk)

    @staticmethod
    def get_event_model_class(event_type: str) -> Any:
        """
        Returns the appropriate event model class based on the event type.

        Args:
            event_type (str): The type of event from the response chunk

        Returns:
            Any: The corresponding event model class

        Raises:
            ValueError: If the event type is unknown
        """
        event_models = {
            ResponsesAPIStreamEvents.RESPONSE_CREATED: ResponseCreatedEvent,
            ResponsesAPIStreamEvents.RESPONSE_IN_PROGRESS: ResponseInProgressEvent,
            ResponsesAPIStreamEvents.RESPONSE_COMPLETED: ResponseCompletedEvent,
            ResponsesAPIStreamEvents.RESPONSE_FAILED: ResponseFailedEvent,
            ResponsesAPIStreamEvents.RESPONSE_INCOMPLETE: ResponseIncompleteEvent,
            ResponsesAPIStreamEvents.OUTPUT_ITEM_ADDED: OutputItemAddedEvent,
            ResponsesAPIStreamEvents.OUTPUT_ITEM_DONE: OutputItemDoneEvent,
            ResponsesAPIStreamEvents.CONTENT_PART_ADDED: ContentPartAddedEvent,
            ResponsesAPIStreamEvents.CONTENT_PART_DONE: ContentPartDoneEvent,
            ResponsesAPIStreamEvents.OUTPUT_TEXT_DELTA: OutputTextDeltaEvent,
            ResponsesAPIStreamEvents.OUTPUT_TEXT_ANNOTATION_ADDED: OutputTextAnnotationAddedEvent,
            ResponsesAPIStreamEvents.OUTPUT_TEXT_DONE: OutputTextDoneEvent,
            ResponsesAPIStreamEvents.REFUSAL_DELTA: RefusalDeltaEvent,
            ResponsesAPIStreamEvents.REFUSAL_DONE: RefusalDoneEvent,
            ResponsesAPIStreamEvents.FUNCTION_CALL_ARGUMENTS_DELTA: FunctionCallArgumentsDeltaEvent,
            ResponsesAPIStreamEvents.FUNCTION_CALL_ARGUMENTS_DONE: FunctionCallArgumentsDoneEvent,
            ResponsesAPIStreamEvents.FILE_SEARCH_CALL_IN_PROGRESS: FileSearchCallInProgressEvent,
            ResponsesAPIStreamEvents.FILE_SEARCH_CALL_SEARCHING: FileSearchCallSearchingEvent,
            ResponsesAPIStreamEvents.FILE_SEARCH_CALL_COMPLETED: FileSearchCallCompletedEvent,
            ResponsesAPIStreamEvents.WEB_SEARCH_CALL_IN_PROGRESS: WebSearchCallInProgressEvent,
            ResponsesAPIStreamEvents.WEB_SEARCH_CALL_SEARCHING: WebSearchCallSearchingEvent,
            ResponsesAPIStreamEvents.WEB_SEARCH_CALL_COMPLETED: WebSearchCallCompletedEvent,
            ResponsesAPIStreamEvents.ERROR: ErrorEvent,
        }

        model_class = event_models.get(cast(ResponsesAPIStreamEvents, event_type))
        if not model_class:
            return GenericEvent

        return model_class

    def should_fake_stream(
        self,
        model: Optional[str],
        stream: Optional[bool],
        custom_llm_provider: Optional[str] = None,
    ) -> bool:
        if stream is not True:
            return False
        if model is not None:
            try:
                if (
                    litellm.utils.supports_native_streaming(
                        model=model,
                        custom_llm_provider=custom_llm_provider,
                    )
                    is False
                ):
                    return True
            except Exception as e:
                verbose_logger.debug(
                    f"Error getting model info in OpenAIResponsesAPIConfig: {e}"
                )
        return False

    #########################################################
    ########## DELETE RESPONSE API TRANSFORMATION ##############
    #########################################################
    def transform_delete_response_api_request(
        self,
        response_id: str,
        api_base: str,
        litellm_params: GenericLiteLLMParams,
        headers: dict,
    ) -> Tuple[str, Dict]:
        """
        Transform the delete response API request into a URL and data

        OpenAI API expects the following request
        - DELETE /v1/responses/{response_id}
        """
        url = f"{api_base}/{response_id}"
        data: Dict = {}
        return url, data

    def transform_delete_response_api_response(
        self,
        raw_response: httpx.Response,
        logging_obj: LiteLLMLoggingObj,
    ) -> DeleteResponseResult:
        """
        Transform the delete response API response into a DeleteResponseResult
        """
        try:
            raw_response_json = raw_response.json()
        except Exception:
            raise OpenAIError(
                message=raw_response.text, status_code=raw_response.status_code
            )
        return DeleteResponseResult(**raw_response_json)

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
        url = f"{api_base}/{response_id}"
        data: Dict = {}
        return url, data

    def transform_get_response_api_response(
        self,
        raw_response: httpx.Response,
        logging_obj: LiteLLMLoggingObj,
    ) -> ResponsesAPIResponse:
        """
        Transform the get response API response into a ResponsesAPIResponse
        """
        try:
            raw_response_json = raw_response.json()
        except Exception:
            raise OpenAIError(
                message=raw_response.text, status_code=raw_response.status_code
            )
        return ResponsesAPIResponse(**raw_response_json)

    #########################################################
    ########## LIST INPUT ITEMS TRANSFORMATION #############
    #########################################################
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
        url = f"{api_base}/{response_id}/input_items"
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
        return url, params

    def transform_list_input_items_response(
        self,
        raw_response: httpx.Response,
        logging_obj: LiteLLMLoggingObj,
    ) -> Dict:
        try:
            return raw_response.json()
        except Exception:
            raise OpenAIError(
                message=raw_response.text, status_code=raw_response.status_code
            )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\guardrails\guardrail_hooks\lakera_ai_v2.py ===
import copy
import os
from datetime import datetime
from typing import Dict, List, Literal, Optional, Tuple, Union

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.exceptions import GuardrailRaisedException
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.proxy._types import UserAPIKeyAuth
from litellm.secret_managers.main import get_secret_str
from litellm.types.guardrails import GuardrailEventHooks
from litellm.types.llms.openai import AllMessageValues
from litellm.types.proxy.guardrails.guardrail_hooks.lakera_ai_v2 import (
    LakeraAIRequest,
    LakeraAIResponse,
)


class LakeraAIGuardrail(CustomGuardrail):
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        project_id: Optional[str] = None,
        payload: Optional[bool] = True,
        breakdown: Optional[bool] = True,
        metadata: Optional[Dict] = None,
        dev_info: Optional[bool] = True,
        **kwargs,
    ):
        """
        Initialize the LakeraAIGuardrail class.

        This calls: https://api.lakera.ai/v2/guard

        Args:
            api_key: Optional[str] = None,
            api_base: Optional[str] = None,
            project_id: Optional[str] = None,
            payload: Optional[bool] = True,
            breakdown: Optional[bool] = True,
            metadata: Optional[Dict] = None,
            dev_info: Optional[bool] = True,
        """
        self.async_handler = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.GuardrailCallback
        )
        self.lakera_api_key = api_key or os.environ["LAKERA_API_KEY"]
        self.project_id = project_id
        self.api_base = (
            api_base or get_secret_str("LAKERA_API_BASE") or "https://api.lakera.ai"
        )
        self.payload: Optional[bool] = payload
        self.breakdown: Optional[bool] = breakdown
        self.metadata: Optional[Dict] = metadata
        self.dev_info: Optional[bool] = dev_info
        super().__init__(**kwargs)

    async def call_v2_guard(
        self,
        messages: List[AllMessageValues],
        request_data: Dict,
    ) -> Tuple[LakeraAIResponse, Dict]:
        """
        Call the Lakera AI v2 guard API.
        """
        status: Literal["success", "failure"] = "success"
        exception_str: str = ""
        start_time: datetime = datetime.now()
        lakera_response: Optional[LakeraAIResponse] = None
        request: Dict = {}
        masked_entity_count: Dict = {}
        try:
            request = dict(
                LakeraAIRequest(
                    messages=messages,
                    project_id=self.project_id,
                    payload=self.payload,
                    breakdown=self.breakdown,
                    metadata=self.metadata,
                    dev_info=self.dev_info,
                )
            )
            verbose_proxy_logger.debug("Lakera AI v2 guard request: %s", request)
            response = await self.async_handler.post(
                url=f"{self.api_base}/v2/guard",
                headers={"Authorization": f"Bearer {self.lakera_api_key}"},
                json=request,
            )
            verbose_proxy_logger.debug(
                "Lakera AI v2 guard response: %s", response.json()
            )
            lakera_response = LakeraAIResponse(**response.json())
            return lakera_response, masked_entity_count
        except Exception as e:
            status = "failure"
            exception_str = str(e)
            raise e
        finally:
            ####################################################
            # Create Guardrail Trace for logging on Langfuse, Datadog, etc.
            ####################################################
            guardrail_json_response: Union[Exception, str, dict, List[dict]] = {}
            if status == "success":
                copy_lakera_response_dict = (
                    dict(copy.deepcopy(lakera_response)) if lakera_response else {}
                )
                # payload contains PII, we don't want to log it
                copy_lakera_response_dict.pop("payload")
                guardrail_json_response = copy_lakera_response_dict
            else:
                guardrail_json_response = exception_str
            self.add_standard_logging_guardrail_information_to_request_data(
                guardrail_json_response=guardrail_json_response,
                guardrail_status=status,
                request_data=request_data,
                start_time=start_time.timestamp(),
                end_time=datetime.now().timestamp(),
                duration=(datetime.now() - start_time).total_seconds(),
                masked_entity_count=masked_entity_count,
            )

    def _mask_pii_in_messages(
        self,
        messages: List[AllMessageValues],
        lakera_response: Optional[LakeraAIResponse],
        masked_entity_count: Dict,
    ) -> List[AllMessageValues]:
        """
        Return a copy of messages with any detected PII replaced by
        “[MASKED <TYPE>]” tokens.
        """
        payload = lakera_response.get("payload") if lakera_response else None
        if not payload:
            return messages

        # For each message, find its detections on the fly
        for idx, msg in enumerate(messages):
            content = msg.get("content", "")
            if not content:
                continue

            # For v1, we only support masking content strings
            if not isinstance(content, str):
                continue

            # Filter only detections for this message
            detected_modifications = [d for d in payload if d.get("message_id") == idx]
            if not detected_modifications:
                continue

            for modification in detected_modifications:
                start, end = modification.get("start", 0), modification.get("end", 0)

                # Extract the type (e.g. 'credit_card' → 'CREDIT_CARD')
                detector_type = modification.get("detector_type", "")
                if not detector_type:
                    continue

                typ = detector_type.split("/")[-1].upper() or "PII"
                mask = f"[MASKED {typ}]"
                if start is not None and end is not None:
                    content = self.mask_content_in_string(
                        content_string=content,
                        mask_string=mask,
                        start_index=start,
                        end_index=end,
                    )
                    masked_entity_count[typ] = masked_entity_count.get(typ, 0) + 1

            msg["content"] = content
        return messages

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: litellm.DualCache,
        data: Dict,
        call_type: Literal[
            "completion",
            "text_completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
            "pass_through_endpoint",
            "rerank",
        ],
    ) -> Optional[Union[Exception, str, Dict]]:
        from litellm.proxy.common_utils.callback_utils import (
            add_guardrail_to_applied_guardrails_header,
        )

        verbose_proxy_logger.debug("Lakera AI: pre_call_hook")

        event_type: GuardrailEventHooks = GuardrailEventHooks.pre_call
        if self.should_run_guardrail(data=data, event_type=event_type) is not True:
            verbose_proxy_logger.debug(
                "Lakera AI: not running guardrail. Guardrail is disabled."
            )
            return data

        new_messages: Optional[List[AllMessageValues]] = data.get("messages")
        if new_messages is None:
            verbose_proxy_logger.warning(
                "Lakera AI: not running guardrail. No messages in data"
            )
            return data

        #########################################################
        ########## 1. Make the Lakera AI v2 guard API request ##########
        #########################################################
        lakera_guardrail_response, masked_entity_count = await self.call_v2_guard(
            messages=new_messages,
            request_data=data,
        )

        #########################################################
        ########## 2. Handle flagged content ##########
        #########################################################
        if lakera_guardrail_response.get("flagged") is True:
            # If only PII violations exist, mask the PII
            if self._is_only_pii_violation(lakera_guardrail_response):
                data["messages"] = self._mask_pii_in_messages(
                    messages=new_messages,
                    lakera_response=lakera_guardrail_response,
                    masked_entity_count=masked_entity_count,
                )
                verbose_proxy_logger.info(
                    "Lakera AI: Masked PII in messages instead of blocking request"
                )
            else:
                # If there are other violations or not set to mask PII, raise exception
                raise GuardrailRaisedException(
                    guardrail_name=self.guardrail_name,
                    message="Lakera AI flagged this request. Please review the request and try again.",
                )

        #########################################################
        ########## 3. Add the guardrail to the applied guardrails header ##########
        #########################################################
        add_guardrail_to_applied_guardrails_header(
            request_data=data, guardrail_name=self.guardrail_name
        )

        return data

    async def async_moderation_hook(
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        call_type: Literal[
            "completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
            "responses",
        ],
    ):
        from litellm.proxy.common_utils.callback_utils import (
            add_guardrail_to_applied_guardrails_header,
        )

        event_type: GuardrailEventHooks = GuardrailEventHooks.during_call
        if self.should_run_guardrail(data=data, event_type=event_type) is not True:
            return

        new_messages: Optional[List[AllMessageValues]] = data.get("messages")
        if new_messages is None:
            verbose_proxy_logger.warning(
                "Lakera AI: not running guardrail. No messages in data"
            )
            return

        #########################################################
        ########## 1. Make the Lakera AI v2 guard API request ##########
        #########################################################
        lakera_guardrail_response, masked_entity_count = await self.call_v2_guard(
            messages=new_messages,
            request_data=data,
        )

        #########################################################
        ########## 2. Handle flagged content ##########
        #########################################################
        if lakera_guardrail_response.get("flagged") is True:
            # If only PII violations exist, mask the PII
            if self._is_only_pii_violation(lakera_guardrail_response):
                data["messages"] = self._mask_pii_in_messages(
                    messages=new_messages,
                    lakera_response=lakera_guardrail_response,
                    masked_entity_count=masked_entity_count,
                )
                verbose_proxy_logger.info(
                    "Lakera AI: Masked PII in messages instead of blocking request"
                )
            else:
                # If there are other violations or not set to mask PII, raise exception
                raise GuardrailRaisedException(
                    guardrail_name=self.guardrail_name,
                    message="Lakera AI flagged this request. Please review the request and try again.",
                )

        #########################################################
        ########## 3. Add the guardrail to the applied guardrails header ##########
        #########################################################
        add_guardrail_to_applied_guardrails_header(
            request_data=data, guardrail_name=self.guardrail_name
        )

        return data

    def _is_only_pii_violation(
        self, lakera_response: Optional[LakeraAIResponse]
    ) -> bool:
        """
        Returns True if there are only PII violations in the response.
        """
        if not lakera_response:
            return False

        for item in lakera_response.get("payload", []) or []:
            detector_type = item.get("detector_type", "") or ""
            if not detector_type.startswith("pii/"):
                return False
        return True

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\pass_through_endpoints\llm_provider_handlers\assembly_passthrough_logging_handler.py ===
import asyncio
import json
import time
from datetime import datetime
from typing import Literal, Optional, TypedDict
from urllib.parse import urlparse

import httpx

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.litellm_core_utils.litellm_logging import (
    get_standard_logging_object_payload,
)
from litellm.litellm_core_utils.thread_pool_executor import executor
from litellm.types.passthrough_endpoints.assembly_ai import (
    ASSEMBLY_AI_MAX_POLLING_ATTEMPTS,
    ASSEMBLY_AI_POLLING_INTERVAL,
)
from litellm.types.passthrough_endpoints.pass_through_endpoints import (
    PassthroughStandardLoggingPayload,
)


class AssemblyAITranscriptResponse(TypedDict, total=False):
    id: str
    speech_model: str
    acoustic_model: str
    language_code: str
    status: str
    audio_duration: float


class AssemblyAIPassthroughLoggingHandler:
    def __init__(self):
        self.assembly_ai_base_url = "https://api.assemblyai.com"
        self.assembly_ai_eu_base_url = "https://eu.assemblyai.com"
        """
        The base URL for the AssemblyAI API
        """

        self.polling_interval: float = ASSEMBLY_AI_POLLING_INTERVAL
        """
        The polling interval for the AssemblyAI API. 
        litellm needs to poll the GET /transcript/{transcript_id} endpoint to get the status of the transcript.
        """

        self.max_polling_attempts = ASSEMBLY_AI_MAX_POLLING_ATTEMPTS
        """
        The maximum number of polling attempts for the AssemblyAI API.
        """

    def assemblyai_passthrough_logging_handler(
        self,
        httpx_response: httpx.Response,
        response_body: dict,
        logging_obj: LiteLLMLoggingObj,
        url_route: str,
        result: str,
        start_time: datetime,
        end_time: datetime,
        cache_hit: bool,
        **kwargs,
    ):
        """
        Since cost tracking requires polling the AssemblyAI API, we need to handle this in a separate thread. Hence the executor.submit.
        """
        executor.submit(
            self._handle_assemblyai_passthrough_logging,
            httpx_response,
            response_body,
            logging_obj,
            url_route,
            result,
            start_time,
            end_time,
            cache_hit,
            **kwargs,
        )

    def _handle_assemblyai_passthrough_logging(
        self,
        httpx_response: httpx.Response,
        response_body: dict,
        logging_obj: LiteLLMLoggingObj,
        url_route: str,
        result: str,
        start_time: datetime,
        end_time: datetime,
        cache_hit: bool,
        **kwargs,
    ):
        """
        Handles logging for AssemblyAI successful passthrough requests
        """
        from ..pass_through_endpoints import pass_through_endpoint_logging

        model = response_body.get("speech_model", "")
        verbose_proxy_logger.debug(
            "response body %s", json.dumps(response_body, indent=4)
        )
        kwargs["model"] = model
        kwargs["custom_llm_provider"] = "assemblyai"
        response_cost: Optional[float] = None

        transcript_id = response_body.get("id")
        if transcript_id is None:
            raise ValueError(
                "Transcript ID is required to log the cost of the transcription"
            )
        transcript_response = self._poll_assembly_for_transcript_response(
            transcript_id=transcript_id, url_route=url_route
        )
        verbose_proxy_logger.debug(
            "finished polling assembly for transcript response- got transcript response %s",
            json.dumps(transcript_response, indent=4),
        )
        if transcript_response:
            cost = self.get_cost_for_assembly_transcript(
                speech_model=model,
                transcript_response=transcript_response,
            )
            response_cost = cost

        # Make standard logging object for Vertex AI
        standard_logging_object = get_standard_logging_object_payload(
            kwargs=kwargs,
            init_response_obj=transcript_response,
            start_time=start_time,
            end_time=end_time,
            logging_obj=logging_obj,
            status="success",
        )

        passthrough_logging_payload: Optional[PassthroughStandardLoggingPayload] = (  # type: ignore
            kwargs.get("passthrough_logging_payload")
        )

        verbose_proxy_logger.debug(
            "standard_passthrough_logging_object %s",
            json.dumps(passthrough_logging_payload, indent=4),
        )

        # pretty print standard logging object
        verbose_proxy_logger.debug(
            "standard_logging_object= %s", json.dumps(standard_logging_object, indent=4)
        )
        logging_obj.model_call_details["model"] = model
        logging_obj.model_call_details["custom_llm_provider"] = "assemblyai"
        logging_obj.model_call_details["response_cost"] = response_cost

        asyncio.run(
            pass_through_endpoint_logging._handle_logging(
                logging_obj=logging_obj,
                standard_logging_response_object=self._get_response_to_log(
                    transcript_response
                ),
                result=result,
                start_time=start_time,
                end_time=end_time,
                cache_hit=cache_hit,
                **kwargs,
            )
        )

        pass

    def _get_response_to_log(
        self, transcript_response: Optional[AssemblyAITranscriptResponse]
    ) -> dict:
        if transcript_response is None:
            return {}
        return dict(transcript_response)

    def _get_assembly_transcript(
        self,
        transcript_id: str,
        request_region: Optional[Literal["eu"]] = None,
    ) -> Optional[dict]:
        """
        Get the transcript details from AssemblyAI API

        Args:
            response_body (dict): Response containing the transcript ID

        Returns:
            Optional[dict]: Transcript details if successful, None otherwise
        """
        from litellm.proxy.pass_through_endpoints.llm_passthrough_endpoints import (
            passthrough_endpoint_router,
        )

        _base_url = (
            self.assembly_ai_eu_base_url
            if request_region == "eu"
            else self.assembly_ai_base_url
        )
        _api_key = passthrough_endpoint_router.get_credentials(
            custom_llm_provider="assemblyai",
            region_name=request_region,
        )
        if _api_key is None:
            raise ValueError("AssemblyAI API key not found")
        try:
            url = f"{_base_url}/v2/transcript/{transcript_id}"
            headers = {
                "Authorization": f"Bearer {_api_key}",
                "Content-Type": "application/json",
            }

            response = httpx.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            verbose_proxy_logger.exception(
                f"[Non blocking logging error] Error getting AssemblyAI transcript: {str(e)}"
            )
            return None

    def _poll_assembly_for_transcript_response(
        self,
        transcript_id: str,
        url_route: Optional[str] = None,
    ) -> Optional[AssemblyAITranscriptResponse]:
        """
        Poll the status of the transcript until it is completed or timeout (30 minutes)
        """
        for _ in range(
            self.max_polling_attempts
        ):  # 180 attempts * 10s = 30 minutes max
            transcript = self._get_assembly_transcript(
                request_region=AssemblyAIPassthroughLoggingHandler._get_assembly_region_from_url(
                    url=url_route
                ),
                transcript_id=transcript_id,
            )
            if transcript is None:
                return None
            if (
                transcript.get("status") == "completed"
                or transcript.get("status") == "error"
            ):
                return AssemblyAITranscriptResponse(**transcript)
            time.sleep(self.polling_interval)
        return None

    @staticmethod
    def get_cost_for_assembly_transcript(
        transcript_response: AssemblyAITranscriptResponse,
        speech_model: str,
    ) -> Optional[float]:
        """
        Get the cost for the assembly transcript
        """
        _audio_duration = transcript_response.get("audio_duration")
        if _audio_duration is None:
            return None
        _cost_per_second = (
            AssemblyAIPassthroughLoggingHandler.get_cost_per_second_for_assembly_model(
                speech_model=speech_model
            )
        )
        if _cost_per_second is None:
            return None
        return _audio_duration * _cost_per_second

    @staticmethod
    def get_cost_per_second_for_assembly_model(speech_model: str) -> Optional[float]:
        """
        Get the cost per second for the assembly model.
        Falls back to assemblyai/nano if the specific speech model info cannot be found.
        """
        try:
            # First try with the provided speech model
            try:
                model_info = litellm.get_model_info(
                    model=speech_model,
                    custom_llm_provider="assemblyai",
                )
                if model_info and model_info.get("input_cost_per_second") is not None:
                    return model_info.get("input_cost_per_second")
            except Exception:
                pass  # Continue to fallback if model not found

            # Fallback to assemblyai/nano if speech model info not found
            try:
                model_info = litellm.get_model_info(
                    model="assemblyai/nano",
                    custom_llm_provider="assemblyai",
                )
                if model_info and model_info.get("input_cost_per_second") is not None:
                    return model_info.get("input_cost_per_second")
            except Exception:
                pass

            return None
        except Exception as e:
            verbose_proxy_logger.exception(
                f"[Non blocking logging error] Error getting AssemblyAI model info: {str(e)}"
            )
            return None

    @staticmethod
    def _should_log_request(request_method: str) -> bool:
        """
        only POST transcription jobs are logged. litellm will POLL assembly to wait for the transcription to complete to log the complete response / cost
        """
        return request_method == "POST"

    @staticmethod
    def _get_assembly_region_from_url(url: Optional[str]) -> Optional[Literal["eu"]]:
        """
        Get the region from the URL
        """
        if url is None:
            return None
        if urlparse(url).hostname == "eu.assemblyai.com":
            return "eu"
        return None

    @staticmethod
    def _get_assembly_base_url_from_region(region: Optional[Literal["eu"]]) -> str:
        """
        Get the base URL for the AssemblyAI API
        if region == "eu", return "https://api.eu.assemblyai.com"
        else return "https://api.assemblyai.com"
        """
        if region == "eu":
            return "https://api.eu.assemblyai.com"
        return "https://api.assemblyai.com"

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\output\base.py ===
"""
Interface for an output.
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TextIO

from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.data_structures import Size
from prompt_toolkit.styles import Attrs

from .color_depth import ColorDepth

__all__ = [
    "Output",
    "DummyOutput",
]


class Output(metaclass=ABCMeta):
    """
    Base class defining the output interface for a
    :class:`~prompt_toolkit.renderer.Renderer`.

    Actual implementations are
    :class:`~prompt_toolkit.output.vt100.Vt100_Output` and
    :class:`~prompt_toolkit.output.win32.Win32Output`.
    """

    stdout: TextIO | None = None

    @abstractmethod
    def fileno(self) -> int:
        "Return the file descriptor to which we can write for the output."

    @abstractmethod
    def encoding(self) -> str:
        """
        Return the encoding for this output, e.g. 'utf-8'.
        (This is used mainly to know which characters are supported by the
        output the data, so that the UI can provide alternatives, when
        required.)
        """

    @abstractmethod
    def write(self, data: str) -> None:
        "Write text (Terminal escape sequences will be removed/escaped.)"

    @abstractmethod
    def write_raw(self, data: str) -> None:
        "Write text."

    @abstractmethod
    def set_title(self, title: str) -> None:
        "Set terminal title."

    @abstractmethod
    def clear_title(self) -> None:
        "Clear title again. (or restore previous title.)"

    @abstractmethod
    def flush(self) -> None:
        "Write to output stream and flush."

    @abstractmethod
    def erase_screen(self) -> None:
        """
        Erases the screen with the background color and moves the cursor to
        home.
        """

    @abstractmethod
    def enter_alternate_screen(self) -> None:
        "Go to the alternate screen buffer. (For full screen applications)."

    @abstractmethod
    def quit_alternate_screen(self) -> None:
        "Leave the alternate screen buffer."

    @abstractmethod
    def enable_mouse_support(self) -> None:
        "Enable mouse."

    @abstractmethod
    def disable_mouse_support(self) -> None:
        "Disable mouse."

    @abstractmethod
    def erase_end_of_line(self) -> None:
        """
        Erases from the current cursor position to the end of the current line.
        """

    @abstractmethod
    def erase_down(self) -> None:
        """
        Erases the screen from the current line down to the bottom of the
        screen.
        """

    @abstractmethod
    def reset_attributes(self) -> None:
        "Reset color and styling attributes."

    @abstractmethod
    def set_attributes(self, attrs: Attrs, color_depth: ColorDepth) -> None:
        "Set new color and styling attributes."

    @abstractmethod
    def disable_autowrap(self) -> None:
        "Disable auto line wrapping."

    @abstractmethod
    def enable_autowrap(self) -> None:
        "Enable auto line wrapping."

    @abstractmethod
    def cursor_goto(self, row: int = 0, column: int = 0) -> None:
        "Move cursor position."

    @abstractmethod
    def cursor_up(self, amount: int) -> None:
        "Move cursor `amount` place up."

    @abstractmethod
    def cursor_down(self, amount: int) -> None:
        "Move cursor `amount` place down."

    @abstractmethod
    def cursor_forward(self, amount: int) -> None:
        "Move cursor `amount` place forward."

    @abstractmethod
    def cursor_backward(self, amount: int) -> None:
        "Move cursor `amount` place backward."

    @abstractmethod
    def hide_cursor(self) -> None:
        "Hide cursor."

    @abstractmethod
    def show_cursor(self) -> None:
        "Show cursor."

    @abstractmethod
    def set_cursor_shape(self, cursor_shape: CursorShape) -> None:
        "Set cursor shape to block, beam or underline."

    @abstractmethod
    def reset_cursor_shape(self) -> None:
        "Reset cursor shape."

    def ask_for_cpr(self) -> None:
        """
        Asks for a cursor position report (CPR).
        (VT100 only.)
        """

    @property
    def responds_to_cpr(self) -> bool:
        """
        `True` if the `Application` can expect to receive a CPR response after
        calling `ask_for_cpr` (this will come back through the corresponding
        `Input`).

        This is used to determine the amount of available rows we have below
        the cursor position. In the first place, we have this so that the drop
        down autocompletion menus are sized according to the available space.

        On Windows, we don't need this, there we have
        `get_rows_below_cursor_position`.
        """
        return False

    @abstractmethod
    def get_size(self) -> Size:
        "Return the size of the output window."

    def bell(self) -> None:
        "Sound bell."

    def enable_bracketed_paste(self) -> None:
        "For vt100 only."

    def disable_bracketed_paste(self) -> None:
        "For vt100 only."

    def reset_cursor_key_mode(self) -> None:
        """
        For vt100 only.
        Put the terminal in normal cursor mode (instead of application mode).

        See: https://vt100.net/docs/vt100-ug/chapter3.html
        """

    def scroll_buffer_to_prompt(self) -> None:
        "For Win32 only."

    def get_rows_below_cursor_position(self) -> int:
        "For Windows only."
        raise NotImplementedError

    @abstractmethod
    def get_default_color_depth(self) -> ColorDepth:
        """
        Get default color depth for this output.

        This value will be used if no color depth was explicitly passed to the
        `Application`.

        .. note::

            If the `$PROMPT_TOOLKIT_COLOR_DEPTH` environment variable has been
            set, then `outputs.defaults.create_output` will pass this value to
            the implementation as the default_color_depth, which is returned
            here. (This is not used when the output corresponds to a
            prompt_toolkit SSH/Telnet session.)
        """


class DummyOutput(Output):
    """
    For testing. An output class that doesn't render anything.
    """

    def fileno(self) -> int:
        "There is no sensible default for fileno()."
        raise NotImplementedError

    def encoding(self) -> str:
        return "utf-8"

    def write(self, data: str) -> None:
        pass

    def write_raw(self, data: str) -> None:
        pass

    def set_title(self, title: str) -> None:
        pass

    def clear_title(self) -> None:
        pass

    def flush(self) -> None:
        pass

    def erase_screen(self) -> None:
        pass

    def enter_alternate_screen(self) -> None:
        pass

    def quit_alternate_screen(self) -> None:
        pass

    def enable_mouse_support(self) -> None:
        pass

    def disable_mouse_support(self) -> None:
        pass

    def erase_end_of_line(self) -> None:
        pass

    def erase_down(self) -> None:
        pass

    def reset_attributes(self) -> None:
        pass

    def set_attributes(self, attrs: Attrs, color_depth: ColorDepth) -> None:
        pass

    def disable_autowrap(self) -> None:
        pass

    def enable_autowrap(self) -> None:
        pass

    def cursor_goto(self, row: int = 0, column: int = 0) -> None:
        pass

    def cursor_up(self, amount: int) -> None:
        pass

    def cursor_down(self, amount: int) -> None:
        pass

    def cursor_forward(self, amount: int) -> None:
        pass

    def cursor_backward(self, amount: int) -> None:
        pass

    def hide_cursor(self) -> None:
        pass

    def show_cursor(self) -> None:
        pass

    def set_cursor_shape(self, cursor_shape: CursorShape) -> None:
        pass

    def reset_cursor_shape(self) -> None:
        pass

    def ask_for_cpr(self) -> None:
        pass

    def bell(self) -> None:
        pass

    def enable_bracketed_paste(self) -> None:
        pass

    def disable_bracketed_paste(self) -> None:
        pass

    def scroll_buffer_to_prompt(self) -> None:
        pass

    def get_size(self) -> Size:
        return Size(rows=40, columns=80)

    def get_rows_below_cursor_position(self) -> int:
        return 40

    def get_default_color_depth(self) -> ColorDepth:
        return ColorDepth.DEPTH_1_BIT

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\kuin.py ===
"""
    pygments.lexers.kuin
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for the Kuin language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, using, this, bygroups, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
        Number, Punctuation, Whitespace

__all__ = ['KuinLexer']


class KuinLexer(RegexLexer):
    """
    For Kuin source code.
    """
    name = 'Kuin'
    url = 'https://github.com/kuina/Kuin'
    aliases = ['kuin']
    filenames = ['*.kn']
    version_added = '2.9'

    tokens = {
        'root': [
            include('statement'),
        ],
        'statement': [
            # Whitespace / Comment
            include('whitespace'),

            # Block-statement
            (r'(\+?)([ \t]*)(\*?)([ \t]*)(\bfunc)([ \t]+(?:\n\s*\|)*[ \t]*)([a-zA-Z_][0-9a-zA-Z_]*)',
             bygroups(Keyword,Whitespace, Keyword, Whitespace,  Keyword,
                      using(this), Name.Function), 'func_'),
            (r'\b(class)([ \t]+(?:\n\s*\|)*[ \t]*)([a-zA-Z_][0-9a-zA-Z_]*)',
             bygroups(Keyword, using(this), Name.Class), 'class_'),
            (r'\b(enum)([ \t]+(?:\n\s*\|)*[ \t]*)([a-zA-Z_][0-9a-zA-Z_]*)',
             bygroups(Keyword, using(this), Name.Constant), 'enum_'),
            (r'\b(block)\b(?:([ \t]+(?:\n\s*\|)*[ \t]*)([a-zA-Z_][0-9a-zA-Z_]*))?',
             bygroups(Keyword, using(this), Name.Other), 'block_'),
            (r'\b(ifdef)\b(?:([ \t]+(?:\n\s*\|)*[ \t]*)([a-zA-Z_][0-9a-zA-Z_]*))?',
             bygroups(Keyword, using(this), Name.Other), 'ifdef_'),
            (r'\b(if)\b(?:([ \t]+(?:\n\s*\|)*[ \t]*)([a-zA-Z_][0-9a-zA-Z_]*))?',
             bygroups(Keyword, using(this), Name.Other), 'if_'),
            (r'\b(switch)\b(?:([ \t]+(?:\n\s*\|)*[ \t]*)([a-zA-Z_][0-9a-zA-Z_]*))?',
             bygroups(Keyword, using(this), Name.Other), 'switch_'),
            (r'\b(while)\b(?:([ \t]+(?:\n\s*\|)*[ \t]*)([a-zA-Z_][0-9a-zA-Z_]*))?',
             bygroups(Keyword, using(this), Name.Other), 'while_'),
            (r'\b(for)\b(?:([ \t]+(?:\n\s*\|)*[ \t]*)([a-zA-Z_][0-9a-zA-Z_]*))?',
             bygroups(Keyword, using(this), Name.Other), 'for_'),
            (r'\b(foreach)\b(?:([ \t]+(?:\n\s*\|)*[ \t]*)([a-zA-Z_][0-9a-zA-Z_]*))?',
             bygroups(Keyword, using(this), Name.Other), 'foreach_'),
            (r'\b(try)\b(?:([ \t]+(?:\n\s*\|)*[ \t]*)([a-zA-Z_][0-9a-zA-Z_]*))?',
             bygroups(Keyword, using(this), Name.Other), 'try_'),

            # Line-statement
            (r'\b(do)\b', Keyword, 'do'),
            (r'(\+?[ \t]*\bvar)\b', Keyword, 'var'),
            (r'\b(const)\b', Keyword, 'const'),
            (r'\b(ret)\b', Keyword, 'ret'),
            (r'\b(throw)\b', Keyword, 'throw'),
            (r'\b(alias)\b', Keyword, 'alias'),
            (r'\b(assert)\b', Keyword, 'assert'),
            (r'\|', Text, 'continued_line'),
            (r'[ \t]*\n', Whitespace),
        ],

        # Whitespace / Comment
        'whitespace': [
            (r'^([ \t]*)(;.*)', bygroups(Comment.Single, Whitespace)),
            (r'[ \t]+(?![; \t])', Whitespace),
            (r'\{', Comment.Multiline, 'multiline_comment'),
        ],
        'multiline_comment': [
            (r'\{', Comment.Multiline, 'multiline_comment'),
            (r'(?:\s*;.*|[^{}\n]+)', Comment.Multiline),
            (r'\n', Comment.Multiline),
            (r'\}', Comment.Multiline, '#pop'),
        ],

        # Block-statement
        'func_': [
            include('expr'),
            (r'\n', Whitespace, 'func'),
        ],
        'func': [
            (r'\b(end)([ \t]+(?:\n\s*\|)*[ \t]*)(func)\b',
             bygroups(Keyword, using(this), Keyword), '#pop:2'),
            include('statement'),
        ],
        'class_': [
            include('expr'),
            (r'\n', Whitespace, 'class'),
        ],
        'class': [
            (r'\b(end)([ \t]+(?:\n\s*\|)*[ \t]*)(class)\b',
             bygroups(Keyword, using(this), Keyword), '#pop:2'),
            include('statement'),
        ],
        'enum_': [
            include('expr'),
            (r'\n', Whitespace, 'enum'),
        ],
        'enum': [
            (r'\b(end)([ \t]+(?:\n\s*\|)*[ \t]*)(enum)\b',
             bygroups(Keyword, using(this), Keyword), '#pop:2'),
            include('expr'),
            (r'\n', Whitespace),
        ],
        'block_': [
            include('expr'),
            (r'\n', Whitespace, 'block'),
        ],
        'block': [
            (r'\b(end)([ \t]+(?:\n\s*\|)*[ \t]*)(block)\b',
             bygroups(Keyword, using(this), Keyword), '#pop:2'),
            include('statement'),
            include('break'),
            include('skip'),
        ],
        'ifdef_': [
            include('expr'),
            (r'\n', Whitespace, 'ifdef'),
        ],
        'ifdef': [
            (r'\b(end)([ \t]+(?:\n\s*\|)*[ \t]*)(ifdef)\b',
             bygroups(Keyword, using(this), Keyword), '#pop:2'),
            (words(('rls', 'dbg'), prefix=r'\b', suffix=r'\b'),
             Keyword.Constant, 'ifdef_sp'),
            include('statement'),
            include('break'),
            include('skip'),
        ],
        'ifdef_sp': [
            include('expr'),
            (r'\n', Whitespace, '#pop'),
        ],
        'if_': [
            include('expr'),
            (r'\n', Whitespace, 'if'),
        ],
        'if': [
            (r'\b(end)([ \t]+(?:\n\s*\|)*[ \t]*)(if)\b',
             bygroups(Keyword, using(this), Keyword), '#pop:2'),
            (words(('elif', 'else'), prefix=r'\b', suffix=r'\b'), Keyword, 'if_sp'),
            include('statement'),
            include('break'),
            include('skip'),
        ],
        'if_sp': [
            include('expr'),
            (r'\n', Whitespace, '#pop'),
        ],
        'switch_': [
            include('expr'),
            (r'\n', Whitespace, 'switch'),
        ],
        'switch': [
            (r'\b(end)([ \t]+(?:\n\s*\|)*[ \t]*)(switch)\b',
             bygroups(Keyword, using(this), Keyword), '#pop:2'),
            (words(('case', 'default', 'to'), prefix=r'\b', suffix=r'\b'),
             Keyword, 'switch_sp'),
            include('statement'),
            include('break'),
            include('skip'),
        ],
        'switch_sp': [
            include('expr'),
            (r'\n', Whitespace, '#pop'),
        ],
        'while_': [
            include('expr'),
            (r'\n', Whitespace, 'while'),
        ],
        'while': [
            (r'\b(end)([ \t]+(?:\n\s*\|)*[ \t]*)(while)\b',
             bygroups(Keyword, using(this), Keyword), '#pop:2'),
            include('statement'),
            include('break'),
            include('skip'),
        ],
        'for_': [
            include('expr'),
            (r'\n', Whitespace, 'for'),
        ],
        'for': [
            (r'\b(end)([ \t]+(?:\n\s*\|)*[ \t]*)(for)\b',
             bygroups(Keyword, using(this), Keyword), '#pop:2'),
            include('statement'),
            include('break'),
            include('skip'),
        ],
        'foreach_': [
            include('expr'),
            (r'\n', Whitespace, 'foreach'),
        ],
        'foreach': [
            (r'\b(end)([ \t]+(?:\n\s*\|)*[ \t]*)(foreach)\b',
             bygroups(Keyword, using(this), Keyword), '#pop:2'),
            include('statement'),
            include('break'),
            include('skip'),
        ],
        'try_': [
            include('expr'),
            (r'\n', Whitespace, 'try'),
        ],
        'try': [
            (r'\b(end)([ \t]+(?:\n\s*\|)*[ \t]*)(try)\b',
             bygroups(Keyword, using(this), Keyword), '#pop:2'),
            (words(('catch', 'finally', 'to'), prefix=r'\b', suffix=r'\b'),
             Keyword, 'try_sp'),
            include('statement'),
            include('break'),
            include('skip'),
        ],
        'try_sp': [
            include('expr'),
            (r'\n', Whitespace, '#pop'),
        ],

        # Line-statement
        'break': [
            (r'\b(break)\b([ \t]+)([a-zA-Z_][0-9a-zA-Z_]*)',
             bygroups(Keyword, using(this), Name.Other)),
        ],
        'skip': [
            (r'\b(skip)\b([ \t]+)([a-zA-Z_][0-9a-zA-Z_]*)',
             bygroups(Keyword, using(this), Name.Other)),
        ],
        'alias': [
            include('expr'),
            (r'\n', Whitespace, '#pop'),
        ],
        'assert': [
            include('expr'),
            (r'\n', Whitespace, '#pop'),
        ],
        'const': [
            include('expr'),
            (r'\n', Whitespace, '#pop'),
        ],
        'do': [
            include('expr'),
            (r'\n', Whitespace, '#pop'),
        ],
        'ret': [
            include('expr'),
            (r'\n', Whitespace, '#pop'),
        ],
        'throw': [
            include('expr'),
            (r'\n', Whitespace, '#pop'),
        ],
        'var': [
            include('expr'),
            (r'\n', Whitespace, '#pop'),
        ],
        'continued_line': [
            include('expr'),
            (r'\n', Whitespace, '#pop'),
        ],

        'expr': [
            # Whitespace / Comment
            include('whitespace'),

            # Punctuation
            (r'\(', Punctuation,),
            (r'\)', Punctuation,),
            (r'\[', Punctuation,),
            (r'\]', Punctuation,),
            (r',', Punctuation),

            # Keyword
            (words((
                'true', 'false', 'null', 'inf'
                ), prefix=r'\b', suffix=r'\b'), Keyword.Constant),
            (words((
                'me'
                ), prefix=r'\b', suffix=r'\b'), Keyword),
            (words((
                'bit16', 'bit32', 'bit64', 'bit8', 'bool',
                'char', 'class', 'dict', 'enum', 'float', 'func',
                'int', 'list', 'queue', 'stack'
                ), prefix=r'\b', suffix=r'\b'), Keyword.Type),

            # Number
            (r'\b[0-9]\.[0-9]+(?!\.)(:?e[\+-][0-9]+)?\b', Number.Float),
            (r'\b2#[01]+(?:b(?:8|16|32|64))?\b', Number.Bin),
            (r'\b8#[0-7]+(?:b(?:8|16|32|64))?\b', Number.Oct),
            (r'\b16#[0-9A-F]+(?:b(?:8|16|32|64))?\b', Number.Hex),
            (r'\b[0-9]+(?:b(?:8|16|32|64))?\b', Number.Decimal),

            # String / Char
            (r'"', String.Double, 'string'),
            (r"'(?:\\.|.)+?'", String.Char),

            # Operator
            (r'(?:\.|\$(?:>|<)?)', Operator),
            (r'(?:\^)', Operator),
            (r'(?:\+|-|!|##?)', Operator),
            (r'(?:\*|/|%)', Operator),
            (r'(?:~)', Operator),
            (r'(?:(?:=|<>)(?:&|\$)?|<=?|>=?)', Operator),
            (r'(?:&)', Operator),
            (r'(?:\|)', Operator),
            (r'(?:\?)', Operator),
            (r'(?::(?::|\+|-|\*|/|%|\^|~)?)', Operator),

            # Identifier
            (r"\b([a-zA-Z_][0-9a-zA-Z_]*)(?=@)\b", Name),
            (r"(@)?\b([a-zA-Z_][0-9a-zA-Z_]*)\b",
             bygroups(Name.Other, Name.Variable)),
        ],

        # String
        'string': [
            (r'(?:\\[^{\n]|[^"\\])+', String.Double),
            (r'\\\{', String.Double, 'toStrInString'),
            (r'"', String.Double, '#pop'),
        ],
        'toStrInString': [
            include('expr'),
            (r'\}', String.Double, '#pop'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\support\color.py ===
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
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Sequence

if sys.version_info >= (3, 9):
    from re import Match
else:
    from typing import Match

if TYPE_CHECKING:
    from typing import SupportsFloat, SupportsIndex, SupportsInt, Union

    ParseableFloat = Union[SupportsFloat, SupportsIndex, str, bytes, bytearray]
    ParseableInt = Union[SupportsInt, SupportsIndex, str, bytes]
else:
    ParseableFloat = Any
    ParseableInt = Any

RGB_PATTERN = r"^\s*rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)\s*$"
RGB_PCT_PATTERN = (
    r"^\s*rgb\(\s*(\d{1,3}|\d{1,2}\.\d+)%\s*,\s*(\d{1,3}|\d{1,2}\.\d+)%\s*,\s*(\d{1,3}|\d{1,2}\.\d+)%\s*\)\s*$"
)
RGBA_PATTERN = r"^\s*rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(0|1|0\.\d+)\s*\)\s*$"
RGBA_PCT_PATTERN = (
    r"^\s*rgba\(\s*(\d{1,3}|\d{1,2}\.\d+)%\s*,\s*(\d{1,3}|\d{1,2}\.\d+)%\s*,"
    + r"\s*(\d{1,3}|\d{1,2}\.\d+)%\s*,\s*(0|1|0\.\d+)\s*\)\s*$"
)
HEX_PATTERN = r"#([A-Fa-f0-9]{2})([A-Fa-f0-9]{2})([A-Fa-f0-9]{2})"
HEX3_PATTERN = r"#([A-Fa-f0-9])([A-Fa-f0-9])([A-Fa-f0-9])"
HSL_PATTERN = r"^\s*hsl\(\s*(\d{1,3})\s*,\s*(\d{1,3})%\s*,\s*(\d{1,3})%\s*\)\s*$"
HSLA_PATTERN = r"^\s*hsla\(\s*(\d{1,3})\s*,\s*(\d{1,3})%\s*,\s*(\d{1,3})%\s*,\s*(0|1|0\.\d+)\s*\)\s*$"


class Color:
    """Color conversion support class.

    Example:

    ::

        from selenium.webdriver.support.color import Color

        print(Color.from_string("#00ff33").rgba)
        print(Color.from_string("rgb(1, 255, 3)").hex)
        print(Color.from_string("blue").rgba)
    """

    @classmethod
    def from_string(cls, str_: str) -> Color:
        import re

        class Matcher:
            match_obj: Match[str] | None

            def __init__(self) -> None:
                self.match_obj = None

            def match(self, pattern: str, str_: str) -> Match[str] | None:
                self.match_obj = re.match(pattern, str_)
                return self.match_obj

            @property
            def groups(self) -> Sequence[str]:
                return () if not self.match_obj else self.match_obj.groups()

        m = Matcher()

        if m.match(RGB_PATTERN, str_):
            return cls(*m.groups)
        if m.match(RGB_PCT_PATTERN, str_):
            rgb = tuple(float(each) / 100 * 255 for each in m.groups)
            return cls(*rgb)
        if m.match(RGBA_PATTERN, str_):
            return cls(*m.groups)
        if m.match(RGBA_PCT_PATTERN, str_):
            rgba = tuple([float(each) / 100 * 255 for each in m.groups[:3]] + [m.groups[3]])
            return cls(*rgba)
        if m.match(HEX_PATTERN, str_):
            rgb = tuple(int(each, 16) for each in m.groups)
            return cls(*rgb)
        if m.match(HEX3_PATTERN, str_):
            rgb = tuple(int(each * 2, 16) for each in m.groups)
            return cls(*rgb)
        if m.match(HSL_PATTERN, str_) or m.match(HSLA_PATTERN, str_):
            return cls._from_hsl(*m.groups)
        if str_.upper() in Colors:
            return Colors[str_.upper()]
        raise ValueError("Could not convert %s into color" % str_)

    @classmethod
    def _from_hsl(cls, h: ParseableFloat, s: ParseableFloat, light: ParseableFloat, a: ParseableFloat = 1) -> Color:
        h = float(h) / 360
        s = float(s) / 100
        _l = float(light) / 100

        if s == 0:
            r = _l
            g = r
            b = r
        else:
            luminocity2 = _l * (1 + s) if _l < 0.5 else _l + s - _l * s
            luminocity1 = 2 * _l - luminocity2

            def hue_to_rgb(lum1: float, lum2: float, hue: float) -> float:
                if hue < 0.0:
                    hue += 1
                if hue > 1.0:
                    hue -= 1

                if hue < 1.0 / 6.0:
                    return lum1 + (lum2 - lum1) * 6.0 * hue
                if hue < 1.0 / 2.0:
                    return lum2
                if hue < 2.0 / 3.0:
                    return lum1 + (lum2 - lum1) * ((2.0 / 3.0) - hue) * 6.0
                return lum1

            r = hue_to_rgb(luminocity1, luminocity2, h + 1.0 / 3.0)
            g = hue_to_rgb(luminocity1, luminocity2, h)
            b = hue_to_rgb(luminocity1, luminocity2, h - 1.0 / 3.0)

        return cls(round(r * 255), round(g * 255), round(b * 255), a)

    def __init__(self, red: ParseableInt, green: ParseableInt, blue: ParseableInt, alpha: ParseableFloat = 1) -> None:
        self.red = int(red)
        self.green = int(green)
        self.blue = int(blue)
        self.alpha = "1" if float(alpha) == 1 else str(float(alpha) or 0)

    @property
    def rgb(self) -> str:
        return f"rgb({self.red}, {self.green}, {self.blue})"

    @property
    def rgba(self) -> str:
        return f"rgba({self.red}, {self.green}, {self.blue}, {self.alpha})"

    @property
    def hex(self) -> str:
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Color):
            return self.rgba == other.rgba
        return NotImplemented

    def __ne__(self, other: Any) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self) -> int:
        return hash((self.red, self.green, self.blue, self.alpha))

    def __repr__(self) -> str:
        return f"Color(red={self.red}, green={self.green}, blue={self.blue}, alpha={self.alpha})"

    def __str__(self) -> str:
        return f"Color: {self.rgba}"


# Basic, extended and transparent colour keywords as defined by the W3C HTML4 spec
# See http://www.w3.org/TR/css3-color/#html4
Colors = {
    "TRANSPARENT": Color(0, 0, 0, 0),
    "ALICEBLUE": Color(240, 248, 255),
    "ANTIQUEWHITE": Color(250, 235, 215),
    "AQUA": Color(0, 255, 255),
    "AQUAMARINE": Color(127, 255, 212),
    "AZURE": Color(240, 255, 255),
    "BEIGE": Color(245, 245, 220),
    "BISQUE": Color(255, 228, 196),
    "BLACK": Color(0, 0, 0),
    "BLANCHEDALMOND": Color(255, 235, 205),
    "BLUE": Color(0, 0, 255),
    "BLUEVIOLET": Color(138, 43, 226),
    "BROWN": Color(165, 42, 42),
    "BURLYWOOD": Color(222, 184, 135),
    "CADETBLUE": Color(95, 158, 160),
    "CHARTREUSE": Color(127, 255, 0),
    "CHOCOLATE": Color(210, 105, 30),
    "CORAL": Color(255, 127, 80),
    "CORNFLOWERBLUE": Color(100, 149, 237),
    "CORNSILK": Color(255, 248, 220),
    "CRIMSON": Color(220, 20, 60),
    "CYAN": Color(0, 255, 255),
    "DARKBLUE": Color(0, 0, 139),
    "DARKCYAN": Color(0, 139, 139),
    "DARKGOLDENROD": Color(184, 134, 11),
    "DARKGRAY": Color(169, 169, 169),
    "DARKGREEN": Color(0, 100, 0),
    "DARKGREY": Color(169, 169, 169),
    "DARKKHAKI": Color(189, 183, 107),
    "DARKMAGENTA": Color(139, 0, 139),
    "DARKOLIVEGREEN": Color(85, 107, 47),
    "DARKORANGE": Color(255, 140, 0),
    "DARKORCHID": Color(153, 50, 204),
    "DARKRED": Color(139, 0, 0),
    "DARKSALMON": Color(233, 150, 122),
    "DARKSEAGREEN": Color(143, 188, 143),
    "DARKSLATEBLUE": Color(72, 61, 139),
    "DARKSLATEGRAY": Color(47, 79, 79),
    "DARKSLATEGREY": Color(47, 79, 79),
    "DARKTURQUOISE": Color(0, 206, 209),
    "DARKVIOLET": Color(148, 0, 211),
    "DEEPPINK": Color(255, 20, 147),
    "DEEPSKYBLUE": Color(0, 191, 255),
    "DIMGRAY": Color(105, 105, 105),
    "DIMGREY": Color(105, 105, 105),
    "DODGERBLUE": Color(30, 144, 255),
    "FIREBRICK": Color(178, 34, 34),
    "FLORALWHITE": Color(255, 250, 240),
    "FORESTGREEN": Color(34, 139, 34),
    "FUCHSIA": Color(255, 0, 255),
    "GAINSBORO": Color(220, 220, 220),
    "GHOSTWHITE": Color(248, 248, 255),
    "GOLD": Color(255, 215, 0),
    "GOLDENROD": Color(218, 165, 32),
    "GRAY": Color(128, 128, 128),
    "GREY": Color(128, 128, 128),
    "GREEN": Color(0, 128, 0),
    "GREENYELLOW": Color(173, 255, 47),
    "HONEYDEW": Color(240, 255, 240),
    "HOTPINK": Color(255, 105, 180),
    "INDIANRED": Color(205, 92, 92),
    "INDIGO": Color(75, 0, 130),
    "IVORY": Color(255, 255, 240),
    "KHAKI": Color(240, 230, 140),
    "LAVENDER": Color(230, 230, 250),
    "LAVENDERBLUSH": Color(255, 240, 245),
    "LAWNGREEN": Color(124, 252, 0),
    "LEMONCHIFFON": Color(255, 250, 205),
    "LIGHTBLUE": Color(173, 216, 230),
    "LIGHTCORAL": Color(240, 128, 128),
    "LIGHTCYAN": Color(224, 255, 255),
    "LIGHTGOLDENRODYELLOW": Color(250, 250, 210),
    "LIGHTGRAY": Color(211, 211, 211),
    "LIGHTGREEN": Color(144, 238, 144),
    "LIGHTGREY": Color(211, 211, 211),
    "LIGHTPINK": Color(255, 182, 193),
    "LIGHTSALMON": Color(255, 160, 122),
    "LIGHTSEAGREEN": Color(32, 178, 170),
    "LIGHTSKYBLUE": Color(135, 206, 250),
    "LIGHTSLATEGRAY": Color(119, 136, 153),
    "LIGHTSLATEGREY": Color(119, 136, 153),
    "LIGHTSTEELBLUE": Color(176, 196, 222),
    "LIGHTYELLOW": Color(255, 255, 224),
    "LIME": Color(0, 255, 0),
    "LIMEGREEN": Color(50, 205, 50),
    "LINEN": Color(250, 240, 230),
    "MAGENTA": Color(255, 0, 255),
    "MAROON": Color(128, 0, 0),
    "MEDIUMAQUAMARINE": Color(102, 205, 170),
    "MEDIUMBLUE": Color(0, 0, 205),
    "MEDIUMORCHID": Color(186, 85, 211),
    "MEDIUMPURPLE": Color(147, 112, 219),
    "MEDIUMSEAGREEN": Color(60, 179, 113),
    "MEDIUMSLATEBLUE": Color(123, 104, 238),
    "MEDIUMSPRINGGREEN": Color(0, 250, 154),
    "MEDIUMTURQUOISE": Color(72, 209, 204),
    "MEDIUMVIOLETRED": Color(199, 21, 133),
    "MIDNIGHTBLUE": Color(25, 25, 112),
    "MINTCREAM": Color(245, 255, 250),
    "MISTYROSE": Color(255, 228, 225),
    "MOCCASIN": Color(255, 228, 181),
    "NAVAJOWHITE": Color(255, 222, 173),
    "NAVY": Color(0, 0, 128),
    "OLDLACE": Color(253, 245, 230),
    "OLIVE": Color(128, 128, 0),
    "OLIVEDRAB": Color(107, 142, 35),
    "ORANGE": Color(255, 165, 0),
    "ORANGERED": Color(255, 69, 0),
    "ORCHID": Color(218, 112, 214),
    "PALEGOLDENROD": Color(238, 232, 170),
    "PALEGREEN": Color(152, 251, 152),
    "PALETURQUOISE": Color(175, 238, 238),
    "PALEVIOLETRED": Color(219, 112, 147),
    "PAPAYAWHIP": Color(255, 239, 213),
    "PEACHPUFF": Color(255, 218, 185),
    "PERU": Color(205, 133, 63),
    "PINK": Color(255, 192, 203),
    "PLUM": Color(221, 160, 221),
    "POWDERBLUE": Color(176, 224, 230),
    "PURPLE": Color(128, 0, 128),
    "REBECCAPURPLE": Color(128, 51, 153),
    "RED": Color(255, 0, 0),
    "ROSYBROWN": Color(188, 143, 143),
    "ROYALBLUE": Color(65, 105, 225),
    "SADDLEBROWN": Color(139, 69, 19),
    "SALMON": Color(250, 128, 114),
    "SANDYBROWN": Color(244, 164, 96),
    "SEAGREEN": Color(46, 139, 87),
    "SEASHELL": Color(255, 245, 238),
    "SIENNA": Color(160, 82, 45),
    "SILVER": Color(192, 192, 192),
    "SKYBLUE": Color(135, 206, 235),
    "SLATEBLUE": Color(106, 90, 205),
    "SLATEGRAY": Color(112, 128, 144),
    "SLATEGREY": Color(112, 128, 144),
    "SNOW": Color(255, 250, 250),
    "SPRINGGREEN": Color(0, 255, 127),
    "STEELBLUE": Color(70, 130, 180),
    "TAN": Color(210, 180, 140),
    "TEAL": Color(0, 128, 128),
    "THISTLE": Color(216, 191, 216),
    "TOMATO": Color(255, 99, 71),
    "TURQUOISE": Color(64, 224, 208),
    "VIOLET": Color(238, 130, 238),
    "WHEAT": Color(245, 222, 179),
    "WHITE": Color(255, 255, 255),
    "WHITESMOKE": Color(245, 245, 245),
    "YELLOW": Color(255, 255, 0),
    "YELLOWGREEN": Color(154, 205, 50),
}

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\cli\convert.py ===
from __future__ import annotations

import os.path
import re
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from collections.abc import Iterator
from email.message import Message
from email.parser import Parser
from email.policy import EmailPolicy
from glob import iglob
from pathlib import Path
from textwrap import dedent
from zipfile import ZipFile

from .. import __version__
from ..metadata import generate_requirements
from ..vendored.packaging.tags import parse_tag
from ..wheelfile import WheelFile

egg_filename_re = re.compile(
    r"""
    (?P<name>.+?)-(?P<ver>.+?)
    (-(?P<pyver>py\d\.\d+)
     (-(?P<arch>.+?))?
    )?.egg$""",
    re.VERBOSE,
)
egg_info_re = re.compile(
    r"""
    ^(?P<name>.+?)-(?P<ver>.+?)
    (-(?P<pyver>py\d\.\d+)
    )?.egg-info/""",
    re.VERBOSE,
)
wininst_re = re.compile(
    r"\.(?P<platform>win32|win-amd64)(?:-(?P<pyver>py\d\.\d))?\.exe$"
)
pyd_re = re.compile(r"\.(?P<abi>[a-z0-9]+)-(?P<platform>win32|win_amd64)\.pyd$")
serialization_policy = EmailPolicy(
    utf8=True,
    mangle_from_=False,
    max_line_length=0,
)
GENERATOR = f"wheel {__version__}"


def convert_requires(requires: str, metadata: Message) -> None:
    extra: str | None = None
    requirements: dict[str | None, list[str]] = defaultdict(list)
    for line in requires.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("[") and line.endswith("]"):
            extra = line[1:-1]
            continue

        requirements[extra].append(line)

    for key, value in generate_requirements(requirements):
        metadata.add_header(key, value)


def convert_pkg_info(pkginfo: str, metadata: Message):
    parsed_message = Parser().parsestr(pkginfo)
    for key, value in parsed_message.items():
        key_lower = key.lower()
        if value == "UNKNOWN":
            continue

        if key_lower == "description":
            description_lines = value.splitlines()
            value = "\n".join(
                (
                    description_lines[0].lstrip(),
                    dedent("\n".join(description_lines[1:])),
                    "\n",
                )
            )
            metadata.set_payload(value)
        elif key_lower == "home-page":
            metadata.add_header("Project-URL", f"Homepage, {value}")
        elif key_lower == "download-url":
            metadata.add_header("Project-URL", f"Download, {value}")
        else:
            metadata.add_header(key, value)

    metadata.replace_header("Metadata-Version", "2.4")


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower().replace("-", "_")


class ConvertSource(metaclass=ABCMeta):
    name: str
    version: str
    pyver: str = "py2.py3"
    abi: str = "none"
    platform: str = "any"
    metadata: Message

    @property
    def dist_info_dir(self) -> str:
        return f"{self.name}-{self.version}.dist-info"

    @abstractmethod
    def generate_contents(self) -> Iterator[tuple[str, bytes]]:
        pass


class EggFileSource(ConvertSource):
    def __init__(self, path: Path):
        if not (match := egg_filename_re.match(path.name)):
            raise ValueError(f"Invalid egg file name: {path.name}")

        # Binary wheels are assumed to be for CPython
        self.path = path
        self.name = normalize(match.group("name"))
        self.version = match.group("ver")
        if pyver := match.group("pyver"):
            self.pyver = pyver.replace(".", "")
            if arch := match.group("arch"):
                self.abi = self.pyver.replace("py", "cp")
                self.platform = normalize(arch)

        self.metadata = Message()

    def generate_contents(self) -> Iterator[tuple[str, bytes]]:
        with ZipFile(self.path, "r") as zip_file:
            for filename in sorted(zip_file.namelist()):
                # Skip pure directory entries
                if filename.endswith("/"):
                    continue

                # Handle files in the egg-info directory specially, selectively moving
                # them to the dist-info directory while converting as needed
                if filename.startswith("EGG-INFO/"):
                    if filename == "EGG-INFO/requires.txt":
                        requires = zip_file.read(filename).decode("utf-8")
                        convert_requires(requires, self.metadata)
                    elif filename == "EGG-INFO/PKG-INFO":
                        pkginfo = zip_file.read(filename).decode("utf-8")
                        convert_pkg_info(pkginfo, self.metadata)
                    elif filename == "EGG-INFO/entry_points.txt":
                        yield (
                            f"{self.dist_info_dir}/entry_points.txt",
                            zip_file.read(filename),
                        )

                    continue

                # For any other file, just pass it through
                yield filename, zip_file.read(filename)


class EggDirectorySource(EggFileSource):
    def generate_contents(self) -> Iterator[tuple[str, bytes]]:
        for dirpath, _, filenames in os.walk(self.path):
            for filename in sorted(filenames):
                path = Path(dirpath, filename)
                if path.parent.name == "EGG-INFO":
                    if path.name == "requires.txt":
                        requires = path.read_text("utf-8")
                        convert_requires(requires, self.metadata)
                    elif path.name == "PKG-INFO":
                        pkginfo = path.read_text("utf-8")
                        convert_pkg_info(pkginfo, self.metadata)
                        if name := self.metadata.get("Name"):
                            self.name = normalize(name)

                        if version := self.metadata.get("Version"):
                            self.version = version
                    elif path.name == "entry_points.txt":
                        yield (
                            f"{self.dist_info_dir}/entry_points.txt",
                            path.read_bytes(),
                        )

                    continue

                # For any other file, just pass it through
                yield str(path.relative_to(self.path)), path.read_bytes()


class WininstFileSource(ConvertSource):
    """
    Handles distributions created with ``bdist_wininst``.

    The egginfo filename has the format::

        name-ver(-pyver)(-arch).egg-info

    The installer filename has the format::

        name-ver.arch(-pyver).exe

    Some things to note:

    1. The installer filename is not definitive. An installer can be renamed
       and work perfectly well as an installer. So more reliable data should
       be used whenever possible.
    2. The egg-info data should be preferred for the name and version, because
       these come straight from the distutils metadata, and are mandatory.
    3. The pyver from the egg-info data should be ignored, as it is
       constructed from the version of Python used to build the installer,
       which is irrelevant - the installer filename is correct here (even to
       the point that when it's not there, any version is implied).
    4. The architecture must be taken from the installer filename, as it is
       not included in the egg-info data.
    5. Architecture-neutral installers still have an architecture because the
       installer format itself (being executable) is architecture-specific. We
       should therefore ignore the architecture if the content is pure-python.
    """

    def __init__(self, path: Path):
        self.path = path
        self.metadata = Message()

        # Determine the initial architecture and Python version from the file name
        # (if possible)
        if match := wininst_re.search(path.name):
            self.platform = normalize(match.group("platform"))
            if pyver := match.group("pyver"):
                self.pyver = pyver.replace(".", "")

        # Look for an .egg-info directory and any .pyd files for more precise info
        egg_info_found = pyd_found = False
        with ZipFile(self.path) as zip_file:
            for filename in zip_file.namelist():
                prefix, filename = filename.split("/", 1)
                if not egg_info_found and (match := egg_info_re.match(filename)):
                    egg_info_found = True
                    self.name = normalize(match.group("name"))
                    self.version = match.group("ver")
                    if pyver := match.group("pyver"):
                        self.pyver = pyver.replace(".", "")
                elif not pyd_found and (match := pyd_re.search(filename)):
                    pyd_found = True
                    self.abi = match.group("abi")
                    self.platform = match.group("platform")

                if egg_info_found and pyd_found:
                    break

    def generate_contents(self) -> Iterator[tuple[str, bytes]]:
        dist_info_dir = f"{self.name}-{self.version}.dist-info"
        data_dir = f"{self.name}-{self.version}.data"
        with ZipFile(self.path, "r") as zip_file:
            for filename in sorted(zip_file.namelist()):
                # Skip pure directory entries
                if filename.endswith("/"):
                    continue

                # Handle files in the egg-info directory specially, selectively moving
                # them to the dist-info directory while converting as needed
                prefix, target_filename = filename.split("/", 1)
                if egg_info_re.search(target_filename):
                    basename = target_filename.rsplit("/", 1)[-1]
                    if basename == "requires.txt":
                        requires = zip_file.read(filename).decode("utf-8")
                        convert_requires(requires, self.metadata)
                    elif basename == "PKG-INFO":
                        pkginfo = zip_file.read(filename).decode("utf-8")
                        convert_pkg_info(pkginfo, self.metadata)
                    elif basename == "entry_points.txt":
                        yield (
                            f"{dist_info_dir}/entry_points.txt",
                            zip_file.read(filename),
                        )

                    continue
                elif prefix == "SCRIPTS":
                    target_filename = f"{data_dir}/scripts/{target_filename}"

                # For any other file, just pass it through
                yield target_filename, zip_file.read(filename)


def convert(files: list[str], dest_dir: str, verbose: bool) -> None:
    for pat in files:
        for archive in iglob(pat):
            path = Path(archive)
            if path.suffix == ".egg":
                if path.is_dir():
                    source: ConvertSource = EggDirectorySource(path)
                else:
                    source = EggFileSource(path)
            else:
                source = WininstFileSource(path)

            if verbose:
                print(f"{archive}...", flush=True, end="")

            dest_path = Path(dest_dir) / (
                f"{source.name}-{source.version}-{source.pyver}-{source.abi}"
                f"-{source.platform}.whl"
            )
            with WheelFile(dest_path, "w") as wheelfile:
                for name_or_zinfo, contents in source.generate_contents():
                    wheelfile.writestr(name_or_zinfo, contents)

                # Write the METADATA file
                wheelfile.writestr(
                    f"{source.dist_info_dir}/METADATA",
                    source.metadata.as_string(policy=serialization_policy).encode(
                        "utf-8"
                    ),
                )

                # Write the WHEEL file
                wheel_message = Message()
                wheel_message.add_header("Wheel-Version", "1.0")
                wheel_message.add_header("Generator", GENERATOR)
                wheel_message.add_header(
                    "Root-Is-Purelib", str(source.platform == "any").lower()
                )
                tags = parse_tag(f"{source.pyver}-{source.abi}-{source.platform}")
                for tag in sorted(tags, key=lambda tag: tag.interpreter):
                    wheel_message.add_header("Tag", str(tag))

                wheelfile.writestr(
                    f"{source.dist_info_dir}/WHEEL",
                    wheel_message.as_string(policy=serialization_policy).encode(
                        "utf-8"
                    ),
                )

            if verbose:
                print("OK")

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\packaging\markers.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import annotations

import operator
import os
import platform
import sys
from typing import Any, Callable, TypedDict, cast

from ._parser import MarkerAtom, MarkerList, Op, Value, Variable
from ._parser import parse_marker as _parse_marker
from ._tokenizer import ParserSyntaxError
from .specifiers import InvalidSpecifier, Specifier
from .utils import canonicalize_name

__all__ = [
    "InvalidMarker",
    "Marker",
    "UndefinedComparison",
    "UndefinedEnvironmentName",
    "default_environment",
]

Operator = Callable[[str, str], bool]


class InvalidMarker(ValueError):
    """
    An invalid marker was found, users should refer to PEP 508.
    """


class UndefinedComparison(ValueError):
    """
    An invalid operation was attempted on a value that doesn't support it.
    """


class UndefinedEnvironmentName(ValueError):
    """
    A name was attempted to be used that does not exist inside of the
    environment.
    """


class Environment(TypedDict):
    implementation_name: str
    """The implementation's identifier, e.g. ``'cpython'``."""

    implementation_version: str
    """
    The implementation's version, e.g. ``'3.13.0a2'`` for CPython 3.13.0a2, or
    ``'7.3.13'`` for PyPy3.10 v7.3.13.
    """

    os_name: str
    """
    The value of :py:data:`os.name`. The name of the operating system dependent module
    imported, e.g. ``'posix'``.
    """

    platform_machine: str
    """
    Returns the machine type, e.g. ``'i386'``.

    An empty string if the value cannot be determined.
    """

    platform_release: str
    """
    The system's release, e.g. ``'2.2.0'`` or ``'NT'``.

    An empty string if the value cannot be determined.
    """

    platform_system: str
    """
    The system/OS name, e.g. ``'Linux'``, ``'Windows'`` or ``'Java'``.

    An empty string if the value cannot be determined.
    """

    platform_version: str
    """
    The system's release version, e.g. ``'#3 on degas'``.

    An empty string if the value cannot be determined.
    """

    python_full_version: str
    """
    The Python version as string ``'major.minor.patchlevel'``.

    Note that unlike the Python :py:data:`sys.version`, this value will always include
    the patchlevel (it defaults to 0).
    """

    platform_python_implementation: str
    """
    A string identifying the Python implementation, e.g. ``'CPython'``.
    """

    python_version: str
    """The Python version as string ``'major.minor'``."""

    sys_platform: str
    """
    This string contains a platform identifier that can be used to append
    platform-specific components to :py:data:`sys.path`, for instance.

    For Unix systems, except on Linux and AIX, this is the lowercased OS name as
    returned by ``uname -s`` with the first part of the version as returned by
    ``uname -r`` appended, e.g. ``'sunos5'`` or ``'freebsd8'``, at the time when Python
    was built.
    """


def _normalize_extra_values(results: Any) -> Any:
    """
    Normalize extra values.
    """
    if isinstance(results[0], tuple):
        lhs, op, rhs = results[0]
        if isinstance(lhs, Variable) and lhs.value == "extra":
            normalized_extra = canonicalize_name(rhs.value)
            rhs = Value(normalized_extra)
        elif isinstance(rhs, Variable) and rhs.value == "extra":
            normalized_extra = canonicalize_name(lhs.value)
            lhs = Value(normalized_extra)
        results[0] = lhs, op, rhs
    return results


def _format_marker(
    marker: list[str] | MarkerAtom | str, first: bool | None = True
) -> str:
    assert isinstance(marker, (list, tuple, str))

    # Sometimes we have a structure like [[...]] which is a single item list
    # where the single item is itself it's own list. In that case we want skip
    # the rest of this function so that we don't get extraneous () on the
    # outside.
    if (
        isinstance(marker, list)
        and len(marker) == 1
        and isinstance(marker[0], (list, tuple))
    ):
        return _format_marker(marker[0])

    if isinstance(marker, list):
        inner = (_format_marker(m, first=False) for m in marker)
        if first:
            return " ".join(inner)
        else:
            return "(" + " ".join(inner) + ")"
    elif isinstance(marker, tuple):
        return " ".join([m.serialize() for m in marker])
    else:
        return marker


_operators: dict[str, Operator] = {
    "in": lambda lhs, rhs: lhs in rhs,
    "not in": lambda lhs, rhs: lhs not in rhs,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    ">": operator.gt,
}


def _eval_op(lhs: str, op: Op, rhs: str) -> bool:
    try:
        spec = Specifier("".join([op.serialize(), rhs]))
    except InvalidSpecifier:
        pass
    else:
        return spec.contains(lhs, prereleases=True)

    oper: Operator | None = _operators.get(op.serialize())
    if oper is None:
        raise UndefinedComparison(f"Undefined {op!r} on {lhs!r} and {rhs!r}.")

    return oper(lhs, rhs)


def _normalize(*values: str, key: str) -> tuple[str, ...]:
    # PEP 685 – Comparison of extra names for optional distribution dependencies
    # https://peps.python.org/pep-0685/
    # > When comparing extra names, tools MUST normalize the names being
    # > compared using the semantics outlined in PEP 503 for names
    if key == "extra":
        return tuple(canonicalize_name(v) for v in values)

    # other environment markers don't have such standards
    return values


def _evaluate_markers(markers: MarkerList, environment: dict[str, str]) -> bool:
    groups: list[list[bool]] = [[]]

    for marker in markers:
        assert isinstance(marker, (list, tuple, str))

        if isinstance(marker, list):
            groups[-1].append(_evaluate_markers(marker, environment))
        elif isinstance(marker, tuple):
            lhs, op, rhs = marker

            if isinstance(lhs, Variable):
                environment_key = lhs.value
                lhs_value = environment[environment_key]
                rhs_value = rhs.value
            else:
                lhs_value = lhs.value
                environment_key = rhs.value
                rhs_value = environment[environment_key]

            lhs_value, rhs_value = _normalize(lhs_value, rhs_value, key=environment_key)
            groups[-1].append(_eval_op(lhs_value, op, rhs_value))
        else:
            assert marker in ["and", "or"]
            if marker == "or":
                groups.append([])

    return any(all(item) for item in groups)


def format_full_version(info: sys._version_info) -> str:
    version = f"{info.major}.{info.minor}.{info.micro}"
    kind = info.releaselevel
    if kind != "final":
        version += kind[0] + str(info.serial)
    return version


def default_environment() -> Environment:
    iver = format_full_version(sys.implementation.version)
    implementation_name = sys.implementation.name
    return {
        "implementation_name": implementation_name,
        "implementation_version": iver,
        "os_name": os.name,
        "platform_machine": platform.machine(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python_full_version": platform.python_version(),
        "platform_python_implementation": platform.python_implementation(),
        "python_version": ".".join(platform.python_version_tuple()[:2]),
        "sys_platform": sys.platform,
    }


class Marker:
    def __init__(self, marker: str) -> None:
        # Note: We create a Marker object without calling this constructor in
        #       packaging.requirements.Requirement. If any additional logic is
        #       added here, make sure to mirror/adapt Requirement.
        try:
            self._markers = _normalize_extra_values(_parse_marker(marker))
            # The attribute `_markers` can be described in terms of a recursive type:
            # MarkerList = List[Union[Tuple[Node, ...], str, MarkerList]]
            #
            # For example, the following expression:
            # python_version > "3.6" or (python_version == "3.6" and os_name == "unix")
            #
            # is parsed into:
            # [
            #     (<Variable('python_version')>, <Op('>')>, <Value('3.6')>),
            #     'and',
            #     [
            #         (<Variable('python_version')>, <Op('==')>, <Value('3.6')>),
            #         'or',
            #         (<Variable('os_name')>, <Op('==')>, <Value('unix')>)
            #     ]
            # ]
        except ParserSyntaxError as e:
            raise InvalidMarker(str(e)) from e

    def __str__(self) -> str:
        return _format_marker(self._markers)

    def __repr__(self) -> str:
        return f"<Marker('{self}')>"

    def __hash__(self) -> int:
        return hash((self.__class__.__name__, str(self)))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Marker):
            return NotImplemented

        return str(self) == str(other)

    def evaluate(self, environment: dict[str, str] | None = None) -> bool:
        """Evaluate a marker.

        Return the boolean from evaluating the given marker against the
        environment. environment is an optional argument to override all or
        part of the determined environment.

        The environment is determined from the current Python process.
        """
        current_environment = cast("dict[str, str]", default_environment())
        current_environment["extra"] = ""
        if environment is not None:
            current_environment.update(environment)
            # The API used to allow setting extra to None. We need to handle this
            # case for backwards compatibility.
            if current_environment["extra"] is None:
                current_environment["extra"] = ""

        return _evaluate_markers(
            self._markers, _repair_python_full_version(current_environment)
        )


def _repair_python_full_version(env: dict[str, str]) -> dict[str, str]:
    """
    Work around platform.python_version() returning something that is not PEP 440
    compliant for non-tagged Python builds.
    """
    if env["python_full_version"].endswith("+"):
        env["python_full_version"] += "local"
    return env

# === NexusCore/openenv\Lib\site-packages\PIL\SpiderImagePlugin.py ===
#
# The Python Imaging Library.
#
# SPIDER image file handling
#
# History:
# 2004-08-02    Created BB
# 2006-03-02    added save method
# 2006-03-13    added support for stack images
#
# Copyright (c) 2004 by Health Research Inc. (HRI) RENSSELAER, NY 12144.
# Copyright (c) 2004 by William Baxter.
# Copyright (c) 2004 by Secret Labs AB.
# Copyright (c) 2004 by Fredrik Lundh.
#

##
# Image plugin for the Spider image format. This format is used
# by the SPIDER software, in processing image data from electron
# microscopy and tomography.
##

#
# SpiderImagePlugin.py
#
# The Spider image format is used by SPIDER software, in processing
# image data from electron microscopy and tomography.
#
# Spider home page:
# https://spider.wadsworth.org/spider_doc/spider/docs/spider.html
#
# Details about the Spider image format:
# https://spider.wadsworth.org/spider_doc/spider/docs/image_doc.html
#
from __future__ import annotations

import os
import struct
import sys
from typing import IO, Any, cast

from . import Image, ImageFile
from ._util import DeferredError

TYPE_CHECKING = False


def isInt(f: Any) -> int:
    try:
        i = int(f)
        if f - i == 0:
            return 1
        else:
            return 0
    except (ValueError, OverflowError):
        return 0


iforms = [1, 3, -11, -12, -21, -22]


# There is no magic number to identify Spider files, so just check a
# series of header locations to see if they have reasonable values.
# Returns no. of bytes in the header, if it is a valid Spider header,
# otherwise returns 0


def isSpiderHeader(t: tuple[float, ...]) -> int:
    h = (99,) + t  # add 1 value so can use spider header index start=1
    # header values 1,2,5,12,13,22,23 should be integers
    for i in [1, 2, 5, 12, 13, 22, 23]:
        if not isInt(h[i]):
            return 0
    # check iform
    iform = int(h[5])
    if iform not in iforms:
        return 0
    # check other header values
    labrec = int(h[13])  # no. records in file header
    labbyt = int(h[22])  # total no. of bytes in header
    lenbyt = int(h[23])  # record length in bytes
    if labbyt != (labrec * lenbyt):
        return 0
    # looks like a valid header
    return labbyt


def isSpiderImage(filename: str) -> int:
    with open(filename, "rb") as fp:
        f = fp.read(92)  # read 23 * 4 bytes
    t = struct.unpack(">23f", f)  # try big-endian first
    hdrlen = isSpiderHeader(t)
    if hdrlen == 0:
        t = struct.unpack("<23f", f)  # little-endian
        hdrlen = isSpiderHeader(t)
    return hdrlen


class SpiderImageFile(ImageFile.ImageFile):
    format = "SPIDER"
    format_description = "Spider 2D image"
    _close_exclusive_fp_after_loading = False

    def _open(self) -> None:
        # check header
        n = 27 * 4  # read 27 float values
        f = self.fp.read(n)

        try:
            self.bigendian = 1
            t = struct.unpack(">27f", f)  # try big-endian first
            hdrlen = isSpiderHeader(t)
            if hdrlen == 0:
                self.bigendian = 0
                t = struct.unpack("<27f", f)  # little-endian
                hdrlen = isSpiderHeader(t)
            if hdrlen == 0:
                msg = "not a valid Spider file"
                raise SyntaxError(msg)
        except struct.error as e:
            msg = "not a valid Spider file"
            raise SyntaxError(msg) from e

        h = (99,) + t  # add 1 value : spider header index starts at 1
        iform = int(h[5])
        if iform != 1:
            msg = "not a Spider 2D image"
            raise SyntaxError(msg)

        self._size = int(h[12]), int(h[2])  # size in pixels (width, height)
        self.istack = int(h[24])
        self.imgnumber = int(h[27])

        if self.istack == 0 and self.imgnumber == 0:
            # stk=0, img=0: a regular 2D image
            offset = hdrlen
            self._nimages = 1
        elif self.istack > 0 and self.imgnumber == 0:
            # stk>0, img=0: Opening the stack for the first time
            self.imgbytes = int(h[12]) * int(h[2]) * 4
            self.hdrlen = hdrlen
            self._nimages = int(h[26])
            # Point to the first image in the stack
            offset = hdrlen * 2
            self.imgnumber = 1
        elif self.istack == 0 and self.imgnumber > 0:
            # stk=0, img>0: an image within the stack
            offset = hdrlen + self.stkoffset
            self.istack = 2  # So Image knows it's still a stack
        else:
            msg = "inconsistent stack header values"
            raise SyntaxError(msg)

        if self.bigendian:
            self.rawmode = "F;32BF"
        else:
            self.rawmode = "F;32F"
        self._mode = "F"

        self.tile = [ImageFile._Tile("raw", (0, 0) + self.size, offset, self.rawmode)]
        self._fp = self.fp  # FIXME: hack

    @property
    def n_frames(self) -> int:
        return self._nimages

    @property
    def is_animated(self) -> bool:
        return self._nimages > 1

    # 1st image index is zero (although SPIDER imgnumber starts at 1)
    def tell(self) -> int:
        if self.imgnumber < 1:
            return 0
        else:
            return self.imgnumber - 1

    def seek(self, frame: int) -> None:
        if self.istack == 0:
            msg = "attempt to seek in a non-stack file"
            raise EOFError(msg)
        if not self._seek_check(frame):
            return
        if isinstance(self._fp, DeferredError):
            raise self._fp.ex
        self.stkoffset = self.hdrlen + frame * (self.hdrlen + self.imgbytes)
        self.fp = self._fp
        self.fp.seek(self.stkoffset)
        self._open()

    # returns a byte image after rescaling to 0..255
    def convert2byte(self, depth: int = 255) -> Image.Image:
        extrema = self.getextrema()
        assert isinstance(extrema[0], float)
        minimum, maximum = cast(tuple[float, float], extrema)
        m: float = 1
        if maximum != minimum:
            m = depth / (maximum - minimum)
        b = -m * minimum
        return self.point(lambda i: i * m + b).convert("L")

    if TYPE_CHECKING:
        from . import ImageTk

    # returns a ImageTk.PhotoImage object, after rescaling to 0..255
    def tkPhotoImage(self) -> ImageTk.PhotoImage:
        from . import ImageTk

        return ImageTk.PhotoImage(self.convert2byte(), palette=256)


# --------------------------------------------------------------------
# Image series


# given a list of filenames, return a list of images
def loadImageSeries(filelist: list[str] | None = None) -> list[Image.Image] | None:
    """create a list of :py:class:`~PIL.Image.Image` objects for use in a montage"""
    if filelist is None or len(filelist) < 1:
        return None

    byte_imgs = []
    for img in filelist:
        if not os.path.exists(img):
            print(f"unable to find {img}")
            continue
        try:
            with Image.open(img) as im:
                assert isinstance(im, SpiderImageFile)
                byte_im = im.convert2byte()
        except Exception:
            if not isSpiderImage(img):
                print(f"{img} is not a Spider image file")
            continue
        byte_im.info["filename"] = img
        byte_imgs.append(byte_im)
    return byte_imgs


# --------------------------------------------------------------------
# For saving images in Spider format


def makeSpiderHeader(im: Image.Image) -> list[bytes]:
    nsam, nrow = im.size
    lenbyt = nsam * 4  # There are labrec records in the header
    labrec = int(1024 / lenbyt)
    if 1024 % lenbyt != 0:
        labrec += 1
    labbyt = labrec * lenbyt
    nvalues = int(labbyt / 4)
    if nvalues < 23:
        return []

    hdr = [0.0] * nvalues

    # NB these are Fortran indices
    hdr[1] = 1.0  # nslice (=1 for an image)
    hdr[2] = float(nrow)  # number of rows per slice
    hdr[3] = float(nrow)  # number of records in the image
    hdr[5] = 1.0  # iform for 2D image
    hdr[12] = float(nsam)  # number of pixels per line
    hdr[13] = float(labrec)  # number of records in file header
    hdr[22] = float(labbyt)  # total number of bytes in header
    hdr[23] = float(lenbyt)  # record length in bytes

    # adjust for Fortran indexing
    hdr = hdr[1:]
    hdr.append(0.0)
    # pack binary data into a string
    return [struct.pack("f", v) for v in hdr]


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    if im.mode != "F":
        im = im.convert("F")

    hdr = makeSpiderHeader(im)
    if len(hdr) < 256:
        msg = "Error creating Spider header"
        raise OSError(msg)

    # write the SPIDER header
    fp.writelines(hdr)

    rawmode = "F;32NF"  # 32-bit native floating point
    ImageFile._save(im, fp, [ImageFile._Tile("raw", (0, 0) + im.size, 0, rawmode)])


def _save_spider(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    # get the filename extension and register it with Image
    filename_ext = os.path.splitext(filename)[1]
    ext = filename_ext.decode() if isinstance(filename_ext, bytes) else filename_ext
    Image.register_extension(SpiderImageFile.format, ext)
    _save(im, fp, filename)


# --------------------------------------------------------------------


Image.register_open(SpiderImageFile.format, SpiderImageFile)
Image.register_save(SpiderImageFile.format, _save_spider)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Syntax: python3 SpiderImagePlugin.py [infile] [outfile]")
        sys.exit()

    filename = sys.argv[1]
    if not isSpiderImage(filename):
        print("input image must be in Spider format")
        sys.exit()

    with Image.open(filename) as im:
        print(f"image: {im}")
        print(f"format: {im.format}")
        print(f"size: {im.size}")
        print(f"mode: {im.mode}")
        print("max, min: ", end=" ")
        print(im.getextrema())

        if len(sys.argv) > 2:
            outfile = sys.argv[2]

            # perform some image operation
            im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            print(
                f"saving a flipped version of {os.path.basename(filename)} "
                f"as {outfile} "
            )
            im.save(outfile, SpiderImageFile.format)

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc3281.py ===
# coding: utf-8
#
# This file is part of pyasn1-modules software.
#
# Created by Stanisław Pitucha with asn1ate tool.
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# An Internet Attribute Certificate Profile for Authorization
#
# ASN.1 source from:
# http://www.ietf.org/rfc/rfc3281.txt
#
from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc3280

MAX = float('inf')


def _buildOid(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


class ObjectDigestInfo(univ.Sequence):
    pass


ObjectDigestInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('digestedObjectType', univ.Enumerated(
        namedValues=namedval.NamedValues(('publicKey', 0), ('publicKeyCert', 1), ('otherObjectTypes', 2)))),
    namedtype.OptionalNamedType('otherObjectTypeID', univ.ObjectIdentifier()),
    namedtype.NamedType('digestAlgorithm', rfc3280.AlgorithmIdentifier()),
    namedtype.NamedType('objectDigest', univ.BitString())
)


class IssuerSerial(univ.Sequence):
    pass


IssuerSerial.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuer', rfc3280.GeneralNames()),
    namedtype.NamedType('serial', rfc3280.CertificateSerialNumber()),
    namedtype.OptionalNamedType('issuerUID', rfc3280.UniqueIdentifier())
)


class TargetCert(univ.Sequence):
    pass


TargetCert.componentType = namedtype.NamedTypes(
    namedtype.NamedType('targetCertificate', IssuerSerial()),
    namedtype.OptionalNamedType('targetName', rfc3280.GeneralName()),
    namedtype.OptionalNamedType('certDigestInfo', ObjectDigestInfo())
)


class Target(univ.Choice):
    pass


Target.componentType = namedtype.NamedTypes(
    namedtype.NamedType('targetName', rfc3280.GeneralName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('targetGroup', rfc3280.GeneralName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('targetCert',
                        TargetCert().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2)))
)


class Targets(univ.SequenceOf):
    pass


Targets.componentType = Target()


class ProxyInfo(univ.SequenceOf):
    pass


ProxyInfo.componentType = Targets()

id_at_role = _buildOid(rfc3280.id_at, 72)

id_pe_aaControls = _buildOid(rfc3280.id_pe, 6)

id_ce_targetInformation = _buildOid(rfc3280.id_ce, 55)

id_pe_ac_auditIdentity = _buildOid(rfc3280.id_pe, 4)


class ClassList(univ.BitString):
    pass


ClassList.namedValues = namedval.NamedValues(
    ('unmarked', 0),
    ('unclassified', 1),
    ('restricted', 2),
    ('confidential', 3),
    ('secret', 4),
    ('topSecret', 5)
)


class SecurityCategory(univ.Sequence):
    pass


SecurityCategory.componentType = namedtype.NamedTypes(
    namedtype.NamedType('type', univ.ObjectIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('value', univ.Any().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class Clearance(univ.Sequence):
    pass


Clearance.componentType = namedtype.NamedTypes(
    namedtype.NamedType('policyId', univ.ObjectIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.DefaultedNamedType('classList',
                                 ClassList().subtype(implicitTag=tag.Tag(tag.tagClassContext,
                                                                         tag.tagFormatSimple, 1)).subtype(
                                     value="unclassified")),
    namedtype.OptionalNamedType('securityCategories', univ.SetOf(componentType=SecurityCategory()).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
)


class AttCertVersion(univ.Integer):
    pass


AttCertVersion.namedValues = namedval.NamedValues(
    ('v2', 1)
)

id_aca = _buildOid(rfc3280.id_pkix, 10)

id_at_clearance = _buildOid(2, 5, 1, 5, 55)


class AttrSpec(univ.SequenceOf):
    pass


AttrSpec.componentType = univ.ObjectIdentifier()


class AAControls(univ.Sequence):
    pass


AAControls.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('pathLenConstraint',
                                univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, MAX))),
    namedtype.OptionalNamedType('permittedAttrs',
                                AttrSpec().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('excludedAttrs',
                                AttrSpec().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.DefaultedNamedType('permitUnSpecified', univ.Boolean().subtype(value=1))
)


class AttCertValidityPeriod(univ.Sequence):
    pass


AttCertValidityPeriod.componentType = namedtype.NamedTypes(
    namedtype.NamedType('notBeforeTime', useful.GeneralizedTime()),
    namedtype.NamedType('notAfterTime', useful.GeneralizedTime())
)


id_aca_authenticationInfo = _buildOid(id_aca, 1)


class V2Form(univ.Sequence):
    pass


V2Form.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('issuerName', rfc3280.GeneralNames()),
    namedtype.OptionalNamedType('baseCertificateID', IssuerSerial().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.OptionalNamedType('objectDigestInfo', ObjectDigestInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
)


class AttCertIssuer(univ.Choice):
    pass


AttCertIssuer.componentType = namedtype.NamedTypes(
    namedtype.NamedType('v1Form', rfc3280.GeneralNames()),
    namedtype.NamedType('v2Form',
                        V2Form().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)))
)


class Holder(univ.Sequence):
    pass


Holder.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('baseCertificateID', IssuerSerial().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.OptionalNamedType('entityName', rfc3280.GeneralNames().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('objectDigestInfo', ObjectDigestInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2)))
)


class AttributeCertificateInfo(univ.Sequence):
    pass


AttributeCertificateInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', AttCertVersion()),
    namedtype.NamedType('holder', Holder()),
    namedtype.NamedType('issuer', AttCertIssuer()),
    namedtype.NamedType('signature', rfc3280.AlgorithmIdentifier()),
    namedtype.NamedType('serialNumber', rfc3280.CertificateSerialNumber()),
    namedtype.NamedType('attrCertValidityPeriod', AttCertValidityPeriod()),
    namedtype.NamedType('attributes', univ.SequenceOf(componentType=rfc3280.Attribute())),
    namedtype.OptionalNamedType('issuerUniqueID', rfc3280.UniqueIdentifier()),
    namedtype.OptionalNamedType('extensions', rfc3280.Extensions())
)


class AttributeCertificate(univ.Sequence):
    pass


AttributeCertificate.componentType = namedtype.NamedTypes(
    namedtype.NamedType('acinfo', AttributeCertificateInfo()),
    namedtype.NamedType('signatureAlgorithm', rfc3280.AlgorithmIdentifier()),
    namedtype.NamedType('signatureValue', univ.BitString())
)

id_mod = _buildOid(rfc3280.id_pkix, 0)

id_mod_attribute_cert = _buildOid(id_mod, 12)

id_aca_accessIdentity = _buildOid(id_aca, 2)


class RoleSyntax(univ.Sequence):
    pass


RoleSyntax.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('roleAuthority', rfc3280.GeneralNames().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('roleName',
                        rfc3280.GeneralName().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)

id_aca_chargingIdentity = _buildOid(id_aca, 3)


class ACClearAttrs(univ.Sequence):
    pass


ACClearAttrs.componentType = namedtype.NamedTypes(
    namedtype.NamedType('acIssuer', rfc3280.GeneralName()),
    namedtype.NamedType('acSerial', univ.Integer()),
    namedtype.NamedType('attrs', univ.SequenceOf(componentType=rfc3280.Attribute()))
)

id_aca_group = _buildOid(id_aca, 4)

id_pe_ac_proxying = _buildOid(rfc3280.id_pe, 10)


class SvceAuthInfo(univ.Sequence):
    pass


SvceAuthInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('service', rfc3280.GeneralName()),
    namedtype.NamedType('ident', rfc3280.GeneralName()),
    namedtype.OptionalNamedType('authInfo', univ.OctetString())
)


class IetfAttrSyntax(univ.Sequence):
    pass


IetfAttrSyntax.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType(
        'policyAuthority', rfc3280.GeneralNames().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))
    ),
    namedtype.NamedType(
        'values', univ.SequenceOf(
            componentType=univ.Choice(
                componentType=namedtype.NamedTypes(
                    namedtype.NamedType('octets', univ.OctetString()),
                    namedtype.NamedType('oid', univ.ObjectIdentifier()),
                    namedtype.NamedType('string', char.UTF8String())
                )
            )
        )
    )
)

id_aca_encAttrs = _buildOid(id_aca, 6)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\types\text_service.py ===
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

from google.ai.generativelanguage_v1beta2.types import citation, safety

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta2",
    manifest={
        "GenerateTextRequest",
        "GenerateTextResponse",
        "TextPrompt",
        "TextCompletion",
        "EmbedTextRequest",
        "EmbedTextResponse",
        "Embedding",
    },
)


class GenerateTextRequest(proto.Message):
    r"""Request to generate a text completion response from the
    model.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        model (str):
            Required. The model name to use with the
            format name=models/{model}.
        prompt (google.ai.generativelanguage_v1beta2.types.TextPrompt):
            Required. The free-form input text given to
            the model as a prompt.
            Given a prompt, the model will generate a
            TextCompletion response it predicts as the
            completion of the input text.
        temperature (float):
            Controls the randomness of the output. Note: The default
            value varies by model, see the ``Model.temperature``
            attribute of the ``Model`` returned the ``getModel``
            function.

            Values can range from [0.0,1.0], inclusive. A value closer
            to 1.0 will produce responses that are more varied and
            creative, while a value closer to 0.0 will typically result
            in more straightforward responses from the model.

            This field is a member of `oneof`_ ``_temperature``.
        candidate_count (int):
            Number of generated responses to return.

            This value must be between [1, 8], inclusive. If unset, this
            will default to 1.

            This field is a member of `oneof`_ ``_candidate_count``.
        max_output_tokens (int):
            The maximum number of tokens to include in a
            candidate.
            If unset, this will default to 64.

            This field is a member of `oneof`_ ``_max_output_tokens``.
        top_p (float):
            The maximum cumulative probability of tokens to consider
            when sampling.

            The model uses combined Top-k and nucleus sampling.

            Tokens are sorted based on their assigned probabilities so
            that only the most liekly tokens are considered. Top-k
            sampling directly limits the maximum number of tokens to
            consider, while Nucleus sampling limits number of tokens
            based on the cumulative probability.

            Note: The default value varies by model, see the
            ``Model.top_p`` attribute of the ``Model`` returned the
            ``getModel`` function.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            The maximum number of tokens to consider when sampling.

            The model uses combined Top-k and nucleus sampling.

            Top-k sampling considers the set of ``top_k`` most probable
            tokens. Defaults to 40.

            Note: The default value varies by model, see the
            ``Model.top_k`` attribute of the ``Model`` returned the
            ``getModel`` function.

            This field is a member of `oneof`_ ``_top_k``.
        safety_settings (MutableSequence[google.ai.generativelanguage_v1beta2.types.SafetySetting]):
            A list of unique ``SafetySetting`` instances for blocking
            unsafe content.

            that will be enforced on the ``GenerateTextRequest.prompt``
            and ``GenerateTextResponse.candidates``. There should not be
            more than one setting for each ``SafetyCategory`` type. The
            API will block any prompts and responses that fail to meet
            the thresholds set by these settings. This list overrides
            the default settings for each ``SafetyCategory`` specified
            in the safety_settings. If there is no ``SafetySetting`` for
            a given ``SafetyCategory`` provided in the list, the API
            will use the default safety setting for that category.
        stop_sequences (MutableSequence[str]):
            The set of character sequences (up to 5) that
            will stop output generation. If specified, the
            API will stop at the first appearance of a stop
            sequence. The stop sequence will not be included
            as part of the response.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    prompt: "TextPrompt" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="TextPrompt",
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=3,
        optional=True,
    )
    candidate_count: int = proto.Field(
        proto.INT32,
        number=4,
        optional=True,
    )
    max_output_tokens: int = proto.Field(
        proto.INT32,
        number=5,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=6,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=7,
        optional=True,
    )
    safety_settings: MutableSequence[safety.SafetySetting] = proto.RepeatedField(
        proto.MESSAGE,
        number=8,
        message=safety.SafetySetting,
    )
    stop_sequences: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=9,
    )


class GenerateTextResponse(proto.Message):
    r"""The response from the model, including candidate completions.

    Attributes:
        candidates (MutableSequence[google.ai.generativelanguage_v1beta2.types.TextCompletion]):
            Candidate responses from the model.
        filters (MutableSequence[google.ai.generativelanguage_v1beta2.types.ContentFilter]):
            A set of content filtering metadata for the prompt and
            response text.

            This indicates which ``SafetyCategory``\ (s) blocked a
            candidate from this response, the lowest ``HarmProbability``
            that triggered a block, and the HarmThreshold setting for
            that category. This indicates the smallest change to the
            ``SafetySettings`` that would be necessary to unblock at
            least 1 response.

            The blocking is configured by the ``SafetySettings`` in the
            request (or the default ``SafetySettings`` of the API).
        safety_feedback (MutableSequence[google.ai.generativelanguage_v1beta2.types.SafetyFeedback]):
            Returns any safety feedback related to
            content filtering.
    """

    candidates: MutableSequence["TextCompletion"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="TextCompletion",
    )
    filters: MutableSequence[safety.ContentFilter] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message=safety.ContentFilter,
    )
    safety_feedback: MutableSequence[safety.SafetyFeedback] = proto.RepeatedField(
        proto.MESSAGE,
        number=4,
        message=safety.SafetyFeedback,
    )


class TextPrompt(proto.Message):
    r"""Text given to the model as a prompt.

    The Model will use this TextPrompt to Generate a text
    completion.

    Attributes:
        text (str):
            Required. The prompt text.
    """

    text: str = proto.Field(
        proto.STRING,
        number=1,
    )


class TextCompletion(proto.Message):
    r"""Output text returned from a model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        output (str):
            Output only. The generated text returned from
            the model.
        safety_ratings (MutableSequence[google.ai.generativelanguage_v1beta2.types.SafetyRating]):
            Ratings for the safety of a response.

            There is at most one rating per category.
        citation_metadata (google.ai.generativelanguage_v1beta2.types.CitationMetadata):
            Output only. Citation information for model-generated
            ``output`` in this ``TextCompletion``.

            This field may be populated with attribution information for
            any text included in the ``output``.

            This field is a member of `oneof`_ ``_citation_metadata``.
    """

    output: str = proto.Field(
        proto.STRING,
        number=1,
    )
    safety_ratings: MutableSequence[safety.SafetyRating] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=safety.SafetyRating,
    )
    citation_metadata: citation.CitationMetadata = proto.Field(
        proto.MESSAGE,
        number=3,
        optional=True,
        message=citation.CitationMetadata,
    )


class EmbedTextRequest(proto.Message):
    r"""Request to get a text embedding from the model.

    Attributes:
        model (str):
            Required. The model name to use with the
            format model=models/{model}.
        text (str):
            Required. The free-form input text that the
            model will turn into an embedding.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    text: str = proto.Field(
        proto.STRING,
        number=2,
    )


class EmbedTextResponse(proto.Message):
    r"""The response to a EmbedTextRequest.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        embedding (google.ai.generativelanguage_v1beta2.types.Embedding):
            Output only. The embedding generated from the
            input text.

            This field is a member of `oneof`_ ``_embedding``.
    """

    embedding: "Embedding" = proto.Field(
        proto.MESSAGE,
        number=1,
        optional=True,
        message="Embedding",
    )


class Embedding(proto.Message):
    r"""A list of floats representing the embedding.

    Attributes:
        value (MutableSequence[float]):
            The embedding values.
    """

    value: MutableSequence[float] = proto.RepeatedField(
        proto.FLOAT,
        number=1,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\_backend_gtk.py ===
"""
Common code for GTK3 and GTK4 backends.
"""

import logging
import sys

import matplotlib as mpl
from matplotlib import _api, backend_tools, cbook
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import (
    _Backend, FigureCanvasBase, FigureManagerBase, NavigationToolbar2,
    TimerBase)
from matplotlib.backend_tools import Cursors

import gi
# The GTK3/GTK4 backends will have already called `gi.require_version` to set
# the desired GTK.
from gi.repository import Gdk, Gio, GLib, Gtk


try:
    gi.require_foreign("cairo")
except ImportError as e:
    raise ImportError("Gtk-based backends require cairo") from e

_log = logging.getLogger(__name__)
_application = None  # Placeholder


def _shutdown_application(app):
    # The application might prematurely shut down if Ctrl-C'd out of IPython,
    # so close all windows.
    for win in app.get_windows():
        win.close()
    # The PyGObject wrapper incorrectly thinks that None is not allowed, or we
    # would call this:
    # Gio.Application.set_default(None)
    # Instead, we set this property and ignore default applications with it:
    app._created_by_matplotlib = True
    global _application
    _application = None


def _create_application():
    global _application

    if _application is None:
        app = Gio.Application.get_default()
        if app is None or getattr(app, '_created_by_matplotlib', False):
            # display_is_valid returns False only if on Linux and neither X11
            # nor Wayland display can be opened.
            if not mpl._c_internal_utils.display_is_valid():
                raise RuntimeError('Invalid DISPLAY variable')
            _application = Gtk.Application.new('org.matplotlib.Matplotlib3',
                                               Gio.ApplicationFlags.NON_UNIQUE)
            # The activate signal must be connected, but we don't care for
            # handling it, since we don't do any remote processing.
            _application.connect('activate', lambda *args, **kwargs: None)
            _application.connect('shutdown', _shutdown_application)
            _application.register()
            cbook._setup_new_guiapp()
        else:
            _application = app

    return _application


def mpl_to_gtk_cursor_name(mpl_cursor):
    return _api.check_getitem({
        Cursors.MOVE: "move",
        Cursors.HAND: "pointer",
        Cursors.POINTER: "default",
        Cursors.SELECT_REGION: "crosshair",
        Cursors.WAIT: "wait",
        Cursors.RESIZE_HORIZONTAL: "ew-resize",
        Cursors.RESIZE_VERTICAL: "ns-resize",
    }, cursor=mpl_cursor)


class TimerGTK(TimerBase):
    """Subclass of `.TimerBase` using GTK timer events."""

    def __init__(self, *args, **kwargs):
        self._timer = None
        super().__init__(*args, **kwargs)

    def _timer_start(self):
        # Need to stop it, otherwise we potentially leak a timer id that will
        # never be stopped.
        self._timer_stop()
        self._timer = GLib.timeout_add(self._interval, self._on_timer)

    def _timer_stop(self):
        if self._timer is not None:
            GLib.source_remove(self._timer)
            self._timer = None

    def _timer_set_interval(self):
        # Only stop and restart it if the timer has already been started.
        if self._timer is not None:
            self._timer_stop()
            self._timer_start()

    def _on_timer(self):
        super()._on_timer()

        # Gtk timeout_add() requires that the callback returns True if it
        # is to be called again.
        if self.callbacks and not self._single:
            return True
        else:
            self._timer = None
            return False


class _FigureCanvasGTK(FigureCanvasBase):
    _timer_cls = TimerGTK


class _FigureManagerGTK(FigureManagerBase):
    """
    Attributes
    ----------
    canvas : `FigureCanvas`
        The FigureCanvas instance
    num : int or str
        The Figure number
    toolbar : Gtk.Toolbar or Gtk.Box
        The toolbar
    vbox : Gtk.VBox
        The Gtk.VBox containing the canvas and toolbar
    window : Gtk.Window
        The Gtk.Window
    """

    def __init__(self, canvas, num):
        self._gtk_ver = gtk_ver = Gtk.get_major_version()

        app = _create_application()
        self.window = Gtk.Window()
        app.add_window(self.window)
        super().__init__(canvas, num)

        if gtk_ver == 3:
            icon_ext = "png" if sys.platform == "win32" else "svg"
            self.window.set_icon_from_file(
                str(cbook._get_data_path(f"images/matplotlib.{icon_ext}")))

        self.vbox = Gtk.Box()
        self.vbox.set_property("orientation", Gtk.Orientation.VERTICAL)

        if gtk_ver == 3:
            self.window.add(self.vbox)
            self.vbox.show()
            self.canvas.show()
            self.vbox.pack_start(self.canvas, True, True, 0)
        elif gtk_ver == 4:
            self.window.set_child(self.vbox)
            self.vbox.prepend(self.canvas)

        # calculate size for window
        w, h = self.canvas.get_width_height()

        if self.toolbar is not None:
            if gtk_ver == 3:
                self.toolbar.show()
                self.vbox.pack_end(self.toolbar, False, False, 0)
            elif gtk_ver == 4:
                sw = Gtk.ScrolledWindow(vscrollbar_policy=Gtk.PolicyType.NEVER)
                sw.set_child(self.toolbar)
                self.vbox.append(sw)
            min_size, nat_size = self.toolbar.get_preferred_size()
            h += nat_size.height

        self.window.set_default_size(w, h)

        self._destroying = False
        self.window.connect("destroy", lambda *args: Gcf.destroy(self))
        self.window.connect({3: "delete_event", 4: "close-request"}[gtk_ver],
                            lambda *args: Gcf.destroy(self))
        if mpl.is_interactive():
            self.window.show()
            self.canvas.draw_idle()

        self.canvas.grab_focus()

    def destroy(self, *args):
        if self._destroying:
            # Otherwise, this can be called twice when the user presses 'q',
            # which calls Gcf.destroy(self), then this destroy(), then triggers
            # Gcf.destroy(self) once again via
            # `connect("destroy", lambda *args: Gcf.destroy(self))`.
            return
        self._destroying = True
        self.window.destroy()
        self.canvas.destroy()

    @classmethod
    def start_main_loop(cls):
        global _application
        if _application is None:
            return

        try:
            _application.run()  # Quits when all added windows close.
        except KeyboardInterrupt:
            # Ensure all windows can process their close event from
            # _shutdown_application.
            context = GLib.MainContext.default()
            while context.pending():
                context.iteration(True)
            raise
        finally:
            # Running after quit is undefined, so create a new one next time.
            _application = None

    def show(self):
        # show the figure window
        self.window.show()
        self.canvas.draw()
        if mpl.rcParams["figure.raise_window"]:
            meth_name = {3: "get_window", 4: "get_surface"}[self._gtk_ver]
            if getattr(self.window, meth_name)():
                self.window.present()
            else:
                # If this is called by a callback early during init,
                # self.window (a GtkWindow) may not have an associated
                # low-level GdkWindow (on GTK3) or GdkSurface (on GTK4) yet,
                # and present() would crash.
                _api.warn_external("Cannot raise window yet to be setup")

    def full_screen_toggle(self):
        is_fullscreen = {
            3: lambda w: (w.get_window().get_state()
                          & Gdk.WindowState.FULLSCREEN),
            4: lambda w: w.is_fullscreen(),
        }[self._gtk_ver]
        if is_fullscreen(self.window):
            self.window.unfullscreen()
        else:
            self.window.fullscreen()

    def get_window_title(self):
        return self.window.get_title()

    def set_window_title(self, title):
        self.window.set_title(title)

    def resize(self, width, height):
        width = int(width / self.canvas.device_pixel_ratio)
        height = int(height / self.canvas.device_pixel_ratio)
        if self.toolbar:
            min_size, nat_size = self.toolbar.get_preferred_size()
            height += nat_size.height
        canvas_size = self.canvas.get_allocation()
        if self._gtk_ver >= 4 or canvas_size.width == canvas_size.height == 1:
            # A canvas size of (1, 1) cannot exist in most cases, because
            # window decorations would prevent such a small window. This call
            # must be before the window has been mapped and widgets have been
            # sized, so just change the window's starting size.
            self.window.set_default_size(width, height)
        else:
            self.window.resize(width, height)


class _NavigationToolbar2GTK(NavigationToolbar2):
    # Must be implemented in GTK3/GTK4 backends:
    # * __init__
    # * save_figure

    def set_message(self, s):
        escaped = GLib.markup_escape_text(s)
        self.message.set_markup(f'<small>{escaped}</small>')

    def draw_rubberband(self, event, x0, y0, x1, y1):
        height = self.canvas.figure.bbox.height
        y1 = height - y1
        y0 = height - y0
        rect = [int(val) for val in (x0, y0, x1 - x0, y1 - y0)]
        self.canvas._draw_rubberband(rect)

    def remove_rubberband(self):
        self.canvas._draw_rubberband(None)

    def _update_buttons_checked(self):
        for name, active in [("Pan", "PAN"), ("Zoom", "ZOOM")]:
            button = self._gtk_ids.get(name)
            if button:
                with button.handler_block(button._signal_handler):
                    button.set_active(self.mode.name == active)

    def pan(self, *args):
        super().pan(*args)
        self._update_buttons_checked()

    def zoom(self, *args):
        super().zoom(*args)
        self._update_buttons_checked()

    def set_history_buttons(self):
        can_backward = self._nav_stack._pos > 0
        can_forward = self._nav_stack._pos < len(self._nav_stack) - 1
        if 'Back' in self._gtk_ids:
            self._gtk_ids['Back'].set_sensitive(can_backward)
        if 'Forward' in self._gtk_ids:
            self._gtk_ids['Forward'].set_sensitive(can_forward)


class RubberbandGTK(backend_tools.RubberbandBase):
    def draw_rubberband(self, x0, y0, x1, y1):
        _NavigationToolbar2GTK.draw_rubberband(
            self._make_classic_style_pseudo_toolbar(), None, x0, y0, x1, y1)

    def remove_rubberband(self):
        _NavigationToolbar2GTK.remove_rubberband(
            self._make_classic_style_pseudo_toolbar())


class ConfigureSubplotsGTK(backend_tools.ConfigureSubplotsBase):
    def trigger(self, *args):
        _NavigationToolbar2GTK.configure_subplots(self, None)


class _BackendGTK(_Backend):
    backend_version = "{}.{}.{}".format(
        Gtk.get_major_version(),
        Gtk.get_minor_version(),
        Gtk.get_micro_version(),
    )
    mainloop = _FigureManagerGTK.start_main_loop

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\reviews.py ===
# Natural Language Toolkit: Product Reviews Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Pierpaolo Pantone <24alsecondo@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
CorpusReader for reviews corpora (syntax based on Customer Review Corpus).

Customer Review Corpus information
==================================

Annotated by: Minqing Hu and Bing Liu, 2004.
    Department of Computer Science
    University of Illinois at Chicago

Contact: Bing Liu, liub@cs.uic.edu
        https://www.cs.uic.edu/~liub

Distributed with permission.

The "product_reviews_1" and "product_reviews_2" datasets respectively contain
annotated customer reviews of 5 and 9 products from amazon.com.

Related papers:

- Minqing Hu and Bing Liu. "Mining and summarizing customer reviews".
    Proceedings of the ACM SIGKDD International Conference on Knowledge
    Discovery & Data Mining (KDD-04), 2004.

- Minqing Hu and Bing Liu. "Mining Opinion Features in Customer Reviews".
    Proceedings of Nineteeth National Conference on Artificial Intelligence
    (AAAI-2004), 2004.

- Xiaowen Ding, Bing Liu and Philip S. Yu. "A Holistic Lexicon-Based Appraoch to
    Opinion Mining." Proceedings of First ACM International Conference on Web
    Search and Data Mining (WSDM-2008), Feb 11-12, 2008, Stanford University,
    Stanford, California, USA.

Symbols used in the annotated reviews:

    :[t]: the title of the review: Each [t] tag starts a review.
    :xxxx[+|-n]: xxxx is a product feature.
    :[+n]: Positive opinion, n is the opinion strength: 3 strongest, and 1 weakest.
           Note that the strength is quite subjective.
           You may want ignore it, but only considering + and -
    :[-n]: Negative opinion
    :##:   start of each sentence. Each line is a sentence.
    :[u]:  feature not appeared in the sentence.
    :[p]:  feature not appeared in the sentence. Pronoun resolution is needed.
    :[s]:  suggestion or recommendation.
    :[cc]: comparison with a competing product from a different brand.
    :[cs]: comparison with a competing product from the same brand.

Note: Some of the files (e.g. "ipod.txt", "Canon PowerShot SD500.txt") do not
    provide separation between different reviews. This is due to the fact that
    the dataset was specifically designed for aspect/feature-based sentiment
    analysis, for which sentence-level annotation is sufficient. For document-
    level classification and analysis, this peculiarity should be taken into
    consideration.
"""

import re

from nltk.corpus.reader.api import *
from nltk.tokenize import *

TITLE = re.compile(r"^\[t\](.*)$")  # [t] Title
FEATURES = re.compile(
    r"((?:(?:\w+\s)+)?\w+)\[((?:\+|\-)\d)\]"
)  # find 'feature' in feature[+3]
NOTES = re.compile(r"\[(?!t)(p|u|s|cc|cs)\]")  # find 'p' in camera[+2][p]
SENT = re.compile(r"##(.*)$")  # find tokenized sentence


class Review:
    """
    A Review is the main block of a ReviewsCorpusReader.
    """

    def __init__(self, title=None, review_lines=None):
        """
        :param title: the title of the review.
        :param review_lines: the list of the ReviewLines that belong to the Review.
        """
        self.title = title
        if review_lines is None:
            self.review_lines = []
        else:
            self.review_lines = review_lines

    def add_line(self, review_line):
        """
        Add a line (ReviewLine) to the review.

        :param review_line: a ReviewLine instance that belongs to the Review.
        """
        assert isinstance(review_line, ReviewLine)
        self.review_lines.append(review_line)

    def features(self):
        """
        Return a list of features in the review. Each feature is a tuple made of
        the specific item feature and the opinion strength about that feature.

        :return: all features of the review as a list of tuples (feat, score).
        :rtype: list(tuple)
        """
        features = []
        for review_line in self.review_lines:
            features.extend(review_line.features)
        return features

    def sents(self):
        """
        Return all tokenized sentences in the review.

        :return: all sentences of the review as lists of tokens.
        :rtype: list(list(str))
        """
        return [review_line.sent for review_line in self.review_lines]

    def __repr__(self):
        return 'Review(title="{}", review_lines={})'.format(
            self.title, self.review_lines
        )


class ReviewLine:
    """
    A ReviewLine represents a sentence of the review, together with (optional)
    annotations of its features and notes about the reviewed item.
    """

    def __init__(self, sent, features=None, notes=None):
        self.sent = sent
        if features is None:
            self.features = []
        else:
            self.features = features

        if notes is None:
            self.notes = []
        else:
            self.notes = notes

    def __repr__(self):
        return "ReviewLine(features={}, notes={}, sent={})".format(
            self.features, self.notes, self.sent
        )


class ReviewsCorpusReader(CorpusReader):
    """
    Reader for the Customer Review Data dataset by Hu, Liu (2004).
    Note: we are not applying any sentence tokenization at the moment, just word
    tokenization.

        >>> from nltk.corpus import product_reviews_1
        >>> camera_reviews = product_reviews_1.reviews('Canon_G3.txt')
        >>> review = camera_reviews[0]
        >>> review.sents()[0] # doctest: +NORMALIZE_WHITESPACE
        ['i', 'recently', 'purchased', 'the', 'canon', 'powershot', 'g3', 'and', 'am',
        'extremely', 'satisfied', 'with', 'the', 'purchase', '.']
        >>> review.features() # doctest: +NORMALIZE_WHITESPACE
        [('canon powershot g3', '+3'), ('use', '+2'), ('picture', '+2'),
        ('picture quality', '+1'), ('picture quality', '+1'), ('camera', '+2'),
        ('use', '+2'), ('feature', '+1'), ('picture quality', '+3'), ('use', '+1'),
        ('option', '+1')]

    We can also reach the same information directly from the stream:

        >>> product_reviews_1.features('Canon_G3.txt')
        [('canon powershot g3', '+3'), ('use', '+2'), ...]

    We can compute stats for specific product features:

        >>> n_reviews = len([(feat,score) for (feat,score) in product_reviews_1.features('Canon_G3.txt') if feat=='picture'])
        >>> tot = sum([int(score) for (feat,score) in product_reviews_1.features('Canon_G3.txt') if feat=='picture'])
        >>> mean = tot / n_reviews
        >>> print(n_reviews, tot, mean)
        15 24 1.6
    """

    CorpusView = StreamBackedCorpusView

    def __init__(
        self, root, fileids, word_tokenizer=WordPunctTokenizer(), encoding="utf8"
    ):
        """
        :param root: The root directory for the corpus.
        :param fileids: a list or regexp specifying the fileids in the corpus.
        :param word_tokenizer: a tokenizer for breaking sentences or paragraphs
            into words. Default: `WordPunctTokenizer`
        :param encoding: the encoding that should be used to read the corpus.
        """

        CorpusReader.__init__(self, root, fileids, encoding)
        self._word_tokenizer = word_tokenizer
        self._readme = "README.txt"

    def features(self, fileids=None):
        """
        Return a list of features. Each feature is a tuple made of the specific
        item feature and the opinion strength about that feature.

        :param fileids: a list or regexp specifying the ids of the files whose
            features have to be returned.
        :return: all features for the item(s) in the given file(s).
        :rtype: list(tuple)
        """
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, str):
            fileids = [fileids]
        return concat(
            [
                self.CorpusView(fileid, self._read_features, encoding=enc)
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def reviews(self, fileids=None):
        """
        Return all the reviews as a list of Review objects. If `fileids` is
        specified, return all the reviews from each of the specified files.

        :param fileids: a list or regexp specifying the ids of the files whose
            reviews have to be returned.
        :return: the given file(s) as a list of reviews.
        """
        if fileids is None:
            fileids = self._fileids
        return concat(
            [
                self.CorpusView(fileid, self._read_review_block, encoding=enc)
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def sents(self, fileids=None):
        """
        Return all sentences in the corpus or in the specified files.

        :param fileids: a list or regexp specifying the ids of the files whose
            sentences have to be returned.
        :return: the given file(s) as a list of sentences, each encoded as a
            list of word strings.
        :rtype: list(list(str))
        """
        return concat(
            [
                self.CorpusView(path, self._read_sent_block, encoding=enc)
                for (path, enc, fileid) in self.abspaths(fileids, True, True)
            ]
        )

    def words(self, fileids=None):
        """
        Return all words and punctuation symbols in the corpus or in the specified
        files.

        :param fileids: a list or regexp specifying the ids of the files whose
            words have to be returned.
        :return: the given file(s) as a list of words and punctuation symbols.
        :rtype: list(str)
        """
        return concat(
            [
                self.CorpusView(path, self._read_word_block, encoding=enc)
                for (path, enc, fileid) in self.abspaths(fileids, True, True)
            ]
        )

    def _read_features(self, stream):
        features = []
        for i in range(20):
            line = stream.readline()
            if not line:
                return features
            features.extend(re.findall(FEATURES, line))
        return features

    def _read_review_block(self, stream):
        while True:
            line = stream.readline()
            if not line:
                return []  # end of file.
            title_match = re.match(TITLE, line)
            if title_match:
                review = Review(
                    title=title_match.group(1).strip()
                )  # We create a new review
                break

        # Scan until we find another line matching the regexp, or EOF.
        while True:
            oldpos = stream.tell()
            line = stream.readline()
            # End of file:
            if not line:
                return [review]
            # Start of a new review: backup to just before it starts, and
            # return the review we've already collected.
            if re.match(TITLE, line):
                stream.seek(oldpos)
                return [review]
            # Anything else is part of the review line.
            feats = re.findall(FEATURES, line)
            notes = re.findall(NOTES, line)
            sent = re.findall(SENT, line)
            if sent:
                sent = self._word_tokenizer.tokenize(sent[0])
            review_line = ReviewLine(sent=sent, features=feats, notes=notes)
            review.add_line(review_line)

    def _read_sent_block(self, stream):
        sents = []
        for review in self._read_review_block(stream):
            sents.extend([sent for sent in review.sents()])
        return sents

    def _read_word_block(self, stream):
        words = []
        for i in range(20):  # Read 20 lines at a time.
            line = stream.readline()
            sent = re.findall(SENT, line)
            if sent:
                words.extend(self._word_tokenizer.tokenize(sent[0]))
        return words

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\packaging\markers.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import annotations

import operator
import os
import platform
import sys
from typing import Any, Callable, TypedDict, cast

from ._parser import MarkerAtom, MarkerList, Op, Value, Variable
from ._parser import parse_marker as _parse_marker
from ._tokenizer import ParserSyntaxError
from .specifiers import InvalidSpecifier, Specifier
from .utils import canonicalize_name

__all__ = [
    "InvalidMarker",
    "Marker",
    "UndefinedComparison",
    "UndefinedEnvironmentName",
    "default_environment",
]

Operator = Callable[[str, str], bool]


class InvalidMarker(ValueError):
    """
    An invalid marker was found, users should refer to PEP 508.
    """


class UndefinedComparison(ValueError):
    """
    An invalid operation was attempted on a value that doesn't support it.
    """


class UndefinedEnvironmentName(ValueError):
    """
    A name was attempted to be used that does not exist inside of the
    environment.
    """


class Environment(TypedDict):
    implementation_name: str
    """The implementation's identifier, e.g. ``'cpython'``."""

    implementation_version: str
    """
    The implementation's version, e.g. ``'3.13.0a2'`` for CPython 3.13.0a2, or
    ``'7.3.13'`` for PyPy3.10 v7.3.13.
    """

    os_name: str
    """
    The value of :py:data:`os.name`. The name of the operating system dependent module
    imported, e.g. ``'posix'``.
    """

    platform_machine: str
    """
    Returns the machine type, e.g. ``'i386'``.

    An empty string if the value cannot be determined.
    """

    platform_release: str
    """
    The system's release, e.g. ``'2.2.0'`` or ``'NT'``.

    An empty string if the value cannot be determined.
    """

    platform_system: str
    """
    The system/OS name, e.g. ``'Linux'``, ``'Windows'`` or ``'Java'``.

    An empty string if the value cannot be determined.
    """

    platform_version: str
    """
    The system's release version, e.g. ``'#3 on degas'``.

    An empty string if the value cannot be determined.
    """

    python_full_version: str
    """
    The Python version as string ``'major.minor.patchlevel'``.

    Note that unlike the Python :py:data:`sys.version`, this value will always include
    the patchlevel (it defaults to 0).
    """

    platform_python_implementation: str
    """
    A string identifying the Python implementation, e.g. ``'CPython'``.
    """

    python_version: str
    """The Python version as string ``'major.minor'``."""

    sys_platform: str
    """
    This string contains a platform identifier that can be used to append
    platform-specific components to :py:data:`sys.path`, for instance.

    For Unix systems, except on Linux and AIX, this is the lowercased OS name as
    returned by ``uname -s`` with the first part of the version as returned by
    ``uname -r`` appended, e.g. ``'sunos5'`` or ``'freebsd8'``, at the time when Python
    was built.
    """


def _normalize_extra_values(results: Any) -> Any:
    """
    Normalize extra values.
    """
    if isinstance(results[0], tuple):
        lhs, op, rhs = results[0]
        if isinstance(lhs, Variable) and lhs.value == "extra":
            normalized_extra = canonicalize_name(rhs.value)
            rhs = Value(normalized_extra)
        elif isinstance(rhs, Variable) and rhs.value == "extra":
            normalized_extra = canonicalize_name(lhs.value)
            lhs = Value(normalized_extra)
        results[0] = lhs, op, rhs
    return results


def _format_marker(
    marker: list[str] | MarkerAtom | str, first: bool | None = True
) -> str:
    assert isinstance(marker, (list, tuple, str))

    # Sometimes we have a structure like [[...]] which is a single item list
    # where the single item is itself it's own list. In that case we want skip
    # the rest of this function so that we don't get extraneous () on the
    # outside.
    if (
        isinstance(marker, list)
        and len(marker) == 1
        and isinstance(marker[0], (list, tuple))
    ):
        return _format_marker(marker[0])

    if isinstance(marker, list):
        inner = (_format_marker(m, first=False) for m in marker)
        if first:
            return " ".join(inner)
        else:
            return "(" + " ".join(inner) + ")"
    elif isinstance(marker, tuple):
        return " ".join([m.serialize() for m in marker])
    else:
        return marker


_operators: dict[str, Operator] = {
    "in": lambda lhs, rhs: lhs in rhs,
    "not in": lambda lhs, rhs: lhs not in rhs,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    ">": operator.gt,
}


def _eval_op(lhs: str, op: Op, rhs: str) -> bool:
    try:
        spec = Specifier("".join([op.serialize(), rhs]))
    except InvalidSpecifier:
        pass
    else:
        return spec.contains(lhs, prereleases=True)

    oper: Operator | None = _operators.get(op.serialize())
    if oper is None:
        raise UndefinedComparison(f"Undefined {op!r} on {lhs!r} and {rhs!r}.")

    return oper(lhs, rhs)


def _normalize(*values: str, key: str) -> tuple[str, ...]:
    # PEP 685 – Comparison of extra names for optional distribution dependencies
    # https://peps.python.org/pep-0685/
    # > When comparing extra names, tools MUST normalize the names being
    # > compared using the semantics outlined in PEP 503 for names
    if key == "extra":
        return tuple(canonicalize_name(v) for v in values)

    # other environment markers don't have such standards
    return values


def _evaluate_markers(markers: MarkerList, environment: dict[str, str]) -> bool:
    groups: list[list[bool]] = [[]]

    for marker in markers:
        assert isinstance(marker, (list, tuple, str))

        if isinstance(marker, list):
            groups[-1].append(_evaluate_markers(marker, environment))
        elif isinstance(marker, tuple):
            lhs, op, rhs = marker

            if isinstance(lhs, Variable):
                environment_key = lhs.value
                lhs_value = environment[environment_key]
                rhs_value = rhs.value
            else:
                lhs_value = lhs.value
                environment_key = rhs.value
                rhs_value = environment[environment_key]

            lhs_value, rhs_value = _normalize(lhs_value, rhs_value, key=environment_key)
            groups[-1].append(_eval_op(lhs_value, op, rhs_value))
        else:
            assert marker in ["and", "or"]
            if marker == "or":
                groups.append([])

    return any(all(item) for item in groups)


def format_full_version(info: sys._version_info) -> str:
    version = f"{info.major}.{info.minor}.{info.micro}"
    kind = info.releaselevel
    if kind != "final":
        version += kind[0] + str(info.serial)
    return version


def default_environment() -> Environment:
    iver = format_full_version(sys.implementation.version)
    implementation_name = sys.implementation.name
    return {
        "implementation_name": implementation_name,
        "implementation_version": iver,
        "os_name": os.name,
        "platform_machine": platform.machine(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python_full_version": platform.python_version(),
        "platform_python_implementation": platform.python_implementation(),
        "python_version": ".".join(platform.python_version_tuple()[:2]),
        "sys_platform": sys.platform,
    }


class Marker:
    def __init__(self, marker: str) -> None:
        # Note: We create a Marker object without calling this constructor in
        #       packaging.requirements.Requirement. If any additional logic is
        #       added here, make sure to mirror/adapt Requirement.
        try:
            self._markers = _normalize_extra_values(_parse_marker(marker))
            # The attribute `_markers` can be described in terms of a recursive type:
            # MarkerList = List[Union[Tuple[Node, ...], str, MarkerList]]
            #
            # For example, the following expression:
            # python_version > "3.6" or (python_version == "3.6" and os_name == "unix")
            #
            # is parsed into:
            # [
            #     (<Variable('python_version')>, <Op('>')>, <Value('3.6')>),
            #     'and',
            #     [
            #         (<Variable('python_version')>, <Op('==')>, <Value('3.6')>),
            #         'or',
            #         (<Variable('os_name')>, <Op('==')>, <Value('unix')>)
            #     ]
            # ]
        except ParserSyntaxError as e:
            raise InvalidMarker(str(e)) from e

    def __str__(self) -> str:
        return _format_marker(self._markers)

    def __repr__(self) -> str:
        return f"<Marker('{self}')>"

    def __hash__(self) -> int:
        return hash((self.__class__.__name__, str(self)))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Marker):
            return NotImplemented

        return str(self) == str(other)

    def evaluate(self, environment: dict[str, str] | None = None) -> bool:
        """Evaluate a marker.

        Return the boolean from evaluating the given marker against the
        environment. environment is an optional argument to override all or
        part of the determined environment.

        The environment is determined from the current Python process.
        """
        current_environment = cast("dict[str, str]", default_environment())
        current_environment["extra"] = ""
        if environment is not None:
            current_environment.update(environment)
            # The API used to allow setting extra to None. We need to handle this
            # case for backwards compatibility.
            if current_environment["extra"] is None:
                current_environment["extra"] = ""

        return _evaluate_markers(
            self._markers, _repair_python_full_version(current_environment)
        )


def _repair_python_full_version(env: dict[str, str]) -> dict[str, str]:
    """
    Work around platform.python_version() returning something that is not PEP 440
    compliant for non-tagged Python builds.
    """
    if env["python_full_version"].endswith("+"):
        env["python_full_version"] += "local"
    return env

# === NexusCore/openenv\Lib\site-packages\pyasn1\codec\cer\encoder.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import warnings

from pyasn1 import error
from pyasn1.codec.ber import encoder
from pyasn1.type import univ
from pyasn1.type import useful

__all__ = ['Encoder', 'encode']


class BooleanEncoder(encoder.IntegerEncoder):
    def encodeValue(self, value, asn1Spec, encodeFun, **options):
        if value == 0:
            substrate = (0,)
        else:
            substrate = (255,)
        return substrate, False, False


class RealEncoder(encoder.RealEncoder):
    def _chooseEncBase(self, value):
        m, b, e = value
        return self._dropFloatingPoint(m, b, e)


# specialized GeneralStringEncoder here

class TimeEncoderMixIn(object):
    Z_CHAR = ord('Z')
    PLUS_CHAR = ord('+')
    MINUS_CHAR = ord('-')
    COMMA_CHAR = ord(',')
    DOT_CHAR = ord('.')
    ZERO_CHAR = ord('0')

    MIN_LENGTH = 12
    MAX_LENGTH = 19

    def encodeValue(self, value, asn1Spec, encodeFun, **options):
        # CER encoding constraints:
        # - minutes are mandatory, seconds are optional
        # - sub-seconds must NOT be zero / no meaningless zeros
        # - no hanging fraction dot
        # - time in UTC (Z)
        # - only dot is allowed for fractions

        if asn1Spec is not None:
            value = asn1Spec.clone(value)

        numbers = value.asNumbers()

        if self.PLUS_CHAR in numbers or self.MINUS_CHAR in numbers:
            raise error.PyAsn1Error('Must be UTC time: %r' % value)

        if numbers[-1] != self.Z_CHAR:
            raise error.PyAsn1Error('Missing "Z" time zone specifier: %r' % value)

        if self.COMMA_CHAR in numbers:
            raise error.PyAsn1Error('Comma in fractions disallowed: %r' % value)

        if self.DOT_CHAR in numbers:

            isModified = False

            numbers = list(numbers)

            searchIndex = min(numbers.index(self.DOT_CHAR) + 4, len(numbers) - 1)

            while numbers[searchIndex] != self.DOT_CHAR:
                if numbers[searchIndex] == self.ZERO_CHAR:
                    del numbers[searchIndex]
                    isModified = True

                searchIndex -= 1

            searchIndex += 1

            if searchIndex < len(numbers):
                if numbers[searchIndex] == self.Z_CHAR:
                    # drop hanging comma
                    del numbers[searchIndex - 1]
                    isModified = True

            if isModified:
                value = value.clone(numbers)

        if not self.MIN_LENGTH < len(numbers) < self.MAX_LENGTH:
            raise error.PyAsn1Error('Length constraint violated: %r' % value)

        options.update(maxChunkSize=1000)

        return encoder.OctetStringEncoder.encodeValue(
            self, value, asn1Spec, encodeFun, **options
        )


class GeneralizedTimeEncoder(TimeEncoderMixIn, encoder.OctetStringEncoder):
    MIN_LENGTH = 12
    MAX_LENGTH = 20


class UTCTimeEncoder(TimeEncoderMixIn, encoder.OctetStringEncoder):
    MIN_LENGTH = 10
    MAX_LENGTH = 14


class SetOfEncoder(encoder.SequenceOfEncoder):
    def encodeValue(self, value, asn1Spec, encodeFun, **options):
        chunks = self._encodeComponents(
            value, asn1Spec, encodeFun, **options)

        # sort by serialised and padded components
        if len(chunks) > 1:
            zero = b'\x00'
            maxLen = max(map(len, chunks))
            paddedChunks = [
                (x.ljust(maxLen, zero), x) for x in chunks
            ]
            paddedChunks.sort(key=lambda x: x[0])

            chunks = [x[1] for x in paddedChunks]

        return b''.join(chunks), True, True


class SequenceOfEncoder(encoder.SequenceOfEncoder):
    def encodeValue(self, value, asn1Spec, encodeFun, **options):

        if options.get('ifNotEmpty', False) and not len(value):
            return b'', True, True

        chunks = self._encodeComponents(
            value, asn1Spec, encodeFun, **options)

        return b''.join(chunks), True, True


class SetEncoder(encoder.SequenceEncoder):
    @staticmethod
    def _componentSortKey(componentAndType):
        """Sort SET components by tag

        Sort regardless of the Choice value (static sort)
        """
        component, asn1Spec = componentAndType

        if asn1Spec is None:
            asn1Spec = component

        if asn1Spec.typeId == univ.Choice.typeId and not asn1Spec.tagSet:
            if asn1Spec.tagSet:
                return asn1Spec.tagSet
            else:
                return asn1Spec.componentType.minTagSet
        else:
            return asn1Spec.tagSet

    def encodeValue(self, value, asn1Spec, encodeFun, **options):

        substrate = b''

        comps = []
        compsMap = {}

        if asn1Spec is None:
            # instance of ASN.1 schema
            inconsistency = value.isInconsistent
            if inconsistency:
                raise error.PyAsn1Error(
                    f"ASN.1 object {value.__class__.__name__} is inconsistent")

            namedTypes = value.componentType

            for idx, component in enumerate(value.values()):
                if namedTypes:
                    namedType = namedTypes[idx]

                    if namedType.isOptional and not component.isValue:
                            continue

                    if namedType.isDefaulted and component == namedType.asn1Object:
                            continue

                    compsMap[id(component)] = namedType

                else:
                    compsMap[id(component)] = None

                comps.append((component, asn1Spec))

        else:
            # bare Python value + ASN.1 schema
            for idx, namedType in enumerate(asn1Spec.componentType.namedTypes):

                try:
                    component = value[namedType.name]

                except KeyError:
                    raise error.PyAsn1Error('Component name "%s" not found in %r' % (namedType.name, value))

                if namedType.isOptional and namedType.name not in value:
                    continue

                if namedType.isDefaulted and component == namedType.asn1Object:
                    continue

                compsMap[id(component)] = namedType
                comps.append((component, asn1Spec[idx]))

        for comp, compType in sorted(comps, key=self._componentSortKey):
            namedType = compsMap[id(comp)]

            if namedType:
                options.update(ifNotEmpty=namedType.isOptional)

            chunk = encodeFun(comp, compType, **options)

            # wrap open type blob if needed
            if namedType and namedType.openType:
                wrapType = namedType.asn1Object
                if wrapType.tagSet and not wrapType.isSameTypeWith(comp):
                    chunk = encodeFun(chunk, wrapType, **options)

            substrate += chunk

        return substrate, True, True


class SequenceEncoder(encoder.SequenceEncoder):
    omitEmptyOptionals = True


TAG_MAP = encoder.TAG_MAP.copy()

TAG_MAP.update({
    univ.Boolean.tagSet: BooleanEncoder(),
    univ.Real.tagSet: RealEncoder(),
    useful.GeneralizedTime.tagSet: GeneralizedTimeEncoder(),
    useful.UTCTime.tagSet: UTCTimeEncoder(),
    # Sequence & Set have same tags as SequenceOf & SetOf
    univ.SetOf.tagSet: SetOfEncoder(),
    univ.Sequence.typeId: SequenceEncoder()
})

TYPE_MAP = encoder.TYPE_MAP.copy()

TYPE_MAP.update({
    univ.Boolean.typeId: BooleanEncoder(),
    univ.Real.typeId: RealEncoder(),
    useful.GeneralizedTime.typeId: GeneralizedTimeEncoder(),
    useful.UTCTime.typeId: UTCTimeEncoder(),
    # Sequence & Set have same tags as SequenceOf & SetOf
    univ.Set.typeId: SetEncoder(),
    univ.SetOf.typeId: SetOfEncoder(),
    univ.Sequence.typeId: SequenceEncoder(),
    univ.SequenceOf.typeId: SequenceOfEncoder()
})


class SingleItemEncoder(encoder.SingleItemEncoder):
    fixedDefLengthMode = False
    fixedChunkSize = 1000

    TAG_MAP = TAG_MAP
    TYPE_MAP = TYPE_MAP


class Encoder(encoder.Encoder):
    SINGLE_ITEM_ENCODER = SingleItemEncoder


#: Turns ASN.1 object into CER octet stream.
#:
#: Takes any ASN.1 object (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative)
#: walks all its components recursively and produces a CER octet stream.
#:
#: Parameters
#: ----------
#: value: either a Python or pyasn1 object (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative)
#:     A Python or pyasn1 object to encode. If Python object is given, `asnSpec`
#:     parameter is required to guide the encoding process.
#:
#: Keyword Args
#: ------------
#: asn1Spec:
#:     Optional ASN.1 schema or value object e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
#:
#: Returns
#: -------
#: : :py:class:`bytes`
#:     Given ASN.1 object encoded into BER octet-stream
#:
#: Raises
#: ------
#: ~pyasn1.error.PyAsn1Error
#:     On encoding errors
#:
#: Examples
#: --------
#: Encode Python value into CER with ASN.1 schema
#:
#: .. code-block:: pycon
#:
#:    >>> seq = SequenceOf(componentType=Integer())
#:    >>> encode([1, 2, 3], asn1Spec=seq)
#:    b'0\x80\x02\x01\x01\x02\x01\x02\x02\x01\x03\x00\x00'
#:
#: Encode ASN.1 value object into CER
#:
#: .. code-block:: pycon
#:
#:    >>> seq = SequenceOf(componentType=Integer())
#:    >>> seq.extend([1, 2, 3])
#:    >>> encode(seq)
#:    b'0\x80\x02\x01\x01\x02\x01\x02\x02\x01\x03\x00\x00'
#:
encode = Encoder()

# EncoderFactory queries class instance and builds a map of tags -> encoders

def __getattr__(attr: str):
    if newAttr := {"tagMap": "TAG_MAP", "typeMap": "TYPE_MAP"}.get(attr):
        warnings.warn(f"{attr} is deprecated. Please use {newAttr} instead.", DeprecationWarning)
        return globals()[newAttr]
    raise AttributeError(attr)

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\packaging\markers.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import annotations

import operator
import os
import platform
import sys
from typing import Any, Callable, TypedDict, cast

from ._parser import MarkerAtom, MarkerList, Op, Value, Variable
from ._parser import parse_marker as _parse_marker
from ._tokenizer import ParserSyntaxError
from .specifiers import InvalidSpecifier, Specifier
from .utils import canonicalize_name

__all__ = [
    "InvalidMarker",
    "Marker",
    "UndefinedComparison",
    "UndefinedEnvironmentName",
    "default_environment",
]

Operator = Callable[[str, str], bool]


class InvalidMarker(ValueError):
    """
    An invalid marker was found, users should refer to PEP 508.
    """


class UndefinedComparison(ValueError):
    """
    An invalid operation was attempted on a value that doesn't support it.
    """


class UndefinedEnvironmentName(ValueError):
    """
    A name was attempted to be used that does not exist inside of the
    environment.
    """


class Environment(TypedDict):
    implementation_name: str
    """The implementation's identifier, e.g. ``'cpython'``."""

    implementation_version: str
    """
    The implementation's version, e.g. ``'3.13.0a2'`` for CPython 3.13.0a2, or
    ``'7.3.13'`` for PyPy3.10 v7.3.13.
    """

    os_name: str
    """
    The value of :py:data:`os.name`. The name of the operating system dependent module
    imported, e.g. ``'posix'``.
    """

    platform_machine: str
    """
    Returns the machine type, e.g. ``'i386'``.

    An empty string if the value cannot be determined.
    """

    platform_release: str
    """
    The system's release, e.g. ``'2.2.0'`` or ``'NT'``.

    An empty string if the value cannot be determined.
    """

    platform_system: str
    """
    The system/OS name, e.g. ``'Linux'``, ``'Windows'`` or ``'Java'``.

    An empty string if the value cannot be determined.
    """

    platform_version: str
    """
    The system's release version, e.g. ``'#3 on degas'``.

    An empty string if the value cannot be determined.
    """

    python_full_version: str
    """
    The Python version as string ``'major.minor.patchlevel'``.

    Note that unlike the Python :py:data:`sys.version`, this value will always include
    the patchlevel (it defaults to 0).
    """

    platform_python_implementation: str
    """
    A string identifying the Python implementation, e.g. ``'CPython'``.
    """

    python_version: str
    """The Python version as string ``'major.minor'``."""

    sys_platform: str
    """
    This string contains a platform identifier that can be used to append
    platform-specific components to :py:data:`sys.path`, for instance.

    For Unix systems, except on Linux and AIX, this is the lowercased OS name as
    returned by ``uname -s`` with the first part of the version as returned by
    ``uname -r`` appended, e.g. ``'sunos5'`` or ``'freebsd8'``, at the time when Python
    was built.
    """


def _normalize_extra_values(results: Any) -> Any:
    """
    Normalize extra values.
    """
    if isinstance(results[0], tuple):
        lhs, op, rhs = results[0]
        if isinstance(lhs, Variable) and lhs.value == "extra":
            normalized_extra = canonicalize_name(rhs.value)
            rhs = Value(normalized_extra)
        elif isinstance(rhs, Variable) and rhs.value == "extra":
            normalized_extra = canonicalize_name(lhs.value)
            lhs = Value(normalized_extra)
        results[0] = lhs, op, rhs
    return results


def _format_marker(
    marker: list[str] | MarkerAtom | str, first: bool | None = True
) -> str:
    assert isinstance(marker, (list, tuple, str))

    # Sometimes we have a structure like [[...]] which is a single item list
    # where the single item is itself it's own list. In that case we want skip
    # the rest of this function so that we don't get extraneous () on the
    # outside.
    if (
        isinstance(marker, list)
        and len(marker) == 1
        and isinstance(marker[0], (list, tuple))
    ):
        return _format_marker(marker[0])

    if isinstance(marker, list):
        inner = (_format_marker(m, first=False) for m in marker)
        if first:
            return " ".join(inner)
        else:
            return "(" + " ".join(inner) + ")"
    elif isinstance(marker, tuple):
        return " ".join([m.serialize() for m in marker])
    else:
        return marker


_operators: dict[str, Operator] = {
    "in": lambda lhs, rhs: lhs in rhs,
    "not in": lambda lhs, rhs: lhs not in rhs,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    ">": operator.gt,
}


def _eval_op(lhs: str, op: Op, rhs: str) -> bool:
    try:
        spec = Specifier("".join([op.serialize(), rhs]))
    except InvalidSpecifier:
        pass
    else:
        return spec.contains(lhs, prereleases=True)

    oper: Operator | None = _operators.get(op.serialize())
    if oper is None:
        raise UndefinedComparison(f"Undefined {op!r} on {lhs!r} and {rhs!r}.")

    return oper(lhs, rhs)


def _normalize(*values: str, key: str) -> tuple[str, ...]:
    # PEP 685 – Comparison of extra names for optional distribution dependencies
    # https://peps.python.org/pep-0685/
    # > When comparing extra names, tools MUST normalize the names being
    # > compared using the semantics outlined in PEP 503 for names
    if key == "extra":
        return tuple(canonicalize_name(v) for v in values)

    # other environment markers don't have such standards
    return values


def _evaluate_markers(markers: MarkerList, environment: dict[str, str]) -> bool:
    groups: list[list[bool]] = [[]]

    for marker in markers:
        assert isinstance(marker, (list, tuple, str))

        if isinstance(marker, list):
            groups[-1].append(_evaluate_markers(marker, environment))
        elif isinstance(marker, tuple):
            lhs, op, rhs = marker

            if isinstance(lhs, Variable):
                environment_key = lhs.value
                lhs_value = environment[environment_key]
                rhs_value = rhs.value
            else:
                lhs_value = lhs.value
                environment_key = rhs.value
                rhs_value = environment[environment_key]

            lhs_value, rhs_value = _normalize(lhs_value, rhs_value, key=environment_key)
            groups[-1].append(_eval_op(lhs_value, op, rhs_value))
        else:
            assert marker in ["and", "or"]
            if marker == "or":
                groups.append([])

    return any(all(item) for item in groups)


def format_full_version(info: sys._version_info) -> str:
    version = f"{info.major}.{info.minor}.{info.micro}"
    kind = info.releaselevel
    if kind != "final":
        version += kind[0] + str(info.serial)
    return version


def default_environment() -> Environment:
    iver = format_full_version(sys.implementation.version)
    implementation_name = sys.implementation.name
    return {
        "implementation_name": implementation_name,
        "implementation_version": iver,
        "os_name": os.name,
        "platform_machine": platform.machine(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python_full_version": platform.python_version(),
        "platform_python_implementation": platform.python_implementation(),
        "python_version": ".".join(platform.python_version_tuple()[:2]),
        "sys_platform": sys.platform,
    }


class Marker:
    def __init__(self, marker: str) -> None:
        # Note: We create a Marker object without calling this constructor in
        #       packaging.requirements.Requirement. If any additional logic is
        #       added here, make sure to mirror/adapt Requirement.
        try:
            self._markers = _normalize_extra_values(_parse_marker(marker))
            # The attribute `_markers` can be described in terms of a recursive type:
            # MarkerList = List[Union[Tuple[Node, ...], str, MarkerList]]
            #
            # For example, the following expression:
            # python_version > "3.6" or (python_version == "3.6" and os_name == "unix")
            #
            # is parsed into:
            # [
            #     (<Variable('python_version')>, <Op('>')>, <Value('3.6')>),
            #     'and',
            #     [
            #         (<Variable('python_version')>, <Op('==')>, <Value('3.6')>),
            #         'or',
            #         (<Variable('os_name')>, <Op('==')>, <Value('unix')>)
            #     ]
            # ]
        except ParserSyntaxError as e:
            raise InvalidMarker(str(e)) from e

    def __str__(self) -> str:
        return _format_marker(self._markers)

    def __repr__(self) -> str:
        return f"<Marker('{self}')>"

    def __hash__(self) -> int:
        return hash((self.__class__.__name__, str(self)))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Marker):
            return NotImplemented

        return str(self) == str(other)

    def evaluate(self, environment: dict[str, str] | None = None) -> bool:
        """Evaluate a marker.

        Return the boolean from evaluating the given marker against the
        environment. environment is an optional argument to override all or
        part of the determined environment.

        The environment is determined from the current Python process.
        """
        current_environment = cast("dict[str, str]", default_environment())
        current_environment["extra"] = ""
        if environment is not None:
            current_environment.update(environment)
            # The API used to allow setting extra to None. We need to handle this
            # case for backwards compatibility.
            if current_environment["extra"] is None:
                current_environment["extra"] = ""

        return _evaluate_markers(
            self._markers, _repair_python_full_version(current_environment)
        )


def _repair_python_full_version(env: dict[str, str]) -> dict[str, str]:
    """
    Work around platform.python_version() returning something that is not PEP 440
    compliant for non-tagged Python builds.
    """
    if env["python_full_version"].endswith("+"):
        env["python_full_version"] += "local"
    return env

# === NexusCore/openenv\Lib\site-packages\win32com\makegw\makegwenum.py ===
"""Utility file for generating PyIEnum support.

This is almost a 'template' file.  It simplay contains almost full
C++ source code for PyIEnum* support, and the Python code simply
substitutes the appropriate interface name.

This module is notmally not used directly - the @makegw@ module
automatically calls this.
"""

#
# INTERNAL FUNCTIONS
#
#


def is_interface_enum(enumtype):
    return not (enumtype[0].isupper() and enumtype[2].isupper())


def _write_enumifc_cpp(f, interface):
    enumtype = interface.name[5:]
    if is_interface_enum(enumtype):
        # Assume an interface.
        enum_interface = "I" + enumtype[:-1]
        converter = "PyObject *ob = PyCom_PyObjectFromIUnknown(rgVar[i], IID_{enum_interface}, FALSE);".format(
            **locals()
        )
        arraydeclare = (
            "{enum_interface} **rgVar = new {enum_interface} *[celt];".format(
                **locals()
            )
        )
    else:
        # Enum of a simple structure
        converter = "PyObject *ob = PyCom_PyObjectFrom{enumtype}(&rgVar[i]);".format(
            **locals()
        )
        arraydeclare = "{enumtype} *rgVar = new {enumtype}[celt];".format(**locals())

    f.write(
        """
// ---------------------------------------------------
//
// Interface Implementation

PyIEnum{enumtype}::PyIEnum{enumtype}(IUnknown *pdisp):
    PyIUnknown(pdisp)
{{
    ob_type = &type;
}}

PyIEnum{enumtype}::~PyIEnum{enumtype}()
{{
}}

/* static */ IEnum{enumtype} *PyIEnum{enumtype}::GetI(PyObject *self)
{{
    return (IEnum{enumtype} *)PyIUnknown::GetI(self);
}}

// @pymethod object|PyIEnum{enumtype}|Next|Retrieves a specified number of items in the enumeration sequence.
PyObject *PyIEnum{enumtype}::Next(PyObject *self, PyObject *args)
{{
    long celt = 1;
    // @pyparm int|num|1|Number of items to retrieve.
    if ( !PyArg_ParseTuple(args, "|l:Next", &celt) )
        return NULL;

    IEnum{enumtype} *pIE{enumtype} = GetI(self);
    if ( pIE{enumtype} == NULL )
        return NULL;

    {arraydeclare}
    if ( rgVar == NULL ) {{
        PyErr_SetString(PyExc_MemoryError, "allocating result {enumtype}s");
        return NULL;
    }}

    int i;
/*    for ( i = celt; i--; )
        // *** possibly init each structure element???
*/

    ULONG celtFetched = 0;
    PY_INTERFACE_PRECALL;
    HRESULT hr = pIE{enumtype}->Next(celt, rgVar, &celtFetched);
    PY_INTERFACE_POSTCALL;
    if (  HRESULT_CODE(hr) != ERROR_NO_MORE_ITEMS && FAILED(hr) )
    {{
        delete [] rgVar;
        return PyCom_BuildPyException(hr,pIE{enumtype}, IID_IE{enumtype});
    }}

    PyObject *result = PyTuple_New(celtFetched);
    if ( result != NULL )
    {{
        for ( i = celtFetched; i--; )
        {{
            {converter}
            if ( ob == NULL )
            {{
                Py_DECREF(result);
                result = NULL;
                break;
            }}
            PyTuple_SET_ITEM(result, i, ob);
        }}
    }}

/*    for ( i = celtFetched; i--; )
        // *** possibly cleanup each structure element???
*/
    delete [] rgVar;
    return result;
}}

// @pymethod |PyIEnum{enumtype}|Skip|Skips over the next specified elementes.
PyObject *PyIEnum{enumtype}::Skip(PyObject *self, PyObject *args)
{{
    long celt;
    if ( !PyArg_ParseTuple(args, "l:Skip", &celt) )
        return NULL;

    IEnum{enumtype} *pIE{enumtype} = GetI(self);
    if ( pIE{enumtype} == NULL )
        return NULL;

    PY_INTERFACE_PRECALL;
    HRESULT hr = pIE{enumtype}->Skip(celt);
    PY_INTERFACE_POSTCALL;
    if ( FAILED(hr) )
        return PyCom_BuildPyException(hr, pIE{enumtype}, IID_IE{enumtype});

    Py_INCREF(Py_None);
    return Py_None;
}}

// @pymethod |PyIEnum{enumtype}|Reset|Resets the enumeration sequence to the beginning.
PyObject *PyIEnum{enumtype}::Reset(PyObject *self, PyObject *args)
{{
    if ( !PyArg_ParseTuple(args, ":Reset") )
        return NULL;

    IEnum{enumtype} *pIE{enumtype} = GetI(self);
    if ( pIE{enumtype} == NULL )
        return NULL;

    PY_INTERFACE_PRECALL;
    HRESULT hr = pIE{enumtype}->Reset();
    PY_INTERFACE_POSTCALL;
    if ( FAILED(hr) )
        return PyCom_BuildPyException(hr, pIE{enumtype}, IID_IE{enumtype});

    Py_INCREF(Py_None);
    return Py_None;
}}

// @pymethod <o PyIEnum{enumtype}>|PyIEnum{enumtype}|Clone|Creates another enumerator that contains the same enumeration state as the current one
PyObject *PyIEnum{enumtype}::Clone(PyObject *self, PyObject *args)
{{
    if ( !PyArg_ParseTuple(args, ":Clone") )
        return NULL;

    IEnum{enumtype} *pIE{enumtype} = GetI(self);
    if ( pIE{enumtype} == NULL )
        return NULL;

    IEnum{enumtype} *pClone;
    PY_INTERFACE_PRECALL;
    HRESULT hr = pIE{enumtype}->Clone(&pClone);
    PY_INTERFACE_POSTCALL;
    if ( FAILED(hr) )
        return PyCom_BuildPyException(hr, pIE{enumtype}, IID_IE{enumtype});

    return PyCom_PyObjectFromIUnknown(pClone, IID_IEnum{enumtype}, FALSE);
}}

// @object PyIEnum{enumtype}|A Python interface to IEnum{enumtype}
static struct PyMethodDef PyIEnum{enumtype}_methods[] =
{{
    {{ "Next", PyIEnum{enumtype}::Next, 1 }},   // @pymeth Next|Retrieves a specified number of items in the enumeration sequence.
    {{ "Skip", PyIEnum{enumtype}::Skip, 1 }},   // @pymeth Skip|Skips over the next specified elementes.
    {{ "Reset", PyIEnum{enumtype}::Reset, 1 }}, // @pymeth Reset|Resets the enumeration sequence to the beginning.
    {{ "Clone", PyIEnum{enumtype}::Clone, 1 }}, // @pymeth Clone|Creates another enumerator that contains the same enumeration state as the current one.
    {{ NULL }}
}};

PyComEnumTypeObject PyIEnum{enumtype}::type("PyIEnum{enumtype}",
        &PyIUnknown::type,
        sizeof(PyIEnum{enumtype}),
        PyIEnum{enumtype}_methods,
        GET_PYCOM_CTOR(PyIEnum{enumtype}));
""".format(**locals())
    )


def _write_enumgw_cpp(f, interface):
    enumtype = interface.name[5:]
    if is_interface_enum(enumtype):
        # Assume an interface.
        enum_interface = "I" + enumtype[:-1]
        converter = "if ( !PyCom_InterfaceFromPyObject(ob, IID_{enum_interface}, (void **)&rgVar[i], FALSE) )".format(
            **locals()
        )
        argdeclare = "{enum_interface} __RPC_FAR * __RPC_FAR *rgVar".format(**locals())
    else:
        argdeclare = "{enumtype} __RPC_FAR *rgVar".format(**locals())
        converter = "if ( !PyCom_PyObjectAs{enumtype}(ob, &rgVar[i]) )".format(
            **locals()
        )
    f.write(
        """
// ---------------------------------------------------
//
// Gateway Implementation

// Std delegation
STDMETHODIMP_(ULONG) PyGEnum{enumtype}::AddRef(void) {{return PyGatewayBase::AddRef();}}
STDMETHODIMP_(ULONG) PyGEnum{enumtype}::Release(void) {{return PyGatewayBase::Release();}}
STDMETHODIMP PyGEnum{enumtype}::QueryInterface(REFIID iid, void ** obj) {{return PyGatewayBase::QueryInterface(iid, obj);}}
STDMETHODIMP PyGEnum{enumtype}::GetTypeInfoCount(UINT FAR* pctInfo) {{return PyGatewayBase::GetTypeInfoCount(pctInfo);}}
STDMETHODIMP PyGEnum{enumtype}::GetTypeInfo(UINT itinfo, LCID lcid, ITypeInfo FAR* FAR* pptInfo) {{return PyGatewayBase::GetTypeInfo(itinfo, lcid, pptInfo);}}
STDMETHODIMP PyGEnum{enumtype}::GetIDsOfNames(REFIID refiid, OLECHAR FAR* FAR* rgszNames, UINT cNames, LCID lcid, DISPID FAR* rgdispid) {{return PyGatewayBase::GetIDsOfNames( refiid, rgszNames, cNames, lcid, rgdispid);}}
STDMETHODIMP PyGEnum{enumtype}::Invoke(DISPID dispid, REFIID riid, LCID lcid, WORD wFlags, DISPPARAMS FAR* params, VARIANT FAR* pVarResult, EXCEPINFO FAR* pexcepinfo, UINT FAR* puArgErr) {{return PyGatewayBase::Invoke( dispid, riid, lcid, wFlags, params, pVarResult, pexcepinfo, puArgErr);}}

STDMETHODIMP PyGEnum{enumtype}::Next(
            /* [in] */ ULONG celt,
            /* [length_is][size_is][out] */ {argdeclare},
            /* [out] */ ULONG __RPC_FAR *pCeltFetched)
{{
    PY_GATEWAY_METHOD;
    PyObject *result;
    HRESULT hr = InvokeViaPolicy("Next", &result, "i", celt);
    if ( FAILED(hr) )
        return hr;

    if ( !PySequence_Check(result) )
        goto error;
    int len;
    len = PyObject_Length(result);
    if ( len == -1 )
        goto error;
    if ( len > (int)celt)
        len = celt;

    if ( pCeltFetched )
        *pCeltFetched = len;

    int i;
    for ( i = 0; i < len; ++i )
    {{
        PyObject *ob = PySequence_GetItem(result, i);
        if ( ob == NULL )
            goto error;

        {converter}
        {{
            Py_DECREF(result);
            return PyCom_SetCOMErrorFromPyException(IID_IEnum{enumtype});
        }}
    }}

    Py_DECREF(result);

    return len < (int)celt ? S_FALSE : S_OK;

  error:
    PyErr_Clear(); // just in case
    Py_DECREF(result);
    return PyCom_HandleIEnumNoSequence(IID_IEnum{enumtype});
}}

STDMETHODIMP PyGEnum{enumtype}::Skip(
            /* [in] */ ULONG celt)
{{
    PY_GATEWAY_METHOD;
    return InvokeViaPolicy("Skip", NULL, "i", celt);
}}

STDMETHODIMP PyGEnum{enumtype}::Reset(void)
{{
    PY_GATEWAY_METHOD;
    return InvokeViaPolicy("Reset");
}}

STDMETHODIMP PyGEnum{enumtype}::Clone(
            /* [out] */ IEnum{enumtype} __RPC_FAR *__RPC_FAR *ppEnum)
{{
    PY_GATEWAY_METHOD;
    PyObject * result;
    HRESULT hr = InvokeViaPolicy("Clone", &result);
    if ( FAILED(hr) )
        return hr;

    /*
    ** Make sure we have the right kind of object: we should have some kind
    ** of IUnknown subclass wrapped into a PyIUnknown instance.
    */
    if ( !PyIBase::is_object(result, &PyIUnknown::type) )
    {{
        /* the wrong kind of object was returned to us */
        Py_DECREF(result);
        return PyCom_SetCOMErrorFromSimple(E_FAIL, IID_IEnum{enumtype});
    }}

    /*
    ** Get the IUnknown out of the thing. note that the Python ob maintains
    ** a reference, so we don't have to explicitly AddRef() here.
    */
    IUnknown *punk = ((PyIUnknown *)result)->m_obj;
    if ( !punk )
    {{
        /* damn. the object was released. */
        Py_DECREF(result);
        return PyCom_SetCOMErrorFromSimple(E_FAIL, IID_IEnum{enumtype});
    }}

    /*
    ** Get the interface we want. note it is returned with a refcount.
    ** This QI is actually going to instantiate a PyGEnum{enumtype}.
    */
    hr = punk->QueryInterface(IID_IEnum{enumtype}, (LPVOID *)ppEnum);

    /* done with the result; this DECREF is also for <punk> */
    Py_DECREF(result);

    return PyCom_CheckIEnumNextResult(hr, IID_IEnum{enumtype});
}}
""".format(**locals())
    )

# === NexusCore/openenv\Lib\site-packages\html2text\cli.py ===
import argparse
import sys

from . import HTML2Text, __version__, config


def main() -> None:
    baseurl = ""

    class bcolors:
        HEADER = "\033[95m"
        OKBLUE = "\033[94m"
        OKGREEN = "\033[92m"
        WARNING = "\033[93m"
        FAIL = "\033[91m"
        ENDC = "\033[0m"
        BOLD = "\033[1m"
        UNDERLINE = "\033[4m"

    p = argparse.ArgumentParser()
    p.add_argument(
        "--default-image-alt",
        dest="default_image_alt",
        default=config.DEFAULT_IMAGE_ALT,
        help="The default alt string for images with missing ones",
    )
    p.add_argument(
        "--pad-tables",
        dest="pad_tables",
        action="store_true",
        default=config.PAD_TABLES,
        help="pad the cells to equal column width in tables",
    )
    p.add_argument(
        "--no-wrap-links",
        dest="wrap_links",
        action="store_false",
        default=config.WRAP_LINKS,
        help="don't wrap links during conversion",
    )
    p.add_argument(
        "--wrap-list-items",
        dest="wrap_list_items",
        action="store_true",
        default=config.WRAP_LIST_ITEMS,
        help="wrap list items during conversion",
    )
    p.add_argument(
        "--wrap-tables",
        dest="wrap_tables",
        action="store_true",
        default=config.WRAP_TABLES,
        help="wrap tables",
    )
    p.add_argument(
        "--ignore-emphasis",
        dest="ignore_emphasis",
        action="store_true",
        default=config.IGNORE_EMPHASIS,
        help="don't include any formatting for emphasis",
    )
    p.add_argument(
        "--reference-links",
        dest="inline_links",
        action="store_false",
        default=config.INLINE_LINKS,
        help="use reference style links instead of inline links",
    )
    p.add_argument(
        "--ignore-links",
        dest="ignore_links",
        action="store_true",
        default=config.IGNORE_ANCHORS,
        help="don't include any formatting for links",
    )
    p.add_argument(
        "--ignore-mailto-links",
        action="store_true",
        dest="ignore_mailto_links",
        default=config.IGNORE_MAILTO_LINKS,
        help="don't include mailto: links",
    )
    p.add_argument(
        "--protect-links",
        dest="protect_links",
        action="store_true",
        default=config.PROTECT_LINKS,
        help="protect links from line breaks surrounding them with angle brackets",
    )
    p.add_argument(
        "--ignore-images",
        dest="ignore_images",
        action="store_true",
        default=config.IGNORE_IMAGES,
        help="don't include any formatting for images",
    )
    p.add_argument(
        "--images-as-html",
        dest="images_as_html",
        action="store_true",
        default=config.IMAGES_AS_HTML,
        help=(
            "Always write image tags as raw html; preserves `height`, `width` and "
            "`alt` if possible."
        ),
    )
    p.add_argument(
        "--images-to-alt",
        dest="images_to_alt",
        action="store_true",
        default=config.IMAGES_TO_ALT,
        help="Discard image data, only keep alt text",
    )
    p.add_argument(
        "--images-with-size",
        dest="images_with_size",
        action="store_true",
        default=config.IMAGES_WITH_SIZE,
        help=(
            "Write image tags with height and width attrs as raw html to retain "
            "dimensions"
        ),
    )
    p.add_argument(
        "-g",
        "--google-doc",
        action="store_true",
        dest="google_doc",
        default=False,
        help="convert an html-exported Google Document",
    )
    p.add_argument(
        "-d",
        "--dash-unordered-list",
        action="store_true",
        dest="ul_style_dash",
        default=False,
        help="use a dash rather than a star for unordered list items",
    )
    p.add_argument(
        "-e",
        "--asterisk-emphasis",
        action="store_true",
        dest="em_style_asterisk",
        default=False,
        help="use an asterisk rather than an underscore for emphasized text",
    )
    p.add_argument(
        "-b",
        "--body-width",
        dest="body_width",
        type=int,
        default=config.BODY_WIDTH,
        help="number of characters per output line, 0 for no wrap",
    )
    p.add_argument(
        "-i",
        "--google-list-indent",
        dest="list_indent",
        type=int,
        default=config.GOOGLE_LIST_INDENT,
        help="number of pixels Google indents nested lists",
    )
    p.add_argument(
        "-s",
        "--hide-strikethrough",
        action="store_true",
        dest="hide_strikethrough",
        default=False,
        help="hide strike-through text. only relevant when -g is " "specified as well",
    )
    p.add_argument(
        "--escape-all",
        action="store_true",
        dest="escape_snob",
        default=False,
        help=(
            "Escape all special characters.  Output is less readable, but avoids "
            "corner case formatting issues."
        ),
    )
    p.add_argument(
        "--bypass-tables",
        action="store_true",
        dest="bypass_tables",
        default=config.BYPASS_TABLES,
        help="Format tables in HTML rather than Markdown syntax.",
    )
    p.add_argument(
        "--ignore-tables",
        action="store_true",
        dest="ignore_tables",
        default=config.IGNORE_TABLES,
        help="Ignore table-related tags (table, th, td, tr) " "while keeping rows.",
    )
    p.add_argument(
        "--single-line-break",
        action="store_true",
        dest="single_line_break",
        default=config.SINGLE_LINE_BREAK,
        help=(
            "Use a single line break after a block element rather than two line "
            "breaks. NOTE: Requires --body-width=0"
        ),
    )
    p.add_argument(
        "--unicode-snob",
        action="store_true",
        dest="unicode_snob",
        default=config.UNICODE_SNOB,
        help="Use unicode throughout document",
    )
    p.add_argument(
        "--no-automatic-links",
        action="store_false",
        dest="use_automatic_links",
        default=config.USE_AUTOMATIC_LINKS,
        help="Do not use automatic links wherever applicable",
    )
    p.add_argument(
        "--no-skip-internal-links",
        action="store_false",
        dest="skip_internal_links",
        default=config.SKIP_INTERNAL_LINKS,
        help="Do not skip internal links",
    )
    p.add_argument(
        "--links-after-para",
        action="store_true",
        dest="links_each_paragraph",
        default=config.LINKS_EACH_PARAGRAPH,
        help="Put links after each paragraph instead of document",
    )
    p.add_argument(
        "--mark-code",
        action="store_true",
        dest="mark_code",
        default=config.MARK_CODE,
        help="Mark program code blocks with [code]...[/code]",
    )
    p.add_argument(
        "--decode-errors",
        dest="decode_errors",
        default=config.DECODE_ERRORS,
        help=(
            "What to do in case of decode errors.'ignore', 'strict' and 'replace' are "
            "acceptable values"
        ),
    )
    p.add_argument(
        "--open-quote",
        dest="open_quote",
        default=config.OPEN_QUOTE,
        help="The character used to open quotes",
    )
    p.add_argument(
        "--close-quote",
        dest="close_quote",
        default=config.CLOSE_QUOTE,
        help="The character used to close quotes",
    )
    p.add_argument(
        "--version", action="version", version=".".join(map(str, __version__))
    )
    p.add_argument("filename", nargs="?")
    p.add_argument("encoding", nargs="?", default="utf-8")
    p.add_argument(
        "--include-sup-sub",
        dest="include_sup_sub",
        action="store_true",
        default=config.INCLUDE_SUP_SUB,
        help="Include the sup and sub tags",
    )
    args = p.parse_args()

    if args.filename and args.filename != "-":
        with open(args.filename, "rb") as fp:
            data = fp.read()
    else:
        data = sys.stdin.buffer.read()

    try:
        html = data.decode(args.encoding, args.decode_errors)
    except UnicodeDecodeError as err:
        warning = bcolors.WARNING + "Warning:" + bcolors.ENDC
        warning += " Use the " + bcolors.OKGREEN
        warning += "--decode-errors=ignore" + bcolors.ENDC + " flag."
        print(warning)
        raise err

    h = HTML2Text(baseurl=baseurl)
    # handle options
    if args.ul_style_dash:
        h.ul_item_mark = "-"
    if args.em_style_asterisk:
        h.emphasis_mark = "*"
        h.strong_mark = "__"

    h.body_width = args.body_width
    h.google_list_indent = args.list_indent
    h.ignore_emphasis = args.ignore_emphasis
    h.ignore_links = args.ignore_links
    h.ignore_mailto_links = args.ignore_mailto_links
    h.protect_links = args.protect_links
    h.ignore_images = args.ignore_images
    h.images_as_html = args.images_as_html
    h.images_to_alt = args.images_to_alt
    h.images_with_size = args.images_with_size
    h.google_doc = args.google_doc
    h.hide_strikethrough = args.hide_strikethrough
    h.escape_snob = args.escape_snob
    h.bypass_tables = args.bypass_tables
    h.ignore_tables = args.ignore_tables
    h.single_line_break = args.single_line_break
    h.inline_links = args.inline_links
    h.unicode_snob = args.unicode_snob
    h.use_automatic_links = args.use_automatic_links
    h.skip_internal_links = args.skip_internal_links
    h.links_each_paragraph = args.links_each_paragraph
    h.mark_code = args.mark_code
    h.wrap_links = args.wrap_links
    h.wrap_list_items = args.wrap_list_items
    h.wrap_tables = args.wrap_tables
    h.pad_tables = args.pad_tables
    h.default_image_alt = args.default_image_alt
    h.open_quote = args.open_quote
    h.close_quote = args.close_quote
    h.include_sup_sub = args.include_sup_sub

    sys.stdout.write(h.handle(html))

# === NexusCore/openenv\Lib\site-packages\IPython\core\magics\ast_mod.py ===
"""
This module contains utility function and classes to inject simple ast
transformations based on code strings into IPython. While it is already possible
with ast-transformers it is not easy to directly manipulate ast.


IPython has pre-code and post-code hooks, but are ran from within the IPython
machinery so may be inappropriate, for example for performance measurement.

This module give you tools to simplify this, and expose 2 classes:

- `ReplaceCodeTransformer` which is a simple ast transformer based on code
  template,

and for advance case:

- `Mangler` which is a simple ast transformer that mangle names in the ast.


Example, let's try to make a simple version of the ``timeit`` magic, that run a
code snippet 10 times and print the average time taken.

Basically we want to run :

.. code-block:: python

    from time import perf_counter
    now = perf_counter()
    for i in range(10):
        __code__ # our code
    print(f"Time taken: {(perf_counter() - now)/10}")
    __ret__ # the result of the last statement

Where ``__code__`` is the code snippet we want to run, and ``__ret__`` is the
result, so that if we for example run `dataframe.head()` IPython still display
the head of dataframe instead of nothing.

Here is a complete example of a file `timit2.py` that define such a magic:

.. code-block:: python

    from IPython.core.magic import (
        Magics,
        magics_class,
        line_cell_magic,
    )
    from IPython.core.magics.ast_mod import ReplaceCodeTransformer
    from textwrap import dedent
    import ast

    template = template = dedent('''
        from time import perf_counter
        now = perf_counter()
        for i in range(10):
            __code__
        print(f"Time taken: {(perf_counter() - now)/10}")
        __ret__
    '''
    )


    @magics_class
    class AstM(Magics):
        @line_cell_magic
        def t2(self, line, cell):
            transformer = ReplaceCodeTransformer.from_string(template)
            transformer.debug = True
            transformer.mangler.debug = True
            new_code = transformer.visit(ast.parse(cell))
            return exec(compile(new_code, "<ast>", "exec"))


    def load_ipython_extension(ip):
        ip.register_magics(AstM)



.. code-block:: python

    In [1]: %load_ext timit2

    In [2]: %%t2
       ...: import time
       ...: time.sleep(0.05)
       ...:
       ...:
    Time taken: 0.05435649999999441


If you wish to ran all the code enter in IPython in an ast transformer, you can
do so as well:

.. code-block:: python

    In [1]: from IPython.core.magics.ast_mod import ReplaceCodeTransformer
       ...:
       ...: template = '''
       ...: from time import perf_counter
       ...: now = perf_counter()
       ...: __code__
       ...: print(f"Code ran in {perf_counter()-now}")
       ...: __ret__'''
       ...:
       ...: get_ipython().ast_transformers.append(ReplaceCodeTransformer.from_string(template))

    In [2]: 1+1
    Code ran in 3.40410006174352e-05
    Out[2]: 2



Hygiene and Mangling
--------------------

The ast transformer above is not hygienic, it may not work if the user code use
the same variable names as the ones used in the template. For example.

To help with this by default the `ReplaceCodeTransformer` will mangle all names
staring with 3 underscores. This is a simple heuristic that should work in most
case, but can be cumbersome in some case. We provide a `Mangler` class that can
be overridden to change the mangling heuristic, or simply use the `mangle_all`
utility function. It will _try_ to mangle all names (except `__ret__` and
`__code__`), but this include builtins (``print``, ``range``, ``type``) and
replace those by invalid identifiers py prepending ``mangle-``:
``mangle-print``, ``mangle-range``, ``mangle-type`` etc. This is not a problem
as currently Python AST support invalid identifiers, but it may not be the case
in the future.

You can set `ReplaceCodeTransformer.debug=True` and
`ReplaceCodeTransformer.mangler.debug=True` to see the code after mangling and
transforming:

.. code-block:: python


    In [1]: from IPython.core.magics.ast_mod import ReplaceCodeTransformer, mangle_all
       ...:
       ...: template = '''
       ...: from builtins import type, print
       ...: from time import perf_counter
       ...: now = perf_counter()
       ...: __code__
       ...: print(f"Code ran in {perf_counter()-now}")
       ...: __ret__'''
       ...:
       ...: transformer = ReplaceCodeTransformer.from_string(template, mangling_predicate=mangle_all)


    In [2]: transformer.debug = True
       ...: transformer.mangler.debug = True
       ...: get_ipython().ast_transformers.append(transformer)

    In [3]: 1+1
    Mangling Alias mangle-type
    Mangling Alias mangle-print
    Mangling Alias mangle-perf_counter
    Mangling now
    Mangling perf_counter
    Not mangling __code__
    Mangling print
    Mangling perf_counter
    Mangling now
    Not mangling __ret__
    ---- Transformed code ----
    from builtins import type as mangle-type, print as mangle-print
    from time import perf_counter as mangle-perf_counter
    mangle-now = mangle-perf_counter()
    ret-tmp = 1 + 1
    mangle-print(f'Code ran in {mangle-perf_counter() - mangle-now}')
    ret-tmp
    ---- ---------------- ----
    Code ran in 0.00013654199938173406
    Out[3]: 2


"""

__skip_doctest__ = True


from ast import (
    NodeTransformer,
    Store,
    Load,
    Name,
    Expr,
    Assign,
    Module,
    Import,
    ImportFrom,
)
import ast
import copy

from typing import Dict, Optional, Union


mangle_all = lambda name: False if name in ("__ret__", "__code__") else True


class Mangler(NodeTransformer):
    """
    Mangle given names in and ast tree to make sure they do not conflict with
    user code.
    """

    enabled: bool = True
    debug: bool = False

    def log(self, *args, **kwargs):
        if self.debug:
            print(*args, **kwargs)

    def __init__(self, predicate=None):
        if predicate is None:
            predicate = lambda name: name.startswith("___")
        self.predicate = predicate

    def visit_Name(self, node):
        if self.predicate(node.id):
            self.log("Mangling", node.id)
            # Once in the ast we do not need
            # names to be valid identifiers.
            node.id = "mangle-" + node.id
        else:
            self.log("Not mangling", node.id)
        return node

    def visit_FunctionDef(self, node):
        if self.predicate(node.name):
            self.log("Mangling", node.name)
            node.name = "mangle-" + node.name
        else:
            self.log("Not mangling", node.name)

        for arg in node.args.args:
            if self.predicate(arg.arg):
                self.log("Mangling function arg", arg.arg)
                arg.arg = "mangle-" + arg.arg
            else:
                self.log("Not mangling function arg", arg.arg)
        return self.generic_visit(node)

    def visit_ImportFrom(self, node: ImportFrom):
        return self._visit_Import_and_ImportFrom(node)

    def visit_Import(self, node: Import):
        return self._visit_Import_and_ImportFrom(node)

    def _visit_Import_and_ImportFrom(self, node: Union[Import, ImportFrom]):
        for alias in node.names:
            asname = alias.name if alias.asname is None else alias.asname
            if self.predicate(asname):
                new_name: str = "mangle-" + asname
                self.log("Mangling Alias", new_name)
                alias.asname = new_name
            else:
                self.log("Not mangling Alias", alias.asname)
        return node


class ReplaceCodeTransformer(NodeTransformer):
    enabled: bool = True
    debug: bool = False
    mangler: Mangler

    def __init__(
        self, template: Module, mapping: Optional[Dict] = None, mangling_predicate=None
    ):
        assert isinstance(mapping, (dict, type(None)))
        assert isinstance(mangling_predicate, (type(None), type(lambda: None)))
        assert isinstance(template, ast.Module)
        self.template = template
        self.mangler = Mangler(predicate=mangling_predicate)
        if mapping is None:
            mapping = {}
        self.mapping = mapping

    @classmethod
    def from_string(
        cls, template: str, mapping: Optional[Dict] = None, mangling_predicate=None
    ):
        return cls(
            ast.parse(template), mapping=mapping, mangling_predicate=mangling_predicate
        )

    def visit_Module(self, code):
        if not self.enabled:
            return code
        # if not isinstance(code, ast.Module):
        # recursively called...
        #    return generic_visit(self, code)
        last = code.body[-1]
        if isinstance(last, Expr):
            code.body.pop()
            code.body.append(Assign([Name("ret-tmp", ctx=Store())], value=last.value))
            ast.fix_missing_locations(code)
            ret = Expr(value=Name("ret-tmp", ctx=Load()))
            ret = ast.fix_missing_locations(ret)
            self.mapping["__ret__"] = ret
        else:
            self.mapping["__ret__"] = ast.parse("None").body[0]
        self.mapping["__code__"] = code.body
        tpl = ast.fix_missing_locations(self.template)

        tx = copy.deepcopy(tpl)
        tx = self.mangler.visit(tx)
        node = self.generic_visit(tx)
        node_2 = ast.fix_missing_locations(node)
        if self.debug:
            print("---- Transformed code ----")
            print(ast.unparse(node_2))
            print("---- ---------------- ----")
        return node_2

    # this does not work as the name might be in a list and one might want to extend the list.
    # def visit_Name(self, name):
    #     if name.id in self.mapping and name.id == "__ret__":
    #         print(name, "in mapping")
    #         if isinstance(name.ctx, ast.Store):
    #             return Name("tmp", ctx=Store())
    #         else:
    #             return copy.deepcopy(self.mapping[name.id])
    #     return name

    def visit_Expr(self, expr):
        if isinstance(expr.value, Name) and expr.value.id in self.mapping:
            if self.mapping[expr.value.id] is not None:
                return copy.deepcopy(self.mapping[expr.value.id])
        return self.generic_visit(expr)

# === NexusCore/openenv\Lib\site-packages\nltk\translate\ribes_score.py ===
# Natural Language Toolkit: RIBES Score
#
# Copyright (C) 2001-2024 NLTK Project
# Contributors: Katsuhito Sudoh, Liling Tan, Kasramvd, J.F.Sebastian
#               Mark Byers, ekhumoro, P. Ortiz
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
""" RIBES score implementation """

import math
from itertools import islice

from nltk.util import choose, ngrams


def sentence_ribes(references, hypothesis, alpha=0.25, beta=0.10):
    """
    The RIBES (Rank-based Intuitive Bilingual Evaluation Score) from
    Hideki Isozaki, Tsutomu Hirao, Kevin Duh, Katsuhito Sudoh and
    Hajime Tsukada. 2010. "Automatic Evaluation of Translation Quality for
    Distant Language Pairs". In Proceedings of EMNLP.
    https://www.aclweb.org/anthology/D/D10/D10-1092.pdf

    The generic RIBES scores used in shared task, e.g. Workshop for
    Asian Translation (WAT) uses the following RIBES calculations:

        RIBES = kendall_tau * (alpha**p1) * (beta**bp)

    Please note that this re-implementation differs from the official
    RIBES implementation and though it emulates the results as describe
    in the original paper, there are further optimization implemented
    in the official RIBES script.

    Users are encouraged to use the official RIBES script instead of this
    implementation when evaluating your machine translation system. Refer
    to https://www.kecl.ntt.co.jp/icl/lirg/ribes/ for the official script.

    :param references: a list of reference sentences
    :type references: list(list(str))
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    :param alpha: hyperparameter used as a prior for the unigram precision.
    :type alpha: float
    :param beta: hyperparameter used as a prior for the brevity penalty.
    :type beta: float
    :return: The best ribes score from one of the references.
    :rtype: float
    """
    best_ribes = -1.0
    # Calculates RIBES for each reference and returns the best score.
    for reference in references:
        # Collects the *worder* from the ranked correlation alignments.
        worder = word_rank_alignment(reference, hypothesis)
        nkt = kendall_tau(worder)

        # Calculates the brevity penalty
        bp = min(1.0, math.exp(1.0 - len(reference) / len(hypothesis)))

        # Calculates the unigram precision, *p1*
        p1 = len(worder) / len(hypothesis)

        _ribes = nkt * (p1**alpha) * (bp**beta)

        if _ribes > best_ribes:  # Keeps the best score.
            best_ribes = _ribes

    return best_ribes


def corpus_ribes(list_of_references, hypotheses, alpha=0.25, beta=0.10):
    """
    This function "calculates RIBES for a system output (hypothesis) with
    multiple references, and returns "best" score among multi-references and
    individual scores. The scores are corpus-wise, i.e., averaged by the number
    of sentences." (c.f. RIBES version 1.03.1 code).

    Different from BLEU's micro-average precision, RIBES calculates the
    macro-average precision by averaging the best RIBES score for each pair of
    hypothesis and its corresponding references

    >>> hyp1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
    ...         'ensures', 'that', 'the', 'military', 'always',
    ...         'obeys', 'the', 'commands', 'of', 'the', 'party']
    >>> ref1a = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
    ...          'ensures', 'that', 'the', 'military', 'will', 'forever',
    ...          'heed', 'Party', 'commands']
    >>> ref1b = ['It', 'is', 'the', 'guiding', 'principle', 'which',
    ...          'guarantees', 'the', 'military', 'forces', 'always',
    ...          'being', 'under', 'the', 'command', 'of', 'the', 'Party']
    >>> ref1c = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
    ...          'army', 'always', 'to', 'heed', 'the', 'directions',
    ...          'of', 'the', 'party']

    >>> hyp2 = ['he', 'read', 'the', 'book', 'because', 'he', 'was',
    ...         'interested', 'in', 'world', 'history']
    >>> ref2a = ['he', 'was', 'interested', 'in', 'world', 'history',
    ...          'because', 'he', 'read', 'the', 'book']

    >>> list_of_references = [[ref1a, ref1b, ref1c], [ref2a]]
    >>> hypotheses = [hyp1, hyp2]
    >>> round(corpus_ribes(list_of_references, hypotheses),4)
    0.3597

    :param references: a corpus of lists of reference sentences, w.r.t. hypotheses
    :type references: list(list(list(str)))
    :param hypotheses: a list of hypothesis sentences
    :type hypotheses: list(list(str))
    :param alpha: hyperparameter used as a prior for the unigram precision.
    :type alpha: float
    :param beta: hyperparameter used as a prior for the brevity penalty.
    :type beta: float
    :return: The best ribes score from one of the references.
    :rtype: float
    """
    corpus_best_ribes = 0.0
    # Iterate through each hypothesis and their corresponding references.
    for references, hypothesis in zip(list_of_references, hypotheses):
        corpus_best_ribes += sentence_ribes(references, hypothesis, alpha, beta)
    return corpus_best_ribes / len(hypotheses)


def position_of_ngram(ngram, sentence):
    """
    This function returns the position of the first instance of the ngram
    appearing in a sentence.

    Note that one could also use string as follows but the code is a little
    convoluted with type casting back and forth:

        char_pos = ' '.join(sent)[:' '.join(sent).index(' '.join(ngram))]
        word_pos = char_pos.count(' ')

    Another way to conceive this is:

        return next(i for i, ng in enumerate(ngrams(sentence, len(ngram)))
                    if ng == ngram)

    :param ngram: The ngram that needs to be searched
    :type ngram: tuple
    :param sentence: The list of tokens to search from.
    :type sentence: list(str)
    """
    # Iterates through the ngrams in sentence.
    for i, sublist in enumerate(ngrams(sentence, len(ngram))):
        # Returns the index of the word when ngram matches.
        if ngram == sublist:
            return i


def word_rank_alignment(reference, hypothesis, character_based=False):
    """
    This is the word rank alignment algorithm described in the paper to produce
    the *worder* list, i.e. a list of word indices of the hypothesis word orders
    w.r.t. the list of reference words.

    Below is (H0, R0) example from the Isozaki et al. 2010 paper,
    note the examples are indexed from 1 but the results here are indexed from 0:

        >>> ref = str('he was interested in world history because he '
        ... 'read the book').split()
        >>> hyp = str('he read the book because he was interested in world '
        ... 'history').split()
        >>> word_rank_alignment(ref, hyp)
        [7, 8, 9, 10, 6, 0, 1, 2, 3, 4, 5]

    The (H1, R1) example from the paper, note the 0th index:

        >>> ref = 'John hit Bob yesterday'.split()
        >>> hyp = 'Bob hit John yesterday'.split()
        >>> word_rank_alignment(ref, hyp)
        [2, 1, 0, 3]

    Here is the (H2, R2) example from the paper, note the 0th index here too:

        >>> ref = 'the boy read the book'.split()
        >>> hyp = 'the book was read by the boy'.split()
        >>> word_rank_alignment(ref, hyp)
        [3, 4, 2, 0, 1]

    :param reference: a reference sentence
    :type reference: list(str)
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    """
    worder = []
    hyp_len = len(hypothesis)
    # Stores a list of possible ngrams from the reference sentence.
    # This is used for matching context window later in the algorithm.
    ref_ngrams = []
    hyp_ngrams = []
    for n in range(1, len(reference) + 1):
        for ng in ngrams(reference, n):
            ref_ngrams.append(ng)
        for ng in ngrams(hypothesis, n):
            hyp_ngrams.append(ng)
    for i, h_word in enumerate(hypothesis):
        # If word is not in the reference, continue.
        if h_word not in reference:
            continue
        # If we can determine one-to-one word correspondence for unigrams that
        # only appear once in both the reference and hypothesis.
        elif hypothesis.count(h_word) == reference.count(h_word) == 1:
            worder.append(reference.index(h_word))
        else:
            max_window_size = max(i, hyp_len - i + 1)
            for window in range(1, max_window_size):
                if i + window < hyp_len:  # If searching the right context is possible.
                    # Retrieve the right context window.
                    right_context_ngram = tuple(islice(hypothesis, i, i + window + 1))
                    num_times_in_ref = ref_ngrams.count(right_context_ngram)
                    num_times_in_hyp = hyp_ngrams.count(right_context_ngram)
                    # If ngram appears only once in both ref and hyp.
                    if num_times_in_ref == num_times_in_hyp == 1:
                        # Find the position of ngram that matched the reference.
                        pos = position_of_ngram(right_context_ngram, reference)
                        worder.append(pos)  # Add the positions of the ngram.
                        break
                if window <= i:  # If searching the left context is possible.
                    # Retrieve the left context window.
                    left_context_ngram = tuple(islice(hypothesis, i - window, i + 1))
                    num_times_in_ref = ref_ngrams.count(left_context_ngram)
                    num_times_in_hyp = hyp_ngrams.count(left_context_ngram)
                    if num_times_in_ref == num_times_in_hyp == 1:
                        # Find the position of ngram that matched the reference.
                        pos = position_of_ngram(left_context_ngram, reference)
                        # Add the positions of the ngram.
                        worder.append(pos + len(left_context_ngram) - 1)
                        break
    return worder


def find_increasing_sequences(worder):
    """
    Given the *worder* list, this function groups monotonic +1 sequences.

        >>> worder = [7, 8, 9, 10, 6, 0, 1, 2, 3, 4, 5]
        >>> list(find_increasing_sequences(worder))
        [(7, 8, 9, 10), (0, 1, 2, 3, 4, 5)]

    :param worder: The worder list output from word_rank_alignment
    :param type: list(int)
    """
    items = iter(worder)
    a, b = None, next(items, None)
    result = [b]
    while b is not None:
        a, b = b, next(items, None)
        if b is not None and a + 1 == b:
            result.append(b)
        else:
            if len(result) > 1:
                yield tuple(result)
            result = [b]


def kendall_tau(worder, normalize=True):
    """
    Calculates the Kendall's Tau correlation coefficient given the *worder*
    list of word alignments from word_rank_alignment(), using the formula:

        tau = 2 * num_increasing_pairs / num_possible_pairs -1

    Note that the no. of increasing pairs can be discontinuous in the *worder*
    list and each each increasing sequence can be tabulated as choose(len(seq), 2)
    no. of increasing pairs, e.g.

        >>> worder = [7, 8, 9, 10, 6, 0, 1, 2, 3, 4, 5]
        >>> number_possible_pairs = choose(len(worder), 2)
        >>> round(kendall_tau(worder, normalize=False),3)
        -0.236
        >>> round(kendall_tau(worder),3)
        0.382

    :param worder: The worder list output from word_rank_alignment
    :type worder: list(int)
    :param normalize: Flag to indicate normalization to between 0.0 and 1.0.
    :type normalize: boolean
    :return: The Kendall's Tau correlation coefficient.
    :rtype: float
    """
    worder_len = len(worder)
    # With worder_len < 2, `choose(worder_len, 2)` will be 0.
    # As we divide by this, it will give a ZeroDivisionError.
    # To avoid this, we can just return the lowest possible score.
    if worder_len < 2:
        tau = -1
    else:
        # Extract the groups of increasing/monotonic sequences.
        increasing_sequences = find_increasing_sequences(worder)
        # Calculate no. of increasing_pairs in *worder* list.
        num_increasing_pairs = sum(choose(len(seq), 2) for seq in increasing_sequences)
        # Calculate no. of possible pairs.
        num_possible_pairs = choose(worder_len, 2)
        # Kendall's Tau computation.
        tau = 2 * num_increasing_pairs / num_possible_pairs - 1
    if normalize:  # If normalized, the tau output falls between 0.0 to 1.0
        return (tau + 1) / 2
    else:  # Otherwise, the tau outputs falls between -1.0 to +1.0
        return tau


def spearman_rho(worder, normalize=True):
    """
    Calculates the Spearman's Rho correlation coefficient given the *worder*
    list of word alignment from word_rank_alignment(), using the formula:

        rho = 1 - sum(d**2) / choose(len(worder)+1, 3)

    Given that d is the sum of difference between the *worder* list of indices
    and the original word indices from the reference sentence.

    Using the (H0,R0) and (H5, R5) example from the paper

        >>> worder =  [7, 8, 9, 10, 6, 0, 1, 2, 3, 4, 5]
        >>> round(spearman_rho(worder, normalize=False), 3)
        -0.591
        >>> round(spearman_rho(worder), 3)
        0.205

    :param worder: The worder list output from word_rank_alignment
    :param type: list(int)
    """
    worder_len = len(worder)
    sum_d_square = sum((wi - i) ** 2 for wi, i in zip(worder, range(worder_len)))
    rho = 1 - sum_d_square / choose(worder_len + 1, 3)

    if normalize:  # If normalized, the rho output falls between 0.0 to 1.0
        return (rho + 1) / 2
    else:  # Otherwise, the rho outputs falls between -1.0 to +1.0
        return rho

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\shortcuts\dialogs.py ===
from __future__ import annotations

import functools
from asyncio import get_running_loop
from typing import Any, Callable, Sequence, TypeVar

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer
from prompt_toolkit.eventloop import run_in_executor_with_context
from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.key_binding.key_bindings import KeyBindings, merge_key_bindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import AnyContainer, HSplit
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.styles import BaseStyle
from prompt_toolkit.validation import Validator
from prompt_toolkit.widgets import (
    Box,
    Button,
    CheckboxList,
    Dialog,
    Label,
    ProgressBar,
    RadioList,
    TextArea,
    ValidationToolbar,
)

__all__ = [
    "yes_no_dialog",
    "button_dialog",
    "input_dialog",
    "message_dialog",
    "radiolist_dialog",
    "checkboxlist_dialog",
    "progress_dialog",
]


def yes_no_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    yes_text: str = "Yes",
    no_text: str = "No",
    style: BaseStyle | None = None,
) -> Application[bool]:
    """
    Display a Yes/No dialog.
    Return a boolean.
    """

    def yes_handler() -> None:
        get_app().exit(result=True)

    def no_handler() -> None:
        get_app().exit(result=False)

    dialog = Dialog(
        title=title,
        body=Label(text=text, dont_extend_height=True),
        buttons=[
            Button(text=yes_text, handler=yes_handler),
            Button(text=no_text, handler=no_handler),
        ],
        with_background=True,
    )

    return _create_app(dialog, style)


_T = TypeVar("_T")


def button_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    buttons: list[tuple[str, _T]] = [],
    style: BaseStyle | None = None,
) -> Application[_T]:
    """
    Display a dialog with button choices (given as a list of tuples).
    Return the value associated with button.
    """

    def button_handler(v: _T) -> None:
        get_app().exit(result=v)

    dialog = Dialog(
        title=title,
        body=Label(text=text, dont_extend_height=True),
        buttons=[
            Button(text=t, handler=functools.partial(button_handler, v))
            for t, v in buttons
        ],
        with_background=True,
    )

    return _create_app(dialog, style)


def input_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    ok_text: str = "OK",
    cancel_text: str = "Cancel",
    completer: Completer | None = None,
    validator: Validator | None = None,
    password: FilterOrBool = False,
    style: BaseStyle | None = None,
    default: str = "",
) -> Application[str]:
    """
    Display a text input box.
    Return the given text, or None when cancelled.
    """

    def accept(buf: Buffer) -> bool:
        get_app().layout.focus(ok_button)
        return True  # Keep text.

    def ok_handler() -> None:
        get_app().exit(result=textfield.text)

    ok_button = Button(text=ok_text, handler=ok_handler)
    cancel_button = Button(text=cancel_text, handler=_return_none)

    textfield = TextArea(
        text=default,
        multiline=False,
        password=password,
        completer=completer,
        validator=validator,
        accept_handler=accept,
    )

    dialog = Dialog(
        title=title,
        body=HSplit(
            [
                Label(text=text, dont_extend_height=True),
                textfield,
                ValidationToolbar(),
            ],
            padding=D(preferred=1, max=1),
        ),
        buttons=[ok_button, cancel_button],
        with_background=True,
    )

    return _create_app(dialog, style)


def message_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    ok_text: str = "Ok",
    style: BaseStyle | None = None,
) -> Application[None]:
    """
    Display a simple message box and wait until the user presses enter.
    """
    dialog = Dialog(
        title=title,
        body=Label(text=text, dont_extend_height=True),
        buttons=[Button(text=ok_text, handler=_return_none)],
        with_background=True,
    )

    return _create_app(dialog, style)


def radiolist_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    ok_text: str = "Ok",
    cancel_text: str = "Cancel",
    values: Sequence[tuple[_T, AnyFormattedText]] | None = None,
    default: _T | None = None,
    style: BaseStyle | None = None,
) -> Application[_T]:
    """
    Display a simple list of element the user can choose amongst.

    Only one element can be selected at a time using Arrow keys and Enter.
    The focus can be moved between the list and the Ok/Cancel button with tab.
    """
    if values is None:
        values = []

    def ok_handler() -> None:
        get_app().exit(result=radio_list.current_value)

    radio_list = RadioList(values=values, default=default)

    dialog = Dialog(
        title=title,
        body=HSplit(
            [Label(text=text, dont_extend_height=True), radio_list],
            padding=1,
        ),
        buttons=[
            Button(text=ok_text, handler=ok_handler),
            Button(text=cancel_text, handler=_return_none),
        ],
        with_background=True,
    )

    return _create_app(dialog, style)


def checkboxlist_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    ok_text: str = "Ok",
    cancel_text: str = "Cancel",
    values: Sequence[tuple[_T, AnyFormattedText]] | None = None,
    default_values: Sequence[_T] | None = None,
    style: BaseStyle | None = None,
) -> Application[list[_T]]:
    """
    Display a simple list of element the user can choose multiple values amongst.

    Several elements can be selected at a time using Arrow keys and Enter.
    The focus can be moved between the list and the Ok/Cancel button with tab.
    """
    if values is None:
        values = []

    def ok_handler() -> None:
        get_app().exit(result=cb_list.current_values)

    cb_list = CheckboxList(values=values, default_values=default_values)

    dialog = Dialog(
        title=title,
        body=HSplit(
            [Label(text=text, dont_extend_height=True), cb_list],
            padding=1,
        ),
        buttons=[
            Button(text=ok_text, handler=ok_handler),
            Button(text=cancel_text, handler=_return_none),
        ],
        with_background=True,
    )

    return _create_app(dialog, style)


def progress_dialog(
    title: AnyFormattedText = "",
    text: AnyFormattedText = "",
    run_callback: Callable[[Callable[[int], None], Callable[[str], None]], None] = (
        lambda *a: None
    ),
    style: BaseStyle | None = None,
) -> Application[None]:
    """
    :param run_callback: A function that receives as input a `set_percentage`
        function and it does the work.
    """
    loop = get_running_loop()
    progressbar = ProgressBar()
    text_area = TextArea(
        focusable=False,
        # Prefer this text area as big as possible, to avoid having a window
        # that keeps resizing when we add text to it.
        height=D(preferred=10**10),
    )

    dialog = Dialog(
        body=HSplit(
            [
                Box(Label(text=text)),
                Box(text_area, padding=D.exact(1)),
                progressbar,
            ]
        ),
        title=title,
        with_background=True,
    )
    app = _create_app(dialog, style)

    def set_percentage(value: int) -> None:
        progressbar.percentage = int(value)
        app.invalidate()

    def log_text(text: str) -> None:
        loop.call_soon_threadsafe(text_area.buffer.insert_text, text)
        app.invalidate()

    # Run the callback in the executor. When done, set a return value for the
    # UI, so that it quits.
    def start() -> None:
        try:
            run_callback(set_percentage, log_text)
        finally:
            app.exit()

    def pre_run() -> None:
        run_in_executor_with_context(start)

    app.pre_run_callables.append(pre_run)

    return app


def _create_app(dialog: AnyContainer, style: BaseStyle | None) -> Application[Any]:
    # Key bindings.
    bindings = KeyBindings()
    bindings.add("tab")(focus_next)
    bindings.add("s-tab")(focus_previous)

    return Application(
        layout=Layout(dialog),
        key_bindings=merge_key_bindings([load_key_bindings(), bindings]),
        mouse_support=True,
        style=style,
        full_screen=True,
    )


def _return_none() -> None:
    "Button handler that returns None."
    get_app().exit()

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\firefox\firefox_profile.py ===
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

import base64
import copy
import json
import os
import re
import shutil
import sys
import tempfile
import warnings
import zipfile
from io import BytesIO
from xml.dom import minidom

from typing_extensions import deprecated

from selenium.common.exceptions import WebDriverException

WEBDRIVER_PREFERENCES = "webdriver_prefs.json"


@deprecated("Addons must be added after starting the session")
class AddonFormatError(Exception):
    """Exception for not well-formed add-on manifest files."""


class FirefoxProfile:
    DEFAULT_PREFERENCES = None

    def __init__(self, profile_directory=None):
        """Initialises a new instance of a Firefox Profile.

        :args:
         - profile_directory: Directory of profile that you want to use. If a
           directory is passed in it will be cloned and the cloned directory
           will be used by the driver when instantiated.
           This defaults to None and will create a new
           directory when object is created.
        """
        self._desired_preferences = {}
        if profile_directory:
            newprof = os.path.join(tempfile.mkdtemp(), "webdriver-py-profilecopy")
            shutil.copytree(
                profile_directory, newprof, ignore=shutil.ignore_patterns("parent.lock", "lock", ".parentlock")
            )
            self._profile_dir = newprof
            os.chmod(self._profile_dir, 0o755)
        else:
            self._profile_dir = tempfile.mkdtemp()
            if not FirefoxProfile.DEFAULT_PREFERENCES:
                with open(
                    os.path.join(os.path.dirname(__file__), WEBDRIVER_PREFERENCES), encoding="utf-8"
                ) as default_prefs:
                    FirefoxProfile.DEFAULT_PREFERENCES = json.load(default_prefs)

            self._desired_preferences = copy.deepcopy(FirefoxProfile.DEFAULT_PREFERENCES["mutable"])
            for key, value in FirefoxProfile.DEFAULT_PREFERENCES["frozen"].items():
                self._desired_preferences[key] = value

    # Public Methods
    def set_preference(self, key, value):
        """Sets the preference that we want in the profile."""
        self._desired_preferences[key] = value

    @deprecated("Addons must be added after starting the session")
    def add_extension(self, extension=None):
        self._install_extension(extension)

    def update_preferences(self):
        """Writes the desired user prefs to disk."""
        user_prefs = os.path.join(self._profile_dir, "user.js")
        if os.path.isfile(user_prefs):
            os.chmod(user_prefs, 0o644)
            self._read_existing_userjs(user_prefs)
        with open(user_prefs, "w", encoding="utf-8") as f:
            for key, value in self._desired_preferences.items():
                f.write(f'user_pref("{key}", {json.dumps(value)});\n')

    # Properties

    @property
    def path(self):
        """Gets the profile directory that is currently being used."""
        return self._profile_dir

    @property
    @deprecated("The port is stored in the Service class")
    def port(self):
        """Gets the port that WebDriver is working on."""
        return self._port

    @port.setter
    @deprecated("The port is stored in the Service class")
    def port(self, port) -> None:
        """Sets the port that WebDriver will be running on."""
        if not isinstance(port, int):
            raise WebDriverException("Port needs to be an integer")
        try:
            port = int(port)
            if port < 1 or port > 65535:
                raise WebDriverException("Port number must be in the range 1..65535")
        except (ValueError, TypeError):
            raise WebDriverException("Port needs to be an integer")
        self._port = port
        self.set_preference("webdriver_firefox_port", self._port)

    @property
    @deprecated("Allowing untrusted certs is toggled in the Options class")
    def accept_untrusted_certs(self):
        return self._desired_preferences["webdriver_accept_untrusted_certs"]

    @accept_untrusted_certs.setter
    @deprecated("Allowing untrusted certs is toggled in the Options class")
    def accept_untrusted_certs(self, value) -> None:
        if not isinstance(value, bool):
            raise WebDriverException("Please pass in a Boolean to this call")
        self.set_preference("webdriver_accept_untrusted_certs", value)

    @property
    @deprecated("Allowing untrusted certs is toggled in the Options class")
    def assume_untrusted_cert_issuer(self):
        return self._desired_preferences["webdriver_assume_untrusted_issuer"]

    @assume_untrusted_cert_issuer.setter
    @deprecated("Allowing untrusted certs is toggled in the Options class")
    def assume_untrusted_cert_issuer(self, value) -> None:
        if not isinstance(value, bool):
            raise WebDriverException("Please pass in a Boolean to this call")

        self.set_preference("webdriver_assume_untrusted_issuer", value)

    @property
    def encoded(self) -> str:
        """Updates preferences and creates a zipped, base64 encoded string of
        profile directory."""
        if self._desired_preferences:
            self.update_preferences()
        fp = BytesIO()
        with zipfile.ZipFile(fp, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as zipped:
            path_root = len(self.path) + 1  # account for trailing slash
            for base, _, files in os.walk(self.path):
                for fyle in files:
                    filename = os.path.join(base, fyle)
                    zipped.write(filename, filename[path_root:])
        return base64.b64encode(fp.getvalue()).decode("UTF-8")

    def _read_existing_userjs(self, userjs):
        """Reads existing preferences and adds them to desired preference
        dictionary."""
        pref_pattern = re.compile(r'user_pref\("(.*)",\s(.*)\)')
        with open(userjs, encoding="utf-8") as f:
            for usr in f:
                matches = pref_pattern.search(usr)
                try:
                    self._desired_preferences[matches.group(1)] = json.loads(matches.group(2))
                except Exception:
                    warnings.warn(
                        f"(skipping) failed to json.loads existing preference: {matches.group(1) + matches.group(2)}"
                    )

    @deprecated("Addons must be added after starting the session")
    def _install_extension(self, addon, unpack=True):
        """Installs addon from a filepath, url or directory of addons in the
        profile.

        - path: url, absolute path to .xpi, or directory of addons
        - unpack: whether to unpack unless specified otherwise in the install.rdf
        """
        tmpdir = None
        xpifile = None
        if addon.endswith(".xpi"):
            tmpdir = tempfile.mkdtemp(suffix="." + os.path.split(addon)[-1])
            compressed_file = zipfile.ZipFile(addon, "r")
            for name in compressed_file.namelist():
                if name.endswith("/"):
                    if not os.path.isdir(os.path.join(tmpdir, name)):
                        os.makedirs(os.path.join(tmpdir, name))
                else:
                    if not os.path.isdir(os.path.dirname(os.path.join(tmpdir, name))):
                        os.makedirs(os.path.dirname(os.path.join(tmpdir, name)))
                    data = compressed_file.read(name)
                    with open(os.path.join(tmpdir, name), "wb") as f:
                        f.write(data)
            xpifile = addon
            addon = tmpdir

        # determine the addon id
        addon_details = self._addon_details(addon)
        addon_id = addon_details.get("id")
        assert addon_id, f"The addon id could not be found: {addon}"

        # copy the addon to the profile
        extensions_dir = os.path.join(self._profile_dir, "extensions")
        addon_path = os.path.join(extensions_dir, addon_id)
        if not unpack and not addon_details["unpack"] and xpifile:
            if not os.path.exists(extensions_dir):
                os.makedirs(extensions_dir)
                os.chmod(extensions_dir, 0o755)
            shutil.copy(xpifile, addon_path + ".xpi")
        else:
            if not os.path.exists(addon_path):
                shutil.copytree(addon, addon_path, symlinks=True)

        # remove the temporary directory, if any
        if tmpdir:
            shutil.rmtree(tmpdir)

    @deprecated("Addons must be added after starting the session")
    def _addon_details(self, addon_path):
        """Returns a dictionary of details about the addon.

        :param addon_path: path to the add-on directory or XPI

        Returns::

            {
                "id": "rainbow@colors.org",  # id of the addon
                "version": "1.4",  # version of the addon
                "name": "Rainbow",  # name of the addon
                "unpack": False,
            }  # whether to unpack the addon
        """

        details = {"id": None, "unpack": False, "name": None, "version": None}

        def get_namespace_id(doc, url):
            attributes = doc.documentElement.attributes
            namespace = ""
            for i in range(attributes.length):
                if attributes.item(i).value == url:
                    if ":" in attributes.item(i).name:
                        # If the namespace is not the default one remove 'xlmns:'
                        namespace = attributes.item(i).name.split(":")[1] + ":"
                        break
            return namespace

        def get_text(element):
            """Retrieve the text value of a given node."""
            rc = []
            for node in element.childNodes:
                if node.nodeType == node.TEXT_NODE:
                    rc.append(node.data)
            return "".join(rc).strip()

        def parse_manifest_json(content):
            """Extracts the details from the contents of a WebExtensions
            `manifest.json` file."""
            manifest = json.loads(content)
            try:
                id = manifest["applications"]["gecko"]["id"]
            except KeyError:
                id = manifest["name"].replace(" ", "") + "@" + manifest["version"]
            return {
                "id": id,
                "version": manifest["version"],
                "name": manifest["version"],
                "unpack": False,
            }

        if not os.path.exists(addon_path):
            raise OSError(f"Add-on path does not exist: {addon_path}")

        try:
            if zipfile.is_zipfile(addon_path):
                with zipfile.ZipFile(addon_path, "r") as compressed_file:
                    if "manifest.json" in compressed_file.namelist():
                        return parse_manifest_json(compressed_file.read("manifest.json"))

                    manifest = compressed_file.read("install.rdf")
            elif os.path.isdir(addon_path):
                manifest_json_filename = os.path.join(addon_path, "manifest.json")
                if os.path.exists(manifest_json_filename):
                    with open(manifest_json_filename, encoding="utf-8") as f:
                        return parse_manifest_json(f.read())

                with open(os.path.join(addon_path, "install.rdf"), encoding="utf-8") as f:
                    manifest = f.read()
            else:
                raise OSError(f"Add-on path is neither an XPI nor a directory: {addon_path}")
        except (OSError, KeyError) as e:
            raise AddonFormatError(str(e), sys.exc_info()[2])

        try:
            doc = minidom.parseString(manifest)

            # Get the namespaces abbreviations
            em = get_namespace_id(doc, "http://www.mozilla.org/2004/em-rdf#")
            rdf = get_namespace_id(doc, "http://www.w3.org/1999/02/22-rdf-syntax-ns#")

            description = doc.getElementsByTagName(rdf + "Description").item(0)
            if not description:
                description = doc.getElementsByTagName("Description").item(0)
            for node in description.childNodes:
                # Remove the namespace prefix from the tag for comparison
                entry = node.nodeName.replace(em, "")
                if entry in details:
                    details.update({entry: get_text(node)})
            if not details.get("id"):
                for i in range(description.attributes.length):
                    attribute = description.attributes.item(i)
                    if attribute.name == em + "id":
                        details.update({"id": attribute.value})
        except Exception as e:
            raise AddonFormatError(str(e), sys.exc_info()[2])

        # turn unpack into a true/false value
        if isinstance(details["unpack"], str):
            details["unpack"] = details["unpack"].lower() == "true"

        # If no ID is set, the add-on is invalid
        if not details.get("id"):
            raise AddonFormatError("Add-on id could not be found.")

        return details

# === NexusCore/myenv\Lib\site-packages\pip\_internal\cli\req_command.py ===
"""Contains the RequirementCommand base class.

This class is in a separate module so the commands that do not always
need PackageFinder capability don't unnecessarily import the
PackageFinder machinery and all its vendored dependencies, etc.
"""

import logging
from functools import partial
from optparse import Values
from typing import Any, List, Optional, Tuple

from pip._internal.cache import WheelCache
from pip._internal.cli import cmdoptions
from pip._internal.cli.index_command import IndexGroupCommand
from pip._internal.cli.index_command import SessionCommandMixin as SessionCommandMixin
from pip._internal.exceptions import CommandError, PreviousBuildDirError
from pip._internal.index.collector import LinkCollector
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.models.target_python import TargetPython
from pip._internal.network.session import PipSession
from pip._internal.operations.build.build_tracker import BuildTracker
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.constructors import (
    install_req_from_editable,
    install_req_from_line,
    install_req_from_parsed_requirement,
    install_req_from_req_string,
)
from pip._internal.req.req_file import parse_requirements
from pip._internal.req.req_install import InstallRequirement
from pip._internal.resolution.base import BaseResolver
from pip._internal.utils.temp_dir import (
    TempDirectory,
    TempDirectoryTypeRegistry,
    tempdir_kinds,
)

logger = logging.getLogger(__name__)


KEEPABLE_TEMPDIR_TYPES = [
    tempdir_kinds.BUILD_ENV,
    tempdir_kinds.EPHEM_WHEEL_CACHE,
    tempdir_kinds.REQ_BUILD,
]


def with_cleanup(func: Any) -> Any:
    """Decorator for common logic related to managing temporary
    directories.
    """

    def configure_tempdir_registry(registry: TempDirectoryTypeRegistry) -> None:
        for t in KEEPABLE_TEMPDIR_TYPES:
            registry.set_delete(t, False)

    def wrapper(
        self: RequirementCommand, options: Values, args: List[Any]
    ) -> Optional[int]:
        assert self.tempdir_registry is not None
        if options.no_clean:
            configure_tempdir_registry(self.tempdir_registry)

        try:
            return func(self, options, args)
        except PreviousBuildDirError:
            # This kind of conflict can occur when the user passes an explicit
            # build directory with a pre-existing folder. In that case we do
            # not want to accidentally remove it.
            configure_tempdir_registry(self.tempdir_registry)
            raise

    return wrapper


class RequirementCommand(IndexGroupCommand):
    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)

        self.cmd_opts.add_option(cmdoptions.no_clean())

    @staticmethod
    def determine_resolver_variant(options: Values) -> str:
        """Determines which resolver should be used, based on the given options."""
        if "legacy-resolver" in options.deprecated_features_enabled:
            return "legacy"

        return "resolvelib"

    @classmethod
    def make_requirement_preparer(
        cls,
        temp_build_dir: TempDirectory,
        options: Values,
        build_tracker: BuildTracker,
        session: PipSession,
        finder: PackageFinder,
        use_user_site: bool,
        download_dir: Optional[str] = None,
        verbosity: int = 0,
    ) -> RequirementPreparer:
        """
        Create a RequirementPreparer instance for the given parameters.
        """
        temp_build_dir_path = temp_build_dir.path
        assert temp_build_dir_path is not None
        legacy_resolver = False

        resolver_variant = cls.determine_resolver_variant(options)
        if resolver_variant == "resolvelib":
            lazy_wheel = "fast-deps" in options.features_enabled
            if lazy_wheel:
                logger.warning(
                    "pip is using lazily downloaded wheels using HTTP "
                    "range requests to obtain dependency information. "
                    "This experimental feature is enabled through "
                    "--use-feature=fast-deps and it is not ready for "
                    "production."
                )
        else:
            legacy_resolver = True
            lazy_wheel = False
            if "fast-deps" in options.features_enabled:
                logger.warning(
                    "fast-deps has no effect when used with the legacy resolver."
                )

        return RequirementPreparer(
            build_dir=temp_build_dir_path,
            src_dir=options.src_dir,
            download_dir=download_dir,
            build_isolation=options.build_isolation,
            check_build_deps=options.check_build_deps,
            build_tracker=build_tracker,
            session=session,
            progress_bar=options.progress_bar,
            finder=finder,
            require_hashes=options.require_hashes,
            use_user_site=use_user_site,
            lazy_wheel=lazy_wheel,
            verbosity=verbosity,
            legacy_resolver=legacy_resolver,
        )

    @classmethod
    def make_resolver(
        cls,
        preparer: RequirementPreparer,
        finder: PackageFinder,
        options: Values,
        wheel_cache: Optional[WheelCache] = None,
        use_user_site: bool = False,
        ignore_installed: bool = True,
        ignore_requires_python: bool = False,
        force_reinstall: bool = False,
        upgrade_strategy: str = "to-satisfy-only",
        use_pep517: Optional[bool] = None,
        py_version_info: Optional[Tuple[int, ...]] = None,
    ) -> BaseResolver:
        """
        Create a Resolver instance for the given parameters.
        """
        make_install_req = partial(
            install_req_from_req_string,
            isolated=options.isolated_mode,
            use_pep517=use_pep517,
        )
        resolver_variant = cls.determine_resolver_variant(options)
        # The long import name and duplicated invocation is needed to convince
        # Mypy into correctly typechecking. Otherwise it would complain the
        # "Resolver" class being redefined.
        if resolver_variant == "resolvelib":
            import pip._internal.resolution.resolvelib.resolver

            return pip._internal.resolution.resolvelib.resolver.Resolver(
                preparer=preparer,
                finder=finder,
                wheel_cache=wheel_cache,
                make_install_req=make_install_req,
                use_user_site=use_user_site,
                ignore_dependencies=options.ignore_dependencies,
                ignore_installed=ignore_installed,
                ignore_requires_python=ignore_requires_python,
                force_reinstall=force_reinstall,
                upgrade_strategy=upgrade_strategy,
                py_version_info=py_version_info,
            )
        import pip._internal.resolution.legacy.resolver

        return pip._internal.resolution.legacy.resolver.Resolver(
            preparer=preparer,
            finder=finder,
            wheel_cache=wheel_cache,
            make_install_req=make_install_req,
            use_user_site=use_user_site,
            ignore_dependencies=options.ignore_dependencies,
            ignore_installed=ignore_installed,
            ignore_requires_python=ignore_requires_python,
            force_reinstall=force_reinstall,
            upgrade_strategy=upgrade_strategy,
            py_version_info=py_version_info,
        )

    def get_requirements(
        self,
        args: List[str],
        options: Values,
        finder: PackageFinder,
        session: PipSession,
    ) -> List[InstallRequirement]:
        """
        Parse command-line arguments into the corresponding requirements.
        """
        requirements: List[InstallRequirement] = []
        for filename in options.constraints:
            for parsed_req in parse_requirements(
                filename,
                constraint=True,
                finder=finder,
                options=options,
                session=session,
            ):
                req_to_add = install_req_from_parsed_requirement(
                    parsed_req,
                    isolated=options.isolated_mode,
                    user_supplied=False,
                )
                requirements.append(req_to_add)

        for req in args:
            req_to_add = install_req_from_line(
                req,
                comes_from=None,
                isolated=options.isolated_mode,
                use_pep517=options.use_pep517,
                user_supplied=True,
                config_settings=getattr(options, "config_settings", None),
            )
            requirements.append(req_to_add)

        for req in options.editables:
            req_to_add = install_req_from_editable(
                req,
                user_supplied=True,
                isolated=options.isolated_mode,
                use_pep517=options.use_pep517,
                config_settings=getattr(options, "config_settings", None),
            )
            requirements.append(req_to_add)

        # NOTE: options.require_hashes may be set if --require-hashes is True
        for filename in options.requirements:
            for parsed_req in parse_requirements(
                filename, finder=finder, options=options, session=session
            ):
                req_to_add = install_req_from_parsed_requirement(
                    parsed_req,
                    isolated=options.isolated_mode,
                    use_pep517=options.use_pep517,
                    user_supplied=True,
                    config_settings=(
                        parsed_req.options.get("config_settings")
                        if parsed_req.options
                        else None
                    ),
                )
                requirements.append(req_to_add)

        # If any requirement has hash options, enable hash checking.
        if any(req.has_hash_options for req in requirements):
            options.require_hashes = True

        if not (args or options.editables or options.requirements):
            opts = {"name": self.name}
            if options.find_links:
                raise CommandError(
                    "You must give at least one requirement to {name} "
                    '(maybe you meant "pip {name} {links}"?)'.format(
                        **dict(opts, links=" ".join(options.find_links))
                    )
                )
            else:
                raise CommandError(
                    "You must give at least one requirement to {name} "
                    '(see "pip help {name}")'.format(**opts)
                )

        return requirements

    @staticmethod
    def trace_basic_info(finder: PackageFinder) -> None:
        """
        Trace basic information about the provided objects.
        """
        # Display where finder is looking for packages
        search_scope = finder.search_scope
        locations = search_scope.get_formatted_locations()
        if locations:
            logger.info(locations)

    def _build_package_finder(
        self,
        options: Values,
        session: PipSession,
        target_python: Optional[TargetPython] = None,
        ignore_requires_python: Optional[bool] = None,
    ) -> PackageFinder:
        """
        Create a package finder appropriate to this requirement command.

        :param ignore_requires_python: Whether to ignore incompatible
            "Requires-Python" values in links. Defaults to False.
        """
        link_collector = LinkCollector.create(session, options=options)
        selection_prefs = SelectionPreferences(
            allow_yanked=True,
            format_control=options.format_control,
            allow_all_prereleases=options.pre,
            prefer_binary=options.prefer_binary,
            ignore_requires_python=ignore_requires_python,
        )

        return PackageFinder.create(
            link_collector=link_collector,
            selection_prefs=selection_prefs,
            target_python=target_python,
        )

# === NexusCore/openenv\Lib\site-packages\nltk\chat\zen.py ===
# Natural Language Toolkit: Zen Chatbot
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Amy Holland <amyrh@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Zen Chatbot talks in gems of Zen wisdom.

This is a sample conversation with Zen Chatbot:
ZC:    Welcome, my child.
me:    Good afternoon.
ZC:    Ask the question you have come to ask.
me:    How can I achieve enlightenment?
ZC:    How do you suppose?
me:    Through meditation.
ZC:    Form is emptiness, and emptiness form.
me:    How can I empty my mind of worldly troubles?
ZC:    Will an answer to that really help in your search for enlightenment?
me:    Yes.
ZC:    It is better to be right than to be certain.
me:    I seek truth and wisdom.
ZC:    The search for truth is a long journey.
me:    Are you sure?
ZC:    Maybe sure, maybe not sure.


The chatbot structure is based on that of chat.eliza. Thus, it uses
a translation table to convert from question to response
i.e. "I am" --> "you are"

Of course, since Zen Chatbot does not understand the meaning of any words,
responses are very limited. Zen Chatbot will usually answer very vaguely, or
respond to a question by asking a different question, in much the same way
as Eliza.
"""

from nltk.chat.util import Chat, reflections

# responses are matched top to bottom, so non-specific matches occur later
# for each match, a list of possible responses is provided
responses = (
    # Zen Chatbot opens with the line "Welcome, my child." The usual
    # response will be a greeting problem: 'good' matches "good morning",
    # "good day" etc, but also "good grief!"  and other sentences starting
    # with the word 'good' that may not be a greeting
    (
        r"(hello(.*))|(good [a-zA-Z]+)",
        (
            "The path to enlightenment is often difficult to see.",
            "Greetings. I sense your mind is troubled. Tell me of your troubles.",
            "Ask the question you have come to ask.",
            "Hello. Do you seek englightenment?",
        ),
    ),
    # "I need" and "I want" can be followed by a thing (eg 'help')
    # or an action (eg 'to see you')
    #
    # This is a problem with this style of response -
    # person:    "I need you"
    # chatbot:    "me can be achieved by hard work and dedication of the mind"
    # i.e. 'you' is not really a thing that can be mapped this way, so this
    # interpretation only makes sense for some inputs
    #
    (
        r"i need (.*)",
        (
            "%1 can be achieved by hard work and dedication of the mind.",
            "%1 is not a need, but a desire of the mind. Clear your mind of such concerns.",
            "Focus your mind on%1, and you will find what you need.",
        ),
    ),
    (
        r"i want (.*)",
        (
            "Desires of the heart will distract you from the path to enlightenment.",
            "Will%1 help you attain enlightenment?",
            "Is%1 a desire of the mind, or of the heart?",
        ),
    ),
    # why questions are separated into three types:
    # "why..I"     e.g. "why am I here?" "Why do I like cake?"
    # "why..you"    e.g. "why are you here?" "Why won't you tell me?"
    # "why..."    e.g. "Why is the sky blue?"
    # problems:
    #     person:  "Why can't you tell me?"
    #     chatbot: "Are you sure I tell you?"
    # - this style works for positives (e.g. "why do you like cake?")
    #   but does not work for negatives (e.g. "why don't you like cake?")
    (r"why (.*) i (.*)\?", ("You%1%2?", "Perhaps you only think you%1%2")),
    (r"why (.*) you(.*)\?", ("Why%1 you%2?", "%2 I%1", "Are you sure I%2?")),
    (r"why (.*)\?", ("I cannot tell you why%1.", "Why do you think %1?")),
    # e.g. "are you listening?", "are you a duck"
    (
        r"are you (.*)\?",
        ("Maybe%1, maybe not%1.", "Whether I am%1 or not is God's business."),
    ),
    # e.g. "am I a duck?", "am I going to die?"
    (
        r"am i (.*)\?",
        ("Perhaps%1, perhaps not%1.", "Whether you are%1 or not is not for me to say."),
    ),
    # what questions, e.g. "what time is it?"
    # problems:
    #     person:  "What do you want?"
    #    chatbot: "Seek truth, not what do me want."
    (r"what (.*)\?", ("Seek truth, not what%1.", "What%1 should not concern you.")),
    # how questions, e.g. "how do you do?"
    (
        r"how (.*)\?",
        (
            "How do you suppose?",
            "Will an answer to that really help in your search for enlightenment?",
            "Ask yourself not how, but why.",
        ),
    ),
    # can questions, e.g. "can you run?", "can you come over here please?"
    (
        r"can you (.*)\?",
        (
            "I probably can, but I may not.",
            "Maybe I can%1, and maybe I cannot.",
            "I can do all, and I can do nothing.",
        ),
    ),
    # can questions, e.g. "can I have some cake?", "can I know truth?"
    (
        r"can i (.*)\?",
        (
            "You can%1 if you believe you can%1, and have a pure spirit.",
            "Seek truth and you will know if you can%1.",
        ),
    ),
    # e.g. "It is raining" - implies the speaker is certain of a fact
    (
        r"it is (.*)",
        (
            "How can you be certain that%1, when you do not even know yourself?",
            "Whether it is%1 or not does not change the way the world is.",
        ),
    ),
    # e.g. "is there a doctor in the house?"
    (
        r"is there (.*)\?",
        ("There is%1 if you believe there is.", "It is possible that there is%1."),
    ),
    # e.g. "is it possible?", "is this true?"
    (r"is(.*)\?", ("%1 is not relevant.", "Does this matter?")),
    # non-specific question
    (
        r"(.*)\?",
        (
            "Do you think %1?",
            "You seek the truth. Does the truth seek you?",
            "If you intentionally pursue the answers to your questions, the answers become hard to see.",
            "The answer to your question cannot be told. It must be experienced.",
        ),
    ),
    # expression of hate of form "I hate you" or "Kelly hates cheese"
    (
        r"(.*) (hate[s]?)|(dislike[s]?)|(don\'t like)(.*)",
        (
            "Perhaps it is not about hating %2, but about hate from within.",
            "Weeds only grow when we dislike them",
            "Hate is a very strong emotion.",
        ),
    ),
    # statement containing the word 'truth'
    (
        r"(.*) truth(.*)",
        (
            "Seek truth, and truth will seek you.",
            "Remember, it is not the spoon which bends - only yourself.",
            "The search for truth is a long journey.",
        ),
    ),
    # desire to do an action
    # e.g. "I want to go shopping"
    (
        r"i want to (.*)",
        ("You may %1 if your heart truly desires to.", "You may have to %1."),
    ),
    # desire for an object
    # e.g. "I want a pony"
    (
        r"i want (.*)",
        (
            "Does your heart truly desire %1?",
            "Is this a desire of the heart, or of the mind?",
        ),
    ),
    # e.g. "I can't wait" or "I can't do this"
    (
        r"i can\'t (.*)",
        (
            "What we can and can't do is a limitation of the mind.",
            "There are limitations of the body, and limitations of the mind.",
            "Have you tried to%1 with a clear mind?",
        ),
    ),
    # "I think.." indicates uncertainty. e.g. "I think so."
    # problem: exceptions...
    # e.g. "I think, therefore I am"
    (
        r"i think (.*)",
        (
            "Uncertainty in an uncertain world.",
            "Indeed, how can we be certain of anything in such uncertain times.",
            "Are you not, in fact, certain that%1?",
        ),
    ),
    # "I feel...emotions/sick/light-headed..."
    (
        r"i feel (.*)",
        (
            "Your body and your emotions are both symptoms of your mind."
            "What do you believe is the root of such feelings?",
            "Feeling%1 can be a sign of your state-of-mind.",
        ),
    ),
    # exclaimation mark indicating emotion
    # e.g. "Wow!" or "No!"
    (
        r"(.*)!",
        (
            "I sense that you are feeling emotional today.",
            "You need to calm your emotions.",
        ),
    ),
    # because [statement]
    # e.g. "because I said so"
    (
        r"because (.*)",
        (
            "Does knowning the reasons behind things help you to understand"
            " the things themselves?",
            "If%1, what else must be true?",
        ),
    ),
    # yes or no - raise an issue of certainty/correctness
    (
        r"(yes)|(no)",
        (
            "Is there certainty in an uncertain world?",
            "It is better to be right than to be certain.",
        ),
    ),
    # sentence containing word 'love'
    (
        r"(.*)love(.*)",
        (
            "Think of the trees: they let the birds perch and fly with no intention to call them when they come, and no longing for their return when they fly away. Let your heart be like the trees.",
            "Free love!",
        ),
    ),
    # sentence containing word 'understand' - r
    (
        r"(.*)understand(.*)",
        (
            "If you understand, things are just as they are;"
            " if you do not understand, things are just as they are.",
            "Imagination is more important than knowledge.",
        ),
    ),
    # 'I', 'me', 'my' - person is talking about themself.
    # this breaks down when words contain these - eg 'Thyme', 'Irish'
    (
        r"(.*)(me )|( me)|(my)|(mine)|(i)(.*)",
        (
            "'I', 'me', 'my'... these are selfish expressions.",
            "Have you ever considered that you might be a selfish person?",
            "Try to consider others, not just yourself.",
            "Think not just of yourself, but of others.",
        ),
    ),
    # 'you' starting a sentence
    # e.g. "you stink!"
    (
        r"you (.*)",
        ("My path is not of concern to you.", "I am but one, and you but one more."),
    ),
    # say goodbye with some extra Zen wisdom.
    (
        r"exit",
        (
            "Farewell. The obstacle is the path.",
            "Farewell. Life is a journey, not a destination.",
            "Good bye. We are cups, constantly and quietly being filled."
            "\nThe trick is knowning how to tip ourselves over and let the beautiful stuff out.",
        ),
    ),
    # fall through case -
    # when stumped, respond with generic zen wisdom
    #
    (
        r"(.*)",
        (
            "When you're enlightened, every word is wisdom.",
            "Random talk is useless.",
            "The reverse side also has a reverse side.",
            "Form is emptiness, and emptiness is form.",
            "I pour out a cup of water. Is the cup empty?",
        ),
    ),
)

zen_chatbot = Chat(responses, reflections)


def zen_chat():
    print("*" * 75)
    print("Zen Chatbot!".center(75))
    print("*" * 75)
    print('"Look beyond mere words and letters - look into your mind"'.center(75))
    print("* Talk your way to truth with Zen Chatbot.")
    print("* Type 'quit' when you have had enough.")
    print("*" * 75)
    print("Welcome, my child.")

    zen_chatbot.converse()


def demo():
    zen_chat()


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\numpy\f2py\func2subr.py ===
"""

Rules for building C/API module with f2py2e.

Copyright 1999 -- 2011 Pearu Peterson all rights reserved.
Copyright 2011 -- present NumPy Developers.
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
"""
import copy

from ._isocbind import isoc_kindmap
from .auxfuncs import (
    getfortranname,
    isexternal,
    isfunction,
    isfunction_wrap,
    isintent_in,
    isintent_out,
    islogicalfunction,
    ismoduleroutine,
    isscalar,
    issubroutine,
    issubroutine_wrap,
    outmess,
    show,
)


def var2fixfortran(vars, a, fa=None, f90mode=None):
    if fa is None:
        fa = a
    if a not in vars:
        show(vars)
        outmess(f'var2fixfortran: No definition for argument "{a}".\n')
        return ''
    if 'typespec' not in vars[a]:
        show(vars[a])
        outmess(f'var2fixfortran: No typespec for argument "{a}".\n')
        return ''
    vardef = vars[a]['typespec']
    if vardef == 'type' and 'typename' in vars[a]:
        vardef = f"{vardef}({vars[a]['typename']})"
    selector = {}
    lk = ''
    if 'kindselector' in vars[a]:
        selector = vars[a]['kindselector']
        lk = 'kind'
    elif 'charselector' in vars[a]:
        selector = vars[a]['charselector']
        lk = 'len'
    if '*' in selector:
        if f90mode:
            if selector['*'] in ['*', ':', '(*)']:
                vardef = f'{vardef}(len=*)'
            else:
                vardef = f"{vardef}({lk}={selector['*']})"
        elif selector['*'] in ['*', ':']:
            vardef = f"{vardef}*({selector['*']})"
        else:
            vardef = f"{vardef}*{selector['*']}"
    elif 'len' in selector:
        vardef = f"{vardef}(len={selector['len']}"
        if 'kind' in selector:
            vardef = f"{vardef},kind={selector['kind']})"
        else:
            vardef = f'{vardef})'
    elif 'kind' in selector:
        vardef = f"{vardef}(kind={selector['kind']})"

    vardef = f'{vardef} {fa}'
    if 'dimension' in vars[a]:
        vardef = f"{vardef}({','.join(vars[a]['dimension'])})"
    return vardef

def useiso_c_binding(rout):
    useisoc = False
    for key, value in rout['vars'].items():
        kind_value = value.get('kindselector', {}).get('kind')
        if kind_value in isoc_kindmap:
            return True
    return useisoc

def createfuncwrapper(rout, signature=0):
    assert isfunction(rout)

    extra_args = []
    vars = rout['vars']
    for a in rout['args']:
        v = rout['vars'][a]
        for i, d in enumerate(v.get('dimension', [])):
            if d == ':':
                dn = f'f2py_{a}_d{i}'
                dv = {'typespec': 'integer', 'intent': ['hide']}
                dv['='] = f'shape({a}, {i})'
                extra_args.append(dn)
                vars[dn] = dv
                v['dimension'][i] = dn
    rout['args'].extend(extra_args)
    need_interface = bool(extra_args)

    ret = ['']

    def add(line, ret=ret):
        ret[0] = f'{ret[0]}\n      {line}'
    name = rout['name']
    fortranname = getfortranname(rout)
    f90mode = ismoduleroutine(rout)
    newname = f'{name}f2pywrap'

    if newname not in vars:
        vars[newname] = vars[name]
        args = [newname] + rout['args'][1:]
    else:
        args = [newname] + rout['args']

    l_tmpl = var2fixfortran(vars, name, '@@@NAME@@@', f90mode)
    if l_tmpl[:13] == 'character*(*)':
        if f90mode:
            l_tmpl = 'character(len=10)' + l_tmpl[13:]
        else:
            l_tmpl = 'character*10' + l_tmpl[13:]
        charselect = vars[name]['charselector']
        if charselect.get('*', '') == '(*)':
            charselect['*'] = '10'

    l1 = l_tmpl.replace('@@@NAME@@@', newname)
    rl = None

    useisoc = useiso_c_binding(rout)
    sargs = ', '.join(args)
    if f90mode:
        # gh-23598 fix warning
        # Essentially, this gets called again with modules where the name of the
        # function is added to the arguments, which is not required, and removed
        sargs = sargs.replace(f"{name}, ", '')
        args = [arg for arg in args if arg != name]
        rout['args'] = args
        add(f"subroutine f2pywrap_{rout['modulename']}_{name} ({sargs})")
        if not signature:
            add(f"use {rout['modulename']}, only : {fortranname}")
        if useisoc:
            add('use iso_c_binding')
    else:
        add(f'subroutine f2pywrap{name} ({sargs})')
        if useisoc:
            add('use iso_c_binding')
        if not need_interface:
            add(f'external {fortranname}')
            rl = l_tmpl.replace('@@@NAME@@@', '') + ' ' + fortranname

    if need_interface:
        for line in rout['saved_interface'].split('\n'):
            if line.lstrip().startswith('use ') and '__user__' not in line:
                add(line)

    args = args[1:]
    dumped_args = []
    for a in args:
        if isexternal(vars[a]):
            add(f'external {a}')
            dumped_args.append(a)
    for a in args:
        if a in dumped_args:
            continue
        if isscalar(vars[a]):
            add(var2fixfortran(vars, a, f90mode=f90mode))
            dumped_args.append(a)
    for a in args:
        if a in dumped_args:
            continue
        if isintent_in(vars[a]):
            add(var2fixfortran(vars, a, f90mode=f90mode))
            dumped_args.append(a)
    for a in args:
        if a in dumped_args:
            continue
        add(var2fixfortran(vars, a, f90mode=f90mode))

    add(l1)
    if rl is not None:
        add(rl)

    if need_interface:
        if f90mode:
            # f90 module already defines needed interface
            pass
        else:
            add('interface')
            add(rout['saved_interface'].lstrip())
            add('end interface')

    sargs = ', '.join([a for a in args if a not in extra_args])

    if not signature:
        if islogicalfunction(rout):
            add(f'{newname} = .not.(.not.{fortranname}({sargs}))')
        else:
            add(f'{newname} = {fortranname}({sargs})')
    if f90mode:
        add(f"end subroutine f2pywrap_{rout['modulename']}_{name}")
    else:
        add('end')
    return ret[0]


def createsubrwrapper(rout, signature=0):
    assert issubroutine(rout)

    extra_args = []
    vars = rout['vars']
    for a in rout['args']:
        v = rout['vars'][a]
        for i, d in enumerate(v.get('dimension', [])):
            if d == ':':
                dn = f'f2py_{a}_d{i}'
                dv = {'typespec': 'integer', 'intent': ['hide']}
                dv['='] = f'shape({a}, {i})'
                extra_args.append(dn)
                vars[dn] = dv
                v['dimension'][i] = dn
    rout['args'].extend(extra_args)
    need_interface = bool(extra_args)

    ret = ['']

    def add(line, ret=ret):
        ret[0] = f'{ret[0]}\n      {line}'
    name = rout['name']
    fortranname = getfortranname(rout)
    f90mode = ismoduleroutine(rout)

    args = rout['args']

    useisoc = useiso_c_binding(rout)
    sargs = ', '.join(args)
    if f90mode:
        add(f"subroutine f2pywrap_{rout['modulename']}_{name} ({sargs})")
        if useisoc:
            add('use iso_c_binding')
        if not signature:
            add(f"use {rout['modulename']}, only : {fortranname}")
    else:
        add(f'subroutine f2pywrap{name} ({sargs})')
        if useisoc:
            add('use iso_c_binding')
        if not need_interface:
            add(f'external {fortranname}')

    if need_interface:
        for line in rout['saved_interface'].split('\n'):
            if line.lstrip().startswith('use ') and '__user__' not in line:
                add(line)

    dumped_args = []
    for a in args:
        if isexternal(vars[a]):
            add(f'external {a}')
            dumped_args.append(a)
    for a in args:
        if a in dumped_args:
            continue
        if isscalar(vars[a]):
            add(var2fixfortran(vars, a, f90mode=f90mode))
            dumped_args.append(a)
    for a in args:
        if a in dumped_args:
            continue
        add(var2fixfortran(vars, a, f90mode=f90mode))

    if need_interface:
        if f90mode:
            # f90 module already defines needed interface
            pass
        else:
            add('interface')
            for line in rout['saved_interface'].split('\n'):
                if line.lstrip().startswith('use ') and '__user__' in line:
                    continue
                add(line)
            add('end interface')

    sargs = ', '.join([a for a in args if a not in extra_args])

    if not signature:
        add(f'call {fortranname}({sargs})')
    if f90mode:
        add(f"end subroutine f2pywrap_{rout['modulename']}_{name}")
    else:
        add('end')
    return ret[0]


def assubr(rout):
    if isfunction_wrap(rout):
        fortranname = getfortranname(rout)
        name = rout['name']
        outmess('\t\tCreating wrapper for Fortran function "%s"("%s")...\n' % (
            name, fortranname))
        rout = copy.copy(rout)
        fname = name
        rname = fname
        if 'result' in rout:
            rname = rout['result']
            rout['vars'][fname] = rout['vars'][rname]
        fvar = rout['vars'][fname]
        if not isintent_out(fvar):
            if 'intent' not in fvar:
                fvar['intent'] = []
            fvar['intent'].append('out')
            flag = 1
            for i in fvar['intent']:
                if i.startswith('out='):
                    flag = 0
                    break
            if flag:
                fvar['intent'].append(f'out={rname}')
        rout['args'][:] = [fname] + rout['args']
        return rout, createfuncwrapper(rout)
    if issubroutine_wrap(rout):
        fortranname = getfortranname(rout)
        name = rout['name']
        outmess('\t\tCreating wrapper for Fortran subroutine "%s"("%s")...\n'
                % (name, fortranname))
        rout = copy.copy(rout)
        return rout, createsubrwrapper(rout)
    return rout, ''