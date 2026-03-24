# 5 分钟让 AI 学会写出金句 —— Meta-Agent 快速体验

> **⏱️ 预计耗时**：环境准备 5 分钟 + 流程体验 20~30 分钟（取决于执行方式）
>
> 你将用 5 条"流行歌金句"测试用例，体验 Agent 的创建、测试、迭代优化全流程。
> 
> **OpenClaw 用户**：无需安装 CLI 工具，clone 项目后即可在浏览器中完成全部流程。

---

### 📖 设计原则

**CLI / IDE 方式**：每一步都是一个独立的 CLI 调用（`-p` 模式）。每步**执行完后**，读取生成的文件，把有趣的内容展示给用户。

**OpenClaw 方式**：每一步通过 spawn sub agent 完成。你（OpenClaw）读取 `source/meta-*/prompt.md` 作为各 sub agent 的 system prompt，spawn 时通过 `tools` 参数赋予 `file_read`、`file_write`、`list_directory` 能力。因此中间产物（提示词、输出、评分）**写入文件系统**，与 CLI / IDE 方式共享相同的目录结构（`source/[AgentName]/`）。

成就感来自"看到 AI 具体写了什么、创作了什么金句、分数怎么变的"，而不是一句"已完成"。

**金句评估逻辑**：Agent 每次需**原创** **10 句**候选金句。评分主要看**原创性**（不得照搬已有歌词）、**意境契合度**（是否抓住了关键词的情感内核）和**文学质量**（修辞、韵律、画面感）。ExpectedOutput 是风格标杆，评估时看 Agent 原创的 10 句中**是否有至少 1 句达到标杆水准**。

### 🚨 三条铁律（OpenClaw 必须遵守）

> **铁律 1：用例是尺子，绝对不能改。**
>
> 5 条测试用例（Input + ExpectedOutput + Judge）在第 2 步生成后就是固定的评估标尺。整个迭代过程中 **严禁修改、调整、替换任何用例内容**。即使 eval-judge 的评估报告中标注了 `[rubric]`（rubric 可能不合理）或 `[testcase]`（ExpectedOutput 可能有误），你也 **绝对不能据此修改用例或评分标准**。唯一允许改的是 **Agent 的提示词**。如果某条用例持续低分，说明提示词还不够好，继续优化提示词，而不是降低标准。
>
> **铁律 2：优化必须保证通用性，严禁过拟合。**
>
> 迭代优化的目标是提升 Agent 的 **通用能力**，而不是让它"记住"这 5 条用例的答案。每次优化提示词时，必须确保改动对 **从未见过的新输入** 同样有效。具体来说：禁止在提示词中嵌入与测试用例高度相似的 few-shot 示例；禁止针对某条用例的具体关键词做特殊处理；所有改动必须是通用能力层面的提升（如推理框架、格式规范、边界处理等）。
>
> **铁律 3：全自动执行，不停下来问用户。**
>
> 除非遇到不可恢复的错误（如 sub agent spawn 失败），否则 **不要停下来询问用户"是否继续""要不要执行下一步"**。整个流程从第 2 步到第 5 步应当一气呵成、自动执行。每个步骤完成后，直接展示结果并立即进入下一步。用户选择了执行本文档，就意味着授权你自动完成全部流程。

---

## 🎯 你将完成的事

```
5 条歌词金句用例（每条要求 Agent 原创 10 句候选金句）
    → AI 反推出提示词（看看它怎么理解"原创金句"）
    → 首次测试，看 Agent 给每条需求写了哪 10 句金句（具体内容！）
    → 迭代优化 3 轮，每轮看提示词改了什么、分数涨了多少
    → 最终对比初始 vs 最终提示词，理解 AI 的优化策略
```

---

## 前置要求

### 选择你的体验方式

Meta-Agent 支持三种体验方式，选**任意一种**即可：

| 方式 | 需要安装 | 适合谁 | 体验完整度 |
|------|---------|--------|-----------|
| **🅰️ OpenClaw** | 无需安装（浏览器即可） | 想快速感受、不想装环境的人 | ⭐⭐⭐⭐⭐ |
| **🅱️ AI IDE** | Cursor / CodeBuddy / Claude Code | 已有 IDE 的开发者 | ⭐⭐⭐⭐⭐ |
| **🅲 CLI** | CodeBuddy CLI 或 Claude Code CLI | 喜欢终端和脚本化的人 | ⭐⭐⭐⭐⭐ |

#### 🅰️ OpenClaw 方式（零门槛）

**不需要安装任何工具**。OpenClaw 会通过 spawn sub agent（spawn 时赋予 `file_read`、`file_write`、`list_directory` 工具）来调用 Meta-Agent 的各个 Sub Agent（如 meta-prompt-engineer、meta-eval-judge 等）。

工作原理：
- 本文档（`README_FORCLAW.md`）本身就是 OpenClaw 的执行手册
- OpenClaw 读取 `source/meta-*/prompt.md` 作为各 sub agent 的 system prompt
- 通过 spawn sub agent 实现 **提示词生成 → 评估打分 → 迭代优化** 的完整流程
- 编排规则（rules）已内嵌在本文档的步骤说明中，无需单独安装到 IDE
- 每个 sub agent 有特定的输入格式（使用 `【】` 格式标记），本文档已在每步中提供了精确的模板
- **Spawn 时赋予文件读写能力**：每次 spawn sub agent 时，通过 `tools` 参数赋予 `file_read`、`file_write`、`list_directory` 工具。这样 sub agent 可以直接读写本地文件系统，中间产物写入 `source/[AgentName]/` 目录，与 CLI / IDE 方式共享相同的目录结构

> 💡 **与 CLI / IDE 的区别**：OpenClaw 不支持 MCP 工具调用和 shell 命令执行，但 spawn 时赋予的文件读写工具使其可以完成本 demo 的全部流程。需要 MCP 的 Agent（如日志分析）仍需 CLI 或 IDE。

#### 🅱️ IDE 方式

在 IDE（Cursor / CodeBuddy / Claude Code）中直接打开项目，用对话框输入触发词（如 `创建 Agent`）即可。IDE 会自动加载 rules 和 sub agent 配置。

#### 🅲 CLI 方式

| CLI 工具 | 安装方式 | 说明 |
|---------|---------|------|
| **CodeBuddy CLI** | 随 CodeBuddy IDE 安装 | 推荐，体验最完整 |
| **Claude Code CLI** | `npm install -g @anthropic-ai/claude-code` | 需要 Anthropic API Key |

---

## 第 0 步：环境准备

### 🅰️ OpenClaw 方式

**Clone 项目到本地**（OpenClaw spawn sub agent 时赋予文件读写工具，需要本地工作区）：

```bash
git clone <your-repo-url>
cd meta-agent
```

> 💡 不需要创建虚拟环境或安装 Python 依赖。OpenClaw 只需要读取仓库中的提示词文件（`source/meta-*/prompt.md`），并将产物写入 `source/` 目录。
>
> 如果 OpenClaw 无法直接访问本地文件系统，也可以通过 `web_fetch` 读取 GitHub Raw URL 获取提示词文件：

| Sub Agent | GitHub Raw URL |
|-----------|---------------|
| 提示词生成/优化专家 | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-prompt-engineer/prompt.md` |
| 提示词反作弊审查专家 | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-reviewer/prompt.md` |
| 评估打分专家 | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-eval-judge/prompt.md` |
| 评分标准生成专家 | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-rubric-gen/prompt.md` |

### 🅱️🅲 CLI / IDE 方式

```bash
git clone <your-repo-url>
cd meta-agent
```

**阅读并执行 [SETUP.md](SETUP.md) 的 Step 1 ~ Step 3**（创建虚拟环境 → 安装依赖 → 分发规则和内置 Agent）。

完成后验证：
```bash
./venv/bin/python scripts/verify_setup.py
```

所有关键项 ✅ 即可。MCP 项为 ⚠️ 是正常的，本 demo 不需要。

确认你有以下 CLI 工具**至少一个**可用：

```bash
# 检查 CodeBuddy CLI
CodeBuddy --version

# 或检查 Claude Code CLI
claude --version
```

> 本 demo **不需要 MCP、不需要额外 API Key**。

---

## 第 1 步：准备测试用例文件

### 🅰️ OpenClaw 方式

与 CLI / IDE 方式相同，在项目根目录创建 `demo_testcases.yaml`（使用 `file_write` 写入下方内容）。

### 🅱️🅲 CLI / IDE 方式

在项目根目录创建 `demo_testcases.yaml`：

```yaml
meta:
  count: 5
  notice: "原创金句助手 demo 用例 —— Agent 每次需原创 10 句候选金句（禁止照搬已有歌词）"
cases:
  - Input: |
      围绕关键词"跳楼机"和爱情主题，原创 10 句歌词金句。要求：不得照搬已有歌词，必须是全新创作。
    ExpectedOutput: |
      风格标杆（不要求复现，评估时作为意境和质量参考）：Baby 我们的感情好像跳楼机，让我突然地升空又急速落地 —— 要抓住"忽上忽下、刺激又不安"的爱情意象
    Judge: ""

  - Input: |
      围绕关键词"世界赠予我的"和人生主题，原创 10 句歌词金句。要求：不得照搬已有歌词，必须是全新创作。
    ExpectedOutput: |
      风格标杆（不要求复现，评估时作为意境和质量参考）：世界赠予我虫鸣，也赠予我雷霆；赠我弯弯一枚月，也赠予我晚星 —— 要抓住"馈赠的对比与感恩"的人生意象
    Judge: ""

  - Input: |
      围绕关键词"字字句句都是暗恋"和爱情主题，原创 10 句歌词金句。要求：不得照搬已有歌词，必须是全新创作。
    ExpectedOutput: |
      风格标杆（不要求复现，评估时作为意境和质量参考）：他字字未提喜欢你，你句句都是我愿意 —— 要抓住"言外之意、欲说还休"的暗恋意象
    Judge: ""

  - Input: |
      围绕关键词"敬自己"和人生主题，原创 10 句歌词金句。要求：不得照搬已有歌词，必须是全新创作。
    ExpectedOutput: |
      风格标杆（不要求复现，评估时作为意境和质量参考）：敬自己一杯酒，往后余生不回头 —— 要抓住"自我和解、释然前行"的人生意象
    Judge: ""

  - Input: |
      围绕关键词"月亮"和"窗台"，原创 10 句歌词金句。要求：不得照搬已有歌词，必须是全新创作。
    ExpectedOutput: |
      风格标杆（不要求复现，评估时作为意境和质量参考）：若是月亮还没来，路灯也可照窗台 —— 要抓住"等待中的日常温柔"的生活意象
    Judge: ""
```

> 📝 **评分核心逻辑**：Agent 需**原创** **10 句**候选金句（严禁照搬已有歌词）。ExpectedOutput 是风格/意境标杆，不要求文字复现。评分主要维度：**原创性**（是否全新创作）、**意境契合度**（是否抓住了关键词的情感内核）、**文学质量**（修辞、韵律、画面感）。`Judge` 留空，后面由 AI 自动生成对应的评分标准（Rubrics）。

---

## 第 2 步：从测试用例创建 Agent

### 🅰️ OpenClaw 方式

先创建 Agent 目录结构，然后依次 spawn 2 个 sub agent 来完成创建：

**2.0 创建目录脚手架**

使用 `file_write` 创建以下目录和文件：
- `source/lyrics-golden-lines/tmp/`（运行时产物）
- `source/lyrics-golden-lines/bak/`（备份）
- `source/lyrics-golden-lines/changelog.md`（变更日志，初始内容为空）

**2a. Spawn `meta-prompt-engineer`** —— 生成提示词

1. 用 `file_read` 读取 `source/meta-prompt-engineer/prompt.md` 作为 system prompt
2. 用 `file_read` 读取 `demo_testcases.yaml`，从中提取 5 条用例的 Input 和 ExpectedOutput
3. Spawn sub agent，**spawn 时通过 `tools` 参数赋予 `file_read`、`file_write`、`list_directory`**，传入以下 user message（注意使用 `【】` 格式标记，这是该 sub agent 要求的输入格式）：

> 💡 **后续所有 spawn 均按此方式赋予 tools**，不再重复说明。

```
【理想态描述】
该 Agent 的功能是：根据用户给定的关键词和主题，原创 10 句高质量歌词金句。
好的原创金句 Agent 应具备：
- 准确理解用户意图（情绪、意象、场景）
- 每次稳定输出 10 句候选金句，全部为原创（严禁照搬已有歌词）
- 金句具有文学质量（修辞、韵律、画面感）
- 候选中至少有 1 句达到 ExpectedOutput 风格标杆的水准

【示例用例】
[从 demo_testcases.yaml 读取，按以下格式组织每条：]
Input: [cases[i].Input]
→ 最佳参考：[cases[i].ExpectedOutput]
```

> 💡 理想态描述和示例用例均从 `demo_testcases.yaml` 提取组装，无需手动硬编码。

🎉 **从 sub agent 返回内容中提取产物并写入文件**：

- prompt-engineer 的输出会包含 `===PROMPT===` 标记，该标记**之后的内容**就是生成的 Agent 提示词
- 将提示词写入 `source/lyrics-golden-lines/prompt.md`
- 将【理想态描述】部分写入 `source/lyrics-golden-lines/ideal_state.md`

**2b. Spawn `meta-rubric-gen`** —— 逐条生成评分标准

1. 用 `file_read` 读取 `source/meta-rubric-gen/prompt.md` 作为 system prompt
2. 用 `file_read` 读取 `demo_testcases.yaml`，遍历每条用例
3. **逐条** spawn（每条用例一次），传入（使用 `【】` 格式标记）：

```
【Input】
[从 demo_testcases.yaml 读取 cases[i].Input]

【任务约束】
核心评分逻辑：Agent 需原创 10 句候选金句（严禁照搬已有歌词）。评分主要维度：原创性（全新创作）、意境契合度（是否抓住关键词的情感内核）、文学质量（修辞、韵律、画面感）。以下是风格标杆（不要求文字复现，用于评估意境和质量水准）。
风格标杆：[从 demo_testcases.yaml 读取 cases[i].ExpectedOutput]
```

> **不需要传 agent_name**（本 demo 无 references 目录），rubric-gen 会直接基于 Input 内容生成评分标准。

🎉 **将 5 条 Judge 评分标准写回 `demo_testcases.yaml`** 中对应用例的 `Judge` 字段（替换空字符串）。同时复制一份到 `source/lyrics-golden-lines/testcases.yaml`。

**2c. 记录变更日志**

向 `source/lyrics-golden-lines/changelog.md` 写入初始创建记录。

> **第 2 步完成后，立即自动进入第 3 步。不要停下来询问用户。**

### 🅱️🅲 CLI / IDE 方式

```bash
CodeBuddy --dangerously-skip-permissions -p "
请执行 create_agent 流程：

1. 创建方式：c（从 YAML 测试用例创建）
2. YAML 文件路径：demo_testcases.yaml
3. Agent 名称：lyrics-golden-lines
4. 简要描述：根据用户给定的关键词和主题，原创 10 句高质量歌词金句
5. 工具语义：无（不需要工具）
6. 是否需要 MCP：否
7. references：不需要，直接继续
8. 是否需要额外补充更多测试用例：否

请按 create_agent 方式 c 的完整流程执行，包括：分析用例提炼理想态、调用 meta-prompt-engineer 生成提示词、调用 meta-rubric-gen 逐条生成 Judge、用基线模型运行填入 ExpectedOutput、保存到 source/lyrics-golden-lines/testcases.yaml、运行 install.py 分发。

注意：Judge 的核心评分逻辑是 Agent 需原创 10 句候选金句（严禁照搬已有歌词），评分维度为原创性、意境契合度和文学质量。ExpectedOutput 是风格标杆，不要求文字复现。
"
```

### 🎉 创建完成！（🅱️🅲 CLI / IDE）读取生成的文件，看看 AI 做了什么：

```bash
# 1. AI 写的提示词 —— 看看它怎么理解"原创金句"这件事
cat source/lyrics-golden-lines/prompt.md

# 2. AI 提炼的理想态 —— 它认为一个好的原创金句 Agent 应该具备什么特质
cat source/lyrics-golden-lines/ideal_state.md

# 3. AI 为每条用例生成的评分标准（Judge）—— 看看它打算用什么维度来评分
#    （用 yaml_tool 读取第 0 条的 Judge 字段，避免一次性读取太大的 YAML）
./venv/bin/python scripts/yaml_tool.py get source/lyrics-golden-lines/testcases.yaml 0 --fields Judge
```

> 💡 **展示建议**：把 `prompt.md` 的核心段落展示给用户，让用户看到"AI 从 5 条金句中悟出了什么样的创作逻辑"。Judge 中应该可以看到"原创 10 句候选金句"、"原创性"和"意境契合度"等评分维度。这是第一个成就感时刻。

---

## 第 3 步：首次测试 —— 看 Agent 写了什么金句

### 🅰️ OpenClaw 方式

**3a. Spawn `lyrics-golden-lines`** —— 获取 Agent 的实际输出

1. 用 `file_read` 读取 `source/lyrics-golden-lines/prompt.md` 作为 system prompt
2. 用 `file_read` 读取 `source/lyrics-golden-lines/testcases.yaml`，提取 5 条 Input
3. Spawn sub agent，**逐条**传入 Input（直接发送用例内容即可）

对每条用例分别 spawn 或在同一 agent 内逐条发送。将 5 条实际输出用 `file_write` 写入文件：
- `source/lyrics-golden-lines/tmp/test_initial/case_0_actual_result.txt`
- `source/lyrics-golden-lines/tmp/test_initial/case_1_actual_result.txt`
- ... 依此类推

**3b. Spawn `meta-eval-judge`** —— 逐条评估打分

1. 用 `file_read` 读取 `source/meta-eval-judge/prompt.md` 作为 system prompt
2. 对每条用例，从文件读取所有传参：
   - **Input**：从 `testcases.yaml` 读取 `cases[i].Input`
   - **ExpectedOutput**：从 `testcases.yaml` 读取 `cases[i].ExpectedOutput`
   - **Judge**：从 `testcases.yaml` 读取 `cases[i].Judge`
   - **ActualOutput**：从 `tmp/test_initial/case_[i]_actual_result.txt` 读取
3. **每条用例 spawn 一次**（严禁多条合并），传入（使用 `【】` 格式标记）：

```
【Input】
[从 testcases.yaml 读取]

【ExpectedOutput】
[从 testcases.yaml 读取]

【Judge】
[从 testcases.yaml 读取]

【ActualOutput】
[从 case_[i]_actual_result.txt 读取]
```

> eval-judge 会按 rubrics 逐条打分，输出总分和不足之处。

🎉 **将 5 条评估结果写入文件**：
- `source/lyrics-golden-lines/tmp/test_initial/case_0_eval_result.md`
- ... 依此类推
- 汇总评估报告写入 `source/lyrics-golden-lines/tmp/test_initial/评估报告.md`

向用户展示每条用例的金句创作结果和得分。

> 💡 **展示建议**：逐条展示每条用例的实际金句输出和评估得分。按以下格式组织（数据从 `评估报告.md` 和 `case_[N]_actual_result.txt` 中读取，不要编造）：
> ```
> 🎵 你问：[用例主题]（要求原创 10 句）
> 🤖 Agent 写了 10 句，其中最佳：「[从 actual_result 中提取最佳句]」
> 📊 得分：[从 eval_result 中读取实际总分] | [从 eval_result 中读取评价]
> ```
>
> **首次得分高低都正常。记住这个分数，接下来看 AI 怎么自我进化。**
>
> ⚠️ **重要**：eval-judge 的报告中可能会标注 `[rubric]`（评分标准可能不合理）或 `[testcase]`（参考答案可能有误）。**忽略这些标签**，不要据此建议修改用例或评分标准。这些用例是固定的尺子。接下来只通过优化提示词来提分。
>
> **展示完评估结果后，立即进入第 4 步，不要询问用户"是否继续"。**

### 🅱️🅲 CLI / IDE 方式

```bash
CodeBuddy --dangerously-skip-permissions -p "
test_agent lyrics-golden-lines
"
```

### 🎉 测试完成！（🅱️🅲 CLI / IDE）读取结果，看 Agent 具体输出了什么（每条原创 10 句候选金句）：

```bash
# 找到最新的测试目录
TEST_DIR=$(ls -td source/lyrics-golden-lines/tmp/test_* | head -1)

# ⭐ 最重要的 —— 看 Agent 对每条金句的实际回复：
echo "===== 🎵 跳楼机 ====="
cat "$TEST_DIR/case_0_actual_result.txt"
echo ""
echo "===== 🎵 世界赠予我的 ====="
cat "$TEST_DIR/case_1_actual_result.txt"
echo ""
echo "===== 🎵 字字句句暗恋 ====="
cat "$TEST_DIR/case_2_actual_result.txt"
echo ""
echo "===== 🎵 敬自己 ====="
cat "$TEST_DIR/case_3_actual_result.txt"
echo ""
echo "===== 🎵 月亮的日常温柔 ====="
cat "$TEST_DIR/case_4_actual_result.txt"

# 📊 评估报告 —— 每条得了多少分，哪里不好
cat "$TEST_DIR/评估报告.md"
```

> 💡 **展示建议**：
> - 把 5 条需求对应的实际回复**逐条展示**给用户，这是最有趣的部分——"看看 AI 为你写了哪 10 句原创金句"
> - 然后展示评估报告的分数表格（核心指标：原创性、意境契合度、文学质量）
> - 用以下格式组织展示（所有数据从文件读取，不要编造）：
>
> ```
> 🎵 你问：[用例主题]（要求原创 10 句）
> 🤖 Agent 写了 10 句，其中最佳：「[从 actual_result 中提取]」
> 📊 得分：[从 eval_result 中读取] | [从 eval_result 中读取评价]
> ```
>
> **首次得分高低都正常。记住这个分数，接下来看 AI 怎么自我进化。**

---

## 第 4 步：迭代优化 —— 看 AI 自我进化

> 每轮迭代 = 运行 Agent → 评估打分 → 根据反馈优化提示词。重复 3 轮，观察分数变化。

### 🅰️ OpenClaw 方式

> 🚨 **提醒：重读三条铁律**。迭代过程中 **绝对不要修改用例、Judge 或 ExpectedOutput**。eval-judge 报告中的 `[rubric]` / `[testcase]` 标签仅用于诊断参考，**不是修改用例的授权**。唯一允许改的是 Agent 的提示词。同时，3 轮迭代应 **全自动连续执行**，不要在每轮之间停下来询问用户。

所有产物通过文件系统持久化，大幅减轻上下文压力：
- 提示词：`source/lyrics-golden-lines/prompt.md`（每轮更新）
- 理想态：`source/lyrics-golden-lines/ideal_state.md`（不变）
- 用例 + Judge：`source/lyrics-golden-lines/testcases.yaml`（不变）
- 每轮产物：`source/lyrics-golden-lines/tmp/iter_[N]/`

**每轮迭代执行 3 步（3 轮自动连续完成，中间不停顿）：**

**4a. 运行 + 评估**（同第 3 步，产物写入 `tmp/iter_[N]/`）

1. 用 `file_read` 读取当前 `source/lyrics-golden-lines/prompt.md` 作为 system prompt
2. 用 `file_read` 读取 `source/lyrics-golden-lines/testcases.yaml`，提取每条用例的 Input
3. spawn `lyrics-golden-lines` sub agent，逐条传入 5 条 Input，将输出写入 `source/lyrics-golden-lines/tmp/iter_[N]/case_[i]_actual_result.txt`
4. 用 `file_read` 读取 eval-judge 的 prompt.md 作为 system prompt，逐条 spawn 评估——每条评估的 4 个字段均从文件读取：
   - **Input**：从 `testcases.yaml` 读取 `cases[i].Input`
   - **ExpectedOutput**：从 `testcases.yaml` 读取 `cases[i].ExpectedOutput`
   - **Judge**：从 `testcases.yaml` 读取 `cases[i].Judge`
   - **ActualOutput**：从 `tmp/iter_[N]/case_[i]_actual_result.txt` 读取
5. 将评估结果写入 `source/lyrics-golden-lines/tmp/iter_[N]/case_[i]_eval_result.md`
6. 汇总为 `source/lyrics-golden-lines/tmp/iter_[N]/评估报告.md`

**4b. 优化提示词**

先备份当前提示词：将 `source/lyrics-golden-lines/prompt.md` 复制到 `source/lyrics-golden-lines/bak/prompt_iter[N].bak`。

Spawn `meta-prompt-engineer`（用 `file_read` 读取其 prompt.md 作为 system prompt），数据来源全部从文件读取：

1. 用 `file_read` 读取 `source/lyrics-golden-lines/prompt.md`（当前 Agent 提示词）
2. 用 `file_read` 读取 `source/lyrics-golden-lines/ideal_state.md`（理想态描述）
3. 用 `file_read` 读取 `source/lyrics-golden-lines/changelog.md`（变更历史）
4. 用 `file_read` 读取 `source/lyrics-golden-lines/tmp/iter_[N]/case_[i]_eval_result.md`（每条评估结果）
5. 用 `file_read` 读取 `source/lyrics-golden-lines/testcases.yaml`，提取低于 80 分用例的 Input

组装为模式 B 的 `【】` 格式传入（以下仅为结构示意，实际内容从文件读取）：

```
【当前 Agent 提示词】
[从 prompt.md 读取]

【理想态描述】
[从 ideal_state.md 读取]

【变更历史】
[从 changelog.md 读取]

【评估反馈】
[从 eval_result.md 文件中提取每条的分数和 [prompt] 标签的不足、改进建议]

【低分用例 Input】
[从 testcases.yaml 中读取低于 80 分用例的 Input 原文]
```

> ⚠️ **严禁传入 ExpectedOutput**——只传 Input 和评估反馈。prompt-engineer 的禁令明确禁止接触 ExpectedOutput。
>
> ⚠️ **通用性约束**：优化目标是提升 Agent 的**通用推理和生成能力**，而不是让它针对这 5 条用例做特殊适配。所有改动必须对从未见过的新输入同样有效。禁止在提示词中嵌入与这 5 条用例主题相似的 few-shot 示例。
>
> ⚠️ **传递评估反馈时的过滤规则**：eval-judge 的不足条目中，标注为 `[rubric]` 或 `[testcase]` 的条目**不要传给 prompt-engineer**，因为那些问题不是提示词能解决的。只传 `[prompt]` 标签的条目。

🎉 **从返回内容的 `===PROMPT===` 标记之后提取新提示词**，**暂存为候选提示词（先不写入 prompt.md）**。

**4b-review. Spawn `meta-reviewer`** —— 反作弊审查（写入前的独立审查）

> 💡 这一步是"生成与审查分离"架构的关键——prompt-engineer 负责生成，reviewer 负责审查，解决"运动员自己当裁判"的问题。

1. 用 `file_read` 读取 `source/meta-reviewer/prompt.md` 作为 system prompt
2. Spawn sub agent，传入：

```
【待审查提示词】
[上一步 prompt-engineer 输出的候选提示词全文]

【测试用例】
[从 testcases.yaml 读取每条用例的 Input 和 ExpectedOutput，逐条列出]

【审查上下文】
[本轮优化的 changelog 说明]
```

3. 解析返回内容中 `===REVIEW_RESULT===` 之后的审查结果：
   - **✅ PASS / ⚠️ WARN** → 候选提示词通过审查，用 `file_write` 写入 `source/lyrics-golden-lines/prompt.md`
   - **❌ REJECT** → 候选提示词被打回，将审查发现（修改建议部分）反馈给 prompt-engineer 重新优化，最多重试 2 次
   - 连续 3 次 REJECT → 回退到备份提示词，记录审查阻塞

同时向 `source/lyrics-golden-lines/changelog.md` 追加本轮优化记录。

**4c. 展示本轮变化（然后立即进入下一轮，不要询问用户）**

向用户展示：
- 每条用例的得分变化（对比上一轮，可从 `tmp/iter_[N-1]/评估报告.md` 和 `tmp/iter_[N]/评估报告.md` 中读取）
- 提示词改了什么（用人话概括新旧提示词的差异）
- 下一轮优化方向

> 🚨 **展示完毕后，立即自动开始下一轮的 4a 步骤。不要询问"是否继续""要不要进行下一轮"。**

**重复 4a~4c 共 3 轮**。每轮结束后展示进度表格：

> ```
> 📊 迭代进度
>
> 轮次 | 平均分 | 变化 | 关键改进
> -----|--------|------|--------
>   1  |  [分数] |  —   | [从 changelog 读取本轮改进摘要]
>   2  |  [分数] | [Δ]  | [从 changelog 读取本轮改进摘要]
>   3  |  [分数] | [Δ]  | [从 changelog 读取本轮改进摘要]
> ```

> 💡 **上下文管理提示**：由于产物已写入文件系统，每轮迭代后上下文只需保留最小必要信息：
> - 当前轮次号和上一轮平均分（用于判断进度）
> - 本轮评估摘要（分数 + `[prompt]` 标签的不足，不需要完整评估报告）
> - 其他所有内容（提示词、理想态、Judge、ActualOutput、历史评估报告）均可从文件读取
>
> ⚠️ **再次强调**：eval-judge 可能会在不足条目中标注 `[rubric]` 或 `[testcase]`，暗示评分标准或参考答案可能有问题。**忽略这些建议**，不要修改任何用例内容。用例是固定的评估尺子，只有提示词是可以改的。

### 🅱️🅲 CLI / IDE 方式

> `evo_looper` 是多轮循环任务（每轮：5 条测试 + 5 次评估 + 优化提示词），单次 `-p` 调用会上下文爆炸。
>
> **解决方案**：拆成独立的步骤，每步一个 `-p` 调用。好处是每步完成后都能读取产物，给用户展示具体改了什么。

### 迭代第 1 轮

**4.1 备份初始提示词**（后面要用来对比）：
```bash
cp source/lyrics-golden-lines/prompt.md source/lyrics-golden-lines/bak/prompt_initial.bak
```

**4.2 测试 + 评估 + 生成反馈**：
```bash
CodeBuddy --dangerously-skip-permissions -p "
test_agent lyrics-golden-lines

测试完成后，请：
1. 汇总评估报告
2. 将评估中每条用例的不足和改进建议整理为优化建议
3. 保存到 source/lyrics-golden-lines/tmp/iter1_feedback.md
"
```

**4.3 展示本轮结果**：
```bash
# 看评估反馈——哪些地方需要改进
cat source/lyrics-golden-lines/tmp/iter1_feedback.md
```

> 💡 **展示建议**：逐条展示每条用例的得分 + 不足（从 `iter1_feedback.md` 读取真实数据），例如："[用例主题] 得分 [X]，因为 [eval-judge 指出的具体不足]"。

**4.4 优化提示词**：
```bash
CodeBuddy --dangerously-skip-permissions -p "
读取以下文件：
- source/lyrics-golden-lines/prompt.md（当前提示词）
- source/lyrics-golden-lines/ideal_state.md（理想态）
- source/lyrics-golden-lines/changelog.md（变更历史）
- source/lyrics-golden-lines/tmp/iter1_feedback.md（评估反馈）

请调用 meta-prompt-engineer 优化提示词。
要求：根据评估反馈中的不足进行针对性优化，不要照抄 ExpectedOutput。
优化完成后，先调用 meta-reviewer 审查提示词是否存在作弊或过拟合：
- PASS / WARN → 将新提示词写入 source/lyrics-golden-lines/prompt.md
- REJECT → 将审查发现反馈给 prompt-engineer 重新优化（最多重试 2 次）
审查通过后：
1. 在 changelog.md 追加本轮优化记录（标签 [优化]）
2. 运行 ./venv/bin/python scripts/install.py lyrics-golden-lines 同步
"
```

**4.5 ⭐ 看看提示词改了什么**：
```bash
# 对比初始版本和优化后的版本
diff source/lyrics-golden-lines/bak/prompt_initial.bak source/lyrics-golden-lines/prompt.md

# 看变更日志
cat source/lyrics-golden-lines/changelog.md
```

> 💡 **展示建议**：把 diff 结果翻译成人话展示给用户，格式如下（内容从 diff 和 changelog 中读取，不要编造）：
>
> ```
> 📝 第 [N] 轮提示词优化：
>
> ✨ [改动 1 的人话描述：从 diff 中归纳]
> ✨ [改动 2 的人话描述：从 diff 中归纳]
> ✨ [改动 3 的人话描述：从 diff 中归纳]
> ```

### 迭代第 2~3 轮

**重复 4.2 ~ 4.5**（把 `iter1` 改成 `iter2`、`iter3`）。每轮完成后：

1. **读取 5 条金句的新回复** → 跟上一轮对比，看 Agent 写的金句是不是更好了
2. **读取评估报告** → 看分数涨了多少
3. **读取 diff** → 看提示词又改了什么

```bash
# 第 2 轮测试后，再看一次 Agent 的实际输出（原创 10 句候选中最佳的那句）
TEST_DIR=$(ls -td source/lyrics-golden-lines/tmp/test_* | head -1)
echo "===== 🎵 月亮的日常温柔（关注上轮得分变化）====="
cat "$TEST_DIR/case_4_actual_result.txt"
```

> 💡 **展示建议**：把每轮的进步可视化（所有数据从 `评估报告.md` 和 `changelog.md` 中读取，不要编造）：
>
> ```
> 📊 迭代进度
>
> 轮次 | 平均分 | 变化 | 关键改进
> -----|--------|------|--------
>   1  |  [分数] |  —   | [从 changelog 读取]
>   2  |  [分数] | [Δ]  | [从 changelog 读取]
>   3  |  [分数] | [Δ]  | [从 changelog 读取]
>
> 🎵 进步最大的用例：[从评估报告中找到分数提升最大的用例]
>   轮次 1: [从 iter_1 评估报告读取该用例的表现]
>   轮次 3: [从 iter_3 评估报告读取该用例的表现]
> ```

### 你会看到的进展

通常 3 轮即可看到明显提升。每轮提升幅度取决于 Agent 和评估标准，但趋势是一致的：分数逐轮上涨，提示词逐轮进化。

> 3 轮足够体验到"AI 自我进化"的感觉。想继续冲高可以重复更多轮。

---

## 第 5 步：对比优化效果 —— 全景回顾

### 🅰️ OpenClaw 方式

使用 `file_read` 读取文件系统中的历史产物，生成全景对比报告：

1. 读取 `source/lyrics-golden-lines/bak/prompt_iter1.bak`（初始版本）
2. 读取 `source/lyrics-golden-lines/prompt.md`（最终版本）
3. 读取 `source/lyrics-golden-lines/tmp/test_initial/评估报告.md` 和 `source/lyrics-golden-lines/tmp/iter_3/评估报告.md`
4. 读取 `source/lyrics-golden-lines/changelog.md`

逐段对比差异，汇总分数变化趋势，总结关键优化策略。将报告写入 `source/lyrics-golden-lines/tmp/optimization_summary.md`。

### 🅱️🅲 CLI / IDE 方式

```bash
CodeBuddy --dangerously-skip-permissions -p "
请帮我对比 lyrics-golden-lines 优化前后的效果：

1. 读取 source/lyrics-golden-lines/bak/prompt_initial.bak（初始版本）
2. 读取当前的 source/lyrics-golden-lines/prompt.md（最终版本）
3. 逐段对比两个版本的差异，说明每处改动解决了什么问题
4. 从 changelog.md 中提取各轮的分数变化
5. 总结：哪些优化策略提分最多，哪些是关键转折点
6. 将对比报告保存到 source/lyrics-golden-lines/tmp/optimization_summary.md
"
```

然后读取报告：
```bash
cat source/lyrics-golden-lines/tmp/optimization_summary.md
```

> 💡 **展示建议**：这是最终的成就感高潮。用对比表格展示（所有数据从 `bak/prompt_initial.bak`、`prompt.md`、两份评估报告和 `changelog.md` 中读取，不要编造）：
>
> ```
> 📊 优化全景
>
>                      初始版本          →  最终版本
> ──────────────────────────────────────────────────
> 平均得分              [初始分]              [最终分]
> 提示词长度            [初始字数]            [最终字数]
> [从 diff 归纳的关键维度变化，如是否新增了推理链、输出格式等]
>
> 🎵 最大进步用例：[从评估报告中找到分数提升最大的用例]
>    初始：[从 test_initial 评估报告读取该用例表现]
>    最终：[从 iter_3 评估报告读取该用例表现]
> ```
>
> **🎉 你定了标准（5 条金句 × 原创 10 句候选），AI 自己想办法达到了标准。这就是 Meta-Agent。**

---

## 📋 完整流程速查

### 🅰️ OpenClaw 方式

| 步骤 | Spawn 的 Sub Agent | 传入内容 | 产出（写入文件） |
|------|-------------------|---------|-----------------|
| 0 | — | — | Clone 项目到本地 |
| 1 | — | — | `demo_testcases.yaml`（写入文件系统） |
| 2 | `meta-prompt-engineer` → `meta-rubric-gen` × 5 | 理想态 + 示例用例 | `prompt.md` + `ideal_state.md` + `testcases.yaml` |
| 3 | `lyrics-golden-lines` × 5 → `meta-eval-judge` × 5 | Input → 评估 | `tmp/test_initial/case_[N]_*.txt` + `评估报告.md` |
| 4 | 循环 3 轮：Agent × 5 → Judge × 5 → Prompt Engineer → **Reviewer 审查** | 上轮反馈（从文件读取） | `tmp/iter_[N]/` + 更新 `prompt.md` + `changelog.md` |
| 5 | — | 从文件读取全部历史 | `tmp/optimization_summary.md` |

### 🅱️🅲 CLI / IDE 方式

| 步骤 | 执行 | 完成后读什么 | 展示什么 |
|------|------|-------------|---------|
| 0 | git clone + SETUP.md | verify_setup.py | 环境 ✅ |
| 1 | 创建 demo_testcases.yaml | — | 5 条金句用例（每条要求原创 10 句候选） |
| 2 | `-p "create_agent ... 方式 c"` | `prompt.md` + `ideal_state.md` | AI 写的提示词和理想态 |
| 3 | `-p "test_agent ..."` | `case_N_actual_result.txt` + `评估报告.md` | **5 条需求各原创 10 句候选金句** + 分数 |
| 4 | 循环：test → feedback → optimize | `iter_feedback.md` + `diff` + `changelog.md` | 每轮分数变化 + 提示词改动 |
| 5 | `-p "对比 bak/初始 vs prompt.md"` | `optimization_summary.md` | 初始 vs 最终全景对比 |

> **关键**：成就感不在于"执行完了"，而在于**每步执行完后去看 AI 生成了什么内容**（文件或对话产物）。

---

## ❓ 常见问题

### Q: 为什么不用 PTY 交互式？

（仅限 CLI 方式）PTY 模式下 CLI 的输出是给人看终端设计的，Agent 拿到的是一大段 stdout 文本，很难从中提取有意义的内容展示给用户。

用 **分步 `-p` + 读文件** 的方式更好：
1. 每步都是独立的 CLI 调用，上下文干净
2. 产物都保存为文件（`.txt`、`.md`、`.yaml`），结构清晰
3. 可以 `cat` 文件后自行组织展示

### Q: OpenClaw 方式和 CLI 方式有什么区别？

| 维度 | OpenClaw | CLI / IDE |
|------|---------|-----------|
| 安装 | 无需安装 CLI 工具（需 clone 项目） | 需要 CLI 工具或 IDE |
| 文件系统 | ✅ 支持（spawn 时赋予 `file_read` / `file_write` / `list_directory`），产物写入 `source/[Agent]/tmp/` | ✅ 支持（产物写入 `source/[Agent]/tmp/`） |
| 工具调用 | 文件读写 + 目录列表（通过 spawn `tools` 参数赋予） | 全功能（MCP、文件读写、命令执行） |
| Shell 命令 | ❌ 不支持 | ✅ 支持 |
| MCP 服务 | ❌ 不支持 | ✅ 支持 |
| 适用场景 | 纯文本生成类 Agent（如歌词金句） | 所有 Agent（含日志分析、代码审查等需要 MCP 的） |
| 体验完整度 | ⭐⭐⭐⭐⭐（核心流程完整，产物持久化） | ⭐⭐⭐⭐⭐（全功能） |

### Q: 为什么 `evo_looper` 要拆成手动步骤？

`evo_looper` 是多轮循环：每轮 5 条测试（每条原创 10 句候选金句）+ 5 次评估 + 优化提示词。单次 `-p` 调用会上下文爆炸。

拆成独立步骤的好处：
1. 每轮上下文都是干净的
2. 每轮之间可以读取文件、给用户展示进度
3. 用户能感受到**每一轮的具体进步**（金句更有原创性了、分数涨了、提示词改了什么）

### Q: 迭代优化卡在某个分数不动了？

先检查评估标准是否合理：
```bash
CodeBuddy --dangerously-skip-permissions -p "calibrate lyrics-golden-lines"
```

### Q: 这个项目能创建什么样的 Agent？

**CLI / IDE 方式**：任何"文本输入 → 文本输出"的 Agent，包括需要工具调用的：代码审查助手、翻译评估、客服话术、SQL 助手、日志分析等。

**OpenClaw 方式**：纯文本生成类 Agent + 涉及文件读写的 Agent。原创金句助手、文案生成、翻译润色、代码生成等都可以。需要 MCP 服务 / Shell 命令执行的 Agent（如日志分析）请使用 CLI 或 IDE。

---

## 🧩 背后的原理

```
你的 5 条金句用例（每条要求原创 10 句候选）
    │
    ▼
meta-prompt-engineer ──→ 从用例反推出提示词
    │
    ▼
meta-rubric-gen ──→ 为每条用例生成评分标准（核心：原创性 + 意境契合度 + 文学质量）
    │
    ▼
[运行 Agent] ──→ 实际输出（5 条需求 × 原创 10 句候选金句）
    │
    ▼
meta-eval-judge ──→ 逐条打分 + 指出不足
    │
    ▼
meta-prompt-engineer ──→ 根据不足优化提示词
    │
    ▼
meta-reviewer ──→ 独立审查：是否作弊/过拟合？（✅ PASS → 写入 / ❌ REJECT → 打回重来）
    │                                              （循环 ↑）
    ▼
meta-retrospective ──→ 每 3 轮全局复盘，防止优化方向跑偏
```

核心思想：**用 AI 来解决 AI 的问题**。你定标准，AI 自己进化。

---

## 🎓 完成后的下一步

1. **创建自己的 Agent** —— 换一组测试用例，走同样的流程
2. **升级到 CLI / IDE** —— 如果你用的是 OpenClaw 方式，安装 CLI 工具可以解锁 MCP 工具调用和 Shell 命令执行能力，支持更复杂的 Agent（如日志分析）
3. **深入评估体系** —— `calibrate` 诊断三元组一致性（CLI / IDE）
4. **多平台测试** —— `test_agent lyrics-golden-lines@codebuddycli`（CLI / IDE）
5. **阅读完整文档** —— [README.md](README.md)、[SETUP.md](SETUP.md)
