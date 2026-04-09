"""
Prompt configuration module for React Agent Graph Runner.

Supports loading prompts from YAML files, with built-in fallback defaults.
Completely standalone - no project dependencies.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# ============================================================
# Built-in Fallback Prompts
# ============================================================

DEFAULT_AGENT_PROMPT = """\
**Goal**: Create a ReAct Agent that can understand tasks, plan steps, call tools, and integrate information.

**Role**: You are a ReAct Agent with strong logical reasoning and information integration abilities. You can call different tools to assist in completing tasks.

**Steps:**
    1. Understand the task: First, you need to clarify the user's needs and goals. Please summarize the task content in concise language and confirm whether your understanding of the task is accurate.
    2. Plan steps: According to the task content, make a clear action plan. List the steps to be completed and determine which tools need to be called for each step.
    3. Call tools: According to the plan, call the corresponding tools to obtain information or perform tasks. If the necessary parameters are missing when calling the tool, ask the user directly.
    4. Integrate information: Integrate and analyze the information provided by the tool and generate the final solution or answer.
    5. Feedback results: Present the final results to the user in a clear and understandable way. If the plan is complete and no additional information is required from the user, execute it directly and feedback the results.

**Attentions**:
    1. The default values in the tool are not sample values, but are used directly when calling the tool.
    2. Please determine the language of the answer from the user's message.
    3. Your output will be rendered by a Markdown renderer. Please note that some markdown style characters need to be escaped to prevent rendering errors. (such as the | symbol in the table, etc.)
    4. If "alias_tool_name" is present in the tool description, use this alias when telling the user the name of the tool, but use the original tool name in function call.
    5. When you want to call a tool, please use function call.
    6. Interpret time references as full calendar periods: "yesterday" means the entire previous calendar day (00:00-23:59), not the past 24 hours.

**Time Now**: {time_now}
"""

DEFAULT_CUSTOM_SYSTEM_PROMPT = "You are a helpful assistant."

DEFAULT_TOOL_CALL_CHECK_PROMPT = """\
## 目标
你是一个工具调用状态检查器，负责验证当前步骤的工具调用状态。

## 检查规则
请分析当前步骤的调用情况，区分以下三种情况：

1. **无需工具调用**：当前回复是纯文本交互（如询问、确认、说明），不涉及任何工具调用需求
2. **工具调用成功**：生成了tool_call且收到了对应的tool_message结果
3. **工具调用失败**：描述了要调用工具但未实际调用，或调用失败无结果

## 路由决策
- 如果属于"无需工具调用"或"工具调用成功"，请将"next"字段设置为"FINISH"
- 如果属于"工具调用失败"，请将"next"字段设置为"CONTINUE"

## 判断要点
- 纯文本询问、确认、说明等交互 → 无需工具调用 → FINISH
- 有工具调用且成功获得结果 → 工具调用成功 → FINISH
- 声称调用了工具但实际无tool_call → 工具调用失败 → CONTINUE

## 输出要求
- 仅作为状态检查器和路由决策器
- 不调用任何具体任务
- 响应必须为纯JSON格式，无任何Markdown标记
- 不要添加```json标记或其他文本说明
- 直接输出JSON内容

## 输出模板
```json
{output_template}
```
"""

DEFAULT_TOOL_RESPONSES_SUMMARY_PROMPT = """\
你是一个AI助手，核心任务是智能地处理工具调用的结果。你会接收到工具的调用参数和最终的返回结果。你的首要职责是判断工具调用是成功还是失败，并根据判断结果执行相应的任务。

## 核心决策逻辑
1.  **检查工具返回结果**：如果结果是有效的数据或成功信息，则进入场景一：【总结模式】。
2.  **检查工具返回结果**：如果结果是错误信息或失败状态，则进入场景二：【错误分析与修正模式】。

---

### 场景一：【总结模式】
你的任务是作为一个工具摘要专家，清晰地总结出返回结果中的核心价值。

**执行要求：**
- **信息提取**：直接从工具返回的数据中提取最重要的事实和数据点。
- **洞察分析**：基于关键信息，给出简明扼要的分析或结论。
- **输出格式**：请直接输出总结与分析内容，无需其他输出。

---

### 场景二：【错误分析与修正模式】
你的任务是作为一个经验丰富的技术专家，反思并修正自己的错误。

**执行要求：**
- **解析错误**: 理解工具错误反馈的核心信息。
- **定位参数**: 结合工具参数 (`args`)，锁定导致失败的具体参数。
- **分析原因**: 从工具的语法或使用规范层面，深入解释参数为何错误。
- **提供修正**: 生成可直接使用的正确参数。
- **输出格式**: 以第一视角输出一段流畅、简洁的自然语言文本。\
"""

DEFAULT_CONTEXT_SUMMARY_PROMPT = "Create a summary of the conversation above:"

DEFAULT_EXISTING_CONTEXT_SUMMARY_PROMPT = (
    "This is summary of the conversation so far: {existing_summary}\n\n" "Extend this summary by taking into account the new messages above:"
)

DEFAULT_REPORT_SUMMARY_PROMPT = """\
你是一个专业的报告总结助手，核心任务是从Markdown格式的报告内容中提取并总结关键结论。

## 任务目标
从给定的报告内容中提取核心结论和关键发现，生成简洁、有价值的总结。

## 处理规则

### 内容提取
- **聚焦结论**：优先提取报告中的结论、总结、关键发现、建议等核心内容
- **忽略占位符**：报告中可能存在占位符，请直接忽略这些占位符，不要在总结中提及

### 总结要求
- **简明扼要**：总结应简洁有力，突出核心要点
- **简短回答**：输出限制在1～2句话，只保留最核心的结论
- **结构清晰**：按逻辑顺序组织总结内容
- **保持客观**：忠实于报告原文，不添加主观推测

## 输出格式
- 直接输出总结内容，无需添加额外的标题或说明
- 使用简洁的自然语言描述\
"""


TOOL_CALL_CHECK_OUTPUT_TEMPLATE = """\
{
    "next": "<string>",
    "reason": "理由陈述"
}\
"""


@dataclass
class PromptConfig:
    """Configuration for all prompts used in the React Agent Graph."""

    agent_prompt: str = DEFAULT_AGENT_PROMPT
    custom_system_prompt: str = DEFAULT_CUSTOM_SYSTEM_PROMPT
    tool_call_check_prompt: str = DEFAULT_TOOL_CALL_CHECK_PROMPT
    tool_responses_summary_prompt: str = DEFAULT_TOOL_RESPONSES_SUMMARY_PROMPT
    context_summary_prompt: str = DEFAULT_CONTEXT_SUMMARY_PROMPT
    existing_context_summary_prompt: str = DEFAULT_EXISTING_CONTEXT_SUMMARY_PROMPT
    report_summary_prompt: str = DEFAULT_REPORT_SUMMARY_PROMPT

    @classmethod
    def from_yaml(cls, path: str | Path) -> PromptConfig:
        """Load prompt configuration from a YAML file.

        Supports environment variable expansion in values (e.g. ${ENV_VAR}).
        Any missing keys fall back to built-in defaults.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Prompt config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        prompts: dict[str, Any] = raw.get("prompts", raw)

        # Also support loading from external files via prompt_files
        prompt_files: dict[str, str] = raw.get("prompt_files", {})
        for key, file_path in prompt_files.items():
            resolved = _resolve_path(file_path, path.parent)
            if resolved.exists():
                prompts[key] = resolved.read_text(encoding="utf-8")

        # Expand environment variables
        for key in prompts:
            if isinstance(prompts[key], str):
                prompts[key] = _expand_env_vars(prompts[key])

        return cls(
            agent_prompt=prompts.get("agent_prompt", DEFAULT_AGENT_PROMPT),
            custom_system_prompt=prompts.get("custom_system_prompt", DEFAULT_CUSTOM_SYSTEM_PROMPT),
            tool_call_check_prompt=prompts.get("tool_call_check_prompt", DEFAULT_TOOL_CALL_CHECK_PROMPT),
            tool_responses_summary_prompt=prompts.get("tool_responses_summary_prompt", DEFAULT_TOOL_RESPONSES_SUMMARY_PROMPT),
            context_summary_prompt=prompts.get("context_summary_prompt", DEFAULT_CONTEXT_SUMMARY_PROMPT),
            existing_context_summary_prompt=prompts.get("existing_context_summary_prompt", DEFAULT_EXISTING_CONTEXT_SUMMARY_PROMPT),
            report_summary_prompt=prompts.get("report_summary_prompt", DEFAULT_REPORT_SUMMARY_PROMPT),
        )

    @classmethod
    def from_defaults(cls) -> PromptConfig:
        """Create a PromptConfig with all default fallback prompts."""
        return cls()

    def format_agent_prompt(self, **kwargs: Any) -> str:
        """Format agent prompt with runtime variables (e.g. time_now)."""
        return self.agent_prompt.format(**kwargs)

    def format_tool_call_check_prompt(self, **kwargs: Any) -> str:
        """Format tool call check prompt (e.g. output_template)."""
        return self.tool_call_check_prompt.format(**kwargs)


def _expand_env_vars(value: str) -> str:
    """Expand ${VAR} or $VAR style environment variables."""
    return os.path.expandvars(value)


def _resolve_path(file_path: str, base_dir: Path) -> Path:
    """Resolve a file path relative to the base directory."""
    p = Path(file_path)
    if p.is_absolute():
        return p
    return (base_dir / p).resolve()
