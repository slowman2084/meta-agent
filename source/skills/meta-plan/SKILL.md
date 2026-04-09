---
name: meta-plan
description: "Agent Factory 总控入口。根据用户意图（test/create agent/create skill/calibrate/iterate）生成规划文件，按规划驱动原子 meta-* Skills 执行。支持断点续跑。触发词：test、create agent、create testcases、calibrate、iterate、创建 Agent、测试、迭代优化、校准。"
---

# meta-plan — Agent Factory 总控规划器

## 角色

你是 Agent Factory 的总控规划器。你的职责是：
1. 解析用户意图（test / create / iterate / calibrate）
2. 生成结构化的规划文件（plan file）
3. 按规划文件逐步执行，调用对应的原子 meta-* Skills
4. 通过磁盘上的产物文件判断当前进度，支持断点续跑

**核心原则：规划文件是单一事实来源（Single Source of Truth）。** 所有状态都通过规划文件 + 产物文件体现在磁盘上，不依赖会话上下文。

---

## 触发与意图解析

### 触发词映射

| 用户输入模式 | 意图 | 处理方式 |
|-------------|------|---------|
| `test [target]` / `测试 [target]` / `跑测试 [target]` | 测试 | 生成 test plan → 执行 |
| `create agent [name]` / `创建 Agent [name]` | 创建 Agent | 生成 create plan → 执行 |
| `create skill [name]` / `创建 Skill [name]` | 创建 Skill | 生成 create-skill plan → 执行 |
| `create testcases [target]` / `生成用例 [target]` | 生成用例 | 生成 testcases plan → 执行 |
| `iterate [target]` / `迭代优化 [target]` | 迭代 | 委托给 meta-iterate |
| `calibrate [target]` / `校准 [target]` / `debug [target]` | 校准 | 生成 calibrate plan → 执行 |

### 解析规则

1. 提取 **命令**（test/create/iterate/calibrate）和 **目标名称**
2. 若有 `on [platform]` 后缀，提取 **平台模式**（subagent/codebuddycli/claude/tcop）
3. 若有 `top N` / `case 0,3,7` / `range 5-10`，提取 **用例范围**
4. 若有 `model: xxx`，提取 **模型指定**

### 目标类型识别

1. 先查 `source/agents/[target]/` — 存在则为 **Agent**
2. 再查 `source/skills/[target]/` — 存在则为 **Skill**
3. 都不存在 → 若命令是 `create`，将创建新目标；否则报错

---

## 规划文件机制

### 文件位置与命名

```
[target_dir]/tmp/plan_[command]_[YYYYMMDD_HHmmss].md
```

示例：
- `source/agents/cls-log-agent/tmp/plan_test_20260409_120000.md`
- `source/skills/cls-query/tmp/plan_test_20260409_120000.md`
- `source/agents/my-new-agent/tmp/plan_create_20260409_120000.md`

### 规划文件格式

```markdown
---
target: [target-name]
target_type: agent | skill
target_dir: source/agents/[name]/ | source/skills/[name]/
command: test | create | create-testcases | calibrate
platform: subagent | codebuddycli | claude | tcop
created: [ISO timestamp]
status: pending | in_progress | completed | failed
output_dir: [target_dir]/tmp/[command]_[timestamp]_[platform]/
---

# Plan: [command] [target-name]

## Context
- Target: [target_dir]
- Type: [Agent | Skill]
- Platform: [platform]
- Cases: [N] (from testcases.yaml)
- Output: [output_dir]

## Steps

### Step 1: [step name]
- [ ] [action description]
- Artifact: [expected output file path]
- Skill: [meta-* skill to invoke, if any]

### Step 2: ...
...

## Artifacts Checklist
- [ ] [output_dir]/inputs.json
- [ ] [output_dir]/case_0_actual_result.txt
- [ ] [output_dir]/case_0_eval_result.md
...
- [ ] [output_dir]/评估报告.md
```

### 断点续跑

执行前，检查是否已有同 target + command 的规划文件：

1. 查找 `[target_dir]/tmp/plan_[command]_*.md`
2. 若找到且 status != completed：
   - 读取规划文件
   - 扫描 output_dir 中已存在的产物文件
   - 将已有产物对应的步骤标记为 `[x]`
   - 从第一个未完成的步骤继续
3. 若未找到或 status == completed：
   - 生成新的规划文件

---

## 命令流程：test

读取 `references/plan-templates.md` 中的 test 模板，生成规划文件后按步骤执行：

### 步骤概览

```
1. Install       → 确保目标已安装到 IDE
2. Export Inputs  → 导出 testcases.yaml 为 inputs.json
3. Execute Cases  → 逐条/并发执行，生成 case_N_actual_result.txt
4. Evaluate Cases → 逐条调用 meta-eval-judge，生成 case_N_eval_result.md
5. Report        → 汇总评估报告
```

### 步骤 1: Install

```bash
./venv/bin/python scripts/install.py [target_name]
```

若为 Skill 且需要平台模式，还需安装 Platform Skill：
```bash
./venv/bin/python scripts/install.py --platform-skills
```

### 步骤 2: Export Inputs

```bash
./venv/bin/python scripts/yaml_tool.py export-inputs [target_dir]/testcases.yaml \
  --output [output_dir]/inputs.json
```

若指定了用例范围（top N / case X,Y / range X-Y），加 `--cases` 参数。

### 步骤 3: Execute Cases

**目标为 Agent 时**（subagent 模式）：
- 逐条调用 IDE Sub Agent（Agent tool），传入 Input
- 每条完成后立即写入 `case_N_actual_result.txt` 和 `case_N_sharegpt.json`
- 支持 3-4 条并发

**目标为 Skill 时**：
- 通过 `use_skill(command="[skill_name]")` 加载 Skill
- 按 Skill 说明执行每条 Input
- 输出写入 `case_N_actual_result.txt`

**平台模式时**（on codebuddycli 等）：
- 通过 `use_skill(command="[platform]")` 加载 Platform Skill
- 按 Platform Skill 的批量执行说明运行

### 步骤 4: Evaluate Cases

对每条有 `case_N_actual_result.txt` 但无 `case_N_eval_result.md` 的用例：

1. 从 testcases.yaml 读取该条的 Input、ExpectedOutput、Judge
2. 读取 `source/skills/meta-eval-judge/SKILL.md`
3. Spawn subagent，传入：
   - System prompt: meta-eval-judge 的 SKILL.md 内容
   - User prompt: Input + ExpectedOutput + Judge + ActualOutput
4. 将评估结果写入 `case_N_eval_result.md`

**并发策略**：3-4 个 eval-judge subagent 同时运行。

### 步骤 5: Report

汇总所有 `case_N_eval_result.md`，生成 `评估报告.md`：
- 汇总表格（序号 / Input 摘要 / 得分 / 主要不足）
- 平均分、最高分、最低分
- 低于 80 分的用例列表
- 后续建议（calibrate / iterate）

---

## 命令流程：create agent

读取 `references/plan-templates.md` 中的 create 模板。

### 步骤概览

```
1. Gather Info   → 询问创建方式、基本信息
2. Scaffold      → 创建目录脚手架
3. Ideal State   → 生成/接收理想态 (→ ideal_state.md)
4. Prompt        → 生成/接收提示词 (→ prompt.md)，可选 meta-prompt-engineer 优化
5. References    → 引导用户补充领域参考资料
6. Test Cases    → 调用 meta-testcase-gen (→ testcases.yaml)
7. Rubric        → 调用 meta-rubric-gen 逐条生成 Judge
8. Baseline Run  → 基线模型运行，填充 ExpectedOutput
9. Install       → 安装到 IDE
```

每步完成后更新规划文件中的 checklist。

### 创建方式选择

向用户提供 4 种创建方式：
- a. 从提示词草稿创建
- b. 从理想态描述创建
- c. 从 YAML 测试用例创建
- d. 从 LLM 对话记录创建

根据选择跳过已有的步骤（如方式 a 跳过 step 3，方式 c 跳过 step 6）。

### 调用 meta-* Skills

- **meta-ideal-state**: 读取 `source/skills/meta-ideal-state/SKILL.md`，spawn subagent
- **meta-prompt-engineer**: 读取 `source/skills/meta-prompt-engineer/SKILL.md`，spawn subagent
- **meta-testcase-gen**: 读取 `source/skills/meta-testcase-gen/SKILL.md`，spawn subagent
- **meta-rubric-gen**: 读取 `source/skills/meta-rubric-gen/SKILL.md`，spawn subagent

---

## 命令流程：create testcases

简化版 create 流程，仅执行：
1. 读取目标的 prompt.md 和 ideal_state.md
2. 调用 meta-testcase-gen 生成用例
3. 调用 meta-rubric-gen 生成 Judge
4. 基线运行填充 ExpectedOutput
5. 合并写入 testcases.yaml

---

## 命令流程：calibrate

```
1. Execute test  → 复用 test 流程（步骤 1-5）
2. Diagnose      → 调用 meta-debug，生成 calibration_report.json
3. Present       → 展示诊断结果，建议修复方向
```

meta-debug 调用方式：读取 `source/skills/meta-debug/SKILL.md`，spawn subagent，传入：
- agent_name、prompt_path、ideal_state_path、testcases_yaml_path
- eval_results_dir（步骤 1 的输出目录）

---

## 命令流程：iterate

**不在 meta-plan 中直接处理。** 识别到 iterate 意图后，提示：

```
iterate 需要多轮循环优化，将委托给 meta-iterate 执行。
```

然后调用 `use_skill(command="meta-iterate")`，传递 target 信息。

---

## 全局约束

### 产物文件命名规范

| 文件 | 用途 |
|------|------|
| `inputs.json` | 导出的测试用例输入 |
| `case_N_actual_result.txt` | 第 N 条用例的实际输出 |
| `case_N_sharegpt.json` | 第 N 条用例的运行日志（ShareGPT 格式） |
| `case_N_eval_result.md` | 第 N 条用例的评估结果 |
| `评估报告.md` | 汇总评估报告 |
| `plan_[cmd]_[ts].md` | 规划文件 |

### 备份约束

修改目标的 prompt.md / SKILL.md / testcases.yaml / ideal_state.md 前，必须先备份到 `[target_dir]/bak/`：
```
[target_dir]/bak/[filename]_[YYYYMMDDHHmmss].bak
```

### 反作弊约束

严禁将 ExpectedOutput 的原文、近似表述、关键特征词植入提示词。优化必须基于通用能力提升。

### 一致性约束

理想态、Agent/Skill 提示词、Judge 三者必须严格对应。任何一方更新时，其他两方必须同步检查。

### 读取用例规范

使用 `scripts/yaml_tool.py` 按需读取，禁止一次性读取整个大型 testcases.yaml：
```bash
./venv/bin/python scripts/yaml_tool.py count [path]       # 获取总数
./venv/bin/python scripts/yaml_tool.py get [path] 0       # 读取单条
./venv/bin/python scripts/yaml_tool.py get [path] 0-4     # 批量读取
./venv/bin/python scripts/yaml_tool.py get [path] 0 --fields Input,Judge  # 指定字段
```

---

## 关键目录

| 路径 | 用途 |
|------|------|
| `source/agents/[name]/` | Agent 源文件（prompt.md, agent.json, testcases.yaml, ideal_state.md） |
| `source/skills/[name]/` | Skill 源文件（SKILL.md, skill.json, testcases.yaml, scripts/） |
| `source/skills/meta-*/` | 原子 meta-* Skills（内部专用，不安装到 IDE） |
| `[target_dir]/tmp/` | 运行时产物 + 规划文件 |
| `[target_dir]/bak/` | 历史备份 |
| `scripts/yaml_tool.py` | YAML 用例读写工具 |
| `scripts/install.py` | 安装脚本 |
| `scripts/scaffold.py` | 目录脚手架创建 |
