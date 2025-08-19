
# === NexusCore/tools\exports\export_20250803_114325\combined_192.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\_experimental\mcp_server\mcp_server_manager.py ===
"""
MCP Client Manager

This class is responsible for managing MCP clients with support for both SSE and HTTP streamable transports.

This is a Proxy
"""

import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional, cast

from mcp.types import CallToolRequestParams as MCPCallToolRequestParams
from mcp.types import CallToolResult
from mcp.types import Tool as MCPTool

from litellm._logging import verbose_logger
from litellm.experimental_mcp_client.client import MCPClient
from litellm.proxy._experimental.mcp_server.auth.user_api_key_auth_mcp import (
    UserAPIKeyAuthMCP,
)
from litellm.proxy._types import (
    LiteLLM_MCPServerTable,
    MCPAuthType,
    MCPSpecVersion,
    MCPSpecVersionType,
    MCPTransport,
    MCPTransportType,
    UserAPIKeyAuth,
)
from litellm.types.mcp_server.mcp_server_manager import MCPInfo, MCPServer


class MCPServerManager:
    def __init__(self):
        self.registry: Dict[str, MCPServer] = {}
        self.config_mcp_servers: Dict[str, MCPServer] = {}
        """
        eg.
        [
            "server-1": {
                "name": "zapier_mcp_server",
                "url": "https://actions.zapier.com/mcp/sk-ak-2ew3bofIeQIkNoeKIdXrF1Hhhp/sse"
                "transport": "sse",
                "auth_type": "api_key",
                "spec_version": "2025-03-26"
            },
            "uuid-2": {
                "name": "google_drive_mcp_server",
                "url": "https://actions.zapier.com/mcp/sk-ak-2ew3bofIeQIkNoeKIdXrF1Hhhp/sse"
            }
        ]
        """

        self.tool_name_to_mcp_server_name_mapping: Dict[str, str] = {}
        """
        {
            "gmail_send_email": "zapier_mcp_server",
        }
        """

    def get_registry(self) -> Dict[str, MCPServer]:
        """
        Get the registered MCP Servers from the registry and union with the config MCP Servers
        """
        return self.config_mcp_servers | self.registry

    def load_servers_from_config(self, mcp_servers_config: Dict[str, Any]):
        """
        Load the MCP Servers from the config
        """
        verbose_logger.debug("Loading MCP Servers from config-----")
        for server_name, server_config in mcp_servers_config.items():
            _mcp_info: dict = server_config.get("mcp_info", None) or {}
            mcp_info = MCPInfo(**_mcp_info)
            mcp_info["server_name"] = server_name
            mcp_info["description"] = server_config.get("description", None)

            # Generate stable server ID based on parameters
            server_id = self._generate_stable_server_id(
                server_name=server_name,
                url=server_config["url"],
                transport=server_config.get("transport", MCPTransport.http),
                spec_version=server_config.get("spec_version", MCPSpecVersion.mar_2025),
                auth_type=server_config.get("auth_type", None),
            )

            new_server = MCPServer(
                server_id=server_id,
                name=server_name,
                url=server_config["url"],
                # TODO: utility fn the default values
                transport=server_config.get("transport", MCPTransport.http),
                spec_version=server_config.get("spec_version", MCPSpecVersion.mar_2025),
                auth_type=server_config.get("auth_type", None),
                mcp_info=mcp_info,
            )
            self.config_mcp_servers[server_id] = new_server
        verbose_logger.debug(
            f"Loaded MCP Servers: {json.dumps(self.config_mcp_servers, indent=4, default=str)}"
        )

        self.initialize_tool_name_to_mcp_server_name_mapping()

    def remove_server(self, mcp_server: LiteLLM_MCPServerTable):
        """
        Remove a server from the registry
        """
        if mcp_server.alias in self.get_registry():
            del self.registry[mcp_server.alias]
            verbose_logger.debug(f"Removed MCP Server: {mcp_server.alias}")
        elif mcp_server.server_id in self.get_registry():
            del self.registry[mcp_server.server_id]
            verbose_logger.debug(f"Removed MCP Server: {mcp_server.server_id}")
        else:
            verbose_logger.warning(
                f"Server ID {mcp_server.server_id} not found in registry"
            )

    def add_update_server(self, mcp_server: LiteLLM_MCPServerTable):
        if mcp_server.server_id not in self.get_registry():
            new_server = MCPServer(
                server_id=mcp_server.server_id,
                name=mcp_server.alias or mcp_server.server_id,
                url=mcp_server.url,
                transport=cast(MCPTransportType, mcp_server.transport),
                spec_version=cast(MCPSpecVersionType, mcp_server.spec_version),
                auth_type=cast(MCPAuthType, mcp_server.auth_type),
                mcp_info=MCPInfo(
                    server_name=mcp_server.alias or mcp_server.server_id,
                    description=mcp_server.description,
                ),
            )
            self.registry[mcp_server.server_id] = new_server
            verbose_logger.debug(
                f"Added MCP Server: {mcp_server.alias or mcp_server.server_id}"
            )

    async def get_allowed_mcp_servers(
        self, user_api_key_auth: Optional[UserAPIKeyAuth] = None
    ) -> List[str]:
        """
        Get the allowed MCP Servers for the user
        """
        allowed_mcp_servers = await UserAPIKeyAuthMCP.get_allowed_mcp_servers(
            user_api_key_auth
        )
        verbose_logger.debug(
            f"Allowed MCP Servers for user api key auth: {allowed_mcp_servers}"
        )
        if len(allowed_mcp_servers) > 0:
            return allowed_mcp_servers
        else:
            verbose_logger.debug(
                "No allowed MCP Servers found for user api key auth, returning default registry servers"
            )
            return list(self.get_registry().keys())

    async def list_tools(
        self, 
        user_api_key_auth: Optional[UserAPIKeyAuth] = None,
        mcp_auth_header: Optional[str] = None,
    ) -> List[MCPTool]:
        """
        List all tools available across all MCP Servers.

        Returns:
            List[MCPTool]: Combined list of tools from all servers
        """
        allowed_mcp_servers = await self.get_allowed_mcp_servers(user_api_key_auth)

        list_tools_result: List[MCPTool] = []
        verbose_logger.debug("SERVER MANAGER LISTING TOOLS")

        for server_id in allowed_mcp_servers:
            server = self.get_mcp_server_by_id(server_id)
            if server is None:
                verbose_logger.warning(f"MCP Server {server_id} not found")
                continue
            try:
                tools = await self._get_tools_from_server(
                    server=server,
                    mcp_auth_header=mcp_auth_header,
                )
                list_tools_result.extend(tools)
            except Exception as e:
                verbose_logger.exception(
                    f"Error listing tools from server {server.name}: {str(e)}"
                )

        return list_tools_result

    #########################################################
    # Methods that call the upstream MCP servers
    #########################################################
    def _create_mcp_client(self, server: MCPServer, mcp_auth_header: Optional[str] = None) -> MCPClient:
        """
        Create an MCPClient instance for the given server.

        Args:
            server (MCPServer): The server configuration
            mcp_auth_header: MCP auth header to be passed to the MCP server. This is optional and will be used if provided.

        Returns:
            MCPClient: Configured MCP client instance
        """
        transport = server.transport or MCPTransport.sse
        return MCPClient(
            server_url=server.url,
            transport_type=transport,
            auth_type=server.auth_type,
            auth_value=mcp_auth_header or server.authentication_token,
            timeout=60.0,
        )

    async def _get_tools_from_server(self, server: MCPServer, mcp_auth_header: Optional[str] = None) -> List[MCPTool]:
        """
        Helper method to get tools from a single MCP server.

        Args:
            server (MCPServer): The server to query tools from

        Returns:
            List[MCPTool]: List of tools available on the server
        """
        verbose_logger.debug(f"Connecting to url: {server.url}")
        verbose_logger.info("_get_tools_from_server...")

        client = self._create_mcp_client(
            server=server,
            mcp_auth_header=mcp_auth_header,
        )
        async with client:
            tools = await client.list_tools()
            verbose_logger.debug(f"Tools from {server.name}: {tools}")

            # Update tool to server mapping
            for tool in tools:
                self.tool_name_to_mcp_server_name_mapping[tool.name] = server.name

            return tools
    
    async def call_tool(
        self, 
        name: str, 
        arguments: Dict[str, Any],
        user_api_key_auth: Optional[UserAPIKeyAuth] = None,
        mcp_auth_header: Optional[str] = None,
    ) -> CallToolResult:
        """
        Call a tool with the given name and arguments
        """
        mcp_server = self._get_mcp_server_from_tool_name(name)
        if mcp_server is None:
            raise ValueError(f"Tool {name} not found")

        client = self._create_mcp_client(
            server=mcp_server,
            mcp_auth_header=mcp_auth_header,
        )
        async with client:
            call_tool_params = MCPCallToolRequestParams(
                name=name,
                arguments=arguments,
            )
            return await client.call_tool(call_tool_params)
    
    #########################################################
    # End of Methods that call the upstream MCP servers
    #########################################################


    def initialize_tool_name_to_mcp_server_name_mapping(self):
        """
        On startup, initialize the tool name to MCP server name mapping
        """
        try:
            if asyncio.get_running_loop():
                asyncio.create_task(
                    self._initialize_tool_name_to_mcp_server_name_mapping()
                )
        except RuntimeError as e:  # no running event loop
            verbose_logger.exception(
                f"No running event loop - skipping tool name to MCP server name mapping initialization: {str(e)}"
            )

    async def _initialize_tool_name_to_mcp_server_name_mapping(self):
        """
        Call list_tools for each server and update the tool name to MCP server name mapping
        """
        for server in self.get_registry().values():
            tools = await self._get_tools_from_server(server)
            for tool in tools:
                self.tool_name_to_mcp_server_name_mapping[tool.name] = server.name

    def _get_mcp_server_from_tool_name(self, tool_name: str) -> Optional[MCPServer]:
        """
        Get the MCP Server from the tool name
        """
        if tool_name in self.tool_name_to_mcp_server_name_mapping:
            for server in self.get_registry().values():
                if server.name == self.tool_name_to_mcp_server_name_mapping[tool_name]:
                    return server
        return None

    async def _add_mcp_servers_from_db_to_in_memory_registry(self):
        from litellm.proxy._experimental.mcp_server.db import get_all_mcp_servers
        from litellm.proxy.management_endpoints.mcp_management_endpoints import (
            get_prisma_client_or_throw,
        )

        # perform authz check to filter the mcp servers user has access to
        prisma_client = get_prisma_client_or_throw(
            "Database not connected. Connect a database to your proxy"
        )
        db_mcp_servers = await get_all_mcp_servers(prisma_client)
        # ensure the global_mcp_server_manager is up to date with the db
        for server in db_mcp_servers:
            self.add_update_server(server)

    def get_mcp_server_by_id(self, server_id: str) -> Optional[MCPServer]:
        """
        Get the MCP Server from the server id
        """
        for server in self.get_registry().values():
            if server.server_id == server_id:
                return server
        return None

    def _generate_stable_server_id(
        self,
        server_name: str,
        url: str,
        transport: str,
        spec_version: str,
        auth_type: Optional[str] = None,
    ) -> str:
        """
        Generate a stable server ID based on server parameters using a hash function.

        This is critical to ensure the server_id is stable across server restarts.
        Some users store MCPs on the config.yaml and permission management is based on server_ids.

        Eg a key might have mcp_servers = ["1234"], if the server_id changes across restarts, the key will no longer have access to the MCP.

        Args:
            server_name: Name of the server
            url: Server URL
            transport: Transport type (sse, http, etc.)
            spec_version: MCP spec version
            auth_type: Authentication type (optional)

        Returns:
            A deterministic server ID string
        """
        # Create a string from all the identifying parameters
        params_string = (
            f"{server_name}|{url}|{transport}|{spec_version}|{auth_type or ''}"
        )

        # Generate SHA-256 hash
        hash_object = hashlib.sha256(params_string.encode("utf-8"))
        hash_hex = hash_object.hexdigest()

        # Take first 32 characters and format as UUID-like string
        return hash_hex[:32]


global_mcp_server_manager: MCPServerManager = MCPServerManager()

# === NexusCore/openenv\Lib\site-packages\openai\types\evals\run_cancel_response.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Dict, List, Union, Optional
from typing_extensions import Literal, Annotated, TypeAlias

from pydantic import Field as FieldInfo

from ..._utils import PropertyInfo
from ..._models import BaseModel
from .eval_api_error import EvalAPIError
from ..responses.tool import Tool
from ..shared.metadata import Metadata
from ..shared.reasoning_effort import ReasoningEffort
from ..responses.response_input_text import ResponseInputText
from .create_eval_jsonl_run_data_source import CreateEvalJSONLRunDataSource
from ..responses.response_format_text_config import ResponseFormatTextConfig
from .create_eval_completions_run_data_source import CreateEvalCompletionsRunDataSource

__all__ = [
    "RunCancelResponse",
    "DataSource",
    "DataSourceResponses",
    "DataSourceResponsesSource",
    "DataSourceResponsesSourceFileContent",
    "DataSourceResponsesSourceFileContentContent",
    "DataSourceResponsesSourceFileID",
    "DataSourceResponsesSourceResponses",
    "DataSourceResponsesInputMessages",
    "DataSourceResponsesInputMessagesTemplate",
    "DataSourceResponsesInputMessagesTemplateTemplate",
    "DataSourceResponsesInputMessagesTemplateTemplateChatMessage",
    "DataSourceResponsesInputMessagesTemplateTemplateEvalItem",
    "DataSourceResponsesInputMessagesTemplateTemplateEvalItemContent",
    "DataSourceResponsesInputMessagesTemplateTemplateEvalItemContentOutputText",
    "DataSourceResponsesInputMessagesItemReference",
    "DataSourceResponsesSamplingParams",
    "DataSourceResponsesSamplingParamsText",
    "PerModelUsage",
    "PerTestingCriteriaResult",
    "ResultCounts",
]


class DataSourceResponsesSourceFileContentContent(BaseModel):
    item: Dict[str, object]

    sample: Optional[Dict[str, object]] = None


class DataSourceResponsesSourceFileContent(BaseModel):
    content: List[DataSourceResponsesSourceFileContentContent]
    """The content of the jsonl file."""

    type: Literal["file_content"]
    """The type of jsonl source. Always `file_content`."""


class DataSourceResponsesSourceFileID(BaseModel):
    id: str
    """The identifier of the file."""

    type: Literal["file_id"]
    """The type of jsonl source. Always `file_id`."""


class DataSourceResponsesSourceResponses(BaseModel):
    type: Literal["responses"]
    """The type of run data source. Always `responses`."""

    created_after: Optional[int] = None
    """Only include items created after this timestamp (inclusive).

    This is a query parameter used to select responses.
    """

    created_before: Optional[int] = None
    """Only include items created before this timestamp (inclusive).

    This is a query parameter used to select responses.
    """

    instructions_search: Optional[str] = None
    """Optional string to search the 'instructions' field.

    This is a query parameter used to select responses.
    """

    metadata: Optional[object] = None
    """Metadata filter for the responses.

    This is a query parameter used to select responses.
    """

    model: Optional[str] = None
    """The name of the model to find responses for.

    This is a query parameter used to select responses.
    """

    reasoning_effort: Optional[ReasoningEffort] = None
    """Optional reasoning effort parameter.

    This is a query parameter used to select responses.
    """

    temperature: Optional[float] = None
    """Sampling temperature. This is a query parameter used to select responses."""

    tools: Optional[List[str]] = None
    """List of tool names. This is a query parameter used to select responses."""

    top_p: Optional[float] = None
    """Nucleus sampling parameter. This is a query parameter used to select responses."""

    users: Optional[List[str]] = None
    """List of user identifiers. This is a query parameter used to select responses."""


DataSourceResponsesSource: TypeAlias = Annotated[
    Union[DataSourceResponsesSourceFileContent, DataSourceResponsesSourceFileID, DataSourceResponsesSourceResponses],
    PropertyInfo(discriminator="type"),
]


class DataSourceResponsesInputMessagesTemplateTemplateChatMessage(BaseModel):
    content: str
    """The content of the message."""

    role: str
    """The role of the message (e.g. "system", "assistant", "user")."""


class DataSourceResponsesInputMessagesTemplateTemplateEvalItemContentOutputText(BaseModel):
    text: str
    """The text output from the model."""

    type: Literal["output_text"]
    """The type of the output text. Always `output_text`."""


DataSourceResponsesInputMessagesTemplateTemplateEvalItemContent: TypeAlias = Union[
    str, ResponseInputText, DataSourceResponsesInputMessagesTemplateTemplateEvalItemContentOutputText
]


class DataSourceResponsesInputMessagesTemplateTemplateEvalItem(BaseModel):
    content: DataSourceResponsesInputMessagesTemplateTemplateEvalItemContent
    """Text inputs to the model - can contain template strings."""

    role: Literal["user", "assistant", "system", "developer"]
    """The role of the message input.

    One of `user`, `assistant`, `system`, or `developer`.
    """

    type: Optional[Literal["message"]] = None
    """The type of the message input. Always `message`."""


DataSourceResponsesInputMessagesTemplateTemplate: TypeAlias = Union[
    DataSourceResponsesInputMessagesTemplateTemplateChatMessage,
    DataSourceResponsesInputMessagesTemplateTemplateEvalItem,
]


class DataSourceResponsesInputMessagesTemplate(BaseModel):
    template: List[DataSourceResponsesInputMessagesTemplateTemplate]
    """A list of chat messages forming the prompt or context.

    May include variable references to the `item` namespace, ie {{item.name}}.
    """

    type: Literal["template"]
    """The type of input messages. Always `template`."""


class DataSourceResponsesInputMessagesItemReference(BaseModel):
    item_reference: str
    """A reference to a variable in the `item` namespace. Ie, "item.name" """

    type: Literal["item_reference"]
    """The type of input messages. Always `item_reference`."""


DataSourceResponsesInputMessages: TypeAlias = Annotated[
    Union[DataSourceResponsesInputMessagesTemplate, DataSourceResponsesInputMessagesItemReference],
    PropertyInfo(discriminator="type"),
]


class DataSourceResponsesSamplingParamsText(BaseModel):
    format: Optional[ResponseFormatTextConfig] = None
    """An object specifying the format that the model must output.

    Configuring `{ "type": "json_schema" }` enables Structured Outputs, which
    ensures the model will match your supplied JSON schema. Learn more in the
    [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

    The default format is `{ "type": "text" }` with no additional options.

    **Not recommended for gpt-4o and newer models:**

    Setting to `{ "type": "json_object" }` enables the older JSON mode, which
    ensures the message the model generates is valid JSON. Using `json_schema` is
    preferred for models that support it.
    """


class DataSourceResponsesSamplingParams(BaseModel):
    max_completion_tokens: Optional[int] = None
    """The maximum number of tokens in the generated output."""

    seed: Optional[int] = None
    """A seed value to initialize the randomness, during sampling."""

    temperature: Optional[float] = None
    """A higher temperature increases randomness in the outputs."""

    text: Optional[DataSourceResponsesSamplingParamsText] = None
    """Configuration options for a text response from the model.

    Can be plain text or structured JSON data. Learn more:

    - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
    - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
    """

    tools: Optional[List[Tool]] = None
    """An array of tools the model may call while generating a response.

    You can specify which tool to use by setting the `tool_choice` parameter.

    The two categories of tools you can provide the model are:

    - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
      capabilities, like
      [web search](https://platform.openai.com/docs/guides/tools-web-search) or
      [file search](https://platform.openai.com/docs/guides/tools-file-search).
      Learn more about
      [built-in tools](https://platform.openai.com/docs/guides/tools).
    - **Function calls (custom tools)**: Functions that are defined by you, enabling
      the model to call your own code. Learn more about
      [function calling](https://platform.openai.com/docs/guides/function-calling).
    """

    top_p: Optional[float] = None
    """An alternative to temperature for nucleus sampling; 1.0 includes all tokens."""


class DataSourceResponses(BaseModel):
    source: DataSourceResponsesSource
    """Determines what populates the `item` namespace in this run's data source."""

    type: Literal["responses"]
    """The type of run data source. Always `responses`."""

    input_messages: Optional[DataSourceResponsesInputMessages] = None
    """Used when sampling from a model.

    Dictates the structure of the messages passed into the model. Can either be a
    reference to a prebuilt trajectory (ie, `item.input_trajectory`), or a template
    with variable references to the `item` namespace.
    """

    model: Optional[str] = None
    """The name of the model to use for generating completions (e.g. "o3-mini")."""

    sampling_params: Optional[DataSourceResponsesSamplingParams] = None


DataSource: TypeAlias = Annotated[
    Union[CreateEvalJSONLRunDataSource, CreateEvalCompletionsRunDataSource, DataSourceResponses],
    PropertyInfo(discriminator="type"),
]


class PerModelUsage(BaseModel):
    cached_tokens: int
    """The number of tokens retrieved from cache."""

    completion_tokens: int
    """The number of completion tokens generated."""

    invocation_count: int
    """The number of invocations."""

    run_model_name: str = FieldInfo(alias="model_name")
    """The name of the model."""

    prompt_tokens: int
    """The number of prompt tokens used."""

    total_tokens: int
    """The total number of tokens used."""


class PerTestingCriteriaResult(BaseModel):
    failed: int
    """Number of tests failed for this criteria."""

    passed: int
    """Number of tests passed for this criteria."""

    testing_criteria: str
    """A description of the testing criteria."""


class ResultCounts(BaseModel):
    errored: int
    """Number of output items that resulted in an error."""

    failed: int
    """Number of output items that failed to pass the evaluation."""

    passed: int
    """Number of output items that passed the evaluation."""

    total: int
    """Total number of executed output items."""


class RunCancelResponse(BaseModel):
    id: str
    """Unique identifier for the evaluation run."""

    created_at: int
    """Unix timestamp (in seconds) when the evaluation run was created."""

    data_source: DataSource
    """Information about the run's data source."""

    error: EvalAPIError
    """An object representing an error response from the Eval API."""

    eval_id: str
    """The identifier of the associated evaluation."""

    metadata: Optional[Metadata] = None
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    model: str
    """The model that is evaluated, if applicable."""

    name: str
    """The name of the evaluation run."""

    object: Literal["eval.run"]
    """The type of the object. Always "eval.run"."""

    per_model_usage: List[PerModelUsage]
    """Usage statistics for each model during the evaluation run."""

    per_testing_criteria_results: List[PerTestingCriteriaResult]
    """Results per testing criteria applied during the evaluation run."""

    report_url: str
    """The URL to the rendered evaluation run report on the UI dashboard."""

    result_counts: ResultCounts
    """Counters summarizing the outcomes of the evaluation run."""

    status: str
    """The status of the evaluation run."""

# === NexusCore/openenv\Lib\site-packages\openai\types\evals\run_create_response.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Dict, List, Union, Optional
from typing_extensions import Literal, Annotated, TypeAlias

from pydantic import Field as FieldInfo

from ..._utils import PropertyInfo
from ..._models import BaseModel
from .eval_api_error import EvalAPIError
from ..responses.tool import Tool
from ..shared.metadata import Metadata
from ..shared.reasoning_effort import ReasoningEffort
from ..responses.response_input_text import ResponseInputText
from .create_eval_jsonl_run_data_source import CreateEvalJSONLRunDataSource
from ..responses.response_format_text_config import ResponseFormatTextConfig
from .create_eval_completions_run_data_source import CreateEvalCompletionsRunDataSource

__all__ = [
    "RunCreateResponse",
    "DataSource",
    "DataSourceResponses",
    "DataSourceResponsesSource",
    "DataSourceResponsesSourceFileContent",
    "DataSourceResponsesSourceFileContentContent",
    "DataSourceResponsesSourceFileID",
    "DataSourceResponsesSourceResponses",
    "DataSourceResponsesInputMessages",
    "DataSourceResponsesInputMessagesTemplate",
    "DataSourceResponsesInputMessagesTemplateTemplate",
    "DataSourceResponsesInputMessagesTemplateTemplateChatMessage",
    "DataSourceResponsesInputMessagesTemplateTemplateEvalItem",
    "DataSourceResponsesInputMessagesTemplateTemplateEvalItemContent",
    "DataSourceResponsesInputMessagesTemplateTemplateEvalItemContentOutputText",
    "DataSourceResponsesInputMessagesItemReference",
    "DataSourceResponsesSamplingParams",
    "DataSourceResponsesSamplingParamsText",
    "PerModelUsage",
    "PerTestingCriteriaResult",
    "ResultCounts",
]


class DataSourceResponsesSourceFileContentContent(BaseModel):
    item: Dict[str, object]

    sample: Optional[Dict[str, object]] = None


class DataSourceResponsesSourceFileContent(BaseModel):
    content: List[DataSourceResponsesSourceFileContentContent]
    """The content of the jsonl file."""

    type: Literal["file_content"]
    """The type of jsonl source. Always `file_content`."""


class DataSourceResponsesSourceFileID(BaseModel):
    id: str
    """The identifier of the file."""

    type: Literal["file_id"]
    """The type of jsonl source. Always `file_id`."""


class DataSourceResponsesSourceResponses(BaseModel):
    type: Literal["responses"]
    """The type of run data source. Always `responses`."""

    created_after: Optional[int] = None
    """Only include items created after this timestamp (inclusive).

    This is a query parameter used to select responses.
    """

    created_before: Optional[int] = None
    """Only include items created before this timestamp (inclusive).

    This is a query parameter used to select responses.
    """

    instructions_search: Optional[str] = None
    """Optional string to search the 'instructions' field.

    This is a query parameter used to select responses.
    """

    metadata: Optional[object] = None
    """Metadata filter for the responses.

    This is a query parameter used to select responses.
    """

    model: Optional[str] = None
    """The name of the model to find responses for.

    This is a query parameter used to select responses.
    """

    reasoning_effort: Optional[ReasoningEffort] = None
    """Optional reasoning effort parameter.

    This is a query parameter used to select responses.
    """

    temperature: Optional[float] = None
    """Sampling temperature. This is a query parameter used to select responses."""

    tools: Optional[List[str]] = None
    """List of tool names. This is a query parameter used to select responses."""

    top_p: Optional[float] = None
    """Nucleus sampling parameter. This is a query parameter used to select responses."""

    users: Optional[List[str]] = None
    """List of user identifiers. This is a query parameter used to select responses."""


DataSourceResponsesSource: TypeAlias = Annotated[
    Union[DataSourceResponsesSourceFileContent, DataSourceResponsesSourceFileID, DataSourceResponsesSourceResponses],
    PropertyInfo(discriminator="type"),
]


class DataSourceResponsesInputMessagesTemplateTemplateChatMessage(BaseModel):
    content: str
    """The content of the message."""

    role: str
    """The role of the message (e.g. "system", "assistant", "user")."""


class DataSourceResponsesInputMessagesTemplateTemplateEvalItemContentOutputText(BaseModel):
    text: str
    """The text output from the model."""

    type: Literal["output_text"]
    """The type of the output text. Always `output_text`."""


DataSourceResponsesInputMessagesTemplateTemplateEvalItemContent: TypeAlias = Union[
    str, ResponseInputText, DataSourceResponsesInputMessagesTemplateTemplateEvalItemContentOutputText
]


class DataSourceResponsesInputMessagesTemplateTemplateEvalItem(BaseModel):
    content: DataSourceResponsesInputMessagesTemplateTemplateEvalItemContent
    """Text inputs to the model - can contain template strings."""

    role: Literal["user", "assistant", "system", "developer"]
    """The role of the message input.

    One of `user`, `assistant`, `system`, or `developer`.
    """

    type: Optional[Literal["message"]] = None
    """The type of the message input. Always `message`."""


DataSourceResponsesInputMessagesTemplateTemplate: TypeAlias = Union[
    DataSourceResponsesInputMessagesTemplateTemplateChatMessage,
    DataSourceResponsesInputMessagesTemplateTemplateEvalItem,
]


class DataSourceResponsesInputMessagesTemplate(BaseModel):
    template: List[DataSourceResponsesInputMessagesTemplateTemplate]
    """A list of chat messages forming the prompt or context.

    May include variable references to the `item` namespace, ie {{item.name}}.
    """

    type: Literal["template"]
    """The type of input messages. Always `template`."""


class DataSourceResponsesInputMessagesItemReference(BaseModel):
    item_reference: str
    """A reference to a variable in the `item` namespace. Ie, "item.name" """

    type: Literal["item_reference"]
    """The type of input messages. Always `item_reference`."""


DataSourceResponsesInputMessages: TypeAlias = Annotated[
    Union[DataSourceResponsesInputMessagesTemplate, DataSourceResponsesInputMessagesItemReference],
    PropertyInfo(discriminator="type"),
]


class DataSourceResponsesSamplingParamsText(BaseModel):
    format: Optional[ResponseFormatTextConfig] = None
    """An object specifying the format that the model must output.

    Configuring `{ "type": "json_schema" }` enables Structured Outputs, which
    ensures the model will match your supplied JSON schema. Learn more in the
    [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

    The default format is `{ "type": "text" }` with no additional options.

    **Not recommended for gpt-4o and newer models:**

    Setting to `{ "type": "json_object" }` enables the older JSON mode, which
    ensures the message the model generates is valid JSON. Using `json_schema` is
    preferred for models that support it.
    """


class DataSourceResponsesSamplingParams(BaseModel):
    max_completion_tokens: Optional[int] = None
    """The maximum number of tokens in the generated output."""

    seed: Optional[int] = None
    """A seed value to initialize the randomness, during sampling."""

    temperature: Optional[float] = None
    """A higher temperature increases randomness in the outputs."""

    text: Optional[DataSourceResponsesSamplingParamsText] = None
    """Configuration options for a text response from the model.

    Can be plain text or structured JSON data. Learn more:

    - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
    - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
    """

    tools: Optional[List[Tool]] = None
    """An array of tools the model may call while generating a response.

    You can specify which tool to use by setting the `tool_choice` parameter.

    The two categories of tools you can provide the model are:

    - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
      capabilities, like
      [web search](https://platform.openai.com/docs/guides/tools-web-search) or
      [file search](https://platform.openai.com/docs/guides/tools-file-search).
      Learn more about
      [built-in tools](https://platform.openai.com/docs/guides/tools).
    - **Function calls (custom tools)**: Functions that are defined by you, enabling
      the model to call your own code. Learn more about
      [function calling](https://platform.openai.com/docs/guides/function-calling).
    """

    top_p: Optional[float] = None
    """An alternative to temperature for nucleus sampling; 1.0 includes all tokens."""


class DataSourceResponses(BaseModel):
    source: DataSourceResponsesSource
    """Determines what populates the `item` namespace in this run's data source."""

    type: Literal["responses"]
    """The type of run data source. Always `responses`."""

    input_messages: Optional[DataSourceResponsesInputMessages] = None
    """Used when sampling from a model.

    Dictates the structure of the messages passed into the model. Can either be a
    reference to a prebuilt trajectory (ie, `item.input_trajectory`), or a template
    with variable references to the `item` namespace.
    """

    model: Optional[str] = None
    """The name of the model to use for generating completions (e.g. "o3-mini")."""

    sampling_params: Optional[DataSourceResponsesSamplingParams] = None


DataSource: TypeAlias = Annotated[
    Union[CreateEvalJSONLRunDataSource, CreateEvalCompletionsRunDataSource, DataSourceResponses],
    PropertyInfo(discriminator="type"),
]


class PerModelUsage(BaseModel):
    cached_tokens: int
    """The number of tokens retrieved from cache."""

    completion_tokens: int
    """The number of completion tokens generated."""

    invocation_count: int
    """The number of invocations."""

    run_model_name: str = FieldInfo(alias="model_name")
    """The name of the model."""

    prompt_tokens: int
    """The number of prompt tokens used."""

    total_tokens: int
    """The total number of tokens used."""


class PerTestingCriteriaResult(BaseModel):
    failed: int
    """Number of tests failed for this criteria."""

    passed: int
    """Number of tests passed for this criteria."""

    testing_criteria: str
    """A description of the testing criteria."""


class ResultCounts(BaseModel):
    errored: int
    """Number of output items that resulted in an error."""

    failed: int
    """Number of output items that failed to pass the evaluation."""

    passed: int
    """Number of output items that passed the evaluation."""

    total: int
    """Total number of executed output items."""


class RunCreateResponse(BaseModel):
    id: str
    """Unique identifier for the evaluation run."""

    created_at: int
    """Unix timestamp (in seconds) when the evaluation run was created."""

    data_source: DataSource
    """Information about the run's data source."""

    error: EvalAPIError
    """An object representing an error response from the Eval API."""

    eval_id: str
    """The identifier of the associated evaluation."""

    metadata: Optional[Metadata] = None
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    model: str
    """The model that is evaluated, if applicable."""

    name: str
    """The name of the evaluation run."""

    object: Literal["eval.run"]
    """The type of the object. Always "eval.run"."""

    per_model_usage: List[PerModelUsage]
    """Usage statistics for each model during the evaluation run."""

    per_testing_criteria_results: List[PerTestingCriteriaResult]
    """Results per testing criteria applied during the evaluation run."""

    report_url: str
    """The URL to the rendered evaluation run report on the UI dashboard."""

    result_counts: ResultCounts
    """Counters summarizing the outcomes of the evaluation run."""

    status: str
    """The status of the evaluation run."""

# === NexusCore/openenv\Lib\site-packages\openai\types\evals\run_list_response.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Dict, List, Union, Optional
from typing_extensions import Literal, Annotated, TypeAlias

from pydantic import Field as FieldInfo

from ..._utils import PropertyInfo
from ..._models import BaseModel
from .eval_api_error import EvalAPIError
from ..responses.tool import Tool
from ..shared.metadata import Metadata
from ..shared.reasoning_effort import ReasoningEffort
from ..responses.response_input_text import ResponseInputText
from .create_eval_jsonl_run_data_source import CreateEvalJSONLRunDataSource
from ..responses.response_format_text_config import ResponseFormatTextConfig
from .create_eval_completions_run_data_source import CreateEvalCompletionsRunDataSource

__all__ = [
    "RunListResponse",
    "DataSource",
    "DataSourceResponses",
    "DataSourceResponsesSource",
    "DataSourceResponsesSourceFileContent",
    "DataSourceResponsesSourceFileContentContent",
    "DataSourceResponsesSourceFileID",
    "DataSourceResponsesSourceResponses",
    "DataSourceResponsesInputMessages",
    "DataSourceResponsesInputMessagesTemplate",
    "DataSourceResponsesInputMessagesTemplateTemplate",
    "DataSourceResponsesInputMessagesTemplateTemplateChatMessage",
    "DataSourceResponsesInputMessagesTemplateTemplateEvalItem",
    "DataSourceResponsesInputMessagesTemplateTemplateEvalItemContent",
    "DataSourceResponsesInputMessagesTemplateTemplateEvalItemContentOutputText",
    "DataSourceResponsesInputMessagesItemReference",
    "DataSourceResponsesSamplingParams",
    "DataSourceResponsesSamplingParamsText",
    "PerModelUsage",
    "PerTestingCriteriaResult",
    "ResultCounts",
]


class DataSourceResponsesSourceFileContentContent(BaseModel):
    item: Dict[str, object]

    sample: Optional[Dict[str, object]] = None


class DataSourceResponsesSourceFileContent(BaseModel):
    content: List[DataSourceResponsesSourceFileContentContent]
    """The content of the jsonl file."""

    type: Literal["file_content"]
    """The type of jsonl source. Always `file_content`."""


class DataSourceResponsesSourceFileID(BaseModel):
    id: str
    """The identifier of the file."""

    type: Literal["file_id"]
    """The type of jsonl source. Always `file_id`."""


class DataSourceResponsesSourceResponses(BaseModel):
    type: Literal["responses"]
    """The type of run data source. Always `responses`."""

    created_after: Optional[int] = None
    """Only include items created after this timestamp (inclusive).

    This is a query parameter used to select responses.
    """

    created_before: Optional[int] = None
    """Only include items created before this timestamp (inclusive).

    This is a query parameter used to select responses.
    """

    instructions_search: Optional[str] = None
    """Optional string to search the 'instructions' field.

    This is a query parameter used to select responses.
    """

    metadata: Optional[object] = None
    """Metadata filter for the responses.

    This is a query parameter used to select responses.
    """

    model: Optional[str] = None
    """The name of the model to find responses for.

    This is a query parameter used to select responses.
    """

    reasoning_effort: Optional[ReasoningEffort] = None
    """Optional reasoning effort parameter.

    This is a query parameter used to select responses.
    """

    temperature: Optional[float] = None
    """Sampling temperature. This is a query parameter used to select responses."""

    tools: Optional[List[str]] = None
    """List of tool names. This is a query parameter used to select responses."""

    top_p: Optional[float] = None
    """Nucleus sampling parameter. This is a query parameter used to select responses."""

    users: Optional[List[str]] = None
    """List of user identifiers. This is a query parameter used to select responses."""


DataSourceResponsesSource: TypeAlias = Annotated[
    Union[DataSourceResponsesSourceFileContent, DataSourceResponsesSourceFileID, DataSourceResponsesSourceResponses],
    PropertyInfo(discriminator="type"),
]


class DataSourceResponsesInputMessagesTemplateTemplateChatMessage(BaseModel):
    content: str
    """The content of the message."""

    role: str
    """The role of the message (e.g. "system", "assistant", "user")."""


class DataSourceResponsesInputMessagesTemplateTemplateEvalItemContentOutputText(BaseModel):
    text: str
    """The text output from the model."""

    type: Literal["output_text"]
    """The type of the output text. Always `output_text`."""


DataSourceResponsesInputMessagesTemplateTemplateEvalItemContent: TypeAlias = Union[
    str, ResponseInputText, DataSourceResponsesInputMessagesTemplateTemplateEvalItemContentOutputText
]


class DataSourceResponsesInputMessagesTemplateTemplateEvalItem(BaseModel):
    content: DataSourceResponsesInputMessagesTemplateTemplateEvalItemContent
    """Text inputs to the model - can contain template strings."""

    role: Literal["user", "assistant", "system", "developer"]
    """The role of the message input.

    One of `user`, `assistant`, `system`, or `developer`.
    """

    type: Optional[Literal["message"]] = None
    """The type of the message input. Always `message`."""


DataSourceResponsesInputMessagesTemplateTemplate: TypeAlias = Union[
    DataSourceResponsesInputMessagesTemplateTemplateChatMessage,
    DataSourceResponsesInputMessagesTemplateTemplateEvalItem,
]


class DataSourceResponsesInputMessagesTemplate(BaseModel):
    template: List[DataSourceResponsesInputMessagesTemplateTemplate]
    """A list of chat messages forming the prompt or context.

    May include variable references to the `item` namespace, ie {{item.name}}.
    """

    type: Literal["template"]
    """The type of input messages. Always `template`."""


class DataSourceResponsesInputMessagesItemReference(BaseModel):
    item_reference: str
    """A reference to a variable in the `item` namespace. Ie, "item.name" """

    type: Literal["item_reference"]
    """The type of input messages. Always `item_reference`."""


DataSourceResponsesInputMessages: TypeAlias = Annotated[
    Union[DataSourceResponsesInputMessagesTemplate, DataSourceResponsesInputMessagesItemReference],
    PropertyInfo(discriminator="type"),
]


class DataSourceResponsesSamplingParamsText(BaseModel):
    format: Optional[ResponseFormatTextConfig] = None
    """An object specifying the format that the model must output.

    Configuring `{ "type": "json_schema" }` enables Structured Outputs, which
    ensures the model will match your supplied JSON schema. Learn more in the
    [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

    The default format is `{ "type": "text" }` with no additional options.

    **Not recommended for gpt-4o and newer models:**

    Setting to `{ "type": "json_object" }` enables the older JSON mode, which
    ensures the message the model generates is valid JSON. Using `json_schema` is
    preferred for models that support it.
    """


class DataSourceResponsesSamplingParams(BaseModel):
    max_completion_tokens: Optional[int] = None
    """The maximum number of tokens in the generated output."""

    seed: Optional[int] = None
    """A seed value to initialize the randomness, during sampling."""

    temperature: Optional[float] = None
    """A higher temperature increases randomness in the outputs."""

    text: Optional[DataSourceResponsesSamplingParamsText] = None
    """Configuration options for a text response from the model.

    Can be plain text or structured JSON data. Learn more:

    - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
    - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
    """

    tools: Optional[List[Tool]] = None
    """An array of tools the model may call while generating a response.

    You can specify which tool to use by setting the `tool_choice` parameter.

    The two categories of tools you can provide the model are:

    - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
      capabilities, like
      [web search](https://platform.openai.com/docs/guides/tools-web-search) or
      [file search](https://platform.openai.com/docs/guides/tools-file-search).
      Learn more about
      [built-in tools](https://platform.openai.com/docs/guides/tools).
    - **Function calls (custom tools)**: Functions that are defined by you, enabling
      the model to call your own code. Learn more about
      [function calling](https://platform.openai.com/docs/guides/function-calling).
    """

    top_p: Optional[float] = None
    """An alternative to temperature for nucleus sampling; 1.0 includes all tokens."""


class DataSourceResponses(BaseModel):
    source: DataSourceResponsesSource
    """Determines what populates the `item` namespace in this run's data source."""

    type: Literal["responses"]
    """The type of run data source. Always `responses`."""

    input_messages: Optional[DataSourceResponsesInputMessages] = None
    """Used when sampling from a model.

    Dictates the structure of the messages passed into the model. Can either be a
    reference to a prebuilt trajectory (ie, `item.input_trajectory`), or a template
    with variable references to the `item` namespace.
    """

    model: Optional[str] = None
    """The name of the model to use for generating completions (e.g. "o3-mini")."""

    sampling_params: Optional[DataSourceResponsesSamplingParams] = None


DataSource: TypeAlias = Annotated[
    Union[CreateEvalJSONLRunDataSource, CreateEvalCompletionsRunDataSource, DataSourceResponses],
    PropertyInfo(discriminator="type"),
]


class PerModelUsage(BaseModel):
    cached_tokens: int
    """The number of tokens retrieved from cache."""

    completion_tokens: int
    """The number of completion tokens generated."""

    invocation_count: int
    """The number of invocations."""

    run_model_name: str = FieldInfo(alias="model_name")
    """The name of the model."""

    prompt_tokens: int
    """The number of prompt tokens used."""

    total_tokens: int
    """The total number of tokens used."""


class PerTestingCriteriaResult(BaseModel):
    failed: int
    """Number of tests failed for this criteria."""

    passed: int
    """Number of tests passed for this criteria."""

    testing_criteria: str
    """A description of the testing criteria."""


class ResultCounts(BaseModel):
    errored: int
    """Number of output items that resulted in an error."""

    failed: int
    """Number of output items that failed to pass the evaluation."""

    passed: int
    """Number of output items that passed the evaluation."""

    total: int
    """Total number of executed output items."""


class RunListResponse(BaseModel):
    id: str
    """Unique identifier for the evaluation run."""

    created_at: int
    """Unix timestamp (in seconds) when the evaluation run was created."""

    data_source: DataSource
    """Information about the run's data source."""

    error: EvalAPIError
    """An object representing an error response from the Eval API."""

    eval_id: str
    """The identifier of the associated evaluation."""

    metadata: Optional[Metadata] = None
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    model: str
    """The model that is evaluated, if applicable."""

    name: str
    """The name of the evaluation run."""

    object: Literal["eval.run"]
    """The type of the object. Always "eval.run"."""

    per_model_usage: List[PerModelUsage]
    """Usage statistics for each model during the evaluation run."""

    per_testing_criteria_results: List[PerTestingCriteriaResult]
    """Results per testing criteria applied during the evaluation run."""

    report_url: str
    """The URL to the rendered evaluation run report on the UI dashboard."""

    result_counts: ResultCounts
    """Counters summarizing the outcomes of the evaluation run."""

    status: str
    """The status of the evaluation run."""

# === NexusCore/openenv\Lib\site-packages\openai\types\evals\run_retrieve_response.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Dict, List, Union, Optional
from typing_extensions import Literal, Annotated, TypeAlias

from pydantic import Field as FieldInfo

from ..._utils import PropertyInfo
from ..._models import BaseModel
from .eval_api_error import EvalAPIError
from ..responses.tool import Tool
from ..shared.metadata import Metadata
from ..shared.reasoning_effort import ReasoningEffort
from ..responses.response_input_text import ResponseInputText
from .create_eval_jsonl_run_data_source import CreateEvalJSONLRunDataSource
from ..responses.response_format_text_config import ResponseFormatTextConfig
from .create_eval_completions_run_data_source import CreateEvalCompletionsRunDataSource

__all__ = [
    "RunRetrieveResponse",
    "DataSource",
    "DataSourceResponses",
    "DataSourceResponsesSource",
    "DataSourceResponsesSourceFileContent",
    "DataSourceResponsesSourceFileContentContent",
    "DataSourceResponsesSourceFileID",
    "DataSourceResponsesSourceResponses",
    "DataSourceResponsesInputMessages",
    "DataSourceResponsesInputMessagesTemplate",
    "DataSourceResponsesInputMessagesTemplateTemplate",
    "DataSourceResponsesInputMessagesTemplateTemplateChatMessage",
    "DataSourceResponsesInputMessagesTemplateTemplateEvalItem",
    "DataSourceResponsesInputMessagesTemplateTemplateEvalItemContent",
    "DataSourceResponsesInputMessagesTemplateTemplateEvalItemContentOutputText",
    "DataSourceResponsesInputMessagesItemReference",
    "DataSourceResponsesSamplingParams",
    "DataSourceResponsesSamplingParamsText",
    "PerModelUsage",
    "PerTestingCriteriaResult",
    "ResultCounts",
]


class DataSourceResponsesSourceFileContentContent(BaseModel):
    item: Dict[str, object]

    sample: Optional[Dict[str, object]] = None


class DataSourceResponsesSourceFileContent(BaseModel):
    content: List[DataSourceResponsesSourceFileContentContent]
    """The content of the jsonl file."""

    type: Literal["file_content"]
    """The type of jsonl source. Always `file_content`."""


class DataSourceResponsesSourceFileID(BaseModel):
    id: str
    """The identifier of the file."""

    type: Literal["file_id"]
    """The type of jsonl source. Always `file_id`."""


class DataSourceResponsesSourceResponses(BaseModel):
    type: Literal["responses"]
    """The type of run data source. Always `responses`."""

    created_after: Optional[int] = None
    """Only include items created after this timestamp (inclusive).

    This is a query parameter used to select responses.
    """

    created_before: Optional[int] = None
    """Only include items created before this timestamp (inclusive).

    This is a query parameter used to select responses.
    """

    instructions_search: Optional[str] = None
    """Optional string to search the 'instructions' field.

    This is a query parameter used to select responses.
    """

    metadata: Optional[object] = None
    """Metadata filter for the responses.

    This is a query parameter used to select responses.
    """

    model: Optional[str] = None
    """The name of the model to find responses for.

    This is a query parameter used to select responses.
    """

    reasoning_effort: Optional[ReasoningEffort] = None
    """Optional reasoning effort parameter.

    This is a query parameter used to select responses.
    """

    temperature: Optional[float] = None
    """Sampling temperature. This is a query parameter used to select responses."""

    tools: Optional[List[str]] = None
    """List of tool names. This is a query parameter used to select responses."""

    top_p: Optional[float] = None
    """Nucleus sampling parameter. This is a query parameter used to select responses."""

    users: Optional[List[str]] = None
    """List of user identifiers. This is a query parameter used to select responses."""


DataSourceResponsesSource: TypeAlias = Annotated[
    Union[DataSourceResponsesSourceFileContent, DataSourceResponsesSourceFileID, DataSourceResponsesSourceResponses],
    PropertyInfo(discriminator="type"),
]


class DataSourceResponsesInputMessagesTemplateTemplateChatMessage(BaseModel):
    content: str
    """The content of the message."""

    role: str
    """The role of the message (e.g. "system", "assistant", "user")."""


class DataSourceResponsesInputMessagesTemplateTemplateEvalItemContentOutputText(BaseModel):
    text: str
    """The text output from the model."""

    type: Literal["output_text"]
    """The type of the output text. Always `output_text`."""


DataSourceResponsesInputMessagesTemplateTemplateEvalItemContent: TypeAlias = Union[
    str, ResponseInputText, DataSourceResponsesInputMessagesTemplateTemplateEvalItemContentOutputText
]


class DataSourceResponsesInputMessagesTemplateTemplateEvalItem(BaseModel):
    content: DataSourceResponsesInputMessagesTemplateTemplateEvalItemContent
    """Text inputs to the model - can contain template strings."""

    role: Literal["user", "assistant", "system", "developer"]
    """The role of the message input.

    One of `user`, `assistant`, `system`, or `developer`.
    """

    type: Optional[Literal["message"]] = None
    """The type of the message input. Always `message`."""


DataSourceResponsesInputMessagesTemplateTemplate: TypeAlias = Union[
    DataSourceResponsesInputMessagesTemplateTemplateChatMessage,
    DataSourceResponsesInputMessagesTemplateTemplateEvalItem,
]


class DataSourceResponsesInputMessagesTemplate(BaseModel):
    template: List[DataSourceResponsesInputMessagesTemplateTemplate]
    """A list of chat messages forming the prompt or context.

    May include variable references to the `item` namespace, ie {{item.name}}.
    """

    type: Literal["template"]
    """The type of input messages. Always `template`."""


class DataSourceResponsesInputMessagesItemReference(BaseModel):
    item_reference: str
    """A reference to a variable in the `item` namespace. Ie, "item.name" """

    type: Literal["item_reference"]
    """The type of input messages. Always `item_reference`."""


DataSourceResponsesInputMessages: TypeAlias = Annotated[
    Union[DataSourceResponsesInputMessagesTemplate, DataSourceResponsesInputMessagesItemReference],
    PropertyInfo(discriminator="type"),
]


class DataSourceResponsesSamplingParamsText(BaseModel):
    format: Optional[ResponseFormatTextConfig] = None
    """An object specifying the format that the model must output.

    Configuring `{ "type": "json_schema" }` enables Structured Outputs, which
    ensures the model will match your supplied JSON schema. Learn more in the
    [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

    The default format is `{ "type": "text" }` with no additional options.

    **Not recommended for gpt-4o and newer models:**

    Setting to `{ "type": "json_object" }` enables the older JSON mode, which
    ensures the message the model generates is valid JSON. Using `json_schema` is
    preferred for models that support it.
    """


class DataSourceResponsesSamplingParams(BaseModel):
    max_completion_tokens: Optional[int] = None
    """The maximum number of tokens in the generated output."""

    seed: Optional[int] = None
    """A seed value to initialize the randomness, during sampling."""

    temperature: Optional[float] = None
    """A higher temperature increases randomness in the outputs."""

    text: Optional[DataSourceResponsesSamplingParamsText] = None
    """Configuration options for a text response from the model.

    Can be plain text or structured JSON data. Learn more:

    - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
    - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
    """

    tools: Optional[List[Tool]] = None
    """An array of tools the model may call while generating a response.

    You can specify which tool to use by setting the `tool_choice` parameter.

    The two categories of tools you can provide the model are:

    - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
      capabilities, like
      [web search](https://platform.openai.com/docs/guides/tools-web-search) or
      [file search](https://platform.openai.com/docs/guides/tools-file-search).
      Learn more about
      [built-in tools](https://platform.openai.com/docs/guides/tools).
    - **Function calls (custom tools)**: Functions that are defined by you, enabling
      the model to call your own code. Learn more about
      [function calling](https://platform.openai.com/docs/guides/function-calling).
    """

    top_p: Optional[float] = None
    """An alternative to temperature for nucleus sampling; 1.0 includes all tokens."""


class DataSourceResponses(BaseModel):
    source: DataSourceResponsesSource
    """Determines what populates the `item` namespace in this run's data source."""

    type: Literal["responses"]
    """The type of run data source. Always `responses`."""

    input_messages: Optional[DataSourceResponsesInputMessages] = None
    """Used when sampling from a model.

    Dictates the structure of the messages passed into the model. Can either be a
    reference to a prebuilt trajectory (ie, `item.input_trajectory`), or a template
    with variable references to the `item` namespace.
    """

    model: Optional[str] = None
    """The name of the model to use for generating completions (e.g. "o3-mini")."""

    sampling_params: Optional[DataSourceResponsesSamplingParams] = None


DataSource: TypeAlias = Annotated[
    Union[CreateEvalJSONLRunDataSource, CreateEvalCompletionsRunDataSource, DataSourceResponses],
    PropertyInfo(discriminator="type"),
]


class PerModelUsage(BaseModel):
    cached_tokens: int
    """The number of tokens retrieved from cache."""

    completion_tokens: int
    """The number of completion tokens generated."""

    invocation_count: int
    """The number of invocations."""

    run_model_name: str = FieldInfo(alias="model_name")
    """The name of the model."""

    prompt_tokens: int
    """The number of prompt tokens used."""

    total_tokens: int
    """The total number of tokens used."""


class PerTestingCriteriaResult(BaseModel):
    failed: int
    """Number of tests failed for this criteria."""

    passed: int
    """Number of tests passed for this criteria."""

    testing_criteria: str
    """A description of the testing criteria."""


class ResultCounts(BaseModel):
    errored: int
    """Number of output items that resulted in an error."""

    failed: int
    """Number of output items that failed to pass the evaluation."""

    passed: int
    """Number of output items that passed the evaluation."""

    total: int
    """Total number of executed output items."""


class RunRetrieveResponse(BaseModel):
    id: str
    """Unique identifier for the evaluation run."""

    created_at: int
    """Unix timestamp (in seconds) when the evaluation run was created."""

    data_source: DataSource
    """Information about the run's data source."""

    error: EvalAPIError
    """An object representing an error response from the Eval API."""

    eval_id: str
    """The identifier of the associated evaluation."""

    metadata: Optional[Metadata] = None
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    model: str
    """The model that is evaluated, if applicable."""

    name: str
    """The name of the evaluation run."""

    object: Literal["eval.run"]
    """The type of the object. Always "eval.run"."""

    per_model_usage: List[PerModelUsage]
    """Usage statistics for each model during the evaluation run."""

    per_testing_criteria_results: List[PerTestingCriteriaResult]
    """Results per testing criteria applied during the evaluation run."""

    report_url: str
    """The URL to the rendered evaluation run report on the UI dashboard."""

    result_counts: ResultCounts
    """Counters summarizing the outcomes of the evaluation run."""

    status: str
    """The status of the evaluation run."""

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\widgets\toolbars.py ===
from __future__ import annotations

from typing import Any

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.enums import SYSTEM_BUFFER
from prompt_toolkit.filters import (
    Condition,
    FilterOrBool,
    emacs_mode,
    has_arg,
    has_completions,
    has_focus,
    has_validation_error,
    to_filter,
    vi_mode,
    vi_navigation_mode,
)
from prompt_toolkit.formatted_text import (
    AnyFormattedText,
    StyleAndTextTuples,
    fragment_list_len,
    to_formatted_text,
)
from prompt_toolkit.key_binding.key_bindings import (
    ConditionalKeyBindings,
    KeyBindings,
    KeyBindingsBase,
    merge_key_bindings,
)
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.key_binding.vi_state import InputMode
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import ConditionalContainer, Container, Window
from prompt_toolkit.layout.controls import (
    BufferControl,
    FormattedTextControl,
    SearchBufferControl,
    UIContent,
    UIControl,
)
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.lexers import SimpleLexer
from prompt_toolkit.search import SearchDirection

__all__ = [
    "ArgToolbar",
    "CompletionsToolbar",
    "FormattedTextToolbar",
    "SearchToolbar",
    "SystemToolbar",
    "ValidationToolbar",
]

E = KeyPressEvent


class FormattedTextToolbar(Window):
    def __init__(self, text: AnyFormattedText, style: str = "", **kw: Any) -> None:
        # Note: The style needs to be applied to the toolbar as a whole, not
        #       just the `FormattedTextControl`.
        super().__init__(
            FormattedTextControl(text, **kw),
            style=style,
            dont_extend_height=True,
            height=Dimension(min=1),
        )


class SystemToolbar:
    """
    Toolbar for a system prompt.

    :param prompt: Prompt to be displayed to the user.
    """

    def __init__(
        self,
        prompt: AnyFormattedText = "Shell command: ",
        enable_global_bindings: FilterOrBool = True,
    ) -> None:
        self.prompt = prompt
        self.enable_global_bindings = to_filter(enable_global_bindings)

        self.system_buffer = Buffer(name=SYSTEM_BUFFER)

        self._bindings = self._build_key_bindings()

        self.buffer_control = BufferControl(
            buffer=self.system_buffer,
            lexer=SimpleLexer(style="class:system-toolbar.text"),
            input_processors=[
                BeforeInput(lambda: self.prompt, style="class:system-toolbar")
            ],
            key_bindings=self._bindings,
        )

        self.window = Window(
            self.buffer_control, height=1, style="class:system-toolbar"
        )

        self.container = ConditionalContainer(
            content=self.window, filter=has_focus(self.system_buffer)
        )

    def _get_display_before_text(self) -> StyleAndTextTuples:
        return [
            ("class:system-toolbar", "Shell command: "),
            ("class:system-toolbar.text", self.system_buffer.text),
            ("", "\n"),
        ]

    def _build_key_bindings(self) -> KeyBindingsBase:
        focused = has_focus(self.system_buffer)

        # Emacs
        emacs_bindings = KeyBindings()
        handle = emacs_bindings.add

        @handle("escape", filter=focused)
        @handle("c-g", filter=focused)
        @handle("c-c", filter=focused)
        def _cancel(event: E) -> None:
            "Hide system prompt."
            self.system_buffer.reset()
            event.app.layout.focus_last()

        @handle("enter", filter=focused)
        async def _accept(event: E) -> None:
            "Run system command."
            await event.app.run_system_command(
                self.system_buffer.text,
                display_before_text=self._get_display_before_text(),
            )
            self.system_buffer.reset(append_to_history=True)
            event.app.layout.focus_last()

        # Vi.
        vi_bindings = KeyBindings()
        handle = vi_bindings.add

        @handle("escape", filter=focused)
        @handle("c-c", filter=focused)
        def _cancel_vi(event: E) -> None:
            "Hide system prompt."
            event.app.vi_state.input_mode = InputMode.NAVIGATION
            self.system_buffer.reset()
            event.app.layout.focus_last()

        @handle("enter", filter=focused)
        async def _accept_vi(event: E) -> None:
            "Run system command."
            event.app.vi_state.input_mode = InputMode.NAVIGATION
            await event.app.run_system_command(
                self.system_buffer.text,
                display_before_text=self._get_display_before_text(),
            )
            self.system_buffer.reset(append_to_history=True)
            event.app.layout.focus_last()

        # Global bindings. (Listen to these bindings, even when this widget is
        # not focussed.)
        global_bindings = KeyBindings()
        handle = global_bindings.add

        @handle(Keys.Escape, "!", filter=~focused & emacs_mode, is_global=True)
        def _focus_me(event: E) -> None:
            "M-'!' will focus this user control."
            event.app.layout.focus(self.window)

        @handle("!", filter=~focused & vi_mode & vi_navigation_mode, is_global=True)
        def _focus_me_vi(event: E) -> None:
            "Focus."
            event.app.vi_state.input_mode = InputMode.INSERT
            event.app.layout.focus(self.window)

        return merge_key_bindings(
            [
                ConditionalKeyBindings(emacs_bindings, emacs_mode),
                ConditionalKeyBindings(vi_bindings, vi_mode),
                ConditionalKeyBindings(global_bindings, self.enable_global_bindings),
            ]
        )

    def __pt_container__(self) -> Container:
        return self.container


class ArgToolbar:
    def __init__(self) -> None:
        def get_formatted_text() -> StyleAndTextTuples:
            arg = get_app().key_processor.arg or ""
            if arg == "-":
                arg = "-1"

            return [
                ("class:arg-toolbar", "Repeat: "),
                ("class:arg-toolbar.text", arg),
            ]

        self.window = Window(FormattedTextControl(get_formatted_text), height=1)

        self.container = ConditionalContainer(content=self.window, filter=has_arg)

    def __pt_container__(self) -> Container:
        return self.container


class SearchToolbar:
    """
    :param vi_mode: Display '/' and '?' instead of I-search.
    :param ignore_case: Search case insensitive.
    """

    def __init__(
        self,
        search_buffer: Buffer | None = None,
        vi_mode: bool = False,
        text_if_not_searching: AnyFormattedText = "",
        forward_search_prompt: AnyFormattedText = "I-search: ",
        backward_search_prompt: AnyFormattedText = "I-search backward: ",
        ignore_case: FilterOrBool = False,
    ) -> None:
        if search_buffer is None:
            search_buffer = Buffer()

        @Condition
        def is_searching() -> bool:
            return self.control in get_app().layout.search_links

        def get_before_input() -> AnyFormattedText:
            if not is_searching():
                return text_if_not_searching
            elif (
                self.control.searcher_search_state.direction == SearchDirection.BACKWARD
            ):
                return "?" if vi_mode else backward_search_prompt
            else:
                return "/" if vi_mode else forward_search_prompt

        self.search_buffer = search_buffer

        self.control = SearchBufferControl(
            buffer=search_buffer,
            input_processors=[
                BeforeInput(get_before_input, style="class:search-toolbar.prompt")
            ],
            lexer=SimpleLexer(style="class:search-toolbar.text"),
            ignore_case=ignore_case,
        )

        self.container = ConditionalContainer(
            content=Window(self.control, height=1, style="class:search-toolbar"),
            filter=is_searching,
        )

    def __pt_container__(self) -> Container:
        return self.container


class _CompletionsToolbarControl(UIControl):
    def create_content(self, width: int, height: int) -> UIContent:
        all_fragments: StyleAndTextTuples = []

        complete_state = get_app().current_buffer.complete_state
        if complete_state:
            completions = complete_state.completions
            index = complete_state.complete_index  # Can be None!

            # Width of the completions without the left/right arrows in the margins.
            content_width = width - 6

            # Booleans indicating whether we stripped from the left/right
            cut_left = False
            cut_right = False

            # Create Menu content.
            fragments: StyleAndTextTuples = []

            for i, c in enumerate(completions):
                # When there is no more place for the next completion
                if fragment_list_len(fragments) + len(c.display_text) >= content_width:
                    # If the current one was not yet displayed, page to the next sequence.
                    if i <= (index or 0):
                        fragments = []
                        cut_left = True
                    # If the current one is visible, stop here.
                    else:
                        cut_right = True
                        break

                fragments.extend(
                    to_formatted_text(
                        c.display_text,
                        style=(
                            "class:completion-toolbar.completion.current"
                            if i == index
                            else "class:completion-toolbar.completion"
                        ),
                    )
                )
                fragments.append(("", " "))

            # Extend/strip until the content width.
            fragments.append(("", " " * (content_width - fragment_list_len(fragments))))
            fragments = fragments[:content_width]

            # Return fragments
            all_fragments.append(("", " "))
            all_fragments.append(
                ("class:completion-toolbar.arrow", "<" if cut_left else " ")
            )
            all_fragments.append(("", " "))

            all_fragments.extend(fragments)

            all_fragments.append(("", " "))
            all_fragments.append(
                ("class:completion-toolbar.arrow", ">" if cut_right else " ")
            )
            all_fragments.append(("", " "))

        def get_line(i: int) -> StyleAndTextTuples:
            return all_fragments

        return UIContent(get_line=get_line, line_count=1)


class CompletionsToolbar:
    def __init__(self) -> None:
        self.container = ConditionalContainer(
            content=Window(
                _CompletionsToolbarControl(), height=1, style="class:completion-toolbar"
            ),
            filter=has_completions,
        )

    def __pt_container__(self) -> Container:
        return self.container


class ValidationToolbar:
    def __init__(self, show_position: bool = False) -> None:
        def get_formatted_text() -> StyleAndTextTuples:
            buff = get_app().current_buffer

            if buff.validation_error:
                row, column = buff.document.translate_index_to_position(
                    buff.validation_error.cursor_position
                )

                if show_position:
                    text = f"{buff.validation_error.message} (line={row + 1} column={column + 1})"
                else:
                    text = buff.validation_error.message

                return [("class:validation-toolbar", text)]
            else:
                return []

        self.control = FormattedTextControl(get_formatted_text)

        self.container = ConditionalContainer(
            content=Window(self.control, height=1), filter=has_validation_error
        )

    def __pt_container__(self) -> Container:
        return self.container

# === NexusCore/openenv\Lib\site-packages\h11\_events.py ===
# High level events that make up HTTP/1.1 conversations. Loosely inspired by
# the corresponding events in hyper-h2:
#
#     http://python-hyper.org/h2/en/stable/api.html#events
#
# Don't subclass these. Stuff will break.

import re
from abc import ABC
from dataclasses import dataclass
from typing import List, Tuple, Union

from ._abnf import method, request_target
from ._headers import Headers, normalize_and_validate
from ._util import bytesify, LocalProtocolError, validate

# Everything in __all__ gets re-exported as part of the h11 public API.
__all__ = [
    "Event",
    "Request",
    "InformationalResponse",
    "Response",
    "Data",
    "EndOfMessage",
    "ConnectionClosed",
]

method_re = re.compile(method.encode("ascii"))
request_target_re = re.compile(request_target.encode("ascii"))


class Event(ABC):
    """
    Base class for h11 events.
    """

    __slots__ = ()


@dataclass(init=False, frozen=True)
class Request(Event):
    """The beginning of an HTTP request.

    Fields:

    .. attribute:: method

       An HTTP method, e.g. ``b"GET"`` or ``b"POST"``. Always a byte
       string. :term:`Bytes-like objects <bytes-like object>` and native
       strings containing only ascii characters will be automatically
       converted to byte strings.

    .. attribute:: target

       The target of an HTTP request, e.g. ``b"/index.html"``, or one of the
       more exotic formats described in `RFC 7320, section 5.3
       <https://tools.ietf.org/html/rfc7230#section-5.3>`_. Always a byte
       string. :term:`Bytes-like objects <bytes-like object>` and native
       strings containing only ascii characters will be automatically
       converted to byte strings.

    .. attribute:: headers

       Request headers, represented as a list of (name, value) pairs. See
       :ref:`the header normalization rules <headers-format>` for details.

    .. attribute:: http_version

       The HTTP protocol version, represented as a byte string like
       ``b"1.1"``. See :ref:`the HTTP version normalization rules
       <http_version-format>` for details.

    """

    __slots__ = ("method", "headers", "target", "http_version")

    method: bytes
    headers: Headers
    target: bytes
    http_version: bytes

    def __init__(
        self,
        *,
        method: Union[bytes, str],
        headers: Union[Headers, List[Tuple[bytes, bytes]], List[Tuple[str, str]]],
        target: Union[bytes, str],
        http_version: Union[bytes, str] = b"1.1",
        _parsed: bool = False,
    ) -> None:
        super().__init__()
        if isinstance(headers, Headers):
            object.__setattr__(self, "headers", headers)
        else:
            object.__setattr__(
                self, "headers", normalize_and_validate(headers, _parsed=_parsed)
            )
        if not _parsed:
            object.__setattr__(self, "method", bytesify(method))
            object.__setattr__(self, "target", bytesify(target))
            object.__setattr__(self, "http_version", bytesify(http_version))
        else:
            object.__setattr__(self, "method", method)
            object.__setattr__(self, "target", target)
            object.__setattr__(self, "http_version", http_version)

        # "A server MUST respond with a 400 (Bad Request) status code to any
        # HTTP/1.1 request message that lacks a Host header field and to any
        # request message that contains more than one Host header field or a
        # Host header field with an invalid field-value."
        # -- https://tools.ietf.org/html/rfc7230#section-5.4
        host_count = 0
        for name, value in self.headers:
            if name == b"host":
                host_count += 1
        if self.http_version == b"1.1" and host_count == 0:
            raise LocalProtocolError("Missing mandatory Host: header")
        if host_count > 1:
            raise LocalProtocolError("Found multiple Host: headers")

        validate(method_re, self.method, "Illegal method characters")
        validate(request_target_re, self.target, "Illegal target characters")

    # This is an unhashable type.
    __hash__ = None  # type: ignore


@dataclass(init=False, frozen=True)
class _ResponseBase(Event):
    __slots__ = ("headers", "http_version", "reason", "status_code")

    headers: Headers
    http_version: bytes
    reason: bytes
    status_code: int

    def __init__(
        self,
        *,
        headers: Union[Headers, List[Tuple[bytes, bytes]], List[Tuple[str, str]]],
        status_code: int,
        http_version: Union[bytes, str] = b"1.1",
        reason: Union[bytes, str] = b"",
        _parsed: bool = False,
    ) -> None:
        super().__init__()
        if isinstance(headers, Headers):
            object.__setattr__(self, "headers", headers)
        else:
            object.__setattr__(
                self, "headers", normalize_and_validate(headers, _parsed=_parsed)
            )
        if not _parsed:
            object.__setattr__(self, "reason", bytesify(reason))
            object.__setattr__(self, "http_version", bytesify(http_version))
            if not isinstance(status_code, int):
                raise LocalProtocolError("status code must be integer")
            # Because IntEnum objects are instances of int, but aren't
            # duck-compatible (sigh), see gh-72.
            object.__setattr__(self, "status_code", int(status_code))
        else:
            object.__setattr__(self, "reason", reason)
            object.__setattr__(self, "http_version", http_version)
            object.__setattr__(self, "status_code", status_code)

        self.__post_init__()

    def __post_init__(self) -> None:
        pass

    # This is an unhashable type.
    __hash__ = None  # type: ignore


@dataclass(init=False, frozen=True)
class InformationalResponse(_ResponseBase):
    """An HTTP informational response.

    Fields:

    .. attribute:: status_code

       The status code of this response, as an integer. For an
       :class:`InformationalResponse`, this is always in the range [100,
       200).

    .. attribute:: headers

       Request headers, represented as a list of (name, value) pairs. See
       :ref:`the header normalization rules <headers-format>` for
       details.

    .. attribute:: http_version

       The HTTP protocol version, represented as a byte string like
       ``b"1.1"``. See :ref:`the HTTP version normalization rules
       <http_version-format>` for details.

    .. attribute:: reason

       The reason phrase of this response, as a byte string. For example:
       ``b"OK"``, or ``b"Not Found"``.

    """

    def __post_init__(self) -> None:
        if not (100 <= self.status_code < 200):
            raise LocalProtocolError(
                "InformationalResponse status_code should be in range "
                "[100, 200), not {}".format(self.status_code)
            )

    # This is an unhashable type.
    __hash__ = None  # type: ignore


@dataclass(init=False, frozen=True)
class Response(_ResponseBase):
    """The beginning of an HTTP response.

    Fields:

    .. attribute:: status_code

       The status code of this response, as an integer. For an
       :class:`Response`, this is always in the range [200,
       1000).

    .. attribute:: headers

       Request headers, represented as a list of (name, value) pairs. See
       :ref:`the header normalization rules <headers-format>` for details.

    .. attribute:: http_version

       The HTTP protocol version, represented as a byte string like
       ``b"1.1"``. See :ref:`the HTTP version normalization rules
       <http_version-format>` for details.

    .. attribute:: reason

       The reason phrase of this response, as a byte string. For example:
       ``b"OK"``, or ``b"Not Found"``.

    """

    def __post_init__(self) -> None:
        if not (200 <= self.status_code < 1000):
            raise LocalProtocolError(
                "Response status_code should be in range [200, 1000), not {}".format(
                    self.status_code
                )
            )

    # This is an unhashable type.
    __hash__ = None  # type: ignore


@dataclass(init=False, frozen=True)
class Data(Event):
    """Part of an HTTP message body.

    Fields:

    .. attribute:: data

       A :term:`bytes-like object` containing part of a message body. Or, if
       using the ``combine=False`` argument to :meth:`Connection.send`, then
       any object that your socket writing code knows what to do with, and for
       which calling :func:`len` returns the number of bytes that will be
       written -- see :ref:`sendfile` for details.

    .. attribute:: chunk_start

       A marker that indicates whether this data object is from the start of a
       chunked transfer encoding chunk. This field is ignored when when a Data
       event is provided to :meth:`Connection.send`: it is only valid on
       events emitted from :meth:`Connection.next_event`. You probably
       shouldn't use this attribute at all; see
       :ref:`chunk-delimiters-are-bad` for details.

    .. attribute:: chunk_end

       A marker that indicates whether this data object is the last for a
       given chunked transfer encoding chunk. This field is ignored when when
       a Data event is provided to :meth:`Connection.send`: it is only valid
       on events emitted from :meth:`Connection.next_event`. You probably
       shouldn't use this attribute at all; see
       :ref:`chunk-delimiters-are-bad` for details.

    """

    __slots__ = ("data", "chunk_start", "chunk_end")

    data: bytes
    chunk_start: bool
    chunk_end: bool

    def __init__(
        self, data: bytes, chunk_start: bool = False, chunk_end: bool = False
    ) -> None:
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "chunk_start", chunk_start)
        object.__setattr__(self, "chunk_end", chunk_end)

    # This is an unhashable type.
    __hash__ = None  # type: ignore


# XX FIXME: "A recipient MUST ignore (or consider as an error) any fields that
# are forbidden to be sent in a trailer, since processing them as if they were
# present in the header section might bypass external security filters."
# https://svn.tools.ietf.org/svn/wg/httpbis/specs/rfc7230.html#chunked.trailer.part
# Unfortunately, the list of forbidden fields is long and vague :-/
@dataclass(init=False, frozen=True)
class EndOfMessage(Event):
    """The end of an HTTP message.

    Fields:

    .. attribute:: headers

       Default value: ``[]``

       Any trailing headers attached to this message, represented as a list of
       (name, value) pairs. See :ref:`the header normalization rules
       <headers-format>` for details.

       Must be empty unless ``Transfer-Encoding: chunked`` is in use.

    """

    __slots__ = ("headers",)

    headers: Headers

    def __init__(
        self,
        *,
        headers: Union[
            Headers, List[Tuple[bytes, bytes]], List[Tuple[str, str]], None
        ] = None,
        _parsed: bool = False,
    ) -> None:
        super().__init__()
        if headers is None:
            headers = Headers([])
        elif not isinstance(headers, Headers):
            headers = normalize_and_validate(headers, _parsed=_parsed)

        object.__setattr__(self, "headers", headers)

    # This is an unhashable type.
    __hash__ = None  # type: ignore


@dataclass(frozen=True)
class ConnectionClosed(Event):
    """This event indicates that the sender has closed their outgoing
    connection.

    Note that this does not necessarily mean that they can't *receive* further
    data, because TCP connections are composed to two one-way channels which
    can be closed independently. See :ref:`closing` for details.

    No fields.
    """

    pass

# === NexusCore/openenv\Lib\site-packages\pycparser\yacctab.py ===

# yacctab.py
# This file is automatically generated. Do not edit.
_tabversion = '3.10'

_lr_method = 'LALR'

_lr_signature = 'translation_unit_or_emptyleftLORleftLANDleftORleftXORleftANDleftEQNEleftGTGELTLEleftRSHIFTLSHIFTleftPLUSMINUSleftTIMESDIVIDEMODAUTO BREAK CASE CHAR CONST CONTINUE DEFAULT DO DOUBLE ELSE ENUM EXTERN FLOAT FOR GOTO IF INLINE INT LONG REGISTER OFFSETOF RESTRICT RETURN SHORT SIGNED SIZEOF STATIC STRUCT SWITCH TYPEDEF UNION UNSIGNED VOID VOLATILE WHILE __INT128 _BOOL _COMPLEX _NORETURN _THREAD_LOCAL _STATIC_ASSERT _ATOMIC _ALIGNOF _ALIGNAS _PRAGMA ID TYPEID INT_CONST_DEC INT_CONST_OCT INT_CONST_HEX INT_CONST_BIN INT_CONST_CHAR FLOAT_CONST HEX_FLOAT_CONST CHAR_CONST WCHAR_CONST U8CHAR_CONST U16CHAR_CONST U32CHAR_CONST STRING_LITERAL WSTRING_LITERAL U8STRING_LITERAL U16STRING_LITERAL U32STRING_LITERAL PLUS MINUS TIMES DIVIDE MOD OR AND NOT XOR LSHIFT RSHIFT LOR LAND LNOT LT LE GT GE EQ NE EQUALS TIMESEQUAL DIVEQUAL MODEQUAL PLUSEQUAL MINUSEQUAL LSHIFTEQUAL RSHIFTEQUAL ANDEQUAL XOREQUAL OREQUAL PLUSPLUS MINUSMINUS ARROW CONDOP LPAREN RPAREN LBRACKET RBRACKET LBRACE RBRACE COMMA PERIOD SEMI COLON ELLIPSIS PPHASH PPPRAGMA PPPRAGMASTRabstract_declarator_opt : empty\n| abstract_declaratorassignment_expression_opt : empty\n| assignment_expressionblock_item_list_opt : empty\n| block_item_listdeclaration_list_opt : empty\n| declaration_listdeclaration_specifiers_no_type_opt : empty\n| declaration_specifiers_no_typedesignation_opt : empty\n| designationexpression_opt : empty\n| expressionid_init_declarator_list_opt : empty\n| id_init_declarator_listidentifier_list_opt : empty\n| identifier_listinit_declarator_list_opt : empty\n| init_declarator_listinitializer_list_opt : empty\n| initializer_listparameter_type_list_opt : empty\n| parameter_type_liststruct_declarator_list_opt : empty\n| struct_declarator_listtype_qualifier_list_opt : empty\n| type_qualifier_list direct_id_declarator   : ID\n         direct_id_declarator   : LPAREN id_declarator RPAREN\n         direct_id_declarator   : direct_id_declarator LBRACKET type_qualifier_list_opt assignment_expression_opt RBRACKET\n         direct_id_declarator   : direct_id_declarator LBRACKET STATIC type_qualifier_list_opt assignment_expression RBRACKET\n                                    | direct_id_declarator LBRACKET type_qualifier_list STATIC assignment_expression RBRACKET\n         direct_id_declarator   : direct_id_declarator LBRACKET type_qualifier_list_opt TIMES RBRACKET\n         direct_id_declarator   : direct_id_declarator LPAREN parameter_type_list RPAREN\n                                    | direct_id_declarator LPAREN identifier_list_opt RPAREN\n         direct_typeid_declarator   : TYPEID\n         direct_typeid_declarator   : LPAREN typeid_declarator RPAREN\n         direct_typeid_declarator   : direct_typeid_declarator LBRACKET type_qualifier_list_opt assignment_expression_opt RBRACKET\n         direct_typeid_declarator   : direct_typeid_declarator LBRACKET STATIC type_qualifier_list_opt assignment_expression RBRACKET\n                                    | direct_typeid_declarator LBRACKET type_qualifier_list STATIC assignment_expression RBRACKET\n         direct_typeid_declarator   : direct_typeid_declarator LBRACKET type_qualifier_list_opt TIMES RBRACKET\n         direct_typeid_declarator   : direct_typeid_declarator LPAREN parameter_type_list RPAREN\n                                    | direct_typeid_declarator LPAREN identifier_list_opt RPAREN\n         direct_typeid_noparen_declarator   : TYPEID\n         direct_typeid_noparen_declarator   : direct_typeid_noparen_declarator LBRACKET type_qualifier_list_opt assignment_expression_opt RBRACKET\n         direct_typeid_noparen_declarator   : direct_typeid_noparen_declarator LBRACKET STATIC type_qualifier_list_opt assignment_expression RBRACKET\n                                    | direct_typeid_noparen_declarator LBRACKET type_qualifier_list STATIC assignment_expression RBRACKET\n         direct_typeid_noparen_declarator   : direct_typeid_noparen_declarator LBRACKET type_qualifier_list_opt TIMES RBRACKET\n         direct_typeid_noparen_declarator   : direct_typeid_noparen_declarator LPAREN parameter_type_list RPAREN\n                                    | direct_typeid_noparen_declarator LPAREN identifier_list_opt RPAREN\n         id_declarator  : direct_id_declarator\n         id_declarator  : pointer direct_id_declarator\n         typeid_declarator  : direct_typeid_declarator\n         typeid_declarator  : pointer direct_typeid_declarator\n         typeid_noparen_declarator  : direct_typeid_noparen_declarator\n         typeid_noparen_declarator  : pointer direct_typeid_noparen_declarator\n         translation_unit_or_empty   : translation_unit\n                                        | empty\n         translation_unit    : external_declaration\n         translation_unit    : translation_unit external_declaration\n         external_declaration    : function_definition\n         external_declaration    : declaration\n         external_declaration    : pp_directive\n                                    | pppragma_directive\n         external_declaration    : SEMI\n         external_declaration    : static_assert\n         static_assert           : _STATIC_ASSERT LPAREN constant_expression COMMA unified_string_literal RPAREN\n                                    | _STATIC_ASSERT LPAREN constant_expression RPAREN\n         pp_directive  : PPHASH\n         pppragma_directive      : PPPRAGMA\n                                    | PPPRAGMA PPPRAGMASTR\n                                    | _PRAGMA LPAREN unified_string_literal RPAREN\n         pppragma_directive_list : pppragma_directive\n                                    | pppragma_directive_list pppragma_directive\n         function_definition : id_declarator declaration_list_opt compound_statement\n         function_definition : declaration_specifiers id_declarator declaration_list_opt compound_statement\n         statement   : labeled_statement\n                        | expression_statement\n                        | compound_statement\n                        | selection_statement\n                        | iteration_statement\n                        | jump_statement\n                        | pppragma_directive\n                        | static_assert\n         pragmacomp_or_statement     : pppragma_directive_list statement\n                                        | statement\n         decl_body : declaration_specifiers init_declarator_list_opt\n                      | declaration_specifiers_no_type id_init_declarator_list_opt\n         declaration : decl_body SEMI\n         declaration_list    : declaration\n                                | declaration_list declaration\n         declaration_specifiers_no_type  : type_qualifier declaration_specifiers_no_type_opt\n         declaration_specifiers_no_type  : storage_class_specifier declaration_specifiers_no_type_opt\n         declaration_specifiers_no_type  : function_specifier declaration_specifiers_no_type_opt\n         declaration_specifiers_no_type  : atomic_specifier declaration_specifiers_no_type_opt\n         declaration_specifiers_no_type  : alignment_specifier declaration_specifiers_no_type_opt\n         declaration_specifiers  : declaration_specifiers type_qualifier\n         declaration_specifiers  : declaration_specifiers storage_class_specifier\n         declaration_specifiers  : declaration_specifiers function_specifier\n         declaration_specifiers  : declaration_specifiers type_specifier_no_typeid\n         declaration_specifiers  : type_specifier\n         declaration_specifiers  : declaration_specifiers_no_type type_specifier\n         declaration_specifiers  : declaration_specifiers alignment_specifier\n         storage_class_specifier : AUTO\n                                    | REGISTER\n                                    | STATIC\n                                    | EXTERN\n                                    | TYPEDEF\n                                    | _THREAD_LOCAL\n         function_specifier  : INLINE\n                                | _NORETURN\n         type_specifier_no_typeid  : VOID\n                                      | _BOOL\n                                      | CHAR\n                                      | SHORT\n                                      | INT\n                                      | LONG\n                                      | FLOAT\n                                      | DOUBLE\n                                      | _COMPLEX\n                                      | SIGNED\n                                      | UNSIGNED\n                                      | __INT128\n         type_specifier  : typedef_name\n                            | enum_specifier\n                            | struct_or_union_specifier\n                            | type_specifier_no_typeid\n                            | atomic_specifier\n         atomic_specifier  : _ATOMIC LPAREN type_name RPAREN\n         type_qualifier  : CONST\n                            | RESTRICT\n                            | VOLATILE\n                            | _ATOMIC\n         init_declarator_list    : init_declarator\n                                    | init_declarator_list COMMA init_declarator\n         init_declarator : declarator\n                            | declarator EQUALS initializer\n         id_init_declarator_list    : id_init_declarator\n                                       | id_init_declarator_list COMMA init_declarator\n         id_init_declarator : id_declarator\n                               | id_declarator EQUALS initializer\n         specifier_qualifier_list    : specifier_qualifier_list type_specifier_no_typeid\n         specifier_qualifier_list    : specifier_qualifier_list type_qualifier\n         specifier_qualifier_list  : type_specifier\n         specifier_qualifier_list  : type_qualifier_list type_specifier\n         specifier_qualifier_list  : alignment_specifier\n         specifier_qualifier_list  : specifier_qualifier_list alignment_specifier\n         struct_or_union_specifier   : struct_or_union ID\n                                        | struct_or_union TYPEID\n         struct_or_union_specifier : struct_or_union brace_open struct_declaration_list brace_close\n                                      | struct_or_union brace_open brace_close\n         struct_or_union_specifier   : struct_or_union ID brace_open struct_declaration_list brace_close\n                                        | struct_or_union ID brace_open brace_close\n                                        | struct_or_union TYPEID brace_open struct_declaration_list brace_close\n                                        | struct_or_union TYPEID brace_open brace_close\n         struct_or_union : STRUCT\n                            | UNION\n         struct_declaration_list     : struct_declaration\n                                        | struct_declaration_list struct_declaration\n         struct_declaration : specifier_qualifier_list struct_declarator_list_opt SEMI\n         struct_declaration : SEMI\n         struct_declaration : pppragma_directive\n         struct_declarator_list  : struct_declarator\n                                    | struct_declarator_list COMMA struct_declarator\n         struct_declarator : declarator\n         struct_declarator   : declarator COLON constant_expression\n                                | COLON constant_expression\n         enum_specifier  : ENUM ID\n                            | ENUM TYPEID\n         enum_specifier  : ENUM brace_open enumerator_list brace_close\n         enum_specifier  : ENUM ID brace_open enumerator_list brace_close\n                            | ENUM TYPEID brace_open enumerator_list brace_close\n         enumerator_list : enumerator\n                            | enumerator_list COMMA\n                            | enumerator_list COMMA enumerator\n         alignment_specifier  : _ALIGNAS LPAREN type_name RPAREN\n                                 | _ALIGNAS LPAREN constant_expression RPAREN\n         enumerator  : ID\n                        | ID EQUALS constant_expression\n         declarator  : id_declarator\n                        | typeid_declarator\n         pointer : TIMES type_qualifier_list_opt\n                    | TIMES type_qualifier_list_opt pointer\n         type_qualifier_list : type_qualifier\n                                | type_qualifier_list type_qualifier\n         parameter_type_list : parameter_list\n                                | parameter_list COMMA ELLIPSIS\n         parameter_list  : parameter_declaration\n                            | parameter_list COMMA parameter_declaration\n         parameter_declaration   : declaration_specifiers id_declarator\n                                    | declaration_specifiers typeid_noparen_declarator\n         parameter_declaration   : declaration_specifiers abstract_declarator_opt\n         identifier_list : identifier\n                            | identifier_list COMMA identifier\n         initializer : assignment_expression\n         initializer : brace_open initializer_list_opt brace_close\n                        | brace_open initializer_list COMMA brace_close\n         initializer_list    : designation_opt initializer\n                                | initializer_list COMMA designation_opt initializer\n         designation : designator_list EQUALS\n         designator_list : designator\n                            | designator_list designator\n         designator  : LBRACKET constant_expression RBRACKET\n                        | PERIOD identifier\n         type_name   : specifier_qualifier_list abstract_declarator_opt\n         abstract_declarator     : pointer\n         abstract_declarator     : pointer direct_abstract_declarator\n         abstract_declarator     : direct_abstract_declarator\n         direct_abstract_declarator  : LPAREN abstract_declarator RPAREN  direct_abstract_declarator  : direct_abstract_declarator LBRACKET assignment_expression_opt RBRACKET\n         direct_abstract_declarator  : LBRACKET type_qualifier_list_opt assignment_expression_opt RBRACKET\n         direct_abstract_declarator  : direct_abstract_declarator LBRACKET TIMES RBRACKET\n         direct_abstract_declarator  : LBRACKET TIMES RBRACKET\n         direct_abstract_declarator  : direct_abstract_declarator LPAREN parameter_type_list_opt RPAREN\n         direct_abstract_declarator  : LPAREN parameter_type_list_opt RPAREN\n         block_item  : declaration\n                        | statement\n         block_item_list : block_item\n                            | block_item_list block_item\n         compound_statement : brace_open block_item_list_opt brace_close  labeled_statement : ID COLON pragmacomp_or_statement  labeled_statement : CASE constant_expression COLON pragmacomp_or_statement  labeled_statement : DEFAULT COLON pragmacomp_or_statement  selection_statement : IF LPAREN expression RPAREN pragmacomp_or_statement  selection_statement : IF LPAREN expression RPAREN statement ELSE pragmacomp_or_statement  selection_statement : SWITCH LPAREN expression RPAREN pragmacomp_or_statement  iteration_statement : WHILE LPAREN expression RPAREN pragmacomp_or_statement  iteration_statement : DO pragmacomp_or_statement WHILE LPAREN expression RPAREN SEMI  iteration_statement : FOR LPAREN expression_opt SEMI expression_opt SEMI expression_opt RPAREN pragmacomp_or_statement  iteration_statement : FOR LPAREN declaration expression_opt SEMI expression_opt RPAREN pragmacomp_or_statement  jump_statement  : GOTO ID SEMI  jump_statement  : BREAK SEMI  jump_statement  : CONTINUE SEMI  jump_statement  : RETURN expression SEMI\n                            | RETURN SEMI\n         expression_statement : expression_opt SEMI  expression  : assignment_expression\n                        | expression COMMA assignment_expression\n         assignment_expression : LPAREN compound_statement RPAREN  typedef_name : TYPEID  assignment_expression   : conditional_expression\n                                    | unary_expression assignment_operator assignment_expression\n         assignment_operator : EQUALS\n                                | XOREQUAL\n                                | TIMESEQUAL\n                                | DIVEQUAL\n                                | MODEQUAL\n                                | PLUSEQUAL\n                                | MINUSEQUAL\n                                | LSHIFTEQUAL\n                                | RSHIFTEQUAL\n                                | ANDEQUAL\n                                | OREQUAL\n         constant_expression : conditional_expression  conditional_expression  : binary_expression\n                                    | binary_expression CONDOP expression COLON conditional_expression\n         binary_expression   : cast_expression\n                                | binary_expression TIMES binary_expression\n                                | binary_expression DIVIDE binary_expression\n                                | binary_expression MOD binary_expression\n                                | binary_expression PLUS binary_expression\n                                | binary_expression MINUS binary_expression\n                                | binary_expression RSHIFT binary_expression\n                                | binary_expression LSHIFT binary_expression\n                                | binary_expression LT binary_expression\n                                | binary_expression LE binary_expression\n                                | binary_expression GE binary_expression\n                                | binary_expression GT binary_expression\n                                | binary_expression EQ binary_expression\n                                | binary_expression NE binary_expression\n                                | binary_expression AND binary_expression\n                                | binary_expression OR binary_expression\n                                | binary_expression XOR binary_expression\n                                | binary_expression LAND binary_expression\n                                | binary_expression LOR binary_expression\n         cast_expression : unary_expression  cast_expression : LPAREN type_name RPAREN cast_expression  unary_expression    : postfix_expression  unary_expression    : PLUSPLUS unary_expression\n                                | MINUSMINUS unary_expression\n                                | unary_operator cast_expression\n         unary_expression    : SIZEOF unary_expression\n                                | SIZEOF LPAREN type_name RPAREN\n                                | _ALIGNOF LPAREN type_name RPAREN\n         unary_operator  : AND\n                            | TIMES\n                            | PLUS\n                            | MINUS\n                            | NOT\n                            | LNOT\n         postfix_expression  : primary_expression  postfix_expression  : postfix_expression LBRACKET expression RBRACKET  postfix_expression  : postfix_expression LPAREN argument_expression_list RPAREN\n                                | postfix_expression LPAREN RPAREN\n         postfix_expression  : postfix_expression PERIOD ID\n                                | postfix_expression PERIOD TYPEID\n                                | postfix_expression ARROW ID\n                                | postfix_expression ARROW TYPEID\n         postfix_expression  : postfix_expression PLUSPLUS\n                                | postfix_expression MINUSMINUS\n         postfix_expression  : LPAREN type_name RPAREN brace_open initializer_list brace_close\n                                | LPAREN type_name RPAREN brace_open initializer_list COMMA brace_close\n         primary_expression  : identifier  primary_expression  : constant  primary_expression  : unified_string_literal\n                                | unified_wstring_literal\n         primary_expression  : LPAREN expression RPAREN  primary_expression  : OFFSETOF LPAREN type_name COMMA offsetof_member_designator RPAREN\n         offsetof_member_designator : identifier\n                                         | offsetof_member_designator PERIOD identifier\n                                         | offsetof_member_designator LBRACKET expression RBRACKET\n         argument_expression_list    : assignment_expression\n                                        | argument_expression_list COMMA assignment_expression\n         identifier  : ID  constant    : INT_CONST_DEC\n                        | INT_CONST_OCT\n                        | INT_CONST_HEX\n                        | INT_CONST_BIN\n                        | INT_CONST_CHAR\n         constant    : FLOAT_CONST\n                        | HEX_FLOAT_CONST\n         constant    : CHAR_CONST\n                        | WCHAR_CONST\n                        | U8CHAR_CONST\n                        | U16CHAR_CONST\n                        | U32CHAR_CONST\n         unified_string_literal  : STRING_LITERAL\n                                    | unified_string_literal STRING_LITERAL\n         unified_wstring_literal : WSTRING_LITERAL\n                                    | U8STRING_LITERAL\n                                    | U16STRING_LITERAL\n                                    | U32STRING_LITERAL\n                                    | unified_wstring_literal WSTRING_LITERAL\n                                    | unified_wstring_literal U8STRING_LITERAL\n                                    | unified_wstring_literal U16STRING_LITERAL\n                                    | unified_wstring_literal U32STRING_LITERAL\n         brace_open  :   LBRACE\n         brace_close :   RBRACE\n        empty : '
    
_lr_action_items = {'$end':([0,1,2,3,4,5,6,7,8,9,10,14,15,64,90,91,127,208,251,262,267,355,499,],[-340,0,-58,-59,-60,-62,-63,-64,-65,-66,-67,-70,-71,-61,-90,-72,-76,-339,-77,-73,-69,-221,-68,]),'SEMI':([0,2,4,5,6,7,8,9,10,12,13,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,69,70,71,72,73,74,75,76,77,78,79,81,83,84,85,86,87,88,89,90,91,97,98,99,100,101,102,103,104,105,106,107,108,110,111,112,117,118,119,121,122,123,124,127,128,130,132,139,140,143,144,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,203,204,205,206,207,208,209,210,211,212,214,220,221,222,223,224,225,226,227,228,229,230,231,232,233,236,239,242,245,246,247,248,249,250,251,252,253,254,255,262,263,267,291,292,293,295,296,297,300,301,302,303,311,312,326,327,330,333,334,335,336,337,338,339,340,341,342,343,344,345,346,348,349,353,354,355,356,357,358,360,361,369,370,371,372,373,374,375,376,377,403,404,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,439,440,459,460,463,464,465,468,469,470,471,473,475,479,480,481,482,483,484,485,486,493,494,497,499,501,502,505,506,508,509,522,523,524,525,526,527,529,530,531,535,536,538,552,553,554,555,556,558,561,563,570,571,574,579,580,582,584,585,586,],[9,9,-60,-62,-63,-64,-65,-66,-67,-340,90,-70,-71,-52,-340,-340,-340,-128,-102,-340,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,-340,-340,-129,-134,-181,-98,-99,-100,-101,-104,-88,-134,-19,-20,-135,-137,-182,-54,-37,-90,-72,-53,-93,-9,-10,-340,-94,-95,-103,-89,-129,-15,-16,-139,-141,-97,-96,-169,-170,-338,-149,-150,210,-76,-340,-181,-55,-328,-30,-306,-255,-256,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,210,210,210,-152,-159,-339,-340,-162,-163,-145,-147,-13,-340,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-315,361,-14,-340,374,375,377,-238,-242,-277,-77,-38,-136,-138,-196,-73,-329,-69,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-35,-36,-140,-142,-171,210,-154,210,-156,-151,-160,465,-143,-144,-148,-25,-26,-164,-166,-146,-130,-177,-178,-221,-220,-13,-340,-340,-237,-340,-87,-74,-340,483,-233,-234,484,-236,-43,-44,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,-272,-273,-274,-275,-276,-295,-296,-297,-298,-299,-31,-34,-172,-173,-153,-155,-161,-168,-222,-340,-224,-240,-239,-86,-75,529,-340,-232,-235,-243,-197,-39,-42,-278,-68,-293,-294,-284,-285,-32,-33,-165,-167,-223,-340,-340,-340,-340,559,-198,-40,-41,-257,-225,-87,-74,-227,-228,572,-302,-309,-340,580,-303,-226,-229,-340,-340,-231,-230,]),'PPHASH':([0,2,4,5,6,7,8,9,10,14,15,64,90,91,127,208,251,262,267,355,499,],[14,14,-60,-62,-63,-64,-65,-66,-67,-70,-71,-61,-90,-72,-76,-339,-77,-73,-69,-221,-68,]),'PPPRAGMA':([0,2,4,5,6,7,8,9,10,14,15,64,90,91,121,124,127,128,203,204,205,207,208,210,211,221,222,223,224,225,226,227,228,229,230,231,232,242,251,262,267,333,335,338,355,356,358,360,361,369,370,371,374,375,377,465,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[15,15,-60,-62,-63,-64,-65,-66,-67,-70,-71,-61,-90,-72,-338,15,-76,15,15,15,15,-159,-339,-162,-163,15,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,15,-77,-73,-69,15,15,-160,-221,-220,15,15,-237,15,-87,-74,-233,-234,-236,-161,-222,15,-224,-86,-75,-232,-235,-68,-223,15,15,15,-225,-87,-74,-227,-228,15,-226,-229,15,15,-231,-230,]),'_PRAGMA':([0,2,4,5,6,7,8,9,10,14,15,64,90,91,121,124,127,128,203,204,205,207,208,210,211,221,222,223,224,225,226,227,228,229,230,231,232,242,251,262,267,333,335,338,355,356,358,360,361,369,370,371,374,375,377,465,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[16,16,-60,-62,-63,-64,-65,-66,-67,-70,-71,-61,-90,-72,-338,16,-76,16,16,16,16,-159,-339,-162,-163,16,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,16,-77,-73,-69,16,16,-160,-221,-220,16,16,-237,16,-87,-74,-233,-234,-236,-161,-222,16,-224,-86,-75,-232,-235,-68,-223,16,16,16,-225,-87,-74,-227,-228,16,-226,-229,16,16,-231,-230,]),'_STATIC_ASSERT':([0,2,4,5,6,7,8,9,10,14,15,64,90,91,121,127,128,208,221,222,223,224,225,226,227,228,229,230,231,232,242,251,262,267,355,356,358,360,361,369,370,371,374,375,377,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[18,18,-60,-62,-63,-64,-65,-66,-67,-70,-71,-61,-90,-72,-338,-76,18,-339,18,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,18,-77,-73,-69,-221,-220,18,18,-237,18,-87,-74,-233,-234,-236,-222,18,-224,-86,-75,-232,-235,-68,-223,18,18,18,-225,-87,-74,-227,-228,18,-226,-229,18,18,-231,-230,]),'ID':([0,2,4,5,6,7,8,9,10,12,14,15,17,20,21,22,23,24,25,26,27,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,62,63,64,69,70,71,72,74,75,76,77,78,80,81,82,90,91,94,95,96,98,99,100,101,102,103,104,106,112,113,114,115,116,117,118,119,120,121,122,123,126,127,128,134,135,136,137,141,147,148,149,150,153,154,155,156,160,161,182,183,184,192,194,195,196,197,198,199,206,208,209,212,214,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,244,247,251,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,289,290,294,298,306,309,310,314,318,322,323,330,331,332,334,336,337,340,341,342,347,348,349,353,354,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,398,400,401,402,405,448,449,452,455,457,459,460,463,464,466,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,507,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,564,565,570,572,579,580,582,584,585,586,],[28,28,-60,-62,-63,-64,-65,-66,-67,28,-70,-71,28,28,-340,-340,-340,-128,-102,28,-340,-107,-340,-125,-126,-127,-129,-241,118,122,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-157,-158,-61,28,28,-129,-134,-98,-99,-100,-101,-104,28,-134,28,-90,-72,159,-340,159,-93,-9,-10,-340,-94,-95,-103,-129,-97,-183,-27,-28,-185,-96,-169,-170,202,-338,-149,-150,159,-76,233,28,159,-340,159,159,-287,-288,-289,-286,159,159,159,159,-290,-291,159,-340,-28,28,28,159,-184,-186,202,202,-152,-339,28,-145,-147,233,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,159,159,233,373,159,-77,-340,159,-340,-28,-73,-69,159,159,159,159,159,159,159,159,159,159,159,159,159,159,159,159,159,159,159,159,159,431,433,159,159,-287,159,159,159,28,28,-340,-171,202,159,-154,-156,-151,-143,-144,-148,159,-146,-130,-177,-178,-221,-220,233,233,-237,159,159,159,159,233,-87,-74,159,-233,-234,-236,159,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,159,-12,159,159,-287,159,159,159,-340,159,28,159,159,-172,-173,-153,-155,28,159,-222,233,-224,159,-86,-75,159,-232,-235,-340,-201,-340,-68,159,159,159,159,-340,-28,-287,-223,233,233,233,159,159,159,-11,-287,159,159,-225,-87,-74,-227,-228,159,-340,159,159,233,159,-226,-229,233,233,-231,-230,]),'LPAREN':([0,2,4,5,6,7,8,9,10,12,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,64,69,70,71,72,74,75,76,77,78,80,81,82,88,89,90,91,94,95,97,98,99,100,101,102,103,104,106,109,112,113,114,115,116,117,118,119,121,122,123,126,127,128,132,134,135,136,139,140,141,143,147,148,149,150,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,192,194,195,196,197,206,208,209,212,214,216,221,222,223,224,225,226,227,228,229,230,231,232,233,234,237,238,240,241,242,243,247,251,252,256,257,258,259,262,263,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,291,292,294,298,300,301,302,303,306,309,310,311,312,318,319,322,323,324,325,330,332,334,336,337,340,341,342,347,348,349,351,352,353,354,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,403,404,405,406,429,431,432,433,434,439,440,446,447,448,452,455,457,459,460,463,464,466,467,469,470,471,474,478,479,480,482,483,484,487,489,493,494,498,499,500,501,502,503,508,509,510,511,512,515,516,518,520,524,525,526,527,528,529,532,533,535,536,543,544,545,546,547,548,549,550,551,552,553,554,555,556,559,561,562,563,565,566,567,570,572,574,577,578,579,580,582,584,585,586,],[17,17,-60,-62,-63,-64,-65,-66,-67,82,-70,-71,92,17,94,96,17,-340,-340,-340,-128,-102,17,-340,-29,-107,-340,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,125,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,126,-61,82,17,-129,125,-98,-99,-100,-101,-104,82,-134,82,137,-37,-90,-72,141,-340,96,-93,-9,-10,-340,-94,-95,-103,-129,125,-97,-183,-27,-28,-185,-96,-169,-170,-338,-149,-150,141,-76,238,137,82,238,-340,-328,-30,238,-306,-287,-288,-289,-286,288,294,294,141,298,299,-292,-315,-290,-291,-304,-305,-307,304,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,238,-340,-28,322,82,238,-184,-186,-152,-339,82,-145,-147,351,238,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-315,141,362,238,366,367,238,372,238,-77,-38,-340,238,-340,-28,-73,-329,-69,238,141,141,141,141,141,141,141,141,141,141,141,141,141,141,141,141,141,141,238,238,-300,-301,238,238,-334,-335,-336,-337,-287,238,238,-35,-36,322,449,322,-340,-45,458,-171,141,-154,-156,-151,-143,-144,-148,141,-146,-130,351,351,-177,-178,-221,-220,238,238,-237,238,238,238,238,238,-87,-74,238,-233,-234,-236,238,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,238,-12,141,-287,238,238,-43,-44,141,-308,-295,-296,-297,-298,-299,-31,-34,449,458,-340,322,238,238,-172,-173,-153,-155,82,141,-222,238,-224,141,528,-86,-75,238,-232,-235,-340,-201,-39,-42,-340,-68,141,-293,-294,238,-32,-33,238,-340,-28,-210,-216,-214,-287,-223,238,238,238,238,238,238,-11,-40,-41,-287,238,238,-50,-51,-212,-211,-213,-215,-225,-87,-74,-227,-228,238,-302,-340,-309,238,-46,-49,238,238,-303,-47,-48,-226,-229,238,238,-231,-230,]),'TIMES':([0,2,4,5,6,7,8,9,10,12,14,15,17,21,22,23,24,25,26,27,29,30,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,69,70,71,72,74,75,76,77,78,81,82,90,91,94,95,98,99,100,101,102,103,104,106,112,113,114,115,116,117,118,119,121,122,123,126,127,128,134,135,136,139,141,143,145,146,147,148,149,150,151,152,153,154,155,156,158,159,160,161,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,192,194,195,197,206,208,209,212,214,216,221,222,223,224,225,226,227,228,229,230,231,232,233,234,238,242,247,250,251,256,257,258,259,262,263,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,291,292,293,294,295,296,297,298,300,301,302,303,306,309,310,322,323,330,332,334,336,337,340,341,342,347,348,349,351,353,354,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,448,455,457,459,460,463,464,466,467,469,470,471,474,479,480,482,483,484,487,489,497,498,499,500,501,502,503,505,506,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,561,562,563,565,570,572,574,579,580,582,584,585,586,],[30,30,-60,-62,-63,-64,-65,-66,-67,30,-70,-71,30,-340,-340,-340,-128,-102,30,-340,-107,-340,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,30,30,-129,-134,-98,-99,-100,-101,-104,-134,30,-90,-72,147,-340,-93,-9,-10,-340,-94,-95,-103,-129,-97,30,-27,-28,-185,-96,-169,-170,-338,-149,-150,147,-76,147,30,147,-340,-328,147,-306,269,-258,-287,-288,-289,-286,-277,-279,147,147,147,147,-292,-315,-290,-291,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,306,-340,-28,30,30,147,-186,-152,-339,30,-145,-147,30,147,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-315,147,147,147,147,-277,-77,-340,400,-340,-28,-73,-329,-69,147,147,147,147,147,147,147,147,147,147,147,147,147,147,147,147,147,147,147,147,147,-300,-301,-280,147,-281,-282,-283,147,-334,-335,-336,-337,-287,147,147,30,456,-171,147,-154,-156,-151,-143,-144,-148,147,-146,-130,30,-177,-178,-221,-220,147,147,-237,147,147,147,147,147,-87,-74,147,-233,-234,-236,147,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,147,-12,147,-287,147,147,147,-308,-259,-260,-261,269,269,269,269,269,269,269,269,269,269,269,269,269,269,269,-295,-296,-297,-298,-299,-340,147,520,-172,-173,-153,-155,30,147,-222,147,-224,147,-86,-75,147,-232,-235,-340,-201,-278,-340,-68,147,-293,-294,147,-284,-285,543,-340,-28,-287,-223,147,147,147,147,147,147,-11,-287,147,147,-225,-87,-74,-227,-228,147,-302,-340,-309,147,147,147,-303,-226,-229,147,147,-231,-230,]),'TYPEID':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,62,63,64,67,68,69,70,71,72,73,74,75,76,77,78,80,81,82,90,91,96,97,98,99,100,101,102,103,104,106,112,113,114,115,116,117,118,119,121,122,123,124,125,126,127,128,129,134,137,140,141,192,193,194,196,197,203,204,205,206,207,208,209,210,211,212,213,214,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,289,290,294,298,299,304,311,312,313,318,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,466,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[35,35,-60,-62,-63,-64,-65,-66,-67,35,89,-70,-71,-52,-340,-340,-340,-128,-102,35,-340,-29,-107,-340,-125,-126,-127,-129,-241,119,123,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-157,-158,-61,35,-91,89,35,-129,-134,35,-98,-99,-100,-101,-104,89,-134,89,-90,-72,35,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-183,-27,-28,-185,-96,-169,-170,-338,-149,-150,35,35,35,-76,35,-92,89,35,-30,35,324,35,89,-184,-186,35,35,35,-152,-159,-339,89,-162,-163,-145,35,-147,35,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,35,-77,-73,-69,432,434,35,35,35,35,-35,-36,35,324,35,-171,35,-154,35,-156,-151,-160,-143,-144,-148,-146,-130,35,-177,-178,-221,-220,-237,-87,-84,35,-233,-234,-236,-31,-34,35,35,-172,-173,-153,-155,-161,89,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'ENUM':([0,2,4,5,6,7,8,9,10,11,14,15,19,21,22,23,26,27,28,29,34,50,51,52,53,54,55,56,57,58,59,60,64,67,68,70,71,72,73,90,91,96,97,98,99,100,101,102,103,112,116,117,121,124,125,126,127,128,129,137,140,141,193,197,203,204,205,207,208,210,211,213,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,333,335,338,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[36,36,-60,-62,-63,-64,-65,-66,-67,36,-70,-71,-52,-340,-340,-340,36,-340,-29,-107,-340,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,36,-91,36,-340,-134,36,-90,-72,36,-53,-93,-9,-10,-340,-94,-95,-97,-185,-96,-338,36,36,36,-76,36,-92,36,-30,36,36,-186,36,36,36,-159,-339,-162,-163,36,36,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,36,-77,-73,-69,36,36,36,36,-35,-36,36,36,36,36,-160,-130,36,-177,-178,-221,-220,-237,-87,-84,36,-233,-234,-236,-31,-34,36,36,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'VOID':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,96,97,98,99,100,101,102,103,104,106,112,116,117,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[38,38,-60,-62,-63,-64,-65,-66,-67,38,38,-70,-71,-52,-340,-340,-340,-128,-102,38,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,38,-91,38,38,-129,-134,38,-98,-99,-100,-101,-104,-134,-90,-72,38,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-185,-96,-169,-170,-338,-149,-150,38,38,38,-76,38,-92,38,-30,38,38,38,-186,38,38,38,-152,-159,-339,38,-162,-163,-145,38,-147,38,38,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,38,-77,-73,-69,38,38,38,38,-35,-36,38,38,-171,38,-154,38,-156,-151,-160,-143,-144,-148,-146,-130,38,-177,-178,-221,-220,-237,-87,-84,38,-233,-234,-236,-31,-34,38,38,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'_BOOL':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,96,97,98,99,100,101,102,103,104,106,112,116,117,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[39,39,-60,-62,-63,-64,-65,-66,-67,39,39,-70,-71,-52,-340,-340,-340,-128,-102,39,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,39,-91,39,39,-129,-134,39,-98,-99,-100,-101,-104,-134,-90,-72,39,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-185,-96,-169,-170,-338,-149,-150,39,39,39,-76,39,-92,39,-30,39,39,39,-186,39,39,39,-152,-159,-339,39,-162,-163,-145,39,-147,39,39,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,39,-77,-73,-69,39,39,39,39,-35,-36,39,39,-171,39,-154,39,-156,-151,-160,-143,-144,-148,-146,-130,39,-177,-178,-221,-220,-237,-87,-84,39,-233,-234,-236,-31,-34,39,39,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'CHAR':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,96,97,98,99,100,101,102,103,104,106,112,116,117,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[40,40,-60,-62,-63,-64,-65,-66,-67,40,40,-70,-71,-52,-340,-340,-340,-128,-102,40,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,40,-91,40,40,-129,-134,40,-98,-99,-100,-101,-104,-134,-90,-72,40,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-185,-96,-169,-170,-338,-149,-150,40,40,40,-76,40,-92,40,-30,40,40,40,-186,40,40,40,-152,-159,-339,40,-162,-163,-145,40,-147,40,40,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,40,-77,-73,-69,40,40,40,40,-35,-36,40,40,-171,40,-154,40,-156,-151,-160,-143,-144,-148,-146,-130,40,-177,-178,-221,-220,-237,-87,-84,40,-233,-234,-236,-31,-34,40,40,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'SHORT':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,96,97,98,99,100,101,102,103,104,106,112,116,117,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[41,41,-60,-62,-63,-64,-65,-66,-67,41,41,-70,-71,-52,-340,-340,-340,-128,-102,41,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,41,-91,41,41,-129,-134,41,-98,-99,-100,-101,-104,-134,-90,-72,41,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-185,-96,-169,-170,-338,-149,-150,41,41,41,-76,41,-92,41,-30,41,41,41,-186,41,41,41,-152,-159,-339,41,-162,-163,-145,41,-147,41,41,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,41,-77,-73,-69,41,41,41,41,-35,-36,41,41,-171,41,-154,41,-156,-151,-160,-143,-144,-148,-146,-130,41,-177,-178,-221,-220,-237,-87,-84,41,-233,-234,-236,-31,-34,41,41,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'INT':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,96,97,98,99,100,101,102,103,104,106,112,116,117,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[42,42,-60,-62,-63,-64,-65,-66,-67,42,42,-70,-71,-52,-340,-340,-340,-128,-102,42,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,42,-91,42,42,-129,-134,42,-98,-99,-100,-101,-104,-134,-90,-72,42,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-185,-96,-169,-170,-338,-149,-150,42,42,42,-76,42,-92,42,-30,42,42,42,-186,42,42,42,-152,-159,-339,42,-162,-163,-145,42,-147,42,42,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,42,-77,-73,-69,42,42,42,42,-35,-36,42,42,-171,42,-154,42,-156,-151,-160,-143,-144,-148,-146,-130,42,-177,-178,-221,-220,-237,-87,-84,42,-233,-234,-236,-31,-34,42,42,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'LONG':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,96,97,98,99,100,101,102,103,104,106,112,116,117,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[43,43,-60,-62,-63,-64,-65,-66,-67,43,43,-70,-71,-52,-340,-340,-340,-128,-102,43,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,43,-91,43,43,-129,-134,43,-98,-99,-100,-101,-104,-134,-90,-72,43,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-185,-96,-169,-170,-338,-149,-150,43,43,43,-76,43,-92,43,-30,43,43,43,-186,43,43,43,-152,-159,-339,43,-162,-163,-145,43,-147,43,43,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,43,-77,-73,-69,43,43,43,43,-35,-36,43,43,-171,43,-154,43,-156,-151,-160,-143,-144,-148,-146,-130,43,-177,-178,-221,-220,-237,-87,-84,43,-233,-234,-236,-31,-34,43,43,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'FLOAT':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,96,97,98,99,100,101,102,103,104,106,112,116,117,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[44,44,-60,-62,-63,-64,-65,-66,-67,44,44,-70,-71,-52,-340,-340,-340,-128,-102,44,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,44,-91,44,44,-129,-134,44,-98,-99,-100,-101,-104,-134,-90,-72,44,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-185,-96,-169,-170,-338,-149,-150,44,44,44,-76,44,-92,44,-30,44,44,44,-186,44,44,44,-152,-159,-339,44,-162,-163,-145,44,-147,44,44,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,44,-77,-73,-69,44,44,44,44,-35,-36,44,44,-171,44,-154,44,-156,-151,-160,-143,-144,-148,-146,-130,44,-177,-178,-221,-220,-237,-87,-84,44,-233,-234,-236,-31,-34,44,44,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'DOUBLE':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,96,97,98,99,100,101,102,103,104,106,112,116,117,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[45,45,-60,-62,-63,-64,-65,-66,-67,45,45,-70,-71,-52,-340,-340,-340,-128,-102,45,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,45,-91,45,45,-129,-134,45,-98,-99,-100,-101,-104,-134,-90,-72,45,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-185,-96,-169,-170,-338,-149,-150,45,45,45,-76,45,-92,45,-30,45,45,45,-186,45,45,45,-152,-159,-339,45,-162,-163,-145,45,-147,45,45,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,45,-77,-73,-69,45,45,45,45,-35,-36,45,45,-171,45,-154,45,-156,-151,-160,-143,-144,-148,-146,-130,45,-177,-178,-221,-220,-237,-87,-84,45,-233,-234,-236,-31,-34,45,45,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'_COMPLEX':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,96,97,98,99,100,101,102,103,104,106,112,116,117,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[46,46,-60,-62,-63,-64,-65,-66,-67,46,46,-70,-71,-52,-340,-340,-340,-128,-102,46,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,46,-91,46,46,-129,-134,46,-98,-99,-100,-101,-104,-134,-90,-72,46,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-185,-96,-169,-170,-338,-149,-150,46,46,46,-76,46,-92,46,-30,46,46,46,-186,46,46,46,-152,-159,-339,46,-162,-163,-145,46,-147,46,46,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,46,-77,-73,-69,46,46,46,46,-35,-36,46,46,-171,46,-154,46,-156,-151,-160,-143,-144,-148,-146,-130,46,-177,-178,-221,-220,-237,-87,-84,46,-233,-234,-236,-31,-34,46,46,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'SIGNED':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,96,97,98,99,100,101,102,103,104,106,112,116,117,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[47,47,-60,-62,-63,-64,-65,-66,-67,47,47,-70,-71,-52,-340,-340,-340,-128,-102,47,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,47,-91,47,47,-129,-134,47,-98,-99,-100,-101,-104,-134,-90,-72,47,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-185,-96,-169,-170,-338,-149,-150,47,47,47,-76,47,-92,47,-30,47,47,47,-186,47,47,47,-152,-159,-339,47,-162,-163,-145,47,-147,47,47,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,47,-77,-73,-69,47,47,47,47,-35,-36,47,47,-171,47,-154,47,-156,-151,-160,-143,-144,-148,-146,-130,47,-177,-178,-221,-220,-237,-87,-84,47,-233,-234,-236,-31,-34,47,47,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'UNSIGNED':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,96,97,98,99,100,101,102,103,104,106,112,116,117,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[48,48,-60,-62,-63,-64,-65,-66,-67,48,48,-70,-71,-52,-340,-340,-340,-128,-102,48,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,48,-91,48,48,-129,-134,48,-98,-99,-100,-101,-104,-134,-90,-72,48,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-185,-96,-169,-170,-338,-149,-150,48,48,48,-76,48,-92,48,-30,48,48,48,-186,48,48,48,-152,-159,-339,48,-162,-163,-145,48,-147,48,48,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,48,-77,-73,-69,48,48,48,48,-35,-36,48,48,-171,48,-154,48,-156,-151,-160,-143,-144,-148,-146,-130,48,-177,-178,-221,-220,-237,-87,-84,48,-233,-234,-236,-31,-34,48,48,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'__INT128':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,96,97,98,99,100,101,102,103,104,106,112,116,117,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[49,49,-60,-62,-63,-64,-65,-66,-67,49,49,-70,-71,-52,-340,-340,-340,-128,-102,49,-340,-29,-107,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,49,-91,49,49,-129,-134,49,-98,-99,-100,-101,-104,-134,-90,-72,49,-53,-93,-9,-10,-340,-94,-95,-103,-129,-97,-185,-96,-169,-170,-338,-149,-150,49,49,49,-76,49,-92,49,-30,49,49,49,-186,49,49,49,-152,-159,-339,49,-162,-163,-145,49,-147,49,49,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,49,-77,-73,-69,49,49,49,49,-35,-36,49,49,-171,49,-154,49,-156,-151,-160,-143,-144,-148,-146,-130,49,-177,-178,-221,-220,-237,-87,-84,49,-233,-234,-236,-31,-34,49,49,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'_ATOMIC':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,70,71,72,73,74,75,76,77,78,81,90,91,95,96,97,98,99,100,101,102,103,104,106,112,115,116,117,118,119,121,122,123,124,125,126,127,128,129,136,137,140,141,183,184,192,193,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,258,259,262,267,294,298,299,304,311,312,313,322,323,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,448,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,511,512,524,552,553,554,555,556,579,580,585,586,],[50,50,-60,-62,-63,-64,-65,-66,-67,72,81,-70,-71,-52,72,72,72,-128,-102,109,72,-29,-107,81,-125,-126,-127,72,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,72,-91,81,109,72,-134,72,-98,-99,-100,-101,-104,-134,-90,-72,81,50,-53,-93,-9,-10,72,-94,-95,-103,-129,-97,81,-185,-96,-169,-170,-338,-149,-150,50,50,50,-76,72,-92,81,50,-30,50,81,81,81,109,-186,50,50,50,-152,-159,-339,81,-162,-163,-145,72,-147,81,72,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,50,-77,81,81,-73,-69,50,50,50,50,-35,-36,50,50,81,-171,50,-154,50,-156,-151,-160,-143,-144,-148,-146,-130,50,-177,-178,-221,-220,-237,-87,-84,72,-233,-234,-236,-31,-34,81,50,50,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,81,81,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'CONST':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,27,28,29,30,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,71,72,73,74,75,76,77,78,81,90,91,95,96,97,101,104,106,115,116,118,119,121,122,123,124,125,126,127,128,129,136,137,140,141,183,184,192,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,258,259,262,267,294,298,299,304,311,312,313,322,323,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,448,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,511,512,524,552,553,554,555,556,579,580,585,586,],[51,51,-60,-62,-63,-64,-65,-66,-67,51,51,-70,-71,-52,51,51,51,-128,-102,51,-29,-107,51,-125,-126,-127,51,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,51,-91,51,51,-134,51,-98,-99,-100,-101,-104,-134,-90,-72,51,51,-53,51,-103,-129,51,-185,-169,-170,-338,-149,-150,51,51,51,-76,51,-92,51,51,-30,51,51,51,51,-186,51,51,51,-152,-159,-339,51,-162,-163,-145,51,-147,51,51,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,51,-77,51,51,-73,-69,51,51,51,51,-35,-36,51,51,51,-171,51,-154,51,-156,-151,-160,-143,-144,-148,-146,-130,51,-177,-178,-221,-220,-237,-87,-84,51,-233,-234,-236,-31,-34,51,51,51,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,51,51,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'RESTRICT':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,27,28,29,30,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,71,72,73,74,75,76,77,78,81,90,91,95,96,97,101,104,106,115,116,118,119,121,122,123,124,125,126,127,128,129,136,137,140,141,183,184,192,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,258,259,262,267,294,298,299,304,311,312,313,322,323,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,448,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,511,512,524,552,553,554,555,556,579,580,585,586,],[52,52,-60,-62,-63,-64,-65,-66,-67,52,52,-70,-71,-52,52,52,52,-128,-102,52,-29,-107,52,-125,-126,-127,52,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,52,-91,52,52,-134,52,-98,-99,-100,-101,-104,-134,-90,-72,52,52,-53,52,-103,-129,52,-185,-169,-170,-338,-149,-150,52,52,52,-76,52,-92,52,52,-30,52,52,52,52,-186,52,52,52,-152,-159,-339,52,-162,-163,-145,52,-147,52,52,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,52,-77,52,52,-73,-69,52,52,52,52,-35,-36,52,52,52,-171,52,-154,52,-156,-151,-160,-143,-144,-148,-146,-130,52,-177,-178,-221,-220,-237,-87,-84,52,-233,-234,-236,-31,-34,52,52,52,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,52,52,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'VOLATILE':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,27,28,29,30,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,71,72,73,74,75,76,77,78,81,90,91,95,96,97,101,104,106,115,116,118,119,121,122,123,124,125,126,127,128,129,136,137,140,141,183,184,192,197,203,204,205,206,207,208,209,210,211,212,213,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,258,259,262,267,294,298,299,304,311,312,313,322,323,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,448,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,511,512,524,552,553,554,555,556,579,580,585,586,],[53,53,-60,-62,-63,-64,-65,-66,-67,53,53,-70,-71,-52,53,53,53,-128,-102,53,-29,-107,53,-125,-126,-127,53,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,53,-91,53,53,-134,53,-98,-99,-100,-101,-104,-134,-90,-72,53,53,-53,53,-103,-129,53,-185,-169,-170,-338,-149,-150,53,53,53,-76,53,-92,53,53,-30,53,53,53,53,-186,53,53,53,-152,-159,-339,53,-162,-163,-145,53,-147,53,53,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,53,-77,53,53,-73,-69,53,53,53,53,-35,-36,53,53,53,-171,53,-154,53,-156,-151,-160,-143,-144,-148,-146,-130,53,-177,-178,-221,-220,-237,-87,-84,53,-233,-234,-236,-31,-34,53,53,53,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,53,53,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'AUTO':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,71,72,73,74,75,76,77,78,81,90,91,96,97,101,104,106,118,119,121,122,123,127,128,129,137,140,192,206,208,221,222,223,224,225,226,227,228,229,230,231,232,251,262,267,311,312,313,322,330,334,336,337,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[54,54,-60,-62,-63,-64,-65,-66,-67,54,54,-70,-71,-52,54,54,54,-128,-102,54,-29,-107,-125,-126,-127,54,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,54,-91,54,54,-134,54,-98,-99,-100,-101,-104,-134,-90,-72,54,-53,54,-103,-129,-169,-170,-338,-149,-150,-76,54,-92,54,-30,54,-152,-339,54,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-77,-73,-69,-35,-36,54,54,-171,-154,-156,-151,-130,54,-177,-178,-221,-220,-237,-87,-84,54,-233,-234,-236,-31,-34,54,54,-172,-173,-153,-155,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'REGISTER':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,71,72,73,74,75,76,77,78,81,90,91,96,97,101,104,106,118,119,121,122,123,127,128,129,137,140,192,206,208,221,222,223,224,225,226,227,228,229,230,231,232,251,262,267,311,312,313,322,330,334,336,337,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[55,55,-60,-62,-63,-64,-65,-66,-67,55,55,-70,-71,-52,55,55,55,-128,-102,55,-29,-107,-125,-126,-127,55,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,55,-91,55,55,-134,55,-98,-99,-100,-101,-104,-134,-90,-72,55,-53,55,-103,-129,-169,-170,-338,-149,-150,-76,55,-92,55,-30,55,-152,-339,55,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-77,-73,-69,-35,-36,55,55,-171,-154,-156,-151,-130,55,-177,-178,-221,-220,-237,-87,-84,55,-233,-234,-236,-31,-34,55,55,-172,-173,-153,-155,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'STATIC':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,71,72,73,74,75,76,77,78,81,90,91,95,96,97,101,104,106,116,118,119,121,122,123,127,128,129,136,137,140,184,192,197,206,208,221,222,223,224,225,226,227,228,229,230,231,232,251,259,262,267,311,312,313,322,330,334,336,337,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,448,449,458,459,460,463,464,469,471,479,480,483,484,499,508,509,512,524,552,553,554,555,556,579,580,585,586,],[29,29,-60,-62,-63,-64,-65,-66,-67,29,29,-70,-71,-52,29,29,29,-128,-102,29,-29,-107,-125,-126,-127,29,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,29,-91,29,29,-134,29,-98,-99,-100,-101,-104,-134,-90,-72,183,29,-53,29,-103,-129,-185,-169,-170,-338,-149,-150,-76,29,-92,258,29,-30,310,29,-186,-152,-339,29,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-77,402,-73,-69,-35,-36,29,29,-171,-154,-156,-151,-130,29,-177,-178,-221,-220,-237,-87,-84,29,-233,-234,-236,-31,-34,511,29,29,-172,-173,-153,-155,-222,-224,-86,-84,-232,-235,-68,-32,-33,545,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'EXTERN':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,71,72,73,74,75,76,77,78,81,90,91,96,97,101,104,106,118,119,121,122,123,127,128,129,137,140,192,206,208,221,222,223,224,225,226,227,228,229,230,231,232,251,262,267,311,312,313,322,330,334,336,337,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[56,56,-60,-62,-63,-64,-65,-66,-67,56,56,-70,-71,-52,56,56,56,-128,-102,56,-29,-107,-125,-126,-127,56,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,56,-91,56,56,-134,56,-98,-99,-100,-101,-104,-134,-90,-72,56,-53,56,-103,-129,-169,-170,-338,-149,-150,-76,56,-92,56,-30,56,-152,-339,56,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-77,-73,-69,-35,-36,56,56,-171,-154,-156,-151,-130,56,-177,-178,-221,-220,-237,-87,-84,56,-233,-234,-236,-31,-34,56,56,-172,-173,-153,-155,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'TYPEDEF':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,71,72,73,74,75,76,77,78,81,90,91,96,97,101,104,106,118,119,121,122,123,127,128,129,137,140,192,206,208,221,222,223,224,225,226,227,228,229,230,231,232,251,262,267,311,312,313,322,330,334,336,337,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[57,57,-60,-62,-63,-64,-65,-66,-67,57,57,-70,-71,-52,57,57,57,-128,-102,57,-29,-107,-125,-126,-127,57,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,57,-91,57,57,-134,57,-98,-99,-100,-101,-104,-134,-90,-72,57,-53,57,-103,-129,-169,-170,-338,-149,-150,-76,57,-92,57,-30,57,-152,-339,57,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-77,-73,-69,-35,-36,57,57,-171,-154,-156,-151,-130,57,-177,-178,-221,-220,-237,-87,-84,57,-233,-234,-236,-31,-34,57,57,-172,-173,-153,-155,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'_THREAD_LOCAL':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,71,72,73,74,75,76,77,78,81,90,91,96,97,101,104,106,118,119,121,122,123,127,128,129,137,140,192,206,208,221,222,223,224,225,226,227,228,229,230,231,232,251,262,267,311,312,313,322,330,334,336,337,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[58,58,-60,-62,-63,-64,-65,-66,-67,58,58,-70,-71,-52,58,58,58,-128,-102,58,-29,-107,-125,-126,-127,58,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,58,-91,58,58,-134,58,-98,-99,-100,-101,-104,-134,-90,-72,58,-53,58,-103,-129,-169,-170,-338,-149,-150,-76,58,-92,58,-30,58,-152,-339,58,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-77,-73,-69,-35,-36,58,58,-171,-154,-156,-151,-130,58,-177,-178,-221,-220,-237,-87,-84,58,-233,-234,-236,-31,-34,58,58,-172,-173,-153,-155,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'INLINE':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,71,72,73,74,75,76,77,78,81,90,91,96,97,101,104,106,118,119,121,122,123,127,128,129,137,140,192,206,208,221,222,223,224,225,226,227,228,229,230,231,232,251,262,267,311,312,313,322,330,334,336,337,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[59,59,-60,-62,-63,-64,-65,-66,-67,59,59,-70,-71,-52,59,59,59,-128,-102,59,-29,-107,-125,-126,-127,59,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,59,-91,59,59,-134,59,-98,-99,-100,-101,-104,-134,-90,-72,59,-53,59,-103,-129,-169,-170,-338,-149,-150,-76,59,-92,59,-30,59,-152,-339,59,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-77,-73,-69,-35,-36,59,59,-171,-154,-156,-151,-130,59,-177,-178,-221,-220,-237,-87,-84,59,-233,-234,-236,-31,-34,59,59,-172,-173,-153,-155,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'_NORETURN':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,71,72,73,74,75,76,77,78,81,90,91,96,97,101,104,106,118,119,121,122,123,127,128,129,137,140,192,206,208,221,222,223,224,225,226,227,228,229,230,231,232,251,262,267,311,312,313,322,330,334,336,337,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[60,60,-60,-62,-63,-64,-65,-66,-67,60,60,-70,-71,-52,60,60,60,-128,-102,60,-29,-107,-125,-126,-127,60,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,60,-91,60,60,-134,60,-98,-99,-100,-101,-104,-134,-90,-72,60,-53,60,-103,-129,-169,-170,-338,-149,-150,-76,60,-92,60,-30,60,-152,-339,60,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-77,-73,-69,-35,-36,60,60,-171,-154,-156,-151,-130,60,-177,-178,-221,-220,-237,-87,-84,60,-233,-234,-236,-31,-34,60,60,-172,-173,-153,-155,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'_ALIGNAS':([0,2,4,5,6,7,8,9,10,11,12,14,15,19,21,22,23,24,25,27,28,29,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,64,67,68,69,71,72,73,74,75,76,77,78,81,90,91,96,97,101,104,106,118,119,121,122,123,124,125,126,127,128,129,137,140,141,192,203,204,205,206,207,208,209,210,211,212,214,216,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,330,333,334,335,336,337,338,340,341,342,348,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,459,460,463,464,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[61,61,-60,-62,-63,-64,-65,-66,-67,61,61,-70,-71,-52,61,61,61,-128,-102,61,-29,-107,-125,-126,-127,61,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,61,-91,61,61,-134,61,-98,-99,-100,-101,-104,-134,-90,-72,61,-53,61,-103,-129,-169,-170,-338,-149,-150,61,61,61,-76,61,-92,61,-30,61,61,61,61,61,-152,-159,-339,61,-162,-163,-145,-147,61,61,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,61,-77,-73,-69,61,61,61,61,-35,-36,61,61,-171,61,-154,61,-156,-151,-160,-143,-144,-148,-146,-130,61,-177,-178,-221,-220,-237,-87,-84,61,-233,-234,-236,-31,-34,61,61,-172,-173,-153,-155,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'STRUCT':([0,2,4,5,6,7,8,9,10,11,14,15,19,21,22,23,26,27,28,29,34,50,51,52,53,54,55,56,57,58,59,60,64,67,68,70,71,72,73,90,91,96,97,98,99,100,101,102,103,112,116,117,121,124,125,126,127,128,129,137,140,141,193,197,203,204,205,207,208,210,211,213,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,333,335,338,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[62,62,-60,-62,-63,-64,-65,-66,-67,62,-70,-71,-52,-340,-340,-340,62,-340,-29,-107,-340,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,62,-91,62,-340,-134,62,-90,-72,62,-53,-93,-9,-10,-340,-94,-95,-97,-185,-96,-338,62,62,62,-76,62,-92,62,-30,62,62,-186,62,62,62,-159,-339,-162,-163,62,62,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,62,-77,-73,-69,62,62,62,62,-35,-36,62,62,62,62,-160,-130,62,-177,-178,-221,-220,-237,-87,-84,62,-233,-234,-236,-31,-34,62,62,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'UNION':([0,2,4,5,6,7,8,9,10,11,14,15,19,21,22,23,26,27,28,29,34,50,51,52,53,54,55,56,57,58,59,60,64,67,68,70,71,72,73,90,91,96,97,98,99,100,101,102,103,112,116,117,121,124,125,126,127,128,129,137,140,141,193,197,203,204,205,207,208,210,211,213,221,222,223,224,225,226,227,228,229,230,231,232,238,251,262,267,294,298,299,304,311,312,313,322,333,335,338,349,351,353,354,355,356,361,370,371,372,374,375,377,439,440,449,458,465,469,471,479,480,483,484,499,508,509,524,552,553,554,555,556,579,580,585,586,],[63,63,-60,-62,-63,-64,-65,-66,-67,63,-70,-71,-52,-340,-340,-340,63,-340,-29,-107,-340,-134,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-61,63,-91,63,-340,-134,63,-90,-72,63,-53,-93,-9,-10,-340,-94,-95,-97,-185,-96,-338,63,63,63,-76,63,-92,63,-30,63,63,-186,63,63,63,-159,-339,-162,-163,63,63,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,63,-77,-73,-69,63,63,63,63,-35,-36,63,63,63,63,-160,-130,63,-177,-178,-221,-220,-237,-87,-84,63,-233,-234,-236,-31,-34,63,63,-161,-222,-224,-86,-84,-232,-235,-68,-32,-33,-223,-225,-87,-84,-227,-228,-226,-229,-231,-230,]),'LBRACE':([11,15,19,28,36,37,62,63,65,66,67,68,73,90,91,97,118,119,121,122,123,128,129,131,135,140,195,208,221,222,223,224,225,226,227,228,229,230,231,232,238,242,256,262,267,311,312,355,356,358,360,361,369,370,371,374,375,377,392,393,394,405,439,440,469,470,471,474,479,480,483,484,487,489,498,499,504,505,508,509,524,525,526,527,532,533,552,553,554,555,556,562,570,579,580,582,584,585,586,],[-340,-71,-52,-29,121,121,-157,-158,121,-7,-8,-91,-340,-90,-72,-53,121,121,-338,121,121,121,-92,121,121,-30,121,-339,121,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,121,121,-340,-73,-69,-35,-36,-221,-220,121,121,-237,121,-87,-74,-233,-234,-236,-11,121,-12,121,-31,-34,-222,121,-224,121,-86,-75,-232,-235,-340,-201,-340,-68,121,121,-32,-33,-223,121,121,121,121,-11,-225,-87,-74,-227,-228,-340,121,-226,-229,121,121,-231,-230,]),'RBRACE':([15,90,91,121,124,128,139,143,144,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,200,201,202,203,204,205,207,208,210,211,219,220,221,222,223,224,225,226,227,228,229,230,231,232,249,250,255,256,262,263,267,291,292,293,295,296,297,300,301,302,303,328,329,331,333,335,338,355,356,361,370,371,374,375,377,390,391,392,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,461,462,465,469,471,473,479,480,483,484,485,486,487,488,497,499,501,502,505,506,524,531,537,538,552,553,554,555,556,560,561,562,563,574,579,580,585,586,],[-71,-90,-72,-338,208,-340,-328,-306,-255,-256,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,208,-174,-179,208,208,208,-159,-339,-162,-163,208,-5,-6,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-242,-277,-196,-340,-73,-329,-69,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,208,208,-175,208,208,-160,-221,-220,-237,-87,-84,-233,-234,-236,208,-22,-21,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,-272,-273,-274,-275,-276,-295,-296,-297,-298,-299,-176,-180,-161,-222,-224,-240,-86,-84,-232,-235,-243,-197,208,-199,-278,-68,-293,-294,-284,-285,-223,-198,208,-257,-225,-87,-84,-227,-228,-200,-302,208,-309,-303,-226,-229,-231,-230,]),'CASE':([15,90,91,121,128,208,221,222,223,224,225,226,227,228,229,230,231,232,242,262,267,355,356,358,360,361,369,370,371,374,375,377,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[-71,-90,-72,-338,234,-339,234,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,234,-73,-69,-221,-220,234,234,-237,234,-87,-74,-233,-234,-236,-222,234,-224,-86,-75,-232,-235,-68,-223,234,234,234,-225,-87,-74,-227,-228,234,-226,-229,234,234,-231,-230,]),'DEFAULT':([15,90,91,121,128,208,221,222,223,224,225,226,227,228,229,230,231,232,242,262,267,355,356,358,360,361,369,370,371,374,375,377,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[-71,-90,-72,-338,235,-339,235,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,235,-73,-69,-221,-220,235,235,-237,235,-87,-74,-233,-234,-236,-222,235,-224,-86,-75,-232,-235,-68,-223,235,235,235,-225,-87,-74,-227,-228,235,-226,-229,235,235,-231,-230,]),'IF':([15,90,91,121,128,208,221,222,223,224,225,226,227,228,229,230,231,232,242,262,267,355,356,358,360,361,369,370,371,374,375,377,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[-71,-90,-72,-338,237,-339,237,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,237,-73,-69,-221,-220,237,237,-237,237,-87,-74,-233,-234,-236,-222,237,-224,-86,-75,-232,-235,-68,-223,237,237,237,-225,-87,-74,-227,-228,237,-226,-229,237,237,-231,-230,]),'SWITCH':([15,90,91,121,128,208,221,222,223,224,225,226,227,228,229,230,231,232,242,262,267,355,356,358,360,361,369,370,371,374,375,377,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[-71,-90,-72,-338,240,-339,240,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,240,-73,-69,-221,-220,240,240,-237,240,-87,-74,-233,-234,-236,-222,240,-224,-86,-75,-232,-235,-68,-223,240,240,240,-225,-87,-74,-227,-228,240,-226,-229,240,240,-231,-230,]),'WHILE':([15,90,91,121,128,208,221,222,223,224,225,226,227,228,229,230,231,232,242,262,267,355,356,358,360,361,368,369,370,371,374,375,377,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[-71,-90,-72,-338,241,-339,241,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,241,-73,-69,-221,-220,241,241,-237,478,241,-87,-74,-233,-234,-236,-222,241,-224,-86,-75,-232,-235,-68,-223,241,241,241,-225,-87,-74,-227,-228,241,-226,-229,241,241,-231,-230,]),'DO':([15,90,91,121,128,208,221,222,223,224,225,226,227,228,229,230,231,232,242,262,267,355,356,358,360,361,369,370,371,374,375,377,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[-71,-90,-72,-338,242,-339,242,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,242,-73,-69,-221,-220,242,242,-237,242,-87,-74,-233,-234,-236,-222,242,-224,-86,-75,-232,-235,-68,-223,242,242,242,-225,-87,-74,-227,-228,242,-226,-229,242,242,-231,-230,]),'FOR':([15,90,91,121,128,208,221,222,223,224,225,226,227,228,229,230,231,232,242,262,267,355,356,358,360,361,369,370,371,374,375,377,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[-71,-90,-72,-338,243,-339,243,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,243,-73,-69,-221,-220,243,243,-237,243,-87,-74,-233,-234,-236,-222,243,-224,-86,-75,-232,-235,-68,-223,243,243,243,-225,-87,-74,-227,-228,243,-226,-229,243,243,-231,-230,]),'GOTO':([15,90,91,121,128,208,221,222,223,224,225,226,227,228,229,230,231,232,242,262,267,355,356,358,360,361,369,370,371,374,375,377,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[-71,-90,-72,-338,244,-339,244,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,244,-73,-69,-221,-220,244,244,-237,244,-87,-74,-233,-234,-236,-222,244,-224,-86,-75,-232,-235,-68,-223,244,244,244,-225,-87,-74,-227,-228,244,-226,-229,244,244,-231,-230,]),'BREAK':([15,90,91,121,128,208,221,222,223,224,225,226,227,228,229,230,231,232,242,262,267,355,356,358,360,361,369,370,371,374,375,377,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[-71,-90,-72,-338,245,-339,245,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,245,-73,-69,-221,-220,245,245,-237,245,-87,-74,-233,-234,-236,-222,245,-224,-86,-75,-232,-235,-68,-223,245,245,245,-225,-87,-74,-227,-228,245,-226,-229,245,245,-231,-230,]),'CONTINUE':([15,90,91,121,128,208,221,222,223,224,225,226,227,228,229,230,231,232,242,262,267,355,356,358,360,361,369,370,371,374,375,377,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[-71,-90,-72,-338,246,-339,246,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,246,-73,-69,-221,-220,246,246,-237,246,-87,-74,-233,-234,-236,-222,246,-224,-86,-75,-232,-235,-68,-223,246,246,246,-225,-87,-74,-227,-228,246,-226,-229,246,246,-231,-230,]),'RETURN':([15,90,91,121,128,208,221,222,223,224,225,226,227,228,229,230,231,232,242,262,267,355,356,358,360,361,369,370,371,374,375,377,469,470,471,479,480,483,484,499,524,525,526,527,552,553,554,555,556,570,579,580,582,584,585,586,],[-71,-90,-72,-338,247,-339,247,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,247,-73,-69,-221,-220,247,247,-237,247,-87,-74,-233,-234,-236,-222,247,-224,-86,-75,-232,-235,-68,-223,247,247,247,-225,-87,-74,-227,-228,247,-226,-229,247,247,-231,-230,]),'PLUSPLUS':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,139,141,143,147,148,149,150,152,153,154,155,156,158,159,160,161,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,233,234,238,242,247,256,257,258,259,262,263,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,291,292,294,298,300,301,302,303,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,406,429,431,432,433,434,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,501,502,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,561,562,563,565,570,572,574,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,153,-340,-27,-28,-185,-338,153,153,153,-340,-328,153,-306,-287,-288,-289,-286,291,153,153,153,153,-292,-315,-290,-291,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,153,-340,-28,153,-186,-339,153,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-315,153,153,153,153,-340,153,-340,-28,-73,-329,-69,153,153,153,153,153,153,153,153,153,153,153,153,153,153,153,153,153,153,153,153,153,-300,-301,153,153,-334,-335,-336,-337,-287,153,153,-340,153,153,-221,-220,153,153,-237,153,153,153,153,153,-87,-74,153,-233,-234,-236,153,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,153,-12,153,-287,153,153,153,-308,-295,-296,-297,-298,-299,-340,153,153,153,-222,153,-224,153,-86,-75,153,-232,-235,-340,-201,-340,-68,153,-293,-294,153,153,-340,-28,-287,-223,153,153,153,153,153,153,-11,-287,153,153,-225,-87,-74,-227,-228,153,-302,-340,-309,153,153,153,-303,-226,-229,153,153,-231,-230,]),'MINUSMINUS':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,139,141,143,147,148,149,150,152,153,154,155,156,158,159,160,161,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,233,234,238,242,247,256,257,258,259,262,263,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,291,292,294,298,300,301,302,303,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,406,429,431,432,433,434,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,501,502,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,561,562,563,565,570,572,574,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,154,-340,-27,-28,-185,-338,154,154,154,-340,-328,154,-306,-287,-288,-289,-286,292,154,154,154,154,-292,-315,-290,-291,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,154,-340,-28,154,-186,-339,154,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-315,154,154,154,154,-340,154,-340,-28,-73,-329,-69,154,154,154,154,154,154,154,154,154,154,154,154,154,154,154,154,154,154,154,154,154,-300,-301,154,154,-334,-335,-336,-337,-287,154,154,-340,154,154,-221,-220,154,154,-237,154,154,154,154,154,-87,-74,154,-233,-234,-236,154,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,154,-12,154,-287,154,154,154,-308,-295,-296,-297,-298,-299,-340,154,154,154,-222,154,-224,154,-86,-75,154,-232,-235,-340,-201,-340,-68,154,-293,-294,154,154,-340,-28,-287,-223,154,154,154,154,154,154,-11,-287,154,154,-225,-87,-74,-227,-228,154,-302,-340,-309,154,154,154,-303,-226,-229,154,154,-231,-230,]),'SIZEOF':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,156,-340,-27,-28,-185,-338,156,156,156,-340,156,-287,-288,-289,-286,156,156,156,156,-290,-291,156,-340,-28,156,-186,-339,156,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,156,156,156,156,-340,156,-340,-28,-73,-69,156,156,156,156,156,156,156,156,156,156,156,156,156,156,156,156,156,156,156,156,156,156,156,-287,156,156,-340,156,156,-221,-220,156,156,-237,156,156,156,156,156,-87,-74,156,-233,-234,-236,156,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,156,-12,156,-287,156,156,156,-340,156,156,156,-222,156,-224,156,-86,-75,156,-232,-235,-340,-201,-340,-68,156,156,156,-340,-28,-287,-223,156,156,156,156,156,156,-11,-287,156,156,-225,-87,-74,-227,-228,156,-340,156,156,156,-226,-229,156,156,-231,-230,]),'_ALIGNOF':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,157,-340,-27,-28,-185,-338,157,157,157,-340,157,-287,-288,-289,-286,157,157,157,157,-290,-291,157,-340,-28,157,-186,-339,157,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,157,157,157,157,-340,157,-340,-28,-73,-69,157,157,157,157,157,157,157,157,157,157,157,157,157,157,157,157,157,157,157,157,157,157,157,-287,157,157,-340,157,157,-221,-220,157,157,-237,157,157,157,157,157,-87,-74,157,-233,-234,-236,157,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,157,-12,157,-287,157,157,157,-340,157,157,157,-222,157,-224,157,-86,-75,157,-232,-235,-340,-201,-340,-68,157,157,157,-340,-28,-287,-223,157,157,157,157,157,157,-11,-287,157,157,-225,-87,-74,-227,-228,157,-340,157,157,157,-226,-229,157,157,-231,-230,]),'AND':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,139,141,143,145,146,147,148,149,150,151,152,153,154,155,156,158,159,160,161,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,233,234,238,242,247,250,256,257,258,259,262,263,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,291,292,293,294,295,296,297,298,300,301,302,303,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,497,498,499,500,501,502,503,505,506,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,561,562,563,565,570,572,574,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,150,-340,-27,-28,-185,-338,150,150,150,-340,-328,150,-306,282,-258,-287,-288,-289,-286,-277,-279,150,150,150,150,-292,-315,-290,-291,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,150,-340,-28,150,-186,-339,150,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-315,150,150,150,150,-277,-340,150,-340,-28,-73,-329,-69,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,-300,-301,-280,150,-281,-282,-283,150,-334,-335,-336,-337,-287,150,150,-340,150,150,-221,-220,150,150,-237,150,150,150,150,150,-87,-74,150,-233,-234,-236,150,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,150,-12,150,-287,150,150,150,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,-272,282,282,282,282,-295,-296,-297,-298,-299,-340,150,150,150,-222,150,-224,150,-86,-75,150,-232,-235,-340,-201,-278,-340,-68,150,-293,-294,150,-284,-285,150,-340,-28,-287,-223,150,150,150,150,150,150,-11,-287,150,150,-225,-87,-74,-227,-228,150,-302,-340,-309,150,150,150,-303,-226,-229,150,150,-231,-230,]),'PLUS':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,139,141,143,145,146,147,148,149,150,151,152,153,154,155,156,158,159,160,161,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,233,234,238,242,247,250,256,257,258,259,262,263,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,291,292,293,294,295,296,297,298,300,301,302,303,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,497,498,499,500,501,502,503,505,506,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,561,562,563,565,570,572,574,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,148,-340,-27,-28,-185,-338,148,148,148,-340,-328,148,-306,272,-258,-287,-288,-289,-286,-277,-279,148,148,148,148,-292,-315,-290,-291,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,148,-340,-28,148,-186,-339,148,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-315,148,148,148,148,-277,-340,148,-340,-28,-73,-329,-69,148,148,148,148,148,148,148,148,148,148,148,148,148,148,148,148,148,148,148,148,148,-300,-301,-280,148,-281,-282,-283,148,-334,-335,-336,-337,-287,148,148,-340,148,148,-221,-220,148,148,-237,148,148,148,148,148,-87,-74,148,-233,-234,-236,148,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,148,-12,148,-287,148,148,148,-308,-259,-260,-261,-262,-263,272,272,272,272,272,272,272,272,272,272,272,272,272,-295,-296,-297,-298,-299,-340,148,148,148,-222,148,-224,148,-86,-75,148,-232,-235,-340,-201,-278,-340,-68,148,-293,-294,148,-284,-285,148,-340,-28,-287,-223,148,148,148,148,148,148,-11,-287,148,148,-225,-87,-74,-227,-228,148,-302,-340,-309,148,148,148,-303,-226,-229,148,148,-231,-230,]),'MINUS':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,139,141,143,145,146,147,148,149,150,151,152,153,154,155,156,158,159,160,161,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,233,234,238,242,247,250,256,257,258,259,262,263,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,291,292,293,294,295,296,297,298,300,301,302,303,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,497,498,499,500,501,502,503,505,506,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,561,562,563,565,570,572,574,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,149,-340,-27,-28,-185,-338,149,149,149,-340,-328,149,-306,273,-258,-287,-288,-289,-286,-277,-279,149,149,149,149,-292,-315,-290,-291,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,149,-340,-28,149,-186,-339,149,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,-315,149,149,149,149,-277,-340,149,-340,-28,-73,-329,-69,149,149,149,149,149,149,149,149,149,149,149,149,149,149,149,149,149,149,149,149,149,-300,-301,-280,149,-281,-282,-283,149,-334,-335,-336,-337,-287,149,149,-340,149,149,-221,-220,149,149,-237,149,149,149,149,149,-87,-74,149,-233,-234,-236,149,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,149,-12,149,-287,149,149,149,-308,-259,-260,-261,-262,-263,273,273,273,273,273,273,273,273,273,273,273,273,273,-295,-296,-297,-298,-299,-340,149,149,149,-222,149,-224,149,-86,-75,149,-232,-235,-340,-201,-278,-340,-68,149,-293,-294,149,-284,-285,149,-340,-28,-287,-223,149,149,149,149,149,149,-11,-287,149,149,-225,-87,-74,-227,-228,149,-302,-340,-309,149,149,149,-303,-226,-229,149,149,-231,-230,]),'NOT':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,160,-340,-27,-28,-185,-338,160,160,160,-340,160,-287,-288,-289,-286,160,160,160,160,-290,-291,160,-340,-28,160,-186,-339,160,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,160,160,160,160,-340,160,-340,-28,-73,-69,160,160,160,160,160,160,160,160,160,160,160,160,160,160,160,160,160,160,160,160,160,160,160,-287,160,160,-340,160,160,-221,-220,160,160,-237,160,160,160,160,160,-87,-74,160,-233,-234,-236,160,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,160,-12,160,-287,160,160,160,-340,160,160,160,-222,160,-224,160,-86,-75,160,-232,-235,-340,-201,-340,-68,160,160,160,-340,-28,-287,-223,160,160,160,160,160,160,-11,-287,160,160,-225,-87,-74,-227,-228,160,-340,160,160,160,-226,-229,160,160,-231,-230,]),'LNOT':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,161,-340,-27,-28,-185,-338,161,161,161,-340,161,-287,-288,-289,-286,161,161,161,161,-290,-291,161,-340,-28,161,-186,-339,161,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,161,161,161,161,-340,161,-340,-28,-73,-69,161,161,161,161,161,161,161,161,161,161,161,161,161,161,161,161,161,161,161,161,161,161,161,-287,161,161,-340,161,161,-221,-220,161,161,-237,161,161,161,161,161,-87,-74,161,-233,-234,-236,161,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,161,-12,161,-287,161,161,161,-340,161,161,161,-222,161,-224,161,-86,-75,161,-232,-235,-340,-201,-340,-68,161,161,161,-340,-28,-287,-223,161,161,161,161,161,161,-11,-287,161,161,-225,-87,-74,-227,-228,161,-340,161,161,161,-226,-229,161,161,-231,-230,]),'OFFSETOF':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,165,-340,-27,-28,-185,-338,165,165,165,-340,165,-287,-288,-289,-286,165,165,165,165,-290,-291,165,-340,-28,165,-186,-339,165,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,165,165,165,165,-340,165,-340,-28,-73,-69,165,165,165,165,165,165,165,165,165,165,165,165,165,165,165,165,165,165,165,165,165,165,165,-287,165,165,-340,165,165,-221,-220,165,165,-237,165,165,165,165,165,-87,-74,165,-233,-234,-236,165,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,165,-12,165,-287,165,165,165,-340,165,165,165,-222,165,-224,165,-86,-75,165,-232,-235,-340,-201,-340,-68,165,165,165,-340,-28,-287,-223,165,165,165,165,165,165,-11,-287,165,165,-225,-87,-74,-227,-228,165,-340,165,165,165,-226,-229,165,165,-231,-230,]),'INT_CONST_DEC':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,166,-340,-27,-28,-185,-338,166,166,166,-340,166,-287,-288,-289,-286,166,166,166,166,-290,-291,166,-340,-28,166,-186,-339,166,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,166,166,166,166,-340,166,-340,-28,-73,-69,166,166,166,166,166,166,166,166,166,166,166,166,166,166,166,166,166,166,166,166,166,166,166,-287,166,166,-340,166,166,-221,-220,166,166,-237,166,166,166,166,166,-87,-74,166,-233,-234,-236,166,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,166,-12,166,-287,166,166,166,-340,166,166,166,-222,166,-224,166,-86,-75,166,-232,-235,-340,-201,-340,-68,166,166,166,-340,-28,-287,-223,166,166,166,166,166,166,-11,-287,166,166,-225,-87,-74,-227,-228,166,-340,166,166,166,-226,-229,166,166,-231,-230,]),'INT_CONST_OCT':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,167,-340,-27,-28,-185,-338,167,167,167,-340,167,-287,-288,-289,-286,167,167,167,167,-290,-291,167,-340,-28,167,-186,-339,167,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,167,167,167,167,-340,167,-340,-28,-73,-69,167,167,167,167,167,167,167,167,167,167,167,167,167,167,167,167,167,167,167,167,167,167,167,-287,167,167,-340,167,167,-221,-220,167,167,-237,167,167,167,167,167,-87,-74,167,-233,-234,-236,167,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,167,-12,167,-287,167,167,167,-340,167,167,167,-222,167,-224,167,-86,-75,167,-232,-235,-340,-201,-340,-68,167,167,167,-340,-28,-287,-223,167,167,167,167,167,167,-11,-287,167,167,-225,-87,-74,-227,-228,167,-340,167,167,167,-226,-229,167,167,-231,-230,]),'INT_CONST_HEX':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,168,-340,-27,-28,-185,-338,168,168,168,-340,168,-287,-288,-289,-286,168,168,168,168,-290,-291,168,-340,-28,168,-186,-339,168,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,168,168,168,168,-340,168,-340,-28,-73,-69,168,168,168,168,168,168,168,168,168,168,168,168,168,168,168,168,168,168,168,168,168,168,168,-287,168,168,-340,168,168,-221,-220,168,168,-237,168,168,168,168,168,-87,-74,168,-233,-234,-236,168,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,168,-12,168,-287,168,168,168,-340,168,168,168,-222,168,-224,168,-86,-75,168,-232,-235,-340,-201,-340,-68,168,168,168,-340,-28,-287,-223,168,168,168,168,168,168,-11,-287,168,168,-225,-87,-74,-227,-228,168,-340,168,168,168,-226,-229,168,168,-231,-230,]),'INT_CONST_BIN':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,169,-340,-27,-28,-185,-338,169,169,169,-340,169,-287,-288,-289,-286,169,169,169,169,-290,-291,169,-340,-28,169,-186,-339,169,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,169,169,169,169,-340,169,-340,-28,-73,-69,169,169,169,169,169,169,169,169,169,169,169,169,169,169,169,169,169,169,169,169,169,169,169,-287,169,169,-340,169,169,-221,-220,169,169,-237,169,169,169,169,169,-87,-74,169,-233,-234,-236,169,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,169,-12,169,-287,169,169,169,-340,169,169,169,-222,169,-224,169,-86,-75,169,-232,-235,-340,-201,-340,-68,169,169,169,-340,-28,-287,-223,169,169,169,169,169,169,-11,-287,169,169,-225,-87,-74,-227,-228,169,-340,169,169,169,-226,-229,169,169,-231,-230,]),'INT_CONST_CHAR':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,170,-340,-27,-28,-185,-338,170,170,170,-340,170,-287,-288,-289,-286,170,170,170,170,-290,-291,170,-340,-28,170,-186,-339,170,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,170,170,170,170,-340,170,-340,-28,-73,-69,170,170,170,170,170,170,170,170,170,170,170,170,170,170,170,170,170,170,170,170,170,170,170,-287,170,170,-340,170,170,-221,-220,170,170,-237,170,170,170,170,170,-87,-74,170,-233,-234,-236,170,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,170,-12,170,-287,170,170,170,-340,170,170,170,-222,170,-224,170,-86,-75,170,-232,-235,-340,-201,-340,-68,170,170,170,-340,-28,-287,-223,170,170,170,170,170,170,-11,-287,170,170,-225,-87,-74,-227,-228,170,-340,170,170,170,-226,-229,170,170,-231,-230,]),'FLOAT_CONST':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,171,-340,-27,-28,-185,-338,171,171,171,-340,171,-287,-288,-289,-286,171,171,171,171,-290,-291,171,-340,-28,171,-186,-339,171,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,171,171,171,171,-340,171,-340,-28,-73,-69,171,171,171,171,171,171,171,171,171,171,171,171,171,171,171,171,171,171,171,171,171,171,171,-287,171,171,-340,171,171,-221,-220,171,171,-237,171,171,171,171,171,-87,-74,171,-233,-234,-236,171,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,171,-12,171,-287,171,171,171,-340,171,171,171,-222,171,-224,171,-86,-75,171,-232,-235,-340,-201,-340,-68,171,171,171,-340,-28,-287,-223,171,171,171,171,171,171,-11,-287,171,171,-225,-87,-74,-227,-228,171,-340,171,171,171,-226,-229,171,171,-231,-230,]),'HEX_FLOAT_CONST':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,172,-340,-27,-28,-185,-338,172,172,172,-340,172,-287,-288,-289,-286,172,172,172,172,-290,-291,172,-340,-28,172,-186,-339,172,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,172,172,172,172,-340,172,-340,-28,-73,-69,172,172,172,172,172,172,172,172,172,172,172,172,172,172,172,172,172,172,172,172,172,172,172,-287,172,172,-340,172,172,-221,-220,172,172,-237,172,172,172,172,172,-87,-74,172,-233,-234,-236,172,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,172,-12,172,-287,172,172,172,-340,172,172,172,-222,172,-224,172,-86,-75,172,-232,-235,-340,-201,-340,-68,172,172,172,-340,-28,-287,-223,172,172,172,172,172,172,-11,-287,172,172,-225,-87,-74,-227,-228,172,-340,172,172,172,-226,-229,172,172,-231,-230,]),'CHAR_CONST':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,173,-340,-27,-28,-185,-338,173,173,173,-340,173,-287,-288,-289,-286,173,173,173,173,-290,-291,173,-340,-28,173,-186,-339,173,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,173,173,173,173,-340,173,-340,-28,-73,-69,173,173,173,173,173,173,173,173,173,173,173,173,173,173,173,173,173,173,173,173,173,173,173,-287,173,173,-340,173,173,-221,-220,173,173,-237,173,173,173,173,173,-87,-74,173,-233,-234,-236,173,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,173,-12,173,-287,173,173,173,-340,173,173,173,-222,173,-224,173,-86,-75,173,-232,-235,-340,-201,-340,-68,173,173,173,-340,-28,-287,-223,173,173,173,173,173,173,-11,-287,173,173,-225,-87,-74,-227,-228,173,-340,173,173,173,-226,-229,173,173,-231,-230,]),'WCHAR_CONST':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,174,-340,-27,-28,-185,-338,174,174,174,-340,174,-287,-288,-289,-286,174,174,174,174,-290,-291,174,-340,-28,174,-186,-339,174,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,174,174,174,174,-340,174,-340,-28,-73,-69,174,174,174,174,174,174,174,174,174,174,174,174,174,174,174,174,174,174,174,174,174,174,174,-287,174,174,-340,174,174,-221,-220,174,174,-237,174,174,174,174,174,-87,-74,174,-233,-234,-236,174,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,174,-12,174,-287,174,174,174,-340,174,174,174,-222,174,-224,174,-86,-75,174,-232,-235,-340,-201,-340,-68,174,174,174,-340,-28,-287,-223,174,174,174,174,174,174,-11,-287,174,174,-225,-87,-74,-227,-228,174,-340,174,174,174,-226,-229,174,174,-231,-230,]),'U8CHAR_CONST':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,175,-340,-27,-28,-185,-338,175,175,175,-340,175,-287,-288,-289,-286,175,175,175,175,-290,-291,175,-340,-28,175,-186,-339,175,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,175,175,175,175,-340,175,-340,-28,-73,-69,175,175,175,175,175,175,175,175,175,175,175,175,175,175,175,175,175,175,175,175,175,175,175,-287,175,175,-340,175,175,-221,-220,175,175,-237,175,175,175,175,175,-87,-74,175,-233,-234,-236,175,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,175,-12,175,-287,175,175,175,-340,175,175,175,-222,175,-224,175,-86,-75,175,-232,-235,-340,-201,-340,-68,175,175,175,-340,-28,-287,-223,175,175,175,175,175,175,-11,-287,175,175,-225,-87,-74,-227,-228,175,-340,175,175,175,-226,-229,175,175,-231,-230,]),'U16CHAR_CONST':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,176,-340,-27,-28,-185,-338,176,176,176,-340,176,-287,-288,-289,-286,176,176,176,176,-290,-291,176,-340,-28,176,-186,-339,176,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,176,176,176,176,-340,176,-340,-28,-73,-69,176,176,176,176,176,176,176,176,176,176,176,176,176,176,176,176,176,176,176,176,176,176,176,-287,176,176,-340,176,176,-221,-220,176,176,-237,176,176,176,176,176,-87,-74,176,-233,-234,-236,176,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,176,-12,176,-287,176,176,176,-340,176,176,176,-222,176,-224,176,-86,-75,176,-232,-235,-340,-201,-340,-68,176,176,176,-340,-28,-287,-223,176,176,176,176,176,176,-11,-287,176,176,-225,-87,-74,-227,-228,176,-340,176,176,176,-226,-229,176,176,-231,-230,]),'U32CHAR_CONST':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,177,-340,-27,-28,-185,-338,177,177,177,-340,177,-287,-288,-289,-286,177,177,177,177,-290,-291,177,-340,-28,177,-186,-339,177,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,177,177,177,177,-340,177,-340,-28,-73,-69,177,177,177,177,177,177,177,177,177,177,177,177,177,177,177,177,177,177,177,177,177,177,177,-287,177,177,-340,177,177,-221,-220,177,177,-237,177,177,177,177,177,-87,-74,177,-233,-234,-236,177,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,177,-12,177,-287,177,177,177,-340,177,177,177,-222,177,-224,177,-86,-75,177,-232,-235,-340,-201,-340,-68,177,177,177,-340,-28,-287,-223,177,177,177,177,177,177,-11,-287,177,177,-225,-87,-74,-227,-228,177,-340,177,177,177,-226,-229,177,177,-231,-230,]),'STRING_LITERAL':([15,51,52,53,81,90,91,92,94,95,114,115,116,121,126,128,135,136,138,139,141,143,147,148,149,150,153,154,155,156,160,161,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,263,266,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,407,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,139,139,-340,-27,-28,-185,-338,139,139,139,-340,263,-328,139,263,-287,-288,-289,-286,139,139,139,139,-290,-291,139,-340,-28,139,-186,-339,139,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,139,139,139,139,-340,139,-340,-28,-73,-329,139,-69,139,139,139,139,139,139,139,139,139,139,139,139,139,139,139,139,139,139,139,139,139,139,139,-287,139,139,-340,139,139,-221,-220,139,139,-237,139,139,139,139,139,-87,-74,139,-233,-234,-236,139,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,139,-12,139,-287,139,139,139,263,-340,139,139,139,-222,139,-224,139,-86,-75,139,-232,-235,-340,-201,-340,-68,139,139,139,-340,-28,-287,-223,139,139,139,139,139,139,-11,-287,139,139,-225,-87,-74,-227,-228,139,-340,139,139,139,-226,-229,139,139,-231,-230,]),'WSTRING_LITERAL':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,164,178,179,180,181,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,300,301,302,303,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,178,-340,-27,-28,-185,-338,178,178,178,-340,178,-287,-288,-289,-286,178,178,178,178,-290,-291,300,-330,-331,-332,-333,178,-340,-28,178,-186,-339,178,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,178,178,178,178,-340,178,-340,-28,-73,-69,178,178,178,178,178,178,178,178,178,178,178,178,178,178,178,178,178,178,178,178,178,178,178,-334,-335,-336,-337,-287,178,178,-340,178,178,-221,-220,178,178,-237,178,178,178,178,178,-87,-74,178,-233,-234,-236,178,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,178,-12,178,-287,178,178,178,-340,178,178,178,-222,178,-224,178,-86,-75,178,-232,-235,-340,-201,-340,-68,178,178,178,-340,-28,-287,-223,178,178,178,178,178,178,-11,-287,178,178,-225,-87,-74,-227,-228,178,-340,178,178,178,-226,-229,178,178,-231,-230,]),'U8STRING_LITERAL':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,164,178,179,180,181,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,300,301,302,303,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,179,-340,-27,-28,-185,-338,179,179,179,-340,179,-287,-288,-289,-286,179,179,179,179,-290,-291,301,-330,-331,-332,-333,179,-340,-28,179,-186,-339,179,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,179,179,179,179,-340,179,-340,-28,-73,-69,179,179,179,179,179,179,179,179,179,179,179,179,179,179,179,179,179,179,179,179,179,179,179,-334,-335,-336,-337,-287,179,179,-340,179,179,-221,-220,179,179,-237,179,179,179,179,179,-87,-74,179,-233,-234,-236,179,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,179,-12,179,-287,179,179,179,-340,179,179,179,-222,179,-224,179,-86,-75,179,-232,-235,-340,-201,-340,-68,179,179,179,-340,-28,-287,-223,179,179,179,179,179,179,-11,-287,179,179,-225,-87,-74,-227,-228,179,-340,179,179,179,-226,-229,179,179,-231,-230,]),'U16STRING_LITERAL':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,164,178,179,180,181,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,300,301,302,303,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,180,-340,-27,-28,-185,-338,180,180,180,-340,180,-287,-288,-289,-286,180,180,180,180,-290,-291,302,-330,-331,-332,-333,180,-340,-28,180,-186,-339,180,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,180,180,180,180,-340,180,-340,-28,-73,-69,180,180,180,180,180,180,180,180,180,180,180,180,180,180,180,180,180,180,180,180,180,180,180,-334,-335,-336,-337,-287,180,180,-340,180,180,-221,-220,180,180,-237,180,180,180,180,180,-87,-74,180,-233,-234,-236,180,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,180,-12,180,-287,180,180,180,-340,180,180,180,-222,180,-224,180,-86,-75,180,-232,-235,-340,-201,-340,-68,180,180,180,-340,-28,-287,-223,180,180,180,180,180,180,-11,-287,180,180,-225,-87,-74,-227,-228,180,-340,180,180,180,-226,-229,180,180,-231,-230,]),'U32STRING_LITERAL':([15,51,52,53,81,90,91,94,95,114,115,116,121,126,128,135,136,141,147,148,149,150,153,154,155,156,160,161,164,178,179,180,181,182,183,184,195,197,208,221,222,223,224,225,226,227,228,229,230,231,232,234,238,242,247,256,257,258,259,262,267,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,300,301,302,303,306,309,310,323,332,347,355,356,358,360,361,362,365,366,367,369,370,371,372,374,375,377,378,379,380,381,382,383,384,385,386,387,388,389,392,393,394,397,400,401,402,405,448,455,457,467,469,470,471,474,479,480,482,483,484,487,489,498,499,500,503,510,511,512,520,524,525,526,527,528,529,532,533,543,544,545,552,553,554,555,556,559,562,565,570,572,579,580,582,584,585,586,],[-71,-131,-132,-133,-134,-90,-72,181,-340,-27,-28,-185,-338,181,181,181,-340,181,-287,-288,-289,-286,181,181,181,181,-290,-291,303,-330,-331,-332,-333,181,-340,-28,181,-186,-339,181,-219,-217,-218,-78,-79,-80,-81,-82,-83,-84,-85,181,181,181,181,-340,181,-340,-28,-73,-69,181,181,181,181,181,181,181,181,181,181,181,181,181,181,181,181,181,181,181,181,181,181,181,-334,-335,-336,-337,-287,181,181,-340,181,181,-221,-220,181,181,-237,181,181,181,181,181,-87,-74,181,-233,-234,-236,181,-244,-245,-246,-247,-248,-249,-250,-251,-252,-253,-254,-11,181,-12,181,-287,181,181,181,-340,181,181,181,-222,181,-224,181,-86,-75,181,-232,-235,-340,-201,-340,-68,181,181,181,-340,-28,-287,-223,181,181,181,181,181,181,-11,-287,181,181,-225,-87,-74,-227,-228,181,-340,181,181,181,-226,-229,181,181,-231,-230,]),'ELSE':([15,91,208,225,226,227,228,229,230,232,262,267,355,361,370,371,374,375,377,469,471,479,480,483,484,499,524,552,553,554,555,556,579,580,585,586,],[-71,-72,-339,-78,-79,-80,-81,-82,-83,-85,-73,-69,-221,-237,-87,-84,-233,-234,-236,-222,-224,-86,-84,-232,-235,-68,-223,-225,570,-84,-227,-228,-226,-229,-231,-230,]),'PPPRAGMASTR':([15,],[91,]),'EQUALS':([19,28,73,86,87,88,89,97,111,130,132,139,140,143,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,202,208,233,250,252,263,291,292,293,295,296,297,300,301,302,303,311,312,395,396,403,404,406,429,431,432,433,434,439,440,490,492,493,494,497,501,502,505,506,508,509,534,535,536,561,563,574,],[-52,-29,-181,135,-182,-54,-37,-53,195,-181,-55,-328,-30,-306,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,332,-339,-315,379,-38,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-35,-36,489,-202,-43,-44,-308,-295,-296,-297,-298,-299,-31,-34,-203,-205,-39,-42,-278,-293,-294,-284,-285,-32,-33,-204,-40,-41,-302,-309,-303,]),'COMMA':([19,24,25,28,29,30,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,51,52,53,54,55,56,57,58,59,60,73,74,75,76,77,78,81,84,85,86,87,88,89,97,104,106,108,110,111,113,114,115,116,118,119,122,123,130,132,139,140,142,143,144,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,187,189,190,191,192,196,197,200,201,202,206,208,212,214,216,233,239,248,249,250,252,253,254,255,263,265,291,292,293,295,296,297,300,301,302,303,311,312,315,316,317,318,319,320,321,324,325,326,327,328,329,330,331,334,336,337,340,341,342,344,345,346,348,349,350,352,353,354,376,391,403,404,406,408,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,427,428,429,430,431,432,433,434,438,439,440,444,445,446,447,459,460,461,462,463,464,468,472,473,475,476,477,485,486,488,493,494,497,501,502,505,506,508,509,515,516,518,522,523,531,535,536,537,538,539,546,547,548,549,550,551,557,560,561,563,566,567,574,576,577,578,],[-52,-128,-102,-29,-107,-340,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-181,-98,-99,-100,-101,-104,-134,134,-135,-137,-182,-54,-37,-53,-103,-129,194,-139,-141,-183,-27,-28,-185,-169,-170,-149,-150,-181,-55,-328,-30,266,-306,-255,-256,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,313,314,-189,-194,-340,-184,-186,331,-174,-179,-152,-339,-145,-147,-340,-315,365,-238,-242,-277,-38,-136,-138,-196,-329,365,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-35,-36,-191,-192,-193,-207,-56,-1,-2,-45,-209,-140,-142,331,331,-171,-175,-154,-156,-151,-143,-144,-148,466,-164,-166,-146,-130,-206,-207,-177,-178,365,487,-43,-44,-308,365,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,-272,-273,-274,-275,-276,365,503,-295,-313,-296,-297,-298,-299,507,-31,-34,-190,-195,-57,-208,-172,-173,-176,-180,-153,-155,-168,365,-240,-239,365,365,-243,-197,-199,-39,-42,-278,-293,-294,-284,-285,-32,-33,-210,-216,-214,-165,-167,-198,-40,-41,562,-257,-314,-50,-51,-212,-211,-213,-215,365,-200,-302,-309,-46,-49,-303,365,-47,-48,]),'RPAREN':([19,24,25,28,29,30,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,51,52,53,54,55,56,57,58,59,60,74,75,76,77,78,81,88,89,93,96,97,104,106,113,114,115,116,118,119,122,123,132,133,137,138,139,140,142,143,144,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,185,186,187,188,189,190,191,192,196,197,206,208,212,214,215,216,217,218,239,248,249,250,252,260,261,263,264,265,288,291,292,293,295,296,297,300,301,302,303,311,312,315,316,317,318,319,320,321,322,324,325,330,334,336,337,340,341,342,348,349,350,351,352,353,354,355,357,363,364,403,404,406,407,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,428,429,430,431,432,433,434,435,436,437,439,440,443,444,445,446,447,449,450,451,452,453,454,458,459,460,463,464,472,473,475,476,477,485,493,494,497,501,502,505,506,508,509,513,514,515,516,518,521,535,536,538,539,540,541,546,547,548,549,550,551,557,559,561,563,566,567,572,573,574,575,577,578,581,583,],[-52,-128,-102,-29,-107,-340,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-98,-99,-100,-101,-104,-134,-54,-37,140,-340,-53,-103,-129,-183,-27,-28,-185,-169,-170,-149,-150,-55,252,-340,262,-328,-30,267,-306,-255,-256,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,311,312,-187,-17,-18,-189,-194,-340,-184,-186,-152,-339,-145,-147,349,-340,353,354,-14,-238,-242,-277,-38,403,404,-329,405,406,429,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-35,-36,-191,-192,-193,-207,-56,-1,-2,-340,-45,-209,-171,-154,-156,-151,-143,-144,-148,-146,-130,-206,-340,-207,-177,-178,-221,-13,473,474,-43,-44,-308,499,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,-272,-273,-274,-275,-276,502,-295,-313,-296,-297,-298,-299,504,505,506,-31,-34,-188,-190,-195,-57,-208,-340,515,516,-207,-23,-24,-340,-172,-173,-153,-155,525,-240,-239,526,527,-243,-39,-42,-278,-293,-294,-284,-285,-32,-33,546,547,-210,-216,-214,551,-40,-41,-257,-314,563,-310,-50,-51,-212,-211,-213,-215,571,-340,-302,-309,-46,-49,-340,582,-303,-311,-47,-48,584,-312,]),'COLON':([19,24,28,31,32,33,35,38,39,40,41,42,43,44,45,46,47,48,49,51,52,53,81,87,88,89,97,106,118,119,122,123,130,132,139,140,143,144,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,206,208,209,212,214,233,235,248,249,250,252,263,291,292,293,295,296,297,300,301,302,303,311,312,330,334,336,337,340,341,342,346,348,349,353,354,359,403,404,406,408,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,439,440,459,460,463,464,466,473,475,485,493,494,497,501,502,505,506,508,509,535,536,538,561,563,574,],[-52,-128,-29,-125,-126,-127,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-131,-132,-133,-134,-182,-54,-37,-53,-129,-169,-170,-149,-150,-181,-55,-328,-30,-306,-255,-256,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-152,-339,347,-145,-147,358,360,-238,-242,-277,-38,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-35,-36,-171,-154,-156,-151,-143,-144,-148,467,-146,-130,-177,-178,470,-43,-44,-308,500,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,-272,-273,-274,-275,-276,-295,-296,-297,-298,-299,-31,-34,-172,-173,-153,-155,347,-240,-239,-243,-39,-42,-278,-293,-294,-284,-285,-32,-33,-40,-41,-257,-302,-309,-303,]),'LBRACKET':([19,24,25,28,29,30,31,32,33,34,35,38,39,40,41,42,43,44,45,46,47,48,49,51,52,53,54,55,56,57,58,59,60,74,75,76,77,78,81,88,89,97,104,106,113,114,115,116,118,119,121,122,123,132,139,140,143,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,192,196,197,206,208,212,214,216,233,252,256,263,291,292,300,301,302,303,311,312,318,319,322,324,325,330,334,336,337,340,341,342,348,349,351,352,353,354,395,396,403,404,406,429,431,432,433,434,439,440,446,447,452,459,460,463,464,487,490,492,493,494,498,501,502,508,509,515,516,518,534,535,536,540,541,546,547,548,549,550,551,561,562,563,566,567,574,575,577,578,583,],[95,-128,-102,-29,-107,-340,-125,-126,-127,-129,-241,-113,-114,-115,-116,-117,-118,-119,-120,-121,-122,-123,-124,-131,-132,-133,-105,-106,-108,-109,-110,-111,-112,-98,-99,-100,-101,-104,-134,136,-37,95,-103,-129,-183,-27,-28,-185,-169,-170,-338,-149,-150,136,-328,-30,-306,287,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,323,-184,-186,-152,-339,-145,-147,323,-315,-38,397,-329,-300,-301,-334,-335,-336,-337,-35,-36,323,448,323,-45,457,-171,-154,-156,-151,-143,-144,-148,-146,-130,323,323,-177,-178,397,-202,-43,-44,-308,-295,-296,-297,-298,-299,-31,-34,448,457,323,-172,-173,-153,-155,397,-203,-205,-39,-42,397,-293,-294,-32,-33,-210,-216,-214,-204,-40,-41,565,-310,-50,-51,-212,-211,-213,-215,-302,397,-309,-46,-49,-303,-311,-47,-48,-312,]),'RBRACKET':([51,52,53,81,95,114,115,116,136,139,143,144,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,184,197,208,248,249,250,257,259,263,291,292,293,295,296,297,300,301,302,303,305,306,307,308,323,399,400,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,427,429,431,432,433,434,441,442,448,455,456,457,473,475,485,491,495,496,497,501,502,505,506,510,512,517,519,520,538,542,543,561,563,568,569,574,576,],[-131,-132,-133,-134,-340,-27,-28,-185,-340,-328,-306,-255,-256,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-340,-28,-186,-339,-238,-242,-277,-340,-28,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,439,440,-3,-4,-340,493,494,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,-272,-273,-274,-275,-276,501,-295,-296,-297,-298,-299,508,509,-340,-340,518,-340,-240,-239,-243,534,535,536,-278,-293,-294,-284,-285,-340,-28,548,549,550,-257,566,567,-302,-309,577,578,-303,583,]),'PERIOD':([121,139,143,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,256,263,291,292,300,301,302,303,395,396,406,429,431,432,433,434,487,490,492,498,501,502,534,540,541,561,562,563,574,575,583,],[-338,-328,-306,289,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,398,-329,-300,-301,-334,-335,-336,-337,398,-202,-308,-295,-296,-297,-298,-299,398,-203,-205,398,-293,-294,-204,564,-310,-302,398,-309,-303,-311,-312,]),'ARROW':([139,143,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,263,291,292,300,301,302,303,406,429,431,432,433,434,501,502,561,563,574,],[-328,-306,290,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-329,-300,-301,-334,-335,-336,-337,-308,-295,-296,-297,-298,-299,-293,-294,-302,-309,-303,]),'CONDOP':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,268,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,-272,-273,-274,-275,-276,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'DIVIDE':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,270,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,270,270,270,270,270,270,270,270,270,270,270,270,270,270,270,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'MOD':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,271,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,271,271,271,271,271,271,271,271,271,271,271,271,271,271,271,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'RSHIFT':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,274,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,274,274,274,274,274,274,274,274,274,274,274,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'LSHIFT':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,275,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,275,275,275,275,275,275,275,275,275,275,275,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'LT':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,276,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,276,276,276,276,276,276,276,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'LE':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,277,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,277,277,277,277,277,277,277,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'GE':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,278,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,278,278,278,278,278,278,278,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'GT':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,279,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,279,279,279,279,279,279,279,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'EQ':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,280,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,280,280,280,280,280,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'NE':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,281,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,281,281,281,281,281,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'OR':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,283,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,-272,-273,-274,283,283,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'XOR':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,284,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,-272,284,-274,284,284,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'LAND':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,285,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,-272,-273,-274,-275,285,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'LOR':([139,143,145,146,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,286,-258,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,-277,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-259,-260,-261,-262,-263,-264,-265,-266,-267,-268,-269,-270,-271,-272,-273,-274,-275,-276,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'XOREQUAL':([139,143,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,380,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'TIMESEQUAL':([139,143,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,381,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'DIVEQUAL':([139,143,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,382,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'MODEQUAL':([139,143,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,383,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'PLUSEQUAL':([139,143,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,384,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'MINUSEQUAL':([139,143,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,385,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'LSHIFTEQUAL':([139,143,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,386,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'RSHIFTEQUAL':([139,143,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,387,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'ANDEQUAL':([139,143,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,388,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'OREQUAL':([139,143,151,152,158,159,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,208,233,250,263,291,292,293,295,296,297,300,301,302,303,406,429,431,432,433,434,497,501,502,505,506,561,563,574,],[-328,-306,-277,-279,-292,-315,-304,-305,-307,-316,-317,-318,-319,-320,-321,-322,-323,-324,-325,-326,-327,-330,-331,-332,-333,-339,-315,389,-329,-300,-301,-280,-281,-282,-283,-334,-335,-336,-337,-308,-295,-296,-297,-298,-299,-278,-293,-294,-284,-285,-302,-309,-303,]),'ELLIPSIS':([313,],[443,]),}

_lr_action = {}
for _k, _v in _lr_action_items.items():
   for _x,_y in zip(_v[0],_v[1]):
      if not _x in _lr_action:  _lr_action[_x] = {}
      _lr_action[_x][_k] = _y
del _lr_action_items

_lr_goto_items = {'translation_unit_or_empty':([0,],[1,]),'translation_unit':([0,],[2,]),'empty':([0,11,12,21,22,23,26,27,30,34,69,70,71,73,95,96,101,128,136,137,182,183,192,209,216,221,242,256,257,258,322,323,351,358,360,369,372,448,449,455,457,458,470,482,487,498,510,511,525,526,527,529,559,562,570,572,582,584,],[3,66,83,99,99,99,107,99,114,99,83,107,99,66,114,188,99,220,114,188,307,114,320,343,320,357,357,392,307,114,453,114,453,357,357,357,357,114,188,307,307,453,357,357,533,533,307,114,357,357,357,357,357,533,357,357,357,357,]),'external_declaration':([0,2,],[4,64,]),'function_definition':([0,2,],[5,5,]),'declaration':([0,2,11,67,73,128,221,372,],[6,6,68,129,68,223,223,482,]),'pp_directive':([0,2,],[7,7,]),'pppragma_directive':([0,2,124,128,203,204,205,221,242,333,335,358,360,369,470,525,526,527,570,582,584,],[8,8,211,231,211,211,211,231,371,211,211,371,371,480,371,554,371,371,371,371,371,]),'static_assert':([0,2,128,221,242,358,360,369,470,525,526,527,570,582,584,],[10,10,232,232,232,232,232,232,232,232,232,232,232,232,232,]),'id_declarator':([0,2,12,17,26,69,70,82,134,192,194,209,322,466,],[11,11,73,93,111,130,111,93,130,315,130,130,93,130,]),'declaration_specifiers':([0,2,11,67,73,96,128,137,221,313,322,351,372,449,458,],[12,12,69,69,69,192,69,192,69,192,192,192,69,192,192,]),'decl_body':([0,2,11,67,73,128,221,372,],[13,13,13,13,13,13,13,13,]),'direct_id_declarator':([0,2,12,17,20,26,69,70,80,82,134,192,194,209,318,322,452,466,],[19,19,19,19,97,19,19,19,97,19,19,19,19,19,97,19,97,19,]),'pointer':([0,2,12,17,26,69,70,82,113,134,192,194,209,216,322,351,466,],[20,20,80,20,20,80,20,80,196,80,318,80,80,352,452,352,80,]),'type_qualifier':([0,2,11,12,21,22,23,27,30,34,67,69,71,73,95,96,101,115,124,125,126,128,136,137,141,183,184,192,203,204,205,209,213,216,221,238,258,259,294,298,299,304,313,322,323,333,335,351,372,448,449,458,511,512,],[21,21,21,74,21,21,21,21,116,21,21,74,21,21,116,21,21,197,116,116,116,21,116,21,116,116,197,74,116,116,116,341,197,341,21,116,116,197,116,116,116,116,21,21,116,116,116,21,21,116,21,21,116,197,]),'storage_class_specifier':([0,2,11,12,21,22,23,27,34,67,69,71,73,96,101,128,137,192,221,313,322,351,372,449,458,],[22,22,22,75,22,22,22,22,22,22,75,22,22,22,22,22,22,75,22,22,22,22,22,22,22,]),'function_specifier':([0,2,11,12,21,22,23,27,34,67,69,71,73,96,101,128,137,192,221,313,322,351,372,449,458,],[23,23,23,76,23,23,23,23,23,23,76,23,23,23,23,23,23,76,23,23,23,23,23,23,23,]),'type_specifier_no_typeid':([0,2,11,12,26,67,69,70,73,96,124,125,126,128,137,141,192,193,203,204,205,209,213,216,221,238,294,298,299,304,313,322,333,335,351,372,449,458,],[24,24,24,77,24,24,77,24,24,24,24,24,24,24,24,24,77,24,24,24,24,340,24,340,24,24,24,24,24,24,24,24,24,24,24,24,24,24,]),'type_specifier':([0,2,11,26,67,70,73,96,124,125,126,128,137,141,193,203,204,205,213,221,238,294,298,299,304,313,322,333,335,351,372,449,458,],[25,25,25,104,25,104,25,25,212,212,212,25,25,212,104,212,212,212,348,25,212,212,212,212,212,25,25,212,212,25,25,25,25,]),'declaration_specifiers_no_type':([0,2,11,21,22,23,27,34,67,71,73,96,101,128,137,221,313,322,351,372,449,458,],[26,26,70,100,100,100,100,100,70,100,70,193,100,70,193,70,193,193,193,70,193,193,]),'alignment_specifier':([0,2,11,12,21,22,23,27,34,67,69,71,73,96,101,124,125,126,128,137,141,192,203,204,205,209,216,221,238,294,298,299,304,313,322,333,335,351,372,449,458,],[27,27,27,78,27,27,27,27,27,27,78,27,27,27,27,214,214,214,27,27,214,78,214,214,214,342,342,27,214,214,214,214,214,27,27,214,214,27,27,27,27,]),'typedef_name':([0,2,11,26,67,70,73,96,124,125,126,128,137,141,193,203,204,205,213,221,238,294,298,299,304,313,322,333,335,351,372,449,458,],[31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,]),'enum_specifier':([0,2,11,26,67,70,73,96,124,125,126,128,137,141,193,203,204,205,213,221,238,294,298,299,304,313,322,333,335,351,372,449,458,],[32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,]),'struct_or_union_specifier':([0,2,11,26,67,70,73,96,124,125,126,128,137,141,193,203,204,205,213,221,238,294,298,299,304,313,322,333,335,351,372,449,458,],[33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,33,]),'atomic_specifier':([0,2,11,21,22,23,26,27,34,67,70,71,73,96,101,124,125,126,128,137,141,193,203,204,205,213,221,238,294,298,299,304,313,322,333,335,351,372,449,458,],[34,34,71,101,101,101,106,101,101,71,106,101,71,34,101,106,106,106,71,34,106,106,106,106,106,106,71,106,106,106,106,106,34,34,106,106,34,71,34,34,]),'struct_or_union':([0,2,11,26,67,70,73,96,124,125,126,128,137,141,193,203,204,205,213,221,238,294,298,299,304,313,322,333,335,351,372,449,458,],[37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,37,]),'declaration_list_opt':([11,73,],[65,131,]),'declaration_list':([11,73,],[67,67,]),'init_declarator_list_opt':([12,69,],[79,79,]),'init_declarator_list':([12,69,],[84,84,]),'init_declarator':([12,69,134,194,],[85,85,253,326,]),'declarator':([12,69,134,194,209,466,],[86,86,86,86,346,346,]),'typeid_declarator':([12,69,82,134,194,209,466,],[87,87,133,87,87,87,87,]),'direct_typeid_declarator':([12,69,80,82,134,194,209,466,],[88,88,132,88,88,88,88,88,]),'declaration_specifiers_no_type_opt':([21,22,23,27,34,71,101,],[98,102,103,112,117,117,117,]),'id_init_declarator_list_opt':([26,70,],[105,105,]),'id_init_declarator_list':([26,70,],[108,108,]),'id_init_declarator':([26,70,],[110,110,]),'type_qualifier_list_opt':([30,95,136,183,258,323,448,511,],[113,182,257,309,401,455,510,544,]),'type_qualifier_list':([30,95,124,125,126,136,141,183,203,204,205,238,258,294,298,299,304,323,333,335,448,511,],[115,184,213,213,213,259,213,115,213,213,213,213,115,213,213,213,213,115,213,213,512,115,]),'brace_open':([36,37,65,118,119,122,123,128,131,135,195,221,238,242,358,360,369,393,405,470,474,504,505,525,526,527,532,570,582,584,],[120,124,128,198,199,203,204,128,128,256,256,128,128,128,128,128,128,256,498,128,498,498,498,128,128,128,256,128,128,128,]),'compound_statement':([65,128,131,221,238,242,358,360,369,470,525,526,527,570,582,584,],[127,227,251,227,363,227,227,227,227,227,227,227,227,227,227,227,]),'unified_string_literal':([92,94,126,128,135,141,153,154,155,156,182,195,221,234,238,242,247,257,266,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,309,310,332,347,358,360,362,365,366,367,369,372,378,393,397,401,402,405,455,457,467,470,474,482,500,503,510,525,526,527,528,529,532,544,545,559,565,570,572,582,584,],[138,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,407,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,143,]),'constant_expression':([94,126,234,332,347,397,467,],[142,218,359,462,468,491,523,]),'conditional_expression':([94,126,128,135,141,182,195,221,234,238,242,247,257,268,287,288,294,298,309,310,332,347,358,360,362,365,366,367,369,372,378,393,397,401,402,455,457,467,470,482,500,503,510,525,526,527,528,529,532,544,545,559,565,570,572,582,584,],[144,144,249,249,249,249,249,249,144,249,249,249,249,249,249,249,249,249,249,249,144,144,249,249,249,249,249,249,249,249,249,249,144,249,249,249,249,144,249,249,538,249,249,249,249,249,249,249,249,249,249,249,249,249,249,249,249,]),'binary_expression':([94,126,128,135,141,182,195,221,234,238,242,247,257,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,309,310,332,347,358,360,362,365,366,367,369,372,378,393,397,401,402,455,457,467,470,482,500,503,510,525,526,527,528,529,532,544,545,559,565,570,572,582,584,],[145,145,145,145,145,145,145,145,145,145,145,145,145,145,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,425,426,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,]),'cast_expression':([94,126,128,135,141,155,182,195,221,234,238,242,247,257,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,309,310,332,347,358,360,362,365,366,367,369,372,378,393,397,401,402,405,455,457,467,470,474,482,500,503,510,525,526,527,528,529,532,544,545,559,565,570,572,582,584,],[146,146,146,146,146,296,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,497,146,146,146,146,497,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,]),'unary_expression':([94,126,128,135,141,153,154,155,156,182,195,221,234,238,242,247,257,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,309,310,332,347,358,360,362,365,366,367,369,372,378,393,397,401,402,405,455,457,467,470,474,482,500,503,510,525,526,527,528,529,532,544,545,559,565,570,572,582,584,],[151,151,250,250,250,293,295,151,297,250,250,250,151,250,250,250,250,250,151,151,151,151,151,151,151,151,151,151,151,151,151,151,151,151,151,151,250,250,250,250,250,250,151,151,250,250,250,250,250,250,250,250,250,250,151,250,250,151,250,250,151,250,151,250,151,250,250,250,250,250,250,250,250,250,250,250,250,250,250,250,250,]),'postfix_expression':([94,126,128,135,141,153,154,155,156,182,195,221,234,238,242,247,257,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,309,310,332,347,358,360,362,365,366,367,369,372,378,393,397,401,402,405,455,457,467,470,474,482,500,503,510,525,526,527,528,529,532,544,545,559,565,570,572,582,584,],[152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,152,]),'unary_operator':([94,126,128,135,141,153,154,155,156,182,195,221,234,238,242,247,257,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,309,310,332,347,358,360,362,365,366,367,369,372,378,393,397,401,402,405,455,457,467,470,474,482,500,503,510,525,526,527,528,529,532,544,545,559,565,570,572,582,584,],[155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,155,]),'primary_expression':([94,126,128,135,141,153,154,155,156,182,195,221,234,238,242,247,257,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,309,310,332,347,358,360,362,365,366,367,369,372,378,393,397,401,402,405,455,457,467,470,474,482,500,503,510,525,526,527,528,529,532,544,545,559,565,570,572,582,584,],[158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,158,]),'identifier':([94,96,126,128,135,137,141,153,154,155,156,182,195,221,234,238,242,247,257,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,309,310,314,332,347,358,360,362,365,366,367,369,372,378,393,397,398,401,402,405,449,455,457,467,470,474,482,500,503,507,510,525,526,527,528,529,532,544,545,559,564,565,570,572,582,584,],[162,191,162,162,162,191,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,162,445,162,162,162,162,162,162,162,162,162,162,162,162,162,492,162,162,162,191,162,162,162,162,162,162,162,162,541,162,162,162,162,162,162,162,162,162,162,575,162,162,162,162,162,]),'constant':([94,126,128,135,141,153,154,155,156,182,195,221,234,238,242,247,257,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,309,310,332,347,358,360,362,365,366,367,369,372,378,393,397,401,402,405,455,457,467,470,474,482,500,503,510,525,526,527,528,529,532,544,545,559,565,570,572,582,584,],[163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,163,]),'unified_wstring_literal':([94,126,128,135,141,153,154,155,156,182,195,221,234,238,242,247,257,268,269,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,285,286,287,288,294,298,309,310,332,347,358,360,362,365,366,367,369,372,378,393,397,401,402,405,455,457,467,470,474,482,500,503,510,525,526,527,528,529,532,544,545,559,565,570,572,582,584,],[164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,164,]),'parameter_type_list':([96,137,322,351,449,458,],[185,260,454,454,513,454,]),'identifier_list_opt':([96,137,449,],[186,261,514,]),'parameter_list':([96,137,322,351,449,458,],[187,187,187,187,187,187,]),'identifier_list':([96,137,449,],[189,189,189,]),'parameter_declaration':([96,137,313,322,351,449,458,],[190,190,444,190,190,190,190,]),'enumerator_list':([120,198,199,],[200,328,329,]),'enumerator':([120,198,199,331,],[201,201,201,461,]),'struct_declaration_list':([124,203,204,],[205,333,335,]),'brace_close':([124,200,203,204,205,219,328,329,333,335,390,487,537,562,],[206,330,334,336,337,355,459,460,463,464,486,531,561,574,]),'struct_declaration':([124,203,204,205,333,335,],[207,207,207,338,338,338,]),'specifier_qualifier_list':([124,125,126,141,203,204,205,238,294,298,299,304,333,335,],[209,216,216,216,209,209,209,216,216,216,216,216,209,209,]),'type_name':([125,126,141,238,294,298,299,304,],[215,217,264,364,435,436,437,438,]),'block_item_list_opt':([128,],[219,]),'block_item_list':([128,],[221,]),'block_item':([128,221,],[222,356,]),'statement':([128,221,242,358,360,369,470,525,526,527,570,582,584,],[224,224,370,370,370,479,370,553,370,370,370,370,370,]),'labeled_statement':([128,221,242,358,360,369,470,525,526,527,570,582,584,],[225,225,225,225,225,225,225,225,225,225,225,225,225,]),'expression_statement':([128,221,242,358,360,369,470,525,526,527,570,582,584,],[226,226,226,226,226,226,226,226,226,226,226,226,226,]),'selection_statement':([128,221,242,358,360,369,470,525,526,527,570,582,584,],[228,228,228,228,228,228,228,228,228,228,228,228,228,]),'iteration_statement':([128,221,242,358,360,369,470,525,526,527,570,582,584,],[229,229,229,229,229,229,229,229,229,229,229,229,229,]),'jump_statement':([128,221,242,358,360,369,470,525,526,527,570,582,584,],[230,230,230,230,230,230,230,230,230,230,230,230,230,]),'expression_opt':([128,221,242,358,360,369,372,470,482,525,526,527,529,559,570,572,582,584,],[236,236,236,236,236,236,481,236,530,236,236,236,558,573,236,581,236,236,]),'expression':([128,141,221,238,242,247,268,287,294,298,358,360,362,366,367,369,372,470,482,525,526,527,528,529,559,565,570,572,582,584,],[239,265,239,265,239,376,408,427,265,265,239,239,472,476,477,239,239,239,239,239,239,239,557,239,239,576,239,239,239,239,]),'assignment_expression':([128,135,141,182,195,221,238,242,247,257,268,287,288,294,298,309,310,358,360,362,365,366,367,369,372,378,393,401,402,455,457,470,482,503,510,525,526,527,528,529,532,544,545,559,565,570,572,582,584,],[248,255,248,308,255,248,248,248,248,308,248,248,430,248,248,441,442,248,248,248,475,248,248,248,248,485,255,495,496,308,308,248,248,539,308,248,248,248,248,248,255,568,569,248,248,248,248,248,248,]),'initializer':([135,195,393,532,],[254,327,488,560,]),'assignment_expression_opt':([182,257,455,457,510,],[305,399,517,519,542,]),'typeid_noparen_declarator':([192,],[316,]),'abstract_declarator_opt':([192,216,],[317,350,]),'direct_typeid_noparen_declarator':([192,318,],[319,446,]),'abstract_declarator':([192,216,322,351,],[321,321,450,450,]),'direct_abstract_declarator':([192,216,318,322,351,352,452,],[325,325,447,325,325,447,447,]),'struct_declarator_list_opt':([209,],[339,]),'struct_declarator_list':([209,],[344,]),'struct_declarator':([209,466,],[345,522,]),'pragmacomp_or_statement':([242,358,360,470,525,526,527,570,582,584,],[368,469,471,524,552,555,556,579,585,586,]),'pppragma_directive_list':([242,358,360,470,525,526,527,570,582,584,],[369,369,369,369,369,369,369,369,369,369,]),'assignment_operator':([250,],[378,]),'initializer_list_opt':([256,],[390,]),'initializer_list':([256,498,],[391,537,]),'designation_opt':([256,487,498,562,],[393,532,393,532,]),'designation':([256,487,498,562,],[394,394,394,394,]),'designator_list':([256,487,498,562,],[395,395,395,395,]),'designator':([256,395,487,498,562,],[396,490,396,396,396,]),'argument_expression_list':([288,],[428,]),'parameter_type_list_opt':([322,351,458,],[451,451,521,]),'offsetof_member_designator':([507,],[540,]),}

_lr_goto = {}
for _k, _v in _lr_goto_items.items():
   for _x, _y in zip(_v[0], _v[1]):
       if not _x in _lr_goto: _lr_goto[_x] = {}
       _lr_goto[_x][_k] = _y
del _lr_goto_items
_lr_productions = [
  ("S' -> translation_unit_or_empty","S'",1,None,None,None),
  ('abstract_declarator_opt -> empty','abstract_declarator_opt',1,'p_abstract_declarator_opt','plyparser.py',43),
  ('abstract_declarator_opt -> abstract_declarator','abstract_declarator_opt',1,'p_abstract_declarator_opt','plyparser.py',44),
  ('assignment_expression_opt -> empty','assignment_expression_opt',1,'p_assignment_expression_opt','plyparser.py',43),
  ('assignment_expression_opt -> assignment_expression','assignment_expression_opt',1,'p_assignment_expression_opt','plyparser.py',44),
  ('block_item_list_opt -> empty','block_item_list_opt',1,'p_block_item_list_opt','plyparser.py',43),
  ('block_item_list_opt -> block_item_list','block_item_list_opt',1,'p_block_item_list_opt','plyparser.py',44),
  ('declaration_list_opt -> empty','declaration_list_opt',1,'p_declaration_list_opt','plyparser.py',43),
  ('declaration_list_opt -> declaration_list','declaration_list_opt',1,'p_declaration_list_opt','plyparser.py',44),
  ('declaration_specifiers_no_type_opt -> empty','declaration_specifiers_no_type_opt',1,'p_declaration_specifiers_no_type_opt','plyparser.py',43),
  ('declaration_specifiers_no_type_opt -> declaration_specifiers_no_type','declaration_specifiers_no_type_opt',1,'p_declaration_specifiers_no_type_opt','plyparser.py',44),
  ('designation_opt -> empty','designation_opt',1,'p_designation_opt','plyparser.py',43),
  ('designation_opt -> designation','designation_opt',1,'p_designation_opt','plyparser.py',44),
  ('expression_opt -> empty','expression_opt',1,'p_expression_opt','plyparser.py',43),
  ('expression_opt -> expression','expression_opt',1,'p_expression_opt','plyparser.py',44),
  ('id_init_declarator_list_opt -> empty','id_init_declarator_list_opt',1,'p_id_init_declarator_list_opt','plyparser.py',43),
  ('id_init_declarator_list_opt -> id_init_declarator_list','id_init_declarator_list_opt',1,'p_id_init_declarator_list_opt','plyparser.py',44),
  ('identifier_list_opt -> empty','identifier_list_opt',1,'p_identifier_list_opt','plyparser.py',43),
  ('identifier_list_opt -> identifier_list','identifier_list_opt',1,'p_identifier_list_opt','plyparser.py',44),
  ('init_declarator_list_opt -> empty','init_declarator_list_opt',1,'p_init_declarator_list_opt','plyparser.py',43),
  ('init_declarator_list_opt -> init_declarator_list','init_declarator_list_opt',1,'p_init_declarator_list_opt','plyparser.py',44),
  ('initializer_list_opt -> empty','initializer_list_opt',1,'p_initializer_list_opt','plyparser.py',43),
  ('initializer_list_opt -> initializer_list','initializer_list_opt',1,'p_initializer_list_opt','plyparser.py',44),
  ('parameter_type_list_opt -> empty','parameter_type_list_opt',1,'p_parameter_type_list_opt','plyparser.py',43),
  ('parameter_type_list_opt -> parameter_type_list','parameter_type_list_opt',1,'p_parameter_type_list_opt','plyparser.py',44),
  ('struct_declarator_list_opt -> empty','struct_declarator_list_opt',1,'p_struct_declarator_list_opt','plyparser.py',43),
  ('struct_declarator_list_opt -> struct_declarator_list','struct_declarator_list_opt',1,'p_struct_declarator_list_opt','plyparser.py',44),
  ('type_qualifier_list_opt -> empty','type_qualifier_list_opt',1,'p_type_qualifier_list_opt','plyparser.py',43),
  ('type_qualifier_list_opt -> type_qualifier_list','type_qualifier_list_opt',1,'p_type_qualifier_list_opt','plyparser.py',44),
  ('direct_id_declarator -> ID','direct_id_declarator',1,'p_direct_id_declarator_1','plyparser.py',126),
  ('direct_id_declarator -> LPAREN id_declarator RPAREN','direct_id_declarator',3,'p_direct_id_declarator_2','plyparser.py',126),
  ('direct_id_declarator -> direct_id_declarator LBRACKET type_qualifier_list_opt assignment_expression_opt RBRACKET','direct_id_declarator',5,'p_direct_id_declarator_3','plyparser.py',126),
  ('direct_id_declarator -> direct_id_declarator LBRACKET STATIC type_qualifier_list_opt assignment_expression RBRACKET','direct_id_declarator',6,'p_direct_id_declarator_4','plyparser.py',126),
  ('direct_id_declarator -> direct_id_declarator LBRACKET type_qualifier_list STATIC assignment_expression RBRACKET','direct_id_declarator',6,'p_direct_id_declarator_4','plyparser.py',127),
  ('direct_id_declarator -> direct_id_declarator LBRACKET type_qualifier_list_opt TIMES RBRACKET','direct_id_declarator',5,'p_direct_id_declarator_5','plyparser.py',126),
  ('direct_id_declarator -> direct_id_declarator LPAREN parameter_type_list RPAREN','direct_id_declarator',4,'p_direct_id_declarator_6','plyparser.py',126),
  ('direct_id_declarator -> direct_id_declarator LPAREN identifier_list_opt RPAREN','direct_id_declarator',4,'p_direct_id_declarator_6','plyparser.py',127),
  ('direct_typeid_declarator -> TYPEID','direct_typeid_declarator',1,'p_direct_typeid_declarator_1','plyparser.py',126),
  ('direct_typeid_declarator -> LPAREN typeid_declarator RPAREN','direct_typeid_declarator',3,'p_direct_typeid_declarator_2','plyparser.py',126),
  ('direct_typeid_declarator -> direct_typeid_declarator LBRACKET type_qualifier_list_opt assignment_expression_opt RBRACKET','direct_typeid_declarator',5,'p_direct_typeid_declarator_3','plyparser.py',126),
  ('direct_typeid_declarator -> direct_typeid_declarator LBRACKET STATIC type_qualifier_list_opt assignment_expression RBRACKET','direct_typeid_declarator',6,'p_direct_typeid_declarator_4','plyparser.py',126),
  ('direct_typeid_declarator -> direct_typeid_declarator LBRACKET type_qualifier_list STATIC assignment_expression RBRACKET','direct_typeid_declarator',6,'p_direct_typeid_declarator_4','plyparser.py',127),
  ('direct_typeid_declarator -> direct_typeid_declarator LBRACKET type_qualifier_list_opt TIMES RBRACKET','direct_typeid_declarator',5,'p_direct_typeid_declarator_5','plyparser.py',126),
  ('direct_typeid_declarator -> direct_typeid_declarator LPAREN parameter_type_list RPAREN','direct_typeid_declarator',4,'p_direct_typeid_declarator_6','plyparser.py',126),
  ('direct_typeid_declarator -> direct_typeid_declarator LPAREN identifier_list_opt RPAREN','direct_typeid_declarator',4,'p_direct_typeid_declarator_6','plyparser.py',127),
  ('direct_typeid_noparen_declarator -> TYPEID','direct_typeid_noparen_declarator',1,'p_direct_typeid_noparen_declarator_1','plyparser.py',126),
  ('direct_typeid_noparen_declarator -> direct_typeid_noparen_declarator LBRACKET type_qualifier_list_opt assignment_expression_opt RBRACKET','direct_typeid_noparen_declarator',5,'p_direct_typeid_noparen_declarator_3','plyparser.py',126),
  ('direct_typeid_noparen_declarator -> direct_typeid_noparen_declarator LBRACKET STATIC type_qualifier_list_opt assignment_expression RBRACKET','direct_typeid_noparen_declarator',6,'p_direct_typeid_noparen_declarator_4','plyparser.py',126),
  ('direct_typeid_noparen_declarator -> direct_typeid_noparen_declarator LBRACKET type_qualifier_list STATIC assignment_expression RBRACKET','direct_typeid_noparen_declarator',6,'p_direct_typeid_noparen_declarator_4','plyparser.py',127),
  ('direct_typeid_noparen_declarator -> direct_typeid_noparen_declarator LBRACKET type_qualifier_list_opt TIMES RBRACKET','direct_typeid_noparen_declarator',5,'p_direct_typeid_noparen_declarator_5','plyparser.py',126),
  ('direct_typeid_noparen_declarator -> direct_typeid_noparen_declarator LPAREN parameter_type_list RPAREN','direct_typeid_noparen_declarator',4,'p_direct_typeid_noparen_declarator_6','plyparser.py',126),
  ('direct_typeid_noparen_declarator -> direct_typeid_noparen_declarator LPAREN identifier_list_opt RPAREN','direct_typeid_noparen_declarator',4,'p_direct_typeid_noparen_declarator_6','plyparser.py',127),
  ('id_declarator -> direct_id_declarator','id_declarator',1,'p_id_declarator_1','plyparser.py',126),
  ('id_declarator -> pointer direct_id_declarator','id_declarator',2,'p_id_declarator_2','plyparser.py',126),
  ('typeid_declarator -> direct_typeid_declarator','typeid_declarator',1,'p_typeid_declarator_1','plyparser.py',126),
  ('typeid_declarator -> pointer direct_typeid_declarator','typeid_declarator',2,'p_typeid_declarator_2','plyparser.py',126),
  ('typeid_noparen_declarator -> direct_typeid_noparen_declarator','typeid_noparen_declarator',1,'p_typeid_noparen_declarator_1','plyparser.py',126),
  ('typeid_noparen_declarator -> pointer direct_typeid_noparen_declarator','typeid_noparen_declarator',2,'p_typeid_noparen_declarator_2','plyparser.py',126),
  ('translation_unit_or_empty -> translation_unit','translation_unit_or_empty',1,'p_translation_unit_or_empty','c_parser.py',509),
  ('translation_unit_or_empty -> empty','translation_unit_or_empty',1,'p_translation_unit_or_empty','c_parser.py',510),
  ('translation_unit -> external_declaration','translation_unit',1,'p_translation_unit_1','c_parser.py',518),
  ('translation_unit -> translation_unit external_declaration','translation_unit',2,'p_translation_unit_2','c_parser.py',524),
  ('external_declaration -> function_definition','external_declaration',1,'p_external_declaration_1','c_parser.py',534),
  ('external_declaration -> declaration','external_declaration',1,'p_external_declaration_2','c_parser.py',539),
  ('external_declaration -> pp_directive','external_declaration',1,'p_external_declaration_3','c_parser.py',544),
  ('external_declaration -> pppragma_directive','external_declaration',1,'p_external_declaration_3','c_parser.py',545),
  ('external_declaration -> SEMI','external_declaration',1,'p_external_declaration_4','c_parser.py',550),
  ('external_declaration -> static_assert','external_declaration',1,'p_external_declaration_5','c_parser.py',555),
  ('static_assert -> _STATIC_ASSERT LPAREN constant_expression COMMA unified_string_literal RPAREN','static_assert',6,'p_static_assert_declaration','c_parser.py',560),
  ('static_assert -> _STATIC_ASSERT LPAREN constant_expression RPAREN','static_assert',4,'p_static_assert_declaration','c_parser.py',561),
  ('pp_directive -> PPHASH','pp_directive',1,'p_pp_directive','c_parser.py',569),
  ('pppragma_directive -> PPPRAGMA','pppragma_directive',1,'p_pppragma_directive','c_parser.py',580),
  ('pppragma_directive -> PPPRAGMA PPPRAGMASTR','pppragma_directive',2,'p_pppragma_directive','c_parser.py',581),
  ('pppragma_directive -> _PRAGMA LPAREN unified_string_literal RPAREN','pppragma_directive',4,'p_pppragma_directive','c_parser.py',582),
  ('pppragma_directive_list -> pppragma_directive','pppragma_directive_list',1,'p_pppragma_directive_list','c_parser.py',592),
  ('pppragma_directive_list -> pppragma_directive_list pppragma_directive','pppragma_directive_list',2,'p_pppragma_directive_list','c_parser.py',593),
  ('function_definition -> id_declarator declaration_list_opt compound_statement','function_definition',3,'p_function_definition_1','c_parser.py',600),
  ('function_definition -> declaration_specifiers id_declarator declaration_list_opt compound_statement','function_definition',4,'p_function_definition_2','c_parser.py',618),
  ('statement -> labeled_statement','statement',1,'p_statement','c_parser.py',633),
  ('statement -> expression_statement','statement',1,'p_statement','c_parser.py',634),
  ('statement -> compound_statement','statement',1,'p_statement','c_parser.py',635),
  ('statement -> selection_statement','statement',1,'p_statement','c_parser.py',636),
  ('statement -> iteration_statement','statement',1,'p_statement','c_parser.py',637),
  ('statement -> jump_statement','statement',1,'p_statement','c_parser.py',638),
  ('statement -> pppragma_directive','statement',1,'p_statement','c_parser.py',639),
  ('statement -> static_assert','statement',1,'p_statement','c_parser.py',640),
  ('pragmacomp_or_statement -> pppragma_directive_list statement','pragmacomp_or_statement',2,'p_pragmacomp_or_statement','c_parser.py',688),
  ('pragmacomp_or_statement -> statement','pragmacomp_or_statement',1,'p_pragmacomp_or_statement','c_parser.py',689),
  ('decl_body -> declaration_specifiers init_declarator_list_opt','decl_body',2,'p_decl_body','c_parser.py',708),
  ('decl_body -> declaration_specifiers_no_type id_init_declarator_list_opt','decl_body',2,'p_decl_body','c_parser.py',709),
  ('declaration -> decl_body SEMI','declaration',2,'p_declaration','c_parser.py',769),
  ('declaration_list -> declaration','declaration_list',1,'p_declaration_list','c_parser.py',778),
  ('declaration_list -> declaration_list declaration','declaration_list',2,'p_declaration_list','c_parser.py',779),
  ('declaration_specifiers_no_type -> type_qualifier declaration_specifiers_no_type_opt','declaration_specifiers_no_type',2,'p_declaration_specifiers_no_type_1','c_parser.py',789),
  ('declaration_specifiers_no_type -> storage_class_specifier declaration_specifiers_no_type_opt','declaration_specifiers_no_type',2,'p_declaration_specifiers_no_type_2','c_parser.py',794),
  ('declaration_specifiers_no_type -> function_specifier declaration_specifiers_no_type_opt','declaration_specifiers_no_type',2,'p_declaration_specifiers_no_type_3','c_parser.py',799),
  ('declaration_specifiers_no_type -> atomic_specifier declaration_specifiers_no_type_opt','declaration_specifiers_no_type',2,'p_declaration_specifiers_no_type_4','c_parser.py',806),
  ('declaration_specifiers_no_type -> alignment_specifier declaration_specifiers_no_type_opt','declaration_specifiers_no_type',2,'p_declaration_specifiers_no_type_5','c_parser.py',811),
  ('declaration_specifiers -> declaration_specifiers type_qualifier','declaration_specifiers',2,'p_declaration_specifiers_1','c_parser.py',816),
  ('declaration_specifiers -> declaration_specifiers storage_class_specifier','declaration_specifiers',2,'p_declaration_specifiers_2','c_parser.py',821),
  ('declaration_specifiers -> declaration_specifiers function_specifier','declaration_specifiers',2,'p_declaration_specifiers_3','c_parser.py',826),
  ('declaration_specifiers -> declaration_specifiers type_specifier_no_typeid','declaration_specifiers',2,'p_declaration_specifiers_4','c_parser.py',831),
  ('declaration_specifiers -> type_specifier','declaration_specifiers',1,'p_declaration_specifiers_5','c_parser.py',836),
  ('declaration_specifiers -> declaration_specifiers_no_type type_specifier','declaration_specifiers',2,'p_declaration_specifiers_6','c_parser.py',841),
  ('declaration_specifiers -> declaration_specifiers alignment_specifier','declaration_specifiers',2,'p_declaration_specifiers_7','c_parser.py',846),
  ('storage_class_specifier -> AUTO','storage_class_specifier',1,'p_storage_class_specifier','c_parser.py',851),
  ('storage_class_specifier -> REGISTER','storage_class_specifier',1,'p_storage_class_specifier','c_parser.py',852),
  ('storage_class_specifier -> STATIC','storage_class_specifier',1,'p_storage_class_specifier','c_parser.py',853),
  ('storage_class_specifier -> EXTERN','storage_class_specifier',1,'p_storage_class_specifier','c_parser.py',854),
  ('storage_class_specifier -> TYPEDEF','storage_class_specifier',1,'p_storage_class_specifier','c_parser.py',855),
  ('storage_class_specifier -> _THREAD_LOCAL','storage_class_specifier',1,'p_storage_class_specifier','c_parser.py',856),
  ('function_specifier -> INLINE','function_specifier',1,'p_function_specifier','c_parser.py',861),
  ('function_specifier -> _NORETURN','function_specifier',1,'p_function_specifier','c_parser.py',862),
  ('type_specifier_no_typeid -> VOID','type_specifier_no_typeid',1,'p_type_specifier_no_typeid','c_parser.py',867),
  ('type_specifier_no_typeid -> _BOOL','type_specifier_no_typeid',1,'p_type_specifier_no_typeid','c_parser.py',868),
  ('type_specifier_no_typeid -> CHAR','type_specifier_no_typeid',1,'p_type_specifier_no_typeid','c_parser.py',869),
  ('type_specifier_no_typeid -> SHORT','type_specifier_no_typeid',1,'p_type_specifier_no_typeid','c_parser.py',870),
  ('type_specifier_no_typeid -> INT','type_specifier_no_typeid',1,'p_type_specifier_no_typeid','c_parser.py',871),
  ('type_specifier_no_typeid -> LONG','type_specifier_no_typeid',1,'p_type_specifier_no_typeid','c_parser.py',872),
  ('type_specifier_no_typeid -> FLOAT','type_specifier_no_typeid',1,'p_type_specifier_no_typeid','c_parser.py',873),
  ('type_specifier_no_typeid -> DOUBLE','type_specifier_no_typeid',1,'p_type_specifier_no_typeid','c_parser.py',874),
  ('type_specifier_no_typeid -> _COMPLEX','type_specifier_no_typeid',1,'p_type_specifier_no_typeid','c_parser.py',875),
  ('type_specifier_no_typeid -> SIGNED','type_specifier_no_typeid',1,'p_type_specifier_no_typeid','c_parser.py',876),
  ('type_specifier_no_typeid -> UNSIGNED','type_specifier_no_typeid',1,'p_type_specifier_no_typeid','c_parser.py',877),
  ('type_specifier_no_typeid -> __INT128','type_specifier_no_typeid',1,'p_type_specifier_no_typeid','c_parser.py',878),
  ('type_specifier -> typedef_name','type_specifier',1,'p_type_specifier','c_parser.py',883),
  ('type_specifier -> enum_specifier','type_specifier',1,'p_type_specifier','c_parser.py',884),
  ('type_specifier -> struct_or_union_specifier','type_specifier',1,'p_type_specifier','c_parser.py',885),
  ('type_specifier -> type_specifier_no_typeid','type_specifier',1,'p_type_specifier','c_parser.py',886),
  ('type_specifier -> atomic_specifier','type_specifier',1,'p_type_specifier','c_parser.py',887),
  ('atomic_specifier -> _ATOMIC LPAREN type_name RPAREN','atomic_specifier',4,'p_atomic_specifier','c_parser.py',893),
  ('type_qualifier -> CONST','type_qualifier',1,'p_type_qualifier','c_parser.py',900),
  ('type_qualifier -> RESTRICT','type_qualifier',1,'p_type_qualifier','c_parser.py',901),
  ('type_qualifier -> VOLATILE','type_qualifier',1,'p_type_qualifier','c_parser.py',902),
  ('type_qualifier -> _ATOMIC','type_qualifier',1,'p_type_qualifier','c_parser.py',903),
  ('init_declarator_list -> init_declarator','init_declarator_list',1,'p_init_declarator_list','c_parser.py',908),
  ('init_declarator_list -> init_declarator_list COMMA init_declarator','init_declarator_list',3,'p_init_declarator_list','c_parser.py',909),
  ('init_declarator -> declarator','init_declarator',1,'p_init_declarator','c_parser.py',917),
  ('init_declarator -> declarator EQUALS initializer','init_declarator',3,'p_init_declarator','c_parser.py',918),
  ('id_init_declarator_list -> id_init_declarator','id_init_declarator_list',1,'p_id_init_declarator_list','c_parser.py',923),
  ('id_init_declarator_list -> id_init_declarator_list COMMA init_declarator','id_init_declarator_list',3,'p_id_init_declarator_list','c_parser.py',924),
  ('id_init_declarator -> id_declarator','id_init_declarator',1,'p_id_init_declarator','c_parser.py',929),
  ('id_init_declarator -> id_declarator EQUALS initializer','id_init_declarator',3,'p_id_init_declarator','c_parser.py',930),
  ('specifier_qualifier_list -> specifier_qualifier_list type_specifier_no_typeid','specifier_qualifier_list',2,'p_specifier_qualifier_list_1','c_parser.py',937),
  ('specifier_qualifier_list -> specifier_qualifier_list type_qualifier','specifier_qualifier_list',2,'p_specifier_qualifier_list_2','c_parser.py',942),
  ('specifier_qualifier_list -> type_specifier','specifier_qualifier_list',1,'p_specifier_qualifier_list_3','c_parser.py',947),
  ('specifier_qualifier_list -> type_qualifier_list type_specifier','specifier_qualifier_list',2,'p_specifier_qualifier_list_4','c_parser.py',952),
  ('specifier_qualifier_list -> alignment_specifier','specifier_qualifier_list',1,'p_specifier_qualifier_list_5','c_parser.py',957),
  ('specifier_qualifier_list -> specifier_qualifier_list alignment_specifier','specifier_qualifier_list',2,'p_specifier_qualifier_list_6','c_parser.py',962),
  ('struct_or_union_specifier -> struct_or_union ID','struct_or_union_specifier',2,'p_struct_or_union_specifier_1','c_parser.py',970),
  ('struct_or_union_specifier -> struct_or_union TYPEID','struct_or_union_specifier',2,'p_struct_or_union_specifier_1','c_parser.py',971),
  ('struct_or_union_specifier -> struct_or_union brace_open struct_declaration_list brace_close','struct_or_union_specifier',4,'p_struct_or_union_specifier_2','c_parser.py',981),
  ('struct_or_union_specifier -> struct_or_union brace_open brace_close','struct_or_union_specifier',3,'p_struct_or_union_specifier_2','c_parser.py',982),
  ('struct_or_union_specifier -> struct_or_union ID brace_open struct_declaration_list brace_close','struct_or_union_specifier',5,'p_struct_or_union_specifier_3','c_parser.py',999),
  ('struct_or_union_specifier -> struct_or_union ID brace_open brace_close','struct_or_union_specifier',4,'p_struct_or_union_specifier_3','c_parser.py',1000),
  ('struct_or_union_specifier -> struct_or_union TYPEID brace_open struct_declaration_list brace_close','struct_or_union_specifier',5,'p_struct_or_union_specifier_3','c_parser.py',1001),
  ('struct_or_union_specifier -> struct_or_union TYPEID brace_open brace_close','struct_or_union_specifier',4,'p_struct_or_union_specifier_3','c_parser.py',1002),
  ('struct_or_union -> STRUCT','struct_or_union',1,'p_struct_or_union','c_parser.py',1018),
  ('struct_or_union -> UNION','struct_or_union',1,'p_struct_or_union','c_parser.py',1019),
  ('struct_declaration_list -> struct_declaration','struct_declaration_list',1,'p_struct_declaration_list','c_parser.py',1026),
  ('struct_declaration_list -> struct_declaration_list struct_declaration','struct_declaration_list',2,'p_struct_declaration_list','c_parser.py',1027),
  ('struct_declaration -> specifier_qualifier_list struct_declarator_list_opt SEMI','struct_declaration',3,'p_struct_declaration_1','c_parser.py',1035),
  ('struct_declaration -> SEMI','struct_declaration',1,'p_struct_declaration_2','c_parser.py',1073),
  ('struct_declaration -> pppragma_directive','struct_declaration',1,'p_struct_declaration_3','c_parser.py',1078),
  ('struct_declarator_list -> struct_declarator','struct_declarator_list',1,'p_struct_declarator_list','c_parser.py',1083),
  ('struct_declarator_list -> struct_declarator_list COMMA struct_declarator','struct_declarator_list',3,'p_struct_declarator_list','c_parser.py',1084),
  ('struct_declarator -> declarator','struct_declarator',1,'p_struct_declarator_1','c_parser.py',1092),
  ('struct_declarator -> declarator COLON constant_expression','struct_declarator',3,'p_struct_declarator_2','c_parser.py',1097),
  ('struct_declarator -> COLON constant_expression','struct_declarator',2,'p_struct_declarator_2','c_parser.py',1098),
  ('enum_specifier -> ENUM ID','enum_specifier',2,'p_enum_specifier_1','c_parser.py',1106),
  ('enum_specifier -> ENUM TYPEID','enum_specifier',2,'p_enum_specifier_1','c_parser.py',1107),
  ('enum_specifier -> ENUM brace_open enumerator_list brace_close','enum_specifier',4,'p_enum_specifier_2','c_parser.py',1112),
  ('enum_specifier -> ENUM ID brace_open enumerator_list brace_close','enum_specifier',5,'p_enum_specifier_3','c_parser.py',1117),
  ('enum_specifier -> ENUM TYPEID brace_open enumerator_list brace_close','enum_specifier',5,'p_enum_specifier_3','c_parser.py',1118),
  ('enumerator_list -> enumerator','enumerator_list',1,'p_enumerator_list','c_parser.py',1123),
  ('enumerator_list -> enumerator_list COMMA','enumerator_list',2,'p_enumerator_list','c_parser.py',1124),
  ('enumerator_list -> enumerator_list COMMA enumerator','enumerator_list',3,'p_enumerator_list','c_parser.py',1125),
  ('alignment_specifier -> _ALIGNAS LPAREN type_name RPAREN','alignment_specifier',4,'p_alignment_specifier','c_parser.py',1136),
  ('alignment_specifier -> _ALIGNAS LPAREN constant_expression RPAREN','alignment_specifier',4,'p_alignment_specifier','c_parser.py',1137),
  ('enumerator -> ID','enumerator',1,'p_enumerator','c_parser.py',1142),
  ('enumerator -> ID EQUALS constant_expression','enumerator',3,'p_enumerator','c_parser.py',1143),
  ('declarator -> id_declarator','declarator',1,'p_declarator','c_parser.py',1158),
  ('declarator -> typeid_declarator','declarator',1,'p_declarator','c_parser.py',1159),
  ('pointer -> TIMES type_qualifier_list_opt','pointer',2,'p_pointer','c_parser.py',1271),
  ('pointer -> TIMES type_qualifier_list_opt pointer','pointer',3,'p_pointer','c_parser.py',1272),
  ('type_qualifier_list -> type_qualifier','type_qualifier_list',1,'p_type_qualifier_list','c_parser.py',1301),
  ('type_qualifier_list -> type_qualifier_list type_qualifier','type_qualifier_list',2,'p_type_qualifier_list','c_parser.py',1302),
  ('parameter_type_list -> parameter_list','parameter_type_list',1,'p_parameter_type_list','c_parser.py',1307),
  ('parameter_type_list -> parameter_list COMMA ELLIPSIS','parameter_type_list',3,'p_parameter_type_list','c_parser.py',1308),
  ('parameter_list -> parameter_declaration','parameter_list',1,'p_parameter_list','c_parser.py',1316),
  ('parameter_list -> parameter_list COMMA parameter_declaration','parameter_list',3,'p_parameter_list','c_parser.py',1317),
  ('parameter_declaration -> declaration_specifiers id_declarator','parameter_declaration',2,'p_parameter_declaration_1','c_parser.py',1336),
  ('parameter_declaration -> declaration_specifiers typeid_noparen_declarator','parameter_declaration',2,'p_parameter_declaration_1','c_parser.py',1337),
  ('parameter_declaration -> declaration_specifiers abstract_declarator_opt','parameter_declaration',2,'p_parameter_declaration_2','c_parser.py',1348),
  ('identifier_list -> identifier','identifier_list',1,'p_identifier_list','c_parser.py',1380),
  ('identifier_list -> identifier_list COMMA identifier','identifier_list',3,'p_identifier_list','c_parser.py',1381),
  ('initializer -> assignment_expression','initializer',1,'p_initializer_1','c_parser.py',1390),
  ('initializer -> brace_open initializer_list_opt brace_close','initializer',3,'p_initializer_2','c_parser.py',1395),
  ('initializer -> brace_open initializer_list COMMA brace_close','initializer',4,'p_initializer_2','c_parser.py',1396),
  ('initializer_list -> designation_opt initializer','initializer_list',2,'p_initializer_list','c_parser.py',1404),
  ('initializer_list -> initializer_list COMMA designation_opt initializer','initializer_list',4,'p_initializer_list','c_parser.py',1405),
  ('designation -> designator_list EQUALS','designation',2,'p_designation','c_parser.py',1416),
  ('designator_list -> designator','designator_list',1,'p_designator_list','c_parser.py',1424),
  ('designator_list -> designator_list designator','designator_list',2,'p_designator_list','c_parser.py',1425),
  ('designator -> LBRACKET constant_expression RBRACKET','designator',3,'p_designator','c_parser.py',1430),
  ('designator -> PERIOD identifier','designator',2,'p_designator','c_parser.py',1431),
  ('type_name -> specifier_qualifier_list abstract_declarator_opt','type_name',2,'p_type_name','c_parser.py',1436),
  ('abstract_declarator -> pointer','abstract_declarator',1,'p_abstract_declarator_1','c_parser.py',1448),
  ('abstract_declarator -> pointer direct_abstract_declarator','abstract_declarator',2,'p_abstract_declarator_2','c_parser.py',1456),
  ('abstract_declarator -> direct_abstract_declarator','abstract_declarator',1,'p_abstract_declarator_3','c_parser.py',1461),
  ('direct_abstract_declarator -> LPAREN abstract_declarator RPAREN','direct_abstract_declarator',3,'p_direct_abstract_declarator_1','c_parser.py',1471),
  ('direct_abstract_declarator -> direct_abstract_declarator LBRACKET assignment_expression_opt RBRACKET','direct_abstract_declarator',4,'p_direct_abstract_declarator_2','c_parser.py',1475),
  ('direct_abstract_declarator -> LBRACKET type_qualifier_list_opt assignment_expression_opt RBRACKET','direct_abstract_declarator',4,'p_direct_abstract_declarator_3','c_parser.py',1486),
  ('direct_abstract_declarator -> direct_abstract_declarator LBRACKET TIMES RBRACKET','direct_abstract_declarator',4,'p_direct_abstract_declarator_4','c_parser.py',1496),
  ('direct_abstract_declarator -> LBRACKET TIMES RBRACKET','direct_abstract_declarator',3,'p_direct_abstract_declarator_5','c_parser.py',1507),
  ('direct_abstract_declarator -> direct_abstract_declarator LPAREN parameter_type_list_opt RPAREN','direct_abstract_declarator',4,'p_direct_abstract_declarator_6','c_parser.py',1516),
  ('direct_abstract_declarator -> LPAREN parameter_type_list_opt RPAREN','direct_abstract_declarator',3,'p_direct_abstract_declarator_7','c_parser.py',1526),
  ('block_item -> declaration','block_item',1,'p_block_item','c_parser.py',1537),
  ('block_item -> statement','block_item',1,'p_block_item','c_parser.py',1538),
  ('block_item_list -> block_item','block_item_list',1,'p_block_item_list','c_parser.py',1545),
  ('block_item_list -> block_item_list block_item','block_item_list',2,'p_block_item_list','c_parser.py',1546),
  ('compound_statement -> brace_open block_item_list_opt brace_close','compound_statement',3,'p_compound_statement_1','c_parser.py',1552),
  ('labeled_statement -> ID COLON pragmacomp_or_statement','labeled_statement',3,'p_labeled_statement_1','c_parser.py',1558),
  ('labeled_statement -> CASE constant_expression COLON pragmacomp_or_statement','labeled_statement',4,'p_labeled_statement_2','c_parser.py',1562),
  ('labeled_statement -> DEFAULT COLON pragmacomp_or_statement','labeled_statement',3,'p_labeled_statement_3','c_parser.py',1566),
  ('selection_statement -> IF LPAREN expression RPAREN pragmacomp_or_statement','selection_statement',5,'p_selection_statement_1','c_parser.py',1570),
  ('selection_statement -> IF LPAREN expression RPAREN statement ELSE pragmacomp_or_statement','selection_statement',7,'p_selection_statement_2','c_parser.py',1574),
  ('selection_statement -> SWITCH LPAREN expression RPAREN pragmacomp_or_statement','selection_statement',5,'p_selection_statement_3','c_parser.py',1578),
  ('iteration_statement -> WHILE LPAREN expression RPAREN pragmacomp_or_statement','iteration_statement',5,'p_iteration_statement_1','c_parser.py',1583),
  ('iteration_statement -> DO pragmacomp_or_statement WHILE LPAREN expression RPAREN SEMI','iteration_statement',7,'p_iteration_statement_2','c_parser.py',1587),
  ('iteration_statement -> FOR LPAREN expression_opt SEMI expression_opt SEMI expression_opt RPAREN pragmacomp_or_statement','iteration_statement',9,'p_iteration_statement_3','c_parser.py',1591),
  ('iteration_statement -> FOR LPAREN declaration expression_opt SEMI expression_opt RPAREN pragmacomp_or_statement','iteration_statement',8,'p_iteration_statement_4','c_parser.py',1595),
  ('jump_statement -> GOTO ID SEMI','jump_statement',3,'p_jump_statement_1','c_parser.py',1600),
  ('jump_statement -> BREAK SEMI','jump_statement',2,'p_jump_statement_2','c_parser.py',1604),
  ('jump_statement -> CONTINUE SEMI','jump_statement',2,'p_jump_statement_3','c_parser.py',1608),
  ('jump_statement -> RETURN expression SEMI','jump_statement',3,'p_jump_statement_4','c_parser.py',1612),
  ('jump_statement -> RETURN SEMI','jump_statement',2,'p_jump_statement_4','c_parser.py',1613),
  ('expression_statement -> expression_opt SEMI','expression_statement',2,'p_expression_statement','c_parser.py',1618),
  ('expression -> assignment_expression','expression',1,'p_expression','c_parser.py',1625),
  ('expression -> expression COMMA assignment_expression','expression',3,'p_expression','c_parser.py',1626),
  ('assignment_expression -> LPAREN compound_statement RPAREN','assignment_expression',3,'p_parenthesized_compound_expression','c_parser.py',1638),
  ('typedef_name -> TYPEID','typedef_name',1,'p_typedef_name','c_parser.py',1642),
  ('assignment_expression -> conditional_expression','assignment_expression',1,'p_assignment_expression','c_parser.py',1646),
  ('assignment_expression -> unary_expression assignment_operator assignment_expression','assignment_expression',3,'p_assignment_expression','c_parser.py',1647),
  ('assignment_operator -> EQUALS','assignment_operator',1,'p_assignment_operator','c_parser.py',1660),
  ('assignment_operator -> XOREQUAL','assignment_operator',1,'p_assignment_operator','c_parser.py',1661),
  ('assignment_operator -> TIMESEQUAL','assignment_operator',1,'p_assignment_operator','c_parser.py',1662),
  ('assignment_operator -> DIVEQUAL','assignment_operator',1,'p_assignment_operator','c_parser.py',1663),
  ('assignment_operator -> MODEQUAL','assignment_operator',1,'p_assignment_operator','c_parser.py',1664),
  ('assignment_operator -> PLUSEQUAL','assignment_operator',1,'p_assignment_operator','c_parser.py',1665),
  ('assignment_operator -> MINUSEQUAL','assignment_operator',1,'p_assignment_operator','c_parser.py',1666),
  ('assignment_operator -> LSHIFTEQUAL','assignment_operator',1,'p_assignment_operator','c_parser.py',1667),
  ('assignment_operator -> RSHIFTEQUAL','assignment_operator',1,'p_assignment_operator','c_parser.py',1668),
  ('assignment_operator -> ANDEQUAL','assignment_operator',1,'p_assignment_operator','c_parser.py',1669),
  ('assignment_operator -> OREQUAL','assignment_operator',1,'p_assignment_operator','c_parser.py',1670),
  ('constant_expression -> conditional_expression','constant_expression',1,'p_constant_expression','c_parser.py',1675),
  ('conditional_expression -> binary_expression','conditional_expression',1,'p_conditional_expression','c_parser.py',1679),
  ('conditional_expression -> binary_expression CONDOP expression COLON conditional_expression','conditional_expression',5,'p_conditional_expression','c_parser.py',1680),
  ('binary_expression -> cast_expression','binary_expression',1,'p_binary_expression','c_parser.py',1688),
  ('binary_expression -> binary_expression TIMES binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1689),
  ('binary_expression -> binary_expression DIVIDE binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1690),
  ('binary_expression -> binary_expression MOD binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1691),
  ('binary_expression -> binary_expression PLUS binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1692),
  ('binary_expression -> binary_expression MINUS binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1693),
  ('binary_expression -> binary_expression RSHIFT binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1694),
  ('binary_expression -> binary_expression LSHIFT binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1695),
  ('binary_expression -> binary_expression LT binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1696),
  ('binary_expression -> binary_expression LE binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1697),
  ('binary_expression -> binary_expression GE binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1698),
  ('binary_expression -> binary_expression GT binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1699),
  ('binary_expression -> binary_expression EQ binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1700),
  ('binary_expression -> binary_expression NE binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1701),
  ('binary_expression -> binary_expression AND binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1702),
  ('binary_expression -> binary_expression OR binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1703),
  ('binary_expression -> binary_expression XOR binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1704),
  ('binary_expression -> binary_expression LAND binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1705),
  ('binary_expression -> binary_expression LOR binary_expression','binary_expression',3,'p_binary_expression','c_parser.py',1706),
  ('cast_expression -> unary_expression','cast_expression',1,'p_cast_expression_1','c_parser.py',1714),
  ('cast_expression -> LPAREN type_name RPAREN cast_expression','cast_expression',4,'p_cast_expression_2','c_parser.py',1718),
  ('unary_expression -> postfix_expression','unary_expression',1,'p_unary_expression_1','c_parser.py',1722),
  ('unary_expression -> PLUSPLUS unary_expression','unary_expression',2,'p_unary_expression_2','c_parser.py',1726),
  ('unary_expression -> MINUSMINUS unary_expression','unary_expression',2,'p_unary_expression_2','c_parser.py',1727),
  ('unary_expression -> unary_operator cast_expression','unary_expression',2,'p_unary_expression_2','c_parser.py',1728),
  ('unary_expression -> SIZEOF unary_expression','unary_expression',2,'p_unary_expression_3','c_parser.py',1733),
  ('unary_expression -> SIZEOF LPAREN type_name RPAREN','unary_expression',4,'p_unary_expression_3','c_parser.py',1734),
  ('unary_expression -> _ALIGNOF LPAREN type_name RPAREN','unary_expression',4,'p_unary_expression_3','c_parser.py',1735),
  ('unary_operator -> AND','unary_operator',1,'p_unary_operator','c_parser.py',1743),
  ('unary_operator -> TIMES','unary_operator',1,'p_unary_operator','c_parser.py',1744),
  ('unary_operator -> PLUS','unary_operator',1,'p_unary_operator','c_parser.py',1745),
  ('unary_operator -> MINUS','unary_operator',1,'p_unary_operator','c_parser.py',1746),
  ('unary_operator -> NOT','unary_operator',1,'p_unary_operator','c_parser.py',1747),
  ('unary_operator -> LNOT','unary_operator',1,'p_unary_operator','c_parser.py',1748),
  ('postfix_expression -> primary_expression','postfix_expression',1,'p_postfix_expression_1','c_parser.py',1753),
  ('postfix_expression -> postfix_expression LBRACKET expression RBRACKET','postfix_expression',4,'p_postfix_expression_2','c_parser.py',1757),
  ('postfix_expression -> postfix_expression LPAREN argument_expression_list RPAREN','postfix_expression',4,'p_postfix_expression_3','c_parser.py',1761),
  ('postfix_expression -> postfix_expression LPAREN RPAREN','postfix_expression',3,'p_postfix_expression_3','c_parser.py',1762),
  ('postfix_expression -> postfix_expression PERIOD ID','postfix_expression',3,'p_postfix_expression_4','c_parser.py',1767),
  ('postfix_expression -> postfix_expression PERIOD TYPEID','postfix_expression',3,'p_postfix_expression_4','c_parser.py',1768),
  ('postfix_expression -> postfix_expression ARROW ID','postfix_expression',3,'p_postfix_expression_4','c_parser.py',1769),
  ('postfix_expression -> postfix_expression ARROW TYPEID','postfix_expression',3,'p_postfix_expression_4','c_parser.py',1770),
  ('postfix_expression -> postfix_expression PLUSPLUS','postfix_expression',2,'p_postfix_expression_5','c_parser.py',1776),
  ('postfix_expression -> postfix_expression MINUSMINUS','postfix_expression',2,'p_postfix_expression_5','c_parser.py',1777),
  ('postfix_expression -> LPAREN type_name RPAREN brace_open initializer_list brace_close','postfix_expression',6,'p_postfix_expression_6','c_parser.py',1782),
  ('postfix_expression -> LPAREN type_name RPAREN brace_open initializer_list COMMA brace_close','postfix_expression',7,'p_postfix_expression_6','c_parser.py',1783),
  ('primary_expression -> identifier','primary_expression',1,'p_primary_expression_1','c_parser.py',1788),
  ('primary_expression -> constant','primary_expression',1,'p_primary_expression_2','c_parser.py',1792),
  ('primary_expression -> unified_string_literal','primary_expression',1,'p_primary_expression_3','c_parser.py',1796),
  ('primary_expression -> unified_wstring_literal','primary_expression',1,'p_primary_expression_3','c_parser.py',1797),
  ('primary_expression -> LPAREN expression RPAREN','primary_expression',3,'p_primary_expression_4','c_parser.py',1802),
  ('primary_expression -> OFFSETOF LPAREN type_name COMMA offsetof_member_designator RPAREN','primary_expression',6,'p_primary_expression_5','c_parser.py',1806),
  ('offsetof_member_designator -> identifier','offsetof_member_designator',1,'p_offsetof_member_designator','c_parser.py',1814),
  ('offsetof_member_designator -> offsetof_member_designator PERIOD identifier','offsetof_member_designator',3,'p_offsetof_member_designator','c_parser.py',1815),
  ('offsetof_member_designator -> offsetof_member_designator LBRACKET expression RBRACKET','offsetof_member_designator',4,'p_offsetof_member_designator','c_parser.py',1816),
  ('argument_expression_list -> assignment_expression','argument_expression_list',1,'p_argument_expression_list','c_parser.py',1828),
  ('argument_expression_list -> argument_expression_list COMMA assignment_expression','argument_expression_list',3,'p_argument_expression_list','c_parser.py',1829),
  ('identifier -> ID','identifier',1,'p_identifier','c_parser.py',1838),
  ('constant -> INT_CONST_DEC','constant',1,'p_constant_1','c_parser.py',1842),
  ('constant -> INT_CONST_OCT','constant',1,'p_constant_1','c_parser.py',1843),
  ('constant -> INT_CONST_HEX','constant',1,'p_constant_1','c_parser.py',1844),
  ('constant -> INT_CONST_BIN','constant',1,'p_constant_1','c_parser.py',1845),
  ('constant -> INT_CONST_CHAR','constant',1,'p_constant_1','c_parser.py',1846),
  ('constant -> FLOAT_CONST','constant',1,'p_constant_2','c_parser.py',1865),
  ('constant -> HEX_FLOAT_CONST','constant',1,'p_constant_2','c_parser.py',1866),
  ('constant -> CHAR_CONST','constant',1,'p_constant_3','c_parser.py',1882),
  ('constant -> WCHAR_CONST','constant',1,'p_constant_3','c_parser.py',1883),
  ('constant -> U8CHAR_CONST','constant',1,'p_constant_3','c_parser.py',1884),
  ('constant -> U16CHAR_CONST','constant',1,'p_constant_3','c_parser.py',1885),
  ('constant -> U32CHAR_CONST','constant',1,'p_constant_3','c_parser.py',1886),
  ('unified_string_literal -> STRING_LITERAL','unified_string_literal',1,'p_unified_string_literal','c_parser.py',1897),
  ('unified_string_literal -> unified_string_literal STRING_LITERAL','unified_string_literal',2,'p_unified_string_literal','c_parser.py',1898),
  ('unified_wstring_literal -> WSTRING_LITERAL','unified_wstring_literal',1,'p_unified_wstring_literal','c_parser.py',1908),
  ('unified_wstring_literal -> U8STRING_LITERAL','unified_wstring_literal',1,'p_unified_wstring_literal','c_parser.py',1909),
  ('unified_wstring_literal -> U16STRING_LITERAL','unified_wstring_literal',1,'p_unified_wstring_literal','c_parser.py',1910),
  ('unified_wstring_literal -> U32STRING_LITERAL','unified_wstring_literal',1,'p_unified_wstring_literal','c_parser.py',1911),
  ('unified_wstring_literal -> unified_wstring_literal WSTRING_LITERAL','unified_wstring_literal',2,'p_unified_wstring_literal','c_parser.py',1912),
  ('unified_wstring_literal -> unified_wstring_literal U8STRING_LITERAL','unified_wstring_literal',2,'p_unified_wstring_literal','c_parser.py',1913),
  ('unified_wstring_literal -> unified_wstring_literal U16STRING_LITERAL','unified_wstring_literal',2,'p_unified_wstring_literal','c_parser.py',1914),
  ('unified_wstring_literal -> unified_wstring_literal U32STRING_LITERAL','unified_wstring_literal',2,'p_unified_wstring_literal','c_parser.py',1915),
  ('brace_open -> LBRACE','brace_open',1,'p_brace_open','c_parser.py',1925),
  ('brace_close -> RBRACE','brace_close',1,'p_brace_close','c_parser.py',1931),
  ('empty -> <empty>','empty',0,'p_empty','c_parser.py',1937),
]

# === NexusCore/openenv\Lib\site-packages\google\oauth2\reauth.py ===
# Copyright 2021 Google LLC
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

"""A module that provides functions for handling rapt authentication.

Reauth is a process of obtaining additional authentication (such as password,
security token, etc.) while refreshing OAuth 2.0 credentials for a user.

Credentials that use the Reauth flow must have the reauth scope,
``https://www.googleapis.com/auth/accounts.reauth``.

This module provides a high-level function for executing the Reauth process,
:func:`refresh_grant`, and lower-level helpers for doing the individual
steps of the reauth process.

Those steps are:

1. Obtaining a list of challenges from the reauth server.
2. Running through each challenge and sending the result back to the reauth
   server.
3. Refreshing the access token using the returned rapt token.
"""

import sys

from google.auth import exceptions
from google.auth import metrics
from google.oauth2 import _client
from google.oauth2 import challenges


_REAUTH_SCOPE = "https://www.googleapis.com/auth/accounts.reauth"
_REAUTH_API = "https://reauth.googleapis.com/v2/sessions"

_REAUTH_NEEDED_ERROR = "invalid_grant"
_REAUTH_NEEDED_ERROR_INVALID_RAPT = "invalid_rapt"
_REAUTH_NEEDED_ERROR_RAPT_REQUIRED = "rapt_required"

_AUTHENTICATED = "AUTHENTICATED"
_CHALLENGE_REQUIRED = "CHALLENGE_REQUIRED"
_CHALLENGE_PENDING = "CHALLENGE_PENDING"


# Override this global variable to set custom max number of rounds of reauth
# challenges should be run.
RUN_CHALLENGE_RETRY_LIMIT = 5


def is_interactive():
    """Check if we are in an interractive environment.

    Override this function with a different logic if you are using this library
    outside a CLI.

    If the rapt token needs refreshing, the user needs to answer the challenges.
    If the user is not in an interractive environment, the challenges can not
    be answered and we just wait for timeout for no reason.

    Returns:
        bool: True if is interactive environment, False otherwise.
    """

    return sys.stdin.isatty()


def _get_challenges(
    request, supported_challenge_types, access_token, requested_scopes=None
):
    """Does initial request to reauth API to get the challenges.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        supported_challenge_types (Sequence[str]): list of challenge names
            supported by the manager.
        access_token (str): Access token with reauth scopes.
        requested_scopes (Optional(Sequence[str])): Authorized scopes for the credentials.

    Returns:
        dict: The response from the reauth API.
    """
    body = {"supportedChallengeTypes": supported_challenge_types}
    if requested_scopes:
        body["oauthScopesForDomainPolicyLookup"] = requested_scopes
    metrics_header = {metrics.API_CLIENT_HEADER: metrics.reauth_start()}

    return _client._token_endpoint_request(
        request,
        _REAUTH_API + ":start",
        body,
        access_token=access_token,
        use_json=True,
        headers=metrics_header,
    )


def _send_challenge_result(
    request, session_id, challenge_id, client_input, access_token
):
    """Attempt to refresh access token by sending next challenge result.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        session_id (str): session id returned by the initial reauth call.
        challenge_id (str): challenge id returned by the initial reauth call.
        client_input: dict with a challenge-specific client input. For example:
            ``{'credential': password}`` for password challenge.
        access_token (str): Access token with reauth scopes.

    Returns:
        dict: The response from the reauth API.
    """
    body = {
        "sessionId": session_id,
        "challengeId": challenge_id,
        "action": "RESPOND",
        "proposalResponse": client_input,
    }
    metrics_header = {metrics.API_CLIENT_HEADER: metrics.reauth_continue()}

    return _client._token_endpoint_request(
        request,
        _REAUTH_API + "/{}:continue".format(session_id),
        body,
        access_token=access_token,
        use_json=True,
        headers=metrics_header,
    )


def _run_next_challenge(msg, request, access_token):
    """Get the next challenge from msg and run it.

    Args:
        msg (dict): Reauth API response body (either from the initial request to
            https://reauth.googleapis.com/v2/sessions:start or from sending the
            previous challenge response to
            https://reauth.googleapis.com/v2/sessions/id:continue)
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        access_token (str): reauth access token

    Returns:
        dict: The response from the reauth API.

    Raises:
        google.auth.exceptions.ReauthError: if reauth failed.
    """
    for challenge in msg["challenges"]:
        if challenge["status"] != "READY":
            # Skip non-activated challenges.
            continue
        c = challenges.AVAILABLE_CHALLENGES.get(challenge["challengeType"], None)
        if not c:
            raise exceptions.ReauthFailError(
                "Unsupported challenge type {0}. Supported types: {1}".format(
                    challenge["challengeType"],
                    ",".join(list(challenges.AVAILABLE_CHALLENGES.keys())),
                )
            )
        if not c.is_locally_eligible:
            raise exceptions.ReauthFailError(
                "Challenge {0} is not locally eligible".format(
                    challenge["challengeType"]
                )
            )
        client_input = c.obtain_challenge_input(challenge)
        if not client_input:
            return None
        return _send_challenge_result(
            request,
            msg["sessionId"],
            challenge["challengeId"],
            client_input,
            access_token,
        )
    return None


def _obtain_rapt(request, access_token, requested_scopes):
    """Given an http request method and reauth access token, get rapt token.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        access_token (str): reauth access token
        requested_scopes (Sequence[str]): scopes required by the client application

    Returns:
        str: The rapt token.

    Raises:
        google.auth.exceptions.ReauthError: if reauth failed
    """
    msg = _get_challenges(
        request,
        list(challenges.AVAILABLE_CHALLENGES.keys()),
        access_token,
        requested_scopes,
    )

    if msg["status"] == _AUTHENTICATED:
        return msg["encodedProofOfReauthToken"]

    for _ in range(0, RUN_CHALLENGE_RETRY_LIMIT):
        if not (
            msg["status"] == _CHALLENGE_REQUIRED or msg["status"] == _CHALLENGE_PENDING
        ):
            raise exceptions.ReauthFailError(
                "Reauthentication challenge failed due to API error: {}".format(
                    msg["status"]
                )
            )

        if not is_interactive():
            raise exceptions.ReauthFailError(
                "Reauthentication challenge could not be answered because you are not"
                " in an interactive session."
            )

        msg = _run_next_challenge(msg, request, access_token)

        if not msg:
            raise exceptions.ReauthFailError("Failed to obtain rapt token.")
        if msg["status"] == _AUTHENTICATED:
            return msg["encodedProofOfReauthToken"]

    # If we got here it means we didn't get authenticated.
    raise exceptions.ReauthFailError("Failed to obtain rapt token.")


def get_rapt_token(
    request, client_id, client_secret, refresh_token, token_uri, scopes=None
):
    """Given an http request method and refresh_token, get rapt token.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        client_id (str): client id to get access token for reauth scope.
        client_secret (str): client secret for the client_id
        refresh_token (str): refresh token to refresh access token
        token_uri (str): uri to refresh access token
        scopes (Optional(Sequence[str])): scopes required by the client application

    Returns:
        str: The rapt token.
    Raises:
        google.auth.exceptions.RefreshError: If reauth failed.
    """
    sys.stderr.write("Reauthentication required.\n")

    # Get access token for reauth.
    access_token, _, _, _ = _client.refresh_grant(
        request=request,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        token_uri=token_uri,
        scopes=[_REAUTH_SCOPE],
    )

    # Get rapt token from reauth API.
    rapt_token = _obtain_rapt(request, access_token, requested_scopes=scopes)
    sys.stderr.write("Reauthentication successful.\n")

    return rapt_token


def refresh_grant(
    request,
    token_uri,
    refresh_token,
    client_id,
    client_secret,
    scopes=None,
    rapt_token=None,
    enable_reauth_refresh=False,
):
    """Implements the reauthentication flow.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        refresh_token (str): The refresh token to use to get a new access
            token.
        client_id (str): The OAuth 2.0 application's client ID.
        client_secret (str): The Oauth 2.0 appliaction's client secret.
        scopes (Optional(Sequence[str])): Scopes to request. If present, all
            scopes must be authorized for the refresh token. Useful if refresh
            token has a wild card scope (e.g.
            'https://www.googleapis.com/auth/any-api').
        rapt_token (Optional(str)): The rapt token for reauth.
        enable_reauth_refresh (Optional[bool]): Whether reauth refresh flow
            should be used. The default value is False. This option is for
            gcloud only, other users should use the default value.

    Returns:
        Tuple[str, Optional[str], Optional[datetime], Mapping[str, str], str]: The
            access token, new refresh token, expiration, the additional data
            returned by the token endpoint, and the rapt token.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.
    """
    body = {
        "grant_type": _client._REFRESH_GRANT_TYPE,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    if scopes:
        body["scope"] = " ".join(scopes)
    if rapt_token:
        body["rapt"] = rapt_token
    metrics_header = {metrics.API_CLIENT_HEADER: metrics.token_request_user()}

    response_status_ok, response_data, retryable_error = _client._token_endpoint_request_no_throw(
        request, token_uri, body, headers=metrics_header
    )

    if not response_status_ok and isinstance(response_data, str):
        raise exceptions.RefreshError(response_data, retryable=False)

    if (
        not response_status_ok
        and response_data.get("error") == _REAUTH_NEEDED_ERROR
        and (
            response_data.get("error_subtype") == _REAUTH_NEEDED_ERROR_INVALID_RAPT
            or response_data.get("error_subtype") == _REAUTH_NEEDED_ERROR_RAPT_REQUIRED
        )
    ):
        if not enable_reauth_refresh:
            raise exceptions.RefreshError(
                "Reauthentication is needed. Please run `gcloud auth application-default login` to reauthenticate."
            )

        rapt_token = get_rapt_token(
            request, client_id, client_secret, refresh_token, token_uri, scopes=scopes
        )
        body["rapt"] = rapt_token
        (
            response_status_ok,
            response_data,
            retryable_error,
        ) = _client._token_endpoint_request_no_throw(
            request, token_uri, body, headers=metrics_header
        )

    if not response_status_ok:
        _client._handle_error_response(response_data, retryable_error)
    return _client._handle_refresh_grant_response(response_data, refresh_token) + (
        rapt_token,
    )

# === NexusCore/openenv\Lib\site-packages\matplotlib\texmanager.py ===
r"""
Support for embedded TeX expressions in Matplotlib.

Requirements:

* LaTeX.
* \*Agg backends: dvipng>=1.6.
* PS backend: PSfrag, dvips, and Ghostscript>=9.0.
* PDF and SVG backends: if LuaTeX is present, it will be used to speed up some
  post-processing steps, but note that it is not used to parse the TeX string
  itself (only LaTeX is supported).

To enable TeX rendering of all text in your Matplotlib figure, set
:rc:`text.usetex` to True.

TeX and dvipng/dvips processing results are cached
in ~/.matplotlib/tex.cache for reuse between sessions.

`TexManager.get_rgba` can also be used to directly obtain raster output as RGBA
NumPy arrays.
"""

import functools
import hashlib
import logging
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import numpy as np

import matplotlib as mpl
from matplotlib import cbook, dviread

_log = logging.getLogger(__name__)


def _usepackage_if_not_loaded(package, *, option=None):
    """
    Output LaTeX code that loads a package (possibly with an option) if it
    hasn't been loaded yet.

    LaTeX cannot load twice a package with different options, so this helper
    can be used to protect against users loading arbitrary packages/options in
    their custom preamble.
    """
    option = f"[{option}]" if option is not None else ""
    return (
        r"\makeatletter"
        r"\@ifpackageloaded{%(package)s}{}{\usepackage%(option)s{%(package)s}}"
        r"\makeatother"
    ) % {"package": package, "option": option}


class TexManager:
    """
    Convert strings to dvi files using TeX, caching the results to a directory.

    The cache directory is called ``tex.cache`` and is located in the directory
    returned by `.get_cachedir`.

    Repeated calls to this constructor always return the same instance.
    """

    _texcache = os.path.join(mpl.get_cachedir(), 'tex.cache')
    _grey_arrayd = {}

    _font_families = ('serif', 'sans-serif', 'cursive', 'monospace')
    _font_preambles = {
        'new century schoolbook': r'\renewcommand{\rmdefault}{pnc}',
        'bookman': r'\renewcommand{\rmdefault}{pbk}',
        'times': r'\usepackage{mathptmx}',
        'palatino': r'\usepackage{mathpazo}',
        'zapf chancery': r'\usepackage{chancery}',
        'cursive': r'\usepackage{chancery}',
        'charter': r'\usepackage{charter}',
        'serif': '',
        'sans-serif': '',
        'helvetica': r'\usepackage{helvet}',
        'avant garde': r'\usepackage{avant}',
        'courier': r'\usepackage{courier}',
        # Loading the type1ec package ensures that cm-super is installed, which
        # is necessary for Unicode computer modern.  (It also allows the use of
        # computer modern at arbitrary sizes, but that's just a side effect.)
        'monospace': r'\usepackage{type1ec}',
        'computer modern roman': r'\usepackage{type1ec}',
        'computer modern sans serif': r'\usepackage{type1ec}',
        'computer modern typewriter': r'\usepackage{type1ec}',
    }
    _font_types = {
        'new century schoolbook': 'serif',
        'bookman': 'serif',
        'times': 'serif',
        'palatino': 'serif',
        'zapf chancery': 'cursive',
        'charter': 'serif',
        'helvetica': 'sans-serif',
        'avant garde': 'sans-serif',
        'courier': 'monospace',
        'computer modern roman': 'serif',
        'computer modern sans serif': 'sans-serif',
        'computer modern typewriter': 'monospace',
    }

    @functools.lru_cache  # Always return the same instance.
    def __new__(cls):
        Path(cls._texcache).mkdir(parents=True, exist_ok=True)
        return object.__new__(cls)

    @classmethod
    def _get_font_family_and_reduced(cls):
        """Return the font family name and whether the font is reduced."""
        ff = mpl.rcParams['font.family']
        ff_val = ff[0].lower() if len(ff) == 1 else None
        if len(ff) == 1 and ff_val in cls._font_families:
            return ff_val, False
        elif len(ff) == 1 and ff_val in cls._font_preambles:
            return cls._font_types[ff_val], True
        else:
            _log.info('font.family must be one of (%s) when text.usetex is '
                      'True. serif will be used by default.',
                      ', '.join(cls._font_families))
            return 'serif', False

    @classmethod
    def _get_font_preamble_and_command(cls):
        requested_family, is_reduced_font = cls._get_font_family_and_reduced()

        preambles = {}
        for font_family in cls._font_families:
            if is_reduced_font and font_family == requested_family:
                preambles[font_family] = cls._font_preambles[
                    mpl.rcParams['font.family'][0].lower()]
            else:
                rcfonts = mpl.rcParams[f"font.{font_family}"]
                for i, font in enumerate(map(str.lower, rcfonts)):
                    if font in cls._font_preambles:
                        preambles[font_family] = cls._font_preambles[font]
                        _log.debug(
                            'family: %s, package: %s, font: %s, skipped: %s',
                            font_family, cls._font_preambles[font], rcfonts[i],
                            ', '.join(rcfonts[:i]),
                        )
                        break
                else:
                    _log.info('No LaTeX-compatible font found for the %s font'
                              'family in rcParams. Using default.',
                              font_family)
                    preambles[font_family] = cls._font_preambles[font_family]

        # The following packages and commands need to be included in the latex
        # file's preamble:
        cmd = {preambles[family]
               for family in ['serif', 'sans-serif', 'monospace']}
        if requested_family == 'cursive':
            cmd.add(preambles['cursive'])
        cmd.add(r'\usepackage{type1cm}')
        preamble = '\n'.join(sorted(cmd))
        fontcmd = (r'\sffamily' if requested_family == 'sans-serif' else
                   r'\ttfamily' if requested_family == 'monospace' else
                   r'\rmfamily')
        return preamble, fontcmd

    @classmethod
    def get_basefile(cls, tex, fontsize, dpi=None):
        """
        Return a filename based on a hash of the string, fontsize, and dpi.
        """
        src = cls._get_tex_source(tex, fontsize) + str(dpi)
        filehash = hashlib.sha256(
            src.encode('utf-8'),
            usedforsecurity=False
        ).hexdigest()
        filepath = Path(cls._texcache)

        num_letters, num_levels = 2, 2
        for i in range(0, num_letters*num_levels, num_letters):
            filepath = filepath / Path(filehash[i:i+2])

        filepath.mkdir(parents=True, exist_ok=True)
        return os.path.join(filepath, filehash)

    @classmethod
    def get_font_preamble(cls):
        """
        Return a string containing font configuration for the tex preamble.
        """
        font_preamble, command = cls._get_font_preamble_and_command()
        return font_preamble

    @classmethod
    def get_custom_preamble(cls):
        """Return a string containing user additions to the tex preamble."""
        return mpl.rcParams['text.latex.preamble']

    @classmethod
    def _get_tex_source(cls, tex, fontsize):
        """Return the complete TeX source for processing a TeX string."""
        font_preamble, fontcmd = cls._get_font_preamble_and_command()
        baselineskip = 1.25 * fontsize
        return "\n".join([
            r"\documentclass{article}",
            r"% Pass-through \mathdefault, which is used in non-usetex mode",
            r"% to use the default text font but was historically suppressed",
            r"% in usetex mode.",
            r"\newcommand{\mathdefault}[1]{#1}",
            font_preamble,
            r"\usepackage[utf8]{inputenc}",
            r"\DeclareUnicodeCharacter{2212}{\ensuremath{-}}",
            r"% geometry is loaded before the custom preamble as ",
            r"% convert_psfrags relies on a custom preamble to change the ",
            r"% geometry.",
            r"\usepackage[papersize=72in, margin=1in]{geometry}",
            cls.get_custom_preamble(),
            r"% Use `underscore` package to take care of underscores in text.",
            r"% The [strings] option allows to use underscores in file names.",
            _usepackage_if_not_loaded("underscore", option="strings"),
            r"% Custom packages (e.g. newtxtext) may already have loaded ",
            r"% textcomp with different options.",
            _usepackage_if_not_loaded("textcomp"),
            r"\pagestyle{empty}",
            r"\begin{document}",
            r"% The empty hbox ensures that a page is printed even for empty",
            r"% inputs, except when using psfrag which gets confused by it.",
            r"% matplotlibbaselinemarker is used by dviread to detect the",
            r"% last line's baseline.",
            rf"\fontsize{{{fontsize}}}{{{baselineskip}}}%",
            r"\ifdefined\psfrag\else\hbox{}\fi%",
            rf"{{{fontcmd} {tex}}}%",
            r"\end{document}",
        ])

    @classmethod
    def make_tex(cls, tex, fontsize):
        """
        Generate a tex file to render the tex string at a specific font size.

        Return the file name.
        """
        texfile = cls.get_basefile(tex, fontsize) + ".tex"
        Path(texfile).write_text(cls._get_tex_source(tex, fontsize),
                                 encoding='utf-8')
        return texfile

    @classmethod
    def _run_checked_subprocess(cls, command, tex, *, cwd=None):
        _log.debug(cbook._pformat_subprocess(command))
        try:
            report = subprocess.check_output(
                command, cwd=cwd if cwd is not None else cls._texcache,
                stderr=subprocess.STDOUT)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f'Failed to process string with tex because {command[0]} '
                'could not be found') from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                '{prog} was not able to process the following string:\n'
                '{tex!r}\n\n'
                'Here is the full command invocation and its output:\n\n'
                '{format_command}\n\n'
                '{exc}\n\n'.format(
                    prog=command[0],
                    format_command=cbook._pformat_subprocess(command),
                    tex=tex.encode('unicode_escape'),
                    exc=exc.output.decode('utf-8', 'backslashreplace'))
                ) from None
        _log.debug(report)
        return report

    @classmethod
    def make_dvi(cls, tex, fontsize):
        """
        Generate a dvi file containing latex's layout of tex string.

        Return the file name.
        """
        basefile = cls.get_basefile(tex, fontsize)
        dvifile = '%s.dvi' % basefile
        if not os.path.exists(dvifile):
            texfile = Path(cls.make_tex(tex, fontsize))
            # Generate the dvi in a temporary directory to avoid race
            # conditions e.g. if multiple processes try to process the same tex
            # string at the same time.  Having tmpdir be a subdirectory of the
            # final output dir ensures that they are on the same filesystem,
            # and thus replace() works atomically.  It also allows referring to
            # the texfile with a relative path (for pathological MPLCONFIGDIRs,
            # the absolute path may contain characters (e.g. ~) that TeX does
            # not support; n.b. relative paths cannot traverse parents, or it
            # will be blocked when `openin_any = p` in texmf.cnf).
            cwd = Path(dvifile).parent
            with TemporaryDirectory(dir=cwd) as tmpdir:
                tmppath = Path(tmpdir)
                cls._run_checked_subprocess(
                    ["latex", "-interaction=nonstopmode", "--halt-on-error",
                     f"--output-directory={tmppath.name}",
                     f"{texfile.name}"], tex, cwd=cwd)
                (tmppath / Path(dvifile).name).replace(dvifile)
        return dvifile

    @classmethod
    def make_png(cls, tex, fontsize, dpi):
        """
        Generate a png file containing latex's rendering of tex string.

        Return the file name.
        """
        basefile = cls.get_basefile(tex, fontsize, dpi)
        pngfile = '%s.png' % basefile
        # see get_rgba for a discussion of the background
        if not os.path.exists(pngfile):
            dvifile = cls.make_dvi(tex, fontsize)
            cmd = ["dvipng", "-bg", "Transparent", "-D", str(dpi),
                   "-T", "tight", "-o", pngfile, dvifile]
            # When testing, disable FreeType rendering for reproducibility; but
            # dvipng 1.16 has a bug (fixed in f3ff241) that breaks --freetype0
            # mode, so for it we keep FreeType enabled; the image will be
            # slightly off.
            if (getattr(mpl, "_called_from_pytest", False) and
                    mpl._get_executable_info("dvipng").raw_version != "1.16"):
                cmd.insert(1, "--freetype0")
            cls._run_checked_subprocess(cmd, tex)
        return pngfile

    @classmethod
    def get_grey(cls, tex, fontsize=None, dpi=None):
        """Return the alpha channel."""
        if not fontsize:
            fontsize = mpl.rcParams['font.size']
        if not dpi:
            dpi = mpl.rcParams['savefig.dpi']
        key = cls._get_tex_source(tex, fontsize), dpi
        alpha = cls._grey_arrayd.get(key)
        if alpha is None:
            pngfile = cls.make_png(tex, fontsize, dpi)
            rgba = mpl.image.imread(os.path.join(cls._texcache, pngfile))
            cls._grey_arrayd[key] = alpha = rgba[:, :, -1]
        return alpha

    @classmethod
    def get_rgba(cls, tex, fontsize=None, dpi=None, rgb=(0, 0, 0)):
        r"""
        Return latex's rendering of the tex string as an RGBA array.

        Examples
        --------
        >>> texmanager = TexManager()
        >>> s = r"\TeX\ is $\displaystyle\sum_n\frac{-e^{i\pi}}{2^n}$!"
        >>> Z = texmanager.get_rgba(s, fontsize=12, dpi=80, rgb=(1, 0, 0))
        """
        alpha = cls.get_grey(tex, fontsize, dpi)
        rgba = np.empty((*alpha.shape, 4))
        rgba[..., :3] = mpl.colors.to_rgb(rgb)
        rgba[..., -1] = alpha
        return rgba

    @classmethod
    def get_text_width_height_descent(cls, tex, fontsize, renderer=None):
        """Return width, height and descent of the text."""
        if tex.strip() == '':
            return 0, 0, 0
        dvifile = cls.make_dvi(tex, fontsize)
        dpi_fraction = renderer.points_to_pixels(1.) if renderer else 1
        with dviread.Dvi(dvifile, 72 * dpi_fraction) as dvi:
            page, = dvi
        # A total height (including the descent) needs to be returned.
        return page.width, page.height + page.descent, page.descent

# === NexusCore/openenv\Lib\site-packages\PIL\ImageMath.py ===
#
# The Python Imaging Library
# $Id$
#
# a simple math add-on for the Python Imaging Library
#
# History:
# 1999-02-15 fl   Original PIL Plus release
# 2005-05-05 fl   Simplified and cleaned up for PIL 1.1.6
# 2005-09-12 fl   Fixed int() and float() for Python 2.4.1
#
# Copyright (c) 1999-2005 by Secret Labs AB
# Copyright (c) 2005 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import builtins
from types import CodeType
from typing import Any, Callable

from . import Image, _imagingmath
from ._deprecate import deprecate


class _Operand:
    """Wraps an image operand, providing standard operators"""

    def __init__(self, im: Image.Image):
        self.im = im

    def __fixup(self, im1: _Operand | float) -> Image.Image:
        # convert image to suitable mode
        if isinstance(im1, _Operand):
            # argument was an image.
            if im1.im.mode in ("1", "L"):
                return im1.im.convert("I")
            elif im1.im.mode in ("I", "F"):
                return im1.im
            else:
                msg = f"unsupported mode: {im1.im.mode}"
                raise ValueError(msg)
        else:
            # argument was a constant
            if isinstance(im1, (int, float)) and self.im.mode in ("1", "L", "I"):
                return Image.new("I", self.im.size, im1)
            else:
                return Image.new("F", self.im.size, im1)

    def apply(
        self,
        op: str,
        im1: _Operand | float,
        im2: _Operand | float | None = None,
        mode: str | None = None,
    ) -> _Operand:
        im_1 = self.__fixup(im1)
        if im2 is None:
            # unary operation
            out = Image.new(mode or im_1.mode, im_1.size, None)
            try:
                op = getattr(_imagingmath, f"{op}_{im_1.mode}")
            except AttributeError as e:
                msg = f"bad operand type for '{op}'"
                raise TypeError(msg) from e
            _imagingmath.unop(op, out.getim(), im_1.getim())
        else:
            # binary operation
            im_2 = self.__fixup(im2)
            if im_1.mode != im_2.mode:
                # convert both arguments to floating point
                if im_1.mode != "F":
                    im_1 = im_1.convert("F")
                if im_2.mode != "F":
                    im_2 = im_2.convert("F")
            if im_1.size != im_2.size:
                # crop both arguments to a common size
                size = (
                    min(im_1.size[0], im_2.size[0]),
                    min(im_1.size[1], im_2.size[1]),
                )
                if im_1.size != size:
                    im_1 = im_1.crop((0, 0) + size)
                if im_2.size != size:
                    im_2 = im_2.crop((0, 0) + size)
            out = Image.new(mode or im_1.mode, im_1.size, None)
            try:
                op = getattr(_imagingmath, f"{op}_{im_1.mode}")
            except AttributeError as e:
                msg = f"bad operand type for '{op}'"
                raise TypeError(msg) from e
            _imagingmath.binop(op, out.getim(), im_1.getim(), im_2.getim())
        return _Operand(out)

    # unary operators
    def __bool__(self) -> bool:
        # an image is "true" if it contains at least one non-zero pixel
        return self.im.getbbox() is not None

    def __abs__(self) -> _Operand:
        return self.apply("abs", self)

    def __pos__(self) -> _Operand:
        return self

    def __neg__(self) -> _Operand:
        return self.apply("neg", self)

    # binary operators
    def __add__(self, other: _Operand | float) -> _Operand:
        return self.apply("add", self, other)

    def __radd__(self, other: _Operand | float) -> _Operand:
        return self.apply("add", other, self)

    def __sub__(self, other: _Operand | float) -> _Operand:
        return self.apply("sub", self, other)

    def __rsub__(self, other: _Operand | float) -> _Operand:
        return self.apply("sub", other, self)

    def __mul__(self, other: _Operand | float) -> _Operand:
        return self.apply("mul", self, other)

    def __rmul__(self, other: _Operand | float) -> _Operand:
        return self.apply("mul", other, self)

    def __truediv__(self, other: _Operand | float) -> _Operand:
        return self.apply("div", self, other)

    def __rtruediv__(self, other: _Operand | float) -> _Operand:
        return self.apply("div", other, self)

    def __mod__(self, other: _Operand | float) -> _Operand:
        return self.apply("mod", self, other)

    def __rmod__(self, other: _Operand | float) -> _Operand:
        return self.apply("mod", other, self)

    def __pow__(self, other: _Operand | float) -> _Operand:
        return self.apply("pow", self, other)

    def __rpow__(self, other: _Operand | float) -> _Operand:
        return self.apply("pow", other, self)

    # bitwise
    def __invert__(self) -> _Operand:
        return self.apply("invert", self)

    def __and__(self, other: _Operand | float) -> _Operand:
        return self.apply("and", self, other)

    def __rand__(self, other: _Operand | float) -> _Operand:
        return self.apply("and", other, self)

    def __or__(self, other: _Operand | float) -> _Operand:
        return self.apply("or", self, other)

    def __ror__(self, other: _Operand | float) -> _Operand:
        return self.apply("or", other, self)

    def __xor__(self, other: _Operand | float) -> _Operand:
        return self.apply("xor", self, other)

    def __rxor__(self, other: _Operand | float) -> _Operand:
        return self.apply("xor", other, self)

    def __lshift__(self, other: _Operand | float) -> _Operand:
        return self.apply("lshift", self, other)

    def __rshift__(self, other: _Operand | float) -> _Operand:
        return self.apply("rshift", self, other)

    # logical
    def __eq__(self, other: _Operand | float) -> _Operand:  # type: ignore[override]
        return self.apply("eq", self, other)

    def __ne__(self, other: _Operand | float) -> _Operand:  # type: ignore[override]
        return self.apply("ne", self, other)

    def __lt__(self, other: _Operand | float) -> _Operand:
        return self.apply("lt", self, other)

    def __le__(self, other: _Operand | float) -> _Operand:
        return self.apply("le", self, other)

    def __gt__(self, other: _Operand | float) -> _Operand:
        return self.apply("gt", self, other)

    def __ge__(self, other: _Operand | float) -> _Operand:
        return self.apply("ge", self, other)


# conversions
def imagemath_int(self: _Operand) -> _Operand:
    return _Operand(self.im.convert("I"))


def imagemath_float(self: _Operand) -> _Operand:
    return _Operand(self.im.convert("F"))


# logical
def imagemath_equal(self: _Operand, other: _Operand | float | None) -> _Operand:
    return self.apply("eq", self, other, mode="I")


def imagemath_notequal(self: _Operand, other: _Operand | float | None) -> _Operand:
    return self.apply("ne", self, other, mode="I")


def imagemath_min(self: _Operand, other: _Operand | float | None) -> _Operand:
    return self.apply("min", self, other)


def imagemath_max(self: _Operand, other: _Operand | float | None) -> _Operand:
    return self.apply("max", self, other)


def imagemath_convert(self: _Operand, mode: str) -> _Operand:
    return _Operand(self.im.convert(mode))


ops = {
    "int": imagemath_int,
    "float": imagemath_float,
    "equal": imagemath_equal,
    "notequal": imagemath_notequal,
    "min": imagemath_min,
    "max": imagemath_max,
    "convert": imagemath_convert,
}


def lambda_eval(
    expression: Callable[[dict[str, Any]], Any],
    options: dict[str, Any] = {},
    **kw: Any,
) -> Any:
    """
    Returns the result of an image function.

    :py:mod:`~PIL.ImageMath` only supports single-layer images. To process multi-band
    images, use the :py:meth:`~PIL.Image.Image.split` method or
    :py:func:`~PIL.Image.merge` function.

    :param expression: A function that receives a dictionary.
    :param options: Values to add to the function's dictionary. Deprecated.
                    You can instead use one or more keyword arguments.
    :param **kw: Values to add to the function's dictionary.
    :return: The expression result. This is usually an image object, but can
             also be an integer, a floating point value, or a pixel tuple,
             depending on the expression.
    """

    if options:
        deprecate(
            "ImageMath.lambda_eval options",
            12,
            "ImageMath.lambda_eval keyword arguments",
        )

    args: dict[str, Any] = ops.copy()
    args.update(options)
    args.update(kw)
    for k, v in args.items():
        if isinstance(v, Image.Image):
            args[k] = _Operand(v)

    out = expression(args)
    try:
        return out.im
    except AttributeError:
        return out


def unsafe_eval(
    expression: str,
    options: dict[str, Any] = {},
    **kw: Any,
) -> Any:
    """
    Evaluates an image expression. This uses Python's ``eval()`` function to process
    the expression string, and carries the security risks of doing so. It is not
    recommended to process expressions without considering this.
    :py:meth:`~lambda_eval` is a more secure alternative.

    :py:mod:`~PIL.ImageMath` only supports single-layer images. To process multi-band
    images, use the :py:meth:`~PIL.Image.Image.split` method or
    :py:func:`~PIL.Image.merge` function.

    :param expression: A string containing a Python-style expression.
    :param options: Values to add to the evaluation context. Deprecated.
                    You can instead use one or more keyword arguments.
    :param **kw: Values to add to the evaluation context.
    :return: The evaluated expression. This is usually an image object, but can
             also be an integer, a floating point value, or a pixel tuple,
             depending on the expression.
    """

    if options:
        deprecate(
            "ImageMath.unsafe_eval options",
            12,
            "ImageMath.unsafe_eval keyword arguments",
        )

    # build execution namespace
    args: dict[str, Any] = ops.copy()
    for k in list(options.keys()) + list(kw.keys()):
        if "__" in k or hasattr(builtins, k):
            msg = f"'{k}' not allowed"
            raise ValueError(msg)

    args.update(options)
    args.update(kw)
    for k, v in args.items():
        if isinstance(v, Image.Image):
            args[k] = _Operand(v)

    compiled_code = compile(expression, "<string>", "eval")

    def scan(code: CodeType) -> None:
        for const in code.co_consts:
            if type(const) is type(compiled_code):
                scan(const)

        for name in code.co_names:
            if name not in args and name != "abs":
                msg = f"'{name}' not allowed"
                raise ValueError(msg)

    scan(compiled_code)
    out = builtins.eval(expression, {"__builtins": {"abs": abs}}, args)
    try:
        return out.im
    except AttributeError:
        return out


def eval(
    expression: str,
    _dict: dict[str, Any] = {},
    **kw: Any,
) -> Any:
    """
    Evaluates an image expression.

    Deprecated. Use lambda_eval() or unsafe_eval() instead.

    :param expression: A string containing a Python-style expression.
    :param _dict: Values to add to the evaluation context.  You
                  can either use a dictionary, or one or more keyword
                  arguments.
    :return: The evaluated expression. This is usually an image object, but can
             also be an integer, a floating point value, or a pixel tuple,
             depending on the expression.

    ..  deprecated:: 10.3.0
    """

    deprecate(
        "ImageMath.eval",
        12,
        "ImageMath.lambda_eval or ImageMath.unsafe_eval",
    )
    return unsafe_eval(expression, _dict, **kw)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1\services\model_service\transports\grpc_asyncio.py ===
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
from google.longrunning import operations_pb2  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1.types import model, model_service

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
                "/google.ai.generativelanguage.v1.ModelService/GetModel",
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
                "/google.ai.generativelanguage.v1.ModelService/ListModels",
                request_serializer=model_service.ListModelsRequest.serialize,
                response_deserializer=model_service.ListModelsResponse.deserialize,
            )
        return self._stubs["list_models"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.get_model: gapic_v1.method_async.wrap_method(
                self.get_model,
                default_timeout=None,
                client_info=client_info,
            ),
            self.list_models: gapic_v1.method_async.wrap_method(
                self.list_models,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        return self.grpc_channel.close()

    @property
    def cancel_operation(
        self,
    ) -> Callable[[operations_pb2.CancelOperationRequest], None]:
        r"""Return a callable for the cancel_operation method over gRPC."""
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "cancel_operation" not in self._stubs:
            self._stubs["cancel_operation"] = self.grpc_channel.unary_unary(
                "/google.longrunning.Operations/CancelOperation",
                request_serializer=operations_pb2.CancelOperationRequest.SerializeToString,
                response_deserializer=None,
            )
        return self._stubs["cancel_operation"]

    @property
    def get_operation(
        self,
    ) -> Callable[[operations_pb2.GetOperationRequest], operations_pb2.Operation]:
        r"""Return a callable for the get_operation method over gRPC."""
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_operation" not in self._stubs:
            self._stubs["get_operation"] = self.grpc_channel.unary_unary(
                "/google.longrunning.Operations/GetOperation",
                request_serializer=operations_pb2.GetOperationRequest.SerializeToString,
                response_deserializer=operations_pb2.Operation.FromString,
            )
        return self._stubs["get_operation"]

    @property
    def list_operations(
        self,
    ) -> Callable[
        [operations_pb2.ListOperationsRequest], operations_pb2.ListOperationsResponse
    ]:
        r"""Return a callable for the list_operations method over gRPC."""
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_operations" not in self._stubs:
            self._stubs["list_operations"] = self.grpc_channel.unary_unary(
                "/google.longrunning.Operations/ListOperations",
                request_serializer=operations_pb2.ListOperationsRequest.SerializeToString,
                response_deserializer=operations_pb2.ListOperationsResponse.FromString,
            )
        return self._stubs["list_operations"]


__all__ = ("ModelServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\fine_tuning\handler.py ===
import json
import traceback
from datetime import datetime
from typing import Any, Coroutine, Literal, Optional, Union

import httpx

import litellm
from litellm._logging import verbose_logger
from litellm.llms.custom_httpx.http_handler import HTTPHandler, get_async_httpx_client
from litellm.llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import VertexLLM
from litellm.types.fine_tuning import OpenAIFineTuningHyperparameters
from litellm.types.llms.openai import FineTuningJobCreate
from litellm.types.llms.vertex_ai import (
    VERTEX_CREDENTIALS_TYPES,
    FineTuneHyperparameters,
    FineTuneJobCreate,
    FineTunesupervisedTuningSpec,
    ResponseSupervisedTuningSpec,
    ResponseTuningJob,
)
from litellm.types.utils import LiteLLMFineTuningJob


class VertexFineTuningAPI(VertexLLM):
    """
    Vertex methods to support for batches
    """

    def __init__(self) -> None:
        super().__init__()
        self.async_handler = get_async_httpx_client(
            llm_provider=litellm.LlmProviders.VERTEX_AI,
            params={"timeout": 600.0},
        )

    def convert_response_created_at(self, response: ResponseTuningJob):
        try:
            create_time_str = response.get("createTime", "") or ""
            create_time_datetime = datetime.fromisoformat(
                create_time_str.replace("Z", "+00:00")
            )
            # Convert to Unix timestamp (seconds since epoch)
            created_at = int(create_time_datetime.timestamp())

            return created_at
        except Exception:
            return 0

    def convert_openai_request_to_vertex(
        self,
        create_fine_tuning_job_data: FineTuningJobCreate,
        original_hyperparameters: dict = {},
        kwargs: Optional[dict] = None,
    ) -> FineTuneJobCreate:
        """
        convert request from OpenAI format to Vertex format
        https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/tuning
        supervised_tuning_spec = FineTunesupervisedTuningSpec(
        """

        supervised_tuning_spec = FineTunesupervisedTuningSpec(
            training_dataset_uri=create_fine_tuning_job_data.training_file,
        )

        if create_fine_tuning_job_data.validation_file:
            supervised_tuning_spec[
                "validation_dataset"
            ] = create_fine_tuning_job_data.validation_file

        _vertex_hyperparameters = (
            self._transform_openai_hyperparameters_to_vertex_hyperparameters(
                create_fine_tuning_job_data=create_fine_tuning_job_data,
                kwargs=kwargs,
                original_hyperparameters=original_hyperparameters,
            )
        )

        if _vertex_hyperparameters and len(_vertex_hyperparameters) > 0:
            supervised_tuning_spec["hyperParameters"] = _vertex_hyperparameters

        fine_tune_job = FineTuneJobCreate(
            baseModel=create_fine_tuning_job_data.model,
            supervisedTuningSpec=supervised_tuning_spec,
            tunedModelDisplayName=create_fine_tuning_job_data.suffix,
        )

        return fine_tune_job

    def _transform_openai_hyperparameters_to_vertex_hyperparameters(
        self,
        create_fine_tuning_job_data: FineTuningJobCreate,
        original_hyperparameters: dict = {},
        kwargs: Optional[dict] = None,
    ) -> FineTuneHyperparameters:
        _oai_hyperparameters = create_fine_tuning_job_data.hyperparameters
        _vertex_hyperparameters = FineTuneHyperparameters()
        if _oai_hyperparameters:
            if _oai_hyperparameters.n_epochs:
                _vertex_hyperparameters["epoch_count"] = int(
                    _oai_hyperparameters.n_epochs
                )
            if _oai_hyperparameters.learning_rate_multiplier:
                _vertex_hyperparameters["learning_rate_multiplier"] = float(
                    _oai_hyperparameters.learning_rate_multiplier
                )

        _adapter_size = original_hyperparameters.get("adapter_size", None)
        if _adapter_size:
            _vertex_hyperparameters["adapter_size"] = _adapter_size

        return _vertex_hyperparameters

    def convert_vertex_response_to_open_ai_response(
        self, response: ResponseTuningJob
    ) -> LiteLLMFineTuningJob:
        status: Literal[
            "validating_files", "queued", "running", "succeeded", "failed", "cancelled"
        ] = "queued"
        if response["state"] == "JOB_STATE_PENDING":
            status = "queued"
        if response["state"] == "JOB_STATE_SUCCEEDED":
            status = "succeeded"
        if response["state"] == "JOB_STATE_FAILED":
            status = "failed"
        if response["state"] == "JOB_STATE_CANCELLED":
            status = "cancelled"
        if response["state"] == "JOB_STATE_RUNNING":
            status = "running"

        created_at = self.convert_response_created_at(response)

        _supervisedTuningSpec: ResponseSupervisedTuningSpec = (
            response.get("supervisedTuningSpec", None) or {}
        )
        training_uri: str = _supervisedTuningSpec.get("trainingDatasetUri", "") or ""
        return LiteLLMFineTuningJob(
            id=response.get("name", "") or "",
            created_at=created_at,
            fine_tuned_model=response.get("tunedModelDisplayName", ""),
            finished_at=None,
            hyperparameters=self._translate_vertex_response_hyperparameters(
                vertex_hyper_parameters=_supervisedTuningSpec.get("hyperParameters", {})
                or {}
            ),
            model=response.get("baseModel", "") or "",
            object="fine_tuning.job",
            organization_id="",
            result_files=[],
            seed=0,
            status=status,
            trained_tokens=None,
            training_file=training_uri,
            validation_file=None,
            estimated_finish=None,
            integrations=[],
        )

    def _translate_vertex_response_hyperparameters(
        self, vertex_hyper_parameters: FineTuneHyperparameters
    ) -> OpenAIFineTuningHyperparameters:
        """
        translate vertex responsehyperparameters to openai hyperparameters
        """
        _dict_remaining_hyperparameters: dict = dict(vertex_hyper_parameters)
        return OpenAIFineTuningHyperparameters(
            n_epochs=_dict_remaining_hyperparameters.pop("epoch_count", 0),
            **_dict_remaining_hyperparameters,
        )

    async def acreate_fine_tuning_job(
        self,
        fine_tuning_url: str,
        headers: dict,
        request_data: FineTuneJobCreate,
    ):
        try:
            verbose_logger.debug(
                "about to create fine tuning job: %s, request_data: %s",
                fine_tuning_url,
                json.dumps(request_data, indent=4),
            )
            if self.async_handler is None:
                raise ValueError(
                    "VertexAI Fine Tuning - async_handler is not initialized"
                )
            response = await self.async_handler.post(
                headers=headers,
                url=fine_tuning_url,
                json=request_data,  # type: ignore
            )

            if response.status_code != 200:
                raise Exception(
                    f"Error creating fine tuning job. Status code: {response.status_code}. Response: {response.text}"
                )

            verbose_logger.debug(
                "got response from creating fine tuning job: %s", response.json()
            )

            vertex_response = ResponseTuningJob(  # type: ignore
                **response.json(),
            )

            verbose_logger.debug("vertex_response %s", vertex_response)
            open_ai_response = self.convert_vertex_response_to_open_ai_response(
                vertex_response
            )
            return open_ai_response

        except Exception as e:
            verbose_logger.error("asyncerror creating fine tuning job %s", e)
            trace_back_str = traceback.format_exc()
            verbose_logger.error(trace_back_str)
            raise e

    def create_fine_tuning_job(
        self,
        _is_async: bool,
        create_fine_tuning_job_data: FineTuningJobCreate,
        vertex_project: Optional[str],
        vertex_location: Optional[str],
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES],
        api_base: Optional[str],
        timeout: Union[float, httpx.Timeout],
        kwargs: Optional[dict] = None,
        original_hyperparameters: Optional[dict] = {},
    ) -> Union[LiteLLMFineTuningJob, Coroutine[Any, Any, LiteLLMFineTuningJob]]:
        verbose_logger.debug(
            "creating fine tuning job, args= %s", create_fine_tuning_job_data
        )
        _auth_header, vertex_project = self._ensure_access_token(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider="vertex_ai_beta",
        )

        auth_header, _ = self._get_token_and_url(
            model="",
            auth_header=_auth_header,
            gemini_api_key=None,
            vertex_credentials=vertex_credentials,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            stream=False,
            custom_llm_provider="vertex_ai_beta",
            api_base=api_base,
        )

        headers = {
            "Authorization": f"Bearer {auth_header}",
            "Content-Type": "application/json",
        }

        fine_tune_job = self.convert_openai_request_to_vertex(
            create_fine_tuning_job_data=create_fine_tuning_job_data,
            kwargs=kwargs,
            original_hyperparameters=original_hyperparameters or {},
        )

        fine_tuning_url = f"https://{vertex_location}-aiplatform.googleapis.com/v1/projects/{vertex_project}/locations/{vertex_location}/tuningJobs"
        if _is_async is True:
            return self.acreate_fine_tuning_job(  # type: ignore
                fine_tuning_url=fine_tuning_url,
                headers=headers,
                request_data=fine_tune_job,
            )
        sync_handler = HTTPHandler(timeout=httpx.Timeout(timeout=600.0, connect=5.0))

        verbose_logger.debug(
            "about to create fine tuning job: %s, request_data: %s",
            fine_tuning_url,
            fine_tune_job,
        )
        response = sync_handler.post(
            headers=headers,
            url=fine_tuning_url,
            json=fine_tune_job,  # type: ignore
        )

        if response.status_code != 200:
            raise Exception(
                f"Error creating fine tuning job. Status code: {response.status_code}. Response: {response.text}"
            )

        verbose_logger.debug(
            "got response from creating fine tuning job: %s", response.json()
        )
        vertex_response = ResponseTuningJob(  # type: ignore
            **response.json(),
        )

        verbose_logger.debug("vertex_response %s", vertex_response)
        open_ai_response = self.convert_vertex_response_to_open_ai_response(
            vertex_response
        )
        return open_ai_response

    async def pass_through_vertex_ai_POST_request(
        self,
        request_data: dict,
        vertex_project: str,
        vertex_location: str,
        vertex_credentials: str,
        request_route: str,
    ):
        _auth_header, vertex_project = await self._ensure_access_token_async(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider="vertex_ai_beta",
        )
        auth_header, _ = self._get_token_and_url(
            model="",
            auth_header=_auth_header,
            gemini_api_key=None,
            vertex_credentials=vertex_credentials,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            stream=False,
            custom_llm_provider="vertex_ai_beta",
            api_base="",
        )

        headers = {
            "Authorization": f"Bearer {auth_header}",
            "Content-Type": "application/json",
        }

        url = None
        if request_route == "/tuningJobs":
            url = f"https://{vertex_location}-aiplatform.googleapis.com/v1/projects/{vertex_project}/locations/{vertex_location}/tuningJobs"
        elif "/tuningJobs/" in request_route and "cancel" in request_route:
            url = f"https://{vertex_location}-aiplatform.googleapis.com/v1/projects/{vertex_project}/locations/{vertex_location}/tuningJobs{request_route}"
        elif "generateContent" in request_route:
            url = f"https://{vertex_location}-aiplatform.googleapis.com/v1/projects/{vertex_project}/locations/{vertex_location}{request_route}"
        elif "predict" in request_route:
            url = f"https://{vertex_location}-aiplatform.googleapis.com/v1/projects/{vertex_project}/locations/{vertex_location}{request_route}"
        elif "/batchPredictionJobs" in request_route:
            url = f"https://{vertex_location}-aiplatform.googleapis.com/v1/projects/{vertex_project}/locations/{vertex_location}{request_route}"
        elif "countTokens" in request_route:
            url = f"https://{vertex_location}-aiplatform.googleapis.com/v1/projects/{vertex_project}/locations/{vertex_location}{request_route}"
        elif "cachedContents" in request_route:
            _model = request_data.get("model")
            if _model is not None and "/publishers/google/models/" not in _model:
                request_data[
                    "model"
                ] = f"projects/{vertex_project}/locations/{vertex_location}/publishers/google/models/{_model}"

            url = f"https://{vertex_location}-aiplatform.googleapis.com/v1beta1/projects/{vertex_project}/locations/{vertex_location}{request_route}"
        else:
            raise ValueError(f"Unsupported Vertex AI request route: {request_route}")
        if self.async_handler is None:
            raise ValueError("VertexAI Fine Tuning - async_handler is not initialized")

        response = await self.async_handler.post(
            headers=headers,
            url=url,
            json=request_data,  # type: ignore
        )

        if response.status_code != 200:
            raise Exception(
                f"Error creating fine tuning job. Status code: {response.status_code}. Response: {response.text}"
            )

        response_json = response.json()
        return response_json

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\support\relative_locator.py ===
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
import warnings
from typing import Dict, List, NoReturn, Optional, Union, overload

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By, ByType
from selenium.webdriver.remote.webelement import WebElement


def with_tag_name(tag_name: str) -> "RelativeBy":
    """Start searching for relative objects using a tag name.

    Parameters:
    -----------
    tag_name : str
        The DOM tag of element to start searching.

    Returns:
    --------
    RelativeBy
        Use this object to create filters within a `find_elements` call.

    Raises:
    -------
    WebDriverException
        If `tag_name` is None.

    Notes:
    ------
    - This method is deprecated and may be removed in future versions.
    - Please use `locate_with` instead.
    """
    warnings.warn("This method is deprecated and may be removed in future versions. Please use `locate_with` instead.")
    if not tag_name:
        raise WebDriverException("tag_name can not be null")
    return RelativeBy({By.CSS_SELECTOR: tag_name})


def locate_with(by: ByType, using: str) -> "RelativeBy":
    """Start searching for relative objects your search criteria with By.

    Parameters:
    -----------
    by : ByType
        The method to find the element.

    using : str
        The value from `By` passed in.

    Returns:
    --------
    RelativeBy
        Use this object to create filters within a `find_elements` call.

    Example:
    --------
    >>> lowest = driver.find_element(By.ID, "below")
    >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").above(lowest))
    """
    assert by is not None, "Please pass in a by argument"
    assert using is not None, "Please pass in a using argument"
    return RelativeBy({by: using})


class RelativeBy:
    """Gives the opportunity to find elements based on their relative location
    on the page from a root element. It is recommended that you use the helper
    function to create it.

    Example:
    --------
    >>> lowest = driver.find_element(By.ID, "below")
    >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").above(lowest))
    >>> ids = [el.get_attribute("id") for el in elements]
    >>> assert "above" in ids
    >>> assert "mid" in ids
    """

    LocatorType = Dict[ByType, str]

    def __init__(self, root: Optional[Dict[ByType, str]] = None, filters: Optional[List] = None):
        """Creates a new RelativeBy object. It is preferred if you use the
        `locate_with` method as this signature could change.

        Attributes:
        -----------
        root : Dict[By, str]
            - A dict with `By` enum as the key and the search query as the value

        filters : List
            - A list of the filters that will be searched. If none are passed
                in please use the fluent API on the object to create the filters
        """
        self.root = root
        self.filters = filters or []

    @overload
    def above(self, element_or_locator: Union[WebElement, LocatorType]) -> "RelativeBy": ...

    @overload
    def above(self, element_or_locator: None = None) -> "NoReturn": ...

    def above(self, element_or_locator: Union[WebElement, LocatorType, None] = None) -> "RelativeBy":
        """Add a filter to look for elements above.

        Parameters:
        -----------
        element_or_locator : Union[WebElement, Dict, None]
            Element to look above

        Returns:
        --------
        RelativeBy

        Raises:
        -------
        WebDriverException
            If `element_or_locator` is None.

        Example:
        --------
        >>> lowest = driver.find_element(By.ID, "below")
        >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").above(lowest))
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling above method")

        self.filters.append({"kind": "above", "args": [element_or_locator]})
        return self

    @overload
    def below(self, element_or_locator: Union[WebElement, LocatorType]) -> "RelativeBy": ...

    @overload
    def below(self, element_or_locator: None = None) -> "NoReturn": ...

    def below(self, element_or_locator: Union[WebElement, Dict, None] = None) -> "RelativeBy":
        """Add a filter to look for elements below.

        Parameters:
        -----------
        element_or_locator : Union[WebElement, Dict, None]
            Element to look below

        Returns:
        --------
        RelativeBy

        Raises:
        -------
        WebDriverException
            If `element_or_locator` is None.

        Example:
        --------
        >>> highest = driver.find_element(By.ID, "high")
        >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").below(highest))
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling below method")

        self.filters.append({"kind": "below", "args": [element_or_locator]})
        return self

    @overload
    def to_left_of(self, element_or_locator: Union[WebElement, LocatorType]) -> "RelativeBy": ...

    @overload
    def to_left_of(self, element_or_locator: None = None) -> "NoReturn": ...

    def to_left_of(self, element_or_locator: Union[WebElement, Dict, None] = None) -> "RelativeBy":
        """Add a filter to look for elements to the left of.

        Parameters:
        -----------
        element_or_locator : Union[WebElement, Dict, None]
            Element to look to the left of

        Returns:
        --------
        RelativeBy

        Raises:
        -------
        WebDriverException
            If `element_or_locator` is None.

        Example:
        --------
        >>> right = driver.find_element(By.ID, "right")
        >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").to_left_of(right))
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling to_left_of method")

        self.filters.append({"kind": "left", "args": [element_or_locator]})
        return self

    @overload
    def to_right_of(self, element_or_locator: Union[WebElement, LocatorType]) -> "RelativeBy": ...

    @overload
    def to_right_of(self, element_or_locator: None = None) -> "NoReturn": ...

    def to_right_of(self, element_or_locator: Union[WebElement, Dict, None] = None) -> "RelativeBy":
        """Add a filter to look for elements right of.

        Parameters:
        -----------
        element_or_locator : Union[WebElement, Dict, None]
            Element to look right of

        Returns:
        --------
        RelativeBy

        Raises:
        -------
        WebDriverException
            If `element_or_locator` is None.

        Example:
        --------
        >>> left = driver.find_element(By.ID, "left")
        >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").to_right_of(left))
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling to_right_of method")

        self.filters.append({"kind": "right", "args": [element_or_locator]})
        return self

    @overload
    def straight_above(self, element_or_locator: Union[WebElement, LocatorType]) -> "RelativeBy": ...

    @overload
    def straight_above(self, element_or_locator: None = None) -> "NoReturn": ...

    def straight_above(self, element_or_locator: Union[WebElement, LocatorType, None] = None) -> "RelativeBy":
        """Add a filter to look for elements above.

        :Args:
            - element_or_locator: Element to look above
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling above method")

        self.filters.append({"kind": "straightAbove", "args": [element_or_locator]})
        return self

    @overload
    def straight_below(self, element_or_locator: Union[WebElement, LocatorType]) -> "RelativeBy": ...

    @overload
    def straight_below(self, element_or_locator: None = None) -> "NoReturn": ...

    def straight_below(self, element_or_locator: Union[WebElement, Dict, None] = None) -> "RelativeBy":
        """Add a filter to look for elements below.

        :Args:
            - element_or_locator: Element to look below
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling below method")

        self.filters.append({"kind": "straightBelow", "args": [element_or_locator]})
        return self

    @overload
    def straight_left_of(self, element_or_locator: Union[WebElement, LocatorType]) -> "RelativeBy": ...

    @overload
    def straight_left_of(self, element_or_locator: None = None) -> "NoReturn": ...

    def straight_left_of(self, element_or_locator: Union[WebElement, Dict, None] = None) -> "RelativeBy":
        """Add a filter to look for elements to the left of.

        :Args:
            - element_or_locator: Element to look to the left of
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling to_left_of method")

        self.filters.append({"kind": "straightLeft", "args": [element_or_locator]})
        return self

    @overload
    def straight_right_of(self, element_or_locator: Union[WebElement, LocatorType]) -> "RelativeBy": ...

    @overload
    def straight_right_of(self, element_or_locator: None = None) -> "NoReturn": ...

    def straight_right_of(self, element_or_locator: Union[WebElement, Dict, None] = None) -> "RelativeBy":
        """Add a filter to look for elements right of.

        :Args:
            - element_or_locator: Element to look right of
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling to_right_of method")

        self.filters.append({"kind": "straightRight", "args": [element_or_locator]})
        return self

    @overload
    def near(self, element_or_locator: Union[WebElement, LocatorType], distance: int = 50) -> "RelativeBy": ...

    @overload
    def near(self, element_or_locator: None = None, distance: int = 50) -> "NoReturn": ...

    def near(self, element_or_locator: Union[WebElement, LocatorType, None] = None, distance: int = 50) -> "RelativeBy":
        """Add a filter to look for elements near.

        Parameters:
        -----------
        element_or_locator : Union[WebElement, Dict, None]
            Element to look near by the element or within a distance

        distance : int
            Distance in pixel

        Returns:
        --------
        RelativeBy

        Raises:
        -------
        WebDriverException
            - If `element_or_locator` is None
            - If `distance` is less than or equal to 0.

        Example:
        --------
        >>> near = driver.find_element(By.ID, "near")
        >>> elements = driver.find_elements(locate_with(By.CSS_SELECTOR, "p").near(near, 50))
        """
        if not element_or_locator:
            raise WebDriverException("Element or locator must be given when calling near method")
        if distance <= 0:
            raise WebDriverException("Distance must be positive")

        self.filters.append({"kind": "near", "args": [element_or_locator, distance]})
        return self

    def to_dict(self) -> Dict:
        """Create a dict that will be passed to the driver to start searching
        for the element."""
        return {
            "relative": {
                "root": self.root,
                "filters": self.filters,
            }
        }

# === NexusCore/openenv\Lib\site-packages\win32com\demos\ietoolbar.py ===
# -*- coding: latin-1 -*-

# PyWin32 Internet Explorer Toolbar
#
# written by Leonard Ritter (paniq@gmx.net)
# and Robert Förtsch (info@robert-foertsch.com)


"""
This sample implements a simple IE Toolbar COM server
supporting Windows XP styles and access to
the IWebBrowser2 interface.

It also demonstrates how to hijack the parent window
to catch WM_COMMAND messages.
"""

import array
import struct

# imports section
import sys
import winreg

import commctrl
import pythoncom
import win32com
import win32con
import win32gui
import win32ui
from win32com.axcontrol import axcontrol
from win32com.client import Dispatch, gencache
from win32com.shell import shell
from win32com.shell.shellcon import DBIMF_VARIABLEHEIGHT

# ensure we know the ms internet controls typelib so we have access to IWebBrowser2 later on
gencache.EnsureModule("{EAB22AC0-30C1-11CF-A7EB-0000C05BAE0B}", 0, 1, 1)

#
IDeskBand_methods = ["GetBandInfo"]
IDockingWindow_methods = ["ShowDW", "CloseDW", "ResizeBorderDW"]
IOleWindow_methods = ["GetWindow", "ContextSensitiveHelp"]
IInputObject_methods = ["UIActivateIO", "HasFocusIO", "TranslateAcceleratorIO"]
IObjectWithSite_methods = ["SetSite", "GetSite"]
IPersistStream_methods = ["GetClassID", "IsDirty", "Load", "Save", "GetSizeMax"]

_ietoolbar_methods_ = (
    IDeskBand_methods
    + IDockingWindow_methods
    + IOleWindow_methods
    + IInputObject_methods
    + IObjectWithSite_methods
    + IPersistStream_methods
)
_ietoolbar_com_interfaces_ = [
    shell.IID_IDeskBand,  # IDeskBand
    axcontrol.IID_IObjectWithSite,  # IObjectWithSite
    pythoncom.IID_IPersistStream,
    axcontrol.IID_IOleCommandTarget,
]


class WIN32STRUCT:
    def __init__(self, **kw):
        full_fmt = ""
        for name, fmt, default in self._struct_items_:
            self.__dict__[name] = None
            if fmt == "z":
                full_fmt += "pi"
            else:
                full_fmt += fmt
        for name, val in kw.items():
            self.__dict__[name] = val

    def __setattr__(self, attr, val):
        if not attr.startswith("_") and attr not in self.__dict__:
            raise AttributeError(attr)
        self.__dict__[attr] = val

    def toparam(self):
        self._buffs = []
        full_fmt = ""
        vals = []
        for name, fmt, default in self._struct_items_:
            val = self.__dict__[name]
            if fmt == "z":
                fmt = "Pi"
                if val is None:
                    vals.append(0)
                    vals.append(0)
                else:
                    str_buf = array.array("c", val + "\0")
                    vals.append(str_buf.buffer_info()[0])
                    vals.append(len(val))
                    self._buffs.append(str_buf)  # keep alive during the call.
            else:
                if val is None:
                    val = default
                vals.append(val)
            full_fmt += fmt
        return struct.pack(*(full_fmt,) + tuple(vals))


class TBBUTTON(WIN32STRUCT):
    _struct_items_ = [
        ("iBitmap", "i", 0),
        ("idCommand", "i", 0),
        ("fsState", "B", 0),
        ("fsStyle", "B", 0),
        ("bReserved", "H", 0),
        ("dwData", "I", 0),
        ("iString", "z", None),
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


class IEToolbarCtrl:
    """
    a tiny wrapper for our winapi-based
    toolbar control implementation.
    """

    def __init__(self, hwndparent):
        styles = (
            win32con.WS_CHILD
            | win32con.WS_VISIBLE
            | win32con.WS_CLIPSIBLINGS
            | win32con.WS_CLIPCHILDREN
            | commctrl.TBSTYLE_LIST
            | commctrl.TBSTYLE_FLAT
            | commctrl.TBSTYLE_TRANSPARENT
            | commctrl.CCS_TOP
            | commctrl.CCS_NODIVIDER
            | commctrl.CCS_NORESIZE
            | commctrl.CCS_NOPARENTALIGN
        )
        self.hwnd = win32gui.CreateWindow(
            "ToolbarWindow32",
            None,
            styles,
            0,
            0,
            100,
            100,
            hwndparent,
            0,
            win32gui.dllhandle,
            None,
        )
        win32gui.SendMessage(self.hwnd, commctrl.TB_BUTTONSTRUCTSIZE, 20, 0)

    def ShowWindow(self, mode):
        win32gui.ShowWindow(self.hwnd, mode)

    def AddButtons(self, *buttons):
        tbbuttons = ""
        for button in buttons:
            tbbuttons += button.toparam()
        return win32gui.SendMessage(
            self.hwnd, commctrl.TB_ADDBUTTONS, len(buttons), tbbuttons
        )

    def GetSafeHwnd(self):
        return self.hwnd


class IEToolbar:
    """
    The actual COM server class
    """

    _com_interfaces_ = _ietoolbar_com_interfaces_
    _public_methods_ = _ietoolbar_methods_
    _reg_clsctx_ = pythoncom.CLSCTX_INPROC_SERVER
    # if you copy and modify this example, be sure to change the clsid below
    _reg_clsid_ = "{F21202A2-959A-4149-B1C3-68B9013F3335}"
    _reg_progid_ = "PyWin32.IEToolbar"
    _reg_desc_ = "PyWin32 IE Toolbar"

    def __init__(self):
        # put stubs for non-implemented methods
        for method in self._public_methods_:
            if not hasattr(self, method):
                print("providing default stub for %s" % method)
                setattr(self, method, Stub(method))

    def GetWindow(self):
        return self.toolbar.GetSafeHwnd()

    def Load(self, stream):
        # called when the toolbar is loaded
        pass

    def Save(self, pStream, fClearDirty):
        # called when the toolbar shall save its information
        pass

    def CloseDW(self, dwReserved):
        del self.toolbar

    def ShowDW(self, bShow):
        if bShow:
            self.toolbar.ShowWindow(win32con.SW_SHOW)
        else:
            self.toolbar.ShowWindow(win32con.SW_HIDE)

    def on_first_button(self):
        print("first!")
        self.webbrowser.Navigate2("https://github.com/mhammond/pywin32")

    def on_second_button(self):
        print("second!")

    def on_third_button(self):
        print("third!")

    def toolbar_command_handler(self, args):
        hwnd, message, wparam, lparam, time, point = args
        if lparam == self.toolbar.GetSafeHwnd():
            self._command_map[wparam]()

    def SetSite(self, unknown):
        if unknown:
            # retrieve the parent window interface for this site
            olewindow = unknown.QueryInterface(pythoncom.IID_IOleWindow)
            # ask the window for its handle
            hwndparent = olewindow.GetWindow()

            # first get a command target
            cmdtarget = unknown.QueryInterface(axcontrol.IID_IOleCommandTarget)
            # then travel over to a service provider
            serviceprovider = cmdtarget.QueryInterface(pythoncom.IID_IServiceProvider)
            # finally ask for the internet explorer application, returned as a dispatch object
            self.webbrowser = Dispatch(
                serviceprovider.QueryService(
                    "{0002DF05-0000-0000-C000-000000000046}", pythoncom.IID_IDispatch
                )
            )

            # now create and set up the toolbar
            self.toolbar = IEToolbarCtrl(hwndparent)

            buttons = [
                ("Visit PyWin32 Homepage", self.on_first_button),
                ("Another Button", self.on_second_button),
                ("Yet Another Button", self.on_third_button),
            ]

            self._command_map = {}
            # wrap our parent window so we can hook message handlers
            window = win32ui.CreateWindowFromHandle(hwndparent)

            # add the buttons
            for i in range(len(buttons)):
                button = TBBUTTON()
                name, func = buttons[i]
                id = 0x4444 + i
                button.iBitmap = -2
                button.idCommand = id
                button.fsState = commctrl.TBSTATE_ENABLED
                button.fsStyle = commctrl.TBSTYLE_BUTTON
                button.iString = name
                self._command_map[0x4444 + i] = func
                self.toolbar.AddButtons(button)
                window.HookMessage(self.toolbar_command_handler, win32con.WM_COMMAND)
        else:
            # lose all references
            self.webbrowser = None

    def GetClassID(self):
        return self._reg_clsid_

    def GetBandInfo(self, dwBandId, dwViewMode, dwMask):
        ptMinSize = (0, 24)
        ptMaxSize = (2000, 24)
        ptIntegral = (0, 0)
        ptActual = (2000, 24)
        wszTitle = "PyWin32 IE Toolbar"
        dwModeFlags = DBIMF_VARIABLEHEIGHT
        crBkgnd = 0
        return (
            ptMinSize,
            ptMaxSize,
            ptIntegral,
            ptActual,
            wszTitle,
            dwModeFlags,
            crBkgnd,
        )


# used for HKLM install
def DllInstall(bInstall, cmdLine):
    comclass = IEToolbar


# register plugin
def DllRegisterServer():
    comclass = IEToolbar

    # register toolbar with IE
    try:
        print("Trying to register Toolbar.\n")
        hkey = winreg.CreateKey(
            winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Internet Explorer\\Toolbar"
        )
        subKey = winreg.SetValueEx(
            hkey, comclass._reg_clsid_, 0, winreg.REG_BINARY, b"\0"
        )
    except OSError:
        print(
            "Couldn't set registry value.\nhkey: %d\tCLSID: %s\n"
            % (hkey, comclass._reg_clsid_)
        )
    else:
        print(
            "Set registry value.\nhkey: %d\tCLSID: %s\n" % (hkey, comclass._reg_clsid_)
        )
    # TODO: implement reg settings for standard toolbar button


# unregister plugin
def DllUnregisterServer():
    comclass = IEToolbar

    # unregister toolbar from internet explorer
    try:
        print("Trying to unregister Toolbar.\n")
        hkey = winreg.CreateKey(
            winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Internet Explorer\\Toolbar"
        )
        winreg.DeleteValue(hkey, comclass._reg_clsid_)
    except OSError:
        print(
            "Couldn't delete registry value.\nhkey: %d\tCLSID: %s\n"
            % (hkey, comclass._reg_clsid_)
        )
    else:
        print("Deleting reg key succeeded.\n")


# entry point
if __name__ == "__main__":
    import win32com.server.register

    win32com.server.register.UseCommandLine(IEToolbar)

    # parse actual command line option
    if "--unregister" in sys.argv:
        DllUnregisterServer()
    else:
        DllRegisterServer()
else:
    # import trace utility for remote debugging
    import win32traceutil

# === NexusCore/openenv\Lib\site-packages\httpcore\_async\http_proxy.py ===
from __future__ import annotations

import base64
import logging
import ssl
import typing

from .._backends.base import SOCKET_OPTION, AsyncNetworkBackend
from .._exceptions import ProxyError
from .._models import (
    URL,
    Origin,
    Request,
    Response,
    enforce_bytes,
    enforce_headers,
    enforce_url,
)
from .._ssl import default_ssl_context
from .._synchronization import AsyncLock
from .._trace import Trace
from .connection import AsyncHTTPConnection
from .connection_pool import AsyncConnectionPool
from .http11 import AsyncHTTP11Connection
from .interfaces import AsyncConnectionInterface

ByteOrStr = typing.Union[bytes, str]
HeadersAsSequence = typing.Sequence[typing.Tuple[ByteOrStr, ByteOrStr]]
HeadersAsMapping = typing.Mapping[ByteOrStr, ByteOrStr]


logger = logging.getLogger("httpcore.proxy")


def merge_headers(
    default_headers: typing.Sequence[tuple[bytes, bytes]] | None = None,
    override_headers: typing.Sequence[tuple[bytes, bytes]] | None = None,
) -> list[tuple[bytes, bytes]]:
    """
    Append default_headers and override_headers, de-duplicating if a key exists
    in both cases.
    """
    default_headers = [] if default_headers is None else list(default_headers)
    override_headers = [] if override_headers is None else list(override_headers)
    has_override = set(key.lower() for key, value in override_headers)
    default_headers = [
        (key, value)
        for key, value in default_headers
        if key.lower() not in has_override
    ]
    return default_headers + override_headers


class AsyncHTTPProxy(AsyncConnectionPool):  # pragma: nocover
    """
    A connection pool that sends requests via an HTTP proxy.
    """

    def __init__(
        self,
        proxy_url: URL | bytes | str,
        proxy_auth: tuple[bytes | str, bytes | str] | None = None,
        proxy_headers: HeadersAsMapping | HeadersAsSequence | None = None,
        ssl_context: ssl.SSLContext | None = None,
        proxy_ssl_context: ssl.SSLContext | None = None,
        max_connections: int | None = 10,
        max_keepalive_connections: int | None = None,
        keepalive_expiry: float | None = None,
        http1: bool = True,
        http2: bool = False,
        retries: int = 0,
        local_address: str | None = None,
        uds: str | None = None,
        network_backend: AsyncNetworkBackend | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> None:
        """
        A connection pool for making HTTP requests.

        Parameters:
            proxy_url: The URL to use when connecting to the proxy server.
                For example `"http://127.0.0.1:8080/"`.
            proxy_auth: Any proxy authentication as a two-tuple of
                (username, password). May be either bytes or ascii-only str.
            proxy_headers: Any HTTP headers to use for the proxy requests.
                For example `{"Proxy-Authorization": "Basic <username>:<password>"}`.
            ssl_context: An SSL context to use for verifying connections.
                If not specified, the default `httpcore.default_ssl_context()`
                will be used.
            proxy_ssl_context: The same as `ssl_context`, but for a proxy server rather than a remote origin.
            max_connections: The maximum number of concurrent HTTP connections that
                the pool should allow. Any attempt to send a request on a pool that
                would exceed this amount will block until a connection is available.
            max_keepalive_connections: The maximum number of idle HTTP connections
                that will be maintained in the pool.
            keepalive_expiry: The duration in seconds that an idle HTTP connection
                may be maintained for before being expired from the pool.
            http1: A boolean indicating if HTTP/1.1 requests should be supported
                by the connection pool. Defaults to True.
            http2: A boolean indicating if HTTP/2 requests should be supported by
                the connection pool. Defaults to False.
            retries: The maximum number of retries when trying to establish
                a connection.
            local_address: Local address to connect from. Can also be used to
                connect using a particular address family. Using
                `local_address="0.0.0.0"` will connect using an `AF_INET` address
                (IPv4), while using `local_address="::"` will connect using an
                `AF_INET6` address (IPv6).
            uds: Path to a Unix Domain Socket to use instead of TCP sockets.
            network_backend: A backend instance to use for handling network I/O.
        """
        super().__init__(
            ssl_context=ssl_context,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            http1=http1,
            http2=http2,
            network_backend=network_backend,
            retries=retries,
            local_address=local_address,
            uds=uds,
            socket_options=socket_options,
        )

        self._proxy_url = enforce_url(proxy_url, name="proxy_url")
        if (
            self._proxy_url.scheme == b"http" and proxy_ssl_context is not None
        ):  # pragma: no cover
            raise RuntimeError(
                "The `proxy_ssl_context` argument is not allowed for the http scheme"
            )

        self._ssl_context = ssl_context
        self._proxy_ssl_context = proxy_ssl_context
        self._proxy_headers = enforce_headers(proxy_headers, name="proxy_headers")
        if proxy_auth is not None:
            username = enforce_bytes(proxy_auth[0], name="proxy_auth")
            password = enforce_bytes(proxy_auth[1], name="proxy_auth")
            userpass = username + b":" + password
            authorization = b"Basic " + base64.b64encode(userpass)
            self._proxy_headers = [
                (b"Proxy-Authorization", authorization)
            ] + self._proxy_headers

    def create_connection(self, origin: Origin) -> AsyncConnectionInterface:
        if origin.scheme == b"http":
            return AsyncForwardHTTPConnection(
                proxy_origin=self._proxy_url.origin,
                proxy_headers=self._proxy_headers,
                remote_origin=origin,
                keepalive_expiry=self._keepalive_expiry,
                network_backend=self._network_backend,
                proxy_ssl_context=self._proxy_ssl_context,
            )
        return AsyncTunnelHTTPConnection(
            proxy_origin=self._proxy_url.origin,
            proxy_headers=self._proxy_headers,
            remote_origin=origin,
            ssl_context=self._ssl_context,
            proxy_ssl_context=self._proxy_ssl_context,
            keepalive_expiry=self._keepalive_expiry,
            http1=self._http1,
            http2=self._http2,
            network_backend=self._network_backend,
        )


class AsyncForwardHTTPConnection(AsyncConnectionInterface):
    def __init__(
        self,
        proxy_origin: Origin,
        remote_origin: Origin,
        proxy_headers: HeadersAsMapping | HeadersAsSequence | None = None,
        keepalive_expiry: float | None = None,
        network_backend: AsyncNetworkBackend | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
        proxy_ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self._connection = AsyncHTTPConnection(
            origin=proxy_origin,
            keepalive_expiry=keepalive_expiry,
            network_backend=network_backend,
            socket_options=socket_options,
            ssl_context=proxy_ssl_context,
        )
        self._proxy_origin = proxy_origin
        self._proxy_headers = enforce_headers(proxy_headers, name="proxy_headers")
        self._remote_origin = remote_origin

    async def handle_async_request(self, request: Request) -> Response:
        headers = merge_headers(self._proxy_headers, request.headers)
        url = URL(
            scheme=self._proxy_origin.scheme,
            host=self._proxy_origin.host,
            port=self._proxy_origin.port,
            target=bytes(request.url),
        )
        proxy_request = Request(
            method=request.method,
            url=url,
            headers=headers,
            content=request.stream,
            extensions=request.extensions,
        )
        return await self._connection.handle_async_request(proxy_request)

    def can_handle_request(self, origin: Origin) -> bool:
        return origin == self._remote_origin

    async def aclose(self) -> None:
        await self._connection.aclose()

    def info(self) -> str:
        return self._connection.info()

    def is_available(self) -> bool:
        return self._connection.is_available()

    def has_expired(self) -> bool:
        return self._connection.has_expired()

    def is_idle(self) -> bool:
        return self._connection.is_idle()

    def is_closed(self) -> bool:
        return self._connection.is_closed()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} [{self.info()}]>"


class AsyncTunnelHTTPConnection(AsyncConnectionInterface):
    def __init__(
        self,
        proxy_origin: Origin,
        remote_origin: Origin,
        ssl_context: ssl.SSLContext | None = None,
        proxy_ssl_context: ssl.SSLContext | None = None,
        proxy_headers: typing.Sequence[tuple[bytes, bytes]] | None = None,
        keepalive_expiry: float | None = None,
        http1: bool = True,
        http2: bool = False,
        network_backend: AsyncNetworkBackend | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> None:
        self._connection: AsyncConnectionInterface = AsyncHTTPConnection(
            origin=proxy_origin,
            keepalive_expiry=keepalive_expiry,
            network_backend=network_backend,
            socket_options=socket_options,
            ssl_context=proxy_ssl_context,
        )
        self._proxy_origin = proxy_origin
        self._remote_origin = remote_origin
        self._ssl_context = ssl_context
        self._proxy_ssl_context = proxy_ssl_context
        self._proxy_headers = enforce_headers(proxy_headers, name="proxy_headers")
        self._keepalive_expiry = keepalive_expiry
        self._http1 = http1
        self._http2 = http2
        self._connect_lock = AsyncLock()
        self._connected = False

    async def handle_async_request(self, request: Request) -> Response:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("connect", None)

        async with self._connect_lock:
            if not self._connected:
                target = b"%b:%d" % (self._remote_origin.host, self._remote_origin.port)

                connect_url = URL(
                    scheme=self._proxy_origin.scheme,
                    host=self._proxy_origin.host,
                    port=self._proxy_origin.port,
                    target=target,
                )
                connect_headers = merge_headers(
                    [(b"Host", target), (b"Accept", b"*/*")], self._proxy_headers
                )
                connect_request = Request(
                    method=b"CONNECT",
                    url=connect_url,
                    headers=connect_headers,
                    extensions=request.extensions,
                )
                connect_response = await self._connection.handle_async_request(
                    connect_request
                )

                if connect_response.status < 200 or connect_response.status > 299:
                    reason_bytes = connect_response.extensions.get("reason_phrase", b"")
                    reason_str = reason_bytes.decode("ascii", errors="ignore")
                    msg = "%d %s" % (connect_response.status, reason_str)
                    await self._connection.aclose()
                    raise ProxyError(msg)

                stream = connect_response.extensions["network_stream"]

                # Upgrade the stream to SSL
                ssl_context = (
                    default_ssl_context()
                    if self._ssl_context is None
                    else self._ssl_context
                )
                alpn_protocols = ["http/1.1", "h2"] if self._http2 else ["http/1.1"]
                ssl_context.set_alpn_protocols(alpn_protocols)

                kwargs = {
                    "ssl_context": ssl_context,
                    "server_hostname": self._remote_origin.host.decode("ascii"),
                    "timeout": timeout,
                }
                async with Trace("start_tls", logger, request, kwargs) as trace:
                    stream = await stream.start_tls(**kwargs)
                    trace.return_value = stream

                # Determine if we should be using HTTP/1.1 or HTTP/2
                ssl_object = stream.get_extra_info("ssl_object")
                http2_negotiated = (
                    ssl_object is not None
                    and ssl_object.selected_alpn_protocol() == "h2"
                )

                # Create the HTTP/1.1 or HTTP/2 connection
                if http2_negotiated or (self._http2 and not self._http1):
                    from .http2 import AsyncHTTP2Connection

                    self._connection = AsyncHTTP2Connection(
                        origin=self._remote_origin,
                        stream=stream,
                        keepalive_expiry=self._keepalive_expiry,
                    )
                else:
                    self._connection = AsyncHTTP11Connection(
                        origin=self._remote_origin,
                        stream=stream,
                        keepalive_expiry=self._keepalive_expiry,
                    )

                self._connected = True
        return await self._connection.handle_async_request(request)

    def can_handle_request(self, origin: Origin) -> bool:
        return origin == self._remote_origin

    async def aclose(self) -> None:
        await self._connection.aclose()

    def info(self) -> str:
        return self._connection.info()

    def is_available(self) -> bool:
        return self._connection.is_available()

    def has_expired(self) -> bool:
        return self._connection.has_expired()

    def is_idle(self) -> bool:
        return self._connection.is_idle()

    def is_closed(self) -> bool:
        return self._connection.is_closed()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} [{self.info()}]>"

# === NexusCore/openenv\Lib\site-packages\httpcore\_sync\http_proxy.py ===
from __future__ import annotations

import base64
import logging
import ssl
import typing

from .._backends.base import SOCKET_OPTION, NetworkBackend
from .._exceptions import ProxyError
from .._models import (
    URL,
    Origin,
    Request,
    Response,
    enforce_bytes,
    enforce_headers,
    enforce_url,
)
from .._ssl import default_ssl_context
from .._synchronization import Lock
from .._trace import Trace
from .connection import HTTPConnection
from .connection_pool import ConnectionPool
from .http11 import HTTP11Connection
from .interfaces import ConnectionInterface

ByteOrStr = typing.Union[bytes, str]
HeadersAsSequence = typing.Sequence[typing.Tuple[ByteOrStr, ByteOrStr]]
HeadersAsMapping = typing.Mapping[ByteOrStr, ByteOrStr]


logger = logging.getLogger("httpcore.proxy")


def merge_headers(
    default_headers: typing.Sequence[tuple[bytes, bytes]] | None = None,
    override_headers: typing.Sequence[tuple[bytes, bytes]] | None = None,
) -> list[tuple[bytes, bytes]]:
    """
    Append default_headers and override_headers, de-duplicating if a key exists
    in both cases.
    """
    default_headers = [] if default_headers is None else list(default_headers)
    override_headers = [] if override_headers is None else list(override_headers)
    has_override = set(key.lower() for key, value in override_headers)
    default_headers = [
        (key, value)
        for key, value in default_headers
        if key.lower() not in has_override
    ]
    return default_headers + override_headers


class HTTPProxy(ConnectionPool):  # pragma: nocover
    """
    A connection pool that sends requests via an HTTP proxy.
    """

    def __init__(
        self,
        proxy_url: URL | bytes | str,
        proxy_auth: tuple[bytes | str, bytes | str] | None = None,
        proxy_headers: HeadersAsMapping | HeadersAsSequence | None = None,
        ssl_context: ssl.SSLContext | None = None,
        proxy_ssl_context: ssl.SSLContext | None = None,
        max_connections: int | None = 10,
        max_keepalive_connections: int | None = None,
        keepalive_expiry: float | None = None,
        http1: bool = True,
        http2: bool = False,
        retries: int = 0,
        local_address: str | None = None,
        uds: str | None = None,
        network_backend: NetworkBackend | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> None:
        """
        A connection pool for making HTTP requests.

        Parameters:
            proxy_url: The URL to use when connecting to the proxy server.
                For example `"http://127.0.0.1:8080/"`.
            proxy_auth: Any proxy authentication as a two-tuple of
                (username, password). May be either bytes or ascii-only str.
            proxy_headers: Any HTTP headers to use for the proxy requests.
                For example `{"Proxy-Authorization": "Basic <username>:<password>"}`.
            ssl_context: An SSL context to use for verifying connections.
                If not specified, the default `httpcore.default_ssl_context()`
                will be used.
            proxy_ssl_context: The same as `ssl_context`, but for a proxy server rather than a remote origin.
            max_connections: The maximum number of concurrent HTTP connections that
                the pool should allow. Any attempt to send a request on a pool that
                would exceed this amount will block until a connection is available.
            max_keepalive_connections: The maximum number of idle HTTP connections
                that will be maintained in the pool.
            keepalive_expiry: The duration in seconds that an idle HTTP connection
                may be maintained for before being expired from the pool.
            http1: A boolean indicating if HTTP/1.1 requests should be supported
                by the connection pool. Defaults to True.
            http2: A boolean indicating if HTTP/2 requests should be supported by
                the connection pool. Defaults to False.
            retries: The maximum number of retries when trying to establish
                a connection.
            local_address: Local address to connect from. Can also be used to
                connect using a particular address family. Using
                `local_address="0.0.0.0"` will connect using an `AF_INET` address
                (IPv4), while using `local_address="::"` will connect using an
                `AF_INET6` address (IPv6).
            uds: Path to a Unix Domain Socket to use instead of TCP sockets.
            network_backend: A backend instance to use for handling network I/O.
        """
        super().__init__(
            ssl_context=ssl_context,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            http1=http1,
            http2=http2,
            network_backend=network_backend,
            retries=retries,
            local_address=local_address,
            uds=uds,
            socket_options=socket_options,
        )

        self._proxy_url = enforce_url(proxy_url, name="proxy_url")
        if (
            self._proxy_url.scheme == b"http" and proxy_ssl_context is not None
        ):  # pragma: no cover
            raise RuntimeError(
                "The `proxy_ssl_context` argument is not allowed for the http scheme"
            )

        self._ssl_context = ssl_context
        self._proxy_ssl_context = proxy_ssl_context
        self._proxy_headers = enforce_headers(proxy_headers, name="proxy_headers")
        if proxy_auth is not None:
            username = enforce_bytes(proxy_auth[0], name="proxy_auth")
            password = enforce_bytes(proxy_auth[1], name="proxy_auth")
            userpass = username + b":" + password
            authorization = b"Basic " + base64.b64encode(userpass)
            self._proxy_headers = [
                (b"Proxy-Authorization", authorization)
            ] + self._proxy_headers

    def create_connection(self, origin: Origin) -> ConnectionInterface:
        if origin.scheme == b"http":
            return ForwardHTTPConnection(
                proxy_origin=self._proxy_url.origin,
                proxy_headers=self._proxy_headers,
                remote_origin=origin,
                keepalive_expiry=self._keepalive_expiry,
                network_backend=self._network_backend,
                proxy_ssl_context=self._proxy_ssl_context,
            )
        return TunnelHTTPConnection(
            proxy_origin=self._proxy_url.origin,
            proxy_headers=self._proxy_headers,
            remote_origin=origin,
            ssl_context=self._ssl_context,
            proxy_ssl_context=self._proxy_ssl_context,
            keepalive_expiry=self._keepalive_expiry,
            http1=self._http1,
            http2=self._http2,
            network_backend=self._network_backend,
        )


class ForwardHTTPConnection(ConnectionInterface):
    def __init__(
        self,
        proxy_origin: Origin,
        remote_origin: Origin,
        proxy_headers: HeadersAsMapping | HeadersAsSequence | None = None,
        keepalive_expiry: float | None = None,
        network_backend: NetworkBackend | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
        proxy_ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self._connection = HTTPConnection(
            origin=proxy_origin,
            keepalive_expiry=keepalive_expiry,
            network_backend=network_backend,
            socket_options=socket_options,
            ssl_context=proxy_ssl_context,
        )
        self._proxy_origin = proxy_origin
        self._proxy_headers = enforce_headers(proxy_headers, name="proxy_headers")
        self._remote_origin = remote_origin

    def handle_request(self, request: Request) -> Response:
        headers = merge_headers(self._proxy_headers, request.headers)
        url = URL(
            scheme=self._proxy_origin.scheme,
            host=self._proxy_origin.host,
            port=self._proxy_origin.port,
            target=bytes(request.url),
        )
        proxy_request = Request(
            method=request.method,
            url=url,
            headers=headers,
            content=request.stream,
            extensions=request.extensions,
        )
        return self._connection.handle_request(proxy_request)

    def can_handle_request(self, origin: Origin) -> bool:
        return origin == self._remote_origin

    def close(self) -> None:
        self._connection.close()

    def info(self) -> str:
        return self._connection.info()

    def is_available(self) -> bool:
        return self._connection.is_available()

    def has_expired(self) -> bool:
        return self._connection.has_expired()

    def is_idle(self) -> bool:
        return self._connection.is_idle()

    def is_closed(self) -> bool:
        return self._connection.is_closed()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} [{self.info()}]>"


class TunnelHTTPConnection(ConnectionInterface):
    def __init__(
        self,
        proxy_origin: Origin,
        remote_origin: Origin,
        ssl_context: ssl.SSLContext | None = None,
        proxy_ssl_context: ssl.SSLContext | None = None,
        proxy_headers: typing.Sequence[tuple[bytes, bytes]] | None = None,
        keepalive_expiry: float | None = None,
        http1: bool = True,
        http2: bool = False,
        network_backend: NetworkBackend | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> None:
        self._connection: ConnectionInterface = HTTPConnection(
            origin=proxy_origin,
            keepalive_expiry=keepalive_expiry,
            network_backend=network_backend,
            socket_options=socket_options,
            ssl_context=proxy_ssl_context,
        )
        self._proxy_origin = proxy_origin
        self._remote_origin = remote_origin
        self._ssl_context = ssl_context
        self._proxy_ssl_context = proxy_ssl_context
        self._proxy_headers = enforce_headers(proxy_headers, name="proxy_headers")
        self._keepalive_expiry = keepalive_expiry
        self._http1 = http1
        self._http2 = http2
        self._connect_lock = Lock()
        self._connected = False

    def handle_request(self, request: Request) -> Response:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("connect", None)

        with self._connect_lock:
            if not self._connected:
                target = b"%b:%d" % (self._remote_origin.host, self._remote_origin.port)

                connect_url = URL(
                    scheme=self._proxy_origin.scheme,
                    host=self._proxy_origin.host,
                    port=self._proxy_origin.port,
                    target=target,
                )
                connect_headers = merge_headers(
                    [(b"Host", target), (b"Accept", b"*/*")], self._proxy_headers
                )
                connect_request = Request(
                    method=b"CONNECT",
                    url=connect_url,
                    headers=connect_headers,
                    extensions=request.extensions,
                )
                connect_response = self._connection.handle_request(
                    connect_request
                )

                if connect_response.status < 200 or connect_response.status > 299:
                    reason_bytes = connect_response.extensions.get("reason_phrase", b"")
                    reason_str = reason_bytes.decode("ascii", errors="ignore")
                    msg = "%d %s" % (connect_response.status, reason_str)
                    self._connection.close()
                    raise ProxyError(msg)

                stream = connect_response.extensions["network_stream"]

                # Upgrade the stream to SSL
                ssl_context = (
                    default_ssl_context()
                    if self._ssl_context is None
                    else self._ssl_context
                )
                alpn_protocols = ["http/1.1", "h2"] if self._http2 else ["http/1.1"]
                ssl_context.set_alpn_protocols(alpn_protocols)

                kwargs = {
                    "ssl_context": ssl_context,
                    "server_hostname": self._remote_origin.host.decode("ascii"),
                    "timeout": timeout,
                }
                with Trace("start_tls", logger, request, kwargs) as trace:
                    stream = stream.start_tls(**kwargs)
                    trace.return_value = stream

                # Determine if we should be using HTTP/1.1 or HTTP/2
                ssl_object = stream.get_extra_info("ssl_object")
                http2_negotiated = (
                    ssl_object is not None
                    and ssl_object.selected_alpn_protocol() == "h2"
                )

                # Create the HTTP/1.1 or HTTP/2 connection
                if http2_negotiated or (self._http2 and not self._http1):
                    from .http2 import HTTP2Connection

                    self._connection = HTTP2Connection(
                        origin=self._remote_origin,
                        stream=stream,
                        keepalive_expiry=self._keepalive_expiry,
                    )
                else:
                    self._connection = HTTP11Connection(
                        origin=self._remote_origin,
                        stream=stream,
                        keepalive_expiry=self._keepalive_expiry,
                    )

                self._connected = True
        return self._connection.handle_request(request)

    def can_handle_request(self, origin: Origin) -> bool:
        return origin == self._remote_origin

    def close(self) -> None:
        self._connection.close()

    def info(self) -> str:
        return self._connection.info()

    def is_available(self) -> bool:
        return self._connection.is_available()

    def has_expired(self) -> bool:
        return self._connection.has_expired()

    def is_idle(self) -> bool:
        return self._connection.is_idle()

    def is_closed(self) -> bool:
        return self._connection.is_closed()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} [{self.info()}]>"

# === NexusCore/openenv\Lib\site-packages\openai\resources\audio\translations.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Union, Mapping, cast
from typing_extensions import Literal, overload, assert_never

import httpx

from ... import _legacy_response
from ..._types import NOT_GIVEN, Body, Query, Headers, NotGiven, FileTypes
from ..._utils import extract_files, maybe_transform, deepcopy_minimal, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...types.audio import translation_create_params
from ..._base_client import make_request_options
from ...types.audio_model import AudioModel
from ...types.audio.translation import Translation
from ...types.audio_response_format import AudioResponseFormat
from ...types.audio.translation_verbose import TranslationVerbose

__all__ = ["Translations", "AsyncTranslations"]

log: logging.Logger = logging.getLogger("openai.audio.transcriptions")


class Translations(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> TranslationsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return TranslationsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> TranslationsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return TranslationsWithStreamingResponse(self)

    @overload
    def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        response_format: Union[Literal["json"], NotGiven] = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Translation: ...

    @overload
    def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        response_format: Literal["verbose_json"],
        prompt: str | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> TranslationVerbose: ...

    @overload
    def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        response_format: Literal["text", "srt", "vtt"],
        prompt: str | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> str: ...

    def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        prompt: str | NotGiven = NOT_GIVEN,
        response_format: Union[Literal["json", "text", "srt", "verbose_json", "vtt"], NotGiven] = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Translation | TranslationVerbose | str:
        """
        Translates audio into English.

        Args:
          file: The audio file object (not file name) translate, in one of these formats: flac,
              mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.

          model: ID of the model to use. Only `whisper-1` (which is powered by our open source
              Whisper V2 model) is currently available.

          prompt: An optional text to guide the model's style or continue a previous audio
              segment. The
              [prompt](https://platform.openai.com/docs/guides/speech-to-text#prompting)
              should be in English.

          response_format: The format of the output, in one of these options: `json`, `text`, `srt`,
              `verbose_json`, or `vtt`.

          temperature: The sampling temperature, between 0 and 1. Higher values like 0.8 will make the
              output more random, while lower values like 0.2 will make it more focused and
              deterministic. If set to 0, the model will use
              [log probability](https://en.wikipedia.org/wiki/Log_probability) to
              automatically increase the temperature until certain thresholds are hit.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "file": file,
                "model": model,
                "prompt": prompt,
                "response_format": response_format,
                "temperature": temperature,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return self._post(  # type: ignore[return-value]
            "/audio/translations",
            body=maybe_transform(body, translation_create_params.TranslationCreateParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=_get_response_format_type(response_format),
        )


class AsyncTranslations(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncTranslationsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncTranslationsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncTranslationsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncTranslationsWithStreamingResponse(self)

    @overload
    async def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        response_format: Union[Literal["json"], NotGiven] = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Translation: ...

    @overload
    async def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        response_format: Literal["verbose_json"],
        prompt: str | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> TranslationVerbose: ...

    @overload
    async def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        response_format: Literal["text", "srt", "vtt"],
        prompt: str | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> str: ...

    async def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        prompt: str | NotGiven = NOT_GIVEN,
        response_format: Union[AudioResponseFormat, NotGiven] = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Translation | TranslationVerbose | str:
        """
        Translates audio into English.

        Args:
          file: The audio file object (not file name) translate, in one of these formats: flac,
              mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.

          model: ID of the model to use. Only `whisper-1` (which is powered by our open source
              Whisper V2 model) is currently available.

          prompt: An optional text to guide the model's style or continue a previous audio
              segment. The
              [prompt](https://platform.openai.com/docs/guides/speech-to-text#prompting)
              should be in English.

          response_format: The format of the output, in one of these options: `json`, `text`, `srt`,
              `verbose_json`, or `vtt`.

          temperature: The sampling temperature, between 0 and 1. Higher values like 0.8 will make the
              output more random, while lower values like 0.2 will make it more focused and
              deterministic. If set to 0, the model will use
              [log probability](https://en.wikipedia.org/wiki/Log_probability) to
              automatically increase the temperature until certain thresholds are hit.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "file": file,
                "model": model,
                "prompt": prompt,
                "response_format": response_format,
                "temperature": temperature,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return await self._post(
            "/audio/translations",
            body=await async_maybe_transform(body, translation_create_params.TranslationCreateParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=_get_response_format_type(response_format),
        )


class TranslationsWithRawResponse:
    def __init__(self, translations: Translations) -> None:
        self._translations = translations

        self.create = _legacy_response.to_raw_response_wrapper(
            translations.create,
        )


class AsyncTranslationsWithRawResponse:
    def __init__(self, translations: AsyncTranslations) -> None:
        self._translations = translations

        self.create = _legacy_response.async_to_raw_response_wrapper(
            translations.create,
        )


class TranslationsWithStreamingResponse:
    def __init__(self, translations: Translations) -> None:
        self._translations = translations

        self.create = to_streamed_response_wrapper(
            translations.create,
        )


class AsyncTranslationsWithStreamingResponse:
    def __init__(self, translations: AsyncTranslations) -> None:
        self._translations = translations

        self.create = async_to_streamed_response_wrapper(
            translations.create,
        )


def _get_response_format_type(
    response_format: Literal["json", "text", "srt", "verbose_json", "vtt"] | NotGiven,
) -> type[Translation | TranslationVerbose | str]:
    if isinstance(response_format, NotGiven) or response_format is None:  # pyright: ignore[reportUnnecessaryComparison]
        return Translation

    if response_format == "json":
        return Translation
    elif response_format == "verbose_json":
        return TranslationVerbose
    elif response_format == "srt" or response_format == "text" or response_format == "vtt":
        return str
    elif TYPE_CHECKING:  # type: ignore[unreachable]
        assert_never(response_format)
    else:
        log.warn("Unexpected audio response format: %s", response_format)
        return Transcription

# === NexusCore/openenv\Lib\site-packages\numpy\_core\_dtype.py ===
"""
A place for code to be called from the implementation of np.dtype

String handling is much easier to do correctly in python.
"""
import numpy as np

_kind_to_stem = {
    'u': 'uint',
    'i': 'int',
    'c': 'complex',
    'f': 'float',
    'b': 'bool',
    'V': 'void',
    'O': 'object',
    'M': 'datetime',
    'm': 'timedelta',
    'S': 'bytes',
    'U': 'str',
}


def _kind_name(dtype):
    try:
        return _kind_to_stem[dtype.kind]
    except KeyError as e:
        raise RuntimeError(
            f"internal dtype error, unknown kind {dtype.kind!r}"
        ) from None


def __str__(dtype):
    if dtype.fields is not None:
        return _struct_str(dtype, include_align=True)
    elif dtype.subdtype:
        return _subarray_str(dtype)
    elif issubclass(dtype.type, np.flexible) or not dtype.isnative:
        return dtype.str
    else:
        return dtype.name


def __repr__(dtype):
    arg_str = _construction_repr(dtype, include_align=False)
    if dtype.isalignedstruct:
        arg_str = arg_str + ", align=True"
    return f"dtype({arg_str})"


def _unpack_field(dtype, offset, title=None):
    """
    Helper function to normalize the items in dtype.fields.

    Call as:

    dtype, offset, title = _unpack_field(*dtype.fields[name])
    """
    return dtype, offset, title


def _isunsized(dtype):
    # PyDataType_ISUNSIZED
    return dtype.itemsize == 0


def _construction_repr(dtype, include_align=False, short=False):
    """
    Creates a string repr of the dtype, excluding the 'dtype()' part
    surrounding the object. This object may be a string, a list, or
    a dict depending on the nature of the dtype. This
    is the object passed as the first parameter to the dtype
    constructor, and if no additional constructor parameters are
    given, will reproduce the exact memory layout.

    Parameters
    ----------
    short : bool
        If true, this creates a shorter repr using 'kind' and 'itemsize',
        instead of the longer type name.

    include_align : bool
        If true, this includes the 'align=True' parameter
        inside the struct dtype construction dict when needed. Use this flag
        if you want a proper repr string without the 'dtype()' part around it.

        If false, this does not preserve the
        'align=True' parameter or sticky NPY_ALIGNED_STRUCT flag for
        struct arrays like the regular repr does, because the 'align'
        flag is not part of first dtype constructor parameter. This
        mode is intended for a full 'repr', where the 'align=True' is
        provided as the second parameter.
    """
    if dtype.fields is not None:
        return _struct_str(dtype, include_align=include_align)
    elif dtype.subdtype:
        return _subarray_str(dtype)
    else:
        return _scalar_str(dtype, short=short)


def _scalar_str(dtype, short):
    byteorder = _byte_order_str(dtype)

    if dtype.type == np.bool:
        if short:
            return "'?'"
        else:
            return "'bool'"

    elif dtype.type == np.object_:
        # The object reference may be different sizes on different
        # platforms, so it should never include the itemsize here.
        return "'O'"

    elif dtype.type == np.bytes_:
        if _isunsized(dtype):
            return "'S'"
        else:
            return "'S%d'" % dtype.itemsize

    elif dtype.type == np.str_:
        if _isunsized(dtype):
            return f"'{byteorder}U'"
        else:
            return "'%sU%d'" % (byteorder, dtype.itemsize / 4)

    elif dtype.type == str:
        return "'T'"

    elif not type(dtype)._legacy:
        return f"'{byteorder}{type(dtype).__name__}{dtype.itemsize * 8}'"

    # unlike the other types, subclasses of void are preserved - but
    # historically the repr does not actually reveal the subclass
    elif issubclass(dtype.type, np.void):
        if _isunsized(dtype):
            return "'V'"
        else:
            return "'V%d'" % dtype.itemsize

    elif dtype.type == np.datetime64:
        return f"'{byteorder}M8{_datetime_metadata_str(dtype)}'"

    elif dtype.type == np.timedelta64:
        return f"'{byteorder}m8{_datetime_metadata_str(dtype)}'"

    elif dtype.isbuiltin == 2:
        return dtype.type.__name__

    elif np.issubdtype(dtype, np.number):
        # Short repr with endianness, like '<f8'
        if short or dtype.byteorder not in ('=', '|'):
            return "'%s%c%d'" % (byteorder, dtype.kind, dtype.itemsize)

        # Longer repr, like 'float64'
        else:
            return "'%s%d'" % (_kind_name(dtype), 8 * dtype.itemsize)

    else:
        raise RuntimeError(
            "Internal error: NumPy dtype unrecognized type number")


def _byte_order_str(dtype):
    """ Normalize byteorder to '<' or '>' """
    # hack to obtain the native and swapped byte order characters
    swapped = np.dtype(int).newbyteorder('S')
    native = swapped.newbyteorder('S')

    byteorder = dtype.byteorder
    if byteorder == '=':
        return native.byteorder
    if byteorder == 'S':
        # TODO: this path can never be reached
        return swapped.byteorder
    elif byteorder == '|':
        return ''
    else:
        return byteorder


def _datetime_metadata_str(dtype):
    # TODO: this duplicates the C metastr_to_unicode functionality
    unit, count = np.datetime_data(dtype)
    if unit == 'generic':
        return ''
    elif count == 1:
        return f'[{unit}]'
    else:
        return f'[{count}{unit}]'


def _struct_dict_str(dtype, includealignedflag):
    # unpack the fields dictionary into ls
    names = dtype.names
    fld_dtypes = []
    offsets = []
    titles = []
    for name in names:
        fld_dtype, offset, title = _unpack_field(*dtype.fields[name])
        fld_dtypes.append(fld_dtype)
        offsets.append(offset)
        titles.append(title)

    # Build up a string to make the dictionary

    if np._core.arrayprint._get_legacy_print_mode() <= 121:
        colon = ":"
        fieldsep = ","
    else:
        colon = ": "
        fieldsep = ", "

    # First, the names
    ret = "{'names'%s[" % colon
    ret += fieldsep.join(repr(name) for name in names)

    # Second, the formats
    ret += f"], 'formats'{colon}["
    ret += fieldsep.join(
        _construction_repr(fld_dtype, short=True) for fld_dtype in fld_dtypes)

    # Third, the offsets
    ret += f"], 'offsets'{colon}["
    ret += fieldsep.join("%d" % offset for offset in offsets)

    # Fourth, the titles
    if any(title is not None for title in titles):
        ret += f"], 'titles'{colon}["
        ret += fieldsep.join(repr(title) for title in titles)

    # Fifth, the itemsize
    ret += "], 'itemsize'%s%d" % (colon, dtype.itemsize)

    if (includealignedflag and dtype.isalignedstruct):
        # Finally, the aligned flag
        ret += ", 'aligned'%sTrue}" % colon
    else:
        ret += "}"

    return ret


def _aligned_offset(offset, alignment):
    # round up offset:
    return - (-offset // alignment) * alignment


def _is_packed(dtype):
    """
    Checks whether the structured data type in 'dtype'
    has a simple layout, where all the fields are in order,
    and follow each other with no alignment padding.

    When this returns true, the dtype can be reconstructed
    from a list of the field names and dtypes with no additional
    dtype parameters.

    Duplicates the C `is_dtype_struct_simple_unaligned_layout` function.
    """
    align = dtype.isalignedstruct
    max_alignment = 1
    total_offset = 0
    for name in dtype.names:
        fld_dtype, fld_offset, title = _unpack_field(*dtype.fields[name])

        if align:
            total_offset = _aligned_offset(total_offset, fld_dtype.alignment)
            max_alignment = max(max_alignment, fld_dtype.alignment)

        if fld_offset != total_offset:
            return False
        total_offset += fld_dtype.itemsize

    if align:
        total_offset = _aligned_offset(total_offset, max_alignment)

    return total_offset == dtype.itemsize


def _struct_list_str(dtype):
    items = []
    for name in dtype.names:
        fld_dtype, fld_offset, title = _unpack_field(*dtype.fields[name])

        item = "("
        if title is not None:
            item += f"({title!r}, {name!r}), "
        else:
            item += f"{name!r}, "
        # Special case subarray handling here
        if fld_dtype.subdtype is not None:
            base, shape = fld_dtype.subdtype
            item += f"{_construction_repr(base, short=True)}, {shape}"
        else:
            item += _construction_repr(fld_dtype, short=True)

        item += ")"
        items.append(item)

    return "[" + ", ".join(items) + "]"


def _struct_str(dtype, include_align):
    # The list str representation can't include the 'align=' flag,
    # so if it is requested and the struct has the aligned flag set,
    # we must use the dict str instead.
    if not (include_align and dtype.isalignedstruct) and _is_packed(dtype):
        sub = _struct_list_str(dtype)

    else:
        sub = _struct_dict_str(dtype, include_align)

    # If the data type isn't the default, void, show it
    if dtype.type != np.void:
        return f"({dtype.type.__module__}.{dtype.type.__name__}, {sub})"
    else:
        return sub


def _subarray_str(dtype):
    base, shape = dtype.subdtype
    return f"({_construction_repr(base, short=True)}, {shape})"


def _name_includes_bit_suffix(dtype):
    if dtype.type == np.object_:
        # pointer size varies by system, best to omit it
        return False
    elif dtype.type == np.bool:
        # implied
        return False
    elif dtype.type is None:
        return True
    elif np.issubdtype(dtype, np.flexible) and _isunsized(dtype):
        # unspecified
        return False
    else:
        return True


def _name_get(dtype):
    # provides dtype.name.__get__, documented as returning a "bit name"

    if dtype.isbuiltin == 2:
        # user dtypes don't promise to do anything special
        return dtype.type.__name__

    if not type(dtype)._legacy:
        name = type(dtype).__name__

    elif issubclass(dtype.type, np.void):
        # historically, void subclasses preserve their name, eg `record64`
        name = dtype.type.__name__
    else:
        name = _kind_name(dtype)

    # append bit counts
    if _name_includes_bit_suffix(dtype):
        name += f"{dtype.itemsize * 8}"

    # append metadata to datetimes
    if dtype.type in (np.datetime64, np.timedelta64):
        name += _datetime_metadata_str(dtype)

    return name

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\modeling.py ===
"""
    pygments.lexers.modeling
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for modeling languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, using, default
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

from pygments.lexers.html import HtmlLexer
from pygments.lexers import _stan_builtins

__all__ = ['ModelicaLexer', 'BugsLexer', 'JagsLexer', 'StanLexer']


class ModelicaLexer(RegexLexer):
    """
    For Modelica source code.
    """
    name = 'Modelica'
    url = 'http://www.modelica.org/'
    aliases = ['modelica']
    filenames = ['*.mo']
    mimetypes = ['text/x-modelica']
    version_added = '1.1'

    flags = re.DOTALL | re.MULTILINE

    _name = r"(?:'(?:[^\\']|\\.)+'|[a-zA-Z_]\w*)"

    tokens = {
        'whitespace': [
            (r'[\s\ufeff]+', Text),
            (r'//[^\n]*\n?', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline)
        ],
        'root': [
            include('whitespace'),
            (r'"', String.Double, 'string'),
            (r'[()\[\]{},;]+', Punctuation),
            (r'\.?[*^/+-]|\.|<>|[<>:=]=?', Operator),
            (r'\d+(\.?\d*[eE][-+]?\d+|\.\d*)', Number.Float),
            (r'\d+', Number.Integer),
            (r'(abs|acos|actualStream|array|asin|assert|AssertionLevel|atan|'
             r'atan2|backSample|Boolean|cardinality|cat|ceil|change|Clock|'
             r'Connections|cos|cosh|cross|delay|diagonal|div|edge|exp|'
             r'ExternalObject|fill|floor|getInstanceName|hold|homotopy|'
             r'identity|inStream|integer|Integer|interval|inverse|isPresent|'
             r'linspace|log|log10|matrix|max|min|mod|ndims|noClock|noEvent|'
             r'ones|outerProduct|pre|previous|product|Real|reinit|rem|rooted|'
             r'sample|scalar|semiLinear|shiftSample|sign|sin|sinh|size|skew|'
             r'smooth|spatialDistribution|sqrt|StateSelect|String|subSample|'
             r'sum|superSample|symmetric|tan|tanh|terminal|terminate|time|'
             r'transpose|vector|zeros)\b', Name.Builtin),
            (r'(algorithm|annotation|break|connect|constant|constrainedby|der|'
             r'discrete|each|else|elseif|elsewhen|encapsulated|enumeration|'
             r'equation|exit|expandable|extends|external|firstTick|final|flow|for|if|'
             r'import|impure|in|initial|inner|input|interval|loop|nondiscrete|outer|'
             r'output|parameter|partial|protected|public|pure|redeclare|'
             r'replaceable|return|stream|then|when|while)\b',
             Keyword.Reserved),
            (r'(and|not|or)\b', Operator.Word),
            (r'(block|class|connector|end|function|model|operator|package|'
             r'record|type)\b', Keyword.Reserved, 'class'),
            (r'(false|true)\b', Keyword.Constant),
            (r'within\b', Keyword.Reserved, 'package-prefix'),
            (_name, Name)
        ],
        'class': [
            include('whitespace'),
            (r'(function|record)\b', Keyword.Reserved),
            (r'(if|for|when|while)\b', Keyword.Reserved, '#pop'),
            (_name, Name.Class, '#pop'),
            default('#pop')
        ],
        'package-prefix': [
            include('whitespace'),
            (_name, Name.Namespace, '#pop'),
            default('#pop')
        ],
        'string': [
            (r'"', String.Double, '#pop'),
            (r'\\[\'"?\\abfnrtv]', String.Escape),
            (r'(?i)<\s*html\s*>([^\\"]|\\.)+?(<\s*/\s*html\s*>|(?="))',
             using(HtmlLexer)),
            (r'<|\\?[^"\\<]+', String.Double)
        ]
    }


class BugsLexer(RegexLexer):
    """
    Pygments Lexer for OpenBugs and WinBugs
    models.
    """

    name = 'BUGS'
    aliases = ['bugs', 'winbugs', 'openbugs']
    filenames = ['*.bug']
    url = 'https://www.mrc-bsu.cam.ac.uk/software/bugs/openbugs'
    version_added = '1.6'

    _FUNCTIONS = (
        # Scalar functions
        'abs', 'arccos', 'arccosh', 'arcsin', 'arcsinh', 'arctan', 'arctanh',
        'cloglog', 'cos', 'cosh', 'cumulative', 'cut', 'density', 'deviance',
        'equals', 'expr', 'gammap', 'ilogit', 'icloglog', 'integral', 'log',
        'logfact', 'loggam', 'logit', 'max', 'min', 'phi', 'post.p.value',
        'pow', 'prior.p.value', 'probit', 'replicate.post', 'replicate.prior',
        'round', 'sin', 'sinh', 'solution', 'sqrt', 'step', 'tan', 'tanh',
        'trunc',
        # Vector functions
        'inprod', 'interp.lin', 'inverse', 'logdet', 'mean', 'eigen.vals',
        'ode', 'prod', 'p.valueM', 'rank', 'ranked', 'replicate.postM',
        'sd', 'sort', 'sum',
        # Special
        'D', 'I', 'F', 'T', 'C')
    """ OpenBUGS built-in functions

    From http://www.openbugs.info/Manuals/ModelSpecification.html#ContentsAII

    This also includes

    - T, C, I : Truncation and censoring.
      ``T`` and ``C`` are in OpenBUGS. ``I`` in WinBUGS.
    - D : ODE
    - F : Functional http://www.openbugs.info/Examples/Functionals.html

    """

    _DISTRIBUTIONS = ('dbern', 'dbin', 'dcat', 'dnegbin', 'dpois',
                      'dhyper', 'dbeta', 'dchisqr', 'ddexp', 'dexp',
                      'dflat', 'dgamma', 'dgev', 'df', 'dggamma', 'dgpar',
                      'dloglik', 'dlnorm', 'dlogis', 'dnorm', 'dpar',
                      'dt', 'dunif', 'dweib', 'dmulti', 'ddirch', 'dmnorm',
                      'dmt', 'dwish')
    """ OpenBUGS built-in distributions

    Functions from
    http://www.openbugs.info/Manuals/ModelSpecification.html#ContentsAI
    """

    tokens = {
        'whitespace': [
            (r"\s+", Text),
        ],
        'comments': [
            # Comments
            (r'#.*$', Comment.Single),
        ],
        'root': [
            # Comments
            include('comments'),
            include('whitespace'),
            # Block start
            (r'(model)(\s+)(\{)',
             bygroups(Keyword.Namespace, Text, Punctuation)),
            # Reserved Words
            (r'(for|in)(?![\w.])', Keyword.Reserved),
            # Built-in Functions
            (r'({})(?=\s*\()'.format(r'|'.join(_FUNCTIONS + _DISTRIBUTIONS)),
             Name.Builtin),
            # Regular variable names
            (r'[A-Za-z][\w.]*', Name),
            # Number Literals
            (r'[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?', Number),
            # Punctuation
            (r'\[|\]|\(|\)|:|,|;', Punctuation),
            # Assignment operators
            # SLexer makes these tokens Operators.
            (r'<-|~', Operator),
            # Infix and prefix operators
            (r'\+|-|\*|/', Operator),
            # Block
            (r'[{}]', Punctuation),
        ]
    }

    def analyse_text(text):
        if re.search(r"^\s*model\s*{", text, re.M):
            return 0.7
        else:
            return 0.0


class JagsLexer(RegexLexer):
    """
    Pygments Lexer for JAGS.
    """

    name = 'JAGS'
    aliases = ['jags']
    filenames = ['*.jag', '*.bug']
    url = 'https://mcmc-jags.sourceforge.io'
    version_added = '1.6'

    # JAGS
    _FUNCTIONS = (
        'abs', 'arccos', 'arccosh', 'arcsin', 'arcsinh', 'arctan', 'arctanh',
        'cos', 'cosh', 'cloglog',
        'equals', 'exp', 'icloglog', 'ifelse', 'ilogit', 'log', 'logfact',
        'loggam', 'logit', 'phi', 'pow', 'probit', 'round', 'sin', 'sinh',
        'sqrt', 'step', 'tan', 'tanh', 'trunc', 'inprod', 'interp.lin',
        'logdet', 'max', 'mean', 'min', 'prod', 'sum', 'sd', 'inverse',
        'rank', 'sort', 't', 'acos', 'acosh', 'asin', 'asinh', 'atan',
        # Truncation/Censoring (should I include)
        'T', 'I')
    # Distributions with density, probability and quartile functions
    _DISTRIBUTIONS = tuple(f'[dpq]{x}' for x in
                           ('bern', 'beta', 'dchiqsqr', 'ddexp', 'dexp',
                            'df', 'gamma', 'gen.gamma', 'logis', 'lnorm',
                            'negbin', 'nchisqr', 'norm', 'par', 'pois', 'weib'))
    # Other distributions without density and probability
    _OTHER_DISTRIBUTIONS = (
        'dt', 'dunif', 'dbetabin', 'dbern', 'dbin', 'dcat', 'dhyper',
        'ddirch', 'dmnorm', 'dwish', 'dmt', 'dmulti', 'dbinom', 'dchisq',
        'dnbinom', 'dweibull', 'ddirich')

    tokens = {
        'whitespace': [
            (r"\s+", Text),
        ],
        'names': [
            # Regular variable names
            (r'[a-zA-Z][\w.]*\b', Name),
        ],
        'comments': [
            # do not use stateful comments
            (r'(?s)/\*.*?\*/', Comment.Multiline),
            # Comments
            (r'#.*$', Comment.Single),
        ],
        'root': [
            # Comments
            include('comments'),
            include('whitespace'),
            # Block start
            (r'(model|data)(\s+)(\{)',
             bygroups(Keyword.Namespace, Text, Punctuation)),
            (r'var(?![\w.])', Keyword.Declaration),
            # Reserved Words
            (r'(for|in)(?![\w.])', Keyword.Reserved),
            # Builtins
            # Need to use lookahead because . is a valid char
            (r'({})(?=\s*\()'.format(r'|'.join(_FUNCTIONS
                                          + _DISTRIBUTIONS
                                          + _OTHER_DISTRIBUTIONS)),
             Name.Builtin),
            # Names
            include('names'),
            # Number Literals
            (r'[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?', Number),
            (r'\[|\]|\(|\)|:|,|;', Punctuation),
            # Assignment operators
            (r'<-|~', Operator),
            # # JAGS includes many more than OpenBUGS
            (r'\+|-|\*|\/|\|\|[&]{2}|[<>=]=?|\^|%.*?%', Operator),
            (r'[{}]', Punctuation),
        ]
    }

    def analyse_text(text):
        if re.search(r'^\s*model\s*\{', text, re.M):
            if re.search(r'^\s*data\s*\{', text, re.M):
                return 0.9
            elif re.search(r'^\s*var', text, re.M):
                return 0.9
            else:
                return 0.3
        else:
            return 0


class StanLexer(RegexLexer):
    """Pygments Lexer for Stan models.

    The Stan modeling language is specified in the *Stan Modeling Language
    User's Guide and Reference Manual, v2.17.0*,
    `pdf <https://github.com/stan-dev/stan/releases/download/v2.17.0/stan-reference-2.17.0.pdf>`__.
    """

    name = 'Stan'
    aliases = ['stan']
    filenames = ['*.stan']
    url = 'https://mc-stan.org'
    version_added = '1.6'

    tokens = {
        'whitespace': [
            (r"\s+", Text),
        ],
        'comments': [
            (r'(?s)/\*.*?\*/', Comment.Multiline),
            # Comments
            (r'(//|#).*$', Comment.Single),
        ],
        'root': [
            (r'"[^"]*"', String),
            # Comments
            include('comments'),
            # block start
            include('whitespace'),
            # Block start
            (r'({})(\s*)(\{{)'.format(r'|'.join(('functions', 'data', r'transformed\s+?data',
                        'parameters', r'transformed\s+parameters',
                        'model', r'generated\s+quantities'))),
             bygroups(Keyword.Namespace, Text, Punctuation)),
            # target keyword
            (r'target\s*\+=', Keyword),
            # Reserved Words
            (r'({})\b'.format(r'|'.join(_stan_builtins.KEYWORDS)), Keyword),
            # Truncation
            (r'T(?=\s*\[)', Keyword),
            # Data types
            (r'({})\b'.format(r'|'.join(_stan_builtins.TYPES)), Keyword.Type),
             # < should be punctuation, but elsewhere I can't tell if it is in
             # a range constraint
            (r'(<)(\s*)(upper|lower|offset|multiplier)(\s*)(=)',
             bygroups(Operator, Whitespace, Keyword, Whitespace, Punctuation)),
            (r'(,)(\s*)(upper)(\s*)(=)',
             bygroups(Punctuation, Whitespace, Keyword, Whitespace, Punctuation)),
            # Punctuation
            (r"[;,\[\]()]", Punctuation),
            # Builtin
            (r'({})(?=\s*\()'.format('|'.join(_stan_builtins.FUNCTIONS)), Name.Builtin),
            (r'(~)(\s*)({})(?=\s*\()'.format('|'.join(_stan_builtins.DISTRIBUTIONS)),
                bygroups(Operator, Whitespace, Name.Builtin)),
            # Special names ending in __, like lp__
            (r'[A-Za-z]\w*__\b', Name.Builtin.Pseudo),
            (r'({})\b'.format(r'|'.join(_stan_builtins.RESERVED)), Keyword.Reserved),
            # user-defined functions
            (r'[A-Za-z]\w*(?=\s*\()]', Name.Function),
            # Imaginary Literals
            (r'[0-9]+(\.[0-9]*)?([eE][+-]?[0-9]+)?i', Number.Float),
            (r'\.[0-9]+([eE][+-]?[0-9]+)?i', Number.Float),
            (r'[0-9]+i', Number.Float),
            # Real Literals
            (r'[0-9]+(\.[0-9]*)?([eE][+-]?[0-9]+)?', Number.Float),
            (r'\.[0-9]+([eE][+-]?[0-9]+)?', Number.Float),
            # Integer Literals
            (r'[0-9]+', Number.Integer),
            # Regular variable names
            (r'[A-Za-z]\w*\b', Name),
            # Assignment operators
            (r'<-|(?:\+|-|\.?/|\.?\*|=)?=|~', Operator),
            # Infix, prefix and postfix operators (and = )
            (r"\+|-|\.?\*|\.?/|\\|'|\.?\^|!=?|<=?|>=?|\|\||&&|%|\?|:|%/%|!", Operator),
            # Block delimiters
            (r'[{}]', Punctuation),
            # Distribution |
            (r'\|', Punctuation)
        ]
    }

    def analyse_text(text):
        if re.search(r'^\s*parameters\s*\{', text, re.M):
            return 1.0
        else:
            return 0.0

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\system_info.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: SystemInfo (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

@dataclass
class GPUDevice:
    '''
    Describes a single graphics processor (GPU).
    '''
    #: PCI ID of the GPU vendor, if available; 0 otherwise.
    vendor_id: float

    #: PCI ID of the GPU device, if available; 0 otherwise.
    device_id: float

    #: String description of the GPU vendor, if the PCI ID is not available.
    vendor_string: str

    #: String description of the GPU device, if the PCI ID is not available.
    device_string: str

    #: String description of the GPU driver vendor.
    driver_vendor: str

    #: String description of the GPU driver version.
    driver_version: str

    #: Sub sys ID of the GPU, only available on Windows.
    sub_sys_id: typing.Optional[float] = None

    #: Revision of the GPU, only available on Windows.
    revision: typing.Optional[float] = None

    def to_json(self):
        json = dict()
        json['vendorId'] = self.vendor_id
        json['deviceId'] = self.device_id
        json['vendorString'] = self.vendor_string
        json['deviceString'] = self.device_string
        json['driverVendor'] = self.driver_vendor
        json['driverVersion'] = self.driver_version
        if self.sub_sys_id is not None:
            json['subSysId'] = self.sub_sys_id
        if self.revision is not None:
            json['revision'] = self.revision
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            vendor_id=float(json['vendorId']),
            device_id=float(json['deviceId']),
            vendor_string=str(json['vendorString']),
            device_string=str(json['deviceString']),
            driver_vendor=str(json['driverVendor']),
            driver_version=str(json['driverVersion']),
            sub_sys_id=float(json['subSysId']) if 'subSysId' in json else None,
            revision=float(json['revision']) if 'revision' in json else None,
        )


@dataclass
class Size:
    '''
    Describes the width and height dimensions of an entity.
    '''
    #: Width in pixels.
    width: int

    #: Height in pixels.
    height: int

    def to_json(self):
        json = dict()
        json['width'] = self.width
        json['height'] = self.height
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            width=int(json['width']),
            height=int(json['height']),
        )


@dataclass
class VideoDecodeAcceleratorCapability:
    '''
    Describes a supported video decoding profile with its associated minimum and
    maximum resolutions.
    '''
    #: Video codec profile that is supported, e.g. VP9 Profile 2.
    profile: str

    #: Maximum video dimensions in pixels supported for this ``profile``.
    max_resolution: Size

    #: Minimum video dimensions in pixels supported for this ``profile``.
    min_resolution: Size

    def to_json(self):
        json = dict()
        json['profile'] = self.profile
        json['maxResolution'] = self.max_resolution.to_json()
        json['minResolution'] = self.min_resolution.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            profile=str(json['profile']),
            max_resolution=Size.from_json(json['maxResolution']),
            min_resolution=Size.from_json(json['minResolution']),
        )


@dataclass
class VideoEncodeAcceleratorCapability:
    '''
    Describes a supported video encoding profile with its associated maximum
    resolution and maximum framerate.
    '''
    #: Video codec profile that is supported, e.g H264 Main.
    profile: str

    #: Maximum video dimensions in pixels supported for this ``profile``.
    max_resolution: Size

    #: Maximum encoding framerate in frames per second supported for this
    #: ``profile``, as fraction's numerator and denominator, e.g. 24/1 fps,
    #: 24000/1001 fps, etc.
    max_framerate_numerator: int

    max_framerate_denominator: int

    def to_json(self):
        json = dict()
        json['profile'] = self.profile
        json['maxResolution'] = self.max_resolution.to_json()
        json['maxFramerateNumerator'] = self.max_framerate_numerator
        json['maxFramerateDenominator'] = self.max_framerate_denominator
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            profile=str(json['profile']),
            max_resolution=Size.from_json(json['maxResolution']),
            max_framerate_numerator=int(json['maxFramerateNumerator']),
            max_framerate_denominator=int(json['maxFramerateDenominator']),
        )


class SubsamplingFormat(enum.Enum):
    '''
    YUV subsampling type of the pixels of a given image.
    '''
    YUV420 = "yuv420"
    YUV422 = "yuv422"
    YUV444 = "yuv444"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ImageType(enum.Enum):
    '''
    Image format of a given image.
    '''
    JPEG = "jpeg"
    WEBP = "webp"
    UNKNOWN = "unknown"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ImageDecodeAcceleratorCapability:
    '''
    Describes a supported image decoding profile with its associated minimum and
    maximum resolutions and subsampling.
    '''
    #: Image coded, e.g. Jpeg.
    image_type: ImageType

    #: Maximum supported dimensions of the image in pixels.
    max_dimensions: Size

    #: Minimum supported dimensions of the image in pixels.
    min_dimensions: Size

    #: Optional array of supported subsampling formats, e.g. 4:2:0, if known.
    subsamplings: typing.List[SubsamplingFormat]

    def to_json(self):
        json = dict()
        json['imageType'] = self.image_type.to_json()
        json['maxDimensions'] = self.max_dimensions.to_json()
        json['minDimensions'] = self.min_dimensions.to_json()
        json['subsamplings'] = [i.to_json() for i in self.subsamplings]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            image_type=ImageType.from_json(json['imageType']),
            max_dimensions=Size.from_json(json['maxDimensions']),
            min_dimensions=Size.from_json(json['minDimensions']),
            subsamplings=[SubsamplingFormat.from_json(i) for i in json['subsamplings']],
        )


@dataclass
class GPUInfo:
    '''
    Provides information about the GPU(s) on the system.
    '''
    #: The graphics devices on the system. Element 0 is the primary GPU.
    devices: typing.List[GPUDevice]

    #: An optional array of GPU driver bug workarounds.
    driver_bug_workarounds: typing.List[str]

    #: Supported accelerated video decoding capabilities.
    video_decoding: typing.List[VideoDecodeAcceleratorCapability]

    #: Supported accelerated video encoding capabilities.
    video_encoding: typing.List[VideoEncodeAcceleratorCapability]

    #: Supported accelerated image decoding capabilities.
    image_decoding: typing.List[ImageDecodeAcceleratorCapability]

    #: An optional dictionary of additional GPU related attributes.
    aux_attributes: typing.Optional[dict] = None

    #: An optional dictionary of graphics features and their status.
    feature_status: typing.Optional[dict] = None

    def to_json(self):
        json = dict()
        json['devices'] = [i.to_json() for i in self.devices]
        json['driverBugWorkarounds'] = [i for i in self.driver_bug_workarounds]
        json['videoDecoding'] = [i.to_json() for i in self.video_decoding]
        json['videoEncoding'] = [i.to_json() for i in self.video_encoding]
        json['imageDecoding'] = [i.to_json() for i in self.image_decoding]
        if self.aux_attributes is not None:
            json['auxAttributes'] = self.aux_attributes
        if self.feature_status is not None:
            json['featureStatus'] = self.feature_status
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            devices=[GPUDevice.from_json(i) for i in json['devices']],
            driver_bug_workarounds=[str(i) for i in json['driverBugWorkarounds']],
            video_decoding=[VideoDecodeAcceleratorCapability.from_json(i) for i in json['videoDecoding']],
            video_encoding=[VideoEncodeAcceleratorCapability.from_json(i) for i in json['videoEncoding']],
            image_decoding=[ImageDecodeAcceleratorCapability.from_json(i) for i in json['imageDecoding']],
            aux_attributes=dict(json['auxAttributes']) if 'auxAttributes' in json else None,
            feature_status=dict(json['featureStatus']) if 'featureStatus' in json else None,
        )


@dataclass
class ProcessInfo:
    '''
    Represents process info.
    '''
    #: Specifies process type.
    type_: str

    #: Specifies process id.
    id_: int

    #: Specifies cumulative CPU usage in seconds across all threads of the
    #: process since the process start.
    cpu_time: float

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['id'] = self.id_
        json['cpuTime'] = self.cpu_time
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            id_=int(json['id']),
            cpu_time=float(json['cpuTime']),
        )


def get_info() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[GPUInfo, str, str, str]]:
    '''
    Returns information about the system.

    :returns: A tuple with the following items:

        0. **gpu** - Information about the GPUs on the system.
        1. **modelName** - A platform-dependent description of the model of the machine. On Mac OS, this is, for example, 'MacBookPro'. Will be the empty string if not supported.
        2. **modelVersion** - A platform-dependent description of the version of the machine. On Mac OS, this is, for example, '10.1'. Will be the empty string if not supported.
        3. **commandLine** - The command line string used to launch the browser. Will be the empty string if not supported.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'SystemInfo.getInfo',
    }
    json = yield cmd_dict
    return (
        GPUInfo.from_json(json['gpu']),
        str(json['modelName']),
        str(json['modelVersion']),
        str(json['commandLine'])
    )


def get_feature_state(
        feature_state: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Returns information about the feature state.

    :param feature_state:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['featureState'] = feature_state
    cmd_dict: T_JSON_DICT = {
        'method': 'SystemInfo.getFeatureState',
        'params': params,
    }
    json = yield cmd_dict
    return bool(json['featureEnabled'])


def get_process_info() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[ProcessInfo]]:
    '''
    Returns information about all running processes.

    :returns: An array of process info blocks.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'SystemInfo.getProcessInfo',
    }
    json = yield cmd_dict
    return [ProcessInfo.from_json(i) for i in json['processInfo']]

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\system_info.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: SystemInfo (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

@dataclass
class GPUDevice:
    '''
    Describes a single graphics processor (GPU).
    '''
    #: PCI ID of the GPU vendor, if available; 0 otherwise.
    vendor_id: float

    #: PCI ID of the GPU device, if available; 0 otherwise.
    device_id: float

    #: String description of the GPU vendor, if the PCI ID is not available.
    vendor_string: str

    #: String description of the GPU device, if the PCI ID is not available.
    device_string: str

    #: String description of the GPU driver vendor.
    driver_vendor: str

    #: String description of the GPU driver version.
    driver_version: str

    #: Sub sys ID of the GPU, only available on Windows.
    sub_sys_id: typing.Optional[float] = None

    #: Revision of the GPU, only available on Windows.
    revision: typing.Optional[float] = None

    def to_json(self):
        json = dict()
        json['vendorId'] = self.vendor_id
        json['deviceId'] = self.device_id
        json['vendorString'] = self.vendor_string
        json['deviceString'] = self.device_string
        json['driverVendor'] = self.driver_vendor
        json['driverVersion'] = self.driver_version
        if self.sub_sys_id is not None:
            json['subSysId'] = self.sub_sys_id
        if self.revision is not None:
            json['revision'] = self.revision
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            vendor_id=float(json['vendorId']),
            device_id=float(json['deviceId']),
            vendor_string=str(json['vendorString']),
            device_string=str(json['deviceString']),
            driver_vendor=str(json['driverVendor']),
            driver_version=str(json['driverVersion']),
            sub_sys_id=float(json['subSysId']) if 'subSysId' in json else None,
            revision=float(json['revision']) if 'revision' in json else None,
        )


@dataclass
class Size:
    '''
    Describes the width and height dimensions of an entity.
    '''
    #: Width in pixels.
    width: int

    #: Height in pixels.
    height: int

    def to_json(self):
        json = dict()
        json['width'] = self.width
        json['height'] = self.height
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            width=int(json['width']),
            height=int(json['height']),
        )


@dataclass
class VideoDecodeAcceleratorCapability:
    '''
    Describes a supported video decoding profile with its associated minimum and
    maximum resolutions.
    '''
    #: Video codec profile that is supported, e.g. VP9 Profile 2.
    profile: str

    #: Maximum video dimensions in pixels supported for this ``profile``.
    max_resolution: Size

    #: Minimum video dimensions in pixels supported for this ``profile``.
    min_resolution: Size

    def to_json(self):
        json = dict()
        json['profile'] = self.profile
        json['maxResolution'] = self.max_resolution.to_json()
        json['minResolution'] = self.min_resolution.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            profile=str(json['profile']),
            max_resolution=Size.from_json(json['maxResolution']),
            min_resolution=Size.from_json(json['minResolution']),
        )


@dataclass
class VideoEncodeAcceleratorCapability:
    '''
    Describes a supported video encoding profile with its associated maximum
    resolution and maximum framerate.
    '''
    #: Video codec profile that is supported, e.g H264 Main.
    profile: str

    #: Maximum video dimensions in pixels supported for this ``profile``.
    max_resolution: Size

    #: Maximum encoding framerate in frames per second supported for this
    #: ``profile``, as fraction's numerator and denominator, e.g. 24/1 fps,
    #: 24000/1001 fps, etc.
    max_framerate_numerator: int

    max_framerate_denominator: int

    def to_json(self):
        json = dict()
        json['profile'] = self.profile
        json['maxResolution'] = self.max_resolution.to_json()
        json['maxFramerateNumerator'] = self.max_framerate_numerator
        json['maxFramerateDenominator'] = self.max_framerate_denominator
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            profile=str(json['profile']),
            max_resolution=Size.from_json(json['maxResolution']),
            max_framerate_numerator=int(json['maxFramerateNumerator']),
            max_framerate_denominator=int(json['maxFramerateDenominator']),
        )


class SubsamplingFormat(enum.Enum):
    '''
    YUV subsampling type of the pixels of a given image.
    '''
    YUV420 = "yuv420"
    YUV422 = "yuv422"
    YUV444 = "yuv444"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ImageType(enum.Enum):
    '''
    Image format of a given image.
    '''
    JPEG = "jpeg"
    WEBP = "webp"
    UNKNOWN = "unknown"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ImageDecodeAcceleratorCapability:
    '''
    Describes a supported image decoding profile with its associated minimum and
    maximum resolutions and subsampling.
    '''
    #: Image coded, e.g. Jpeg.
    image_type: ImageType

    #: Maximum supported dimensions of the image in pixels.
    max_dimensions: Size

    #: Minimum supported dimensions of the image in pixels.
    min_dimensions: Size

    #: Optional array of supported subsampling formats, e.g. 4:2:0, if known.
    subsamplings: typing.List[SubsamplingFormat]

    def to_json(self):
        json = dict()
        json['imageType'] = self.image_type.to_json()
        json['maxDimensions'] = self.max_dimensions.to_json()
        json['minDimensions'] = self.min_dimensions.to_json()
        json['subsamplings'] = [i.to_json() for i in self.subsamplings]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            image_type=ImageType.from_json(json['imageType']),
            max_dimensions=Size.from_json(json['maxDimensions']),
            min_dimensions=Size.from_json(json['minDimensions']),
            subsamplings=[SubsamplingFormat.from_json(i) for i in json['subsamplings']],
        )


@dataclass
class GPUInfo:
    '''
    Provides information about the GPU(s) on the system.
    '''
    #: The graphics devices on the system. Element 0 is the primary GPU.
    devices: typing.List[GPUDevice]

    #: An optional array of GPU driver bug workarounds.
    driver_bug_workarounds: typing.List[str]

    #: Supported accelerated video decoding capabilities.
    video_decoding: typing.List[VideoDecodeAcceleratorCapability]

    #: Supported accelerated video encoding capabilities.
    video_encoding: typing.List[VideoEncodeAcceleratorCapability]

    #: Supported accelerated image decoding capabilities.
    image_decoding: typing.List[ImageDecodeAcceleratorCapability]

    #: An optional dictionary of additional GPU related attributes.
    aux_attributes: typing.Optional[dict] = None

    #: An optional dictionary of graphics features and their status.
    feature_status: typing.Optional[dict] = None

    def to_json(self):
        json = dict()
        json['devices'] = [i.to_json() for i in self.devices]
        json['driverBugWorkarounds'] = [i for i in self.driver_bug_workarounds]
        json['videoDecoding'] = [i.to_json() for i in self.video_decoding]
        json['videoEncoding'] = [i.to_json() for i in self.video_encoding]
        json['imageDecoding'] = [i.to_json() for i in self.image_decoding]
        if self.aux_attributes is not None:
            json['auxAttributes'] = self.aux_attributes
        if self.feature_status is not None:
            json['featureStatus'] = self.feature_status
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            devices=[GPUDevice.from_json(i) for i in json['devices']],
            driver_bug_workarounds=[str(i) for i in json['driverBugWorkarounds']],
            video_decoding=[VideoDecodeAcceleratorCapability.from_json(i) for i in json['videoDecoding']],
            video_encoding=[VideoEncodeAcceleratorCapability.from_json(i) for i in json['videoEncoding']],
            image_decoding=[ImageDecodeAcceleratorCapability.from_json(i) for i in json['imageDecoding']],
            aux_attributes=dict(json['auxAttributes']) if 'auxAttributes' in json else None,
            feature_status=dict(json['featureStatus']) if 'featureStatus' in json else None,
        )


@dataclass
class ProcessInfo:
    '''
    Represents process info.
    '''
    #: Specifies process type.
    type_: str

    #: Specifies process id.
    id_: int

    #: Specifies cumulative CPU usage in seconds across all threads of the
    #: process since the process start.
    cpu_time: float

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['id'] = self.id_
        json['cpuTime'] = self.cpu_time
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            id_=int(json['id']),
            cpu_time=float(json['cpuTime']),
        )


def get_info() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[GPUInfo, str, str, str]]:
    '''
    Returns information about the system.

    :returns: A tuple with the following items:

        0. **gpu** - Information about the GPUs on the system.
        1. **modelName** - A platform-dependent description of the model of the machine. On Mac OS, this is, for example, 'MacBookPro'. Will be the empty string if not supported.
        2. **modelVersion** - A platform-dependent description of the version of the machine. On Mac OS, this is, for example, '10.1'. Will be the empty string if not supported.
        3. **commandLine** - The command line string used to launch the browser. Will be the empty string if not supported.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'SystemInfo.getInfo',
    }
    json = yield cmd_dict
    return (
        GPUInfo.from_json(json['gpu']),
        str(json['modelName']),
        str(json['modelVersion']),
        str(json['commandLine'])
    )


def get_feature_state(
        feature_state: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Returns information about the feature state.

    :param feature_state:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['featureState'] = feature_state
    cmd_dict: T_JSON_DICT = {
        'method': 'SystemInfo.getFeatureState',
        'params': params,
    }
    json = yield cmd_dict
    return bool(json['featureEnabled'])


def get_process_info() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[ProcessInfo]]:
    '''
    Returns information about all running processes.

    :returns: An array of process info blocks.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'SystemInfo.getProcessInfo',
    }
    json = yield cmd_dict
    return [ProcessInfo.from_json(i) for i in json['processInfo']]

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\system_info.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: SystemInfo (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

@dataclass
class GPUDevice:
    '''
    Describes a single graphics processor (GPU).
    '''
    #: PCI ID of the GPU vendor, if available; 0 otherwise.
    vendor_id: float

    #: PCI ID of the GPU device, if available; 0 otherwise.
    device_id: float

    #: String description of the GPU vendor, if the PCI ID is not available.
    vendor_string: str

    #: String description of the GPU device, if the PCI ID is not available.
    device_string: str

    #: String description of the GPU driver vendor.
    driver_vendor: str

    #: String description of the GPU driver version.
    driver_version: str

    #: Sub sys ID of the GPU, only available on Windows.
    sub_sys_id: typing.Optional[float] = None

    #: Revision of the GPU, only available on Windows.
    revision: typing.Optional[float] = None

    def to_json(self):
        json = dict()
        json['vendorId'] = self.vendor_id
        json['deviceId'] = self.device_id
        json['vendorString'] = self.vendor_string
        json['deviceString'] = self.device_string
        json['driverVendor'] = self.driver_vendor
        json['driverVersion'] = self.driver_version
        if self.sub_sys_id is not None:
            json['subSysId'] = self.sub_sys_id
        if self.revision is not None:
            json['revision'] = self.revision
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            vendor_id=float(json['vendorId']),
            device_id=float(json['deviceId']),
            vendor_string=str(json['vendorString']),
            device_string=str(json['deviceString']),
            driver_vendor=str(json['driverVendor']),
            driver_version=str(json['driverVersion']),
            sub_sys_id=float(json['subSysId']) if 'subSysId' in json else None,
            revision=float(json['revision']) if 'revision' in json else None,
        )


@dataclass
class Size:
    '''
    Describes the width and height dimensions of an entity.
    '''
    #: Width in pixels.
    width: int

    #: Height in pixels.
    height: int

    def to_json(self):
        json = dict()
        json['width'] = self.width
        json['height'] = self.height
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            width=int(json['width']),
            height=int(json['height']),
        )


@dataclass
class VideoDecodeAcceleratorCapability:
    '''
    Describes a supported video decoding profile with its associated minimum and
    maximum resolutions.
    '''
    #: Video codec profile that is supported, e.g. VP9 Profile 2.
    profile: str

    #: Maximum video dimensions in pixels supported for this ``profile``.
    max_resolution: Size

    #: Minimum video dimensions in pixels supported for this ``profile``.
    min_resolution: Size

    def to_json(self):
        json = dict()
        json['profile'] = self.profile
        json['maxResolution'] = self.max_resolution.to_json()
        json['minResolution'] = self.min_resolution.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            profile=str(json['profile']),
            max_resolution=Size.from_json(json['maxResolution']),
            min_resolution=Size.from_json(json['minResolution']),
        )


@dataclass
class VideoEncodeAcceleratorCapability:
    '''
    Describes a supported video encoding profile with its associated maximum
    resolution and maximum framerate.
    '''
    #: Video codec profile that is supported, e.g H264 Main.
    profile: str

    #: Maximum video dimensions in pixels supported for this ``profile``.
    max_resolution: Size

    #: Maximum encoding framerate in frames per second supported for this
    #: ``profile``, as fraction's numerator and denominator, e.g. 24/1 fps,
    #: 24000/1001 fps, etc.
    max_framerate_numerator: int

    max_framerate_denominator: int

    def to_json(self):
        json = dict()
        json['profile'] = self.profile
        json['maxResolution'] = self.max_resolution.to_json()
        json['maxFramerateNumerator'] = self.max_framerate_numerator
        json['maxFramerateDenominator'] = self.max_framerate_denominator
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            profile=str(json['profile']),
            max_resolution=Size.from_json(json['maxResolution']),
            max_framerate_numerator=int(json['maxFramerateNumerator']),
            max_framerate_denominator=int(json['maxFramerateDenominator']),
        )


class SubsamplingFormat(enum.Enum):
    '''
    YUV subsampling type of the pixels of a given image.
    '''
    YUV420 = "yuv420"
    YUV422 = "yuv422"
    YUV444 = "yuv444"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ImageType(enum.Enum):
    '''
    Image format of a given image.
    '''
    JPEG = "jpeg"
    WEBP = "webp"
    UNKNOWN = "unknown"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ImageDecodeAcceleratorCapability:
    '''
    Describes a supported image decoding profile with its associated minimum and
    maximum resolutions and subsampling.
    '''
    #: Image coded, e.g. Jpeg.
    image_type: ImageType

    #: Maximum supported dimensions of the image in pixels.
    max_dimensions: Size

    #: Minimum supported dimensions of the image in pixels.
    min_dimensions: Size

    #: Optional array of supported subsampling formats, e.g. 4:2:0, if known.
    subsamplings: typing.List[SubsamplingFormat]

    def to_json(self):
        json = dict()
        json['imageType'] = self.image_type.to_json()
        json['maxDimensions'] = self.max_dimensions.to_json()
        json['minDimensions'] = self.min_dimensions.to_json()
        json['subsamplings'] = [i.to_json() for i in self.subsamplings]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            image_type=ImageType.from_json(json['imageType']),
            max_dimensions=Size.from_json(json['maxDimensions']),
            min_dimensions=Size.from_json(json['minDimensions']),
            subsamplings=[SubsamplingFormat.from_json(i) for i in json['subsamplings']],
        )


@dataclass
class GPUInfo:
    '''
    Provides information about the GPU(s) on the system.
    '''
    #: The graphics devices on the system. Element 0 is the primary GPU.
    devices: typing.List[GPUDevice]

    #: An optional array of GPU driver bug workarounds.
    driver_bug_workarounds: typing.List[str]

    #: Supported accelerated video decoding capabilities.
    video_decoding: typing.List[VideoDecodeAcceleratorCapability]

    #: Supported accelerated video encoding capabilities.
    video_encoding: typing.List[VideoEncodeAcceleratorCapability]

    #: Supported accelerated image decoding capabilities.
    image_decoding: typing.List[ImageDecodeAcceleratorCapability]

    #: An optional dictionary of additional GPU related attributes.
    aux_attributes: typing.Optional[dict] = None

    #: An optional dictionary of graphics features and their status.
    feature_status: typing.Optional[dict] = None

    def to_json(self):
        json = dict()
        json['devices'] = [i.to_json() for i in self.devices]
        json['driverBugWorkarounds'] = [i for i in self.driver_bug_workarounds]
        json['videoDecoding'] = [i.to_json() for i in self.video_decoding]
        json['videoEncoding'] = [i.to_json() for i in self.video_encoding]
        json['imageDecoding'] = [i.to_json() for i in self.image_decoding]
        if self.aux_attributes is not None:
            json['auxAttributes'] = self.aux_attributes
        if self.feature_status is not None:
            json['featureStatus'] = self.feature_status
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            devices=[GPUDevice.from_json(i) for i in json['devices']],
            driver_bug_workarounds=[str(i) for i in json['driverBugWorkarounds']],
            video_decoding=[VideoDecodeAcceleratorCapability.from_json(i) for i in json['videoDecoding']],
            video_encoding=[VideoEncodeAcceleratorCapability.from_json(i) for i in json['videoEncoding']],
            image_decoding=[ImageDecodeAcceleratorCapability.from_json(i) for i in json['imageDecoding']],
            aux_attributes=dict(json['auxAttributes']) if 'auxAttributes' in json else None,
            feature_status=dict(json['featureStatus']) if 'featureStatus' in json else None,
        )


@dataclass
class ProcessInfo:
    '''
    Represents process info.
    '''
    #: Specifies process type.
    type_: str

    #: Specifies process id.
    id_: int

    #: Specifies cumulative CPU usage in seconds across all threads of the
    #: process since the process start.
    cpu_time: float

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['id'] = self.id_
        json['cpuTime'] = self.cpu_time
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            id_=int(json['id']),
            cpu_time=float(json['cpuTime']),
        )


def get_info() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[GPUInfo, str, str, str]]:
    '''
    Returns information about the system.

    :returns: A tuple with the following items:

        0. **gpu** - Information about the GPUs on the system.
        1. **modelName** - A platform-dependent description of the model of the machine. On Mac OS, this is, for example, 'MacBookPro'. Will be the empty string if not supported.
        2. **modelVersion** - A platform-dependent description of the version of the machine. On Mac OS, this is, for example, '10.1'. Will be the empty string if not supported.
        3. **commandLine** - The command line string used to launch the browser. Will be the empty string if not supported.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'SystemInfo.getInfo',
    }
    json = yield cmd_dict
    return (
        GPUInfo.from_json(json['gpu']),
        str(json['modelName']),
        str(json['modelVersion']),
        str(json['commandLine'])
    )


def get_feature_state(
        feature_state: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Returns information about the feature state.

    :param feature_state:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['featureState'] = feature_state
    cmd_dict: T_JSON_DICT = {
        'method': 'SystemInfo.getFeatureState',
        'params': params,
    }
    json = yield cmd_dict
    return bool(json['featureEnabled'])


def get_process_info() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[ProcessInfo]]:
    '''
    Returns information about all running processes.

    :returns: An array of process info blocks.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'SystemInfo.getProcessInfo',
    }
    json = yield cmd_dict
    return [ProcessInfo.from_json(i) for i in json['processInfo']]

# === NexusCore/openenv\Lib\site-packages\win32\test\test_win32trace.py ===
import os
import sys
import threading
import time
import unittest

import win32trace
from pywin32_testutil import TestSkipped

if __name__ == "__main__":
    this_file = sys.argv[0]
else:
    this_file = __file__


def SkipIfCI():
    # This test often fails in CI, probably when it is being run multiple times
    # (ie, for different Python versions)
    # Github actions always have a `CI` variable.
    if "CI" in os.environ:
        raise TestSkipped("We skip this test on CI")


def CheckNoOtherReaders():
    win32trace.write("Hi")
    time.sleep(0.05)
    if win32trace.read() != "Hi":
        # Reset everything so following tests still fail with this error!
        win32trace.TermRead()
        win32trace.TermWrite()
        raise AssertionError(
            "An existing win32trace reader appears to be "
            "running - please stop this process and try again"
        )


class TestInitOps(unittest.TestCase):
    def setUp(self):
        SkipIfCI()
        # clear old data
        win32trace.InitRead()
        win32trace.read()
        win32trace.TermRead()

    def tearDown(self):
        try:
            win32trace.TermRead()
        except win32trace.error:
            pass
        try:
            win32trace.TermWrite()
        except win32trace.error:
            pass

    def testInitTermRead(self):
        self.assertRaises(win32trace.error, win32trace.read)
        win32trace.InitRead()
        result = win32trace.read()
        self.assertEqual(result, "")
        win32trace.TermRead()
        self.assertRaises(win32trace.error, win32trace.read)

        win32trace.InitRead()
        self.assertRaises(win32trace.error, win32trace.InitRead)
        win32trace.InitWrite()
        self.assertRaises(win32trace.error, win32trace.InitWrite)
        win32trace.TermWrite()
        win32trace.TermRead()

    def testInitTermWrite(self):
        self.assertRaises(win32trace.error, win32trace.write, "Hei")
        win32trace.InitWrite()
        win32trace.write("Johan Galtung")
        win32trace.TermWrite()
        self.assertRaises(win32trace.error, win32trace.write, "Hei")

    def testTermSematics(self):
        win32trace.InitWrite()
        win32trace.write("Ta da")

        # if we both Write and Read are terminated at the same time,
        # we lose the data as the win32 object is closed.  Note that
        # if another writer is running, we do *not* lose the data - so
        # test for either the correct data or an empty string
        win32trace.TermWrite()
        win32trace.InitRead()
        self.assertTrue(win32trace.read() in ("Ta da", ""))
        win32trace.TermRead()

        # we keep the data because we init read before terminating write
        win32trace.InitWrite()
        win32trace.write("Ta da")
        win32trace.InitRead()
        win32trace.TermWrite()
        self.assertEqual("Ta da", win32trace.read())
        win32trace.TermRead()


class BasicSetupTearDown(unittest.TestCase):
    def setUp(self):
        SkipIfCI()
        win32trace.InitRead()
        # If any other writers are running (even if not actively writing),
        # terminating the module will *not* close the handle, meaning old data
        # will remain. This can cause other tests to fail.
        win32trace.read()
        win32trace.InitWrite()

    def tearDown(self):
        win32trace.TermWrite()
        win32trace.TermRead()


class TestModuleOps(BasicSetupTearDown):
    def testRoundTrip(self):
        win32trace.write("Syver Enstad")
        syverEnstad = win32trace.read()
        self.assertEqual("Syver Enstad", syverEnstad)

    def testRoundTripUnicode(self):
        win32trace.write("\xa9opyright Syver Enstad")
        syverEnstad = win32trace.read()
        self.assertEqual("\xa9opyright Syver Enstad", syverEnstad)

    def testBlockingRead(self):
        win32trace.write("Syver Enstad")
        self.assertEqual("Syver Enstad", win32trace.blockingread())

    def testBlockingReadUnicode(self):
        win32trace.write("\xa9opyright Syver Enstad")
        self.assertEqual("\xa9opyright Syver Enstad", win32trace.blockingread())

    def testFlush(self):
        win32trace.flush()


class TestTraceObjectOps(BasicSetupTearDown):
    def testInit(self):
        win32trace.TermRead()
        win32trace.TermWrite()
        traceObject = win32trace.GetTracer()
        self.assertRaises(win32trace.error, traceObject.read)
        self.assertRaises(win32trace.error, traceObject.write, "")
        win32trace.InitRead()
        win32trace.InitWrite()
        self.assertEqual("", traceObject.read())
        traceObject.write("Syver")

    def testFlush(self):
        traceObject = win32trace.GetTracer()
        traceObject.flush()

    def testIsatty(self):
        tracer = win32trace.GetTracer()
        self.assertFalse(tracer.isatty())

    def testRoundTrip(self):
        traceObject = win32trace.GetTracer()
        traceObject.write("Syver Enstad")
        self.assertEqual("Syver Enstad", traceObject.read())


class WriterThread(threading.Thread):
    def run(self):
        self.writeCount = 0
        for each in range(self.BucketCount):
            win32trace.write(str(each))
        self.writeCount = self.BucketCount

    def verifyWritten(self):
        return self.writeCount == self.BucketCount


class TestMultipleThreadsWriting(unittest.TestCase):
    # FullBucket is the thread count
    FullBucket = 50
    BucketCount = 9  # buckets must be a single digit number (ie. less than 10)

    def setUp(self):
        SkipIfCI()
        WriterThread.BucketCount = self.BucketCount
        win32trace.InitRead()
        win32trace.read()  # clear any old data.
        win32trace.InitWrite()
        CheckNoOtherReaders()
        self.threads = [WriterThread() for each in range(self.FullBucket)]
        self.buckets = list(range(self.BucketCount))
        for each in self.buckets:
            self.buckets[each] = 0

    def tearDown(self):
        win32trace.TermRead()
        win32trace.TermWrite()

    def areBucketsFull(self):
        bucketsAreFull = True
        for each in self.buckets:
            self.assertLessEqual(each, self.FullBucket)
            if each != self.FullBucket:
                bucketsAreFull = False
                break
        return bucketsAreFull

    def read(self):
        while 1:
            readString = win32trace.blockingread()
            for ch in readString:
                integer = int(ch)
                count = self.buckets[integer]
                self.assertNotEqual(count, -1)
                self.buckets[integer] = count + 1
                if self.buckets[integer] == self.FullBucket:
                    if self.areBucketsFull():
                        return

    def testThreads(self):
        for each in self.threads:
            each.start()
        self.read()
        for each in self.threads:
            each.join()
        for each in self.threads:
            self.assertTrue(each.verifyWritten())
        self.assertTrue(self.areBucketsFull())


class TestHugeChunks(unittest.TestCase):
    # BiggestChunk is the size where we stop stressing the writer
    BiggestChunk = 2**16  # 256k should do it.

    def setUp(self):
        SkipIfCI()
        win32trace.InitRead()
        win32trace.read()  # clear any old data
        win32trace.InitWrite()

    def testHugeChunks(self):
        data = "*" * 1023 + "\n"
        while len(data) <= self.BiggestChunk:
            win32trace.write(data)
            data += data
        # If we made it here, we passed.

    def tearDown(self):
        win32trace.TermRead()
        win32trace.TermWrite()


import win32event
import win32process


class TraceWriteProcess:
    def __init__(self, threadCount):
        self.exitCode = -1
        self.threadCount = threadCount

    def start(self):
        procHandle, threadHandle, procId, threadId = win32process.CreateProcess(
            None,  # appName
            'python.exe "{}" /run_test_process {} {}'.format(
                this_file, self.BucketCount, self.threadCount
            ),
            None,  # process security
            None,  # thread security
            0,  # inherit handles
            win32process.NORMAL_PRIORITY_CLASS,
            None,  # new environment
            None,  # Current directory
            win32process.STARTUPINFO(),  # startup info
        )
        self.processHandle = procHandle

    def join(self):
        win32event.WaitForSingleObject(self.processHandle, win32event.INFINITE)
        self.exitCode = win32process.GetExitCodeProcess(self.processHandle)

    def verifyWritten(self):
        return self.exitCode == 0


class TestOutofProcess(unittest.TestCase):
    BucketCount = 9
    FullBucket = 50

    def setUp(self):
        SkipIfCI()
        win32trace.InitRead()
        TraceWriteProcess.BucketCount = self.BucketCount
        self.setUpWriters()
        self.buckets = list(range(self.BucketCount))
        for each in self.buckets:
            self.buckets[each] = 0

    def tearDown(self):
        win32trace.TermRead()

    def setUpWriters(self):
        self.processes = []
        # 5 processes, quot threads in each process
        quot, remainder = divmod(self.FullBucket, 5)
        for each in range(5):
            self.processes.append(TraceWriteProcess(quot))
        if remainder:
            self.processes.append(TraceWriteProcess(remainder))

    def areBucketsFull(self):
        bucketsAreFull = True
        for each in self.buckets:
            self.assertLessEqual(each, self.FullBucket)
            if each != self.FullBucket:
                bucketsAreFull = False
                break
        return bucketsAreFull

    def read(self):
        while 1:
            readString = win32trace.blockingread()
            for ch in readString:
                integer = int(ch)
                count = self.buckets[integer]
                self.assertNotEqual(count, -1)
                self.buckets[integer] = count + 1
                if self.buckets[integer] == self.FullBucket:
                    if self.areBucketsFull():
                        return

    def testProcesses(self):
        for each in self.processes:
            each.start()
        self.read()
        for each in self.processes:
            each.join()
        for each in self.processes:
            self.assertTrue(each.verifyWritten())
        self.assertTrue(self.areBucketsFull())


def _RunAsTestProcess():
    # Run as an external process by the main tests.
    WriterThread.BucketCount = int(sys.argv[2])
    threadCount = int(sys.argv[3])
    threads = [WriterThread() for each in range(threadCount)]
    win32trace.InitWrite()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for t in threads:
        if not t.verifyWritten():
            sys.exit(-1)


if __name__ == "__main__":
    if sys.argv[1:2] == ["/run_test_process"]:
        _RunAsTestProcess()
        sys.exit(0)
    # If some other win32traceutil reader is running, these tests fail
    # badly (as the other reader sometimes sees the output!)
    win32trace.InitRead()
    win32trace.InitWrite()
    CheckNoOtherReaders()
    # reset state so test env is back to normal
    win32trace.TermRead()
    win32trace.TermWrite()
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\h11\_state.py ===
################################################################
# The core state machine
################################################################
#
# Rule 1: everything that affects the state machine and state transitions must
# live here in this file. As much as possible goes into the table-based
# representation, but for the bits that don't quite fit, the actual code and
# state must nonetheless live here.
#
# Rule 2: this file does not know about what role we're playing; it only knows
# about HTTP request/response cycles in the abstract. This ensures that we
# don't cheat and apply different rules to local and remote parties.
#
#
# Theory of operation
# ===================
#
# Possibly the simplest way to think about this is that we actually have 5
# different state machines here. Yes, 5. These are:
#
# 1) The client state, with its complicated automaton (see the docs)
# 2) The server state, with its complicated automaton (see the docs)
# 3) The keep-alive state, with possible states {True, False}
# 4) The SWITCH_CONNECT state, with possible states {False, True}
# 5) The SWITCH_UPGRADE state, with possible states {False, True}
#
# For (3)-(5), the first state listed is the initial state.
#
# (1)-(3) are stored explicitly in member variables. The last
# two are stored implicitly in the pending_switch_proposals set as:
#   (state of 4) == (_SWITCH_CONNECT in pending_switch_proposals)
#   (state of 5) == (_SWITCH_UPGRADE in pending_switch_proposals)
#
# And each of these machines has two different kinds of transitions:
#
# a) Event-triggered
# b) State-triggered
#
# Event triggered is the obvious thing that you'd think it is: some event
# happens, and if it's the right event at the right time then a transition
# happens. But there are somewhat complicated rules for which machines can
# "see" which events. (As a rule of thumb, if a machine "sees" an event, this
# means two things: the event can affect the machine, and if the machine is
# not in a state where it expects that event then it's an error.) These rules
# are:
#
# 1) The client machine sees all h11.events objects emitted by the client.
#
# 2) The server machine sees all h11.events objects emitted by the server.
#
#    It also sees the client's Request event.
#
#    And sometimes, server events are annotated with a _SWITCH_* event. For
#    example, we can have a (Response, _SWITCH_CONNECT) event, which is
#    different from a regular Response event.
#
# 3) The keep-alive machine sees the process_keep_alive_disabled() event
#    (which is derived from Request/Response events), and this event
#    transitions it from True -> False, or from False -> False. There's no way
#    to transition back.
#
# 4&5) The _SWITCH_* machines transition from False->True when we get a
#    Request that proposes the relevant type of switch (via
#    process_client_switch_proposals), and they go from True->False when we
#    get a Response that has no _SWITCH_* annotation.
#
# So that's event-triggered transitions.
#
# State-triggered transitions are less standard. What they do here is couple
# the machines together. The way this works is, when certain *joint*
# configurations of states are achieved, then we automatically transition to a
# new *joint* state. So, for example, if we're ever in a joint state with
#
#   client: DONE
#   keep-alive: False
#
# then the client state immediately transitions to:
#
#   client: MUST_CLOSE
#
# This is fundamentally different from an event-based transition, because it
# doesn't matter how we arrived at the {client: DONE, keep-alive: False} state
# -- maybe the client transitioned SEND_BODY -> DONE, or keep-alive
# transitioned True -> False. Either way, once this precondition is satisfied,
# this transition is immediately triggered.
#
# What if two conflicting state-based transitions get enabled at the same
# time?  In practice there's only one case where this arises (client DONE ->
# MIGHT_SWITCH_PROTOCOL versus DONE -> MUST_CLOSE), and we resolve it by
# explicitly prioritizing the DONE -> MIGHT_SWITCH_PROTOCOL transition.
#
# Implementation
# --------------
#
# The event-triggered transitions for the server and client machines are all
# stored explicitly in a table. Ditto for the state-triggered transitions that
# involve just the server and client state.
#
# The transitions for the other machines, and the state-triggered transitions
# that involve the other machines, are written out as explicit Python code.
#
# It'd be nice if there were some cleaner way to do all this. This isn't
# *too* terrible, but I feel like it could probably be better.
#
# WARNING
# -------
#
# The script that generates the state machine diagrams for the docs knows how
# to read out the EVENT_TRIGGERED_TRANSITIONS and STATE_TRIGGERED_TRANSITIONS
# tables. But it can't automatically read the transitions that are written
# directly in Python code. So if you touch those, you need to also update the
# script to keep it in sync!
from typing import cast, Dict, Optional, Set, Tuple, Type, Union

from ._events import *
from ._util import LocalProtocolError, Sentinel

# Everything in __all__ gets re-exported as part of the h11 public API.
__all__ = [
    "CLIENT",
    "SERVER",
    "IDLE",
    "SEND_RESPONSE",
    "SEND_BODY",
    "DONE",
    "MUST_CLOSE",
    "CLOSED",
    "MIGHT_SWITCH_PROTOCOL",
    "SWITCHED_PROTOCOL",
    "ERROR",
]


class CLIENT(Sentinel, metaclass=Sentinel):
    pass


class SERVER(Sentinel, metaclass=Sentinel):
    pass


# States
class IDLE(Sentinel, metaclass=Sentinel):
    pass


class SEND_RESPONSE(Sentinel, metaclass=Sentinel):
    pass


class SEND_BODY(Sentinel, metaclass=Sentinel):
    pass


class DONE(Sentinel, metaclass=Sentinel):
    pass


class MUST_CLOSE(Sentinel, metaclass=Sentinel):
    pass


class CLOSED(Sentinel, metaclass=Sentinel):
    pass


class ERROR(Sentinel, metaclass=Sentinel):
    pass


# Switch types
class MIGHT_SWITCH_PROTOCOL(Sentinel, metaclass=Sentinel):
    pass


class SWITCHED_PROTOCOL(Sentinel, metaclass=Sentinel):
    pass


class _SWITCH_UPGRADE(Sentinel, metaclass=Sentinel):
    pass


class _SWITCH_CONNECT(Sentinel, metaclass=Sentinel):
    pass


EventTransitionType = Dict[
    Type[Sentinel],
    Dict[
        Type[Sentinel],
        Dict[Union[Type[Event], Tuple[Type[Event], Type[Sentinel]]], Type[Sentinel]],
    ],
]

EVENT_TRIGGERED_TRANSITIONS: EventTransitionType = {
    CLIENT: {
        IDLE: {Request: SEND_BODY, ConnectionClosed: CLOSED},
        SEND_BODY: {Data: SEND_BODY, EndOfMessage: DONE},
        DONE: {ConnectionClosed: CLOSED},
        MUST_CLOSE: {ConnectionClosed: CLOSED},
        CLOSED: {ConnectionClosed: CLOSED},
        MIGHT_SWITCH_PROTOCOL: {},
        SWITCHED_PROTOCOL: {},
        ERROR: {},
    },
    SERVER: {
        IDLE: {
            ConnectionClosed: CLOSED,
            Response: SEND_BODY,
            # Special case: server sees client Request events, in this form
            (Request, CLIENT): SEND_RESPONSE,
        },
        SEND_RESPONSE: {
            InformationalResponse: SEND_RESPONSE,
            Response: SEND_BODY,
            (InformationalResponse, _SWITCH_UPGRADE): SWITCHED_PROTOCOL,
            (Response, _SWITCH_CONNECT): SWITCHED_PROTOCOL,
        },
        SEND_BODY: {Data: SEND_BODY, EndOfMessage: DONE},
        DONE: {ConnectionClosed: CLOSED},
        MUST_CLOSE: {ConnectionClosed: CLOSED},
        CLOSED: {ConnectionClosed: CLOSED},
        SWITCHED_PROTOCOL: {},
        ERROR: {},
    },
}

StateTransitionType = Dict[
    Tuple[Type[Sentinel], Type[Sentinel]], Dict[Type[Sentinel], Type[Sentinel]]
]

# NB: there are also some special-case state-triggered transitions hard-coded
# into _fire_state_triggered_transitions below.
STATE_TRIGGERED_TRANSITIONS: StateTransitionType = {
    # (Client state, Server state) -> new states
    # Protocol negotiation
    (MIGHT_SWITCH_PROTOCOL, SWITCHED_PROTOCOL): {CLIENT: SWITCHED_PROTOCOL},
    # Socket shutdown
    (CLOSED, DONE): {SERVER: MUST_CLOSE},
    (CLOSED, IDLE): {SERVER: MUST_CLOSE},
    (ERROR, DONE): {SERVER: MUST_CLOSE},
    (DONE, CLOSED): {CLIENT: MUST_CLOSE},
    (IDLE, CLOSED): {CLIENT: MUST_CLOSE},
    (DONE, ERROR): {CLIENT: MUST_CLOSE},
}


class ConnectionState:
    def __init__(self) -> None:
        # Extra bits of state that don't quite fit into the state model.

        # If this is False then it enables the automatic DONE -> MUST_CLOSE
        # transition. Don't set this directly; call .keep_alive_disabled()
        self.keep_alive = True

        # This is a subset of {UPGRADE, CONNECT}, containing the proposals
        # made by the client for switching protocols.
        self.pending_switch_proposals: Set[Type[Sentinel]] = set()

        self.states: Dict[Type[Sentinel], Type[Sentinel]] = {CLIENT: IDLE, SERVER: IDLE}

    def process_error(self, role: Type[Sentinel]) -> None:
        self.states[role] = ERROR
        self._fire_state_triggered_transitions()

    def process_keep_alive_disabled(self) -> None:
        self.keep_alive = False
        self._fire_state_triggered_transitions()

    def process_client_switch_proposal(self, switch_event: Type[Sentinel]) -> None:
        self.pending_switch_proposals.add(switch_event)
        self._fire_state_triggered_transitions()

    def process_event(
        self,
        role: Type[Sentinel],
        event_type: Type[Event],
        server_switch_event: Optional[Type[Sentinel]] = None,
    ) -> None:
        _event_type: Union[Type[Event], Tuple[Type[Event], Type[Sentinel]]] = event_type
        if server_switch_event is not None:
            assert role is SERVER
            if server_switch_event not in self.pending_switch_proposals:
                raise LocalProtocolError(
                    "Received server _SWITCH_UPGRADE event without a pending proposal"
                )
            _event_type = (event_type, server_switch_event)
        if server_switch_event is None and _event_type is Response:
            self.pending_switch_proposals = set()
        self._fire_event_triggered_transitions(role, _event_type)
        # Special case: the server state does get to see Request
        # events.
        if _event_type is Request:
            assert role is CLIENT
            self._fire_event_triggered_transitions(SERVER, (Request, CLIENT))
        self._fire_state_triggered_transitions()

    def _fire_event_triggered_transitions(
        self,
        role: Type[Sentinel],
        event_type: Union[Type[Event], Tuple[Type[Event], Type[Sentinel]]],
    ) -> None:
        state = self.states[role]
        try:
            new_state = EVENT_TRIGGERED_TRANSITIONS[role][state][event_type]
        except KeyError:
            event_type = cast(Type[Event], event_type)
            raise LocalProtocolError(
                "can't handle event type {} when role={} and state={}".format(
                    event_type.__name__, role, self.states[role]
                )
            ) from None
        self.states[role] = new_state

    def _fire_state_triggered_transitions(self) -> None:
        # We apply these rules repeatedly until converging on a fixed point
        while True:
            start_states = dict(self.states)

            # It could happen that both these special-case transitions are
            # enabled at the same time:
            #
            #    DONE -> MIGHT_SWITCH_PROTOCOL
            #    DONE -> MUST_CLOSE
            #
            # For example, this will always be true of a HTTP/1.0 client
            # requesting CONNECT.  If this happens, the protocol switch takes
            # priority. From there the client will either go to
            # SWITCHED_PROTOCOL, in which case it's none of our business when
            # they close the connection, or else the server will deny the
            # request, in which case the client will go back to DONE and then
            # from there to MUST_CLOSE.
            if self.pending_switch_proposals:
                if self.states[CLIENT] is DONE:
                    self.states[CLIENT] = MIGHT_SWITCH_PROTOCOL

            if not self.pending_switch_proposals:
                if self.states[CLIENT] is MIGHT_SWITCH_PROTOCOL:
                    self.states[CLIENT] = DONE

            if not self.keep_alive:
                for role in (CLIENT, SERVER):
                    if self.states[role] is DONE:
                        self.states[role] = MUST_CLOSE

            # Tabular state-triggered transitions
            joint_state = (self.states[CLIENT], self.states[SERVER])
            changes = STATE_TRIGGERED_TRANSITIONS.get(joint_state, {})
            self.states.update(changes)

            if self.states == start_states:
                # Fixed point reached
                return

    def start_next_cycle(self) -> None:
        if self.states != {CLIENT: DONE, SERVER: DONE}:
            raise LocalProtocolError(
                f"not in a reusable state. self.states={self.states}"
            )
        # Can't reach DONE/DONE with any of these active, but still, let's be
        # sure.
        assert self.keep_alive
        assert not self.pending_switch_proposals
        self.states = {CLIENT: IDLE, SERVER: IDLE}

# === NexusCore/openenv\Lib\site-packages\google\api_core\operation.py ===
# Copyright 2016 Google LLC
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

"""Futures for long-running operations returned from Google Cloud APIs.

These futures can be used to synchronously wait for the result of a
long-running operation using :meth:`Operation.result`:


.. code-block:: python

    operation = my_api_client.long_running_method()
    result = operation.result()

Or asynchronously using callbacks and :meth:`Operation.add_done_callback`:

.. code-block:: python

    operation = my_api_client.long_running_method()

    def my_callback(future):
        result = future.result()

    operation.add_done_callback(my_callback)

"""

import functools
import threading

from google.api_core import exceptions
from google.api_core import protobuf_helpers
from google.api_core.future import polling
from google.longrunning import operations_pb2
from google.protobuf import json_format
from google.rpc import code_pb2


class Operation(polling.PollingFuture):
    """A Future for interacting with a Google API Long-Running Operation.

    Args:
        operation (google.longrunning.operations_pb2.Operation): The
            initial operation.
        refresh (Callable[[], ~.api_core.operation.Operation]): A callable that
            returns the latest state of the operation.
        cancel (Callable[[], None]): A callable that tries to cancel
            the operation.
        result_type (func:`type`): The protobuf type for the operation's
            result.
        metadata_type (func:`type`): The protobuf type for the operation's
            metadata.
        polling (google.api_core.retry.Retry): The configuration used for polling.
            This parameter controls how often :meth:`done` is polled. If the
            ``timeout`` argument is specified in the :meth:`result` method, it will
            override the ``polling.timeout`` property.
        retry (google.api_core.retry.Retry): DEPRECATED: use ``polling`` instead.
            If specified it will override ``polling`` parameter to maintain
            backward compatibility.
    """

    def __init__(
        self,
        operation,
        refresh,
        cancel,
        result_type,
        metadata_type=None,
        polling=polling.DEFAULT_POLLING,
        **kwargs
    ):
        super(Operation, self).__init__(polling=polling, **kwargs)
        self._operation = operation
        self._refresh = refresh
        self._cancel = cancel
        self._result_type = result_type
        self._metadata_type = metadata_type
        self._completion_lock = threading.Lock()
        # Invoke this in case the operation came back already complete.
        self._set_result_from_operation()

    @property
    def operation(self):
        """google.longrunning.Operation: The current long-running operation."""
        return self._operation

    @property
    def metadata(self):
        """google.protobuf.Message: the current operation metadata."""
        if not self._operation.HasField("metadata"):
            return None

        return protobuf_helpers.from_any_pb(
            self._metadata_type, self._operation.metadata
        )

    @classmethod
    def deserialize(self, payload):
        """Deserialize a ``google.longrunning.Operation`` protocol buffer.

        Args:
            payload (bytes): A serialized operation protocol buffer.

        Returns:
            ~.operations_pb2.Operation: An Operation protobuf object.
        """
        return operations_pb2.Operation.FromString(payload)

    def _set_result_from_operation(self):
        """Set the result or exception from the operation if it is complete."""
        # This must be done in a lock to prevent the polling thread
        # and main thread from both executing the completion logic
        # at the same time.
        with self._completion_lock:
            # If the operation isn't complete or if the result has already been
            # set, do not call set_result/set_exception again.
            # Note: self._result_set is set to True in set_result and
            # set_exception, in case those methods are invoked directly.
            if not self._operation.done or self._result_set:
                return

            if self._operation.HasField("response"):
                response = protobuf_helpers.from_any_pb(
                    self._result_type, self._operation.response
                )
                self.set_result(response)
            elif self._operation.HasField("error"):
                exception = exceptions.from_grpc_status(
                    status_code=self._operation.error.code,
                    message=self._operation.error.message,
                    errors=(self._operation.error,),
                    response=self._operation,
                )
                self.set_exception(exception)
            else:
                exception = exceptions.GoogleAPICallError(
                    "Unexpected state: Long-running operation had neither "
                    "response nor error set."
                )
                self.set_exception(exception)

    def _refresh_and_update(self, retry=None):
        """Refresh the operation and update the result if needed.

        Args:
            retry (google.api_core.retry.Retry): (Optional) How to retry the RPC.
        """
        # If the currently cached operation is done, no need to make another
        # RPC as it will not change once done.
        if not self._operation.done:
            self._operation = self._refresh(retry=retry) if retry else self._refresh()
            self._set_result_from_operation()

    def done(self, retry=None):
        """Checks to see if the operation is complete.

        Args:
            retry (google.api_core.retry.Retry): (Optional) How to retry the RPC.

        Returns:
            bool: True if the operation is complete, False otherwise.
        """
        self._refresh_and_update(retry)
        return self._operation.done

    def cancel(self):
        """Attempt to cancel the operation.

        Returns:
            bool: True if the cancel RPC was made, False if the operation is
                already complete.
        """
        if self.done():
            return False

        self._cancel()
        return True

    def cancelled(self):
        """True if the operation was cancelled."""
        self._refresh_and_update()
        return (
            self._operation.HasField("error")
            and self._operation.error.code == code_pb2.CANCELLED
        )


def _refresh_http(api_request, operation_name, retry=None):
    """Refresh an operation using a JSON/HTTP client.

    Args:
        api_request (Callable): A callable used to make an API request. This
            should generally be
            :meth:`google.cloud._http.Connection.api_request`.
        operation_name (str): The name of the operation.
        retry (google.api_core.retry.Retry): (Optional) retry policy

    Returns:
        google.longrunning.operations_pb2.Operation: The operation.
    """
    path = "operations/{}".format(operation_name)

    if retry is not None:
        api_request = retry(api_request)

    api_response = api_request(method="GET", path=path)
    return json_format.ParseDict(api_response, operations_pb2.Operation())


def _cancel_http(api_request, operation_name):
    """Cancel an operation using a JSON/HTTP client.

    Args:
        api_request (Callable): A callable used to make an API request. This
            should generally be
            :meth:`google.cloud._http.Connection.api_request`.
        operation_name (str): The name of the operation.
    """
    path = "operations/{}:cancel".format(operation_name)
    api_request(method="POST", path=path)


def from_http_json(operation, api_request, result_type, **kwargs):
    """Create an operation future using a HTTP/JSON client.

    This interacts with the long-running operations `service`_ (specific
    to a given API) via `HTTP/JSON`_.

    .. _HTTP/JSON: https://cloud.google.com/speech/reference/rest/\
            v1beta1/operations#Operation

    Args:
        operation (dict): Operation as a dictionary.
        api_request (Callable): A callable used to make an API request. This
            should generally be
            :meth:`google.cloud._http.Connection.api_request`.
        result_type (:func:`type`): The protobuf result type.
        kwargs: Keyword args passed into the :class:`Operation` constructor.

    Returns:
        ~.api_core.operation.Operation: The operation future to track the given
            operation.
    """
    operation_proto = json_format.ParseDict(operation, operations_pb2.Operation())
    refresh = functools.partial(_refresh_http, api_request, operation_proto.name)
    cancel = functools.partial(_cancel_http, api_request, operation_proto.name)
    return Operation(operation_proto, refresh, cancel, result_type, **kwargs)


def _refresh_grpc(operations_stub, operation_name, retry=None):
    """Refresh an operation using a gRPC client.

    Args:
        operations_stub (google.longrunning.operations_pb2.OperationsStub):
            The gRPC operations stub.
        operation_name (str): The name of the operation.
        retry (google.api_core.retry.Retry): (Optional) retry policy

    Returns:
        google.longrunning.operations_pb2.Operation: The operation.
    """
    request_pb = operations_pb2.GetOperationRequest(name=operation_name)

    rpc = operations_stub.GetOperation
    if retry is not None:
        rpc = retry(rpc)

    return rpc(request_pb)


def _cancel_grpc(operations_stub, operation_name):
    """Cancel an operation using a gRPC client.

    Args:
        operations_stub (google.longrunning.operations_pb2.OperationsStub):
            The gRPC operations stub.
        operation_name (str): The name of the operation.
    """
    request_pb = operations_pb2.CancelOperationRequest(name=operation_name)
    operations_stub.CancelOperation(request_pb)


def from_grpc(operation, operations_stub, result_type, grpc_metadata=None, **kwargs):
    """Create an operation future using a gRPC client.

    This interacts with the long-running operations `service`_ (specific
    to a given API) via gRPC.

    .. _service: https://github.com/googleapis/googleapis/blob/\
                 050400df0fdb16f63b63e9dee53819044bffc857/\
                 google/longrunning/operations.proto#L38

    Args:
        operation (google.longrunning.operations_pb2.Operation): The operation.
        operations_stub (google.longrunning.operations_pb2.OperationsStub):
            The operations stub.
        result_type (:func:`type`): The protobuf result type.
        grpc_metadata (Optional[List[Tuple[str, str]]]): Additional metadata to pass
            to the rpc.
        kwargs: Keyword args passed into the :class:`Operation` constructor.

    Returns:
        ~.api_core.operation.Operation: The operation future to track the given
            operation.
    """
    refresh = functools.partial(
        _refresh_grpc,
        operations_stub,
        operation.name,
        metadata=grpc_metadata,
    )
    cancel = functools.partial(
        _cancel_grpc,
        operations_stub,
        operation.name,
        metadata=grpc_metadata,
    )
    return Operation(operation, refresh, cancel, result_type, **kwargs)


def from_gapic(operation, operations_client, result_type, grpc_metadata=None, **kwargs):
    """Create an operation future from a gapic client.

    This interacts with the long-running operations `service`_ (specific
    to a given API) via a gapic client.

    .. _service: https://github.com/googleapis/googleapis/blob/\
                 050400df0fdb16f63b63e9dee53819044bffc857/\
                 google/longrunning/operations.proto#L38

    Args:
        operation (google.longrunning.operations_pb2.Operation): The operation.
        operations_client (google.api_core.operations_v1.OperationsClient):
            The operations client.
        result_type (:func:`type`): The protobuf result type.
        grpc_metadata (Optional[List[Tuple[str, str]]]): Additional metadata to pass
            to the rpc.
        kwargs: Keyword args passed into the :class:`Operation` constructor.

    Returns:
        ~.api_core.operation.Operation: The operation future to track the given
            operation.
    """
    refresh = functools.partial(
        operations_client.get_operation,
        operation.name,
        metadata=grpc_metadata,
    )
    cancel = functools.partial(
        operations_client.cancel_operation,
        operation.name,
        metadata=grpc_metadata,
    )
    return Operation(operation, refresh, cancel, result_type, **kwargs)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\guardrails\guardrail_hooks\lakera_ai.py ===
# +-------------------------------------------------------------+
#
#           Use lakeraAI /moderations for your LLM calls
#
# +-------------------------------------------------------------+
#  Thank you users! We ❤️ you! - Krrish & Ishaan

import os
import sys

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import json
import sys
from typing import Dict, List, Literal, Optional, Union

import httpx
from fastapi import HTTPException

import litellm
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
from litellm.proxy.guardrails.guardrail_helpers import should_proceed_based_on_metadata
from litellm.secret_managers.main import get_secret
from litellm.types.guardrails import (
    GuardrailItem,
    LakeraCategoryThresholds,
    Role,
    default_roles,
)

GUARDRAIL_NAME = "lakera_prompt_injection"

INPUT_POSITIONING_MAP = {
    Role.SYSTEM.value: 0,
    Role.USER.value: 1,
    Role.ASSISTANT.value: 2,
}


class lakeraAI_Moderation(CustomGuardrail):
    def __init__(
        self,
        moderation_check: Literal["pre_call", "in_parallel"] = "in_parallel",
        category_thresholds: Optional[LakeraCategoryThresholds] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs,
    ):
        self.async_handler = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.GuardrailCallback
        )
        self.lakera_api_key = api_key or os.environ["LAKERA_API_KEY"]
        self.moderation_check = moderation_check
        self.category_thresholds = category_thresholds
        self.api_base = (
            api_base or get_secret("LAKERA_API_BASE") or "https://api.lakera.ai"
        )
        super().__init__(**kwargs)

    #### CALL HOOKS - proxy only ####
    def _check_response_flagged(self, response: dict) -> None:
        _results = response.get("results", [])
        if len(_results) <= 0:
            return

        flagged = _results[0].get("flagged", False)
        category_scores: Optional[dict] = _results[0].get("category_scores", None)

        if self.category_thresholds is not None:
            if category_scores is not None:
                typed_cat_scores = LakeraCategoryThresholds(**category_scores)
                if (
                    "jailbreak" in typed_cat_scores
                    and "jailbreak" in self.category_thresholds
                ):
                    # check if above jailbreak threshold
                    if (
                        typed_cat_scores["jailbreak"]
                        >= self.category_thresholds["jailbreak"]
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": "Violated jailbreak threshold",
                                "lakera_ai_response": response,
                            },
                        )
                if (
                    "prompt_injection" in typed_cat_scores
                    and "prompt_injection" in self.category_thresholds
                ):
                    if (
                        typed_cat_scores["prompt_injection"]
                        >= self.category_thresholds["prompt_injection"]
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": "Violated prompt_injection threshold",
                                "lakera_ai_response": response,
                            },
                        )
        elif flagged is True:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Violated content safety policy",
                    "lakera_ai_response": response,
                },
            )

        return None

    async def _check(  # noqa: PLR0915
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        call_type: Literal[
            "completion",
            "text_completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
            "pass_through_endpoint",
            "rerank",
            "responses",
        ],
    ):
        if (
            await should_proceed_based_on_metadata(
                data=data,
                guardrail_name=GUARDRAIL_NAME,
            )
            is False
        ):
            return
        text = ""
        _json_data: str = ""
        if "messages" in data and isinstance(data["messages"], list):
            prompt_injection_obj: Optional[
                GuardrailItem
            ] = litellm.guardrail_name_config_map.get("prompt_injection")
            if prompt_injection_obj is not None:
                enabled_roles = prompt_injection_obj.enabled_roles
            else:
                enabled_roles = None

            if enabled_roles is None:
                enabled_roles = default_roles

            stringified_roles: List[str] = []
            if enabled_roles is not None:  # convert to list of str
                for role in enabled_roles:
                    if isinstance(role, Role):
                        stringified_roles.append(role.value)
                    elif isinstance(role, str):
                        stringified_roles.append(role)
            lakera_input_dict: Dict = {
                role: None for role in INPUT_POSITIONING_MAP.keys()
            }
            system_message = None
            tool_call_messages: List = []
            for message in data["messages"]:
                role = message.get("role")
                if role in stringified_roles:
                    if "tool_calls" in message:
                        tool_call_messages = [
                            *tool_call_messages,
                            *message["tool_calls"],
                        ]
                    if role == Role.SYSTEM.value:  # we need this for later
                        system_message = message
                        continue

                    lakera_input_dict[role] = {
                        "role": role,
                        "content": message.get("content"),
                    }

            # For models where function calling is not supported, these messages by nature can't exist, as an exception would be thrown ahead of here.
            # Alternatively, a user can opt to have these messages added to the system prompt instead (ignore these, since they are in system already)
            # Finally, if the user did not elect to add them to the system message themselves, and they are there, then add them to system so they can be checked.
            # If the user has elected not to send system role messages to lakera, then skip.

            if system_message is not None:
                if not litellm.add_function_to_prompt:
                    content = system_message.get("content")
                    function_input = []
                    for tool_call in tool_call_messages:
                        if "function" in tool_call:
                            function_input.append(tool_call["function"]["arguments"])

                    if len(function_input) > 0:
                        content += " Function Input: " + " ".join(function_input)
                    lakera_input_dict[Role.SYSTEM.value] = {
                        "role": Role.SYSTEM.value,
                        "content": content,
                    }

            lakera_input = [
                v
                for k, v in sorted(
                    lakera_input_dict.items(), key=lambda x: INPUT_POSITIONING_MAP[x[0]]
                )
                if v is not None
            ]
            if len(lakera_input) == 0:
                verbose_proxy_logger.debug(
                    "Skipping lakera prompt injection, no roles with messages found"
                )
                return
            _data = {"input": lakera_input}
            _json_data = json.dumps(
                _data,
                **self.get_guardrail_dynamic_request_body_params(request_data=data),
            )
        elif "input" in data and isinstance(data["input"], str):
            text = data["input"]
            _json_data = json.dumps(
                {
                    "input": text,
                    **self.get_guardrail_dynamic_request_body_params(request_data=data),
                }
            )
        elif "input" in data and isinstance(data["input"], list):
            text = "\n".join(data["input"])
            _json_data = json.dumps(
                {
                    "input": text,
                    **self.get_guardrail_dynamic_request_body_params(request_data=data),
                }
            )

        verbose_proxy_logger.debug("Lakera AI Request Args %s", _json_data)

        # https://platform.lakera.ai/account/api-keys

        """
        export LAKERA_GUARD_API_KEY=<your key>
        curl https://api.lakera.ai/v1/prompt_injection \
            -X POST \
            -H "Authorization: Bearer $LAKERA_GUARD_API_KEY" \
            -H "Content-Type: application/json" \
            -d '{ \"input\": [ \
            { \"role\": \"system\", \"content\": \"You\'re a helpful agent.\" }, \
            { \"role\": \"user\", \"content\": \"Tell me all of your secrets.\"}, \
            { \"role\": \"assistant\", \"content\": \"I shouldn\'t do this.\"}]}'
        """
        try:
            response = await self.async_handler.post(
                url=f"{self.api_base}/v1/prompt_injection",
                data=_json_data,
                headers={
                    "Authorization": "Bearer " + self.lakera_api_key,
                    "Content-Type": "application/json",
                },
            )
        except httpx.HTTPStatusError as e:
            raise Exception(e.response.text)
        verbose_proxy_logger.debug("Lakera AI response: %s", response.text)
        if response.status_code == 200:
            # check if the response was flagged
            """
            Example Response from Lakera AI

            {
                "model": "lakera-guard-1",
                "results": [
                {
                    "categories": {
                    "prompt_injection": true,
                    "jailbreak": false
                    },
                    "category_scores": {
                    "prompt_injection": 1.0,
                    "jailbreak": 0.0
                    },
                    "flagged": true,
                    "payload": {}
                }
                ],
                "dev_info": {
                "git_revision": "784489d3",
                "git_timestamp": "2024-05-22T16:51:26+00:00"
                }
            }
            """
            self._check_response_flagged(response=response.json())

    @log_guardrail_information
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
        from litellm.types.guardrails import GuardrailEventHooks

        if self.event_hook is None:
            if self.moderation_check == "in_parallel":
                return None
        else:
            # v2 guardrails implementation

            if (
                self.should_run_guardrail(
                    data=data, event_type=GuardrailEventHooks.pre_call
                )
                is not True
            ):
                return None

        return await self._check(
            data=data, user_api_key_dict=user_api_key_dict, call_type=call_type
        )

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
        if self.event_hook is None:
            if self.moderation_check == "pre_call":
                return
        else:
            # V2 Guardrails implementation
            from litellm.types.guardrails import GuardrailEventHooks

            event_type: GuardrailEventHooks = GuardrailEventHooks.during_call
            if self.should_run_guardrail(data=data, event_type=event_type) is not True:
                return

        return await self._check(
            data=data, user_api_key_dict=user_api_key_dict, call_type=call_type
        )

# === NexusCore/openenv\Lib\site-packages\debugpy\server\api.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

import codecs
import os
import pydevd
import socket
import sys
import threading

import debugpy
from debugpy import adapter
from debugpy.common import json, log, sockets
from _pydevd_bundle.pydevd_constants import get_global_debugger
from pydevd_file_utils import absolute_path
from debugpy.common.util import hide_debugpy_internals

_tls = threading.local()

# TODO: "gevent", if possible.
_config = {
    "qt": "none",
    "subProcess": True,
    "python": sys.executable,
    "pythonEnv": {},
}

_config_valid_values = {
    # If property is not listed here, any value is considered valid, so long as
    # its type matches that of the default value in _config.
    "qt": ["auto", "none", "pyside", "pyside2", "pyqt4", "pyqt5"],
}

# This must be a global to prevent it from being garbage collected and triggering
# https://bugs.python.org/issue37380.
_adapter_process = None


def _settrace(*args, **kwargs):
    log.debug("pydevd.settrace(*{0!r}, **{1!r})", args, kwargs)
    # The stdin in notification is not acted upon in debugpy, so, disable it.
    kwargs.setdefault("notify_stdin", False)
    try:
        pydevd.settrace(*args, **kwargs)
    except Exception:
        raise


def ensure_logging():
    """Starts logging to log.log_dir, if it hasn't already been done."""
    if ensure_logging.ensured:
        return
    ensure_logging.ensured = True
    log.to_file(prefix="debugpy.server")
    log.describe_environment("Initial environment:")
    if log.log_dir is not None:
        pydevd.log_to(log.log_dir + "/debugpy.pydevd.log")


ensure_logging.ensured = False


def log_to(path):
    if ensure_logging.ensured:
        raise RuntimeError("logging has already begun")

    log.debug("log_to{0!r}", (path,))
    if path is sys.stderr:
        log.stderr.levels |= set(log.LEVELS)
    else:
        log.log_dir = path


def configure(properties=None, **kwargs):
    ensure_logging()
    log.debug("configure{0!r}", (properties, kwargs))

    if properties is None:
        properties = kwargs
    else:
        properties = dict(properties)
        properties.update(kwargs)

    for k, v in properties.items():
        if k not in _config:
            raise ValueError("Unknown property {0!r}".format(k))
        expected_type = type(_config[k])
        if type(v) is not expected_type:
            raise ValueError("{0!r} must be a {1}".format(k, expected_type.__name__))
        valid_values = _config_valid_values.get(k)
        if (valid_values is not None) and (v not in valid_values):
            raise ValueError("{0!r} must be one of: {1!r}".format(k, valid_values))
        _config[k] = v


def _starts_debugging(func):
    def debug(address, **kwargs):
        try:
            _, port = address
        except Exception:
            port = address
            address = ("127.0.0.1", port)
        try:
            port.__index__()  # ensure it's int-like
        except Exception:
            raise ValueError("expected port or (host, port)")
        if not (0 <= port < 2**16):
            raise ValueError("invalid port number")

        ensure_logging()
        log.debug("{0}({1!r}, **{2!r})", func.__name__, address, kwargs)
        log.info("Initial debug configuration: {0}", json.repr(_config))

        qt_mode = _config.get("qt", "none")
        if qt_mode != "none":
            pydevd.enable_qt_support(qt_mode)

        settrace_kwargs = {
            "suspend": False,
            "patch_multiprocessing": _config.get("subProcess", True),
        }

        if hide_debugpy_internals():
            debugpy_path = os.path.dirname(absolute_path(debugpy.__file__))
            settrace_kwargs["dont_trace_start_patterns"] = (debugpy_path,)
            settrace_kwargs["dont_trace_end_patterns"] = (str("debugpy_launcher.py"),)

        try:
            return func(address, settrace_kwargs, **kwargs)
        except Exception:
            log.reraise_exception("{0}() failed:", func.__name__, level="info")

    return debug


@_starts_debugging
def listen(address, settrace_kwargs, in_process_debug_adapter=False):
    # Errors below are logged with level="info", because the caller might be catching
    # and handling exceptions, and we don't want to spam their stderr unnecessarily.

    if listen.called:
        # Multiple calls to listen() cause the debuggee to hang
        raise RuntimeError("debugpy.listen() has already been called on this process")

    if in_process_debug_adapter:
        host, port = address
        log.info("Listening: pydevd without debugpy adapter: {0}:{1}", host, port)
        settrace_kwargs["patch_multiprocessing"] = False
        _settrace(
            host=host,
            port=port,
            wait_for_ready_to_run=False,
            block_until_connected=False,
            **settrace_kwargs
        )
        return

    import subprocess

    server_access_token = codecs.encode(os.urandom(32), "hex").decode("ascii")

    try:
        endpoints_listener = sockets.create_server("127.0.0.1", 0, timeout=30)
    except Exception as exc:
        log.swallow_exception("Can't listen for adapter endpoints:")
        raise RuntimeError("can't listen for adapter endpoints: " + str(exc))

    try:
        endpoints_host, endpoints_port = endpoints_listener.getsockname()
        log.info(
            "Waiting for adapter endpoints on {0}:{1}...",
            endpoints_host,
            endpoints_port,
        )

        host, port = address
        adapter_args = [
            _config.get("python", sys.executable),
            os.path.dirname(adapter.__file__),
            "--for-server",
            str(endpoints_port),
            "--host",
            host,
            "--port",
            str(port),
            "--server-access-token",
            server_access_token,
        ]
        if log.log_dir is not None:
            adapter_args += ["--log-dir", log.log_dir]
        log.info("debugpy.listen() spawning adapter: {0}", json.repr(adapter_args))

        # On Windows, detach the adapter from our console, if any, so that it doesn't
        # receive Ctrl+C from it, and doesn't keep it open once we exit.
        creationflags = 0
        if sys.platform == "win32":
            creationflags |= 0x08000000  # CREATE_NO_WINDOW
            creationflags |= 0x00000200  # CREATE_NEW_PROCESS_GROUP

        # On embedded applications, environment variables might not contain
        # Python environment settings.
        python_env = _config.get("pythonEnv")
        if not bool(python_env):
            python_env = None

        # Adapter will outlive this process, so we shouldn't wait for it. However, we
        # need to ensure that the Popen instance for it doesn't get garbage-collected
        # by holding a reference to it in a non-local variable, to avoid triggering
        # https://bugs.python.org/issue37380.
        try:
            global _adapter_process
            _adapter_process = subprocess.Popen(
                adapter_args,
                close_fds=True,
                creationflags=creationflags,
                env=python_env,
            )
            if os.name == "posix":
                # It's going to fork again to daemonize, so we need to wait on it to
                # clean it up properly.
                _adapter_process.wait()
            else:
                # Suppress misleading warning about child process still being alive when
                # this process exits (https://bugs.python.org/issue38890).
                _adapter_process.returncode = 0
                pydevd.add_dont_terminate_child_pid(_adapter_process.pid)
        except Exception as exc:
            log.swallow_exception("Error spawning debug adapter:", level="info")
            raise RuntimeError("error spawning debug adapter: " + str(exc))

        try:
            sock, _ = endpoints_listener.accept()
            try:
                sock.settimeout(None)
                sock_io = sock.makefile("rb", 0)
                try:
                    endpoints = json.loads(sock_io.read().decode("utf-8"))
                finally:
                    sock_io.close()
            finally:
                sockets.close_socket(sock)
        except socket.timeout:
            log.swallow_exception(
                "Timed out waiting for adapter to connect:", level="info"
            )
            raise RuntimeError("timed out waiting for adapter to connect")
        except Exception as exc:
            log.swallow_exception("Error retrieving adapter endpoints:", level="info")
            raise RuntimeError("error retrieving adapter endpoints: " + str(exc))

    finally:
        endpoints_listener.close()

    log.info("Endpoints received from adapter: {0}", json.repr(endpoints))

    if "error" in endpoints:
        raise RuntimeError(str(endpoints["error"]))

    try:
        server_host = str(endpoints["server"]["host"])
        server_port = int(endpoints["server"]["port"])
        client_host = str(endpoints["client"]["host"])
        client_port = int(endpoints["client"]["port"])
    except Exception as exc:
        log.swallow_exception(
            "Error parsing adapter endpoints:\n{0}\n",
            json.repr(endpoints),
            level="info",
        )
        raise RuntimeError("error parsing adapter endpoints: " + str(exc))
    log.info(
        "Adapter is accepting incoming client connections on {0}:{1}",
        client_host,
        client_port,
    )

    _settrace(
        host=server_host,
        port=server_port,
        wait_for_ready_to_run=False,
        block_until_connected=True,
        access_token=server_access_token,
        **settrace_kwargs
    )
    log.info("pydevd is connected to adapter at {0}:{1}", server_host, server_port)
    listen.called = True
    return client_host, client_port

listen.called = False


@_starts_debugging
def connect(address, settrace_kwargs, access_token=None):
    host, port = address
    _settrace(host=host, port=port, client_access_token=access_token, **settrace_kwargs)


class wait_for_client:
    def __call__(self):
        ensure_logging()
        log.debug("wait_for_client()")

        pydb = get_global_debugger()
        if pydb is None:
            raise RuntimeError("listen() or connect() must be called first")

        cancel_event = threading.Event()
        self.cancel = cancel_event.set
        pydevd._wait_for_attach(cancel=cancel_event)

    @staticmethod
    def cancel():
        raise RuntimeError("wait_for_client() must be called first")


wait_for_client = wait_for_client()


def is_client_connected():
    return pydevd._is_attached()


def breakpoint():
    ensure_logging()
    if not is_client_connected():
        log.info("breakpoint() ignored - debugger not attached")
        return
    log.debug("breakpoint()")

    # Get the first frame in the stack that's not an internal frame.
    pydb = get_global_debugger()
    stop_at_frame = sys._getframe().f_back
    while (
        stop_at_frame is not None
        and pydb.get_file_type(stop_at_frame) == pydb.PYDEV_FILE
    ):
        stop_at_frame = stop_at_frame.f_back

    _settrace(
        suspend=True,
        trace_only_current_thread=True,
        patch_multiprocessing=False,
        stop_at_frame=stop_at_frame,
    )
    stop_at_frame = None


def debug_this_thread():
    ensure_logging()
    log.debug("debug_this_thread()")

    _settrace(suspend=False)


def trace_this_thread(should_trace):
    ensure_logging()
    log.debug("trace_this_thread({0!r})", should_trace)

    pydb = get_global_debugger()
    if should_trace:
        pydb.enable_tracing()
    else:
        pydb.disable_tracing()