"""
React Agent Graph Runner - Standalone runtime for React Agent Graph.

This module provides a fully independent implementation of the React Agent Graph
that can be configured via YAML and run as a standalone script.

Dependencies: langchain-openai, langgraph, pyyaml, mcp (see requirements.txt)
No project-internal imports.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from inspect import signature
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Dict, List, Literal, Optional, Sequence, Tuple, cast

import yaml
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, AnyMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.managed import IsLastStep, RemainingSteps
from langgraph.prebuilt.tool_node import ToolNode
from langgraph.utils.runnable import RunnableCallable
try:
    from prompt_config import DEFAULT_CONTEXT_SUMMARY_PROMPT, DEFAULT_EXISTING_CONTEXT_SUMMARY_PROMPT, TOOL_CALL_CHECK_OUTPUT_TEMPLATE, PromptConfig
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from prompt_config import DEFAULT_CONTEXT_SUMMARY_PROMPT, DEFAULT_EXISTING_CONTEXT_SUMMARY_PROMPT, TOOL_CALL_CHECK_OUTPUT_TEMPLATE, PromptConfig
from pydantic import BaseModel, Field, create_model
from typing_extensions import Annotated, TypedDict

# ============================================================
# Logging Setup
# ============================================================
logger = logging.getLogger("react_agent_runner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)


# ============================================================
# TodoList Models & Constants
# ============================================================
TODO_LIST_UPDATE_TOOL_NAME = "__Update_Todos__"
TODO_LIST_UPDATE_TOOL_DESC = """
**使用此工具为当前会话创建和管理结构化的任务列表。这有跟踪进度、组织复杂任务并展现细致周全的工作态度。**

**注意：除了首次创建待办事项时，不要告知用户您正在更新待办事项，直接更新即可。**

### 任务状态和管理

1. **任务状态：**
- pending：尚未开始（冻结状态，不可提前触碰）
- in_progress：正在进行中（一次只能处理一个任务）
- completed：已成功完成

2. **任务管理：**
- 实时更新状态 - 完成后立即标记为已完成
- 一次只能处理一个 in_progress 任务
- 完成当前任务后再开始新任务
- 禁止在一个回合内同时完成当前任务和启动下一任务
- 调用本工具后必须立即停止当前回合，等待下一轮系统调度
"""


class TodoItemStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


STATUS_TO_CHINESE = {
    "pending": "尚未开始",
    "in_progress": "正在进行中",
    "completed": "已成功完成",
}


class TodoItemSchema(BaseModel):
    id: str = Field(description="任务ID")
    name: str = Field(description="任务名称", max_length=100)
    status: TodoItemStatus = Field(description="任务状态", default=TodoItemStatus.PENDING)
    should_fold: bool = Field(description="是否进行折叠展示")

    class Config:
        use_enum_values = True


class TodoUpdateToolSchema(BaseModel):
    todos: List[TodoItemSchema] = Field(description="待办事项列表")


class TodoListUpdateSchema(BaseModel):
    current_todo_id: Optional[str] = Field(description="当前待办 ID")
    updated_todo_list: List[TodoItemSchema] = Field(description="更新后的任务列表")


def _create_todo_update_tool() -> StructuredTool:
    """Create the __Update_Todos__ fake tool that always returns '更新完毕'."""

    def _update_todos(**kwargs: Any) -> str:
        return "更新完毕"

    tool = StructuredTool.from_function(
        func=_update_todos,
        name=TODO_LIST_UPDATE_TOOL_NAME,
        description=TODO_LIST_UPDATE_TOOL_DESC,
        args_schema=TodoUpdateToolSchema,
    )
    tool.metadata = {"agent_skip_tool_summary": True}
    return tool


# ============================================================
# TodoList Helper Functions
# ============================================================
def extract_last_todo_list(messages: Sequence[BaseMessage]) -> list[TodoItemSchema]:
    """Extract todo list from the last AIMessage's tool calls."""
    if len(messages) >= 2 and isinstance(messages[-1], ToolMessage) and isinstance(messages[-2], AIMessage):
        last_ai: AIMessage = messages[-2]
        for tool_call in last_ai.tool_calls:
            if tool_call["name"] != TODO_LIST_UPDATE_TOOL_NAME:
                continue
            try:
                todo_update = TodoUpdateToolSchema(**tool_call["args"])
                return todo_update.todos
            except Exception as e:
                logger.error(f"Failed to parse TodoList: {e}")
    return []


def get_todo_reminder_lines(todo_list: list[TodoItemSchema] | None = None) -> list[str]:
    """Generate markdown-formatted reminder lines for current todo list."""
    if not todo_list or len(todo_list) == 0:
        return []

    lines = [
        "以下是您当前针对此任务的提醒列表。请随着任务的进展及时更新这些提醒。",
        "| # | 内容 | 状态 | 折叠 |",
        "|---|---------|--------|--------|",
    ]

    for idx, item in enumerate(todo_list):
        escaped_content = item.name.replace("\\", "\\\\").replace("|", "\\|")
        status = item.status.value if isinstance(item.status, TodoItemStatus) else item.status
        should_fold = "是" if item.should_fold else "否"
        lines.append(f"| {idx + 1} | {escaped_content} | {status}({STATUS_TO_CHINESE[status]}) | {should_fold} |")

    all_completed = all(item.status == TodoItemStatus.COMPLETED for item in todo_list)
    lines.append("")
    lines.append(
        f"重要提示：{'当前还有未完成的任务状态，' if not all_completed else ''}当任务状态发生变化时，请记得调用 `{TODO_LIST_UPDATE_TOOL_NAME}` 工具来更新待办项列表。"
    )
    return lines


# ============================================================
# State Definition
# ============================================================
class AgentState(TypedDict):
    """The state of the agent."""

    is_last_step: IsLastStep
    remaining_steps: RemainingSteps
    messages: Annotated[Sequence[BaseMessage], add_messages]
    agent_tool_call_check_times: int
    need_break: bool
    context: dict[str, Any]
    todo_list: list[TodoItemSchema]
    current_todo_id: str | None


# ============================================================
# Node Names
# ============================================================
AGENT_NODE = "agent"
TOOLS_NODE = "tools"
TODO_LIST_UPDATE_NODE = "todo_list_update"
TOOL_RESPONSES_SUMMARY_NODE = "tool_responses_summary"
AGENT_TOOL_CALL_CHECK_NODE = "agent_tool_call_check"
CONDENSE_NODE = "condense"

# Constants
MAX_TOOL_CALL_CHECK_TIMES = 5
MAX_RESPONSES_SUMMARY_TOKENS = 80000

# MCP Constants
SSE_TRANSPORT_TYPE = "sse"
STREAMABLE_HTTP_TRANSPORT_TYPE = "streamable_http"
McpTransportType = Literal["sse", "streamable_http"]

BASIC_TYPE: Dict[str, type | None] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
    "null": None,
}


# ============================================================
# MCP Client (Standalone)
# ============================================================
def _run_async(coro: Any, timeout: float = 120) -> Any:
    """Run async coroutine in a separate thread (for sync context)."""
    result_container: list[Any] = [None]
    exception_container: list[Exception] = []

    async def _wrapped():
        return await asyncio.wait_for(coro, timeout)

    def _execute():
        try:
            result_container[0] = asyncio.run(_wrapped())
        except Exception as e:
            exception_container.append(e)

    thread = threading.Thread(target=_execute)
    thread.start()
    thread.join(timeout + 10)

    if thread.is_alive():
        raise TimeoutError(f"MCP operation timed out after {timeout}s")
    if exception_container:
        raise exception_container[0]
    return result_container[0]


@asynccontextmanager
async def _mcp_client(
    transport_type: str,
    url: str,
    headers: Dict[str, Any] | None = None,
    timeout: float = 30,
    sse_read_timeout: float = 60,
) -> AsyncGenerator:
    """Create an MCP client connection (supports sse and streamable_http)."""
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamablehttp_client

    if transport_type == SSE_TRANSPORT_TYPE:
        async with sse_client(url, headers, timeout, sse_read_timeout) as (read, write):
            yield read, write, None
    elif transport_type == STREAMABLE_HTTP_TRANSPORT_TYPE:
        async with streamablehttp_client(url, headers, timedelta(seconds=timeout), timedelta(seconds=sse_read_timeout), True) as (
            read,
            write,
            callback,
        ):
            yield read, write, callback
    else:
        raise ValueError(f"Invalid MCP transport type: {transport_type}")


async def _list_mcp_tools(
    transport_type: str,
    url: str,
    headers: Dict[str, Any] | None = None,
    timeout: float = 30,
    sse_read_timeout: float = 60,
) -> list[dict[str, Any]]:
    """Connect to an MCP server and list available tools."""
    from mcp.client.session import ClientSession as _MCP_ClientSession  # noqa: F811

    async with _mcp_client(transport_type, url, headers, timeout, sse_read_timeout) as (read, write, _):
        async with _MCP_ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.inputSchema if hasattr(t, "inputSchema") else {},
                }
                for t in tools_result.tools
            ]


async def _call_mcp_tool_async(
    transport_type: str,
    url: str,
    name: str,
    arguments: dict[str, Any] | None = None,
    headers: Dict[str, Any] | None = None,
    timeout: float = 30,
    sse_read_timeout: float = 60,
) -> str:
    """Call a single MCP tool and return the result as string."""
    logger.debug(f"MCP tool call: {name}({arguments}) -> {url}")
    from mcp.client.session import ClientSession as _MCP_ClientSession  # noqa: F811
    from mcp.types import CallToolRequest, CallToolRequestParams, CallToolResult, ClientRequest, EmbeddedResource, ImageContent, TextContent

    # Collect result inside context managers, process outside to avoid
    # exceptions breaking anyio TaskGroup cleanup.
    text_parts: list[str] = []
    is_error = False

    async with _mcp_client(transport_type, url, headers, timeout, sse_read_timeout) as (read, write, _):
        async with _MCP_ClientSession(read, write) as session:
            await session.initialize()
            result = await session.send_request(
                ClientRequest(
                    CallToolRequest(
                        params=CallToolRequestParams(name=name, arguments=arguments),
                    )
                ),
                CallToolResult,
                request_read_timeout_seconds=timedelta(seconds=sse_read_timeout),
            )

            for content in result.content:
                if isinstance(content, TextContent):
                    text_parts.append(content.text)
                elif isinstance(content, ImageContent):
                    text_parts.append(f"[Image: {content.mimeType}]")
                elif isinstance(content, EmbeddedResource):
                    text_parts.append(f"[Resource: {content.resource.uri}]")

            is_error = bool(result.isError)

    # Process result outside context managers
    output = "\n".join(text_parts) if len(text_parts) != 1 else text_parts[0] if text_parts else ""
    logger.debug(f"MCP tool result: {name} -> {output[:200]}{'...' if len(output) > 200 else ''}")

    if is_error:
        raise ToolException(f"MCP tool error: {output}")

    return output


def _convert_input_schema_to_fields(input_schema: Dict[str, Any]) -> Dict[str, Tuple[type, Any]]:
    """Convert MCP tool inputSchema (JSON Schema) into Pydantic field definitions."""
    schema_fields = {}
    if not isinstance(input_schema, dict) or "properties" not in input_schema:
        return schema_fields

    required = input_schema.get("required", [])
    for field_name, props in input_schema["properties"].items():
        if field_name.startswith("_"):
            continue

        type_str = props.get("type", "string")
        if type_str == "array":
            item_type_str = props.get("items", {}).get("type", "")
            props_type = list[BASIC_TYPE.get(item_type_str, Any)] if item_type_str in BASIC_TYPE else list  # type: ignore
        else:
            props_type = BASIC_TYPE.get(type_str, Any)

        field_kwargs = {}
        field_params = signature(Field).parameters
        for key, value in props.items():
            if key in field_params and key != "type" and key != "default":
                field_kwargs[key] = value

        # Extract the default value from the MCP schema if present
        schema_default = props.get("default")

        is_required = field_name in required
        if not is_required and props_type:
            # Only widen to Optional (union with None) when there is no schema default
            if schema_default is None:
                props_type = props_type | None  # type: ignore

        if is_required:
            schema_fields[field_name] = (props_type, Field(..., **field_kwargs))  # type: ignore
        else:
            # Use the MCP schema default if available, otherwise None
            default_value = schema_default if schema_default is not None else None
            schema_fields[field_name] = (props_type, Field(default=default_value, **field_kwargs))  # type: ignore

    return schema_fields


def create_mcp_tools(mcp_servers_config: list[dict[str, Any]]) -> list[BaseTool]:
    """Create LangChain tools from MCP server configurations.

    Each MCP server config should have:
        - url: MCP server URL
        - transport_type: "sse" or "streamable_http" (default: "streamable_http")
        - headers: optional dict of HTTP headers
        - timeout: connection timeout (default: 5)
        - sse_read_timeout: read timeout (default: 300)
    """
    if not mcp_servers_config:
        return []

    tools: list[BaseTool] = []

    for server_conf in mcp_servers_config:
        server_url = server_conf.get("url", "")
        transport_type = server_conf.get("transport_type", STREAMABLE_HTTP_TRANSPORT_TYPE)
        headers = server_conf.get("headers")
        timeout = server_conf.get("timeout", 30)
        sse_read_timeout = server_conf.get("sse_read_timeout", 60)
        allowed_tools: set[str] | None = set(server_conf["allowed_tools"]) if "allowed_tools" in server_conf else None

        if not server_url:
            logger.warning("MCP server config missing 'url', skipping.")
            continue

        logger.debug(f"Connecting to MCP server: {server_url} (transport: {transport_type})")

        try:
            mcp_tool_defs: list[dict[str, Any]] = _run_async(
                _list_mcp_tools(transport_type, server_url, headers, timeout, sse_read_timeout),
                timeout=timeout + sse_read_timeout,
            )
        except Exception as e:
            logger.error(f"Failed to list tools from MCP server {server_url}: {e}")
            continue

        if not mcp_tool_defs:
            logger.warning(f"No tools found from MCP server: {server_url}")
            continue

        logger.debug(f"Found {len(mcp_tool_defs)} tools from MCP server: {server_url}")

        for tool_def in mcp_tool_defs:
            tool_name = tool_def["name"]

            # Filter by allowed_tools if specified
            if allowed_tools is not None and tool_name not in allowed_tools:
                logger.debug(f"  Skipping MCP tool (not in allowed_tools): {tool_name}")
                continue

            tool_description = tool_def.get("description", "")
            tool_input_schema = tool_def.get("input_schema", {})

            # Build Pydantic args_schema
            schema_fields = _convert_input_schema_to_fields(tool_input_schema)

            if schema_fields:
                args_model = create_model(f"{tool_name}_Args", **schema_fields)  # type: ignore[call-overload]
            else:
                args_model = None

            # Capture closure variables
            _url = server_url
            _transport = transport_type
            _headers = headers
            _timeout = timeout
            _sse_timeout = sse_read_timeout
            _tool_name = tool_name

            def _make_invoke_fn(url, transport, hdr, tout, sse_tout, tname):
                def _invoke(**kwargs: Any) -> str:
                    # Filter out None values to avoid sending null for optional
                    # params that the MCP server may not handle correctly.
                    filtered = {k: v for k, v in kwargs.items() if v is not None} if kwargs else {}
                    return _run_async(
                        _call_mcp_tool_async(
                            transport_type=transport,
                            url=url,
                            name=tname,
                            arguments=filtered if filtered else None,
                            headers=hdr,
                            timeout=tout,
                            sse_read_timeout=sse_tout,
                        ),
                        timeout=tout + sse_tout,
                    )

                return _invoke

            invoke_fn = _make_invoke_fn(_url, _transport, _headers, _timeout, _sse_timeout, _tool_name)

            # Create the LangChain tool using StructuredTool.from_function
            t = StructuredTool.from_function(
                func=invoke_fn,
                name=tool_name,
                description=tool_description or f"MCP tool: {tool_name}",
                args_schema=args_model,
                infer_schema=args_model is None,
                handle_tool_error=True,
            )
            tools.append(t)
            logger.debug(f"  Registered MCP tool: {tool_name}")

    return tools


# ============================================================
# Node Output Formatting
# ============================================================
def format_node_output(node_name: str, output: dict[str, Any] | None) -> str:
    """Format a node's intermediate output for display."""
    lines = [f"\n{'='*60}", f"  Node: {node_name}", f"{'='*60}"]

    if output is None:
        lines.append("  (no output)")
        lines.append(f"{'─'*60}")
        return "\n".join(lines)

    messages = output.get("messages", [])
    for msg in messages:
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                lines.append(f"  [AI Tool Calls]:")
                for tc in msg.tool_calls:
                    args_str = json.dumps(tc.get("args", {}), ensure_ascii=False)
                    lines.append(f"    -> {tc.get('name', '?')}({args_str})")
            if msg.content:
                content = str(msg.content)
                if len(content) > 500:
                    content = content[:500] + "...(truncated)"
                lines.append(f"  [AI]: {content}")
        elif isinstance(msg, ToolMessage):
            content = str(msg.content)
            if len(content) > 500:
                content = content[:500] + "...(truncated)"
            lines.append(f"  [Tool {msg.name}]: {content}")
        elif isinstance(msg, HumanMessage):
            lines.append(f"  [Human]: {msg.content}")

    # Non-message keys
    for key, value in output.items():
        if key == "messages":
            continue
        if key == "goto":
            lines.append(f"  [Route]: -> {value}")
        elif key == "llm_input_messages":
            lines.append(f"  [Condensed Messages]: {len(value)} messages")
        elif key == "context":
            summary = value.get("running_summary", {}).get("summary", "")
            if summary:
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                lines.append(f"  [Context Summary]: {summary}")
        else:
            lines.append(f"  [{key}]: {value}")

    lines.append(f"{'─'*60}")
    return "\n".join(lines)


# ============================================================
# Condense Node (Context Summarization)
# ============================================================
class CondenseNode(RunnableCallable):
    """Simplified condense node for context compression via summarization."""

    def __init__(
        self,
        *,
        model: BaseChatModel,
        token_counter: Callable = count_tokens_approximately,
        threshold_tokens: int = 70000,
        max_summary_tokens: int = 20000,
        input_messages_key: str = "messages",
        output_messages_key: str = "llm_input_messages",
        context_summary_prompt: str = DEFAULT_CONTEXT_SUMMARY_PROMPT,
        existing_context_summary_prompt: str = DEFAULT_EXISTING_CONTEXT_SUMMARY_PROMPT,
    ) -> None:
        super().__init__(self._func, name="condense", trace=False)
        self.model = model
        self.token_counter = token_counter
        self.threshold_tokens = threshold_tokens
        self.max_summary_tokens = max_summary_tokens
        self.input_messages_key = input_messages_key
        self.output_messages_key = output_messages_key
        self.context_summary_prompt = ChatPromptTemplate.from_messages(
            [
                ("placeholder", "{messages}"),
                ("user", context_summary_prompt),
            ]
        )
        self.existing_context_summary_prompt = ChatPromptTemplate.from_messages(
            [
                ("placeholder", "{messages}"),
                ("user", existing_context_summary_prompt),
            ]
        )
        self.final_llm_input_prompt = ChatPromptTemplate.from_messages(
            [
                ("placeholder", "{system_message}"),
                ("system", "Summary of the conversation so far:\n\n {summary}"),
                ("placeholder", "{messages}"),
            ]
        )
        self.hard_limit_tokens = self.threshold_tokens * 2 - self.max_summary_tokens

    def _func(self, input: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
        messages = input.get(self.input_messages_key, [])
        context = input.get("context", {})
        running_summary = context.get("running_summary")

        # Filter large tool messages
        messages = self._filter_tool_messages(messages)

        # Summarize if needed
        result = self._summarize_messages(messages, running_summary=running_summary)

        state_update: dict[str, Any] = {self.output_messages_key: result["messages"]}
        if result.get("running_summary"):
            state_update["context"] = {**context, "running_summary": result["running_summary"]}

        return state_update

    def _filter_tool_messages(self, messages: list[AnyMessage]) -> list[AnyMessage]:
        """Replace oversized tool messages with a placeholder."""
        filter_placeholder = (
            "Attention: The tool output is too long and may be incomplete. " "Please refer directly to the content summary in the next message."
        )
        result = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                tokens = self.token_counter([msg])
                if tokens > self.threshold_tokens:
                    new_msg = msg.model_copy(deep=True)
                    new_msg.content = filter_placeholder
                    result.append(new_msg)
                    continue
            result.append(msg)
        return result

    def _summarize_messages(
        self,
        messages: list[AnyMessage],
        running_summary: dict | None = None,
    ) -> dict[str, Any]:
        system_message = None
        if messages and isinstance(messages[0], SystemMessage):
            system_message = messages[0]
            messages = messages[1:]

        if not messages:
            final = [system_message] + messages if system_message else messages
            return {"messages": final, "running_summary": running_summary}

        threshold = self.threshold_tokens
        next_unsummarized = 0
        summarized_ids: set[str] = set()

        if running_summary:
            summarized_ids = running_summary.get("summarized_message_ids", set())
            threshold -= self.token_counter([SystemMessage(content=running_summary["summary"])])
            for i, msg in enumerate(messages):
                if msg.id == running_summary.get("last_summarized_message_id"):
                    next_unsummarized = i + 1
                    break

        accumulated = 0
        cutoff = max(0, next_unsummarized - 1)
        for i in range(next_unsummarized, len(messages)):
            accumulated += self.token_counter([messages[i]])
            if accumulated <= threshold:
                cutoff = i

        if accumulated <= self.threshold_tokens:
            msgs_to_summarize = []
        else:
            msgs_to_summarize = messages[next_unsummarized : cutoff + 1]

        if msgs_to_summarize:
            if running_summary:
                prompt = cast(
                    ChatPromptValue,
                    self.existing_context_summary_prompt.invoke(
                        {
                            "messages": msgs_to_summarize,
                            "existing_summary": running_summary["summary"],
                        }
                    ),
                )
            else:
                prompt = cast(
                    ChatPromptValue,
                    self.context_summary_prompt.invoke({"messages": msgs_to_summarize}),
                )
            resp = self.model.invoke(prompt.messages)
            summary_text = resp.content

            new_ids = summarized_ids | {m.id for m in msgs_to_summarize}
            running_summary = {
                "summary": summary_text,
                "summarized_message_ids": new_ids,
                "last_summarized_message_id": msgs_to_summarize[-1].id,
            }
            next_unsummarized += len(msgs_to_summarize)

        if running_summary:
            include_sys = bool(system_message and not (running_summary.get("summary", "") in (system_message.content or "")))
            result = cast(
                ChatPromptValue,
                self.final_llm_input_prompt.invoke(
                    {
                        "system_message": [system_message] if include_sys else [],
                        "summary": running_summary["summary"],
                        "messages": messages[next_unsummarized:],
                    }
                ),
            )
            return {"messages": result.messages, "running_summary": running_summary}
        else:
            final = [system_message] + messages if system_message else messages
            return {"messages": final, "running_summary": None}


# ============================================================
# Graph Construction
# ============================================================
def create_react_agent_graph(
    model: BaseChatModel,
    tools: list[BaseTool],
    prompt_config: PromptConfig,
    *,
    max_threshold_tokens: int = 70000,
    max_summary_tokens: int = 20000,
    recursion_limit: int = 25,
    enable_condense: bool = True,
    enable_todolist: bool = True,
    debug: bool = False,
    name: str | None = "react_agent",
) -> CompiledStateGraph:
    """Build and compile the React Agent graph.

    Args:
        model: The OpenAI chat model (already instantiated).
        tools: List of LangChain tools to bind.
        prompt_config: Prompt configuration for all graph stages.
        max_threshold_tokens: Token threshold for condense node.
        max_summary_tokens: Max tokens for summary output.
        recursion_limit: Max recursion steps for the graph.
        enable_condense: Whether to enable the condense (context compression) node.
        enable_todolist: Whether to enable the todolist management feature.
        debug: Enable debug mode.
        name: Name for the compiled graph.

    Returns:
        CompiledStateGraph ready to invoke.
    """
    # Format prompts with runtime values
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_agent_prompt = prompt_config.format_agent_prompt(time_now=time_now)
    formatted_tool_call_check_prompt = prompt_config.format_tool_call_check_prompt(
        output_template=TOOL_CALL_CHECK_OUTPUT_TEMPLATE,
    )
    custom_system_prompt = prompt_config.custom_system_prompt
    tool_responses_summary_prompt = prompt_config.tool_responses_summary_prompt
    report_summary_prompt = prompt_config.report_summary_prompt

    # Create tool node (add todo update tool if enabled)
    all_tools = list(tools)
    if enable_todolist:
        all_tools.append(_create_todo_update_tool())

    tool_node = ToolNode(all_tools)
    tool_classes = list(tool_node.tools_by_name.values())
    tool_calling_enabled = len(tool_classes) > 0

    # Bind tools to model
    if tool_calling_enabled:
        model_with_tools = model.bind_tools(tool_classes, tool_choice="auto")
    else:
        model_with_tools = model

    # State schema
    if enable_condense:

        class GraphState(AgentState):
            llm_input_messages: list[AnyMessage]

    else:
        GraphState = AgentState  # type: ignore

    # ---- Node Functions ----

    def _get_messages(state: Any) -> list[BaseMessage]:
        if enable_condense:
            return (state.get("llm_input_messages") or []) or state.get("messages", [])
        return state.get("messages", [])

    def call_agent(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        messages = _get_messages(state)

        input_messages = [
            SystemMessage(content=formatted_agent_prompt),
            SystemMessage(content=custom_system_prompt),
        ] + list(messages)

        # Inject todo reminder if todolist is enabled
        if enable_todolist:
            todo_list: list[TodoItemSchema] = state.get("todo_list", [])
            reminder_lines = get_todo_reminder_lines(todo_list)
            if reminder_lines:
                reminder_section = "\n## REMINDERS\n\n====\n\n" + "\n".join(reminder_lines)
                input_messages.append(SystemMessage(content=reminder_section))

        response = cast(AIMessage, model_with_tools.invoke(input_messages, config))
        response.name = name

        agent_tool_call_check_times = state.get("agent_tool_call_check_times", 0)
        if response.tool_calls:
            agent_tool_call_check_times = 0

        return {
            "messages": [response],
            "agent_tool_call_check_times": agent_tool_call_check_times,
        }

    def call_tool_responses_summary(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        # Always read from state["messages"] (not condensed llm_input_messages)
        # because this node runs BEFORE condense, so llm_input_messages is stale.
        messages = state.get("messages", [])

        # Find latest tool messages and corresponding AI message
        tool_messages: list[ToolMessage] = []
        ai_message: AIMessage | None = None
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if isinstance(msg, ToolMessage):
                tool_messages.insert(0, msg)
            elif isinstance(msg, AIMessage) and ai_message is None:
                ai_message = msg
                break

        if not ai_message or not ai_message.tool_calls or not tool_messages:
            return {"messages": []}

        # Build tool content list (with token limit)
        tools_content: list[dict[str, str]] = []
        token_count = 0
        for msg in reversed(tool_messages):
            t = count_tokens_approximately([msg])
            if (token_count + t) <= MAX_RESPONSES_SUMMARY_TOKENS:
                token_count += t
                tools_content.append({"name": msg.name or "unknown", "content": str(msg.content)})
            else:
                remain = MAX_RESPONSES_SUMMARY_TOKENS - token_count
                tools_content.append(
                    {
                        "name": msg.name or "unknown",
                        "content": str(msg.content)[: remain * 4] + "...(内容过大，已截断)",
                    }
                )
                break
        tools_content = list(reversed(tools_content))

        # Check per-tool metadata flags (matching original implementation)
        # Build a name -> tool lookup
        tools_by_name: dict[str, BaseTool] = {t.name: t for t in all_tools}
        for tc in tools_content:
            tool_instance = tools_by_name.get(tc["name"])
            if tool_instance and hasattr(tool_instance, "metadata") and tool_instance.metadata:
                if tool_instance.metadata.get("agent_break_directly") is True:
                    return {"need_break": True}
                elif tool_instance.metadata.get("agent_skip_tool_summary") is True:
                    return {"messages": []}

        ai_tool_calls = ai_message.tool_calls

        # Build messages for summary model
        user_msg1 = HumanMessage(content=f"【AI工具调用】: {json.dumps(ai_tool_calls, ensure_ascii=False)}")
        user_msgs = [HumanMessage(content=f"【工具 `{tc['name']}` 返回结果】: {tc['content']}") for tc in tools_content]
        input_msgs = [SystemMessage(content=tool_responses_summary_prompt), user_msg1] + user_msgs

        response = cast(AIMessage, model.invoke(input_msgs, config))
        response.name = name
        return {"messages": [response]}

    def call_tool_call_check(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        """Check if the agent's last response needs retry or is finished."""
        # Skip if max times
        times = state.get("agent_tool_call_check_times", 0)
        if times >= MAX_TOOL_CALL_CHECK_TIMES:
            return {"goto": END}

        # Todo-aware: if there are pending/in_progress todos, route back to agent
        if enable_todolist:
            todo_list: list[TodoItemSchema] = state.get("todo_list", [])
            if todo_list and len(todo_list) > 0:
                last_todo = todo_list[-1]
                last_status = last_todo.status.value if isinstance(last_todo.status, TodoItemStatus) else last_todo.status
                if last_status in (TodoItemStatus.PENDING.value, TodoItemStatus.IN_PROGRESS.value):
                    logger.debug(f"Todo-aware check: pending/in_progress todo found, routing back to agent")
                    return {
                        "goto": AGENT_NODE,
                        "agent_tool_call_check_times": times + 1,
                    }

        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None

        system_msg = SystemMessage(content=formatted_tool_call_check_prompt)
        check_msgs = [system_msg, last_message] if last_message else [system_msg]

        try:
            response = model.invoke(check_msgs, config)
            content = str(response.content).strip()
            # Try to parse JSON
            parsed = json.loads(content)
            next_action = parsed.get("next", "").lower()
        except Exception:
            next_action = "finish"

        if next_action == "finish":
            return {"goto": END}
        elif next_action == "continue":
            return {
                "goto": AGENT_NODE,
                "agent_tool_call_check_times": times + 1,
            }
        else:
            return {"goto": END}

    # ---- TodoList Update Node ----

    def call_todo_list_update(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        """Update todo list state based on the last __Update_Todos__ tool call."""
        current_todo_list: list[TodoItemSchema] = state.get("todo_list", [])
        messages = state.get("messages", [])
        new_todo_list = extract_last_todo_list(messages)

        if not new_todo_list:
            return {}

        # Build index for fast lookup
        current_todo_dict = {todo.id: todo for todo in current_todo_list}

        # Merge: update existing, add new
        merged_todos: dict[str, TodoItemSchema] = {}
        current_todo_id = ""

        # Keep all non-PENDING old todos
        for todo in current_todo_list:
            if todo.status != TodoItemStatus.PENDING:
                merged_todos[todo.id] = todo

        # Apply new updates (override or add)
        for new_todo in new_todo_list:
            merged_todos[new_todo.id] = new_todo
            if new_todo.status == TodoItemStatus.IN_PROGRESS:
                current_todo_id = new_todo.id

        # Build final list maintaining original order
        final_todo_list: list[TodoItemSchema] = []

        # Existing items in original order
        for todo in current_todo_list:
            if todo.id in merged_todos:
                final_todo_list.append(merged_todos[todo.id])

        # New items not in original list
        for todo_id, todo in merged_todos.items():
            if todo_id not in current_todo_dict:
                final_todo_list.append(todo)

        # Find IN_PROGRESS if not already found
        if not current_todo_id:
            for todo in reversed(final_todo_list):
                if todo.status == TodoItemStatus.IN_PROGRESS:
                    current_todo_id = todo.id
                    break

        if not final_todo_list:
            return {}

        logger.debug(f"Todo list updated: {len(final_todo_list)} items, current_todo_id={current_todo_id}")
        return {"todo_list": final_todo_list, "current_todo_id": current_todo_id}

    # ---- Routing ----

    def should_continue(state: AgentState) -> str:
        messages = state.get("messages", [])
        if not messages:
            return AGENT_TOOL_CALL_CHECK_NODE

        last_message = messages[-1]
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return AGENT_TOOL_CALL_CHECK_NODE
        return TOOLS_NODE

    def check_route(state: dict[str, Any]) -> str:
        return state.get("goto", END)

    def check_need_break(goto: str):
        def _check(state: dict[str, Any]) -> str:
            if state.get("need_break", False):
                return END
            return goto

        return _check

    # ---- Build Graph ----
    workflow = StateGraph(GraphState)

    if enable_condense:
        condense_node = CondenseNode(
            model=model,
            threshold_tokens=max_threshold_tokens,
            max_summary_tokens=max_summary_tokens,
            input_messages_key="messages",
            output_messages_key="llm_input_messages",
            context_summary_prompt=prompt_config.context_summary_prompt,
            existing_context_summary_prompt=prompt_config.existing_context_summary_prompt,
        )
        workflow.add_node(CONDENSE_NODE, condense_node)

    workflow.add_node(AGENT_NODE, RunnableCallable(call_agent))
    workflow.add_node(AGENT_TOOL_CALL_CHECK_NODE, RunnableCallable(call_tool_call_check))

    if tool_calling_enabled:
        workflow.add_node(TOOLS_NODE, tool_node)
        workflow.add_node(
            TOOL_RESPONSES_SUMMARY_NODE,
            RunnableCallable(call_tool_responses_summary),
        )

        if enable_todolist:
            # TOOLS -> TODO_LIST_UPDATE -> TOOL_RESPONSES_SUMMARY
            workflow.add_node(TODO_LIST_UPDATE_NODE, RunnableCallable(call_todo_list_update))
            workflow.add_edge(TOOLS_NODE, TODO_LIST_UPDATE_NODE)
            workflow.add_edge(TODO_LIST_UPDATE_NODE, TOOL_RESPONSES_SUMMARY_NODE)
        else:
            # TOOLS -> TOOL_RESPONSES_SUMMARY
            workflow.add_edge(TOOLS_NODE, TOOL_RESPONSES_SUMMARY_NODE)

        if enable_condense:
            workflow.add_edge(TOOL_RESPONSES_SUMMARY_NODE, CONDENSE_NODE)
        else:
            workflow.add_edge(TOOL_RESPONSES_SUMMARY_NODE, AGENT_NODE)

    # Conditional edges from agent
    if tool_calling_enabled:
        workflow.add_conditional_edges(
            AGENT_NODE,
            should_continue,
            path_map=[TOOLS_NODE, AGENT_TOOL_CALL_CHECK_NODE],
        )
    else:
        workflow.add_edge(AGENT_NODE, AGENT_TOOL_CALL_CHECK_NODE)

    # check node routes to END or back to agent
    workflow.add_conditional_edges(
        AGENT_TOOL_CALL_CHECK_NODE,
        check_route,
        path_map={END: END, AGENT_NODE: CONDENSE_NODE if enable_condense else AGENT_NODE},
    )

    # Entry
    if enable_condense:
        workflow.set_entry_point(CONDENSE_NODE)
        workflow.add_conditional_edges(
            CONDENSE_NODE,
            check_need_break(AGENT_NODE),
            path_map=[AGENT_NODE, END],
        )
    else:
        workflow.set_entry_point(AGENT_NODE)

    graph = workflow.compile(debug=debug, name=name)

    # Print graph structure
    try:
        logger.debug(f"Graph Mermaid:\n{graph.get_graph().draw_mermaid()}")
    except Exception:
        pass

    return graph


# ============================================================
# Configuration Loader
# ============================================================
def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load the full YAML config file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def create_openai_model(llm_config: dict[str, Any]) -> ChatOpenAI:
    """Create a ChatOpenAI instance from config dict."""
    api_key = llm_config.get("api_key", "")
    if api_key.startswith("${") and api_key.endswith("}"):
        env_var = api_key[2:-1]
        api_key = os.environ.get(env_var, "")
    elif api_key.startswith("$"):
        api_key = os.environ.get(api_key[1:], "")

    base_url = llm_config.get("base_url", None)
    if base_url and base_url.startswith("${"):
        env_var = base_url[2:-1]
        base_url = os.environ.get(env_var, base_url)

    return ChatOpenAI(
        model=llm_config.get("model", "Qwen3_235B_A22B_Instruct_2507"),
        api_key=api_key,  # type: ignore
        base_url=base_url,
        temperature=llm_config.get("temperature", 0.7),
        streaming=True,
        max_retries=llm_config.get("max_retries", 8),
    )


# ============================================================
# Runner
# ============================================================
class ReactAgentRunner:
    """High-level runner that ties config, model, tools, and graph together."""

    def __init__(self, config_path: str | Path | None = None, config_dict: dict[str, Any] | None = None):
        if config_path:
            self.config = load_config(config_path)
        elif config_dict:
            self.config = config_dict
        else:
            self.config = {}

        # Load prompts
        if config_path:
            self.prompt_config = PromptConfig.from_yaml(config_path)
        else:
            self.prompt_config = PromptConfig.from_defaults()

        # Create model
        llm_config = self.config.get("llm", {})
        self.model = create_openai_model(llm_config)

        # Load MCP tools
        self.tools: list[BaseTool] = []
        mcp_servers_config = self.config.get("mcp_servers", [])
        if mcp_servers_config:
            self.tools.extend(create_mcp_tools(mcp_servers_config))

        # Graph config
        graph_config = self.config.get("graph", {})
        self.recursion_limit = graph_config.get("recursion_limit", 256)
        self.graph = create_react_agent_graph(
            model=self.model,
            tools=self.tools,
            prompt_config=self.prompt_config,
            max_threshold_tokens=graph_config.get("max_threshold_tokens", 70000),
            max_summary_tokens=graph_config.get("max_summary_tokens", 20000),
            recursion_limit=self.recursion_limit,
            enable_condense=graph_config.get("enable_condense", True),
            enable_todolist=graph_config.get("enable_todolist", True),
            debug=graph_config.get("debug", False),
            name=graph_config.get("name", "react_agent"),
        )

    def _runtime_config(self, config: RunnableConfig | None = None) -> RunnableConfig:
        """Build runtime config with recursion_limit."""
        base: RunnableConfig = {"recursion_limit": self.recursion_limit}
        if config:
            base.update(config)
        return base

    def invoke(self, user_message: str, config: RunnableConfig | None = None, verbose: bool = True) -> dict[str, Any]:
        """Run the graph with a single user message, with optional streaming output."""
        input_data = {
            "messages": [HumanMessage(content=user_message)],
        }
        run_config = self._runtime_config(config)
        if verbose:
            final_state: dict[str, Any] = {}
            current_node = ""
            streaming_content = False
            for stream_mode, chunk in self.graph.stream(input_data, run_config, stream_mode=["messages", "updates"]):
                if stream_mode == "messages":
                    msg_chunk, metadata = chunk  # type: ignore[assignment]
                    node = metadata.get("langgraph_node", "")
                    # Print node header on first token of a new node
                    if node != current_node:
                        if streaming_content:
                            print()  # newline after previous stream
                            streaming_content = False
                        current_node = node
                        print(f"\n{'='*60}\n  Node: {node}\n{'='*60}")
                    # Only process AIMessageChunk for streaming
                    if not isinstance(msg_chunk, AIMessageChunk):
                        if hasattr(msg_chunk, "content") and msg_chunk.content:
                            print(msg_chunk.content, end="", flush=True)
                            streaming_content = True
                        continue
                    # Stream AI content tokens
                    if msg_chunk.content:
                        print(msg_chunk.content, end="", flush=True)
                        streaming_content = True
                    # Show tool calls as they appear
                    if msg_chunk.tool_call_chunks:
                        for tc in msg_chunk.tool_call_chunks:
                            if tc.get("name"):
                                if streaming_content:
                                    print()
                                    streaming_content = False
                                print(f"  [Tool Call]: {tc['name']}({tc.get('args', '')})", end="", flush=True)
                                streaming_content = True
                            elif tc.get("args"):
                                print(tc["args"], end="", flush=True)
                                streaming_content = True
                elif stream_mode == "updates":
                    # Updates give us the full node output for state accumulation
                    for node_name, node_output in chunk.items():
                        if node_output is None:
                            continue
                        if "messages" in node_output:
                            final_state.setdefault("messages", []).extend(node_output["messages"])
                        for k, v in node_output.items():
                            if k != "messages":
                                final_state[k] = v
            if streaming_content:
                print()  # final newline
            print(f"{'─'*60}")
            return final_state
        else:
            return self.graph.invoke(input_data, run_config)

    async def ainvoke(self, user_message: str, config: RunnableConfig | None = None) -> dict[str, Any]:
        """Async run the graph with a single user message."""
        input_data = {
            "messages": [HumanMessage(content=user_message)],
        }
        return await self.graph.ainvoke(input_data, self._runtime_config(config))

    def stream(self, user_message: str, config: RunnableConfig | None = None):
        """Stream the graph execution with per-node updates."""
        input_data = {
            "messages": [HumanMessage(content=user_message)],
        }
        return self.graph.stream(input_data, self._runtime_config(config), stream_mode="updates")

    def interactive(self):
        """Run an interactive chat session with node-level output."""
        print("=" * 60)
        print("React Agent Graph Runner - Interactive Mode")
        print("Type 'quit' or 'exit' to stop, 'clear' to reset history.")
        print("Type 'verbose off' to hide node details, 'verbose on' to show.")
        print("=" * 60)

        messages: list[BaseMessage] = []
        verbose = True
        while True:
            try:
                user_input = input("\n[You]: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                print("Bye!")
                break
            if user_input.lower() == "clear":
                messages = []
                print("[System]: History cleared.")
                continue
            if user_input.lower() == "verbose off":
                verbose = False
                print("[System]: Verbose mode OFF - only final answers shown.")
                continue
            if user_input.lower() == "verbose on":
                verbose = True
                print("[System]: Verbose mode ON - showing node intermediate outputs.")
                continue

            messages.append(HumanMessage(content=user_input))
            input_data = {"messages": messages}

            try:
                if verbose:
                    result_messages = []
                    current_node = ""
                    streaming_content = False
                    for stream_mode_tag, chunk in self.graph.stream(input_data, self._runtime_config(), stream_mode=["messages", "updates"]):
                        if stream_mode_tag == "messages":
                            msg_chunk, metadata = chunk  # type: ignore[assignment]
                            node = metadata.get("langgraph_node", "")
                            if node != current_node:
                                if streaming_content:
                                    print()
                                    streaming_content = False
                                current_node = node
                                print(f"\n{'='*60}\n  Node: {node}\n{'='*60}")
                            if not isinstance(msg_chunk, AIMessageChunk):
                                if hasattr(msg_chunk, "content") and msg_chunk.content:
                                    print(msg_chunk.content, end="", flush=True)
                                    streaming_content = True
                                continue
                            if msg_chunk.content:
                                print(msg_chunk.content, end="", flush=True)
                                streaming_content = True
                            if msg_chunk.tool_call_chunks:
                                for tc in msg_chunk.tool_call_chunks:
                                    if tc.get("name"):
                                        if streaming_content:
                                            print()
                                            streaming_content = False
                                        print(f"  [Tool Call]: {tc['name']}({tc.get('args', '')})", end="", flush=True)
                                        streaming_content = True
                                    elif tc.get("args"):
                                        print(tc["args"], end="", flush=True)
                                        streaming_content = True
                        elif stream_mode_tag == "updates":
                            for node_name, node_output in chunk.items():
                                if node_output and "messages" in node_output:
                                    result_messages.extend(node_output["messages"])
                    if streaming_content:
                        print()

                    # Show final answer
                    last_ai = None
                    for msg in reversed(result_messages):
                        if isinstance(msg, AIMessage) and msg.content:
                            last_ai = msg
                            break
                    if last_ai:
                        print(f"\n{'*'*60}")
                        print(f"  FINAL ANSWER:")
                        print(f"{'*'*60}")
                        print(f"  {last_ai.content}")
                        print(f"{'*'*60}")
                    messages = messages[:-1] + result_messages
                else:
                    result = self.graph.invoke(input_data, self._runtime_config())
                    result_messages = result.get("messages", [])
                    last_ai = None
                    for msg in reversed(result_messages):
                        if isinstance(msg, AIMessage) and msg.content:
                            last_ai = msg
                            break
                    if last_ai:
                        print(f"\n[Agent]: {last_ai.content}")
                    messages = list(result_messages)
            except Exception as e:
                logger.error(f"Error during invoke: {e}")
                print(f"\n[Error]: {e}")


# ============================================================
# CLI Entry Point
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="React Agent Graph Runner")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default=None,
        help="Single query to run (non-interactive mode)",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        default=False,
        help="Run in interactive chat mode",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug logging",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=True,
        help="Show node intermediate outputs (default: True)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Hide node intermediate outputs (only show final result)",
    )
    parser.add_argument(
        "--prompt-override",
        "-p",
        type=str,
        action="append",
        default=[],
        help=(
            "Override a prompt at runtime. Format: key=value. "
            "Supported keys: agent_prompt, custom_system_prompt, tool_call_check_prompt, "
            "tool_responses_summary_prompt, context_summary_prompt, "
            "existing_context_summary_prompt, report_summary_prompt. "
            "Can be specified multiple times."
        ),
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    verbose = not args.quiet

    # Parse prompt overrides into a dict
    prompt_overrides: dict[str, str] = {}
    for item in args.prompt_override:
        eq_idx = item.find("=")
        if eq_idx <= 0:
            logger.warning(f"Invalid --prompt-override format (expected key=value): {item!r}")
            continue
        key = item[:eq_idx].strip()
        value = item[eq_idx + 1:]
        prompt_overrides[key] = value

    # Determine config path
    config_path = args.config
    if config_path is None:
        # Try default locations
        for default in ["config.yaml", "config/example_config.yaml"]:
            p = Path(__file__).parent.parent / default
            if p.exists():
                config_path = str(p)
                break

    if config_path is None:
        logger.warning("No config file found. Using defaults (requires OPENAI_API_KEY env var).")
        runner = ReactAgentRunner(
            config_dict={
                "llm": {
                    "model": "Qwen3_235B_A22B_Instruct_2507",
                    "api_key": os.environ.get("OPENAI_API_KEY", ""),
                }
            }
        )
    else:
        logger.info(f"Loading config from: {config_path}")
        runner = ReactAgentRunner(config_path=config_path)

    # Apply prompt overrides from CLI
    if prompt_overrides:
        valid_keys = set(runner.prompt_config.__dataclass_fields__)
        for key, value in prompt_overrides.items():
            if key not in valid_keys:
                logger.warning(f"Unknown prompt key: {key!r}. Valid keys: {sorted(valid_keys)}")
                continue
            setattr(runner.prompt_config, key, value)
            logger.info(f"Prompt override applied: {key}")
        # Rebuild graph with updated prompts
        graph_config = runner.config.get("graph", {})
        runner.graph = create_react_agent_graph(
            model=runner.model,
            tools=runner.tools,
            prompt_config=runner.prompt_config,
            max_threshold_tokens=graph_config.get("max_threshold_tokens", 70000),
            max_summary_tokens=graph_config.get("max_summary_tokens", 20000),
            recursion_limit=runner.recursion_limit,
            enable_condense=graph_config.get("enable_condense", True),
            enable_todolist=graph_config.get("enable_todolist", True),
            debug=graph_config.get("debug", False),
            name=graph_config.get("name", "react_agent"),
        )

    if args.interactive or args.query is None:
        runner.interactive()
    else:
        result = runner.invoke(args.query, verbose=verbose)
        if not verbose:
            messages = result.get("messages", [])
            for msg in messages:
                if isinstance(msg, AIMessage) and msg.content:
                    print(msg.content)


if __name__ == "__main__":
    main()
