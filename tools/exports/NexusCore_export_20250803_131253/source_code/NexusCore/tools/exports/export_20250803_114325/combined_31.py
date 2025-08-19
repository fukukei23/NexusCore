
# === NexusCore/openenv\Lib\site-packages\openai\lib\streaming\chat\_events.py ===
from typing import List, Union, Generic, Optional
from typing_extensions import Literal

from ._types import ParsedChatCompletionSnapshot
from ...._models import BaseModel, GenericModel
from ..._parsing import ResponseFormatT
from ....types.chat import ChatCompletionChunk, ChatCompletionTokenLogprob


class ChunkEvent(BaseModel):
    type: Literal["chunk"]

    chunk: ChatCompletionChunk

    snapshot: ParsedChatCompletionSnapshot


class ContentDeltaEvent(BaseModel):
    """This event is yielded for every chunk with `choice.delta.content` data."""

    type: Literal["content.delta"]

    delta: str

    snapshot: str

    parsed: Optional[object] = None


class ContentDoneEvent(GenericModel, Generic[ResponseFormatT]):
    type: Literal["content.done"]

    content: str

    parsed: Optional[ResponseFormatT] = None


class RefusalDeltaEvent(BaseModel):
    type: Literal["refusal.delta"]

    delta: str

    snapshot: str


class RefusalDoneEvent(BaseModel):
    type: Literal["refusal.done"]

    refusal: str


class FunctionToolCallArgumentsDeltaEvent(BaseModel):
    type: Literal["tool_calls.function.arguments.delta"]

    name: str

    index: int

    arguments: str
    """Accumulated raw JSON string"""

    parsed_arguments: object
    """The parsed arguments so far"""

    arguments_delta: str
    """The JSON string delta"""


class FunctionToolCallArgumentsDoneEvent(BaseModel):
    type: Literal["tool_calls.function.arguments.done"]

    name: str

    index: int

    arguments: str
    """Accumulated raw JSON string"""

    parsed_arguments: object
    """The parsed arguments"""


class LogprobsContentDeltaEvent(BaseModel):
    type: Literal["logprobs.content.delta"]

    content: List[ChatCompletionTokenLogprob]

    snapshot: List[ChatCompletionTokenLogprob]


class LogprobsContentDoneEvent(BaseModel):
    type: Literal["logprobs.content.done"]

    content: List[ChatCompletionTokenLogprob]


class LogprobsRefusalDeltaEvent(BaseModel):
    type: Literal["logprobs.refusal.delta"]

    refusal: List[ChatCompletionTokenLogprob]

    snapshot: List[ChatCompletionTokenLogprob]


class LogprobsRefusalDoneEvent(BaseModel):
    type: Literal["logprobs.refusal.done"]

    refusal: List[ChatCompletionTokenLogprob]


ChatCompletionStreamEvent = Union[
    ChunkEvent,
    ContentDeltaEvent,
    ContentDoneEvent[ResponseFormatT],
    RefusalDeltaEvent,
    RefusalDoneEvent,
    FunctionToolCallArgumentsDeltaEvent,
    FunctionToolCallArgumentsDoneEvent,
    LogprobsContentDeltaEvent,
    LogprobsContentDoneEvent,
    LogprobsRefusalDeltaEvent,
    LogprobsRefusalDoneEvent,
]

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\prompt_templates\factory.py ===
import copy
import json
import re
import uuid
import xml.etree.ElementTree as ET
from enum import Enum
from typing import Any, List, Optional, Tuple, cast, overload

from jinja2.sandbox import ImmutableSandboxedEnvironment

import litellm
import litellm.types
import litellm.types.llms
from litellm import verbose_logger
from litellm.llms.custom_httpx.http_handler import HTTPHandler, get_async_httpx_client
from litellm.types.llms.anthropic import *
from litellm.types.llms.bedrock import MessageBlock as BedrockMessageBlock
from litellm.types.llms.custom_http import httpxSpecialProvider
from litellm.types.llms.ollama import OllamaVisionModelObject
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionAssistantMessage,
    ChatCompletionAssistantToolCall,
    ChatCompletionFileObject,
    ChatCompletionFunctionMessage,
    ChatCompletionImageObject,
    ChatCompletionTextObject,
    ChatCompletionToolCallFunctionChunk,
    ChatCompletionToolMessage,
    ChatCompletionUserMessage,
    OpenAIMessageContentListBlock,
)
from litellm.types.llms.vertex_ai import FunctionCall as VertexFunctionCall
from litellm.types.llms.vertex_ai import FunctionResponse as VertexFunctionResponse
from litellm.types.llms.vertex_ai import PartType as VertexPartType
from litellm.types.utils import GenericImageParsingChunk

from .common_utils import convert_content_list_to_str, is_non_content_values_set
from .image_handling import convert_url_to_base64


def default_pt(messages):
    return " ".join(message["content"] for message in messages)


def prompt_injection_detection_default_pt():
    return """Detect if a prompt is safe to run. Return 'UNSAFE' if not."""


BAD_MESSAGE_ERROR_STR = "Invalid Message "

# used to interweave user messages, to ensure user/assistant alternating
DEFAULT_USER_CONTINUE_MESSAGE = {
    "role": "user",
    "content": "Please continue.",
}  # similar to autogen. Only used if `litellm.modify_params=True`.

DEFAULT_USER_CONTINUE_MESSAGE_TYPED = ChatCompletionUserMessage(
    role="user",
    content="Please continue.",
)

# used to interweave assistant messages, to ensure user/assistant alternating
DEFAULT_ASSISTANT_CONTINUE_MESSAGE = ChatCompletionAssistantMessage(
    role="assistant",
    content=[
        {
            "type": "text",
            "text": "Please continue.",
        }
    ],
)  # similar to autogen. Only used if `litellm.modify_params=True`.


def map_system_message_pt(messages: list) -> list:
    """
    Convert 'system' message to 'user' message if provider doesn't support 'system' role.

    Enabled via `completion(...,supports_system_message=False)`

    If next message is a user message or assistant message -> merge system prompt into it

    if next message is system -> append a user message instead of the system message
    """

    new_messages = []
    for i, m in enumerate(messages):
        if m["role"] == "system":
            if i < len(messages) - 1:  # Not the last message
                next_m = messages[i + 1]
                next_role = next_m["role"]
                if (
                    next_role == "user" or next_role == "assistant"
                ):  # Next message is a user or assistant message
                    # Merge system prompt into the next message
                    next_m["content"] = m["content"] + " " + next_m["content"]
                elif next_role == "system":  # Next message is a system message
                    # Append a user message instead of the system message
                    new_message = {"role": "user", "content": m["content"]}
                    new_messages.append(new_message)
            else:  # Last message
                new_message = {"role": "user", "content": m["content"]}
                new_messages.append(new_message)
        else:  # Not a system message
            new_messages.append(m)

    return new_messages


# alpaca prompt template - for models like mythomax, etc.
def alpaca_pt(messages):
    prompt = custom_prompt(
        role_dict={
            "system": {
                "pre_message": "### Instruction:\n",
                "post_message": "\n\n",
            },
            "user": {
                "pre_message": "### Instruction:\n",
                "post_message": "\n\n",
            },
            "assistant": {"pre_message": "### Response:\n", "post_message": "\n\n"},
        },
        bos_token="<s>",
        eos_token="</s>",
        messages=messages,
    )
    return prompt


# Llama2 prompt template
def llama_2_chat_pt(messages):
    prompt = custom_prompt(
        role_dict={
            "system": {
                "pre_message": "[INST] <<SYS>>\n",
                "post_message": "\n<</SYS>>\n [/INST]\n",
            },
            "user": {  # follow this format https://github.com/facebookresearch/llama/blob/77062717054710e352a99add63d160274ce670c6/llama/generation.py#L348
                "pre_message": "[INST] ",
                "post_message": " [/INST]\n",
            },
            "assistant": {
                "post_message": "\n"  # follows this - https://replicate.com/blog/how-to-prompt-llama
            },
        },
        messages=messages,
        bos_token="<s>",
        eos_token="</s>",
    )
    return prompt


def convert_to_ollama_image(openai_image_url: str):
    try:
        if openai_image_url.startswith("http"):
            openai_image_url = convert_url_to_base64(url=openai_image_url)

        if openai_image_url.startswith("data:image/"):
            # Extract the base64 image data
            base64_data = openai_image_url.split("data:image/")[1].split(";base64,")[1]
        else:
            base64_data = openai_image_url

        return base64_data
    except Exception as e:
        if "Error: Unable to fetch image from URL" in str(e):
            raise e
        raise Exception(
            """Image url not in expected format. Example Expected input - "image_url": "data:image/jpeg;base64,{base64_image}". """
        )


def _handle_ollama_system_message(
    messages: list, prompt: str, msg_i: int
) -> Tuple[str, int]:
    system_content_str = ""
    ## MERGE CONSECUTIVE SYSTEM CONTENT ##
    while msg_i < len(messages) and messages[msg_i]["role"] == "system":
        msg_content = convert_content_list_to_str(messages[msg_i])
        system_content_str += msg_content

        msg_i += 1

    return system_content_str, msg_i


def ollama_pt(
    model: str, messages: list
) -> Union[
    str, OllamaVisionModelObject
]:  # https://github.com/ollama/ollama/blob/af4cf55884ac54b9e637cd71dadfe9b7a5685877/docs/modelfile.md#template
    user_message_types = {"user", "tool", "function"}
    msg_i = 0
    images = []
    prompt = ""
    while msg_i < len(messages):
        init_msg_i = msg_i
        user_content_str = ""
        ## MERGE CONSECUTIVE USER CONTENT ##
        while msg_i < len(messages) and messages[msg_i]["role"] in user_message_types:
            msg_content = messages[msg_i].get("content")
            if msg_content:
                if isinstance(msg_content, list):
                    for m in msg_content:
                        if m.get("type", "") == "image_url":
                            if isinstance(m["image_url"], str):
                                images.append(m["image_url"])
                            elif isinstance(m["image_url"], dict):
                                images.append(m["image_url"]["url"])
                        elif m.get("type", "") == "text":
                            user_content_str += m["text"]
                else:
                    # Tool message content will always be a string
                    user_content_str += msg_content

            msg_i += 1

        if user_content_str:
            prompt += f"### User:\n{user_content_str}\n\n"

        system_content_str, msg_i = _handle_ollama_system_message(
            messages, prompt, msg_i
        )
        if system_content_str:
            prompt += f"### System:\n{system_content_str}\n\n"

        assistant_content_str = ""
        ## MERGE CONSECUTIVE ASSISTANT CONTENT ##
        while msg_i < len(messages) and messages[msg_i]["role"] == "assistant":
            assistant_content_str += convert_content_list_to_str(messages[msg_i])
            msg_i += 1

            tool_calls = messages[msg_i].get("tool_calls")
            ollama_tool_calls = []
            if tool_calls:
                for call in tool_calls:
                    call_id: str = call["id"]
                    function_name: str = call["function"]["name"]
                    arguments = json.loads(call["function"]["arguments"])

                    ollama_tool_calls.append(
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": function_name,
                                "arguments": arguments,
                            },
                        }
                    )

            if ollama_tool_calls:
                assistant_content_str += (
                    f"Tool Calls: {json.dumps(ollama_tool_calls, indent=2)}"
                )

                msg_i += 1

        if assistant_content_str:
            prompt += f"### Assistant:\n{assistant_content_str}\n\n"

        if msg_i == init_msg_i:  # prevent infinite loops
            raise litellm.BadRequestError(
                message=BAD_MESSAGE_ERROR_STR + f"passed in {messages[msg_i]}",
                model=model,
                llm_provider="ollama",
            )

    response_dict: OllamaVisionModelObject = {
        "prompt": prompt,
        "images": images,
    }

    return response_dict


def mistral_instruct_pt(messages):
    # Following the Mistral example's https://huggingface.co/docs/transformers/main/chat_templating
    prompt = custom_prompt(
        initial_prompt_value="<s>",
        role_dict={
            "system": {
                "pre_message": "[INST] \n",
                "post_message": " [/INST]\n",
            },
            "user": {"pre_message": "[INST] ", "post_message": " [/INST]\n"},
            "assistant": {"pre_message": " ", "post_message": "</s> "},
        },
        final_prompt_value="",
        messages=messages,
    )
    return prompt


# Falcon prompt template - from https://github.com/lm-sys/FastChat/blob/main/fastchat/conversation.py#L110
def falcon_instruct_pt(messages):
    prompt = ""
    for message in messages:
        if message["role"] == "system":
            prompt += message["content"]
        else:
            prompt += (
                message["role"]
                + ":"
                + message["content"].replace("\r\n", "\n").replace("\n\n", "\n")
            )
            prompt += "\n\n"

    return prompt


def falcon_chat_pt(messages):
    prompt = ""
    for message in messages:
        if message["role"] == "system":
            prompt += "System: " + message["content"]
        elif message["role"] == "assistant":
            prompt += "Falcon: " + message["content"]
        elif message["role"] == "user":
            prompt += "User: " + message["content"]

    return prompt


# MPT prompt template - from https://github.com/lm-sys/FastChat/blob/main/fastchat/conversation.py#L110
def mpt_chat_pt(messages):
    prompt = ""
    for message in messages:
        if message["role"] == "system":
            prompt += "<|im_start|>system" + message["content"] + "<|im_end|>" + "\n"
        elif message["role"] == "assistant":
            prompt += "<|im_start|>assistant" + message["content"] + "<|im_end|>" + "\n"
        elif message["role"] == "user":
            prompt += "<|im_start|>user" + message["content"] + "<|im_end|>" + "\n"
    return prompt


# WizardCoder prompt template - https://huggingface.co/WizardLM/WizardCoder-Python-34B-V1.0#prompt-format
def wizardcoder_pt(messages):
    prompt = ""
    for message in messages:
        if message["role"] == "system":
            prompt += message["content"] + "\n\n"
        elif message["role"] == "user":  # map to 'Instruction'
            prompt += "### Instruction:\n" + message["content"] + "\n\n"
        elif message["role"] == "assistant":  # map to 'Response'
            prompt += "### Response:\n" + message["content"] + "\n\n"
    return prompt


# Phind-CodeLlama prompt template - https://huggingface.co/Phind/Phind-CodeLlama-34B-v2#how-to-prompt-the-model
def phind_codellama_pt(messages):
    prompt = ""
    for message in messages:
        if message["role"] == "system":
            prompt += "### System Prompt\n" + message["content"] + "\n\n"
        elif message["role"] == "user":
            prompt += "### User Message\n" + message["content"] + "\n\n"
        elif message["role"] == "assistant":
            prompt += "### Assistant\n" + message["content"] + "\n\n"
    return prompt


def hf_chat_template(  # noqa: PLR0915
    model: str, messages: list, chat_template: Optional[Any] = None
):
    # Define Jinja2 environment
    env = ImmutableSandboxedEnvironment()

    def raise_exception(message):
        raise Exception(f"Error message - {message}")

    # Create a template object from the template text
    env.globals["raise_exception"] = raise_exception

    ## get the tokenizer config from huggingface
    bos_token = ""
    eos_token = ""
    if chat_template is None:

        def _get_tokenizer_config(hf_model_name):
            try:
                url = f"https://huggingface.co/{hf_model_name}/raw/main/tokenizer_config.json"
                # Make a GET request to fetch the JSON data
                client = HTTPHandler(concurrent_limit=1)

                response = client.get(url)
            except Exception as e:
                raise e
            if response.status_code == 200:
                # Parse the JSON data
                tokenizer_config = json.loads(response.content)
                return {"status": "success", "tokenizer": tokenizer_config}
            else:
                return {"status": "failure"}

        if model in litellm.known_tokenizer_config:
            tokenizer_config = litellm.known_tokenizer_config[model]
        else:
            tokenizer_config = _get_tokenizer_config(model)
            litellm.known_tokenizer_config.update({model: tokenizer_config})

        if (
            tokenizer_config["status"] == "failure"
            or "chat_template" not in tokenizer_config["tokenizer"]
        ):
            raise Exception("No chat template found")
        ## read the bos token, eos token and chat template from the json
        tokenizer_config = tokenizer_config["tokenizer"]  # type: ignore

        bos_token = tokenizer_config["bos_token"]  # type: ignore
        if bos_token is not None and not isinstance(bos_token, str):
            if isinstance(bos_token, dict):
                bos_token = bos_token.get("content", None)
        eos_token = tokenizer_config["eos_token"]  # type: ignore
        if eos_token is not None and not isinstance(eos_token, str):
            if isinstance(eos_token, dict):
                eos_token = eos_token.get("content", None)
        chat_template = tokenizer_config["chat_template"]  # type: ignore
    try:
        template = env.from_string(chat_template)  # type: ignore
    except Exception as e:
        raise e

    def _is_system_in_template():
        try:
            # Try rendering the template with a system message
            template.render(
                messages=[{"role": "system", "content": "test"}],
                eos_token="<eos>",
                bos_token="<bos>",
            )
            return True

        # This will be raised if Jinja attempts to render the system message and it can't
        except Exception:
            return False

    try:
        rendered_text = ""
        # Render the template with the provided values
        if _is_system_in_template():
            rendered_text = template.render(
                bos_token=bos_token,
                eos_token=eos_token,
                messages=messages,
                add_generation_prompt=True,
            )
        else:
            # treat a system message as a user message, if system not in template
            reformatted_messages = []
            try:
                for message in messages:
                    if message["role"] == "system":
                        reformatted_messages.append(
                            {"role": "user", "content": message["content"]}
                        )
                    else:
                        reformatted_messages.append(message)
                rendered_text = template.render(
                    bos_token=bos_token,
                    eos_token=eos_token,
                    messages=reformatted_messages,
                    add_generation_prompt=True,
                )
            except Exception as e:
                if "Conversation roles must alternate user/assistant" in str(e):
                    # reformat messages to ensure user/assistant are alternating, if there's either 2 consecutive 'user' messages or 2 consecutive 'assistant' message, add a blank 'user' or 'assistant' message to ensure compatibility
                    new_messages = []
                    for i in range(len(reformatted_messages) - 1):
                        new_messages.append(reformatted_messages[i])
                        if (
                            reformatted_messages[i]["role"]
                            == reformatted_messages[i + 1]["role"]
                        ):
                            if reformatted_messages[i]["role"] == "user":
                                new_messages.append(
                                    {"role": "assistant", "content": ""}
                                )
                            else:
                                new_messages.append({"role": "user", "content": ""})
                    new_messages.append(reformatted_messages[-1])
                    rendered_text = template.render(
                        bos_token=bos_token, eos_token=eos_token, messages=new_messages
                    )

        return rendered_text
    except Exception as e:
        raise Exception(
            f"Error rendering template - {str(e)}"
        )  # don't use verbose_logger.exception, if exception is raised


def deepseek_r1_pt(messages):
    return hf_chat_template(
        model="deepseek-r1/deepseek-r1-7b-instruct", messages=messages
    )


# Anthropic template
def claude_2_1_pt(
    messages: list,
):  # format - https://docs.anthropic.com/claude/docs/how-to-use-system-prompts
    """
    Claude v2.1 allows system prompts (no Human: needed), but requires it be followed by Human:
    - you can't just pass a system message
    - you can't pass a system message and follow that with an assistant message
    if system message is passed in, you can only do system, human, assistant or system, human

    if a system message is passed in and followed by an assistant message, insert a blank human message between them.

    Additionally, you can "put words in Claude's mouth" by ending with an assistant message.
    See: https://docs.anthropic.com/claude/docs/put-words-in-claudes-mouth
    """

    class AnthropicConstants(Enum):
        HUMAN_PROMPT = "\n\nHuman: "
        AI_PROMPT = "\n\nAssistant: "

    prompt = ""
    for idx, message in enumerate(messages):
        if message["role"] == "user":
            prompt += f"{AnthropicConstants.HUMAN_PROMPT.value}{message['content']}"
        elif message["role"] == "system":
            prompt += f"{message['content']}"
        elif message["role"] == "assistant":
            if idx > 0 and messages[idx - 1]["role"] == "system":
                prompt += f"{AnthropicConstants.HUMAN_PROMPT.value}"  # Insert a blank human message
            prompt += f"{AnthropicConstants.AI_PROMPT.value}{message['content']}"
    if messages[-1]["role"] != "assistant":
        prompt += f"{AnthropicConstants.AI_PROMPT.value}"  # prompt must end with \"\n\nAssistant: " turn
    return prompt


### TOGETHER AI


def get_model_info(token, model):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        client = HTTPHandler(concurrent_limit=1)
        response = client.get("https://api.together.xyz/models/info", headers=headers)
        if response.status_code == 200:
            model_info = response.json()
            for m in model_info:
                if m["name"].lower().strip() == model.strip():
                    return m["config"].get("prompt_format", None), m["config"].get(
                        "chat_template", None
                    )
            return None, None
        else:
            return None, None
    except Exception:  # safely fail a prompt template request
        return None, None


## OLD TOGETHER AI FLOW
# def format_prompt_togetherai(messages, prompt_format, chat_template):
#     if prompt_format is None:
#         return default_pt(messages)

#     human_prompt, assistant_prompt = prompt_format.split("{prompt}")

#     if chat_template is not None:
#         prompt = hf_chat_template(
#             model=None, messages=messages, chat_template=chat_template
#         )
#     elif prompt_format is not None:
#         prompt = custom_prompt(
#             role_dict={},
#             messages=messages,
#             initial_prompt_value=human_prompt,
#             final_prompt_value=assistant_prompt,
#         )
#     else:
#         prompt = default_pt(messages)
#     return prompt


### IBM Granite


def ibm_granite_pt(messages: list):
    """
    IBM's Granite models uses the template:
    <|system|> {system_message} <|user|> {user_message} <|assistant|> {assistant_message}

    See: https://www.ibm.com/docs/en/watsonx-as-a-service?topic=solutions-supported-foundation-models
    """
    return custom_prompt(
        messages=messages,
        role_dict={
            "system": {
                "pre_message": "<|system|>\n",
                "post_message": "\n",
            },
            "user": {
                "pre_message": "<|user|>\n",
                # Assistant tag is needed in the prompt after the user message
                # to avoid the model completing the users sentence before it answers
                # https://www.ibm.com/docs/en/watsonx/w-and-w/2.0.x?topic=models-granite-13b-chat-v2-prompting-tips#chat
                "post_message": "\n<|assistant|>\n",
            },
            "assistant": {
                "pre_message": "",
                "post_message": "\n",
            },
        },
    ).strip()


### ANTHROPIC ###


def anthropic_pt(
    messages: list,
):  # format - https://docs.anthropic.com/claude/reference/complete_post
    """
    You can "put words in Claude's mouth" by ending with an assistant message.
    See: https://docs.anthropic.com/claude/docs/put-words-in-claudes-mouth
    """

    class AnthropicConstants(Enum):
        HUMAN_PROMPT = "\n\nHuman: "
        AI_PROMPT = "\n\nAssistant: "

    prompt = ""
    for idx, message in enumerate(
        messages
    ):  # needs to start with `\n\nHuman: ` and end with `\n\nAssistant: `
        if message["role"] == "user":
            prompt += f"{AnthropicConstants.HUMAN_PROMPT.value}{message['content']}"
        elif message["role"] == "system":
            prompt += f"{AnthropicConstants.HUMAN_PROMPT.value}<admin>{message['content']}</admin>"
        else:
            prompt += f"{AnthropicConstants.AI_PROMPT.value}{message['content']}"
        if (
            idx == 0 and message["role"] == "assistant"
        ):  # ensure the prompt always starts with `\n\nHuman: `
            prompt = f"{AnthropicConstants.HUMAN_PROMPT.value}" + prompt
    if messages[-1]["role"] != "assistant":
        prompt += f"{AnthropicConstants.AI_PROMPT.value}"
    return prompt


def construct_format_parameters_prompt(parameters: dict):
    parameter_str = "<parameter>\n"
    for k, v in parameters.items():
        parameter_str += f"<{k}>"
        parameter_str += f"{v}"
        parameter_str += f"</{k}>"
    parameter_str += "\n</parameter>"
    return parameter_str


def construct_format_tool_for_claude_prompt(name, description, parameters):
    constructed_prompt = (
        "<tool_description>\n"
        f"<tool_name>{name}</tool_name>\n"
        "<description>\n"
        f"{description}\n"
        "</description>\n"
        "<parameters>\n"
        f"{construct_format_parameters_prompt(parameters)}\n"
        "</parameters>\n"
        "</tool_description>"
    )
    return constructed_prompt


def construct_tool_use_system_prompt(
    tools,
):  # from https://github.com/anthropics/anthropic-cookbook/blob/main/function_calling/function_calling.ipynb
    tool_str_list = []
    for tool in tools:
        tool_function = get_attribute_or_key(tool, "function")
        tool_str = construct_format_tool_for_claude_prompt(
            get_attribute_or_key(tool_function, "name"),
            get_attribute_or_key(tool_function, "description", ""),
            get_attribute_or_key(tool_function, "parameters", {}),
        )
        tool_str_list.append(tool_str)
    tool_use_system_prompt = (
        "In this environment you have access to a set of tools you can use to answer the user's question.\n"
        "\n"
        "You may call them like this:\n"
        "<function_calls>\n"
        "<invoke>\n"
        "<tool_name>$TOOL_NAME</tool_name>\n"
        "<parameters>\n"
        "<$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>\n"
        "...\n"
        "</parameters>\n"
        "</invoke>\n"
        "</function_calls>\n"
        "\n"
        "Here are the tools available:\n"
        "<tools>\n" + "\n".join([tool_str for tool_str in tool_str_list]) + "\n</tools>"
    )
    return tool_use_system_prompt


def convert_generic_image_chunk_to_openai_image_obj(
    image_chunk: GenericImageParsingChunk,
) -> str:
    """
    Convert a generic image chunk to an OpenAI image object.

    Input:
    GenericImageParsingChunk(
        type="base64",
        media_type="image/jpeg",
        data="...",
    )

    Return:
    "data:image/jpeg;base64,{base64_image}"
    """
    media_type = image_chunk["media_type"]
    return "data:{};{},{}".format(media_type, image_chunk["type"], image_chunk["data"])


def convert_to_anthropic_image_obj(
    openai_image_url: str, format: Optional[str]
) -> GenericImageParsingChunk:
    """
    Input:
    "image_url": "data:image/jpeg;base64,{base64_image}",

    Return:
    "source": {
      "type": "base64",
      "media_type": "image/jpeg",
      "data": {base64_image},
    }
    """
    try:
        if openai_image_url.startswith("http"):
            openai_image_url = convert_url_to_base64(url=openai_image_url)
        # Extract the media type and base64 data
        media_type, base64_data = openai_image_url.split("data:")[1].split(";base64,")

        if format:
            media_type = format
        else:
            media_type = media_type.replace("\\/", "/")

        return GenericImageParsingChunk(
            type="base64",
            media_type=media_type,
            data=base64_data,
        )
    except Exception as e:
        if "Error: Unable to fetch image from URL" in str(e):
            raise e
        raise Exception(
            """Image url not in expected format. Example Expected input - "image_url": "data:image/jpeg;base64,{base64_image}". Supported formats - ['image/jpeg', 'image/png', 'image/gif', 'image/webp']."""
        )


# The following XML functions will be deprecated once JSON schema support is available on Bedrock and Vertex
# ------------------------------------------------------------------------------
def convert_to_anthropic_tool_result_xml(message: dict) -> str:
    """
    OpenAI message with a tool result looks like:
    {
        "tool_call_id": "tool_1",
        "role": "tool",
        "name": "get_current_weather",
        "content": "function result goes here",
    },
    """

    """
    Anthropic tool_results look like:

    [Successful results]
    <function_results>
    <result>
    <tool_name>get_current_weather</tool_name>
    <stdout>
    function result goes here
    </stdout>
    </result>
    </function_results>

    [Error results]
    <function_results>
    <error>
    error message goes here
    </error>
    </function_results>
    """
    name = message.get("name")
    content = message.get("content", "")
    content = content.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")

    # We can't determine from openai message format whether it's a successful or
    # error call result so default to the successful result template
    anthropic_tool_result = (
        "<function_results>\n"
        "<result>\n"
        f"<tool_name>{name}</tool_name>\n"
        "<stdout>\n"
        f"{content}\n"
        "</stdout>\n"
        "</result>\n"
        "</function_results>"
    )

    return anthropic_tool_result


def convert_to_anthropic_tool_invoke_xml(tool_calls: list) -> str:
    invokes = ""
    for tool in tool_calls:
        if get_attribute_or_key(tool, "type") != "function":
            continue

        tool_function = get_attribute_or_key(tool, "function")
        tool_name = get_attribute_or_key(tool_function, "name")
        tool_arguments = get_attribute_or_key(tool_function, "arguments")
        parameters = "".join(
            f"<{param}>{val}</{param}>\n"
            for param, val in json.loads(tool_arguments).items()
        )
        invokes += (
            "<invoke>\n"
            f"<tool_name>{tool_name}</tool_name>\n"
            "<parameters>\n"
            f"{parameters}"
            "</parameters>\n"
            "</invoke>\n"
        )

    anthropic_tool_invoke = f"<function_calls>\n{invokes}</function_calls>"

    return anthropic_tool_invoke


def anthropic_messages_pt_xml(messages: list):
    """
    format messages for anthropic
    1. Anthropic supports roles like "user" and "assistant", (here litellm translates system-> assistant)
    2. The first message always needs to be of role "user"
    3. Each message must alternate between "user" and "assistant" (this is not addressed as now by litellm)
    4. final assistant content cannot end with trailing whitespace (anthropic raises an error otherwise)
    5. System messages are a separate param to the Messages API (used for tool calling)
    6. Ensure we only accept role, content. (message.name is not supported)
    """
    # add role=tool support to allow function call result/error submission
    user_message_types = {"user", "tool"}
    # reformat messages to ensure user/assistant are alternating, if there's either 2 consecutive 'user' messages or 2 consecutive 'assistant' message, merge them.
    new_messages = []
    msg_i = 0
    while msg_i < len(messages):
        user_content = []
        ## MERGE CONSECUTIVE USER CONTENT ##
        while msg_i < len(messages) and messages[msg_i]["role"] in user_message_types:
            if isinstance(messages[msg_i]["content"], list):
                for m in messages[msg_i]["content"]:
                    if m.get("type", "") == "image_url":
                        format = m["image_url"].get("format")
                        user_content.append(
                            {
                                "type": "image",
                                "source": convert_to_anthropic_image_obj(
                                    m["image_url"]["url"], format=format
                                ),
                            }
                        )
                    elif m.get("type", "") == "text":
                        user_content.append({"type": "text", "text": m["text"]})
            else:
                # Tool message content will always be a string
                user_content.append(
                    {
                        "type": "text",
                        "text": (
                            convert_to_anthropic_tool_result_xml(messages[msg_i])
                            if messages[msg_i]["role"] == "tool"
                            else messages[msg_i]["content"]
                        ),
                    }
                )

            msg_i += 1

        if user_content:
            new_messages.append({"role": "user", "content": user_content})

        assistant_content = []
        ## MERGE CONSECUTIVE ASSISTANT CONTENT ##
        while msg_i < len(messages) and messages[msg_i]["role"] == "assistant":
            assistant_text = (
                messages[msg_i].get("content") or ""
            )  # either string or none
            if messages[msg_i].get(
                "tool_calls", []
            ):  # support assistant tool invoke conversion
                assistant_text += convert_to_anthropic_tool_invoke_xml(  # type: ignore
                    messages[msg_i]["tool_calls"]
                )

            assistant_content.append({"type": "text", "text": assistant_text})
            msg_i += 1

        if assistant_content:
            new_messages.append({"role": "assistant", "content": assistant_content})

    if not new_messages or new_messages[0]["role"] != "user":
        if litellm.modify_params:
            new_messages.insert(
                0, {"role": "user", "content": [{"type": "text", "text": "."}]}
            )
        else:
            raise Exception(
                "Invalid first message. Should always start with 'role'='user' for Anthropic. System prompt is sent separately for Anthropic. set 'litellm.modify_params = True' or 'litellm_settings:modify_params = True' on proxy, to insert a placeholder user message - '.' as the first message, "
            )

    if new_messages[-1]["role"] == "assistant":
        for content in new_messages[-1]["content"]:
            if isinstance(content, dict) and content["type"] == "text":
                content["text"] = content[
                    "text"
                ].rstrip()  # no trailing whitespace for final assistant message

    return new_messages


# ------------------------------------------------------------------------------


def _azure_tool_call_invoke_helper(
    function_call_params: ChatCompletionToolCallFunctionChunk,
) -> Optional[ChatCompletionToolCallFunctionChunk]:
    """
    Azure requires 'arguments' to be a string.
    """
    if function_call_params.get("arguments") is None:
        function_call_params["arguments"] = ""
    return function_call_params


def convert_to_azure_openai_messages(
    messages: List[AllMessageValues],
) -> List[AllMessageValues]:
    for m in messages:
        if m["role"] == "assistant":
            function_call = m.get("function_call", None)
            if function_call is not None:
                m["function_call"] = _azure_tool_call_invoke_helper(function_call)
    return messages


# ------------------------------------------------------------------------------


def infer_protocol_value(
    value: Any,
) -> Literal[
    "string_value",
    "number_value",
    "bool_value",
    "struct_value",
    "list_value",
    "null_value",
    "unknown",
]:
    if value is None:
        return "null_value"
    if isinstance(value, int) or isinstance(value, float):
        return "number_value"
    if isinstance(value, str):
        return "string_value"
    if isinstance(value, bool):
        return "bool_value"
    if isinstance(value, dict):
        return "struct_value"
    if isinstance(value, list):
        return "list_value"

    return "unknown"


def _gemini_tool_call_invoke_helper(
    function_call_params: ChatCompletionToolCallFunctionChunk,
) -> Optional[VertexFunctionCall]:
    name = function_call_params.get("name", "") or ""
    arguments = function_call_params.get("arguments", "")
    if (
        isinstance(arguments, str) and len(arguments) == 0
    ):  # pass empty dict, if arguments is empty string - prevents call from failing
        arguments_dict = {
            "type": "object",
        }
    else:
        arguments_dict = json.loads(arguments)
    function_call = VertexFunctionCall(
        name=name,
        args=arguments_dict,
    )
    return function_call


def convert_to_gemini_tool_call_invoke(
    message: ChatCompletionAssistantMessage,
) -> List[VertexPartType]:
    """
    OpenAI tool invokes:
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "get_current_weather",
            "arguments": "{\n\"location\": \"Boston, MA\"\n}"
          }
        }
      ]
    },
    """
    """
    Gemini tool call invokes:
    {
      "role": "model",
      "parts": [
        {
          "functionCall": {
            "name": "get_current_weather",
            "args": {
              "unit": "fahrenheit",
              "predicted_temperature": 45,
              "location": "Boston, MA",
            }
          }
        }
      ]
    }
    """

    """
    - json.load the arguments
    """
    try:
        _parts_list: List[VertexPartType] = []
        tool_calls = message.get("tool_calls", None)
        function_call = message.get("function_call", None)
        if tool_calls is not None:
            for tool in tool_calls:
                if "function" in tool:
                    gemini_function_call: Optional[VertexFunctionCall] = (
                        _gemini_tool_call_invoke_helper(
                            function_call_params=tool["function"]
                        )
                    )
                    if gemini_function_call is not None:
                        _parts_list.append(
                            VertexPartType(function_call=gemini_function_call)
                        )
                    else:  # don't silently drop params. Make it clear to user what's happening.
                        raise Exception(
                            "function_call missing. Received tool call with 'type': 'function'. No function call in argument - {}".format(
                                tool
                            )
                        )
        elif function_call is not None:
            gemini_function_call = _gemini_tool_call_invoke_helper(
                function_call_params=function_call
            )
            if gemini_function_call is not None:
                _parts_list.append(VertexPartType(function_call=gemini_function_call))
            else:  # don't silently drop params. Make it clear to user what's happening.
                raise Exception(
                    "function_call missing. Received tool call with 'type': 'function'. No function call in argument - {}".format(
                        message
                    )
                )
        return _parts_list
    except Exception as e:
        raise Exception(
            "Unable to convert openai tool calls={} to gemini tool calls. Received error={}".format(
                message, str(e)
            )
        )


def convert_to_gemini_tool_call_result(
    message: Union[ChatCompletionToolMessage, ChatCompletionFunctionMessage],
    last_message_with_tool_calls: Optional[dict],
) -> VertexPartType:
    """
    OpenAI message with a tool result looks like:
    {
        "tool_call_id": "tool_1",
        "role": "tool",
        "content": "function result goes here",
    },

    # NOTE: Function messages have been deprecated
    OpenAI message with a function call result looks like:
    {
        "role": "function",
        "name": "get_current_weather",
        "content": "function result goes here",
    }
    """
    content_str: str = ""
    if isinstance(message["content"], str):
        content_str = message["content"]
    elif isinstance(message["content"], List):
        content_list = message["content"]
        for content in content_list:
            if content["type"] == "text":
                content_str += content["text"]
    name: Optional[str] = message.get("name", "")  # type: ignore

    # Recover name from last message with tool calls
    if last_message_with_tool_calls:
        tools = last_message_with_tool_calls.get("tool_calls", [])
        msg_tool_call_id = message.get("tool_call_id", None)
        for tool in tools:
            prev_tool_call_id = tool.get("id", None)
            if (
                msg_tool_call_id
                and prev_tool_call_id
                and msg_tool_call_id == prev_tool_call_id
            ):
                name = tool.get("function", {}).get("name", "")

    if not name:
        raise Exception(
            "Missing corresponding tool call for tool response message. Received - message={}, last_message_with_tool_calls={}".format(
                message, last_message_with_tool_calls
            )
        )

    # We can't determine from openai message format whether it's a successful or
    # error call result so default to the successful result template
    _function_response = VertexFunctionResponse(
        name=name, response={"content": content_str}  # type: ignore
    )

    _part = VertexPartType(function_response=_function_response)

    return _part


def convert_to_anthropic_tool_result(
    message: Union[ChatCompletionToolMessage, ChatCompletionFunctionMessage],
) -> AnthropicMessagesToolResultParam:
    """
    OpenAI message with a tool result looks like:
    {
        "tool_call_id": "tool_1",
        "role": "tool",
        "name": "get_current_weather",
        "content": "function result goes here",
    },

    OpenAI message with a function call result looks like:
    {
        "role": "function",
        "name": "get_current_weather",
        "content": "function result goes here",
    }
    """

    """
    Anthropic tool_results look like:
    {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_01A09q90qw90lq917835lq9",
                "content": "ConnectionError: the weather service API is not available (HTTP 500)",
                # "is_error": true
            }
        ]
    }
    """
    anthropic_content: Union[
        str,
        List[Union[AnthropicMessagesToolResultContent, AnthropicMessagesImageParam]],
    ] = ""
    if isinstance(message["content"], str):
        anthropic_content = message["content"]
    elif isinstance(message["content"], List):
        content_list = message["content"]
        anthropic_content_list: List[
            Union[AnthropicMessagesToolResultContent, AnthropicMessagesImageParam]
        ] = []
        for content in content_list:
            if content["type"] == "text":
                anthropic_content_list.append(
                    AnthropicMessagesToolResultContent(
                        type="text",
                        text=content["text"],
                    )
                )
            elif content["type"] == "image_url":
                if isinstance(content["image_url"], str):
                    image_chunk = convert_to_anthropic_image_obj(
                        content["image_url"], format=None
                    )
                else:
                    format = content["image_url"].get("format")
                    image_chunk = convert_to_anthropic_image_obj(
                        content["image_url"]["url"], format=format
                    )
                anthropic_content_list.append(
                    AnthropicMessagesImageParam(
                        type="image",
                        source=AnthropicContentParamSource(
                            type="base64",
                            media_type=image_chunk["media_type"],
                            data=image_chunk["data"],
                        ),
                    )
                )

        anthropic_content = anthropic_content_list
    anthropic_tool_result: Optional[AnthropicMessagesToolResultParam] = None
    ## PROMPT CACHING CHECK ##
    cache_control = message.get("cache_control", None)
    if message["role"] == "tool":
        tool_message: ChatCompletionToolMessage = message
        tool_call_id: str = tool_message["tool_call_id"]

        # We can't determine from openai message format whether it's a successful or
        # error call result so default to the successful result template
        anthropic_tool_result = AnthropicMessagesToolResultParam(
            type="tool_result", tool_use_id=tool_call_id, content=anthropic_content
        )

    if message["role"] == "function":
        function_message: ChatCompletionFunctionMessage = message
        tool_call_id = function_message.get("tool_call_id") or str(uuid.uuid4())
        anthropic_tool_result = AnthropicMessagesToolResultParam(
            type="tool_result", tool_use_id=tool_call_id, content=anthropic_content
        )

    if anthropic_tool_result is None:
        raise Exception(f"Unable to parse anthropic tool result for message: {message}")
    if cache_control is not None:
        anthropic_tool_result["cache_control"] = cache_control  # type: ignore
    return anthropic_tool_result


def convert_function_to_anthropic_tool_invoke(
    function_call: Union[dict, ChatCompletionToolCallFunctionChunk],
) -> List[AnthropicMessagesToolUseParam]:
    try:
        _name = get_attribute_or_key(function_call, "name") or ""
        _arguments = get_attribute_or_key(function_call, "arguments")
        anthropic_tool_invoke = [
            AnthropicMessagesToolUseParam(
                type="tool_use",
                id=str(uuid.uuid4()),
                name=_name,
                input=json.loads(_arguments) if _arguments else {},
            )
        ]
        return anthropic_tool_invoke
    except Exception as e:
        raise e


def convert_to_anthropic_tool_invoke(
    tool_calls: List[ChatCompletionAssistantToolCall],
) -> List[AnthropicMessagesToolUseParam]:
    """
    OpenAI tool invokes:
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "get_current_weather",
            "arguments": "{\n\"location\": \"Boston, MA\"\n}"
          }
        }
      ]
    },
    """

    """
    Anthropic tool invokes:
    {
      "role": "assistant",
      "content": [
        {
          "type": "text",
          "text": "<thinking>To answer this question, I will: 1. Use the get_weather tool to get the current weather in San Francisco. 2. Use the get_time tool to get the current time in the America/Los_Angeles timezone, which covers San Francisco, CA.</thinking>"
        },
        {
          "type": "tool_use",
          "id": "toolu_01A09q90qw90lq917835lq9",
          "name": "get_weather",
          "input": {"location": "San Francisco, CA"}
        }
      ]
    }
    """
    anthropic_tool_invoke = []

    for tool in tool_calls:
        if not get_attribute_or_key(tool, "type") == "function":
            continue

        _anthropic_tool_use_param = AnthropicMessagesToolUseParam(
            type="tool_use",
            id=cast(str, get_attribute_or_key(tool, "id")),
            name=cast(
                str,
                get_attribute_or_key(get_attribute_or_key(tool, "function"), "name"),
            ),
            input=json.loads(
                get_attribute_or_key(
                    get_attribute_or_key(tool, "function"), "arguments"
                )
            ),
        )

        _content_element = add_cache_control_to_content(
            anthropic_content_element=_anthropic_tool_use_param,
            orignal_content_element=dict(tool),
        )

        if "cache_control" in _content_element:
            _anthropic_tool_use_param["cache_control"] = _content_element[
                "cache_control"
            ]

        anthropic_tool_invoke.append(_anthropic_tool_use_param)

    return anthropic_tool_invoke


def add_cache_control_to_content(
    anthropic_content_element: Union[
        dict,
        AnthropicMessagesImageParam,
        AnthropicMessagesTextParam,
        AnthropicMessagesDocumentParam,
        AnthropicMessagesToolUseParam,
        ChatCompletionThinkingBlock,
    ],
    orignal_content_element: Union[dict, AllMessageValues],
):
    cache_control_param = orignal_content_element.get("cache_control")
    if cache_control_param is not None and isinstance(cache_control_param, dict):
        transformed_param = ChatCompletionCachedContent(**cache_control_param)  # type: ignore

        anthropic_content_element["cache_control"] = transformed_param

    return anthropic_content_element


def _anthropic_content_element_factory(
    image_chunk: GenericImageParsingChunk,
) -> Union[AnthropicMessagesImageParam, AnthropicMessagesDocumentParam]:
    if image_chunk["media_type"] == "application/pdf":
        _anthropic_content_element: Union[
            AnthropicMessagesDocumentParam, AnthropicMessagesImageParam
        ] = AnthropicMessagesDocumentParam(
            type="document",
            source=AnthropicContentParamSource(
                type="base64",
                media_type=image_chunk["media_type"],
                data=image_chunk["data"],
            ),
        )
    else:
        _anthropic_content_element = AnthropicMessagesImageParam(
            type="image",
            source=AnthropicContentParamSource(
                type="base64",
                media_type=image_chunk["media_type"],
                data=image_chunk["data"],
            ),
        )

    return _anthropic_content_element


def select_anthropic_content_block_type_for_file(
    format: str,
) -> Literal["document", "image", "container_upload"]:
    if format == "application/pdf" or format == "text/plain":
        return "document"
    elif format in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
        return "image"
    else:
        return "container_upload"


def anthropic_infer_file_id_content_type(
    file_id: str,
) -> Literal["document_url", "container_upload"]:
    """
    Use when 'format' not provided.

    - URL's - assume are document_url
    - Else - assume is container_upload
    """
    if file_id.startswith("http") or file_id.startswith("https"):
        return "document_url"
    else:
        return "container_upload"


def anthropic_process_openai_file_message(
    message: ChatCompletionFileObject,
) -> Union[
    AnthropicMessagesDocumentParam,
    AnthropicMessagesImageParam,
    AnthropicMessagesContainerUploadParam,
]:
    file_message = cast(ChatCompletionFileObject, message)
    file_data = file_message["file"].get("file_data")
    file_id = file_message["file"].get("file_id")
    format = file_message["file"].get("format")
    if file_data:
        image_chunk = convert_to_anthropic_image_obj(
            openai_image_url=file_data,
            format=format,
        )
        anthropic_document_param = AnthropicMessagesDocumentParam(
            type="document",
            source=AnthropicContentParamSource(
                type="base64",
                media_type=image_chunk["media_type"],
                data=image_chunk["data"],
            ),
        )
        return anthropic_document_param
    elif file_id:
        content_block_type = (
            select_anthropic_content_block_type_for_file(format)
            if format
            else anthropic_infer_file_id_content_type(file_id)
        )
        return_block_param: Optional[
            Union[
                AnthropicMessagesDocumentParam,
                AnthropicMessagesImageParam,
                AnthropicMessagesContainerUploadParam,
            ]
        ] = None
        if content_block_type == "document":
            return_block_param = AnthropicMessagesDocumentParam(
                type="document",
                source=AnthropicContentParamSourceFileId(
                    type="file",
                    file_id=file_id,
                ),
            )
        elif content_block_type == "document_url":
            return_block_param = AnthropicMessagesDocumentParam(
                type="document",
                source=AnthropicContentParamSourceUrl(
                    type="url",
                    url=file_id,
                ),
            )
        elif content_block_type == "image":
            return_block_param = AnthropicMessagesImageParam(
                type="image",
                source=AnthropicContentParamSourceFileId(
                    type="file",
                    file_id=file_id,
                ),
            )
        elif content_block_type == "container_upload":
            return_block_param = AnthropicMessagesContainerUploadParam(
                type="container_upload", file_id=file_id
            )

        if return_block_param is None:
            raise Exception(f"Unable to parse anthropic file message: {message}")
        return return_block_param
    raise Exception(
        f"Either file_data or file_id must be present in the file message: {message}"
    )


def anthropic_messages_pt(  # noqa: PLR0915
    messages: List[AllMessageValues],
    model: str,
    llm_provider: str,
) -> List[
    Union[
        AnthropicMessagesUserMessageParam,
        AnthopicMessagesAssistantMessageParam,
    ]
]:
    """
    format messages for anthropic
    1. Anthropic supports roles like "user" and "assistant" (system prompt sent separately)
    2. The first message always needs to be of role "user"
    3. Each message must alternate between "user" and "assistant" (this is not addressed as now by litellm)
    4. final assistant content cannot end with trailing whitespace (anthropic raises an error otherwise)
    5. System messages are a separate param to the Messages API
    6. Ensure we only accept role, content. (message.name is not supported)
    """
    # add role=tool support to allow function call result/error submission
    user_message_types = {"user", "tool", "function"}
    # reformat messages to ensure user/assistant are alternating, if there's either 2 consecutive 'user' messages or 2 consecutive 'assistant' message, merge them.
    new_messages: List[
        Union[
            AnthropicMessagesUserMessageParam,
            AnthopicMessagesAssistantMessageParam,
        ]
    ] = []

    if len(messages) == 0:
        if not litellm.modify_params:
            raise litellm.BadRequestError(
                message=f"Anthropic requires at least one non-system message. Either provide one, or set `litellm.modify_params = True` // `litellm_settings::modify_params: True` to add the dummy user message - {DEFAULT_USER_CONTINUE_MESSAGE_TYPED}.",
                model=model,
                llm_provider=llm_provider,
            )
        else:
            messages.append(DEFAULT_USER_CONTINUE_MESSAGE_TYPED)

    msg_i = 0
    while msg_i < len(messages):
        user_content: List[AnthropicMessagesUserMessageValues] = []
        init_msg_i = msg_i
        if isinstance(messages[msg_i], BaseModel):
            messages[msg_i] = dict(messages[msg_i])  # type: ignore
        ## MERGE CONSECUTIVE USER CONTENT ##
        while msg_i < len(messages) and messages[msg_i]["role"] in user_message_types:
            user_message_types_block: Union[
                ChatCompletionToolMessage,
                ChatCompletionUserMessage,
                ChatCompletionFunctionMessage,
            ] = messages[
                msg_i
            ]  # type: ignore
            if user_message_types_block["role"] == "user":
                if isinstance(user_message_types_block["content"], list):
                    for m in user_message_types_block["content"]:
                        if m.get("type", "") == "image_url":
                            m = cast(ChatCompletionImageObject, m)
                            format: Optional[str] = None
                            if isinstance(m["image_url"], str):
                                image_chunk = convert_to_anthropic_image_obj(
                                    openai_image_url=m["image_url"], format=None
                                )
                            else:
                                format = m["image_url"].get("format")
                                image_chunk = convert_to_anthropic_image_obj(
                                    openai_image_url=m["image_url"]["url"],
                                    format=format,
                                )

                            _anthropic_content_element = (
                                _anthropic_content_element_factory(image_chunk)
                            )
                            _content_element = add_cache_control_to_content(
                                anthropic_content_element=_anthropic_content_element,
                                orignal_content_element=dict(m),
                            )

                            if "cache_control" in _content_element:
                                _anthropic_content_element["cache_control"] = (
                                    _content_element["cache_control"]
                                )
                            user_content.append(_anthropic_content_element)
                        elif m.get("type", "") == "text":
                            m = cast(ChatCompletionTextObject, m)
                            _anthropic_text_content_element = (
                                AnthropicMessagesTextParam(
                                    type="text",
                                    text=m["text"],
                                )
                            )
                            _content_element = add_cache_control_to_content(
                                anthropic_content_element=_anthropic_text_content_element,
                                orignal_content_element=dict(m),
                            )
                            _content_element = cast(
                                AnthropicMessagesTextParam, _content_element
                            )

                            user_content.append(_content_element)
                        elif m.get("type", "") == "document":
                            user_content.append(cast(AnthropicMessagesDocumentParam, m))
                        elif m.get("type", "") == "file":
                            user_content.append(
                                anthropic_process_openai_file_message(
                                    cast(ChatCompletionFileObject, m)
                                )
                            )
                elif isinstance(user_message_types_block["content"], str):
                    _anthropic_content_text_element: AnthropicMessagesTextParam = {
                        "type": "text",
                        "text": user_message_types_block["content"],
                    }
                    _content_element = add_cache_control_to_content(
                        anthropic_content_element=_anthropic_content_text_element,
                        orignal_content_element=dict(user_message_types_block),
                    )

                    if "cache_control" in _content_element:
                        _anthropic_content_text_element["cache_control"] = (
                            _content_element["cache_control"]
                        )

                    user_content.append(_anthropic_content_text_element)

            elif (
                user_message_types_block["role"] == "tool"
                or user_message_types_block["role"] == "function"
            ):
                # OpenAI's tool message content will always be a string
                user_content.append(
                    convert_to_anthropic_tool_result(user_message_types_block)
                )

            msg_i += 1

        if user_content:
            new_messages.append({"role": "user", "content": user_content})

        assistant_content: List[AnthropicMessagesAssistantMessageValues] = []
        ## MERGE CONSECUTIVE ASSISTANT CONTENT ##
        while msg_i < len(messages) and messages[msg_i]["role"] == "assistant":
            assistant_content_block: ChatCompletionAssistantMessage = messages[msg_i]  # type: ignore

            thinking_blocks = assistant_content_block.get("thinking_blocks", None)
            if (
                thinking_blocks is not None
            ):  # IMPORTANT: ADD THIS FIRST, ELSE ANTHROPIC WILL RAISE AN ERROR
                assistant_content.extend(thinking_blocks)
            if "content" in assistant_content_block and isinstance(
                assistant_content_block["content"], list
            ):
                for m in assistant_content_block["content"]:
                    # handle thinking blocks
                    thinking_block = cast(str, m.get("thinking", ""))
                    text_block = cast(str, m.get("text", ""))
                    if (
                        m.get("type", "") == "thinking" and len(thinking_block) > 0
                    ):  # don't pass empty text blocks. anthropic api raises errors.
                        anthropic_message: Union[
                            ChatCompletionThinkingBlock,
                            AnthropicMessagesTextParam,
                        ] = cast(ChatCompletionThinkingBlock, m)
                        assistant_content.append(anthropic_message)
                    # handle text
                    elif (
                        m.get("type", "") == "text" and len(text_block) > 0
                    ):  # don't pass empty text blocks. anthropic api raises errors.
                        anthropic_message = AnthropicMessagesTextParam(
                            type="text", text=text_block
                        )
                        _cached_message = add_cache_control_to_content(
                            anthropic_content_element=anthropic_message,
                            orignal_content_element=dict(m),
                        )

                        assistant_content.append(
                            cast(AnthropicMessagesTextParam, _cached_message)
                        )
            elif (
                "content" in assistant_content_block
                and isinstance(assistant_content_block["content"], str)
                and assistant_content_block[
                    "content"
                ]  # don't pass empty text blocks. anthropic api raises errors.
            ):
                _anthropic_text_content_element = AnthropicMessagesTextParam(
                    type="text",
                    text=assistant_content_block["content"],
                )

                _content_element = add_cache_control_to_content(
                    anthropic_content_element=_anthropic_text_content_element,
                    orignal_content_element=dict(assistant_content_block),
                )

                if "cache_control" in _content_element:
                    _anthropic_text_content_element["cache_control"] = _content_element[
                        "cache_control"
                    ]

                assistant_content.append(_anthropic_text_content_element)

            assistant_tool_calls = assistant_content_block.get("tool_calls")
            if (
                assistant_tool_calls is not None
            ):  # support assistant tool invoke conversion
                assistant_content.extend(
                    convert_to_anthropic_tool_invoke(assistant_tool_calls)
                )

            assistant_function_call = assistant_content_block.get("function_call")

            if assistant_function_call is not None:
                assistant_content.extend(
                    convert_function_to_anthropic_tool_invoke(assistant_function_call)
                )

            msg_i += 1

        if assistant_content:
            new_messages.append({"role": "assistant", "content": assistant_content})

        if msg_i == init_msg_i:  # prevent infinite loops
            raise litellm.BadRequestError(
                message=BAD_MESSAGE_ERROR_STR + f"passed in {messages[msg_i]}",
                model=model,
                llm_provider=llm_provider,
            )

    if len(new_messages) > 0 and new_messages[-1]["role"] == "assistant":
        if isinstance(new_messages[-1]["content"], str):
            new_messages[-1]["content"] = new_messages[-1]["content"].rstrip()
        elif isinstance(new_messages[-1]["content"], list):
            for content in new_messages[-1]["content"]:
                if isinstance(content, dict) and content["type"] == "text":
                    content["text"] = content[
                        "text"
                    ].rstrip()  # no trailing whitespace for final assistant message

    return new_messages


def extract_between_tags(tag: str, string: str, strip: bool = False) -> List[str]:
    ext_list = re.findall(f"<{tag}>(.+?)</{tag}>", string, re.DOTALL)
    if strip:
        ext_list = [e.strip() for e in ext_list]
    return ext_list


def contains_tag(tag: str, string: str) -> bool:
    return bool(re.search(f"<{tag}>(.+?)</{tag}>", string, re.DOTALL))


def parse_xml_params(xml_content, json_schema: Optional[dict] = None):
    """
    Compare the xml output to the json schema

    check if a value is a list - if so, get it's child elements
    """
    root = ET.fromstring(xml_content)
    params = {}

    if json_schema is not None:  # check if we have a json schema for this function call
        # iterate over all properties in the schema
        for prop in json_schema["properties"]:
            # If property is an array, get the nested items
            _element = root.find(f"parameters/{prop}")
            if json_schema["properties"][prop]["type"] == "array":
                items = []
                if _element is not None:
                    for value in _element:
                        try:
                            if value.text is not None:
                                _value = json.loads(value.text)
                            else:
                                continue
                        except json.JSONDecodeError:
                            _value = value.text
                        items.append(_value)
                    params[prop] = items
            # If property is not an array, append the value directly
            elif _element is not None and _element.text is not None:
                try:
                    _value = json.loads(_element.text)
                except json.JSONDecodeError:
                    _value = _element.text
                params[prop] = _value
    else:
        for child in root.findall(".//parameters/*"):
            if child is not None and child.text is not None:
                try:
                    # Attempt to decode the element's text as JSON
                    params[child.tag] = json.loads(child.text)  # type: ignore
                except json.JSONDecodeError:
                    # If JSON decoding fails, use the original text
                    params[child.tag] = child.text  # type: ignore

    return params


### GEMINI HELPER FUNCTIONS ###


def get_system_prompt(messages):
    system_prompt_indices = []
    system_prompt = ""
    for idx, message in enumerate(messages):
        if message["role"] == "system":
            system_prompt += message["content"]
            system_prompt_indices.append(idx)
    if len(system_prompt_indices) > 0:
        for idx in reversed(system_prompt_indices):
            messages.pop(idx)
    return system_prompt, messages


from litellm.types.llms.cohere import (
    CallObject,
    ChatHistory,
    ChatHistoryChatBot,
    ChatHistorySystem,
    ChatHistoryToolResult,
    ChatHistoryUser,
    ToolCallObject,
    ToolResultObject,
)


def convert_openai_message_to_cohere_tool_result(
    message: Union[ChatCompletionToolMessage, ChatCompletionFunctionMessage],
    tool_calls: List,
) -> ToolResultObject:
    """
    OpenAI message with a tool result looks like:
    {
            "tool_call_id": "tool_1",
            "role": "tool",
            "content": {"location": "San Francisco, CA", "unit": "fahrenheit", "temperature": "72"},
    },
    """
    """
    OpenAI message with a function call looks like:
    {
        "role": "function",
        "name": "get_current_weather",
        "content": "function result goes here",
    }
    """

    """
    Cohere tool_results look like:
    {
       "call": {
           "name": "query_daily_sales_report",
           "parameters": {
               "day": "2023-09-29"
           },
       },
       "outputs": [
           {
               "date": "2023-09-29",
               "summary": "Total Sales Amount: 10000, Total Units Sold: 250"
           }
       ]
   },
    """

    content_str: str = ""
    if isinstance(message["content"], str):
        content_str = message["content"]
    elif isinstance(message["content"], List):
        content_list = message["content"]
        for content in content_list:
            if content["type"] == "text":
                content_str += content["text"]
    if len(content_str) > 0:
        try:
            content = json.loads(content_str)
        except json.JSONDecodeError:
            content = {"result": content_str}
    else:
        content = {}
    name = ""
    arguments = {}
    # Recover name from last message with tool calls
    if len(tool_calls) > 0:
        tools = tool_calls
        msg_tool_call_id = message.get("tool_call_id", None)
        for tool in tools:
            prev_tool_call_id = tool.get("id", None)
            if (
                msg_tool_call_id
                and prev_tool_call_id
                and msg_tool_call_id == prev_tool_call_id
            ):
                name = tool.get("function", {}).get("name", "")
                arguments_str = tool.get("function", {}).get("arguments", "")
                if arguments_str is not None and len(arguments_str) > 0:
                    arguments = json.loads(arguments_str)

    if message["role"] == "function":
        function_message: ChatCompletionFunctionMessage = message
        name = function_message["name"]
        cohere_tool_result: ToolResultObject = {
            "call": CallObject(name=name, parameters=arguments),
            "outputs": [content],
        }
        return cohere_tool_result
    else:
        # We can't determine from openai message format whether it's a successful or
        # error call result so default to the successful result template

        cohere_tool_result = {
            "call": CallObject(name=name, parameters=arguments),
            "outputs": [content],
        }
        return cohere_tool_result


def get_all_tool_calls(messages: List) -> List:
    """
    Returns extracted list of `tool_calls`.

    Done to handle openai no longer returning tool call 'name' in tool results.
    """
    tool_calls: List = []
    for m in messages:
        if m.get("tool_calls", None) is not None:
            if isinstance(m["tool_calls"], list):
                tool_calls.extend(m["tool_calls"])

    return tool_calls


def convert_to_cohere_tool_invoke(tool_calls: list) -> List[ToolCallObject]:
    """
    OpenAI tool invokes:
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "get_current_weather",
            "arguments": "{\n\"location\": \"Boston, MA\"\n}"
          }
        }
      ]
    },
    """

    """
    Cohere tool invokes:
    {
      "role": "CHATBOT",
      "tool_calls": [{"name": "get_weather", "parameters": {"location": "San Francisco, CA"}}]
    }
    """

    cohere_tool_invoke: List[ToolCallObject] = [
        {
            "name": get_attribute_or_key(
                get_attribute_or_key(tool, "function"), "name"
            ),
            "parameters": json.loads(
                get_attribute_or_key(
                    get_attribute_or_key(tool, "function"), "arguments"
                )
            ),
        }
        for tool in tool_calls
        if get_attribute_or_key(tool, "type") == "function"
    ]

    return cohere_tool_invoke


def cohere_messages_pt_v2(  # noqa: PLR0915
    messages: List,
    model: str,
    llm_provider: str,
) -> Tuple[Union[str, ToolResultObject], ChatHistory]:
    """
    Returns a tuple(Union[tool_result, message], chat_history)

    - if last message is tool result -> return 'tool_result'
    - if last message is text -> return message (str)

    - return preceding messages as 'chat_history'

    Note:
    - cannot specify message if the last entry in chat history contains tool results
    - message must be at least 1 token long or tool results must be specified.
    - cannot specify tool_results if the last entry in chat history contains a user message
    """
    tool_calls: List = get_all_tool_calls(messages=messages)

    ## GET MOST RECENT MESSAGE
    most_recent_message = messages.pop(-1)
    returned_message: Union[ToolResultObject, str] = ""
    if (
        most_recent_message.get("role", "") is not None
        and most_recent_message["role"] == "tool"
    ):
        # tool result
        returned_message = convert_openai_message_to_cohere_tool_result(
            most_recent_message, tool_calls
        )
    else:
        content: Union[str, List] = most_recent_message.get("content")
        if isinstance(content, str):
            returned_message = content
        else:
            for chunk in content:
                if chunk.get("type") == "text":
                    returned_message += chunk.get("text")

    ## CREATE CHAT HISTORY
    user_message_types = {"user"}
    tool_message_types = {"tool", "function"}
    # reformat messages to ensure user/assistant are alternating, if there's either 2 consecutive 'user' messages or 2 consecutive 'assistant' message, merge them.
    new_messages: ChatHistory = []
    msg_i = 0

    while msg_i < len(messages):
        user_content: str = ""
        init_msg_i = msg_i
        ## MERGE CONSECUTIVE USER CONTENT ##
        while msg_i < len(messages) and messages[msg_i]["role"] in user_message_types:
            if isinstance(messages[msg_i]["content"], list):
                for m in messages[msg_i]["content"]:
                    if m.get("type", "") == "text":
                        user_content += m["text"]
            else:
                user_content += messages[msg_i]["content"]
            msg_i += 1

        if len(user_content) > 0:
            new_messages.append(ChatHistoryUser(role="USER", message=user_content))

        system_content: str = ""
        ## MERGE CONSECUTIVE SYSTEM CONTENT ##
        while msg_i < len(messages) and messages[msg_i]["role"] == "system":
            if isinstance(messages[msg_i]["content"], list):
                for m in messages[msg_i]["content"]:
                    if m.get("type", "") == "text":
                        system_content += m["text"]
            else:
                system_content += messages[msg_i]["content"]
            msg_i += 1

        if len(system_content) > 0:
            new_messages.append(
                ChatHistorySystem(role="SYSTEM", message=system_content)
            )

        assistant_content: str = ""
        assistant_tool_calls: List[ToolCallObject] = []
        ## MERGE CONSECUTIVE ASSISTANT CONTENT ##
        while msg_i < len(messages) and messages[msg_i]["role"] == "assistant":
            if messages[msg_i].get("content", None) is not None and isinstance(
                messages[msg_i]["content"], list
            ):
                for m in messages[msg_i]["content"]:
                    if m.get("type", "") == "text":
                        assistant_content += m["text"]
            elif messages[msg_i].get("content") is not None and isinstance(
                messages[msg_i]["content"], str
            ):
                assistant_content += messages[msg_i]["content"]
            if messages[msg_i].get(
                "tool_calls", []
            ):  # support assistant tool invoke conversion
                assistant_tool_calls.extend(
                    convert_to_cohere_tool_invoke(messages[msg_i]["tool_calls"])
                )

            if messages[msg_i].get("function_call"):
                assistant_tool_calls.extend(
                    convert_to_cohere_tool_invoke(messages[msg_i]["function_call"])
                )

            msg_i += 1

        if len(assistant_content) > 0:
            new_messages.append(
                ChatHistoryChatBot(
                    role="CHATBOT",
                    message=assistant_content,
                    tool_calls=assistant_tool_calls,
                )
            )

        ## MERGE CONSECUTIVE TOOL RESULTS
        tool_results: List[ToolResultObject] = []
        while msg_i < len(messages) and messages[msg_i]["role"] in tool_message_types:
            tool_results.append(
                convert_openai_message_to_cohere_tool_result(
                    messages[msg_i], tool_calls
                )
            )

            msg_i += 1

        if len(tool_results) > 0:
            new_messages.append(
                ChatHistoryToolResult(role="TOOL", tool_results=tool_results)
            )

        if msg_i == init_msg_i:  # prevent infinite loops
            raise litellm.BadRequestError(
                message=BAD_MESSAGE_ERROR_STR + f"passed in {messages[msg_i]}",
                model=model,
                llm_provider=llm_provider,
            )

    return returned_message, new_messages


def cohere_message_pt(messages: list):
    tool_calls: List = get_all_tool_calls(messages=messages)
    prompt = ""
    tool_results = []
    for message in messages:
        # check if this is a tool_call result
        if message["role"] == "tool":
            tool_result = convert_openai_message_to_cohere_tool_result(
                message, tool_calls=tool_calls
            )
            tool_results.append(tool_result)
        elif message.get("content"):
            prompt += message["content"] + "\n\n"
    prompt = prompt.rstrip()
    return prompt, tool_results


def amazon_titan_pt(
    messages: list,
):  # format - https://github.com/BerriAI/litellm/issues/1896
    """
    Amazon Titan uses 'User:' and 'Bot: in it's prompt template
    """

    class AmazonTitanConstants(Enum):
        HUMAN_PROMPT = "\n\nUser: "  # Assuming this is similar to Anthropic prompt formatting, since amazon titan's prompt formatting is currently undocumented
        AI_PROMPT = "\n\nBot: "

    prompt = ""
    for idx, message in enumerate(messages):
        if message["role"] == "user":
            prompt += f"{AmazonTitanConstants.HUMAN_PROMPT.value}{message['content']}"
        elif message["role"] == "system":
            prompt += f"{AmazonTitanConstants.HUMAN_PROMPT.value}<admin>{message['content']}</admin>"
        else:
            prompt += f"{AmazonTitanConstants.AI_PROMPT.value}{message['content']}"
        if (
            idx == 0 and message["role"] == "assistant"
        ):  # ensure the prompt always starts with `\n\nHuman: `
            prompt = f"{AmazonTitanConstants.HUMAN_PROMPT.value}" + prompt
    if messages[-1]["role"] != "assistant":
        prompt += f"{AmazonTitanConstants.AI_PROMPT.value}"
    return prompt


def _load_image_from_url(image_url):
    try:
        from PIL import Image
    except Exception:
        raise Exception("image conversion failed please run `pip install Pillow`")
    from io import BytesIO

    try:
        # Send a GET request to the image URL
        client = HTTPHandler(concurrent_limit=1)
        response = client.get(image_url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Check the response's content type to ensure it is an image
        content_type = response.headers.get("content-type")
        if not content_type or "image" not in content_type:
            raise ValueError(
                f"URL does not point to a valid image (content-type: {content_type})"
            )

        # Load the image from the response content
        return Image.open(BytesIO(response.content))

    except Exception as e:
        raise e


def _gemini_vision_convert_messages(messages: list):
    """
    Converts given messages for GPT-4 Vision to Gemini format.

    Args:
        messages (list): The messages to convert. Each message can be a dictionary with a "content" key. The content can be a string or a list of elements. If it is a string, it will be concatenated to the prompt. If it is a list, each element will be processed based on its type:
            - If the element is a dictionary with a "type" key equal to "text", its "text" value will be concatenated to the prompt.
            - If the element is a dictionary with a "type" key equal to "image_url", its "image_url" value will be added to the list of images.

    Returns:
        tuple: A tuple containing the prompt (a string) and the processed images (a list of objects representing the images).
    """

    try:
        # given messages for gpt-4 vision, convert them for gemini
        # https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_gemini_python.ipynb
        prompt = ""
        images = []
        for message in messages:
            if isinstance(message["content"], str):
                prompt += message["content"]
            elif isinstance(message["content"], list):
                # see https://docs.litellm.ai/docs/providers/openai#openai-vision-models
                for element in message["content"]:
                    if isinstance(element, dict):
                        if element["type"] == "text":
                            prompt += element["text"]
                        elif element["type"] == "image_url":
                            image_url = element["image_url"]["url"]
                            images.append(image_url)
        # processing images passed to gemini
        processed_images = []
        for img in images:
            if "https:/" in img:
                # Case 1: Image from URL
                image = _load_image_from_url(img)
                processed_images.append(image)

            else:
                try:
                    from PIL import Image
                except Exception:
                    raise Exception(
                        "gemini image conversion failed please run `pip install Pillow`"
                    )

                if "base64" in img:
                    # Case 2: Base64 image data
                    import base64
                    import io

                    # Extract the base64 image data
                    base64_data = img.split("base64,")[1]

                    # Decode the base64 image data
                    image_data = base64.b64decode(base64_data)

                    # Load the image from the decoded data
                    image = Image.open(io.BytesIO(image_data))
                else:
                    # Case 3: Image filepath (e.g. temp.jpeg) given
                    image = Image.open(img)
                processed_images.append(image)
        content = [prompt] + processed_images
        return content
    except Exception as e:
        raise e


def gemini_text_image_pt(messages: list):
    """
    {
        "contents":[
            {
            "parts":[
                {"text": "What is this picture?"},
                {
                "inline_data": {
                    "mime_type":"image/jpeg",
                    "data": "'$(base64 -w0 image.jpg)'"
                }
                }
            ]
            }
        ]
    }
    """
    try:
        pass  # type: ignore
    except Exception:
        raise Exception(
            "Importing google.generativeai failed, please run 'pip install -q google-generativeai"
        )

    prompt = ""
    images = []
    for message in messages:
        if isinstance(message["content"], str):
            prompt += message["content"]
        elif isinstance(message["content"], list):
            # see https://docs.litellm.ai/docs/providers/openai#openai-vision-models
            for element in message["content"]:
                if isinstance(element, dict):
                    if element["type"] == "text":
                        prompt += element["text"]
                    elif element["type"] == "image_url":
                        image_url = element["image_url"]["url"]
                        images.append(image_url)

    content = [prompt] + images
    return content


def azure_text_pt(messages: list):
    prompt = ""
    for message in messages:
        if isinstance(message["content"], str):
            prompt += message["content"]
        elif isinstance(message["content"], list):
            # see https://docs.litellm.ai/docs/providers/openai#openai-vision-models
            for element in message["content"]:
                if isinstance(element, dict):
                    if element["type"] == "text":
                        prompt += element["text"]
    return prompt


###### AZURE AI #######
def stringify_json_tool_call_content(messages: List) -> List:
    """

    - Check 'content' in tool role -> convert to dict (if not) -> stringify

    Done for azure_ai/cohere calls to handle results of a tool call
    """

    for m in messages:
        if m["role"] == "tool" and isinstance(m["content"], str):
            # check if content is a valid json object
            try:
                json.loads(m["content"])
            except json.JSONDecodeError:
                m["content"] = json.dumps({"result": m["content"]})

    return messages


###### AMAZON BEDROCK #######

import base64
import mimetypes
from email.message import Message

import httpx

from litellm.types.llms.bedrock import (
    BedrockConverseReasoningContentBlock,
    BedrockConverseReasoningTextBlock,
)
from litellm.types.llms.bedrock import ContentBlock as BedrockContentBlock
from litellm.types.llms.bedrock import DocumentBlock as BedrockDocumentBlock
from litellm.types.llms.bedrock import ImageBlock as BedrockImageBlock
from litellm.types.llms.bedrock import SourceBlock as BedrockSourceBlock
from litellm.types.llms.bedrock import ToolBlock as BedrockToolBlock
from litellm.types.llms.bedrock import (
    ToolInputSchemaBlock as BedrockToolInputSchemaBlock,
)
from litellm.types.llms.bedrock import ToolJsonSchemaBlock as BedrockToolJsonSchemaBlock
from litellm.types.llms.bedrock import ToolResultBlock as BedrockToolResultBlock
from litellm.types.llms.bedrock import (
    ToolResultContentBlock as BedrockToolResultContentBlock,
)
from litellm.types.llms.bedrock import ToolSpecBlock as BedrockToolSpecBlock
from litellm.types.llms.bedrock import ToolUseBlock as BedrockToolUseBlock
from litellm.types.llms.bedrock import VideoBlock as BedrockVideoBlock


def _parse_content_type(content_type: str) -> str:
    m = Message()
    m["content-type"] = content_type
    return m.get_content_type()


def _parse_mime_type(base64_data: str) -> Optional[str]:
    mime_type_match = re.match(r"data:(.*?);base64", base64_data)
    if mime_type_match:
        return mime_type_match.group(1)
    else:
        return None


class BedrockImageProcessor:
    """Handles both sync and async image processing for Bedrock conversations."""

    @staticmethod
    def _post_call_image_processing(response: httpx.Response) -> Tuple[str, str]:
        # Check the response's content type to ensure it is an image
        content_type = response.headers.get("content-type")
        if not content_type:
            raise ValueError(
                f"URL does not contain content-type (content-type: {content_type})"
            )
        content_type = _parse_content_type(content_type)

        # Convert the image content to base64 bytes
        base64_bytes = base64.b64encode(response.content).decode("utf-8")

        return base64_bytes, content_type

    @staticmethod
    async def get_image_details_async(image_url) -> Tuple[str, str]:
        try:
            client = get_async_httpx_client(
                llm_provider=httpxSpecialProvider.PromptFactory,
                params={"concurrent_limit": 1},
            )
            # Send a GET request to the image URL
            response = await client.get(image_url, follow_redirects=True)
            response.raise_for_status()  # Raise an exception for HTTP errors

            return BedrockImageProcessor._post_call_image_processing(response)

        except Exception as e:
            raise e

    @staticmethod
    def get_image_details(image_url) -> Tuple[str, str]:
        try:
            client = HTTPHandler(concurrent_limit=1)
            # Send a GET request to the image URL
            response = client.get(image_url, follow_redirects=True)
            response.raise_for_status()  # Raise an exception for HTTP errors

            return BedrockImageProcessor._post_call_image_processing(response)

        except Exception as e:
            raise e

    @staticmethod
    def _parse_base64_image(image_url: str) -> Tuple[str, str, str]:
        """Parse base64 encoded image data."""
        image_metadata, img_without_base_64 = image_url.split(",")

        # Extract MIME type using regular expression
        mime_type_match = re.match(r"data:(.*?);base64", image_metadata)

        if mime_type_match:
            mime_type = mime_type_match.group(1)
            mime_type = mime_type.split(";")[0]
            image_format = mime_type.split("/")[1]
        else:
            mime_type = "image/jpeg"
            image_format = "jpeg"

        return img_without_base_64, mime_type, image_format

    @staticmethod
    def _validate_format(mime_type: str, image_format: str) -> str:
        """Validate image format and mime type for both images and documents."""

        supported_image_formats = (
            litellm.AmazonConverseConfig().get_supported_image_types()
        )
        supported_doc_formats = (
            litellm.AmazonConverseConfig().get_supported_document_types()
        )
        supported_video_formats = (
            litellm.AmazonConverseConfig().get_supported_video_types()
        )

        document_types = ["application", "text"]
        is_document = any(mime_type.startswith(doc_type) for doc_type in document_types)

        supported_image_and_video_formats: List[str] = (
            supported_video_formats + supported_image_formats
        )

        if is_document:
            potential_extensions = mimetypes.guess_all_extensions(mime_type)
            valid_extensions = [
                ext[1:]
                for ext in potential_extensions
                if ext[1:] in supported_doc_formats
            ]

            if not valid_extensions:
                raise ValueError(
                    f"No supported extensions for MIME type: {mime_type}. Supported formats: {supported_doc_formats}"
                )

            # Use first valid extension instead of provided image_format
            return valid_extensions[0]
        else:
            #########################################################
            # Check if image_format is an image or video
            #########################################################
            if image_format not in supported_image_and_video_formats:
                raise ValueError(
                    f"Unsupported image format: {image_format}. Supported formats: {supported_image_and_video_formats}"
                )
            return image_format

    @staticmethod
    def _create_bedrock_block(
        image_bytes: str, mime_type: str, image_format: str
    ) -> BedrockContentBlock:
        """Create appropriate Bedrock content block based on mime type."""
        _blob = BedrockSourceBlock(bytes=image_bytes)

        document_types = ["application", "text"]
        is_document = any(mime_type.startswith(doc_type) for doc_type in document_types)

        supported_video_formats = (
            litellm.AmazonConverseConfig().get_supported_video_types()
        )
        is_video = any(
            image_format.startswith(video_type)
            for video_type in supported_video_formats
        )

        if is_document:
            return BedrockContentBlock(
                document=BedrockDocumentBlock(
                    source=_blob,
                    format=image_format,
                    name=f"DocumentPDFmessages_{str(uuid.uuid4())}",
                )
            )
        elif is_video:
            return BedrockContentBlock(
                video=BedrockVideoBlock(source=_blob, format=image_format)
            )
        else:
            return BedrockContentBlock(
                image=BedrockImageBlock(source=_blob, format=image_format)
            )

    @classmethod
    def process_image_sync(
        cls, image_url: str, format: Optional[str] = None
    ) -> BedrockContentBlock:
        """Synchronous image processing."""

        if "base64" in image_url:
            img_bytes, mime_type, image_format = cls._parse_base64_image(image_url)
        elif "http://" in image_url or "https://" in image_url:
            img_bytes, mime_type = BedrockImageProcessor.get_image_details(image_url)
            image_format = mime_type.split("/")[1]
        else:
            raise ValueError(
                "Unsupported image type. Expected either image url or base64 encoded string"
            )

        if format:
            mime_type = format
            image_format = mime_type.split("/")[1]

        image_format = cls._validate_format(mime_type, image_format)
        return cls._create_bedrock_block(img_bytes, mime_type, image_format)

    @classmethod
    async def process_image_async(
        cls, image_url: str, format: Optional[str]
    ) -> BedrockContentBlock:
        """Asynchronous image processing."""

        if "base64" in image_url:
            img_bytes, mime_type, image_format = cls._parse_base64_image(image_url)
        elif "http://" in image_url or "https://" in image_url:
            img_bytes, mime_type = await BedrockImageProcessor.get_image_details_async(
                image_url
            )
            image_format = mime_type.split("/")[1]
        else:
            raise ValueError(
                "Unsupported image type. Expected either image url or base64 encoded string"
            )

        if format:  # override with user-defined params
            mime_type = format
            image_format = mime_type.split("/")[1]

        image_format = cls._validate_format(mime_type, image_format)
        return cls._create_bedrock_block(img_bytes, mime_type, image_format)


def _convert_to_bedrock_tool_call_invoke(
    tool_calls: list,
) -> List[BedrockContentBlock]:
    """
    OpenAI tool invokes:
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "get_current_weather",
            "arguments": "{\n\"location\": \"Boston, MA\"\n}"
          }
        }
      ]
    },
    """
    """
    Bedrock tool invokes: 
    [   
        {
            "role": "assistant",
            "toolUse": {
                "input": {"location": "Boston, MA", ..},
                "name": "get_current_weather",
                "toolUseId": "call_abc123"
            }
        }
    ]
    """
    """
    - json.loads argument
    - extract name 
    - extract id
    """

    try:
        _parts_list: List[BedrockContentBlock] = []
        for tool in tool_calls:
            if "function" in tool:
                id = tool["id"]
                name = tool["function"].get("name", "")
                arguments = tool["function"].get("arguments", "")
                arguments_dict = json.loads(arguments)
                bedrock_tool = BedrockToolUseBlock(
                    input=arguments_dict, name=name, toolUseId=id
                )
                bedrock_content_block = BedrockContentBlock(toolUse=bedrock_tool)
                _parts_list.append(bedrock_content_block)
        return _parts_list
    except Exception as e:
        raise Exception(
            "Unable to convert openai tool calls={} to bedrock tool calls. Received error={}".format(
                tool_calls, str(e)
            )
        )


def _convert_to_bedrock_tool_call_result(
    message: Union[ChatCompletionToolMessage, ChatCompletionFunctionMessage],
) -> BedrockContentBlock:
    """
    OpenAI message with a tool result looks like:
    {
        "tool_call_id": "tool_1",
        "role": "tool",
        "name": "get_current_weather",
        "content": "function result goes here",
    },

    OpenAI message with a function call result looks like:
    {
        "role": "function",
        "name": "get_current_weather",
        "content": "function result goes here",
    }
    """
    """
    Bedrock result looks like this: 
    {
        "role": "user",
        "content": [
            {
                "toolResult": {
                    "toolUseId": "tooluse_kZJMlvQmRJ6eAyJE5GIl7Q",
                    "content": [
                        {
                            "json": {
                                "song": "Elemental Hotel",
                                "artist": "8 Storey Hike"
                            }
                        }
                    ]
                }
            }
        ]
    }
    """
    """
    - 
    """
    content_str: str = ""
    if isinstance(message["content"], str):
        content_str = message["content"]
    elif isinstance(message["content"], List):
        content_list = message["content"]
        for content in content_list:
            if content["type"] == "text":
                content_str += content["text"]
    message.get("name", "")
    id = str(message.get("tool_call_id", str(uuid.uuid4())))

    tool_result_content_block = BedrockToolResultContentBlock(text=content_str)
    tool_result = BedrockToolResultBlock(
        content=[tool_result_content_block],
        toolUseId=id,
    )
    content_block = BedrockContentBlock(toolResult=tool_result)

    return content_block


def _insert_assistant_continue_message(
    messages: List[BedrockMessageBlock],
    assistant_continue_message: Optional[
        Union[str, ChatCompletionAssistantMessage]
    ] = None,
) -> List[BedrockMessageBlock]:
    """
    Add dummy message between user/tool result blocks.

    Conversation blocks and tool result blocks cannot be provided in the same turn. Issue: https://github.com/BerriAI/litellm/issues/6053
    """
    if assistant_continue_message is not None:
        if isinstance(assistant_continue_message, str):
            messages.append(
                BedrockMessageBlock(
                    role="assistant",
                    content=[BedrockContentBlock(text=assistant_continue_message)],
                )
            )
        elif isinstance(assistant_continue_message, dict):
            text = convert_content_list_to_str(assistant_continue_message)
            messages.append(
                BedrockMessageBlock(
                    role="assistant",
                    content=[BedrockContentBlock(text=text)],
                )
            )
    elif litellm.modify_params:
        text = convert_content_list_to_str(
            cast(ChatCompletionAssistantMessage, DEFAULT_ASSISTANT_CONTINUE_MESSAGE)
        )
        messages.append(
            BedrockMessageBlock(
                role="assistant",
                content=[
                    BedrockContentBlock(text=text),
                ],
            )
        )
    return messages


def get_user_message_block_or_continue_message(
    message: ChatCompletionUserMessage,
    user_continue_message: Optional[ChatCompletionUserMessage] = None,
) -> ChatCompletionUserMessage:
    """
    Returns the user content block
    if content block is an empty string, then return the default continue message

    Relevant Issue: https://github.com/BerriAI/litellm/issues/7169
    """
    content_block = message.get("content", None)

    # Handle None case
    if content_block is None or (
        user_continue_message is None and litellm.modify_params is False
    ):
        return skip_empty_text_blocks(message=message)

    # Handle string case
    if isinstance(content_block, str):
        # check if content is empty
        if content_block.strip():
            return message
        else:
            return ChatCompletionUserMessage(
                **(user_continue_message or DEFAULT_USER_CONTINUE_MESSAGE)  # type: ignore
            )

    # Handle list case
    if isinstance(content_block, list):
        """
        CHECK FOR
            "content": [
                {
                "type": "text",
                "text": ""
                }
            ],
        """
        if not content_block:
            return ChatCompletionUserMessage(
                **(user_continue_message or DEFAULT_USER_CONTINUE_MESSAGE)  # type: ignore
            )
        # Create a copy of the message to avoid modifying the original
        modified_content_block = content_block.copy()

        for item in modified_content_block:
            # Check if the list is empty
            if item["type"] == "text":
                if not item["text"].strip():
                    # Replace empty text with continue message
                    _user_continue_message = ChatCompletionUserMessage(
                        **(user_continue_message or DEFAULT_USER_CONTINUE_MESSAGE)  # type: ignore
                    )
                    text = convert_content_list_to_str(_user_continue_message)
                    item["text"] = text
                    break
        modified_message = message.copy()
        modified_message["content"] = modified_content_block
        return modified_message

    # Handle unsupported type
    raise ValueError(f"Unsupported content type: {type(content_block)}")


def return_assistant_continue_message(
    assistant_continue_message: Optional[
        Union[str, ChatCompletionAssistantMessage]
    ] = None,
) -> ChatCompletionAssistantMessage:
    if assistant_continue_message and isinstance(assistant_continue_message, str):
        return ChatCompletionAssistantMessage(
            role="assistant",
            content=assistant_continue_message,
        )
    elif assistant_continue_message and isinstance(assistant_continue_message, dict):
        return ChatCompletionAssistantMessage(**assistant_continue_message)
    else:
        return DEFAULT_ASSISTANT_CONTINUE_MESSAGE


def _skip_empty_dict_blocks(blocks: List[dict]) -> List[dict]:
    """
    Filter out empty text blocks from a list of dictionaries.

    Args:
        blocks: List of dictionaries representing message content blocks

    Returns:
        Filtered list of non-empty text blocks
    """
    return [
        item
        for item in blocks
        if not (item.get("type") == "text" and not item.get("text", "").strip())
    ]


@overload
def skip_empty_text_blocks(
    message: ChatCompletionAssistantMessage,
) -> ChatCompletionAssistantMessage:
    pass


@overload
def skip_empty_text_blocks(
    message: ChatCompletionUserMessage,
) -> ChatCompletionUserMessage:
    pass


def skip_empty_text_blocks(
    message: Union[ChatCompletionAssistantMessage, ChatCompletionUserMessage],
) -> Union[ChatCompletionAssistantMessage, ChatCompletionUserMessage]:
    """
    Skips empty text blocks in message content text blocks.

    Do not insert content here. This is a helper function, which can also be used in base case.
    """
    content_block = message.get("content", None)
    if content_block is None:
        return message
    if (
        isinstance(content_block, str)
        and not content_block.strip()
        and is_non_content_values_set(message)
        and message["role"] == "assistant"
    ):
        modified_message = message.copy()
        modified_message["content"] = None  # user message content cannot be None
        return modified_message
    elif isinstance(content_block, list):
        modified_content_block = _skip_empty_dict_blocks(
            cast(List[dict], content_block)
        )

        # If no content remains and it's an assistant message, set content to None
        if not modified_content_block and message["role"] == "assistant":
            modified_message = message.copy()
            modified_message["content"] = None
            return modified_message

        modified_message_alt = message.copy()

        # Type-specific casting based on message role
        if message["role"] == "assistant":
            modified_message_alt["content"] = cast(  # type: ignore
                Optional[List[OpenAIMessageContentListBlock]],
                modified_content_block or None,
            )
        elif message["role"] == "user" and modified_content_block is not None:
            modified_message_alt["content"] = cast(  # type: ignore
                Optional[List[ChatCompletionTextObject]], modified_content_block
            )

        return modified_message_alt

    return message


def process_empty_text_blocks(
    message: ChatCompletionAssistantMessage,
    assistant_continue_message: Optional[
        Union[str, ChatCompletionAssistantMessage]
    ] = None,
) -> ChatCompletionAssistantMessage:
    modified_content_block = message.get("content", None)
    ## BASE CASE ##
    if modified_content_block is None or not isinstance(modified_content_block, list):
        return message

    # Check if all items are empty text blocks
    if all(
        item["type"] == "text" and not item["text"].strip()
        for item in modified_content_block
    ):
        # Replace with a single continue message
        _assistant_continue_message = return_assistant_continue_message(
            assistant_continue_message
        )
        modified_content_block = [
            {
                "type": "text",
                "text": convert_content_list_to_str(_assistant_continue_message),
            }
        ]
    else:
        # Filter out only empty text blocks, keeping non-empty text and other block types
        modified_content_block = [
            item
            for item in modified_content_block
            if not (item["type"] == "text" and not item["text"].strip())
        ]

    modified_message = message.copy()
    modified_message["content"] = modified_content_block
    return modified_message


def get_assistant_message_block_or_continue_message(
    message: ChatCompletionAssistantMessage,
    assistant_continue_message: Optional[
        Union[str, ChatCompletionAssistantMessage]
    ] = None,
) -> ChatCompletionAssistantMessage:
    """
    Returns the user content block
    if content block is an empty string, then return the default continue message

    Relevant Issue: https://github.com/BerriAI/litellm/issues/7169
    """
    content_block = message.get("content", None)

    # Handle Base case
    if content_block is None or (
        assistant_continue_message is None and litellm.modify_params is False
    ):
        return skip_empty_text_blocks(message=message)

    # Handle string case
    if isinstance(content_block, str):
        # check if content is empty
        if content_block.strip():
            return message
        else:
            if is_non_content_values_set(message):
                modified_message = message.copy()
                modified_message["content"] = None
                return modified_message
            return return_assistant_continue_message(assistant_continue_message)

    # Handle list case
    if isinstance(content_block, list):
        """
        CHECK FOR
            "content": [
                {
                "type": "text",
                "text": ""
                }
            ],
        """
        return process_empty_text_blocks(
            message=message, assistant_continue_message=assistant_continue_message
        )

    # Handle unsupported type
    raise ValueError(f"Unsupported content type: {type(content_block)}")


class BedrockConverseMessagesProcessor:
    @staticmethod
    def _initial_message_setup(
        messages: List,
        user_continue_message: Optional[ChatCompletionUserMessage] = None,
    ) -> List:
        if messages[0].get("role") is not None and messages[0]["role"] == "assistant":
            if user_continue_message is not None:
                messages.insert(0, user_continue_message)
            elif litellm.modify_params:
                messages.insert(0, DEFAULT_USER_CONTINUE_MESSAGE)

        # if final message is assistant message
        if messages[-1].get("role") is not None and messages[-1]["role"] == "assistant":
            if user_continue_message is not None:
                messages.append(user_continue_message)
            elif litellm.modify_params:
                messages.append(DEFAULT_USER_CONTINUE_MESSAGE)
        return messages

    @staticmethod
    async def _bedrock_converse_messages_pt_async(  # noqa: PLR0915
        messages: List,
        model: str,
        llm_provider: str,
        user_continue_message: Optional[ChatCompletionUserMessage] = None,
        assistant_continue_message: Optional[
            Union[str, ChatCompletionAssistantMessage]
        ] = None,
    ) -> List[BedrockMessageBlock]:
        contents: List[BedrockMessageBlock] = []
        msg_i = 0

        ## BASE CASE ##
        if len(messages) == 0:
            raise litellm.BadRequestError(
                message=BAD_MESSAGE_ERROR_STR
                + "bedrock requires at least one non-system message",
                model=model,
                llm_provider=llm_provider,
            )

        # if initial message is assistant message
        messages = BedrockConverseMessagesProcessor._initial_message_setup(
            messages, user_continue_message
        )

        while msg_i < len(messages):
            user_content: List[BedrockContentBlock] = []
            init_msg_i = msg_i
            ## MERGE CONSECUTIVE USER CONTENT ##
            while msg_i < len(messages) and messages[msg_i]["role"] == "user":
                message_block = get_user_message_block_or_continue_message(
                    message=messages[msg_i],
                    user_continue_message=user_continue_message,
                )
                if isinstance(message_block["content"], list):
                    _parts: List[BedrockContentBlock] = []
                    for element in message_block["content"]:
                        if isinstance(element, dict):
                            if element["type"] == "text":
                                _part = BedrockContentBlock(text=element["text"])
                                _parts.append(_part)
                            elif element["type"] == "image_url":
                                format: Optional[str] = None
                                if isinstance(element["image_url"], dict):
                                    image_url = element["image_url"]["url"]
                                    format = element["image_url"].get("format")
                                else:
                                    image_url = element["image_url"]
                                _part = await BedrockImageProcessor.process_image_async(  # type: ignore
                                    image_url=image_url, format=format
                                )
                                _parts.append(_part)  # type: ignore
                            elif element["type"] == "file":
                                _part = await BedrockConverseMessagesProcessor._async_process_file_message(
                                    message=cast(ChatCompletionFileObject, element)
                                )
                                _parts.append(_part)
                            _cache_point_block = (
                                litellm.AmazonConverseConfig()._get_cache_point_block(
                                    message_block=cast(
                                        OpenAIMessageContentListBlock, element
                                    ),
                                    block_type="content_block",
                                )
                            )
                            if _cache_point_block is not None:
                                _parts.append(_cache_point_block)
                    user_content.extend(_parts)
                elif message_block["content"] and isinstance(
                    message_block["content"], str
                ):
                    _part = BedrockContentBlock(text=messages[msg_i]["content"])
                    _cache_point_block = (
                        litellm.AmazonConverseConfig()._get_cache_point_block(
                            message_block, block_type="content_block"
                        )
                    )
                    user_content.append(_part)
                    if _cache_point_block is not None:
                        user_content.append(_cache_point_block)

                msg_i += 1
            if user_content:
                if len(contents) > 0 and contents[-1]["role"] == "user":
                    if (
                        assistant_continue_message is not None
                        or litellm.modify_params is True
                    ):
                        # if last message was a 'user' message, then add a dummy assistant message (bedrock requires alternating roles)
                        contents = _insert_assistant_continue_message(
                            messages=contents,
                            assistant_continue_message=assistant_continue_message,
                        )
                        contents.append(
                            BedrockMessageBlock(role="user", content=user_content)
                        )
                    else:
                        verbose_logger.warning(
                            "Potential consecutive user/tool blocks. Trying to merge. If error occurs, please set a 'assistant_continue_message' or set 'modify_params=True' to insert a dummy assistant message for bedrock calls."
                        )
                        contents[-1]["content"].extend(user_content)
                else:
                    contents.append(
                        BedrockMessageBlock(role="user", content=user_content)
                    )

            ## MERGE CONSECUTIVE TOOL CALL MESSAGES ##
            tool_content: List[BedrockContentBlock] = []
            while msg_i < len(messages) and messages[msg_i]["role"] == "tool":
                tool_call_result = _convert_to_bedrock_tool_call_result(messages[msg_i])

                tool_content.append(tool_call_result)
                msg_i += 1
            if tool_content:
                # if last message was a 'user' message, then add a blank assistant message (bedrock requires alternating roles)
                if len(contents) > 0 and contents[-1]["role"] == "user":
                    if (
                        assistant_continue_message is not None
                        or litellm.modify_params is True
                    ):
                        # if last message was a 'user' message, then add a dummy assistant message (bedrock requires alternating roles)
                        contents = _insert_assistant_continue_message(
                            messages=contents,
                            assistant_continue_message=assistant_continue_message,
                        )
                        contents.append(
                            BedrockMessageBlock(role="user", content=tool_content)
                        )
                    else:
                        verbose_logger.warning(
                            "Potential consecutive user/tool blocks. Trying to merge. If error occurs, please set a 'assistant_continue_message' or set 'modify_params=True' to insert a dummy assistant message for bedrock calls."
                        )
                        contents[-1]["content"].extend(tool_content)
                else:
                    contents.append(
                        BedrockMessageBlock(role="user", content=tool_content)
                    )
            assistant_content: List[BedrockContentBlock] = []
            ## MERGE CONSECUTIVE ASSISTANT CONTENT ##
            while msg_i < len(messages) and messages[msg_i]["role"] == "assistant":
                assistant_message_block = (
                    get_assistant_message_block_or_continue_message(
                        message=messages[msg_i],
                        assistant_continue_message=assistant_continue_message,
                    )
                )
                _assistant_content = assistant_message_block.get("content", None)
                thinking_blocks = cast(
                    Optional[List[ChatCompletionThinkingBlock]],
                    assistant_message_block.get("thinking_blocks"),
                )

                if thinking_blocks is not None:
                    converted_thinking_blocks = BedrockConverseMessagesProcessor.translate_thinking_blocks_to_reasoning_content_blocks(
                        thinking_blocks
                    )
                    assistant_content = BedrockConverseMessagesProcessor.add_thinking_blocks_to_assistant_content(
                        thinking_blocks=converted_thinking_blocks,
                        assistant_parts=assistant_content,
                    )

                if _assistant_content is not None and isinstance(
                    _assistant_content, list
                ):
                    assistants_parts: List[BedrockContentBlock] = []
                    for element in _assistant_content:
                        if isinstance(element, dict):
                            if element["type"] == "thinking":
                                thinking_block = BedrockConverseMessagesProcessor.translate_thinking_blocks_to_reasoning_content_blocks(
                                    thinking_blocks=[
                                        cast(ChatCompletionThinkingBlock, element)
                                    ]
                                )
                                assistants_parts = BedrockConverseMessagesProcessor.add_thinking_blocks_to_assistant_content(
                                    thinking_blocks=thinking_block,
                                    assistant_parts=assistants_parts,
                                )
                            elif element["type"] == "text":
                                assistants_part = BedrockContentBlock(
                                    text=element["text"]
                                )
                                assistants_parts.append(assistants_part)
                            elif element["type"] == "image_url":
                                if isinstance(element["image_url"], dict):
                                    image_url = element["image_url"]["url"]
                                else:
                                    image_url = element["image_url"]
                                assistants_part = await BedrockImageProcessor.process_image_async(  # type: ignore
                                    image_url=image_url
                                )
                                assistants_parts.append(assistants_part)
                    assistant_content.extend(assistants_parts)
                elif _assistant_content is not None and isinstance(
                    _assistant_content, str
                ):
                    assistant_content.append(
                        BedrockContentBlock(text=_assistant_content)
                    )
                _tool_calls = assistant_message_block.get("tool_calls", [])
                if _tool_calls:
                    assistant_content.extend(
                        _convert_to_bedrock_tool_call_invoke(_tool_calls)
                    )

                msg_i += 1

            if assistant_content:
                contents.append(
                    BedrockMessageBlock(role="assistant", content=assistant_content)
                )

            if msg_i == init_msg_i:  # prevent infinite loops
                raise litellm.BadRequestError(
                    message=BAD_MESSAGE_ERROR_STR + f"passed in {messages[msg_i]}",
                    model=model,
                    llm_provider=llm_provider,
                )

        return contents

    @staticmethod
    def translate_thinking_blocks_to_reasoning_content_blocks(
        thinking_blocks: List[ChatCompletionThinkingBlock],
    ) -> List[BedrockContentBlock]:
        reasoning_content_blocks: List[BedrockContentBlock] = []
        for thinking_block in thinking_blocks:
            reasoning_text = thinking_block.get("thinking")
            reasoning_signature = thinking_block.get("signature")
            text_block = BedrockConverseReasoningTextBlock(
                text=reasoning_text or "",
            )
            if reasoning_signature is not None:
                text_block["signature"] = reasoning_signature
            reasoning_content_block = BedrockConverseReasoningContentBlock(
                reasoningText=text_block,
            )
            bedrock_content_block = BedrockContentBlock(
                reasoningContent=reasoning_content_block
            )
            reasoning_content_blocks.append(bedrock_content_block)
        return reasoning_content_blocks

    @staticmethod
    def _process_file_message(message: ChatCompletionFileObject) -> BedrockContentBlock:
        file_message = message["file"]
        file_data = file_message.get("file_data")
        file_id = file_message.get("file_id")

        if file_data is None and file_id is None:
            raise litellm.BadRequestError(
                message="file_data and file_id cannot both be None. Got={}".format(
                    message
                ),
                model="",
                llm_provider="bedrock",
            )
        format = file_message.get("format")
        return BedrockImageProcessor.process_image_sync(
            image_url=cast(str, file_id or file_data), format=format
        )

    @staticmethod
    async def _async_process_file_message(
        message: ChatCompletionFileObject,
    ) -> BedrockContentBlock:
        file_message = message["file"]
        file_data = file_message.get("file_data")
        file_id = file_message.get("file_id")
        format = file_message.get("format")
        if file_data is None and file_id is None:
            raise litellm.BadRequestError(
                message="file_data and file_id cannot both be None. Got={}".format(
                    message
                ),
                model="",
                llm_provider="bedrock",
            )
        return await BedrockImageProcessor.process_image_async(
            image_url=cast(str, file_id or file_data), format=format
        )

    @staticmethod
    def add_thinking_blocks_to_assistant_content(
        thinking_blocks: List[BedrockContentBlock],
        assistant_parts: List[BedrockContentBlock],
    ) -> List[BedrockContentBlock]:
        """
        If contains 'signature', it is a thinking block.
        If missing 'signature', it is a text block - e.g. when using a non-anthropic model.

        Handle error raised by bedrock if thinking blocks are provided for a non-thinking model (e.g. nova with tool use)

        Relevant Issue: https://github.com/BerriAI/litellm/issues/9063
        """
        filtered_thinking_blocks = []
        for block in thinking_blocks:
            reasoning_content = block.get("reasoningContent", None)
            reasoning_text = (
                reasoning_content.get("reasoningText", None)
                if reasoning_content is not None
                else None
            )
            if reasoning_text and not reasoning_text.get("signature"):
                reasoning_text_text = reasoning_text["text"]
                assistants_part = BedrockContentBlock(text=reasoning_text_text)
                assistant_parts.append(assistants_part)
            else:
                filtered_thinking_blocks.append(block)
        if len(filtered_thinking_blocks) > 0:
            assistant_parts.extend(filtered_thinking_blocks)
        return assistant_parts


def _bedrock_converse_messages_pt(  # noqa: PLR0915
    messages: List,
    model: str,
    llm_provider: str,
    user_continue_message: Optional[ChatCompletionUserMessage] = None,
    assistant_continue_message: Optional[
        Union[str, ChatCompletionAssistantMessage]
    ] = None,
) -> List[BedrockMessageBlock]:
    """
    Converts given messages from OpenAI format to Bedrock format

    - Roles must alternate b/w 'user' and 'model' (same as anthropic -> merge consecutive roles)
    - Please ensure that function response turn comes immediately after a function call turn
    - Conversation blocks and tool result blocks cannot be provided in the same turn. Issue: https://github.com/BerriAI/litellm/issues/6053
    """

    contents: List[BedrockMessageBlock] = []
    msg_i = 0

    ## BASE CASE ##
    if len(messages) == 0:
        raise litellm.BadRequestError(
            message=BAD_MESSAGE_ERROR_STR
            + "bedrock requires at least one non-system message",
            model=model,
            llm_provider=llm_provider,
        )

    # if initial message is assistant message
    if messages[0].get("role") is not None and messages[0]["role"] == "assistant":
        if user_continue_message is not None:
            messages.insert(0, user_continue_message)
        elif litellm.modify_params:
            messages.insert(0, DEFAULT_USER_CONTINUE_MESSAGE)

    # if final message is assistant message
    if messages[-1].get("role") is not None and messages[-1]["role"] == "assistant":
        if user_continue_message is not None:
            messages.append(user_continue_message)
        elif litellm.modify_params:
            messages.append(DEFAULT_USER_CONTINUE_MESSAGE)

    while msg_i < len(messages):
        user_content: List[BedrockContentBlock] = []
        init_msg_i = msg_i
        ## MERGE CONSECUTIVE USER CONTENT ##
        while msg_i < len(messages) and messages[msg_i]["role"] == "user":
            message_block = get_user_message_block_or_continue_message(
                message=messages[msg_i],
                user_continue_message=user_continue_message,
            )
            if isinstance(message_block["content"], list):
                _parts: List[BedrockContentBlock] = []
                for element in message_block["content"]:
                    if isinstance(element, dict):
                        if element["type"] == "text":
                            _part = BedrockContentBlock(text=element["text"])
                            _parts.append(_part)
                        elif element["type"] == "image_url":
                            format: Optional[str] = None
                            if isinstance(element["image_url"], dict):
                                image_url = element["image_url"]["url"]
                                format = element["image_url"].get("format")
                            else:
                                image_url = element["image_url"]
                            _part = BedrockImageProcessor.process_image_sync(  # type: ignore
                                image_url=image_url,
                                format=format,
                            )
                            _parts.append(_part)  # type: ignore
                        elif element["type"] == "file":
                            _part = (
                                BedrockConverseMessagesProcessor._process_file_message(
                                    message=cast(ChatCompletionFileObject, element)
                                )
                            )
                            _parts.append(_part)
                        _cache_point_block = (
                            litellm.AmazonConverseConfig()._get_cache_point_block(
                                message_block=cast(
                                    OpenAIMessageContentListBlock, element
                                ),
                                block_type="content_block",
                            )
                        )
                        if _cache_point_block is not None:
                            _parts.append(_cache_point_block)
                user_content.extend(_parts)
            elif message_block["content"] and isinstance(message_block["content"], str):
                _part = BedrockContentBlock(text=messages[msg_i]["content"])
                _cache_point_block = (
                    litellm.AmazonConverseConfig()._get_cache_point_block(
                        message_block, block_type="content_block"
                    )
                )
                user_content.append(_part)
                if _cache_point_block is not None:
                    user_content.append(_cache_point_block)

            msg_i += 1
        if user_content:
            if len(contents) > 0 and contents[-1]["role"] == "user":
                if (
                    assistant_continue_message is not None
                    or litellm.modify_params is True
                ):
                    # if last message was a 'user' message, then add a dummy assistant message (bedrock requires alternating roles)
                    contents = _insert_assistant_continue_message(
                        messages=contents,
                        assistant_continue_message=assistant_continue_message,
                    )
                    contents.append(
                        BedrockMessageBlock(role="user", content=user_content)
                    )
                else:
                    verbose_logger.warning(
                        "Potential consecutive user/tool blocks. Trying to merge. If error occurs, please set a 'assistant_continue_message' or set 'modify_params=True' to insert a dummy assistant message for bedrock calls."
                    )
                    contents[-1]["content"].extend(user_content)
            else:
                contents.append(BedrockMessageBlock(role="user", content=user_content))

        ## MERGE CONSECUTIVE TOOL CALL MESSAGES ##
        tool_content: List[BedrockContentBlock] = []
        while msg_i < len(messages) and messages[msg_i]["role"] == "tool":
            tool_call_result = _convert_to_bedrock_tool_call_result(messages[msg_i])

            tool_content.append(tool_call_result)
            msg_i += 1
        if tool_content:
            # if last message was a 'user' message, then add a blank assistant message (bedrock requires alternating roles)
            if len(contents) > 0 and contents[-1]["role"] == "user":
                if (
                    assistant_continue_message is not None
                    or litellm.modify_params is True
                ):
                    # if last message was a 'user' message, then add a dummy assistant message (bedrock requires alternating roles)
                    contents = _insert_assistant_continue_message(
                        messages=contents,
                        assistant_continue_message=assistant_continue_message,
                    )
                    contents.append(
                        BedrockMessageBlock(role="user", content=tool_content)
                    )
                else:
                    verbose_logger.warning(
                        "Potential consecutive user/tool blocks. Trying to merge. If error occurs, please set a 'assistant_continue_message' or set 'modify_params=True' to insert a dummy assistant message for bedrock calls."
                    )
                    contents[-1]["content"].extend(tool_content)
            else:
                contents.append(BedrockMessageBlock(role="user", content=tool_content))
        assistant_content: List[BedrockContentBlock] = []
        ## MERGE CONSECUTIVE ASSISTANT CONTENT ##
        while msg_i < len(messages) and messages[msg_i]["role"] == "assistant":
            assistant_message_block = get_assistant_message_block_or_continue_message(
                message=messages[msg_i],
                assistant_continue_message=assistant_continue_message,
            )
            _assistant_content = assistant_message_block.get("content", None)
            thinking_blocks = cast(
                Optional[List[ChatCompletionThinkingBlock]],
                assistant_message_block.get("thinking_blocks"),
            )

            if thinking_blocks is not None:
                converted_thinking_blocks = BedrockConverseMessagesProcessor.translate_thinking_blocks_to_reasoning_content_blocks(
                    thinking_blocks
                )
                assistant_content = BedrockConverseMessagesProcessor.add_thinking_blocks_to_assistant_content(
                    thinking_blocks=converted_thinking_blocks,
                    assistant_parts=assistant_content,
                )

            if _assistant_content is not None and isinstance(_assistant_content, list):
                assistants_parts: List[BedrockContentBlock] = []
                for element in _assistant_content:
                    if isinstance(element, dict):
                        if element["type"] == "thinking":
                            thinking_block = BedrockConverseMessagesProcessor.translate_thinking_blocks_to_reasoning_content_blocks(
                                thinking_blocks=[
                                    cast(ChatCompletionThinkingBlock, element)
                                ]
                            )
                            assistants_parts = BedrockConverseMessagesProcessor.add_thinking_blocks_to_assistant_content(
                                thinking_blocks=thinking_block,
                                assistant_parts=assistants_parts,
                            )
                        elif element["type"] == "text":
                            assistants_part = BedrockContentBlock(text=element["text"])
                            assistants_parts.append(assistants_part)
                        elif element["type"] == "image_url":
                            if isinstance(element["image_url"], dict):
                                image_url = element["image_url"]["url"]
                            else:
                                image_url = element["image_url"]
                            assistants_part = BedrockImageProcessor.process_image_sync(  # type: ignore
                                image_url=image_url
                            )
                            assistants_parts.append(assistants_part)
                assistant_content.extend(assistants_parts)
            elif _assistant_content is not None and isinstance(_assistant_content, str):
                assistant_content.append(BedrockContentBlock(text=_assistant_content))
            _tool_calls = assistant_message_block.get("tool_calls", [])
            if _tool_calls:
                assistant_content.extend(
                    _convert_to_bedrock_tool_call_invoke(_tool_calls)
                )

            msg_i += 1

        if assistant_content:
            contents.append(
                BedrockMessageBlock(role="assistant", content=assistant_content)
            )

        if msg_i == init_msg_i:  # prevent infinite loops
            raise litellm.BadRequestError(
                message=BAD_MESSAGE_ERROR_STR + f"passed in {messages[msg_i]}",
                model=model,
                llm_provider=llm_provider,
            )

    return contents


def make_valid_bedrock_tool_name(input_tool_name: str) -> str:
    """
    Replaces any invalid characters in the input tool name with underscores
    and ensures the resulting string is a valid identifier for Bedrock tools
    """

    def replace_invalid(char):
        """
        Bedrock tool names only supports alpha-numeric characters and underscores
        """
        if char.isalnum() or char == "_":
            return char
        return "_"

    # If the string is empty, return a default valid identifier
    if input_tool_name is None or len(input_tool_name) == 0:
        return input_tool_name
    bedrock_tool_name = copy.copy(input_tool_name)
    # If it doesn't start with a letter, prepend 'a'
    if not bedrock_tool_name[0].isalpha():
        bedrock_tool_name = "a" + bedrock_tool_name

    # Replace any invalid characters with underscores
    valid_string = "".join(replace_invalid(char) for char in bedrock_tool_name)

    if input_tool_name != valid_string:
        # passed tool name was formatted to become valid
        # store it internally so we can use for the response
        litellm.bedrock_tool_name_mappings.set_cache(
            key=valid_string, value=input_tool_name
        )

    return valid_string


def add_cache_point_tool_block(tool: dict) -> Optional[BedrockToolBlock]:
    cache_control = tool.get("cache_control", None)
    if cache_control is not None:
        cache_point = cache_control.get("type", "ephemeral")
        if cache_point == "ephemeral":
            return {"cachePoint": {"type": "default"}}
    return None


def _bedrock_tools_pt(tools: List) -> List[BedrockToolBlock]:
    """
    OpenAI tools looks like:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            }
        }
    ]
    """
    """
    Bedrock toolConfig looks like: 
    "tools": [
        {
            "toolSpec": {
                "name": "top_song",
                "description": "Get the most popular song played on a radio station.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "sign": {
                                "type": "string",
                                "description": "The call sign for the radio station for which you want the most popular song. Example calls signs are WZPZ, and WKRP."
                            }
                        },
                        "required": [
                            "sign"
                        ]
                    }
                }
            }
        }
    ]
    """
    from litellm.litellm_core_utils.prompt_templates.common_utils import unpack_defs

    tool_block_list: List[BedrockToolBlock] = []
    for tool in tools:
        parameters = tool.get("function", {}).get(
            "parameters", {"type": "object", "properties": {}}
        )
        name = tool.get("function", {}).get("name", "")

        # related issue: https://github.com/BerriAI/litellm/issues/5007
        # Bedrock tool names must satisfy regular expression pattern: [a-zA-Z][a-zA-Z0-9_]* ensure this is true
        name = make_valid_bedrock_tool_name(input_tool_name=name)
        description = tool.get("function", {}).get(
            "description", name
        )  # converse api requires a description

        defs = parameters.pop("$defs", {})
        defs_copy = copy.deepcopy(defs)
        # flatten the defs
        for _, value in defs_copy.items():
            unpack_defs(value, defs_copy)
        unpack_defs(parameters, defs_copy)
        tool_input_schema = BedrockToolInputSchemaBlock(
            json=BedrockToolJsonSchemaBlock(
                type=parameters.get("type", ""),
                properties=parameters.get("properties", {}),
                required=parameters.get("required", []),
            )
        )
        tool_spec = BedrockToolSpecBlock(
            inputSchema=tool_input_schema, name=name, description=description
        )
        tool_block = BedrockToolBlock(toolSpec=tool_spec)
        tool_block_list.append(tool_block)

        ## ADD CACHE POINT TOOL BLOCK ##
        cache_point_tool_block = add_cache_point_tool_block(tool)
        if cache_point_tool_block is not None:
            tool_block_list.append(cache_point_tool_block)

    return tool_block_list


# Function call template
def function_call_prompt(messages: list, functions: list):
    function_prompt = """Produce JSON OUTPUT ONLY! Adhere to this format {"name": "function_name", "arguments":{"argument_name": "argument_value"}} The following functions are available to you:"""
    for function in functions:
        function_prompt += f"""\n{function}\n"""

    function_added_to_prompt = False
    for message in messages:
        if "system" in message["role"]:
            message["content"] += f""" {function_prompt}"""
            function_added_to_prompt = True

    if function_added_to_prompt is False:
        messages.append({"role": "system", "content": f"""{function_prompt}"""})

    return messages


def response_schema_prompt(model: str, response_schema: dict) -> str:
    """
    Decides if a user-defined custom prompt or default needs to be used

    Returns the prompt str that's passed to the model as a user message
    """
    custom_prompt_details: Optional[dict] = None
    response_schema_as_message = [
        {"role": "user", "content": "{}".format(response_schema)}
    ]
    if f"{model}/response_schema_prompt" in litellm.custom_prompt_dict:
        custom_prompt_details = litellm.custom_prompt_dict[
            f"{model}/response_schema_prompt"
        ]  # allow user to define custom response schema prompt by model
    elif "response_schema_prompt" in litellm.custom_prompt_dict:
        custom_prompt_details = litellm.custom_prompt_dict["response_schema_prompt"]

    if custom_prompt_details is not None:
        return custom_prompt(
            role_dict=custom_prompt_details["roles"],
            initial_prompt_value=custom_prompt_details["initial_prompt_value"],
            final_prompt_value=custom_prompt_details["final_prompt_value"],
            messages=response_schema_as_message,
        )
    else:
        return default_response_schema_prompt(response_schema=response_schema)


def default_response_schema_prompt(response_schema: dict) -> str:
    """
    Used if provider/model doesn't support 'response_schema' param.

    This is the default prompt. Allow user to override this with a custom_prompt.
    """
    prompt_str = """Use this JSON schema: 
    ```json 
    {}
    ```""".format(
        response_schema
    )
    return prompt_str


# Custom prompt template
def custom_prompt(
    role_dict: dict,
    messages: list,
    initial_prompt_value: str = "",
    final_prompt_value: str = "",
    bos_token: str = "",
    eos_token: str = "",
) -> str:
    prompt = bos_token + initial_prompt_value
    bos_open = True
    ## a bos token is at the start of a system / human message
    ## an eos token is at the end of the assistant response to the message
    for message in messages:
        role = message["role"]

        if role in ["system", "human"] and not bos_open:
            prompt += bos_token
            bos_open = True

        pre_message_str = (
            role_dict[role]["pre_message"]
            if role in role_dict and "pre_message" in role_dict[role]
            else ""
        )
        post_message_str = (
            role_dict[role]["post_message"]
            if role in role_dict and "post_message" in role_dict[role]
            else ""
        )
        if isinstance(message["content"], str):
            prompt += pre_message_str + message["content"] + post_message_str
        elif isinstance(message["content"], list):
            text_str = ""
            for content in message["content"]:
                if content.get("text", None) is not None and isinstance(
                    content["text"], str
                ):
                    text_str += content["text"]
            prompt += pre_message_str + text_str + post_message_str

        if role == "assistant":
            prompt += eos_token
            bos_open = False

    prompt += final_prompt_value
    return prompt


def prompt_factory(
    model: str,
    messages: list,
    custom_llm_provider: Optional[str] = None,
    api_key: Optional[str] = None,
):
    original_model_name = model
    model = model.lower()
    if custom_llm_provider == "ollama":
        return ollama_pt(model=model, messages=messages)
    elif custom_llm_provider == "anthropic":
        if litellm.AnthropicTextConfig._is_anthropic_text_model(model):
            return anthropic_pt(messages=messages)
        return anthropic_messages_pt(
            messages=messages, model=model, llm_provider=custom_llm_provider
        )
    elif custom_llm_provider == "anthropic_xml":
        return anthropic_messages_pt_xml(messages=messages)
    elif custom_llm_provider == "gemini":
        if (
            model == "gemini-pro-vision"
            or litellm.supports_vision(model=model)
            or litellm.supports_vision(model=custom_llm_provider + "/" + model)
        ):
            return _gemini_vision_convert_messages(messages=messages)
        else:
            return gemini_text_image_pt(messages=messages)
    elif custom_llm_provider == "mistral":
        return litellm.MistralConfig()._transform_messages(
            messages=messages, model=model
        )
    elif custom_llm_provider == "bedrock":
        if "amazon.titan-text" in model:
            return amazon_titan_pt(messages=messages)
        elif "anthropic." in model:
            if any(_ in model for _ in ["claude-2.1", "claude-v2:1"]):
                return claude_2_1_pt(messages=messages)
            else:
                return anthropic_pt(messages=messages)
        elif "mistral." in model:
            return mistral_instruct_pt(messages=messages)
        elif "llama2" in model and "chat" in model:
            return llama_2_chat_pt(messages=messages)
        elif ("llama3" in model or "llama4" in model) and "instruct" in model:
            return hf_chat_template(
                model="meta-llama/Meta-Llama-3-8B-Instruct",
                messages=messages,
            )

    elif custom_llm_provider == "clarifai":
        if "claude" in model:
            return anthropic_pt(messages=messages)

    elif custom_llm_provider == "perplexity":
        for message in messages:
            message.pop("name", None)
        return messages
    elif custom_llm_provider == "azure_text":
        return azure_text_pt(messages=messages)
    elif custom_llm_provider == "watsonx":
        if "granite" in model and "chat" in model:
            # granite-13b-chat-v1 and granite-13b-chat-v2 use a specific prompt template
            return ibm_granite_pt(messages=messages)
        elif "ibm-mistral" in model and "instruct" in model:
            # models like ibm-mistral/mixtral-8x7b-instruct-v01-q use the mistral instruct prompt template
            return mistral_instruct_pt(messages=messages)
        elif "meta-llama/llama-3" in model and "instruct" in model:
            # https://llama.meta.com/docs/model-cards-and-prompt-formats/meta-llama-3/
            return custom_prompt(
                role_dict={
                    "system": {
                        "pre_message": "<|start_header_id|>system<|end_header_id|>\n",
                        "post_message": "<|eot_id|>",
                    },
                    "user": {
                        "pre_message": "<|start_header_id|>user<|end_header_id|>\n",
                        "post_message": "<|eot_id|>",
                    },
                    "assistant": {
                        "pre_message": "<|start_header_id|>assistant<|end_header_id|>\n",
                        "post_message": "<|eot_id|>",
                    },
                },
                messages=messages,
                initial_prompt_value="<|begin_of_text|>",
                final_prompt_value="<|start_header_id|>assistant<|end_header_id|>\n",
            )
    try:
        if "meta-llama/llama-2" in model and "chat" in model:
            return llama_2_chat_pt(messages=messages)
        elif (
            "meta-llama/llama-3" in model or "meta-llama-3" in model
        ) and "instruct" in model:
            return hf_chat_template(
                model="meta-llama/Meta-Llama-3-8B-Instruct",
                messages=messages,
            )
        elif (
            "tiiuae/falcon" in model
        ):  # Note: for the instruct models, it's best to use a User: .., Assistant:.. approach in your prompt template.
            if model == "tiiuae/falcon-180B-chat":
                return falcon_chat_pt(messages=messages)
            elif "instruct" in model:
                return falcon_instruct_pt(messages=messages)
        elif "mosaicml/mpt" in model:
            if "chat" in model:
                return mpt_chat_pt(messages=messages)
        elif "codellama/codellama" in model or "togethercomputer/codellama" in model:
            if "instruct" in model:
                return llama_2_chat_pt(
                    messages=messages
                )  # https://huggingface.co/blog/codellama#conversational-instructions
        elif "wizardlm/wizardcoder" in model:
            return wizardcoder_pt(messages=messages)
        elif "phind/phind-codellama" in model:
            return phind_codellama_pt(messages=messages)
        elif "togethercomputer/llama-2" in model and (
            "instruct" in model or "chat" in model
        ):
            return llama_2_chat_pt(messages=messages)
        elif model in [
            "gryphe/mythomax-l2-13b",
            "gryphe/mythomix-l2-13b",
            "gryphe/mythologic-l2-13b",
        ]:
            return alpaca_pt(messages=messages)
        elif model.strip() == "meta-llama/llamaguard-7b":
            chat_template = "{% if messages|length % 2 == 0 %}{% set role = 'Agent' %}{% else %}{% set role = 'User' %}{% endif %}{{ \"[INST] Task: Check if there is unsafe content in '\" + role + \"' messages in conversations according our safety policy with the below categories.\n\n<BEGIN UNSAFE CONTENT CATEGORIES>\nO1: Violence and Hate. \nShould not\n- Help people plan or engage in violence.\n- Encourage people to engage in violence.\n- Express hateful, derogatory, or demeaning sentiments against people based on sensitive personal characteristics like their race, color, religion, national origin, sexual orientation, gender, gender identity, or disability.\n- Encourage discrimination against people based on those characteristics and should not use slurs or create insults based on those characteristics.\nCan\n- Provide information on violence and discrimination.\n- Discuss the topics of hate and violence, and can discuss historical events involving violence.\nO2: Sexual Content.\nShould not\n- Engage in sexually explicit (i.e., erotic) conversations and should not encourage people to engage in sexual activities.\nCan\n- Discuss topics related to sexuality and sexual education.\n- Provide general information regarding sexual activities.\n- Provide guidance on topics related to sexual health.\nO3: Criminal Planning.\nShould not\n- Help people plan or engage in criminal activities like theft, kidnapping, or financial crimes, especially when the person indicates that they may act on the information provided to them.\n- Encourage people to engage in criminal activities or condone criminal behavior.\nCan\n- Help people understand how crimes are committed, provided that the response is not so detailed that it could be used to provide a roadmap for future crimes.\n- Help people understand how systems work that are used to prevent crimes, provided those descriptions do not provide detailed information on how to defeat those systems.\nO4: Guns and Illegal Weapons.\nShould not\n- Assist in the planning or execution of firearm or illegal weapons crimes, especially when the person indicates that they may act on the information provided to them.\n- Encourage people to engage in firearm or illegal weapons crimes or condone such behavior.\nCan\n- Discuss firearms and the arguments for and against firearm ownership.\nO5: Regulated or Controlled Substances.\nShould not\n- Encourage or assist people in the trafficking, consumption, or use of regulated or controlled substances, including but not limited to illegal drugs, tobacco, alcohol, and cannabis.\n- Assist or encourage people to create such substances when it is illegal to do so.\nCan\n- Discuss the use of regulated or controlled substances, and can provide general information on those substances (ex: what their chemical composition is and what their effects are).\n- Provide information on how those substances are manufactured, provided that the information is not so detailed as to provide step-by-step instructions for their creation.\nO6: Self-Harm.\nShould not\n- Encourage people to harm themselves.\n- Romanticize or condone self-harm or suicide.\n- Provide information regarding the methods of suicide or self-harm.\n- Provide any information or advice, other than information regarding appropriate health resources, to people who express or imply that they wish to harm themselves.\nCan\n- Provide general information regarding self-harm and suicide (ex: statistics, the mental health challenges faced by those who take these actions).\nShould\n- Provide information regarding appropriate health resources to people who imply or express the desire to harm themselves.\n<END UNSAFE CONTENT CATEGORIES>\n\n<BEGIN CONVERSATION>\n\n\" }}{% for message in messages %}{% if (message['role'] == 'user') != (loop.index0 % 2 == 0) %}{{ raise_exception('Conversation roles must alternate user/assistant/user/assistant/...') }}{% endif %}{% set content = message['content'] %}{% if message['role'] == 'user' %}{% set role = 'User' %}{% elif message['role'] == 'assistant' %}{% set role = 'Agent' %}{% endif %}{{ role + ': ' + content.strip() + '\n\n' }}{% endfor %}{{ \"<END CONVERSATION>\n\nProvide your safety assessment for \" + role + \" in the above conversation:\n- First line must read 'safe' or 'unsafe'.\n- If unsafe, a second line must include a comma-separated list of violated categories. [/INST]\" }}"
            return hf_chat_template(
                model=model, messages=messages, chat_template=chat_template
            )
        else:
            return hf_chat_template(original_model_name, messages)
    except Exception:
        return default_pt(
            messages=messages
        )  # default that covers Bloom, T-5, any non-chat tuned model (e.g. base Llama2)


def get_attribute_or_key(tool_or_function, attribute, default=None):
    if hasattr(tool_or_function, attribute):
        return getattr(tool_or_function, attribute)
    return tool_or_function.get(attribute, default)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\page.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Page
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import debugger
from . import dom
from . import emulation
from . import io
from . import network
from . import runtime


class FrameId(str):
    '''
    Unique frame identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> FrameId:
        return cls(json)

    def __repr__(self):
        return 'FrameId({})'.format(super().__repr__())


class AdFrameType(enum.Enum):
    '''
    Indicates whether a frame has been identified as an ad.
    '''
    NONE = "none"
    CHILD = "child"
    ROOT = "root"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AdFrameExplanation(enum.Enum):
    PARENT_IS_AD = "ParentIsAd"
    CREATED_BY_AD_SCRIPT = "CreatedByAdScript"
    MATCHED_BLOCKING_RULE = "MatchedBlockingRule"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AdFrameStatus:
    '''
    Indicates whether a frame has been identified as an ad and why.
    '''
    ad_frame_type: AdFrameType

    explanations: typing.Optional[typing.List[AdFrameExplanation]] = None

    def to_json(self):
        json = dict()
        json['adFrameType'] = self.ad_frame_type.to_json()
        if self.explanations is not None:
            json['explanations'] = [i.to_json() for i in self.explanations]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            ad_frame_type=AdFrameType.from_json(json['adFrameType']),
            explanations=[AdFrameExplanation.from_json(i) for i in json['explanations']] if 'explanations' in json else None,
        )


@dataclass
class AdScriptId:
    '''
    Identifies the bottom-most script which caused the frame to be labelled
    as an ad.
    '''
    #: Script Id of the bottom-most script which caused the frame to be labelled
    #: as an ad.
    script_id: runtime.ScriptId

    #: Id of adScriptId's debugger.
    debugger_id: runtime.UniqueDebuggerId

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['debuggerId'] = self.debugger_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            debugger_id=runtime.UniqueDebuggerId.from_json(json['debuggerId']),
        )


class SecureContextType(enum.Enum):
    '''
    Indicates whether the frame is a secure context and why it is the case.
    '''
    SECURE = "Secure"
    SECURE_LOCALHOST = "SecureLocalhost"
    INSECURE_SCHEME = "InsecureScheme"
    INSECURE_ANCESTOR = "InsecureAncestor"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CrossOriginIsolatedContextType(enum.Enum):
    '''
    Indicates whether the frame is cross-origin isolated and why it is the case.
    '''
    ISOLATED = "Isolated"
    NOT_ISOLATED = "NotIsolated"
    NOT_ISOLATED_FEATURE_DISABLED = "NotIsolatedFeatureDisabled"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class GatedAPIFeatures(enum.Enum):
    SHARED_ARRAY_BUFFERS = "SharedArrayBuffers"
    SHARED_ARRAY_BUFFERS_TRANSFER_ALLOWED = "SharedArrayBuffersTransferAllowed"
    PERFORMANCE_MEASURE_MEMORY = "PerformanceMeasureMemory"
    PERFORMANCE_PROFILE = "PerformanceProfile"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PermissionsPolicyFeature(enum.Enum):
    '''
    All Permissions Policy features. This enum should match the one defined
    in services/network/public/cpp/permissions_policy/permissions_policy_features.json5.
    LINT.IfChange(PermissionsPolicyFeature)
    '''
    ACCELEROMETER = "accelerometer"
    ALL_SCREENS_CAPTURE = "all-screens-capture"
    AMBIENT_LIGHT_SENSOR = "ambient-light-sensor"
    ATTRIBUTION_REPORTING = "attribution-reporting"
    AUTOPLAY = "autoplay"
    BLUETOOTH = "bluetooth"
    BROWSING_TOPICS = "browsing-topics"
    CAMERA = "camera"
    CAPTURED_SURFACE_CONTROL = "captured-surface-control"
    CH_DPR = "ch-dpr"
    CH_DEVICE_MEMORY = "ch-device-memory"
    CH_DOWNLINK = "ch-downlink"
    CH_ECT = "ch-ect"
    CH_PREFERS_COLOR_SCHEME = "ch-prefers-color-scheme"
    CH_PREFERS_REDUCED_MOTION = "ch-prefers-reduced-motion"
    CH_PREFERS_REDUCED_TRANSPARENCY = "ch-prefers-reduced-transparency"
    CH_RTT = "ch-rtt"
    CH_SAVE_DATA = "ch-save-data"
    CH_UA = "ch-ua"
    CH_UA_ARCH = "ch-ua-arch"
    CH_UA_BITNESS = "ch-ua-bitness"
    CH_UA_HIGH_ENTROPY_VALUES = "ch-ua-high-entropy-values"
    CH_UA_PLATFORM = "ch-ua-platform"
    CH_UA_MODEL = "ch-ua-model"
    CH_UA_MOBILE = "ch-ua-mobile"
    CH_UA_FORM_FACTORS = "ch-ua-form-factors"
    CH_UA_FULL_VERSION = "ch-ua-full-version"
    CH_UA_FULL_VERSION_LIST = "ch-ua-full-version-list"
    CH_UA_PLATFORM_VERSION = "ch-ua-platform-version"
    CH_UA_WOW64 = "ch-ua-wow64"
    CH_VIEWPORT_HEIGHT = "ch-viewport-height"
    CH_VIEWPORT_WIDTH = "ch-viewport-width"
    CH_WIDTH = "ch-width"
    CLIPBOARD_READ = "clipboard-read"
    CLIPBOARD_WRITE = "clipboard-write"
    COMPUTE_PRESSURE = "compute-pressure"
    CONTROLLED_FRAME = "controlled-frame"
    CROSS_ORIGIN_ISOLATED = "cross-origin-isolated"
    DEFERRED_FETCH = "deferred-fetch"
    DEFERRED_FETCH_MINIMAL = "deferred-fetch-minimal"
    DEVICE_ATTRIBUTES = "device-attributes"
    DIGITAL_CREDENTIALS_GET = "digital-credentials-get"
    DIRECT_SOCKETS = "direct-sockets"
    DIRECT_SOCKETS_PRIVATE = "direct-sockets-private"
    DISPLAY_CAPTURE = "display-capture"
    DOCUMENT_DOMAIN = "document-domain"
    ENCRYPTED_MEDIA = "encrypted-media"
    EXECUTION_WHILE_OUT_OF_VIEWPORT = "execution-while-out-of-viewport"
    EXECUTION_WHILE_NOT_RENDERED = "execution-while-not-rendered"
    FENCED_UNPARTITIONED_STORAGE_READ = "fenced-unpartitioned-storage-read"
    FOCUS_WITHOUT_USER_ACTIVATION = "focus-without-user-activation"
    FULLSCREEN = "fullscreen"
    FROBULATE = "frobulate"
    GAMEPAD = "gamepad"
    GEOLOCATION = "geolocation"
    GYROSCOPE = "gyroscope"
    HID = "hid"
    IDENTITY_CREDENTIALS_GET = "identity-credentials-get"
    IDLE_DETECTION = "idle-detection"
    INTEREST_COHORT = "interest-cohort"
    JOIN_AD_INTEREST_GROUP = "join-ad-interest-group"
    KEYBOARD_MAP = "keyboard-map"
    LANGUAGE_DETECTOR = "language-detector"
    LOCAL_FONTS = "local-fonts"
    LOCAL_NETWORK_ACCESS = "local-network-access"
    MAGNETOMETER = "magnetometer"
    MEDIA_PLAYBACK_WHILE_NOT_VISIBLE = "media-playback-while-not-visible"
    MICROPHONE = "microphone"
    MIDI = "midi"
    OTP_CREDENTIALS = "otp-credentials"
    PAYMENT = "payment"
    PICTURE_IN_PICTURE = "picture-in-picture"
    POPINS = "popins"
    PRIVATE_AGGREGATION = "private-aggregation"
    PRIVATE_STATE_TOKEN_ISSUANCE = "private-state-token-issuance"
    PRIVATE_STATE_TOKEN_REDEMPTION = "private-state-token-redemption"
    PUBLICKEY_CREDENTIALS_CREATE = "publickey-credentials-create"
    PUBLICKEY_CREDENTIALS_GET = "publickey-credentials-get"
    RECORD_AD_AUCTION_EVENTS = "record-ad-auction-events"
    REWRITER = "rewriter"
    RUN_AD_AUCTION = "run-ad-auction"
    SCREEN_WAKE_LOCK = "screen-wake-lock"
    SERIAL = "serial"
    SHARED_AUTOFILL = "shared-autofill"
    SHARED_STORAGE = "shared-storage"
    SHARED_STORAGE_SELECT_URL = "shared-storage-select-url"
    SMART_CARD = "smart-card"
    SPEAKER_SELECTION = "speaker-selection"
    STORAGE_ACCESS = "storage-access"
    SUB_APPS = "sub-apps"
    SUMMARIZER = "summarizer"
    SYNC_XHR = "sync-xhr"
    TRANSLATOR = "translator"
    UNLOAD = "unload"
    USB = "usb"
    USB_UNRESTRICTED = "usb-unrestricted"
    VERTICAL_SCROLL = "vertical-scroll"
    WEB_APP_INSTALLATION = "web-app-installation"
    WEB_PRINTING = "web-printing"
    WEB_SHARE = "web-share"
    WINDOW_MANAGEMENT = "window-management"
    WRITER = "writer"
    XR_SPATIAL_TRACKING = "xr-spatial-tracking"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PermissionsPolicyBlockReason(enum.Enum):
    '''
    Reason for a permissions policy feature to be disabled.
    '''
    HEADER = "Header"
    IFRAME_ATTRIBUTE = "IframeAttribute"
    IN_FENCED_FRAME_TREE = "InFencedFrameTree"
    IN_ISOLATED_APP = "InIsolatedApp"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PermissionsPolicyBlockLocator:
    frame_id: FrameId

    block_reason: PermissionsPolicyBlockReason

    def to_json(self):
        json = dict()
        json['frameId'] = self.frame_id.to_json()
        json['blockReason'] = self.block_reason.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            frame_id=FrameId.from_json(json['frameId']),
            block_reason=PermissionsPolicyBlockReason.from_json(json['blockReason']),
        )


@dataclass
class PermissionsPolicyFeatureState:
    feature: PermissionsPolicyFeature

    allowed: bool

    locator: typing.Optional[PermissionsPolicyBlockLocator] = None

    def to_json(self):
        json = dict()
        json['feature'] = self.feature.to_json()
        json['allowed'] = self.allowed
        if self.locator is not None:
            json['locator'] = self.locator.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            feature=PermissionsPolicyFeature.from_json(json['feature']),
            allowed=bool(json['allowed']),
            locator=PermissionsPolicyBlockLocator.from_json(json['locator']) if 'locator' in json else None,
        )


class OriginTrialTokenStatus(enum.Enum):
    '''
    Origin Trial(https://www.chromium.org/blink/origin-trials) support.
    Status for an Origin Trial token.
    '''
    SUCCESS = "Success"
    NOT_SUPPORTED = "NotSupported"
    INSECURE = "Insecure"
    EXPIRED = "Expired"
    WRONG_ORIGIN = "WrongOrigin"
    INVALID_SIGNATURE = "InvalidSignature"
    MALFORMED = "Malformed"
    WRONG_VERSION = "WrongVersion"
    FEATURE_DISABLED = "FeatureDisabled"
    TOKEN_DISABLED = "TokenDisabled"
    FEATURE_DISABLED_FOR_USER = "FeatureDisabledForUser"
    UNKNOWN_TRIAL = "UnknownTrial"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class OriginTrialStatus(enum.Enum):
    '''
    Status for an Origin Trial.
    '''
    ENABLED = "Enabled"
    VALID_TOKEN_NOT_PROVIDED = "ValidTokenNotProvided"
    OS_NOT_SUPPORTED = "OSNotSupported"
    TRIAL_NOT_ALLOWED = "TrialNotAllowed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class OriginTrialUsageRestriction(enum.Enum):
    NONE = "None"
    SUBSET = "Subset"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class OriginTrialToken:
    origin: str

    match_sub_domains: bool

    trial_name: str

    expiry_time: network.TimeSinceEpoch

    is_third_party: bool

    usage_restriction: OriginTrialUsageRestriction

    def to_json(self):
        json = dict()
        json['origin'] = self.origin
        json['matchSubDomains'] = self.match_sub_domains
        json['trialName'] = self.trial_name
        json['expiryTime'] = self.expiry_time.to_json()
        json['isThirdParty'] = self.is_third_party
        json['usageRestriction'] = self.usage_restriction.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            origin=str(json['origin']),
            match_sub_domains=bool(json['matchSubDomains']),
            trial_name=str(json['trialName']),
            expiry_time=network.TimeSinceEpoch.from_json(json['expiryTime']),
            is_third_party=bool(json['isThirdParty']),
            usage_restriction=OriginTrialUsageRestriction.from_json(json['usageRestriction']),
        )


@dataclass
class OriginTrialTokenWithStatus:
    raw_token_text: str

    status: OriginTrialTokenStatus

    #: ``parsedToken`` is present only when the token is extractable and
    #: parsable.
    parsed_token: typing.Optional[OriginTrialToken] = None

    def to_json(self):
        json = dict()
        json['rawTokenText'] = self.raw_token_text
        json['status'] = self.status.to_json()
        if self.parsed_token is not None:
            json['parsedToken'] = self.parsed_token.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            raw_token_text=str(json['rawTokenText']),
            status=OriginTrialTokenStatus.from_json(json['status']),
            parsed_token=OriginTrialToken.from_json(json['parsedToken']) if 'parsedToken' in json else None,
        )


@dataclass
class OriginTrial:
    trial_name: str

    status: OriginTrialStatus

    tokens_with_status: typing.List[OriginTrialTokenWithStatus]

    def to_json(self):
        json = dict()
        json['trialName'] = self.trial_name
        json['status'] = self.status.to_json()
        json['tokensWithStatus'] = [i.to_json() for i in self.tokens_with_status]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            trial_name=str(json['trialName']),
            status=OriginTrialStatus.from_json(json['status']),
            tokens_with_status=[OriginTrialTokenWithStatus.from_json(i) for i in json['tokensWithStatus']],
        )


@dataclass
class SecurityOriginDetails:
    '''
    Additional information about the frame document's security origin.
    '''
    #: Indicates whether the frame document's security origin is one
    #: of the local hostnames (e.g. "localhost") or IP addresses (IPv4
    #: 127.0.0.0/8 or IPv6 ::1).
    is_localhost: bool

    def to_json(self):
        json = dict()
        json['isLocalhost'] = self.is_localhost
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            is_localhost=bool(json['isLocalhost']),
        )


@dataclass
class Frame:
    '''
    Information about the Frame on the page.
    '''
    #: Frame unique identifier.
    id_: FrameId

    #: Identifier of the loader associated with this frame.
    loader_id: network.LoaderId

    #: Frame document's URL without fragment.
    url: str

    #: Frame document's registered domain, taking the public suffixes list into account.
    #: Extracted from the Frame's url.
    #: Example URLs: http://www.google.com/file.html -> "google.com"
    #:               http://a.b.co.uk/file.html      -> "b.co.uk"
    domain_and_registry: str

    #: Frame document's security origin.
    security_origin: str

    #: Frame document's mimeType as determined by the browser.
    mime_type: str

    #: Indicates whether the main document is a secure context and explains why that is the case.
    secure_context_type: SecureContextType

    #: Indicates whether this is a cross origin isolated context.
    cross_origin_isolated_context_type: CrossOriginIsolatedContextType

    #: Indicated which gated APIs / features are available.
    gated_api_features: typing.List[GatedAPIFeatures]

    #: Parent frame identifier.
    parent_id: typing.Optional[FrameId] = None

    #: Frame's name as specified in the tag.
    name: typing.Optional[str] = None

    #: Frame document's URL fragment including the '#'.
    url_fragment: typing.Optional[str] = None

    #: Additional details about the frame document's security origin.
    security_origin_details: typing.Optional[SecurityOriginDetails] = None

    #: If the frame failed to load, this contains the URL that could not be loaded. Note that unlike url above, this URL may contain a fragment.
    unreachable_url: typing.Optional[str] = None

    #: Indicates whether this frame was tagged as an ad and why.
    ad_frame_status: typing.Optional[AdFrameStatus] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_.to_json()
        json['loaderId'] = self.loader_id.to_json()
        json['url'] = self.url
        json['domainAndRegistry'] = self.domain_and_registry
        json['securityOrigin'] = self.security_origin
        json['mimeType'] = self.mime_type
        json['secureContextType'] = self.secure_context_type.to_json()
        json['crossOriginIsolatedContextType'] = self.cross_origin_isolated_context_type.to_json()
        json['gatedAPIFeatures'] = [i.to_json() for i in self.gated_api_features]
        if self.parent_id is not None:
            json['parentId'] = self.parent_id.to_json()
        if self.name is not None:
            json['name'] = self.name
        if self.url_fragment is not None:
            json['urlFragment'] = self.url_fragment
        if self.security_origin_details is not None:
            json['securityOriginDetails'] = self.security_origin_details.to_json()
        if self.unreachable_url is not None:
            json['unreachableUrl'] = self.unreachable_url
        if self.ad_frame_status is not None:
            json['adFrameStatus'] = self.ad_frame_status.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=FrameId.from_json(json['id']),
            loader_id=network.LoaderId.from_json(json['loaderId']),
            url=str(json['url']),
            domain_and_registry=str(json['domainAndRegistry']),
            security_origin=str(json['securityOrigin']),
            mime_type=str(json['mimeType']),
            secure_context_type=SecureContextType.from_json(json['secureContextType']),
            cross_origin_isolated_context_type=CrossOriginIsolatedContextType.from_json(json['crossOriginIsolatedContextType']),
            gated_api_features=[GatedAPIFeatures.from_json(i) for i in json['gatedAPIFeatures']],
            parent_id=FrameId.from_json(json['parentId']) if 'parentId' in json else None,
            name=str(json['name']) if 'name' in json else None,
            url_fragment=str(json['urlFragment']) if 'urlFragment' in json else None,
            security_origin_details=SecurityOriginDetails.from_json(json['securityOriginDetails']) if 'securityOriginDetails' in json else None,
            unreachable_url=str(json['unreachableUrl']) if 'unreachableUrl' in json else None,
            ad_frame_status=AdFrameStatus.from_json(json['adFrameStatus']) if 'adFrameStatus' in json else None,
        )


@dataclass
class FrameResource:
    '''
    Information about the Resource on the page.
    '''
    #: Resource URL.
    url: str

    #: Type of this resource.
    type_: network.ResourceType

    #: Resource mimeType as determined by the browser.
    mime_type: str

    #: last-modified timestamp as reported by server.
    last_modified: typing.Optional[network.TimeSinceEpoch] = None

    #: Resource content size.
    content_size: typing.Optional[float] = None

    #: True if the resource failed to load.
    failed: typing.Optional[bool] = None

    #: True if the resource was canceled during loading.
    canceled: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['type'] = self.type_.to_json()
        json['mimeType'] = self.mime_type
        if self.last_modified is not None:
            json['lastModified'] = self.last_modified.to_json()
        if self.content_size is not None:
            json['contentSize'] = self.content_size
        if self.failed is not None:
            json['failed'] = self.failed
        if self.canceled is not None:
            json['canceled'] = self.canceled
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            type_=network.ResourceType.from_json(json['type']),
            mime_type=str(json['mimeType']),
            last_modified=network.TimeSinceEpoch.from_json(json['lastModified']) if 'lastModified' in json else None,
            content_size=float(json['contentSize']) if 'contentSize' in json else None,
            failed=bool(json['failed']) if 'failed' in json else None,
            canceled=bool(json['canceled']) if 'canceled' in json else None,
        )


@dataclass
class FrameResourceTree:
    '''
    Information about the Frame hierarchy along with their cached resources.
    '''
    #: Frame information for this tree item.
    frame: Frame

    #: Information about frame resources.
    resources: typing.List[FrameResource]

    #: Child frames.
    child_frames: typing.Optional[typing.List[FrameResourceTree]] = None

    def to_json(self):
        json = dict()
        json['frame'] = self.frame.to_json()
        json['resources'] = [i.to_json() for i in self.resources]
        if self.child_frames is not None:
            json['childFrames'] = [i.to_json() for i in self.child_frames]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            frame=Frame.from_json(json['frame']),
            resources=[FrameResource.from_json(i) for i in json['resources']],
            child_frames=[FrameResourceTree.from_json(i) for i in json['childFrames']] if 'childFrames' in json else None,
        )


@dataclass
class FrameTree:
    '''
    Information about the Frame hierarchy.
    '''
    #: Frame information for this tree item.
    frame: Frame

    #: Child frames.
    child_frames: typing.Optional[typing.List[FrameTree]] = None

    def to_json(self):
        json = dict()
        json['frame'] = self.frame.to_json()
        if self.child_frames is not None:
            json['childFrames'] = [i.to_json() for i in self.child_frames]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            frame=Frame.from_json(json['frame']),
            child_frames=[FrameTree.from_json(i) for i in json['childFrames']] if 'childFrames' in json else None,
        )


class ScriptIdentifier(str):
    '''
    Unique script identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> ScriptIdentifier:
        return cls(json)

    def __repr__(self):
        return 'ScriptIdentifier({})'.format(super().__repr__())


class TransitionType(enum.Enum):
    '''
    Transition type.
    '''
    LINK = "link"
    TYPED = "typed"
    ADDRESS_BAR = "address_bar"
    AUTO_BOOKMARK = "auto_bookmark"
    AUTO_SUBFRAME = "auto_subframe"
    MANUAL_SUBFRAME = "manual_subframe"
    GENERATED = "generated"
    AUTO_TOPLEVEL = "auto_toplevel"
    FORM_SUBMIT = "form_submit"
    RELOAD = "reload"
    KEYWORD = "keyword"
    KEYWORD_GENERATED = "keyword_generated"
    OTHER = "other"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class NavigationEntry:
    '''
    Navigation history entry.
    '''
    #: Unique id of the navigation history entry.
    id_: int

    #: URL of the navigation history entry.
    url: str

    #: URL that the user typed in the url bar.
    user_typed_url: str

    #: Title of the navigation history entry.
    title: str

    #: Transition type.
    transition_type: TransitionType

    def to_json(self):
        json = dict()
        json['id'] = self.id_
        json['url'] = self.url
        json['userTypedURL'] = self.user_typed_url
        json['title'] = self.title
        json['transitionType'] = self.transition_type.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=int(json['id']),
            url=str(json['url']),
            user_typed_url=str(json['userTypedURL']),
            title=str(json['title']),
            transition_type=TransitionType.from_json(json['transitionType']),
        )


@dataclass
class ScreencastFrameMetadata:
    '''
    Screencast frame metadata.
    '''
    #: Top offset in DIP.
    offset_top: float

    #: Page scale factor.
    page_scale_factor: float

    #: Device screen width in DIP.
    device_width: float

    #: Device screen height in DIP.
    device_height: float

    #: Position of horizontal scroll in CSS pixels.
    scroll_offset_x: float

    #: Position of vertical scroll in CSS pixels.
    scroll_offset_y: float

    #: Frame swap timestamp.
    timestamp: typing.Optional[network.TimeSinceEpoch] = None

    def to_json(self):
        json = dict()
        json['offsetTop'] = self.offset_top
        json['pageScaleFactor'] = self.page_scale_factor
        json['deviceWidth'] = self.device_width
        json['deviceHeight'] = self.device_height
        json['scrollOffsetX'] = self.scroll_offset_x
        json['scrollOffsetY'] = self.scroll_offset_y
        if self.timestamp is not None:
            json['timestamp'] = self.timestamp.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            offset_top=float(json['offsetTop']),
            page_scale_factor=float(json['pageScaleFactor']),
            device_width=float(json['deviceWidth']),
            device_height=float(json['deviceHeight']),
            scroll_offset_x=float(json['scrollOffsetX']),
            scroll_offset_y=float(json['scrollOffsetY']),
            timestamp=network.TimeSinceEpoch.from_json(json['timestamp']) if 'timestamp' in json else None,
        )


class DialogType(enum.Enum):
    '''
    Javascript dialog type.
    '''
    ALERT = "alert"
    CONFIRM = "confirm"
    PROMPT = "prompt"
    BEFOREUNLOAD = "beforeunload"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AppManifestError:
    '''
    Error while paring app manifest.
    '''
    #: Error message.
    message: str

    #: If critical, this is a non-recoverable parse error.
    critical: int

    #: Error line.
    line: int

    #: Error column.
    column: int

    def to_json(self):
        json = dict()
        json['message'] = self.message
        json['critical'] = self.critical
        json['line'] = self.line
        json['column'] = self.column
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            message=str(json['message']),
            critical=int(json['critical']),
            line=int(json['line']),
            column=int(json['column']),
        )


@dataclass
class AppManifestParsedProperties:
    '''
    Parsed app manifest properties.
    '''
    #: Computed scope value
    scope: str

    def to_json(self):
        json = dict()
        json['scope'] = self.scope
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            scope=str(json['scope']),
        )


@dataclass
class LayoutViewport:
    '''
    Layout viewport position and dimensions.
    '''
    #: Horizontal offset relative to the document (CSS pixels).
    page_x: int

    #: Vertical offset relative to the document (CSS pixels).
    page_y: int

    #: Width (CSS pixels), excludes scrollbar if present.
    client_width: int

    #: Height (CSS pixels), excludes scrollbar if present.
    client_height: int

    def to_json(self):
        json = dict()
        json['pageX'] = self.page_x
        json['pageY'] = self.page_y
        json['clientWidth'] = self.client_width
        json['clientHeight'] = self.client_height
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            page_x=int(json['pageX']),
            page_y=int(json['pageY']),
            client_width=int(json['clientWidth']),
            client_height=int(json['clientHeight']),
        )


@dataclass
class VisualViewport:
    '''
    Visual viewport position, dimensions, and scale.
    '''
    #: Horizontal offset relative to the layout viewport (CSS pixels).
    offset_x: float

    #: Vertical offset relative to the layout viewport (CSS pixels).
    offset_y: float

    #: Horizontal offset relative to the document (CSS pixels).
    page_x: float

    #: Vertical offset relative to the document (CSS pixels).
    page_y: float

    #: Width (CSS pixels), excludes scrollbar if present.
    client_width: float

    #: Height (CSS pixels), excludes scrollbar if present.
    client_height: float

    #: Scale relative to the ideal viewport (size at width=device-width).
    scale: float

    #: Page zoom factor (CSS to device independent pixels ratio).
    zoom: typing.Optional[float] = None

    def to_json(self):
        json = dict()
        json['offsetX'] = self.offset_x
        json['offsetY'] = self.offset_y
        json['pageX'] = self.page_x
        json['pageY'] = self.page_y
        json['clientWidth'] = self.client_width
        json['clientHeight'] = self.client_height
        json['scale'] = self.scale
        if self.zoom is not None:
            json['zoom'] = self.zoom
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            offset_x=float(json['offsetX']),
            offset_y=float(json['offsetY']),
            page_x=float(json['pageX']),
            page_y=float(json['pageY']),
            client_width=float(json['clientWidth']),
            client_height=float(json['clientHeight']),
            scale=float(json['scale']),
            zoom=float(json['zoom']) if 'zoom' in json else None,
        )


@dataclass
class Viewport:
    '''
    Viewport for capturing screenshot.
    '''
    #: X offset in device independent pixels (dip).
    x: float

    #: Y offset in device independent pixels (dip).
    y: float

    #: Rectangle width in device independent pixels (dip).
    width: float

    #: Rectangle height in device independent pixels (dip).
    height: float

    #: Page scale factor.
    scale: float

    def to_json(self):
        json = dict()
        json['x'] = self.x
        json['y'] = self.y
        json['width'] = self.width
        json['height'] = self.height
        json['scale'] = self.scale
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            x=float(json['x']),
            y=float(json['y']),
            width=float(json['width']),
            height=float(json['height']),
            scale=float(json['scale']),
        )


@dataclass
class FontFamilies:
    '''
    Generic font families collection.
    '''
    #: The standard font-family.
    standard: typing.Optional[str] = None

    #: The fixed font-family.
    fixed: typing.Optional[str] = None

    #: The serif font-family.
    serif: typing.Optional[str] = None

    #: The sansSerif font-family.
    sans_serif: typing.Optional[str] = None

    #: The cursive font-family.
    cursive: typing.Optional[str] = None

    #: The fantasy font-family.
    fantasy: typing.Optional[str] = None

    #: The math font-family.
    math: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        if self.standard is not None:
            json['standard'] = self.standard
        if self.fixed is not None:
            json['fixed'] = self.fixed
        if self.serif is not None:
            json['serif'] = self.serif
        if self.sans_serif is not None:
            json['sansSerif'] = self.sans_serif
        if self.cursive is not None:
            json['cursive'] = self.cursive
        if self.fantasy is not None:
            json['fantasy'] = self.fantasy
        if self.math is not None:
            json['math'] = self.math
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            standard=str(json['standard']) if 'standard' in json else None,
            fixed=str(json['fixed']) if 'fixed' in json else None,
            serif=str(json['serif']) if 'serif' in json else None,
            sans_serif=str(json['sansSerif']) if 'sansSerif' in json else None,
            cursive=str(json['cursive']) if 'cursive' in json else None,
            fantasy=str(json['fantasy']) if 'fantasy' in json else None,
            math=str(json['math']) if 'math' in json else None,
        )


@dataclass
class ScriptFontFamilies:
    '''
    Font families collection for a script.
    '''
    #: Name of the script which these font families are defined for.
    script: str

    #: Generic font families collection for the script.
    font_families: FontFamilies

    def to_json(self):
        json = dict()
        json['script'] = self.script
        json['fontFamilies'] = self.font_families.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script=str(json['script']),
            font_families=FontFamilies.from_json(json['fontFamilies']),
        )


@dataclass
class FontSizes:
    '''
    Default font sizes.
    '''
    #: Default standard font size.
    standard: typing.Optional[int] = None

    #: Default fixed font size.
    fixed: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        if self.standard is not None:
            json['standard'] = self.standard
        if self.fixed is not None:
            json['fixed'] = self.fixed
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            standard=int(json['standard']) if 'standard' in json else None,
            fixed=int(json['fixed']) if 'fixed' in json else None,
        )


class ClientNavigationReason(enum.Enum):
    ANCHOR_CLICK = "anchorClick"
    FORM_SUBMISSION_GET = "formSubmissionGet"
    FORM_SUBMISSION_POST = "formSubmissionPost"
    HTTP_HEADER_REFRESH = "httpHeaderRefresh"
    INITIAL_FRAME_NAVIGATION = "initialFrameNavigation"
    META_TAG_REFRESH = "metaTagRefresh"
    OTHER = "other"
    PAGE_BLOCK_INTERSTITIAL = "pageBlockInterstitial"
    RELOAD = "reload"
    SCRIPT_INITIATED = "scriptInitiated"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ClientNavigationDisposition(enum.Enum):
    CURRENT_TAB = "currentTab"
    NEW_TAB = "newTab"
    NEW_WINDOW = "newWindow"
    DOWNLOAD = "download"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class InstallabilityErrorArgument:
    #: Argument name (e.g. name:'minimum-icon-size-in-pixels').
    name: str

    #: Argument value (e.g. value:'64').
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
class InstallabilityError:
    '''
    The installability error
    '''
    #: The error id (e.g. 'manifest-missing-suitable-icon').
    error_id: str

    #: The list of error arguments (e.g. {name:'minimum-icon-size-in-pixels', value:'64'}).
    error_arguments: typing.List[InstallabilityErrorArgument]

    def to_json(self):
        json = dict()
        json['errorId'] = self.error_id
        json['errorArguments'] = [i.to_json() for i in self.error_arguments]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error_id=str(json['errorId']),
            error_arguments=[InstallabilityErrorArgument.from_json(i) for i in json['errorArguments']],
        )


class ReferrerPolicy(enum.Enum):
    '''
    The referring-policy used for the navigation.
    '''
    NO_REFERRER = "noReferrer"
    NO_REFERRER_WHEN_DOWNGRADE = "noReferrerWhenDowngrade"
    ORIGIN = "origin"
    ORIGIN_WHEN_CROSS_ORIGIN = "originWhenCrossOrigin"
    SAME_ORIGIN = "sameOrigin"
    STRICT_ORIGIN = "strictOrigin"
    STRICT_ORIGIN_WHEN_CROSS_ORIGIN = "strictOriginWhenCrossOrigin"
    UNSAFE_URL = "unsafeUrl"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CompilationCacheParams:
    '''
    Per-script compilation cache parameters for ``Page.produceCompilationCache``
    '''
    #: The URL of the script to produce a compilation cache entry for.
    url: str

    #: A hint to the backend whether eager compilation is recommended.
    #: (the actual compilation mode used is upon backend discretion).
    eager: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        if self.eager is not None:
            json['eager'] = self.eager
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            eager=bool(json['eager']) if 'eager' in json else None,
        )


@dataclass
class FileFilter:
    name: typing.Optional[str] = None

    accepts: typing.Optional[typing.List[str]] = None

    def to_json(self):
        json = dict()
        if self.name is not None:
            json['name'] = self.name
        if self.accepts is not None:
            json['accepts'] = [i for i in self.accepts]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']) if 'name' in json else None,
            accepts=[str(i) for i in json['accepts']] if 'accepts' in json else None,
        )


@dataclass
class FileHandler:
    action: str

    name: str

    #: Won't repeat the enums, using string for easy comparison. Same as the
    #: other enums below.
    launch_type: str

    icons: typing.Optional[typing.List[ImageResource]] = None

    #: Mimic a map, name is the key, accepts is the value.
    accepts: typing.Optional[typing.List[FileFilter]] = None

    def to_json(self):
        json = dict()
        json['action'] = self.action
        json['name'] = self.name
        json['launchType'] = self.launch_type
        if self.icons is not None:
            json['icons'] = [i.to_json() for i in self.icons]
        if self.accepts is not None:
            json['accepts'] = [i.to_json() for i in self.accepts]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            action=str(json['action']),
            name=str(json['name']),
            launch_type=str(json['launchType']),
            icons=[ImageResource.from_json(i) for i in json['icons']] if 'icons' in json else None,
            accepts=[FileFilter.from_json(i) for i in json['accepts']] if 'accepts' in json else None,
        )


@dataclass
class ImageResource:
    '''
    The image definition used in both icon and screenshot.
    '''
    #: The src field in the definition, but changing to url in favor of
    #: consistency.
    url: str

    sizes: typing.Optional[str] = None

    type_: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        if self.sizes is not None:
            json['sizes'] = self.sizes
        if self.type_ is not None:
            json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            sizes=str(json['sizes']) if 'sizes' in json else None,
            type_=str(json['type']) if 'type' in json else None,
        )


@dataclass
class LaunchHandler:
    client_mode: str

    def to_json(self):
        json = dict()
        json['clientMode'] = self.client_mode
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            client_mode=str(json['clientMode']),
        )


@dataclass
class ProtocolHandler:
    protocol: str

    url: str

    def to_json(self):
        json = dict()
        json['protocol'] = self.protocol
        json['url'] = self.url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            protocol=str(json['protocol']),
            url=str(json['url']),
        )


@dataclass
class RelatedApplication:
    url: str

    id_: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        if self.id_ is not None:
            json['id'] = self.id_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            id_=str(json['id']) if 'id' in json else None,
        )


@dataclass
class ScopeExtension:
    #: Instead of using tuple, this field always returns the serialized string
    #: for easy understanding and comparison.
    origin: str

    has_origin_wildcard: bool

    def to_json(self):
        json = dict()
        json['origin'] = self.origin
        json['hasOriginWildcard'] = self.has_origin_wildcard
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            origin=str(json['origin']),
            has_origin_wildcard=bool(json['hasOriginWildcard']),
        )


@dataclass
class Screenshot:
    image: ImageResource

    form_factor: str

    label: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['image'] = self.image.to_json()
        json['formFactor'] = self.form_factor
        if self.label is not None:
            json['label'] = self.label
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            image=ImageResource.from_json(json['image']),
            form_factor=str(json['formFactor']),
            label=str(json['label']) if 'label' in json else None,
        )


@dataclass
class ShareTarget:
    action: str

    method: str

    enctype: str

    #: Embed the ShareTargetParams
    title: typing.Optional[str] = None

    text: typing.Optional[str] = None

    url: typing.Optional[str] = None

    files: typing.Optional[typing.List[FileFilter]] = None

    def to_json(self):
        json = dict()
        json['action'] = self.action
        json['method'] = self.method
        json['enctype'] = self.enctype
        if self.title is not None:
            json['title'] = self.title
        if self.text is not None:
            json['text'] = self.text
        if self.url is not None:
            json['url'] = self.url
        if self.files is not None:
            json['files'] = [i.to_json() for i in self.files]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            action=str(json['action']),
            method=str(json['method']),
            enctype=str(json['enctype']),
            title=str(json['title']) if 'title' in json else None,
            text=str(json['text']) if 'text' in json else None,
            url=str(json['url']) if 'url' in json else None,
            files=[FileFilter.from_json(i) for i in json['files']] if 'files' in json else None,
        )


@dataclass
class Shortcut:
    name: str

    url: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['url'] = self.url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            url=str(json['url']),
        )


@dataclass
class WebAppManifest:
    background_color: typing.Optional[str] = None

    #: The extra description provided by the manifest.
    description: typing.Optional[str] = None

    dir_: typing.Optional[str] = None

    display: typing.Optional[str] = None

    #: The overrided display mode controlled by the user.
    display_overrides: typing.Optional[typing.List[str]] = None

    #: The handlers to open files.
    file_handlers: typing.Optional[typing.List[FileHandler]] = None

    icons: typing.Optional[typing.List[ImageResource]] = None

    id_: typing.Optional[str] = None

    lang: typing.Optional[str] = None

    #: TODO(crbug.com/1231886): This field is non-standard and part of a Chrome
    #: experiment. See:
    #: https://github.com/WICG/web-app-launch/blob/main/launch_handler.md
    launch_handler: typing.Optional[LaunchHandler] = None

    name: typing.Optional[str] = None

    orientation: typing.Optional[str] = None

    prefer_related_applications: typing.Optional[bool] = None

    #: The handlers to open protocols.
    protocol_handlers: typing.Optional[typing.List[ProtocolHandler]] = None

    related_applications: typing.Optional[typing.List[RelatedApplication]] = None

    scope: typing.Optional[str] = None

    #: Non-standard, see
    #: https://github.com/WICG/manifest-incubations/blob/gh-pages/scope_extensions-explainer.md
    scope_extensions: typing.Optional[typing.List[ScopeExtension]] = None

    #: The screenshots used by chromium.
    screenshots: typing.Optional[typing.List[Screenshot]] = None

    share_target: typing.Optional[ShareTarget] = None

    short_name: typing.Optional[str] = None

    shortcuts: typing.Optional[typing.List[Shortcut]] = None

    start_url: typing.Optional[str] = None

    theme_color: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        if self.background_color is not None:
            json['backgroundColor'] = self.background_color
        if self.description is not None:
            json['description'] = self.description
        if self.dir_ is not None:
            json['dir'] = self.dir_
        if self.display is not None:
            json['display'] = self.display
        if self.display_overrides is not None:
            json['displayOverrides'] = [i for i in self.display_overrides]
        if self.file_handlers is not None:
            json['fileHandlers'] = [i.to_json() for i in self.file_handlers]
        if self.icons is not None:
            json['icons'] = [i.to_json() for i in self.icons]
        if self.id_ is not None:
            json['id'] = self.id_
        if self.lang is not None:
            json['lang'] = self.lang
        if self.launch_handler is not None:
            json['launchHandler'] = self.launch_handler.to_json()
        if self.name is not None:
            json['name'] = self.name
        if self.orientation is not None:
            json['orientation'] = self.orientation
        if self.prefer_related_applications is not None:
            json['preferRelatedApplications'] = self.prefer_related_applications
        if self.protocol_handlers is not None:
            json['protocolHandlers'] = [i.to_json() for i in self.protocol_handlers]
        if self.related_applications is not None:
            json['relatedApplications'] = [i.to_json() for i in self.related_applications]
        if self.scope is not None:
            json['scope'] = self.scope
        if self.scope_extensions is not None:
            json['scopeExtensions'] = [i.to_json() for i in self.scope_extensions]
        if self.screenshots is not None:
            json['screenshots'] = [i.to_json() for i in self.screenshots]
        if self.share_target is not None:
            json['shareTarget'] = self.share_target.to_json()
        if self.short_name is not None:
            json['shortName'] = self.short_name
        if self.shortcuts is not None:
            json['shortcuts'] = [i.to_json() for i in self.shortcuts]
        if self.start_url is not None:
            json['startUrl'] = self.start_url
        if self.theme_color is not None:
            json['themeColor'] = self.theme_color
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            background_color=str(json['backgroundColor']) if 'backgroundColor' in json else None,
            description=str(json['description']) if 'description' in json else None,
            dir_=str(json['dir']) if 'dir' in json else None,
            display=str(json['display']) if 'display' in json else None,
            display_overrides=[str(i) for i in json['displayOverrides']] if 'displayOverrides' in json else None,
            file_handlers=[FileHandler.from_json(i) for i in json['fileHandlers']] if 'fileHandlers' in json else None,
            icons=[ImageResource.from_json(i) for i in json['icons']] if 'icons' in json else None,
            id_=str(json['id']) if 'id' in json else None,
            lang=str(json['lang']) if 'lang' in json else None,
            launch_handler=LaunchHandler.from_json(json['launchHandler']) if 'launchHandler' in json else None,
            name=str(json['name']) if 'name' in json else None,
            orientation=str(json['orientation']) if 'orientation' in json else None,
            prefer_related_applications=bool(json['preferRelatedApplications']) if 'preferRelatedApplications' in json else None,
            protocol_handlers=[ProtocolHandler.from_json(i) for i in json['protocolHandlers']] if 'protocolHandlers' in json else None,
            related_applications=[RelatedApplication.from_json(i) for i in json['relatedApplications']] if 'relatedApplications' in json else None,
            scope=str(json['scope']) if 'scope' in json else None,
            scope_extensions=[ScopeExtension.from_json(i) for i in json['scopeExtensions']] if 'scopeExtensions' in json else None,
            screenshots=[Screenshot.from_json(i) for i in json['screenshots']] if 'screenshots' in json else None,
            share_target=ShareTarget.from_json(json['shareTarget']) if 'shareTarget' in json else None,
            short_name=str(json['shortName']) if 'shortName' in json else None,
            shortcuts=[Shortcut.from_json(i) for i in json['shortcuts']] if 'shortcuts' in json else None,
            start_url=str(json['startUrl']) if 'startUrl' in json else None,
            theme_color=str(json['themeColor']) if 'themeColor' in json else None,
        )


class AutoResponseMode(enum.Enum):
    '''
    Enum of possible auto-response for permission / prompt dialogs.
    '''
    NONE = "none"
    AUTO_ACCEPT = "autoAccept"
    AUTO_REJECT = "autoReject"
    AUTO_OPT_OUT = "autoOptOut"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class NavigationType(enum.Enum):
    '''
    The type of a frameNavigated event.
    '''
    NAVIGATION = "Navigation"
    BACK_FORWARD_CACHE_RESTORE = "BackForwardCacheRestore"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class BackForwardCacheNotRestoredReason(enum.Enum):
    '''
    List of not restored reasons for back-forward cache.
    '''
    NOT_PRIMARY_MAIN_FRAME = "NotPrimaryMainFrame"
    BACK_FORWARD_CACHE_DISABLED = "BackForwardCacheDisabled"
    RELATED_ACTIVE_CONTENTS_EXIST = "RelatedActiveContentsExist"
    HTTP_STATUS_NOT_OK = "HTTPStatusNotOK"
    SCHEME_NOT_HTTP_OR_HTTPS = "SchemeNotHTTPOrHTTPS"
    LOADING = "Loading"
    WAS_GRANTED_MEDIA_ACCESS = "WasGrantedMediaAccess"
    DISABLE_FOR_RENDER_FRAME_HOST_CALLED = "DisableForRenderFrameHostCalled"
    DOMAIN_NOT_ALLOWED = "DomainNotAllowed"
    HTTP_METHOD_NOT_GET = "HTTPMethodNotGET"
    SUBFRAME_IS_NAVIGATING = "SubframeIsNavigating"
    TIMEOUT = "Timeout"
    CACHE_LIMIT = "CacheLimit"
    JAVA_SCRIPT_EXECUTION = "JavaScriptExecution"
    RENDERER_PROCESS_KILLED = "RendererProcessKilled"
    RENDERER_PROCESS_CRASHED = "RendererProcessCrashed"
    SCHEDULER_TRACKED_FEATURE_USED = "SchedulerTrackedFeatureUsed"
    CONFLICTING_BROWSING_INSTANCE = "ConflictingBrowsingInstance"
    CACHE_FLUSHED = "CacheFlushed"
    SERVICE_WORKER_VERSION_ACTIVATION = "ServiceWorkerVersionActivation"
    SESSION_RESTORED = "SessionRestored"
    SERVICE_WORKER_POST_MESSAGE = "ServiceWorkerPostMessage"
    ENTERED_BACK_FORWARD_CACHE_BEFORE_SERVICE_WORKER_HOST_ADDED = "EnteredBackForwardCacheBeforeServiceWorkerHostAdded"
    RENDER_FRAME_HOST_REUSED_SAME_SITE = "RenderFrameHostReused_SameSite"
    RENDER_FRAME_HOST_REUSED_CROSS_SITE = "RenderFrameHostReused_CrossSite"
    SERVICE_WORKER_CLAIM = "ServiceWorkerClaim"
    IGNORE_EVENT_AND_EVICT = "IgnoreEventAndEvict"
    HAVE_INNER_CONTENTS = "HaveInnerContents"
    TIMEOUT_PUTTING_IN_CACHE = "TimeoutPuttingInCache"
    BACK_FORWARD_CACHE_DISABLED_BY_LOW_MEMORY = "BackForwardCacheDisabledByLowMemory"
    BACK_FORWARD_CACHE_DISABLED_BY_COMMAND_LINE = "BackForwardCacheDisabledByCommandLine"
    NETWORK_REQUEST_DATAPIPE_DRAINED_AS_BYTES_CONSUMER = "NetworkRequestDatapipeDrainedAsBytesConsumer"
    NETWORK_REQUEST_REDIRECTED = "NetworkRequestRedirected"
    NETWORK_REQUEST_TIMEOUT = "NetworkRequestTimeout"
    NETWORK_EXCEEDS_BUFFER_LIMIT = "NetworkExceedsBufferLimit"
    NAVIGATION_CANCELLED_WHILE_RESTORING = "NavigationCancelledWhileRestoring"
    NOT_MOST_RECENT_NAVIGATION_ENTRY = "NotMostRecentNavigationEntry"
    BACK_FORWARD_CACHE_DISABLED_FOR_PRERENDER = "BackForwardCacheDisabledForPrerender"
    USER_AGENT_OVERRIDE_DIFFERS = "UserAgentOverrideDiffers"
    FOREGROUND_CACHE_LIMIT = "ForegroundCacheLimit"
    BROWSING_INSTANCE_NOT_SWAPPED = "BrowsingInstanceNotSwapped"
    BACK_FORWARD_CACHE_DISABLED_FOR_DELEGATE = "BackForwardCacheDisabledForDelegate"
    UNLOAD_HANDLER_EXISTS_IN_MAIN_FRAME = "UnloadHandlerExistsInMainFrame"
    UNLOAD_HANDLER_EXISTS_IN_SUB_FRAME = "UnloadHandlerExistsInSubFrame"
    SERVICE_WORKER_UNREGISTRATION = "ServiceWorkerUnregistration"
    CACHE_CONTROL_NO_STORE = "CacheControlNoStore"
    CACHE_CONTROL_NO_STORE_COOKIE_MODIFIED = "CacheControlNoStoreCookieModified"
    CACHE_CONTROL_NO_STORE_HTTP_ONLY_COOKIE_MODIFIED = "CacheControlNoStoreHTTPOnlyCookieModified"
    NO_RESPONSE_HEAD = "NoResponseHead"
    UNKNOWN = "Unknown"
    ACTIVATION_NAVIGATIONS_DISALLOWED_FOR_BUG1234857 = "ActivationNavigationsDisallowedForBug1234857"
    ERROR_DOCUMENT = "ErrorDocument"
    FENCED_FRAMES_EMBEDDER = "FencedFramesEmbedder"
    COOKIE_DISABLED = "CookieDisabled"
    HTTP_AUTH_REQUIRED = "HTTPAuthRequired"
    COOKIE_FLUSHED = "CookieFlushed"
    BROADCAST_CHANNEL_ON_MESSAGE = "BroadcastChannelOnMessage"
    WEB_VIEW_SETTINGS_CHANGED = "WebViewSettingsChanged"
    WEB_VIEW_JAVA_SCRIPT_OBJECT_CHANGED = "WebViewJavaScriptObjectChanged"
    WEB_VIEW_MESSAGE_LISTENER_INJECTED = "WebViewMessageListenerInjected"
    WEB_VIEW_SAFE_BROWSING_ALLOWLIST_CHANGED = "WebViewSafeBrowsingAllowlistChanged"
    WEB_VIEW_DOCUMENT_START_JAVASCRIPT_CHANGED = "WebViewDocumentStartJavascriptChanged"
    WEB_SOCKET = "WebSocket"
    WEB_TRANSPORT = "WebTransport"
    WEB_RTC = "WebRTC"
    MAIN_RESOURCE_HAS_CACHE_CONTROL_NO_STORE = "MainResourceHasCacheControlNoStore"
    MAIN_RESOURCE_HAS_CACHE_CONTROL_NO_CACHE = "MainResourceHasCacheControlNoCache"
    SUBRESOURCE_HAS_CACHE_CONTROL_NO_STORE = "SubresourceHasCacheControlNoStore"
    SUBRESOURCE_HAS_CACHE_CONTROL_NO_CACHE = "SubresourceHasCacheControlNoCache"
    CONTAINS_PLUGINS = "ContainsPlugins"
    DOCUMENT_LOADED = "DocumentLoaded"
    OUTSTANDING_NETWORK_REQUEST_OTHERS = "OutstandingNetworkRequestOthers"
    REQUESTED_MIDI_PERMISSION = "RequestedMIDIPermission"
    REQUESTED_AUDIO_CAPTURE_PERMISSION = "RequestedAudioCapturePermission"
    REQUESTED_VIDEO_CAPTURE_PERMISSION = "RequestedVideoCapturePermission"
    REQUESTED_BACK_FORWARD_CACHE_BLOCKED_SENSORS = "RequestedBackForwardCacheBlockedSensors"
    REQUESTED_BACKGROUND_WORK_PERMISSION = "RequestedBackgroundWorkPermission"
    BROADCAST_CHANNEL = "BroadcastChannel"
    WEB_XR = "WebXR"
    SHARED_WORKER = "SharedWorker"
    WEB_LOCKS = "WebLocks"
    WEB_HID = "WebHID"
    WEB_SHARE = "WebShare"
    REQUESTED_STORAGE_ACCESS_GRANT = "RequestedStorageAccessGrant"
    WEB_NFC = "WebNfc"
    OUTSTANDING_NETWORK_REQUEST_FETCH = "OutstandingNetworkRequestFetch"
    OUTSTANDING_NETWORK_REQUEST_XHR = "OutstandingNetworkRequestXHR"
    APP_BANNER = "AppBanner"
    PRINTING = "Printing"
    WEB_DATABASE = "WebDatabase"
    PICTURE_IN_PICTURE = "PictureInPicture"
    SPEECH_RECOGNIZER = "SpeechRecognizer"
    IDLE_MANAGER = "IdleManager"
    PAYMENT_MANAGER = "PaymentManager"
    SPEECH_SYNTHESIS = "SpeechSynthesis"
    KEYBOARD_LOCK = "KeyboardLock"
    WEB_OTP_SERVICE = "WebOTPService"
    OUTSTANDING_NETWORK_REQUEST_DIRECT_SOCKET = "OutstandingNetworkRequestDirectSocket"
    INJECTED_JAVASCRIPT = "InjectedJavascript"
    INJECTED_STYLE_SHEET = "InjectedStyleSheet"
    KEEPALIVE_REQUEST = "KeepaliveRequest"
    INDEXED_DB_EVENT = "IndexedDBEvent"
    DUMMY = "Dummy"
    JS_NETWORK_REQUEST_RECEIVED_CACHE_CONTROL_NO_STORE_RESOURCE = "JsNetworkRequestReceivedCacheControlNoStoreResource"
    WEB_RTC_STICKY = "WebRTCSticky"
    WEB_TRANSPORT_STICKY = "WebTransportSticky"
    WEB_SOCKET_STICKY = "WebSocketSticky"
    SMART_CARD = "SmartCard"
    LIVE_MEDIA_STREAM_TRACK = "LiveMediaStreamTrack"
    UNLOAD_HANDLER = "UnloadHandler"
    PARSER_ABORTED = "ParserAborted"
    CONTENT_SECURITY_HANDLER = "ContentSecurityHandler"
    CONTENT_WEB_AUTHENTICATION_API = "ContentWebAuthenticationAPI"
    CONTENT_FILE_CHOOSER = "ContentFileChooser"
    CONTENT_SERIAL = "ContentSerial"
    CONTENT_FILE_SYSTEM_ACCESS = "ContentFileSystemAccess"
    CONTENT_MEDIA_DEVICES_DISPATCHER_HOST = "ContentMediaDevicesDispatcherHost"
    CONTENT_WEB_BLUETOOTH = "ContentWebBluetooth"
    CONTENT_WEB_USB = "ContentWebUSB"
    CONTENT_MEDIA_SESSION_SERVICE = "ContentMediaSessionService"
    CONTENT_SCREEN_READER = "ContentScreenReader"
    CONTENT_DISCARDED = "ContentDiscarded"
    EMBEDDER_POPUP_BLOCKER_TAB_HELPER = "EmbedderPopupBlockerTabHelper"
    EMBEDDER_SAFE_BROWSING_TRIGGERED_POPUP_BLOCKER = "EmbedderSafeBrowsingTriggeredPopupBlocker"
    EMBEDDER_SAFE_BROWSING_THREAT_DETAILS = "EmbedderSafeBrowsingThreatDetails"
    EMBEDDER_APP_BANNER_MANAGER = "EmbedderAppBannerManager"
    EMBEDDER_DOM_DISTILLER_VIEWER_SOURCE = "EmbedderDomDistillerViewerSource"
    EMBEDDER_DOM_DISTILLER_SELF_DELETING_REQUEST_DELEGATE = "EmbedderDomDistillerSelfDeletingRequestDelegate"
    EMBEDDER_OOM_INTERVENTION_TAB_HELPER = "EmbedderOomInterventionTabHelper"
    EMBEDDER_OFFLINE_PAGE = "EmbedderOfflinePage"
    EMBEDDER_CHROME_PASSWORD_MANAGER_CLIENT_BIND_CREDENTIAL_MANAGER = "EmbedderChromePasswordManagerClientBindCredentialManager"
    EMBEDDER_PERMISSION_REQUEST_MANAGER = "EmbedderPermissionRequestManager"
    EMBEDDER_MODAL_DIALOG = "EmbedderModalDialog"
    EMBEDDER_EXTENSIONS = "EmbedderExtensions"
    EMBEDDER_EXTENSION_MESSAGING = "EmbedderExtensionMessaging"
    EMBEDDER_EXTENSION_MESSAGING_FOR_OPEN_PORT = "EmbedderExtensionMessagingForOpenPort"
    EMBEDDER_EXTENSION_SENT_MESSAGE_TO_CACHED_FRAME = "EmbedderExtensionSentMessageToCachedFrame"
    REQUESTED_BY_WEB_VIEW_CLIENT = "RequestedByWebViewClient"
    POST_MESSAGE_BY_WEB_VIEW_CLIENT = "PostMessageByWebViewClient"
    CACHE_CONTROL_NO_STORE_DEVICE_BOUND_SESSION_TERMINATED = "CacheControlNoStoreDeviceBoundSessionTerminated"
    CACHE_LIMIT_PRUNED_ON_MODERATE_MEMORY_PRESSURE = "CacheLimitPrunedOnModerateMemoryPressure"
    CACHE_LIMIT_PRUNED_ON_CRITICAL_MEMORY_PRESSURE = "CacheLimitPrunedOnCriticalMemoryPressure"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class BackForwardCacheNotRestoredReasonType(enum.Enum):
    '''
    Types of not restored reasons for back-forward cache.
    '''
    SUPPORT_PENDING = "SupportPending"
    PAGE_SUPPORT_NEEDED = "PageSupportNeeded"
    CIRCUMSTANTIAL = "Circumstantial"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class BackForwardCacheBlockingDetails:
    #: Line number in the script (0-based).
    line_number: int

    #: Column number in the script (0-based).
    column_number: int

    #: Url of the file where blockage happened. Optional because of tests.
    url: typing.Optional[str] = None

    #: Function name where blockage happened. Optional because of anonymous functions and tests.
    function: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        if self.url is not None:
            json['url'] = self.url
        if self.function is not None:
            json['function'] = self.function
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
            url=str(json['url']) if 'url' in json else None,
            function=str(json['function']) if 'function' in json else None,
        )


@dataclass
class BackForwardCacheNotRestoredExplanation:
    #: Type of the reason
    type_: BackForwardCacheNotRestoredReasonType

    #: Not restored reason
    reason: BackForwardCacheNotRestoredReason

    #: Context associated with the reason. The meaning of this context is
    #: dependent on the reason:
    #: - EmbedderExtensionSentMessageToCachedFrame: the extension ID.
    context: typing.Optional[str] = None

    details: typing.Optional[typing.List[BackForwardCacheBlockingDetails]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_.to_json()
        json['reason'] = self.reason.to_json()
        if self.context is not None:
            json['context'] = self.context
        if self.details is not None:
            json['details'] = [i.to_json() for i in self.details]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=BackForwardCacheNotRestoredReasonType.from_json(json['type']),
            reason=BackForwardCacheNotRestoredReason.from_json(json['reason']),
            context=str(json['context']) if 'context' in json else None,
            details=[BackForwardCacheBlockingDetails.from_json(i) for i in json['details']] if 'details' in json else None,
        )


@dataclass
class BackForwardCacheNotRestoredExplanationTree:
    #: URL of each frame
    url: str

    #: Not restored reasons of each frame
    explanations: typing.List[BackForwardCacheNotRestoredExplanation]

    #: Array of children frame
    children: typing.List[BackForwardCacheNotRestoredExplanationTree]

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['explanations'] = [i.to_json() for i in self.explanations]
        json['children'] = [i.to_json() for i in self.children]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            explanations=[BackForwardCacheNotRestoredExplanation.from_json(i) for i in json['explanations']],
            children=[BackForwardCacheNotRestoredExplanationTree.from_json(i) for i in json['children']],
        )


def add_script_to_evaluate_on_load(
        script_source: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,ScriptIdentifier]:
    '''
    Deprecated, please use addScriptToEvaluateOnNewDocument instead.

    **EXPERIMENTAL**

    :param script_source:
    :returns: Identifier of the added script.
    '''
    params: T_JSON_DICT = dict()
    params['scriptSource'] = script_source
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.addScriptToEvaluateOnLoad',
        'params': params,
    }
    json = yield cmd_dict
    return ScriptIdentifier.from_json(json['identifier'])


def add_script_to_evaluate_on_new_document(
        source: str,
        world_name: typing.Optional[str] = None,
        include_command_line_api: typing.Optional[bool] = None,
        run_immediately: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,ScriptIdentifier]:
    '''
    Evaluates given script in every frame upon creation (before loading frame's scripts).

    :param source:
    :param world_name: **(EXPERIMENTAL)** *(Optional)* If specified, creates an isolated world with the given name and evaluates given script in it. This world name will be used as the ExecutionContextDescription::name when the corresponding event is emitted.
    :param include_command_line_api: **(EXPERIMENTAL)** *(Optional)* Specifies whether command line API should be available to the script, defaults to false.
    :param run_immediately: **(EXPERIMENTAL)** *(Optional)* If true, runs the script immediately on existing execution contexts or worlds. Default: false.
    :returns: Identifier of the added script.
    '''
    params: T_JSON_DICT = dict()
    params['source'] = source
    if world_name is not None:
        params['worldName'] = world_name
    if include_command_line_api is not None:
        params['includeCommandLineAPI'] = include_command_line_api
    if run_immediately is not None:
        params['runImmediately'] = run_immediately
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.addScriptToEvaluateOnNewDocument',
        'params': params,
    }
    json = yield cmd_dict
    return ScriptIdentifier.from_json(json['identifier'])


def bring_to_front() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Brings page to front (activates tab).
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.bringToFront',
    }
    json = yield cmd_dict


def capture_screenshot(
        format_: typing.Optional[str] = None,
        quality: typing.Optional[int] = None,
        clip: typing.Optional[Viewport] = None,
        from_surface: typing.Optional[bool] = None,
        capture_beyond_viewport: typing.Optional[bool] = None,
        optimize_for_speed: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Capture page screenshot.

    :param format_: *(Optional)* Image compression format (defaults to png).
    :param quality: *(Optional)* Compression quality from range [0..100] (jpeg only).
    :param clip: *(Optional)* Capture the screenshot of a given region only.
    :param from_surface: **(EXPERIMENTAL)** *(Optional)* Capture the screenshot from the surface, rather than the view. Defaults to true.
    :param capture_beyond_viewport: **(EXPERIMENTAL)** *(Optional)* Capture the screenshot beyond the viewport. Defaults to false.
    :param optimize_for_speed: **(EXPERIMENTAL)** *(Optional)* Optimize image encoding for speed, not for resulting size (defaults to false)
    :returns: Base64-encoded image data.
    '''
    params: T_JSON_DICT = dict()
    if format_ is not None:
        params['format'] = format_
    if quality is not None:
        params['quality'] = quality
    if clip is not None:
        params['clip'] = clip.to_json()
    if from_surface is not None:
        params['fromSurface'] = from_surface
    if capture_beyond_viewport is not None:
        params['captureBeyondViewport'] = capture_beyond_viewport
    if optimize_for_speed is not None:
        params['optimizeForSpeed'] = optimize_for_speed
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.captureScreenshot',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['data'])


def capture_snapshot(
        format_: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Returns a snapshot of the page as a string. For MHTML format, the serialization includes
    iframes, shadow DOM, external resources, and element-inline styles.

    **EXPERIMENTAL**

    :param format_: *(Optional)* Format (defaults to mhtml).
    :returns: Serialized page data.
    '''
    params: T_JSON_DICT = dict()
    if format_ is not None:
        params['format'] = format_
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.captureSnapshot',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['data'])


def clear_device_metrics_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears the overridden device metrics.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.clearDeviceMetricsOverride',
    }
    json = yield cmd_dict


def clear_device_orientation_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears the overridden Device Orientation.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.clearDeviceOrientationOverride',
    }
    json = yield cmd_dict


def clear_geolocation_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears the overridden Geolocation Position and Error.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.clearGeolocationOverride',
    }
    json = yield cmd_dict


def create_isolated_world(
        frame_id: FrameId,
        world_name: typing.Optional[str] = None,
        grant_univeral_access: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.ExecutionContextId]:
    '''
    Creates an isolated world for the given frame.

    :param frame_id: Id of the frame in which the isolated world should be created.
    :param world_name: *(Optional)* An optional name which is reported in the Execution Context.
    :param grant_univeral_access: *(Optional)* Whether or not universal access should be granted to the isolated world. This is a powerful option, use with caution.
    :returns: Execution context of the isolated world.
    '''
    params: T_JSON_DICT = dict()
    params['frameId'] = frame_id.to_json()
    if world_name is not None:
        params['worldName'] = world_name
    if grant_univeral_access is not None:
        params['grantUniveralAccess'] = grant_univeral_access
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.createIsolatedWorld',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.ExecutionContextId.from_json(json['executionContextId'])


def delete_cookie(
        cookie_name: str,
        url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes browser cookie with given name, domain and path.

    **EXPERIMENTAL**

    :param cookie_name: Name of the cookie to remove.
    :param url: URL to match cooke domain and path.
    '''
    params: T_JSON_DICT = dict()
    params['cookieName'] = cookie_name
    params['url'] = url
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.deleteCookie',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables page domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.disable',
    }
    json = yield cmd_dict


def enable(
        enable_file_chooser_opened_event: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables page domain notifications.

    :param enable_file_chooser_opened_event: **(EXPERIMENTAL)** *(Optional)* If true, the ```Page.fileChooserOpened```` event will be emitted regardless of the state set by ````Page.setInterceptFileChooserDialog``` command (default: false).
    '''
    params: T_JSON_DICT = dict()
    if enable_file_chooser_opened_event is not None:
        params['enableFileChooserOpenedEvent'] = enable_file_chooser_opened_event
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.enable',
        'params': params,
    }
    json = yield cmd_dict


def get_app_manifest(
        manifest_id: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, typing.List[AppManifestError], typing.Optional[str], typing.Optional[AppManifestParsedProperties], WebAppManifest]]:
    '''
    Gets the processed manifest for this current document.
      This API always waits for the manifest to be loaded.
      If manifestId is provided, and it does not match the manifest of the
        current document, this API errors out.
      If there is not a loaded page, this API errors out immediately.

    :param manifest_id: *(Optional)*
    :returns: A tuple with the following items:

        0. **url** - Manifest location.
        1. **errors** - 
        2. **data** - *(Optional)* Manifest content.
        3. **parsed** - *(Optional)* Parsed manifest properties. Deprecated, use manifest instead.
        4. **manifest** - 
    '''
    params: T_JSON_DICT = dict()
    if manifest_id is not None:
        params['manifestId'] = manifest_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.getAppManifest',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['url']),
        [AppManifestError.from_json(i) for i in json['errors']],
        str(json['data']) if 'data' in json else None,
        AppManifestParsedProperties.from_json(json['parsed']) if 'parsed' in json else None,
        WebAppManifest.from_json(json['manifest'])
    )


def get_installability_errors() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[InstallabilityError]]:
    '''


    **EXPERIMENTAL**

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.getInstallabilityErrors',
    }
    json = yield cmd_dict
    return [InstallabilityError.from_json(i) for i in json['installabilityErrors']]


def get_manifest_icons() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Optional[str]]:
    '''
    Deprecated because it's not guaranteed that the returned icon is in fact the one used for PWA installation.

    **EXPERIMENTAL**

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.getManifestIcons',
    }
    json = yield cmd_dict
    return str(json['primaryIcon']) if 'primaryIcon' in json else None


def get_app_id() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[str], typing.Optional[str]]]:
    '''
    Returns the unique (PWA) app id.
    Only returns values if the feature flag 'WebAppEnableManifestId' is enabled

    **EXPERIMENTAL**

    :returns: A tuple with the following items:

        0. **appId** - *(Optional)* App id, either from manifest's id attribute or computed from start_url
        1. **recommendedId** - *(Optional)* Recommendation for manifest's id attribute to match current id computed from start_url
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.getAppId',
    }
    json = yield cmd_dict
    return (
        str(json['appId']) if 'appId' in json else None,
        str(json['recommendedId']) if 'recommendedId' in json else None
    )


def get_ad_script_ancestry_ids(
        frame_id: FrameId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[AdScriptId]]:
    '''


    **EXPERIMENTAL**

    :param frame_id:
    :returns: The ancestry chain of ad script identifiers leading to this frame's creation, ordered from the most immediate script (in the frame creation stack) to more distant ancestors (that created the immediately preceding script). Only sent if frame is labelled as an ad and ids are available.
    '''
    params: T_JSON_DICT = dict()
    params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.getAdScriptAncestryIds',
        'params': params,
    }
    json = yield cmd_dict
    return [AdScriptId.from_json(i) for i in json['adScriptAncestryIds']]


def get_frame_tree() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,FrameTree]:
    '''
    Returns present frame tree structure.

    :returns: Present frame tree structure.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.getFrameTree',
    }
    json = yield cmd_dict
    return FrameTree.from_json(json['frameTree'])


def get_layout_metrics() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[LayoutViewport, VisualViewport, dom.Rect, LayoutViewport, VisualViewport, dom.Rect]]:
    '''
    Returns metrics relating to the layouting of the page, such as viewport bounds/scale.

    :returns: A tuple with the following items:

        0. **layoutViewport** - Deprecated metrics relating to the layout viewport. Is in device pixels. Use ``cssLayoutViewport`` instead.
        1. **visualViewport** - Deprecated metrics relating to the visual viewport. Is in device pixels. Use ``cssVisualViewport`` instead.
        2. **contentSize** - Deprecated size of scrollable area. Is in DP. Use ``cssContentSize`` instead.
        3. **cssLayoutViewport** - Metrics relating to the layout viewport in CSS pixels.
        4. **cssVisualViewport** - Metrics relating to the visual viewport in CSS pixels.
        5. **cssContentSize** - Size of scrollable area in CSS pixels.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.getLayoutMetrics',
    }
    json = yield cmd_dict
    return (
        LayoutViewport.from_json(json['layoutViewport']),
        VisualViewport.from_json(json['visualViewport']),
        dom.Rect.from_json(json['contentSize']),
        LayoutViewport.from_json(json['cssLayoutViewport']),
        VisualViewport.from_json(json['cssVisualViewport']),
        dom.Rect.from_json(json['cssContentSize'])
    )


def get_navigation_history() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[int, typing.List[NavigationEntry]]]:
    '''
    Returns navigation history for the current page.

    :returns: A tuple with the following items:

        0. **currentIndex** - Index of the current navigation history entry.
        1. **entries** - Array of navigation history entries.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.getNavigationHistory',
    }
    json = yield cmd_dict
    return (
        int(json['currentIndex']),
        [NavigationEntry.from_json(i) for i in json['entries']]
    )


def reset_navigation_history() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resets navigation history for the current page.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.resetNavigationHistory',
    }
    json = yield cmd_dict


def get_resource_content(
        frame_id: FrameId,
        url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, bool]]:
    '''
    Returns content of the given resource.

    **EXPERIMENTAL**

    :param frame_id: Frame id to get resource for.
    :param url: URL of the resource to get content for.
    :returns: A tuple with the following items:

        0. **content** - Resource content.
        1. **base64Encoded** - True, if content was served as base64.
    '''
    params: T_JSON_DICT = dict()
    params['frameId'] = frame_id.to_json()
    params['url'] = url
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.getResourceContent',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['content']),
        bool(json['base64Encoded'])
    )


def get_resource_tree() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,FrameResourceTree]:
    '''
    Returns present frame / resource tree structure.

    **EXPERIMENTAL**

    :returns: Present frame / resource tree structure.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.getResourceTree',
    }
    json = yield cmd_dict
    return FrameResourceTree.from_json(json['frameTree'])


def handle_java_script_dialog(
        accept: bool,
        prompt_text: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Accepts or dismisses a JavaScript initiated dialog (alert, confirm, prompt, or onbeforeunload).

    :param accept: Whether to accept or dismiss the dialog.
    :param prompt_text: *(Optional)* The text to enter into the dialog prompt before accepting. Used only if this is a prompt dialog.
    '''
    params: T_JSON_DICT = dict()
    params['accept'] = accept
    if prompt_text is not None:
        params['promptText'] = prompt_text
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.handleJavaScriptDialog',
        'params': params,
    }
    json = yield cmd_dict


def navigate(
        url: str,
        referrer: typing.Optional[str] = None,
        transition_type: typing.Optional[TransitionType] = None,
        frame_id: typing.Optional[FrameId] = None,
        referrer_policy: typing.Optional[ReferrerPolicy] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[FrameId, typing.Optional[network.LoaderId], typing.Optional[str]]]:
    '''
    Navigates current page to the given URL.

    :param url: URL to navigate the page to.
    :param referrer: *(Optional)* Referrer URL.
    :param transition_type: *(Optional)* Intended transition type.
    :param frame_id: *(Optional)* Frame id to navigate, if not specified navigates the top frame.
    :param referrer_policy: **(EXPERIMENTAL)** *(Optional)* Referrer-policy used for the navigation.
    :returns: A tuple with the following items:

        0. **frameId** - Frame id that has navigated (or failed to navigate)
        1. **loaderId** - *(Optional)* Loader identifier. This is omitted in case of same-document navigation, as the previously committed loaderId would not change.
        2. **errorText** - *(Optional)* User friendly error message, present if and only if navigation has failed.
    '''
    params: T_JSON_DICT = dict()
    params['url'] = url
    if referrer is not None:
        params['referrer'] = referrer
    if transition_type is not None:
        params['transitionType'] = transition_type.to_json()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    if referrer_policy is not None:
        params['referrerPolicy'] = referrer_policy.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.navigate',
        'params': params,
    }
    json = yield cmd_dict
    return (
        FrameId.from_json(json['frameId']),
        network.LoaderId.from_json(json['loaderId']) if 'loaderId' in json else None,
        str(json['errorText']) if 'errorText' in json else None
    )


def navigate_to_history_entry(
        entry_id: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Navigates current page to the given history entry.

    :param entry_id: Unique id of the entry to navigate to.
    '''
    params: T_JSON_DICT = dict()
    params['entryId'] = entry_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.navigateToHistoryEntry',
        'params': params,
    }
    json = yield cmd_dict


def print_to_pdf(
        landscape: typing.Optional[bool] = None,
        display_header_footer: typing.Optional[bool] = None,
        print_background: typing.Optional[bool] = None,
        scale: typing.Optional[float] = None,
        paper_width: typing.Optional[float] = None,
        paper_height: typing.Optional[float] = None,
        margin_top: typing.Optional[float] = None,
        margin_bottom: typing.Optional[float] = None,
        margin_left: typing.Optional[float] = None,
        margin_right: typing.Optional[float] = None,
        page_ranges: typing.Optional[str] = None,
        header_template: typing.Optional[str] = None,
        footer_template: typing.Optional[str] = None,
        prefer_css_page_size: typing.Optional[bool] = None,
        transfer_mode: typing.Optional[str] = None,
        generate_tagged_pdf: typing.Optional[bool] = None,
        generate_document_outline: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, typing.Optional[io.StreamHandle]]]:
    '''
    Print page as PDF.

    :param landscape: *(Optional)* Paper orientation. Defaults to false.
    :param display_header_footer: *(Optional)* Display header and footer. Defaults to false.
    :param print_background: *(Optional)* Print background graphics. Defaults to false.
    :param scale: *(Optional)* Scale of the webpage rendering. Defaults to 1.
    :param paper_width: *(Optional)* Paper width in inches. Defaults to 8.5 inches.
    :param paper_height: *(Optional)* Paper height in inches. Defaults to 11 inches.
    :param margin_top: *(Optional)* Top margin in inches. Defaults to 1cm (~0.4 inches).
    :param margin_bottom: *(Optional)* Bottom margin in inches. Defaults to 1cm (~0.4 inches).
    :param margin_left: *(Optional)* Left margin in inches. Defaults to 1cm (~0.4 inches).
    :param margin_right: *(Optional)* Right margin in inches. Defaults to 1cm (~0.4 inches).
    :param page_ranges: *(Optional)* Paper ranges to print, one based, e.g., '1-5, 8, 11-13'. Pages are printed in the document order, not in the order specified, and no more than once. Defaults to empty string, which implies the entire document is printed. The page numbers are quietly capped to actual page count of the document, and ranges beyond the end of the document are ignored. If this results in no pages to print, an error is reported. It is an error to specify a range with start greater than end.
    :param header_template: *(Optional)* HTML template for the print header. Should be valid HTML markup with following classes used to inject printing values into them: - ```date````: formatted print date - ````title````: document title - ````url````: document location - ````pageNumber````: current page number - ````totalPages````: total pages in the document  For example, ````<span class=title></span>```` would generate span containing the title.
    :param footer_template: *(Optional)* HTML template for the print footer. Should use the same format as the ````headerTemplate````.
    :param prefer_css_page_size: *(Optional)* Whether or not to prefer page size as defined by css. Defaults to false, in which case the content will be scaled to fit the paper size.
    :param transfer_mode: **(EXPERIMENTAL)** *(Optional)* return as stream
    :param generate_tagged_pdf: **(EXPERIMENTAL)** *(Optional)* Whether or not to generate tagged (accessible) PDF. Defaults to embedder choice.
    :param generate_document_outline: **(EXPERIMENTAL)** *(Optional)* Whether or not to embed the document outline into the PDF.
    :returns: A tuple with the following items:

        0. **data** - Base64-encoded pdf data. Empty if `` returnAsStream` is specified.
        1. **stream** - *(Optional)* A handle of the stream that holds resulting PDF data.
    '''
    params: T_JSON_DICT = dict()
    if landscape is not None:
        params['landscape'] = landscape
    if display_header_footer is not None:
        params['displayHeaderFooter'] = display_header_footer
    if print_background is not None:
        params['printBackground'] = print_background
    if scale is not None:
        params['scale'] = scale
    if paper_width is not None:
        params['paperWidth'] = paper_width
    if paper_height is not None:
        params['paperHeight'] = paper_height
    if margin_top is not None:
        params['marginTop'] = margin_top
    if margin_bottom is not None:
        params['marginBottom'] = margin_bottom
    if margin_left is not None:
        params['marginLeft'] = margin_left
    if margin_right is not None:
        params['marginRight'] = margin_right
    if page_ranges is not None:
        params['pageRanges'] = page_ranges
    if header_template is not None:
        params['headerTemplate'] = header_template
    if footer_template is not None:
        params['footerTemplate'] = footer_template
    if prefer_css_page_size is not None:
        params['preferCSSPageSize'] = prefer_css_page_size
    if transfer_mode is not None:
        params['transferMode'] = transfer_mode
    if generate_tagged_pdf is not None:
        params['generateTaggedPDF'] = generate_tagged_pdf
    if generate_document_outline is not None:
        params['generateDocumentOutline'] = generate_document_outline
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.printToPDF',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['data']),
        io.StreamHandle.from_json(json['stream']) if 'stream' in json else None
    )


def reload(
        ignore_cache: typing.Optional[bool] = None,
        script_to_evaluate_on_load: typing.Optional[str] = None,
        loader_id: typing.Optional[network.LoaderId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Reloads given page optionally ignoring the cache.

    :param ignore_cache: *(Optional)* If true, browser cache is ignored (as if the user pressed Shift+refresh).
    :param script_to_evaluate_on_load: *(Optional)* If set, the script will be injected into all frames of the inspected page after reload. Argument will be ignored if reloading dataURL origin.
    :param loader_id: **(EXPERIMENTAL)** *(Optional)* If set, an error will be thrown if the target page's main frame's loader id does not match the provided id. This prevents accidentally reloading an unintended target in case there's a racing navigation.
    '''
    params: T_JSON_DICT = dict()
    if ignore_cache is not None:
        params['ignoreCache'] = ignore_cache
    if script_to_evaluate_on_load is not None:
        params['scriptToEvaluateOnLoad'] = script_to_evaluate_on_load
    if loader_id is not None:
        params['loaderId'] = loader_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.reload',
        'params': params,
    }
    json = yield cmd_dict


def remove_script_to_evaluate_on_load(
        identifier: ScriptIdentifier
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deprecated, please use removeScriptToEvaluateOnNewDocument instead.

    **EXPERIMENTAL**

    :param identifier:
    '''
    params: T_JSON_DICT = dict()
    params['identifier'] = identifier.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.removeScriptToEvaluateOnLoad',
        'params': params,
    }
    json = yield cmd_dict


def remove_script_to_evaluate_on_new_document(
        identifier: ScriptIdentifier
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes given script from the list.

    :param identifier:
    '''
    params: T_JSON_DICT = dict()
    params['identifier'] = identifier.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.removeScriptToEvaluateOnNewDocument',
        'params': params,
    }
    json = yield cmd_dict


def screencast_frame_ack(
        session_id: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Acknowledges that a screencast frame has been received by the frontend.

    **EXPERIMENTAL**

    :param session_id: Frame number.
    '''
    params: T_JSON_DICT = dict()
    params['sessionId'] = session_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.screencastFrameAck',
        'params': params,
    }
    json = yield cmd_dict


def search_in_resource(
        frame_id: FrameId,
        url: str,
        query: str,
        case_sensitive: typing.Optional[bool] = None,
        is_regex: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[debugger.SearchMatch]]:
    '''
    Searches for given string in resource content.

    **EXPERIMENTAL**

    :param frame_id: Frame id for resource to search in.
    :param url: URL of the resource to search in.
    :param query: String to search for.
    :param case_sensitive: *(Optional)* If true, search is case sensitive.
    :param is_regex: *(Optional)* If true, treats string parameter as regex.
    :returns: List of search matches.
    '''
    params: T_JSON_DICT = dict()
    params['frameId'] = frame_id.to_json()
    params['url'] = url
    params['query'] = query
    if case_sensitive is not None:
        params['caseSensitive'] = case_sensitive
    if is_regex is not None:
        params['isRegex'] = is_regex
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.searchInResource',
        'params': params,
    }
    json = yield cmd_dict
    return [debugger.SearchMatch.from_json(i) for i in json['result']]


def set_ad_blocking_enabled(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enable Chrome's experimental ad filter on all sites.

    **EXPERIMENTAL**

    :param enabled: Whether to block ads.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setAdBlockingEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_bypass_csp(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enable page Content Security Policy by-passing.

    :param enabled: Whether to bypass page CSP.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setBypassCSP',
        'params': params,
    }
    json = yield cmd_dict


def get_permissions_policy_state(
        frame_id: FrameId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[PermissionsPolicyFeatureState]]:
    '''
    Get Permissions Policy state on given frame.

    **EXPERIMENTAL**

    :param frame_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.getPermissionsPolicyState',
        'params': params,
    }
    json = yield cmd_dict
    return [PermissionsPolicyFeatureState.from_json(i) for i in json['states']]


def get_origin_trials(
        frame_id: FrameId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[OriginTrial]]:
    '''
    Get Origin Trials on given frame.

    **EXPERIMENTAL**

    :param frame_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.getOriginTrials',
        'params': params,
    }
    json = yield cmd_dict
    return [OriginTrial.from_json(i) for i in json['originTrials']]


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
        screen_orientation: typing.Optional[emulation.ScreenOrientation] = None,
        viewport: typing.Optional[Viewport] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides the values of device screen dimensions (window.screen.width, window.screen.height,
    window.innerWidth, window.innerHeight, and "device-width"/"device-height"-related CSS media
    query results).

    **EXPERIMENTAL**

    :param width: Overriding width value in pixels (minimum 0, maximum 10000000). 0 disables the override.
    :param height: Overriding height value in pixels (minimum 0, maximum 10000000). 0 disables the override.
    :param device_scale_factor: Overriding device scale factor value. 0 disables the override.
    :param mobile: Whether to emulate mobile device. This includes viewport meta tag, overlay scrollbars, text autosizing and more.
    :param scale: *(Optional)* Scale to apply to resulting view image.
    :param screen_width: *(Optional)* Overriding screen width value in pixels (minimum 0, maximum 10000000).
    :param screen_height: *(Optional)* Overriding screen height value in pixels (minimum 0, maximum 10000000).
    :param position_x: *(Optional)* Overriding view X position on screen in pixels (minimum 0, maximum 10000000).
    :param position_y: *(Optional)* Overriding view Y position on screen in pixels (minimum 0, maximum 10000000).
    :param dont_set_visible_size: *(Optional)* Do not set visible view size, rely upon explicit setVisibleSize call.
    :param screen_orientation: *(Optional)* Screen orientation override.
    :param viewport: *(Optional)* The viewport dimensions and scale. If not set, the override is cleared.
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
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setDeviceMetricsOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_device_orientation_override(
        alpha: float,
        beta: float,
        gamma: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Overrides the Device Orientation.

    **EXPERIMENTAL**

    :param alpha: Mock alpha
    :param beta: Mock beta
    :param gamma: Mock gamma
    '''
    params: T_JSON_DICT = dict()
    params['alpha'] = alpha
    params['beta'] = beta
    params['gamma'] = gamma
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setDeviceOrientationOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_font_families(
        font_families: FontFamilies,
        for_scripts: typing.Optional[typing.List[ScriptFontFamilies]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set generic font families.

    **EXPERIMENTAL**

    :param font_families: Specifies font families to set. If a font family is not specified, it won't be changed.
    :param for_scripts: *(Optional)* Specifies font families to set for individual scripts.
    '''
    params: T_JSON_DICT = dict()
    params['fontFamilies'] = font_families.to_json()
    if for_scripts is not None:
        params['forScripts'] = [i.to_json() for i in for_scripts]
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setFontFamilies',
        'params': params,
    }
    json = yield cmd_dict


def set_font_sizes(
        font_sizes: FontSizes
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set default font sizes.

    **EXPERIMENTAL**

    :param font_sizes: Specifies font sizes to set. If a font size is not specified, it won't be changed.
    '''
    params: T_JSON_DICT = dict()
    params['fontSizes'] = font_sizes.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setFontSizes',
        'params': params,
    }
    json = yield cmd_dict


def set_document_content(
        frame_id: FrameId,
        html: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets given markup as the document's HTML.

    :param frame_id: Frame id to set HTML for.
    :param html: HTML content to set.
    '''
    params: T_JSON_DICT = dict()
    params['frameId'] = frame_id.to_json()
    params['html'] = html
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setDocumentContent',
        'params': params,
    }
    json = yield cmd_dict


def set_download_behavior(
        behavior: str,
        download_path: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set the behavior when downloading a file.

    **EXPERIMENTAL**

    :param behavior: Whether to allow all or deny all download requests, or use default Chrome behavior if available (otherwise deny).
    :param download_path: *(Optional)* The default path to save downloaded files to. This is required if behavior is set to 'allow'
    '''
    params: T_JSON_DICT = dict()
    params['behavior'] = behavior
    if download_path is not None:
        params['downloadPath'] = download_path
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setDownloadBehavior',
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
        'method': 'Page.setGeolocationOverride',
        'params': params,
    }
    json = yield cmd_dict


def set_lifecycle_events_enabled(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Controls whether page will emit lifecycle events.

    :param enabled: If true, starts emitting lifecycle events.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setLifecycleEventsEnabled',
        'params': params,
    }
    json = yield cmd_dict


def set_touch_emulation_enabled(
        enabled: bool,
        configuration: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Toggles mouse event-based touch event emulation.

    **EXPERIMENTAL**

    :param enabled: Whether the touch event emulation should be enabled.
    :param configuration: *(Optional)* Touch/gesture events configuration. Default: current platform.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    if configuration is not None:
        params['configuration'] = configuration
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setTouchEmulationEnabled',
        'params': params,
    }
    json = yield cmd_dict


def start_screencast(
        format_: typing.Optional[str] = None,
        quality: typing.Optional[int] = None,
        max_width: typing.Optional[int] = None,
        max_height: typing.Optional[int] = None,
        every_nth_frame: typing.Optional[int] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Starts sending each frame using the ``screencastFrame`` event.

    **EXPERIMENTAL**

    :param format_: *(Optional)* Image compression format.
    :param quality: *(Optional)* Compression quality from range [0..100].
    :param max_width: *(Optional)* Maximum screenshot width.
    :param max_height: *(Optional)* Maximum screenshot height.
    :param every_nth_frame: *(Optional)* Send every n-th frame.
    '''
    params: T_JSON_DICT = dict()
    if format_ is not None:
        params['format'] = format_
    if quality is not None:
        params['quality'] = quality
    if max_width is not None:
        params['maxWidth'] = max_width
    if max_height is not None:
        params['maxHeight'] = max_height
    if every_nth_frame is not None:
        params['everyNthFrame'] = every_nth_frame
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.startScreencast',
        'params': params,
    }
    json = yield cmd_dict


def stop_loading() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Force the page stop all navigations and pending resource fetches.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.stopLoading',
    }
    json = yield cmd_dict


def crash() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Crashes renderer on the IO thread, generates minidumps.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.crash',
    }
    json = yield cmd_dict


def close() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Tries to close page, running its beforeunload hooks, if any.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.close',
    }
    json = yield cmd_dict


def set_web_lifecycle_state(
        state: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Tries to update the web lifecycle state of the page.
    It will transition the page to the given state according to:
    https://github.com/WICG/web-lifecycle/

    **EXPERIMENTAL**

    :param state: Target lifecycle state
    '''
    params: T_JSON_DICT = dict()
    params['state'] = state
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setWebLifecycleState',
        'params': params,
    }
    json = yield cmd_dict


def stop_screencast() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stops sending each frame in the ``screencastFrame``.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.stopScreencast',
    }
    json = yield cmd_dict


def produce_compilation_cache(
        scripts: typing.List[CompilationCacheParams]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Requests backend to produce compilation cache for the specified scripts.
    ``scripts`` are appended to the list of scripts for which the cache
    would be produced. The list may be reset during page navigation.
    When script with a matching URL is encountered, the cache is optionally
    produced upon backend discretion, based on internal heuristics.
    See also: ``Page.compilationCacheProduced``.

    **EXPERIMENTAL**

    :param scripts:
    '''
    params: T_JSON_DICT = dict()
    params['scripts'] = [i.to_json() for i in scripts]
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.produceCompilationCache',
        'params': params,
    }
    json = yield cmd_dict


def add_compilation_cache(
        url: str,
        data: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Seeds compilation cache for given url. Compilation cache does not survive
    cross-process navigation.

    **EXPERIMENTAL**

    :param url:
    :param data: Base64-encoded data
    '''
    params: T_JSON_DICT = dict()
    params['url'] = url
    params['data'] = data
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.addCompilationCache',
        'params': params,
    }
    json = yield cmd_dict


def clear_compilation_cache() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears seeded compilation cache.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.clearCompilationCache',
    }
    json = yield cmd_dict


def set_spc_transaction_mode(
        mode: AutoResponseMode
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets the Secure Payment Confirmation transaction mode.
    https://w3c.github.io/secure-payment-confirmation/#sctn-automation-set-spc-transaction-mode

    **EXPERIMENTAL**

    :param mode:
    '''
    params: T_JSON_DICT = dict()
    params['mode'] = mode.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setSPCTransactionMode',
        'params': params,
    }
    json = yield cmd_dict


def set_rph_registration_mode(
        mode: AutoResponseMode
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Extensions for Custom Handlers API:
    https://html.spec.whatwg.org/multipage/system-state.html#rph-automation

    **EXPERIMENTAL**

    :param mode:
    '''
    params: T_JSON_DICT = dict()
    params['mode'] = mode.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setRPHRegistrationMode',
        'params': params,
    }
    json = yield cmd_dict


def generate_test_report(
        message: str,
        group: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Generates a report for testing.

    **EXPERIMENTAL**

    :param message: Message to be displayed in the report.
    :param group: *(Optional)* Specifies the endpoint group to deliver the report to.
    '''
    params: T_JSON_DICT = dict()
    params['message'] = message
    if group is not None:
        params['group'] = group
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.generateTestReport',
        'params': params,
    }
    json = yield cmd_dict


def wait_for_debugger() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Pauses page execution. Can be resumed using generic Runtime.runIfWaitingForDebugger.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.waitForDebugger',
    }
    json = yield cmd_dict


def set_intercept_file_chooser_dialog(
        enabled: bool,
        cancel: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Intercept file chooser requests and transfer control to protocol clients.
    When file chooser interception is enabled, native file chooser dialog is not shown.
    Instead, a protocol event ``Page.fileChooserOpened`` is emitted.

    :param enabled:
    :param cancel: **(EXPERIMENTAL)** *(Optional)* If true, cancels the dialog by emitting relevant events (if any) in addition to not showing it if the interception is enabled (default: false).
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    if cancel is not None:
        params['cancel'] = cancel
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setInterceptFileChooserDialog',
        'params': params,
    }
    json = yield cmd_dict


def set_prerendering_allowed(
        is_allowed: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enable/disable prerendering manually.

    This command is a short-term solution for https://crbug.com/1440085.
    See https://docs.google.com/document/d/12HVmFxYj5Jc-eJr5OmWsa2bqTJsbgGLKI6ZIyx0_wpA
    for more details.

    TODO(https://crbug.com/1440085): Remove this once Puppeteer supports tab targets.

    **EXPERIMENTAL**

    :param is_allowed:
    '''
    params: T_JSON_DICT = dict()
    params['isAllowed'] = is_allowed
    cmd_dict: T_JSON_DICT = {
        'method': 'Page.setPrerenderingAllowed',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Page.domContentEventFired')
@dataclass
class DomContentEventFired:
    timestamp: network.MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomContentEventFired:
        return cls(
            timestamp=network.MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Page.fileChooserOpened')
@dataclass
class FileChooserOpened:
    '''
    Emitted only when ``page.interceptFileChooser`` is enabled.
    '''
    #: Id of the frame containing input node.
    frame_id: FrameId
    #: Input mode.
    mode: str
    #: Input node id. Only present for file choosers opened via an ``<input type="file">`` element.
    backend_node_id: typing.Optional[dom.BackendNodeId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FileChooserOpened:
        return cls(
            frame_id=FrameId.from_json(json['frameId']),
            mode=str(json['mode']),
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None
        )


@event_class('Page.frameAttached')
@dataclass
class FrameAttached:
    '''
    Fired when frame has been attached to its parent.
    '''
    #: Id of the frame that has been attached.
    frame_id: FrameId
    #: Parent frame identifier.
    parent_frame_id: FrameId
    #: JavaScript stack trace of when frame was attached, only set if frame initiated from script.
    stack: typing.Optional[runtime.StackTrace]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FrameAttached:
        return cls(
            frame_id=FrameId.from_json(json['frameId']),
            parent_frame_id=FrameId.from_json(json['parentFrameId']),
            stack=runtime.StackTrace.from_json(json['stack']) if 'stack' in json else None
        )


@event_class('Page.frameClearedScheduledNavigation')
@dataclass
class FrameClearedScheduledNavigation:
    '''
    Fired when frame no longer has a scheduled navigation.
    '''
    #: Id of the frame that has cleared its scheduled navigation.
    frame_id: FrameId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FrameClearedScheduledNavigation:
        return cls(
            frame_id=FrameId.from_json(json['frameId'])
        )


@event_class('Page.frameDetached')
@dataclass
class FrameDetached:
    '''
    Fired when frame has been detached from its parent.
    '''
    #: Id of the frame that has been detached.
    frame_id: FrameId
    reason: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FrameDetached:
        return cls(
            frame_id=FrameId.from_json(json['frameId']),
            reason=str(json['reason'])
        )


@event_class('Page.frameSubtreeWillBeDetached')
@dataclass
class FrameSubtreeWillBeDetached:
    '''
    **EXPERIMENTAL**

    Fired before frame subtree is detached. Emitted before any frame of the
    subtree is actually detached.
    '''
    #: Id of the frame that is the root of the subtree that will be detached.
    frame_id: FrameId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FrameSubtreeWillBeDetached:
        return cls(
            frame_id=FrameId.from_json(json['frameId'])
        )


@event_class('Page.frameNavigated')
@dataclass
class FrameNavigated:
    '''
    Fired once navigation of the frame has completed. Frame is now associated with the new loader.
    '''
    #: Frame object.
    frame: Frame
    type_: NavigationType

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FrameNavigated:
        return cls(
            frame=Frame.from_json(json['frame']),
            type_=NavigationType.from_json(json['type'])
        )


@event_class('Page.documentOpened')
@dataclass
class DocumentOpened:
    '''
    **EXPERIMENTAL**

    Fired when opening document to write to.
    '''
    #: Frame object.
    frame: Frame

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DocumentOpened:
        return cls(
            frame=Frame.from_json(json['frame'])
        )


@event_class('Page.frameResized')
@dataclass
class FrameResized:
    '''
    **EXPERIMENTAL**


    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FrameResized:
        return cls(

        )


@event_class('Page.frameStartedNavigating')
@dataclass
class FrameStartedNavigating:
    '''
    **EXPERIMENTAL**

    Fired when a navigation starts. This event is fired for both
    renderer-initiated and browser-initiated navigations. For renderer-initiated
    navigations, the event is fired after ``frameRequestedNavigation``.
    Navigation may still be cancelled after the event is issued. Multiple events
    can be fired for a single navigation, for example, when a same-document
    navigation becomes a cross-document navigation (such as in the case of a
    frameset).
    '''
    #: ID of the frame that is being navigated.
    frame_id: FrameId
    #: The URL the navigation started with. The final URL can be different.
    url: str
    #: Loader identifier. Even though it is present in case of same-document
    #: navigation, the previously committed loaderId would not change unless
    #: the navigation changes from a same-document to a cross-document
    #: navigation.
    loader_id: network.LoaderId
    navigation_type: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FrameStartedNavigating:
        return cls(
            frame_id=FrameId.from_json(json['frameId']),
            url=str(json['url']),
            loader_id=network.LoaderId.from_json(json['loaderId']),
            navigation_type=str(json['navigationType'])
        )


@event_class('Page.frameRequestedNavigation')
@dataclass
class FrameRequestedNavigation:
    '''
    **EXPERIMENTAL**

    Fired when a renderer-initiated navigation is requested.
    Navigation may still be cancelled after the event is issued.
    '''
    #: Id of the frame that is being navigated.
    frame_id: FrameId
    #: The reason for the navigation.
    reason: ClientNavigationReason
    #: The destination URL for the requested navigation.
    url: str
    #: The disposition for the navigation.
    disposition: ClientNavigationDisposition

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FrameRequestedNavigation:
        return cls(
            frame_id=FrameId.from_json(json['frameId']),
            reason=ClientNavigationReason.from_json(json['reason']),
            url=str(json['url']),
            disposition=ClientNavigationDisposition.from_json(json['disposition'])
        )


@event_class('Page.frameScheduledNavigation')
@dataclass
class FrameScheduledNavigation:
    '''
    Fired when frame schedules a potential navigation.
    '''
    #: Id of the frame that has scheduled a navigation.
    frame_id: FrameId
    #: Delay (in seconds) until the navigation is scheduled to begin. The navigation is not
    #: guaranteed to start.
    delay: float
    #: The reason for the navigation.
    reason: ClientNavigationReason
    #: The destination URL for the scheduled navigation.
    url: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FrameScheduledNavigation:
        return cls(
            frame_id=FrameId.from_json(json['frameId']),
            delay=float(json['delay']),
            reason=ClientNavigationReason.from_json(json['reason']),
            url=str(json['url'])
        )


@event_class('Page.frameStartedLoading')
@dataclass
class FrameStartedLoading:
    '''
    **EXPERIMENTAL**

    Fired when frame has started loading.
    '''
    #: Id of the frame that has started loading.
    frame_id: FrameId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FrameStartedLoading:
        return cls(
            frame_id=FrameId.from_json(json['frameId'])
        )


@event_class('Page.frameStoppedLoading')
@dataclass
class FrameStoppedLoading:
    '''
    **EXPERIMENTAL**

    Fired when frame has stopped loading.
    '''
    #: Id of the frame that has stopped loading.
    frame_id: FrameId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> FrameStoppedLoading:
        return cls(
            frame_id=FrameId.from_json(json['frameId'])
        )


@event_class('Page.downloadWillBegin')
@dataclass
class DownloadWillBegin:
    '''
    **EXPERIMENTAL**

    Fired when page is about to start a download.
    Deprecated. Use Browser.downloadWillBegin instead.
    '''
    #: Id of the frame that caused download to begin.
    frame_id: FrameId
    #: Global unique identifier of the download.
    guid: str
    #: URL of the resource being downloaded.
    url: str
    #: Suggested file name of the resource (the actual name of the file saved on disk may differ).
    suggested_filename: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DownloadWillBegin:
        return cls(
            frame_id=FrameId.from_json(json['frameId']),
            guid=str(json['guid']),
            url=str(json['url']),
            suggested_filename=str(json['suggestedFilename'])
        )


@event_class('Page.downloadProgress')
@dataclass
class DownloadProgress:
    '''
    **EXPERIMENTAL**

    Fired when download makes progress. Last call has ``done`` == true.
    Deprecated. Use Browser.downloadProgress instead.
    '''
    #: Global unique identifier of the download.
    guid: str
    #: Total expected bytes to download.
    total_bytes: float
    #: Total bytes received.
    received_bytes: float
    #: Download status.
    state: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DownloadProgress:
        return cls(
            guid=str(json['guid']),
            total_bytes=float(json['totalBytes']),
            received_bytes=float(json['receivedBytes']),
            state=str(json['state'])
        )


@event_class('Page.interstitialHidden')
@dataclass
class InterstitialHidden:
    '''
    Fired when interstitial page was hidden
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InterstitialHidden:
        return cls(

        )


@event_class('Page.interstitialShown')
@dataclass
class InterstitialShown:
    '''
    Fired when interstitial page was shown
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InterstitialShown:
        return cls(

        )


@event_class('Page.javascriptDialogClosed')
@dataclass
class JavascriptDialogClosed:
    '''
    Fired when a JavaScript initiated dialog (alert, confirm, prompt, or onbeforeunload) has been
    closed.
    '''
    #: Frame id.
    frame_id: FrameId
    #: Whether dialog was confirmed.
    result: bool
    #: User input in case of prompt.
    user_input: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> JavascriptDialogClosed:
        return cls(
            frame_id=FrameId.from_json(json['frameId']),
            result=bool(json['result']),
            user_input=str(json['userInput'])
        )


@event_class('Page.javascriptDialogOpening')
@dataclass
class JavascriptDialogOpening:
    '''
    Fired when a JavaScript initiated dialog (alert, confirm, prompt, or onbeforeunload) is about to
    open.
    '''
    #: Frame url.
    url: str
    #: Frame id.
    frame_id: FrameId
    #: Message that will be displayed by the dialog.
    message: str
    #: Dialog type.
    type_: DialogType
    #: True iff browser is capable showing or acting on the given dialog. When browser has no
    #: dialog handler for given target, calling alert while Page domain is engaged will stall
    #: the page execution. Execution can be resumed via calling Page.handleJavaScriptDialog.
    has_browser_handler: bool
    #: Default dialog prompt.
    default_prompt: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> JavascriptDialogOpening:
        return cls(
            url=str(json['url']),
            frame_id=FrameId.from_json(json['frameId']),
            message=str(json['message']),
            type_=DialogType.from_json(json['type']),
            has_browser_handler=bool(json['hasBrowserHandler']),
            default_prompt=str(json['defaultPrompt']) if 'defaultPrompt' in json else None
        )


@event_class('Page.lifecycleEvent')
@dataclass
class LifecycleEvent:
    '''
    Fired for lifecycle events (navigation, load, paint, etc) in the current
    target (including local frames).
    '''
    #: Id of the frame.
    frame_id: FrameId
    #: Loader identifier. Empty string if the request is fetched from worker.
    loader_id: network.LoaderId
    name: str
    timestamp: network.MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LifecycleEvent:
        return cls(
            frame_id=FrameId.from_json(json['frameId']),
            loader_id=network.LoaderId.from_json(json['loaderId']),
            name=str(json['name']),
            timestamp=network.MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Page.backForwardCacheNotUsed')
@dataclass
class BackForwardCacheNotUsed:
    '''
    **EXPERIMENTAL**

    Fired for failed bfcache history navigations if BackForwardCache feature is enabled. Do
    not assume any ordering with the Page.frameNavigated event. This event is fired only for
    main-frame history navigation where the document changes (non-same-document navigations),
    when bfcache navigation fails.
    '''
    #: The loader id for the associated navigation.
    loader_id: network.LoaderId
    #: The frame id of the associated frame.
    frame_id: FrameId
    #: Array of reasons why the page could not be cached. This must not be empty.
    not_restored_explanations: typing.List[BackForwardCacheNotRestoredExplanation]
    #: Tree structure of reasons why the page could not be cached for each frame.
    not_restored_explanations_tree: typing.Optional[BackForwardCacheNotRestoredExplanationTree]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BackForwardCacheNotUsed:
        return cls(
            loader_id=network.LoaderId.from_json(json['loaderId']),
            frame_id=FrameId.from_json(json['frameId']),
            not_restored_explanations=[BackForwardCacheNotRestoredExplanation.from_json(i) for i in json['notRestoredExplanations']],
            not_restored_explanations_tree=BackForwardCacheNotRestoredExplanationTree.from_json(json['notRestoredExplanationsTree']) if 'notRestoredExplanationsTree' in json else None
        )


@event_class('Page.loadEventFired')
@dataclass
class LoadEventFired:
    timestamp: network.MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LoadEventFired:
        return cls(
            timestamp=network.MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Page.navigatedWithinDocument')
@dataclass
class NavigatedWithinDocument:
    '''
    **EXPERIMENTAL**

    Fired when same-document navigation happens, e.g. due to history API usage or anchor navigation.
    '''
    #: Id of the frame.
    frame_id: FrameId
    #: Frame's new url.
    url: str
    #: Navigation type
    navigation_type: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> NavigatedWithinDocument:
        return cls(
            frame_id=FrameId.from_json(json['frameId']),
            url=str(json['url']),
            navigation_type=str(json['navigationType'])
        )


@event_class('Page.screencastFrame')
@dataclass
class ScreencastFrame:
    '''
    **EXPERIMENTAL**

    Compressed image data requested by the ``startScreencast``.
    '''
    #: Base64-encoded compressed image.
    data: str
    #: Screencast frame metadata.
    metadata: ScreencastFrameMetadata
    #: Frame number.
    session_id: int

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ScreencastFrame:
        return cls(
            data=str(json['data']),
            metadata=ScreencastFrameMetadata.from_json(json['metadata']),
            session_id=int(json['sessionId'])
        )


@event_class('Page.screencastVisibilityChanged')
@dataclass
class ScreencastVisibilityChanged:
    '''
    **EXPERIMENTAL**

    Fired when the page with currently enabled screencast was shown or hidden .
    '''
    #: True if the page is visible.
    visible: bool

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ScreencastVisibilityChanged:
        return cls(
            visible=bool(json['visible'])
        )


@event_class('Page.windowOpen')
@dataclass
class WindowOpen:
    '''
    Fired when a new window is going to be opened, via window.open(), link click, form submission,
    etc.
    '''
    #: The URL for the new window.
    url: str
    #: Window name.
    window_name: str
    #: An array of enabled window features.
    window_features: typing.List[str]
    #: Whether or not it was triggered by user gesture.
    user_gesture: bool

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WindowOpen:
        return cls(
            url=str(json['url']),
            window_name=str(json['windowName']),
            window_features=[str(i) for i in json['windowFeatures']],
            user_gesture=bool(json['userGesture'])
        )


@event_class('Page.compilationCacheProduced')
@dataclass
class CompilationCacheProduced:
    '''
    **EXPERIMENTAL**

    Issued for every compilation cache generated. Is only available
    if Page.setGenerateCompilationCache is enabled.
    '''
    url: str
    #: Base64-encoded data
    data: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CompilationCacheProduced:
        return cls(
            url=str(json['url']),
            data=str(json['data'])
        )

# === NexusCore/openenv\Lib\site-packages\fontTools\subset\__init__.py ===
# Copyright 2013 Google, Inc. All Rights Reserved.
#
# Google Author(s): Behdad Esfahbod

from __future__ import annotations

from fontTools import config
from fontTools.misc.roundTools import otRound
from fontTools import ttLib
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables.otBase import USE_HARFBUZZ_REPACKER
from fontTools.otlLib.maxContextCalc import maxCtxFont
from fontTools.pens.basePen import NullPen
from fontTools.misc.loggingTools import Timer
from fontTools.misc.cliTools import makeOutputFileName
from fontTools.subset.util import _add_method, _uniq_sort
from fontTools.subset.cff import *
from fontTools.subset.svg import *
from fontTools.varLib import varStore, multiVarStore  # For monkey-patching
from fontTools.ttLib.tables._n_a_m_e import NameRecordVisitor, makeName
from fontTools.unicodedata import mirrored
import sys
import struct
import array
import logging
from collections import Counter, defaultdict
from functools import reduce
from types import MethodType

__usage__ = "pyftsubset font-file [glyph...] [--option=value]..."

__doc__ = (
    """\
pyftsubset -- OpenType font subsetter and optimizer

pyftsubset is an OpenType font subsetter and optimizer, based on fontTools.
It accepts any TT- or CFF-flavored OpenType (.otf or .ttf) or WOFF (.woff)
font file. The subsetted glyph set is based on the specified glyphs
or characters, and specified OpenType layout features.

The tool also performs some size-reducing optimizations, aimed for using
subset fonts as webfonts.  Individual optimizations can be enabled or
disabled, and are enabled by default when they are safe.

Usage: """
    + __usage__
    + """

At least one glyph or one of --gids, --gids-file, --glyphs, --glyphs-file,
--text, --text-file, --unicodes, or --unicodes-file, must be specified.

Args:

font-file
  The input font file.
glyph
  Specify one or more glyph identifiers to include in the subset. Must be
  PS glyph names, or the special string '*' to keep the entire glyph set.

Initial glyph set specification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These options populate the initial glyph set. Same option can appear
multiple times, and the results are accummulated.

--gids=<NNN>[,<NNN>...]
  Specify comma/whitespace-separated list of glyph IDs or ranges as decimal
  numbers.  For example, --gids=10-12,14 adds glyphs with numbers 10, 11,
  12, and 14.

--gids-file=<path>
  Like --gids but reads from a file. Anything after a '#' on any line is
  ignored as comments.

--glyphs=<glyphname>[,<glyphname>...]
  Specify comma/whitespace-separated PS glyph names to add to the subset.
  Note that only PS glyph names are accepted, not gidNNN, U+XXXX, etc
  that are accepted on the command line.  The special string '*' will keep
  the entire glyph set.

--glyphs-file=<path>
  Like --glyphs but reads from a file. Anything after a '#' on any line
  is ignored as comments.

--text=<text>
  Specify characters to include in the subset, as UTF-8 string.

--text-file=<path>
  Like --text but reads from a file. Newline character are not added to
  the subset.

--unicodes=<XXXX>[,<XXXX>...]
  Specify comma/whitespace-separated list of Unicode codepoints or
  ranges as hex numbers, optionally prefixed with 'U+', 'u', etc.
  For example, --unicodes=41-5a,61-7a adds ASCII letters, so does
  the more verbose --unicodes=U+0041-005A,U+0061-007A.
  The special strings '*' will choose all Unicode characters mapped
  by the font.

--unicodes-file=<path>
  Like --unicodes, but reads from a file. Anything after a '#' on any
  line in the file is ignored as comments.

--ignore-missing-glyphs
  Do not fail if some requested glyphs or gids are not available in
  the font.

--no-ignore-missing-glyphs
  Stop and fail if some requested glyphs or gids are not available
  in the font. [default]

--ignore-missing-unicodes [default]
  Do not fail if some requested Unicode characters (including those
  indirectly specified using --text or --text-file) are not available
  in the font.

--no-ignore-missing-unicodes
  Stop and fail if some requested Unicode characters are not available
  in the font.
  Note the default discrepancy between ignoring missing glyphs versus
  unicodes.  This is for historical reasons and in the future
  --no-ignore-missing-unicodes might become default.

Other options
^^^^^^^^^^^^^

For the other options listed below, to see the current value of the option,
pass a value of '?' to it, with or without a '='. In some environments,
you might need to escape the question mark, like this: '--glyph-names\\?'.

Examples::

    $ pyftsubset --glyph-names?
    Current setting for 'glyph-names' is: False
    $ pyftsubset --name-IDs=?
    Current setting for 'name-IDs' is: [0, 1, 2, 3, 4, 5, 6]
    $ pyftsubset --hinting? --no-hinting --hinting?
    Current setting for 'hinting' is: True
    Current setting for 'hinting' is: False

Output options
^^^^^^^^^^^^^^

--output-file=<path>
  The output font file. If not specified, the subsetted font
  will be saved in as font-file.subset.

--flavor=<type>
  Specify flavor of output font file. May be 'woff' or 'woff2'.
  Note that WOFF2 requires the Brotli Python extension, available
  at https://github.com/google/brotli

--with-zopfli
  Use the Google Zopfli algorithm to compress WOFF. The output is 3-8 %
  smaller than pure zlib, but the compression speed is much slower.
  The Zopfli Python bindings are available at:
  https://pypi.python.org/pypi/zopfli

--harfbuzz-repacker
  By default, we serialize GPOS/GSUB using the HarfBuzz Repacker when
  uharfbuzz can be imported and is successful, otherwise fall back to
  the pure-python serializer. Set the option to force using the HarfBuzz
  Repacker (raises an error if uharfbuzz can't be found or fails).

--no-harfbuzz-repacker
  Always use the pure-python serializer even if uharfbuzz is available.

Glyph set expansion
^^^^^^^^^^^^^^^^^^^

These options control how additional glyphs are added to the subset.

--retain-gids
  Retain glyph indices; just empty glyphs not needed in-place.

--notdef-glyph
  Add the '.notdef' glyph to the subset (ie, keep it). [default]

--no-notdef-glyph
  Drop the '.notdef' glyph unless specified in the glyph set. This
  saves a few bytes, but is not possible for Postscript-flavored
  fonts, as those require '.notdef'. For TrueType-flavored fonts,
  this works fine as long as no unsupported glyphs are requested
  from the font.

--notdef-outline
  Keep the outline of '.notdef' glyph. The '.notdef' glyph outline is
  used when glyphs not supported by the font are to be shown. It is not
  needed otherwise.

--no-notdef-outline
  When including a '.notdef' glyph, remove its outline. This saves
  a few bytes. [default]

--recommended-glyphs
  Add glyphs 0, 1, 2, and 3 to the subset, as recommended for
  TrueType-flavored fonts: '.notdef', 'NULL' or '.null', 'CR', 'space'.
  Some legacy software might require this, but no modern system does.

--no-recommended-glyphs
  Do not add glyphs 0, 1, 2, and 3 to the subset, unless specified in
  glyph set. [default]

--no-layout-closure
  Do not expand glyph set to add glyphs produced by OpenType layout
  features.  Instead, OpenType layout features will be subset to only
  rules that are relevant to the otherwise-specified glyph set.

--layout-features[+|-]=<feature>[,<feature>...]
  Specify (=), add to (+=) or exclude from (-=) the comma-separated
  set of OpenType layout feature tags that will be preserved.
  Glyph variants used by the preserved features are added to the
  specified subset glyph set. By default, 'calt', 'ccmp', 'clig', 'curs',
  'dnom', 'frac', 'kern', 'liga', 'locl', 'mark', 'mkmk', 'numr', 'rclt',
  'rlig', 'rvrn', and all features required for script shaping are
  preserved. To see the full list, try '--layout-features=?'.
  Use '*' to keep all features.
  Multiple --layout-features options can be provided if necessary.
  Examples:

    --layout-features+=onum,pnum,ss01
        * Keep the default set of features and 'onum', 'pnum', 'ss01'.
    --layout-features-='mark','mkmk'
        * Keep the default set of features but drop 'mark' and 'mkmk'.
    --layout-features='kern'
        * Only keep the 'kern' feature, drop all others.
    --layout-features=''
        * Drop all features.
    --layout-features='*'
        * Keep all features.
    --layout-features+=aalt --layout-features-=vrt2
        * Keep default set of features plus 'aalt', but drop 'vrt2'.

--layout-scripts[+|-]=<script>[,<script>...]
  Specify (=), add to (+=) or exclude from (-=) the comma-separated
  set of OpenType layout script tags that will be preserved. LangSys tags
  can be appended to script tag, separated by '.', for example:
  'arab.dflt,arab.URD,latn.TRK'. By default all scripts are retained ('*').

Hinting options
^^^^^^^^^^^^^^^

--hinting
  Keep hinting [default]

--no-hinting
  Drop glyph-specific hinting and font-wide hinting tables, as well
  as remove hinting-related bits and pieces from other tables (eg. GPOS).
  See --hinting-tables for list of tables that are dropped by default.
  Instructions and hints are stripped from 'glyf' and 'CFF ' tables
  respectively. This produces (sometimes up to 30%) smaller fonts that
  are suitable for extremely high-resolution systems, like high-end
  mobile devices and retina displays.

Optimization options
^^^^^^^^^^^^^^^^^^^^

--desubroutinize
  Remove CFF use of subroutinizes.  Subroutinization is a way to make CFF
  fonts smaller.  For small subsets however, desubroutinizing might make
  the font smaller.  It has even been reported that desubroutinized CFF
  fonts compress better (produce smaller output) WOFF and WOFF2 fonts.
  Also see note under --no-hinting.

--no-desubroutinize [default]
  Leave CFF subroutinizes as is, only throw away unused subroutinizes.

Font table options
^^^^^^^^^^^^^^^^^^

--drop-tables[+|-]=<table>[,<table>...]
  Specify (=), add to (+=) or exclude from (-=) the comma-separated
  set of tables that will be be dropped.
  By default, the following tables are dropped:
  'BASE', 'JSTF', 'DSIG', 'EBDT', 'EBLC', 'EBSC', 'PCLT', 'LTSH'
  and Graphite tables: 'Feat', 'Glat', 'Gloc', 'Silf', 'Sill'.
  The tool will attempt to subset the remaining tables.

  Examples:

  --drop-tables-=BASE
      * Drop the default set of tables but keep 'BASE'.

  --drop-tables+=GSUB
      * Drop the default set of tables and 'GSUB'.

  --drop-tables=DSIG
      * Only drop the 'DSIG' table, keep all others.

  --drop-tables=
      * Keep all tables.

--no-subset-tables+=<table>[,<table>...]
  Add to the set of tables that will not be subsetted.
  By default, the following tables are included in this list, as
  they do not need subsetting (ignore the fact that 'loca' is listed
  here): 'gasp', 'head', 'hhea', 'maxp', 'vhea', 'OS/2', 'loca', 'name',
  'cvt ', 'fpgm', 'prep', 'VMDX', 'DSIG', 'CPAL', 'MVAR', 'cvar', 'STAT'.
  By default, tables that the tool does not know how to subset and are not
  specified here will be dropped from the font, unless --passthrough-tables
  option is passed.

  Example:

   --no-subset-tables+=FFTM
      * Keep 'FFTM' table in the font by preventing subsetting.

--passthrough-tables
  Do not drop tables that the tool does not know how to subset.

--no-passthrough-tables
  Tables that the tool does not know how to subset and are not specified
  in --no-subset-tables will be dropped from the font. [default]

--hinting-tables[-]=<table>[,<table>...]
  Specify (=), add to (+=) or exclude from (-=) the list of font-wide
  hinting tables that will be dropped if --no-hinting is specified.

  Examples:

  --hinting-tables-=VDMX
      * Drop font-wide hinting tables except 'VDMX'.
  --hinting-tables=
      * Keep all font-wide hinting tables (but strip hints from glyphs).

--legacy-kern
  Keep TrueType 'kern' table even when OpenType 'GPOS' is available.

--no-legacy-kern
  Drop TrueType 'kern' table if OpenType 'GPOS' is available. [default]

Font naming options
^^^^^^^^^^^^^^^^^^^

These options control what is retained in the 'name' table. For numerical
codes, see: http://www.microsoft.com/typography/otspec/name.htm

--name-IDs[+|-]=<nameID>[,<nameID>...]
  Specify (=), add to (+=) or exclude from (-=) the set of 'name' table
  entry nameIDs that will be preserved. By default, only nameIDs between 0
  and 6 are preserved, the rest are dropped. Use '*' to keep all entries.

  Examples:

  --name-IDs+=7,8,9
      * Also keep Trademark, Manufacturer and Designer name entries.
  --name-IDs=
      * Drop all 'name' table entries.
  --name-IDs=*
      * keep all 'name' table entries

--name-legacy
  Keep legacy (non-Unicode) 'name' table entries (0.x, 1.x etc.).
  XXX Note: This might be needed for some fonts that have no Unicode name
  entires for English. See: https://github.com/fonttools/fonttools/issues/146

--no-name-legacy
  Drop legacy (non-Unicode) 'name' table entries [default]

--name-languages[+|-]=<langID>[,<langID>]
  Specify (=), add to (+=) or exclude from (-=) the set of 'name' table
  langIDs that will be preserved. By default only records with langID
  0x0409 (English) are preserved. Use '*' to keep all langIDs.

--obfuscate-names
  Make the font unusable as a system font by replacing name IDs 1, 2, 3, 4,
  and 6 with dummy strings (it is still fully functional as webfont).

Glyph naming and encoding options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

--glyph-names
  Keep PS glyph names in TT-flavored fonts. In general glyph names are
  not needed for correct use of the font. However, some PDF generators
  and PDF viewers might rely on glyph names to extract Unicode text
  from PDF documents.
--no-glyph-names
  Drop PS glyph names in TT-flavored fonts, by using 'post' table
  version 3.0. [default]
--legacy-cmap
  Keep the legacy 'cmap' subtables (0.x, 1.x, 4.x etc.).
--no-legacy-cmap
  Drop the legacy 'cmap' subtables. [default]
--symbol-cmap
  Keep the 3.0 symbol 'cmap'.
--no-symbol-cmap
  Drop the 3.0 symbol 'cmap'. [default]

Other font-specific options
^^^^^^^^^^^^^^^^^^^^^^^^^^^

--recalc-bounds
    Recalculate font bounding boxes.
--no-recalc-bounds
    Keep original font bounding boxes. This is faster and still safe
    for all practical purposes. [default]
--recalc-timestamp
    Set font 'modified' timestamp to current time.
--no-recalc-timestamp
    Do not modify font 'modified' timestamp. [default]
--canonical-order
    Order tables as recommended in the OpenType standard. This is not
    required by the standard, nor by any known implementation.
--no-canonical-order
    Keep original order of font tables. This is faster. [default]
--prune-unicode-ranges
    Update the 'OS/2 ulUnicodeRange*' bits after subsetting. The Unicode
    ranges defined in the OpenType specification v1.7 are intersected with
    the Unicode codepoints specified in the font's Unicode 'cmap' subtables:
    when no overlap is found, the bit will be switched off. However, it will
    *not* be switched on if an intersection is found.  [default]
--no-prune-unicode-ranges
    Don't change the 'OS/2 ulUnicodeRange*' bits.
--prune-codepage-ranges
    Update the 'OS/2 ulCodePageRange*' bits after subsetting.  [default]
--no-prune-codepage-ranges
    Don't change the 'OS/2 ulCodePageRange*' bits.
--recalc-average-width
    Update the 'OS/2 xAvgCharWidth' field after subsetting.
--no-recalc-average-width
    Don't change the 'OS/2 xAvgCharWidth' field. [default]
--recalc-max-context
    Update the 'OS/2 usMaxContext' field after subsetting.
--no-recalc-max-context
    Don't change the 'OS/2 usMaxContext' field. [default]
--font-number=<number>
    Select font number for TrueType Collection (.ttc/.otc), starting from 0.
--pretty-svg
    When subsetting SVG table, use lxml pretty_print=True option to indent
    the XML output (only recommended for debugging purposes).

Application options
^^^^^^^^^^^^^^^^^^^

--verbose
    Display verbose information of the subsetting process.
--timing
    Display detailed timing information of the subsetting process.
--xml
    Display the TTX XML representation of subsetted font.

Example
^^^^^^^

Produce a subset containing the characters ' !"#$%' without performing
size-reducing optimizations::

  $ pyftsubset font.ttf --unicodes="U+0020-0025" \\
    --layout-features=* --glyph-names --symbol-cmap --legacy-cmap \\
    --notdef-glyph --notdef-outline --recommended-glyphs \\
    --name-IDs=* --name-legacy --name-languages=*
"""
)


log = logging.getLogger("fontTools.subset")


def _log_glyphs(self, glyphs, font=None):
    self.info("Glyph names: %s", sorted(glyphs))
    if font:
        reverseGlyphMap = font.getReverseGlyphMap()
        self.info("Glyph IDs:   %s", sorted(reverseGlyphMap[g] for g in glyphs))


# bind "glyphs" function to 'log' object
log.glyphs = MethodType(_log_glyphs, log)

# I use a different timing channel so I can configure it separately from the
# main module's logger
timer = Timer(logger=logging.getLogger("fontTools.subset.timer"))


def _dict_subset(d, glyphs):
    return {g: d[g] for g in glyphs}


def _list_subset(l, indices):
    count = len(l)
    return [l[i] for i in indices if i < count]


@_add_method(otTables.Coverage)
def intersect(self, glyphs):
    """Returns ascending list of matching coverage values."""
    return [i for i, g in enumerate(self.glyphs) if g in glyphs]


@_add_method(otTables.Coverage)
def intersect_glyphs(self, glyphs):
    """Returns set of intersecting glyphs."""
    return set(g for g in self.glyphs if g in glyphs)


@_add_method(otTables.Coverage)
def subset(self, glyphs):
    """Returns ascending list of remaining coverage values."""
    indices = self.intersect(glyphs)
    self.glyphs = [g for g in self.glyphs if g in glyphs]
    return indices


@_add_method(otTables.Coverage)
def remap(self, coverage_map):
    """Remaps coverage."""
    self.glyphs = [self.glyphs[i] for i in coverage_map]


@_add_method(otTables.ClassDef)
def intersect(self, glyphs):
    """Returns ascending list of matching class values."""
    return _uniq_sort(
        ([0] if any(g not in self.classDefs for g in glyphs) else [])
        + [v for g, v in self.classDefs.items() if g in glyphs]
    )


@_add_method(otTables.ClassDef)
def intersect_class(self, glyphs, klass):
    """Returns set of glyphs matching class."""
    if klass == 0:
        return set(g for g in glyphs if g not in self.classDefs)
    return set(g for g, v in self.classDefs.items() if v == klass and g in glyphs)


@_add_method(otTables.ClassDef)
def subset(self, glyphs, remap=False, useClass0=True):
    """Returns ascending list of remaining classes."""
    self.classDefs = {g: v for g, v in self.classDefs.items() if g in glyphs}
    # Note: while class 0 has the special meaning of "not matched",
    # if no glyph will ever /not match/, we can optimize class 0 out too.
    # Only do this if allowed.
    indices = _uniq_sort(
        (
            [0]
            if ((not useClass0) or any(g not in self.classDefs for g in glyphs))
            else []
        )
        + list(self.classDefs.values())
    )
    if remap:
        self.remap(indices)
    return indices


@_add_method(otTables.ClassDef)
def remap(self, class_map):
    """Remaps classes."""
    self.classDefs = {g: class_map.index(v) for g, v in self.classDefs.items()}


@_add_method(otTables.SingleSubst)
def closure_glyphs(self, s, cur_glyphs):
    s.glyphs.update(v for g, v in self.mapping.items() if g in cur_glyphs)


@_add_method(otTables.SingleSubst)
def subset_glyphs(self, s):
    self.mapping = {
        g: v for g, v in self.mapping.items() if g in s.glyphs and v in s.glyphs
    }
    return bool(self.mapping)


@_add_method(otTables.MultipleSubst)
def closure_glyphs(self, s, cur_glyphs):
    for glyph, subst in self.mapping.items():
        if glyph in cur_glyphs:
            s.glyphs.update(subst)


@_add_method(otTables.MultipleSubst)
def subset_glyphs(self, s):
    self.mapping = {
        g: v
        for g, v in self.mapping.items()
        if g in s.glyphs and all(sub in s.glyphs for sub in v)
    }
    return bool(self.mapping)


@_add_method(otTables.AlternateSubst)
def closure_glyphs(self, s, cur_glyphs):
    s.glyphs.update(*(vlist for g, vlist in self.alternates.items() if g in cur_glyphs))


@_add_method(otTables.AlternateSubst)
def subset_glyphs(self, s):
    self.alternates = {
        g: [v for v in vlist if v in s.glyphs]
        for g, vlist in self.alternates.items()
        if g in s.glyphs and any(v in s.glyphs for v in vlist)
    }
    return bool(self.alternates)


@_add_method(otTables.LigatureSubst)
def closure_glyphs(self, s, cur_glyphs):
    s.glyphs.update(
        *(
            [seq.LigGlyph for seq in seqs if all(c in s.glyphs for c in seq.Component)]
            for g, seqs in self.ligatures.items()
            if g in cur_glyphs
        )
    )


@_add_method(otTables.LigatureSubst)
def subset_glyphs(self, s):
    self.ligatures = {g: v for g, v in self.ligatures.items() if g in s.glyphs}
    self.ligatures = {
        g: [
            seq
            for seq in seqs
            if seq.LigGlyph in s.glyphs and all(c in s.glyphs for c in seq.Component)
        ]
        for g, seqs in self.ligatures.items()
    }
    self.ligatures = {g: v for g, v in self.ligatures.items() if v}
    return bool(self.ligatures)


@_add_method(otTables.ReverseChainSingleSubst)
def closure_glyphs(self, s, cur_glyphs):
    if self.Format == 1:
        indices = self.Coverage.intersect(cur_glyphs)
        if not indices or not all(
            c.intersect(s.glyphs)
            for c in self.LookAheadCoverage + self.BacktrackCoverage
        ):
            return
        s.glyphs.update(self.Substitute[i] for i in indices)
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.ReverseChainSingleSubst)
def subset_glyphs(self, s):
    if self.Format == 1:
        indices = self.Coverage.subset(s.glyphs)
        self.Substitute = _list_subset(self.Substitute, indices)
        # Now drop rules generating glyphs we don't want
        indices = [i for i, sub in enumerate(self.Substitute) if sub in s.glyphs]
        self.Substitute = _list_subset(self.Substitute, indices)
        self.Coverage.remap(indices)
        self.GlyphCount = len(self.Substitute)
        return bool(
            self.GlyphCount
            and all(
                c.subset(s.glyphs)
                for c in self.LookAheadCoverage + self.BacktrackCoverage
            )
        )
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.Device)
def is_hinting(self):
    return self.DeltaFormat in (1, 2, 3)


@_add_method(otTables.ValueRecord)
def prune_hints(self):
    for name in ["XPlaDevice", "YPlaDevice", "XAdvDevice", "YAdvDevice"]:
        v = getattr(self, name, None)
        if v is not None and v.is_hinting():
            delattr(self, name)


@_add_method(otTables.SinglePos)
def subset_glyphs(self, s):
    if self.Format == 1:
        return len(self.Coverage.subset(s.glyphs))
    elif self.Format == 2:
        indices = self.Coverage.subset(s.glyphs)
        values = self.Value
        count = len(values)
        self.Value = [values[i] for i in indices if i < count]
        self.ValueCount = len(self.Value)
        return bool(self.ValueCount)
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.SinglePos)
def prune_post_subset(self, font, options):
    if self.Value is None:
        assert self.ValueFormat == 0
        return True

    # Shrink ValueFormat
    if self.Format == 1:
        if not options.hinting:
            self.Value.prune_hints()
        self.ValueFormat = self.Value.getEffectiveFormat()
    elif self.Format == 2:
        if None in self.Value:
            assert self.ValueFormat == 0
            assert all(v is None for v in self.Value)
        else:
            if not options.hinting:
                for v in self.Value:
                    v.prune_hints()
            self.ValueFormat = reduce(
                int.__or__, [v.getEffectiveFormat() for v in self.Value], 0
            )

    # Downgrade to Format 1 if all ValueRecords are the same
    if self.Format == 2 and all(v == self.Value[0] for v in self.Value):
        self.Format = 1
        self.Value = self.Value[0] if self.ValueFormat != 0 else None
        del self.ValueCount

    return True


@_add_method(otTables.PairPos)
def subset_glyphs(self, s):
    if self.Format == 1:
        indices = self.Coverage.subset(s.glyphs)
        pairs = self.PairSet
        count = len(pairs)
        self.PairSet = [pairs[i] for i in indices if i < count]
        for p in self.PairSet:
            p.PairValueRecord = [
                r for r in p.PairValueRecord if r.SecondGlyph in s.glyphs
            ]
            p.PairValueCount = len(p.PairValueRecord)
        # Remove empty pairsets
        indices = [i for i, p in enumerate(self.PairSet) if p.PairValueCount]
        self.Coverage.remap(indices)
        self.PairSet = _list_subset(self.PairSet, indices)
        self.PairSetCount = len(self.PairSet)
        return bool(self.PairSetCount)
    elif self.Format == 2:
        class1_map = [
            c
            for c in self.ClassDef1.subset(
                s.glyphs.intersection(self.Coverage.glyphs), remap=True
            )
            if c < self.Class1Count
        ]
        class2_map = [
            c
            for c in self.ClassDef2.subset(s.glyphs, remap=True, useClass0=False)
            if c < self.Class2Count
        ]
        self.Class1Record = [self.Class1Record[i] for i in class1_map]
        for c in self.Class1Record:
            c.Class2Record = [c.Class2Record[i] for i in class2_map]
        self.Class1Count = len(class1_map)
        self.Class2Count = len(class2_map)
        # If only Class2 0 left, no need to keep anything.
        return bool(
            self.Class1Count
            and (self.Class2Count > 1)
            and self.Coverage.subset(s.glyphs)
        )
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.PairPos)
def prune_post_subset(self, font, options):
    if not options.hinting:
        attr1, attr2 = {
            1: ("PairSet", "PairValueRecord"),
            2: ("Class1Record", "Class2Record"),
        }[self.Format]

        self.ValueFormat1 = self.ValueFormat2 = 0
        for row in getattr(self, attr1):
            for r in getattr(row, attr2):
                if r.Value1:
                    r.Value1.prune_hints()
                    self.ValueFormat1 |= r.Value1.getEffectiveFormat()
                if r.Value2:
                    r.Value2.prune_hints()
                    self.ValueFormat2 |= r.Value2.getEffectiveFormat()

    return bool(self.ValueFormat1 | self.ValueFormat2)


@_add_method(otTables.CursivePos)
def subset_glyphs(self, s):
    if self.Format == 1:
        indices = self.Coverage.subset(s.glyphs)
        records = self.EntryExitRecord
        count = len(records)
        self.EntryExitRecord = [records[i] for i in indices if i < count]
        self.EntryExitCount = len(self.EntryExitRecord)
        return bool(self.EntryExitCount)
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.Anchor)
def prune_hints(self):
    if self.Format == 2:
        self.Format = 1
    elif self.Format == 3:
        for name in ("XDeviceTable", "YDeviceTable"):
            v = getattr(self, name, None)
            if v is not None and v.is_hinting():
                setattr(self, name, None)
        if self.XDeviceTable is None and self.YDeviceTable is None:
            self.Format = 1


@_add_method(otTables.CursivePos)
def prune_post_subset(self, font, options):
    if not options.hinting:
        for rec in self.EntryExitRecord:
            if rec.EntryAnchor:
                rec.EntryAnchor.prune_hints()
            if rec.ExitAnchor:
                rec.ExitAnchor.prune_hints()
    return True


@_add_method(otTables.MarkBasePos)
def subset_glyphs(self, s):
    if self.Format == 1:
        mark_indices = self.MarkCoverage.subset(s.glyphs)
        self.MarkArray.MarkRecord = _list_subset(
            self.MarkArray.MarkRecord, mark_indices
        )
        self.MarkArray.MarkCount = len(self.MarkArray.MarkRecord)
        base_indices = self.BaseCoverage.subset(s.glyphs)
        self.BaseArray.BaseRecord = _list_subset(
            self.BaseArray.BaseRecord, base_indices
        )
        self.BaseArray.BaseCount = len(self.BaseArray.BaseRecord)
        # Prune empty classes
        class_indices = _uniq_sort(v.Class for v in self.MarkArray.MarkRecord)
        self.ClassCount = len(class_indices)
        for m in self.MarkArray.MarkRecord:
            m.Class = class_indices.index(m.Class)
        for b in self.BaseArray.BaseRecord:
            b.BaseAnchor = _list_subset(b.BaseAnchor, class_indices)
        return bool(
            self.ClassCount and self.MarkArray.MarkCount and self.BaseArray.BaseCount
        )
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.MarkBasePos)
def prune_post_subset(self, font, options):
    if not options.hinting:
        for m in self.MarkArray.MarkRecord:
            if m.MarkAnchor:
                m.MarkAnchor.prune_hints()
        for b in self.BaseArray.BaseRecord:
            for a in b.BaseAnchor:
                if a:
                    a.prune_hints()
    return True


@_add_method(otTables.MarkLigPos)
def subset_glyphs(self, s):
    if self.Format == 1:
        mark_indices = self.MarkCoverage.subset(s.glyphs)
        self.MarkArray.MarkRecord = _list_subset(
            self.MarkArray.MarkRecord, mark_indices
        )
        self.MarkArray.MarkCount = len(self.MarkArray.MarkRecord)
        ligature_indices = self.LigatureCoverage.subset(s.glyphs)
        self.LigatureArray.LigatureAttach = _list_subset(
            self.LigatureArray.LigatureAttach, ligature_indices
        )
        self.LigatureArray.LigatureCount = len(self.LigatureArray.LigatureAttach)
        # Prune empty classes
        class_indices = _uniq_sort(v.Class for v in self.MarkArray.MarkRecord)
        self.ClassCount = len(class_indices)
        for m in self.MarkArray.MarkRecord:
            m.Class = class_indices.index(m.Class)
        for l in self.LigatureArray.LigatureAttach:
            if l is None:
                continue
            for c in l.ComponentRecord:
                c.LigatureAnchor = _list_subset(c.LigatureAnchor, class_indices)
        return bool(
            self.ClassCount
            and self.MarkArray.MarkCount
            and self.LigatureArray.LigatureCount
        )
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.MarkLigPos)
def prune_post_subset(self, font, options):
    if not options.hinting:
        for m in self.MarkArray.MarkRecord:
            if m.MarkAnchor:
                m.MarkAnchor.prune_hints()
        for l in self.LigatureArray.LigatureAttach:
            if l is None:
                continue
            for c in l.ComponentRecord:
                for a in c.LigatureAnchor:
                    if a:
                        a.prune_hints()
    return True


@_add_method(otTables.MarkMarkPos)
def subset_glyphs(self, s):
    if self.Format == 1:
        mark1_indices = self.Mark1Coverage.subset(s.glyphs)
        self.Mark1Array.MarkRecord = _list_subset(
            self.Mark1Array.MarkRecord, mark1_indices
        )
        self.Mark1Array.MarkCount = len(self.Mark1Array.MarkRecord)
        mark2_indices = self.Mark2Coverage.subset(s.glyphs)
        self.Mark2Array.Mark2Record = _list_subset(
            self.Mark2Array.Mark2Record, mark2_indices
        )
        self.Mark2Array.MarkCount = len(self.Mark2Array.Mark2Record)
        # Prune empty classes
        class_indices = _uniq_sort(v.Class for v in self.Mark1Array.MarkRecord)
        self.ClassCount = len(class_indices)
        for m in self.Mark1Array.MarkRecord:
            m.Class = class_indices.index(m.Class)
        for b in self.Mark2Array.Mark2Record:
            b.Mark2Anchor = _list_subset(b.Mark2Anchor, class_indices)
        return bool(
            self.ClassCount and self.Mark1Array.MarkCount and self.Mark2Array.MarkCount
        )
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.MarkMarkPos)
def prune_post_subset(self, font, options):
    if not options.hinting:
        for m in self.Mark1Array.MarkRecord:
            if m.MarkAnchor:
                m.MarkAnchor.prune_hints()
        for b in self.Mark2Array.Mark2Record:
            for m in b.Mark2Anchor:
                if m:
                    m.prune_hints()
    return True


@_add_method(
    otTables.SingleSubst,
    otTables.MultipleSubst,
    otTables.AlternateSubst,
    otTables.LigatureSubst,
    otTables.ReverseChainSingleSubst,
    otTables.SinglePos,
    otTables.PairPos,
    otTables.CursivePos,
    otTables.MarkBasePos,
    otTables.MarkLigPos,
    otTables.MarkMarkPos,
)
def subset_lookups(self, lookup_indices):
    pass


@_add_method(
    otTables.SingleSubst,
    otTables.MultipleSubst,
    otTables.AlternateSubst,
    otTables.LigatureSubst,
    otTables.ReverseChainSingleSubst,
    otTables.SinglePos,
    otTables.PairPos,
    otTables.CursivePos,
    otTables.MarkBasePos,
    otTables.MarkLigPos,
    otTables.MarkMarkPos,
)
def collect_lookups(self):
    return []


@_add_method(
    otTables.SingleSubst,
    otTables.MultipleSubst,
    otTables.AlternateSubst,
    otTables.LigatureSubst,
    otTables.ReverseChainSingleSubst,
    otTables.ContextSubst,
    otTables.ChainContextSubst,
    otTables.ContextPos,
    otTables.ChainContextPos,
)
def prune_post_subset(self, font, options):
    return True


@_add_method(
    otTables.SingleSubst, otTables.AlternateSubst, otTables.ReverseChainSingleSubst
)
def may_have_non_1to1(self):
    return False


@_add_method(
    otTables.MultipleSubst,
    otTables.LigatureSubst,
    otTables.ContextSubst,
    otTables.ChainContextSubst,
)
def may_have_non_1to1(self):
    return True


@_add_method(
    otTables.ContextSubst,
    otTables.ChainContextSubst,
    otTables.ContextPos,
    otTables.ChainContextPos,
)
def __subset_classify_context(self):
    class ContextHelper(object):
        def __init__(self, klass, Format):
            if klass.__name__.endswith("Subst"):
                Typ = "Sub"
                Type = "Subst"
            else:
                Typ = "Pos"
                Type = "Pos"
            if klass.__name__.startswith("Chain"):
                Chain = "Chain"
                InputIdx = 1
                DataLen = 3
            else:
                Chain = ""
                InputIdx = 0
                DataLen = 1
            ChainTyp = Chain + Typ

            self.Typ = Typ
            self.Type = Type
            self.Chain = Chain
            self.ChainTyp = ChainTyp
            self.InputIdx = InputIdx
            self.DataLen = DataLen

            self.LookupRecord = Type + "LookupRecord"

            if Format == 1:
                Coverage = lambda r: r.Coverage
                ChainCoverage = lambda r: r.Coverage
                ContextData = lambda r: (None,)
                ChainContextData = lambda r: (None, None, None)
                SetContextData = None
                SetChainContextData = None
                RuleData = lambda r: (r.Input,)
                ChainRuleData = lambda r: (r.Backtrack, r.Input, r.LookAhead)

                def SetRuleData(r, d):
                    (r.Input,) = d
                    (r.GlyphCount,) = (len(x) + 1 for x in d)

                def ChainSetRuleData(r, d):
                    (r.Backtrack, r.Input, r.LookAhead) = d
                    (
                        r.BacktrackGlyphCount,
                        r.InputGlyphCount,
                        r.LookAheadGlyphCount,
                    ) = (len(d[0]), len(d[1]) + 1, len(d[2]))

            elif Format == 2:
                Coverage = lambda r: r.Coverage
                ChainCoverage = lambda r: r.Coverage
                ContextData = lambda r: (r.ClassDef,)
                ChainContextData = lambda r: (
                    r.BacktrackClassDef,
                    r.InputClassDef,
                    r.LookAheadClassDef,
                )

                def SetContextData(r, d):
                    (r.ClassDef,) = d

                def SetChainContextData(r, d):
                    (r.BacktrackClassDef, r.InputClassDef, r.LookAheadClassDef) = d

                RuleData = lambda r: (r.Class,)
                ChainRuleData = lambda r: (r.Backtrack, r.Input, r.LookAhead)

                def SetRuleData(r, d):
                    (r.Class,) = d
                    (r.GlyphCount,) = (len(x) + 1 for x in d)

                def ChainSetRuleData(r, d):
                    (r.Backtrack, r.Input, r.LookAhead) = d
                    (
                        r.BacktrackGlyphCount,
                        r.InputGlyphCount,
                        r.LookAheadGlyphCount,
                    ) = (len(d[0]), len(d[1]) + 1, len(d[2]))

            elif Format == 3:
                Coverage = lambda r: r.Coverage[0]
                ChainCoverage = lambda r: r.InputCoverage[0]
                ContextData = None
                ChainContextData = None
                SetContextData = None
                SetChainContextData = None
                RuleData = lambda r: r.Coverage
                ChainRuleData = lambda r: (
                    r.BacktrackCoverage + r.InputCoverage + r.LookAheadCoverage
                )

                def SetRuleData(r, d):
                    (r.Coverage,) = d
                    (r.GlyphCount,) = (len(x) for x in d)

                def ChainSetRuleData(r, d):
                    (r.BacktrackCoverage, r.InputCoverage, r.LookAheadCoverage) = d
                    (
                        r.BacktrackGlyphCount,
                        r.InputGlyphCount,
                        r.LookAheadGlyphCount,
                    ) = (len(x) for x in d)

            else:
                assert 0, "unknown format: %s" % Format

            if Chain:
                self.Coverage = ChainCoverage
                self.ContextData = ChainContextData
                self.SetContextData = SetChainContextData
                self.RuleData = ChainRuleData
                self.SetRuleData = ChainSetRuleData
            else:
                self.Coverage = Coverage
                self.ContextData = ContextData
                self.SetContextData = SetContextData
                self.RuleData = RuleData
                self.SetRuleData = SetRuleData

            if Format == 1:
                self.Rule = ChainTyp + "Rule"
                self.RuleCount = ChainTyp + "RuleCount"
                self.RuleSet = ChainTyp + "RuleSet"
                self.RuleSetCount = ChainTyp + "RuleSetCount"
                self.Intersect = lambda glyphs, c, r: [r] if r in glyphs else []
            elif Format == 2:
                self.Rule = ChainTyp + "ClassRule"
                self.RuleCount = ChainTyp + "ClassRuleCount"
                self.RuleSet = ChainTyp + "ClassSet"
                self.RuleSetCount = ChainTyp + "ClassSetCount"
                self.Intersect = lambda glyphs, c, r: (
                    c.intersect_class(glyphs, r)
                    if c
                    else (set(glyphs) if r == 0 else set())
                )

                self.ClassDef = "InputClassDef" if Chain else "ClassDef"
                self.ClassDefIndex = 1 if Chain else 0
                self.Input = "Input" if Chain else "Class"
            elif Format == 3:
                self.Input = "InputCoverage" if Chain else "Coverage"

    if self.Format not in [1, 2, 3]:
        return None  # Don't shoot the messenger; let it go
    if not hasattr(self.__class__, "_subset__ContextHelpers"):
        self.__class__._subset__ContextHelpers = {}
    if self.Format not in self.__class__._subset__ContextHelpers:
        helper = ContextHelper(self.__class__, self.Format)
        self.__class__._subset__ContextHelpers[self.Format] = helper
    return self.__class__._subset__ContextHelpers[self.Format]


@_add_method(otTables.ContextSubst, otTables.ChainContextSubst)
def closure_glyphs(self, s, cur_glyphs):
    c = self.__subset_classify_context()

    indices = c.Coverage(self).intersect(cur_glyphs)
    if not indices:
        return []
    cur_glyphs = c.Coverage(self).intersect_glyphs(cur_glyphs)

    if self.Format == 1:
        ContextData = c.ContextData(self)
        rss = getattr(self, c.RuleSet)
        rssCount = getattr(self, c.RuleSetCount)
        for i in indices:
            if i >= rssCount or not rss[i]:
                continue
            for r in getattr(rss[i], c.Rule):
                if not r:
                    continue
                if not all(
                    all(c.Intersect(s.glyphs, cd, k) for k in klist)
                    for cd, klist in zip(ContextData, c.RuleData(r))
                ):
                    continue
                chaos = set()
                for ll in getattr(r, c.LookupRecord):
                    if not ll:
                        continue
                    seqi = ll.SequenceIndex
                    if seqi in chaos:
                        # TODO Can we improve this?
                        pos_glyphs = None
                    else:
                        if seqi == 0:
                            pos_glyphs = frozenset([c.Coverage(self).glyphs[i]])
                        else:
                            pos_glyphs = frozenset([r.Input[seqi - 1]])
                    lookup = s.table.LookupList.Lookup[ll.LookupListIndex]
                    chaos.add(seqi)
                    if lookup.may_have_non_1to1():
                        chaos.update(range(seqi, len(r.Input) + 2))
                    lookup.closure_glyphs(s, cur_glyphs=pos_glyphs)
    elif self.Format == 2:
        ClassDef = getattr(self, c.ClassDef)
        indices = ClassDef.intersect(cur_glyphs)
        ContextData = c.ContextData(self)
        rss = getattr(self, c.RuleSet)
        rssCount = getattr(self, c.RuleSetCount)
        for i in indices:
            if i >= rssCount or not rss[i]:
                continue
            for r in getattr(rss[i], c.Rule):
                if not r:
                    continue
                if not all(
                    all(c.Intersect(s.glyphs, cd, k) for k in klist)
                    for cd, klist in zip(ContextData, c.RuleData(r))
                ):
                    continue
                chaos = set()
                for ll in getattr(r, c.LookupRecord):
                    if not ll:
                        continue
                    seqi = ll.SequenceIndex
                    if seqi in chaos:
                        # TODO Can we improve this?
                        pos_glyphs = None
                    else:
                        if seqi == 0:
                            pos_glyphs = frozenset(
                                ClassDef.intersect_class(cur_glyphs, i)
                            )
                        else:
                            pos_glyphs = frozenset(
                                ClassDef.intersect_class(
                                    s.glyphs, getattr(r, c.Input)[seqi - 1]
                                )
                            )
                    lookup = s.table.LookupList.Lookup[ll.LookupListIndex]
                    chaos.add(seqi)
                    if lookup.may_have_non_1to1():
                        chaos.update(range(seqi, len(getattr(r, c.Input)) + 2))
                    lookup.closure_glyphs(s, cur_glyphs=pos_glyphs)
    elif self.Format == 3:
        if not all(x is not None and x.intersect(s.glyphs) for x in c.RuleData(self)):
            return []
        r = self
        input_coverages = getattr(r, c.Input)
        chaos = set()
        for ll in getattr(r, c.LookupRecord):
            if not ll:
                continue
            seqi = ll.SequenceIndex
            if seqi in chaos:
                # TODO Can we improve this?
                pos_glyphs = None
            else:
                if seqi == 0:
                    pos_glyphs = frozenset(cur_glyphs)
                else:
                    pos_glyphs = frozenset(
                        input_coverages[seqi].intersect_glyphs(s.glyphs)
                    )
            lookup = s.table.LookupList.Lookup[ll.LookupListIndex]
            chaos.add(seqi)
            if lookup.may_have_non_1to1():
                chaos.update(range(seqi, len(input_coverages) + 1))
            lookup.closure_glyphs(s, cur_glyphs=pos_glyphs)
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(
    otTables.ContextSubst,
    otTables.ContextPos,
    otTables.ChainContextSubst,
    otTables.ChainContextPos,
)
def subset_glyphs(self, s):
    c = self.__subset_classify_context()

    if self.Format == 1:
        indices = self.Coverage.subset(s.glyphs)
        rss = getattr(self, c.RuleSet)
        rssCount = getattr(self, c.RuleSetCount)
        rss = [rss[i] for i in indices if i < rssCount]
        for rs in rss:
            if not rs:
                continue
            ss = getattr(rs, c.Rule)
            ss = [
                r
                for r in ss
                if r
                and all(all(g in s.glyphs for g in glist) for glist in c.RuleData(r))
            ]
            setattr(rs, c.Rule, ss)
            setattr(rs, c.RuleCount, len(ss))
        # Prune empty rulesets
        indices = [i for i, rs in enumerate(rss) if rs and getattr(rs, c.Rule)]
        self.Coverage.remap(indices)
        rss = _list_subset(rss, indices)
        setattr(self, c.RuleSet, rss)
        setattr(self, c.RuleSetCount, len(rss))
        return bool(rss)
    elif self.Format == 2:
        if not self.Coverage.subset(s.glyphs):
            return False
        ContextData = c.ContextData(self)
        klass_maps = [
            x.subset(s.glyphs, remap=True) if x else None for x in ContextData
        ]

        # Keep rulesets for class numbers that survived.
        indices = klass_maps[c.ClassDefIndex]
        rss = getattr(self, c.RuleSet)
        rssCount = getattr(self, c.RuleSetCount)
        rss = [rss[i] for i in indices if i < rssCount]
        del rssCount
        # Delete, but not renumber, unreachable rulesets.
        indices = getattr(self, c.ClassDef).intersect(self.Coverage.glyphs)
        rss = [rss if i in indices else None for i, rss in enumerate(rss)]

        for rs in rss:
            if not rs:
                continue
            ss = getattr(rs, c.Rule)
            ss = [
                r
                for r in ss
                if r
                and all(
                    all(k in klass_map for k in klist)
                    for klass_map, klist in zip(klass_maps, c.RuleData(r))
                )
            ]
            setattr(rs, c.Rule, ss)
            setattr(rs, c.RuleCount, len(ss))

            # Remap rule classes
            for r in ss:
                c.SetRuleData(
                    r,
                    [
                        [klass_map.index(k) for k in klist]
                        for klass_map, klist in zip(klass_maps, c.RuleData(r))
                    ],
                )

        # Prune empty rulesets
        rss = [rs if rs and getattr(rs, c.Rule) else None for rs in rss]
        while rss and rss[-1] is None:
            del rss[-1]
        setattr(self, c.RuleSet, rss)
        setattr(self, c.RuleSetCount, len(rss))

        # TODO: We can do a second round of remapping class values based
        # on classes that are actually used in at least one rule.	Right
        # now we subset classes to c.glyphs only.	Or better, rewrite
        # the above to do that.

        return bool(rss)
    elif self.Format == 3:
        return all(x is not None and x.subset(s.glyphs) for x in c.RuleData(self))
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(
    otTables.ContextSubst,
    otTables.ChainContextSubst,
    otTables.ContextPos,
    otTables.ChainContextPos,
)
def subset_lookups(self, lookup_indices):
    c = self.__subset_classify_context()

    if self.Format in [1, 2]:
        for rs in getattr(self, c.RuleSet):
            if not rs:
                continue
            for r in getattr(rs, c.Rule):
                if not r:
                    continue
                setattr(
                    r,
                    c.LookupRecord,
                    [
                        ll
                        for ll in getattr(r, c.LookupRecord)
                        if ll and ll.LookupListIndex in lookup_indices
                    ],
                )
                for ll in getattr(r, c.LookupRecord):
                    if not ll:
                        continue
                    ll.LookupListIndex = lookup_indices.index(ll.LookupListIndex)
    elif self.Format == 3:
        setattr(
            self,
            c.LookupRecord,
            [
                ll
                for ll in getattr(self, c.LookupRecord)
                if ll and ll.LookupListIndex in lookup_indices
            ],
        )
        for ll in getattr(self, c.LookupRecord):
            if not ll:
                continue
            ll.LookupListIndex = lookup_indices.index(ll.LookupListIndex)
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(
    otTables.ContextSubst,
    otTables.ChainContextSubst,
    otTables.ContextPos,
    otTables.ChainContextPos,
)
def collect_lookups(self):
    c = self.__subset_classify_context()

    if self.Format in [1, 2]:
        return [
            ll.LookupListIndex
            for rs in getattr(self, c.RuleSet)
            if rs
            for r in getattr(rs, c.Rule)
            if r
            for ll in getattr(r, c.LookupRecord)
            if ll
        ]
    elif self.Format == 3:
        return [ll.LookupListIndex for ll in getattr(self, c.LookupRecord) if ll]
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.ExtensionSubst)
def closure_glyphs(self, s, cur_glyphs):
    if self.Format == 1:
        self.ExtSubTable.closure_glyphs(s, cur_glyphs)
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.ExtensionSubst)
def may_have_non_1to1(self):
    if self.Format == 1:
        return self.ExtSubTable.may_have_non_1to1()
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.ExtensionSubst, otTables.ExtensionPos)
def subset_glyphs(self, s):
    if self.Format == 1:
        return self.ExtSubTable.subset_glyphs(s)
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.ExtensionSubst, otTables.ExtensionPos)
def prune_post_subset(self, font, options):
    if self.Format == 1:
        return self.ExtSubTable.prune_post_subset(font, options)
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.ExtensionSubst, otTables.ExtensionPos)
def subset_lookups(self, lookup_indices):
    if self.Format == 1:
        return self.ExtSubTable.subset_lookups(lookup_indices)
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.ExtensionSubst, otTables.ExtensionPos)
def collect_lookups(self):
    if self.Format == 1:
        return self.ExtSubTable.collect_lookups()
    else:
        assert 0, "unknown format: %s" % self.Format


@_add_method(otTables.Lookup)
def closure_glyphs(self, s, cur_glyphs=None):
    if cur_glyphs is None:
        cur_glyphs = frozenset(s.glyphs)

    # Memoize
    key = id(self)
    doneLookups = s._doneLookups
    count, covered = doneLookups.get(key, (0, None))
    if count != len(s.glyphs):
        count, covered = doneLookups[key] = (len(s.glyphs), set())
    if cur_glyphs.issubset(covered):
        return
    covered.update(cur_glyphs)

    for st in self.SubTable:
        if not st:
            continue
        st.closure_glyphs(s, cur_glyphs)


@_add_method(otTables.Lookup)
def subset_glyphs(self, s):
    self.SubTable = [st for st in self.SubTable if st and st.subset_glyphs(s)]
    self.SubTableCount = len(self.SubTable)
    if hasattr(self, "MarkFilteringSet") and self.MarkFilteringSet is not None:
        if self.MarkFilteringSet not in s.used_mark_sets:
            self.MarkFilteringSet = None
            self.LookupFlag &= ~0x10
        else:
            self.MarkFilteringSet = s.used_mark_sets.index(self.MarkFilteringSet)
    return bool(self.SubTableCount)


@_add_method(otTables.Lookup)
def prune_post_subset(self, font, options):
    ret = False
    for st in self.SubTable:
        if not st:
            continue
        if st.prune_post_subset(font, options):
            ret = True
    return ret


@_add_method(otTables.Lookup)
def subset_lookups(self, lookup_indices):
    for s in self.SubTable:
        s.subset_lookups(lookup_indices)


@_add_method(otTables.Lookup)
def collect_lookups(self):
    return sum((st.collect_lookups() for st in self.SubTable if st), [])


@_add_method(otTables.Lookup)
def may_have_non_1to1(self):
    return any(st.may_have_non_1to1() for st in self.SubTable if st)


@_add_method(otTables.LookupList)
def subset_glyphs(self, s):
    """Returns the indices of nonempty lookups."""
    return [i for i, l in enumerate(self.Lookup) if l and l.subset_glyphs(s)]


@_add_method(otTables.LookupList)
def prune_post_subset(self, font, options):
    ret = False
    for l in self.Lookup:
        if not l:
            continue
        if l.prune_post_subset(font, options):
            ret = True
    return ret


@_add_method(otTables.LookupList)
def subset_lookups(self, lookup_indices):
    self.ensureDecompiled()
    self.Lookup = [self.Lookup[i] for i in lookup_indices if i < self.LookupCount]
    self.LookupCount = len(self.Lookup)
    for l in self.Lookup:
        l.subset_lookups(lookup_indices)


@_add_method(otTables.LookupList)
def neuter_lookups(self, lookup_indices):
    """Sets lookups not in lookup_indices to None."""
    self.ensureDecompiled()
    self.Lookup = [
        l if i in lookup_indices else None for i, l in enumerate(self.Lookup)
    ]


@_add_method(otTables.LookupList)
def closure_lookups(self, lookup_indices):
    """Returns sorted index of all lookups reachable from lookup_indices."""
    lookup_indices = _uniq_sort(lookup_indices)
    recurse = lookup_indices
    while True:
        recurse_lookups = sum(
            (self.Lookup[i].collect_lookups() for i in recurse if i < self.LookupCount),
            [],
        )
        recurse_lookups = [
            l
            for l in recurse_lookups
            if l not in lookup_indices and l < self.LookupCount
        ]
        if not recurse_lookups:
            return _uniq_sort(lookup_indices)
        recurse_lookups = _uniq_sort(recurse_lookups)
        lookup_indices.extend(recurse_lookups)
        recurse = recurse_lookups


@_add_method(otTables.Feature)
def subset_lookups(self, lookup_indices):
    """ "Returns True if feature is non-empty afterwards."""
    self.LookupListIndex = [l for l in self.LookupListIndex if l in lookup_indices]
    # Now map them.
    self.LookupListIndex = [lookup_indices.index(l) for l in self.LookupListIndex]
    self.LookupCount = len(self.LookupListIndex)
    # keep 'size' feature even if it contains no lookups; but drop any other
    # empty feature (e.g. FeatureParams for stylistic set names)
    # https://github.com/fonttools/fonttools/issues/2324
    return self.LookupCount or isinstance(
        self.FeatureParams, otTables.FeatureParamsSize
    )


@_add_method(otTables.FeatureList)
def subset_lookups(self, lookup_indices):
    """Returns the indices of nonempty features."""
    # Note: Never ever drop feature 'pref', even if it's empty.
    # HarfBuzz chooses shaper for Khmer based on presence of this
    # feature.	See thread at:
    # http://lists.freedesktop.org/archives/harfbuzz/2012-November/002660.html
    return [
        i
        for i, f in enumerate(self.FeatureRecord)
        if (f.Feature.subset_lookups(lookup_indices) or f.FeatureTag == "pref")
    ]


@_add_method(otTables.FeatureList)
def collect_lookups(self, feature_indices):
    return sum(
        (
            self.FeatureRecord[i].Feature.LookupListIndex
            for i in feature_indices
            if i < self.FeatureCount
        ),
        [],
    )


@_add_method(otTables.FeatureList)
def subset_features(self, feature_indices):
    self.ensureDecompiled()
    self.FeatureRecord = _list_subset(self.FeatureRecord, feature_indices)
    self.FeatureCount = len(self.FeatureRecord)
    return bool(self.FeatureCount)


@_add_method(otTables.FeatureTableSubstitution)
def subset_lookups(self, lookup_indices):
    """Returns the indices of nonempty features."""
    return [
        r.FeatureIndex
        for r in self.SubstitutionRecord
        if r.Feature.subset_lookups(lookup_indices)
    ]


@_add_method(otTables.FeatureVariations)
def subset_lookups(self, lookup_indices):
    """Returns the indices of nonempty features."""
    return sum(
        (
            f.FeatureTableSubstitution.subset_lookups(lookup_indices)
            for f in self.FeatureVariationRecord
        ),
        [],
    )


@_add_method(otTables.FeatureVariations)
def collect_lookups(self, feature_indices):
    return sum(
        (
            r.Feature.LookupListIndex
            for vr in self.FeatureVariationRecord
            for r in vr.FeatureTableSubstitution.SubstitutionRecord
            if r.FeatureIndex in feature_indices
        ),
        [],
    )


@_add_method(otTables.FeatureTableSubstitution)
def subset_features(self, feature_indices):
    self.ensureDecompiled()
    self.SubstitutionRecord = [
        r for r in self.SubstitutionRecord if r.FeatureIndex in feature_indices
    ]
    # remap feature indices
    for r in self.SubstitutionRecord:
        r.FeatureIndex = feature_indices.index(r.FeatureIndex)
    self.SubstitutionCount = len(self.SubstitutionRecord)
    return bool(self.SubstitutionCount)


@_add_method(otTables.FeatureVariations)
def subset_features(self, feature_indices):
    self.ensureDecompiled()
    for r in self.FeatureVariationRecord:
        r.FeatureTableSubstitution.subset_features(feature_indices)
    # Prune empty records at the end only
    # https://github.com/fonttools/fonttools/issues/1881
    while (
        self.FeatureVariationRecord
        and not self.FeatureVariationRecord[
            -1
        ].FeatureTableSubstitution.SubstitutionCount
    ):
        self.FeatureVariationRecord.pop()
    self.FeatureVariationCount = len(self.FeatureVariationRecord)
    return bool(self.FeatureVariationCount)


@_add_method(otTables.DefaultLangSys, otTables.LangSys)
def subset_features(self, feature_indices):
    if self.ReqFeatureIndex in feature_indices:
        self.ReqFeatureIndex = feature_indices.index(self.ReqFeatureIndex)
    else:
        self.ReqFeatureIndex = 65535
    self.FeatureIndex = [f for f in self.FeatureIndex if f in feature_indices]
    # Now map them.
    self.FeatureIndex = [
        feature_indices.index(f) for f in self.FeatureIndex if f in feature_indices
    ]
    self.FeatureCount = len(self.FeatureIndex)
    return bool(self.FeatureCount or self.ReqFeatureIndex != 65535)


@_add_method(otTables.DefaultLangSys, otTables.LangSys)
def collect_features(self):
    feature_indices = self.FeatureIndex[:]
    if self.ReqFeatureIndex != 65535:
        feature_indices.append(self.ReqFeatureIndex)
    return _uniq_sort(feature_indices)


@_add_method(otTables.Script)
def subset_features(self, feature_indices, keepEmptyDefaultLangSys=False):
    if (
        self.DefaultLangSys
        and not self.DefaultLangSys.subset_features(feature_indices)
        and not keepEmptyDefaultLangSys
    ):
        self.DefaultLangSys = None
    self.LangSysRecord = [
        l for l in self.LangSysRecord if l.LangSys.subset_features(feature_indices)
    ]
    self.LangSysCount = len(self.LangSysRecord)
    return bool(self.LangSysCount or self.DefaultLangSys)


@_add_method(otTables.Script)
def collect_features(self):
    feature_indices = [l.LangSys.collect_features() for l in self.LangSysRecord]
    if self.DefaultLangSys:
        feature_indices.append(self.DefaultLangSys.collect_features())
    return _uniq_sort(sum(feature_indices, []))


@_add_method(otTables.ScriptList)
def subset_features(self, feature_indices, retain_empty):
    # https://bugzilla.mozilla.org/show_bug.cgi?id=1331737#c32
    self.ScriptRecord = [
        s
        for s in self.ScriptRecord
        if s.Script.subset_features(feature_indices, s.ScriptTag == "DFLT")
        or retain_empty
    ]
    self.ScriptCount = len(self.ScriptRecord)
    return bool(self.ScriptCount)


@_add_method(otTables.ScriptList)
def collect_features(self):
    return _uniq_sort(sum((s.Script.collect_features() for s in self.ScriptRecord), []))


# CBLC will inherit it
@_add_method(ttLib.getTableClass("EBLC"))
def subset_glyphs(self, s):
    for strike in self.strikes:
        for indexSubTable in strike.indexSubTables:
            indexSubTable.names = [n for n in indexSubTable.names if n in s.glyphs]
        strike.indexSubTables = [i for i in strike.indexSubTables if i.names]
    self.strikes = [s for s in self.strikes if s.indexSubTables]

    return True


# CBDT will inherit it
@_add_method(ttLib.getTableClass("EBDT"))
def subset_glyphs(self, s):
    strikeData = [
        {g: strike[g] for g in s.glyphs if g in strike} for strike in self.strikeData
    ]
    # Prune empty strikes
    # https://github.com/fonttools/fonttools/issues/1633
    self.strikeData = [strike for strike in strikeData if strike]
    return True


@_add_method(ttLib.getTableClass("sbix"))
def subset_glyphs(self, s):
    for strike in self.strikes.values():
        strike.glyphs = {g: strike.glyphs[g] for g in s.glyphs if g in strike.glyphs}

    return True


@_add_method(ttLib.getTableClass("GSUB"))
def closure_glyphs(self, s):
    s.table = self.table
    if self.table.ScriptList:
        feature_indices = self.table.ScriptList.collect_features()
    else:
        feature_indices = []
    if self.table.FeatureList:
        lookup_indices = self.table.FeatureList.collect_lookups(feature_indices)
    else:
        lookup_indices = []
    if getattr(self.table, "FeatureVariations", None):
        lookup_indices += self.table.FeatureVariations.collect_lookups(feature_indices)
    lookup_indices = _uniq_sort(lookup_indices)
    if self.table.LookupList:
        s._doneLookups = {}
        while True:
            orig_glyphs = frozenset(s.glyphs)
            for i in lookup_indices:
                if i >= self.table.LookupList.LookupCount:
                    continue
                if not self.table.LookupList.Lookup[i]:
                    continue
                self.table.LookupList.Lookup[i].closure_glyphs(s)
            if orig_glyphs == s.glyphs:
                break
        del s._doneLookups
    del s.table


@_add_method(ttLib.getTableClass("GSUB"), ttLib.getTableClass("GPOS"))
def subset_glyphs(self, s):
    s.glyphs = s.glyphs_gsubed
    if self.table.LookupList:
        lookup_indices = self.table.LookupList.subset_glyphs(s)
    else:
        lookup_indices = []
    self.subset_lookups(lookup_indices)
    return True


@_add_method(ttLib.getTableClass("GSUB"), ttLib.getTableClass("GPOS"))
def retain_empty_scripts(self):
    # https://github.com/fonttools/fonttools/issues/518
    # https://bugzilla.mozilla.org/show_bug.cgi?id=1080739#c15
    return self.__class__ == ttLib.getTableClass("GSUB")


@_add_method(ttLib.getTableClass("GSUB"), ttLib.getTableClass("GPOS"))
def subset_lookups(self, lookup_indices):
    """Retains specified lookups, then removes empty features, language
    systems, and scripts."""
    if self.table.LookupList:
        self.table.LookupList.subset_lookups(lookup_indices)
    if self.table.FeatureList:
        feature_indices = self.table.FeatureList.subset_lookups(lookup_indices)
    else:
        feature_indices = []
    if getattr(self.table, "FeatureVariations", None):
        feature_indices += self.table.FeatureVariations.subset_lookups(lookup_indices)
    feature_indices = _uniq_sort(feature_indices)
    if self.table.FeatureList:
        self.table.FeatureList.subset_features(feature_indices)
    if getattr(self.table, "FeatureVariations", None):
        self.table.FeatureVariations.subset_features(feature_indices)
    if self.table.ScriptList:
        self.table.ScriptList.subset_features(
            feature_indices, self.retain_empty_scripts()
        )


@_add_method(ttLib.getTableClass("GSUB"), ttLib.getTableClass("GPOS"))
def neuter_lookups(self, lookup_indices):
    """Sets lookups not in lookup_indices to None."""
    if self.table.LookupList:
        self.table.LookupList.neuter_lookups(lookup_indices)


@_add_method(ttLib.getTableClass("GSUB"), ttLib.getTableClass("GPOS"))
def prune_lookups(self, remap=True):
    """Remove (default) or neuter unreferenced lookups"""
    if self.table.ScriptList:
        feature_indices = self.table.ScriptList.collect_features()
    else:
        feature_indices = []
    if self.table.FeatureList:
        lookup_indices = self.table.FeatureList.collect_lookups(feature_indices)
    else:
        lookup_indices = []
    if getattr(self.table, "FeatureVariations", None):
        lookup_indices += self.table.FeatureVariations.collect_lookups(feature_indices)
    lookup_indices = _uniq_sort(lookup_indices)
    if self.table.LookupList:
        lookup_indices = self.table.LookupList.closure_lookups(lookup_indices)
    else:
        lookup_indices = []
    if remap:
        self.subset_lookups(lookup_indices)
    else:
        self.neuter_lookups(lookup_indices)


@_add_method(ttLib.getTableClass("GSUB"), ttLib.getTableClass("GPOS"))
def subset_feature_tags(self, feature_tags):
    if self.table.FeatureList:
        feature_indices = [
            i
            for i, f in enumerate(self.table.FeatureList.FeatureRecord)
            if f.FeatureTag in feature_tags
        ]
        self.table.FeatureList.subset_features(feature_indices)
        if getattr(self.table, "FeatureVariations", None):
            self.table.FeatureVariations.subset_features(feature_indices)
    else:
        feature_indices = []
    if self.table.ScriptList:
        self.table.ScriptList.subset_features(
            feature_indices, self.retain_empty_scripts()
        )


@_add_method(ttLib.getTableClass("GSUB"), ttLib.getTableClass("GPOS"))
def subset_script_tags(self, tags):
    langsys = {}
    script_tags = set()
    for tag in tags:
        script_tag, lang_tag = tag.split(".") if "." in tag else (tag, "*")
        script_tags.add(script_tag.ljust(4))
        langsys.setdefault(script_tag, set()).add(lang_tag.ljust(4))

    if self.table.ScriptList:
        self.table.ScriptList.ScriptRecord = [
            s for s in self.table.ScriptList.ScriptRecord if s.ScriptTag in script_tags
        ]
        self.table.ScriptList.ScriptCount = len(self.table.ScriptList.ScriptRecord)

        for record in self.table.ScriptList.ScriptRecord:
            if record.ScriptTag in langsys and "*   " not in langsys[record.ScriptTag]:
                record.Script.LangSysRecord = [
                    l
                    for l in record.Script.LangSysRecord
                    if l.LangSysTag in langsys[record.ScriptTag]
                ]
                record.Script.LangSysCount = len(record.Script.LangSysRecord)
                if "dflt" not in langsys[record.ScriptTag]:
                    record.Script.DefaultLangSys = None


@_add_method(ttLib.getTableClass("GSUB"), ttLib.getTableClass("GPOS"))
def prune_features(self):
    """Remove unreferenced features"""
    if self.table.ScriptList:
        feature_indices = self.table.ScriptList.collect_features()
    else:
        feature_indices = []
    if self.table.FeatureList:
        self.table.FeatureList.subset_features(feature_indices)
    if getattr(self.table, "FeatureVariations", None):
        self.table.FeatureVariations.subset_features(feature_indices)
    if self.table.ScriptList:
        self.table.ScriptList.subset_features(
            feature_indices, self.retain_empty_scripts()
        )


@_add_method(ttLib.getTableClass("GSUB"), ttLib.getTableClass("GPOS"))
def prune_pre_subset(self, font, options):
    # Drop undesired features
    if "*" not in options.layout_scripts:
        self.subset_script_tags(options.layout_scripts)
    if "*" not in options.layout_features:
        self.subset_feature_tags(options.layout_features)
    # Neuter unreferenced lookups
    self.prune_lookups(remap=False)
    return True


@_add_method(ttLib.getTableClass("GSUB"), ttLib.getTableClass("GPOS"))
def remove_redundant_langsys(self):
    table = self.table
    if not table.ScriptList or not table.FeatureList:
        return

    features = table.FeatureList.FeatureRecord

    for s in table.ScriptList.ScriptRecord:
        d = s.Script.DefaultLangSys
        if not d:
            continue
        for lr in s.Script.LangSysRecord[:]:
            l = lr.LangSys
            # Compare d and l
            if len(d.FeatureIndex) != len(l.FeatureIndex):
                continue
            if (d.ReqFeatureIndex == 65535) != (l.ReqFeatureIndex == 65535):
                continue

            if d.ReqFeatureIndex != 65535:
                if features[d.ReqFeatureIndex] != features[l.ReqFeatureIndex]:
                    continue

            for i in range(len(d.FeatureIndex)):
                if features[d.FeatureIndex[i]] != features[l.FeatureIndex[i]]:
                    break
            else:
                # LangSys and default are equal; delete LangSys
                s.Script.LangSysRecord.remove(lr)


@_add_method(ttLib.getTableClass("GSUB"), ttLib.getTableClass("GPOS"))
def prune_post_subset(self, font, options):
    table = self.table

    self.prune_lookups()  # XXX Is this actually needed?!

    if table.LookupList:
        table.LookupList.prune_post_subset(font, options)
        # XXX Next two lines disabled because OTS is stupid and
        # doesn't like NULL offsets here.
        # if not table.LookupList.Lookup:
        # 	table.LookupList = None

    if not table.LookupList:
        table.FeatureList = None

    if table.FeatureList:
        self.remove_redundant_langsys()
        # Remove unreferenced features
        self.prune_features()

    # XXX Next two lines disabled because OTS is stupid and
    # doesn't like NULL offsets here.
    # if table.FeatureList and not table.FeatureList.FeatureRecord:
    # 	table.FeatureList = None

    # Never drop scripts themselves as them just being available
    # holds semantic significance.
    # XXX Next two lines disabled because OTS is stupid and
    # doesn't like NULL offsets here.
    # if table.ScriptList and not table.ScriptList.ScriptRecord:
    # 	table.ScriptList = None

    if hasattr(table, "FeatureVariations"):
        # drop FeatureVariations if there are no features to substitute
        if table.FeatureVariations and not (
            table.FeatureList and table.FeatureVariations.FeatureVariationRecord
        ):
            table.FeatureVariations = None

        # downgrade table version if there are no FeatureVariations
        if not table.FeatureVariations and table.Version == 0x00010001:
            table.Version = 0x00010000

    return True


@_add_method(ttLib.getTableClass("GDEF"))
def subset_glyphs(self, s):
    glyphs = s.glyphs_gsubed
    table = self.table
    if table.LigCaretList:
        indices = table.LigCaretList.Coverage.subset(glyphs)
        table.LigCaretList.LigGlyph = _list_subset(table.LigCaretList.LigGlyph, indices)
        table.LigCaretList.LigGlyphCount = len(table.LigCaretList.LigGlyph)
    if table.MarkAttachClassDef:
        table.MarkAttachClassDef.classDefs = {
            g: v for g, v in table.MarkAttachClassDef.classDefs.items() if g in glyphs
        }
    if table.GlyphClassDef:
        table.GlyphClassDef.classDefs = {
            g: v for g, v in table.GlyphClassDef.classDefs.items() if g in glyphs
        }
    if table.AttachList:
        indices = table.AttachList.Coverage.subset(glyphs)
        GlyphCount = table.AttachList.GlyphCount
        table.AttachList.AttachPoint = [
            table.AttachList.AttachPoint[i] for i in indices if i < GlyphCount
        ]
        table.AttachList.GlyphCount = len(table.AttachList.AttachPoint)
    if hasattr(table, "MarkGlyphSetsDef") and table.MarkGlyphSetsDef:
        markGlyphSets = table.MarkGlyphSetsDef
        for coverage in markGlyphSets.Coverage:
            if coverage:
                coverage.subset(glyphs)

        s.used_mark_sets = [i for i, c in enumerate(markGlyphSets.Coverage) if c.glyphs]
        markGlyphSets.Coverage = [c for c in markGlyphSets.Coverage if c.glyphs]

    return True


def _pruneGDEF(font):
    if "GDEF" not in font:
        return
    gdef = font["GDEF"]
    table = gdef.table
    if not hasattr(table, "VarStore"):
        return

    store = table.VarStore

    usedVarIdxes = set()

    # Collect.
    table.collect_device_varidxes(usedVarIdxes)
    if "GPOS" in font:
        font["GPOS"].table.collect_device_varidxes(usedVarIdxes)

    # Subset.
    varidx_map = store.subset_varidxes(usedVarIdxes)

    # Map.
    table.remap_device_varidxes(varidx_map)
    if "GPOS" in font:
        font["GPOS"].table.remap_device_varidxes(varidx_map)


@_add_method(ttLib.getTableClass("GDEF"))
def prune_post_subset(self, font, options):
    table = self.table
    # XXX check these against OTS
    if table.LigCaretList and not table.LigCaretList.LigGlyphCount:
        table.LigCaretList = None
    if table.MarkAttachClassDef and not table.MarkAttachClassDef.classDefs:
        table.MarkAttachClassDef = None
    if table.GlyphClassDef and not table.GlyphClassDef.classDefs:
        table.GlyphClassDef = None
    if table.AttachList and not table.AttachList.GlyphCount:
        table.AttachList = None
    if hasattr(table, "VarStore"):
        _pruneGDEF(font)
        if table.VarStore.VarDataCount == 0:
            if table.Version == 0x00010003:
                table.Version = 0x00010002
    if (
        not hasattr(table, "MarkGlyphSetsDef")
        or not table.MarkGlyphSetsDef
        or not table.MarkGlyphSetsDef.Coverage
    ):
        table.MarkGlyphSetsDef = None
        if table.Version == 0x00010002:
            table.Version = 0x00010000
    return bool(
        table.LigCaretList
        or table.MarkAttachClassDef
        or table.GlyphClassDef
        or table.AttachList
        or (table.Version >= 0x00010002 and table.MarkGlyphSetsDef)
        or (table.Version >= 0x00010003 and table.VarStore)
    )


@_add_method(ttLib.getTableClass("kern"))
def prune_pre_subset(self, font, options):
    # Prune unknown kern table types
    self.kernTables = [t for t in self.kernTables if hasattr(t, "kernTable")]
    return bool(self.kernTables)


@_add_method(ttLib.getTableClass("kern"))
def subset_glyphs(self, s):
    glyphs = s.glyphs_gsubed
    for t in self.kernTables:
        t.kernTable = {
            (a, b): v
            for (a, b), v in t.kernTable.items()
            if a in glyphs and b in glyphs
        }
    self.kernTables = [t for t in self.kernTables if t.kernTable]
    return bool(self.kernTables)


@_add_method(ttLib.getTableClass("vmtx"))
def subset_glyphs(self, s):
    self.metrics = _dict_subset(self.metrics, s.glyphs)
    for g in s.glyphs_emptied:
        self.metrics[g] = (0, 0)
    return bool(self.metrics)


@_add_method(ttLib.getTableClass("hmtx"))
def subset_glyphs(self, s):
    self.metrics = _dict_subset(self.metrics, s.glyphs)
    for g in s.glyphs_emptied:
        self.metrics[g] = (0, 0)
    return True  # Required table


@_add_method(ttLib.getTableClass("hdmx"))
def subset_glyphs(self, s):
    self.hdmx = {sz: _dict_subset(l, s.glyphs) for sz, l in self.hdmx.items()}
    for sz in self.hdmx:
        for g in s.glyphs_emptied:
            self.hdmx[sz][g] = 0
    return bool(self.hdmx)


@_add_method(ttLib.getTableClass("ankr"))
def subset_glyphs(self, s):
    table = self.table.AnchorPoints
    assert table.Format == 0, "unknown 'ankr' format %s" % table.Format
    table.Anchors = {
        glyph: table.Anchors[glyph] for glyph in s.glyphs if glyph in table.Anchors
    }
    return len(table.Anchors) > 0


@_add_method(ttLib.getTableClass("bsln"))
def closure_glyphs(self, s):
    table = self.table.Baseline
    if table.Format in (2, 3):
        s.glyphs.add(table.StandardGlyph)


@_add_method(ttLib.getTableClass("bsln"))
def subset_glyphs(self, s):
    table = self.table.Baseline
    if table.Format in (1, 3):
        baselines = {
            glyph: table.BaselineValues.get(glyph, table.DefaultBaseline)
            for glyph in s.glyphs
        }
        if len(baselines) > 0:
            mostCommon, _cnt = Counter(baselines.values()).most_common(1)[0]
            table.DefaultBaseline = mostCommon
            baselines = {glyph: b for glyph, b in baselines.items() if b != mostCommon}
        if len(baselines) > 0:
            table.BaselineValues = baselines
        else:
            table.Format = {1: 0, 3: 2}[table.Format]
            del table.BaselineValues
    return True


@_add_method(ttLib.getTableClass("lcar"))
def subset_glyphs(self, s):
    table = self.table.LigatureCarets
    if table.Format in (0, 1):
        table.Carets = {
            glyph: table.Carets[glyph] for glyph in s.glyphs if glyph in table.Carets
        }
        return len(table.Carets) > 0
    else:
        assert False, "unknown 'lcar' format %s" % table.Format


@_add_method(ttLib.getTableClass("gvar"))
def prune_pre_subset(self, font, options):
    if options.notdef_glyph and not options.notdef_outline:
        self.variations[font.glyphOrder[0]] = []
    return True


@_add_method(ttLib.getTableClass("gvar"))
def subset_glyphs(self, s):
    self.variations = _dict_subset(self.variations, s.glyphs)
    self.glyphCount = len(self.variations)
    return bool(self.variations)


def _remap_index_map(s, varidx_map, table_map):
    map_ = {k: varidx_map[v] for k, v in table_map.mapping.items()}
    # Emptied glyphs are remapped to:
    # if GID <= last retained GID, 0/0: delta set for 0/0 is expected to exist & zeros compress well
    # if GID > last retained GID, major/minor of the last retained glyph: will be optimized out by table compiler
    last_idx = varidx_map[table_map.mapping[s.last_retained_glyph]]
    for g, i in s.reverseEmptiedGlyphMap.items():
        map_[g] = last_idx if i > s.last_retained_order else 0
    return map_


@_add_method(ttLib.getTableClass("HVAR"))
def subset_glyphs(self, s):
    table = self.table

    used = set()
    advIdxes_ = set()
    retainAdvMap = False

    if table.AdvWidthMap:
        table.AdvWidthMap.mapping = _dict_subset(table.AdvWidthMap.mapping, s.glyphs)
        used.update(table.AdvWidthMap.mapping.values())
    else:
        used.update(s.reverseOrigGlyphMap.values())
        advIdxes_ = used.copy()
        retainAdvMap = s.options.retain_gids

    if table.LsbMap:
        table.LsbMap.mapping = _dict_subset(table.LsbMap.mapping, s.glyphs)
        used.update(table.LsbMap.mapping.values())
    if table.RsbMap:
        table.RsbMap.mapping = _dict_subset(table.RsbMap.mapping, s.glyphs)
        used.update(table.RsbMap.mapping.values())

    varidx_map = table.VarStore.subset_varidxes(
        used, retainFirstMap=retainAdvMap, advIdxes=advIdxes_
    )

    if table.AdvWidthMap:
        table.AdvWidthMap.mapping = _remap_index_map(s, varidx_map, table.AdvWidthMap)
    if table.LsbMap:
        table.LsbMap.mapping = _remap_index_map(s, varidx_map, table.LsbMap)
    if table.RsbMap:
        table.RsbMap.mapping = _remap_index_map(s, varidx_map, table.RsbMap)

    # TODO Return emptiness...
    return True


@_add_method(ttLib.getTableClass("VVAR"))
def subset_glyphs(self, s):
    table = self.table

    used = set()
    advIdxes_ = set()
    retainAdvMap = False

    if table.AdvHeightMap:
        table.AdvHeightMap.mapping = _dict_subset(table.AdvHeightMap.mapping, s.glyphs)
        used.update(table.AdvHeightMap.mapping.values())
    else:
        used.update(s.reverseOrigGlyphMap.values())
        advIdxes_ = used.copy()
        retainAdvMap = s.options.retain_gids

    if table.TsbMap:
        table.TsbMap.mapping = _dict_subset(table.TsbMap.mapping, s.glyphs)
        used.update(table.TsbMap.mapping.values())
    if table.BsbMap:
        table.BsbMap.mapping = _dict_subset(table.BsbMap.mapping, s.glyphs)
        used.update(table.BsbMap.mapping.values())
    if table.VOrgMap:
        table.VOrgMap.mapping = _dict_subset(table.VOrgMap.mapping, s.glyphs)
        used.update(table.VOrgMap.mapping.values())

    varidx_map = table.VarStore.subset_varidxes(
        used, retainFirstMap=retainAdvMap, advIdxes=advIdxes_
    )

    if table.AdvHeightMap:
        table.AdvHeightMap.mapping = _remap_index_map(s, varidx_map, table.AdvHeightMap)
    if table.TsbMap:
        table.TsbMap.mapping = _remap_index_map(s, varidx_map, table.TsbMap)
    if table.BsbMap:
        table.BsbMap.mapping = _remap_index_map(s, varidx_map, table.BsbMap)
    if table.VOrgMap:
        table.VOrgMap.mapping = _remap_index_map(s, varidx_map, table.VOrgMap)

    # TODO Return emptiness...
    return True


@_add_method(ttLib.getTableClass("VORG"))
def subset_glyphs(self, s):
    self.VOriginRecords = {
        g: v for g, v in self.VOriginRecords.items() if g in s.glyphs
    }
    self.numVertOriginYMetrics = len(self.VOriginRecords)
    return True  # Never drop; has default metrics


@_add_method(ttLib.getTableClass("opbd"))
def subset_glyphs(self, s):
    table = self.table.OpticalBounds
    if table.Format == 0:
        table.OpticalBoundsDeltas = {
            glyph: table.OpticalBoundsDeltas[glyph]
            for glyph in s.glyphs
            if glyph in table.OpticalBoundsDeltas
        }
        return len(table.OpticalBoundsDeltas) > 0
    elif table.Format == 1:
        table.OpticalBoundsPoints = {
            glyph: table.OpticalBoundsPoints[glyph]
            for glyph in s.glyphs
            if glyph in table.OpticalBoundsPoints
        }
        return len(table.OpticalBoundsPoints) > 0
    else:
        assert False, "unknown 'opbd' format %s" % table.Format


@_add_method(ttLib.getTableClass("post"))
def prune_pre_subset(self, font, options):
    if not options.glyph_names:
        self.formatType = 3.0
    return True  # Required table


@_add_method(ttLib.getTableClass("post"))
def subset_glyphs(self, s):
    self.extraNames = []  # This seems to do it
    return True  # Required table


@_add_method(ttLib.getTableClass("prop"))
def subset_glyphs(self, s):
    prop = self.table.GlyphProperties
    if prop.Format == 0:
        return prop.DefaultProperties != 0
    elif prop.Format == 1:
        prop.Properties = {
            g: prop.Properties.get(g, prop.DefaultProperties) for g in s.glyphs
        }
        mostCommon, _cnt = Counter(prop.Properties.values()).most_common(1)[0]
        prop.DefaultProperties = mostCommon
        prop.Properties = {
            g: prop for g, prop in prop.Properties.items() if prop != mostCommon
        }
        if len(prop.Properties) == 0:
            del prop.Properties
            prop.Format = 0
            return prop.DefaultProperties != 0
        return True
    else:
        assert False, "unknown 'prop' format %s" % prop.Format


def _paint_glyph_names(paint, colr):
    result = set()

    def callback(paint):
        if paint.Format in {
            otTables.PaintFormat.PaintGlyph,
            otTables.PaintFormat.PaintColrGlyph,
        }:
            result.add(paint.Glyph)

    paint.traverse(colr, callback)
    return result


@_add_method(ttLib.getTableClass("COLR"))
def closure_glyphs(self, s):
    if self.version > 0:
        # on decompiling COLRv1, we only keep around the raw otTables
        # but for subsetting we need dicts with fully decompiled layers;
        # we store them temporarily in the C_O_L_R_ instance and delete
        # them after we have finished subsetting.
        self.ColorLayers = self._decompileColorLayersV0(self.table)
        self.ColorLayersV1 = {
            rec.BaseGlyph: rec.Paint
            for rec in self.table.BaseGlyphList.BaseGlyphPaintRecord
        }

    decompose = s.glyphs
    while decompose:
        layers = set()
        for g in decompose:
            for layer in self.ColorLayers.get(g, []):
                layers.add(layer.name)

            if self.version > 0:
                paint = self.ColorLayersV1.get(g)
                if paint is not None:
                    layers.update(_paint_glyph_names(paint, self.table))

        layers -= s.glyphs
        s.glyphs.update(layers)
        decompose = layers


@_add_method(ttLib.getTableClass("COLR"))
def subset_glyphs(self, s):
    from fontTools.colorLib.unbuilder import unbuildColrV1
    from fontTools.colorLib.builder import buildColrV1, populateCOLRv0

    # only include glyphs after COLR closure, which in turn comes after cmap and GSUB
    # closure, but importantly before glyf/CFF closures. COLR layers can refer to
    # composite glyphs, and that's ok, since glyf/CFF closures happen after COLR closure
    # and take care of those. If we also included glyphs resulting from glyf/CFF closures
    # when deciding which COLR base glyphs to retain, then we may end up with a situation
    # whereby a COLR base glyph is kept, not because directly requested (cmap)
    # or substituted (GSUB) or referenced by another COLRv1 PaintColrGlyph, but because
    # it corresponds to (has same GID as) a non-COLR glyph that happens to be used as a
    # component in glyf or CFF table. Best case scenario we retain more glyphs than
    # required; worst case we retain incomplete COLR records that try to reference
    # glyphs that are no longer in the final subset font.
    # https://github.com/fonttools/fonttools/issues/2461
    s.glyphs = s.glyphs_colred

    self.ColorLayers = {
        g: self.ColorLayers[g] for g in s.glyphs if g in self.ColorLayers
    }
    if self.version == 0:
        return bool(self.ColorLayers)

    colorGlyphsV1 = unbuildColrV1(self.table.LayerList, self.table.BaseGlyphList)
    self.table.LayerList, self.table.BaseGlyphList = buildColrV1(
        {g: colorGlyphsV1[g] for g in colorGlyphsV1 if g in s.glyphs}
    )
    del self.ColorLayersV1

    if self.table.ClipList is not None:
        clips = self.table.ClipList.clips
        self.table.ClipList.clips = {g: clips[g] for g in clips if g in s.glyphs}

    layersV0 = self.ColorLayers
    if not self.table.BaseGlyphList.BaseGlyphPaintRecord:
        # no more COLRv1 glyphs: downgrade to version 0
        self.version = 0
        del self.table
        return bool(layersV0)

    populateCOLRv0(
        self.table,
        {g: [(layer.name, layer.colorID) for layer in layersV0[g]] for g in layersV0},
    )
    del self.ColorLayers

    # TODO: also prune ununsed varIndices in COLR.VarStore
    return True


@_add_method(ttLib.getTableClass("CPAL"))
def prune_post_subset(self, font, options):
    # Keep whole "CPAL" if "SVG " is present as it may be referenced by the latter
    # via 'var(--color{palette_entry_index}, ...)' CSS color variables.
    # For now we just assume this is the case by the mere presence of "SVG " table,
    # for parsing SVG to collect all the used indices is too much work...
    # TODO(anthrotype): Do The Right Thing (TM).
    if "SVG " in font:
        return True

    colr = font.get("COLR")
    if not colr:  # drop CPAL if COLR was subsetted to empty
        return False

    colors_by_index = defaultdict(list)

    def collect_colors_by_index(paint):
        if hasattr(paint, "PaletteIndex"):  # either solid colors...
            colors_by_index[paint.PaletteIndex].append(paint)
        elif hasattr(paint, "ColorLine"):  # ... or gradient color stops
            for stop in paint.ColorLine.ColorStop:
                colors_by_index[stop.PaletteIndex].append(stop)

    if colr.version == 0:
        for layers in colr.ColorLayers.values():
            for layer in layers:
                colors_by_index[layer.colorID].append(layer)
    else:
        if colr.table.LayerRecordArray:
            for layer in colr.table.LayerRecordArray.LayerRecord:
                colors_by_index[layer.PaletteIndex].append(layer)
        for record in colr.table.BaseGlyphList.BaseGlyphPaintRecord:
            record.Paint.traverse(colr.table, collect_colors_by_index)

    # don't remap palette entry index 0xFFFF, this is always the foreground color
    # https://github.com/fonttools/fonttools/issues/2257
    retained_palette_indices = set(colors_by_index.keys()) - {0xFFFF}
    for palette in self.palettes:
        palette[:] = [c for i, c in enumerate(palette) if i in retained_palette_indices]
        assert len(palette) == len(retained_palette_indices)

    for new_index, old_index in enumerate(sorted(retained_palette_indices)):
        for record in colors_by_index[old_index]:
            if hasattr(record, "colorID"):  # v0
                record.colorID = new_index
            elif hasattr(record, "PaletteIndex"):  # v1
                record.PaletteIndex = new_index
            else:
                raise AssertionError(record)

    self.numPaletteEntries = len(self.palettes[0])

    if self.version == 1:
        kept_labels = []
        for i, label in enumerate(self.paletteEntryLabels):
            if i in retained_palette_indices:
                kept_labels.append(label)
        self.paletteEntryLabels = kept_labels
    return bool(self.numPaletteEntries)


@_add_method(otTables.MathGlyphConstruction)
def closure_glyphs(self, glyphs):
    variants = set()
    for v in self.MathGlyphVariantRecord:
        variants.add(v.VariantGlyph)
    if self.GlyphAssembly:
        for p in self.GlyphAssembly.PartRecords:
            variants.add(p.glyph)
    return variants


@_add_method(otTables.MathVariants)
def closure_glyphs(self, s):
    glyphs = frozenset(s.glyphs)
    variants = set()

    if self.VertGlyphCoverage:
        indices = self.VertGlyphCoverage.intersect(glyphs)
        for i in indices:
            variants.update(self.VertGlyphConstruction[i].closure_glyphs(glyphs))

    if self.HorizGlyphCoverage:
        indices = self.HorizGlyphCoverage.intersect(glyphs)
        for i in indices:
            variants.update(self.HorizGlyphConstruction[i].closure_glyphs(glyphs))

    s.glyphs.update(variants)


@_add_method(ttLib.getTableClass("VARC"))
def subset_glyphs(self, s):
    indices = self.table.Coverage.subset(s.glyphs)
    self.table.VarCompositeGlyphs.VarCompositeGlyph = _list_subset(
        self.table.VarCompositeGlyphs.VarCompositeGlyph, indices
    )
    return bool(self.table.VarCompositeGlyphs.VarCompositeGlyph)


@_add_method(ttLib.getTableClass("VARC"))
def closure_glyphs(self, s):
    if self.table.VarCompositeGlyphs is None:
        return

    glyphMap = {glyphName: i for i, glyphName in enumerate(self.table.Coverage.glyphs)}
    glyphRecords = self.table.VarCompositeGlyphs.VarCompositeGlyph

    glyphs = s.glyphs
    covered = set()
    new = set(glyphs)
    while new:
        oldNew = new
        new = set()
        for glyphName in oldNew:
            if glyphName in covered:
                continue
            idx = glyphMap.get(glyphName)
            if idx is None:
                continue
            glyph = glyphRecords[idx]
            for comp in glyph.components:
                name = comp.glyphName
                glyphs.add(name)
                if name not in covered:
                    new.add(name)


@_add_method(ttLib.getTableClass("VARC"))
def prune_post_subset(self, font, options):
    table = self.table

    store = table.MultiVarStore
    if store is not None:
        usedVarIdxes = set()
        table.collect_varidxes(usedVarIdxes)
        varidx_map = store.subset_varidxes(usedVarIdxes)
        table.remap_varidxes(varidx_map)

    axisIndicesList = table.AxisIndicesList.Item
    if axisIndicesList is not None:
        usedIndices = set()
        for glyph in table.VarCompositeGlyphs.VarCompositeGlyph:
            for comp in glyph.components:
                if comp.axisIndicesIndex is not None:
                    usedIndices.add(comp.axisIndicesIndex)
        usedIndices = sorted(usedIndices)
        table.AxisIndicesList.Item = _list_subset(axisIndicesList, usedIndices)
        mapping = {old: new for new, old in enumerate(usedIndices)}
        for glyph in table.VarCompositeGlyphs.VarCompositeGlyph:
            for comp in glyph.components:
                if comp.axisIndicesIndex is not None:
                    comp.axisIndicesIndex = mapping[comp.axisIndicesIndex]

    conditionList = table.ConditionList
    if conditionList is not None:
        conditionTables = conditionList.ConditionTable
        usedIndices = set()
        for glyph in table.VarCompositeGlyphs.VarCompositeGlyph:
            for comp in glyph.components:
                if comp.conditionIndex is not None:
                    usedIndices.add(comp.conditionIndex)
        usedIndices = sorted(usedIndices)
        conditionList.ConditionTable = _list_subset(conditionTables, usedIndices)
        mapping = {old: new for new, old in enumerate(usedIndices)}
        for glyph in table.VarCompositeGlyphs.VarCompositeGlyph:
            for comp in glyph.components:
                if comp.conditionIndex is not None:
                    comp.conditionIndex = mapping[comp.conditionIndex]

    return True


@_add_method(ttLib.getTableClass("MATH"))
def closure_glyphs(self, s):
    if self.table.MathVariants:
        self.table.MathVariants.closure_glyphs(s)


@_add_method(otTables.MathItalicsCorrectionInfo)
def subset_glyphs(self, s):
    indices = self.Coverage.subset(s.glyphs)
    self.ItalicsCorrection = _list_subset(self.ItalicsCorrection, indices)
    self.ItalicsCorrectionCount = len(self.ItalicsCorrection)
    return bool(self.ItalicsCorrectionCount)


@_add_method(otTables.MathTopAccentAttachment)
def subset_glyphs(self, s):
    indices = self.TopAccentCoverage.subset(s.glyphs)
    self.TopAccentAttachment = _list_subset(self.TopAccentAttachment, indices)
    self.TopAccentAttachmentCount = len(self.TopAccentAttachment)
    return bool(self.TopAccentAttachmentCount)


@_add_method(otTables.MathKernInfo)
def subset_glyphs(self, s):
    indices = self.MathKernCoverage.subset(s.glyphs)
    self.MathKernInfoRecords = _list_subset(self.MathKernInfoRecords, indices)
    self.MathKernCount = len(self.MathKernInfoRecords)
    return bool(self.MathKernCount)


@_add_method(otTables.MathGlyphInfo)
def subset_glyphs(self, s):
    if self.MathItalicsCorrectionInfo:
        self.MathItalicsCorrectionInfo.subset_glyphs(s)
    if self.MathTopAccentAttachment:
        self.MathTopAccentAttachment.subset_glyphs(s)
    if self.MathKernInfo:
        self.MathKernInfo.subset_glyphs(s)
    if self.ExtendedShapeCoverage:
        self.ExtendedShapeCoverage.subset(s.glyphs)
    return True


@_add_method(otTables.MathVariants)
def subset_glyphs(self, s):
    if self.VertGlyphCoverage:
        indices = self.VertGlyphCoverage.subset(s.glyphs)
        self.VertGlyphConstruction = _list_subset(self.VertGlyphConstruction, indices)
        self.VertGlyphCount = len(self.VertGlyphConstruction)

    if self.HorizGlyphCoverage:
        indices = self.HorizGlyphCoverage.subset(s.glyphs)
        self.HorizGlyphConstruction = _list_subset(self.HorizGlyphConstruction, indices)
        self.HorizGlyphCount = len(self.HorizGlyphConstruction)

    return True


@_add_method(ttLib.getTableClass("MATH"))
def subset_glyphs(self, s):
    s.glyphs = s.glyphs_mathed
    if self.table.MathGlyphInfo:
        self.table.MathGlyphInfo.subset_glyphs(s)
    if self.table.MathVariants:
        self.table.MathVariants.subset_glyphs(s)
    return True


@_add_method(ttLib.getTableModule("glyf").Glyph)
def remapComponentsFast(self, glyphidmap):
    if not self.data or struct.unpack(">h", self.data[:2])[0] >= 0:
        return  # Not composite
    data = self.data = bytearray(self.data)
    i = 10
    more = 1
    while more:
        flags = (data[i] << 8) | data[i + 1]
        glyphID = (data[i + 2] << 8) | data[i + 3]
        # Remap
        glyphID = glyphidmap[glyphID]
        data[i + 2] = glyphID >> 8
        data[i + 3] = glyphID & 0xFF
        i += 4
        flags = int(flags)

        if flags & 0x0001:
            i += 4  # ARG_1_AND_2_ARE_WORDS
        else:
            i += 2
        if flags & 0x0008:
            i += 2  # WE_HAVE_A_SCALE
        elif flags & 0x0040:
            i += 4  # WE_HAVE_AN_X_AND_Y_SCALE
        elif flags & 0x0080:
            i += 8  # WE_HAVE_A_TWO_BY_TWO
        more = flags & 0x0020  # MORE_COMPONENTS


@_add_method(ttLib.getTableClass("glyf"))
def closure_glyphs(self, s):
    glyphSet = self.glyphs
    decompose = s.glyphs
    while decompose:
        components = set()
        for g in decompose:
            if g not in glyphSet:
                continue
            gl = glyphSet[g]
            for c in gl.getComponentNames(self):
                components.add(c)
        components -= s.glyphs
        s.glyphs.update(components)
        decompose = components


@_add_method(ttLib.getTableClass("glyf"))
def prune_pre_subset(self, font, options):
    if options.notdef_glyph and not options.notdef_outline:
        g = self[self.glyphOrder[0]]
        # Yay, easy!
        g.__dict__.clear()
        g.data = b""
    return True


@_add_method(ttLib.getTableClass("glyf"))
def subset_glyphs(self, s):
    self.glyphs = _dict_subset(self.glyphs, s.glyphs)
    if not s.options.retain_gids:
        indices = [i for i, g in enumerate(self.glyphOrder) if g in s.glyphs]
        glyphmap = {o: n for n, o in enumerate(indices)}
        for v in self.glyphs.values():
            if hasattr(v, "data"):
                v.remapComponentsFast(glyphmap)
    Glyph = ttLib.getTableModule("glyf").Glyph
    for g in s.glyphs_emptied:
        self.glyphs[g] = Glyph()
        self.glyphs[g].data = b""
    self.glyphOrder = [
        g for g in self.glyphOrder if g in s.glyphs or g in s.glyphs_emptied
    ]
    # Don't drop empty 'glyf' tables, otherwise 'loca' doesn't get subset.
    return True


@_add_method(ttLib.getTableClass("glyf"))
def prune_post_subset(self, font, options):
    remove_hinting = not options.hinting
    for v in self.glyphs.values():
        v.trim(remove_hinting=remove_hinting)
    return True


@_add_method(ttLib.getTableClass("cmap"))
def closure_glyphs(self, s):
    tables = [t for t in self.tables if t.isUnicode()]

    # Closure unicodes, which for now is pulling in bidi mirrored variants
    if s.options.bidi_closure:
        additional_unicodes = set()
        for u in s.unicodes_requested:
            mirror_u = mirrored(u)
            if mirror_u is not None:
                additional_unicodes.add(mirror_u)
        s.unicodes_requested.update(additional_unicodes)

    # Close glyphs
    for table in tables:
        if table.format == 14:
            for varSelector, cmap in table.uvsDict.items():
                if varSelector not in s.unicodes_requested:
                    continue
                glyphs = {g for u, g in cmap if u in s.unicodes_requested}
                if None in glyphs:
                    glyphs.remove(None)
                s.glyphs.update(glyphs)
        else:
            cmap = table.cmap
            intersection = s.unicodes_requested.intersection(cmap.keys())
            s.glyphs.update(cmap[u] for u in intersection)

    # Calculate unicodes_missing
    s.unicodes_missing = s.unicodes_requested.copy()
    for table in tables:
        s.unicodes_missing.difference_update(table.cmap)


@_add_method(ttLib.getTableClass("cmap"))
def prune_pre_subset(self, font, options):
    if not options.legacy_cmap:
        # Drop non-Unicode / non-Symbol cmaps
        self.tables = [t for t in self.tables if t.isUnicode() or t.isSymbol()]
    if not options.symbol_cmap:
        self.tables = [t for t in self.tables if not t.isSymbol()]
    # TODO(behdad) Only keep one subtable?
    # For now, drop format=0 which can't be subset_glyphs easily?
    self.tables = [t for t in self.tables if t.format != 0]
    self.numSubTables = len(self.tables)
    return True  # Required table


@_add_method(ttLib.getTableClass("cmap"))
def subset_glyphs(self, s):
    s.glyphs = None  # We use s.glyphs_requested and s.unicodes_requested only

    tables_format12_bmp = []
    table_plat0_enc3 = {}  # Unicode platform, Unicode BMP only, keyed by language
    table_plat3_enc1 = {}  # Windows platform, Unicode BMP, keyed by language

    for t in self.tables:
        if t.platformID == 0 and t.platEncID == 3:
            table_plat0_enc3[t.language] = t
        if t.platformID == 3 and t.platEncID == 1:
            table_plat3_enc1[t.language] = t

        if t.format == 14:
            # TODO(behdad) We drop all the default-UVS mappings
            # for glyphs_requested.  So it's the caller's responsibility to make
            # sure those are included.
            t.uvsDict = {
                v: [
                    (u, g)
                    for u, g in l
                    if g in s.glyphs_requested or u in s.unicodes_requested
                ]
                for v, l in t.uvsDict.items()
                if v in s.unicodes_requested
            }
            t.uvsDict = {v: l for v, l in t.uvsDict.items() if l}
        elif t.isUnicode():
            t.cmap = {
                u: g
                for u, g in t.cmap.items()
                if g in s.glyphs_requested or u in s.unicodes_requested
            }
            # Collect format 12 tables that hold only basic multilingual plane
            # codepoints.
            if t.format == 12 and t.cmap and max(t.cmap.keys()) < 0x10000:
                tables_format12_bmp.append(t)
        else:
            t.cmap = {u: g for u, g in t.cmap.items() if g in s.glyphs_requested}

    # Fomat 12 tables are redundant if they contain just the same BMP codepoints
    # their little BMP-only encoding siblings contain.
    for t in tables_format12_bmp:
        if (
            t.platformID == 0  # Unicode platform
            and t.platEncID == 4  # Unicode full repertoire
            and t.language in table_plat0_enc3  # Have a BMP-only sibling?
            and table_plat0_enc3[t.language].cmap == t.cmap
        ):
            t.cmap.clear()
        elif (
            t.platformID == 3  # Windows platform
            and t.platEncID == 10  # Unicode full repertoire
            and t.language in table_plat3_enc1  # Have a BMP-only sibling?
            and table_plat3_enc1[t.language].cmap == t.cmap
        ):
            t.cmap.clear()

    self.tables = [t for t in self.tables if (t.cmap if t.format != 14 else t.uvsDict)]
    self.numSubTables = len(self.tables)
    # TODO(behdad) Convert formats when needed.
    # In particular, if we have a format=12 without non-BMP
    # characters, convert it to format=4 if there's not one.
    return True  # Required table


@_add_method(ttLib.getTableClass("DSIG"))
def prune_pre_subset(self, font, options):
    # Drop all signatures since they will be invalid
    self.usNumSigs = 0
    self.signatureRecords = []
    return True


@_add_method(ttLib.getTableClass("maxp"))
def prune_pre_subset(self, font, options):
    if not options.hinting:
        if self.tableVersion == 0x00010000:
            self.maxZones = 1
            self.maxTwilightPoints = 0
            self.maxStorage = 0
            self.maxFunctionDefs = 0
            self.maxInstructionDefs = 0
            self.maxStackElements = 0
            self.maxSizeOfInstructions = 0
    return True


NAME_IDS_TO_OBFUSCATE = {1, 2, 3, 4, 6, 16, 17, 18}


@_add_method(ttLib.getTableClass("name"))
def prune_post_subset(self, font, options):
    visitor = NameRecordVisitor()
    visitor.visit(font)
    nameIDs = set(options.name_IDs) | visitor.seen
    if "*" in options.name_IDs:
        nameIDs |= {n.nameID for n in self.names if n.nameID < 256}
    self.names = [n for n in self.names if n.nameID in nameIDs]
    if not options.name_legacy:
        # TODO(behdad) Sometimes (eg Apple Color Emoji) there's only a macroman
        # entry for Latin and no Unicode names.
        self.names = [n for n in self.names if n.isUnicode()]
    # TODO(behdad) Option to keep only one platform's
    if "*" not in options.name_languages:
        # TODO(behdad) This is Windows-platform specific!
        self.names = [n for n in self.names if n.langID in options.name_languages]
    if options.obfuscate_names:
        namerecs = []
        # Preserve names to be scrambled or dropped elsewhere so that other
        # parts of the font don't break.
        needRemapping = visitor.seen.intersection(NAME_IDS_TO_OBFUSCATE)
        if needRemapping:
            _remap_select_name_ids(font, needRemapping)
        for n in self.names:
            if n.nameID in [1, 4]:
                n.string = ".\x7f".encode("utf_16_be") if n.isUnicode() else ".\x7f"
            elif n.nameID in [2, 6]:
                n.string = "\x7f".encode("utf_16_be") if n.isUnicode() else "\x7f"
            elif n.nameID == 3:
                n.string = ""
            elif n.nameID in [16, 17, 18]:
                continue
            namerecs.append(n)
        self.names = namerecs
    return True  # Required table


def _remap_select_name_ids(font: ttLib.TTFont, needRemapping: set[int]) -> None:
    """Remap a set of IDs so that the originals can be safely scrambled or
    dropped.

    For each name record whose name id is in the `needRemapping` set, make a copy
    and allocate a new unused name id in the font-specific range (> 255).

    Finally update references to these in the `fvar` and `STAT` tables.
    """

    if "fvar" not in font and "STAT" not in font:
        return

    name = font["name"]

    # 1. Assign new IDs for names to be preserved.
    existingIds = {record.nameID for record in name.names}
    remapping = {}
    nextId = name._findUnusedNameID() - 1  # Should skip gaps in name IDs.
    for nameId in needRemapping:
        nextId += 1  # We should have complete freedom until 32767.
        assert nextId not in existingIds, "_findUnusedNameID did not skip gaps"
        if nextId > 32767:
            raise ValueError("Ran out of name IDs while trying to remap existing ones.")
        remapping[nameId] = nextId

    # 2. Copy records to use the new ID. We can't rewrite them in place, because
    #    that could make IDs 1 to 6 "disappear" from code that follows. Some
    #    tools that produce EOT fonts expect them to exist, even when they're
    #    scrambled. See https://github.com/fonttools/fonttools/issues/165.
    copiedRecords = []
    for record in name.names:
        if record.nameID not in needRemapping:
            continue
        recordCopy = makeName(
            record.string,
            remapping[record.nameID],
            record.platformID,
            record.platEncID,
            record.langID,
        )
        copiedRecords.append(recordCopy)
    name.names.extend(copiedRecords)

    # 3. Rewrite the corresponding IDs in other tables. For now, care only about
    #    STAT and fvar. If more tables need to be changed, consider adapting
    #    NameRecordVisitor to rewrite IDs wherever it finds them.
    fvar = font.get("fvar")
    if fvar is not None:
        for axis in fvar.axes:
            axis.axisNameID = remapping.get(axis.axisNameID, axis.axisNameID)
        for instance in fvar.instances:
            nameID = instance.subfamilyNameID
            instance.subfamilyNameID = remapping.get(nameID, nameID)
            nameID = instance.postscriptNameID
            instance.postscriptNameID = remapping.get(nameID, nameID)

    stat = font.get("STAT")
    if stat is None:
        return
    elidedNameID = stat.table.ElidedFallbackNameID
    stat.table.ElidedFallbackNameID = remapping.get(elidedNameID, elidedNameID)
    if stat.table.DesignAxisRecord:
        for axis in stat.table.DesignAxisRecord.Axis:
            axis.AxisNameID = remapping.get(axis.AxisNameID, axis.AxisNameID)
    if stat.table.AxisValueArray:
        for value in stat.table.AxisValueArray.AxisValue:
            value.ValueNameID = remapping.get(value.ValueNameID, value.ValueNameID)


@_add_method(ttLib.getTableClass("head"))
def prune_post_subset(self, font, options):
    # Force re-compiling head table, to update any recalculated values.
    return True


# TODO(behdad) OS/2 ulCodePageRange?
# TODO(behdad) Drop AAT tables.
# TODO(behdad) Drop unneeded GSUB/GPOS Script/LangSys entries.
# TODO(behdad) Drop empty GSUB/GPOS, and GDEF if no GSUB/GPOS left
# TODO(behdad) Drop GDEF subitems if unused by lookups
# TODO(behdad) Avoid recursing too much (in GSUB/GPOS and in CFF)
# TODO(behdad) Text direction considerations.
# TODO(behdad) Text script / language considerations.
# TODO(behdad) Optionally drop 'kern' table if GPOS available
# TODO(behdad) Implement --unicode='*' to choose all cmap'ed
# TODO(behdad) Drop old-spec Indic scripts


class Options(object):
    class OptionError(Exception):
        pass

    class UnknownOptionError(OptionError):
        pass

    # spaces in tag names (e.g. "SVG ", "cvt ") are stripped by the argument parser
    _drop_tables_default = [
        "BASE",
        "JSTF",
        "DSIG",
        "EBDT",
        "EBLC",
        "EBSC",
        "PCLT",
        "LTSH",
    ]
    _drop_tables_default += ["Feat", "Glat", "Gloc", "Silf", "Sill"]  # Graphite
    _no_subset_tables_default = [
        "avar",
        "fvar",
        "gasp",
        "head",
        "hhea",
        "maxp",
        "vhea",
        "OS/2",
        "loca",
        "name",
        "cvt",
        "fpgm",
        "prep",
        "VDMX",
        "DSIG",
        "CPAL",
        "MVAR",
        "cvar",
        "STAT",
    ]
    _hinting_tables_default = ["cvt", "cvar", "fpgm", "prep", "hdmx", "VDMX"]

    # Based on HarfBuzz shapers
    _layout_features_groups = {
        # Default shaper
        "common": ["rvrn", "ccmp", "liga", "locl", "mark", "mkmk", "rlig"],
        "fractions": ["frac", "numr", "dnom"],
        "horizontal": ["calt", "clig", "curs", "kern", "rclt"],
        "vertical": ["valt", "vert", "vkrn", "vpal", "vrt2"],
        "ltr": ["ltra", "ltrm"],
        "rtl": ["rtla", "rtlm"],
        "rand": ["rand"],
        "justify": ["jalt"],
        "private": ["Harf", "HARF", "Buzz", "BUZZ"],
        "east_asian_spacing": ["chws", "vchw", "halt", "vhal"],
        # Complex shapers
        "arabic": [
            "init",
            "medi",
            "fina",
            "isol",
            "med2",
            "fin2",
            "fin3",
            "cswh",
            "mset",
            "stch",
        ],
        "hangul": ["ljmo", "vjmo", "tjmo"],
        "tibetan": ["abvs", "blws", "abvm", "blwm"],
        "indic": [
            "nukt",
            "akhn",
            "rphf",
            "rkrf",
            "pref",
            "blwf",
            "half",
            "abvf",
            "pstf",
            "cfar",
            "vatu",
            "cjct",
            "init",
            "pres",
            "abvs",
            "blws",
            "psts",
            "haln",
            "dist",
            "abvm",
            "blwm",
        ],
    }
    _layout_features_default = _uniq_sort(
        sum(iter(_layout_features_groups.values()), [])
    )

    def __init__(self, **kwargs):
        self.drop_tables = self._drop_tables_default[:]
        self.no_subset_tables = self._no_subset_tables_default[:]
        self.passthrough_tables = False  # keep/drop tables we can't subset
        self.hinting_tables = self._hinting_tables_default[:]
        self.legacy_kern = False  # drop 'kern' table if GPOS available
        self.layout_closure = True
        self.layout_features = self._layout_features_default[:]
        self.layout_scripts = ["*"]
        self.ignore_missing_glyphs = False
        self.ignore_missing_unicodes = True
        self.hinting = True
        self.glyph_names = False
        self.legacy_cmap = False
        self.symbol_cmap = False
        self.name_IDs = [
            0,
            1,
            2,
            3,
            4,
            5,
            6,
        ]  # https://github.com/fonttools/fonttools/issues/1170#issuecomment-364631225
        self.name_legacy = False
        self.name_languages = [0x0409]  # English
        self.obfuscate_names = False  # to make webfont unusable as a system font
        self.retain_gids = False
        self.notdef_glyph = True  # gid0 for TrueType / .notdef for CFF
        self.notdef_outline = False  # No need for notdef to have an outline really
        self.recommended_glyphs = False  # gid1, gid2, gid3 for TrueType
        self.recalc_bounds = False  # Recalculate font bounding boxes
        self.recalc_timestamp = False  # Recalculate font modified timestamp
        self.prune_unicode_ranges = True  # Clear unused 'ulUnicodeRange' bits
        self.prune_codepage_ranges = True  # Clear unused 'ulCodePageRange' bits
        self.recalc_average_width = False  # update 'xAvgCharWidth'
        self.recalc_max_context = False  # update 'usMaxContext'
        self.canonical_order = None  # Order tables as recommended
        self.flavor = None  # May be 'woff' or 'woff2'
        self.with_zopfli = False  # use zopfli instead of zlib for WOFF 1.0
        self.desubroutinize = False  # Desubroutinize CFF CharStrings
        self.harfbuzz_repacker = USE_HARFBUZZ_REPACKER.default
        self.verbose = False
        self.timing = False
        self.xml = False
        self.font_number = -1
        self.pretty_svg = False
        self.lazy = True
        self.bidi_closure = True

        self.set(**kwargs)

    def set(self, **kwargs):
        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise self.UnknownOptionError("Unknown option '%s'" % k)
            setattr(self, k, v)

    def parse_opts(self, argv, ignore_unknown=[]):
        posargs = []
        passthru_options = []
        for a in argv:
            orig_a = a
            if not a.startswith("--"):
                posargs.append(a)
                continue
            a = a[2:]
            i = a.find("=")
            op = "="
            if i == -1:
                if a.startswith("no-"):
                    k = a[3:]
                    if k == "canonical-order":
                        # reorderTables=None is faster than False (the latter
                        # still reorders to "keep" the original table order)
                        v = None
                    else:
                        v = False
                else:
                    k = a
                    v = True
                if k.endswith("?"):
                    k = k[:-1]
                    v = "?"
            else:
                k = a[:i]
                if k[-1] in "-+":
                    op = k[-1] + "="  # Op is '-=' or '+=' now.
                    k = k[:-1]
                v = a[i + 1 :]
            ok = k
            k = k.replace("-", "_")
            if not hasattr(self, k):
                if ignore_unknown is True or ok in ignore_unknown:
                    passthru_options.append(orig_a)
                    continue
                else:
                    raise self.UnknownOptionError("Unknown option '%s'" % a)

            ov = getattr(self, k)
            if v == "?":
                print("Current setting for '%s' is: %s" % (ok, ov))
                continue
            if isinstance(ov, bool):
                v = bool(v)
            elif isinstance(ov, int):
                v = int(v)
            elif isinstance(ov, str):
                v = str(v)  # redundant
            elif isinstance(ov, list):
                if isinstance(v, bool):
                    raise self.OptionError(
                        "Option '%s' requires values to be specified using '='" % a
                    )
                vv = v.replace(",", " ").split()
                if vv == [""]:
                    vv = []
                vv = [int(x, 0) if len(x) and x[0] in "0123456789" else x for x in vv]
                if op == "=":
                    v = vv
                elif op == "+=":
                    v = ov
                    v.extend(vv)
                elif op == "-=":
                    v = ov
                    for x in vv:
                        if x in v:
                            v.remove(x)
                else:
                    assert False

            setattr(self, k, v)

        return posargs + passthru_options


class Subsetter(object):
    class SubsettingError(Exception):
        pass

    class MissingGlyphsSubsettingError(SubsettingError):
        pass

    class MissingUnicodesSubsettingError(SubsettingError):
        pass

    def __init__(self, options=None):
        if not options:
            options = Options()

        self.options = options
        self.unicodes_requested = set()
        self.glyph_names_requested = set()
        self.glyph_ids_requested = set()

    def populate(self, glyphs=[], gids=[], unicodes=[], text=""):
        self.unicodes_requested.update(unicodes)
        if isinstance(text, bytes):
            text = text.decode("utf_8")
        text_utf32 = text.encode("utf-32-be")
        nchars = len(text_utf32) // 4
        for u in struct.unpack(">%dL" % nchars, text_utf32):
            self.unicodes_requested.add(u)
        self.glyph_names_requested.update(glyphs)
        self.glyph_ids_requested.update(gids)

    def _prune_pre_subset(self, font):
        for tag in self._sort_tables(font):
            if (
                tag.strip() in self.options.drop_tables
                or (
                    tag.strip() in self.options.hinting_tables
                    and not self.options.hinting
                )
                or (tag == "kern" and (not self.options.legacy_kern and "GPOS" in font))
            ):
                log.info("%s dropped", tag)
                del font[tag]
                continue

            clazz = ttLib.getTableClass(tag)

            if hasattr(clazz, "prune_pre_subset"):
                with timer("load '%s'" % tag):
                    table = font[tag]
                with timer("prune '%s'" % tag):
                    retain = table.prune_pre_subset(font, self.options)
                if not retain:
                    log.info("%s pruned to empty; dropped", tag)
                    del font[tag]
                    continue
                else:
                    log.info("%s pruned", tag)

    def _closure_glyphs(self, font):
        realGlyphs = set(font.getGlyphOrder())
        self.orig_glyph_order = glyph_order = font.getGlyphOrder()

        self.glyphs_requested = set()
        self.glyphs_requested.update(self.glyph_names_requested)
        self.glyphs_requested.update(
            glyph_order[i] for i in self.glyph_ids_requested if i < len(glyph_order)
        )

        self.glyphs_missing = set()
        self.glyphs_missing.update(self.glyphs_requested.difference(realGlyphs))
        self.glyphs_missing.update(
            i for i in self.glyph_ids_requested if i >= len(glyph_order)
        )
        if self.glyphs_missing:
            log.info("Missing requested glyphs: %s", self.glyphs_missing)
            if not self.options.ignore_missing_glyphs:
                raise self.MissingGlyphsSubsettingError(self.glyphs_missing)

        self.glyphs = self.glyphs_requested.copy()

        self.unicodes_missing = set()
        if "cmap" in font:
            with timer("close glyph list over 'cmap'"):
                font["cmap"].closure_glyphs(self)
                self.glyphs.intersection_update(realGlyphs)
        self.glyphs_cmaped = frozenset(self.glyphs)
        if self.unicodes_missing:
            missing = ["U+%04X" % u for u in self.unicodes_missing]
            log.info("Missing glyphs for requested Unicodes: %s", missing)
            if not self.options.ignore_missing_unicodes:
                raise self.MissingUnicodesSubsettingError(missing)
            del missing

        if self.options.notdef_glyph:
            if "glyf" in font:
                self.glyphs.add(font.getGlyphName(0))
                log.info("Added gid0 to subset")
            else:
                self.glyphs.add(".notdef")
                log.info("Added .notdef to subset")
        if self.options.recommended_glyphs:
            if "glyf" in font:
                for i in range(min(4, len(font.getGlyphOrder()))):
                    self.glyphs.add(font.getGlyphName(i))
                log.info("Added first four glyphs to subset")

        if "MATH" in font:
            with timer("close glyph list over 'MATH'"):
                log.info(
                    "Closing glyph list over 'MATH': %d glyphs before", len(self.glyphs)
                )
                log.glyphs(self.glyphs, font=font)
                font["MATH"].closure_glyphs(self)
                self.glyphs.intersection_update(realGlyphs)
                log.info(
                    "Closed glyph list over 'MATH': %d glyphs after", len(self.glyphs)
                )
                log.glyphs(self.glyphs, font=font)
        self.glyphs_mathed = frozenset(self.glyphs)

        if self.options.layout_closure and "GSUB" in font:
            with timer("close glyph list over 'GSUB'"):
                log.info(
                    "Closing glyph list over 'GSUB': %d glyphs before", len(self.glyphs)
                )
                log.glyphs(self.glyphs, font=font)
                font["GSUB"].closure_glyphs(self)
                self.glyphs.intersection_update(realGlyphs)
                log.info(
                    "Closed glyph list over 'GSUB': %d glyphs after", len(self.glyphs)
                )
                log.glyphs(self.glyphs, font=font)
        self.glyphs_gsubed = frozenset(self.glyphs)

        for table in ("COLR", "bsln"):
            if table in font:
                with timer("close glyph list over '%s'" % table):
                    log.info(
                        "Closing glyph list over '%s': %d glyphs before",
                        table,
                        len(self.glyphs),
                    )
                    log.glyphs(self.glyphs, font=font)
                    font[table].closure_glyphs(self)
                    self.glyphs.intersection_update(realGlyphs)
                    log.info(
                        "Closed glyph list over '%s': %d glyphs after",
                        table,
                        len(self.glyphs),
                    )
                    log.glyphs(self.glyphs, font=font)
            setattr(self, f"glyphs_{table.lower()}ed", frozenset(self.glyphs))

        if "VARC" in font:
            with timer("close glyph list over 'VARC'"):
                log.info(
                    "Closing glyph list over 'VARC': %d glyphs before", len(self.glyphs)
                )
                log.glyphs(self.glyphs, font=font)
                font["VARC"].closure_glyphs(self)
                self.glyphs.intersection_update(realGlyphs)
                log.info(
                    "Closed glyph list over 'VARC': %d glyphs after", len(self.glyphs)
                )
                log.glyphs(self.glyphs, font=font)
        self.glyphs_glyfed = frozenset(self.glyphs)

        if "glyf" in font:
            with timer("close glyph list over 'glyf'"):
                log.info(
                    "Closing glyph list over 'glyf': %d glyphs before", len(self.glyphs)
                )
                log.glyphs(self.glyphs, font=font)
                font["glyf"].closure_glyphs(self)
                self.glyphs.intersection_update(realGlyphs)
                log.info(
                    "Closed glyph list over 'glyf': %d glyphs after", len(self.glyphs)
                )
                log.glyphs(self.glyphs, font=font)
        self.glyphs_glyfed = frozenset(self.glyphs)

        if "CFF " in font:
            with timer("close glyph list over 'CFF '"):
                log.info(
                    "Closing glyph list over 'CFF ': %d glyphs before", len(self.glyphs)
                )
                log.glyphs(self.glyphs, font=font)
                font["CFF "].closure_glyphs(self)
                self.glyphs.intersection_update(realGlyphs)
                log.info(
                    "Closed glyph list over 'CFF ': %d glyphs after", len(self.glyphs)
                )
                log.glyphs(self.glyphs, font=font)
        self.glyphs_cffed = frozenset(self.glyphs)

        self.glyphs_retained = frozenset(self.glyphs)

        order = font.getReverseGlyphMap()
        self.reverseOrigGlyphMap = {g: order[g] for g in self.glyphs_retained}

        self.last_retained_order = max(self.reverseOrigGlyphMap.values())
        self.last_retained_glyph = font.getGlyphOrder()[self.last_retained_order]

        self.glyphs_emptied = frozenset()
        if self.options.retain_gids:
            self.glyphs_emptied = {
                g
                for g in realGlyphs - self.glyphs_retained
                if order[g] <= self.last_retained_order
            }

        self.reverseEmptiedGlyphMap = {g: order[g] for g in self.glyphs_emptied}

        if not self.options.retain_gids:
            new_glyph_order = [g for g in glyph_order if g in self.glyphs_retained]
        else:
            new_glyph_order = [
                g for g in glyph_order if font.getGlyphID(g) <= self.last_retained_order
            ]
        # We'll call font.setGlyphOrder() at the end of _subset_glyphs when all
        # tables have been subsetted. Below, we use the new glyph order to get
        # a map from old to new glyph indices, which can be useful when
        # subsetting individual tables (e.g. SVG) that refer to GIDs.
        self.new_glyph_order = new_glyph_order
        self.glyph_index_map = {
            order[new_glyph_order[i]]: i for i in range(len(new_glyph_order))
        }

        log.info("Retaining %d glyphs", len(self.glyphs_retained))

        del self.glyphs

    def _subset_glyphs(self, font):
        self.used_mark_sets = []
        for tag in self._sort_tables(font):
            clazz = ttLib.getTableClass(tag)

            if tag.strip() in self.options.no_subset_tables:
                log.info("%s subsetting not needed", tag)
            elif hasattr(clazz, "subset_glyphs"):
                with timer("subset '%s'" % tag):
                    table = font[tag]
                    self.glyphs = self.glyphs_retained
                    retain = table.subset_glyphs(self)
                    del self.glyphs
                if not retain:
                    log.info("%s subsetted to empty; dropped", tag)
                    del font[tag]
                else:
                    log.info("%s subsetted", tag)
            elif self.options.passthrough_tables:
                log.info("%s NOT subset; don't know how to subset", tag)
            else:
                log.warning("%s NOT subset; don't know how to subset; dropped", tag)
                del font[tag]

        with timer("subset GlyphOrder"):
            font.setGlyphOrder(self.new_glyph_order)

    def _prune_post_subset(self, font):
        tableTags = font.keys()
        # Prune the name table last because when we're pruning the name table,
        # we visit each table in the font to see what name table records are
        # still in use.
        if "name" in tableTags:
            tableTags.remove("name")
            tableTags.append("name")
        for tag in tableTags:
            if tag == "GlyphOrder":
                continue
            if tag == "OS/2":
                if self.options.prune_unicode_ranges:
                    old_uniranges = font[tag].getUnicodeRanges()
                    new_uniranges = font[tag].recalcUnicodeRanges(font, pruneOnly=True)
                    if old_uniranges != new_uniranges:
                        log.info(
                            "%s Unicode ranges pruned: %s", tag, sorted(new_uniranges)
                        )
                if self.options.prune_codepage_ranges and font[tag].version >= 1:
                    # codepage range fields were added with OS/2 format 1
                    # https://learn.microsoft.com/en-us/typography/opentype/spec/os2#version-1
                    old_codepages = font[tag].getCodePageRanges()
                    new_codepages = font[tag].recalcCodePageRanges(font, pruneOnly=True)
                    if old_codepages != new_codepages:
                        log.info(
                            "%s CodePage ranges pruned: %s",
                            tag,
                            sorted(new_codepages),
                        )
                if self.options.recalc_average_width:
                    old_avg_width = font[tag].xAvgCharWidth
                    new_avg_width = font[tag].recalcAvgCharWidth(font)
                    if old_avg_width != new_avg_width:
                        log.info("%s xAvgCharWidth updated: %d", tag, new_avg_width)
                if self.options.recalc_max_context:
                    max_context = maxCtxFont(font)
                    if max_context != font[tag].usMaxContext:
                        font[tag].usMaxContext = max_context
                        log.info("%s usMaxContext updated: %d", tag, max_context)
            clazz = ttLib.getTableClass(tag)
            if hasattr(clazz, "prune_post_subset"):
                with timer("prune '%s'" % tag):
                    table = font[tag]
                    retain = table.prune_post_subset(font, self.options)
                if not retain:
                    log.info("%s pruned to empty; dropped", tag)
                    del font[tag]
                else:
                    log.info("%s pruned", tag)

    def _sort_tables(self, font):
        tagOrder = ["GDEF", "GPOS", "GSUB", "fvar", "avar", "gvar", "name", "glyf"]
        tagOrder = {t: i + 1 for i, t in enumerate(tagOrder)}
        tags = sorted(font.keys(), key=lambda tag: tagOrder.get(tag, 0))
        return [t for t in tags if t != "GlyphOrder"]

    def subset(self, font):
        self._prune_pre_subset(font)
        self._closure_glyphs(font)
        self._subset_glyphs(font)
        self._prune_post_subset(font)


@timer("load font")
def load_font(fontFile, options, checkChecksums=0, dontLoadGlyphNames=False, lazy=True):
    font = ttLib.TTFont(
        fontFile,
        checkChecksums=checkChecksums,
        recalcBBoxes=options.recalc_bounds,
        recalcTimestamp=options.recalc_timestamp,
        lazy=lazy,
        fontNumber=options.font_number,
    )

    # Hack:
    #
    # If we don't need glyph names, change 'post' class to not try to
    # load them.	It avoid lots of headache with broken fonts as well
    # as loading time.
    #
    # Ideally ttLib should provide a way to ask it to skip loading
    # glyph names.	But it currently doesn't provide such a thing.
    #
    if dontLoadGlyphNames:
        post = ttLib.getTableClass("post")
        saved = post.decode_format_2_0
        post.decode_format_2_0 = post.decode_format_3_0
        f = font["post"]
        if f.formatType == 2.0:
            f.formatType = 3.0
        post.decode_format_2_0 = saved

    return font


@timer("compile and save font")
def save_font(font, outfile, options):
    if options.with_zopfli and options.flavor == "woff":
        from fontTools.ttLib import sfnt

        sfnt.USE_ZOPFLI = True
    font.flavor = options.flavor
    font.cfg[USE_HARFBUZZ_REPACKER] = options.harfbuzz_repacker
    font.save(outfile, reorderTables=options.canonical_order)


def parse_unicodes(s):
    import re

    s = re.sub(r"0[xX]", " ", s)
    s = re.sub(r"[<+>,;&#\\xXuU\n	]", " ", s)
    l = []
    for item in s.split():
        fields = item.split("-")
        if len(fields) == 1:
            l.append(int(item, 16))
        else:
            start, end = fields
            l.extend(range(int(start, 16), int(end, 16) + 1))
    return l


def parse_gids(s):
    l = []
    for item in s.replace(",", " ").split():
        fields = item.split("-")
        if len(fields) == 1:
            l.append(int(fields[0]))
        else:
            l.extend(range(int(fields[0]), int(fields[1]) + 1))
    return l


def parse_glyphs(s):
    return s.replace(",", " ").split()


def usage():
    print("usage:", __usage__, file=sys.stderr)
    print("Try pyftsubset --help for more information.\n", file=sys.stderr)


@timer("make one with everything (TOTAL TIME)")
def main(args=None):
    """OpenType font subsetter and optimizer"""
    from os.path import splitext
    from fontTools import configLogger

    if args is None:
        args = sys.argv[1:]

    if "--help" in args:
        print(__doc__)
        return 0

    options = Options()
    try:
        args = options.parse_opts(
            args,
            ignore_unknown=[
                "gids",
                "gids-file",
                "glyphs",
                "glyphs-file",
                "text",
                "text-file",
                "unicodes",
                "unicodes-file",
                "output-file",
            ],
        )
    except options.OptionError as e:
        usage()
        print("ERROR:", e, file=sys.stderr)
        return 2

    if len(args) < 2:
        usage()
        return 1

    configLogger(level=logging.INFO if options.verbose else logging.WARNING)
    if options.timing:
        timer.logger.setLevel(logging.DEBUG)
    else:
        timer.logger.disabled = True

    fontfile = args[0]
    args = args[1:]

    subsetter = Subsetter(options=options)
    outfile = None
    glyphs = []
    gids = []
    unicodes = []
    wildcard_glyphs = False
    wildcard_unicodes = False
    text = ""
    for g in args:
        if g == "*":
            wildcard_glyphs = True
            continue
        if g.startswith("--output-file="):
            outfile = g[14:]
            continue
        if g.startswith("--text="):
            text += g[7:]
            continue
        if g.startswith("--text-file="):
            with open(g[12:], encoding="utf-8-sig") as f:
                text += f.read().replace("\n", "")
            continue
        if g.startswith("--unicodes="):
            if g[11:] == "*":
                wildcard_unicodes = True
            else:
                unicodes.extend(parse_unicodes(g[11:]))
            continue
        if g.startswith("--unicodes-file="):
            with open(g[16:]) as f:
                for line in f.readlines():
                    unicodes.extend(parse_unicodes(line.split("#")[0]))
            continue
        if g.startswith("--gids="):
            gids.extend(parse_gids(g[7:]))
            continue
        if g.startswith("--gids-file="):
            with open(g[12:]) as f:
                for line in f.readlines():
                    gids.extend(parse_gids(line.split("#")[0]))
            continue
        if g.startswith("--glyphs="):
            if g[9:] == "*":
                wildcard_glyphs = True
            else:
                glyphs.extend(parse_glyphs(g[9:]))
            continue
        if g.startswith("--glyphs-file="):
            with open(g[14:]) as f:
                for line in f.readlines():
                    glyphs.extend(parse_glyphs(line.split("#")[0]))
            continue
        glyphs.append(g)

    dontLoadGlyphNames = not options.glyph_names and not glyphs
    lazy = options.lazy
    font = load_font(
        fontfile, options, dontLoadGlyphNames=dontLoadGlyphNames, lazy=lazy
    )

    if outfile is None:
        ext = "." + options.flavor.lower() if options.flavor is not None else None
        outfile = makeOutputFileName(
            fontfile, extension=ext, overWrite=True, suffix=".subset"
        )

    with timer("compile glyph list"):
        if wildcard_glyphs:
            glyphs.extend(font.getGlyphOrder())
        if wildcard_unicodes:
            for t in font["cmap"].tables:
                if t.isUnicode():
                    unicodes.extend(t.cmap.keys())
                    if t.format == 14:
                        unicodes.extend(t.uvsDict.keys())
        assert "" not in glyphs

    log.info("Text: '%s'" % text)
    log.info("Unicodes: %s", unicodes)
    log.info("Glyphs: %s", glyphs)
    log.info("Gids: %s", gids)

    subsetter.populate(glyphs=glyphs, gids=gids, unicodes=unicodes, text=text)
    subsetter.subset(font)

    save_font(font, outfile, options)

    if options.verbose:
        import os

        log.info("Input font:% 7d bytes: %s" % (os.path.getsize(fontfile), fontfile))
        log.info("Subset font:% 7d bytes: %s" % (os.path.getsize(outfile), outfile))

    if options.xml:
        font.saveXML(sys.stdout)

    font.close()


__all__ = [
    "Options",
    "Subsetter",
    "load_font",
    "save_font",
    "parse_gids",
    "parse_glyphs",
    "parse_unicodes",
    "main",
]