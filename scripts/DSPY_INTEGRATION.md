# DSPy 集成指南

## 概述

DSPy 是 Stanford 开发的声明式 LLM 编程框架，可以自动优化提示词。本指南说明如何在 `meta-agent` 项目中集成和使用 DSPy。

## 核心优势

| 特性 | 传统优化 | DSPy 优化 |
|------|---------|----------|
| **Few-Shot 选择** | 手工挑选或 LLM 建议 | 基于数据自动搜索最佳示例 |
| **指令优化** | 基于语义分析重写 | 基于评估分数的数学优化 |
| **稳定性** | 依赖 LLM 单次推理质量 | 多轮验证，选出最稳定版本 |
| **可复现性** | 低（每次运行不同） | 高（相同数据+配置=相同结果） |

## 使用方式

### 方式 1：独立优化（推荐用于实验）

直接运行优化脚本：

```bash
# 使用 BootstrapFewShot 优化（快速）
./venv/bin/python scripts/dspy_optimizer.py --agent meta-rubric-gen

# 使用 MIPRO 优化（更彻底）
./venv/bin/python scripts/dspy_optimizer.py --agent meta-rubric-gen --optimizer mipro

# 指定模型
./venv/bin/python scripts/dspy_optimizer.py --agent meta-rubric-gen --model gpt-5.3-codex

# Dry run（仅测试，不写文件）
./venv/bin/python scripts/dspy_optimizer.py --agent meta-rubric-gen --dry-run
```

### 方式 2：集成到 evo_looper（推荐用于生产）

在 `evo_looper` 迭代优化模式中，将 DSPy 作为**步骤 C 的高级优化策略**。

#### 触发条件

当满足以下任一条件时，建议使用 DSPy 模式：

1. **数据充足**：测试用例 ≥ 20 条
2. **收敛困难**：传统优化连续 3 轮无改善
3. **高稳定性要求**：任务对输出一致性要求极高

#### 集成流程

在 `evo_looper` 的**步骤 C (优化提示词)** 中，增加 DSPy 分支：

```
步骤 C：优化提示词
├─ 判断优化模式
│  ├─ 轮次 ≤ 3 或用户指定 → 单路模式（meta-prompt-engineer）
│  ├─ 轮次 ≥ 4 或停滞触发 → 3路候选模式
│  └─ 数据充足 + 收敛困难 → DSPy 模式 ⭐ 新增
│
├─ 执行优化
│  ├─ 单路模式 → 调用 meta-prompt-engineer
│  ├─ 3路模式 → 并行调用 meta-prompt-engineer × 3
│  └─ DSPy 模式 → 调用 scripts/dspy_optimizer.py ⭐ 新增
│
└─ 后续处理
   ├─ 测试 + 评估（步骤 A）
   └─ 决定是否继续迭代
```

#### 调用示例

在主控编排中，当检测到需要 DSPy 优化时：

```bash
# 1. 运行 DSPy 优化
./venv/bin/python scripts/dspy_optimizer.py \
  --agent meta-rubric-gen \
  --optimizer bootstrap \
  --max-demos 4 \
  --model gpt-5.3-codex

# 2. 重新安装（同步到 IDE）
./venv/bin/python scripts/install.py meta-rubric-gen

# 3. 继续测试评估（步骤 A）
# ... 调用 meta-eval-judge ...
```

## 配置选项

### 优化器选择

| 优化器 | 适用场景 | 速度 | 效果 |
|--------|---------|------|------|
| **BootstrapFewShot** | 快速优化 Few-Shot 示例 | ⚡⚡⚡ | ⭐⭐⭐ |
| **MIPRO** | 同时优化指令和示例 | ⚡ | ⭐⭐⭐⭐⭐ |

### 参数调优

```bash
--max-demos 4          # Few-Shot 示例数量（建议 2-8）
--threshold 80.0       # 评估分数阈值（建议 75-90）
--model gpt-5.3-codex   # 使用的 LLM 模型
```

## 与现有组件的集成

### 1. 数据来源：`testcases.yaml`

DSPy 直接使用 `testcases.yaml` 作为训练数据：

```yaml
cases:
  - Input: "..."
    ExpectedOutput: "..."  # DSPy 将学习这些示例
    Judge: "..."
```

**注意**：DSPy 只会使用 `Input` 和 `ExpectedOutput`，不会使用 `Judge` 字段（因为 Judge 是评估标准，不是答案）。

### 2. 评估标准：`meta-eval-judge`

DSPy 的 Metric 函数需要调用 `meta-eval-judge`：

```python
def metric(example, pred):
    # 调用 meta-eval-judge Sub Agent
    score = call_meta_eval_judge(
        input=example.input_text,
        expected=example.output_text,
        actual=pred.output_text
    )
    return score >= 80
```

当前实现使用简单的词重叠作为占位符，生产环境需要替换为真实的 `meta-eval-judge` 调用。

### 3. 理想态：`ideal_state.md`

DSPy 不会直接使用 `ideal_state.md`，但：
- `ideal_state.md` 定义了 Agent 的核心能力
- DSPy 优化的目标是通过测试用例来实现这些能力
- 优化后的提示词应该符合理想态的描述

### 4. 变更记录：`changelog.md`

DSPy 优化会自动追加变更记录：

```markdown
## [优化] DSPy 自动优化 (第 N 轮)

**优化时间:** 2026-03-06T10:45:00
**优化器:** bootstrap
**Few-Shot 示例数:** 4
**训练集大小:** 16

**优化说明:**
- 使用 DSPy BootstrapFewShot 优化器自动选择最佳 Few-Shot 示例
- 自动生成推理链 (Chain-of-Thought)
```

## 最佳实践

### 1. 何时使用 DSPy

| 场景 | 推荐方式 |
|------|---------|
| 初始创建 Agent | 使用 `meta-prompt-engineer`（语义理解更准确） |
| 小数据集（< 10 条） | 使用 `meta-prompt-engineer`（DSPy 需要更多数据） |
| 中等数据集（10-20 条） | 混合使用（先传统优化，再用 DSPy 微调） |
| 大数据集（> 20 条） | **首选 DSPy**（数据驱动效果更稳定） |
| 需要高稳定性 | **首选 DSPy**（多次验证选最优） |
| 需要快速迭代 | 使用 `meta-prompt-engineer`（更快） |

### 2. 组合策略

**推荐流程**：

```
第 1-3 轮：传统优化（meta-prompt-engineer）
  → 快速建立基础能力

第 4-6 轮：DSPy 优化
  → 数据驱动精细调优

第 7+ 轮：混合使用
  → 根据收敛情况灵活选择
```

### 3. 质量保证

DSPy 优化后，务必：

1. **运行完整测试**：
   ```bash
   # 使用 test_agent 模式
   ./venv/bin/python scripts/install.py meta-rubric-gen
   # 然后调用 meta-eval-judge 评估所有用例
   ```

2. **检查 Few-Shot 示例**：
   - 确认示例与测试用例**不重复**
   - 确认示例展示了**通用推理模式**
   - 确认示例符合**理想态要求**

3. **对比基线**：
   ```bash
   # 比较优化前后的平均分
   diff baseline_scores.json current_scores.json
   ```

## 常见问题

### Q1: DSPy 优化需要多长时间？

- **BootstrapFewShot**: 2-5 分钟（取决于测试用例数量）
- **MIPRO**: 10-30 分钟（会尝试多种组合）

### Q2: DSPy 会覆盖我的提示词吗？

不会完全覆盖。DSPy 会：
1. 提取最佳 Few-Shot 示例
2. 保留原有提示词的核心结构
3. 将优化内容注入到合适的位置

建议优化前先备份（脚本会自动备份到 `bak/`）。

### Q3: 如何回退 DSPy 优化？

```bash
# 从备份恢复
cp source/meta-rubric-gen/bak/prompt_20260306_104500.bak \
   source/meta-rubric-gen/prompt.md

# 重新安装
./venv/bin/python scripts/install.py meta-rubric-gen
```

### Q4: DSPy 优化失败怎么办？

检查：
1. **API Key**: 是否设置了 `OPENAI_API_KEY`
2. **测试用例**: `testcases.yaml` 是否包含足够的 `Input` 和 `ExpectedOutput`
3. **网络**: 是否能访问 LLM API
4. **日志**: 查看 DSPy 的详细输出

## 示例：完整优化流程

```bash
# 1. 准备测试用例（至少 20 条）
vim source/meta-rubric-gen/testcases.yaml

# 2. 运行 DSPy 优化
./venv/bin/python scripts/dspy_optimizer.py \
  --agent meta-rubric-gen \
  --optimizer bootstrap \
  --max-demos 4

# 3. 安装优化后的提示词
./venv/bin/python scripts/install.py meta-rubric-gen

# 4. 测试评估
# ... 调用 test_agent 模式 ...

# 5. 如果满意，提交变更
git add source/meta-rubric-gen/
git commit -m "feat: DSPy 优化 meta-rubric-gen 提示词"
```

## 下一步

1. **尝试 DSPy 优化**：选择一个测试用例较多的 Agent（如 `meta-rubric-gen`）
2. **对比效果**：与传统优化方式对比分数改善
3. **反馈调优**：根据效果调整参数（`--max-demos`, `--optimizer`）
4. **集成流程**：将 DSPy 作为 `evo_looper` 的标准优化选项

## 参考资料

- [DSPy 官方文档](https://dspy.ai/)
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)
- [BootstrapFewShot 论文](https://arxiv.org/abs/2310.06827)
- [MIPRO 论文](https://arxiv.org/abs/2401.11529)
