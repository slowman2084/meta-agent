---
name: platform_react_runner
description: 基于 LangGraph 的平台级 ReAct 智能体运行时，用于通过外部平台（而非 IDE Sub Agent）执行 Agent 提示词测试。配置文件中使用 {{AgentName}} 占位符（如 {{cls-log-agent}}），运行前由编排器自动替换为 source/AgentName/prompt.md 的内容。
allowed-tools: 
disable: false
---

# Platform React Runner

基于 LangGraph 的独立可配置 ReAct 智能体运行时，**专门用于通过外部线上平台执行 Agent 提示词测试**。所有代码自包含，零项目内部依赖。

## 与 IDE Sub Agent 测试的区别

| 维度 | IDE Sub Agent 测试 | 平台测试 (本 Skill) |
|------|-------------------|---------------------|
| 执行环境 | IDE 内置 Agent 框架 | 外部 LLM API + MCP 工具 |
| 模型 | IDE 配置的模型 | YAML 中配置的任意模型 |
| 工具 | IDE 内置工具 | MCP 服务器提供的工具 |
| 适用场景 | 开发阶段快速验证 | 线上生产环境测评 |

## 占位符机制

配置文件中使用 `{{AgentName}}` 格式的占位符，其中 **AgentName 就是 `source/` 下的文件夹名**。例如：
- 测试 `cls-log-agent` → 配置文件中写 `{{cls-log-agent}}`
- 测试 `歌词生成系统` → 配置文件中写 `{{歌词生成系统}}`

**查找与替换流程**（由编排器在调用 tester 之前执行）：
1. 根据被测 Agent 名称，构造占位符字符串（如 `{{cls-log-agent}}`）
2. 在 `skills/platform_react_runner/config/` 目录下扫描 YAML 文件，找到包含该占位符的文件
3. 读取 `source/[AgentName]/prompt.md` 的完整内容
4. 将 `{{[AgentName]}}` 替换为实际提示词内容
5. 将替换后的配置写入临时文件（`config_snapshot.yaml`），传给 tester 执行

## 用途

- 在线上生产环境中测试 Agent 提示词的实际表现
- 与 `#test_agent` 和 `#evalooper` 流程集成，作为 IDE Sub Agent 的替代执行方式
- 验证 Agent 在不同模型（如 Qwen、GLM 等）上的兼容性

## 前置条件

### 1. Python 环境
```bash
pip install -r requirements.txt
```

### 2. 配置文件
复制 `config/platform_template.yaml` 并填写实际的 LLM 和 MCP 配置：
- LLM: 模型名称、API Key、Base URL
- MCP 工具服务器（可选）
- `{{AgentName}}` 占位符（如 `{{cls-log-agent}}`）会由编排器自动填充，无需手动修改

## 使用方式

### 命令行运行

```bash
# 单次查询
python scripts/react_agent_runner.py --config config/your_platform.yaml --query "你的测试问题"

# 通过 --prompt-override 在命令行覆盖 custom_system_prompt（等效于替换 {{AgentName}}）
python scripts/react_agent_runner.py --config config/your_platform.yaml \
  -p 'custom_system_prompt=你的Agent提示词内容' \
  --query "你的测试问题"
```

### 作为库使用

```python
from scripts.react_agent_runner import ReactAgentRunner

runner = ReactAgentRunner(config_path="config/your_platform.yaml")
result = runner.invoke("你的测试问题")
print(result["messages"][-1].content)
```

## 配置参考

YAML 配置文件支持以下章节：

- **`llm`**：模型设置（`model`、`api_key`、`base_url`、`temperature`），支持 `${ENV_VAR}` 环境变量展开
- **`mcp_servers`**：MCP 工具服务器列表
- **`prompts`**：提示词模板，其中 `custom_system_prompt` 使用 `{{AgentName}}` 占位符（如 `{{cls-log-agent}}`）
- **`prompt_files`**：从外部文件加载提示词
- **`graph`**：运行时设置（token 阈值、递归限制等）
