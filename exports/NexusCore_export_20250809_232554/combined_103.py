
# === NexusCore/tools\exports\NexusCore_export_20250803_131253\combined_42.py ===

# === NexusCore/tools\exports\export_20250803_114325\combined_55.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\types\utils.py ===
import json
import time
import uuid
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from aiohttp import FormData
from openai._models import BaseModel as OpenAIObject
from openai.types.audio.transcription_create_params import FileTypes  # type: ignore
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.completion_usage import (
    CompletionTokensDetails,
    CompletionUsage,
    PromptTokensDetails,
)
from openai.types.moderation import (
    Categories,
    CategoryAppliedInputTypes,
    CategoryScores,
)
from openai.types.moderation_create_response import Moderation, ModerationCreateResponse
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator
from typing_extensions import Callable, Dict, Required, TypedDict, override

import litellm
from litellm.types.llms.base import BaseLiteLLMOpenAIResponseObject

from ..litellm_core_utils.core_helpers import map_finish_reason
from .guardrails import GuardrailEventHooks
from .llms.openai import (
    Batch,
    ChatCompletionAnnotation,
    ChatCompletionRedactedThinkingBlock,
    ChatCompletionThinkingBlock,
    ChatCompletionToolCallChunk,
    ChatCompletionUsageBlock,
    FileSearchTool,
    FineTuningJob,
    OpenAIChatCompletionChunk,
    OpenAIFileObject,
    OpenAIRealtimeStreamList,
    WebSearchOptions,
)
from .rerank import RerankResponse

if TYPE_CHECKING:
    from .vector_stores import VectorStoreSearchResponse
else:
    VectorStoreSearchResponse = Any


def _generate_id():  # private helper function
    return "chatcmpl-" + str(uuid.uuid4())


class LiteLLMPydanticObjectBase(BaseModel):
    """
    Implements default functions, all pydantic objects should have.
    """

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump(**kwargs)  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict(**kwargs)

    def fields_set(self):
        try:
            return self.model_fields_set  # noqa
        except Exception:
            # if using pydantic v1
            return self.__fields_set__

    model_config = ConfigDict(protected_namespaces=())


class LiteLLMCommonStrings(Enum):
    redacted_by_litellm = "redacted by litellm. 'litellm.turn_off_message_logging=True'"
    llm_provider_not_provided = "Unmapped LLM provider for this endpoint. You passed model={model}, custom_llm_provider={custom_llm_provider}. Check supported provider and route: https://docs.litellm.ai/docs/providers"


SupportedCacheControls = ["ttl", "s-maxage", "no-cache", "no-store"]


class CostPerToken(TypedDict):
    input_cost_per_token: float
    output_cost_per_token: float


class ProviderField(TypedDict):
    field_name: str
    field_type: Literal["string"]
    field_description: str
    field_value: str


class ProviderSpecificModelInfo(TypedDict, total=False):
    supports_system_messages: Optional[bool]
    supports_response_schema: Optional[bool]
    supports_vision: Optional[bool]
    supports_function_calling: Optional[bool]
    supports_tool_choice: Optional[bool]
    supports_assistant_prefill: Optional[bool]
    supports_prompt_caching: Optional[bool]
    supports_computer_use: Optional[bool]
    supports_audio_input: Optional[bool]
    supports_embedding_image_input: Optional[bool]
    supports_audio_output: Optional[bool]
    supports_pdf_input: Optional[bool]
    supports_native_streaming: Optional[bool]
    supports_parallel_function_calling: Optional[bool]
    supports_web_search: Optional[bool]
    supports_reasoning: Optional[bool]
    supports_url_context: Optional[bool]


class SearchContextCostPerQuery(TypedDict, total=False):
    search_context_size_low: float
    search_context_size_medium: float
    search_context_size_high: float


class ModelInfoBase(ProviderSpecificModelInfo, total=False):
    key: Required[str]  # the key in litellm.model_cost which is returned

    max_tokens: Required[Optional[int]]
    max_input_tokens: Required[Optional[int]]
    max_output_tokens: Required[Optional[int]]
    input_cost_per_token: Required[float]
    cache_creation_input_token_cost: Optional[float]
    cache_read_input_token_cost: Optional[float]
    input_cost_per_character: Optional[float]  # only for vertex ai models
    input_cost_per_audio_token: Optional[float]
    input_cost_per_token_above_128k_tokens: Optional[float]  # only for vertex ai models
    input_cost_per_token_above_200k_tokens: Optional[
        float
    ]  # only for vertex ai gemini-2.5-pro models
    input_cost_per_character_above_128k_tokens: Optional[
        float
    ]  # only for vertex ai models
    input_cost_per_query: Optional[float]  # only for rerank models
    input_cost_per_image: Optional[float]  # only for vertex ai models
    input_cost_per_audio_per_second: Optional[float]  # only for vertex ai models
    input_cost_per_video_per_second: Optional[float]  # only for vertex ai models
    input_cost_per_second: Optional[float]  # for OpenAI Speech models
    input_cost_per_token_batches: Optional[float]
    output_cost_per_token_batches: Optional[float]
    output_cost_per_token: Required[float]
    output_cost_per_character: Optional[float]  # only for vertex ai models
    output_cost_per_audio_token: Optional[float]
    output_cost_per_token_above_128k_tokens: Optional[
        float
    ]  # only for vertex ai models
    output_cost_per_token_above_200k_tokens: Optional[
        float
    ]  # only for vertex ai gemini-2.5-pro models
    output_cost_per_character_above_128k_tokens: Optional[
        float
    ]  # only for vertex ai models
    output_cost_per_image: Optional[float]
    output_vector_size: Optional[int]
    output_cost_per_reasoning_token: Optional[float]
    output_cost_per_video_per_second: Optional[float]  # only for vertex ai models
    output_cost_per_audio_per_second: Optional[float]  # only for vertex ai models
    output_cost_per_second: Optional[float]  # for OpenAI Speech models
    search_context_cost_per_query: Optional[
        SearchContextCostPerQuery
    ]  # Cost for using web search tool

    litellm_provider: Required[str]
    mode: Required[
        Literal[
            "completion", "embedding", "image_generation", "chat", "audio_transcription"
        ]
    ]
    tpm: Optional[int]
    rpm: Optional[int]


class ModelInfo(ModelInfoBase, total=False):
    """
    Model info for a given model, this is information found in litellm.model_prices_and_context_window.json
    """

    supported_openai_params: Required[Optional[List[str]]]


class GenericStreamingChunk(TypedDict, total=False):
    text: Required[str]
    tool_use: Optional[ChatCompletionToolCallChunk]
    is_finished: Required[bool]
    finish_reason: Required[str]
    usage: Required[Optional[ChatCompletionUsageBlock]]
    index: int

    # use this dict if you want to return any provider specific fields in the response
    provider_specific_fields: Optional[Dict[str, Any]]


from enum import Enum


class CallTypes(Enum):
    embedding = "embedding"
    aembedding = "aembedding"
    completion = "completion"
    acompletion = "acompletion"
    atext_completion = "atext_completion"
    text_completion = "text_completion"
    image_generation = "image_generation"
    aimage_generation = "aimage_generation"
    image_edit = "image_edit"
    aimage_edit = "aimage_edit"
    moderation = "moderation"
    amoderation = "amoderation"
    atranscription = "atranscription"
    transcription = "transcription"
    aspeech = "aspeech"
    speech = "speech"
    rerank = "rerank"
    arerank = "arerank"
    arealtime = "_arealtime"
    create_batch = "create_batch"
    acreate_batch = "acreate_batch"
    aretrieve_batch = "aretrieve_batch"
    retrieve_batch = "retrieve_batch"
    pass_through = "pass_through_endpoint"
    anthropic_messages = "anthropic_messages"
    get_assistants = "get_assistants"
    aget_assistants = "aget_assistants"
    create_assistants = "create_assistants"
    acreate_assistants = "acreate_assistants"
    delete_assistant = "delete_assistant"
    adelete_assistant = "adelete_assistant"
    acreate_thread = "acreate_thread"
    create_thread = "create_thread"
    aget_thread = "aget_thread"
    get_thread = "get_thread"
    a_add_message = "a_add_message"
    add_message = "add_message"
    aget_messages = "aget_messages"
    get_messages = "get_messages"
    arun_thread = "arun_thread"
    run_thread = "run_thread"
    arun_thread_stream = "arun_thread_stream"
    run_thread_stream = "run_thread_stream"
    afile_retrieve = "afile_retrieve"
    file_retrieve = "file_retrieve"
    afile_delete = "afile_delete"
    file_delete = "file_delete"
    afile_list = "afile_list"
    file_list = "file_list"
    acreate_file = "acreate_file"
    create_file = "create_file"
    afile_content = "afile_content"
    file_content = "file_content"
    create_fine_tuning_job = "create_fine_tuning_job"
    acreate_fine_tuning_job = "acreate_fine_tuning_job"
    acancel_fine_tuning_job = "acancel_fine_tuning_job"
    cancel_fine_tuning_job = "cancel_fine_tuning_job"
    alist_fine_tuning_jobs = "alist_fine_tuning_jobs"
    list_fine_tuning_jobs = "list_fine_tuning_jobs"
    aretrieve_fine_tuning_job = "aretrieve_fine_tuning_job"
    retrieve_fine_tuning_job = "retrieve_fine_tuning_job"
    responses = "responses"
    aresponses = "aresponses"
    alist_input_items = "alist_input_items"


CallTypesLiteral = Literal[
    "embedding",
    "aembedding",
    "completion",
    "acompletion",
    "atext_completion",
    "text_completion",
    "image_generation",
    "aimage_generation",
    "image_edit",
    "aimage_edit",
    "moderation",
    "amoderation",
    "atranscription",
    "transcription",
    "aspeech",
    "speech",
    "rerank",
    "arerank",
    "_arealtime",
    "create_batch",
    "acreate_batch",
    "pass_through_endpoint",
    "anthropic_messages",
    "aretrieve_batch",
    "retrieve_batch",
]


class PassthroughCallTypes(Enum):
    passthrough_image_generation = "passthrough-image-generation"


class TopLogprob(OpenAIObject):
    token: str
    """The token."""

    bytes: Optional[List[int]] = None
    """A list of integers representing the UTF-8 bytes representation of the token.

    Useful in instances where characters are represented by multiple tokens and
    their byte representations must be combined to generate the correct text
    representation. Can be `null` if there is no bytes representation for the token.
    """

    logprob: float
    """The log probability of this token, if it is within the top 20 most likely
    tokens.

    Otherwise, the value `-9999.0` is used to signify that the token is very
    unlikely.
    """


class ChatCompletionTokenLogprob(OpenAIObject):
    token: str
    """The token."""

    bytes: Optional[List[int]] = None
    """A list of integers representing the UTF-8 bytes representation of the token.

    Useful in instances where characters are represented by multiple tokens and
    their byte representations must be combined to generate the correct text
    representation. Can be `null` if there is no bytes representation for the token.
    """

    logprob: float
    """The log probability of this token, if it is within the top 20 most likely
    tokens.

    Otherwise, the value `-9999.0` is used to signify that the token is very
    unlikely.
    """

    top_logprobs: List[TopLogprob]
    """List of the most likely tokens and their log probability, at this token
    position.

    In rare cases, there may be fewer than the number of requested `top_logprobs`
    returned.
    """

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)


class ChoiceLogprobs(OpenAIObject):
    content: Optional[List[ChatCompletionTokenLogprob]] = None
    """A list of message content tokens with log probability information."""

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)


class FunctionCall(OpenAIObject):
    arguments: str
    name: Optional[str] = None


class Function(OpenAIObject):
    arguments: str
    name: Optional[
        str
    ]  # can be None - openai e.g.: ChoiceDeltaToolCallFunction(arguments='{"', name=None), type=None)

    def __init__(
        self,
        arguments: Optional[Union[Dict, str]] = None,
        name: Optional[str] = None,
        **params,
    ):
        if arguments is None:
            if params.get("parameters", None) is not None and isinstance(
                params["parameters"], dict
            ):
                arguments = json.dumps(params["parameters"])
                params.pop("parameters")
            else:
                arguments = ""
        elif isinstance(arguments, Dict):
            arguments = json.dumps(arguments)
        else:
            arguments = arguments

        name = name

        # Build a dictionary with the structure your BaseModel expects
        data = {"arguments": arguments, "name": name}

        super(Function, self).__init__(**data)

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


class ChatCompletionDeltaToolCall(OpenAIObject):
    id: Optional[str] = None
    function: Function
    type: Optional[str] = None
    index: int

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


class HiddenParams(OpenAIObject):
    original_response: Optional[Union[str, Any]] = None
    model_id: Optional[str] = None  # used in Router for individual deployments
    api_base: Optional[str] = None  # returns api base used for making completion call
    _response_ms: Optional[float] = None

    model_config = ConfigDict(extra="allow", protected_namespaces=())

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict()

    def model_dump(self, **kwargs):
        # Override model_dump to include private attributes
        data = super().model_dump(**kwargs)
        data["_response_ms"] = self._response_ms
        return data


class ChatCompletionMessageToolCall(OpenAIObject):
    def __init__(
        self,
        function: Union[Dict, Function],
        id: Optional[str] = None,
        type: Optional[str] = None,
        **params,
    ):
        super(ChatCompletionMessageToolCall, self).__init__(**params)
        if isinstance(function, Dict):
            self.function = Function(**function)
        else:
            self.function = function

        if id is not None:
            self.id = id
        else:
            self.id = f"{uuid.uuid4()}"

        if type is not None:
            self.type = type
        else:
            self.type = "function"

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


from openai.types.chat.chat_completion_audio import ChatCompletionAudio


class ChatCompletionAudioResponse(ChatCompletionAudio):
    def __init__(
        self,
        data: str,
        expires_at: int,
        transcript: str,
        id: Optional[str] = None,
        **params,
    ):
        if id is not None:
            id = id
        else:
            id = f"{uuid.uuid4()}"
        super(ChatCompletionAudioResponse, self).__init__(
            data=data, expires_at=expires_at, transcript=transcript, id=id, **params
        )

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


"""
Reference:
ChatCompletionMessage(content='This is a test', role='assistant', function_call=None, tool_calls=None))
"""


def add_provider_specific_fields(
    object: BaseModel, provider_specific_fields: Optional[Dict[str, Any]]
):
    if not provider_specific_fields:  # set if provider_specific_fields is not empty
        return
    setattr(object, "provider_specific_fields", provider_specific_fields)


class Message(OpenAIObject):
    content: Optional[str]
    role: Literal["assistant", "user", "system", "tool", "function"]
    tool_calls: Optional[List[ChatCompletionMessageToolCall]]
    function_call: Optional[FunctionCall]
    audio: Optional[ChatCompletionAudioResponse] = None
    reasoning_content: Optional[str] = None
    thinking_blocks: Optional[
        List[Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]]
    ] = None
    provider_specific_fields: Optional[Dict[str, Any]] = Field(
        default=None, exclude=True
    )
    annotations: Optional[List[ChatCompletionAnnotation]] = None

    def __init__(
        self,
        content: Optional[str] = None,
        role: Literal["assistant"] = "assistant",
        function_call=None,
        tool_calls: Optional[list] = None,
        audio: Optional[ChatCompletionAudioResponse] = None,
        provider_specific_fields: Optional[Dict[str, Any]] = None,
        reasoning_content: Optional[str] = None,
        thinking_blocks: Optional[
            List[
                Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]
            ]
        ] = None,
        annotations: Optional[List[ChatCompletionAnnotation]] = None,
        **params,
    ):
        init_values: Dict[str, Any] = {
            "content": content,
            "role": role or "assistant",  # handle null input
            "function_call": (
                FunctionCall(**function_call) if function_call is not None else None
            ),
            "tool_calls": (
                [
                    (
                        ChatCompletionMessageToolCall(**tool_call)
                        if isinstance(tool_call, dict)
                        else tool_call
                    )
                    for tool_call in tool_calls
                ]
                if tool_calls is not None and len(tool_calls) > 0
                else None
            ),
        }

        if audio is not None:
            init_values["audio"] = audio

        if thinking_blocks is not None:
            init_values["thinking_blocks"] = thinking_blocks

        if annotations is not None:
            init_values["annotations"] = annotations

        if reasoning_content is not None:
            init_values["reasoning_content"] = reasoning_content

        super(Message, self).__init__(
            **init_values,  # type: ignore
            **params,
        )

        if audio is None:
            # delete audio from self
            # OpenAI compatible APIs like mistral API will raise an error if audio is passed in
            if hasattr(self, "audio"):
                del self.audio

        if annotations is None:
            # ensure default response matches OpenAI spec
            # Some OpenAI compatible APIs raise an error if annotations are passed in
            if hasattr(self, "annotations"):
                del self.annotations

        if reasoning_content is None:
            # ensure default response matches OpenAI spec
            if hasattr(self, "reasoning_content"):
                del self.reasoning_content

        if thinking_blocks is None:
            # ensure default response matches OpenAI spec
            if hasattr(self, "thinking_blocks"):
                del self.thinking_blocks

        add_provider_specific_fields(self, provider_specific_fields)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict()


class Delta(OpenAIObject):
    reasoning_content: Optional[str] = None
    thinking_blocks: Optional[
        List[Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]]
    ] = None
    provider_specific_fields: Optional[Dict[str, Any]] = Field(default=None)

    def __init__(
        self,
        content=None,
        role=None,
        function_call=None,
        tool_calls=None,
        audio: Optional[ChatCompletionAudioResponse] = None,
        reasoning_content: Optional[str] = None,
        thinking_blocks: Optional[
            List[
                Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]
            ]
        ] = None,
        annotations: Optional[List[ChatCompletionAnnotation]] = None,
        **params,
    ):
        super(Delta, self).__init__(**params)
        add_provider_specific_fields(self, params.get("provider_specific_fields", {}))
        self.content = content
        self.role = role
        # Set default values and correct types
        self.function_call: Optional[Union[FunctionCall, Any]] = None
        self.tool_calls: Optional[List[Union[ChatCompletionDeltaToolCall, Any]]] = None
        self.audio: Optional[ChatCompletionAudioResponse] = None
        self.annotations: Optional[List[ChatCompletionAnnotation]] = None

        if reasoning_content is not None:
            self.reasoning_content = reasoning_content
        else:
            # ensure default response matches OpenAI spec
            del self.reasoning_content

        if thinking_blocks is not None:
            self.thinking_blocks = thinking_blocks
        else:
            # ensure default response matches OpenAI spec
            del self.thinking_blocks

        # Add annotations to the delta, ensure they are only on Delta if they exist (Match OpenAI spec)
        if annotations is not None:
            self.annotations = annotations
        else:
            del self.annotations

        if function_call is not None and isinstance(function_call, dict):
            self.function_call = FunctionCall(**function_call)
        else:
            self.function_call = function_call
        if tool_calls is not None and isinstance(tool_calls, list):
            self.tool_calls = []
            for tool_call in tool_calls:
                if isinstance(tool_call, dict):
                    if tool_call.get("index", None) is None:
                        tool_call["index"] = 0
                    self.tool_calls.append(ChatCompletionDeltaToolCall(**tool_call))
                elif isinstance(tool_call, ChatCompletionDeltaToolCall):
                    self.tool_calls.append(tool_call)
        else:
            self.tool_calls = tool_calls

        self.audio = audio

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


class Choices(OpenAIObject):
    finish_reason: str
    index: int
    message: Message
    logprobs: Optional[Union[ChoiceLogprobs, Any]] = None

    provider_specific_fields: Optional[Dict[str, Any]] = Field(default=None)

    def __init__(
        self,
        finish_reason=None,
        index=0,
        message: Optional[Union[Message, dict]] = None,
        logprobs: Optional[Union[ChoiceLogprobs, dict, Any]] = None,
        enhancements=None,
        provider_specific_fields: Optional[Dict[str, Any]] = None,
        **params,
    ):
        if finish_reason is not None:
            params["finish_reason"] = map_finish_reason(finish_reason)
        else:
            params["finish_reason"] = "stop"
        if index is not None:
            params["index"] = index
        else:
            params["index"] = 0
        if message is None:
            params["message"] = Message()
        else:
            if isinstance(message, Message):
                params["message"] = message
            elif isinstance(message, dict):
                params["message"] = Message(**message)
        if logprobs is not None:
            if isinstance(logprobs, dict):
                params["logprobs"] = ChoiceLogprobs(**logprobs)
            else:
                params["logprobs"] = logprobs
        else:
            params["logprobs"] = None
        super(Choices, self).__init__(**params)

        if enhancements is not None:
            self.enhancements = enhancements

        self.provider_specific_fields = provider_specific_fields

        if self.logprobs is None:
            del self.logprobs
        if self.provider_specific_fields is None:
            del self.provider_specific_fields

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


class CompletionTokensDetailsWrapper(
    CompletionTokensDetails
):  # wrapper for older openai versions
    text_tokens: Optional[int] = None
    """Text tokens generated by the model."""


class PromptTokensDetailsWrapper(
    PromptTokensDetails
):  # wrapper for older openai versions
    text_tokens: Optional[int] = None
    """Text tokens sent to the model."""

    image_tokens: Optional[int] = None
    """Image tokens sent to the model."""

    web_search_requests: Optional[int] = None
    """Number of web search requests made by the tool call. Used for Anthropic to calculate web search cost."""

    character_count: Optional[int] = None
    """Character count sent to the model. Used for Vertex AI multimodal embeddings."""

    image_count: Optional[int] = None
    """Number of images sent to the model. Used for Vertex AI multimodal embeddings."""

    video_length_seconds: Optional[float] = None
    """Length of videos sent to the model. Used for Vertex AI multimodal embeddings."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.character_count is None:
            del self.character_count
        if self.image_count is None:
            del self.image_count
        if self.video_length_seconds is None:
            del self.video_length_seconds
        if self.web_search_requests is None:
            del self.web_search_requests


class ServerToolUse(BaseModel):
    web_search_requests: Optional[int]


class Usage(CompletionUsage):
    _cache_creation_input_tokens: int = PrivateAttr(
        0
    )  # hidden param for prompt caching. Might change, once openai introduces their equivalent.
    _cache_read_input_tokens: int = PrivateAttr(
        0
    )  # hidden param for prompt caching. Might change, once openai introduces their equivalent.

    server_tool_use: Optional[ServerToolUse] = None

    def __init__(
        self,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        reasoning_tokens: Optional[int] = None,
        prompt_tokens_details: Optional[Union[PromptTokensDetailsWrapper, dict]] = None,
        completion_tokens_details: Optional[
            Union[CompletionTokensDetailsWrapper, dict]
        ] = None,
        server_tool_use: Optional[ServerToolUse] = None,
        **params,
    ):
        # handle reasoning_tokens
        _completion_tokens_details: Optional[CompletionTokensDetailsWrapper] = None
        if reasoning_tokens:
            text_tokens = (
                completion_tokens - reasoning_tokens if completion_tokens else None
            )
            completion_tokens_details = CompletionTokensDetailsWrapper(
                reasoning_tokens=reasoning_tokens, text_tokens=text_tokens
            )

        # Ensure completion_tokens_details is properly handled
        if completion_tokens_details:
            if isinstance(completion_tokens_details, dict):
                _completion_tokens_details = CompletionTokensDetailsWrapper(
                    **completion_tokens_details
                )
            elif isinstance(completion_tokens_details, CompletionTokensDetails):
                _completion_tokens_details = completion_tokens_details

        ## DEEPSEEK MAPPING ##
        if "prompt_cache_hit_tokens" in params and isinstance(
            params["prompt_cache_hit_tokens"], int
        ):
            if prompt_tokens_details is None:
                prompt_tokens_details = PromptTokensDetailsWrapper(
                    cached_tokens=params["prompt_cache_hit_tokens"]
                )

        ## ANTHROPIC MAPPING ##
        if "cache_read_input_tokens" in params and isinstance(
            params["cache_read_input_tokens"], int
        ):
            if prompt_tokens_details is None:
                prompt_tokens_details = PromptTokensDetailsWrapper(
                    cached_tokens=params["cache_read_input_tokens"]
                )

        # handle prompt_tokens_details
        _prompt_tokens_details: Optional[PromptTokensDetailsWrapper] = None
        if prompt_tokens_details:
            if isinstance(prompt_tokens_details, dict):
                _prompt_tokens_details = PromptTokensDetailsWrapper(
                    **prompt_tokens_details
                )
            elif isinstance(prompt_tokens_details, PromptTokensDetails):
                _prompt_tokens_details = prompt_tokens_details

        super().__init__(
            prompt_tokens=prompt_tokens or 0,
            completion_tokens=completion_tokens or 0,
            total_tokens=total_tokens or 0,
            completion_tokens_details=_completion_tokens_details or None,
            prompt_tokens_details=_prompt_tokens_details or None,
        )

        if server_tool_use is not None:
            self.server_tool_use = server_tool_use
        else:  # maintain openai compatibility in usage object if possible
            del self.server_tool_use

        ## ANTHROPIC MAPPING ##
        if "cache_creation_input_tokens" in params and isinstance(
            params["cache_creation_input_tokens"], int
        ):
            self._cache_creation_input_tokens = params["cache_creation_input_tokens"]

        if "cache_read_input_tokens" in params and isinstance(
            params["cache_read_input_tokens"], int
        ):
            self._cache_read_input_tokens = params["cache_read_input_tokens"]

        ## DEEPSEEK MAPPING ##
        if "prompt_cache_hit_tokens" in params and isinstance(
            params["prompt_cache_hit_tokens"], int
        ):
            self._cache_read_input_tokens = params["prompt_cache_hit_tokens"]

        for k, v in params.items():
            setattr(self, k, v)

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


class StreamingChoices(OpenAIObject):
    def __init__(
        self,
        finish_reason=None,
        index=0,
        delta: Optional[Delta] = None,
        logprobs=None,
        enhancements=None,
        **params,
    ):
        # Fix Perplexity return both delta and message cause OpenWebUI repect text
        # https://github.com/BerriAI/litellm/issues/8455
        params.pop("message", None)
        super(StreamingChoices, self).__init__(**params)
        if finish_reason:
            self.finish_reason = map_finish_reason(finish_reason)
        else:
            self.finish_reason = None
        self.index = index
        if delta is not None:
            if isinstance(delta, Delta):
                self.delta = delta
            elif isinstance(delta, dict):
                self.delta = Delta(**delta)
        else:
            self.delta = Delta()
        if enhancements is not None:
            self.enhancements = enhancements

        if logprobs is not None and isinstance(logprobs, dict):
            self.logprobs = ChoiceLogprobs(**logprobs)
        else:
            self.logprobs = logprobs  # type: ignore

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


class StreamingChatCompletionChunk(OpenAIChatCompletionChunk):
    def __init__(self, **kwargs):
        new_choices = []
        for choice in kwargs["choices"]:
            new_choice = StreamingChoices(**choice).model_dump()
            new_choices.append(new_choice)
        kwargs["choices"] = new_choices

        super().__init__(**kwargs)


from openai.types.chat import ChatCompletionChunk


class ModelResponseBase(OpenAIObject):
    id: str
    """A unique identifier for the completion."""

    created: int
    """The Unix timestamp (in seconds) of when the completion was created."""

    model: Optional[str] = None
    """The model used for completion."""

    object: str
    """The object type, which is always "text_completion" """

    system_fingerprint: Optional[str] = None
    """This fingerprint represents the backend configuration that the model runs with.

    Can be used in conjunction with the `seed` request parameter to understand when
    backend changes have been made that might impact determinism.
    """

    _hidden_params: dict = {}

    _response_headers: Optional[dict] = None


class ModelResponseStream(ModelResponseBase):
    choices: List[StreamingChoices]
    provider_specific_fields: Optional[Dict[str, Any]] = Field(default=None)

    def __init__(
        self,
        choices: Optional[
            Union[List[StreamingChoices], Union[StreamingChoices, dict, BaseModel]]
        ] = None,
        id: Optional[str] = None,
        created: Optional[int] = None,
        provider_specific_fields: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        if choices is not None and isinstance(choices, list):
            new_choices = []
            for choice in choices:
                _new_choice = None
                if isinstance(choice, StreamingChoices):
                    _new_choice = choice
                elif isinstance(choice, dict):
                    _new_choice = StreamingChoices(**choice)
                elif isinstance(choice, BaseModel):
                    _new_choice = StreamingChoices(**choice.model_dump())
                new_choices.append(_new_choice)
            kwargs["choices"] = new_choices
        else:
            kwargs["choices"] = [StreamingChoices()]

        if id is None:
            id = _generate_id()
        else:
            id = id
        if created is None:
            created = int(time.time())
        else:
            created = created

        if (
            "usage" in kwargs
            and kwargs["usage"] is not None
            and isinstance(kwargs["usage"], dict)
        ):
            kwargs["usage"] = Usage(**kwargs["usage"])

        kwargs["id"] = id
        kwargs["created"] = created
        kwargs["object"] = "chat.completion.chunk"
        kwargs["provider_specific_fields"] = provider_specific_fields

        super().__init__(**kwargs)

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict()


class ModelResponse(ModelResponseBase):
    choices: List[Union[Choices, StreamingChoices]]
    """The list of completion choices the model generated for the input prompt."""

    def __init__(
        self,
        id=None,
        choices=None,
        created=None,
        model=None,
        object=None,
        system_fingerprint=None,
        usage=None,
        stream=None,
        stream_options=None,
        response_ms=None,
        hidden_params=None,
        _response_headers=None,
        **params,
    ) -> None:
        if stream is not None and stream is True:
            object = "chat.completion.chunk"
            if choices is not None and isinstance(choices, list):
                new_choices = []
                for choice in choices:
                    _new_choice = None
                    if isinstance(choice, StreamingChoices):
                        _new_choice = choice
                    elif isinstance(choice, dict):
                        _new_choice = StreamingChoices(**choice)
                    elif isinstance(choice, BaseModel):
                        _new_choice = StreamingChoices(**choice.model_dump())
                    new_choices.append(_new_choice)
                choices = new_choices
            else:
                choices = [StreamingChoices()]
        else:
            object = "chat.completion"
            if choices is not None and isinstance(choices, list):
                new_choices = []
                for choice in choices:
                    if isinstance(choice, Choices):
                        _new_choice = choice  # type: ignore
                    elif isinstance(choice, dict):
                        _new_choice = Choices(**choice)  # type: ignore
                    else:
                        _new_choice = choice
                    new_choices.append(_new_choice)
                choices = new_choices
            else:
                choices = [Choices()]
        if id is None:
            id = _generate_id()
        else:
            id = id
        if created is None:
            created = int(time.time())
        else:
            created = created
        model = model
        if usage is not None:
            if isinstance(usage, dict):
                usage = Usage(**usage)
            else:
                usage = usage
        elif stream is None or stream is False:
            usage = Usage()
        if hidden_params:
            self._hidden_params = hidden_params

        if _response_headers:
            self._response_headers = _response_headers

        init_values = {
            "id": id,
            "choices": choices,
            "created": created,
            "model": model,
            "object": object,
            "system_fingerprint": system_fingerprint,
        }

        if usage is not None:
            init_values["usage"] = usage

        super().__init__(
            **init_values,
            **params,
        )

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict()


class Embedding(OpenAIObject):
    embedding: Union[list, str] = []
    index: int
    object: Literal["embedding"]

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


class EmbeddingResponse(OpenAIObject):
    model: Optional[str] = None
    """The model used for embedding."""

    data: List
    """The actual embedding value"""

    object: Literal["list"]
    """The object type, which is always "list" """

    usage: Optional[Usage] = None
    """Usage statistics for the embedding request."""

    _hidden_params: dict = {}
    _response_headers: Optional[Dict] = None
    _response_ms: Optional[float] = None

    def __init__(
        self,
        model: Optional[str] = None,
        usage: Optional[Usage] = None,
        response_ms=None,
        data: Optional[Union[List, List[Embedding]]] = None,
        hidden_params=None,
        _response_headers=None,
        **params,
    ):
        object = "list"
        if response_ms:
            _response_ms = response_ms
        else:
            _response_ms = None
        if data:
            data = data
        else:
            data = []

        if usage:
            usage = usage
        else:
            usage = Usage()

        if _response_headers:
            self._response_headers = _response_headers

        model = model
        super().__init__(model=model, object=object, data=data, usage=usage)  # type: ignore

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict()


class Logprobs(OpenAIObject):
    text_offset: Optional[List[int]]
    token_logprobs: Optional[List[Union[float, None]]]
    tokens: Optional[List[str]]
    top_logprobs: Optional[List[Union[Dict[str, float], None]]]


class TextChoices(OpenAIObject):
    def __init__(self, finish_reason=None, index=0, text=None, logprobs=None, **params):
        super(TextChoices, self).__init__(**params)
        if finish_reason:
            self.finish_reason = map_finish_reason(finish_reason)
        else:
            self.finish_reason = None
        self.index = index
        if text is not None:
            self.text = text
        else:
            self.text = None
        if logprobs is None:
            self.logprobs = None
        else:
            if isinstance(logprobs, dict):
                self.logprobs = Logprobs(**logprobs)
            else:
                self.logprobs = logprobs

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict()


class TextCompletionResponse(OpenAIObject):
    """
    {
        "id": response["id"],
        "object": "text_completion",
        "created": response["created"],
        "model": response["model"],
        "choices": [
        {
            "text": response["choices"][0]["message"]["content"],
            "index": response["choices"][0]["index"],
            "logprobs": transformed_logprobs,
            "finish_reason": response["choices"][0]["finish_reason"]
        }
        ],
        "usage": response["usage"]
    }
    """

    id: str
    object: str
    created: int
    model: Optional[str]
    choices: List[TextChoices]
    usage: Optional[Usage]
    _response_ms: Optional[int] = None
    _hidden_params: HiddenParams

    def __init__(
        self,
        id=None,
        choices=None,
        created=None,
        model=None,
        usage=None,
        stream=False,
        response_ms=None,
        object=None,
        **params,
    ):
        if stream:
            object = "text_completion.chunk"
            choices = [TextChoices()]
        else:
            object = "text_completion"
            if choices is not None and isinstance(choices, list):
                new_choices = []
                for choice in choices:
                    _new_choice = None
                    if isinstance(choice, TextChoices):
                        _new_choice = choice
                    elif isinstance(choice, dict):
                        _new_choice = TextChoices(**choice)
                    new_choices.append(_new_choice)
                choices = new_choices
            else:
                choices = [TextChoices()]
        if object is not None:
            object = object
        if id is None:
            id = _generate_id()
        else:
            id = id
        if created is None:
            created = int(time.time())
        else:
            created = created

        model = model
        if usage:
            usage = usage
        else:
            usage = Usage()

        super(TextCompletionResponse, self).__init__(
            id=id,  # type: ignore
            object=object,  # type: ignore
            created=created,  # type: ignore
            model=model,  # type: ignore
            choices=choices,  # type: ignore
            usage=usage,  # type: ignore
            **params,
        )

        if response_ms:
            self._response_ms = response_ms
        else:
            self._response_ms = None
        self._hidden_params = HiddenParams()

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


from openai.types.images_response import Image as OpenAIImage


class ImageObject(OpenAIImage):
    """
    Represents the url or the content of an image generated by the OpenAI API.

    Attributes:
    b64_json: The base64-encoded JSON of the generated image, if response_format is b64_json.
    url: The URL of the generated image, if response_format is url (default).
    revised_prompt: The prompt that was used to generate the image, if there was any revision to the prompt.

    https://platform.openai.com/docs/api-reference/images/object
    """

    b64_json: Optional[str] = None
    url: Optional[str] = None
    revised_prompt: Optional[str] = None

    def __init__(self, b64_json=None, url=None, revised_prompt=None, **kwargs):
        super().__init__(b64_json=b64_json, url=url, revised_prompt=revised_prompt)  # type: ignore

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict()


class ImageUsageInputTokensDetails(BaseLiteLLMOpenAIResponseObject):
    image_tokens: int
    """The number of image tokens in the input prompt."""

    text_tokens: int
    """The number of text tokens in the input prompt."""


class ImageUsage(BaseLiteLLMOpenAIResponseObject):
    input_tokens: int
    """The number of tokens (images and text) in the input prompt."""

    input_tokens_details: ImageUsageInputTokensDetails
    """The input tokens detailed information for the image generation."""

    output_tokens: int
    """The number of image tokens in the output image."""

    total_tokens: int
    """The total number of tokens (images and text) used for the image generation."""


from openai.types.images_response import ImagesResponse as OpenAIImageResponse


class ImageResponse(OpenAIImageResponse, BaseLiteLLMOpenAIResponseObject):
    _hidden_params: dict = {}

    usage: Optional[ImageUsage] = None  # type: ignore
    """
    Users might use litellm with older python versions, we don't want this to break for them. 
    Happens when their OpenAIImageResponse has the old OpenAI usage class.
    """

    model_config = ConfigDict(extra="allow", protected_namespaces=())

    def __init__(
        self,
        created: Optional[int] = None,
        data: Optional[List[ImageObject]] = None,
        response_ms=None,
        usage: Optional[ImageUsage] = None,
        hidden_params: Optional[dict] = None,
        **kwargs,
    ):
        if response_ms:
            _response_ms = response_ms
        else:
            _response_ms = None
        if data:
            data = data
        else:
            data = []

        if created:
            created = created
        else:
            created = int(time.time())

        _data: List[OpenAIImage] = []
        for d in data:
            if isinstance(d, dict):
                _data.append(ImageObject(**d))
            elif isinstance(d, BaseModel):
                _data.append(ImageObject(**d.model_dump()))

        _usage = usage or ImageUsage(
            input_tokens=0,
            input_tokens_details=ImageUsageInputTokensDetails(
                image_tokens=0,
                text_tokens=0,
            ),
            output_tokens=0,
            total_tokens=0,
        )
        super().__init__(created=created, data=_data, usage=_usage)  # type: ignore
        self._hidden_params = hidden_params or {}

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict()


class TranscriptionResponse(OpenAIObject):
    text: Optional[str] = None

    _hidden_params: dict = {}
    _response_headers: Optional[dict] = None

    def __init__(self, text=None):
        super().__init__(text=text)  # type: ignore

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict()


class GenericImageParsingChunk(TypedDict):
    type: str
    media_type: str
    data: str


class ResponseFormatChunk(TypedDict, total=False):
    type: Required[Literal["json_object", "text"]]
    response_schema: dict


class LoggedLiteLLMParams(TypedDict, total=False):
    force_timeout: Optional[float]
    custom_llm_provider: Optional[str]
    api_base: Optional[str]
    litellm_call_id: Optional[str]
    model_alias_map: Optional[dict]
    metadata: Optional[dict]
    model_info: Optional[dict]
    proxy_server_request: Optional[dict]
    acompletion: Optional[bool]
    preset_cache_key: Optional[str]
    no_log: Optional[bool]
    input_cost_per_second: Optional[float]
    input_cost_per_token: Optional[float]
    output_cost_per_token: Optional[float]
    output_cost_per_second: Optional[float]
    cooldown_time: Optional[float]


class AdapterCompletionStreamWrapper:
    def __init__(self, completion_stream):
        self.completion_stream = completion_stream

    def __iter__(self):
        return self

    def __aiter__(self):
        return self

    def __next__(self):
        try:
            for chunk in self.completion_stream:
                if chunk == "None" or chunk is None:
                    raise Exception
                return chunk
            raise StopIteration
        except StopIteration:
            raise StopIteration
        except Exception as e:
            print(f"AdapterCompletionStreamWrapper - {e}")  # noqa

    async def __anext__(self):
        try:
            async for chunk in self.completion_stream:
                if chunk == "None" or chunk is None:
                    raise Exception
                return chunk
            raise StopIteration
        except StopIteration:
            raise StopAsyncIteration


class StandardLoggingUserAPIKeyMetadata(TypedDict):
    user_api_key_hash: Optional[str]  # hash of the litellm virtual key used
    user_api_key_alias: Optional[str]
    user_api_key_org_id: Optional[str]
    user_api_key_team_id: Optional[str]
    user_api_key_user_id: Optional[str]
    user_api_key_user_email: Optional[str]
    user_api_key_team_alias: Optional[str]
    user_api_key_end_user_id: Optional[str]
    user_api_key_request_route: Optional[str]


class StandardLoggingMCPToolCall(TypedDict, total=False):
    name: str
    """
    Name of the tool to call
    """
    arguments: dict
    """
    Arguments to pass to the tool
    """
    result: dict
    """
    Result of the tool call
    """

    mcp_server_name: Optional[str]
    """
    Name of the MCP server that the tool call was made to
    """

    mcp_server_logo_url: Optional[str]
    """
    Optional logo URL of the MCP server that the tool call was made to

    (this is to render the logo on the logs page on litellm ui)
    """


class StandardLoggingVectorStoreRequest(TypedDict, total=False):
    """
    Logging information for a vector store request/payload
    """

    vector_store_id: Optional[str]
    """
    ID of the vector store
    """

    custom_llm_provider: Optional[str]
    """
    Custom LLM provider the vector store is associated with eg. bedrock, openai, anthropic, etc.
    """

    query: Optional[str]
    """
    Query to the vector store
    """

    vector_store_search_response: Optional[VectorStoreSearchResponse]
    """
    OpenAI format vector store search response
    """

    start_time: Optional[float]
    """
    Start time of the vector store request
    """

    end_time: Optional[float]
    """
    End time of the vector store request
    """


class StandardBuiltInToolsParams(TypedDict, total=False):
    """
    Standard built-in OpenAItools parameters

    This is used to calculate the cost of built-in tools, insert any standard built-in tools parameters here

    OpenAI charges users based on the `web_search_options` parameter
    """

    web_search_options: Optional[WebSearchOptions]
    file_search: Optional[FileSearchTool]


class StandardLoggingPromptManagementMetadata(TypedDict):
    prompt_id: str
    prompt_variables: Optional[dict]
    prompt_integration: str


class StandardLoggingMetadata(StandardLoggingUserAPIKeyMetadata):
    """
    Specific metadata k,v pairs logged to integration for easier cost tracking and prompt management
    """

    spend_logs_metadata: Optional[
        dict
    ]  # special param to log k,v pairs to spendlogs for a call
    requester_ip_address: Optional[str]
    requester_metadata: Optional[dict]
    requester_custom_headers: Optional[
        Dict[str, str]
    ]  # Log any custom (`x-`) headers sent by the client to the proxy.
    prompt_management_metadata: Optional[StandardLoggingPromptManagementMetadata]
    mcp_tool_call_metadata: Optional[StandardLoggingMCPToolCall]
    vector_store_request_metadata: Optional[List[StandardLoggingVectorStoreRequest]]
    applied_guardrails: Optional[List[str]]
    usage_object: Optional[dict]


class StandardLoggingAdditionalHeaders(TypedDict, total=False):
    x_ratelimit_limit_requests: int
    x_ratelimit_limit_tokens: int
    x_ratelimit_remaining_requests: int
    x_ratelimit_remaining_tokens: int


class StandardLoggingHiddenParams(TypedDict):
    model_id: Optional[
        str
    ]  # id of the model in the router, separates multiple models with the same name but different credentials
    cache_key: Optional[str]
    api_base: Optional[str]
    response_cost: Optional[str]
    litellm_overhead_time_ms: Optional[float]
    additional_headers: Optional[StandardLoggingAdditionalHeaders]
    batch_models: Optional[List[str]]
    litellm_model_name: Optional[str]  # the model name sent to the provider by litellm
    usage_object: Optional[dict]


class StandardLoggingModelInformation(TypedDict):
    model_map_key: str
    model_map_value: Optional[ModelInfo]


class StandardLoggingModelCostFailureDebugInformation(TypedDict, total=False):
    """
    Debug information, if cost tracking fails.

    Avoid logging sensitive information like response or optional params
    """

    error_str: Required[str]
    traceback_str: Required[str]
    model: str
    cache_hit: Optional[bool]
    custom_llm_provider: Optional[str]
    base_model: Optional[str]
    call_type: str
    custom_pricing: Optional[bool]


class StandardLoggingPayloadErrorInformation(TypedDict, total=False):
    error_code: Optional[str]
    error_class: Optional[str]
    llm_provider: Optional[str]
    traceback: Optional[str]
    error_message: Optional[str]


class StandardLoggingGuardrailInformation(TypedDict, total=False):
    guardrail_name: Optional[str]
    guardrail_mode: Optional[Union[GuardrailEventHooks, List[GuardrailEventHooks]]]
    guardrail_request: Optional[dict]
    guardrail_response: Optional[Union[dict, str, List[dict]]]
    guardrail_status: Literal["success", "failure"]
    start_time: Optional[float]
    end_time: Optional[float]
    duration: Optional[float]
    """
    Duration of the guardrail in seconds
    """

    masked_entity_count: Optional[Dict[str, int]]
    """
    Count of masked entities
    {
        "CREDIT_CARD": 2,
        "PHONE": 1
    }
    """


StandardLoggingPayloadStatus = Literal["success", "failure"]


class StandardLoggingPayload(TypedDict):
    id: str
    trace_id: str  # Trace multiple LLM calls belonging to same overall request (e.g. fallbacks/retries)
    call_type: str
    stream: Optional[bool]
    response_cost: float
    response_cost_failure_debug_info: Optional[
        StandardLoggingModelCostFailureDebugInformation
    ]
    status: StandardLoggingPayloadStatus
    custom_llm_provider: Optional[str]
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    startTime: float  # Note: making this camelCase was a mistake, everything should be snake case
    endTime: float
    completionStartTime: float
    response_time: float
    model_map_information: StandardLoggingModelInformation
    model: str
    model_id: Optional[str]
    model_group: Optional[str]
    api_base: str
    metadata: StandardLoggingMetadata
    cache_hit: Optional[bool]
    cache_key: Optional[str]
    saved_cache_cost: float
    request_tags: list
    end_user: Optional[str]
    requester_ip_address: Optional[str]
    messages: Optional[Union[str, list, dict]]
    response: Optional[Union[str, list, dict]]
    error_str: Optional[str]
    error_information: Optional[StandardLoggingPayloadErrorInformation]
    model_parameters: dict
    hidden_params: StandardLoggingHiddenParams
    guardrail_information: Optional[StandardLoggingGuardrailInformation]
    standard_built_in_tools_params: Optional[StandardBuiltInToolsParams]


from typing import AsyncIterator, Iterator


class CustomStreamingDecoder:
    async def aiter_bytes(
        self, iterator: AsyncIterator[bytes]
    ) -> AsyncIterator[
        Optional[Union[GenericStreamingChunk, StreamingChatCompletionChunk]]
    ]:
        raise NotImplementedError

    def iter_bytes(
        self, iterator: Iterator[bytes]
    ) -> Iterator[Optional[Union[GenericStreamingChunk, StreamingChatCompletionChunk]]]:
        raise NotImplementedError


class StandardPassThroughResponseObject(TypedDict):
    response: str


OPENAI_RESPONSE_HEADERS = [
    "x-ratelimit-remaining-requests",
    "x-ratelimit-remaining-tokens",
    "x-ratelimit-limit-requests",
    "x-ratelimit-limit-tokens",
    "x-ratelimit-reset-requests",
    "x-ratelimit-reset-tokens",
]


class StandardCallbackDynamicParams(TypedDict, total=False):
    # Langfuse dynamic params
    langfuse_public_key: Optional[str]
    langfuse_secret: Optional[str]
    langfuse_secret_key: Optional[str]
    langfuse_host: Optional[str]

    # GCS dynamic params
    gcs_bucket_name: Optional[str]
    gcs_path_service_account: Optional[str]

    # Langsmith dynamic params
    langsmith_api_key: Optional[str]
    langsmith_project: Optional[str]
    langsmith_base_url: Optional[str]

    # Humanloop dynamic params
    humanloop_api_key: Optional[str]

    # Arize dynamic params
    arize_api_key: Optional[str]
    arize_space_key: Optional[str]

    # Logging settings
    turn_off_message_logging: Optional[bool]  # when true will not log messages


all_litellm_params = [
    "metadata",
    "litellm_metadata",
    "litellm_trace_id",
    "tags",
    "acompletion",
    "aimg_generation",
    "atext_completion",
    "text_completion",
    "caching",
    "mock_response",
    "mock_timeout",
    "disable_add_transform_inline_image_block",
    "litellm_proxy_rate_limit_response",
    "api_key",
    "api_version",
    "prompt_id",
    "provider_specific_header",
    "prompt_variables",
    "api_base",
    "force_timeout",
    "logger_fn",
    "verbose",
    "custom_llm_provider",
    "model_file_id_mapping",
    "litellm_logging_obj",
    "litellm_call_id",
    "use_client",
    "id",
    "fallbacks",
    "azure",
    "headers",
    "model_list",
    "num_retries",
    "context_window_fallback_dict",
    "retry_policy",
    "retry_strategy",
    "roles",
    "final_prompt_value",
    "bos_token",
    "eos_token",
    "request_timeout",
    "complete_response",
    "self",
    "client",
    "rpm",
    "tpm",
    "max_parallel_requests",
    "input_cost_per_token",
    "output_cost_per_token",
    "input_cost_per_second",
    "output_cost_per_second",
    "hf_model_name",
    "model_info",
    "proxy_server_request",
    "preset_cache_key",
    "caching_groups",
    "ttl",
    "cache",
    "no-log",
    "base_model",
    "stream_timeout",
    "supports_system_message",
    "region_name",
    "allowed_model_region",
    "model_config",
    "fastest_response",
    "cooldown_time",
    "cache_key",
    "max_retries",
    "azure_ad_token_provider",
    "tenant_id",
    "client_id",
    "azure_username",
    "azure_password",
    "azure_scope",
    "client_secret",
    "user_continue_message",
    "configurable_clientside_auth_params",
    "weight",
    "ensure_alternating_roles",
    "assistant_continue_message",
    "user_continue_message",
    "fallback_depth",
    "max_fallbacks",
    "max_budget",
    "budget_duration",
    "use_in_pass_through",
    "merge_reasoning_content_in_choices",
    "litellm_credential_name",
    "allowed_openai_params",
    "litellm_session_id",
    "use_litellm_proxy",
    "prompt_label",
] + list(StandardCallbackDynamicParams.__annotations__.keys())


class KeyGenerationConfig(TypedDict, total=False):
    required_params: List[
        str
    ]  # specify params that must be present in the key generation request


class TeamUIKeyGenerationConfig(KeyGenerationConfig):
    allowed_team_member_roles: List[str]


class PersonalUIKeyGenerationConfig(KeyGenerationConfig):
    allowed_user_roles: List[str]


class StandardKeyGenerationConfig(TypedDict, total=False):
    team_key_generation: TeamUIKeyGenerationConfig
    personal_key_generation: PersonalUIKeyGenerationConfig


class BudgetConfig(BaseModel):
    max_budget: Optional[float] = None
    budget_duration: Optional[str] = None
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None

    def __init__(self, **data: Any) -> None:
        # Map time_period to budget_duration if present
        if "time_period" in data:
            data["budget_duration"] = data.pop("time_period")

        # Map budget_limit to max_budget if present
        if "budget_limit" in data:
            data["max_budget"] = data.pop("budget_limit")

        super().__init__(**data)


GenericBudgetConfigType = Dict[str, BudgetConfig]


class LlmProviders(str, Enum):
    OPENAI = "openai"
    OPENAI_LIKE = "openai_like"  # embedding only
    JINA_AI = "jina_ai"
    XAI = "xai"
    CUSTOM_OPENAI = "custom_openai"
    TEXT_COMPLETION_OPENAI = "text-completion-openai"
    COHERE = "cohere"
    COHERE_CHAT = "cohere_chat"
    CLARIFAI = "clarifai"
    ANTHROPIC = "anthropic"
    ANTHROPIC_TEXT = "anthropic_text"
    REPLICATE = "replicate"
    HUGGINGFACE = "huggingface"
    TOGETHER_AI = "together_ai"
    OPENROUTER = "openrouter"
    DATAROBOT = "datarobot"
    VERTEX_AI = "vertex_ai"
    VERTEX_AI_BETA = "vertex_ai_beta"
    GEMINI = "gemini"
    AI21 = "ai21"
    BASETEN = "baseten"
    AZURE = "azure"
    AZURE_TEXT = "azure_text"
    AZURE_AI = "azure_ai"
    SAGEMAKER = "sagemaker"
    SAGEMAKER_CHAT = "sagemaker_chat"
    BEDROCK = "bedrock"
    VLLM = "vllm"
    NLP_CLOUD = "nlp_cloud"
    PETALS = "petals"
    OOBABOOGA = "oobabooga"
    OLLAMA = "ollama"
    OLLAMA_CHAT = "ollama_chat"
    DEEPINFRA = "deepinfra"
    PERPLEXITY = "perplexity"
    MISTRAL = "mistral"
    GROQ = "groq"
    NVIDIA_NIM = "nvidia_nim"
    CEREBRAS = "cerebras"
    AI21_CHAT = "ai21_chat"
    VOLCENGINE = "volcengine"
    CODESTRAL = "codestral"
    TEXT_COMPLETION_CODESTRAL = "text-completion-codestral"
    DEEPSEEK = "deepseek"
    SAMBANOVA = "sambanova"
    MARITALK = "maritalk"
    VOYAGE = "voyage"
    CLOUDFLARE = "cloudflare"
    XINFERENCE = "xinference"
    FIREWORKS_AI = "fireworks_ai"
    FRIENDLIAI = "friendliai"
    FEATHERLESS_AI = "featherless_ai"
    WATSONX = "watsonx"
    WATSONX_TEXT = "watsonx_text"
    TRITON = "triton"
    PREDIBASE = "predibase"
    DATABRICKS = "databricks"
    EMPOWER = "empower"
    GITHUB = "github"
    CUSTOM = "custom"
    LITELLM_PROXY = "litellm_proxy"
    HOSTED_VLLM = "hosted_vllm"
    LLAMAFILE = "llamafile"
    LM_STUDIO = "lm_studio"
    GALADRIEL = "galadriel"
    NEBIUS = "nebius"
    INFINITY = "infinity"
    DEEPGRAM = "deepgram"
    NOVITA = "novita"
    AIOHTTP_OPENAI = "aiohttp_openai"
    LANGFUSE = "langfuse"
    HUMANLOOP = "humanloop"
    TOPAZ = "topaz"
    ASSEMBLYAI = "assemblyai"
    SNOWFLAKE = "snowflake"
    LLAMA = "meta_llama"
    NSCALE = "nscale"


# Create a set of all provider values for quick lookup
LlmProvidersSet = {provider.value for provider in LlmProviders}


class LiteLLMLoggingBaseClass:
    """
    Base class for logging pre and post call

    Meant to simplify type checking for logging obj.
    """

    def pre_call(self, input, api_key, model=None, additional_args={}):
        pass

    def post_call(
        self, original_response, input=None, api_key=None, additional_args={}
    ):
        pass


class CustomHuggingfaceTokenizer(TypedDict):
    identifier: str
    revision: str  # usually 'main'
    auth_token: Optional[str]


class LITELLM_IMAGE_VARIATION_PROVIDERS(Enum):
    """
    Try using an enum for endpoints. This should make it easier to track what provider is supported for what endpoint.
    """

    OPENAI = LlmProviders.OPENAI.value
    TOPAZ = LlmProviders.TOPAZ.value


class HttpHandlerRequestFields(TypedDict, total=False):
    data: dict  # request body
    params: dict  # query params
    files: dict  # file uploads
    content: Any  # raw content


class ProviderSpecificHeader(TypedDict):
    custom_llm_provider: str
    extra_headers: dict


class SelectTokenizerResponse(TypedDict):
    type: Literal["openai_tokenizer", "huggingface_tokenizer"]
    tokenizer: Any


class LiteLLMFineTuningJob(FineTuningJob):
    _hidden_params: dict = {}
    seed: Optional[int] = None  # type: ignore

    def __init__(self, **kwargs):
        if "error" in kwargs and kwargs["error"] is not None:
            # check if error is all None - if so, set error to None
            if all(value is None for value in kwargs["error"].values()):
                kwargs["error"] = None
        super().__init__(**kwargs)
        self._hidden_params = kwargs.get("_hidden_params", {})


class LiteLLMBatch(Batch):
    _hidden_params: dict = {}
    usage: Optional[Usage] = None

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict()


class LiteLLMRealtimeStreamLoggingObject(LiteLLMPydanticObjectBase):
    results: OpenAIRealtimeStreamList
    usage: Usage
    _hidden_params: dict = {}

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict()


class RawRequestTypedDict(TypedDict, total=False):
    raw_request_api_base: Optional[str]
    raw_request_body: Optional[dict]
    raw_request_headers: Optional[dict]
    error: Optional[str]


class CredentialBase(BaseModel):
    credential_name: str
    credential_info: dict


class CredentialItem(CredentialBase):
    credential_values: dict


class CreateCredentialItem(CredentialBase):
    credential_values: Optional[dict] = None
    model_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def check_credential_params(cls, values):
        if not values.get("credential_values") and not values.get("model_id"):
            raise ValueError("Either credential_values or model_id must be set")
        return values


class ExtractedFileData(TypedDict):
    """
    TypedDict for storing processed file data

    Attributes:
        filename: Name of the file if provided
        content: The file content in bytes
        content_type: MIME type of the file
        headers: Any additional headers for the file
    """

    filename: Optional[str]
    content: bytes
    content_type: Optional[str]
    headers: Mapping[str, str]


class SpecialEnums(Enum):
    LITELM_MANAGED_FILE_ID_PREFIX = "litellm_proxy"
    LITELLM_MANAGED_FILE_COMPLETE_STR = "litellm_proxy:{};unified_id,{};target_model_names,{};llm_output_file_id,{};llm_output_file_model_id,{}"

    LITELLM_MANAGED_RESPONSE_COMPLETE_STR = (
        "litellm:custom_llm_provider:{};model_id:{};response_id:{}"
    )

    LITELLM_MANAGED_BATCH_COMPLETE_STR = "litellm_proxy;model_id:{};llm_batch_id:{}"

    LITELLM_MANAGED_GENERIC_RESPONSE_COMPLETE_STR = "litellm_proxy;model_id:{};generic_response_id:{}"  # generic implementation of 'managed batches' - used for finetuning and any future work.


LLMResponseTypes = Union[
    ModelResponse,
    EmbeddingResponse,
    ImageResponse,
    OpenAIFileObject,
    LiteLLMBatch,
    LiteLLMFineTuningJob,
]


class DynamicPromptManagementParamLiteral(str, Enum):
    """
    If any of these params are passed, the user is trying to use dynamic prompt management
    """

    CACHE_CONTROL_INJECTION_POINTS = "cache_control_injection_points"
    KNOWLEDGE_BASES = "knowledge_bases"
    VECTOR_STORE_IDS = "vector_store_ids"

    @classmethod
    def list_all_params(cls):
        return [param.value for param in cls]

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\wordnet.py ===
# Natural Language Toolkit: WordNet
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bethard <Steven.Bethard@colorado.edu>
#         Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
#         Nitin Madnani <nmadnani@ets.org>
#         Nasruddin A’aidil Shari
#         Sim Wei Ying Geraldine
#         Soe Lynn
#         Francis Bond <bond@ieee.org>
#         Eric Kafe <kafe.eric@gmail.com>

# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
An NLTK interface for WordNet

WordNet is a lexical database of English.
Using synsets, helps find conceptual relationships between words
such as hypernyms, hyponyms, synonyms, antonyms etc.

For details about WordNet see:
https://wordnet.princeton.edu/

This module also allows you to find lemmas in languages
other than English from the Open Multilingual Wordnet
https://omwn.org/

"""

import math
import os
import re
import warnings
from collections import defaultdict, deque
from functools import total_ordering
from itertools import chain, islice
from operator import itemgetter

from nltk.corpus.reader import CorpusReader
from nltk.internals import deprecated
from nltk.probability import FreqDist
from nltk.util import binary_search_file as _binary_search_file

######################################################################
# Table of Contents
######################################################################
# - Constants
# - Data Classes
#   - WordNetError
#   - Lemma
#   - Synset
# - WordNet Corpus Reader
# - WordNet Information Content Corpus Reader
# - Similarity Metrics
# - Demo

######################################################################
# Constants
######################################################################

#: Positive infinity (for similarity functions)
_INF = 1e300

# { Part-of-speech constants
ADJ, ADJ_SAT, ADV, NOUN, VERB = "a", "s", "r", "n", "v"
# }

POS_LIST = [NOUN, VERB, ADJ, ADV]

# A table of strings that are used to express verb frames.
VERB_FRAME_STRINGS = (
    None,
    "Something %s",
    "Somebody %s",
    "It is %sing",
    "Something is %sing PP",
    "Something %s something Adjective/Noun",
    "Something %s Adjective/Noun",
    "Somebody %s Adjective",
    "Somebody %s something",
    "Somebody %s somebody",
    "Something %s somebody",
    "Something %s something",
    "Something %s to somebody",
    "Somebody %s on something",
    "Somebody %s somebody something",
    "Somebody %s something to somebody",
    "Somebody %s something from somebody",
    "Somebody %s somebody with something",
    "Somebody %s somebody of something",
    "Somebody %s something on somebody",
    "Somebody %s somebody PP",
    "Somebody %s something PP",
    "Somebody %s PP",
    "Somebody's (body part) %s",
    "Somebody %s somebody to INFINITIVE",
    "Somebody %s somebody INFINITIVE",
    "Somebody %s that CLAUSE",
    "Somebody %s to somebody",
    "Somebody %s to INFINITIVE",
    "Somebody %s whether INFINITIVE",
    "Somebody %s somebody into V-ing something",
    "Somebody %s something with something",
    "Somebody %s INFINITIVE",
    "Somebody %s VERB-ing",
    "It %s that CLAUSE",
    "Something %s INFINITIVE",
    # OEWN additions:
    "Somebody %s at something",
    "Somebody %s for something",
    "Somebody %s on somebody",
    "Somebody %s out of somebody",
)

SENSENUM_RE = re.compile(r"\.[\d]+\.")


######################################################################
# Data Classes
######################################################################


class WordNetError(Exception):
    """An exception class for wordnet-related errors."""


@total_ordering
class _WordNetObject:
    """A common base class for lemmas and synsets."""

    def hypernyms(self):
        return self._related("@")

    def _hypernyms(self):
        return self._related("@")

    def instance_hypernyms(self):
        return self._related("@i")

    def _instance_hypernyms(self):
        return self._related("@i")

    def hyponyms(self):
        return self._related("~")

    def instance_hyponyms(self):
        return self._related("~i")

    def member_holonyms(self):
        return self._related("#m")

    def substance_holonyms(self):
        return self._related("#s")

    def part_holonyms(self):
        return self._related("#p")

    def member_meronyms(self):
        return self._related("%m")

    def substance_meronyms(self):
        return self._related("%s")

    def part_meronyms(self):
        return self._related("%p")

    def topic_domains(self):
        return self._related(";c")

    def in_topic_domains(self):
        return self._related("-c")

    def region_domains(self):
        return self._related(";r")

    def in_region_domains(self):
        return self._related("-r")

    def usage_domains(self):
        return self._related(";u")

    def in_usage_domains(self):
        return self._related("-u")

    def attributes(self):
        return self._related("=")

    def entailments(self):
        return self._related("*")

    def causes(self):
        return self._related(">")

    def also_sees(self):
        return self._related("^")

    def verb_groups(self):
        return self._related("$")

    def similar_tos(self):
        return self._related("&")

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        return self._name == other._name

    def __ne__(self, other):
        return self._name != other._name

    def __lt__(self, other):
        return self._name < other._name


class Lemma(_WordNetObject):
    """
    The lexical entry for a single morphological form of a
    sense-disambiguated word.

    Create a Lemma from a "<word>.<pos>.<number>.<lemma>" string where:
    <word> is the morphological stem identifying the synset
    <pos> is one of the module attributes ADJ, ADJ_SAT, ADV, NOUN or VERB
    <number> is the sense number, counting from 0.
    <lemma> is the morphological form of interest

    Note that <word> and <lemma> can be different, e.g. the Synset
    'salt.n.03' has the Lemmas 'salt.n.03.salt', 'salt.n.03.saltiness' and
    'salt.n.03.salinity'.

    Lemma attributes, accessible via methods with the same name:

    - name: The canonical name of this lemma.
    - synset: The synset that this lemma belongs to.
    - syntactic_marker: For adjectives, the WordNet string identifying the
      syntactic position relative modified noun. See:
      https://wordnet.princeton.edu/documentation/wninput5wn
      For all other parts of speech, this attribute is None.
    - count: The frequency of this lemma in wordnet.

    Lemma methods:

    Lemmas have the following methods for retrieving related Lemmas. They
    correspond to the names for the pointer symbols defined here:
    https://wordnet.princeton.edu/documentation/wninput5wn
    These methods all return lists of Lemmas:

    - antonyms
    - hypernyms, instance_hypernyms
    - hyponyms, instance_hyponyms
    - member_holonyms, substance_holonyms, part_holonyms
    - member_meronyms, substance_meronyms, part_meronyms
    - topic_domains, region_domains, usage_domains
    - attributes
    - derivationally_related_forms
    - entailments
    - causes
    - also_sees
    - verb_groups
    - similar_tos
    - pertainyms
    """

    __slots__ = [
        "_wordnet_corpus_reader",
        "_name",
        "_syntactic_marker",
        "_synset",
        "_frame_strings",
        "_frame_ids",
        "_lexname_index",
        "_lex_id",
        "_lang",
        "_key",
    ]

    def __init__(
        self,
        wordnet_corpus_reader,
        synset,
        name,
        lexname_index,
        lex_id,
        syntactic_marker,
    ):
        self._wordnet_corpus_reader = wordnet_corpus_reader
        self._name = name
        self._syntactic_marker = syntactic_marker
        self._synset = synset
        self._frame_strings = []
        self._frame_ids = []
        self._lexname_index = lexname_index
        self._lex_id = lex_id
        self._lang = "eng"

        self._key = None  # gets set later.

    def name(self):
        return self._name

    def syntactic_marker(self):
        return self._syntactic_marker

    def synset(self):
        return self._synset

    def frame_strings(self):
        return self._frame_strings

    def frame_ids(self):
        return self._frame_ids

    def lang(self):
        return self._lang

    def key(self):
        return self._key

    def __repr__(self):
        tup = type(self).__name__, self._synset._name, self._name
        return "%s('%s.%s')" % tup

    def _related(self, relation_symbol):
        get_synset = self._wordnet_corpus_reader.synset_from_pos_and_offset
        if (self._name, relation_symbol) not in self._synset._lemma_pointers:
            return []
        return [
            get_synset(pos, offset)._lemmas[lemma_index]
            for pos, offset, lemma_index in self._synset._lemma_pointers[
                self._name, relation_symbol
            ]
        ]

    def count(self):
        """Return the frequency count for this Lemma"""
        return self._wordnet_corpus_reader.lemma_count(self)

    def antonyms(self):
        return self._related("!")

    def derivationally_related_forms(self):
        return self._related("+")

    def pertainyms(self):
        return self._related("\\")


class Synset(_WordNetObject):
    """Create a Synset from a "<lemma>.<pos>.<number>" string where:
    <lemma> is the word's morphological stem
    <pos> is one of the module attributes ADJ, ADJ_SAT, ADV, NOUN or VERB
    <number> is the sense number, counting from 0.

    Synset attributes, accessible via methods with the same name:

    - name: The canonical name of this synset, formed using the first lemma
      of this synset. Note that this may be different from the name
      passed to the constructor if that string used a different lemma to
      identify the synset.
    - pos: The synset's part of speech, matching one of the module level
      attributes ADJ, ADJ_SAT, ADV, NOUN or VERB.
    - lemmas: A list of the Lemma objects for this synset.
    - definition: The definition for this synset.
    - examples: A list of example strings for this synset.
    - offset: The offset in the WordNet dict file of this synset.
    - lexname: The name of the lexicographer file containing this synset.

    Synset methods:

    Synsets have the following methods for retrieving related Synsets.
    They correspond to the names for the pointer symbols defined here:
    https://wordnet.princeton.edu/documentation/wninput5wn
    These methods all return lists of Synsets.

    - hypernyms, instance_hypernyms
    - hyponyms, instance_hyponyms
    - member_holonyms, substance_holonyms, part_holonyms
    - member_meronyms, substance_meronyms, part_meronyms
    - attributes
    - entailments
    - causes
    - also_sees
    - verb_groups
    - similar_tos

    Additionally, Synsets support the following methods specific to the
    hypernym relation:

    - root_hypernyms
    - common_hypernyms
    - lowest_common_hypernyms

    Note that Synsets do not support the following relations because
    these are defined by WordNet as lexical relations:

    - antonyms
    - derivationally_related_forms
    - pertainyms
    """

    __slots__ = [
        "_pos",
        "_offset",
        "_name",
        "_frame_ids",
        "_lemmas",
        "_lemma_names",
        "_definition",
        "_examples",
        "_lexname",
        "_pointers",
        "_lemma_pointers",
        "_max_depth",
        "_min_depth",
    ]

    def __init__(self, wordnet_corpus_reader):
        self._wordnet_corpus_reader = wordnet_corpus_reader
        # All of these attributes get initialized by
        # WordNetCorpusReader._synset_from_pos_and_line()

        self._pos = None
        self._offset = None
        self._name = None
        self._frame_ids = []
        self._lemmas = []
        self._lemma_names = []
        self._definition = None
        self._examples = []
        self._lexname = None  # lexicographer name
        self._all_hypernyms = None

        self._pointers = defaultdict(set)
        self._lemma_pointers = defaultdict(list)

    def pos(self):
        return self._pos

    def offset(self):
        return self._offset

    def name(self):
        return self._name

    def frame_ids(self):
        return self._frame_ids

    def _doc(self, doc_type, default, lang="eng"):
        """Helper method for Synset.definition and Synset.examples"""
        corpus = self._wordnet_corpus_reader
        if lang not in corpus.langs():
            return None
        elif lang == "eng":
            return default
        else:
            corpus._load_lang_data(lang)
            of = corpus.ss2of(self)
            i = corpus.lg_attrs.index(doc_type)
            if of in corpus._lang_data[lang][i]:
                return corpus._lang_data[lang][i][of]
            else:
                return None

    def definition(self, lang="eng"):
        """Return definition in specified language"""
        return self._doc("def", self._definition, lang=lang)

    def examples(self, lang="eng"):
        """Return examples in specified language"""
        return self._doc("exe", self._examples, lang=lang)

    def lexname(self):
        return self._lexname

    def _needs_root(self):
        if self._pos == NOUN and self._wordnet_corpus_reader.get_version() != "1.6":
            return False
        else:
            return True

    def lemma_names(self, lang="eng"):
        """Return all the lemma_names associated with the synset"""
        if lang == "eng":
            return self._lemma_names
        else:
            reader = self._wordnet_corpus_reader
            reader._load_lang_data(lang)
            i = reader.ss2of(self)
            if i in reader._lang_data[lang][0]:
                return reader._lang_data[lang][0][i]
            else:
                return []

    def lemmas(self, lang="eng"):
        """Return all the lemma objects associated with the synset"""
        if lang == "eng":
            return self._lemmas
        elif self._name:
            self._wordnet_corpus_reader._load_lang_data(lang)
            lemmark = []
            lemmy = self.lemma_names(lang)
            for lem in lemmy:
                temp = Lemma(
                    self._wordnet_corpus_reader,
                    self,
                    lem,
                    self._wordnet_corpus_reader._lexnames.index(self.lexname()),
                    0,
                    None,
                )
                temp._lang = lang
                lemmark.append(temp)
            return lemmark

    def root_hypernyms(self):
        """Get the topmost hypernyms of this synset in WordNet."""

        result = []
        seen = set()
        todo = [self]
        while todo:
            next_synset = todo.pop()
            if next_synset not in seen:
                seen.add(next_synset)
                next_hypernyms = (
                    next_synset.hypernyms() + next_synset.instance_hypernyms()
                )
                if not next_hypernyms:
                    result.append(next_synset)
                else:
                    todo.extend(next_hypernyms)
        return result

    # Simpler implementation which makes incorrect assumption that
    # hypernym hierarchy is acyclic:
    #
    #        if not self.hypernyms():
    #            return [self]
    #        else:
    #            return list(set(root for h in self.hypernyms()
    #                            for root in h.root_hypernyms()))
    def max_depth(self):
        """
        :return: The length of the longest hypernym path from this
            synset to the root.
        """

        if "_max_depth" not in self.__dict__:
            hypernyms = self.hypernyms() + self.instance_hypernyms()
            if not hypernyms:
                self._max_depth = 0
            else:
                self._max_depth = 1 + max(h.max_depth() for h in hypernyms)
        return self._max_depth

    def min_depth(self):
        """
        :return: The length of the shortest hypernym path from this
            synset to the root.
        """

        if "_min_depth" not in self.__dict__:
            hypernyms = self.hypernyms() + self.instance_hypernyms()
            if not hypernyms:
                self._min_depth = 0
            else:
                self._min_depth = 1 + min(h.min_depth() for h in hypernyms)
        return self._min_depth

    def closure(self, rel, depth=-1):
        """
        Return the transitive closure of source under the rel
        relationship, breadth-first, discarding cycles:

        >>> from nltk.corpus import wordnet as wn
        >>> computer = wn.synset('computer.n.01')
        >>> topic = lambda s:s.topic_domains()
        >>> print(list(computer.closure(topic)))
        [Synset('computer_science.n.01')]

        UserWarning: Discarded redundant search for Synset('computer.n.01') at depth 2


        Include redundant paths (but only once), avoiding duplicate searches
        (from 'animal.n.01' to 'entity.n.01'):

        >>> dog = wn.synset('dog.n.01')
        >>> hyp = lambda s:sorted(s.hypernyms())
        >>> print(list(dog.closure(hyp)))
        [Synset('canine.n.02'), Synset('domestic_animal.n.01'), Synset('carnivore.n.01'),\
 Synset('animal.n.01'), Synset('placental.n.01'), Synset('organism.n.01'),\
 Synset('mammal.n.01'), Synset('living_thing.n.01'), Synset('vertebrate.n.01'),\
 Synset('whole.n.02'), Synset('chordate.n.01'), Synset('object.n.01'),\
 Synset('physical_entity.n.01'), Synset('entity.n.01')]

        UserWarning: Discarded redundant search for Synset('animal.n.01') at depth 7
        """

        from nltk.util import acyclic_breadth_first

        for synset in acyclic_breadth_first(self, rel, depth):
            if synset != self:
                yield synset

    from nltk.util import acyclic_depth_first as acyclic_tree
    from nltk.util import unweighted_minimum_spanning_tree as mst

    # Also add this shortcut?
    #    from nltk.util import unweighted_minimum_spanning_digraph as umsd

    def tree(self, rel, depth=-1, cut_mark=None):
        """
        Return the full relation tree, including self,
        discarding cycles:

        >>> from nltk.corpus import wordnet as wn
        >>> from pprint import pprint
        >>> computer = wn.synset('computer.n.01')
        >>> topic = lambda s:sorted(s.topic_domains())
        >>> pprint(computer.tree(topic))
        [Synset('computer.n.01'), [Synset('computer_science.n.01')]]

        UserWarning: Discarded redundant search for Synset('computer.n.01') at depth -3


        But keep duplicate branches (from 'animal.n.01' to 'entity.n.01'):

        >>> dog = wn.synset('dog.n.01')
        >>> hyp = lambda s:sorted(s.hypernyms())
        >>> pprint(dog.tree(hyp))
        [Synset('dog.n.01'),
         [Synset('canine.n.02'),
          [Synset('carnivore.n.01'),
           [Synset('placental.n.01'),
            [Synset('mammal.n.01'),
             [Synset('vertebrate.n.01'),
              [Synset('chordate.n.01'),
               [Synset('animal.n.01'),
                [Synset('organism.n.01'),
                 [Synset('living_thing.n.01'),
                  [Synset('whole.n.02'),
                   [Synset('object.n.01'),
                    [Synset('physical_entity.n.01'),
                     [Synset('entity.n.01')]]]]]]]]]]]]],
         [Synset('domestic_animal.n.01'),
          [Synset('animal.n.01'),
           [Synset('organism.n.01'),
            [Synset('living_thing.n.01'),
             [Synset('whole.n.02'),
              [Synset('object.n.01'),
               [Synset('physical_entity.n.01'), [Synset('entity.n.01')]]]]]]]]]
        """

        from nltk.util import acyclic_branches_depth_first

        return acyclic_branches_depth_first(self, rel, depth, cut_mark)

    def hypernym_paths(self):
        """
        Get the path(s) from this synset to the root, where each path is a
        list of the synset nodes traversed on the way to the root.

        :return: A list of lists, where each list gives the node sequence
           connecting the initial ``Synset`` node and a root node.
        """
        paths = []

        hypernyms = self.hypernyms() + self.instance_hypernyms()
        if len(hypernyms) == 0:
            paths = [[self]]

        for hypernym in hypernyms:
            for ancestor_list in hypernym.hypernym_paths():
                ancestor_list.append(self)
                paths.append(ancestor_list)
        return paths

    def common_hypernyms(self, other):
        """
        Find all synsets that are hypernyms of this synset and the
        other synset.

        :type other: Synset
        :param other: other input synset.
        :return: The synsets that are hypernyms of both synsets.
        """
        if not self._all_hypernyms:
            self._all_hypernyms = {
                self_synset
                for self_synsets in self._iter_hypernym_lists()
                for self_synset in self_synsets
            }
        if not other._all_hypernyms:
            other._all_hypernyms = {
                other_synset
                for other_synsets in other._iter_hypernym_lists()
                for other_synset in other_synsets
            }
        return list(self._all_hypernyms.intersection(other._all_hypernyms))

    def lowest_common_hypernyms(self, other, simulate_root=False, use_min_depth=False):
        """
        Get a list of lowest synset(s) that both synsets have as a hypernym.
        When `use_min_depth == False` this means that the synset which appears
        as a hypernym of both `self` and `other` with the lowest maximum depth
        is returned or if there are multiple such synsets at the same depth
        they are all returned

        However, if `use_min_depth == True` then the synset(s) which has/have
        the lowest minimum depth and appear(s) in both paths is/are returned.

        By setting the use_min_depth flag to True, the behavior of NLTK2 can be
        preserved. This was changed in NLTK3 to give more accurate results in a
        small set of cases, generally with synsets concerning people. (eg:
        'chef.n.01', 'fireman.n.01', etc.)

        This method is an implementation of Ted Pedersen's "Lowest Common
        Subsumer" method from the Perl Wordnet module. It can return either
        "self" or "other" if they are a hypernym of the other.

        :type other: Synset
        :param other: other input synset
        :type simulate_root: bool
        :param simulate_root: The various verb taxonomies do not
            share a single root which disallows this metric from working for
            synsets that are not connected. This flag (False by default)
            creates a fake root that connects all the taxonomies. Set it
            to True to enable this behavior. For the noun taxonomy,
            there is usually a default root except for WordNet version 1.6.
            If you are using wordnet 1.6, a fake root will need to be added
            for nouns as well.
        :type use_min_depth: bool
        :param use_min_depth: This setting mimics older (v2) behavior of NLTK
            wordnet If True, will use the min_depth function to calculate the
            lowest common hypernyms. This is known to give strange results for
            some synset pairs (eg: 'chef.n.01', 'fireman.n.01') but is retained
            for backwards compatibility
        :return: The synsets that are the lowest common hypernyms of both
            synsets
        """
        synsets = self.common_hypernyms(other)
        if simulate_root:
            fake_synset = Synset(None)
            fake_synset._name = "*ROOT*"
            fake_synset.hypernyms = lambda: []
            fake_synset.instance_hypernyms = lambda: []
            synsets.append(fake_synset)

        try:
            if use_min_depth:
                max_depth = max(s.min_depth() for s in synsets)
                unsorted_lch = [s for s in synsets if s.min_depth() == max_depth]
            else:
                max_depth = max(s.max_depth() for s in synsets)
                unsorted_lch = [s for s in synsets if s.max_depth() == max_depth]
            return sorted(unsorted_lch)
        except ValueError:
            return []

    def hypernym_distances(self, distance=0, simulate_root=False):
        """
        Get the path(s) from this synset to the root, counting the distance
        of each node from the initial node on the way. A set of
        (synset, distance) tuples is returned.

        :type distance: int
        :param distance: the distance (number of edges) from this hypernym to
            the original hypernym ``Synset`` on which this method was called.
        :return: A set of ``(Synset, int)`` tuples where each ``Synset`` is
           a hypernym of the first ``Synset``.
        """
        distances = {(self, distance)}
        for hypernym in self._hypernyms() + self._instance_hypernyms():
            distances |= hypernym.hypernym_distances(distance + 1, simulate_root=False)
        if simulate_root:
            fake_synset = Synset(None)
            fake_synset._name = "*ROOT*"
            fake_synset_distance = max(distances, key=itemgetter(1))[1]
            distances.add((fake_synset, fake_synset_distance + 1))
        return distances

    def _shortest_hypernym_paths(self, simulate_root):
        if self._name == "*ROOT*":
            return {self: 0}

        queue = deque([(self, 0)])
        path = {}

        while queue:
            s, depth = queue.popleft()
            if s in path:
                continue
            path[s] = depth

            depth += 1
            queue.extend((hyp, depth) for hyp in s._hypernyms())
            queue.extend((hyp, depth) for hyp in s._instance_hypernyms())

        if simulate_root:
            fake_synset = Synset(None)
            fake_synset._name = "*ROOT*"
            path[fake_synset] = max(path.values()) + 1

        return path

    def shortest_path_distance(self, other, simulate_root=False):
        """
        Returns the distance of the shortest path linking the two synsets (if
        one exists). For each synset, all the ancestor nodes and their
        distances are recorded and compared. The ancestor node common to both
        synsets that can be reached with the minimum number of traversals is
        used. If no ancestor nodes are common, None is returned. If a node is
        compared with itself 0 is returned.

        :type other: Synset
        :param other: The Synset to which the shortest path will be found.
        :return: The number of edges in the shortest path connecting the two
            nodes, or None if no path exists.
        """

        if self == other:
            return 0

        dist_dict1 = self._shortest_hypernym_paths(simulate_root)
        dist_dict2 = other._shortest_hypernym_paths(simulate_root)

        # For each ancestor synset common to both subject synsets, find the
        # connecting path length. Return the shortest of these.

        inf = float("inf")
        path_distance = inf
        for synset, d1 in dist_dict1.items():
            d2 = dist_dict2.get(synset, inf)
            path_distance = min(path_distance, d1 + d2)

        return None if math.isinf(path_distance) else path_distance

    # interface to similarity methods
    def path_similarity(self, other, verbose=False, simulate_root=True):
        """
        Path Distance Similarity:
        Return a score denoting how similar two word senses are, based on the
        shortest path that connects the senses in the is-a (hypernym/hypnoym)
        taxonomy. The score is in the range 0 to 1, except in those cases where
        a path cannot be found (will only be true for verbs as there are many
        distinct verb taxonomies), in which case None is returned. A score of
        1 represents identity i.e. comparing a sense with itself will return 1.

        :type other: Synset
        :param other: The ``Synset`` that this ``Synset`` is being compared to.
        :type simulate_root: bool
        :param simulate_root: The various verb taxonomies do not
            share a single root which disallows this metric from working for
            synsets that are not connected. This flag (True by default)
            creates a fake root that connects all the taxonomies. Set it
            to false to disable this behavior. For the noun taxonomy,
            there is usually a default root except for WordNet version 1.6.
            If you are using wordnet 1.6, a fake root will be added for nouns
            as well.
        :return: A score denoting the similarity of the two ``Synset`` objects,
            normally between 0 and 1. None is returned if no connecting path
            could be found. 1 is returned if a ``Synset`` is compared with
            itself.
        """

        distance = self.shortest_path_distance(
            other,
            simulate_root=simulate_root and (self._needs_root() or other._needs_root()),
        )
        if distance is None or distance < 0:
            return None
        return 1.0 / (distance + 1)

    def lch_similarity(self, other, verbose=False, simulate_root=True):
        """
        Leacock Chodorow Similarity:
        Return a score denoting how similar two word senses are, based on the
        shortest path that connects the senses (as above) and the maximum depth
        of the taxonomy in which the senses occur. The relationship is given as
        -log(p/2d) where p is the shortest path length and d is the taxonomy
        depth.

        :type  other: Synset
        :param other: The ``Synset`` that this ``Synset`` is being compared to.
        :type simulate_root: bool
        :param simulate_root: The various verb taxonomies do not
            share a single root which disallows this metric from working for
            synsets that are not connected. This flag (True by default)
            creates a fake root that connects all the taxonomies. Set it
            to false to disable this behavior. For the noun taxonomy,
            there is usually a default root except for WordNet version 1.6.
            If you are using wordnet 1.6, a fake root will be added for nouns
            as well.
        :return: A score denoting the similarity of the two ``Synset`` objects,
            normally greater than 0. None is returned if no connecting path
            could be found. If a ``Synset`` is compared with itself, the
            maximum score is returned, which varies depending on the taxonomy
            depth.
        """

        if self._pos != other._pos:
            raise WordNetError(
                "Computing the lch similarity requires "
                "%s and %s to have the same part of speech." % (self, other)
            )

        need_root = self._needs_root()

        if self._pos not in self._wordnet_corpus_reader._max_depth:
            self._wordnet_corpus_reader._compute_max_depth(self._pos, need_root)

        depth = self._wordnet_corpus_reader._max_depth[self._pos]

        distance = self.shortest_path_distance(
            other, simulate_root=simulate_root and need_root
        )

        if distance is None or distance < 0 or depth == 0:
            return None
        return -math.log((distance + 1) / (2.0 * depth))

    def wup_similarity(self, other, verbose=False, simulate_root=True):
        """
        Wu-Palmer Similarity:
        Return a score denoting how similar two word senses are, based on the
        depth of the two senses in the taxonomy and that of their Least Common
        Subsumer (most specific ancestor node). Previously, the scores computed
        by this implementation did _not_ always agree with those given by
        Pedersen's Perl implementation of WordNet Similarity. However, with
        the addition of the simulate_root flag (see below), the score for
        verbs now almost always agree but not always for nouns.

        The LCS does not necessarily feature in the shortest path connecting
        the two senses, as it is by definition the common ancestor deepest in
        the taxonomy, not closest to the two senses. Typically, however, it
        will so feature. Where multiple candidates for the LCS exist, that
        whose shortest path to the root node is the longest will be selected.
        Where the LCS has multiple paths to the root, the longer path is used
        for the purposes of the calculation.

        :type  other: Synset
        :param other: The ``Synset`` that this ``Synset`` is being compared to.
        :type simulate_root: bool
        :param simulate_root: The various verb taxonomies do not
            share a single root which disallows this metric from working for
            synsets that are not connected. This flag (True by default)
            creates a fake root that connects all the taxonomies. Set it
            to false to disable this behavior. For the noun taxonomy,
            there is usually a default root except for WordNet version 1.6.
            If you are using wordnet 1.6, a fake root will be added for nouns
            as well.
        :return: A float score denoting the similarity of the two ``Synset``
            objects, normally greater than zero. If no connecting path between
            the two senses can be found, None is returned.

        """
        need_root = self._needs_root() or other._needs_root()

        # Note that to preserve behavior from NLTK2 we set use_min_depth=True
        # It is possible that more accurate results could be obtained by
        # removing this setting and it should be tested later on
        subsumers = self.lowest_common_hypernyms(
            other, simulate_root=simulate_root and need_root, use_min_depth=True
        )

        # If no LCS was found return None
        if len(subsumers) == 0:
            return None

        subsumer = self if self in subsumers else subsumers[0]

        # Get the longest path from the LCS to the root,
        # including a correction:
        # - add one because the calculations include both the start and end
        #   nodes
        depth = subsumer.max_depth() + 1

        # Note: No need for an additional add-one correction for non-nouns
        # to account for an imaginary root node because that is now
        # automatically handled by simulate_root
        # if subsumer._pos != NOUN:
        #     depth += 1

        # Get the shortest path from the LCS to each of the synsets it is
        # subsuming.  Add this to the LCS path length to get the path
        # length from each synset to the root.
        len1 = self.shortest_path_distance(
            subsumer, simulate_root=simulate_root and need_root
        )
        len2 = other.shortest_path_distance(
            subsumer, simulate_root=simulate_root and need_root
        )
        if len1 is None or len2 is None:
            return None
        len1 += depth
        len2 += depth
        return (2.0 * depth) / (len1 + len2)

    def res_similarity(self, other, ic, verbose=False):
        """
        Resnik Similarity:
        Return a score denoting how similar two word senses are, based on the
        Information Content (IC) of the Least Common Subsumer (most specific
        ancestor node).

        :type  other: Synset
        :param other: The ``Synset`` that this ``Synset`` is being compared to.
        :type ic: dict
        :param ic: an information content object (as returned by
            ``nltk.corpus.wordnet_ic.ic()``).
        :return: A float score denoting the similarity of the two ``Synset``
            objects. Synsets whose LCS is the root node of the taxonomy will
            have a score of 0 (e.g. N['dog'][0] and N['table'][0]).
        """

        ic1, ic2, lcs_ic = _lcs_ic(self, other, ic)
        return lcs_ic

    def jcn_similarity(self, other, ic, verbose=False):
        """
        Jiang-Conrath Similarity:
        Return a score denoting how similar two word senses are, based on the
        Information Content (IC) of the Least Common Subsumer (most specific
        ancestor node) and that of the two input Synsets. The relationship is
        given by the equation 1 / (IC(s1) + IC(s2) - 2 * IC(lcs)).

        :type  other: Synset
        :param other: The ``Synset`` that this ``Synset`` is being compared to.
        :type  ic: dict
        :param ic: an information content object (as returned by
            ``nltk.corpus.wordnet_ic.ic()``).
        :return: A float score denoting the similarity of the two ``Synset``
            objects.
        """

        if self == other:
            return _INF

        ic1, ic2, lcs_ic = _lcs_ic(self, other, ic)

        # If either of the input synsets are the root synset, or have a
        # frequency of 0 (sparse data problem), return 0.
        if ic1 == 0 or ic2 == 0:
            return 0

        ic_difference = ic1 + ic2 - 2 * lcs_ic

        if ic_difference == 0:
            return _INF

        return 1 / ic_difference

    def lin_similarity(self, other, ic, verbose=False):
        """
        Lin Similarity:
        Return a score denoting how similar two word senses are, based on the
        Information Content (IC) of the Least Common Subsumer (most specific
        ancestor node) and that of the two input Synsets. The relationship is
        given by the equation 2 * IC(lcs) / (IC(s1) + IC(s2)).

        :type other: Synset
        :param other: The ``Synset`` that this ``Synset`` is being compared to.
        :type ic: dict
        :param ic: an information content object (as returned by
            ``nltk.corpus.wordnet_ic.ic()``).
        :return: A float score denoting the similarity of the two ``Synset``
            objects, in the range 0 to 1.
        """

        ic1, ic2, lcs_ic = _lcs_ic(self, other, ic)
        return (2.0 * lcs_ic) / (ic1 + ic2)

    def _iter_hypernym_lists(self):
        """
        :return: An iterator over ``Synset`` objects that are either proper
        hypernyms or instance of hypernyms of the synset.
        """
        todo = [self]
        seen = set()
        while todo:
            for synset in todo:
                seen.add(synset)
            yield todo
            todo = [
                hypernym
                for synset in todo
                for hypernym in (synset.hypernyms() + synset.instance_hypernyms())
                if hypernym not in seen
            ]

    def __repr__(self):
        return f"{type(self).__name__}('{self._name}')"

    def _related(self, relation_symbol):
        get_synset = self._wordnet_corpus_reader.synset_from_pos_and_offset
        if relation_symbol not in self._pointers:
            return []
        pointer_tuples = self._pointers[relation_symbol]
        r = [get_synset(pos, offset) for pos, offset in pointer_tuples]
        return r


######################################################################
# WordNet Corpus Reader
######################################################################


class WordNetCorpusReader(CorpusReader):
    """
    A corpus reader used to access wordnet or its variants.
    """

    _ENCODING = "utf8"

    # { Part-of-speech constants
    ADJ, ADJ_SAT, ADV, NOUN, VERB = "a", "s", "r", "n", "v"
    # }

    # { Filename constants
    _FILEMAP = {ADJ: "adj", ADV: "adv", NOUN: "noun", VERB: "verb"}
    # }

    # { Part of speech constants
    _pos_numbers = {NOUN: 1, VERB: 2, ADJ: 3, ADV: 4, ADJ_SAT: 5}
    _pos_names = dict(tup[::-1] for tup in _pos_numbers.items())
    # }

    #: A list of file identifiers for all the fileids used by this
    #: corpus reader.
    _FILES = (
        "cntlist.rev",
        "lexnames",
        "index.sense",
        "index.adj",
        "index.adv",
        "index.noun",
        "index.verb",
        "data.adj",
        "data.adv",
        "data.noun",
        "data.verb",
        "adj.exc",
        "adv.exc",
        "noun.exc",
        "verb.exc",
    )

    def __init__(self, root, omw_reader):
        """
        Construct a new wordnet corpus reader, with the given root
        directory.
        """

        super().__init__(root, self._FILES, encoding=self._ENCODING)

        # A index that provides the file offset
        # Map from lemma -> pos -> synset_index -> offset
        self._lemma_pos_offset_map = defaultdict(dict)

        # A cache so we don't have to reconstruct synsets
        # Map from pos -> offset -> synset
        self._synset_offset_cache = defaultdict(dict)

        # A lookup for the maximum depth of each part of speech.  Useful for
        # the lch similarity metric.
        self._max_depth = defaultdict(dict)

        # Corpus reader containing omw data.
        self._omw_reader = omw_reader

        # Corpus reader containing extended_omw data.
        self._exomw_reader = None

        self.provenances = defaultdict(str)
        self.provenances["eng"] = ""

        if self._omw_reader is None:
            warnings.warn(
                "The multilingual functions are not available with this Wordnet version"
            )

        self.omw_langs = set()

        # A cache to store the wordnet data of multiple languages
        self._lang_data = defaultdict(list)

        self._data_file_map = {}
        self._exception_map = {}
        self._lexnames = []
        self._key_count_file = None
        self._key_synset_file = None

        # Load the lexnames
        with self.open("lexnames") as fp:
            for i, line in enumerate(fp):
                index, lexname, _ = line.split()
                assert int(index) == i
                self._lexnames.append(lexname)

        # Load the indices for lemmas and synset offsets
        self._load_lemma_pos_offset_map()

        # load the exception file data into memory
        self._load_exception_map()

        self.nomap = {}
        self.splits = {}
        self.merges = {}

        # map from WordNet 3.0 for OMW data
        self.map30 = self.map_wn()

        # Language data attributes
        self.lg_attrs = ["lemma", "of", "def", "exe"]

    def index_sense(self, version=None):
        """Read sense key to synset id mapping from index.sense file in corpus directory"""
        fn = "index.sense"
        if version:
            from nltk.corpus import CorpusReader, LazyCorpusLoader

            ixreader = LazyCorpusLoader(version, CorpusReader, r".*/" + fn)
        else:
            ixreader = self
        with ixreader.open(fn) as fp:
            sensekey_map = {}
            for line in fp:
                fields = line.strip().split()
                sensekey = fields[0]
                pos = self._pos_names[int(sensekey.split("%")[1].split(":")[0])]
                sensekey_map[sensekey] = f"{fields[1]}-{pos}"
        return sensekey_map

    def map_to_many(self, version="wordnet"):
        sensekey_map1 = self.index_sense(version)
        sensekey_map2 = self.index_sense()
        synset_to_many = {}
        for synsetid in set(sensekey_map1.values()):
            synset_to_many[synsetid] = []
        for sensekey in set(sensekey_map1.keys()).intersection(
            set(sensekey_map2.keys())
        ):
            source = sensekey_map1[sensekey]
            target = sensekey_map2[sensekey]
            synset_to_many[source].append(target)
        return synset_to_many

    def map_to_one(self, version="wordnet"):
        self.nomap[version] = set()
        self.splits[version] = {}
        synset_to_many = self.map_to_many(version)
        synset_to_one = {}
        for source in synset_to_many:
            candidates_bag = synset_to_many[source]
            if candidates_bag:
                candidates_set = set(candidates_bag)
                if len(candidates_set) == 1:
                    target = candidates_bag[0]
                else:
                    counts = []
                    for candidate in candidates_set:
                        counts.append((candidates_bag.count(candidate), candidate))
                    self.splits[version][source] = counts
                    target = max(counts)[1]
                synset_to_one[source] = target
                if source[-1] == "s":
                    # Add a mapping from "a" to target for applications like omw,
                    # where only Lithuanian and Slovak use the "s" ss_type.
                    synset_to_one[f"{source[:-1]}a"] = target
            else:
                self.nomap[version].add(source)
        return synset_to_one

    def map_wn(self, version="wordnet"):
        """Mapping from Wordnet 'version' to currently loaded Wordnet version"""
        if self.get_version() == version:
            return None
        else:
            return self.map_to_one(version)

    def split_synsets(self, version="wordnet"):
        if version not in self.splits:
            _mymap = self.map_to_one(version)
        return self.splits[version]

    def merged_synsets(self, version="wordnet"):
        if version not in self.merges:
            merge = defaultdict(set)
            for source, targets in self.map_to_many(version).items():
                for target in targets:
                    merge[target].add(source)
            self.merges[version] = {
                trg: src for trg, src in merge.items() if len(src) > 1
            }
        return self.merges[version]

    # Open Multilingual WordNet functions, contributed by
    # Nasruddin A’aidil Shari, Sim Wei Ying Geraldine, and Soe Lynn

    def of2ss(self, of):
        """take an id and return the synsets"""
        return self.synset_from_pos_and_offset(of[-1], int(of[:8]))

    def ss2of(self, ss):
        """return the ID of the synset"""
        if ss:
            return f"{ss.offset():08d}-{ss.pos()}"

    def _load_lang_data(self, lang):
        """load the wordnet data of the requested language from the file to
        the cache, _lang_data"""

        if lang in self._lang_data:
            return

        if self._omw_reader and not self.omw_langs:
            self.add_omw()

        if lang not in self.langs():
            raise WordNetError("Language is not supported.")

        if self._exomw_reader and lang not in self.omw_langs:
            reader = self._exomw_reader
        else:
            reader = self._omw_reader

        prov = self.provenances[lang]
        if prov in ["cldr", "wikt"]:
            prov2 = prov
        else:
            prov2 = "data"

        with reader.open(f"{prov}/wn-{prov2}-{lang.split('_')[0]}.tab") as fp:
            self.custom_lemmas(fp, lang)
        self.disable_custom_lemmas(lang)

    def add_provs(self, reader):
        """Add languages from Multilingual Wordnet to the provenance dictionary"""
        fileids = reader.fileids()
        for fileid in fileids:
            prov, langfile = os.path.split(fileid)
            file_name, file_extension = os.path.splitext(langfile)
            if file_extension == ".tab":
                lang = file_name.split("-")[-1]
                if lang in self.provenances or prov in ["cldr", "wikt"]:
                    # We already have another resource for this lang,
                    # so we need to further specify the lang id:
                    lang = f"{lang}_{prov}"
                self.provenances[lang] = prov

    def add_omw(self):
        self.add_provs(self._omw_reader)
        self.omw_langs = set(self.provenances.keys())

    def add_exomw(self):
        """
        Add languages from Extended OMW

        >>> import nltk
        >>> from nltk.corpus import wordnet as wn
        >>> wn.add_exomw()
        >>> print(wn.synset('intrinsically.r.01').lemmas(lang="eng_wikt"))
        [Lemma('intrinsically.r.01.per_se'), Lemma('intrinsically.r.01.as_such')]
        """
        from nltk.corpus import extended_omw

        self.add_omw()
        self._exomw_reader = extended_omw
        self.add_provs(self._exomw_reader)

    def langs(self):
        """return a list of languages supported by Multilingual Wordnet"""
        return list(self.provenances.keys())

    def _load_lemma_pos_offset_map(self):
        for suffix in self._FILEMAP.values():
            # parse each line of the file (ignoring comment lines)
            with self.open("index.%s" % suffix) as fp:
                for i, line in enumerate(fp):
                    if line.startswith(" "):
                        continue

                    _iter = iter(line.split())

                    def _next_token():
                        return next(_iter)

                    try:
                        # get the lemma and part-of-speech
                        lemma = _next_token()
                        pos = _next_token()

                        # get the number of synsets for this lemma
                        n_synsets = int(_next_token())
                        assert n_synsets > 0

                        # get and ignore the pointer symbols for all synsets of
                        # this lemma
                        n_pointers = int(_next_token())
                        [_next_token() for _ in range(n_pointers)]

                        # same as number of synsets
                        n_senses = int(_next_token())
                        assert n_synsets == n_senses

                        # get and ignore number of senses ranked according to
                        # frequency
                        _next_token()

                        # get synset offsets
                        synset_offsets = [int(_next_token()) for _ in range(n_synsets)]

                    # raise more informative error with file name and line number
                    except (AssertionError, ValueError) as e:
                        tup = ("index.%s" % suffix), (i + 1), e
                        raise WordNetError("file %s, line %i: %s" % tup) from e

                    # map lemmas and parts of speech to synsets
                    self._lemma_pos_offset_map[lemma][pos] = synset_offsets
                    if pos == ADJ:
                        # Duplicate all adjectives indiscriminately?:
                        self._lemma_pos_offset_map[lemma][ADJ_SAT] = synset_offsets

    def _load_exception_map(self):
        # load the exception file data into memory
        for pos, suffix in self._FILEMAP.items():
            self._exception_map[pos] = {}
            with self.open("%s.exc" % suffix) as fp:
                for line in fp:
                    terms = line.split()
                    self._exception_map[pos][terms[0]] = terms[1:]
        self._exception_map[ADJ_SAT] = self._exception_map[ADJ]

    def _compute_max_depth(self, pos, simulate_root):
        """
        Compute the max depth for the given part of speech.  This is
        used by the lch similarity metric.
        """
        depth = 0
        for ii in self.all_synsets(pos):
            try:
                depth = max(depth, ii.max_depth())
            except RuntimeError:
                print(ii)
        if simulate_root:
            depth += 1
        self._max_depth[pos] = depth

    def get_version(self):
        fh = self._data_file(ADJ)
        fh.seek(0)
        for line in fh:
            match = re.search(r"Word[nN]et (\d+|\d+\.\d+) Copyright", line)
            if match is not None:
                version = match.group(1)
                fh.seek(0)
                return version

    #############################################################
    # Loading Lemmas
    #############################################################

    def lemma(self, name, lang="eng"):
        """Return lemma object that matches the name"""
        # cannot simply split on first '.',
        # e.g.: '.45_caliber.a.01..45_caliber'
        separator = SENSENUM_RE.search(name).end()

        synset_name, lemma_name = name[: separator - 1], name[separator:]

        synset = self.synset(synset_name)
        for lemma in synset.lemmas(lang):
            if lemma._name == lemma_name:
                return lemma
        raise WordNetError(f"No lemma {lemma_name!r} in {synset_name!r}")

    def lemma_from_key(self, key):
        # Keys are case sensitive and always lower-case
        key = key.lower()

        lemma_name, lex_sense = key.split("%")
        pos_number, lexname_index, lex_id, _, _ = lex_sense.split(":")
        pos = self._pos_names[int(pos_number)]

        # open the key -> synset file if necessary
        if self._key_synset_file is None:
            self._key_synset_file = self.open("index.sense")

        # Find the synset for the lemma.
        synset_line = _binary_search_file(self._key_synset_file, key)
        if not synset_line:
            raise WordNetError("No synset found for key %r" % key)
        offset = int(synset_line.split()[1])
        synset = self.synset_from_pos_and_offset(pos, offset)
        # return the corresponding lemma
        for lemma in synset._lemmas:
            if lemma._key == key:
                return lemma
        raise WordNetError("No lemma found for for key %r" % key)

    #############################################################
    # Loading Synsets
    #############################################################
    def synset(self, name):
        # split name into lemma, part of speech and synset number
        lemma, pos, synset_index_str = name.lower().rsplit(".", 2)
        synset_index = int(synset_index_str) - 1

        # get the offset for this synset
        try:
            offset = self._lemma_pos_offset_map[lemma][pos][synset_index]
        except KeyError as e:
            raise WordNetError(f"No lemma {lemma!r} with part of speech {pos!r}") from e
        except IndexError as e:
            n_senses = len(self._lemma_pos_offset_map[lemma][pos])
            raise WordNetError(
                f"Lemma {lemma!r} with part of speech {pos!r} only "
                f"has {n_senses} {'sense' if n_senses == 1 else 'senses'}"
            ) from e

        # load synset information from the appropriate file
        synset = self.synset_from_pos_and_offset(pos, offset)

        # some basic sanity checks on loaded attributes
        if pos == "s" and synset._pos == "a":
            message = (
                "Adjective satellite requested but only plain "
                "adjective found for lemma %r"
            )
            raise WordNetError(message % lemma)
        assert synset._pos == pos or (pos == "a" and synset._pos == "s")

        # Return the synset object.
        return synset

    def _data_file(self, pos):
        """
        Return an open file pointer for the data file for the given
        part of speech.
        """
        if pos == ADJ_SAT:
            pos = ADJ
        if self._data_file_map.get(pos) is None:
            fileid = "data.%s" % self._FILEMAP[pos]
            self._data_file_map[pos] = self.open(fileid)
        return self._data_file_map[pos]

    def synset_from_pos_and_offset(self, pos, offset):
        """
        - pos: The synset's part of speech, matching one of the module level
          attributes ADJ, ADJ_SAT, ADV, NOUN or VERB ('a', 's', 'r', 'n', or 'v').
        - offset: The byte offset of this synset in the WordNet dict file
          for this pos.

        >>> from nltk.corpus import wordnet as wn
        >>> print(wn.synset_from_pos_and_offset('n', 1740))
        Synset('entity.n.01')
        """
        # Check to see if the synset is in the cache
        if offset in self._synset_offset_cache[pos]:
            return self._synset_offset_cache[pos][offset]

        data_file = self._data_file(pos)
        data_file.seek(offset)
        data_file_line = data_file.readline()
        # If valid, the offset equals the 8-digit 0-padded integer found at the start of the line:
        line_offset = data_file_line[:8]
        if (
            line_offset.isalnum()
            and line_offset == f"{'0'*(8-len(str(offset)))}{str(offset)}"
        ):
            synset = self._synset_from_pos_and_line(pos, data_file_line)
            assert synset._offset == offset
            self._synset_offset_cache[pos][offset] = synset
        else:
            synset = None
            warnings.warn(f"No WordNet synset found for pos={pos} at offset={offset}.")
        data_file.seek(0)
        return synset

    @deprecated("Use public method synset_from_pos_and_offset() instead")
    def _synset_from_pos_and_offset(self, *args, **kwargs):
        """
        Hack to help people like the readers of
        https://stackoverflow.com/a/27145655/1709587
        who were using this function before it was officially a public method
        """
        return self.synset_from_pos_and_offset(*args, **kwargs)

    def _synset_from_pos_and_line(self, pos, data_file_line):
        # Construct a new (empty) synset.
        synset = Synset(self)

        # parse the entry for this synset
        try:
            # parse out the definitions and examples from the gloss
            columns_str, gloss = data_file_line.strip().split("|")
            definition = re.sub(r"[\"].*?[\"]", "", gloss).strip()
            examples = re.findall(r'"([^"]*)"', gloss)
            for example in examples:
                synset._examples.append(example)

            synset._definition = definition.strip("; ")

            # split the other info into fields
            _iter = iter(columns_str.split())

            def _next_token():
                return next(_iter)

            # get the offset
            synset._offset = int(_next_token())

            # determine the lexicographer file name
            lexname_index = int(_next_token())
            synset._lexname = self._lexnames[lexname_index]

            # get the part of speech
            synset._pos = _next_token()

            # create Lemma objects for each lemma
            n_lemmas = int(_next_token(), 16)
            for _ in range(n_lemmas):
                # get the lemma name
                lemma_name = _next_token()
                # get the lex_id (used for sense_keys)
                lex_id = int(_next_token(), 16)
                # If the lemma has a syntactic marker, extract it.
                m = re.match(r"(.*?)(\(.*\))?$", lemma_name)
                lemma_name, syn_mark = m.groups()
                # create the lemma object
                lemma = Lemma(self, synset, lemma_name, lexname_index, lex_id, syn_mark)
                synset._lemmas.append(lemma)
                synset._lemma_names.append(lemma._name)

            # collect the pointer tuples
            n_pointers = int(_next_token())
            for _ in range(n_pointers):
                symbol = _next_token()
                offset = int(_next_token())
                pos = _next_token()
                lemma_ids_str = _next_token()
                if lemma_ids_str == "0000":
                    synset._pointers[symbol].add((pos, offset))
                else:
                    source_index = int(lemma_ids_str[:2], 16) - 1
                    target_index = int(lemma_ids_str[2:], 16) - 1
                    source_lemma_name = synset._lemmas[source_index]._name
                    lemma_pointers = synset._lemma_pointers
                    tups = lemma_pointers[source_lemma_name, symbol]
                    tups.append((pos, offset, target_index))

            # read the verb frames
            try:
                frame_count = int(_next_token())
            except StopIteration:
                pass
            else:
                for _ in range(frame_count):
                    # read the plus sign
                    plus = _next_token()
                    assert plus == "+"
                    # read the frame and lemma number
                    frame_number = int(_next_token())
                    frame_string_fmt = VERB_FRAME_STRINGS[frame_number]
                    lemma_number = int(_next_token(), 16)
                    # lemma number of 00 means all words in the synset
                    if lemma_number == 0:
                        synset._frame_ids.append(frame_number)
                        for lemma in synset._lemmas:
                            lemma._frame_ids.append(frame_number)
                            lemma._frame_strings.append(frame_string_fmt % lemma._name)
                    # only a specific word in the synset
                    else:
                        lemma = synset._lemmas[lemma_number - 1]
                        lemma._frame_ids.append(frame_number)
                        lemma._frame_strings.append(frame_string_fmt % lemma._name)

        # raise a more informative error with line text
        except ValueError as e:
            raise WordNetError(f"line {data_file_line!r}: {e}") from e

        # set sense keys for Lemma objects - note that this has to be
        # done afterwards so that the relations are available
        for lemma in synset._lemmas:
            if synset._pos == ADJ_SAT:
                head_lemma = synset.similar_tos()[0]._lemmas[0]
                head_name = head_lemma._name
                head_id = "%02d" % head_lemma._lex_id
            else:
                head_name = head_id = ""
            tup = (
                lemma._name,
                WordNetCorpusReader._pos_numbers[synset._pos],
                lemma._lexname_index,
                lemma._lex_id,
                head_name,
                head_id,
            )
            lemma._key = ("%s%%%d:%02d:%02d:%s:%s" % tup).lower()

        # the canonical name is based on the first lemma
        lemma_name = synset._lemmas[0]._name.lower()
        offsets = self._lemma_pos_offset_map[lemma_name][synset._pos]
        sense_index = offsets.index(synset._offset)
        tup = lemma_name, synset._pos, sense_index + 1
        synset._name = "%s.%s.%02i" % tup

        return synset

    def synset_from_sense_key(self, sense_key):
        """
        Retrieves synset based on a given sense_key. Sense keys can be
        obtained from lemma.key()

        From https://wordnet.princeton.edu/documentation/senseidx5wn:
        A sense_key is represented as::

            lemma % lex_sense (e.g. 'dog%1:18:01::')

        where lex_sense is encoded as::

            ss_type:lex_filenum:lex_id:head_word:head_id

        :lemma:       ASCII text of word/collocation, in lower case
        :ss_type:     synset type for the sense (1 digit int)
                      The synset type is encoded as follows::

                          1    NOUN
                          2    VERB
                          3    ADJECTIVE
                          4    ADVERB
                          5    ADJECTIVE SATELLITE
        :lex_filenum: name of lexicographer file containing the synset for the sense (2 digit int)
        :lex_id:      when paired with lemma, uniquely identifies a sense in the lexicographer file (2 digit int)
        :head_word:   lemma of the first word in satellite's head synset
                      Only used if sense is in an adjective satellite synset
        :head_id:     uniquely identifies sense in a lexicographer file when paired with head_word
                      Only used if head_word is present (2 digit int)

        >>> import nltk
        >>> from nltk.corpus import wordnet as wn
        >>> print(wn.synset_from_sense_key("drive%1:04:03::"))
        Synset('drive.n.06')

        >>> print(wn.synset_from_sense_key("driving%1:04:03::"))
        Synset('drive.n.06')
        """
        return self.lemma_from_key(sense_key).synset()

    #############################################################
    # Retrieve synsets and lemmas.
    #############################################################

    def synsets(self, lemma, pos=None, lang="eng", check_exceptions=True):
        """Load all synsets with a given lemma and part of speech tag.
        If no pos is specified, all synsets for all parts of speech
        will be loaded.
        If lang is specified, all the synsets associated with the lemma name
        of that language will be returned.
        """
        lemma = lemma.lower()

        if lang == "eng":
            get_synset = self.synset_from_pos_and_offset
            index = self._lemma_pos_offset_map
            if pos is None:
                pos = POS_LIST
            return [
                get_synset(p, offset)
                for p in pos
                for form in self._morphy(lemma, p, check_exceptions)
                for offset in index[form].get(p, [])
            ]

        else:
            self._load_lang_data(lang)
            synset_list = []
            if lemma in self._lang_data[lang][1]:
                for l in self._lang_data[lang][1][lemma]:
                    if pos is not None and l[-1] != pos:
                        continue
                    synset_list.append(self.of2ss(l))
            return synset_list

    def lemmas(self, lemma, pos=None, lang="eng"):
        """Return all Lemma objects with a name matching the specified lemma
        name and part of speech tag. Matches any part of speech tag if none is
        specified."""

        lemma = lemma.lower()
        if lang == "eng":
            return [
                lemma_obj
                for synset in self.synsets(lemma, pos)
                for lemma_obj in synset.lemmas()
                if lemma_obj.name().lower() == lemma
            ]

        else:
            self._load_lang_data(lang)
            lemmas = []
            syn = self.synsets(lemma, lang=lang)
            for s in syn:
                if pos is not None and s.pos() != pos:
                    continue
                for lemma_obj in s.lemmas(lang=lang):
                    if lemma_obj.name().lower() == lemma:
                        lemmas.append(lemma_obj)
            return lemmas

    def all_lemma_names(self, pos=None, lang="eng"):
        """Return all lemma names for all synsets for the given
        part of speech tag and language or languages. If pos is
        not specified, all synsets for all parts of speech will
        be used."""

        if lang == "eng":
            if pos is None:
                return iter(self._lemma_pos_offset_map)
            else:
                return (
                    lemma
                    for lemma in self._lemma_pos_offset_map
                    if pos in self._lemma_pos_offset_map[lemma]
                )
        else:
            self._load_lang_data(lang)
            lemma = []
            for i in self._lang_data[lang][0]:
                if pos is not None and i[-1] != pos:
                    continue
                lemma.extend(self._lang_data[lang][0][i])

            lemma = iter(set(lemma))
            return lemma

    def all_omw_synsets(self, pos=None, lang=None):
        if lang not in self.langs():
            return None
        self._load_lang_data(lang)
        for of in self._lang_data[lang][0]:
            if not pos or of[-1] == pos:
                ss = self.of2ss(of)
                if ss:
                    yield ss

    #            else:
    # A few OMW offsets don't exist in Wordnet 3.0.
    #                warnings.warn(f"Language {lang}: no synset found for {of}")

    def all_synsets(self, pos=None, lang="eng"):
        """Iterate over all synsets with a given part of speech tag.
        If no pos is specified, all synsets for all parts of speech
        will be loaded.
        """
        if lang == "eng":
            return self.all_eng_synsets(pos=pos)
        else:
            return self.all_omw_synsets(pos=pos, lang=lang)

    def all_eng_synsets(self, pos=None):
        if pos is None:
            pos_tags = self._FILEMAP.keys()
        else:
            pos_tags = [pos]

        cache = self._synset_offset_cache
        from_pos_and_line = self._synset_from_pos_and_line

        # generate all synsets for each part of speech
        for pos_tag in pos_tags:
            # Open the file for reading.  Note that we can not re-use
            # the file pointers from self._data_file_map here, because
            # we're defining an iterator, and those file pointers might
            # be moved while we're not looking.
            if pos_tag == ADJ_SAT:
                pos_file = ADJ
            else:
                pos_file = pos_tag
            fileid = "data.%s" % self._FILEMAP[pos_file]
            data_file = self.open(fileid)

            try:
                # generate synsets for each line in the POS file
                offset = data_file.tell()
                line = data_file.readline()
                while line:
                    if not line[0].isspace():
                        if offset in cache[pos_tag]:
                            # See if the synset is cached
                            synset = cache[pos_tag][offset]
                        else:
                            # Otherwise, parse the line
                            synset = from_pos_and_line(pos_tag, line)
                            cache[pos_tag][offset] = synset

                        # adjective satellites are in the same file as
                        # adjectives so only yield the synset if it's actually
                        # a satellite
                        if pos_tag == ADJ_SAT and synset._pos == ADJ_SAT:
                            yield synset
                        # for all other POS tags, yield all synsets (this means
                        # that adjectives also include adjective satellites)
                        elif pos_tag != ADJ_SAT:
                            yield synset
                    offset = data_file.tell()
                    line = data_file.readline()

            # close the extra file handle we opened
            except:
                data_file.close()
                raise
            else:
                data_file.close()

    def words(self, lang="eng"):
        """return lemmas of the given language as list of words"""
        return self.all_lemma_names(lang=lang)

    def synonyms(self, word, lang="eng"):
        """return nested list with the synonyms of the different senses of word in the given language"""
        return [
            sorted(list(set(ss.lemma_names(lang=lang)) - {word}))
            for ss in self.synsets(word, lang=lang)
        ]

    def doc(self, file="README", lang="eng"):
        """Return the contents of readme, license or citation file
        use lang=lang to get the file for an individual language"""
        if lang == "eng":
            reader = self
        else:
            reader = self._omw_reader
            if lang in self.langs():
                file = f"{os.path.join(self.provenances[lang],file)}"
        try:
            with reader.open(file) as fp:
                return fp.read()
        except:
            if lang in self._lang_data:
                return f"Cannot determine {file} for {lang}"
            else:
                return f"Language {lang} is not supported."

    def license(self, lang="eng"):
        """Return the contents of LICENSE (for omw)
        use lang=lang to get the license for an individual language"""
        return self.doc(file="LICENSE", lang=lang)

    def readme(self, lang="eng"):
        """Return the contents of README (for omw)
        use lang=lang to get the readme for an individual language"""
        return self.doc(file="README", lang=lang)

    def citation(self, lang="eng"):
        """Return the contents of citation.bib file (for omw)
        use lang=lang to get the citation for an individual language"""
        return self.doc(file="citation.bib", lang=lang)

    #############################################################
    # Misc
    #############################################################
    def lemma_count(self, lemma):
        """Return the frequency count for this Lemma"""
        # Currently, count is only work for English
        if lemma._lang != "eng":
            return 0
        # open the count file if we haven't already
        if self._key_count_file is None:
            self._key_count_file = self.open("cntlist.rev")
        # find the key in the counts file and return the count
        line = _binary_search_file(self._key_count_file, lemma._key)
        if line:
            return int(line.rsplit(" ", 1)[-1])
        else:
            return 0

    def path_similarity(self, synset1, synset2, verbose=False, simulate_root=True):
        return synset1.path_similarity(synset2, verbose, simulate_root)

    path_similarity.__doc__ = Synset.path_similarity.__doc__

    def lch_similarity(self, synset1, synset2, verbose=False, simulate_root=True):
        return synset1.lch_similarity(synset2, verbose, simulate_root)

    lch_similarity.__doc__ = Synset.lch_similarity.__doc__

    def wup_similarity(self, synset1, synset2, verbose=False, simulate_root=True):
        return synset1.wup_similarity(synset2, verbose, simulate_root)

    wup_similarity.__doc__ = Synset.wup_similarity.__doc__

    def res_similarity(self, synset1, synset2, ic, verbose=False):
        return synset1.res_similarity(synset2, ic, verbose)

    res_similarity.__doc__ = Synset.res_similarity.__doc__

    def jcn_similarity(self, synset1, synset2, ic, verbose=False):
        return synset1.jcn_similarity(synset2, ic, verbose)

    jcn_similarity.__doc__ = Synset.jcn_similarity.__doc__

    def lin_similarity(self, synset1, synset2, ic, verbose=False):
        return synset1.lin_similarity(synset2, ic, verbose)

    lin_similarity.__doc__ = Synset.lin_similarity.__doc__

    #############################################################
    # Morphy
    #############################################################
    # Morphy, adapted from Oliver Steele's pywordnet
    def morphy(self, form, pos=None, check_exceptions=True):
        """
        Find a possible base form for the given form, with the given
        part of speech, by checking WordNet's list of exceptional
        forms, or by substituting suffixes for this part of speech.
        If pos=None, try every part of speech until finding lemmas.
        Return the first form found in WordNet, or eventually None.

        >>> from nltk.corpus import wordnet as wn
        >>> print(wn.morphy('dogs'))
        dog
        >>> print(wn.morphy('churches'))
        church
        >>> print(wn.morphy('aardwolves'))
        aardwolf
        >>> print(wn.morphy('abaci'))
        abacus
        >>> wn.morphy('hardrock', wn.ADV)
        >>> print(wn.morphy('book', wn.NOUN))
        book
        >>> wn.morphy('book', wn.ADJ)
        """
        for pos in [pos] if pos else POS_LIST:
            analyses = self._morphy(form, pos, check_exceptions)
            if analyses:
                # Stop (don't try more parts of speech):
                return analyses[0]

    MORPHOLOGICAL_SUBSTITUTIONS = {
        NOUN: [
            ("s", ""),
            ("ses", "s"),
            ("ves", "f"),
            ("xes", "x"),
            ("zes", "z"),
            ("ches", "ch"),
            ("shes", "sh"),
            ("men", "man"),
            ("ies", "y"),
        ],
        VERB: [
            ("s", ""),
            ("ies", "y"),
            ("es", "e"),
            ("es", ""),
            ("ed", "e"),
            ("ed", ""),
            ("ing", "e"),
            ("ing", ""),
        ],
        ADJ: [("er", ""), ("est", ""), ("er", "e"), ("est", "e")],
        ADV: [],
    }

    MORPHOLOGICAL_SUBSTITUTIONS[ADJ_SAT] = MORPHOLOGICAL_SUBSTITUTIONS[ADJ]

    def _morphy(self, form, pos, check_exceptions=True):
        # from jordanbg:
        # Given an original string x
        # 1. Apply rules once to the input to get y1, y2, y3, etc.
        # 2. Return all that are in the database
        #    (edited by ekaf) If there are no matches return an empty list.

        exceptions = self._exception_map[pos]
        substitutions = self.MORPHOLOGICAL_SUBSTITUTIONS[pos]

        def apply_rules(forms):
            return [
                form[: -len(old)] + new
                for form in forms
                for old, new in substitutions
                if form.endswith(old)
            ]

        def filter_forms(forms):
            result = []
            seen = set()
            for form in forms:
                if form in self._lemma_pos_offset_map:
                    if pos in self._lemma_pos_offset_map[form]:
                        if form not in seen:
                            result.append(form)
                            seen.add(form)
            return result

        if check_exceptions and form in exceptions:
            # 0. Check the exception lists
            forms = exceptions[form]
        else:
            # 1. Apply rules once to the input to get y1, y2, y3, etc.
            forms = apply_rules([form])

        # 2. Return all that are in the database (and check the original too)
        return filter_forms([form] + forms)

    #############################################################
    # Create information content from corpus
    #############################################################
    def ic(self, corpus, weight_senses_equally=False, smoothing=1.0):
        """
        Creates an information content lookup dictionary from a corpus.

        :type corpus: CorpusReader
        :param corpus: The corpus from which we create an information
            content dictionary.
        :type weight_senses_equally: bool
        :param weight_senses_equally: If this is True, gives all
            possible senses equal weight rather than dividing by the
            number of possible senses.  (If a word has 3 synses, each
            sense gets 0.3333 per appearance when this is False, 1.0 when
            it is true.)
        :param smoothing: How much do we smooth synset counts (default is 1.0)
        :type smoothing: float
        :return: An information content dictionary
        """
        counts = FreqDist()
        for ww in corpus.words():
            counts[ww] += 1

        ic = {}
        for pp in POS_LIST:
            ic[pp] = defaultdict(float)

        # Initialize the counts with the smoothing value
        if smoothing > 0.0:
            for pp in POS_LIST:
                ic[pp][0] = smoothing
            for ss in self.all_synsets():
                pos = ss._pos
                if pos == ADJ_SAT:
                    pos = ADJ
                ic[pos][ss._offset] = smoothing

        for ww in counts:
            possible_synsets = self.synsets(ww)
            if len(possible_synsets) == 0:
                continue

            # Distribute weight among possible synsets
            weight = float(counts[ww])
            if not weight_senses_equally:
                weight /= float(len(possible_synsets))

            for ss in possible_synsets:
                pos = ss._pos
                if pos == ADJ_SAT:
                    pos = ADJ
                for level in ss._iter_hypernym_lists():
                    for hh in level:
                        ic[pos][hh._offset] += weight
                # Add the weight to the root
                ic[pos][0] += weight
        return ic

    def custom_lemmas(self, tab_file, lang):
        """
        Reads a custom tab file containing mappings of lemmas in the given
        language to Princeton WordNet 3.0 synset offsets, allowing NLTK's
        WordNet functions to then be used with that language.

        See the "Tab files" section at https://omwn.org/omw1.html for
        documentation on the Multilingual WordNet tab file format.

        :param tab_file: Tab file as a file or file-like object
        :type: lang str
        :param: lang ISO 639-3 code of the language of the tab file
        """
        lg = lang.split("_")[0]
        if len(lg) != 3:
            raise ValueError("lang should be a (3 character) ISO 639-3 code")
        self._lang_data[lang] = [
            defaultdict(list),
            defaultdict(list),
            defaultdict(list),
            defaultdict(list),
        ]
        for line in tab_file.readlines():
            if isinstance(line, bytes):
                # Support byte-stream files (e.g. as returned by Python 2's
                # open() function) as well as text-stream ones
                line = line.decode("utf-8")
            if not line.startswith("#"):
                triple = line.strip().split("\t")
                if len(triple) < 3:
                    continue
                offset_pos, label = triple[:2]
                val = triple[-1]
                if self.map30:
                    if offset_pos in self.map30:
                        # Map offset_pos to current Wordnet version:
                        offset_pos = self.map30[offset_pos]
                    else:
                        # Some OMW offsets were never in Wordnet:
                        if (
                            offset_pos not in self.nomap["wordnet"]
                            and offset_pos.replace("a", "s")
                            not in self.nomap["wordnet"]
                        ):
                            warnings.warn(
                                f"{lang}: invalid offset {offset_pos} in '{line}'"
                            )
                        continue
                elif offset_pos[-1] == "a":
                    wnss = self.of2ss(offset_pos)
                    if wnss and wnss.pos() == "s":  # Wordnet pos is "s"
                        # Label OMW adjective satellites back to their Wordnet pos ("s")
                        offset_pos = self.ss2of(wnss)
                pair = label.split(":")
                attr = pair[-1]
                if len(pair) == 1 or pair[0] == lg:
                    if attr == "lemma":
                        val = val.strip().replace(" ", "_")
                        lang_offsets = self._lang_data[lang][1][val.lower()]
                        if offset_pos not in lang_offsets:
                            lang_offsets.append(offset_pos)
                    if attr in self.lg_attrs:
                        lang_lemmas = self._lang_data[lang][self.lg_attrs.index(attr)][
                            offset_pos
                        ]
                        if val not in lang_lemmas:
                            lang_lemmas.append(val)

    def disable_custom_lemmas(self, lang):
        """prevent synsets from being mistakenly added"""
        for n in range(len(self.lg_attrs)):
            self._lang_data[lang][n].default_factory = None

    ######################################################################
    # Visualize WordNet relation graphs using Graphviz
    ######################################################################

    def digraph(
        self,
        inputs,
        rel=lambda s: s.hypernyms(),
        pos=None,
        maxdepth=-1,
        shapes=None,
        attr=None,
        verbose=False,
    ):
        """
        Produce a graphical representation from 'inputs' (a list of
        start nodes, which can be a mix of Synsets, Lemmas and/or words),
        and a synset relation, for drawing with the 'dot' graph visualisation
        program from the Graphviz package.

        Return a string in the DOT graph file language, which can then be
        converted to an image by nltk.parse.dependencygraph.dot2img(dot_string).

        Optional Parameters:
        :rel: Wordnet synset relation
        :pos: for words, restricts Part of Speech to 'n', 'v', 'a' or 'r'
        :maxdepth: limit the longest path
        :shapes: dictionary of strings that trigger a specified shape
        :attr: dictionary with global graph attributes
        :verbose: warn about cycles

        >>> from nltk.corpus import wordnet as wn
        >>> print(wn.digraph([wn.synset('dog.n.01')]))
        digraph G {
        "Synset('animal.n.01')" -> "Synset('organism.n.01')";
        "Synset('canine.n.02')" -> "Synset('carnivore.n.01')";
        "Synset('carnivore.n.01')" -> "Synset('placental.n.01')";
        "Synset('chordate.n.01')" -> "Synset('animal.n.01')";
        "Synset('dog.n.01')" -> "Synset('canine.n.02')";
        "Synset('dog.n.01')" -> "Synset('domestic_animal.n.01')";
        "Synset('domestic_animal.n.01')" -> "Synset('animal.n.01')";
        "Synset('living_thing.n.01')" -> "Synset('whole.n.02')";
        "Synset('mammal.n.01')" -> "Synset('vertebrate.n.01')";
        "Synset('object.n.01')" -> "Synset('physical_entity.n.01')";
        "Synset('organism.n.01')" -> "Synset('living_thing.n.01')";
        "Synset('physical_entity.n.01')" -> "Synset('entity.n.01')";
        "Synset('placental.n.01')" -> "Synset('mammal.n.01')";
        "Synset('vertebrate.n.01')" -> "Synset('chordate.n.01')";
        "Synset('whole.n.02')" -> "Synset('object.n.01')";
        }
        <BLANKLINE>
        """
        from nltk.util import edge_closure, edges2dot

        synsets = set()
        edges = set()
        if not shapes:
            shapes = dict()
        if not attr:
            attr = dict()

        def add_lemma(lem):
            ss = lem.synset()
            synsets.add(ss)
            edges.add((lem, ss))

        for node in inputs:
            typ = type(node)
            if typ == Synset:
                synsets.add(node)
            elif typ == Lemma:
                add_lemma(node)
            elif typ == str:
                for lemma in self.lemmas(node, pos):
                    add_lemma(lemma)

        for ss in synsets:
            edges = edges.union(edge_closure(ss, rel, maxdepth, verbose))
        dot_string = edges2dot(sorted(list(edges)), shapes=shapes, attr=attr)
        return dot_string


######################################################################
# WordNet Information Content Corpus Reader
######################################################################


class WordNetICCorpusReader(CorpusReader):
    """
    A corpus reader for the WordNet information content corpus.
    """

    def __init__(self, root, fileids):
        CorpusReader.__init__(self, root, fileids, encoding="utf8")

    # this load function would be more efficient if the data was pickled
    # Note that we can't use NLTK's frequency distributions because
    # synsets are overlapping (each instance of a synset also counts
    # as an instance of its hypernyms)
    def ic(self, icfile):
        """
        Load an information content file from the wordnet_ic corpus
        and return a dictionary.  This dictionary has just two keys,
        NOUN and VERB, whose values are dictionaries that map from
        synsets to information content values.

        :type icfile: str
        :param icfile: The name of the wordnet_ic file (e.g. "ic-brown.dat")
        :return: An information content dictionary
        """
        ic = {}
        ic[NOUN] = defaultdict(float)
        ic[VERB] = defaultdict(float)
        with self.open(icfile) as fp:
            for num, line in enumerate(fp):
                if num == 0:  # skip the header
                    continue
                fields = line.split()
                offset = int(fields[0][:-1])
                value = float(fields[1])
                pos = _get_pos(fields[0])
                if len(fields) == 3 and fields[2] == "ROOT":
                    # Store root count.
                    ic[pos][0] += value
                if value != 0:
                    ic[pos][offset] = value
        return ic


######################################################################
# Similarity metrics
######################################################################

# TODO: Add in the option to manually add a new root node; this will be
# useful for verb similarity as there exist multiple verb taxonomies.

# More information about the metrics is available at
# http://marimba.d.umn.edu/similarity/measures.html


def path_similarity(synset1, synset2, verbose=False, simulate_root=True):
    return synset1.path_similarity(
        synset2, verbose=verbose, simulate_root=simulate_root
    )


def lch_similarity(synset1, synset2, verbose=False, simulate_root=True):
    return synset1.lch_similarity(synset2, verbose=verbose, simulate_root=simulate_root)


def wup_similarity(synset1, synset2, verbose=False, simulate_root=True):
    return synset1.wup_similarity(synset2, verbose=verbose, simulate_root=simulate_root)


def res_similarity(synset1, synset2, ic, verbose=False):
    return synset1.res_similarity(synset2, ic, verbose=verbose)


def jcn_similarity(synset1, synset2, ic, verbose=False):
    return synset1.jcn_similarity(synset2, ic, verbose=verbose)


def lin_similarity(synset1, synset2, ic, verbose=False):
    return synset1.lin_similarity(synset2, ic, verbose=verbose)


path_similarity.__doc__ = Synset.path_similarity.__doc__
lch_similarity.__doc__ = Synset.lch_similarity.__doc__
wup_similarity.__doc__ = Synset.wup_similarity.__doc__
res_similarity.__doc__ = Synset.res_similarity.__doc__
jcn_similarity.__doc__ = Synset.jcn_similarity.__doc__
lin_similarity.__doc__ = Synset.lin_similarity.__doc__


def _lcs_ic(synset1, synset2, ic, verbose=False):
    """
    Get the information content of the least common subsumer that has
    the highest information content value.  If two nodes have no
    explicit common subsumer, assume that they share an artificial
    root node that is the hypernym of all explicit roots.

    :type synset1: Synset
    :param synset1: First input synset.
    :type synset2: Synset
    :param synset2: Second input synset.  Must be the same part of
    speech as the first synset.
    :type  ic: dict
    :param ic: an information content object (as returned by ``load_ic()``).
    :return: The information content of the two synsets and their most
    informative subsumer
    """
    if synset1._pos != synset2._pos:
        raise WordNetError(
            "Computing the least common subsumer requires "
            "%s and %s to have the same part of speech." % (synset1, synset2)
        )

    ic1 = information_content(synset1, ic)
    ic2 = information_content(synset2, ic)
    subsumers = synset1.common_hypernyms(synset2)
    if len(subsumers) == 0:
        subsumer_ic = 0
    else:
        subsumer_ic = max(information_content(s, ic) for s in subsumers)

    if verbose:
        print("> LCS Subsumer by content:", subsumer_ic)

    return ic1, ic2, subsumer_ic


# Utility functions


def information_content(synset, ic):
    pos = synset._pos
    if pos == ADJ_SAT:
        pos = ADJ
    try:
        icpos = ic[pos]
    except KeyError as e:
        msg = "Information content file has no entries for part-of-speech: %s"
        raise WordNetError(msg % pos) from e

    counts = icpos[synset._offset]
    if counts == 0:
        return _INF
    else:
        return -math.log(counts / icpos[0])


# get the part of speech (NOUN or VERB) from the information content record
# (each identifier has a 'n' or 'v' suffix)


def _get_pos(field):
    if field[-1] == "n":
        return NOUN
    elif field[-1] == "v":
        return VERB
    else:
        msg = (
            "Unidentified part of speech in WordNet Information Content file "
            "for field %s" % field
        )
        raise ValueError(msg)

# === NexusCore/openenv\Lib\site-packages\fontTools\ufoLib\__init__.py ===
"""
A library for importing .ufo files and their descendants.
Refer to http://unifiedfontobject.org for the UFO specification.

The main interfaces are the :class:`.UFOReader` and :class:`.UFOWriter`
classes, which support versions 1, 2, and 3 of the UFO specification.

Set variables are available for external use that list the font
info attribute names for the `fontinfo.plist` formats. These are:

- :obj:`.fontInfoAttributesVersion1`
- :obj:`.fontInfoAttributesVersion2`
- :obj:`.fontInfoAttributesVersion3`

A set listing the `fontinfo.plist` attributes that were deprecated
in version 2 is available for external use:

- :obj:`.deprecatedFontInfoAttributesVersion2`

Functions that do basic validation on values for `fontinfo.plist`
are available for external use. These are

- :func:`.validateFontInfoVersion2ValueForAttribute`
- :func:`.validateFontInfoVersion3ValueForAttribute`

Value conversion functions are available for converting
`fontinfo.plist` values between the possible format versions.

- :func:`.convertFontInfoValueForAttributeFromVersion1ToVersion2`
- :func:`.convertFontInfoValueForAttributeFromVersion2ToVersion1`
- :func:`.convertFontInfoValueForAttributeFromVersion2ToVersion3`
- :func:`.convertFontInfoValueForAttributeFromVersion3ToVersion2`
"""

import os
from copy import deepcopy
from os import fsdecode
import logging
import zipfile
import enum
from collections import OrderedDict
import fs
import fs.base
import fs.subfs
import fs.errors
import fs.copy
import fs.osfs
import fs.zipfs
import fs.tempfs
import fs.tools
from fontTools.misc import plistlib
from fontTools.ufoLib.validators import *
from fontTools.ufoLib.filenames import userNameToFileName
from fontTools.ufoLib.converters import convertUFO1OrUFO2KerningToUFO3Kerning
from fontTools.ufoLib.errors import UFOLibError
from fontTools.ufoLib.utils import numberTypes, _VersionTupleEnumMixin

__all__ = [
    "makeUFOPath",
    "UFOLibError",
    "UFOReader",
    "UFOWriter",
    "UFOReaderWriter",
    "UFOFileStructure",
    "fontInfoAttributesVersion1",
    "fontInfoAttributesVersion2",
    "fontInfoAttributesVersion3",
    "deprecatedFontInfoAttributesVersion2",
    "validateFontInfoVersion2ValueForAttribute",
    "validateFontInfoVersion3ValueForAttribute",
    "convertFontInfoValueForAttributeFromVersion1ToVersion2",
    "convertFontInfoValueForAttributeFromVersion2ToVersion1",
]

__version__ = "3.0.0"


logger = logging.getLogger(__name__)


# ---------
# Constants
# ---------

DEFAULT_GLYPHS_DIRNAME = "glyphs"
DATA_DIRNAME = "data"
IMAGES_DIRNAME = "images"
METAINFO_FILENAME = "metainfo.plist"
FONTINFO_FILENAME = "fontinfo.plist"
LIB_FILENAME = "lib.plist"
GROUPS_FILENAME = "groups.plist"
KERNING_FILENAME = "kerning.plist"
FEATURES_FILENAME = "features.fea"
LAYERCONTENTS_FILENAME = "layercontents.plist"
LAYERINFO_FILENAME = "layerinfo.plist"

DEFAULT_LAYER_NAME = "public.default"


class UFOFormatVersion(tuple, _VersionTupleEnumMixin, enum.Enum):
    FORMAT_1_0 = (1, 0)
    FORMAT_2_0 = (2, 0)
    FORMAT_3_0 = (3, 0)


# python 3.11 doesn't like when a mixin overrides a dunder method like __str__
# for some reasons it keep using Enum.__str__, see
# https://github.com/fonttools/fonttools/pull/2655
UFOFormatVersion.__str__ = _VersionTupleEnumMixin.__str__


class UFOFileStructure(enum.Enum):
    ZIP = "zip"
    PACKAGE = "package"


# --------------
# Shared Methods
# --------------


class _UFOBaseIO:
    def getFileModificationTime(self, path):
        """
        Returns the modification time for the file at the given path, as a
        floating point number giving the number of seconds since the epoch.
        The path must be relative to the UFO path.
        Returns None if the file does not exist.
        """
        try:
            dt = self.fs.getinfo(fsdecode(path), namespaces=["details"]).modified
        except (fs.errors.MissingInfoNamespace, fs.errors.ResourceNotFound):
            return None
        else:
            return dt.timestamp()

    def _getPlist(self, fileName, default=None):
        """
        Read a property list relative to the UFO filesystem's root.
        Raises UFOLibError if the file is missing and default is None,
        otherwise default is returned.

        The errors that could be raised during the reading of a plist are
        unpredictable and/or too large to list, so, a blind try: except:
        is done. If an exception occurs, a UFOLibError will be raised.
        """
        try:
            with self.fs.open(fileName, "rb") as f:
                return plistlib.load(f)
        except fs.errors.ResourceNotFound:
            if default is None:
                raise UFOLibError(
                    "'%s' is missing on %s. This file is required" % (fileName, self.fs)
                )
            else:
                return default
        except Exception as e:
            # TODO(anthrotype): try to narrow this down a little
            raise UFOLibError(f"'{fileName}' could not be read on {self.fs}: {e}")

    def _writePlist(self, fileName, obj):
        """
        Write a property list to a file relative to the UFO filesystem's root.

        Do this sort of atomically, making it harder to corrupt existing files,
        for example when plistlib encounters an error halfway during write.
        This also checks to see if text matches the text that is already in the
        file at path. If so, the file is not rewritten so that the modification
        date is preserved.

        The errors that could be raised during the writing of a plist are
        unpredictable and/or too large to list, so, a blind try: except: is done.
        If an exception occurs, a UFOLibError will be raised.
        """
        if self._havePreviousFile:
            try:
                data = plistlib.dumps(obj)
            except Exception as e:
                raise UFOLibError(
                    "'%s' could not be written on %s because "
                    "the data is not properly formatted: %s" % (fileName, self.fs, e)
                )
            if self.fs.exists(fileName) and data == self.fs.readbytes(fileName):
                return
            self.fs.writebytes(fileName, data)
        else:
            with self.fs.openbin(fileName, mode="w") as fp:
                try:
                    plistlib.dump(obj, fp)
                except Exception as e:
                    raise UFOLibError(
                        "'%s' could not be written on %s because "
                        "the data is not properly formatted: %s"
                        % (fileName, self.fs, e)
                    )


# ----------
# UFO Reader
# ----------


class UFOReader(_UFOBaseIO):
    """Read the various components of a .ufo.

    Attributes:
        path: An :class:`os.PathLike` object pointing to the .ufo.
        validate: A boolean indicating if the data read should be
          validated. Defaults to `True`.

    By default read data is validated. Set ``validate`` to
    ``False`` to not validate the data.
    """

    def __init__(self, path, validate=True):
        if hasattr(path, "__fspath__"):  # support os.PathLike objects
            path = path.__fspath__()

        if isinstance(path, str):
            structure = _sniffFileStructure(path)
            try:
                if structure is UFOFileStructure.ZIP:
                    parentFS = fs.zipfs.ZipFS(path, write=False, encoding="utf-8")
                else:
                    parentFS = fs.osfs.OSFS(path)
            except fs.errors.CreateFailed as e:
                raise UFOLibError(f"unable to open '{path}': {e}")

            if structure is UFOFileStructure.ZIP:
                # .ufoz zip files must contain a single root directory, with arbitrary
                # name, containing all the UFO files
                rootDirs = [
                    p.name
                    for p in parentFS.scandir("/")
                    # exclude macOS metadata contained in zip file
                    if p.is_dir and p.name != "__MACOSX"
                ]
                if len(rootDirs) == 1:
                    # 'ClosingSubFS' ensures that the parent zip file is closed when
                    # its root subdirectory is closed
                    self.fs = parentFS.opendir(
                        rootDirs[0], factory=fs.subfs.ClosingSubFS
                    )
                else:
                    raise UFOLibError(
                        "Expected exactly 1 root directory, found %d" % len(rootDirs)
                    )
            else:
                # normal UFO 'packages' are just a single folder
                self.fs = parentFS
            # when passed a path string, we make sure we close the newly opened fs
            # upon calling UFOReader.close method or context manager's __exit__
            self._shouldClose = True
            self._fileStructure = structure
        elif isinstance(path, fs.base.FS):
            filesystem = path
            try:
                filesystem.check()
            except fs.errors.FilesystemClosed:
                raise UFOLibError("the filesystem '%s' is closed" % path)
            else:
                self.fs = filesystem
            try:
                path = filesystem.getsyspath("/")
            except fs.errors.NoSysPath:
                # network or in-memory FS may not map to the local one
                path = str(filesystem)
            # when user passed an already initialized fs instance, it is her
            # responsibility to close it, thus UFOReader.close/__exit__ are no-op
            self._shouldClose = False
            # default to a 'package' structure
            self._fileStructure = UFOFileStructure.PACKAGE
        else:
            raise TypeError(
                "Expected a path string or fs.base.FS object, found '%s'"
                % type(path).__name__
            )
        self._path = fsdecode(path)
        self._validate = validate
        self._upConvertedKerningData = None

        try:
            self.readMetaInfo(validate=validate)
        except UFOLibError:
            self.close()
            raise

    # properties

    def _get_path(self):
        import warnings

        warnings.warn(
            "The 'path' attribute is deprecated; use the 'fs' attribute instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._path

    path = property(_get_path, doc="The path of the UFO (DEPRECATED).")

    def _get_formatVersion(self):
        import warnings

        warnings.warn(
            "The 'formatVersion' attribute is deprecated; use the 'formatVersionTuple'",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._formatVersion.major

    formatVersion = property(
        _get_formatVersion,
        doc="The (major) format version of the UFO. DEPRECATED: Use formatVersionTuple",
    )

    @property
    def formatVersionTuple(self):
        """The (major, minor) format version of the UFO.
        This is determined by reading metainfo.plist during __init__.
        """
        return self._formatVersion

    def _get_fileStructure(self):
        return self._fileStructure

    fileStructure = property(
        _get_fileStructure,
        doc=(
            "The file structure of the UFO: "
            "either UFOFileStructure.ZIP or UFOFileStructure.PACKAGE"
        ),
    )

    # up conversion

    def _upConvertKerning(self, validate):
        """
        Up convert kerning and groups in UFO 1 and 2.
        The data will be held internally until each bit of data
        has been retrieved. The conversion of both must be done
        at once, so the raw data is cached and an error is raised
        if one bit of data becomes obsolete before it is called.

        ``validate`` will validate the data.
        """
        if self._upConvertedKerningData:
            testKerning = self._readKerning()
            if testKerning != self._upConvertedKerningData["originalKerning"]:
                raise UFOLibError(
                    "The data in kerning.plist has been modified since it was converted to UFO 3 format."
                )
            testGroups = self._readGroups()
            if testGroups != self._upConvertedKerningData["originalGroups"]:
                raise UFOLibError(
                    "The data in groups.plist has been modified since it was converted to UFO 3 format."
                )
        else:
            groups = self._readGroups()
            if validate:
                invalidFormatMessage = "groups.plist is not properly formatted."
                if not isinstance(groups, dict):
                    raise UFOLibError(invalidFormatMessage)
                for groupName, glyphList in groups.items():
                    if not isinstance(groupName, str):
                        raise UFOLibError(invalidFormatMessage)
                    elif not isinstance(glyphList, list):
                        raise UFOLibError(invalidFormatMessage)
                    for glyphName in glyphList:
                        if not isinstance(glyphName, str):
                            raise UFOLibError(invalidFormatMessage)
            self._upConvertedKerningData = dict(
                kerning={},
                originalKerning=self._readKerning(),
                groups={},
                originalGroups=groups,
            )
            # convert kerning and groups
            kerning, groups, conversionMaps = convertUFO1OrUFO2KerningToUFO3Kerning(
                self._upConvertedKerningData["originalKerning"],
                deepcopy(self._upConvertedKerningData["originalGroups"]),
                self.getGlyphSet(),
            )
            # store
            self._upConvertedKerningData["kerning"] = kerning
            self._upConvertedKerningData["groups"] = groups
            self._upConvertedKerningData["groupRenameMaps"] = conversionMaps

    # support methods

    def readBytesFromPath(self, path):
        """
        Returns the bytes in the file at the given path.
        The path must be relative to the UFO's filesystem root.
        Returns None if the file does not exist.
        """
        try:
            return self.fs.readbytes(fsdecode(path))
        except fs.errors.ResourceNotFound:
            return None

    def getReadFileForPath(self, path, encoding=None):
        """
        Returns a file (or file-like) object for the file at the given path.
        The path must be relative to the UFO path.
        Returns None if the file does not exist.
        By default the file is opened in binary mode (reads bytes).
        If encoding is passed, the file is opened in text mode (reads str).

        Note: The caller is responsible for closing the open file.
        """
        path = fsdecode(path)
        try:
            if encoding is None:
                return self.fs.openbin(path)
            else:
                return self.fs.open(path, mode="r", encoding=encoding)
        except fs.errors.ResourceNotFound:
            return None

    # metainfo.plist

    def _readMetaInfo(self, validate=None):
        """
        Read metainfo.plist and return raw data. Only used for internal operations.

        ``validate`` will validate the read data, by default it is set
        to the class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        data = self._getPlist(METAINFO_FILENAME)
        if validate and not isinstance(data, dict):
            raise UFOLibError("metainfo.plist is not properly formatted.")
        try:
            formatVersionMajor = data["formatVersion"]
        except KeyError:
            raise UFOLibError(
                f"Missing required formatVersion in '{METAINFO_FILENAME}' on {self.fs}"
            )
        formatVersionMinor = data.setdefault("formatVersionMinor", 0)

        try:
            formatVersion = UFOFormatVersion((formatVersionMajor, formatVersionMinor))
        except ValueError as e:
            unsupportedMsg = (
                f"Unsupported UFO format ({formatVersionMajor}.{formatVersionMinor}) "
                f"in '{METAINFO_FILENAME}' on {self.fs}"
            )
            if validate:
                from fontTools.ufoLib.errors import UnsupportedUFOFormat

                raise UnsupportedUFOFormat(unsupportedMsg) from e

            formatVersion = UFOFormatVersion.default()
            logger.warning(
                "%s. Assuming the latest supported version (%s). "
                "Some data may be skipped or parsed incorrectly",
                unsupportedMsg,
                formatVersion,
            )
        data["formatVersionTuple"] = formatVersion
        return data

    def readMetaInfo(self, validate=None):
        """
        Read metainfo.plist and set formatVersion. Only used for internal operations.

        ``validate`` will validate the read data, by default it is set
        to the class's validate value, can be overridden.
        """
        data = self._readMetaInfo(validate=validate)
        self._formatVersion = data["formatVersionTuple"]

    # groups.plist

    def _readGroups(self):
        groups = self._getPlist(GROUPS_FILENAME, {})
        # remove any duplicate glyphs in a kerning group
        for groupName, glyphList in groups.items():
            if groupName.startswith(("public.kern1.", "public.kern2.")):
                groups[groupName] = list(OrderedDict.fromkeys(glyphList))
        return groups

    def readGroups(self, validate=None):
        """
        Read groups.plist. Returns a dict.
        ``validate`` will validate the read data, by default it is set to the
        class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        # handle up conversion
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0:
            self._upConvertKerning(validate)
            groups = self._upConvertedKerningData["groups"]
        # normal
        else:
            groups = self._readGroups()
        if validate:
            valid, message = groupsValidator(groups)
            if not valid:
                raise UFOLibError(message)
        return groups

    def getKerningGroupConversionRenameMaps(self, validate=None):
        """
        Get maps defining the renaming that was done during any
        needed kerning group conversion. This method returns a
        dictionary of this form::

                {
                        "side1" : {"old group name" : "new group name"},
                        "side2" : {"old group name" : "new group name"}
                }

        When no conversion has been performed, the side1 and side2
        dictionaries will be empty.

        ``validate`` will validate the groups, by default it is set to the
        class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        if self._formatVersion >= UFOFormatVersion.FORMAT_3_0:
            return dict(side1={}, side2={})
        # use the public group reader to force the load and
        # conversion of the data if it hasn't happened yet.
        self.readGroups(validate=validate)
        return self._upConvertedKerningData["groupRenameMaps"]

    # fontinfo.plist

    def _readInfo(self, validate):
        data = self._getPlist(FONTINFO_FILENAME, {})
        if validate and not isinstance(data, dict):
            raise UFOLibError("fontinfo.plist is not properly formatted.")
        return data

    def readInfo(self, info, validate=None):
        """
        Read fontinfo.plist. It requires an object that allows
        setting attributes with names that follow the fontinfo.plist
        version 3 specification. This will write the attributes
        defined in the file into the object.

        ``validate`` will validate the read data, by default it is set to the
        class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        infoDict = self._readInfo(validate)
        infoDataToSet = {}
        # version 1
        if self._formatVersion == UFOFormatVersion.FORMAT_1_0:
            for attr in fontInfoAttributesVersion1:
                value = infoDict.get(attr)
                if value is not None:
                    infoDataToSet[attr] = value
            infoDataToSet = _convertFontInfoDataVersion1ToVersion2(infoDataToSet)
            infoDataToSet = _convertFontInfoDataVersion2ToVersion3(infoDataToSet)
        # version 2
        elif self._formatVersion == UFOFormatVersion.FORMAT_2_0:
            for attr, dataValidationDict in list(
                fontInfoAttributesVersion2ValueData.items()
            ):
                value = infoDict.get(attr)
                if value is None:
                    continue
                infoDataToSet[attr] = value
            infoDataToSet = _convertFontInfoDataVersion2ToVersion3(infoDataToSet)
        # version 3.x
        elif self._formatVersion.major == UFOFormatVersion.FORMAT_3_0.major:
            for attr, dataValidationDict in list(
                fontInfoAttributesVersion3ValueData.items()
            ):
                value = infoDict.get(attr)
                if value is None:
                    continue
                infoDataToSet[attr] = value
        # unsupported version
        else:
            raise NotImplementedError(self._formatVersion)
        # validate data
        if validate:
            infoDataToSet = validateInfoVersion3Data(infoDataToSet)
        # populate the object
        for attr, value in list(infoDataToSet.items()):
            try:
                setattr(info, attr, value)
            except AttributeError:
                raise UFOLibError(
                    "The supplied info object does not support setting a necessary attribute (%s)."
                    % attr
                )

    # kerning.plist

    def _readKerning(self):
        data = self._getPlist(KERNING_FILENAME, {})
        return data

    def readKerning(self, validate=None):
        """
        Read kerning.plist. Returns a dict.

        ``validate`` will validate the kerning data, by default it is set to the
        class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        # handle up conversion
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0:
            self._upConvertKerning(validate)
            kerningNested = self._upConvertedKerningData["kerning"]
        # normal
        else:
            kerningNested = self._readKerning()
        if validate:
            valid, message = kerningValidator(kerningNested)
            if not valid:
                raise UFOLibError(message)
        # flatten
        kerning = {}
        for left in kerningNested:
            for right in kerningNested[left]:
                value = kerningNested[left][right]
                kerning[left, right] = value
        return kerning

    # lib.plist

    def readLib(self, validate=None):
        """
        Read lib.plist. Returns a dict.

        ``validate`` will validate the data, by default it is set to the
        class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        data = self._getPlist(LIB_FILENAME, {})
        if validate:
            valid, message = fontLibValidator(data)
            if not valid:
                raise UFOLibError(message)
        return data

    # features.fea

    def readFeatures(self):
        """
        Read features.fea. Return a string.
        The returned string is empty if the file is missing.
        """
        try:
            with self.fs.open(FEATURES_FILENAME, "r", encoding="utf-8-sig") as f:
                return f.read()
        except fs.errors.ResourceNotFound:
            return ""

    # glyph sets & layers

    def _readLayerContents(self, validate):
        """
        Rebuild the layer contents list by checking what glyphsets
        are available on disk.

        ``validate`` will validate the layer contents.
        """
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0:
            return [(DEFAULT_LAYER_NAME, DEFAULT_GLYPHS_DIRNAME)]
        contents = self._getPlist(LAYERCONTENTS_FILENAME)
        if validate:
            valid, error = layerContentsValidator(contents, self.fs)
            if not valid:
                raise UFOLibError(error)
        return contents

    def getLayerNames(self, validate=None):
        """
        Get the ordered layer names from layercontents.plist.

        ``validate`` will validate the data, by default it is set to the
        class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        layerContents = self._readLayerContents(validate)
        layerNames = [layerName for layerName, directoryName in layerContents]
        return layerNames

    def getDefaultLayerName(self, validate=None):
        """
        Get the default layer name from layercontents.plist.

        ``validate`` will validate the data, by default it is set to the
        class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        layerContents = self._readLayerContents(validate)
        for layerName, layerDirectory in layerContents:
            if layerDirectory == DEFAULT_GLYPHS_DIRNAME:
                return layerName
        # this will already have been raised during __init__
        raise UFOLibError("The default layer is not defined in layercontents.plist.")

    def getGlyphSet(self, layerName=None, validateRead=None, validateWrite=None):
        """
        Return the GlyphSet associated with the
        glyphs directory mapped to layerName
        in the UFO. If layerName is not provided,
        the name retrieved with getDefaultLayerName
        will be used.

        ``validateRead`` will validate the read data, by default it is set to the
        class's validate value, can be overridden.
        ``validateWrite`` will validate the written data, by default it is set to the
        class's validate value, can be overridden.
        """
        from fontTools.ufoLib.glifLib import GlyphSet

        if validateRead is None:
            validateRead = self._validate
        if validateWrite is None:
            validateWrite = self._validate
        if layerName is None:
            layerName = self.getDefaultLayerName(validate=validateRead)
        directory = None
        layerContents = self._readLayerContents(validateRead)
        for storedLayerName, storedLayerDirectory in layerContents:
            if layerName == storedLayerName:
                directory = storedLayerDirectory
                break
        if directory is None:
            raise UFOLibError('No glyphs directory is mapped to "%s".' % layerName)
        try:
            glyphSubFS = self.fs.opendir(directory)
        except fs.errors.ResourceNotFound:
            raise UFOLibError(f"No '{directory}' directory for layer '{layerName}'")
        return GlyphSet(
            glyphSubFS,
            ufoFormatVersion=self._formatVersion,
            validateRead=validateRead,
            validateWrite=validateWrite,
            expectContentsFile=True,
        )

    def getCharacterMapping(self, layerName=None, validate=None):
        """
        Return a dictionary that maps unicode values (ints) to
        lists of glyph names.
        """
        if validate is None:
            validate = self._validate
        glyphSet = self.getGlyphSet(
            layerName, validateRead=validate, validateWrite=True
        )
        allUnicodes = glyphSet.getUnicodes()
        cmap = {}
        for glyphName, unicodes in allUnicodes.items():
            for code in unicodes:
                if code in cmap:
                    cmap[code].append(glyphName)
                else:
                    cmap[code] = [glyphName]
        return cmap

    # /data

    def getDataDirectoryListing(self):
        """
        Returns a list of all files in the data directory.
        The returned paths will be relative to the UFO.
        This will not list directory names, only file names.
        Thus, empty directories will be skipped.
        """
        try:
            self._dataFS = self.fs.opendir(DATA_DIRNAME)
        except fs.errors.ResourceNotFound:
            return []
        except fs.errors.DirectoryExpected:
            raise UFOLibError('The UFO contains a "data" file instead of a directory.')
        try:
            # fs Walker.files method returns "absolute" paths (in terms of the
            # root of the 'data' SubFS), so we strip the leading '/' to make
            # them relative
            return [p.lstrip("/") for p in self._dataFS.walk.files()]
        except fs.errors.ResourceError:
            return []

    def getImageDirectoryListing(self, validate=None):
        """
        Returns a list of all image file names in
        the images directory. Each of the images will
        have been verified to have the PNG signature.

        ``validate`` will validate the data, by default it is set to the
        class's validate value, can be overridden.
        """
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0:
            return []
        if validate is None:
            validate = self._validate
        try:
            self._imagesFS = imagesFS = self.fs.opendir(IMAGES_DIRNAME)
        except fs.errors.ResourceNotFound:
            return []
        except fs.errors.DirectoryExpected:
            raise UFOLibError(
                'The UFO contains an "images" file instead of a directory.'
            )
        result = []
        for path in imagesFS.scandir("/"):
            if path.is_dir:
                # silently skip this as version control
                # systems often have hidden directories
                continue
            if validate:
                with imagesFS.openbin(path.name) as fp:
                    valid, error = pngValidator(fileObj=fp)
                if valid:
                    result.append(path.name)
            else:
                result.append(path.name)
        return result

    def readData(self, fileName):
        """
        Return bytes for the file named 'fileName' inside the 'data/' directory.
        """
        fileName = fsdecode(fileName)
        try:
            try:
                dataFS = self._dataFS
            except AttributeError:
                # in case readData is called before getDataDirectoryListing
                dataFS = self.fs.opendir(DATA_DIRNAME)
            data = dataFS.readbytes(fileName)
        except fs.errors.ResourceNotFound:
            raise UFOLibError(f"No data file named '{fileName}' on {self.fs}")
        return data

    def readImage(self, fileName, validate=None):
        """
        Return image data for the file named fileName.

        ``validate`` will validate the data, by default it is set to the
        class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0:
            raise UFOLibError(
                f"Reading images is not allowed in UFO {self._formatVersion.major}."
            )
        fileName = fsdecode(fileName)
        try:
            try:
                imagesFS = self._imagesFS
            except AttributeError:
                # in case readImage is called before getImageDirectoryListing
                imagesFS = self.fs.opendir(IMAGES_DIRNAME)
            data = imagesFS.readbytes(fileName)
        except fs.errors.ResourceNotFound:
            raise UFOLibError(f"No image file named '{fileName}' on {self.fs}")
        if validate:
            valid, error = pngValidator(data=data)
            if not valid:
                raise UFOLibError(error)
        return data

    def close(self):
        if self._shouldClose:
            self.fs.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


# ----------
# UFO Writer
# ----------


class UFOWriter(UFOReader):
    """Write the various components of a .ufo.

    Attributes:
        path: An :class:`os.PathLike` object pointing to the .ufo.
        formatVersion: the UFO format version as a tuple of integers (major, minor),
            or as a single integer for the major digit only (minor is implied to be 0).
            By default, the latest formatVersion will be used; currently it is 3.0,
            which is equivalent to formatVersion=(3, 0).
        fileCreator: The creator of the .ufo file. Defaults to
            `com.github.fonttools.ufoLib`.
        structure: The internal structure of the .ufo file: either `ZIP` or `PACKAGE`.
        validate: A boolean indicating if the data read should be validated. Defaults
            to `True`.

    By default, the written data will be validated before writing. Set ``validate`` to
    ``False`` if you do not want to validate the data. Validation can also be overriden
    on a per-method level if desired.

    Raises:
        UnsupportedUFOFormat: An exception indicating that the requested UFO
            formatVersion is not supported.
    """

    def __init__(
        self,
        path,
        formatVersion=None,
        fileCreator="com.github.fonttools.ufoLib",
        structure=None,
        validate=True,
    ):
        try:
            formatVersion = UFOFormatVersion(formatVersion)
        except ValueError as e:
            from fontTools.ufoLib.errors import UnsupportedUFOFormat

            raise UnsupportedUFOFormat(
                f"Unsupported UFO format: {formatVersion!r}"
            ) from e

        if hasattr(path, "__fspath__"):  # support os.PathLike objects
            path = path.__fspath__()

        if isinstance(path, str):
            # normalize path by removing trailing or double slashes
            path = os.path.normpath(path)
            havePreviousFile = os.path.exists(path)
            if havePreviousFile:
                # ensure we use the same structure as the destination
                existingStructure = _sniffFileStructure(path)
                if structure is not None:
                    try:
                        structure = UFOFileStructure(structure)
                    except ValueError:
                        raise UFOLibError(
                            "Invalid or unsupported structure: '%s'" % structure
                        )
                    if structure is not existingStructure:
                        raise UFOLibError(
                            "A UFO with a different structure (%s) already exists "
                            "at the given path: '%s'" % (existingStructure, path)
                        )
                else:
                    structure = existingStructure
            else:
                # if not exists, default to 'package' structure
                if structure is None:
                    structure = UFOFileStructure.PACKAGE
                dirName = os.path.dirname(path)
                if dirName and not os.path.isdir(dirName):
                    raise UFOLibError(
                        "Cannot write to '%s': directory does not exist" % path
                    )
            if structure is UFOFileStructure.ZIP:
                if havePreviousFile:
                    # we can't write a zip in-place, so we have to copy its
                    # contents to a temporary location and work from there, then
                    # upon closing UFOWriter we create the final zip file
                    parentFS = fs.tempfs.TempFS()
                    with fs.zipfs.ZipFS(path, encoding="utf-8") as origFS:
                        fs.copy.copy_fs(origFS, parentFS)
                    # if output path is an existing zip, we require that it contains
                    # one, and only one, root directory (with arbitrary name), in turn
                    # containing all the existing UFO contents
                    rootDirs = [
                        p.name
                        for p in parentFS.scandir("/")
                        # exclude macOS metadata contained in zip file
                        if p.is_dir and p.name != "__MACOSX"
                    ]
                    if len(rootDirs) != 1:
                        raise UFOLibError(
                            "Expected exactly 1 root directory, found %d"
                            % len(rootDirs)
                        )
                    else:
                        # 'ClosingSubFS' ensures that the parent filesystem is closed
                        # when its root subdirectory is closed
                        self.fs = parentFS.opendir(
                            rootDirs[0], factory=fs.subfs.ClosingSubFS
                        )
                else:
                    # if the output zip file didn't exist, we create the root folder;
                    # we name it the same as input 'path', but with '.ufo' extension
                    rootDir = os.path.splitext(os.path.basename(path))[0] + ".ufo"
                    parentFS = fs.zipfs.ZipFS(path, write=True, encoding="utf-8")
                    parentFS.makedir(rootDir)
                    self.fs = parentFS.opendir(rootDir, factory=fs.subfs.ClosingSubFS)
            else:
                self.fs = fs.osfs.OSFS(path, create=True)
            self._fileStructure = structure
            self._havePreviousFile = havePreviousFile
            self._shouldClose = True
        elif isinstance(path, fs.base.FS):
            filesystem = path
            try:
                filesystem.check()
            except fs.errors.FilesystemClosed:
                raise UFOLibError("the filesystem '%s' is closed" % path)
            else:
                self.fs = filesystem
            try:
                path = filesystem.getsyspath("/")
            except fs.errors.NoSysPath:
                # network or in-memory FS may not map to the local one
                path = str(filesystem)
            # if passed an FS object, always use 'package' structure
            if structure and structure is not UFOFileStructure.PACKAGE:
                import warnings

                warnings.warn(
                    "The 'structure' argument is not used when input is an FS object",
                    UserWarning,
                    stacklevel=2,
                )
            self._fileStructure = UFOFileStructure.PACKAGE
            # if FS contains a "metainfo.plist", we consider it non-empty
            self._havePreviousFile = filesystem.exists(METAINFO_FILENAME)
            # the user is responsible for closing the FS object
            self._shouldClose = False
        else:
            raise TypeError(
                "Expected a path string or fs object, found %s" % type(path).__name__
            )

        # establish some basic stuff
        self._path = fsdecode(path)
        self._formatVersion = formatVersion
        self._fileCreator = fileCreator
        self._downConversionKerningData = None
        self._validate = validate
        # if the file already exists, get the format version.
        # this will be needed for up and down conversion.
        previousFormatVersion = None
        if self._havePreviousFile:
            metaInfo = self._readMetaInfo(validate=validate)
            previousFormatVersion = metaInfo["formatVersionTuple"]
            # catch down conversion
            if previousFormatVersion > formatVersion:
                from fontTools.ufoLib.errors import UnsupportedUFOFormat

                raise UnsupportedUFOFormat(
                    "The UFO located at this path is a higher version "
                    f"({previousFormatVersion}) than the version ({formatVersion}) "
                    "that is trying to be written. This is not supported."
                )
        # handle the layer contents
        self.layerContents = {}
        if previousFormatVersion is not None and previousFormatVersion.major >= 3:
            # already exists
            self.layerContents = OrderedDict(self._readLayerContents(validate))
        else:
            # previous < 3
            # imply the layer contents
            if self.fs.exists(DEFAULT_GLYPHS_DIRNAME):
                self.layerContents = {DEFAULT_LAYER_NAME: DEFAULT_GLYPHS_DIRNAME}
        # write the new metainfo
        self._writeMetaInfo()

    # properties

    def _get_fileCreator(self):
        return self._fileCreator

    fileCreator = property(
        _get_fileCreator,
        doc="The file creator of the UFO. This is set into metainfo.plist during __init__.",
    )

    # support methods for file system interaction

    def copyFromReader(self, reader, sourcePath, destPath):
        """
        Copy the sourcePath in the provided UFOReader to destPath
        in this writer. The paths must be relative. This works with
        both individual files and directories.
        """
        if not isinstance(reader, UFOReader):
            raise UFOLibError("The reader must be an instance of UFOReader.")
        sourcePath = fsdecode(sourcePath)
        destPath = fsdecode(destPath)
        if not reader.fs.exists(sourcePath):
            raise UFOLibError(
                'The reader does not have data located at "%s".' % sourcePath
            )
        if self.fs.exists(destPath):
            raise UFOLibError('A file named "%s" already exists.' % destPath)
        # create the destination directory if it doesn't exist
        self.fs.makedirs(fs.path.dirname(destPath), recreate=True)
        if reader.fs.isdir(sourcePath):
            fs.copy.copy_dir(reader.fs, sourcePath, self.fs, destPath)
        else:
            fs.copy.copy_file(reader.fs, sourcePath, self.fs, destPath)

    def writeBytesToPath(self, path, data):
        """
        Write bytes to a path relative to the UFO filesystem's root.
        If writing to an existing UFO, check to see if data matches the data
        that is already in the file at path; if so, the file is not rewritten
        so that the modification date is preserved.
        If needed, the directory tree for the given path will be built.
        """
        path = fsdecode(path)
        if self._havePreviousFile:
            if self.fs.isfile(path) and data == self.fs.readbytes(path):
                return
        try:
            self.fs.writebytes(path, data)
        except fs.errors.FileExpected:
            raise UFOLibError("A directory exists at '%s'" % path)
        except fs.errors.ResourceNotFound:
            self.fs.makedirs(fs.path.dirname(path), recreate=True)
            self.fs.writebytes(path, data)

    def getFileObjectForPath(self, path, mode="w", encoding=None):
        """
        Returns a file (or file-like) object for the
        file at the given path. The path must be relative
        to the UFO path. Returns None if the file does
        not exist and the mode is "r" or "rb.
        An encoding may be passed if the file is opened in text mode.

        Note: The caller is responsible for closing the open file.
        """
        path = fsdecode(path)
        try:
            return self.fs.open(path, mode=mode, encoding=encoding)
        except fs.errors.ResourceNotFound as e:
            m = mode[0]
            if m == "r":
                # XXX I think we should just let it raise. The docstring,
                # however, says that this returns None if mode is 'r'
                return None
            elif m == "w" or m == "a" or m == "x":
                self.fs.makedirs(fs.path.dirname(path), recreate=True)
                return self.fs.open(path, mode=mode, encoding=encoding)
        except fs.errors.ResourceError as e:
            return UFOLibError(f"unable to open '{path}' on {self.fs}: {e}")

    def removePath(self, path, force=False, removeEmptyParents=True):
        """
        Remove the file (or directory) at path. The path
        must be relative to the UFO.
        Raises UFOLibError if the path doesn't exist.
        If force=True, ignore non-existent paths.
        If the directory where 'path' is located becomes empty, it will
        be automatically removed, unless 'removeEmptyParents' is False.
        """
        path = fsdecode(path)
        try:
            self.fs.remove(path)
        except fs.errors.FileExpected:
            self.fs.removetree(path)
        except fs.errors.ResourceNotFound:
            if not force:
                raise UFOLibError(f"'{path}' does not exist on {self.fs}")
        if removeEmptyParents:
            parent = fs.path.dirname(path)
            if parent:
                fs.tools.remove_empty(self.fs, parent)

    # alias kept for backward compatibility with old API
    removeFileForPath = removePath

    # UFO mod time

    def setModificationTime(self):
        """
        Set the UFO modification time to the current time.
        This is never called automatically. It is up to the
        caller to call this when finished working on the UFO.
        """
        path = self._path
        if path is not None and os.path.exists(path):
            try:
                # this may fail on some filesystems (e.g. SMB servers)
                os.utime(path, None)
            except OSError as e:
                logger.warning("Failed to set modified time: %s", e)

    # metainfo.plist

    def _writeMetaInfo(self):
        metaInfo = dict(
            creator=self._fileCreator,
            formatVersion=self._formatVersion.major,
        )
        if self._formatVersion.minor != 0:
            metaInfo["formatVersionMinor"] = self._formatVersion.minor
        self._writePlist(METAINFO_FILENAME, metaInfo)

    # groups.plist

    def setKerningGroupConversionRenameMaps(self, maps):
        """
        Set maps defining the renaming that should be done
        when writing groups and kerning in UFO 1 and UFO 2.
        This will effectively undo the conversion done when
        UFOReader reads this data. The dictionary should have
        this form::

                {
                        "side1" : {"group name to use when writing" : "group name in data"},
                        "side2" : {"group name to use when writing" : "group name in data"}
                }

        This is the same form returned by UFOReader's
        getKerningGroupConversionRenameMaps method.
        """
        if self._formatVersion >= UFOFormatVersion.FORMAT_3_0:
            return  # XXX raise an error here
        # flip the dictionaries
        remap = {}
        for side in ("side1", "side2"):
            for writeName, dataName in list(maps[side].items()):
                remap[dataName] = writeName
        self._downConversionKerningData = dict(groupRenameMap=remap)

    def writeGroups(self, groups, validate=None):
        """
        Write groups.plist. This method requires a
        dict of glyph groups as an argument.

        ``validate`` will validate the data, by default it is set to the
        class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        # validate the data structure
        if validate:
            valid, message = groupsValidator(groups)
            if not valid:
                raise UFOLibError(message)
        # down convert
        if (
            self._formatVersion < UFOFormatVersion.FORMAT_3_0
            and self._downConversionKerningData is not None
        ):
            remap = self._downConversionKerningData["groupRenameMap"]
            remappedGroups = {}
            # there are some edge cases here that are ignored:
            # 1. if a group is being renamed to a name that
            #    already exists, the existing group is always
            #    overwritten. (this is why there are two loops
            #    below.) there doesn't seem to be a logical
            #    solution to groups mismatching and overwriting
            #    with the specifiecd group seems like a better
            #    solution than throwing an error.
            # 2. if side 1 and side 2 groups are being renamed
            #    to the same group name there is no check to
            #    ensure that the contents are identical. that
            #    is left up to the caller.
            for name, contents in list(groups.items()):
                if name in remap:
                    continue
                remappedGroups[name] = contents
            for name, contents in list(groups.items()):
                if name not in remap:
                    continue
                name = remap[name]
                remappedGroups[name] = contents
            groups = remappedGroups
        # pack and write
        groupsNew = {}
        for key, value in groups.items():
            groupsNew[key] = list(value)
        if groupsNew:
            self._writePlist(GROUPS_FILENAME, groupsNew)
        elif self._havePreviousFile:
            self.removePath(GROUPS_FILENAME, force=True, removeEmptyParents=False)

    # fontinfo.plist

    def writeInfo(self, info, validate=None):
        """
        Write info.plist. This method requires an object
        that supports getting attributes that follow the
        fontinfo.plist version 2 specification. Attributes
        will be taken from the given object and written
        into the file.

        ``validate`` will validate the data, by default it is set to the
        class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        # gather version 3 data
        infoData = {}
        for attr in list(fontInfoAttributesVersion3ValueData.keys()):
            if hasattr(info, attr):
                try:
                    value = getattr(info, attr)
                except AttributeError:
                    raise UFOLibError(
                        "The supplied info object does not support getting a necessary attribute (%s)."
                        % attr
                    )
                if value is None:
                    continue
                infoData[attr] = value
        # down convert data if necessary and validate
        if self._formatVersion == UFOFormatVersion.FORMAT_3_0:
            if validate:
                infoData = validateInfoVersion3Data(infoData)
        elif self._formatVersion == UFOFormatVersion.FORMAT_2_0:
            infoData = _convertFontInfoDataVersion3ToVersion2(infoData)
            if validate:
                infoData = validateInfoVersion2Data(infoData)
        elif self._formatVersion == UFOFormatVersion.FORMAT_1_0:
            infoData = _convertFontInfoDataVersion3ToVersion2(infoData)
            if validate:
                infoData = validateInfoVersion2Data(infoData)
            infoData = _convertFontInfoDataVersion2ToVersion1(infoData)
        # write file if there is anything to write
        if infoData:
            self._writePlist(FONTINFO_FILENAME, infoData)

    # kerning.plist

    def writeKerning(self, kerning, validate=None):
        """
        Write kerning.plist. This method requires a
        dict of kerning pairs as an argument.

        This performs basic structural validation of the kerning,
        but it does not check for compliance with the spec in
        regards to conflicting pairs. The assumption is that the
        kerning data being passed is standards compliant.

        ``validate`` will validate the data, by default it is set to the
        class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        # validate the data structure
        if validate:
            invalidFormatMessage = "The kerning is not properly formatted."
            if not isDictEnough(kerning):
                raise UFOLibError(invalidFormatMessage)
            for pair, value in list(kerning.items()):
                if not isinstance(pair, (list, tuple)):
                    raise UFOLibError(invalidFormatMessage)
                if not len(pair) == 2:
                    raise UFOLibError(invalidFormatMessage)
                if not isinstance(pair[0], str):
                    raise UFOLibError(invalidFormatMessage)
                if not isinstance(pair[1], str):
                    raise UFOLibError(invalidFormatMessage)
                if not isinstance(value, numberTypes):
                    raise UFOLibError(invalidFormatMessage)
        # down convert
        if (
            self._formatVersion < UFOFormatVersion.FORMAT_3_0
            and self._downConversionKerningData is not None
        ):
            remap = self._downConversionKerningData["groupRenameMap"]
            remappedKerning = {}
            for (side1, side2), value in list(kerning.items()):
                side1 = remap.get(side1, side1)
                side2 = remap.get(side2, side2)
                remappedKerning[side1, side2] = value
            kerning = remappedKerning
        # pack and write
        kerningDict = {}
        for left, right in kerning.keys():
            value = kerning[left, right]
            if left not in kerningDict:
                kerningDict[left] = {}
            kerningDict[left][right] = value
        if kerningDict:
            self._writePlist(KERNING_FILENAME, kerningDict)
        elif self._havePreviousFile:
            self.removePath(KERNING_FILENAME, force=True, removeEmptyParents=False)

    # lib.plist

    def writeLib(self, libDict, validate=None):
        """
        Write lib.plist. This method requires a
        lib dict as an argument.

        ``validate`` will validate the data, by default it is set to the
        class's validate value, can be overridden.
        """
        if validate is None:
            validate = self._validate
        if validate:
            valid, message = fontLibValidator(libDict)
            if not valid:
                raise UFOLibError(message)
        if libDict:
            self._writePlist(LIB_FILENAME, libDict)
        elif self._havePreviousFile:
            self.removePath(LIB_FILENAME, force=True, removeEmptyParents=False)

    # features.fea

    def writeFeatures(self, features, validate=None):
        """
        Write features.fea. This method requires a
        features string as an argument.
        """
        if validate is None:
            validate = self._validate
        if self._formatVersion == UFOFormatVersion.FORMAT_1_0:
            raise UFOLibError("features.fea is not allowed in UFO Format Version 1.")
        if validate:
            if not isinstance(features, str):
                raise UFOLibError("The features are not text.")
        if features:
            self.writeBytesToPath(FEATURES_FILENAME, features.encode("utf8"))
        elif self._havePreviousFile:
            self.removePath(FEATURES_FILENAME, force=True, removeEmptyParents=False)

    # glyph sets & layers

    def writeLayerContents(self, layerOrder=None, validate=None):
        """
        Write the layercontents.plist file. This method  *must* be called
        after all glyph sets have been written.
        """
        if validate is None:
            validate = self._validate
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0:
            return
        if layerOrder is not None:
            newOrder = []
            for layerName in layerOrder:
                if layerName is None:
                    layerName = DEFAULT_LAYER_NAME
                newOrder.append(layerName)
            layerOrder = newOrder
        else:
            layerOrder = list(self.layerContents.keys())
        if validate and set(layerOrder) != set(self.layerContents.keys()):
            raise UFOLibError(
                "The layer order content does not match the glyph sets that have been created."
            )
        layerContents = [
            (layerName, self.layerContents[layerName]) for layerName in layerOrder
        ]
        self._writePlist(LAYERCONTENTS_FILENAME, layerContents)

    def _findDirectoryForLayerName(self, layerName):
        foundDirectory = None
        for existingLayerName, directoryName in list(self.layerContents.items()):
            if layerName is None and directoryName == DEFAULT_GLYPHS_DIRNAME:
                foundDirectory = directoryName
                break
            elif existingLayerName == layerName:
                foundDirectory = directoryName
                break
        if not foundDirectory:
            raise UFOLibError(
                "Could not locate a glyph set directory for the layer named %s."
                % layerName
            )
        return foundDirectory

    def getGlyphSet(
        self,
        layerName=None,
        defaultLayer=True,
        glyphNameToFileNameFunc=None,
        validateRead=None,
        validateWrite=None,
        expectContentsFile=False,
    ):
        """
        Return the GlyphSet object associated with the
        appropriate glyph directory in the .ufo.
        If layerName is None, the default glyph set
        will be used. The defaultLayer flag indictes
        that the layer should be saved into the default
        glyphs directory.

        ``validateRead`` will validate the read data, by default it is set to the
        class's validate value, can be overridden.
        ``validateWrte`` will validate the written data, by default it is set to the
        class's validate value, can be overridden.
        ``expectContentsFile`` will raise a GlifLibError if a contents.plist file is
        not found on the glyph set file system. This should be set to ``True`` if you
        are reading an existing UFO and ``False`` if you use ``getGlyphSet`` to create
        a fresh	glyph set.
        """
        if validateRead is None:
            validateRead = self._validate
        if validateWrite is None:
            validateWrite = self._validate
        # only default can be written in < 3
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0 and (
            not defaultLayer or layerName is not None
        ):
            raise UFOLibError(
                f"Only the default layer can be writen in UFO {self._formatVersion.major}."
            )
        # locate a layer name when None has been given
        if layerName is None and defaultLayer:
            for existingLayerName, directory in self.layerContents.items():
                if directory == DEFAULT_GLYPHS_DIRNAME:
                    layerName = existingLayerName
            if layerName is None:
                layerName = DEFAULT_LAYER_NAME
        elif layerName is None and not defaultLayer:
            raise UFOLibError("A layer name must be provided for non-default layers.")
        # move along to format specific writing
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0:
            return self._getDefaultGlyphSet(
                validateRead,
                validateWrite,
                glyphNameToFileNameFunc=glyphNameToFileNameFunc,
                expectContentsFile=expectContentsFile,
            )
        elif self._formatVersion.major == UFOFormatVersion.FORMAT_3_0.major:
            return self._getGlyphSetFormatVersion3(
                validateRead,
                validateWrite,
                layerName=layerName,
                defaultLayer=defaultLayer,
                glyphNameToFileNameFunc=glyphNameToFileNameFunc,
                expectContentsFile=expectContentsFile,
            )
        else:
            raise NotImplementedError(self._formatVersion)

    def _getDefaultGlyphSet(
        self,
        validateRead,
        validateWrite,
        glyphNameToFileNameFunc=None,
        expectContentsFile=False,
    ):
        from fontTools.ufoLib.glifLib import GlyphSet

        glyphSubFS = self.fs.makedir(DEFAULT_GLYPHS_DIRNAME, recreate=True)
        return GlyphSet(
            glyphSubFS,
            glyphNameToFileNameFunc=glyphNameToFileNameFunc,
            ufoFormatVersion=self._formatVersion,
            validateRead=validateRead,
            validateWrite=validateWrite,
            expectContentsFile=expectContentsFile,
        )

    def _getGlyphSetFormatVersion3(
        self,
        validateRead,
        validateWrite,
        layerName=None,
        defaultLayer=True,
        glyphNameToFileNameFunc=None,
        expectContentsFile=False,
    ):
        from fontTools.ufoLib.glifLib import GlyphSet

        # if the default flag is on, make sure that the default in the file
        # matches the default being written. also make sure that this layer
        # name is not already linked to a non-default layer.
        if defaultLayer:
            for existingLayerName, directory in self.layerContents.items():
                if directory == DEFAULT_GLYPHS_DIRNAME:
                    if existingLayerName != layerName:
                        raise UFOLibError(
                            "Another layer ('%s') is already mapped to the default directory."
                            % existingLayerName
                        )
                elif existingLayerName == layerName:
                    raise UFOLibError(
                        "The layer name is already mapped to a non-default layer."
                    )
        # get an existing directory name
        if layerName in self.layerContents:
            directory = self.layerContents[layerName]
        # get a  new directory name
        else:
            if defaultLayer:
                directory = DEFAULT_GLYPHS_DIRNAME
            else:
                # not caching this could be slightly expensive,
                # but caching it will be cumbersome
                existing = {d.lower() for d in self.layerContents.values()}
                directory = userNameToFileName(
                    layerName, existing=existing, prefix="glyphs."
                )
        # make the directory
        glyphSubFS = self.fs.makedir(directory, recreate=True)
        # store the mapping
        self.layerContents[layerName] = directory
        # load the glyph set
        return GlyphSet(
            glyphSubFS,
            glyphNameToFileNameFunc=glyphNameToFileNameFunc,
            ufoFormatVersion=self._formatVersion,
            validateRead=validateRead,
            validateWrite=validateWrite,
            expectContentsFile=expectContentsFile,
        )

    def renameGlyphSet(self, layerName, newLayerName, defaultLayer=False):
        """
        Rename a glyph set.

        Note: if a GlyphSet object has already been retrieved for
        layerName, it is up to the caller to inform that object that
        the directory it represents has changed.
        """
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0:
            # ignore renaming glyph sets for UFO1 UFO2
            # just write the data from the default layer
            return
        # the new and old names can be the same
        # as long as the default is being switched
        if layerName == newLayerName:
            # if the default is off and the layer is already not the default, skip
            if (
                self.layerContents[layerName] != DEFAULT_GLYPHS_DIRNAME
                and not defaultLayer
            ):
                return
            # if the default is on and the layer is already the default, skip
            if self.layerContents[layerName] == DEFAULT_GLYPHS_DIRNAME and defaultLayer:
                return
        else:
            # make sure the new layer name doesn't already exist
            if newLayerName is None:
                newLayerName = DEFAULT_LAYER_NAME
            if newLayerName in self.layerContents:
                raise UFOLibError("A layer named %s already exists." % newLayerName)
            # make sure the default layer doesn't already exist
            if defaultLayer and DEFAULT_GLYPHS_DIRNAME in self.layerContents.values():
                raise UFOLibError("A default layer already exists.")
        # get the paths
        oldDirectory = self._findDirectoryForLayerName(layerName)
        if defaultLayer:
            newDirectory = DEFAULT_GLYPHS_DIRNAME
        else:
            existing = {name.lower() for name in self.layerContents.values()}
            newDirectory = userNameToFileName(
                newLayerName, existing=existing, prefix="glyphs."
            )
        # update the internal mapping
        del self.layerContents[layerName]
        self.layerContents[newLayerName] = newDirectory
        # do the file system copy
        self.fs.movedir(oldDirectory, newDirectory, create=True)

    def deleteGlyphSet(self, layerName):
        """
        Remove the glyph set matching layerName.
        """
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0:
            # ignore deleting glyph sets for UFO1 UFO2 as there are no layers
            # just write the data from the default layer
            return
        foundDirectory = self._findDirectoryForLayerName(layerName)
        self.removePath(foundDirectory, removeEmptyParents=False)
        del self.layerContents[layerName]

    def writeData(self, fileName, data):
        """
        Write data to fileName in the 'data' directory.
        The data must be a bytes string.
        """
        self.writeBytesToPath(f"{DATA_DIRNAME}/{fsdecode(fileName)}", data)

    def removeData(self, fileName):
        """
        Remove the file named fileName from the data directory.
        """
        self.removePath(f"{DATA_DIRNAME}/{fsdecode(fileName)}")

    # /images

    def writeImage(self, fileName, data, validate=None):
        """
        Write data to fileName in the images directory.
        The data must be a valid PNG.
        """
        if validate is None:
            validate = self._validate
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0:
            raise UFOLibError(
                f"Images are not allowed in UFO {self._formatVersion.major}."
            )
        fileName = fsdecode(fileName)
        if validate:
            valid, error = pngValidator(data=data)
            if not valid:
                raise UFOLibError(error)
        self.writeBytesToPath(f"{IMAGES_DIRNAME}/{fileName}", data)

    def removeImage(self, fileName, validate=None):  # XXX remove unused 'validate'?
        """
        Remove the file named fileName from the
        images directory.
        """
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0:
            raise UFOLibError(
                f"Images are not allowed in UFO {self._formatVersion.major}."
            )
        self.removePath(f"{IMAGES_DIRNAME}/{fsdecode(fileName)}")

    def copyImageFromReader(self, reader, sourceFileName, destFileName, validate=None):
        """
        Copy the sourceFileName in the provided UFOReader to destFileName
        in this writer. This uses the most memory efficient method possible
        for copying the data possible.
        """
        if validate is None:
            validate = self._validate
        if self._formatVersion < UFOFormatVersion.FORMAT_3_0:
            raise UFOLibError(
                f"Images are not allowed in UFO {self._formatVersion.major}."
            )
        sourcePath = f"{IMAGES_DIRNAME}/{fsdecode(sourceFileName)}"
        destPath = f"{IMAGES_DIRNAME}/{fsdecode(destFileName)}"
        self.copyFromReader(reader, sourcePath, destPath)

    def close(self):
        if self._havePreviousFile and self._fileStructure is UFOFileStructure.ZIP:
            # if we are updating an existing zip file, we can now compress the
            # contents of the temporary filesystem in the destination path
            rootDir = os.path.splitext(os.path.basename(self._path))[0] + ".ufo"
            with fs.zipfs.ZipFS(self._path, write=True, encoding="utf-8") as destFS:
                fs.copy.copy_fs(self.fs, destFS.makedir(rootDir))
        super().close()


# just an alias, makes it more explicit
UFOReaderWriter = UFOWriter


# ----------------
# Helper Functions
# ----------------


def _sniffFileStructure(ufo_path):
    """Return UFOFileStructure.ZIP if the UFO at path 'ufo_path' (str)
    is a zip file, else return UFOFileStructure.PACKAGE if 'ufo_path' is a
    directory.
    Raise UFOLibError if it is a file with unknown structure, or if the path
    does not exist.
    """
    if zipfile.is_zipfile(ufo_path):
        return UFOFileStructure.ZIP
    elif os.path.isdir(ufo_path):
        return UFOFileStructure.PACKAGE
    elif os.path.isfile(ufo_path):
        raise UFOLibError(
            "The specified UFO does not have a known structure: '%s'" % ufo_path
        )
    else:
        raise UFOLibError("No such file or directory: '%s'" % ufo_path)


def makeUFOPath(path):
    """
    Return a .ufo pathname.

    >>> makeUFOPath("directory/something.ext") == (
    ... 	os.path.join('directory', 'something.ufo'))
    True
    >>> makeUFOPath("directory/something.another.thing.ext") == (
    ... 	os.path.join('directory', 'something.another.thing.ufo'))
    True
    """
    dir, name = os.path.split(path)
    name = ".".join([".".join(name.split(".")[:-1]), "ufo"])
    return os.path.join(dir, name)


# ----------------------
# fontinfo.plist Support
# ----------------------

# Version Validators

# There is no version 1 validator and there shouldn't be.
# The version 1 spec was very loose and there were numerous
# cases of invalid values.


def validateFontInfoVersion2ValueForAttribute(attr, value):
    """
    This performs very basic validation of the value for attribute
    following the UFO 2 fontinfo.plist specification. The results
    of this should not be interpretted as *correct* for the font
    that they are part of. This merely indicates that the value
    is of the proper type and, where the specification defines
    a set range of possible values for an attribute, that the
    value is in the accepted range.
    """
    dataValidationDict = fontInfoAttributesVersion2ValueData[attr]
    valueType = dataValidationDict.get("type")
    validator = dataValidationDict.get("valueValidator")
    valueOptions = dataValidationDict.get("valueOptions")
    # have specific options for the validator
    if valueOptions is not None:
        isValidValue = validator(value, valueOptions)
    # no specific options
    else:
        if validator == genericTypeValidator:
            isValidValue = validator(value, valueType)
        else:
            isValidValue = validator(value)
    return isValidValue


def validateInfoVersion2Data(infoData):
    """
    This performs very basic validation of the value for infoData
    following the UFO 2 fontinfo.plist specification. The results
    of this should not be interpretted as *correct* for the font
    that they are part of. This merely indicates that the values
    are of the proper type and, where the specification defines
    a set range of possible values for an attribute, that the
    value is in the accepted range.
    """
    validInfoData = {}
    for attr, value in list(infoData.items()):
        isValidValue = validateFontInfoVersion2ValueForAttribute(attr, value)
        if not isValidValue:
            raise UFOLibError(f"Invalid value for attribute {attr} ({value!r}).")
        else:
            validInfoData[attr] = value
    return validInfoData


def validateFontInfoVersion3ValueForAttribute(attr, value):
    """
    This performs very basic validation of the value for attribute
    following the UFO 3 fontinfo.plist specification. The results
    of this should not be interpretted as *correct* for the font
    that they are part of. This merely indicates that the value
    is of the proper type and, where the specification defines
    a set range of possible values for an attribute, that the
    value is in the accepted range.
    """
    dataValidationDict = fontInfoAttributesVersion3ValueData[attr]
    valueType = dataValidationDict.get("type")
    validator = dataValidationDict.get("valueValidator")
    valueOptions = dataValidationDict.get("valueOptions")
    # have specific options for the validator
    if valueOptions is not None:
        isValidValue = validator(value, valueOptions)
    # no specific options
    else:
        if validator == genericTypeValidator:
            isValidValue = validator(value, valueType)
        else:
            isValidValue = validator(value)
    return isValidValue


def validateInfoVersion3Data(infoData):
    """
    This performs very basic validation of the value for infoData
    following the UFO 3 fontinfo.plist specification. The results
    of this should not be interpretted as *correct* for the font
    that they are part of. This merely indicates that the values
    are of the proper type and, where the specification defines
    a set range of possible values for an attribute, that the
    value is in the accepted range.
    """
    validInfoData = {}
    for attr, value in list(infoData.items()):
        isValidValue = validateFontInfoVersion3ValueForAttribute(attr, value)
        if not isValidValue:
            raise UFOLibError(f"Invalid value for attribute {attr} ({value!r}).")
        else:
            validInfoData[attr] = value
    return validInfoData


# Value Options

fontInfoOpenTypeHeadFlagsOptions = list(range(0, 15))
fontInfoOpenTypeOS2SelectionOptions = [1, 2, 3, 4, 7, 8, 9]
fontInfoOpenTypeOS2UnicodeRangesOptions = list(range(0, 128))
fontInfoOpenTypeOS2CodePageRangesOptions = list(range(0, 64))
fontInfoOpenTypeOS2TypeOptions = [0, 1, 2, 3, 8, 9]

# Version Attribute Definitions
# This defines the attributes, types and, in some
# cases the possible values, that can exist is
# fontinfo.plist.

fontInfoAttributesVersion1 = {
    "familyName",
    "styleName",
    "fullName",
    "fontName",
    "menuName",
    "fontStyle",
    "note",
    "versionMajor",
    "versionMinor",
    "year",
    "copyright",
    "notice",
    "trademark",
    "license",
    "licenseURL",
    "createdBy",
    "designer",
    "designerURL",
    "vendorURL",
    "unitsPerEm",
    "ascender",
    "descender",
    "capHeight",
    "xHeight",
    "defaultWidth",
    "slantAngle",
    "italicAngle",
    "widthName",
    "weightName",
    "weightValue",
    "fondName",
    "otFamilyName",
    "otStyleName",
    "otMacName",
    "msCharSet",
    "fondID",
    "uniqueID",
    "ttVendor",
    "ttUniqueID",
    "ttVersion",
}

fontInfoAttributesVersion2ValueData = {
    "familyName": dict(type=str),
    "styleName": dict(type=str),
    "styleMapFamilyName": dict(type=str),
    "styleMapStyleName": dict(
        type=str, valueValidator=fontInfoStyleMapStyleNameValidator
    ),
    "versionMajor": dict(type=int),
    "versionMinor": dict(type=int),
    "year": dict(type=int),
    "copyright": dict(type=str),
    "trademark": dict(type=str),
    "unitsPerEm": dict(type=(int, float)),
    "descender": dict(type=(int, float)),
    "xHeight": dict(type=(int, float)),
    "capHeight": dict(type=(int, float)),
    "ascender": dict(type=(int, float)),
    "italicAngle": dict(type=(float, int)),
    "note": dict(type=str),
    "openTypeHeadCreated": dict(
        type=str, valueValidator=fontInfoOpenTypeHeadCreatedValidator
    ),
    "openTypeHeadLowestRecPPEM": dict(type=(int, float)),
    "openTypeHeadFlags": dict(
        type="integerList",
        valueValidator=genericIntListValidator,
        valueOptions=fontInfoOpenTypeHeadFlagsOptions,
    ),
    "openTypeHheaAscender": dict(type=(int, float)),
    "openTypeHheaDescender": dict(type=(int, float)),
    "openTypeHheaLineGap": dict(type=(int, float)),
    "openTypeHheaCaretSlopeRise": dict(type=int),
    "openTypeHheaCaretSlopeRun": dict(type=int),
    "openTypeHheaCaretOffset": dict(type=(int, float)),
    "openTypeNameDesigner": dict(type=str),
    "openTypeNameDesignerURL": dict(type=str),
    "openTypeNameManufacturer": dict(type=str),
    "openTypeNameManufacturerURL": dict(type=str),
    "openTypeNameLicense": dict(type=str),
    "openTypeNameLicenseURL": dict(type=str),
    "openTypeNameVersion": dict(type=str),
    "openTypeNameUniqueID": dict(type=str),
    "openTypeNameDescription": dict(type=str),
    "openTypeNamePreferredFamilyName": dict(type=str),
    "openTypeNamePreferredSubfamilyName": dict(type=str),
    "openTypeNameCompatibleFullName": dict(type=str),
    "openTypeNameSampleText": dict(type=str),
    "openTypeNameWWSFamilyName": dict(type=str),
    "openTypeNameWWSSubfamilyName": dict(type=str),
    "openTypeOS2WidthClass": dict(
        type=int, valueValidator=fontInfoOpenTypeOS2WidthClassValidator
    ),
    "openTypeOS2WeightClass": dict(
        type=int, valueValidator=fontInfoOpenTypeOS2WeightClassValidator
    ),
    "openTypeOS2Selection": dict(
        type="integerList",
        valueValidator=genericIntListValidator,
        valueOptions=fontInfoOpenTypeOS2SelectionOptions,
    ),
    "openTypeOS2VendorID": dict(type=str),
    "openTypeOS2Panose": dict(
        type="integerList", valueValidator=fontInfoVersion2OpenTypeOS2PanoseValidator
    ),
    "openTypeOS2FamilyClass": dict(
        type="integerList", valueValidator=fontInfoOpenTypeOS2FamilyClassValidator
    ),
    "openTypeOS2UnicodeRanges": dict(
        type="integerList",
        valueValidator=genericIntListValidator,
        valueOptions=fontInfoOpenTypeOS2UnicodeRangesOptions,
    ),
    "openTypeOS2CodePageRanges": dict(
        type="integerList",
        valueValidator=genericIntListValidator,
        valueOptions=fontInfoOpenTypeOS2CodePageRangesOptions,
    ),
    "openTypeOS2TypoAscender": dict(type=(int, float)),
    "openTypeOS2TypoDescender": dict(type=(int, float)),
    "openTypeOS2TypoLineGap": dict(type=(int, float)),
    "openTypeOS2WinAscent": dict(type=(int, float)),
    "openTypeOS2WinDescent": dict(type=(int, float)),
    "openTypeOS2Type": dict(
        type="integerList",
        valueValidator=genericIntListValidator,
        valueOptions=fontInfoOpenTypeOS2TypeOptions,
    ),
    "openTypeOS2SubscriptXSize": dict(type=(int, float)),
    "openTypeOS2SubscriptYSize": dict(type=(int, float)),
    "openTypeOS2SubscriptXOffset": dict(type=(int, float)),
    "openTypeOS2SubscriptYOffset": dict(type=(int, float)),
    "openTypeOS2SuperscriptXSize": dict(type=(int, float)),
    "openTypeOS2SuperscriptYSize": dict(type=(int, float)),
    "openTypeOS2SuperscriptXOffset": dict(type=(int, float)),
    "openTypeOS2SuperscriptYOffset": dict(type=(int, float)),
    "openTypeOS2StrikeoutSize": dict(type=(int, float)),
    "openTypeOS2StrikeoutPosition": dict(type=(int, float)),
    "openTypeVheaVertTypoAscender": dict(type=(int, float)),
    "openTypeVheaVertTypoDescender": dict(type=(int, float)),
    "openTypeVheaVertTypoLineGap": dict(type=(int, float)),
    "openTypeVheaCaretSlopeRise": dict(type=int),
    "openTypeVheaCaretSlopeRun": dict(type=int),
    "openTypeVheaCaretOffset": dict(type=(int, float)),
    "postscriptFontName": dict(type=str),
    "postscriptFullName": dict(type=str),
    "postscriptSlantAngle": dict(type=(float, int)),
    "postscriptUniqueID": dict(type=int),
    "postscriptUnderlineThickness": dict(type=(int, float)),
    "postscriptUnderlinePosition": dict(type=(int, float)),
    "postscriptIsFixedPitch": dict(type=bool),
    "postscriptBlueValues": dict(
        type="integerList", valueValidator=fontInfoPostscriptBluesValidator
    ),
    "postscriptOtherBlues": dict(
        type="integerList", valueValidator=fontInfoPostscriptOtherBluesValidator
    ),
    "postscriptFamilyBlues": dict(
        type="integerList", valueValidator=fontInfoPostscriptBluesValidator
    ),
    "postscriptFamilyOtherBlues": dict(
        type="integerList", valueValidator=fontInfoPostscriptOtherBluesValidator
    ),
    "postscriptStemSnapH": dict(
        type="integerList", valueValidator=fontInfoPostscriptStemsValidator
    ),
    "postscriptStemSnapV": dict(
        type="integerList", valueValidator=fontInfoPostscriptStemsValidator
    ),
    "postscriptBlueFuzz": dict(type=(int, float)),
    "postscriptBlueShift": dict(type=(int, float)),
    "postscriptBlueScale": dict(type=(float, int)),
    "postscriptForceBold": dict(type=bool),
    "postscriptDefaultWidthX": dict(type=(int, float)),
    "postscriptNominalWidthX": dict(type=(int, float)),
    "postscriptWeightName": dict(type=str),
    "postscriptDefaultCharacter": dict(type=str),
    "postscriptWindowsCharacterSet": dict(
        type=int, valueValidator=fontInfoPostscriptWindowsCharacterSetValidator
    ),
    "macintoshFONDFamilyID": dict(type=int),
    "macintoshFONDName": dict(type=str),
}
fontInfoAttributesVersion2 = set(fontInfoAttributesVersion2ValueData.keys())

fontInfoAttributesVersion3ValueData = deepcopy(fontInfoAttributesVersion2ValueData)
fontInfoAttributesVersion3ValueData.update(
    {
        "versionMinor": dict(type=int, valueValidator=genericNonNegativeIntValidator),
        "unitsPerEm": dict(
            type=(int, float), valueValidator=genericNonNegativeNumberValidator
        ),
        "openTypeHeadLowestRecPPEM": dict(
            type=int, valueValidator=genericNonNegativeNumberValidator
        ),
        "openTypeHheaAscender": dict(type=int),
        "openTypeHheaDescender": dict(type=int),
        "openTypeHheaLineGap": dict(type=int),
        "openTypeHheaCaretOffset": dict(type=int),
        "openTypeOS2Panose": dict(
            type="integerList",
            valueValidator=fontInfoVersion3OpenTypeOS2PanoseValidator,
        ),
        "openTypeOS2TypoAscender": dict(type=int),
        "openTypeOS2TypoDescender": dict(type=int),
        "openTypeOS2TypoLineGap": dict(type=int),
        "openTypeOS2WinAscent": dict(
            type=int, valueValidator=genericNonNegativeNumberValidator
        ),
        "openTypeOS2WinDescent": dict(
            type=int, valueValidator=genericNonNegativeNumberValidator
        ),
        "openTypeOS2SubscriptXSize": dict(type=int),
        "openTypeOS2SubscriptYSize": dict(type=int),
        "openTypeOS2SubscriptXOffset": dict(type=int),
        "openTypeOS2SubscriptYOffset": dict(type=int),
        "openTypeOS2SuperscriptXSize": dict(type=int),
        "openTypeOS2SuperscriptYSize": dict(type=int),
        "openTypeOS2SuperscriptXOffset": dict(type=int),
        "openTypeOS2SuperscriptYOffset": dict(type=int),
        "openTypeOS2StrikeoutSize": dict(type=int),
        "openTypeOS2StrikeoutPosition": dict(type=int),
        "openTypeGaspRangeRecords": dict(
            type="dictList", valueValidator=fontInfoOpenTypeGaspRangeRecordsValidator
        ),
        "openTypeNameRecords": dict(
            type="dictList", valueValidator=fontInfoOpenTypeNameRecordsValidator
        ),
        "openTypeVheaVertTypoAscender": dict(type=int),
        "openTypeVheaVertTypoDescender": dict(type=int),
        "openTypeVheaVertTypoLineGap": dict(type=int),
        "openTypeVheaCaretOffset": dict(type=int),
        "woffMajorVersion": dict(
            type=int, valueValidator=genericNonNegativeIntValidator
        ),
        "woffMinorVersion": dict(
            type=int, valueValidator=genericNonNegativeIntValidator
        ),
        "woffMetadataUniqueID": dict(
            type=dict, valueValidator=fontInfoWOFFMetadataUniqueIDValidator
        ),
        "woffMetadataVendor": dict(
            type=dict, valueValidator=fontInfoWOFFMetadataVendorValidator
        ),
        "woffMetadataCredits": dict(
            type=dict, valueValidator=fontInfoWOFFMetadataCreditsValidator
        ),
        "woffMetadataDescription": dict(
            type=dict, valueValidator=fontInfoWOFFMetadataDescriptionValidator
        ),
        "woffMetadataLicense": dict(
            type=dict, valueValidator=fontInfoWOFFMetadataLicenseValidator
        ),
        "woffMetadataCopyright": dict(
            type=dict, valueValidator=fontInfoWOFFMetadataCopyrightValidator
        ),
        "woffMetadataTrademark": dict(
            type=dict, valueValidator=fontInfoWOFFMetadataTrademarkValidator
        ),
        "woffMetadataLicensee": dict(
            type=dict, valueValidator=fontInfoWOFFMetadataLicenseeValidator
        ),
        "woffMetadataExtensions": dict(
            type=list, valueValidator=fontInfoWOFFMetadataExtensionsValidator
        ),
        "guidelines": dict(type=list, valueValidator=guidelinesValidator),
    }
)
fontInfoAttributesVersion3 = set(fontInfoAttributesVersion3ValueData.keys())

# insert the type validator for all attrs that
# have no defined validator.
for attr, dataDict in list(fontInfoAttributesVersion2ValueData.items()):
    if "valueValidator" not in dataDict:
        dataDict["valueValidator"] = genericTypeValidator

for attr, dataDict in list(fontInfoAttributesVersion3ValueData.items()):
    if "valueValidator" not in dataDict:
        dataDict["valueValidator"] = genericTypeValidator

# Version Conversion Support
# These are used from converting from version 1
# to version 2 or vice-versa.


def _flipDict(d):
    flipped = {}
    for key, value in list(d.items()):
        flipped[value] = key
    return flipped


fontInfoAttributesVersion1To2 = {
    "menuName": "styleMapFamilyName",
    "designer": "openTypeNameDesigner",
    "designerURL": "openTypeNameDesignerURL",
    "createdBy": "openTypeNameManufacturer",
    "vendorURL": "openTypeNameManufacturerURL",
    "license": "openTypeNameLicense",
    "licenseURL": "openTypeNameLicenseURL",
    "ttVersion": "openTypeNameVersion",
    "ttUniqueID": "openTypeNameUniqueID",
    "notice": "openTypeNameDescription",
    "otFamilyName": "openTypeNamePreferredFamilyName",
    "otStyleName": "openTypeNamePreferredSubfamilyName",
    "otMacName": "openTypeNameCompatibleFullName",
    "weightName": "postscriptWeightName",
    "weightValue": "openTypeOS2WeightClass",
    "ttVendor": "openTypeOS2VendorID",
    "uniqueID": "postscriptUniqueID",
    "fontName": "postscriptFontName",
    "fondID": "macintoshFONDFamilyID",
    "fondName": "macintoshFONDName",
    "defaultWidth": "postscriptDefaultWidthX",
    "slantAngle": "postscriptSlantAngle",
    "fullName": "postscriptFullName",
    # require special value conversion
    "fontStyle": "styleMapStyleName",
    "widthName": "openTypeOS2WidthClass",
    "msCharSet": "postscriptWindowsCharacterSet",
}
fontInfoAttributesVersion2To1 = _flipDict(fontInfoAttributesVersion1To2)
deprecatedFontInfoAttributesVersion2 = set(fontInfoAttributesVersion1To2.keys())

_fontStyle1To2 = {64: "regular", 1: "italic", 32: "bold", 33: "bold italic"}
_fontStyle2To1 = _flipDict(_fontStyle1To2)
# Some UFO 1 files have 0
_fontStyle1To2[0] = "regular"

_widthName1To2 = {
    "Ultra-condensed": 1,
    "Extra-condensed": 2,
    "Condensed": 3,
    "Semi-condensed": 4,
    "Medium (normal)": 5,
    "Semi-expanded": 6,
    "Expanded": 7,
    "Extra-expanded": 8,
    "Ultra-expanded": 9,
}
_widthName2To1 = _flipDict(_widthName1To2)
# FontLab's default width value is "Normal".
# Many format version 1 UFOs will have this.
_widthName1To2["Normal"] = 5
# FontLab has an "All" width value. In UFO 1
# move this up to "Normal".
_widthName1To2["All"] = 5
# "medium" appears in a lot of UFO 1 files.
_widthName1To2["medium"] = 5
# "Medium" appears in a lot of UFO 1 files.
_widthName1To2["Medium"] = 5

_msCharSet1To2 = {
    0: 1,
    1: 2,
    2: 3,
    77: 4,
    128: 5,
    129: 6,
    130: 7,
    134: 8,
    136: 9,
    161: 10,
    162: 11,
    163: 12,
    177: 13,
    178: 14,
    186: 15,
    200: 16,
    204: 17,
    222: 18,
    238: 19,
    255: 20,
}
_msCharSet2To1 = _flipDict(_msCharSet1To2)

# 1 <-> 2


def convertFontInfoValueForAttributeFromVersion1ToVersion2(attr, value):
    """
    Convert value from version 1 to version 2 format.
    Returns the new attribute name and the converted value.
    If the value is None, None will be returned for the new value.
    """
    # convert floats to ints if possible
    if isinstance(value, float):
        if int(value) == value:
            value = int(value)
    if value is not None:
        if attr == "fontStyle":
            v = _fontStyle1To2.get(value)
            if v is None:
                raise UFOLibError(
                    f"Cannot convert value ({value!r}) for attribute {attr}."
                )
            value = v
        elif attr == "widthName":
            v = _widthName1To2.get(value)
            if v is None:
                raise UFOLibError(
                    f"Cannot convert value ({value!r}) for attribute {attr}."
                )
            value = v
        elif attr == "msCharSet":
            v = _msCharSet1To2.get(value)
            if v is None:
                raise UFOLibError(
                    f"Cannot convert value ({value!r}) for attribute {attr}."
                )
            value = v
    attr = fontInfoAttributesVersion1To2.get(attr, attr)
    return attr, value


def convertFontInfoValueForAttributeFromVersion2ToVersion1(attr, value):
    """
    Convert value from version 2 to version 1 format.
    Returns the new attribute name and the converted value.
    If the value is None, None will be returned for the new value.
    """
    if value is not None:
        if attr == "styleMapStyleName":
            value = _fontStyle2To1.get(value)
        elif attr == "openTypeOS2WidthClass":
            value = _widthName2To1.get(value)
        elif attr == "postscriptWindowsCharacterSet":
            value = _msCharSet2To1.get(value)
    attr = fontInfoAttributesVersion2To1.get(attr, attr)
    return attr, value


def _convertFontInfoDataVersion1ToVersion2(data):
    converted = {}
    for attr, value in list(data.items()):
        # FontLab gives -1 for the weightValue
        # for fonts wil no defined value. Many
        # format version 1 UFOs will have this.
        if attr == "weightValue" and value == -1:
            continue
        newAttr, newValue = convertFontInfoValueForAttributeFromVersion1ToVersion2(
            attr, value
        )
        # skip if the attribute is not part of version 2
        if newAttr not in fontInfoAttributesVersion2:
            continue
        # catch values that can't be converted
        if value is None:
            raise UFOLibError(
                f"Cannot convert value ({value!r}) for attribute {newAttr}."
            )
        # store
        converted[newAttr] = newValue
    return converted


def _convertFontInfoDataVersion2ToVersion1(data):
    converted = {}
    for attr, value in list(data.items()):
        newAttr, newValue = convertFontInfoValueForAttributeFromVersion2ToVersion1(
            attr, value
        )
        # only take attributes that are registered for version 1
        if newAttr not in fontInfoAttributesVersion1:
            continue
        # catch values that can't be converted
        if value is None:
            raise UFOLibError(
                f"Cannot convert value ({value!r}) for attribute {newAttr}."
            )
        # store
        converted[newAttr] = newValue
    return converted


# 2 <-> 3

_ufo2To3NonNegativeInt = {
    "versionMinor",
    "openTypeHeadLowestRecPPEM",
    "openTypeOS2WinAscent",
    "openTypeOS2WinDescent",
}
_ufo2To3NonNegativeIntOrFloat = {
    "unitsPerEm",
}
_ufo2To3FloatToInt = {
    "openTypeHeadLowestRecPPEM",
    "openTypeHheaAscender",
    "openTypeHheaDescender",
    "openTypeHheaLineGap",
    "openTypeHheaCaretOffset",
    "openTypeOS2TypoAscender",
    "openTypeOS2TypoDescender",
    "openTypeOS2TypoLineGap",
    "openTypeOS2WinAscent",
    "openTypeOS2WinDescent",
    "openTypeOS2SubscriptXSize",
    "openTypeOS2SubscriptYSize",
    "openTypeOS2SubscriptXOffset",
    "openTypeOS2SubscriptYOffset",
    "openTypeOS2SuperscriptXSize",
    "openTypeOS2SuperscriptYSize",
    "openTypeOS2SuperscriptXOffset",
    "openTypeOS2SuperscriptYOffset",
    "openTypeOS2StrikeoutSize",
    "openTypeOS2StrikeoutPosition",
    "openTypeVheaVertTypoAscender",
    "openTypeVheaVertTypoDescender",
    "openTypeVheaVertTypoLineGap",
    "openTypeVheaCaretOffset",
}


def convertFontInfoValueForAttributeFromVersion2ToVersion3(attr, value):
    """
    Convert value from version 2 to version 3 format.
    Returns the new attribute name and the converted value.
    If the value is None, None will be returned for the new value.
    """
    if attr in _ufo2To3FloatToInt:
        try:
            value = round(value)
        except (ValueError, TypeError):
            raise UFOLibError("Could not convert value for %s." % attr)
    if attr in _ufo2To3NonNegativeInt:
        try:
            value = int(abs(value))
        except (ValueError, TypeError):
            raise UFOLibError("Could not convert value for %s." % attr)
    elif attr in _ufo2To3NonNegativeIntOrFloat:
        try:
            v = float(abs(value))
        except (ValueError, TypeError):
            raise UFOLibError("Could not convert value for %s." % attr)
        if v == int(v):
            v = int(v)
        if v != value:
            value = v
    return attr, value


def convertFontInfoValueForAttributeFromVersion3ToVersion2(attr, value):
    """
    Convert value from version 3 to version 2 format.
    Returns the new attribute name and the converted value.
    If the value is None, None will be returned for the new value.
    """
    return attr, value


def _convertFontInfoDataVersion3ToVersion2(data):
    converted = {}
    for attr, value in list(data.items()):
        newAttr, newValue = convertFontInfoValueForAttributeFromVersion3ToVersion2(
            attr, value
        )
        if newAttr not in fontInfoAttributesVersion2:
            continue
        converted[newAttr] = newValue
    return converted


def _convertFontInfoDataVersion2ToVersion3(data):
    converted = {}
    for attr, value in list(data.items()):
        attr, value = convertFontInfoValueForAttributeFromVersion2ToVersion3(
            attr, value
        )
        converted[attr] = value
    return converted


if __name__ == "__main__":
    import doctest

    doctest.testmod()

# === NexusCore/openenv\Lib\site-packages\matplotlib\cbook.py ===
"""
A collection of utility functions and classes.  Originally, many
(but not all) were from the Python Cookbook -- hence the name cbook.
"""

import collections
import collections.abc
import contextlib
import functools
import gzip
import itertools
import math
import operator
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import traceback
import types
import weakref

import numpy as np

try:
    from numpy.exceptions import VisibleDeprecationWarning  # numpy >= 1.25
except ImportError:
    from numpy import VisibleDeprecationWarning

import matplotlib
from matplotlib import _api, _c_internal_utils


class _ExceptionInfo:
    """
    A class to carry exception information around.

    This is used to store and later raise exceptions. It's an alternative to
    directly storing Exception instances that circumvents traceback-related
    issues: caching tracebacks can keep user's objects in local namespaces
    alive indefinitely, which can lead to very surprising memory issues for
    users and result in incorrect tracebacks.
    """

    def __init__(self, cls, *args):
        self._cls = cls
        self._args = args

    @classmethod
    def from_exception(cls, exc):
        return cls(type(exc), *exc.args)

    def to_exception(self):
        return self._cls(*self._args)


def _get_running_interactive_framework():
    """
    Return the interactive framework whose event loop is currently running, if
    any, or "headless" if no event loop can be started, or None.

    Returns
    -------
    Optional[str]
        One of the following values: "qt", "gtk3", "gtk4", "wx", "tk",
        "macosx", "headless", ``None``.
    """
    # Use ``sys.modules.get(name)`` rather than ``name in sys.modules`` as
    # entries can also have been explicitly set to None.
    QtWidgets = (
        sys.modules.get("PyQt6.QtWidgets")
        or sys.modules.get("PySide6.QtWidgets")
        or sys.modules.get("PyQt5.QtWidgets")
        or sys.modules.get("PySide2.QtWidgets")
    )
    if QtWidgets and QtWidgets.QApplication.instance():
        return "qt"
    Gtk = sys.modules.get("gi.repository.Gtk")
    if Gtk:
        if Gtk.MAJOR_VERSION == 4:
            from gi.repository import GLib
            if GLib.main_depth():
                return "gtk4"
        if Gtk.MAJOR_VERSION == 3 and Gtk.main_level():
            return "gtk3"
    wx = sys.modules.get("wx")
    if wx and wx.GetApp():
        return "wx"
    tkinter = sys.modules.get("tkinter")
    if tkinter:
        codes = {tkinter.mainloop.__code__, tkinter.Misc.mainloop.__code__}
        for frame in sys._current_frames().values():
            while frame:
                if frame.f_code in codes:
                    return "tk"
                frame = frame.f_back
        # Preemptively break reference cycle between locals and the frame.
        del frame
    macosx = sys.modules.get("matplotlib.backends._macosx")
    if macosx and macosx.event_loop_is_running():
        return "macosx"
    if not _c_internal_utils.display_is_valid():
        return "headless"
    return None


def _exception_printer(exc):
    if _get_running_interactive_framework() in ["headless", None]:
        raise exc
    else:
        traceback.print_exc()


class _StrongRef:
    """
    Wrapper similar to a weakref, but keeping a strong reference to the object.
    """

    def __init__(self, obj):
        self._obj = obj

    def __call__(self):
        return self._obj

    def __eq__(self, other):
        return isinstance(other, _StrongRef) and self._obj == other._obj

    def __hash__(self):
        return hash(self._obj)


def _weak_or_strong_ref(func, callback):
    """
    Return a `WeakMethod` wrapping *func* if possible, else a `_StrongRef`.
    """
    try:
        return weakref.WeakMethod(func, callback)
    except TypeError:
        return _StrongRef(func)


class _UnhashDict:
    """
    A minimal dict-like class that also supports unhashable keys, storing them
    in a list of key-value pairs.

    This class only implements the interface needed for `CallbackRegistry`, and
    tries to minimize the overhead for the hashable case.
    """

    def __init__(self, pairs):
        self._dict = {}
        self._pairs = []
        for k, v in pairs:
            self[k] = v

    def __setitem__(self, key, value):
        try:
            self._dict[key] = value
        except TypeError:
            for i, (k, v) in enumerate(self._pairs):
                if k == key:
                    self._pairs[i] = (key, value)
                    break
            else:
                self._pairs.append((key, value))

    def __getitem__(self, key):
        try:
            return self._dict[key]
        except TypeError:
            pass
        for k, v in self._pairs:
            if k == key:
                return v
        raise KeyError(key)

    def pop(self, key, *args):
        try:
            if key in self._dict:
                return self._dict.pop(key)
        except TypeError:
            for i, (k, v) in enumerate(self._pairs):
                if k == key:
                    del self._pairs[i]
                    return v
        if args:
            return args[0]
        raise KeyError(key)

    def __iter__(self):
        yield from self._dict
        for k, v in self._pairs:
            yield k


class CallbackRegistry:
    """
    Handle registering, processing, blocking, and disconnecting
    for a set of signals and callbacks:

        >>> def oneat(x):
        ...     print('eat', x)
        >>> def ondrink(x):
        ...     print('drink', x)

        >>> from matplotlib.cbook import CallbackRegistry
        >>> callbacks = CallbackRegistry()

        >>> id_eat = callbacks.connect('eat', oneat)
        >>> id_drink = callbacks.connect('drink', ondrink)

        >>> callbacks.process('drink', 123)
        drink 123
        >>> callbacks.process('eat', 456)
        eat 456
        >>> callbacks.process('be merry', 456)   # nothing will be called

        >>> callbacks.disconnect(id_eat)
        >>> callbacks.process('eat', 456)        # nothing will be called

        >>> with callbacks.blocked(signal='drink'):
        ...     callbacks.process('drink', 123)  # nothing will be called
        >>> callbacks.process('drink', 123)
        drink 123

    In practice, one should always disconnect all callbacks when they are
    no longer needed to avoid dangling references (and thus memory leaks).
    However, real code in Matplotlib rarely does so, and due to its design,
    it is rather difficult to place this kind of code.  To get around this,
    and prevent this class of memory leaks, we instead store weak references
    to bound methods only, so when the destination object needs to die, the
    CallbackRegistry won't keep it alive.

    Parameters
    ----------
    exception_handler : callable, optional
       If not None, *exception_handler* must be a function that takes an
       `Exception` as single parameter.  It gets called with any `Exception`
       raised by the callbacks during `CallbackRegistry.process`, and may
       either re-raise the exception or handle it in another manner.

       The default handler prints the exception (with `traceback.print_exc`) if
       an interactive event loop is running; it re-raises the exception if no
       interactive event loop is running.

    signals : list, optional
        If not None, *signals* is a list of signals that this registry handles:
        attempting to `process` or to `connect` to a signal not in the list
        throws a `ValueError`.  The default, None, does not restrict the
        handled signals.
    """

    # We maintain two mappings:
    #   callbacks: signal -> {cid -> weakref-to-callback}
    #   _func_cid_map: {(signal, weakref-to-callback) -> cid}

    def __init__(self, exception_handler=_exception_printer, *, signals=None):
        self._signals = None if signals is None else list(signals)  # Copy it.
        self.exception_handler = exception_handler
        self.callbacks = {}
        self._cid_gen = itertools.count()
        self._func_cid_map = _UnhashDict([])
        # A hidden variable that marks cids that need to be pickled.
        self._pickled_cids = set()

    def __getstate__(self):
        return {
            **vars(self),
            # In general, callbacks may not be pickled, so we just drop them,
            # unless directed otherwise by self._pickled_cids.
            "callbacks": {s: {cid: proxy() for cid, proxy in d.items()
                              if cid in self._pickled_cids}
                          for s, d in self.callbacks.items()},
            # It is simpler to reconstruct this from callbacks in __setstate__.
            "_func_cid_map": None,
            "_cid_gen": next(self._cid_gen)
        }

    def __setstate__(self, state):
        cid_count = state.pop('_cid_gen')
        vars(self).update(state)
        self.callbacks = {
            s: {cid: _weak_or_strong_ref(func, functools.partial(self._remove_proxy, s))
                for cid, func in d.items()}
            for s, d in self.callbacks.items()}
        self._func_cid_map = _UnhashDict(
            ((s, proxy), cid)
            for s, d in self.callbacks.items() for cid, proxy in d.items())
        self._cid_gen = itertools.count(cid_count)

    def connect(self, signal, func):
        """Register *func* to be called when signal *signal* is generated."""
        if self._signals is not None:
            _api.check_in_list(self._signals, signal=signal)
        proxy = _weak_or_strong_ref(func, functools.partial(self._remove_proxy, signal))
        try:
            return self._func_cid_map[signal, proxy]
        except KeyError:
            cid = self._func_cid_map[signal, proxy] = next(self._cid_gen)
            self.callbacks.setdefault(signal, {})[cid] = proxy
            return cid

    def _connect_picklable(self, signal, func):
        """
        Like `.connect`, but the callback is kept when pickling/unpickling.

        Currently internal-use only.
        """
        cid = self.connect(signal, func)
        self._pickled_cids.add(cid)
        return cid

    # Keep a reference to sys.is_finalizing, as sys may have been cleared out
    # at that point.
    def _remove_proxy(self, signal, proxy, *, _is_finalizing=sys.is_finalizing):
        if _is_finalizing():
            # Weakrefs can't be properly torn down at that point anymore.
            return
        cid = self._func_cid_map.pop((signal, proxy), None)
        if cid is not None:
            del self.callbacks[signal][cid]
            self._pickled_cids.discard(cid)
        else:  # Not found
            return
        if len(self.callbacks[signal]) == 0:  # Clean up empty dicts
            del self.callbacks[signal]

    def disconnect(self, cid):
        """
        Disconnect the callback registered with callback id *cid*.

        No error is raised if such a callback does not exist.
        """
        self._pickled_cids.discard(cid)
        for signal, proxy in self._func_cid_map:
            if self._func_cid_map[signal, proxy] == cid:
                break
        else:  # Not found
            return
        assert self.callbacks[signal][cid] == proxy
        del self.callbacks[signal][cid]
        self._func_cid_map.pop((signal, proxy))
        if len(self.callbacks[signal]) == 0:  # Clean up empty dicts
            del self.callbacks[signal]

    def process(self, s, *args, **kwargs):
        """
        Process signal *s*.

        All of the functions registered to receive callbacks on *s* will be
        called with ``*args`` and ``**kwargs``.
        """
        if self._signals is not None:
            _api.check_in_list(self._signals, signal=s)
        for ref in list(self.callbacks.get(s, {}).values()):
            func = ref()
            if func is not None:
                try:
                    func(*args, **kwargs)
                # this does not capture KeyboardInterrupt, SystemExit,
                # and GeneratorExit
                except Exception as exc:
                    if self.exception_handler is not None:
                        self.exception_handler(exc)
                    else:
                        raise

    @contextlib.contextmanager
    def blocked(self, *, signal=None):
        """
        Block callback signals from being processed.

        A context manager to temporarily block/disable callback signals
        from being processed by the registered listeners.

        Parameters
        ----------
        signal : str, optional
            The callback signal to block. The default is to block all signals.
        """
        orig = self.callbacks
        try:
            if signal is None:
                # Empty out the callbacks
                self.callbacks = {}
            else:
                # Only remove the specific signal
                self.callbacks = {k: orig[k] for k in orig if k != signal}
            yield
        finally:
            self.callbacks = orig


class silent_list(list):
    """
    A list with a short ``repr()``.

    This is meant to be used for a homogeneous list of artists, so that they
    don't cause long, meaningless output.

    Instead of ::

        [<matplotlib.lines.Line2D object at 0x7f5749fed3c8>,
         <matplotlib.lines.Line2D object at 0x7f5749fed4e0>,
         <matplotlib.lines.Line2D object at 0x7f5758016550>]

    one will get ::

        <a list of 3 Line2D objects>

    If ``self.type`` is None, the type name is obtained from the first item in
    the list (if any).
    """

    def __init__(self, type, seq=None):
        self.type = type
        if seq is not None:
            self.extend(seq)

    def __repr__(self):
        if self.type is not None or len(self) != 0:
            tp = self.type if self.type is not None else type(self[0]).__name__
            return f"<a list of {len(self)} {tp} objects>"
        else:
            return "<an empty list>"


def _local_over_kwdict(
        local_var, kwargs, *keys,
        warning_cls=_api.MatplotlibDeprecationWarning):
    out = local_var
    for key in keys:
        kwarg_val = kwargs.pop(key, None)
        if kwarg_val is not None:
            if out is None:
                out = kwarg_val
            else:
                _api.warn_external(f'"{key}" keyword argument will be ignored',
                                   warning_cls)
    return out


def strip_math(s):
    """
    Remove latex formatting from mathtext.

    Only handles fully math and fully non-math strings.
    """
    if len(s) >= 2 and s[0] == s[-1] == "$":
        s = s[1:-1]
        for tex, plain in [
                (r"\times", "x"),  # Specifically for Formatter support.
                (r"\mathdefault", ""),
                (r"\rm", ""),
                (r"\cal", ""),
                (r"\tt", ""),
                (r"\it", ""),
                ("\\", ""),
                ("{", ""),
                ("}", ""),
        ]:
            s = s.replace(tex, plain)
    return s


def _strip_comment(s):
    """Strip everything from the first unquoted #."""
    pos = 0
    while True:
        quote_pos = s.find('"', pos)
        hash_pos = s.find('#', pos)
        if quote_pos < 0:
            without_comment = s if hash_pos < 0 else s[:hash_pos]
            return without_comment.strip()
        elif 0 <= hash_pos < quote_pos:
            return s[:hash_pos].strip()
        else:
            closing_quote_pos = s.find('"', quote_pos + 1)
            if closing_quote_pos < 0:
                raise ValueError(
                    f"Missing closing quote in: {s!r}. If you need a double-"
                    'quote inside a string, use escaping: e.g. "the \" char"')
            pos = closing_quote_pos + 1  # behind closing quote


def is_writable_file_like(obj):
    """Return whether *obj* looks like a file object with a *write* method."""
    return callable(getattr(obj, 'write', None))


def file_requires_unicode(x):
    """
    Return whether the given writable file-like object requires Unicode to be
    written to it.
    """
    try:
        x.write(b'')
    except TypeError:
        return True
    else:
        return False


def to_filehandle(fname, flag='r', return_opened=False, encoding=None):
    """
    Convert a path to an open file handle or pass-through a file-like object.

    Consider using `open_file_cm` instead, as it allows one to properly close
    newly created file objects more easily.

    Parameters
    ----------
    fname : str or path-like or file-like
        If `str` or `os.PathLike`, the file is opened using the flags specified
        by *flag* and *encoding*.  If a file-like object, it is passed through.
    flag : str, default: 'r'
        Passed as the *mode* argument to `open` when *fname* is `str` or
        `os.PathLike`; ignored if *fname* is file-like.
    return_opened : bool, default: False
        If True, return both the file object and a boolean indicating whether
        this was a new file (that the caller needs to close).  If False, return
        only the new file.
    encoding : str or None, default: None
        Passed as the *mode* argument to `open` when *fname* is `str` or
        `os.PathLike`; ignored if *fname* is file-like.

    Returns
    -------
    fh : file-like
    opened : bool
        *opened* is only returned if *return_opened* is True.
    """
    if isinstance(fname, os.PathLike):
        fname = os.fspath(fname)
    if isinstance(fname, str):
        if fname.endswith('.gz'):
            fh = gzip.open(fname, flag)
        elif fname.endswith('.bz2'):
            # python may not be compiled with bz2 support,
            # bury import until we need it
            import bz2
            fh = bz2.BZ2File(fname, flag)
        else:
            fh = open(fname, flag, encoding=encoding)
        opened = True
    elif hasattr(fname, 'seek'):
        fh = fname
        opened = False
    else:
        raise ValueError('fname must be a PathLike or file handle')
    if return_opened:
        return fh, opened
    return fh


def open_file_cm(path_or_file, mode="r", encoding=None):
    r"""Pass through file objects and context-manage path-likes."""
    fh, opened = to_filehandle(path_or_file, mode, True, encoding)
    return fh if opened else contextlib.nullcontext(fh)


def is_scalar_or_string(val):
    """Return whether the given object is a scalar or string like."""
    return isinstance(val, str) or not np.iterable(val)


def get_sample_data(fname, asfileobj=True):
    """
    Return a sample data file.  *fname* is a path relative to the
    :file:`mpl-data/sample_data` directory.  If *asfileobj* is `True`
    return a file object, otherwise just a file path.

    Sample data files are stored in the 'mpl-data/sample_data' directory within
    the Matplotlib package.

    If the filename ends in .gz, the file is implicitly ungzipped.  If the
    filename ends with .npy or .npz, and *asfileobj* is `True`, the file is
    loaded with `numpy.load`.
    """
    path = _get_data_path('sample_data', fname)
    if asfileobj:
        suffix = path.suffix.lower()
        if suffix == '.gz':
            return gzip.open(path)
        elif suffix in ['.npy', '.npz']:
            return np.load(path)
        elif suffix in ['.csv', '.xrc', '.txt']:
            return path.open('r')
        else:
            return path.open('rb')
    else:
        return str(path)


def _get_data_path(*args):
    """
    Return the `pathlib.Path` to a resource file provided by Matplotlib.

    ``*args`` specify a path relative to the base data path.
    """
    return Path(matplotlib.get_data_path(), *args)


def flatten(seq, scalarp=is_scalar_or_string):
    """
    Return a generator of flattened nested containers.

    For example:

        >>> from matplotlib.cbook import flatten
        >>> l = (('John', ['Hunter']), (1, 23), [[([42, (5, 23)], )]])
        >>> print(list(flatten(l)))
        ['John', 'Hunter', 1, 23, 42, 5, 23]

    By: Composite of Holger Krekel and Luther Blissett
    From: https://code.activestate.com/recipes/121294-simple-generator-for-flattening-nested-containers/
    and Recipe 1.12 in cookbook
    """  # noqa: E501
    for item in seq:
        if scalarp(item) or item is None:
            yield item
        else:
            yield from flatten(item, scalarp)


class _Stack:
    """
    Stack of elements with a movable cursor.

    Mimics home/back/forward in a web browser.
    """

    def __init__(self):
        self._pos = -1
        self._elements = []

    def clear(self):
        """Empty the stack."""
        self._pos = -1
        self._elements = []

    def __call__(self):
        """Return the current element, or None."""
        return self._elements[self._pos] if self._elements else None

    def __len__(self):
        return len(self._elements)

    def __getitem__(self, ind):
        return self._elements[ind]

    def forward(self):
        """Move the position forward and return the current element."""
        self._pos = min(self._pos + 1, len(self._elements) - 1)
        return self()

    def back(self):
        """Move the position back and return the current element."""
        self._pos = max(self._pos - 1, 0)
        return self()

    def push(self, o):
        """
        Push *o* to the stack after the current position, and return *o*.

        Discard all later elements.
        """
        self._elements[self._pos + 1:] = [o]
        self._pos = len(self._elements) - 1
        return o

    def home(self):
        """
        Push the first element onto the top of the stack.

        The first element is returned.
        """
        return self.push(self._elements[0]) if self._elements else None


def safe_masked_invalid(x, copy=False):
    x = np.array(x, subok=True, copy=copy)
    if not x.dtype.isnative:
        # If we have already made a copy, do the byteswap in place, else make a
        # copy with the byte order swapped.
        # Swap to native order.
        x = x.byteswap(inplace=copy).view(x.dtype.newbyteorder('N'))
    try:
        xm = np.ma.masked_where(~(np.isfinite(x)), x, copy=False)
    except TypeError:
        return x
    return xm


def print_cycles(objects, outstream=sys.stdout, show_progress=False):
    """
    Print loops of cyclic references in the given *objects*.

    It is often useful to pass in ``gc.garbage`` to find the cycles that are
    preventing some objects from being garbage collected.

    Parameters
    ----------
    objects
        A list of objects to find cycles in.
    outstream
        The stream for output.
    show_progress : bool
        If True, print the number of objects reached as they are found.
    """
    import gc

    def print_path(path):
        for i, step in enumerate(path):
            # next "wraps around"
            next = path[(i + 1) % len(path)]

            outstream.write("   %s -- " % type(step))
            if isinstance(step, dict):
                for key, val in step.items():
                    if val is next:
                        outstream.write(f"[{key!r}]")
                        break
                    if key is next:
                        outstream.write(f"[key] = {val!r}")
                        break
            elif isinstance(step, list):
                outstream.write("[%d]" % step.index(next))
            elif isinstance(step, tuple):
                outstream.write("( tuple )")
            else:
                outstream.write(repr(step))
            outstream.write(" ->\n")
        outstream.write("\n")

    def recurse(obj, start, all, current_path):
        if show_progress:
            outstream.write("%d\r" % len(all))

        all[id(obj)] = None

        referents = gc.get_referents(obj)
        for referent in referents:
            # If we've found our way back to the start, this is
            # a cycle, so print it out
            if referent is start:
                print_path(current_path)

            # Don't go back through the original list of objects, or
            # through temporary references to the object, since those
            # are just an artifact of the cycle detector itself.
            elif referent is objects or isinstance(referent, types.FrameType):
                continue

            # We haven't seen this object before, so recurse
            elif id(referent) not in all:
                recurse(referent, start, all, current_path + [obj])

    for obj in objects:
        outstream.write(f"Examining: {obj!r}\n")
        recurse(obj, obj, {}, [])


class Grouper:
    """
    A disjoint-set data structure.

    Objects can be joined using :meth:`join`, tested for connectedness
    using :meth:`joined`, and all disjoint sets can be retrieved by
    using the object as an iterator.

    The objects being joined must be hashable and weak-referenceable.

    Examples
    --------
    >>> from matplotlib.cbook import Grouper
    >>> class Foo:
    ...     def __init__(self, s):
    ...         self.s = s
    ...     def __repr__(self):
    ...         return self.s
    ...
    >>> a, b, c, d, e, f = [Foo(x) for x in 'abcdef']
    >>> grp = Grouper()
    >>> grp.join(a, b)
    >>> grp.join(b, c)
    >>> grp.join(d, e)
    >>> list(grp)
    [[a, b, c], [d, e]]
    >>> grp.joined(a, b)
    True
    >>> grp.joined(a, c)
    True
    >>> grp.joined(a, d)
    False
    """

    def __init__(self, init=()):
        self._mapping = weakref.WeakKeyDictionary(
            {x: weakref.WeakSet([x]) for x in init})
        self._ordering = weakref.WeakKeyDictionary()
        for x in init:
            if x not in self._ordering:
                self._ordering[x] = len(self._ordering)
        self._next_order = len(self._ordering)  # Plain int to simplify pickling.

    def __getstate__(self):
        return {
            **vars(self),
            # Convert weak refs to strong ones.
            "_mapping": {k: set(v) for k, v in self._mapping.items()},
            "_ordering": {**self._ordering},
        }

    def __setstate__(self, state):
        vars(self).update(state)
        # Convert strong refs to weak ones.
        self._mapping = weakref.WeakKeyDictionary(
            {k: weakref.WeakSet(v) for k, v in self._mapping.items()})
        self._ordering = weakref.WeakKeyDictionary(self._ordering)

    def __contains__(self, item):
        return item in self._mapping

    def join(self, a, *args):
        """
        Join given arguments into the same set.  Accepts one or more arguments.
        """
        mapping = self._mapping
        try:
            set_a = mapping[a]
        except KeyError:
            set_a = mapping[a] = weakref.WeakSet([a])
            self._ordering[a] = self._next_order
            self._next_order += 1
        for arg in args:
            try:
                set_b = mapping[arg]
            except KeyError:
                set_b = mapping[arg] = weakref.WeakSet([arg])
                self._ordering[arg] = self._next_order
                self._next_order += 1
            if set_b is not set_a:
                if len(set_b) > len(set_a):
                    set_a, set_b = set_b, set_a
                set_a.update(set_b)
                for elem in set_b:
                    mapping[elem] = set_a

    def joined(self, a, b):
        """Return whether *a* and *b* are members of the same set."""
        return (self._mapping.get(a, object()) is self._mapping.get(b))

    def remove(self, a):
        """Remove *a* from the grouper, doing nothing if it is not there."""
        self._mapping.pop(a, {a}).remove(a)
        self._ordering.pop(a, None)

    def __iter__(self):
        """
        Iterate over each of the disjoint sets as a list.

        The iterator is invalid if interleaved with calls to join().
        """
        unique_groups = {id(group): group for group in self._mapping.values()}
        for group in unique_groups.values():
            yield sorted(group, key=self._ordering.__getitem__)

    def get_siblings(self, a):
        """Return all of the items joined with *a*, including itself."""
        siblings = self._mapping.get(a, [a])
        return sorted(siblings, key=self._ordering.get)


class GrouperView:
    """Immutable view over a `.Grouper`."""

    def __init__(self, grouper): self._grouper = grouper
    def __contains__(self, item): return item in self._grouper
    def __iter__(self): return iter(self._grouper)

    def joined(self, a, b):
        """
        Return whether *a* and *b* are members of the same set.
        """
        return self._grouper.joined(a, b)

    def get_siblings(self, a):
        """
        Return all of the items joined with *a*, including itself.
        """
        return self._grouper.get_siblings(a)


def simple_linear_interpolation(a, steps):
    """
    Resample an array with ``steps - 1`` points between original point pairs.

    Along each column of *a*, ``(steps - 1)`` points are introduced between
    each original values; the values are linearly interpolated.

    Parameters
    ----------
    a : array, shape (n, ...)
    steps : int

    Returns
    -------
    array
        shape ``((n - 1) * steps + 1, ...)``
    """
    fps = a.reshape((len(a), -1))
    xp = np.arange(len(a)) * steps
    x = np.arange((len(a) - 1) * steps + 1)
    return (np.column_stack([np.interp(x, xp, fp) for fp in fps.T])
            .reshape((len(x),) + a.shape[1:]))


def delete_masked_points(*args):
    """
    Find all masked and/or non-finite points in a set of arguments,
    and return the arguments with only the unmasked points remaining.

    Arguments can be in any of 5 categories:

    1) 1-D masked arrays
    2) 1-D ndarrays
    3) ndarrays with more than one dimension
    4) other non-string iterables
    5) anything else

    The first argument must be in one of the first four categories;
    any argument with a length differing from that of the first
    argument (and hence anything in category 5) then will be
    passed through unchanged.

    Masks are obtained from all arguments of the correct length
    in categories 1, 2, and 4; a point is bad if masked in a masked
    array or if it is a nan or inf.  No attempt is made to
    extract a mask from categories 2, 3, and 4 if `numpy.isfinite`
    does not yield a Boolean array.

    All input arguments that are not passed unchanged are returned
    as ndarrays after removing the points or rows corresponding to
    masks in any of the arguments.

    A vastly simpler version of this function was originally
    written as a helper for Axes.scatter().

    """
    if not len(args):
        return ()
    if is_scalar_or_string(args[0]):
        raise ValueError("First argument must be a sequence")
    nrecs = len(args[0])
    margs = []
    seqlist = [False] * len(args)
    for i, x in enumerate(args):
        if not isinstance(x, str) and np.iterable(x) and len(x) == nrecs:
            seqlist[i] = True
            if isinstance(x, np.ma.MaskedArray):
                if x.ndim > 1:
                    raise ValueError("Masked arrays must be 1-D")
            else:
                x = np.asarray(x)
        margs.append(x)
    masks = []  # List of masks that are True where good.
    for i, x in enumerate(margs):
        if seqlist[i]:
            if x.ndim > 1:
                continue  # Don't try to get nan locations unless 1-D.
            if isinstance(x, np.ma.MaskedArray):
                masks.append(~np.ma.getmaskarray(x))  # invert the mask
                xd = x.data
            else:
                xd = x
            try:
                mask = np.isfinite(xd)
                if isinstance(mask, np.ndarray):
                    masks.append(mask)
            except Exception:  # Fixme: put in tuple of possible exceptions?
                pass
    if len(masks):
        mask = np.logical_and.reduce(masks)
        igood = mask.nonzero()[0]
        if len(igood) < nrecs:
            for i, x in enumerate(margs):
                if seqlist[i]:
                    margs[i] = x[igood]
    for i, x in enumerate(margs):
        if seqlist[i] and isinstance(x, np.ma.MaskedArray):
            margs[i] = x.filled()
    return margs


def _combine_masks(*args):
    """
    Find all masked and/or non-finite points in a set of arguments,
    and return the arguments as masked arrays with a common mask.

    Arguments can be in any of 5 categories:

    1) 1-D masked arrays
    2) 1-D ndarrays
    3) ndarrays with more than one dimension
    4) other non-string iterables
    5) anything else

    The first argument must be in one of the first four categories;
    any argument with a length differing from that of the first
    argument (and hence anything in category 5) then will be
    passed through unchanged.

    Masks are obtained from all arguments of the correct length
    in categories 1, 2, and 4; a point is bad if masked in a masked
    array or if it is a nan or inf.  No attempt is made to
    extract a mask from categories 2 and 4 if `numpy.isfinite`
    does not yield a Boolean array.  Category 3 is included to
    support RGB or RGBA ndarrays, which are assumed to have only
    valid values and which are passed through unchanged.

    All input arguments that are not passed unchanged are returned
    as masked arrays if any masked points are found, otherwise as
    ndarrays.

    """
    if not len(args):
        return ()
    if is_scalar_or_string(args[0]):
        raise ValueError("First argument must be a sequence")
    nrecs = len(args[0])
    margs = []  # Output args; some may be modified.
    seqlist = [False] * len(args)  # Flags: True if output will be masked.
    masks = []    # List of masks.
    for i, x in enumerate(args):
        if is_scalar_or_string(x) or len(x) != nrecs:
            margs.append(x)  # Leave it unmodified.
        else:
            if isinstance(x, np.ma.MaskedArray) and x.ndim > 1:
                raise ValueError("Masked arrays must be 1-D")
            try:
                x = np.asanyarray(x)
            except (VisibleDeprecationWarning, ValueError):
                # NumPy 1.19 raises a warning about ragged arrays, but we want
                # to accept basically anything here.
                x = np.asanyarray(x, dtype=object)
            if x.ndim == 1:
                x = safe_masked_invalid(x)
                seqlist[i] = True
                if np.ma.is_masked(x):
                    masks.append(np.ma.getmaskarray(x))
            margs.append(x)  # Possibly modified.
    if len(masks):
        mask = np.logical_or.reduce(masks)
        for i, x in enumerate(margs):
            if seqlist[i]:
                margs[i] = np.ma.array(x, mask=mask)
    return margs


def _broadcast_with_masks(*args, compress=False):
    """
    Broadcast inputs, combining all masked arrays.

    Parameters
    ----------
    *args : array-like
        The inputs to broadcast.
    compress : bool, default: False
        Whether to compress the masked arrays. If False, the masked values
        are replaced by NaNs.

    Returns
    -------
    list of array-like
        The broadcasted and masked inputs.
    """
    # extract the masks, if any
    masks = [k.mask for k in args if isinstance(k, np.ma.MaskedArray)]
    # broadcast to match the shape
    bcast = np.broadcast_arrays(*args, *masks)
    inputs = bcast[:len(args)]
    masks = bcast[len(args):]
    if masks:
        # combine the masks into one
        mask = np.logical_or.reduce(masks)
        # put mask on and compress
        if compress:
            inputs = [np.ma.array(k, mask=mask).compressed()
                      for k in inputs]
        else:
            inputs = [np.ma.array(k, mask=mask, dtype=float).filled(np.nan).ravel()
                      for k in inputs]
    else:
        inputs = [np.ravel(k) for k in inputs]
    return inputs


def boxplot_stats(X, whis=1.5, bootstrap=None, labels=None, autorange=False):
    r"""
    Return a list of dictionaries of statistics used to draw a series of box
    and whisker plots using `~.Axes.bxp`.

    Parameters
    ----------
    X : array-like
        Data that will be represented in the boxplots. Should have 2 or
        fewer dimensions.

    whis : float or (float, float), default: 1.5
        The position of the whiskers.

        If a float, the lower whisker is at the lowest datum above
        ``Q1 - whis*(Q3-Q1)``, and the upper whisker at the highest datum below
        ``Q3 + whis*(Q3-Q1)``, where Q1 and Q3 are the first and third
        quartiles.  The default value of ``whis = 1.5`` corresponds to Tukey's
        original definition of boxplots.

        If a pair of floats, they indicate the percentiles at which to draw the
        whiskers (e.g., (5, 95)).  In particular, setting this to (0, 100)
        results in whiskers covering the whole range of the data.

        In the edge case where ``Q1 == Q3``, *whis* is automatically set to
        (0, 100) (cover the whole range of the data) if *autorange* is True.

        Beyond the whiskers, data are considered outliers and are plotted as
        individual points.

    bootstrap : int, optional
        Number of times the confidence intervals around the median
        should be bootstrapped (percentile method).

    labels : list of str, optional
        Labels for each dataset. Length must be compatible with
        dimensions of *X*.

    autorange : bool, optional (False)
        When `True` and the data are distributed such that the 25th and 75th
        percentiles are equal, ``whis`` is set to (0, 100) such that the
        whisker ends are at the minimum and maximum of the data.

    Returns
    -------
    list of dict
        A list of dictionaries containing the results for each column
        of data. Keys of each dictionary are the following:

        ========   ===================================
        Key        Value Description
        ========   ===================================
        label      tick label for the boxplot
        mean       arithmetic mean value
        med        50th percentile
        q1         first quartile (25th percentile)
        q3         third quartile (75th percentile)
        iqr        interquartile range
        cilo       lower notch around the median
        cihi       upper notch around the median
        whislo     end of the lower whisker
        whishi     end of the upper whisker
        fliers     outliers
        ========   ===================================

    Notes
    -----
    Non-bootstrapping approach to confidence interval uses Gaussian-based
    asymptotic approximation:

    .. math::

        \mathrm{med} \pm 1.57 \times \frac{\mathrm{iqr}}{\sqrt{N}}

    General approach from:
    McGill, R., Tukey, J.W., and Larsen, W.A. (1978) "Variations of
    Boxplots", The American Statistician, 32:12-16.
    """

    def _bootstrap_median(data, N=5000):
        # determine 95% confidence intervals of the median
        M = len(data)
        percentiles = [2.5, 97.5]

        bs_index = np.random.randint(M, size=(N, M))
        bsData = data[bs_index]
        estimate = np.median(bsData, axis=1, overwrite_input=True)

        CI = np.percentile(estimate, percentiles)
        return CI

    def _compute_conf_interval(data, med, iqr, bootstrap):
        if bootstrap is not None:
            # Do a bootstrap estimate of notch locations.
            # get conf. intervals around median
            CI = _bootstrap_median(data, N=bootstrap)
            notch_min = CI[0]
            notch_max = CI[1]
        else:

            N = len(data)
            notch_min = med - 1.57 * iqr / np.sqrt(N)
            notch_max = med + 1.57 * iqr / np.sqrt(N)

        return notch_min, notch_max

    # output is a list of dicts
    bxpstats = []

    # convert X to a list of lists
    X = _reshape_2D(X, "X")

    ncols = len(X)
    if labels is None:
        labels = itertools.repeat(None)
    elif len(labels) != ncols:
        raise ValueError("Dimensions of labels and X must be compatible")

    input_whis = whis
    for ii, (x, label) in enumerate(zip(X, labels)):

        # empty dict
        stats = {}
        if label is not None:
            stats['label'] = label

        # restore whis to the input values in case it got changed in the loop
        whis = input_whis

        # note tricksiness, append up here and then mutate below
        bxpstats.append(stats)

        # if empty, bail
        if len(x) == 0:
            stats['fliers'] = np.array([])
            stats['mean'] = np.nan
            stats['med'] = np.nan
            stats['q1'] = np.nan
            stats['q3'] = np.nan
            stats['iqr'] = np.nan
            stats['cilo'] = np.nan
            stats['cihi'] = np.nan
            stats['whislo'] = np.nan
            stats['whishi'] = np.nan
            continue

        # up-convert to an array, just to be safe
        x = np.ma.asarray(x)
        x = x.data[~x.mask].ravel()

        # arithmetic mean
        stats['mean'] = np.mean(x)

        # medians and quartiles
        q1, med, q3 = np.percentile(x, [25, 50, 75])

        # interquartile range
        stats['iqr'] = q3 - q1
        if stats['iqr'] == 0 and autorange:
            whis = (0, 100)

        # conf. interval around median
        stats['cilo'], stats['cihi'] = _compute_conf_interval(
            x, med, stats['iqr'], bootstrap
        )

        # lowest/highest non-outliers
        if np.iterable(whis) and not isinstance(whis, str):
            loval, hival = np.percentile(x, whis)
        elif np.isreal(whis):
            loval = q1 - whis * stats['iqr']
            hival = q3 + whis * stats['iqr']
        else:
            raise ValueError('whis must be a float or list of percentiles')

        # get high extreme
        wiskhi = x[x <= hival]
        if len(wiskhi) == 0 or np.max(wiskhi) < q3:
            stats['whishi'] = q3
        else:
            stats['whishi'] = np.max(wiskhi)

        # get low extreme
        wisklo = x[x >= loval]
        if len(wisklo) == 0 or np.min(wisklo) > q1:
            stats['whislo'] = q1
        else:
            stats['whislo'] = np.min(wisklo)

        # compute a single array of outliers
        stats['fliers'] = np.concatenate([
            x[x < stats['whislo']],
            x[x > stats['whishi']],
        ])

        # add in the remaining stats
        stats['q1'], stats['med'], stats['q3'] = q1, med, q3

    return bxpstats


#: Maps short codes for line style to their full name used by backends.
ls_mapper = {'-': 'solid', '--': 'dashed', '-.': 'dashdot', ':': 'dotted'}
#: Maps full names for line styles used by backends to their short codes.
ls_mapper_r = {v: k for k, v in ls_mapper.items()}


def contiguous_regions(mask):
    """
    Return a list of (ind0, ind1) such that ``mask[ind0:ind1].all()`` is
    True and we cover all such regions.
    """
    mask = np.asarray(mask, dtype=bool)

    if not mask.size:
        return []

    # Find the indices of region changes, and correct offset
    idx, = np.nonzero(mask[:-1] != mask[1:])
    idx += 1

    # List operations are faster for moderately sized arrays
    idx = idx.tolist()

    # Add first and/or last index if needed
    if mask[0]:
        idx = [0] + idx
    if mask[-1]:
        idx.append(len(mask))

    return list(zip(idx[::2], idx[1::2]))


def is_math_text(s):
    """
    Return whether the string *s* contains math expressions.

    This is done by checking whether *s* contains an even number of
    non-escaped dollar signs.
    """
    s = str(s)
    dollar_count = s.count(r'$') - s.count(r'\$')
    even_dollars = (dollar_count > 0 and dollar_count % 2 == 0)
    return even_dollars


def _to_unmasked_float_array(x):
    """
    Convert a sequence to a float array; if input was a masked array, masked
    values are converted to nans.
    """
    if hasattr(x, 'mask'):
        return np.ma.asarray(x, float).filled(np.nan)
    else:
        return np.asarray(x, float)


def _check_1d(x):
    """Convert scalars to 1D arrays; pass-through arrays as is."""
    # Unpack in case of e.g. Pandas or xarray object
    x = _unpack_to_numpy(x)
    # plot requires `shape` and `ndim`.  If passed an
    # object that doesn't provide them, then force to numpy array.
    # Note this will strip unit information.
    if (not hasattr(x, 'shape') or
            not hasattr(x, 'ndim') or
            len(x.shape) < 1):
        return np.atleast_1d(x)
    else:
        return x


def _reshape_2D(X, name):
    """
    Use Fortran ordering to convert ndarrays and lists of iterables to lists of
    1D arrays.

    Lists of iterables are converted by applying `numpy.asanyarray` to each of
    their elements.  1D ndarrays are returned in a singleton list containing
    them.  2D ndarrays are converted to the list of their *columns*.

    *name* is used to generate the error message for invalid inputs.
    """

    # Unpack in case of e.g. Pandas or xarray object
    X = _unpack_to_numpy(X)

    # Iterate over columns for ndarrays.
    if isinstance(X, np.ndarray):
        X = X.transpose()

        if len(X) == 0:
            return [[]]
        elif X.ndim == 1 and np.ndim(X[0]) == 0:
            # 1D array of scalars: directly return it.
            return [X]
        elif X.ndim in [1, 2]:
            # 2D array, or 1D array of iterables: flatten them first.
            return [np.reshape(x, -1) for x in X]
        else:
            raise ValueError(f'{name} must have 2 or fewer dimensions')

    # Iterate over list of iterables.
    if len(X) == 0:
        return [[]]

    result = []
    is_1d = True
    for xi in X:
        # check if this is iterable, except for strings which we
        # treat as singletons.
        if not isinstance(xi, str):
            try:
                iter(xi)
            except TypeError:
                pass
            else:
                is_1d = False
        xi = np.asanyarray(xi)
        nd = np.ndim(xi)
        if nd > 1:
            raise ValueError(f'{name} must have 2 or fewer dimensions')
        result.append(xi.reshape(-1))

    if is_1d:
        # 1D array of scalars: directly return it.
        return [np.reshape(result, -1)]
    else:
        # 2D array, or 1D array of iterables: use flattened version.
        return result


def violin_stats(X, method, points=100, quantiles=None):
    """
    Return a list of dictionaries of data which can be used to draw a series
    of violin plots.

    See the ``Returns`` section below to view the required keys of the
    dictionary.

    Users can skip this function and pass a user-defined set of dictionaries
    with the same keys to `~.axes.Axes.violinplot` instead of using Matplotlib
    to do the calculations. See the *Returns* section below for the keys
    that must be present in the dictionaries.

    Parameters
    ----------
    X : array-like
        Sample data that will be used to produce the gaussian kernel density
        estimates. Must have 2 or fewer dimensions.

    method : callable
        The method used to calculate the kernel density estimate for each
        column of data. When called via ``method(v, coords)``, it should
        return a vector of the values of the KDE evaluated at the values
        specified in coords.

    points : int, default: 100
        Defines the number of points to evaluate each of the gaussian kernel
        density estimates at.

    quantiles : array-like, default: None
        Defines (if not None) a list of floats in interval [0, 1] for each
        column of data, which represents the quantiles that will be rendered
        for that column of data. Must have 2 or fewer dimensions. 1D array will
        be treated as a singleton list containing them.

    Returns
    -------
    list of dict
        A list of dictionaries containing the results for each column of data.
        The dictionaries contain at least the following:

        - coords: A list of scalars containing the coordinates this particular
          kernel density estimate was evaluated at.
        - vals: A list of scalars containing the values of the kernel density
          estimate at each of the coordinates given in *coords*.
        - mean: The mean value for this column of data.
        - median: The median value for this column of data.
        - min: The minimum value for this column of data.
        - max: The maximum value for this column of data.
        - quantiles: The quantile values for this column of data.
    """

    # List of dictionaries describing each of the violins.
    vpstats = []

    # Want X to be a list of data sequences
    X = _reshape_2D(X, "X")

    # Want quantiles to be as the same shape as data sequences
    if quantiles is not None and len(quantiles) != 0:
        quantiles = _reshape_2D(quantiles, "quantiles")
    # Else, mock quantiles if it's none or empty
    else:
        quantiles = [[]] * len(X)

    # quantiles should have the same size as dataset
    if len(X) != len(quantiles):
        raise ValueError("List of violinplot statistics and quantiles values"
                         " must have the same length")

    # Zip x and quantiles
    for (x, q) in zip(X, quantiles):
        # Dictionary of results for this distribution
        stats = {}

        # Calculate basic stats for the distribution
        min_val = np.min(x)
        max_val = np.max(x)
        quantile_val = np.percentile(x, 100 * q)

        # Evaluate the kernel density estimate
        coords = np.linspace(min_val, max_val, points)
        stats['vals'] = method(x, coords)
        stats['coords'] = coords

        # Store additional statistics for this distribution
        stats['mean'] = np.mean(x)
        stats['median'] = np.median(x)
        stats['min'] = min_val
        stats['max'] = max_val
        stats['quantiles'] = np.atleast_1d(quantile_val)

        # Append to output
        vpstats.append(stats)

    return vpstats


def pts_to_prestep(x, *args):
    """
    Convert continuous line to pre-steps.

    Given a set of ``N`` points, convert to ``2N - 1`` points, which when
    connected linearly give a step function which changes values at the
    beginning of the intervals.

    Parameters
    ----------
    x : array
        The x location of the steps. May be empty.

    y1, ..., yp : array
        y arrays to be turned into steps; all must be the same length as ``x``.

    Returns
    -------
    array
        The x and y values converted to steps in the same order as the input;
        can be unpacked as ``x_out, y1_out, ..., yp_out``.  If the input is
        length ``N``, each of these arrays will be length ``2N + 1``. For
        ``N=0``, the length will be 0.

    Examples
    --------
    >>> x_s, y1_s, y2_s = pts_to_prestep(x, y1, y2)
    """
    steps = np.zeros((1 + len(args), max(2 * len(x) - 1, 0)))
    # In all `pts_to_*step` functions, only assign once using *x* and *args*,
    # as converting to an array may be expensive.
    steps[0, 0::2] = x
    steps[0, 1::2] = steps[0, 0:-2:2]
    steps[1:, 0::2] = args
    steps[1:, 1::2] = steps[1:, 2::2]
    return steps


def pts_to_poststep(x, *args):
    """
    Convert continuous line to post-steps.

    Given a set of ``N`` points convert to ``2N + 1`` points, which when
    connected linearly give a step function which changes values at the end of
    the intervals.

    Parameters
    ----------
    x : array
        The x location of the steps. May be empty.

    y1, ..., yp : array
        y arrays to be turned into steps; all must be the same length as ``x``.

    Returns
    -------
    array
        The x and y values converted to steps in the same order as the input;
        can be unpacked as ``x_out, y1_out, ..., yp_out``.  If the input is
        length ``N``, each of these arrays will be length ``2N + 1``. For
        ``N=0``, the length will be 0.

    Examples
    --------
    >>> x_s, y1_s, y2_s = pts_to_poststep(x, y1, y2)
    """
    steps = np.zeros((1 + len(args), max(2 * len(x) - 1, 0)))
    steps[0, 0::2] = x
    steps[0, 1::2] = steps[0, 2::2]
    steps[1:, 0::2] = args
    steps[1:, 1::2] = steps[1:, 0:-2:2]
    return steps


def pts_to_midstep(x, *args):
    """
    Convert continuous line to mid-steps.

    Given a set of ``N`` points convert to ``2N`` points which when connected
    linearly give a step function which changes values at the middle of the
    intervals.

    Parameters
    ----------
    x : array
        The x location of the steps. May be empty.

    y1, ..., yp : array
        y arrays to be turned into steps; all must be the same length as
        ``x``.

    Returns
    -------
    array
        The x and y values converted to steps in the same order as the input;
        can be unpacked as ``x_out, y1_out, ..., yp_out``.  If the input is
        length ``N``, each of these arrays will be length ``2N``.

    Examples
    --------
    >>> x_s, y1_s, y2_s = pts_to_midstep(x, y1, y2)
    """
    steps = np.zeros((1 + len(args), 2 * len(x)))
    x = np.asanyarray(x)
    steps[0, 1:-1:2] = steps[0, 2::2] = (x[:-1] + x[1:]) / 2
    steps[0, :1] = x[:1]  # Also works for zero-sized input.
    steps[0, -1:] = x[-1:]
    steps[1:, 0::2] = args
    steps[1:, 1::2] = steps[1:, 0::2]
    return steps


STEP_LOOKUP_MAP = {'default': lambda x, y: (x, y),
                   'steps': pts_to_prestep,
                   'steps-pre': pts_to_prestep,
                   'steps-post': pts_to_poststep,
                   'steps-mid': pts_to_midstep}


def index_of(y):
    """
    A helper function to create reasonable x values for the given *y*.

    This is used for plotting (x, y) if x values are not explicitly given.

    First try ``y.index`` (assuming *y* is a `pandas.Series`), if that
    fails, use ``range(len(y))``.

    This will be extended in the future to deal with more types of
    labeled data.

    Parameters
    ----------
    y : float or array-like

    Returns
    -------
    x, y : ndarray
       The x and y values to plot.
    """
    try:
        return y.index.to_numpy(), y.to_numpy()
    except AttributeError:
        pass
    try:
        y = _check_1d(y)
    except (VisibleDeprecationWarning, ValueError):
        # NumPy 1.19 will warn on ragged input, and we can't actually use it.
        pass
    else:
        return np.arange(y.shape[0], dtype=float), y
    raise ValueError('Input could not be cast to an at-least-1D NumPy array')


def safe_first_element(obj):
    """
    Return the first element in *obj*.

    This is a type-independent way of obtaining the first element,
    supporting both index access and the iterator protocol.
    """
    if isinstance(obj, collections.abc.Iterator):
        # needed to accept `array.flat` as input.
        # np.flatiter reports as an instance of collections.Iterator but can still be
        # indexed via []. This has the side effect of re-setting the iterator, but
        # that is acceptable.
        try:
            return obj[0]
        except TypeError:
            pass
        raise RuntimeError("matplotlib does not support generators as input")
    return next(iter(obj))


def _safe_first_finite(obj):
    """
    Return the first finite element in *obj* if one is available and skip_nonfinite is
    True. Otherwise, return the first element.

    This is a method for internal use.

    This is a type-independent way of obtaining the first finite element, supporting
    both index access and the iterator protocol.
    """
    def safe_isfinite(val):
        if val is None:
            return False
        try:
            return math.isfinite(val)
        except (TypeError, ValueError):
            # if the outer object is 2d, then val is a 1d array, and
            # - math.isfinite(numpy.zeros(3)) raises TypeError
            # - math.isfinite(torch.zeros(3)) raises ValueError
            pass
        try:
            return np.isfinite(val) if np.isscalar(val) else True
        except TypeError:
            # This is something that NumPy cannot make heads or tails of,
            # assume "finite"
            return True

    if isinstance(obj, np.flatiter):
        # TODO do the finite filtering on this
        return obj[0]
    elif isinstance(obj, collections.abc.Iterator):
        raise RuntimeError("matplotlib does not support generators as input")
    else:
        for val in obj:
            if safe_isfinite(val):
                return val
        return safe_first_element(obj)


def sanitize_sequence(data):
    """
    Convert dictview objects to list. Other inputs are returned unchanged.
    """
    return (list(data) if isinstance(data, collections.abc.MappingView)
            else data)


def normalize_kwargs(kw, alias_mapping=None):
    """
    Helper function to normalize kwarg inputs.

    Parameters
    ----------
    kw : dict or None
        A dict of keyword arguments.  None is explicitly supported and treated
        as an empty dict, to support functions with an optional parameter of
        the form ``props=None``.

    alias_mapping : dict or Artist subclass or Artist instance, optional
        A mapping between a canonical name to a list of aliases, in order of
        precedence from lowest to highest.

        If the canonical value is not in the list it is assumed to have the
        highest priority.

        If an Artist subclass or instance is passed, use its properties alias
        mapping.

    Raises
    ------
    TypeError
        To match what Python raises if invalid arguments/keyword arguments are
        passed to a callable.
    """
    from matplotlib.artist import Artist

    if kw is None:
        return {}

    # deal with default value of alias_mapping
    if alias_mapping is None:
        alias_mapping = {}
    elif (isinstance(alias_mapping, type) and issubclass(alias_mapping, Artist)
          or isinstance(alias_mapping, Artist)):
        alias_mapping = getattr(alias_mapping, "_alias_map", {})

    to_canonical = {alias: canonical
                    for canonical, alias_list in alias_mapping.items()
                    for alias in alias_list}
    canonical_to_seen = {}
    ret = {}  # output dictionary

    for k, v in kw.items():
        canonical = to_canonical.get(k, k)
        if canonical in canonical_to_seen:
            raise TypeError(f"Got both {canonical_to_seen[canonical]!r} and "
                            f"{k!r}, which are aliases of one another")
        canonical_to_seen[canonical] = k
        ret[canonical] = v

    return ret


@contextlib.contextmanager
def _lock_path(path):
    """
    Context manager for locking a path.

    Usage::

        with _lock_path(path):
            ...

    Another thread or process that attempts to lock the same path will wait
    until this context manager is exited.

    The lock is implemented by creating a temporary file in the parent
    directory, so that directory must exist and be writable.
    """
    path = Path(path)
    lock_path = path.with_name(path.name + ".matplotlib-lock")
    retries = 50
    sleeptime = 0.1
    for _ in range(retries):
        try:
            with lock_path.open("xb"):
                break
        except FileExistsError:
            time.sleep(sleeptime)
    else:
        raise TimeoutError("""\
Lock error: Matplotlib failed to acquire the following lock file:
    {}
This maybe due to another process holding this lock file.  If you are sure no
other Matplotlib process is running, remove this file and try again.""".format(
            lock_path))
    try:
        yield
    finally:
        lock_path.unlink()


def _topmost_artist(
        artists,
        _cached_max=functools.partial(max, key=operator.attrgetter("zorder"))):
    """
    Get the topmost artist of a list.

    In case of a tie, return the *last* of the tied artists, as it will be
    drawn on top of the others. `max` returns the first maximum in case of
    ties, so we need to iterate over the list in reverse order.
    """
    return _cached_max(reversed(artists))


def _str_equal(obj, s):
    """
    Return whether *obj* is a string equal to string *s*.

    This helper solely exists to handle the case where *obj* is a numpy array,
    because in such cases, a naive ``obj == s`` would yield an array, which
    cannot be used in a boolean context.
    """
    return isinstance(obj, str) and obj == s


def _str_lower_equal(obj, s):
    """
    Return whether *obj* is a string equal, when lowercased, to string *s*.

    This helper solely exists to handle the case where *obj* is a numpy array,
    because in such cases, a naive ``obj == s`` would yield an array, which
    cannot be used in a boolean context.
    """
    return isinstance(obj, str) and obj.lower() == s


def _array_perimeter(arr):
    """
    Get the elements on the perimeter of *arr*.

    Parameters
    ----------
    arr : ndarray, shape (M, N)
        The input array.

    Returns
    -------
    ndarray, shape (2*(M - 1) + 2*(N - 1),)
        The elements on the perimeter of the array::

           [arr[0, 0], ..., arr[0, -1], ..., arr[-1, -1], ..., arr[-1, 0], ...]

    Examples
    --------
    >>> i, j = np.ogrid[:3, :4]
    >>> a = i*10 + j
    >>> a
    array([[ 0,  1,  2,  3],
           [10, 11, 12, 13],
           [20, 21, 22, 23]])
    >>> _array_perimeter(a)
    array([ 0,  1,  2,  3, 13, 23, 22, 21, 20, 10])
    """
    # note we use Python's half-open ranges to avoid repeating
    # the corners
    forward = np.s_[0:-1]      # [0 ... -1)
    backward = np.s_[-1:0:-1]  # [-1 ... 0)
    return np.concatenate((
        arr[0, forward],
        arr[forward, -1],
        arr[-1, backward],
        arr[backward, 0],
    ))


def _unfold(arr, axis, size, step):
    """
    Append an extra dimension containing sliding windows along *axis*.

    All windows are of size *size* and begin with every *step* elements.

    Parameters
    ----------
    arr : ndarray, shape (N_1, ..., N_k)
        The input array
    axis : int
        Axis along which the windows are extracted
    size : int
        Size of the windows
    step : int
        Stride between first elements of subsequent windows.

    Returns
    -------
    ndarray, shape (N_1, ..., 1 + (N_axis-size)/step, ..., N_k, size)

    Examples
    --------
    >>> i, j = np.ogrid[:3, :7]
    >>> a = i*10 + j
    >>> a
    array([[ 0,  1,  2,  3,  4,  5,  6],
           [10, 11, 12, 13, 14, 15, 16],
           [20, 21, 22, 23, 24, 25, 26]])
    >>> _unfold(a, axis=1, size=3, step=2)
    array([[[ 0,  1,  2],
            [ 2,  3,  4],
            [ 4,  5,  6]],
           [[10, 11, 12],
            [12, 13, 14],
            [14, 15, 16]],
           [[20, 21, 22],
            [22, 23, 24],
            [24, 25, 26]]])
    """
    new_shape = [*arr.shape, size]
    new_strides = [*arr.strides, arr.strides[axis]]
    new_shape[axis] = (new_shape[axis] - size) // step + 1
    new_strides[axis] = new_strides[axis] * step
    return np.lib.stride_tricks.as_strided(arr,
                                           shape=new_shape,
                                           strides=new_strides,
                                           writeable=False)


def _array_patch_perimeters(x, rstride, cstride):
    """
    Extract perimeters of patches from *arr*.

    Extracted patches are of size (*rstride* + 1) x (*cstride* + 1) and
    share perimeters with their neighbors. The ordering of the vertices matches
    that returned by ``_array_perimeter``.

    Parameters
    ----------
    x : ndarray, shape (N, M)
        Input array
    rstride : int
        Vertical (row) stride between corresponding elements of each patch
    cstride : int
        Horizontal (column) stride between corresponding elements of each patch

    Returns
    -------
    ndarray, shape (N/rstride * M/cstride, 2 * (rstride + cstride))
    """
    assert rstride > 0 and cstride > 0
    assert (x.shape[0] - 1) % rstride == 0
    assert (x.shape[1] - 1) % cstride == 0
    # We build up each perimeter from four half-open intervals. Here is an
    # illustrated explanation for rstride == cstride == 3
    #
    #       T T T R
    #       L     R
    #       L     R
    #       L B B B
    #
    # where T means that this element will be in the top array, R for right,
    # B for bottom and L for left. Each of the arrays below has a shape of:
    #
    #    (number of perimeters that can be extracted vertically,
    #     number of perimeters that can be extracted horizontally,
    #     cstride for top and bottom and rstride for left and right)
    #
    # Note that _unfold doesn't incur any memory copies, so the only costly
    # operation here is the np.concatenate.
    top = _unfold(x[:-1:rstride, :-1], 1, cstride, cstride)
    bottom = _unfold(x[rstride::rstride, 1:], 1, cstride, cstride)[..., ::-1]
    right = _unfold(x[:-1, cstride::cstride], 0, rstride, rstride)
    left = _unfold(x[1:, :-1:cstride], 0, rstride, rstride)[..., ::-1]
    return (np.concatenate((top, right, bottom, left), axis=2)
              .reshape(-1, 2 * (rstride + cstride)))


@contextlib.contextmanager
def _setattr_cm(obj, **kwargs):
    """
    Temporarily set some attributes; restore original state at context exit.
    """
    sentinel = object()
    origs = {}
    for attr in kwargs:
        orig = getattr(obj, attr, sentinel)
        if attr in obj.__dict__ or orig is sentinel:
            # if we are pulling from the instance dict or the object
            # does not have this attribute we can trust the above
            origs[attr] = orig
        else:
            # if the attribute is not in the instance dict it must be
            # from the class level
            cls_orig = getattr(type(obj), attr)
            # if we are dealing with a property (but not a general descriptor)
            # we want to set the original value back.
            if isinstance(cls_orig, property):
                origs[attr] = orig
            # otherwise this is _something_ we are going to shadow at
            # the instance dict level from higher up in the MRO.  We
            # are going to assume we can delattr(obj, attr) to clean
            # up after ourselves.  It is possible that this code will
            # fail if used with a non-property custom descriptor which
            # implements __set__ (and __delete__ does not act like a
            # stack).  However, this is an internal tool and we do not
            # currently have any custom descriptors.
            else:
                origs[attr] = sentinel

    try:
        for attr, val in kwargs.items():
            setattr(obj, attr, val)
        yield
    finally:
        for attr, orig in origs.items():
            if orig is sentinel:
                delattr(obj, attr)
            else:
                setattr(obj, attr, orig)


class _OrderedSet(collections.abc.MutableSet):
    def __init__(self):
        self._od = collections.OrderedDict()

    def __contains__(self, key):
        return key in self._od

    def __iter__(self):
        return iter(self._od)

    def __len__(self):
        return len(self._od)

    def add(self, key):
        self._od.pop(key, None)
        self._od[key] = None

    def discard(self, key):
        self._od.pop(key, None)


# Agg's buffers are unmultiplied RGBA8888, which neither PyQt<=5.1 nor cairo
# support; however, both do support premultiplied ARGB32.


def _premultiplied_argb32_to_unmultiplied_rgba8888(buf):
    """
    Convert a premultiplied ARGB32 buffer to an unmultiplied RGBA8888 buffer.
    """
    rgba = np.take(  # .take() ensures C-contiguity of the result.
        buf,
        [2, 1, 0, 3] if sys.byteorder == "little" else [1, 2, 3, 0], axis=2)
    rgb = rgba[..., :-1]
    alpha = rgba[..., -1]
    # Un-premultiply alpha.  The formula is the same as in cairo-png.c.
    mask = alpha != 0
    for channel in np.rollaxis(rgb, -1):
        channel[mask] = (
            (channel[mask].astype(int) * 255 + alpha[mask] // 2)
            // alpha[mask])
    return rgba


def _unmultiplied_rgba8888_to_premultiplied_argb32(rgba8888):
    """
    Convert an unmultiplied RGBA8888 buffer to a premultiplied ARGB32 buffer.
    """
    if sys.byteorder == "little":
        argb32 = np.take(rgba8888, [2, 1, 0, 3], axis=2)
        rgb24 = argb32[..., :-1]
        alpha8 = argb32[..., -1:]
    else:
        argb32 = np.take(rgba8888, [3, 0, 1, 2], axis=2)
        alpha8 = argb32[..., :1]
        rgb24 = argb32[..., 1:]
    # Only bother premultiplying when the alpha channel is not fully opaque,
    # as the cost is not negligible.  The unsafe cast is needed to do the
    # multiplication in-place in an integer buffer.
    if alpha8.min() != 0xff:
        np.multiply(rgb24, alpha8 / 0xff, out=rgb24, casting="unsafe")
    return argb32


def _get_nonzero_slices(buf):
    """
    Return the bounds of the nonzero region of a 2D array as a pair of slices.

    ``buf[_get_nonzero_slices(buf)]`` is the smallest sub-rectangle in *buf*
    that encloses all non-zero entries in *buf*.  If *buf* is fully zero, then
    ``(slice(0, 0), slice(0, 0))`` is returned.
    """
    x_nz, = buf.any(axis=0).nonzero()
    y_nz, = buf.any(axis=1).nonzero()
    if len(x_nz) and len(y_nz):
        l, r = x_nz[[0, -1]]
        b, t = y_nz[[0, -1]]
        return slice(b, t + 1), slice(l, r + 1)
    else:
        return slice(0, 0), slice(0, 0)


def _pformat_subprocess(command):
    """Pretty-format a subprocess command for printing/logging purposes."""
    return (command if isinstance(command, str)
            else " ".join(shlex.quote(os.fspath(arg)) for arg in command))


def _check_and_log_subprocess(command, logger, **kwargs):
    """
    Run *command*, returning its stdout output if it succeeds.

    If it fails (exits with nonzero return code), raise an exception whose text
    includes the failed command and captured stdout and stderr output.

    Regardless of the return code, the command is logged at DEBUG level on
    *logger*.  In case of success, the output is likewise logged.
    """
    logger.debug('%s', _pformat_subprocess(command))
    proc = subprocess.run(command, capture_output=True, **kwargs)
    if proc.returncode:
        stdout = proc.stdout
        if isinstance(stdout, bytes):
            stdout = stdout.decode()
        stderr = proc.stderr
        if isinstance(stderr, bytes):
            stderr = stderr.decode()
        raise RuntimeError(
            f"The command\n"
            f"    {_pformat_subprocess(command)}\n"
            f"failed and generated the following output:\n"
            f"{stdout}\n"
            f"and the following error:\n"
            f"{stderr}")
    if proc.stdout:
        logger.debug("stdout:\n%s", proc.stdout)
    if proc.stderr:
        logger.debug("stderr:\n%s", proc.stderr)
    return proc.stdout


def _setup_new_guiapp():
    """
    Perform OS-dependent setup when Matplotlib creates a new GUI application.
    """
    # Windows: If not explicit app user model id has been set yet (so we're not
    # already embedded), then set it to "matplotlib", so that taskbar icons are
    # correct.
    try:
        _c_internal_utils.Win32_GetCurrentProcessExplicitAppUserModelID()
    except OSError:
        _c_internal_utils.Win32_SetCurrentProcessExplicitAppUserModelID(
            "matplotlib")


def _format_approx(number, precision):
    """
    Format the number with at most the number of decimals given as precision.
    Remove trailing zeros and possibly the decimal point.
    """
    return f'{number:.{precision}f}'.rstrip('0').rstrip('.') or '0'


def _g_sig_digits(value, delta):
    """
    Return the number of significant digits to %g-format *value*, assuming that
    it is known with an error of *delta*.
    """
    if delta == 0:
        if value == 0:
            # if both value and delta are 0, np.spacing below returns 5e-324
            # which results in rather silly results
            return 3
        # delta = 0 may occur when trying to format values over a tiny range;
        # in that case, replace it by the distance to the closest float.
        delta = abs(np.spacing(value))
    # If e.g. value = 45.67 and delta = 0.02, then we want to round to 2 digits
    # after the decimal point (floor(log10(0.02)) = -2); 45.67 contributes 2
    # digits before the decimal point (floor(log10(45.67)) + 1 = 2): the total
    # is 4 significant digits.  A value of 0 contributes 1 "digit" before the
    # decimal point.
    # For inf or nan, the precision doesn't matter.
    return max(
        0,
        (math.floor(math.log10(abs(value))) + 1 if value else 1)
        - math.floor(math.log10(delta))) if math.isfinite(value) else 0


def _unikey_or_keysym_to_mplkey(unikey, keysym):
    """
    Convert a Unicode key or X keysym to a Matplotlib key name.

    The Unicode key is checked first; this avoids having to list most printable
    keysyms such as ``EuroSign``.
    """
    # For non-printable characters, gtk3 passes "\0" whereas tk passes an "".
    if unikey and unikey.isprintable():
        return unikey
    key = keysym.lower()
    if key.startswith("kp_"):  # keypad_x (including kp_enter).
        key = key[3:]
    if key.startswith("page_"):  # page_{up,down}
        key = key.replace("page_", "page")
    if key.endswith(("_l", "_r")):  # alt_l, ctrl_l, shift_l.
        key = key[:-2]
    if sys.platform == "darwin" and key == "meta":
        # meta should be reported as command on mac
        key = "cmd"
    key = {
        "return": "enter",
        "prior": "pageup",  # Used by tk.
        "next": "pagedown",  # Used by tk.
    }.get(key, key)
    return key


@functools.cache
def _make_class_factory(mixin_class, fmt, attr_name=None):
    """
    Return a function that creates picklable classes inheriting from a mixin.

    After ::

        factory = _make_class_factory(FooMixin, fmt, attr_name)
        FooAxes = factory(Axes)

    ``Foo`` is a class that inherits from ``FooMixin`` and ``Axes`` and **is
    picklable** (picklability is what differentiates this from a plain call to
    `type`).  Its ``__name__`` is set to ``fmt.format(Axes.__name__)`` and the
    base class is stored in the ``attr_name`` attribute, if not None.

    Moreover, the return value of ``factory`` is memoized: calls with the same
    ``Axes`` class always return the same subclass.
    """

    @functools.cache
    def class_factory(axes_class):
        # if we have already wrapped this class, declare victory!
        if issubclass(axes_class, mixin_class):
            return axes_class

        # The parameter is named "axes_class" for backcompat but is really just
        # a base class; no axes semantics are used.
        base_class = axes_class

        class subcls(mixin_class, base_class):
            # Better approximation than __module__ = "matplotlib.cbook".
            __module__ = mixin_class.__module__

            def __reduce__(self):
                return (_picklable_class_constructor,
                        (mixin_class, fmt, attr_name, base_class),
                        self.__getstate__())

        subcls.__name__ = subcls.__qualname__ = fmt.format(base_class.__name__)
        if attr_name is not None:
            setattr(subcls, attr_name, base_class)
        return subcls

    class_factory.__module__ = mixin_class.__module__
    return class_factory


def _picklable_class_constructor(mixin_class, fmt, attr_name, base_class):
    """Internal helper for _make_class_factory."""
    factory = _make_class_factory(mixin_class, fmt, attr_name)
    cls = factory(base_class)
    return cls.__new__(cls)


def _is_torch_array(x):
    """Check if 'x' is a PyTorch Tensor."""
    try:
        # we're intentionally not attempting to import torch. If somebody
        # has created a torch array, torch should already be in sys.modules
        return isinstance(x, sys.modules['torch'].Tensor)
    except Exception:  # TypeError, KeyError, AttributeError, maybe others?
        # we're attempting to access attributes on imported modules which
        # may have arbitrary user code, so we deliberately catch all exceptions
        return False


def _is_jax_array(x):
    """Check if 'x' is a JAX Array."""
    try:
        # we're intentionally not attempting to import jax. If somebody
        # has created a jax array, jax should already be in sys.modules
        return isinstance(x, sys.modules['jax'].Array)
    except Exception:  # TypeError, KeyError, AttributeError, maybe others?
        # we're attempting to access attributes on imported modules which
        # may have arbitrary user code, so we deliberately catch all exceptions
        return False


def _is_tensorflow_array(x):
    """Check if 'x' is a TensorFlow Tensor or Variable."""
    try:
        # we're intentionally not attempting to import TensorFlow. If somebody
        # has created a TensorFlow array, TensorFlow should already be in sys.modules
        # we use `is_tensor` to not depend on the class structure of TensorFlow
        # arrays, as `tf.Variables` are not instances of `tf.Tensor`
        # (they both convert the same way)
        return isinstance(x, sys.modules['tensorflow'].is_tensor(x))
    except Exception:  # TypeError, KeyError, AttributeError, maybe others?
        # we're attempting to access attributes on imported modules which
        # may have arbitrary user code, so we deliberately catch all exceptions
        return False


def _unpack_to_numpy(x):
    """Internal helper to extract data from e.g. pandas and xarray objects."""
    if isinstance(x, np.ndarray):
        # If numpy, return directly
        return x
    if hasattr(x, 'to_numpy'):
        # Assume that any to_numpy() method actually returns a numpy array
        return x.to_numpy()
    if hasattr(x, 'values'):
        xtmp = x.values
        # For example a dict has a 'values' attribute, but it is not a property
        # so in this case we do not want to return a function
        if isinstance(xtmp, np.ndarray):
            return xtmp
    if _is_torch_array(x) or _is_jax_array(x) or _is_tensorflow_array(x):
        # using np.asarray() instead of explicitly __array__(), as the latter is
        # only _one_ of many methods, and it's the last resort, see also
        # https://numpy.org/devdocs/user/basics.interoperability.html#using-arbitrary-objects-in-numpy
        # therefore, let arrays do better if they can
        xtmp = np.asarray(x)

        # In case np.asarray method does not return a numpy array in future
        if isinstance(xtmp, np.ndarray):
            return xtmp
    return x


def _auto_format_str(fmt, value):
    """
    Apply *value* to the format string *fmt*.

    This works both with unnamed %-style formatting and
    unnamed {}-style formatting. %-style formatting has priority.
    If *fmt* is %-style formattable that will be used. Otherwise,
    {}-formatting is applied. Strings without formatting placeholders
    are passed through as is.

    Examples
    --------
    >>> _auto_format_str('%.2f m', 0.2)
    '0.20 m'
    >>> _auto_format_str('{} m', 0.2)
    '0.2 m'
    >>> _auto_format_str('const', 0.2)
    'const'
    >>> _auto_format_str('%d or {}', 0.2)
    '0 or {}'
    """
    try:
        return fmt % (value,)
    except (TypeError, ValueError):
        return fmt.format(value)


def _is_pandas_dataframe(x):
    """Check if 'x' is a Pandas DataFrame."""
    try:
        # we're intentionally not attempting to import Pandas. If somebody
        # has created a Pandas DataFrame, Pandas should already be in sys.modules
        return isinstance(x, sys.modules['pandas'].DataFrame)
    except Exception:  # TypeError, KeyError, AttributeError, maybe others?
        # we're attempting to access attributes on imported modules which
        # may have arbitrary user code, so we deliberately catch all exceptions
        return False

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\lib\llmfn_post_process.py ===
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
"""Signatures for post-processing functions and other common definitions."""
from __future__ import annotations

from typing import Any, Callable, Sequence, Tuple

from google.generativeai.notebook.lib import llmfn_output_row


class PostProcessExecutionError(RuntimeError):
    """An error while executing a post-processing command."""


# A batch-process function takes a batch of rows, and returns a sequence of
# indices representing which rows to keep.
# This can be used to implement operations such as filtering and sorting.
#
# Requires:
# - Indices must be in the range [0, len(input rows)).
LLMFnPostProcessBatchReorderFn = Callable[
    [Sequence[llmfn_output_row.LLMFnOutputRowView]],
    Sequence[int],
]

# An add function takes a batch of rows and returns a sequence of values to
# be added as new columns.
#
# Requires:
# - Output sequence must be exactly the same length as number of rows.
LLMFnPostProcessBatchAddFn = Callable[
    [Sequence[llmfn_output_row.LLMFnOutputRowView]], Sequence[Any]
]

# A replace function takes a batch of rows and returns a sequence of values
# to replace the existing results.
#
# Requires:
# - Output sequence must be exactly the same length as number of rows.
# - Return type must match the result_type of LLMFnOutputRow.
LLMFnPostProcessBatchReplaceFn = Callable[
    [Sequence[llmfn_output_row.LLMFnOutputRowView]], Sequence[Any]
]

# An add function takes a batch of pairs of rows and returns a sequence of
# values to be added as new columns.
#
# This is used for LLMCompareFunction.
#
# Requires:
# - Output sequence must be exactly the same length as number of rows.
LLMCompareFnPostProcessBatchAddFn = Callable[
    [
        Sequence[
            Tuple[
                llmfn_output_row.LLMFnOutputRowView,
                llmfn_output_row.LLMFnOutputRowView,
            ]
        ]
    ],
    Sequence[Any],
]

# === NexusCore/openenv\Lib\site-packages\fontTools\feaLib\parser.py ===
from fontTools.feaLib.error import FeatureLibError
from fontTools.feaLib.lexer import Lexer, IncludingLexer, NonIncludingLexer
from fontTools.feaLib.variableScalar import VariableScalar
from fontTools.misc.encodingTools import getEncoding
from fontTools.misc.textTools import bytechr, tobytes, tostr
import fontTools.feaLib.ast as ast
import logging
import os
import re


log = logging.getLogger(__name__)


class Parser(object):
    """Initializes a Parser object.

    Example:

        .. code:: python

            from fontTools.feaLib.parser import Parser
            parser = Parser(file, font.getReverseGlyphMap())
            parsetree = parser.parse()

    Note: the ``glyphNames`` iterable serves a double role to help distinguish
    glyph names from ranges in the presence of hyphens and to ensure that glyph
    names referenced in a feature file are actually part of a font's glyph set.
    If the iterable is left empty, no glyph name in glyph set checking takes
    place, and all glyph tokens containing hyphens are treated as literal glyph
    names, not as ranges. (Adding a space around the hyphen can, in any case,
    help to disambiguate ranges from glyph names containing hyphens.)

    By default, the parser will follow ``include()`` statements in the feature
    file. To turn this off, pass ``followIncludes=False``. Pass a directory string as
    ``includeDir`` to explicitly declare a directory to search included feature files
    in.
    """

    extensions = {}
    ast = ast
    SS_FEATURE_TAGS = {"ss%02d" % i for i in range(1, 20 + 1)}
    CV_FEATURE_TAGS = {"cv%02d" % i for i in range(1, 99 + 1)}

    def __init__(
        self, featurefile, glyphNames=(), followIncludes=True, includeDir=None, **kwargs
    ):
        if "glyphMap" in kwargs:
            from fontTools.misc.loggingTools import deprecateArgument

            deprecateArgument("glyphMap", "use 'glyphNames' (iterable) instead")
            if glyphNames:
                raise TypeError(
                    "'glyphNames' and (deprecated) 'glyphMap' are " "mutually exclusive"
                )
            glyphNames = kwargs.pop("glyphMap")
        if kwargs:
            raise TypeError(
                "unsupported keyword argument%s: %s"
                % ("" if len(kwargs) == 1 else "s", ", ".join(repr(k) for k in kwargs))
            )

        self.glyphNames_ = set(glyphNames)
        self.doc_ = self.ast.FeatureFile()
        self.anchors_ = SymbolTable()
        self.glyphclasses_ = SymbolTable()
        self.lookups_ = SymbolTable()
        self.valuerecords_ = SymbolTable()
        self.symbol_tables_ = {self.anchors_, self.valuerecords_}
        self.next_token_type_, self.next_token_ = (None, None)
        self.cur_comments_ = []
        self.next_token_location_ = None
        lexerClass = IncludingLexer if followIncludes else NonIncludingLexer
        self.lexer_ = lexerClass(featurefile, includeDir=includeDir)
        self.missing = {}
        self.advance_lexer_(comments=True)

    def parse(self):
        """Parse the file, and return a :class:`fontTools.feaLib.ast.FeatureFile`
        object representing the root of the abstract syntax tree containing the
        parsed contents of the file."""
        statements = self.doc_.statements
        while self.next_token_type_ is not None or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.is_cur_keyword_("include"):
                statements.append(self.parse_include_())
            elif self.cur_token_type_ is Lexer.GLYPHCLASS:
                statements.append(self.parse_glyphclass_definition_())
            elif self.is_cur_keyword_(("anon", "anonymous")):
                statements.append(self.parse_anonymous_())
            elif self.is_cur_keyword_("anchorDef"):
                statements.append(self.parse_anchordef_())
            elif self.is_cur_keyword_("languagesystem"):
                statements.append(self.parse_languagesystem_())
            elif self.is_cur_keyword_("lookup"):
                statements.append(self.parse_lookup_(vertical=False))
            elif self.is_cur_keyword_("markClass"):
                statements.append(self.parse_markClass_())
            elif self.is_cur_keyword_("feature"):
                statements.append(self.parse_feature_block_())
            elif self.is_cur_keyword_("conditionset"):
                statements.append(self.parse_conditionset_())
            elif self.is_cur_keyword_("variation"):
                statements.append(self.parse_feature_block_(variation=True))
            elif self.is_cur_keyword_("table"):
                statements.append(self.parse_table_())
            elif self.is_cur_keyword_("valueRecordDef"):
                statements.append(self.parse_valuerecord_definition_(vertical=False))
            elif (
                self.cur_token_type_ is Lexer.NAME
                and self.cur_token_ in self.extensions
            ):
                statements.append(self.extensions[self.cur_token_](self))
            elif self.cur_token_type_ is Lexer.SYMBOL and self.cur_token_ == ";":
                continue
            else:
                raise FeatureLibError(
                    "Expected feature, languagesystem, lookup, markClass, "
                    'table, or glyph class definition, got {} "{}"'.format(
                        self.cur_token_type_, self.cur_token_
                    ),
                    self.cur_token_location_,
                )
        # Report any missing glyphs at the end of parsing
        if self.missing:
            error = [
                " %s (first found at %s)" % (name, loc)
                for name, loc in self.missing.items()
            ]
            raise FeatureLibError(
                "The following glyph names are referenced but are missing from the "
                "glyph set:\n" + ("\n".join(error)),
                None,
            )
        return self.doc_

    def parse_anchor_(self):
        # Parses an anchor in any of the four formats given in the feature
        # file specification (2.e.vii).
        self.expect_symbol_("<")
        self.expect_keyword_("anchor")
        location = self.cur_token_location_

        if self.next_token_ == "NULL":  # Format D
            self.expect_keyword_("NULL")
            self.expect_symbol_(">")
            return None

        if self.next_token_type_ == Lexer.NAME:  # Format E
            name = self.expect_name_()
            anchordef = self.anchors_.resolve(name)
            if anchordef is None:
                raise FeatureLibError(
                    'Unknown anchor "%s"' % name, self.cur_token_location_
                )
            self.expect_symbol_(">")
            return self.ast.Anchor(
                anchordef.x,
                anchordef.y,
                name=name,
                contourpoint=anchordef.contourpoint,
                xDeviceTable=None,
                yDeviceTable=None,
                location=location,
            )

        x, y = self.expect_number_(variable=True), self.expect_number_(variable=True)

        contourpoint = None
        if self.next_token_ == "contourpoint":  # Format B
            self.expect_keyword_("contourpoint")
            contourpoint = self.expect_number_()

        if self.next_token_ == "<":  # Format C
            xDeviceTable = self.parse_device_()
            yDeviceTable = self.parse_device_()
        else:
            xDeviceTable, yDeviceTable = None, None

        self.expect_symbol_(">")
        return self.ast.Anchor(
            x,
            y,
            name=None,
            contourpoint=contourpoint,
            xDeviceTable=xDeviceTable,
            yDeviceTable=yDeviceTable,
            location=location,
        )

    def parse_anchor_marks_(self):
        # Parses a sequence of ``[<anchor> mark @MARKCLASS]*.``
        anchorMarks = []  # [(self.ast.Anchor, markClassName)*]
        while self.next_token_ == "<":
            anchor = self.parse_anchor_()
            if anchor is None and self.next_token_ != "mark":
                continue  # <anchor NULL> without mark, eg. in GPOS type 5
            self.expect_keyword_("mark")
            markClass = self.expect_markClass_reference_()
            anchorMarks.append((anchor, markClass))
        return anchorMarks

    def parse_anchordef_(self):
        # Parses a named anchor definition (`section 2.e.viii <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#2.e.vii>`_).
        assert self.is_cur_keyword_("anchorDef")
        location = self.cur_token_location_
        x, y = self.expect_number_(), self.expect_number_()
        contourpoint = None
        if self.next_token_ == "contourpoint":
            self.expect_keyword_("contourpoint")
            contourpoint = self.expect_number_()
        name = self.expect_name_()
        self.expect_symbol_(";")
        anchordef = self.ast.AnchorDefinition(
            name, x, y, contourpoint=contourpoint, location=location
        )
        self.anchors_.define(name, anchordef)
        return anchordef

    def parse_anonymous_(self):
        # Parses an anonymous data block (`section 10 <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#10>`_).
        assert self.is_cur_keyword_(("anon", "anonymous"))
        tag = self.expect_tag_()
        _, content, location = self.lexer_.scan_anonymous_block(tag)
        self.advance_lexer_()
        self.expect_symbol_("}")
        end_tag = self.expect_tag_()
        assert tag == end_tag, "bad splitting in Lexer.scan_anonymous_block()"
        self.expect_symbol_(";")
        return self.ast.AnonymousBlock(tag, content, location=location)

    def parse_attach_(self):
        # Parses a GDEF Attach statement (`section 9.b <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#9.b>`_)
        assert self.is_cur_keyword_("Attach")
        location = self.cur_token_location_
        glyphs = self.parse_glyphclass_(accept_glyphname=True)
        contourPoints = {self.expect_number_()}
        while self.next_token_ != ";":
            contourPoints.add(self.expect_number_())
        self.expect_symbol_(";")
        return self.ast.AttachStatement(glyphs, contourPoints, location=location)

    def parse_enumerate_(self, vertical):
        # Parse an enumerated pair positioning rule (`section 6.b.ii <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#6.b.ii>`_).
        assert self.cur_token_ in {"enumerate", "enum"}
        self.advance_lexer_()
        return self.parse_position_(enumerated=True, vertical=vertical)

    def parse_GlyphClassDef_(self):
        # Parses 'GlyphClassDef @BASE, @LIGATURES, @MARKS, @COMPONENTS;'
        assert self.is_cur_keyword_("GlyphClassDef")
        location = self.cur_token_location_
        if self.next_token_ != ",":
            baseGlyphs = self.parse_glyphclass_(accept_glyphname=False)
        else:
            baseGlyphs = None
        self.expect_symbol_(",")
        if self.next_token_ != ",":
            ligatureGlyphs = self.parse_glyphclass_(accept_glyphname=False)
        else:
            ligatureGlyphs = None
        self.expect_symbol_(",")
        if self.next_token_ != ",":
            markGlyphs = self.parse_glyphclass_(accept_glyphname=False)
        else:
            markGlyphs = None
        self.expect_symbol_(",")
        if self.next_token_ != ";":
            componentGlyphs = self.parse_glyphclass_(accept_glyphname=False)
        else:
            componentGlyphs = None
        self.expect_symbol_(";")
        return self.ast.GlyphClassDefStatement(
            baseGlyphs, markGlyphs, ligatureGlyphs, componentGlyphs, location=location
        )

    def parse_glyphclass_definition_(self):
        # Parses glyph class definitions such as '@UPPERCASE = [A-Z];'
        location, name = self.cur_token_location_, self.cur_token_
        self.expect_symbol_("=")
        glyphs = self.parse_glyphclass_(accept_glyphname=False)
        self.expect_symbol_(";")
        glyphclass = self.ast.GlyphClassDefinition(name, glyphs, location=location)
        self.glyphclasses_.define(name, glyphclass)
        return glyphclass

    def split_glyph_range_(self, name, location):
        # Since v1.20, the OpenType Feature File specification allows
        # for dashes in glyph names. A sequence like "a-b-c-d" could
        # therefore mean a single glyph whose name happens to be
        # "a-b-c-d", or it could mean a range from glyph "a" to glyph
        # "b-c-d", or a range from glyph "a-b" to glyph "c-d", or a
        # range from glyph "a-b-c" to glyph "d".Technically, this
        # example could be resolved because the (pretty complex)
        # definition of glyph ranges renders most of these splits
        # invalid. But the specification does not say that a compiler
        # should try to apply such fancy heuristics. To encourage
        # unambiguous feature files, we therefore try all possible
        # splits and reject the feature file if there are multiple
        # splits possible. It is intentional that we don't just emit a
        # warning; warnings tend to get ignored. To fix the problem,
        # font designers can trivially add spaces around the intended
        # split point, and we emit a compiler error that suggests
        # how exactly the source should be rewritten to make things
        # unambiguous.
        parts = name.split("-")
        solutions = []
        for i in range(len(parts)):
            start, limit = "-".join(parts[0:i]), "-".join(parts[i:])
            if start in self.glyphNames_ and limit in self.glyphNames_:
                solutions.append((start, limit))
        if len(solutions) == 1:
            start, limit = solutions[0]
            return start, limit
        elif len(solutions) == 0:
            raise FeatureLibError(
                '"%s" is not a glyph in the font, and it can not be split '
                "into a range of known glyphs" % name,
                location,
            )
        else:
            ranges = " or ".join(['"%s - %s"' % (s, l) for s, l in solutions])
            raise FeatureLibError(
                'Ambiguous glyph range "%s"; '
                "please use %s to clarify what you mean" % (name, ranges),
                location,
            )

    def parse_glyphclass_(self, accept_glyphname, accept_null=False):
        # Parses a glyph class, either named or anonymous, or (if
        # ``bool(accept_glyphname)``) a glyph name. If ``bool(accept_null)`` then
        # also accept the special NULL glyph.
        if accept_glyphname and self.next_token_type_ in (Lexer.NAME, Lexer.CID):
            if accept_null and self.next_token_ == "NULL":
                # If you want a glyph called NULL, you should escape it.
                self.advance_lexer_()
                return self.ast.NullGlyph(location=self.cur_token_location_)
            glyph = self.expect_glyph_()
            self.check_glyph_name_in_glyph_set(glyph)
            return self.ast.GlyphName(glyph, location=self.cur_token_location_)
        if self.next_token_type_ is Lexer.GLYPHCLASS:
            self.advance_lexer_()
            gc = self.glyphclasses_.resolve(self.cur_token_)
            if gc is None:
                raise FeatureLibError(
                    "Unknown glyph class @%s" % self.cur_token_,
                    self.cur_token_location_,
                )
            if isinstance(gc, self.ast.MarkClass):
                return self.ast.MarkClassName(gc, location=self.cur_token_location_)
            else:
                return self.ast.GlyphClassName(gc, location=self.cur_token_location_)

        self.expect_symbol_("[")
        location = self.cur_token_location_
        glyphs = self.ast.GlyphClass(location=location)
        while self.next_token_ != "]":
            if self.next_token_type_ is Lexer.NAME:
                glyph = self.expect_glyph_()
                location = self.cur_token_location_
                if "-" in glyph and self.glyphNames_ and glyph not in self.glyphNames_:
                    start, limit = self.split_glyph_range_(glyph, location)
                    self.check_glyph_name_in_glyph_set(start, limit)
                    glyphs.add_range(
                        start, limit, self.make_glyph_range_(location, start, limit)
                    )
                elif self.next_token_ == "-":
                    start = glyph
                    self.expect_symbol_("-")
                    limit = self.expect_glyph_()
                    self.check_glyph_name_in_glyph_set(start, limit)
                    glyphs.add_range(
                        start, limit, self.make_glyph_range_(location, start, limit)
                    )
                else:
                    if "-" in glyph and not self.glyphNames_:
                        log.warning(
                            str(
                                FeatureLibError(
                                    f"Ambiguous glyph name that looks like a range: {glyph!r}",
                                    location,
                                )
                            )
                        )
                    self.check_glyph_name_in_glyph_set(glyph)
                    glyphs.append(glyph)
            elif self.next_token_type_ is Lexer.CID:
                glyph = self.expect_glyph_()
                if self.next_token_ == "-":
                    range_location = self.cur_token_location_
                    range_start = self.cur_token_
                    self.expect_symbol_("-")
                    range_end = self.expect_cid_()
                    self.check_glyph_name_in_glyph_set(
                        f"cid{range_start:05d}",
                        f"cid{range_end:05d}",
                    )
                    glyphs.add_cid_range(
                        range_start,
                        range_end,
                        self.make_cid_range_(range_location, range_start, range_end),
                    )
                else:
                    glyph_name = f"cid{self.cur_token_:05d}"
                    self.check_glyph_name_in_glyph_set(glyph_name)
                    glyphs.append(glyph_name)
            elif self.next_token_type_ is Lexer.GLYPHCLASS:
                self.advance_lexer_()
                gc = self.glyphclasses_.resolve(self.cur_token_)
                if gc is None:
                    raise FeatureLibError(
                        "Unknown glyph class @%s" % self.cur_token_,
                        self.cur_token_location_,
                    )
                if isinstance(gc, self.ast.MarkClass):
                    gc = self.ast.MarkClassName(gc, location=self.cur_token_location_)
                else:
                    gc = self.ast.GlyphClassName(gc, location=self.cur_token_location_)
                glyphs.add_class(gc)
            else:
                raise FeatureLibError(
                    "Expected glyph name, glyph range, "
                    f"or glyph class reference, found {self.next_token_!r}",
                    self.next_token_location_,
                )
        self.expect_symbol_("]")
        return glyphs

    def parse_glyph_pattern_(self, vertical):
        # Parses a glyph pattern, including lookups and context, e.g.::
        #
        #    a b
        #    a b c' d e
        #    a b c' lookup ChangeC d e
        prefix, glyphs, lookups, values, suffix = ([], [], [], [], [])
        hasMarks = False
        while self.next_token_ not in {"by", "from", ";", ","}:
            gc = self.parse_glyphclass_(accept_glyphname=True)
            marked = False
            if self.next_token_ == "'":
                self.expect_symbol_("'")
                hasMarks = marked = True
            if marked:
                if suffix:
                    # makeotf also reports this as an error, while FontForge
                    # silently inserts ' in all the intervening glyphs.
                    # https://github.com/fonttools/fonttools/pull/1096
                    raise FeatureLibError(
                        "Unsupported contextual target sequence: at most "
                        "one run of marked (') glyph/class names allowed",
                        self.cur_token_location_,
                    )
                glyphs.append(gc)
            elif glyphs:
                suffix.append(gc)
            else:
                prefix.append(gc)

            if self.is_next_value_():
                values.append(self.parse_valuerecord_(vertical))
            else:
                values.append(None)

            lookuplist = None
            while self.next_token_ == "lookup":
                if lookuplist is None:
                    lookuplist = []
                self.expect_keyword_("lookup")
                if not marked:
                    raise FeatureLibError(
                        "Lookups can only follow marked glyphs",
                        self.cur_token_location_,
                    )
                lookup_name = self.expect_name_()
                lookup = self.lookups_.resolve(lookup_name)
                if lookup is None:
                    raise FeatureLibError(
                        'Unknown lookup "%s"' % lookup_name, self.cur_token_location_
                    )
                lookuplist.append(lookup)
            if marked:
                lookups.append(lookuplist)

        if not glyphs and not suffix:  # eg., "sub f f i by"
            assert lookups == []
            return ([], prefix, [None] * len(prefix), values, [], hasMarks)
        else:
            if any(values[: len(prefix)]):
                raise FeatureLibError(
                    "Positioning cannot be applied in the bactrack glyph sequence, "
                    "before the marked glyph sequence.",
                    self.cur_token_location_,
                )
            marked_values = values[len(prefix) : len(prefix) + len(glyphs)]
            if any(marked_values):
                if any(values[len(prefix) + len(glyphs) :]):
                    raise FeatureLibError(
                        "Positioning values are allowed only in the marked glyph "
                        "sequence, or after the final glyph node when only one glyph "
                        "node is marked.",
                        self.cur_token_location_,
                    )
                values = marked_values
            elif values and values[-1]:
                if len(glyphs) > 1 or any(values[:-1]):
                    raise FeatureLibError(
                        "Positioning values are allowed only in the marked glyph "
                        "sequence, or after the final glyph node when only one glyph "
                        "node is marked.",
                        self.cur_token_location_,
                    )
                values = values[-1:]
            elif any(values):
                raise FeatureLibError(
                    "Positioning values are allowed only in the marked glyph "
                    "sequence, or after the final glyph node when only one glyph "
                    "node is marked.",
                    self.cur_token_location_,
                )
            return (prefix, glyphs, lookups, values, suffix, hasMarks)

    def parse_ignore_glyph_pattern_(self, sub):
        location = self.cur_token_location_
        prefix, glyphs, lookups, values, suffix, hasMarks = self.parse_glyph_pattern_(
            vertical=False
        )
        if any(lookups):
            raise FeatureLibError(
                f'No lookups can be specified for "ignore {sub}"', location
            )
        if not hasMarks:
            error = FeatureLibError(
                f'Ambiguous "ignore {sub}", there should be least one marked glyph',
                location,
            )
            log.warning(str(error))
            suffix, glyphs = glyphs[1:], glyphs[0:1]
        chainContext = (prefix, glyphs, suffix)
        return chainContext

    def parse_ignore_context_(self, sub):
        location = self.cur_token_location_
        chainContext = [self.parse_ignore_glyph_pattern_(sub)]
        while self.next_token_ == ",":
            self.expect_symbol_(",")
            chainContext.append(self.parse_ignore_glyph_pattern_(sub))
        self.expect_symbol_(";")
        return chainContext

    def parse_ignore_(self):
        # Parses an ignore sub/pos rule.
        assert self.is_cur_keyword_("ignore")
        location = self.cur_token_location_
        self.advance_lexer_()
        if self.cur_token_ in ["substitute", "sub"]:
            chainContext = self.parse_ignore_context_("sub")
            return self.ast.IgnoreSubstStatement(chainContext, location=location)
        if self.cur_token_ in ["position", "pos"]:
            chainContext = self.parse_ignore_context_("pos")
            return self.ast.IgnorePosStatement(chainContext, location=location)
        raise FeatureLibError(
            'Expected "substitute" or "position"', self.cur_token_location_
        )

    def parse_include_(self):
        assert self.cur_token_ == "include"
        location = self.cur_token_location_
        filename = self.expect_filename_()
        # self.expect_symbol_(";")
        return ast.IncludeStatement(filename, location=location)

    def parse_language_(self):
        assert self.is_cur_keyword_("language")
        location = self.cur_token_location_
        language = self.expect_language_tag_()
        include_default, required = (True, False)
        if self.next_token_ in {"exclude_dflt", "include_dflt"}:
            include_default = self.expect_name_() == "include_dflt"
        if self.next_token_ == "required":
            self.expect_keyword_("required")
            required = True
        self.expect_symbol_(";")
        return self.ast.LanguageStatement(
            language, include_default, required, location=location
        )

    def parse_ligatureCaretByIndex_(self):
        assert self.is_cur_keyword_("LigatureCaretByIndex")
        location = self.cur_token_location_
        glyphs = self.parse_glyphclass_(accept_glyphname=True)
        carets = [self.expect_number_()]
        while self.next_token_ != ";":
            carets.append(self.expect_number_())
        self.expect_symbol_(";")
        return self.ast.LigatureCaretByIndexStatement(glyphs, carets, location=location)

    def parse_ligatureCaretByPos_(self):
        assert self.is_cur_keyword_("LigatureCaretByPos")
        location = self.cur_token_location_
        glyphs = self.parse_glyphclass_(accept_glyphname=True)
        carets = [self.expect_number_(variable=True)]
        while self.next_token_ != ";":
            carets.append(self.expect_number_(variable=True))
        self.expect_symbol_(";")
        return self.ast.LigatureCaretByPosStatement(glyphs, carets, location=location)

    def parse_lookup_(self, vertical):
        # Parses a ``lookup`` - either a lookup block, or a lookup reference
        # inside a feature.
        assert self.is_cur_keyword_("lookup")
        location, name = self.cur_token_location_, self.expect_name_()

        if self.next_token_ == ";":
            lookup = self.lookups_.resolve(name)
            if lookup is None:
                raise FeatureLibError(
                    'Unknown lookup "%s"' % name, self.cur_token_location_
                )
            self.expect_symbol_(";")
            return self.ast.LookupReferenceStatement(lookup, location=location)

        use_extension = False
        if self.next_token_ == "useExtension":
            self.expect_keyword_("useExtension")
            use_extension = True

        block = self.ast.LookupBlock(name, use_extension, location=location)
        self.parse_block_(block, vertical)
        self.lookups_.define(name, block)
        return block

    def parse_lookupflag_(self):
        # Parses a ``lookupflag`` statement, either specified by number or
        # in words.
        assert self.is_cur_keyword_("lookupflag")
        location = self.cur_token_location_

        # format B: "lookupflag 6;"
        if self.next_token_type_ == Lexer.NUMBER:
            value = self.expect_number_()
            self.expect_symbol_(";")
            return self.ast.LookupFlagStatement(value, location=location)

        # format A: "lookupflag RightToLeft MarkAttachmentType @M;"
        value_seen = False
        value, markAttachment, markFilteringSet = 0, None, None
        flags = {
            "RightToLeft": 1,
            "IgnoreBaseGlyphs": 2,
            "IgnoreLigatures": 4,
            "IgnoreMarks": 8,
        }
        seen = set()
        while self.next_token_ != ";":
            if self.next_token_ in seen:
                raise FeatureLibError(
                    "%s can be specified only once" % self.next_token_,
                    self.next_token_location_,
                )
            seen.add(self.next_token_)
            if self.next_token_ == "MarkAttachmentType":
                self.expect_keyword_("MarkAttachmentType")
                markAttachment = self.parse_glyphclass_(accept_glyphname=False)
            elif self.next_token_ == "UseMarkFilteringSet":
                self.expect_keyword_("UseMarkFilteringSet")
                markFilteringSet = self.parse_glyphclass_(accept_glyphname=False)
            elif self.next_token_ in flags:
                value_seen = True
                value = value | flags[self.expect_name_()]
            else:
                raise FeatureLibError(
                    '"%s" is not a recognized lookupflag' % self.next_token_,
                    self.next_token_location_,
                )
        self.expect_symbol_(";")

        if not any([value_seen, markAttachment, markFilteringSet]):
            raise FeatureLibError(
                "lookupflag must have a value", self.next_token_location_
            )

        return self.ast.LookupFlagStatement(
            value,
            markAttachment=markAttachment,
            markFilteringSet=markFilteringSet,
            location=location,
        )

    def parse_markClass_(self):
        assert self.is_cur_keyword_("markClass")
        location = self.cur_token_location_
        glyphs = self.parse_glyphclass_(accept_glyphname=True)
        if not glyphs.glyphSet():
            raise FeatureLibError(
                "Empty glyph class in mark class definition", location
            )
        anchor = self.parse_anchor_()
        name = self.expect_class_name_()
        self.expect_symbol_(";")
        markClass = self.doc_.markClasses.get(name)
        if markClass is None:
            markClass = self.ast.MarkClass(name)
            self.doc_.markClasses[name] = markClass
            self.glyphclasses_.define(name, markClass)
        mcdef = self.ast.MarkClassDefinition(
            markClass, anchor, glyphs, location=location
        )
        markClass.addDefinition(mcdef)
        return mcdef

    def parse_position_(self, enumerated, vertical):
        assert self.cur_token_ in {"position", "pos"}
        if self.next_token_ == "cursive":  # GPOS type 3
            return self.parse_position_cursive_(enumerated, vertical)
        elif self.next_token_ == "base":  # GPOS type 4
            return self.parse_position_base_(enumerated, vertical)
        elif self.next_token_ == "ligature":  # GPOS type 5
            return self.parse_position_ligature_(enumerated, vertical)
        elif self.next_token_ == "mark":  # GPOS type 6
            return self.parse_position_mark_(enumerated, vertical)

        location = self.cur_token_location_
        prefix, glyphs, lookups, values, suffix, hasMarks = self.parse_glyph_pattern_(
            vertical
        )
        self.expect_symbol_(";")

        if any(lookups):
            # GPOS type 8: Chaining contextual positioning; explicit lookups
            if any(values):
                raise FeatureLibError(
                    'If "lookup" is present, no values must be specified', location
                )
            return self.ast.ChainContextPosStatement(
                prefix, glyphs, suffix, lookups, location=location
            )

        # Pair positioning, format A: "pos V 10 A -10;"
        # Pair positioning, format B: "pos V A -20;"
        if not prefix and not suffix and len(glyphs) == 2 and not hasMarks:
            if values[0] is None:  # Format B: "pos V A -20;"
                values.reverse()
            return self.ast.PairPosStatement(
                glyphs[0],
                values[0],
                glyphs[1],
                values[1],
                enumerated=enumerated,
                location=location,
            )

        if enumerated:
            raise FeatureLibError(
                '"enumerate" is only allowed with pair positionings', location
            )
        return self.ast.SinglePosStatement(
            list(zip(glyphs, values)),
            prefix,
            suffix,
            forceChain=hasMarks,
            location=location,
        )

    def parse_position_cursive_(self, enumerated, vertical):
        location = self.cur_token_location_
        self.expect_keyword_("cursive")
        if enumerated:
            raise FeatureLibError(
                '"enumerate" is not allowed with ' "cursive attachment positioning",
                location,
            )
        glyphclass = self.parse_glyphclass_(accept_glyphname=True)
        entryAnchor = self.parse_anchor_()
        exitAnchor = self.parse_anchor_()
        self.expect_symbol_(";")
        return self.ast.CursivePosStatement(
            glyphclass, entryAnchor, exitAnchor, location=location
        )

    def parse_position_base_(self, enumerated, vertical):
        location = self.cur_token_location_
        self.expect_keyword_("base")
        if enumerated:
            raise FeatureLibError(
                '"enumerate" is not allowed with '
                "mark-to-base attachment positioning",
                location,
            )
        base = self.parse_glyphclass_(accept_glyphname=True)
        marks = self.parse_anchor_marks_()
        self.expect_symbol_(";")
        return self.ast.MarkBasePosStatement(base, marks, location=location)

    def parse_position_ligature_(self, enumerated, vertical):
        location = self.cur_token_location_
        self.expect_keyword_("ligature")
        if enumerated:
            raise FeatureLibError(
                '"enumerate" is not allowed with '
                "mark-to-ligature attachment positioning",
                location,
            )
        ligatures = self.parse_glyphclass_(accept_glyphname=True)
        marks = [self.parse_anchor_marks_()]
        while self.next_token_ == "ligComponent":
            self.expect_keyword_("ligComponent")
            marks.append(self.parse_anchor_marks_())
        self.expect_symbol_(";")
        return self.ast.MarkLigPosStatement(ligatures, marks, location=location)

    def parse_position_mark_(self, enumerated, vertical):
        location = self.cur_token_location_
        self.expect_keyword_("mark")
        if enumerated:
            raise FeatureLibError(
                '"enumerate" is not allowed with '
                "mark-to-mark attachment positioning",
                location,
            )
        baseMarks = self.parse_glyphclass_(accept_glyphname=True)
        marks = self.parse_anchor_marks_()
        self.expect_symbol_(";")
        return self.ast.MarkMarkPosStatement(baseMarks, marks, location=location)

    def parse_script_(self):
        assert self.is_cur_keyword_("script")
        location, script = self.cur_token_location_, self.expect_script_tag_()
        self.expect_symbol_(";")
        return self.ast.ScriptStatement(script, location=location)

    def parse_substitute_(self):
        assert self.cur_token_ in {"substitute", "sub", "reversesub", "rsub"}
        location = self.cur_token_location_
        reverse = self.cur_token_ in {"reversesub", "rsub"}
        (
            old_prefix,
            old,
            lookups,
            values,
            old_suffix,
            hasMarks,
        ) = self.parse_glyph_pattern_(vertical=False)
        if any(values):
            raise FeatureLibError(
                "Substitution statements cannot contain values", location
            )
        new = []
        if self.next_token_ == "by":
            keyword = self.expect_keyword_("by")
            while self.next_token_ != ";":
                gc = self.parse_glyphclass_(accept_glyphname=True, accept_null=True)
                new.append(gc)
        elif self.next_token_ == "from":
            keyword = self.expect_keyword_("from")
            new = [self.parse_glyphclass_(accept_glyphname=False)]
        else:
            keyword = None
        self.expect_symbol_(";")
        if len(new) == 0 and not any(lookups):
            raise FeatureLibError(
                'Expected "by", "from" or explicit lookup references',
                self.cur_token_location_,
            )

        # GSUB lookup type 3: Alternate substitution.
        # Format: "substitute a from [a.1 a.2 a.3];"
        if keyword == "from":
            if reverse:
                raise FeatureLibError(
                    'Reverse chaining substitutions do not support "from"', location
                )
            if len(old) != 1 or len(old[0].glyphSet()) != 1:
                raise FeatureLibError('Expected a single glyph before "from"', location)
            if len(new) != 1:
                raise FeatureLibError(
                    'Expected a single glyphclass after "from"', location
                )
            return self.ast.AlternateSubstStatement(
                old_prefix, old[0], old_suffix, new[0], location=location
            )

        num_lookups = len([l for l in lookups if l is not None])

        is_deletion = False
        if len(new) == 1 and isinstance(new[0], ast.NullGlyph):
            new = []  # Deletion
            is_deletion = True

        # GSUB lookup type 1: Single substitution.
        # Format A: "substitute a by a.sc;"
        # Format B: "substitute [one.fitted one.oldstyle] by one;"
        # Format C: "substitute [a-d] by [A.sc-D.sc];"
        if not reverse and len(old) == 1 and len(new) == 1 and num_lookups == 0:
            glyphs = list(old[0].glyphSet())
            replacements = list(new[0].glyphSet())
            if len(replacements) == 1:
                replacements = replacements * len(glyphs)
            if len(glyphs) != len(replacements):
                raise FeatureLibError(
                    'Expected a glyph class with %d elements after "by", '
                    "but found a glyph class with %d elements"
                    % (len(glyphs), len(replacements)),
                    location,
                )
            return self.ast.SingleSubstStatement(
                old, new, old_prefix, old_suffix, forceChain=hasMarks, location=location
            )

        # Glyph deletion, built as GSUB lookup type 2: Multiple substitution
        # with empty replacement.
        if is_deletion and len(old) == 1 and num_lookups == 0:
            return self.ast.MultipleSubstStatement(
                old_prefix,
                old[0],
                old_suffix,
                (),
                forceChain=hasMarks,
                location=location,
            )

        # GSUB lookup type 2: Multiple substitution.
        # Format: "substitute f_f_i by f f i;"
        #
        # GlyphsApp introduces two additional formats:
        # Format 1: "substitute [f_i f_l] by [f f] [i l];"
        # Format 2: "substitute [f_i f_l] by f [i l];"
        # http://handbook.glyphsapp.com/en/layout/multiple-substitution-with-classes/
        if not reverse and len(old) == 1 and len(new) > 1 and num_lookups == 0:
            count = len(old[0].glyphSet())
            for n in new:
                if not list(n.glyphSet()):
                    raise FeatureLibError("Empty class in replacement", location)
                if len(n.glyphSet()) != 1 and len(n.glyphSet()) != count:
                    raise FeatureLibError(
                        f'Expected a glyph class with 1 or {count} elements after "by", '
                        f"but found a glyph class with {len(n.glyphSet())} elements",
                        location,
                    )
            return self.ast.MultipleSubstStatement(
                old_prefix,
                old[0],
                old_suffix,
                new,
                forceChain=hasMarks,
                location=location,
            )

        # GSUB lookup type 4: Ligature substitution.
        # Format: "substitute f f i by f_f_i;"
        if (
            not reverse
            and len(old) > 1
            and len(new) == 1
            and len(new[0].glyphSet()) == 1
            and num_lookups == 0
        ):
            return self.ast.LigatureSubstStatement(
                old_prefix,
                old,
                old_suffix,
                list(new[0].glyphSet())[0],
                forceChain=hasMarks,
                location=location,
            )

        # GSUB lookup type 8: Reverse chaining substitution.
        if reverse:
            if len(old) != 1:
                raise FeatureLibError(
                    "In reverse chaining single substitutions, "
                    "only a single glyph or glyph class can be replaced",
                    location,
                )
            if len(new) != 1:
                raise FeatureLibError(
                    "In reverse chaining single substitutions, "
                    'the replacement (after "by") must be a single glyph '
                    "or glyph class",
                    location,
                )
            if num_lookups != 0:
                raise FeatureLibError(
                    "Reverse chaining substitutions cannot call named lookups", location
                )
            glyphs = sorted(list(old[0].glyphSet()))
            replacements = sorted(list(new[0].glyphSet()))
            if len(replacements) == 1:
                replacements = replacements * len(glyphs)
            if len(glyphs) != len(replacements):
                raise FeatureLibError(
                    'Expected a glyph class with %d elements after "by", '
                    "but found a glyph class with %d elements"
                    % (len(glyphs), len(replacements)),
                    location,
                )
            return self.ast.ReverseChainSingleSubstStatement(
                old_prefix, old_suffix, old, new, location=location
            )

        if len(old) > 1 and len(new) > 1:
            raise FeatureLibError(
                "Direct substitution of multiple glyphs by multiple glyphs "
                "is not supported",
                location,
            )

        # If there are remaining glyphs to parse, this is an invalid GSUB statement
        if len(new) != 0 or is_deletion:
            raise FeatureLibError("Invalid substitution statement", location)

        # GSUB lookup type 6: Chaining contextual substitution.
        rule = self.ast.ChainContextSubstStatement(
            old_prefix, old, old_suffix, lookups, location=location
        )
        return rule

    def parse_subtable_(self):
        assert self.is_cur_keyword_("subtable")
        location = self.cur_token_location_
        self.expect_symbol_(";")
        return self.ast.SubtableStatement(location=location)

    def parse_size_parameters_(self):
        # Parses a ``parameters`` statement used in ``size`` features. See
        # `section 8.b <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#8.b>`_.
        assert self.is_cur_keyword_("parameters")
        location = self.cur_token_location_
        DesignSize = self.expect_decipoint_()
        SubfamilyID = self.expect_number_()
        RangeStart = 0.0
        RangeEnd = 0.0
        if self.next_token_type_ in (Lexer.NUMBER, Lexer.FLOAT) or SubfamilyID != 0:
            RangeStart = self.expect_decipoint_()
            RangeEnd = self.expect_decipoint_()

        self.expect_symbol_(";")
        return self.ast.SizeParameters(
            DesignSize, SubfamilyID, RangeStart, RangeEnd, location=location
        )

    def parse_size_menuname_(self):
        assert self.is_cur_keyword_("sizemenuname")
        location = self.cur_token_location_
        platformID, platEncID, langID, string = self.parse_name_()
        return self.ast.FeatureNameStatement(
            "size", platformID, platEncID, langID, string, location=location
        )

    def parse_table_(self):
        assert self.is_cur_keyword_("table")
        location, name = self.cur_token_location_, self.expect_tag_()
        table = self.ast.TableBlock(name, location=location)
        self.expect_symbol_("{")
        handler = {
            "GDEF": self.parse_table_GDEF_,
            "head": self.parse_table_head_,
            "hhea": self.parse_table_hhea_,
            "vhea": self.parse_table_vhea_,
            "name": self.parse_table_name_,
            "BASE": self.parse_table_BASE_,
            "OS/2": self.parse_table_OS_2_,
            "STAT": self.parse_table_STAT_,
        }.get(name)
        if handler:
            handler(table)
        else:
            raise FeatureLibError(
                '"table %s" is not supported' % name.strip(), location
            )
        self.expect_symbol_("}")
        end_tag = self.expect_tag_()
        if end_tag != name:
            raise FeatureLibError(
                'Expected "%s"' % name.strip(), self.cur_token_location_
            )
        self.expect_symbol_(";")
        return table

    def parse_table_GDEF_(self, table):
        statements = table.statements
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.is_cur_keyword_("Attach"):
                statements.append(self.parse_attach_())
            elif self.is_cur_keyword_("GlyphClassDef"):
                statements.append(self.parse_GlyphClassDef_())
            elif self.is_cur_keyword_("LigatureCaretByIndex"):
                statements.append(self.parse_ligatureCaretByIndex_())
            elif self.is_cur_keyword_("LigatureCaretByPos"):
                statements.append(self.parse_ligatureCaretByPos_())
            elif self.cur_token_ == ";":
                continue
            else:
                raise FeatureLibError(
                    "Expected Attach, LigatureCaretByIndex, " "or LigatureCaretByPos",
                    self.cur_token_location_,
                )

    def parse_table_head_(self, table):
        statements = table.statements
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.is_cur_keyword_("FontRevision"):
                statements.append(self.parse_FontRevision_())
            elif self.cur_token_ == ";":
                continue
            else:
                raise FeatureLibError("Expected FontRevision", self.cur_token_location_)

    def parse_table_hhea_(self, table):
        statements = table.statements
        fields = ("CaretOffset", "Ascender", "Descender", "LineGap")
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.cur_token_type_ is Lexer.NAME and self.cur_token_ in fields:
                key = self.cur_token_.lower()
                value = self.expect_number_()
                statements.append(
                    self.ast.HheaField(key, value, location=self.cur_token_location_)
                )
                if self.next_token_ != ";":
                    raise FeatureLibError(
                        "Incomplete statement", self.next_token_location_
                    )
            elif self.cur_token_ == ";":
                continue
            else:
                raise FeatureLibError(
                    "Expected CaretOffset, Ascender, " "Descender or LineGap",
                    self.cur_token_location_,
                )

    def parse_table_vhea_(self, table):
        statements = table.statements
        fields = ("VertTypoAscender", "VertTypoDescender", "VertTypoLineGap")
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.cur_token_type_ is Lexer.NAME and self.cur_token_ in fields:
                key = self.cur_token_.lower()
                value = self.expect_number_()
                statements.append(
                    self.ast.VheaField(key, value, location=self.cur_token_location_)
                )
                if self.next_token_ != ";":
                    raise FeatureLibError(
                        "Incomplete statement", self.next_token_location_
                    )
            elif self.cur_token_ == ";":
                continue
            else:
                raise FeatureLibError(
                    "Expected VertTypoAscender, "
                    "VertTypoDescender or VertTypoLineGap",
                    self.cur_token_location_,
                )

    def parse_table_name_(self, table):
        statements = table.statements
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.is_cur_keyword_("nameid"):
                statement = self.parse_nameid_()
                if statement:
                    statements.append(statement)
            elif self.cur_token_ == ";":
                continue
            else:
                raise FeatureLibError("Expected nameid", self.cur_token_location_)

    def parse_name_(self):
        """Parses a name record. See `section 9.e <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#9.e>`_."""
        platEncID = None
        langID = None
        if self.next_token_type_ in Lexer.NUMBERS:
            platformID = self.expect_any_number_()
            location = self.cur_token_location_
            if platformID not in (1, 3):
                raise FeatureLibError("Expected platform id 1 or 3", location)
            if self.next_token_type_ in Lexer.NUMBERS:
                platEncID = self.expect_any_number_()
                langID = self.expect_any_number_()
        else:
            platformID = 3
            location = self.cur_token_location_

        if platformID == 1:  # Macintosh
            platEncID = platEncID or 0  # Roman
            langID = langID or 0  # English
        else:  # 3, Windows
            platEncID = platEncID or 1  # Unicode
            langID = langID or 0x0409  # English

        string = self.expect_string_()
        self.expect_symbol_(";")

        encoding = getEncoding(platformID, platEncID, langID)
        if encoding is None:
            raise FeatureLibError("Unsupported encoding", location)
        unescaped = self.unescape_string_(string, encoding)
        return platformID, platEncID, langID, unescaped

    def parse_stat_name_(self):
        platEncID = None
        langID = None
        if self.next_token_type_ in Lexer.NUMBERS:
            platformID = self.expect_any_number_()
            location = self.cur_token_location_
            if platformID not in (1, 3):
                raise FeatureLibError("Expected platform id 1 or 3", location)
            if self.next_token_type_ in Lexer.NUMBERS:
                platEncID = self.expect_any_number_()
                langID = self.expect_any_number_()
        else:
            platformID = 3
            location = self.cur_token_location_

        if platformID == 1:  # Macintosh
            platEncID = platEncID or 0  # Roman
            langID = langID or 0  # English
        else:  # 3, Windows
            platEncID = platEncID or 1  # Unicode
            langID = langID or 0x0409  # English

        string = self.expect_string_()
        encoding = getEncoding(platformID, platEncID, langID)
        if encoding is None:
            raise FeatureLibError("Unsupported encoding", location)
        unescaped = self.unescape_string_(string, encoding)
        return platformID, platEncID, langID, unescaped

    def parse_nameid_(self):
        assert self.cur_token_ == "nameid", self.cur_token_
        location, nameID = self.cur_token_location_, self.expect_any_number_()
        if nameID > 32767:
            raise FeatureLibError(
                "Name id value cannot be greater than 32767", self.cur_token_location_
            )
        platformID, platEncID, langID, string = self.parse_name_()
        return self.ast.NameRecord(
            nameID, platformID, platEncID, langID, string, location=location
        )

    def unescape_string_(self, string, encoding):
        if encoding == "utf_16_be":
            s = re.sub(r"\\[0-9a-fA-F]{4}", self.unescape_unichr_, string)
        else:
            unescape = lambda m: self.unescape_byte_(m, encoding)
            s = re.sub(r"\\[0-9a-fA-F]{2}", unescape, string)
        # We now have a Unicode string, but it might contain surrogate pairs.
        # We convert surrogates to actual Unicode by round-tripping through
        # Python's UTF-16 codec in a special mode.
        utf16 = tobytes(s, "utf_16_be", "surrogatepass")
        return tostr(utf16, "utf_16_be")

    @staticmethod
    def unescape_unichr_(match):
        n = match.group(0)[1:]
        return chr(int(n, 16))

    @staticmethod
    def unescape_byte_(match, encoding):
        n = match.group(0)[1:]
        return bytechr(int(n, 16)).decode(encoding)

    def find_previous(self, statements, class_):
        for previous in reversed(statements):
            if isinstance(previous, self.ast.Comment):
                continue
            elif isinstance(previous, class_):
                return previous
            else:
                # If we find something that doesn't match what we're looking
                # for, and isn't a comment, fail
                return None
        # Out of statements to look at
        return None

    def parse_table_BASE_(self, table):
        statements = table.statements
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.is_cur_keyword_("HorizAxis.BaseTagList"):
                horiz_bases = self.parse_base_tag_list_()
            elif self.is_cur_keyword_("HorizAxis.BaseScriptList"):
                horiz_scripts = self.parse_base_script_list_(len(horiz_bases))
                statements.append(
                    self.ast.BaseAxis(
                        horiz_bases,
                        horiz_scripts,
                        False,
                        location=self.cur_token_location_,
                    )
                )
            elif self.is_cur_keyword_("HorizAxis.MinMax"):
                base_script_list = self.find_previous(statements, ast.BaseAxis)
                if base_script_list is None:
                    raise FeatureLibError(
                        "MinMax must be preceded by BaseScriptList",
                        self.cur_token_location_,
                    )
                if base_script_list.vertical:
                    raise FeatureLibError(
                        "HorizAxis.MinMax must be preceded by HorizAxis statements",
                        self.cur_token_location_,
                    )
                base_script_list.minmax.append(self.parse_base_minmax_())
            elif self.is_cur_keyword_("VertAxis.BaseTagList"):
                vert_bases = self.parse_base_tag_list_()
            elif self.is_cur_keyword_("VertAxis.BaseScriptList"):
                vert_scripts = self.parse_base_script_list_(len(vert_bases))
                statements.append(
                    self.ast.BaseAxis(
                        vert_bases,
                        vert_scripts,
                        True,
                        location=self.cur_token_location_,
                    )
                )
            elif self.is_cur_keyword_("VertAxis.MinMax"):
                base_script_list = self.find_previous(statements, ast.BaseAxis)
                if base_script_list is None:
                    raise FeatureLibError(
                        "MinMax must be preceded by BaseScriptList",
                        self.cur_token_location_,
                    )
                if not base_script_list.vertical:
                    raise FeatureLibError(
                        "VertAxis.MinMax must be preceded by VertAxis statements",
                        self.cur_token_location_,
                    )
                base_script_list.minmax.append(self.parse_base_minmax_())
            elif self.cur_token_ == ";":
                continue

    def parse_table_OS_2_(self, table):
        statements = table.statements
        numbers = (
            "FSType",
            "TypoAscender",
            "TypoDescender",
            "TypoLineGap",
            "winAscent",
            "winDescent",
            "XHeight",
            "CapHeight",
            "WeightClass",
            "WidthClass",
            "LowerOpSize",
            "UpperOpSize",
        )
        ranges = ("UnicodeRange", "CodePageRange")
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.cur_token_type_ is Lexer.NAME:
                key = self.cur_token_.lower()
                value = None
                if self.cur_token_ in numbers:
                    value = self.expect_number_()
                elif self.is_cur_keyword_("Panose"):
                    value = []
                    for i in range(10):
                        value.append(self.expect_number_())
                elif self.cur_token_ in ranges:
                    value = []
                    while self.next_token_ != ";":
                        value.append(self.expect_number_())
                elif self.is_cur_keyword_("Vendor"):
                    value = self.expect_string_()
                statements.append(
                    self.ast.OS2Field(key, value, location=self.cur_token_location_)
                )
            elif self.cur_token_ == ";":
                continue

    def parse_STAT_ElidedFallbackName(self):
        assert self.is_cur_keyword_("ElidedFallbackName")
        self.expect_symbol_("{")
        names = []
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_()
            if self.is_cur_keyword_("name"):
                platformID, platEncID, langID, string = self.parse_stat_name_()
                nameRecord = self.ast.STATNameStatement(
                    "stat",
                    platformID,
                    platEncID,
                    langID,
                    string,
                    location=self.cur_token_location_,
                )
                names.append(nameRecord)
            else:
                if self.cur_token_ != ";":
                    raise FeatureLibError(
                        f"Unexpected token {self.cur_token_} " f"in ElidedFallbackName",
                        self.cur_token_location_,
                    )
        self.expect_symbol_("}")
        if not names:
            raise FeatureLibError('Expected "name"', self.cur_token_location_)
        return names

    def parse_STAT_design_axis(self):
        assert self.is_cur_keyword_("DesignAxis")
        names = []
        axisTag = self.expect_tag_()
        if (
            axisTag not in ("ital", "opsz", "slnt", "wdth", "wght")
            and not axisTag.isupper()
        ):
            log.warning(f"Unregistered axis tag {axisTag} should be uppercase.")
        axisOrder = self.expect_number_()
        self.expect_symbol_("{")
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_()
            if self.cur_token_type_ is Lexer.COMMENT:
                continue
            elif self.is_cur_keyword_("name"):
                location = self.cur_token_location_
                platformID, platEncID, langID, string = self.parse_stat_name_()
                name = self.ast.STATNameStatement(
                    "stat", platformID, platEncID, langID, string, location=location
                )
                names.append(name)
            elif self.cur_token_ == ";":
                continue
            else:
                raise FeatureLibError(
                    f'Expected "name", got {self.cur_token_}', self.cur_token_location_
                )

        self.expect_symbol_("}")
        return self.ast.STATDesignAxisStatement(
            axisTag, axisOrder, names, self.cur_token_location_
        )

    def parse_STAT_axis_value_(self):
        assert self.is_cur_keyword_("AxisValue")
        self.expect_symbol_("{")
        locations = []
        names = []
        flags = 0
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                continue
            elif self.is_cur_keyword_("name"):
                location = self.cur_token_location_
                platformID, platEncID, langID, string = self.parse_stat_name_()
                name = self.ast.STATNameStatement(
                    "stat", platformID, platEncID, langID, string, location=location
                )
                names.append(name)
            elif self.is_cur_keyword_("location"):
                location = self.parse_STAT_location()
                locations.append(location)
            elif self.is_cur_keyword_("flag"):
                flags = self.expect_stat_flags()
            elif self.cur_token_ == ";":
                continue
            else:
                raise FeatureLibError(
                    f"Unexpected token {self.cur_token_} " f"in AxisValue",
                    self.cur_token_location_,
                )
        self.expect_symbol_("}")
        if not names:
            raise FeatureLibError('Expected "Axis Name"', self.cur_token_location_)
        if not locations:
            raise FeatureLibError('Expected "Axis location"', self.cur_token_location_)
        if len(locations) > 1:
            for location in locations:
                if len(location.values) > 1:
                    raise FeatureLibError(
                        "Only one value is allowed in a "
                        "Format 4 Axis Value Record, but "
                        f"{len(location.values)} were found.",
                        self.cur_token_location_,
                    )
            format4_tags = []
            for location in locations:
                tag = location.tag
                if tag in format4_tags:
                    raise FeatureLibError(
                        f"Axis tag {tag} already " "defined.", self.cur_token_location_
                    )
                format4_tags.append(tag)

        return self.ast.STATAxisValueStatement(
            names, locations, flags, self.cur_token_location_
        )

    def parse_STAT_location(self):
        values = []
        tag = self.expect_tag_()
        if len(tag.strip()) != 4:
            raise FeatureLibError(
                f"Axis tag {self.cur_token_} must be 4 " "characters",
                self.cur_token_location_,
            )

        while self.next_token_ != ";":
            if self.next_token_type_ is Lexer.FLOAT:
                value = self.expect_float_()
                values.append(value)
            elif self.next_token_type_ is Lexer.NUMBER:
                value = self.expect_number_()
                values.append(value)
            else:
                raise FeatureLibError(
                    f'Unexpected value "{self.next_token_}". '
                    "Expected integer or float.",
                    self.next_token_location_,
                )
        if len(values) == 3:
            nominal, min_val, max_val = values
            if nominal < min_val or nominal > max_val:
                raise FeatureLibError(
                    f"Default value {nominal} is outside "
                    f"of specified range "
                    f"{min_val}-{max_val}.",
                    self.next_token_location_,
                )
        return self.ast.AxisValueLocationStatement(tag, values)

    def parse_table_STAT_(self, table):
        statements = table.statements
        design_axes = []
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.cur_token_type_ is Lexer.NAME:
                if self.is_cur_keyword_("ElidedFallbackName"):
                    names = self.parse_STAT_ElidedFallbackName()
                    statements.append(self.ast.ElidedFallbackName(names))
                elif self.is_cur_keyword_("ElidedFallbackNameID"):
                    value = self.expect_number_()
                    statements.append(self.ast.ElidedFallbackNameID(value))
                    self.expect_symbol_(";")
                elif self.is_cur_keyword_("DesignAxis"):
                    designAxis = self.parse_STAT_design_axis()
                    design_axes.append(designAxis.tag)
                    statements.append(designAxis)
                    self.expect_symbol_(";")
                elif self.is_cur_keyword_("AxisValue"):
                    axisValueRecord = self.parse_STAT_axis_value_()
                    for location in axisValueRecord.locations:
                        if location.tag not in design_axes:
                            # Tag must be defined in a DesignAxis before it
                            # can be referenced
                            raise FeatureLibError(
                                "DesignAxis not defined for " f"{location.tag}.",
                                self.cur_token_location_,
                            )
                    statements.append(axisValueRecord)
                    self.expect_symbol_(";")
                else:
                    raise FeatureLibError(
                        f"Unexpected token {self.cur_token_}", self.cur_token_location_
                    )
            elif self.cur_token_ == ";":
                continue

    def parse_base_tag_list_(self):
        # Parses BASE table entries. (See `section 9.a <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#9.a>`_)
        assert self.cur_token_ in (
            "HorizAxis.BaseTagList",
            "VertAxis.BaseTagList",
        ), self.cur_token_
        bases = []
        while self.next_token_ != ";":
            bases.append(self.expect_script_tag_())
        self.expect_symbol_(";")
        return bases

    def parse_base_script_list_(self, count):
        assert self.cur_token_ in (
            "HorizAxis.BaseScriptList",
            "VertAxis.BaseScriptList",
        ), self.cur_token_
        scripts = [self.parse_base_script_record_(count)]
        while self.next_token_ == ",":
            self.expect_symbol_(",")
            scripts.append(self.parse_base_script_record_(count))
        self.expect_symbol_(";")
        return scripts

    def parse_base_script_record_(self, count):
        script_tag = self.expect_script_tag_()
        base_tag = self.expect_script_tag_()
        coords = [self.expect_number_() for i in range(count)]
        return script_tag, base_tag, coords

    def parse_base_minmax_(self):
        script_tag = self.expect_script_tag_()
        language = self.expect_language_tag_()
        min_coord = self.expect_number_()
        self.advance_lexer_()
        if not (self.cur_token_type_ is Lexer.SYMBOL and self.cur_token_ == ","):
            raise FeatureLibError(
                "Expected a comma between min and max coordinates",
                self.cur_token_location_,
            )
        max_coord = self.expect_number_()
        if self.next_token_ == ",":  # feature tag...
            raise FeatureLibError(
                "Feature tags are not yet supported in BASE table",
                self.cur_token_location_,
            )

        return script_tag, language, min_coord, max_coord

    def parse_device_(self):
        result = None
        self.expect_symbol_("<")
        self.expect_keyword_("device")
        if self.next_token_ == "NULL":
            self.expect_keyword_("NULL")
        else:
            result = [(self.expect_number_(), self.expect_number_())]
            while self.next_token_ == ",":
                self.expect_symbol_(",")
                result.append((self.expect_number_(), self.expect_number_()))
            result = tuple(result)  # make it hashable
        self.expect_symbol_(">")
        return result

    def is_next_value_(self):
        return (
            self.next_token_type_ is Lexer.NUMBER
            or self.next_token_ == "<"
            or self.next_token_ == "("
        )

    def parse_valuerecord_(self, vertical):
        if (
            self.next_token_type_ is Lexer.SYMBOL and self.next_token_ == "("
        ) or self.next_token_type_ is Lexer.NUMBER:
            number, location = (
                self.expect_number_(variable=True),
                self.cur_token_location_,
            )
            if vertical:
                val = self.ast.ValueRecord(
                    yAdvance=number, vertical=vertical, location=location
                )
            else:
                val = self.ast.ValueRecord(
                    xAdvance=number, vertical=vertical, location=location
                )
            return val
        self.expect_symbol_("<")
        location = self.cur_token_location_
        if self.next_token_type_ is Lexer.NAME:
            name = self.expect_name_()
            if name == "NULL":
                self.expect_symbol_(">")
                return self.ast.ValueRecord()
            vrd = self.valuerecords_.resolve(name)
            if vrd is None:
                raise FeatureLibError(
                    'Unknown valueRecordDef "%s"' % name, self.cur_token_location_
                )
            value = vrd.value
            xPlacement, yPlacement = (value.xPlacement, value.yPlacement)
            xAdvance, yAdvance = (value.xAdvance, value.yAdvance)
        else:
            xPlacement, yPlacement, xAdvance, yAdvance = (
                self.expect_number_(variable=True),
                self.expect_number_(variable=True),
                self.expect_number_(variable=True),
                self.expect_number_(variable=True),
            )

        if self.next_token_ == "<":
            xPlaDevice, yPlaDevice, xAdvDevice, yAdvDevice = (
                self.parse_device_(),
                self.parse_device_(),
                self.parse_device_(),
                self.parse_device_(),
            )
            allDeltas = sorted(
                [
                    delta
                    for size, delta in (xPlaDevice if xPlaDevice else ())
                    + (yPlaDevice if yPlaDevice else ())
                    + (xAdvDevice if xAdvDevice else ())
                    + (yAdvDevice if yAdvDevice else ())
                ]
            )
            if allDeltas[0] < -128 or allDeltas[-1] > 127:
                raise FeatureLibError(
                    "Device value out of valid range (-128..127)",
                    self.cur_token_location_,
                )
        else:
            xPlaDevice, yPlaDevice, xAdvDevice, yAdvDevice = (None, None, None, None)

        self.expect_symbol_(">")
        return self.ast.ValueRecord(
            xPlacement,
            yPlacement,
            xAdvance,
            yAdvance,
            xPlaDevice,
            yPlaDevice,
            xAdvDevice,
            yAdvDevice,
            vertical=vertical,
            location=location,
        )

    def parse_valuerecord_definition_(self, vertical):
        # Parses a named value record definition. (See section `2.e.v <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#2.e.v>`_)
        assert self.is_cur_keyword_("valueRecordDef")
        location = self.cur_token_location_
        value = self.parse_valuerecord_(vertical)
        name = self.expect_name_()
        self.expect_symbol_(";")
        vrd = self.ast.ValueRecordDefinition(name, value, location=location)
        self.valuerecords_.define(name, vrd)
        return vrd

    def parse_languagesystem_(self):
        assert self.cur_token_ == "languagesystem"
        location = self.cur_token_location_
        script = self.expect_script_tag_()
        language = self.expect_language_tag_()
        self.expect_symbol_(";")
        return self.ast.LanguageSystemStatement(script, language, location=location)

    def parse_feature_block_(self, variation=False):
        if variation:
            assert self.cur_token_ == "variation"
        else:
            assert self.cur_token_ == "feature"
        location = self.cur_token_location_
        tag = self.expect_tag_()
        vertical = tag in {"vkrn", "vpal", "vhal", "valt"}

        stylisticset = None
        cv_feature = None
        size_feature = False
        if tag in self.SS_FEATURE_TAGS:
            stylisticset = tag
        elif tag in self.CV_FEATURE_TAGS:
            cv_feature = tag
        elif tag == "size":
            size_feature = True

        if variation:
            conditionset = self.expect_name_()

        use_extension = False
        if self.next_token_ == "useExtension":
            self.expect_keyword_("useExtension")
            use_extension = True

        if variation:
            block = self.ast.VariationBlock(
                tag, conditionset, use_extension=use_extension, location=location
            )
        else:
            block = self.ast.FeatureBlock(
                tag, use_extension=use_extension, location=location
            )
        self.parse_block_(block, vertical, stylisticset, size_feature, cv_feature)
        return block

    def parse_feature_reference_(self):
        assert self.cur_token_ == "feature", self.cur_token_
        location = self.cur_token_location_
        featureName = self.expect_tag_()
        self.expect_symbol_(";")
        return self.ast.FeatureReferenceStatement(featureName, location=location)

    def parse_featureNames_(self, tag):
        """Parses a ``featureNames`` statement found in stylistic set features.
        See section `8.c <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#8.c>`_.
        """
        assert self.cur_token_ == "featureNames", self.cur_token_
        block = self.ast.NestedBlock(
            tag, self.cur_token_, location=self.cur_token_location_
        )
        self.expect_symbol_("{")
        for symtab in self.symbol_tables_:
            symtab.enter_scope()
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                block.statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.is_cur_keyword_("name"):
                location = self.cur_token_location_
                platformID, platEncID, langID, string = self.parse_name_()
                block.statements.append(
                    self.ast.FeatureNameStatement(
                        tag, platformID, platEncID, langID, string, location=location
                    )
                )
            elif self.cur_token_ == ";":
                continue
            else:
                raise FeatureLibError('Expected "name"', self.cur_token_location_)
        self.expect_symbol_("}")
        for symtab in self.symbol_tables_:
            symtab.exit_scope()
        self.expect_symbol_(";")
        return block

    def parse_cvParameters_(self, tag):
        # Parses a ``cvParameters`` block found in Character Variant features.
        # See section `8.d <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#8.d>`_.
        assert self.cur_token_ == "cvParameters", self.cur_token_
        block = self.ast.NestedBlock(
            tag, self.cur_token_, location=self.cur_token_location_
        )
        self.expect_symbol_("{")
        for symtab in self.symbol_tables_:
            symtab.enter_scope()

        statements = block.statements
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.is_cur_keyword_(
                {
                    "FeatUILabelNameID",
                    "FeatUITooltipTextNameID",
                    "SampleTextNameID",
                    "ParamUILabelNameID",
                }
            ):
                statements.append(self.parse_cvNameIDs_(tag, self.cur_token_))
            elif self.is_cur_keyword_("Character"):
                statements.append(self.parse_cvCharacter_(tag))
            elif self.cur_token_ == ";":
                continue
            else:
                raise FeatureLibError(
                    "Expected statement: got {} {}".format(
                        self.cur_token_type_, self.cur_token_
                    ),
                    self.cur_token_location_,
                )

        self.expect_symbol_("}")
        for symtab in self.symbol_tables_:
            symtab.exit_scope()
        self.expect_symbol_(";")
        return block

    def parse_cvNameIDs_(self, tag, block_name):
        assert self.cur_token_ == block_name, self.cur_token_
        block = self.ast.NestedBlock(tag, block_name, location=self.cur_token_location_)
        self.expect_symbol_("{")
        for symtab in self.symbol_tables_:
            symtab.enter_scope()
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                block.statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.is_cur_keyword_("name"):
                location = self.cur_token_location_
                platformID, platEncID, langID, string = self.parse_name_()
                block.statements.append(
                    self.ast.CVParametersNameStatement(
                        tag,
                        platformID,
                        platEncID,
                        langID,
                        string,
                        block_name,
                        location=location,
                    )
                )
            elif self.cur_token_ == ";":
                continue
            else:
                raise FeatureLibError('Expected "name"', self.cur_token_location_)
        self.expect_symbol_("}")
        for symtab in self.symbol_tables_:
            symtab.exit_scope()
        self.expect_symbol_(";")
        return block

    def parse_cvCharacter_(self, tag):
        assert self.cur_token_ == "Character", self.cur_token_
        location, character = self.cur_token_location_, self.expect_any_number_()
        self.expect_symbol_(";")
        if not (0xFFFFFF >= character >= 0):
            raise FeatureLibError(
                "Character value must be between "
                "{:#x} and {:#x}".format(0, 0xFFFFFF),
                location,
            )
        return self.ast.CharacterStatement(character, tag, location=location)

    def parse_FontRevision_(self):
        # Parses a ``FontRevision`` statement found in the head table. See
        # `section 9.c <https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html#9.c>`_.
        assert self.cur_token_ == "FontRevision", self.cur_token_
        location, version = self.cur_token_location_, self.expect_float_()
        self.expect_symbol_(";")
        if version <= 0:
            raise FeatureLibError("Font revision numbers must be positive", location)
        return self.ast.FontRevisionStatement(version, location=location)

    def parse_conditionset_(self):
        name = self.expect_name_()

        conditions = {}
        self.expect_symbol_("{")

        while self.next_token_ != "}":
            self.advance_lexer_()
            if self.cur_token_type_ is not Lexer.NAME:
                raise FeatureLibError("Expected an axis name", self.cur_token_location_)

            axis = self.cur_token_
            if axis in conditions:
                raise FeatureLibError(
                    f"Repeated condition for axis {axis}", self.cur_token_location_
                )

            if self.next_token_type_ is Lexer.FLOAT:
                min_value = self.expect_float_()
            elif self.next_token_type_ is Lexer.NUMBER:
                min_value = self.expect_number_(variable=False)

            if self.next_token_type_ is Lexer.FLOAT:
                max_value = self.expect_float_()
            elif self.next_token_type_ is Lexer.NUMBER:
                max_value = self.expect_number_(variable=False)
            self.expect_symbol_(";")

            conditions[axis] = (min_value, max_value)

        self.expect_symbol_("}")

        finalname = self.expect_name_()
        if finalname != name:
            raise FeatureLibError('Expected "%s"' % name, self.cur_token_location_)
        return self.ast.ConditionsetStatement(name, conditions)

    def parse_block_(
        self, block, vertical, stylisticset=None, size_feature=False, cv_feature=None
    ):
        self.expect_symbol_("{")
        for symtab in self.symbol_tables_:
            symtab.enter_scope()

        statements = block.statements
        while self.next_token_ != "}" or self.cur_comments_:
            self.advance_lexer_(comments=True)
            if self.cur_token_type_ is Lexer.COMMENT:
                statements.append(
                    self.ast.Comment(self.cur_token_, location=self.cur_token_location_)
                )
            elif self.cur_token_type_ is Lexer.GLYPHCLASS:
                statements.append(self.parse_glyphclass_definition_())
            elif self.is_cur_keyword_("anchorDef"):
                statements.append(self.parse_anchordef_())
            elif self.is_cur_keyword_({"enum", "enumerate"}):
                statements.append(self.parse_enumerate_(vertical=vertical))
            elif self.is_cur_keyword_("feature"):
                statements.append(self.parse_feature_reference_())
            elif self.is_cur_keyword_("ignore"):
                statements.append(self.parse_ignore_())
            elif self.is_cur_keyword_("language"):
                statements.append(self.parse_language_())
            elif self.is_cur_keyword_("lookup"):
                statements.append(self.parse_lookup_(vertical))
            elif self.is_cur_keyword_("lookupflag"):
                statements.append(self.parse_lookupflag_())
            elif self.is_cur_keyword_("markClass"):
                statements.append(self.parse_markClass_())
            elif self.is_cur_keyword_({"pos", "position"}):
                statements.append(
                    self.parse_position_(enumerated=False, vertical=vertical)
                )
            elif self.is_cur_keyword_("script"):
                statements.append(self.parse_script_())
            elif self.is_cur_keyword_({"sub", "substitute", "rsub", "reversesub"}):
                statements.append(self.parse_substitute_())
            elif self.is_cur_keyword_("subtable"):
                statements.append(self.parse_subtable_())
            elif self.is_cur_keyword_("valueRecordDef"):
                statements.append(self.parse_valuerecord_definition_(vertical))
            elif stylisticset and self.is_cur_keyword_("featureNames"):
                statements.append(self.parse_featureNames_(stylisticset))
            elif cv_feature and self.is_cur_keyword_("cvParameters"):
                statements.append(self.parse_cvParameters_(cv_feature))
            elif size_feature and self.is_cur_keyword_("parameters"):
                statements.append(self.parse_size_parameters_())
            elif size_feature and self.is_cur_keyword_("sizemenuname"):
                statements.append(self.parse_size_menuname_())
            elif (
                self.cur_token_type_ is Lexer.NAME
                and self.cur_token_ in self.extensions
            ):
                statements.append(self.extensions[self.cur_token_](self))
            elif self.cur_token_ == ";":
                continue
            else:
                raise FeatureLibError(
                    "Expected glyph class definition or statement: got {} {}".format(
                        self.cur_token_type_, self.cur_token_
                    ),
                    self.cur_token_location_,
                )

        self.expect_symbol_("}")
        for symtab in self.symbol_tables_:
            symtab.exit_scope()

        name = self.expect_name_()
        if name != block.name.strip():
            raise FeatureLibError(
                'Expected "%s"' % block.name.strip(), self.cur_token_location_
            )
        self.expect_symbol_(";")

    def is_cur_keyword_(self, k):
        if self.cur_token_type_ is Lexer.NAME:
            if isinstance(k, type("")):  # basestring is gone in Python3
                return self.cur_token_ == k
            else:
                return self.cur_token_ in k
        return False

    def expect_class_name_(self):
        self.advance_lexer_()
        if self.cur_token_type_ is not Lexer.GLYPHCLASS:
            raise FeatureLibError("Expected @NAME", self.cur_token_location_)
        return self.cur_token_

    def expect_cid_(self):
        self.advance_lexer_()
        if self.cur_token_type_ is Lexer.CID:
            return self.cur_token_
        raise FeatureLibError("Expected a CID", self.cur_token_location_)

    def expect_filename_(self):
        self.advance_lexer_()
        if self.cur_token_type_ is not Lexer.FILENAME:
            raise FeatureLibError("Expected file name", self.cur_token_location_)
        return self.cur_token_

    def expect_glyph_(self):
        self.advance_lexer_()
        if self.cur_token_type_ is Lexer.NAME:
            return self.cur_token_.lstrip("\\")
        elif self.cur_token_type_ is Lexer.CID:
            return "cid%05d" % self.cur_token_
        raise FeatureLibError("Expected a glyph name or CID", self.cur_token_location_)

    def check_glyph_name_in_glyph_set(self, *names):
        """Adds a glyph name (just `start`) or glyph names of a
        range (`start` and `end`) which are not in the glyph set
        to the "missing list" for future error reporting.

        If no glyph set is present, does nothing.
        """
        if self.glyphNames_:
            for name in names:
                if name in self.glyphNames_:
                    continue
                if name not in self.missing:
                    self.missing[name] = self.cur_token_location_

    def expect_markClass_reference_(self):
        name = self.expect_class_name_()
        mc = self.glyphclasses_.resolve(name)
        if mc is None:
            raise FeatureLibError(
                "Unknown markClass @%s" % name, self.cur_token_location_
            )
        if not isinstance(mc, self.ast.MarkClass):
            raise FeatureLibError(
                "@%s is not a markClass" % name, self.cur_token_location_
            )
        return mc

    def expect_tag_(self):
        self.advance_lexer_()
        if self.cur_token_type_ is not Lexer.NAME:
            raise FeatureLibError("Expected a tag", self.cur_token_location_)
        if len(self.cur_token_) > 4:
            raise FeatureLibError(
                "Tags cannot be longer than 4 characters", self.cur_token_location_
            )
        return (self.cur_token_ + "    ")[:4]

    def expect_script_tag_(self):
        tag = self.expect_tag_()
        if tag == "dflt":
            raise FeatureLibError(
                '"dflt" is not a valid script tag; use "DFLT" instead',
                self.cur_token_location_,
            )
        return tag

    def expect_language_tag_(self):
        tag = self.expect_tag_()
        if tag == "DFLT":
            raise FeatureLibError(
                '"DFLT" is not a valid language tag; use "dflt" instead',
                self.cur_token_location_,
            )
        return tag

    def expect_symbol_(self, symbol):
        self.advance_lexer_()
        if self.cur_token_type_ is Lexer.SYMBOL and self.cur_token_ == symbol:
            return symbol
        raise FeatureLibError("Expected '%s'" % symbol, self.cur_token_location_)

    def expect_keyword_(self, keyword):
        self.advance_lexer_()
        if self.cur_token_type_ is Lexer.NAME and self.cur_token_ == keyword:
            return self.cur_token_
        raise FeatureLibError('Expected "%s"' % keyword, self.cur_token_location_)

    def expect_name_(self):
        self.advance_lexer_()
        if self.cur_token_type_ is Lexer.NAME:
            return self.cur_token_
        raise FeatureLibError("Expected a name", self.cur_token_location_)

    def expect_number_(self, variable=False):
        self.advance_lexer_()
        if self.cur_token_type_ is Lexer.NUMBER:
            return self.cur_token_
        if variable and self.cur_token_type_ is Lexer.SYMBOL and self.cur_token_ == "(":
            return self.expect_variable_scalar_()
        raise FeatureLibError("Expected a number", self.cur_token_location_)

    def expect_variable_scalar_(self):
        self.advance_lexer_()  # "("
        scalar = VariableScalar()
        while True:
            if self.cur_token_type_ == Lexer.SYMBOL and self.cur_token_ == ")":
                break
            location, value = self.expect_master_()
            scalar.add_value(location, value)
        return scalar

    def expect_master_(self):
        location = {}
        while True:
            if self.cur_token_type_ is not Lexer.NAME:
                raise FeatureLibError("Expected an axis name", self.cur_token_location_)
            axis = self.cur_token_
            self.advance_lexer_()
            if not (self.cur_token_type_ is Lexer.SYMBOL and self.cur_token_ == "="):
                raise FeatureLibError(
                    "Expected an equals sign", self.cur_token_location_
                )
            value = self.expect_number_()
            location[axis] = value
            if self.next_token_type_ is Lexer.NAME and self.next_token_[0] == ":":
                # Lexer has just read the value as a glyph name. We'll correct it later
                break
            self.advance_lexer_()
            if not (self.cur_token_type_ is Lexer.SYMBOL and self.cur_token_ == ","):
                raise FeatureLibError(
                    "Expected an comma or an equals sign", self.cur_token_location_
                )
            self.advance_lexer_()
        self.advance_lexer_()
        value = int(self.cur_token_[1:])
        self.advance_lexer_()
        return location, value

    def expect_any_number_(self):
        self.advance_lexer_()
        if self.cur_token_type_ in Lexer.NUMBERS:
            return self.cur_token_
        raise FeatureLibError(
            "Expected a decimal, hexadecimal or octal number", self.cur_token_location_
        )

    def expect_float_(self):
        self.advance_lexer_()
        if self.cur_token_type_ is Lexer.FLOAT:
            return self.cur_token_
        raise FeatureLibError(
            "Expected a floating-point number", self.cur_token_location_
        )

    def expect_decipoint_(self):
        if self.next_token_type_ == Lexer.FLOAT:
            return self.expect_float_()
        elif self.next_token_type_ is Lexer.NUMBER:
            return self.expect_number_() / 10
        else:
            raise FeatureLibError(
                "Expected an integer or floating-point number", self.cur_token_location_
            )

    def expect_stat_flags(self):
        value = 0
        flags = {
            "OlderSiblingFontAttribute": 1,
            "ElidableAxisValueName": 2,
        }
        while self.next_token_ != ";":
            if self.next_token_ in flags:
                name = self.expect_name_()
                value = value | flags[name]
            else:
                raise FeatureLibError(
                    f"Unexpected STAT flag {self.cur_token_}", self.cur_token_location_
                )
        return value

    def expect_stat_values_(self):
        if self.next_token_type_ == Lexer.FLOAT:
            return self.expect_float_()
        elif self.next_token_type_ is Lexer.NUMBER:
            return self.expect_number_()
        else:
            raise FeatureLibError(
                "Expected an integer or floating-point number", self.cur_token_location_
            )

    def expect_string_(self):
        self.advance_lexer_()
        if self.cur_token_type_ is Lexer.STRING:
            return self.cur_token_
        raise FeatureLibError("Expected a string", self.cur_token_location_)

    def advance_lexer_(self, comments=False):
        if comments and self.cur_comments_:
            self.cur_token_type_ = Lexer.COMMENT
            self.cur_token_, self.cur_token_location_ = self.cur_comments_.pop(0)
            return
        else:
            self.cur_token_type_, self.cur_token_, self.cur_token_location_ = (
                self.next_token_type_,
                self.next_token_,
                self.next_token_location_,
            )
        while True:
            try:
                (
                    self.next_token_type_,
                    self.next_token_,
                    self.next_token_location_,
                ) = next(self.lexer_)
            except StopIteration:
                self.next_token_type_, self.next_token_ = (None, None)
            if self.next_token_type_ != Lexer.COMMENT:
                break
            self.cur_comments_.append((self.next_token_, self.next_token_location_))

    @staticmethod
    def reverse_string_(s):
        """'abc' --> 'cba'"""
        return "".join(reversed(list(s)))

    def make_cid_range_(self, location, start, limit):
        """(location, 999, 1001) --> ["cid00999", "cid01000", "cid01001"]"""
        result = list()
        if start > limit:
            raise FeatureLibError(
                "Bad range: start should be less than limit", location
            )
        for cid in range(start, limit + 1):
            result.append("cid%05d" % cid)
        return result

    def make_glyph_range_(self, location, start, limit):
        """(location, "a.sc", "d.sc") --> ["a.sc", "b.sc", "c.sc", "d.sc"]"""
        result = list()
        if len(start) != len(limit):
            raise FeatureLibError(
                'Bad range: "%s" and "%s" should have the same length' % (start, limit),
                location,
            )

        rev = self.reverse_string_
        prefix = os.path.commonprefix([start, limit])
        suffix = rev(os.path.commonprefix([rev(start), rev(limit)]))
        if len(suffix) > 0:
            start_range = start[len(prefix) : -len(suffix)]
            limit_range = limit[len(prefix) : -len(suffix)]
        else:
            start_range = start[len(prefix) :]
            limit_range = limit[len(prefix) :]

        if start_range >= limit_range:
            raise FeatureLibError(
                "Start of range must be smaller than its end", location
            )

        uppercase = re.compile(r"^[A-Z]$")
        if uppercase.match(start_range) and uppercase.match(limit_range):
            for c in range(ord(start_range), ord(limit_range) + 1):
                result.append("%s%c%s" % (prefix, c, suffix))
            return result

        lowercase = re.compile(r"^[a-z]$")
        if lowercase.match(start_range) and lowercase.match(limit_range):
            for c in range(ord(start_range), ord(limit_range) + 1):
                result.append("%s%c%s" % (prefix, c, suffix))
            return result

        digits = re.compile(r"^[0-9]{1,3}$")
        if digits.match(start_range) and digits.match(limit_range):
            for i in range(int(start_range, 10), int(limit_range, 10) + 1):
                number = ("000" + str(i))[-len(start_range) :]
                result.append("%s%s%s" % (prefix, number, suffix))
            return result

        raise FeatureLibError('Bad range: "%s-%s"' % (start, limit), location)


class SymbolTable(object):
    def __init__(self):
        self.scopes_ = [{}]

    def enter_scope(self):
        self.scopes_.append({})

    def exit_scope(self):
        self.scopes_.pop()

    def define(self, name, item):
        self.scopes_[-1][name] = item

    def resolve(self, name):
        for scope in reversed(self.scopes_):
            item = scope.get(name)
            if item:
                return item
        return None