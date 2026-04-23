# Platform Skills — 平台执行环境封装

本目录存放平台级 Skill 的 Sample 和模板，用于封装不同测试执行环境（如 CodeBuddy CLI、Observable 等）。

## 目录结构

```
platform-skills/
├── [platform_name]/        # 平台 Skill 示例
│   ├── SKILL.md            #   平台适配指令
│   ├── skill.json          #   元数据
│   ├── config/             #   平台配置模板
│   └── scripts/            #   执行脚本
└── README.md               # 本文件
```

## 说明

Platform Skill 负责将 meta-agent 的测试执行流程适配到不同的运行平台。每个 Platform Skill 封装了：

- 平台特定的认证和连接逻辑
- 测试用例的批量执行方式
- 输出格式转换（→ ShareGPT 格式）
- 日志收集和结果回传

## 可用 Sample

### sample_platform

脱敏的 Platform Skill 示例，展示：
- `SKILL.md` 的标准结构和约定
- ShareGPT 对话格式规范（含 tool_call / tool_response）
- 配置模板（`config/platform.yaml.example`）
- 执行脚本骨架（`scripts/execute.py`）

**使用方式**：复制 `sample_platform/` 为你的平台名称，替换 API 调用逻辑即可。
