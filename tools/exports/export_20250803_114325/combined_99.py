
# === NexusCore/openenv\Lib\site-packages\litellm\__init__.py ===
### Hide pydantic namespace conflict warnings globally ###
import warnings

warnings.filterwarnings("ignore", message=".*conflict with protected namespace.*")
### INIT VARIABLES ############
import threading
import os
from typing import Callable, List, Optional, Dict, Union, Any, Literal, get_args
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler
from litellm.caching.caching import Cache, DualCache, RedisCache, InMemoryCache
from litellm.caching.llm_caching_handler import LLMClientCache
from litellm.types.llms.bedrock import COHERE_EMBEDDING_INPUT_TYPES
from litellm.types.utils import (
    ImageObject,
    BudgetConfig,
    all_litellm_params,
    all_litellm_params as _litellm_completion_params,
    CredentialItem,
)  # maintain backwards compatibility for root param
from litellm._logging import (
    set_verbose,
    _turn_on_debug,
    verbose_logger,
    json_logs,
    _turn_on_json,
    log_level,
)
import re
from litellm.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_FLUSH_INTERVAL_SECONDS,
    ROUTER_MAX_FALLBACKS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_REPLICATE_POLLING_RETRIES,
    DEFAULT_REPLICATE_POLLING_DELAY_SECONDS,
    LITELLM_CHAT_PROVIDERS,
    HUMANLOOP_PROMPT_CACHE_TTL_SECONDS,
    OPENAI_CHAT_COMPLETION_PARAMS,
    OPENAI_CHAT_COMPLETION_PARAMS as _openai_completion_params,  # backwards compatibility
    OPENAI_FINISH_REASONS,
    OPENAI_FINISH_REASONS as _openai_finish_reasons,  # backwards compatibility
    openai_compatible_endpoints,
    openai_compatible_providers,
    openai_text_completion_compatible_providers,
    _openai_like_providers,
    replicate_models,
    clarifai_models,
    huggingface_models,
    empower_models,
    together_ai_models,
    baseten_models,
    REPEATED_STREAMING_CHUNK_LIMIT,
    request_timeout,
    open_ai_embedding_models,
    cohere_embedding_models,
    bedrock_embedding_models,
    known_tokenizer_config,
    BEDROCK_INVOKE_PROVIDERS_LITERAL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_SOFT_BUDGET,
    DEFAULT_ALLOWED_FAILS,
)
from litellm.types.guardrails import GuardrailItem
from litellm.proxy._types import (
    KeyManagementSystem,
    KeyManagementSettings,
    LiteLLM_UpperboundKeyGenerateParams,
)
from litellm.types.proxy.management_endpoints.ui_sso import DefaultTeamSSOParams
from litellm.types.utils import StandardKeyGenerationConfig, LlmProviders
from litellm.integrations.custom_logger import CustomLogger
from litellm.litellm_core_utils.logging_callback_manager import LoggingCallbackManager
import httpx
import dotenv

litellm_mode = os.getenv("LITELLM_MODE", "DEV")  # "PRODUCTION", "DEV"
if litellm_mode == "DEV":
    dotenv.load_dotenv()
################################################
if set_verbose == True:
    _turn_on_debug()
################################################
### Callbacks /Logging / Success / Failure Handlers #####
CALLBACK_TYPES = Union[str, Callable, CustomLogger]
input_callback: List[CALLBACK_TYPES] = []
success_callback: List[CALLBACK_TYPES] = []
failure_callback: List[CALLBACK_TYPES] = []
service_callback: List[CALLBACK_TYPES] = []
logging_callback_manager = LoggingCallbackManager()
_custom_logger_compatible_callbacks_literal = Literal[
    "lago",
    "openmeter",
    "logfire",
    "literalai",
    "dynamic_rate_limiter",
    "langsmith",
    "prometheus",
    "otel",
    "datadog",
    "datadog_llm_observability",
    "galileo",
    "braintrust",
    "arize",
    "arize_phoenix",
    "langtrace",
    "gcs_bucket",
    "azure_storage",
    "opik",
    "argilla",
    "mlflow",
    "langfuse",
    "langfuse_otel",
    "pagerduty",
    "humanloop",
    "gcs_pubsub",
    "agentops",
    "anthropic_cache_control_hook",
    "bedrock_vector_store",
    "generic_api",
    "resend_email",
    "smtp_email",
    "deepeval",
    "s3_v2",
]
logged_real_time_event_types: Optional[Union[List[str], Literal["*"]]] = None
_known_custom_logger_compatible_callbacks: List = list(
    get_args(_custom_logger_compatible_callbacks_literal)
)
callbacks: List[
    Union[Callable, _custom_logger_compatible_callbacks_literal, CustomLogger]
] = []
initialized_langfuse_clients: int = 0
langfuse_default_tags: Optional[List[str]] = None
langsmith_batch_size: Optional[int] = None
prometheus_initialize_budget_metrics: Optional[bool] = False
require_auth_for_metrics_endpoint: Optional[bool] = False
argilla_batch_size: Optional[int] = None
datadog_use_v1: Optional[bool] = False  # if you want to use v1 datadog logged payload.
gcs_pub_sub_use_v1: Optional[bool] = (
    False  # if you want to use v1 gcs pubsub logged payload
)
generic_api_use_v1: Optional[bool] = (
    False  # if you want to use v1 generic api logged payload
)
argilla_transformation_object: Optional[Dict[str, Any]] = None
_async_input_callback: List[Union[str, Callable, CustomLogger]] = (
    []
)  # internal variable - async custom callbacks are routed here.
_async_success_callback: List[Union[str, Callable, CustomLogger]] = (
    []
)  # internal variable - async custom callbacks are routed here.
_async_failure_callback: List[Union[str, Callable, CustomLogger]] = (
    []
)  # internal variable - async custom callbacks are routed here.
pre_call_rules: List[Callable] = []
post_call_rules: List[Callable] = []
turn_off_message_logging: Optional[bool] = False
log_raw_request_response: bool = False
redact_messages_in_exceptions: Optional[bool] = False
redact_user_api_key_info: Optional[bool] = False
filter_invalid_headers: Optional[bool] = False
add_user_information_to_llm_headers: Optional[bool] = (
    None  # adds user_id, team_id, token hash (params from StandardLoggingMetadata) to request headers
)
store_audit_logs = False  # Enterprise feature, allow users to see audit logs
### end of callbacks #############

email: Optional[str] = (
    None  # Not used anymore, will be removed in next MAJOR release - https://github.com/BerriAI/litellm/discussions/648
)
token: Optional[str] = (
    None  # Not used anymore, will be removed in next MAJOR release - https://github.com/BerriAI/litellm/discussions/648
)
telemetry = True
max_tokens: int = DEFAULT_MAX_TOKENS  # OpenAI Defaults
drop_params = bool(os.getenv("LITELLM_DROP_PARAMS", False))
modify_params = bool(os.getenv("LITELLM_MODIFY_PARAMS", False))
retry = True
### AUTH ###
api_key: Optional[str] = None
openai_key: Optional[str] = None
groq_key: Optional[str] = None
databricks_key: Optional[str] = None
openai_like_key: Optional[str] = None
azure_key: Optional[str] = None
anthropic_key: Optional[str] = None
replicate_key: Optional[str] = None
cohere_key: Optional[str] = None
infinity_key: Optional[str] = None
clarifai_key: Optional[str] = None
maritalk_key: Optional[str] = None
ai21_key: Optional[str] = None
ollama_key: Optional[str] = None
openrouter_key: Optional[str] = None
datarobot_key: Optional[str] = None
predibase_key: Optional[str] = None
huggingface_key: Optional[str] = None
vertex_project: Optional[str] = None
vertex_location: Optional[str] = None
predibase_tenant_id: Optional[str] = None
togetherai_api_key: Optional[str] = None
cloudflare_api_key: Optional[str] = None
baseten_key: Optional[str] = None
llama_api_key: Optional[str] = None
aleph_alpha_key: Optional[str] = None
nlp_cloud_key: Optional[str] = None
novita_api_key: Optional[str] = None
snowflake_key: Optional[str] = None
nebius_key: Optional[str] = None
common_cloud_provider_auth_params: dict = {
    "params": ["project", "region_name", "token"],
    "providers": ["vertex_ai", "bedrock", "watsonx", "azure", "vertex_ai_beta"],
}
use_litellm_proxy: bool = (
    False  # when True, requests will be sent to the specified litellm proxy endpoint
)
use_client: bool = False
ssl_verify: Union[str, bool] = True
ssl_certificate: Optional[str] = None
disable_streaming_logging: bool = False
disable_token_counter: bool = False
disable_add_transform_inline_image_block: bool = False
disable_add_user_agent_to_request_tags: bool = False
in_memory_llm_clients_cache: LLMClientCache = LLMClientCache()
safe_memory_mode: bool = False
enable_azure_ad_token_refresh: Optional[bool] = False
### DEFAULT AZURE API VERSION ###
AZURE_DEFAULT_API_VERSION = "2025-02-01-preview"  # this is updated to the latest
### DEFAULT WATSONX API VERSION ###
WATSONX_DEFAULT_API_VERSION = "2024-03-13"
### COHERE EMBEDDINGS DEFAULT TYPE ###
COHERE_DEFAULT_EMBEDDING_INPUT_TYPE: COHERE_EMBEDDING_INPUT_TYPES = "search_document"
### CREDENTIALS ###
credential_list: List[CredentialItem] = []
### GUARDRAILS ###
llamaguard_model_name: Optional[str] = None
openai_moderations_model_name: Optional[str] = None
presidio_ad_hoc_recognizers: Optional[str] = None
google_moderation_confidence_threshold: Optional[float] = None
llamaguard_unsafe_content_categories: Optional[str] = None
blocked_user_list: Optional[Union[str, List]] = None
banned_keywords_list: Optional[Union[str, List]] = None
llm_guard_mode: Literal["all", "key-specific", "request-specific"] = "all"
guardrail_name_config_map: Dict[str, GuardrailItem] = {}
##################
### PREVIEW FEATURES ###
enable_preview_features: bool = False
return_response_headers: bool = (
    False  # get response headers from LLM Api providers - example x-remaining-requests,
)
enable_json_schema_validation: bool = False
##################
logging: bool = True
enable_loadbalancing_on_batch_endpoints: Optional[bool] = None
enable_caching_on_provider_specific_optional_params: bool = (
    False  # feature-flag for caching on optional params - e.g. 'top_k'
)
caching: bool = (
    False  # Not used anymore, will be removed in next MAJOR release - https://github.com/BerriAI/litellm/discussions/648
)
caching_with_models: bool = (
    False  # # Not used anymore, will be removed in next MAJOR release - https://github.com/BerriAI/litellm/discussions/648
)
cache: Optional[Cache] = (
    None  # cache object <- use this - https://docs.litellm.ai/docs/caching
)
default_in_memory_ttl: Optional[float] = None
default_redis_ttl: Optional[float] = None
default_redis_batch_cache_expiry: Optional[float] = None
model_alias_map: Dict[str, str] = {}
model_group_alias_map: Dict[str, str] = {}
max_budget: float = 0.0  # set the max budget across all providers
budget_duration: Optional[str] = (
    None  # proxy only - resets budget after fixed duration. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d").
)
default_soft_budget: float = (
    DEFAULT_SOFT_BUDGET  # by default all litellm proxy keys have a soft budget of 50.0
)
forward_traceparent_to_llm_provider: bool = False


_current_cost = 0.0  # private variable, used if max budget is set
error_logs: Dict = {}
add_function_to_prompt: bool = (
    False  # if function calling not supported by api, append function call details to system prompt
)
client_session: Optional[httpx.Client] = None
aclient_session: Optional[httpx.AsyncClient] = None
model_fallbacks: Optional[List] = None  # Deprecated for 'litellm.fallbacks'
model_cost_map_url: str = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
)
suppress_debug_info = False
dynamodb_table_name: Optional[str] = None
s3_callback_params: Optional[Dict] = None
generic_logger_headers: Optional[Dict] = None
default_key_generate_params: Optional[Dict] = None
upperbound_key_generate_params: Optional[LiteLLM_UpperboundKeyGenerateParams] = None
key_generation_settings: Optional[StandardKeyGenerationConfig] = None
default_internal_user_params: Optional[Dict] = None
default_team_params: Optional[Union[DefaultTeamSSOParams, Dict]] = None
default_team_settings: Optional[List] = None
max_user_budget: Optional[float] = None
default_max_internal_user_budget: Optional[float] = None
max_internal_user_budget: Optional[float] = None
max_ui_session_budget: Optional[float] = 10  # $10 USD budgets for UI Chat sessions
internal_user_budget_duration: Optional[str] = None
tag_budget_config: Optional[Dict[str, BudgetConfig]] = None
max_end_user_budget: Optional[float] = None
disable_end_user_cost_tracking: Optional[bool] = None
disable_end_user_cost_tracking_prometheus_only: Optional[bool] = None
enable_end_user_cost_tracking_prometheus_only: Optional[bool] = None
custom_prometheus_metadata_labels: List[str] = []
prometheus_metrics_config: Optional[List] = None
disable_add_prefix_to_prompt: bool = (
    False  # used by anthropic, to disable adding prefix to prompt
)
#### REQUEST PRIORITIZATION #####
priority_reservation: Optional[Dict[str, float]] = None


######## Networking Settings ########
use_aiohttp_transport: bool = (
    True  # Older variable, aiohttp is now the default. use disable_aiohttp_transport instead.
)
disable_aiohttp_transport: bool = False  # Set this to true to use httpx instead
force_ipv4: bool = (
    False  # when True, litellm will force ipv4 for all LLM requests. Some users have seen httpx ConnectionError when using ipv6.
)
module_level_aclient = AsyncHTTPHandler(
    timeout=request_timeout, client_alias="module level aclient"
)
module_level_client = HTTPHandler(timeout=request_timeout)

#### RETRIES ####
num_retries: Optional[int] = None  # per model endpoint
max_fallbacks: Optional[int] = None
default_fallbacks: Optional[List] = None
fallbacks: Optional[List] = None
context_window_fallbacks: Optional[List] = None
content_policy_fallbacks: Optional[List] = None
allowed_fails: int = 3
num_retries_per_request: Optional[int] = (
    None  # for the request overall (incl. fallbacks + model retries)
)
####### SECRET MANAGERS #####################
secret_manager_client: Optional[Any] = (
    None  # list of instantiated key management clients - e.g. azure kv, infisical, etc.
)
_google_kms_resource_name: Optional[str] = None
_key_management_system: Optional[KeyManagementSystem] = None
_key_management_settings: KeyManagementSettings = KeyManagementSettings()
#### PII MASKING ####
output_parse_pii: bool = False
#############################################
from litellm.litellm_core_utils.get_model_cost_map import get_model_cost_map

model_cost = get_model_cost_map(url=model_cost_map_url)
custom_prompt_dict: Dict[str, dict] = {}
check_provider_endpoint = False


####### THREAD-SPECIFIC DATA ####################
class MyLocal(threading.local):
    def __init__(self):
        self.user = "Hello World"


_thread_context = MyLocal()


def identify(event_details):
    # Store user in thread local data
    if "user" in event_details:
        _thread_context.user = event_details["user"]


####### ADDITIONAL PARAMS ################### configurable params if you use proxy models like Helicone, map spend to org id, etc.
api_base: Optional[str] = None
headers = None
api_version = None
organization = None
project = None
config_path = None
vertex_ai_safety_settings: Optional[dict] = None
BEDROCK_CONVERSE_MODELS = [
    "anthropic.claude-opus-4-20250514-v1:0",
    "anthropic.claude-sonnet-4-20250514-v1:0",
    "anthropic.claude-3-7-sonnet-20250219-v1:0",
    "anthropic.claude-3-5-haiku-20241022-v1:0",
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "anthropic.claude-3-opus-20240229-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-v2",
    "anthropic.claude-v2:1",
    "anthropic.claude-v1",
    "anthropic.claude-instant-v1",
    "ai21.jamba-instruct-v1:0",
    "ai21.jamba-1-5-mini-v1:0",
    "ai21.jamba-1-5-large-v1:0",
    "meta.llama3-70b-instruct-v1:0",
    "meta.llama3-8b-instruct-v1:0",
    "meta.llama3-1-8b-instruct-v1:0",
    "meta.llama3-1-70b-instruct-v1:0",
    "meta.llama3-1-405b-instruct-v1:0",
    "meta.llama3-70b-instruct-v1:0",
    "mistral.mistral-large-2407-v1:0",
    "mistral.mistral-large-2402-v1:0",
    "mistral.mistral-small-2402-v1:0",
    "meta.llama3-2-1b-instruct-v1:0",
    "meta.llama3-2-3b-instruct-v1:0",
    "meta.llama3-2-11b-instruct-v1:0",
    "meta.llama3-2-90b-instruct-v1:0",
]

####### COMPLETION MODELS ###################
open_ai_chat_completion_models: List = []
open_ai_text_completion_models: List = []
cohere_models: List = []
cohere_chat_models: List = []
mistral_chat_models: List = []
text_completion_codestral_models: List = []
anthropic_models: List = []
openrouter_models: List = []
datarobot_models: List = []
vertex_language_models: List = []
vertex_vision_models: List = []
vertex_chat_models: List = []
vertex_code_chat_models: List = []
vertex_ai_image_models: List = []
vertex_text_models: List = []
vertex_code_text_models: List = []
vertex_embedding_models: List = []
vertex_anthropic_models: List = []
vertex_llama3_models: List = []
vertex_ai_ai21_models: List = []
vertex_mistral_models: List = []
ai21_models: List = []
ai21_chat_models: List = []
nlp_cloud_models: List = []
aleph_alpha_models: List = []
bedrock_models: List = []
bedrock_converse_models: List = BEDROCK_CONVERSE_MODELS
fireworks_ai_models: List = []
fireworks_ai_embedding_models: List = []
deepinfra_models: List = []
perplexity_models: List = []
watsonx_models: List = []
gemini_models: List = []
xai_models: List = []
deepseek_models: List = []
azure_ai_models: List = []
jina_ai_models: List = []
voyage_models: List = []
infinity_models: List = []
databricks_models: List = []
cloudflare_models: List = []
codestral_models: List = []
friendliai_models: List = []
featherless_ai_models: List = []
palm_models: List = []
groq_models: List = []
azure_models: List = []
azure_text_models: List = []
anyscale_models: List = []
cerebras_models: List = []
galadriel_models: List = []
sambanova_models: List = []
novita_models: List = []
assemblyai_models: List = []
snowflake_models: List = []
llama_models: List = []
nscale_models: List = []
nebius_models: List = []
nebius_embedding_models: List = []
deepgram_models: List = []


def is_bedrock_pricing_only_model(key: str) -> bool:
    """
    Excludes keys with the pattern 'bedrock/<region>/<model>'. These are in the model_prices_and_context_window.json file for pricing purposes only.

    Args:
        key (str): A key to filter.

    Returns:
        bool: True if the key matches the Bedrock pattern, False otherwise.
    """
    # Regex to match 'bedrock/<region>/<model>'
    bedrock_pattern = re.compile(r"^bedrock/[a-zA-Z0-9_-]+/.+$")

    if "month-commitment" in key:
        return True

    is_match = bedrock_pattern.match(key)
    return is_match is not None


def is_openai_finetune_model(key: str) -> bool:
    """
    Excludes model cost keys with the pattern 'ft:<model>'. These are in the model_prices_and_context_window.json file for pricing purposes only.

    Args:
        key (str): A key to filter.

    Returns:
        bool: True if the key matches the OpenAI finetune pattern, False otherwise.
    """
    return key.startswith("ft:") and not key.count(":") > 1


def add_known_models():
    for key, value in model_cost.items():
        if value.get("litellm_provider") == "openai" and not is_openai_finetune_model(
            key
        ):
            open_ai_chat_completion_models.append(key)
        elif value.get("litellm_provider") == "text-completion-openai":
            open_ai_text_completion_models.append(key)
        elif value.get("litellm_provider") == "azure_text":
            azure_text_models.append(key)
        elif value.get("litellm_provider") == "cohere":
            cohere_models.append(key)
        elif value.get("litellm_provider") == "cohere_chat":
            cohere_chat_models.append(key)
        elif value.get("litellm_provider") == "mistral":
            mistral_chat_models.append(key)
        elif value.get("litellm_provider") == "anthropic":
            anthropic_models.append(key)
        elif value.get("litellm_provider") == "empower":
            empower_models.append(key)
        elif value.get("litellm_provider") == "openrouter":
            openrouter_models.append(key)
        elif value.get("litellm_provider") == "datarobot":
            datarobot_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-text-models":
            vertex_text_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-code-text-models":
            vertex_code_text_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-language-models":
            vertex_language_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-vision-models":
            vertex_vision_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-chat-models":
            vertex_chat_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-code-chat-models":
            vertex_code_chat_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-embedding-models":
            vertex_embedding_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-anthropic_models":
            key = key.replace("vertex_ai/", "")
            vertex_anthropic_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-llama_models":
            key = key.replace("vertex_ai/", "")
            vertex_llama3_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-mistral_models":
            key = key.replace("vertex_ai/", "")
            vertex_mistral_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-ai21_models":
            key = key.replace("vertex_ai/", "")
            vertex_ai_ai21_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-image-models":
            key = key.replace("vertex_ai/", "")
            vertex_ai_image_models.append(key)
        elif value.get("litellm_provider") == "ai21":
            if value.get("mode") == "chat":
                ai21_chat_models.append(key)
            else:
                ai21_models.append(key)
        elif value.get("litellm_provider") == "nlp_cloud":
            nlp_cloud_models.append(key)
        elif value.get("litellm_provider") == "aleph_alpha":
            aleph_alpha_models.append(key)
        elif value.get(
            "litellm_provider"
        ) == "bedrock" and not is_bedrock_pricing_only_model(key):
            bedrock_models.append(key)
        elif value.get("litellm_provider") == "bedrock_converse":
            bedrock_converse_models.append(key)
        elif value.get("litellm_provider") == "deepinfra":
            deepinfra_models.append(key)
        elif value.get("litellm_provider") == "perplexity":
            perplexity_models.append(key)
        elif value.get("litellm_provider") == "watsonx":
            watsonx_models.append(key)
        elif value.get("litellm_provider") == "gemini":
            gemini_models.append(key)
        elif value.get("litellm_provider") == "fireworks_ai":
            # ignore the 'up-to', '-to-' model names -> not real models. just for cost tracking based on model params.
            if "-to-" not in key and "fireworks-ai-default" not in key:
                fireworks_ai_models.append(key)
        elif value.get("litellm_provider") == "fireworks_ai-embedding-models":
            # ignore the 'up-to', '-to-' model names -> not real models. just for cost tracking based on model params.
            if "-to-" not in key:
                fireworks_ai_embedding_models.append(key)
        elif value.get("litellm_provider") == "text-completion-codestral":
            text_completion_codestral_models.append(key)
        elif value.get("litellm_provider") == "xai":
            xai_models.append(key)
        elif value.get("litellm_provider") == "deepseek":
            deepseek_models.append(key)
        elif value.get("litellm_provider") == "meta_llama":
            llama_models.append(key)
        elif value.get("litellm_provider") == "nscale":
            nscale_models.append(key)
        elif value.get("litellm_provider") == "azure_ai":
            azure_ai_models.append(key)
        elif value.get("litellm_provider") == "voyage":
            voyage_models.append(key)
        elif value.get("litellm_provider") == "infinity":
            infinity_models.append(key)
        elif value.get("litellm_provider") == "databricks":
            databricks_models.append(key)
        elif value.get("litellm_provider") == "cloudflare":
            cloudflare_models.append(key)
        elif value.get("litellm_provider") == "codestral":
            codestral_models.append(key)
        elif value.get("litellm_provider") == "friendliai":
            friendliai_models.append(key)
        elif value.get("litellm_provider") == "palm":
            palm_models.append(key)
        elif value.get("litellm_provider") == "groq":
            groq_models.append(key)
        elif value.get("litellm_provider") == "azure":
            azure_models.append(key)
        elif value.get("litellm_provider") == "anyscale":
            anyscale_models.append(key)
        elif value.get("litellm_provider") == "cerebras":
            cerebras_models.append(key)
        elif value.get("litellm_provider") == "galadriel":
            galadriel_models.append(key)
        elif value.get("litellm_provider") == "sambanova":
            sambanova_models.append(key)
        elif value.get("litellm_provider") == "novita":
            novita_models.append(key)
        elif value.get("litellm_provider") == "nebius-chat-models":
            nebius_models.append(key)
        elif value.get("litellm_provider") == "nebius-embedding-models":
            nebius_embedding_models.append(key)
        elif value.get("litellm_provider") == "assemblyai":
            assemblyai_models.append(key)
        elif value.get("litellm_provider") == "jina_ai":
            jina_ai_models.append(key)
        elif value.get("litellm_provider") == "snowflake":
            snowflake_models.append(key)
        elif value.get("litellm_provider") == "featherless_ai":
            featherless_ai_models.append(key)
        elif value.get("litellm_provider") == "deepgram":
            deepgram_models.append(key)


add_known_models()
# known openai compatible endpoints - we'll eventually move this list to the model_prices_and_context_window.json dictionary

# this is maintained for Exception Mapping


# used for Cost Tracking & Token counting
# https://azure.microsoft.com/en-in/pricing/details/cognitive-services/openai-service/
# Azure returns gpt-35-turbo in their responses, we need to map this to azure/gpt-3.5-turbo for token counting
azure_llms = {
    "gpt-35-turbo": "azure/gpt-35-turbo",
    "gpt-35-turbo-16k": "azure/gpt-35-turbo-16k",
    "gpt-35-turbo-instruct": "azure/gpt-35-turbo-instruct",
}

azure_embedding_models = {
    "ada": "azure/ada",
}

petals_models = [
    "petals-team/StableBeluga2",
]

ollama_models = ["llama2"]

maritalk_models = ["maritalk"]


model_list = (
    open_ai_chat_completion_models
    + open_ai_text_completion_models
    + cohere_models
    + cohere_chat_models
    + anthropic_models
    + replicate_models
    + openrouter_models
    + datarobot_models
    + huggingface_models
    + vertex_chat_models
    + vertex_text_models
    + ai21_models
    + ai21_chat_models
    + together_ai_models
    + baseten_models
    + aleph_alpha_models
    + nlp_cloud_models
    + ollama_models
    + bedrock_models
    + deepinfra_models
    + perplexity_models
    + maritalk_models
    + vertex_language_models
    + watsonx_models
    + gemini_models
    + text_completion_codestral_models
    + xai_models
    + deepseek_models
    + azure_ai_models
    + voyage_models
    + infinity_models
    + databricks_models
    + cloudflare_models
    + codestral_models
    + friendliai_models
    + palm_models
    + groq_models
    + azure_models
    + anyscale_models
    + cerebras_models
    + galadriel_models
    + sambanova_models
    + azure_text_models
    + novita_models
    + assemblyai_models
    + jina_ai_models
    + snowflake_models
    + llama_models
    + featherless_ai_models
    + nscale_models
    + deepgram_models
)

model_list_set = set(model_list)

provider_list: List[Union[LlmProviders, str]] = list(LlmProviders)


models_by_provider: dict = {
    "openai": open_ai_chat_completion_models + open_ai_text_completion_models,
    "text-completion-openai": open_ai_text_completion_models,
    "cohere": cohere_models + cohere_chat_models,
    "cohere_chat": cohere_chat_models,
    "anthropic": anthropic_models,
    "replicate": replicate_models,
    "huggingface": huggingface_models,
    "together_ai": together_ai_models,
    "baseten": baseten_models,
    "openrouter": openrouter_models,
    "datarobot": datarobot_models,
    "vertex_ai": vertex_chat_models
    + vertex_text_models
    + vertex_anthropic_models
    + vertex_vision_models
    + vertex_language_models,
    "ai21": ai21_models,
    "bedrock": bedrock_models + bedrock_converse_models,
    "petals": petals_models,
    "ollama": ollama_models,
    "deepinfra": deepinfra_models,
    "perplexity": perplexity_models,
    "maritalk": maritalk_models,
    "watsonx": watsonx_models,
    "gemini": gemini_models,
    "fireworks_ai": fireworks_ai_models + fireworks_ai_embedding_models,
    "aleph_alpha": aleph_alpha_models,
    "text-completion-codestral": text_completion_codestral_models,
    "xai": xai_models,
    "deepseek": deepseek_models,
    "mistral": mistral_chat_models,
    "azure_ai": azure_ai_models,
    "voyage": voyage_models,
    "infinity": infinity_models,
    "databricks": databricks_models,
    "cloudflare": cloudflare_models,
    "codestral": codestral_models,
    "nlp_cloud": nlp_cloud_models,
    "friendliai": friendliai_models,
    "palm": palm_models,
    "groq": groq_models,
    "azure": azure_models + azure_text_models,
    "azure_text": azure_text_models,
    "anyscale": anyscale_models,
    "cerebras": cerebras_models,
    "galadriel": galadriel_models,
    "sambanova": sambanova_models,
    "novita": novita_models,
    "nebius": nebius_models + nebius_embedding_models,
    "assemblyai": assemblyai_models,
    "jina_ai": jina_ai_models,
    "snowflake": snowflake_models,
    "meta_llama": llama_models,
    "nscale": nscale_models,
    "featherless_ai": featherless_ai_models,
    "deepgram": deepgram_models,
}

# mapping for those models which have larger equivalents
longer_context_model_fallback_dict: dict = {
    # openai chat completion models
    "gpt-3.5-turbo": "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-0301": "gpt-3.5-turbo-16k-0301",
    "gpt-3.5-turbo-0613": "gpt-3.5-turbo-16k-0613",
    "gpt-4": "gpt-4-32k",
    "gpt-4-0314": "gpt-4-32k-0314",
    "gpt-4-0613": "gpt-4-32k-0613",
    # anthropic
    "claude-instant-1": "claude-2",
    "claude-instant-1.2": "claude-2",
    # vertexai
    "chat-bison": "chat-bison-32k",
    "chat-bison@001": "chat-bison-32k",
    "codechat-bison": "codechat-bison-32k",
    "codechat-bison@001": "codechat-bison-32k",
    # openrouter
    "openrouter/openai/gpt-3.5-turbo": "openrouter/openai/gpt-3.5-turbo-16k",
    "openrouter/anthropic/claude-instant-v1": "openrouter/anthropic/claude-2",
}

####### EMBEDDING MODELS ###################

all_embedding_models = (
    open_ai_embedding_models
    + cohere_embedding_models
    + bedrock_embedding_models
    + vertex_embedding_models
    + fireworks_ai_embedding_models
    + nebius_embedding_models
)

####### IMAGE GENERATION MODELS ###################
openai_image_generation_models = ["dall-e-2", "dall-e-3"]

from .timeout import timeout
from .cost_calculator import completion_cost
from litellm.litellm_core_utils.litellm_logging import Logging, modify_integration
from litellm.litellm_core_utils.get_llm_provider_logic import get_llm_provider
from litellm.litellm_core_utils.core_helpers import remove_index_from_tool_calls
from litellm.litellm_core_utils.token_counter import get_modified_max_tokens
from .utils import (
    client,
    exception_type,
    get_optional_params,
    get_response_string,
    token_counter,
    create_pretrained_tokenizer,
    create_tokenizer,
    supports_function_calling,
    supports_web_search,
    supports_url_context,
    supports_response_schema,
    supports_parallel_function_calling,
    supports_vision,
    supports_audio_input,
    supports_audio_output,
    supports_system_messages,
    supports_reasoning,
    get_litellm_params,
    acreate,
    get_max_tokens,
    get_model_info,
    register_prompt_template,
    validate_environment,
    check_valid_key,
    register_model,
    encode,
    decode,
    _calculate_retry_after,
    _should_retry,
    get_supported_openai_params,
    get_api_base,
    get_first_chars_messages,
    ModelResponse,
    ModelResponseStream,
    EmbeddingResponse,
    ImageResponse,
    TranscriptionResponse,
    TextCompletionResponse,
    get_provider_fields,
    ModelResponseListIterator,
    get_valid_models,
)

ALL_LITELLM_RESPONSE_TYPES = [
    ModelResponse,
    EmbeddingResponse,
    ImageResponse,
    TranscriptionResponse,
    TextCompletionResponse,
]

from .llms.custom_llm import CustomLLM
from .llms.bedrock.chat.converse_transformation import AmazonConverseConfig
from .llms.openai_like.chat.handler import OpenAILikeChatConfig
from .llms.aiohttp_openai.chat.transformation import AiohttpOpenAIChatConfig
from .llms.galadriel.chat.transformation import GaladrielChatConfig
from .llms.github.chat.transformation import GithubChatConfig
from .llms.empower.chat.transformation import EmpowerChatConfig
from .llms.huggingface.chat.transformation import HuggingFaceChatConfig
from .llms.huggingface.embedding.transformation import HuggingFaceEmbeddingConfig
from .llms.oobabooga.chat.transformation import OobaboogaConfig
from .llms.maritalk import MaritalkConfig
from .llms.openrouter.chat.transformation import OpenrouterConfig
from .llms.datarobot.chat.transformation import DataRobotConfig
from .llms.anthropic.chat.transformation import AnthropicConfig
from .llms.anthropic.common_utils import AnthropicModelInfo
from .llms.groq.stt.transformation import GroqSTTConfig
from .llms.anthropic.completion.transformation import AnthropicTextConfig
from .llms.triton.completion.transformation import TritonConfig
from .llms.triton.completion.transformation import TritonGenerateConfig
from .llms.triton.completion.transformation import TritonInferConfig
from .llms.triton.embedding.transformation import TritonEmbeddingConfig
from .llms.huggingface.rerank.transformation import HuggingFaceRerankConfig
from .llms.databricks.chat.transformation import DatabricksConfig
from .llms.databricks.embed.transformation import DatabricksEmbeddingConfig
from .llms.predibase.chat.transformation import PredibaseConfig
from .llms.replicate.chat.transformation import ReplicateConfig
from .llms.cohere.completion.transformation import CohereTextConfig as CohereConfig
from .llms.snowflake.chat.transformation import SnowflakeConfig
from .llms.cohere.rerank.transformation import CohereRerankConfig
from .llms.cohere.rerank_v2.transformation import CohereRerankV2Config
from .llms.azure_ai.rerank.transformation import AzureAIRerankConfig
from .llms.infinity.rerank.transformation import InfinityRerankConfig
from .llms.jina_ai.rerank.transformation import JinaAIRerankConfig
from .llms.clarifai.chat.transformation import ClarifaiConfig
from .llms.ai21.chat.transformation import AI21ChatConfig, AI21ChatConfig as AI21Config
from .llms.meta_llama.chat.transformation import LlamaAPIConfig
from .llms.anthropic.experimental_pass_through.messages.transformation import (
    AnthropicMessagesConfig,
)
from .llms.bedrock.messages.invoke_transformations.anthropic_claude3_transformation import (
    AmazonAnthropicClaude3MessagesConfig,
)
from .llms.together_ai.chat import TogetherAIConfig
from .llms.together_ai.completion.transformation import TogetherAITextCompletionConfig
from .llms.cloudflare.chat.transformation import CloudflareChatConfig
from .llms.novita.chat.transformation import NovitaConfig
from .llms.deprecated_providers.palm import (
    PalmConfig,
)  # here to prevent breaking changes
from .llms.nlp_cloud.chat.handler import NLPCloudConfig
from .llms.petals.completion.transformation import PetalsConfig
from .llms.deprecated_providers.aleph_alpha import AlephAlphaConfig
from .llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import (
    VertexGeminiConfig,
    VertexGeminiConfig as VertexAIConfig,
)
from .llms.gemini.common_utils import GeminiModelInfo
from .llms.gemini.chat.transformation import (
    GoogleAIStudioGeminiConfig,
    GoogleAIStudioGeminiConfig as GeminiConfig,  # aliased to maintain backwards compatibility
)


from .llms.vertex_ai.vertex_embeddings.transformation import (
    VertexAITextEmbeddingConfig,
)

vertexAITextEmbeddingConfig = VertexAITextEmbeddingConfig()

from .llms.vertex_ai.vertex_ai_partner_models.anthropic.transformation import (
    VertexAIAnthropicConfig,
)
from .llms.vertex_ai.vertex_ai_partner_models.llama3.transformation import (
    VertexAILlama3Config,
)
from .llms.vertex_ai.vertex_ai_partner_models.ai21.transformation import (
    VertexAIAi21Config,
)
from .llms.ollama.chat.transformation import OllamaChatConfig
from .llms.ollama.completion.transformation import OllamaConfig
from .llms.sagemaker.completion.transformation import SagemakerConfig
from .llms.sagemaker.chat.transformation import SagemakerChatConfig
from .llms.bedrock.chat.invoke_handler import (
    AmazonCohereChatConfig,
    bedrock_tool_name_mappings,
)

from .llms.bedrock.common_utils import (
    AmazonBedrockGlobalConfig,
)
from .llms.bedrock.chat.invoke_transformations.amazon_ai21_transformation import (
    AmazonAI21Config,
)
from .llms.bedrock.chat.invoke_transformations.amazon_nova_transformation import (
    AmazonInvokeNovaConfig,
)
from .llms.bedrock.chat.invoke_transformations.anthropic_claude2_transformation import (
    AmazonAnthropicConfig,
)
from .llms.bedrock.chat.invoke_transformations.anthropic_claude3_transformation import (
    AmazonAnthropicClaude3Config,
)
from .llms.bedrock.chat.invoke_transformations.amazon_cohere_transformation import (
    AmazonCohereConfig,
)
from .llms.bedrock.chat.invoke_transformations.amazon_llama_transformation import (
    AmazonLlamaConfig,
)
from .llms.bedrock.chat.invoke_transformations.amazon_deepseek_transformation import (
    AmazonDeepSeekR1Config,
)
from .llms.bedrock.chat.invoke_transformations.amazon_mistral_transformation import (
    AmazonMistralConfig,
)
from .llms.bedrock.chat.invoke_transformations.amazon_titan_transformation import (
    AmazonTitanConfig,
)
from .llms.bedrock.chat.invoke_transformations.base_invoke_transformation import (
    AmazonInvokeConfig,
)

from .llms.bedrock.image.amazon_stability1_transformation import AmazonStabilityConfig
from .llms.bedrock.image.amazon_stability3_transformation import AmazonStability3Config
from .llms.bedrock.image.amazon_nova_canvas_transformation import AmazonNovaCanvasConfig
from .llms.bedrock.embed.amazon_titan_g1_transformation import AmazonTitanG1Config
from .llms.bedrock.embed.amazon_titan_multimodal_transformation import (
    AmazonTitanMultimodalEmbeddingG1Config,
)
from .llms.bedrock.embed.amazon_titan_v2_transformation import (
    AmazonTitanV2Config,
)
from .llms.cohere.chat.transformation import CohereChatConfig
from .llms.bedrock.embed.cohere_transformation import BedrockCohereEmbeddingConfig
from .llms.openai.openai import OpenAIConfig, MistralEmbeddingConfig
from .llms.openai.image_variations.transformation import OpenAIImageVariationConfig
from .llms.deepinfra.chat.transformation import DeepInfraConfig
from .llms.deepgram.audio_transcription.transformation import (
    DeepgramAudioTranscriptionConfig,
)
from .llms.topaz.common_utils import TopazModelInfo
from .llms.topaz.image_variations.transformation import TopazImageVariationConfig
from litellm.llms.openai.completion.transformation import OpenAITextCompletionConfig
from .llms.groq.chat.transformation import GroqChatConfig
from .llms.voyage.embedding.transformation import VoyageEmbeddingConfig
from .llms.infinity.embedding.transformation import InfinityEmbeddingConfig
from .llms.azure_ai.chat.transformation import AzureAIStudioConfig
from .llms.mistral.mistral_chat_transformation import MistralConfig
from .llms.openai.responses.transformation import OpenAIResponsesAPIConfig
from .llms.azure.responses.transformation import AzureOpenAIResponsesAPIConfig
from .llms.openai.chat.o_series_transformation import (
    OpenAIOSeriesConfig as OpenAIO1Config,  # maintain backwards compatibility
    OpenAIOSeriesConfig,
)

from .llms.snowflake.chat.transformation import SnowflakeConfig

openaiOSeriesConfig = OpenAIOSeriesConfig()
from .llms.openai.chat.gpt_transformation import (
    OpenAIGPTConfig,
)
from .llms.openai.transcriptions.whisper_transformation import (
    OpenAIWhisperAudioTranscriptionConfig,
)
from .llms.openai.transcriptions.gpt_transformation import (
    OpenAIGPTAudioTranscriptionConfig,
)

openAIGPTConfig = OpenAIGPTConfig()
from .llms.openai.chat.gpt_audio_transformation import (
    OpenAIGPTAudioConfig,
)

openAIGPTAudioConfig = OpenAIGPTAudioConfig()

from .llms.nvidia_nim.chat.transformation import NvidiaNimConfig
from .llms.nvidia_nim.embed import NvidiaNimEmbeddingConfig

nvidiaNimConfig = NvidiaNimConfig()
nvidiaNimEmbeddingConfig = NvidiaNimEmbeddingConfig()

from .llms.featherless_ai.chat.transformation import FeatherlessAIConfig
from .llms.cerebras.chat import CerebrasConfig
from .llms.sambanova.chat import SambanovaConfig
from .llms.ai21.chat.transformation import AI21ChatConfig
from .llms.fireworks_ai.chat.transformation import FireworksAIConfig
from .llms.fireworks_ai.completion.transformation import FireworksAITextCompletionConfig
from .llms.fireworks_ai.audio_transcription.transformation import (
    FireworksAIAudioTranscriptionConfig,
)
from .llms.fireworks_ai.embed.fireworks_ai_transformation import (
    FireworksAIEmbeddingConfig,
)
from .llms.friendliai.chat.transformation import FriendliaiChatConfig
from .llms.jina_ai.embedding.transformation import JinaAIEmbeddingConfig
from .llms.xai.chat.transformation import XAIChatConfig
from .llms.xai.common_utils import XAIModelInfo
from .llms.volcengine import VolcEngineConfig
from .llms.codestral.completion.transformation import CodestralTextCompletionConfig
from .llms.azure.azure import (
    AzureOpenAIError,
    AzureOpenAIAssistantsAPIConfig,
)

from .llms.azure.chat.gpt_transformation import AzureOpenAIConfig
from .llms.azure.completion.transformation import AzureOpenAITextConfig
from .llms.hosted_vllm.chat.transformation import HostedVLLMChatConfig
from .llms.llamafile.chat.transformation import LlamafileChatConfig
from .llms.litellm_proxy.chat.transformation import LiteLLMProxyChatConfig
from .llms.vllm.completion.transformation import VLLMConfig
from .llms.deepseek.chat.transformation import DeepSeekChatConfig
from .llms.lm_studio.chat.transformation import LMStudioChatConfig
from .llms.lm_studio.embed.transformation import LmStudioEmbeddingConfig
from .llms.nscale.chat.transformation import NscaleConfig
from .llms.perplexity.chat.transformation import PerplexityChatConfig
from .llms.azure.chat.o_series_transformation import AzureOpenAIO1Config
from .llms.watsonx.completion.transformation import IBMWatsonXAIConfig
from .llms.watsonx.chat.transformation import IBMWatsonXChatConfig
from .llms.watsonx.embed.transformation import IBMWatsonXEmbeddingConfig
from .llms.nebius.chat.transformation import NebiusConfig
from .main import *  # type: ignore
from .integrations import *
from .exceptions import (
    AuthenticationError,
    InvalidRequestError,
    BadRequestError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    OpenAIError,
    ContextWindowExceededError,
    ContentPolicyViolationError,
    BudgetExceededError,
    APIError,
    Timeout,
    APIConnectionError,
    UnsupportedParamsError,
    APIResponseValidationError,
    UnprocessableEntityError,
    InternalServerError,
    JSONSchemaValidationError,
    LITELLM_EXCEPTION_TYPES,
    MockException,
)
from .budget_manager import BudgetManager
from .proxy.proxy_cli import run_server
from .router import Router
from .assistants.main import *
from .batches.main import *
from .images.main import *
from .batch_completion.main import *  # type: ignore
from .rerank_api.main import *
from .llms.anthropic.experimental_pass_through.messages.handler import *
from .responses.main import *
from .realtime_api.main import _arealtime
from .fine_tuning.main import *
from .files.main import *
from .scheduler import *
from .cost_calculator import response_cost_calculator, cost_per_token

### ADAPTERS ###
from .types.adapter import AdapterItem
import litellm.anthropic_interface as anthropic

adapters: List[AdapterItem] = []

### Vector Store Registry ###
from .vector_stores.vector_store_registry import VectorStoreRegistry

vector_store_registry: Optional[VectorStoreRegistry] = None

### CUSTOM LLMs ###
from .types.llms.custom_llm import CustomLLMItem
from .types.utils import GenericStreamingChunk

custom_provider_map: List[CustomLLMItem] = []
_custom_providers: List[str] = (
    []
)  # internal helper util, used to track names of custom providers
disable_hf_tokenizer_download: Optional[bool] = (
    None  # disable huggingface tokenizer download. Defaults to openai clk100
)
global_disable_no_log_param: bool = False

### PASSTHROUGH ###
from .passthrough import allm_passthrough_route, llm_passthrough_route

# === NexusCore/openenv\Lib\site-packages\urllib3\connectionpool.py ===
from __future__ import annotations

import errno
import logging
import queue
import sys
import typing
import warnings
import weakref
from socket import timeout as SocketTimeout
from types import TracebackType

from ._base_connection import _TYPE_BODY
from ._collections import HTTPHeaderDict
from ._request_methods import RequestMethods
from .connection import (
    BaseSSLError,
    BrokenPipeError,
    DummyConnection,
    HTTPConnection,
    HTTPException,
    HTTPSConnection,
    ProxyConfig,
    _wrap_proxy_error,
)
from .connection import port_by_scheme as port_by_scheme
from .exceptions import (
    ClosedPoolError,
    EmptyPoolError,
    FullPoolError,
    HostChangedError,
    InsecureRequestWarning,
    LocationValueError,
    MaxRetryError,
    NewConnectionError,
    ProtocolError,
    ProxyError,
    ReadTimeoutError,
    SSLError,
    TimeoutError,
)
from .response import BaseHTTPResponse
from .util.connection import is_connection_dropped
from .util.proxy import connection_requires_http_tunnel
from .util.request import _TYPE_BODY_POSITION, set_file_position
from .util.retry import Retry
from .util.ssl_match_hostname import CertificateError
from .util.timeout import _DEFAULT_TIMEOUT, _TYPE_DEFAULT, Timeout
from .util.url import Url, _encode_target
from .util.url import _normalize_host as normalize_host
from .util.url import parse_url
from .util.util import to_str

if typing.TYPE_CHECKING:
    import ssl

    from typing_extensions import Self

    from ._base_connection import BaseHTTPConnection, BaseHTTPSConnection

log = logging.getLogger(__name__)

_TYPE_TIMEOUT = typing.Union[Timeout, float, _TYPE_DEFAULT, None]


# Pool objects
class ConnectionPool:
    """
    Base class for all connection pools, such as
    :class:`.HTTPConnectionPool` and :class:`.HTTPSConnectionPool`.

    .. note::
       ConnectionPool.urlopen() does not normalize or percent-encode target URIs
       which is useful if your target server doesn't support percent-encoded
       target URIs.
    """

    scheme: str | None = None
    QueueCls = queue.LifoQueue

    def __init__(self, host: str, port: int | None = None) -> None:
        if not host:
            raise LocationValueError("No host specified.")

        self.host = _normalize_host(host, scheme=self.scheme)
        self.port = port

        # This property uses 'normalize_host()' (not '_normalize_host()')
        # to avoid removing square braces around IPv6 addresses.
        # This value is sent to `HTTPConnection.set_tunnel()` if called
        # because square braces are required for HTTP CONNECT tunneling.
        self._tunnel_host = normalize_host(host, scheme=self.scheme).lower()

    def __str__(self) -> str:
        return f"{type(self).__name__}(host={self.host!r}, port={self.port!r})"

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> typing.Literal[False]:
        self.close()
        # Return False to re-raise any potential exceptions
        return False

    def close(self) -> None:
        """
        Close all pooled connections and disable the pool.
        """


# This is taken from http://hg.python.org/cpython/file/7aaba721ebc0/Lib/socket.py#l252
_blocking_errnos = {errno.EAGAIN, errno.EWOULDBLOCK}


class HTTPConnectionPool(ConnectionPool, RequestMethods):
    """
    Thread-safe connection pool for one host.

    :param host:
        Host used for this HTTP Connection (e.g. "localhost"), passed into
        :class:`http.client.HTTPConnection`.

    :param port:
        Port used for this HTTP Connection (None is equivalent to 80), passed
        into :class:`http.client.HTTPConnection`.

    :param timeout:
        Socket timeout in seconds for each individual connection. This can
        be a float or integer, which sets the timeout for the HTTP request,
        or an instance of :class:`urllib3.util.Timeout` which gives you more
        fine-grained control over request timeouts. After the constructor has
        been parsed, this is always a `urllib3.util.Timeout` object.

    :param maxsize:
        Number of connections to save that can be reused. More than 1 is useful
        in multithreaded situations. If ``block`` is set to False, more
        connections will be created but they will not be saved once they've
        been used.

    :param block:
        If set to True, no more than ``maxsize`` connections will be used at
        a time. When no free connections are available, the call will block
        until a connection has been released. This is a useful side effect for
        particular multithreaded situations where one does not want to use more
        than maxsize connections per host to prevent flooding.

    :param headers:
        Headers to include with all requests, unless other headers are given
        explicitly.

    :param retries:
        Retry configuration to use by default with requests in this pool.

    :param _proxy:
        Parsed proxy URL, should not be used directly, instead, see
        :class:`urllib3.ProxyManager`

    :param _proxy_headers:
        A dictionary with proxy headers, should not be used directly,
        instead, see :class:`urllib3.ProxyManager`

    :param \\**conn_kw:
        Additional parameters are used to create fresh :class:`urllib3.connection.HTTPConnection`,
        :class:`urllib3.connection.HTTPSConnection` instances.
    """

    scheme = "http"
    ConnectionCls: type[BaseHTTPConnection] | type[BaseHTTPSConnection] = HTTPConnection

    def __init__(
        self,
        host: str,
        port: int | None = None,
        timeout: _TYPE_TIMEOUT | None = _DEFAULT_TIMEOUT,
        maxsize: int = 1,
        block: bool = False,
        headers: typing.Mapping[str, str] | None = None,
        retries: Retry | bool | int | None = None,
        _proxy: Url | None = None,
        _proxy_headers: typing.Mapping[str, str] | None = None,
        _proxy_config: ProxyConfig | None = None,
        **conn_kw: typing.Any,
    ):
        ConnectionPool.__init__(self, host, port)
        RequestMethods.__init__(self, headers)

        if not isinstance(timeout, Timeout):
            timeout = Timeout.from_float(timeout)

        if retries is None:
            retries = Retry.DEFAULT

        self.timeout = timeout
        self.retries = retries

        self.pool: queue.LifoQueue[typing.Any] | None = self.QueueCls(maxsize)
        self.block = block

        self.proxy = _proxy
        self.proxy_headers = _proxy_headers or {}
        self.proxy_config = _proxy_config

        # Fill the queue up so that doing get() on it will block properly
        for _ in range(maxsize):
            self.pool.put(None)

        # These are mostly for testing and debugging purposes.
        self.num_connections = 0
        self.num_requests = 0
        self.conn_kw = conn_kw

        if self.proxy:
            # Enable Nagle's algorithm for proxies, to avoid packet fragmentation.
            # We cannot know if the user has added default socket options, so we cannot replace the
            # list.
            self.conn_kw.setdefault("socket_options", [])

            self.conn_kw["proxy"] = self.proxy
            self.conn_kw["proxy_config"] = self.proxy_config

        # Do not pass 'self' as callback to 'finalize'.
        # Then the 'finalize' would keep an endless living (leak) to self.
        # By just passing a reference to the pool allows the garbage collector
        # to free self if nobody else has a reference to it.
        pool = self.pool

        # Close all the HTTPConnections in the pool before the
        # HTTPConnectionPool object is garbage collected.
        weakref.finalize(self, _close_pool_connections, pool)

    def _new_conn(self) -> BaseHTTPConnection:
        """
        Return a fresh :class:`HTTPConnection`.
        """
        self.num_connections += 1
        log.debug(
            "Starting new HTTP connection (%d): %s:%s",
            self.num_connections,
            self.host,
            self.port or "80",
        )

        conn = self.ConnectionCls(
            host=self.host,
            port=self.port,
            timeout=self.timeout.connect_timeout,
            **self.conn_kw,
        )
        return conn

    def _get_conn(self, timeout: float | None = None) -> BaseHTTPConnection:
        """
        Get a connection. Will return a pooled connection if one is available.

        If no connections are available and :prop:`.block` is ``False``, then a
        fresh connection is returned.

        :param timeout:
            Seconds to wait before giving up and raising
            :class:`urllib3.exceptions.EmptyPoolError` if the pool is empty and
            :prop:`.block` is ``True``.
        """
        conn = None

        if self.pool is None:
            raise ClosedPoolError(self, "Pool is closed.")

        try:
            conn = self.pool.get(block=self.block, timeout=timeout)

        except AttributeError:  # self.pool is None
            raise ClosedPoolError(self, "Pool is closed.") from None  # Defensive:

        except queue.Empty:
            if self.block:
                raise EmptyPoolError(
                    self,
                    "Pool is empty and a new connection can't be opened due to blocking mode.",
                ) from None
            pass  # Oh well, we'll create a new connection then

        # If this is a persistent connection, check if it got disconnected
        if conn and is_connection_dropped(conn):
            log.debug("Resetting dropped connection: %s", self.host)
            conn.close()

        return conn or self._new_conn()

    def _put_conn(self, conn: BaseHTTPConnection | None) -> None:
        """
        Put a connection back into the pool.

        :param conn:
            Connection object for the current host and port as returned by
            :meth:`._new_conn` or :meth:`._get_conn`.

        If the pool is already full, the connection is closed and discarded
        because we exceeded maxsize. If connections are discarded frequently,
        then maxsize should be increased.

        If the pool is closed, then the connection will be closed and discarded.
        """
        if self.pool is not None:
            try:
                self.pool.put(conn, block=False)
                return  # Everything is dandy, done.
            except AttributeError:
                # self.pool is None.
                pass
            except queue.Full:
                # Connection never got put back into the pool, close it.
                if conn:
                    conn.close()

                if self.block:
                    # This should never happen if you got the conn from self._get_conn
                    raise FullPoolError(
                        self,
                        "Pool reached maximum size and no more connections are allowed.",
                    ) from None

                log.warning(
                    "Connection pool is full, discarding connection: %s. Connection pool size: %s",
                    self.host,
                    self.pool.qsize(),
                )

        # Connection never got put back into the pool, close it.
        if conn:
            conn.close()

    def _validate_conn(self, conn: BaseHTTPConnection) -> None:
        """
        Called right before a request is made, after the socket is created.
        """

    def _prepare_proxy(self, conn: BaseHTTPConnection) -> None:
        # Nothing to do for HTTP connections.
        pass

    def _get_timeout(self, timeout: _TYPE_TIMEOUT) -> Timeout:
        """Helper that always returns a :class:`urllib3.util.Timeout`"""
        if timeout is _DEFAULT_TIMEOUT:
            return self.timeout.clone()

        if isinstance(timeout, Timeout):
            return timeout.clone()
        else:
            # User passed us an int/float. This is for backwards compatibility,
            # can be removed later
            return Timeout.from_float(timeout)

    def _raise_timeout(
        self,
        err: BaseSSLError | OSError | SocketTimeout,
        url: str,
        timeout_value: _TYPE_TIMEOUT | None,
    ) -> None:
        """Is the error actually a timeout? Will raise a ReadTimeout or pass"""

        if isinstance(err, SocketTimeout):
            raise ReadTimeoutError(
                self, url, f"Read timed out. (read timeout={timeout_value})"
            ) from err

        # See the above comment about EAGAIN in Python 3.
        if hasattr(err, "errno") and err.errno in _blocking_errnos:
            raise ReadTimeoutError(
                self, url, f"Read timed out. (read timeout={timeout_value})"
            ) from err

    def _make_request(
        self,
        conn: BaseHTTPConnection,
        method: str,
        url: str,
        body: _TYPE_BODY | None = None,
        headers: typing.Mapping[str, str] | None = None,
        retries: Retry | None = None,
        timeout: _TYPE_TIMEOUT = _DEFAULT_TIMEOUT,
        chunked: bool = False,
        response_conn: BaseHTTPConnection | None = None,
        preload_content: bool = True,
        decode_content: bool = True,
        enforce_content_length: bool = True,
    ) -> BaseHTTPResponse:
        """
        Perform a request on a given urllib connection object taken from our
        pool.

        :param conn:
            a connection from one of our connection pools

        :param method:
            HTTP request method (such as GET, POST, PUT, etc.)

        :param url:
            The URL to perform the request on.

        :param body:
            Data to send in the request body, either :class:`str`, :class:`bytes`,
            an iterable of :class:`str`/:class:`bytes`, or a file-like object.

        :param headers:
            Dictionary of custom headers to send, such as User-Agent,
            If-None-Match, etc. If None, pool headers are used. If provided,
            these headers completely replace any pool-specific headers.

        :param retries:
            Configure the number of retries to allow before raising a
            :class:`~urllib3.exceptions.MaxRetryError` exception.

            Pass ``None`` to retry until you receive a response. Pass a
            :class:`~urllib3.util.retry.Retry` object for fine-grained control
            over different types of retries.
            Pass an integer number to retry connection errors that many times,
            but no other types of errors. Pass zero to never retry.

            If ``False``, then retries are disabled and any exception is raised
            immediately. Also, instead of raising a MaxRetryError on redirects,
            the redirect response will be returned.

        :type retries: :class:`~urllib3.util.retry.Retry`, False, or an int.

        :param timeout:
            If specified, overrides the default timeout for this one
            request. It may be a float (in seconds) or an instance of
            :class:`urllib3.util.Timeout`.

        :param chunked:
            If True, urllib3 will send the body using chunked transfer
            encoding. Otherwise, urllib3 will send the body using the standard
            content-length form. Defaults to False.

        :param response_conn:
            Set this to ``None`` if you will handle releasing the connection or
            set the connection to have the response release it.

        :param preload_content:
          If True, the response's body will be preloaded during construction.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.

        :param enforce_content_length:
            Enforce content length checking. Body returned by server must match
            value of Content-Length header, if present. Otherwise, raise error.
        """
        self.num_requests += 1

        timeout_obj = self._get_timeout(timeout)
        timeout_obj.start_connect()
        conn.timeout = Timeout.resolve_default_timeout(timeout_obj.connect_timeout)

        try:
            # Trigger any extra validation we need to do.
            try:
                self._validate_conn(conn)
            except (SocketTimeout, BaseSSLError) as e:
                self._raise_timeout(err=e, url=url, timeout_value=conn.timeout)
                raise

        # _validate_conn() starts the connection to an HTTPS proxy
        # so we need to wrap errors with 'ProxyError' here too.
        except (
            OSError,
            NewConnectionError,
            TimeoutError,
            BaseSSLError,
            CertificateError,
            SSLError,
        ) as e:
            new_e: Exception = e
            if isinstance(e, (BaseSSLError, CertificateError)):
                new_e = SSLError(e)
            # If the connection didn't successfully connect to it's proxy
            # then there
            if isinstance(
                new_e, (OSError, NewConnectionError, TimeoutError, SSLError)
            ) and (conn and conn.proxy and not conn.has_connected_to_proxy):
                new_e = _wrap_proxy_error(new_e, conn.proxy.scheme)
            raise new_e

        # conn.request() calls http.client.*.request, not the method in
        # urllib3.request. It also calls makefile (recv) on the socket.
        try:
            conn.request(
                method,
                url,
                body=body,
                headers=headers,
                chunked=chunked,
                preload_content=preload_content,
                decode_content=decode_content,
                enforce_content_length=enforce_content_length,
            )

        # We are swallowing BrokenPipeError (errno.EPIPE) since the server is
        # legitimately able to close the connection after sending a valid response.
        # With this behaviour, the received response is still readable.
        except BrokenPipeError:
            pass
        except OSError as e:
            # MacOS/Linux
            # EPROTOTYPE and ECONNRESET are needed on macOS
            # https://erickt.github.io/blog/2014/11/19/adventures-in-debugging-a-potential-osx-kernel-bug/
            # Condition changed later to emit ECONNRESET instead of only EPROTOTYPE.
            if e.errno != errno.EPROTOTYPE and e.errno != errno.ECONNRESET:
                raise

        # Reset the timeout for the recv() on the socket
        read_timeout = timeout_obj.read_timeout

        if not conn.is_closed:
            # In Python 3 socket.py will catch EAGAIN and return None when you
            # try and read into the file pointer created by http.client, which
            # instead raises a BadStatusLine exception. Instead of catching
            # the exception and assuming all BadStatusLine exceptions are read
            # timeouts, check for a zero timeout before making the request.
            if read_timeout == 0:
                raise ReadTimeoutError(
                    self, url, f"Read timed out. (read timeout={read_timeout})"
                )
            conn.timeout = read_timeout

        # Receive the response from the server
        try:
            response = conn.getresponse()
        except (BaseSSLError, OSError) as e:
            self._raise_timeout(err=e, url=url, timeout_value=read_timeout)
            raise

        # Set properties that are used by the pooling layer.
        response.retries = retries
        response._connection = response_conn  # type: ignore[attr-defined]
        response._pool = self  # type: ignore[attr-defined]

        log.debug(
            '%s://%s:%s "%s %s %s" %s %s',
            self.scheme,
            self.host,
            self.port,
            method,
            url,
            response.version_string,
            response.status,
            response.length_remaining,
        )

        return response

    def close(self) -> None:
        """
        Close all pooled connections and disable the pool.
        """
        if self.pool is None:
            return
        # Disable access to the pool
        old_pool, self.pool = self.pool, None

        # Close all the HTTPConnections in the pool.
        _close_pool_connections(old_pool)

    def is_same_host(self, url: str) -> bool:
        """
        Check if the given ``url`` is a member of the same host as this
        connection pool.
        """
        if url.startswith("/"):
            return True

        # TODO: Add optional support for socket.gethostbyname checking.
        scheme, _, host, port, *_ = parse_url(url)
        scheme = scheme or "http"
        if host is not None:
            host = _normalize_host(host, scheme=scheme)

        # Use explicit default port for comparison when none is given
        if self.port and not port:
            port = port_by_scheme.get(scheme)
        elif not self.port and port == port_by_scheme.get(scheme):
            port = None

        return (scheme, host, port) == (self.scheme, self.host, self.port)

    def urlopen(  # type: ignore[override]
        self,
        method: str,
        url: str,
        body: _TYPE_BODY | None = None,
        headers: typing.Mapping[str, str] | None = None,
        retries: Retry | bool | int | None = None,
        redirect: bool = True,
        assert_same_host: bool = True,
        timeout: _TYPE_TIMEOUT = _DEFAULT_TIMEOUT,
        pool_timeout: int | None = None,
        release_conn: bool | None = None,
        chunked: bool = False,
        body_pos: _TYPE_BODY_POSITION | None = None,
        preload_content: bool = True,
        decode_content: bool = True,
        **response_kw: typing.Any,
    ) -> BaseHTTPResponse:
        """
        Get a connection from the pool and perform an HTTP request. This is the
        lowest level call for making a request, so you'll need to specify all
        the raw details.

        .. note::

           More commonly, it's appropriate to use a convenience method
           such as :meth:`request`.

        .. note::

           `release_conn` will only behave as expected if
           `preload_content=False` because we want to make
           `preload_content=False` the default behaviour someday soon without
           breaking backwards compatibility.

        :param method:
            HTTP request method (such as GET, POST, PUT, etc.)

        :param url:
            The URL to perform the request on.

        :param body:
            Data to send in the request body, either :class:`str`, :class:`bytes`,
            an iterable of :class:`str`/:class:`bytes`, or a file-like object.

        :param headers:
            Dictionary of custom headers to send, such as User-Agent,
            If-None-Match, etc. If None, pool headers are used. If provided,
            these headers completely replace any pool-specific headers.

        :param retries:
            Configure the number of retries to allow before raising a
            :class:`~urllib3.exceptions.MaxRetryError` exception.

            If ``None`` (default) will retry 3 times, see ``Retry.DEFAULT``. Pass a
            :class:`~urllib3.util.retry.Retry` object for fine-grained control
            over different types of retries.
            Pass an integer number to retry connection errors that many times,
            but no other types of errors. Pass zero to never retry.

            If ``False``, then retries are disabled and any exception is raised
            immediately. Also, instead of raising a MaxRetryError on redirects,
            the redirect response will be returned.

        :type retries: :class:`~urllib3.util.retry.Retry`, False, or an int.

        :param redirect:
            If True, automatically handle redirects (status codes 301, 302,
            303, 307, 308). Each redirect counts as a retry. Disabling retries
            will disable redirect, too.

        :param assert_same_host:
            If ``True``, will make sure that the host of the pool requests is
            consistent else will raise HostChangedError. When ``False``, you can
            use the pool on an HTTP proxy and request foreign hosts.

        :param timeout:
            If specified, overrides the default timeout for this one
            request. It may be a float (in seconds) or an instance of
            :class:`urllib3.util.Timeout`.

        :param pool_timeout:
            If set and the pool is set to block=True, then this method will
            block for ``pool_timeout`` seconds and raise EmptyPoolError if no
            connection is available within the time period.

        :param bool preload_content:
            If True, the response's body will be preloaded into memory.

        :param bool decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.

        :param release_conn:
            If False, then the urlopen call will not release the connection
            back into the pool once a response is received (but will release if
            you read the entire contents of the response such as when
            `preload_content=True`). This is useful if you're not preloading
            the response's content immediately. You will need to call
            ``r.release_conn()`` on the response ``r`` to return the connection
            back into the pool. If None, it takes the value of ``preload_content``
            which defaults to ``True``.

        :param bool chunked:
            If True, urllib3 will send the body using chunked transfer
            encoding. Otherwise, urllib3 will send the body using the standard
            content-length form. Defaults to False.

        :param int body_pos:
            Position to seek to in file-like body in the event of a retry or
            redirect. Typically this won't need to be set because urllib3 will
            auto-populate the value when needed.
        """
        parsed_url = parse_url(url)
        destination_scheme = parsed_url.scheme

        if headers is None:
            headers = self.headers

        if not isinstance(retries, Retry):
            retries = Retry.from_int(retries, redirect=redirect, default=self.retries)

        if release_conn is None:
            release_conn = preload_content

        # Check host
        if assert_same_host and not self.is_same_host(url):
            raise HostChangedError(self, url, retries)

        # Ensure that the URL we're connecting to is properly encoded
        if url.startswith("/"):
            url = to_str(_encode_target(url))
        else:
            url = to_str(parsed_url.url)

        conn = None

        # Track whether `conn` needs to be released before
        # returning/raising/recursing. Update this variable if necessary, and
        # leave `release_conn` constant throughout the function. That way, if
        # the function recurses, the original value of `release_conn` will be
        # passed down into the recursive call, and its value will be respected.
        #
        # See issue #651 [1] for details.
        #
        # [1] <https://github.com/urllib3/urllib3/issues/651>
        release_this_conn = release_conn

        http_tunnel_required = connection_requires_http_tunnel(
            self.proxy, self.proxy_config, destination_scheme
        )

        # Merge the proxy headers. Only done when not using HTTP CONNECT. We
        # have to copy the headers dict so we can safely change it without those
        # changes being reflected in anyone else's copy.
        if not http_tunnel_required:
            headers = headers.copy()  # type: ignore[attr-defined]
            headers.update(self.proxy_headers)  # type: ignore[union-attr]

        # Must keep the exception bound to a separate variable or else Python 3
        # complains about UnboundLocalError.
        err = None

        # Keep track of whether we cleanly exited the except block. This
        # ensures we do proper cleanup in finally.
        clean_exit = False

        # Rewind body position, if needed. Record current position
        # for future rewinds in the event of a redirect/retry.
        body_pos = set_file_position(body, body_pos)

        try:
            # Request a connection from the queue.
            timeout_obj = self._get_timeout(timeout)
            conn = self._get_conn(timeout=pool_timeout)

            conn.timeout = timeout_obj.connect_timeout  # type: ignore[assignment]

            # Is this a closed/new connection that requires CONNECT tunnelling?
            if self.proxy is not None and http_tunnel_required and conn.is_closed:
                try:
                    self._prepare_proxy(conn)
                except (BaseSSLError, OSError, SocketTimeout) as e:
                    self._raise_timeout(
                        err=e, url=self.proxy.url, timeout_value=conn.timeout
                    )
                    raise

            # If we're going to release the connection in ``finally:``, then
            # the response doesn't need to know about the connection. Otherwise
            # it will also try to release it and we'll have a double-release
            # mess.
            response_conn = conn if not release_conn else None

            # Make the request on the HTTPConnection object
            response = self._make_request(
                conn,
                method,
                url,
                timeout=timeout_obj,
                body=body,
                headers=headers,
                chunked=chunked,
                retries=retries,
                response_conn=response_conn,
                preload_content=preload_content,
                decode_content=decode_content,
                **response_kw,
            )

            # Everything went great!
            clean_exit = True

        except EmptyPoolError:
            # Didn't get a connection from the pool, no need to clean up
            clean_exit = True
            release_this_conn = False
            raise

        except (
            TimeoutError,
            HTTPException,
            OSError,
            ProtocolError,
            BaseSSLError,
            SSLError,
            CertificateError,
            ProxyError,
        ) as e:
            # Discard the connection for these exceptions. It will be
            # replaced during the next _get_conn() call.
            clean_exit = False
            new_e: Exception = e
            if isinstance(e, (BaseSSLError, CertificateError)):
                new_e = SSLError(e)
            if isinstance(
                new_e,
                (
                    OSError,
                    NewConnectionError,
                    TimeoutError,
                    SSLError,
                    HTTPException,
                ),
            ) and (conn and conn.proxy and not conn.has_connected_to_proxy):
                new_e = _wrap_proxy_error(new_e, conn.proxy.scheme)
            elif isinstance(new_e, (OSError, HTTPException)):
                new_e = ProtocolError("Connection aborted.", new_e)

            retries = retries.increment(
                method, url, error=new_e, _pool=self, _stacktrace=sys.exc_info()[2]
            )
            retries.sleep()

            # Keep track of the error for the retry warning.
            err = e

        finally:
            if not clean_exit:
                # We hit some kind of exception, handled or otherwise. We need
                # to throw the connection away unless explicitly told not to.
                # Close the connection, set the variable to None, and make sure
                # we put the None back in the pool to avoid leaking it.
                if conn:
                    conn.close()
                    conn = None
                release_this_conn = True

            if release_this_conn:
                # Put the connection back to be reused. If the connection is
                # expired then it will be None, which will get replaced with a
                # fresh connection during _get_conn.
                self._put_conn(conn)

        if not conn:
            # Try again
            log.warning(
                "Retrying (%r) after connection broken by '%r': %s", retries, err, url
            )
            return self.urlopen(
                method,
                url,
                body,
                headers,
                retries,
                redirect,
                assert_same_host,
                timeout=timeout,
                pool_timeout=pool_timeout,
                release_conn=release_conn,
                chunked=chunked,
                body_pos=body_pos,
                preload_content=preload_content,
                decode_content=decode_content,
                **response_kw,
            )

        # Handle redirect?
        redirect_location = redirect and response.get_redirect_location()
        if redirect_location:
            if response.status == 303:
                # Change the method according to RFC 9110, Section 15.4.4.
                method = "GET"
                # And lose the body not to transfer anything sensitive.
                body = None
                headers = HTTPHeaderDict(headers)._prepare_for_method_change()

            try:
                retries = retries.increment(method, url, response=response, _pool=self)
            except MaxRetryError:
                if retries.raise_on_redirect:
                    response.drain_conn()
                    raise
                return response

            response.drain_conn()
            retries.sleep_for_retry(response)
            log.debug("Redirecting %s -> %s", url, redirect_location)
            return self.urlopen(
                method,
                redirect_location,
                body,
                headers,
                retries=retries,
                redirect=redirect,
                assert_same_host=assert_same_host,
                timeout=timeout,
                pool_timeout=pool_timeout,
                release_conn=release_conn,
                chunked=chunked,
                body_pos=body_pos,
                preload_content=preload_content,
                decode_content=decode_content,
                **response_kw,
            )

        # Check if we should retry the HTTP response.
        has_retry_after = bool(response.headers.get("Retry-After"))
        if retries.is_retry(method, response.status, has_retry_after):
            try:
                retries = retries.increment(method, url, response=response, _pool=self)
            except MaxRetryError:
                if retries.raise_on_status:
                    response.drain_conn()
                    raise
                return response

            response.drain_conn()
            retries.sleep(response)
            log.debug("Retry: %s", url)
            return self.urlopen(
                method,
                url,
                body,
                headers,
                retries=retries,
                redirect=redirect,
                assert_same_host=assert_same_host,
                timeout=timeout,
                pool_timeout=pool_timeout,
                release_conn=release_conn,
                chunked=chunked,
                body_pos=body_pos,
                preload_content=preload_content,
                decode_content=decode_content,
                **response_kw,
            )

        return response


class HTTPSConnectionPool(HTTPConnectionPool):
    """
    Same as :class:`.HTTPConnectionPool`, but HTTPS.

    :class:`.HTTPSConnection` uses one of ``assert_fingerprint``,
    ``assert_hostname`` and ``host`` in this order to verify connections.
    If ``assert_hostname`` is False, no verification is done.

    The ``key_file``, ``cert_file``, ``cert_reqs``, ``ca_certs``,
    ``ca_cert_dir``, ``ssl_version``, ``key_password`` are only used if :mod:`ssl`
    is available and are fed into :meth:`urllib3.util.ssl_wrap_socket` to upgrade
    the connection socket into an SSL socket.
    """

    scheme = "https"
    ConnectionCls: type[BaseHTTPSConnection] = HTTPSConnection

    def __init__(
        self,
        host: str,
        port: int | None = None,
        timeout: _TYPE_TIMEOUT | None = _DEFAULT_TIMEOUT,
        maxsize: int = 1,
        block: bool = False,
        headers: typing.Mapping[str, str] | None = None,
        retries: Retry | bool | int | None = None,
        _proxy: Url | None = None,
        _proxy_headers: typing.Mapping[str, str] | None = None,
        key_file: str | None = None,
        cert_file: str | None = None,
        cert_reqs: int | str | None = None,
        key_password: str | None = None,
        ca_certs: str | None = None,
        ssl_version: int | str | None = None,
        ssl_minimum_version: ssl.TLSVersion | None = None,
        ssl_maximum_version: ssl.TLSVersion | None = None,
        assert_hostname: str | typing.Literal[False] | None = None,
        assert_fingerprint: str | None = None,
        ca_cert_dir: str | None = None,
        **conn_kw: typing.Any,
    ) -> None:
        super().__init__(
            host,
            port,
            timeout,
            maxsize,
            block,
            headers,
            retries,
            _proxy,
            _proxy_headers,
            **conn_kw,
        )

        self.key_file = key_file
        self.cert_file = cert_file
        self.cert_reqs = cert_reqs
        self.key_password = key_password
        self.ca_certs = ca_certs
        self.ca_cert_dir = ca_cert_dir
        self.ssl_version = ssl_version
        self.ssl_minimum_version = ssl_minimum_version
        self.ssl_maximum_version = ssl_maximum_version
        self.assert_hostname = assert_hostname
        self.assert_fingerprint = assert_fingerprint

    def _prepare_proxy(self, conn: HTTPSConnection) -> None:  # type: ignore[override]
        """Establishes a tunnel connection through HTTP CONNECT."""
        if self.proxy and self.proxy.scheme == "https":
            tunnel_scheme = "https"
        else:
            tunnel_scheme = "http"

        conn.set_tunnel(
            scheme=tunnel_scheme,
            host=self._tunnel_host,
            port=self.port,
            headers=self.proxy_headers,
        )
        conn.connect()

    def _new_conn(self) -> BaseHTTPSConnection:
        """
        Return a fresh :class:`urllib3.connection.HTTPConnection`.
        """
        self.num_connections += 1
        log.debug(
            "Starting new HTTPS connection (%d): %s:%s",
            self.num_connections,
            self.host,
            self.port or "443",
        )

        if not self.ConnectionCls or self.ConnectionCls is DummyConnection:  # type: ignore[comparison-overlap]
            raise ImportError(
                "Can't connect to HTTPS URL because the SSL module is not available."
            )

        actual_host: str = self.host
        actual_port = self.port
        if self.proxy is not None and self.proxy.host is not None:
            actual_host = self.proxy.host
            actual_port = self.proxy.port

        return self.ConnectionCls(
            host=actual_host,
            port=actual_port,
            timeout=self.timeout.connect_timeout,
            cert_file=self.cert_file,
            key_file=self.key_file,
            key_password=self.key_password,
            cert_reqs=self.cert_reqs,
            ca_certs=self.ca_certs,
            ca_cert_dir=self.ca_cert_dir,
            assert_hostname=self.assert_hostname,
            assert_fingerprint=self.assert_fingerprint,
            ssl_version=self.ssl_version,
            ssl_minimum_version=self.ssl_minimum_version,
            ssl_maximum_version=self.ssl_maximum_version,
            **self.conn_kw,
        )

    def _validate_conn(self, conn: BaseHTTPConnection) -> None:
        """
        Called right before a request is made, after the socket is created.
        """
        super()._validate_conn(conn)

        # Force connect early to allow us to validate the connection.
        if conn.is_closed:
            conn.connect()

        # TODO revise this, see https://github.com/urllib3/urllib3/issues/2791
        if not conn.is_verified and not conn.proxy_is_verified:
            warnings.warn(
                (
                    f"Unverified HTTPS request is being made to host '{conn.host}'. "
                    "Adding certificate verification is strongly advised. See: "
                    "https://urllib3.readthedocs.io/en/latest/advanced-usage.html"
                    "#tls-warnings"
                ),
                InsecureRequestWarning,
            )


def connection_from_url(url: str, **kw: typing.Any) -> HTTPConnectionPool:
    """
    Given a url, return an :class:`.ConnectionPool` instance of its host.

    This is a shortcut for not having to parse out the scheme, host, and port
    of the url before creating an :class:`.ConnectionPool` instance.

    :param url:
        Absolute URL string that must include the scheme. Port is optional.

    :param \\**kw:
        Passes additional parameters to the constructor of the appropriate
        :class:`.ConnectionPool`. Useful for specifying things like
        timeout, maxsize, headers, etc.

    Example::

        >>> conn = connection_from_url('http://google.com/')
        >>> r = conn.request('GET', '/')
    """
    scheme, _, host, port, *_ = parse_url(url)
    scheme = scheme or "http"
    port = port or port_by_scheme.get(scheme, 80)
    if scheme == "https":
        return HTTPSConnectionPool(host, port=port, **kw)  # type: ignore[arg-type]
    else:
        return HTTPConnectionPool(host, port=port, **kw)  # type: ignore[arg-type]


@typing.overload
def _normalize_host(host: None, scheme: str | None) -> None: ...


@typing.overload
def _normalize_host(host: str, scheme: str | None) -> str: ...


def _normalize_host(host: str | None, scheme: str | None) -> str | None:
    """
    Normalize hosts for comparisons and use with sockets.
    """

    host = normalize_host(host, scheme)

    # httplib doesn't like it when we include brackets in IPv6 addresses
    # Specifically, if we include brackets but also pass the port then
    # httplib crazily doubles up the square brackets on the Host header.
    # Instead, we need to make sure we never pass ``None`` as the port.
    # However, for backward compatibility reasons we can't actually
    # *assert* that.  See http://bugs.python.org/issue28539
    if host and host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host


def _url_from_pool(
    pool: HTTPConnectionPool | HTTPSConnectionPool, path: str | None = None
) -> str:
    """Returns the URL from a given connection pool. This is mainly used for testing and logging."""
    return Url(scheme=pool.scheme, host=pool.host, port=pool.port, path=path).url


def _close_pool_connections(pool: queue.LifoQueue[typing.Any]) -> None:
    """Drains a queue of connections and closes each one."""
    try:
        while True:
            conn = pool.get(block=False)
            if conn:
                conn.close()
    except queue.Empty:
        pass  # Done.

# === NexusCore/openenv\Lib\site-packages\grpc\aio\_interceptor.py ===
# Copyright 2019 gRPC authors.
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
"""Interceptors implementation of gRPC Asyncio Python."""
from abc import ABCMeta
from abc import abstractmethod
import asyncio
import collections
import functools
from typing import (
    AsyncIterable,
    Awaitable,
    Callable,
    Iterator,
    List,
    Optional,
    Sequence,
    Union,
)

import grpc
from grpc._cython import cygrpc

from . import _base_call
from ._call import AioRpcError
from ._call import StreamStreamCall
from ._call import StreamUnaryCall
from ._call import UnaryStreamCall
from ._call import UnaryUnaryCall
from ._call import _API_STYLE_ERROR
from ._call import _RPC_ALREADY_FINISHED_DETAILS
from ._call import _RPC_HALF_CLOSED_DETAILS
from ._metadata import Metadata
from ._typing import DeserializingFunction
from ._typing import DoneCallbackType
from ._typing import EOFType
from ._typing import RequestIterableType
from ._typing import RequestType
from ._typing import ResponseIterableType
from ._typing import ResponseType
from ._typing import SerializingFunction
from ._utils import _timeout_to_deadline

_LOCAL_CANCELLATION_DETAILS = "Locally cancelled by application!"


class ServerInterceptor(metaclass=ABCMeta):
    """Affords intercepting incoming RPCs on the service-side.

    This is an EXPERIMENTAL API.
    """

    @abstractmethod
    async def intercept_service(
        self,
        continuation: Callable[
            [grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler]
        ],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """Intercepts incoming RPCs before handing them over to a handler.

        State can be passed from an interceptor to downstream interceptors
        via contextvars. The first interceptor is called from an empty
        contextvars.Context, and the same Context is used for downstream
        interceptors and for the final handler call. Note that there are no
        guarantees that interceptors and handlers will be called from the
        same thread.

        Args:
            continuation: A function that takes a HandlerCallDetails and
                proceeds to invoke the next interceptor in the chain, if any,
                or the RPC handler lookup logic, with the call details passed
                as an argument, and returns an RpcMethodHandler instance if
                the RPC is considered serviced, or None otherwise.
            handler_call_details: A HandlerCallDetails describing the RPC.

        Returns:
            An RpcMethodHandler with which the RPC may be serviced if the
            interceptor chooses to service this RPC, or None otherwise.
        """


class ClientCallDetails(
    collections.namedtuple(
        "ClientCallDetails",
        ("method", "timeout", "metadata", "credentials", "wait_for_ready"),
    ),
    grpc.ClientCallDetails,
):
    """Describes an RPC to be invoked.

    This is an EXPERIMENTAL API.

    Args:
        method: The method name of the RPC.
        timeout: An optional duration of time in seconds to allow for the RPC.
        metadata: Optional metadata to be transmitted to the service-side of
          the RPC.
        credentials: An optional CallCredentials for the RPC.
        wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
    """

    method: str
    timeout: Optional[float]
    metadata: Optional[Metadata]
    credentials: Optional[grpc.CallCredentials]
    wait_for_ready: Optional[bool]


class ClientInterceptor(metaclass=ABCMeta):
    """Base class used for all Aio Client Interceptor classes"""


class UnaryUnaryClientInterceptor(ClientInterceptor, metaclass=ABCMeta):
    """Affords intercepting unary-unary invocations."""

    @abstractmethod
    async def intercept_unary_unary(
        self,
        continuation: Callable[
            [ClientCallDetails, RequestType], UnaryUnaryCall
        ],
        client_call_details: ClientCallDetails,
        request: RequestType,
    ) -> Union[UnaryUnaryCall, ResponseType]:
        """Intercepts a unary-unary invocation asynchronously.

        Args:
          continuation: A coroutine that proceeds with the invocation by
            executing the next interceptor in the chain or invoking the
            actual RPC on the underlying Channel. It is the interceptor's
            responsibility to call it if it decides to move the RPC forward.
            The interceptor can use
            `call = await continuation(client_call_details, request)`
            to continue with the RPC. `continuation` returns the call to the
            RPC.
          client_call_details: A ClientCallDetails object describing the
            outgoing RPC.
          request: The request value for the RPC.

        Returns:
          An object with the RPC response.

        Raises:
          AioRpcError: Indicating that the RPC terminated with non-OK status.
          asyncio.CancelledError: Indicating that the RPC was canceled.
        """


class UnaryStreamClientInterceptor(ClientInterceptor, metaclass=ABCMeta):
    """Affords intercepting unary-stream invocations."""

    @abstractmethod
    async def intercept_unary_stream(
        self,
        continuation: Callable[
            [ClientCallDetails, RequestType], UnaryStreamCall
        ],
        client_call_details: ClientCallDetails,
        request: RequestType,
    ) -> Union[ResponseIterableType, UnaryStreamCall]:
        """Intercepts a unary-stream invocation asynchronously.

        The function could return the call object or an asynchronous
        iterator, in case of being an asyncrhonous iterator this will
        become the source of the reads done by the caller.

        Args:
          continuation: A coroutine that proceeds with the invocation by
            executing the next interceptor in the chain or invoking the
            actual RPC on the underlying Channel. It is the interceptor's
            responsibility to call it if it decides to move the RPC forward.
            The interceptor can use
            `call = await continuation(client_call_details, request)`
            to continue with the RPC. `continuation` returns the call to the
            RPC.
          client_call_details: A ClientCallDetails object describing the
            outgoing RPC.
          request: The request value for the RPC.

        Returns:
          The RPC Call or an asynchronous iterator.

        Raises:
          AioRpcError: Indicating that the RPC terminated with non-OK status.
          asyncio.CancelledError: Indicating that the RPC was canceled.
        """


class StreamUnaryClientInterceptor(ClientInterceptor, metaclass=ABCMeta):
    """Affords intercepting stream-unary invocations."""

    @abstractmethod
    async def intercept_stream_unary(
        self,
        continuation: Callable[
            [ClientCallDetails, RequestType], StreamUnaryCall
        ],
        client_call_details: ClientCallDetails,
        request_iterator: RequestIterableType,
    ) -> StreamUnaryCall:
        """Intercepts a stream-unary invocation asynchronously.

        Within the interceptor the usage of the call methods like `write` or
        even awaiting the call should be done carefully, since the caller
        could be expecting an untouched call, for example for start writing
        messages to it.

        Args:
          continuation: A coroutine that proceeds with the invocation by
            executing the next interceptor in the chain or invoking the
            actual RPC on the underlying Channel. It is the interceptor's
            responsibility to call it if it decides to move the RPC forward.
            The interceptor can use
            `call = await continuation(client_call_details, request_iterator)`
            to continue with the RPC. `continuation` returns the call to the
            RPC.
          client_call_details: A ClientCallDetails object describing the
            outgoing RPC.
          request_iterator: The request iterator that will produce requests
            for the RPC.

        Returns:
          The RPC Call.

        Raises:
          AioRpcError: Indicating that the RPC terminated with non-OK status.
          asyncio.CancelledError: Indicating that the RPC was canceled.
        """


class StreamStreamClientInterceptor(ClientInterceptor, metaclass=ABCMeta):
    """Affords intercepting stream-stream invocations."""

    @abstractmethod
    async def intercept_stream_stream(
        self,
        continuation: Callable[
            [ClientCallDetails, RequestType], StreamStreamCall
        ],
        client_call_details: ClientCallDetails,
        request_iterator: RequestIterableType,
    ) -> Union[ResponseIterableType, StreamStreamCall]:
        """Intercepts a stream-stream invocation asynchronously.

        Within the interceptor the usage of the call methods like `write` or
        even awaiting the call should be done carefully, since the caller
        could be expecting an untouched call, for example for start writing
        messages to it.

        The function could return the call object or an asynchronous
        iterator, in case of being an asyncrhonous iterator this will
        become the source of the reads done by the caller.

        Args:
          continuation: A coroutine that proceeds with the invocation by
            executing the next interceptor in the chain or invoking the
            actual RPC on the underlying Channel. It is the interceptor's
            responsibility to call it if it decides to move the RPC forward.
            The interceptor can use
            `call = await continuation(client_call_details, request_iterator)`
            to continue with the RPC. `continuation` returns the call to the
            RPC.
          client_call_details: A ClientCallDetails object describing the
            outgoing RPC.
          request_iterator: The request iterator that will produce requests
            for the RPC.

        Returns:
          The RPC Call or an asynchronous iterator.

        Raises:
          AioRpcError: Indicating that the RPC terminated with non-OK status.
          asyncio.CancelledError: Indicating that the RPC was canceled.
        """


class InterceptedCall:
    """Base implementation for all intercepted call arities.

    Interceptors might have some work to do before the RPC invocation with
    the capacity of changing the invocation parameters, and some work to do
    after the RPC invocation with the capacity for accessing to the wrapped
    `UnaryUnaryCall`.

    It handles also early and later cancellations, when the RPC has not even
    started and the execution is still held by the interceptors or when the
    RPC has finished but again the execution is still held by the interceptors.

    Once the RPC is finally executed, all methods are finally done against the
    intercepted call, being at the same time the same call returned to the
    interceptors.

    As a base class for all of the interceptors implements the logic around
    final status, metadata and cancellation.
    """

    _interceptors_task: asyncio.Task
    _pending_add_done_callbacks: Sequence[DoneCallbackType]

    def __init__(self, interceptors_task: asyncio.Task) -> None:
        self._interceptors_task = interceptors_task
        self._pending_add_done_callbacks = []
        self._interceptors_task.add_done_callback(
            self._fire_or_add_pending_done_callbacks
        )

    def __del__(self):
        self.cancel()

    def _fire_or_add_pending_done_callbacks(
        self, interceptors_task: asyncio.Task
    ) -> None:
        if not self._pending_add_done_callbacks:
            return

        call_completed = False

        try:
            call = interceptors_task.result()
            if call.done():
                call_completed = True
        except (AioRpcError, asyncio.CancelledError):
            call_completed = True

        if call_completed:
            for callback in self._pending_add_done_callbacks:
                callback(self)
        else:
            for callback in self._pending_add_done_callbacks:
                callback = functools.partial(
                    self._wrap_add_done_callback, callback
                )
                call.add_done_callback(callback)

        self._pending_add_done_callbacks = []

    def _wrap_add_done_callback(
        self, callback: DoneCallbackType, unused_call: _base_call.Call
    ) -> None:
        callback(self)

    def cancel(self) -> bool:
        if not self._interceptors_task.done():
            # There is no yet the intercepted call available,
            # Trying to cancel it by using the generic Asyncio
            # cancellation method.
            return self._interceptors_task.cancel()

        try:
            call = self._interceptors_task.result()
        except AioRpcError:
            return False
        except asyncio.CancelledError:
            return False

        return call.cancel()

    def cancelled(self) -> bool:
        if not self._interceptors_task.done():
            return False

        try:
            call = self._interceptors_task.result()
        except AioRpcError as err:
            return err.code() == grpc.StatusCode.CANCELLED
        except asyncio.CancelledError:
            return True

        return call.cancelled()

    def done(self) -> bool:
        if not self._interceptors_task.done():
            return False

        try:
            call = self._interceptors_task.result()
        except (AioRpcError, asyncio.CancelledError):
            return True

        return call.done()

    def add_done_callback(self, callback: DoneCallbackType) -> None:
        if not self._interceptors_task.done():
            self._pending_add_done_callbacks.append(callback)
            return

        try:
            call = self._interceptors_task.result()
        except (AioRpcError, asyncio.CancelledError):
            callback(self)
            return

        if call.done():
            callback(self)
        else:
            callback = functools.partial(self._wrap_add_done_callback, callback)
            call.add_done_callback(callback)

    def time_remaining(self) -> Optional[float]:
        raise NotImplementedError()

    async def initial_metadata(self) -> Optional[Metadata]:
        try:
            call = await self._interceptors_task
        except AioRpcError as err:
            return err.initial_metadata()
        except asyncio.CancelledError:
            return None

        return await call.initial_metadata()

    async def trailing_metadata(self) -> Optional[Metadata]:
        try:
            call = await self._interceptors_task
        except AioRpcError as err:
            return err.trailing_metadata()
        except asyncio.CancelledError:
            return None

        return await call.trailing_metadata()

    async def code(self) -> grpc.StatusCode:
        try:
            call = await self._interceptors_task
        except AioRpcError as err:
            return err.code()
        except asyncio.CancelledError:
            return grpc.StatusCode.CANCELLED

        return await call.code()

    async def details(self) -> str:
        try:
            call = await self._interceptors_task
        except AioRpcError as err:
            return err.details()
        except asyncio.CancelledError:
            return _LOCAL_CANCELLATION_DETAILS

        return await call.details()

    async def debug_error_string(self) -> Optional[str]:
        try:
            call = await self._interceptors_task
        except AioRpcError as err:
            return err.debug_error_string()
        except asyncio.CancelledError:
            return ""

        return await call.debug_error_string()

    async def wait_for_connection(self) -> None:
        call = await self._interceptors_task
        return await call.wait_for_connection()


class _InterceptedUnaryResponseMixin:
    def __await__(self):
        call = yield from self._interceptors_task.__await__()
        response = yield from call.__await__()
        return response


class _InterceptedStreamResponseMixin:
    _response_aiter: Optional[AsyncIterable[ResponseType]]

    def _init_stream_response_mixin(self) -> None:
        # Is initialized later, otherwise if the iterator is not finally
        # consumed a logging warning is emitted by Asyncio.
        self._response_aiter = None

    async def _wait_for_interceptor_task_response_iterator(
        self,
    ) -> ResponseType:
        call = await self._interceptors_task
        async for response in call:
            yield response

    def __aiter__(self) -> AsyncIterable[ResponseType]:
        if self._response_aiter is None:
            self._response_aiter = (
                self._wait_for_interceptor_task_response_iterator()
            )
        return self._response_aiter

    async def read(self) -> Union[EOFType, ResponseType]:
        if self._response_aiter is None:
            self._response_aiter = (
                self._wait_for_interceptor_task_response_iterator()
            )
        try:
            return await self._response_aiter.asend(None)
        except StopAsyncIteration:
            return cygrpc.EOF


class _InterceptedStreamRequestMixin:
    _write_to_iterator_async_gen: Optional[AsyncIterable[RequestType]]
    _write_to_iterator_queue: Optional[asyncio.Queue]
    _status_code_task: Optional[asyncio.Task]

    _FINISH_ITERATOR_SENTINEL = object()

    def _init_stream_request_mixin(
        self, request_iterator: Optional[RequestIterableType]
    ) -> RequestIterableType:
        if request_iterator is None:
            # We provide our own request iterator which is a proxy
            # of the futures writes that will be done by the caller.
            self._write_to_iterator_queue = asyncio.Queue(maxsize=1)
            self._write_to_iterator_async_gen = (
                self._proxy_writes_as_request_iterator()
            )
            self._status_code_task = None
            request_iterator = self._write_to_iterator_async_gen
        else:
            self._write_to_iterator_queue = None

        return request_iterator

    async def _proxy_writes_as_request_iterator(self):
        await self._interceptors_task

        while True:
            value = await self._write_to_iterator_queue.get()
            if (
                value
                is _InterceptedStreamRequestMixin._FINISH_ITERATOR_SENTINEL
            ):
                break
            yield value

    async def _write_to_iterator_queue_interruptible(
        self, request: RequestType, call: InterceptedCall
    ):
        # Write the specified 'request' to the request iterator queue using the
        # specified 'call' to allow for interruption of the write in the case
        # of abrupt termination of the call.
        if self._status_code_task is None:
            self._status_code_task = self._loop.create_task(call.code())

        await asyncio.wait(
            (
                self._loop.create_task(
                    self._write_to_iterator_queue.put(request)
                ),
                self._status_code_task,
            ),
            return_when=asyncio.FIRST_COMPLETED,
        )

    async def write(self, request: RequestType) -> None:
        # If no queue was created it means that requests
        # should be expected through an iterators provided
        # by the caller.
        if self._write_to_iterator_queue is None:
            raise cygrpc.UsageError(_API_STYLE_ERROR)

        try:
            call = await self._interceptors_task
        except (asyncio.CancelledError, AioRpcError):
            raise asyncio.InvalidStateError(_RPC_ALREADY_FINISHED_DETAILS)

        if call.done():
            raise asyncio.InvalidStateError(_RPC_ALREADY_FINISHED_DETAILS)
        elif call._done_writing_flag:
            raise asyncio.InvalidStateError(_RPC_HALF_CLOSED_DETAILS)

        await self._write_to_iterator_queue_interruptible(request, call)

        if call.done():
            raise asyncio.InvalidStateError(_RPC_ALREADY_FINISHED_DETAILS)

    async def done_writing(self) -> None:
        """Signal peer that client is done writing.

        This method is idempotent.
        """
        # If no queue was created it means that requests
        # should be expected through an iterators provided
        # by the caller.
        if self._write_to_iterator_queue is None:
            raise cygrpc.UsageError(_API_STYLE_ERROR)

        try:
            call = await self._interceptors_task
        except asyncio.CancelledError:
            raise asyncio.InvalidStateError(_RPC_ALREADY_FINISHED_DETAILS)

        await self._write_to_iterator_queue_interruptible(
            _InterceptedStreamRequestMixin._FINISH_ITERATOR_SENTINEL, call
        )


class InterceptedUnaryUnaryCall(
    _InterceptedUnaryResponseMixin, InterceptedCall, _base_call.UnaryUnaryCall
):
    """Used for running a `UnaryUnaryCall` wrapped by interceptors.

    For the `__await__` method is it is proxied to the intercepted call only when
    the interceptor task is finished.
    """

    _loop: asyncio.AbstractEventLoop
    _channel: cygrpc.AioChannel

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        interceptors: Sequence[UnaryUnaryClientInterceptor],
        request: RequestType,
        timeout: Optional[float],
        metadata: Metadata,
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        channel: cygrpc.AioChannel,
        method: bytes,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._loop = loop
        self._channel = channel
        interceptors_task = loop.create_task(
            self._invoke(
                interceptors,
                method,
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                request,
                request_serializer,
                response_deserializer,
            )
        )
        super().__init__(interceptors_task)

    # pylint: disable=too-many-arguments
    async def _invoke(
        self,
        interceptors: Sequence[UnaryUnaryClientInterceptor],
        method: bytes,
        timeout: Optional[float],
        metadata: Optional[Metadata],
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        request: RequestType,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
    ) -> UnaryUnaryCall:
        """Run the RPC call wrapped in interceptors"""

        async def _run_interceptor(
            interceptors: List[UnaryUnaryClientInterceptor],
            client_call_details: ClientCallDetails,
            request: RequestType,
        ) -> _base_call.UnaryUnaryCall:
            if interceptors:
                continuation = functools.partial(
                    _run_interceptor, interceptors[1:]
                )
                call_or_response = await interceptors[0].intercept_unary_unary(
                    continuation, client_call_details, request
                )

                if isinstance(call_or_response, _base_call.UnaryUnaryCall):
                    return call_or_response
                else:
                    return UnaryUnaryCallResponse(call_or_response)

            else:
                return UnaryUnaryCall(
                    request,
                    _timeout_to_deadline(client_call_details.timeout),
                    client_call_details.metadata,
                    client_call_details.credentials,
                    client_call_details.wait_for_ready,
                    self._channel,
                    client_call_details.method,
                    request_serializer,
                    response_deserializer,
                    self._loop,
                )

        client_call_details = ClientCallDetails(
            method, timeout, metadata, credentials, wait_for_ready
        )
        return await _run_interceptor(
            list(interceptors), client_call_details, request
        )

    def time_remaining(self) -> Optional[float]:
        raise NotImplementedError()


class InterceptedUnaryStreamCall(
    _InterceptedStreamResponseMixin, InterceptedCall, _base_call.UnaryStreamCall
):
    """Used for running a `UnaryStreamCall` wrapped by interceptors."""

    _loop: asyncio.AbstractEventLoop
    _channel: cygrpc.AioChannel
    _last_returned_call_from_interceptors = Optional[_base_call.UnaryStreamCall]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        interceptors: Sequence[UnaryStreamClientInterceptor],
        request: RequestType,
        timeout: Optional[float],
        metadata: Metadata,
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        channel: cygrpc.AioChannel,
        method: bytes,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._loop = loop
        self._channel = channel
        self._init_stream_response_mixin()
        self._last_returned_call_from_interceptors = None
        interceptors_task = loop.create_task(
            self._invoke(
                interceptors,
                method,
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                request,
                request_serializer,
                response_deserializer,
            )
        )
        super().__init__(interceptors_task)

    # pylint: disable=too-many-arguments
    async def _invoke(
        self,
        interceptors: Sequence[UnaryStreamClientInterceptor],
        method: bytes,
        timeout: Optional[float],
        metadata: Optional[Metadata],
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        request: RequestType,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
    ) -> UnaryStreamCall:
        """Run the RPC call wrapped in interceptors"""

        async def _run_interceptor(
            interceptors: List[UnaryStreamClientInterceptor],
            client_call_details: ClientCallDetails,
            request: RequestType,
        ) -> _base_call.UnaryStreamCall:
            if interceptors:
                continuation = functools.partial(
                    _run_interceptor, interceptors[1:]
                )

                call_or_response_iterator = await interceptors[
                    0
                ].intercept_unary_stream(
                    continuation, client_call_details, request
                )

                if isinstance(
                    call_or_response_iterator, _base_call.UnaryStreamCall
                ):
                    self._last_returned_call_from_interceptors = (
                        call_or_response_iterator
                    )
                else:
                    self._last_returned_call_from_interceptors = (
                        UnaryStreamCallResponseIterator(
                            self._last_returned_call_from_interceptors,
                            call_or_response_iterator,
                        )
                    )
                return self._last_returned_call_from_interceptors
            else:
                self._last_returned_call_from_interceptors = UnaryStreamCall(
                    request,
                    _timeout_to_deadline(client_call_details.timeout),
                    client_call_details.metadata,
                    client_call_details.credentials,
                    client_call_details.wait_for_ready,
                    self._channel,
                    client_call_details.method,
                    request_serializer,
                    response_deserializer,
                    self._loop,
                )

                return self._last_returned_call_from_interceptors

        client_call_details = ClientCallDetails(
            method, timeout, metadata, credentials, wait_for_ready
        )
        return await _run_interceptor(
            list(interceptors), client_call_details, request
        )

    def time_remaining(self) -> Optional[float]:
        raise NotImplementedError()


class InterceptedStreamUnaryCall(
    _InterceptedUnaryResponseMixin,
    _InterceptedStreamRequestMixin,
    InterceptedCall,
    _base_call.StreamUnaryCall,
):
    """Used for running a `StreamUnaryCall` wrapped by interceptors.

    For the `__await__` method is it is proxied to the intercepted call only when
    the interceptor task is finished.
    """

    _loop: asyncio.AbstractEventLoop
    _channel: cygrpc.AioChannel

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        interceptors: Sequence[StreamUnaryClientInterceptor],
        request_iterator: Optional[RequestIterableType],
        timeout: Optional[float],
        metadata: Metadata,
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        channel: cygrpc.AioChannel,
        method: bytes,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._loop = loop
        self._channel = channel
        request_iterator = self._init_stream_request_mixin(request_iterator)
        interceptors_task = loop.create_task(
            self._invoke(
                interceptors,
                method,
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                request_iterator,
                request_serializer,
                response_deserializer,
            )
        )
        super().__init__(interceptors_task)

    # pylint: disable=too-many-arguments
    async def _invoke(
        self,
        interceptors: Sequence[StreamUnaryClientInterceptor],
        method: bytes,
        timeout: Optional[float],
        metadata: Optional[Metadata],
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        request_iterator: RequestIterableType,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
    ) -> StreamUnaryCall:
        """Run the RPC call wrapped in interceptors"""

        async def _run_interceptor(
            interceptors: Iterator[StreamUnaryClientInterceptor],
            client_call_details: ClientCallDetails,
            request_iterator: RequestIterableType,
        ) -> _base_call.StreamUnaryCall:
            if interceptors:
                continuation = functools.partial(
                    _run_interceptor, interceptors[1:]
                )

                return await interceptors[0].intercept_stream_unary(
                    continuation, client_call_details, request_iterator
                )
            else:
                return StreamUnaryCall(
                    request_iterator,
                    _timeout_to_deadline(client_call_details.timeout),
                    client_call_details.metadata,
                    client_call_details.credentials,
                    client_call_details.wait_for_ready,
                    self._channel,
                    client_call_details.method,
                    request_serializer,
                    response_deserializer,
                    self._loop,
                )

        client_call_details = ClientCallDetails(
            method, timeout, metadata, credentials, wait_for_ready
        )
        return await _run_interceptor(
            list(interceptors), client_call_details, request_iterator
        )

    def time_remaining(self) -> Optional[float]:
        raise NotImplementedError()


class InterceptedStreamStreamCall(
    _InterceptedStreamResponseMixin,
    _InterceptedStreamRequestMixin,
    InterceptedCall,
    _base_call.StreamStreamCall,
):
    """Used for running a `StreamStreamCall` wrapped by interceptors."""

    _loop: asyncio.AbstractEventLoop
    _channel: cygrpc.AioChannel
    _last_returned_call_from_interceptors = Optional[
        _base_call.StreamStreamCall
    ]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        interceptors: Sequence[StreamStreamClientInterceptor],
        request_iterator: Optional[RequestIterableType],
        timeout: Optional[float],
        metadata: Metadata,
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        channel: cygrpc.AioChannel,
        method: bytes,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._loop = loop
        self._channel = channel
        self._init_stream_response_mixin()
        request_iterator = self._init_stream_request_mixin(request_iterator)
        self._last_returned_call_from_interceptors = None
        interceptors_task = loop.create_task(
            self._invoke(
                interceptors,
                method,
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                request_iterator,
                request_serializer,
                response_deserializer,
            )
        )
        super().__init__(interceptors_task)

    # pylint: disable=too-many-arguments
    async def _invoke(
        self,
        interceptors: Sequence[StreamStreamClientInterceptor],
        method: bytes,
        timeout: Optional[float],
        metadata: Optional[Metadata],
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        request_iterator: RequestIterableType,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
    ) -> StreamStreamCall:
        """Run the RPC call wrapped in interceptors"""

        async def _run_interceptor(
            interceptors: List[StreamStreamClientInterceptor],
            client_call_details: ClientCallDetails,
            request_iterator: RequestIterableType,
        ) -> _base_call.StreamStreamCall:
            if interceptors:
                continuation = functools.partial(
                    _run_interceptor, interceptors[1:]
                )

                call_or_response_iterator = await interceptors[
                    0
                ].intercept_stream_stream(
                    continuation, client_call_details, request_iterator
                )

                if isinstance(
                    call_or_response_iterator, _base_call.StreamStreamCall
                ):
                    self._last_returned_call_from_interceptors = (
                        call_or_response_iterator
                    )
                else:
                    self._last_returned_call_from_interceptors = (
                        StreamStreamCallResponseIterator(
                            self._last_returned_call_from_interceptors,
                            call_or_response_iterator,
                        )
                    )
                return self._last_returned_call_from_interceptors
            else:
                self._last_returned_call_from_interceptors = StreamStreamCall(
                    request_iterator,
                    _timeout_to_deadline(client_call_details.timeout),
                    client_call_details.metadata,
                    client_call_details.credentials,
                    client_call_details.wait_for_ready,
                    self._channel,
                    client_call_details.method,
                    request_serializer,
                    response_deserializer,
                    self._loop,
                )
                return self._last_returned_call_from_interceptors

        client_call_details = ClientCallDetails(
            method, timeout, metadata, credentials, wait_for_ready
        )
        return await _run_interceptor(
            list(interceptors), client_call_details, request_iterator
        )

    def time_remaining(self) -> Optional[float]:
        raise NotImplementedError()


class UnaryUnaryCallResponse(_base_call.UnaryUnaryCall):
    """Final UnaryUnaryCall class finished with a response."""

    _response: ResponseType

    def __init__(self, response: ResponseType) -> None:
        self._response = response

    def cancel(self) -> bool:
        return False

    def cancelled(self) -> bool:
        return False

    def done(self) -> bool:
        return True

    def add_done_callback(self, unused_callback) -> None:
        raise NotImplementedError()

    def time_remaining(self) -> Optional[float]:
        raise NotImplementedError()

    async def initial_metadata(self) -> Optional[Metadata]:
        return None

    async def trailing_metadata(self) -> Optional[Metadata]:
        return None

    async def code(self) -> grpc.StatusCode:
        return grpc.StatusCode.OK

    async def details(self) -> str:
        return ""

    async def debug_error_string(self) -> Optional[str]:
        return None

    def __await__(self):
        if False:  # pylint: disable=using-constant-test
            # This code path is never used, but a yield statement is needed
            # for telling the interpreter that __await__ is a generator.
            yield None
        return self._response

    async def wait_for_connection(self) -> None:
        pass


class _StreamCallResponseIterator:
    _call: Union[_base_call.UnaryStreamCall, _base_call.StreamStreamCall]
    _response_iterator: AsyncIterable[ResponseType]

    def __init__(
        self,
        call: Union[_base_call.UnaryStreamCall, _base_call.StreamStreamCall],
        response_iterator: AsyncIterable[ResponseType],
    ) -> None:
        self._response_iterator = response_iterator
        self._call = call

    def cancel(self) -> bool:
        return self._call.cancel()

    def cancelled(self) -> bool:
        return self._call.cancelled()

    def done(self) -> bool:
        return self._call.done()

    def add_done_callback(self, callback) -> None:
        self._call.add_done_callback(callback)

    def time_remaining(self) -> Optional[float]:
        return self._call.time_remaining()

    async def initial_metadata(self) -> Optional[Metadata]:
        return await self._call.initial_metadata()

    async def trailing_metadata(self) -> Optional[Metadata]:
        return await self._call.trailing_metadata()

    async def code(self) -> grpc.StatusCode:
        return await self._call.code()

    async def details(self) -> str:
        return await self._call.details()

    async def debug_error_string(self) -> Optional[str]:
        return await self._call.debug_error_string()

    def __aiter__(self):
        return self._response_iterator.__aiter__()

    async def wait_for_connection(self) -> None:
        return await self._call.wait_for_connection()


class UnaryStreamCallResponseIterator(
    _StreamCallResponseIterator, _base_call.UnaryStreamCall
):
    """UnaryStreamCall class which uses an alternative response iterator."""

    async def read(self) -> Union[EOFType, ResponseType]:
        # Behind the scenes everything goes through the
        # async iterator. So this path should not be reached.
        raise NotImplementedError()


class StreamStreamCallResponseIterator(
    _StreamCallResponseIterator, _base_call.StreamStreamCall
):
    """StreamStreamCall class which uses an alternative response iterator."""

    async def read(self) -> Union[EOFType, ResponseType]:
        # Behind the scenes everything goes through the
        # async iterator. So this path should not be reached.
        raise NotImplementedError()

    async def write(self, request: RequestType) -> None:
        # Behind the scenes everything goes through the
        # async iterator provided by the InterceptedStreamStreamCall.
        # So this path should not be reached.
        raise NotImplementedError()

    async def done_writing(self) -> None:
        # Behind the scenes everything goes through the
        # async iterator provided by the InterceptedStreamStreamCall.
        # So this path should not be reached.
        raise NotImplementedError()

    @property
    def _done_writing_flag(self) -> bool:
        return self._call._done_writing_flag

# === NexusCore/openenv\Lib\site-packages\nltk\draw\table.py ===
# Natural Language Toolkit: Table widget
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Tkinter widgets for displaying multi-column listboxes and tables.
"""

import operator
from tkinter import Frame, Label, Listbox, Scrollbar, Tk

######################################################################
# Multi-Column Listbox
######################################################################


class MultiListbox(Frame):
    """
    A multi-column listbox, where the current selection applies to an
    entire row.  Based on the MultiListbox Tkinter widget
    recipe from the Python Cookbook (https://code.activestate.com/recipes/52266/)

    For the most part, ``MultiListbox`` methods delegate to its
    contained listboxes.  For any methods that do not have docstrings,
    see ``Tkinter.Listbox`` for a description of what that method does.
    """

    # /////////////////////////////////////////////////////////////////
    # Configuration
    # /////////////////////////////////////////////////////////////////

    #: Default configuration values for the frame.
    FRAME_CONFIG = dict(background="#888", takefocus=True, highlightthickness=1)

    #: Default configurations for the column labels.
    LABEL_CONFIG = dict(
        borderwidth=1,
        relief="raised",
        font="helvetica -16 bold",
        background="#444",
        foreground="white",
    )

    #: Default configuration for the column listboxes.
    LISTBOX_CONFIG = dict(
        borderwidth=1,
        selectborderwidth=0,
        highlightthickness=0,
        exportselection=False,
        selectbackground="#888",
        activestyle="none",
        takefocus=False,
    )

    # /////////////////////////////////////////////////////////////////
    # Constructor
    # /////////////////////////////////////////////////////////////////

    def __init__(self, master, columns, column_weights=None, cnf={}, **kw):
        """
        Construct a new multi-column listbox widget.

        :param master: The widget that should contain the new
            multi-column listbox.

        :param columns: Specifies what columns should be included in
            the new multi-column listbox.  If ``columns`` is an integer,
            then it is the number of columns to include.  If it is
            a list, then its length indicates the number of columns
            to include; and each element of the list will be used as
            a label for the corresponding column.

        :param cnf, kw: Configuration parameters for this widget.
            Use ``label_*`` to configure all labels; and ``listbox_*``
            to configure all listboxes.  E.g.:
                >>> root = Tk()  # doctest: +SKIP
                >>> MultiListbox(root, ["Subject", "Sender", "Date"], label_foreground='red').pack()  # doctest: +SKIP
        """
        # If columns was specified as an int, convert it to a list.
        if isinstance(columns, int):
            columns = list(range(columns))
            include_labels = False
        else:
            include_labels = True

        if len(columns) == 0:
            raise ValueError("Expected at least one column")

        # Instance variables
        self._column_names = tuple(columns)
        self._listboxes = []
        self._labels = []

        # Pick a default value for column_weights, if none was specified.
        if column_weights is None:
            column_weights = [1] * len(columns)
        elif len(column_weights) != len(columns):
            raise ValueError("Expected one column_weight for each column")
        self._column_weights = column_weights

        # Configure our widgets.
        Frame.__init__(self, master, **self.FRAME_CONFIG)
        self.grid_rowconfigure(1, weight=1)
        for i, label in enumerate(self._column_names):
            self.grid_columnconfigure(i, weight=column_weights[i])

            # Create a label for the column
            if include_labels:
                l = Label(self, text=label, **self.LABEL_CONFIG)
                self._labels.append(l)
                l.grid(column=i, row=0, sticky="news", padx=0, pady=0)
                l.column_index = i

            # Create a listbox for the column
            lb = Listbox(self, **self.LISTBOX_CONFIG)
            self._listboxes.append(lb)
            lb.grid(column=i, row=1, sticky="news", padx=0, pady=0)
            lb.column_index = i

            # Clicking or dragging selects:
            lb.bind("<Button-1>", self._select)
            lb.bind("<B1-Motion>", self._select)
            # Scroll wheel scrolls:
            lb.bind("<Button-4>", lambda e: self._scroll(-1))
            lb.bind("<Button-5>", lambda e: self._scroll(+1))
            lb.bind("<MouseWheel>", lambda e: self._scroll(e.delta))
            # Button 2 can be used to scan:
            lb.bind("<Button-2>", lambda e: self.scan_mark(e.x, e.y))
            lb.bind("<B2-Motion>", lambda e: self.scan_dragto(e.x, e.y))
            # Dragging outside the window has no effect (disable
            # the default listbox behavior, which scrolls):
            lb.bind("<B1-Leave>", lambda e: "break")
            # Columns can be resized by dragging them:
            lb.bind("<Button-1>", self._resize_column)

        # Columns can be resized by dragging them.  (This binding is
        # used if they click on the grid between columns:)
        self.bind("<Button-1>", self._resize_column)

        # Set up key bindings for the widget:
        self.bind("<Up>", lambda e: self.select(delta=-1))
        self.bind("<Down>", lambda e: self.select(delta=1))
        self.bind("<Prior>", lambda e: self.select(delta=-self._pagesize()))
        self.bind("<Next>", lambda e: self.select(delta=self._pagesize()))

        # Configuration customizations
        self.configure(cnf, **kw)

    # /////////////////////////////////////////////////////////////////
    # Column Resizing
    # /////////////////////////////////////////////////////////////////

    def _resize_column(self, event):
        """
        Callback used to resize a column of the table.  Return ``True``
        if the column is actually getting resized (if the user clicked
        on the far left or far right 5 pixels of a label); and
        ``False`` otherwies.
        """
        # If we're already waiting for a button release, then ignore
        # the new button press.
        if event.widget.bind("<ButtonRelease>"):
            return False

        # Decide which column (if any) to resize.
        self._resize_column_index = None
        if event.widget is self:
            for i, lb in enumerate(self._listboxes):
                if abs(event.x - (lb.winfo_x() + lb.winfo_width())) < 10:
                    self._resize_column_index = i
        elif event.x > (event.widget.winfo_width() - 5):
            self._resize_column_index = event.widget.column_index
        elif event.x < 5 and event.widget.column_index != 0:
            self._resize_column_index = event.widget.column_index - 1

        # Bind callbacks that are used to resize it.
        if self._resize_column_index is not None:
            event.widget.bind("<Motion>", self._resize_column_motion_cb)
            event.widget.bind(
                "<ButtonRelease-%d>" % event.num, self._resize_column_buttonrelease_cb
            )
            return True
        else:
            return False

    def _resize_column_motion_cb(self, event):
        lb = self._listboxes[self._resize_column_index]
        charwidth = lb.winfo_width() / lb["width"]

        x1 = event.x + event.widget.winfo_x()
        x2 = lb.winfo_x() + lb.winfo_width()

        lb["width"] = max(3, int(lb["width"] + (x1 - x2) // charwidth))

    def _resize_column_buttonrelease_cb(self, event):
        event.widget.unbind("<ButtonRelease-%d>" % event.num)
        event.widget.unbind("<Motion>")

    # /////////////////////////////////////////////////////////////////
    # Properties
    # /////////////////////////////////////////////////////////////////

    @property
    def column_names(self):
        """
        A tuple containing the names of the columns used by this
        multi-column listbox.
        """
        return self._column_names

    @property
    def column_labels(self):
        """
        A tuple containing the ``Tkinter.Label`` widgets used to
        display the label of each column.  If this multi-column
        listbox was created without labels, then this will be an empty
        tuple.  These widgets will all be augmented with a
        ``column_index`` attribute, which can be used to determine
        which column they correspond to.  This can be convenient,
        e.g., when defining callbacks for bound events.
        """
        return tuple(self._labels)

    @property
    def listboxes(self):
        """
        A tuple containing the ``Tkinter.Listbox`` widgets used to
        display individual columns.  These widgets will all be
        augmented with a ``column_index`` attribute, which can be used
        to determine which column they correspond to.  This can be
        convenient, e.g., when defining callbacks for bound events.
        """
        return tuple(self._listboxes)

    # /////////////////////////////////////////////////////////////////
    # Mouse & Keyboard Callback Functions
    # /////////////////////////////////////////////////////////////////

    def _select(self, e):
        i = e.widget.nearest(e.y)
        self.selection_clear(0, "end")
        self.selection_set(i)
        self.activate(i)
        self.focus()

    def _scroll(self, delta):
        for lb in self._listboxes:
            lb.yview_scroll(delta, "unit")
        return "break"

    def _pagesize(self):
        """:return: The number of rows that makes up one page"""
        return int(self.index("@0,1000000")) - int(self.index("@0,0"))

    # /////////////////////////////////////////////////////////////////
    # Row selection
    # /////////////////////////////////////////////////////////////////

    def select(self, index=None, delta=None, see=True):
        """
        Set the selected row.  If ``index`` is specified, then select
        row ``index``.  Otherwise, if ``delta`` is specified, then move
        the current selection by ``delta`` (negative numbers for up,
        positive numbers for down).  This will not move the selection
        past the top or the bottom of the list.

        :param see: If true, then call ``self.see()`` with the newly
            selected index, to ensure that it is visible.
        """
        if (index is not None) and (delta is not None):
            raise ValueError("specify index or delta, but not both")

        # If delta was given, then calculate index.
        if delta is not None:
            if len(self.curselection()) == 0:
                index = -1 + delta
            else:
                index = int(self.curselection()[0]) + delta

        # Clear all selected rows.
        self.selection_clear(0, "end")

        # Select the specified index
        if index is not None:
            index = min(max(index, 0), self.size() - 1)
            # self.activate(index)
            self.selection_set(index)
            if see:
                self.see(index)

    # /////////////////////////////////////////////////////////////////
    # Configuration
    # /////////////////////////////////////////////////////////////////

    def configure(self, cnf={}, **kw):
        """
        Configure this widget.  Use ``label_*`` to configure all
        labels; and ``listbox_*`` to configure all listboxes.  E.g.:

                >>> master = Tk()  # doctest: +SKIP
                >>> mlb = MultiListbox(master, 5)  # doctest: +SKIP
                >>> mlb.configure(label_foreground='red')  # doctest: +SKIP
                >>> mlb.configure(listbox_foreground='red')  # doctest: +SKIP
        """
        cnf = dict(list(cnf.items()) + list(kw.items()))
        for key, val in list(cnf.items()):
            if key.startswith("label_") or key.startswith("label-"):
                for label in self._labels:
                    label.configure({key[6:]: val})
            elif key.startswith("listbox_") or key.startswith("listbox-"):
                for listbox in self._listboxes:
                    listbox.configure({key[8:]: val})
            else:
                Frame.configure(self, {key: val})

    def __setitem__(self, key, val):
        """
        Configure this widget.  This is equivalent to
        ``self.configure({key,val``)}.  See ``configure()``.
        """
        self.configure({key: val})

    def rowconfigure(self, row_index, cnf={}, **kw):
        """
        Configure all table cells in the given row.  Valid keyword
        arguments are: ``background``, ``bg``, ``foreground``, ``fg``,
        ``selectbackground``, ``selectforeground``.
        """
        for lb in self._listboxes:
            lb.itemconfigure(row_index, cnf, **kw)

    def columnconfigure(self, col_index, cnf={}, **kw):
        """
        Configure all table cells in the given column.  Valid keyword
        arguments are: ``background``, ``bg``, ``foreground``, ``fg``,
        ``selectbackground``, ``selectforeground``.
        """
        lb = self._listboxes[col_index]

        cnf = dict(list(cnf.items()) + list(kw.items()))
        for key, val in list(cnf.items()):
            if key in (
                "background",
                "bg",
                "foreground",
                "fg",
                "selectbackground",
                "selectforeground",
            ):
                for i in range(lb.size()):
                    lb.itemconfigure(i, {key: val})
            else:
                lb.configure({key: val})

    def itemconfigure(self, row_index, col_index, cnf=None, **kw):
        """
        Configure the table cell at the given row and column.  Valid
        keyword arguments are: ``background``, ``bg``, ``foreground``,
        ``fg``, ``selectbackground``, ``selectforeground``.
        """
        lb = self._listboxes[col_index]
        return lb.itemconfigure(row_index, cnf, **kw)

    # /////////////////////////////////////////////////////////////////
    # Value Access
    # /////////////////////////////////////////////////////////////////

    def insert(self, index, *rows):
        """
        Insert the given row or rows into the table, at the given
        index.  Each row value should be a tuple of cell values, one
        for each column in the row.  Index may be an integer or any of
        the special strings (such as ``'end'``) accepted by
        ``Tkinter.Listbox``.
        """
        for elt in rows:
            if len(elt) != len(self._column_names):
                raise ValueError(
                    "rows should be tuples whose length "
                    "is equal to the number of columns"
                )
        for lb, elts in zip(self._listboxes, list(zip(*rows))):
            lb.insert(index, *elts)

    def get(self, first, last=None):
        """
        Return the value(s) of the specified row(s).  If ``last`` is
        not specified, then return a single row value; otherwise,
        return a list of row values.  Each row value is a tuple of
        cell values, one for each column in the row.
        """
        values = [lb.get(first, last) for lb in self._listboxes]
        if last:
            return [tuple(row) for row in zip(*values)]
        else:
            return tuple(values)

    def bbox(self, row, col):
        """
        Return the bounding box for the given table cell, relative to
        this widget's top-left corner.  The bounding box is a tuple
        of integers ``(left, top, width, height)``.
        """
        dx, dy, _, _ = self.grid_bbox(row=0, column=col)
        x, y, w, h = self._listboxes[col].bbox(row)
        return int(x) + int(dx), int(y) + int(dy), int(w), int(h)

    # /////////////////////////////////////////////////////////////////
    # Hide/Show Columns
    # /////////////////////////////////////////////////////////////////

    def hide_column(self, col_index):
        """
        Hide the given column.  The column's state is still
        maintained: its values will still be returned by ``get()``, and
        you must supply its values when calling ``insert()``.  It is
        safe to call this on a column that is already hidden.

        :see: ``show_column()``
        """
        if self._labels:
            self._labels[col_index].grid_forget()
        self.listboxes[col_index].grid_forget()
        self.grid_columnconfigure(col_index, weight=0)

    def show_column(self, col_index):
        """
        Display a column that has been hidden using ``hide_column()``.
        It is safe to call this on a column that is not hidden.
        """
        weight = self._column_weights[col_index]
        if self._labels:
            self._labels[col_index].grid(
                column=col_index, row=0, sticky="news", padx=0, pady=0
            )
        self._listboxes[col_index].grid(
            column=col_index, row=1, sticky="news", padx=0, pady=0
        )
        self.grid_columnconfigure(col_index, weight=weight)

    # /////////////////////////////////////////////////////////////////
    # Binding Methods
    # /////////////////////////////////////////////////////////////////

    def bind_to_labels(self, sequence=None, func=None, add=None):
        """
        Add a binding to each ``Tkinter.Label`` widget in this
        mult-column listbox that will call ``func`` in response to the
        event sequence.

        :return: A list of the identifiers of replaced binding
            functions (if any), allowing for their deletion (to
            prevent a memory leak).
        """
        return [label.bind(sequence, func, add) for label in self.column_labels]

    def bind_to_listboxes(self, sequence=None, func=None, add=None):
        """
        Add a binding to each ``Tkinter.Listbox`` widget in this
        mult-column listbox that will call ``func`` in response to the
        event sequence.

        :return: A list of the identifiers of replaced binding
            functions (if any), allowing for their deletion (to
            prevent a memory leak).
        """
        for listbox in self.listboxes:
            listbox.bind(sequence, func, add)

    def bind_to_columns(self, sequence=None, func=None, add=None):
        """
        Add a binding to each ``Tkinter.Label`` and ``Tkinter.Listbox``
        widget in this mult-column listbox that will call ``func`` in
        response to the event sequence.

        :return: A list of the identifiers of replaced binding
            functions (if any), allowing for their deletion (to
            prevent a memory leak).
        """
        return self.bind_to_labels(sequence, func, add) + self.bind_to_listboxes(
            sequence, func, add
        )

    # /////////////////////////////////////////////////////////////////
    # Simple Delegation
    # /////////////////////////////////////////////////////////////////

    # These methods delegate to the first listbox:
    def curselection(self, *args, **kwargs):
        return self._listboxes[0].curselection(*args, **kwargs)

    def selection_includes(self, *args, **kwargs):
        return self._listboxes[0].selection_includes(*args, **kwargs)

    def itemcget(self, *args, **kwargs):
        return self._listboxes[0].itemcget(*args, **kwargs)

    def size(self, *args, **kwargs):
        return self._listboxes[0].size(*args, **kwargs)

    def index(self, *args, **kwargs):
        return self._listboxes[0].index(*args, **kwargs)

    def nearest(self, *args, **kwargs):
        return self._listboxes[0].nearest(*args, **kwargs)

    # These methods delegate to each listbox (and return None):
    def activate(self, *args, **kwargs):
        for lb in self._listboxes:
            lb.activate(*args, **kwargs)

    def delete(self, *args, **kwargs):
        for lb in self._listboxes:
            lb.delete(*args, **kwargs)

    def scan_mark(self, *args, **kwargs):
        for lb in self._listboxes:
            lb.scan_mark(*args, **kwargs)

    def scan_dragto(self, *args, **kwargs):
        for lb in self._listboxes:
            lb.scan_dragto(*args, **kwargs)

    def see(self, *args, **kwargs):
        for lb in self._listboxes:
            lb.see(*args, **kwargs)

    def selection_anchor(self, *args, **kwargs):
        for lb in self._listboxes:
            lb.selection_anchor(*args, **kwargs)

    def selection_clear(self, *args, **kwargs):
        for lb in self._listboxes:
            lb.selection_clear(*args, **kwargs)

    def selection_set(self, *args, **kwargs):
        for lb in self._listboxes:
            lb.selection_set(*args, **kwargs)

    def yview(self, *args, **kwargs):
        for lb in self._listboxes:
            v = lb.yview(*args, **kwargs)
        return v  # if called with no arguments

    def yview_moveto(self, *args, **kwargs):
        for lb in self._listboxes:
            lb.yview_moveto(*args, **kwargs)

    def yview_scroll(self, *args, **kwargs):
        for lb in self._listboxes:
            lb.yview_scroll(*args, **kwargs)

    # /////////////////////////////////////////////////////////////////
    # Aliases
    # /////////////////////////////////////////////////////////////////

    itemconfig = itemconfigure
    rowconfig = rowconfigure
    columnconfig = columnconfigure
    select_anchor = selection_anchor
    select_clear = selection_clear
    select_includes = selection_includes
    select_set = selection_set

    # /////////////////////////////////////////////////////////////////
    # These listbox methods are not defined for multi-listbox
    # /////////////////////////////////////////////////////////////////
    # def xview(self, *what): pass
    # def xview_moveto(self, fraction): pass
    # def xview_scroll(self, number, what): pass


######################################################################
# Table
######################################################################


class Table:
    """
    A display widget for a table of values, based on a ``MultiListbox``
    widget.  For many purposes, ``Table`` can be treated as a
    list-of-lists.  E.g., table[i] is a list of the values for row i;
    and table.append(row) adds a new row with the given list of
    values.  Individual cells can be accessed using table[i,j], which
    refers to the j-th column of the i-th row.  This can be used to
    both read and write values from the table.  E.g.:

        >>> table[i,j] = 'hello'  # doctest: +SKIP

    The column (j) can be given either as an index number, or as a
    column name.  E.g., the following prints the value in the 3rd row
    for the 'First Name' column:

        >>> print(table[3, 'First Name'])  # doctest: +SKIP
        John

    You can configure the colors for individual rows, columns, or
    cells using ``rowconfig()``, ``columnconfig()``, and ``itemconfig()``.
    The color configuration for each row will be preserved if the
    table is modified; however, when new rows are added, any color
    configurations that have been made for *columns* will not be
    applied to the new row.

    Note: Although ``Table`` acts like a widget in some ways (e.g., it
    defines ``grid()``, ``pack()``, and ``bind()``), it is not itself a
    widget; it just contains one.  This is because widgets need to
    define ``__getitem__()``, ``__setitem__()``, and ``__nonzero__()`` in
    a way that's incompatible with the fact that ``Table`` behaves as a
    list-of-lists.

    :ivar _mlb: The multi-column listbox used to display this table's data.
    :ivar _rows: A list-of-lists used to hold the cell values of this
        table.  Each element of _rows is a row value, i.e., a list of
        cell values, one for each column in the row.
    """

    def __init__(
        self,
        master,
        column_names,
        rows=None,
        column_weights=None,
        scrollbar=True,
        click_to_sort=True,
        reprfunc=None,
        cnf={},
        **kw
    ):
        """
        Construct a new Table widget.

        :type master: Tkinter.Widget
        :param master: The widget that should contain the new table.
        :type column_names: list(str)
        :param column_names: A list of names for the columns; these
            names will be used to create labels for each column;
            and can be used as an index when reading or writing
            cell values from the table.
        :type rows: list(list)
        :param rows: A list of row values used to initialize the table.
            Each row value should be a tuple of cell values, one for
            each column in the row.
        :type scrollbar: bool
        :param scrollbar: If true, then create a scrollbar for the
            new table widget.
        :type click_to_sort: bool
        :param click_to_sort: If true, then create bindings that will
            sort the table's rows by a given column's values if the
            user clicks on that colum's label.
        :type reprfunc: function
        :param reprfunc: If specified, then use this function to
            convert each table cell value to a string suitable for
            display.  ``reprfunc`` has the following signature:
            reprfunc(row_index, col_index, cell_value) -> str
            (Note that the column is specified by index, not by name.)
        :param cnf, kw: Configuration parameters for this widget's
            contained ``MultiListbox``.  See ``MultiListbox.__init__()``
            for details.
        """
        self._num_columns = len(column_names)
        self._reprfunc = reprfunc
        self._frame = Frame(master)

        self._column_name_to_index = {c: i for (i, c) in enumerate(column_names)}

        # Make a copy of the rows & check that it's valid.
        if rows is None:
            self._rows = []
        else:
            self._rows = [[v for v in row] for row in rows]
        for row in self._rows:
            self._checkrow(row)

        # Create our multi-list box.
        self._mlb = MultiListbox(self._frame, column_names, column_weights, cnf, **kw)
        self._mlb.pack(side="left", expand=True, fill="both")

        # Optional scrollbar
        if scrollbar:
            sb = Scrollbar(self._frame, orient="vertical", command=self._mlb.yview)
            self._mlb.listboxes[0]["yscrollcommand"] = sb.set
            # for listbox in self._mlb.listboxes:
            #    listbox['yscrollcommand'] = sb.set
            sb.pack(side="right", fill="y")
            self._scrollbar = sb

        # Set up sorting
        self._sortkey = None
        if click_to_sort:
            for i, l in enumerate(self._mlb.column_labels):
                l.bind("<Button-1>", self._sort)

        # Fill in our multi-list box.
        self._fill_table()

    # /////////////////////////////////////////////////////////////////
    # { Widget-like Methods
    # /////////////////////////////////////////////////////////////////
    # These all just delegate to either our frame or our MLB.

    def pack(self, *args, **kwargs):
        """Position this table's main frame widget in its parent
        widget.  See ``Tkinter.Frame.pack()`` for more info."""
        self._frame.pack(*args, **kwargs)

    def grid(self, *args, **kwargs):
        """Position this table's main frame widget in its parent
        widget.  See ``Tkinter.Frame.grid()`` for more info."""
        self._frame.grid(*args, **kwargs)

    def focus(self):
        """Direct (keyboard) input foxus to this widget."""
        self._mlb.focus()

    def bind(self, sequence=None, func=None, add=None):
        """Add a binding to this table's main frame that will call
        ``func`` in response to the event sequence."""
        self._mlb.bind(sequence, func, add)

    def rowconfigure(self, row_index, cnf={}, **kw):
        """:see: ``MultiListbox.rowconfigure()``"""
        self._mlb.rowconfigure(row_index, cnf, **kw)

    def columnconfigure(self, col_index, cnf={}, **kw):
        """:see: ``MultiListbox.columnconfigure()``"""
        col_index = self.column_index(col_index)
        self._mlb.columnconfigure(col_index, cnf, **kw)

    def itemconfigure(self, row_index, col_index, cnf=None, **kw):
        """:see: ``MultiListbox.itemconfigure()``"""
        col_index = self.column_index(col_index)
        return self._mlb.itemconfigure(row_index, col_index, cnf, **kw)

    def bind_to_labels(self, sequence=None, func=None, add=None):
        """:see: ``MultiListbox.bind_to_labels()``"""
        return self._mlb.bind_to_labels(sequence, func, add)

    def bind_to_listboxes(self, sequence=None, func=None, add=None):
        """:see: ``MultiListbox.bind_to_listboxes()``"""
        return self._mlb.bind_to_listboxes(sequence, func, add)

    def bind_to_columns(self, sequence=None, func=None, add=None):
        """:see: ``MultiListbox.bind_to_columns()``"""
        return self._mlb.bind_to_columns(sequence, func, add)

    rowconfig = rowconfigure
    columnconfig = columnconfigure
    itemconfig = itemconfigure

    # /////////////////////////////////////////////////////////////////
    # { Table as list-of-lists
    # /////////////////////////////////////////////////////////////////

    def insert(self, row_index, rowvalue):
        """
        Insert a new row into the table, so that its row index will be
        ``row_index``.  If the table contains any rows whose row index
        is greater than or equal to ``row_index``, then they will be
        shifted down.

        :param rowvalue: A tuple of cell values, one for each column
            in the new row.
        """
        self._checkrow(rowvalue)
        self._rows.insert(row_index, rowvalue)
        if self._reprfunc is not None:
            rowvalue = [
                self._reprfunc(row_index, j, v) for (j, v) in enumerate(rowvalue)
            ]
        self._mlb.insert(row_index, rowvalue)
        if self._DEBUG:
            self._check_table_vs_mlb()

    def extend(self, rowvalues):
        """
        Add new rows at the end of the table.

        :param rowvalues: A list of row values used to initialize the
            table.  Each row value should be a tuple of cell values,
            one for each column in the row.
        """
        for rowvalue in rowvalues:
            self.append(rowvalue)
        if self._DEBUG:
            self._check_table_vs_mlb()

    def append(self, rowvalue):
        """
        Add a new row to the end of the table.

        :param rowvalue: A tuple of cell values, one for each column
            in the new row.
        """
        self.insert(len(self._rows), rowvalue)
        if self._DEBUG:
            self._check_table_vs_mlb()

    def clear(self):
        """
        Delete all rows in this table.
        """
        self._rows = []
        self._mlb.delete(0, "end")
        if self._DEBUG:
            self._check_table_vs_mlb()

    def __getitem__(self, index):
        """
        Return the value of a row or a cell in this table.  If
        ``index`` is an integer, then the row value for the ``index``th
        row.  This row value consists of a tuple of cell values, one
        for each column in the row.  If ``index`` is a tuple of two
        integers, ``(i,j)``, then return the value of the cell in the
        ``i``th row and the ``j``th column.
        """
        if isinstance(index, slice):
            raise ValueError("Slicing not supported")
        elif isinstance(index, tuple) and len(index) == 2:
            return self._rows[index[0]][self.column_index(index[1])]
        else:
            return tuple(self._rows[index])

    def __setitem__(self, index, val):
        """
        Replace the value of a row or a cell in this table with
        ``val``.

        If ``index`` is an integer, then ``val`` should be a row value
        (i.e., a tuple of cell values, one for each column).  In this
        case, the values of the ``index``th row of the table will be
        replaced with the values in ``val``.

        If ``index`` is a tuple of integers, ``(i,j)``, then replace the
        value of the cell in the ``i``th row and ``j``th column with
        ``val``.
        """
        if isinstance(index, slice):
            raise ValueError("Slicing not supported")

        # table[i,j] = val
        elif isinstance(index, tuple) and len(index) == 2:
            i, j = index[0], self.column_index(index[1])
            config_cookie = self._save_config_info([i])
            self._rows[i][j] = val
            if self._reprfunc is not None:
                val = self._reprfunc(i, j, val)
            self._mlb.listboxes[j].insert(i, val)
            self._mlb.listboxes[j].delete(i + 1)
            self._restore_config_info(config_cookie)

        # table[i] = val
        else:
            config_cookie = self._save_config_info([index])
            self._checkrow(val)
            self._rows[index] = list(val)
            if self._reprfunc is not None:
                val = [self._reprfunc(index, j, v) for (j, v) in enumerate(val)]
            self._mlb.insert(index, val)
            self._mlb.delete(index + 1)
            self._restore_config_info(config_cookie)

    def __delitem__(self, row_index):
        """
        Delete the ``row_index``th row from this table.
        """
        if isinstance(row_index, slice):
            raise ValueError("Slicing not supported")
        if isinstance(row_index, tuple) and len(row_index) == 2:
            raise ValueError("Cannot delete a single cell!")
        del self._rows[row_index]
        self._mlb.delete(row_index)
        if self._DEBUG:
            self._check_table_vs_mlb()

    def __len__(self):
        """
        :return: the number of rows in this table.
        """
        return len(self._rows)

    def _checkrow(self, rowvalue):
        """
        Helper function: check that a given row value has the correct
        number of elements; and if not, raise an exception.
        """
        if len(rowvalue) != self._num_columns:
            raise ValueError(
                "Row %r has %d columns; expected %d"
                % (rowvalue, len(rowvalue), self._num_columns)
            )

    # /////////////////////////////////////////////////////////////////
    # Columns
    # /////////////////////////////////////////////////////////////////

    @property
    def column_names(self):
        """A list of the names of the columns in this table."""
        return self._mlb.column_names

    def column_index(self, i):
        """
        If ``i`` is a valid column index integer, then return it as is.
        Otherwise, check if ``i`` is used as the name for any column;
        if so, return that column's index.  Otherwise, raise a
        ``KeyError`` exception.
        """
        if isinstance(i, int) and 0 <= i < self._num_columns:
            return i
        else:
            # This raises a key error if the column is not found.
            return self._column_name_to_index[i]

    def hide_column(self, column_index):
        """:see: ``MultiListbox.hide_column()``"""
        self._mlb.hide_column(self.column_index(column_index))

    def show_column(self, column_index):
        """:see: ``MultiListbox.show_column()``"""
        self._mlb.show_column(self.column_index(column_index))

    # /////////////////////////////////////////////////////////////////
    # Selection
    # /////////////////////////////////////////////////////////////////

    def selected_row(self):
        """
        Return the index of the currently selected row, or None if
        no row is selected.  To get the row value itself, use
        ``table[table.selected_row()]``.
        """
        sel = self._mlb.curselection()
        if sel:
            return int(sel[0])
        else:
            return None

    def select(self, index=None, delta=None, see=True):
        """:see: ``MultiListbox.select()``"""
        self._mlb.select(index, delta, see)

    # /////////////////////////////////////////////////////////////////
    # Sorting
    # /////////////////////////////////////////////////////////////////

    def sort_by(self, column_index, order="toggle"):
        """
        Sort the rows in this table, using the specified column's
        values as a sort key.

        :param column_index: Specifies which column to sort, using
            either a column index (int) or a column's label name
            (str).

        :param order: Specifies whether to sort the values in
            ascending or descending order:

              - ``'ascending'``: Sort from least to greatest.
              - ``'descending'``: Sort from greatest to least.
              - ``'toggle'``: If the most recent call to ``sort_by()``
                sorted the table by the same column (``column_index``),
                then reverse the rows; otherwise sort in ascending
                order.
        """
        if order not in ("ascending", "descending", "toggle"):
            raise ValueError(
                'sort_by(): order should be "ascending", ' '"descending", or "toggle".'
            )
        column_index = self.column_index(column_index)
        config_cookie = self._save_config_info(index_by_id=True)

        # Sort the rows.
        if order == "toggle" and column_index == self._sortkey:
            self._rows.reverse()
        else:
            self._rows.sort(
                key=operator.itemgetter(column_index), reverse=(order == "descending")
            )
            self._sortkey = column_index

        # Redraw the table.
        self._fill_table()
        self._restore_config_info(config_cookie, index_by_id=True, see=True)
        if self._DEBUG:
            self._check_table_vs_mlb()

    def _sort(self, event):
        """Event handler for clicking on a column label -- sort by
        that column."""
        column_index = event.widget.column_index

        # If they click on the far-left of far-right of a column's
        # label, then resize rather than sorting.
        if self._mlb._resize_column(event):
            return "continue"

        # Otherwise, sort.
        else:
            self.sort_by(column_index)
            return "continue"

    # /////////////////////////////////////////////////////////////////
    # { Table Drawing Helpers
    # /////////////////////////////////////////////////////////////////

    def _fill_table(self, save_config=True):
        """
        Re-draw the table from scratch, by clearing out the table's
        multi-column listbox; and then filling it in with values from
        ``self._rows``.  Note that any cell-, row-, or column-specific
        color configuration that has been done will be lost.  The
        selection will also be lost -- i.e., no row will be selected
        after this call completes.
        """
        self._mlb.delete(0, "end")
        for i, row in enumerate(self._rows):
            if self._reprfunc is not None:
                row = [self._reprfunc(i, j, v) for (j, v) in enumerate(row)]
            self._mlb.insert("end", row)

    def _get_itemconfig(self, r, c):
        return {
            k: self._mlb.itemconfig(r, c, k)[-1]
            for k in (
                "foreground",
                "selectforeground",
                "background",
                "selectbackground",
            )
        }

    def _save_config_info(self, row_indices=None, index_by_id=False):
        """
        Return a 'cookie' containing information about which row is
        selected, and what color configurations have been applied.
        this information can the be re-applied to the table (after
        making modifications) using ``_restore_config_info()``.  Color
        configuration information will be saved for any rows in
        ``row_indices``, or in the entire table, if
        ``row_indices=None``.  If ``index_by_id=True``, the the cookie
        will associate rows with their configuration information based
        on the rows' python id.  This is useful when performing
        operations that re-arrange the rows (e.g. ``sort``).  If
        ``index_by_id=False``, then it is assumed that all rows will be
        in the same order when ``_restore_config_info()`` is called.
        """
        # Default value for row_indices is all rows.
        if row_indices is None:
            row_indices = list(range(len(self._rows)))

        # Look up our current selection.
        selection = self.selected_row()
        if index_by_id and selection is not None:
            selection = id(self._rows[selection])

        # Look up the color configuration info for each row.
        if index_by_id:
            config = {
                id(self._rows[r]): [
                    self._get_itemconfig(r, c) for c in range(self._num_columns)
                ]
                for r in row_indices
            }
        else:
            config = {
                r: [self._get_itemconfig(r, c) for c in range(self._num_columns)]
                for r in row_indices
            }

        return selection, config

    def _restore_config_info(self, cookie, index_by_id=False, see=False):
        """
        Restore selection & color configuration information that was
        saved using ``_save_config_info``.
        """
        selection, config = cookie

        # Clear the selection.
        if selection is None:
            self._mlb.selection_clear(0, "end")

        # Restore selection & color config
        if index_by_id:
            for r, row in enumerate(self._rows):
                if id(row) in config:
                    for c in range(self._num_columns):
                        self._mlb.itemconfigure(r, c, config[id(row)][c])
                if id(row) == selection:
                    self._mlb.select(r, see=see)
        else:
            if selection is not None:
                self._mlb.select(selection, see=see)
            for r in config:
                for c in range(self._num_columns):
                    self._mlb.itemconfigure(r, c, config[r][c])

    # /////////////////////////////////////////////////////////////////
    # Debugging (Invariant Checker)
    # /////////////////////////////////////////////////////////////////

    _DEBUG = False
    """If true, then run ``_check_table_vs_mlb()`` after any operation
       that modifies the table."""

    def _check_table_vs_mlb(self):
        """
        Verify that the contents of the table's ``_rows`` variable match
        the contents of its multi-listbox (``_mlb``).  This is just
        included for debugging purposes, to make sure that the
        list-modifying operations are working correctly.
        """
        for col in self._mlb.listboxes:
            assert len(self) == col.size()
        for row in self:
            assert len(row) == self._num_columns
        assert self._num_columns == len(self._mlb.column_names)
        # assert self._column_names == self._mlb.column_names
        for i, row in enumerate(self):
            for j, cell in enumerate(row):
                if self._reprfunc is not None:
                    cell = self._reprfunc(i, j, cell)
                assert self._mlb.get(i)[j] == cell


######################################################################
# Demo/Test Function
######################################################################


# update this to use new WordNet API
def demo():
    root = Tk()
    root.bind("<Control-q>", lambda e: root.destroy())

    table = Table(
        root,
        "Word Synset Hypernym Hyponym".split(),
        column_weights=[0, 1, 1, 1],
        reprfunc=(lambda i, j, s: "  %s" % s),
    )
    table.pack(expand=True, fill="both")

    from nltk.corpus import brown, wordnet

    for word, pos in sorted(set(brown.tagged_words()[:500])):
        if pos[0] != "N":
            continue
        word = word.lower()
        for synset in wordnet.synsets(word):
            try:
                hyper_def = synset.hypernyms()[0].definition()
            except:
                hyper_def = "*none*"
            try:
                hypo_def = synset.hypernyms()[0].definition()
            except:
                hypo_def = "*none*"
            table.append([word, synset.definition(), hyper_def, hypo_def])

    table.columnconfig("Word", background="#afa")
    table.columnconfig("Synset", background="#efe")
    table.columnconfig("Hypernym", background="#fee")
    table.columnconfig("Hyponym", background="#ffe")
    for row in range(len(table)):
        for column in ("Hypernym", "Hyponym"):
            if table[row, column] == "*none*":
                table.itemconfig(
                    row, column, foreground="#666", selectforeground="#666"
                )
    root.mainloop()


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\importlib_metadata\__init__.py ===
"""
APIs exposing metadata from third-party Python packages.

This codebase is shared between importlib.metadata in the stdlib
and importlib_metadata in PyPI. See
https://github.com/python/importlib_metadata/wiki/Development-Methodology
for more detail.
"""

from __future__ import annotations

import abc
import collections
import email
import functools
import itertools
import operator
import os
import pathlib
import posixpath
import re
import sys
import textwrap
import types
from collections.abc import Iterable, Mapping
from contextlib import suppress
from importlib import import_module
from importlib.abc import MetaPathFinder
from itertools import starmap
from typing import Any

from . import _meta
from ._collections import FreezableDefaultDict, Pair
from ._compat import (
    NullFinder,
    install,
)
from ._functools import method_cache, pass_none
from ._itertools import always_iterable, bucket, unique_everseen
from ._meta import PackageMetadata, SimplePath
from ._typing import md_none
from .compat import py39, py311

__all__ = [
    'Distribution',
    'DistributionFinder',
    'PackageMetadata',
    'PackageNotFoundError',
    'SimplePath',
    'distribution',
    'distributions',
    'entry_points',
    'files',
    'metadata',
    'packages_distributions',
    'requires',
    'version',
]


class PackageNotFoundError(ModuleNotFoundError):
    """The package was not found."""

    def __str__(self) -> str:
        return f"No package metadata was found for {self.name}"

    @property
    def name(self) -> str:  # type: ignore[override] # make readonly
        (name,) = self.args
        return name


class Sectioned:
    """
    A simple entry point config parser for performance

    >>> for item in Sectioned.read(Sectioned._sample):
    ...     print(item)
    Pair(name='sec1', value='# comments ignored')
    Pair(name='sec1', value='a = 1')
    Pair(name='sec1', value='b = 2')
    Pair(name='sec2', value='a = 2')

    >>> res = Sectioned.section_pairs(Sectioned._sample)
    >>> item = next(res)
    >>> item.name
    'sec1'
    >>> item.value
    Pair(name='a', value='1')
    >>> item = next(res)
    >>> item.value
    Pair(name='b', value='2')
    >>> item = next(res)
    >>> item.name
    'sec2'
    >>> item.value
    Pair(name='a', value='2')
    >>> list(res)
    []
    """

    _sample = textwrap.dedent(
        """
        [sec1]
        # comments ignored
        a = 1
        b = 2

        [sec2]
        a = 2
        """
    ).lstrip()

    @classmethod
    def section_pairs(cls, text):
        return (
            section._replace(value=Pair.parse(section.value))
            for section in cls.read(text, filter_=cls.valid)
            if section.name is not None
        )

    @staticmethod
    def read(text, filter_=None):
        lines = filter(filter_, map(str.strip, text.splitlines()))
        name = None
        for value in lines:
            section_match = value.startswith('[') and value.endswith(']')
            if section_match:
                name = value.strip('[]')
                continue
            yield Pair(name, value)

    @staticmethod
    def valid(line: str):
        return line and not line.startswith('#')


class _EntryPointMatch(types.SimpleNamespace):
    module: str
    attr: str
    extras: str


class EntryPoint:
    """An entry point as defined by Python packaging conventions.

    See `the packaging docs on entry points
    <https://packaging.python.org/specifications/entry-points/>`_
    for more information.

    >>> ep = EntryPoint(
    ...     name=None, group=None, value='package.module:attr [extra1, extra2]')
    >>> ep.module
    'package.module'
    >>> ep.attr
    'attr'
    >>> ep.extras
    ['extra1', 'extra2']

    If the value package or module are not valid identifiers, a
    ValueError is raised on access.

    >>> EntryPoint(name=None, group=None, value='invalid-name').module
    Traceback (most recent call last):
    ...
    ValueError: ('Invalid object reference...invalid-name...
    >>> EntryPoint(name=None, group=None, value='invalid-name').attr
    Traceback (most recent call last):
    ...
    ValueError: ('Invalid object reference...invalid-name...
    >>> EntryPoint(name=None, group=None, value='invalid-name').extras
    Traceback (most recent call last):
    ...
    ValueError: ('Invalid object reference...invalid-name...

    The same thing happens on construction.

    >>> EntryPoint(name=None, group=None, value='invalid-name')
    Traceback (most recent call last):
    ...
    ValueError: ('Invalid object reference...invalid-name...

    """

    pattern = re.compile(
        r'(?P<module>[\w.]+)\s*'
        r'(:\s*(?P<attr>[\w.]+)\s*)?'
        r'((?P<extras>\[.*\])\s*)?$'
    )
    """
    A regular expression describing the syntax for an entry point,
    which might look like:

        - module
        - package.module
        - package.module:attribute
        - package.module:object.attribute
        - package.module:attr [extra1, extra2]

    Other combinations are possible as well.

    The expression is lenient about whitespace around the ':',
    following the attr, and following any extras.
    """

    name: str
    value: str
    group: str

    dist: Distribution | None = None

    def __init__(self, name: str, value: str, group: str) -> None:
        vars(self).update(name=name, value=value, group=group)
        self.module

    def load(self) -> Any:
        """Load the entry point from its definition. If only a module
        is indicated by the value, return that module. Otherwise,
        return the named object.
        """
        module = import_module(self.module)
        attrs = filter(None, (self.attr or '').split('.'))
        return functools.reduce(getattr, attrs, module)

    @property
    def module(self) -> str:
        return self._match.module

    @property
    def attr(self) -> str:
        return self._match.attr

    @property
    def extras(self) -> list[str]:
        return re.findall(r'\w+', self._match.extras or '')

    @functools.cached_property
    def _match(self) -> _EntryPointMatch:
        match = self.pattern.match(self.value)
        if not match:
            raise ValueError(
                'Invalid object reference. '
                'See https://packaging.python.org'
                '/en/latest/specifications/entry-points/#data-model',
                self.value,
            )
        return _EntryPointMatch(**match.groupdict())

    def _for(self, dist):
        vars(self).update(dist=dist)
        return self

    def matches(self, **params):
        """
        EntryPoint matches the given parameters.

        >>> ep = EntryPoint(group='foo', name='bar', value='bing:bong [extra1, extra2]')
        >>> ep.matches(group='foo')
        True
        >>> ep.matches(name='bar', value='bing:bong [extra1, extra2]')
        True
        >>> ep.matches(group='foo', name='other')
        False
        >>> ep.matches()
        True
        >>> ep.matches(extras=['extra1', 'extra2'])
        True
        >>> ep.matches(module='bing')
        True
        >>> ep.matches(attr='bong')
        True
        """
        self._disallow_dist(params)
        attrs = (getattr(self, param) for param in params)
        return all(map(operator.eq, params.values(), attrs))

    @staticmethod
    def _disallow_dist(params):
        """
        Querying by dist is not allowed (dist objects are not comparable).
        >>> EntryPoint(name='fan', value='fav', group='fag').matches(dist='foo')
        Traceback (most recent call last):
        ...
        ValueError: "dist" is not suitable for matching...
        """
        if "dist" in params:
            raise ValueError(
                '"dist" is not suitable for matching. '
                "Instead, use Distribution.entry_points.select() on a "
                "located distribution."
            )

    def _key(self):
        return self.name, self.value, self.group

    def __lt__(self, other):
        return self._key() < other._key()

    def __eq__(self, other):
        return self._key() == other._key()

    def __setattr__(self, name, value):
        raise AttributeError("EntryPoint objects are immutable.")

    def __repr__(self):
        return (
            f'EntryPoint(name={self.name!r}, value={self.value!r}, '
            f'group={self.group!r})'
        )

    def __hash__(self) -> int:
        return hash(self._key())


class EntryPoints(tuple):
    """
    An immutable collection of selectable EntryPoint objects.
    """

    __slots__ = ()

    def __getitem__(self, name: str) -> EntryPoint:  # type: ignore[override] # Work with str instead of int
        """
        Get the EntryPoint in self matching name.
        """
        try:
            return next(iter(self.select(name=name)))
        except StopIteration:
            raise KeyError(name)

    def __repr__(self):
        """
        Repr with classname and tuple constructor to
        signal that we deviate from regular tuple behavior.
        """
        return '%s(%r)' % (self.__class__.__name__, tuple(self))

    def select(self, **params) -> EntryPoints:
        """
        Select entry points from self that match the
        given parameters (typically group and/or name).
        """
        return EntryPoints(ep for ep in self if py39.ep_matches(ep, **params))

    @property
    def names(self) -> set[str]:
        """
        Return the set of all names of all entry points.
        """
        return {ep.name for ep in self}

    @property
    def groups(self) -> set[str]:
        """
        Return the set of all groups of all entry points.
        """
        return {ep.group for ep in self}

    @classmethod
    def _from_text_for(cls, text, dist):
        return cls(ep._for(dist) for ep in cls._from_text(text))

    @staticmethod
    def _from_text(text):
        return (
            EntryPoint(name=item.value.name, value=item.value.value, group=item.name)
            for item in Sectioned.section_pairs(text or '')
        )


class PackagePath(pathlib.PurePosixPath):
    """A reference to a path in a package"""

    hash: FileHash | None
    size: int
    dist: Distribution

    def read_text(self, encoding: str = 'utf-8') -> str:
        return self.locate().read_text(encoding=encoding)

    def read_binary(self) -> bytes:
        return self.locate().read_bytes()

    def locate(self) -> SimplePath:
        """Return a path-like object for this path"""
        return self.dist.locate_file(self)


class FileHash:
    def __init__(self, spec: str) -> None:
        self.mode, _, self.value = spec.partition('=')

    def __repr__(self) -> str:
        return f'<FileHash mode: {self.mode} value: {self.value}>'


class Distribution(metaclass=abc.ABCMeta):
    """
    An abstract Python distribution package.

    Custom providers may derive from this class and define
    the abstract methods to provide a concrete implementation
    for their environment. Some providers may opt to override
    the default implementation of some properties to bypass
    the file-reading mechanism.
    """

    @abc.abstractmethod
    def read_text(self, filename) -> str | None:
        """Attempt to load metadata file given by the name.

        Python distribution metadata is organized by blobs of text
        typically represented as "files" in the metadata directory
        (e.g. package-1.0.dist-info). These files include things
        like:

        - METADATA: The distribution metadata including fields
          like Name and Version and Description.
        - entry_points.txt: A series of entry points as defined in
          `the entry points spec <https://packaging.python.org/en/latest/specifications/entry-points/#file-format>`_.
        - RECORD: A record of files according to
          `this recording spec <https://packaging.python.org/en/latest/specifications/recording-installed-packages/#the-record-file>`_.

        A package may provide any set of files, including those
        not listed here or none at all.

        :param filename: The name of the file in the distribution info.
        :return: The text if found, otherwise None.
        """

    @abc.abstractmethod
    def locate_file(self, path: str | os.PathLike[str]) -> SimplePath:
        """
        Given a path to a file in this distribution, return a SimplePath
        to it.

        This method is used by callers of ``Distribution.files()`` to
        locate files within the distribution. If it's possible for a
        Distribution to represent files in the distribution as
        ``SimplePath`` objects, it should implement this method
        to resolve such objects.

        Some Distribution providers may elect not to resolve SimplePath
        objects within the distribution by raising a
        NotImplementedError, but consumers of such a Distribution would
        be unable to invoke ``Distribution.files()``.
        """

    @classmethod
    def from_name(cls, name: str) -> Distribution:
        """Return the Distribution for the given package name.

        :param name: The name of the distribution package to search for.
        :return: The Distribution instance (or subclass thereof) for the named
            package, if found.
        :raises PackageNotFoundError: When the named package's distribution
            metadata cannot be found.
        :raises ValueError: When an invalid value is supplied for name.
        """
        if not name:
            raise ValueError("A distribution name is required.")
        try:
            return next(iter(cls._prefer_valid(cls.discover(name=name))))
        except StopIteration:
            raise PackageNotFoundError(name)

    @classmethod
    def discover(
        cls, *, context: DistributionFinder.Context | None = None, **kwargs
    ) -> Iterable[Distribution]:
        """Return an iterable of Distribution objects for all packages.

        Pass a ``context`` or pass keyword arguments for constructing
        a context.

        :context: A ``DistributionFinder.Context`` object.
        :return: Iterable of Distribution objects for packages matching
          the context.
        """
        if context and kwargs:
            raise ValueError("cannot accept context and kwargs")
        context = context or DistributionFinder.Context(**kwargs)
        return itertools.chain.from_iterable(
            resolver(context) for resolver in cls._discover_resolvers()
        )

    @staticmethod
    def _prefer_valid(dists: Iterable[Distribution]) -> Iterable[Distribution]:
        """
        Prefer (move to the front) distributions that have metadata.

        Ref python/importlib_resources#489.
        """
        buckets = bucket(dists, lambda dist: bool(dist.metadata))
        return itertools.chain(buckets[True], buckets[False])

    @staticmethod
    def at(path: str | os.PathLike[str]) -> Distribution:
        """Return a Distribution for the indicated metadata path.

        :param path: a string or path-like object
        :return: a concrete Distribution instance for the path
        """
        return PathDistribution(pathlib.Path(path))

    @staticmethod
    def _discover_resolvers():
        """Search the meta_path for resolvers (MetadataPathFinders)."""
        declared = (
            getattr(finder, 'find_distributions', None) for finder in sys.meta_path
        )
        return filter(None, declared)

    @property
    def metadata(self) -> _meta.PackageMetadata | None:
        """Return the parsed metadata for this Distribution.

        The returned object will have keys that name the various bits of
        metadata per the
        `Core metadata specifications <https://packaging.python.org/en/latest/specifications/core-metadata/#core-metadata>`_.

        Custom providers may provide the METADATA file or override this
        property.
        """

        text = (
            self.read_text('METADATA')
            or self.read_text('PKG-INFO')
            # This last clause is here to support old egg-info files.  Its
            # effect is to just end up using the PathDistribution's self._path
            # (which points to the egg-info file) attribute unchanged.
            or self.read_text('')
        )
        return self._assemble_message(text)

    @staticmethod
    @pass_none
    def _assemble_message(text: str) -> _meta.PackageMetadata:
        # deferred for performance (python/cpython#109829)
        from . import _adapters

        return _adapters.Message(email.message_from_string(text))

    @property
    def name(self) -> str:
        """Return the 'Name' metadata for the distribution package."""
        return md_none(self.metadata)['Name']

    @property
    def _normalized_name(self):
        """Return a normalized version of the name."""
        return Prepared.normalize(self.name)

    @property
    def version(self) -> str:
        """Return the 'Version' metadata for the distribution package."""
        return md_none(self.metadata)['Version']

    @property
    def entry_points(self) -> EntryPoints:
        """
        Return EntryPoints for this distribution.

        Custom providers may provide the ``entry_points.txt`` file
        or override this property.
        """
        return EntryPoints._from_text_for(self.read_text('entry_points.txt'), self)

    @property
    def files(self) -> list[PackagePath] | None:
        """Files in this distribution.

        :return: List of PackagePath for this distribution or None

        Result is `None` if the metadata file that enumerates files
        (i.e. RECORD for dist-info, or installed-files.txt or
        SOURCES.txt for egg-info) is missing.
        Result may be empty if the metadata exists but is empty.

        Custom providers are recommended to provide a "RECORD" file (in
        ``read_text``) or override this property to allow for callers to be
        able to resolve filenames provided by the package.
        """

        def make_file(name, hash=None, size_str=None):
            result = PackagePath(name)
            result.hash = FileHash(hash) if hash else None
            result.size = int(size_str) if size_str else None
            result.dist = self
            return result

        @pass_none
        def make_files(lines):
            # Delay csv import, since Distribution.files is not as widely used
            # as other parts of importlib.metadata
            import csv

            return starmap(make_file, csv.reader(lines))

        @pass_none
        def skip_missing_files(package_paths):
            return list(filter(lambda path: path.locate().exists(), package_paths))

        return skip_missing_files(
            make_files(
                self._read_files_distinfo()
                or self._read_files_egginfo_installed()
                or self._read_files_egginfo_sources()
            )
        )

    def _read_files_distinfo(self):
        """
        Read the lines of RECORD.
        """
        text = self.read_text('RECORD')
        return text and text.splitlines()

    def _read_files_egginfo_installed(self):
        """
        Read installed-files.txt and return lines in a similar
        CSV-parsable format as RECORD: each file must be placed
        relative to the site-packages directory and must also be
        quoted (since file names can contain literal commas).

        This file is written when the package is installed by pip,
        but it might not be written for other installation methods.
        Assume the file is accurate if it exists.
        """
        text = self.read_text('installed-files.txt')
        # Prepend the .egg-info/ subdir to the lines in this file.
        # But this subdir is only available from PathDistribution's
        # self._path.
        subdir = getattr(self, '_path', None)
        if not text or not subdir:
            return

        paths = (
            py311.relative_fix((subdir / name).resolve())
            .relative_to(self.locate_file('').resolve(), walk_up=True)
            .as_posix()
            for name in text.splitlines()
        )
        return map('"{}"'.format, paths)

    def _read_files_egginfo_sources(self):
        """
        Read SOURCES.txt and return lines in a similar CSV-parsable
        format as RECORD: each file name must be quoted (since it
        might contain literal commas).

        Note that SOURCES.txt is not a reliable source for what
        files are installed by a package. This file is generated
        for a source archive, and the files that are present
        there (e.g. setup.py) may not correctly reflect the files
        that are present after the package has been installed.
        """
        text = self.read_text('SOURCES.txt')
        return text and map('"{}"'.format, text.splitlines())

    @property
    def requires(self) -> list[str] | None:
        """Generated requirements specified for this Distribution"""
        reqs = self._read_dist_info_reqs() or self._read_egg_info_reqs()
        return reqs and list(reqs)

    def _read_dist_info_reqs(self):
        return self.metadata.get_all('Requires-Dist')

    def _read_egg_info_reqs(self):
        source = self.read_text('requires.txt')
        return pass_none(self._deps_from_requires_text)(source)

    @classmethod
    def _deps_from_requires_text(cls, source):
        return cls._convert_egg_info_reqs_to_simple_reqs(Sectioned.read(source))

    @staticmethod
    def _convert_egg_info_reqs_to_simple_reqs(sections):
        """
        Historically, setuptools would solicit and store 'extra'
        requirements, including those with environment markers,
        in separate sections. More modern tools expect each
        dependency to be defined separately, with any relevant
        extras and environment markers attached directly to that
        requirement. This method converts the former to the
        latter. See _test_deps_from_requires_text for an example.
        """

        def make_condition(name):
            return name and f'extra == "{name}"'

        def quoted_marker(section):
            section = section or ''
            extra, sep, markers = section.partition(':')
            if extra and markers:
                markers = f'({markers})'
            conditions = list(filter(None, [markers, make_condition(extra)]))
            return '; ' + ' and '.join(conditions) if conditions else ''

        def url_req_space(req):
            """
            PEP 508 requires a space between the url_spec and the quoted_marker.
            Ref python/importlib_metadata#357.
            """
            # '@' is uniquely indicative of a url_req.
            return ' ' * ('@' in req)

        for section in sections:
            space = url_req_space(section.value)
            yield section.value + space + quoted_marker(section.name)

    @property
    def origin(self):
        return self._load_json('direct_url.json')

    def _load_json(self, filename):
        # Deferred for performance (python/importlib_metadata#503)
        import json

        return pass_none(json.loads)(
            self.read_text(filename),
            object_hook=lambda data: types.SimpleNamespace(**data),
        )


class DistributionFinder(MetaPathFinder):
    """
    A MetaPathFinder capable of discovering installed distributions.

    Custom providers should implement this interface in order to
    supply metadata.
    """

    class Context:
        """
        Keyword arguments presented by the caller to
        ``distributions()`` or ``Distribution.discover()``
        to narrow the scope of a search for distributions
        in all DistributionFinders.

        Each DistributionFinder may expect any parameters
        and should attempt to honor the canonical
        parameters defined below when appropriate.

        This mechanism gives a custom provider a means to
        solicit additional details from the caller beyond
        "name" and "path" when searching distributions.
        For example, imagine a provider that exposes suites
        of packages in either a "public" or "private" ``realm``.
        A caller may wish to query only for distributions in
        a particular realm and could call
        ``distributions(realm="private")`` to signal to the
        custom provider to only include distributions from that
        realm.
        """

        name = None
        """
        Specific name for which a distribution finder should match.
        A name of ``None`` matches all distributions.
        """

        def __init__(self, **kwargs):
            vars(self).update(kwargs)

        @property
        def path(self) -> list[str]:
            """
            The sequence of directory path that a distribution finder
            should search.

            Typically refers to Python installed package paths such as
            "site-packages" directories and defaults to ``sys.path``.
            """
            return vars(self).get('path', sys.path)

    @abc.abstractmethod
    def find_distributions(self, context=Context()) -> Iterable[Distribution]:
        """
        Find distributions.

        Return an iterable of all Distribution instances capable of
        loading the metadata for packages matching the ``context``,
        a DistributionFinder.Context instance.
        """


class FastPath:
    """
    Micro-optimized class for searching a root for children.

    Root is a path on the file system that may contain metadata
    directories either as natural directories or within a zip file.

    >>> FastPath('').children()
    ['...']

    FastPath objects are cached and recycled for any given root.

    >>> FastPath('foobar') is FastPath('foobar')
    True
    """

    @functools.lru_cache()  # type: ignore[misc]
    def __new__(cls, root):
        return super().__new__(cls)

    def __init__(self, root):
        self.root = root

    def joinpath(self, child):
        return pathlib.Path(self.root, child)

    def children(self):
        with suppress(Exception):
            return os.listdir(self.root or '.')
        with suppress(Exception):
            return self.zip_children()
        return []

    def zip_children(self):
        # deferred for performance (python/importlib_metadata#502)
        from zipp.compat.overlay import zipfile

        zip_path = zipfile.Path(self.root)
        names = zip_path.root.namelist()
        self.joinpath = zip_path.joinpath

        return dict.fromkeys(child.split(posixpath.sep, 1)[0] for child in names)

    def search(self, name):
        return self.lookup(self.mtime).search(name)

    @property
    def mtime(self):
        with suppress(OSError):
            return os.stat(self.root).st_mtime
        self.lookup.cache_clear()

    @method_cache
    def lookup(self, mtime):
        return Lookup(self)


class Lookup:
    """
    A micro-optimized class for searching a (fast) path for metadata.
    """

    def __init__(self, path: FastPath):
        """
        Calculate all of the children representing metadata.

        From the children in the path, calculate early all of the
        children that appear to represent metadata (infos) or legacy
        metadata (eggs).
        """

        base = os.path.basename(path.root).lower()
        base_is_egg = base.endswith(".egg")
        self.infos = FreezableDefaultDict(list)
        self.eggs = FreezableDefaultDict(list)

        for child in path.children():
            low = child.lower()
            if low.endswith((".dist-info", ".egg-info")):
                # rpartition is faster than splitext and suitable for this purpose.
                name = low.rpartition(".")[0].partition("-")[0]
                normalized = Prepared.normalize(name)
                self.infos[normalized].append(path.joinpath(child))
            elif base_is_egg and low == "egg-info":
                name = base.rpartition(".")[0].partition("-")[0]
                legacy_normalized = Prepared.legacy_normalize(name)
                self.eggs[legacy_normalized].append(path.joinpath(child))

        self.infos.freeze()
        self.eggs.freeze()

    def search(self, prepared: Prepared):
        """
        Yield all infos and eggs matching the Prepared query.
        """
        infos = (
            self.infos[prepared.normalized]
            if prepared
            else itertools.chain.from_iterable(self.infos.values())
        )
        eggs = (
            self.eggs[prepared.legacy_normalized]
            if prepared
            else itertools.chain.from_iterable(self.eggs.values())
        )
        return itertools.chain(infos, eggs)


class Prepared:
    """
    A prepared search query for metadata on a possibly-named package.

    Pre-calculates the normalization to prevent repeated operations.

    >>> none = Prepared(None)
    >>> none.normalized
    >>> none.legacy_normalized
    >>> bool(none)
    False
    >>> sample = Prepared('Sample__Pkg-name.foo')
    >>> sample.normalized
    'sample_pkg_name_foo'
    >>> sample.legacy_normalized
    'sample__pkg_name.foo'
    >>> bool(sample)
    True
    """

    normalized = None
    legacy_normalized = None

    def __init__(self, name: str | None):
        self.name = name
        if name is None:
            return
        self.normalized = self.normalize(name)
        self.legacy_normalized = self.legacy_normalize(name)

    @staticmethod
    def normalize(name):
        """
        PEP 503 normalization plus dashes as underscores.
        """
        return re.sub(r"[-_.]+", "-", name).lower().replace('-', '_')

    @staticmethod
    def legacy_normalize(name):
        """
        Normalize the package name as found in the convention in
        older packaging tools versions and specs.
        """
        return name.lower().replace('-', '_')

    def __bool__(self):
        return bool(self.name)


@install
class MetadataPathFinder(NullFinder, DistributionFinder):
    """A degenerate finder for distribution packages on the file system.

    This finder supplies only a find_distributions() method for versions
    of Python that do not have a PathFinder find_distributions().
    """

    @classmethod
    def find_distributions(
        cls, context=DistributionFinder.Context()
    ) -> Iterable[PathDistribution]:
        """
        Find distributions.

        Return an iterable of all Distribution instances capable of
        loading the metadata for packages matching ``context.name``
        (or all names if ``None`` indicated) along the paths in the list
        of directories ``context.path``.
        """
        found = cls._search_paths(context.name, context.path)
        return map(PathDistribution, found)

    @classmethod
    def _search_paths(cls, name, paths):
        """Find metadata directories in paths heuristically."""
        prepared = Prepared(name)
        return itertools.chain.from_iterable(
            path.search(prepared) for path in map(FastPath, paths)
        )

    @classmethod
    def invalidate_caches(cls) -> None:
        FastPath.__new__.cache_clear()


class PathDistribution(Distribution):
    def __init__(self, path: SimplePath) -> None:
        """Construct a distribution.

        :param path: SimplePath indicating the metadata directory.
        """
        self._path = path

    def read_text(self, filename: str | os.PathLike[str]) -> str | None:
        with suppress(
            FileNotFoundError,
            IsADirectoryError,
            KeyError,
            NotADirectoryError,
            PermissionError,
        ):
            return self._path.joinpath(filename).read_text(encoding='utf-8')

        return None

    read_text.__doc__ = Distribution.read_text.__doc__

    def locate_file(self, path: str | os.PathLike[str]) -> SimplePath:
        return self._path.parent / path

    @property
    def _normalized_name(self):
        """
        Performance optimization: where possible, resolve the
        normalized name from the file system path.
        """
        stem = os.path.basename(str(self._path))
        return (
            pass_none(Prepared.normalize)(self._name_from_stem(stem))
            or super()._normalized_name
        )

    @staticmethod
    def _name_from_stem(stem):
        """
        >>> PathDistribution._name_from_stem('foo-3.0.egg-info')
        'foo'
        >>> PathDistribution._name_from_stem('CherryPy-3.0.dist-info')
        'CherryPy'
        >>> PathDistribution._name_from_stem('face.egg-info')
        'face'
        >>> PathDistribution._name_from_stem('foo.bar')
        """
        filename, ext = os.path.splitext(stem)
        if ext not in ('.dist-info', '.egg-info'):
            return
        name, sep, rest = filename.partition('-')
        return name


def distribution(distribution_name: str) -> Distribution:
    """Get the ``Distribution`` instance for the named package.

    :param distribution_name: The name of the distribution package as a string.
    :return: A ``Distribution`` instance (or subclass thereof).
    """
    return Distribution.from_name(distribution_name)


def distributions(**kwargs) -> Iterable[Distribution]:
    """Get all ``Distribution`` instances in the current environment.

    :return: An iterable of ``Distribution`` instances.
    """
    return Distribution.discover(**kwargs)


def metadata(distribution_name: str) -> _meta.PackageMetadata | None:
    """Get the metadata for the named package.

    :param distribution_name: The name of the distribution package to query.
    :return: A PackageMetadata containing the parsed metadata.
    """
    return Distribution.from_name(distribution_name).metadata


def version(distribution_name: str) -> str:
    """Get the version string for the named package.

    :param distribution_name: The name of the distribution package to query.
    :return: The version string for the package as defined in the package's
        "Version" metadata key.
    """
    return distribution(distribution_name).version


_unique = functools.partial(
    unique_everseen,
    key=py39.normalized_name,
)
"""
Wrapper for ``distributions`` to return unique distributions by name.
"""


def entry_points(**params) -> EntryPoints:
    """Return EntryPoint objects for all installed packages.

    Pass selection parameters (group or name) to filter the
    result to entry points matching those properties (see
    EntryPoints.select()).

    :return: EntryPoints for all installed packages.
    """
    eps = itertools.chain.from_iterable(
        dist.entry_points for dist in _unique(distributions())
    )
    return EntryPoints(eps).select(**params)


def files(distribution_name: str) -> list[PackagePath] | None:
    """Return a list of files for the named package.

    :param distribution_name: The name of the distribution package to query.
    :return: List of files composing the distribution.
    """
    return distribution(distribution_name).files


def requires(distribution_name: str) -> list[str] | None:
    """
    Return a list of requirements for the named package.

    :return: An iterable of requirements, suitable for
        packaging.requirement.Requirement.
    """
    return distribution(distribution_name).requires


def packages_distributions() -> Mapping[str, list[str]]:
    """
    Return a mapping of top-level packages to their
    distributions.

    >>> import collections.abc
    >>> pkgs = packages_distributions()
    >>> all(isinstance(dist, collections.abc.Sequence) for dist in pkgs.values())
    True
    """
    pkg_to_dist = collections.defaultdict(list)
    for dist in distributions():
        for pkg in _top_level_declared(dist) or _top_level_inferred(dist):
            pkg_to_dist[pkg].append(md_none(dist.metadata)['Name'])
    return dict(pkg_to_dist)


def _top_level_declared(dist):
    return (dist.read_text('top_level.txt') or '').split()


def _topmost(name: PackagePath) -> str | None:
    """
    Return the top-most parent as long as there is a parent.
    """
    top, *rest = name.parts
    return top if rest else None


def _get_toplevel_name(name: PackagePath) -> str:
    """
    Infer a possibly importable module name from a name presumed on
    sys.path.

    >>> _get_toplevel_name(PackagePath('foo.py'))
    'foo'
    >>> _get_toplevel_name(PackagePath('foo'))
    'foo'
    >>> _get_toplevel_name(PackagePath('foo.pyc'))
    'foo'
    >>> _get_toplevel_name(PackagePath('foo/__init__.py'))
    'foo'
    >>> _get_toplevel_name(PackagePath('foo.pth'))
    'foo.pth'
    >>> _get_toplevel_name(PackagePath('foo.dist-info'))
    'foo.dist-info'
    """
    # Defer import of inspect for performance (python/cpython#118761)
    import inspect

    return _topmost(name) or inspect.getmodulename(name) or str(name)


def _top_level_inferred(dist):
    opt_names = set(map(_get_toplevel_name, always_iterable(dist.files)))

    def importable_name(name):
        return '.' not in name

    return filter(importable_name, opt_names)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\generative_service.py ===
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

from google.ai.generativelanguage_v1beta.types import citation
from google.ai.generativelanguage_v1beta.types import content as gag_content
from google.ai.generativelanguage_v1beta.types import retriever, safety

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "TaskType",
        "GenerateContentRequest",
        "GenerationConfig",
        "SemanticRetrieverConfig",
        "GenerateContentResponse",
        "Candidate",
        "AttributionSourceId",
        "GroundingAttribution",
        "GenerateAnswerRequest",
        "GenerateAnswerResponse",
        "EmbedContentRequest",
        "ContentEmbedding",
        "EmbedContentResponse",
        "BatchEmbedContentsRequest",
        "BatchEmbedContentsResponse",
        "CountTokensRequest",
        "CountTokensResponse",
    },
)


class TaskType(proto.Enum):
    r"""Type of task for which the embedding will be used.

    Values:
        TASK_TYPE_UNSPECIFIED (0):
            Unset value, which will default to one of the
            other enum values.
        RETRIEVAL_QUERY (1):
            Specifies the given text is a query in a
            search/retrieval setting.
        RETRIEVAL_DOCUMENT (2):
            Specifies the given text is a document from
            the corpus being searched.
        SEMANTIC_SIMILARITY (3):
            Specifies the given text will be used for
            STS.
        CLASSIFICATION (4):
            Specifies that the given text will be
            classified.
        CLUSTERING (5):
            Specifies that the embeddings will be used
            for clustering.
        QUESTION_ANSWERING (6):
            Specifies that the given text will be used
            for question answering.
        FACT_VERIFICATION (7):
            Specifies that the given text will be used
            for fact verification.
    """
    TASK_TYPE_UNSPECIFIED = 0
    RETRIEVAL_QUERY = 1
    RETRIEVAL_DOCUMENT = 2
    SEMANTIC_SIMILARITY = 3
    CLASSIFICATION = 4
    CLUSTERING = 5
    QUESTION_ANSWERING = 6
    FACT_VERIFICATION = 7


class GenerateContentRequest(proto.Message):
    r"""Request to generate a completion from the model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        model (str):
            Required. The name of the ``Model`` to use for generating
            the completion.

            Format: ``name=models/{model}``.
        system_instruction (google.ai.generativelanguage_v1beta.types.Content):
            Optional. Developer set system instruction.
            Currently, text only.

            This field is a member of `oneof`_ ``_system_instruction``.
        contents (MutableSequence[google.ai.generativelanguage_v1beta.types.Content]):
            Required. The content of the current
            conversation with the model.
            For single-turn queries, this is a single
            instance. For multi-turn queries, this is a
            repeated field that contains conversation
            history + latest request.
        tools (MutableSequence[google.ai.generativelanguage_v1beta.types.Tool]):
            Optional. A list of ``Tools`` the model may use to generate
            the next response.

            A ``Tool`` is a piece of code that enables the system to
            interact with external systems to perform an action, or set
            of actions, outside of knowledge and scope of the model. The
            only supported tool is currently ``Function``.
        tool_config (google.ai.generativelanguage_v1beta.types.ToolConfig):
            Optional. Tool configuration for any ``Tool`` specified in
            the request.
        safety_settings (MutableSequence[google.ai.generativelanguage_v1beta.types.SafetySetting]):
            Optional. A list of unique ``SafetySetting`` instances for
            blocking unsafe content.

            This will be enforced on the
            ``GenerateContentRequest.contents`` and
            ``GenerateContentResponse.candidates``. There should not be
            more than one setting for each ``SafetyCategory`` type. The
            API will block any contents and responses that fail to meet
            the thresholds set by these settings. This list overrides
            the default settings for each ``SafetyCategory`` specified
            in the safety_settings. If there is no ``SafetySetting`` for
            a given ``SafetyCategory`` provided in the list, the API
            will use the default safety setting for that category. Harm
            categories HARM_CATEGORY_HATE_SPEECH,
            HARM_CATEGORY_SEXUALLY_EXPLICIT,
            HARM_CATEGORY_DANGEROUS_CONTENT, HARM_CATEGORY_HARASSMENT
            are supported.
        generation_config (google.ai.generativelanguage_v1beta.types.GenerationConfig):
            Optional. Configuration options for model
            generation and outputs.

            This field is a member of `oneof`_ ``_generation_config``.
        cached_content (str):
            Optional. The name of the cached content used as context to
            serve the prediction. Note: only used in explicit caching,
            where users can have control over caching (e.g. what content
            to cache) and enjoy guaranteed cost savings. Format:
            ``cachedContents/{cachedContent}``

            This field is a member of `oneof`_ ``_cached_content``.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    system_instruction: gag_content.Content = proto.Field(
        proto.MESSAGE,
        number=8,
        optional=True,
        message=gag_content.Content,
    )
    contents: MutableSequence[gag_content.Content] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=gag_content.Content,
    )
    tools: MutableSequence[gag_content.Tool] = proto.RepeatedField(
        proto.MESSAGE,
        number=5,
        message=gag_content.Tool,
    )
    tool_config: gag_content.ToolConfig = proto.Field(
        proto.MESSAGE,
        number=7,
        message=gag_content.ToolConfig,
    )
    safety_settings: MutableSequence[safety.SafetySetting] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message=safety.SafetySetting,
    )
    generation_config: "GenerationConfig" = proto.Field(
        proto.MESSAGE,
        number=4,
        optional=True,
        message="GenerationConfig",
    )
    cached_content: str = proto.Field(
        proto.STRING,
        number=9,
        optional=True,
    )


class GenerationConfig(proto.Message):
    r"""Configuration options for model generation and outputs. Not
    all parameters may be configurable for every model.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        candidate_count (int):
            Optional. Number of generated responses to
            return.
            Currently, this value can only be set to 1. If
            unset, this will default to 1.

            This field is a member of `oneof`_ ``_candidate_count``.
        stop_sequences (MutableSequence[str]):
            Optional. The set of character sequences (up
            to 5) that will stop output generation. If
            specified, the API will stop at the first
            appearance of a stop sequence. The stop sequence
            will not be included as part of the response.
        max_output_tokens (int):
            Optional. The maximum number of tokens to include in a
            candidate.

            Note: The default value varies by model, see the
            ``Model.output_token_limit`` attribute of the ``Model``
            returned from the ``getModel`` function.

            This field is a member of `oneof`_ ``_max_output_tokens``.
        temperature (float):
            Optional. Controls the randomness of the output.

            Note: The default value varies by model, see the
            ``Model.temperature`` attribute of the ``Model`` returned
            from the ``getModel`` function.

            Values can range from [0.0, 2.0].

            This field is a member of `oneof`_ ``_temperature``.
        top_p (float):
            Optional. The maximum cumulative probability of tokens to
            consider when sampling.

            The model uses combined Top-k and nucleus sampling.

            Tokens are sorted based on their assigned probabilities so
            that only the most likely tokens are considered. Top-k
            sampling directly limits the maximum number of tokens to
            consider, while Nucleus sampling limits number of tokens
            based on the cumulative probability.

            Note: The default value varies by model, see the
            ``Model.top_p`` attribute of the ``Model`` returned from the
            ``getModel`` function.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            Optional. The maximum number of tokens to consider when
            sampling.

            Models use nucleus sampling or combined Top-k and nucleus
            sampling. Top-k sampling considers the set of ``top_k`` most
            probable tokens. Models running with nucleus sampling don't
            allow top_k setting.

            Note: The default value varies by model, see the
            ``Model.top_k`` attribute of the ``Model`` returned from the
            ``getModel`` function. Empty ``top_k`` field in ``Model``
            indicates the model doesn't apply top-k sampling and doesn't
            allow setting ``top_k`` on requests.

            This field is a member of `oneof`_ ``_top_k``.
        response_mime_type (str):
            Optional. Output response mimetype of the generated
            candidate text. Supported mimetype: ``text/plain``:
            (default) Text output. ``application/json``: JSON response
            in the candidates.
        response_schema (google.ai.generativelanguage_v1beta.types.Schema):
            Optional. Output response schema of the generated candidate
            text when response mime type can have schema. Schema can be
            objects, primitives or arrays and is a subset of `OpenAPI
            schema <https://spec.openapis.org/oas/v3.0.3#schema>`__.

            If set, a compatible response_mime_type must also be set.
            Compatible mimetypes: ``application/json``: Schema for JSON
            response.
    """

    candidate_count: int = proto.Field(
        proto.INT32,
        number=1,
        optional=True,
    )
    stop_sequences: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=2,
    )
    max_output_tokens: int = proto.Field(
        proto.INT32,
        number=4,
        optional=True,
    )
    temperature: float = proto.Field(
        proto.FLOAT,
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
    response_mime_type: str = proto.Field(
        proto.STRING,
        number=13,
    )
    response_schema: gag_content.Schema = proto.Field(
        proto.MESSAGE,
        number=14,
        message=gag_content.Schema,
    )


class SemanticRetrieverConfig(proto.Message):
    r"""Configuration for retrieving grounding content from a ``Corpus`` or
    ``Document`` created using the Semantic Retriever API.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        source (str):
            Required. Name of the resource for retrieval,
            e.g. corpora/123 or corpora/123/documents/abc.
        query (google.ai.generativelanguage_v1beta.types.Content):
            Required. Query to use for similarity matching ``Chunk``\ s
            in the given resource.
        metadata_filters (MutableSequence[google.ai.generativelanguage_v1beta.types.MetadataFilter]):
            Optional. Filters for selecting ``Document``\ s and/or
            ``Chunk``\ s from the resource.
        max_chunks_count (int):
            Optional. Maximum number of relevant ``Chunk``\ s to
            retrieve.

            This field is a member of `oneof`_ ``_max_chunks_count``.
        minimum_relevance_score (float):
            Optional. Minimum relevance score for retrieved relevant
            ``Chunk``\ s.

            This field is a member of `oneof`_ ``_minimum_relevance_score``.
    """

    source: str = proto.Field(
        proto.STRING,
        number=1,
    )
    query: gag_content.Content = proto.Field(
        proto.MESSAGE,
        number=2,
        message=gag_content.Content,
    )
    metadata_filters: MutableSequence[retriever.MetadataFilter] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message=retriever.MetadataFilter,
    )
    max_chunks_count: int = proto.Field(
        proto.INT32,
        number=4,
        optional=True,
    )
    minimum_relevance_score: float = proto.Field(
        proto.FLOAT,
        number=5,
        optional=True,
    )


class GenerateContentResponse(proto.Message):
    r"""Response from the model supporting multiple candidates.

    Note on safety ratings and content filtering. They are reported for
    both prompt in ``GenerateContentResponse.prompt_feedback`` and for
    each candidate in ``finish_reason`` and in ``safety_ratings``. The
    API contract is that:

    -  either all requested candidates are returned or no candidates at
       all
    -  no candidates are returned only if there was something wrong with
       the prompt (see ``prompt_feedback``)
    -  feedback on each candidate is reported on ``finish_reason`` and
       ``safety_ratings``.

    Attributes:
        candidates (MutableSequence[google.ai.generativelanguage_v1beta.types.Candidate]):
            Candidate responses from the model.
        prompt_feedback (google.ai.generativelanguage_v1beta.types.GenerateContentResponse.PromptFeedback):
            Returns the prompt's feedback related to the
            content filters.
        usage_metadata (google.ai.generativelanguage_v1beta.types.GenerateContentResponse.UsageMetadata):
            Output only. Metadata on the generation
            requests' token usage.
    """

    class PromptFeedback(proto.Message):
        r"""A set of the feedback metadata the prompt specified in
        ``GenerateContentRequest.content``.

        Attributes:
            block_reason (google.ai.generativelanguage_v1beta.types.GenerateContentResponse.PromptFeedback.BlockReason):
                Optional. If set, the prompt was blocked and
                no candidates are returned. Rephrase your
                prompt.
            safety_ratings (MutableSequence[google.ai.generativelanguage_v1beta.types.SafetyRating]):
                Ratings for safety of the prompt.
                There is at most one rating per category.
        """

        class BlockReason(proto.Enum):
            r"""Specifies what was the reason why prompt was blocked.

            Values:
                BLOCK_REASON_UNSPECIFIED (0):
                    Default value. This value is unused.
                SAFETY (1):
                    Prompt was blocked due to safety reasons. You can inspect
                    ``safety_ratings`` to understand which safety category
                    blocked it.
                OTHER (2):
                    Prompt was blocked due to unknown reasons.
            """
            BLOCK_REASON_UNSPECIFIED = 0
            SAFETY = 1
            OTHER = 2

        block_reason: "GenerateContentResponse.PromptFeedback.BlockReason" = (
            proto.Field(
                proto.ENUM,
                number=1,
                enum="GenerateContentResponse.PromptFeedback.BlockReason",
            )
        )
        safety_ratings: MutableSequence[safety.SafetyRating] = proto.RepeatedField(
            proto.MESSAGE,
            number=2,
            message=safety.SafetyRating,
        )

    class UsageMetadata(proto.Message):
        r"""Metadata on the generation request's token usage.

        Attributes:
            prompt_token_count (int):
                Number of tokens in the prompt. When cached_content is set,
                this is still the total effective prompt size. I.e. this
                includes the number of tokens in the cached content.
            cached_content_token_count (int):
                Number of tokens in the cached part of the
                prompt, i.e. in the cached content.
            candidates_token_count (int):
                Total number of tokens across the generated
                candidates.
            total_token_count (int):
                Total token count for the generation request
                (prompt + candidates).
        """

        prompt_token_count: int = proto.Field(
            proto.INT32,
            number=1,
        )
        cached_content_token_count: int = proto.Field(
            proto.INT32,
            number=4,
        )
        candidates_token_count: int = proto.Field(
            proto.INT32,
            number=2,
        )
        total_token_count: int = proto.Field(
            proto.INT32,
            number=3,
        )

    candidates: MutableSequence["Candidate"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="Candidate",
    )
    prompt_feedback: PromptFeedback = proto.Field(
        proto.MESSAGE,
        number=2,
        message=PromptFeedback,
    )
    usage_metadata: UsageMetadata = proto.Field(
        proto.MESSAGE,
        number=3,
        message=UsageMetadata,
    )


class Candidate(proto.Message):
    r"""A response candidate generated from the model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        index (int):
            Output only. Index of the candidate in the
            list of candidates.

            This field is a member of `oneof`_ ``_index``.
        content (google.ai.generativelanguage_v1beta.types.Content):
            Output only. Generated content returned from
            the model.
        finish_reason (google.ai.generativelanguage_v1beta.types.Candidate.FinishReason):
            Optional. Output only. The reason why the
            model stopped generating tokens.
            If empty, the model has not stopped generating
            the tokens.
        safety_ratings (MutableSequence[google.ai.generativelanguage_v1beta.types.SafetyRating]):
            List of ratings for the safety of a response
            candidate.
            There is at most one rating per category.
        citation_metadata (google.ai.generativelanguage_v1beta.types.CitationMetadata):
            Output only. Citation information for model-generated
            candidate.

            This field may be populated with recitation information for
            any text included in the ``content``. These are passages
            that are "recited" from copyrighted material in the
            foundational LLM's training data.
        token_count (int):
            Output only. Token count for this candidate.
        grounding_attributions (MutableSequence[google.ai.generativelanguage_v1beta.types.GroundingAttribution]):
            Output only. Attribution information for sources that
            contributed to a grounded answer.

            This field is populated for ``GenerateAnswer`` calls.
    """

    class FinishReason(proto.Enum):
        r"""Defines the reason why the model stopped generating tokens.

        Values:
            FINISH_REASON_UNSPECIFIED (0):
                Default value. This value is unused.
            STOP (1):
                Natural stop point of the model or provided
                stop sequence.
            MAX_TOKENS (2):
                The maximum number of tokens as specified in
                the request was reached.
            SAFETY (3):
                The candidate content was flagged for safety
                reasons.
            RECITATION (4):
                The candidate content was flagged for
                recitation reasons.
            OTHER (5):
                Unknown reason.
        """
        FINISH_REASON_UNSPECIFIED = 0
        STOP = 1
        MAX_TOKENS = 2
        SAFETY = 3
        RECITATION = 4
        OTHER = 5

    index: int = proto.Field(
        proto.INT32,
        number=3,
        optional=True,
    )
    content: gag_content.Content = proto.Field(
        proto.MESSAGE,
        number=1,
        message=gag_content.Content,
    )
    finish_reason: FinishReason = proto.Field(
        proto.ENUM,
        number=2,
        enum=FinishReason,
    )
    safety_ratings: MutableSequence[safety.SafetyRating] = proto.RepeatedField(
        proto.MESSAGE,
        number=5,
        message=safety.SafetyRating,
    )
    citation_metadata: citation.CitationMetadata = proto.Field(
        proto.MESSAGE,
        number=6,
        message=citation.CitationMetadata,
    )
    token_count: int = proto.Field(
        proto.INT32,
        number=7,
    )
    grounding_attributions: MutableSequence[
        "GroundingAttribution"
    ] = proto.RepeatedField(
        proto.MESSAGE,
        number=8,
        message="GroundingAttribution",
    )


class AttributionSourceId(proto.Message):
    r"""Identifier for the source contributing to this attribution.

    This message has `oneof`_ fields (mutually exclusive fields).
    For each oneof, at most one member field can be set at the same time.
    Setting any member of the oneof automatically clears all other
    members.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        grounding_passage (google.ai.generativelanguage_v1beta.types.AttributionSourceId.GroundingPassageId):
            Identifier for an inline passage.

            This field is a member of `oneof`_ ``source``.
        semantic_retriever_chunk (google.ai.generativelanguage_v1beta.types.AttributionSourceId.SemanticRetrieverChunk):
            Identifier for a ``Chunk`` fetched via Semantic Retriever.

            This field is a member of `oneof`_ ``source``.
    """

    class GroundingPassageId(proto.Message):
        r"""Identifier for a part within a ``GroundingPassage``.

        Attributes:
            passage_id (str):
                Output only. ID of the passage matching the
                ``GenerateAnswerRequest``'s ``GroundingPassage.id``.
            part_index (int):
                Output only. Index of the part within the
                ``GenerateAnswerRequest``'s ``GroundingPassage.content``.
        """

        passage_id: str = proto.Field(
            proto.STRING,
            number=1,
        )
        part_index: int = proto.Field(
            proto.INT32,
            number=2,
        )

    class SemanticRetrieverChunk(proto.Message):
        r"""Identifier for a ``Chunk`` retrieved via Semantic Retriever
        specified in the ``GenerateAnswerRequest`` using
        ``SemanticRetrieverConfig``.

        Attributes:
            source (str):
                Output only. Name of the source matching the request's
                ``SemanticRetrieverConfig.source``. Example: ``corpora/123``
                or ``corpora/123/documents/abc``
            chunk (str):
                Output only. Name of the ``Chunk`` containing the attributed
                text. Example: ``corpora/123/documents/abc/chunks/xyz``
        """

        source: str = proto.Field(
            proto.STRING,
            number=1,
        )
        chunk: str = proto.Field(
            proto.STRING,
            number=2,
        )

    grounding_passage: GroundingPassageId = proto.Field(
        proto.MESSAGE,
        number=1,
        oneof="source",
        message=GroundingPassageId,
    )
    semantic_retriever_chunk: SemanticRetrieverChunk = proto.Field(
        proto.MESSAGE,
        number=2,
        oneof="source",
        message=SemanticRetrieverChunk,
    )


class GroundingAttribution(proto.Message):
    r"""Attribution for a source that contributed to an answer.

    Attributes:
        source_id (google.ai.generativelanguage_v1beta.types.AttributionSourceId):
            Output only. Identifier for the source
            contributing to this attribution.
        content (google.ai.generativelanguage_v1beta.types.Content):
            Grounding source content that makes up this
            attribution.
    """

    source_id: "AttributionSourceId" = proto.Field(
        proto.MESSAGE,
        number=3,
        message="AttributionSourceId",
    )
    content: gag_content.Content = proto.Field(
        proto.MESSAGE,
        number=2,
        message=gag_content.Content,
    )


class GenerateAnswerRequest(proto.Message):
    r"""Request to generate a grounded answer from the model.

    This message has `oneof`_ fields (mutually exclusive fields).
    For each oneof, at most one member field can be set at the same time.
    Setting any member of the oneof automatically clears all other
    members.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        inline_passages (google.ai.generativelanguage_v1beta.types.GroundingPassages):
            Passages provided inline with the request.

            This field is a member of `oneof`_ ``grounding_source``.
        semantic_retriever (google.ai.generativelanguage_v1beta.types.SemanticRetrieverConfig):
            Content retrieved from resources created via
            the Semantic Retriever API.

            This field is a member of `oneof`_ ``grounding_source``.
        model (str):
            Required. The name of the ``Model`` to use for generating
            the grounded response.

            Format: ``model=models/{model}``.
        contents (MutableSequence[google.ai.generativelanguage_v1beta.types.Content]):
            Required. The content of the current conversation with the
            model. For single-turn queries, this is a single question to
            answer. For multi-turn queries, this is a repeated field
            that contains conversation history and the last ``Content``
            in the list containing the question.

            Note: GenerateAnswer currently only supports queries in
            English.
        answer_style (google.ai.generativelanguage_v1beta.types.GenerateAnswerRequest.AnswerStyle):
            Required. Style in which answers should be
            returned.
        safety_settings (MutableSequence[google.ai.generativelanguage_v1beta.types.SafetySetting]):
            Optional. A list of unique ``SafetySetting`` instances for
            blocking unsafe content.

            This will be enforced on the
            ``GenerateAnswerRequest.contents`` and
            ``GenerateAnswerResponse.candidate``. There should not be
            more than one setting for each ``SafetyCategory`` type. The
            API will block any contents and responses that fail to meet
            the thresholds set by these settings. This list overrides
            the default settings for each ``SafetyCategory`` specified
            in the safety_settings. If there is no ``SafetySetting`` for
            a given ``SafetyCategory`` provided in the list, the API
            will use the default safety setting for that category. Harm
            categories HARM_CATEGORY_HATE_SPEECH,
            HARM_CATEGORY_SEXUALLY_EXPLICIT,
            HARM_CATEGORY_DANGEROUS_CONTENT, HARM_CATEGORY_HARASSMENT
            are supported.
        temperature (float):
            Optional. Controls the randomness of the output.

            Values can range from [0.0,1.0], inclusive. A value closer
            to 1.0 will produce responses that are more varied and
            creative, while a value closer to 0.0 will typically result
            in more straightforward responses from the model. A low
            temperature (~0.2) is usually recommended for
            Attributed-Question-Answering use cases.

            This field is a member of `oneof`_ ``_temperature``.
    """

    class AnswerStyle(proto.Enum):
        r"""Style for grounded answers.

        Values:
            ANSWER_STYLE_UNSPECIFIED (0):
                Unspecified answer style.
            ABSTRACTIVE (1):
                Succint but abstract style.
            EXTRACTIVE (2):
                Very brief and extractive style.
            VERBOSE (3):
                Verbose style including extra details. The
                response may be formatted as a sentence,
                paragraph, multiple paragraphs, or bullet
                points, etc.
        """
        ANSWER_STYLE_UNSPECIFIED = 0
        ABSTRACTIVE = 1
        EXTRACTIVE = 2
        VERBOSE = 3

    inline_passages: gag_content.GroundingPassages = proto.Field(
        proto.MESSAGE,
        number=6,
        oneof="grounding_source",
        message=gag_content.GroundingPassages,
    )
    semantic_retriever: "SemanticRetrieverConfig" = proto.Field(
        proto.MESSAGE,
        number=7,
        oneof="grounding_source",
        message="SemanticRetrieverConfig",
    )
    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    contents: MutableSequence[gag_content.Content] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=gag_content.Content,
    )
    answer_style: AnswerStyle = proto.Field(
        proto.ENUM,
        number=5,
        enum=AnswerStyle,
    )
    safety_settings: MutableSequence[safety.SafetySetting] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message=safety.SafetySetting,
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=4,
        optional=True,
    )


class GenerateAnswerResponse(proto.Message):
    r"""Response from the model for a grounded answer.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        answer (google.ai.generativelanguage_v1beta.types.Candidate):
            Candidate answer from the model.

            Note: The model *always* attempts to provide a grounded
            answer, even when the answer is unlikely to be answerable
            from the given passages. In that case, a low-quality or
            ungrounded answer may be provided, along with a low
            ``answerable_probability``.
        answerable_probability (float):
            Output only. The model's estimate of the probability that
            its answer is correct and grounded in the input passages.

            A low answerable_probability indicates that the answer might
            not be grounded in the sources.

            When ``answerable_probability`` is low, some clients may
            wish to:

            -  Display a message to the effect of "We couldn’t answer
               that question" to the user.
            -  Fall back to a general-purpose LLM that answers the
               question from world knowledge. The threshold and nature
               of such fallbacks will depend on individual clients’ use
               cases. 0.5 is a good starting threshold.

            This field is a member of `oneof`_ ``_answerable_probability``.
        input_feedback (google.ai.generativelanguage_v1beta.types.GenerateAnswerResponse.InputFeedback):
            Output only. Feedback related to the input data used to
            answer the question, as opposed to model-generated response
            to the question.

            "Input data" can be one or more of the following:

            -  Question specified by the last entry in
               ``GenerateAnswerRequest.content``
            -  Conversation history specified by the other entries in
               ``GenerateAnswerRequest.content``
            -  Grounding sources
               (``GenerateAnswerRequest.semantic_retriever`` or
               ``GenerateAnswerRequest.inline_passages``)

            This field is a member of `oneof`_ ``_input_feedback``.
    """

    class InputFeedback(proto.Message):
        r"""Feedback related to the input data used to answer the
        question, as opposed to model-generated response to the
        question.


        .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

        Attributes:
            block_reason (google.ai.generativelanguage_v1beta.types.GenerateAnswerResponse.InputFeedback.BlockReason):
                Optional. If set, the input was blocked and
                no candidates are returned. Rephrase your input.

                This field is a member of `oneof`_ ``_block_reason``.
            safety_ratings (MutableSequence[google.ai.generativelanguage_v1beta.types.SafetyRating]):
                Ratings for safety of the input.
                There is at most one rating per category.
        """

        class BlockReason(proto.Enum):
            r"""Specifies what was the reason why input was blocked.

            Values:
                BLOCK_REASON_UNSPECIFIED (0):
                    Default value. This value is unused.
                SAFETY (1):
                    Input was blocked due to safety reasons. You can inspect
                    ``safety_ratings`` to understand which safety category
                    blocked it.
                OTHER (2):
                    Input was blocked due to other reasons.
            """
            BLOCK_REASON_UNSPECIFIED = 0
            SAFETY = 1
            OTHER = 2

        block_reason: "GenerateAnswerResponse.InputFeedback.BlockReason" = proto.Field(
            proto.ENUM,
            number=1,
            optional=True,
            enum="GenerateAnswerResponse.InputFeedback.BlockReason",
        )
        safety_ratings: MutableSequence[safety.SafetyRating] = proto.RepeatedField(
            proto.MESSAGE,
            number=2,
            message=safety.SafetyRating,
        )

    answer: "Candidate" = proto.Field(
        proto.MESSAGE,
        number=1,
        message="Candidate",
    )
    answerable_probability: float = proto.Field(
        proto.FLOAT,
        number=2,
        optional=True,
    )
    input_feedback: InputFeedback = proto.Field(
        proto.MESSAGE,
        number=3,
        optional=True,
        message=InputFeedback,
    )


class EmbedContentRequest(proto.Message):
    r"""Request containing the ``Content`` for the model to embed.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        content (google.ai.generativelanguage_v1beta.types.Content):
            Required. The content to embed. Only the ``parts.text``
            fields will be counted.
        task_type (google.ai.generativelanguage_v1beta.types.TaskType):
            Optional. Optional task type for which the embeddings will
            be used. Can only be set for ``models/embedding-001``.

            This field is a member of `oneof`_ ``_task_type``.
        title (str):
            Optional. An optional title for the text. Only applicable
            when TaskType is ``RETRIEVAL_DOCUMENT``.

            Note: Specifying a ``title`` for ``RETRIEVAL_DOCUMENT``
            provides better quality embeddings for retrieval.

            This field is a member of `oneof`_ ``_title``.
        output_dimensionality (int):
            Optional. Optional reduced dimension for the output
            embedding. If set, excessive values in the output embedding
            are truncated from the end. Supported by newer models since
            2024, and the earlier model (``models/embedding-001``)
            cannot specify this value.

            This field is a member of `oneof`_ ``_output_dimensionality``.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    content: gag_content.Content = proto.Field(
        proto.MESSAGE,
        number=2,
        message=gag_content.Content,
    )
    task_type: "TaskType" = proto.Field(
        proto.ENUM,
        number=3,
        optional=True,
        enum="TaskType",
    )
    title: str = proto.Field(
        proto.STRING,
        number=4,
        optional=True,
    )
    output_dimensionality: int = proto.Field(
        proto.INT32,
        number=5,
        optional=True,
    )


class ContentEmbedding(proto.Message):
    r"""A list of floats representing an embedding.

    Attributes:
        values (MutableSequence[float]):
            The embedding values.
    """

    values: MutableSequence[float] = proto.RepeatedField(
        proto.FLOAT,
        number=1,
    )


class EmbedContentResponse(proto.Message):
    r"""The response to an ``EmbedContentRequest``.

    Attributes:
        embedding (google.ai.generativelanguage_v1beta.types.ContentEmbedding):
            Output only. The embedding generated from the
            input content.
    """

    embedding: "ContentEmbedding" = proto.Field(
        proto.MESSAGE,
        number=1,
        message="ContentEmbedding",
    )


class BatchEmbedContentsRequest(proto.Message):
    r"""Batch request to get embeddings from the model for a list of
    prompts.

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        requests (MutableSequence[google.ai.generativelanguage_v1beta.types.EmbedContentRequest]):
            Required. Embed requests for the batch. The model in each of
            these requests must match the model specified
            ``BatchEmbedContentsRequest.model``.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    requests: MutableSequence["EmbedContentRequest"] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message="EmbedContentRequest",
    )


class BatchEmbedContentsResponse(proto.Message):
    r"""The response to a ``BatchEmbedContentsRequest``.

    Attributes:
        embeddings (MutableSequence[google.ai.generativelanguage_v1beta.types.ContentEmbedding]):
            Output only. The embeddings for each request,
            in the same order as provided in the batch
            request.
    """

    embeddings: MutableSequence["ContentEmbedding"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="ContentEmbedding",
    )


class CountTokensRequest(proto.Message):
    r"""Counts the number of tokens in the ``prompt`` sent to a model.

    Models may tokenize text differently, so each model may return a
    different ``token_count``.

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        contents (MutableSequence[google.ai.generativelanguage_v1beta.types.Content]):
            Optional. The input given to the model as a prompt. This
            field is ignored when ``generate_content_request`` is set.
        generate_content_request (google.ai.generativelanguage_v1beta.types.GenerateContentRequest):
            Optional. The overall input given to the
            model. CountTokens will count prompt, function
            calling, etc.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    contents: MutableSequence[gag_content.Content] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=gag_content.Content,
    )
    generate_content_request: "GenerateContentRequest" = proto.Field(
        proto.MESSAGE,
        number=3,
        message="GenerateContentRequest",
    )


class CountTokensResponse(proto.Message):
    r"""A response from ``CountTokens``.

    It returns the model's ``token_count`` for the ``prompt``.

    Attributes:
        total_tokens (int):
            The number of tokens that the ``model`` tokenizes the
            ``prompt`` into.

            Always non-negative. When cached_content is set, this is
            still the total effective prompt size. I.e. this includes
            the number of tokens in the cached content.
        cached_content_token_count (int):
            Number of tokens in the cached part of the
            prompt, i.e. in the cached content.
    """

    total_tokens: int = proto.Field(
        proto.INT32,
        number=1,
    )
    cached_content_token_count: int = proto.Field(
        proto.INT32,
        number=5,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_mql_builtins.py ===
"""
    pygments.lexers._mql_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Builtins for the MqlLexer.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
types = (
    'AccountBalance',
    'AccountCompany',
    'AccountCredit',
    'AccountCurrency',
    'AccountEquity',
    'AccountFreeMarginCheck',
    'AccountFreeMarginMode',
    'AccountFreeMargin',
    'AccountInfoDouble',
    'AccountInfoInteger',
    'AccountInfoString',
    'AccountLeverage',
    'AccountMargin',
    'AccountName',
    'AccountNumber',
    'AccountProfit',
    'AccountServer',
    'AccountStopoutLevel',
    'AccountStopoutMode',
    'Alert',
    'ArrayBsearch',
    'ArrayCompare',
    'ArrayCopyRates',
    'ArrayCopySeries',
    'ArrayCopy',
    'ArrayDimension',
    'ArrayFill',
    'ArrayFree',
    'ArrayGetAsSeries',
    'ArrayInitialize',
    'ArrayIsDynamic',
    'ArrayIsSeries',
    'ArrayMaximum',
    'ArrayMinimum',
    'ArrayRange',
    'ArrayResize',
    'ArraySetAsSeries',
    'ArraySize',
    'ArraySort',
    'CharArrayToString',
    'CharToString',
    'CharToStr',
    'CheckPointer',
    'ColorToARGB',
    'ColorToString',
    'Comment',
    'CopyClose',
    'CopyHigh',
    'CopyLow',
    'CopyOpen',
    'CopyRates',
    'CopyRealVolume',
    'CopySpread',
    'CopyTickVolume',
    'CopyTime',
    'DayOfWeek',
    'DayOfYear',
    'Day',
    'DebugBreak',
    'Digits',
    'DoubleToString',
    'DoubleToStr',
    'EnumToString',
    'EventChartCustom',
    'EventKillTimer',
    'EventSetMillisecondTimer',
    'EventSetTimer',
    'ExpertRemove',
    'FileClose',
    'FileCopy',
    'FileDelete',
    'FileFindClose',
    'FileFindFirst',
    'FileFindNext',
    'FileFlush',
    'FileGetInteger',
    'FileIsEnding',
    'FileIsExist',
    'FileIsLineEnding',
    'FileMove',
    'FileOpenHistory',
    'FileOpen',
    'FileReadArray',
    'FileReadBool',
    'FileReadDatetime',
    'FileReadDouble',
    'FileReadFloat',
    'FileReadInteger',
    'FileReadLong',
    'FileReadNumber',
    'FileReadString',
    'FileReadStruct',
    'FileSeek',
    'FileSize',
    'FileTell',
    'FileWriteArray',
    'FileWriteDouble',
    'FileWriteFloat',
    'FileWriteInteger',
    'FileWriteLong',
    'FileWriteString',
    'FileWriteStruct',
    'FileWrite',
    'FolderClean',
    'FolderCreate',
    'FolderDelete',
    'GetLastError',
    'GetPointer',
    'GetTickCount',
    'GlobalVariableCheck',
    'GlobalVariableDel',
    'GlobalVariableGet',
    'GlobalVariableName',
    'GlobalVariableSetOnCondition',
    'GlobalVariableSet',
    'GlobalVariableTemp',
    'GlobalVariableTime',
    'GlobalVariablesDeleteAll',
    'GlobalVariablesFlush',
    'GlobalVariablesTotal',
    'HideTestIndicators',
    'Hour',
    'IndicatorBuffers',
    'IndicatorCounted',
    'IndicatorDigits',
    'IndicatorSetDouble',
    'IndicatorSetInteger',
    'IndicatorSetString',
    'IndicatorShortName',
    'IntegerToString',
    'IsConnected',
    'IsDemo',
    'IsDllsAllowed',
    'IsExpertEnabled',
    'IsLibrariesAllowed',
    'IsOptimization',
    'IsStopped',
    'IsTesting',
    'IsTradeAllowed',
    'IsTradeContextBusy',
    'IsVisualMode',
    'MQLInfoInteger',
    'MQLInfoString',
    'MarketInfo',
    'MathAbs',
    'MathArccos',
    'MathArcsin',
    'MathArctan',
    'MathCeil',
    'MathCos',
    'MathExp',
    'MathFloor',
    'MathIsValidNumber',
    'MathLog',
    'MathMax',
    'MathMin',
    'MathMod',
    'MathPow',
    'MathRand',
    'MathRound',
    'MathSin',
    'MathSqrt',
    'MathSrand',
    'MathTan',
    'MessageBox',
    'Minute',
    'Month',
    'NormalizeDouble',
    'ObjectCreate',
    'ObjectDelete',
    'ObjectDescription',
    'ObjectFind',
    'ObjectGetDouble',
    'ObjectGetFiboDescription',
    'ObjectGetInteger',
    'ObjectGetShiftByValue',
    'ObjectGetString',
    'ObjectGetTimeByValue',
    'ObjectGetValueByShift',
    'ObjectGetValueByTime',
    'ObjectGet',
    'ObjectMove',
    'ObjectName',
    'ObjectSetDouble',
    'ObjectSetFiboDescription',
    'ObjectSetInteger',
    'ObjectSetString',
    'ObjectSetText',
    'ObjectSet',
    'ObjectType',
    'ObjectsDeleteAll',
    'ObjectsTotal',
    'OrderCloseBy',
    'OrderClosePrice',
    'OrderCloseTime',
    'OrderClose',
    'OrderComment',
    'OrderCommission',
    'OrderDelete',
    'OrderExpiration',
    'OrderLots',
    'OrderMagicNumber',
    'OrderModify',
    'OrderOpenPrice',
    'OrderOpenTime',
    'OrderPrint',
    'OrderProfit',
    'OrderSelect',
    'OrderSend',
    'OrderStopLoss',
    'OrderSwap',
    'OrderSymbol',
    'OrderTakeProfit',
    'OrderTicket',
    'OrderType',
    'OrdersHistoryTotal',
    'OrdersTotal',
    'PeriodSeconds',
    'Period',
    'PlaySound',
    'Point',
    'PrintFormat',
    'Print',
    'RefreshRates',
    'ResetLastError',
    'ResourceCreate',
    'ResourceFree',
    'ResourceReadImage',
    'ResourceSave',
    'Seconds',
    'SendFTP',
    'SendMail',
    'SendNotification',
    'SeriesInfoInteger',
    'SetIndexArrow',
    'SetIndexBuffer',
    'SetIndexDrawBegin',
    'SetIndexEmptyValue',
    'SetIndexLabel',
    'SetIndexShift',
    'SetIndexStyle',
    'SetLevelStyle',
    'SetLevelValue',
    'ShortArrayToString',
    'ShortToString',
    'Sleep',
    'StrToDouble',
    'StrToInteger',
    'StrToTime',
    'StringAdd',
    'StringBufferLen',
    'StringCompare',
    'StringConcatenate',
    'StringFill',
    'StringFind',
    'StringFormat',
    'StringGetCharacter',
    'StringGetChar',
    'StringInit',
    'StringLen',
    'StringReplace',
    'StringSetCharacter',
    'StringSetChar',
    'StringSplit',
    'StringSubstr',
    'StringToCharArray',
    'StringToColor',
    'StringToDouble',
    'StringToInteger',
    'StringToLower',
    'StringToShortArray',
    'StringToTime',
    'StringToUpper',
    'StringTrimLeft',
    'StringTrimRight',
    'StructToTime',
    'SymbolInfoDouble',
    'SymbolInfoInteger',
    'SymbolInfoSessionQuote',
    'SymbolInfoSessionTrade',
    'SymbolInfoString',
    'SymbolInfoTick',
    'SymbolIsSynchronized',
    'SymbolName',
    'SymbolSelect',
    'SymbolsTotal',
    'Symbol',
    'TerminalClose',
    'TerminalCompany',
    'TerminalName',
    'TerminalPath',
    'TesterStatistics',
    'TextGetSize',
    'TextOut',
    'TextSetFont',
    'TimeCurrent',
    'TimeDayOfWeek',
    'TimeDayOfYear',
    'TimeDaylightSavings',
    'TimeDay',
    'TimeGMTOffset',
    'TimeGMT',
    'TimeHour',
    'TimeLocal',
    'TimeMinute',
    'TimeMonth',
    'TimeSeconds',
    'TimeToString',
    'TimeToStruct',
    'TimeToStr',
    'TimeTradeServer',
    'TimeYear',
    'UninitializeReason',
    'WindowBarsPerChart',
    'WindowExpertName',
    'WindowFind',
    'WindowFirstVisibleBar',
    'WindowHandle',
    'WindowIsVisible',
    'WindowOnDropped',
    'WindowPriceMax',
    'WindowPriceMin',
    'WindowPriceOnDropped',
    'WindowRedraw',
    'WindowScreenShot',
    'WindowTimeOnDropped',
    'WindowXOnDropped',
    'WindowYOnDropped',
    'WindowsTotal',
    'Year',
    'ZeroMemory',
    'iAC',
    'iADX',
    'iAD',
    'iAO',
    'iATR',
    'iAlligator',
    'iBWMFI',
    'iBandsOnArray',
    'iBands',
    'iBarShift',
    'iBars',
    'iBearsPower',
    'iBullsPower',
    'iCCIOnArray',
    'iCCI',
    'iClose',
    'iCustom',
    'iDeMarker',
    'iEnvelopesOnArray',
    'iEnvelopes',
    'iForce',
    'iFractals',
    'iGator',
    'iHighest',
    'iHigh',
    'iIchimoku',
    'iLowest',
    'iLow',
    'iMACD',
    'iMAOnArray',
    'iMA',
    'iMFI',
    'iMomentumOnArray',
    'iMomentum',
    'iOBV',
    'iOpen',
    'iOsMA',
    'iRSIOnArray',
    'iRSI',
    'iRVI',
    'iSAR',
    'iStdDevOnArray',
    'iStdDev',
    'iStochastic',
    'iTime',
    'iVolume',
    'iWPR',
)

constants = (
    'ACCOUNT_BALANCE',
    'ACCOUNT_COMPANY',
    'ACCOUNT_CREDIT',
    'ACCOUNT_CURRENCY',
    'ACCOUNT_EQUITY',
    'ACCOUNT_FREEMARGIN',
    'ACCOUNT_LEVERAGE',
    'ACCOUNT_LIMIT_ORDERS',
    'ACCOUNT_LOGIN',
    'ACCOUNT_MARGIN',
    'ACCOUNT_MARGIN_LEVEL',
    'ACCOUNT_MARGIN_SO_CALL',
    'ACCOUNT_MARGIN_SO_MODE',
    'ACCOUNT_MARGIN_SO_SO',
    'ACCOUNT_NAME',
    'ACCOUNT_PROFIT',
    'ACCOUNT_SERVER',
    'ACCOUNT_STOPOUT_MODE_MONEY',
    'ACCOUNT_STOPOUT_MODE_PERCENT',
    'ACCOUNT_TRADE_ALLOWED',
    'ACCOUNT_TRADE_EXPERT',
    'ACCOUNT_TRADE_MODE',
    'ACCOUNT_TRADE_MODE_CONTEST',
    'ACCOUNT_TRADE_MODE_DEMO',
    'ACCOUNT_TRADE_MODE_REAL',
    'ALIGN_CENTER',
    'ALIGN_LEFT',
    'ALIGN_RIGHT',
    'ANCHOR_BOTTOM',
    'ANCHOR_CENTER',
    'ANCHOR_LEFT',
    'ANCHOR_LEFT_LOWER',
    'ANCHOR_LEFT_UPPER',
    'ANCHOR_LOWER',
    'ANCHOR_RIGHT',
    'ANCHOR_RIGHT_LOWER',
    'ANCHOR_RIGHT_UPPER',
    'ANCHOR_TOP',
    'ANCHOR_UPPER',
    'BORDER_FLAT',
    'BORDER_RAISED',
    'BORDER_SUNKEN',
    'CHARTEVENT_CHART_CHANGE',
    'CHARTEVENT_CLICK',
    'CHARTEVENT_CUSTOM',
    'CHARTEVENT_CUSTOM_LAST',
    'CHARTEVENT_KEYDOWN',
    'CHARTEVENT_MOUSE_MOVE',
    'CHARTEVENT_OBJECT_CHANGE',
    'CHARTEVENT_OBJECT_CLICK',
    'CHARTEVENT_OBJECT_CREATE',
    'CHARTEVENT_OBJECT_DELETE',
    'CHARTEVENT_OBJECT_DRAG',
    'CHARTEVENT_OBJECT_ENDEDIT',
    'CHARTS_MAX',
    'CHART_AUTOSCROLL',
    'CHART_BARS',
    'CHART_BEGIN',
    'CHART_BRING_TO_TOP',
    'CHART_CANDLES',
    'CHART_COLOR_ASK',
    'CHART_COLOR_BACKGROUND',
    'CHART_COLOR_BID',
    'CHART_COLOR_CANDLE_BEAR',
    'CHART_COLOR_CANDLE_BULL',
    'CHART_COLOR_CHART_DOWN',
    'CHART_COLOR_CHART_LINE',
    'CHART_COLOR_CHART_UP',
    'CHART_COLOR_FOREGROUND',
    'CHART_COLOR_GRID',
    'CHART_COLOR_LAST',
    'CHART_COLOR_STOP_LEVEL',
    'CHART_COLOR_VOLUME',
    'CHART_COMMENT',
    'CHART_CURRENT_POS',
    'CHART_DRAG_TRADE_LEVELS',
    'CHART_END',
    'CHART_EVENT_MOUSE_MOVE',
    'CHART_EVENT_OBJECT_CREATE',
    'CHART_EVENT_OBJECT_DELETE',
    'CHART_FIRST_VISIBLE_BAR',
    'CHART_FIXED_MAX',
    'CHART_FIXED_MIN',
    'CHART_FIXED_POSITION',
    'CHART_FOREGROUND',
    'CHART_HEIGHT_IN_PIXELS',
    'CHART_IS_OBJECT',
    'CHART_LINE',
    'CHART_MODE',
    'CHART_MOUSE_SCROLL',
    'CHART_POINTS_PER_BAR',
    'CHART_PRICE_MAX',
    'CHART_PRICE_MIN',
    'CHART_SCALEFIX',
    'CHART_SCALEFIX_11',
    'CHART_SCALE',
    'CHART_SCALE_PT_PER_BAR',
    'CHART_SHIFT',
    'CHART_SHIFT_SIZE',
    'CHART_SHOW_ASK_LINE',
    'CHART_SHOW_BID_LINE',
    'CHART_SHOW_DATE_SCALE',
    'CHART_SHOW_GRID',
    'CHART_SHOW_LAST_LINE',
    'CHART_SHOW_OBJECT_DESCR',
    'CHART_SHOW_OHLC',
    'CHART_SHOW_PERIOD_SEP',
    'CHART_SHOW_PRICE_SCALE',
    'CHART_SHOW_TRADE_LEVELS',
    'CHART_SHOW_VOLUMES',
    'CHART_VISIBLE_BARS',
    'CHART_VOLUME_HIDE',
    'CHART_VOLUME_REAL',
    'CHART_VOLUME_TICK',
    'CHART_WIDTH_IN_BARS',
    'CHART_WIDTH_IN_PIXELS',
    'CHART_WINDOWS_TOTAL',
    'CHART_WINDOW_HANDLE',
    'CHART_WINDOW_IS_VISIBLE',
    'CHART_WINDOW_YDISTANCE',
    'CHAR_MAX',
    'CHAR_MIN',
    'CLR_NONE',
    'CORNER_LEFT_LOWER',
    'CORNER_LEFT_UPPER',
    'CORNER_RIGHT_LOWER',
    'CORNER_RIGHT_UPPER',
    'CP_ACP',
    'CP_MACCP',
    'CP_OEMCP',
    'CP_SYMBOL',
    'CP_THREAD_ACP',
    'CP_UTF7',
    'CP_UTF8',
    'DBL_DIG',
    'DBL_EPSILON',
    'DBL_MANT_DIG',
    'DBL_MAX',
    'DBL_MAX_10_EXP',
    'DBL_MAX_EXP',
    'DBL_MIN',
    'DBL_MIN_10_EXP',
    'DBL_MIN_EXP',
    'DRAW_ARROW',
    'DRAW_FILLING',
    'DRAW_HISTOGRAM',
    'DRAW_LINE',
    'DRAW_NONE',
    'DRAW_SECTION',
    'DRAW_ZIGZAG',
    'EMPTY',
    'EMPTY_VALUE',
    'ERR_ACCOUNT_DISABLED',
    'ERR_BROKER_BUSY',
    'ERR_COMMON_ERROR',
    'ERR_INVALID_ACCOUNT',
    'ERR_INVALID_PRICE',
    'ERR_INVALID_STOPS',
    'ERR_INVALID_TRADE_PARAMETERS',
    'ERR_INVALID_TRADE_VOLUME',
    'ERR_LONG_POSITIONS_ONLY_ALLOWED',
    'ERR_MALFUNCTIONAL_TRADE',
    'ERR_MARKET_CLOSED',
    'ERR_NOT_ENOUGH_MONEY',
    'ERR_NOT_ENOUGH_RIGHTS',
    'ERR_NO_CONNECTION',
    'ERR_NO_ERROR',
    'ERR_NO_RESULT',
    'ERR_OFF_QUOTES',
    'ERR_OLD_VERSION',
    'ERR_ORDER_LOCKED',
    'ERR_PRICE_CHANGED',
    'ERR_REQUOTE',
    'ERR_SERVER_BUSY',
    'ERR_TOO_FREQUENT_REQUESTS',
    'ERR_TOO_MANY_REQUESTS',
    'ERR_TRADE_CONTEXT_BUSY',
    'ERR_TRADE_DISABLED',
    'ERR_TRADE_EXPIRATION_DENIED',
    'ERR_TRADE_HEDGE_PROHIBITED',
    'ERR_TRADE_MODIFY_DENIED',
    'ERR_TRADE_PROHIBITED_BY_FIFO',
    'ERR_TRADE_TIMEOUT',
    'ERR_TRADE_TOO_MANY_ORDERS',
    'FILE_ACCESS_DATE',
    'FILE_ANSI',
    'FILE_BIN',
    'FILE_COMMON',
    'FILE_CREATE_DATE',
    'FILE_CSV',
    'FILE_END',
    'FILE_EXISTS',
    'FILE_IS_ANSI',
    'FILE_IS_BINARY',
    'FILE_IS_COMMON',
    'FILE_IS_CSV',
    'FILE_IS_READABLE',
    'FILE_IS_TEXT',
    'FILE_IS_WRITABLE',
    'FILE_LINE_END',
    'FILE_MODIFY_DATE',
    'FILE_POSITION',
    'FILE_READ',
    'FILE_REWRITE',
    'FILE_SHARE_READ',
    'FILE_SHARE_WRITE',
    'FILE_SIZE',
    'FILE_TXT',
    'FILE_UNICODE',
    'FILE_WRITE',
    'FLT_DIG',
    'FLT_EPSILON',
    'FLT_MANT_DIG',
    'FLT_MAX',
    'FLT_MAX_10_EXP',
    'FLT_MAX_EXP',
    'FLT_MIN',
    'FLT_MIN_10_EXP',
    'FLT_MIN_EXP',
    'FRIDAY',
    'GANN_DOWN_TREND',
    'GANN_UP_TREND',
    'IDABORT',
    'IDCANCEL',
    'IDCONTINUE',
    'IDIGNORE',
    'IDNO',
    'IDOK',
    'IDRETRY',
    'IDTRYAGAIN',
    'IDYES',
    'INDICATOR_CALCULATIONS',
    'INDICATOR_COLOR_INDEX',
    'INDICATOR_DATA',
    'INDICATOR_DIGITS',
    'INDICATOR_HEIGHT',
    'INDICATOR_LEVELCOLOR',
    'INDICATOR_LEVELSTYLE',
    'INDICATOR_LEVELS',
    'INDICATOR_LEVELTEXT',
    'INDICATOR_LEVELVALUE',
    'INDICATOR_LEVELWIDTH',
    'INDICATOR_MAXIMUM',
    'INDICATOR_MINIMUM',
    'INDICATOR_SHORTNAME',
    'INT_MAX',
    'INT_MIN',
    'INVALID_HANDLE',
    'IS_DEBUG_MODE',
    'IS_PROFILE_MODE',
    'LICENSE_DEMO',
    'LICENSE_FREE',
    'LICENSE_FULL',
    'LICENSE_TIME',
    'LONG_MAX',
    'LONG_MIN',
    'MB_ABORTRETRYIGNORE',
    'MB_CANCELTRYCONTINUE',
    'MB_DEFBUTTON1',
    'MB_DEFBUTTON2',
    'MB_DEFBUTTON3',
    'MB_DEFBUTTON4',
    'MB_ICONASTERISK',
    'MB_ICONERROR',
    'MB_ICONEXCLAMATION',
    'MB_ICONHAND',
    'MB_ICONINFORMATION',
    'MB_ICONQUESTION',
    'MB_ICONSTOP',
    'MB_ICONWARNING',
    'MB_OKCANCEL',
    'MB_OK',
    'MB_RETRYCANCEL',
    'MB_YESNOCANCEL',
    'MB_YESNO',
    'MODE_ASK',
    'MODE_BID',
    'MODE_CHINKOUSPAN',
    'MODE_CLOSE',
    'MODE_DIGITS',
    'MODE_EMA',
    'MODE_EXPIRATION',
    'MODE_FREEZELEVEL',
    'MODE_GATORJAW',
    'MODE_GATORLIPS',
    'MODE_GATORTEETH',
    'MODE_HIGH',
    'MODE_KIJUNSEN',
    'MODE_LOTSIZE',
    'MODE_LOTSTEP',
    'MODE_LOWER',
    'MODE_LOW',
    'MODE_LWMA',
    'MODE_MAIN',
    'MODE_MARGINCALCMODE',
    'MODE_MARGINHEDGED',
    'MODE_MARGININIT',
    'MODE_MARGINMAINTENANCE',
    'MODE_MARGINREQUIRED',
    'MODE_MAXLOT',
    'MODE_MINLOT',
    'MODE_MINUSDI',
    'MODE_OPEN',
    'MODE_PLUSDI',
    'MODE_POINT',
    'MODE_PROFITCALCMODE',
    'MODE_SENKOUSPANA',
    'MODE_SENKOUSPANB',
    'MODE_SIGNAL',
    'MODE_SMA',
    'MODE_SMMA',
    'MODE_SPREAD',
    'MODE_STARTING',
    'MODE_STOPLEVEL',
    'MODE_SWAPLONG',
    'MODE_SWAPSHORT',
    'MODE_SWAPTYPE',
    'MODE_TENKANSEN',
    'MODE_TICKSIZE',
    'MODE_TICKVALUE',
    'MODE_TIME',
    'MODE_TRADEALLOWED',
    'MODE_UPPER',
    'MODE_VOLUME',
    'MONDAY',
    'MQL_DEBUG',
    'MQL_DLLS_ALLOWED',
    'MQL_FRAME_MODE',
    'MQL_LICENSE_TYPE',
    'MQL_OPTIMIZATION',
    'MQL_PROFILER',
    'MQL_PROGRAM_NAME',
    'MQL_PROGRAM_PATH',
    'MQL_PROGRAM_TYPE',
    'MQL_TESTER',
    'MQL_TRADE_ALLOWED',
    'MQL_VISUAL_MODE',
    'M_1_PI',
    'M_2_PI',
    'M_2_SQRTPI',
    'M_E',
    'M_LN2',
    'M_LN10',
    'M_LOG2E',
    'M_LOG10E',
    'M_PI',
    'M_PI_2',
    'M_PI_4',
    'M_SQRT1_2',
    'M_SQRT2',
    'NULL',
    'OBJPROP_ALIGN',
    'OBJPROP_ANCHOR',
    'OBJPROP_ANGLE',
    'OBJPROP_ARROWCODE',
    'OBJPROP_BACK',
    'OBJPROP_BGCOLOR',
    'OBJPROP_BMPFILE',
    'OBJPROP_BORDER_COLOR',
    'OBJPROP_BORDER_TYPE',
    'OBJPROP_CHART_ID',
    'OBJPROP_CHART_SCALE',
    'OBJPROP_COLOR',
    'OBJPROP_CORNER',
    'OBJPROP_CREATETIME',
    'OBJPROP_DATE_SCALE',
    'OBJPROP_DEVIATION',
    'OBJPROP_DRAWLINES',
    'OBJPROP_ELLIPSE',
    'OBJPROP_FIBOLEVELS',
    'OBJPROP_FILL',
    'OBJPROP_FIRSTLEVEL',
    'OBJPROP_FONTSIZE',
    'OBJPROP_FONT',
    'OBJPROP_HIDDEN',
    'OBJPROP_LEVELCOLOR',
    'OBJPROP_LEVELSTYLE',
    'OBJPROP_LEVELS',
    'OBJPROP_LEVELTEXT',
    'OBJPROP_LEVELVALUE',
    'OBJPROP_LEVELWIDTH',
    'OBJPROP_NAME',
    'OBJPROP_PERIOD',
    'OBJPROP_PRICE1',
    'OBJPROP_PRICE2',
    'OBJPROP_PRICE3',
    'OBJPROP_PRICE',
    'OBJPROP_PRICE_SCALE',
    'OBJPROP_RAY',
    'OBJPROP_RAY_RIGHT',
    'OBJPROP_READONLY',
    'OBJPROP_SCALE',
    'OBJPROP_SELECTABLE',
    'OBJPROP_SELECTED',
    'OBJPROP_STATE',
    'OBJPROP_STYLE',
    'OBJPROP_SYMBOL',
    'OBJPROP_TEXT',
    'OBJPROP_TIME1',
    'OBJPROP_TIME2',
    'OBJPROP_TIME3',
    'OBJPROP_TIMEFRAMES',
    'OBJPROP_TIME',
    'OBJPROP_TOOLTIP',
    'OBJPROP_TYPE',
    'OBJPROP_WIDTH',
    'OBJPROP_XDISTANCE',
    'OBJPROP_XOFFSET',
    'OBJPROP_XSIZE',
    'OBJPROP_YDISTANCE',
    'OBJPROP_YOFFSET',
    'OBJPROP_YSIZE',
    'OBJPROP_ZORDER',
    'OBJ_ALL_PERIODS',
    'OBJ_ARROW',
    'OBJ_ARROW_BUY',
    'OBJ_ARROW_CHECK',
    'OBJ_ARROW_DOWN',
    'OBJ_ARROW_LEFT_PRICE',
    'OBJ_ARROW_RIGHT_PRICE',
    'OBJ_ARROW_SELL',
    'OBJ_ARROW_STOP',
    'OBJ_ARROW_THUMB_DOWN',
    'OBJ_ARROW_THUMB_UP',
    'OBJ_ARROW_UP',
    'OBJ_BITMAP',
    'OBJ_BITMAP_LABEL',
    'OBJ_BUTTON',
    'OBJ_CHANNEL',
    'OBJ_CYCLES',
    'OBJ_EDIT',
    'OBJ_ELLIPSE',
    'OBJ_EVENT',
    'OBJ_EXPANSION',
    'OBJ_FIBOARC',
    'OBJ_FIBOCHANNEL',
    'OBJ_FIBOFAN',
    'OBJ_FIBOTIMES',
    'OBJ_FIBO',
    'OBJ_GANNFAN',
    'OBJ_GANNGRID',
    'OBJ_GANNLINE',
    'OBJ_HLINE',
    'OBJ_LABEL',
    'OBJ_NO_PERIODS',
    'OBJ_PERIOD_D1',
    'OBJ_PERIOD_H1',
    'OBJ_PERIOD_H4',
    'OBJ_PERIOD_M1',
    'OBJ_PERIOD_M5',
    'OBJ_PERIOD_M15',
    'OBJ_PERIOD_M30',
    'OBJ_PERIOD_MN1',
    'OBJ_PERIOD_W1',
    'OBJ_PITCHFORK',
    'OBJ_RECTANGLE',
    'OBJ_RECTANGLE_LABEL',
    'OBJ_REGRESSION',
    'OBJ_STDDEVCHANNEL',
    'OBJ_TEXT',
    'OBJ_TRENDBYANGLE',
    'OBJ_TREND',
    'OBJ_TRIANGLE',
    'OBJ_VLINE',
    'OP_BUYLIMIT',
    'OP_BUYSTOP',
    'OP_BUY',
    'OP_SELLLIMIT',
    'OP_SELLSTOP',
    'OP_SELL',
    'PERIOD_CURRENT',
    'PERIOD_D1',
    'PERIOD_H1',
    'PERIOD_H2',
    'PERIOD_H3',
    'PERIOD_H4',
    'PERIOD_H6',
    'PERIOD_H8',
    'PERIOD_H12',
    'PERIOD_M1',
    'PERIOD_M2',
    'PERIOD_M3',
    'PERIOD_M4',
    'PERIOD_M5',
    'PERIOD_M6',
    'PERIOD_M10',
    'PERIOD_M12',
    'PERIOD_M15',
    'PERIOD_M20',
    'PERIOD_M30',
    'PERIOD_MN1',
    'PERIOD_W1',
    'POINTER_AUTOMATIC',
    'POINTER_DYNAMIC',
    'POINTER_INVALID',
    'PRICE_CLOSE',
    'PRICE_HIGH',
    'PRICE_LOW',
    'PRICE_MEDIAN',
    'PRICE_OPEN',
    'PRICE_TYPICAL',
    'PRICE_WEIGHTED',
    'PROGRAM_EXPERT',
    'PROGRAM_INDICATOR',
    'PROGRAM_SCRIPT',
    'REASON_ACCOUNT',
    'REASON_CHARTCHANGE',
    'REASON_CHARTCLOSE',
    'REASON_CLOSE',
    'REASON_INITFAILED',
    'REASON_PARAMETERS',
    'REASON_PROGRAM'
    'REASON_RECOMPILE',
    'REASON_REMOVE',
    'REASON_TEMPLATE',
    'SATURDAY',
    'SEEK_CUR',
    'SEEK_END',
    'SEEK_SET',
    'SERIES_BARS_COUNT',
    'SERIES_FIRSTDATE',
    'SERIES_LASTBAR_DATE',
    'SERIES_SERVER_FIRSTDATE',
    'SERIES_SYNCHRONIZED',
    'SERIES_TERMINAL_FIRSTDATE',
    'SHORT_MAX',
    'SHORT_MIN',
    'STAT_BALANCEDD_PERCENT',
    'STAT_BALANCEMIN',
    'STAT_BALANCE_DDREL_PERCENT',
    'STAT_BALANCE_DD',
    'STAT_BALANCE_DD_RELATIVE',
    'STAT_CONLOSSMAX',
    'STAT_CONLOSSMAX_TRADES',
    'STAT_CONPROFITMAX',
    'STAT_CONPROFITMAX_TRADES',
    'STAT_CUSTOM_ONTESTER',
    'STAT_DEALS',
    'STAT_EQUITYDD_PERCENT',
    'STAT_EQUITYMIN',
    'STAT_EQUITY_DDREL_PERCENT',
    'STAT_EQUITY_DD',
    'STAT_EQUITY_DD_RELATIVE',
    'STAT_EXPECTED_PAYOFF',
    'STAT_GROSS_LOSS',
    'STAT_GROSS_PROFIT',
    'STAT_INITIAL_DEPOSIT',
    'STAT_LONG_TRADES',
    'STAT_LOSSTRADES_AVGCON',
    'STAT_LOSS_TRADES',
    'STAT_MAX_CONLOSSES',
    'STAT_MAX_CONLOSS_TRADES',
    'STAT_MAX_CONPROFIT_TRADES',
    'STAT_MAX_CONWINS',
    'STAT_MAX_LOSSTRADE',
    'STAT_MAX_PROFITTRADE',
    'STAT_MIN_MARGINLEVEL',
    'STAT_PROFITTRADES_AVGCON',
    'STAT_PROFIT',
    'STAT_PROFIT_FACTOR',
    'STAT_PROFIT_LONGTRADES',
    'STAT_PROFIT_SHORTTRADES',
    'STAT_PROFIT_TRADES',
    'STAT_RECOVERY_FACTOR',
    'STAT_SHARPE_RATIO',
    'STAT_SHORT_TRADES',
    'STAT_TRADES',
    'STAT_WITHDRAWAL',
    'STO_CLOSECLOSE',
    'STO_LOWHIGH',
    'STYLE_DASHDOTDOT',
    'STYLE_DASHDOT',
    'STYLE_DASH',
    'STYLE_DOT',
    'STYLE_SOLID',
    'SUNDAY',
    'SYMBOL_ARROWDOWN',
    'SYMBOL_ARROWUP',
    'SYMBOL_CHECKSIGN',
    'SYMBOL_LEFTPRICE',
    'SYMBOL_RIGHTPRICE',
    'SYMBOL_STOPSIGN',
    'SYMBOL_THUMBSDOWN',
    'SYMBOL_THUMBSUP',
    'TERMINAL_BUILD',
    'TERMINAL_CODEPAGE',
    'TERMINAL_COMMONDATA_PATH',
    'TERMINAL_COMPANY',
    'TERMINAL_CONNECTED',
    'TERMINAL_CPU_CORES',
    'TERMINAL_DATA_PATH',
    'TERMINAL_DISK_SPACE',
    'TERMINAL_DLLS_ALLOWED',
    'TERMINAL_EMAIL_ENABLED',
    'TERMINAL_FTP_ENABLED',
    'TERMINAL_LANGUAGE',
    'TERMINAL_MAXBARS',
    'TERMINAL_MEMORY_AVAILABLE',
    'TERMINAL_MEMORY_PHYSICAL',
    'TERMINAL_MEMORY_TOTAL',
    'TERMINAL_MEMORY_USED',
    'TERMINAL_NAME',
    'TERMINAL_OPENCL_SUPPORT',
    'TERMINAL_PATH',
    'TERMINAL_TRADE_ALLOWED',
    'TERMINAL_X64',
    'THURSDAY',
    'TRADE_ACTION_DEAL',
    'TRADE_ACTION_MODIFY',
    'TRADE_ACTION_PENDING',
    'TRADE_ACTION_REMOVE',
    'TRADE_ACTION_SLTP',
    'TUESDAY',
    'UCHAR_MAX',
    'UINT_MAX',
    'ULONG_MAX',
    'USHORT_MAX',
    'VOLUME_REAL',
    'VOLUME_TICK',
    'WEDNESDAY',
    'WHOLE_ARRAY',
    'WRONG_VALUE',
    'clrNONE',
    '__DATETIME__',
    '__DATE__',
    '__FILE__',
    '__FUNCSIG__',
    '__FUNCTION__',
    '__LINE__',
    '__MQL4BUILD__',
    '__MQLBUILD__',
    '__PATH__',
)

colors = (
    'AliceBlue',
    'AntiqueWhite',
    'Aquamarine',
    'Aqua',
    'Beige',
    'Bisque',
    'Black',
    'BlanchedAlmond',
    'BlueViolet',
    'Blue',
    'Brown',
    'BurlyWood',
    'CadetBlue',
    'Chartreuse',
    'Chocolate',
    'Coral',
    'CornflowerBlue',
    'Cornsilk',
    'Crimson',
    'DarkBlue',
    'DarkGoldenrod',
    'DarkGray',
    'DarkGreen',
    'DarkKhaki',
    'DarkOliveGreen',
    'DarkOrange',
    'DarkOrchid',
    'DarkSalmon',
    'DarkSeaGreen',
    'DarkSlateBlue',
    'DarkSlateGray',
    'DarkTurquoise',
    'DarkViolet',
    'DeepPink',
    'DeepSkyBlue',
    'DimGray',
    'DodgerBlue',
    'FireBrick',
    'ForestGreen',
    'Gainsboro',
    'Goldenrod',
    'Gold',
    'Gray',
    'GreenYellow',
    'Green',
    'Honeydew',
    'HotPink',
    'IndianRed',
    'Indigo',
    'Ivory',
    'Khaki',
    'LavenderBlush',
    'Lavender',
    'LawnGreen',
    'LemonChiffon',
    'LightBlue',
    'LightCoral',
    'LightCyan',
    'LightGoldenrod',
    'LightGray',
    'LightGreen',
    'LightPink',
    'LightSalmon',
    'LightSeaGreen',
    'LightSkyBlue',
    'LightSlateGray',
    'LightSteelBlue',
    'LightYellow',
    'LimeGreen',
    'Lime',
    'Linen',
    'Magenta',
    'Maroon',
    'MediumAquamarine',
    'MediumBlue',
    'MediumOrchid',
    'MediumPurple',
    'MediumSeaGreen',
    'MediumSlateBlue',
    'MediumSpringGreen',
    'MediumTurquoise',
    'MediumVioletRed',
    'MidnightBlue',
    'MintCream',
    'MistyRose',
    'Moccasin',
    'NavajoWhite',
    'Navy',
    'OldLace',
    'OliveDrab',
    'Olive',
    'OrangeRed',
    'Orange',
    'Orchid',
    'PaleGoldenrod',
    'PaleGreen',
    'PaleTurquoise',
    'PaleVioletRed',
    'PapayaWhip',
    'PeachPuff',
    'Peru',
    'Pink',
    'Plum',
    'PowderBlue',
    'Purple',
    'Red',
    'RosyBrown',
    'RoyalBlue',
    'SaddleBrown',
    'Salmon',
    'SandyBrown',
    'SeaGreen',
    'Seashell',
    'Sienna',
    'Silver',
    'SkyBlue',
    'SlateBlue',
    'SlateGray',
    'Snow',
    'SpringGreen',
    'SteelBlue',
    'Tan',
    'Teal',
    'Thistle',
    'Tomato',
    'Turquoise',
    'Violet',
    'Wheat',
    'WhiteSmoke',
    'White',
    'YellowGreen',
    'Yellow',
)

keywords = (
    'input', '_Digits', '_Point', '_LastError', '_Period', '_RandomSeed',
    '_StopFlag', '_Symbol', '_UninitReason', 'Ask', 'Bars', 'Bid',
    'Close', 'Digits', 'High', 'Low', 'Open', 'Point', 'Time',
    'Volume',
)
c_types = (
    'void', 'char', 'uchar', 'bool', 'short', 'ushort', 'int', 'uint',
    'color', 'long', 'ulong', 'datetime', 'float', 'double',
    'string',
)

# === NexusCore/openenv\Lib\site-packages\psutil\_pswindows.py ===
# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Windows platform implementation."""

import contextlib
import errno
import functools
import os
import signal
import sys
import time
from collections import namedtuple

from . import _common
from ._common import ENCODING
from ._common import ENCODING_ERRS
from ._common import AccessDenied
from ._common import NoSuchProcess
from ._common import TimeoutExpired
from ._common import conn_tmap
from ._common import conn_to_ntuple
from ._common import debug
from ._common import isfile_strict
from ._common import memoize
from ._common import memoize_when_activated
from ._common import parse_environ_block
from ._common import usage_percent
from ._compat import PY3
from ._compat import long
from ._compat import lru_cache
from ._compat import range
from ._compat import unicode
from ._psutil_windows import ABOVE_NORMAL_PRIORITY_CLASS
from ._psutil_windows import BELOW_NORMAL_PRIORITY_CLASS
from ._psutil_windows import HIGH_PRIORITY_CLASS
from ._psutil_windows import IDLE_PRIORITY_CLASS
from ._psutil_windows import NORMAL_PRIORITY_CLASS
from ._psutil_windows import REALTIME_PRIORITY_CLASS


try:
    from . import _psutil_windows as cext
except ImportError as err:
    if (
        str(err).lower().startswith("dll load failed")
        and sys.getwindowsversion()[0] < 6
    ):
        # We may get here if:
        # 1) we are on an old Windows version
        # 2) psutil was installed via pip + wheel
        # See: https://github.com/giampaolo/psutil/issues/811
        msg = "this Windows version is too old (< Windows Vista); "
        msg += "psutil 3.4.2 is the latest version which supports Windows "
        msg += "2000, XP and 2003 server"
        raise RuntimeError(msg)
    else:
        raise

if PY3:
    import enum
else:
    enum = None

# process priority constants, import from __init__.py:
# http://msdn.microsoft.com/en-us/library/ms686219(v=vs.85).aspx
# fmt: off
__extra__all__ = [
    "win_service_iter", "win_service_get",
    # Process priority
    "ABOVE_NORMAL_PRIORITY_CLASS", "BELOW_NORMAL_PRIORITY_CLASS",
    "HIGH_PRIORITY_CLASS", "IDLE_PRIORITY_CLASS", "NORMAL_PRIORITY_CLASS",
    "REALTIME_PRIORITY_CLASS",
    # IO priority
    "IOPRIO_VERYLOW", "IOPRIO_LOW", "IOPRIO_NORMAL", "IOPRIO_HIGH",
    # others
    "CONN_DELETE_TCB", "AF_LINK",
]
# fmt: on


# =====================================================================
# --- globals
# =====================================================================

CONN_DELETE_TCB = "DELETE_TCB"
ERROR_PARTIAL_COPY = 299
PYPY = '__pypy__' in sys.builtin_module_names

if enum is None:
    AF_LINK = -1
else:
    AddressFamily = enum.IntEnum('AddressFamily', {'AF_LINK': -1})
    AF_LINK = AddressFamily.AF_LINK

TCP_STATUSES = {
    cext.MIB_TCP_STATE_ESTAB: _common.CONN_ESTABLISHED,
    cext.MIB_TCP_STATE_SYN_SENT: _common.CONN_SYN_SENT,
    cext.MIB_TCP_STATE_SYN_RCVD: _common.CONN_SYN_RECV,
    cext.MIB_TCP_STATE_FIN_WAIT1: _common.CONN_FIN_WAIT1,
    cext.MIB_TCP_STATE_FIN_WAIT2: _common.CONN_FIN_WAIT2,
    cext.MIB_TCP_STATE_TIME_WAIT: _common.CONN_TIME_WAIT,
    cext.MIB_TCP_STATE_CLOSED: _common.CONN_CLOSE,
    cext.MIB_TCP_STATE_CLOSE_WAIT: _common.CONN_CLOSE_WAIT,
    cext.MIB_TCP_STATE_LAST_ACK: _common.CONN_LAST_ACK,
    cext.MIB_TCP_STATE_LISTEN: _common.CONN_LISTEN,
    cext.MIB_TCP_STATE_CLOSING: _common.CONN_CLOSING,
    cext.MIB_TCP_STATE_DELETE_TCB: CONN_DELETE_TCB,
    cext.PSUTIL_CONN_NONE: _common.CONN_NONE,
}

if enum is not None:

    class Priority(enum.IntEnum):
        ABOVE_NORMAL_PRIORITY_CLASS = ABOVE_NORMAL_PRIORITY_CLASS
        BELOW_NORMAL_PRIORITY_CLASS = BELOW_NORMAL_PRIORITY_CLASS
        HIGH_PRIORITY_CLASS = HIGH_PRIORITY_CLASS
        IDLE_PRIORITY_CLASS = IDLE_PRIORITY_CLASS
        NORMAL_PRIORITY_CLASS = NORMAL_PRIORITY_CLASS
        REALTIME_PRIORITY_CLASS = REALTIME_PRIORITY_CLASS

    globals().update(Priority.__members__)

if enum is None:
    IOPRIO_VERYLOW = 0
    IOPRIO_LOW = 1
    IOPRIO_NORMAL = 2
    IOPRIO_HIGH = 3
else:

    class IOPriority(enum.IntEnum):
        IOPRIO_VERYLOW = 0
        IOPRIO_LOW = 1
        IOPRIO_NORMAL = 2
        IOPRIO_HIGH = 3

    globals().update(IOPriority.__members__)

pinfo_map = dict(
    num_handles=0,
    ctx_switches=1,
    user_time=2,
    kernel_time=3,
    create_time=4,
    num_threads=5,
    io_rcount=6,
    io_wcount=7,
    io_rbytes=8,
    io_wbytes=9,
    io_count_others=10,
    io_bytes_others=11,
    num_page_faults=12,
    peak_wset=13,
    wset=14,
    peak_paged_pool=15,
    paged_pool=16,
    peak_non_paged_pool=17,
    non_paged_pool=18,
    pagefile=19,
    peak_pagefile=20,
    mem_private=21,
)


# =====================================================================
# --- named tuples
# =====================================================================


# fmt: off
# psutil.cpu_times()
scputimes = namedtuple('scputimes',
                       ['user', 'system', 'idle', 'interrupt', 'dpc'])
# psutil.virtual_memory()
svmem = namedtuple('svmem', ['total', 'available', 'percent', 'used', 'free'])
# psutil.Process.memory_info()
pmem = namedtuple(
    'pmem', ['rss', 'vms',
             'num_page_faults', 'peak_wset', 'wset', 'peak_paged_pool',
             'paged_pool', 'peak_nonpaged_pool', 'nonpaged_pool',
             'pagefile', 'peak_pagefile', 'private'])
# psutil.Process.memory_full_info()
pfullmem = namedtuple('pfullmem', pmem._fields + ('uss', ))
# psutil.Process.memory_maps(grouped=True)
pmmap_grouped = namedtuple('pmmap_grouped', ['path', 'rss'])
# psutil.Process.memory_maps(grouped=False)
pmmap_ext = namedtuple(
    'pmmap_ext', 'addr perms ' + ' '.join(pmmap_grouped._fields))
# psutil.Process.io_counters()
pio = namedtuple('pio', ['read_count', 'write_count',
                         'read_bytes', 'write_bytes',
                         'other_count', 'other_bytes'])
# fmt: on


# =====================================================================
# --- utils
# =====================================================================


@lru_cache(maxsize=512)
def convert_dos_path(s):
    r"""Convert paths using native DOS format like:
        "\Device\HarddiskVolume1\Windows\systemew\file.txt"
    into:
        "C:\Windows\systemew\file.txt".
    """
    rawdrive = '\\'.join(s.split('\\')[:3])
    driveletter = cext.QueryDosDevice(rawdrive)
    remainder = s[len(rawdrive) :]
    return os.path.join(driveletter, remainder)


def py2_strencode(s):
    """Encode a unicode string to a byte string by using the default fs
    encoding + "replace" error handler.
    """
    if PY3:
        return s
    else:
        if isinstance(s, str):
            return s
        else:
            return s.encode(ENCODING, ENCODING_ERRS)


@memoize
def getpagesize():
    return cext.getpagesize()


# =====================================================================
# --- memory
# =====================================================================


def virtual_memory():
    """System virtual memory as a namedtuple."""
    mem = cext.virtual_mem()
    totphys, availphys, totsys, availsys = mem
    #
    total = totphys
    avail = availphys
    free = availphys
    used = total - avail
    percent = usage_percent((total - avail), total, round_=1)
    return svmem(total, avail, percent, used, free)


def swap_memory():
    """Swap system memory as a (total, used, free, sin, sout) tuple."""
    mem = cext.virtual_mem()

    total_phys = mem[0]
    total_system = mem[2]

    # system memory (commit total/limit) is the sum of physical and swap
    # thus physical memory values need to be subtracted to get swap values
    total = total_system - total_phys
    # commit total is incremented immediately (decrementing free_system)
    # while the corresponding free physical value is not decremented until
    # pages are accessed, so we can't use free system memory for swap.
    # instead, we calculate page file usage based on performance counter
    if total > 0:
        percentswap = cext.swap_percent()
        used = int(0.01 * percentswap * total)
    else:
        percentswap = 0.0
        used = 0

    free = total - used
    percent = round(percentswap, 1)
    return _common.sswap(total, used, free, percent, 0, 0)


# =====================================================================
# --- disk
# =====================================================================


disk_io_counters = cext.disk_io_counters


def disk_usage(path):
    """Return disk usage associated with path."""
    if PY3 and isinstance(path, bytes):
        # XXX: do we want to use "strict"? Probably yes, in order
        # to fail immediately. After all we are accepting input here...
        path = path.decode(ENCODING, errors="strict")
    total, free = cext.disk_usage(path)
    used = total - free
    percent = usage_percent(used, total, round_=1)
    return _common.sdiskusage(total, used, free, percent)


def disk_partitions(all):
    """Return disk partitions."""
    rawlist = cext.disk_partitions(all)
    return [_common.sdiskpart(*x) for x in rawlist]


# =====================================================================
# --- CPU
# =====================================================================


def cpu_times():
    """Return system CPU times as a named tuple."""
    user, system, idle = cext.cpu_times()
    # Internally, GetSystemTimes() is used, and it doesn't return
    # interrupt and dpc times. cext.per_cpu_times() does, so we
    # rely on it to get those only.
    percpu_summed = scputimes(*[sum(n) for n in zip(*cext.per_cpu_times())])
    return scputimes(
        user, system, idle, percpu_summed.interrupt, percpu_summed.dpc
    )


def per_cpu_times():
    """Return system per-CPU times as a list of named tuples."""
    ret = []
    for user, system, idle, interrupt, dpc in cext.per_cpu_times():
        item = scputimes(user, system, idle, interrupt, dpc)
        ret.append(item)
    return ret


def cpu_count_logical():
    """Return the number of logical CPUs in the system."""
    return cext.cpu_count_logical()


def cpu_count_cores():
    """Return the number of CPU cores in the system."""
    return cext.cpu_count_cores()


def cpu_stats():
    """Return CPU statistics."""
    ctx_switches, interrupts, dpcs, syscalls = cext.cpu_stats()
    soft_interrupts = 0
    return _common.scpustats(
        ctx_switches, interrupts, soft_interrupts, syscalls
    )


def cpu_freq():
    """Return CPU frequency.
    On Windows per-cpu frequency is not supported.
    """
    curr, max_ = cext.cpu_freq()
    min_ = 0.0
    return [_common.scpufreq(float(curr), min_, float(max_))]


_loadavg_inititialized = False


def getloadavg():
    """Return the number of processes in the system run queue averaged
    over the last 1, 5, and 15 minutes respectively as a tuple.
    """
    global _loadavg_inititialized

    if not _loadavg_inititialized:
        cext.init_loadavg_counter()
        _loadavg_inititialized = True

    # Drop to 2 decimal points which is what Linux does
    raw_loads = cext.getloadavg()
    return tuple([round(load, 2) for load in raw_loads])


# =====================================================================
# --- network
# =====================================================================


def net_connections(kind, _pid=-1):
    """Return socket connections.  If pid == -1 return system-wide
    connections (as opposed to connections opened by one process only).
    """
    if kind not in conn_tmap:
        raise ValueError(
            "invalid %r kind argument; choose between %s"
            % (kind, ', '.join([repr(x) for x in conn_tmap]))
        )
    families, types = conn_tmap[kind]
    rawlist = cext.net_connections(_pid, families, types)
    ret = set()
    for item in rawlist:
        fd, fam, type, laddr, raddr, status, pid = item
        nt = conn_to_ntuple(
            fd,
            fam,
            type,
            laddr,
            raddr,
            status,
            TCP_STATUSES,
            pid=pid if _pid == -1 else None,
        )
        ret.add(nt)
    return list(ret)


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    ret = {}
    rawdict = cext.net_if_stats()
    for name, items in rawdict.items():
        if not PY3:
            assert isinstance(name, unicode), type(name)
            name = py2_strencode(name)
        isup, duplex, speed, mtu = items
        if hasattr(_common, 'NicDuplex'):
            duplex = _common.NicDuplex(duplex)
        ret[name] = _common.snicstats(isup, duplex, speed, mtu, '')
    return ret


def net_io_counters():
    """Return network I/O statistics for every network interface
    installed on the system as a dict of raw tuples.
    """
    ret = cext.net_io_counters()
    return dict([(py2_strencode(k), v) for k, v in ret.items()])


def net_if_addrs():
    """Return the addresses associated to each NIC."""
    ret = []
    for items in cext.net_if_addrs():
        items = list(items)
        items[0] = py2_strencode(items[0])
        ret.append(items)
    return ret


# =====================================================================
# --- sensors
# =====================================================================


def sensors_battery():
    """Return battery information."""
    # For constants meaning see:
    # https://msdn.microsoft.com/en-us/library/windows/desktop/
    #     aa373232(v=vs.85).aspx
    acline_status, flags, percent, secsleft = cext.sensors_battery()
    power_plugged = acline_status == 1
    no_battery = bool(flags & 128)
    charging = bool(flags & 8)

    if no_battery:
        return None
    if power_plugged or charging:
        secsleft = _common.POWER_TIME_UNLIMITED
    elif secsleft == -1:
        secsleft = _common.POWER_TIME_UNKNOWN

    return _common.sbattery(percent, secsleft, power_plugged)


# =====================================================================
# --- other system functions
# =====================================================================


_last_btime = 0


def boot_time():
    """The system boot time expressed in seconds since the epoch."""
    # This dirty hack is to adjust the precision of the returned
    # value which may have a 1 second fluctuation, see:
    # https://github.com/giampaolo/psutil/issues/1007
    global _last_btime
    ret = float(cext.boot_time())
    if abs(ret - _last_btime) <= 1:
        return _last_btime
    else:
        _last_btime = ret
        return ret


def users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    rawlist = cext.users()
    for item in rawlist:
        user, hostname, tstamp = item
        user = py2_strencode(user)
        nt = _common.suser(user, None, hostname, tstamp, None)
        retlist.append(nt)
    return retlist


# =====================================================================
# --- Windows services
# =====================================================================


def win_service_iter():
    """Yields a list of WindowsService instances."""
    for name, display_name in cext.winservice_enumerate():
        yield WindowsService(py2_strencode(name), py2_strencode(display_name))


def win_service_get(name):
    """Open a Windows service and return it as a WindowsService instance."""
    service = WindowsService(name, None)
    service._display_name = service._query_config()['display_name']
    return service


class WindowsService:
    """Represents an installed Windows service."""

    def __init__(self, name, display_name):
        self._name = name
        self._display_name = display_name

    def __str__(self):
        details = "(name=%r, display_name=%r)" % (
            self._name,
            self._display_name,
        )
        return "%s%s" % (self.__class__.__name__, details)

    def __repr__(self):
        return "<%s at %s>" % (self.__str__(), id(self))

    def __eq__(self, other):
        # Test for equality with another WindosService object based
        # on name.
        if not isinstance(other, WindowsService):
            return NotImplemented
        return self._name == other._name

    def __ne__(self, other):
        return not self == other

    def _query_config(self):
        with self._wrap_exceptions():
            display_name, binpath, username, start_type = (
                cext.winservice_query_config(self._name)
            )
        # XXX - update _self.display_name?
        return dict(
            display_name=py2_strencode(display_name),
            binpath=py2_strencode(binpath),
            username=py2_strencode(username),
            start_type=py2_strencode(start_type),
        )

    def _query_status(self):
        with self._wrap_exceptions():
            status, pid = cext.winservice_query_status(self._name)
        if pid == 0:
            pid = None
        return dict(status=status, pid=pid)

    @contextlib.contextmanager
    def _wrap_exceptions(self):
        """Ctx manager which translates bare OSError and WindowsError
        exceptions into NoSuchProcess and AccessDenied.
        """
        try:
            yield
        except OSError as err:
            if is_permission_err(err):
                msg = (
                    "service %r is not querable (not enough privileges)"
                    % self._name
                )
                raise AccessDenied(pid=None, name=self._name, msg=msg)
            elif err.winerror in (
                cext.ERROR_INVALID_NAME,
                cext.ERROR_SERVICE_DOES_NOT_EXIST,
            ):
                msg = "service %r does not exist" % self._name
                raise NoSuchProcess(pid=None, name=self._name, msg=msg)
            else:
                raise

    # config query

    def name(self):
        """The service name. This string is how a service is referenced
        and can be passed to win_service_get() to get a new
        WindowsService instance.
        """
        return self._name

    def display_name(self):
        """The service display name. The value is cached when this class
        is instantiated.
        """
        return self._display_name

    def binpath(self):
        """The fully qualified path to the service binary/exe file as
        a string, including command line arguments.
        """
        return self._query_config()['binpath']

    def username(self):
        """The name of the user that owns this service."""
        return self._query_config()['username']

    def start_type(self):
        """A string which can either be "automatic", "manual" or
        "disabled".
        """
        return self._query_config()['start_type']

    # status query

    def pid(self):
        """The process PID, if any, else None. This can be passed
        to Process class to control the service's process.
        """
        return self._query_status()['pid']

    def status(self):
        """Service status as a string."""
        return self._query_status()['status']

    def description(self):
        """Service long description."""
        return py2_strencode(cext.winservice_query_descr(self.name()))

    # utils

    def as_dict(self):
        """Utility method retrieving all the information above as a
        dictionary.
        """
        d = self._query_config()
        d.update(self._query_status())
        d['name'] = self.name()
        d['display_name'] = self.display_name()
        d['description'] = self.description()
        return d

    # actions
    # XXX: the necessary C bindings for start() and stop() are
    # implemented but for now I prefer not to expose them.
    # I may change my mind in the future. Reasons:
    # - they require Administrator privileges
    # - can't implement a timeout for stop() (unless by using a thread,
    #   which sucks)
    # - would require adding ServiceAlreadyStarted and
    #   ServiceAlreadyStopped exceptions, adding two new APIs.
    # - we might also want to have modify(), which would basically mean
    #   rewriting win32serviceutil.ChangeServiceConfig, which involves a
    #   lot of stuff (and API constants which would pollute the API), see:
    #   http://pyxr.sourceforge.net/PyXR/c/python24/lib/site-packages/
    #       win32/lib/win32serviceutil.py.html#0175
    # - psutil is typically about "read only" monitoring stuff;
    #   win_service_* APIs should only be used to retrieve a service and
    #   check whether it's running

    # def start(self, timeout=None):
    #     with self._wrap_exceptions():
    #         cext.winservice_start(self.name())
    #         if timeout:
    #             giveup_at = time.time() + timeout
    #             while True:
    #                 if self.status() == "running":
    #                     return
    #                 else:
    #                     if time.time() > giveup_at:
    #                         raise TimeoutExpired(timeout)
    #                     else:
    #                         time.sleep(.1)

    # def stop(self):
    #     # Note: timeout is not implemented because it's just not
    #     # possible, see:
    #     # http://stackoverflow.com/questions/11973228/
    #     with self._wrap_exceptions():
    #         return cext.winservice_stop(self.name())


# =====================================================================
# --- processes
# =====================================================================


pids = cext.pids
pid_exists = cext.pid_exists
ppid_map = cext.ppid_map  # used internally by Process.children()


def is_permission_err(exc):
    """Return True if this is a permission error."""
    assert isinstance(exc, OSError), exc
    if exc.errno in (errno.EPERM, errno.EACCES):
        return True
    # On Python 2 OSError doesn't always have 'winerror'. Sometimes
    # it does, in which case the original exception was WindowsError
    # (which is a subclass of OSError).
    if getattr(exc, "winerror", -1) in (
        cext.ERROR_ACCESS_DENIED,
        cext.ERROR_PRIVILEGE_NOT_HELD,
    ):
        return True
    return False


def convert_oserror(exc, pid=None, name=None):
    """Convert OSError into NoSuchProcess or AccessDenied."""
    assert isinstance(exc, OSError), exc
    if is_permission_err(exc):
        return AccessDenied(pid=pid, name=name)
    if exc.errno == errno.ESRCH:
        return NoSuchProcess(pid=pid, name=name)
    raise exc


def wrap_exceptions(fun):
    """Decorator which converts OSError into NoSuchProcess or AccessDenied."""

    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except OSError as err:
            raise convert_oserror(err, pid=self.pid, name=self._name)

    return wrapper


def retry_error_partial_copy(fun):
    """Workaround for https://github.com/giampaolo/psutil/issues/875.
    See: https://stackoverflow.com/questions/4457745#4457745.
    """

    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        delay = 0.0001
        times = 33
        for _ in range(times):  # retries for roughly 1 second
            try:
                return fun(self, *args, **kwargs)
            except WindowsError as _:
                err = _
                if err.winerror == ERROR_PARTIAL_COPY:
                    time.sleep(delay)
                    delay = min(delay * 2, 0.04)
                    continue
                raise
        msg = (
            "{} retried {} times, converted to AccessDenied as it's still"
            "returning {}".format(fun, times, err)
        )
        raise AccessDenied(pid=self.pid, name=self._name, msg=msg)

    return wrapper


class Process:
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_name", "_ppid", "_cache"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None

    # --- oneshot() stuff

    def oneshot_enter(self):
        self._proc_info.cache_activate(self)
        self.exe.cache_activate(self)

    def oneshot_exit(self):
        self._proc_info.cache_deactivate(self)
        self.exe.cache_deactivate(self)

    @memoize_when_activated
    def _proc_info(self):
        """Return multiple information about this process as a
        raw tuple.
        """
        ret = cext.proc_info(self.pid)
        assert len(ret) == len(pinfo_map)
        return ret

    def name(self):
        """Return process name, which on Windows is always the final
        part of the executable.
        """
        # This is how PIDs 0 and 4 are always represented in taskmgr
        # and process-hacker.
        if self.pid == 0:
            return "System Idle Process"
        if self.pid == 4:
            return "System"
        return os.path.basename(self.exe())

    @wrap_exceptions
    @memoize_when_activated
    def exe(self):
        if PYPY:
            try:
                exe = cext.proc_exe(self.pid)
            except WindowsError as err:
                # 24 = ERROR_TOO_MANY_OPEN_FILES. Not sure why this happens
                # (perhaps PyPy's JIT delaying garbage collection of files?).
                if err.errno == 24:
                    debug("%r translated into AccessDenied" % err)
                    raise AccessDenied(self.pid, self._name)
                raise
        else:
            exe = cext.proc_exe(self.pid)
        if not PY3:
            exe = py2_strencode(exe)
        if exe.startswith('\\'):
            return convert_dos_path(exe)
        return exe  # May be "Registry", "MemCompression", ...

    @wrap_exceptions
    @retry_error_partial_copy
    def cmdline(self):
        if cext.WINVER >= cext.WINDOWS_8_1:
            # PEB method detects cmdline changes but requires more
            # privileges: https://github.com/giampaolo/psutil/pull/1398
            try:
                ret = cext.proc_cmdline(self.pid, use_peb=True)
            except OSError as err:
                if is_permission_err(err):
                    ret = cext.proc_cmdline(self.pid, use_peb=False)
                else:
                    raise
        else:
            ret = cext.proc_cmdline(self.pid, use_peb=True)
        if PY3:
            return ret
        else:
            return [py2_strencode(s) for s in ret]

    @wrap_exceptions
    @retry_error_partial_copy
    def environ(self):
        ustr = cext.proc_environ(self.pid)
        if ustr and not PY3:
            assert isinstance(ustr, unicode), type(ustr)
        return parse_environ_block(py2_strencode(ustr))

    def ppid(self):
        try:
            return ppid_map()[self.pid]
        except KeyError:
            raise NoSuchProcess(self.pid, self._name)

    def _get_raw_meminfo(self):
        try:
            return cext.proc_memory_info(self.pid)
        except OSError as err:
            if is_permission_err(err):
                # TODO: the C ext can probably be refactored in order
                # to get this from cext.proc_info()
                info = self._proc_info()
                return (
                    info[pinfo_map['num_page_faults']],
                    info[pinfo_map['peak_wset']],
                    info[pinfo_map['wset']],
                    info[pinfo_map['peak_paged_pool']],
                    info[pinfo_map['paged_pool']],
                    info[pinfo_map['peak_non_paged_pool']],
                    info[pinfo_map['non_paged_pool']],
                    info[pinfo_map['pagefile']],
                    info[pinfo_map['peak_pagefile']],
                    info[pinfo_map['mem_private']],
                )
            raise

    @wrap_exceptions
    def memory_info(self):
        # on Windows RSS == WorkingSetSize and VSM == PagefileUsage.
        # Underlying C function returns fields of PROCESS_MEMORY_COUNTERS
        # struct.
        t = self._get_raw_meminfo()
        rss = t[2]  # wset
        vms = t[7]  # pagefile
        return pmem(*(rss, vms) + t)

    @wrap_exceptions
    def memory_full_info(self):
        basic_mem = self.memory_info()
        uss = cext.proc_memory_uss(self.pid)
        uss *= getpagesize()
        return pfullmem(*basic_mem + (uss,))

    def memory_maps(self):
        try:
            raw = cext.proc_memory_maps(self.pid)
        except OSError as err:
            # XXX - can't use wrap_exceptions decorator as we're
            # returning a generator; probably needs refactoring.
            raise convert_oserror(err, self.pid, self._name)
        else:
            for addr, perm, path, rss in raw:
                path = convert_dos_path(path)
                if not PY3:
                    path = py2_strencode(path)
                addr = hex(addr)
                yield (addr, perm, path, rss)

    @wrap_exceptions
    def kill(self):
        return cext.proc_kill(self.pid)

    @wrap_exceptions
    def send_signal(self, sig):
        if sig == signal.SIGTERM:
            cext.proc_kill(self.pid)
        # py >= 2.7
        elif sig in (
            getattr(signal, "CTRL_C_EVENT", object()),
            getattr(signal, "CTRL_BREAK_EVENT", object()),
        ):
            os.kill(self.pid, sig)
        else:
            msg = (
                "only SIGTERM, CTRL_C_EVENT and CTRL_BREAK_EVENT signals "
                "are supported on Windows"
            )
            raise ValueError(msg)

    @wrap_exceptions
    def wait(self, timeout=None):
        if timeout is None:
            cext_timeout = cext.INFINITE
        else:
            # WaitForSingleObject() expects time in milliseconds.
            cext_timeout = int(timeout * 1000)

        timer = getattr(time, 'monotonic', time.time)
        stop_at = timer() + timeout if timeout is not None else None

        try:
            # Exit code is supposed to come from GetExitCodeProcess().
            # May also be None if OpenProcess() failed with
            # ERROR_INVALID_PARAMETER, meaning PID is already gone.
            exit_code = cext.proc_wait(self.pid, cext_timeout)
        except cext.TimeoutExpired:
            # WaitForSingleObject() returned WAIT_TIMEOUT. Just raise.
            raise TimeoutExpired(timeout, self.pid, self._name)
        except cext.TimeoutAbandoned:
            # WaitForSingleObject() returned WAIT_ABANDONED, see:
            # https://github.com/giampaolo/psutil/issues/1224
            # We'll just rely on the internal polling and return None
            # when the PID disappears. Subprocess module does the same
            # (return None):
            # https://github.com/python/cpython/blob/
            #     be50a7b627d0aa37e08fa8e2d5568891f19903ce/
            #     Lib/subprocess.py#L1193-L1194
            exit_code = None

        # At this point WaitForSingleObject() returned WAIT_OBJECT_0,
        # meaning the process is gone. Stupidly there are cases where
        # its PID may still stick around so we do a further internal
        # polling.
        delay = 0.0001
        while True:
            if not pid_exists(self.pid):
                return exit_code
            if stop_at and timer() >= stop_at:
                raise TimeoutExpired(timeout, pid=self.pid, name=self._name)
            time.sleep(delay)
            delay = min(delay * 2, 0.04)  # incremental delay

    @wrap_exceptions
    def username(self):
        if self.pid in (0, 4):
            return 'NT AUTHORITY\\SYSTEM'
        domain, user = cext.proc_username(self.pid)
        return py2_strencode(domain) + '\\' + py2_strencode(user)

    @wrap_exceptions
    def create_time(self):
        # Note: proc_times() not put under oneshot() 'cause create_time()
        # is already cached by the main Process class.
        try:
            user, system, created = cext.proc_times(self.pid)
            return created
        except OSError as err:
            if is_permission_err(err):
                return self._proc_info()[pinfo_map['create_time']]
            raise

    @wrap_exceptions
    def num_threads(self):
        return self._proc_info()[pinfo_map['num_threads']]

    @wrap_exceptions
    def threads(self):
        rawlist = cext.proc_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = _common.pthread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist

    @wrap_exceptions
    def cpu_times(self):
        try:
            user, system, created = cext.proc_times(self.pid)
        except OSError as err:
            if not is_permission_err(err):
                raise
            info = self._proc_info()
            user = info[pinfo_map['user_time']]
            system = info[pinfo_map['kernel_time']]
        # Children user/system times are not retrievable (set to 0).
        return _common.pcputimes(user, system, 0.0, 0.0)

    @wrap_exceptions
    def suspend(self):
        cext.proc_suspend_or_resume(self.pid, True)

    @wrap_exceptions
    def resume(self):
        cext.proc_suspend_or_resume(self.pid, False)

    @wrap_exceptions
    @retry_error_partial_copy
    def cwd(self):
        if self.pid in (0, 4):
            raise AccessDenied(self.pid, self._name)
        # return a normalized pathname since the native C function appends
        # "\\" at the and of the path
        path = cext.proc_cwd(self.pid)
        return py2_strencode(os.path.normpath(path))

    @wrap_exceptions
    def open_files(self):
        if self.pid in (0, 4):
            return []
        ret = set()
        # Filenames come in in native format like:
        # "\Device\HarddiskVolume1\Windows\systemew\file.txt"
        # Convert the first part in the corresponding drive letter
        # (e.g. "C:\") by using Windows's QueryDosDevice()
        raw_file_names = cext.proc_open_files(self.pid)
        for _file in raw_file_names:
            _file = convert_dos_path(_file)
            if isfile_strict(_file):
                if not PY3:
                    _file = py2_strencode(_file)
                ntuple = _common.popenfile(_file, -1)
                ret.add(ntuple)
        return list(ret)

    @wrap_exceptions
    def connections(self, kind='inet'):
        return net_connections(kind, _pid=self.pid)

    @wrap_exceptions
    def nice_get(self):
        value = cext.proc_priority_get(self.pid)
        if enum is not None:
            value = Priority(value)
        return value

    @wrap_exceptions
    def nice_set(self, value):
        return cext.proc_priority_set(self.pid, value)

    @wrap_exceptions
    def ionice_get(self):
        ret = cext.proc_io_priority_get(self.pid)
        if enum is not None:
            ret = IOPriority(ret)
        return ret

    @wrap_exceptions
    def ionice_set(self, ioclass, value):
        if value:
            msg = "value argument not accepted on Windows"
            raise TypeError(msg)
        if ioclass not in (
            IOPRIO_VERYLOW,
            IOPRIO_LOW,
            IOPRIO_NORMAL,
            IOPRIO_HIGH,
        ):
            raise ValueError("%s is not a valid priority" % ioclass)
        cext.proc_io_priority_set(self.pid, ioclass)

    @wrap_exceptions
    def io_counters(self):
        try:
            ret = cext.proc_io_counters(self.pid)
        except OSError as err:
            if not is_permission_err(err):
                raise
            info = self._proc_info()
            ret = (
                info[pinfo_map['io_rcount']],
                info[pinfo_map['io_wcount']],
                info[pinfo_map['io_rbytes']],
                info[pinfo_map['io_wbytes']],
                info[pinfo_map['io_count_others']],
                info[pinfo_map['io_bytes_others']],
            )
        return pio(*ret)

    @wrap_exceptions
    def status(self):
        suspended = cext.proc_is_suspended(self.pid)
        if suspended:
            return _common.STATUS_STOPPED
        else:
            return _common.STATUS_RUNNING

    @wrap_exceptions
    def cpu_affinity_get(self):
        def from_bitmask(x):
            return [i for i in range(64) if (1 << i) & x]

        bitmask = cext.proc_cpu_affinity_get(self.pid)
        return from_bitmask(bitmask)

    @wrap_exceptions
    def cpu_affinity_set(self, value):
        def to_bitmask(ls):
            if not ls:
                raise ValueError("invalid argument %r" % ls)
            out = 0
            for b in ls:
                out |= 2**b
            return out

        # SetProcessAffinityMask() states that ERROR_INVALID_PARAMETER
        # is returned for an invalid CPU but this seems not to be true,
        # therefore we check CPUs validy beforehand.
        allcpus = list(range(len(per_cpu_times())))
        for cpu in value:
            if cpu not in allcpus:
                if not isinstance(cpu, (int, long)):
                    raise TypeError(
                        "invalid CPU %r; an integer is required" % cpu
                    )
                else:
                    raise ValueError("invalid CPU %r" % cpu)

        bitmask = to_bitmask(value)
        cext.proc_cpu_affinity_set(self.pid, bitmask)

    @wrap_exceptions
    def num_handles(self):
        try:
            return cext.proc_num_handles(self.pid)
        except OSError as err:
            if is_permission_err(err):
                return self._proc_info()[pinfo_map['num_handles']]
            raise

    @wrap_exceptions
    def num_ctx_switches(self):
        ctx_switches = self._proc_info()[pinfo_map['ctx_switches']]
        # only voluntary ctx switches are supported
        return _common.pctxsw(ctx_switches, 0)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\services\generative_service\transports\rest.py ===
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

import dataclasses
import json  # type: ignore
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, path_template, rest_helpers, rest_streaming
from google.api_core import exceptions as core_exceptions
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.auth.transport.requests import AuthorizedSession  # type: ignore
from google.protobuf import json_format
import grpc  # type: ignore
from requests import __version__ as requests_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore


from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1.types import generative_service

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import GenerativeServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class GenerativeServiceRestInterceptor:
    """Interceptor for GenerativeService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the GenerativeServiceRestTransport.

    .. code-block:: python
        class MyCustomGenerativeServiceInterceptor(GenerativeServiceRestInterceptor):
            def pre_batch_embed_contents(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_batch_embed_contents(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_count_tokens(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_count_tokens(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_embed_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_embed_content(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_generate_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_generate_content(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_stream_generate_content(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_stream_generate_content(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = GenerativeServiceRestTransport(interceptor=MyCustomGenerativeServiceInterceptor())
        client = GenerativeServiceClient(transport=transport)


    """

    def pre_batch_embed_contents(
        self,
        request: generative_service.BatchEmbedContentsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[generative_service.BatchEmbedContentsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for batch_embed_contents

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_batch_embed_contents(
        self, response: generative_service.BatchEmbedContentsResponse
    ) -> generative_service.BatchEmbedContentsResponse:
        """Post-rpc interceptor for batch_embed_contents

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response

    def pre_count_tokens(
        self,
        request: generative_service.CountTokensRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[generative_service.CountTokensRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for count_tokens

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_count_tokens(
        self, response: generative_service.CountTokensResponse
    ) -> generative_service.CountTokensResponse:
        """Post-rpc interceptor for count_tokens

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response

    def pre_embed_content(
        self,
        request: generative_service.EmbedContentRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[generative_service.EmbedContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for embed_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_embed_content(
        self, response: generative_service.EmbedContentResponse
    ) -> generative_service.EmbedContentResponse:
        """Post-rpc interceptor for embed_content

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response

    def pre_generate_content(
        self,
        request: generative_service.GenerateContentRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[generative_service.GenerateContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for generate_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_generate_content(
        self, response: generative_service.GenerateContentResponse
    ) -> generative_service.GenerateContentResponse:
        """Post-rpc interceptor for generate_content

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response

    def pre_stream_generate_content(
        self,
        request: generative_service.GenerateContentRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[generative_service.GenerateContentRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for stream_generate_content

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_stream_generate_content(
        self, response: rest_streaming.ResponseIterator
    ) -> rest_streaming.ResponseIterator:
        """Post-rpc interceptor for stream_generate_content

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response

    def pre_cancel_operation(
        self,
        request: operations_pb2.CancelOperationRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[operations_pb2.CancelOperationRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for cancel_operation

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_cancel_operation(self, response: None) -> None:
        """Post-rpc interceptor for cancel_operation

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response

    def pre_get_operation(
        self,
        request: operations_pb2.GetOperationRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[operations_pb2.GetOperationRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for get_operation

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_get_operation(
        self, response: operations_pb2.Operation
    ) -> operations_pb2.Operation:
        """Post-rpc interceptor for get_operation

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response

    def pre_list_operations(
        self,
        request: operations_pb2.ListOperationsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[operations_pb2.ListOperationsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for list_operations

        Override in a subclass to manipulate the request or metadata
        before they are sent to the GenerativeService server.
        """
        return request, metadata

    def post_list_operations(
        self, response: operations_pb2.ListOperationsResponse
    ) -> operations_pb2.ListOperationsResponse:
        """Post-rpc interceptor for list_operations

        Override in a subclass to manipulate the response
        after it is returned by the GenerativeService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class GenerativeServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: GenerativeServiceRestInterceptor


class GenerativeServiceRestTransport(GenerativeServiceTransport):
    """REST backend transport for GenerativeService.

    API for using Large Models that generate multimodal content
    and have additional capabilities beyond text generation.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1

    """

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme: str = "https",
        interceptor: Optional[GenerativeServiceRestInterceptor] = None,
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

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you are developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(
                f"Unexpected hostname structure: {host}"
            )  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST
        )
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        self._interceptor = interceptor or GenerativeServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _BatchEmbedContents(GenerativeServiceRestStub):
        def __hash__(self):
            return hash("BatchEmbedContents")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: generative_service.BatchEmbedContentsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> generative_service.BatchEmbedContentsResponse:
            r"""Call the batch embed contents method over HTTP.

            Args:
                request (~.generative_service.BatchEmbedContentsRequest):
                    The request object. Batch request to get embeddings from
                the model for a list of prompts.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.generative_service.BatchEmbedContentsResponse:
                    The response to a ``BatchEmbedContentsRequest``.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1/{model=models/*}:batchEmbedContents",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_batch_embed_contents(
                request, metadata
            )
            pb_request = generative_service.BatchEmbedContentsRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = generative_service.BatchEmbedContentsResponse()
            pb_resp = generative_service.BatchEmbedContentsResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_batch_embed_contents(resp)
            return resp

    class _CountTokens(GenerativeServiceRestStub):
        def __hash__(self):
            return hash("CountTokens")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: generative_service.CountTokensRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> generative_service.CountTokensResponse:
            r"""Call the count tokens method over HTTP.

            Args:
                request (~.generative_service.CountTokensRequest):
                    The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.generative_service.CountTokensResponse:
                    A response from ``CountTokens``.

                It returns the model's ``token_count`` for the
                ``prompt``.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1/{model=models/*}:countTokens",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_count_tokens(request, metadata)
            pb_request = generative_service.CountTokensRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = generative_service.CountTokensResponse()
            pb_resp = generative_service.CountTokensResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_count_tokens(resp)
            return resp

    class _EmbedContent(GenerativeServiceRestStub):
        def __hash__(self):
            return hash("EmbedContent")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: generative_service.EmbedContentRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> generative_service.EmbedContentResponse:
            r"""Call the embed content method over HTTP.

            Args:
                request (~.generative_service.EmbedContentRequest):
                    The request object. Request containing the ``Content`` for the model to
                embed.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.generative_service.EmbedContentResponse:
                    The response to an ``EmbedContentRequest``.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1/{model=models/*}:embedContent",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_embed_content(request, metadata)
            pb_request = generative_service.EmbedContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = generative_service.EmbedContentResponse()
            pb_resp = generative_service.EmbedContentResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_embed_content(resp)
            return resp

    class _GenerateContent(GenerativeServiceRestStub):
        def __hash__(self):
            return hash("GenerateContent")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: generative_service.GenerateContentRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> generative_service.GenerateContentResponse:
            r"""Call the generate content method over HTTP.

            Args:
                request (~.generative_service.GenerateContentRequest):
                    The request object. Request to generate a completion from
                the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.generative_service.GenerateContentResponse:
                    Response from the model supporting multiple candidates.

                Note on safety ratings and content filtering. They are
                reported for both prompt in
                ``GenerateContentResponse.prompt_feedback`` and for each
                candidate in ``finish_reason`` and in
                ``safety_ratings``. The API contract is that:

                -  either all requested candidates are returned or no
                   candidates at all
                -  no candidates are returned only if there was
                   something wrong with the prompt (see
                   ``prompt_feedback``)
                -  feedback on each candidate is reported on
                   ``finish_reason`` and ``safety_ratings``.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1/{model=models/*}:generateContent",
                    "body": "*",
                },
                {
                    "method": "post",
                    "uri": "/v1/{model=tunedModels/*}:generateContent",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_generate_content(
                request, metadata
            )
            pb_request = generative_service.GenerateContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = generative_service.GenerateContentResponse()
            pb_resp = generative_service.GenerateContentResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_generate_content(resp)
            return resp

    class _StreamGenerateContent(GenerativeServiceRestStub):
        def __hash__(self):
            return hash("StreamGenerateContent")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: generative_service.GenerateContentRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> rest_streaming.ResponseIterator:
            r"""Call the stream generate content method over HTTP.

            Args:
                request (~.generative_service.GenerateContentRequest):
                    The request object. Request to generate a completion from
                the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.generative_service.GenerateContentResponse:
                    Response from the model supporting multiple candidates.

                Note on safety ratings and content filtering. They are
                reported for both prompt in
                ``GenerateContentResponse.prompt_feedback`` and for each
                candidate in ``finish_reason`` and in
                ``safety_ratings``. The API contract is that:

                -  either all requested candidates are returned or no
                   candidates at all
                -  no candidates are returned only if there was
                   something wrong with the prompt (see
                   ``prompt_feedback``)
                -  feedback on each candidate is reported on
                   ``finish_reason`` and ``safety_ratings``.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1/{model=models/*}:streamGenerateContent",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_stream_generate_content(
                request, metadata
            )
            pb_request = generative_service.GenerateContentRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = rest_streaming.ResponseIterator(
                response, generative_service.GenerateContentResponse
            )
            resp = self._interceptor.post_stream_generate_content(resp)
            return resp

    @property
    def batch_embed_contents(
        self,
    ) -> Callable[
        [generative_service.BatchEmbedContentsRequest],
        generative_service.BatchEmbedContentsResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._BatchEmbedContents(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def count_tokens(
        self,
    ) -> Callable[
        [generative_service.CountTokensRequest], generative_service.CountTokensResponse
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CountTokens(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def embed_content(
        self,
    ) -> Callable[
        [generative_service.EmbedContentRequest],
        generative_service.EmbedContentResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._EmbedContent(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def generate_content(
        self,
    ) -> Callable[
        [generative_service.GenerateContentRequest],
        generative_service.GenerateContentResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GenerateContent(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def stream_generate_content(
        self,
    ) -> Callable[
        [generative_service.GenerateContentRequest],
        generative_service.GenerateContentResponse,
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._StreamGenerateContent(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def cancel_operation(self):
        return self._CancelOperation(self._session, self._host, self._interceptor)  # type: ignore

    class _CancelOperation(GenerativeServiceRestStub):
        def __call__(
            self,
            request: operations_pb2.CancelOperationRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> None:
            r"""Call the cancel operation method over HTTP.

            Args:
                request (operations_pb2.CancelOperationRequest):
                    The request object for CancelOperation method.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1/{name=tunedModels/*/operations/*}:cancel",
                    "body": "*",
                },
            ]

            request, metadata = self._interceptor.pre_cancel_operation(
                request, metadata
            )
            request_kwargs = json_format.MessageToDict(request)
            transcoded_request = path_template.transcode(http_options, **request_kwargs)

            body = json.dumps(transcoded_request["body"])
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(json.dumps(transcoded_request["query_params"]))

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"

            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            return self._interceptor.post_cancel_operation(None)

    @property
    def get_operation(self):
        return self._GetOperation(self._session, self._host, self._interceptor)  # type: ignore

    class _GetOperation(GenerativeServiceRestStub):
        def __call__(
            self,
            request: operations_pb2.GetOperationRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> operations_pb2.Operation:
            r"""Call the get operation method over HTTP.

            Args:
                request (operations_pb2.GetOperationRequest):
                    The request object for GetOperation method.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                operations_pb2.Operation: Response from GetOperation method.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1/{name=tunedModels/*/operations/*}",
                },
            ]

            request, metadata = self._interceptor.pre_get_operation(request, metadata)
            request_kwargs = json_format.MessageToDict(request)
            transcoded_request = path_template.transcode(http_options, **request_kwargs)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(json.dumps(transcoded_request["query_params"]))

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"

            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            resp = operations_pb2.Operation()
            resp = json_format.Parse(response.content.decode("utf-8"), resp)
            resp = self._interceptor.post_get_operation(resp)
            return resp

    @property
    def list_operations(self):
        return self._ListOperations(self._session, self._host, self._interceptor)  # type: ignore

    class _ListOperations(GenerativeServiceRestStub):
        def __call__(
            self,
            request: operations_pb2.ListOperationsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> operations_pb2.ListOperationsResponse:
            r"""Call the list operations method over HTTP.

            Args:
                request (operations_pb2.ListOperationsRequest):
                    The request object for ListOperations method.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                operations_pb2.ListOperationsResponse: Response from ListOperations method.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1/{name=operations}",
                },
                {
                    "method": "get",
                    "uri": "/v1/{name=tunedModels/*}/operations",
                },
            ]

            request, metadata = self._interceptor.pre_list_operations(request, metadata)
            request_kwargs = json_format.MessageToDict(request)
            transcoded_request = path_template.transcode(http_options, **request_kwargs)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(json.dumps(transcoded_request["query_params"]))

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"

            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            resp = operations_pb2.ListOperationsResponse()
            resp = json_format.Parse(response.content.decode("utf-8"), resp)
            resp = self._interceptor.post_list_operations(resp)
            return resp

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("GenerativeServiceRestTransport",)