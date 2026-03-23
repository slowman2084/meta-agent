# 5 分钟让 AI 学会推荐金句 —— Meta-Agent 快速体验

> **⏱️ 预计耗时**：环境准备 5 分钟 + 流程体验 20~30 分钟（取决于执行方式）
>
> 你将用 5 条"流行歌金句"测试用例，体验 Agent 的创建、测试、迭代优化全流程。
> 
> **OpenClaw 用户**：无需安装任何工具，直接在浏览器中完成全部流程。

---

### 📖 设计原则

**CLI / IDE 方式**：每一步都是一个独立的 CLI 调用（`-p` 模式）。每步**执行完后**，读取生成的文件，把有趣的内容展示给用户。

**OpenClaw 方式**：每一步通过 spawn sub agent 完成。你（OpenClaw）读取 `source/meta-*/prompt.md` 作为各 sub agent 的 system prompt，在对话上下文中传递中间产物（提示词、输出、评分），无需文件系统。

成就感来自"看到 AI 具体写了什么、推荐了什么金句、分数怎么变的"，而不是一句"已完成"。

**金句评估逻辑**：Agent 每次需生成 **10 句**候选金句。评分主要看是否有**至少 1 句与 ExpectedOutput 达到 90% 相似度**——这是核心加分项。

---

## 🎯 你将完成的事

```
5 条歌词金句用例（每条要求 Agent 推荐 10 句候选金句）
    → AI 反推出提示词（看看它怎么理解"金句推荐"）
    → 首次测试，看 Agent 给每条需求推荐了哪 10 句金句（具体内容！）
    → 迭代优化 3 轮，每轮看提示词改了什么、分数涨了多少
    → 最终对比初始 vs 最终提示词，理解 AI 的优化策略
```

---

## 前置要求

### 选择你的体验方式

Meta-Agent 支持三种体验方式，选**任意一种**即可：

| 方式 | 需要安装 | 适合谁 | 体验完整度 |
|------|---------|--------|-----------|
| **🅰️ OpenClaw** | 无需安装（浏览器即可） | 想快速感受、不想装环境的人 | ⭐⭐⭐⭐ |
| **🅱️ AI IDE** | Cursor / CodeBuddy / Claude Code | 已有 IDE 的开发者 | ⭐⭐⭐⭐⭐ |
| **🅲 CLI** | CodeBuddy CLI 或 Claude Code CLI | 喜欢终端和脚本化的人 | ⭐⭐⭐⭐⭐ |

#### 🅰️ OpenClaw 方式（零门槛）

**不需要安装任何工具**。OpenClaw 会通过 sub agent spawn 来调用 Meta-Agent 的各个 Sub Agent（如 meta-prompt-engineer、meta-eval-judge 等）。

工作原理：
- 本文档（`README_FORCLAW.md`）本身就是 OpenClaw 的执行手册
- OpenClaw 读取 `source/meta-*/prompt.md` 作为各 sub agent 的 system prompt
- 通过 spawn sub agent 实现 **提示词生成 → 评估打分 → 迭代优化** 的完整流程
- 编排规则（rules）已内嵌在本文档的步骤说明中，无需单独安装到 IDE
- 每个 sub agent 有特定的输入格式（使用 `【】` 格式标记），本文档已在每步中提供了精确的模板

> ⚠️ **限制**：OpenClaw spawn 的 sub agent 没有工具调用能力（无法读写文件、执行命令），因此只适合**纯文本生成类 Agent**（如本 demo 的歌词金句推荐）。需要 MCP / 工具调用的 Agent（如日志分析）仍需 CLI 或 IDE。

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

**不需要 clone 项目、不需要安装环境。** 直接跳到「第 1 步」准备测试用例即可。

OpenClaw 需要能读取 GitHub 仓库中以下 3 个提示词文件，作为 spawn sub agent 时的 system prompt：

| Sub Agent | GitHub Raw URL |
|-----------|---------------|
| 提示词生成/优化专家 | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-prompt-engineer/prompt.md` |
| 评估打分专家 | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-eval-judge/prompt.md` |
| 评分标准生成专家 | `https://raw.githubusercontent.com/slowman2084/meta-agent/main/source/meta-rubric-gen/prompt.md` |

> 💡 如果 OpenClaw 支持 `web_fetch` 或类似工具，可以直接读取上述 URL。如果不支持，可以在首轮对话中手动粘贴这 3 个文件的内容。

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

**不需要创建文件**。将下方 5 条测试用例的内容记在对话上下文中，后续步骤直接引用即可。

### 🅱️🅲 CLI / IDE 方式

在项目根目录创建 `demo_testcases.yaml`：

```yaml
meta:
  count: 5
  notice: "流行歌金句助手 demo 用例 —— Agent 每次需生成 10 句候选金句"
cases:
  - Input: |
      根据“跳楼机"生成 10 句歌词金句
    ExpectedOutput: |
      Baby 我们的感情好像跳楼机，让我突然地升空又急速落地
      —— 五月天《跳楼机》
      （以上为 10 句中最佳金句的参考方向，Agent 实际输出应包含 10 句候选）
    Judge: ""

  - Input: |
      根据“世界赠予我的"生成 10 句歌词金句
    ExpectedOutput: |
      🎵 **世界赠予我虫鸣，也赠予我雷霆；赠我弯弯一枚月，也赠予我晚星**
      —— (待 Agent 填充歌名和歌手)
      （以上为 10 句中最佳金句的参考方向）
    Judge: ""

  - Input: |
      根据“字字句句都是暗恋"生成 10 句歌词金句
    ExpectedOutput: |
      他字字未提喜欢你，你句句都是我愿意
    Judge: ""

  - Input: |
      根据“敬自己"生成 10 句歌词金句
    ExpectedOutput: |
      敬自己一杯酒，往后余生不回头
    Judge: ""

  - Input: |
      有没有关于"月亮"的歌词金句，请推荐 10 句。
    ExpectedOutput: |
      若是月亮还没来，路灯也可照窗台
    Judge: ""
```

> 📝 **评分核心逻辑**：Agent 需输出 **10 句**候选金句。要求 Judge 中的 Rubrics 主要加分项是：10 句中**至少有 1 句与 ExpectedOutput 达到 90% 相似度**。`Judge` 留空，后面由 AI 自动生成对应的

---

## 第 2 步：从测试用例创建 Agent

### 🅰️ OpenClaw 方式

依次 spawn 2 个 sub agent 来完成创建：

**2a. Spawn `meta-prompt-engineer`** —— 生成提示词

用 `source/meta-prompt-engineer/prompt.md` 的完整内容作为 system prompt，spawn 一个 sub agent，传入以下 user message（注意使用 `【】` 格式标记，这是该 sub agent 要求的输入格式）：

```
【理想态描述】
该 Agent 的功能是：根据用户的心情、情境或关键词，推荐 10 句契合的流行歌歌词金句，标注歌名和歌手。
好的金句推荐 Agent 应具备：
- 准确理解用户意图（情绪、意象、场景）
- 每次稳定输出 10 句候选金句
- 每句标注歌名和歌手
- 候选中至少有 1 句高度契合用户需求

【示例用例】
Input: 根据"跳楼机"生成 10 句歌词金句
→ 最佳参考：Baby 我们的感情好像跳楼机，让我突然地升空又急速落地 —— 五月天《跳楼机》

Input: 根据"世界赠予我的"生成 10 句歌词金句
→ 最佳参考：世界赠予我虫鸣，也赠予我雷霆；赠我弯弯一枚月，也赠予我晚星

Input: 根据"字字句句都是暗恋"生成 10 句歌词金句
→ 最佳参考：他字字未提喜欢你，你句句都是我愿意

Input: 根据"敬自己"生成 10 句歌词金句
→ 最佳参考：敬自己一杯酒，往后余生不回头

Input: 有没有关于"月亮"的歌词金句，请推荐 10 句
→ 最佳参考：若是月亮还没来，路灯也可照窗台
```

🎉 **从 sub agent 返回内容中提取产物**：

prompt-engineer 的输出会包含 `===PROMPT===` 标记，该标记**之后的内容**就是生成的 Agent 提示词。将其记录为 `PROMPT`（后续步骤使用）。

同时，从输入中的【理想态描述】部分保留一份 `IDEAL_STATE`，后续迭代优化时传给 prompt-engineer。

**2b. Spawn `meta-rubric-gen`** —— 逐条生成评分标准

用 `source/meta-rubric-gen/prompt.md` 的完整内容作为 system prompt，**逐条** spawn（每条用例一次），传入（使用 `【】` 格式标记）：

```
【Input】
根据"跳楼机"生成 10 句歌词金句

【任务约束】
核心评分逻辑：Agent 需生成 10 句候选金句，其中至少 1 句与以下参考金句达到 90% 相似度为主要加分项。
参考金句：Baby 我们的感情好像跳楼机，让我突然地升空又急速落地 —— 五月天《跳楼机》
```

> 对每条用例替换对应的 Input 和参考金句。**不需要传 agent_name**（本 demo 无 references 目录），rubric-gen 会直接基于 Input 内容生成评分标准。

🎉 **记录 5 条 Judge 评分标准**（YAML 格式的 rubrics 列表），后续评估时使用。

### 🅱️🅲 CLI / IDE 方式

```bash
CodeBuddy --dangerously-skip-permissions -p "
请执行 create_agent 流程：

1. 创建方式：c（从 YAML 测试用例创建）
2. YAML 文件路径：demo_testcases.yaml
3. Agent 名称：lyrics-golden-lines
4. 简要描述：根据用户的心情或情境，推荐 10 句契合的流行歌歌词金句，标注歌名和歌手
5. 工具语义：无（不需要工具）
6. 是否需要 MCP：否
7. references：不需要，直接继续
8. 是否需要额外补充更多测试用例：否

请按 create_agent 方式 c 的完整流程执行，包括：分析用例提炼理想态、调用 meta-prompt-engineer 生成提示词、调用 meta-rubric-gen 逐条生成 Judge、用基线模型运行填入 ExpectedOutput、保存到 source/lyrics-golden-lines/testcases.yaml、运行 install.py 分发。

注意：Judge 的核心评分逻辑是 Agent 需生成 10 句候选金句，其中至少 1 句与 ExpectedOutput 达到 90% 相似度即为主要加分项。
"
```

### 🎉 创建完成！（🅱️🅲 CLI / IDE）读取生成的文件，看看 AI 做了什么：

```bash
# 1. AI 写的提示词 —— 看看它怎么理解"金句推荐"这件事
cat source/lyrics-golden-lines/prompt.md

# 2. AI 提炼的理想态 —— 它认为一个好的金句推荐应该具备什么特质
cat source/lyrics-golden-lines/ideal_state.md

# 3. AI 为每条用例生成的评分标准（Judge）—— 看看它打算用什么维度来评分
#    （用 yaml_tool 读取第 0 条的 Judge 字段，避免一次性读取太大的 YAML）
./venv/bin/python scripts/yaml_tool.py get source/lyrics-golden-lines/testcases.yaml 0 --fields Judge
```

> 💡 **展示建议**：把 `prompt.md` 的核心段落展示给用户，让用户看到"AI 从 5 条金句中悟出了什么样的推荐逻辑"。Judge 中应该可以看到"生成 10 句候选金句"和"至少 1 句 90% 相似"的评分维度。这是第一个成就感时刻。

---

## 第 3 步：首次测试 —— 看 Agent 推荐了什么金句

### 🅰️ OpenClaw 方式

**3a. Spawn `lyrics-golden-lines`** —— 获取 Agent 的实际输出

用第 2 步生成的 `PROMPT` 作为 system prompt，spawn 一个 sub agent。**逐条**传入 5 条 Input（直接发送用例内容即可）：

```
根据"跳楼机"生成 10 句歌词金句
```

对每条用例分别 spawn 或在同一 agent 内逐条发送。记录 5 条实际输出（`ActualOutput_0` ~ `ActualOutput_4`）。

**3b. Spawn `meta-eval-judge`** —— 逐条评估打分

用 `source/meta-eval-judge/prompt.md` 的完整内容作为 system prompt，**每条用例 spawn 一次**（严禁多条合并），传入（使用 `【】` 格式标记，这是该 sub agent 要求的输入格式）：

```
【Input】
根据"跳楼机"生成 10 句歌词金句

【ExpectedOutput】
Baby 我们的感情好像跳楼机，让我突然地升空又急速落地
—— 五月天《跳楼机》
（以上为 10 句中最佳金句的参考方向，Agent 实际输出应包含 10 句候选）

【Judge】
[粘贴第 2b 步为该用例生成的 YAML rubrics]

【ActualOutput】
[粘贴第 3a 步该用例的实际输出]
```

> 对每条用例替换对应的 Input、ExpectedOutput、Judge、ActualOutput。eval-judge 会按 rubrics 逐条打分，输出总分和不足之处。

🎉 **汇总 5 条评分**，计算平均分。向用户展示每条用例的金句推荐结果和得分。

> 💡 **展示建议**：
> ```
> 🎵 你问："跳楼机"的意象（要求 10 句）
> 🤖 Agent 推荐了 10 句，其中最佳：「Baby 我们的感情好像跳楼机…」—— 五月天《跳楼机》
> 📊 得分：85/100 | 最佳命中率：92% 相似 ✅
> ```
>
> **首次得分 65-85 是正常的。记住这个分数，接下来看 AI 怎么自我进化。**

### 🅱️🅲 CLI / IDE 方式

```bash
CodeBuddy --dangerously-skip-permissions -p "
test_agent lyrics-golden-lines
"
```

### 🎉 测试完成！（🅱️🅲 CLI / IDE）读取结果，看 Agent 具体输出了什么（每条 10 句候选金句）：

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
> - 把 5 条需求对应的实际回复**逐条展示**给用户，这是最有趣的部分——"看看 AI 为你推荐了哪 10 句歌词金句"
> - 然后展示评估报告的分数表格（核心指标：是否有 1 句达到 90% 相似度）
> - 用类似这样的方式组织展示：
>
> ```
> 🎵 你问："跳楼机"的意象（要求 10 句）
> 🤖 Agent 推荐了 10 句，其中最佳：「Baby 我们的感情好像跳楼机…」—— 五月天《跳楼机》
> 📊 得分：85/100 | 最佳命中率：92% 相似 ✅
>
> 🎵 你问："月亮"的日常温柔（要求 10 句）
> 🤖 Agent 推荐了 10 句，但最接近的一句相似度仅 65%
> 📊 得分：62/100 | 不足：10 句中没有一句抓住"日常"感，偏大气方向
> ```
>
> **首次得分 65-85 是正常的。记住这个分数，接下来看 AI 怎么自我进化。**

---

## 第 4 步：迭代优化 —— 看 AI 自我进化

> 每轮迭代 = 运行 Agent → 评估打分 → 根据反馈优化提示词。重复 3 轮，观察分数变化。

### 🅰️ OpenClaw 方式

对话上下文中保存着：`PROMPT`（当前提示词）、`IDEAL_STATE`（理想态）、5 条 Judge（YAML rubrics）、上一轮的评分结果。

**每轮迭代执行 3 步：**

**4a. 运行 + 评估**（同第 3 步）

1. 用当前 `PROMPT` 作为 system prompt，spawn `lyrics-golden-lines` sub agent，逐条传入 5 条 Input，记录 5 条 `ActualOutput`
2. 用 eval-judge 的 prompt.md 作为 system prompt，逐条 spawn 评估（同第 3b 步的 `【】` 格式），得到 5 条评分和不足

**4b. 优化提示词**

Spawn `meta-prompt-engineer`（用其 prompt.md 作为 system prompt），传入（使用 `【】` 格式标记，这是模式 B 的标准输入格式）：

```
【当前 Agent 提示词】
[粘贴当前 PROMPT 的完整内容]

【理想态描述】
[粘贴 IDEAL_STATE]

【评估反馈】
用例 1（跳楼机）：[分数] 分
不足：[eval-judge 输出的不足描述]
改进建议：[eval-judge 输出的改进建议]

用例 2（世界赠予我的）：[分数] 分
不足：[不足描述]
改进建议：[改进建议]

...（共 5 条）

【低分用例 Input】
[列出低于 80 分的用例的 Input 原文]
```

> ⚠️ **严禁传入 ExpectedOutput**——只传 Input 和评估反馈。prompt-engineer 的禁令明确禁止接触 ExpectedOutput。

🎉 **从返回内容的 `===PROMPT===` 标记之后提取新提示词**，用它替换上下文中的 `PROMPT`。

**4c. 展示本轮变化**

向用户展示：
- 每条用例的得分变化（对比上一轮）
- 提示词改了什么（用人话概括新旧提示词的差异）
- 下一轮优化方向

**重复 4a~4c 共 3 轮**。每轮结束后展示进度表格：

> ```
> 📊 迭代进度
>
> 轮次 | 平均分 | 变化 | 关键改进
> -----|--------|------|--------
>   1  |   72   |  —   | 初始版本
>   2  |   83   | +11  | 新增推理链
>   3  |   91   | +8   | 新增 few-shot 示例
> ```

> ⚠️ **上下文管理提示**：每轮迭代涉及 11 次 sub agent spawn（5 次 Agent + 5 次 Judge + 1 次 Prompt Engineer），3 轮共 33 次。建议每轮结束后，仅保留以下关键产物到下一轮上下文，丢弃 spawn 的中间过程：
> - `PROMPT`（最新版提示词）
> - `IDEAL_STATE`（理想态，不变）
> - 5 条 Judge（不变）
> - 本轮 5 条评分摘要（分数 + 不足，不需要完整评估报告）
> - 5 条 ExpectedOutput（不变，用于 eval-judge 传参）

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

> 💡 **展示建议**：展示每条用例的得分 + 不足，例如："月亮的日常温柔只有 69 分，因为 Agent 推荐了太大气的歌词，没理解'日常温柔'的要求。"

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
优化完成后：
1. 将新提示词写入 source/lyrics-golden-lines/prompt.md
2. 在 changelog.md 追加本轮优化记录（标签 [优化]）
3. 运行 ./venv/bin/python scripts/install.py lyrics-golden-lines 同步
"
```

**4.5 ⭐ 看看提示词改了什么**：
```bash
# 对比初始版本和优化后的版本
diff source/lyrics-golden-lines/bak/prompt_initial.bak source/lyrics-golden-lines/prompt.md

# 看变更日志
cat source/lyrics-golden-lines/changelog.md
```

> 💡 **展示建议**：把 diff 结果翻译成人话展示给用户，例如：
>
> ```
> 📝 第 1 轮提示词优化：
>
> ✨ 新增「推理链」：Agent 现在会先分析用户描述中的情绪关键词（如"升空又落地"→忽上忽下的刺激感），
>    再去匹配歌词，而不是直接搜索字面关键词。
>
> ✨ 新增「输出格式约束」：要求统一用 🎵 金句 —— 《歌名》歌手 + 一句话共鸣解读 的格式回复。
>
> ✨ 新增「边界处理」：当用户描述比较模糊时（如"日常温柔"），要求 Agent 先确认理解再推荐。
> ```

### 迭代第 2~3 轮

**重复 4.2 ~ 4.5**（把 `iter1` 改成 `iter2`、`iter3`）。每轮完成后：

1. **读取 5 条金句的新回复** → 跟上一轮对比，看 Agent 回答是不是更好了
2. **读取评估报告** → 看分数涨了多少
3. **读取 diff** → 看提示词又改了什么

```bash
# 第 2 轮测试后，再看一次 Agent 的实际输出（10 句候选中最佳的那句）
TEST_DIR=$(ls -td source/lyrics-golden-lines/tmp/test_* | head -1)
echo "===== 🎵 月亮的日常温柔（上轮 62 分）====="
cat "$TEST_DIR/case_4_actual_result.txt"
```

> 💡 **展示建议**：把每轮的进步可视化：
>
> ```
> 📊 迭代进度
>
> 轮次 | 平均分 | 变化 | 关键改进
> -----|--------|------|--------
>   1  |   72   |  —   | 初始版本，部分用例 10 句中没命中
>   2  |   83   | +11  | 新增推理链，"跳楼机"命中率从 78%→95%
>   3  |   91   | +8   | 新增 few-shot 示例，"月亮"10 句中终于有 1 句 92% 相似
>
> 🎵 "月亮的日常温柔" 的回答变化：
>   轮次 1: 10 句全偏大气（最高相似度仅 55%，62 分）
>   轮次 3: 10 句中第 3 句「若是月亮还没来，路灯也可照窗台」达到 92% 相似（89 分）
> ```

### 你会看到的进展

通常 3 轮即可看到明显提升：

```
迭代 1: 平均 72 分
迭代 2: 平均 83 分  ↑11  ← 新增推理链/CoT，10 句命中率提升
迭代 3: 平均 91 分  ↑8   ← 新增 few-shot 示例 + 边界条件处理
```

> 3 轮足够体验到"AI 自我进化"的感觉。想继续冲高可以重复更多轮。

---

## 第 5 步：对比优化效果 —— 全景回顾

### 🅰️ OpenClaw 方式

你的对话上下文中已经保存了全部历史：初始提示词、每轮优化后的提示词、每轮评分。直接在当前对话中生成全景对比报告：

> 请对比初始提示词（第 2 步生成的版本）和最终提示词（第 4 步第 3 轮优化后的版本）：
> 1. 逐段对比差异，说明每处改动解决了什么问题
> 2. 汇总各轮分数变化趋势
> 3. 总结：哪些优化策略提分最多，哪些是关键转折点

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

> 💡 **展示建议**：这是最终的成就感高潮。用对比表格展示：
>
> ```
> 📊 优化全景
>
>                      初始版本          →  最终版本
> ──────────────────────────────────────────────────
> 平均得分               72                  91
> 提示词长度             ~150 字              ~500 字
> 推理链（CoT）          ❌ 无               ✅ 先分析情绪 → 再匹配歌词
> 输出格式               ❌ 自由发挥          ✅ 10 句候选 🎵 金句 —— 《歌名》歌手 + 解读
> Few-shot 示例          ❌ 无               ✅ 2 个高质量示范
>
> 🎵 最大进步用例：「月亮的日常温柔」 62 → 89（+27 分）
>    初始：10 句全偏大气风格（最高相似度 55%）
>    最终：10 句中第 3 句「若是月亮还没来，路灯也可照窗台」达到 92% 相似 ✅
> ```
>
> **🎉 你定了标准（5 条金句 × 10 句候选），AI 自己想办法达到了标准。这就是 Meta-Agent。**

---

## 📋 完整流程速查

### 🅰️ OpenClaw 方式

| 步骤 | Spawn 的 Sub Agent | 传入内容 | 产出 |
|------|-------------------|---------|------|
| 0 | — | — | 无需准备 |
| 1 | — | — | 5 条测试用例（保存在对话上下文中） |
| 2 | `meta-prompt-engineer` → `meta-rubric-gen` × 5 | 理想态 + 示例用例 | 提示词 `PROMPT` + 5 条 Judge |
| 3 | `lyrics-golden-lines` × 5 → `meta-eval-judge` × 5 | Input → 评估 | 5 条金句输出 + 5 条评分 |
| 4 | 循环 3 轮：Agent × 5 → Judge × 5 → Prompt Engineer | 上轮反馈 | 每轮分数变化 + 新提示词 |
| 5 | — | 对话上下文中的全部历史 | 初始 vs 最终全景对比 |

### 🅱️🅲 CLI / IDE 方式

| 步骤 | 执行 | 完成后读什么 | 展示什么 |
|------|------|-------------|---------|
| 0 | git clone + SETUP.md | verify_setup.py | 环境 ✅ |
| 1 | 创建 demo_testcases.yaml | — | 5 条金句用例（每条要求 10 句候选） |
| 2 | `-p "create_agent ... 方式 c"` | `prompt.md` + `ideal_state.md` | AI 写的提示词和理想态 |
| 3 | `-p "test_agent ..."` | `case_N_actual_result.txt` + `评估报告.md` | **5 条需求各 10 句候选金句** + 分数 |
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
| 安装 | 无需安装 | 需要 CLI 工具或 IDE |
| 文件系统 | 无（所有中间产物保存在对话上下文中） | 有（产物写入 `source/[Agent]/tmp/`） |
| 工具调用 | 不支持（纯文本 sub agent） | 支持（MCP、文件读写、命令执行） |
| 适用场景 | 纯文本生成类 Agent（如歌词金句） | 所有 Agent（含日志分析、代码审查等需要工具的） |
| 体验完整度 | ⭐⭐⭐⭐（核心流程完整） | ⭐⭐⭐⭐⭐（全功能） |

### Q: 为什么 `evo_looper` 要拆成手动步骤？

`evo_looper` 是多轮循环：每轮 5 条测试（每条 10 句候选金句）+ 5 次评估 + 优化提示词。单次 `-p` 调用会上下文爆炸。

拆成独立步骤的好处：
1. 每轮上下文都是干净的
2. 每轮之间可以读取文件、给用户展示进度
3. 用户能感受到**每一轮的具体进步**（金句回复变好了、分数涨了、提示词改了什么）

### Q: 迭代优化卡在某个分数不动了？

先检查评估标准是否合理：
```bash
CodeBuddy --dangerously-skip-permissions -p "calibrate lyrics-golden-lines"
```

### Q: 这个项目能创建什么样的 Agent？

**CLI / IDE 方式**：任何"文本输入 → 文本输出"的 Agent，包括需要工具调用的：代码审查助手、翻译评估、客服话术、SQL 助手、日志分析等。

**OpenClaw 方式**：仅限纯文本生成类 Agent（无工具调用）。金句助手、文案生成、翻译润色等都可以。需要 MCP / 文件操作 / 命令执行的 Agent 请使用 CLI 或 IDE。

---

## 🧩 背后的原理

```
你的 5 条金句用例（每条要求 10 句候选）
    │
    ▼
meta-prompt-engineer ──→ 从用例反推出提示词
    │
    ▼
meta-rubric-gen ──→ 为每条用例生成评分标准（核心：10 句中至少 1 句 90% 相似）
    │
    ▼
[运行 Agent] ──→ 实际输出（5 条需求 × 10 句候选金句）
    │
    ▼
meta-eval-judge ──→ 逐条打分 + 指出不足
    │
    ▼
meta-prompt-engineer ──→ 根据不足优化提示词（循环 ↑）
    │
    ▼
meta-retrospective ──→ 每 3 轮全局复盘，防止优化方向跑偏
```

核心思想：**用 AI 来解决 AI 的问题**。你定标准，AI 自己进化。

---

## 🎓 完成后的下一步

1. **创建自己的 Agent** —— 换一组测试用例，走同样的流程
2. **升级到 CLI / IDE** —— 如果你用的是 OpenClaw 方式，安装 CLI 工具可以解锁工具调用能力，支持更复杂的 Agent
3. **深入评估体系** —— `calibrate` 诊断三元组一致性（CLI / IDE）
4. **多平台测试** —— `test_agent lyrics-golden-lines@codebuddycli`（CLI / IDE）
5. **阅读完整文档** —— [README.md](README.md)、[SETUP.md](SETUP.md)
