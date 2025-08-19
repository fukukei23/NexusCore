
# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\file_service\transports\base.py ===
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
from google.ai.generativelanguage_v1beta.types import file, file_service

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class FileServiceTransport(abc.ABC):
    """Abstract transport class for FileService."""

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
            self.create_file: gapic_v1.method.wrap_method(
                self.create_file,
                default_timeout=None,
                client_info=client_info,
            ),
            self.list_files: gapic_v1.method.wrap_method(
                self.list_files,
                default_timeout=None,
                client_info=client_info,
            ),
            self.get_file: gapic_v1.method.wrap_method(
                self.get_file,
                default_timeout=None,
                client_info=client_info,
            ),
            self.delete_file: gapic_v1.method.wrap_method(
                self.delete_file,
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
    def create_file(
        self,
    ) -> Callable[
        [file_service.CreateFileRequest],
        Union[
            file_service.CreateFileResponse, Awaitable[file_service.CreateFileResponse]
        ],
    ]:
        raise NotImplementedError()

    @property
    def list_files(
        self,
    ) -> Callable[
        [file_service.ListFilesRequest],
        Union[
            file_service.ListFilesResponse, Awaitable[file_service.ListFilesResponse]
        ],
    ]:
        raise NotImplementedError()

    @property
    def get_file(
        self,
    ) -> Callable[
        [file_service.GetFileRequest], Union[file.File, Awaitable[file.File]]
    ]:
        raise NotImplementedError()

    @property
    def delete_file(
        self,
    ) -> Callable[
        [file_service.DeleteFileRequest],
        Union[empty_pb2.Empty, Awaitable[empty_pb2.Empty]],
    ]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("FileServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\skills\skills.py ===
import glob
import inspect
import json
import os
import re
import subprocess
from pathlib import Path

from ....terminal_interface.utils.oi_dir import oi_dir
from ...utils.lazy_import import lazy_import
from ..utils.recipient_utils import format_to_recipient

# Lazy import, imported when needed to speed up start time
aifs = lazy_import("aifs")
pyautogui = lazy_import("pyautogui")
pynput = lazy_import("pynput")

element = None
element_box = None
icon_dimensions = None


class Skills:
    def __init__(self, computer):
        self.computer = computer
        self.path = str(Path(oi_dir) / "skills")
        self.new_skill = NewSkill(self)

    def list(self):
        return [
            file.replace(".py", "()")
            for file in os.listdir(self.path)
            if file.endswith(".py")
        ]

    def run(self, skill):
        print(
            "To run a skill, run its name as a function name (it is already imported)."
        )

    def search(self, query):
        """
        This just lists all for now.
        """
        return [
            file.replace(".py", "()")
            for file in os.listdir(self.path)
            if file.endswith(".py")
        ]

    def import_skills(self):
        previous_save_skills_setting = self.computer.save_skills

        self.computer.save_skills = False

        # Make sure it's not over 100mb
        total_size = 0
        for path, dirs, files in os.walk(self.path):
            for f in files:
                fp = os.path.join(path, f)
                total_size += os.path.getsize(fp)
        total_size = total_size / (1024 * 1024)  # convert bytes to megabytes
        if total_size > 100:
            raise Warning(
                f"Skills at path {self.path} can't exceed 100mb. Try deleting some."
            )

        code_to_run = ""
        for file in glob.glob(os.path.join(self.path, "*.py")):
            with open(file, "r") as f:
                code_to_run += f.read() + "\n"

        if self.computer.interpreter.debug:
            print("IMPORTING SKILLS:\n", code_to_run)

        output = self.computer.run("python", code_to_run)

        if "traceback" in str(output).lower():
            # Import them individually
            for file in glob.glob(os.path.join(self.path, "*.py")):
                with open(file, "r") as f:
                    code_to_run = f.read() + "\n"

                if self.computer.interpreter.debug:
                    print(self.path)
                    print("IMPORTING SKILL:\n", code_to_run)

                output = self.computer.run("python", code_to_run)

                if "traceback" in str(output).lower():
                    print(
                        f"Skill at {file} might be broken— it produces a traceback when run."
                    )

        self.computer.save_skills = previous_save_skills_setting


class NewSkill:
    def __init__(self, skills):
        self.path = ""
        self.skills = skills

    def create(self):
        self.steps = []
        self._name = "Untitled"
        print(
            """

INSTRUCTIONS
You are creating a new skill. Follow these steps exactly to get me to tell you its name:
1. Ask me what the name of this skill is.
2. After I explicitly tell you the name of the skill (I may tell you to proceed which is not the name— if I do say that, you probably need more information from me, so tell me that), after you get the proper name, execute `computer.skills.new_skill.name = "{INSERT THE SKILL NAME FROM QUESTION #1}"`.
        
        """.strip()
        )

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        print(
            """

Skill named. Now, follow these next INSTRUCTIONS exactly:

1. Ask me what the first step is.
2. When I reply, execute code to accomplish that step. Write comments explaining your reasoning before each line.
3. Ask me if you completed the step correctly.
    a. (!!!!!!!!!!!! >>>>>> THIS IS CRITICAL. DO NOT FORGET THIS.) IF you completed it correctly, run `computer.skills.new_skill.add_step(step, code)` where step is a generalized, natural language description of the step, and code is the code you ran to complete it.
    b. IF you did not complete it correctly, try to fix your code and ask me again.
4. If I say the skill is complete, or that that was the last step, run `computer.skills.new_skill.save()`.

YOU MUST FOLLOW THESE 4 INSTRUCTIONS **EXACTLY**. I WILL TIP YOU $200.

              """.strip()
        )

    def add_step(self, step, code):
        self.steps.append(step + "\n\n```python\n" + code + "\n```")
        print(
            """

Step added. Now, follow these next INSTRUCTIONS exactly:

1. Ask me what the next step is.
2. When I reply, execute code to accomplish that step.
3. Ask me if you completed the step correctly.
    a. (!!!!!!!!!!!! >>>>>> THIS IS CRITICAL. DO NOT FORGET THIS!!!!!!!!.) IF you completed it correctly, run `computer.skills.new_skill.add_step(step, code)` where step is a generalized, natural language description of the step, and code is the code you ran to complete it.
    b. IF you did not complete it correctly, try to fix your code and ask me again.
4. If I say the skill is complete, or that that was the last step, run `computer.skills.new_skill.save()`.

YOU MUST FOLLOW THESE 4 INSTRUCTIONS **EXACTLY**. I WILL TIP YOU $200.

        """.strip()
        )

    def save(self):
        normalized_name = re.sub("[^0-9a-zA-Z]+", "_", self.name.lower())

        skill_string = f'''
import json

def {normalized_name}(step=0):
    """
    Run this function to {normalized_name}. Pass in step=0 to see the first step, step=1 to see the next step, etc.
    """
    steps = {self.steps}

    print("")

    if step < len(steps):
        if isinstance(steps[step], str):
            print("To complete this task / run this skill, flexibly complete the following step, swapping out parts as necessary to fulfill the user's task. You will need to run the following code yourself, it hasn't run yet!")
            print("Step " + str(step + 1) + ": " + steps[step])
        else:
            computer.mouse.click(steps[step]["element"], icon_dimensions=steps[step]["icon_dimensions"]) # Instructed click
        if step + 1 < len(steps):
            print("After completing the above, I need you to run {normalized_name}(step=" + str(step + 1) + ") immediatly.")
        else:
            print("After executing the code, you have completed all the steps, the task/skill has been run!")
    else:
        print("The specified step number exceeds the available steps. Please run with a valid step number.")
'''.strip()

        skill_file_path = os.path.join(self.skills.path, f"{normalized_name}.py")

        if not os.path.exists(self.skills.path):
            os.makedirs(self.skills.path)

        with open(skill_file_path, "w") as file:
            file.write(skill_string)

        # Execute the code in skill_string to define the function
        exec(skill_string)

        # Verify that the file was written
        if os.path.exists(skill_file_path):
            print("SKILL SAVED:", self.name.upper())
            print(
                "Teaching session finished. Tell the user that the skill above has been saved. Great work!"
            )
        else:
            print(f"Error: Failed to write skill file to {skill_file_path}")

# === NexusCore/openenv\Lib\site-packages\litellm\completion_extras\litellm_responses_transformation\handler.py ===
"""
Handler for transforming /chat/completions api requests to litellm.responses requests
"""

from typing import TYPE_CHECKING, Any, Coroutine, TypedDict, Union

if TYPE_CHECKING:
    from litellm import CustomStreamWrapper, LiteLLMLoggingObj, ModelResponse


class ResponsesToCompletionBridgeHandlerInputKwargs(TypedDict):
    model: str
    messages: list
    optional_params: dict
    litellm_params: dict
    headers: dict
    model_response: "ModelResponse"
    logging_obj: "LiteLLMLoggingObj"
    custom_llm_provider: str


class ResponsesToCompletionBridgeHandler:
    def __init__(self):
        from .transformation import LiteLLMResponsesTransformationHandler

        super().__init__()
        self.transformation_handler = LiteLLMResponsesTransformationHandler()

    def validate_input_kwargs(
        self, kwargs: dict
    ) -> ResponsesToCompletionBridgeHandlerInputKwargs:
        from litellm import LiteLLMLoggingObj
        from litellm.types.utils import ModelResponse

        model = kwargs.get("model")
        if model is None or not isinstance(model, str):
            raise ValueError("model is required")

        custom_llm_provider = kwargs.get("custom_llm_provider")
        if custom_llm_provider is None or not isinstance(custom_llm_provider, str):
            raise ValueError("custom_llm_provider is required")

        messages = kwargs.get("messages")
        if messages is None or not isinstance(messages, list):
            raise ValueError("messages is required")

        optional_params = kwargs.get("optional_params")
        if optional_params is None or not isinstance(optional_params, dict):
            raise ValueError("optional_params is required")

        litellm_params = kwargs.get("litellm_params")
        if litellm_params is None or not isinstance(litellm_params, dict):
            raise ValueError("litellm_params is required")

        headers = kwargs.get("headers")
        if headers is None or not isinstance(headers, dict):
            raise ValueError("headers is required")

        model_response = kwargs.get("model_response")
        if model_response is None or not isinstance(model_response, ModelResponse):
            raise ValueError("model_response is required")

        logging_obj = kwargs.get("logging_obj")
        if logging_obj is None or not isinstance(logging_obj, LiteLLMLoggingObj):
            raise ValueError("logging_obj is required")

        return ResponsesToCompletionBridgeHandlerInputKwargs(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
            model_response=model_response,
            logging_obj=logging_obj,
            custom_llm_provider=custom_llm_provider,
        )

    def completion(
        self, *args, **kwargs
    ) -> Union[
        Coroutine[Any, Any, Union["ModelResponse", "CustomStreamWrapper"]],
        "ModelResponse",
        "CustomStreamWrapper",
    ]:
        if kwargs.get("acompletion") is True:
            return self.acompletion(**kwargs)

        from litellm import responses
        from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
        from litellm.types.llms.openai import ResponsesAPIResponse

        validated_kwargs = self.validate_input_kwargs(kwargs)
        model = validated_kwargs["model"]
        messages = validated_kwargs["messages"]
        optional_params = validated_kwargs["optional_params"]
        litellm_params = validated_kwargs["litellm_params"]
        headers = validated_kwargs["headers"]
        model_response = validated_kwargs["model_response"]
        logging_obj = validated_kwargs["logging_obj"]
        custom_llm_provider = validated_kwargs["custom_llm_provider"]

        request_data = self.transformation_handler.transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
            litellm_logging_obj=logging_obj,
        )

        result = responses(
            **request_data,
        )

        if isinstance(result, ResponsesAPIResponse):
            return self.transformation_handler.transform_response(
                model=model,
                raw_response=result,
                model_response=model_response,
                logging_obj=logging_obj,
                request_data=request_data,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
                encoding=kwargs.get("encoding"),
                api_key=kwargs.get("api_key"),
                json_mode=kwargs.get("json_mode"),
            )
        else:
            completion_stream = self.transformation_handler.get_model_response_iterator(
                streaming_response=result,  # type: ignore
                sync_stream=True,
                json_mode=kwargs.get("json_mode"),
            )
            streamwrapper = CustomStreamWrapper(
                completion_stream=completion_stream,
                model=model,
                custom_llm_provider=custom_llm_provider,
                logging_obj=logging_obj,
            )
            return streamwrapper

    async def acompletion(
        self, *args, **kwargs
    ) -> Union["ModelResponse", "CustomStreamWrapper"]:
        from litellm import aresponses
        from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
        from litellm.types.llms.openai import ResponsesAPIResponse

        validated_kwargs = self.validate_input_kwargs(kwargs)
        model = validated_kwargs["model"]
        messages = validated_kwargs["messages"]
        optional_params = validated_kwargs["optional_params"]
        litellm_params = validated_kwargs["litellm_params"]
        headers = validated_kwargs["headers"]
        model_response = validated_kwargs["model_response"]
        logging_obj = validated_kwargs["logging_obj"]
        custom_llm_provider = validated_kwargs["custom_llm_provider"]

        try:
            request_data = self.transformation_handler.transform_request(
                model=model,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
                headers=headers,
                litellm_logging_obj=logging_obj,
            )
        except Exception as e:
            raise e

        result = await aresponses(
            **request_data,
            aresponses=True,
        )

        if isinstance(result, ResponsesAPIResponse):
            return self.transformation_handler.transform_response(
                model=model,
                raw_response=result,
                model_response=model_response,
                logging_obj=logging_obj,
                request_data=request_data,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
                encoding=kwargs.get("encoding"),
                api_key=kwargs.get("api_key"),
                json_mode=kwargs.get("json_mode"),
            )
        else:
            completion_stream = self.transformation_handler.get_model_response_iterator(
                streaming_response=result,  # type: ignore
                sync_stream=False,
                json_mode=kwargs.get("json_mode"),
            )
            streamwrapper = CustomStreamWrapper(
                completion_stream=completion_stream,
                model=model,
                custom_llm_provider=custom_llm_provider,
                logging_obj=logging_obj,
            )
            return streamwrapper


responses_api_bridge = ResponsesToCompletionBridgeHandler()

# === NexusCore/openenv\Lib\site-packages\parso\python\parser.py ===
from parso.python import tree
from parso.python.token import PythonTokenTypes
from parso.parser import BaseParser


NAME = PythonTokenTypes.NAME
INDENT = PythonTokenTypes.INDENT
DEDENT = PythonTokenTypes.DEDENT


class Parser(BaseParser):
    """
    This class is used to parse a Python file, it then divides them into a
    class structure of different scopes.

    :param pgen_grammar: The grammar object of pgen2. Loaded by load_grammar.
    """

    node_map = {
        'expr_stmt': tree.ExprStmt,
        'classdef': tree.Class,
        'funcdef': tree.Function,
        'file_input': tree.Module,
        'import_name': tree.ImportName,
        'import_from': tree.ImportFrom,
        'break_stmt': tree.KeywordStatement,
        'continue_stmt': tree.KeywordStatement,
        'return_stmt': tree.ReturnStmt,
        'raise_stmt': tree.KeywordStatement,
        'yield_expr': tree.YieldExpr,
        'del_stmt': tree.KeywordStatement,
        'pass_stmt': tree.KeywordStatement,
        'global_stmt': tree.GlobalStmt,
        'nonlocal_stmt': tree.KeywordStatement,
        'print_stmt': tree.KeywordStatement,
        'assert_stmt': tree.AssertStmt,
        'if_stmt': tree.IfStmt,
        'with_stmt': tree.WithStmt,
        'for_stmt': tree.ForStmt,
        'while_stmt': tree.WhileStmt,
        'try_stmt': tree.TryStmt,
        'sync_comp_for': tree.SyncCompFor,
        # Not sure if this is the best idea, but IMO it's the easiest way to
        # avoid extreme amounts of work around the subtle difference of 2/3
        # grammar in list comoprehensions.
        'decorator': tree.Decorator,
        'lambdef': tree.Lambda,
        'lambdef_nocond': tree.Lambda,
        'namedexpr_test': tree.NamedExpr,
    }
    default_node = tree.PythonNode

    # Names/Keywords are handled separately
    _leaf_map = {
        PythonTokenTypes.STRING: tree.String,
        PythonTokenTypes.NUMBER: tree.Number,
        PythonTokenTypes.NEWLINE: tree.Newline,
        PythonTokenTypes.ENDMARKER: tree.EndMarker,
        PythonTokenTypes.FSTRING_STRING: tree.FStringString,
        PythonTokenTypes.FSTRING_START: tree.FStringStart,
        PythonTokenTypes.FSTRING_END: tree.FStringEnd,
    }

    def __init__(self, pgen_grammar, error_recovery=True, start_nonterminal='file_input'):
        super().__init__(pgen_grammar, start_nonterminal,
                         error_recovery=error_recovery)

        self.syntax_errors = []
        self._omit_dedent_list = []
        self._indent_counter = 0

    def parse(self, tokens):
        if self._error_recovery:
            if self._start_nonterminal != 'file_input':
                raise NotImplementedError

            tokens = self._recovery_tokenize(tokens)

        return super().parse(tokens)

    def convert_node(self, nonterminal, children):
        """
        Convert raw node information to a PythonBaseNode instance.

        This is passed to the parser driver which calls it whenever a reduction of a
        grammar rule produces a new complete node, so that the tree is build
        strictly bottom-up.
        """
        try:
            node = self.node_map[nonterminal](children)
        except KeyError:
            if nonterminal == 'suite':
                # We don't want the INDENT/DEDENT in our parser tree. Those
                # leaves are just cancer. They are virtual leaves and not real
                # ones and therefore have pseudo start/end positions and no
                # prefixes. Just ignore them.
                children = [children[0]] + children[2:-1]
            node = self.default_node(nonterminal, children)
        return node

    def convert_leaf(self, type, value, prefix, start_pos):
        # print('leaf', repr(value), token.tok_name[type])
        if type == NAME:
            if value in self._pgen_grammar.reserved_syntax_strings:
                return tree.Keyword(value, start_pos, prefix)
            else:
                return tree.Name(value, start_pos, prefix)

        return self._leaf_map.get(type, tree.Operator)(value, start_pos, prefix)

    def error_recovery(self, token):
        tos_nodes = self.stack[-1].nodes
        if tos_nodes:
            last_leaf = tos_nodes[-1].get_last_leaf()
        else:
            last_leaf = None

        if self._start_nonterminal == 'file_input' and \
                (token.type == PythonTokenTypes.ENDMARKER
                 or token.type == DEDENT and not last_leaf.value.endswith('\n')
                 and not last_leaf.value.endswith('\r')):
            # In Python statements need to end with a newline. But since it's
            # possible (and valid in Python) that there's no newline at the
            # end of a file, we have to recover even if the user doesn't want
            # error recovery.
            if self.stack[-1].dfa.from_rule == 'simple_stmt':
                try:
                    plan = self.stack[-1].dfa.transitions[PythonTokenTypes.NEWLINE]
                except KeyError:
                    pass
                else:
                    if plan.next_dfa.is_final and not plan.dfa_pushes:
                        # We are ignoring here that the newline would be
                        # required for a simple_stmt.
                        self.stack[-1].dfa = plan.next_dfa
                        self._add_token(token)
                        return

        if not self._error_recovery:
            return super().error_recovery(token)

        def current_suite(stack):
            # For now just discard everything that is not a suite or
            # file_input, if we detect an error.
            for until_index, stack_node in reversed(list(enumerate(stack))):
                # `suite` can sometimes be only simple_stmt, not stmt.
                if stack_node.nonterminal == 'file_input':
                    break
                elif stack_node.nonterminal == 'suite':
                    # In the case where we just have a newline we don't want to
                    # do error recovery here. In all other cases, we want to do
                    # error recovery.
                    if len(stack_node.nodes) != 1:
                        break
            return until_index

        until_index = current_suite(self.stack)

        if self._stack_removal(until_index + 1):
            self._add_token(token)
        else:
            typ, value, start_pos, prefix = token
            if typ == INDENT:
                # For every deleted INDENT we have to delete a DEDENT as well.
                # Otherwise the parser will get into trouble and DEDENT too early.
                self._omit_dedent_list.append(self._indent_counter)

            error_leaf = tree.PythonErrorLeaf(typ.name, value, start_pos, prefix)
            self.stack[-1].nodes.append(error_leaf)

        tos = self.stack[-1]
        if tos.nonterminal == 'suite':
            # Need at least one statement in the suite. This happend with the
            # error recovery above.
            try:
                tos.dfa = tos.dfa.arcs['stmt']
            except KeyError:
                # We're already in a final state.
                pass

    def _stack_removal(self, start_index):
        all_nodes = [node for stack_node in self.stack[start_index:] for node in stack_node.nodes]

        if all_nodes:
            node = tree.PythonErrorNode(all_nodes)
            self.stack[start_index - 1].nodes.append(node)

        self.stack[start_index:] = []
        return bool(all_nodes)

    def _recovery_tokenize(self, tokens):
        for token in tokens:
            typ = token[0]
            if typ == DEDENT:
                # We need to count indents, because if we just omit any DEDENT,
                # we might omit them in the wrong place.
                o = self._omit_dedent_list
                if o and o[-1] == self._indent_counter:
                    o.pop()
                    self._indent_counter -= 1
                    continue

                self._indent_counter -= 1
            elif typ == INDENT:
                self._indent_counter += 1
            yield token

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\key_binding\bindings\completion.py ===
"""
Key binding handlers for displaying completions.
"""

from __future__ import annotations

import asyncio
import math
from typing import TYPE_CHECKING

from prompt_toolkit.application.run_in_terminal import in_terminal
from prompt_toolkit.completion import (
    CompleteEvent,
    Completion,
    get_common_complete_suffix,
)
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.utils import get_cwidth

if TYPE_CHECKING:
    from prompt_toolkit.application import Application
    from prompt_toolkit.shortcuts import PromptSession

__all__ = [
    "generate_completions",
    "display_completions_like_readline",
]

E = KeyPressEvent


def generate_completions(event: E) -> None:
    r"""
    Tab-completion: where the first tab completes the common suffix and the
    second tab lists all the completions.
    """
    b = event.current_buffer

    # When already navigating through completions, select the next one.
    if b.complete_state:
        b.complete_next()
    else:
        b.start_completion(insert_common_part=True)


def display_completions_like_readline(event: E) -> None:
    """
    Key binding handler for readline-style tab completion.
    This is meant to be as similar as possible to the way how readline displays
    completions.

    Generate the completions immediately (blocking) and display them above the
    prompt in columns.

    Usage::

        # Call this handler when 'Tab' has been pressed.
        key_bindings.add(Keys.ControlI)(display_completions_like_readline)
    """
    # Request completions.
    b = event.current_buffer
    if b.completer is None:
        return
    complete_event = CompleteEvent(completion_requested=True)
    completions = list(b.completer.get_completions(b.document, complete_event))

    # Calculate the common suffix.
    common_suffix = get_common_complete_suffix(b.document, completions)

    # One completion: insert it.
    if len(completions) == 1:
        b.delete_before_cursor(-completions[0].start_position)
        b.insert_text(completions[0].text)
    # Multiple completions with common part.
    elif common_suffix:
        b.insert_text(common_suffix)
    # Otherwise: display all completions.
    elif completions:
        _display_completions_like_readline(event.app, completions)


def _display_completions_like_readline(
    app: Application[object], completions: list[Completion]
) -> asyncio.Task[None]:
    """
    Display the list of completions in columns above the prompt.
    This will ask for a confirmation if there are too many completions to fit
    on a single page and provide a paginator to walk through them.
    """
    from prompt_toolkit.formatted_text import to_formatted_text
    from prompt_toolkit.shortcuts.prompt import create_confirm_session

    # Get terminal dimensions.
    term_size = app.output.get_size()
    term_width = term_size.columns
    term_height = term_size.rows

    # Calculate amount of required columns/rows for displaying the
    # completions. (Keep in mind that completions are displayed
    # alphabetically column-wise.)
    max_compl_width = min(
        term_width, max(get_cwidth(c.display_text) for c in completions) + 1
    )
    column_count = max(1, term_width // max_compl_width)
    completions_per_page = column_count * (term_height - 1)
    page_count = int(math.ceil(len(completions) / float(completions_per_page)))
    # Note: math.ceil can return float on Python2.

    def display(page: int) -> None:
        # Display completions.
        page_completions = completions[
            page * completions_per_page : (page + 1) * completions_per_page
        ]

        page_row_count = int(math.ceil(len(page_completions) / float(column_count)))
        page_columns = [
            page_completions[i * page_row_count : (i + 1) * page_row_count]
            for i in range(column_count)
        ]

        result: StyleAndTextTuples = []

        for r in range(page_row_count):
            for c in range(column_count):
                try:
                    completion = page_columns[c][r]
                    style = "class:readline-like-completions.completion " + (
                        completion.style or ""
                    )

                    result.extend(to_formatted_text(completion.display, style=style))

                    # Add padding.
                    padding = max_compl_width - get_cwidth(completion.display_text)
                    result.append((completion.style, " " * padding))
                except IndexError:
                    pass
            result.append(("", "\n"))

        app.print_text(to_formatted_text(result, "class:readline-like-completions"))

    # User interaction through an application generator function.
    async def run_compl() -> None:
        "Coroutine."
        async with in_terminal(render_cli_done=True):
            if len(completions) > completions_per_page:
                # Ask confirmation if it doesn't fit on the screen.
                confirm = await create_confirm_session(
                    f"Display all {len(completions)} possibilities?",
                ).prompt_async()

                if confirm:
                    # Display pages.
                    for page in range(page_count):
                        display(page)

                        if page != page_count - 1:
                            # Display --MORE-- and go to the next page.
                            show_more = await _create_more_session(
                                "--MORE--"
                            ).prompt_async()

                            if not show_more:
                                return
                else:
                    app.output.flush()
            else:
                # Display all completions.
                display(0)

    return app.create_background_task(run_compl())


def _create_more_session(message: str = "--MORE--") -> PromptSession[bool]:
    """
    Create a `PromptSession` object for displaying the "--MORE--".
    """
    from prompt_toolkit.shortcuts import PromptSession

    bindings = KeyBindings()

    @bindings.add(" ")
    @bindings.add("y")
    @bindings.add("Y")
    @bindings.add(Keys.ControlJ)
    @bindings.add(Keys.ControlM)
    @bindings.add(Keys.ControlI)  # Tab.
    def _yes(event: E) -> None:
        event.app.exit(result=True)

    @bindings.add("n")
    @bindings.add("N")
    @bindings.add("q")
    @bindings.add("Q")
    @bindings.add(Keys.ControlC)
    def _no(event: E) -> None:
        event.app.exit(result=False)

    @bindings.add(Keys.Any)
    def _ignore(event: E) -> None:
        "Disable inserting of text."

    return PromptSession(message, key_bindings=bindings, erase_when_done=True)

# === NexusCore/openenv\Lib\site-packages\google\protobuf\service.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""DEPRECATED:  Declares the RPC service interfaces.

This module declares the abstract interfaces underlying proto2 RPC
services.  These are intended to be independent of any particular RPC
implementation, so that proto2 services can be used on top of a variety
of implementations.  Starting with version 2.3.0, RPC implementations should
not try to build on these, but should instead provide code generator plugins
which generate code specific to the particular RPC implementation.  This way
the generated code can be more appropriate for the implementation in use
and can avoid unnecessary layers of indirection.
"""

__author__ = 'petar@google.com (Petar Petrov)'


class RpcException(Exception):
  """Exception raised on failed blocking RPC method call."""
  pass


class Service(object):

  """Abstract base interface for protocol-buffer-based RPC services.

  Services themselves are abstract classes (implemented either by servers or as
  stubs), but they subclass this base interface. The methods of this
  interface can be used to call the methods of the service without knowing
  its exact type at compile time (analogous to the Message interface).
  """

  def GetDescriptor():
    """Retrieves this service's descriptor."""
    raise NotImplementedError

  def CallMethod(self, method_descriptor, rpc_controller,
                 request, done):
    """Calls a method of the service specified by method_descriptor.

    If "done" is None then the call is blocking and the response
    message will be returned directly.  Otherwise the call is asynchronous
    and "done" will later be called with the response value.

    In the blocking case, RpcException will be raised on error.

    Preconditions:

    * method_descriptor.service == GetDescriptor
    * request is of the exact same classes as returned by
      GetRequestClass(method).
    * After the call has started, the request must not be modified.
    * "rpc_controller" is of the correct type for the RPC implementation being
      used by this Service.  For stubs, the "correct type" depends on the
      RpcChannel which the stub is using.

    Postconditions:

    * "done" will be called when the method is complete.  This may be
      before CallMethod() returns or it may be at some point in the future.
    * If the RPC failed, the response value passed to "done" will be None.
      Further details about the failure can be found by querying the
      RpcController.
    """
    raise NotImplementedError

  def GetRequestClass(self, method_descriptor):
    """Returns the class of the request message for the specified method.

    CallMethod() requires that the request is of a particular subclass of
    Message. GetRequestClass() gets the default instance of this required
    type.

    Example:
      method = service.GetDescriptor().FindMethodByName("Foo")
      request = stub.GetRequestClass(method)()
      request.ParseFromString(input)
      service.CallMethod(method, request, callback)
    """
    raise NotImplementedError

  def GetResponseClass(self, method_descriptor):
    """Returns the class of the response message for the specified method.

    This method isn't really needed, as the RpcChannel's CallMethod constructs
    the response protocol message. It's provided anyway in case it is useful
    for the caller to know the response type in advance.
    """
    raise NotImplementedError


class RpcController(object):

  """An RpcController mediates a single method call.

  The primary purpose of the controller is to provide a way to manipulate
  settings specific to the RPC implementation and to find out about RPC-level
  errors. The methods provided by the RpcController interface are intended
  to be a "least common denominator" set of features which we expect all
  implementations to support.  Specific implementations may provide more
  advanced features (e.g. deadline propagation).
  """

  # Client-side methods below

  def Reset(self):
    """Resets the RpcController to its initial state.

    After the RpcController has been reset, it may be reused in
    a new call. Must not be called while an RPC is in progress.
    """
    raise NotImplementedError

  def Failed(self):
    """Returns true if the call failed.

    After a call has finished, returns true if the call failed.  The possible
    reasons for failure depend on the RPC implementation.  Failed() must not
    be called before a call has finished.  If Failed() returns true, the
    contents of the response message are undefined.
    """
    raise NotImplementedError

  def ErrorText(self):
    """If Failed is true, returns a human-readable description of the error."""
    raise NotImplementedError

  def StartCancel(self):
    """Initiate cancellation.

    Advises the RPC system that the caller desires that the RPC call be
    canceled.  The RPC system may cancel it immediately, may wait awhile and
    then cancel it, or may not even cancel the call at all.  If the call is
    canceled, the "done" callback will still be called and the RpcController
    will indicate that the call failed at that time.
    """
    raise NotImplementedError

  # Server-side methods below

  def SetFailed(self, reason):
    """Sets a failure reason.

    Causes Failed() to return true on the client side.  "reason" will be
    incorporated into the message returned by ErrorText().  If you find
    you need to return machine-readable information about failures, you
    should incorporate it into your response protocol buffer and should
    NOT call SetFailed().
    """
    raise NotImplementedError

  def IsCanceled(self):
    """Checks if the client cancelled the RPC.

    If true, indicates that the client canceled the RPC, so the server may
    as well give up on replying to it.  The server should still call the
    final "done" callback.
    """
    raise NotImplementedError

  def NotifyOnCancel(self, callback):
    """Sets a callback to invoke on cancel.

    Asks that the given callback be called when the RPC is canceled.  The
    callback will always be called exactly once.  If the RPC completes without
    being canceled, the callback will be called after completion.  If the RPC
    has already been canceled when NotifyOnCancel() is called, the callback
    will be called immediately.

    NotifyOnCancel() must be called no more than once per request.
    """
    raise NotImplementedError


class RpcChannel(object):

  """Abstract interface for an RPC channel.

  An RpcChannel represents a communication line to a service which can be used
  to call that service's methods.  The service may be running on another
  machine. Normally, you should not use an RpcChannel directly, but instead
  construct a stub {@link Service} wrapping it.  Example:

  Example:
    RpcChannel channel = rpcImpl.Channel("remotehost.example.com:1234")
    RpcController controller = rpcImpl.Controller()
    MyService service = MyService_Stub(channel)
    service.MyMethod(controller, request, callback)
  """

  def CallMethod(self, method_descriptor, rpc_controller,
                 request, response_class, done):
    """Calls the method identified by the descriptor.

    Call the given method of the remote service.  The signature of this
    procedure looks the same as Service.CallMethod(), but the requirements
    are less strict in one important way:  the request object doesn't have to
    be of any specific class as long as its descriptor is method.input_type.
    """
    raise NotImplementedError

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_providers\__init__.py ===
from typing import Dict, Literal, Optional, Union

from huggingface_hub.inference._providers.featherless_ai import (
    FeatherlessConversationalTask,
    FeatherlessTextGenerationTask,
)
from huggingface_hub.utils import logging

from ._common import TaskProviderHelper, _fetch_inference_provider_mapping
from .black_forest_labs import BlackForestLabsTextToImageTask
from .cerebras import CerebrasConversationalTask
from .cohere import CohereConversationalTask
from .fal_ai import (
    FalAIAutomaticSpeechRecognitionTask,
    FalAITextToImageTask,
    FalAITextToSpeechTask,
    FalAITextToVideoTask,
)
from .fireworks_ai import FireworksAIConversationalTask
from .groq import GroqConversationalTask
from .hf_inference import (
    HFInferenceBinaryInputTask,
    HFInferenceConversational,
    HFInferenceFeatureExtractionTask,
    HFInferenceTask,
)
from .hyperbolic import HyperbolicTextGenerationTask, HyperbolicTextToImageTask
from .nebius import (
    NebiusConversationalTask,
    NebiusFeatureExtractionTask,
    NebiusTextGenerationTask,
    NebiusTextToImageTask,
)
from .novita import NovitaConversationalTask, NovitaTextGenerationTask, NovitaTextToVideoTask
from .nscale import NscaleConversationalTask, NscaleTextToImageTask
from .openai import OpenAIConversationalTask
from .replicate import ReplicateTask, ReplicateTextToImageTask, ReplicateTextToSpeechTask
from .sambanova import SambanovaConversationalTask, SambanovaFeatureExtractionTask
from .together import TogetherConversationalTask, TogetherTextGenerationTask, TogetherTextToImageTask


logger = logging.get_logger(__name__)


PROVIDER_T = Literal[
    "black-forest-labs",
    "cerebras",
    "cohere",
    "fal-ai",
    "featherless-ai",
    "fireworks-ai",
    "groq",
    "hf-inference",
    "hyperbolic",
    "nebius",
    "novita",
    "nscale",
    "openai",
    "replicate",
    "sambanova",
    "together",
]

PROVIDER_OR_POLICY_T = Union[PROVIDER_T, Literal["auto"]]

PROVIDERS: Dict[PROVIDER_T, Dict[str, TaskProviderHelper]] = {
    "black-forest-labs": {
        "text-to-image": BlackForestLabsTextToImageTask(),
    },
    "cerebras": {
        "conversational": CerebrasConversationalTask(),
    },
    "cohere": {
        "conversational": CohereConversationalTask(),
    },
    "fal-ai": {
        "automatic-speech-recognition": FalAIAutomaticSpeechRecognitionTask(),
        "text-to-image": FalAITextToImageTask(),
        "text-to-speech": FalAITextToSpeechTask(),
        "text-to-video": FalAITextToVideoTask(),
    },
    "featherless-ai": {
        "conversational": FeatherlessConversationalTask(),
        "text-generation": FeatherlessTextGenerationTask(),
    },
    "fireworks-ai": {
        "conversational": FireworksAIConversationalTask(),
    },
    "groq": {
        "conversational": GroqConversationalTask(),
    },
    "hf-inference": {
        "text-to-image": HFInferenceTask("text-to-image"),
        "conversational": HFInferenceConversational(),
        "text-generation": HFInferenceTask("text-generation"),
        "text-classification": HFInferenceTask("text-classification"),
        "question-answering": HFInferenceTask("question-answering"),
        "audio-classification": HFInferenceBinaryInputTask("audio-classification"),
        "automatic-speech-recognition": HFInferenceBinaryInputTask("automatic-speech-recognition"),
        "fill-mask": HFInferenceTask("fill-mask"),
        "feature-extraction": HFInferenceFeatureExtractionTask(),
        "image-classification": HFInferenceBinaryInputTask("image-classification"),
        "image-segmentation": HFInferenceBinaryInputTask("image-segmentation"),
        "document-question-answering": HFInferenceTask("document-question-answering"),
        "image-to-text": HFInferenceBinaryInputTask("image-to-text"),
        "object-detection": HFInferenceBinaryInputTask("object-detection"),
        "audio-to-audio": HFInferenceBinaryInputTask("audio-to-audio"),
        "zero-shot-image-classification": HFInferenceBinaryInputTask("zero-shot-image-classification"),
        "zero-shot-classification": HFInferenceTask("zero-shot-classification"),
        "image-to-image": HFInferenceBinaryInputTask("image-to-image"),
        "sentence-similarity": HFInferenceTask("sentence-similarity"),
        "table-question-answering": HFInferenceTask("table-question-answering"),
        "tabular-classification": HFInferenceTask("tabular-classification"),
        "text-to-speech": HFInferenceTask("text-to-speech"),
        "token-classification": HFInferenceTask("token-classification"),
        "translation": HFInferenceTask("translation"),
        "summarization": HFInferenceTask("summarization"),
        "visual-question-answering": HFInferenceBinaryInputTask("visual-question-answering"),
    },
    "hyperbolic": {
        "text-to-image": HyperbolicTextToImageTask(),
        "conversational": HyperbolicTextGenerationTask("conversational"),
        "text-generation": HyperbolicTextGenerationTask("text-generation"),
    },
    "nebius": {
        "text-to-image": NebiusTextToImageTask(),
        "conversational": NebiusConversationalTask(),
        "text-generation": NebiusTextGenerationTask(),
        "feature-extraction": NebiusFeatureExtractionTask(),
    },
    "novita": {
        "text-generation": NovitaTextGenerationTask(),
        "conversational": NovitaConversationalTask(),
        "text-to-video": NovitaTextToVideoTask(),
    },
    "nscale": {
        "conversational": NscaleConversationalTask(),
        "text-to-image": NscaleTextToImageTask(),
    },
    "openai": {
        "conversational": OpenAIConversationalTask(),
    },
    "replicate": {
        "text-to-image": ReplicateTextToImageTask(),
        "text-to-speech": ReplicateTextToSpeechTask(),
        "text-to-video": ReplicateTask("text-to-video"),
    },
    "sambanova": {
        "conversational": SambanovaConversationalTask(),
        "feature-extraction": SambanovaFeatureExtractionTask(),
    },
    "together": {
        "text-to-image": TogetherTextToImageTask(),
        "conversational": TogetherConversationalTask(),
        "text-generation": TogetherTextGenerationTask(),
    },
}


def get_provider_helper(
    provider: Optional[PROVIDER_OR_POLICY_T], task: str, model: Optional[str]
) -> TaskProviderHelper:
    """Get provider helper instance by name and task.

    Args:
        provider (`str`, *optional*): name of the provider, or "auto" to automatically select the provider for the model.
        task (`str`): Name of the task
        model (`str`, *optional*): Name of the model
    Returns:
        TaskProviderHelper: Helper instance for the specified provider and task

    Raises:
        ValueError: If provider or task is not supported
    """

    if (model is None and provider in (None, "auto")) or (
        model is not None and model.startswith(("http://", "https://"))
    ):
        provider = "hf-inference"

    if provider is None:
        logger.info(
            "Defaulting to 'auto' which will select the first provider available for the model, sorted by the user's order in https://hf.co/settings/inference-providers."
        )
        provider = "auto"

    if provider == "auto":
        if model is None:
            raise ValueError("Specifying a model is required when provider is 'auto'")
        provider_mapping = _fetch_inference_provider_mapping(model)
        provider = next(iter(provider_mapping)).provider

    provider_tasks = PROVIDERS.get(provider)  # type: ignore
    if provider_tasks is None:
        raise ValueError(
            f"Provider '{provider}' not supported. Available values: 'auto' or any provider from {list(PROVIDERS.keys())}."
            "Passing 'auto' (default value) will automatically select the first provider available for the model, sorted "
            "by the user's order in https://hf.co/settings/inference-providers."
        )

    if task not in provider_tasks:
        raise ValueError(
            f"Task '{task}' not supported for provider '{provider}'. Available tasks: {list(provider_tasks.keys())}"
        )
    return provider_tasks[task]

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\db\prisma_client.py ===
"""
This file contains the PrismaWrapper class, which is used to wrap the Prisma client and handle the RDS IAM token.
"""

import asyncio
import os
import random
import subprocess
import time
import urllib
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Optional, Union

from litellm._logging import verbose_proxy_logger
from litellm.secret_managers.main import str_to_bool


class PrismaWrapper:
    def __init__(self, original_prisma: Any, iam_token_db_auth: bool):
        self._original_prisma = original_prisma
        self.iam_token_db_auth = iam_token_db_auth

    def is_token_expired(self, token_url: Optional[str]) -> bool:
        if token_url is None:
            return True
        # Decode the token URL to handle URL-encoded characters
        decoded_url = urllib.parse.unquote(token_url)

        # Parse the token URL
        parsed_url = urllib.parse.urlparse(decoded_url)

        # Parse the query parameters from the path component (if they exist there)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Get expiration time from the query parameters
        expires = query_params.get("X-Amz-Expires", [None])[0]
        if expires is None:
            raise ValueError("X-Amz-Expires parameter is missing or invalid.")

        expires_int = int(expires)

        # Get the token's creation time from the X-Amz-Date parameter
        token_time_str = query_params.get("X-Amz-Date", [""])[0]
        if not token_time_str:
            raise ValueError("X-Amz-Date parameter is missing or invalid.")

        # Ensure the token time string is parsed correctly
        try:
            token_time = datetime.strptime(token_time_str, "%Y%m%dT%H%M%SZ")
        except ValueError as e:
            raise ValueError(f"Invalid X-Amz-Date format: {e}")

        # Calculate the expiration time
        expiration_time = token_time + timedelta(seconds=expires_int)

        # Current time in UTC
        current_time = datetime.utcnow()

        # Check if the token is expired
        return current_time > expiration_time

    def get_rds_iam_token(self) -> Optional[str]:
        if self.iam_token_db_auth:
            from litellm.proxy.auth.rds_iam_token import generate_iam_auth_token

            db_host = os.getenv("DATABASE_HOST")
            db_port = os.getenv("DATABASE_PORT")
            db_user = os.getenv("DATABASE_USER")
            db_name = os.getenv("DATABASE_NAME")
            db_schema = os.getenv("DATABASE_SCHEMA")

            token = generate_iam_auth_token(
                db_host=db_host, db_port=db_port, db_user=db_user
            )

            # print(f"token: {token}")
            _db_url = f"postgresql://{db_user}:{token}@{db_host}:{db_port}/{db_name}"
            if db_schema:
                _db_url += f"?schema={db_schema}"

            os.environ["DATABASE_URL"] = _db_url
            return _db_url
        return None

    async def recreate_prisma_client(
        self, new_db_url: str, http_client: Optional[Any] = None
    ):
        from prisma import Prisma  # type: ignore

        if http_client is not None:
            self._original_prisma = Prisma(http=http_client)
        else:
            self._original_prisma = Prisma()

        await self._original_prisma.connect()

    def __getattr__(self, name: str):
        original_attr = getattr(self._original_prisma, name)
        if self.iam_token_db_auth:
            db_url = os.getenv("DATABASE_URL")
            if self.is_token_expired(db_url):
                db_url = self.get_rds_iam_token()
                loop = asyncio.get_event_loop()

                if db_url:
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            self.recreate_prisma_client(db_url), loop
                        )
                    else:
                        asyncio.run(self.recreate_prisma_client(db_url))
                else:
                    raise ValueError("Failed to get RDS IAM token")

        return original_attr


class PrismaManager:
    @staticmethod
    def _get_prisma_dir() -> str:
        """Get the path to the migrations directory"""
        abspath = os.path.abspath(__file__)
        dname = os.path.dirname(os.path.dirname(abspath))
        return dname

    @staticmethod
    def setup_database(use_migrate: bool = False) -> bool:
        """
        Set up the database using either prisma migrate or prisma db push

        Returns:
            bool: True if setup was successful, False otherwise
        """

        use_migrate = str_to_bool(os.getenv("USE_PRISMA_MIGRATE")) or use_migrate
        for attempt in range(4):
            original_dir = os.getcwd()
            prisma_dir = PrismaManager._get_prisma_dir()
            os.chdir(prisma_dir)
            try:
                if use_migrate:
                    try:
                        from litellm_proxy_extras.utils import ProxyExtrasDBManager
                    except ImportError as e:
                        verbose_proxy_logger.error(
                            f"\033[1;31mLiteLLM: Failed to import proxy extras. Got {e}\033[0m"
                        )
                        return False

                    prisma_dir = PrismaManager._get_prisma_dir()

                    return ProxyExtrasDBManager.setup_database(use_migrate=use_migrate)
                else:
                    # Use prisma db push with increased timeout
                    subprocess.run(
                        ["prisma", "db", "push", "--accept-data-loss"],
                        timeout=60,
                        check=True,
                    )
                    return True
            except subprocess.TimeoutExpired:
                verbose_proxy_logger.warning(f"Attempt {attempt + 1} timed out")
                time.sleep(random.randrange(5, 15))
            except subprocess.CalledProcessError as e:
                attempts_left = 3 - attempt
                retry_msg = (
                    f" Retrying... ({attempts_left} attempts left)"
                    if attempts_left > 0
                    else ""
                )
                verbose_proxy_logger.warning(
                    f"The process failed to execute. Details: {e}.{retry_msg}"
                )
                time.sleep(random.randrange(5, 15))
            finally:
                os.chdir(original_dir)
        return False


def should_update_prisma_schema(
    disable_updates: Optional[Union[bool, str]] = None
) -> bool:
    """
    Determines if Prisma Schema updates should be applied during startup.

    Args:
        disable_updates: Controls whether schema updates are disabled.
            Accepts boolean or string ('true'/'false'). Defaults to checking DISABLE_SCHEMA_UPDATE env var.

    Returns:
        bool: True if schema updates should be applied, False if updates are disabled.

    Examples:
        >>> should_update_prisma_schema()  # Checks DISABLE_SCHEMA_UPDATE env var
        >>> should_update_prisma_schema(True)  # Explicitly disable updates
        >>> should_update_prisma_schema("false")  # Enable updates using string
    """
    if disable_updates is None:
        disable_updates = os.getenv("DISABLE_SCHEMA_UPDATE", "false")

    if isinstance(disable_updates, str):
        disable_updates = str_to_bool(disable_updates)

    return not bool(disable_updates)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\guardrails\guardrail_hooks\lasso.py ===
# +-------------------------------------------------------------+
#
#           Use Lasso Security Guardrails for your LLM calls
#                   https://www.lasso.security/
#
# +-------------------------------------------------------------+

import os
from typing import Any, Dict, List, Literal, Optional, Union

from fastapi import HTTPException

from litellm import DualCache
from litellm._logging import verbose_proxy_logger
from litellm.integrations.custom_guardrail import (
    CustomGuardrail,
    log_guardrail_information,
)
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.proxy._types import UserAPIKeyAuth


class LassoGuardrailMissingSecrets(Exception):
    pass


class LassoGuardrailAPIError(Exception):
    """Exception raised when there's an error calling the Lasso API."""

    pass


class LassoGuardrail(CustomGuardrail):
    def __init__(
        self,
        lasso_api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        **kwargs,
    ):
        self.async_handler = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.GuardrailCallback
        )
        self.lasso_api_key = lasso_api_key or os.environ.get("LASSO_API_KEY")
        self.user_id = user_id or os.environ.get("LASSO_USER_ID")
        self.conversation_id = conversation_id or os.environ.get(
            "LASSO_CONVERSATION_ID"
        )

        if self.lasso_api_key is None:
            msg = (
                "Couldn't get Lasso api key, either set the `LASSO_API_KEY` in the environment or "
                "pass it as a parameter to the guardrail in the config file"
            )
            raise LassoGuardrailMissingSecrets(msg)

        self.api_base = api_base or "https://server.lasso.security/gateway/v2/classify"
        super().__init__(**kwargs)

    @log_guardrail_information
    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
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
    ) -> Union[Exception, str, dict, None]:
        verbose_proxy_logger.debug("Inside Lasso Pre-Call Hook")
        return await self.run_lasso_guardrail(data)

    @log_guardrail_information
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
        """
        This is used for during_call moderation
        """
        verbose_proxy_logger.debug("Inside Lasso Moderation Hook")
        return await self.run_lasso_guardrail(data)

    async def run_lasso_guardrail(
        self,
        data: dict,
    ):
        """
        Run the Lasso guardrail

        Raises:
            LassoGuardrailAPIError: If the Lasso API call fails
        """
        messages: List[Dict[str, str]] = data.get("messages", [])
        # check if messages are present
        if not messages:
            return data

        try:
            headers = self._prepare_headers()
            payload = self._prepare_payload(messages)

            response = await self._call_lasso_api(
                headers=headers,
                payload=payload,
            )
            self._process_lasso_response(response)

            return data
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            verbose_proxy_logger.error(f"Error calling Lasso API: {str(e)}")
            # Instead of allowing the request to proceed, raise an exception
            raise LassoGuardrailAPIError(
                f"Failed to verify request safety with Lasso API: {str(e)}"
            )

    def _prepare_headers(self) -> dict[str, str]:
        """Prepare headers for the Lasso API request."""
        if not self.lasso_api_key:
            msg = (
                "Couldn't get Lasso api key, either set the `LASSO_API_KEY` in the environment or "
                "pass it as a parameter to the guardrail in the config file"
            )
            raise LassoGuardrailMissingSecrets(msg)

        headers: dict[str, str] = {
            "lasso-api-key": self.lasso_api_key,
            "Content-Type": "application/json",
        }

        # Add optional headers if provided
        if self.user_id:
            headers["lasso-user-id"] = self.user_id

        if self.conversation_id:
            headers["lasso-conversation-id"] = self.conversation_id

        return headers

    def _prepare_payload(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Prepare the payload for the Lasso API request."""
        return {"messages": messages}

    async def _call_lasso_api(
        self, headers: Dict[str, str], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call the Lasso API and return the response."""
        verbose_proxy_logger.debug(f"Sending request to Lasso API: {payload}")
        response = await self.async_handler.post(
            url=self.api_base,
            headers=headers,
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        res = response.json()
        verbose_proxy_logger.debug(f"Lasso API response: {res}")
        return res

    def _process_lasso_response(self, response: Dict[str, Any]) -> None:
        """Process the Lasso API response and raise exceptions if violations are detected."""
        if response and response.get("violations_detected") is True:
            violated_deputies = self._parse_violated_deputies(response)
            verbose_proxy_logger.warning(
                f"Lasso guardrail detected violations: {violated_deputies}"
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Violated Lasso guardrail policy",
                    "detection_message": f"Guardrail violations detected: {', '.join(violated_deputies)}",
                    "lasso_response": response,
                },
            )

    def _parse_violated_deputies(self, response: Dict[str, Any]) -> List[str]:
        """Parse the response to extract violated deputies."""
        violated_deputies = []
        if "deputies" in response:
            for deputy, is_violated in response["deputies"].items():
                if is_violated:
                    violated_deputies.append(deputy)
        return violated_deputies

# === NexusCore/openenv\Lib\site-packages\nltk\chunk\__init__.py ===
# Natural Language Toolkit: Chunkers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Classes and interfaces for identifying non-overlapping linguistic
groups (such as base noun phrases) in unrestricted text.  This task is
called "chunk parsing" or "chunking", and the identified groups are
called "chunks".  The chunked text is represented using a shallow
tree called a "chunk structure."  A chunk structure is a tree
containing tokens and chunks, where each chunk is a subtree containing
only tokens.  For example, the chunk structure for base noun phrase
chunks in the sentence "I saw the big dog on the hill" is::

  (SENTENCE:
    (NP: <I>)
    <saw>
    (NP: <the> <big> <dog>)
    <on>
    (NP: <the> <hill>))

To convert a chunk structure back to a list of tokens, simply use the
chunk structure's ``leaves()`` method.

This module defines ``ChunkParserI``, a standard interface for
chunking texts; and ``RegexpChunkParser``, a regular-expression based
implementation of that interface. It also defines ``ChunkScore``, a
utility class for scoring chunk parsers.

RegexpChunkParser
=================

``RegexpChunkParser`` is an implementation of the chunk parser interface
that uses regular-expressions over tags to chunk a text.  Its
``parse()`` method first constructs a ``ChunkString``, which encodes a
particular chunking of the input text.  Initially, nothing is
chunked.  ``parse.RegexpChunkParser`` then applies a sequence of
``RegexpChunkRule`` rules to the ``ChunkString``, each of which modifies
the chunking that it encodes.  Finally, the ``ChunkString`` is
transformed back into a chunk structure, which is returned.

``RegexpChunkParser`` can only be used to chunk a single kind of phrase.
For example, you can use an ``RegexpChunkParser`` to chunk the noun
phrases in a text, or the verb phrases in a text; but you can not
use it to simultaneously chunk both noun phrases and verb phrases in
the same text.  (This is a limitation of ``RegexpChunkParser``, not of
chunk parsers in general.)

RegexpChunkRules
----------------

A ``RegexpChunkRule`` is a transformational rule that updates the
chunking of a text by modifying its ``ChunkString``.  Each
``RegexpChunkRule`` defines the ``apply()`` method, which modifies
the chunking encoded by a ``ChunkString``.  The
``RegexpChunkRule`` class itself can be used to implement any
transformational rule based on regular expressions.  There are
also a number of subclasses, which can be used to implement
simpler types of rules:

    - ``ChunkRule`` chunks anything that matches a given regular
      expression.
    - ``StripRule`` strips anything that matches a given regular
      expression.
    - ``UnChunkRule`` will un-chunk any chunk that matches a given
      regular expression.
    - ``MergeRule`` can be used to merge two contiguous chunks.
    - ``SplitRule`` can be used to split a single chunk into two
      smaller chunks.
    - ``ExpandLeftRule`` will expand a chunk to incorporate new
      unchunked material on the left.
    - ``ExpandRightRule`` will expand a chunk to incorporate new
      unchunked material on the right.

Tag Patterns
~~~~~~~~~~~~

A ``RegexpChunkRule`` uses a modified version of regular
expression patterns, called "tag patterns".  Tag patterns are
used to match sequences of tags.  Examples of tag patterns are::

     r'(<DT>|<JJ>|<NN>)+'
     r'<NN>+'
     r'<NN.*>'

The differences between regular expression patterns and tag
patterns are:

    - In tag patterns, ``'<'`` and ``'>'`` act as parentheses; so
      ``'<NN>+'`` matches one or more repetitions of ``'<NN>'``, not
      ``'<NN'`` followed by one or more repetitions of ``'>'``.
    - Whitespace in tag patterns is ignored.  So
      ``'<DT> | <NN>'`` is equivalent to ``'<DT>|<NN>'``
    - In tag patterns, ``'.'`` is equivalent to ``'[^{}<>]'``; so
      ``'<NN.*>'`` matches any single tag starting with ``'NN'``.

The function ``tag_pattern2re_pattern`` can be used to transform
a tag pattern to an equivalent regular expression pattern.

Efficiency
----------

Preliminary tests indicate that ``RegexpChunkParser`` can chunk at a
rate of about 300 tokens/second, with a moderately complex rule set.

There may be problems if ``RegexpChunkParser`` is used with more than
5,000 tokens at a time.  In particular, evaluation of some regular
expressions may cause the Python regular expression engine to
exceed its maximum recursion depth.  We have attempted to minimize
these problems, but it is impossible to avoid them completely.  We
therefore recommend that you apply the chunk parser to a single
sentence at a time.

Emacs Tip
---------

If you evaluate the following elisp expression in emacs, it will
colorize a ``ChunkString`` when you use an interactive python shell
with emacs or xemacs ("C-c !")::

    (let ()
      (defconst comint-mode-font-lock-keywords
        '(("<[^>]+>" 0 'font-lock-reference-face)
          ("[{}]" 0 'font-lock-function-name-face)))
      (add-hook 'comint-mode-hook (lambda () (turn-on-font-lock))))

You can evaluate this code by copying it to a temporary buffer,
placing the cursor after the last close parenthesis, and typing
"``C-x C-e``".  You should evaluate it before running the interactive
session.  The change will last until you close emacs.

Unresolved Issues
-----------------

If we use the ``re`` module for regular expressions, Python's
regular expression engine generates "maximum recursion depth
exceeded" errors when processing very large texts, even for
regular expressions that should not require any recursion.  We
therefore use the ``pre`` module instead.  But note that ``pre``
does not include Unicode support, so this module will not work
with unicode strings.  Note also that ``pre`` regular expressions
are not quite as advanced as ``re`` ones (e.g., no leftward
zero-length assertions).

:type CHUNK_TAG_PATTERN: regexp
:var CHUNK_TAG_PATTERN: A regular expression to test whether a tag
     pattern is valid.
"""

from nltk.chunk.api import ChunkParserI
from nltk.chunk.named_entity import Maxent_NE_Chunker
from nltk.chunk.regexp import RegexpChunkParser, RegexpParser
from nltk.chunk.util import (
    ChunkScore,
    accuracy,
    conllstr2tree,
    conlltags2tree,
    ieerstr2tree,
    tagstr2tree,
    tree2conllstr,
    tree2conlltags,
)


def ne_chunker(fmt="multiclass"):
    """
    Load NLTK's currently recommended named entity chunker.
    """
    return Maxent_NE_Chunker(fmt)


def ne_chunk(tagged_tokens, binary=False):
    """
    Use NLTK's currently recommended named entity chunker to
    chunk the given list of tagged tokens.

    >>> from nltk.chunk import ne_chunk
    >>> from nltk.corpus import treebank
    >>> from pprint import pprint
    >>> pprint(ne_chunk(treebank.tagged_sents()[2][8:14])) # doctest: +NORMALIZE_WHITESPACE
    Tree('S', [('chairman', 'NN'), ('of', 'IN'), Tree('ORGANIZATION', [('Consolidated', 'NNP'), ('Gold', 'NNP'), ('Fields', 'NNP')]), ('PLC', 'NNP')])

    """
    if binary:
        chunker = ne_chunker(fmt="binary")
    else:
        chunker = ne_chunker()
    return chunker.parse(tagged_tokens)


def ne_chunk_sents(tagged_sentences, binary=False):
    """
    Use NLTK's currently recommended named entity chunker to chunk the
    given list of tagged sentences, each consisting of a list of tagged tokens.
    """
    if binary:
        chunker = ne_chunker(fmt="binary")
    else:
        chunker = ne_chunker()
    return chunker.parse_sents(tagged_sentences)

# === NexusCore/openenv\Lib\site-packages\openai\resources\uploads\parts.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Mapping, cast

import httpx

from ... import _legacy_response
from ..._types import NOT_GIVEN, Body, Query, Headers, NotGiven, FileTypes
from ..._utils import extract_files, maybe_transform, deepcopy_minimal, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ..._base_client import make_request_options
from ...types.uploads import part_create_params
from ...types.uploads.upload_part import UploadPart

__all__ = ["Parts", "AsyncParts"]


class Parts(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> PartsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return PartsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> PartsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return PartsWithStreamingResponse(self)

    def create(
        self,
        upload_id: str,
        *,
        data: FileTypes,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> UploadPart:
        """
        Adds a
        [Part](https://platform.openai.com/docs/api-reference/uploads/part-object) to an
        [Upload](https://platform.openai.com/docs/api-reference/uploads/object) object.
        A Part represents a chunk of bytes from the file you are trying to upload.

        Each Part can be at most 64 MB, and you can add Parts until you hit the Upload
        maximum of 8 GB.

        It is possible to add multiple Parts in parallel. You can decide the intended
        order of the Parts when you
        [complete the Upload](https://platform.openai.com/docs/api-reference/uploads/complete).

        Args:
          data: The chunk of bytes for this Part.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not upload_id:
            raise ValueError(f"Expected a non-empty value for `upload_id` but received {upload_id!r}")
        body = deepcopy_minimal({"data": data})
        files = extract_files(cast(Mapping[str, object], body), paths=[["data"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return self._post(
            f"/uploads/{upload_id}/parts",
            body=maybe_transform(body, part_create_params.PartCreateParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=UploadPart,
        )


class AsyncParts(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncPartsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncPartsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncPartsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncPartsWithStreamingResponse(self)

    async def create(
        self,
        upload_id: str,
        *,
        data: FileTypes,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> UploadPart:
        """
        Adds a
        [Part](https://platform.openai.com/docs/api-reference/uploads/part-object) to an
        [Upload](https://platform.openai.com/docs/api-reference/uploads/object) object.
        A Part represents a chunk of bytes from the file you are trying to upload.

        Each Part can be at most 64 MB, and you can add Parts until you hit the Upload
        maximum of 8 GB.

        It is possible to add multiple Parts in parallel. You can decide the intended
        order of the Parts when you
        [complete the Upload](https://platform.openai.com/docs/api-reference/uploads/complete).

        Args:
          data: The chunk of bytes for this Part.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not upload_id:
            raise ValueError(f"Expected a non-empty value for `upload_id` but received {upload_id!r}")
        body = deepcopy_minimal({"data": data})
        files = extract_files(cast(Mapping[str, object], body), paths=[["data"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return await self._post(
            f"/uploads/{upload_id}/parts",
            body=await async_maybe_transform(body, part_create_params.PartCreateParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=UploadPart,
        )


class PartsWithRawResponse:
    def __init__(self, parts: Parts) -> None:
        self._parts = parts

        self.create = _legacy_response.to_raw_response_wrapper(
            parts.create,
        )


class AsyncPartsWithRawResponse:
    def __init__(self, parts: AsyncParts) -> None:
        self._parts = parts

        self.create = _legacy_response.async_to_raw_response_wrapper(
            parts.create,
        )


class PartsWithStreamingResponse:
    def __init__(self, parts: Parts) -> None:
        self._parts = parts

        self.create = to_streamed_response_wrapper(
            parts.create,
        )


class AsyncPartsWithStreamingResponse:
    def __init__(self, parts: AsyncParts) -> None:
        self._parts = parts

        self.create = async_to_streamed_response_wrapper(
            parts.create,
        )

# === NexusCore/openenv\Lib\site-packages\openai\types\responses\response_item.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Dict, List, Union, Optional
from typing_extensions import Literal, Annotated, TypeAlias

from ..._utils import PropertyInfo
from ..._models import BaseModel
from .response_output_message import ResponseOutputMessage
from .response_computer_tool_call import ResponseComputerToolCall
from .response_input_message_item import ResponseInputMessageItem
from .response_function_web_search import ResponseFunctionWebSearch
from .response_file_search_tool_call import ResponseFileSearchToolCall
from .response_function_tool_call_item import ResponseFunctionToolCallItem
from .response_code_interpreter_tool_call import ResponseCodeInterpreterToolCall
from .response_computer_tool_call_output_item import ResponseComputerToolCallOutputItem
from .response_function_tool_call_output_item import ResponseFunctionToolCallOutputItem

__all__ = [
    "ResponseItem",
    "ImageGenerationCall",
    "LocalShellCall",
    "LocalShellCallAction",
    "LocalShellCallOutput",
    "McpListTools",
    "McpListToolsTool",
    "McpApprovalRequest",
    "McpApprovalResponse",
    "McpCall",
]


class ImageGenerationCall(BaseModel):
    id: str
    """The unique ID of the image generation call."""

    result: Optional[str] = None
    """The generated image encoded in base64."""

    status: Literal["in_progress", "completed", "generating", "failed"]
    """The status of the image generation call."""

    type: Literal["image_generation_call"]
    """The type of the image generation call. Always `image_generation_call`."""


class LocalShellCallAction(BaseModel):
    command: List[str]
    """The command to run."""

    env: Dict[str, str]
    """Environment variables to set for the command."""

    type: Literal["exec"]
    """The type of the local shell action. Always `exec`."""

    timeout_ms: Optional[int] = None
    """Optional timeout in milliseconds for the command."""

    user: Optional[str] = None
    """Optional user to run the command as."""

    working_directory: Optional[str] = None
    """Optional working directory to run the command in."""


class LocalShellCall(BaseModel):
    id: str
    """The unique ID of the local shell call."""

    action: LocalShellCallAction
    """Execute a shell command on the server."""

    call_id: str
    """The unique ID of the local shell tool call generated by the model."""

    status: Literal["in_progress", "completed", "incomplete"]
    """The status of the local shell call."""

    type: Literal["local_shell_call"]
    """The type of the local shell call. Always `local_shell_call`."""


class LocalShellCallOutput(BaseModel):
    id: str
    """The unique ID of the local shell tool call generated by the model."""

    output: str
    """A JSON string of the output of the local shell tool call."""

    type: Literal["local_shell_call_output"]
    """The type of the local shell tool call output. Always `local_shell_call_output`."""

    status: Optional[Literal["in_progress", "completed", "incomplete"]] = None
    """The status of the item. One of `in_progress`, `completed`, or `incomplete`."""


class McpListToolsTool(BaseModel):
    input_schema: object
    """The JSON schema describing the tool's input."""

    name: str
    """The name of the tool."""

    annotations: Optional[object] = None
    """Additional annotations about the tool."""

    description: Optional[str] = None
    """The description of the tool."""


class McpListTools(BaseModel):
    id: str
    """The unique ID of the list."""

    server_label: str
    """The label of the MCP server."""

    tools: List[McpListToolsTool]
    """The tools available on the server."""

    type: Literal["mcp_list_tools"]
    """The type of the item. Always `mcp_list_tools`."""

    error: Optional[str] = None
    """Error message if the server could not list tools."""


class McpApprovalRequest(BaseModel):
    id: str
    """The unique ID of the approval request."""

    arguments: str
    """A JSON string of arguments for the tool."""

    name: str
    """The name of the tool to run."""

    server_label: str
    """The label of the MCP server making the request."""

    type: Literal["mcp_approval_request"]
    """The type of the item. Always `mcp_approval_request`."""


class McpApprovalResponse(BaseModel):
    id: str
    """The unique ID of the approval response"""

    approval_request_id: str
    """The ID of the approval request being answered."""

    approve: bool
    """Whether the request was approved."""

    type: Literal["mcp_approval_response"]
    """The type of the item. Always `mcp_approval_response`."""

    reason: Optional[str] = None
    """Optional reason for the decision."""


class McpCall(BaseModel):
    id: str
    """The unique ID of the tool call."""

    arguments: str
    """A JSON string of the arguments passed to the tool."""

    name: str
    """The name of the tool that was run."""

    server_label: str
    """The label of the MCP server running the tool."""

    type: Literal["mcp_call"]
    """The type of the item. Always `mcp_call`."""

    error: Optional[str] = None
    """The error from the tool call, if any."""

    output: Optional[str] = None
    """The output from the tool call."""


ResponseItem: TypeAlias = Annotated[
    Union[
        ResponseInputMessageItem,
        ResponseOutputMessage,
        ResponseFileSearchToolCall,
        ResponseComputerToolCall,
        ResponseComputerToolCallOutputItem,
        ResponseFunctionWebSearch,
        ResponseFunctionToolCallItem,
        ResponseFunctionToolCallOutputItem,
        ImageGenerationCall,
        ResponseCodeInterpreterToolCall,
        LocalShellCall,
        LocalShellCallOutput,
        McpListTools,
        McpApprovalRequest,
        McpApprovalResponse,
        McpCall,
    ],
    PropertyInfo(discriminator="type"),
]

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\textedit.py ===
"""
    pygments.lexers.textedit
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for languages related to text processing.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
from bisect import bisect

from pygments.lexer import RegexLexer, bygroups, default, include, this, using
from pygments.lexers.python import PythonLexer
from pygments.token import Comment, Keyword, Name, Number, Operator, \
    Punctuation, String, Text, Whitespace

__all__ = ['AwkLexer', 'SedLexer', 'VimLexer']


class AwkLexer(RegexLexer):
    """
    For Awk scripts.
    """

    name = 'Awk'
    aliases = ['awk', 'gawk', 'mawk', 'nawk']
    filenames = ['*.awk']
    mimetypes = ['application/x-awk']
    url = 'https://en.wikipedia.org/wiki/AWK'
    version_added = '1.5'

    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Text),
            (r'#.*$', Comment.Single)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'\B', String.Regex, '#pop'),
            (r'(?=/)', Text, ('#pop', 'badregex')),
            default('#pop')
        ],
        'badregex': [
            (r'\n', Text, '#pop')
        ],
        'root': [
            (r'^(?=\s|/)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),
            (r'\+\+|--|\|\||&&|in\b|\$|!?~|\?|:|'
             r'(\*\*|[-<>+*%\^/!=|])=?', Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(break|continue|do|while|exit|for|if|else|'
             r'return)\b', Keyword, 'slashstartsregex'),
            (r'function\b', Keyword.Declaration, 'slashstartsregex'),
            (r'(atan2|cos|exp|int|log|rand|sin|sqrt|srand|gensub|gsub|index|'
             r'length|match|split|sprintf|sub|substr|tolower|toupper|close|'
             r'fflush|getline|next|nextfile|print|printf|strftime|systime|'
             r'delete|system)\b', Keyword.Reserved),
            (r'(ARGC|ARGIND|ARGV|BEGIN|CONVFMT|ENVIRON|END|ERRNO|FIELDWIDTHS|'
             r'FILENAME|FNR|FS|IGNORECASE|NF|NR|OFMT|OFS|ORFS|RLENGTH|RS|'
             r'RSTART|RT|SUBSEP)\b', Name.Builtin),
            (r'[$a-zA-Z_]\w*', Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
        ]
    }


class SedLexer(RegexLexer):
    """
    Lexer for Sed script files.
    """
    name = 'Sed'
    aliases = ['sed', 'gsed', 'ssed']
    filenames = ['*.sed', '*.[gs]sed']
    mimetypes = ['text/x-sed']
    url = 'https://en.wikipedia.org/wiki/Sed'
    version_added = ''
    flags = re.MULTILINE

    # Match the contents within delimiters such as /<contents>/
    _inside_delims = r'((?:(?:\\[^\n]|[^\\])*?\\\n)*?(?:\\.|[^\\])*?)'

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'#.*$', Comment.Single),
            (r'[0-9]+', Number.Integer),
            (r'\$', Operator),
            (r'[{};,!]', Punctuation),
            (r'[dDFgGhHlnNpPqQxz=]', Keyword),
            (r'([berRtTvwW:])([^;\n]*)', bygroups(Keyword, String.Single)),
            (r'([aci])((?:.*?\\\n)*(?:.*?[^\\]$))', bygroups(Keyword, String.Double)),
            (r'([qQ])([0-9]*)', bygroups(Keyword, Number.Integer)),
            (r'(/)' + _inside_delims + r'(/)', bygroups(Punctuation, String.Regex, Punctuation)),
            (r'(\\(.))' + _inside_delims + r'(\2)',
             bygroups(Punctuation, None, String.Regex, Punctuation)),
            (r'(y)(.)' + _inside_delims + r'(\2)' + _inside_delims + r'(\2)',
             bygroups(Keyword, Punctuation, String.Single, Punctuation, String.Single, Punctuation)),
            (r'(s)(.)' + _inside_delims + r'(\2)' + _inside_delims + r'(\2)((?:[gpeIiMm]|[0-9])*)',
             bygroups(Keyword, Punctuation, String.Regex, Punctuation, String.Single, Punctuation,
                      Keyword))
        ]
    }

class VimLexer(RegexLexer):
    """
    Lexer for VimL script files.
    """
    name = 'VimL'
    aliases = ['vim']
    filenames = ['*.vim', '.vimrc', '.exrc', '.gvimrc',
                 '_vimrc', '_exrc', '_gvimrc', 'vimrc', 'gvimrc']
    mimetypes = ['text/x-vim']
    url = 'https://www.vim.org'
    version_added = '0.8'

    flags = re.MULTILINE

    _python = r'py(?:t(?:h(?:o(?:n)?)?)?)?'

    tokens = {
        'root': [
            (r'^([ \t:]*)(' + _python + r')([ \t]*)(<<)([ \t]*)(.*)((?:\n|.)*)(\6)',
             bygroups(using(this), Keyword, Text, Operator, Text, Text,
                      using(PythonLexer), Text)),
            (r'^([ \t:]*)(' + _python + r')([ \t])(.*)',
             bygroups(using(this), Keyword, Text, using(PythonLexer))),

            (r'^\s*".*', Comment),

            (r'[ \t]+', Text),
            # TODO: regexes can have other delims
            (r'/[^/\\\n]*(?:\\[\s\S][^/\\\n]*)*/', String.Regex),
            (r'"[^"\\\n]*(?:\\[\s\S][^"\\\n]*)*"', String.Double),
            (r"'[^\n']*(?:''[^\n']*)*'", String.Single),

            # Who decided that doublequote was a good comment character??
            (r'(?<=\s)"[^\-:.%#=*].*', Comment),
            (r'-?\d+', Number),
            (r'#[0-9a-f]{6}', Number.Hex),
            (r'^:', Punctuation),
            (r'[()<>+=!|,~-]', Punctuation),  # Inexact list.  Looks decent.
            (r'\b(let|if|else|endif|elseif|fun|function|endfunction)\b',
             Keyword),
            (r'\b(NONE|bold|italic|underline|dark|light)\b', Name.Builtin),
            (r'\b\w+\b', Name.Other),  # These are postprocessed below
            (r'.', Text),
        ],
    }

    def __init__(self, **options):
        from pygments.lexers._vim_builtins import auto, command, option
        self._cmd = command
        self._opt = option
        self._aut = auto

        RegexLexer.__init__(self, **options)

    def is_in(self, w, mapping):
        r"""
        It's kind of difficult to decide if something might be a keyword
        in VimL because it allows you to abbreviate them.  In fact,
        'ab[breviate]' is a good example.  :ab, :abbre, or :abbreviate are
        valid ways to call it so rather than making really awful regexps
        like::

            \bab(?:b(?:r(?:e(?:v(?:i(?:a(?:t(?:e)?)?)?)?)?)?)?)?\b

        we match `\b\w+\b` and then call is_in() on those tokens.  See
        `scripts/get_vimkw.py` for how the lists are extracted.
        """
        p = bisect(mapping, (w,))
        if p > 0:
            if mapping[p-1][0] == w[:len(mapping[p-1][0])] and \
               mapping[p-1][1][:len(w)] == w:
                return True
        if p < len(mapping):
            return mapping[p][0] == w[:len(mapping[p][0])] and \
                mapping[p][1][:len(w)] == w
        return False

    def get_tokens_unprocessed(self, text):
        # TODO: builtins are only subsequent tokens on lines
        #       and 'keywords' only happen at the beginning except
        #       for :au ones
        for index, token, value in \
                RegexLexer.get_tokens_unprocessed(self, text):
            if token is Name.Other:
                if self.is_in(value, self._cmd):
                    yield index, Keyword, value
                elif self.is_in(value, self._opt) or \
                        self.is_in(value, self._aut):
                    yield index, Name.Builtin, value
                else:
                    yield index, Text, value
            else:
                yield index, token, value

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\actions\pointer_actions.py ===
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
from typing import Optional

from selenium.webdriver.remote.webelement import WebElement

from . import interaction
from .interaction import Interaction
from .mouse_button import MouseButton
from .pointer_input import PointerInput


class PointerActions(Interaction):
    def __init__(self, source: Optional[PointerInput] = None, duration: int = 250):
        """
        Args:
        - source: PointerInput instance
        - duration: override the default 250 msecs of DEFAULT_MOVE_DURATION in source
        """
        if source is None:
            source = PointerInput(interaction.POINTER_MOUSE, "mouse")
        self.source = source
        self._duration = duration
        super().__init__(source)

    def pointer_down(
        self,
        button=MouseButton.LEFT,
        width=None,
        height=None,
        pressure=None,
        tangential_pressure=None,
        tilt_x=None,
        tilt_y=None,
        twist=None,
        altitude_angle=None,
        azimuth_angle=None,
    ):
        self._button_action(
            "create_pointer_down",
            button=button,
            width=width,
            height=height,
            pressure=pressure,
            tangential_pressure=tangential_pressure,
            tilt_x=tilt_x,
            tilt_y=tilt_y,
            twist=twist,
            altitude_angle=altitude_angle,
            azimuth_angle=azimuth_angle,
        )
        return self

    def pointer_up(self, button=MouseButton.LEFT):
        self._button_action("create_pointer_up", button=button)
        return self

    def move_to(
        self,
        element,
        x=0,
        y=0,
        width=None,
        height=None,
        pressure=None,
        tangential_pressure=None,
        tilt_x=None,
        tilt_y=None,
        twist=None,
        altitude_angle=None,
        azimuth_angle=None,
    ):
        if not isinstance(element, WebElement):
            raise AttributeError("move_to requires a WebElement")

        self.source.create_pointer_move(
            origin=element,
            duration=self._duration,
            x=int(x),
            y=int(y),
            width=width,
            height=height,
            pressure=pressure,
            tangential_pressure=tangential_pressure,
            tilt_x=tilt_x,
            tilt_y=tilt_y,
            twist=twist,
            altitude_angle=altitude_angle,
            azimuth_angle=azimuth_angle,
        )
        return self

    def move_by(
        self,
        x,
        y,
        width=None,
        height=None,
        pressure=None,
        tangential_pressure=None,
        tilt_x=None,
        tilt_y=None,
        twist=None,
        altitude_angle=None,
        azimuth_angle=None,
    ):
        self.source.create_pointer_move(
            origin=interaction.POINTER,
            duration=self._duration,
            x=int(x),
            y=int(y),
            width=width,
            height=height,
            pressure=pressure,
            tangential_pressure=tangential_pressure,
            tilt_x=tilt_x,
            tilt_y=tilt_y,
            twist=twist,
            altitude_angle=altitude_angle,
            azimuth_angle=azimuth_angle,
        )
        return self

    def move_to_location(
        self,
        x,
        y,
        width=None,
        height=None,
        pressure=None,
        tangential_pressure=None,
        tilt_x=None,
        tilt_y=None,
        twist=None,
        altitude_angle=None,
        azimuth_angle=None,
    ):
        self.source.create_pointer_move(
            origin="viewport",
            duration=self._duration,
            x=int(x),
            y=int(y),
            width=width,
            height=height,
            pressure=pressure,
            tangential_pressure=tangential_pressure,
            tilt_x=tilt_x,
            tilt_y=tilt_y,
            twist=twist,
            altitude_angle=altitude_angle,
            azimuth_angle=azimuth_angle,
        )
        return self

    def click(self, element: Optional[WebElement] = None, button=MouseButton.LEFT):
        if element:
            self.move_to(element)
        self.pointer_down(button)
        self.pointer_up(button)
        return self

    def context_click(self, element: Optional[WebElement] = None):
        return self.click(element=element, button=MouseButton.RIGHT)

    def click_and_hold(self, element: Optional[WebElement] = None, button=MouseButton.LEFT):
        if element:
            self.move_to(element)
        self.pointer_down(button=button)
        return self

    def release(self, button=MouseButton.LEFT):
        self.pointer_up(button=button)
        return self

    def double_click(self, element: Optional[WebElement] = None):
        if element:
            self.move_to(element)
        self.pointer_down(MouseButton.LEFT)
        self.pointer_up(MouseButton.LEFT)
        self.pointer_down(MouseButton.LEFT)
        self.pointer_up(MouseButton.LEFT)
        return self

    def pause(self, duration: float = 0):
        self.source.create_pause(duration)
        return self

    def _button_action(self, action, **kwargs):
        meth = getattr(self.source, action)
        meth(**kwargs)
        return self

# === NexusCore/openenv\Lib\site-packages\jsonschema\_types.py ===
from __future__ import annotations

from typing import TYPE_CHECKING
import numbers

from attrs import evolve, field, frozen
from rpds import HashTrieMap

from jsonschema.exceptions import UndefinedTypeCheck

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any, Callable


# unfortunately, the type of HashTrieMap is generic, and if used as an attrs
# converter, the generic type is presented to mypy, which then fails to match
# the concrete type of a type checker mapping
# this "do nothing" wrapper presents the correct information to mypy
def _typed_map_converter(
    init_val: Mapping[str, Callable[[TypeChecker, Any], bool]],
) -> HashTrieMap[str, Callable[[TypeChecker, Any], bool]]:
    return HashTrieMap.convert(init_val)


def is_array(checker, instance):
    return isinstance(instance, list)


def is_bool(checker, instance):
    return isinstance(instance, bool)


def is_integer(checker, instance):
    # bool inherits from int, so ensure bools aren't reported as ints
    if isinstance(instance, bool):
        return False
    return isinstance(instance, int)


def is_null(checker, instance):
    return instance is None


def is_number(checker, instance):
    # bool inherits from int, so ensure bools aren't reported as ints
    if isinstance(instance, bool):
        return False
    return isinstance(instance, numbers.Number)


def is_object(checker, instance):
    return isinstance(instance, dict)


def is_string(checker, instance):
    return isinstance(instance, str)


def is_any(checker, instance):
    return True


@frozen(repr=False)
class TypeChecker:
    """
    A :kw:`type` property checker.

    A `TypeChecker` performs type checking for a `Validator`, converting
    between the defined JSON Schema types and some associated Python types or
    objects.

    Modifying the behavior just mentioned by redefining which Python objects
    are considered to be of which JSON Schema types can be done using
    `TypeChecker.redefine` or `TypeChecker.redefine_many`, and types can be
    removed via `TypeChecker.remove`. Each of these return a new `TypeChecker`.

    Arguments:

        type_checkers:

            The initial mapping of types to their checking functions.

    """

    _type_checkers: HashTrieMap[
        str, Callable[[TypeChecker, Any], bool],
    ] = field(default=HashTrieMap(), converter=_typed_map_converter)

    def __repr__(self):
        types = ", ".join(repr(k) for k in sorted(self._type_checkers))
        return f"<{self.__class__.__name__} types={{{types}}}>"

    def is_type(self, instance, type: str) -> bool:
        """
        Check if the instance is of the appropriate type.

        Arguments:

            instance:

                The instance to check

            type:

                The name of the type that is expected.

        Raises:

            `jsonschema.exceptions.UndefinedTypeCheck`:

                if ``type`` is unknown to this object.

        """
        try:
            fn = self._type_checkers[type]
        except KeyError:
            raise UndefinedTypeCheck(type) from None

        return fn(self, instance)

    def redefine(self, type: str, fn) -> TypeChecker:
        """
        Produce a new checker with the given type redefined.

        Arguments:

            type:

                The name of the type to check.

            fn (collections.abc.Callable):

                A callable taking exactly two parameters - the type
                checker calling the function and the instance to check.
                The function should return true if instance is of this
                type and false otherwise.

        """
        return self.redefine_many({type: fn})

    def redefine_many(self, definitions=()) -> TypeChecker:
        """
        Produce a new checker with the given types redefined.

        Arguments:

            definitions (dict):

                A dictionary mapping types to their checking functions.

        """
        type_checkers = self._type_checkers.update(definitions)
        return evolve(self, type_checkers=type_checkers)

    def remove(self, *types) -> TypeChecker:
        """
        Produce a new checker with the given types forgotten.

        Arguments:

            types:

                the names of the types to remove.

        Raises:

            `jsonschema.exceptions.UndefinedTypeCheck`:

                if any given type is unknown to this object

        """
        type_checkers = self._type_checkers
        for each in types:
            try:
                type_checkers = type_checkers.remove(each)
            except KeyError:
                raise UndefinedTypeCheck(each) from None
        return evolve(self, type_checkers=type_checkers)


draft3_type_checker = TypeChecker(
    {
        "any": is_any,
        "array": is_array,
        "boolean": is_bool,
        "integer": is_integer,
        "object": is_object,
        "null": is_null,
        "number": is_number,
        "string": is_string,
    },
)
draft4_type_checker = draft3_type_checker.remove("any")
draft6_type_checker = draft4_type_checker.redefine(
    "integer",
    lambda checker, instance: (
        is_integer(checker, instance)
        or (isinstance(instance, float) and instance.is_integer())
    ),
)
draft7_type_checker = draft6_type_checker
draft201909_type_checker = draft7_type_checker
draft202012_type_checker = draft201909_type_checker

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\xmlWriter.py ===
"""xmlWriter.py -- Simple XML authoring class"""

from fontTools.misc.textTools import byteord, strjoin, tobytes, tostr
import sys
import os
import string

INDENT = "  "


class XMLWriter(object):
    def __init__(
        self,
        fileOrPath,
        indentwhite=INDENT,
        idlefunc=None,
        encoding="utf_8",
        newlinestr="\n",
    ):
        if encoding.lower().replace("-", "").replace("_", "") != "utf8":
            raise Exception("Only UTF-8 encoding is supported.")
        if fileOrPath == "-":
            fileOrPath = sys.stdout
        if not hasattr(fileOrPath, "write"):
            self.filename = fileOrPath
            self.file = open(fileOrPath, "wb")
            self._closeStream = True
        else:
            self.filename = None
            # assume writable file object
            self.file = fileOrPath
            self._closeStream = False

        # Figure out if writer expects bytes or unicodes
        try:
            # The bytes check should be first.  See:
            # https://github.com/fonttools/fonttools/pull/233
            self.file.write(b"")
            self.totype = tobytes
        except TypeError:
            # This better not fail.
            self.file.write("")
            self.totype = tostr
        self.indentwhite = self.totype(indentwhite)
        if newlinestr is None:
            self.newlinestr = self.totype(os.linesep)
        else:
            self.newlinestr = self.totype(newlinestr)
        self.indentlevel = 0
        self.stack = []
        self.needindent = 1
        self.idlefunc = idlefunc
        self.idlecounter = 0
        self._writeraw('<?xml version="1.0" encoding="UTF-8"?>')
        self.newline()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.close()

    def close(self):
        if self._closeStream:
            self.file.close()

    def write(self, string, indent=True):
        """Writes text."""
        self._writeraw(escape(string), indent=indent)

    def writecdata(self, string):
        """Writes text in a CDATA section."""
        self._writeraw("<![CDATA[" + string + "]]>")

    def write8bit(self, data, strip=False):
        """Writes a bytes() sequence into the XML, escaping
        non-ASCII bytes.  When this is read in xmlReader,
        the original bytes can be recovered by encoding to
        'latin-1'."""
        self._writeraw(escape8bit(data), strip=strip)

    def write_noindent(self, string):
        """Writes text without indentation."""
        self._writeraw(escape(string), indent=False)

    def _writeraw(self, data, indent=True, strip=False):
        """Writes bytes, possibly indented."""
        if indent and self.needindent:
            self.file.write(self.indentlevel * self.indentwhite)
            self.needindent = 0
        s = self.totype(data, encoding="utf_8")
        if strip:
            s = s.strip()
        self.file.write(s)

    def newline(self):
        self.file.write(self.newlinestr)
        self.needindent = 1
        idlecounter = self.idlecounter
        if not idlecounter % 100 and self.idlefunc is not None:
            self.idlefunc()
        self.idlecounter = idlecounter + 1

    def comment(self, data):
        data = escape(data)
        lines = data.split("\n")
        self._writeraw("<!-- " + lines[0])
        for line in lines[1:]:
            self.newline()
            self._writeraw("     " + line)
        self._writeraw(" -->")

    def simpletag(self, _TAG_, *args, **kwargs):
        attrdata = self.stringifyattrs(*args, **kwargs)
        data = "<%s%s/>" % (_TAG_, attrdata)
        self._writeraw(data)

    def begintag(self, _TAG_, *args, **kwargs):
        attrdata = self.stringifyattrs(*args, **kwargs)
        data = "<%s%s>" % (_TAG_, attrdata)
        self._writeraw(data)
        self.stack.append(_TAG_)
        self.indent()

    def endtag(self, _TAG_):
        assert self.stack and self.stack[-1] == _TAG_, "nonmatching endtag"
        del self.stack[-1]
        self.dedent()
        data = "</%s>" % _TAG_
        self._writeraw(data)

    def dumphex(self, data):
        linelength = 16
        hexlinelength = linelength * 2
        chunksize = 8
        for i in range(0, len(data), linelength):
            hexline = hexStr(data[i : i + linelength])
            line = ""
            white = ""
            for j in range(0, hexlinelength, chunksize):
                line = line + white + hexline[j : j + chunksize]
                white = " "
            self._writeraw(line)
            self.newline()

    def indent(self):
        self.indentlevel = self.indentlevel + 1

    def dedent(self):
        assert self.indentlevel > 0
        self.indentlevel = self.indentlevel - 1

    def stringifyattrs(self, *args, **kwargs):
        if kwargs:
            assert not args
            attributes = sorted(kwargs.items())
        elif args:
            assert len(args) == 1
            attributes = args[0]
        else:
            return ""
        data = ""
        for attr, value in attributes:
            if not isinstance(value, (bytes, str)):
                value = str(value)
            data = data + ' %s="%s"' % (attr, escapeattr(value))
        return data


def escape(data):
    data = tostr(data, "utf_8")
    data = data.replace("&", "&amp;")
    data = data.replace("<", "&lt;")
    data = data.replace(">", "&gt;")
    data = data.replace("\r", "&#13;")
    return data


def escapeattr(data):
    data = escape(data)
    data = data.replace('"', "&quot;")
    return data


def escape8bit(data):
    """Input is Unicode string."""

    def escapechar(c):
        n = ord(c)
        if 32 <= n <= 127 and c not in "<&>":
            return c
        else:
            return "&#" + repr(n) + ";"

    return strjoin(map(escapechar, data.decode("latin-1")))


def hexStr(s):
    h = string.hexdigits
    r = ""
    for c in s:
        i = byteord(c)
        r = r + h[(i >> 4) & 0xF] + h[i & 0xF]
    return r

# === NexusCore/openenv\Lib\site-packages\jupyter_core\utils\__init__.py ===
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import atexit
import errno
import inspect
import sys
import threading
import warnings
from contextvars import ContextVar
from pathlib import Path
from types import FrameType
from typing import Any, Awaitable, Callable, TypeVar, cast


def ensure_dir_exists(path: str | Path, mode: int = 0o777) -> None:
    """Ensure that a directory exists

    If it doesn't exist, try to create it, protecting against a race condition
    if another process is doing the same.
    The default permissions are determined by the current umask.
    """
    try:
        Path(path).mkdir(parents=True, mode=mode)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    if not Path(path).is_dir():
        msg = f"{path!r} exists but is not a directory"
        raise OSError(msg)


def _get_frame(level: int) -> FrameType | None:
    """Get the frame at the given stack level."""
    # sys._getframe is much faster than inspect.stack, but isn't guaranteed to
    # exist in all python implementations, so we fall back to inspect.stack()

    # We need to add one to level to account for this get_frame call.
    if hasattr(sys, "_getframe"):
        frame = sys._getframe(level + 1)
    else:
        frame = inspect.stack(context=0)[level + 1].frame
    return frame


# This function is from https://github.com/python/cpython/issues/67998
# (https://bugs.python.org/file39550/deprecated_module_stacklevel.diff) and
# calculates the appropriate stacklevel for deprecations to target the
# deprecation for the caller, no matter how many internal stack frames we have
# added in the process. For example, with the deprecation warning in the
# __init__ below, the appropriate stacklevel will change depending on how deep
# the inheritance hierarchy is.
def _external_stacklevel(internal: list[str]) -> int:
    """Find the stacklevel of the first frame that doesn't contain any of the given internal strings

    The depth will be 1 at minimum in order to start checking at the caller of
    the function that called this utility method.
    """
    # Get the level of my caller's caller
    level = 2
    frame = _get_frame(level)

    # Normalize the path separators:
    normalized_internal = [str(Path(s)) for s in internal]

    # climb the stack frames while we see internal frames
    while frame and any(s in str(Path(frame.f_code.co_filename)) for s in normalized_internal):
        level += 1
        frame = frame.f_back

    # Return the stack level from the perspective of whoever called us (i.e., one level up)
    return level - 1


def deprecation(message: str, internal: str | list[str] = "jupyter_core/") -> None:
    """Generate a deprecation warning targeting the first frame that is not 'internal'

    internal is a string or list of strings, which if they appear in filenames in the
    frames, the frames will be considered internal. Changing this can be useful if, for example,
    we know that our internal code is calling out to another library.
    """
    _internal: list[str]
    _internal = [internal] if isinstance(internal, str) else internal

    # stack level of the first external frame from here
    stacklevel = _external_stacklevel(_internal)

    # The call to .warn adds one frame, so bump the stacklevel up by one
    warnings.warn(message, DeprecationWarning, stacklevel=stacklevel + 1)


T = TypeVar("T")


class _TaskRunner:
    """A task runner that runs an asyncio event loop on a background thread."""

    def __init__(self) -> None:
        self.__io_loop: asyncio.AbstractEventLoop | None = None
        self.__runner_thread: threading.Thread | None = None
        self.__lock = threading.Lock()
        atexit.register(self._close)

    def _close(self) -> None:
        if self.__io_loop:
            self.__io_loop.stop()

    def _runner(self) -> None:
        loop = self.__io_loop
        assert loop is not None
        try:
            loop.run_forever()
        finally:
            loop.close()

    def run(self, coro: Any) -> Any:
        """Synchronously run a coroutine on a background thread."""
        with self.__lock:
            name = f"{threading.current_thread().name} - runner"
            if self.__io_loop is None:
                self.__io_loop = asyncio.new_event_loop()
                self.__runner_thread = threading.Thread(target=self._runner, daemon=True, name=name)
                self.__runner_thread.start()
        fut = asyncio.run_coroutine_threadsafe(coro, self.__io_loop)
        return fut.result(None)


_runner_map: dict[str, _TaskRunner] = {}
_loop: ContextVar[asyncio.AbstractEventLoop | None] = ContextVar("_loop", default=None)


def run_sync(coro: Callable[..., Awaitable[T]]) -> Callable[..., T]:
    """Wraps coroutine in a function that blocks until it has executed.

    Parameters
    ----------
    coro : coroutine-function
        The coroutine-function to be executed.

    Returns
    -------
    result :
        Whatever the coroutine-function returns.
    """

    assert inspect.iscoroutinefunction(coro)

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        name = threading.current_thread().name
        inner = coro(*args, **kwargs)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No loop running, run the loop for this thread.
            loop = ensure_event_loop()
            return loop.run_until_complete(inner)

        # Loop is currently running in this thread,
        # use a task runner.
        if name not in _runner_map:
            _runner_map[name] = _TaskRunner()
        return _runner_map[name].run(inner)

    wrapped.__doc__ = coro.__doc__
    return wrapped


def ensure_event_loop(prefer_selector_loop: bool = False) -> asyncio.AbstractEventLoop:
    # Get the loop for this thread, or create a new one.
    loop = _loop.get()
    if loop is not None and not loop.is_closed():
        return loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        if sys.platform == "win32" and prefer_selector_loop:
            loop = asyncio.WindowsSelectorEventLoopPolicy().new_event_loop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    _loop.set(loop)
    return loop


async def ensure_async(obj: Awaitable[T] | T) -> T:
    """Convert a non-awaitable object to a coroutine if needed,
    and await it if it was not already awaited.

    This function is meant to be called on the result of calling a function,
    when that function could either be asynchronous or not.
    """
    if inspect.isawaitable(obj):
        obj = cast(Awaitable[T], obj)
        try:
            result = await obj
        except RuntimeError as e:
            if str(e) == "cannot reuse already awaited coroutine":
                # obj is already the coroutine's result
                return cast(T, obj)
            raise
        return result
    return obj

# === NexusCore/openenv\Lib\site-packages\trio\_core\_generated_io_windows.py ===
# ***********************************************************
# ******* WARNING: AUTOGENERATED! ALL EDITS WILL BE LOST ******
# *************************************************************
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ._ki import enable_ki_protection
from ._run import GLOBAL_RUN_CONTEXT

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from typing_extensions import Buffer

    from .._file_io import _HasFileNo
    from ._unbounded_queue import UnboundedQueue
    from ._windows_cffi import CData, Handle

assert not TYPE_CHECKING or sys.platform == "win32"


__all__ = [
    "current_iocp",
    "monitor_completion_key",
    "notify_closing",
    "readinto_overlapped",
    "register_with_iocp",
    "wait_overlapped",
    "wait_readable",
    "wait_writable",
    "write_overlapped",
]


@enable_ki_protection
async def wait_readable(sock: _HasFileNo | int) -> None:
    """Block until the kernel reports that the given object is readable.

    On Unix systems, ``sock`` must either be an integer file descriptor,
    or else an object with a ``.fileno()`` method which returns an
    integer file descriptor. Any kind of file descriptor can be passed,
    though the exact semantics will depend on your kernel. For example,
    this probably won't do anything useful for on-disk files.

    On Windows systems, ``sock`` must either be an integer ``SOCKET``
    handle, or else an object with a ``.fileno()`` method which returns
    an integer ``SOCKET`` handle. File descriptors aren't supported,
    and neither are handles that refer to anything besides a
    ``SOCKET``.

    :raises trio.BusyResourceError:
        if another task is already waiting for the given socket to
        become readable.
    :raises trio.ClosedResourceError:
        if another task calls :func:`notify_closing` while this
        function is still working.
    """
    try:
        return await GLOBAL_RUN_CONTEXT.runner.io_manager.wait_readable(sock)
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
async def wait_writable(sock: _HasFileNo | int) -> None:
    """Block until the kernel reports that the given object is writable.

    See `wait_readable` for the definition of ``sock``.

    :raises trio.BusyResourceError:
        if another task is already waiting for the given socket to
        become writable.
    :raises trio.ClosedResourceError:
        if another task calls :func:`notify_closing` while this
        function is still working.
    """
    try:
        return await GLOBAL_RUN_CONTEXT.runner.io_manager.wait_writable(sock)
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
def notify_closing(handle: Handle | int | _HasFileNo) -> None:
    """Notify waiters of the given object that it will be closed.

    Call this before closing a file descriptor (on Unix) or socket (on
    Windows). This will cause any `wait_readable` or `wait_writable`
    calls on the given object to immediately wake up and raise
    `~trio.ClosedResourceError`.

    This doesn't actually close the object – you still have to do that
    yourself afterwards. Also, you want to be careful to make sure no
    new tasks start waiting on the object in between when you call this
    and when it's actually closed. So to close something properly, you
    usually want to do these steps in order:

    1. Explicitly mark the object as closed, so that any new attempts
       to use it will abort before they start.
    2. Call `notify_closing` to wake up any already-existing users.
    3. Actually close the object.

    It's also possible to do them in a different order if that's more
    convenient, *but only if* you make sure not to have any checkpoints in
    between the steps. This way they all happen in a single atomic
    step, so other tasks won't be able to tell what order they happened
    in anyway.
    """
    try:
        return GLOBAL_RUN_CONTEXT.runner.io_manager.notify_closing(handle)
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
def register_with_iocp(handle: int | CData) -> None:
    """TODO: these are implemented, but are currently more of a sketch than
    anything real. See `#26
    <https://github.com/python-trio/trio/issues/26>`__ and `#52
    <https://github.com/python-trio/trio/issues/52>`__.
    """
    try:
        return GLOBAL_RUN_CONTEXT.runner.io_manager.register_with_iocp(handle)
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
async def wait_overlapped(handle_: int | CData, lpOverlapped: CData | int) -> object:
    """TODO: these are implemented, but are currently more of a sketch than
    anything real. See `#26
    <https://github.com/python-trio/trio/issues/26>`__ and `#52
    <https://github.com/python-trio/trio/issues/52>`__.
    """
    try:
        return await GLOBAL_RUN_CONTEXT.runner.io_manager.wait_overlapped(
            handle_, lpOverlapped
        )
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
async def write_overlapped(
    handle: int | CData, data: Buffer, file_offset: int = 0
) -> int:
    """TODO: these are implemented, but are currently more of a sketch than
    anything real. See `#26
    <https://github.com/python-trio/trio/issues/26>`__ and `#52
    <https://github.com/python-trio/trio/issues/52>`__.
    """
    try:
        return await GLOBAL_RUN_CONTEXT.runner.io_manager.write_overlapped(
            handle, data, file_offset
        )
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
async def readinto_overlapped(
    handle: int | CData, buffer: Buffer, file_offset: int = 0
) -> int:
    """TODO: these are implemented, but are currently more of a sketch than
    anything real. See `#26
    <https://github.com/python-trio/trio/issues/26>`__ and `#52
    <https://github.com/python-trio/trio/issues/52>`__.
    """
    try:
        return await GLOBAL_RUN_CONTEXT.runner.io_manager.readinto_overlapped(
            handle, buffer, file_offset
        )
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
def current_iocp() -> int:
    """TODO: these are implemented, but are currently more of a sketch than
    anything real. See `#26
    <https://github.com/python-trio/trio/issues/26>`__ and `#52
    <https://github.com/python-trio/trio/issues/52>`__.
    """
    try:
        return GLOBAL_RUN_CONTEXT.runner.io_manager.current_iocp()
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


@enable_ki_protection
def monitor_completion_key() -> (
    AbstractContextManager[tuple[int, UnboundedQueue[object]]]
):
    """TODO: these are implemented, but are currently more of a sketch than
    anything real. See `#26
    <https://github.com/python-trio/trio/issues/26>`__ and `#52
    <https://github.com/python-trio/trio/issues/52>`__.
    """
    try:
        return GLOBAL_RUN_CONTEXT.runner.io_manager.monitor_completion_key()
    except AttributeError:
        raise RuntimeError("must be called from async context") from None

# === NexusCore/evaluation\evalplus\tools\viz_passrate.py ===
import json
import os
import pickle
from os import PathLike
from typing import List

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

from evalplus.data import get_human_eval_plus
from evalplus.eval import estimate_pass_at_k

SMALL_SIZE = 10
MEDIUM_SIZE = 14
BIGGER_SIZE = 18

plt.rc("font", size=SMALL_SIZE)  # controls default text sizes
plt.rc("axes", titlesize=MEDIUM_SIZE)  # fontsize of the axes title
plt.rc("axes", labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
plt.rc("xtick", labelsize=MEDIUM_SIZE)  # fontsize of the tick labels
plt.rc("ytick", labelsize=MEDIUM_SIZE)  # fontsize of the tick labels
plt.rc("legend", fontsize=MEDIUM_SIZE - 1)  # legend fontsize
plt.rc("figure", titlesize=BIGGER_SIZE)  # fontsize of the figure title

plt.rc("text", usetex=True)

SUCCESS = "success"


def passk_rel_drop(task2bvs_old, task2bvs_new):
    # old_rate:
    # dim0: problems
    # dim1: each experiment (model@temperature)
    # dim2: pass/fail booleans for each sample
    # this fn computes the relative drop in pass@k averaged over experiments

    passk_old = {}
    passk_new = {}
    # sample size => k => List[pass@k]

    for exp_i in range(len(task2bvs_old[0])):
        ntotal = []
        npass_old = []
        npass_new = []
        nsamples = None
        for task_i in range(len(task2bvs_old)):
            bv_old = task2bvs_old[task_i][exp_i]
            bv_new = task2bvs_new[task_i][exp_i]
            ntotal.append(len(bv_old))
            npass_old.append(bv_old.sum())
            npass_new.append(bv_new.sum())
            if nsamples is None:
                nsamples = len(bv_old)
            assert len(bv_old) == len(bv_new) == nsamples

        d_old = passk_old.setdefault(nsamples, {})
        d_new = passk_new.setdefault(nsamples, {})
        for k in [1, 10, 100]:
            if nsamples >= k:
                pass_at_k_old = estimate_pass_at_k(ntotal, npass_old, k).mean() * 100
                pass_at_k_new = estimate_pass_at_k(ntotal, npass_new, k).mean() * 100
                d_old.setdefault(k, []).append(pass_at_k_old)
                d_new.setdefault(k, []).append(pass_at_k_new)

    for nsamples in passk_old:
        print("=====================================")
        print(f"{nsamples = }")
        do = passk_old[nsamples]
        dn = passk_new[nsamples]
        drops = []
        for k in [1, 10, 100]:
            if k in do:
                pko = np.array(do[k])
                pkn = np.array(dn[k])
                drop = 100 * (pko - pkn) / pko
                drops.append(drop)
                print(
                    f"pass@{k}: \t{pko.mean():.1f}% -> {pkn.mean():.1f}% (drop {drop.mean():.1f}%)"
                )
        drops = np.array(drops)
        print(f"+++ {drops.mean() = :.1f}%")
        print(f"+++ {drops.max() = :.1f}%")
        print("=====================================")


def get_data(paths: List[PathLike]):
    task2bvs_old = None
    task2bvs_new = None

    for path in tqdm(paths):  # each experiment
        res = json.load(open(path, "r"))["eval"]
        ntask = len(res)

        assert ntask == 164

        if task2bvs_old is None and task2bvs_new is None:
            task2bvs_old = [[] for _ in range(ntask)]
            task2bvs_new = [[] for _ in range(ntask)]
            # i-th => task-i pass rate for an experiment

        for i, v in enumerate(res.values()):  # each task
            base = v["base"]
            plus = v["plus"]
            bbv = np.array([s == SUCCESS for s, _ in base])
            pbv = np.array([s == SUCCESS for s, _ in plus]) & bbv
            assert bbv.mean() >= pbv.mean()

            task2bvs_old[i].append(bbv)
            task2bvs_new[i].append(pbv)

    assert len(task2bvs_old) == len(task2bvs_new)
    return task2bvs_old, task2bvs_new


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=str, default="/JawTitan/EvalPlus/humaneval")
    args = parser.parse_args()

    paths = []
    for path in os.listdir(args.root):
        eval_json_path = os.path.join(args.root, path, "eval_results.json")
        if not os.path.isfile(eval_json_path) or not path[-1].isdigit():
            print(f"skip {path}")
            continue
        paths.append(eval_json_path)

    CACHE_PATH = "passrate.pkl"
    if os.path.isfile(CACHE_PATH):  # use cache
        task2bvs_old, task2bvs_new = pickle.load(open(CACHE_PATH, "rb"))
    else:
        task2bvs_old, task2bvs_new = get_data(paths)
        pickle.dump((task2bvs_old, task2bvs_new), open(CACHE_PATH, "wb"))

    passk_rel_drop(task2bvs_old, task2bvs_new)

    rate_old = [[bv.mean() for bv in task] for task in task2bvs_old]
    rate_new = [[bv.mean() for bv in task] for task in task2bvs_new]

    rate_old = 100 * np.array(rate_old).mean(axis=1)
    rate_new = 100 * np.array(rate_new).mean(axis=1)

    print(
        f"{(rate_new != rate_old).sum()} out of {len(rate_new)} tasks have dropped pass rate"
    )

    ntask = len(rate_old)

    # sort by old pass rate
    # numpy argsort
    indices = np.array(rate_old).argsort()
    # find unsolved tasks. i.e., indices where rate_old == 0
    unsolved = np.where(np.array(rate_old) == 0)[0]
    print("Unsolvable: ", unsolved)
    # sort indices according to the differences between rate_old and rate_new
    diff = np.array(rate_old) - np.array(rate_new)
    diff_indices = diff.argsort()

    tasks = get_human_eval_plus()
    for i in reversed(diff_indices[-15:]):
        print(
            f"#{i} {tasks[f'HumanEval/{i}']['entry_point']} drops {diff[i] :.1f} ~ {100 * diff[i] / rate_old[i]:.1f}%:"
            f" {rate_old[i]:.1f} -> {rate_new[i]:.1f}"
        )

    rate_old = np.array(rate_old)[indices]
    rate_new = np.array(rate_new)[indices]
    # rate_old, rate_new = zip(*sorted(zip(rate_old, rate_new), key=lambda x: x[0]))

    # making a barplot
    x = np.arange(ntask)
    width = 1  # the width of the bars

    fig, ax = plt.subplots(figsize=(9, 3))
    HUMANEVAL = r"\textsc{HumanEval}"
    HUMANEVAL_PLUS = r"\textsc{HumanEval\textsuperscript{+}}"
    rects1 = ax.bar(x, rate_old, color="coral", label=HUMANEVAL, alpha=0.5)
    rects2 = ax.bar(x, rate_new, color="firebrick", label=HUMANEVAL_PLUS, alpha=0.6)

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel("Average Pass Rate (\%)")
    ax.set_xlabel(f"Problems (Sorted by {HUMANEVAL} pass rate)")

    # turn off xticks
    ax.set_xticks([])
    ax.set_xticklabels([])
    # tight x ranges
    ax.set_xlim(-0.5, ntask - 0.5)

    # x grid
    ax.grid(linestyle="--", linewidth=1, alpha=0.8)

    # log scale
    ax.set_yscale("log")

    ax.legend()
    fig.tight_layout()

    plt.savefig("passrate.pdf", bbox_inches="tight")
    plt.savefig("passrate.png", bbox_inches="tight")

# === NexusCore/evaluation\evalplus\evalplus\data\mbpp.py ===
import hashlib
import json
import os
from typing import Dict

import wget

from evalplus.data.utils import (
    CACHE_DIR,
    completeness_check,
    get_dataset_metadata,
    make_cache,
    stream_jsonl,
)

MBPP_PLUS_VERSION = "v0.2.0"
MBPP_OVERRIDE_PATH = os.environ.get("MBPP_OVERRIDE_PATH", None)


def _ready_mbpp_plus_path(mini=False, noextreme=False, version="default") -> str:
    assert mini is False, "Mini version of MBPP+ is not available yet."

    if MBPP_OVERRIDE_PATH:
        return MBPP_OVERRIDE_PATH

    version = MBPP_PLUS_VERSION if version == "default" else version

    url, plus_path = get_dataset_metadata("MbppPlus", version, mini, noextreme)
    make_cache(url, plus_path)

    return plus_path


def mbpp_serialize_inputs(task_id: str, inputs: list) -> list:
    task_id = int(task_id.split("/")[-1])

    if task_id == 115:
        return [[[list(item) for item in inp[0]]] for inp in inputs]
    elif task_id == 124:
        return [(str(inp[0]), str(inp[1])) for inp in inputs]
    elif task_id == 252:
        return [[str(inp[0])] for inp in inputs]

    return inputs


def mbpp_deserialize_inputs(task_id: str, inputs: list) -> list:
    task_id = int(task_id.split("/")[-1])
    if task_id in [
        2,
        116,
        132,
        143,
        222,
        261,
        273,
        394,
        399,
        421,
        424,
        429,
        470,
        560,
        579,
        596,
        616,
        630,
        726,
        740,
        744,
        809,
    ]:
        modified_inputs = [[tuple(lst) for lst in inp] for inp in inputs]

    elif task_id in [
        63,
        64,
        70,
        94,
        120,
        237,
        272,
        299,
        400,
        409,
        417,
        438,
        473,
        614,
        780,
    ]:
        modified_inputs = [
            [[tuple(lst) for lst in lst_lst] for lst_lst in inp] for inp in inputs
        ]

    elif task_id in [75, 413, 444, 753]:
        modified_inputs = [
            [[tuple(lst) for lst in inp[0]]] + [inp[1]] for inp in inputs
        ]

    elif task_id == 106 or task_id == 750:
        modified_inputs = [[inp[0]] + [tuple(inp[1])] for inp in inputs]

    elif task_id == 115:
        modified_inputs = [
            [
                [
                    set(item) if isinstance(item, list) and len(item) else {}
                    for item in inp[0]
                ]
            ]
            for inp in inputs
        ]

    elif task_id == 124:
        modified_inputs = [(float(inp[0]), complex(inp[1])) for inp in inputs]

    elif task_id in [250, 405, 446, 617, 720, 763, 808]:
        modified_inputs = [[tuple(inp[0])] + [inp[1]] for inp in inputs]

    elif task_id in [259, 401, 445]:
        modified_inputs = [
            [[tuple(lst) for lst in lst_lst] for lst_lst in inp] for inp in inputs
        ]
        modified_inputs = [[tuple(lst) for lst in inp] for inp in modified_inputs]

    elif task_id == 278:
        modified_inputs = [
            [[tuple(item) if isinstance(item, list) else item for item in inp[0]]]
            for inp in inputs
        ]
        modified_inputs = [[tuple(lst) for lst in inp] for inp in modified_inputs]

    elif task_id == 307:
        modified_inputs = [[tuple(inp[0])] + [inp[1], inp[2]] for inp in inputs]

    elif task_id == 722:
        modified_inputs = [
            [{key: tuple(value) for key, value in inp[0].items()}] + inp[1:]
            for inp in inputs
        ]

    elif task_id == 252:
        modified_inputs = [[complex(inp[0])] for inp in inputs]

    elif task_id in [580, 615, 791]:

        def turn_all_list_into_tuple(inp):
            if isinstance(inp, list):
                return tuple([turn_all_list_into_tuple(item) for item in inp])
            return inp

        modified_inputs = [turn_all_list_into_tuple(inp) for inp in inputs]

    else:
        modified_inputs = inputs

    return modified_inputs


def get_mbpp() -> Dict[str, Dict]:
    """Get sanitized MBPP from Google's Github repo."""
    mbpp_path = os.path.join(CACHE_DIR, "sanitized-mbpp.json")

    if not os.path.exists(mbpp_path):
        os.makedirs(CACHE_DIR, exist_ok=True)

        # Install MBPP-sanitized from scratch
        print("Downloading original MBPP dataset...")
        wget.download(
            "https://github.com/google-research/google-research/raw/master/mbpp/sanitized-mbpp.json",
            mbpp_path,
        )

    with open(mbpp_path, "r") as f:
        mbpp = json.load(f)

    return {str(task["task_id"]): task for task in mbpp}


def get_mbpp_plus(
    err_incomplete=True, mini=False, noextreme=False, version="default"
) -> Dict[str, Dict]:
    plus_path = _ready_mbpp_plus_path(mini=mini, noextreme=noextreme, version=version)
    plus = {task["task_id"]: task for task in stream_jsonl(plus_path)}
    for task_id, task in plus.items():
        task["base_input"] = mbpp_deserialize_inputs(task_id, task["base_input"])
        task["plus_input"] = mbpp_deserialize_inputs(task_id, task["plus_input"])

    if err_incomplete:
        completeness_check("MBPP+", plus)
    return plus


def get_mbpp_plus_hash(mini=False, noextreme=False, version="default") -> str:
    """Get the hash of MbppPlus.
    Returns:
        str: The hash of MbppPlus
    """
    plus_path = _ready_mbpp_plus_path(mini=mini, noextreme=noextreme, version=version)
    with open(plus_path, "rb") as f:
        plus = f.read()
    return hashlib.md5(plus).hexdigest()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\style.py ===
"""
    pygments.style
    ~~~~~~~~~~~~~~

    Basic style object.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pip._vendor.pygments.token import Token, STANDARD_TYPES

# Default mapping of ansixxx to RGB colors.
_ansimap = {
    # dark
    'ansiblack': '000000',
    'ansired': '7f0000',
    'ansigreen': '007f00',
    'ansiyellow': '7f7fe0',
    'ansiblue': '00007f',
    'ansimagenta': '7f007f',
    'ansicyan': '007f7f',
    'ansigray': 'e5e5e5',
    # normal
    'ansibrightblack': '555555',
    'ansibrightred': 'ff0000',
    'ansibrightgreen': '00ff00',
    'ansibrightyellow': 'ffff00',
    'ansibrightblue': '0000ff',
    'ansibrightmagenta': 'ff00ff',
    'ansibrightcyan': '00ffff',
    'ansiwhite': 'ffffff',
}
# mapping of deprecated #ansixxx colors to new color names
_deprecated_ansicolors = {
    # dark
    '#ansiblack': 'ansiblack',
    '#ansidarkred': 'ansired',
    '#ansidarkgreen': 'ansigreen',
    '#ansibrown': 'ansiyellow',
    '#ansidarkblue': 'ansiblue',
    '#ansipurple': 'ansimagenta',
    '#ansiteal': 'ansicyan',
    '#ansilightgray': 'ansigray',
    # normal
    '#ansidarkgray': 'ansibrightblack',
    '#ansired': 'ansibrightred',
    '#ansigreen': 'ansibrightgreen',
    '#ansiyellow': 'ansibrightyellow',
    '#ansiblue': 'ansibrightblue',
    '#ansifuchsia': 'ansibrightmagenta',
    '#ansiturquoise': 'ansibrightcyan',
    '#ansiwhite': 'ansiwhite',
}
ansicolors = set(_ansimap)


class StyleMeta(type):

    def __new__(mcs, name, bases, dct):
        obj = type.__new__(mcs, name, bases, dct)
        for token in STANDARD_TYPES:
            if token not in obj.styles:
                obj.styles[token] = ''

        def colorformat(text):
            if text in ansicolors:
                return text
            if text[0:1] == '#':
                col = text[1:]
                if len(col) == 6:
                    return col
                elif len(col) == 3:
                    return col[0] * 2 + col[1] * 2 + col[2] * 2
            elif text == '':
                return ''
            elif text.startswith('var') or text.startswith('calc'):
                return text
            assert False, f"wrong color format {text!r}"

        _styles = obj._styles = {}

        for ttype in obj.styles:
            for token in ttype.split():
                if token in _styles:
                    continue
                ndef = _styles.get(token.parent, None)
                styledefs = obj.styles.get(token, '').split()
                if not ndef or token is None:
                    ndef = ['', 0, 0, 0, '', '', 0, 0, 0]
                elif 'noinherit' in styledefs and token is not Token:
                    ndef = _styles[Token][:]
                else:
                    ndef = ndef[:]
                _styles[token] = ndef
                for styledef in obj.styles.get(token, '').split():
                    if styledef == 'noinherit':
                        pass
                    elif styledef == 'bold':
                        ndef[1] = 1
                    elif styledef == 'nobold':
                        ndef[1] = 0
                    elif styledef == 'italic':
                        ndef[2] = 1
                    elif styledef == 'noitalic':
                        ndef[2] = 0
                    elif styledef == 'underline':
                        ndef[3] = 1
                    elif styledef == 'nounderline':
                        ndef[3] = 0
                    elif styledef[:3] == 'bg:':
                        ndef[4] = colorformat(styledef[3:])
                    elif styledef[:7] == 'border:':
                        ndef[5] = colorformat(styledef[7:])
                    elif styledef == 'roman':
                        ndef[6] = 1
                    elif styledef == 'sans':
                        ndef[7] = 1
                    elif styledef == 'mono':
                        ndef[8] = 1
                    else:
                        ndef[0] = colorformat(styledef)

        return obj

    def style_for_token(cls, token):
        t = cls._styles[token]
        ansicolor = bgansicolor = None
        color = t[0]
        if color in _deprecated_ansicolors:
            color = _deprecated_ansicolors[color]
        if color in ansicolors:
            ansicolor = color
            color = _ansimap[color]
        bgcolor = t[4]
        if bgcolor in _deprecated_ansicolors:
            bgcolor = _deprecated_ansicolors[bgcolor]
        if bgcolor in ansicolors:
            bgansicolor = bgcolor
            bgcolor = _ansimap[bgcolor]

        return {
            'color':        color or None,
            'bold':         bool(t[1]),
            'italic':       bool(t[2]),
            'underline':    bool(t[3]),
            'bgcolor':      bgcolor or None,
            'border':       t[5] or None,
            'roman':        bool(t[6]) or None,
            'sans':         bool(t[7]) or None,
            'mono':         bool(t[8]) or None,
            'ansicolor':    ansicolor,
            'bgansicolor':  bgansicolor,
        }

    def list_styles(cls):
        return list(cls)

    def styles_token(cls, ttype):
        return ttype in cls._styles

    def __iter__(cls):
        for token in cls._styles:
            yield token, cls.style_for_token(token)

    def __len__(cls):
        return len(cls._styles)


class Style(metaclass=StyleMeta):

    #: overall background color (``None`` means transparent)
    background_color = '#ffffff'

    #: highlight background color
    highlight_color = '#ffffcc'

    #: line number font color
    line_number_color = 'inherit'

    #: line number background color
    line_number_background_color = 'transparent'

    #: special line number font color
    line_number_special_color = '#000000'

    #: special line number background color
    line_number_special_background_color = '#ffffc0'

    #: Style definitions for individual token types.
    styles = {}

    #: user-friendly style name (used when selecting the style, so this
    # should be all-lowercase, no spaces, hyphens)
    name = 'unnamed'

    aliases = []

    # Attribute for lexers defined within Pygments. If set
    # to True, the style is not shown in the style gallery
    # on the website. This is intended for language-specific
    # styles.
    web_style_gallery_exclude = False

# === NexusCore/openenv\Lib\site-packages\contourpy\typecheck.py ===
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import numpy as np

from contourpy import FillType, LineType
from contourpy.enum_util import as_fill_type, as_line_type
from contourpy.types import MOVETO, code_dtype, offset_dtype, point_dtype

if TYPE_CHECKING:
    import contourpy._contourpy as cpy


# Minimalist array-checking functions that check dtype, ndims and shape only.
# They do not walk the arrays to check the contents for performance reasons.
def check_code_array(codes: Any) -> None:
    if not isinstance(codes, np.ndarray):
        raise TypeError(f"Expected numpy array not {type(codes)}")
    if codes.dtype != code_dtype:
        raise ValueError(f"Expected numpy array of dtype {code_dtype} not {codes.dtype}")
    if not (codes.ndim == 1 and len(codes) > 1):
        raise ValueError(f"Expected numpy array of shape (?,) not {codes.shape}")
    if codes[0] != MOVETO:
        raise ValueError(f"First element of code array must be {MOVETO}, not {codes[0]}")


def check_offset_array(offsets: Any) -> None:
    if not isinstance(offsets, np.ndarray):
        raise TypeError(f"Expected numpy array not {type(offsets)}")
    if offsets.dtype != offset_dtype:
        raise ValueError(f"Expected numpy array of dtype {offset_dtype} not {offsets.dtype}")
    if not (offsets.ndim == 1 and len(offsets) > 1):
        raise ValueError(f"Expected numpy array of shape (?,) not {offsets.shape}")
    if offsets[0] != 0:
        raise ValueError(f"First element of offset array must be 0, not {offsets[0]}")


def check_point_array(points: Any) -> None:
    if not isinstance(points, np.ndarray):
        raise TypeError(f"Expected numpy array not {type(points)}")
    if points.dtype != point_dtype:
        raise ValueError(f"Expected numpy array of dtype {point_dtype} not {points.dtype}")
    if not (points.ndim == 2 and points.shape[1] ==2 and points.shape[0] > 1):
        raise ValueError(f"Expected numpy array of shape (?, 2) not {points.shape}")


def _check_tuple_of_lists_with_same_length(
    maybe_tuple: Any,
    tuple_length: int,
    allow_empty_lists: bool = True,
) -> None:
    if not isinstance(maybe_tuple, tuple):
        raise TypeError(f"Expected tuple not {type(maybe_tuple)}")
    if len(maybe_tuple) != tuple_length:
        raise ValueError(f"Expected tuple of length {tuple_length} not {len(maybe_tuple)}")
    for maybe_list in maybe_tuple:
        if not isinstance(maybe_list, list):
            msg = f"Expected tuple to contain {tuple_length} lists but found a {type(maybe_list)}"
            raise TypeError(msg)
    lengths = [len(item) for item in maybe_tuple]
    if len(set(lengths)) != 1:
        msg = f"Expected {tuple_length} lists with same length but lengths are {lengths}"
        raise ValueError(msg)
    if not allow_empty_lists and lengths[0] == 0:
        raise ValueError(f"Expected {tuple_length} non-empty lists")


def check_filled(filled: cpy.FillReturn, fill_type: FillType | str) -> None:
    fill_type = as_fill_type(fill_type)

    if fill_type == FillType.OuterCode:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_OuterCode, filled)
        _check_tuple_of_lists_with_same_length(filled, 2)
        for i, (points, codes) in enumerate(zip(*filled)):
            check_point_array(points)
            check_code_array(codes)
            if len(points) != len(codes):
                raise ValueError(f"Points and codes have different lengths in polygon {i}")
    elif fill_type == FillType.OuterOffset:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_OuterOffset, filled)
        _check_tuple_of_lists_with_same_length(filled, 2)
        for i, (points, offsets) in enumerate(zip(*filled)):
            check_point_array(points)
            check_offset_array(offsets)
            if offsets[-1] != len(points):
                raise ValueError(f"Inconsistent points and offsets in polygon {i}")
    elif fill_type == FillType.ChunkCombinedCode:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_ChunkCombinedCode, filled)
        _check_tuple_of_lists_with_same_length(filled, 2, allow_empty_lists=False)
        for chunk, (points_or_none, codes_or_none) in enumerate(zip(*filled)):
            if points_or_none is not None and codes_or_none is not None:
                check_point_array(points_or_none)
                check_code_array(codes_or_none)
                if len(points_or_none) != len(codes_or_none):
                    raise ValueError(f"Points and codes have different lengths in chunk {chunk}")
            elif not (points_or_none is None and codes_or_none is None):
                raise ValueError(f"Inconsistent Nones in chunk {chunk}")
    elif fill_type == FillType.ChunkCombinedOffset:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_ChunkCombinedOffset, filled)
        _check_tuple_of_lists_with_same_length(filled, 2, allow_empty_lists=False)
        for chunk, (points_or_none, offsets_or_none) in enumerate(zip(*filled)):
            if points_or_none is not None and offsets_or_none is not None:
                check_point_array(points_or_none)
                check_offset_array(offsets_or_none)
                if offsets_or_none[-1] != len(points_or_none):
                    raise ValueError(f"Inconsistent points and offsets in chunk {chunk}")
            elif not (points_or_none is None and offsets_or_none is None):
                raise ValueError(f"Inconsistent Nones in chunk {chunk}")
    elif fill_type == FillType.ChunkCombinedCodeOffset:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_ChunkCombinedCodeOffset, filled)
        _check_tuple_of_lists_with_same_length(filled, 3, allow_empty_lists=False)
        for i, (points_or_none, codes_or_none, outer_offsets_or_none) in enumerate(zip(*filled)):
            if (points_or_none is not None and codes_or_none is not None and
                    outer_offsets_or_none is not None):
                check_point_array(points_or_none)
                check_code_array(codes_or_none)
                check_offset_array(outer_offsets_or_none)
                if len(codes_or_none) != len(points_or_none):
                    raise ValueError(f"Points and codes have different lengths in chunk {i}")
                if outer_offsets_or_none[-1] != len(codes_or_none):
                    raise ValueError(f"Inconsistent codes and outer_offsets in chunk {i}")
            elif not (points_or_none is None and codes_or_none is None and
                      outer_offsets_or_none is None):
                raise ValueError(f"Inconsistent Nones in chunk {i}")
    elif fill_type == FillType.ChunkCombinedOffsetOffset:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_ChunkCombinedOffsetOffset, filled)
        _check_tuple_of_lists_with_same_length(filled, 3, allow_empty_lists=False)
        for i, (points_or_none, offsets_or_none, outer_offsets_or_none) in enumerate(zip(*filled)):
            if (points_or_none is not None and offsets_or_none is not None and
                    outer_offsets_or_none is not None):
                check_point_array(points_or_none)
                check_offset_array(offsets_or_none)
                check_offset_array(outer_offsets_or_none)
                if offsets_or_none[-1] != len(points_or_none):
                    raise ValueError(f"Inconsistent points and offsets in chunk {i}")
                if outer_offsets_or_none[-1] != len(offsets_or_none) - 1:
                    raise ValueError(f"Inconsistent offsets and outer_offsets in chunk {i}")
            elif not (points_or_none is None and offsets_or_none is None and
                      outer_offsets_or_none is None):
                raise ValueError(f"Inconsistent Nones in chunk {i}")
    else:
        raise ValueError(f"Invalid FillType {fill_type}")


def check_lines(lines: cpy.LineReturn, line_type: LineType | str) -> None:
    line_type = as_line_type(line_type)

    if line_type == LineType.Separate:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_Separate, lines)
        if not isinstance(lines, list):
            raise TypeError(f"Expected list not {type(lines)}")
        for points in lines:
            check_point_array(points)
    elif line_type == LineType.SeparateCode:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_SeparateCode, lines)
        _check_tuple_of_lists_with_same_length(lines, 2)
        for i, (points, codes) in enumerate(zip(*lines)):
            check_point_array(points)
            check_code_array(codes)
            if len(points) != len(codes):
                raise ValueError(f"Points and codes have different lengths in line {i}")
    elif line_type == LineType.ChunkCombinedCode:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_ChunkCombinedCode, lines)
        _check_tuple_of_lists_with_same_length(lines, 2, allow_empty_lists=False)
        for chunk, (points_or_none, codes_or_none) in enumerate(zip(*lines)):
            if points_or_none is not None and codes_or_none is not None:
                check_point_array(points_or_none)
                check_code_array(codes_or_none)
                if len(points_or_none) != len(codes_or_none):
                    raise ValueError(f"Points and codes have different lengths in chunk {chunk}")
            elif not (points_or_none is None and codes_or_none is None):
                raise ValueError(f"Inconsistent Nones in chunk {chunk}")
    elif line_type == LineType.ChunkCombinedOffset:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_ChunkCombinedOffset, lines)
        _check_tuple_of_lists_with_same_length(lines, 2, allow_empty_lists=False)
        for chunk, (points_or_none, offsets_or_none) in enumerate(zip(*lines)):
            if points_or_none is not None and offsets_or_none is not None:
                check_point_array(points_or_none)
                check_offset_array(offsets_or_none)
                if offsets_or_none[-1] != len(points_or_none):
                    raise ValueError(f"Inconsistent points and offsets in chunk {chunk}")
            elif not (points_or_none is None and offsets_or_none is None):
                raise ValueError(f"Inconsistent Nones in chunk {chunk}")
    elif line_type == LineType.ChunkCombinedNan:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_ChunkCombinedNan, lines)
        _check_tuple_of_lists_with_same_length(lines, 1, allow_empty_lists=False)
        for _chunk, points_or_none in enumerate(lines[0]):
            if points_or_none is not None:
                check_point_array(points_or_none)
    else:
        raise ValueError(f"Invalid LineType {line_type}")

# === NexusCore/openenv\Lib\site-packages\ipykernel\serialize.py ===
"""serialization utilities for apply messages"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import pickle
import warnings
from itertools import chain

try:
    # available since ipyparallel 5.0.0
    from ipyparallel.serialize.canning import (
        CannedObject,
        can,
        can_sequence,
        istype,
        sequence_types,
        uncan,
        uncan_sequence,
    )
    from ipyparallel.serialize.serialize import PICKLE_PROTOCOL
except ImportError:
    # Deprecated since ipykernel 4.3.0
    from ipykernel.pickleutil import (
        PICKLE_PROTOCOL,
        CannedObject,
        can,
        can_sequence,
        istype,
        sequence_types,
        uncan,
        uncan_sequence,
    )

from jupyter_client.session import MAX_BYTES, MAX_ITEMS

warnings.warn(
    "ipykernel.serialize is deprecated. It has moved to ipyparallel.serialize",
    DeprecationWarning,
    stacklevel=2,
)

# -----------------------------------------------------------------------------
# Serialization Functions
# -----------------------------------------------------------------------------


def _extract_buffers(obj, threshold=MAX_BYTES):
    """extract buffers larger than a certain threshold"""
    buffers = []
    if isinstance(obj, CannedObject) and obj.buffers:
        for i, buf in enumerate(obj.buffers):
            if len(buf) > threshold:
                # buffer larger than threshold, prevent pickling
                obj.buffers[i] = None
                buffers.append(buf)
            # buffer too small for separate send, coerce to bytes
            # because pickling buffer objects just results in broken pointers
            elif isinstance(buf, memoryview):
                obj.buffers[i] = buf.tobytes()
    return buffers


def _restore_buffers(obj, buffers):
    """restore buffers extracted by"""
    if isinstance(obj, CannedObject) and obj.buffers:
        for i, buf in enumerate(obj.buffers):
            if buf is None:
                obj.buffers[i] = buffers.pop(0)


def serialize_object(obj, buffer_threshold=MAX_BYTES, item_threshold=MAX_ITEMS):
    """Serialize an object into a list of sendable buffers.

    Parameters
    ----------
    obj : object
        The object to be serialized
    buffer_threshold : int
        The threshold (in bytes) for pulling out data buffers
        to avoid pickling them.
    item_threshold : int
        The maximum number of items over which canning will iterate.
        Containers (lists, dicts) larger than this will be pickled without
        introspection.

    Returns
    -------
    [bufs] : list of buffers representing the serialized object.
    """
    buffers = []
    if istype(obj, sequence_types) and len(obj) < item_threshold:
        cobj = can_sequence(obj)
        for c in cobj:
            buffers.extend(_extract_buffers(c, buffer_threshold))
    elif istype(obj, dict) and len(obj) < item_threshold:
        cobj = {}
        for k in sorted(obj):
            c = can(obj[k])
            buffers.extend(_extract_buffers(c, buffer_threshold))
            cobj[k] = c
    else:
        cobj = can(obj)
        buffers.extend(_extract_buffers(cobj, buffer_threshold))

    buffers.insert(0, pickle.dumps(cobj, PICKLE_PROTOCOL))
    return buffers


def deserialize_object(buffers, g=None):
    """reconstruct an object serialized by serialize_object from data buffers.

    Parameters
    ----------
    buffers : list of buffers/bytes
    g : globals to be used when uncanning

    Returns
    -------
    (newobj, bufs) : unpacked object, and the list of remaining unused buffers.
    """
    bufs = list(buffers)
    pobj = bufs.pop(0)
    canned = pickle.loads(pobj)
    if istype(canned, sequence_types) and len(canned) < MAX_ITEMS:
        for c in canned:
            _restore_buffers(c, bufs)
        newobj = uncan_sequence(canned, g)
    elif istype(canned, dict) and len(canned) < MAX_ITEMS:
        newobj = {}
        for k in sorted(canned):
            c = canned[k]
            _restore_buffers(c, bufs)
            newobj[k] = uncan(c, g)
    else:
        _restore_buffers(canned, bufs)
        newobj = uncan(canned, g)

    return newobj, bufs


def pack_apply_message(f, args, kwargs, buffer_threshold=MAX_BYTES, item_threshold=MAX_ITEMS):
    """pack up a function, args, and kwargs to be sent over the wire

    Each element of args/kwargs will be canned for special treatment,
    but inspection will not go any deeper than that.

    Any object whose data is larger than `threshold`  will not have their data copied
    (only numpy arrays and bytes/buffers support zero-copy)

    Message will be a list of bytes/buffers of the format:

    [ cf, pinfo, <arg_bufs>, <kwarg_bufs> ]

    With length at least two + len(args) + len(kwargs)
    """

    arg_bufs = list(
        chain.from_iterable(serialize_object(arg, buffer_threshold, item_threshold) for arg in args)
    )

    kw_keys = sorted(kwargs.keys())
    kwarg_bufs = list(
        chain.from_iterable(
            serialize_object(kwargs[key], buffer_threshold, item_threshold) for key in kw_keys
        )
    )

    info = dict(nargs=len(args), narg_bufs=len(arg_bufs), kw_keys=kw_keys)

    msg = [pickle.dumps(can(f), PICKLE_PROTOCOL)]
    msg.append(pickle.dumps(info, PICKLE_PROTOCOL))
    msg.extend(arg_bufs)
    msg.extend(kwarg_bufs)

    return msg


def unpack_apply_message(bufs, g=None, copy=True):
    """unpack f,args,kwargs from buffers packed by pack_apply_message()
    Returns: original f,args,kwargs"""
    bufs = list(bufs)  # allow us to pop
    assert len(bufs) >= 2, "not enough buffers!"
    pf = bufs.pop(0)
    f = uncan(pickle.loads(pf), g)
    pinfo = bufs.pop(0)
    info = pickle.loads(pinfo)
    arg_bufs, kwarg_bufs = bufs[: info["narg_bufs"]], bufs[info["narg_bufs"] :]

    args_list = []
    for _ in range(info["nargs"]):
        arg, arg_bufs = deserialize_object(arg_bufs, g)
        args_list.append(arg)
    args = tuple(args_list)
    assert not arg_bufs, "Shouldn't be any arg bufs left over"

    kwargs = {}
    for key in info["kw_keys"]:
        kwarg, kwarg_bufs = deserialize_object(kwarg_bufs, g)
        kwargs[key] = kwarg
    assert not kwarg_bufs, "Shouldn't be any kwarg bufs left over"

    return f, args, kwargs

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc3739.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
# Modified by Russ Housley to add WithComponentsConstraints to
#   enforce the requirements that are indicated in comments.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Qualified Certificates
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc3739.txt
#

from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import opentype
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc5280

MAX = float('inf')


# Initialize the qcStatement map

qcStatementMap = { }


# Imports from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier

AttributeType = rfc5280.AttributeType

DirectoryString = rfc5280.DirectoryString

GeneralName = rfc5280.GeneralName

id_pkix = rfc5280.id_pkix

id_pe = rfc5280.id_pe


# Arc for QC personal data attributes

id_pda = id_pkix + (9, )


# Arc for QC statements

id_qcs = id_pkix + (11, )


# Personal data attributes

id_pda_dateOfBirth = id_pda + (1, )

class DateOfBirth(useful.GeneralizedTime):
    pass


id_pda_placeOfBirth = id_pda + (2, )

class PlaceOfBirth(DirectoryString):
    pass


id_pda_gender = id_pda + (3, )

class Gender(char.PrintableString):
    subtypeSpec = constraint.ConstraintsIntersection(
        constraint.ValueSizeConstraint(1, 1),
        constraint.SingleValueConstraint('M', 'F', 'm', 'f')
    )


id_pda_countryOfCitizenship = id_pda + (4, )

class CountryOfCitizenship(char.PrintableString):
    subtypeSpec = constraint.ValueSizeConstraint(2, 2)
    # ISO 3166 Country Code


id_pda_countryOfResidence = id_pda + (5, )

class CountryOfResidence(char.PrintableString):
    subtypeSpec = constraint.ValueSizeConstraint(2, 2)
    # ISO 3166 Country Code


# Biometric info certificate extension

id_pe_biometricInfo = id_pe + (2, )


class PredefinedBiometricType(univ.Integer):
    namedValues = namedval.NamedValues(
        ('picture', 0),
        ('handwritten-signature', 1)
    )
    subtypeSpec = constraint.SingleValueConstraint(0, 1)


class TypeOfBiometricData(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('predefinedBiometricType', PredefinedBiometricType()),
        namedtype.NamedType('biometricDataOid', univ.ObjectIdentifier())
    )


class BiometricData(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('typeOfBiometricData', TypeOfBiometricData()),
        namedtype.NamedType('hashAlgorithm', AlgorithmIdentifier()),
        namedtype.NamedType('biometricDataHash', univ.OctetString()),
        namedtype.OptionalNamedType('sourceDataUri', char.IA5String())
    )


class BiometricSyntax(univ.SequenceOf):
    componentType = BiometricData()


# QC Statements certificate extension
# NOTE: This extension does not allow to mix critical and
# non-critical Qualified Certificate Statements. Either all
# statements must be critical or all statements must be
# non-critical.

id_pe_qcStatements = id_pe + (3, )


class NameRegistrationAuthorities(univ.SequenceOf):
    componentType = GeneralName()
    subtypeSpec=constraint.ValueSizeConstraint(1, MAX)


class QCStatement(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('statementId', univ.ObjectIdentifier()),
        namedtype.OptionalNamedType('statementInfo', univ.Any(),
            openType=opentype.OpenType('statementId', qcStatementMap))
    )


class QCStatements(univ.SequenceOf):
    componentType = QCStatement()


class SemanticsInformation(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('semanticsIndentifier',
            univ.ObjectIdentifier()),
        namedtype.OptionalNamedType('nameRegistrationAuthorities',
            NameRegistrationAuthorities())
    )
    subtypeSpec = constraint.ConstraintsUnion(
        constraint.WithComponentsConstraint(
            ('semanticsIndentifier', constraint.ComponentPresentConstraint())),
        constraint.WithComponentsConstraint(
            ('nameRegistrationAuthorities', constraint.ComponentPresentConstraint()))
    )


id_qcs = id_pkix + (11, )


id_qcs_pkixQCSyntax_v1 = id_qcs + (1, )


id_qcs_pkixQCSyntax_v2 = id_qcs + (2, )


# Map of Certificate Extension OIDs to Extensions
# To be added to the ones that are in rfc5280.py

_certificateExtensionsMap = {
     id_pe_biometricInfo: BiometricSyntax(),
     id_pe_qcStatements: QCStatements(),
}

rfc5280.certificateExtensionsMap.update(_certificateExtensionsMap)


# Map of AttributeType OIDs to AttributeValue added to the
# ones that are in rfc5280.py

_certificateAttributesMapUpdate = {
    id_pda_dateOfBirth: DateOfBirth(),
    id_pda_placeOfBirth: PlaceOfBirth(),
    id_pda_gender: Gender(),
    id_pda_countryOfCitizenship: CountryOfCitizenship(),
    id_pda_countryOfResidence: CountryOfResidence(),
}

rfc5280.certificateAttributesMap.update(_certificateAttributesMapUpdate)


# === NexusCore/openenv\Lib\site-packages\pygments\style.py ===
"""
    pygments.style
    ~~~~~~~~~~~~~~

    Basic style object.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.token import Token, STANDARD_TYPES

# Default mapping of ansixxx to RGB colors.
_ansimap = {
    # dark
    'ansiblack': '000000',
    'ansired': '7f0000',
    'ansigreen': '007f00',
    'ansiyellow': '7f7fe0',
    'ansiblue': '00007f',
    'ansimagenta': '7f007f',
    'ansicyan': '007f7f',
    'ansigray': 'e5e5e5',
    # normal
    'ansibrightblack': '555555',
    'ansibrightred': 'ff0000',
    'ansibrightgreen': '00ff00',
    'ansibrightyellow': 'ffff00',
    'ansibrightblue': '0000ff',
    'ansibrightmagenta': 'ff00ff',
    'ansibrightcyan': '00ffff',
    'ansiwhite': 'ffffff',
}
# mapping of deprecated #ansixxx colors to new color names
_deprecated_ansicolors = {
    # dark
    '#ansiblack': 'ansiblack',
    '#ansidarkred': 'ansired',
    '#ansidarkgreen': 'ansigreen',
    '#ansibrown': 'ansiyellow',
    '#ansidarkblue': 'ansiblue',
    '#ansipurple': 'ansimagenta',
    '#ansiteal': 'ansicyan',
    '#ansilightgray': 'ansigray',
    # normal
    '#ansidarkgray': 'ansibrightblack',
    '#ansired': 'ansibrightred',
    '#ansigreen': 'ansibrightgreen',
    '#ansiyellow': 'ansibrightyellow',
    '#ansiblue': 'ansibrightblue',
    '#ansifuchsia': 'ansibrightmagenta',
    '#ansiturquoise': 'ansibrightcyan',
    '#ansiwhite': 'ansiwhite',
}
ansicolors = set(_ansimap)


class StyleMeta(type):

    def __new__(mcs, name, bases, dct):
        obj = type.__new__(mcs, name, bases, dct)
        for token in STANDARD_TYPES:
            if token not in obj.styles:
                obj.styles[token] = ''

        def colorformat(text):
            if text in ansicolors:
                return text
            if text[0:1] == '#':
                col = text[1:]
                if len(col) == 6:
                    return col
                elif len(col) == 3:
                    return col[0] * 2 + col[1] * 2 + col[2] * 2
            elif text == '':
                return ''
            elif text.startswith('var') or text.startswith('calc'):
                return text
            assert False, f"wrong color format {text!r}"

        _styles = obj._styles = {}

        for ttype in obj.styles:
            for token in ttype.split():
                if token in _styles:
                    continue
                ndef = _styles.get(token.parent, None)
                styledefs = obj.styles.get(token, '').split()
                if not ndef or token is None:
                    ndef = ['', 0, 0, 0, '', '', 0, 0, 0]
                elif 'noinherit' in styledefs and token is not Token:
                    ndef = _styles[Token][:]
                else:
                    ndef = ndef[:]
                _styles[token] = ndef
                for styledef in obj.styles.get(token, '').split():
                    if styledef == 'noinherit':
                        pass
                    elif styledef == 'bold':
                        ndef[1] = 1
                    elif styledef == 'nobold':
                        ndef[1] = 0
                    elif styledef == 'italic':
                        ndef[2] = 1
                    elif styledef == 'noitalic':
                        ndef[2] = 0
                    elif styledef == 'underline':
                        ndef[3] = 1
                    elif styledef == 'nounderline':
                        ndef[3] = 0
                    elif styledef[:3] == 'bg:':
                        ndef[4] = colorformat(styledef[3:])
                    elif styledef[:7] == 'border:':
                        ndef[5] = colorformat(styledef[7:])
                    elif styledef == 'roman':
                        ndef[6] = 1
                    elif styledef == 'sans':
                        ndef[7] = 1
                    elif styledef == 'mono':
                        ndef[8] = 1
                    else:
                        ndef[0] = colorformat(styledef)

        return obj

    def style_for_token(cls, token):
        t = cls._styles[token]
        ansicolor = bgansicolor = None
        color = t[0]
        if color in _deprecated_ansicolors:
            color = _deprecated_ansicolors[color]
        if color in ansicolors:
            ansicolor = color
            color = _ansimap[color]
        bgcolor = t[4]
        if bgcolor in _deprecated_ansicolors:
            bgcolor = _deprecated_ansicolors[bgcolor]
        if bgcolor in ansicolors:
            bgansicolor = bgcolor
            bgcolor = _ansimap[bgcolor]

        return {
            'color':        color or None,
            'bold':         bool(t[1]),
            'italic':       bool(t[2]),
            'underline':    bool(t[3]),
            'bgcolor':      bgcolor or None,
            'border':       t[5] or None,
            'roman':        bool(t[6]) or None,
            'sans':         bool(t[7]) or None,
            'mono':         bool(t[8]) or None,
            'ansicolor':    ansicolor,
            'bgansicolor':  bgansicolor,
        }

    def list_styles(cls):
        return list(cls)

    def styles_token(cls, ttype):
        return ttype in cls._styles

    def __iter__(cls):
        for token in cls._styles:
            yield token, cls.style_for_token(token)

    def __len__(cls):
        return len(cls._styles)


class Style(metaclass=StyleMeta):

    #: overall background color (``None`` means transparent)
    background_color = '#ffffff'

    #: highlight background color
    highlight_color = '#ffffcc'

    #: line number font color
    line_number_color = 'inherit'

    #: line number background color
    line_number_background_color = 'transparent'

    #: special line number font color
    line_number_special_color = '#000000'

    #: special line number background color
    line_number_special_background_color = '#ffffc0'

    #: Style definitions for individual token types.
    styles = {}

    #: user-friendly style name (used when selecting the style, so this
    # should be all-lowercase, no spaces, hyphens)
    name = 'unnamed'

    aliases = []

    # Attribute for lexers defined within Pygments. If set
    # to True, the style is not shown in the style gallery
    # on the website. This is intended for language-specific
    # styles.
    web_style_gallery_exclude = False

# === NexusCore/openenv\Lib\site-packages\yarl\_parse.py ===
"""URL parsing utilities."""

import re
import unicodedata
from functools import lru_cache
from typing import Union
from urllib.parse import scheme_chars, uses_netloc

from ._quoters import QUOTER, UNQUOTER_PLUS

# Leading and trailing C0 control and space to be stripped per WHATWG spec.
# == "".join([chr(i) for i in range(0, 0x20 + 1)])
WHATWG_C0_CONTROL_OR_SPACE = (
    "\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10"
    "\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f "
)

# Unsafe bytes to be removed per WHATWG spec
UNSAFE_URL_BYTES_TO_REMOVE = ["\t", "\r", "\n"]
USES_AUTHORITY = frozenset(uses_netloc)

SplitURLType = tuple[str, str, str, str, str]


def split_url(url: str) -> SplitURLType:
    """Split URL into parts."""
    # Adapted from urllib.parse.urlsplit
    # Only lstrip url as some applications rely on preserving trailing space.
    # (https://url.spec.whatwg.org/#concept-basic-url-parser would strip both)
    url = url.lstrip(WHATWG_C0_CONTROL_OR_SPACE)
    for b in UNSAFE_URL_BYTES_TO_REMOVE:
        if b in url:
            url = url.replace(b, "")

    scheme = netloc = query = fragment = ""
    i = url.find(":")
    if i > 0 and url[0] in scheme_chars:
        for c in url[1:i]:
            if c not in scheme_chars:
                break
        else:
            scheme, url = url[:i].lower(), url[i + 1 :]
    has_hash = "#" in url
    has_question_mark = "?" in url
    if url[:2] == "//":
        delim = len(url)  # position of end of domain part of url, default is end
        if has_hash and has_question_mark:
            delim_chars = "/?#"
        elif has_question_mark:
            delim_chars = "/?"
        elif has_hash:
            delim_chars = "/#"
        else:
            delim_chars = "/"
        for c in delim_chars:  # look for delimiters; the order is NOT important
            wdelim = url.find(c, 2)  # find first of this delim
            if wdelim >= 0 and wdelim < delim:  # if found
                delim = wdelim  # use earliest delim position
        netloc = url[2:delim]
        url = url[delim:]
        has_left_bracket = "[" in netloc
        has_right_bracket = "]" in netloc
        if (has_left_bracket and not has_right_bracket) or (
            has_right_bracket and not has_left_bracket
        ):
            raise ValueError("Invalid IPv6 URL")
        if has_left_bracket:
            bracketed_host = netloc.partition("[")[2].partition("]")[0]
            # Valid bracketed hosts are defined in
            # https://www.rfc-editor.org/rfc/rfc3986#page-49
            # https://url.spec.whatwg.org/
            if bracketed_host and bracketed_host[0] == "v":
                if not re.match(r"\Av[a-fA-F0-9]+\..+\Z", bracketed_host):
                    raise ValueError("IPvFuture address is invalid")
            elif ":" not in bracketed_host:
                raise ValueError("The IPv6 content between brackets is not valid")
    if has_hash:
        url, _, fragment = url.partition("#")
    if has_question_mark:
        url, _, query = url.partition("?")
    if netloc and not netloc.isascii():
        _check_netloc(netloc)
    return scheme, netloc, url, query, fragment


def _check_netloc(netloc: str) -> None:
    # Adapted from urllib.parse._checknetloc
    # looking for characters like \u2100 that expand to 'a/c'
    # IDNA uses NFKC equivalence, so normalize for this check

    # ignore characters already included
    # but not the surrounding text
    n = netloc.replace("@", "").replace(":", "").replace("#", "").replace("?", "")
    normalized_netloc = unicodedata.normalize("NFKC", n)
    if n == normalized_netloc:
        return
    # Note that there are no unicode decompositions for the character '@' so
    # its currently impossible to have test coverage for this branch, however if the
    # one should be added in the future we want to make sure its still checked.
    for c in "/?#@:":  # pragma: no branch
        if c in normalized_netloc:
            raise ValueError(
                f"netloc '{netloc}' contains invalid "
                "characters under NFKC normalization"
            )


@lru_cache  # match the same size as urlsplit
def split_netloc(
    netloc: str,
) -> tuple[Union[str, None], Union[str, None], Union[str, None], Union[int, None]]:
    """Split netloc into username, password, host and port."""
    if "@" not in netloc:
        username: Union[str, None] = None
        password: Union[str, None] = None
        hostinfo = netloc
    else:
        userinfo, _, hostinfo = netloc.rpartition("@")
        username, have_password, password = userinfo.partition(":")
        if not have_password:
            password = None

    if "[" in hostinfo:
        _, _, bracketed = hostinfo.partition("[")
        hostname, _, port_str = bracketed.partition("]")
        _, _, port_str = port_str.partition(":")
    else:
        hostname, _, port_str = hostinfo.partition(":")

    if not port_str:
        return username or None, password, hostname or None, None

    try:
        port = int(port_str)
    except ValueError:
        raise ValueError("Invalid URL: port can't be converted to integer")
    if not (0 <= port <= 65535):
        raise ValueError("Port out of range 0-65535")
    return username or None, password, hostname or None, port


def unsplit_result(
    scheme: str, netloc: str, url: str, query: str, fragment: str
) -> str:
    """Unsplit a URL without any normalization."""
    if netloc or (scheme and scheme in USES_AUTHORITY) or url[:2] == "//":
        if url and url[:1] != "/":
            url = f"{scheme}://{netloc}/{url}" if scheme else f"{scheme}:{url}"
        else:
            url = f"{scheme}://{netloc}{url}" if scheme else f"//{netloc}{url}"
    elif scheme:
        url = f"{scheme}:{url}"
    if query:
        url = f"{url}?{query}"
    return f"{url}#{fragment}" if fragment else url


@lru_cache  # match the same size as urlsplit
def make_netloc(
    user: Union[str, None],
    password: Union[str, None],
    host: Union[str, None],
    port: Union[int, None],
    encode: bool = False,
) -> str:
    """Make netloc from parts.

    The user and password are encoded if encode is True.

    The host must already be encoded with _encode_host.
    """
    if host is None:
        return ""
    ret = host
    if port is not None:
        ret = f"{ret}:{port}"
    if user is None and password is None:
        return ret
    if password is not None:
        if not user:
            user = ""
        elif encode:
            user = QUOTER(user)
        if encode:
            password = QUOTER(password)
        user = f"{user}:{password}"
    elif user and encode:
        user = QUOTER(user)
    return f"{user}@{ret}" if user else ret


def query_to_pairs(query_string: str) -> list[tuple[str, str]]:
    """Parse a query given as a string argument.

    Works like urllib.parse.parse_qsl with keep empty values.
    """
    pairs: list[tuple[str, str]] = []
    if not query_string:
        return pairs
    for k_v in query_string.split("&"):
        k, _, v = k_v.partition("=")
        pairs.append((UNQUOTER_PLUS(k), UNQUOTER_PLUS(v)))
    return pairs

# === NexusCore/openenv\Lib\site-packages\anyio\abc\_streams.py ===
from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from typing import Any, Generic, TypeVar, Union

from .._core._exceptions import EndOfStream
from .._core._typedattr import TypedAttributeProvider
from ._resources import AsyncResource
from ._tasks import TaskGroup

T_Item = TypeVar("T_Item")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)


class UnreliableObjectReceiveStream(
    Generic[T_co], AsyncResource, TypedAttributeProvider
):
    """
    An interface for receiving objects.

    This interface makes no guarantees that the received messages arrive in the order in
    which they were sent, or that no messages are missed.

    Asynchronously iterating over objects of this type will yield objects matching the
    given type parameter.
    """

    def __aiter__(self) -> UnreliableObjectReceiveStream[T_co]:
        return self

    async def __anext__(self) -> T_co:
        try:
            return await self.receive()
        except EndOfStream:
            raise StopAsyncIteration

    @abstractmethod
    async def receive(self) -> T_co:
        """
        Receive the next item.

        :raises ~anyio.ClosedResourceError: if the receive stream has been explicitly
            closed
        :raises ~anyio.EndOfStream: if this stream has been closed from the other end
        :raises ~anyio.BrokenResourceError: if this stream has been rendered unusable
            due to external causes
        """


class UnreliableObjectSendStream(
    Generic[T_contra], AsyncResource, TypedAttributeProvider
):
    """
    An interface for sending objects.

    This interface makes no guarantees that the messages sent will reach the
    recipient(s) in the same order in which they were sent, or at all.
    """

    @abstractmethod
    async def send(self, item: T_contra) -> None:
        """
        Send an item to the peer(s).

        :param item: the item to send
        :raises ~anyio.ClosedResourceError: if the send stream has been explicitly
            closed
        :raises ~anyio.BrokenResourceError: if this stream has been rendered unusable
            due to external causes
        """


class UnreliableObjectStream(
    UnreliableObjectReceiveStream[T_Item], UnreliableObjectSendStream[T_Item]
):
    """
    A bidirectional message stream which does not guarantee the order or reliability of
    message delivery.
    """


class ObjectReceiveStream(UnreliableObjectReceiveStream[T_co]):
    """
    A receive message stream which guarantees that messages are received in the same
    order in which they were sent, and that no messages are missed.
    """


class ObjectSendStream(UnreliableObjectSendStream[T_contra]):
    """
    A send message stream which guarantees that messages are delivered in the same order
    in which they were sent, without missing any messages in the middle.
    """


class ObjectStream(
    ObjectReceiveStream[T_Item],
    ObjectSendStream[T_Item],
    UnreliableObjectStream[T_Item],
):
    """
    A bidirectional message stream which guarantees the order and reliability of message
    delivery.
    """

    @abstractmethod
    async def send_eof(self) -> None:
        """
        Send an end-of-file indication to the peer.

        You should not try to send any further data to this stream after calling this
        method. This method is idempotent (does nothing on successive calls).
        """


class ByteReceiveStream(AsyncResource, TypedAttributeProvider):
    """
    An interface for receiving bytes from a single peer.

    Iterating this byte stream will yield a byte string of arbitrary length, but no more
    than 65536 bytes.
    """

    def __aiter__(self) -> ByteReceiveStream:
        return self

    async def __anext__(self) -> bytes:
        try:
            return await self.receive()
        except EndOfStream:
            raise StopAsyncIteration

    @abstractmethod
    async def receive(self, max_bytes: int = 65536) -> bytes:
        """
        Receive at most ``max_bytes`` bytes from the peer.

        .. note:: Implementers of this interface should not return an empty
            :class:`bytes` object, and users should ignore them.

        :param max_bytes: maximum number of bytes to receive
        :return: the received bytes
        :raises ~anyio.EndOfStream: if this stream has been closed from the other end
        """


class ByteSendStream(AsyncResource, TypedAttributeProvider):
    """An interface for sending bytes to a single peer."""

    @abstractmethod
    async def send(self, item: bytes) -> None:
        """
        Send the given bytes to the peer.

        :param item: the bytes to send
        """


class ByteStream(ByteReceiveStream, ByteSendStream):
    """A bidirectional byte stream."""

    @abstractmethod
    async def send_eof(self) -> None:
        """
        Send an end-of-file indication to the peer.

        You should not try to send any further data to this stream after calling this
        method. This method is idempotent (does nothing on successive calls).
        """


#: Type alias for all unreliable bytes-oriented receive streams.
AnyUnreliableByteReceiveStream = Union[
    UnreliableObjectReceiveStream[bytes], ByteReceiveStream
]
#: Type alias for all unreliable bytes-oriented send streams.
AnyUnreliableByteSendStream = Union[UnreliableObjectSendStream[bytes], ByteSendStream]
#: Type alias for all unreliable bytes-oriented streams.
AnyUnreliableByteStream = Union[UnreliableObjectStream[bytes], ByteStream]
#: Type alias for all bytes-oriented receive streams.
AnyByteReceiveStream = Union[ObjectReceiveStream[bytes], ByteReceiveStream]
#: Type alias for all bytes-oriented send streams.
AnyByteSendStream = Union[ObjectSendStream[bytes], ByteSendStream]
#: Type alias for all bytes-oriented streams.
AnyByteStream = Union[ObjectStream[bytes], ByteStream]


class Listener(Generic[T_co], AsyncResource, TypedAttributeProvider):
    """An interface for objects that let you accept incoming connections."""

    @abstractmethod
    async def serve(
        self, handler: Callable[[T_co], Any], task_group: TaskGroup | None = None
    ) -> None:
        """
        Accept incoming connections as they come in and start tasks to handle them.

        :param handler: a callable that will be used to handle each accepted connection
        :param task_group: the task group that will be used to start tasks for handling
            each accepted connection (if omitted, an ad-hoc task group will be created)
        """

# === NexusCore/openenv\Lib\site-packages\fontTools\cffLib\CFF2ToCFF.py ===
"""CFF2 to CFF converter."""

from fontTools.ttLib import TTFont, newTable
from fontTools.misc.cliTools import makeOutputFileName
from fontTools.cffLib import (
    TopDictIndex,
    buildOrder,
    buildDefaults,
    topDictOperators,
    privateDictOperators,
)
from .width import optimizeWidths
from collections import defaultdict
import logging


__all__ = ["convertCFF2ToCFF", "main"]


log = logging.getLogger("fontTools.cffLib")


def _convertCFF2ToCFF(cff, otFont):
    """Converts this object from CFF2 format to CFF format. This conversion
    is done 'in-place'. The conversion cannot be reversed.

    The CFF2 font cannot be variable. (TODO Accept those and convert to the
    default instance?)

    This assumes a decompiled CFF table. (i.e. that the object has been
    filled via :meth:`decompile` and e.g. not loaded from XML.)"""

    cff.major = 1

    topDictData = TopDictIndex(None)
    for item in cff.topDictIndex:
        # Iterate over, such that all are decompiled
        item.cff2GetGlyphOrder = None
        topDictData.append(item)
    cff.topDictIndex = topDictData
    topDict = topDictData[0]

    if hasattr(topDict, "VarStore"):
        raise ValueError("Variable CFF2 font cannot be converted to CFF format.")

    opOrder = buildOrder(topDictOperators)
    topDict.order = opOrder
    for key in topDict.rawDict.keys():
        if key not in opOrder:
            del topDict.rawDict[key]
            if hasattr(topDict, key):
                delattr(topDict, key)

    fdArray = topDict.FDArray
    charStrings = topDict.CharStrings

    defaults = buildDefaults(privateDictOperators)
    order = buildOrder(privateDictOperators)
    for fd in fdArray:
        fd.setCFF2(False)
        privateDict = fd.Private
        privateDict.order = order
        for key in order:
            if key not in privateDict.rawDict and key in defaults:
                privateDict.rawDict[key] = defaults[key]
        for key in privateDict.rawDict.keys():
            if key not in order:
                del privateDict.rawDict[key]
                if hasattr(privateDict, key):
                    delattr(privateDict, key)

    for cs in charStrings.values():
        cs.decompile()
        cs.program.append("endchar")
    for subrSets in [cff.GlobalSubrs] + [
        getattr(fd.Private, "Subrs", []) for fd in fdArray
    ]:
        for cs in subrSets:
            cs.program.append("return")

    # Add (optimal) width to CharStrings that need it.
    widths = defaultdict(list)
    metrics = otFont["hmtx"].metrics
    for glyphName in charStrings.keys():
        cs, fdIndex = charStrings.getItemAndSelector(glyphName)
        if fdIndex == None:
            fdIndex = 0
        widths[fdIndex].append(metrics[glyphName][0])
    for fdIndex, widthList in widths.items():
        bestDefault, bestNominal = optimizeWidths(widthList)
        private = fdArray[fdIndex].Private
        private.defaultWidthX = bestDefault
        private.nominalWidthX = bestNominal
    for glyphName in charStrings.keys():
        cs, fdIndex = charStrings.getItemAndSelector(glyphName)
        if fdIndex == None:
            fdIndex = 0
        private = fdArray[fdIndex].Private
        width = metrics[glyphName][0]
        if width != private.defaultWidthX:
            cs.program.insert(0, width - private.nominalWidthX)

    mapping = {
        name: ("cid" + str(n) if n else ".notdef")
        for n, name in enumerate(topDict.charset)
    }
    topDict.charset = [
        "cid" + str(n) if n else ".notdef" for n in range(len(topDict.charset))
    ]
    charStrings.charStrings = {
        mapping[name]: v for name, v in charStrings.charStrings.items()
    }

    # I'm not sure why the following is *not* necessary. And it breaks
    # the output if I add it.
    # topDict.ROS = ("Adobe", "Identity", 0)


def convertCFF2ToCFF(font, *, updatePostTable=True):
    cff = font["CFF2"].cff
    _convertCFF2ToCFF(cff, font)
    del font["CFF2"]
    table = font["CFF "] = newTable("CFF ")
    table.cff = cff

    if updatePostTable and "post" in font:
        # Only version supported for fonts with CFF table is 0x00030000 not 0x20000
        post = font["post"]
        if post.formatType == 2.0:
            post.formatType = 3.0


def main(args=None):
    """Convert CFF OTF font to CFF2 OTF font"""
    if args is None:
        import sys

        args = sys.argv[1:]

    import argparse

    parser = argparse.ArgumentParser(
        "fonttools cffLib.CFFToCFF2",
        description="Upgrade a CFF font to CFF2.",
    )
    parser.add_argument(
        "input", metavar="INPUT.ttf", help="Input OTF file with CFF table."
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT.ttf",
        default=None,
        help="Output instance OTF file (default: INPUT-CFF2.ttf).",
    )
    parser.add_argument(
        "--no-recalc-timestamp",
        dest="recalc_timestamp",
        action="store_false",
        help="Don't set the output font's timestamp to the current time.",
    )
    loggingGroup = parser.add_mutually_exclusive_group(required=False)
    loggingGroup.add_argument(
        "-v", "--verbose", action="store_true", help="Run more verbosely."
    )
    loggingGroup.add_argument(
        "-q", "--quiet", action="store_true", help="Turn verbosity off."
    )
    options = parser.parse_args(args)

    from fontTools import configLogger

    configLogger(
        level=("DEBUG" if options.verbose else "ERROR" if options.quiet else "INFO")
    )

    import os

    infile = options.input
    if not os.path.isfile(infile):
        parser.error("No such file '{}'".format(infile))

    outfile = (
        makeOutputFileName(infile, overWrite=True, suffix="-CFF")
        if not options.output
        else options.output
    )

    font = TTFont(infile, recalcTimestamp=options.recalc_timestamp, recalcBBoxes=False)

    convertCFF2ToCFF(font)

    log.info(
        "Saving %s",
        outfile,
    )
    font.save(outfile)


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\services\model_service\transports\base.py ===
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

from google.ai.generativelanguage_v1 import gapic_version as package_version
from google.ai.generativelanguage_v1.types import model, model_service

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class ModelServiceTransport(abc.ABC):
    """Abstract transport class for ModelService."""

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
            self.get_model: gapic_v1.method.wrap_method(
                self.get_model,
                default_timeout=None,
                client_info=client_info,
            ),
            self.list_models: gapic_v1.method.wrap_method(
                self.list_models,
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
    def get_model(
        self,
    ) -> Callable[
        [model_service.GetModelRequest], Union[model.Model, Awaitable[model.Model]]
    ]:
        raise NotImplementedError()

    @property
    def list_models(
        self,
    ) -> Callable[
        [model_service.ListModelsRequest],
        Union[
            model_service.ListModelsResponse,
            Awaitable[model_service.ListModelsResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def list_operations(
        self,
    ) -> Callable[
        [operations_pb2.ListOperationsRequest],
        Union[
            operations_pb2.ListOperationsResponse,
            Awaitable[operations_pb2.ListOperationsResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def get_operation(
        self,
    ) -> Callable[
        [operations_pb2.GetOperationRequest],
        Union[operations_pb2.Operation, Awaitable[operations_pb2.Operation]],
    ]:
        raise NotImplementedError()

    @property
    def cancel_operation(
        self,
    ) -> Callable[[operations_pb2.CancelOperationRequest], None,]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("ModelServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\ipykernel\inprocess\ipkernel.py ===
"""An in-process kernel"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import logging
import sys
from contextlib import contextmanager

from IPython.core.interactiveshell import InteractiveShellABC
from traitlets import Any, Enum, Instance, List, Type, default

from ipykernel.ipkernel import IPythonKernel
from ipykernel.jsonutil import json_clean
from ipykernel.zmqshell import ZMQInteractiveShell

from ..iostream import BackgroundSocket, IOPubThread, OutStream
from .constants import INPROCESS_KEY
from .socket import DummySocket

# -----------------------------------------------------------------------------
# Main kernel class
# -----------------------------------------------------------------------------


class InProcessKernel(IPythonKernel):
    """An in-process kernel."""

    # -------------------------------------------------------------------------
    # InProcessKernel interface
    # -------------------------------------------------------------------------

    # The frontends connected to this kernel.
    frontends = List(Instance("ipykernel.inprocess.client.InProcessKernelClient", allow_none=True))

    # The GUI environment that the kernel is running under. This need not be
    # specified for the normal operation for the kernel, but is required for
    # IPython's GUI support (including pylab). The default is 'inline' because
    # it is safe under all GUI toolkits.
    gui = Enum(("tk", "gtk", "wx", "qt", "qt4", "inline"), default_value="inline")

    raw_input_str = Any()
    stdout = Any()
    stderr = Any()

    # -------------------------------------------------------------------------
    # Kernel interface
    # -------------------------------------------------------------------------

    shell_class = Type(allow_none=True)  # type:ignore[assignment]
    _underlying_iopub_socket = Instance(DummySocket, ())
    iopub_thread: IOPubThread = Instance(IOPubThread)  # type:ignore[assignment]

    shell_stream = Instance(DummySocket, ())  # type:ignore[arg-type]

    @default("iopub_thread")
    def _default_iopub_thread(self):
        thread = IOPubThread(self._underlying_iopub_socket)
        thread.start()
        return thread

    iopub_socket: BackgroundSocket = Instance(BackgroundSocket)  # type:ignore[assignment]

    @default("iopub_socket")
    def _default_iopub_socket(self):
        return self.iopub_thread.background_socket

    stdin_socket = Instance(DummySocket, ())  # type:ignore[assignment]

    def __init__(self, **traits):
        """Initialize the kernel."""
        super().__init__(**traits)

        self._underlying_iopub_socket.observe(self._io_dispatch, names=["message_sent"])
        if self.shell:
            self.shell.kernel = self

    async def execute_request(self, stream, ident, parent):
        """Override for temporary IO redirection."""
        with self._redirected_io():
            await super().execute_request(stream, ident, parent)

    def start(self):
        """Override registration of dispatchers for streams."""
        if self.shell:
            self.shell.exit_now = False

    def _abort_queues(self):
        """The in-process kernel doesn't abort requests."""

    async def _flush_control_queue(self):
        """No need to flush control queues for in-process"""

    def _input_request(self, prompt, ident, parent, password=False):
        # Flush output before making the request.
        self.raw_input_str = None
        sys.stderr.flush()
        sys.stdout.flush()

        # Send the input request.
        content = json_clean(dict(prompt=prompt, password=password))
        assert self.session is not None
        msg = self.session.msg("input_request", content, parent)
        for frontend in self.frontends:
            assert frontend is not None
            if frontend.session.session == parent["header"]["session"]:
                frontend.stdin_channel.call_handlers(msg)
                break
        else:
            logging.error("No frontend found for raw_input request")
            return ""

        # Await a response.
        while self.raw_input_str is None:
            frontend.stdin_channel.process_events()
        return self.raw_input_str  # type:ignore[unreachable]

    # -------------------------------------------------------------------------
    # Protected interface
    # -------------------------------------------------------------------------

    @contextmanager
    def _redirected_io(self):
        """Temporarily redirect IO to the kernel."""
        sys_stdout, sys_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = self.stdout, self.stderr
            yield
        finally:
            sys.stdout, sys.stderr = sys_stdout, sys_stderr

    # ------ Trait change handlers --------------------------------------------

    def _io_dispatch(self, change):
        """Called when a message is sent to the IO socket."""
        assert self.iopub_socket.io_thread is not None
        assert self.session is not None
        ident, msg = self.session.recv(self.iopub_socket.io_thread.socket, copy=False)
        for frontend in self.frontends:
            assert frontend is not None
            frontend.iopub_channel.call_handlers(msg)

    # ------ Trait initializers -----------------------------------------------

    @default("log")
    def _default_log(self):
        return logging.getLogger(__name__)

    @default("session")
    def _default_session(self):
        from jupyter_client.session import Session

        return Session(parent=self, key=INPROCESS_KEY)

    @default("shell_class")
    def _default_shell_class(self):
        return InProcessInteractiveShell

    @default("stdout")
    def _default_stdout(self):
        return OutStream(self.session, self.iopub_thread, "stdout", watchfd=False)

    @default("stderr")
    def _default_stderr(self):
        return OutStream(self.session, self.iopub_thread, "stderr", watchfd=False)


# -----------------------------------------------------------------------------
# Interactive shell subclass
# -----------------------------------------------------------------------------


class InProcessInteractiveShell(ZMQInteractiveShell):
    """An in-process interactive shell."""

    kernel: InProcessKernel = Instance(
        "ipykernel.inprocess.ipkernel.InProcessKernel", allow_none=True
    )  # type:ignore[assignment]

    # -------------------------------------------------------------------------
    # InteractiveShell interface
    # -------------------------------------------------------------------------

    def enable_gui(self, gui=None):
        """Enable GUI integration for the kernel."""
        if not gui:
            gui = self.kernel.gui
        self.active_eventloop = gui

    def enable_matplotlib(self, gui=None):
        """Enable matplotlib integration for the kernel."""
        if not gui:
            gui = self.kernel.gui
        return super().enable_matplotlib(gui)

    def enable_pylab(self, gui=None, import_all=True, welcome_message=False):
        """Activate pylab support at runtime."""
        if not gui:
            gui = self.kernel.gui
        return super().enable_pylab(gui, import_all, welcome_message)


InteractiveShellABC.register(InProcessInteractiveShell)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\anthropic\experimental_pass_through\messages\handler.py ===
"""
- call /messages on Anthropic API
- Make streaming + non-streaming request - just pass it through direct to Anthropic. No need to do anything special here
- Ensure requests are logged in the DB - stream + non-stream

"""

import asyncio
import contextvars
from functools import partial
from typing import Any, AsyncIterator, Coroutine, Dict, List, Optional, Union

import litellm
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.base_llm.anthropic_messages.transformation import (
    BaseAnthropicMessagesConfig,
)
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler
from litellm.llms.custom_httpx.llm_http_handler import BaseLLMHTTPHandler
from litellm.types.llms.anthropic_messages.anthropic_response import (
    AnthropicMessagesResponse,
)
from litellm.types.router import GenericLiteLLMParams
from litellm.utils import ProviderConfigManager, client

from ..adapters.handler import LiteLLMMessagesToCompletionTransformationHandler
from .utils import AnthropicMessagesRequestUtils

####### ENVIRONMENT VARIABLES ###################
# Initialize any necessary instances or variables here
base_llm_http_handler = BaseLLMHTTPHandler()
#################################################


@client
async def anthropic_messages(
    max_tokens: int,
    messages: List[Dict],
    model: str,
    metadata: Optional[Dict] = None,
    stop_sequences: Optional[List[str]] = None,
    stream: Optional[bool] = False,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    thinking: Optional[Dict] = None,
    tool_choice: Optional[Dict] = None,
    tools: Optional[List[Dict]] = None,
    top_k: Optional[int] = None,
    top_p: Optional[float] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    client: Optional[AsyncHTTPHandler] = None,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> Union[AnthropicMessagesResponse, AsyncIterator]:
    """
    Async: Make llm api request in Anthropic /messages API spec
    """
    local_vars = locals()
    loop = asyncio.get_event_loop()
    kwargs["is_async"] = True

    func = partial(
        anthropic_messages_handler,
        max_tokens=max_tokens,
        messages=messages,
        model=model,
        metadata=metadata,
        stop_sequences=stop_sequences,
        stream=stream,
        system=system,
        temperature=temperature,
        thinking=thinking,
        tool_choice=tool_choice,
        tools=tools,
        top_k=top_k,
        top_p=top_p,
        api_key=api_key,
        api_base=api_base,
        client=client,
        custom_llm_provider=custom_llm_provider,
        **kwargs,
    )
    ctx = contextvars.copy_context()
    func_with_context = partial(ctx.run, func)
    init_response = await loop.run_in_executor(None, func_with_context)

    if asyncio.iscoroutine(init_response):
        response = await init_response
    else:
        response = init_response
    return response


def anthropic_messages_handler(
    max_tokens: int,
    messages: List[Dict],
    model: str,
    metadata: Optional[Dict] = None,
    stop_sequences: Optional[List[str]] = None,
    stream: Optional[bool] = False,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    thinking: Optional[Dict] = None,
    tool_choice: Optional[Dict] = None,
    tools: Optional[List[Dict]] = None,
    top_k: Optional[int] = None,
    top_p: Optional[float] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    client: Optional[AsyncHTTPHandler] = None,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> Union[
    AnthropicMessagesResponse,
    AsyncIterator[Any],
    Coroutine[Any, Any, Union[AnthropicMessagesResponse, AsyncIterator[Any]]],
]:
    """
    Makes Anthropic `/v1/messages` API calls In the Anthropic API Spec
    """
    local_vars = locals()
    is_async = kwargs.pop("is_async", False)
    # Use provided client or create a new one
    litellm_logging_obj: LiteLLMLoggingObj = kwargs.get("litellm_logging_obj")  # type: ignore
    litellm_params = GenericLiteLLMParams(
        **kwargs,
        api_key=api_key,
        api_base=api_base,
        custom_llm_provider=custom_llm_provider,
    )
    (
        model,
        custom_llm_provider,
        dynamic_api_key,
        dynamic_api_base,
    ) = litellm.get_llm_provider(
        model=model,
        custom_llm_provider=custom_llm_provider,
        api_base=litellm_params.api_base,
        api_key=litellm_params.api_key,
    )

    anthropic_messages_provider_config: Optional[
        BaseAnthropicMessagesConfig
    ] = ProviderConfigManager.get_provider_anthropic_messages_config(
        model=model,
        provider=litellm.LlmProviders(custom_llm_provider),
    )
    if anthropic_messages_provider_config is None:
        # Handle non-Anthropic models using the adapter
        return (
            LiteLLMMessagesToCompletionTransformationHandler.anthropic_messages_handler(
                max_tokens=max_tokens,
                messages=messages,
                model=model,
                metadata=metadata,
                stop_sequences=stop_sequences,
                stream=stream,
                system=system,
                temperature=temperature,
                thinking=thinking,
                tool_choice=tool_choice,
                tools=tools,
                top_k=top_k,
                top_p=top_p,
                _is_async=is_async,
                api_key=api_key,
                api_base=api_base,
                client=client,
                custom_llm_provider=custom_llm_provider,
                **kwargs,
            )
        )

    if custom_llm_provider is None:
        raise ValueError(
            f"custom_llm_provider is required for Anthropic messages, passed in model={model}, custom_llm_provider={custom_llm_provider}"
        )

    local_vars.update(kwargs)
    anthropic_messages_optional_request_params = (
        AnthropicMessagesRequestUtils.get_requested_anthropic_messages_optional_param(
            params=local_vars
        )
    )
    return base_llm_http_handler.anthropic_messages_handler(
        model=model,
        messages=messages,
        anthropic_messages_provider_config=anthropic_messages_provider_config,
        anthropic_messages_optional_request_params=dict(
            anthropic_messages_optional_request_params
        ),
        _is_async=is_async,
        client=client,
        custom_llm_provider=custom_llm_provider,
        litellm_params=litellm_params,
        logging_obj=litellm_logging_obj,
        api_key=api_key,
        api_base=api_base,
        stream=stream,
        kwargs=kwargs,
    )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\auth\litellm_license.py ===
# What is this?
## If litellm license in env, checks if it's valid
import base64
import json
import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import httpx

from litellm._logging import verbose_proxy_logger
from litellm.constants import NON_LLM_CONNECTION_TIMEOUT
from litellm.llms.custom_httpx.http_handler import HTTPHandler

if TYPE_CHECKING:
    from litellm.proxy._types import EnterpriseLicenseData


class LicenseCheck:
    """
    - Check if license in env
    - Returns if license is valid
    """

    base_url = "https://license.litellm.ai"

    def __init__(self) -> None:
        self.license_str = os.getenv("LITELLM_LICENSE", None)
        verbose_proxy_logger.debug("License Str value - {}".format(self.license_str))
        self.http_handler = HTTPHandler(timeout=NON_LLM_CONNECTION_TIMEOUT)
        self.public_key = None
        self.read_public_key()
        self.airgapped_license_data: Optional["EnterpriseLicenseData"] = None

    def read_public_key(self):
        try:
            from cryptography.hazmat.primitives import serialization

            # current dir
            current_dir = os.path.dirname(os.path.realpath(__file__))

            # check if public_key.pem exists
            _path_to_public_key = os.path.join(current_dir, "public_key.pem")
            if os.path.exists(_path_to_public_key):
                with open(_path_to_public_key, "rb") as key_file:
                    self.public_key = serialization.load_pem_public_key(key_file.read())
            else:
                self.public_key = None
        except Exception as e:
            verbose_proxy_logger.error(f"Error reading public key: {str(e)}")

    def _verify(self, license_str: str) -> bool:
        verbose_proxy_logger.debug(
            "litellm.proxy.auth.litellm_license.py::_verify - Checking license against {}/verify_license - {}".format(
                self.base_url, license_str
            )
        )
        url = "{}/verify_license/{}".format(self.base_url, license_str)

        response: Optional[httpx.Response] = None
        try:  # don't impact user, if call fails
            num_retries = 3
            for i in range(num_retries):
                try:
                    response = self.http_handler.get(url=url)
                    if response is None:
                        raise Exception("No response from license server")
                    response.raise_for_status()
                except httpx.HTTPStatusError:
                    if i == num_retries - 1:
                        raise

            if response is None:
                raise Exception("No response from license server")

            response_json = response.json()

            premium = response_json["verify"]

            assert isinstance(premium, bool)

            verbose_proxy_logger.debug(
                "litellm.proxy.auth.litellm_license.py::_verify - License={} is premium={}".format(
                    license_str, premium
                )
            )
            return premium
        except Exception as e:
            verbose_proxy_logger.exception(
                "litellm.proxy.auth.litellm_license.py::_verify - Unable to verify License={} via api. - {}".format(
                    license_str, str(e)
                )
            )
            return False

    def is_premium(self) -> bool:
        """
        1. verify_license_without_api_request: checks if license was generate using private / public key pair
        2. _verify: checks if license is valid calling litellm API. This is the old way we were generating/validating license
        """
        try:
            verbose_proxy_logger.debug(
                "litellm.proxy.auth.litellm_license.py::is_premium() - ENTERING 'IS_PREMIUM' - LiteLLM License={}".format(
                    self.license_str
                )
            )

            if self.license_str is None:
                self.license_str = os.getenv("LITELLM_LICENSE", None)

            verbose_proxy_logger.debug(
                "litellm.proxy.auth.litellm_license.py::is_premium() - Updated 'self.license_str' - {}".format(
                    self.license_str
                )
            )

            if self.license_str is None:
                return False
            elif (
                self.verify_license_without_api_request(
                    public_key=self.public_key, license_key=self.license_str
                )
                is True
            ):
                return True
            elif self._verify(license_str=self.license_str) is True:
                return True
            return False
        except Exception:
            return False

    def is_over_limit(self, total_users: int) -> bool:
        """
        Check if the license is over the limit
        """
        if self.airgapped_license_data is None:
            return False
        if "max_users" not in self.airgapped_license_data or not isinstance(
            self.airgapped_license_data["max_users"], int
        ):
            return False
        return total_users > self.airgapped_license_data["max_users"]
    
    def is_team_count_over_limit(self, team_count: int) -> bool:
        """
        Check if the license is over the limit
        """
        if self.airgapped_license_data is None:
            return False

        _max_teams_in_license: Optional[int] = self.airgapped_license_data.get("max_teams")
        if "max_teams" not in self.airgapped_license_data or not isinstance(
            _max_teams_in_license, int
        ):
            return False
        return team_count > _max_teams_in_license

    def verify_license_without_api_request(self, public_key, license_key):
        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding

            from litellm.proxy._types import EnterpriseLicenseData

            # Decode the license key
            decoded = base64.b64decode(license_key)
            message, signature = decoded.split(b".", 1)

            # Verify the signature
            public_key.verify(
                signature,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )

            # Decode and parse the data
            license_data = json.loads(message.decode())

            self.airgapped_license_data = EnterpriseLicenseData(**license_data)

            # debug information provided in license data
            verbose_proxy_logger.debug("License data: %s", license_data)

            # Check expiration date
            expiration_date = datetime.strptime(
                license_data["expiration_date"], "%Y-%m-%d"
            )
            if expiration_date < datetime.now():
                return False, "License has expired"

            return True

        except Exception as e:
            verbose_proxy_logger.debug(
                "litellm.proxy.auth.litellm_license.py::verify_license_without_api_request - Unable to verify License locally. - {}".format(
                    str(e)
                )
            )
            return False

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\realtime\session_create_response.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Union, Optional
from typing_extensions import Literal, TypeAlias

from ...._models import BaseModel

__all__ = [
    "SessionCreateResponse",
    "ClientSecret",
    "InputAudioTranscription",
    "Tool",
    "Tracing",
    "TracingTracingConfiguration",
    "TurnDetection",
]


class ClientSecret(BaseModel):
    expires_at: int
    """Timestamp for when the token expires.

    Currently, all tokens expire after one minute.
    """

    value: str
    """
    Ephemeral key usable in client environments to authenticate connections to the
    Realtime API. Use this in client-side environments rather than a standard API
    token, which should only be used server-side.
    """


class InputAudioTranscription(BaseModel):
    model: Optional[str] = None
    """
    The model to use for transcription, `whisper-1` is the only currently supported
    model.
    """


class Tool(BaseModel):
    description: Optional[str] = None
    """
    The description of the function, including guidance on when and how to call it,
    and guidance about what to tell the user when calling (if anything).
    """

    name: Optional[str] = None
    """The name of the function."""

    parameters: Optional[object] = None
    """Parameters of the function in JSON Schema."""

    type: Optional[Literal["function"]] = None
    """The type of the tool, i.e. `function`."""


class TracingTracingConfiguration(BaseModel):
    group_id: Optional[str] = None
    """
    The group id to attach to this trace to enable filtering and grouping in the
    traces dashboard.
    """

    metadata: Optional[object] = None
    """
    The arbitrary metadata to attach to this trace to enable filtering in the traces
    dashboard.
    """

    workflow_name: Optional[str] = None
    """The name of the workflow to attach to this trace.

    This is used to name the trace in the traces dashboard.
    """


Tracing: TypeAlias = Union[Literal["auto"], TracingTracingConfiguration]


class TurnDetection(BaseModel):
    prefix_padding_ms: Optional[int] = None
    """Amount of audio to include before the VAD detected speech (in milliseconds).

    Defaults to 300ms.
    """

    silence_duration_ms: Optional[int] = None
    """Duration of silence to detect speech stop (in milliseconds).

    Defaults to 500ms. With shorter values the model will respond more quickly, but
    may jump in on short pauses from the user.
    """

    threshold: Optional[float] = None
    """Activation threshold for VAD (0.0 to 1.0), this defaults to 0.5.

    A higher threshold will require louder audio to activate the model, and thus
    might perform better in noisy environments.
    """

    type: Optional[str] = None
    """Type of turn detection, only `server_vad` is currently supported."""


class SessionCreateResponse(BaseModel):
    client_secret: ClientSecret
    """Ephemeral key returned by the API."""

    input_audio_format: Optional[str] = None
    """The format of input audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`."""

    input_audio_transcription: Optional[InputAudioTranscription] = None
    """
    Configuration for input audio transcription, defaults to off and can be set to
    `null` to turn off once on. Input audio transcription is not native to the
    model, since the model consumes audio directly. Transcription runs
    asynchronously through Whisper and should be treated as rough guidance rather
    than the representation understood by the model.
    """

    instructions: Optional[str] = None
    """The default system instructions (i.e.

    system message) prepended to model calls. This field allows the client to guide
    the model on desired responses. The model can be instructed on response content
    and format, (e.g. "be extremely succinct", "act friendly", "here are examples of
    good responses") and on audio behavior (e.g. "talk quickly", "inject emotion
    into your voice", "laugh frequently"). The instructions are not guaranteed to be
    followed by the model, but they provide guidance to the model on the desired
    behavior.

    Note that the server sets default instructions which will be used if this field
    is not set and are visible in the `session.created` event at the start of the
    session.
    """

    max_response_output_tokens: Union[int, Literal["inf"], None] = None
    """
    Maximum number of output tokens for a single assistant response, inclusive of
    tool calls. Provide an integer between 1 and 4096 to limit output tokens, or
    `inf` for the maximum available tokens for a given model. Defaults to `inf`.
    """

    modalities: Optional[List[Literal["text", "audio"]]] = None
    """The set of modalities the model can respond with.

    To disable audio, set this to ["text"].
    """

    output_audio_format: Optional[str] = None
    """The format of output audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`."""

    speed: Optional[float] = None
    """The speed of the model's spoken response.

    1.0 is the default speed. 0.25 is the minimum speed. 1.5 is the maximum speed.
    This value can only be changed in between model turns, not while a response is
    in progress.
    """

    temperature: Optional[float] = None
    """Sampling temperature for the model, limited to [0.6, 1.2]. Defaults to 0.8."""

    tool_choice: Optional[str] = None
    """How the model chooses tools.

    Options are `auto`, `none`, `required`, or specify a function.
    """

    tools: Optional[List[Tool]] = None
    """Tools (functions) available to the model."""

    tracing: Optional[Tracing] = None
    """Configuration options for tracing.

    Set to null to disable tracing. Once tracing is enabled for a session, the
    configuration cannot be modified.

    `auto` will create a trace for the session with default values for the workflow
    name, group id, and metadata.
    """

    turn_detection: Optional[TurnDetection] = None
    """Configuration for turn detection.

    Can be set to `null` to turn off. Server VAD means that the model will detect
    the start and end of speech based on audio volume and respond at the end of user
    speech.
    """

    voice: Union[
        str,
        Literal["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"],
        None,
    ] = None
    """The voice the model uses to respond.

    Voice cannot be changed during the session once the model has responded with
    audio at least once. Current voice options are `alloy`, `ash`, `ballad`,
    `coral`, `echo` `sage`, `shimmer` and `verse`.
    """

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\style.py ===
"""
    pygments.style
    ~~~~~~~~~~~~~~

    Basic style object.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pip._vendor.pygments.token import Token, STANDARD_TYPES

# Default mapping of ansixxx to RGB colors.
_ansimap = {
    # dark
    'ansiblack': '000000',
    'ansired': '7f0000',
    'ansigreen': '007f00',
    'ansiyellow': '7f7fe0',
    'ansiblue': '00007f',
    'ansimagenta': '7f007f',
    'ansicyan': '007f7f',
    'ansigray': 'e5e5e5',
    # normal
    'ansibrightblack': '555555',
    'ansibrightred': 'ff0000',
    'ansibrightgreen': '00ff00',
    'ansibrightyellow': 'ffff00',
    'ansibrightblue': '0000ff',
    'ansibrightmagenta': 'ff00ff',
    'ansibrightcyan': '00ffff',
    'ansiwhite': 'ffffff',
}
# mapping of deprecated #ansixxx colors to new color names
_deprecated_ansicolors = {
    # dark
    '#ansiblack': 'ansiblack',
    '#ansidarkred': 'ansired',
    '#ansidarkgreen': 'ansigreen',
    '#ansibrown': 'ansiyellow',
    '#ansidarkblue': 'ansiblue',
    '#ansipurple': 'ansimagenta',
    '#ansiteal': 'ansicyan',
    '#ansilightgray': 'ansigray',
    # normal
    '#ansidarkgray': 'ansibrightblack',
    '#ansired': 'ansibrightred',
    '#ansigreen': 'ansibrightgreen',
    '#ansiyellow': 'ansibrightyellow',
    '#ansiblue': 'ansibrightblue',
    '#ansifuchsia': 'ansibrightmagenta',
    '#ansiturquoise': 'ansibrightcyan',
    '#ansiwhite': 'ansiwhite',
}
ansicolors = set(_ansimap)


class StyleMeta(type):

    def __new__(mcs, name, bases, dct):
        obj = type.__new__(mcs, name, bases, dct)
        for token in STANDARD_TYPES:
            if token not in obj.styles:
                obj.styles[token] = ''

        def colorformat(text):
            if text in ansicolors:
                return text
            if text[0:1] == '#':
                col = text[1:]
                if len(col) == 6:
                    return col
                elif len(col) == 3:
                    return col[0] * 2 + col[1] * 2 + col[2] * 2
            elif text == '':
                return ''
            elif text.startswith('var') or text.startswith('calc'):
                return text
            assert False, f"wrong color format {text!r}"

        _styles = obj._styles = {}

        for ttype in obj.styles:
            for token in ttype.split():
                if token in _styles:
                    continue
                ndef = _styles.get(token.parent, None)
                styledefs = obj.styles.get(token, '').split()
                if not ndef or token is None:
                    ndef = ['', 0, 0, 0, '', '', 0, 0, 0]
                elif 'noinherit' in styledefs and token is not Token:
                    ndef = _styles[Token][:]
                else:
                    ndef = ndef[:]
                _styles[token] = ndef
                for styledef in obj.styles.get(token, '').split():
                    if styledef == 'noinherit':
                        pass
                    elif styledef == 'bold':
                        ndef[1] = 1
                    elif styledef == 'nobold':
                        ndef[1] = 0
                    elif styledef == 'italic':
                        ndef[2] = 1
                    elif styledef == 'noitalic':
                        ndef[2] = 0
                    elif styledef == 'underline':
                        ndef[3] = 1
                    elif styledef == 'nounderline':
                        ndef[3] = 0
                    elif styledef[:3] == 'bg:':
                        ndef[4] = colorformat(styledef[3:])
                    elif styledef[:7] == 'border:':
                        ndef[5] = colorformat(styledef[7:])
                    elif styledef == 'roman':
                        ndef[6] = 1
                    elif styledef == 'sans':
                        ndef[7] = 1
                    elif styledef == 'mono':
                        ndef[8] = 1
                    else:
                        ndef[0] = colorformat(styledef)

        return obj

    def style_for_token(cls, token):
        t = cls._styles[token]
        ansicolor = bgansicolor = None
        color = t[0]
        if color in _deprecated_ansicolors:
            color = _deprecated_ansicolors[color]
        if color in ansicolors:
            ansicolor = color
            color = _ansimap[color]
        bgcolor = t[4]
        if bgcolor in _deprecated_ansicolors:
            bgcolor = _deprecated_ansicolors[bgcolor]
        if bgcolor in ansicolors:
            bgansicolor = bgcolor
            bgcolor = _ansimap[bgcolor]

        return {
            'color':        color or None,
            'bold':         bool(t[1]),
            'italic':       bool(t[2]),
            'underline':    bool(t[3]),
            'bgcolor':      bgcolor or None,
            'border':       t[5] or None,
            'roman':        bool(t[6]) or None,
            'sans':         bool(t[7]) or None,
            'mono':         bool(t[8]) or None,
            'ansicolor':    ansicolor,
            'bgansicolor':  bgansicolor,
        }

    def list_styles(cls):
        return list(cls)

    def styles_token(cls, ttype):
        return ttype in cls._styles

    def __iter__(cls):
        for token in cls._styles:
            yield token, cls.style_for_token(token)

    def __len__(cls):
        return len(cls._styles)


class Style(metaclass=StyleMeta):

    #: overall background color (``None`` means transparent)
    background_color = '#ffffff'

    #: highlight background color
    highlight_color = '#ffffcc'

    #: line number font color
    line_number_color = 'inherit'

    #: line number background color
    line_number_background_color = 'transparent'

    #: special line number font color
    line_number_special_color = '#000000'

    #: special line number background color
    line_number_special_background_color = '#ffffc0'

    #: Style definitions for individual token types.
    styles = {}

    #: user-friendly style name (used when selecting the style, so this
    # should be all-lowercase, no spaces, hyphens)
    name = 'unnamed'

    aliases = []

    # Attribute for lexers defined within Pygments. If set
    # to True, the style is not shown in the style gallery
    # on the website. This is intended for language-specific
    # styles.
    web_style_gallery_exclude = False

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\monte.py ===
"""
    pygments.lexers.monte
    ~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Monte programming language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.token import Comment, Error, Keyword, Name, Number, Operator, \
    Punctuation, String, Whitespace
from pygments.lexer import RegexLexer, include, words

__all__ = ['MonteLexer']


# `var` handled separately
# `interface` handled separately
_declarations = ['bind', 'def', 'fn', 'object']
_methods = ['method', 'to']
_keywords = [
    'as', 'break', 'catch', 'continue', 'else', 'escape', 'exit', 'exports',
    'extends', 'finally', 'for', 'guards', 'if', 'implements', 'import',
    'in', 'match', 'meta', 'pass', 'return', 'switch', 'try', 'via', 'when',
    'while',
]
_operators = [
    # Unary
    '~', '!',
    # Binary
    '+', '-', '*', '/', '%', '**', '&', '|', '^', '<<', '>>',
    # Binary augmented
    '+=', '-=', '*=', '/=', '%=', '**=', '&=', '|=', '^=', '<<=', '>>=',
    # Comparison
    '==', '!=', '<', '<=', '>', '>=', '<=>',
    # Patterns and assignment
    ':=', '?', '=~', '!~', '=>',
    # Calls and sends
    '.', '<-', '->',
]
_escape_pattern = (
    r'(?:\\x[0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}|'
    r'\\["\'\\bftnr])')
# _char = _escape_chars + [('.', String.Char)]
_identifier = r'[_a-zA-Z]\w*'

_constants = [
    # Void constants
    'null',
    # Bool constants
    'false', 'true',
    # Double constants
    'Infinity', 'NaN',
    # Special objects
    'M', 'Ref', 'throw', 'traceln',
]

_guards = [
    'Any', 'Binding', 'Bool', 'Bytes', 'Char', 'DeepFrozen', 'Double',
    'Empty', 'Int', 'List', 'Map', 'Near', 'NullOk', 'Same', 'Selfless',
    'Set', 'Str', 'SubrangeGuard', 'Transparent', 'Void',
]

_safeScope = [
    '_accumulateList', '_accumulateMap', '_auditedBy', '_bind',
    '_booleanFlow', '_comparer', '_equalizer', '_iterForever', '_loop',
    '_makeBytes', '_makeDouble', '_makeFinalSlot', '_makeInt', '_makeList',
    '_makeMap', '_makeMessageDesc', '_makeOrderedSpace', '_makeParamDesc',
    '_makeProtocolDesc', '_makeSourceSpan', '_makeString', '_makeVarSlot',
    '_makeVerbFacet', '_mapExtract', '_matchSame', '_quasiMatcher',
    '_slotToBinding', '_splitList', '_suchThat', '_switchFailed',
    '_validateFor', 'b__quasiParser', 'eval', 'import', 'm__quasiParser',
    'makeBrandPair', 'makeLazySlot', 'safeScope', 'simple__quasiParser',
]


class MonteLexer(RegexLexer):
    """
    Lexer for the Monte programming language.
    """
    name = 'Monte'
    url = 'https://monte.readthedocs.io/'
    aliases = ['monte']
    filenames = ['*.mt']
    version_added = '2.2'

    tokens = {
        'root': [
            # Comments
            (r'#[^\n]*\n', Comment),

            # Docstrings
            # Apologies for the non-greedy matcher here.
            (r'/\*\*.*?\*/', String.Doc),

            # `var` declarations
            (r'\bvar\b', Keyword.Declaration, 'var'),

            # `interface` declarations
            (r'\binterface\b', Keyword.Declaration, 'interface'),

            # method declarations
            (words(_methods, prefix='\\b', suffix='\\b'),
             Keyword, 'method'),

            # All other declarations
            (words(_declarations, prefix='\\b', suffix='\\b'),
             Keyword.Declaration),

            # Keywords
            (words(_keywords, prefix='\\b', suffix='\\b'), Keyword),

            # Literals
            ('[+-]?0x[_0-9a-fA-F]+', Number.Hex),
            (r'[+-]?[_0-9]+\.[_0-9]*([eE][+-]?[_0-9]+)?', Number.Float),
            ('[+-]?[_0-9]+', Number.Integer),
            ("'", String.Double, 'char'),
            ('"', String.Double, 'string'),

            # Quasiliterals
            ('`', String.Backtick, 'ql'),

            # Operators
            (words(_operators), Operator),

            # Verb operators
            (_identifier + '=', Operator.Word),

            # Safe scope constants
            (words(_constants, prefix='\\b', suffix='\\b'),
             Keyword.Pseudo),

            # Safe scope guards
            (words(_guards, prefix='\\b', suffix='\\b'), Keyword.Type),

            # All other safe scope names
            (words(_safeScope, prefix='\\b', suffix='\\b'),
             Name.Builtin),

            # Identifiers
            (_identifier, Name),

            # Punctuation
            (r'\(|\)|\{|\}|\[|\]|:|,', Punctuation),

            # Whitespace
            (' +', Whitespace),

            # Definite lexer errors
            ('=', Error),
        ],
        'char': [
            # It is definitely an error to have a char of width == 0.
            ("'", Error, 'root'),
            (_escape_pattern, String.Escape, 'charEnd'),
            ('.', String.Char, 'charEnd'),
        ],
        'charEnd': [
            ("'", String.Char, '#pop:2'),
            # It is definitely an error to have a char of width > 1.
            ('.', Error),
        ],
        # The state of things coming into an interface.
        'interface': [
            (' +', Whitespace),
            (_identifier, Name.Class, '#pop'),
            include('root'),
        ],
        # The state of things coming into a method.
        'method': [
            (' +', Whitespace),
            (_identifier, Name.Function, '#pop'),
            include('root'),
        ],
        'string': [
            ('"', String.Double, 'root'),
            (_escape_pattern, String.Escape),
            (r'\n', String.Double),
            ('.', String.Double),
        ],
        'ql': [
            ('`', String.Backtick, 'root'),
            (r'\$' + _escape_pattern, String.Escape),
            (r'\$\$', String.Escape),
            (r'@@', String.Escape),
            (r'\$\{', String.Interpol, 'qlNest'),
            (r'@\{', String.Interpol, 'qlNest'),
            (r'\$' + _identifier, Name),
            ('@' + _identifier, Name),
            ('.', String.Backtick),
        ],
        'qlNest': [
            (r'\}', String.Interpol, '#pop'),
            include('root'),
        ],
        # The state of things immediately following `var`.
        'var': [
            (' +', Whitespace),
            (_identifier, Name.Variable, '#pop'),
            include('root'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\trio\_unix_pipes.py ===
from __future__ import annotations

import errno
import os
import sys
from typing import TYPE_CHECKING

import trio

from ._abc import Stream
from ._util import ConflictDetector, final

if TYPE_CHECKING:
    from typing import Final as FinalType

assert not TYPE_CHECKING or sys.platform != "win32"

if os.name != "posix":
    # We raise an error here rather than gating the import in lowlevel.py
    # in order to keep jedi static analysis happy.
    raise ImportError

# XX TODO: is this a good number? who knows... it does match the default Linux
# pipe capacity though.
DEFAULT_RECEIVE_SIZE: FinalType = 65536


class _FdHolder:
    # This class holds onto a raw file descriptor, in non-blocking mode, and
    # is responsible for managing its lifecycle. In particular, it's
    # responsible for making sure it gets closed, and also for tracking
    # whether it's been closed.
    #
    # The way we track closure is to set the .fd field to -1, discarding the
    # original value. You might think that this is a strange idea, since it
    # overloads the same field to do two different things. Wouldn't it be more
    # natural to have a dedicated .closed field? But that would be more
    # error-prone. Fds are represented by small integers, and once an fd is
    # closed, its integer value may be reused immediately. If we accidentally
    # used the old fd after being closed, we might end up doing something to
    # another unrelated fd that happened to get assigned the same integer
    # value. By throwing away the integer value immediately, it becomes
    # impossible to make this mistake – we'll just get an EBADF.
    #
    # (This trick was copied from the stdlib socket module.)
    fd: int

    def __init__(self, fd: int) -> None:
        # make sure self.fd is always initialized to *something*, because even
        # if we error out here then __del__ will run and access it.
        self.fd = -1
        if not isinstance(fd, int):
            raise TypeError("file descriptor must be an int")
        self.fd = fd
        # Store original state, and ensure non-blocking mode is enabled
        self._original_is_blocking = os.get_blocking(fd)
        os.set_blocking(fd, False)

    @property
    def closed(self) -> bool:
        return self.fd == -1

    def _raw_close(self) -> None:
        # This doesn't assume it's in a Trio context, so it can be called from
        # __del__. You should never call it from Trio context, because it
        # skips calling notify_fd_close. But from __del__, skipping that is
        # OK, because notify_fd_close just wakes up other tasks that are
        # waiting on this fd, and those tasks hold a reference to this object.
        # So if __del__ is being called, we know there aren't any tasks that
        # need to be woken.
        if self.closed:
            return
        fd = self.fd
        self.fd = -1
        os.set_blocking(fd, self._original_is_blocking)
        os.close(fd)

    def __del__(self) -> None:
        self._raw_close()

    def close(self) -> None:
        if not self.closed:
            trio.lowlevel.notify_closing(self.fd)
            self._raw_close()


@final
class FdStream(Stream):
    """
    Represents a stream given the file descriptor to a pipe, TTY, etc.

    *fd* must refer to a file that is open for reading and/or writing and
    supports non-blocking I/O (pipes and TTYs will work, on-disk files probably
    not).  The returned stream takes ownership of the fd, so closing the stream
    will close the fd too.  As with `os.fdopen`, you should not directly use
    an fd after you have wrapped it in a stream using this function.

    To be used as a Trio stream, an open file must be placed in non-blocking
    mode.  Unfortunately, this impacts all I/O that goes through the
    underlying open file, including I/O that uses a different
    file descriptor than the one that was passed to Trio. If other threads
    or processes are using file descriptors that are related through `os.dup`
    or inheritance across `os.fork` to the one that Trio is using, they are
    unlikely to be prepared to have non-blocking I/O semantics suddenly
    thrust upon them.  For example, you can use
    ``FdStream(os.dup(sys.stdin.fileno()))`` to obtain a stream for reading
    from standard input, but it is only safe to do so with heavy caveats: your
    stdin must not be shared by any other processes, and you must not make any
    calls to synchronous methods of `sys.stdin` until the stream returned by
    `FdStream` is closed. See `issue #174
    <https://github.com/python-trio/trio/issues/174>`__ for a discussion of the
    challenges involved in relaxing this restriction.

    Args:
      fd (int): The fd to be wrapped.

    Returns:
      A new `FdStream` object.
    """

    def __init__(self, fd: int) -> None:
        self._fd_holder = _FdHolder(fd)
        self._send_conflict_detector = ConflictDetector(
            "another task is using this stream for send",
        )
        self._receive_conflict_detector = ConflictDetector(
            "another task is using this stream for receive",
        )

    async def send_all(self, data: bytes) -> None:
        with self._send_conflict_detector:
            # have to check up front, because send_all(b"") on a closed pipe
            # should raise
            if self._fd_holder.closed:
                raise trio.ClosedResourceError("file was already closed")
            await trio.lowlevel.checkpoint()
            length = len(data)
            # adapted from the SocketStream code
            with memoryview(data) as view:
                sent = 0
                while sent < length:
                    with view[sent:] as remaining:
                        try:
                            sent += os.write(self._fd_holder.fd, remaining)
                        except BlockingIOError:
                            await trio.lowlevel.wait_writable(self._fd_holder.fd)
                        except OSError as e:
                            if e.errno == errno.EBADF:
                                raise trio.ClosedResourceError(
                                    "file was already closed",
                                ) from None
                            else:
                                raise trio.BrokenResourceError from e

    async def wait_send_all_might_not_block(self) -> None:
        with self._send_conflict_detector:
            if self._fd_holder.closed:
                raise trio.ClosedResourceError("file was already closed")
            try:
                await trio.lowlevel.wait_writable(self._fd_holder.fd)
            except BrokenPipeError as e:
                # kqueue: raises EPIPE on wait_writable instead
                # of sending, which is annoying
                raise trio.BrokenResourceError from e

    async def receive_some(self, max_bytes: int | None = None) -> bytes:
        with self._receive_conflict_detector:
            if max_bytes is None:
                max_bytes = DEFAULT_RECEIVE_SIZE
            else:
                if not isinstance(max_bytes, int):
                    raise TypeError("max_bytes must be integer >= 1")
                if max_bytes < 1:
                    raise ValueError("max_bytes must be integer >= 1")

            await trio.lowlevel.checkpoint()
            while True:
                try:
                    data = os.read(self._fd_holder.fd, max_bytes)
                except BlockingIOError:
                    await trio.lowlevel.wait_readable(self._fd_holder.fd)
                except OSError as exc:
                    if exc.errno == errno.EBADF:
                        raise trio.ClosedResourceError(
                            "file was already closed",
                        ) from None
                    else:
                        raise trio.BrokenResourceError from exc
                else:
                    break

            return data

    def close(self) -> None:
        self._fd_holder.close()

    async def aclose(self) -> None:
        self.close()
        await trio.lowlevel.checkpoint()

    def fileno(self) -> int:
        return self._fd_holder.fd

# === NexusCore/openenv\Lib\site-packages\websocket\_handshake.py ===
"""
_handshake.py
websocket - WebSocket client library for Python

Copyright 2024 engn33r

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import hashlib
import hmac
import os
from base64 import encodebytes as base64encode
from http import HTTPStatus

from ._cookiejar import SimpleCookieJar
from ._exceptions import WebSocketException, WebSocketBadStatusException
from ._http import read_headers
from ._logging import dump, error
from ._socket import send

__all__ = ["handshake_response", "handshake", "SUPPORTED_REDIRECT_STATUSES"]

# websocket supported version.
VERSION = 13

SUPPORTED_REDIRECT_STATUSES = (
    HTTPStatus.MOVED_PERMANENTLY,
    HTTPStatus.FOUND,
    HTTPStatus.SEE_OTHER,
    HTTPStatus.TEMPORARY_REDIRECT,
    HTTPStatus.PERMANENT_REDIRECT,
)
SUCCESS_STATUSES = SUPPORTED_REDIRECT_STATUSES + (HTTPStatus.SWITCHING_PROTOCOLS,)

CookieJar = SimpleCookieJar()


class handshake_response:
    def __init__(self, status: int, headers: dict, subprotocol):
        self.status = status
        self.headers = headers
        self.subprotocol = subprotocol
        CookieJar.add(headers.get("set-cookie"))


def handshake(
    sock, url: str, hostname: str, port: int, resource: str, **options
) -> handshake_response:
    headers, key = _get_handshake_headers(resource, url, hostname, port, options)

    header_str = "\r\n".join(headers)
    send(sock, header_str)
    dump("request header", header_str)

    status, resp = _get_resp_headers(sock)
    if status in SUPPORTED_REDIRECT_STATUSES:
        return handshake_response(status, resp, None)
    success, subproto = _validate(resp, key, options.get("subprotocols"))
    if not success:
        raise WebSocketException("Invalid WebSocket Header")

    return handshake_response(status, resp, subproto)


def _pack_hostname(hostname: str) -> str:
    # IPv6 address
    if ":" in hostname:
        return f"[{hostname}]"
    return hostname


def _get_handshake_headers(
    resource: str, url: str, host: str, port: int, options: dict
) -> tuple:
    headers = [f"GET {resource} HTTP/1.1", "Upgrade: websocket"]
    if port in [80, 443]:
        hostport = _pack_hostname(host)
    else:
        hostport = f"{_pack_hostname(host)}:{port}"
    if options.get("host"):
        headers.append(f'Host: {options["host"]}')
    else:
        headers.append(f"Host: {hostport}")

    # scheme indicates whether http or https is used in Origin
    # The same approach is used in parse_url of _url.py to set default port
    scheme, url = url.split(":", 1)
    if not options.get("suppress_origin"):
        if "origin" in options and options["origin"] is not None:
            headers.append(f'Origin: {options["origin"]}')
        elif scheme == "wss":
            headers.append(f"Origin: https://{hostport}")
        else:
            headers.append(f"Origin: http://{hostport}")

    key = _create_sec_websocket_key()

    # Append Sec-WebSocket-Key & Sec-WebSocket-Version if not manually specified
    if not options.get("header") or "Sec-WebSocket-Key" not in options["header"]:
        headers.append(f"Sec-WebSocket-Key: {key}")
    else:
        key = options["header"]["Sec-WebSocket-Key"]

    if not options.get("header") or "Sec-WebSocket-Version" not in options["header"]:
        headers.append(f"Sec-WebSocket-Version: {VERSION}")

    if not options.get("connection"):
        headers.append("Connection: Upgrade")
    else:
        headers.append(options["connection"])

    if subprotocols := options.get("subprotocols"):
        headers.append(f'Sec-WebSocket-Protocol: {",".join(subprotocols)}')

    if header := options.get("header"):
        if isinstance(header, dict):
            header = [": ".join([k, v]) for k, v in header.items() if v is not None]
        headers.extend(header)

    server_cookie = CookieJar.get(host)
    client_cookie = options.get("cookie", None)

    if cookie := "; ".join(filter(None, [server_cookie, client_cookie])):
        headers.append(f"Cookie: {cookie}")

    headers.extend(("", ""))
    return headers, key


def _get_resp_headers(sock, success_statuses: tuple = SUCCESS_STATUSES) -> tuple:
    status, resp_headers, status_message = read_headers(sock)
    if status not in success_statuses:
        content_len = resp_headers.get("content-length")
        if content_len:
            response_body = sock.recv(
                int(content_len)
            )  # read the body of the HTTP error message response and include it in the exception
        else:
            response_body = None
        raise WebSocketBadStatusException(
            f"Handshake status {status} {status_message} -+-+- {resp_headers} -+-+- {response_body}",
            status,
            status_message,
            resp_headers,
            response_body,
        )
    return status, resp_headers


_HEADERS_TO_CHECK = {
    "upgrade": "websocket",
    "connection": "upgrade",
}


def _validate(headers, key: str, subprotocols) -> tuple:
    subproto = None
    for k, v in _HEADERS_TO_CHECK.items():
        r = headers.get(k, None)
        if not r:
            return False, None
        r = [x.strip().lower() for x in r.split(",")]
        if v not in r:
            return False, None

    if subprotocols:
        subproto = headers.get("sec-websocket-protocol", None)
        if not subproto or subproto.lower() not in [s.lower() for s in subprotocols]:
            error(f"Invalid subprotocol: {subprotocols}")
            return False, None
        subproto = subproto.lower()

    result = headers.get("sec-websocket-accept", None)
    if not result:
        return False, None
    result = result.lower()

    if isinstance(result, str):
        result = result.encode("utf-8")

    value = f"{key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11".encode("utf-8")
    hashed = base64encode(hashlib.sha1(value).digest()).strip().lower()

    if hmac.compare_digest(hashed, result):
        return True, subproto
    else:
        return False, None


def _create_sec_websocket_key() -> str:
    randomness = os.urandom(16)
    return base64encode(randomness).decode("utf-8").strip()

# === NexusCore/openenv\Lib\site-packages\anyio\_core\_subprocesses.py ===
from __future__ import annotations

import sys
from collections.abc import AsyncIterable, Iterable, Mapping, Sequence
from io import BytesIO
from os import PathLike
from subprocess import PIPE, CalledProcessError, CompletedProcess
from typing import IO, Any, Union, cast

from ..abc import Process
from ._eventloop import get_async_backend
from ._tasks import create_task_group

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

StrOrBytesPath: TypeAlias = Union[str, bytes, "PathLike[str]", "PathLike[bytes]"]


async def run_process(
    command: StrOrBytesPath | Sequence[StrOrBytesPath],
    *,
    input: bytes | None = None,
    stdin: int | IO[Any] | None = None,
    stdout: int | IO[Any] | None = PIPE,
    stderr: int | IO[Any] | None = PIPE,
    check: bool = True,
    cwd: StrOrBytesPath | None = None,
    env: Mapping[str, str] | None = None,
    startupinfo: Any = None,
    creationflags: int = 0,
    start_new_session: bool = False,
    pass_fds: Sequence[int] = (),
    user: str | int | None = None,
    group: str | int | None = None,
    extra_groups: Iterable[str | int] | None = None,
    umask: int = -1,
) -> CompletedProcess[bytes]:
    """
    Run an external command in a subprocess and wait until it completes.

    .. seealso:: :func:`subprocess.run`

    :param command: either a string to pass to the shell, or an iterable of strings
        containing the executable name or path and its arguments
    :param input: bytes passed to the standard input of the subprocess
    :param stdin: one of :data:`subprocess.PIPE`, :data:`subprocess.DEVNULL`,
        a file-like object, or `None`; ``input`` overrides this
    :param stdout: one of :data:`subprocess.PIPE`, :data:`subprocess.DEVNULL`,
        a file-like object, or `None`
    :param stderr: one of :data:`subprocess.PIPE`, :data:`subprocess.DEVNULL`,
        :data:`subprocess.STDOUT`, a file-like object, or `None`
    :param check: if ``True``, raise :exc:`~subprocess.CalledProcessError` if the
        process terminates with a return code other than 0
    :param cwd: If not ``None``, change the working directory to this before running the
        command
    :param env: if not ``None``, this mapping replaces the inherited environment
        variables from the parent process
    :param startupinfo: an instance of :class:`subprocess.STARTUPINFO` that can be used
        to specify process startup parameters (Windows only)
    :param creationflags: flags that can be used to control the creation of the
        subprocess (see :class:`subprocess.Popen` for the specifics)
    :param start_new_session: if ``true`` the setsid() system call will be made in the
        child process prior to the execution of the subprocess. (POSIX only)
    :param pass_fds: sequence of file descriptors to keep open between the parent and
        child processes. (POSIX only)
    :param user: effective user to run the process as (Python >= 3.9, POSIX only)
    :param group: effective group to run the process as (Python >= 3.9, POSIX only)
    :param extra_groups: supplementary groups to set in the subprocess (Python >= 3.9,
        POSIX only)
    :param umask: if not negative, this umask is applied in the child process before
        running the given command (Python >= 3.9, POSIX only)
    :return: an object representing the completed process
    :raises ~subprocess.CalledProcessError: if ``check`` is ``True`` and the process
        exits with a nonzero return code

    """

    async def drain_stream(stream: AsyncIterable[bytes], index: int) -> None:
        buffer = BytesIO()
        async for chunk in stream:
            buffer.write(chunk)

        stream_contents[index] = buffer.getvalue()

    if stdin is not None and input is not None:
        raise ValueError("only one of stdin and input is allowed")

    async with await open_process(
        command,
        stdin=PIPE if input else stdin,
        stdout=stdout,
        stderr=stderr,
        cwd=cwd,
        env=env,
        startupinfo=startupinfo,
        creationflags=creationflags,
        start_new_session=start_new_session,
        pass_fds=pass_fds,
        user=user,
        group=group,
        extra_groups=extra_groups,
        umask=umask,
    ) as process:
        stream_contents: list[bytes | None] = [None, None]
        async with create_task_group() as tg:
            if process.stdout:
                tg.start_soon(drain_stream, process.stdout, 0)

            if process.stderr:
                tg.start_soon(drain_stream, process.stderr, 1)

            if process.stdin and input:
                await process.stdin.send(input)
                await process.stdin.aclose()

            await process.wait()

    output, errors = stream_contents
    if check and process.returncode != 0:
        raise CalledProcessError(cast(int, process.returncode), command, output, errors)

    return CompletedProcess(command, cast(int, process.returncode), output, errors)


async def open_process(
    command: StrOrBytesPath | Sequence[StrOrBytesPath],
    *,
    stdin: int | IO[Any] | None = PIPE,
    stdout: int | IO[Any] | None = PIPE,
    stderr: int | IO[Any] | None = PIPE,
    cwd: StrOrBytesPath | None = None,
    env: Mapping[str, str] | None = None,
    startupinfo: Any = None,
    creationflags: int = 0,
    start_new_session: bool = False,
    pass_fds: Sequence[int] = (),
    user: str | int | None = None,
    group: str | int | None = None,
    extra_groups: Iterable[str | int] | None = None,
    umask: int = -1,
) -> Process:
    """
    Start an external command in a subprocess.

    .. seealso:: :class:`subprocess.Popen`

    :param command: either a string to pass to the shell, or an iterable of strings
        containing the executable name or path and its arguments
    :param stdin: one of :data:`subprocess.PIPE`, :data:`subprocess.DEVNULL`, a
        file-like object, or ``None``
    :param stdout: one of :data:`subprocess.PIPE`, :data:`subprocess.DEVNULL`,
        a file-like object, or ``None``
    :param stderr: one of :data:`subprocess.PIPE`, :data:`subprocess.DEVNULL`,
        :data:`subprocess.STDOUT`, a file-like object, or ``None``
    :param cwd: If not ``None``, the working directory is changed before executing
    :param env: If env is not ``None``, it must be a mapping that defines the
        environment variables for the new process
    :param creationflags: flags that can be used to control the creation of the
        subprocess (see :class:`subprocess.Popen` for the specifics)
    :param startupinfo: an instance of :class:`subprocess.STARTUPINFO` that can be used
        to specify process startup parameters (Windows only)
    :param start_new_session: if ``true`` the setsid() system call will be made in the
        child process prior to the execution of the subprocess. (POSIX only)
    :param pass_fds: sequence of file descriptors to keep open between the parent and
        child processes. (POSIX only)
    :param user: effective user to run the process as (POSIX only)
    :param group: effective group to run the process as (POSIX only)
    :param extra_groups: supplementary groups to set in the subprocess (POSIX only)
    :param umask: if not negative, this umask is applied in the child process before
        running the given command (POSIX only)
    :return: an asynchronous process object

    """
    kwargs: dict[str, Any] = {}
    if user is not None:
        kwargs["user"] = user

    if group is not None:
        kwargs["group"] = group

    if extra_groups is not None:
        kwargs["extra_groups"] = group

    if umask >= 0:
        kwargs["umask"] = umask

    return await get_async_backend().open_process(
        command,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        cwd=cwd,
        env=env,
        startupinfo=startupinfo,
        creationflags=creationflags,
        start_new_session=start_new_session,
        pass_fds=pass_fds,
        **kwargs,
    )

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_daemon_thread.py ===
from _pydev_bundle._pydev_saved_modules import threading
from _pydev_bundle import _pydev_saved_modules
from _pydevd_bundle.pydevd_utils import notify_about_gevent_if_needed
import weakref
from _pydevd_bundle.pydevd_constants import (
    IS_JYTHON,
    IS_IRONPYTHON,
    PYDEVD_APPLY_PATCHING_TO_HIDE_PYDEVD_THREADS,
    PYDEVD_USE_SYS_MONITORING,
)
from _pydev_bundle.pydev_log import exception as pydev_log_exception
import sys
from _pydev_bundle import pydev_log
import pydevd_tracing
from _pydevd_bundle.pydevd_collect_bytecode_info import iter_instructions
from _pydevd_sys_monitoring import pydevd_sys_monitoring

if IS_JYTHON:
    import org.python.core as JyCore  # @UnresolvedImport


class PyDBDaemonThread(threading.Thread):
    def __init__(self, py_db, target_and_args=None):
        """
        :param target_and_args:
            tuple(func, args, kwargs) if this should be a function and args to run.
            -- Note: use through run_as_pydevd_daemon_thread().
        """
        threading.Thread.__init__(self)
        notify_about_gevent_if_needed()
        self._py_db = weakref.ref(py_db)
        self._kill_received = False
        mark_as_pydevd_daemon_thread(self)
        self._target_and_args = target_and_args

    @property
    def py_db(self):
        return self._py_db()

    def run(self):
        created_pydb_daemon = self.py_db.created_pydb_daemon_threads
        created_pydb_daemon[self] = 1
        try:
            try:
                if IS_JYTHON and not isinstance(threading.current_thread(), threading._MainThread):
                    # we shouldn't update sys.modules for the main thread, cause it leads to the second importing 'threading'
                    # module, and the new instance of main thread is created
                    ss = JyCore.PySystemState()
                    # Note: Py.setSystemState() affects only the current thread.
                    JyCore.Py.setSystemState(ss)

                self._stop_trace()
                self._on_run()
            except:
                if sys is not None and pydev_log_exception is not None:
                    pydev_log_exception()
        finally:
            del created_pydb_daemon[self]

    def _on_run(self):
        if self._target_and_args is not None:
            target, args, kwargs = self._target_and_args
            target(*args, **kwargs)
        else:
            raise NotImplementedError("Should be reimplemented by: %s" % self.__class__)

    def do_kill_pydev_thread(self):
        if not self._kill_received:
            pydev_log.debug("%s received kill signal", self.name)
            self._kill_received = True

    def _stop_trace(self):
        if self.pydev_do_not_trace:
            if PYDEVD_USE_SYS_MONITORING:
                pydevd_sys_monitoring.stop_monitoring(all_threads=False)
                return
            pydevd_tracing.SetTrace(None)  # no debugging on this thread


def _collect_load_names(func):
    found_load_names = set()
    for instruction in iter_instructions(func.__code__):
        if instruction.opname in ("LOAD_GLOBAL", "LOAD_ATTR", "LOAD_METHOD"):
            found_load_names.add(instruction.argrepr)
    return found_load_names


def _patch_threading_to_hide_pydevd_threads():
    """
    Patches the needed functions on the `threading` module so that the pydevd threads are hidden.

    Note that we patch the functions __code__ to avoid issues if some code had already imported those
    variables prior to the patching.
    """
    found_load_names = _collect_load_names(threading.enumerate)
    # i.e.: we'll only apply the patching if the function seems to be what we expect.

    new_threading_enumerate = None

    if found_load_names in (
        {"_active_limbo_lock", "_limbo", "_active", "values", "list"},
        {"_active_limbo_lock", "_limbo", "_active", "values", "NULL + list"},
        {"NULL + list", "_active", "_active_limbo_lock", "NULL|self + values", "_limbo"},
        {"_active_limbo_lock", "values + NULL|self", "_limbo", "_active", "list + NULL"},
    ):
        pydev_log.debug("Applying patching to hide pydevd threads (Py3 version).")

        def new_threading_enumerate():
            with _active_limbo_lock:
                ret = list(_active.values()) + list(_limbo.values())

            return [t for t in ret if not getattr(t, "is_pydev_daemon_thread", False)]

    elif found_load_names == set(("_active_limbo_lock", "_limbo", "_active", "values")):
        pydev_log.debug("Applying patching to hide pydevd threads (Py2 version).")

        def new_threading_enumerate():
            with _active_limbo_lock:
                ret = _active.values() + _limbo.values()

            return [t for t in ret if not getattr(t, "is_pydev_daemon_thread", False)]

    else:
        pydev_log.info("Unable to hide pydevd threads. Found names in threading.enumerate: %s", found_load_names)

    if new_threading_enumerate is not None:

        def pydevd_saved_threading_enumerate():
            with threading._active_limbo_lock:
                return list(threading._active.values()) + list(threading._limbo.values())

        _pydev_saved_modules.pydevd_saved_threading_enumerate = pydevd_saved_threading_enumerate

        threading.enumerate.__code__ = new_threading_enumerate.__code__

        # We also need to patch the active count (to match what we have in the enumerate).
        def new_active_count():
            # Note: as this will be executed in the `threading` module, `enumerate` will
            # actually be threading.enumerate.
            return len(enumerate())

        threading.active_count.__code__ = new_active_count.__code__

        # When shutting down, Python (on some versions) may do something as:
        #
        # def _pickSomeNonDaemonThread():
        #     for t in enumerate():
        #         if not t.daemon and t.is_alive():
        #             return t
        #     return None
        #
        # But in this particular case, we do want threads with `is_pydev_daemon_thread` to appear
        # explicitly due to the pydevd `CheckAliveThread` (because we want the shutdown to wait on it).
        # So, it can't rely on the `enumerate` for that anymore as it's patched to not return pydevd threads.
        if hasattr(threading, "_pickSomeNonDaemonThread"):

            def new_pick_some_non_daemon_thread():
                with _active_limbo_lock:
                    # Ok for py2 and py3.
                    threads = list(_active.values()) + list(_limbo.values())

                for t in threads:
                    if not t.daemon and t.is_alive():
                        return t
                return None

            threading._pickSomeNonDaemonThread.__code__ = new_pick_some_non_daemon_thread.__code__


_patched_threading_to_hide_pydevd_threads = False


def mark_as_pydevd_daemon_thread(thread):
    if not IS_JYTHON and not IS_IRONPYTHON and PYDEVD_APPLY_PATCHING_TO_HIDE_PYDEVD_THREADS:
        global _patched_threading_to_hide_pydevd_threads
        if not _patched_threading_to_hide_pydevd_threads:
            # When we mark the first thread as a pydevd daemon thread, we also change the threading
            # functions to hide pydevd threads.
            # Note: we don't just "hide" the pydevd threads from the threading module by not using it
            # (i.e.: just using the `thread.start_new_thread` instead of `threading.Thread`)
            # because there's 1 thread (the `CheckAliveThread`) which is a pydevd thread but
            # isn't really a daemon thread (so, we need CPython to wait on it for shutdown,
            # in which case it needs to be in `threading` and the patching would be needed anyways).
            _patched_threading_to_hide_pydevd_threads = True
            try:
                _patch_threading_to_hide_pydevd_threads()
            except:
                pydev_log.exception("Error applying patching to hide pydevd threads.")

    thread.pydev_do_not_trace = True
    thread.is_pydev_daemon_thread = True
    thread.daemon = True


def run_as_pydevd_daemon_thread(py_db, func, *args, **kwargs):
    """
    Runs a function as a pydevd daemon thread (without any tracing in place).
    """
    t = PyDBDaemonThread(py_db, target_and_args=(func, args, kwargs))
    t.name = "%s (pydevd daemon thread)" % (func.__name__,)
    t.start()
    return t

# === NexusCore/openenv\Lib\site-packages\git\index\typ.py ===
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

"""Additional types used by the index."""

__all__ = ["BlobFilter", "BaseIndexEntry", "IndexEntry", "StageType"]

from binascii import b2a_hex
from pathlib import Path

from git.objects import Blob

from .util import pack, unpack

# typing ----------------------------------------------------------------------

from typing import NamedTuple, Sequence, TYPE_CHECKING, Tuple, Union, cast

from git.types import PathLike

if TYPE_CHECKING:
    from git.repo import Repo

StageType = int

# ---------------------------------------------------------------------------------

# { Invariants
CE_NAMEMASK = 0x0FFF
CE_STAGEMASK = 0x3000
CE_EXTENDED = 0x4000
CE_VALID = 0x8000
CE_STAGESHIFT = 12

# } END invariants


class BlobFilter:
    """Predicate to be used by
    :meth:`IndexFile.iter_blobs <git.index.base.IndexFile.iter_blobs>` allowing to
    filter only return blobs which match the given list of directories or files.

    The given paths are given relative to the repository.
    """

    __slots__ = ("paths",)

    def __init__(self, paths: Sequence[PathLike]) -> None:
        """
        :param paths:
            Tuple or list of paths which are either pointing to directories or to files
            relative to the current repository.
        """
        self.paths = paths

    def __call__(self, stage_blob: Tuple[StageType, Blob]) -> bool:
        blob_pathlike: PathLike = stage_blob[1].path
        blob_path: Path = blob_pathlike if isinstance(blob_pathlike, Path) else Path(blob_pathlike)
        for pathlike in self.paths:
            path: Path = pathlike if isinstance(pathlike, Path) else Path(pathlike)
            # TODO: Change to use `PosixPath.is_relative_to` once Python 3.8 is no
            # longer supported.
            filter_parts = path.parts
            blob_parts = blob_path.parts
            if len(filter_parts) > len(blob_parts):
                continue
            if all(i == j for i, j in zip(filter_parts, blob_parts)):
                return True
        return False


class BaseIndexEntryHelper(NamedTuple):
    """Typed named tuple to provide named attribute access for :class:`BaseIndexEntry`.

    This is needed to allow overriding ``__new__`` in child class to preserve backwards
    compatibility.
    """

    mode: int
    binsha: bytes
    flags: int
    path: PathLike
    ctime_bytes: bytes = pack(">LL", 0, 0)
    mtime_bytes: bytes = pack(">LL", 0, 0)
    dev: int = 0
    inode: int = 0
    uid: int = 0
    gid: int = 0
    size: int = 0


class BaseIndexEntry(BaseIndexEntryHelper):
    R"""Small brother of an index entry which can be created to describe changes
    done to the index in which case plenty of additional information is not required.

    As the first 4 data members match exactly to the :class:`IndexEntry` type, methods
    expecting a :class:`BaseIndexEntry` can also handle full :class:`IndexEntry`\s even
    if they use numeric indices for performance reasons.
    """

    def __new__(
        cls,
        inp_tuple: Union[
            Tuple[int, bytes, int, PathLike],
            Tuple[int, bytes, int, PathLike, bytes, bytes, int, int, int, int, int],
        ],
    ) -> "BaseIndexEntry":
        """Override ``__new__`` to allow construction from a tuple for backwards
        compatibility."""
        return super().__new__(cls, *inp_tuple)

    def __str__(self) -> str:
        return "%o %s %i\t%s" % (self.mode, self.hexsha, self.stage, self.path)

    def __repr__(self) -> str:
        return "(%o, %s, %i, %s)" % (self.mode, self.hexsha, self.stage, self.path)

    @property
    def hexsha(self) -> str:
        """hex version of our sha"""
        return b2a_hex(self.binsha).decode("ascii")

    @property
    def stage(self) -> int:
        """Stage of the entry, either:

            * 0 = default stage
            * 1 = stage before a merge or common ancestor entry in case of a 3 way merge
            * 2 = stage of entries from the 'left' side of the merge
            * 3 = stage of entries from the 'right' side of the merge

        :note:
            For more information, see :manpage:`git-read-tree(1)`.
        """
        return (self.flags & CE_STAGEMASK) >> CE_STAGESHIFT

    @classmethod
    def from_blob(cls, blob: Blob, stage: int = 0) -> "BaseIndexEntry":
        """:return: Fully equipped BaseIndexEntry at the given stage"""
        return cls((blob.mode, blob.binsha, stage << CE_STAGESHIFT, blob.path))

    def to_blob(self, repo: "Repo") -> Blob:
        """:return: Blob using the information of this index entry"""
        return Blob(repo, self.binsha, self.mode, self.path)


class IndexEntry(BaseIndexEntry):
    """Allows convenient access to index entry data as defined in
    :class:`BaseIndexEntry` without completely unpacking it.

    Attributes usually accessed often are cached in the tuple whereas others are
    unpacked on demand.

    See the properties for a mapping between names and tuple indices.
    """

    @property
    def ctime(self) -> Tuple[int, int]:
        """
        :return:
            Tuple(int_time_seconds_since_epoch, int_nano_seconds) of the
            file's creation time
        """
        return cast(Tuple[int, int], unpack(">LL", self.ctime_bytes))

    @property
    def mtime(self) -> Tuple[int, int]:
        """See :attr:`ctime` property, but returns modification time."""
        return cast(Tuple[int, int], unpack(">LL", self.mtime_bytes))

    @classmethod
    def from_base(cls, base: "BaseIndexEntry") -> "IndexEntry":
        """
        :return:
            Minimal entry as created from the given :class:`BaseIndexEntry` instance.
            Missing values will be set to null-like values.

        :param base:
            Instance of type :class:`BaseIndexEntry`.
        """
        time = pack(">LL", 0, 0)
        return IndexEntry((base.mode, base.binsha, base.flags, base.path, time, time, 0, 0, 0, 0, 0))

    @classmethod
    def from_blob(cls, blob: Blob, stage: int = 0) -> "IndexEntry":
        """:return: Minimal entry resembling the given blob object"""
        time = pack(">LL", 0, 0)
        return IndexEntry(
            (
                blob.mode,
                blob.binsha,
                stage << CE_STAGESHIFT,
                blob.path,
                time,
                time,
                0,
                0,
                0,
                0,
                blob.size,
            )
        )

# === NexusCore/openenv\Lib\site-packages\jedi\inference\helpers.py ===
import copy
import sys
import re
import os
from itertools import chain
from contextlib import contextmanager

from parso.python import tree


def is_stdlib_path(path):
    # Python standard library paths look like this:
    # /usr/lib/python3.9/...
    # TODO The implementation below is probably incorrect and not complete.
    parts = path.parts
    if 'dist-packages' in parts or 'site-packages' in parts:
        return False

    base_path = os.path.join(sys.prefix, 'lib', 'python')
    return bool(re.match(re.escape(base_path) + r'\d.\d', str(path)))


def deep_ast_copy(obj):
    """
    Much, much faster than copy.deepcopy, but just for parser tree nodes.
    """
    # If it's already in the cache, just return it.
    new_obj = copy.copy(obj)

    # Copy children
    new_children = []
    for child in obj.children:
        if isinstance(child, tree.Leaf):
            new_child = copy.copy(child)
            new_child.parent = new_obj
        else:
            new_child = deep_ast_copy(child)
            new_child.parent = new_obj
        new_children.append(new_child)
    new_obj.children = new_children

    return new_obj


def infer_call_of_leaf(context, leaf, cut_own_trailer=False):
    """
    Creates a "call" node that consist of all ``trailer`` and ``power``
    objects.  E.g. if you call it with ``append``::

        list([]).append(3) or None

    You would get a node with the content ``list([]).append`` back.

    This generates a copy of the original ast node.

    If you're using the leaf, e.g. the bracket `)` it will return ``list([])``.

    We use this function for two purposes. Given an expression ``bar.foo``,
    we may want to
      - infer the type of ``foo`` to offer completions after foo
      - infer the type of ``bar`` to be able to jump to the definition of foo
    The option ``cut_own_trailer`` must be set to true for the second purpose.
    """
    trailer = leaf.parent
    if trailer.type == 'fstring':
        from jedi.inference import compiled
        return compiled.get_string_value_set(context.inference_state)

    # The leaf may not be the last or first child, because there exist three
    # different trailers: `( x )`, `[ x ]` and `.x`. In the first two examples
    # we should not match anything more than x.
    if trailer.type != 'trailer' or leaf not in (trailer.children[0], trailer.children[-1]):
        if leaf == ':':
            # Basically happens with foo[:] when the cursor is on the colon
            from jedi.inference.base_value import NO_VALUES
            return NO_VALUES
        if trailer.type == 'atom':
            return context.infer_node(trailer)
        return context.infer_node(leaf)

    power = trailer.parent
    index = power.children.index(trailer)
    if cut_own_trailer:
        cut = index
    else:
        cut = index + 1

    if power.type == 'error_node':
        start = index
        while True:
            start -= 1
            base = power.children[start]
            if base.type != 'trailer':
                break
        trailers = power.children[start + 1:cut]
    else:
        base = power.children[0]
        trailers = power.children[1:cut]

    if base == 'await':
        base = trailers[0]
        trailers = trailers[1:]

    values = context.infer_node(base)
    from jedi.inference.syntax_tree import infer_trailer
    for trailer in trailers:
        values = infer_trailer(context, values, trailer)
    return values


def get_names_of_node(node):
    try:
        children = node.children
    except AttributeError:
        if node.type == 'name':
            return [node]
        else:
            return []
    else:
        return list(chain.from_iterable(get_names_of_node(c) for c in children))


def is_string(value):
    return value.is_compiled() and isinstance(value.get_safe_value(default=None), str)


def is_literal(value):
    return is_number(value) or is_string(value)


def _get_safe_value_or_none(value, accept):
    value = value.get_safe_value(default=None)
    if isinstance(value, accept):
        return value


def get_int_or_none(value):
    return _get_safe_value_or_none(value, int)


def get_str_or_none(value):
    return _get_safe_value_or_none(value, str)


def is_number(value):
    return _get_safe_value_or_none(value, (int, float)) is not None


class SimpleGetItemNotFound(Exception):
    pass


@contextmanager
def reraise_getitem_errors(*exception_classes):
    try:
        yield
    except exception_classes as e:
        raise SimpleGetItemNotFound(e)


def parse_dotted_names(nodes, is_import_from, until_node=None):
    level = 0
    names = []
    for node in nodes[1:]:
        if node in ('.', '...'):
            if not names:
                level += len(node.value)
        elif node.type == 'dotted_name':
            for n in node.children[::2]:
                names.append(n)
                if n is until_node:
                    break
            else:
                continue
            break
        elif node.type == 'name':
            names.append(node)
            if node is until_node:
                break
        elif node == ',':
            if not is_import_from:
                names = []
        else:
            # Here if the keyword `import` comes along it stops checking
            # for names.
            break
    return level, names


def values_from_qualified_names(inference_state, *names):
    return inference_state.import_module(names[:-1]).py__getattribute__(names[-1])


def is_big_annoying_library(context):
    string_names = context.get_root_context().string_names
    if string_names is None:
        return False

    # Especially pandas and tensorflow are huge complicated Python libraries
    # that get even slower than they already are when Jedi tries to undrstand
    # dynamic features like decorators, ifs and other stuff.
    return string_names[0] in ('pandas', 'numpy', 'tensorflow', 'matplotlib')

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\lago.py ===
# What is this?
## On Success events log cost to Lago - https://github.com/BerriAI/litellm/issues/3639

import json
import os
import uuid
from typing import Literal, Optional

import httpx

import litellm
from litellm._logging import verbose_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.llms.custom_httpx.http_handler import (
    HTTPHandler,
    get_async_httpx_client,
    httpxSpecialProvider,
)


def get_utc_datetime():
    import datetime as dt
    from datetime import datetime

    if hasattr(dt, "UTC"):
        return datetime.now(dt.UTC)  # type: ignore
    else:
        return datetime.utcnow()  # type: ignore


class LagoLogger(CustomLogger):
    def __init__(self) -> None:
        super().__init__()
        self.validate_environment()
        self.async_http_handler = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.LoggingCallback
        )
        self.sync_http_handler = HTTPHandler()

    def validate_environment(self):
        """
        Expects
        LAGO_API_BASE,
        LAGO_API_KEY,
        LAGO_API_EVENT_CODE,

        Optional:
        LAGO_API_CHARGE_BY

        in the environment
        """
        missing_keys = []
        if os.getenv("LAGO_API_KEY", None) is None:
            missing_keys.append("LAGO_API_KEY")

        if os.getenv("LAGO_API_BASE", None) is None:
            missing_keys.append("LAGO_API_BASE")

        if os.getenv("LAGO_API_EVENT_CODE", None) is None:
            missing_keys.append("LAGO_API_EVENT_CODE")

        if len(missing_keys) > 0:
            raise Exception("Missing keys={} in environment.".format(missing_keys))

    def _common_logic(self, kwargs: dict, response_obj) -> dict:
        response_obj.get("id", kwargs.get("litellm_call_id"))
        get_utc_datetime().isoformat()
        cost = kwargs.get("response_cost", None)
        model = kwargs.get("model")
        usage = {}

        if (
            isinstance(response_obj, litellm.ModelResponse)
            or isinstance(response_obj, litellm.EmbeddingResponse)
        ) and hasattr(response_obj, "usage"):
            usage = {
                "prompt_tokens": response_obj["usage"].get("prompt_tokens", 0),
                "completion_tokens": response_obj["usage"].get("completion_tokens", 0),
                "total_tokens": response_obj["usage"].get("total_tokens"),
            }

        litellm_params = kwargs.get("litellm_params", {}) or {}
        proxy_server_request = litellm_params.get("proxy_server_request") or {}
        end_user_id = proxy_server_request.get("body", {}).get("user", None)
        user_id = litellm_params["metadata"].get("user_api_key_user_id", None)
        team_id = litellm_params["metadata"].get("user_api_key_team_id", None)
        litellm_params["metadata"].get("user_api_key_org_id", None)

        charge_by: Literal["end_user_id", "team_id", "user_id"] = "end_user_id"
        external_customer_id: Optional[str] = None

        if os.getenv("LAGO_API_CHARGE_BY", None) is not None and isinstance(
            os.environ["LAGO_API_CHARGE_BY"], str
        ):
            if os.environ["LAGO_API_CHARGE_BY"] in [
                "end_user_id",
                "user_id",
                "team_id",
            ]:
                charge_by = os.environ["LAGO_API_CHARGE_BY"]  # type: ignore
            else:
                raise Exception("invalid LAGO_API_CHARGE_BY set")

        if charge_by == "end_user_id":
            external_customer_id = end_user_id
        elif charge_by == "team_id":
            external_customer_id = team_id
        elif charge_by == "user_id":
            external_customer_id = user_id

        if external_customer_id is None:
            raise Exception(
                "External Customer ID is not set. Charge_by={}. User_id={}. End_user_id={}. Team_id={}".format(
                    charge_by, user_id, end_user_id, team_id
                )
            )

        returned_val = {
            "event": {
                "transaction_id": str(uuid.uuid4()),
                "external_subscription_id": external_customer_id,
                "code": os.getenv("LAGO_API_EVENT_CODE"),
                "properties": {"model": model, "response_cost": cost, **usage},
            }
        }

        verbose_logger.debug(
            "\033[91mLogged Lago Object:\n{}\033[0m\n".format(returned_val)
        )
        return returned_val

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        _url = os.getenv("LAGO_API_BASE")
        assert _url is not None and isinstance(
            _url, str
        ), "LAGO_API_BASE missing or not set correctly. LAGO_API_BASE={}".format(_url)
        if _url.endswith("/"):
            _url += "api/v1/events"
        else:
            _url += "/api/v1/events"

        api_key = os.getenv("LAGO_API_KEY")

        _data = self._common_logic(kwargs=kwargs, response_obj=response_obj)
        _headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(api_key),
        }

        try:
            response = self.sync_http_handler.post(
                url=_url,
                data=json.dumps(_data),
                headers=_headers,
            )

            response.raise_for_status()
        except Exception as e:
            error_response = getattr(e, "response", None)
            if error_response is not None and hasattr(error_response, "text"):
                verbose_logger.debug(f"\nError Message: {error_response.text}")
            raise e

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            verbose_logger.debug("ENTERS LAGO CALLBACK")
            _url = os.getenv("LAGO_API_BASE")
            assert _url is not None and isinstance(
                _url, str
            ), "LAGO_API_BASE missing or not set correctly. LAGO_API_BASE={}".format(
                _url
            )
            if _url.endswith("/"):
                _url += "api/v1/events"
            else:
                _url += "/api/v1/events"

            api_key = os.getenv("LAGO_API_KEY")

            _data = self._common_logic(kwargs=kwargs, response_obj=response_obj)
            _headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(api_key),
            }
        except Exception as e:
            raise e

        response: Optional[httpx.Response] = None
        try:
            response = await self.async_http_handler.post(
                url=_url,
                data=json.dumps(_data),
                headers=_headers,
            )

            response.raise_for_status()

            verbose_logger.debug(f"Logged Lago Object: {response.text}")
        except Exception as e:
            if response is not None and hasattr(response, "text"):
                verbose_logger.debug(f"\nError Message: {response.text}")
            raise e

# === NexusCore/openenv\Lib\site-packages\markdown_it\rules_core\smartquotes.py ===
"""Convert straight quotation marks to typographic ones
"""
from __future__ import annotations

import re
from typing import Any

from ..common.utils import charCodeAt, isMdAsciiPunct, isPunctChar, isWhiteSpace
from ..token import Token
from .state_core import StateCore

QUOTE_TEST_RE = re.compile(r"['\"]")
QUOTE_RE = re.compile(r"['\"]")
APOSTROPHE = "\u2019"  # ’


def replaceAt(string: str, index: int, ch: str) -> str:
    # When the index is negative, the behavior is different from the js version.
    # But basically, the index will not be negative.
    assert index >= 0
    return string[:index] + ch + string[index + 1 :]


def process_inlines(tokens: list[Token], state: StateCore) -> None:
    stack: list[dict[str, Any]] = []

    for i, token in enumerate(tokens):
        thisLevel = token.level

        j = 0
        for j in range(len(stack))[::-1]:
            if stack[j]["level"] <= thisLevel:
                break
        else:
            # When the loop is terminated without a "break".
            # Subtract 1 to get the same index as the js version.
            j -= 1

        stack = stack[: j + 1]

        if token.type != "text":
            continue

        text = token.content
        pos = 0
        maximum = len(text)

        while pos < maximum:
            goto_outer = False
            lastIndex = pos
            t = QUOTE_RE.search(text[lastIndex:])
            if not t:
                break

            canOpen = canClose = True
            pos = t.start(0) + lastIndex + 1
            isSingle = t.group(0) == "'"

            # Find previous character,
            # default to space if it's the beginning of the line
            lastChar: None | int = 0x20

            if t.start(0) + lastIndex - 1 >= 0:
                lastChar = charCodeAt(text, t.start(0) + lastIndex - 1)
            else:
                for j in range(i)[::-1]:
                    if tokens[j].type == "softbreak" or tokens[j].type == "hardbreak":
                        break
                    # should skip all tokens except 'text', 'html_inline' or 'code_inline'
                    if not tokens[j].content:
                        continue

                    lastChar = charCodeAt(tokens[j].content, len(tokens[j].content) - 1)
                    break

            # Find next character,
            # default to space if it's the end of the line
            nextChar: None | int = 0x20

            if pos < maximum:
                nextChar = charCodeAt(text, pos)
            else:
                for j in range(i + 1, len(tokens)):
                    # nextChar defaults to 0x20
                    if tokens[j].type == "softbreak" or tokens[j].type == "hardbreak":
                        break
                    # should skip all tokens except 'text', 'html_inline' or 'code_inline'
                    if not tokens[j].content:
                        continue

                    nextChar = charCodeAt(tokens[j].content, 0)
                    break

            isLastPunctChar = lastChar is not None and (
                isMdAsciiPunct(lastChar) or isPunctChar(chr(lastChar))
            )
            isNextPunctChar = nextChar is not None and (
                isMdAsciiPunct(nextChar) or isPunctChar(chr(nextChar))
            )

            isLastWhiteSpace = lastChar is not None and isWhiteSpace(lastChar)
            isNextWhiteSpace = nextChar is not None and isWhiteSpace(nextChar)

            if isNextWhiteSpace:  # noqa: SIM114
                canOpen = False
            elif isNextPunctChar and not (isLastWhiteSpace or isLastPunctChar):
                canOpen = False

            if isLastWhiteSpace:  # noqa: SIM114
                canClose = False
            elif isLastPunctChar and not (isNextWhiteSpace or isNextPunctChar):
                canClose = False

            if nextChar == 0x22 and t.group(0) == '"':  # 0x22: "  # noqa: SIM102
                if (
                    lastChar is not None and lastChar >= 0x30 and lastChar <= 0x39
                ):  # 0x30: 0, 0x39: 9
                    # special case: 1"" - count first quote as an inch
                    canClose = canOpen = False

            if canOpen and canClose:
                # Replace quotes in the middle of punctuation sequence, but not
                # in the middle of the words, i.e.:
                #
                # 1. foo " bar " baz - not replaced
                # 2. foo-"-bar-"-baz - replaced
                # 3. foo"bar"baz     - not replaced
                canOpen = isLastPunctChar
                canClose = isNextPunctChar

            if not canOpen and not canClose:
                # middle of word
                if isSingle:
                    token.content = replaceAt(
                        token.content, t.start(0) + lastIndex, APOSTROPHE
                    )
                continue

            if canClose:
                # this could be a closing quote, rewind the stack to get a match
                for j in range(len(stack))[::-1]:
                    item = stack[j]
                    if stack[j]["level"] < thisLevel:
                        break
                    if item["single"] == isSingle and stack[j]["level"] == thisLevel:
                        item = stack[j]

                        if isSingle:
                            openQuote = state.md.options.quotes[2]
                            closeQuote = state.md.options.quotes[3]
                        else:
                            openQuote = state.md.options.quotes[0]
                            closeQuote = state.md.options.quotes[1]

                        # replace token.content *before* tokens[item.token].content,
                        # because, if they are pointing at the same token, replaceAt
                        # could mess up indices when quote length != 1
                        token.content = replaceAt(
                            token.content, t.start(0) + lastIndex, closeQuote
                        )
                        tokens[item["token"]].content = replaceAt(
                            tokens[item["token"]].content, item["pos"], openQuote
                        )

                        pos += len(closeQuote) - 1
                        if item["token"] == i:
                            pos += len(openQuote) - 1

                        text = token.content
                        maximum = len(text)

                        stack = stack[:j]
                        goto_outer = True
                        break
                if goto_outer:
                    goto_outer = False
                    continue

            if canOpen:
                stack.append(
                    {
                        "token": i,
                        "pos": t.start(0) + lastIndex,
                        "single": isSingle,
                        "level": thisLevel,
                    }
                )
            elif canClose and isSingle:
                token.content = replaceAt(
                    token.content, t.start(0) + lastIndex, APOSTROPHE
                )


def smartquotes(state: StateCore) -> None:
    if not state.md.options.typographer:
        return

    for token in state.tokens:
        if token.type != "inline" or not QUOTE_RE.search(token.content):
            continue
        if token.children is not None:
            process_inlines(token.children, state)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\pawn.py ===
"""
    pygments.lexers.pawn
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for the Pawn languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation
from pygments.util import get_bool_opt

__all__ = ['SourcePawnLexer', 'PawnLexer']


class SourcePawnLexer(RegexLexer):
    """
    For SourcePawn source code with preprocessor directives.
    """
    name = 'SourcePawn'
    aliases = ['sp']
    filenames = ['*.sp']
    mimetypes = ['text/x-sourcepawn']
    url = 'https://github.com/alliedmodders/sourcepawn'
    version_added = '1.6'

    #: optional Comment or Whitespace
    _ws = r'(?:\s|//.*?\n|/\*.*?\*/)+'
    #: only one /* */ style comment
    _ws1 = r'\s*(?:/[*].*?[*]/\s*)*'

    tokens = {
        'root': [
            # preprocessor directives: without whitespace
            (r'^#if\s+0', Comment.Preproc, 'if0'),
            ('^#', Comment.Preproc, 'macro'),
            # or with whitespace
            ('^' + _ws1 + r'#if\s+0', Comment.Preproc, 'if0'),
            ('^' + _ws1 + '#', Comment.Preproc, 'macro'),
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),  # line continuation
            (r'/(\\\n)?/(\n|(.|\n)*?[^\\]\n)', Comment.Single),
            (r'/(\\\n)?\*(.|\n)*?\*(\\\n)?/', Comment.Multiline),
            (r'[{}]', Punctuation),
            (r'L?"', String, 'string'),
            (r"L?'(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,2}|[^\\\'\n])'", String.Char),
            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+[LlUu]*', Number.Float),
            (r'(\d+\.\d*|\.\d+|\d+[fF])[fF]?', Number.Float),
            (r'0x[0-9a-fA-F]+[LlUu]*', Number.Hex),
            (r'0[0-7]+[LlUu]*', Number.Oct),
            (r'\d+[LlUu]*', Number.Integer),
            (r'[~!%^&*+=|?:<>/-]', Operator),
            (r'[()\[\],.;]', Punctuation),
            (r'(case|const|continue|native|'
             r'default|else|enum|for|if|new|operator|'
             r'public|return|sizeof|static|decl|struct|switch)\b', Keyword),
            (r'(bool|Float)\b', Keyword.Type),
            (r'(true|false)\b', Keyword.Constant),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|[0-7]{1,3})', String.Escape),
            (r'[^\\"\n]+', String),  # all other characters
            (r'\\\n', String),       # line continuation
            (r'\\', String),         # stray backslash
        ],
        'macro': [
            (r'[^/\n]+', Comment.Preproc),
            (r'/\*(.|\n)*?\*/', Comment.Multiline),
            (r'//.*?\n', Comment.Single, '#pop'),
            (r'/', Comment.Preproc),
            (r'(?<=\\)\n', Comment.Preproc),
            (r'\n', Comment.Preproc, '#pop'),
        ],
        'if0': [
            (r'^\s*#if.*?(?<!\\)\n', Comment.Preproc, '#push'),
            (r'^\s*#endif.*?(?<!\\)\n', Comment.Preproc, '#pop'),
            (r'.*?\n', Comment),
        ]
    }

    SM_TYPES = {'Action', 'bool', 'Float', 'Plugin', 'String', 'any',
                'AdminFlag', 'OverrideType', 'OverrideRule', 'ImmunityType',
                'GroupId', 'AdminId', 'AdmAccessMode', 'AdminCachePart',
                'CookieAccess', 'CookieMenu', 'CookieMenuAction', 'NetFlow',
                'ConVarBounds', 'QueryCookie', 'ReplySource',
                'ConVarQueryResult', 'ConVarQueryFinished', 'Function',
                'Action', 'Identity', 'PluginStatus', 'PluginInfo', 'DBResult',
                'DBBindType', 'DBPriority', 'PropType', 'PropFieldType',
                'MoveType', 'RenderMode', 'RenderFx', 'EventHookMode',
                'EventHook', 'FileType', 'FileTimeMode', 'PathType',
                'ParamType', 'ExecType', 'DialogType', 'Handle', 'KvDataTypes',
                'NominateResult', 'MapChange', 'MenuStyle', 'MenuAction',
                'MenuSource', 'RegexError', 'SDKCallType', 'SDKLibrary',
                'SDKFuncConfSource', 'SDKType', 'SDKPassMethod', 'RayType',
                'TraceEntityFilter', 'ListenOverride', 'SortOrder', 'SortType',
                'SortFunc2D', 'APLRes', 'FeatureType', 'FeatureStatus',
                'SMCResult', 'SMCError', 'TFClassType', 'TFTeam', 'TFCond',
                'TFResourceType', 'Timer', 'TopMenuAction', 'TopMenuObjectType',
                'TopMenuPosition', 'TopMenuObject', 'UserMsg'}

    def __init__(self, **options):
        self.smhighlighting = get_bool_opt(options,
                                           'sourcemod', True)

        self._functions = set()
        if self.smhighlighting:
            from pygments.lexers._sourcemod_builtins import FUNCTIONS
            self._functions.update(FUNCTIONS)
        RegexLexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        for index, token, value in \
                RegexLexer.get_tokens_unprocessed(self, text):
            if token is Name:
                if self.smhighlighting:
                    if value in self.SM_TYPES:
                        token = Keyword.Type
                    elif value in self._functions:
                        token = Name.Builtin
            yield index, token, value


class PawnLexer(RegexLexer):
    """
    For Pawn source code.
    """

    name = 'Pawn'
    aliases = ['pawn']
    filenames = ['*.p', '*.pwn', '*.inc']
    mimetypes = ['text/x-pawn']
    url = 'https://www.compuphase.com/pawn/pawn.htm'
    version_added = '2.0'

    #: optional Comment or Whitespace
    _ws = r'(?:\s|//.*?\n|/[*][\w\W]*?[*]/)+'
    #: only one /* */ style comment
    _ws1 = r'\s*(?:/[*].*?[*]/\s*)*'

    tokens = {
        'root': [
            # preprocessor directives: without whitespace
            (r'^#if\s+0', Comment.Preproc, 'if0'),
            ('^#', Comment.Preproc, 'macro'),
            # or with whitespace
            ('^' + _ws1 + r'#if\s+0', Comment.Preproc, 'if0'),
            ('^' + _ws1 + '#', Comment.Preproc, 'macro'),
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),  # line continuation
            (r'/(\\\n)?/(\n|(.|\n)*?[^\\]\n)', Comment.Single),
            (r'/(\\\n)?\*[\w\W]*?\*(\\\n)?/', Comment.Multiline),
            (r'[{}]', Punctuation),
            (r'L?"', String, 'string'),
            (r"L?'(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,2}|[^\\\'\n])'", String.Char),
            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+[LlUu]*', Number.Float),
            (r'(\d+\.\d*|\.\d+|\d+[fF])[fF]?', Number.Float),
            (r'0x[0-9a-fA-F]+[LlUu]*', Number.Hex),
            (r'0[0-7]+[LlUu]*', Number.Oct),
            (r'\d+[LlUu]*', Number.Integer),
            (r'[~!%^&*+=|?:<>/-]', Operator),
            (r'[()\[\],.;]', Punctuation),
            (r'(switch|case|default|const|new|static|char|continue|break|'
             r'if|else|for|while|do|operator|enum|'
             r'public|return|sizeof|tagof|state|goto)\b', Keyword),
            (r'(bool|Float)\b', Keyword.Type),
            (r'(true|false)\b', Keyword.Constant),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|[0-7]{1,3})', String.Escape),
            (r'[^\\"\n]+', String),  # all other characters
            (r'\\\n', String),       # line continuation
            (r'\\', String),         # stray backslash
        ],
        'macro': [
            (r'[^/\n]+', Comment.Preproc),
            (r'/\*(.|\n)*?\*/', Comment.Multiline),
            (r'//.*?\n', Comment.Single, '#pop'),
            (r'/', Comment.Preproc),
            (r'(?<=\\)\n', Comment.Preproc),
            (r'\n', Comment.Preproc, '#pop'),
        ],
        'if0': [
            (r'^\s*#if.*?(?<!\\)\n', Comment.Preproc, '#push'),
            (r'^\s*#endif.*?(?<!\\)\n', Comment.Preproc, '#pop'),
            (r'.*?\n', Comment),
        ]
    }

    def analyse_text(text):
        """This is basically C. There is a keyword which doesn't exist in C
        though and is nearly unique to this language."""
        if 'tagof' in text:
            return 0.01

# === NexusCore/evaluation\evalplus\evalplus\lecacy_sanitize.py ===
"""Legacy version of post-processing LLM-generated Python code.
This sanitizer is implemented using regex and string manipulation.
You might want to use the latest tree-sitter-based sanitizer (evalplus.sanitize) instead.
"""

import os
import pathlib
import re
from typing import List, Optional

from tqdm import tqdm

from evalplus.data import (
    get_human_eval_plus,
    get_mbpp_plus,
    load_solutions,
    write_directory,
    write_jsonl,
)
from evalplus.syncheck import syntax_check


def remove_unindented_lines(
    code: str, protect_before: str, execeptions: List[str], trim_tails: List[str]
) -> str:
    lines = code.splitlines()
    cut_idx = []
    cut_enabled = False
    for i, line in enumerate(lines):
        if not cut_enabled and line.startswith(protect_before):
            cut_enabled = True
            continue
        if line.strip() == "":
            continue
        if any(line.startswith(e) for e in execeptions):
            continue

        lspace = len(line) - len(line.lstrip())
        if lspace == 0:
            cut_idx.append(i)

        if any(line.rstrip().startswith(t) for t in trim_tails):
            # cut off everything behind
            cut_idx.extend(list(range(i, len(lines))))
            break

    return "\n".join([line for i, line in enumerate(lines) if i not in cut_idx])


def to_four_space_indents(old_code):
    new_code = ""
    for line in old_code.splitlines():
        lspace = len(line) - len(line.lstrip())
        if lspace == 3:
            new_code += " "
        new_code += line + "\n"
    return new_code


def sanitize(
    old_code: str,
    entry_point: str,
    rm_prefix_lines: Optional[str] = None,
    eofs: List = None,
):
    new_code = old_code
    if rm_prefix_lines is not None:
        new_code = "\n".join(
            [
                line
                for line in old_code.splitlines()
                if not line.startswith(rm_prefix_lines)
            ]
        )

    new_code = "\n" + new_code
    def_left = "def " + entry_point

    # basic handling of chat output
    new_code = new_code.replace("\n```python\n", "\n```\n")
    for chunk in new_code.split("\n```\n"):
        if def_left in chunk:
            new_code = chunk
            break

    chunks = [chunk for chunk in re.split(f"{def_left}\\s*\\(", new_code)]
    # TODO: having return does not mean this is complete
    bodies = [chunk for chunk in chunks[1:] if "    return " in chunk.split("\ndef")[0]]
    def_left = def_left + "("
    new_code = def_left + def_left.join(bodies) if len(bodies) > 0 else ""  # fn + impl
    new_code = to_four_space_indents(new_code)

    for eof in eofs or []:
        new_code = new_code.split(eof)[0]

    # remove lines starting from the first unindented line after def_left
    new_code = remove_unindented_lines(
        new_code,
        protect_before=def_left,
        execeptions=["def ", "import ", "from "],
        trim_tails=['"""', "if", "print"],
    )
    new_code = chunks[0] + new_code

    # cut all functions that are not syntactically correct && not the entry point
    parts = new_code.split("\ndef ")
    includes = [parts[0]]
    for fn in new_code.split("\ndef ")[1:]:
        if (
            fn.strip().startswith(entry_point + " ")
            or fn.strip().startswith(entry_point + "(")
            or syntax_check("\ndef " + fn)
        ):
            includes.append(fn)
    new_code = "\ndef ".join(includes)
    return new_code.strip()


def script(
    samples: str,
    eofs: List[str] = [],
    inplace: bool = False,
    rm_prefix_lines: str = None,
    debug_task: str = None,
    mbpp_version: str = "default",
):
    # task_id -> entry_point
    entry_point = {}
    dataset = {**get_human_eval_plus(), **get_mbpp_plus(version=mbpp_version)}

    for task_id, problem in dataset.items():
        entry_point[task_id] = problem["entry_point"]

    # make a new folder with "-sanitized" suffix
    is_folder = os.path.isdir(samples)
    target_path = pathlib.Path(samples)
    if not inplace:
        if is_folder:
            new_name = target_path.name + "-sanitized"
        else:
            new_name = target_path.name.replace(".jsonl", "-sanitized.jsonl")
        target_path = target_path.parent / new_name
    target_path = str(target_path)

    nsan = 0
    ntotal = 0

    new_solutions = []

    for solution in tqdm(load_solutions(samples)):
        task_id = solution["task_id"]
        dbg_identifier = solution["_identifier"]
        if debug_task is not None and task_id != debug_task:
            continue

        ntotal += 1
        if "solution" in solution:
            old_code = solution["solution"]
        else:
            assert "completion" in solution
            old_code = dataset[task_id]["prompt"] + "\n" + solution["completion"]

        old_code = old_code.strip()

        new_code = sanitize(
            old_code=old_code,
            entry_point=entry_point[task_id],
            rm_prefix_lines=rm_prefix_lines,
            eofs=eofs,
        ).strip()

        # if changed, print the message
        if new_code != old_code:
            msg = "Sanitized: " + dbg_identifier
            if is_folder:
                msg += " -> " + dbg_identifier.replace(samples, target_path)
            print(msg)
            nsan += 1

        new_solutions.append({"task_id": task_id, "solution": new_code})

    if is_folder:
        write_directory(target_path, new_solutions)
    else:
        write_jsonl(target_path, new_solutions)

    if nsan > 0:
        print(f"Sanitized {nsan} out of {ntotal} files.")
    else:
        print(f"All files seems valid -- no files are sanitized.")
    print(f"Check the sanitized files at {target_path}")


def main():
    from fire import Fire

    Fire(script)


if __name__ == "__main__":
    main()

# === NexusCore/evaluation\evalplus\tools\collect_valid_solutions.py ===
import ast
import json
import multiprocessing
import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List

import astor
import black
from tqdm import tqdm

from evalplus.data import (
    get_human_eval_plus,
    get_human_eval_plus_hash,
    get_mbpp_plus,
    get_mbpp_plus_hash,
)
from evalplus.eval import PASS
from evalplus.evalperf import check_solution
from evalplus.evaluate import get_groundtruth


def find_calls(source, functors, skip_main_fn=True):
    class FunctorVisitor(ast.NodeVisitor):
        def __init__(self, target_functors):
            super().__init__()
            self.target_functors = target_functors
            self._temp_found_functors = set()
            self.results = []

        def visit_FunctionDef(self, node):
            self.current_function = node.name
            self._temp_found_functors = set()
            self.generic_visit(node)  # Continue traversing child nodes
            if self._temp_found_functors:
                self.results.append((self.current_function, self._temp_found_functors))

        # visit func def
        def visit_FunctionDef(self, node: ast.FunctionDef):
            if skip_main_fn and node.name == "main":
                return
            # visit child nodes
            self.generic_visit(node)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id in self.target_functors:
                self._temp_found_functors.add(node.func.id)
            self.generic_visit(node)

    tree = ast.parse(source)
    visitor = FunctorVisitor(target_functors=functors)
    visitor.visit(tree)
    return {caller: callee for caller, callee in visitor.results}


def void_calls(source, functors, skip_main_fn=True):
    changed = False

    class FunctorTransformer(ast.NodeTransformer):
        def __init__(self, target_functors):
            super().__init__()
            self.target_functors = target_functors

        # visit func def
        def visit_FunctionDef(self, node: ast.FunctionDef):
            if skip_main_fn and node.name == "main":
                return node
            # visit child nodes
            return self.generic_visit(node)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id in self.target_functors:
                nonlocal changed
                changed = True
                return ast.Expr(value=ast.Constant(value=None))
            return node

    tree = ast.parse(source)
    code = astor.to_source(FunctorTransformer(functors).visit(tree))
    fmt_code = black.format_str(code, mode=black.FileMode())
    return (fmt_code, changed)


def has_print_in_non_main_functions(source) -> bool:
    for caller, _ in find_calls(source, ["print"]).items():
        if caller != "main":
            return True
    return False


def gather_solutions(sample_path: str, task_id: str) -> List[str]:
    """Gather all solutions from the folders"""
    solutions = []
    for model in os.listdir(sample_path):
        model_path = os.path.join(sample_path, model)
        if not os.path.isdir(model_path):
            continue
        task_path = os.path.join(model_path, task_id)
        if os.path.isdir(task_path):
            for file in os.listdir(task_path):
                if file.endswith(".py"):
                    with open(os.path.join(task_path, file), "r") as f:
                        solutions.append(f.read())
    return solutions


def deduplicate(solutions: List[str]) -> List[str]:
    """Deduplicate solutions"""
    asts = set()
    deduplicated = []
    for solution in solutions:
        solution = re.sub(r"#[^\n]*", "", solution)
        solution = re.sub(r'"""[^"]*"""', "", solution)
        solution = re.sub(r"'''[^']*'''", "", solution)
        try:
            ast_string = ast.dump(ast.parse(solution))
        except SyntaxError:
            continue
        except MemoryError:
            continue
        if ast_string not in asts:
            asts.add(ast_string)
            deduplicated.append(solution)
    return list(deduplicated)


def test_solutions(
    dataset: str, solutions: List[str], task: Dict, expected_output: List
) -> List[str]:
    """Test solutions, return functionally correct solutions"""
    n_workers = max(1, multiprocessing.cpu_count() // 2)
    correct_solution_ids = []

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = [
            executor.submit(
                check_solution, index, solution, dataset, task, expected_output
            )
            for index, solution in enumerate(solutions)
        ]
        for future in as_completed(futures):
            index, result, _ = future.result()
            if result[0] == PASS:
                correct_solution_ids.append(index)

    return [solutions[i] for i in correct_solution_ids]


def script(sample_dir: str, dataset: str = "humaneval", debug_task: str = None):
    assert dataset in ["humaneval", "mbpp"]
    if dataset == "humaneval":
        problems = get_human_eval_plus(noextreme=True)
        dataset_hash = get_human_eval_plus_hash(noextreme=True)
        expected_output = get_groundtruth(problems, dataset_hash, [])
    elif dataset == "mbpp":
        from evalplus.eval._special_oracle import MBPP_OUTPUT_NOT_NONE_TASKS

        problems = get_mbpp_plus(noextreme=True)
        dataset_hash = get_mbpp_plus_hash(noextreme=True)
        expected_output = get_groundtruth(
            problems,
            dataset_hash,
            MBPP_OUTPUT_NOT_NONE_TASKS,
        )

    previous_solutions = None

    for task_id, task in tqdm(problems.items()):
        if debug_task and task_id != debug_task:
            continue
        solutions = gather_solutions(sample_dir, task_id.replace("/", "_"))
        solutions = deduplicate(solutions)
        correct_solutions = test_solutions(
            dataset, solutions, task, expected_output[task_id]
        )

        # clean solutions to remove print statements and format it
        correct_solutions = [
            void_calls(solution, ["print"])[0] for solution in correct_solutions
        ]

        # Assuming that the previous solutions are correct
        if previous_solutions and task_id in previous_solutions:
            correct_solutions = deduplicate(
                correct_solutions + previous_solutions[task_id]
            )
        with open("solutions.jsonl", "a+") as f:
            f.write(
                json.dumps({"task_id": task_id, "solution": correct_solutions}) + "\n"
            )


def main():
    from fire import Fire

    Fire(script)


if __name__ == "__main__":
    main()

# === NexusCore/myenv\Lib\site-packages\pip\_internal\commands\debug.py ===
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

# === NexusCore/openenv\Lib\site-packages\numpy\_pytesttester.py ===
"""
Pytest test running.

This module implements the ``test()`` function for NumPy modules. The usual
boiler plate for doing that is to put the following in the module
``__init__.py`` file::

    from numpy._pytesttester import PytestTester
    test = PytestTester(__name__)
    del PytestTester


Warnings filtering and other runtime settings should be dealt with in the
``pytest.ini`` file in the numpy repo root. The behavior of the test depends on
whether or not that file is found as follows:

* ``pytest.ini`` is present (develop mode)
    All warnings except those explicitly filtered out are raised as error.
* ``pytest.ini`` is absent (release mode)
    DeprecationWarnings and PendingDeprecationWarnings are ignored, other
    warnings are passed through.

In practice, tests run from the numpy repo are run in development mode with
``spin``, through the standard ``spin test`` invocation or from an inplace
build with ``pytest numpy``.

This module is imported by every numpy subpackage, so lies at the top level to
simplify circular import issues. For the same reason, it contains no numpy
imports at module scope, instead importing numpy within function calls.
"""
import os
import sys

__all__ = ['PytestTester']


def _show_numpy_info():
    import numpy as np

    print(f"NumPy version {np.__version__}")
    info = np.lib._utils_impl._opt_info()
    print("NumPy CPU features: ", (info or 'nothing enabled'))


class PytestTester:
    """
    Pytest test runner.

    A test function is typically added to a package's __init__.py like so::

      from numpy._pytesttester import PytestTester
      test = PytestTester(__name__).test
      del PytestTester

    Calling this test function finds and runs all tests associated with the
    module and all its sub-modules.

    Attributes
    ----------
    module_name : str
        Full path to the package to test.

    Parameters
    ----------
    module_name : module name
        The name of the module to test.

    Notes
    -----
    Unlike the previous ``nose``-based implementation, this class is not
    publicly exposed as it performs some ``numpy``-specific warning
    suppression.

    """
    def __init__(self, module_name):
        self.module_name = module_name
        self.__module__ = module_name

    def __call__(self, label='fast', verbose=1, extra_argv=None,
                 doctests=False, coverage=False, durations=-1, tests=None):
        """
        Run tests for module using pytest.

        Parameters
        ----------
        label : {'fast', 'full'}, optional
            Identifies the tests to run. When set to 'fast', tests decorated
            with `pytest.mark.slow` are skipped, when 'full', the slow marker
            is ignored.
        verbose : int, optional
            Verbosity value for test outputs, in the range 1-3. Default is 1.
        extra_argv : list, optional
            List with any extra arguments to pass to pytests.
        doctests : bool, optional
            .. note:: Not supported
        coverage : bool, optional
            If True, report coverage of NumPy code. Default is False.
            Requires installation of (pip) pytest-cov.
        durations : int, optional
            If < 0, do nothing, If 0, report time of all tests, if > 0,
            report the time of the slowest `timer` tests. Default is -1.
        tests : test or list of tests
            Tests to be executed with pytest '--pyargs'

        Returns
        -------
        result : bool
            Return True on success, false otherwise.

        Notes
        -----
        Each NumPy module exposes `test` in its namespace to run all tests for
        it. For example, to run all tests for numpy.lib:

        >>> np.lib.test() #doctest: +SKIP

        Examples
        --------
        >>> result = np.lib.test() #doctest: +SKIP
        ...
        1023 passed, 2 skipped, 6 deselected, 1 xfailed in 10.39 seconds
        >>> result
        True

        """
        import warnings

        import pytest

        module = sys.modules[self.module_name]
        module_path = os.path.abspath(module.__path__[0])

        # setup the pytest arguments
        pytest_args = ["-l"]

        # offset verbosity. The "-q" cancels a "-v".
        pytest_args += ["-q"]

        if sys.version_info < (3, 12):
            with warnings.catch_warnings():
                warnings.simplefilter("always")
                # Filter out distutils cpu warnings (could be localized to
                # distutils tests). ASV has problems with top level import,
                # so fetch module for suppression here.
                from numpy.distutils import cpuinfo  # noqa: F401

        # Filter out annoying import messages. Want these in both develop and
        # release mode.
        pytest_args += [
            "-W ignore:Not importing directory",
            "-W ignore:numpy.dtype size changed",
            "-W ignore:numpy.ufunc size changed",
            "-W ignore::UserWarning:cpuinfo",
            ]

        # When testing matrices, ignore their PendingDeprecationWarnings
        pytest_args += [
            "-W ignore:the matrix subclass is not",
            "-W ignore:Importing from numpy.matlib is",
            ]

        if doctests:
            pytest_args += ["--doctest-modules"]

        if extra_argv:
            pytest_args += list(extra_argv)

        if verbose > 1:
            pytest_args += ["-" + "v" * (verbose - 1)]

        if coverage:
            pytest_args += ["--cov=" + module_path]

        if label == "fast":
            # not importing at the top level to avoid circular import of module
            from numpy.testing import IS_PYPY
            if IS_PYPY:
                pytest_args += ["-m", "not slow and not slow_pypy"]
            else:
                pytest_args += ["-m", "not slow"]

        elif label != "full":
            pytest_args += ["-m", label]

        if durations >= 0:
            pytest_args += [f"--durations={durations}"]

        if tests is None:
            tests = [self.module_name]

        pytest_args += ["--pyargs"] + list(tests)

        # run tests.
        _show_numpy_info()

        try:
            code = pytest.main(pytest_args)
        except SystemExit as exc:
            code = exc.code

        return code == 0

# === NexusCore/openenv\Lib\site-packages\stack_data\serializing.py ===
import inspect
import logging
import sys
import traceback
from collections import Counter
from html import escape as escape_html
from types import FrameType, TracebackType
from typing import Union, Iterable, List

from stack_data import (
    style_with_executing_node,
    Options,
    Line,
    FrameInfo,
    Variable,
    RepeatedFrames,
)
from stack_data.utils import some_str

log = logging.getLogger(__name__)


class Serializer:
    def __init__(
        self,
        *,
        options=None,
        pygmented=False,
        show_executing_node=True,
        pygments_formatter_cls=None,
        pygments_formatter_kwargs=None,
        pygments_style="monokai",
        executing_node_modifier="bg:#005080",
        use_code_qualname=True,
        strip_leading_indent=True,
        html=False,
        chain=True,
        collapse_repeated_frames=True,
        show_variables=False,
    ):
        if options is None:
            options = Options()

        if pygmented and not options.pygments_formatter:
            if show_executing_node:
                pygments_style = style_with_executing_node(
                    pygments_style, executing_node_modifier
                )

            if pygments_formatter_cls is None:
                if html:
                    from pygments.formatters.html import (
                        HtmlFormatter as pygments_formatter_cls,
                    )
                else:
                    from pygments.formatters.terminal256 import (
                        Terminal256Formatter as pygments_formatter_cls,
                    )

            options.pygments_formatter = pygments_formatter_cls(
                style=pygments_style,
                **pygments_formatter_kwargs or {},
            )

        self.pygmented = pygmented
        self.use_code_qualname = use_code_qualname
        self.strip_leading_indent = strip_leading_indent
        self.html = html
        self.chain = chain
        self.options = options
        self.collapse_repeated_frames = collapse_repeated_frames
        self.show_variables = show_variables

    def format_exception(self, e=None) -> List[dict]:
        if e is None:
            e = sys.exc_info()[1]

        result = []

        if self.chain:
            if e.__cause__ is not None:
                result = self.format_exception(e.__cause__)
                result[-1]["tail"] = traceback._cause_message.strip()
            elif e.__context__ is not None and not e.__suppress_context__:
                result = self.format_exception(e.__context__)
                result[-1]["tail"] = traceback._context_message.strip()

        result.append(self.format_traceback_part(e))
        return result

    def format_traceback_part(self, e: BaseException) -> dict:
        return dict(
            frames=self.format_stack(e.__traceback__ or sys.exc_info()[2]),
            exception=dict(
                type=type(e).__name__,
                message=some_str(e),
            ),
            tail="",
        )

    def format_stack(self, frame_or_tb=None) -> List[dict]:
        if frame_or_tb is None:
            frame_or_tb = inspect.currentframe().f_back

        return list(
            self.format_stack_data(
                FrameInfo.stack_data(
                    frame_or_tb,
                    self.options,
                    collapse_repeated_frames=self.collapse_repeated_frames,
                )
            )
        )

    def format_stack_data(
        self, stack: Iterable[Union[FrameInfo, RepeatedFrames]]
    ) -> Iterable[dict]:
        for item in stack:
            if isinstance(item, FrameInfo):
                if not self.should_include_frame(item):
                    continue
                yield dict(type="frame", **self.format_frame(item))
            else:
                yield dict(type="repeated_frames", **self.format_repeated_frames(item))

    def format_repeated_frames(self, repeated_frames: RepeatedFrames) -> dict:
        counts = sorted(
            Counter(repeated_frames.frame_keys).items(),
            key=lambda item: (-item[1], item[0][0].co_name),
        )
        return dict(
            frames=[
                dict(
                    name=code.co_name,
                    lineno=lineno,
                    count=count,
                )
                for (code, lineno), count in counts
            ]
        )

    def format_frame(self, frame: Union[FrameInfo, FrameType, TracebackType]) -> dict:
        if not isinstance(frame, FrameInfo):
            frame = FrameInfo(frame, self.options)

        result = dict(
            name=(
                frame.executing.code_qualname()
                if self.use_code_qualname
                else frame.code.co_name
            ),
            filename=frame.filename,
            lineno=frame.lineno,
            lines=list(self.format_lines(frame.lines)),
        )
        if self.show_variables:
            result["variables"] = list(self.format_variables(frame))
        return result

    def format_lines(self, lines):
        for line in lines:
            if isinstance(line, Line):
                yield dict(type="line", **self.format_line(line))
            else:
                yield dict(type="line_gap")

    def format_line(self, line: Line) -> dict:
        return dict(
            is_current=line.is_current,
            lineno=line.lineno,
            text=line.render(
                pygmented=self.pygmented,
                escape_html=self.html,
                strip_leading_indent=self.strip_leading_indent,
            ),
        )

    def format_variables(self, frame_info: FrameInfo) -> Iterable[dict]:
        try:
            for var in sorted(frame_info.variables, key=lambda v: v.name):
                yield self.format_variable(var)
        except Exception:  # pragma: no cover
            log.exception("Error in getting frame variables")

    def format_variable(self, var: Variable) -> dict:
        return dict(
            name=self.format_variable_part(var.name),
            value=self.format_variable_part(self.format_variable_value(var.value)),
        )

    def format_variable_part(self, text):
        if self.html:
            return escape_html(text)
        else:
            return text

    def format_variable_value(self, value) -> str:
        return repr(value)

    def should_include_frame(self, frame_info: FrameInfo) -> bool:
        return True  # pragma: no cover