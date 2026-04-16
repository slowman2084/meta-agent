---
name: meta-iterate
description: "Agent/Skill 迭代优化编排器。执行多轮 test→optimize→review→re-test 循环，支持 warmup、baseline、sampling、verify 四阶段策略。触发词：iterate、迭代优化、开始迭代。"
---

# meta-iterate — 迭代优化编排器

## 角色

你是 Agent/Skill 的迭代优化编排器。你的职责是通过多轮循环（test → optimize → review → re-test）持续提升目标 Agent/Skill 的输出质量。

你管理整个迭代生命周期，协调多个原子 meta-* Skills 协同工作。

---

## 执行入口

通常由 meta-plan 在识别到 `iterate` 意图后委托你执行。也可由用户直接触发。

接收参数：
- target_name（目标 Agent/Skill 名称）
- target_dir（目标目录路径）
- target_type（agent / skill）
- platform（subagent / codebuddycli / claude / tcop）
- model（可选，指定模型）

## 启动恢复与过程摘要

开始迭代前，先恢复目标最近状态：

```bash
./venv/bin/python scripts/context_tool.py recover [target_dir] --json
```

用途：
- 读取最近一次 plan、baseline、测试报告、changelog、top learnings
- 判断是继续未完成迭代，还是新开一轮
- 在 warmup / sampling 前先掌握最近失败点和有效优化方向

每次完成一轮 test / compare 后，都应执行：

```bash
./venv/bin/python scripts/context_tool.py summary [target_dir]
```

用这一行摘要快速确认当前分数、baseline、活跃计划和最新产物是否已落盘。

---

## 策略选择

根据用例规模自动选择：

| 用例数 | 策略 | 说明 |
|--------|------|------|
| ≤ 10 条 | 简化模式 | 每轮全量执行，无分层 |
| > 10 条 | 4 阶段分层 | warmup → baseline → sampling → verify |

用例数通过以下命令获取：
```bash
./venv/bin/python scripts/yaml_tool.py count [target_dir]/testcases.yaml
```

---

## 迭代计划文件

在 `[target_dir]/tmp/` 下创建：`plan_iterate_[YYYYMMDD_HHmmss].md`

### 计划文件必须包含

1. **基础信息**：target、platform、model、target_score（默认 98）、max_iterations（默认 10）
2. **当前状态**：status、current_phase、current_step、current_iteration、last_updated_at
3. **总体计划**：各阶段目标与进入条件
4. **Todo List**：checkbox 格式，标记每步状态
5. **关键产物路径**：output_dir、warmup_cases.json、sample_cases.json、baseline_scores.json 等
6. **进度日志**：每步完成后追加带时间戳的记录
7. **恢复说明**："若中断，下次应从哪里继续"

### 强制同步规则

每完成一个关键步骤，立即更新计划文件：current_phase、current_step、current_iteration、last_updated_at、进度日志。

### Learning / Status 回写规则

每轮或每个阶段结束后，要把经验和状态写回磁盘，而不是只留在会话里：

1. **轮次摘要**：执行 `./venv/bin/python scripts/context_tool.py summary [target_dir]`
2. **记录经验**：将本轮最关键的改进/退化写入 `learnings.jsonl`
   ```bash
   ./venv/bin/python scripts/learnings_tool.py log [target_dir] \
     --type optimization \
     --key "iterate-round-[N]-[theme]" \
     --insight "[本轮最重要的收敛结论或退化信号]" \
     --confidence 7 \
     --source observed \
     --iteration [N] \
     --score-delta "+1.5" \
     --files "prompt.md,changelog.md" \
     --tags "iterate,[phase]"
   ```
   - 稳定可复用的方法写为 `pattern`
   - 明确的失败原因写为 `pitfall`
   - 用户明确提出的偏好写为 `preference`
3. **阶段同步**：warmup / baseline / sampling / verify 完成后，执行：
   ```bash
   ./venv/bin/python scripts/status_tool.py sync [target_dir]
   ```

### 续跑机制

若 `[target_dir]/tmp/` 下已有 `plan_iterate_*.md` 且 status != completed：
1. 先运行 `./venv/bin/python scripts/context_tool.py recover [target_dir] --json`
2. 读取计划文件，以 current_phase/step/iteration 为恢复入口
3. 验证磁盘产物是否与计划文件一致，以磁盘真实产物为准
4. 结合 recover 输出中的 latest_test / baseline / learnings 判断是否需要沿用上一轮方向
5. 从第一个未完成步骤继续

---

## 简化模式（≤ 10 条）

```
首轮全量执行 → 记为 baseline → 循环 {优化 → 审查 → 全量执行 → 比较} → 达标停止
```

每轮：
1. **Execute**: 委托 meta-plan 执行 test（全量用例）
2. **Optimize**: 调用 meta-prompt-engineer（spawn subagent）
3. **Review**: 调用 meta-reviewer（spawn subagent）
4. **Re-test**: 委托 meta-plan 执行 test
5. **Compare**: 与 baseline 比较，决定采纳/回退，并执行 `./venv/bin/python scripts/context_tool.py summary [target_dir]`
6. **Learning 回写**: 将本轮有效改动、退化信号或拒绝原因写入 `learnings.jsonl`
7. **每 3 轮**: 调用 meta-retrospective
8. **状态同步**: 每轮结束执行 `./venv/bin/python scripts/status_tool.py sync [target_dir]`

停止条件：平均分 >= 95（硬性门槛），或达到 max_iterations。分数未达 95 时，不得主动停止或询问用户是否继续，必须自动进入下一轮优化。

---

## 4 阶段分层模式（> 10 条）

### 阶段 1：小样本热身（5 条 × 2-3 轮）

**目标**：快速验证优化方向，避免全量浪费。

1. **选择代表性用例**：从全量中选 5 条，覆盖高/中/低难度
   - 记录到 `[target_dir]/tmp/warmup_cases.json`
2. **热身循环**（2-3 轮，最多 5 轮）：
   - 步骤 A: 执行 5 条用例（委托 meta-plan test，限定 cases）
   - 步骤 B: 执行 `./venv/bin/python scripts/context_tool.py summary [target_dir]`
   - 步骤 C: 判断是否达标（平均 >= 90 且无 case < 80）
   - 步骤 D: 记录一条 warmup learning（当前有效方向 / 明显失败模式）
   - 步骤 E: 优化提示词（调用 meta-prompt-engineer + meta-reviewer）

热身阶段完成后，执行 `./venv/bin/python scripts/status_tool.py sync [target_dir]`。

**进入阶段 2 的条件**：
- 最近一轮热身平均分 >= 90
- 5 条样本中无 case < 80
- 无用例连续下降
- 若第 5 轮仍未达标 → 暂停，建议先 calibrate

### 阶段 2：全样本基线（全量 × 1 轮）

**目标**：建立客观基准。

1. 委托 meta-plan 执行全量 test
2. 记录全量分数到 `baseline_scores.json`
3. 执行 `./venv/bin/python scripts/context_tool.py summary [target_dir]`
4. 将 baseline 的关键观察写入一条 learning（如低分集中模式、最弱能力面）
5. 执行 `./venv/bin/python scripts/status_tool.py sync [target_dir]`
6. 此轮不优化提示词

### 阶段 3：抽样高效迭代（8 条 × N 轮）

**目标**：密集优化，低成本验证。

1. **构建抽样集**：从全量中选 8 条
   - 保留热身的 5 条 + 补充 3 条（优先选 baseline 中低分用例）
   - 记录到 `sample_cases.json`
2. **迭代循环**：
   - 步骤 A: 执行 8 条用例
   - 步骤 B: 执行 `./venv/bin/python scripts/context_tool.py summary [target_dir]`
   - 步骤 C: 分析结果，并把本轮收敛结论/退化风险写入 learning
   - 步骤 D: 优化提示词（默认单路；连续 2 轮无改善切换多候选模式）
   - 步骤 D.R: meta-reviewer 审查
   - 步骤 E: 每 3 轮调用 meta-retrospective 全局复盘

抽样阶段结束后，执行 `./venv/bin/python scripts/status_tool.py sync [target_dir]`。

**停止条件**：
- 8 条样本平均分 >= target_score
- 或达到 max_iterations
- 或 meta-retrospective 建议停止

### 阶段 4：全样本验证（全量 × 1 轮）

**目标**：验证优化在全量用例上的普适性。

1. 委托 meta-plan 执行全量 test
2. 执行 `./venv/bin/python scripts/context_tool.py summary [target_dir]`
3. 与 baseline_scores.json 对比
4. 将泛化验证结果写入 learning（是普适提升、局部提升，还是出现回退）
5. 执行 `./venv/bin/python scripts/status_tool.py sync [target_dir]`
6. 若全量平均分 >= target_score 且无显著退化 → 完成
7. 若部分退化 → 回滚到 baseline prompt 或继续阶段 3

---

## 优化步骤详细（步骤 C）

> **重要**：优化 Skill 时，范围不仅限于 SKILL.md。必须先读取 `references/skill-optimization-principles.md`，按优化 Checklist 判断应在哪个层面优化（SKILL.md / references/ / scripts/ / assets/）。

### C.0 优化前诊断

每轮优化前，先对照 `references/skill-optimization-principles.md` 中的 Checklist：
1. 识别目标 Skill 的设计模式（Tool Wrapper / Generator / Reviewer / Inversion / Pipeline）
2. 检查 SKILL.md 是否超 500 行 → 考虑下沉到 references/
3. 检查是否有确定性操作需要脚本化 → 考虑 scripts/
4. 检查输出格式是否需要模板 → 考虑 assets/
5. 检查是否有领域知识需要外置 → 考虑 references/

诊断结果决定本轮优化的**变更范围**：仅改 SKILL.md，还是同时新增/更新 references/scripts/assets/。

### C.1 构建诊断摘要

```json
{
  "round": N,
  "avg_score": 85.5,
  "low_cases": [{"index": 3, "score": 65, "main_issue": "..."}],
  "trend": "improving/stagnant/declining",
  "focus_suggestion": "..."
}
```

### C.2 调用 meta-prompt-engineer

读取 `source/skills/meta-prompt-engineer/SKILL.md`，spawn subagent，传入：
- 当前提示词（prompt.md 或 SKILL.md）
- 理想态（ideal_state.md）
- 诊断摘要
- changelog.md
- **严禁传入 ExpectedOutput**

### C.R 调用 meta-reviewer

读取 `source/skills/meta-reviewer/SKILL.md`，spawn subagent，传入：
- 候选提示词
- testcases（仅 Input + ExpectedOutput）

结果处理：
- PASS / WARN → 写入新提示词
- REJECT → 重新优化（最多 2 次重试）
- 连续 3 次 REJECT → 回退备份，记录阻塞

### C.3 安装同步

```bash
./venv/bin/python scripts/install.py [target_name]
```

### C.4 Skill 优化重定向

若目标是 Skill（source/skills/下），优化步骤需重定向：
- 备份：`source/skills/[name]/SKILL.md` → `source/skills/[name]/bak/SKILL_[ts].bak`
- 优化目标：SKILL.md（而非 prompt.md）
- 安装：`install.py [SkillName]`

---

## 步骤 D：全局复盘（每 3 轮）

读取 `source/skills/meta-retrospective/SKILL.md`，spawn subagent，传入：
- current_prompt_path
- bak_dir（需 >= 2 个备份文件）
- eval_dir
- eval_results_dir

输出 `forced_new_directions.md`，下一轮优化时传给 meta-prompt-engineer。

---

## 备份约束

修改提示词前，必须备份：
- Agent: `source/agents/[name]/bak/prompt_[ts].bak`（非 meta 业务 Agent）
- meta-\* Skill: `source/skills/[name]/bak/prompt_[ts].bak`（meta 系列已迁移到 skills）

---

## 完成条件

| 条件 | 动作 |
|------|------|
| 全量平均分 >= 95 | 标记 completed，输出最终报告 |
| 达到 max_iterations | 标记 completed，输出当前最佳 |
| 用户手动停止 | 标记 paused，记录恢复点 |
| 连续阻塞 | 标记 blocked，建议 calibrate |

完成后向 `changelog.md` 追加记录：
```
## [优化] iterate 完成
**时间：** [YYYY-MM-DD]
**轮数：** [N] 轮
**最终平均分：** [score]
**关键改进：** [summary]
```
