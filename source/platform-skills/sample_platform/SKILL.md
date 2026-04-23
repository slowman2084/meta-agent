---
name: sample_platform
description: "Platform Skill 示例 — 展示如何将 meta-agent 的测试流程适配到外部执行平台"
---

# sample_platform — Platform Skill 示例

> 这是一个脱敏的 Sample，展示 Platform Skill 的结构和约定。实际使用时请根据你的平台特性修改。

## 角色

你是一个平台适配器，负责将 meta-agent 的测试用例在外部平台上批量执行，并将结果转换为标准格式回传。

## 平台连接

在执行前，确保平台配置正确：

```yaml
# config/platform.yaml（此文件包含敏感信息，已被 .gitignore 排除）
platform:
  name: sample-platform
  api_endpoint: https://api.example.com/v1
  api_key: ${SAMPLE_PLATFORM_API_KEY}
  model: default
  timeout: 120
  max_concurrent: 3
```

## 执行流程

### 1. 加载配置

```bash
# 从环境变量或 config/platform.yaml 读取平台连接信息
```

### 2. 批量执行用例

对 `inputs.json` 中的每条用例：

1. 构造平台 API 请求：
   - `system_prompt`: 目标 Agent/Skill 的 prompt.md / SKILL.md 内容
   - `user_message`: 用例的 Input 字段
   - `model`: 配置中指定的模型
   - `tools`: 目标 Agent 声明的 MCP tools（如有）

2. 发送请求，等待响应

3. 将响应写入标准产物文件：
   - `case_N_actual_result.txt` — 最终文本输出
   - `case_N_sharegpt.json` — ShareGPT 格式的完整对话记录

### 3. ShareGPT 格式规范

```json
{
  "conversations": [
    {"from": "system", "value": "（system prompt 内容）"},
    {"from": "human", "value": "（用户 Input）"},
    {"from": "gpt", "value": "（AI 思考/回复）"},
    {"from": "tool_call", "value": "{\"name\": \"SearchLog\", \"arguments\": {\"TopicId\": \"xxx\"}}"},
    {"from": "tool_response", "value": "[SearchLog]: {\"Results\": [...]}"},
    {"from": "gpt", "value": "（基于 tool 返回的最终回复）"}
  ],
  "metadata": {
    "agent_name": "my-agent",
    "platform": "sample-platform",
    "model": "gpt-4o",
    "timestamp": "2026-04-20T10:00:00Z"
  }
}
```

**关键字段说明**：
- `tool_call`: AI 发起的工具调用，value 为 JSON 字符串（含 `name` 和 `arguments`）
- `tool_response`: 工具返回结果，格式 `[ToolName]: 返回内容`
- `gpt` + `role: "summary"`: 工具调用后的摘要（可选）

### 4. 并发控制

- 默认最多 `max_concurrent` 条用例同时执行
- 每条用例有独立的超时时间
- 失败的用例写入 `case_N_actual_result.txt` 并标记错误

### 5. 重试策略

```python
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒

for attempt in range(1, MAX_RETRIES + 1):
    try:
        response = call_platform_api(...)
        break
    except TimeoutError:
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY * attempt)
        else:
            raise
```

## 产物约定

执行完成后，输出目录结构：

```
[output_dir]/
├── inputs.json                    # 输入（由 meta-plan 生成）
├── case_0_actual_result.txt       # 用例 0 的最终输出
├── case_0_sharegpt.json           # 用例 0 的完整对话记录
├── case_1_actual_result.txt
├── case_1_sharegpt.json
├── ...
└── execution_summary.json         # 执行摘要（成功/失败数、耗时）
```

`execution_summary.json`:
```json
{
  "total": 10,
  "success": 9,
  "failed": 1,
  "failed_cases": ["case_7"],
  "total_time_seconds": 245,
  "avg_time_per_case_seconds": 24.5,
  "platform": "sample-platform",
  "model": "gpt-4o"
}
```

## 创建你自己的 Platform Skill

1. 复制本目录为 `source/platform-skills/your-platform/`
2. 修改 `SKILL.md` 中的平台连接和 API 调用逻辑
3. 在 `scripts/` 下实现执行脚本
4. 在 `config/` 下放置配置模板（`.yaml.example`）
5. 运行 `./venv/bin/python scripts/install.py --platform-skills` 安装
